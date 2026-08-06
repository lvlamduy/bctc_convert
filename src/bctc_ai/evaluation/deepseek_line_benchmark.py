from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.document_phase.multisignal_statement_discovery import (
    discover_statement_pages,
    load_multisignal_statement_config,
)
from bctc_ai.document_phase.statement_evidence import load_ocr_pages_from_batch
from bctc_ai.evaluation.line_recognition_metrics import compare_reader_scores, score_reader
from bctc_ai.evaluation.semantic_line_replay import build_frozen_semantic_proposals
from bctc_ai.ocr.semantic_line_fusion import (
    fuse_semantic_line_proposals,
    load_semantic_line_fusion_config,
)


class DeepSeekLineBenchmarkError(RuntimeError):
    pass


def _load_json(path: Path, name: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DeepSeekLineBenchmarkError(f"cannot load {name}: {path}") from exc
    if not isinstance(payload, dict):
        raise DeepSeekLineBenchmarkError(f"{name} must be an object")
    return payload


def _resolve(project_root: Path, value: str, name: str) -> Path:
    path = (project_root / value).resolve()
    if not path.is_relative_to(project_root):
        raise DeepSeekLineBenchmarkError(f"{name} escapes project root")
    return path


def _git(project_root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=project_root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _verify_run(directory: Path, *, experiment_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest_path = directory / "run_manifest.json"
    result_path = directory / "ocr_result.json"
    manifest = _load_json(manifest_path, f"{experiment_id} run manifest")
    result = _load_json(result_path, f"{experiment_id} OCR result")
    if (
        manifest.get("experiment_id") != experiment_id
        or result.get("experiment_id") != experiment_id
        or manifest.get("state")
        != "REFERENCE_BLIND_DEEPSEEK_BOUNDED_LINE_INFERENCE_COMPLETE"
        or result.get("state")
        != "REFERENCE_BLIND_DEEPSEEK_BOUNDED_LINE_INFERENCE_COMPLETE"
        or manifest.get("git_dirty") is not False
        or result.get("reference_text_available_to_reader") is not False
    ):
        raise DeepSeekLineBenchmarkError(f"{experiment_id} identity or reference policy drifted")
    artifacts = manifest.get("artifacts")
    record = artifacts.get("ocr_result") if isinstance(artifacts, dict) else None
    if not isinstance(record, dict) or (
        record.get("path") != "ocr_result.json"
        or result_path.stat().st_size != int(record.get("size_bytes", -1))
        or sha256_file(result_path) != record.get("sha256")
    ):
        raise DeepSeekLineBenchmarkError(f"{experiment_id} result artifact drifted")
    return manifest, result


def statement_result_summary(result: dict[str, Any]) -> dict[str, Any]:
    block = result.get("block") if isinstance(result.get("block"), dict) else {}
    cash = result.get("cash_flow") if isinstance(result.get("cash_flow"), dict) else {}
    return {
        "status": result.get("status"),
        "mapping_eligible_pages_by_statement_type": block.get(
            "mapping_eligible_pages_by_statement_type"
        ),
        "off_balance_excluded_pages": block.get("off_balance_excluded_pages"),
        "notes_boundary_page": block.get("notes_boundary_page"),
        "runner_up_margin": result.get("runner_up_margin"),
        "cash_flow_method": cash.get("method"),
    }


def semantic_reader_gate(
    baseline: dict[str, Any],
    challenger: dict[str, Any],
    *,
    structural_rejection_count: int,
    maximum_raw_output_characters: int,
    maximum_allowed_characters: int,
) -> dict[str, bool]:
    before = baseline["aggregate"]
    after = challenger["aggregate"]
    return {
        "lower_cer_than_ppocrv6": (
            after["character_error_rate"] < before["character_error_rate"]
        ),
        "no_title_exactness_regression_vs_ppocrv6": (
            after["title_exact_line_count"] >= before["title_exact_line_count"]
        ),
        "zero_structural_rejections": structural_rejection_count == 0,
        "zero_empty_or_suffix_truncated_predictions": (
            after["empty_or_suffix_truncated_count"] == 0
        ),
        "maximum_raw_output_characters_within_bound": (
            maximum_raw_output_characters <= maximum_allowed_characters
        ),
    }


def _score_deepseek(
    crop_manifest: dict[str, Any],
    inference: dict[str, Any],
    *,
    title_categories: set[str],
) -> dict[str, Any]:
    crops = crop_manifest.get("samples")
    predictions = inference.get("samples")
    if not isinstance(crops, list) or not isinstance(predictions, list):
        raise DeepSeekLineBenchmarkError("line benchmark samples are absent")
    by_id = {str(item.get("sample_id")): item for item in predictions if isinstance(item, dict)}
    if len(by_id) != len(predictions) or len(crops) != len(predictions):
        raise DeepSeekLineBenchmarkError("line benchmark sample denominator/identity drifted")
    records = []
    for crop in crops:
        if not isinstance(crop, dict):
            raise DeepSeekLineBenchmarkError("line crop record is invalid")
        sample_id = str(crop.get("sample_id", ""))
        prediction = by_id.get(sample_id)
        if not isinstance(prediction, dict):
            raise DeepSeekLineBenchmarkError("line prediction is missing")
        records.append(
            {
                "sample_id": sample_id,
                "document": str(crop.get("document", "")),
                "category": str(crop.get("category", "")),
                "reference": str(crop.get("expected_text", "")),
                "prediction": str(prediction.get("proposal_text", "")),
            }
        )
    return score_reader(
        records,
        title_categories=title_categories,
        minimum_missing_characters=2,
        minimum_missing_fraction=0.1,
    )


def capture_deepseek_line_benchmark(
    project_root: Path,
    *,
    experiment_config_path: Path,
    e0025_directory: Path,
    e0026_directory: Path,
    e0013_artifact_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise DeepSeekLineBenchmarkError("formal DeepSeek benchmark requires clean Git code")
    config_path = _resolve(project_root, experiment_config_path.as_posix(), "experiment config")
    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise DeepSeekLineBenchmarkError("cannot load E-0026 experiment config") from exc
    if not isinstance(config, dict) or (
        config.get("version") != 1
        or config.get("experiment_id") != "E-0026"
        or config.get("dataset_role") != "LOGIC_DEVELOPMENT_AND_CALIBRATION"
    ):
        raise DeepSeekLineBenchmarkError("E-0026 experiment identity drifted")
    frozen = config.get("frozen_inputs")
    if not isinstance(frozen, dict):
        raise DeepSeekLineBenchmarkError("E-0026 frozen inputs are absent")
    verified_inputs = {}
    for name, record in frozen.items():
        if not isinstance(record, dict):
            raise DeepSeekLineBenchmarkError("E-0026 frozen input record is invalid")
        path = _resolve(project_root, str(record.get("path", "")), name)
        if not path.is_file() or sha256_file(path) != record.get("sha256"):
            raise DeepSeekLineBenchmarkError(f"E-0026 frozen input drifted: {name}")
        verified_inputs[name] = {"path": path, "sha256": sha256_file(path)}

    e0025_root = _resolve(project_root, e0025_directory.as_posix(), "E-0025 directory")
    e0026_root = _resolve(project_root, e0026_directory.as_posix(), "E-0026 directory")
    e0025_manifest, e0025_result = _verify_run(e0025_root, experiment_id="E-0025")
    e0026_manifest, e0026_result = _verify_run(e0026_root, experiment_id="E-0026")
    diagnosis = config["failed_direct_resize_diagnosis"]
    if (
        sha256_file(e0025_root / "ocr_result.json") != diagnosis["result_sha256"]
        or sha256_file(e0025_root / "run_manifest.json") != diagnosis["run_manifest_sha256"]
        or e0025_manifest.get("git_commit") != diagnosis["inference_commit"]
    ):
        raise DeepSeekLineBenchmarkError("E-0025 failure diagnosis identity drifted")
    candidate = config["candidate"]
    if e0026_manifest.get("configuration", {}).get("sha256") != candidate["config_sha256"]:
        raise DeepSeekLineBenchmarkError("E-0026 candidate config identity drifted")

    crop_manifest = _load_json(verified_inputs["crop_manifest"]["path"], "crop manifest")
    e0024 = _load_json(verified_inputs["e0024_evaluation"]["path"], "E-0024 result")
    title_categories = set(config["evaluation_policy"]["title_categories"])
    e0025_score = _score_deepseek(
        crop_manifest, e0025_result, title_categories=title_categories
    )
    e0026_score = _score_deepseek(
        crop_manifest, e0026_result, title_categories=title_categories
    )
    baseline = e0024["baseline"]
    vietocr = e0024["challenger"]
    e0026_raw_lengths = [len(str(item.get("raw_output", ""))) for item in e0026_result["samples"]]
    gate = semantic_reader_gate(
        baseline,
        e0026_score,
        structural_rejection_count=int(
            e0026_manifest["metrics"]["structural_rejection_count"]
        ),
        maximum_raw_output_characters=max(e0026_raw_lengths),
        maximum_allowed_characters=int(
            config["evaluation_policy"]["semantic_reader_gate"][
                "maximum_raw_output_characters_at_most"
            ]
        ),
    )

    e0013_path = _resolve(project_root, e0013_artifact_path.as_posix(), "E-0013 artifact")
    e0013 = _load_json(e0013_path, "E-0013 artifact")
    fusion_config_path = project_root / "config/ocr/semantic-line-fusion-v1.yaml"
    locator_config_path = project_root / "config/document_phase/statement-discovery-v3.yaml"
    fusion_config = load_semantic_line_fusion_config(fusion_config_path)
    locator_config = load_multisignal_statement_config(locator_config_path)
    downstream = []
    for document in e0013.get("documents", []):
        if not isinstance(document, dict):
            raise DeepSeekLineBenchmarkError("E-0013 document record is invalid")
        key = str(document.get("key", ""))
        batch_record = document.get("ocr_batch")
        if not isinstance(batch_record, dict):
            raise DeepSeekLineBenchmarkError("E-0013 batch identity is absent")
        batch_root = _resolve(project_root, str(batch_record.get("path", "")), key)
        _, geometry_pages = load_ocr_pages_from_batch(batch_root, project_root=project_root)
        built = build_frozen_semantic_proposals(
            crop_manifest=crop_manifest,
            inference_result=e0026_result,
            geometry_pages=geometry_pages,
            document=key,
            reader="DEEPSEEK_OCR_2",
        )
        fused = fuse_semantic_line_proposals(geometry_pages, built.proposals, fusion_config)
        baseline_result = discover_statement_pages(geometry_pages, locator_config)
        semantic_result = discover_statement_pages(
            geometry_pages, locator_config, semantic_pages=fused.semantic_pages
        )
        baseline_summary = statement_result_summary(baseline_result)
        semantic_summary = statement_result_summary(semantic_result)
        expected_result = document.get("result")
        expected_summary = {
            "status": "ACCEPTED_MULTI_SIGNAL_STATEMENT_BLOCK",
            "mapping_eligible_pages_by_statement_type": expected_result.get(
                "mapping_eligible_pages_by_statement_type"
            ),
            "off_balance_excluded_pages": expected_result.get("off_balance_excluded_pages"),
            "notes_boundary_page": expected_result.get("notes_boundary_page"),
            "runner_up_margin": 8.5,
            "cash_flow_method": expected_result.get("cash_flow", {}).get("pdf_method"),
        }
        downstream.append(
            {
                "document": key,
                "proposal_count": len(built.proposals),
                "skipped_sample_ids": list(built.skipped_sample_ids),
                "fusion_emitted_count": fused.emitted_count,
                "fusion_rejected_count": fused.rejected_count,
                "expected_or_reference_fields_read_during_fusion": (
                    built.expected_or_reference_fields_read
                ),
                "baseline": baseline_summary,
                "with_deepseek_semantics": semantic_summary,
                "expected_calibration_contract": expected_summary,
                "no_regression": (
                    baseline_summary == semantic_summary == expected_summary
                ),
            }
        )
    downstream_pass = bool(downstream) and all(item["no_regression"] for item in downstream)
    character_gate_pass = all(gate.values())
    status = (
        "PASS_BOUNDED_DEEPSEEK_SEMANTIC_PROPOSAL_NO_PRODUCTION_PROMOTION"
        if character_gate_pass and downstream_pass
        else "REJECT_DEEPSEEK_SEMANTIC_CONFIGURATION"
    )
    payload = {
        "format_version": 1,
        "experiment_id": "E-0026",
        "status": status,
        "dataset_role": config["dataset_role"],
        "selection_policy": config["selection_policy"],
        "code": {
            "git_commit": _git(project_root, "rev-parse", "HEAD"),
            "git_dirty": False,
        },
        "configuration": {
            "path": config_path.relative_to(project_root).as_posix(),
            "sha256": sha256_file(config_path),
        },
        "inputs": {
            name: {
                "path": record["path"].relative_to(project_root).as_posix(),
                "sha256": record["sha256"],
            }
            for name, record in verified_inputs.items()
        }
        | {
            "e0025_result_sha256": sha256_file(e0025_root / "ocr_result.json"),
            "e0025_manifest_sha256": sha256_file(e0025_root / "run_manifest.json"),
            "e0026_result_sha256": sha256_file(e0026_root / "ocr_result.json"),
            "e0026_manifest_sha256": sha256_file(e0026_root / "run_manifest.json"),
            "e0013_artifact": {
                "path": e0013_path.relative_to(project_root).as_posix(),
                "sha256": sha256_file(e0013_path),
            },
        },
        "readers": {
            "ppocrv6_geometry_text_baseline": baseline,
            "deepseek_direct_resize_rejected": e0025_score,
            "deepseek_aspect_preserving": e0026_score,
            "vietocr_optional_challenger": vietocr,
        },
        "comparisons": {
            "ppocrv6_to_deepseek_v2": compare_reader_scores(baseline, e0026_score),
            "deepseek_v2_to_vietocr_challenger": compare_reader_scores(
                e0026_score, vietocr
            ),
            "deepseek_v2_gate": gate,
            "character_gate_pass": character_gate_pass,
            "vietocr_outperforms_deepseek_on_this_calibration": (
                vietocr["aggregate"]["character_error_rate"]
                < e0026_score["aggregate"]["character_error_rate"]
            ),
            "vietocr_production_adoption_permitted": False,
            "bank_and_period_disjoint_validation_completed": False,
        },
        "runtime": {
            "e0025": e0025_manifest["metrics"],
            "e0026": e0026_manifest["metrics"],
            "e0026_maximum_raw_output_characters": max(e0026_raw_lengths),
        },
        "statement_discovery": {
            "documents": downstream,
            "no_regression_pass": downstream_pass,
            "e0022_read_rerun_or_retuned": False,
        },
        "acceptance": {
            "deepseek_eligible_as_bounded_semantic_proposal": (
                character_gate_pass and downstream_pass
            ),
            "ppocrv6_geometry_authority": True,
            "independent_numeric_reader_required": True,
            "automatic_value_period_unit_sign_scope_mapping_truth": False,
            "schema_mapping_evaluated": False,
            "excel_output_evaluated": False,
            "human_gold_or_production_accuracy": False,
            "vietocr_production_component": False,
            "fine_tuning_workstream_started": False,
        },
        "algorithm_files_sha256": {
            path: sha256_file(project_root / path)
            for path in (
                "src/bctc_ai/ocr/deepseek_line_reader.py",
                "src/bctc_ai/ocr/semantic_line_fusion.py",
                "src/bctc_ai/evaluation/semantic_line_replay.py",
                "src/bctc_ai/evaluation/deepseek_line_benchmark.py",
                "src/bctc_ai/document_phase/multisignal_statement_discovery.py",
            )
        },
        "claim_boundary": config["claim_boundary"],
    }
    destination = _resolve(project_root, output_path.as_posix(), "E-0026 output")
    if destination.exists():
        raise DeepSeekLineBenchmarkError(f"refusing to overwrite E-0026 output: {destination}")
    atomic_write_json(destination, payload)
    return payload


__all__ = [
    "DeepSeekLineBenchmarkError",
    "capture_deepseek_line_benchmark",
    "semantic_reader_gate",
    "statement_result_summary",
]
