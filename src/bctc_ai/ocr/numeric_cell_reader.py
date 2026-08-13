from __future__ import annotations

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
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from bctc_ai.core.hashing import sha256_file


class NumericCellReaderError(RuntimeError):
    pass


_CELL_ID = re.compile(r"page-\d{4}-row-\d{3}-axis-\d+")
_NUMERIC_CHARACTERS = re.compile(r"^[0-9.,()\-–—−\s]*$")


def _stable_bytes(path: Path, label: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise NumericCellReaderError(f"{label} is absent or not a regular file")
    try:
        before = path.stat()
        first = path.read_bytes()
        second = path.read_bytes()
        after = path.stat()
    except OSError as exc:
        raise NumericCellReaderError(f"cannot read {label}: {path}") from exc
    if (
        first != second
        or before.st_size != len(first)
        or after.st_size != len(first)
        or before.st_mtime_ns != after.st_mtime_ns
    ):
        raise NumericCellReaderError(f"{label} changed while read")
    return first


def _json_object(payload: bytes, label: str) -> dict[str, Any]:
    def closed_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise NumericCellReaderError(f"{label} contains duplicate JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(payload, object_pairs_hook=closed_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NumericCellReaderError(f"{label} is not valid UTF-8 JSON") from exc
    if type(value) is not dict:
        raise NumericCellReaderError(f"{label} must be a JSON object")
    return value


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
        config = tomllib.loads(_stable_bytes(resolved, "numeric reader config").decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
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
        payload = _stable_bytes(path, f"numeric reader model file {expected['path']}")
        if (
            len(payload) != int(expected["size_bytes"])
            or hashlib.sha256(payload).hexdigest() != expected["sha256"]
        ):
            raise NumericCellReaderError(f"numeric reader model file drifted: {path}")
        records.append(
            {
                "path": expected["path"],
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
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


def _load_reference_blind_numeric_request_snapshot(
    project_root: Path, registry_path: Path
) -> tuple[dict[str, Any], list[dict[str, Any]], Path]:
    project_root = project_root.resolve()
    resolved = _project_path(project_root, registry_path, "numeric crop registry")
    registry = _json_object(
        _stable_bytes(resolved, "numeric crop registry"), "numeric crop registry"
    )
    allowed_registries = {
        (1, "FIXED_GRID_NUMERIC_CELL_CROPS_V1", "E0029_PP_OCRV6_FIXED_GRID"),
        (2, "FIXED_GRID_NUMERIC_CELL_CROPS_V2", "E0033_PP_OCRV6_FIXED_GRID"),
        (
            3,
            "SEMANTIC_GRAPH_V2_VALUE_POSITION_CROPS_V1",
            "AUTHENTICATED_V3_LINE_GEOMETRY",
        ),
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
        or (
            registry.get("format_version") == 3
            and registry.get("reference_isolation")
            != {
                "accounting_or_family_roles_available_to_reader": False,
                "expected_or_primary_numeric_text_or_value_available_to_reader": False,
                "human_review_available_to_reader": False,
                "label_owner_or_branch_text_available_to_reader": False,
                "period_unit_or_scope_available_to_reader": False,
                "schema_label_or_report_norm_id_available_to_reader": False,
            }
        )
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
        unresolved_crop_path = resolved.parent / str(payload["crop_path"])
        if unresolved_crop_path.is_symlink():
            raise NumericCellReaderError(f"numeric crop path is unsafe: {cell_id}")
        crop_path = unresolved_crop_path.resolve()
        if not crop_path.is_relative_to(resolved.parent) or not crop_path.is_file():
            raise NumericCellReaderError(f"numeric crop path is unsafe: {cell_id}")
        crop_bytes = _stable_bytes(crop_path, f"numeric crop {cell_id}")
        crop_sha256 = hashlib.sha256(crop_bytes).hexdigest()
        if len(crop_bytes) != int(cell.get("crop_size_bytes", -1)) or crop_sha256 != cell.get(
            "crop_sha256"
        ):
            raise NumericCellReaderError(f"numeric crop drifted: {cell_id}")
        image = cv2.imdecode(np.frombuffer(crop_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None or image.ndim != 3:
            raise NumericCellReaderError(f"numeric crop is not a decodable color image: {cell_id}")
        samples.append(
            {
                "cell_id": cell_id,
                "crop_path": crop_path.as_posix(),
                "crop_sha256": crop_sha256,
                "input_image": image,
            }
        )
    return registry, samples, resolved


def _reader_safe_samples(snapshots: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "cell_id": sample["cell_id"],
            "crop_path": sample["crop_path"],
            "crop_sha256": sample["crop_sha256"],
        }
        for sample in snapshots
    ]


def load_reference_blind_numeric_request(
    project_root: Path, registry_path: Path
) -> tuple[dict[str, Any], list[dict[str, str]], Path]:
    """Validate the request while exposing only reader-safe sample metadata."""

    registry, snapshots, resolved = _load_reference_blind_numeric_request_snapshot(
        project_root, registry_path
    )
    return registry, _reader_safe_samples(snapshots), resolved


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
    registry, samples, resolved_registry = _load_reference_blind_numeric_request_snapshot(
        project_root, registry_path
    )
    reader_samples = _reader_safe_samples(samples)
    config_sha256 = hashlib.sha256(
        _stable_bytes(resolved_config, "numeric reader config final snapshot")
    ).hexdigest()
    registry_sha256 = hashlib.sha256(
        _stable_bytes(resolved_registry, "numeric crop registry final snapshot")
    ).hexdigest()
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
    verified_model_after_load = verify_numeric_reader_model(model_directory, config)
    if verified_model_after_load != model_record:
        raise NumericCellReaderError("numeric reader model changed during model load")
    if (
        hashlib.sha256(
            _stable_bytes(resolved_config, "numeric reader config before inference")
        ).hexdigest()
        != config_sha256
        or hashlib.sha256(
            _stable_bytes(resolved_registry, "numeric crop registry before inference")
        ).hexdigest()
        != registry_sha256
    ):
        raise NumericCellReaderError("numeric reader inputs changed before inference")
    predictions = model.predict(
        input=[sample["input_image"] for sample in samples],
        batch_size=batch_size,
    )
    records = []
    for sample, result in zip(reader_samples, predictions, strict=True):
        payload = result.json.get("res")
        if not isinstance(payload, dict):
            raise NumericCellReaderError("numeric reader returned no result payload")
        if payload.get("input_path") is not None:
            raise NumericCellReaderError("in-memory numeric reader returned a path identity")
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
                "cell_id": sample["cell_id"],
                "crop_path": sample["crop_path"],
                "crop_sha256": sample["crop_sha256"],
                "raw_prediction": raw_text,
                "reader_score": float(score),
                "proposal_status": classify_numeric_prediction(raw_text),
            }
        )
    if len(records) != len(samples):
        raise NumericCellReaderError("numeric reader changed the fixed crop denominator")
    if verify_numeric_reader_model(model_directory, config) != model_record:
        raise NumericCellReaderError("numeric reader model changed during inference")
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
                "sha256": config_sha256,
                "network_policy": "PROCESS_SOCKET_CONNECT_DENIED",
                "batch_size": batch_size,
                "cpu_threads": cpu_threads,
                "precision": "fp32",
                "device": "cpu",
            },
            "crop_registry": {
                "path": resolved_registry.relative_to(project_root).as_posix(),
                "sha256": registry_sha256,
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
