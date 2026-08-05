from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from bctc_ai.core.hashing import sha256_bytes, sha256_file


class AtomicWriteError(RuntimeError):
    pass


def atomic_write_bytes(path: Path, payload: bytes, *, mode: int = 0o644) -> str:
    """Durably replace a generated artifact and verify its SHA-256 digest.

    Source inputs must never be passed to this function. Generated artifacts
    are written in the destination directory, fsynced, renamed atomically, and
    verified after the rename.
    """

    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    expected = sha256_bytes(payload)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary_path, mode)
        os.replace(temporary_path, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        actual = sha256_file(path)
        if actual != expected:
            raise AtomicWriteError(f"hash mismatch after atomic write: {path}")
        return actual
    finally:
        temporary_path.unlink(missing_ok=True)


def atomic_write_text(path: Path, text: str) -> str:
    return atomic_write_bytes(path, text.encode("utf-8"))


def atomic_write_json(path: Path, value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    return atomic_write_text(path, payload)


def atomic_write_jsonl(path: Path, records: Iterable[Mapping[str, Any]]) -> str:
    payload = "".join(
        json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records
    )
    return atomic_write_text(path, payload)
