from __future__ import annotations

import json

from bctc_ai.core.hashing import sha256_file


def test_e0032_note_row_split_is_hash_locked(project_root):
    path = project_root / "docs/experiments/E-0032-mbb-cdkt-note-row-split.json"
    assert sha256_file(path) == (
        "8bbd9a6713fece470113a5ef1003a786736be26d351cfc105858fb5adcd683bc"
    )
    artifact = json.loads(path.read_text(encoding="utf-8"))

    assert artifact["experiment_id"] == "E-0032"
    assert artifact["status"] == "PASS_REFERENCE_BLIND_NOTE_ROW_ANCHOR_SPLIT"
    assert artifact["capture_git_commit"] == (
        "bf5ff340d08bbb53f0ed59f8f47fcc126e5f3e33"
    )
    assert [page["summary"]["row_count"] for page in artifact["after"]] == [39, 25]
    assert [page["summary"]["cell_count"] for page in artifact["after"]] == [78, 50]
    assert artifact["after"][0]["summary"]["observation_counts"] == {
        "BLANK": 3,
        "DASH": 3,
        "VALUE": 72,
    }
    comparison = artifact["comparison"]
    assert comparison["common_row_count"] == 62
    assert comparison["unchanged_common_row_count"] == 62
    assert comparison["changed_common_row_count"] == 0
    assert comparison["removed_composite_row_count"] == 1
    assert comparison["replacement_row_count"] == 2
    assert comparison["partitioned_split_count"] == 1
    assert comparison["preserved_value_cell_split_count"] == 1
    assert comparison["source_line_coverage_delta_count"] == 0
    assert all(artifact["gates"].values())
    assert artifact["reference_isolation"]["human_review_loaded"] is False
    assert artifact["reference_isolation"]["schema_mapping_invoked"] is False
    assert artifact["reference_isolation"]["off_balance_page_5_loaded"] is False

    replacement = comparison["replacement_rows"]
    assert len(replacement) == 2
    dash_row = next(
        row for row in replacement if all(cell["observation"] == "DASH" for cell in row["cells"])
    )
    assert all(
        evidence["observation"] == "DASH"
        for evidence in dash_row["geometry"]["visual_cell_evidence"]
    )
