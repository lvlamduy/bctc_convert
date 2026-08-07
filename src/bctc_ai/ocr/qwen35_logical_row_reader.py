from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import json
import os
import re
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image

from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import normalize_text
from bctc_ai.ocr.logical_row_label_reader_contract import (
    LogicalRowLabelReaderContractError,
    validate_logical_row_label_reader_request,
)


class Qwen35LogicalRowReaderError(RuntimeError):
    """Raised when the reference-blind Qwen challenger fails closed."""


EXPECTED_STATUS = "CONDITIONAL_E0036_CALIBRATION_ONLY_REFERENCE_BLIND_QWEN_CHALLENGER"
AUTHORIZATION_KEYS = {
    "authorization_scope",
    "dataset_role",
    "decision",
    "derived_from_reviewed_evaluation_sha256",
    "experiment_id",
    "format_version",
    "model",
    "reference_labels_ids_values_or_periods_available_to_reader",
    "request",
    "state",
    "triggered",
}
_SHA256 = re.compile(r"[0-9a-f]{64}")
_FORBIDDEN_OUTPUT = re.compile(
    r"(?:<\|[^>]*\|>|</?(?:think|tool_call|tool_response)>|</?table>|```|^\s*assistant\s*:)",
    re.IGNORECASE | re.MULTILINE,
)
_TRANSCRIPTION_PREAMBLE = re.compile(
    r"(?:the transcription is|here is the transcription|transcription|visible text is)\s*:",
    re.IGNORECASE,
)
_OVERLAY_DISTRIBUTIONS = (
    "accelerate",
    "datasets",
    "defuser",
    "device-smi",
    "dill",
    "gptqmodel",
    "logbar",
    "maturin",
    "multiprocess",
    "ninja",
    "numpy",
    "optimum",
    "pyarrow",
    "pypcre",
    "tokenicer",
    "torchao",
    "xxhash",
)
_OVERLAY_IMPORT_ROOTS = (
    "accelerate",
    "datasets",
    "defuser",
    "device_smi",
    "dill",
    "gptqmodel",
    "logbar",
    "maturin",
    "multiprocess",
    "ninja",
    "numpy",
    "optimum",
    "pyarrow",
    "pcre",
    "tokenicer",
    "torchao",
    "xxhash",
)


def _expected_device_map() -> dict[str, str]:
    return {
        "model.visual": "cuda:0",
        "model.language_model.embed_tokens": "cuda:0",
        **{f"model.language_model.layers.{index}": "cuda:0" for index in range(38)},
        **{f"model.language_model.layers.{index}": "cpu" for index in range(38, 64)},
        "model.language_model.norm": "cuda:0",
        "lm_head": "cuda:0",
    }


