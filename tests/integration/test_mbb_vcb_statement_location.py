from __future__ import annotations

import json

from bctc_ai.core.hashing import sha256_file


def test_clean_mbb_vcb_statement_location_calibration(project_root):
    artifact_path = project_root / "docs/experiments/E-0013-mbb-vcb-statement-location.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert artifact["format_version"] == 1
    assert artifact["experiment_id"] == "E-0013"
    assert artifact["design"] == "CLEAN_MULTI_INSTITUTION_COARSE_STATEMENT_LOCATION_CALIBRATION"
    assert artifact["dataset_role"] == "CALIBRATION"
    assert artifact["status"] == "PASS_ORDERED_STATEMENT_LOCATION_AND_SCOPE_EXCLUSION"
    assert artifact["code"] == {
        "git_commit": "b165c6001b914d1d2ab234903c45c91f557974ed",
        "git_dirty": False,
    }
    assert "/workspace/" not in json.dumps(artifact)

    for relative_path, digest in artifact["algorithm_files_sha256"].items():
        assert sha256_file(project_root / relative_path) == digest
    for identity in (
        artifact["configuration"],
        artifact["upstream_reader"]["ocr_configuration"],
        artifact["upstream_reader"]["runtime_manifest"],
        artifact["upstream_reader"]["package_freeze"],
    ):
        assert sha256_file(project_root / identity["path"]) == identity["sha256"]

    expected = {
        "MBB_2025_CONSOLIDATED": {
            "eligible": {"CDKT": [10, 11], "KQKD": [13], "LCTT": [14, 15]},
            "excluded": [12],
            "notes": 16,
            "anchors": [(14, 14), (14, 17)],
        },
        "VCB_2025_CONSOLIDATED": {
            "eligible": {"CDKT": [8, 9], "KQKD": [11, 12], "LCTT": [13, 14]},
            "excluded": [10],
            "notes": 15,
            "anchors": [(13, 20), (13, 25)],
        },
    }
    assert {document["key"] for document in artifact["documents"]} == set(expected)
    for document in artifact["documents"]:
        contract = expected[document["key"]]
        result = document["result"]
        assert result["mapping_eligible_pages_by_statement_type"] == contract["eligible"]
        assert result["off_balance_excluded_pages"] == contract["excluded"]
        assert result["notes_boundary_page"] == contract["notes"]
        assert result["interstitial_pages"] == []
        assert result["winner_runner_up_margin"] == 2.0
        assert not set(result["off_balance_excluded_pages"]) & {
            page
            for pages in result["mapping_eligible_pages_by_statement_type"].values()
            for page in pages
        }
        cash_flow = result["cash_flow"]
        assert cash_flow["pdf_method"] == "DIRECT"
        assert cash_flow["indirect_sequence_complete"] is False
        assert cash_flow["schema_branch_assignment_permitted"] is False
        assert [
            (record["page"], record["line_index"]) for record in cash_flow["ordered_anchors"]
        ] == contract["anchors"]

        source_path = project_root / document["source"]["path"]
        if source_path.is_file():
            assert sha256_file(source_path) == document["source"]["sha256"]
        preprocess_path = project_root / document["preprocess_manifest"]["path"]
        if preprocess_path.is_file():
            assert sha256_file(preprocess_path) == document["preprocess_manifest"]["sha256"]
        batch_manifest = project_root / document["ocr_batch"]["path"] / "batch_manifest.json"
        if batch_manifest.is_file():
            assert sha256_file(batch_manifest) == document["ocr_batch"]["manifest_sha256"]
        output_path = project_root / document["location_output"]["path"]
        if not output_path.is_file():
            continue
        assert sha256_file(output_path) == document["location_output"]["sha256"]
        output = json.loads(output_path.read_text(encoding="utf-8"))
        assert output["state"] == "STATEMENT_LOCATION_COMPLETE"
        assert output["code"] == {
            "commit": artifact["code"]["git_commit"],
            "dirty": False,
        }
        output_result = output["result"]
        assert output_result["errors"] == []
        assert output_result["runner_up_margin"] == result["winner_runner_up_margin"]
        assert (
            output_result["block"]["mapping_eligible_pages_by_statement_type"]
            == result["mapping_eligible_pages_by_statement_type"]
        )
        assert (
            output_result["block"]["off_balance_excluded_pages"]
            == result["off_balance_excluded_pages"]
        )
        assert output_result["cash_flow"]["method"] == cash_flow["pdf_method"]
        assert output_result["cash_flow"]["schema_branch_assignment_permitted"] is False

    checks = artifact["cross_document_checks"]
    assert checks["bank_name_or_page_rule_in_algorithm"] is False
    assert checks["unknown_interstitial_pages"] == 0
    assert checks["off_balance_pages_mapping_eligible"] == 0
    assert checks["scope_crossing_continuation_links"] == 0
    assert checks["cash_flow_schema_assignment_attempts"] == 0
    assert checks["historical_reference_invoked"] is False
    assert checks["arithmetic_value_generation_invoked"] is False
    assert checks["ytd_derivation_invoked"] is False
    assert artifact["software_or_model_change"] is False
    assert artifact["report_norm_id"]["ids_proposed_or_added"] == 0
    assert artifact["acceptance"]["human_gold_evaluated"] is False
    assert artifact["acceptance"]["row_or_schema_mapping_evaluated"] is False
    assert artifact["acceptance"]["production_accuracy_approved"] is False
