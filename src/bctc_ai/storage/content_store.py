from __future__ import annotations

import os
import tempfile
from pathlib import Path

from bctc_ai.core.hashing import sha256_file


class ContentStoreIntegrityError(RuntimeError):
    pass


def content_path(store_root: Path, digest: str, suffix: str) -> Path:
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ValueError("digest must be a lowercase SHA-256 hex string")
    safe_suffix = suffix.casefold() if suffix else ".bin"
    if not safe_suffix.startswith(".") or "/" in safe_suffix or "\\" in safe_suffix:
        raise ValueError("invalid content suffix")
    return store_root / "sha256" / digest[:2] / f"{digest}{safe_suffix}"


def materialize_immutable(source: Path, store_root: Path) -> tuple[Path, str]:
    source = source.resolve()
    digest = sha256_file(source)
    destination = content_path(store_root.resolve(), digest, source.suffix)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if sha256_file(destination) != digest:
            raise ContentStoreIntegrityError(f"existing content has wrong hash: {destination}")
        return destination, digest

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with source.open("rb") as input_stream, os.fdopen(descriptor, "wb") as output_stream:
            while chunk := input_stream.read(1024 * 1024):
                output_stream.write(chunk)
            output_stream.flush()
            os.fsync(output_stream.fileno())
        if sha256_file(temporary) != digest:
            raise ContentStoreIntegrityError(f"copy verification failed for {source}")
        try:
            os.link(temporary, destination)
        except FileExistsError:
            if sha256_file(destination) != digest:
                raise ContentStoreIntegrityError(
                    f"concurrent content has wrong hash: {destination}"
                ) from None
        destination.chmod(0o444)
        directory_fd = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return destination, digest
    finally:
        temporary.unlink(missing_ok=True)
