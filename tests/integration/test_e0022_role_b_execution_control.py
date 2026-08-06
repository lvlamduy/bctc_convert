from __future__ import annotations

import json

from bctc_ai.core.hashing import sha256_file


def test_e0022_role_b_execution_control_is_hash_locked(project_root):
    artifact_path = project_root / "docs/experiments/E-0022-role-b-execution-control.json"
    assert sha256_file(artifact_path) == (
        "c56721c3164c42e5ddd869778134b0196a914d04144b7a591524b0a6bc200d81"
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert artifact["experiment_id"] == "E-0022"
    assert artifact["state"] == "ROLE_B_EXECUTION_READY"
    assert artifact["dataset_role"] == "UNTOUCHED_HOLDOUT"
    assert artifact["capture_git_commit"] == "cf83314391e1cb94669481acc48bca2d12535579"
    assert artifact["capture_git_dirty"] is False
    assert artifact["role_a_access_permitted"] is False
    assert artifact["threshold_or_page_selection_tuning_performed"] is False
    assert artifact["allowed_next_action"] == "PREPROCESS_ROLE_B_FULL_DOCUMENT"

    validation = artifact["validation"]
    assert validation["frozen_git_commit"] == "e0496e2196ada0a66213469d09296528dd37cc54"
    assert validation["role_b_sha256"] == (
        "a85402445a34e80dd4248471c2d23d4cf4b349ab2455b91db457f3e6effbdd4a"
    )
    assert validation["role_b_page_count"] == 33
    assert validation["role_b_text_layer_chars_first_five_pages"] == [0, 0, 0, 0, 0]
    assert validation["role_a_locally_present"] is False
    assert validation["role_a_immutable_locally_present"] is False
    assert validation["role_a_holdout_output_count"] == 0
    assert validation["output_root_exists"] is False
    assert validation["execution_file_count"] == 11
    assert len(validation["execution_files_sha256"]) == 11

    config = artifact["configuration"]
    assert sha256_file(project_root / config["path"]) == config["sha256"]
