"""Я замораживаю опубликованные входы и время, пока не выполняя расчёт сверки."""

from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from .domain import require_id, utc
from .file_contracts import canonical_time
from .ingestion import _locks
from .ingest_journal import schema_guard
from .migrations import require_current_storage
from .postgres import postgres_session
from .reconcile import RULESET_VERSION

MAX_PSP_INPUTS = 10000


class RunPlanError(ValueError):
    """Я возвращаю только фиксированную причину, без сумм и исходных строк."""


@dataclass(frozen=True, slots=True)
class RunInput:
    source: str
    batch_id: str
    snapshot_id: str | None
    manifest_sha256: str
    content_sha256: str


@dataclass(frozen=True, slots=True)
class PreparedRun:
    action: str
    run_id: str
    run_key: str
    state: str
    duplicate_manifest: bool
    input_count: int
    ruleset_version: str
    engine_sha256: str
    mode: str
    as_of: str
    knowledge_at: str
    reason: str
    baseline_run_id: str | None


def engine_sha256() -> str:
    """Я фиксирую точные байты своего kernel/selector, не импортируя файл как код."""
    root = Path(__file__).parent
    digests = []
    try:
        for name in ("domain.py", "file_contracts.py", "reconcile.py", "run_plans.py"):
            path = root / name
            if path.is_symlink() or not path.is_file():
                raise RunPlanError("ENGINE_SOURCE: нужен обычный исходный файл пакета")
            with path.open("rb") as stream:
                data = stream.read(256001)
            if not data or len(data) > 256000:
                raise RunPlanError("ENGINE_SIZE: исходник превышает предел fingerprint")
            digests.append([name, hashlib.sha256(data).hexdigest()])
    except OSError:
        raise RunPlanError("ENGINE_IO: не удалось прочитать исходники kernel") from None
    return hashlib.sha256(json.dumps(digests, separators=(",", ":")).encode("ascii")).hexdigest()


def _select_inputs(cursor, merchant_id: str, as_of: datetime, knowledge_at: datetime) -> tuple[RunInput, ...]:
    cursor.execute(
        "SELECT s.snapshot_id, s.batch_id, s.effective_at, s.observed_at, "
        "b.manifest_sha256, b.content_sha256 FROM commerceguard.core_oms_snapshot s "
        "JOIN commerceguard.ingest_batch b ON b.batch_id = s.batch_id "
        "WHERE s.merchant_id = %s AND s.is_complete AND b.state = 'published' "
        "AND s.effective_at <= %s AND s.observed_at <= %s AND b.published_at <= %s "
        "ORDER BY s.effective_at DESC, s.observed_at DESC, s.snapshot_id LIMIT 2",
        (merchant_id, as_of, knowledge_at, knowledge_at),
    )
    oms = cursor.fetchall()
    if not oms:
        raise RunPlanError("OMS_INPUT_MISSING: нет опубликованного полного снимка в выбранном времени")
    if len(oms) > 1 and oms[0][2:4] == oms[1][2:4]:
        raise RunPlanError("OMS_INPUT_AMBIGUOUS: два снимка имеют одинаковые effective/observed времена")
    snapshot_id, batch_id, _, _, manifest_hash, content_hash = oms[0]
    inputs = [RunInput("oms", str(batch_id), str(snapshot_id), manifest_hash, content_hash)]
    cursor.execute(
        "SELECT batch_id, manifest_sha256, content_sha256 FROM commerceguard.ingest_batch "
        "WHERE merchant_id = %s AND source = 'psp' AND state = 'published' "
        "AND published_at <= %s AND (manifest_json->>'observed_at')::timestamptz <= %s "
        "ORDER BY batch_id LIMIT %s", (merchant_id, knowledge_at, knowledge_at, MAX_PSP_INPUTS + 1),
    )
    psp = cursor.fetchall()
    if not psp:
        raise RunPlanError("PSP_INPUT_MISSING: отсутствие источника не считаю нулевой суммой")
    if len(psp) > MAX_PSP_INPUTS:
        raise RunPlanError("INPUT_LIMIT: слишком много PSP-пакетов для одного manifest")
    inputs.extend(RunInput("psp", str(batch), None, manifest_hash, content_hash)
                  for batch, manifest_hash, content_hash in psp)
    return tuple(inputs)


