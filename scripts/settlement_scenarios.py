"""Я выполняю settlement сценарии только внутри одноразовой БД основного runner."""

from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import psycopg

from commerceguard.ingestion import publish_input
from commerceguard.settlement_contract import SettlementError, generate_advice
from commerceguard.settlement_store import publish_advice, read_settlement, run_settlement


def verify_settlements(work, db, raw, env_arg, now):
    def require(condition, label):
        if not condition:
            raise AssertionError(label)
    folder = work / 'settlement'
    generate_advice(folder)
    base = json.loads((folder / 'matched.json').read_text(encoding='utf-8'))
    def publish(value):
        path = folder / 'current.json'
        path.write_text(json.dumps(value), encoding='ascii')
        return publish_advice(path, raw, **env_arg)
    def run(advice_id, cutoff=None, bps=200):
        return run_settlement(advice_id, cutoff or now(), bps, **env_arg)
    first = publish(base)
    require(publish(base)['duplicate_advice'], 'settlement advice replay')
    require((raw / first['raw_object_key']).is_file(), 'advice raw persisted')
    cutoff = now()
    first_result = run(first['advice_id'], cutoff)
    require(first_result['state'] == 'matched', 'settlement matched')
    require(run(first['advice_id'], cutoff)['duplicate_result'], 'settlement result replay')
    full = read_settlement(first_result['report_id'], limit=1, **env_arg)
    require(full['result']['expected'] == dict(gross=36000, refund=1000, fee=720, net=34280), 'batch amounts')
    require(full['result']['evidence_truncated'] and len(full['result']['evidence']) == 1, 'bounded evidence')
    original_hash = full['result_sha256']
    other_tariff = run(first['advice_id'], cutoff, bps=201)
    require(other_tariff['report_id'] != first_result['report_id'] and other_tariff['state'] == 'discrepancy',
            'tariff belongs to request identity')

    incomplete = publish(dict(base, revision=2, is_complete=False, expected_event_count=5))
    require(run(incomplete['advice_id'])['state'] == 'unknown', 'incomplete advice unknown')
    bad_fee = publish(dict(base, revision=3, fee_minor=800, net_minor=34200))
    fee_result = run(bad_fee['advice_id'])
    fee_payload = read_settlement(fee_result['report_id'], **env_arg)['result']
    require(fee_result['state'] == 'discrepancy' and fee_payload['delta']['fee'] == 80, 'fee overcharge')
    membership = publish(dict(base, revision=4, expected_event_count=5))
    require(run(membership['advice_id'])['state'] == 'unknown', 'membership count unknown')

    # Я сначала сохраняю unknown, затем принимаю PSP fact и делаю новый cutoff.
    missing = publish(dict(base, revision=5, event_ids=base['event_ids']+['X-MISSING'], expected_event_count=5,
                           gross_minor=36100, fee_minor=722, net_minor=34378))
    missing_cutoff = now()
    unknown = run(missing['advice_id'], missing_cutoff)
    require(unknown['state'] == 'unknown', 'missing PSP fact is unknown')
    def psp(event_id, occurred, amount=100):
        path = work / ('settlement-psp-' + event_id)
        path.mkdir()
        value = json.loads((work / 'baseline/psp.jsonl').read_text(encoding='utf-8').splitlines()[0])
        value.update(source_event_id=event_id, amount_minor=amount, occurred_at=occurred,
                     observed_at='2026-10-25T12:00:00Z')
        data = (json.dumps(value) + '\n').encode()
        manifest = json.loads((work / 'baseline/psp.manifest.json').read_text(encoding='utf-8'))
        manifest.update(row_count=1, byte_count=len(data), content_sha256=hashlib.sha256(data).hexdigest(),
                        observed_at='2026-10-25T12:00:00Z')
        (path / 'psp.jsonl').write_bytes(data)
        (path / 'manifest.json').write_text(json.dumps(manifest), encoding='ascii')
        publish_input(path / 'manifest.json', path / 'psp.jsonl', raw, **env_arg)
    psp('X-MISSING', '2026-10-22T10:00:00Z')
    require(run(missing['advice_id'], missing_cutoff)['state'] == 'unknown', 'old unknown remains immutable')
    resolved = run(missing['advice_id'])
    require(resolved['state'] == 'matched', 'new cutoff observes late fact')
    require(read_settlement(unknown['report_id'], **env_arg)['result']['expected']['gross'] is None,
            'old unknown is not backfilled')

    wrong_currency = publish(dict(base, revision=6, expected_event_count=1, event_ids=['C05']))
    require(run(wrong_currency['advice_id'])['state'] == 'unknown', 'cross-currency never summed')
    psp('END', '2026-10-23T00:00:00Z')
    outside = publish(dict(base, revision=7, expected_event_count=1, event_ids=['END']))
    require(run(outside['advice_id'])['state'] == 'unknown', 'exclusive period end')
    zero = publish(dict(base, settlement_id='ZERO-RUB', expected_event_count=0, event_ids=[],
                        gross_minor=0, refund_minor=0, fee_minor=0, net_minor=0))
    require(run(zero['advice_id'])['state'] == 'matched', 'complete empty statement is known zero')
    negative = publish(dict(base, revision=8, expected_event_count=1, event_ids=['R03'],
                            gross_minor=0, refund_minor=1000, fee_minor=0, net_minor=-1000))
    require(run(negative['advice_id'])['state'] == 'matched', 'refund-only negative net')

    before = db.execute('SELECT count(*) FROM commerceguard.core_settlement_advice').fetchone()[0]
    for value, code in (
        (dict(base, fee_minor=1), 'SETTLEMENT_REVISION_CONFLICT'),
        (dict(base, settlement_id='OTHER-RUB'), 'SETTLEMENT_EVENT_ALREADY_ASSIGNED'),
        (dict(base, revision=9, currency='USD'), 'SETTLEMENT_BATCH_CONTEXT_CONFLICT'),
    ):
        try:
            publish(value)
        except SettlementError as error:
            require(str(error) == code, 'safe publication conflict')
        else:
            raise AssertionError(code)
    require(db.execute('SELECT count(*) FROM commerceguard.core_settlement_advice').fetchone()[0] == before,
            'conflict cannot partially publish advice')
    for table, column in (('core_settlement_advice', 'revision'), ('ops_settlement_result', 'fee_bps')):
        try:
            db.execute(f'UPDATE commerceguard.{table} SET {column}={column}')
        except psycopg.Error as error:
            require(error.sqlstate == '55000', 'immutable settlement rows')
        else:
            raise AssertionError('settlement UPDATE must fail')
    root = Path(__file__).resolve().parents[1]
    completed = subprocess.run([sys.executable, '-m', 'commerceguard', 'settlement', 'result',
                                '--report-id', first_result['report_id'], '--dsn-env', env_arg['dsn_env']],
                               cwd=root, check=True, capture_output=True, text=True, encoding='utf-8')
    require(json.loads(completed.stdout)['result']['state'] == 'matched', 'CLI result round trip')
    require(read_settlement(first_result['report_id'], **env_arg)['result_sha256'] == original_hash,
            'old report unchanged after revisions and late facts')
    return {'reports': db.execute('SELECT count(*) FROM commerceguard.ops_settlement_result').fetchone()[0],
            'advice_revisions': before, 'gross_minor': 36000, 'refund_minor': 1000,
            'fee_minor': 720, 'net_minor': 34280, 'fee_overcharge_minor': 80,
            'missing_report_id': unknown['report_id'], 'resolved_report_id': resolved['report_id'],
            'matched_report_id': first_result['report_id']}
