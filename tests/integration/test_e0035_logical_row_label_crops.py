from __future__ import annotations

import json

from bctc_ai.core.hashing import sha256_file


def test_e0035_logical_row_label_crop_seal_is_hash_locked(project_root):
    path = project_root / "docs/experiments/E-0035-mbb-cdkt-logical-row-label-crops.json"
    assert sha256_file(path) == ("a1bb81e895b45d003910aba523ba121461f15079b9452dde8d508600c5dcc3e3")
    artifact = json.loads(path.read_text(encoding="utf-8"))

    assert artifact["experiment_id"] == "E-0035"
    assert artifact["status"] == ("PASS_REFERENCE_BLIND_ALL_LOGICAL_ROW_LABEL_CROPS_FROZEN")
    assert artifact["capture_git_commit"] == ("bf7be982b109de537f5b2ab280be0c3144750573")
    assert artifact["metrics"]["crop_count"] == 64
    assert artifact["metrics"]["page_crop_counts"] == {"3": 39, "4": 25}
    assert artifact["metrics"]["unique_crop_sha256_count"] == 64
    assert artifact["metrics"]["minimum_note_boundary_clearance_pixels"] == 137.0
    assert all(artifact["gates"].values())
    assert all(not value for value in artifact["reference_isolation"].values())
    assert artifact["recovery_provenance"]["original_batch_manifest_recovered"] is False
    assert artifact["s3_artifact_snapshot"]["restore_verified"] is True
    assert artifact["s3_artifact_snapshot"]["hydrate_probe"]["reused_file_count"] == 1
