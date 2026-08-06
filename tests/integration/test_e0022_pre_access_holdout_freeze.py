from __future__ import annotations

import json

from bctc_ai.core.hashing import sha256_file


def test_e0022_pre_access_holdout_freeze_is_hash_locked(project_root):
    artifact_path = project_root / "docs/experiments/E-0022-pre-access-holdout-freeze.json"
    assert sha256_file(artifact_path) == (
        "33c296c0cc2e0d2bd3a54a2d6835b6eea8c634a6a626f7de5ca1b0940c786b4c"
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert artifact["format_version"] == 1
    assert artifact["experiment_id"] == "E-0022"
    assert artifact["state"] == "PRE_ACCESS_HOLDOUT_FREEZE_VERIFIED"
    assert artifact["dataset_role"] == "UNTOUCHED_HOLDOUT"
    assert artifact["capture_git_commit"] == ("d56a86a837a1e6a1d1318cd73dbba7bee888d515")
    assert artifact["capture_git_dirty"] is False
    assert artifact["source_content_read_by_capture"] is False
    assert artifact["all_sources_locally_absent"] is True
    assert artifact["allowed_next_action"] == "HYDRATE_ROLE_B_SOURCE_ONLY"
    assert artifact["role_a_access_permitted"] is False
    assert "does not inspect PDF bytes" in artifact["claim_boundary"]

    config = artifact["freeze_config"]
    assert sha256_file(project_root / config["path"]) == config["sha256"]

    validation = artifact["validation"]
    assert validation["frozen_git_commit"] == ("e0496e2196ada0a66213469d09296528dd37cc54")
    assert validation["frozen_file_count"] == 24
    assert validation["schema_item_count"] == 1593
    assert validation["tm_1944_present"] is True
    assert validation["role_a_access_gate"] == "FORBIDDEN_UNTIL_ROLE_B_SEALED"
    assert validation["thresholds_reusable_for_retuning"] is False
    assert len(validation["sources"]) == 2
    assert {source["fixture_role"] for source in validation["sources"]} == {
        "ROLE_A_SOURCE",
        "ROLE_B_SOURCE",
    }
    assert all(source["dataset_role"] == "UNTOUCHED_HOLDOUT" for source in validation["sources"])
    assert all(source["locally_present"] is False for source in validation["sources"])
    assert all(
        source["s3_object_key"].endswith(source["sha256"]) for source in validation["sources"]
    )

    for relative_path, digest in validation["frozen_files_sha256"].items():
        assert sha256_file(project_root / relative_path) == digest
