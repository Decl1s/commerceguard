"""CG-102: ограниченный файл → фиксированный временный снимок → поток записей.

Код не исполнялся разработчиком. Временный снимок избегает ситуации «hash одного
содержимого, parse уже изменившегося файла». Постоянные raw и БД здесь не пишутся.
"""

from contextlib import contextmanager
from dataclasses import dataclass
import csv
import hashlib
import io
import os
from pathlib import Path
import stat
import tempfile
from typing import BinaryIO, Iterator, TextIO

from .domain import OrderExpectation, PaymentEvent
from .file_contracts import (
    FileInputError, FileManifest, MAX_MANIFEST_BYTES, MAX_RECORD_BYTES, OMS_COLUMNS,
    canonical_time, event_from_json, manifest_from_json, order_from_csv, semantic_sha256,
)


@dataclass(frozen=True, slots=True)
class InputRecord:
    row_number: int
    physical_line_start: int
    physical_line_end: int
    raw_text: str
    record_sha256: str
    semantic_sha256: str
    value: OrderExpectation | PaymentEvent


@contextmanager
def regular_file(path: Path, *, artifact: str) -> Iterator[BinaryIO]:
    """Читаем обычный файл. Конечную symlink отвергаем, POSIX дополнительно NOFOLLOW.

    Не является sandbox для произвольных путей/родительских каталогов. Два пути
    задаёт вызывающий пользователь, ни один не извлекается из manifest.
    """
    descriptor = None
    try:
        if path.is_symlink():
            raise FileInputError("NOT_REGULAR_FILE", artifact=artifact)
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        descriptor = os.open(path, flags)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise FileInputError("NOT_REGULAR_FILE", artifact=artifact)
        stream = os.fdopen(descriptor, "rb")
        descriptor = None  # Теперь дескриптором владеет stream.
        with stream:
            yield stream
    except OSError:
        raise FileInputError("IO_ERROR", artifact=artifact) from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def read_manifest(path: Path) -> FileManifest:
    with regular_file(path, artifact="manifest") as stream:
        data = stream.read(MAX_MANIFEST_BYTES + 1)
    if len(data) > MAX_MANIFEST_BYTES:
        raise FileInputError("MANIFEST_TOO_LARGE", artifact="manifest")
    try:
        return manifest_from_json(data.decode("utf-8-sig"))
    except UnicodeError:
        raise FileInputError("INVALID_UTF8", artifact="manifest") from None


def freeze_data(path: Path, manifest: FileManifest, snapshot: BinaryIO) -> None:
    """Считаем hash исходных байтов, включая BOM/newlines; snapshot ограничен byte_count."""
    digest = hashlib.sha256()
    size = 0
    with regular_file(path, artifact="data") as source:
        if os.fstat(source.fileno()).st_size != manifest.byte_count:
            raise FileInputError("SIZE_MISMATCH")
        while True:
            chunk = source.read(64000)
            if not chunk:
                break
            size += len(chunk)
            if size > manifest.byte_count:
                raise FileInputError("SIZE_MISMATCH")
            digest.update(chunk)
            snapshot.write(chunk)
    if size != manifest.byte_count:
        raise FileInputError("SIZE_MISMATCH")
    if digest.hexdigest() != manifest.content_sha256:
        raise FileInputError("HASH_MISMATCH")
    snapshot.seek(0)


class TrackedLines:
    """Даём csv.reader физические строки и ограничиваем суммарный размер записи.

    Лимит проверяется и при переносах внутри quoted CSV field. Глобальный
    csv.field_size_limit не меняем: parser не должен менять чужую настройку процесса.
    """

    def __init__(self, stream: TextIO):
        self.stream = stream
        self.physical_line = 0
        self.start_line = 1
        self.row_number = 0
        self.parts: list[str] = []
        self.bytes = 0

    def start_record(self, row_number: int) -> None:
        self.row_number = row_number
        self.start_line = self.physical_line + 1
        self.parts = []
        self.bytes = 0

    def __iter__(self):
        return self

    def __next__(self) -> str:
        line = self.stream.readline(MAX_RECORD_BYTES + 1)
        if line == "":
            raise StopIteration
        self.physical_line += 1
        if "\x00" in line:
            raise FileInputError("INVALID_TEXT", row=self.row_number)
        self.bytes += len(line.encode("utf-8"))
        if self.bytes > MAX_RECORD_BYTES:
            raise FileInputError("RECORD_TOO_LARGE", row=self.row_number)
        self.parts.append(line)
        return line


