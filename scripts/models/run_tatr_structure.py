from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bctc_ai.core.hashing import sha256_file
from bctc_ai.evaluation.tatr_structure import (
    build_query_predictions,
    resolve_checkpoint_compatibility,
    resolve_processor_size_compatibility,
    summarize_thresholds,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "config/models/tatr-v1.1-all.toml"


def _deny_network_connections() -> None:
    def audit_hook(event: str, _: tuple[Any, ...]) -> None:
        if event == "socket.connect":
            raise RuntimeError("network access is forbidden during sealed TATR inference")

    sys.addaudithook(audit_hook)


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


def _load_and_verify_config(path: Path) -> dict[str, Any]:
    config = tomllib.loads(path.read_text(encoding="utf-8"))
    if config.get("status") != "CALIBRATION_ONLY_STRUCTURE_PROPOSAL":
        raise RuntimeError("TATR runner requires calibration-only configuration")
    if any(bool(value) for value in config.get("safety", {}).values()):
        raise RuntimeError("TATR configuration grants forbidden authority")
    runtime_manifest = PROJECT_ROOT / str(config["runtime_manifest"])
    if sha256_file(runtime_manifest) != str(config["runtime_manifest_sha256"]):
        raise RuntimeError("TATR base runtime manifest hash drifted")
    return config


def _verify_model(model_cache: Path, config: dict[str, Any]) -> tuple[Path, list[dict[str, Any]]]:
    directory = model_cache / "official_models" / str(config["cache_directory"])
    records = []
    for key, artifact in sorted(config["artifacts"].items()):
        path = directory / str(artifact["path"])
        if not path.is_file():
            raise FileNotFoundError(f"missing pinned TATR artifact: {path}")
        size = path.stat().st_size
        digest = sha256_file(path)
        if size != int(artifact["size_bytes"]) or digest != str(artifact["sha256"]):
            raise RuntimeError(f"pinned TATR artifact integrity mismatch: {path}")
        records.append(
            {
                "key": key,
                "path": path.as_posix(),
                "size_bytes": size,
                "sha256": digest,
            }
        )
    return directory, records


def _write_artifacts(
    output_directory: Path, result: dict[str, Any], manifest: dict[str, Any]
) -> None:
    output_directory.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{output_directory.name}.", dir=output_directory.parent)
    )
    try:
        result_path = temporary / "structure_result.json"
        result_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        manifest["artifacts"] = {
            "structure_result": {
                "path": "structure_result.json",
                "size_bytes": result_path.stat().st_size,
                "sha256": sha256_file(result_path),
            }
        }
        (temporary / "run_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if output_directory.exists():
            raise FileExistsError(f"output appeared during inference: {output_directory}")
        os.replace(temporary, output_directory)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run hash-pinned TATR structure inference")
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
    model_cache = args.model_cache.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"input image does not exist: {input_path}")
    if output_directory.exists():
        raise FileExistsError(f"refusing to overwrite output: {output_directory}")
    git = _git_state()
    if git["dirty"] and not args.allow_dirty:
        raise RuntimeError("refusing TATR evidence inference from a dirty Git worktree")
    config = _load_and_verify_config(config_path)
    model_directory, model_artifacts = _verify_model(model_cache, config)

    _deny_network_connections()
    import torch
    from PIL import Image, ImageOps
    from transformers import (
        AutoImageProcessor,
        AutoModelForObjectDetection,
        TableTransformerConfig,
    )

    if not torch.cuda.is_available():
        raise RuntimeError("TATR evidence run requires the approved CUDA runtime")
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True)
    device = torch.device("cuda:0")
    processor = AutoImageProcessor.from_pretrained(
        model_directory.as_posix(), local_files_only=True
    )
    checkpoint_processor_size = dict(processor.size)
    expected_longest_edge = int(config["processor"]["longest_edge"])
    if checkpoint_processor_size.get("longest_edge") != expected_longest_edge:
        raise RuntimeError(
            f"checkpoint processor longest edge drifted: {checkpoint_processor_size} "
            f"!= {expected_longest_edge}"
        )
    transformers_version = importlib.metadata.version("transformers")
    processor_size, processor_compatibility_record = resolve_processor_size_compatibility(
        checkpoint_processor_size,
        config["processor_compatibility"],
        transformers_version=transformers_version,
    )
    processor.size = processor_size
    checkpoint_config_payload = json.loads(
        (model_directory / str(config["artifacts"]["config_json"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    resolved_config_payload, compatibility_record = resolve_checkpoint_compatibility(
        checkpoint_config_payload,
        config["compatibility"],
        transformers_version=transformers_version,
    )
    model_config = TableTransformerConfig.from_dict(resolved_config_payload)
    model = AutoModelForObjectDetection.from_pretrained(
        model_directory.as_posix(),
        config=model_config,
        local_files_only=True,
        use_safetensors=True,
    ).eval()
    model.to(device)

    with Image.open(input_path) as source_image:
        image = ImageOps.exif_transpose(source_image).convert("RGB")
    image_width, image_height = image.size
    inputs = processor(images=image, return_tensors="pt")
    pixel_values = inputs["pixel_values"].to(device)
    pixel_mask = inputs.get("pixel_mask")
    if pixel_mask is not None:
        pixel_mask = pixel_mask.to(device)

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats(device)
    torch.cuda.synchronize(device)
    started_at = datetime.now(UTC)
    started = time.perf_counter()
    with torch.inference_mode():
        outputs = model(pixel_values=pixel_values, pixel_mask=pixel_mask)
    torch.cuda.synchronize(device)
    wall_seconds = time.perf_counter() - started
    probabilities = outputs.logits[0].softmax(-1).detach().cpu().tolist()
    boxes = outputs.pred_boxes[0].detach().cpu().tolist()
    id2label = {int(key): str(value) for key, value in model.config.id2label.items()}
    predictions = build_query_predictions(
        boxes=boxes,
        probabilities=probabilities,
        id2label=id2label,
        image_width=image_width,
        image_height=image_height,
    )
    threshold_summary = summarize_thresholds(
        predictions, config["reporting"]["object_score_thresholds"]
    )
    result = {
        "schema_version": 1,
        "model_key": config["model_key"],
        "image": {"width": image_width, "height": image_height},
        "model_labels": id2label,
        "query_predictions": predictions,
        "threshold_summary": threshold_summary,
    }
    manifest = {
        "schema_version": 1,
        "state": "STRUCTURE_INFERENCE_COMPLETE",
        "dataset_role": args.dataset_role,
        "evidence_role": "NON_GENERATIVE_TABLE_STRUCTURE_PROPOSAL_ONLY",
        "confidence_policy": "NO_AUTOMATIC_TRUTH_SCHEMA_OR_VALUE_PROMOTION",
        "input": {
            "path": input_path.as_posix(),
            "size_bytes": input_path.stat().st_size,
            "sha256": sha256_file(input_path),
            "width": image_width,
            "height": image_height,
        },
        "code": git,
        "configuration": {
            "path": config_path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": sha256_file(config_path),
            "runner_path": Path(__file__).relative_to(PROJECT_ROOT).as_posix(),
            "runner_sha256": sha256_file(Path(__file__)),
            "checkpoint_processor_size": checkpoint_processor_size,
            "runtime_processor_size": processor_size,
            "processor_compatibility_applied": True,
            "experimental_processor_size_override": False,
            "implicit_orientation_or_unwarp": False,
            "network_policy": "PROCESS_SOCKET_CONNECT_DENIED",
            "checkpoint_compatibility": {
                "model_config": compatibility_record,
                "image_processor": processor_compatibility_record,
            },
        },
        "runtime": {
            "base_manifest_path": config["runtime_manifest"],
            "base_manifest_sha256": config["runtime_manifest_sha256"],
            "python": sys.version.split()[0],
            "torch": importlib.metadata.version("torch"),
            "torchvision": importlib.metadata.version("torchvision"),
            "transformers": transformers_version,
            "device": torch.cuda.get_device_name(device),
            "compute_capability": ".".join(map(str, torch.cuda.get_device_capability(device))),
            "model": {
                "repo_id": config["model"]["repo_id"],
                "revision": config["model"]["revision"],
                "license": config["license"],
                "artifacts": model_artifacts,
                "loaded_parameter_count": sum(
                    parameter.numel() for parameter in model.parameters()
                ),
                "loaded_state_element_count": sum(
                    tensor.numel() for tensor in model.state_dict().values()
                ),
            },
        },
        "metrics": {
            "wall_seconds": wall_seconds,
            "peak_gpu_allocated_mib": torch.cuda.max_memory_allocated(device) / (1024**2),
            "peak_gpu_reserved_mib": torch.cuda.max_memory_reserved(device) / (1024**2),
            "query_count": len(predictions),
            "processed_tensor_shape": list(pixel_values.shape),
            "threshold_summary": threshold_summary,
        },
        "safety": config["safety"],
        "started_at": started_at.isoformat(),
        "completed_at": datetime.now(UTC).isoformat(),
    }
    _write_artifacts(output_directory, result, manifest)
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
