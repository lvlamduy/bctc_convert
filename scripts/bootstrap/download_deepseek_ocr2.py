from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import tomllib
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "config/models/deepseek-ocr2-v1.toml"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_config(path: Path) -> dict[str, Any]:
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "CALIBRATION_ONLY_SEMANTIC_OCR_PROPOSAL":
        raise RuntimeError("DeepSeek-OCR-2 config is not calibration-only")
    safety = payload.get("safety", {})
    if not safety or any(bool(value) for value in safety.values()):
        raise RuntimeError("DeepSeek-OCR-2 config grants forbidden authority")
    inference = payload.get("inference", {})
    if inference.get("network_permitted") is not False:
        raise RuntimeError("DeepSeek-OCR-2 inference must be offline")
    if inference.get("target_policy") != "FAILED_OR_AMBIGUOUS_REGIONS_ONLY":
        raise RuntimeError("DeepSeek-OCR-2 target policy is too broad")
    return payload


def _verify_model(directory: Path, config: dict[str, Any]) -> dict[str, Any]:
    records = []
    total_bytes = 0
    for key, artifact in sorted(config["artifacts"].items()):
        path = directory / str(artifact["path"])
        if not path.is_file():
            raise FileNotFoundError(f"missing pinned DeepSeek-OCR-2 artifact: {path}")
        size = path.stat().st_size
        digest = _sha256_file(path)
        if size != int(artifact["size_bytes"]):
            raise RuntimeError(f"DeepSeek-OCR-2 artifact size mismatch: {path}")
        if digest != str(artifact["sha256"]):
            raise RuntimeError(f"DeepSeek-OCR-2 artifact SHA-256 mismatch: {path}")
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
            "DeepSeek-OCR-2 required-artifact byte count mismatch: "
            f"{total_bytes} != {config['required_artifact_bytes']}"
        )
    return {
        "status": "VERIFIED",
        "directory": directory.as_posix(),
        "repo_id": config["model"]["repo_id"],
        "revision": config["model"]["revision"],
        "required_artifact_bytes": total_bytes,
        "artifacts": records,
    }


def _preflight_capacity(parent: Path, config: dict[str, Any]) -> dict[str, int]:
    usage = shutil.disk_usage(parent)
    required = int(config["required_artifact_bytes"])
    reserve = int(config["minimum_free_bytes_after_download"])
    if usage.free < required + reserve:
        raise RuntimeError(
            "insufficient cache filesystem space for DeepSeek-OCR-2: "
            f"free={usage.free}, required={required}, reserve={reserve}"
        )
    return {
        "free_bytes_before": usage.free,
        "required_artifact_bytes": required,
        "minimum_free_bytes_after_download": reserve,
    }


def _download_model(directory: Path, config: dict[str, Any]) -> dict[str, Any]:
    capacity = _preflight_capacity(directory.parent, config)
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    os.environ.setdefault("HF_HOME", str(directory.parent / ".hf-home"))
    from huggingface_hub import snapshot_download

    directory.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{directory.name}.", dir=directory.parent) as temp:
        payload = Path(temp) / "payload"
        snapshot_download(
            repo_id=str(config["model"]["repo_id"]),
            revision=str(config["model"]["revision"]),
            local_dir=payload,
            allow_patterns=[str(item["path"]) for item in config["artifacts"].values()],
            max_workers=1,
        )
        record = _verify_model(payload, config)
        os.replace(payload, directory)
    record["directory"] = directory.as_posix()
    record["status"] = "DOWNLOADED_AND_VERIFIED"
    record["capacity_preflight"] = capacity
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch the hash-pinned official DeepSeek-OCR-2 model"
    )
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--verify-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = _load_config(args.config.resolve())
    destination = args.cache_root.resolve() / "official_models" / config["cache_directory"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if not destination.is_dir():
            raise RuntimeError(
                f"DeepSeek-OCR-2 destination is not a directory: {destination}"
            )
        record = _verify_model(destination, config)
    elif args.verify_only:
        raise FileNotFoundError(
            f"DeepSeek-OCR-2 is absent in verify-only mode: {destination}"
        )
    else:
        record = _download_model(destination, config)
    print(json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
