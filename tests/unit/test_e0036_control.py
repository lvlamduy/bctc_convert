from __future__ import annotations

import json
import tomllib

import yaml

from bctc_ai.core.hashing import sha256_file


def test_e0036_control_freezes_same_crops_and_delays_reference_access(project_root):
    path = project_root / "config/experiments/e0036-mbb-cdkt-semantic-label-readers.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert payload["experiment_id"] == "E-0036"
    assert payload["frozen_input"]["exact_sample_count"] == 64
    assert payload["request"]["reference_text_available_to_reader"] is False
    assert payload["request"]["decoder_visible_sample_fields"] == [
        "sample_id",
        "category",
        "crop_path",
        "crop_sha256",
    ]
    assert payload["evaluation_only_after_both_baseline_seals"]["exact_reviewed_row_count"] == 6
    assert (
        payload["evaluation_only_after_both_baseline_seals"][
            "reviewed_rows_are_not_reader_routing_inputs"
        ]
        is True
    )
    assert payload["conditional_qwen_challenger"]["invocation_state"] == (
        "AUTHORIZED_BY_SEALED_BASELINE_REVIEW_EVALUATION_NOT_YET_RUN"
    )
    assert payload["conditional_qwen_challenger"]["model_revision"] == (
        "8f0c09f227ae570e79617c6d9172b59df9c16081"
    )
    assert payload["conditional_qwen_challenger"]["required_same_request_sha256"] == (
        "ad4c1a9fecf9686249a9c4eea2a5b6a2a903fc4716536e5804c481facc217781"
    )
    assert payload["conditional_qwen_challenger"]["output_directory"] == (
        "output/calibration/e0036-mbb-cdkt-semantic-label-readers/qwen-reader"
    )
    assert payload["conditional_qwen_challenger"]["output_seal_path"] == (
        "docs/experiments/E-0036-qwen-output-seal.json"
    )
    assert payload["conditional_qwen_challenger"]["exact_output_files"] == [
        "ocr_result.json",
        "run_manifest.json",
    ]
    assert (
        payload["conditional_qwen_challenger"]["reviewed_evaluation_requires_qwen_output_seal"]
        is True
    )
    assert payload["baseline_output_sealing"]["exact_reader_count"] == 2
    assert payload["baseline_output_sealing"]["exact_sample_count_per_reader"] == 64
    assert payload["baseline_output_sealing"]["reference_or_human_review_loaded_by_sealer"] is False
    assert payload["authority"]["semantic_readers_propose_label_text_only"] is True
    assert payload["authority"]["semantic_reader_may_assign_report_norm_id"] is False
    assert payload["conditional_qwen_challenger"]["selected_pinned_runtime_artifact_bytes"] == (
        30_258_477_628
    )
    assert (
        payload["conditional_qwen_challenger"]["authorization"][
            "contains_review_labels_ids_values_or_periods"
        ]
        is False
    )
    assert payload["conditional_qwen_challenger"]["implementation"]["loader"] == (
        "GPTQModel.from_quantized"
    )
    assert payload["conditional_qwen_challenger"]["implementation"]["backend"] == ("gptq_triton")
    assert (
        payload["conditional_qwen_challenger"]["implementation"]["installed_overlay_tree_sha256"]
        == "d703e549fad8a65f86b137695f8a2bab3f6b77cbb39289220aa136cfe7feeeba"
    )
    assert (
        payload["conditional_qwen_challenger"]["implementation"][
            "exact_registered_model_file_set_required"
        ]
        is True
    )
    assert (
        payload["conditional_qwen_challenger"]["implementation"]["hf_transformers_gptq_loader_used"]
        is False
    )
    model_config = tomllib.loads(
        (
            project_root
            / payload["conditional_qwen_challenger"]["implementation"]["model_config"]["path"]
        ).read_text(encoding="utf-8")
    )
    assert (
        model_config["output"]["sealer"]
        == payload["conditional_qwen_challenger"]["implementation"]["output_sealer"]
    )
    assert (
        model_config["output"]["capture_script"]
        == payload["conditional_qwen_challenger"]["implementation"]["output_seal_capture_script"]
    )

    for record in (
        payload["request"]["algorithm"],
        payload["request"]["capture_script"],
        payload["request"]["reader_contract"],
        payload["baseline_output_sealing"]["algorithm"],
        payload["baseline_output_sealing"]["capture_script"],
        *(
            payload["evaluation_only_after_both_baseline_seals"][key]
            for key in (
                "baseline_output_seal",
                "numeric_row_linkage",
                "human_review_policy",
                "human_review_dataset",
                "target_schema",
                "ordered_mapping_policy",
                "scope_policy",
                "hierarchy_reference",
                "algorithm",
                "capture_script",
            )
        ),
        *payload["evaluation_only_after_both_baseline_seals"]["algorithm_dependencies"],
        *(
            record[key]
            for record in payload["baseline_readers"].values()
            for key in (
                "model_config",
                "reader_algorithm",
                "immutable_runtime_helper",
                "runner",
            )
        ),
        payload["conditional_qwen_challenger"]["authorization"],
        *(
            payload["conditional_qwen_challenger"]["implementation"][key]
            for key in (
                "model_config",
                "overlay_requirements",
                "downloader",
                "reader_algorithm",
                "runner",
                "hard_watchdog",
                "output_sealer",
                "output_seal_capture_script",
            )
        ),
    ):
        artifact = project_root / record["path"]
        assert artifact.stat().st_size == record["size_bytes"]
        assert sha256_file(artifact) == record["sha256"]


