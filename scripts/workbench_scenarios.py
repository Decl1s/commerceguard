"""Я проверяю очередь на настоящих Case и HTTP на собственном loopback сервере."""
from http.client import HTTPConnection
from threading import Thread
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
    with Server(0,env_arg['dsn_env']) as server:
        thread=Thread(target=server.serve_forever,daemon=True);thread.start()
        def request(path,headers=None,method='GET',body=None):
            c=HTTPConnection('127.0.0.1',server.server_port,timeout=10)
            c.request(method,path,body=body,headers=headers or {})
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
            assert request('/',method='POST',body='')[0]==405
        finally:server.shutdown();thread.join(timeout=5)
    assert before==db.execute('SELECT run_id,result_sha256 FROM commerceguard.ops_run_result ORDER BY run_id').fetchall()
    return {'queue_filters':True,'keyset_head_guard':True,'http_read_only':True,'financial_hashes_unchanged':True}
