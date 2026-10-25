"""Я проецирую опубликованные результаты в карточки явно и атомарно."""

import hashlib
import json
from pathlib import Path
from uuid import UUID

from .case_projection import CaseError, MAX_CASES, case_key, finding_snapshots, transition
from .domain import require_id
from .file_contracts import canonical_time
from .ingest_journal import schema_guard
from .postgres import postgres_session

POLICY = "canonical-as-was-v1"


def _uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except (ValueError, AttributeError, TypeError):
        raise CaseError("RUN_ID_INVALID") from None


def _limit(value: int, maximum: int) -> None:
    if type(value) is not int or not 1 <= value <= maximum:
        raise CaseError("CASE_VIEW_LIMIT")


def _projector_sha() -> str:
    digest = hashlib.sha256()
    for name in ("case_projection.py", "case_store.py"):
        digest.update(name.encode("ascii") + b"\0")
        digest.update(Path(__file__).with_name(name).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def apply_cases(run_id: str, *, dsn_env: str = "COMMERCEGUARD_DATABASE_URL") -> dict:
    """Я не выбираю latest run и не совмещаю вычисление с продвижением карточек."""
    identity = _uuid(run_id)
    with postgres_session(dsn_env, application_name="commerceguard-case-apply",
                          statement_timeout_ms=120000) as connection:
        from psycopg.types.json import Jsonb

        with connection.transaction():
            with connection.cursor() as cursor:
                schema_guard(cursor)
                cursor.execute(
                    "SELECT r.merchant_id, m.as_of, m.knowledge_at, m.ruleset_version, m.mode, "
                    "r.payload_text, r.payload_json, r.result_sha256, r.finding_count "
                    "FROM commerceguard.ops_run_result r JOIN commerceguard.ops_run_manifest m "
                    "ON m.run_id = r.run_id WHERE r.run_id = %s", (identity,),
                )
                result = cursor.fetchone()
                if not result:
                    raise CaseError("PUBLISHED_RESULT_REQUIRED")
                merchant, cutoff, knowledge, ruleset, mode, text, payload, digest, count = result
                key = int.from_bytes(hashlib.sha256(("commerceguard:case-stream:v1:" + merchant).encode()).digest()[:8],
                                     "big", signed=True)
                cursor.execute("SELECT pg_try_advisory_xact_lock(%s::bigint)", (key,))
                if not cursor.fetchone()[0]:
                    raise CaseError("CASE_STREAM_BUSY")
                cursor.execute("SELECT current_run_id, generation FROM commerceguard.ops_case_stream "
                               "WHERE merchant_id = %s", (merchant,))
                stream = cursor.fetchone()
                cursor.execute("SELECT generation, revision_count, case_count FROM commerceguard.ops_case_application "
                               "WHERE run_id = %s", (identity,))
                applied = cursor.fetchone()
                if applied:
                    return {"action": "case_apply", "run_id": str(identity), "already_applied": True,
                            "is_current": bool(stream and stream[0] == identity), "generation": applied[0],
                            "revision_count": applied[1], "case_count": applied[2]}
                if mode == "as-known-now":
                    raise CaseError("CASE_CORRECTION_REPORT_ONLY")
                if mode != "as-was" or knowledge != cutoff or ruleset != "balance-v1":
                    raise CaseError("CASE_POLICY_UNSUPPORTED")
                if stream:
                    cursor.execute("SELECT as_of, knowledge_at, ruleset_version FROM commerceguard.ops_run_manifest "
                                   "WHERE run_id = %s", (stream[0],))
                    previous_cutoff, previous_knowledge, previous_ruleset = cursor.fetchone()
                    if ruleset != previous_ruleset:
                        raise CaseError("CASE_RULESET_MIGRATION_REQUIRED")
                    if cutoff == previous_cutoff and knowledge == previous_knowledge:
                        raise CaseError("CANONICAL_TIME_TIE")
                    if cutoff <= previous_cutoff or knowledge < previous_knowledge:
                        raise CaseError("CANONICAL_RUN_REGRESSION")
                if (hashlib.sha256(text.encode("ascii")).hexdigest() != digest or json.loads(text) != payload or
                        payload.get("as_of") != canonical_time(cutoff) or payload.get("ruleset_version") != ruleset or
                        payload.get("mode", mode) != mode or
                        payload.get("knowledge_at", canonical_time(knowledge)) != canonical_time(knowledge)):
                    raise CaseError("CASE_RESULT_INTEGRITY")
                findings = finding_snapshots(payload, merchant)
                if len(findings) != count:
                    raise CaseError("CASE_FINDING_COUNT")
                cursor.execute(
                    "SELECT c.case_key, c.order_id, c.currency, c.rule_code, c.finding_state, c.revision_number, "
                    "c.first_run_id, c.last_seen_run_id, r.finding_sha256 FROM commerceguard.ops_case c "
                    "JOIN commerceguard.ops_case_revision r ON r.case_key = c.case_key "
                    "AND r.revision_number = c.revision_number WHERE c.merchant_id = %s "
                    "ORDER BY c.case_key LIMIT %s", (merchant, MAX_CASES + 1),
                )
                old_cases = {row[0]: row for row in cursor.fetchall()}
                all_keys = sorted(set(old_cases) | set(findings))
                if len(all_keys) > MAX_CASES:
                    raise CaseError("CASE_PROJECTION_LIMIT")
                heads, revisions, events = [], [], []
                for finding_key in all_keys:
                    old, current = old_cases.get(finding_key), findings.get(finding_key)
                    if old and current and old[1:4] != (current.order_id, current.currency, current.rule):
                        raise CaseError("CASE_IDENTITY_CONFLICT")
                    event = transition(old[4] if old else None, old[8] if old else None, current)
                    revision = (old[5] if old else 0) + (1 if event else 0)
                    state = "present" if current else "absent"
                    order, currency, rule = (current.order_id, current.currency, current.rule) if current else old[1:4]
                    heads.append((finding_key, merchant, order, currency, rule, state,
                                  old[6] if old else identity, identity if current else old[7], identity, revision))
                    if event:
                        revisions.append((finding_key, merchant, revision, identity, state,
                                          current.sha256 if current else None,
                                          Jsonb(json.loads(current.text)) if current else None))
                        events.append((finding_key, revision, event))
                generation = stream[1] + 1 if stream else 1
                cursor.execute(
                    "INSERT INTO commerceguard.ops_case_application "
                    "(run_id, merchant_id, generation, previous_run_id, policy, projector_sha256, revision_count, case_count) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (identity, merchant, generation, stream[0] if stream else None, POLICY,
                     _projector_sha(), len(revisions), len(heads)),
                )
                # Я откладываю circular FK до COMMIT: сначала heads, затем immutable revisions.
                if heads:
                    cursor.executemany(
                        "INSERT INTO commerceguard.ops_case (case_key, merchant_id, order_id, currency, rule_code, "
                        "finding_state, first_run_id, last_seen_run_id, evaluated_run_id, revision_number) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                        "ON CONFLICT (case_key) DO UPDATE SET finding_state = EXCLUDED.finding_state, "
                        "last_seen_run_id = EXCLUDED.last_seen_run_id, evaluated_run_id = EXCLUDED.evaluated_run_id, "
                        "revision_number = EXCLUDED.revision_number WHERE ops_case.merchant_id = EXCLUDED.merchant_id",
                        heads,
                    )
                if revisions:
                    cursor.executemany("INSERT INTO commerceguard.ops_case_revision "
                                       "(case_key, merchant_id, revision_number, run_id, finding_state, finding_sha256, finding_json) "
                                       "VALUES (%s, %s, %s, %s, %s, %s, %s)", revisions)
                    cursor.executemany("INSERT INTO commerceguard.ops_case_event(case_key, revision_number, event_kind) "
                                       "VALUES (%s, %s, %s)", events)
                cursor.execute("INSERT INTO commerceguard.ops_case_stream(merchant_id, current_run_id, generation) "
                               "VALUES (%s, %s, %s) ON CONFLICT (merchant_id) DO UPDATE "
                               "SET current_run_id = EXCLUDED.current_run_id, generation = EXCLUDED.generation",
                               (merchant, identity, generation))
        return {"action": "case_apply", "run_id": str(identity), "merchant_id": merchant,
                "already_applied": False, "is_current": True, "generation": generation,
                "revision_count": len(revisions), "case_count": len(heads), "policy": POLICY}


