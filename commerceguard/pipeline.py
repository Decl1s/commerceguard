"""Я запускаю локальный pipeline в изолированном процессе, не импортируя Prefect в ядро."""

import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from uuid import UUID

from .domain import require_id
from .file_contracts import canonical_manifest_bytes, canonical_time, timestamp
from .file_inputs import open_input
from .ingestion import publish_input
from .ingest_journal import PublicationFailure
from .run_execution import execute_run, RunExecutionError
from .run_plans import prepare_run, RunPlanError

ROOT = Path(__file__).resolve().parents[1]
PIPELINE_VERSION = 'local-sequential-v1'
STAGES = ('preflight', 'ingest_oms', 'ingest_psp', 'cutoff', 'prepare', 'execute', 'marts')


class PipelineError(ValueError):
    def __init__(self, stage: str, code: str, *, retryable: bool = False):
        if stage not in STAGES or not re.fullmatch(r'[A-Z0-9_]{1,80}', code):
            raise ValueError('PIPELINE_ERROR_CONTRACT')
        self.stage, self.code, self.retryable = stage, code, retryable
        super().__init__(stage + ':' + code)


def local_environment(job: Path) -> dict[str, str]:
    # Я исключаю Cloud/profile/.env из запуска, не меняя настройки основного процесса.
    env = {k: v for k, v in os.environ.items() if not k.startswith('PREFECT_')}
    env.update(PYTHONPATH=str(ROOT), TMPDIR=str(job), PYTHONUTF8='1',
               NO_PROXY='127.0.0.1,localhost', no_proxy='127.0.0.1,localhost',
               PREFECT_HOME=str(job / 'prefect'), PREFECT_PROFILES_PATH=str(job / 'profiles.toml'),
               PREFECT_SERVER_EPHEMERAL_ENABLED='true', PREFECT_SERVER_EPHEMERAL_STARTUP_TIMEOUT_SECONDS='45',
               PREFECT_SERVER_ANALYTICS_ENABLED='false', PREFECT_CLOUD_ENABLE_ORCHESTRATION_TELEMETRY='false',
               PREFECT_TELEMETRY_ENABLED='false', PREFECT_SERVER_UI_ENABLED='false',
               PREFECT_LOGGING_TO_API_ENABLED='false', PREFECT_LOGGING_LEVEL='WARNING',
               PREFECT_RESULTS_PERSIST_BY_DEFAULT='false', PREFECT_TASKS_REFRESH_CACHE='true',
               PREFECT_SERVER_PLUGINS_ENABLED='false', PREFECT_PLUGINS_ENABLED='false',
               DO_NOT_TRACK='1', DBT_SEND_ANONYMOUS_USAGE_STATS='false')
    return env


def freeze_packages(config: dict, job: Path) -> dict:
    frozen = {}
    for source in ('oms', 'psp'):
        manifest_path, data_path = job / (source + '.manifest.json'), job / (source + '.data')
        def sink(manifest, stream):
            manifest_path.write_bytes(canonical_manifest_bytes(manifest))
            with data_path.open('xb') as output:
                shutil.copyfileobj(stream, output, length=64000)
        # Я читаю каждый исходник один раз, все retry получают уже эти private snapshots.
        with open_input(Path(config[source + '_manifest']), Path(config[source + '_data']), snapshot_sink=sink) as batch:
            if batch.manifest.source != source or batch.manifest.merchant_id != config['merchant']:
                raise PipelineError('preflight', 'PIPELINE_INPUT_CONTEXT')
            for _ in batch.records():
                pass
            batch.summary()
        frozen[source + '_manifest'], frozen[source + '_data'] = str(manifest_path), str(data_path)
    return frozen


def publish_step(source: str, config: dict) -> dict:
    stage = 'ingest_' + source
    try:
        report = publish_input(Path(config[source + '_manifest']), Path(config[source + '_data']),
                               Path(config['raw_root']), dsn_env=config['dsn_env'])
        return {'batch_id': report.batch_id, 'duplicate_batch': report.duplicate_batch,
                'source': source, 'manifest_sha256': report.manifest_sha256}
    except PublicationFailure as error:
        code = error.rejection.code
        # Я не называю любую infrastructure ошибку временной: COMMIT unknown требует разбора.
        retryable = code in {'MERCHANT_BUSY', 'SCHEMA_BUSY'}
        raise PipelineError(stage, code if re.fullmatch(r'[A-Z0-9_]{1,80}', code) else 'INGEST_REJECTED',
                            retryable=retryable) from None
    except Exception:
        raise PipelineError(stage, 'INGEST_UNCONFIRMED') from None


def choose_cutoff(config: dict) -> str:
    if config['as_of'] != 'now':
        return config['as_of']
    from .postgres import postgres_session
    with postgres_session(config['dsn_env'], application_name='commerceguard-pipeline-cutoff') as connection:
        return canonical_time(connection.execute('SELECT clock_timestamp()').fetchone()[0])


