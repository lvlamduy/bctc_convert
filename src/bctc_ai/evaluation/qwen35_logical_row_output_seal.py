from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image

from bctc_ai.ocr.logical_row_label_reader_contract import (
    LogicalRowLabelReaderContractError,
    validate_logical_row_label_reader_request,
)
from bctc_ai.ocr.qwen35_logical_row_reader import (
    Qwen35LogicalRowReaderError,
    load_qwen35_logical_row_config,
    parse_qwen_transcription,
)


class Qwen35LogicalRowOutputSealError(RuntimeError):
    """Raised when the reference-blind Qwen output cannot be sealed."""


_STATE = "REFERENCE_BLIND_LOGICAL_ROW_LABEL_INFERENCE_COMPLETE"
_SEAL_STATE = "QWEN_OUTPUT_HASH_SEALED_BEFORE_REVIEW_ACCESS"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_GIT_COMMIT = re.compile(r"[0-9a-f]{40}")
_CANONICAL_CONFIG_PATH = Path("config/models/qwen35-27b-gptq-int4-rtx4090-v1.toml")
_RESULT_KEYS = {
    "format_version",
    "experiment_id",
    "reader",
    "state",
    "dataset_role",
    "evidence_role",
    "reference_text_available_to_reader",
    "sample_count",
    "samples",
    "authority",
}
_SAMPLE_KEYS = {
    "sample_id",
    "category",
    "crop_path",
    "crop_sha256",
    "crop_width",
    "crop_height",
    "input_token_count",
    "visual_token_count",
    "generated_token_ids",
    "forbidden_generated_control_token_ids",
    "raw_generated_output",
    "raw_output",
    "nonempty_line_count",
    "generated_token_count",
    "terminated_by_eos",
    "status",
    "proposal_text",
    "reader_score",
    "reader_score_available",
    "inference_seconds",
}
_MANIFEST_KEYS = {
    "format_version",
    "experiment_id",
    "reader",
    "state",
    "dataset_role",
    "evidence_role",
    "git_commit",
    "git_dirty",
    "authorization",
    "request",
    "crop_manifest",
    "configuration",
    "runtime",
    "metrics",
    "started_at",
    "completed_at",
    "safety",
    "artifacts",
}
_RUNTIME_KEYS = {
    "packages",
    "overlay_tree_identity",
    "torch_cuda",
    "gpu_name",
    "compute_capability",
    "bf16_supported",
    "host_available_memory_bytes_before_load",
    "host_available_memory_bytes_after_inference",
    "hf_device_map",
    "weight_map_coverage",
    "gptq_backend",
    "gptq_dynamic_exclusion_keys",
    "quantized_linear_module_count",
    "quantized_placeholder_initialization",
    "temporary_load_staging",
    "hard_watchdog",
    "vram_preflight",
    "model",
}
_METRIC_KEYS = {
    "model_load_seconds",
    "total_wall_seconds",
    "mechanism_probe",
    "sample_count",
    "parsed_proposal_count",
    "structural_rejection_count",
    "minimum_visual_tokens",
    "maximum_visual_tokens",
    "peak_gpu_memory_allocated_mib",
    "peak_gpu_memory_reserved_mib",
    "free_vram_bytes_after_inference",
    "total_vram_bytes",
}


