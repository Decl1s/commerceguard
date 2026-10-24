"""Я считаю только закреплённые входы и публикую весь результат одним COMMIT."""

from collections import Counter
from dataclasses import asdict
import hashlib
import json
import re
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from .domain import ContractError, EventKind, OrderExpectation, PaymentEvent, require_id
from .file_contracts import canonical_time, semantic_sha256, timestamp
from .ingest_journal import schema_guard
from .postgres import DatabaseError, postgres_session
from .reconcile import RULESET_VERSION, reconcile
from .run_plans import engine_sha256

MAX_ORDERS = 10000
MAX_RECEIPTS = 50000
MAX_RESULT_BYTES = 16777216


class RunExecutionError(ValueError):
    def __init__(self, code: str, *, attempt_id: UUID | None = None,
                 journal_status: str | None = None, interrupted: bool = False):
        self.code = code
        self.attempt_id = str(attempt_id) if attempt_id else None
        self.journal_status = journal_status
        self.interrupted = interrupted
        detail = f"; attempt_id={attempt_id}; journal={journal_status}" if attempt_id else ""
        super().__init__(code + detail)


def _identity(value: str) -> UUID:
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        raise RunExecutionError("RUN_ID_INVALID") from None


def _manifest(cursor, run_id: UUID) -> tuple[dict, list[tuple]]:
    cursor.execute("SELECT run_key, manifest_text, manifest_json, input_count "
                   "FROM commerceguard.ops_run_manifest WHERE run_id = %s", (run_id,))
    row = cursor.fetchone()
    if not row:
        raise RunExecutionError("RUN_NOT_FOUND")
    key, text, manifest, count = row
    if (hashlib.sha256(text.encode("ascii")).hexdigest() != key or
            uuid5(NAMESPACE_URL, "commerceguard:run:v1:" + key) != run_id or
            json.loads(text) != manifest or manifest.get("ruleset_version") != RULESET_VERSION or
            manifest.get("engine_sha256") != engine_sha256() or
            manifest.get("mode") != "as-was" or manifest.get("manifest_version") != 1 or
            manifest.get("knowledge_basis") != "published-at-marker-v1"):
        raise RunExecutionError("MANIFEST_OR_ENGINE_MISMATCH")
    cursor.execute(
        "SELECT i.source, i.batch_id, i.snapshot_id, i.manifest_sha256, i.content_sha256, "
        "b.declared_row_count FROM commerceguard.ops_run_input i "
        "JOIN commerceguard.ingest_batch b ON b.batch_id = i.batch_id "
        "WHERE i.run_id = %s AND b.state = 'published' AND i.merchant_id = b.merchant_id "
        "AND i.source = b.source AND i.manifest_sha256 = b.manifest_sha256 "
        "AND i.content_sha256 = b.content_sha256 ORDER BY i.ordinal", (run_id,),
    )
    inputs = cursor.fetchall()
    actual = [dict(source=r[0], batch_id=str(r[1]), snapshot_id=str(r[2]) if r[2] else None,
                   manifest_sha256=r[3], content_sha256=r[4]) for r in inputs]
    if len(inputs) != count or actual != manifest.get("inputs") or sum(r[0] == "oms" for r in inputs) != 1:
        raise RunExecutionError("INPUT_MANIFEST_MISMATCH")
    return manifest, inputs


