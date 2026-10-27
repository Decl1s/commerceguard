"""Я проверяю выбор сетевого профиля, валидацию домена и отсутствие ambient подмены."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from deploy.configure import configure,domain_name
from deploy.manage import compose_command

class DeploymentTests(unittest.TestCase):
    def test_local_default_and_secrets_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'settings';configure(root)
            command,env=compose_command(root/'.env')
            self.assertEqual(env['COMMERCEGUARD_ORIGIN'],'http://127.0.0.1:8765')
            self.assertEqual(command.count('-f'),1)
            secret=(root/'operator_password').read_bytes()
            self.assertNotIn(secret.strip().decode(),(root/'.env').read_text())
            with self.assertRaises(FileExistsError):configure(root,domain='shop.example.org')
            self.assertEqual(secret,(root/'operator_password').read_bytes())
    def test_internet_is_explicit_and_ambient_cannot_change_origin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'settings';configure(root,domain='Shop.Example.org')
            with patch.dict(os.environ,{'COMMERCEGUARD_ORIGIN':'http://bad.test','COMPOSE_FILE':'bad.yml'}):
                command,env=compose_command(root/'.env')
            self.assertEqual(env['COMMERCEGUARD_ORIGIN'],'https://shop.example.org')
            self.assertEqual(command.count('-f'),2);self.assertNotIn('COMPOSE_FILE',env)
    def test_domains_cannot_inject_caddy_or_urls(self):
        for value in ('localhost','127.0.0.1','*.example.org','https://example.org','example.org:443','example.org/path','a..org','a_bad.org','example.org\n{','example.org.','-a.example.org'):
            with self.subTest(value=value),self.assertRaises(ValueError):domain_name(value)
    def test_settings_conflicts_and_interpolation_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'settings';configure(root,domain='shop.example.org')
            path=root/'.env';good=path.read_text()
            for text in (good+'COMMERCEGUARD_MODE=local\n',good.replace('https://shop.example.org','http://shop.example.org'),good+'OTHER=${SECRET}\n'):
                path.write_text(text)
                with self.assertRaises(ValueError):compose_command(path)
    def test_old_local_settings_still_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'settings';configure(root);path=root/'.env'
            path.write_text(path.read_text().replace('COMMERCEGUARD_MODE=local\n',''))
            self.assertEqual(compose_command(path)[1]['COMMERCEGUARD_ORIGIN'],'http://127.0.0.1:8765')
