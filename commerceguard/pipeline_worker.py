"""Я исполняю один isolated Prefect flow и записываю только безопасную сводку."""

from importlib.metadata import version
import json
from pathlib import Path
import sys

from .pipeline import PIPELINE_VERSION, PipelineError


def main():
    path = Path(sys.argv[1])
    config = json.loads(path.read_text(encoding='utf-8'))
    progress = {'action': 'pipeline', 'pipeline_version': PIPELINE_VERSION, 'status': 'failed',
                'mode': config['mode'], 'stage': 'preflight', 'completed_stages': [], 'attempts': {}}
    try:
        if version('prefect') != '3.8.8' or version('fastapi') != '0.154.0':
            raise PipelineError('preflight', 'PREFECT_VERSION')
        from prefect.settings import get_current_settings
        settings = get_current_settings()
        if (settings.api.url is not None or settings.api.key is not None
                or settings.server.analytics_enabled or settings.cloud.enable_orchestration_telemetry
                or settings.home != path.parent / 'prefect'):
            raise PipelineError('preflight', 'PREFECT_LOCAL_SETTINGS')
        from prefect.server.api.server import SubprocessASGIServer
        from .pipeline_flow import commerce_flow
        server = SubprocessASGIServer()
        try:
            state = commerce_flow(config, str(path.parent), progress, return_state=True)
            progress['prefect_state'] = state.name
            if state.is_completed():
                progress['status'] = 'completed'
            else:
                error = state.result(raise_on_failure=False)
                progress['error_code'] = error.code if isinstance(error, PipelineError) else 'FLOW_UNCONFIRMED'
        finally:
            server.stop()
            progress['backend_stopped'] = not server.running and server.server_process is None
    except PipelineError as error:
        progress['status'] = 'failed'
        progress['error_code'] = error.code
    except Exception:
        progress['status'] = 'failed'
        progress['error_code'] = 'PREFECT_UNCONFIRMED'
    (path.parent / 'report.json').write_text(json.dumps(progress), encoding='utf-8')
    return 0 if progress['status'] == 'completed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
