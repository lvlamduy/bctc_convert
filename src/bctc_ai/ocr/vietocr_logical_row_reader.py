from __future__ import annotations

import importlib.metadata
import math
import sys
import time
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image

from bctc_ai.core.hashing import sha256_file
from bctc_ai.ocr.logical_row_label_reader_contract import (
    LogicalRowLabelReaderContractError,
    validate_logical_row_label_reader_request,
)
from bctc_ai.ocr.vietocr_line_reader import (
    VietOCRLineReaderError,
    _deny_network_connections,
    _git,
    _load_json,
    _model_configuration,
    _project_path,
    _runtime_path,
    _verify_artifacts,
    _verify_wheel_overlay,
    _write_output_directory,
)


class VietOCRLogicalRowReaderError(VietOCRLineReaderError):
    """Raised when the RTX 4090 logical-row VietOCR adapter fails closed."""


def load_vietocr_logical_row_config(path: Path) -> dict[str, Any]:
    try:
        config = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise VietOCRLogicalRowReaderError(
            f"cannot load VietOCR logical-row config: {path}"
        ) from error
    inference = config.get("inference")
    compatibility = config.get("runtime_compatibility")
    safety = config.get("safety")
    if (
        config.get("version") != 2
        or config.get("status") != "CALIBRATION_ONLY_RTX4090_VIETNAMESE_LOGICAL_ROW_LABEL_PROPOSAL"
        or config.get("model_name") != "VietOCR VGG Transformer"
        or config.get("package_version") != "0.3.13"
        or not isinstance(inference, dict)
        or inference.get("device") != "cuda:0"
        or inference.get("beam_search") is not False
        or inference.get("cnn_pretrained_download") is not False
        or inference.get("network_permitted") is not False
        or inference.get("reference_text_available_to_decoder") is not False
        or not isinstance(compatibility, dict)
        or compatibility.get("gpu_family") != "NVIDIA_GEFORCE_RTX_4090_ADA"
        or compatibility.get("minimum_compute_capability") != [8, 9]
        or compatibility.get("historical_blackwell_runtime_claimed") is not False
        or not isinstance(safety, dict)
        or not safety
        or any(bool(value) for value in safety.values())
    ):
        raise VietOCRLogicalRowReaderError("VietOCR logical-row configuration drifted")
    return config


