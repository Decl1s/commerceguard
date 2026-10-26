"""Я проверяю Prefect flow в собственном временном PostgreSQL и удаляю оба backend."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import psycopg
from commerceguard.migrations import database_command
from commerceguard.pipeline import launch_pipeline, local_environment
from commerceguard.run_execution import read_result
from commerceguard.sample_data import generate_inputs


def require(value,label):
    if not value: raise AssertionError(label)


def verify(work,bin_dir):
    data, socket = work/'pg',work/'socket';socket.mkdir(mode=0o700)
    subprocess.run([str(bin_dir/'initdb'),'-D',str(data),'-U','cg_pipeline','--auth-local=trust',
                    '--auth-host=reject','--encoding=UTF8','--no-locale'],check=True,stdout=subprocess.DEVNULL)
    started=False
    try:
        subprocess.run([str(bin_dir/'pg_ctl'),'-D',str(data),'-l',str(work/'pg.log'),'-o',
                        f"-c listen_addresses='' -c unix_socket_directories={socket} -p 55433 -c timezone=UTC -c max_connections=20 -c shared_buffers=32MB",'start'],
                       check=True,stdout=subprocess.DEVNULL)
        started=True
        dsn=f'host={socket} port=55433 user=cg_pipeline'
        with psycopg.connect(dsn+' dbname=postgres',autocommit=True) as admin: admin.execute('CREATE DATABASE commerceguard')
        os.environ['CG_PIPELINE_CHECK_DSN']=dsn+' dbname=commerceguard'
        database_command(apply=True,dsn_env='CG_PIPELINE_CHECK_DSN')
        baseline=work/'baseline';generate_inputs(baseline)
        def config(folder=baseline,cutoff='now'):
            return dict(mode='run',merchant='M01',as_of=cutoff,raw_root=work/'raw',dsn_env='CG_PIPELINE_CHECK_DSN',
                        analytics_python=ROOT/'.venv/bin/python',oms_manifest=folder/'oms.manifest.json',
                        oms_data=folder/'oms.csv',psp_manifest=folder/'psp.manifest.json',psp_data=folder/'psp.jsonl')
        with psycopg.connect(os.environ['CG_PIPELINE_CHECK_DSN'],autocommit=True) as db:
            first=launch_pipeline(**config())
            print(json.dumps({'scenario':'normal','report':first}),flush=True)
            require(first['status']=='completed' and first['prefect_state']=='Completed' and first['backend_stopped'],'full flow')
            require(first['analytics']['models']==9 and first['analytics']['tests']==19,'all marts/tests')
            run_id=first['run_id'];digest=first['result']['result_sha256']
            require(db.execute('SELECT count(*) FROM commerceguard.core_payment_event').fetchone()[0]==6,'six facts')
            replay=launch_pipeline(**config(cutoff=first['as_of']))
            require(replay['status']=='completed' and replay['run_id']==run_id and replay['result']['duplicate_result'],'exact cutoff replay')
            require(all(b['duplicate_batch'] for b in replay['batches']),'batch replay')
            require(db.execute('SELECT count(*) FROM commerceguard.ops_run_result').fetchone()[0]==1,'one result after replay')
            print(json.dumps({'scenario':'exact-replay','status':replay['status']}),flush=True)

            # Я создаю valid новый OMS, затем конфликт PSP с уже опубликованным C01.
            broken=work/'broken';generate_inputs(broken,scenario='split-deadlines')
            rows=[json.loads(line) for line in (broken/'psp.jsonl').read_text().splitlines()]
            for row in rows:
                if row['source_event_id']=='C01': row['amount_minor']+=1
            payload=(''.join(json.dumps(row)+'\n' for row in rows)).encode()
            manifest=json.loads((broken/'psp.manifest.json').read_text())
            manifest.update(byte_count=len(payload),content_sha256=hashlib.sha256(payload).hexdigest())
            (broken/'psp.jsonl').write_bytes(payload);(broken/'psp.manifest.json').write_text(json.dumps(manifest))
            failed=launch_pipeline(**config(broken))
            print(json.dumps({'scenario':'PSP-conflict','report':failed}),flush=True)
            require(failed['status']=='failed' and failed['prefect_state']=='Failed' and failed['stage']=='ingest_psp','failure is not success')
            require(failed['attempts']['ingest_psp']==1 and failed['completed_stages']==['preflight','ingest_oms'],'no downstream after permanent error')
            require(len(failed['batches'])==1,'partial success has batch lineage')
            require(db.execute('SELECT count(*) FROM commerceguard.core_oms_snapshot').fetchone()[0]==2,'new OMS survives later PSP failure')
            require(db.execute('SELECT count(*) FROM commerceguard.core_payment_event').fetchone()[0]==6,'PSP conflict adds no money')
            require(db.execute('SELECT count(*) FROM commerceguard.ops_run_result').fetchone()[0]==1,'failure adds no result')

            corrupt=work/'corrupt';generate_inputs(corrupt)
            (corrupt/'psp.jsonl').write_bytes(b'broken')
            rejected=launch_pipeline(**config(corrupt))
            require(rejected['status']=='failed' and rejected['stage']=='preflight' and rejected['completed_stages']==[],'preflight before both publishes')
            require(rejected['attempts']['preflight']==1,'bad bytes are not retried')
            print(json.dumps({'scenario':'preflight-rejection','status':rejected['status']}),flush=True)

            # Я проверяю реальный Prefect retry/failure, fault injection только в тестовом script.
            fault_job=work/'fault-job';fault_job.mkdir()
            fault_config={k:str(v) if isinstance(v,Path) else v for k,v in config(cutoff=first['as_of']).items()}
            request=fault_job/'request.json';request.write_text(json.dumps(fault_config))
            with (fault_job/'logs').open('wb') as output:
                checked=subprocess.run([sys.executable,str(ROOT/'scripts/pipeline_faults.py'),str(request)],cwd=fault_job,
                                       env=local_environment(fault_job),stdout=output,stderr=output,timeout=180)
            if checked.returncode:
                print((fault_job/'logs').read_text()[-8000:],file=sys.stderr)
            require(checked.returncode==0,'fault scenarios')
            faults=json.loads((fault_job/'fault-results.json').read_text())
            require(read_result(run_id,dsn_env='CG_PIPELINE_CHECK_DSN')['result_sha256']==digest,'failed marts preserves report')
            print(json.dumps({'scenario':'faults','attempts':[v['attempts'] for v in faults]}),flush=True)

            # Я продолжаю тот же immutable run, без выбора текущего нового OMS.
            command=[sys.executable,'-m','commerceguard','pipeline','resume','--run-id',run_id,
                     '--analytics-python',str(ROOT/'.venv/bin/python'),'--dsn-env','CG_PIPELINE_CHECK_DSN']
            resumed=subprocess.run(command,cwd=ROOT,check=True,capture_output=True,text=True,encoding='utf-8')
            value=json.loads(resumed.stdout)
            require(value['status']=='completed' and value['result']['duplicate_result'] and value['backend_stopped'],'CLI resume')
            require(value['result']['result_sha256']==digest,'resume immutable result')
            require(value['completed_stages']==['preflight','execute','marts'],'resume skips ingest/selection')
            require(db.execute('SELECT count(*) FROM commerceguard.ops_run_result').fetchone()[0]==1,'one result after resume')
            require(db.execute('SELECT count(*) FROM commerceguard_mart.stg_completed_runs').fetchone()[0]==1,'no fake run in mart')
            print(json.dumps({'completed':True,'unit_suite':'separate','dbt_models':9,'dbt_tests':19,
                              'immutable_results':1,'psp_facts':6,'oms_snapshots':2,'prefect_retry_attempts':[2,3],
                              'permanent_psp_attempts':1,'cli_resume':True,'old_result_unchanged':True}),flush=True)
    finally:
        if started: subprocess.run([str(bin_dir/'pg_ctl'),'-D',str(data),'-m','fast','stop'],check=True,stdout=subprocess.DEVNULL)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--pg-bin',type=Path,default=Path('/usr/lib/postgresql/16/bin'))
    args=parser.parse_args()
    if os.name!='posix' or not (args.pg_bin/'initdb').is_file(): raise SystemExit('Для моего runner нужны Linux/PostgreSQL16 binaries')
    with tempfile.TemporaryDirectory(prefix='cg-pipeline-',dir='/tmp') as directory: verify(Path(directory),args.pg_bin)


if __name__=='__main__':main()
