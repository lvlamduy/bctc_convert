from __future__ import annotations

import argparse
import ast
import hashlib
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

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "config/models/deepseek-ocr2-v1.toml"
RUNTIME_MANIFEST = PROJECT_ROOT / "config/models/gpu-runtime.toml"
REFERENCE_PATTERN = re.compile(
    r"<\|ref\|>(.*?)<\|/ref\|>\s*<\|det\|>(.*?)<\|/det\|>",
    flags=re.DOTALL,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _project_path(path_text: str, label: str) -> Path:
    path = (PROJECT_ROOT / path_text).resolve()
    try:
        path.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise RuntimeError(f"{label} escapes the project root") from exc
    return path


def _load_config(path: Path) -> dict[str, Any]:
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != 1:
        raise RuntimeError("DeepSeek-OCR-2 config must be version 1")
    if payload.get("status") != "CALIBRATION_ONLY_SEMANTIC_OCR_PROPOSAL":
        raise RuntimeError("DeepSeek-OCR-2 is not restricted to calibration proposals")
    inference = payload.get("inference", {})
    if inference.get("target_policy") != "FAILED_OR_AMBIGUOUS_REGIONS_ONLY":
        raise RuntimeError("DeepSeek-OCR-2 target policy is too broad")
    if inference.get("network_permitted") is not False:
        raise RuntimeError("DeepSeek-OCR-2 inference must be offline")
    if inference.get("attention_implementation") != "eager":
        raise RuntimeError("only the pinned eager-attention path is permitted")
    safety = payload.get("safety", {})
    if not safety or any(bool(value) for value in safety.values()):
        raise RuntimeError("DeepSeek-OCR-2 config grants forbidden pipeline authority")
    overlay = payload.get("runtime_overlay", {})
    requirements = _project_path(str(overlay.get("requirements_path", "")), "overlay lock")
    if not requirements.is_file():
        raise FileNotFoundError(f"DeepSeek-OCR-2 overlay lock is missing: {requirements}")
    if _sha256(requirements) != overlay.get("requirements_sha256"):
        raise RuntimeError("DeepSeek-OCR-2 overlay lock hash drifted")
    if overlay.get("flash_attention_required") is not False:
        raise RuntimeError("the Blackwell compatibility path must not require FlashAttention")
    return payload


def _git_state() -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return {"commit": commit, "dirty": bool(status.strip())}


def _verify_model(model_directory: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    total_bytes = 0
    for key, artifact in sorted(config["artifacts"].items()):
        path = model_directory / str(artifact["path"])
        if not path.is_file():
            raise FileNotFoundError(f"missing pinned DeepSeek-OCR-2 artifact: {path}")
        size = path.stat().st_size
        digest = _sha256(path)
        if size != int(artifact["size_bytes"]) or digest != str(artifact["sha256"]):
            raise RuntimeError(f"pinned DeepSeek-OCR-2 artifact mismatch: {path}")
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
        raise RuntimeError("DeepSeek-OCR-2 verified byte count differs from the config")
    return records


def _verify_package_versions(config: dict[str, Any]) -> dict[str, str]:
    expected = config["runtime_compatibility"]["packages"]
    actual: dict[str, str] = {}
    for distribution, expected_version in expected.items():
        try:
            version = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError as exc:
            raise RuntimeError(f"required runtime package is missing: {distribution}") from exc
        if version != expected_version:
            raise RuntimeError(
                f"runtime version mismatch for {distribution}: {version} != {expected_version}"
            )
        actual[distribution] = version
    expected_python = str(config["runtime_compatibility"]["python_major_minor"])
    actual_python = f"{sys.version_info.major}.{sys.version_info.minor}"
    if actual_python != expected_python:
        raise RuntimeError(f"Python runtime mismatch: {actual_python} != {expected_python}")
    return actual


def _deny_network_connections() -> None:
    def audit_hook(event: str, _: tuple[Any, ...]) -> None:
        if event in {"socket.connect", "socket.getaddrinfo"}:
            raise RuntimeError("network access is forbidden during DeepSeek-OCR-2 inference")

    sys.addaudithook(audit_hook)


def _normalize_boxes(value: Any) -> tuple[list[list[float]], str]:
    if (
        isinstance(value, (list, tuple))
        and len(value) == 4
        and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value)
    ):
        value = [value]
    if not isinstance(value, (list, tuple)):
        return [], "INVALID_COORDINATE_SYNTAX"
    boxes: list[list[float]] = []
    for box in value:
        if not isinstance(box, (list, tuple)) or len(box) != 4:
            return [], "INVALID_COORDINATE_SYNTAX"
        if not all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in box):
            return [], "INVALID_COORDINATE_SYNTAX"
        numeric_box = [float(item) for item in box]
        if not all(0 <= item <= 999 for item in numeric_box):
            return [], "OUT_OF_NORMALIZED_RANGE"
        if numeric_box[2] < numeric_box[0] or numeric_box[3] < numeric_box[1]:
            return [], "INVERTED_COORDINATES"
        boxes.append(numeric_box)
    return boxes, "PROPOSAL_ONLY"