def _load_toml(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise Qwen35LogicalRowReaderError(f"cannot load {label}: {path}") from error
    if not isinstance(payload, dict):
        raise Qwen35LogicalRowReaderError(f"{label} must be a TOML object")
    return payload


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise Qwen35LogicalRowReaderError(f"cannot load {label}: {path}") from error
    if not isinstance(payload, dict):
        raise Qwen35LogicalRowReaderError(f"{label} must be a JSON object")
    return payload


def _project_path(project_root: Path, value: str, label: str) -> Path:
    path = (project_root / value).resolve()
    if not path.is_relative_to(project_root):
        raise Qwen35LogicalRowReaderError(f"{label} escapes project root")
    return path


def _git(project_root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _verify_bound_file(
    project_root: Path,
    record: dict[str, Any],
    label: str,
) -> Path:
    if not {"path", "sha256"} <= set(record):
        raise Qwen35LogicalRowReaderError(f"{label} identity is incomplete")
    path = _project_path(project_root, str(record["path"]), label)
    if not path.is_file() or sha256_file(path) != record["sha256"]:
        raise Qwen35LogicalRowReaderError(f"{label} is absent or hash-drifted")
    expected_size = record.get("size_bytes")
    if expected_size is not None and path.stat().st_size != int(expected_size):
        raise Qwen35LogicalRowReaderError(f"{label} size drifted")
    return path


def _verify_authorization(
    project_root: Path,
    config: dict[str, Any],
) -> tuple[dict[str, Any], Path]:
    identity = config.get("authorization")
    if not isinstance(identity, dict):
        raise Qwen35LogicalRowReaderError("Qwen authorization identity is missing")
    path = _verify_bound_file(project_root, identity, "Qwen inference authorization")
    authorization = _load_json(path, "Qwen inference authorization")
    model = authorization.get("model")
    request = authorization.get("request")
    expected_model = config["model"]
    if (
        set(authorization) != AUTHORIZATION_KEYS
        or authorization.get("format_version") != 1
        or authorization.get("experiment_id") != "E-0036"
        or authorization.get("dataset_role") != "CALIBRATION"
        or authorization.get("state") != identity.get("required_state")
        or authorization.get("decision") != identity.get("required_decision")
        or authorization.get("triggered") is not True
        or authorization.get("authorization_scope") != "UNCHANGED_E0036_FROZEN_64_CROP_REQUEST_ONLY"
        or authorization.get("reference_labels_ids_values_or_periods_available_to_reader")
        is not False
        or identity.get("reference_content_available_to_reader") is not False
        or not isinstance(model, dict)
        or set(model) != {"quantization", "repo_id", "revision"}
        or model.get("repo_id") != expected_model.get("repo_id")
        or model.get("revision") != expected_model.get("revision")
        or model.get("quantization") != "OFFICIAL_GPTQ_INT4"
        or not isinstance(request, dict)
        or set(request) != {"sample_count", "sha256"}
        or request.get("sample_count") != config["request"].get("sample_count")
        or request.get("sha256") != config["request"].get("sha256")
        or _SHA256.fullmatch(str(authorization.get("derived_from_reviewed_evaluation_sha256", "")))
        is None
    ):
        raise Qwen35LogicalRowReaderError("Qwen inference authorization drifted")
    return authorization, path


def load_qwen35_logical_row_config(
    project_root: Path,
    config_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], Path, Path]:
    project_root = project_root.resolve()
    resolved = (
        config_path.resolve()
        if config_path.is_absolute()
        else _project_path(project_root, config_path.as_posix(), "Qwen config")
    )
    if not resolved.is_relative_to(project_root):
        raise Qwen35LogicalRowReaderError("Qwen config escapes project root")
    config = _load_toml(resolved, "Qwen config")
    model = config.get("model")
    quantization = config.get("quantization")
    inference = config.get("inference")
    device_map = config.get("device_map")
    compatibility = config.get("runtime_compatibility")
    overlay = config.get("runtime_overlay")
    artifacts = config.get("artifacts")
    safety = config.get("safety")
    request = config.get("request")
    hard_watchdog = config.get("hard_watchdog")
    if (
        config.get("version") != 1
        or config.get("status") != EXPECTED_STATUS
        or config.get("model_key") != "QWEN3_5_27B_GPTQ_INT4"
        or config.get("reader") != "QWEN3_5_27B_GPTQ_INT4"
        or config.get("geometry_authority") != "PP_OCRV6_WORD_BOXES"
        or config.get("evidence_role") != "VIETNAMESE_LOGICAL_ROW_LABEL_PROPOSAL_ONLY"
        or not isinstance(model, dict)
        or model.get("repo_id") != "Qwen/Qwen3.5-27B-GPTQ-Int4"
        or model.get("revision") != "8f0c09f227ae570e79617c6d9172b59df9c16081"
        or model.get("architecture") != "Qwen3_5ForConditionalGeneration"
        or model.get("model_type") != "qwen3_5"
        or not isinstance(quantization, dict)
        or quantization.get("method") != "GPTQ"
        or quantization.get("bits") != 4
        or quantization.get("group_size") != 128
        or quantization.get("symmetric") is not True
        or quantization.get("desc_act") is not False
        or quantization.get("official_prequantized_weights") is not True
        or quantization.get("runtime") != "GPTQMODEL"
        or quantization.get("runtime_bits") != 4
        or quantization.get("format") != "gptq"
        or quantization.get("lm_head") is not False
        or quantization.get("pack_dtype") != "torch.int32"
        or quantization.get("backend") != "gptq_triton"
        or quantization.get("loader") != "GPTQModel.from_quantized"
        or quantization.get("expected_quantized_linear_module_count") != 192
        or quantization.get("dynamic_exclusion_keys")
        != [
            "lm_head",
            "model.language_model.embed_tokens",
            "-:.*attn.*",
            "-:.*shared_expert.*",
            "-:.*mtp.*",
            "-:.*visual.*",
        ]
        or not isinstance(inference, dict)
        or inference.get("prompt")
        != (
            "Transcribe exactly the visible Vietnamese text in this crop. "
            "Do not correct spelling. Do not normalize. Do not infer missing text. "
            "Return only the transcription."
        )
        or inference.get("network_permitted") is not False
        or inference.get("reference_text_available_to_decoder") is not False
        or inference.get("target_policy")
        != "UNCHANGED_E0036_FROZEN_64_LOGICAL_ROW_LABEL_CROPS_ONLY"
        or inference.get("aspect_preservation") != "QWEN_SMART_RESIZE_NO_SQUARE_STRETCH"
        or inference.get("processor_min_pixels") != 65536
        or inference.get("processor_max_pixels") != 1048576
        or inference.get("processor_use_fast") is not False
        or inference.get("linear_attention_implementation") != "TRANSFORMERS_TORCH_FALLBACK"
        or inference.get("context_length") != 4096
        or inference.get("maximum_new_tokens") != 96
        or inference.get("maximum_output_characters") != 512
        or inference.get("maximum_nonempty_output_lines") != 4
        or inference.get("minimum_observed_visual_tokens") != 66
        or inference.get("maximum_observed_visual_tokens") != 108
        or inference.get("enable_thinking") is not False
        or inference.get("do_sample") is not False
        or inference.get("eos_token_ids") != [248044, 248046]
        or inference.get("pad_token_id") != 248044
        or inference.get("attention_implementation") != "sdpa"
        or inference.get("use_cache") is not True
        or inference.get("execution_model") != "ONE_SHOT_PROCESS_REQUIRED"
        or inference.get("one_shot_worker_environment_variable") != "BCTC_QWEN35_ONE_SHOT_WORKER"
        or inference.get("mechanism_probe_sample_count") != 1
        or inference.get("maximum_mechanism_probe_seconds") != 900
        or inference.get("maximum_sample_inference_seconds") != 900
        or inference.get("maximum_projected_total_wall_seconds") != 21600
        or inference.get("forbidden_generated_control_token_id_min") != 248045
        or inference.get("forbidden_generated_control_token_id_max") != 248076
        or inference.get("expected_assistant_prompt_suffix")
        != "<|im_start|>assistant\n<think>\n\n</think>\n\n"
        or not isinstance(device_map, dict)
        or device_map.get("strategy") != "EXPLICIT_LAYER_SPLIT_38_GPU_26_CPU"
        or device_map.get("persistent_weight_device_map_disk_permitted") is not False
        or device_map.get("temporary_load_staging_required") is not True
        or device_map.get("temporary_load_staging_minimum_free_bytes") != 17179869184
        or device_map.get("gpu_and_cpu_both_required") is not True
        or not isinstance(device_map.get("modules"), dict)
        or device_map["modules"] != _expected_device_map()
        or device_map.get("estimated_registered_tensor_bytes_gpu") != 19899114624
        or device_map.get("estimated_registered_tensor_bytes_cpu") != 9486530400
        or device_map.get("excluded_auxiliary_mtp_tensor_bytes") != 849398784
        or device_map.get("minimum_runtime_vram_headroom_bytes") != 4294967296
        or device_map.get("expected_weight_index_tensor_count") != 1775
        or device_map.get("expected_device_map_covered_tensor_count") != 1760
        or device_map.get("expected_excluded_auxiliary_mtp_tensor_count") != 15
        or not isinstance(compatibility, dict)
        or compatibility.get("python_major_minor") != "3.11"
        or compatibility.get("gpu_family") != "NVIDIA_GEFORCE_RTX_4090_ADA"
        or compatibility.get("minimum_compute_capability") != [8, 9]
        or compatibility.get("bf16_supported_required") is not True
        or compatibility.get("minimum_host_available_memory_bytes") != 42949672960
        or compatibility.get("native_shell_probe_without_weights") != "PASS_192_GPTQ_MLP_MODULES"
        or compatibility.get("native_shell_probe_peak_rss_bytes") != 10209718272
        or compatibility.get("native_shell_quantized_buffer_bytes") != 8897691976
        or compatibility.get("native_shell_lazy_remaining_parameter_bytes") != 20487936480
        or not isinstance(overlay, dict)
        or overlay.get("installed_tree_distributions") != list(_OVERLAY_DISTRIBUTIONS)
        or overlay.get("installed_tree_import_roots") != list(_OVERLAY_IMPORT_ROOTS)
        or overlay.get("installed_tree_file_count") != 3347
        or overlay.get("installed_tree_total_bytes") != 260712989
        or overlay.get("installed_tree_pyc_file_count") != 1
        or overlay.get("installed_tree_sha256")
        != "d703e549fad8a65f86b137695f8a2bab3f6b77cbb39289220aa136cfe7feeeba"
        or not isinstance(artifacts, dict)
        or len(artifacts) != 24
        or sum(int(item["size_bytes"]) for item in artifacts.values())
        != config.get("required_artifact_bytes")
        or not isinstance(safety, dict)
        or not safety
        or any(bool(value) for value in safety.values())
        or not isinstance(request, dict)
        or request.get("sha256")
        != "ad4c1a9fecf9686249a9c4eea2a5b6a2a903fc4716536e5804c481facc217781"
        or request.get("sample_count") != 64
        or not isinstance(hard_watchdog, dict)
        or hard_watchdog.get("ready_timeout_seconds") != 5
    ):
        raise Qwen35LogicalRowReaderError("Qwen logical-row configuration drifted")
    for key, sha_key in (
        ("base_runtime_manifest", "base_runtime_manifest_sha256"),
        ("requirements_path", "requirements_sha256"),
    ):
        path = _project_path(project_root, str(overlay.get(key, "")), f"Qwen {key}")
        if not path.is_file() or sha256_file(path) != overlay.get(sha_key):
            raise Qwen35LogicalRowReaderError(f"Qwen runtime control drifted: {key}")
    authorization, authorization_path = _verify_authorization(project_root, config)
    _verify_bound_file(project_root, hard_watchdog, "Qwen hard watchdog")
    return config, authorization, resolved, authorization_path


def _verify_model(model_directory: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    if not model_directory.is_dir() or model_directory.is_symlink():
        raise Qwen35LogicalRowReaderError("Qwen model directory is absent or unsafe")
    records: list[dict[str, Any]] = []
    registered_paths: set[str] = set()
    total_bytes = 0
    for key, raw in sorted(config["artifacts"].items()):
        path = (model_directory / str(raw.get("path", ""))).resolve()
        if not path.is_relative_to(model_directory.resolve()):
            raise Qwen35LogicalRowReaderError("Qwen model artifact escapes model directory")
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size != int(raw.get("size_bytes", -1))
            or sha256_file(path) != str(raw.get("sha256", ""))
        ):
            raise Qwen35LogicalRowReaderError(f"Qwen model artifact is absent or drifted: {key}")
        total_bytes += path.stat().st_size
        registered_paths.add(path.relative_to(model_directory.resolve()).as_posix())
        records.append(
            {
                "key": key,
                "path": str(raw["path"]),
                "size_bytes": path.stat().st_size,
                "sha256": str(raw["sha256"]),
            }
        )
    if total_bytes != int(config["required_artifact_bytes"]):
        raise Qwen35LogicalRowReaderError("Qwen verified artifact byte count drifted")
    actual_paths = {
        path.relative_to(model_directory).as_posix()
        for path in model_directory.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    if actual_paths != registered_paths:
        extra = sorted(actual_paths - registered_paths)
        missing = sorted(registered_paths - actual_paths)
        raise Qwen35LogicalRowReaderError(
            "Qwen model directory is not the exact registered file set: "
            f"extra={extra[:3]}, missing={missing[:3]}"
        )
    return records


def _verify_weight_map_coverage(
    model_directory: Path,
    config: dict[str, Any],
) -> dict[str, int]:
    index_path = model_directory / "model.safetensors.index.json"
    index = _load_json(index_path, "Qwen weight index")
    weight_map = index.get("weight_map")
    if not isinstance(weight_map, dict) or not weight_map:
        raise Qwen35LogicalRowReaderError("Qwen weight index has no weight map")
    module_prefixes = tuple(str(key) for key in config["device_map"]["modules"])
    auxiliary = [name for name in weight_map if str(name).startswith("mtp.")]
    uncovered = [
        str(name)
        for name in weight_map
        if not str(name).startswith("mtp.")
        and not any(
            str(name) == prefix or str(name).startswith(f"{prefix}.") for prefix in module_prefixes
        )
    ]
    covered_count = len(weight_map) - len(auxiliary) - len(uncovered)
    expected = config["device_map"]
    if (
        len(weight_map) != int(expected["expected_weight_index_tensor_count"])
        or covered_count != int(expected["expected_device_map_covered_tensor_count"])
        or len(auxiliary) != int(expected["expected_excluded_auxiliary_mtp_tensor_count"])
        or uncovered
    ):
        preview = ", ".join(uncovered[:3])
        raise Qwen35LogicalRowReaderError(
            f"Qwen weight index is not fully covered by the explicit device map: {preview}"
        )
    return {
        "weight_index_tensor_count": len(weight_map),
        "device_map_covered_tensor_count": covered_count,
        "excluded_auxiliary_mtp_tensor_count": len(auxiliary),
    }


def _verify_packages(
    config: dict[str, Any],
) -> tuple[dict[str, str], dict[str, int | str]]:
    expected = config["runtime_compatibility"].get("packages")
    if not isinstance(expected, dict):
        raise Qwen35LogicalRowReaderError("Qwen package registry is missing")
    actual: dict[str, str] = {}
    for distribution, expected_version in expected.items():
        try:
            version = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError as error:
            raise Qwen35LogicalRowReaderError(
                f"required Qwen runtime package is missing: {distribution}"
            ) from error
        if version != expected_version:
            raise Qwen35LogicalRowReaderError(
                f"Qwen runtime package drift: {distribution} {version} != {expected_version}"
            )
        actual[str(distribution)] = version
    python = f"{sys.version_info.major}.{sys.version_info.minor}"
    if python != config["runtime_compatibility"]["python_major_minor"]:
        raise Qwen35LogicalRowReaderError("Qwen Python runtime version drifted")
    return actual, _verify_overlay_tree(config)


def _exact_tree_identity(root: Path) -> dict[str, int | str]:
    if not root.is_dir() or root.is_symlink():
        raise Qwen35LogicalRowReaderError("Qwen runtime overlay root is absent or unsafe")
    files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise Qwen35LogicalRowReaderError(f"Qwen runtime overlay contains symlink: {path}")
        if path.is_file():
            files.append(path)
    digest = hashlib.sha256()
    total_bytes = 0
    for path in sorted(files, key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        size = path.stat().st_size
        total_bytes += size
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\0")
        digest.update(sha256_file(path).encode("ascii"))
        digest.update(b"\n")
    return {
        "file_count": len(files),
        "total_bytes": total_bytes,
        "pyc_file_count": sum(path.suffix == ".pyc" for path in files),
        "tree_sha256": digest.hexdigest(),
    }


def _verify_overlay_tree(config: dict[str, Any]) -> dict[str, int | str]:
    overlay = config["runtime_overlay"]
    distributions = overlay.get("installed_tree_distributions")
    import_roots = overlay.get("installed_tree_import_roots")
    if not isinstance(distributions, list) or not isinstance(import_roots, list):
        raise Qwen35LogicalRowReaderError("Qwen runtime overlay tree registry is missing")
    roots: set[Path] = set()
    for name in distributions:
        try:
            distribution = importlib.metadata.distribution(str(name))
        except importlib.metadata.PackageNotFoundError as error:
            raise Qwen35LogicalRowReaderError(
                f"Qwen overlay distribution is missing: {name}"
            ) from error
        roots.add(Path(distribution.locate_file("")).resolve())
    if len(roots) != 1:
        raise Qwen35LogicalRowReaderError("Qwen overlay distributions do not share one root")
    root = roots.pop()
    for import_root in import_roots:
        spec = importlib.util.find_spec(str(import_root))
        if spec is None:
            raise Qwen35LogicalRowReaderError(
                f"Qwen overlay import root is unresolved: {import_root}"
            )
        origins = (
            [Path(spec.origin).resolve()]
            if spec.origin is not None
            else [Path(value).resolve() for value in spec.submodule_search_locations or ()]
        )
        if not origins or any(not origin.is_relative_to(root) for origin in origins):
            raise Qwen35LogicalRowReaderError(
                f"Qwen overlay import root resolves outside sealed tree: {import_root}"
            )
    identity = _exact_tree_identity(root)
    if (
        identity["file_count"] != int(overlay["installed_tree_file_count"])
        or identity["total_bytes"] != int(overlay["installed_tree_total_bytes"])
        or identity["pyc_file_count"] != int(overlay["installed_tree_pyc_file_count"])
        or identity["tree_sha256"] != overlay["installed_tree_sha256"]
    ):
        raise Qwen35LogicalRowReaderError("Qwen installed runtime overlay tree drifted")
    return identity


def _host_available_memory_bytes() -> int:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError) as error:
        raise Qwen35LogicalRowReaderError("cannot read available host memory") from error
    raise Qwen35LogicalRowReaderError("MemAvailable is missing from /proc/meminfo")


def _deny_network_connections() -> None:
    def audit_hook(event: str, _: tuple[Any, ...]) -> None:
        if event.startswith("socket."):
            raise RuntimeError("network access is forbidden during Qwen inference")

    sys.addaudithook(audit_hook)


def _has_pathological_repetition(text: str) -> bool:
    lines = [normalize_text(line).casefold() for line in text.splitlines() if line.strip()]
    if any(lines.count(line) >= 3 for line in set(lines)):
        return True
    tokens = normalize_text(text).casefold().split()
    if len(tokens) >= 12 and len(set(tokens)) / len(tokens) < 0.35:
        return True
    trigrams = [tuple(tokens[index : index + 3]) for index in range(max(0, len(tokens) - 2))]
    return any(trigrams.count(gram) >= 4 for gram in set(trigrams))


def parse_qwen_transcription(
    raw_output: str,
    *,
    generated_token_count: int,
    maximum_new_tokens: int,
    terminated_by_eos: bool,
    maximum_nonempty_lines: int,
    maximum_output_characters: int,
    prompt: str | None = None,
) -> dict[str, Any]:
    lines = [normalize_text(line) for line in raw_output.splitlines() if normalize_text(line)]
    base = {
        "nonempty_line_count": len(lines),
        "generated_token_count": generated_token_count,
        "terminated_by_eos": terminated_by_eos,
    }
    if not raw_output.strip():
        return base | {"status": "REJECT_EMPTY_OUTPUT", "proposal_text": ""}
    if generated_token_count >= maximum_new_tokens and not terminated_by_eos:
        return base | {"status": "REJECT_TOKEN_BUDGET_EXHAUSTED", "proposal_text": ""}
    if len(raw_output) > maximum_output_characters:
        return base | {
            "status": "REJECT_OUTPUT_CHARACTER_BUDGET_EXCEEDED",
            "proposal_text": "",
        }
    if len(lines) > maximum_nonempty_lines:
        return base | {"status": "REJECT_TOO_MANY_OUTPUT_LINES", "proposal_text": ""}
    if _FORBIDDEN_OUTPUT.search(raw_output) or _TRANSCRIPTION_PREAMBLE.search(raw_output):
        return base | {"status": "REJECT_REASONING_OR_SERIALIZATION", "proposal_text": ""}
    if prompt:
        normalized_output = normalize_text(raw_output).casefold()
        prompt_fragments = [
            normalize_text(fragment).casefold()
            for fragment in re.split(r"[.!?]+", prompt)
            if len(normalize_text(fragment).split()) >= 3
        ]
        if any(fragment in normalized_output for fragment in prompt_fragments):
            return base | {"status": "REJECT_PROMPT_ECHO", "proposal_text": ""}
    if _has_pathological_repetition(raw_output):
        return base | {"status": "REJECT_PATHOLOGICAL_REPETITION", "proposal_text": ""}
    proposal = normalize_text(" ".join(lines))
    if not proposal or not any(character.isalpha() for character in proposal):
        return base | {"status": "REJECT_NON_TEXTUAL_OUTPUT", "proposal_text": ""}
    return base | {"status": "PARSED_SEMANTIC_PROPOSAL_ONLY", "proposal_text": proposal}


def _normalize_device_map(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict) or not raw:
        raise Qwen35LogicalRowReaderError("Qwen hf_device_map is missing")
    normalized = {str(key): str(value) for key, value in raw.items()}
    placements = set(normalized.values())
    allowed = {"0", "cuda:0", "cpu"}
    if not placements <= allowed or not placements & {"0", "cuda:0"} or "cpu" not in placements:
        raise Qwen35LogicalRowReaderError(
            f"Qwen device map violates bounded GPU/CPU-only policy: {sorted(placements)}"
        )
    return normalized


def _start_hard_watchdog(
    watchdog_path: Path,
    *,
    timeout_seconds: int,
    ready_timeout_seconds: int,
) -> subprocess.Popen[str]:
    process = subprocess.Popen(
        [
            sys.executable,
            watchdog_path.as_posix(),
            "--pid",
            str(os.getpid()),
            "--timeout-seconds",
            str(timeout_seconds),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1"},
    )
    assert process.stdout is not None
    ready, _, _ = select.select([process.stdout], [], [], ready_timeout_seconds)
    line = process.stdout.readline().strip() if ready else ""
    if line != "READY":
        process.terminate()
        try:
            _, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            _, stderr = process.communicate()
        raise Qwen35LogicalRowReaderError(
            f"Qwen hard watchdog failed to become ready: {stderr.strip()}"
        )
    return process


def _stop_hard_watchdog(process: subprocess.Popen[str]) -> None:
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    if process.returncode not in {-signal.SIGTERM, 0}:
        assert process.stderr is not None
        raise Qwen35LogicalRowReaderError(
            f"Qwen hard watchdog exited unexpectedly: {process.returncode}: "
            f"{process.stderr.read().strip()}"
        )


def _forbidden_generated_control_tokens(
    token_ids: list[int],
    *,
    minimum: int,
    maximum: int,
) -> list[int]:
    return sorted({token for token in token_ids if minimum <= token <= maximum})


def _write_output_directory(
    destination: Path,
    result: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    try:
        result_path = temporary / "ocr_result.json"
        result_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        manifest["artifacts"] = {
            "ocr_result": {
                "path": result_path.name,
                "size_bytes": result_path.stat().st_size,
                "sha256": sha256_file(result_path),
            }
        }
        manifest_path = temporary / "run_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if destination.exists():
            raise Qwen35LogicalRowReaderError(f"output appeared during inference: {destination}")
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def _run_qwen35_logical_row_reader_impl(
    project_root: Path,
    *,
    request_path: Path,
    output_directory: Path,
    model_cache_root: Path,
    config_path: Path = Path("config/models/qwen35-27b-gptq-int4-rtx4090-v1.toml"),
) -> dict[str, Any]:
    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise Qwen35LogicalRowReaderError("formal E-0036 Qwen inference requires clean Git code")
    initial_git_commit = _git(project_root, "rev-parse", "HEAD")
    config, authorization, config_file, authorization_path = load_qwen35_logical_row_config(
        project_root, config_path
    )
    watchdog_path = _verify_bound_file(project_root, config["hard_watchdog"], "Qwen hard watchdog")
    request_file = _project_path(project_root, request_path.as_posix(), "Qwen request")
    configured_request = _project_path(
        project_root, str(config["request"]["path"]), "configured Qwen request"
    )
    if (
        request_file != configured_request
        or sha256_file(request_file) != config["request"]["sha256"]
    ):
        raise Qwen35LogicalRowReaderError("Qwen must receive the unchanged E-0036 request")
    destination = _project_path(project_root, output_directory.as_posix(), "Qwen output")
    if destination.exists():
        raise Qwen35LogicalRowReaderError(f"refusing to overwrite Qwen output: {destination}")
    request = _load_json(request_file, "E-0036 Qwen request")
    try:
        samples = validate_logical_row_label_reader_request(request)
    except LogicalRowLabelReaderContractError as error:
        raise Qwen35LogicalRowReaderError(str(error)) from error
    if len(samples) != int(config["request"]["sample_count"]):
        raise Qwen35LogicalRowReaderError("Qwen request sample denominator drifted")
    crop_manifest = request["crop_manifest"]
    crop_manifest_path = _project_path(project_root, crop_manifest["path"], "crop manifest")
    if (
        not crop_manifest_path.is_file()
        or sha256_file(crop_manifest_path) != crop_manifest["sha256"]
    ):
        raise Qwen35LogicalRowReaderError("E-0035 crop manifest is absent or drifted")
    verified_samples: list[dict[str, Any]] = []
    for sample in samples:
        crop = _project_path(project_root, sample["crop_path"], "logical-row crop")
        if not crop.is_file() or sha256_file(crop) != sample["crop_sha256"]:
            raise Qwen35LogicalRowReaderError(f"crop is absent or drifted: {sample['sample_id']}")
        try:
            with Image.open(crop) as image:
                width, height = image.size
                image.verify()
        except OSError as error:
            raise Qwen35LogicalRowReaderError(f"invalid crop image: {crop}") from error
        verified_samples.append(sample | {"resolved_crop": crop, "width": width, "height": height})

    model_directory = model_cache_root.resolve() / "official_models" / config["cache_directory"]
    model_artifacts = _verify_model(model_directory, config)
    weight_map_coverage = _verify_weight_map_coverage(model_directory, config)
    package_versions, overlay_tree_identity = _verify_packages(config)
    host_available_before = _host_available_memory_bytes()
    minimum_host_memory = int(
        config["runtime_compatibility"]["minimum_host_available_memory_bytes"]
    )
    if host_available_before < minimum_host_memory:
        raise Qwen35LogicalRowReaderError(
            "insufficient available host memory for bounded Qwen CPU offload"
        )
    model_cache_root = model_cache_root.resolve()
    temporary_load_minimum_free = int(
        config["device_map"]["temporary_load_staging_minimum_free_bytes"]
    )
    temporary_load_free_before = shutil.disk_usage(model_cache_root).free
    if temporary_load_free_before < temporary_load_minimum_free:
        raise Qwen35LogicalRowReaderError(
            "insufficient filesystem space for controlled Qwen load staging"
        )
    controlled_load_temp = Path(tempfile.gettempdir()).resolve()
    if controlled_load_temp.parent != model_cache_root or not controlled_load_temp.name.startswith(
        "qwen-e0036-load-"
    ):
        raise Qwen35LogicalRowReaderError("Qwen controlled temporary load directory drifted")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ.setdefault("HF_HOME", "/dev/shm/bctc-qwen-e0036-hf")
    _deny_network_connections()

    import torch
    from gptqmodel import GPTQModel
    from gptqmodel.nn_modules.qlinear import BaseQuantLinear
    from gptqmodel.nn_modules.qlinear.tritonv2 import TritonV2Linear
    from gptqmodel.quantization import FORMAT, METHOD
    from gptqmodel.utils.backend import BACKEND
    from transformers import AutoProcessor
    from transformers.models.qwen3_5 import modeling_qwen3_5

    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise Qwen35LogicalRowReaderError("Qwen E-0036 requires BF16-capable CUDA")
    capability = list(torch.cuda.get_device_capability(0))
    if capability < list(config["runtime_compatibility"]["minimum_compute_capability"]):
        raise Qwen35LogicalRowReaderError("GPU capability is below Qwen E-0036 minimum")
    if torch.cuda.get_device_name(0) != "NVIDIA GeForce RTX 4090":
        raise Qwen35LogicalRowReaderError("formal Qwen calibration requires the declared RTX 4090")
    free_vram_before_load, total_vram = torch.cuda.mem_get_info()
    minimum_free_vram = int(config["device_map"]["estimated_registered_tensor_bytes_gpu"]) + int(
        config["device_map"]["minimum_runtime_vram_headroom_bytes"]
    )
    if free_vram_before_load < minimum_free_vram:
        raise Qwen35LogicalRowReaderError(
            "insufficient free VRAM for pinned Qwen weights and runtime headroom"
        )

    inference = config["inference"]
    started_at = datetime.now(UTC)
    started = time.perf_counter()
    torch.manual_seed(0)
    torch.cuda.manual_seed_all(0)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    if (
        modeling_qwen3_5.is_fast_path_available is not False
        or modeling_qwen3_5.causal_conv1d_fn is not None
        or modeling_qwen3_5.causal_conv1d_update is not None
        or modeling_qwen3_5.chunk_gated_delta_rule is not None
        or modeling_qwen3_5.fused_recurrent_gated_delta_rule is not None
        or modeling_qwen3_5.FusedRMSNormGated is not None
    ):
        raise Qwen35LogicalRowReaderError("Qwen linear-attention implementation drifted")
    processor = AutoProcessor.from_pretrained(
        model_directory.as_posix(),
        local_files_only=True,
        trust_remote_code=False,
        use_fast=False,
        min_pixels=int(inference["processor_min_pixels"]),
        max_pixels=int(inference["processor_max_pixels"]),
    )
    processor_size = processor.image_processor.size
    if (
        processor.__class__.__name__ != "Qwen3VLProcessor"
        or processor.image_processor.__class__.__name__ != "Qwen2VLImageProcessorPil"
        or int(processor_size.shortest_edge) != int(inference["processor_min_pixels"])
        or int(processor_size.longest_edge) != int(inference["processor_max_pixels"])
    ):
        raise Qwen35LogicalRowReaderError("Qwen processor pixel bounds drifted")
    with Image.open(verified_samples[0]["resolved_crop"]) as probe_source:
        probe_image = probe_source.convert("RGB")
        rendered_probe = processor.apply_chat_template(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": probe_image},
                        {"type": "text", "text": inference["prompt"]},
                    ],
                }
            ],
            add_generation_prompt=True,
            tokenize=False,
            enable_thinking=False,
            add_vision_id=False,
        )
    if not rendered_probe.endswith(inference["expected_assistant_prompt_suffix"]):
        raise Qwen35LogicalRowReaderError("Qwen no-thinking chat-template suffix drifted")
    load_started = time.perf_counter()
    qmodel = GPTQModel.from_quantized(
        model_directory.as_posix(),
        device_map=dict(config["device_map"]["modules"]),
        backend=BACKEND.GPTQ_TRITON,
        dtype=torch.bfloat16,
        local_files_only=True,
        trust_remote_code=False,
        attn_implementation=inference["attention_implementation"],
    )
    model = qmodel.model.eval()
    expected_dynamic = set(config["quantization"]["dynamic_exclusion_keys"])
    actual_dynamic = qmodel.quantize_config.dynamic
    if (
        qmodel.quantize_config.bits != 4
        or qmodel.quantize_config.runtime_bits != 4
        or qmodel.quantize_config.group_size != 128
        or qmodel.quantize_config.sym is not True
        or qmodel.quantize_config.desc_act is not False
        or qmodel.quantize_config.method is not METHOD.GPTQ
        or qmodel.quantize_config.format is not FORMAT.GPTQ
        or qmodel.quantize_config.lm_head is not False
        or qmodel.quantize_config.pack_dtype is not torch.int32
        or not isinstance(actual_dynamic, dict)
        or set(actual_dynamic) != expected_dynamic
        or any(value != {} for value in actual_dynamic.values())
    ):
        raise Qwen35LogicalRowReaderError("Qwen GPTQ dynamic exclusions drifted")
    if qmodel.qlinear_kernel is not TritonV2Linear:
        raise Qwen35LogicalRowReaderError("Qwen did not load the pinned GPTQ Triton backend")
    quantized_module_names = [
        name for name, module in model.named_modules() if isinstance(module, BaseQuantLinear)
    ]
    expected_quantized_count = int(config["quantization"]["expected_quantized_linear_module_count"])
    quantized_name_pattern = re.compile(
        r"model\.language_model\.layers\.[0-9]+\.mlp\.(?:gate_proj|up_proj|down_proj)"
    )
    if len(quantized_module_names) != expected_quantized_count or any(
        quantized_name_pattern.fullmatch(name) is None for name in quantized_module_names
    ):
        raise Qwen35LogicalRowReaderError("Qwen quantized-module boundary drifted")
    normalized_device_map = _normalize_device_map(getattr(model, "hf_device_map", None))
    if normalized_device_map != {
        key: str(value) for key, value in config["device_map"]["modules"].items()
    }:
        raise Qwen35LogicalRowReaderError("Qwen explicit device map drifted after loading")
    if any(parameter.device.type == "meta" for parameter in model.parameters()) or any(
        buffer.device.type == "meta" for buffer in model.buffers()
    ):
        raise Qwen35LogicalRowReaderError("Qwen contains unresolved meta-device tensors")
    torch.cuda.synchronize()
    model_load_seconds = time.perf_counter() - load_started
    qmodel.processor = processor
    input_device = torch.device("cuda:0")
    eos_ids = model.generation_config.eos_token_id
    eos_set = {int(eos_ids)} if isinstance(eos_ids, int) else {int(value) for value in eos_ids}
    pad_token_id = processor.tokenizer.pad_token_id
    if (
        eos_set != {int(value) for value in inference["eos_token_ids"]}
        or pad_token_id != int(inference["pad_token_id"])
        or qmodel.tokenizer.pad_token_id != pad_token_id
    ):
        raise Qwen35LogicalRowReaderError("Qwen generation stop-token configuration drifted")

    records: list[dict[str, Any]] = []
    observed_visual_tokens: list[int] = []
    mechanism_probe: dict[str, Any] | None = None
    for sample in verified_samples:
        item_started = time.perf_counter()
        with Image.open(sample["resolved_crop"]) as source_image:
            image = source_image.convert("RGB")
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": inference["prompt"]},
                    ],
                }
            ]
            inputs = processor.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
                enable_thinking=False,
                add_vision_id=False,
            )
        input_tokens = int(inputs["input_ids"].shape[-1])
        if input_tokens + int(inference["maximum_new_tokens"]) > int(inference["context_length"]):
            raise Qwen35LogicalRowReaderError(
                f"Qwen context budget exceeded: {sample['sample_id']}"
            )
        grid = inputs["image_grid_thw"]
        visual_tokens = int((grid[:, 0] * grid[:, 1] * grid[:, 2]).sum().item()) // 4
        if not (
            int(inference["minimum_observed_visual_tokens"])
            <= visual_tokens
            <= int(inference["maximum_observed_visual_tokens"])
        ):
            raise Qwen35LogicalRowReaderError(
                f"Qwen visual-token envelope drifted: {sample['sample_id']}={visual_tokens}"
            )
        observed_visual_tokens.append(visual_tokens)
        inputs = inputs.to(input_device)
        watchdog_process = _start_hard_watchdog(
            watchdog_path,
            timeout_seconds=int(inference["maximum_sample_inference_seconds"]),
            ready_timeout_seconds=int(config["hard_watchdog"]["ready_timeout_seconds"]),
        )
        try:
            with torch.inference_mode():
                output_ids = qmodel.generate(
                    inputs,
                    max_new_tokens=int(inference["maximum_new_tokens"]),
                    do_sample=False,
                    use_cache=bool(inference["use_cache"]),
                    eos_token_id=sorted(eos_set),
                    pad_token_id=pad_token_id,
                )
        finally:
            _stop_hard_watchdog(watchdog_process)
        torch.cuda.synchronize()
        if output_ids.shape[-1] < input_tokens or not torch.equal(
            output_ids[:, :input_tokens], inputs["input_ids"]
        ):
            raise Qwen35LogicalRowReaderError("Qwen generation did not preserve the input prefix")
        generated = output_ids[:, input_tokens:]
        generated_token_count = int(generated.shape[-1])
        last_token = int(generated[0, -1].item()) if generated_token_count else None
        terminated_by_eos = last_token in eos_set
        content_ids = generated[:, :-1] if terminated_by_eos else generated
        content_token_ids = [int(value) for value in content_ids[0].tolist()]
        forbidden_control_token_ids = _forbidden_generated_control_tokens(
            content_token_ids,
            minimum=int(inference["forbidden_generated_control_token_id_min"]),
            maximum=int(inference["forbidden_generated_control_token_id_max"]),
        )
        raw_generated_output = processor.batch_decode(
            generated,
            skip_special_tokens=False,
            clean_up_tokenization_spaces=False,
        )[0]
        raw_output = processor.batch_decode(
            content_ids,
            skip_special_tokens=False,
            clean_up_tokenization_spaces=False,
        )[0]
        parsed = parse_qwen_transcription(
            raw_output,
            generated_token_count=generated_token_count,
            maximum_new_tokens=int(inference["maximum_new_tokens"]),
            terminated_by_eos=terminated_by_eos,
            maximum_nonempty_lines=int(inference["maximum_nonempty_output_lines"]),
            maximum_output_characters=int(inference["maximum_output_characters"]),
            prompt=inference["prompt"],
        )
        if forbidden_control_token_ids:
            parsed = parsed | {
                "status": "REJECT_GENERATED_CONTROL_TOKEN",
                "proposal_text": "",
            }
        inference_seconds = time.perf_counter() - item_started
        record = {
            "sample_id": sample["sample_id"],
            "category": sample["category"],
            "crop_path": sample["crop_path"],
            "crop_sha256": sample["crop_sha256"],
            "crop_width": sample["width"],
            "crop_height": sample["height"],
            "input_token_count": input_tokens,
            "visual_token_count": visual_tokens,
            "generated_token_ids": [int(value) for value in generated[0].tolist()],
            "forbidden_generated_control_token_ids": forbidden_control_token_ids,
            "raw_generated_output": raw_generated_output,
            "raw_output": raw_output,
            **parsed,
            "reader_score": None,
            "reader_score_available": False,
            "inference_seconds": inference_seconds,
        }
        records.append(record)
        if len(records) == int(inference["mechanism_probe_sample_count"]):
            projected_seconds = model_load_seconds + (
                inference_seconds
                / max(1, generated_token_count)
                * int(inference["maximum_new_tokens"])
                * len(verified_samples)
            )
            mechanism_probe = {
                "sample_id": sample["sample_id"],
                "inference_seconds": inference_seconds,
                "generated_token_count": generated_token_count,
                "projected_maximum_total_wall_seconds": projected_seconds,
                "projection_policy": "FIRST_CROP_SECONDS_PER_TOKEN_TIMES_96_TOKENS_TIMES_64",
            }
            if inference_seconds > float(
                inference["maximum_mechanism_probe_seconds"]
            ) or projected_seconds > float(inference["maximum_projected_total_wall_seconds"]):
                raise Qwen35LogicalRowReaderError(
                    "Qwen one-crop mechanism probe exceeded the frozen wall-time bound"
                )

    total_seconds = time.perf_counter() - started
    state = "REFERENCE_BLIND_LOGICAL_ROW_LABEL_INFERENCE_COMPLETE"
    result = {
        "format_version": 1,
        "experiment_id": "E-0036",
        "reader": "QWEN3_5_27B_GPTQ_INT4",
        "state": state,
        "dataset_role": "CALIBRATION",
        "evidence_role": config["evidence_role"],
        "reference_text_available_to_reader": False,
        "sample_count": len(records),
        "samples": records,
        "authority": {key: False for key in config["safety"]},
    }
    free_vram, observed_total_vram = torch.cuda.mem_get_info()
    if observed_total_vram != total_vram:
        raise Qwen35LogicalRowReaderError("Qwen CUDA device memory total drifted during inference")
    manifest: dict[str, Any] = {
        "format_version": 1,
        "experiment_id": "E-0036",
        "reader": "QWEN3_5_27B_GPTQ_INT4",
        "state": state,
        "dataset_role": "CALIBRATION",
        "evidence_role": config["evidence_role"],
        "git_commit": initial_git_commit,
        "git_dirty": False,
        "authorization": {
            "path": authorization_path.relative_to(project_root).as_posix(),
            "sha256": sha256_file(authorization_path),
            "decision": authorization["decision"],
            "reference_content_available_to_reader": False,
        },
        "request": {
            "path": request_file.relative_to(project_root).as_posix(),
            "sha256": sha256_file(request_file),
        },
        "crop_manifest": dict(crop_manifest),
        "configuration": {
            "path": config_file.relative_to(project_root).as_posix(),
            "sha256": sha256_file(config_file),
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
        },
        "runtime": {
            "packages": package_versions,
            "overlay_tree_identity": overlay_tree_identity,
            "torch_cuda": torch.version.cuda,
            "gpu_name": torch.cuda.get_device_name(0),
            "compute_capability": capability,
            "bf16_supported": torch.cuda.is_bf16_supported(),
            "host_available_memory_bytes_before_load": host_available_before,
            "host_available_memory_bytes_after_inference": _host_available_memory_bytes(),
            "hf_device_map": normalized_device_map,
            "weight_map_coverage": weight_map_coverage,
            "gptq_backend": "gptq_triton",
            "gptq_dynamic_exclusion_keys": sorted(expected_dynamic),
            "quantized_linear_module_count": len(quantized_module_names),
            "temporary_load_staging": {
                "persistent_weight_device_map_disk": False,
                "controlled_root": model_cache_root.as_posix(),
                "ephemeral_directory_name": controlled_load_temp.name,
                "triton_cache_is_ephemeral": True,
                "torchinductor_cache_is_ephemeral": True,
                "free_bytes_before_load": temporary_load_free_before,
                "minimum_free_bytes_required": temporary_load_minimum_free,
            },
            "hard_watchdog": {
                "path": watchdog_path.relative_to(project_root).as_posix(),
                "sha256": sha256_file(watchdog_path),
                "timeout_seconds_per_sample": inference["maximum_sample_inference_seconds"],
                "mechanism": "LINUX_PIDFD_EXTERNAL_SIGKILL",
            },
            "vram_preflight": {
                "free_bytes_before_load": free_vram_before_load,
                "minimum_free_bytes_required": minimum_free_vram,
                "registered_gpu_tensor_bytes": config["device_map"][
                    "estimated_registered_tensor_bytes_gpu"
                ],
                "minimum_runtime_headroom_bytes": config["device_map"][
                    "minimum_runtime_vram_headroom_bytes"
                ],
            },
            "model": {
                "repo_id": config["model"]["repo_id"],
                "revision": config["model"]["revision"],
                "quantization": dict(config["quantization"]),
                "artifacts": model_artifacts,
            },
        },
        "metrics": {
            "model_load_seconds": model_load_seconds,
            "total_wall_seconds": total_seconds,
            "mechanism_probe": mechanism_probe,
            "sample_count": len(records),
            "parsed_proposal_count": sum(
                item["status"] == "PARSED_SEMANTIC_PROPOSAL_ONLY" for item in records
            ),
            "structural_rejection_count": sum(
                item["status"] != "PARSED_SEMANTIC_PROPOSAL_ONLY" for item in records
            ),
            "minimum_visual_tokens": min(observed_visual_tokens),
            "maximum_visual_tokens": max(observed_visual_tokens),
            "peak_gpu_memory_allocated_mib": torch.cuda.max_memory_allocated() / 1024**2,
            "peak_gpu_memory_reserved_mib": torch.cuda.max_memory_reserved() / 1024**2,
            "free_vram_bytes_after_inference": free_vram,
            "total_vram_bytes": total_vram,
        },
        "started_at": started_at.isoformat(),
        "completed_at": datetime.now(UTC).isoformat(),
        "safety": {key: False for key in config["safety"]},
    }
    if mechanism_probe is None:
        raise Qwen35LogicalRowReaderError("Qwen one-crop mechanism probe did not run")
    if _git(project_root, "rev-parse", "HEAD") != initial_git_commit or _git(
        project_root, "status", "--porcelain"
    ):
        raise Qwen35LogicalRowReaderError("Git code drifted during formal Qwen inference")
    _write_output_directory(destination, result, manifest)
    return manifest