def prepare_run(merchant_id: str, as_of: datetime, *, mode: str = "as-was",
                knowledge_at: datetime | None = None,
                reason: str = "manual", baseline_run_id: str | None = None,
                dsn_env: str = "COMMERCEGUARD_DATABASE_URL") -> PreparedRun:
    """Я сохраняю immutable план с двумя временами и основанием пересчёта."""
    require_id(merchant_id, "merchant_id")
    cutoff = utc(as_of, "as_of")
    if mode not in ("as-was", "as-known-now"):
        raise RunPlanError("MODE: допустимы as-was/as-known-now")
    knowledge = utc(knowledge_at, "knowledge_at") if knowledge_at is not None else cutoff
    if knowledge < cutoff or (mode == "as-was" and knowledge != cutoff):
        raise RunPlanError("CUTOFF_ORDER: knowledge_at >= as_of, для as-was границы равны")
    if reason not in ("manual", "scheduled", "late-data", "recovery"):
        raise RunPlanError("RUN_REASON: нужен фиксированный reason code")
    baseline = None
    if mode == "as-known-now":
        if knowledge_at is None or baseline_run_id is None:
            raise RunPlanError("CORRECTION_CONTEXT: явно нужны knowledge_at и baseline_run_id")
        try:
            baseline = UUID(baseline_run_id)
        except (ValueError, AttributeError, TypeError):
            raise RunPlanError("BASELINE_ID: нужен UUID") from None
    elif baseline_run_id is not None or reason == "late-data":
        raise RunPlanError("CORRECTION_MODE: baseline/late-data относятся к as-known-now")
    engine = engine_sha256()
    with postgres_session(dsn_env, application_name="commerceguard-run-prepare") as connection:
        from psycopg.types.json import Jsonb

        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
                cursor.execute("SET LOCAL TIME ZONE 'UTC'")
                # Я использую тот же merchant lock, что ingestion: набор входов
                # стабилен между командами после получения lock в READ COMMITTED.
                _locks(cursor, merchant_id)
                require_current_storage(cursor)
                cursor.execute("SELECT clock_timestamp()")
                if knowledge > cursor.fetchone()[0]:
                    raise RunPlanError("FUTURE_KNOWLEDGE: не фиксирую будущее как уже известные данные")
                if baseline:
                    cursor.execute("SELECT m.merchant_id, m.as_of, m.knowledge_at FROM commerceguard.ops_run_manifest m "
                                   "JOIN commerceguard.ops_run_result r ON r.run_id = m.run_id WHERE m.run_id = %s",
                                   (baseline,))
                    previous = cursor.fetchone()
                    if not previous or previous[0] != merchant_id or previous[1] != cutoff or previous[2] >= knowledge:
                        raise RunPlanError("BASELINE_CONTEXT: нужен опубликованный run магазина с тем же as_of и меньшим knowledge_at")
                inputs = _select_inputs(cursor, merchant_id, cutoff, knowledge)
                manifest = {"manifest_version": 2, "knowledge_basis": "published-at-marker-v1",
                            "visibility_version": "occurred-observed-v2",
                            "request": {"reason": reason, "baseline_run_id": str(baseline) if baseline else None},
                            "merchant_id": merchant_id, "mode": mode,
                            "as_of": canonical_time(cutoff), "knowledge_at": canonical_time(knowledge),
                            "ruleset_version": RULESET_VERSION, "engine_sha256": engine,
                            "inputs": [asdict(item) for item in inputs]}
                text = json.dumps(manifest, sort_keys=True, ensure_ascii=True, separators=(",", ":")) + "\n"
                if len(text.encode("ascii")) > 5000000:
                    raise RunPlanError("MANIFEST_LIMIT: manifest превышает предел размера")
                key = hashlib.sha256(text.encode("ascii")).hexdigest()
                run_id = uuid5(NAMESPACE_URL, "commerceguard:run:v1:" + key)
                cursor.execute("SELECT run_id, manifest_text FROM commerceguard.ops_run_manifest WHERE run_key = %s",
                               (key,))
                old = cursor.fetchone()
                if old is not None:
                    if old != (run_id, text):
                        raise RunPlanError("RUN_IDENTITY: сохранённый manifest не совпадает с identity")
                    duplicate = True
                else:
                    duplicate = False
                    cursor.execute(
                        "INSERT INTO commerceguard.ops_run_manifest "
                        "(run_id, run_key, merchant_id, mode, as_of, knowledge_at, ruleset_version, "
                        "engine_sha256, input_count, manifest_text, manifest_json, reason_code, baseline_run_id) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (run_id, key, merchant_id, mode, cutoff, knowledge, RULESET_VERSION,
                         engine, len(inputs), text, Jsonb(manifest), reason, baseline),
                    )
                    for ordinal, item in enumerate(inputs, start=1):
                        cursor.execute(
                            "INSERT INTO commerceguard.ops_run_input "
                            "(run_id, merchant_id, ordinal, source, batch_id, snapshot_id, manifest_sha256, content_sha256) "
                            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                            (run_id, merchant_id, ordinal, item.source, UUID(item.batch_id),
                             UUID(item.snapshot_id) if item.snapshot_id else None,
                             item.manifest_sha256, item.content_sha256),
                        )
                    cursor.execute("SELECT count(*) FROM commerceguard.ops_run_input WHERE run_id = %s", (run_id,))
                    if cursor.fetchone()[0] != len(inputs):
                        raise RunPlanError("INPUT_COUNT: сохранён неполный список входов")
                report = PreparedRun("prepare", str(run_id), key, "prepared", duplicate,
                                     len(inputs), RULESET_VERSION, engine, mode, canonical_time(cutoff),
                                     canonical_time(knowledge), reason, str(baseline) if baseline else None)
        return report


def show_run(run_id: str, *, dsn_env: str = "COMMERCEGUARD_DATABASE_URL") -> dict:
    """Я показываю зафиксированный план, не вычисляю результат по текущей БД."""
    try:
        identity = UUID(run_id)
    except (ValueError, AttributeError):
        raise RunPlanError("RUN_ID: нужен корректный UUID") from None
    with postgres_session(dsn_env, application_name="commerceguard-run-show") as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
                schema_guard(cursor, write=False)
                cursor.execute("SELECT manifest_json, prepared_at FROM commerceguard.ops_run_manifest WHERE run_id = %s",
                               (identity,))
                row = cursor.fetchone()
    return {"action": "show-manifest", "run_id": str(identity), "found": row is not None,
            "manifest": row[0] if row else None, "prepared_at": canonical_time(row[1]) if row else None,
            "calculation_performed": False}
