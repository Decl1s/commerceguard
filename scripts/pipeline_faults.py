"""Я инъецирую известный transient и сбой marts в настоящие Prefect tasks своей тестовой БД."""

import json
from pathlib import Path
import sys
from unittest.mock import patch

from commerceguard.pipeline import PipelineError
from commerceguard.pipeline_flow import commerce_flow
from prefect.server.api.server import SubprocessASGIServer
import commerceguard.pipeline_flow as module


def main():
    path = Path(sys.argv[1]); config = json.loads(path.read_text())
    saved_publish, saved_analytics = module.publish_step, module.analytics_step
    calls = 0
    def transient_once(source, config):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise PipelineError('ingest_oms','MERCHANT_BUSY',retryable=True)
        return saved_publish(source,config)
    def fail_marts(config, job, *, probe=False):
        if probe: return saved_analytics(config,job,probe=True)
        raise PipelineError('marts','INJECTED_MART_FAILURE')
    server = SubprocessASGIServer()
    results = []
    try:
        for index in (1,2):
            folder = path.parent / ('fault-'+str(index)); folder.mkdir()
            progress = dict(stage='preflight',completed_stages=[],attempts={})
            def always_busy(*args):
                raise PipelineError('ingest_oms','MERCHANT_BUSY',retryable=True)
            with patch.object(module,'publish_step',side_effect=transient_once if index==1 else always_busy), \
                 patch.object(module,'analytics_step',side_effect=fail_marts):
                state = commerce_flow(config,str(folder),progress,return_state=True)
            if not state.is_failed(): raise AssertionError('flow must fail')
            error = state.result(raise_on_failure=False)
            if not isinstance(error,PipelineError): raise AssertionError('fixed pipeline error')
            progress.update(prefect_state=state.name,error_code=error.code)
            results.append(progress)
        if results[0]['attempts']['ingest_oms']!=2: raise AssertionError('transient retried once')
        if results[0]['attempts']['marts']!=1: raise AssertionError('marts not retried')
        if results[0]['completed_stages']!=['preflight','ingest_oms','ingest_psp','cutoff','prepare','execute']:
            raise AssertionError('marts failure keeps only earlier successes')
        if results[1]['attempts']['ingest_oms']!=3 or results[1]['completed_stages']!=['preflight']:
            raise AssertionError('two retries exhausted without next steps')
    finally:
        server.stop()
    (path.parent/'fault-results.json').write_text(json.dumps(results))
    return 0


if __name__=='__main__': raise SystemExit(main())
