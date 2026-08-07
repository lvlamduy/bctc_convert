from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from bctc_ai.core.hashing import sha256_file
from bctc_ai.evaluation import qwen35_reviewed_evaluation as reviewed_evaluation
from bctc_ai.evaluation.qwen35_reviewed_evaluation import (
    Qwen35ReviewedEvaluationError,
    capture_qwen35_reviewed_evaluation,
    evaluate_reviewed_proposals,
    extract_fixed_reviewed_rows,
    summarize_generation_degeneracy,
)

HEAD = "a" * 40
CONTROL_PATH = Path("config/experiments/e0036-qwen-reviewed-evaluation.yaml")
OUTPUT_PATH = Path("docs/experiments/E-0036-qwen-reviewed-evaluation.json")
SEAL_PATH = Path("docs/experiments/E-0036-qwen-output-seal.json")
BASELINE_PATH = Path("docs/experiments/E-0036-mbb-cdkt-reviewed-reader-evaluation.json")
E0036_CONTROL_PATH = Path("config/experiments/e0036-mbb-cdkt-semantic-label-readers.yaml")
REQUEST_PATH = Path("output/calibration/e0036/request.json")
QWEN_DIRECTORY = Path("output/calibration/e0036/qwen-reader")
EVALUATOR_PATH = Path("src/bctc_ai/evaluation/qwen35_reviewed_evaluation.py")
CAPTURE_PATH = Path("scripts/experiments/capture_e0036_qwen_reviewed_evaluation.py")

