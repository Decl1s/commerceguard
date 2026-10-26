"""Я ловлю потерю покрытия, смысла валют и связь каталога с настоящим SQL."""
import copy
import unittest
from commerceguard.catalog import CatalogError, load_catalog, validate

class CatalogTests(unittest.TestCase):
    def test_complete(self): self.assertEqual(len(load_catalog()['entries']),9)
    def test_omitted_view(self):
        d=copy.deepcopy(load_catalog()); d['entries'].pop()
        with self.assertRaisesRegex(CatalogError,'COVERAGE'): validate(d)
    def test_currency_required(self):
        d=copy.deepcopy(load_catalog()); d['entries'][0]['currency_policy']=''
        with self.assertRaisesRegex(CatalogError,'MEANING'): validate(d)
    def test_false_lineage(self):
        d=copy.deepcopy(load_catalog()); d['entries'][0]['lineage']=['source:fake']
        with self.assertRaisesRegex(CatalogError,'LINEAGE'): validate(d)
    def test_unsafe_path(self):
        d=copy.deepcopy(load_catalog()); d['entries'][0]['path']='../outside.sql'
        with self.assertRaisesRegex(CatalogError,'PATH'): validate(d)
    def test_no_duplicate_identity(self):
        d=copy.deepcopy(load_catalog()); d['entries'].append(d['entries'][0])
        with self.assertRaisesRegex(CatalogError,'IDENTITY'): validate(d)
