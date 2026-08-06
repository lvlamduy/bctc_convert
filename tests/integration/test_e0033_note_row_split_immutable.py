from __future__ import annotations

import json

from bctc_ai.core.hashing import sha256_file


def test_e0033_note_row_split_preserves_frozen_v3(project_root):
    path = (
        project_root
        / "docs/experiments/E-0033-mbb-cdkt-note-row-split-immutable.json"
    )
    assert sha256_file(path) == (
        "d9c0ecf44f6a0f652e6c991d3ab95b7ab0e821068366764e39a3f0de7f0711fb"
    )
    artifact = json.loads(path.read_text(encoding="utf-8"))

    assert artifact["experiment_id"] == "E-0033"
    assert artifact["status"] == "PASS_REFERENCE_BLIND_NOTE_ROW_ANCHOR_SPLIT"
    assert artifact["capture_git_commit"] == (
        "82d64989313f917be40d4baf39a23b5d77506444"
    )
    assert artifact["verified_inputs"]["inherited_v3_algorithm"]["sha256"] == (
        "e5650bd48866340cec32ed41e8b131cdf8289c25479be43a11c29763ea153663"
    )
    assert sha256_file(
        project_root / "src/bctc_ai/evaluation/word_box_rows_v3.py"
    ) == ("e5650bd48866340cec32ed41e8b131cdf8289c25479be43a11c29763ea153663")
    assert [page["summary"]["row_count"] for page in artifact["after"]] == [39, 25]
    comparison = artifact["comparison"]
    assert comparison["unchanged_common_row_count"] == 62
    assert comparison["changed_common_row_count"] == 0
    assert comparison["partitioned_split_count"] == 1
    assert comparison["preserved_value_cell_split_count"] == 1
    assert comparison["source_line_coverage_delta_count"] == 0
    assert all(artifact["gates"].values())
    assert all(not value for value in artifact["reference_isolation"].values())
