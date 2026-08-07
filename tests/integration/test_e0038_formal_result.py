from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

MAPPING_ONLY = {
    "path": "output/calibration/e0038-mbb-cdkt-exact-mapping/mapping_only.json",
    "sha256": "8b1074d2ca57efcb1c6da123615ace86438069b4d581b9afb4b6e4cfbf01a9e9",
    "size_bytes": 646_606,
}
MAPPING_SEAL = {
    "path": "docs/experiments/E-0038-mbb-cdkt-exact-mapping-seal.json",
    "sha256": "bffcaf56d80af458187a646269862b8bf669237d865fa1561ab41b056db06137",
    "size_bytes": 6_421,
}
S3_REGISTRATION = {
    "path": "docs/experiments/E-0038-mbb-cdkt-exact-mapping-s3-registration.json",
    "sha256": "6baf6a90842066e5253533072a800c5066e97248745efed8480cb67c410601e4",
    "size_bytes": 9_555,
}
SHARED_REGISTRY = {
    "path": "data/registered/s3_artifact_snapshot_registry.jsonl",
    "sha256": "25da6b205a775d87eca8e4ffe55e3f762ee64e92cbb7190c2834708a7de0d78d",
    "size_bytes": 6_050,
}

SNAPSHOT_ID = "20260807T192436Z-e0038-exact-mapping-seal-8b1074d2ca57"
CONTENT_KEY = (
    "bctc-ai/objects/sha256/8b/8b1074d2ca57efcb1c6da123615ace86438069b4d581b9afb4b6e4cfbf01a9e9"
)
CONTENT_VERSION = "79cSikvjXwMrTfnT9UqiPKLpKVrufjwq"
MANIFEST_SHA256 = "9b961638b80a85256f6926120ab71fb11dcd1ac8e2995110e13285a54539a95e"
MANIFEST_KEY = f"bctc-ai/artifact-snapshots/{SNAPSHOT_ID}/manifest-{MANIFEST_SHA256}.json"
MANIFEST_VERSION = "mFQGsJo6jw_TMYgeDo8eYhVYc9N3DKDs"
RUN_SHA256 = "c69742341292b5547a7154e2db0efc840e36becad0fc772ff51ded0f09500a4a"
RUN_KEY = f"bctc-ai/artifact-runs/{SNAPSHOT_ID}/run-{RUN_SHA256}.json"
RUN_VERSION = "SO4BVN2zgXIGokPQJrmwStG4T0WhZwRl"
PARENT_SNAPSHOT_ID = "20260806T050030130746Z-4a469fab2334"
PARENT_MANIFEST_SHA256 = "74be9ea09905f0c7842d5a0b46bfe44f3fc5f32cc2c15b5040efcc4e99e8981b"
PARENT_RUN_SHA256 = "24eb066b51443066dfd14538ef7aeb21e9b700cc6ce995c49e56ff23b6701b04"
MAPPING_CLAIM_BOUNDARY = (
    "E-0038 is an MBB CDKT calibration-only mechanism run over the exact hash-sealed "
    "E-0037 mapping-only evidence. Its two ID-scoped aliases are unapproved calibration "
    "hypotheses, not schema authority or review evidence. Exact-search completion records "
    "deterministic zero-pruning behavior under pinned inputs; it does not establish mapping "
    "accuracy, schema correctness, period, unit, numeric truth, accounting validity, Excel "
    "correctness, holdout performance, or production readiness."
)
SEAL_CLAIM_BOUNDARY = (
    "This artifact hash-seals exactly one E-0038 mapping-only file after deterministic "
    "replay from a clean Git commit and before review access. It adds no schema, "
    "mapping-accuracy, numeric, period, unit, accounting, Excel, holdout, or production "
    "claim."
)
REGISTRATION_CLAIM_BOUNDARY = (
    "This immutable post-seal artifact registers only S3 durability and restore facts for "
    "the already hash-sealed E-0038 calibration mapping. It does not add or imply schema "
    "authority, mapping accuracy, review or steward approval, numeric, period, unit, "
    "accounting, Excel, holdout, or production authority."
)


def _read_exact_artifact(project_root: Path, record: dict[str, object]) -> bytes:
    payload = (project_root / str(record["path"])).read_bytes()
    assert len(payload) == record["size_bytes"]
    assert hashlib.sha256(payload).hexdigest() == record["sha256"]
    return payload


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _head_receipt(
    *, checksum: str, key: str, sha256: str, size_bytes: int, version_id: str
) -> dict[str, object]:
    return {
        "checksum_sha256": checksum,
        "checksum_type": "FULL_OBJECT",
        "content_length": size_bytes,
        "key": key,
        "metadata_format": "raw-v1",
        "metadata_sha256": sha256,
        "server_side_encryption": "AES256",
        "status": "PASS",
        "version_id": version_id,
    }


