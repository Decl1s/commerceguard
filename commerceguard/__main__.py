"""CLI: demo, миграции db, inspect и атомарная публикация входа."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from . import __version__
from .demo import scenario
from .domain import ContractError
from .file_contracts import FileInputError
from .migrations import MigrationError
from .postgres import DatabaseError
from .raw_store import RawStoreError
from .ingestion import PublicationError
from .ingest_journal import PublicationFailure
from .sample_data import SampleDataError
from .ingest_status import StatusError


def main() -> int:
    """Разбор аргументов отделён от правил: новые команды не меняют расчёт."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="CommerceGuard — начальный срез сверки")
    parser.add_argument("--version", action="version", version=__version__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("demo", help="Напечатать расчёт синтетического сценария")
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
    generate.add_argument("--scenario", choices=("baseline", "invalid-json", "conflict", "earlier-observed"),
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
    arguments = parser.parse_args()
    try:
        if arguments.command == "db":
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
        else:
            result = asdict(scenario())
            result["as_of"] = result["as_of"].isoformat()
    except (ContractError, MigrationError, FileInputError, DatabaseError, RawStoreError, PublicationError, PublicationFailure, SampleDataError, StatusError) as exc:
        print("Операция не подтверждена: " + str(exc), file=sys.stderr)
        return 130 if isinstance(exc, PublicationFailure) and exc.rejection.category == "interrupted" else 2
    result["execution_notice"] = "Я пока не запускал исходники; статус unverified"
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
