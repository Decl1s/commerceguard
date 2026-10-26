"""Я публикую ограниченные операционные показатели и безопасные JSON события."""
from collections import Counter
from datetime import datetime,timezone
import json
import logging
import re
import threading
from uuid import uuid4
from .access import authorize
from .ingest_journal import schema_guard
from .postgres import postgres_session
from .source_health_store import source_health

class HttpStats:
    def __init__(self):self.lock=threading.Lock();self.count=Counter();self.total_us=0
    def observe(self,status,duration_us):
        with self.lock:self.count[str(status//100)+'xx']+=1;self.total_us+=duration_us
    def snapshot(self):
        with self.lock:return dict(self.count),self.total_us

_LOGGER=logging.getLogger('commerceguard.events')
_LOGGER.propagate=False
_LOG_LOCK=threading.Lock()

def event(kind,*,request_id=None,status=None,duration_us=None,case_key=None):
    if kind not in {'http_request','startup','shutdown'}:raise ValueError('EVENT_KIND')
    payload={'event':kind,'at':datetime.now(timezone.utc).isoformat()}
    if request_id is not None:
        from uuid import UUID
        payload['request_id']=str(UUID(request_id))
    if status is not None:
        if type(status) is not int or not 100<=status<=599:raise ValueError('EVENT_STATUS')
        payload['status']=status;payload['retry_policy']='read_or_exact_request_only' if status==503 else 'wait' if status==429 else 'none'
    if duration_us is not None:
        if type(duration_us) is not int or duration_us<0:raise ValueError('EVENT_DURATION')
        payload['duration_us']=duration_us
    if case_key is not None and re.fullmatch('[a-f0-9]{64}',case_key):payload['case_key']=case_key
    with _LOG_LOCK:
        if not _LOGGER.handlers:
            handler=logging.StreamHandler();handler.setFormatter(logging.Formatter('%(message)s'));_LOGGER.addHandler(handler);_LOGGER.setLevel(logging.INFO)
    _LOGGER.info(json.dumps(payload,sort_keys=True,separators=(',',':')))
    return payload

def readiness(*,dsn_env='COMMERCEGUARD_DATABASE_URL'):
    try:
        with postgres_session(dsn_env,application_name='commerceguard-ready') as conn:
            with conn.transaction():
                with conn.cursor() as c:
                    c.execute('SET TRANSACTION READ ONLY');schema_guard(c,write=False)
        return True
    except Exception:return False

def metrics(merchant,*,token,stats,dsn_env='COMMERCEGUARD_DATABASE_URL'):
    with postgres_session(dsn_env,application_name='commerceguard-metrics') as conn:
        with conn.transaction():
            with conn.cursor() as c:
                schema_guard(c,write=False);authorize(c,token,merchant=merchant)
                c.execute('SELECT currency,finding_state,workflow_status,count(*) FROM commerceguard.ops_case WHERE merchant_id=%s GROUP BY 1,2,3 ORDER BY 1,2,3',(merchant,));cases=c.fetchall()
                c.execute('SELECT source,state,count(*) FROM commerceguard.ingest_attempt WHERE merchant_id=%s GROUP BY 1,2 ORDER BY 1,2',(merchant,));attempts=c.fetchall()
                c.execute('SELECT count(*) FROM commerceguard.ops_run_result WHERE merchant_id=%s',(merchant,));results=c.fetchone()[0]
    health=source_health(merchant,as_of='now',business_timezone='Europe/Moscow',max_age_seconds=86400,late_after_seconds=3600,dsn_env=dsn_env)
    # Я не использую IDs/actors/URL как labels: число series ограничено контрактом.
    lines=['# TYPE commerceguard_cases gauge']
    for currency,presence,status,count in cases:lines.append(f'commerceguard_cases{{currency="{currency}",presence="{presence}",status="{status}"}} {count}')
    lines+=['# TYPE commerceguard_ingest_attempts gauge']
    for source,state,count in attempts:lines.append(f'commerceguard_ingest_attempts{{source="{source}",state="{state}"}} {count}')
    lines+=['# TYPE commerceguard_saved_results gauge',f'commerceguard_saved_results {results}']
    lines+=['# TYPE commerceguard_source_stale gauge']
    for row in health['sources']:lines.append(f'commerceguard_source_stale{{source="{row["source"]}"}} {1 if row["freshness"]=="stale" else 0}')
    counts,total_us=stats.snapshot()
    lines+=['# TYPE commerceguard_http_requests_total counter']
    for status,count in sorted(counts.items()):lines.append(f'commerceguard_http_requests_total{{status_class="{status}"}} {count}')
    lines+=['# TYPE commerceguard_http_duration_seconds_total counter',f'commerceguard_http_duration_seconds_total {total_us/1000000:.6f}']
    return ('\n'.join(lines)+'\n').encode('ascii')
