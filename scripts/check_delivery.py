"""Я проверяю настоящую Compose поставку в отдельном project и удаляю только его ресурсы."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from http.client import HTTPConnection
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import tempfile
import time
from urllib.parse import urlencode
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]

def verify(*,build=True,browser_check=None):
    project='cg-check-'+uuid4().hex[:10]
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix='cg-delivery-') as tmp:
        cfg=Path(tmp)/'settings'
        spec=importlib.util.spec_from_file_location('configure',ROOT/'deploy/configure.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        import sys
        sys.path.insert(0,str(ROOT));module.configure(cfg,port)
        command=['docker','compose','--project-name',project,'--env-file',str(cfg/'.env'),'-f',str(ROOT/'deploy/compose.yml')]
        env={k:v for k,v in os.environ.items() if not k.startswith('COMPOSE_')}
        def compose(*args,capture=False):
            result=subprocess.run([*command,*args],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=600)
            if result.returncode:
                print(result.stderr[-4000:])
                diagnostic=subprocess.run([*command,'logs','--no-color','--tail','30'],cwd=ROOT,env=env,capture_output=True,text=True)
                print(diagnostic.stdout[-6000:]);raise AssertionError('compose action failed: '+args[0])
            return result.stdout
        host_client=False
        cookie='';origin='http://127.0.0.1:'+str(port)
        def request(path,method='GET',form=None,headers=None):
            nonlocal host_client
            hs={'Cookie':cookie,**(headers or {})};body=None
            if form is not None:body=urlencode(form);hs.update({'Content-Type':'application/x-www-form-urlencoded','Origin':origin})
            if not host_client:
                try:
                    conn=HTTPConnection('127.0.0.1',port,timeout=20)
                    conn.request(method,path,body=body,headers=hs);response=conn.getresponse();raw=response.read();status=response.status;out=dict(response.getheaders());conn.close();return status,out,raw
                except ConnectionRefusedError:host_client=True
            # Я учитываю Docker-outside-of-Docker: loopback daemon host отличается от loopback runner.
            client="import json,sys,base64;from http.client import HTTPConnection;p=json.load(sys.stdin);c=HTTPConnection('127.0.0.1',p['port'],timeout=20);c.request(p['method'],p['path'],body=p['body'],headers=p['headers']);r=c.getresponse();print(json.dumps([r.status,dict(r.getheaders()),base64.b64encode(r.read()).decode()]))"
            result=subprocess.run(['docker','run','--rm','-i','--network','host','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges:true','--entrypoint','python','commerceguard:local','-c',client],input=json.dumps({'port':port,'method':method,'path':path,'body':body,'headers':hs}),capture_output=True,text=True,timeout=40)
            if result.returncode:raise AssertionError('host-network HTTP probe failed: '+result.stderr[-300:])
            status,out,encoded=json.loads(result.stdout);return status,out,base64.b64decode(encoded)
        def fields(raw,action):
            block=re.search(r'<form[^>]*action="'+re.escape(action)+r'"[^>]*>(.*?)</form>',raw.decode(),re.S)
            assert block, 'form missing'
            return {name:unescape(value) for name,value in re.findall(r'<input[^>]*name="([^"]+)"[^>]*value="([^"]*)"',block.group(1))}
        def wait_ready():
            for _ in range(60):
                try:
                    if request('/readyz')[0]==200:return
                except OSError:pass
                time.sleep(.5)
            raise AssertionError('delivery readiness timeout')
        try:
            compose('up','-d',*(['--build'] if build else []),'--wait','--wait-timeout','120')
            assert request('/readyz')[0]==200 and request('/')[0]==401
            compose('run','--rm','--build','tools','demo')
            assert 'Prefect' in compose('run','--rm','tools','pipeline-demo')
            # Я передаю ровно два синтетических файла с хоста; повтор не добавляет факты.
            from commerceguard.sample_data import generate_inputs
            inputs=Path(tmp)/'host-input';generate_inputs(inputs)
            host_command=[sys.executable,str(ROOT/'deploy/import_input.py'),'--settings',str(cfg/'.env'),'--project',project,'--manifest',str(inputs/'psp.manifest.json'),'--data',str(inputs/'psp.jsonl')]
            for _ in range(2):
                imported=subprocess.run(host_command,capture_output=True,text=True,timeout=120,env=env)
                assert imported.returncode==0,imported.stderr[-300:]
                assert json.loads(imported.stdout.strip().splitlines()[-1])['duplicate_batch']

            backup='/var/lib/commerceguard/backups/delivery-check'
            compose('run','--rm','tools','backup','create','--raw-root','/var/lib/commerceguard/raw','--bundle',backup)
            assert 'verified' in compose('run','--rm','tools','backup','verify','--bundle',backup)
            status,headers,raw=request('/login');assert status==200
            challenge=headers['Set-Cookie'].split(';')[0];form=fields(raw,'/login')
            form.update(username='manager',password=(cfg/'operator_password').read_text().strip())
            status,headers,raw=request('/login','POST',form,{'Cookie':challenge});assert status==303,(status,raw[:100])
            cookie=headers['Set-Cookie'].split(';')[0]
            status,headers,raw=request('/?merchant=M01');assert status==200,(status,raw[:300])
            key=re.search(rb'/case/([a-f0-9]{64})',raw).group(1).decode();path='/case/'+key
            status,headers,raw=request(path);assert status==200
            form=fields(raw,path+'/comment');form['value']='Я проверяю поставку <script>текст</script>.'
            assert request(path+'/comment','POST',form)[0]==303
            raw=request(path)[2];assert b'&lt;script&gt;' in raw
            close=fields(raw,path+'/close');close.update(value='Я принял синтетическую разницу.',reason_code='accepted_difference')
            assert request(path+'/close','POST',close)[0]==303
            assert request(path+'/close','POST',close)[0]==303
            reopen=fields(request(path)[2],path+'/reopen');reopen.update(value='Я проверяю повторное открытие.',reason_code='new_evidence')
            assert request(path+'/reopen','POST',reopen)[0]==303
            assert request('/export?merchant=M01&currency=RUB&status=all')[0]==200
            # Я проверяю реальный SQL отказ runtime роли, а не скрытую кнопку UI.
            probe="import sys;sys.path.insert(0,'/app/deploy');import entrypoint;entrypoint.database();import psycopg,os;db=psycopg.connect(os.environ['COMMERCEGUARD_DATABASE_URL']);denied=False\ntry:db.execute('DELETE FROM commerceguard.core_payment_event WHERE false')\nexcept psycopg.errors.InsufficientPrivilege:denied=True\nassert denied;print('runtime mutation denied')"
            assert 'runtime mutation denied' in compose('exec','-T','web','python','-c',probe)
            browser_result=browser_check(origin,(cfg/'operator_password').read_text().strip()) if browser_check else None
            begin=time.monotonic()
            with ThreadPoolExecutor(max_workers=4) as pool:statuses=list(pool.map(lambda _:request('/?merchant=M01')[0],range(40)))
            elapsed=time.monotonic()-begin
            assert statuses==[200]*40
            compose('restart','web');wait_ready();assert request(path)[0]==200
            compose('down')
            compose('up','-d','--wait','--wait-timeout','120');wait_ready()
            assert request(path)[0]==200 and b'&lt;script&gt;' in request(path)[2]
            return {'browser':browser_result,'compose':True,'container_prefect_dbt':True,'container_backup_tools':True,'host_file_import_replay':True,'waitress':'3.0.2','runtime_sql_denial':True,'normal_comment_close_reopen_export':True,
                    'session_restart_persistence':True,'volume_restart_persistence':True,'requests':40,'concurrency':4,'seconds':round(elapsed,3),'client_container_overhead':host_client}
        finally:
            compose('down','--volumes','--remove-orphans')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--no-build',action='store_true');a=p.parse_args()
    print(json.dumps(verify(build=not a.no_build),ensure_ascii=False))
