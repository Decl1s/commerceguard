"""Я связываю существующие сервисы последовательными Prefect tasks, не меняя формулы."""

from pathlib import Path
from prefect import flow, task
from prefect.cache_policies import NO_CACHE
from prefect.runtime import task_run

from .pipeline import PipelineError, analytics_step, choose_cutoff, execute_step, freeze_packages, prepare_step, publish_step


def retry_known_transient(task, task_run, state) -> bool:
    error = state.result(raise_on_failure=False)
    return isinstance(error, PipelineError) and error.retryable


@task(name='commerceguard-step', retries=2, retry_delay_seconds=[1, 3],
      retry_condition_fn=retry_known_transient, cache_policy=NO_CACHE, persist_result=False, log_prints=False)
def step(stage: str, config: dict, job: str, progress: dict, **kwargs) -> dict | str:
    progress['attempts'][stage] = max(progress['attempts'].get(stage, 0), task_run.run_count)
    progress['stage'] = stage
    try:
        if stage == 'preflight':
            analytics_step(config, Path(job), probe=True)
            return freeze_packages(config, Path(job)) if config['mode'] == 'run' else {}
        if stage in ('ingest_oms', 'ingest_psp'):
            return publish_step(stage.removeprefix('ingest_'), config)
        if stage == 'cutoff':
            return choose_cutoff(config)
        if stage == 'prepare':
            return prepare_step(config, kwargs['cutoff'], kwargs['batches'])
        if stage == 'execute':
            return execute_step(kwargs['run_id'], config['dsn_env'])
        if stage == 'marts':
            return analytics_step(config, Path(job))
        raise PipelineError('preflight', 'PIPELINE_STAGE')
    except PipelineError:
        raise
    except Exception:
        raise PipelineError(stage, 'STEP_UNCONFIRMED') from None


@flow(name='commerceguard-local', retries=0, persist_result=False, log_prints=False, validate_parameters=False)
def commerce_flow(config: dict, job: str, progress: dict) -> dict:
    def call(stage, **kwargs):
        value = step.with_options(name=stage)(stage, config, job, progress, **kwargs)
        progress['completed_stages'].append(stage)
        return value
    config = dict(config)
    config.update(call('preflight'))
    if config['mode'] == 'run':
        batches = []
        progress['batches'] = batches
        for source in ('oms', 'psp'):
            batches.append(call('ingest_' + source))
        cutoff = call('cutoff')
        progress['as_of'] = cutoff
        prepared = call('prepare', cutoff=cutoff, batches=batches)
        progress['run_id'] = prepared['run_id']
    else:
        progress['run_id'] = config['run_id']
    progress['result'] = call('execute', run_id=progress['run_id'])
    progress['analytics'] = call('marts')
    progress['stage'] = 'marts'
    return {'status': 'completed'}