def test_e0038_formal_mapping_and_seal_are_exactly_linked(project_root: Path):
    mapping = json.loads(_read_exact_artifact(project_root, MAPPING_ONLY))
    seal = json.loads(_read_exact_artifact(project_root, MAPPING_SEAL))
    registration = json.loads(_read_exact_artifact(project_root, S3_REGISTRATION))

    assert seal["inventory"] == {"file_count": 1, "files": [MAPPING_ONLY]}
    assert seal["input_hash_ledger"]["mapping_only"] == MAPPING_ONLY
    assert seal["mapping_capture_git_commit"] == mapping["capture_git_commit"]
    assert seal["seal_git_commit"] == mapping["capture_git_commit"]
    assert (
        seal["result_projection_sha256"]
        == (mapping["result_input_binding"]["result_projection_sha256"])
    )
    assert registration["local_artifacts"] == {
        "mapping_only": MAPPING_ONLY,
        "mapping_seal": MAPPING_SEAL,
    }
    assert registration["seal_linkage"] == {
        "mapping_capture_git_commit": mapping["capture_git_commit"],
        "mapping_inventory_identity_matches": True,
        "mapping_ledger_identity_matches": True,
        "result_projection_matches_mapping": True,
        "result_projection_sha256": seal["result_projection_sha256"],
        "seal_git_commit": seal["seal_git_commit"],
    }
    assert mapping["claim_boundary"] == MAPPING_CLAIM_BOUNDARY
    assert seal["claim_boundary"] == SEAL_CLAIM_BOUNDARY
    assert registration["claim_boundary"] == REGISTRATION_CLAIM_BOUNDARY

    exact = mapping["exact_mapping_bundle"]["exact_search"]
    result = exact["mapping_result_without_internal_alias_authority"]
    rows = result["row_mappings"]
    schema_dispositions = result["schema_dispositions"]
    search = result["search"]
    row_statuses = Counter(record["status"] for record in rows)
    schema_statuses = Counter(record["status"] for record in schema_dispositions)
    selected_count = sum(record["selected_report_norm_id"] is not None for record in rows)
    unselected_count = sum(record["selected_report_norm_id"] is None for record in rows)

    assert len(rows) == 64
    assert selected_count == 58
    assert unselected_count == 6
    assert row_statuses == {
        "BEST_PATH_SKIPPED": 2,
        "NO_ADMISSIBLE_PAIR": 4,
        "RESOLVED_ANCHOR": 41,
        "RESOLVED_PATH": 17,
    }
    assert schema_statuses == {
        "MAPPED": 58,
        "UNMATCHED_SCHEMA_NODE": 13,
        "UNMATCHED_SCHEMA_NODE_WITH_SKIPPED_CANDIDATES": 6,
    }
    assert exact["main_search_pruned_states"] == 0
    assert exact["counterfactual_search_pruned_states"] == 0
    assert search["pruned_states"] == 0
    assert search["main_search_pruned_states"] == 0
    assert search["counterfactual_search_pruned_states"] == 0

    assert registration["formal_result_summary"] == {
        "align_invocation_count": mapping["metrics"]["align_invocation_count"],
        "automatic_selection_allowed": result["automatic_selection_allowed"],
        "changed_report_norm_ids": [4375, 5699],
        "core_result_status": result["status"],
        "counterfactual_search_pruned_states": search["counterfactual_search_pruned_states"],
        "counterfactual_searches": search["counterfactual_searches"],
        "dp_cells": search["dp_cells"],
        "exact_interval_count": mapping["metrics"]["exact_interval_count"],
        "exact_status": exact["status"],
        "generated_states": search["generated_states"],
        "main_search_pruned_states": search["main_search_pruned_states"],
        "mapping_result_sha256": _canonical_sha256(result),
        "mapping_state": mapping["state"],
        "plan_certificate": {
            "hard_retained_states_per_cell_cap": search["beam_width_per_dp_cell"],
            "maximum_monotone_signature_bound": exact["plan"]["maximum_monotone_signature_bound"],
            "total_signature_work_bound": exact["plan"]["total_signature_work_bound"],
            "total_signature_work_cap": exact["resource_semantics"][
                "retained_signature_certificate_cap"
            ],
        },
        "result_projection_sha256": result["schema_projection_sha256"],
        "result_pruned_states": search["pruned_states"],
        "retained_states": search["retained_states"],
        "row_mapping_status_counts": dict(sorted(row_statuses.items())),
        "schema_disposition_status_counts": dict(sorted(schema_statuses.items())),
        "schema_node_count": len(schema_dispositions),
        "score_margin": result["score_margin"],
        "sealed_e0037_interval_count": mapping["metrics"]["sealed_e0037_interval_count"],
        "selected_row_count": selected_count,
        "source_row_count": len(rows),
        "unselected_row_count": unselected_count,
    }

    assert set(mapping["input_hash_ledger"]) == {
        "control",
        "e0037_mapping_only",
        "e0037_mapping_policy",
        "e0037_mapping_seal",
        "e0038_alias_policy",
        "e0038_exact_mapping_policy",
        "s3_snapshot_registry",
    }
    assert mapping["access_contract"]["review_or_human_labels_opened"] is False
    assert mapping["access_contract"]["history_or_mongodb_opened"] is False
    assert mapping["access_contract"]["numeric_period_or_unit_features_passed"] is False
    assert mapping["authority"]["mapping_accuracy"] is False
    assert mapping["authority"]["review_or_steward_approval"] is False
    assert seal["access_contract"]["review_opened"] is False
    assert seal["access_contract"]["history_opened"] is False
    assert seal["authority"]["mapping_accuracy"] is False
    assert seal["authority"]["review_or_steward_approval"] is False


