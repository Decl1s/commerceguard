"""Контракт между источниками, расчётом и будущими адаптерами.

Все суммы — целые minor units (копейки для RUB). У дат обязательно есть пояс.
Входы неизменяемые: повторный расчёт не меняет переданный снимок. Аннотации
сами не проверяют данные, поэтому существенные условия заданы явно.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import re


class ContractError(ValueError):
    """Партию нельзя интерпретировать однозначно; сохранять результат запрещено."""


class EventKind(StrEnum):
    CAPTURE = "capture"
    REFUND = "refund"


class OrderState(StrEnum):
    MATCHED = "matched"
    PENDING = "pending"
    DISCREPANCY = "discrepancy"
    BLOCKED = "blocked"


class Rule(StrEnum):
    PAYMENT_SHORTFALL = "payment_shortfall"
    PAYMENT_EXCESS = "payment_excess"
    REFUND_MISSING = "refund_missing"
    REFUND_EXCESS = "refund_excess"
    CURRENCY_MISMATCH = "currency_mismatch"
    ORPHAN_PAYMENT = "orphan_payment"


def require_id(value: str, field: str) -> None:
    """Ограничить синтетические идентификаторы и размер будущих ключей хранения."""
    if type(value) is not str or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", value) is None:
        raise ContractError(f"{field}: нужен идентификатор из 1–64 ASCII символов")


def require_currency(value: str) -> None:
    """Список валют ограничен контрактом демо; три произвольные буквы не валюта."""
    if type(value) is not str or value not in {"RUB", "USD", "EUR"}:
        raise ContractError("currency: допустимы RUB, USD, EUR; конвертация не выполняется")


def require_minor(value: int, field: str, *, positive: bool = False) -> None:
    """Не принимать bool/float: bool является подклассом int в Python."""
    minimum = 1 if positive else 0
    if type(value) is not int or not minimum <= value <= 10**12:
        raise ContractError(f"{field}: нужен целый minor amount от {minimum} до 10^12")


def utc(value: datetime, field: str) -> datetime:
    """Сравнивать моменты, а не локальные подписи часов компьютера."""
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ContractError(f"{field}: нужен datetime с часовым поясом")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class OrderExpectation:
    """Одна ожидаемая позиция сверки заказа на выбранный снимок OMS.

    capture_due_minor — полный ожидаемый capture, refund_due_minor — отдельная
    ожидаемая сумма уже одобренных возвратов. Возврат не уменьшает первый счётчик.
    settle_after — конец согласованного периода ожидания обеих сумм.
    """

    merchant_id: str
    order_id: str
    currency: str
    capture_due_minor: int
    refund_due_minor: int
    settle_after: datetime

    def __post_init__(self) -> None:
        require_id(self.merchant_id, "merchant_id")
        require_id(self.order_id, "order_id")
        require_currency(self.currency)
        require_minor(self.capture_due_minor, "capture_due_minor")
        require_minor(self.refund_due_minor, "refund_due_minor")
        if self.refund_due_minor > self.capture_due_minor:
            raise ContractError("refund_due_minor не может превышать capture_due_minor")
        object.__setattr__(self, "settle_after", utc(self.settle_after, "settle_after"))

    @property
    def key(self) -> tuple[str, str]:
        return self.merchant_id, self.order_id


@dataclass(frozen=True, slots=True)
class PaymentEvent:
    """Один подтверждённый PSP факт; авторизации и неуспешные операции не входят.

    observed_at — когда факт впервые стал известен системе, а не время очередной
    доставки. Два времени позволяют не подтянуть будущее знание в старую сверку.
    source_event_id уникален внутри merchant_id и единственного PSP версии v1.
    """

    merchant_id: str
    source_event_id: str
    order_id: str
    currency: str
    kind: EventKind
    amount_minor: int
    occurred_at: datetime
    observed_at: datetime

    def __post_init__(self) -> None:
        require_id(self.merchant_id, "merchant_id")
        require_id(self.source_event_id, "source_event_id")
        require_id(self.order_id, "order_id")
        require_currency(self.currency)
        if not isinstance(self.kind, EventKind):
            raise ContractError("kind: нужен EventKind.CAPTURE или EventKind.REFUND")
        require_minor(self.amount_minor, "amount_minor", positive=True)
        object.__setattr__(self, "occurred_at", utc(self.occurred_at, "occurred_at"))
        object.__setattr__(self, "observed_at", utc(self.observed_at, "observed_at"))
        if self.observed_at < self.occurred_at:
            raise ContractError("observed_at не может предшествовать occurred_at")

    @property
    def key(self) -> tuple[str, str]:
        return self.merchant_id, self.source_event_id

    @property
    def order_key(self) -> tuple[str, str]:
        return self.merchant_id, self.order_id

    @property
    def fingerprint(self) -> tuple:
        """Содержание факта; время наблюдения не превращает повтор в новую оплату."""
        return (self.order_id, self.currency, self.kind, self.amount_minor, self.occurred_at)


@dataclass(frozen=True, slots=True)
class Finding:
    """Предложение создать/обновить кейс; не сохранённая карточка и не перевод денег."""

    case_key: str
    merchant_id: str
    order_id: str
    currency: str
    rule: Rule
    expected_minor: int | None
    actual_minor: int | None
    delta_minor: int | None
    evidence_event_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OrderBalance:
    merchant_id: str
    order_id: str
    currency: str
    state: OrderState
    expected_capture_minor: int
    expected_refund_minor: int
    actual_capture_minor: int | None
    actual_refund_minor: int | None
    capture_delta_minor: int | None
    refund_delta_minor: int | None


@dataclass(frozen=True, slots=True)
class Reconciliation:
    """Чистый результат снимка: хранение и журнал запусков появятся в S1–S2."""

    ruleset_version: str
    as_of: datetime
    unique_visible_events: int
    duplicates_removed: int
    not_yet_visible_events: int
    balances: tuple[OrderBalance, ...]
    findings: tuple[Finding, ...]
