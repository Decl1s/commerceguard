"""Я читаю очередь отдельным snapshot, сохраняя зерно Case и run context."""
from uuid import UUID
from .case_projection import case_key
from .domain import Rule, require_currency, require_id
from .file_contracts import canonical_time
from .ingest_journal import schema_guard
from .postgres import postgres_session

class WorkbenchError(ValueError):
    def __init__(self, code, status=400): self.code=code; self.status=status; super().__init__(code)

def filters(params: dict) -> dict:
    allowed={'merchant','currency','rule','status','presence','age_min_days','age_max_days','after','run_id','limit','assignee'}
    if set(params)-allowed: raise WorkbenchError('QUEUE_FILTER_UNKNOWN')
    p={**{'status':'open','presence':'present','limit':'50','age_min_days':'0','age_max_days':'36500'},**params}
    require_id(p.get('merchant'),'merchant_id')
    if p.get('assignee'):
        import re
        if not re.fullmatch('[a-z][a-z0-9_-]{2,31}',p['assignee']):raise WorkbenchError('ASSIGNEE_FILTER')
    if p.get('currency'): require_currency(p['currency'])
    if p.get('rule'): Rule(p['rule'])
    if p['status'] not in ('open','closed','all') or p['presence'] not in ('present','absent','all'): raise WorkbenchError('QUEUE_FILTER')
    for k,lo,hi in [('limit',1,100),('age_min_days',0,36500),('age_max_days',0,36500)]:
        if not isinstance(p[k],str) or not p[k].isascii() or not p[k].isdigit() or not lo<=int(p[k])<=hi: raise WorkbenchError('QUEUE_RANGE')
        p[k]=int(p[k])
    if p['age_min_days']>p['age_max_days']: raise WorkbenchError('QUEUE_AGE_RANGE')
    if p.get('after'):
        case_key(p['after'])
        if not p.get('run_id'): raise WorkbenchError('QUEUE_CURSOR_RUN_REQUIRED')
    if p.get('run_id'):
        try: p['run_id']=str(UUID(p['run_id']))
        except (ValueError,TypeError): raise WorkbenchError('QUEUE_RUN_ID') from None
    return p

def queue(params, *, dsn_env='COMMERCEGUARD_DATABASE_URL'):
    p=filters(params)
    with postgres_session(dsn_env,application_name='commerceguard-workbench') as conn:
        with conn.transaction():
            with conn.cursor() as c:
                c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
                schema_guard(c,write=False)
                c.execute('SELECT clock_timestamp()'); now=c.fetchone()[0]
                c.execute('SELECT s.current_run_id,s.generation,m.as_of,m.knowledge_at,r.published_at '
                          'FROM commerceguard.ops_case_stream s JOIN commerceguard.ops_run_manifest m ON m.run_id=s.current_run_id '
                          'JOIN commerceguard.ops_run_result r ON r.run_id=s.current_run_id WHERE s.merchant_id=%s',(p['merchant'],))
                row=c.fetchone()
                context=None if not row else dict(run_id=str(row[0]),generation=row[1],as_of=canonical_time(row[2]),
                    knowledge_at=canonical_time(row[3]),published_at=canonical_time(row[4]),age_seconds=max(0,int((now-row[2]).total_seconds())))
                if p.get('run_id') and (not row or p['run_id']!=str(row[0])): raise WorkbenchError('QUEUE_HEAD_CHANGED',409)
                c.execute("SELECT count(*) FROM commerceguard.ops_case c JOIN LATERAL "
                          "(SELECT observed_revision FROM commerceguard.ops_case_human_event e WHERE e.case_key=c.case_key AND e.action='close' ORDER BY e.workflow_version DESC LIMIT 1) e ON true "
                          "WHERE c.merchant_id=%s AND c.workflow_status='closed' AND c.finding_state='present' AND e.observed_revision<c.revision_number",(p['merchant'],))
                needs_review=c.fetchone()[0]
                where=['c.merchant_id=%s']; args=[p['merchant']]
                for field,col in [('currency','currency'),('rule','rule_code'),('status','workflow_status'),('presence','finding_state'),('assignee','assignee')]:
                    if p.get(field) and p[field]!='all': where.append('c.'+col+'=%s');args.append(p[field])
                where.extend(['a.applied_at<=%s - %s * interval \'1 day\'','a.applied_at>=%s - %s * interval \'1 day\''])
                args.extend([now,p['age_min_days'],now,p['age_max_days']])
                base=' FROM commerceguard.ops_case c JOIN commerceguard.ops_case_application a ON a.run_id=c.first_run_id WHERE '+' AND '.join(where)
                c.execute('SELECT c.currency,count(*)'+base+' GROUP BY c.currency ORDER BY c.currency',args)
                counts=[{'currency':x[0],'case_count':x[1]} for x in c.fetchall()]
                c.execute('SELECT c.case_key,c.order_id,c.currency,c.rule_code,c.finding_state,c.workflow_status,c.revision_number,a.applied_at,c.assignee'+
                          base+' AND c.case_key>%s ORDER BY c.case_key LIMIT %s',(*args,p.get('after') or '',p['limit']+1))
                rows=c.fetchall()
    items=[dict(zip(('case_key','order_id','currency','rule','presence','status','revision','first_detected_at','assignee'),(*r[:7],canonical_time(r[7]),r[8]))) for r in rows[:p['limit']]]
    return {'closed_needs_review':needs_review,'merchant':p['merchant'],'evaluated_at':canonical_time(now),'context':context,'counts_by_currency':counts,'items':items,
            'next_after':items[-1]['case_key'] if len(rows)>p['limit'] else None,'queue_consistency':'live-per-page'}
