from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, replace
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


class SourceRegistryConflict(RuntimeError):
    pass


def _load_existing_registry(path: Path) -> dict[str, SourceRecord]:
    if not path.is_file():
        return {}
    records: dict[str, SourceRecord] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = SourceRecord(**json.loads(line))
        except (TypeError, json.JSONDecodeError) as exc:
            raise SourceRegistryConflict(
                f"invalid source registry record at {path}:{line_number}"
            ) from exc
        if record.relative_path in records:
            raise SourceRegistryConflict(
                f"duplicate source path in registry: {record.relative_path}"
            )
        records[record.relative_path] = record
    return records


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
    existing = _load_existing_registry(output_path)
    discovered_paths = {source.path.relative_to(project_root).as_posix() for source in sources}
    missing_paths = sorted(set(existing) - discovered_paths)
    if missing_paths:
        preview = ", ".join(missing_paths[:3])
        raise SourceRegistryConflict(
            f"{len(missing_paths)} registered source path(s) disappeared; first: {preview}"
        )
    timestamp = datetime.now(UTC).isoformat()
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        records = list(
            executor.map(lambda source: _hash_source(source, project_root, timestamp), sources)
        )
    reconciled = []
    for record in records:
        previous = existing.get(record.relative_path)
        if previous is not None and previous.sha256 != record.sha256:
            raise SourceRegistryConflict(
                "registered source content changed at path "
                f"{record.relative_path}: {previous.sha256} -> {record.sha256}"
            )
        if previous is not None:
            record = replace(
                record,
                registered_at=previous.registered_at,
                state=previous.state,
                immutable_copy=previous.immutable_copy,
            )
        reconciled.append(record)
    records = sorted(reconciled, key=lambda record: record.relative_path)
    atomic_write_jsonl(output_path, (asdict(record) for record in records))
    registry_hash = stable_records_hash(
        f"{record.sha256}  {record.relative_path}" for record in records
    )
    return records, registry_hash
