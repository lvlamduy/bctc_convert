from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path

import pytest

from bctc_ai.evaluation import e0038_exact_mapping as exact_mapping
from bctc_ai.evaluation.e0038_exact_mapping import (
    MAPPING_ONLY_RELATIVE_PATH,
    MAPPING_SEAL_RELATIVE_PATH,
    _encoded_json,
    build_e0038_mapping_only,
)

PUBLISHED_E0038_ARTIFACTS = (
    {
        "path": MAPPING_ONLY_RELATIVE_PATH.as_posix(),
        "sha256": "8b1074d2ca57efcb1c6da123615ace86438069b4d581b9afb4b6e4cfbf01a9e9",
        "size_bytes": 646_606,
    },
    {
        "path": MAPPING_SEAL_RELATIVE_PATH.as_posix(),
        "sha256": "bffcaf56d80af458187a646269862b8bf669237d865fa1561ab41b056db06137",
        "size_bytes": 6_421,
    },
)


def _read_published_artifact(project_root: Path, record: dict[str, object]) -> bytes:
    payload = (project_root / str(record["path"])).read_bytes()
    assert len(payload) == record["size_bytes"]
    assert hashlib.sha256(payload).hexdigest() == record["sha256"]
    return payload


@pytest.fixture(scope="module")
def published_e0038_artifacts(project_root: Path):
    return {
        str(record["path"]): _read_published_artifact(project_root, record)
        for record in PUBLISHED_E0038_ARTIFACTS
    }


@pytest.fixture(scope="module")
def exact_payload(project_root: Path, published_e0038_artifacts):
    opened: list[str] = []

    def tracking_reader(root, path, label, **kwargs):
        opened.append(label)
        return exact_mapping._read_stable_file(root, path, label, **kwargs)

    payload = build_e0038_mapping_only(
        project_root,
        capture_git_commit=exact_mapping._git_commit(project_root),
        _reader=tracking_reader,
    )
    for record in PUBLISHED_E0038_ARTIFACTS:
        assert (
            _read_published_artifact(project_root, record)
            == published_e0038_artifacts[str(record["path"])]
        )
    return payload, opened


