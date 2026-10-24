"""Локальные content-addressed объекты. Код написан без исполнения.

Отдельный user-owned root; конкурентный враждебный процесс с правом менять его
родителей вне модели угроз. Никаких исходных имён файлов, путей из JSON и overwrite.
"""

from dataclasses import dataclass
import hashlib
import io
import os
from pathlib import Path
import tempfile
from typing import BinaryIO

from .file_contracts import FileManifest, canonical_manifest_bytes
from .file_inputs import regular_file


class RawStoreError(ValueError):
    """Безопасная причина, без абсолютного пути или содержимого файла."""


@dataclass(frozen=True, slots=True)
class RawArtifacts:
    manifest_sha256: str
    raw_object_key: str
    manifest_object_key: str
    manifest_bytes: bytes


class RawStore:
    MARKER = ".commerceguard-raw-v1"
    IDENTITY = b"commerceguard:raw:v1\n"

    def __init__(self, root: Path):
        self.root = root

    def describe(self, manifest: FileManifest) -> RawArtifacts:
        data = canonical_manifest_bytes(manifest)
        digest = hashlib.sha256(data).hexdigest()
        return RawArtifacts(
            digest, f"objects/{manifest.content_sha256[:2]}/{manifest.content_sha256}",
            f"manifests/{digest[:2]}/{digest}.json", data,
        )

    @staticmethod
    def _verify(path: Path, size: int, digest: str) -> None:
        # Повторная запись ничего не чинит: повреждённый объект требует разбора.
        with regular_file(path, "raw") as source:
            seen = 0
            checksum = hashlib.sha256()
            while block := source.read(64000):
                seen += len(block)
                if seen > size:
                    raise RawStoreError("RAW_CORRUPT: размер существующего объекта неверен")
                checksum.update(block)
            if seen != size or checksum.hexdigest() != digest:
                raise RawStoreError("RAW_CORRUPT: существующий объект не совпадает с hash")

    @staticmethod
    def _sync_directory(path: Path) -> None:
        # У Windows нет переносимого directory fsync; гарантия power-loss не обещана.
        if os.name == "posix":
            descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)

    def _install(self, destination: Path, source: BinaryIO, size: int, digest: str) -> None:
        pending = None
        try:
            with tempfile.NamedTemporaryFile(mode="w+b", prefix=".pending-", dir=destination.parent,
                                             delete=False) as temporary:
                pending = Path(temporary.name)
                checksum = hashlib.sha256()
                seen = 0
                while block := source.read(64000):
                    seen += len(block)
                    if seen > size:
                        raise RawStoreError("RAW_SIZE: поток превышает заявленный размер")
                    checksum.update(block)
                    temporary.write(block)
                if seen != size or checksum.hexdigest() != digest:
                    raise RawStoreError("RAW_HASH: поток не совпадает с manifest")
                temporary.flush()
                os.fsync(temporary.fileno())
            try:
                # Hard link создаётся целиком и эксклюзивно на том же filesystem.
                # os.replace здесь неверен: он мог бы затереть существующий объект.
                os.link(pending, destination)
            except FileExistsError:
                self._verify(destination, size, digest)
            self._sync_directory(destination.parent)
        finally:
            if pending is not None:
                pending.unlink(missing_ok=True)  # Только собственный временный файл.

    def _prepare_root(self) -> None:
        if self.root.is_symlink():
            raise RawStoreError("RAW_ROOT: конечная ссылка недопустима")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        marker = self.root / self.MARKER
        digest = hashlib.sha256(self.IDENTITY).hexdigest()
        if marker.exists() or marker.is_symlink():
            self._verify(marker, len(self.IDENTITY), digest)
        else:
            if any(self.root.iterdir()):
                raise RawStoreError("RAW_ROOT: непустой каталог без маркера не присваивается")
            self._install(marker, io.BytesIO(self.IDENTITY), len(self.IDENTITY), digest)

    def _object_path(self, key: str) -> Path:
        # key формируется только describe(), не из имени пользовательского файла.
        target = self.root
        for component in key.split("/")[:-1]:
            target = target / component
            if target.is_symlink():
                raise RawStoreError("RAW_ROOT: ссылка внутри raw недопустима")
            target.mkdir(mode=0o700, exist_ok=True)
            self._sync_directory(target.parent)
        return self.root / key

    def persist(self, manifest: FileManifest, frozen: BinaryIO) -> None:
        """Данные, затем canonical manifest; БД начнётся после обоих объектов.

        Сбой может оставить один объект или пару без batch в БД. Это ожидаемый
        orphan, не опубликованный факт; удаления/recovery относятся к CG-104.
        """
        artifacts = self.describe(manifest)
        try:
            self._prepare_root()
            frozen.seek(0)
            self._install(self._object_path(artifacts.raw_object_key), frozen,
                          manifest.byte_count, manifest.content_sha256)
            self._install(self._object_path(artifacts.manifest_object_key),
                          io.BytesIO(artifacts.manifest_bytes), len(artifacts.manifest_bytes),
                          artifacts.manifest_sha256)
        except OSError:
            raise RawStoreError("RAW_IO: сохранение не подтверждено; нужны обычные файлы и hard links") from None
