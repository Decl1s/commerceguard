"""Я проверяю spreadsheet injection и запрет подмены полного среза страницей."""
import unittest
from commerceguard.queue_export import safe_cell,export_queue
from commerceguard.workbench_store import WorkbenchError
class ExportTests(unittest.TestCase):
    def test_formulas(self):
        for v in ['=SUM(A1:A2)',' +1','-2','@cmd','\tvalue','\ufeff=1']:
            self.assertTrue(safe_cell(v).startswith("'"))
    def test_empty(self):self.assertEqual(safe_cell(None),'')
    def test_plain(self):self.assertEqual(safe_cell('O1001'),'O1001')
    def test_currency_required(self):
        with self.assertRaisesRegex(WorkbenchError,'CURRENCY_REQUIRED'):export_queue({'merchant':'M01'},token='')
    def test_page_rejected(self):
        with self.assertRaisesRegex(WorkbenchError,'NOT_A_PAGE'):export_queue({'merchant':'M01','limit':'1'},token='')
