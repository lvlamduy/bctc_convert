from __future__ import annotations

import json

from bctc_ai.core.hashing import sha256_file


def test_e0029_reference_blind_row_reconstruction_is_hash_locked(project_root):
    artifact_path = (
        project_root
        / "docs/experiments/E-0029-mbb-cdkt-row-reconstruction.json"
    )
    assert sha256_file(artifact_path) == (
        "affe74a243e342b56c4ead2fac984f10d9a1f42378823b50ccdde8946eeed373"
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert artifact["experiment_id"] == "E-0029"
    assert artifact["status"] == "PASS_REFERENCE_BLIND_ROW_RECONSTRUCTION"
    assert artifact["dataset_role"] == "CALIBRATION"
    assert artifact["capture_git_commit"] == (
        "f71fb4ea4bcbb5192213644e4f1e9e41394929c6"
    )
    assert artifact["before"] == [
        {
            "error": "could not infer two separated period header axes",
            "page": page,
            "status": "FAILED_CLOSED",
        }
        for page in (3, 4)
    ]

    summaries = {page["page"]: page["summary"] for page in artifact["after"]}
    assert summaries[3] == {
        "axis_headers_left_to_right": ["31/03/2026", "31/12/2025"],
        "blank_cell_count": 3,
        "cell_count": 76,
        "dash_cell_count": 1,
        "duplicate_source_line_assignment_count": 0,
        "header_companion_leak_count": 0,
        "invalid_cell_count": 0,
        "note_reference_count": 18,
        "note_reference_prefix_leak_count": 0,
        "observation_counts": {
            "BLANK": 3,
            "DASH": 1,
            "VALUE": 72,
        },
        "page": 3,
        "row_count": 38,
        "rows_with_exactly_two_cells": 38,
        "trailing_row_count": 0,
        "unassigned_numeric_line_count": 0,
        "unassigned_numeric_line_indices": [],
    }
    assert summaries[4] == {
        "axis_headers_left_to_right": ["31/03/2026", "31/12/2025"],
        "blank_cell_count": 6,
        "cell_count": 50,
        "dash_cell_count": 2,
        "duplicate_source_line_assignment_count": 0,
        "header_companion_leak_count": 0,
        "invalid_cell_count": 0,
        "note_reference_count": 8,
        "note_reference_prefix_leak_count": 0,
        "observation_counts": {
            "BLANK": 6,
            "DASH": 2,
            "VALUE": 42,
        },
        "page": 4,
        "row_count": 25,
        "rows_with_exactly_two_cells": 25,
        "trailing_row_count": 0,
        "unassigned_numeric_line_count": 1,
        "unassigned_numeric_line_indices": [66],
    }
    assert all(artifact["gates"].values())
    assert artifact["reference_isolation"] == {
        "accounting_validation_invoked": False,
        "e0022_evidence_loaded": False,
        "excel_export_invoked": False,
        "historical_values_loaded": False,
        "human_review_loaded": False,
        "mapping_invoked": False,
        "off_balance_page_5_loaded": False,
        "period_role_assignment_invoked": False,
        "report_norm_ids_loaded": False,
        "semantic_reader_invoked": False,
        "template_labels_loaded": False,
    }

