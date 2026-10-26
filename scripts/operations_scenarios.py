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
    return {'backfill_fixed_ids':True,'failed_resume':True,'replayed':True}
