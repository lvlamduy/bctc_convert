from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.evaluation.line_reader_request import prepare_line_reader_request
from bctc_ai.evaluation.line_recognition_metrics import (
    compare_reader_scores,
    score_reader,
)
from bctc_ai.ocr.vietocr_line_reader import validate_reference_blind_request


class LineRecognizerEvaluationError(RuntimeError):
    pass


def _git(project_root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _resolve(project_root: Path, path: Path | str) -> Path:
    value = (project_root / path).resolve()
    try:
        value.relative_to(project_root)
    except ValueError as exc:
        raise LineRecognizerEvaluationError(f"evaluation path escapes project root: {path}") from exc
    return value


def _load_json(path: Path, name: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise LineRecognizerEvaluationError(f"cannot read {name}: {path}") from exc
    if not isinstance(value, dict):
        raise LineRecognizerEvaluationError(f"{name} must be an object")
    return value


def _load_config(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, yaml.YAMLError) as exc:
        raise LineRecognizerEvaluationError(f"cannot read E-0024 config: {path}") from exc
    if not isinstance(value, dict) or (
        value.get("version") != 1
        or value.get("experiment_id") != "E-0024"
        or value.get("dataset_role") != "LOGIC_DEVELOPMENT_AND_CALIBRATION"
        or value.get("selection_policy")
        != "FROZEN_BEFORE_CHALLENGER_INFERENCE_SOURCE_VISIBLE_SINGLE_LINES"
    ):
        raise LineRecognizerEvaluationError("E-0024 config identity or role drifted")
    evaluation = value.get("evaluation_policy")
    if not isinstance(evaluation, dict) or (
        evaluation.get("unicode_normalization") != "NFC"
        or evaluation.get("whitespace_normalization") != "STRIP_AND_COLLAPSE_RUNS"
        or evaluation.get("title_categories") != ["TITLE", "OFF_BALANCE_TITLE"]
        or int(evaluation.get("suffix_truncation_minimum_missing_characters", 0)) < 1
        or not 0 < float(evaluation.get("suffix_truncation_minimum_missing_fraction", 0)) < 1
    ):
        raise LineRecognizerEvaluationError("E-0024 evaluation policy drifted")
    return value


def _verify_result_artifact(
    inference_directory: Path,
    manifest: dict[str, Any],
) -> tuple[Path, dict[str, Any]]:
    artifacts = manifest.get("artifacts")
    result_record = artifacts.get("ocr_result") if isinstance(artifacts, dict) else None
    if not isinstance(result_record, dict) or result_record.get("path") != "ocr_result.json":
        raise LineRecognizerEvaluationError("VietOCR result artifact identity is invalid")
    result_path = inference_directory / "ocr_result.json"
    if (
        not result_path.is_file()
        or result_path.stat().st_size != int(result_record.get("size_bytes", -1))
        or sha256_file(result_path) != result_record.get("sha256")
    ):
        raise LineRecognizerEvaluationError("VietOCR result is absent or hash-drifted")
    return result_path, _load_json(result_path, "VietOCR result")


def capture_line_recognizer_evaluation(
    project_root: Path,
    *,
    config_path: Path,
    crop_manifest_path: Path,
    inference_directory: Path,
    output_path: Path,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise LineRecognizerEvaluationError("formal E-0024 evaluation requires a clean worktree")
    config_file = _resolve(project_root, config_path)
    crop_manifest_file = _resolve(project_root, crop_manifest_path)
    inference_root = _resolve(project_root, inference_directory)
    destination = _resolve(project_root, output_path)
    if destination.exists():
        raise LineRecognizerEvaluationError(f"refusing to overwrite E-0024 artifact: {destination}")
    config = _load_config(config_file)
    crop_manifest = _load_json(crop_manifest_file, "E-0024 crop manifest")
    config_identity = crop_manifest.get("config")
    if not isinstance(config_identity, dict) or (
        config_identity.get("path") != config_file.relative_to(project_root).as_posix()
        or config_identity.get("sha256") != sha256_file(config_file)
        or crop_manifest.get("state") != "FROZEN_CROPS_BUILT_NO_CHALLENGER_INFERENCE"
        or crop_manifest.get("sample_count") != config.get("expected_sample_count")
    ):
        raise LineRecognizerEvaluationError("crop manifest is not bound to the current E-0024 config")

    inference_manifest_path = inference_root / "run_manifest.json"
    inference_manifest = _load_json(inference_manifest_path, "VietOCR run manifest")
    if (
        inference_manifest.get("experiment_id") != "E-0024"
        or inference_manifest.get("state") != "REFERENCE_BLIND_LINE_INFERENCE_COMPLETE"
        or inference_manifest.get("git_dirty") is not False
    ):
        raise LineRecognizerEvaluationError("VietOCR run manifest identity or state is invalid")
    request_identity = inference_manifest.get("request")
    if not isinstance(request_identity, dict):
        raise LineRecognizerEvaluationError("VietOCR run has no request identity")
    request_path = _resolve(project_root, str(request_identity.get("path", "")))
    if not request_path.is_file() or sha256_file(request_path) != request_identity.get("sha256"):
        raise LineRecognizerEvaluationError("VietOCR reference-blind request is hash-drifted")
    request_payload = _load_json(request_path, "VietOCR reference-blind request")
    request_samples = validate_reference_blind_request(request_payload)
    if request_payload["crop_manifest"] != {
        "path": crop_manifest_file.relative_to(project_root).as_posix(),
        "sha256": sha256_file(crop_manifest_file),
    }:
        raise LineRecognizerEvaluationError("VietOCR request references a different crop manifest")
    result_path, inference_result = _verify_result_artifact(inference_root, inference_manifest)
    if (
        inference_result.get("state") != "REFERENCE_BLIND_LINE_INFERENCE_COMPLETE"
        or inference_result.get("reference_text_available_to_reader") is not False
        or inference_result.get("sample_count") != len(request_samples)
    ):
        raise LineRecognizerEvaluationError("VietOCR result role or denominator is invalid")

    raw_crop_samples = crop_manifest.get("samples")
    raw_predictions = inference_result.get("samples")
    if not isinstance(raw_crop_samples, list) or not isinstance(raw_predictions, list):
        raise LineRecognizerEvaluationError("E-0024 sample evidence is missing")
    if not (len(raw_crop_samples) == len(raw_predictions) == len(request_samples)):
        raise LineRecognizerEvaluationError("E-0024 sample denominators disagree")
    prediction_by_id: dict[str, dict[str, Any]] = {}
    for record in raw_predictions:
        if not isinstance(record, dict) or not record.get("sample_id"):
            raise LineRecognizerEvaluationError("invalid VietOCR prediction record")
        sample_id = str(record["sample_id"])
        if sample_id in prediction_by_id:
            raise LineRecognizerEvaluationError("duplicate VietOCR prediction")
        prediction_by_id[sample_id] = record

    baseline_inputs = []
    challenger_inputs = []
    for sample, request_sample in zip(raw_crop_samples, request_samples, strict=True):
        if not isinstance(sample, dict):
            raise LineRecognizerEvaluationError("invalid crop sample record")
        sample_id = str(sample.get("sample_id", ""))
        if sample_id != request_sample["sample_id"] or sample_id not in prediction_by_id:
            raise LineRecognizerEvaluationError("sample order or identity drifted")
        prediction = prediction_by_id[sample_id]
        if (
            str(prediction.get("crop_path", "")) != str(sample.get("crop_path", ""))
            or str(prediction.get("crop_sha256", "")) != str(sample.get("crop_sha256", ""))
            or str(prediction.get("category", "")) != str(sample.get("category", ""))
        ):
            raise LineRecognizerEvaluationError(f"prediction crop identity drifted: {sample_id}")
        common = {
            "sample_id": sample_id,
            "document": str(sample.get("document", "")),
            "category": str(sample.get("category", "")),
            "reference": str(sample.get("expected_text", "")),
        }
        baseline_inputs.append(common | {"prediction": str(sample.get("ppocr_text", ""))})
        challenger_inputs.append(common | {"prediction": str(prediction.get("raw_prediction", ""))})

    policy = config["evaluation_policy"]
    score_arguments = {
        "title_categories": set(policy["title_categories"]),
        "minimum_missing_characters": int(
            policy["suffix_truncation_minimum_missing_characters"]
        ),
        "minimum_missing_fraction": float(
            policy["suffix_truncation_minimum_missing_fraction"]
        ),
    }
    baseline = score_reader(baseline_inputs, **score_arguments)
    challenger = score_reader(challenger_inputs, **score_arguments)
    comparison = compare_reader_scores(baseline, challenger)
    status = (
        "PASS_BOUNDED_SEMANTIC_PROPOSAL_READER_NO_AUTHORITY_PROMOTION"
        if comparison["adopt_as_semantic_proposal_reader"]
        else "REJECT_CHALLENGER_NO_PIPELINE_INTEGRATION"
    )
    payload: dict[str, Any] = {
        "format_version": 1,
        "experiment_id": "E-0024",
        "status": status,
        "dataset_role": config["dataset_role"],
        "selection_policy": config["selection_policy"],
        "evaluation_commit": _git(project_root, "rev-parse", "HEAD"),
        "config": {
            "path": config_file.relative_to(project_root).as_posix(),
            "sha256": sha256_file(config_file),
        },
        "crop_manifest": {
            "path": crop_manifest_file.relative_to(project_root).as_posix(),
            "sha256": sha256_file(crop_manifest_file),
        },
        "reference_blind_request": {
            "path": request_path.relative_to(project_root).as_posix(),
            "sha256": sha256_file(request_path),
        },
        "inference": {
            "directory": inference_root.relative_to(project_root).as_posix(),
            "manifest_path": inference_manifest_path.relative_to(project_root).as_posix(),
            "manifest_sha256": sha256_file(inference_manifest_path),
            "result_path": result_path.relative_to(project_root).as_posix(),
            "result_sha256": sha256_file(result_path),
            "runtime": inference_manifest.get("runtime"),
            "metrics": inference_manifest.get("metrics"),
        },
        "evaluation_policy": policy,
        "baseline": baseline,
        "challenger": challenger,
        "comparison": comparison,
        "safety": {
            "expected_text_available_during_inference": False,
            "numeric_authority": False,
            "period_authority": False,
            "unit_authority": False,
            "sign_authority": False,
            "geometry_authority": False,
            "mapping_authority": False,
            "automatic_truth_promotion": False,
        },
        "claim_boundary": config["claim_boundary"],
    }
    atomic_write_json(destination, payload)
    return payload


__all__ = [
    "LineRecognizerEvaluationError",
    "capture_line_recognizer_evaluation",
    "prepare_line_reader_request",
]