def parse_layout_references(raw_output: str) -> list[dict[str, Any]]:
    records = []
    for index, match in enumerate(REFERENCE_PATTERN.finditer(raw_output)):
        raw_coordinates = match.group(2).strip()
        try:
            decoded = ast.literal_eval(raw_coordinates)
        except (SyntaxError, ValueError):
            decoded = None
        boxes, status = _normalize_boxes(decoded)
        records.append(
            {
                "index": index,
                "label": match.group(1).strip(),
                "raw_coordinates": raw_coordinates,
                "normalized_0_999_boxes": boxes,
                "status": status,
                "authority": "NONE_GEOMETRY_PROPOSAL_ONLY",
            }
        )
    return records


def _write_result(
    output_directory: Path,
    temporary: Path,
    result: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    result_path = temporary / "ocr_result.json"
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest["artifacts"] = {
        "ocr_result": {
            "path": result_path.name,
            "size_bytes": result_path.stat().st_size,
            "sha256": _sha256(result_path),
        }
    }
    manifest_path = temporary / "run_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if output_directory.exists():
        raise FileExistsError(f"output appeared during inference: {output_directory}")
    os.replace(temporary, output_directory)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run pinned DeepSeek-OCR-2 on one failed or ambiguous document region"
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--model-cache", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--dataset-role", choices=("CALIBRATION", "HOLDOUT"), required=True)
    parser.add_argument("--allow-dirty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = args.input.resolve()
    output_directory = args.output_directory.resolve()
    config_path = args.config.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"input image does not exist: {input_path}")
    if output_directory.exists():
        raise FileExistsError(f"refusing to overwrite output: {output_directory}")
    if not config_path.is_file():
        raise FileNotFoundError(f"DeepSeek-OCR-2 config does not exist: {config_path}")

    config = _load_config(config_path)
    git = _git_state()
    if git["dirty"] and not args.allow_dirty:
        raise RuntimeError("refusing evidence OCR from a dirty Git worktree")
    model_directory = (
        args.model_cache.resolve() / "official_models" / str(config["cache_directory"])
    )
    model_records = _verify_model(model_directory, config)
    package_versions = _verify_package_versions(config)

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ.setdefault("HF_HOME", "/dev/shm/bctc-deepseek-ocr2-hf-runtime")
    os.environ.setdefault("HF_MODULES_CACHE", "/dev/shm/bctc-deepseek-ocr2-hf-runtime/modules")
    _deny_network_connections()

    import torch
    from transformers import AutoModel, AutoTokenizer

    if not torch.cuda.is_available():
        raise RuntimeError("DeepSeek-OCR-2 requires an available CUDA GPU")
    capability = list(torch.cuda.get_device_capability(0))
    minimum_capability = list(config["runtime_compatibility"]["minimum_compute_capability"])
    if capability < minimum_capability:
        raise RuntimeError(f"GPU compute capability is too old: {capability}")
    if not torch.cuda.is_bf16_supported():
        raise RuntimeError("GPU does not report BF16 support")

    output_directory.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{output_directory.name}.", dir=output_directory.parent)
    )
    started_at = datetime.now(UTC)
    total_started = time.perf_counter()
    torch.cuda.reset_peak_memory_stats()
    try:
        load_started = time.perf_counter()
        tokenizer = AutoTokenizer.from_pretrained(
            model_directory.as_posix(),
            trust_remote_code=True,
            local_files_only=True,
        )
        model = AutoModel.from_pretrained(
            model_directory.as_posix(),
            trust_remote_code=True,
            local_files_only=True,
            use_safetensors=True,
            _attn_implementation=str(config["inference"]["attention_implementation"]),
            torch_dtype=torch.bfloat16,
        )
        model = model.eval().cuda()
        torch.cuda.synchronize()
        load_seconds = time.perf_counter() - load_started

        inference_started = time.perf_counter()
        internal_output = temporary / "model-internal"
        raw_output = model.infer(
            tokenizer,
            prompt=str(config["inference"]["prompt"]),
            image_file=input_path.as_posix(),
            output_path=internal_output.as_posix(),
            base_size=int(config["inference"]["base_size"]),
            image_size=int(config["inference"]["image_size"]),
            crop_mode=bool(config["inference"]["crop_mode"]),
            save_results=False,
            eval_mode=True,
        )
        torch.cuda.synchronize()
        inference_seconds = time.perf_counter() - inference_started
        if not isinstance(raw_output, str) or not raw_output.strip():
            raise RuntimeError("DeepSeek-OCR-2 returned no semantic OCR proposal")
        if internal_output.exists():
            shutil.rmtree(internal_output)

        references = parse_layout_references(raw_output)
        lines = raw_output.splitlines()
        result = {
            "schema_version": 1,
            "state": "SEMANTIC_OCR_PROPOSAL_COMPLETE",
            "dataset_role": args.dataset_role,
            "evidence_role": "SEMANTIC_AND_READING_ORDER_PROPOSAL_ONLY",
            "authority": {
                "mapping": False,
                "value": False,
                "period": False,
                "scope": False,
                "geometry": False,
                "confidence_promotion": False,
            },
            "raw_output": raw_output,
            "layout_references": references,
        }
        free_bytes, total_bytes = torch.cuda.mem_get_info()
        total_seconds = time.perf_counter() - total_started
        runtime_manifest_hash = _sha256(RUNTIME_MANIFEST)
        requirements_path = _project_path(
            str(config["runtime_overlay"]["requirements_path"]), "overlay lock"
        )
        manifest = {
            "schema_version": 1,
            "state": "OCR_COMPLETE",
            "dataset_role": args.dataset_role,
            "evidence_role": "SEMANTIC_AND_READING_ORDER_PROPOSAL_ONLY",
            "confidence_policy": "NO_AUTOMATIC_TRUTH_OR_SCHEMA_PROMOTION",
            "input": {
                "path": input_path.as_posix(),
                "size_bytes": input_path.stat().st_size,
                "sha256": _sha256(input_path),
            },
            "code": {
                **git,
                "runner_path": Path(__file__).relative_to(PROJECT_ROOT).as_posix(),
                "runner_sha256": _sha256(Path(__file__)),
            },
            "configuration": {
                "path": config_path.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": _sha256(config_path),
                "prompt": config["inference"]["prompt"],
                "base_size": config["inference"]["base_size"],
                "image_size": config["inference"]["image_size"],
                "crop_mode": config["inference"]["crop_mode"],
                "attention_implementation": config["inference"]["attention_implementation"],
                "network_policy": "PROCESS_SOCKET_CONNECT_AND_DNS_DENIED",
                "requirements_path": requirements_path.relative_to(PROJECT_ROOT).as_posix(),
                "requirements_sha256": _sha256(requirements_path),
            },
            "runtime": {
                "manifest_path": RUNTIME_MANIFEST.relative_to(PROJECT_ROOT).as_posix(),
                "manifest_sha256": runtime_manifest_hash,
                "packages": package_versions,
                "torch_cuda": torch.version.cuda,
                "gpu_name": torch.cuda.get_device_name(0),
                "compute_capability": capability,
                "bf16_supported": torch.cuda.is_bf16_supported(),
                "model": {
                    "repo_id": config["model"]["repo_id"],
                    "revision": config["model"]["revision"],
                    "directory": model_directory.as_posix(),
                    "artifacts": model_records,
                },
            },
            "metrics": {
                "load_seconds": load_seconds,
                "inference_seconds": inference_seconds,
                "wall_seconds": total_seconds,
                "peak_allocated_vram_bytes": torch.cuda.max_memory_allocated(),
                "peak_reserved_vram_bytes": torch.cuda.max_memory_reserved(),
                "free_vram_bytes_after_inference": free_bytes,
                "total_vram_bytes": total_bytes,
                "output_character_count": len(raw_output),
                "output_line_count": len(lines),
                "markdown_table_line_count": sum(line.strip().startswith("|") for line in lines),
                "layout_reference_count": len(references),
                "invalid_layout_reference_count": sum(
                    item["status"] != "PROPOSAL_ONLY" for item in references
                ),
            },
            "started_at": started_at.isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
        }
        _write_result(output_directory, temporary, result, manifest)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)

    print(
        json.dumps(
            {
                "status": "PASS",
                "output_directory": output_directory.as_posix(),
                "metrics": manifest["metrics"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
