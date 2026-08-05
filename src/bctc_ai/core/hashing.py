from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path

DEFAULT_CHUNK_SIZE = 1024 * 1024


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path, chunk_size: int = DEFAULT_CHUNK_SIZE) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def stable_records_hash(lines: Iterable[str]) -> str:
    """Hash newline-delimited records after caller-defined stable ordering."""
    digest = hashlib.sha256()
    for line in lines:
        digest.update(line.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def source_tree_hash(root: Path, excluded: set[str] | None = None) -> str:
    excluded = excluded or set()
    records: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if any(relative == item or relative.startswith(f"{item}/") for item in excluded):
            continue
        records.append(f"{sha256_file(path)}  {relative}")
    return stable_records_hash(records)