def test_real_dry_run_orders_authority_checks_and_pins_exact_result(
    project_root: Path,
    exact_payload,
    published_e0038_artifacts,
):
    payload, opened = exact_payload
    first = {label: opened.index(label) for label in set(opened)}
    mapping_index = first["E-0037 mapping-only bytes"]
    assert first["E-0037 mapping seal"] < first["S3 artifact snapshot registry"] < mapping_index
    assert first["E-0038 control"] < mapping_index
    assert all(
        first[f"E-0038 implementation {name}"] < mapping_index
        for name in exact_mapping._IMPLEMENTATION_PATHS
    )
    assert all(
        first[f"E-0038 policy {name}"] < mapping_index
        for name in (
            "e0037_mapping_policy",
            "e0038_exact_mapping_policy",
            "e0038_alias_policy",
        )
    )
    assert all(
        first[f"E-0038 runtime artifact {name}"] < mapping_index
        for name in exact_mapping._RUNTIME_PATHS
    )

    assert payload["reconstruction"]["source_row_count"] == 64
    assert payload["reconstruction"]["source_rows_sha256"] == exact_mapping.SOURCE_ROWS_SHA256
    assert payload["reconstruction"]["source_row_ids_sha256"] == exact_mapping.SOURCE_ROW_IDS_SHA256
    assert payload["reconstruction"]["base_schema_node_count"] == 77
    assert (
        payload["reconstruction"]["base_schema_report_norm_ids_sha256"]
        == exact_mapping.SCHEMA_IDS_SHA256
    )
    assert payload["reconstruction"]["sealed_e0037_interval_count"] == 40
    assert (
        payload["reconstruction"]["sealed_e0037_intervals_sha256"]
        == exact_mapping.SEALED_INTERVALS_SHA256
    )
    bundle = payload["exact_mapping_bundle"]
    receipt = bundle["alias_overlay_receipt"]
    assert receipt["config_sha256"] == (
        "d1cfbfd3782e1c5af1e605f8218d3f656358877f7d70c360e6bc9555e8be8948"
    )
    assert receipt["base_projection_sha256"] == exact_mapping.BASE_PROJECTION_SHA256
    assert receipt["result_projection_sha256"] == exact_mapping.RESULT_PROJECTION_SHA256
    assert receipt["changed_report_norm_ids"] == [4375, 5699]
    assert receipt["unchanged_node_count"] == 75
    assert receipt["collision_delta_pair_count"] == 0
    assert receipt["new_collision_pairs"] == []
    assert bundle["alias_overlay_receipt_sha256"] == exact_mapping.ALIAS_RECEIPT_SHA256
    assert all(
        receipt[key] is False
        for key in (
            "review_or_steward_approved",
            "production_allowed",
            "holdout_evidence_allowed",
            "historical_alias_authority_allowed",
            "numeric_period_or_value_features_allowed",
        )
    )

    exact = bundle["exact_search"]
    result = exact["mapping_result_without_internal_alias_authority"]
    assert exact["status"] == "EXACT_SEARCH_COMPLETE"
    assert exact["align_invocation_count"] == 1
    assert exact["main_search_pruned_states"] == 0
    assert exact["counterfactual_search_pruned_states"] == 0
    assert exact["plan"]["maximum_monotone_signature_bound"] == 5005
    assert exact["plan"]["total_signature_work_bound"] == 136661
    assert exact["resource_semantics"] == {
        "actual_generated_states": 9977,
        "actual_retained_states": 6833,
        "cap_is_not_a_generated_state_or_total_compute_cap": True,
        "planned_retained_signature_work_bound": 136661,
        "retained_signature_certificate_cap": 150000,
    }
    assert result["status"] == "RESOLVED"
    assert result["automatic_selection_allowed"] is True
    assert "schema_alias_authority" not in result
    assert result["schema_projection_sha256"] == exact_mapping.RESULT_PROJECTION_SHA256
    assert exact["mapping_result_sha256"] == exact_mapping.MAPPING_RESULT_SHA256
    assert result["search"]["pruned_states"] == 0
    assert payload["metrics"] == {
        "align_invocation_count": 1,
        "exact_interval_count": 42,
        "row_mapping_status_counts": {
            "BEST_PATH_SKIPPED": 2,
            "NO_ADMISSIBLE_PAIR": 4,
            "RESOLVED_ANCHOR": 41,
            "RESOLVED_PATH": 17,
        },
        "schema_disposition_status_counts": {
            "MAPPED": 58,
            "UNMATCHED_SCHEMA_NODE": 13,
            "UNMATCHED_SCHEMA_NODE_WITH_SKIPPED_CANDIDATES": 6,
        },
        "schema_node_count": 77,
        "sealed_e0037_interval_count": 40,
        "selected_row_count": 58,
        "source_row_count": 64,
    }
    assert payload["e0037_input_authority"]["s3_registry_record_sha256"] == (
        exact_mapping.S3_SNAPSHOT_RECORD_SHA256
    )
    assert payload["result_input_binding"]["mapping_result_sha256"] == (
        exact_mapping.MAPPING_RESULT_SHA256
    )
    assert payload["runtime_versions"] == exact_mapping._RUNTIME_VERSIONS
    for record in PUBLISHED_E0038_ARTIFACTS:
        assert (
            _read_published_artifact(project_root, record)
            == published_e0038_artifacts[str(record["path"])]
        )


