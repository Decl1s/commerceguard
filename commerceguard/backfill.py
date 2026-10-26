"""Я сначала показываю чистый календарный план, затем явно закрепляю и выполняю run IDs."""
import argparse
from datetime import date,datetime,time,timedelta,timezone
from importlib import resources
from zoneinfo import ZoneInfo
import hashlib
import json
from pathlib import Path
import re
from .domain import require_id
from .file_contracts import canonical_time,timestamp
from .ingest_journal import schema_guard
from .postgres import postgres_session
from .run_plans import prepare_run,engine_sha256
from .run_execution import execute_run
from .source_health import business_context
from .workbench_store import WorkbenchError

MAX_DAYS=31

def make_plan(merchant,start,end,business_timezone,*,mode='as-was',knowledge_at=None,baselines=None,through=None):
    require_id(merchant,'merchant_id')
    try:first=date.fromisoformat(start);last=date.fromisoformat(end)
    except (TypeError,ValueError):raise WorkbenchError('BACKFILL_DATE') from None
    if not 1<=(last-first).days+1<=MAX_DAYS:raise WorkbenchError('BACKFILL_RANGE_1_31')
    if mode not in ('as-was','as-known-now'):raise WorkbenchError('BACKFILL_MODE')
    # Я валидирую pinned tzdata, затем строю каждую местную полночь отдельно: DST не равен24часам.
    business_context(datetime(2000,1,1,tzinfo=timezone.utc),business_timezone)
    with resources.files('tzdata.zoneinfo').joinpath(*business_timezone.split('/')).open('rb') as stream:zone=ZoneInfo.from_file(stream)
    boundary=timestamp(through,artifact='backfill',field='through') if through else None
    knowledge=timestamp(knowledge_at,artifact='backfill',field='knowledge_at') if knowledge_at else None
    if mode=='as-known-now' and (knowledge is None or type(baselines) is not dict):raise WorkbenchError('BACKFILL_BASELINES_REQUIRED')
    if mode=='as-was' and (knowledge is not None or baselines):raise WorkbenchError('BACKFILL_MODE_CONTEXT')
    days=[]
    for n in range((last-first).days+1):
        day=first+timedelta(days=n)
        begin=datetime.combine(day,time.min,zone).astimezone(timezone.utc)
        until=datetime.combine(day+timedelta(days=1),time.min,zone).astimezone(timezone.utc)-timedelta(microseconds=1)
        if until<begin:raise WorkbenchError('BACKFILL_SKIPPED_DAY')
        if boundary and day==last:
            if not begin<=boundary<=until:raise WorkbenchError('BACKFILL_THROUGH_CONTEXT')
            until=boundary
        if knowledge and knowledge<=until:raise WorkbenchError('BACKFILL_KNOWLEDGE')
        baseline=baselines.get(day.isoformat()) if baselines else None
        if mode=='as-known-now':
            from uuid import UUID
            try:baseline=str(UUID(baseline))
            except (ValueError,TypeError,AttributeError):raise WorkbenchError('BACKFILL_BASELINE_ID') from None
        days.append({'date':day.isoformat(),'as_of':canonical_time(until),'partial':bool(boundary and day==last),'baseline_run_id':baseline})
    return {'version':1,'merchant':merchant,'timezone':business_timezone,'tzdata_version':'2026.5',
            'mode':mode,'knowledge_at':canonical_time(knowledge) if knowledge else None,
            'ruleset':'balance-v2','engine_sha256':engine_sha256(),'days':days}

def _identity(plan):
    return hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()

def _lock(c,job_id):
    if not isinstance(job_id,str) or not re.fullmatch('[a-f0-9]{64}',job_id):raise WorkbenchError('BACKFILL_ID')
    key=int.from_bytes(bytes.fromhex(job_id)[:8],'big',signed=True)
    c.execute('SELECT pg_try_advisory_lock(%s::bigint)',(key,))
    if not c.fetchone()[0]:raise WorkbenchError('BACKFILL_BUSY',409)
    return key

def start(plan,*,dsn_env='COMMERCEGUARD_DATABASE_URL'):
    # Я принимаю только план своей текущей версии; произвольный JSON не становится SQL.
    try:
        expected=make_plan(plan['merchant'],plan['days'][0]['date'],plan['days'][-1]['date'],plan['timezone'],mode=plan['mode'],knowledge_at=plan['knowledge_at'],
                           baselines={d['date']:d['baseline_run_id'] for d in plan['days']} if plan['mode']=='as-known-now' else None,
                           through=plan['days'][-1]['as_of'] if plan['days'][-1]['partial'] else None)
    except (KeyError,IndexError,TypeError):raise WorkbenchError('BACKFILL_PLAN') from None
    if expected!=plan:raise WorkbenchError('BACKFILL_PLAN_CHANGED')
    job_id=_identity(plan)
    from psycopg.types.json import Jsonb
    with postgres_session(dsn_env,application_name='commerceguard-backfill-plan') as conn:
        with conn.cursor() as c:
            key=_lock(c,job_id)
            try:
                with conn.transaction():
                    schema_guard(c)
                    c.execute('SELECT job_id FROM commerceguard.ops_backfill_job WHERE job_id=%s',(job_id,))
                    if c.fetchone():return {'job_id':job_id,'replayed':True}
                    c.execute('SELECT clock_timestamp()');now=c.fetchone()[0]
                    if any(timestamp(d['as_of'],artifact='backfill',field='as_of')>now for d in plan['days']):raise WorkbenchError('BACKFILL_FUTURE_DAY')
                runs=[]
                for d in plan['days']:
                    run=prepare_run(plan['merchant'],timestamp(d['as_of'],artifact='backfill',field='as_of'),mode=plan['mode'],
                        knowledge_at=timestamp(plan['knowledge_at'],artifact='backfill',field='knowledge_at') if plan['knowledge_at'] else None,
                        reason='late-data' if plan['mode']=='as-known-now' else 'recovery',baseline_run_id=d['baseline_run_id'],dsn_env=dsn_env)
                    runs.append((job_id,d['date'],run.run_id))
                with conn.transaction():
                    schema_guard(c)
                    c.execute('INSERT INTO commerceguard.ops_backfill_job(job_id,plan_json) VALUES(%s,%s)',(job_id,Jsonb(plan)))
                    c.executemany('INSERT INTO commerceguard.ops_backfill_item(job_id,business_date,run_id) VALUES(%s,%s,%s)',runs)
            finally:c.execute('SELECT pg_advisory_unlock(%s::bigint)',(key,))
    return {'job_id':job_id,'replayed':False}

