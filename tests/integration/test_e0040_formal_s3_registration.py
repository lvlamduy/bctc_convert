from __future__ import annotations

import base64
import copy
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

MAPPING = {
    "path": "output/calibration/e0040-mbb-cdkt-formal-mapping/mapping_only.json",
    "sha256": "8def983007fc3aacf59351395426d5246ad3f28d605442f590de55eaf396cb0d",
    "size_bytes": 1_157_172,
}
SEAL = {
    "path": "docs/experiments/E-0040-mbb-cdkt-formal-mapping-seal.json",
    "sha256": "68306f7f540faa77d6e2e383927eae23fc3724cfdc8c53cded978a86f3a00b29",
    "size_bytes": 7_611,
}
REGISTRATION = {
    "path": "docs/experiments/E-0040-mbb-cdkt-formal-mapping-s3-registration.json",
    "sha256": "f38d9a1bbed4ec48e2156d441e5c76c6e6d82b0771208de3eef92d96173dd4b5",
    "size_bytes": 13_360,
}
SHARED_REGISTRY = {
    "path": "data/registered/s3_artifact_snapshot_registry.jsonl",
    "sha256": "25da6b205a775d87eca8e4ffe55e3f762ee64e92cbb7190c2834708a7de0d78d",
    "size_bytes": 6_050,
}
CONFIGURATION = {
    "path": "config/backup/s3-v1.toml",
    "sha256": "65a844b0f63b7ad57dfb1533db90b833900c0ad08c3500788a323f2f0dfd6e1c",
    "size_bytes": 1_569,
}

CAPTURE_COMMIT = "18aca8942faf5d47e1ac5f049045d7a7a297b5fc"
SNAPSHOT_SOURCE_COMMIT = "0049997c37df3d75941caf258f03c665b8784df6"
POST_SNAPSHOT_TEST_COMMIT = "f54e39f0af6e68bef2662d5dc4f9fa74b7bd296d"
SNAPSHOT_ID = "20260808T011052Z-e0040-formal-mapping-seal-8def983007fc"
CONTENT_KEY = (
    "bctc-ai/objects/sha256/8d/8def983007fc3aacf59351395426d5246ad3f28d605442f590de55eaf396cb0d"
)
CONTENT_VERSION = "9LL0Geymo8YSTtl2k2rOdVx43QRE4DXZ"
MANIFEST_SHA256 = "adb8ea8c6a35e7df8c0756b8fc646d5565344a4da31513bc16690eddc508037b"
MANIFEST_KEY = f"bctc-ai/artifact-snapshots/{SNAPSHOT_ID}/manifest-{MANIFEST_SHA256}.json"
MANIFEST_VERSION = "3eiqX6Ai3IyxMTshHSjBFQL0WFiLuU_U"
RUN_SHA256 = "8e597ddc9288a096076bc5006e2d550226a64e97883aafabd1239eeb8465424b"
RUN_KEY = f"bctc-ai/artifact-runs/{SNAPSHOT_ID}/run-{RUN_SHA256}.json"
RUN_VERSION = "1HJ_ReAdnojLxqixC_IuIIRMg4qpS7SI"
PARENT_SNAPSHOT_ID = "20260806T050030130746Z-4a469fab2334"
PARENT_MANIFEST_SHA256 = "74be9ea09905f0c7842d5a0b46bfe44f3fc5f32cc2c15b5040efcc4e99e8981b"
PARENT_RUN_SHA256 = "24eb066b51443066dfd14538ef7aeb21e9b700cc6ce995c49e56ff23b6701b04"


def _read_exact(project_root: Path, record: dict[str, object]) -> bytes:
    payload = (project_root / str(record["path"])).read_bytes()
    assert len(payload) == record["size_bytes"]
    assert hashlib.sha256(payload).hexdigest() == record["sha256"]
    return payload


def _reject_constant(value: str) -> None:
    raise AssertionError(f"non-finite JSON constant: {value}")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        assert key not in result, f"duplicate JSON key: {key}"
        result[key] = value
    return result


def _decode(payload: bytes) -> dict[str, Any]:
    result = json.loads(
        payload,
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=_reject_constant,
    )
    assert type(result) is dict
    return result


