"""CG-102: строгий envelope пакета и единая канонизация смысла строки.

Не открывает файлы/БД при импорте. Manifest описывает один магазин и источник;
путь к данным не берётся из недоверенного JSON. Все проверки написаны без запуска.
"""

from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
import re

from .domain import ContractError, EventKind, OrderExpectation, PaymentEvent, require_id, utc

MAX_MANIFEST_BYTES = 64000
MAX_DATA_BYTES = 100000000
MAX_RECORD_BYTES = 1000000
MAX_ROWS = 1000000
OMS_COLUMNS = (
    "merchant_id", "order_id", "currency", "capture_due_minor", "refund_due_minor", "settle_after",
)


def canonical_manifest_bytes(manifest: "FileManifest") -> bytes:
    """Identity пакета — нормализованный envelope, не отступы исходного JSON.

    Один LF входит в hash и сохраняемый manifest. PSP не получает OMS-поля null.
    Изменение effective_at полного снимка создаёт новый пакет даже при том же CSV.
    """
    value = asdict(manifest)
    value["observed_at"] = canonical_time(manifest.observed_at)
    if manifest.source == "oms":
        value["effective_at"] = canonical_time(manifest.effective_at)
    else:
        del value["effective_at"]
        del value["is_complete"]
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")) + "\n").encode("ascii")
PSP_COLUMNS = {
    "merchant_id", "source_event_id", "order_id", "currency", "kind", "amount_minor",
    "occurred_at", "observed_at",
}
COMMON_MANIFEST = {
    "contract_version", "source", "merchant_id", "content_sha256", "row_count",
    "byte_count", "observed_at",
}

MESSAGES = {
    "IO_ERROR": "Не удалось прочитать вход или создать временный снимок",
    "NOT_REGULAR_FILE": "Нужен обычный файл, без конечной символической ссылки",
    "MANIFEST_TOO_LARGE": "Manifest превышает установленный размер",
    "INVALID_UTF8": "Вход должен быть UTF-8; BOM допустим только в начале файла",
    "INVALID_TEXT": "Нулевой символ недопустим",
    "JSON_SYNTAX": "Некорректный JSON",
    "JSON_DUPLICATE_KEY": "Ключ JSON повторился",
    "JSON_INTEGER_ONLY": "Контракт не допускает дроби, NaN или Infinity",
    "JSON_INTEGER_LIMIT": "Целое JSON превышает лексический предел",
    "JSON_DEPTH": "JSON слишком глубоко вложен",
    "OBJECT_REQUIRED": "Нужен JSON-объект",
    "FIELD_SET": "Набор полей не совпадает с контрактом",
    "FIELD_VALUE": "Значение поля не соответствует контракту",
    "TIMESTAMP_FORMAT": "Нужна RFC3339-дата с известным смещением, до 6 знаков долей секунды",
    "TIMESTAMP_ORDER": "Порядок времён противоречит контракту",
    "INCOMPLETE_SNAPSHOT": "OMS manifest должен объявлять полный снимок",
    "SIZE_MISMATCH": "Размер файла не совпадает с manifest",
    "HASH_MISMATCH": "SHA-256 файла не совпадает с manifest",
    "RECORD_TOO_LARGE": "Логическая запись превышает установленный размер",
    "CSV_HEADER": "Заголовок CSV не совпадает с точным порядком полей OMS",
    "CSV_SYNTAX": "Нарушен синтаксис CSV или предел поля CSV-движка",
    "CSV_WIDTH": "Количество значений CSV не совпадает с заголовком",
    "BLANK_RECORD": "Пустые записи не допускаются",
    "ROW_COUNT": "Число записей не совпадает с manifest",
    "MERCHANT_MISMATCH": "Магазин строки отличается от магазина пакета",
    "DOMAIN_CONTRACT": "Строка нарушает ограничения предметной модели",
    "OMS_DUPLICATE": "Ключ заказа повторился в полном OMS-снимке",
    "PSP_CONFLICT": "PSP ID повторился с другим смыслом",
    "STREAM_USED": "Поток пакета допускает только одно чтение",
    "STREAM_INCOMPLETE": "Пакет нужно дочитать до конца перед получением результата",
}


