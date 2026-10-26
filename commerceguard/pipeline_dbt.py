"""Я строю витрины в analytics Python, используя то же явное подключение, что ingestion."""

import argparse
from importlib.metadata import version
import json
import os
from pathlib import Path
import tempfile


def connection_profile(dsn: str) -> dict:
    from psycopg.conninfo import conninfo_to_dict
    values = conninfo_to_dict(dsn)
    allowed = {'dbname', 'host', 'port', 'user', 'password', 'sslmode', 'sslcert', 'sslkey', 'sslrootcert',
               'connect_timeout', 'application_name'}
    if set(values) - allowed or any(not values.get(k) for k in ('dbname', 'host', 'user')):
        raise ValueError('ANALYTICS_CONNECTION_CONTRACT')
    port = int(values.get('port', '5432'))
    if values['dbname'] != 'commerceguard' or not 1 <= port <= 65535 or ',' in values['host']:
        raise ValueError('ANALYTICS_CONNECTION_CONTRACT')
    os.environ['DBT_ENV_SECRET_CG_PIPELINE_PASSWORD'] = values.get('password', os.environ.get('PGPASSWORD', ''))
    result = {'type': 'postgres', 'host': values['host'], 'port': port, 'user': values['user'],
              'dbname': 'commerceguard', 'schema': 'commerceguard_mart', 'threads': 2, 'retries': 0,
              'connect_timeout': 5, 'sslmode': values.get('sslmode', 'prefer'),
              'password': "{{ env_var('DBT_ENV_SECRET_CG_PIPELINE_PASSWORD', '') }}"}
    result.update({k: values[k] for k in ('sslcert', 'sslkey', 'sslrootcert') if k in values})
    return {'commerceguard_analytics': {'target': 'local', 'outputs': {'local': result}}}


def build(dsn_env: str, *, probe: bool) -> dict:
    if version('dbt-core') != '1.12.6' or version('dbt-postgres') != '1.11.0' or version('psycopg') != '3.3.6':
        raise ValueError('ANALYTICS_VERSION')
    profile = connection_profile(os.environ[dsn_env])
    if probe:
        return {'status': 'completed', 'dbt_core': '1.12.6', 'dbt_postgres': '1.11.0'}
    from dbt.cli.main import dbtRunner
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='cg-marts-') as directory:
        folder = Path(directory)
        (folder / 'profiles.yml').write_text(json.dumps(profile), encoding='utf-8')
        result = dbtRunner().invoke(['build', '--project-dir', str(root / 'analytics'), '--profiles-dir', str(folder),
                                     '--target-path', str(folder / 'target'), '--log-path', str(folder / 'logs'),
                                     '--no-use-colors', '--no-send-anonymous-usage-stats'])
        path = folder / 'target/run_results.json'
        if not result.success or not path.is_file() or path.stat().st_size > 4194304:
            raise ValueError('ANALYTICS_BUILD_FAILED')
        nodes = json.loads(path.read_text(encoding='utf-8'))['results']
        if not nodes or any(n['status'] not in ('success', 'pass') for n in nodes):
            raise ValueError('ANALYTICS_NODE_FAILED')
        return {'status': 'completed', 'models': sum(n['unique_id'].startswith('model.') for n in nodes),
                'tests': sum(n['unique_id'].startswith('test.') for n in nodes)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--result', type=Path, required=True)
    parser.add_argument('--dsn-env', required=True)
    parser.add_argument('--probe', action='store_true')
    args = parser.parse_args()
    try:
        value, code = build(args.dsn_env, probe=args.probe), 0
    except Exception:
        # Я не передаю наверх dbt logs/DSN/значения строк; ошибка этапа остаётся явной.
        value, code = {'status': 'failed'}, 2
    args.result.write_text(json.dumps(value), encoding='utf-8')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