def test_e0038_post_seal_s3_registration_is_exact_and_registry_stays_frozen(
    project_root: Path,
):
    registration_bytes = _read_exact_artifact(project_root, S3_REGISTRATION)
    registration = json.loads(registration_bytes)
    assert registration_bytes == (
        json.dumps(
            registration,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    assert set(registration) == {
        "access_contract",
        "authority",
        "claim_boundary",
        "dataset_role",
        "experiment_id",
        "formal_result_summary",
        "format_version",
        "local_artifacts",
        "policy",
        "remote_verification",
        "s3_snapshot",
        "seal_linkage",
        "shared_registry",
        "state",
    }
    assert registration["access_contract"] == {
        "history_artifacts_opened": False,
        "numeric_artifacts_opened": False,
        "review_artifacts_opened": False,
        "seal_identity_validated_before_registration": True,
        "shared_registry_modified": False,
    }
    assert registration["authority"] == {
        "accounting_excel_holdout_or_production": False,
        "mapping_accuracy": False,
        "numeric_period_unit_or_value": False,
        "review_or_steward_approval": False,
        "s3_durability_registration": True,
        "schema_authority": False,
    }
    assert registration["dataset_role"] == "CALIBRATION"
    assert registration["experiment_id"] == "E-0038"
    assert registration["format_version"] == 1
    assert registration["policy"] == "IMMUTABLE_POST_SEAL_S3_REGISTRATION_V1"
    assert registration["state"] == ("E0038_EXACT_MAPPING_IMMUTABLY_REGISTERED_IN_S3_POST_SEAL")

    s3 = registration["s3_snapshot"]
    assert set(s3) == {
        "configuration",
        "content_object",
        "internal_restore",
        "inventory",
        "isolated_hydrate",
        "label",
        "manifest",
        "parent_full_snapshot",
        "policy",
        "run_record",
        "snapshot_id",
        "source_git_commit",
    }
    assert s3["snapshot_id"] == SNAPSHOT_ID
    assert s3["label"] == "e0038-exact-mapping-seal"
    assert s3["policy"] == "S3_BOUNDED_ARTIFACT_SNAPSHOT_V1"
    assert s3["source_git_commit"] == "956854c86e97ac04185999cb20a62501191da81a"
    assert s3["configuration"] == {
        "path": "s3-v1.toml",
        "sha256": "65a844b0f63b7ad57dfb1533db90b833900c0ad08c3500788a323f2f0dfd6e1c",
    }
    assert s3["content_object"] == {
        "disposition": "UPLOADED",
        "key": CONTENT_KEY,
        "logical_path": MAPPING_ONLY["path"],
        "sha256": MAPPING_ONLY["sha256"],
        "size_bytes": MAPPING_ONLY["size_bytes"],
        "version_id": CONTENT_VERSION,
    }
    assert s3["inventory"] == {
        "logical_bytes": MAPPING_ONLY["size_bytes"],
        "logical_file_count": 1,
        "registration_receipt_included": False,
        "seal_included": False,
        "shared_registry_included": False,
        "unique_bytes": MAPPING_ONLY["size_bytes"],
        "unique_object_count": 1,
    }
    assert {s3["content_object"]["logical_path"]} == {MAPPING_ONLY["path"]}
    assert MAPPING_SEAL["path"] != s3["content_object"]["logical_path"]
    assert S3_REGISTRATION["path"] != s3["content_object"]["logical_path"]
    assert SHARED_REGISTRY["path"] != s3["content_object"]["logical_path"]
    assert s3["manifest"] == {
        "initial_restore_gate_state": "PENDING_INDEPENDENT_DOWNLOAD_TEST",
        "key": MANIFEST_KEY,
        "sha256": MANIFEST_SHA256,
        "size_bytes": 3_103,
        "version_id": MANIFEST_VERSION,
    }
    assert s3["run_record"] == {
        "all_incremental_objects_restore_verified": True,
        "key": RUN_KEY,
        "sha256": RUN_SHA256,
        "size_bytes": 1_403,
        "status": "PASS",
        "upload_counts": {
            "logical_file_count": 1,
            "reused_object_count": 0,
            "unique_object_count": 1,
            "uploaded_object_count": 1,
        },
        "version_id": RUN_VERSION,
    }
    assert s3["internal_restore"] == {"status": "PASS"}
    assert s3["isolated_hydrate"] == {
        "first_hydrate": {
            "byte_equal_to_local": True,
            "restored_bytes": MAPPING_ONLY["size_bytes"],
            "restored_file_count": 1,
            "reused_file_count": 0,
            "sha256_matches": True,
            "size_bytes_matches": True,
        },
        "logical_path": MAPPING_ONLY["path"],
        "second_hydrate": {
            "byte_equal_to_local": True,
            "restored_bytes": 0,
            "restored_file_count": 0,
            "reused_file_count": 1,
            "sha256_matches": True,
            "size_bytes_matches": True,
        },
        "status": "PASS",
    }
    assert s3["parent_full_snapshot"] == {
        "full_content_stream_verified": True,
        "manifest_key": (
            f"bctc-ai/snapshots/{PARENT_SNAPSHOT_ID}/manifest-{PARENT_MANIFEST_SHA256}.json"
        ),
        "manifest_sha256": PARENT_MANIFEST_SHA256,
        "production_status": "PASS",
        "restore_status": "PASS",
        "run_record_key": (f"bctc-ai/runs/{PARENT_SNAPSHOT_ID}/run-{PARENT_RUN_SHA256}.json"),
        "run_record_sha256": PARENT_RUN_SHA256,
        "snapshot_id": PARENT_SNAPSHOT_ID,
    }

    remote = registration["remote_verification"]
    assert remote == {
        "bucket_preflight": {
            "bucket_identity": {
                "bucket": "test-s3-duylv",
                "expected_owner_verified": True,
                "prefix": "bctc-ai",
                "region": "us-east-1",
            },
            "default_encryption": "AES256",
            "public_access_block": {
                "block_public_acls": True,
                "block_public_policy": True,
                "ignore_public_acls": True,
                "restrict_public_buckets": True,
            },
            "status": "PASS",
            "versioning_status": "Enabled",
        },
        "head_objects": {
            "content_object": _head_receipt(
                checksum="ixB00spX78scbaEjYVrOhkOAabTVgbmvtLbkz78Bqek=",
                key=CONTENT_KEY,
                sha256=str(MAPPING_ONLY["sha256"]),
                size_bytes=int(MAPPING_ONLY["size_bytes"]),
                version_id=CONTENT_VERSION,
            ),
            "manifest": _head_receipt(
                checksum="m5YWOLgKhSVvaSYSCrcfsR3NGsjimVEQ4TKFpUU5qV4=",
                key=MANIFEST_KEY,
                sha256=MANIFEST_SHA256,
                size_bytes=3_103,
                version_id=MANIFEST_VERSION,
            ),
            "run_record": _head_receipt(
                checksum="xpdCNBKStVR6cVTi2w78hA42vsrQ/Hcv9R3tDwlQCko=",
                key=RUN_KEY,
                sha256=RUN_SHA256,
                size_bytes=1_403,
                version_id=RUN_VERSION,
            ),
        },
        "status": "PASS",
    }

    registry_bytes = _read_exact_artifact(project_root, SHARED_REGISTRY)
    registry_records = [json.loads(line) for line in registry_bytes.decode("utf-8").splitlines()]
    assert registration["shared_registry"] == {
        "not_registered_there": True,
        "path": SHARED_REGISTRY["path"],
        "sha256": SHARED_REGISTRY["sha256"],
        "size_bytes": SHARED_REGISTRY["size_bytes"],
        "unchanged": True,
    }
    assert not any(record.get("artifact_snapshot_id") == SNAPSHOT_ID for record in registry_records)
