"""Я проверяю календарь, DST и явный контекст восстановления без подключения."""
from datetime import datetime
import unittest
from commerceguard.backfill import make_plan
from commerceguard.workbench_store import WorkbenchError
class BackfillTests(unittest.TestCase):
    def test_dst(self):
        p=make_plan('M01','2026-03-07','2026-03-09','America/New_York')
        times=[datetime.fromisoformat(x['as_of'].replace('Z','+00:00')) for x in p['days']]
        self.assertEqual((times[1]-times[0]).total_seconds(),23*3600)
    def test_bounds(self):
        with self.assertRaises(WorkbenchError):make_plan('M01','2026-01-01','2026-03-01','UTC')
    def test_correction_context(self):
        with self.assertRaises(WorkbenchError):make_plan('M01','2026-01-01','2026-01-01','UTC',mode='as-known-now')
    def test_partial_explicit(self):
        p=make_plan('M01','2026-01-01','2026-01-01','UTC',through='2026-01-01T12:00:00Z')
        self.assertTrue(p['days'][0]['partial'])
    def test_partial_wrong_day(self):
        with self.assertRaises(WorkbenchError):make_plan('M01','2026-01-01','2026-01-01','UTC',through='2026-01-02T12:00:00Z')
