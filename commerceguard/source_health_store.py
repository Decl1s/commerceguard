"""Я читаю source health одним REPEATABLE READ snapshot, не меняя факты и отчёты."""

from datetime import datetime

from .domain import require_id
from .file_contracts import timestamp, canonical_time
from .ingest_journal import schema_guard
from .postgres import postgres_session
from .source_health import (SOURCES, SourceAttempt, SourceHealthError, SourcePackage, business_context,
                            evaluate_source, microseconds, threshold)

def _visible(merchant,source,cutoff):
    if source=='settlement':
        return ("SELECT advice_id::text,observed_at,published_at,member_count,is_complete,canonical_sha256,period_end,expected_event_count "
                "FROM commerceguard.core_settlement_advice WHERE merchant_id=%s AND published_at<=%s AND observed_at<=%s",(merchant,cutoff,cutoff))
    return ("SELECT batch_id::text,(manifest_json->>'observed_at')::timestamptz,published_at,declared_row_count,"
            "CASE WHEN source='oms' THEN (manifest_json->>'is_complete')::boolean END,content_sha256,"
            "CASE WHEN source='oms' THEN (manifest_json->>'effective_at')::timestamptz END,NULL::integer "
            "FROM commerceguard.ingest_batch WHERE merchant_id=%s AND source=%s AND state='published' AND published_at<=%s "
            "AND (manifest_json->>'observed_at')::timestamptz<=%s",(merchant,source,cutoff,cutoff))


def _packages(cursor,merchant,source,cutoff):
    sql,args=_visible(merchant,source,cutoff)
    cte='WITH visible(id,observed,published,items,complete,sha,business,expected) AS ('+sql+') '
    cursor.execute(cte+'SELECT count(*) FROM visible',args);count=cursor.fetchone()[0]
    # Я передаю pure evaluator только настоящие representative rows: latest, max observed и max business.
    # Их достаточно для всех полей health, а count считаю по всему snapshot в PostgreSQL.
    cursor.execute(cte+"(SELECT * FROM visible ORDER BY published DESC,id DESC LIMIT 1) UNION "
                   "(SELECT * FROM visible ORDER BY observed DESC,id DESC LIMIT 1) UNION "
                   "(SELECT * FROM visible WHERE business<=%s ORDER BY business DESC,id DESC LIMIT 1)",(*args,cutoff))
    return [SourcePackage(str(r[0]),source,*r[1:]) for r in cursor.fetchall()],count


def _attempts(cursor,merchant,source,cutoff):
    if source=='settlement':return []
    fields='attempt_id,batch_id,state,started_at,finished_at,error_code'
    base=' FROM commerceguard.ingest_attempt WHERE merchant_id=%s AND source=%s AND started_at<=%s'
    cursor.execute('(SELECT '+fields+base+' ORDER BY started_at DESC,attempt_id DESC LIMIT 1) UNION '
                   '(SELECT '+fields+base+" AND state IN ('published','duplicate') AND finished_at<=%s ORDER BY finished_at DESC,attempt_id DESC LIMIT 1)",
                   (merchant,source,cutoff,merchant,source,cutoff,cutoff))
    return [SourceAttempt(str(r[0]),str(r[1]),source,*r[2:]) for r in cursor.fetchall()]


def _events(cursor,merchant,packages,cutoff):
    if not packages:return None,None
    cursor.execute("SELECT max(e.occurred_at),max((extract(epoch FROM(r.observed_at-e.occurred_at))*1000000)::bigint) "
                   "FROM commerceguard.core_payment_receipt r JOIN commerceguard.core_payment_event e USING(merchant_id,source_event_id) "
                   "JOIN commerceguard.ingest_batch b ON b.batch_id=r.batch_id WHERE r.merchant_id=%s AND r.observed_at<=%s "
                   "AND e.occurred_at<=%s AND b.published_at<=%s AND b.state='published' AND b.source='psp' "
                   "AND (b.manifest_json->>'observed_at')::timestamptz<=%s",(merchant,cutoff,cutoff,cutoff,cutoff))
    return cursor.fetchone()


def source_health(merchant: str, *, as_of: str, business_timezone: str, max_age_seconds: int,
                  late_after_seconds: int, dsn_env: str = 'COMMERCEGUARD_DATABASE_URL') -> dict:
    require_id(merchant, 'merchant_id')
    threshold(max_age_seconds); threshold(late_after_seconds, allow_zero=True)
    explicit = None if as_of == 'now' else timestamp(as_of, artifact='source_health', field='as_of')
    # Я проверяю наличие timezone данных до обращения к БД.
    business_context(explicit or datetime.fromisoformat('2000-01-01T00:00:00+00:00'), business_timezone)
    with postgres_session(dsn_env, application_name='commerceguard-source-health') as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
                cursor.execute("SET LOCAL TIME ZONE 'UTC'")
                schema_guard(cursor, write=False)
                cursor.execute('SELECT clock_timestamp()')
                evaluated_at = cursor.fetchone()[0]
                cutoff = explicit or evaluated_at
                if cutoff > evaluated_at:
                    raise SourceHealthError('SOURCE_FUTURE_CUTOFF')
                rows = []
                for source in SOURCES:
                    packages,package_count = _packages(cursor, merchant, source, cutoff)
                    attempts = _attempts(cursor, merchant, source, cutoff)
                    event, event_lag = _events(cursor, merchant, packages, cutoff) if source == 'psp' else (None, None)
                    value = evaluate_source(source, packages, attempts, as_of=cutoff, max_age_seconds=max_age_seconds,
                                            late_after_seconds=late_after_seconds, event_watermark=event,
                                            max_event_lag_us=event_lag)
                    value['published_package_count']=package_count
                    if source == 'psp':
                        value['business_watermark'] = value['event_watermark']
                    rows.append(value)
    return {'action': 'source_health', 'view_version': 'source-health-v2', 'merchant_id': merchant,
            'as_of': canonical_time(cutoff), 'evaluated_at': canonical_time(evaluated_at),
            'business': business_context(cutoff, business_timezone), 'sources': rows,
            'visibility_version': 'published-at-marker-v1', 'database_actions': 'read_only',
            'limits': {'representative_packages_per_source': 3, 'representative_attempts_per_source': 2,
                       'aggregation': 'postgresql', 'statement_timeout_seconds': 30},
            'historical_snapshot_reconstructed': False}
