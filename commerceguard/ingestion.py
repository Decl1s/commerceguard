"""CG-103: raw → полный поток COPY → одна публикация. Написано без запуска.

Приём не вызывает сверку и не меняет финансовые операции. Граница атомарности —
PostgreSQL, а не PostgreSQL вместе с filesystem. Raw сохраняется раньше транзакции.
"""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from .domain import OrderExpectation
from .file_inputs import InputRecord, open_input
from .migrations import LOCK_KEY, SQL_ROOT, _script, read_sql, require_current_storage
from .postgres import postgres_session
from .raw_store import RawArtifacts, RawStore
from .ingest_journal import PublicationFailure, begin_attempt, classify, finish_success, record_rejection


class PublicationError(ValueError):
    """Я сохраняю только код и ordinal, без конфликтующих значений."""

    def __init__(self, message: str, *, row: int | None = None):
        self.code = message.partition(":")[0]
        self.row = row
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class PublicationReport:
    action: str
    published: bool
    batch_id: str
    snapshot_id: str | None
    source: str
    merchant_id: str
    manifest_sha256: str
    content_sha256: str
    duplicate_batch: bool
    rows_parsed: int
    raw_rows_inserted: int
    new_facts: int
    known_events: int
    duplicate_rows: int
    raw_object_key: str
    manifest_object_key: str
    attempt_id: str


def _stage_row(record: InputRecord) -> tuple:
    """Порядок соответствует stage_input.sql и COPY, строки не склеиваются в SQL."""
    value = record.value
    prefix = (record.row_number, record.record_sha256, record.raw_text, record.semantic_sha256)
    if isinstance(value, OrderExpectation):
        return prefix + (None, value.order_id, value.currency, None, None,
                         value.capture_due_minor, value.refund_due_minor, value.settle_after, None, None)
    return prefix + (value.source_event_id, value.order_id, value.currency, value.kind.value,
                     value.amount_minor, None, None, None, value.occurred_at, value.observed_at)


def _locks(cursor, merchant_id: str) -> None:
    # Общая shared-блокировка мешает нашему мигратору менять DDL во время ingest.
    cursor.execute("SELECT pg_try_advisory_xact_lock_shared(%s, %s)", LOCK_KEY)
    if not cursor.fetchone()[0]:
        raise PublicationError("SCHEMA_BUSY: работает мигратор; повтори позже")
    # Отдельное bigint-пространство advisory lock; один merchant сериализован
    # между OMS и PSP, разные merchant могут загружаться независимо.
    digest = hashlib.sha256(("commerceguard:ingest:v1:" + merchant_id).encode("ascii")).digest()
    key = int.from_bytes(digest[:8], "big", signed=True)
    cursor.execute("SELECT pg_try_advisory_xact_lock(%s::bigint)", (key,))
    if not cursor.fetchone()[0]:
        raise PublicationError("MERCHANT_BUSY: пакет магазина уже загружается; повтори позже")


def _already_published(cursor, batch_id: UUID, manifest, artifacts: RawArtifacts, envelope) -> bool:
    cursor.execute(
        "SELECT batch_id, merchant_id, source, contract_version, content_sha256, "
        "declared_row_count, raw_byte_count, manifest_json, raw_object_key, manifest_object_key, "
        "state, parsed_row_count FROM commerceguard.ingest_batch WHERE manifest_sha256 = %s",
        (artifacts.manifest_sha256,),
    )
    row = cursor.fetchone()
    if row is None:
        return False
    expected = (batch_id, manifest.merchant_id, manifest.source, manifest.contract_version,
                manifest.content_sha256, manifest.row_count, manifest.byte_count, envelope,
                artifacts.raw_object_key, artifacts.manifest_object_key)
    if row[:10] != expected:
        raise PublicationError("BATCH_CONFLICT: identity пакета не совпадает с сохранёнными метаданными")
    if row[10:] != ("published", manifest.row_count):
        raise PublicationError("BATCH_NOT_PUBLISHED: требуется отдельное восстановление состояния")
    return True