def resume(job_id,*,limit=MAX_DAYS,dsn_env='COMMERCEGUARD_DATABASE_URL'):
    if type(limit) is not int or not 1<=limit<=MAX_DAYS:raise WorkbenchError('BACKFILL_LIMIT')
    completed=[];failure=None
    with postgres_session(dsn_env,application_name='commerceguard-backfill') as conn:
        with conn.cursor() as c:
            key=_lock(c,job_id)
            try:
                with conn.transaction():
                    schema_guard(c,write=False)
                    c.execute('SELECT plan_json FROM commerceguard.ops_backfill_job WHERE job_id=%s',(job_id,));row=c.fetchone()
                    if not row:raise WorkbenchError('BACKFILL_NOT_FOUND',404)
                    if row[0]['engine_sha256']!=engine_sha256():raise WorkbenchError('BACKFILL_ENGINE_CHANGED')
                    c.execute("SELECT business_date,run_id,attempts FROM commerceguard.ops_backfill_item WHERE job_id=%s AND state<>'published' ORDER BY business_date LIMIT %s",(job_id,limit));items=c.fetchall()
                for day,run_id,attempts in items:
                    if attempts>=100:raise WorkbenchError('BACKFILL_ATTEMPTS_EXHAUSTED')
                    try:result=execute_run(str(run_id),dsn_env=dsn_env);state='published';error=None;sha=result['result_sha256']
                    except Exception as ex:state='failed';error=getattr(ex,'code','BACKFILL_EXECUTION_UNCONFIRMED');sha=None
                    if error and (not isinstance(error,str) or not re.fullmatch('[A-Z][A-Z0-9_]{2,63}',error)):error='BACKFILL_EXECUTION_UNCONFIRMED'
                    with conn.transaction():
                        schema_guard(c)
                        c.execute('UPDATE commerceguard.ops_backfill_item SET state=%s,result_sha256=%s,error_code=%s,attempts=attempts+1 WHERE job_id=%s AND business_date=%s',(state,sha,error,job_id,day))
                    if error:failure={'date':day.isoformat(),'run_id':str(run_id),'code':error};break
                    completed.append({'date':day.isoformat(),'run_id':str(run_id),'result_sha256':sha})
                c.execute("SELECT count(*) FROM commerceguard.ops_backfill_item WHERE job_id=%s AND state<>'published'",(job_id,));remaining=c.fetchone()[0]
            finally:c.execute('SELECT pg_advisory_unlock(%s::bigint)',(key,))
    return {'job_id':job_id,'completed':completed,'failure':failure,'remaining':remaining}

def main():
    p=argparse.ArgumentParser(description='Я планирую/закрепляю/возобновляю bounded backfill; Case не продвигаю')
    sub=p.add_subparsers(dest='action',required=True)
    plan=sub.add_parser('plan');plan.add_argument('--merchant',required=True);plan.add_argument('--start',required=True);plan.add_argument('--end',required=True);plan.add_argument('--timezone',required=True)
    plan.add_argument('--mode',choices=['as-was','as-known-now'],default='as-was');plan.add_argument('--knowledge-at');plan.add_argument('--baselines',type=Path);plan.add_argument('--through')
    begin=sub.add_parser('start');begin.add_argument('--plan',type=Path,required=True)
    run=sub.add_parser('resume');run.add_argument('--job-id',required=True);run.add_argument('--limit',type=int,default=31)
    p.add_argument('--dsn-env',default='COMMERCEGUARD_DATABASE_URL');a=p.parse_args()
    try:
        if a.action=='plan':result=make_plan(a.merchant,a.start,a.end,a.timezone,mode=a.mode,knowledge_at=a.knowledge_at,baselines=json.loads(a.baselines.read_text()) if a.baselines else None,through=a.through)
        elif a.action=='start':result=start(json.loads(a.plan.read_text()),dsn_env=a.dsn_env)
        else:result=resume(a.job_id,limit=a.limit,dsn_env=a.dsn_env)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        if result.get('failure'):p.exit(2)
    except (ValueError,OSError,KeyError):p.exit(2,'Я не подтвердил backfill; проверяю план, границы и состояние БД.\n')
if __name__=='__main__':main()
