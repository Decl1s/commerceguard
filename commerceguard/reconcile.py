"""Расчёт сверки в памяти: без I/O, часов компьютера, БД и побочных эффектов.

Два отдельных денежные плеча не дают пропавшей оплате и пропавшему возврату
взаимно скрыться в net-сумме. Обоснование и формулы — docs/DATA_CONTRACTS.md.
"""

from collections import defaultdict
from datetime import datetime
import hashlib
import json
from typing import Iterable

from .domain import (
    ContractError, EventKind, Finding, OrderBalance, OrderExpectation,
    OrderState, PaymentEvent, Reconciliation, Rule, utc,
)

RULESET_VERSION = "balance-v1"


def make_finding(
    merchant_id: str, order_id: str, currency: str, rule: Rule,
    events: Iterable[PaymentEvent], *, expected: int | None = None,
    actual: int | None = None,
) -> Finding:
    """Один стабильный ключ на магазин/заказ/валюту/правило, независимо от суммы.

    Изменение evidence обновит тот же будущий кейс. Суммы и версия правила
    попадут в ревизии кейса; разделение кодов правил сохраняет смысл ключа.
    JSON-массив устраняет неоднозначность склеивания строк через разделитель.
    """
    identity = json.dumps([merchant_id, order_id, currency, rule.value], separators=(",", ":"))
    key = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    evidence = tuple(sorted(e.source_event_id for e in events))
    delta = None if expected is None or actual is None else actual - expected
    return Finding(key, merchant_id, order_id, currency, rule, expected, actual, delta, evidence)


def reconcile(
    orders: Iterable[OrderExpectation], events: Iterable[PaymentEvent], *, as_of: datetime,
) -> Reconciliation:
    """Сопоставить один полный снимок ожиданий OMS и известных PSP событий.

    as_of задаёт вызывающий код. Неполный OMS-снимок даст ложные orphan: загрузчик
    следующего спринта обязан публиковать только завершённые манифесты снимков.
    Ошибочный контракт обрывает весь расчёт; бизнес-расхождение даёт Finding.
    """
    cutoff = utc(as_of, "as_of")
    expected: dict[tuple[str, str], OrderExpectation] = {}
    for order in orders:
        if not isinstance(order, OrderExpectation):
            raise ContractError("orders: нужны объекты OrderExpectation")
        if order.key in expected:
            raise ContractError("OMS snapshot содержит повтор ключа merchant_id/order_id")
        expected[order.key] = order

    visible: dict[tuple[str, str], PaymentEvent] = {}
    duplicates = 0
    future = 0
    for event in events:
        if not isinstance(event, PaymentEvent):
            raise ContractError("events: нужны объекты PaymentEvent")
        if event.observed_at > cutoff or event.occurred_at > cutoff:
            future += 1
            continue
        previous = visible.get(event.key)
        if previous is not None:
            if previous.fingerprint != event.fingerprint:
                # «Последняя строка победила» незаметно переписала бы финансовый факт.
                raise ContractError("PSP source_event_id повторился с другим содержимым")
            duplicates += 1
            if event.observed_at < previous.observed_at:
                visible[event.key] = event
        else:
            visible[event.key] = event

    grouped: dict[tuple[str, str], list[PaymentEvent]] = defaultdict(list)
    for event in visible.values():
        grouped[event.order_key].append(event)

    findings: list[Finding] = []
    balances: list[OrderBalance] = []
    # Явная сортировка делает порядок отчёта независимым от порядка доставки.
    for order_key in sorted(set(expected) | set(grouped)):
        order_events = sorted(grouped.get(order_key, []), key=lambda e: e.source_event_id)
        order = expected.get(order_key)
        if order is None:
            by_currency: dict[str, list[PaymentEvent]] = defaultdict(list)
            for event in order_events:
                by_currency[event.currency].append(event)
            for currency, evidence in sorted(by_currency.items()):
                findings.append(make_finding(*order_key, currency, Rule.ORPHAN_PAYMENT, evidence))
            continue

        mismatched: dict[str, list[PaymentEvent]] = defaultdict(list)
        for event in order_events:
            if event.currency != order.currency:
                mismatched[event.currency].append(event)
        if mismatched:
            for currency, evidence in sorted(mismatched.items()):
                findings.append(make_finding(*order.key, currency, Rule.CURRENCY_MISMATCH, evidence))
            # Не выдаю частичный RUB-баланс за весь заказ при наличии USD-факта.
            balances.append(OrderBalance(
                *order.key, order.currency, OrderState.BLOCKED,
                order.capture_due_minor, order.refund_due_minor, None, None, None, None,
            ))
            continue

        captures = [e for e in order_events if e.kind == EventKind.CAPTURE]
        refunds = [e for e in order_events if e.kind == EventKind.REFUND]
        actual_capture = sum(e.amount_minor for e in captures)
        actual_refund = sum(e.amount_minor for e in refunds)
        capture_delta = actual_capture - order.capture_due_minor
        refund_delta = actual_refund - order.refund_due_minor
        state = OrderState.PENDING
        if cutoff >= order.settle_after:
            state = OrderState.MATCHED
            for delta, short_rule, excess_rule, due, actual, evidence in (
                (capture_delta, Rule.PAYMENT_SHORTFALL, Rule.PAYMENT_EXCESS,
                 order.capture_due_minor, actual_capture, captures),
                (refund_delta, Rule.REFUND_MISSING, Rule.REFUND_EXCESS,
                 order.refund_due_minor, actual_refund, refunds),
            ):
                if delta != 0:
                    state = OrderState.DISCREPANCY
                    findings.append(make_finding(
                        *order.key, order.currency, short_rule if delta < 0 else excess_rule,
                        evidence, expected=due, actual=actual,
                    ))
        balances.append(OrderBalance(
            *order.key, order.currency, state, order.capture_due_minor,
            order.refund_due_minor, actual_capture, actual_refund, capture_delta, refund_delta,
        ))

    return Reconciliation(
        RULESET_VERSION, cutoff, len(visible), duplicates, future,
        tuple(balances), tuple(sorted(findings, key=lambda f: f.case_key)),
    )
