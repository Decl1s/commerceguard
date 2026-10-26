"""Я проверяю эксплуатационные команды на собственной БД основного runner."""
from datetime import timezone
from unittest.mock import patch
from commerceguard.backfill import make_plan,start,resume
from commerceguard.file_contracts import canonical_time

def verify_operations(work,db,raw,env_arg,bin_dir):
    now=db.execute('SELECT clock_timestamp()').fetchone()[0]
    day=now.astimezone(timezone.utc).date().isoformat()
    plan=make_plan('M01',day,day,'UTC',through=canonical_time(now))
    job=start(plan,**env_arg)
    assert start(plan,**env_arg)['replayed']
    with patch('commerceguard.backfill.execute_run',side_effect=RuntimeError('synthetic stop')):
        failed=resume(job['job_id'],**env_arg)
    assert failed['failure'] and failed['remaining']==1
    fixed=db.execute('SELECT run_id FROM commerceguard.ops_backfill_item WHERE job_id=%s',(job['job_id'],)).fetchone()[0]
    completed=resume(job['job_id'],**env_arg)
    assert completed['remaining']==0 and str(fixed)==completed['completed'][0]['run_id']
    assert not resume(job['job_id'],**env_arg)['completed']
    from commerceguard.backup import create_backup,verify_backup,restore_backup,finish_restore
    from commerceguard.workbench_store import WorkbenchError
    import os,subprocess,psycopg
    bundle=work/'backup-bundle';backup=create_backup(raw,bundle,pg_bin=bin_dir,**env_arg)
    assert verify_backup(bundle)['version']==1
    original=(bundle/'database.dump').read_bytes()
    with (bundle/'database.dump').open('ab') as f:f.write(b'tamper')
    try:verify_backup(bundle)
    except WorkbenchError as ex:assert ex.code=='BACKUP_CHECKSUM'
    else:raise AssertionError('tampered backup accepted')
    (bundle/'database.dump').write_bytes(original)
    target=work/'restored-pg';socket=work/'restored-socket';socket.mkdir(mode=0o700)
    subprocess.run([str(bin_dir/'initdb'),'-D',str(target),'-U','cg_restore','--auth-local=trust','--auth-host=reject','--encoding=UTF8','--no-locale'],check=True,stdout=subprocess.DEVNULL)
    options=f"-c listen_addresses='' -c unix_socket_directories={socket} -p 55432 -c shared_buffers=32MB"
    subprocess.run([str(bin_dir/'pg_ctl'),'-D',str(target),'-l',str(work/'restored.log'),'-o',options,'start'],check=True,stdout=subprocess.DEVNULL)
    try:
        conninfo=f'host={socket} port=55432 user=cg_restore'
        with psycopg.connect(conninfo+' dbname=postgres',autocommit=True) as admin:admin.execute('CREATE DATABASE commerceguard')
        os.environ['CG_RESTORE_CHECK_DSN']=conninfo+' dbname=commerceguard'
        restored_raw=work/'restored-raw'
        # Я имитирую остановку после DB COMMIT, до публикации raw root.
        with patch('commerceguard.backup.finish_restore',side_effect=WorkbenchError('SYNTHETIC_STOP')):
            try:restore_backup(bundle,restored_raw,dsn_env='CG_RESTORE_CHECK_DSN',pg_bin=bin_dir)
            except WorkbenchError as ex:assert ex.code=='SYNTHETIC_STOP'
            else:raise AssertionError('restore stop not reached')
        recovered=finish_restore(bundle,restored_raw,dsn_env='CG_RESTORE_CHECK_DSN')
        assert recovered['restored']
        with psycopg.connect(os.environ['CG_RESTORE_CHECK_DSN'],autocommit=True) as restored:
            for table,cols in [('ops_run_result','run_id,result_sha256'),('ops_case','case_key,workflow_version,workflow_status,revision_number'),('ops_case_human_event','case_key,workflow_version,command_sha256')]:
                query='SELECT '+cols+' FROM commerceguard.'+table+' ORDER BY 1,2'
                assert db.execute(query).fetchall()==restored.execute(query).fetchall(),table
            assert restored.execute('SELECT count(*) FROM commerceguard.web_session').fetchone()[0]==0
            assert restored.execute('SELECT count(*) FROM commerceguard.ops_restore_receipt').fetchone()[0]==1
        try:restore_backup(bundle,work/'no-overwrite',dsn_env='CG_RESTORE_CHECK_DSN',pg_bin=bin_dir)
        except WorkbenchError as ex:assert ex.code=='RESTORE_EMPTY_DATABASE_REQUIRED'
        else:raise AssertionError('existing DB overwritten')
    finally:
        subprocess.run([str(bin_dir/'pg_ctl'),'-D',str(target),'-m','fast','stop'],check=True,stdout=subprocess.DEVNULL)
        os.environ.pop('CG_RESTORE_CHECK_DSN',None)
    return {'backup_restore_real':True,'tampering_rejected':True,'restore_commit_resume':True,'sessions_revoked':True,'backfill_fixed_ids':True,'failed_resume':True,'replayed':True}