def _prepare_psp(cursor, merchant_id: str) -> None:
    # Из равных бизнес-фактов нового пакета выбираем минимальный observed_at.
    # raw ordinal разрывает ничью; остальные поступления сохраняются в receipts.
    cursor.execute(
        "CREATE TEMP TABLE cg_stage_event ON COMMIT DROP AS "
        "SELECT DISTINCT ON (source_event_id) * FROM pg_temp.cg_stage_input "
        "ORDER BY source_event_id, observed_at, row_number"
    )
    cursor.execute(
        "SELECT s.row_number FROM pg_temp.cg_stage_event s "
        "JOIN commerceguard.core_payment_event e "
        "ON e.merchant_id = %s AND e.source_event_id = s.source_event_id "
        "WHERE (e.order_id, e.currency, e.kind, e.amount_minor, e.occurred_at, e.semantic_sha256) "
        "IS DISTINCT FROM (s.order_id, s.currency, s.kind, s.amount_minor, s.occurred_at, s.semantic_sha256) "
        "ORDER BY s.row_number LIMIT 1", (merchant_id,),
    )
    conflict = cursor.fetchone()
    if conflict:
        raise PublicationError(f"PSP_CONFLICT: иной смысл существующего события, запись {conflict[0]}", row=conflict[0])
    cursor.execute(
        "SELECT s.row_number FROM pg_temp.cg_stage_event s "
        "JOIN commerceguard.core_payment_event e "
        "ON e.merchant_id = %s AND e.source_event_id = s.source_event_id "
        "WHERE s.observed_at < e.observed_at ORDER BY s.row_number LIMIT 1", (merchant_id,),
    )
    conflict = cursor.fetchone()
    if conflict:
        raise PublicationError(f"TEMPORAL_CONFLICT: наблюдение раньше опубликованного, запись {conflict[0]}", row=conflict[0])


def _publish_oms(cursor, batch_id: UUID, snapshot_id: UUID, manifest) -> int:
    cursor.execute(
        "INSERT INTO commerceguard.core_oms_snapshot "
        "(snapshot_id, batch_id, merchant_id, effective_at, observed_at, is_complete) "
        "VALUES (%s, %s, %s, %s, %s, true)",
        (snapshot_id, batch_id, manifest.merchant_id, manifest.effective_at, manifest.observed_at),
    )
    cursor.execute(
        "INSERT INTO commerceguard.core_order_expectation "
        "(snapshot_id, batch_id, merchant_id, order_id, raw_row_number, currency, "
        "capture_due_minor, refund_due_minor, settle_after) "
        "SELECT %s, %s, %s, order_id, row_number, currency, "
        "capture_due_minor, refund_due_minor, settle_after FROM pg_temp.cg_stage_input",
        (snapshot_id, batch_id, manifest.merchant_id),
    )
    return cursor.rowcount


def _publish_psp(cursor, batch_id: UUID, merchant_id: str) -> int:
    cursor.execute(
        "INSERT INTO commerceguard.core_payment_event "
        "(merchant_id, source_event_id, order_id, batch_id, raw_row_number, currency, kind, "
        "amount_minor, occurred_at, observed_at, semantic_sha256) "
        "SELECT %s, s.source_event_id, s.order_id, %s, s.row_number, s.currency, s.kind, "
        "s.amount_minor, s.occurred_at, s.observed_at, s.semantic_sha256 "
        "FROM pg_temp.cg_stage_event s WHERE NOT EXISTS "
        "(SELECT 1 FROM commerceguard.core_payment_event e "
        "WHERE e.merchant_id = %s AND e.source_event_id = s.source_event_id)",
        (merchant_id, batch_id, merchant_id),
    )
    inserted = cursor.rowcount
    # Нет ON CONFLICT DO NOTHING: запись в обход cooperative lock должна
    # вызвать отказ транзакции, а не замаскировать конфликт под равный повтор.
    cursor.execute(
        "INSERT INTO commerceguard.core_payment_receipt "
        "(merchant_id, source_event_id, batch_id, raw_row_number, observed_at) "
        "SELECT %s, source_event_id, %s, row_number, observed_at FROM pg_temp.cg_stage_input",
        (merchant_id, batch_id),
    )
    return inserted


