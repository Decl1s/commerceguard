"""Я проверяю очередь на настоящих Case и HTTP на собственном loopback сервере."""
from http.client import HTTPConnection
from threading import Thread
import re
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from commerceguard.case_workflow import mutate,read_workflow
import psycopg
from urllib.parse import urlencode
from commerceguard.access import create_user,login,session,disable_user,authorize,logout
from commerceguard.workbench import Server
from commerceguard.workbench_store import queue, WorkbenchError

def verify_workbench(work,db,env_arg):
    row=db.execute('SELECT merchant_id,case_key,currency FROM commerceguard.ops_case ORDER BY case_key LIMIT 1').fetchone()
    assert row, 'published Case fixture required'
    merchant,key,currency=row
    before=db.execute('SELECT run_id,result_sha256 FROM commerceguard.ops_run_result ORDER BY run_id').fetchall()
    q=queue({'merchant':merchant,'limit':'1','presence':'all'},**env_arg)
    assert len(q['items'])==1 and q['context']
    filtered=queue({'merchant':merchant,'currency':currency,'presence':'all'},**env_arg)
    assert all(x['currency']==currency for x in filtered['items'])
    assert all(x['currency']==currency for x in filtered['counts_by_currency'])
    if q['next_after']:
        q2=queue({'merchant':merchant,'limit':'1','presence':'all','after':q['next_after'],'run_id':q['context']['run_id']},**env_arg)
        assert q2['items'][0]['case_key']>q['items'][0]['case_key']
    try:queue({'merchant':merchant,'run_id':'00000000-0000-0000-0000-000000000000'},**env_arg)
    except WorkbenchError as ex:assert ex.code=='QUEUE_HEAD_CHANGED'
    else:raise AssertionError('stale cursor must fail')
    assert not queue({'merchant':'empty_synthetic'},**env_arg)['items']
    password='synthetic-local-password'
    for name,role,scope in [('analyst_one','analyst',merchant),('manager_one','manager',merchant),('observer_one','observer',merchant),('engineer_one','engineer',merchant),('foreign_one','analyst','other_synthetic')]:
        create_user(name,password,role,[scope],**env_arg)
    token=login('analyst_one',password,**env_arg)
    identity=session(token,**env_arg)
    assert identity['role']=='analyst' and identity['merchants']==[merchant]
    stored=db.execute('SELECT token_hash FROM commerceguard.web_session WHERE username=%s',('analyst_one',)).fetchone()[0]
    assert stored!=token
    for name in ['observer_one','engineer_one']:
        denied_token=login(name,password,**env_arg);denied=session(denied_token,**env_arg)
        try:authorize(db.cursor(),denied_token,merchant=merchant,action='comment',csrf=denied['csrf'])
        except WorkbenchError as ex:assert ex.status==403
        else:raise AssertionError('role bypass')
    manager_token=login('manager_one',password,**env_arg);manager=session(manager_token,**env_arg)
    def perform(actor_token,actor_identity,action,value,request_id=None,expected=None):
        state=read_workflow(key,token=actor_token,**env_arg)
        return mutate(key,action=action,value=value,request_id=request_id or str(uuid4()),expected_version=state['version'] if expected is None else expected,
                      expected_revision=state['revision'],expected_run_id=state['run_id'],token=actor_token,csrf=actor_identity['csrf'],**env_arg)
    assignment=perform(token,identity,'assign','analyst_one')
    assert assignment['saved']['version']==1
    initial=read_workflow(key,token=token,**env_arg)
    rid=str(uuid4())
    kwargs=dict(action='comment',value='<script>synthetic</script>',request_id=rid,expected_version=initial['version'],expected_revision=initial['revision'],expected_run_id=initial['run_id'],token=token,csrf=identity['csrf'],**env_arg)
    a=mutate(key,**kwargs);b=mutate(key,**kwargs)
    assert not a['replayed'] and b['replayed'] and a['saved']==b['saved']
    try:mutate(key,**{**kwargs,'value':'different'})
    except WorkbenchError as ex:assert ex.code=='REQUEST_ID_REUSED'
    else:raise AssertionError('request reused with changed body')
    try:perform(manager_token,manager,'comment','stale',expected=0)
    except WorkbenchError as ex:assert ex.code=='CASE_VERSION_CONFLICT'
    else:raise AssertionError('lost update accepted')
    state=read_workflow(key,token=token,**env_arg);barrier=Barrier(2)
    def race(actor_token,actor):
        barrier.wait(timeout=5)
        try:return perform(actor_token,actor,'comment','concurrent synthetic',expected=state['version'])
        except WorkbenchError as ex:return ex.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        one=pool.submit(race,token,identity);two=pool.submit(race,manager_token,manager);out=[one.result(),two.result()]
    assert sum(isinstance(x,dict) for x in out)==1 and out.count('CASE_VERSION_CONFLICT')==1
    # Я вызываю реальную ошибку между UPDATE и INSERT audit, чтобы подтвердить rollback.
    unchanged=read_workflow(key,token=token,**env_arg)
    execute=psycopg.Cursor.execute
    def fail_audit(cursor,query,*args,**kw):
        if isinstance(query,str) and query.startswith('INSERT INTO commerceguard.ops_case_human_event'):raise RuntimeError('synthetic audit insert failure')
        return execute(cursor,query,*args,**kw)
    with patch.object(psycopg.Cursor,'execute',fail_audit):
        try:perform(token,identity,'comment','rollback synthetic')
        except RuntimeError:pass
        else:raise AssertionError('audit fault not reached')
    assert unchanged==read_workflow(key,token=token,**env_arg)
    try:db.execute('UPDATE commerceguard.ops_case SET workflow_version=workflow_version+1 WHERE case_key=%s',(key,))
    except psycopg.Error:pass
    else:raise AssertionError('unlogged workflow write accepted')
    assert unchanged==read_workflow(key,token=token,**env_arg)
    with Server(0,env_arg['dsn_env']) as server:
        thread=Thread(target=server.serve_forever,daemon=True);thread.start()
        def request(path,headers=None,method='GET',body=None):
            c=HTTPConnection('127.0.0.1',server.server_port,timeout=10)
            c.request(method,path,body=body,headers={'Cookie':'cg_session='+token,**(headers or {})})
            response=c.getresponse();raw=response.read();status=response.status;hs=dict(response.getheaders());c.close()
            return status,hs,raw
        try:
            for path in ['/?merchant='+merchant,'/case/'+key,'/case/'+key+'/evidence','/catalog','/health?merchant='+merchant]:
                status,headers,raw=request(path)
                assert status==200,(path,status,raw[:300])
                assert headers['Cache-Control']=='no-store' and 'frame-ancestors' in headers['Content-Security-Policy']
                assert b'raw_text' not in raw
            assert request('/',{'Host':'evil.invalid'})[0]==403
            assert request('/',{'Sec-Fetch-Site':'cross-site'})[0]==403
            assert request('/?merchant='+merchant+'&limit=999')[0]==400
            assert request('/',{'Cookie':''})[0]==401
            assert request('/?merchant=other_synthetic')[0]==403
            def post(path,form,headers=None):return request(path,{'Content-Type':'application/x-www-form-urlencoded','Origin':server.origin,**(headers or {})},'POST',urlencode(form))
            assert post('/logout',{'csrf':'wrong'})[0]==403
            assert post('/logout',{'csrf':identity['csrf']},{'Origin':'https://evil.invalid'})[0]==403
            code,hs,body=request('/login',{'Cookie':''});assert code==200
            challenge=hs['Set-Cookie'].split(';')[0]
            csrf=re.search(rb'name="csrf" value="([a-f0-9]+)"',body).group(1).decode()
            assert post('/login',{'username':'analyst_one','password':password,'csrf':csrf},{'Cookie':challenge})[0]==303
            assert post('/login',{'username':'analyst_one','password':password,'csrf':csrf},{'Cookie':challenge})[0]==403
            wf=read_workflow(key,token=token,**env_arg)
            form={'csrf':identity['csrf'],'request_id':str(uuid4()),'expected_version':str(wf['version']),'expected_revision':str(wf['revision']),'expected_run_id':wf['run_id'],'value':'HTTP synthetic comment'}
            assert post('/case/'+key+'/comment',form)[0]==303
            assert post('/case/'+key+'/comment',form)[0]==303
            assert post('/case/'+key+'/comment',{**form,'request_id':str(uuid4())})[0]==409
            assert post('/case/'+key+'/comment',{**form,'csrf':'ошибка'})[0]==403
            raw=request('/case/'+key)[2]
            assert b'<script>synthetic</script>' not in raw and b'&lt;script&gt;synthetic&lt;/script&gt;' in raw
            assert post('/logout',{'csrf':identity['csrf']})[0]==303
            assert request('/')[0]==401
        finally:server.shutdown();thread.join(timeout=5)
    disabled=login('foreign_one',password,**env_arg)
    disable_user('foreign_one',**env_arg)
    try:session(disabled,**env_arg)
    except WorkbenchError as ex:assert ex.status==401
    else:raise AssertionError('disabled session active')
    for _ in range(5):
        try:login('observer_one','wrong-password',**env_arg)
        except WorkbenchError:pass
    try:login('observer_one',password,**env_arg)
    except WorkbenchError as ex:assert ex.code=='LOGIN_FAILED'
    else:raise AssertionError('account throttle absent')
    assert before==db.execute('SELECT run_id,result_sha256 FROM commerceguard.ops_run_result ORDER BY run_id').fetchall()
    return {'queue_filters':True,'keyset_head_guard':True,'http_sessions_csrf_scope':True,'role_denial':True,'disable_revokes':True,'login_throttle':True,'financial_hashes_unchanged':True,'atomic_audit_rollback':True,'real_two_connection_conflict':True,'request_replay':True,'stored_xss_escaped':True}
