"""Я проверяю gross/refund/fee/net, неизвестность, версии и файловую границу."""

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from commerceguard.domain import EventKind, PaymentEvent
from commerceguard.file_contracts import FileInputError, json_object
from commerceguard.raw_store import RawStore
from commerceguard.settlement import evaluate
from commerceguard.settlement_contract import SettlementError, generate_advice, parse_advice


class Settlement(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        generate_advice(self.root / 'advice')
        self.base = json.loads((self.root / 'advice/matched.json').read_text(encoding='utf-8'))
        self.cutoff = datetime(2026, 10, 26, tzinfo=timezone.utc)
        at = datetime(2026, 10, 22, 10, tzinfo=timezone.utc)
        self.events = [PaymentEvent('M01', key, 'O1', 'RUB', kind, amount, at, at) for key, kind, amount in (
            ('C01', EventKind.CAPTURE, 10000), ('C02', EventKind.CAPTURE, 11000),
            ('C03', EventKind.CAPTURE, 15000), ('R03', EventKind.REFUND, 1000))]

    def advice(self, **changes):
        return parse_advice(json.dumps(dict(self.base, **changes)).encode())

    def test_matching_money_and_independent_tariff(self):
        result = evaluate(self.advice(), self.events, as_of=self.cutoff, fee_bps=200)
        self.assertEqual(result['state'], 'matched')
        self.assertEqual(result['expected'], dict(gross=36000, refund=1000, fee=720, net=34280))
        other = evaluate(self.advice(), self.events, as_of=self.cutoff, fee_bps=201)
        self.assertEqual(other['state'], 'discrepancy')
        self.assertEqual(other['expected']['fee'], 724)

    def test_fee_overcharge_is_not_distributed_to_orders(self):
        result = evaluate(self.advice(fee_minor=800, net_minor=34200), self.events,
                          as_of=self.cutoff, fee_bps=200)
        self.assertEqual(result['delta']['fee'], 80)
        self.assertEqual(result['delta']['net'], -80)
        self.assertEqual(result['discrepancies'], ['fee_mismatch', 'net_mismatch'])

    def test_incomplete_and_missing_are_unknown_not_zero(self):
        for advice, events, reason in (
            (self.advice(is_complete=False), self.events, 'advice_incomplete'),
            (self.advice(expected_event_count=5), self.events, 'membership_incomplete'),
            (self.advice(), self.events[:-1], 'event_missing'),
        ):
            with self.subTest(reason=reason):
                result = evaluate(advice, events, as_of=self.cutoff, fee_bps=200)
                self.assertEqual(result['state'], 'unknown')
                self.assertIn(reason, result['completeness']['reason_codes'])
                self.assertTrue(all(v is None for v in result['expected'].values()))
                self.assertTrue(all(v is None for v in result['delta'].values()))

    def test_complete_zero_and_incomplete_zero_are_different(self):
        empty = self.advice(event_ids=[], expected_event_count=0, gross_minor=0, refund_minor=0,
                            fee_minor=0, net_minor=0)
        self.assertEqual(evaluate(empty, [], as_of=self.cutoff, fee_bps=200)['state'], 'matched')
        incomplete = self.advice(event_ids=[], expected_event_count=0, is_complete=False,
                                 gross_minor=0, refund_minor=0, fee_minor=0, net_minor=0)
        self.assertEqual(evaluate(incomplete, [], as_of=self.cutoff, fee_bps=200)['state'], 'unknown')

    def test_batch_rounding_half_up_and_negative_net(self):
        event = self.events[0]
        small = PaymentEvent('M01', 'C01', 'O1', 'RUB', EventKind.CAPTURE, 25, event.occurred_at, event.observed_at)
        result = evaluate(self.advice(event_ids=['C01'], expected_event_count=1, gross_minor=25,
                                      refund_minor=0, fee_minor=1, net_minor=24), [small],
                          as_of=self.cutoff, fee_bps=200)
        self.assertEqual(result['state'], 'matched')
        negative = evaluate(self.advice(event_ids=['R03'], expected_event_count=1, gross_minor=0,
                                        refund_minor=1000, fee_minor=0, net_minor=-1000), [self.events[-1]],
                            as_of=self.cutoff, fee_bps=200)
        self.assertEqual(negative['state'], 'matched')

    def test_currency_and_half_open_period(self):
        first = self.events[0]
        for currency, moment, reason in (
            ('USD', first.occurred_at, 'event_currency_mismatch'),
            ('RUB', datetime(2026, 10, 23, tzinfo=timezone.utc), 'event_outside_period'),
        ):
            event = PaymentEvent('M01', 'C01', 'O1', currency, EventKind.CAPTURE, 10000, moment, moment)
            result = evaluate(self.advice(event_ids=['C01'], expected_event_count=1), [event],
                              as_of=self.cutoff, fee_bps=200)
            self.assertEqual(result['state'], 'unknown')
            self.assertIn(reason, result['completeness']['reason_codes'])

    def test_arithmetic_mismatch_is_explicit(self):
        result = evaluate(self.advice(net_minor=1), self.events, as_of=self.cutoff, fee_bps=200)
        self.assertFalse(result['reported_arithmetic_ok'])
        self.assertIn('reported_arithmetic_mismatch', result['discrepancies'])

    def test_canonical_identity_ignores_whitespace_and_member_order(self):
        left = self.advice()
        value = dict(self.base, event_ids=list(reversed(self.base['event_ids'])))
        right = parse_advice(json.dumps(value, indent=4).encode())
        self.assertEqual((left.advice_id, left.sha256), (right.advice_id, right.sha256))
        self.assertNotEqual(left.advice_id, self.advice(revision=2).advice_id)

    def test_bad_contracts_are_rejected(self):
        for changes in ({'fee_minor': True}, {'contract_version': True}, {'revision': 0},
                        {'expected_event_count': 0}, {'event_ids': ['C01', 'C01']},
                        {'period_end': self.base['period_start']}, {'currency': 'XYZ'},
                        {'observed_at': '2026-10-22T12:00:00Z'}, {'extra': 'ignored'}):
            with self.subTest(changes=list(changes)), self.assertRaises(SettlementError):
                self.advice(**changes)
        with self.assertRaises(SettlementError):
            parse_advice(b'{"contract_version":1,"contract_version":1}')

    def test_evidence_and_tariff_guards(self):
        with self.assertRaises(SettlementError):
            evaluate(self.advice(), self.events + self.events[:1], as_of=self.cutoff, fee_bps=200)
        for bps in (True, -1, 10001, 1.5):
            with self.subTest(bps=bps), self.assertRaises(SettlementError):
                evaluate(self.advice(), self.events, as_of=self.cutoff, fee_bps=bps)

    def test_batch_totals_allow_17_digits_without_relaxing_oms_psp(self):
        large = self.advice(gross_minor=10**16, refund_minor=10**16, fee_minor=10**16, net_minor=-2*10**16)
        self.assertEqual(large.value()['net_minor'], -2*10**16)
        with self.assertRaises(FileInputError):
            json_object('{"x":10000000000000000}', artifact='data')

    def test_standalone_raw_document_and_cli_inspect(self):
        path = self.root / 'advice/matched.json'
        raw = RawStore(self.root / 'raw')
        key = raw.persist_document(path.read_bytes())
        self.assertEqual(raw.persist_document(path.read_bytes()), key)
        self.assertEqual((self.root / 'raw' / key).read_bytes(), path.read_bytes())
        completed = subprocess.run([sys.executable, '-m', 'commerceguard', 'settlement', 'inspect',
                                    '--input', str(path)], check=True, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(json.loads(completed.stdout)['member_count'], 4)


if __name__ == '__main__':
    unittest.main()
