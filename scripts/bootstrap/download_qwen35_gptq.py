from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import tomllib
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = Path("config/models/qwen35-27b-gptq-int4-rtx4090-v1.toml")
E0036_CONTROL = Path("config/experiments/e0036-mbb-cdkt-semantic-label-readers.yaml")
DOWNLOADER_PATH = Path("scripts/bootstrap/download_qwen35_gptq.py")
EXPECTED_STATUS = "CONDITIONAL_E0036_CALIBRATION_ONLY_REFERENCE_BLIND_QWEN_CHALLENGER"
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _identity(value: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _reject_symlink_components(path: Path, anchor: Path, label: str) -> None:
    try:
        relative = path.relative_to(anchor)
    except ValueError as error:
        raise RuntimeError(f"{label} escapes its lexical root") from error
    current = anchor
    for component in relative.parts:
        current /= component
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            break
        if stat.S_ISLNK(mode):
            raise RuntimeError(f"{label} contains a symlink component")


def _project_path(relative: Path | str, label: str) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or not raw.parts or ".." in raw.parts:
        raise RuntimeError(f"{label} is not a safe relative path")
    path = PROJECT_ROOT / raw
    _reject_symlink_components(path, PROJECT_ROOT, label)
    return path


def _absolute_lexical_path(path: Path, label: str) -> Path:
    if not path.is_absolute() or ".." in path.parts:
        raise RuntimeError(f"{label} must be an absolute lexical path")
    _reject_symlink_components(path, Path(path.anchor), label)
    return path


def _sha256_file_with_identity(path: Path, label: str) -> tuple[str, os.stat_result]:
    digest = hashlib.sha256()
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise RuntimeError(f"cannot open {label}: {path}") from error
    byte_count = 0
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise RuntimeError(f"{label} is not a regular file")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                byte_count += len(block)
                digest.update(block)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if _identity(before) != _identity(after) or byte_count != before.st_size:
        raise RuntimeError(f"{label} changed while being hashed")
    return digest.hexdigest(), before


def _sha256_file(path: Path) -> str:
    digest, _ = _sha256_file_with_identity(path, "Qwen artifact")
    return digest


def _read_stable_bytes(path: Path, label: str) -> tuple[bytes, os.stat_result]:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise RuntimeError(f"cannot open {label}: {path}") from error
    chunks: list[bytes] = []
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise RuntimeError(f"{label} is not a regular file")
        while block := os.read(descriptor, 1024 * 1024):
            chunks.append(block)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    payload = b"".join(chunks)
    if _identity(before) != _identity(after) or len(payload) != before.st_size:
        raise RuntimeError(f"{label} changed while being read")
    return payload, before


def _verify_control_record(record: object, expected_path: Path, label: str) -> None:
    if (
        not isinstance(record, dict)
        or set(record) != {"path", "sha256", "size_bytes"}
        or record.get("path") != expected_path.as_posix()
        or _SHA256.fullmatch(str(record.get("sha256", ""))) is None
        or isinstance(record.get("size_bytes"), bool)
        or not isinstance(record.get("size_bytes"), int)
        or record["size_bytes"] < 1
    ):
        raise RuntimeError(f"canonical E-0036 {label} record drifted")
    path = _project_path(expected_path, f"E-0036 {label}")
    digest, identity = _sha256_file_with_identity(path, f"E-0036 {label}")
    if digest != record["sha256"] or identity.st_size != record["size_bytes"]:
        raise RuntimeError(f"canonical E-0036 {label} artifact drifted")


def _load_control_implementation() -> dict[str, Any]:
    control_path = _project_path(E0036_CONTROL, "E-0036 control")
    try:
        payload = yaml.safe_load(_read_stable_bytes(control_path, "E-0036 control")[0])
    except yaml.YAMLError as error:
        raise RuntimeError("cannot load canonical E-0036 control") from error
    challenger = payload.get("conditional_qwen_challenger") if isinstance(payload, dict) else None
    implementation = challenger.get("implementation") if isinstance(challenger, dict) else None
    if (
        not isinstance(payload, dict)
        or payload.get("experiment_id") != "E-0036"
        or not isinstance(implementation, dict)
    ):
        raise RuntimeError("canonical E-0036 control identity drifted")
    return implementation


def _load_config(path: Path) -> dict[str, Any]:
    if Path(path) != DEFAULT_CONFIG or Path(path).is_absolute():
        raise RuntimeError("Qwen config must use its canonical lexical path")
    implementation = _load_control_implementation()
    _verify_control_record(implementation.get("model_config"), DEFAULT_CONFIG, "model config")
    _verify_control_record(implementation.get("downloader"), DOWNLOADER_PATH, "downloader")
    config_path = _project_path(DEFAULT_CONFIG, "Qwen config")
    config_bytes, _ = _read_stable_bytes(config_path, "Qwen config")
    model_record = implementation["model_config"]
    if hashlib.sha256(config_bytes).hexdigest() != model_record["sha256"]:
        raise RuntimeError("canonical E-0036 model config changed during loading")
    try:
        payload = tomllib.loads(config_bytes.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise RuntimeError("cannot load canonical Qwen config") from error
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
    directory = _absolute_lexical_path(directory, "Qwen model directory")
    if not directory.is_dir():
        raise RuntimeError(f"Qwen3.5 GPTQ model directory is unsafe: {directory}")
    records: list[dict[str, Any]] = []
    registered_paths: set[str] = set()
    total_bytes = 0
    for key, artifact in sorted(config["artifacts"].items()):
        relative = Path(str(artifact["path"]))
        if relative.is_absolute() or not relative.parts or ".." in relative.parts:
            raise RuntimeError(f"Qwen3.5 GPTQ artifact escapes model directory: {key}")
        path = directory / relative
        _reject_symlink_components(path, directory, f"Qwen model artifact {key}")
        digest, identity = _sha256_file_with_identity(path, f"Qwen model artifact {key}")
        size = identity.st_size
        if size != int(artifact["size_bytes"]):
            raise RuntimeError(f"Qwen3.5 GPTQ artifact size mismatch: {path}")
        if digest != str(artifact["sha256"]):
            raise RuntimeError(f"Qwen3.5 GPTQ artifact SHA-256 mismatch: {path}")
        total_bytes += size
        registered_paths.add(path.relative_to(directory).as_posix())
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
    actual_paths: set[str] = set()
    actual_directories: set[str] = set()
    for path in directory.rglob("*"):
        relative = path.relative_to(directory).as_posix()
        mode = path.lstat().st_mode
        if stat.S_ISREG(mode):
            actual_paths.add(relative)
        elif stat.S_ISDIR(mode):
            actual_directories.add(relative)
        else:
            raise RuntimeError("Qwen3.5 GPTQ directory contains a non-regular filesystem entry")
    registered_directories = {
        parent.as_posix()
        for registered in registered_paths
        for parent in Path(registered).parents
        if parent != Path(".")
    }
    if actual_paths != registered_paths or actual_directories != registered_directories:
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
        relative = Path(str(artifact["path"]))
        if relative.is_absolute() or not relative.parts or ".." in relative.parts:
            continue
        path = directory / relative
        try:
            _reject_symlink_components(path, directory, "Qwen partial artifact")
            identity = path.lstat()
        except (FileNotFoundError, RuntimeError):
            continue
        if stat.S_ISREG(identity.st_mode) and identity.st_size == int(artifact["size_bytes"]):
            present += identity.st_size
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
    directory = _absolute_lexical_path(directory, "Qwen model destination")
    revision = str(config["model"]["revision"])
    staging = directory.parent / f".{directory.name}.{revision[:12]}.partial"
    _reject_symlink_components(staging, Path(staging.anchor), "Qwen model staging")
    if staging.exists() and not staging.is_dir():
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
    config = _load_config(args.config)
    raw_cache_root = Path(args.cache_root)
    if not raw_cache_root.is_absolute():
        raw_cache_root = PROJECT_ROOT / raw_cache_root
    cache_root = _absolute_lexical_path(raw_cache_root, "Qwen model cache root")
    if not cache_root.is_dir():
        raise RuntimeError(f"Qwen3.5 GPTQ cache root is unsafe: {cache_root}")
    destination = cache_root / "official_models" / config["cache_directory"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(destination, Path(destination.anchor), "Qwen model destination")
    if destination.exists():
        if not destination.is_dir():
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
