"""Общее ленивое подключение: параметры и строки драйвера не попадают в CLI."""

from contextlib import contextmanager
import os
import re


class DatabaseError(ValueError):
    """Безопасное сообщение, без DSN, значений COPY и серверного DETAIL."""


@contextmanager
def postgres_session(dsn_env: str, *, application_name: str, statement_timeout_ms: int = 30000):
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", dsn_env) is None:
        raise DatabaseError("Имя переменной подключения некорректно")
    dsn = os.environ.get(dsn_env, "")
    if not dsn.strip() or "\x00" in dsn:
        raise DatabaseError("Задай переменную подключения к отдельной БД commerceguard")
    try:
        import psycopg
    except ImportError:
        raise DatabaseError("Для БД нужен отдельный набор requirements-postgres.lock") from None
    if psycopg.__version__ != "3.3.6":
        raise DatabaseError("Нужна закреплённая версия Psycopg 3.3.6")
    if statement_timeout_ms not in (30000, 120000):
        raise DatabaseError("Неподдерживаемый предел времени команды БД")
    try:
        # autocommit не публикует строки отдельно: сервис обязан открыть transaction().
        with psycopg.connect(
            dsn, autocommit=True, connect_timeout=5, application_name=application_name,
            options="-c search_path=pg_catalog -c lock_timeout=5000 "
                    f"-c statement_timeout={statement_timeout_ms} "
                    "-c idle_in_transaction_session_timeout=30000",
        ) as connection:
            yield connection
    except psycopg.Error as exc:
        state = exc.sqlstate if exc.sqlstate and re.fullmatch(r"[A-Z0-9]{5}", exc.sqlstate) else "unknown"
        raise DatabaseError(
            "Операция БД не подтверждена (SQLSTATE=" + state + "). "
            "Текст драйвера скрыт. При обрыве связи во время COMMIT исход неизвестен; "
            "повтори тот же пакет, не меняя manifest."
        ) from None
