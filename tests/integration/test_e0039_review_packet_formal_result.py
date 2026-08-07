from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

PACKET = {
    "path": "output/calibration/e0039-mbb-cdkt-review-packet/evidence_packet.json",
    "sha256": "04c6b0509713f46423b03857a5e509d36cfa95d9ffd34bbe981f564915cdf93d",
    "size_bytes": 74_601,
}
PACKET_SEAL = {
    "path": "docs/experiments/E-0039-mbb-cdkt-review-packet-seal.json",
    "sha256": "2e876af8e0b4128180dce9c1ed6750b587485112320d06cb219dd7fb20e857a5",
    "size_bytes": 8_416,
}
S3_REGISTRATION = {
    "path": "docs/experiments/E-0039-mbb-cdkt-review-packet-s3-registration.json",
    "sha256": "b0821a3c7d01041f8f179af0f387b1b38f1fa8f3bb06739f99528e0c9f6a09d9",
    "size_bytes": 11_591,
}
SHARED_REGISTRY = {
    "path": "data/registered/s3_artifact_snapshot_registry.jsonl",
    "sha256": "25da6b205a775d87eca8e4ffe55e3f762ee64e92cbb7190c2834708a7de0d78d",
    "size_bytes": 6_050,
}

PACKET_CAPTURE_COMMIT = "35d02d62e96b2fa449f4eb8ee6a13982a5f2fe75"
SEAL_CAPTURE_COMMIT = "9a1b3f7c58cbcfdea0c006bcf7365a2ec9a3c144"
SEAL_ARTIFACT_COMMIT = "2dd5072fd280e8520ae80d7c47ce12fecfc834ac"
SNAPSHOT_ID = "20260807T223520Z-e0039-review-packet-seal-04c6b0509713"
CONTENT_KEY = (
    "bctc-ai/objects/sha256/04/04c6b0509713f46423b03857a5e509d36cfa95d9ffd34bbe981f564915cdf93d"
)
CONTENT_VERSION = "3a_v4tyJO3klOBvDpdOVOut0KypBoOLl"
MANIFEST_SHA256 = "bea33b3ccf70f05db7f60501da83c123da6a184509b1acc32d4f67f4f1a0c773"
MANIFEST_KEY = f"bctc-ai/artifact-snapshots/{SNAPSHOT_ID}/manifest-{MANIFEST_SHA256}.json"
MANIFEST_VERSION = "AkVtmOpMq95PfzjAF1_uJsDlWozRnjPI"
RUN_SHA256 = "6de1ee3681659c1b75a130e95219f64b85055fa701f14a727b31230c01df5b07"
RUN_KEY = f"bctc-ai/artifact-runs/{SNAPSHOT_ID}/run-{RUN_SHA256}.json"
RUN_VERSION = "8_WtJO_ypIBnlNqtWD9ShRugxET5PR3."
PARENT_SNAPSHOT_ID = "20260806T050030130746Z-4a469fab2334"
PARENT_MANIFEST_SHA256 = "74be9ea09905f0c7842d5a0b46bfe44f3fc5f32cc2c15b5040efcc4e99e8981b"
PARENT_RUN_SHA256 = "24eb066b51443066dfd14538ef7aeb21e9b700cc6ce995c49e56ff23b6701b04"

ROW_IDS = [
    "page-0003-row-002-label",
    "page-0003-row-003-label",
    "page-0004-row-000-label",
    "page-0004-row-002-label",
    "page-0004-row-013-label",
    "page-0004-row-023-label",
]
ALIAS_IDS = [
    "CDKT_4375_TOTAL_ASSETS_BANKING_WORDING",
    "CDKT_5699_NCI_POSSESSIVE_PARTICLE",
]
ROW_DECISIONS = [
    "MAP_EXISTING_REPORT_NORM_ID",
    "OUT_OF_SCOPE_FOR_TARGET_TEMPLATE",
    "REQUIRES_SCHEMA_CHANGE",
    "SOURCE_ONLY_STRUCTURAL_ROW",
    "UNRESOLVED",
]
ALIAS_DECISIONS = ["APPROVE_ID_SCOPED_ALIAS", "DEFER", "REJECT", "REPLACE"]
REGISTRATION_CLAIM_BOUNDARY = (
    "This immutable post-seal artifact registers only S3 durability and exact restore "
    "facts for the already hash-sealed, answer-free E-0039 calibration pre-decision "
    "packet. It does not add or imply row adjudication, schema-steward decision, alias "
    "approval, mapping adoption or accuracy, schema, numeric, period, unit, accounting, "
    "Excel, history, MongoDB, holdout, or production authority, and it opens no response "
    "answer or prior-review artifact."
)


