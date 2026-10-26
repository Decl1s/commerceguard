"""Я задаю отдельную выписку провайдера, не подменяя её пакетом доставки PSP."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from .domain import ContractError, require_currency, require_id
from .file_contracts import FileInputError, canonical_time, json_object, timestamp
from .file_inputs import regular_file

MAX_MEMBERS = 10000
MAX_DOCUMENT_BYTES = 1048576
MAX_TOTAL = MAX_MEMBERS * 10**12
FIELDS = frozenset({'contract_version', 'merchant_id', 'settlement_id', 'revision', 'currency',
                    'period_start', 'period_end', 'observed_at', 'is_complete', 'expected_event_count',
                    'event_ids', 'gross_minor', 'refund_minor', 'fee_minor', 'net_minor'})


class SettlementError(ValueError):
    """Я возвращаю фиксированный код без исходного документа и серверных деталей."""


@dataclass(frozen=True, slots=True)
class Advice:
    text: str
    sha256: str
    advice_id: str

    def value(self) -> dict:
        # Я возвращаю копию нормализованного JSON, mutable dict не храню внутри Advice.
        return json.loads(self.text)


def parse_advice(data: bytes) -> Advice:
    if not data or len(data) > MAX_DOCUMENT_BYTES:
        raise SettlementError('SETTLEMENT_DOCUMENT_SIZE')
    try:
        value = json_object(data.decode('utf-8'), artifact='settlement', max_integer_digits=18)
        if set(value) != FIELDS or type(value['contract_version']) is not int or value['contract_version'] != 1:
            raise SettlementError('SETTLEMENT_FIELDS_OR_VERSION')
        for field in ('merchant_id', 'settlement_id'):
            require_id(value[field], field)
        require_currency(value['currency'])
        if type(value['revision']) is not int or not 1 <= value['revision'] <= 1000000:
            raise SettlementError('SETTLEMENT_REVISION')
        if type(value['is_complete']) is not bool:
            raise SettlementError('SETTLEMENT_COMPLETENESS')
        count, ids = value['expected_event_count'], value['event_ids']
        if (type(count) is not int or not 0 <= count <= MAX_MEMBERS or type(ids) is not list
                or len(ids) > count):
            raise SettlementError('SETTLEMENT_MEMBER_COUNT')
        for event_id in ids:
            require_id(event_id, 'source_event_id')
        if len(ids) != len(set(ids)):
            raise SettlementError('SETTLEMENT_DUPLICATE_MEMBER')
        value['event_ids'] = sorted(ids)
        for field in ('gross_minor', 'refund_minor', 'fee_minor', 'net_minor'):
            minimum, maximum = (-2 * MAX_TOTAL, 2 * MAX_TOTAL) if field == 'net_minor' else (0, MAX_TOTAL)
            if type(value[field]) is not int or not minimum <= value[field] <= maximum:
                raise SettlementError('SETTLEMENT_AMOUNT')
        times = {field: timestamp(value[field], artifact='settlement', field=field)
                 for field in ('period_start', 'period_end', 'observed_at')}
        if times['period_start'] >= times['period_end'] or times['observed_at'] < times['period_start']:
            raise SettlementError('SETTLEMENT_TIME_ORDER')
        if value['is_complete'] and times['observed_at'] < times['period_end']:
            raise SettlementError('SETTLEMENT_COMPLETE_BEFORE_END')
        value.update({field: canonical_time(moment) for field, moment in times.items()})
    except SettlementError:
        raise
    except (FileInputError, ContractError, UnicodeError, TypeError, ValueError, KeyError):
        raise SettlementError('SETTLEMENT_CONTRACT') from None
    text = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':')) + '\n'
    if len(text.encode('ascii')) > MAX_DOCUMENT_BYTES:
        raise SettlementError('SETTLEMENT_DOCUMENT_SIZE')
    digest = hashlib.sha256(text.encode('ascii')).hexdigest()
    return Advice(text, digest, str(uuid5(NAMESPACE_URL, 'commerceguard:settlement-advice:v1:' + digest)))


def read_advice(path: Path) -> tuple[Advice, bytes]:
    try:
        with regular_file(path, artifact='settlement') as stream:
            data = stream.read(MAX_DOCUMENT_BYTES + 1)
    except FileInputError:
        raise SettlementError('SETTLEMENT_INPUT_IO') from None
    return parse_advice(data), data


def inspect_advice(path: Path) -> dict:
    advice, data = read_advice(path)
    value = advice.value()
    return {'advice_id': advice.advice_id, 'canonical_sha256': advice.sha256,
            'raw_sha256': hashlib.sha256(data).hexdigest(), 'merchant_id': value['merchant_id'],
            'settlement_id': value['settlement_id'], 'revision': value['revision'],
            'currency': value['currency'], 'is_complete': value['is_complete'],
            'expected_event_count': value['expected_event_count'], 'member_count': len(value['event_ids'])}


def generate_advice(output: Path) -> dict:
    if output.exists() or output.is_symlink():
        raise SettlementError('SETTLEMENT_OUTPUT_EXISTS')
    base = {'contract_version': 1, 'merchant_id': 'M01', 'settlement_id': 'PSP-20261022-RUB',
            'revision': 1, 'currency': 'RUB', 'period_start': '2026-10-22T00:00:00Z',
            'period_end': '2026-10-23T00:00:00Z', 'observed_at': '2026-10-23T13:00:00Z',
            'is_complete': True, 'expected_event_count': 4, 'event_ids': ['C01', 'C02', 'C03', 'R03'],
            'gross_minor': 36000, 'refund_minor': 1000, 'fee_minor': 720, 'net_minor': 34280}
    examples = {'matched.json': base,
                'incomplete.json': dict(base, revision=2, is_complete=False, expected_event_count=5),
                'fee-mismatch.json': dict(base, revision=3, fee_minor=800, net_minor=34200)}
    try:
        output.mkdir()
        for name, value in examples.items():
            (output / name).write_text(parse_advice(json.dumps(value).encode()).text, encoding='ascii')
    except OSError:
        raise SettlementError('SETTLEMENT_OUTPUT_IO') from None
    return {'generated_files': len(examples), 'tariff_bps_for_example': 200}
