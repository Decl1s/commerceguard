"""Я читаю метаданные пакета и попыток одним снимком, без raw payload."""

import re
from uuid import UUID, NAMESPACE_URL, uuid5

from .file_contracts import canonical_time
from .ingest_journal import schema_guard
from .postgres import postgres_session


class StatusError(ValueError):
    pass


def _uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        raise StatusError("Нужен корректный UUID пакета или попытки") from None


def _record(columns: tuple[str, ...], row: tuple) -> dict:
    value = dict(zip(columns, row, strict=True))
    for key, item in value.items():
        if isinstance(item, UUID):
            value[key] = str(item)
        elif key.endswith("_at") and item is not None:
            value[key] = canonical_time(item)
    return value


def ingest_status(*, batch_id: str | None = None, attempt_id: str | None = None,
                  manifest_sha256: str | None = None, limit: int = 20,
                  dsn_env: str = "COMMERCEGUARD_DATABASE_URL") -> dict:
    """Я отделяю not_found от состояния failed, а текущий batch — от старой попытки."""
    if sum(value is not None for value in (batch_id, attempt_id, manifest_sha256)) != 1:
        raise StatusError("Выбери ровно один из batch-id, attempt-id или manifest-sha")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise StatusError("Предел истории попыток — от 1 до 100")
    selected_attempt = _uuid(attempt_id) if attempt_id is not None else None
    selected_batch = _uuid(batch_id) if batch_id is not None else None
    if manifest_sha256 is not None:
        if re.fullmatch(r"[a-f0-9]{64}", manifest_sha256) is None:
            raise StatusError("Нужен SHA-256 manifest в нижнем регистре")
        selected_batch = uuid5(NAMESPACE_URL, "commerceguard:batch:v1:" + manifest_sha256)
    batch_columns = ("batch_id", "merchant_id", "source", "state", "manifest_sha256", "content_sha256",
                     "declared_row_count", "parsed_row_count", "new_fact_count", "known_event_count",
                     "duplicate_rows", "received_at", "published_at")
    attempt_columns = ("attempt_id", "batch_id", "state", "category", "error_code", "error_row",
                       "error_field", "started_at", "finished_at")
    with postgres_session(dsn_env, application_name="commerceguard-status") as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                cursor.execute("SET LOCAL TIME ZONE 'UTC'")
                schema_guard(cursor, write=False)
                if selected_attempt is not None:
                    cursor.execute("SELECT batch_id FROM commerceguard.ingest_attempt WHERE attempt_id = %s",
                                   (selected_attempt,))
                    row = cursor.fetchone()
                    if row:
                        selected_batch = row[0]
                cursor.execute(
                    "SELECT batch_id, merchant_id, source, state, manifest_sha256, content_sha256, "
                    "declared_row_count, parsed_row_count, new_fact_count, known_event_count, duplicate_rows, "
                    "received_at, published_at FROM commerceguard.ingest_batch WHERE batch_id = %s",
                    (selected_batch,),
                )
                row = cursor.fetchone()
                batch = _record(batch_columns, row) if row else None
                # Имена SQL фиксированы; выбор фильтра не включает пользовательский SQL.
                predicate = "attempt_id = %s" if selected_attempt is not None else "batch_id = %s"
                cursor.execute(
                    "SELECT attempt_id, batch_id, state, category, error_code, error_row, error_field, "
                    "started_at, finished_at FROM commerceguard.ingest_attempt WHERE " + predicate +
                    " ORDER BY started_at DESC, attempt_id DESC LIMIT %s",
                    (selected_attempt if selected_attempt is not None else selected_batch, limit + 1),
                )
                rows = cursor.fetchall()
    return {"action": "status", "found": batch is not None or bool(rows), "batch": batch,
            "attempts": [_record(attempt_columns, row) for row in rows[:limit]],
            "attempts_truncated": len(rows) > limit, "database_actions": "read_only"}
