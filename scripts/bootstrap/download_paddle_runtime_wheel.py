from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import tomllib
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_MANIFEST = PROJECT_ROOT / "config/models/gpu-runtime.toml"
ARTIFACT_KEY = "paddlepaddle_cpu_cp311_linux_x86_64"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verify(path: Path, config: dict[str, object]) -> dict[str, object]:
    if not path.is_file():
        raise FileNotFoundError(f"missing Paddle wheel: {path}")
    size = path.stat().st_size
    expected_size = int(config["size_bytes"])
    if size != expected_size:
        raise RuntimeError(f"Paddle wheel size mismatch at {path}: {size} != {expected_size}")
    digest = _sha256(path)
    expected_digest = str(config["sha256"])
    if digest != expected_digest:
        raise RuntimeError(
            f"Paddle wheel SHA-256 mismatch at {path}: {digest} != {expected_digest}"
        )
    return {
        "path": path.as_posix(),
        "size_bytes": size,
        "sha256": digest,
        "status": "VERIFIED",
    }


def _download(path: Path, config: dict[str, object]) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        str(config["url"]), headers={"User-Agent": "bctc-ai-pinned-runtime/1"}
    )
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{path.name}.", suffix=".partial", dir=path.parent, delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
            with urllib.request.urlopen(request, timeout=60) as response:
                shutil.copyfileobj(response, temporary, length=1024 * 1024)
        record = _verify(temporary_path, config)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    record["path"] = path.as_posix()
    record["status"] = "DOWNLOADED_AND_VERIFIED"
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch the hash-pinned Paddle runtime wheel")
    parser.add_argument("--destination-directory", type=Path, required=True)
    parser.add_argument("--verify-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = tomllib.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    config = manifest["artifacts"][ARTIFACT_KEY]
    destination = args.destination_directory.resolve() / str(config["filename"])
    if destination.exists():
        record = _verify(destination, config)
    elif args.verify_only:
        raise FileNotFoundError(f"Paddle wheel is absent in verify-only mode: {destination}")
    else:
        record = _download(destination, config)
    print(json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
