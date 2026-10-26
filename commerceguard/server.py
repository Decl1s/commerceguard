"""Я запускаю WSGI приложение через Waitress с фиксированным origin и bounded ресурсами."""
import argparse
from email.message import Message
from http import HTTPStatus
import io
from importlib.metadata import version
import os
import signal
import threading
from types import SimpleNamespace
from urllib.parse import urlsplit
from .observability import HttpStats,event
from .workbench import Handler


def origin(value):
    try:u=urlsplit(value);port=u.port
    except ValueError:raise ValueError('SERVER_ORIGIN') from None
    if u.scheme not in ('http','https') or not u.hostname or u.username or u.password or u.path not in ('','/') or u.query or u.fragment or any(x in u.netloc for x in '\r\n, '):raise ValueError('SERVER_ORIGIN')
    if u.scheme=='http' and u.hostname not in ('127.0.0.1','localhost','::1'):raise ValueError('SERVER_HTTPS_REQUIRED')
    if port is not None and not 1<=port<=65535:raise ValueError('SERVER_PORT')
    return u.scheme+'://'+u.netloc

class Bridge(Handler):
    """Я использую проверенные handlers как адаптер запросов, без HTTP socket/parser stdlib."""
    def send_response(self,status,message=None):self.status=status
    def send_header(self,name,value):self.response_headers.append((name,value))
    def end_headers(self):pass

class Application:
    def __init__(self,public_origin,dsn_env='COMMERCEGUARD_DATABASE_URL'):
        self.config=SimpleNamespace(origin=origin(public_origin),dsn_env=dsn_env,stats=HttpStats(),
                                    challenges={},login_attempts=[],state_lock=threading.RLock(),secure_cookies=public_origin.startswith('https://'))
    def __call__(self,environ,start_response):
        h=Bridge.__new__(Bridge);h.server=self.config;h.response_headers=[];h.status=500
        h.headers=Message();h.path=environ.get('PATH_INFO','/')
        if environ.get('QUERY_STRING'):h.path+='?'+environ['QUERY_STRING']
        for key,value in environ.items():
            if key.startswith('HTTP_'):h.headers.add_header(key[5:].replace('_','-'),value)
        for key in ('CONTENT_LENGTH','CONTENT_TYPE'):
            if key in environ:h.headers.add_header(key.replace('_','-'),environ[key])
        h.rfile=environ['wsgi.input'];h.wfile=io.BytesIO()
        method=environ.get('REQUEST_METHOD','GET')
        if method=='GET':h.do_GET()
        elif method=='POST':h.do_POST()
        elif method=='HEAD':
            h.do_GET();h.wfile=io.BytesIO()
        else:h.send(405,'Метод не поддерживается','Я использую GET/POST/HEAD.',{'Allow':'GET, POST, HEAD'})
        # Waitress управляет соединением; hop-by-hop заголовки не входят в WSGI response.
        headers=[(k,v) for k,v in h.response_headers if k.lower() not in ('connection','transfer-encoding')]
        start_response(str(h.status)+' '+HTTPStatus(h.status).phrase,headers)
        return [h.wfile.getvalue()]

def create(public_origin,*,dsn_env='COMMERCEGUARD_DATABASE_URL',host='127.0.0.1',port=8765):
    if version('waitress')!='3.0.2':raise ValueError('WAITRESS_VERSION')
    if host not in ('127.0.0.1','0.0.0.0') or not 0<=port<=65535:raise ValueError('SERVER_LISTENER')
    checked=origin(public_origin)
    if host=='0.0.0.0' and checked.startswith('http://') and os.environ.get('COMMERCEGUARD_INTERNAL_NETWORK')!='1':raise ValueError('SERVER_INTERNAL_NETWORK_REQUIRED')
    from waitress import create_server
    return create_server(Application(checked,dsn_env),host=host,port=port,threads=4,connection_limit=64,
                         channel_timeout=30,cleanup_interval=5,max_request_header_size=16384,
                         max_request_body_size=32768,expose_tracebacks=False,clear_untrusted_proxy_headers=True)

def main():
    p=argparse.ArgumentParser(description='Рабочий WSGI server CommerceGuard')
    p.add_argument('--origin',default='http://127.0.0.1:8765');p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=8765);p.add_argument('--dsn-env',default='COMMERCEGUARD_DATABASE_URL');a=p.parse_args()
    server=None
    try:
        server=create(a.origin,dsn_env=a.dsn_env,host=a.host,port=a.port)
        signal.signal(signal.SIGTERM,lambda *_:server.close())
        event('startup');server.run()
    except KeyboardInterrupt:pass
    except (ValueError,OSError):p.exit(2,'Я не смог запустить WSGI server; проверяю версию, origin и listener.\n')
    finally:
        if server is not None:server.close();server.task_dispatcher.shutdown(timeout=30);event('shutdown')
if __name__=='__main__':main()
