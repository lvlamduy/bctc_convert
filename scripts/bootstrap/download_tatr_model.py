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
DEFAULT_CONFIG = PROJECT_ROOT / "config/models/tatr-v1.1-all.toml"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_config(path: Path) -> dict[str, Any]:
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "CALIBRATION_ONLY_STRUCTURE_PROPOSAL":
        raise RuntimeError("TATR config is not calibration-only")
    safety = payload.get("safety", {})
    if not safety or any(bool(value) for value in safety.values()):
        raise RuntimeError("TATR config grants forbidden authority")
    return payload


def _verify_model(directory: Path, config: dict[str, Any]) -> dict[str, Any]:
    records = []
    total_bytes = 0
    for key, artifact in sorted(config["artifacts"].items()):
        path = directory / str(artifact["path"])
        if not path.is_file():
            raise FileNotFoundError(f"missing pinned TATR artifact: {path}")
        size = path.stat().st_size
        digest = _sha256_file(path)
        if size != int(artifact["size_bytes"]):
            raise RuntimeError(f"TATR artifact size mismatch: {path}")
        if digest != str(artifact["sha256"]):
            raise RuntimeError(f"TATR artifact SHA-256 mismatch: {path}")
        total_bytes += size
        records.append(
            {
                "key": key,
                "path": str(artifact["path"]),
                "size_bytes": size,
                "sha256": digest,
            }
        )
    if total_bytes != int(config["required_artifact_bytes"]):
        raise RuntimeError(
            f"TATR required-artifact byte count mismatch: {total_bytes} "
            f"!= {config['required_artifact_bytes']}"
        )
    return {
        "status": "VERIFIED",
        "directory": directory.as_posix(),
        "repo_id": config["model"]["repo_id"],
        "revision": config["model"]["revision"],
        "required_artifact_bytes": total_bytes,
        "artifacts": records,
    }


def _download_model(directory: Path, config: dict[str, Any]) -> dict[str, Any]:
    from huggingface_hub import snapshot_download

    directory.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{directory.name}.", dir=directory.parent) as temp:
        payload = Path(temp) / "payload"
        snapshot_download(
            repo_id=str(config["model"]["repo_id"]),
            revision=str(config["model"]["revision"]),
            local_dir=payload,
            allow_patterns=[str(item["path"]) for item in config["artifacts"].values()],
        )
        record = _verify_model(payload, config)
        os.replace(payload, directory)
    record["directory"] = directory.as_posix()
    record["status"] = "DOWNLOADED_AND_VERIFIED"
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch the hash-pinned TATR v1.1 All model")
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--verify-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = _load_config(args.config.resolve())
    destination = args.cache_root.resolve() / "official_models" / config["cache_directory"]
    if destination.exists():
        if not destination.is_dir():
            raise RuntimeError(f"TATR model destination is not a directory: {destination}")
        record = _verify_model(destination, config)
    elif args.verify_only:
        raise FileNotFoundError(f"TATR model is absent in verify-only mode: {destination}")
    else:
        record = _download_model(destination, config)
    print(json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
