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
REVIEWED_EVALUATION = {
    "path": "docs/experiments/E-0038-mbb-cdkt-reviewed-evaluation.json",
    "sha256": "324d7aff03447ca9ae5538debb5b71735c475f7408b5c8aa8381ddee7872b12e",
    "size_bytes": 18_273,
}
E0037_MAPPING_ONLY = {
    "path": "output/calibration/e0037-mbb-cdkt-sealed-evidence-mapping/mapping_only.json",
    "sha256": "e18f6b20825f93b20023c0d89caca1737481008b244696594852ca9fa972f99e",
    "size_bytes": 646_393,
}
MAPPING_CONTROL = {
    "path": "config/experiments/e0038-mbb-cdkt-exact-mapping.yaml",
    "sha256": "59db541208b6295aeff0cead9b0c9cb8624962738726b128432b1ca4cb074855",
    "size_bytes": 8_814,
}
PRIOR_REVIEWED_EVALUATION = {
    "path": "docs/experiments/E-0036-mbb-cdkt-reviewed-reader-evaluation.json",
    "sha256": "8ea952bc008d4bf4c274c25299cadb1c624424114be9ea3a38ba9b15d1b1c133",
    "size_bytes": 213_025,
}
REVIEW_CONTROL = {
    "path": "config/experiments/e0038-mbb-cdkt-reviewed-evaluation.yaml",
    "sha256": "9e82b9bd134eac643879192895fdc1d02b6211739c2817ed99c9218d849d1daf",
    "size_bytes": 2_249,
}
REVIEW_EVALUATOR = {
    "path": "src/bctc_ai/evaluation/e0038_reviewed_evaluation.py",
    "sha256": "99a3e363f78022c72aa3dd7cdaf4feb22bda061faf3946ef933fe6948b34f7e2",
    "size_bytes": 58_816,
}
REVIEW_CAPTURE_SCRIPT = {
    "path": "scripts/experiments/capture_e0038_mbb_cdkt_reviewed_evaluation.py",
    "sha256": "98df640fedfe216e626ff757f157dc440d9b0a742f41909b27f158423a467157",
    "size_bytes": 1_863,
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
REVIEWED_CLAIM_BOUNDARY = (
    "This calibration-only post-seal evaluation compares the immutable E-0038 mapping "
    "against exactly six pre-existing reviewed MBB CDKT rows after validating the mapping "
    "seal, its immutable post-seal S3 registration, and the mapping bytes and internal "
    "identities. All six reviewed rows are selected with the reviewed ReportNormId, which "
    "is fixed-six non-contradiction evidence only. The six rows cover neither E-0038 alias "
    "target and none of the six unselected rows, so aliases remain unapproved and the result "
    "grants no automatic adoption, schema, numeric, period, unit, accounting, Excel, "
    "history, holdout, or production authority. The frozen review interface contains "
    "numeric linkage fields, but this evaluator neither extracts nor uses them and opens no "
    "separate numeric artifact."
)
REVIEW_COMMIT = "e825c51f4725062b00ecaee0d098d6e278fe4ade"
SELECTED_PAIR_PROJECTION_SHA256 = "8135658100d83772812aeecff4beb4378ad7163c96a286a3770d430027a87df3"
FIXED_REVIEWED_ROWS = (
    ("page-0003-row-018-label", 4317, "mbb-p3-4317", 3, 18, "RESOLVED_ANCHOR"),
    ("page-0003-row-019-label", 4354, "mbb-p3-4354", 3, 19, "RESOLVED_ANCHOR"),
    ("page-0003-row-034-label", 4357, "mbb-p3-4357", 3, 34, "RESOLVED_PATH"),
    ("page-0003-row-035-label", 4335, "mbb-p3-4335", 3, 35, "RESOLVED_ANCHOR"),
    ("page-0003-row-036-label", 4366, "mbb-p3-4366", 3, 36, "RESOLVED_ANCHOR"),
    ("page-0004-row-009-label", 4336, "mbb-p4-4336", 4, 9, "RESOLVED_ANCHOR"),
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


def test_e0038_reviewed_evaluation_is_exactly_postseal_and_mapping_immutable(
    project_root: Path,
):
    reviewed_bytes = _read_exact_artifact(project_root, REVIEWED_EVALUATION)
    reviewed = json.loads(reviewed_bytes)
    registration = json.loads(_read_exact_artifact(project_root, S3_REGISTRATION))
    mapping = json.loads(_read_exact_artifact(project_root, MAPPING_ONLY))
    e0037 = json.loads(_read_exact_artifact(project_root, E0037_MAPPING_ONLY))

    assert reviewed_bytes == (
        json.dumps(
            reviewed,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    assert set(reviewed) == {
        "authority",
        "claim_boundary",
        "conclusion",
        "fixed_review_contract",
        "identity",
        "input_artifacts",
        "mechanism_calibration_gate",
        "pre_review_validation",
        "prior_comparison",
        "review_access_order",
        "review_authority_chain",
        "reviewed_mapping_evaluation",
        "state",
    }
    assert reviewed["identity"] == {
        "capture_script": REVIEW_CAPTURE_SCRIPT,
        "control": REVIEW_CONTROL,
        "dataset_role": "CALIBRATION",
        "evaluation_git_commit": REVIEW_COMMIT,
        "evaluation_git_dirty": False,
        "evaluator": REVIEW_EVALUATOR,
        "experiment_id": "E-0038",
        "format_version": 1,
    }
    assert reviewed["input_artifacts"] == {
        "e0037_mapping_only": E0037_MAPPING_ONLY,
        "mapping_control": MAPPING_CONTROL,
        "mapping_only": MAPPING_ONLY,
        "mapping_seal": MAPPING_SEAL,
        "postseal_s3_registration": S3_REGISTRATION,
        "prior_reviewed_evaluation": PRIOR_REVIEWED_EVALUATION,
    }
    assert reviewed["state"] == "E0038_POSTSEAL_REVIEWED_EVALUATION_COMPLETE"
    assert reviewed["mechanism_calibration_gate"] == "PASS_FIXED_SIX_AUTOMATIC_SELECTION_EXACT"

    validation = reviewed["pre_review_validation"]
    assert set(validation) == {
        "align_invocation_count",
        "automatic_selection_allowed",
        "changed_alias_report_norm_ids",
        "core_result_status",
        "counterfactual_search_pruned_states",
        "e0037_e0038_selected_pair_parity",
        "exact_interval_count",
        "exact_status",
        "formal_result_summary",
        "main_search_pruned_states",
        "mapping_bytes_validated",
        "mapping_mutation_count",
        "mapping_payload_validated_without_replay",
        "mapping_rerun_invocation_count",
        "mapping_result_sha256",
        "mapping_seal_validated",
        "plan_certificate",
        "postseal_s3_registration_validated",
        "result_projection_sha256",
        "result_pruned_states",
        "row_mapping_status_counts",
        "s3_internal_restore_status",
        "s3_isolated_hydrate_status",
        "s3_snapshot_id",
        "schema_disposition_status_counts",
        "schema_node_count",
        "score_margin",
        "sealed_e0037_interval_count",
        "search",
        "selected_row_count",
        "source_row_count",
        "unselected_row_count",
        "validation_order",
    }
    assert validation["validation_order"] == [
        "REVIEW_CONTROL_AND_IMPLEMENTATION",
        "E0038_MAPPING_SEAL",
        "E0038_POSTSEAL_S3_REGISTRATION",
        "E0038_MAPPING_CONTROL",
        "E0038_MAPPING_ONLY_BYTES_AND_IDENTITIES",
        "E0037_DIAGNOSTIC_BEST_PATH_IDENTITY",
        "PRE_EXISTING_E0036_REVIEWED_ROWS",
    ]
    assert validation["mapping_seal_validated"] is True
    assert validation["postseal_s3_registration_validated"] is True
    assert validation["mapping_bytes_validated"] is True
    assert validation["mapping_payload_validated_without_replay"] is True
    assert validation["mapping_rerun_invocation_count"] == 0
    assert validation["mapping_mutation_count"] == 0
    assert validation["formal_result_summary"] == registration["formal_result_summary"]
    formal = validation["formal_result_summary"]
    assert len(formal) == 25
    assert formal == {
        **registration["formal_result_summary"],
        "align_invocation_count": 1,
        "automatic_selection_allowed": True,
        "changed_report_norm_ids": [4375, 5699],
        "core_result_status": "RESOLVED",
        "counterfactual_search_pruned_states": 0,
        "exact_interval_count": 42,
        "exact_status": "EXACT_SEARCH_COMPLETE",
        "main_search_pruned_states": 0,
        "mapping_result_sha256": (
            "45133c4c6a441327afc611d6cce6c4711b7fe18b945339d854944817b90a9e86"
        ),
        "result_projection_sha256": (
            "d0934db910063bdb98db83f02bc2444fc1fe6e1dce7e1ebc7e09c7d36e434283"
        ),
        "result_pruned_states": 0,
        "schema_node_count": 77,
        "score_margin": 0.224488,
        "sealed_e0037_interval_count": 40,
        "selected_row_count": 58,
        "source_row_count": 64,
        "unselected_row_count": 6,
    }
    assert validation["search"] == {
        "algorithm": "ANCHORED_INTERVAL_K_BEST_MONOTONE_DP_FAIL_CLOSED",
        "beam_width_per_dp_cell": 8192,
        "counterfactual_search_pruned_states": 0,
        "counterfactual_searches": 17,
        "dp_cells": 675,
        "generated_states": 9977,
        "intervals": 42,
        "main_search_pruned_states": 0,
        "pruned_states": 0,
        "retained_states": 6833,
    }
    assert validation["plan_certificate"] == {
        "hard_retained_states_per_cell_cap": 8192,
        "maximum_monotone_signature_bound": 5005,
        "total_signature_work_bound": 136661,
        "total_signature_work_cap": 150000,
    }

    e0037_projection = [
        {"row_id": record["row_id"], "report_norm_id": record["report_norm_id"]}
        for record in e0037["mapping"]["best_path"]["matches"]
    ]
    e0038_rows = mapping["exact_mapping_bundle"]["exact_search"][
        "mapping_result_without_internal_alias_authority"
    ]["row_mappings"]
    e0038_projection = [
        {
            "row_id": record["row_id"],
            "report_norm_id": record["selected_report_norm_id"],
        }
        for record in e0038_rows
        if record["selected_report_norm_id"] is not None
    ]
    assert e0037_projection == e0038_projection
    assert len(e0038_projection) == 58
    assert _canonical_sha256(e0038_projection) == SELECTED_PAIR_PROJECTION_SHA256
    parity = validation["e0037_e0038_selected_pair_parity"]
    assert parity["selected_pairs_identical"] is True
    assert parity["same_selected_pair_count"] == 58
    assert parity["same_unselected_row_count"] == 6
    assert parity["selected_pair_projection_sha256"] == SELECTED_PAIR_PROJECTION_SHA256
    assert parity["e0037_status"] == "AMBIGUOUS_MAPPING"
    assert parity["e0037_automatic_selection_allowed"] is False
    assert parity["e0037_score_margin"] == 0.1
    assert parity["e0038_status"] == "RESOLVED"
    assert parity["e0038_automatic_selection_allowed"] is True
    assert parity["e0038_score_margin"] == 0.224488


def test_e0038_reviewed_evaluation_is_fixed_six_only_and_grants_no_authority(
    project_root: Path,
):
    reviewed = json.loads(_read_exact_artifact(project_root, REVIEWED_EVALUATION))
    prior_review = json.loads(_read_exact_artifact(project_root, PRIOR_REVIEWED_EVALUATION))
    evaluation = reviewed["reviewed_mapping_evaluation"]

    assert set(evaluation) == {
        "abstention_count",
        "automatically_selected_count",
        "automatically_selected_exact_count",
        "coverage_limits",
        "exact_rate",
        "exact_report_norm_id_count",
        "reviewed_row_count",
        "row_mapping_status_counts",
        "rows",
        "selected_row_count",
        "unselected_row_count",
        "wrong_report_norm_id_count",
    }
    assert evaluation["reviewed_row_count"] == 6
    assert evaluation["selected_row_count"] == 6
    assert evaluation["automatically_selected_count"] == 6
    assert evaluation["automatically_selected_exact_count"] == 6
    assert evaluation["exact_report_norm_id_count"] == 6
    assert evaluation["wrong_report_norm_id_count"] == 0
    assert evaluation["unselected_row_count"] == 0
    assert evaluation["abstention_count"] == 0
    assert evaluation["exact_rate"] == 1.0
    assert evaluation["row_mapping_status_counts"] == {
        "RESOLVED_ANCHOR": 5,
        "RESOLVED_PATH": 1,
    }
    rows = evaluation["rows"]
    assert all(
        set(row)
        == {
            "changed_alias_target",
            "exact_report_norm_id",
            "mapping_status",
            "page",
            "reviewed_report_norm_id",
            "row_ordinal",
            "sample_id",
            "selected",
            "selected_report_norm_id",
            "visible_row_id",
        }
        for row in rows
    )
    assert [
        (
            row["sample_id"],
            row["reviewed_report_norm_id"],
            row["visible_row_id"],
            row["page"],
            row["row_ordinal"],
            row["mapping_status"],
        )
        for row in rows
    ] == list(FIXED_REVIEWED_ROWS)
    assert all(row["selected_report_norm_id"] == row["reviewed_report_norm_id"] for row in rows)
    assert all(row["selected"] is True for row in rows)
    assert all(row["exact_report_norm_id"] is True for row in rows)
    assert all(row["changed_alias_target"] is False for row in rows)

    prior_bindings = prior_review["human_review"]["row_bindings"]
    assert [
        (
            binding["sample_id"],
            binding["reviewed_item_id"],
            binding["visible_row_id"],
            binding["page"],
            binding["row_ordinal"],
        )
        for binding in prior_bindings
    ] == [record[:5] for record in FIXED_REVIEWED_ROWS]
    assert all("reviewed_numeric_pair" in binding for binding in prior_bindings)
    assert evaluation["coverage_limits"] == {
        "all_mapping_selected_row_count": 58,
        "all_mapping_source_row_count": 64,
        "all_mapping_unselected_row_count": 6,
        "changed_alias_target_reviewed_count": 0,
        "changed_alias_target_reviewed_rate": 0.0,
        "changed_alias_target_total_count": 2,
        "schema_alias_hypotheses_reviewed": False,
        "selected_row_reviewed_count": 6,
        "selected_row_reviewed_rate": 0.10344827586206896,
        "source_row_reviewed_count": 6,
        "source_row_reviewed_rate": 0.09375,
        "unselected_row_mechanism_reviewed": False,
        "unselected_row_reviewed_count": 0,
        "unselected_row_reviewed_rate": 0.0,
    }

    comparison = reviewed["prior_comparison"]
    assert comparison["same_fixed_six_reviewed_rows"] is True
    assert comparison["e0036_baseline_readers"] == {
        "deepseek_ocr2": {
            "label_exact_count": 1,
            "label_row_count": 6,
            "mapping_status": "AMBIGUOUS_MAPPING",
            "reader": "DEEPSEEK_OCR_2",
            "reviewed_abstention_count": 6,
            "reviewed_automatically_selected_exact_count": 0,
            "reviewed_best_path_exact_count": 6,
            "score_margin": 0.008494,
        },
        "vietocr": {
            "label_exact_count": 3,
            "label_row_count": 6,
            "mapping_status": "AMBIGUOUS_MAPPING",
            "reader": "VIETOCR_VGG_TRANSFORMER",
            "reviewed_abstention_count": 6,
            "reviewed_automatically_selected_exact_count": 0,
            "reviewed_best_path_exact_count": 6,
            "score_margin": 0.051282,
        },
    }
    assert comparison["e0037_diagnostic_best_path"] == {
        "mapping_status": "AMBIGUOUS_MAPPING",
        "reviewed_abstention_count": 6,
        "reviewed_automatically_selected_exact_count": 0,
        "reviewed_best_path_exact_count": 6,
        "score_margin": 0.1,
        "selected_pair_count": 58,
        "selected_pair_projection_sha256": SELECTED_PAIR_PROJECTION_SHA256,
    }
    assert comparison["e0038_exact_mapping"] == {
        "mapping_status": "RESOLVED",
        "reviewed_abstention_count": 0,
        "reviewed_automatically_selected_exact_count": 6,
        "reviewed_selected_exact_count": 6,
        "score_margin": 0.224488,
        "selected_pair_count": 58,
        "selected_pair_projection_sha256": SELECTED_PAIR_PROJECTION_SHA256,
    }

    assert reviewed["fixed_review_contract"] == {
        "alias_approval_allowed": False,
        "automatic_mapping_adoption_allowed": False,
        "exact_reviewed_row_count": 6,
        "history_inputs_allowed": False,
        "holdout_or_production_claim_allowed": False,
        "mapping_must_be_validated_before_review_open": True,
        "mapping_mutation_allowed": False,
        "mapping_rerun_allowed": False,
        "numeric_fields_may_be_present_but_must_not_be_extracted_or_used": True,
        "review_source": "PRE_EXISTING_E0036_REVIEWED_EVALUATION_ONLY",
        "separate_numeric_artifact_allowed": False,
    }
    assert reviewed["review_access_order"] == {
        "e0030_artifact_opened": False,
        "e0033_artifact_opened": False,
        "e0034_artifact_opened": False,
        "e0037_diagnostic_pair_parity_validated_before_review_open": True,
        "history_or_mongodb_artifact_loaded": False,
        "human_review_registry_loaded_directly": False,
        "mapping_bytes_and_internal_identities_validated_before_review_open": True,
        "mapping_mutated_after_review_open": False,
        "mapping_rerun_after_review_open": False,
        "mapping_seal_validated_before_review_open": True,
        "numeric_fields_extracted_or_used": False,
        "opened_input_paths": [
            REVIEW_CONTROL["path"],
            REVIEW_EVALUATOR["path"],
            REVIEW_CAPTURE_SCRIPT["path"],
            MAPPING_SEAL["path"],
            S3_REGISTRATION["path"],
            MAPPING_CONTROL["path"],
            MAPPING_ONLY["path"],
            E0037_MAPPING_ONLY["path"],
            PRIOR_REVIEWED_EVALUATION["path"],
        ],
        "postseal_s3_registration_validated_before_review_open": True,
        "qwen_raw_or_rejected_output_opened": False,
        "review_interface_contains_numeric_fields": True,
        "review_source": PRIOR_REVIEWED_EVALUATION["path"],
        "review_source_count": 1,
        "separate_numeric_artifact_opened": False,
    }
    assert reviewed["review_authority_chain"] == {
        "authority_records_bound_through_frozen_artifacts": True,
        "authority_records_opened_directly": False,
        "document_key": "mbb-q1-2026-consolidated",
        "document_source_sha256": (
            "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
        ),
        "human_review_dataset": {
            "path": "reference/human_review/reviewed-mapping-corrections-2026-08-06.yaml",
            "sha256": ("32c86c0bf7642d3bd7596225331fc6f10906970476e1a9ba982b2f478d0f8e74"),
            "size_bytes": 22_000,
        },
        "human_review_policy": {
            "path": "config/reference/human-review-v1.yaml",
            "sha256": ("88011b6f9b85cc3561e0a4dddef39a9f57aa73f7d19e5fc4cb09825d2ea6fa34"),
            "size_bytes": 980,
        },
        "review_id": "HR-2026-08-06-CTG-ACB-MBB",
        "schema_graph": {
            "graph_sha256": ("831cde59c00b87a23c79b840484e580b6fa8786711d42bd894e3beccd1fddb5b"),
            "node_count": 77,
            "numeric_report_norm_id_sort_used": False,
            "statement_type": "CDKT",
            "workbook_display_order_used": True,
        },
        "target_workbook": {
            "path": "template/Bank_CDKT_ReportNormId.xlsx",
            "sha256": ("a07ff47f7c41011fe4ca5a66681106d476586ded9013b5874cbb9f67a6ad8486"),
            "size_bytes": 10_945,
        },
    }
    assert reviewed["authority"] == {
        "accounting_or_excel": False,
        "automatic_mapping_adoption": False,
        "dataset_role": "CALIBRATION_ONLY",
        "exact_search_zero_pruning_mechanism_evidence": True,
        "fixed_six_reviewed_non_contradiction": True,
        "history_or_mongodb": False,
        "holdout_or_production": False,
        "mapping_accuracy_beyond_fixed_six": False,
        "numeric_period_or_unit": False,
        "schema_alias_approval": False,
        "schema_authority": False,
        "sealed_mapping_identity_and_s3_durability": True,
    }
    assert reviewed["conclusion"] == {
        "accepted_evidence": [
            "EXACT_SEARCH_ZERO_PRUNING_MECHANICAL_EVIDENCE",
            "FIXED_SIX_REVIEWED_ROWS_DO_NOT_CONTRADICT_SELECTED_MAPPING",
        ],
        "automatic_mapping_adoption": False,
        "next_milestone": (
            "E-0039 schema-governed alias approval or replacement plus a "
            "review/adjudication of the exact six unselected rows and a "
            "review-independent unmatched-row role/acronym mechanism; numeric and history "
            "evidence remain unused and out of scope."
        ),
        "production": False,
        "reason": (
            "The fixed six are selected and exact, but they cover zero of two alias targets "
            "and zero of six unselected rows."
        ),
        "schema_alias_approval": False,
    }
    assert reviewed["claim_boundary"] == REVIEWED_CLAIM_BOUNDARY