def _publish_input(
    manifest_path: Path, data_path: Path, raw_root: Path, *,
    dsn_env: str, attempt_id: UUID,
) -> PublicationReport:
    """Повтор того же envelope не добавляет ни batch, ни receipts, ни факты.

    Даже повтор полностью разбирается и проходит COPY до определения результата:
    нельзя принять prefix или довериться одному наличию имени объекта/hash в БД.
    """
    store = RawStore(raw_root)
    stage_sql, _ = read_sql(SQL_ROOT / "stage_input.sql")
    with open_input(manifest_path, data_path, snapshot_sink=store.persist) as batch:
        manifest = batch.manifest
        artifacts = store.describe(manifest)
        envelope = json.loads(artifacts.manifest_bytes)
        batch_id = uuid5(NAMESPACE_URL, "commerceguard:batch:v1:" + artifacts.manifest_sha256)
        snapshot_id = (uuid5(NAMESPACE_URL, "commerceguard:oms-snapshot:v1:" + artifacts.manifest_sha256)
                       if manifest.source == "oms" else None)
        with postgres_session(dsn_env, application_name="commerceguard-ingest",
                              statement_timeout_ms=120000) as connection:
            # Импорт только после проверки закреплённого драйвера в postgres_session.
            from psycopg.types.json import Jsonb

            begin_attempt(connection, attempt_id, batch_id, manifest, artifacts)
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
                    cursor.execute("SET LOCAL TIME ZONE 'UTC'")
                    _locks(cursor, manifest.merchant_id)
                    require_current_storage(cursor)
                    _script(cursor, stage_sql)
                    with cursor.copy(
                        "COPY pg_temp.cg_stage_input (row_number, record_sha256, record_text, "
                        "semantic_sha256, source_event_id, order_id, currency, kind, amount_minor, "
                        "capture_due_minor, refund_due_minor, settle_after, occurred_at, observed_at) FROM STDIN"
                    ) as copy:
                        for record in batch.records():
                            copy.write_row(_stage_row(record))
                    summary = batch.summary()  # Только после EOF и declared row_count.
                    cursor.execute("SELECT count(*) FROM pg_temp.cg_stage_input")
                    if cursor.fetchone()[0] != manifest.row_count:
                        raise PublicationError("STAGE_COUNT: staging не содержит полный пакет")
                    replay = _already_published(cursor, batch_id, manifest, artifacts, envelope)
                    new_facts = known_events = raw_rows = 0
                    if not replay:
                        if manifest.source == "psp":
                            _prepare_psp(cursor, manifest.merchant_id)
                        cursor.execute(
                            "INSERT INTO commerceguard.ingest_batch "
                            "(batch_id, merchant_id, source, contract_version, content_sha256, "
                            "declared_row_count, raw_byte_count, state, received_at, manifest_sha256, "
                            "manifest_json, raw_object_key, manifest_object_key) "
                            "VALUES (%s, %s, %s, %s, %s, %s, %s, 'received', transaction_timestamp(), %s, %s, %s, %s)",
                            (batch_id, manifest.merchant_id, manifest.source, manifest.contract_version,
                             manifest.content_sha256, manifest.row_count, manifest.byte_count,
                             artifacts.manifest_sha256, Jsonb(envelope), artifacts.raw_object_key,
                             artifacts.manifest_object_key),
                        )
                        cursor.execute(
                            "INSERT INTO commerceguard.ingest_raw_record "
                            "(batch_id, row_number, record_sha256, record_text) "
                            "SELECT %s, row_number, record_sha256, record_text FROM pg_temp.cg_stage_input", (batch_id,),
                        )
                        raw_rows = cursor.rowcount
                        cursor.execute("UPDATE commerceguard.ingest_batch SET state = 'staged' WHERE batch_id = %s",
                                       (batch_id,))
                        if manifest.source == "oms":
                            new_facts = _publish_oms(cursor, batch_id, snapshot_id, manifest)
                        else:
                            new_facts = _publish_psp(cursor, batch_id, manifest.merchant_id)
                            known_events = summary["unique_keys"] - new_facts
                        cursor.execute(
                            "UPDATE commerceguard.ingest_batch SET state = 'published', "
                            "published_at = clock_timestamp(), parsed_row_count = %s, "
                            "new_fact_count = %s, known_event_count = %s, duplicate_rows = %s "
                            "WHERE batch_id = %s AND state = 'staged'",
                            (manifest.row_count, new_facts, known_events, summary["duplicate_rows"], batch_id),
                        )
                        if cursor.rowcount != 1 or raw_rows != manifest.row_count:
                            raise PublicationError("PUBLISH_COUNT: переход состояния/число raw неверно")
                    finish_success(cursor, attempt_id, batch_id, replay)
                    report = PublicationReport(
                        "publish", True, str(batch_id), str(snapshot_id) if snapshot_id else None,
                        manifest.source, manifest.merchant_id, artifacts.manifest_sha256,
                        manifest.content_sha256, replay, manifest.row_count, raw_rows,
                        new_facts, known_events, summary["duplicate_rows"],
                        artifacts.raw_object_key, artifacts.manifest_object_key, str(attempt_id),
                    )
            # Только здесь COMMIT подтверждён драйвером. Потеря ответа — unknown,
            # а не доказательство rollback; повтор идентичного пакета разрешён.
        return report


def publish_input(
    manifest_path: Path, data_path: Path, raw_root: Path, *,
    dsn_env: str = "COMMERCEGUARD_DATABASE_URL",
) -> PublicationReport:
    """Я создаю новую попытку для каждого вызова, сохраняя identity бизнес-пакета."""
    attempt_id = uuid4()
    try:
        return _publish_input(manifest_path, data_path, raw_root, dsn_env=dsn_env, attempt_id=attempt_id)
    except (Exception, KeyboardInterrupt) as error:
        rejection = classify(error)
        status = record_rejection(attempt_id, rejection, dsn_env)
        raise PublicationFailure(attempt_id, rejection, status) from None