def prepare_step(config: dict, cutoff: str, batches: list[dict]) -> dict:
    try:
        prepared = prepare_run(config['merchant'], timestamp(cutoff, artifact='pipeline', field='as_of'),
                               reason='manual', dsn_env=config['dsn_env'])
        from .run_plans import show_run
        saved = show_run(prepared.run_id, dsn_env=config['dsn_env'])
        selected = {item['batch_id'] for item in saved['manifest']['inputs']}
        if any(batch['batch_id'] not in selected for batch in batches):
            raise PipelineError('prepare', 'PIPELINE_INPUT_NOT_SELECTED')
        return {'run_id': prepared.run_id, 'as_of': prepared.as_of,
                'duplicate_manifest': prepared.duplicate_manifest}
    except PipelineError:
        raise
    except RunPlanError:
        raise PipelineError('prepare', 'PREPARE_REJECTED') from None
    except Exception:
        raise PipelineError('prepare', 'PREPARE_UNCONFIRMED') from None


def execute_step(run_id: str, dsn_env: str) -> dict:
    try:
        value = execute_run(run_id, dsn_env=dsn_env)
        return {k: value[k] for k in ('run_id', 'duplicate_result', 'result_sha256', 'balances', 'findings')}
    except RunExecutionError as error:
        code = error.code
        raise PipelineError('execute', code, retryable=code == 'RUN_BUSY') from None
    except Exception:
        raise PipelineError('execute', 'EXECUTION_UNCONFIRMED') from None


def analytics_step(config: dict, job: Path, *, probe: bool = False) -> dict:
    result = job / ('analytics-probe.json' if probe else 'analytics-result.json')
    command = [config['analytics_python'], '-m', 'commerceguard.pipeline_dbt', '--result', str(result),
               '--dsn-env', config['dsn_env']]
    if probe:
        command.append('--probe')
    try:
        value = subprocess.run(command, cwd=job, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=300, check=False)
        if not result.is_file() or result.stat().st_size > 65536:
            raise PipelineError('preflight' if probe else 'marts', 'ANALYTICS_NO_RESPONSE')
        data = json.loads(result.read_text(encoding='utf-8'))
        if value.returncode != 0 or data.get('status') != 'completed':
            raise PipelineError('preflight' if probe else 'marts', 'ANALYTICS_REJECTED')
        return data
    except PipelineError:
        raise
    except Exception:
        raise PipelineError('preflight' if probe else 'marts', 'ANALYTICS_UNCONFIRMED') from None


def launch_pipeline(*, mode: str, analytics_python: Path, dsn_env: str, merchant: str | None = None,
                    as_of: str = 'now', oms_manifest: Path | None = None, oms_data: Path | None = None,
                    psp_manifest: Path | None = None, psp_data: Path | None = None,
                    raw_root: Path = Path('workspace/raw'), run_id: str | None = None) -> dict:
    if mode not in ('run', 'resume') or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,127}', dsn_env):
        raise PipelineError('preflight', 'PIPELINE_ARGUMENTS')
    if dsn_env.startswith('PREFECT_') or not os.environ.get(dsn_env, '').strip():
        raise PipelineError('preflight', 'PIPELINE_DSN_ENV')
    if not analytics_python.is_file() or not os.access(analytics_python, os.X_OK):
        raise PipelineError('preflight', 'ANALYTICS_PYTHON_REQUIRED')
    config = {'mode': mode, 'analytics_python': str(analytics_python.absolute()), 'dsn_env': dsn_env,
              'raw_root': str(raw_root.absolute()), 'as_of': as_of}
    if mode == 'run':
        require_id(merchant, 'merchant_id')
        if any(p is None for p in (oms_manifest, oms_data, psp_manifest, psp_data)):
            raise PipelineError('preflight', 'PIPELINE_INPUTS_REQUIRED')
        if as_of != 'now':
            config['as_of'] = canonical_time(timestamp(as_of, artifact='pipeline', field='as_of'))
        config.update(merchant=merchant, **{name: str(path.absolute()) for name, path in (
            ('oms_manifest', oms_manifest), ('oms_data', oms_data), ('psp_manifest', psp_manifest), ('psp_data', psp_data))})
    else:
        try:
            config['run_id'] = str(UUID(run_id))
        except (ValueError, TypeError, AttributeError):
            raise PipelineError('preflight', 'PIPELINE_RUN_ID') from None
    # Я ограничиваю backend одной командой; конфигурация и Prefect SQLite не живут в репозитории.
    with tempfile.TemporaryDirectory(prefix='cg-flow-') as directory:
        job = Path(directory)
        path = job / 'request.json'
        path.write_text(json.dumps(config), encoding='utf-8')
        path.chmod(0o600)
        env = local_environment(job)
        log = job / 'worker.log'
        with log.open('wb') as output:
            process = subprocess.Popen([sys.executable, '-m', 'commerceguard.pipeline_worker', str(path)], cwd=job,
                                       env=env, stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                                       start_new_session=os.name == 'posix')
            try:
                process.wait(timeout=900)
            except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
                if os.name == 'posix':
                    os.killpg(process.pid, signal.SIGINT)
                else:
                    process.terminate()
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    if os.name == 'posix':
                        os.killpg(process.pid, signal.SIGKILL)
                    else:
                        process.kill()
                    process.wait()
                if isinstance(error, KeyboardInterrupt):
                    raise
                raise PipelineError('preflight', 'PIPELINE_TIMEOUT') from None
        report = job / 'report.json'
        if not report.is_file() or report.stat().st_size > 65536:
            raise PipelineError('preflight', 'PIPELINE_WORKER_UNCONFIRMED')
        value = json.loads(report.read_text(encoding='utf-8'))
        if process.returncode != 0 and value.get('status') == 'completed':
            raise PipelineError('preflight', 'PIPELINE_WORKER_UNCONFIRMED')
        return value