def _git(project_root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


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
        raise Qwen35LogicalRowOutputSealError(f"{label} escapes its lexical root") from error
    current = anchor
    for component in relative.parts:
        current /= component
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            break
        except OSError as error:
            raise Qwen35LogicalRowOutputSealError(f"cannot inspect {label}: {current}") from error
        if stat.S_ISLNK(mode):
            raise Qwen35LogicalRowOutputSealError(f"{label} contains a symlink component")


def _project_path(project_root: Path, value: Path | str, label: str) -> Path:
    raw = Path(value)
    if raw.is_absolute() or not raw.parts or ".." in raw.parts:
        raise Qwen35LogicalRowOutputSealError(f"unsafe {label} path: {value}")
    path = project_root / raw
    _reject_symlink_components(path, project_root, label)
    return path


def _canonical_project_argument(
    project_root: Path,
    value: Path | str,
    canonical: Path,
    label: str,
) -> Path:
    raw = Path(value)
    if raw.is_absolute() or raw != canonical:
        raise Qwen35LogicalRowOutputSealError(f"{label} requires its canonical lexical path")
    return _project_path(project_root, raw, label)


@dataclass(frozen=True)
class _StableFile:
    path: Path
    payload: bytes
    identity: tuple[int, int, int, int, int, int]
    artifact: dict[str, Any]


def _read_stable_file(project_root: Path, path: Path, label: str) -> _StableFile:
    _reject_symlink_components(path, project_root, label)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise Qwen35LogicalRowOutputSealError(f"cannot open {label}: {path}") from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise Qwen35LogicalRowOutputSealError(f"{label} is not a regular file")
        chunks: list[bytes] = []
        while block := os.read(descriptor, 8 * 1024 * 1024):
            chunks.append(block)
        after = os.fstat(descriptor)
    except OSError as error:
        raise Qwen35LogicalRowOutputSealError(f"cannot read {label}: {path}") from error
    finally:
        os.close(descriptor)
    payload = b"".join(chunks)
    if _identity(before) != _identity(after) or len(payload) != before.st_size:
        raise Qwen35LogicalRowOutputSealError(f"{label} changed while being read")
    return _StableFile(
        path=path,
        payload=payload,
        identity=_identity(before),
        artifact={
            "path": path.relative_to(project_root).as_posix(),
            "size_bytes": before.st_size,
            "sha256": hashlib.sha256(payload).hexdigest(),
        },
    )


def _load_stable_json(
    project_root: Path, path: Path, label: str
) -> tuple[dict[str, Any], _StableFile]:
    stable = _read_stable_file(project_root, path, label)
    try:
        payload = json.loads(stable.payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Qwen35LogicalRowOutputSealError(f"cannot load {label}: {path}") from error
    if not isinstance(payload, dict):
        raise Qwen35LogicalRowOutputSealError(f"{label} must be an object")
    return payload, stable


def _artifact(project_root: Path, path: Path) -> dict[str, Any]:
    return _read_stable_file(project_root, path, "artifact").artifact


def _output_inventory_identity(
    output_directory: Path,
    expected_files: set[str],
) -> tuple[int, int, int, int, int, int]:
    try:
        directory_stat = output_directory.lstat()
        entries = list(os.scandir(output_directory))
    except OSError as error:
        raise Qwen35LogicalRowOutputSealError(
            "Qwen output directory is absent, unsafe, or not the exact two-file set"
        ) from error
    if (
        not stat.S_ISDIR(directory_stat.st_mode)
        or {entry.name for entry in entries} != expected_files
        or any(not entry.is_file(follow_symlinks=False) for entry in entries)
    ):
        raise Qwen35LogicalRowOutputSealError(
            "Qwen output directory is absent, unsafe, or not the exact two-file set"
        )
    return _identity(directory_stat)


def _assert_stable_file_unchanged(project_root: Path, original: _StableFile, label: str) -> None:
    current = _read_stable_file(project_root, original.path, label)
    if current.identity != original.identity or current.artifact != original.artifact:
        raise Qwen35LogicalRowOutputSealError(f"{label} changed after validation")


def _exclusive_atomic_write_json(destination: Path, payload: dict[str, Any]) -> None:
    serialized = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(destination, Path(destination.anchor), "Qwen seal")
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        directory_fd = os.open(destination.parent, directory_flags)
    except OSError as error:
        raise Qwen35LogicalRowOutputSealError("cannot open Qwen seal directory") from error
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        dir=destination.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary_path, 0o644)
        try:
            os.link(
                temporary_path.name,
                destination.name,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
                follow_symlinks=False,
            )
        except FileExistsError as error:
            raise Qwen35LogicalRowOutputSealError(
                f"refusing to overwrite Qwen seal: {destination}"
            ) from error
        os.fsync(directory_fd)
        flags = (
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        published_fd = os.open(destination.name, flags, dir_fd=directory_fd)
        try:
            digest = hashlib.sha256()
            while block := os.read(published_fd, 1024 * 1024):
                digest.update(block)
        finally:
            os.close(published_fd)
        if digest.hexdigest() != hashlib.sha256(serialized).hexdigest():
            raise Qwen35LogicalRowOutputSealError("Qwen seal hash mismatch after publication")
    finally:
        os.close(directory_fd)
        temporary_path.unlink(missing_ok=True)


def _is_nonnegative_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and value >= 0
    )


def _is_positive_int(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value > 0


def _timestamp(value: object, label: str) -> datetime:
    if not isinstance(value, str):
        raise Qwen35LogicalRowOutputSealError(f"{label} timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise Qwen35LogicalRowOutputSealError(f"{label} timestamp is invalid") from error
    if parsed.tzinfo is None:
        raise Qwen35LogicalRowOutputSealError(f"{label} timestamp lacks a timezone")
    return parsed.astimezone(UTC)


def _verify_request_crops(
    project_root: Path,
    request: dict[str, Any],
    samples: list[dict[str, str]],
) -> dict[str, tuple[int, int]]:
    crop_manifest = request["crop_manifest"]
    crop_manifest_path = _project_path(project_root, crop_manifest["path"], "crop manifest")
    crop_manifest_file = _read_stable_file(project_root, crop_manifest_path, "E-0035 crop manifest")
    if crop_manifest_file.artifact["sha256"] != crop_manifest["sha256"]:
        raise Qwen35LogicalRowOutputSealError("E-0035 crop manifest is absent or drifted")
    dimensions: dict[str, tuple[int, int]] = {}
    for sample in samples:
        crop = _project_path(project_root, sample["crop_path"], "logical-row crop")
        stable = _read_stable_file(project_root, crop, f"logical-row crop {sample['sample_id']}")
        if stable.artifact["sha256"] != sample["crop_sha256"]:
            raise Qwen35LogicalRowOutputSealError(
                f"logical-row crop is absent or drifted: {sample['sample_id']}"
            )
        try:
            with Image.open(io.BytesIO(stable.payload)) as image:
                dimensions[sample["sample_id"]] = image.size
                image.verify()
        except OSError as error:
            raise Qwen35LogicalRowOutputSealError(
                f"logical-row crop is invalid: {sample['sample_id']}"
            ) from error
    return dimensions


def _validate_sample(
    raw: object,
    request_sample: dict[str, str],
    config: dict[str, Any],
    expected_dimensions: tuple[int, int],
) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != _SAMPLE_KEYS:
        raise Qwen35LogicalRowOutputSealError("Qwen result sample fields drifted")
    for key in ("sample_id", "category", "crop_path", "crop_sha256"):
        if raw.get(key) != request_sample[key]:
            raise Qwen35LogicalRowOutputSealError(
                f"Qwen result sample identity drifted: {request_sample['sample_id']}"
            )
    inference = config["inference"]
    generated_ids = raw.get("generated_token_ids")
    forbidden_ids = raw.get("forbidden_generated_control_token_ids")
    if (
        not _is_positive_int(raw.get("crop_width"))
        or not _is_positive_int(raw.get("crop_height"))
        or (raw.get("crop_width"), raw.get("crop_height")) != expected_dimensions
        or not _is_positive_int(raw.get("input_token_count"))
        or raw["input_token_count"] + int(inference["maximum_new_tokens"])
        > int(inference["context_length"])
        or not _is_positive_int(raw.get("visual_token_count"))
        or not isinstance(generated_ids, list)
        or any(isinstance(value, bool) or not isinstance(value, int) for value in generated_ids)
        or not isinstance(forbidden_ids, list)
        or any(isinstance(value, bool) or not isinstance(value, int) for value in forbidden_ids)
        or not isinstance(raw.get("raw_generated_output"), str)
        or not isinstance(raw.get("raw_output"), str)
        or isinstance(raw.get("nonempty_line_count"), bool)
        or not isinstance(raw.get("nonempty_line_count"), int)
        or raw["nonempty_line_count"] < 0
        or isinstance(raw.get("generated_token_count"), bool)
        or not isinstance(raw.get("generated_token_count"), int)
        or raw["generated_token_count"] < 0
        or raw["generated_token_count"] > int(inference["maximum_new_tokens"])
        or len(generated_ids) != raw["generated_token_count"]
        or not isinstance(raw.get("terminated_by_eos"), bool)
        or not isinstance(raw.get("status"), str)
        or not isinstance(raw.get("proposal_text"), str)
        or raw.get("reader_score") is not None
        or raw.get("reader_score_available") is not False
        or not _is_nonnegative_number(raw.get("inference_seconds"))
    ):
        raise Qwen35LogicalRowOutputSealError("Qwen result sample value drifted")
    if not (
        int(inference["minimum_observed_visual_tokens"])
        <= raw["visual_token_count"]
        <= int(inference["maximum_observed_visual_tokens"])
    ):
        raise Qwen35LogicalRowOutputSealError("Qwen result visual-token envelope drifted")
    eos_ids = {int(value) for value in inference["eos_token_ids"]}
    if raw["terminated_by_eos"]:
        if not generated_ids or generated_ids[-1] not in eos_ids:
            raise Qwen35LogicalRowOutputSealError("Qwen result terminal EOS evidence drifted")
        content_ids = generated_ids[:-1]
    else:
        if generated_ids and generated_ids[-1] in eos_ids:
            raise Qwen35LogicalRowOutputSealError("Qwen result omitted terminal EOS state")
        content_ids = generated_ids
    expected_forbidden = sorted(
        {
            value
            for value in content_ids
            if int(inference["forbidden_generated_control_token_id_min"])
            <= value
            <= int(inference["forbidden_generated_control_token_id_max"])
        }
    )
    if forbidden_ids != expected_forbidden:
        raise Qwen35LogicalRowOutputSealError("Qwen generated-control-token evidence drifted")
    if raw["terminated_by_eos"]:
        expected_suffix = {
            248044: "<|endoftext|>",
            248046: "<|im_end|>",
        }.get(generated_ids[-1])
        if (
            expected_suffix is None
            or raw["raw_generated_output"] != raw["raw_output"] + expected_suffix
        ):
            raise Qwen35LogicalRowOutputSealError("Qwen raw/token decoding evidence drifted")
    elif raw["raw_generated_output"] != raw["raw_output"]:
        raise Qwen35LogicalRowOutputSealError("Qwen raw/token decoding evidence drifted")
    parsed = parse_qwen_transcription(
        raw["raw_output"],
        generated_token_count=raw["generated_token_count"],
        maximum_new_tokens=int(inference["maximum_new_tokens"]),
        terminated_by_eos=raw["terminated_by_eos"],
        maximum_nonempty_lines=int(inference["maximum_nonempty_output_lines"]),
        maximum_output_characters=int(inference["maximum_output_characters"]),
        prompt=str(inference["prompt"]),
    )
    if forbidden_ids:
        parsed = parsed | {"status": "REJECT_GENERATED_CONTROL_TOKEN", "proposal_text": ""}
    for key in (
        "nonempty_line_count",
        "generated_token_count",
        "terminated_by_eos",
        "status",
        "proposal_text",
    ):
        if raw[key] != parsed[key]:
            raise Qwen35LogicalRowOutputSealError(
                f"Qwen parsed sample evidence drifted: {request_sample['sample_id']}"
            )
    return raw


def _validate_result(
    payload: dict[str, Any],
    request_samples: list[dict[str, str]],
    config: dict[str, Any],
    crop_dimensions: dict[str, tuple[int, int]],
) -> list[dict[str, Any]]:
    expected_authority = {key: False for key in config["safety"]}
    if (
        set(payload) != _RESULT_KEYS
        or payload.get("format_version") != 1
        or payload.get("experiment_id") != "E-0036"
        or payload.get("reader") != "QWEN3_5_27B_GPTQ_INT4"
        or payload.get("state") != _STATE
        or payload.get("dataset_role") != "CALIBRATION"
        or payload.get("evidence_role") != config["evidence_role"]
        or payload.get("reference_text_available_to_reader") is not False
        or payload.get("sample_count") != len(request_samples)
        or payload.get("authority") != expected_authority
        or not isinstance(payload.get("samples"), list)
        or len(payload["samples"]) != len(request_samples)
    ):
        raise Qwen35LogicalRowOutputSealError("Qwen result identity drifted")
    return [
        _validate_sample(
            raw,
            request_sample,
            config,
            crop_dimensions[request_sample["sample_id"]],
        )
        for raw, request_sample in zip(payload["samples"], request_samples, strict=True)
    ]


def _expected_model_artifacts(config: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "key": key,
            "path": str(record["path"]),
            "size_bytes": int(record["size_bytes"]),
            "sha256": str(record["sha256"]),
        }
        for key, record in sorted(config["artifacts"].items())
    ]


def _validate_runtime(runtime: object, config: dict[str, Any]) -> None:
    if not isinstance(runtime, dict) or set(runtime) != _RUNTIME_KEYS:
        raise Qwen35LogicalRowOutputSealError("Qwen manifest runtime fields drifted")
    compatibility = config["runtime_compatibility"]
    overlay = config["runtime_overlay"]
    device_map = config["device_map"]
    expected_overlay = {
        "file_count": overlay["installed_tree_file_count"],
        "total_bytes": overlay["installed_tree_total_bytes"],
        "pyc_file_count": overlay["installed_tree_pyc_file_count"],
        "tree_sha256": overlay["installed_tree_sha256"],
    }
    expected_coverage = {
        "weight_index_tensor_count": device_map["expected_weight_index_tensor_count"],
        "device_map_covered_tensor_count": device_map["expected_device_map_covered_tensor_count"],
        "excluded_auxiliary_mtp_tensor_count": device_map[
            "expected_excluded_auxiliary_mtp_tensor_count"
        ],
    }
    if (
        runtime.get("packages") != compatibility["packages"]
        or runtime.get("overlay_tree_identity") != expected_overlay
        or runtime.get("torch_cuda") != compatibility["cuda_runtime"]
        or runtime.get("gpu_name") != "NVIDIA GeForce RTX 4090"
        or runtime.get("compute_capability") != compatibility["minimum_compute_capability"]
        or runtime.get("bf16_supported") is not True
        or not _is_nonnegative_number(runtime.get("host_available_memory_bytes_before_load"))
        or runtime["host_available_memory_bytes_before_load"]
        < compatibility["minimum_host_available_memory_bytes"]
        or not _is_nonnegative_number(runtime.get("host_available_memory_bytes_after_inference"))
        or runtime.get("hf_device_map")
        != {key: str(value) for key, value in device_map["modules"].items()}
        or runtime.get("weight_map_coverage") != expected_coverage
        or runtime.get("gptq_backend") != "gptq_triton"
        or runtime.get("gptq_dynamic_exclusion_keys")
        != sorted(config["quantization"]["dynamic_exclusion_keys"])
        or runtime.get("quantized_linear_module_count")
        != config["quantization"]["expected_quantized_linear_module_count"]
    ):
        raise Qwen35LogicalRowOutputSealError("Qwen manifest runtime identity drifted")
    placeholder = runtime.get("quantized_placeholder_initialization")
    if placeholder != {
        "mechanism": "GPTQ_META_AFTER_CPU_SOURCE_SHAPE_VALIDATION",
        "module_count": config["quantization"]["expected_quantized_linear_module_count"],
        "buffer_count": compatibility["native_shell_quantized_placeholder_buffer_count"],
        "buffer_names": compatibility["native_shell_quantized_placeholder_buffer_names"],
        "nominal_buffer_bytes": compatibility["native_shell_quantized_buffer_bytes"],
        "placeholder_device": compatibility["native_shell_quantized_placeholder_device"],
        "hooks_restored_after_load": True,
        "materialized_after_checkpoint_load": True,
    }:
        raise Qwen35LogicalRowOutputSealError("Qwen meta-placeholder evidence drifted")
    staging = runtime.get("temporary_load_staging")
    if (
        not isinstance(staging, dict)
        or set(staging)
        != {
            "persistent_weight_device_map_disk",
            "controlled_root",
            "ephemeral_directory_name",
            "triton_cache_is_ephemeral",
            "torchinductor_cache_is_ephemeral",
            "free_bytes_before_load",
            "minimum_free_bytes_required",
        }
        or staging.get("persistent_weight_device_map_disk") is not False
        or not isinstance(staging.get("controlled_root"), str)
        or not Path(staging["controlled_root"]).is_absolute()
        or not isinstance(staging.get("ephemeral_directory_name"), str)
        or not staging["ephemeral_directory_name"].startswith("qwen-e0036-load-")
        or staging.get("triton_cache_is_ephemeral") is not True
        or staging.get("torchinductor_cache_is_ephemeral") is not True
        or staging.get("minimum_free_bytes_required")
        != device_map["temporary_load_staging_minimum_free_bytes"]
        or not _is_nonnegative_number(staging.get("free_bytes_before_load"))
        or staging["free_bytes_before_load"] < staging["minimum_free_bytes_required"]
    ):
        raise Qwen35LogicalRowOutputSealError("Qwen temporary-load staging evidence drifted")
    watchdog = runtime.get("hard_watchdog")
    if watchdog != {
        "path": config["hard_watchdog"]["path"],
        "sha256": config["hard_watchdog"]["sha256"],
        "timeout_seconds_per_sample": config["inference"]["maximum_sample_inference_seconds"],
        "mechanism": "LINUX_PIDFD_EXTERNAL_SIGKILL",
    }:
        raise Qwen35LogicalRowOutputSealError("Qwen hard-watchdog evidence drifted")
    vram = runtime.get("vram_preflight")
    minimum_free = (
        device_map["estimated_registered_tensor_bytes_gpu"]
        + device_map["minimum_runtime_vram_headroom_bytes"]
    )
    if (
        not isinstance(vram, dict)
        or set(vram)
        != {
            "free_bytes_before_load",
            "minimum_free_bytes_required",
            "registered_gpu_tensor_bytes",
            "minimum_runtime_headroom_bytes",
        }
        or vram.get("minimum_free_bytes_required") != minimum_free
        or vram.get("registered_gpu_tensor_bytes")
        != device_map["estimated_registered_tensor_bytes_gpu"]
        or vram.get("minimum_runtime_headroom_bytes")
        != device_map["minimum_runtime_vram_headroom_bytes"]
        or not _is_nonnegative_number(vram.get("free_bytes_before_load"))
        or vram["free_bytes_before_load"] < minimum_free
    ):
        raise Qwen35LogicalRowOutputSealError("Qwen VRAM preflight evidence drifted")
    model = runtime.get("model")
    if (
        not isinstance(model, dict)
        or set(model) != {"repo_id", "revision", "quantization", "artifacts"}
        or model.get("repo_id") != config["model"]["repo_id"]
        or model.get("revision") != config["model"]["revision"]
        or model.get("quantization") != config["quantization"]
        or model.get("artifacts") != _expected_model_artifacts(config)
    ):
        raise Qwen35LogicalRowOutputSealError("Qwen manifest model evidence drifted")


def _validate_metrics(
    metrics: object,
    samples: list[dict[str, Any]],
    config: dict[str, Any],
) -> None:
    if not isinstance(metrics, dict) or set(metrics) != _METRIC_KEYS:
        raise Qwen35LogicalRowOutputSealError("Qwen manifest metric fields drifted")
    parsed_count = sum(item["status"] == "PARSED_SEMANTIC_PROPOSAL_ONLY" for item in samples)
    visual_tokens = [int(item["visual_token_count"]) for item in samples]
    first = samples[0]
    probe = metrics.get("mechanism_probe")
    model_load_for_projection = metrics.get("model_load_seconds")
    expected_projection = (
        float(model_load_for_projection)
        if _is_nonnegative_number(model_load_for_projection)
        else math.inf
    ) + (
        float(first["inference_seconds"])
        / max(1, int(first["generated_token_count"]))
        * int(config["inference"]["maximum_new_tokens"])
        * len(samples)
    )
    if (
        not all(
            _is_nonnegative_number(metrics.get(key))
            for key in (
                "model_load_seconds",
                "total_wall_seconds",
                "peak_gpu_memory_allocated_mib",
                "peak_gpu_memory_reserved_mib",
                "free_vram_bytes_after_inference",
                "total_vram_bytes",
            )
        )
        or metrics["total_wall_seconds"] < metrics["model_load_seconds"]
        or metrics.get("sample_count") != len(samples)
        or metrics.get("parsed_proposal_count") != parsed_count
        or metrics.get("structural_rejection_count") != len(samples) - parsed_count
        or metrics.get("minimum_visual_tokens") != min(visual_tokens)
        or metrics.get("maximum_visual_tokens") != max(visual_tokens)
        or metrics["free_vram_bytes_after_inference"] > metrics["total_vram_bytes"]
        or not isinstance(probe, dict)
        or set(probe)
        != {
            "sample_id",
            "inference_seconds",
            "generated_token_count",
            "projected_maximum_total_wall_seconds",
            "projection_policy",
        }
        or probe.get("sample_id") != first["sample_id"]
        or probe.get("inference_seconds") != first["inference_seconds"]
        or probe.get("generated_token_count") != first["generated_token_count"]
        or not _is_nonnegative_number(probe.get("projected_maximum_total_wall_seconds"))
        or not math.isclose(
            float(probe.get("projected_maximum_total_wall_seconds", -1)),
            expected_projection,
            rel_tol=1e-12,
            abs_tol=1e-9,
        )
        or probe["projected_maximum_total_wall_seconds"]
        > config["inference"]["maximum_projected_total_wall_seconds"]
        or first["inference_seconds"] > config["inference"]["maximum_mechanism_probe_seconds"]
        or probe.get("projection_policy") != "FIRST_CROP_SECONDS_PER_TOKEN_TIMES_96_TOKENS_TIMES_64"
    ):
        raise Qwen35LogicalRowOutputSealError("Qwen manifest metrics drifted")


def _validate_manifest(
    manifest: dict[str, Any],
    *,
    project_root: Path,
    current_commit: str,
    config: dict[str, Any],
    config_path: Path,
    config_artifact: dict[str, Any],
    authorization: dict[str, Any],
    authorization_path: Path,
    authorization_artifact: dict[str, Any],
    request: dict[str, Any],
    request_path: Path,
    request_artifact: dict[str, Any],
    samples: list[dict[str, Any]],
    result_artifact: dict[str, Any],
) -> None:
    if (
        set(manifest) != _MANIFEST_KEYS
        or manifest.get("format_version") != 1
        or manifest.get("experiment_id") != "E-0036"
        or manifest.get("reader") != "QWEN3_5_27B_GPTQ_INT4"
        or manifest.get("state") != _STATE
        or manifest.get("dataset_role") != "CALIBRATION"
        or manifest.get("evidence_role") != config["evidence_role"]
        or not isinstance(manifest.get("git_commit"), str)
        or _GIT_COMMIT.fullmatch(manifest["git_commit"]) is None
        or manifest["git_commit"] != current_commit
        or manifest.get("git_dirty") is not False
        or manifest.get("authorization")
        != {
            "path": authorization_path.relative_to(project_root).as_posix(),
            "sha256": authorization_artifact["sha256"],
            "decision": authorization["decision"],
            "reference_content_available_to_reader": False,
        }
        or manifest.get("request")
        != {
            "path": request_path.relative_to(project_root).as_posix(),
            "sha256": request_artifact["sha256"],
        }
        or manifest.get("crop_manifest") != request["crop_manifest"]
        or manifest.get("safety") != {key: False for key in config["safety"]}
        or manifest.get("artifacts")
        != {"ocr_result": result_artifact | {"path": "ocr_result.json"}}
    ):
        raise Qwen35LogicalRowOutputSealError("Qwen run manifest identity drifted")
    inference = config["inference"]
    expected_configuration = {
        "path": config_path.relative_to(project_root).as_posix(),
        "sha256": config_artifact["sha256"],
        "prompt": inference["prompt"],
        "aspect_preservation": inference["aspect_preservation"],
        "processor_min_pixels": inference["processor_min_pixels"],
        "processor_max_pixels": inference["processor_max_pixels"],
        "processor_use_fast": False,
        "context_length": inference["context_length"],
        "maximum_new_tokens": inference["maximum_new_tokens"],
        "enable_thinking": False,
        "do_sample": False,
        "network_policy": "PYTHON_AUDIT_ALL_SOCKET_EVENTS_DENIED",
        "deterministic_algorithms": True,
        "linear_attention_implementation": "TRANSFORMERS_TORCH_FALLBACK",
        "execution_model": "ONE_SHOT_PROCESS_REQUIRED",
        "network_audit_hook_persists_until_process_exit": True,
        "hard_watchdog_seconds_per_sample": inference["maximum_sample_inference_seconds"],
    }
    if manifest.get("configuration") != expected_configuration:
        raise Qwen35LogicalRowOutputSealError("Qwen manifest configuration drifted")
    _validate_runtime(manifest.get("runtime"), config)
    _validate_metrics(manifest.get("metrics"), samples, config)
    started = _timestamp(manifest.get("started_at"), "Qwen start")
    completed = _timestamp(manifest.get("completed_at"), "Qwen completion")
    if completed < started:
        raise Qwen35LogicalRowOutputSealError("Qwen manifest timestamps are reversed")


def seal_qwen35_logical_row_output(
    project_root: Path,
    *,
    config_path: Path,
    output_directory: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Validate and hash-seal the complete Qwen output without opening review data."""

    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise Qwen35LogicalRowOutputSealError("formal E-0036 Qwen seal requires clean Git")
    current_commit = _git(project_root, "rev-parse", "HEAD")
    supplied_config = _canonical_project_argument(
        project_root,
        config_path,
        _CANONICAL_CONFIG_PATH,
        "Qwen config",
    )
    try:
        config, authorization, model_config_path, authorization_path = (
            load_qwen35_logical_row_config(project_root, config_path)
        )
    except Qwen35LogicalRowReaderError as error:
        raise Qwen35LogicalRowOutputSealError(str(error)) from error
    if model_config_path != supplied_config:
        raise Qwen35LogicalRowOutputSealError("Qwen loader returned a noncanonical config path")
    config_file = _read_stable_file(project_root, model_config_path, "Qwen model config")
    authorization_file = _read_stable_file(
        project_root, authorization_path, "Qwen inference authorization"
    )
    if authorization_file.artifact["sha256"] != config["authorization"]["sha256"]:
        raise Qwen35LogicalRowOutputSealError("Qwen inference authorization drifted")
    canonical_output_relative = Path(str(config["output"]["directory"]))
    supplied_output = _canonical_project_argument(
        project_root,
        output_directory,
        canonical_output_relative,
        "Qwen output directory",
    )
    canonical_seal_relative = Path(str(config["output"]["seal_path"]))
    destination = _canonical_project_argument(
        project_root,
        output_path,
        canonical_seal_relative,
        "Qwen seal",
    )
    if destination.exists():
        raise Qwen35LogicalRowOutputSealError(f"refusing to overwrite Qwen seal: {destination}")
    expected_files = set(config["output"]["exact_files"])
    output_identity = _output_inventory_identity(supplied_output, expected_files)
    request_path = _project_path(project_root, config["request"]["path"], "Qwen request")
    request, request_file = _load_stable_json(project_root, request_path, "E-0036 Qwen request")
    if request_file.artifact["sha256"] != config["request"]["sha256"]:
        raise Qwen35LogicalRowOutputSealError("Qwen request is absent or hash-drifted")
    try:
        request_samples = validate_logical_row_label_reader_request(request)
    except LogicalRowLabelReaderContractError as error:
        raise Qwen35LogicalRowOutputSealError(str(error)) from error
    if len(request_samples) != config["request"]["sample_count"]:
        raise Qwen35LogicalRowOutputSealError("Qwen request denominator drifted")
    crop_dimensions = _verify_request_crops(project_root, request, request_samples)
    result_path = supplied_output / "ocr_result.json"
    manifest_path = supplied_output / "run_manifest.json"
    result, result_file = _load_stable_json(project_root, result_path, "Qwen result")
    samples = _validate_result(result, request_samples, config, crop_dimensions)
    result_artifact = result_file.artifact
    manifest, manifest_file = _load_stable_json(project_root, manifest_path, "Qwen run manifest")
    _validate_manifest(
        manifest,
        project_root=project_root,
        current_commit=current_commit,
        config=config,
        config_path=model_config_path,
        config_artifact=config_file.artifact,
        authorization=authorization,
        authorization_path=authorization_path,
        authorization_artifact=authorization_file.artifact,
        request=request,
        request_path=request_path,
        request_artifact=request_file.artifact,
        samples=samples,
        result_artifact=result_artifact,
    )
    manifest_artifact = manifest_file.artifact
    sealer_path = _project_path(project_root, config["output"]["sealer"]["path"], "Qwen sealer")
    capture_script_path = _project_path(
        project_root,
        config["output"]["capture_script"]["path"],
        "Qwen seal capture script",
    )
    status_counts: dict[str, int] = {}
    for sample in samples:
        status = str(sample["status"])
        status_counts[status] = status_counts.get(status, 0) + 1
    payload: dict[str, Any] = {
        "format_version": 1,
        "experiment_id": "E-0036",
        "state": _SEAL_STATE,
        "dataset_role": "CALIBRATION",
        "captured_at": datetime.now(UTC).isoformat(),
        "seal_git_commit": current_commit,
        "seal_git_dirty": False,
        "inference_git_commit": manifest["git_commit"],
        "model_config": config_file.artifact,
        "seal_algorithm": _artifact(project_root, sealer_path),
        "seal_capture_script": _artifact(project_root, capture_script_path),
        "authorization": authorization_file.artifact,
        "request": request_file.artifact,
        "crop_manifest": dict(request["crop_manifest"]),
        "reader": {
            "reader": "QWEN3_5_27B_GPTQ_INT4",
            "output_directory": supplied_output.relative_to(project_root).as_posix(),
            "result": result_artifact,
            "manifest": manifest_artifact,
            "sample_count": len(samples),
            "status_counts": dict(sorted(status_counts.items())),
            "metrics": manifest["metrics"],
            "reference_text_available_to_reader": False,
            "human_review_available_to_reader": False,
            "all_authority_flags": False,
        },
        "exact_output_file_count": 2,
        "same_ordered_sample_ids_as_request": True,
        "reference_or_human_review_loaded_by_sealer": False,
        "evaluation_allowed_only_after_this_seal": True,
        "authority": {
            "label_truth": False,
            "numeric_value_or_status": False,
            "geometry": False,
            "period_unit_scope": False,
            "report_norm_id_or_schema_mapping": False,
            "automatic_model_promotion": False,
        },
        "claim_boundary": (
            "This artifact seals the one canonical, complete reference-blind E-0036 Qwen "
            "output before reviewed labels or ReportNormIds are opened. It establishes output, "
            "runtime and request identity only; it makes no label, mapping, numeric, accounting, "
            "holdout or production claim."
        ),
    }
    if _git(project_root, "rev-parse", "HEAD") != current_commit or _git(
        project_root, "status", "--porcelain"
    ):
        raise Qwen35LogicalRowOutputSealError("Git code drifted during formal Qwen seal")
    _assert_stable_file_unchanged(project_root, result_file, "Qwen result")
    _assert_stable_file_unchanged(project_root, manifest_file, "Qwen run manifest")
    if _output_inventory_identity(supplied_output, expected_files) != output_identity:
        raise Qwen35LogicalRowOutputSealError("Qwen output directory changed after validation")
    _exclusive_atomic_write_json(destination, payload)
    return payload


__all__ = [
    "Qwen35LogicalRowOutputSealError",
    "seal_qwen35_logical_row_output",
]