def _pretty(payload: object) -> bytes:
    return (
        json.dumps(payload, allow_nan=False, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode()


def _checksum(sha256: str) -> str:
    return base64.b64encode(bytes.fromhex(sha256)).decode("ascii")


def _scalar_paths(value: object, prefix: tuple[str | int, ...] = ()):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _scalar_paths(child, (*prefix, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _scalar_paths(child, (*prefix, index))
    else:
        yield prefix


def _mutate_at_path(value: dict[str, Any], path: tuple[str | int, ...]) -> dict[str, Any]:
    mutated = copy.deepcopy(value)
    cursor: Any = mutated
    for component in path[:-1]:
        cursor = cursor[component]
    leaf = path[-1]
    current = cursor[leaf]
    if isinstance(current, bool):
        cursor[leaf] = not current
    elif isinstance(current, int):
        cursor[leaf] = current + 1
    elif isinstance(current, str):
        cursor[leaf] = f"{current}__MUTATED__"
    else:
        raise AssertionError(f"unsupported registration scalar: {type(current).__name__}")
    return mutated


def test_e0040_postseal_registration_is_exact_canonical_and_linked(project_root: Path):
    mapping_bytes = _read_exact(project_root, MAPPING)
    seal_bytes = _read_exact(project_root, SEAL)
    registration_bytes = _read_exact(project_root, REGISTRATION)
    mapping = _decode(mapping_bytes)
    seal = _decode(seal_bytes)
    registration = _decode(registration_bytes)

    assert registration_bytes == _pretty(registration)
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
    assert registration["local_artifacts"] == {
        "mapping_only": MAPPING,
        "mapping_seal": SEAL,
    }
    assert seal["inventory"] == {"file_count": 1, "files": [MAPPING]}
    assert seal["input_hash_ledger"]["mapping_only"] == MAPPING
    assert mapping["capture_git_commit"] == CAPTURE_COMMIT
    assert seal["mapping_capture_git_commit"] == CAPTURE_COMMIT
    assert seal["seal_git_commit"] == CAPTURE_COMMIT
    assert registration["seal_linkage"] == {
        "mapping_canonical_bytes_validated": True,
        "mapping_capture_git_commit": CAPTURE_COMMIT,
        "mapping_inventory_identity_matches": True,
        "mapping_ledger_identity_matches": True,
        "mapping_metrics_match_seal": True,
        "mapping_result_receipts_match_seal": True,
        "mapping_seal_git_commit": CAPTURE_COMMIT,
        "post_snapshot_test_only_commit": POST_SNAPSHOT_TEST_COMMIT,
        "result_projection_matches_mapping": True,
        "result_projection_sha256": seal["result_projection_sha256"],
        "s3_source_git_commit_matches_seal_artifact_commit": True,
        "seal_artifact_git_commit": SNAPSHOT_SOURCE_COMMIT,
    }
    assert mapping["metrics"] == seal["metrics"]
    assert mapping["result_receipts"] == seal["result_receipts"]

    metrics = mapping["metrics"]
    receipts = mapping["result_receipts"]
    assert registration["formal_result_summary"] == {
        "all_intervals_exhaustive": metrics["all_intervals_exhaustive"],
        "all_pruning_counts_zero": metrics["all_pruning_counts_zero"],
        "base_collision_pair_count": metrics["base_collision_pair_count"],
        "baseline_interval_count": metrics["baseline_interval_count"],
        "baseline_selected_count": metrics["baseline_selected_count"],
        "challenger_result_sha256": receipts["challenger_result_sha256"],
        "final_interval_count": metrics["final_interval_count"],
        "final_result_sha256": receipts["final_result_sha256"],
        "final_row_status_counts": metrics["final_row_status_counts"],
        "final_selected_count": metrics["final_selected_count"],
        "final_selected_pairs_sha256": receipts["final_selected_pairs_sha256"],
        "internal_role_repair_selected_count": metrics["internal_role_repair_selected_count"],
        "mapper_invocation_count": metrics["mapper_invocation_count"],
        "mapping_state": mapping["state"],
        "mapping_status": seal["mapping_status"],
        "new_collision_pair_count": metrics["new_collision_pair_count"],
        "normalization_changed_schema_node_count": metrics[
            "normalization_changed_schema_node_count"
        ],
        "normalization_derived_key_count": metrics["normalization_derived_key_count"],
        "result_collision_pair_count": metrics["result_collision_pair_count"],
        "result_projection_sha256": seal["result_projection_sha256"],
        "schema_node_count": metrics["schema_node_count"],
        "selected_anchor_count": metrics["selected_anchor_count"],
        "selected_path_count": metrics["selected_path_count"],
        "source_only_structural_count": metrics["source_only_structural_count"],
        "source_row_count": metrics["source_row_count"],
    }
    final_rows = mapping["challenger_result"]["final_result"]["row_mappings"]
    assert sum(row["selected_report_norm_id"] is not None for row in final_rows) == 61
    assert Counter(row["status"] for row in final_rows) == {
        "NO_ADMISSIBLE_PAIR": 3,
        "RESOLVED_ANCHOR": 43,
        "RESOLVED_PATH": 18,
    }
    assert len(mapping["challenger_result"]["source_only_structural_rows"]) == 3

    assert registration["access_contract"] == {
        "history_artifacts_opened": False,
        "holdout_artifacts_opened": False,
        "numeric_artifacts_opened": False,
        "review_artifacts_opened": False,
        "seal_identity_validated_before_registration": True,
        "shared_registry_modified": False,
    }
    assert registration["authority"] == {
        "accounting_or_excel": False,
        "automatic_mapping_adoption": False,
        "exact_mapping_hash_identity": True,
        "exact_restore_hash_identity": True,
        "holdout_or_production": False,
        "mapping_accuracy": False,
        "numeric_period_unit_scope": False,
        "review_or_steward_approval": False,
        "s3_durability_registration": True,
        "schema_authority": False,
    }
    assert registration["dataset_role"] == "CALIBRATION"
    assert registration["experiment_id"] == "E-0040"
    assert registration["format_version"] == 1
    assert registration["policy"] == "IMMUTABLE_POST_SEAL_S3_REGISTRATION_V1"
    assert registration["state"] == ("E0040_FORMAL_MAPPING_IMMUTABLY_REGISTERED_IN_S3_POST_SEAL")

    committed_seal = subprocess.run(
        ["git", "-C", str(project_root), "show", f"{SNAPSHOT_SOURCE_COMMIT}:{SEAL['path']}"],
        check=True,
        capture_output=True,
    ).stdout
    assert committed_seal == seal_bytes
    parent = subprocess.run(
        ["git", "-C", str(project_root), "rev-parse", f"{POST_SNAPSHOT_TEST_COMMIT}^"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert parent == SNAPSHOT_SOURCE_COMMIT
    changed = subprocess.run(
        [
            "git",
            "-C",
            str(project_root),
            "diff",
            "--name-only",
            SNAPSHOT_SOURCE_COMMIT,
            POST_SNAPSHOT_TEST_COMMIT,
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert changed == ["tests/integration/test_e0040_formal_result.py"]


def test_e0040_s3_receipt_is_exact_one_file_and_registry_stays_frozen(project_root: Path):
    registration = _decode(_read_exact(project_root, REGISTRATION))
    s3 = registration["s3_snapshot"]
    remote = registration["remote_verification"]
    assert set(s3) == {
        "configuration",
        "content_object",
        "created_at_utc",
        "internal_restore",
        "inventory",
        "isolated_hydrate",
        "label",
        "manifest",
        "parent_full_snapshot",
        "policy",
        "run_record",
        "snapshot_id",
        "source_git_branch",
        "source_git_commit",
        "source_git_remote",
    }
    assert s3["snapshot_id"] == SNAPSHOT_ID
    assert s3["label"] == "e0040-formal-mapping-seal"
    assert s3["policy"] == "S3_BOUNDED_ARTIFACT_SNAPSHOT_V1"
    assert s3["created_at_utc"] == "2026-08-08T01:10:52.608634+00:00"
    assert s3["source_git_branch"] == "codex/rebuild-bootstrap"
    assert s3["source_git_commit"] == SNAPSHOT_SOURCE_COMMIT
    assert s3["source_git_remote"] == "https://github.com/lvlamduy/bctc_convert.git"
    assert s3["configuration"] == {
        "manifest_path": "s3-v1.toml",
        **CONFIGURATION,
    }
    _read_exact(project_root, CONFIGURATION)
    assert s3["content_object"] == {
        "asset_class": "generated_output",
        "disposition": "UPLOADED",
        "key": CONTENT_KEY,
        "logical_path": MAPPING["path"],
        "sha256": MAPPING["sha256"],
        "size_bytes": MAPPING["size_bytes"],
        "version_id": CONTENT_VERSION,
    }
    assert s3["inventory"] == {
        "diagnostic_included": False,
        "logical_bytes": MAPPING["size_bytes"],
        "logical_file_count": 1,
        "registration_receipt_included": False,
        "seal_included": False,
        "shared_registry_included": False,
        "unique_bytes": MAPPING["size_bytes"],
        "unique_object_count": 1,
    }
    assert s3["manifest"] == {
        "format_version": 1,
        "key": MANIFEST_KEY,
        "policy": "S3_BOUNDED_ARTIFACT_SNAPSHOT_V1",
        "restore_gate": {
            "all_incremental_objects_download_required": True,
            "parent_full_content_restore_required": True,
            "state": "PENDING_INDEPENDENT_DOWNLOAD_TEST",
        },
        "selection": [MAPPING["path"]],
        "sha256": MANIFEST_SHA256,
        "size_bytes": 3_110,
        "version_id": MANIFEST_VERSION,
    }
    assert s3["run_record"] == {
        "all_incremental_objects_restore_verified": True,
        "completed_at_utc": "2026-08-08T01:11:08.687981+00:00",
        "key": RUN_KEY,
        "manifest": {"key": MANIFEST_KEY, "sha256": MANIFEST_SHA256},
        "sha256": RUN_SHA256,
        "size_bytes": 1_405,
        "status": "PASS",
        "upload_counts": {
            "logical_file_count": 1,
            "reused_object_count": 0,
            "unique_object_count": 1,
            "uploaded_object_count": 1,
        },
        "version_id": RUN_VERSION,
    }
    assert s3["internal_restore"] == {"restore_verified": True, "status": "PASS"}
    assert s3["isolated_hydrate"] == {
        "first_hydrate": {
            "byte_equal_to_local": True,
            "restored_bytes": MAPPING["size_bytes"],
            "restored_file_count": 1,
            "reused_file_count": 0,
            "sha256_matches": True,
            "size_bytes_matches": True,
        },
        "logical_path": MAPPING["path"],
        "second_hydrate": {
            "byte_equal_to_local": True,
            "destination_bytes_unchanged": True,
            "destination_device_unchanged": True,
            "destination_inode_unchanged": True,
            "destination_mtime_unchanged": True,
            "destination_size_unchanged": True,
            "matching_file_reused_without_overwrite": True,
            "restored_bytes": 0,
            "restored_file_count": 0,
            "reused_file_count": 1,
            "sha256_matches": True,
            "size_bytes_matches": True,
        },
        "status": "PASS",
    }
    assert {s3["content_object"]["logical_path"]} == {MAPPING["path"]}
    assert SEAL["path"] != s3["content_object"]["logical_path"]
    assert REGISTRATION["path"] != s3["content_object"]["logical_path"]
    assert SHARED_REGISTRY["path"] != s3["content_object"]["logical_path"]

    parent = s3["parent_full_snapshot"]
    assert parent["snapshot_id"] == PARENT_SNAPSHOT_ID
    assert parent["production_status"] == parent["restore_status"] == "PASS"
    assert parent["full_content_stream_verified"] is True
    assert parent["manifest"]["sha256"] == PARENT_MANIFEST_SHA256
    assert parent["manifest"]["metadata_sha256"] == PARENT_MANIFEST_SHA256
    assert parent["manifest"]["checksum_sha256"] == _checksum(PARENT_MANIFEST_SHA256)
    assert parent["manifest"]["size_bytes"] == 3_044_426
    assert parent["manifest"]["version_id"] == "8pu1ufCeFQ4RDdkwXxyjBZY.ljSECvCE"
    assert parent["run_record"]["sha256"] == PARENT_RUN_SHA256
    assert parent["run_record"]["metadata_sha256"] == PARENT_RUN_SHA256
    assert parent["run_record"]["checksum_sha256"] == _checksum(PARENT_RUN_SHA256)
    assert parent["run_record"]["size_bytes"] == 1_192
    assert parent["run_record"]["version_id"] == "dLD5zPHg7rHOERptvYt37WxKSCbPlSvl"

    assert set(remote) == {"bucket_preflight", "head_objects", "prefix_inventory", "status"}
    assert remote["status"] == "PASS"
    assert remote["prefix_inventory"] == {
        "manifest_object_count": 1,
        "run_record_object_count": 1,
    }
    assert remote["bucket_preflight"] == {
        "authenticated_principal": "arn:aws:iam::037827769459:user/vps_username",
        "aws_cli": ("aws-cli/2.36.18 Python/3.14.6 Linux/6.6.0-hiveos exe/x86_64.ubuntu.22"),
        "bucket_identity": {
            "bucket": "test-s3-duylv",
            "expected_owner": "037827769459",
            "expected_owner_verified": True,
            "prefix": "bctc-ai",
            "region": "us-east-1",
        },
        "content_addressing": "SHA256",
        "default_encryption": ["AES256"],
        "public_access_block": {
            "block_public_acls": True,
            "block_public_policy": True,
            "ignore_public_acls": True,
            "restrict_public_buckets": True,
        },
        "request_safety": {
            "delete_operations_enabled": False,
            "overwrite_operations_enabled": False,
            "put_precondition": "If-None-Match: *",
        },
        "server_side_checksum": "SHA256",
        "status": "PASS",
        "versioning_status": "Enabled",
    }
    heads = remote["head_objects"]
    assert set(heads) == {"content_object", "manifest", "run_record"}
    for name, sha256, size, key, version, checksum in (
        (
            "content_object",
            MAPPING["sha256"],
            MAPPING["size_bytes"],
            CONTENT_KEY,
            CONTENT_VERSION,
            "je+YMAf8Oqz1k1E5VCbVJGrT8o1gVEL1kN5V6vOWyw0=",
        ),
        (
            "manifest",
            MANIFEST_SHA256,
            3_110,
            MANIFEST_KEY,
            MANIFEST_VERSION,
            "rbjqjGo159+MB1a4/GRtVWU0Sk2jFRO8FmkO3cUIA3s=",
        ),
        (
            "run_record",
            RUN_SHA256,
            1_405,
            RUN_KEY,
            RUN_VERSION,
            "jll93JKIoJYHa8UAbi1VAiamTpeIOq+r0SOe64RlQks=",
        ),
    ):
        head = heads[name]
        assert head["checksum_sha256"] == checksum == _checksum(str(sha256))
        assert head["checksum_type"] == "FULL_OBJECT"
        assert head["content_length"] == size
        assert head["key"] == key
        assert head["metadata_format"] == "raw-v1"
        assert head["metadata_sha256"] == sha256
        assert head["server_side_encryption"] == "AES256"
        assert head["status"] == "PASS"
        assert head["version_id"] == version
        assert head["exact_version_get_sha256_matches"] is True
        assert head["exact_version_get_size_matches"] is True
    assert heads["content_object"]["byte_equal_to_local"] is True
    assert heads["content_object"]["is_latest"] is True
    assert heads["content_object"]["only_version"] is True

    registry_bytes = _read_exact(project_root, SHARED_REGISTRY)
    registry_records = [json.loads(line) for line in registry_bytes.decode().splitlines()]
    assert registration["shared_registry"] == {
        "appended": False,
        "not_registered_there": True,
        **SHARED_REGISTRY,
        "unchanged": True,
    }
    assert not any(record.get("artifact_snapshot_id") == SNAPSHOT_ID for record in registry_records)


def test_e0040_registration_is_scalar_mutation_complete(project_root: Path):
    registration_bytes = _read_exact(project_root, REGISTRATION)
    registration = _decode(registration_bytes)
    paths = list(_scalar_paths(registration))
    assert len(paths) == len(set(paths)) == 228
    for path in paths:
        mutated_bytes = _pretty(_mutate_at_path(registration, path))
        assert mutated_bytes != registration_bytes
        assert hashlib.sha256(mutated_bytes).hexdigest() != REGISTRATION["sha256"]

    added = copy.deepcopy(registration)
    added["mapping_accuracy"] = True
    removed = copy.deepcopy(registration)
    del removed["state"]
    assert hashlib.sha256(_pretty(added)).hexdigest() != REGISTRATION["sha256"]
    assert hashlib.sha256(_pretty(removed)).hexdigest() != REGISTRATION["sha256"]
