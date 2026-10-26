"""Я отделяю свежесть источника, полноту последнего пакета и состояние попытки."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from importlib import resources
from importlib.metadata import PackageNotFoundError, version
import re
from zoneinfo import ZoneInfo

from .domain import utc
from .file_contracts import canonical_time

SOURCES = ('oms', 'psp', 'settlement')
TZDATA_VERSION = '2026.5'
MAX_THRESHOLD_SECONDS = 2678400


class SourceHealthError(ValueError):
    """Я возвращаю фиксированный код без raw, DSN и произвольных входных значений."""


@dataclass(frozen=True, slots=True)
class SourcePackage:
    package_id: str
    source: str
    observed_at: datetime
    published_at: datetime
    item_count: int
    declared_complete: bool | None
    content_sha256: str
    business_at: datetime | None = None
    expected_count: int | None = None

    def __post_init__(self):
        for field in ('observed_at', 'published_at', 'business_at'):
            if (value := getattr(self, field)) is not None:
                object.__setattr__(self, field, utc(value, field))
        if (self.source not in SOURCES or type(self.item_count) is not int or not 0 <= self.item_count <= 1000000
                or (self.declared_complete is not None and type(self.declared_complete) is not bool)
                or (self.source == 'psp' and self.declared_complete is not None)
                or (self.source == 'oms' and self.declared_complete is not True)
                or (self.expected_count is not None and (type(self.expected_count) is not int
                    or not self.item_count <= self.expected_count <= 1000000))):
            raise SourceHealthError('SOURCE_PACKAGE_CONTRACT')


@dataclass(frozen=True, slots=True)
class SourceAttempt:
    attempt_id: str
    package_id: str
    source: str
    state: str
    started_at: datetime
    finished_at: datetime | None
    error_code: str | None = None

    def __post_init__(self):
        for field in ('started_at', 'finished_at'):
            if (value := getattr(self, field)) is not None:
                object.__setattr__(self, field, utc(value, field))
        if (self.source not in ('oms', 'psp')
                or self.state not in ('started', 'published', 'duplicate', 'quarantined', 'failed', 'unknown')
                or (self.finished_at is None) != (self.state == 'started')
                or (self.finished_at is not None and self.finished_at < self.started_at)
                or (self.error_code is not None and re.fullmatch(r'[A-Z][A-Z0-9_]{2,63}', self.error_code) is None)):
            raise SourceHealthError('SOURCE_ATTEMPT_CONTRACT')


def threshold(value: int, *, allow_zero: bool = False) -> int:
    if type(value) is not int or not (0 if allow_zero else 1) <= value <= MAX_THRESHOLD_SECONDS:
        raise SourceHealthError('SOURCE_THRESHOLD')
    return value


def business_context(as_of: datetime, key: str) -> dict:
    # Я читаю wheel tzdata явно: обновление timezone базы ОС не меняет мои границы.
    if not isinstance(key, str) or len(key) > 128 or re.fullmatch(r'[A-Za-z][A-Za-z0-9_+\-/]*', key) is None:
        raise SourceHealthError('SOURCE_TIMEZONE')
    if any(part in ('', '.', '..') for part in key.split('/')):
        raise SourceHealthError('SOURCE_TIMEZONE')
    try:
        if version('tzdata') != TZDATA_VERSION:
            raise SourceHealthError('SOURCE_TZDATA_VERSION')
        import tzdata
        with resources.files('tzdata.zoneinfo').joinpath(*key.split('/')).open('rb') as stream:
            zone = ZoneInfo.from_file(stream, key=key)
    except SourceHealthError:
        raise
    except PackageNotFoundError:
        raise SourceHealthError('SOURCE_TZDATA_REQUIRED') from None
    except (OSError, ValueError, ImportError):
        raise SourceHealthError('SOURCE_TIMEZONE') from None
    local = utc(as_of, 'as_of').astimezone(zone)
    return {'timezone': key, 'tzdata_version': TZDATA_VERSION, 'iana_version': tzdata.IANA_VERSION,
            'as_of_local': local.isoformat(), 'business_date': local.date().isoformat(), 'fold': local.fold}


def microseconds(later: datetime, earlier: datetime) -> int:
    return (utc(later, 'later') - utc(earlier, 'earlier')) // timedelta(microseconds=1)


def attempt_at(value: SourceAttempt, as_of: datetime) -> dict:
    terminal = value.finished_at is not None and value.finished_at <= as_of
    # Я не раскрываю terminal state/error из будущего относительно выбранного cutoff.
    return {'attempt_id': value.attempt_id, 'package_id': value.package_id,
            'started_at': canonical_time(value.started_at),
            'finished_at': canonical_time(value.finished_at) if terminal else None,
            'state': value.state if terminal else 'started_at_boundary',
            'terminal_known_at_cutoff': terminal, 'error_code': value.error_code if terminal else None}


def package_summary(value: SourcePackage) -> dict:
    return {'package_id': value.package_id, 'observed_at': canonical_time(value.observed_at),
            'published_at': canonical_time(value.published_at), 'item_count': value.item_count,
            'declared_complete': value.declared_complete, 'content_sha256': value.content_sha256,
            'expected_count': value.expected_count}


def evaluate_source(source: str, packages: list[SourcePackage], attempts: list[SourceAttempt], *,
                    as_of: datetime, max_age_seconds: int, late_after_seconds: int,
                    event_watermark: datetime | None = None, max_event_lag_us: int | None = None) -> dict:
    if source not in SOURCES or any(p.source != source for p in packages) or any(a.source != source for a in attempts):
        raise SourceHealthError('SOURCE_CONTEXT')
    threshold(max_age_seconds); threshold(late_after_seconds, allow_zero=True)
    cutoff = utc(as_of, 'as_of')
    visible = [p for p in packages if utc(p.published_at, 'published_at') <= cutoff
               and utc(p.observed_at, 'observed_at') <= cutoff]
    known = [a for a in attempts if utc(a.started_at, 'started_at') <= cutoff]
    if event_watermark is not None and utc(event_watermark, 'event_watermark') > cutoff:
        raise SourceHealthError('SOURCE_EVENT_CUTOFF')
    if max_event_lag_us is not None and (type(max_event_lag_us) is not int or max_event_lag_us < 0):
        raise SourceHealthError('SOURCE_EVENT_LAG')
    latest = max(visible, key=lambda p: (p.published_at, p.package_id), default=None)
    watermark = max((p.observed_at for p in visible), default=None)
    business = max((p.business_at for p in visible if p.business_at is not None and p.business_at <= cutoff), default=None)
    age = microseconds(cutoff, watermark) if watermark is not None else None
    delivery_lag = microseconds(latest.published_at, latest.observed_at) if latest else None
    clock_anomaly = delivery_lag is not None and delivery_lag < 0
    if clock_anomaly:
        delivery_lag = None
    # Я не считаю row_count=0 подтверждением нулевого оборота PSP v1.
    complete = ('unknown' if latest is None or latest.declared_complete is None else
                'incomplete' if not latest.declared_complete or
                (latest.expected_count is not None and latest.expected_count != latest.item_count) else 'declared_complete')
    volume = ('no_data' if latest is None else 'rows_present' if latest.item_count else
              'complete_zero' if complete == 'declared_complete' else 'empty_unproven')
    last_attempt = max(known, key=lambda a: (a.started_at, a.attempt_id), default=None)
    successes = [a for a in known if a.state in ('published', 'duplicate') and a.finished_at is not None
                 and a.finished_at <= cutoff]
    last_success = max(successes, key=lambda a: (a.finished_at, a.attempt_id), default=None)
    return {'source': source, 'freshness': 'no_data' if age is None else
            'stale' if age > max_age_seconds * 1000000 else 'fresh',
            'max_age_seconds': max_age_seconds, 'late_after_seconds': late_after_seconds,
            'published_package_count': len(visible), 'observed_watermark': canonical_time(watermark) if watermark else None,
            'age_microseconds': age, 'business_watermark': canonical_time(business) if business else None,
            'business_watermark_kind': {'oms': 'effective_at', 'psp': 'occurred_at', 'settlement': 'period_end'}[source],
            'event_watermark': canonical_time(event_watermark) if event_watermark else None,
            'max_event_observation_lag_microseconds': max_event_lag_us,
            'late_events_observed': max_event_lag_us > late_after_seconds * 1000000 if max_event_lag_us is not None else None,
            'latest_publication': package_summary(latest) if latest else None,
            'delivery_lag_microseconds': delivery_lag,
            'publication_before_observed': clock_anomaly,
            'late_delivery': delivery_lag > late_after_seconds * 1000000 if delivery_lag is not None else None,
            'completeness': complete, 'completeness_scope': 'last_published_package', 'volume': volume,
            'attempt_journal_supported': source != 'settlement',
            'last_attempt': attempt_at(last_attempt, cutoff) if last_attempt else None,
            'last_successful_attempt': attempt_at(last_success, cutoff) if last_success else None}
