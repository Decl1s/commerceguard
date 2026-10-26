"""Я читаю только смонтированные secrets нужной роли, не печатая DSN и пароли."""
from pathlib import Path
import os
import sys
from uuid import uuid4

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def database(owner=False):
    from psycopg.conninfo import make_conninfo
    name='owner_password' if owner else 'web_password'
    password=(Path('/run/secrets')/name).read_text().strip()
    if len(password)<32:raise ValueError('DEPLOY_SECRET')
    os.environ['COMMERCEGUARD_DATABASE_URL']=make_conninfo(host='db',port='5432',user='cg_owner' if owner else 'commerceguard_web',dbname='commerceguard',password=password)

def main():
    action=sys.argv[1] if len(sys.argv)>1 else 'web'
    if action=='health':
        from urllib.request import Request,urlopen
        from urllib.parse import urlsplit
        host=urlsplit(os.environ['COMMERCEGUARD_ORIGIN']).netloc
        with urlopen(Request('http://127.0.0.1:8080/readyz',headers={'Host':host}),timeout=4) as r:
            if r.status!=200:raise ValueError('NOT_READY')
        return
    database(owner=action!='web')
    if action=='init':
        from commerceguard.migrations import database_command
        from commerceguard.runtime_role import configure
        from commerceguard.access import create_user
        from commerceguard.workbench_store import WorkbenchError
        database_command(apply=True)
        configure(Path('/run/secrets/web_password').read_text().strip())
        try:create_user('manager',Path('/run/secrets/operator_password').read_text().strip(),'manager',[os.environ.get('COMMERCEGUARD_MERCHANT','M01')])
        except WorkbenchError as ex:
            if ex.code!='ACCOUNT_EXISTS':raise
        print('Я подготовил схему, runtime grants и первый manager; существующий пароль аккаунта не менял.')
    elif action=='web':
        from commerceguard.server import main as serve
        sys.argv=['commerceguard.server','--host','0.0.0.0','--port','8080','--origin',os.environ['COMMERCEGUARD_ORIGIN']];serve()
    elif action=='import-input':
        from dataclasses import asdict
        import json
        import tempfile
        from transfer import receive
        from commerceguard.ingestion import publish_input
        with tempfile.TemporaryDirectory(prefix='import-') as tmp:
            manifest,data=receive(sys.stdin.buffer,Path(tmp))
            result=publish_input(manifest,data,Path('/var/lib/commerceguard/raw'))
            print(json.dumps(asdict(result),ensure_ascii=False))
    elif action=='demo':
        from commerceguard.sample_data import generate_inputs
        from commerceguard.ingestion import publish_input
        from commerceguard.run_plans import prepare_run
        from commerceguard.run_execution import execute_run
        from commerceguard.case_store import apply_cases
        from commerceguard.postgres import postgres_session
        folder=Path('/var/lib/commerceguard/demo')/str(uuid4());generate_inputs(folder)
        for stem,ext in [('oms','.csv'),('psp','.jsonl')]:publish_input(folder/(stem+'.manifest.json'),folder/(stem+ext),Path('/var/lib/commerceguard/raw'))
        with postgres_session('COMMERCEGUARD_DATABASE_URL',application_name='commerceguard-demo') as db:now=db.execute('SELECT clock_timestamp()').fetchone()[0]
        run=prepare_run('M01',now);execute_run(run.run_id);apply_cases(run.run_id)
        print('Я подготовил синтетический M01; реальные файлы не использовал.')
    elif action=='pipeline-demo':
        if sys.executable!='/opt/orchestration/bin/python':os.execv('/opt/orchestration/bin/python',['/opt/orchestration/bin/python',__file__,*sys.argv[1:]])
        from commerceguard.sample_data import generate_inputs
        from commerceguard.pipeline import launch_pipeline
        folder=Path('/var/lib/commerceguard/demo')/str(uuid4());generate_inputs(folder)
        result=launch_pipeline(mode='run',merchant='M01',as_of='now',raw_root=Path('/var/lib/commerceguard/raw'),dsn_env='COMMERCEGUARD_DATABASE_URL',analytics_python=Path('/opt/analytics/bin/python'),oms_manifest=folder/'oms.manifest.json',oms_data=folder/'oms.csv',psp_manifest=folder/'psp.manifest.json',psp_data=folder/'psp.jsonl')
        if result['status']!='completed':raise ValueError('DEPLOY_PIPELINE_FAILED')
        print('Я выполнил Prefect ingest/reconcile/dbt; временный backend остановлен.')
    elif action=='cli':
        if len(sys.argv)>2 and sys.argv[2]=='pipeline' and sys.executable!='/opt/orchestration/bin/python':
            os.execv('/opt/orchestration/bin/python',['/opt/orchestration/bin/python',__file__,*sys.argv[1:]])
        from commerceguard.__main__ import main as cli
        sys.argv=['commerceguard',*sys.argv[2:]];cli()
    elif action=='account':
        from commerceguard.access import main as account
        sys.argv=['commerceguard.access',*sys.argv[2:]];account()
    elif action=='backup':
        from commerceguard.backup import main as backup
        sys.argv=['commerceguard.backup',*sys.argv[2:]];backup()
    else:raise ValueError('DEPLOY_ACTION')

if __name__=='__main__':
    try:main()
    except Exception as error:
        print("DEPLOY_FAILED:"+type(error).__name__,file=sys.stderr)
        print('Я не подтвердил действие поставки; проверяю readiness, secrets и версии локально.',file=sys.stderr);sys.exit(2)
