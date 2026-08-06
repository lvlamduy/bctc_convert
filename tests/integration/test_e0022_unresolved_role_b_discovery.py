from __future__ import annotations

import json

from bctc_ai.core.hashing import sha256_file


def test_e0022_unresolved_role_b_discovery_is_hash_locked(project_root):
    artifact_path = project_root / "docs/experiments/E-0022-role-b-unresolved-discovery.json"
    assert sha256_file(artifact_path) == (
        "41ef962361cfead7cdfa4d7b8a782e61ab3fc4a938aa4fa86ebb45cbe637660e"
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert artifact["experiment_id"] == "E-0022"
    assert artifact["state"] == "ROLE_B_DISCOVERY_SEALED_UNRESOLVED"
    assert artifact["dataset_role"] == "UNTOUCHED_HOLDOUT"
    assert artifact["capture_git_commit"] == "d8daad3f2976ae474e16ae50076aac860f43f7d8"
    assert artifact["capture_git_dirty"] is False
    assert artifact["semantic_reader"] == {
        "invoked": False,
        "reason": "NO_DISCOVERED_MAIN_STATEMENT_BLOCK",
    }
    assert artifact["mapping"] == {"invoked": False}
    assert artifact["historical_reference"] == {"invoked": False}
    assert artifact["threshold_or_page_selection_tuning_performed"] is False
    assert artifact["role_a_access_permitted_during_role_b"] is False
    assert artifact["allowed_next_action"] == (
        "HYDRATE_ROLE_A_AND_BUILD_MACHINE_REFERENCE_FOR_ONE_SHOT_DIAGNOSIS"
    )

    validation = artifact["validation"]
    assert validation["source_sha256"] == (
        "a85402445a34e80dd4248471c2d23d4cf4b349ab2455b91db457f3e6effbdd4a"
    )
    assert validation["preprocess_page_count"] == 33
    assert validation["preprocess_dpi"] == 300
    assert validation["batch_page_count"] == 33
    assert validation["batch_line_count"] == 2477
    assert validation["batch_word_token_count"] == 24299
    assert validation["location_state"] == "UNRESOLVED"
    assert validation["location_candidate_count"] == 0
    assert validation["location_mapping_eligible_page_count"] == 0
    assert validation["semantic_reader_invoked"] is False
    assert validation["downstream_extraction_file_count"] == 0
    assert validation["role_a_locally_present"] is False
    assert validation["role_a_immutable_locally_present"] is False
    assert validation["role_a_holdout_output_count"] == 0
    assert validation["sealed_artifact_file_count"] == 108
    assert validation["sealed_artifact_set_sha256"] == (
        "4bdec4bad026d6ee5ad5fd69b7236692c0ee36e6a5e4a95181b142c81df700d9"
    )

    records = artifact["artifact_records"]
    assert len(records) == 108
    assert len({record["path"] for record in records}) == 108
    for record in records:
        path = project_root / record["path"]
        if path.is_file():
            assert path.stat().st_size == record["size_bytes"]
            assert sha256_file(path) == record["sha256"]

    implementation = artifact["seal_implementation"]
    assert sha256_file(project_root / implementation["path"]) == implementation["sha256"]
