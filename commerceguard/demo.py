"""Синтетический сценарий для будущего просмотра; я пока не запускал его.

Фиксированное время — время предметной модели. Оно не используется для коммитов.
Здесь нет реальных магазинов, клиентов, контактов или выгрузок пользователя.
"""

from datetime import datetime

from .domain import EventKind, OrderExpectation, PaymentEvent, Reconciliation
from .reconcile import reconcile


def moment(value: str) -> datetime:
    """Внутренний помощник для констант демо, не парсер произвольного входного файла."""
    return datetime.fromisoformat(value)


def scenario() -> Reconciliation:
    """Пять ожиданий OMS, один повтор, будущий факт и четыре типа расхождений."""
    closed = moment("2026-10-23T12:00:00+00:00")
    later = moment("2026-10-25T12:00:00+00:00")
    cutoff = moment("2026-10-24T12:00:00+00:00")
    occurred = moment("2026-10-22T10:00:00+00:00")
    known = moment("2026-10-22T10:01:00+00:00")
    orders = (
        OrderExpectation("M01", "O1001", "RUB", 10000, 0, closed),
        OrderExpectation("M01", "O1002", "RUB", 12000, 0, closed),
        OrderExpectation("M01", "O1003", "RUB", 15000, 3000, closed),
        OrderExpectation("M01", "O1004", "RUB", 5000, 0, later),
        OrderExpectation("M01", "O1005", "RUB", 5000, 0, closed),
    )
    first = PaymentEvent("M01", "C01", "O1001", "RUB", EventKind.CAPTURE, 10000, occurred, known)
    events = (
        first,
        first,
        PaymentEvent("M01", "C02", "O1002", "RUB", EventKind.CAPTURE, 11000, occurred, known),
        PaymentEvent("M01", "C03", "O1003", "RUB", EventKind.CAPTURE, 15000, occurred, known),
        PaymentEvent("M01", "R03", "O1003", "RUB", EventKind.REFUND, 1000, occurred, known),
        PaymentEvent("M01", "C05", "O1005", "USD", EventKind.CAPTURE, 5000, occurred, known),
        PaymentEvent("M01", "C99", "O1999", "RUB", EventKind.CAPTURE, 7000, occurred, known),
        PaymentEvent("M01", "C02L", "O1002", "RUB", EventKind.CAPTURE, 1000, occurred, later),
    )
    return reconcile(orders, events, as_of=cutoff)
