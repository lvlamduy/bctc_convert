from __future__ import annotations

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
