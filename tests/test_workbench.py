"""Я проверяю недоверенные фильтры, безопасный вывод и origin без запуска сервера."""
import unittest
from commerceguard.workbench import params, page, queue_html
from commerceguard.workbench_store import filters, WorkbenchError

class WorkbenchTests(unittest.TestCase):
    def test_money_currency(self):
        with self.assertRaises(ValueError):filters({'merchant':'demo','currency':'XXX'})
    def test_unknown(self):
        with self.assertRaises(WorkbenchError):filters({'merchant':'demo','sql':'drop'})
    def test_cursor_bound_to_run(self):
        with self.assertRaisesRegex(WorkbenchError,'CURSOR_RUN'):filters({'merchant':'demo','after':'a'*64})
    def test_limit_and_age(self):
        for extra in [{'limit':'101'},{'age_min_days':'5','age_max_days':'2'},{'limit':'true'}]:
            with self.assertRaises(WorkbenchError):filters({'merchant':'demo',**extra})
    def test_duplicate_query(self):
        with self.assertRaises(WorkbenchError):params('merchant=a&merchant=b')
    def test_html_escaped(self):
        self.assertNotIn(b'<script>',page('<script>','safe'))
        d={'context':None,'evaluated_at':'now','counts_by_currency':[],'items':[],'next_after':None,'merchant':'demo'}
        html=queue_html(d,{'merchant':'"><script>alert(1)</script>'})
        self.assertNotIn('<script>',html);self.assertIn('карточек нет',html)
