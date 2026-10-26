"""Я сохраняю выписку и её расчёты append-only, с точным происхождением PSP."""

from datetime import datetime
import hashlib
import json
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from .domain import EventKind, PaymentEvent, utc
from .file_contracts import canonical_time, timestamp
from .ingestion import _locks
from .ingest_journal import schema_guard
from .postgres import postgres_session
from .raw_store import RawStore
from .settlement import FEE_POLICY, evaluate, require_fee_bps
from .settlement_contract import SettlementError, parse_advice, read_advice

MAX_RESULT_BYTES = 16777216


def _uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except (ValueError, TypeError, AttributeError):
        raise SettlementError('SETTLEMENT_ID_INVALID') from None


def engine_sha256() -> str:
    parts = []
    for name in ('domain.py', 'file_contracts.py', 'settlement_contract.py', 'settlement.py', 'settlement_store.py'):
        path = Path(__file__).with_name(name)
        if path.is_symlink() or not path.is_file():
            raise SettlementError('SETTLEMENT_ENGINE_SOURCE')
        data = path.read_bytes()
        if not data or len(data) > 256000:
            raise SettlementError('SETTLEMENT_ENGINE_SIZE')
        parts.append([name, hashlib.sha256(data).hexdigest()])
    return hashlib.sha256(json.dumps(parts, separators=(',', ':')).encode('ascii')).hexdigest()


def publish_advice(path: Path, raw_root: Path, *, dsn_env: str = 'COMMERCEGUARD_DATABASE_URL') -> dict:
    advice, data = read_advice(path)
    value = advice.value()
    raw_sha = hashlib.sha256(data).hexdigest()
    key = RawStore(raw_root).persist_document(data)
    identity = UUID(advice.advice_id)
    times = {field: timestamp(value[field], artifact='settlement', field=field)
             for field in ('period_start', 'period_end', 'observed_at')}
    with postgres_session(dsn_env, application_name='commerceguard-settlement-publish',
                          statement_timeout_ms=120000) as connection:
        from psycopg.types.json import Jsonb
        with connection.transaction():
            with connection.cursor() as cursor:
                _locks(cursor, value['merchant_id'])
                schema_guard(cursor)
                cursor.execute('SELECT advice_id, canonical_text, raw_sha256, raw_object_key '
                               'FROM commerceguard.core_settlement_advice '
                               'WHERE merchant_id=%s AND settlement_id=%s AND revision=%s',
                               (value['merchant_id'], value['settlement_id'], value['revision']))
                old = cursor.fetchone()
                if old:
                    if old[:2] != (identity, advice.text):
                        raise SettlementError('SETTLEMENT_REVISION_CONFLICT')
                    return {'action': 'settlement_publish', 'advice_id': str(identity), 'duplicate_advice': True,
                            'raw_sha256': old[2], 'raw_object_key': old[3]}
                cursor.execute('SELECT currency, period_start, period_end FROM commerceguard.core_settlement_advice '
                               'WHERE merchant_id=%s AND settlement_id=%s LIMIT 1',
                               (value['merchant_id'], value['settlement_id']))
                family = cursor.fetchone()
                if family and family != (value['currency'], times['period_start'], times['period_end']):
                    raise SettlementError('SETTLEMENT_BATCH_CONTEXT_CONFLICT')
                cursor.execute('SELECT 1 FROM commerceguard.core_settlement_event_assignment '
                               'WHERE merchant_id=%s AND source_event_id=ANY(%s) AND settlement_id<>%s LIMIT 1',
                               (value['merchant_id'], value['event_ids'], value['settlement_id']))
                if cursor.fetchone():
                    raise SettlementError('SETTLEMENT_EVENT_ALREADY_ASSIGNED')
                cursor.execute(
                    'INSERT INTO commerceguard.core_settlement_advice '
                    '(advice_id,merchant_id,settlement_id,revision,currency,period_start,period_end,observed_at,'
                    'is_complete,expected_event_count,member_count,canonical_sha256,canonical_text,canonical_json,'
                    'raw_sha256,raw_object_key) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                    (identity, value['merchant_id'], value['settlement_id'], value['revision'], value['currency'],
                     times['period_start'], times['period_end'], times['observed_at'], value['is_complete'],
                     value['expected_event_count'], len(value['event_ids']), advice.sha256, advice.text,
                     Jsonb(value), raw_sha, key))
                assignments = [(value['merchant_id'], e, value['settlement_id'], identity) for e in value['event_ids']]
                if assignments:
                    cursor.executemany('INSERT INTO commerceguard.core_settlement_event_assignment '
                                       '(merchant_id,source_event_id,settlement_id,first_advice_id) VALUES (%s,%s,%s,%s) '
                                       'ON CONFLICT (merchant_id,source_event_id) DO NOTHING', assignments)
                    cursor.executemany('INSERT INTO commerceguard.core_settlement_member '
                                       '(advice_id,merchant_id,settlement_id,source_event_id) VALUES (%s,%s,%s,%s)',
                                       [(identity, value['merchant_id'], value['settlement_id'], e) for e in value['event_ids']])
                cursor.execute('SELECT count(*) FROM commerceguard.core_settlement_member WHERE advice_id=%s', (identity,))
                if cursor.fetchone()[0] != len(value['event_ids']):
                    raise SettlementError('SETTLEMENT_MEMBERSHIP_COUNT')
    return {'action': 'settlement_publish', 'advice_id': str(identity), 'duplicate_advice': False,
            'raw_sha256': raw_sha, 'raw_object_key': key}