REVIEWED = [
    ("page-0003-row-018-label", 4317, "Góp vốn, đầu tư dài hạn"),
    ("page-0003-row-019-label", 4354, "Đầu tư vào công ty liên kết"),
    ("page-0003-row-034-label", 4357, "Các khoản lãi, phí phải thu"),
    ("page-0003-row-035-label", 4335, "Tài sản thuế TNDN hoãn lại"),
    ("page-0003-row-036-label", 4366, "Tài sản Có khác"),
    ("page-0004-row-009-label", 4336, "Thuế TNDN hoãn lại phải trả"),
]


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_yaml(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _record(root: Path, relative: Path) -> dict[str, object]:
    path = root / relative
    return {
        "path": relative.as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def _fake_git(_project_root: Path, *arguments: str) -> str:
    if arguments == ("status", "--porcelain"):
        return ""
    if arguments == ("rev-parse", "HEAD"):
        return HEAD
    raise AssertionError(arguments)


def _request_samples() -> list[dict[str, str]]:
    samples: list[dict[str, str]] = []
    for page, count in ((3, 39), (4, 25)):
        for row in range(count):
            sample_id = f"page-{page:04d}-row-{row:03d}-label"
            samples.append(
                {
                    "sample_id": sample_id,
                    "category": "LOGICAL_ROW_LABEL",
                    "crop_path": f"output/calibration/e0035/crops/{sample_id}.png",
                    "crop_sha256": f"{len(samples) + 1:064x}",
                }
            )
    return samples


def _rejected_result_sample(sample: dict[str, str]) -> dict[str, object]:
    raw = "teras" * 96
    return {
        **sample,
        "crop_width": 200,
        "crop_height": 70,
        "input_token_count": 123,
        "visual_token_count": 78,
        "generated_token_ids": [163749] * 96,
        "forbidden_generated_control_token_ids": [],
        "raw_generated_output": raw,
        "raw_output": raw,
        "nonempty_line_count": 1,
        "generated_token_count": 96,
        "terminated_by_eos": False,
        "status": "REJECT_TOKEN_BUDGET_EXHAUSTED",
        "proposal_text": "",
        "reader_score": None,
        "reader_score_available": False,
        "inference_seconds": 1.0,
    }


def _baseline_payload(request_record: dict[str, object]) -> dict[str, object]:
    readers: dict[str, object] = {}
    for reader_key, reader_name, exact_count in (
        ("vietocr", "VIETOCR_VGG_TRANSFORMER", 3),
        ("deepseek_ocr2", "DEEPSEEK_OCR_2", 1),
    ):
        readers[reader_key] = {
            "reader": reader_name,
            "labels": {
                "aggregate": {"exact_line_count": exact_count, "line_count": 6},
                "samples": [
                    {"sample_id": sample_id, "reference": reference}
                    for sample_id, _reviewed_id, reference in REVIEWED
                ],
            },
            "mapping": {
                "status": "AMBIGUOUS_MAPPING",
                "reviewed_best_path_exact_count": 6,
                "reviewed_automatically_accepted_exact_count": 0,
                "reviewed_mapping_abstention_count": 6,
            },
        }
    return {
        "format_version": 1,
        "experiment_id": "E-0036",
        "dataset_role": "CALIBRATION",
        "state": "BASELINES_REVIEWED_QWEN_TRIGGERED",
        "request": request_record,
        "conditional_qwen": {
            "triggered": True,
            "decision": "RUN_QWEN_SAME_REQUEST",
            "required_same_request_sha256": request_record["sha256"],
        },
        "human_review": {
            "document_key": "mbb-q1-2026-consolidated",
            "reviewed_row_count": 6,
            "row_bindings": [
                {"sample_id": sample_id, "reviewed_item_id": reviewed_id}
                for sample_id, reviewed_id, _reference in REVIEWED
            ],
        },
        "reader_evaluations": readers,
    }


def _build_fixture(tmp_path: Path) -> dict[str, object]:
    root = tmp_path / "project"
    for relative, text in (
        (EVALUATOR_PATH, "# frozen evaluator\n"),
        (CAPTURE_PATH, "# frozen capture\n"),
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    request_samples = _request_samples()
    request = {
        "format_version": 1,
        "experiment_id": "E-0036",
        "state": "READY_FOR_REFERENCE_BLIND_LOGICAL_ROW_LABEL_INFERENCE",
        "dataset_role": "CALIBRATION",
        "evidence_role": "INDEPENDENT_VIETNAMESE_LOGICAL_ROW_LABEL_PROPOSAL_ONLY",
        "git_commit": HEAD,
        "git_dirty": False,
        "crop_manifest": {
            "path": "output/calibration/e0035/crop_manifest.json",
            "sha256": "b" * 64,
        },
        "reference_text_available_to_reader": False,
        "sample_count": 64,
        "samples": request_samples,
    }
    _write_json(root / REQUEST_PATH, request)
    request_record = _record(root, REQUEST_PATH)

    result = {
        "format_version": 1,
        "experiment_id": "E-0036",
        "reader": "QWEN3_5_27B_GPTQ_INT4",
        "state": "REFERENCE_BLIND_LOGICAL_ROW_LABEL_INFERENCE_COMPLETE",
        "dataset_role": "CALIBRATION",
        "evidence_role": "INDEPENDENT_VIETNAMESE_LOGICAL_ROW_LABEL_PROPOSAL_ONLY",
        "reference_text_available_to_reader": False,
        "sample_count": 64,
        "samples": [_rejected_result_sample(sample) for sample in request_samples],
        "authority": {"label_truth": False, "mapping": False},
    }
    _write_json(root / QWEN_DIRECTORY / "ocr_result.json", result)
    metrics = {
        "model_load_seconds": 238.0,
        "sample_count": 64,
        "parsed_proposal_count": 0,
        "structural_rejection_count": 64,
        "total_wall_seconds": 15586.0,
    }
    _write_json(root / QWEN_DIRECTORY / "run_manifest.json", {"metrics": metrics})
    result_record = _record(root, QWEN_DIRECTORY / "ocr_result.json")
    manifest_record = _record(root, QWEN_DIRECTORY / "run_manifest.json")
    seal = {
        "format_version": 1,
        "experiment_id": "E-0036",
        "dataset_role": "CALIBRATION",
        "state": "QWEN_OUTPUT_HASH_SEALED_BEFORE_REVIEW_ACCESS",
        "seal_git_dirty": False,
        "exact_output_file_count": 2,
        "same_ordered_sample_ids_as_request": True,
        "reference_or_human_review_loaded_by_sealer": False,
        "evaluation_allowed_only_after_this_seal": True,
        "request": request_record,
        "reader": {
            "reader": "QWEN3_5_27B_GPTQ_INT4",
            "output_directory": QWEN_DIRECTORY.as_posix(),
            "result": result_record,
            "manifest": manifest_record,
            "sample_count": 64,
            "status_counts": {"REJECT_TOKEN_BUDGET_EXHAUSTED": 64},
            "metrics": metrics,
            "reference_text_available_to_reader": False,
            "human_review_available_to_reader": False,
            "all_authority_flags": False,
        },
        "s3_artifact_snapshot": {
            "artifact_snapshot_id": "fixture-snapshot",
            "file_count": 2,
            "uploaded_object_count": 2,
            "total_bytes": result_record["size_bytes"] + manifest_record["size_bytes"],
            "restore_verified": True,
            "manifest": {"key": "snapshots/manifest.json", "sha256": "c" * 64},
            "run_record": {"key": "runs/run.json", "sha256": "d" * 64},
            "hydrate_probe": {
                "status": "PASS",
                "restored_file_count": 2,
                "seal_hashes_match": True,
                "existing_target_no_overwrite_refused": True,
                "logical_path": QWEN_DIRECTORY.as_posix(),
            },
        },
    }
    _write_json(root / SEAL_PATH, seal)

    baseline = _baseline_payload(request_record)
    _write_json(root / BASELINE_PATH, baseline)
    e0036_control = {
        "version": 1,
        "experiment_id": "E-0036",
        "dataset_role": "CALIBRATION",
        "conditional_qwen_challenger": {
            "required_same_request_sha256": request_record["sha256"],
            "output_seal_path": SEAL_PATH.as_posix(),
            "reviewed_evaluation_requires_qwen_output_seal": True,
            "exact_output_files": ["ocr_result.json", "run_manifest.json"],
        },
    }
    _write_yaml(root / E0036_CONTROL_PATH, e0036_control)
    control = {
        "version": 1,
        "experiment_id": "E-0036",
        "dataset_role": "CALIBRATION",
        "state": "READY_FOR_QWEN_REVIEWED_EVALUATION",
        "frozen_inputs": {
            "qwen_output_seal": _record(root, SEAL_PATH),
            "baseline_reviewed_evaluation": _record(root, BASELINE_PATH),
            "e0036_control": _record(root, E0036_CONTROL_PATH),
        },
        "implementation": {
            "evaluator": _record(root, EVALUATOR_PATH),
            "capture_script": _record(root, CAPTURE_PATH),
        },
        "output": {"path": OUTPUT_PATH.as_posix()},
    }
    _write_yaml(root / CONTROL_PATH, control)
    return {
        "root": root,
        "control": control,
        "seal": seal,
        "baseline": baseline,
        "result": result,
    }


def test_rejected_outputs_score_empty_proposals_and_never_enter_mapping() -> None:
    samples = [
        {
            "sample_id": sample["sample_id"],
            "status": "REJECT_TOKEN_BUDGET_EXHAUSTED",
            "proposal_text": "",
            "raw_output": next(
                (
                    reference
                    for reviewed_sample_id, _reviewed_id, reference in REVIEWED
                    if reviewed_sample_id == sample["sample_id"]
                ),
                "diagnostic raw text",
            ),
        }
        for sample in _request_samples()
    ]
    reviewed_rows = [
        {
            "sample_id": sample_id,
            "reviewed_report_norm_id": reviewed_id,
            "reference": reference,
        }
        for sample_id, reviewed_id, reference in REVIEWED
    ]

    coverage, evaluation, mapping = evaluate_reviewed_proposals(
        samples,
        reviewed_rows,
        document_key="mbb-q1-2026-consolidated",
    )

    assert coverage["valid_semantic_proposal_count"] == 0
    assert coverage["mapping_eligible_sample_ids"] == []
    aggregate = evaluation["fixed_denominator_failure_score"]["aggregate"]
    assert aggregate["exact_line_count"] == 0
    assert aggregate["empty_prediction_count"] == 6
    assert aggregate["character_edit_distance"] == 145
    assert aggregate["word_edit_distance"] == 35
    assert evaluation["accepted_only_label_metrics"]["metrics"] is None
    assert mapping["status"] == "NOT_RUN_NO_VALID_PROPOSALS"
    assert mapping["invoked"] is False
    assert mapping["mapping_input_sample_count"] == 0
    assert mapping["rejected_sample_ids_passed_to_mapping"] == []
    assert mapping["reviewed_mapping_abstention_count"] == 6


def test_rejected_output_with_nonempty_proposal_is_invalid() -> None:
    samples = [
        {
            "sample_id": sample["sample_id"],
            "status": "REJECT_TOKEN_BUDGET_EXHAUSTED",
            "proposal_text": "",
        }
        for sample in _request_samples()
    ]
    samples[0]["proposal_text"] = "must not be consumed"
    reviewed_rows = [
        {
            "sample_id": sample_id,
            "reviewed_report_norm_id": reviewed_id,
            "reference": reference,
        }
        for sample_id, reviewed_id, reference in REVIEWED
    ]

    with pytest.raises(Qwen35ReviewedEvaluationError, match="must have an empty proposal"):
        evaluate_reviewed_proposals(
            samples,
            reviewed_rows,
            document_key="mbb-q1-2026-consolidated",
        )


def test_degeneracy_summary_records_repeated_token_without_exposing_raw_text() -> None:
    samples = [
        {
            "generated_token_ids": [163749] * 96,
            "raw_output": "teras" * 96,
            "raw_generated_output": "teras" * 96,
        }
        for _index in range(64)
    ]

    summary = summarize_generation_degeneracy(samples)

    assert summary["unique_generated_token_sequence_count"] == 1
    assert summary["unique_raw_output_count"] == 1
    assert summary["repeated_token_id"] == 163749
    assert summary["repeated_token_count_per_sample"] == 96
    assert summary["repeated_token_total_count"] == 6144
    assert summary["raw_output_used_for_label_scoring"] is False
    assert "teras" not in json.dumps(summary)


def test_fixed_review_extraction_rejects_reader_reference_disagreement() -> None:
    baseline = _baseline_payload(
        {"path": REQUEST_PATH.as_posix(), "size_bytes": 1, "sha256": "a" * 64}
    )
    baseline["reader_evaluations"]["vietocr"]["labels"]["samples"][0]["reference"] = "different"

    with pytest.raises(Qwen35ReviewedEvaluationError, match="disagree"):
        extract_fixed_reviewed_rows(baseline)


def test_capture_validates_seal_then_scores_fixed_reviewed_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_fixture(tmp_path)
    monkeypatch.setattr(reviewed_evaluation, "_git", _fake_git)

    result = capture_qwen35_reviewed_evaluation(fixture["root"])

    assert result["state"] == "QWEN_REVIEWED_EVALUATION_COMPLETE"
    assert result["decision"] == "REJECT_CURRENT_PINNED_CONFIGURATION_NO_VALID_SEMANTIC_PROPOSALS"
    assert result["seal_and_s3_verification"]["s3_hydrate_probe_status"] == "PASS"
    assert result["all_row_proposal_coverage"]["valid_semantic_proposal_count"] == 0
    assert result["reviewed_row_evaluation"]["valid_semantic_proposal_count"] == 0
    assert result["mapping_disposition"]["reviewed_mapping_abstention_count"] == 6
    assert result["runtime_metrics"]["generation_degeneracy"]["repeated_token_id"] == 163749
    assert result["model_family_conclusion"] == "NOT_ESTABLISHED"
    assert (fixture["root"] / OUTPUT_PATH).is_file()


def test_capture_rejects_incomplete_s3_hydrate_proof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_fixture(tmp_path)
    root = fixture["root"]
    seal = copy.deepcopy(fixture["seal"])
    seal["s3_artifact_snapshot"]["hydrate_probe"]["status"] = "FAIL"
    _write_json(root / SEAL_PATH, seal)
    control = fixture["control"]
    control["frozen_inputs"]["qwen_output_seal"] = _record(root, SEAL_PATH)
    _write_yaml(root / CONTROL_PATH, control)
    monkeypatch.setattr(reviewed_evaluation, "_git", _fake_git)

    with pytest.raises(Qwen35ReviewedEvaluationError, match="S3 restore/hydrate"):
        capture_qwen35_reviewed_evaluation(root)


def test_capture_refuses_to_overwrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_fixture(tmp_path)
    root = fixture["root"]
    output = root / OUTPUT_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("existing\n", encoding="utf-8")
    monkeypatch.setattr(reviewed_evaluation, "_git", _fake_git)

    with pytest.raises(Qwen35ReviewedEvaluationError, match="refusing to overwrite"):
        capture_qwen35_reviewed_evaluation(root)


def test_capture_rejects_symlinked_canonical_control(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_fixture(tmp_path)
    root = fixture["root"]
    canonical = root / CONTROL_PATH
    moved = root / "outside-control.yaml"
    canonical.replace(moved)
    canonical.symlink_to(moved)
    monkeypatch.setattr(reviewed_evaluation, "_git", _fake_git)

    with pytest.raises(Qwen35ReviewedEvaluationError, match="symlink"):
        capture_qwen35_reviewed_evaluation(root)


def test_capture_rechecks_clean_git_before_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_fixture(tmp_path)
    root = fixture["root"]
    status_call_count = 0

    def drifting_git(_project_root: Path, *arguments: str) -> str:
        nonlocal status_call_count
        if arguments == ("rev-parse", "HEAD"):
            return HEAD
        if arguments == ("status", "--porcelain"):
            status_call_count += 1
            return "" if status_call_count == 1 else " M tracked-file"
        raise AssertionError(arguments)

    monkeypatch.setattr(reviewed_evaluation, "_git", drifting_git)

    with pytest.raises(Qwen35ReviewedEvaluationError, match="Git code drifted"):
        capture_qwen35_reviewed_evaluation(root)
    assert not (root / OUTPUT_PATH).exists()
