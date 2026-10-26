"""Я отделяю команды приёма, сохранённой сверки и карточек от их предметных правил."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from . import __version__
from .demo import scenario
from .domain import ContractError
from .file_contracts import FileInputError, canonical_time
from .migrations import MigrationError
from .postgres import DatabaseError
from .raw_store import RawStoreError
from .ingestion import PublicationError
from .ingest_journal import PublicationFailure
from .sample_data import SampleDataError
from .ingest_status import StatusError
from .run_plans import RunPlanError
from .run_execution import RunExecutionError
from .case_projection import CaseError
from .source_health import SourceHealthError
from .pipeline import PipelineError
from .settlement_contract import SettlementError


def main() -> int:
    """Разбор аргументов отделён от правил: новые команды не меняют расчёт."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="CommerceGuard — сверка и история решений")
    parser.add_argument("--version", action="version", version=__version__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("demo", help="Напечатать расчёт синтетического сценария")
    settlement = subcommands.add_parser("settlement", help="Выписка PSP batch, комиссия и сохранённая сверка")
    settlement_actions = settlement.add_subparsers(dest="settlement_action", required=True)
    sg = settlement_actions.add_parser("generate", help="Создать три синтетические выписки в новом каталоге")
    sg.add_argument("--output", type=Path, required=True)
    si = settlement_actions.add_parser("inspect", help="Разобрать выписку без БД и показать только metadata")
    si.add_argument("--input", type=Path, required=True)
    sp = settlement_actions.add_parser("publish", help="Сохранить immutable выписку и membership")
    sp.add_argument("--input", type=Path, required=True)
    sp.add_argument("--raw-root", type=Path, default=Path("workspace/raw"))
    sp.add_argument("--dsn-env", default="COMMERCEGUARD_DATABASE_URL")
    sr = settlement_actions.add_parser("run", help="Сверить выписку с PSP и явно заданным тарифом")
    sr.add_argument("--advice-id", required=True)
    sr.add_argument("--as-of", required=True)
    sr.add_argument("--fee-bps", type=int, required=True)
    sr.add_argument("--dsn-env", default="COMMERCEGUARD_DATABASE_URL")
    sv = settlement_actions.add_parser("result", help="Прочитать сохранённый результат с bounded evidence")
    sv.add_argument("--report-id", required=True)
    sv.add_argument("--limit", type=int, default=50)
    sv.add_argument("--dsn-env", default="COMMERCEGUARD_DATABASE_URL")
    pipeline = subcommands.add_parser("pipeline", help="Локальная цепочка Prefect: приём → сверка → витрины")
    pipeline_actions = pipeline.add_subparsers(dest="pipeline_action", required=True)
    for action in ("run", "resume"):
        command = pipeline_actions.add_parser(action, help="Новая цепочка" if action == "run" else "Повтор по immutable run_id")
        command.add_argument("--analytics-python", type=Path, required=True)
        command.add_argument("--dsn-env", default="COMMERCEGUARD_DATABASE_URL")
        if action == "run":
            command.add_argument("--merchant", required=True)
            command.add_argument("--as-of", default="now", help="RFC3339 или now: часы БД после ingest")
            for field in ("oms-manifest", "oms-data", "psp-manifest", "psp-data"):
                command.add_argument("--" + field, type=Path, required=True)
            command.add_argument("--raw-root", type=Path, default=Path("workspace/raw"))
        else:
            command.add_argument("--run-id", required=True)
    sources = subcommands.add_parser("source", help="Состояние свежести и полноты источников")
    source_actions = sources.add_subparsers(dest="source_action", required=True)
    health = source_actions.add_parser("health", help="Прочитать watermarks, последний пакет и попытку")
    health.add_argument("--merchant", required=True)
    health.add_argument("--as-of", required=True, help="Явный RFC3339 или now по часам БД")
    health.add_argument("--business-timezone", required=True, help="IANA timezone из закреплённого tzdata")
    health.add_argument("--max-age-seconds", type=int, required=True)
    health.add_argument("--late-after-seconds", type=int, required=True)
    health.add_argument("--dsn-env", default="COMMERCEGUARD_DATABASE_URL")
    database = subcommands.add_parser("db", help="Версии и миграции отдельной БД commerceguard")
    database.add_argument("--dsn-env", default="COMMERCEGUARD_DATABASE_URL", help="Имя внешней переменной подключения")
    actions = database.add_subparsers(dest="database_action", required=True)
    actions.add_parser("status", help="Прочитать текущую и доступную версии, без создания схемы")
    actions.add_parser("migrate", help="Применить pending-миграции одним COMMIT")
    inputs = subcommands.add_parser("input", help="Разбор файла OMS CSV / PSP JSONL без БД")
    input_actions = inputs.add_subparsers(dest="input_action", required=True)
    inspect = input_actions.add_parser("inspect", help="Проверить manifest и весь файл, напечатать только сводку")
    inspect.add_argument("--manifest", type=Path, required=True, help="Явный путь к JSON manifest")
    inspect.add_argument("--data", type=Path, required=True, help="Явный путь к CSV/JSONL; путь не берётся из manifest")
    generate = input_actions.add_parser("generate", help="Создать синтетический набор в новом каталоге")
    generate.add_argument("--output", type=Path, default=Path("workspace/input"))
    generate.add_argument("--scenario", choices=("baseline", "invalid-json", "conflict", "earlier-observed", "split-deadlines"),
                          default="baseline")
    ingest = subcommands.add_parser("ingest", help="Постоянный raw и атомарная публикация в PostgreSQL")
    ingest_actions = ingest.add_subparsers(dest="ingest_action", required=True)
    publish = ingest_actions.add_parser("publish", help="Принять полный пакет OMS/PSP одним COMMIT")
    publish.add_argument("--manifest", type=Path, required=True)
    publish.add_argument("--data", type=Path, required=True)
    publish.add_argument("--raw-root", type=Path, default=Path("workspace/raw"))
    publish.add_argument("--dsn-env", default="COMMERCEGUARD_DATABASE_URL")
    recover = ingest_actions.add_parser("recover", help="Повторить приём по сохранённому manifest SHA")
    recover.add_argument("--manifest-sha", required=True)
    recover.add_argument("--raw-root", type=Path, default=Path("workspace/raw"))
    recover.add_argument("--dsn-env", default="COMMERCEGUARD_DATABASE_URL")
    scan = ingest_actions.add_parser("scan-raw", help="Сопоставить ограниченный список raw manifests с БД")
    scan.add_argument("--raw-root", type=Path, default=Path("workspace/raw"))
    scan.add_argument("--limit", type=int, default=100)
    scan.add_argument("--dsn-env", default="COMMERCEGUARD_DATABASE_URL")
    status = ingest_actions.add_parser("status", help="Прочитать metadata пакета и историю попыток")
    selector = status.add_mutually_exclusive_group(required=True)
    selector.add_argument("--batch-id")
    selector.add_argument("--attempt-id")
    selector.add_argument("--manifest-sha")
    status.add_argument("--limit", type=int, default=20)
    status.add_argument("--dsn-env", default="COMMERCEGUARD_DATABASE_URL")
    runs = subcommands.add_parser("run", help="Неизменяемый manifest входов сверки")
    run_actions = runs.add_subparsers(dest="run_action", required=True)
    prepare = run_actions.add_parser("prepare", help="Закрепить опубликованные входы без вычисления результата")
    prepare.add_argument("--merchant", required=True)
    prepare.add_argument("--as-of", required=True)
    prepare.add_argument("--mode", choices=("as-was", "as-known-now"), default="as-was")
    prepare.add_argument("--knowledge-at", help="Явная RFC3339 граница знания для корректировки")
    prepare.add_argument("--reason", choices=("manual", "scheduled", "late-data", "recovery"), default="manual")
    prepare.add_argument("--baseline-run-id", help="Опубликованный run той же даты для as-known-now")
    prepare.add_argument("--dsn-env", default="COMMERCEGUARD_DATABASE_URL")
    show = run_actions.add_parser("show", help="Прочитать ранее сохранённый manifest")
    show.add_argument("--run-id", required=True)
    show.add_argument("--dsn-env", default="COMMERCEGUARD_DATABASE_URL")
    execute = run_actions.add_parser("execute", help="Посчитать и сохранить результат по immutable manifest")
    execute.add_argument("--run-id", required=True)
    execute.add_argument("--dsn-env", default="COMMERCEGUARD_DATABASE_URL")
    result_view = run_actions.add_parser("result", help="Прочитать опубликованный результат")
    result_view.add_argument("--run-id", required=True)
    result_view.add_argument("--limit", type=int, default=50)
    result_view.add_argument("--dsn-env", default="COMMERCEGUARD_DATABASE_URL")
    evidence_view = run_actions.add_parser("evidence", help="Показать raw ссылки для finding или заказа")
    evidence_view.add_argument("--run-id", required=True)
    evidence_selector = evidence_view.add_mutually_exclusive_group(required=True)
    evidence_selector.add_argument("--case-key")
    evidence_selector.add_argument("--order-id")
    evidence_view.add_argument("--limit", type=int, default=50)
    evidence_view.add_argument("--dsn-env", default="COMMERCEGUARD_DATABASE_URL")
    changes_view = run_actions.add_parser("changes", help="Прочитать отличие корректировки от её baseline")
    changes_view.add_argument("--run-id", required=True)
    changes_view.add_argument("--limit", type=int, default=50)
    changes_view.add_argument("--dsn-env", default="COMMERCEGUARD_DATABASE_URL")
    cases = subcommands.add_parser("case", help="Применение результата и история карточек расхождений")
    case_actions = cases.add_subparsers(dest="case_action", required=True)
    case_apply = case_actions.add_parser("apply", help="Явно продвинуть канонический результат магазина")
    case_apply.add_argument("--run-id", required=True)
    case_apply.add_argument("--upgrade-from-run-id", help="Точный текущий head для явного перехода balance-v1 → balance-v2")
    case_apply.add_argument("--dsn-env", default="COMMERCEGUARD_DATABASE_URL")
    case_list = case_actions.add_parser("list", help="Прочитать ограниченный список карточек")
    case_list.add_argument("--merchant", required=True)
    case_list.add_argument("--presence", choices=("present", "absent", "all"), default="present")
    case_list.add_argument("--after", help="case_key последней карточки предыдущей страницы")
    case_list.add_argument("--limit", type=int, default=50)
    case_list.add_argument("--dsn-env", default="COMMERCEGUARD_DATABASE_URL")
    case_show = case_actions.add_parser("show", help="Прочитать карточку и страницу ревизий")
    case_show.add_argument("--case-key", required=True)
    case_show.add_argument("--before-revision", type=int)
    case_show.add_argument("--limit", type=int, default=20)
    case_show.add_argument("--dsn-env", default="COMMERCEGUARD_DATABASE_URL")
    arguments = parser.parse_args()
    try:
        if arguments.command == "pipeline":
            from .pipeline import launch_pipeline
            keys = ("merchant", "as_of", "oms_manifest", "oms_data", "psp_manifest", "psp_data", "raw_root", "run_id")
            extra = {key: getattr(arguments, key) for key in keys if hasattr(arguments, key)}
            result = launch_pipeline(mode=arguments.pipeline_action, analytics_python=arguments.analytics_python,
                                     dsn_env=arguments.dsn_env, **extra)
        elif arguments.command == "source":
            from .source_health_store import source_health
            result = source_health(arguments.merchant, as_of=arguments.as_of, business_timezone=arguments.business_timezone,
                                   max_age_seconds=arguments.max_age_seconds, late_after_seconds=arguments.late_after_seconds,
                                   dsn_env=arguments.dsn_env)
        elif arguments.command == "db":
            from .migrations import database_command
            result = asdict(database_command(
                apply=arguments.database_action == "migrate", dsn_env=arguments.dsn_env,
            ))
        elif arguments.command == "input":
            if arguments.input_action == "generate":
                from .sample_data import generate_inputs
                result = generate_inputs(arguments.output, scenario=arguments.scenario)
            else:
                from .file_inputs import inspect_input
                result = inspect_input(arguments.manifest, arguments.data)
        elif arguments.command == "settlement":
            if arguments.settlement_action in ("generate", "inspect"):
                from .settlement_contract import generate_advice, inspect_advice
                result = (generate_advice(arguments.output) if arguments.settlement_action == "generate"
                          else inspect_advice(arguments.input))
            else:
                from .settlement_store import publish_advice, run_settlement, read_settlement
                if arguments.settlement_action == "publish":
                    result = publish_advice(arguments.input, arguments.raw_root, dsn_env=arguments.dsn_env)
                elif arguments.settlement_action == "run":
                    from .file_contracts import timestamp
                    result = run_settlement(arguments.advice_id,
                                            timestamp(arguments.as_of, artifact="arguments", field="as_of"),
                                            arguments.fee_bps, dsn_env=arguments.dsn_env)
                else:
                    result = read_settlement(arguments.report_id, limit=arguments.limit, dsn_env=arguments.dsn_env)
        elif arguments.command == "ingest":
            if arguments.ingest_action == "publish":
                from .ingestion import publish_input
                result = asdict(publish_input(
                    arguments.manifest, arguments.data, arguments.raw_root, dsn_env=arguments.dsn_env,
                ))
            elif arguments.ingest_action == "recover":
                from .recovery import recover_input
                result = asdict(recover_input(arguments.raw_root, arguments.manifest_sha, dsn_env=arguments.dsn_env))
            elif arguments.ingest_action == "scan-raw":
                from .recovery import scan_raw
                result = scan_raw(arguments.raw_root, limit=arguments.limit, dsn_env=arguments.dsn_env)
            else:
                from .ingest_status import ingest_status
                result = ingest_status(batch_id=arguments.batch_id, attempt_id=arguments.attempt_id,
                                       manifest_sha256=arguments.manifest_sha, limit=arguments.limit,
                                       dsn_env=arguments.dsn_env)
        elif arguments.command == "case":
            from .case_store import apply_cases, list_cases, show_case
            if arguments.case_action == "apply":
                result = apply_cases(arguments.run_id, upgrade_from_run_id=arguments.upgrade_from_run_id,
                                     dsn_env=arguments.dsn_env)
            elif arguments.case_action == "list":
                result = list_cases(arguments.merchant, presence=arguments.presence, after=arguments.after,
                                    limit=arguments.limit, dsn_env=arguments.dsn_env)
            else:
                result = show_case(arguments.case_key, before_revision=arguments.before_revision,
                                   limit=arguments.limit, dsn_env=arguments.dsn_env)
        elif arguments.command == "run":
            if arguments.run_action == "prepare":
                from .file_contracts import timestamp
                from .run_plans import prepare_run
                cutoff = timestamp(arguments.as_of, artifact="arguments", field="as_of")
                knowledge = (timestamp(arguments.knowledge_at, artifact="arguments", field="knowledge_at")
                             if arguments.knowledge_at is not None else None)
                result = asdict(prepare_run(arguments.merchant, cutoff, mode=arguments.mode,
                                           knowledge_at=knowledge, reason=arguments.reason,
                                           baseline_run_id=arguments.baseline_run_id, dsn_env=arguments.dsn_env))
            elif arguments.run_action == "show":
                from .run_plans import show_run
                result = show_run(arguments.run_id, dsn_env=arguments.dsn_env)
                result["calculation_invoked"] = result.pop("calculation_performed")
            elif arguments.run_action == "execute":
                from .run_execution import execute_run
                result = execute_run(arguments.run_id, dsn_env=arguments.dsn_env)
            elif arguments.run_action == "result":
                from .run_execution import read_result
                result = read_result(arguments.run_id, limit=arguments.limit, dsn_env=arguments.dsn_env)
            elif arguments.run_action == "changes":
                from .run_changes import read_changes
                result = read_changes(arguments.run_id, limit=arguments.limit, dsn_env=arguments.dsn_env)
            else:
                from .run_execution import read_evidence
                result = read_evidence(arguments.run_id, case_key=arguments.case_key, order_id=arguments.order_id,
                                       limit=arguments.limit, dsn_env=arguments.dsn_env)
        else:
            result = asdict(scenario())
            result["as_of"] = result["as_of"].isoformat()
            result["knowledge_at"] = result["knowledge_at"].isoformat()
            for balance in result["balances"]:
                balance["capture_due_at"] = canonical_time(balance["capture_due_at"])
                balance["refund_due_at"] = canonical_time(balance["refund_due_at"])
    except (ContractError, MigrationError, FileInputError, DatabaseError, RawStoreError, PublicationError, PublicationFailure, SampleDataError, StatusError, RunPlanError, RunExecutionError, CaseError, SettlementError, PipelineError, SourceHealthError) as exc:
        print("Операция не подтверждена: " + str(exc), file=sys.stderr)
        return 130 if (isinstance(exc, PublicationFailure) and exc.rejection.category == "interrupted") or getattr(exc, "interrupted", False) else 2
    result["execution_notice"] = "Результат этой команды; область выполненных проверок я фиксирую в VALIDATION.md"
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result.get("action") == "pipeline" and result.get("status") != "completed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
