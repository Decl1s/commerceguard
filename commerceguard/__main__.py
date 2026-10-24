"""CLI: demo печатает JSON; db status читает версии, db migrate меняет свою схему."""

import argparse
from dataclasses import asdict
import json
import sys

from . import __version__
from .demo import scenario
from .domain import ContractError
from .migrations import MigrationError


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
    arguments = parser.parse_args()
    try:
        if arguments.command == "db":
            from .migrations import database_command
            result = asdict(database_command(
                apply=arguments.database_action == "migrate", dsn_env=arguments.dsn_env,
            ))
        else:
            result = asdict(scenario())
            result["as_of"] = result["as_of"].isoformat()
    except (ContractError, MigrationError) as exc:
        print("Ошибка контракта: " + str(exc), file=sys.stderr)
        return 2
    result["execution_notice"] = "Я пока не запускал исходники; статус unverified"
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
