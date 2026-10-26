"""Я сверяю batch gross/refund и отдельно заданный тариф, без распределения fee на заказы."""

from datetime import datetime

from .domain import EventKind, PaymentEvent, utc
from .file_contracts import canonical_time, timestamp
from .settlement_contract import Advice, SettlementError

FEE_POLICY = 'gross-bps-half-up-v1'


def require_fee_bps(value: int) -> None:
    if type(value) is not int or not 0 <= value <= 10000:
        raise SettlementError('SETTLEMENT_FEE_BPS')


def evaluate(advice: Advice, events: list[PaymentEvent], *, as_of: datetime, fee_bps: int) -> dict:
    require_fee_bps(fee_bps)
    cutoff = utc(as_of, 'as_of')
    value = advice.value()
    start = timestamp(value['period_start'], artifact='settlement', field='period_start')
    end = timestamp(value['period_end'], artifact='settlement', field='period_end')
    members = set(value['event_ids'])
    seen = {}
    for event in events:
        if (event.merchant_id != value['merchant_id'] or event.source_event_id not in members
                or event.source_event_id in seen or event.occurred_at > cutoff or event.observed_at > cutoff):
            raise SettlementError('SETTLEMENT_EVIDENCE_CONTEXT')
        seen[event.source_event_id] = event
    missing = sorted(members - seen.keys())
    currencies = sorted(k for k, e in seen.items() if e.currency != value['currency'])
    outside = sorted(k for k, e in seen.items() if not start <= e.occurred_at < end)
    reasons = []
    for condition, code in (
        (cutoff < end, 'period_open'), (not value['is_complete'], 'advice_incomplete'),
        (len(members) != value['expected_event_count'], 'membership_incomplete'),
        (bool(missing), 'event_missing'), (bool(currencies), 'event_currency_mismatch'),
        (bool(outside), 'event_outside_period'),
    ):
        if condition:
            reasons.append(code)
    reported = {field: value[field + '_minor'] for field in ('gross', 'refund', 'fee', 'net')}
    arithmetic = reported['net'] == reported['gross'] - reported['refund'] - reported['fee']
    expected = dict.fromkeys(reported)
    delta = dict.fromkeys(reported)
    discrepancies = []
    if not reasons:
        gross = sum(e.amount_minor for e in seen.values() if e.kind == EventKind.CAPTURE)
        refund = sum(e.amount_minor for e in seen.values() if e.kind == EventKind.REFUND)
        # Я округляю один раз на уровне batch: половину minor unit — вверх.
        fee = (gross * fee_bps + 5000) // 10000
        expected = dict(gross=gross, refund=refund, fee=fee, net=gross - refund - fee)
        delta = {field: reported[field] - expected[field] for field in reported}
        discrepancies = [field + '_mismatch' for field in reported if delta[field] != 0]
        if not arithmetic:
            discrepancies.append('reported_arithmetic_mismatch')
    return {'result_version': 1, 'state': 'unknown' if reasons else 'discrepancy' if discrepancies else 'matched',
            'merchant_id': value['merchant_id'], 'settlement_id': value['settlement_id'],
            'revision': value['revision'], 'currency': value['currency'],
            'period_start': value['period_start'], 'period_end': value['period_end'],
            'as_of': canonical_time(cutoff), 'fee_policy': {'version': FEE_POLICY, 'fee_bps': fee_bps},
            'completeness': {'advice_complete': value['is_complete'], 'expected_event_count': value['expected_event_count'],
                             'member_count': len(members), 'visible_event_count': len(seen),
                             'missing_event_ids': missing, 'currency_mismatch_ids': currencies,
                             'outside_period_ids': outside, 'reason_codes': reasons},
            'reported': reported, 'expected': expected, 'delta': delta,
            'reported_arithmetic_ok': arithmetic, 'discrepancies': discrepancies}
