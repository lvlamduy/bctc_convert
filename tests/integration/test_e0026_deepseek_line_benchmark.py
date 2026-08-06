from __future__ import annotations

import json

import pytest

from bctc_ai.core.hashing import sha256_file


def test_e0026_deepseek_line_benchmark_is_hash_locked_and_fail_closed(project_root):
    artifact_path = (
        project_root
        / "docs/experiments/E-0026-deepseek-aspect-preserving-line.json"
    )
    assert sha256_file(artifact_path) == (
        "1753f382e141fbeb48e94cb1ef30a89ebd08cb2f1bb0836bdbf960e811eb33dd"
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert artifact["format_version"] == 1
    assert artifact["experiment_id"] == "E-0026"
    assert artifact["dataset_role"] == "LOGIC_DEVELOPMENT_AND_CALIBRATION"
    assert artifact["status"] == (
        "PASS_BOUNDED_DEEPSEEK_SEMANTIC_PROPOSAL_NO_PRODUCTION_PROMOTION"
    )
    assert artifact["code"] == {
        "git_commit": "3ea0fb9afc5de2dabc2a465e0e19c7019ffb37b4",
        "git_dirty": False,
    }
    assert artifact["configuration"] == {
        "path": "config/experiments/e0026-deepseek-aspect-preserving-line.yaml",
        "sha256": "d9a6312db6a583aa8677e90a1e9f7a9d5a9062c7ab77b524e8315860e473d292",
    }

    score = artifact["readers"]["deepseek_aspect_preserving"]["aggregate"]
    assert score["line_count"] == 37
    assert score["exact_line_count"] == 27
    assert score["title_line_count"] == 10
    assert score["title_exact_line_count"] == 5
    assert score["character_error_rate"] == pytest.approx(0.00964630225080386)
    assert score["word_error_rate"] == pytest.approx(0.038461538461538464)
    assert score["base_character_error_count"] == 1
    assert score["diacritic_only_error_count"] == 10
    assert score["insertion_count"] == 1
    assert score["deletion_count"] == 0
    assert score["empty_or_suffix_truncated_count"] == 0

    runtime = artifact["runtime"]
    assert runtime["e0025"]["structural_rejection_count"] == 7
    assert runtime["e0026"]["structural_rejection_count"] == 0
    assert runtime["e0026"]["parsed_proposal_count"] == 37
    assert runtime["e0026"]["total_wall_seconds"] == pytest.approx(
        23.16505541303195
    )
    assert runtime["e0026"]["peak_gpu_memory_allocated_mib"] == pytest.approx(
        7058.90283203125
    )
    assert runtime["e0026_maximum_raw_output_characters"] == 55

    comparisons = artifact["comparisons"]
    assert comparisons["character_gate_pass"] is True
    assert all(comparisons["deepseek_v2_gate"].values())
    assert comparisons["vietocr_outperforms_deepseek_on_this_calibration"] is True
    assert comparisons["vietocr_production_adoption_permitted"] is False
    assert comparisons["bank_and_period_disjoint_validation_completed"] is False

    documents = artifact["statement_discovery"]["documents"]
    assert [(item["document"], item["proposal_count"]) for item in documents] == [
        ("MBB_2025_CONSOLIDATED", 19),
        ("VCB_2025_CONSOLIDATED", 18),
    ]
    for item in documents:
        assert item["fusion_emitted_count"] == item["proposal_count"]
        assert item["fusion_rejected_count"] == 0
        assert item["skipped_sample_ids"] == []
        assert item["expected_or_reference_fields_read_during_fusion"] is False
        assert item["no_regression"] is True
        assert item["baseline"] == item["with_deepseek_semantics"]
        assert item["baseline"] == item["expected_calibration_contract"]
    assert artifact["statement_discovery"]["no_regression_pass"] is True
    assert artifact["statement_discovery"]["e0022_read_rerun_or_retuned"] is False

    acceptance = artifact["acceptance"]
    assert acceptance["deepseek_eligible_as_bounded_semantic_proposal"] is True
    assert acceptance["ppocrv6_geometry_authority"] is True
    assert acceptance["independent_numeric_reader_required"] is True
    for key in (
        "automatic_value_period_unit_sign_scope_mapping_truth",
        "excel_output_evaluated",
        "fine_tuning_workstream_started",
        "human_gold_or_production_accuracy",
        "schema_mapping_evaluated",
        "vietocr_production_component",
    ):
        assert acceptance[key] is False

    assert sha256_file(project_root / artifact["configuration"]["path"]) == (
        artifact["configuration"]["sha256"]
    )
    for relative_path, digest in artifact["algorithm_files_sha256"].items():
        assert sha256_file(project_root / relative_path) == digest
