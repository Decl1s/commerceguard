"""Я сохраняю безопасный диагноз отдельно от откатываемой публикации. Не запускал."""

from dataclasses import dataclass
from uuid import UUID

from .file_contracts import COMMON_MANIFEST, OMS_COLUMNS, OMS_V2_COLUMNS, PSP_COLUMNS, FileInputError
from .migrations import LOCK_KEY, MigrationError, require_current_storage
from .postgres import DatabaseError, postgres_session
from .raw_store import RawStoreError


@dataclass(frozen=True, slots=True)
class Rejection:
    state: str
    category: str
    code: str
    row: int | None = None
    field: str | None = None


class PublicationFailure(ValueError):
    def __init__(self, attempt_id: UUID, rejection: Rejection, journal_status: str):
        self.attempt_id = str(attempt_id)
        self.rejection = rejection
        self.journal_status = journal_status
        location = f"; record={rejection.row}" if rejection.row is not None else ""
        super().__init__(f"{rejection.code}: {rejection.category}{location}; "
                         f"attempt_id={attempt_id}; journal={journal_status}")


def schema_guard(cursor, *, write: bool = True) -> None:
    """Я исключаю собственный мигратор, но не объявляю lock защитой от DBA."""
    cursor.execute("SELECT pg_try_advisory_xact_lock_shared(%s, %s)", LOCK_KEY)
    if not cursor.fetchone()[0]:
        raise MigrationError("Схема занята мигратором; повтори позже")
    require_current_storage(cursor, write=write)


def begin_attempt(connection, attempt_id, batch_id, manifest, artifacts) -> None:
    """Первый COMMIT подтверждает попытку; core я запишу следующей транзакцией."""
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL TIME ZONE 'UTC'")
            schema_guard(cursor)
            cursor.execute(
                "INSERT INTO commerceguard.ingest_attempt "
                "(attempt_id, batch_id, manifest_sha256, merchant_id, source, raw_object_key, "
                "manifest_object_key, state) VALUES (%s, %s, %s, %s, %s, %s, %s, 'started')",
                (attempt_id, batch_id, artifacts.manifest_sha256, manifest.merchant_id,
                 manifest.source, artifacts.raw_object_key, artifacts.manifest_object_key),
            )


def finish_success(cursor, attempt_id, batch_id, replay: bool) -> None:
    """Успешную попытку я завершаю тем же COMMIT, что фиксирует published batch."""
    cursor.execute(
        "UPDATE commerceguard.ingest_attempt SET state = %s, finished_at = clock_timestamp(), "
        "published_batch_id = %s WHERE attempt_id = %s AND state = 'started'",
        ("duplicate" if replay else "published", batch_id, attempt_id),
    )
    if cursor.rowcount != 1:
        raise MigrationError("Попытка приёма не находится в состоянии started")


def classify(error: BaseException) -> Rejection:
    """Я не сохраняю str(error): серверный DETAIL может включать исходные значения."""
    if isinstance(error, KeyboardInterrupt):
        return Rejection("unknown", "interrupted", "PROCESS_INTERRUPTED")
    if isinstance(error, FileInputError):
        infrastructure = error.code in {"IO_ERROR", "NOT_REGULAR_FILE", "STREAM_USED", "STREAM_INCOMPLETE"}
        business = error.code in {"OMS_DUPLICATE", "PSP_CONFLICT"}
        return Rejection("failed" if infrastructure else "quarantined",
                         "infrastructure" if infrastructure else "business" if business else "structural",
                         error.code, error.row, error.field)
    if isinstance(error, DatabaseError):
        # Даже если ошибка случилась до COMMIT, без подтверждения я не заявляю rollback.
        return Rejection("unknown", "infrastructure", "DATABASE_UNCONFIRMED")
    if isinstance(error, MigrationError):
        return Rejection("failed", "infrastructure", "STORAGE_NOT_READY")
    if isinstance(error, RawStoreError):
        return Rejection("failed", "infrastructure", "RAW_UNAVAILABLE")
    code = getattr(error, "code", None)
    if code in {"PSP_CONFLICT", "TEMPORAL_CONFLICT", "BATCH_CONFLICT"}:
        return Rejection("quarantined", "business", code, getattr(error, "row", None))
    if code in {"SCHEMA_BUSY", "MERCHANT_BUSY", "BATCH_NOT_PUBLISHED", "STAGE_COUNT", "PUBLISH_COUNT"}:
        return Rejection("failed", "infrastructure", code)
    return Rejection("unknown", "infrastructure", "UNEXPECTED_ERROR")


def record_rejection(attempt_id: UUID, rejection: Rejection, dsn_env: str) -> str:
    """Я пробую отдельное соединение; сбой журнала не заменяет исходную причину."""
    # Поля от decoder могут содержать имя неизвестного JSON-ключа. Я допускаю
    # только фиксированный набор имён полей и не сохраняю произвольные значения.
    field = rejection.field
    if field not in (COMMON_MANIFEST | set(OMS_COLUMNS) | set(OMS_V2_COLUMNS) | PSP_COLUMNS | {"effective_at", "is_complete"}):
        field = None
    row = rejection.row if type(rejection.row) is int and 1 <= rejection.row <= 1000001 else None
    try:
        with postgres_session(dsn_env, application_name="commerceguard-rejection") as connection:
            with connection.transaction():
                with connection.cursor() as cursor:
                    schema_guard(cursor)
                    cursor.execute(
                        "UPDATE commerceguard.ingest_attempt SET state = %s, category = %s, "
                        "error_code = %s, error_row = %s, error_field = %s, finished_at = clock_timestamp() "
                        "WHERE attempt_id = %s AND state = 'started'",
                        (rejection.state, rejection.category, rejection.code, row, field, attempt_id),
                    )
                    if cursor.rowcount == 1:
                        status = "recorded"
                    else:
                        cursor.execute("SELECT state FROM commerceguard.ingest_attempt WHERE attempt_id = %s",
                                       (attempt_id,))
                        status = "already_terminal" if cursor.fetchone() else "not_registered"
            return status
    except Exception:
        return "unavailable"
