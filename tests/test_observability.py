"""Я ограничиваю поля событий и cardinality показателей."""
import unittest
from unittest.mock import patch
from commerceguard.observability import event,HttpStats
class ObservabilityTests(unittest.TestCase):
    def test_event_shape(self):
        with patch('commerceguard.observability._LOGGER.info'):
            d=event('http_request',request_id='00000000-0000-0000-0000-000000000001',status=503,duration_us=1)
        self.assertEqual(d['retry_policy'],'read_or_exact_request_only')
        self.assertNotIn('cookie',d)
    def test_forbidden_event(self):
        with self.assertRaises(ValueError):event('arbitrary payload')
    def test_counter(self):
        s=HttpStats();s.observe(200,123);s.observe(409,456)
        self.assertEqual(s.snapshot(),({'2xx':1,'4xx':1},579))
