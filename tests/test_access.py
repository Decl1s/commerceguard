"""Я проверяю пароль и session token без сохранения реального секрета."""
import unittest
from commerceguard.access import password_hash,verify_password,token_hash,username
from commerceguard.workbench_store import WorkbenchError

class AccessTests(unittest.TestCase):
    def test_salted_kdf(self):
        a=password_hash('synthetic-test-password');b=password_hash('synthetic-test-password')
        self.assertNotEqual(a,b);self.assertTrue(verify_password('synthetic-test-password',a));self.assertFalse(verify_password('wrong-password',a))
    def test_bad_hash(self):self.assertFalse(verify_password('password','plain text'))
    def test_password_bounds(self):
        for p in ['short','x'*257]:
            with self.assertRaises(WorkbenchError):password_hash(p)
    def test_token_shape(self):
        with self.assertRaises(WorkbenchError):token_hash('attacker')
        self.assertNotEqual(token_hash('a'*64),'a'*64)
    def test_account_name(self):
        with self.assertRaises(WorkbenchError):username('<script>')
