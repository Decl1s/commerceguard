"""Точка входа первого среза. Команда печатает JSON, не изменяя файлы и БД."""

import argparse
from dataclasses import asdict
import json
import sys

from . import __version__
from .demo import scenario
from .domain import ContractError


def main() -> int:
    """Разбор аргументов отделён от правил: новые команды не меняют расчёт."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="CommerceGuard — начальный срез сверки")
    parser.add_argument("--version", action="version", version=__version__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("demo", help="Напечатать расчёт синтетического сценария")
    parser.parse_args()
    try:
        result = asdict(scenario())
    except ContractError as exc:
        print("Ошибка контракта: " + str(exc), file=sys.stderr)
        return 2
    result["as_of"] = result["as_of"].isoformat()
    result["execution_notice"] = "Начальный срез; проверки разработчиком не выполнялись"
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
