from __future__ import annotations

import json

from bctc_ai.core.hashing import sha256_file


def test_e0015_mbb_vcb_structural_fusion_is_hash_locked_and_fail_closed(project_root):
    artifact_path = project_root / "docs/experiments/E-0015-mbb-vcb-structural-fusion.json"
    assert sha256_file(artifact_path) == (
        "ee49ea1595c0d6507366739046005023308529352a3457d2d925cfd10c70d35a"
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert artifact["format_version"] == 1
    assert artifact["experiment_id"] == "E-0015"
    assert artifact["dataset_role"] == "CALIBRATION"
    assert artifact["status"] == (
        "PASS_STRUCTURAL_COMPARISON_WITH_RETAINED_DISAGREEMENTS_NO_ACCURACY_CLAIM"
    )
    assert artifact["code"] == {
        "commit": "94a2c7c4c4809764a59f9f8c977fcd6318e2d6ad",
        "dirty": False,
    }
    assert "/workspace/" not in json.dumps(artifact)

    for relative_path, digest in artifact["algorithm_files_sha256"].items():
        assert sha256_file(project_root / relative_path) == digest
    for identity in artifact["configuration"].values():
        assert sha256_file(project_root / identity["path"]) == identity["sha256"]
    upstream = artifact["upstream"]["reader_acquisition_artifact"]
    assert sha256_file(project_root / upstream["path"]) == upstream["sha256"]

    assert artifact["policy"] == {
        "alignment_features": ["DOCUMENT_ORDER", "NORMALIZED_LABEL_TEXT"],
        "automatic_confidence_effect": "NONE",
        "page_scope_applied_before_mapping": True,
        "reader_agreement_is_truth": False,
        "values_notes_codes_history_schema_arithmetic_affect_alignment": False,
    }
    metrics = artifact["metrics"]
    assert metrics["page_count"] == 13
    assert metrics["role_b_table_blocks"] == 14
    assert metrics["role_b_header_only_blocks"] == 1
    assert metrics["role_b_unresolved_table_blocks"] == 1
    assert metrics["role_b_rows"] == 244
    assert metrics["role_c_rows"] == 288
    assert metrics["role_c_two_axis_pages"] == 13
    assert metrics["role_c_index_band_pages"] == 7
    assert metrics["alignment_actions"] == {
        "EXTRA_CANDIDATE": 46,
        "MATCH": 235,
        "MERGE_CANDIDATE": 2,
        "MERGE_REFERENCE": 3,
        "MISSING_CANDIDATE": 1,
    }
    assert metrics["paired_observed_cells"] == 454
    assert metrics["exact_paired_observed_cells"] == 432
    assert metrics["paired_observed_cell_exact_agreement_rate"] == 0.95154185
    assert metrics["role_b_financial_row_structural_coverage_rate"] == 0.99565217
    assert metrics["role_c_financial_row_structural_coverage_rate"] == 0.83636364
    assert metrics["note_comparison_units"] == 94
    assert metrics["exact_note_units"] == 86
    assert metrics["row_code_comparison_units"] == 104
    assert metrics["exact_row_code_units"] == 97
    assert metrics["source_exact_labels"] == 7
    assert metrics["semantic_key_exact_labels"] == 50
    assert metrics["role_b_invalid_cells"] == 8
    assert metrics["role_c_invalid_cells"] == 0
    assert metrics["role_c_pixel_dash_cells"] == 10
    assert metrics["role_c_unassigned_numeric_lines"] == 3
    assert metrics["off_balance_mapping_eligible_alignment_units"] == 0

    expected_pages = {
        "MBB_2025_CONSOLIDATED": {
            10: ("CDKT", True, 42, 41),
            11: ("CDKT", True, 25, 24),
            12: ("CDKT", False, 12, 12),
            13: ("KQKD", True, 26, 25),
            14: ("LCTT", True, 6, 27),
            15: ("LCTT", True, 18, 19),
        },
        "VCB_2025_CONSOLIDATED": {
            8: ("CDKT", True, 37, 37),
            9: ("CDKT", True, 0, 25),
            10: ("CDKT", False, 11, 11),
            11: ("KQKD", True, 18, 18),
            12: ("KQKD", True, 8, 8),
            13: ("LCTT", True, 27, 27),
            14: ("LCTT", True, 14, 14),
        },
    }
    assert {document["key"] for document in artifact["documents"]} == set(expected_pages)
    for document in artifact["documents"]:
        source_path = project_root / document["source"]["path"]
        if source_path.is_file():
            assert source_path.stat().st_size == document["source"]["size_bytes"]
            assert sha256_file(source_path) == document["source"]["sha256"]
        for seal in document["reader_seals"].values():
            seal_path = project_root / seal["path"]
            if seal_path.is_file():
                assert sha256_file(seal_path) == seal["sha256"]

        expected = expected_pages[document["key"]]
        assert [page["page"] for page in document["pages"]] == list(expected)
        for page in document["pages"]:
            statement_type, eligible, role_b_rows, role_c_rows = expected[page["page"]]
            assert page["statement_type"] == statement_type
            assert page["mapping_eligible"] is eligible
            counts = page["comparison"]["counts"]
            assert counts["role_b_rows"] == role_b_rows
            assert counts["role_c_rows"] == role_c_rows
            role_b_result = page["role_b"]["result"]
            role_c_result = page["role_c"]["result"]
            for identity in (role_b_result, role_c_result):
                result_path = project_root / identity["path"]
                if result_path.is_file():
                    assert sha256_file(result_path) == identity["sha256"]
                    if "size_bytes" in identity:
                        assert result_path.stat().st_size == identity["size_bytes"]
            if not eligible:
                assert counts["mapping_eligible_alignment_units"] == 0
                assert all(
                    not record["scope"]["mapping_eligible"]
                    for record in page["comparison"]["alignment"]
                )

        assert all(edge["accepted"] is True for edge in document["continuation_edges"])
        assert all(
            edge["automatic_cross_page_row_merge"] is False
            for edge in document["continuation_edges"]
        )
        assert all(
            result["page_boundaries_are_hard_alignment_separators"] is True
            for result in document["statement_level_comparisons"]
        )

    mbb = next(document for document in artifact["documents"] if document["key"].startswith("MBB"))
    mbb_page_14 = next(page for page in mbb["pages"] if page["page"] == 14)
    assert mbb_page_14["comparison"]["counts"]["role_b_invalid_cells"] == 8
    assert mbb_page_14["comparison"]["counts"]["alignment_actions"] == {
        "EXTRA_CANDIDATE": 20,
        "MATCH": 5,
        "MERGE_CANDIDATE": 1,
    }

    vcb = next(document for document in artifact["documents"] if document["key"].startswith("VCB"))
    vcb_page_9 = next(page for page in vcb["pages"] if page["page"] == 9)
    table = vcb_page_9["role_b"]["tables"][0]
    assert table["status"] == "UNRESOLVED_COLUMN_ROLES"
    assert table["roles"] is None
    assert table["row_count"] == 0
    assert len(table["raw_grid"]) == 7
    vcb_page_10 = next(page for page in vcb["pages"] if page["page"] == 10)
    assert [table["status"] for table in vcb_page_10["role_b"]["tables"]] == [
        "HEADER_ONLY",
        "PARSED",
    ]
    assert vcb_page_10["role_b"]["tables"][1]["roles"]["inherited_from_table"] == 1

    assert artifact["acceptance"]["contract_exact"] is True
    assert artifact["acceptance"]["accuracy_threshold_evaluated"] is False
    assert artifact["acceptance"]["human_gold_evaluated"] is False
    assert artifact["acceptance"]["production_accuracy_approved"] is False
    assert all(value is False for value in artifact["safety"].values())
    assert artifact["report_norm_id"]["ids_proposed_or_added"] == 0
    assert artifact["report_norm_id"]["collision_check_invoked"] is False
    assert artifact["software_or_model_change"] is False
