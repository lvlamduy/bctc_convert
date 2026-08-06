from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.evaluation.numeric_cell_verification import (
    NumericCellVerificationError,
    verify_numeric_cell_proposals,
)


class NumericCellVerificationBenchmarkError(RuntimeError):
    pass


def _git(project_root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=project_root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _resolve(project_root: Path, value: str | Path, name: str) -> Path:
    raw = Path(value)
    path = (project_root / raw).resolve() if not raw.is_absolute() else raw.resolve()
    if not path.is_relative_to(project_root):
        raise NumericCellVerificationBenchmarkError(f"{name} escapes project root")
    return path


def _load_json(path: Path, name: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise NumericCellVerificationBenchmarkError(f"cannot load {name}: {path}") from exc


def _load_yaml(path: Path, name: str) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise NumericCellVerificationBenchmarkError(f"cannot load {name}: {path}") from exc
    if not isinstance(payload, dict):
        raise NumericCellVerificationBenchmarkError(f"{name} must be an object")
    return payload


def _artifact(project_root: Path, path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise NumericCellVerificationBenchmarkError(f"required artifact is absent: {path}")
    return {
        "path": path.relative_to(project_root).as_posix(),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _verify_record(
    project_root: Path, record: object, name: str
) -> tuple[Path, dict[str, Any]]:
    if not isinstance(record, dict):
        raise NumericCellVerificationBenchmarkError(f"invalid frozen record: {name}")
    path = _resolve(project_root, str(record.get("path", "")), name)
    if not path.is_file() or sha256_file(path) != record.get("sha256"):
        raise NumericCellVerificationBenchmarkError(f"frozen input drifted: {name}")
    return path, _artifact(project_root, path)


def _verify_source_artifacts(project_root: Path, registry: dict[str, Any]) -> list[dict]:
    records = []
    for page in registry.get("pages", []):
        for prefix in ("render", "ocr"):
            path = _resolve(project_root, page[f"{prefix}_path"], f"source {prefix}")
            if not path.is_file() or sha256_file(path) != page[f"{prefix}_sha256"]:
                raise NumericCellVerificationBenchmarkError(
                    f"numeric crop source {prefix} drifted"
                )
            records.append(_artifact(project_root, path))
    return records


def capture_e0031_numeric_cell_verification_benchmark(
    project_root: Path,
    *,
    experiment_config_path: Path,
    crop_registry_path: Path,
    reader_output_directory: Path,
    output_path: Path,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise NumericCellVerificationBenchmarkError(
            "formal E-0031 capture requires clean Git code"
        )
    output = _resolve(project_root, output_path, "output")
    if not output.is_relative_to((project_root / "docs" / "experiments").resolve()):
        raise NumericCellVerificationBenchmarkError("output must remain in docs/experiments")
    if output.exists():
        raise NumericCellVerificationBenchmarkError(f"refusing to overwrite capture: {output}")

    experiment_path = _resolve(project_root, experiment_config_path, "experiment config")
    experiment = _load_yaml(experiment_path, "E-0031 experiment config")
    if (
        experiment.get("version") != 1
        or experiment.get("experiment_id") != "E-0031"
        or experiment.get("dataset_role") != "CALIBRATION"
        or experiment.get("design")
        != "REFERENCE_BLIND_FIXED_GRID_INDEPENDENT_NUMERIC_VERIFICATION"
    ):
        raise NumericCellVerificationBenchmarkError("E-0031 experiment identity drifted")
    source = experiment.get("source")
    frozen = experiment.get("frozen_inputs")
    candidate = experiment.get("candidate")
    acceptance = experiment.get("acceptance_policy")
    if not all(isinstance(value, dict) for value in (source, frozen, candidate, acceptance)):
        raise NumericCellVerificationBenchmarkError("E-0031 controls are incomplete")

    verified_inputs: dict[str, dict[str, Any]] = {}
    verified_paths: dict[str, Path] = {}
    for name, record in frozen.items():
        verified_paths[name], verified_inputs[name] = _verify_record(
            project_root, record, name
        )
    for name in ("crop_policy", "model_config", "crop_algorithm", "reader_algorithm", "verification_algorithm"):
        verified_paths[name], verified_inputs[name] = _verify_record(
            project_root, candidate.get(name), name
        )

    row_contract = _load_json(verified_paths["e0029_row_contract"], "E-0029 contract")
    if (
        not isinstance(row_contract, dict)
        or row_contract.get("status") != "PASS_REFERENCE_BLIND_ROW_RECONSTRUCTION"
        or [record.get("page") for record in row_contract.get("after", [])]
        != source.get("target_pages")
    ):
        raise NumericCellVerificationBenchmarkError("E-0029 row contract drifted")

    registry_path = _resolve(project_root, crop_registry_path, "crop registry")
    registry = _load_json(registry_path, "numeric crop registry")
    if not isinstance(registry, dict):
        raise NumericCellVerificationBenchmarkError("numeric crop registry must be an object")
    if (
        registry.get("row_contract", {}).get("sha256")
        != frozen["e0029_row_contract"]["sha256"]
        or registry.get("crop_policy", {}).get("sha256")
        != candidate["crop_policy"]["sha256"]
        or [page.get("page") for page in registry.get("pages", [])]
        != source.get("target_pages")
    ):
        raise NumericCellVerificationBenchmarkError("numeric crop contract drifted")
    source_artifacts = _verify_source_artifacts(project_root, registry)

    reader_root = _resolve(project_root, reader_output_directory, "reader output")
    reader_manifest_path = reader_root / "run_manifest.json"
    reader_manifest = _load_json(reader_manifest_path, "numeric reader manifest")
    if not isinstance(reader_manifest, dict):
        raise NumericCellVerificationBenchmarkError("numeric reader manifest must be an object")
    prediction_record = reader_manifest.get("artifacts", {}).get("predictions")
    if not isinstance(prediction_record, dict):
        raise NumericCellVerificationBenchmarkError("numeric predictions record is absent")
    prediction_path = reader_root / str(prediction_record.get("path", ""))
    if (
        reader_manifest.get("state") != "NUMERIC_CELL_PROPOSALS_COMPLETE"
        or reader_manifest.get("code", {}).get("dirty") is not False
        or reader_manifest.get("crop_registry", {}).get("sha256") != sha256_file(registry_path)
        or reader_manifest.get("configuration", {}).get("sha256")
        != candidate["model_config"]["sha256"]
        or reader_manifest.get("runtime", {}).get("model", {}).get("repo_id")
        != candidate.get("model_repo_id")
        or reader_manifest.get("runtime", {}).get("model", {}).get("revision")
        != candidate.get("model_revision")
        or reader_manifest.get("runtime", {}).get("model", {}).get("weights_sha256")
        != candidate.get("model_weights_sha256")
        or not prediction_path.is_file()
        or prediction_path.stat().st_size != int(prediction_record.get("size_bytes", -1))
        or sha256_file(prediction_path) != prediction_record.get("sha256")
    ):
        raise NumericCellVerificationBenchmarkError("numeric reader evidence drifted")
    predictions = _load_json(prediction_path, "numeric predictions")
    if not isinstance(predictions, list):
        raise NumericCellVerificationBenchmarkError("numeric predictions must be a list")
    try:
        verification = verify_numeric_cell_proposals(registry, predictions)
    except NumericCellVerificationError as exc:
        raise NumericCellVerificationBenchmarkError(str(exc)) from exc

    metrics = verification["metrics"]
    expected_counts = acceptance["exact_primary_observation_counts"]
    gates = {
        "exact_page_set": [page["page"] for page in registry["pages"]]
        == acceptance["exact_page_set"],
        "exact_row_count": registry["metrics"]["row_count"]
        == int(acceptance["exact_row_count"]),
        "exact_cell_count": metrics["cell_count"] == int(acceptance["exact_cell_count"]),
        "exact_primary_observation_counts": metrics["primary_observation_counts"]
        == expected_counts,
        "zero_crop_clips": registry["metrics"]["crop_line_clip_count"] == 0
        and registry["metrics"]["visual_evidence_clip_count"] == 0,
        "one_model_load_session": reader_manifest["metrics"]["model_load_session_count"]
        == 1,
        "minimum_observed_exact_agreement_rate": metrics[
            "observed_exact_agreement_rate"
        ]
        >= float(acceptance["minimum_observed_exact_agreement_rate"]),
        "maximum_unresolved_observed_cells": metrics["unresolved_observed_cell_count"]
        <= int(acceptance["maximum_unresolved_observed_cells"]),
        "exact_verified_dash_count": metrics["verification_status_counts"].get(
            "VERIFIED_OBSERVED_DASH", 0
        )
        == int(acceptance["exact_verified_dash_count"]),
        "all_blank_cells_retained": metrics["blank_cell_count"]
        == int(expected_counts["BLANK"])
        and metrics["blank_to_zero_or_value_promotion_count"] == 0,
        "zero_automatic_overwrite": metrics["automatic_reader_overwrite_count"] == 0,
        "reader_score_not_used": metrics["reader_score_decision_use_count"] == 0,
        "off_balance_page_not_loaded": 5 not in [page["page"] for page in registry["pages"]],
    }
    isolation = {
        "human_review_loaded": False,
        "historical_or_mongodb_values_loaded": False,
        "template_labels_or_report_norm_ids_loaded": False,
        "row_labels_loaded_by_numeric_reader": False,
        "period_or_unit_loaded_by_numeric_reader": False,
        "numeric_reader_probability_used_for_acceptance": False,
        "blank_promoted_to_zero_or_value": False,
        "reader_disagreement_automatically_repaired": False,
        "e0022_evidence_loaded": False,
        "off_balance_page_5_loaded": False,
        "schema_mapping_invoked": False,
        "accounting_validation_invoked": False,
        "excel_export_invoked": False,
    }
    result = {
        "format_version": 1,
        "experiment_id": "E-0031",
        "dataset_role": "CALIBRATION",
        "capture_git_commit": _git(project_root, "rev-parse", "HEAD"),
        "capture_git_dirty": False,
        "experiment_config": _artifact(project_root, experiment_path),
        "verified_inputs": verified_inputs,
        "source_artifacts": source_artifacts,
        "crop_registry": _artifact(project_root, registry_path),
        "reader_manifest": _artifact(project_root, reader_manifest_path),
        "reader_predictions": _artifact(project_root, prediction_path),
        "before": {
            "status": "SINGLE_READER_NUMERIC_CELLS_NOT_INDEPENDENTLY_VERIFIED",
            "verified_observed_cell_count": 0,
        },
        "after": verification,
        "gates": gates,
        "reference_isolation": isolation,
        "development_note": experiment["development_note"],
        "claim_boundary": experiment["claim_boundary"],
        "status": (
            "PASS_REFERENCE_BLIND_INDEPENDENT_NUMERIC_VERIFICATION"
            if all(gates.values())
            else "FAIL_REFERENCE_BLIND_INDEPENDENT_NUMERIC_VERIFICATION"
        ),
    }
    atomic_write_json(output, result)
    return result
