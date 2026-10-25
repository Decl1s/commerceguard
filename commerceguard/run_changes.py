"""Я сравниваю сохранённые результаты, не запускаю kernel и не меняю Case."""

import hashlib
import json
from uuid import UUID

from .file_contracts import canonical_time
from .ingest_journal import schema_guard
from .postgres import postgres_session
from .run_execution import RunExecutionError


def _result(cursor, identity: UUID) -> dict:
    cursor.execute(
        "SELECT m.merchant_id, m.as_of, m.knowledge_at, m.mode, m.ruleset_version, "
        "m.baseline_run_id, m.reason_code, r.payload_text, r.payload_json, r.result_sha256, m.engine_sha256 "
        "FROM commerceguard.ops_run_manifest m JOIN commerceguard.ops_run_result r ON r.run_id = m.run_id "
        "WHERE m.run_id = %s", (identity,),
    )
    row = cursor.fetchone()
    if not row:
        raise RunExecutionError("CHANGES_PUBLISHED_RESULT_REQUIRED")
    if hashlib.sha256(row[7].encode("ascii")).hexdigest() != row[9] or json.loads(row[7]) != row[8]:
        raise RunExecutionError("CHANGES_RESULT_INTEGRITY")
    return dict(zip(("merchant_id", "as_of", "knowledge_at", "mode", "ruleset_version", "baseline_run_id",
                     "reason", "text", "payload", "result_sha256", "engine_sha256"), row))


def _inputs(cursor, identity: UUID) -> dict:
    cursor.execute("SELECT batch_id, source, snapshot_id, manifest_sha256, content_sha256 "
                   "FROM commerceguard.ops_run_input WHERE run_id = %s ORDER BY ordinal", (identity,))
    return {str(r[0]): {"batch_id": str(r[0]), "source": r[1], "snapshot_id": str(r[2]) if r[2] else None,
                       "manifest_sha256": r[3], "content_sha256": r[4]} for r in cursor.fetchall()}


def read_changes(run_id: str, *, limit: int = 50, dsn_env: str = "COMMERCEGUARD_DATABASE_URL") -> dict:
    try:
        identity = UUID(run_id)
    except (ValueError, AttributeError, TypeError):
        raise RunExecutionError("RUN_ID_INVALID") from None
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise RunExecutionError("CHANGES_VIEW_LIMIT")
    with postgres_session(dsn_env, application_name="commerceguard-run-changes") as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                schema_guard(cursor, write=False)
                current = _result(cursor, identity)
                baseline_id = current["baseline_run_id"]
                if current["mode"] != "as-known-now" or baseline_id is None:
                    raise RunExecutionError("CHANGES_CORRECTION_REQUIRED")
                previous = _result(cursor, baseline_id)
                if (current["merchant_id"] != previous["merchant_id"] or current["as_of"] != previous["as_of"] or
                        current["ruleset_version"] != previous["ruleset_version"] or
                        current["knowledge_at"] <= previous["knowledge_at"]):
                    raise RunExecutionError("CHANGES_BASELINE_CONTEXT")
                before = {f["case_key"]: f for f in previous["payload"]["findings"]}
                after = {f["case_key"]: f for f in current["payload"]["findings"]}
                if len(before) != len(previous["payload"]["findings"]) or len(after) != len(current["payload"]["findings"]):
                    raise RunExecutionError("CHANGES_DUPLICATE_FINDING")
                changes, counts = [], {"appeared": 0, "disappeared": 0, "changed": 0, "unchanged": 0}
                for key in sorted(set(before) | set(after)):
                    old, new = before.get(key), after.get(key)
                    kind = ("appeared" if old is None else "disappeared" if new is None else
                            "unchanged" if old == new else "changed")
                    counts[kind] += 1
                    if kind != "unchanged" and len(changes) < limit:
                        changes.append({"case_key": key, "kind": kind, "before": old, "after": new})
                old_inputs, new_inputs = _inputs(cursor, baseline_id), _inputs(cursor, identity)
                added = [new_inputs[k] for k in sorted(new_inputs.keys() - old_inputs.keys())]
                removed = [old_inputs[k] for k in sorted(old_inputs.keys() - new_inputs.keys())]
                # Я считаю видимость event отдельно от доставки ещё одного receipt того же event.
                receipts_from = (
                    " FROM commerceguard.ops_run_evidence e "
                    "JOIN commerceguard.core_payment_event p ON p.merchant_id = e.merchant_id "
                    "AND p.source_event_id = e.source_event_id "
                    "JOIN commerceguard.core_payment_receipt receipt ON receipt.batch_id = e.batch_id "
                    "AND receipt.raw_row_number = e.raw_row_number "
                    "JOIN commerceguard.ingest_batch b ON b.batch_id = e.batch_id "
                    "WHERE e.run_id = %s AND p.occurred_at <= %s AND receipt.observed_at <= %s "
                    "AND NOT EXISTS (SELECT 1 FROM commerceguard.ops_run_evidence old "
                    "JOIN commerceguard.core_payment_receipt old_receipt ON old_receipt.batch_id = old.batch_id "
                    "AND old_receipt.raw_row_number = old.raw_row_number "
                    "WHERE old.run_id = %s AND old.merchant_id = e.merchant_id "
                    "AND old.source_event_id = e.source_event_id AND old_receipt.observed_at <= %s)"
                )
                parameters = (identity, current["as_of"], current["knowledge_at"], baseline_id, previous["knowledge_at"])
                cursor.execute("SELECT count(*), count(DISTINCT e.source_event_id)" + receipts_from, parameters)
                receipt_count, event_count = cursor.fetchone()
                cursor.execute("SELECT e.source_event_id, e.batch_id, e.raw_row_number, e.record_sha256, "
                               "b.raw_object_key, p.occurred_at, receipt.observed_at" + receipts_from +
                               " ORDER BY e.source_event_id, e.batch_id, e.raw_row_number LIMIT %s",
                               (*parameters, limit),)
                receipts = cursor.fetchall()
    changed_count = sum(v for k, v in counts.items() if k != "unchanged")
    return {"action": "run_changes", "run_id": str(identity), "baseline_run_id": str(baseline_id),
            "merchant_id": current["merchant_id"], "as_of": canonical_time(current["as_of"]),
            "previous_knowledge_at": canonical_time(previous["knowledge_at"]),
            "knowledge_at": canonical_time(current["knowledge_at"]), "reason": current["reason"],
            "result_sha256": current["result_sha256"], "baseline_result_sha256": previous["result_sha256"],
            "engine_changed": current["engine_sha256"] != previous["engine_sha256"],
            "visibility_changed": current["payload"].get("visibility_version") != previous["payload"].get("visibility_version"),
            "finding_counts": counts, "findings": changes, "findings_truncated": changed_count > limit,
            "added_input_count": len(added), "removed_input_count": len(removed),
            "added_inputs": added[:limit], "removed_inputs": removed[:limit],
            "inputs_truncated": len(added) > limit or len(removed) > limit,
            "newly_visible_event_count": event_count, "newly_visible_receipt_count": receipt_count,
            "newly_visible_receipts": [{"source_event_id": r[0], "batch_id": str(r[1]), "row_number": r[2],
                                        "record_sha256": r[3], "raw_object_key": r[4],
                                        "occurred_at": canonical_time(r[5]), "observed_at": canonical_time(r[6])}
                                       for r in receipts],
            "receipts_truncated": receipt_count > limit, "cases_modified": False,
            "calculation_invoked": False}
