from __future__ import annotations

import fcntl
import json
from datetime import UTC, datetime
from pathlib import Path

from bctc_ai.core.atomic import atomic_write_jsonl
from bctc_ai.core.contracts import DatasetRole


class DatasetRoleConflict(ValueError):
    pass


def _read(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def assign_dataset_role(
    registry_path: Path,
    *,
    document_id: str,
    role: DatasetRole,
    source_path: str,
) -> dict[str, object]:
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = registry_path.with_suffix(registry_path.suffix + ".lock")
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        records = _read(registry_path)
        existing = next(
            (record for record in records if record["document_id"] == document_id), None
        )
        if existing:
            if existing["dataset_role"] != role.value:
                raise DatasetRoleConflict(
                    f"{document_id} is already frozen as {existing['dataset_role']}; "
                    f"cannot relabel it {role.value}"
                )
            return existing
        record: dict[str, object] = {
            "document_id": document_id,
            "dataset_role": role.value,
            "source_path": source_path,
            "assigned_at": datetime.now(UTC).isoformat(),
            "immutable": True,
        }
        records.append(record)
        records.sort(key=lambda item: str(item["document_id"]))
        atomic_write_jsonl(registry_path, records)
        return record
