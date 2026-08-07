from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image

from bctc_ai.core.hashing import sha256_file
from bctc_ai.ocr.deepseek_line_reader import (
    DeepSeekLineReaderError,
    _deny_network_connections,
    _git,
    _load_toml,
    _project_path,
    _verify_model,
    _verify_packages,
    _write_output_directory,
    install_generation_token_cap,
    parse_free_ocr_output,
)
from bctc_ai.ocr.logical_row_label_reader_contract import (
    LogicalRowLabelReaderContractError,
    validate_logical_row_label_reader_request,
)


class DeepSeekLogicalRowReaderError(DeepSeekLineReaderError):
    """Raised when the RTX 4090 logical-row DeepSeek adapter fails closed."""


def load_deepseek_logical_row_config(
    project_root: Path,
    config_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    project_root = project_root.resolve()
    resolved = (
        config_path.resolve()
        if config_path.is_absolute()
        else _project_path(project_root, config_path.as_posix(), "logical-row config")
    )
    if not resolved.is_relative_to(project_root):
        raise DeepSeekLogicalRowReaderError("DeepSeek logical-row config escapes project root")
    config = _load_toml(resolved, "DeepSeek logical-row config")
    inference = config.get("inference")
    compatibility = config.get("runtime_compatibility")
    safety = config.get("safety")
    if (
        config.get("version") != 3
        or config.get("status")
        != "CALIBRATION_ONLY_RTX4090_REFERENCE_BLIND_ASPECT_PRESERVING_LOGICAL_ROW_LABEL_READER"
        or config.get("reader") != "DEEPSEEK_OCR_2"
        or config.get("geometry_authority") != "PP_OCRV6_WORD_BOXES"
        or config.get("evidence_role") != "VIETNAMESE_LOGICAL_ROW_LABEL_PROPOSAL_ONLY"
        or not isinstance(inference, dict)
        or inference.get("prompt") != "<image>\nFree OCR."
        or inference.get("crop_mode") is not True
        or inference.get("aspect_preservation") != "OFFICIAL_IMAGEOPS_PAD"
        or inference.get("attention_implementation") != "eager"
        or inference.get("network_permitted") is not False
        or inference.get("reference_text_available_to_decoder") is not False
        or inference.get("target_policy") != "FROZEN_PP_OCRV6_LINE_TITLE_OR_LOGICAL_ROW_CROPS_ONLY"
        or inference.get("upstream_requested_maximum_new_tokens") != 8192
        or not isinstance(inference.get("maximum_new_tokens"), int)
        or not 1 <= int(inference["maximum_new_tokens"]) <= 512
        or not isinstance(inference.get("maximum_output_characters"), int)
        or int(inference["maximum_output_characters"]) < 1
        or not isinstance(inference.get("maximum_nonempty_output_lines"), int)
        or int(inference["maximum_nonempty_output_lines"]) < 1
        or not isinstance(compatibility, dict)
        or compatibility.get("gpu_family") != "NVIDIA_GEFORCE_RTX_4090_ADA"
        or compatibility.get("minimum_compute_capability") != [8, 9]
        or compatibility.get("bf16_required") is not True
        or compatibility.get("historical_blackwell_runtime_claimed") is not False
        or not isinstance(safety, dict)
        or not safety
        or any(bool(value) for value in safety.values())
    ):
        raise DeepSeekLogicalRowReaderError("DeepSeek logical-row configuration drifted")
    base_identity = config.get("base_model")
    if not isinstance(base_identity, dict):
        raise DeepSeekLogicalRowReaderError("DeepSeek base-model identity is missing")
    base_path = _project_path(
        project_root,
        str(base_identity.get("config_path", "")),
        "DeepSeek base-model config",
    )
    if not base_path.is_file() or sha256_file(base_path) != base_identity.get("config_sha256"):
        raise DeepSeekLogicalRowReaderError("DeepSeek base-model config is absent or drifted")
    base = _load_toml(base_path, "DeepSeek base-model config")
    base_inference = base.get("inference")
    base_safety = base.get("safety")
    if (
        base.get("version") != 1
        or base.get("status") != "CALIBRATION_ONLY_SEMANTIC_OCR_PROPOSAL"
        or not isinstance(base_inference, dict)
        or base_inference.get("network_permitted") is not False
        or not isinstance(base_safety, dict)
        or not base_safety
        or any(bool(value) for value in base_safety.values())
    ):
        raise DeepSeekLogicalRowReaderError("DeepSeek base-model safety boundary drifted")
    return config, base, resolved


def run_deepseek_logical_row_reader(
    project_root: Path,
    *,
    request_path: Path,
    output_directory: Path,
    model_cache_root: Path,
    config_path: Path = Path("config/models/deepseek-ocr2-line-rtx4090-v3.toml"),
) -> dict[str, Any]:
    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise DeepSeekLogicalRowReaderError(
            "formal E-0036 DeepSeek inference requires clean Git code"
        )
    config, base, config_file = load_deepseek_logical_row_config(project_root, config_path)
    request_file = _project_path(project_root, request_path.as_posix(), "logical-row request")
    destination = _project_path(project_root, output_directory.as_posix(), "DeepSeek output")
    if destination.exists():
        raise DeepSeekLogicalRowReaderError(f"refusing to overwrite output: {destination}")
    try:
        request = json.loads(request_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DeepSeekLogicalRowReaderError("cannot load E-0036 request") from error
    if not isinstance(request, dict):
        raise DeepSeekLogicalRowReaderError("E-0036 request must be an object")
    try:
        samples = validate_logical_row_label_reader_request(request)
    except LogicalRowLabelReaderContractError as error:
        raise DeepSeekLogicalRowReaderError(str(error)) from error
    crop_manifest = request["crop_manifest"]
    crop_manifest_path = _project_path(project_root, str(crop_manifest["path"]), "crop manifest")
    if (
        not crop_manifest_path.is_file()
        or sha256_file(crop_manifest_path) != crop_manifest["sha256"]
    ):
        raise DeepSeekLogicalRowReaderError("E-0035 crop manifest is absent or drifted")

    verified_samples: list[dict[str, Any]] = []
    for sample in samples:
        crop = _project_path(project_root, sample["crop_path"], "logical-row crop")
        if not crop.is_file() or sha256_file(crop) != sample["crop_sha256"]:
            raise DeepSeekLogicalRowReaderError(
                f"crop is absent or hash-drifted: {sample['sample_id']}"
            )
        try:
            with Image.open(crop) as image:
                width, height = image.size
                image.verify()
        except OSError as error:
            raise DeepSeekLogicalRowReaderError(f"invalid crop image: {crop}") from error
        verified_samples.append(sample | {"resolved_crop": crop, "width": width, "height": height})

    model_directory = model_cache_root.resolve() / "official_models" / str(base["cache_directory"])
    model_artifacts = _verify_model(model_directory, base)
    package_versions = _verify_packages(base)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ.setdefault("HF_HOME", "/dev/shm/bctc-deepseek-e0036-hf")
    os.environ.setdefault("HF_MODULES_CACHE", "/dev/shm/bctc-deepseek-e0036-hf/modules")
    _deny_network_connections()

    import torch
    from transformers import AutoModel, AutoTokenizer

    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise DeepSeekLogicalRowReaderError("DeepSeek E-0036 requires BF16 CUDA")
    capability = list(torch.cuda.get_device_capability(0))
    if capability < list(config["runtime_compatibility"]["minimum_compute_capability"]):
        raise DeepSeekLogicalRowReaderError("GPU capability is below E-0036 minimum")

    started_at = datetime.now(UTC)
    started = time.perf_counter()
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    inference = config["inference"]
    load_started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(
        model_directory.as_posix(), trust_remote_code=True, local_files_only=True
    )
    model = (
        AutoModel.from_pretrained(
            model_directory.as_posix(),
            trust_remote_code=True,
            local_files_only=True,
            use_safetensors=True,
            _attn_implementation="eager",
            torch_dtype=torch.bfloat16,
        )
        .eval()
        .cuda()
    )
    install_generation_token_cap(
        model,
        upstream_requested_maximum_new_tokens=int(
            inference["upstream_requested_maximum_new_tokens"]
        ),
        maximum_new_tokens=int(inference["maximum_new_tokens"]),
    )
    torch.cuda.synchronize()
    model_load_seconds = time.perf_counter() - load_started

    temporary_internal = Path(tempfile.mkdtemp(prefix="bctc-deepseek-e0036-", dir="/dev/shm"))
    records: list[dict[str, Any]] = []
    try:
        for sample in verified_samples:
            item_started = time.perf_counter()
            internal_output = temporary_internal / sample["sample_id"]
            raw_output = model.infer(
                tokenizer,
                prompt=str(inference["prompt"]),
                image_file=sample["resolved_crop"].as_posix(),
                output_path=internal_output.as_posix(),
                base_size=int(inference["base_size"]),
                image_size=int(inference["image_size"]),
                crop_mode=True,
                save_results=False,
                eval_mode=True,
            )
            torch.cuda.synchronize()
            if not isinstance(raw_output, str):
                raise DeepSeekLogicalRowReaderError(
                    f"DeepSeek returned non-text output: {sample['sample_id']}"
                )
            parsed = parse_free_ocr_output(
                raw_output,
                maximum_nonempty_lines=int(inference["maximum_nonempty_output_lines"]),
                maximum_output_characters=int(inference["maximum_output_characters"]),
            )
            if internal_output.exists():
                shutil.rmtree(internal_output)
            records.append(
                {
                    "sample_id": sample["sample_id"],
                    "category": sample["category"],
                    "crop_path": sample["crop_path"],
                    "crop_sha256": sample["crop_sha256"],
                    "crop_width": sample["width"],
                    "crop_height": sample["height"],
                    "raw_output": raw_output,
                    **parsed,
                    "reader_score": None,
                    "reader_score_available": False,
                    "inference_seconds": time.perf_counter() - item_started,
                }
            )
    finally:
        shutil.rmtree(temporary_internal, ignore_errors=True)

    total_seconds = time.perf_counter() - started
    state_name = "REFERENCE_BLIND_LOGICAL_ROW_LABEL_INFERENCE_COMPLETE"
    result = {
        "format_version": 1,
        "experiment_id": "E-0036",
        "reader": "DEEPSEEK_OCR_2",
        "state": state_name,
        "dataset_role": "CALIBRATION",
        "evidence_role": config["evidence_role"],
        "reference_text_available_to_reader": False,
        "sample_count": len(records),
        "samples": records,
        "authority": {key: False for key in config["safety"]},
    }
    free_bytes, total_bytes = torch.cuda.mem_get_info()
    manifest: dict[str, Any] = {
        "format_version": 1,
        "experiment_id": "E-0036",
        "reader": "DEEPSEEK_OCR_2",
        "state": state_name,
        "dataset_role": "CALIBRATION",
        "evidence_role": config["evidence_role"],
        "git_commit": _git(project_root, "rev-parse", "HEAD"),
        "git_dirty": False,
        "request": {
            "path": request_file.relative_to(project_root).as_posix(),
            "sha256": sha256_file(request_file),
        },
        "crop_manifest": dict(crop_manifest),
        "configuration": {
            "path": config_file.relative_to(project_root).as_posix(),
            "sha256": sha256_file(config_file),
            "base_model_config_path": config["base_model"]["config_path"],
            "base_model_config_sha256": config["base_model"]["config_sha256"],
            "prompt": inference["prompt"],
            "base_size": inference["base_size"],
            "image_size": inference["image_size"],
            "crop_mode": True,
            "aspect_preservation": inference["aspect_preservation"],
            "maximum_new_tokens": inference["maximum_new_tokens"],
            "maximum_output_characters": inference["maximum_output_characters"],
            "network_policy": "PROCESS_SOCKET_CONNECT_AND_DNS_DENIED",
        },
        "runtime": {
            "packages": package_versions,
            "torch_cuda": torch.version.cuda,
            "gpu_name": torch.cuda.get_device_name(0),
            "compute_capability": capability,
            "bf16_supported": torch.cuda.is_bf16_supported(),
            "model": {
                "repo_id": base["model"]["repo_id"],
                "revision": base["model"]["revision"],
                "artifacts": model_artifacts,
            },
        },
        "metrics": {
            "model_load_seconds": model_load_seconds,
            "total_wall_seconds": total_seconds,
            "sample_count": len(records),
            "parsed_proposal_count": sum(
                item["status"] == "PARSED_SEMANTIC_PROPOSAL_ONLY" for item in records
            ),
            "structural_rejection_count": sum(
                item["status"] != "PARSED_SEMANTIC_PROPOSAL_ONLY" for item in records
            ),
            "peak_gpu_memory_allocated_mib": torch.cuda.max_memory_allocated() / 1024**2,
            "peak_gpu_memory_reserved_mib": torch.cuda.max_memory_reserved() / 1024**2,
            "free_vram_bytes_after_inference": free_bytes,
            "total_vram_bytes": total_bytes,
        },
        "started_at": started_at.isoformat(),
        "completed_at": datetime.now(UTC).isoformat(),
        "safety": {key: False for key in config["safety"]},
    }
    _write_output_directory(destination, result, manifest)
    return manifest


__all__ = [
    "DeepSeekLogicalRowReaderError",
    "load_deepseek_logical_row_config",
    "run_deepseek_logical_row_reader",
]