class FileInputError(ValueError):
    """Только безопасные коды, фиксированные имена полей и номер; без payload/path."""

    def __init__(self, code: str, *, artifact: str = "data", row: int | None = None, field: str | None = None):
        self.code = code
        self.artifact = artifact
        self.row = row
        self.field = field
        location = artifact
        if row is not None:
            location += "; record=" + str(row)
        if field is not None:
            location += "; field=" + field
        super().__init__(code + " (" + location + "): " + MESSAGES[code])


def json_object(text: str, *, artifact: str, row: int | None = None) -> dict:
    """Не позволяем стандартному JSON decoder молча выбрать последний дубль ключа."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise FileInputError("JSON_DUPLICATE_KEY", artifact=artifact, row=row)
            result[key] = value
        return result

    def integer(token):
        if len(token.lstrip("-")) > 16:
            raise FileInputError("JSON_INTEGER_LIMIT", artifact=artifact, row=row)
        return int(token)

    def reject_number(_):
        raise FileInputError("JSON_INTEGER_ONLY", artifact=artifact, row=row)

    if "\x00" in text:
        raise FileInputError("INVALID_TEXT", artifact=artifact, row=row)
    try:
        value = json.loads(text, object_pairs_hook=pairs, parse_int=integer,
                           parse_float=reject_number, parse_constant=reject_number)
    except json.JSONDecodeError:
        raise FileInputError("JSON_SYNTAX", artifact=artifact, row=row) from None
    except RecursionError:
        raise FileInputError("JSON_DEPTH", artifact=artifact, row=row) from None
    if type(value) is not dict:
        raise FileInputError("OBJECT_REQUIRED", artifact=artifact, row=row)
    return value


def exact_fields(value: dict, fields: set[str], *, artifact: str, row: int | None = None) -> None:
    if set(value) != fields:
        # Не печатаем неизвестные имена: даже JSON key может содержать приватные данные.
        raise FileInputError("FIELD_SET", artifact=artifact, row=row)


def timestamp(value, *, artifact: str, field: str, row: int | None = None) -> datetime:
    pattern = r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])"
    if (type(value) is not str or re.fullmatch(pattern, value) is None
            or value.endswith("-00:00")):
        raise FileInputError("TIMESTAMP_FORMAT", artifact=artifact, field=field, row=row)
    try:
        return utc(datetime.fromisoformat(value.replace("Z", "+00:00")), field)
    except (ValueError, OverflowError):
        raise FileInputError("TIMESTAMP_FORMAT", artifact=artifact, field=field, row=row) from None


def canonical_time(value: datetime) -> str:
    """Эквивалентные смещения/доли секунды получают одну UTC-запись."""
    return utc(value, "timestamp").isoformat(timespec="microseconds").replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class FileManifest:
    contract_version: int
    source: str
    merchant_id: str
    content_sha256: str
    row_count: int
    byte_count: int
    observed_at: datetime
    effective_at: datetime | None
    is_complete: bool | None


def manifest_from_json(text: str) -> FileManifest:
    value = json_object(text, artifact="manifest")
    source = value.get("source")
    if type(source) is not str or source not in {"oms", "psp"}:
        raise FileInputError("FIELD_VALUE", artifact="manifest", field="source")
    fields = COMMON_MANIFEST | ({"effective_at", "is_complete"} if source == "oms" else set())
    exact_fields(value, fields, artifact="manifest")
    if type(value["contract_version"]) is not int or value["contract_version"] != 1:
        raise FileInputError("FIELD_VALUE", artifact="manifest", field="contract_version")
    try:
        require_id(value["merchant_id"], "merchant_id")
    except ContractError:
        raise FileInputError("FIELD_VALUE", artifact="manifest", field="merchant_id") from None
    checksum = value["content_sha256"]
    if type(checksum) is not str or re.fullmatch(r"[a-f0-9]{64}", checksum) is None:
        raise FileInputError("FIELD_VALUE", artifact="manifest", field="content_sha256")
    for field, maximum in (("row_count", MAX_ROWS), ("byte_count", MAX_DATA_BYTES)):
        if type(value[field]) is not int or not 0 <= value[field] <= maximum:
            raise FileInputError("FIELD_VALUE", artifact="manifest", field=field)
    observed = timestamp(value["observed_at"], artifact="manifest", field="observed_at")
    effective = None
    complete = None
    if source == "oms":
        if value["is_complete"] is not True:
            raise FileInputError("INCOMPLETE_SNAPSHOT", artifact="manifest", field="is_complete")
        complete = True
        effective = timestamp(value["effective_at"], artifact="manifest", field="effective_at")
        if effective > observed:
            raise FileInputError("TIMESTAMP_ORDER", artifact="manifest", field="effective_at")
    return FileManifest(1, source, value["merchant_id"], checksum, value["row_count"],
                        value["byte_count"], observed, effective, complete)


def order_from_csv(values: list[str], manifest: FileManifest, row: int) -> OrderExpectation:
    if len(values) != len(OMS_COLUMNS):
        raise FileInputError("CSV_WIDTH", row=row)
    value = dict(zip(OMS_COLUMNS, values))
    if value["merchant_id"] != manifest.merchant_id:
        raise FileInputError("MERCHANT_MISMATCH", row=row, field="merchant_id")
    amounts = []
    for field in ("capture_due_minor", "refund_due_minor"):
        token = value[field]
        if re.fullmatch(r"0|[1-9][0-9]{0,12}", token) is None:
            raise FileInputError("FIELD_VALUE", row=row, field=field)
        amounts.append(int(token))
    due = timestamp(value["settle_after"], artifact="data", field="settle_after", row=row)
    try:
        return OrderExpectation(value["merchant_id"], value["order_id"], value["currency"], *amounts, due)
    except ContractError:
        raise FileInputError("DOMAIN_CONTRACT", row=row) from None


def event_from_json(text: str, manifest: FileManifest, row: int) -> PaymentEvent:
    value = json_object(text, artifact="data", row=row)
    exact_fields(value, PSP_COLUMNS, artifact="data", row=row)
    if value["merchant_id"] != manifest.merchant_id:
        raise FileInputError("MERCHANT_MISMATCH", row=row, field="merchant_id")
    kind = value["kind"]
    if type(kind) is not str or kind not in {"capture", "refund"}:
        raise FileInputError("FIELD_VALUE", row=row, field="kind")
    occurred = timestamp(value["occurred_at"], artifact="data", field="occurred_at", row=row)
    observed = timestamp(value["observed_at"], artifact="data", field="observed_at", row=row)
    if observed > manifest.observed_at:
        raise FileInputError("TIMESTAMP_ORDER", row=row, field="observed_at")
    try:
        return PaymentEvent(value["merchant_id"], value["source_event_id"], value["order_id"],
                            value["currency"], EventKind(kind), value["amount_minor"], occurred, observed)
    except ContractError:
        raise FileInputError("DOMAIN_CONTRACT", row=row) from None


def semantic_sha256(value: OrderExpectation | PaymentEvent) -> str:
    """Версионированный hash смысла, независимо от JSON layout/CSV quoting.

    Для PSP observed_at не входит в fingerprint: повтор доставки не новая оплата.
    merchant/event ID используются отдельно как ключ, как в предметном kernel.
    """
    if isinstance(value, PaymentEvent):
        payload = ["psp:v1", value.order_id, value.currency, value.kind.value,
                   value.amount_minor, canonical_time(value.occurred_at)]
    else:
        payload = ["oms:v1", value.merchant_id, value.order_id, value.currency,
                   value.capture_due_minor, value.refund_due_minor, canonical_time(value.settle_after)]
    encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()
