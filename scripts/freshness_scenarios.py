"""Я проверяю read model свежести только в собственном кластере основного runner."""

from datetime import timedelta
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from commerceguard.file_contracts import canonical_time
from commerceguard.file_inputs import read_manifest
from commerceguard.ingest_journal import Rejection, begin_attempt, record_rejection, PublicationFailure
from commerceguard.ingestion import publish_input
from commerceguard.raw_store import RawStore
from commerceguard.sample_data import generate_inputs
from commerceguard.settlement_contract import generate_advice
from commerceguard.settlement_store import publish_advice
from commerceguard.source_health import SourceHealthError
from commerceguard.source_health_store import source_health


def verify_source_health(work, db, raw, env_arg, now):
    def require(value, label):
        if not value: raise AssertionError(label)
    def report(cutoff='now', merchant='M01'):
        return source_health(merchant, as_of=cutoff, business_timezone='Europe/Moscow',
                             max_age_seconds=1, late_after_seconds=1, **env_arg)
    def indexed(value): return {r['source']:r for r in value['sources']}
    def counts():
        return tuple(db.execute('SELECT count(*) FROM commerceguard.'+name).fetchone()[0] for name in
                     ('ingest_batch','ingest_attempt','ops_run_result','core_payment_event','ops_settlement_result'))
    before=counts(); initial=indexed(report())
    require(counts()==before, 'source health is read only')
    require(initial['oms']['freshness']=='stale' and initial['psp']['freshness']=='stale','old data is stale')
    require(initial['psp']['completeness']=='unknown','PSP contract has no completeness')
    require(initial['psp']['late_events_observed'],'late PSP event observation')
    require(all(r['freshness']=='no_data' and r['volume']=='no_data' for r in report(merchant='MISSING')['sources']),
            'missing merchant is not zero')
    try:
        report(canonical_time(now()+timedelta(days=1)))
    except SourceHealthError as error: require(str(error)=='SOURCE_FUTURE_CUTOFF','future cutoff guard')
    else: raise AssertionError('future cutoff must fail')

    # Я сохраняю started, снимаю cutoff, затем пишу terminal diagnosis существующим journal API.
    baseline=work/'baseline'; manifest=read_manifest(baseline/'psp.manifest.json')
    artifacts=RawStore(raw).describe(manifest)
    from uuid import NAMESPACE_URL, uuid5
    batch_id=uuid5(NAMESPACE_URL,'commerceguard:batch:v1:'+artifacts.manifest_sha256)
    attempt=uuid4()
    begin_attempt(db,attempt,batch_id,manifest,artifacts)
    cutoff=canonical_time(now())
    require(record_rejection(attempt,Rejection('failed','infrastructure','DATABASE_UNCONFIRMED'),env_arg['dsn_env'])=='recorded',
            'terminal diagnosis recorded')
    historical=indexed(report(cutoff))['psp']
    require(historical['last_attempt']['attempt_id']==str(attempt) and
            historical['last_attempt']['state']=='started_at_boundary' and
            historical['last_attempt']['error_code'] is None,'future terminal hidden')
    failed=indexed(report())['psp']
    require(failed['last_attempt']['state']=='failed' and failed['last_successful_attempt'] is not None,
            'failed latest does not erase earlier success')
    require(failed['observed_watermark']==initial['psp']['observed_watermark'],'failure does not refresh watermark')
    require(publish_input(baseline/'psp.manifest.json',baseline/'psp.jsonl',raw,**env_arg).duplicate_batch,'PSP replay')
    replay=indexed(report())['psp']
    require(replay['last_attempt']['state']=='duplicate' and replay['freshness']=='stale','successful duplicate still stale')
    require(replay['observed_watermark']==failed['observed_watermark'],'duplicate does not advance observed')

    # Я публикую более старый observed OMS и проверяю latest delivery отдельно от watermark.
    empty=work/'health-empty';generate_inputs(empty)
    oms_data=(empty/'oms.csv').read_bytes().splitlines(keepends=True)[0]
    def replace_input(stem, data, **changes):
        path=empty/(stem+'.manifest.json'); value=json.loads(path.read_text())
        value.update(row_count=0,byte_count=len(data),content_sha256=hashlib.sha256(data).hexdigest(),**changes)
        path.write_text(json.dumps(value)); (empty/(stem+('.csv' if stem=='oms' else '.jsonl'))).write_bytes(data)
        return path
    oms_manifest=replace_input('oms',oms_data,effective_at='2026-10-22T12:00:00Z',observed_at='2026-10-22T13:00:00Z')
    empty_oms=publish_input(oms_manifest,empty/'oms.csv',raw,**env_arg)
    empty_view=indexed(report())['oms']
    require(empty_view['volume']=='complete_zero' and empty_view['latest_publication']['package_id']==empty_oms.batch_id,
            'explicit complete zero OMS')
    require(empty_view['observed_watermark']==initial['oms']['observed_watermark'] and empty_view['late_delivery'],
            'late backfill does not refresh observed watermark')
    historical_after=indexed(report(cutoff))['oms']
    require(historical_after['latest_publication']['package_id']!=empty_oms.batch_id,'later publication excluded by cutoff')
    psp_manifest=replace_input('psp',b'',observed_at='2026-10-26T00:00:00Z')
    publish_input(psp_manifest,empty/'psp.jsonl',raw,**env_arg)
    require(indexed(report())['psp']['volume']=='empty_unproven','empty PSP is not complete zero')

    # Incomplete OMS отвергается до begin_attempt, поэтому его отсутствие в журнале я не скрываю.
    prior=indexed(report())['oms']['last_attempt']['attempt_id']
    bad=json.loads(oms_manifest.read_text());bad['is_complete']=False
    bad_path=empty/'incomplete.manifest.json';bad_path.write_text(json.dumps(bad))
    try: publish_input(bad_path,empty/'oms.csv',raw,**env_arg)
    except PublicationFailure as error: require(error.journal_status=='not_registered','pre-registration failure boundary')
    else: raise AssertionError('incomplete OMS must fail')
    require(indexed(report())['oms']['last_attempt']['attempt_id']==prior,'no fabricated journal entry')

    folder=work/'health-advice';generate_advice(folder)
    base=json.loads((folder/'matched.json').read_text())
    base.update(settlement_id='HEALTH-RUB',period_start='2026-10-26T00:00:00Z',period_end='2026-10-26T02:00:00Z',
                observed_at='2026-10-26T03:00:00Z',expected_event_count=0,event_ids=[],gross_minor=0,refund_minor=0,
                fee_minor=0,net_minor=0,is_complete=False)
    advice_path=folder/'current.json'
    for revision,complete,expected,volume in ((1,False,0,'empty_unproven'),(2,True,1,'empty_unproven'),(3,True,0,'complete_zero')):
        base.update(revision=revision,is_complete=complete,expected_event_count=expected)
        advice_path.write_text(json.dumps(base));publish_advice(advice_path,raw,**env_arg)
        item=indexed(report())['settlement']
        require(item['volume']==volume,'settlement volume completeness')
        require(item['completeness']==('declared_complete' if revision==3 else 'incomplete'),'settlement completeness')
        require(item['last_attempt'] is None and not item['attempt_journal_supported'],'no invented settlement journal')

    before=counts(); report();require(counts()==before,'read does not update any attempt/report')
    completed=sys.executable
    command=[completed,'-m','commerceguard','source','health','--merchant','M01','--as-of','now',
             '--business-timezone','Europe/Moscow','--max-age-seconds','1','--late-after-seconds','1',
             '--dsn-env',env_arg['dsn_env']]
    result=subprocess.run(command,cwd=Path(__file__).resolve().parents[1],check=True,capture_output=True,text=True,encoding='utf-8')
    value=json.loads(result.stdout)
    require(value['database_actions']=='read_only' and len(value['sources'])==3,'health CLI round trip')
    require(value['business']['tzdata_version']=='2026.5','pinned timezone data in CLI')
    return {'sources':3,'readonly':True,'duplicate_stays_stale':True,'terminal_future_hidden':True,
            'oms_complete_zero':True,'psp_empty_unproven':True,'settlement_incomplete_checked':True,'cli':True}