def _load_inputs(cursor, run_id: UUID, manifest: dict, inputs: list[tuple]):
    oms = next(r for r in inputs if r[0] == "oms")
    psp_counts = {r[1]: r[5] for r in inputs if r[0] == "psp"}
    if not psp_counts or oms[5] > MAX_ORDERS or sum(psp_counts.values()) > MAX_RECEIPTS:
        raise RunExecutionError("EXECUTION_INPUT_LIMIT")
    cursor.execute(
        "SELECT merchant_id, order_id, currency, capture_due_minor, refund_due_minor, settle_after "
        "FROM commerceguard.core_order_expectation WHERE snapshot_id = %s "
        "ORDER BY merchant_id, order_id LIMIT %s", (oms[2], MAX_ORDERS + 1),
    )
    orders = tuple(OrderExpectation(*row) for row in cursor.fetchall())
    if len(orders) != oms[5] or any(o.merchant_id != manifest["merchant_id"] for o in orders):
        raise RunExecutionError("OMS_ROW_COUNT")
    cursor.execute(
        "SELECT e.merchant_id, e.source_event_id, e.order_id, e.currency, e.kind, e.amount_minor, "
        "e.occurred_at, r.observed_at, r.batch_id, r.raw_row_number, raw.record_sha256, e.semantic_sha256 "
        "FROM commerceguard.ops_run_input i "
        "JOIN commerceguard.core_payment_receipt r ON r.batch_id = i.batch_id AND r.merchant_id = i.merchant_id "
        "JOIN commerceguard.core_payment_event e ON e.merchant_id = r.merchant_id AND e.source_event_id = r.source_event_id "
        "JOIN commerceguard.ingest_raw_record raw ON raw.batch_id = r.batch_id AND raw.row_number = r.raw_row_number "
        "WHERE i.run_id = %s AND i.source = 'psp' ORDER BY r.batch_id, r.raw_row_number LIMIT %s",
        (run_id, MAX_RECEIPTS + 1),
    )
    rows = cursor.fetchall()
    counts = Counter(row[8] for row in rows)
    if len(rows) > MAX_RECEIPTS or any(counts[batch] != count for batch, count in psp_counts.items()):
        raise RunExecutionError("PSP_RECEIPT_COUNT")
    events, evidence = [], []
    for row in rows:
        event = PaymentEvent(*row[:4], EventKind(row[4]), *row[5:8])
        if event.merchant_id != manifest["merchant_id"] or semantic_sha256(event) != row[11]:
            raise RunExecutionError("PSP_SEMANTIC_MISMATCH")
        events.append(event)
        evidence.append((run_id, row[0], row[1], row[8], row[9], row[10]))
    return oms[2], orders, events, evidence


def _finish(cursor, attempt_id: UUID, state: str) -> None:
    cursor.execute("UPDATE commerceguard.ops_run_attempt SET state = %s, finished_at = clock_timestamp() "
                   "WHERE attempt_id = %s AND state = 'started'", (state, attempt_id))
    if cursor.rowcount != 1:
        raise RunExecutionError("ATTEMPT_NOT_STARTED")


def _failure(attempt_id: UUID, error: BaseException, dsn_env: str) -> str:
    state = "failed" if isinstance(error, (RunExecutionError, ContractError)) else "unknown"
    code = (error.code if isinstance(error, RunExecutionError) else
            "CONTRACT_REJECTED" if isinstance(error, ContractError) else "EXECUTION_UNCONFIRMED")
    try:
        with postgres_session(dsn_env, application_name="commerceguard-run-failure") as connection:
            with connection.transaction():
                with connection.cursor() as cursor:
                    schema_guard(cursor)
                    cursor.execute("UPDATE commerceguard.ops_run_attempt SET state = %s, error_code = %s, "
                                   "finished_at = clock_timestamp() WHERE attempt_id = %s AND state = 'started'",
                                   (state, code, attempt_id))
                    saved = cursor.rowcount == 1
            return "recorded" if saved else "not_started_or_terminal"
    except Exception:
        return "unavailable"


