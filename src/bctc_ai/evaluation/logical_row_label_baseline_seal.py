from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.ocr.logical_row_label_reader_contract import (
    LogicalRowLabelReaderContractError,
    validate_logical_row_label_reader_request,
)


class LogicalRowLabelBaselineSealError(RuntimeError):
    """Raised when E-0036 baseline outputs cannot be sealed before review access."""


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
_VIETOCR_SAMPLE_KEYS = {
    "sample_id",
    "category",
    "crop_path",
    "crop_sha256",
    "processed_width",
    "processed_height",
    "raw_prediction",
    "mean_decoded_character_probability",
    "wall_seconds",
}
_DEEPSEEK_SAMPLE_KEYS = {
    "sample_id",
    "category",
    "crop_path",
    "crop_sha256",
    "crop_width",
    "crop_height",
    "raw_output",
    "status",
    "proposal_text",
    "nonempty_line_count",
    "reader_score",
    "reader_score_available",
    "inference_seconds",
}
_DEEPSEEK_STATUSES = {
    "PARSED_SEMANTIC_PROPOSAL_ONLY",
    "REJECT_EMPTY_OUTPUT",
    "REJECT_OUTPUT_CHARACTER_BUDGET_EXCEEDED",
    "REJECT_TOO_MANY_OUTPUT_LINES",
    "REJECT_DOCUMENT_OR_LAYOUT_SERIALIZATION",
    "REJECT_NON_TEXTUAL_OUTPUT",
}
_READER_IDENTITIES = {
    "vietocr": "VIETOCR_VGG_TRANSFORMER",
    "deepseek_ocr2": "DEEPSEEK_OCR_2",
}
_STATE = "REFERENCE_BLIND_LOGICAL_ROW_LABEL_INFERENCE_COMPLETE"


def _git(project_root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_is_ancestor(project_root: Path, ancestor: str, descendant: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=project_root,
            check=False,
            capture_output=True,
        ).returncode
        == 0
    )


def _resolve(project_root: Path, value: Path | str) -> Path:
    raw = Path(value)
    if raw.is_absolute() or ".." in raw.parts:
        raise LogicalRowLabelBaselineSealError(f"unsafe project-relative path: {value}")
    resolved = (project_root / raw).resolve()
    if not resolved.is_relative_to(project_root):
        raise LogicalRowLabelBaselineSealError(f"path escapes project root: {value}")
    return resolved


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LogicalRowLabelBaselineSealError(f"cannot load {label}: {path}") from error
    if not isinstance(payload, dict):
        raise LogicalRowLabelBaselineSealError(f"{label} must be an object")
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise LogicalRowLabelBaselineSealError(
            f"cannot load E-0036 experiment config: {path}"
        ) from error
    if not isinstance(payload, dict):
        raise LogicalRowLabelBaselineSealError("E-0036 experiment config must be an object")
    return payload


