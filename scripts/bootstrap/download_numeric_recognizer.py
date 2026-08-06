from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import tomllib
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "config/models/numeric-recognizer-v1.toml"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verify(directory: Path, config: dict[str, Any]) -> dict[str, Any]:
    model = config["model"]
    records = []
    for expected in model["files"]:
        path = directory / expected["path"]
        if (
            not path.is_file()
            or path.stat().st_size != int(expected["size_bytes"])
            or _sha256(path) != expected["sha256"]
        ):
            raise RuntimeError(f"numeric recognizer artifact drifted: {path}")
        records.append(
            {
                "path": expected["path"],
                "size_bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    weights = directory / model["weights_file"]
    if (
        weights.stat().st_size != int(model["weights_size_bytes"])
        or _sha256(weights) != model["weights_sha256"]
    ):
        raise RuntimeError("numeric recognizer weight identity drifted")
    return {
        "status": "VERIFIED",
        "directory": directory.as_posix(),
        "repo_id": model["repo_id"],
        "revision": model["revision"],
        "weights_size_bytes": weights.stat().st_size,
        "weights_sha256": _sha256(weights),
        "files": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Download the pinned numeric recognizer")
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    model = config["model"]
    destination = args.cache_root.resolve() / "official_models" / model["cache_directory"]
    if destination.exists():
        if not destination.is_dir():
            raise RuntimeError(f"numeric model destination is not a directory: {destination}")
        record = _verify(destination, config)
    elif args.verify_only:
        raise FileNotFoundError(f"numeric recognizer is absent: {destination}")
    else:
        from huggingface_hub import snapshot_download

        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix=f".{destination.name}.", dir=destination.parent
        ) as temporary:
            payload = Path(temporary) / "payload"
            snapshot_download(
                repo_id=model["repo_id"],
                revision=model["revision"],
                local_dir=payload,
            )
            record = _verify(payload, config)
            os.replace(payload, destination)
        record["directory"] = destination.as_posix()
        record["status"] = "DOWNLOADED_AND_VERIFIED"
    print(json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
