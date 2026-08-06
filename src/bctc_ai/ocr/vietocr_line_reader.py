from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from PIL import Image

from bctc_ai.core.hashing import sha256_file


class VietOCRLineReaderError(RuntimeError):
    pass


_REQUEST_KEYS = {
    "format_version",
    "experiment_id",
    "state",
    "dataset_role",
    "evidence_role",
    "git_commit",
    "git_dirty",
    "crop_manifest",
    "reference_text_available_to_reader",
    "sample_count",
    "samples",
}
_REQUEST_SAMPLE_KEYS = {"sample_id", "category", "crop_path", "crop_sha256"}


def _git(project_root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _project_path(project_root: Path, path: Path | str) -> Path:
    value = (project_root / path).resolve()
    try:
        value.relative_to(project_root)
    except ValueError as exc:
        raise VietOCRLineReaderError(f"project artifact escapes project root: {path}") from exc
    return value


def _runtime_path(runtime_root: Path, relative: str) -> Path:
    value = (runtime_root / relative).resolve()
    try:
        value.relative_to(runtime_root)
    except ValueError as exc:
        raise VietOCRLineReaderError(f"runtime artifact escapes runtime root: {relative}") from exc
    return value


def _load_json(path: Path, name: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise VietOCRLineReaderError(f"cannot read {name}: {path}") from exc
    if not isinstance(value, dict):
        raise VietOCRLineReaderError(f"{name} must be an object")
    return value


def _load_config(path: Path) -> dict[str, Any]:
    try:
        value = tomllib.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, tomllib.TOMLDecodeError) as exc:
        raise VietOCRLineReaderError(f"cannot read VietOCR config: {path}") from exc
    if (
        value.get("version") != 1
        or value.get("status") != "CALIBRATION_ONLY_VIETNAMESE_SEMANTIC_LINE_PROPOSAL"
    ):
        raise VietOCRLineReaderError("VietOCR config identity or status drifted")
    inference = value.get("inference")
    if not isinstance(inference, dict) or (
        inference.get("network_permitted") is not False
        or inference.get("beam_search") is not False
        or inference.get("cnn_pretrained_download") is not False
        or inference.get("reference_text_available_to_decoder") is not False
        or inference.get("device") != "cuda:0"
    ):
        raise VietOCRLineReaderError("VietOCR inference policy is unsafe or unsupported")
    safety = value.get("safety")
    if not isinstance(safety, dict) or not safety or any(bool(item) for item in safety.values()):
        raise VietOCRLineReaderError("VietOCR config grants forbidden pipeline authority")
    return value


def validate_reference_blind_request(payload: dict[str, Any]) -> list[dict[str, str]]:
    if set(payload) != _REQUEST_KEYS:
        raise VietOCRLineReaderError("line-reader request has non-allowlisted top-level fields")
    if (
        payload.get("format_version") != 1
        or payload.get("experiment_id") != "E-0024"
        or payload.get("state") != "READY_FOR_REFERENCE_BLIND_LINE_INFERENCE"
        or payload.get("dataset_role") != "LOGIC_DEVELOPMENT_AND_CALIBRATION"
        or payload.get("evidence_role")
        != "INDEPENDENT_VIETNAMESE_SEMANTIC_PROPOSAL_ONLY"
        or payload.get("git_dirty") is not False
        or payload.get("reference_text_available_to_reader") is not False
    ):
        raise VietOCRLineReaderError("line-reader request identity or role is invalid")
    manifest = payload.get("crop_manifest")
    if not isinstance(manifest, dict) or set(manifest) != {"path", "sha256"}:
        raise VietOCRLineReaderError("line-reader request crop-manifest identity is invalid")
    raw_samples = payload.get("samples")
    if not isinstance(raw_samples, list) or len(raw_samples) != payload.get("sample_count"):
        raise VietOCRLineReaderError("line-reader request sample denominator is invalid")
    samples: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in raw_samples:
        if not isinstance(raw, dict) or set(raw) != _REQUEST_SAMPLE_KEYS:
            raise VietOCRLineReaderError("line-reader sample contains a forbidden field")
        sample = {key: str(raw[key]) for key in _REQUEST_SAMPLE_KEYS}
        if not sample["sample_id"] or sample["sample_id"] in seen:
            raise VietOCRLineReaderError("line-reader sample IDs must be unique")
        seen.add(sample["sample_id"])
        samples.append(sample)
    return samples


def _verify_artifacts(runtime_root: Path, config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = config.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != {
        "wheel",
        "base_config",
        "model_config",
        "weights",
    }:
        raise VietOCRLineReaderError("VietOCR artifact registry is incomplete")
    records: dict[str, dict[str, Any]] = {}
    for key, raw in artifacts.items():
        if not isinstance(raw, dict):
            raise VietOCRLineReaderError(f"invalid VietOCR artifact record: {key}")
        path = _runtime_path(runtime_root, str(raw.get("path", "")))
        if (
            not path.is_file()
            or path.stat().st_size != int(raw.get("size_bytes", -1))
            or sha256_file(path) != str(raw.get("sha256", ""))
        ):
            raise VietOCRLineReaderError(f"VietOCR artifact is absent or hash-drifted: {key}")
        records[key] = {
            "path": path,
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "url": str(raw.get("url", "")),
        }
    return records


def _verify_wheel_overlay(wheel: Path, site_packages: Path) -> None:
    if not site_packages.is_dir():
        raise VietOCRLineReaderError(f"VietOCR overlay is missing: {site_packages}")
    with zipfile.ZipFile(wheel) as archive:
        members = [member for member in archive.infolist() if not member.is_dir()]
        for member in members:
            installed = site_packages / member.filename
            if not installed.is_file():
                raise VietOCRLineReaderError(f"VietOCR overlay file is missing: {member.filename}")
            expected = hashlib.sha256(archive.read(member)).hexdigest()
            if sha256_file(installed) != expected:
                raise VietOCRLineReaderError(f"VietOCR overlay file drifted: {member.filename}")


def _deny_network_connections() -> None:
    def audit_hook(event: str, _: tuple[Any, ...]) -> None:
        if event in {"socket.connect", "socket.getaddrinfo"}:
            raise RuntimeError("network access is forbidden during VietOCR inference")

    sys.addaudithook(audit_hook)


def _model_configuration(
    base_path: Path,
    model_path: Path,
    weights_path: Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    try:
        base = yaml.safe_load(base_path.read_text(encoding="utf-8"))
        model = yaml.safe_load(model_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise VietOCRLineReaderError("VietOCR upstream YAML is invalid") from exc
    if not isinstance(base, dict) or not isinstance(model, dict):
        raise VietOCRLineReaderError("VietOCR upstream YAML must contain objects")
    merged = dict(base)
    merged.update(model)
    merged["device"] = str(config["inference"]["device"])
    merged["weights"] = weights_path.as_posix()
    merged["predictor"] = dict(merged.get("predictor", {}))
    merged["predictor"]["beamsearch"] = False
    merged["cnn"] = dict(merged.get("cnn", {}))
    merged["cnn"]["pretrained"] = False
    required = {"vocab", "device", "seq_modeling", "transformer", "dataset", "backbone", "cnn"}
    if not required.issubset(merged):
        raise VietOCRLineReaderError("VietOCR merged model configuration is incomplete")
    if merged["seq_modeling"] != "transformer" or merged["backbone"] != "vgg19_bn":
        raise VietOCRLineReaderError("VietOCR architecture differs from the declared challenger")
    return merged


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
                "path": "ocr_result.json",
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
            raise VietOCRLineReaderError(f"output appeared during inference: {destination}")
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def run_vietocr_line_reader(
    project_root: Path,
    *,
    request_path: Path,
    output_directory: Path,
    runtime_root: Path,
    config_path: Path = Path("config/models/vietocr-0.3.13.toml"),
) -> dict[str, Any]:
    project_root = project_root.resolve()
    runtime_root = runtime_root.resolve()
    request = _project_path(project_root, request_path)
    destination = _project_path(project_root, output_directory)
    model_config_path = _project_path(project_root, config_path)
    if destination.exists():
        raise VietOCRLineReaderError(f"refusing to overwrite output: {destination}")
    git_status = _git(project_root, "status", "--porcelain")
    if git_status:
        raise VietOCRLineReaderError("formal VietOCR inference requires a clean Git worktree")
    request_payload = _load_json(request, "reference-blind inference request")
    samples = validate_reference_blind_request(request_payload)
    config = _load_config(model_config_path)
    artifact_records = _verify_artifacts(runtime_root, config)
    site_packages = _runtime_path(runtime_root, str(config["runtime"]["site_packages"]))
    _verify_wheel_overlay(artifact_records["wheel"]["path"], site_packages)
    if site_packages.as_posix() not in sys.path:
        sys.path.insert(0, site_packages.as_posix())

    crop_records = []
    for sample in samples:
        crop = _project_path(project_root, sample["crop_path"])
        if not crop.is_file() or sha256_file(crop) != sample["crop_sha256"]:
            raise VietOCRLineReaderError(f"crop is missing or hash-drifted: {sample['sample_id']}")
        crop_records.append((sample, crop))

    merged_config = _model_configuration(
        artifact_records["base_config"]["path"],
        artifact_records["model_config"]["path"],
        artifact_records["weights"]["path"],
        config,
    )
    started_at = datetime.now(UTC)
    started = time.perf_counter()
    _deny_network_connections()

    import torch
    from vietocr.tool.translate import build_model, process_input, translate

    expected_packages = config["runtime"]["packages"]
    actual_packages = {
        distribution: importlib.metadata.version(distribution)
        for distribution in expected_packages
    }
    if actual_packages != expected_packages:
        raise VietOCRLineReaderError(
            f"VietOCR runtime package drift: {actual_packages} != {expected_packages}"
        )
    if not torch.cuda.is_available() or torch.cuda.get_device_capability(0) != (12, 0):
        raise VietOCRLineReaderError("VietOCR requires the verified Blackwell CUDA device")
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
        artifact_records["weights"]["path"],
        map_location=torch.device(merged_config["device"]),
        weights_only=True,
    )
    model.load_state_dict(state)
    model.eval()
    model_load_seconds = time.perf_counter() - started

    results = []
    for sample, crop_path in crop_records:
        line_started = time.perf_counter()
        with Image.open(crop_path) as raw_image:
            image = raw_image.convert("RGB")
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
                "mean_decoded_character_probability": probability
                if math.isfinite(probability)
                else None,
                "wall_seconds": time.perf_counter() - line_started,
            }
        )
        del tensor

    torch.cuda.synchronize()
    total_seconds = time.perf_counter() - started
    result_payload = {
        "format_version": 1,
        "experiment_id": "E-0024",
        "state": "REFERENCE_BLIND_LINE_INFERENCE_COMPLETE",
        "dataset_role": request_payload["dataset_role"],
        "evidence_role": request_payload["evidence_role"],
        "reference_text_available_to_reader": False,
        "sample_count": len(results),
        "samples": results,
    }
    manifest: dict[str, Any] = {
        "format_version": 1,
        "experiment_id": "E-0024",
        "state": "REFERENCE_BLIND_LINE_INFERENCE_COMPLETE",
        "started_at": started_at.isoformat(),
        "completed_at": datetime.now(UTC).isoformat(),
        "git_commit": _git(project_root, "rev-parse", "HEAD"),
        "git_dirty": False,
        "request": {
            "path": request.relative_to(project_root).as_posix(),
            "sha256": sha256_file(request),
        },
        "configuration": {
            "path": model_config_path.relative_to(project_root).as_posix(),
            "sha256": sha256_file(model_config_path),
            "network_policy": "PROCESS_SOCKET_CONNECT_AND_DNS_DENIED",
            "cnn_pretrained_download": False,
            "beam_search": False,
            "reference_text_available_to_decoder": False,
        },
        "runtime": {
            "external_root": runtime_root.as_posix(),
            "site_packages": site_packages.relative_to(runtime_root).as_posix(),
            "packages": actual_packages,
            "torch_cuda_build": torch.version.cuda,
            "device": torch.cuda.get_device_name(0),
            "compute_capability": ".".join(map(str, torch.cuda.get_device_capability(0))),
            "artifacts": {
                key: {
                    "path": value["path"].relative_to(runtime_root).as_posix(),
                    "size_bytes": value["size_bytes"],
                    "sha256": value["sha256"],
                    "url": value["url"],
                }
                for key, value in artifact_records.items()
            },
        },
        "metrics": {
            "sample_count": len(results),
            "model_load_seconds": model_load_seconds,
            "total_wall_seconds": total_seconds,
            "peak_gpu_memory_allocated_mib": torch.cuda.max_memory_allocated() / (1024**2),
            "peak_gpu_memory_reserved_mib": torch.cuda.max_memory_reserved() / (1024**2),
        },
        "safety": {
            "numeric_authority": False,
            "period_authority": False,
            "unit_authority": False,
            "sign_authority": False,
            "geometry_authority": False,
            "mapping_authority": False,
            "automatic_truth_promotion": False,
        },
    }
    _write_output_directory(destination, result_payload, manifest)
    return manifest
