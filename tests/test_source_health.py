"""Я проверяю временные границы, известный ноль и неизвестность отдельно от БД."""

from dataclasses import replace
from datetime import datetime, timedelta
import unittest
from unittest.mock import patch

from commerceguard.source_health import (SourceAttempt, SourceHealthError, SourcePackage, business_context,
                                        evaluate_source, threshold)
from commerceguard.source_health_store import _limited


def moment(text): return datetime.fromisoformat(text.replace('Z','+00:00'))
T=moment('2026-10-26T12:00:00Z')


class SourceHealth(unittest.TestCase):
    def package(self, source='oms', **kw):
        defaults=dict(package_id='P1',source=source,observed_at=T-timedelta(seconds=60),published_at=T,
                      item_count=5,declared_complete=True if source!='psp' else None,content_sha256='a'*64)
        defaults.update(kw);return SourcePackage(**defaults)

    def evaluate(self,packages=(),attempts=(),source='oms',**kw):
        args=dict(as_of=T,max_age_seconds=60,late_after_seconds=60);args.update(kw)
        return evaluate_source(source,list(packages),list(attempts),**args)

    def test_exact_threshold_and_one_microsecond_later(self):
        package=self.package()
        self.assertEqual(self.evaluate([package])['freshness'],'fresh')
        value=self.evaluate([package],as_of=T+timedelta(microseconds=1))
        self.assertEqual((value['freshness'],value['age_microseconds']),('stale',60000001))

    def test_no_data_is_not_complete_zero(self):
        self.assertEqual((self.evaluate()['freshness'],self.evaluate()['volume']),('no_data','no_data'))
        value=self.evaluate([self.package(item_count=0)])
        self.assertEqual((value['completeness'],value['volume']),('declared_complete','complete_zero'))

    def test_empty_psp_does_not_claim_complete(self):
        value=self.evaluate([self.package('psp',item_count=0)],source='psp')
        self.assertEqual((value['completeness'],value['volume']),('unknown','empty_unproven'))
        with self.assertRaises(SourceHealthError): self.package('psp',declared_complete=True)

    def test_incomplete_advice_and_missing_members(self):
        for package in (self.package('settlement',declared_complete=False),
                        self.package('settlement',expected_count=6)):
            value=self.evaluate([package],source='settlement')
            self.assertEqual(value['completeness'],'incomplete')
            self.assertFalse(value['attempt_journal_supported'])

    def test_backfill_does_not_advance_observed_watermark(self):
        first=self.package(published_at=T-timedelta(seconds=10))
        late=self.package(package_id='P2',observed_at=T-timedelta(days=2))
        value=self.evaluate([first,late])
        self.assertEqual(value['latest_publication']['package_id'],'P2')
        self.assertEqual(value['observed_watermark'],'2026-10-26T11:59:00.000000Z')
        self.assertTrue(value['late_delivery'])

    def test_successful_duplicate_does_not_refresh_source(self):
        attempt=SourceAttempt('A1','P1','oms','duplicate',T-timedelta(seconds=1),T)
        value=self.evaluate([self.package(observed_at=T-timedelta(days=1))],[attempt])
        self.assertEqual(value['freshness'],'stale')
        self.assertEqual(value['last_successful_attempt']['attempt_id'],'A1')

    def test_later_failure_does_not_erase_last_success(self):
        ok=SourceAttempt('A1','P1','oms','published',T-timedelta(seconds=20),T-timedelta(seconds=10))
        failed=SourceAttempt('A2','P2','oms','failed',T-timedelta(seconds=5),T,'DATABASE_UNCONFIRMED')
        value=self.evaluate([self.package()],[ok,failed])
        self.assertEqual(value['last_attempt']['state'],'failed')
        self.assertEqual(value['last_successful_attempt']['attempt_id'],'A1')

    def test_future_terminal_diagnosis_is_hidden(self):
        terminal=SourceAttempt('A1','P1','oms','failed',T-timedelta(seconds=1),T+timedelta(seconds=1),'RAW_UNAVAILABLE')
        value=self.evaluate(attempts=[terminal])['last_attempt']
        self.assertEqual(value['state'],'started_at_boundary')
        self.assertIsNone(value['error_code']);self.assertIsNone(value['finished_at'])

    def test_future_publication_or_observation_is_excluded(self):
        packages=[self.package(published_at=T+timedelta(microseconds=1)),
                  self.package(observed_at=T+timedelta(microseconds=1))]
        self.assertEqual(self.evaluate(packages)['published_package_count'],0)

    def test_published_before_observation_is_explicit_anomaly(self):
        value=self.evaluate([self.package(observed_at=T,published_at=T-timedelta(seconds=1))])
        self.assertTrue(value['publication_before_observed'])
        self.assertIsNone(value['delivery_lag_microseconds']);self.assertIsNone(value['late_delivery'])

    def test_event_lag_is_independent_from_delivery_freshness(self):
        value=self.evaluate([self.package('psp')],source='psp',event_watermark=T-timedelta(days=1),
                            max_event_lag_us=86400000000)
        self.assertEqual(value['freshness'],'fresh');self.assertTrue(value['late_events_observed'])
        with self.assertRaises(SourceHealthError):
            self.evaluate(source='psp',event_watermark=T+timedelta(seconds=1))

    def test_business_date_uses_explicit_pinned_timezone(self):
        context=business_context(moment('2026-10-26T21:30:00Z'),'Europe/Moscow')
        self.assertEqual((context['business_date'],context['tzdata_version']),('2026-10-27','2026.5'))
        self.assertTrue(context['as_of_local'].endswith('+03:00'))

    def test_fall_back_fold_is_preserved_without_naive_local_parsing(self):
        first=business_context(moment('2026-11-01T05:30:00Z'),'America/New_York')
        second=business_context(moment('2026-11-01T06:30:00Z'),'America/New_York')
        self.assertEqual((first['fold'],second['fold']),(0,1))
        self.assertNotEqual(first['as_of_local'],second['as_of_local'])

    def test_threshold_timezone_and_history_guards(self):
        for value in (True,0,-1,1.5,2678401):
            with self.assertRaises(SourceHealthError):threshold(value)
        self.assertEqual(threshold(0,allow_zero=True),0)
        for key in ('../UTC','/etc/passwd','Europe//Moscow','Missing/Zone'):
            with self.assertRaises(SourceHealthError):business_context(T,key)
        with patch('commerceguard.source_health.version',return_value='wrong'):
            with self.assertRaisesRegex(SourceHealthError,'SOURCE_TZDATA_VERSION'):business_context(T,'UTC')
        with self.assertRaisesRegex(SourceHealthError,'SOURCE_HISTORY_LIMIT'):_limited([1,2],1)

    def test_wrong_source_and_invalid_attempt_diagnosis_are_rejected(self):
        with self.assertRaises(SourceHealthError):self.evaluate([self.package('psp')])
        with self.assertRaises(SourceHealthError):
            SourceAttempt('A1','P1','oms','failed',T,T,'unsafe private message')
