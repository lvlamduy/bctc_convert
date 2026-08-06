from __future__ import annotations

import json

from bctc_ai.core.hashing import sha256_file


def test_e0030_visible_word_box_table_metadata_is_hash_locked(project_root):
    artifact_path = project_root / "docs/experiments/E-0030-mbb-cdkt-table-metadata.json"
    assert sha256_file(artifact_path) == (
        "3e0e6888802fc190879f360cf8c679f1cefb334e9188b4baec05a668fee12577"
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert artifact["experiment_id"] == "E-0030"
    assert artifact["status"] == "PASS_REFERENCE_BLIND_VISIBLE_HEADER_BINDING"
    assert artifact["dataset_role"] == "CALIBRATION"
    assert artifact["capture_git_commit"] == ("10cd8bf1a2a8d0210f4820ed9d637a70ec99537b")
    assert artifact["before"] == {
        "resolved_axis_count": 0,
        "status": "NO_WORD_BOX_VISIBLE_HEADER_BINDING_CONTRACT",
    }
    assert [record["page"] for record in artifact["after"]] == [3, 4]
    for record in artifact["after"]:
        assert record["binding_mode"] == "LOCAL_VISIBLE_HEADERS"
        assert [axis["raw_period_header"] for axis in record["axes"]] == [
            "31/03/2026",
            "31/12/2025",
        ]
        assert [axis["period_end"] for axis in record["axes"]] == [
            "2026-03-31",
            "2025-12-31",
        ]
        assert [axis["current_or_comparative"] for axis in record["axes"]] == [
            "CURRENT",
            "COMPARATIVE",
        ]
        assert [axis["raw_unit_text"] for axis in record["axes"]] == [
            "triu đồng",
            "triu đồng",
        ]
        assert all(axis["canonical_unit"] == "VND" for axis in record["axes"])
        assert all(axis["unit_multiplier"] == 1_000_000 for axis in record["axes"])
        assert all(axis["unit_similarity"] == 0.947368 for axis in record["axes"])
        assert all(axis["distinct_semantics_margin"] == 0.315789 for axis in record["axes"])
        assert all(
            column["source_header_page"] == record["page"]
            for column in record["period_map_columns"]
        )
    assert artifact["propagation_issues"] == []
    assert all(artifact["gates"].values())
    assert artifact["reference_isolation"] == {
        "accounting_validation_invoked": False,
        "continuation_inheritance_used": False,
        "e0022_evidence_loaded": False,
        "excel_export_invoked": False,
        "historical_or_mongodb_values_loaded": False,
        "horizontal_position_used_as_period_role": False,
        "human_review_loaded": False,
        "numeric_cell_text_or_value_used_as_period_unit_feature": False,
        "numeric_value_magnitude_used": False,
        "off_balance_page_5_loaded": False,
        "schema_mapping_invoked": False,
        "template_labels_or_report_norm_ids_loaded": False,
    }
