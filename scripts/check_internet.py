"""Я проверяю будущий HTTPS профиль на localhost с отдельной временной CA и честной TLS проверкой."""
import argparse
from hashlib import sha256
from html import unescape
from http.client import HTTPConnection,HTTPSConnection
import json
from pathlib import Path
import re
import socket
import ssl
import subprocess
import sys
import tempfile
from urllib.parse import urlencode
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from deploy.configure import configure
from deploy.manage import compose_command

def free_port():
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));return sock.getsockname()[1]

def verify(build=True):
    project='cg-https-'+uuid4().hex[:10];domain='commerceguard.test';origin='https://'+domain
    with tempfile.TemporaryDirectory(prefix='cg-https-') as tmp:
        work=Path(tmp);cfg=work/'settings';configure(cfg,domain=domain)
        base,env=compose_command(cfg/'.env',project)
        def run(command,*args):
            result=subprocess.run([*command,*args],cwd=ROOT,env=env,capture_output=True,text=True,timeout=600)
            if result.returncode:raise AssertionError('HTTPS compose action failed: '+args[0]+' '+result.stderr[-2000:])
            return result.stdout
        model=json.loads(run(base,'--profile','tools','config','--format','json'))
        assert sorted(int(p['published']) for p in model['services']['proxy']['ports'])==[80,443]
        assert all(not model['services'][name].get('ports') for name in ('db','web','init','tools'))
        assert {v['target'] for v in model['services']['proxy']['volumes']}=={'/data','/config'}
        # Я заменяю только issuer в временном fixture: рабочий Caddyfile остаётся ACME.
        testfile=work/'Caddyfile'
        testfile.write_text((ROOT/'deploy/Caddyfile.internet').read_text().replace('acme_ca https://acme-v02.api.letsencrypt.org/directory','local_certs\n    skip_install_trust'))
        http_port=https_port=free_port()
        while https_port==http_port:https_port=free_port()
        overlay=work/'test.yml'
        overlay.write_text('services:\n  proxy:\n    ports: !override\n      - "127.0.0.1:'+str(http_port)+':8080"\n      - "127.0.0.1:'+str(https_port)+':8443"\n    volumes:\n      - type: bind\n        source: '+str(testfile)+'\n        target: /etc/caddy/Caddyfile.internet\n        read_only: true\n')
        command=[*base,'-f',str(overlay)]
        cookie='';context=None
        class LocalTLS(HTTPSConnection):
            def connect(self):
                plain=socket.create_connection(('127.0.0.1',https_port),timeout=self.timeout)
                try:self.sock=self._context.wrap_socket(plain,server_hostname=self.host)
                except BaseException:plain.close();raise
        def request(path,method='GET',form=None,headers=None,tls=True,verify_context=None):
            connection=LocalTLS(domain,timeout=15,context=verify_context or context) if tls else HTTPConnection('127.0.0.1',http_port,timeout=15)
            hs={'Host':domain,'Cookie':cookie,**(headers or {})};body=None
            if form is not None:body=urlencode(form);hs.setdefault('Origin',origin);hs['Content-Type']='application/x-www-form-urlencoded'
            try:
                connection.request(method,path,body=body,headers=hs);r=connection.getresponse();return r.status,dict(r.getheaders()),r.read()
            finally:connection.close()
        def fields(raw,action):
            block=re.search(r'<form[^>]*action="'+re.escape(action)+r'"[^>]*>(.*?)</form>',raw.decode(),re.S)
            assert block
            return {n:unescape(v) for n,v in re.findall(r'<input[^>]*name="([^"]+)"[^>]*value="([^"]*)"',block[1])}
        try:
            if build:run(base,'build','web','proxy','tools')
            adapted=run(base,'run','--rm','--no-deps','proxy','caddy','adapt','--config','/etc/caddy/Caddyfile.internet','--adapter','caddyfile')
            assert 'letsencrypt.org/directory' in adapted and '"module":"internal"' not in adapted
            run(command,'up','-d','--wait','--wait-timeout','120')
            run(command,'run','--rm','tools','demo')
            root=work/'root.crt';run(command,'cp','proxy:/data/caddy/pki/authorities/local/root.crt',str(root))
            cert_hash=sha256(root.read_bytes()).hexdigest();context=ssl.create_default_context(cafile=str(root))
            assert context.check_hostname and context.verify_mode==ssl.CERT_REQUIRED
            try:request('/login',verify_context=ssl.create_default_context())
            except ssl.SSLCertVerificationError:pass
            else:raise AssertionError('untrusted CA unexpectedly accepted')
            status,headers,raw=request('/login',tls=False)
            assert status==308 and headers['Location']==origin+'/login'
            status,headers,raw=request('/login');assert status==200
            assert headers['Strict-Transport-Security']=='max-age=31536000'
            assert all(flag in headers['Set-Cookie'] for flag in ('Secure','HttpOnly','SameSite=Strict'))
            cookie=headers['Set-Cookie'].split(';')[0];form=fields(raw,'/login')
            form.update(username='manager',password=(cfg/'operator_password').read_text().strip())
            assert request('/login','POST',form,{'Origin':'https://other.test'})[0]==403
            status,headers,raw=request('/login','POST',form);assert status==303
            assert 'Secure' in headers['Set-Cookie'];cookie=headers['Set-Cookie'].split(';')[0]
            status,headers,raw=request('/?merchant=M01');assert status==200
            key=re.search(rb'/case/([a-f0-9]{64})',raw)[1].decode();path='/case/'+key
            raw=request(path)[2];comment=fields(raw,path+'/comment');comment['value']='Я проверяю HTTPS на временном стенде.'
            bad={**comment,'csrf':'invalid'}
            assert request(path+'/comment','POST',bad)[0]==403
            assert request(path+'/comment','POST',comment)[0]==303
            assert request('/readyz',headers={'Host':'other.test'})[0] in (403,421)
            assert request('/export?merchant=M01&currency=RUB&status=all')[0]==200
            run(command,'down');run(command,'up','-d','--wait','--wait-timeout','120')
            assert request(path)[0]==200
            run(command,'cp','proxy:/data/caddy/pki/authorities/local/root.crt',str(root))
            assert sha256(root.read_bytes()).hexdigest()==cert_hash
            return {'https_profile':True,'production_acme_config':True,'public_cert_issued':False,'tls_chain_and_hostname_verified':True,'untrusted_ca_rejected':True,'http_redirect':308,'hsts':True,'secure_cookies':True,'csrf_origin_host_rejection':True,'login_comment_export':True,'certificate_and_session_persist_after_recreate':True,'production_published_ports':[80,443],'test_bind':'127.0.0.1','host_trust_store_modified':False}
        finally:run(command,'down','--volumes','--remove-orphans')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--no-build',action='store_true');a=p.parse_args();print(json.dumps(verify(not a.no_build)))
