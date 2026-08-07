from __future__ import annotations

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
        "NOT_ALLOWED_UNTIL_BASELINES_SEALED_AND_EVALUATED"
    )
    assert payload["conditional_qwen_challenger"]["model_revision"] == (
        "8f0c09f227ae570e79617c6d9172b59df9c16081"
    )
    assert payload["baseline_output_sealing"]["exact_reader_count"] == 2
    assert payload["baseline_output_sealing"]["exact_sample_count_per_reader"] == 64
    assert payload["baseline_output_sealing"]["reference_or_human_review_loaded_by_sealer"] is False
    assert payload["authority"]["semantic_readers_propose_label_text_only"] is True
    assert payload["authority"]["semantic_reader_may_assign_report_norm_id"] is False

    for record in (
        payload["request"]["algorithm"],
        payload["request"]["capture_script"],
        payload["request"]["reader_contract"],
        payload["baseline_output_sealing"]["algorithm"],
        payload["baseline_output_sealing"]["capture_script"],
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
    ):
        artifact = project_root / record["path"]
        assert artifact.stat().st_size == record["size_bytes"]
        assert sha256_file(artifact) == record["sha256"]