def _saved(cursor, identity: UUID) -> dict | None:
    cursor.execute('SELECT request_text,request_json,payload_text,payload_json,result_sha256,request_key '
                   'FROM commerceguard.ops_settlement_result WHERE report_id=%s', (identity,))
    row = cursor.fetchone()
    if not row:
        return None
    if (hashlib.sha256(row[0].encode('ascii')).hexdigest() != row[5] or json.loads(row[0]) != row[1]
            or uuid5(NAMESPACE_URL, 'commerceguard:settlement-result:v1:' + row[5]) != identity
            or hashlib.sha256(row[2].encode('ascii')).hexdigest() != row[4] or json.loads(row[2]) != row[3]):
        raise SettlementError('SETTLEMENT_RESULT_INTEGRITY')
    return {'action': 'settlement_result', 'report_id': str(identity), 'found': True,
            'request': row[1], 'result': row[3], 'result_sha256': row[4]}


def run_settlement(advice_id: str, as_of: datetime, fee_bps: int, *,
                   dsn_env: str = 'COMMERCEGUARD_DATABASE_URL') -> dict:
    identity, cutoff = _uuid(advice_id), utc(as_of, 'as_of')
    require_fee_bps(fee_bps)
    engine = engine_sha256()
    request = {'request_version': 1, 'advice_id': str(identity), 'as_of': canonical_time(cutoff),
               'fee_policy': {'version': FEE_POLICY, 'fee_bps': fee_bps},
               'visibility_version': 'published-receipt-v1', 'engine_sha256': engine}
    request_text = json.dumps(request, sort_keys=True, ensure_ascii=True, separators=(',', ':')) + '\n'
    request_key = hashlib.sha256(request_text.encode('ascii')).hexdigest()
    report_id = uuid5(NAMESPACE_URL, 'commerceguard:settlement-result:v1:' + request_key)
    with postgres_session(dsn_env, application_name='commerceguard-settlement-run',
                          statement_timeout_ms=120000) as connection:
        from psycopg.types.json import Jsonb
        with connection.transaction():
            with connection.cursor() as cursor:
                schema_guard(cursor)
                cursor.execute('SELECT merchant_id,canonical_text,observed_at,published_at,raw_sha256,raw_object_key '
                               'FROM commerceguard.core_settlement_advice WHERE advice_id=%s', (identity,))
                row = cursor.fetchone()
                if not row:
                    raise SettlementError('SETTLEMENT_ADVICE_NOT_FOUND')
                merchant, text, observed, published, raw_sha, raw_key = row
                _locks(cursor, merchant)
                cursor.execute('SELECT clock_timestamp()')
                if cutoff > cursor.fetchone()[0]:
                    raise SettlementError('SETTLEMENT_FUTURE_CUTOFF')
                if observed > cutoff or published > cutoff:
                    raise SettlementError('SETTLEMENT_ADVICE_NOT_VISIBLE')
                cached = _saved(cursor, report_id)
                if cached:
                    return {'action': 'settlement_run', 'report_id': str(report_id), 'duplicate_result': True,
                            'state': cached['result']['state'], 'result_sha256': cached['result_sha256']}
                advice = parse_advice(text.encode('ascii'))
                if advice.advice_id != str(identity):
                    raise SettlementError('SETTLEMENT_ADVICE_INTEGRITY')
                # Один видимый receipt на каждый явно перечисленный event; повтор доставки не множит сумму.
                cursor.execute(
                    'SELECT m.source_event_id,chosen.order_id,chosen.currency,chosen.kind,chosen.amount_minor,'
                    'chosen.occurred_at,chosen.observed_at,chosen.batch_id,chosen.raw_row_number,'
                    'chosen.record_sha256,chosen.raw_object_key FROM commerceguard.core_settlement_member m '
                    'LEFT JOIN LATERAL ('
                    ' SELECT e.order_id,e.currency,e.kind,e.amount_minor,e.occurred_at,r.observed_at,r.batch_id,'
                    'r.raw_row_number,raw.record_sha256,b.raw_object_key FROM commerceguard.core_payment_event e '
                    'JOIN commerceguard.core_payment_receipt r ON r.merchant_id=e.merchant_id '
                    'AND r.source_event_id=e.source_event_id '
                    'JOIN commerceguard.ingest_batch b ON b.batch_id=r.batch_id '
                    'JOIN commerceguard.ingest_raw_record raw ON raw.batch_id=r.batch_id AND raw.row_number=r.raw_row_number '
                    "WHERE e.merchant_id=m.merchant_id AND e.source_event_id=m.source_event_id AND b.state='published' "
                    'AND b.published_at<=%s AND r.observed_at<=%s AND e.occurred_at<=%s '
                    'ORDER BY r.observed_at,r.batch_id,r.raw_row_number LIMIT 1'
                    ') chosen ON true WHERE m.advice_id=%s ORDER BY m.source_event_id',
                    (cutoff, cutoff, cutoff, identity))
                rows = cursor.fetchall()
                if [r[0] for r in rows] != advice.value()['event_ids']:
                    raise SettlementError('SETTLEMENT_MEMBERSHIP_COUNT')
                events, evidence = [], []
                for record in rows:
                    if record[1] is None:
                        continue
                    events.append(PaymentEvent(merchant, record[0], record[1], record[2], EventKind(record[3]),
                                               record[4], record[5], record[6]))
                    evidence.append({'source_event_id': record[0], 'batch_id': str(record[7]),
                                     'raw_row_number': record[8], 'record_sha256': record[9],
                                     'raw_object_key': record[10], 'observed_at': canonical_time(record[6])})
                payload = evaluate(advice, events, as_of=cutoff, fee_bps=fee_bps)
                payload['advice_source'] = {'advice_id': str(identity), 'canonical_sha256': advice.sha256,
                                            'raw_sha256': raw_sha, 'raw_object_key': raw_key}
                payload['evidence'] = evidence
                payload_text = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(',', ':')) + '\n'
                if len(payload_text.encode('ascii')) > MAX_RESULT_BYTES:
                    raise SettlementError('SETTLEMENT_RESULT_SIZE')
                if engine_sha256() != engine:
                    raise SettlementError('SETTLEMENT_ENGINE_CHANGED')
                digest = hashlib.sha256(payload_text.encode('ascii')).hexdigest()
                cursor.execute('INSERT INTO commerceguard.ops_settlement_result '
                               '(report_id,advice_id,merchant_id,as_of,fee_bps,engine_sha256,request_key,request_text,'
                               'request_json,result_sha256,payload_text,payload_json,state) '
                               'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                               (report_id, identity, merchant, cutoff, fee_bps, engine, request_key, request_text,
                                Jsonb(request), digest, payload_text, Jsonb(payload), payload['state']))
    return {'action': 'settlement_run', 'report_id': str(report_id), 'duplicate_result': False,
            'state': payload['state'], 'result_sha256': digest}


def read_settlement(report_id: str, *, limit: int = 50, dsn_env: str = 'COMMERCEGUARD_DATABASE_URL') -> dict:
    identity = _uuid(report_id)
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise SettlementError('SETTLEMENT_VIEW_LIMIT')
    with postgres_session(dsn_env, application_name='commerceguard-settlement-result') as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute('SET TRANSACTION READ ONLY')
                schema_guard(cursor, write=False)
                value = _saved(cursor, identity)
    if value is None:
        return {'action': 'settlement_result', 'report_id': str(identity), 'found': False}
    payload = value['result']
    evidence = payload['evidence']
    payload['evidence_truncated'] = len(evidence) > limit
    payload['evidence'] = evidence[:limit]
    for field in ('missing_event_ids', 'currency_mismatch_ids', 'outside_period_ids'):
        members = payload['completeness'][field]
        payload['completeness'][field + '_count'] = len(members)
        payload['completeness'][field + '_truncated'] = len(members) > limit
        payload['completeness'][field] = members[:limit]
    return value
