"""CG-101: собственная схема и атомарное применение доверенных SQL-миграций.

Модуль написан без исполнения. PostgreSQL и Psycopg используются только при
явной команде db. Ни импорт этого модуля, ни demo не подключаются к серверу.
SQL берётся из пакета, DSN — из внешнего окружения и никогда не печатается.
"""

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re

from .postgres import postgres_session

APP_ID = "commerceguard:storage:v1"
DATABASE_NAME = "commerceguard"
SCHEMA = "commerceguard"
LOCK_KEY = (1128744772, 1)
SQL_ROOT = Path(__file__).with_name("sql")


class MigrationError(ValueError):
    """Сообщение составлено приложением и не включает текст ошибки/DSN драйвера."""


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    checksum: str
    sql: str


@dataclass(frozen=True, slots=True)
class MigrationReport:
    action: str
    schema: str
    current_version: int
    available_version: int
    applied: tuple[str, ...]
    pending: tuple[str, ...]


def read_sql(path: Path) -> tuple[str, str]:
    """Контрольная сумма точных исходных байтов, до декодирования UTF-8."""
    try:
        if path.is_symlink() or not path.is_file():
            raise MigrationError("SQL-файл пакета отсутствует или является ссылкой")
        data = path.read_bytes()
        if not data or len(data) > 256000:
            raise MigrationError("SQL-файл пакета пуст или превышает 256000 байт")
        return data.decode("utf-8"), hashlib.sha256(data).hexdigest()
    except (OSError, UnicodeError):
        raise MigrationError("Не удалось прочитать UTF-8 SQL-файл из пакета") from None


def load_migrations() -> tuple[Migration, ...]:
    """Непрерывная последовательность 0001..N; произвольного пути CLI не принимает."""
    folder = SQL_ROOT / "migrations"
    try:
        if SQL_ROOT.is_symlink() or folder.is_symlink() or not folder.is_dir():
            raise MigrationError("Каталог SQL-миграций пакета недоступен")
        paths = sorted(folder.iterdir())
    except OSError:
        raise MigrationError("Не удалось прочитать каталог SQL-миграций") from None
    migrations = []
    for expected, path in enumerate(paths, start=1):
        match = re.fullmatch(r"([0-9]{4})_[a-z][a-z0-9_]*\.sql", path.name)
        if match is None or int(match.group(1)) != expected:
            raise MigrationError("Имена SQL-миграций должны идти непрерывно от 0001")
        text, checksum = read_sql(path)
        migrations.append(Migration(expected, path.name, checksum, text))
    if not migrations:
        raise MigrationError("Пакет не содержит SQL-миграций")
    return tuple(migrations)


def _check_target(cursor, *, apply: bool) -> str:
    """Не создаю схему в случайно указанной БД; версия сервера ограничена веткой 16."""
    cursor.execute(
        "SELECT current_database(), current_user, session_user, "
        "current_setting('server_version_num')::integer, pg_is_in_recovery(), "
        "current_setting('transaction_read_only')"
    )
    name, role, session_role, version, recovery, read_only = cursor.fetchone()
    if name != DATABASE_NAME:
        raise MigrationError("Разрешена только отдельная БД commerceguard; текущая БД другая")
    if version // 10000 != 16:
        raise MigrationError("Этот срез рассчитан только на PostgreSQL 16")
    if role != session_role:
        raise MigrationError("Миграции выполняются без подмены роли через SET ROLE")
    if apply and (recovery or read_only == "on"):
        raise MigrationError("Миграции требуют записываемый primary PostgreSQL")
    return role


def _namespace(cursor, role: str) -> bool:
    """Существующую схему признаём своей только по владельцу и маркеру формата."""
    cursor.execute(
        "SELECT pg_get_userbyid(nspowner), obj_description(oid, 'pg_namespace') "
        "FROM pg_namespace WHERE nspname = %s", (SCHEMA,),
    )
    row = cursor.fetchone()
    if row is None:
        return False
    if row != (role, APP_ID):
        raise MigrationError("Схема commerceguard занята чужим владельцем или другим форматом")
    cursor.execute(
        "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = %s AND c.relkind = 'r' "
        "AND pg_get_userbyid(c.relowner) = %s "
        "AND c.relname IN ('app_identity', 'schema_migration')", (SCHEMA, role),
    )
    if {row[0] for row in cursor.fetchall()} != {"app_identity", "schema_migration"}:
        raise MigrationError("В схеме отсутствуют собственные таблицы идентичности/версий")
    cursor.execute("SELECT singleton, app_id, storage_format FROM commerceguard.app_identity")
    if cursor.fetchall() != [(True, APP_ID, 1)]:
        raise MigrationError("Идентичность хранилища не совпадает с CommerceGuard v1")
    return True


