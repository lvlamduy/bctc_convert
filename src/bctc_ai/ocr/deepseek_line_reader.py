from __future__ import annotations

import importlib.metadata
import json
import os
import re
import shutil
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


class DeepSeekLineReaderError(RuntimeError):
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
_SAMPLE_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,127}")
_FORBIDDEN_SERIALIZATION = re.compile(
    r"(?:<\|/?(?:ref|det|grounding)\|>|<table|</table>|```|^\s*\|.*\|\s*$)",
    re.IGNORECASE | re.MULTILINE,
)


def _load_toml(path: Path, name: str) -> dict[str, Any]:
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise DeepSeekLineReaderError(f"cannot load {name}: {path}") from exc
    if not isinstance(payload, dict):
        raise DeepSeekLineReaderError(f"{name} must contain a TOML table")
    return payload


def _project_path(project_root: Path, value: str, label: str) -> Path:
    path = (project_root / value).resolve()
    try:
        path.relative_to(project_root)
    except ValueError as exc:
        raise DeepSeekLineReaderError(f"{label} escapes the project root") from exc
    return path


def _git(project_root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def load_deepseek_line_config(
    project_root: Path,
    config_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    project_root = project_root.resolve()
    resolved = (
        config_path.resolve()
        if config_path.is_absolute()
        else _project_path(project_root, config_path.as_posix(), "line config")
    )
    if not resolved.is_relative_to(project_root):
        raise DeepSeekLineReaderError("line config escapes the project root")
    config = _load_toml(resolved, "DeepSeek line config")
    if (
        config.get("version") != 1
        or config.get("status")
        != "CALIBRATION_ONLY_REFERENCE_BLIND_BOUNDED_SEMANTIC_READER"
        or config.get("reader") != "DEEPSEEK_OCR_2"
        or config.get("geometry_authority") != "PP_OCRV6_WORD_BOXES"
        or config.get("evidence_role")
        != "VIETNAMESE_TITLE_LABEL_READING_ORDER_PROPOSAL_ONLY"
    ):
        raise DeepSeekLineReaderError("DeepSeek line config identity or role drifted")
    base_identity = config.get("base_model")
    if not isinstance(base_identity, dict):
        raise DeepSeekLineReaderError("DeepSeek line config has no base-model identity")
    base_path = _project_path(
        project_root, str(base_identity.get("config_path", "")), "base model config"
    )
    if not base_path.is_file() or sha256_file(base_path) != base_identity.get("config_sha256"):
        raise DeepSeekLineReaderError("DeepSeek base model config is absent or hash-drifted")
    base = _load_toml(base_path, "DeepSeek base model config")
    inference = config.get("inference")
    if not isinstance(inference, dict) or (
        inference.get("prompt") != "<image>\nFree OCR."
        or inference.get("crop_mode") is not False
        or inference.get("attention_implementation") != "eager"
        or inference.get("network_permitted") is not False
        or inference.get("reference_text_available_to_decoder") is not False
        or inference.get("target_policy")
        != "FROZEN_PP_OCRV6_LINE_TITLE_OR_LOGICAL_ROW_CROPS_ONLY"
        or not isinstance(inference.get("maximum_nonempty_output_lines"), int)
        or int(inference["maximum_nonempty_output_lines"]) < 1
    ):
        raise DeepSeekLineReaderError("DeepSeek bounded line inference policy drifted")
    if any(
        isinstance(inference.get(key), bool)
        or not isinstance(inference.get(key), int)
        or int(inference[key]) < 1
        for key in ("base_size", "image_size")
    ):
        raise DeepSeekLineReaderError("DeepSeek line image sizing is invalid")
    safety = config.get("safety")
    if not isinstance(safety, dict) or not safety or any(bool(value) for value in safety.values()):
        raise DeepSeekLineReaderError("DeepSeek line config grants forbidden authority")
    base_inference = base.get("inference")
    base_safety = base.get("safety")
    if not isinstance(base_inference, dict) or (
        base.get("version") != 1
        or base.get("status") != "CALIBRATION_ONLY_SEMANTIC_OCR_PROPOSAL"
        or base_inference.get("attention_implementation") != "eager"
        or base_inference.get("network_permitted") is not False
        or not isinstance(base_safety, dict)
        or not base_safety
        or any(bool(value) for value in base_safety.values())
    ):
        raise DeepSeekLineReaderError("DeepSeek base model safety policy drifted")
    return config, base, resolved


def validate_reference_blind_line_request(payload: dict[str, Any]) -> list[dict[str, str]]:
    if set(payload) != _REQUEST_KEYS:
        raise DeepSeekLineReaderError("line-reader request contains forbidden fields")
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
        raise DeepSeekLineReaderError("line-reader request identity or evidence role is invalid")
    manifest = payload.get("crop_manifest")
    if not isinstance(manifest, dict) or set(manifest) != {"path", "sha256"}:
        raise DeepSeekLineReaderError("line-reader crop-manifest identity is invalid")
    raw_samples = payload.get("samples")
    if not isinstance(raw_samples, list) or len(raw_samples) != payload.get("sample_count"):
        raise DeepSeekLineReaderError("line-reader sample denominator is invalid")
    samples: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in raw_samples:
        if not isinstance(raw, dict) or set(raw) != _REQUEST_SAMPLE_KEYS:
            raise DeepSeekLineReaderError("line-reader sample contains a forbidden field")
        sample = {key: str(raw[key]) for key in _REQUEST_SAMPLE_KEYS}
        if _SAMPLE_ID.fullmatch(sample["sample_id"]) is None or sample["sample_id"] in seen:
            raise DeepSeekLineReaderError("line-reader sample identity is unsafe or duplicated")
        seen.add(sample["sample_id"])
        samples.append(sample)
    return samples


def parse_free_ocr_output(raw_output: str, *, maximum_nonempty_lines: int) -> dict[str, Any]:
    if not isinstance(raw_output, str) or not raw_output.strip():
        return {
            "status": "REJECT_EMPTY_OUTPUT",
            "proposal_text": "",
            "nonempty_line_count": 0,
        }
    lines = [normalize_text(line) for line in raw_output.splitlines() if normalize_text(line)]
    if len(lines) > maximum_nonempty_lines:
        return {
            "status": "REJECT_TOO_MANY_OUTPUT_LINES",
            "proposal_text": "",
            "nonempty_line_count": len(lines),
        }
    if _FORBIDDEN_SERIALIZATION.search(raw_output):
        return {
            "status": "REJECT_DOCUMENT_OR_LAYOUT_SERIALIZATION",
            "proposal_text": "",
            "nonempty_line_count": len(lines),
        }
    proposal = normalize_text(" ".join(lines))
    if not proposal or not any(char.isalpha() for char in proposal):
        return {
            "status": "REJECT_NON_TEXTUAL_OUTPUT",
            "proposal_text": "",
            "nonempty_line_count": len(lines),
        }
    return {
        "status": "PARSED_SEMANTIC_PROPOSAL_ONLY",
        "proposal_text": proposal,
        "nonempty_line_count": len(lines),
    }


def _verify_model(model_directory: Path, base: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts = base.get("artifacts")
    if not isinstance(artifacts, dict) or len(artifacts) != 14:
        raise DeepSeekLineReaderError("DeepSeek artifact registry is incomplete")
    records = []
    total_bytes = 0
    for key, raw in sorted(artifacts.items()):
        if not isinstance(raw, dict):
            raise DeepSeekLineReaderError("DeepSeek artifact record is invalid")
        path = (model_directory / str(raw.get("path", ""))).resolve()
        if not path.is_relative_to(model_directory.resolve()):
            raise DeepSeekLineReaderError("DeepSeek artifact escapes model directory")
        if (
            not path.is_file()
            or path.stat().st_size != int(raw.get("size_bytes", -1))
            or sha256_file(path) != str(raw.get("sha256", ""))
        ):
            raise DeepSeekLineReaderError(f"DeepSeek artifact is absent or drifted: {key}")
        total_bytes += path.stat().st_size
        records.append(
            {
                "key": key,
                "path": str(raw["path"]),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    if total_bytes != int(base.get("required_artifact_bytes", -1)):
        raise DeepSeekLineReaderError("DeepSeek verified artifact byte count drifted")
    return records


def _verify_packages(base: dict[str, Any]) -> dict[str, str]:
    compatibility = base.get("runtime_compatibility")
    expected = compatibility.get("packages") if isinstance(compatibility, dict) else None
    if not isinstance(expected, dict):
        raise DeepSeekLineReaderError("DeepSeek runtime package registry is absent")
    actual: dict[str, str] = {}
    for distribution, expected_version in expected.items():
        try:
            version = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError as exc:
            raise DeepSeekLineReaderError(
                f"required DeepSeek runtime package is missing: {distribution}"
            ) from exc
        if version != expected_version:
            raise DeepSeekLineReaderError(
                f"DeepSeek runtime package drift: {distribution} {version} != {expected_version}"
            )
        actual[str(distribution)] = version
    actual_python = f"{sys.version_info.major}.{sys.version_info.minor}"
    if actual_python != str(compatibility.get("python_major_minor")):
        raise DeepSeekLineReaderError("DeepSeek Python runtime version drifted")
    return actual


def _deny_network_connections() -> None:
    def audit_hook(event: str, _: tuple[Any, ...]) -> None:
        if event in {"socket.connect", "socket.getaddrinfo"}:
            raise RuntimeError("network access is forbidden during DeepSeek line inference")

    sys.addaudithook(audit_hook)


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
            raise DeepSeekLineReaderError(f"output appeared during inference: {destination}")
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def run_deepseek_line_reader(
    project_root: Path,
    *,
    request_path: Path,
    output_directory: Path,
    model_cache_root: Path,
    config_path: Path = Path("config/models/deepseek-ocr2-line-v1.toml"),
) -> dict[str, Any]:
    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise DeepSeekLineReaderError("formal DeepSeek line inference requires clean Git code")
    config, base, config_file = load_deepseek_line_config(project_root, config_path)
    request_file = _project_path(project_root, request_path.as_posix(), "line-reader request")
    destination = _project_path(
        project_root, output_directory.as_posix(), "DeepSeek line output"
    )
    if destination.exists():
        raise DeepSeekLineReaderError(f"refusing to overwrite DeepSeek line output: {destination}")
    try:
        request = json.loads(request_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DeepSeekLineReaderError("cannot read reference-blind line request") from exc
    if not isinstance(request, dict):
        raise DeepSeekLineReaderError("reference-blind line request must be an object")
    samples = validate_reference_blind_line_request(request)
    crop_manifest = request["crop_manifest"]
    crop_manifest_path = _project_path(
        project_root, str(crop_manifest["path"]), "crop manifest"
    )
    if (
        not crop_manifest_path.is_file()
        or sha256_file(crop_manifest_path) != crop_manifest["sha256"]
    ):
        raise DeepSeekLineReaderError("reference-blind crop manifest is absent or drifted")

    verified_samples = []
    for sample in samples:
        crop = _project_path(project_root, sample["crop_path"], "line crop")
        if not crop.is_file() or sha256_file(crop) != sample["crop_sha256"]:
            raise DeepSeekLineReaderError(f"line crop is absent or drifted: {sample['sample_id']}")
        try:
            with Image.open(crop) as image:
                width, height = image.size
                image.verify()
        except OSError as exc:
            raise DeepSeekLineReaderError(f"line crop is not a valid image: {crop}") from exc
        if width < 1 or height < 1:
            raise DeepSeekLineReaderError("line crop dimensions are invalid")
        verified_samples.append(sample | {"resolved_crop": crop, "width": width, "height": height})

    model_directory = (
        model_cache_root.resolve() / "official_models" / str(base["cache_directory"])
    )
    model_artifacts = _verify_model(model_directory, base)
    package_versions = _verify_packages(base)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ.setdefault("HF_HOME", "/dev/shm/bctc-deepseek-ocr2-line-hf")
    os.environ.setdefault("HF_MODULES_CACHE", "/dev/shm/bctc-deepseek-ocr2-line-hf/modules")
    _deny_network_connections()

    import torch
    from transformers import AutoModel, AutoTokenizer

    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise DeepSeekLineReaderError("DeepSeek line reader requires BF16 CUDA")
    compatibility = base["runtime_compatibility"]
    capability = list(torch.cuda.get_device_capability(0))
    if capability < list(compatibility["minimum_compute_capability"]):
        raise DeepSeekLineReaderError("GPU compute capability is below DeepSeek minimum")

    started_at = datetime.now(UTC)
    total_started = time.perf_counter()
    torch.cuda.reset_peak_memory_stats()
    load_started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(
        model_directory.as_posix(), trust_remote_code=True, local_files_only=True
    )
    model = AutoModel.from_pretrained(
        model_directory.as_posix(),
        trust_remote_code=True,
        local_files_only=True,
        use_safetensors=True,
        _attn_implementation="eager",
        torch_dtype=torch.bfloat16,
    ).eval().cuda()
    torch.cuda.synchronize()
    load_seconds = time.perf_counter() - load_started

    inference = config["inference"]
    temporary_internal = Path(
        tempfile.mkdtemp(prefix="bctc-deepseek-line-", dir="/dev/shm")
    )
    records = []
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
                crop_mode=False,
                save_results=False,
                eval_mode=True,
            )
            torch.cuda.synchronize()
            if not isinstance(raw_output, str):
                raise DeepSeekLineReaderError(
                    f"DeepSeek returned non-text output: {sample['sample_id']}"
                )
            parsed = parse_free_ocr_output(
                raw_output,
                maximum_nonempty_lines=int(inference["maximum_nonempty_output_lines"]),
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

    total_seconds = time.perf_counter() - total_started
    result: dict[str, Any] = {
        "format_version": 1,
        "experiment_id": "E-0025",
        "state": "REFERENCE_BLIND_DEEPSEEK_BOUNDED_LINE_INFERENCE_COMPLETE",
        "dataset_role": request["dataset_role"],
        "evidence_role": config["evidence_role"],
        "reference_text_available_to_reader": False,
        "sample_count": len(records),
        "samples": records,
        "authority": {key: False for key in config["safety"]},
    }
    free_bytes, total_bytes = torch.cuda.mem_get_info()
    manifest: dict[str, Any] = {
        "format_version": 1,
        "experiment_id": "E-0025",
        "state": "REFERENCE_BLIND_DEEPSEEK_BOUNDED_LINE_INFERENCE_COMPLETE",
        "dataset_role": request["dataset_role"],
        "evidence_role": config["evidence_role"],
        "git_commit": _git(project_root, "rev-parse", "HEAD"),
        "git_dirty": False,
        "request": {
            "path": request_file.relative_to(project_root).as_posix(),
            "sha256": sha256_file(request_file),
        },
        "crop_manifest": request["crop_manifest"],
        "configuration": {
            "path": config_file.relative_to(project_root).as_posix(),
            "sha256": sha256_file(config_file),
            "base_model_config_path": config["base_model"]["config_path"],
            "base_model_config_sha256": config["base_model"]["config_sha256"],
            "prompt": inference["prompt"],
            "base_size": inference["base_size"],
            "image_size": inference["image_size"],
            "crop_mode": False,
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
            "model_load_seconds": load_seconds,
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
    "DeepSeekLineReaderError",
    "load_deepseek_line_config",
    "parse_free_ocr_output",
    "run_deepseek_line_reader",
    "validate_reference_blind_line_request",
]