def _artifact(project_root: Path, path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise LogicalRowLabelBaselineSealError(f"artifact is absent: {path}")
    return {
        "path": path.relative_to(project_root).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def _is_nonnegative_number(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and value >= 0


def _validate_result_samples(
    reader_key: str,
    raw_samples: object,
    request_samples: list[dict[str, str]],
) -> tuple[int, int]:
    if not isinstance(raw_samples, list) or len(raw_samples) != len(request_samples):
        raise LogicalRowLabelBaselineSealError(f"{reader_key} result denominator drifted")
    parsed_count = 0
    rejected_count = 0
    for raw, request_sample in zip(raw_samples, request_samples, strict=True):
        expected_keys = _VIETOCR_SAMPLE_KEYS if reader_key == "vietocr" else _DEEPSEEK_SAMPLE_KEYS
        if not isinstance(raw, dict) or set(raw) != expected_keys:
            raise LogicalRowLabelBaselineSealError(f"{reader_key} output sample fields drifted")
        for key in ("sample_id", "category", "crop_path", "crop_sha256"):
            if raw[key] != request_sample[key]:
                raise LogicalRowLabelBaselineSealError(
                    f"{reader_key} output sample identity drifted: {request_sample['sample_id']}"
                )
        if reader_key == "vietocr":
            probability = raw["mean_decoded_character_probability"]
            if (
                isinstance(raw["processed_width"], bool)
                or not isinstance(raw["processed_width"], int)
                or raw["processed_width"] < 1
                or isinstance(raw["processed_height"], bool)
                or not isinstance(raw["processed_height"], int)
                or raw["processed_height"] < 1
                or not isinstance(raw["raw_prediction"], str)
                or (
                    probability is not None
                    and (not _is_nonnegative_number(probability) or float(probability) > 1.0)
                )
                or not _is_nonnegative_number(raw["wall_seconds"])
            ):
                raise LogicalRowLabelBaselineSealError("VietOCR output value drifted")
            parsed_count += 1
            continue
        status = raw["status"]
        if (
            status not in _DEEPSEEK_STATUSES
            or isinstance(raw["crop_width"], bool)
            or not isinstance(raw["crop_width"], int)
            or raw["crop_width"] < 1
            or isinstance(raw["crop_height"], bool)
            or not isinstance(raw["crop_height"], int)
            or raw["crop_height"] < 1
            or not isinstance(raw["raw_output"], str)
            or not isinstance(raw["proposal_text"], str)
            or isinstance(raw["nonempty_line_count"], bool)
            or not isinstance(raw["nonempty_line_count"], int)
            or raw["nonempty_line_count"] < 0
            or raw["reader_score"] is not None
            or raw["reader_score_available"] is not False
            or not _is_nonnegative_number(raw["inference_seconds"])
        ):
            raise LogicalRowLabelBaselineSealError("DeepSeek output value drifted")
        if status == "PARSED_SEMANTIC_PROPOSAL_ONLY":
            if not raw["proposal_text"]:
                raise LogicalRowLabelBaselineSealError("DeepSeek parsed proposal is empty")
            parsed_count += 1
        else:
            if raw["proposal_text"]:
                raise LogicalRowLabelBaselineSealError(
                    "DeepSeek rejected proposal retained semantic text"
                )
            rejected_count += 1
    return parsed_count, rejected_count


def _validate_reader_output(
    project_root: Path,
    *,
    reader_key: str,
    output_directory: Path,
    request_path: Path,
    request: dict[str, Any],
    request_samples: list[dict[str, str]],
    model_config_record: dict[str, Any],
) -> dict[str, Any]:
    if not output_directory.is_dir() or {path.name for path in output_directory.iterdir()} != {
        "ocr_result.json",
        "run_manifest.json",
    }:
        raise LogicalRowLabelBaselineSealError(
            f"{reader_key} output directory is absent or contains unexpected files"
        )
    result_path = output_directory / "ocr_result.json"
    manifest_path = output_directory / "run_manifest.json"
    result = _load_json(result_path, f"{reader_key} result")
    manifest = _load_json(manifest_path, f"{reader_key} manifest")
    expected_reader = _READER_IDENTITIES[reader_key]
    expected_evidence_role = (
        request["evidence_role"]
        if reader_key == "vietocr"
        else "VIETNAMESE_LOGICAL_ROW_LABEL_PROPOSAL_ONLY"
    )
    if (
        set(result) != _RESULT_KEYS
        or result.get("format_version") != 1
        or result.get("experiment_id") != "E-0036"
        or result.get("reader") != expected_reader
        or result.get("state") != _STATE
        or result.get("dataset_role") != "CALIBRATION"
        or result.get("evidence_role") != expected_evidence_role
        or result.get("reference_text_available_to_reader") is not False
        or result.get("sample_count") != 64
        or not isinstance(result.get("authority"), dict)
        or not result["authority"]
        or any(bool(value) for value in result["authority"].values())
    ):
        raise LogicalRowLabelBaselineSealError(f"{reader_key} result identity drifted")
    parsed_count, rejected_count = _validate_result_samples(
        reader_key, result["samples"], request_samples
    )
    result_artifact = _artifact(project_root, result_path)
    manifest_result = manifest.get("artifacts", {}).get("ocr_result")
    configuration = manifest.get("configuration")
    metrics = manifest.get("metrics")
    if (
        manifest.get("format_version") != 1
        or manifest.get("experiment_id") != "E-0036"
        or manifest.get("reader") != expected_reader
        or manifest.get("state") != _STATE
        or manifest.get("git_commit") != request["git_commit"]
        or manifest.get("git_dirty") is not False
        or manifest.get("request")
        != {
            "path": request_path.relative_to(project_root).as_posix(),
            "sha256": sha256_file(request_path),
        }
        or manifest.get("crop_manifest") != request["crop_manifest"]
        or not isinstance(configuration, dict)
        or configuration.get("path") != model_config_record.get("path")
        or configuration.get("sha256") != model_config_record.get("sha256")
        or not isinstance(manifest_result, dict)
        or manifest_result.get("path") != "ocr_result.json"
        or manifest_result.get("size_bytes") != result_artifact["size_bytes"]
        or manifest_result.get("sha256") != result_artifact["sha256"]
        or not isinstance(manifest.get("safety"), dict)
        or not manifest["safety"]
        or any(bool(value) for value in manifest["safety"].values())
        or not isinstance(metrics, dict)
        or metrics.get("sample_count") != 64
    ):
        raise LogicalRowLabelBaselineSealError(f"{reader_key} manifest drifted")
    if reader_key == "deepseek_ocr2" and (
        metrics.get("parsed_proposal_count") != parsed_count
        or metrics.get("structural_rejection_count") != rejected_count
        or parsed_count + rejected_count != 64
    ):
        raise LogicalRowLabelBaselineSealError("DeepSeek manifest metrics drifted")
    return {
        "reader": expected_reader,
        "output_directory": output_directory.relative_to(project_root).as_posix(),
        "result": result_artifact,
        "manifest": _artifact(project_root, manifest_path),
        "sample_count": 64,
        "parsed_proposal_count": parsed_count,
        "structural_rejection_count": rejected_count,
        "metrics": metrics,
        "reference_text_available_to_reader": False,
        "human_review_available_to_reader": False,
        "all_authority_flags": False,
    }


def seal_logical_row_label_baselines(
    project_root: Path,
    *,
    experiment_config_path: Path,
    request_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Hash-seal both E-0036 baseline outputs without reading review data."""

    project_root = project_root.resolve()
    config_path = _resolve(project_root, experiment_config_path)
    request_file = _resolve(project_root, request_path)
    destination = _resolve(project_root, output_path)
    if destination.exists():
        raise LogicalRowLabelBaselineSealError(f"refusing to overwrite seal: {destination}")
    if _git(project_root, "status", "--porcelain"):
        raise LogicalRowLabelBaselineSealError("formal E-0036 baseline seal requires clean Git")
    config = _load_yaml(config_path)
    if (
        config.get("version") != 1
        or config.get("experiment_id") != "E-0036"
        or config.get("dataset_role") != "CALIBRATION"
        or config.get("authority", {}).get("reviewed_rows_may_be_loaded_before_baseline_seals")
        is not False
        or config.get("request", {}).get("output_path")
        != request_file.relative_to(project_root).as_posix()
    ):
        raise LogicalRowLabelBaselineSealError("E-0036 experiment control drifted")
    request = _load_json(request_file, "E-0036 request")
    try:
        request_samples = validate_logical_row_label_reader_request(request)
    except LogicalRowLabelReaderContractError as error:
        raise LogicalRowLabelBaselineSealError(str(error)) from error
    current_commit = _git(project_root, "rev-parse", "HEAD")
    if not _git_is_ancestor(project_root, str(request["git_commit"]), current_commit):
        raise LogicalRowLabelBaselineSealError(
            "E-0036 inference commit is not an ancestor of the seal commit"
        )
    baseline_config = config.get("baseline_readers")
    if not isinstance(baseline_config, dict) or set(baseline_config) != {
        "vietocr",
        "deepseek_ocr2",
    }:
        raise LogicalRowLabelBaselineSealError("E-0036 baseline reader registry drifted")
    readers: dict[str, Any] = {}
    for reader_key in ("vietocr", "deepseek_ocr2"):
        record = baseline_config[reader_key]
        if not isinstance(record, dict) or not isinstance(record.get("model_config"), dict):
            raise LogicalRowLabelBaselineSealError(
                f"E-0036 {reader_key} reader registry is invalid"
            )
        output_directory = _resolve(project_root, str(record.get("output_directory", "")))
        readers[reader_key] = _validate_reader_output(
            project_root,
            reader_key=reader_key,
            output_directory=output_directory,
            request_path=request_file,
            request=request,
            request_samples=request_samples,
            model_config_record=record["model_config"],
        )

    payload: dict[str, Any] = {
        "format_version": 1,
        "experiment_id": "E-0036",
        "state": "BASELINE_OUTPUTS_HASH_SEALED_BEFORE_REVIEW_ACCESS",
        "dataset_role": "CALIBRATION",
        "captured_at": datetime.now(UTC).isoformat(),
        "seal_git_commit": current_commit,
        "seal_git_dirty": False,
        "inference_git_commit": request["git_commit"],
        "experiment_config": _artifact(project_root, config_path),
        "request": _artifact(project_root, request_file),
        "crop_manifest": dict(request["crop_manifest"]),
        "sample_count_per_reader": 64,
        "same_ordered_sample_ids": True,
        "readers": readers,
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
            "This artifact seals the unchanged E-0036 request and both complete "
            "reference-blind baseline outputs before any reviewed label or ReportNormId "
            "is loaded. It establishes artifact identity and structural completeness only; "
            "it makes no label, mapping, numeric, accounting, holdout or production claim."
        ),
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(destination, payload)
    return payload


__all__ = [
    "LogicalRowLabelBaselineSealError",
    "seal_logical_row_label_baselines",
]
