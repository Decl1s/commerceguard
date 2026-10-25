"""Я проверяю денежные инварианты, границы времени и недоверенные файлы."""

from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from commerceguard.case_projection import CaseError, finding_snapshots, transition
from commerceguard.demo import scenario
from commerceguard.domain import ContractError, EventKind, OrderExpectation, PaymentEvent
from commerceguard.file_contracts import FileInputError, json_object, semantic_sha256
from commerceguard.file_inputs import inspect_input, open_input, read_manifest
from commerceguard.raw_store import RawStore, RawStoreError
from commerceguard.reconcile import reconcile
from commerceguard.sample_data import generate_inputs


class Contracts(unittest.TestCase):
    def setUp(self):
        self.t = datetime(2026, 10, 24, 12, tzinfo=timezone.utc)
        self.order = OrderExpectation('M01', 'O1', 'RUB', 10000, 3000,
                                      self.t + timedelta(days=2), self.t, self.t + timedelta(days=2))
        self.events = (
            PaymentEvent('M01', 'C1', 'O1', 'RUB', EventKind.CAPTURE, 9000, self.t, self.t),
            PaymentEvent('M01', 'R1', 'O1', 'RUB', EventKind.REFUND, 1000, self.t, self.t),
        )

    def test_demo_business_outcome(self):
        result = scenario()
        self.assertEqual((len(result.balances), len(result.findings)), (5, 4))
        self.assertEqual(sorted(b.state for b in result.balances),
                         ['blocked', 'discrepancy', 'discrepancy', 'matched', 'pending'])
        self.assertEqual((result.unique_visible_events, result.duplicates_removed,
                          result.not_yet_visible_events), (6, 1, 1))

    def test_distinct_deadlines_and_exact_boundary(self):
        before = reconcile([self.order], self.events, as_of=self.t)
        self.assertEqual((before.balances[0].capture_state, before.balances[0].refund_state),
                         ('discrepancy', 'pending'))
        self.assertEqual([f.rule for f in before.findings], ['payment_shortfall'])
        after = reconcile([self.order], self.events, as_of=self.order.refund_deadline)
        self.assertEqual({f.rule for f in after.findings}, {'payment_shortfall', 'refund_missing'})

    def test_excess_waits_for_own_deadline(self):
        event = replace(self.events[0], amount_minor=12000)
        before = reconcile([self.order], [event], as_of=self.t - timedelta(seconds=1))
        self.assertFalse(before.findings)
        after = reconcile([self.order], [event], as_of=self.t)
        self.assertEqual([f.rule for f in after.findings], ['payment_excess'])

    def test_late_knowledge_does_not_change_business_cutoff(self):
        late = replace(self.events[0], observed_at=self.t + timedelta(days=1))
        original = reconcile([self.order], [late], as_of=self.t)
        correction = reconcile([self.order], [late], as_of=self.t, knowledge_at=late.observed_at)
        self.assertEqual(original.balances[0].actual_capture_minor, 0)
        self.assertEqual(correction.balances[0].actual_capture_minor, 9000)
        future = replace(late, occurred_at=late.observed_at)
        self.assertEqual(reconcile([self.order], [future], as_of=self.t,
                                  knowledge_at=late.observed_at).balances[0].actual_capture_minor, 0)

    def test_duplicates_and_conflicting_event_identity(self):
        result = reconcile([self.order], [self.events[0], self.events[0]], as_of=self.t)
        self.assertEqual(result.balances[0].actual_capture_minor, 9000)
        self.assertEqual(result.duplicates_removed, 1)
        with self.assertRaises(ContractError):
            reconcile([self.order], [self.events[0], replace(self.events[0], amount_minor=9001)], as_of=self.t)

    def test_currency_mismatch_preserves_unknown(self):
        result = reconcile([self.order], [replace(self.events[0], currency='USD')], as_of=self.t)
        self.assertEqual(result.balances[0].state, 'blocked')
        self.assertIsNone(result.balances[0].actual_capture_minor)
        self.assertIsNone(result.balances[0].refund_delta_minor)

    def test_domain_rejects_bool_naive_and_partial_deadlines(self):
        for changes in ({'capture_due_minor': True}, {'settle_after': datetime(2026, 10, 24)},
                        {'refund_due_at': None}):
            with self.subTest(changes=list(changes)), self.assertRaises(ContractError):
                replace(self.order, **changes)

    def test_legacy_semantic_identity_is_explicit(self):
        old = OrderExpectation('M01', 'O1', 'RUB', 10000, 3000, self.t)
        # Я закрепляю прежний framing независимо от новых полей dataclass.
        payload = ['oms:v1', 'M01', 'O1', 'RUB', 10000, 3000, '2026-10-24T12:00:00.000000Z']
        expected = hashlib.sha256(json.dumps(payload, ensure_ascii=True, separators=(',', ':')).encode()).hexdigest()
        self.assertEqual(semantic_sha256(old), expected)
        self.assertEqual(old.capture_deadline, old.refund_deadline)
        self.assertNotEqual(semantic_sha256(self.order), semantic_sha256(replace(
            self.order, refund_due_at=self.order.refund_due_at + timedelta(days=1),
            settle_after=self.order.settle_after + timedelta(days=1))))

    def test_finding_identity_and_transitions(self):
        # Я передаю форму сохранённого JSON, где evidence — list, не tuple dataclass.
        payload = json.loads(json.dumps({'findings': [asdict(f) for f in scenario().findings]}))
        snapshots = finding_snapshots(payload, 'M01')
        current = next(iter(snapshots.values()))
        self.assertEqual(transition(None, None, current), 'detected')
        self.assertIsNone(transition('present', current.sha256, current))
        self.assertEqual(transition('present', current.sha256, None), 'absent')
        self.assertEqual(transition('absent', None, current), 'reappeared')
        payload['findings'][0]['delta_minor'] = 123
        with self.assertRaises(CaseError):
            finding_snapshots(payload, 'M01')

    def test_all_generated_contracts_and_safe_rejections(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ('baseline', 'split-deadlines', 'invalid-json', 'conflict', 'earlier-observed'):
                folder = Path(tmp) / name
                generate_inputs(folder, scenario=name)
                inspect_input(folder / 'oms.manifest.json', folder / 'oms.csv')
                if name in ('invalid-json', 'conflict'):
                    with self.assertRaises(FileInputError):
                        inspect_input(folder / 'psp.manifest.json', folder / 'psp.jsonl')
                else:
                    inspect_input(folder / 'psp.manifest.json', folder / 'psp.jsonl')
                if name == 'split-deadlines':
                    self.assertEqual(len(list(folder.iterdir())), 9)
                    inspect_input(folder / 'oms-before.manifest.json', folder / 'oms-before.csv')

    def test_hash_mismatch_and_required_eof(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'input'
            generate_inputs(folder)
            with self.assertRaisesRegex(FileInputError, 'STREAM_INCOMPLETE'):
                with open_input(folder / 'oms.manifest.json', folder / 'oms.csv') as prepared:
                    with self.assertRaises(FileInputError):
                        prepared.summary()
            path = folder / 'oms.csv'
            path.write_bytes(path.read_bytes().replace(b'O1001', b'O9001'))
            with self.assertRaises(FileInputError) as error:
                inspect_input(folder / 'oms.manifest.json', path)
            self.assertEqual(error.exception.code, 'HASH_MISMATCH')

    def test_cli_json_serializes_deadlines(self):
        completed = subprocess.run([sys.executable, '-m', 'commerceguard', 'demo'],
                                   check=True, capture_output=True, text=True, encoding='utf-8')
        payload = json.loads(completed.stdout)
        self.assertEqual(payload['ruleset_version'], 'balance-v2')
        self.assertTrue(payload['balances'][0]['capture_due_at'].endswith('Z'))

    def test_raw_repeat_resolve_and_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'input'
            generate_inputs(folder)
            store = RawStore(Path(tmp) / 'raw')
            for _ in range(2):
                with open_input(folder / 'oms.manifest.json', folder / 'oms.csv', snapshot_sink=store.persist) as batch:
                    self.assertEqual(len(list(batch.records())), 5)
            identity = store.describe(read_manifest(folder / 'oms.manifest.json')).manifest_sha256
            _, _, data = store.resolve_manifest(identity, verify_data=False)
            self.assertEqual(data.read_bytes(), (folder / 'oms.csv').read_bytes())
            data.write_bytes(data.read_bytes().replace(b'O1001', b'O9001'))
            with self.assertRaisesRegex(RawStoreError, 'RAW_CORRUPT'):
                store.resolve_manifest(identity)

    def test_reject_duplicate_json_keys_and_non_integer_numbers(self):
        for value in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":1.25}'):
            with self.subTest(value=value), self.assertRaises(FileInputError):
                json_object(value, artifact='data')

    @unittest.skipUnless(sys.platform == 'linux', 'Я проверяю symlink contract на Linux')
    def test_input_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'input'
            generate_inputs(folder)
            link = Path(tmp) / 'link.csv'
            link.symlink_to(folder / 'oms.csv')
            with self.assertRaises(FileInputError) as error:
                inspect_input(folder / 'oms.manifest.json', link)
            self.assertEqual(error.exception.code, 'NOT_REGULAR_FILE')


if __name__ == '__main__':
    unittest.main()