def run_qwen35_logical_row_reader(
    project_root: Path,
    *,
    request_path: Path,
    output_directory: Path,
    model_cache_root: Path,
    config_path: Path = Path("config/models/qwen35-27b-gptq-int4-rtx4090-v1.toml"),
) -> dict[str, Any]:
    if os.environ.get("BCTC_QWEN35_ONE_SHOT_WORKER") != "1":
        raise Qwen35LogicalRowReaderError(
            "Qwen formal inference must run in the declared one-shot worker process"
        )
    cache_root = model_cache_root.resolve()
    if not cache_root.is_dir() or cache_root.is_symlink():
        raise Qwen35LogicalRowReaderError(f"Qwen model cache root is invalid: {cache_root}")
    environment_keys = (
        "TMPDIR",
        "TRITON_CACHE_DIR",
        "TORCHINDUCTOR_CACHE_DIR",
        "HF_HOME",
        "HF_HUB_CACHE",
        "XDG_CACHE_HOME",
        "HF_HUB_OFFLINE",
        "TRANSFORMERS_OFFLINE",
        "HF_HUB_DISABLE_TELEMETRY",
        "TOKENIZERS_PARALLELISM",
        "PYTORCH_ALLOC_CONF",
        "CUDA_DEVICE_ORDER",
    )
    previous_environment = {key: os.environ.get(key) for key in environment_keys}
    previous_tempfile_tempdir = tempfile.tempdir
    previous_dont_write_bytecode = sys.dont_write_bytecode
    try:
        with tempfile.TemporaryDirectory(prefix="qwen-e0036-load-", dir=cache_root) as temporary:
            controlled = Path(temporary)
            cache_directories = {
                "TRITON_CACHE_DIR": controlled / "triton",
                "TORCHINDUCTOR_CACHE_DIR": controlled / "torchinductor",
                "HF_HOME": controlled / "huggingface",
                "HF_HUB_CACHE": controlled / "huggingface" / "hub",
                "XDG_CACHE_HOME": controlled / "xdg-cache",
            }
            for directory in cache_directories.values():
                directory.mkdir(parents=True, exist_ok=True)
            os.environ["TMPDIR"] = controlled.as_posix()
            tempfile.tempdir = controlled.as_posix()
            sys.dont_write_bytecode = True
            for key, directory in cache_directories.items():
                os.environ[key] = directory.as_posix()
            return _run_qwen35_logical_row_reader_impl(
                project_root,
                request_path=request_path,
                output_directory=output_directory,
                model_cache_root=cache_root,
                config_path=config_path,
            )
    finally:
        for key, value in previous_environment.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        tempfile.tempdir = previous_tempfile_tempdir
        sys.dont_write_bytecode = previous_dont_write_bytecode


__all__ = [
    "Qwen35LogicalRowReaderError",
    "load_qwen35_logical_row_config",
    "parse_qwen_transcription",
    "run_qwen35_logical_row_reader",
]
