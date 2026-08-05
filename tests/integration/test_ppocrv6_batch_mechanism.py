from __future__ import annotations

import json

from bctc_ai.core.hashing import sha256_file


def test_clean_ppocrv6_batch_equivalence_resume_and_seal(project_root):
    artifact_path = project_root / "docs/experiments/E-0012-ppocrv6-batch-mechanism.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert artifact["format_version"] == 1
    assert artifact["experiment_id"] == "E-0012"
    assert artifact["design"] == "CLEAN_COMMIT_BATCH_MECHANISM_REGRESSION"
    assert artifact["dataset_role"] == "CALIBRATION"
    assert artifact["status"] == "PASS_BATCH_EQUIVALENCE_RESUME_AND_SEAL"
    assert artifact["code"]["git_dirty"] is False
    assert "/workspace/" not in json.dumps(artifact)

    for relative_path, digest in artifact["algorithm_files_sha256"].items():
        assert sha256_file(project_root / relative_path) == digest
    for identity in (
        artifact["configuration"],
        artifact["runtime"]["manifest"],
        artifact["runtime"]["package_freeze"],
    ):
        assert sha256_file(project_root / identity["path"]) == identity["sha256"]

    assert artifact["batch"]["state"] == "OCR_COMPLETE"
    assert artifact["batch"]["metrics"]["completed_page_count"] == 1
    assert artifact["batch"]["metrics"]["line_count"] == 50
    assert artifact["batch"]["metrics"]["word_token_count"] == 380
    assert artifact["batch"]["metrics"]["model_load_session_count"] == 1
    assert artifact["equivalence"]["byte_identical"] is True
    assert (
        artifact["equivalence"]["batch_ocr_result_sha256"]
        == artifact["equivalence"]["baseline_ocr_result_sha256"]
    )
    assert artifact["resume"] == {
        "status": "PASS_ALREADY_COMPLETE",
        "completed_pages_before": 1,
        "completed_pages_after": 1,
        "model_load_sessions_before": 1,
        "model_load_sessions_after": 1,
        "model_reloaded": False,
    }

    sealing = artifact["sealing"]
    assert sealing["status"] == "GEOMETRY_OCR_COMPLETE"
    assert sealing["batch_runner_verified"] is True
    assert sealing["single_page_helper_verified"] is True
    assert sealing["automatic_truth_promotion"] is False
    assert sealing["automatic_schema_promotion"] is False
    assert sealing["automatic_pdf_confidence_promotion"] is False
    assert artifact["software_or_model_change"] is False
    assert artifact["historical_weak_reference"]["invoked"] is False
    assert artifact["report_norm_id"]["ids_proposed_or_added"] == 0
    assert artifact["ytd_derivation"]["invoked"] is False
    assert artifact["acceptance"]["new_accuracy_sample"] is False
    assert artifact["acceptance"]["production_accuracy_approved"] is False

    local_records = (
        artifact["source"],
        artifact["input_manifest"],
        artifact["upstream_role_b_seal"],
        artifact["source"]["render"],
        artifact["batch"]["page_manifest"],
        artifact["batch"]["ocr_result"],
        artifact["sealing"],
    )
    for record in local_records:
        local_path = project_root / record["path"]
        if local_path.is_file():
            assert sha256_file(local_path) == record["sha256"]

    batch_manifest = project_root / artifact["batch"]["path"] / "batch_manifest.json"
    if batch_manifest.is_file():
        assert sha256_file(batch_manifest) == artifact["batch"][
            "manifest_sha256_after_resume"
        ]
