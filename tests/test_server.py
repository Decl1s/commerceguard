"""Я проверяю явный origin и WSGI протокол без сети."""
import io
import unittest
from commerceguard.server import origin,Application
class ServerTests(unittest.TestCase):
    def test_external_http_denied(self):
        with self.assertRaises(ValueError):origin('http://example.test')
    def test_origin_path_denied(self):
        with self.assertRaises(ValueError):origin('https://example.test/path')
    def test_live_wsgi(self):
        app=Application('http://127.0.0.1:8765');out=[]
        result=app({'PATH_INFO':'/livez','REQUEST_METHOD':'GET','HTTP_HOST':'127.0.0.1:8765','wsgi.input':io.BytesIO()},lambda status,headers:out.append((status,headers)))
        self.assertEqual(out[0][0],'200 OK');self.assertIn(b'ok',b''.join(result))
        self.assertNotIn('Connection',dict(out[0][1]))
    def test_secure_login_cookie(self):
        app=Application('https://example.test');out=[]
        app({'PATH_INFO':'/login','REQUEST_METHOD':'GET','HTTP_HOST':'example.test','wsgi.input':io.BytesIO()},lambda status,headers:out.append((status,headers)))
        self.assertIn('Secure',dict(out[0][1])['Set-Cookie'])