class PreparedInput:
    """Один проход; summary и нормальный выход разрешены только после полного EOF.

    Память: текущая запись + hashes ключей. Ключи растут до row_count (<=10^6),
    поэтому это ограниченный поток, а не обещание O(1) памяти.
    """

    def __init__(self, manifest: FileManifest, stream: TextIO):
        self.manifest = manifest
        self.lines = TrackedLines(stream)
        self.started = False
        self.completed = False
        self.row_count = 0
        self.duplicate_rows = 0
        self.seen: dict[tuple[str, str], str] = {}

    def _csv(self) -> Iterator[OrderExpectation]:
        reader = csv.reader(self.lines, delimiter=",", quotechar='"', doublequote=True,
                            skipinitialspace=False, strict=True)
        self.lines.start_record(0)
        if next(reader, None) != list(OMS_COLUMNS):
            raise FileInputError("CSV_HEADER", row=0)
        ordinal = 1
        while True:
            self.lines.start_record(ordinal)
            values = next(reader, None)
            if values is None:
                return
            if ordinal > self.manifest.row_count:
                raise FileInputError("ROW_COUNT", row=ordinal)
            if not values:
                raise FileInputError("BLANK_RECORD", row=ordinal)
            yield order_from_csv(values, self.manifest, ordinal)
            ordinal += 1

    def _jsonl(self) -> Iterator[PaymentEvent]:
        ordinal = 1
        while True:
            self.lines.start_record(ordinal)
            text = next(self.lines, None)
            if text is None:
                return
            if ordinal > self.manifest.row_count:
                raise FileInputError("ROW_COUNT", row=ordinal)
            if not text.strip():
                raise FileInputError("BLANK_RECORD", row=ordinal)
            yield event_from_json(text, self.manifest, ordinal)
            ordinal += 1

    def records(self) -> Iterator[InputRecord]:
        if self.started:
            raise FileInputError("STREAM_USED")
        self.started = True
        try:
            values = self._csv() if self.manifest.source == "oms" else self._jsonl()
            for value in values:
                checksum = semantic_sha256(value)
                previous = self.seen.get(value.key)
                if previous is not None:
                    if self.manifest.source == "oms":
                        raise FileInputError("OMS_DUPLICATE", row=self.lines.row_number)
                    if previous != checksum:
                        raise FileInputError("PSP_CONFLICT", row=self.lines.row_number)
                    self.duplicate_rows += 1
                else:
                    self.seen[value.key] = checksum
                self.row_count += 1
                raw = "".join(self.lines.parts)
                yield InputRecord(self.row_count, self.lines.start_line, self.lines.physical_line,
                                  raw, hashlib.sha256(raw.encode("utf-8")).hexdigest(), checksum, value)
        except UnicodeError:
            raise FileInputError("INVALID_UTF8", row=self.lines.row_number) from None
        except csv.Error:
            raise FileInputError("CSV_SYNTAX", row=self.lines.row_number) from None
        if self.row_count != self.manifest.row_count:
            raise FileInputError("ROW_COUNT", row=self.row_count + 1)
        self.completed = True

    def summary(self) -> dict:
        if not self.completed:
            raise FileInputError("STREAM_INCOMPLETE")
        return {
            "action": "inspect", "source": self.manifest.source,
            "merchant_id": self.manifest.merchant_id, "contract_version": 1,
            "row_count": self.row_count, "unique_keys": len(self.seen),
            "duplicate_rows": self.duplicate_rows, "byte_count": self.manifest.byte_count,
            "content_sha256": self.manifest.content_sha256,
            "observed_at": canonical_time(self.manifest.observed_at),
        }


@contextmanager
def open_input(manifest_path: Path, data_path: Path) -> Iterator[PreparedInput]:
    """Контекст должен пережить весь проход будущего COPY/валидации перед COMMIT."""
    manifest = read_manifest(manifest_path)
    try:
        with tempfile.TemporaryFile(mode="w+b") as snapshot:
            freeze_data(data_path, manifest, snapshot)
            with io.TextIOWrapper(snapshot, encoding="utf-8-sig", newline="") as text:
                batch = PreparedInput(manifest, text)
                yield batch
                if not batch.completed:
                    raise FileInputError("STREAM_INCOMPLETE")
    except OSError:
        raise FileInputError("IO_ERROR") from None


def inspect_input(manifest_path: Path, data_path: Path) -> dict:
    """Полный проход, затем безопасная сводка; строки/их значения в CLI не печатаются."""
    with open_input(manifest_path, data_path) as batch:
        for _ in batch.records():
            pass
        return batch.summary()