def test_e0036_qwen_output_is_sealed_and_s3_restore_verified(project_root):
    seal = json.loads(
        (project_root / "docs/experiments/E-0036-qwen-output-seal.json").read_text(encoding="utf-8")
    )
    snapshot = seal["s3_artifact_snapshot"]
    assert seal["state"] == "QWEN_OUTPUT_HASH_SEALED_BEFORE_REVIEW_ACCESS"
    assert seal["reader"]["sample_count"] == 64
    assert seal["reader"]["status_counts"] == {"REJECT_TOKEN_BUDGET_EXHAUSTED": 64}
    assert snapshot["file_count"] == 2
    assert snapshot["total_bytes"] == 232_798
    assert snapshot["restore_verified"] is True
    assert snapshot["hydrate_probe"] == {
        "existing_target_no_overwrite_refused": True,
        "logical_path": "output/calibration/e0036-mbb-cdkt-semantic-label-readers/qwen-reader",
        "restored_file_count": 2,
        "seal_hashes_match": True,
        "status": "PASS",
    }

    registry = [
        json.loads(line)
        for line in (project_root / "data/registered/s3_artifact_snapshot_registry.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]
    matches = [
        record
        for record in registry
        if record["artifact_snapshot_id"] == snapshot["artifact_snapshot_id"]
    ]
    assert len(matches) == 1
    assert matches[0]["manifest"] == snapshot["manifest"]
    assert matches[0]["run_record"] == snapshot["run_record"]
    assert matches[0]["restore_verified"] is True


def test_e0036_qwen_review_control_binds_only_sealed_inputs(project_root):
    control = yaml.safe_load(
        (project_root / "config/experiments/e0036-qwen-reviewed-evaluation.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert control["experiment_id"] == "E-0036"
    assert control["dataset_role"] == "CALIBRATION"
    assert control["state"] == "READY_FOR_QWEN_REVIEWED_EVALUATION"
    assert control["output"] == {"path": "docs/experiments/E-0036-qwen-reviewed-evaluation.json"}
    assert set(control["frozen_inputs"]) == {
        "qwen_output_seal",
        "baseline_reviewed_evaluation",
        "e0036_control",
    }
    assert set(control["implementation"]) == {"evaluator", "capture_script"}

    for record in (*control["frozen_inputs"].values(), *control["implementation"].values()):
        artifact = project_root / record["path"]
        assert artifact.stat().st_size == record["size_bytes"]
        assert sha256_file(artifact) == record["sha256"]


def test_e0036_qwen_reviewed_result_records_fail_closed_decision(project_root):
    result_path = project_root / "docs/experiments/E-0036-qwen-reviewed-evaluation.json"
    assert result_path.stat().st_size == 18_836
    assert sha256_file(result_path) == (
        "d0be37a35d43091f8bd9575893e713b603877f3ea517597a3c0f6a5481e0382d"
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))

    assert result["state"] == "QWEN_REVIEWED_EVALUATION_COMPLETE"
    assert result["decision"] == ("REJECT_CURRENT_PINNED_CONFIGURATION_NO_VALID_SEMANTIC_PROPOSALS")
    assert result["model_family_conclusion"] == "NOT_ESTABLISHED"
    assert result["all_row_proposal_coverage"] == {
        "mapping_eligible_sample_ids": [],
        "rejected_proposal_text_empty_count": 64,
        "rejected_sample_count": 64,
        "sample_count": 64,
        "status_counts": {"REJECT_TOKEN_BUDGET_EXHAUSTED": 64},
        "valid_semantic_proposal_count": 0,
        "valid_semantic_proposal_rate": 0.0,
    }

    mapping = result["mapping_disposition"]
    assert mapping["status"] == "NOT_RUN_NO_VALID_PROPOSALS"
    assert mapping["invoked"] is False
    assert mapping["mapping_input_sample_count"] == 0
    assert mapping["best_path"] is None
    assert mapping["runner_up_path"] is None
    assert mapping["reviewed_mapping_abstention_count"] == 6
    assert mapping["rejected_raw_output_used_for_mapping"] is False

    order = result["review_access_order"]
    assert order["qwen_output_seal_validated_before_baseline_review_open"] is True
    assert order["s3_restore_and_hydrate_validated_before_baseline_review_open"] is True
    assert order["baseline_reviewed_evaluation_is_only_review_source"] is True
    assert order["human_review_registry_or_dataset_loaded_directly"] is False
    assert order["mapping_not_invoked_because_no_valid_proposals"] is True

    storage = result["seal_and_s3_verification"]
    assert storage["qwen_output_hash_sealed_before_review"] is True
    assert storage["s3_restore_verified"] is True
    assert storage["s3_hydrate_probe_status"] == "PASS"
    assert storage["s3_hydrate_existing_target_no_overwrite_refused"] is True
    assert storage["same_ordered_sample_ids_as_request"] is True

    reviewed = result["reviewed_row_evaluation"]
    assert reviewed["valid_semantic_proposal_count"] == 0
    assert reviewed["rejected_sample_count"] == 6
    assert reviewed["accepted_only_label_metrics"] == {
        "metrics": None,
        "sample_count": 0,
        "status": "NOT_SCORABLE_NO_VALID_PROPOSALS",
    }
    assert reviewed["rejected_raw_output_used_for_scoring"] is False

    fixed = reviewed["fixed_denominator_failure_score"]["aggregate"]
    assert fixed["line_count"] == 6
    assert fixed["exact_line_count"] == 0
    assert fixed["character_error_rate"] == 1.0
    assert fixed["word_error_rate"] == 1.0
    assert fixed["empty_prediction_count"] == 6

    assert result["authority"]
    assert set(result["authority"].values()) == {False}

    degeneracy = result["runtime_metrics"]["generation_degeneracy"]
    assert degeneracy["sample_count"] == 64
    assert degeneracy["repeated_token_id"] == 163_749
    assert degeneracy["repeated_token_count_per_sample"] == 96
    assert degeneracy["repeated_token_total_count"] == 6_144
    assert degeneracy["unique_generated_token_sequence_count"] == 1
    assert degeneracy["unique_raw_generated_output_count"] == 1
    assert degeneracy["single_repeated_token_sequence_across_all_samples"] is True
    assert degeneracy["raw_output_used_for_label_scoring"] is False
    assert degeneracy["raw_output_used_for_mapping"] is False
