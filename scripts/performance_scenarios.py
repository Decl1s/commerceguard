"""Я измеряю настоящий план очереди на синтетических2000расхождениях, не подменяя optimizer."""
import csv
from datetime import datetime,timezone
import hashlib
import io
import json
from pathlib import Path
from commerceguard.file_contracts import FileManifest,OMS_V2_COLUMNS,canonical_manifest_bytes
from commerceguard.ingestion import publish_input
from commerceguard.run_plans import prepare_run
from commerceguard.run_execution import execute_run
from commerceguard.case_store import apply_cases


def verify_performance(work,db,raw,env_arg):
    folder=work/'performance';folder.mkdir()
    text=io.StringIO(newline='');writer=csv.writer(text,lineterminator='\n');writer.writerow(OMS_V2_COLUMNS)
    for n in range(2000):writer.writerow(['PERF1','P'+str(n).zfill(5),'RUB',100,0,'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z'])
    content=text.getvalue().encode();now=db.execute('SELECT clock_timestamp()').fetchone()[0]
    manifest=FileManifest(contract_version=2,source='oms',merchant_id='PERF1',content_sha256=hashlib.sha256(content).hexdigest(),row_count=2000,byte_count=len(content),observed_at=now,effective_at=now,is_complete=True)
    (folder/'oms.csv').write_bytes(content);(folder/'oms.manifest.json').write_bytes(canonical_manifest_bytes(manifest))
    publish_input(folder/'oms.manifest.json',folder/'oms.csv',raw,**env_arg)
    empty=FileManifest(contract_version=1,source='psp',merchant_id='PERF1',content_sha256=hashlib.sha256(b'').hexdigest(),row_count=0,byte_count=0,observed_at=now,effective_at=None,is_complete=None)
    (folder/'psp.jsonl').write_bytes(b'');(folder/'psp.manifest.json').write_bytes(canonical_manifest_bytes(empty))
    publish_input(folder/'psp.manifest.json',folder/'psp.jsonl',raw,**env_arg)
    run=prepare_run('PERF1',db.execute('SELECT clock_timestamp()').fetchone()[0],**env_arg);execute_run(run.run_id,**env_arg);apply_cases(run.run_id,**env_arg)
    db.execute('ANALYZE commerceguard.ops_case');db.execute('ANALYZE commerceguard.ops_case_application')
    cursor=db.execute("SELECT case_key FROM commerceguard.ops_case WHERE merchant_id='PERF1' ORDER BY case_key OFFSET 1000 LIMIT 1").fetchone()[0]
    query="SELECT c.case_key,c.order_id FROM commerceguard.ops_case c JOIN commerceguard.ops_case_application a ON a.run_id=c.first_run_id WHERE c.merchant_id=%s AND c.workflow_status='open' AND c.currency='RUB' AND c.finding_state='present' AND c.case_key>%s ORDER BY c.case_key LIMIT 50"
    plan=db.execute('EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) '+query,('PERF1',cursor)).fetchone()[0][0]
    nodes=[];indexes=[]
    def walk(node):
        nodes.append(node['Node Type'])
        if node.get('Index Name'):indexes.append(node['Index Name'])
        for child in node.get('Plans',[]):walk(child)
    walk(plan['Plan'])
    assert plan['Plan']['Actual Rows']==50
    # Я не требую определённого узла плана и не отключаю Seq Scan ради красивого результата.
    result={'synthetic_cases':2000,'page_rows':50,'node_types':nodes,'indexes':indexes,'planning_ms':plan['Planning Time'],'execution_ms':plan['Execution Time']}
    (work/'performance.json').write_text(json.dumps(result,indent=2))
    return result
