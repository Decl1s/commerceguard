"""Я проверяю сквозной путь в одноразовом PostgreSQL 16 и всегда останавливаю его."""

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import traceback
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import psycopg
from commerceguard.case_projection import CaseError
from commerceguard.case_store import apply_cases, show_case
from commerceguard.ingestion import publish_input
from commerceguard.ingest_journal import PublicationFailure
from commerceguard.migrations import database_command, load_migrations
from commerceguard.run_changes import read_changes
from commerceguard.run_execution import execute_run, read_result, read_evidence
from commerceguard.run_plans import prepare_run
from commerceguard.sample_data import generate_inputs
from settlement_scenarios import verify_settlements
from freshness_scenarios import verify_source_health
from workbench_scenarios import verify_workbench
from operations_scenarios import verify_operations


def require(condition, label):
    if not condition:
        raise AssertionError(label)


def verify(work: Path, *, bin_dir: Path):
    data, socket = work / 'pg', work / 'socket'
    socket.mkdir(mode=0o700)
    log = work / 'postgres.log'
    subprocess.run([str(bin_dir / 'initdb'), '-D', str(data), '-U', 'cg_check',
                    '--auth-local=trust', '--auth-host=reject', '--encoding=UTF8', '--no-locale'],
                   check=True, stdout=subprocess.DEVNULL)
    options = f"-c listen_addresses='' -c unix_socket_directories={socket} -p 55432 -c timezone=UTC -c max_connections=20 -c shared_buffers=32MB"
    started = False
    legacy_patch = None
    try:
        subprocess.run([str(bin_dir / 'pg_ctl'), '-D', str(data), '-l', str(log), '-o', options, 'start'],
                       check=True, stdout=subprocess.DEVNULL)
        started = True
        conninfo = f'host={socket} port=55432 user=cg_check'
        with psycopg.connect(conninfo + ' dbname=postgres', autocommit=True) as admin:
            admin.execute('CREATE DATABASE commerceguard')
        os.environ['COMMERCEGUARD_CHECK_DSN'] = conninfo + ' dbname=commerceguard'
        env_arg = {'dsn_env': 'COMMERCEGUARD_CHECK_DSN'}
        with psycopg.connect(os.environ['COMMERCEGUARD_CHECK_DSN'], autocommit=True) as db:
            now = lambda: db.execute('select clock_timestamp()').fetchone()[0]
            # Я сначала создаю настоящий schema8 набор с фактами/results, затем обновляю до9.
            legacy_patch = patch('commerceguard.migrations.load_migrations', return_value=load_migrations()[:8])
            legacy_patch.start()
            report = database_command(apply=True, **env_arg)
            require(report.current_version == 8, 'all eight migrations')
            require(not database_command(apply=True, **env_arg).applied, 'migration repeat is noop')
            require(db.execute("select count(*) from information_schema.tables where table_schema='commerceguard' "
                               "and table_type='BASE TABLE'").fetchone()[0] == 20, '20 core tables')

            baseline, split = work / 'baseline', work / 'split'
            generate_inputs(baseline)
            generate_inputs(split, scenario='split-deadlines')
            raw = work / 'raw'
            def publish(folder, stem):
                extension = '.csv' if stem.startswith('oms') else '.jsonl'
                return publish_input(folder / (stem + '.manifest.json'), folder / (stem + extension), raw, **env_arg)

            oms = publish(baseline, 'oms')
            psp = publish(baseline, 'psp')
            require(publish(baseline, 'psp').duplicate_batch, 'identical batch repeat')
            require((oms.rows_parsed, psp.rows_parsed) == (5, 7), 'full file counts')
            def run(cutoff=None, **kwargs):
                return prepare_run('M01', cutoff or now(), **kwargs, **env_arg)
            first = run()
            require(prepare_run('M01', datetime.fromisoformat(first.as_of.replace('Z', '+00:00')),
                                **env_arg).duplicate_manifest, 'prepare repeat')
            executed = execute_run(first.run_id, **env_arg)
            require(execute_run(first.run_id, **env_arg)['duplicate_result'], 'execute repeat')
            first_payload = read_result(first.run_id, **env_arg)
            shortfall = next(f for f in first_payload['findings'] if f['order_id'] == 'O1002')
            require(shortfall['delta_minor'] == -1000, 'baseline shortfall')
            apply_cases(first.run_id, **env_arg)
            require(apply_cases(first.run_id, **env_arg)['already_applied'], 'case repeat')
            evidence = read_evidence(first.run_id, order_id='O1002', **env_arg)
            require(evidence['found'], 'raw lineage viewer')

            publish(baseline, 'psp-late')
            correction = run(datetime.fromisoformat(first.as_of.replace('Z', '+00:00')),
                             mode='as-known-now', knowledge_at=now(), reason='late-data', baseline_run_id=first.run_id)
            execute_run(correction.run_id, **env_arg)
            changes = read_changes(correction.run_id, **env_arg)
            require(changes['finding_counts']['disappeared'] == 1, 'late payment removes one finding')
            require(changes['newly_visible_event_count'] == 1, 'late event lineage')
            require(read_result(first.run_id, **env_arg)['result_sha256'] == executed['result_sha256'], 'old result immutable')
            try:
                apply_cases(correction.run_id, **env_arg)
            except CaseError as exc:
                require(str(exc) == 'CASE_CORRECTION_REPORT_ONLY', 'correction case guard code')
            else:
                raise AssertionError('correction must not advance cases')
            current = run()
            execute_run(current.run_id, **env_arg)
            apply_cases(current.run_id, **env_arg)
            case = show_case(shortfall['case_key'], **env_arg)
            require(case['found'], 'case history viewer')
            require(apply_cases(first.run_id, **env_arg)['is_current'] is False, 'old retry cannot regress stream')

            # Я сохраняю сырой whole-package отказ и отсутствие частичных новых фактов.
            fact_count = db.execute('select count(*) from commerceguard.core_payment_event').fetchone()[0]
            for scenario in ('conflict', 'earlier-observed', 'invalid-json'):
                folder = work / scenario
                generate_inputs(folder, scenario=scenario)
                try:
                    publish(folder, 'psp')
                except PublicationFailure:
                    pass
                else:
                    raise AssertionError('package rejection: ' + scenario)
                require(db.execute('select count(*) from commerceguard.core_payment_event').fetchone()[0] == fact_count,
                        'rejected package cannot publish facts')

            # Два capture и два refund одного заказа выявляют fanout на сыром JOIN.
            fanout = work / 'fanout'
            fanout.mkdir()
            original = json.loads((baseline / 'psp.jsonl').read_text().splitlines()[0])
            records = [original]
            for event_id, kind, amount in [('CA', 'capture', 200), ('CB', 'capture', 300),
                                            ('RA', 'refund', 70), ('RB', 'refund', 30)]:
                records.append(dict(original, source_event_id=event_id, kind=kind, amount_minor=amount))
            content = ''.join(json.dumps(x, separators=(',', ':')) + '\n' for x in records).encode()
            manifest = json.loads((baseline / 'psp.manifest.json').read_text())
            manifest.update(row_count=len(records), byte_count=len(content), content_sha256=hashlib.sha256(content).hexdigest())
            (fanout / 'psp.jsonl').write_bytes(content)
            (fanout / 'psp.manifest.json').write_text(json.dumps(manifest))
            publish(fanout, 'psp')
            publish(split, 'oms')
            final = run()
            execute_run(final.run_id, **env_arg)
            apply_cases(final.run_id, **env_arg)
            balance = next(b for b in read_result(final.run_id, **env_arg)['balances'] if b['order_id'] == 'O1003')
            require(balance['expectation_version'] == 2, 'OMS v2 selected')
            # Fixture refund deadline 26 October: этот относительный сценарий читаю по явному cutoff.
            require(balance['capture_state'] == 'discrepancy', 'capture independent from refund deadline')
            unfinished = run()
            legacy_patch.stop()
            upgraded = database_command(apply=True, **env_arg)
            require(upgraded.current_version == len(load_migrations()) and len(upgraded.applied) == len(load_migrations())-8, 'upgrade populated schema8 to current')
            require(not database_command(apply=True, **env_arg).applied, 'schema9 replay')
            require(read_result(first.run_id, **env_arg)['result_sha256'] == executed['result_sha256'],
                    'migration preserves old reports')
            require(db.execute("select count(*) from information_schema.tables where table_schema='commerceguard' "
                               "and table_type='BASE TABLE'").fetchone()[0] == 30, '30 tables including backfill')
            settlement = verify_settlements(work, db, raw, env_arg, now)
            env = dict(os.environ, CG_PGHOST=str(socket), CG_PGPORT='55432', CG_PGUSER='cg_check',
                       DBT_SEND_ANONYMOUS_USAGE_STATS='false', DO_NOT_TRACK='1')
            subprocess.run([str(ROOT / '.venv/bin/dbt'), 'build', '--project-dir', str(ROOT / 'analytics'),
                            '--profiles-dir', str(ROOT / 'analytics')], check=True, cwd=ROOT, env=env)
            build = json.loads((ROOT / 'analytics/target/run_results.json').read_text())['results']
            model_count = sum(item['unique_id'].startswith('model.') for item in build)
            test_count = sum(item['unique_id'].startswith('test.') for item in build)
            require(all(item['status'] in ('success', 'pass') for item in build), 'all dbt nodes pass')
            count = db.execute('select count(*) from commerceguard_mart.stg_completed_runs').fetchone()[0]
            require(count == 4, 'only four completed reports')
            require(db.execute('select count(*) from commerceguard_mart.stg_completed_runs where run_id=%s',
                               (unfinished.run_id,)).fetchone()[0] == 0, 'prepared run excluded')
            values = db.execute('select receipt_capture_minor,receipt_refund_minor,capture_events,refund_events '
                                'from commerceguard_mart.fct_order_reconciliation where run_id=%s and order_id=%s',
                                (final.run_id, 'O1001')).fetchone()
            require(values == (10500, 100, 3, 2), 'pre-aggregation prevents fanout and deduplicates delivery')
            usd = db.execute('select order_count,finding_count,known_actual_capture_minor '
                             'from commerceguard_mart.mart_reconciliation_currency where run_id=%s and currency=%s',
                             (final.run_id, 'USD')).fetchone()
            require(usd == (0, 1, None), 'USD finding retained without fabricated balances')
            require(db.execute('select actual_capture_minor,receipt_capture_minor '
                               'from commerceguard_mart.fct_order_reconciliation where run_id=%s and order_id=%s',
                               (final.run_id, 'O1005')).fetchone() == (None, None), 'blocked is unknown in mart')
            require(db.execute('select count(*) from commerceguard_mart.mart_settlement_reconciliation').fetchone()[0]
                    == settlement['reports'], 'all settlement reports in mart')
            require(db.execute('select expected_gross_minor,expected_net_minor '
                               'from commerceguard_mart.mart_settlement_reconciliation where report_id=%s',
                               (settlement['missing_report_id'],)).fetchone() == (None, None), 'mart unknown not zero')
            # Я убеждаюсь, что построение dbt не изменило исходный результат.
            require(read_result(first.run_id, **env_arg)['result_sha256'] == executed['result_sha256'], 'dbt leaves source intact')
            health = verify_source_health(work, db, raw, env_arg, now)
            workplace = verify_workbench(work, db, env_arg, raw)
            operations = verify_operations(work, db, raw, env_arg, bin_dir)
            print(json.dumps({'postgres': db.info.server_version, 'migrations': upgraded.current_version,
                              'completed_runs': count, 'dbt_models': model_count, 'dbt_tests': test_count,
                              'fanout_capture_minor': int(values[0]), 'fanout_refund_minor': int(values[1]),
                              'operations':operations, 'workbench':workplace, 'source_results_immutable': True, 'settlement': settlement, 'source_health': health}, ensure_ascii=False))
    except BaseException as error:
        if error.__context__ is not None:
            traceback.print_exception(error.__context__)
        if log.exists():
            # Я использую только собственные synthetic inputs; вывожу диагностику своего кластера.
            print(log.read_text()[-6000:], file=sys.stderr)
        raise
    finally:
        if legacy_patch is not None:
            legacy_patch.stop()
        if started:
            subprocess.run([str(bin_dir / 'pg_ctl'), '-D', str(data), '-m', 'fast', 'stop'], check=True,
                           stdout=subprocess.DEVNULL)


def main():
    parser = argparse.ArgumentParser(description='Одноразовая сквозная проверка CommerceGuard + dbt')
    parser.add_argument('--pg-bin', type=Path, default=Path('/usr/lib/postgresql/16/bin'))
    args = parser.parse_args()
    if os.name != 'posix' or not (args.pg_bin / 'initdb').is_file():
        raise SystemExit('Я проверил этот runner только на Linux с PostgreSQL 16 binaries; задаю --pg-bin явно.')
    with tempfile.TemporaryDirectory(prefix='cg-', dir='/tmp') as tmp:
        verify(Path(tmp), bin_dir=args.pg_bin)


if __name__ == '__main__':
    main()