def test_real_mapping_replay_is_byte_deterministic_and_does_not_publish(
    project_root: Path,
    exact_payload,
    published_e0038_artifacts,
):
    first_payload, _opened = exact_payload
    second_payload = build_e0038_mapping_only(
        project_root,
        capture_git_commit=first_payload["capture_git_commit"],
    )
    first_bytes = _encoded_json(first_payload)
    second_bytes = _encoded_json(second_payload)

    assert first_payload == second_payload
    assert first_bytes == second_bytes
    assert hashlib.sha256(first_bytes).hexdigest() == hashlib.sha256(second_bytes).hexdigest()
    for record in PUBLISHED_E0038_ARTIFACTS:
        assert (
            _read_published_artifact(project_root, record)
            == published_e0038_artifacts[str(record["path"])]
        )


def test_mapping_validator_rejects_injected_review_or_accuracy_authority(
    project_root: Path,
    exact_payload,
):
    payload, _opened = exact_payload
    control = exact_mapping._decode_control(
        (project_root / exact_mapping.CONTROL_RELATIVE_PATH).read_bytes()
    )
    injected = deepcopy(payload)
    injected["exact_mapping_bundle"]["alias_overlay_receipt"]["human_review"] = "APPROVED"
    with pytest.raises(exact_mapping.E0038ExactMappingError, match="keyset"):
        exact_mapping._validate_e0038_mapping_payload(
            injected,
            control,
            expected_control_artifact=payload["input_hash_ledger"]["control"],
            expected_git_commit=payload["capture_git_commit"],
        )

    elevated = deepcopy(payload)
    elevated["authority"]["mapping_accuracy"] = True
    with pytest.raises(exact_mapping.E0038ExactMappingError, match="authority"):
        exact_mapping._validate_e0038_mapping_payload(
            elevated,
            control,
            expected_control_artifact=payload["input_hash_ledger"]["control"],
            expected_git_commit=payload["capture_git_commit"],
        )


def test_mapping_validator_rejects_certification_cross_binding_mutations(
    project_root: Path,
    exact_payload,
):
    payload, _opened = exact_payload
    control = exact_mapping._decode_control(
        (project_root / exact_mapping.CONTROL_RELATIVE_PATH).read_bytes()
    )
    mutations = []

    alias_scores = deepcopy(payload)
    alias_scores["exact_mapping_bundle"]["alias_overlay_receipt"]["score_audits"] = [{}, {}]
    mutations.append(alias_scores)

    row_id = deepcopy(payload)
    row_id["exact_mapping_bundle"]["exact_search"][
        "mapping_result_without_internal_alias_authority"
    ]["row_mappings"][0]["row_id"] = "forged-row"
    mutations.append(row_id)

    schema_id = deepcopy(payload)
    schema_id["exact_mapping_bundle"]["exact_search"][
        "mapping_result_without_internal_alias_authority"
    ]["schema_dispositions"][0]["report_norm_id"] = 2_000_000_000
    mutations.append(schema_id)

    status = deepcopy(payload)
    status["exact_mapping_bundle"]["exact_search"]["status"] = "ABSTAINED_HARD_CAP_EXCEEDED"
    mutations.append(status)

    reason = deepcopy(payload)
    reason["exact_mapping_bundle"]["exact_search"]["reason"] = "forged reason"
    mutations.append(reason)

    interval_bound = deepcopy(payload)
    interval_bound["exact_mapping_bundle"]["exact_search"]["plan"]["interval_bounds"][0][
        "row_count"
    ] = 999
    mutations.append(interval_bound)

    s3_digest = deepcopy(payload)
    s3_digest["e0037_input_authority"]["s3_registry_record_sha256"] = "0" * 64
    mutations.append(s3_digest)

    injected_upstream_authority = deepcopy(payload)
    injected_upstream_authority["e0037_input_authority"]["review_approved"] = True
    mutations.append(injected_upstream_authority)

    metrics = deepcopy(payload)
    metrics["metrics"]["selected_row_count"] = 57
    mutations.append(metrics)

    binding = deepcopy(payload)
    binding["result_input_binding"]["source_rows_sha256"] = "0" * 64
    mutations.append(binding)

    forged_control = deepcopy(payload)
    forged_control["input_hash_ledger"]["control"] = {
        **forged_control["input_hash_ledger"]["control"],
        "sha256": "3" * 64,
    }
    mutations.append(forged_control)

    forged_capture_commit = deepcopy(payload)
    forged_capture_commit["capture_git_commit"] = "c" * 40
    mutations.append(forged_capture_commit)

    for mutated in mutations:
        with pytest.raises(exact_mapping.E0038ExactMappingError):
            exact_mapping._validate_e0038_mapping_payload(
                mutated,
                control,
                expected_control_artifact=payload["input_hash_ledger"]["control"],
                expected_git_commit=payload["capture_git_commit"],
            )


