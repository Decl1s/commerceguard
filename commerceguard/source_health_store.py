"""Я читаю source health одним REPEATABLE READ snapshot, не меняя факты и отчёты."""

from datetime import datetime

from .domain import require_id
from .file_contracts import timestamp, canonical_time
from .ingest_journal import schema_guard
from .postgres import postgres_session
from .source_health import (SOURCES, SourceAttempt, SourceHealthError, SourcePackage, business_context,
                            evaluate_source, microseconds, threshold)

MAX_PACKAGES = 10000
MAX_ATTEMPTS = 10000
MAX_RECEIPTS = 50000


def _limited(rows: list, maximum: int) -> list:
    if len(rows) > maximum:
        raise SourceHealthError('SOURCE_HISTORY_LIMIT')
    return rows


def _packages(cursor, merchant: str, source: str, cutoff: datetime) -> list[SourcePackage]:
    if source == 'settlement':
        cursor.execute('SELECT advice_id,observed_at,published_at,member_count,is_complete,canonical_sha256,'
                       'period_end,expected_event_count FROM commerceguard.core_settlement_advice '
                       'WHERE merchant_id=%s AND published_at<=%s AND observed_at<=%s '
                       'ORDER BY published_at DESC,advice_id DESC LIMIT %s', (merchant, cutoff, cutoff, MAX_PACKAGES+1))
        rows = _limited(cursor.fetchall(), MAX_PACKAGES)
        return [SourcePackage(str(r[0]), source, *r[1:]) for r in rows]
    cursor.execute('SELECT batch_id,(manifest_json->>\'observed_at\')::timestamptz,published_at,'
                   'declared_row_count,CASE WHEN source=\'oms\' THEN (manifest_json->>\'is_complete\')::boolean END,'
                   'content_sha256,CASE WHEN source=\'oms\' THEN (manifest_json->>\'effective_at\')::timestamptz END '
                   'FROM commerceguard.ingest_batch WHERE merchant_id=%s AND source=%s '
                   'AND state=\'published\' AND published_at<=%s '
                   'AND (manifest_json->>\'observed_at\')::timestamptz<=%s '
                   'ORDER BY published_at DESC,batch_id DESC LIMIT %s',
                   (merchant, source, cutoff, cutoff, MAX_PACKAGES+1))
    return [SourcePackage(str(r[0]), source, *r[1:]) for r in _limited(cursor.fetchall(), MAX_PACKAGES)]


def _attempts(cursor, merchant: str, source: str, cutoff: datetime) -> list[SourceAttempt]:
    if source == 'settlement':
        return []
    cursor.execute('SELECT attempt_id,batch_id,state,started_at,finished_at,error_code '
                   'FROM commerceguard.ingest_attempt WHERE merchant_id=%s AND source=%s AND started_at<=%s '
                   'ORDER BY started_at DESC,attempt_id DESC LIMIT %s', (merchant, source, cutoff, MAX_ATTEMPTS+1))
    return [SourceAttempt(str(r[0]), str(r[1]), source, *r[2:])
            for r in _limited(cursor.fetchall(), MAX_ATTEMPTS)]


def _events(cursor, merchant: str, packages: list[SourcePackage], cutoff: datetime):
    if not packages:
        return None, None
    from uuid import UUID
    cursor.execute('SELECT e.occurred_at,r.observed_at FROM commerceguard.core_payment_receipt r '
                   'JOIN commerceguard.core_payment_event e USING(merchant_id,source_event_id) '
                   'WHERE r.merchant_id=%s AND r.batch_id=ANY(%s) AND r.observed_at<=%s AND e.occurred_at<=%s LIMIT %s',
                   (merchant, [UUID(p.package_id) for p in packages], cutoff, cutoff, MAX_RECEIPTS+1))
    rows = _limited(cursor.fetchall(), MAX_RECEIPTS)
    return (max((r[0] for r in rows), default=None),
            max((microseconds(r[1], r[0]) for r in rows), default=None))


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
                    packages = _packages(cursor, merchant, source, cutoff)
                    attempts = _attempts(cursor, merchant, source, cutoff)
                    event, event_lag = _events(cursor, merchant, packages, cutoff) if source == 'psp' else (None, None)
                    value = evaluate_source(source, packages, attempts, as_of=cutoff, max_age_seconds=max_age_seconds,
                                            late_after_seconds=late_after_seconds, event_watermark=event,
                                            max_event_lag_us=event_lag)
                    if source == 'psp':
                        value['business_watermark'] = value['event_watermark']
                    rows.append(value)
    return {'action': 'source_health', 'view_version': 'source-health-v1', 'merchant_id': merchant,
            'as_of': canonical_time(cutoff), 'evaluated_at': canonical_time(evaluated_at),
            'business': business_context(cutoff, business_timezone), 'sources': rows,
            'visibility_version': 'published-at-marker-v1', 'database_actions': 'read_only',
            'limits': {'packages_per_source': MAX_PACKAGES, 'attempts_per_source': MAX_ATTEMPTS,
                       'psp_receipts': MAX_RECEIPTS},
            'historical_snapshot_reconstructed': False}
