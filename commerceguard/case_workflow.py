"""Я фиксирую человеческий разбор с audit и optimistic version одним COMMIT."""
import hashlib
import json
from uuid import UUID
from .access import authorize,username
from .case_projection import case_key
from .file_contracts import canonical_time
from .ingest_journal import schema_guard
from .postgres import postgres_session
from .workbench_store import WorkbenchError

ACTIONS={'assign','comment'}

def command(key,action,request_id,expected_version,expected_revision,expected_run_id,value):
    case_key(key)
    if action not in ACTIONS:raise WorkbenchError('ACTION_FORBIDDEN',403)
    try:rid=str(UUID(request_id));run=str(UUID(expected_run_id))
    except (ValueError,TypeError,AttributeError):raise WorkbenchError('REQUEST_ID_INVALID') from None
    for n,minimum in [(expected_version,0),(expected_revision,1)]:
        if type(n) is not int or not minimum<=n<2**63-1:raise WorkbenchError('EXPECTED_VERSION_INVALID')
    if type(value) is not str:raise WorkbenchError('VALUE_INVALID')
    if action=='assign':
        if value:username(value)
    else:
        if not value.strip() or len(value)>2000 or any(ord(x)<32 and x not in '\n\t\r' for x in value):raise WorkbenchError('COMMENT_LENGTH_1_2000')
        try:value.encode('utf-8')
        except UnicodeError:raise WorkbenchError('COMMENT_ENCODING') from None
    payload={'case_key':key,'action':action,'expected_version':expected_version,'expected_revision':expected_revision,'expected_run_id':run,'value':value}
    text=json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=True)
    return rid,payload,hashlib.sha256(text.encode('ascii')).hexdigest()

def mutate(key,*,action,request_id,expected_version,expected_revision,expected_run_id,value,token,csrf,dsn_env='COMMERCEGUARD_DATABASE_URL'):
    rid,payload,digest=command(key,action,request_id,expected_version,expected_revision,expected_run_id,value)
    from psycopg.types.json import Jsonb
    with postgres_session(dsn_env,application_name='commerceguard-case-workflow') as conn:
        with conn.transaction():
            with conn.cursor() as c:
                schema_guard(c)
                # Я получаю actor только из активной серверной сессии, не из поля формы.
                actor=authorize(c,token,action=action,csrf=csrf)
                lock=int.from_bytes(hashlib.sha256((actor['username']+':'+rid).encode()).digest()[:8],'big',signed=True)
                c.execute('SELECT pg_advisory_xact_lock(%s::bigint)',(lock,))
                c.execute('SELECT merchant_id,workflow_version,assignee,workflow_status,revision_number,evaluated_run_id,finding_state '
                          'FROM commerceguard.ops_case WHERE case_key=%s FOR UPDATE',(key,))
                row=c.fetchone()
                if not row:raise WorkbenchError('CASE_NOT_FOUND',404)
                merchant,version,assignee,status,revision,run,presence=row
                if merchant not in actor['merchants']:raise WorkbenchError('SCOPE_FORBIDDEN',403)
                c.execute('SELECT case_key,command_sha256,after_json FROM commerceguard.ops_case_human_event WHERE actor=%s AND request_id=%s',(actor['username'],UUID(rid)))
                previous=c.fetchone()
                if previous:
                    if previous[0]!=key or previous[1]!=digest:raise WorkbenchError('REQUEST_ID_REUSED',409)
                    return {'replayed':True,'request_id':rid,'case_key':key,'saved':previous[2]}
                if version!=expected_version or revision!=expected_revision or str(run)!=payload['expected_run_id']:raise WorkbenchError('CASE_VERSION_CONFLICT',409)
                if action=='assign':
                    target=value or None
                    if actor['role']=='analyst' and (target not in (None,actor['username']) or assignee not in (None,actor['username'])):raise WorkbenchError('ASSIGN_SELF_ONLY',403)
                    if target:
                        c.execute('SELECT u.username FROM commerceguard.web_user u JOIN commerceguard.web_user_merchant m USING(username) '
                                  "WHERE u.username=%s AND u.active AND u.role IN ('analyst','manager') AND m.merchant_id=%s FOR SHARE OF u",(target,merchant))
                        if not c.fetchone():raise WorkbenchError('ASSIGNEE_UNAVAILABLE',400)
                    if target==assignee:raise WorkbenchError('WORKFLOW_NO_CHANGE',409)
                    assignee=target
                before={'version':version,'assignee':row[2],'status':row[3]}
                after={'version':version+1,'assignee':assignee,'status':status}
                c.execute('UPDATE commerceguard.ops_case SET workflow_version=%s,assignee=%s WHERE case_key=%s',(version+1,assignee,key))
                c.execute('INSERT INTO commerceguard.ops_case_human_event(case_key,workflow_version,actor,request_id,command_sha256,command_json,action,before_json,after_json,observed_revision,observed_run_id,finding_state) '
                          'VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                          (key,version+1,actor['username'],UUID(rid),digest,Jsonb(payload),action,Jsonb(before),Jsonb(after),revision,run,presence))
    return {'replayed':False,'request_id':rid,'case_key':key,'saved':after}

def read_workflow(key,*,token,before_version=None,dsn_env='COMMERCEGUARD_DATABASE_URL'):
    case_key(key)
    if before_version is not None and (type(before_version) is not int or not 1<=before_version<2**63):raise WorkbenchError('WORKFLOW_CURSOR')
    with postgres_session(dsn_env,application_name='commerceguard-case-audit') as conn:
        with conn.transaction():
            with conn.cursor() as c:
                c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
                schema_guard(c,write=False)
                actor=authorize(c,token)
                c.execute('SELECT merchant_id,workflow_version,assignee,workflow_status,revision_number,evaluated_run_id FROM commerceguard.ops_case WHERE case_key=%s',(key,))
                row=c.fetchone()
                if not row:raise WorkbenchError('CASE_NOT_FOUND',404)
                if row[0] not in actor['merchants']:raise WorkbenchError('SCOPE_FORBIDDEN',403)
                c.execute('SELECT workflow_version,actor,request_id,action,command_json,before_json,after_json,observed_revision,observed_run_id,finding_state,recorded_at '
                          'FROM commerceguard.ops_case_human_event WHERE case_key=%s AND (%s::bigint IS NULL OR workflow_version<%s) ORDER BY workflow_version DESC LIMIT 21',(key,before_version,before_version))
                rows=c.fetchall()
    history=[dict(zip(('version','actor','request_id','action','command','before','after','observed_revision','observed_run_id','presence','recorded_at'),(*r[:2],str(r[2]),*r[3:8],str(r[8]),r[9],canonical_time(r[10])))) for r in rows[:20]]
    return {'version':row[1],'assignee':row[2],'status':row[3],'revision':row[4],'run_id':str(row[5]),'history':history,
            'next_before_version':history[-1]['version'] if len(rows)>20 else None}
