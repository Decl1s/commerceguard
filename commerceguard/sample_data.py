"""Я формирую воспроизводимые учебные файлы, не используя часы и реальные выгрузки."""

import csv
from datetime import datetime
import hashlib
import io
import json
import os
from pathlib import Path

from .file_contracts import FileManifest, OMS_COLUMNS, canonical_manifest_bytes


class SampleDataError(ValueError):
    """Я скрываю абсолютные пути и сообщения файловой системы."""


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _manifest(data: bytes, source: str, rows: int, observed: str) -> bytes:
    manifest = FileManifest(
        contract_version=1, source=source, merchant_id="M01",
        content_sha256=hashlib.sha256(data).hexdigest(), row_count=rows, byte_count=len(data),
        observed_at=_timestamp(observed),
        effective_at=_timestamp("2026-10-23T00:00:00Z") if source == "oms" else None,
        is_complete=True if source == "oms" else None,
    )
    return canonical_manifest_bytes(manifest)


def sample_files(scenario: str) -> dict[str, bytes]:
    """Я отделяю чистое построение байтов от записи файлов, не вызываю reconcile."""
    if scenario not in {"baseline", "invalid-json", "conflict", "earlier-observed"}:
        raise SampleDataError("Неизвестный учебный сценарий")
    csv_text = io.StringIO(newline="")
    writer = csv.writer(csv_text, lineterminator="\n")
    writer.writerow(OMS_COLUMNS)
    for order_id, capture, refund, deadline in (
        ("O1001", 10000, 0, "2026-10-23T12:00:00Z"),
        ("O1002", 12000, 0, "2026-10-23T12:00:00Z"),
        ("O1003", 15000, 3000, "2026-10-23T12:00:00Z"),
        ("O1004", 5000, 0, "2026-10-25T12:00:00Z"),
        ("O1005", 5000, 0, "2026-10-23T12:00:00Z"),
    ):
        writer.writerow(("M01", order_id, "RUB", capture, refund, deadline))
    oms = csv_text.getvalue().encode("utf-8")

    def event(event_id, order_id, amount, kind="capture", currency="RUB", observed="2026-10-22T10:01:00Z"):
        return dict(merchant_id="M01", source_event_id=event_id, order_id=order_id,
                    currency=currency, kind=kind, amount_minor=amount,
                    occurred_at="2026-10-22T10:00:00Z", observed_at=observed)

    events = [event("C01", "O1001", 10000), event("C01", "O1001", 10000),
              event("C02", "O1002", 11000), event("C03", "O1003", 15000),
              event("R03", "O1003", 1000, kind="refund"),
              event("C05", "O1005", 5000, currency="USD"), event("C99", "O1999", 7000)]
    if scenario == "conflict":
        events[1]["amount_minor"] = 10001
    if scenario == "earlier-observed":
        events[0]["observed_at"] = "2026-10-22T10:00:30Z"
    lines = [json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n" for value in events]
    if scenario == "invalid-json":
        lines[-1] = '{"broken":\n'  # Я сохраняю верный file hash для намеренно сломанной JSON-строки.
    psp = "".join(lines).encode("utf-8")
    late = (json.dumps(event("C02L", "O1002", 1000, observed="2026-10-25T12:00:00Z"),
                       sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    return {
        "oms.csv": oms,
        "oms.manifest.json": _manifest(oms, "oms", 5, "2026-10-24T12:00:00Z"),
        "psp.jsonl": psp,
        "psp.manifest.json": _manifest(psp, "psp", 7, "2026-10-24T12:00:00Z"),
        "psp-late.jsonl": late,
        "psp-late.manifest.json": _manifest(late, "psp", 1, "2026-10-25T12:00:00Z"),
    }


def generate_inputs(output: Path, *, scenario: str = "baseline") -> dict:
    """Я создаю только новый каталог. При сбое оставляю его для ручного разбора."""
    files = sample_files(scenario)
    created = False
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.mkdir(mode=0o700)  # exist_ok=False: чужой каталог, даже пустой, не присваиваю.
        created = True
        for name, content in files.items():
            with (output / name).open("xb") as destination:
                destination.write(content)
                destination.flush()
                os.fsync(destination.fileno())
        # Последний файл — свидетельство завершения записи набора, не тестов программы.
        with (output / "GENERATED.md").open("x", encoding="utf-8", newline="\n") as guide:
            guide.write("# Учебный вход CommerceGuard\n\n"
                        f"Я сформировал сценарий {scenario}. Данные синтетические.\n"
                        "Путь: inspect → publish OMS/PSP → status → точный replay.\n"
                        "Поздний PSP вынесен отдельно; фактический результат надо смотреть в своей БД.\n"
                        "Полный маршрут и ручные ориентиры: docs/WORKBENCH.md в исходниках.\n")
        return {"action": "generate", "scenario": scenario, "files": sorted(files) + ["GENERATED.md"],
                "oms_rows": 5, "psp_rows": 7, "late_psp_rows": 1, "database_actions": 0}
    except OSError:
        message = ("Запись набора не завершена; каталог может быть частичным. Выбери новое имя."
                   if created else "Нужен доступный новый каталог; существующий каталог не заменяю.")
        raise SampleDataError(message) from None