def execute_run(run_id: str, *, dsn_env: str = "COMMERCEGUARD_DATABASE_URL") -> dict:
    identity = _identity(run_id)
    attempt_id = uuid4()
    try:
        with postgres_session(dsn_env, application_name="commerceguard-run-execute",
                              statement_timeout_ms=120000) as connection:
            from psycopg.types.json import Jsonb

            with connection.transaction():
                with connection.cursor() as cursor:
                    schema_guard(cursor)
                    manifest, inputs = _manifest(cursor, identity)
                    cursor.execute("INSERT INTO commerceguard.ops_run_attempt(attempt_id, run_id, state) "
                                   "VALUES (%s, %s, 'started')", (attempt_id, identity))
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                    schema_guard(cursor, write=False)
                    snapshot_id, orders, events, evidence = _load_inputs(cursor, identity, manifest, inputs)
            # Я не держу idle transaction, пока Python считает ограниченный набор.
            cutoff = timestamp(manifest["as_of"], artifact="run", field="as_of")
            result = reconcile(orders, events, as_of=cutoff)
            if engine_sha256() != manifest["engine_sha256"]:
                raise RunExecutionError("ENGINE_CHANGED_DURING_RUN")
            payload = asdict(result)
            payload["as_of"] = canonical_time(result.as_of)
            text = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
            if len(text.encode("ascii")) > MAX_RESULT_BYTES or len(result.findings) > 100000:
                raise RunExecutionError("RESULT_SIZE_LIMIT")
            digest = hashlib.sha256(text.encode("ascii")).hexdigest()
            # Отдельный fingerprint адаптера дополняет kernel hash immutable manifest.
            executor_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            with connection.transaction():
                with connection.cursor() as cursor:
                    schema_guard(cursor)
                    key = int.from_bytes(hashlib.sha256(("commerceguard:run-publish:v1:" + str(identity)).encode()).digest()[:8],
                                         "big", signed=True)
                    cursor.execute("SELECT pg_try_advisory_xact_lock(%s::bigint)", (key,))
                    if not cursor.fetchone()[0]:
                        raise RunExecutionError("RUN_BUSY")
                    cursor.execute("SELECT result_sha256 FROM commerceguard.ops_run_result WHERE run_id = %s", (identity,))
                    old = cursor.fetchone()
                    duplicate = old is not None
                    if old and old[0] != digest:
                        raise RunExecutionError("RESULT_IDENTITY_CONFLICT")
                    if not duplicate:
                        cursor.execute(
                            "INSERT INTO commerceguard.ops_run_result "
                            "(run_id, attempt_id, merchant_id, oms_snapshot_id, result_version, result_sha256, "
                            "executor_sha256, payload_text, payload_json, balance_count, finding_count, evidence_count) "
                            "VALUES (%s, %s, %s, %s, 1, %s, %s, %s, %s, %s, %s, %s)",
                            (identity, attempt_id, manifest["merchant_id"], snapshot_id, digest, executor_hash,
                             text, Jsonb(payload), len(result.balances), len(result.findings), len(evidence)),
                        )
                        if evidence:
                            cursor.executemany("INSERT INTO commerceguard.ops_run_evidence "
                                               "(run_id, merchant_id, source_event_id, batch_id, raw_row_number, record_sha256) "
                                               "VALUES (%s, %s, %s, %s, %s, %s)", evidence)
                        cursor.execute("SELECT count(*) FROM commerceguard.ops_run_evidence WHERE run_id = %s", (identity,))
                        if cursor.fetchone()[0] != len(evidence):
                            raise RunExecutionError("EVIDENCE_COUNT")
                    _finish(cursor, attempt_id, "duplicate" if duplicate else "published")
            return {"action": "execute", "run_id": str(identity), "attempt_id": str(attempt_id),
                    "published": True, "duplicate_result": duplicate, "result_sha256": digest,
                    "balances": len(result.balances), "findings": len(result.findings), "evidence_rows": len(evidence)}
    except (Exception, KeyboardInterrupt) as error:
        status = _failure(attempt_id, error, dsn_env)
        code = error.code if isinstance(error, RunExecutionError) else "EXECUTION_UNCONFIRMED"
        raise RunExecutionError(code, attempt_id=attempt_id, journal_status=status,
                                interrupted=isinstance(error, KeyboardInterrupt)) from None


