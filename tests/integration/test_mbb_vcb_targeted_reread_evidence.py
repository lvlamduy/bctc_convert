from __future__ import annotations

import json

import yaml

from bctc_ai.core.hashing import sha256_file, stable_records_hash


def _regions_by_identity(artifact):
    return {
        (document["key"], page["page"], region["region_id"]): region
        for document in artifact["documents"]
        for page in document["pages_with_rereads"]
        for region in page["regions"]
    }


def test_e0016_targeted_reread_evidence_is_hash_locked_and_retains_failures(project_root):
    artifact_path = project_root / "docs/experiments/E-0016-mbb-vcb-targeted-reread-evidence.json"
    assert sha256_file(artifact_path) == (
        "fe9c83bc612709630183c7bf871caa5ba59406c6b6dc83c39ede54e6293a4762"
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert artifact["format_version"] == 1
    assert artifact["experiment_id"] == "E-0016"
    assert artifact["phase"] == "ORIGINAL_VARIANT_OCR_EVIDENCE"
    assert artifact["dataset_role"] == "CALIBRATION"
    assert artifact["status"] == (
        "PASS_ORIGINAL_CROP_OCR_EVIDENCE_WITH_RETAINED_FAILURES_NO_VALUE_SELECTION"
    )
    assert artifact["code"] == {
        "commit": "8c2f7fbe08affce491df26113eaee10920fd459c",
        "dirty": False,
    }
    assert "/workspace/" not in json.dumps(artifact)

    for relative_path, digest in artifact["algorithm_files_sha256"].items():
        assert sha256_file(project_root / relative_path) == digest
    for identity in artifact["configuration"].values():
        assert sha256_file(project_root / identity["path"]) == identity["sha256"]

    input_identity = artifact["upstream"]["targeted_reread_input_manifest"]
    input_path = project_root / input_identity["path"]
    if input_path.is_file():
        assert input_path.stat().st_size == input_identity["size_bytes"]
        assert sha256_file(input_path) == input_identity["sha256"]
    assert artifact["upstream"]["verified_input_chain_file_count"] == 47
    assert artifact["upstream"]["input_generation_code"] == {
        "commit": "d9a18d47d950d7be97e6e6d12ddae125714e5f5b",
        "dirty": False,
    }
    assert artifact["runtime"]["ppocrv6_inference_git_commits"] == [
        "d9a18d47d950d7be97e6e6d12ddae125714e5f5b"
    ]
    assert artifact["runtime"]["paddleocr_vl_inference_git_commit_evidence"] == (
        "NOT_SELF_RECORDED_BY_RUNNER"
    )

    config_path = project_root / "config/experiments/e0016-mbb-vcb-targeted-reread-evidence.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert artifact["metrics"] == config["expected_evidence_contract"]
    assert artifact["metrics"] == {
        "automatic_confidence_promotion_count": 0,
        "automatic_value_replacement_count": 0,
        "automatic_variant_selection_count": 0,
        "completed_reader_run_count": 15,
        "document_count": 2,
        "evaluated_original_variant_count": 8,
        "full_table_exact_paired_observed_cell_count": 66,
        "full_table_paddleocr_vl_parse_success_count": 2,
        "full_table_paddleocr_vl_row_count": 44,
        "full_table_paired_observed_cell_count": 84,
        "full_table_ppocrv6_parse_success_count": 2,
        "full_table_ppocrv6_row_count": 54,
        "full_table_ppocrv6_two_axis_count": 2,
        "full_table_reader_row_count_disagreement_count": 2,
        "full_table_region_count": 2,
        "mapping_ineligible_region_count": 0,
        "numeric_cell_strip_region_count": 1,
        "paddleocr_vl_invalid_cell_count": 14,
        "paddleocr_vl_no_table_region_count": 1,
        "paddleocr_vl_parsed_row_count": 62,
        "paddleocr_vl_parsed_table_count": 5,
        "paddleocr_vl_pass_count": 7,
        "paddleocr_vl_run_count": 7,
        "paddleocr_vl_table_block_count": 6,
        "paddleocr_vl_unresolved_table_count": 1,
        "planned_page_count": 6,
        "ppocrv6_line_count": 308,
        "ppocrv6_run_count": 8,
        "ppocrv6_strict_financial_token_line_count": 181,
        "ppocrv6_word_token_count": 2241,
        "region_count": 8,
        "report_norm_ids_proposed_or_added": 0,
        "requested_reader_run_count": 15,
        "row_band_region_count": 5,
        "source_variant_count": 18,
        "unevaluated_variant_count": 10,
    }

    output_set = artifact["reader_output_artifact_set"]
    assert output_set["file_count"] == 52
    assert output_set["sha256"] == (
        "0c993e0192f3bbdf67dfa9e9a3d0f054e2bd20fa2b4b8c7fab57fc970997875d"
    )
    local_outputs = [project_root / record["path"] for record in output_set["files"]]
    present_outputs = [path for path in local_outputs if path.is_file()]
    if present_outputs:
        assert len(present_outputs) == len(local_outputs)
        for path, identity in zip(local_outputs, output_set["files"], strict=True):
            assert path.stat().st_size == identity["size_bytes"]
            assert sha256_file(path) == identity["sha256"]
        assert (
            stable_records_hash(
                f"{record['sha256']}  {record['path']}  {record['size_bytes']}"
                for record in output_set["files"]
            )
            == output_set["sha256"]
        )

    regions = _regions_by_identity(artifact)
    assert len(regions) == 8
    for region in regions.values():
        assert region["evaluated_variant"] == "original"
        assert region["variant_selection_status"] == ("NO_VARIANT_SELECTED_BASELINE_EVIDENCE_ONLY")
        assert sum(variant["evaluated"] for variant in region["variants"]) == 1
        assert all(variant["selected"] is False for variant in region["variants"])
        assert region["automatic_value_replacement"] is False
        assert region["automatic_confidence_promotion"] is False
        if not region["includes_period_header_pixels"]:
            assert region["period_binding_from_reread_allowed"] is False
            assert region["readers"]["PP_OCRV6_MEDIUM"]["parser"]["status"] == (
                "NOT_APPLICABLE_REGION_HAS_NO_PERIOD_HEADER"
            )

    mbb_14 = regions[("MBB_2025_CONSOLIDATED", 14, "region-0001")]
    assert mbb_14["upstream_page"]["role_b_row_count"] == 6
    assert mbb_14["upstream_page"]["role_c_row_count"] == 27
    assert mbb_14["readers"]["PADDLEOCR_VL_1_6"]["parser"]["row_count"] == 18
    assert mbb_14["readers"]["PADDLEOCR_VL_1_6"]["parser"]["invalid_cell_count"] == 14
    assert mbb_14["readers"]["PP_OCRV6_MEDIUM"]["parser"]["row_count"] == 27
    assert mbb_14["readers"]["PP_OCRV6_MEDIUM"]["parser"]["invalid_cell_count"] == 0
    assert mbb_14["full_table_comparison"]["counts"]["alignment_actions"] == {
        "EXTRA_CANDIDATE": 8,
        "MATCH": 17,
        "MERGE_CANDIDATE": 1,
    }
    assert mbb_14["full_table_comparison"]["counts"]["exact_paired_observed_cells"] == 18
    assert mbb_14["full_table_comparison"]["counts"]["paired_observed_cells"] == 36

    vcb_9 = regions[("VCB_2025_CONSOLIDATED", 9, "region-0001")]
    assert vcb_9["upstream_page"]["role_b_row_count"] == 0
    assert vcb_9["upstream_page"]["role_b_raw_grid_row_count"] == 7
    assert vcb_9["upstream_page"]["role_c_row_count"] == 25
    assert vcb_9["readers"]["PADDLEOCR_VL_1_6"]["parser"]["row_count"] == 26
    assert vcb_9["readers"]["PP_OCRV6_MEDIUM"]["parser"]["row_count"] == 27
    assert vcb_9["full_table_comparison"]["counts"]["exact_paired_observed_cells"] == 48
    assert vcb_9["full_table_comparison"]["counts"]["paired_observed_cells"] == 48
    assert vcb_9["full_table_comparison"]["policy"]["agreement_promotes_confidence"] is False

    assert (
        regions[("MBB_2025_CONSOLIDATED", 10, "region-0002")]["readers"]["PADDLEOCR_VL_1_6"][
            "parser"
        ]["status"]
        == "PARTIALLY_UNRESOLVED"
    )
    assert (
        regions[("MBB_2025_CONSOLIDATED", 13, "region-0002")]["readers"]["PADDLEOCR_VL_1_6"][
            "parser"
        ]["status"]
        == "NO_TABLE_BLOCK"
    )

    assert artifact["acceptance"]["contract_exact"] is True
    assert artifact["acceptance"]["all_requested_original_reader_runs_complete"] is True
    assert artifact["acceptance"]["variant_selection_evaluated"] is False
    assert artifact["acceptance"]["human_gold_evaluated"] is False
    assert artifact["acceptance"]["accuracy_threshold_evaluated"] is False
    assert artifact["acceptance"]["production_accuracy_approved"] is False
    assert artifact["safety"] == {
        "arithmetic_invoked": False,
        "automatic_confidence_promotion": False,
        "automatic_value_replacement": False,
        "automatic_variant_selection": False,
        "history_invoked": False,
        "report_norm_id_order_or_magnitude_used": False,
        "report_norm_ids_proposed_or_added": 0,
        "schema_mapping_invoked": False,
    }
