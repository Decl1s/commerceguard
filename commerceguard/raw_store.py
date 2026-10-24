"""Локальные content-addressed объекты. Код написан без исполнения.

Отдельный user-owned root; конкурентный враждебный процесс с правом менять его
родителей вне модели угроз. Никаких исходных имён файлов, путей из JSON и overwrite.
"""

from dataclasses import dataclass
import hashlib
import io
import os
from pathlib import Path
import re
import tempfile
from typing import BinaryIO

from .file_contracts import FileManifest, canonical_manifest_bytes
from .file_inputs import read_manifest, regular_file


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

    def _read_path(self, key: str) -> Path:
        """При чтении я не создаю каталоги и не следую ссылкам внутри raw root."""
        target = self.root
        if target.is_symlink() or not target.is_dir():
            raise RawStoreError("RAW_ROOT: собственный raw root недоступен")
        for part in key.split("/")[:-1]:
            target = target / part
            if target.is_symlink() or not target.is_dir():
                raise RawStoreError("RAW_LAYOUT: каталог объекта недоступен")
        return self.root / key

    def require_owned_root(self) -> None:
        try:
            marker = self._read_path(self.MARKER)
            self._verify(marker, len(self.IDENTITY), hashlib.sha256(self.IDENTITY).hexdigest())
        except OSError:
            raise RawStoreError("RAW_IO: чтение raw root не подтверждено") from None

    def resolve_manifest(self, digest: str, *, verify_data: bool = True) -> tuple[FileManifest, Path, Path]:
        """Я восстанавливаю пути только из hash и подтверждённого envelope."""
        if re.fullmatch(r"[a-f0-9]{64}", digest) is None:
            raise RawStoreError("MANIFEST_KEY: нужен SHA-256 в нижнем регистре")
        try:
            self.require_owned_root()
            manifest_path = self._read_path(f"manifests/{digest[:2]}/{digest}.json")
            manifest = read_manifest(manifest_path)
            artifacts = self.describe(manifest)
            if artifacts.manifest_sha256 != digest:
                raise RawStoreError("MANIFEST_HASH: envelope не соответствует имени объекта")
            self._verify(manifest_path, len(artifacts.manifest_bytes), digest)
            data_path = self._read_path(artifacts.raw_object_key)
            if verify_data:
                self._verify(data_path, manifest.byte_count, manifest.content_sha256)
            else:
                # В обзорном сканировании я проверяю тип/размер, но не читаю до 100 MB на объект.
                with regular_file(data_path, "raw") as data:
                    if os.fstat(data.fileno()).st_size != manifest.byte_count:
                        raise RawStoreError("RAW_SIZE: размер объекта отличается от manifest")
            return manifest, manifest_path, data_path
        except OSError:
            raise RawStoreError("RAW_IO: объекты восстановления недоступны") from None

    def discover(self, limit: int) -> tuple[list[str], bool, int]:
        """Я ограничиваю обзор: truncated означает неполный список, а не отсутствие orphan."""
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise RawStoreError("SCAN_LIMIT: разрешено от 1 до 1000 объектов")
        self.require_owned_root()
        found = []
        ignored = 0
        try:
            manifests = self.root / "manifests"
            if not manifests.exists():
                return [], False, 0
            self._read_path("manifests/probe")
            # 256 фиксированных shard исключают произвольную рекурсию по чужому дереву.
            for number in range(256):
                shard = manifests / f"{number:02x}"
                if not shard.exists():
                    continue
                self._read_path(f"manifests/{number:02x}/probe")
                with os.scandir(shard) as entries:
                    for entry in entries:
                        if len(found) + ignored >= limit:
                            return found, True, ignored
                        match = re.fullmatch(r"([a-f0-9]{64})\.json", entry.name)
                        if (not match or not match[1].startswith(shard.name)
                                or not entry.is_file(follow_symlinks=False)):
                            ignored += 1  # Имена посторонних файлов в отчёт не включаю.
                        else:
                            found.append(match[1])
            return found, False, ignored
        except OSError:
            raise RawStoreError("RAW_IO: сканирование не подтверждено") from None