def read_result(run_id: str, *, limit: int = 50, dsn_env: str = "COMMERCEGUARD_DATABASE_URL") -> dict:
    identity = _identity(run_id)
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise RunExecutionError("RESULT_VIEW_LIMIT")
    with postgres_session(dsn_env, application_name="commerceguard-run-result") as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
                schema_guard(cursor, write=False)
                cursor.execute("SELECT payload_json, result_sha256, published_at FROM commerceguard.ops_run_result "
                               "WHERE run_id = %s", (identity,))
                row = cursor.fetchone()
    if not row:
        return {"action": "result", "run_id": str(identity), "found": False}
    payload = row[0]
    balances, findings = payload.pop("balances"), payload.pop("findings")
    return {"action": "result", "run_id": str(identity), "found": True, "result_sha256": row[1],
            "published_at": canonical_time(row[2]), "summary": payload,
            "balances": balances[:limit], "findings": findings[:limit],
            "balances_truncated": len(balances) > limit, "findings_truncated": len(findings) > limit}


def read_evidence(run_id: str, *, case_key: str | None = None, order_id: str | None = None,
                  limit: int = 50, dsn_env: str = "COMMERCEGUARD_DATABASE_URL") -> dict:
    """Я показываю источник ожидания и receipt refs, не раскрывая raw_text в CLI."""
    identity = _identity(run_id)
    if (case_key is None) == (order_id is None) or type(limit) is not int or not 1 <= limit <= 1000:
        raise RunExecutionError("EVIDENCE_SELECTOR")
    if case_key is not None and re.fullmatch(r"[a-f0-9]{64}", case_key) is None:
        raise RunExecutionError("CASE_KEY_INVALID")
    if order_id is not None:
        require_id(order_id, "order_id")
    with postgres_session(dsn_env, application_name="commerceguard-evidence") as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                schema_guard(cursor, write=False)
                cursor.execute("SELECT payload_json FROM commerceguard.ops_run_result WHERE run_id = %s", (identity,))
                row = cursor.fetchone()
                if not row:
                    return {"action": "evidence", "run_id": str(identity), "found": False}
                event_ids = None
                if case_key is not None:
                    finding = next((f for f in row[0]["findings"] if f["case_key"] == case_key), None)
                    if finding is None:
                        return {"action": "evidence", "run_id": str(identity), "found": False}
                    order_id = finding["order_id"]
                    event_ids = finding["evidence_event_ids"]
                cursor.execute(
                    "SELECT o.batch_id, o.raw_row_number, raw.record_sha256, b.raw_object_key "
                    "FROM commerceguard.ops_run_result r JOIN commerceguard.core_order_expectation o "
                    "ON o.snapshot_id = r.oms_snapshot_id AND o.merchant_id = r.merchant_id "
                    "JOIN commerceguard.ingest_raw_record raw ON raw.batch_id = o.batch_id AND raw.row_number = o.raw_row_number "
                    "JOIN commerceguard.ingest_batch b ON b.batch_id = o.batch_id "
                    "WHERE r.run_id = %s AND o.order_id = %s", (identity, order_id),
                )
                oms = cursor.fetchone()
                predicate = "e.source_event_id = ANY(%s::text[])" if event_ids is not None else "p.order_id = %s"
                cursor.execute(
                    "SELECT e.source_event_id, e.batch_id, e.raw_row_number, e.record_sha256, b.raw_object_key "
                    "FROM commerceguard.ops_run_evidence e JOIN commerceguard.ingest_batch b ON b.batch_id = e.batch_id "
                    "JOIN commerceguard.core_payment_event p ON p.merchant_id = e.merchant_id AND p.source_event_id = e.source_event_id "
                    "WHERE e.run_id = %s AND " + predicate + " ORDER BY e.batch_id, e.raw_row_number LIMIT %s",
                    (identity, event_ids if event_ids is not None else order_id, limit + 1),
                )
                receipts = cursor.fetchall()
    def ref(item, *, event=False):
        offset = 1 if event else 0
        data = {"batch_id": str(item[offset]), "row_number": item[offset+1],
                "record_sha256": item[offset+2], "raw_object_key": item[offset+3]}
        if event:
            data["source_event_id"] = item[0]
        return data
    return {"action": "evidence", "run_id": str(identity), "found": bool(oms or receipts) or case_key is not None,
            "order_id": order_id, "case_key": case_key, "oms": ref(oms) if oms else None,
            "psp_receipts": [ref(item, event=True) for item in receipts[:limit]],
            "receipts_truncated": len(receipts) > limit}
