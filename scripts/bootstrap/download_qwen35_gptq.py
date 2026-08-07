from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tomllib
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "config/models/qwen35-27b-gptq-int4-rtx4090-v1.toml"
EXPECTED_STATUS = "CONDITIONAL_E0036_CALIBRATION_ONLY_REFERENCE_BLIND_QWEN_CHALLENGER"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_config(path: Path) -> dict[str, Any]:
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    inference = payload.get("inference")
    quantization = payload.get("quantization")
    safety = payload.get("safety")
    artifacts = payload.get("artifacts")
    if (
        payload.get("version") != 1
        or payload.get("status") != EXPECTED_STATUS
        or payload.get("model_key") != "QWEN3_5_27B_GPTQ_INT4"
        or payload.get("reader") != "QWEN3_5_27B_GPTQ_INT4"
        or not isinstance(inference, dict)
        or inference.get("network_permitted") is not False
        or inference.get("reference_text_available_to_decoder") is not False
        or inference.get("target_policy")
        != "UNCHANGED_E0036_FROZEN_64_LOGICAL_ROW_LABEL_CROPS_ONLY"
        or not isinstance(quantization, dict)
        or quantization.get("method") != "GPTQ"
        or quantization.get("bits") != 4
        or quantization.get("official_prequantized_weights") is not True
        or not isinstance(safety, dict)
        or not safety
        or any(bool(value) for value in safety.values())
        or not isinstance(artifacts, dict)
        or len(artifacts) != 24
    ):
        raise RuntimeError("Qwen3.5 GPTQ config identity or safety boundary drifted")
    required = payload.get("required_artifact_bytes")
    if isinstance(required, bool) or not isinstance(required, int) or required < 1:
        raise RuntimeError("Qwen3.5 GPTQ required-artifact byte count is invalid")
    if sum(int(item["size_bytes"]) for item in artifacts.values()) != required:
        raise RuntimeError("Qwen3.5 GPTQ artifact registry byte count drifted")
    return payload


def _verify_model(directory: Path, config: dict[str, Any]) -> dict[str, Any]:
    if not directory.is_dir() or directory.is_symlink():
        raise RuntimeError(f"Qwen3.5 GPTQ model directory is unsafe: {directory}")
    records: list[dict[str, Any]] = []
    registered_paths: set[str] = set()
    total_bytes = 0
    for key, artifact in sorted(config["artifacts"].items()):
        path = (directory / str(artifact["path"])).resolve()
        if not path.is_relative_to(directory.resolve()):
            raise RuntimeError(f"Qwen3.5 GPTQ artifact escapes model directory: {key}")
        if path.is_symlink() or not path.is_file():
            raise FileNotFoundError(f"missing pinned Qwen3.5 GPTQ artifact: {path}")
        size = path.stat().st_size
        if size != int(artifact["size_bytes"]):
            raise RuntimeError(f"Qwen3.5 GPTQ artifact size mismatch: {path}")
        digest = _sha256_file(path)
        if digest != str(artifact["sha256"]):
            raise RuntimeError(f"Qwen3.5 GPTQ artifact SHA-256 mismatch: {path}")
        total_bytes += size
        registered_paths.add(path.relative_to(directory.resolve()).as_posix())
        records.append(
            {
                "key": key,
                "path": str(artifact["path"]),
                "size_bytes": size,
                "sha256": digest,
            }
        )
    if total_bytes != int(config["required_artifact_bytes"]):
        raise RuntimeError("Qwen3.5 GPTQ verified artifact byte count drifted")
    actual_paths = {
        path.relative_to(directory).as_posix()
        for path in directory.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    if actual_paths != registered_paths:
        extra = sorted(actual_paths - registered_paths)
        missing = sorted(registered_paths - actual_paths)
        raise RuntimeError(
            "Qwen3.5 GPTQ directory is not the exact registered file set: "
            f"extra={extra[:3]}, missing={missing[:3]}"
        )
    return {
        "status": "VERIFIED",
        "directory": directory.as_posix(),
        "repo_id": config["model"]["repo_id"],
        "revision": config["model"]["revision"],
        "required_artifact_bytes": total_bytes,
        "artifacts": records,
    }


def _registered_complete_bytes(directory: Path, config: dict[str, Any]) -> int:
    present = 0
    for artifact in config["artifacts"].values():
        path = directory / str(artifact["path"])
        if path.is_file() and path.stat().st_size == int(artifact["size_bytes"]):
            present += path.stat().st_size
    return present


def _preflight_capacity(
    parent: Path,
    config: dict[str, Any],
    *,
    staging: Path | None = None,
) -> dict[str, int]:
    usage = shutil.disk_usage(parent)
    required = int(config["required_artifact_bytes"])
    already_present = _registered_complete_bytes(staging, config) if staging else 0
    remaining = required - already_present
    reserve = int(config["minimum_free_bytes_after_download"])
    if usage.free < remaining + reserve:
        raise RuntimeError(
            "insufficient cache filesystem space for Qwen3.5 GPTQ: "
            f"free={usage.free}, remaining={remaining}, reserve={reserve}"
        )
    return {
        "free_bytes_before": usage.free,
        "required_artifact_bytes": required,
        "registered_complete_bytes_already_present": already_present,
        "remaining_registered_bytes": remaining,
        "minimum_free_bytes_after_download": reserve,
    }


def _download_model(directory: Path, config: dict[str, Any]) -> dict[str, Any]:
    revision = str(config["model"]["revision"])
    staging = directory.parent / f".{directory.name}.{revision[:12]}.partial"
    if staging.exists() and (not staging.is_dir() or staging.is_symlink()):
        raise RuntimeError(f"unsafe Qwen3.5 GPTQ staging path: {staging}")
    staging.mkdir(parents=True, exist_ok=True)
    capacity = _preflight_capacity(directory.parent, config, staging=staging)
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    os.environ.setdefault("HF_HOME", str(directory.parent / ".hf-home"))
    from huggingface_hub import snapshot_download

    snapshot_download(
        repo_id=str(config["model"]["repo_id"]),
        revision=revision,
        local_dir=staging,
        allow_patterns=[str(item["path"]) for item in config["artifacts"].values()],
        max_workers=1,
    )
    metadata = staging / ".cache" / "huggingface"
    if metadata.exists():
        if metadata.is_symlink() or not metadata.is_dir():
            raise RuntimeError(f"unsafe Hugging Face staging metadata: {metadata}")
        shutil.rmtree(metadata)
    metadata_parent = staging / ".cache"
    if metadata_parent.exists() and metadata_parent.is_dir() and not any(metadata_parent.iterdir()):
        metadata_parent.rmdir()
    record = _verify_model(staging, config)
    if directory.exists():
        raise RuntimeError(f"Qwen3.5 GPTQ destination appeared during download: {directory}")
    os.replace(staging, directory)
    record["directory"] = directory.as_posix()
    record["status"] = "DOWNLOADED_AND_VERIFIED"
    record["capacity_preflight"] = capacity
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch the hash-pinned official Qwen3.5-27B GPTQ-Int4 challenger"
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
        if not destination.is_dir() or destination.is_symlink():
            raise RuntimeError(f"Qwen3.5 GPTQ destination is not a safe directory: {destination}")
        record = _verify_model(destination, config)
    elif args.verify_only:
        raise FileNotFoundError(f"Qwen3.5 GPTQ is absent in verify-only mode: {destination}")
    else:
        record = _download_model(destination, config)
    print(json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