def _history(cursor, available: tuple[Migration, ...]) -> int:
    """Серверная история должна быть точным префиксом исходников данного checkout."""
    cursor.execute("SELECT version, name, checksum FROM commerceguard.schema_migration ORDER BY version")
    rows = cursor.fetchall()
    if len(rows) > len(available):
        raise MigrationError("База новее этого checkout; downgrade не выполняется")
    for index, row in enumerate(rows):
        item = available[index]
        if row != (item.version, item.name, item.checksum):
            raise MigrationError("История/контрольная сумма SQL изменена; автоматического исправления нет")
    return len(rows)


def _script(cursor, text: str) -> None:
    """Не делим SQL по ';': внутри PL/pgSQL это разрушило бы тело функции."""
    cursor.execute(text, prepare=False)
    while cursor.nextset():
        pass


def database_command(*, apply: bool, dsn_env: str = "COMMERCEGUARD_DATABASE_URL") -> MigrationReport:
    """status читает, migrate применяет весь pending-набор одним COMMIT.

    Соединение autocommit=True не создаёт неявной внешней транзакции. Единственный
    conn.transaction() ниже — настоящая граница атомарной смены схемы и журнала.
    При ошибке контекст откатывает её, включая первый CREATE SCHEMA.
    """
    available = load_migrations()
    bootstrap, _ = read_sql(SQL_ROOT / "bootstrap.sql")
    with postgres_session(dsn_env, application_name="commerceguard-migrate") as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                # READ COMMITTED нужен и после получения lock: новая команда
                # должна увидеть предыдущий завершённый мигратор, не старый snapshot.
                cursor.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
                if not apply:
                    cursor.execute("SET TRANSACTION READ ONLY")
                cursor.execute("SET LOCAL TIME ZONE 'UTC'")
                role = _check_target(cursor, apply=apply)
                cursor.execute("SELECT pg_try_advisory_xact_lock(%s, %s)", LOCK_KEY)
                if not cursor.fetchone()[0]:
                    raise MigrationError("Другой мигратор уже работает; повтори команду позже")
                exists = _namespace(cursor, role)
                current = _history(cursor, available) if exists else 0
                pending = available[current:]
                if apply:
                    if not exists:
                        _script(cursor, bootstrap)
                    for item in pending:
                        _script(cursor, item.sql)
                        cursor.execute(
                            "INSERT INTO commerceguard.schema_migration(version, name, checksum) "
                            "VALUES (%s, %s, %s)", (item.version, item.name, item.checksum),
                        )
                    # Ограничение только собственных объектов; не меняем public,
                    # роли, параметры кластера или чужие схемы.
                    cursor.execute("REVOKE ALL ON SCHEMA commerceguard FROM PUBLIC")
                    cursor.execute("REVOKE ALL ON ALL TABLES IN SCHEMA commerceguard FROM PUBLIC")
                    cursor.execute("REVOKE ALL ON ALL SEQUENCES IN SCHEMA commerceguard FROM PUBLIC")
                    cursor.execute("REVOKE ALL ON ALL FUNCTIONS IN SCHEMA commerceguard FROM PUBLIC")
                report = MigrationReport(
                    "migrate" if apply else "status", SCHEMA,
                    len(available) if apply else current, len(available),
                    tuple(item.name for item in pending) if apply else (),
                    () if apply else tuple(item.name for item in pending),
                )
        # Возвращаем success только после выхода из transaction(), то есть COMMIT.
        return report


def require_current_storage(cursor, *, write: bool = True) -> None:
    """Ingest не мигрирует неявно: owner/identity/история и весь schema version нужны заранее."""
    role = _check_target(cursor, apply=write)
    available = load_migrations()
    if not _namespace(cursor, role) or _history(cursor, available) != len(available):
        raise MigrationError("Сначала явно примени все миграции этого checkout через db migrate")