def _read_exact_artifact(project_root: Path, record: dict[str, object]) -> bytes:
    payload = (project_root / str(record["path"])).read_bytes()
    assert len(payload) == record["size_bytes"]
    assert hashlib.sha256(payload).hexdigest() == record["sha256"]
    return payload


def _pretty_json(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _compact_json(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


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


def _scalar_paths(value: object, prefix: tuple[str | int, ...] = ()):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _scalar_paths(child, (*prefix, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _scalar_paths(child, (*prefix, index))
    else:
        yield prefix


def _mutate_scalar(value: object) -> object:
    if value is None:
        return "MUTATED_NULL"
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, str):
        return f"{value}__MUTATED__"
    raise AssertionError(f"unsupported registration scalar: {type(value).__name__}")


def _mutate_at_path(value: dict[str, Any], path: tuple[str | int, ...]) -> dict[str, Any]:
    mutated = copy.deepcopy(value)
    cursor: Any = mutated
    for component in path[:-1]:
        cursor = cursor[component]
    leaf = path[-1]
    cursor[leaf] = _mutate_scalar(cursor[leaf])
    return mutated


def test_e0039_packet_seal_and_registration_are_exactly_linked(project_root: Path):
    packet_bytes = _read_exact_artifact(project_root, PACKET)
    seal_bytes = _read_exact_artifact(project_root, PACKET_SEAL)
    registration_bytes = _read_exact_artifact(project_root, S3_REGISTRATION)
    packet = json.loads(packet_bytes)
    seal = json.loads(seal_bytes)
    registration = json.loads(registration_bytes)

    assert packet_bytes == _compact_json(packet)
    assert seal_bytes == _pretty_json(seal)
    assert registration_bytes == _pretty_json(registration)
    assert set(packet) == {
        "access_contract",
        "alias_steward_packet",
        "authority",
        "blank_response_contracts",
        "claim_boundary",
        "deterministic_replay",
        "evidence_identity",
        "identity",
        "input_artifacts",
        "row_review_packet",
        "state",
    }
    assert set(seal) == {
        "access_contract",
        "authority",
        "claim_boundary",
        "dataset_role",
        "experiment_id",
        "format_version",
        "input_hash_ledger",
        "inventory",
        "packet_capture_git_commit",
        "packet_contract",
        "replay",
        "seal_git_commit",
        "seal_git_dirty",
        "state",
    }

    assert packet["identity"]["capture_git_commit"] == PACKET_CAPTURE_COMMIT
    assert packet["identity"]["capture_git_dirty"] is False
    assert packet["state"] == "E0039_PREDECISION_REVIEW_AND_STEWARD_EVIDENCE_PACKET"
    assert seal["inventory"] == {"file_count": 1, "files": [PACKET]}
    assert seal["packet_capture_git_commit"] == PACKET_CAPTURE_COMMIT
    assert seal["seal_git_commit"] == SEAL_CAPTURE_COMMIT
    assert seal["seal_git_dirty"] is False
    assert registration["local_artifacts"] == {
        "evidence_packet": PACKET,
        "packet_seal": PACKET_SEAL,
    }
    assert registration["formal_result_summary"] == seal["packet_contract"]
    assert registration["seal_linkage"] == {
        "packet_canonical_bytes_validated": True,
        "packet_capture_git_commit": PACKET_CAPTURE_COMMIT,
        "packet_contract_matches_seal": True,
        "packet_evidence_sections_sha256": (
            "a4cd5cb429d5894424c9e50fa8c559ef6ad042cafc940da73b4cd2ed0d831185"
        ),
        "packet_inventory_identity_matches": True,
        "packet_ledger_identity_matches": True,
        "packet_seal_artifact_git_commit": SEAL_ARTIFACT_COMMIT,
        "packet_seal_capture_git_commit": SEAL_CAPTURE_COMMIT,
        "s3_source_git_commit_matches_seal_artifact_commit": True,
    }

    contracts = packet["blank_response_contracts"]
    row_contract = contracts["row_adjudication"]
    alias_contract = contracts["alias_stewardship"]
    assert contracts["vocabulary_ordering"] == "ALPHABETIC_NON_PREFERENTIAL_NO_DEFAULT"
    assert row_contract["allowed_vocabulary"] == {
        "authority_role": ["INDEPENDENT_ROW_ADJUDICATOR"],
        "decision": ROW_DECISIONS,
    }
    assert alias_contract["allowed_vocabulary"] == {
        "authority_role": ["REVIEW_INDEPENDENT_SCHEMA_STEWARD"],
        "decision": ALIAS_DECISIONS,
    }
    assert all(value is None for value in row_contract["template"].values())
    assert all(value is None for value in alias_contract["template"].values())

    row_packet = packet["row_review_packet"]
    alias_packet = packet["alias_steward_packet"]
    assert row_packet["row_count"] == 6
    assert row_packet["row_ids"] == ROW_IDS
    assert [row["row_id"] for row in row_packet["rows"]] == ROW_IDS
    assert row_packet["authority_required"] == "INDEPENDENT_ROW_ADJUDICATOR"
    assert row_packet["decision_status"] == "NOT_STARTED_BLANK_RESPONSE_REQUIRED"
    assert alias_packet["candidate_count"] == 2
    assert alias_packet["candidate_ids"] == ALIAS_IDS
    assert [row["candidate_id"] for row in alias_packet["rows"]] == ALIAS_IDS
    assert alias_packet["authority_required"] == "REVIEW_INDEPENDENT_SCHEMA_STEWARD"
    assert alias_packet["decision_status"] == "NOT_STARTED_BLANK_RESPONSE_REQUIRED"

    summary = registration["formal_result_summary"]
    assert summary["row_count"] == 6
    assert summary["row_ids"] == ROW_IDS
    assert summary["row_response_vocabulary"]["decision"] == ROW_DECISIONS
    assert summary["alias_candidate_count"] == 2
    assert summary["alias_candidate_ids"] == ALIAS_IDS
    assert summary["alias_response_vocabulary"]["decision"] == ALIAS_DECISIONS
    assert summary["all_response_template_values_null"] is True
    assert summary["recommended_or_default_response_fields_present"] is False
    assert summary["row_and_alias_authorities_separate"] is True


def test_e0039_capture_seal_and_publication_commits_are_direct(project_root: Path):
    def parent_of(commit: str) -> str:
        return subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", f"{commit}^"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    assert parent_of(SEAL_CAPTURE_COMMIT) == PACKET_CAPTURE_COMMIT
    assert parent_of(SEAL_ARTIFACT_COMMIT) == SEAL_CAPTURE_COMMIT


def test_e0039_registration_is_canonical_and_scalar_mutation_complete(project_root: Path):
    registration_bytes = _read_exact_artifact(project_root, S3_REGISTRATION)
    registration = json.loads(registration_bytes)
    assert registration_bytes == _pretty_json(registration)

    paths = list(_scalar_paths(registration))
    assert len(paths) == 196
    assert len(paths) == len(set(paths))
    for path in paths:
        mutated = _mutate_at_path(registration, path)
        assert _pretty_json(mutated) != registration_bytes
        assert hashlib.sha256(_pretty_json(mutated)).hexdigest() != S3_REGISTRATION["sha256"]

    added = copy.deepcopy(registration)
    added["recommended_answer"] = 4311
    removed = copy.deepcopy(registration)
    del removed["state"]
    assert hashlib.sha256(_pretty_json(added)).hexdigest() != S3_REGISTRATION["sha256"]
    assert hashlib.sha256(_pretty_json(removed)).hexdigest() != S3_REGISTRATION["sha256"]


def test_e0039_postseal_s3_registration_is_exact_and_registry_stays_frozen(
    project_root: Path,
):
    registration = json.loads(_read_exact_artifact(project_root, S3_REGISTRATION))
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
        "full_page_render_opened": False,
        "history_or_mongodb_artifact_opened": False,
        "holdout_artifact_opened": False,
        "numeric_or_accounting_artifact_opened": False,
        "packet_evidence_inputs_reopened": False,
        "packet_opened_after_seal_identity_validation": True,
        "prior_review_artifact_or_answer_opened": False,
        "qwen_raw_rejected_or_token_output_opened": False,
        "response_answer_opened": False,
        "review_or_steward_decision_invocation_count": 0,
        "seal_identity_validated_before_registration": True,
        "shared_registry_modified": False,
    }
    assert registration["authority"] == {
        "accounting_or_excel": False,
        "automatic_mapping_adoption": False,
        "blank_predecision_contract_identity": True,
        "exact_packet_hash_identity": True,
        "history_or_mongodb": False,
        "holdout_or_production": False,
        "mapping_accuracy": False,
        "numeric_period_or_unit": False,
        "row_adjudication_completed": False,
        "s3_durability_registration": True,
        "schema_alias_approval": False,
        "schema_authority": False,
        "schema_steward_decision_completed": False,
    }
    assert registration["claim_boundary"] == REGISTRATION_CLAIM_BOUNDARY
    assert registration["dataset_role"] == "CALIBRATION"
    assert registration["experiment_id"] == "E-0039"
    assert registration["format_version"] == 1
    assert registration["policy"] == "IMMUTABLE_POST_SEAL_S3_REGISTRATION_V1"
    assert registration["state"] == (
        "E0039_PREDECISION_REVIEW_PACKET_IMMUTABLY_REGISTERED_IN_S3_POST_SEAL"
    )

    s3 = registration["s3_snapshot"]
    assert s3 == {
        "configuration": {
            "path": "s3-v1.toml",
            "sha256": "65a844b0f63b7ad57dfb1533db90b833900c0ad08c3500788a323f2f0dfd6e1c",
        },
        "content_object": {
            "disposition": "UPLOADED",
            "key": CONTENT_KEY,
            "logical_path": PACKET["path"],
            "sha256": PACKET["sha256"],
            "size_bytes": PACKET["size_bytes"],
            "version_id": CONTENT_VERSION,
        },
        "internal_restore": {"status": "PASS"},
        "inventory": {
            "logical_bytes": PACKET["size_bytes"],
            "logical_file_count": 1,
            "registration_receipt_included": False,
            "seal_included": False,
            "shared_registry_included": False,
            "unique_bytes": PACKET["size_bytes"],
            "unique_object_count": 1,
        },
        "isolated_hydrate": {
            "first_hydrate": {
                "byte_equal_to_local": True,
                "restored_bytes": PACKET["size_bytes"],
                "restored_file_count": 1,
                "reused_file_count": 0,
                "sha256_matches": True,
                "size_bytes_matches": True,
            },
            "logical_path": PACKET["path"],
            "second_hydrate": {
                "byte_equal_to_local": True,
                "restored_bytes": 0,
                "restored_file_count": 0,
                "reused_file_count": 1,
                "sha256_matches": True,
                "size_bytes_matches": True,
            },
            "status": "PASS",
        },
        "label": "e0039-review-packet-seal",
        "manifest": {
            "initial_restore_gate_state": "PENDING_INDEPENDENT_DOWNLOAD_TEST",
            "key": MANIFEST_KEY,
            "sha256": MANIFEST_SHA256,
            "size_bytes": 3_105,
            "version_id": MANIFEST_VERSION,
        },
        "parent_full_snapshot": {
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
        },
        "policy": "S3_BOUNDED_ARTIFACT_SNAPSHOT_V1",
        "run_record": {
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
        },
        "snapshot_id": SNAPSHOT_ID,
        "source_git_commit": SEAL_ARTIFACT_COMMIT,
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
                checksum="BMawUJcT9GQjsDhXpeUJ02z6ldn/00u+mB9WSRXN+T0=",
                key=CONTENT_KEY,
                sha256=str(PACKET["sha256"]),
                size_bytes=int(PACKET["size_bytes"]),
                version_id=CONTENT_VERSION,
            ),
            "manifest": _head_receipt(
                checksum="vqM7PM9w8F239gUB2oPBI9pqGEUJsazDLU9n9PGgx3M=",
                key=MANIFEST_KEY,
                sha256=MANIFEST_SHA256,
                size_bytes=3_105,
                version_id=MANIFEST_VERSION,
            ),
            "run_record": _head_receipt(
                checksum="beHuNoFlnBt1oTDpUhn2S4UFX6cB8UpyezEjDAHfWwc=",
                key=RUN_KEY,
                sha256=RUN_SHA256,
                size_bytes=1_403,
                version_id=RUN_VERSION,
            ),
        },
        "status": "PASS",
    }

    assert {s3["content_object"]["logical_path"]} == {PACKET["path"]}
    assert PACKET_SEAL["path"] != s3["content_object"]["logical_path"]
    assert S3_REGISTRATION["path"] != s3["content_object"]["logical_path"]
    assert SHARED_REGISTRY["path"] != s3["content_object"]["logical_path"]

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