def list_cases(merchant: str, *, presence: str = "present", after: str | None = None,
               limit: int = 50, dsn_env: str = "COMMERCEGUARD_DATABASE_URL") -> dict:
    require_id(merchant, "merchant_id")
    _limit(limit, 100)
    if presence not in ("present", "absent", "all"):
        raise CaseError("CASE_PRESENCE_INVALID")
    if after is not None:
        case_key(after)
    with postgres_session(dsn_env, application_name="commerceguard-case-list") as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                schema_guard(cursor, write=False)
                cursor.execute("SELECT current_run_id, generation FROM commerceguard.ops_case_stream "
                               "WHERE merchant_id = %s", (merchant,))
                stream = cursor.fetchone()
                cursor.execute(
                    "SELECT case_key, order_id, currency, rule_code, finding_state, workflow_status, revision_number, "
                    "evaluated_run_id, last_seen_run_id FROM commerceguard.ops_case WHERE merchant_id = %s "
                    "AND (%s = 'all' OR finding_state = %s) AND case_key > %s ORDER BY case_key LIMIT %s",
                    (merchant, presence, presence, after or "", limit + 1),
                )
                rows = cursor.fetchall()
    fields = ("case_key", "order_id", "currency", "rule_code", "finding_state", "workflow_status",
              "revision_number", "evaluated_run_id", "last_seen_run_id")
    items = [dict(zip(fields, (*r[:7], str(r[7]), str(r[8])))) for r in rows[:limit]]
    return {"action": "case_list", "merchant_id": merchant,
            "canonical_run_id": str(stream[0]) if stream else None, "generation": stream[1] if stream else None,
            "items": items, "truncated": len(rows) > limit,
            "next_after": items[-1]["case_key"] if len(rows) > limit else None}


