from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from bctc_ai.core.atomic import atomic_write_jsonl
from bctc_ai.core.hashing import sha256_file, stable_records_hash
from bctc_ai.ingestion.discovery import DiscoveredSource


@dataclass(frozen=True)
class SourceRecord:
    document_id: str
    sha256: str
    size_bytes: int
    relative_path: str
    kind: str
    bank: str | None
    year: int | None
    registered_at: str
    source_mtime_ns: int
    hash_verified_stable: bool
    state: str = "REGISTERED"
    immutable_copy: str | None = None


def _hash_source(source: DiscoveredSource, project_root: Path, timestamp: str) -> SourceRecord:
    before = source.path.stat()
    digest = sha256_file(source.path)
    after = source.path.stat()
    stable = before.st_size == after.st_size and before.st_mtime_ns == after.st_mtime_ns
    if not stable:
        # One retry handles an atomic upload completing while the first read was
        # in flight. If it changes again, the record is retained but explicitly
        # cannot be treated as frozen.
        before = after
        digest = sha256_file(source.path)
        after = source.path.stat()
        stable = before.st_size == after.st_size and before.st_mtime_ns == after.st_mtime_ns
    return SourceRecord(
        document_id=f"sha256:{digest}",
        sha256=digest,
        size_bytes=source.path.stat().st_size,
        relative_path=source.path.relative_to(project_root).as_posix(),
        kind=source.kind,
        bank=source.bank,
        year=source.year,
        registered_at=timestamp,
        source_mtime_ns=after.st_mtime_ns,
        hash_verified_stable=stable,
    )


def register_sources(
    sources: list[DiscoveredSource],
    project_root: Path,
    output_path: Path,
    *,
    workers: int = 4,
) -> tuple[list[SourceRecord], str]:
    timestamp = datetime.now(UTC).isoformat()
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        records = list(
            executor.map(lambda source: _hash_source(source, project_root, timestamp), sources)
        )
    records.sort(key=lambda record: record.relative_path)
    atomic_write_jsonl(output_path, (asdict(record) for record in records))
    registry_hash = stable_records_hash(
        f"{record.sha256}  {record.relative_path}" for record in records
    )
    return records, registry_hash
