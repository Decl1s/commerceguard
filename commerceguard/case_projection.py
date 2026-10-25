"""Я отделяю форму finding от состояния карточки; здесь нет БД и часов."""

from dataclasses import dataclass
import hashlib
import json
import re

from .domain import ContractError, Rule, require_currency, require_id

MAX_CASES = 10000
FINDING_FIELDS = frozenset({"case_key", "merchant_id", "order_id", "currency", "rule",
                            "expected_minor", "actual_minor", "delta_minor", "evidence_event_ids"})


class CaseError(ValueError):
    """Я возвращаю фиксированный код без содержимого finding и серверного DETAIL."""


def case_key(value: str) -> str:
    if type(value) is not str or re.fullmatch(r"[a-f0-9]{64}", value) is None:
        raise CaseError("CASE_KEY_INVALID")
    return value


@dataclass(frozen=True, slots=True)
class FindingSnapshot:
    case_key: str
    merchant_id: str
    order_id: str
    currency: str
    rule: str
    text: str
    sha256: str


def finding_snapshots(payload: dict, merchant: str) -> dict[str, FindingSnapshot]:
    """Я принимаю только полную известную форму balance-v1, без тихого усечения."""
    findings = payload.get("findings")
    if type(findings) is not list or len(findings) > MAX_CASES:
        raise CaseError("CASE_PROJECTION_LIMIT")
    snapshots = {}
    for value in findings:
        if type(value) is not dict or set(value) != FINDING_FIELDS:
            raise CaseError("FINDING_SHAPE")
        try:
            require_id(value["merchant_id"], "merchant_id")
            require_id(value["order_id"], "order_id")
            require_currency(value["currency"])
            rule = Rule(value["rule"])
            identity = [value["merchant_id"], value["order_id"], value["currency"], rule.value]
            expected_key = hashlib.sha256(json.dumps(identity, separators=(",", ":")).encode()).hexdigest()
            if value["merchant_id"] != merchant or case_key(value["case_key"]) != expected_key:
                raise CaseError("FINDING_IDENTITY")
            evidence = value["evidence_event_ids"]
            if type(evidence) is not list or len(evidence) > 50000:
                raise CaseError("FINDING_EVIDENCE")
            for event_id in evidence:
                require_id(event_id, "source_event_id")
            if evidence != sorted(set(evidence)):
                raise CaseError("FINDING_EVIDENCE")
            expected, actual, delta = (value[k] for k in ("expected_minor", "actual_minor", "delta_minor"))
            if rule in (Rule.CURRENCY_MISMATCH, Rule.ORPHAN_PAYMENT):
                if (expected, actual, delta) != (None, None, None):
                    raise CaseError("FINDING_AMOUNTS")
            elif (type(expected) is not int or type(actual) is not int or type(delta) is not int or
                  not 0 <= expected <= 10**12 or not 0 <= actual <= 50000 * 10**12 or
                  delta != actual - expected):
                raise CaseError("FINDING_AMOUNTS")
            text = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
            if len(text.encode("ascii")) > 65536:
                raise CaseError("FINDING_SIZE_LIMIT")
            # Я называю все поля явно: identity key не подменяет merchant/order.
            snapshot = FindingSnapshot(value["case_key"], *identity[:3], rule.value, text,
                                       hashlib.sha256(text.encode("ascii")).hexdigest())
        except CaseError:
            raise
        except (ContractError, ValueError, TypeError, KeyError):
            raise CaseError("FINDING_CONTRACT") from None
        if snapshot.case_key in snapshots:
            raise CaseError("FINDING_DUPLICATE")
        snapshots[snapshot.case_key] = snapshot
    return snapshots


def transition(previous_state: str | None, previous_sha: str | None,
               current: FindingSnapshot | None) -> str | None:
    """Я создаю событие только при изменении, а не при каждом наблюдении."""
    if previous_state is None:
        return "detected" if current else None
    if current is None:
        return "absent" if previous_state == "present" else None
    if previous_state == "absent":
        return "reappeared"
    return "changed" if previous_sha != current.sha256 else None