def show_case(key: str, *, before_revision: int | None = None, limit: int = 20,
              dsn_env: str = "COMMERCEGUARD_DATABASE_URL") -> dict:
    case_key(key)
    _limit(limit, 100)
    if before_revision is not None and (type(before_revision) is not int or not 1 <= before_revision <= 2**63 - 1):
        raise CaseError("CASE_REVISION_CURSOR")
    with postgres_session(dsn_env, application_name="commerceguard-case-show") as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                schema_guard(cursor, write=False)
                cursor.execute(
                    "SELECT merchant_id, order_id, currency, rule_code, finding_state, workflow_status, "
                    "first_run_id, last_seen_run_id, evaluated_run_id, revision_number "
                    "FROM commerceguard.ops_case WHERE case_key = %s", (key,),
                )
                row = cursor.fetchone()
                if not row:
                    return {"action": "case_show", "case_key": key, "found": False}
                cursor.execute(
                    "SELECT r.revision_number, r.run_id, r.finding_state, r.finding_sha256, r.finding_json, "
                    "e.event_kind, a.generation, a.applied_at FROM commerceguard.ops_case_revision r "
                    "JOIN commerceguard.ops_case_event e ON e.case_key = r.case_key AND e.revision_number = r.revision_number "
                    "JOIN commerceguard.ops_case_application a ON a.run_id = r.run_id WHERE r.case_key = %s "
                    "AND (%s::bigint IS NULL OR r.revision_number < %s) ORDER BY r.revision_number DESC LIMIT %s",
                    (key, before_revision, before_revision, limit + 1),
                )
                revisions = cursor.fetchall()
    fields = ("merchant_id", "order_id", "currency", "rule_code", "finding_state", "workflow_status",
              "first_run_id", "last_seen_run_id", "evaluated_run_id", "revision_number")
    head = dict(zip(fields, (*row[:6], *(str(v) for v in row[6:9]), row[9])))
    history = [{"revision_number": r[0], "run_id": str(r[1]), "finding_state": r[2],
                "finding_sha256": r[3], "finding": r[4], "event_kind": r[5],
                "generation": r[6], "applied_at": canonical_time(r[7])} for r in revisions[:limit]]
    return {"action": "case_show", "case_key": key, "found": True, "head": head, "history": history,
            "truncated": len(revisions) > limit,
            "next_before_revision": history[-1]["revision_number"] if len(revisions) > limit else None}