def run_vietocr_logical_row_reader(
    project_root: Path,
    *,
    request_path: Path,
    output_directory: Path,
    runtime_root: Path,
    config_path: Path = Path("config/models/vietocr-0.3.13-rtx4090.toml"),
) -> dict[str, Any]:
    project_root = project_root.resolve()
    runtime_root = runtime_root.resolve()
    request_file = _project_path(project_root, request_path)
    destination = _project_path(project_root, output_directory)
    config_file = _project_path(project_root, config_path)
    if destination.exists():
        raise VietOCRLogicalRowReaderError(f"refusing to overwrite output: {destination}")
    if _git(project_root, "status", "--porcelain"):
        raise VietOCRLogicalRowReaderError(
            "formal E-0036 VietOCR inference requires clean Git code"
        )
    request = _load_json(request_file, "E-0036 reference-blind inference request")
    try:
        samples = validate_logical_row_label_reader_request(request)
    except LogicalRowLabelReaderContractError as error:
        raise VietOCRLogicalRowReaderError(str(error)) from error
    crop_manifest = request["crop_manifest"]
    crop_manifest_path = _project_path(project_root, str(crop_manifest["path"]))
    if (
        not crop_manifest_path.is_file()
        or sha256_file(crop_manifest_path) != crop_manifest["sha256"]
    ):
        raise VietOCRLogicalRowReaderError("E-0035 crop manifest is absent or drifted")

    config = load_vietocr_logical_row_config(config_file)
    artifacts = _verify_artifacts(runtime_root, config)
    site_packages = _runtime_path(runtime_root, str(config["runtime"]["site_packages"]))
    _verify_wheel_overlay(artifacts["wheel"]["path"], site_packages)
    if site_packages.as_posix() not in sys.path:
        sys.path.insert(0, site_packages.as_posix())

    crop_records: list[tuple[dict[str, str], Path]] = []
    for sample in samples:
        crop = _project_path(project_root, sample["crop_path"])
        if not crop.is_file() or sha256_file(crop) != sample["crop_sha256"]:
            raise VietOCRLogicalRowReaderError(
                f"crop is absent or hash-drifted: {sample['sample_id']}"
            )
        crop_records.append((sample, crop))

    merged_config = _model_configuration(
        artifacts["base_config"]["path"],
        artifacts["model_config"]["path"],
        artifacts["weights"]["path"],
        config,
    )
    _deny_network_connections()
    import torch
    from vietocr.tool.translate import build_model, process_input, translate

    expected_packages = config["runtime"]["packages"]
    actual_packages = {
        distribution: importlib.metadata.version(distribution) for distribution in expected_packages
    }
    if actual_packages != expected_packages:
        raise VietOCRLogicalRowReaderError(
            f"VietOCR runtime package drift: {actual_packages} != {expected_packages}"
        )
    capability = torch.cuda.get_device_capability(0) if torch.cuda.is_available() else None
    minimum = tuple(config["runtime_compatibility"]["minimum_compute_capability"])
    if capability is None or capability < minimum:
        raise VietOCRLogicalRowReaderError("VietOCR requires RTX 4090-compatible CUDA")

    started_at = datetime.now(UTC)
    started = time.perf_counter()
    torch.manual_seed(int(config["inference"]["random_seed"]))
    torch.cuda.manual_seed_all(int(config["inference"]["random_seed"]))
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()

    model, vocab = build_model(merged_config)
    state = torch.load(
        artifacts["weights"]["path"],
        map_location=torch.device(merged_config["device"]),
        weights_only=True,
    )
    model.load_state_dict(state)
    model.eval()
    model_load_seconds = time.perf_counter() - started

    results: list[dict[str, Any]] = []
    for sample, crop_path in crop_records:
        line_started = time.perf_counter()
        with Image.open(crop_path) as opened:
            image = opened.convert("RGB")
            tensor = process_input(
                image,
                int(merged_config["dataset"]["image_height"]),
                int(merged_config["dataset"]["image_min_width"]),
                int(merged_config["dataset"]["image_max_width"]),
            ).to(merged_config["device"])
        sentence, probabilities = translate(
            tensor,
            model,
            max_seq_length=int(config["inference"]["max_sequence_length"]),
        )
        prediction = vocab.decode(sentence[0].tolist())
        probability = float(probabilities[0])
        torch.cuda.synchronize()
        results.append(
            {
                "sample_id": sample["sample_id"],
                "category": sample["category"],
                "crop_path": sample["crop_path"],
                "crop_sha256": sample["crop_sha256"],
                "processed_width": int(tensor.shape[-1]),
                "processed_height": int(tensor.shape[-2]),
                "raw_prediction": prediction,
                "mean_decoded_character_probability": (
                    probability if math.isfinite(probability) else None
                ),
                "wall_seconds": time.perf_counter() - line_started,
            }
        )
        del tensor

    torch.cuda.synchronize()
    total_seconds = time.perf_counter() - started
    state_name = "REFERENCE_BLIND_LOGICAL_ROW_LABEL_INFERENCE_COMPLETE"
    result_payload = {
        "format_version": 1,
        "experiment_id": "E-0036",
        "reader": "VIETOCR_VGG_TRANSFORMER",
        "state": state_name,
        "dataset_role": "CALIBRATION",
        "evidence_role": request["evidence_role"],
        "reference_text_available_to_reader": False,
        "sample_count": len(results),
        "samples": results,
        "authority": {key: False for key in config["safety"]},
    }
    manifest: dict[str, Any] = {
        "format_version": 1,
        "experiment_id": "E-0036",
        "reader": "VIETOCR_VGG_TRANSFORMER",
        "state": state_name,
        "started_at": started_at.isoformat(),
        "completed_at": datetime.now(UTC).isoformat(),
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
            "network_policy": "PROCESS_SOCKET_CONNECT_AND_DNS_DENIED",
            "reference_text_available_to_decoder": False,
        },
        "runtime": {
            "external_root": runtime_root.as_posix(),
            "site_packages": site_packages.relative_to(runtime_root).as_posix(),
            "packages": actual_packages,
            "torch_cuda_build": torch.version.cuda,
            "device": torch.cuda.get_device_name(0),
            "compute_capability": list(capability),
            "artifacts": {
                key: {
                    "path": value["path"].relative_to(runtime_root).as_posix(),
                    "size_bytes": value["size_bytes"],
                    "sha256": value["sha256"],
                    "url": value["url"],
                }
                for key, value in artifacts.items()
            },
        },
        "metrics": {
            "sample_count": len(results),
            "model_load_seconds": model_load_seconds,
            "total_wall_seconds": total_seconds,
            "peak_gpu_memory_allocated_mib": torch.cuda.max_memory_allocated() / 1024**2,
            "peak_gpu_memory_reserved_mib": torch.cuda.max_memory_reserved() / 1024**2,
        },
        "safety": {key: False for key in config["safety"]},
    }
    _write_output_directory(destination, result_payload, manifest)
    return manifest


__all__ = [
    "VietOCRLogicalRowReaderError",
    "load_vietocr_logical_row_config",
    "run_vietocr_logical_row_reader",
]
