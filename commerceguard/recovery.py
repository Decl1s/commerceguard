"""Я сопоставляю сохранённый manifest с БД и повторяю полный протокол приёма."""

from pathlib import Path

from .file_contracts import FileInputError
from .ingest_journal import schema_guard
from .postgres import postgres_session
from .raw_store import RawStore, RawStoreError


def scan_raw(raw_root: Path, *, limit: int = 100, dsn_env: str = "COMMERCEGUARD_DATABASE_URL") -> dict:
    store = RawStore(raw_root)
    digests, truncated, ignored = store.discover(limit)
    candidates = []
    for digest in digests:
        try:
            store.resolve_manifest(digest, verify_data=False)
            candidates.append({"manifest_sha256": digest, "status": "unregistered",
                               "data_hash": "not_checked"})
        except (FileInputError, RawStoreError):
            candidates.append({"manifest_sha256": digest, "status": "damaged",
                               "data_hash": "not_checked"})
    # Один короткий снимок БД для всего ограниченного обзора. Я не беру ownership
    # чужих каталогов и не превращаю отсутствие строки в доказательство rollback.
    with postgres_session(dsn_env, application_name="commerceguard-discovery") as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                schema_guard(cursor, write=False)
                cursor.execute(
                    "SELECT manifest_sha256, state FROM commerceguard.ingest_batch "
                    "WHERE manifest_sha256 = ANY(%s::text[])", (digests,),
                )
                batches = dict(cursor.fetchall())
                cursor.execute(
                    "SELECT DISTINCT ON (manifest_sha256) manifest_sha256, state "
                    "FROM commerceguard.ingest_attempt WHERE manifest_sha256 = ANY(%s::text[]) "
                    "ORDER BY manifest_sha256, started_at DESC, attempt_id DESC", (digests,),
                )
                attempts = dict(cursor.fetchall())
    for item in candidates:
        if item["status"] == "damaged":
            continue
        digest = item["manifest_sha256"]
        if digest in batches:
            item["status"] = "published" if batches[digest] == "published" else "blocked"
        elif digest in attempts:
            state = attempts[digest]
            item["status"] = state if state in {"quarantined", "failed"} else "unknown"
        else:
            item["status"] = "orphan"
    return {"action": "scan-raw", "items": candidates, "truncated": truncated,
            "ignored_entries": ignored, "automatic_actions": 0}


def recover_input(raw_root: Path, manifest_sha256: str, *, dsn_env: str = "COMMERCEGUARD_DATABASE_URL"):
    """Я перепроверяю точные объекты, затем вызываю тот же COPY/EOF/publish путь."""
    from .ingestion import publish_input

    _, manifest_path, data_path = RawStore(raw_root).resolve_manifest(manifest_sha256)
    return publish_input(manifest_path, data_path, raw_root, dsn_env=dsn_env)