def test_standalone_seal_validator_binds_status_and_both_control_receipts(
    project_root: Path,
    exact_payload,
):
    payload, _opened = exact_payload
    control_bytes = (project_root / exact_mapping.CONTROL_RELATIVE_PATH).read_bytes()
    control = exact_mapping._decode_control(control_bytes)
    control_artifact = payload["input_hash_ledger"]["control"]
    control_stable = exact_mapping._StableFile(
        path=project_root / exact_mapping.CONTROL_RELATIVE_PATH,
        payload=control_bytes,
        identity=(1, 2, 0o100644, len(control_bytes), 3, 4),
        artifact=control_artifact,
    )
    mapping_bytes = _encoded_json(payload)
    mapping_artifact = {
        "path": exact_mapping.MAPPING_ONLY_RELATIVE_PATH.as_posix(),
        "sha256": hashlib.sha256(mapping_bytes).hexdigest(),
        "size_bytes": len(mapping_bytes),
    }
    mapping_stable = exact_mapping._StableFile(
        path=project_root / exact_mapping.MAPPING_ONLY_RELATIVE_PATH,
        payload=mapping_bytes,
        identity=(1, 3, 0o100644, len(mapping_bytes), 4, 5),
        artifact=mapping_artifact,
    )
    seal = exact_mapping._assemble_mapping_seal(
        commit=payload["capture_git_commit"],
        control_stable=control_stable,
        mapping_stable=mapping_stable,
        mapping_payload=payload,
    )
    exact_mapping._validate_e0038_mapping_seal_payload(
        seal,
        control,
        expected_control_artifact=control_artifact,
        expected_mapping_artifact=mapping_artifact,
        expected_git_commit=payload["capture_git_commit"],
    )

    forged_status = deepcopy(seal)
    forged_status["mapping_status"] = "FORGED"
    forged_outer = deepcopy(seal)
    forged_outer["input_hash_ledger"]["control"] = {
        **forged_outer["input_hash_ledger"]["control"],
        "sha256": "0" * 64,
    }
    forged_replay = deepcopy(seal)
    forged_replay["input_hash_ledger"]["deterministic_replay_inputs"]["control"] = {
        **forged_replay["input_hash_ledger"]["deterministic_replay_inputs"]["control"],
        "sha256": "1" * 64,
    }
    injected_inventory = deepcopy(seal)
    injected_inventory["inventory"]["review_approved"] = True
    forged_mapping = deepcopy(seal)
    forged_mapping_record = {
        **forged_mapping["inventory"]["files"][0],
        "sha256": "2" * 64,
    }
    forged_mapping["inventory"]["files"][0] = forged_mapping_record
    forged_mapping["input_hash_ledger"]["mapping_only"] = dict(forged_mapping_record)
    forged_commit = deepcopy(seal)
    forged_commit["seal_git_commit"] = "b" * 40
    forged_commit["mapping_capture_git_commit"] = "b" * 40
    for mutated in (
        forged_status,
        forged_outer,
        forged_replay,
        injected_inventory,
        forged_mapping,
        forged_commit,
    ):
        with pytest.raises(exact_mapping.E0038ExactMappingError):
            exact_mapping._validate_e0038_mapping_seal_payload(
                mutated,
                control,
                expected_control_artifact=control_artifact,
                expected_mapping_artifact=mapping_artifact,
                expected_git_commit=payload["capture_git_commit"],
            )
