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
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bctc_ai.core.hashing import sha256_file


class NumericCellReaderError(RuntimeError):
    pass


_CELL_ID = re.compile(r"page-\d{4}-row-\d{3}-axis-\d+")
_NUMERIC_CHARACTERS = re.compile(r"^[0-9.,()\-–—−\s]*$")


def _git(project_root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=project_root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _project_path(project_root: Path, value: str | Path, name: str) -> Path:
    raw = Path(value)
    path = (project_root / raw).resolve() if not raw.is_absolute() else raw.resolve()
    if not path.is_relative_to(project_root):
        raise NumericCellReaderError(f"{name} escapes project root")
    return path


def load_numeric_reader_config(project_root: Path, path: Path) -> tuple[dict[str, Any], Path]:
    project_root = project_root.resolve()
    resolved = _project_path(project_root, path, "numeric reader config")
    try:
        config = tomllib.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise NumericCellReaderError(f"cannot load numeric reader config: {resolved}") from exc
    expected_forbidden = {
        "GEOMETRY",
        "PERIOD",
        "UNIT",
        "SCOPE",
        "LABEL",
        "REPORT_NORM_ID",
        "SCHEMA_MAPPING",
        "ACCOUNTING_REPAIR",
        "CONFIDENCE_PROMOTION",
    }
    if (
        config.get("version") != 1
        or config.get("policy") != "INDEPENDENT_FIXED_CELL_NUMERIC_PROPOSAL_V1"
        or config.get("runtime_python") != ".gpu-venv/bin/python"
        or config.get("device") != "cpu"
        or config.get("precision") != "fp32"
        or config.get("network_during_inference") is not False
        or config.get("authority") != "NUMERIC_CELL_PROPOSAL_ONLY"
        or set(config.get("forbidden_authority", ())) != expected_forbidden
    ):
        raise NumericCellReaderError("numeric reader identity or authority drifted")
    model = config.get("model")
    if (
        not isinstance(model, dict)
        or model.get("repo_id") != "PaddlePaddle/en_PP-OCRv5_mobile_rec"
        or model.get("revision") != "267c36e24c331595590fe7bd72bde2436fd286f2"
        or model.get("weights_file") != "inference.pdiparams"
        or model.get("weights_sha256")
        != "3ec8a97ed6cefe8568d3e2ee90bb193299b566a7661aa4fd52d224b96b59f66b"
        or model.get("weights_size_bytes") != 7_772_315
        or not isinstance(model.get("files"), list)
        or len(model["files"]) != 6
    ):
        raise NumericCellReaderError("numeric reader model identity drifted")
    return config, resolved


def verify_numeric_reader_model(model_directory: Path, config: dict[str, Any]) -> dict[str, Any]:
    model_directory = model_directory.resolve()
    model = config["model"]
    records = []
    for expected in model["files"]:
        path = model_directory / expected["path"]
        if (
            not path.is_file()
            or path.stat().st_size != int(expected["size_bytes"])
            or sha256_file(path) != expected["sha256"]
        ):
            raise NumericCellReaderError(f"numeric reader model file drifted: {path}")
        records.append(
            {
                "path": expected["path"],
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return {
        "repo_id": model["repo_id"],
        "revision": model["revision"],
        "directory": model_directory.as_posix(),
        "weights_size_bytes": model["weights_size_bytes"],
        "weights_sha256": model["weights_sha256"],
        "files": records,
    }


def load_reference_blind_numeric_request(
    project_root: Path, registry_path: Path
) -> tuple[dict[str, Any], list[dict[str, str]], Path]:
    project_root = project_root.resolve()
    resolved = _project_path(project_root, registry_path, "numeric crop registry")
    try:
        registry = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise NumericCellReaderError(f"cannot load numeric crop registry: {resolved}") from exc
    allowed_registries = {
        (1, "FIXED_GRID_NUMERIC_CELL_CROPS_V1", "E0029_PP_OCRV6_FIXED_GRID"),
        (2, "FIXED_GRID_NUMERIC_CELL_CROPS_V2", "E0033_PP_OCRV6_FIXED_GRID"),
    }
    if (
        not isinstance(registry, dict)
        or (
            registry.get("format_version"),
            registry.get("policy"),
            registry.get("geometry_authority"),
        )
        not in allowed_registries
        or registry.get("recognizer_input_fields") != ["crop_path"]
        or not isinstance(registry.get("cells"), list)
        or registry.get("metrics", {}).get("cell_count") != len(registry["cells"])
    ):
        raise NumericCellReaderError("numeric crop registry identity drifted")
    samples = []
    seen = set()
    for cell in registry["cells"]:
        if not isinstance(cell, dict):
            raise NumericCellReaderError("numeric crop cell must be an object")
        cell_id = cell.get("cell_id")
        payload = cell.get("recognizer_payload")
        if (
            not isinstance(cell_id, str)
            or _CELL_ID.fullmatch(cell_id) is None
            or cell_id in seen
            or not isinstance(payload, dict)
            or set(payload) != {"crop_path"}
            or payload.get("crop_path") != cell.get("crop_path")
        ):
            raise NumericCellReaderError("numeric crop cell identity or payload is unsafe")
        seen.add(cell_id)
        crop_path = (resolved.parent / str(payload["crop_path"])).resolve()
        if not crop_path.is_relative_to(resolved.parent) or (
            not crop_path.is_file()
            or crop_path.stat().st_size != int(cell.get("crop_size_bytes", -1))
            or sha256_file(crop_path) != cell.get("crop_sha256")
        ):
            raise NumericCellReaderError(f"numeric crop drifted: {cell_id}")
        samples.append(
            {
                "cell_id": cell_id,
                "crop_path": crop_path.as_posix(),
                "crop_sha256": sha256_file(crop_path),
            }
        )
    return registry, samples, resolved


def classify_numeric_prediction(raw_text: str) -> str:
    if not isinstance(raw_text, str):
        raise NumericCellReaderError("numeric prediction must be a string")
    if not raw_text.strip():
        return "EMPTY_PROPOSAL"
    if _NUMERIC_CHARACTERS.fullmatch(raw_text) is None:
        return "REJECT_NON_NUMERIC_CHARACTERS"
    return "NUMERIC_CHARACTERS_ONLY_PROPOSAL"


def _deny_network_connections() -> None:
    def audit_hook(event: str, _args: tuple[Any, ...]) -> None:
        if event == "socket.connect":
            raise NumericCellReaderError(
                "network access is forbidden during numeric-cell inference"
            )

    sys.addaudithook(audit_hook)


def run_numeric_cell_reader(
    project_root: Path,
    *,
    config_path: Path,
    registry_path: Path,
    model_cache: Path,
    output_directory: Path,
    batch_size: int = 16,
    cpu_threads: int = 8,
    allow_dirty: bool = False,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    if batch_size < 1 or cpu_threads < 1:
        raise NumericCellReaderError("numeric reader batch size and CPU threads must be positive")
    git_commit = _git(project_root, "rev-parse", "HEAD")
    git_dirty = bool(_git(project_root, "status", "--porcelain"))
    if git_dirty and not allow_dirty:
        raise NumericCellReaderError("refusing numeric-cell evidence from a dirty worktree")
    output = _project_path(project_root, output_directory, "numeric reader output")
    if output.exists():
        raise NumericCellReaderError(f"refusing to overwrite numeric reader output: {output}")
    config, resolved_config = load_numeric_reader_config(project_root, config_path)
    registry, samples, resolved_registry = load_reference_blind_numeric_request(
        project_root, registry_path
    )
    model_directory = (
        model_cache.resolve() / "official_models" / str(config["model"]["cache_directory"])
    )
    model_record = verify_numeric_reader_model(model_directory, config)

    started_at = datetime.now(UTC)
    started = time.perf_counter()
    _deny_network_connections()
    import paddle
    from paddleocr import TextRecognition

    model = TextRecognition(
        model_name="en_PP-OCRv5_mobile_rec",
        model_dir=model_directory.as_posix(),
        device="cpu",
        precision="fp32",
        enable_mkldnn=False,
        cpu_threads=cpu_threads,
    )
    predictions = model.predict(
        input=[sample["crop_path"] for sample in samples],
        batch_size=batch_size,
    )
    records = []
    for sample, result in zip(samples, predictions, strict=True):
        payload = result.json.get("res")
        if not isinstance(payload, dict):
            raise NumericCellReaderError("numeric reader returned no result payload")
        returned_path = Path(str(payload.get("input_path", ""))).resolve()
        if returned_path != Path(sample["crop_path"]):
            raise NumericCellReaderError("numeric reader changed crop ordering or identity")
        raw_text = payload.get("rec_text")
        score = payload.get("rec_score")
        if (
            not isinstance(raw_text, str)
            or isinstance(score, bool)
            or not isinstance(score, (int, float))
        ):
            raise NumericCellReaderError("numeric reader output types are invalid")
        records.append(
            {
                **sample,
                "raw_prediction": raw_text,
                "reader_score": float(score),
                "proposal_status": classify_numeric_prediction(raw_text),
            }
        )
    if len(records) != len(samples):
        raise NumericCellReaderError("numeric reader changed the fixed crop denominator")
    elapsed = time.perf_counter() - started
    counts = Counter(record["proposal_status"] for record in records)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        predictions_path = temporary / "predictions.json"
        predictions_path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        manifest = {
            "format_version": 1,
            "state": "NUMERIC_CELL_PROPOSALS_COMPLETE",
            "dataset_role": "CALIBRATION",
            "evidence_role": "INDEPENDENT_NUMERIC_CELL_PROPOSAL_ONLY",
            "confidence_policy": "NO_AUTOMATIC_TRUTH_MAPPING_OR_CONFIDENCE_PROMOTION",
            "code": {"commit": git_commit, "dirty": git_dirty},
            "configuration": {
                "path": resolved_config.relative_to(project_root).as_posix(),
                "sha256": sha256_file(resolved_config),
                "network_policy": "PROCESS_SOCKET_CONNECT_DENIED",
                "batch_size": batch_size,
                "cpu_threads": cpu_threads,
                "precision": "fp32",
                "device": "cpu",
            },
            "crop_registry": {
                "path": resolved_registry.relative_to(project_root).as_posix(),
                "sha256": sha256_file(resolved_registry),
                "cell_count": len(samples),
                "recognizer_input_fields": registry["recognizer_input_fields"],
            },
            "runtime": {
                "paddlepaddle": importlib.metadata.version("paddlepaddle"),
                "paddleocr": importlib.metadata.version("paddleocr"),
                "paddlex": importlib.metadata.version("paddlex"),
                "paddle_device": paddle.device.get_device(),
                "model": model_record,
            },
            "metrics": {
                "cell_count": len(records),
                "proposal_status_counts": dict(sorted(counts.items())),
                "wall_seconds": elapsed,
                "model_load_session_count": 1,
            },
            "artifacts": {
                "predictions": {
                    "path": "predictions.json",
                    "size_bytes": predictions_path.stat().st_size,
                    "sha256": sha256_file(predictions_path),
                }
            },
            "started_at": started_at.isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
        }
        manifest_path = temporary / "run_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return manifest
