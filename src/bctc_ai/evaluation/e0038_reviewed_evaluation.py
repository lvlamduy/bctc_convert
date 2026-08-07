"""Post-seal reviewed evaluation for the immutable E-0038 mapping."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, cast

from bctc_ai.evaluation.e0038_exact_mapping import (
    MAPPING_ONLY_STATE,
    MAPPING_SEAL_STATE,
    RESULT_PROJECTION_SHA256,
    E0038ExactMappingError,
    _assert_tracked_record_matches_head,
    _assert_unchanged,
    _canonical_path,
    _clean_git_commit,
    _decode_control,
    _decode_json_object,
    _encoded_json,
    _exclusive_publish_json,
    _read_stable_file,
    _StableFile,
    _validate_e0038_mapping_payload,
    _verify_record,
)


class E0038ReviewedEvaluationError(RuntimeError):
    """Raised when E-0038 cannot be reviewed without weakening its seal."""


CONTROL_RELATIVE_PATH = Path("config/experiments/e0038-mbb-cdkt-reviewed-evaluation.yaml")
OUTPUT_RELATIVE_PATH = Path("docs/experiments/E-0038-mbb-cdkt-reviewed-evaluation.json")
MAPPING_ONLY_RELATIVE_PATH = Path(
    "output/calibration/e0038-mbb-cdkt-exact-mapping/mapping_only.json"
)
MAPPING_SEAL_RELATIVE_PATH = Path("docs/experiments/E-0038-mbb-cdkt-exact-mapping-seal.json")
S3_REGISTRATION_RELATIVE_PATH = Path(
    "docs/experiments/E-0038-mbb-cdkt-exact-mapping-s3-registration.json"
)
MAPPING_CONTROL_RELATIVE_PATH = Path("config/experiments/e0038-mbb-cdkt-exact-mapping.yaml")
PRIOR_REVIEW_RELATIVE_PATH = Path(
    "docs/experiments/E-0036-mbb-cdkt-reviewed-reader-evaluation.json"
)
E0037_MAPPING_ONLY_RELATIVE_PATH = Path(
    "output/calibration/e0037-mbb-cdkt-sealed-evidence-mapping/mapping_only.json"
)
EVALUATOR_RELATIVE_PATH = Path("src/bctc_ai/evaluation/e0038_reviewed_evaluation.py")
CAPTURE_SCRIPT_RELATIVE_PATH = Path(
    "scripts/experiments/capture_e0038_mbb_cdkt_reviewed_evaluation.py"
)

READY_STATE = "READY_FOR_E0038_POSTSEAL_REVIEWED_EVALUATION"
COMPLETE_STATE = "E0038_POSTSEAL_REVIEWED_EVALUATION_COMPLETE"
S3_REGISTRATION_STATE = "E0038_EXACT_MAPPING_IMMUTABLY_REGISTERED_IN_S3_POST_SEAL"
MECHANISM_CALIBRATION_GATE = "PASS_FIXED_SIX_AUTOMATIC_SELECTION_EXACT"

MAPPING_ONLY_ARTIFACT = {
    "path": MAPPING_ONLY_RELATIVE_PATH.as_posix(),
    "sha256": "8b1074d2ca57efcb1c6da123615ace86438069b4d581b9afb4b6e4cfbf01a9e9",
    "size_bytes": 646_606,
}
MAPPING_SEAL_ARTIFACT = {
    "path": MAPPING_SEAL_RELATIVE_PATH.as_posix(),
    "sha256": "bffcaf56d80af458187a646269862b8bf669237d865fa1561ab41b056db06137",
    "size_bytes": 6_421,
}
S3_REGISTRATION_ARTIFACT = {
    "path": S3_REGISTRATION_RELATIVE_PATH.as_posix(),
    "sha256": "6baf6a90842066e5253533072a800c5066e97248745efed8480cb67c410601e4",
    "size_bytes": 9_555,
}
MAPPING_CONTROL_ARTIFACT = {
    "path": MAPPING_CONTROL_RELATIVE_PATH.as_posix(),
    "sha256": "59db541208b6295aeff0cead9b0c9cb8624962738726b128432b1ca4cb074855",
    "size_bytes": 8_814,
}
PRIOR_REVIEW_ARTIFACT = {
    "path": PRIOR_REVIEW_RELATIVE_PATH.as_posix(),
    "sha256": "8ea952bc008d4bf4c274c25299cadb1c624424114be9ea3a38ba9b15d1b1c133",
    "size_bytes": 213_025,
}
E0037_MAPPING_ONLY_ARTIFACT = {
    "path": E0037_MAPPING_ONLY_RELATIVE_PATH.as_posix(),
    "sha256": "e18f6b20825f93b20023c0d89caca1737481008b244696594852ca9fa972f99e",
    "size_bytes": 646_393,
}

MAPPING_RESULT_SHA256 = "45133c4c6a441327afc611d6cce6c4711b7fe18b945339d854944817b90a9e86"
E0037_E0038_SELECTED_PAIR_PROJECTION_SHA256 = (
    "8135658100d83772812aeecff4beb4378ad7163c96a286a3770d430027a87df3"
)
S3_SNAPSHOT_ID = "20260807T192436Z-e0038-exact-mapping-seal-8b1074d2ca57"
CHANGED_ALIAS_REPORT_NORM_IDS = (4375, 5699)
_FIXED_REVIEWED_IDENTITIES = (
    ("page-0003-row-018-label", 4317, "mbb-p3-4317", 3, 18),
    ("page-0003-row-019-label", 4354, "mbb-p3-4354", 3, 19),
    ("page-0003-row-034-label", 4357, "mbb-p3-4357", 3, 34),
    ("page-0003-row-035-label", 4335, "mbb-p3-4335", 3, 35),
    ("page-0003-row-036-label", 4366, "mbb-p3-4366", 3, 36),
    ("page-0004-row-009-label", 4336, "mbb-p4-4336", 4, 9),
)
_EXPECTED_ALL_ROW_STATUS_COUNTS = {
    "BEST_PATH_SKIPPED": 2,
    "NO_ADMISSIBLE_PAIR": 4,
    "RESOLVED_ANCHOR": 41,
    "RESOLVED_PATH": 17,
}
_EXPECTED_REVIEWED_STATUS_COUNTS = {
    "RESOLVED_ANCHOR": 5,
    "RESOLVED_PATH": 1,
}
_EXPECTED_SCHEMA_STATUS_COUNTS = {
    "MAPPED": 58,
    "UNMATCHED_SCHEMA_NODE": 13,
    "UNMATCHED_SCHEMA_NODE_WITH_SKIPPED_CANDIDATES": 6,
}
_HUMAN_REVIEW_POLICY_ARTIFACT = {
    "path": "config/reference/human-review-v1.yaml",
    "sha256": "88011b6f9b85cc3561e0a4dddef39a9f57aa73f7d19e5fc4cb09825d2ea6fa34",
    "size_bytes": 980,
}
_HUMAN_REVIEW_DATASET_ARTIFACT = {
    "path": "reference/human_review/reviewed-mapping-corrections-2026-08-06.yaml",
    "sha256": "32c86c0bf7642d3bd7596225331fc6f10906970476e1a9ba982b2f478d0f8e74",
    "size_bytes": 22_000,
}
_TARGET_WORKBOOK_ARTIFACT = {
    "path": "template/Bank_CDKT_ReportNormId.xlsx",
    "sha256": "a07ff47f7c41011fe4ca5a66681106d476586ded9013b5874cbb9f67a6ad8486",
    "size_bytes": 10_945,
}
_MBB_REVIEW_SOURCE_SHA256 = "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
_REVIEW_SCHEMA_GRAPH = {
    "graph_sha256": "831cde59c00b87a23c79b840484e580b6fa8786711d42bd894e3beccd1fddb5b",
    "node_count": 77,
    "numeric_report_norm_id_sort_used": False,
    "statement_type": "CDKT",
    "workbook_display_order_used": True,
}
_VALIDATION_ORDER = [
    "REVIEW_CONTROL_AND_IMPLEMENTATION",
    "E0038_MAPPING_SEAL",
    "E0038_POSTSEAL_S3_REGISTRATION",
    "E0038_MAPPING_CONTROL",
    "E0038_MAPPING_ONLY_BYTES_AND_IDENTITIES",
    "E0037_DIAGNOSTIC_BEST_PATH_IDENTITY",
    "PRE_EXISTING_E0036_REVIEWED_ROWS",
]
_CLAIM_BOUNDARY = (
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

_CONTROL_KEYS = {
    "version",
    "experiment_id",
    "dataset_role",
    "state",
    "frozen_inputs",
    "implementation",
    "review_contract",
    "output",
}
_FROZEN_INPUT_KEYS = {
    "mapping_only",
    "mapping_seal",
    "postseal_s3_registration",
    "mapping_control",
    "e0037_mapping_only",
    "prior_reviewed_evaluation",
}
_IMPLEMENTATION_KEYS = {"evaluator", "capture_script"}
_REVIEW_CONTRACT = {
    "review_source": "PRE_EXISTING_E0036_REVIEWED_EVALUATION_ONLY",
    "exact_reviewed_row_count": 6,
    "mapping_must_be_validated_before_review_open": True,
    "mapping_rerun_allowed": False,
    "mapping_mutation_allowed": False,
    "alias_approval_allowed": False,
    "automatic_mapping_adoption_allowed": False,
    "numeric_fields_may_be_present_but_must_not_be_extracted_or_used": True,
    "separate_numeric_artifact_allowed": False,
    "history_inputs_allowed": False,
    "holdout_or_production_claim_allowed": False,
}

StableReader = Callable[..., _StableFile]


def _fail(label: str, exc: Exception) -> E0038ReviewedEvaluationError:
    return E0038ReviewedEvaluationError(f"{label}: {exc}")


def _strict_json(stable: _StableFile, label: str) -> dict[str, Any]:
    try:
        payload = _decode_json_object(stable.payload, label)
        if stable.payload != _encoded_json(payload):
            raise E0038ReviewedEvaluationError(f"{label} is not canonical JSON")
        return payload
    except E0038ReviewedEvaluationError:
        raise
    except E0038ExactMappingError as exc:
        raise _fail(f"cannot load {label}", exc) from exc


def _exact_keys(value: object, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise E0038ReviewedEvaluationError(f"{label} keyset drifted")
    return cast(dict[str, Any], value)


def _verified_record(
    reader: StableReader,
    project_root: Path,
    record: object,
    label: str,
    *,
    expected_path: Path,
    maximum_size: int,
) -> _StableFile:
    try:
        return _verify_record(
            reader,
            project_root,
            record,
            label,
            expected_path=expected_path,
            maximum_size=maximum_size,
        )
    except E0038ExactMappingError as exc:
        raise _fail(f"cannot validate {label}", exc) from exc


def _validate_control(
    project_root: Path,
    control: dict[str, Any],
    reader: StableReader,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if (
        set(control) != _CONTROL_KEYS
        or control.get("version") != 1
        or control.get("experiment_id") != "E-0038"
        or control.get("dataset_role") != "CALIBRATION"
        or control.get("state") != READY_STATE
    ):
        raise E0038ReviewedEvaluationError("E-0038 reviewed-evaluation control drifted")
    frozen = _exact_keys(
        control.get("frozen_inputs"),
        _FROZEN_INPUT_KEYS,
        "E-0038 reviewed frozen inputs",
    )
    implementation = _exact_keys(
        control.get("implementation"),
        _IMPLEMENTATION_KEYS,
        "E-0038 reviewed implementation",
    )
    if control.get("review_contract") != _REVIEW_CONTRACT:
        raise E0038ReviewedEvaluationError("E-0038 reviewed contract drifted")
    if control.get("output") != {"path": OUTPUT_RELATIVE_PATH.as_posix()}:
        raise E0038ReviewedEvaluationError("E-0038 reviewed output is noncanonical")
    expected_frozen = {
        "mapping_only": MAPPING_ONLY_ARTIFACT,
        "mapping_seal": MAPPING_SEAL_ARTIFACT,
        "postseal_s3_registration": S3_REGISTRATION_ARTIFACT,
        "mapping_control": MAPPING_CONTROL_ARTIFACT,
        "e0037_mapping_only": E0037_MAPPING_ONLY_ARTIFACT,
        "prior_reviewed_evaluation": PRIOR_REVIEW_ARTIFACT,
    }
    if frozen != expected_frozen:
        raise E0038ReviewedEvaluationError("E-0038 reviewed frozen identities drifted")
    evaluator = _verified_record(
        reader,
        project_root,
        implementation["evaluator"],
        "E-0038 reviewed evaluator",
        expected_path=EVALUATOR_RELATIVE_PATH,
        maximum_size=2 * 1024 * 1024,
    )
    capture = _verified_record(
        reader,
        project_root,
        implementation["capture_script"],
        "E-0038 reviewed capture script",
        expected_path=CAPTURE_SCRIPT_RELATIVE_PATH,
        maximum_size=1024 * 1024,
    )
    return frozen, {"evaluator": evaluator, "capture_script": capture}


def _validate_mapping_seal(seal: dict[str, Any]) -> None:
    _exact_keys(
        seal,
        {
            "access_contract",
            "authority",
            "claim_boundary",
            "dataset_role",
            "experiment_id",
            "format_version",
            "input_hash_ledger",
            "inventory",
            "mapping_capture_git_commit",
            "mapping_status",
            "replay",
            "result_projection_sha256",
            "seal_git_commit",
            "seal_git_dirty",
            "state",
        },
        "E-0038 mapping seal",
    )
    access = seal.get("access_contract")
    authority = seal.get("authority")
    replay = seal.get("replay")
    ledger = seal.get("input_hash_ledger")
    deterministic_inputs = (
        ledger.get("deterministic_replay_inputs") if isinstance(ledger, dict) else None
    )
    if (
        seal.get("format_version") != 1
        or seal.get("experiment_id") != "E-0038"
        or seal.get("dataset_role") != "CALIBRATION"
        or seal.get("state") != MAPPING_SEAL_STATE
        or seal.get("mapping_status") != "EXACT_SEARCH_COMPLETE"
        or seal.get("seal_git_dirty") is not False
        or seal.get("mapping_capture_git_commit") != seal.get("seal_git_commit")
        or seal.get("result_projection_sha256") != RESULT_PROJECTION_SHA256
        or seal.get("inventory") != {"file_count": 1, "files": [MAPPING_ONLY_ARTIFACT]}
        or not isinstance(ledger, dict)
        or ledger.get("mapping_only") != MAPPING_ONLY_ARTIFACT
        or not isinstance(deterministic_inputs, dict)
        or deterministic_inputs.get("control") != MAPPING_CONTROL_ARTIFACT
        or deterministic_inputs.get("e0037_mapping_only") != E0037_MAPPING_ONLY_ARTIFACT
        or not isinstance(access, dict)
        or access.get("review_opened") is not False
        or access.get("history_opened") is not False
        or access.get("qwen_raw_or_rejected_output_opened") is not False
        or access.get("e0030_opened") is not False
        or access.get("e0033_opened") is not False
        or access.get("e0034_opened") is not False
        or access.get("numeric_period_or_unit_features_passed") is not False
        or not isinstance(authority, dict)
        or authority.get("mapping_accuracy") is not False
        or authority.get("review_or_steward_approval") is not False
        or authority.get("numeric_period_or_unit") is not False
        or authority.get("accounting_excel_holdout_or_production") is not False
        or not isinstance(replay, dict)
        or replay.get("deterministic_replay_invocation_count") != 1
        or replay.get("exact_byte_equality") is not True
        or replay.get("mapping_core_result_used_to_change_published_mapping") is not False
    ):
        raise E0038ReviewedEvaluationError("E-0038 mapping seal linkage drifted")


def _validate_postseal_registration(
    registration: dict[str, Any],
    seal: dict[str, Any],
) -> None:
    _exact_keys(
        registration,
        {
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
        },
        "E-0038 post-seal S3 registration",
    )
    access = registration.get("access_contract")
    authority = registration.get("authority")
    s3 = registration.get("s3_snapshot")
    remote = registration.get("remote_verification")
    content = s3.get("content_object") if isinstance(s3, dict) else None
    hydrate = s3.get("isolated_hydrate") if isinstance(s3, dict) else None
    first_hydrate = hydrate.get("first_hydrate") if isinstance(hydrate, dict) else None
    second_hydrate = hydrate.get("second_hydrate") if isinstance(hydrate, dict) else None
    run_record = s3.get("run_record") if isinstance(s3, dict) else None
    head_objects = remote.get("head_objects") if isinstance(remote, dict) else None
    content_head = head_objects.get("content_object") if isinstance(head_objects, dict) else None
    summary = _exact_keys(
        registration.get("formal_result_summary"),
        {
            "align_invocation_count",
            "automatic_selection_allowed",
            "changed_report_norm_ids",
            "core_result_status",
            "counterfactual_search_pruned_states",
            "counterfactual_searches",
            "dp_cells",
            "exact_interval_count",
            "exact_status",
            "generated_states",
            "main_search_pruned_states",
            "mapping_result_sha256",
            "mapping_state",
            "plan_certificate",
            "result_projection_sha256",
            "result_pruned_states",
            "retained_states",
            "row_mapping_status_counts",
            "schema_disposition_status_counts",
            "schema_node_count",
            "score_margin",
            "sealed_e0037_interval_count",
            "selected_row_count",
            "source_row_count",
            "unselected_row_count",
        },
        "E-0038 post-seal formal result summary",
    )
    if (
        registration.get("format_version") != 1
        or registration.get("experiment_id") != "E-0038"
        or registration.get("dataset_role") != "CALIBRATION"
        or registration.get("state") != S3_REGISTRATION_STATE
        or registration.get("policy") != "IMMUTABLE_POST_SEAL_S3_REGISTRATION_V1"
        or registration.get("local_artifacts")
        != {"mapping_only": MAPPING_ONLY_ARTIFACT, "mapping_seal": MAPPING_SEAL_ARTIFACT}
        or not isinstance(access, dict)
        or access.get("review_artifacts_opened") is not False
        or access.get("numeric_artifacts_opened") is not False
        or access.get("history_artifacts_opened") is not False
        or access.get("seal_identity_validated_before_registration") is not True
        or not isinstance(authority, dict)
        or authority.get("s3_durability_registration") is not True
        or authority.get("mapping_accuracy") is not False
        or authority.get("review_or_steward_approval") is not False
        or authority.get("numeric_period_unit_or_value") is not False
        or authority.get("accounting_excel_holdout_or_production") is not False
        or not isinstance(s3, dict)
        or s3.get("snapshot_id") != S3_SNAPSHOT_ID
        or s3.get("policy") != "S3_BOUNDED_ARTIFACT_SNAPSHOT_V1"
        or not isinstance(content, dict)
        or content.get("disposition") != "UPLOADED"
        or content.get("logical_path") != MAPPING_ONLY_ARTIFACT["path"]
        or content.get("sha256") != MAPPING_ONLY_ARTIFACT["sha256"]
        or content.get("size_bytes") != MAPPING_ONLY_ARTIFACT["size_bytes"]
        or s3.get("internal_restore") != {"status": "PASS"}
        or not isinstance(hydrate, dict)
        or hydrate.get("status") != "PASS"
        or hydrate.get("logical_path") != MAPPING_ONLY_ARTIFACT["path"]
        or not isinstance(first_hydrate, dict)
        or first_hydrate.get("byte_equal_to_local") is not True
        or first_hydrate.get("sha256_matches") is not True
        or first_hydrate.get("size_bytes_matches") is not True
        or first_hydrate.get("restored_file_count") != 1
        or not isinstance(second_hydrate, dict)
        or second_hydrate.get("byte_equal_to_local") is not True
        or second_hydrate.get("sha256_matches") is not True
        or second_hydrate.get("size_bytes_matches") is not True
        or second_hydrate.get("reused_file_count") != 1
        or not isinstance(run_record, dict)
        or run_record.get("status") != "PASS"
        or run_record.get("all_incremental_objects_restore_verified") is not True
        or not isinstance(remote, dict)
        or remote.get("status") != "PASS"
        or remote.get("bucket_preflight", {}).get("status") != "PASS"
        or not isinstance(content_head, dict)
        or content_head.get("status") != "PASS"
        or content_head.get("metadata_sha256") != MAPPING_ONLY_ARTIFACT["sha256"]
        or content_head.get("content_length") != MAPPING_ONLY_ARTIFACT["size_bytes"]
        or summary.get("align_invocation_count") != 1
        or summary.get("source_row_count") != 64
        or summary.get("selected_row_count") != 58
        or summary.get("unselected_row_count") != 6
        or summary.get("main_search_pruned_states") != 0
        or summary.get("counterfactual_search_pruned_states") != 0
        or summary.get("result_pruned_states") != 0
        or summary.get("mapping_result_sha256") != MAPPING_RESULT_SHA256
        or summary.get("mapping_state") != MAPPING_ONLY_STATE
        or summary.get("result_projection_sha256") != RESULT_PROJECTION_SHA256
        or summary.get("changed_report_norm_ids") != list(CHANGED_ALIAS_REPORT_NORM_IDS)
        or summary.get("row_mapping_status_counts") != _EXPECTED_ALL_ROW_STATUS_COUNTS
        or summary.get("schema_disposition_status_counts") != _EXPECTED_SCHEMA_STATUS_COUNTS
        or summary.get("core_result_status") != "RESOLVED"
        or summary.get("automatic_selection_allowed") is not True
        or summary.get("exact_status") != "EXACT_SEARCH_COMPLETE"
        or summary.get("schema_node_count") != 77
        or summary.get("sealed_e0037_interval_count") != 40
        or summary.get("score_margin") != 0.224488
        or summary.get("exact_interval_count") != 42
        or summary.get("dp_cells") != 675
        or summary.get("generated_states") != 9977
        or summary.get("retained_states") != 6833
        or summary.get("counterfactual_searches") != 17
        or summary.get("plan_certificate")
        != {
            "hard_retained_states_per_cell_cap": 8192,
            "maximum_monotone_signature_bound": 5005,
            "total_signature_work_bound": 136661,
            "total_signature_work_cap": 150000,
        }
    ):
        raise E0038ReviewedEvaluationError(
            "E-0038 immutable post-seal S3 registration is incomplete or drifted"
        )
    expected_linkage = {
        "mapping_capture_git_commit": seal["mapping_capture_git_commit"],
        "mapping_inventory_identity_matches": True,
        "mapping_ledger_identity_matches": True,
        "result_projection_matches_mapping": True,
        "result_projection_sha256": RESULT_PROJECTION_SHA256,
        "seal_git_commit": seal["seal_git_commit"],
    }
    if registration.get("seal_linkage") != expected_linkage:
        raise E0038ReviewedEvaluationError("E-0038 S3 registration/seal linkage drifted")


def _validate_mapping_payload(
    mapping: dict[str, Any],
    mapping_control: dict[str, Any],
    mapping_control_artifact: Mapping[str, Any],
    seal: dict[str, Any],
    registration: dict[str, Any],
) -> dict[str, Any]:
    capture_commit = mapping.get("capture_git_commit")
    try:
        _validate_e0038_mapping_payload(
            mapping,
            mapping_control,
            expected_control_artifact=mapping_control_artifact,
            expected_git_commit=cast(str, capture_commit),
        )
    except (E0038ExactMappingError, TypeError) as exc:
        raise _fail("E-0038 mapping payload identity validation failed", exc) from exc
    exact = mapping["exact_mapping_bundle"]["exact_search"]
    result = exact["mapping_result_without_internal_alias_authority"]
    rows = result["row_mappings"]
    row_statuses = dict(sorted(Counter(row["status"] for row in rows).items()))
    selected_count = sum(row["selected_report_norm_id"] is not None for row in rows)
    unselected_count = len(rows) - selected_count
    alias_receipt = mapping["exact_mapping_bundle"]["alias_overlay_receipt"]
    summary = registration["formal_result_summary"]
    search = result["search"]
    plan = exact["plan"]
    resources = exact["resource_semantics"]
    schema_statuses = dict(
        sorted(Counter(item["status"] for item in result["schema_dispositions"]).items())
    )
    if (
        mapping.get("state") != MAPPING_ONLY_STATE
        or capture_commit != seal["mapping_capture_git_commit"]
        or mapping.get("result_input_binding", {}).get("mapping_result_sha256")
        != MAPPING_RESULT_SHA256
        or result.get("schema_projection_sha256") != RESULT_PROJECTION_SHA256
        or exact.get("main_search_pruned_states") != 0
        or exact.get("counterfactual_search_pruned_states") != 0
        or search.get("pruned_states") != 0
        or len(rows) != 64
        or selected_count != 58
        or unselected_count != 6
        or row_statuses != _EXPECTED_ALL_ROW_STATUS_COUNTS
        or schema_statuses != _EXPECTED_SCHEMA_STATUS_COUNTS
        or alias_receipt.get("changed_report_norm_ids") != list(CHANGED_ALIAS_REPORT_NORM_IDS)
        or alias_receipt.get("review_or_steward_approved") is not False
        or alias_receipt.get("production_allowed") is not False
        or alias_receipt.get("historical_alias_authority_allowed") is not False
        or alias_receipt.get("numeric_period_or_value_features_allowed") is not False
        or summary.get("mapping_state") != mapping.get("state")
        or summary.get("core_result_status") != result.get("status")
        or summary.get("automatic_selection_allowed") != result.get("automatic_selection_allowed")
        or summary.get("align_invocation_count") != exact.get("align_invocation_count")
        or summary.get("exact_status") != exact.get("status")
        or summary.get("schema_node_count") != len(result["schema_dispositions"])
        or summary.get("sealed_e0037_interval_count")
        != mapping["metrics"]["sealed_e0037_interval_count"]
        or result.get("status") != "RESOLVED"
        or result.get("automatic_selection_allowed") is not True
        or result.get("score_margin") != 0.224488
        or search
        != {
            "algorithm": "ANCHORED_INTERVAL_K_BEST_MONOTONE_DP_FAIL_CLOSED",
            "intervals": 42,
            "dp_cells": 675,
            "generated_states": 9977,
            "retained_states": 6833,
            "pruned_states": 0,
            "main_search_pruned_states": 0,
            "counterfactual_search_pruned_states": 0,
            "counterfactual_searches": 17,
            "beam_width_per_dp_cell": 8192,
        }
        or plan.get("maximum_monotone_signature_bound") != 5005
        or plan.get("total_signature_work_bound") != 136661
        or resources.get("retained_signature_certificate_cap") != 150000
    ):
        raise E0038ReviewedEvaluationError("E-0038 mapping identity or summary drifted")
    return {
        "source_row_count": len(rows),
        "selected_row_count": selected_count,
        "unselected_row_count": unselected_count,
        "row_mapping_status_counts": row_statuses,
        "schema_disposition_status_counts": schema_statuses,
        "schema_node_count": len(result["schema_dispositions"]),
        "sealed_e0037_interval_count": mapping["metrics"]["sealed_e0037_interval_count"],
        "align_invocation_count": exact["align_invocation_count"],
        "exact_status": exact["status"],
        "core_result_status": result["status"],
        "automatic_selection_allowed": result["automatic_selection_allowed"],
        "score_margin": result["score_margin"],
        "exact_interval_count": len(result["intervals"]),
        "search": dict(search),
        "plan_certificate": {
            "maximum_monotone_signature_bound": plan["maximum_monotone_signature_bound"],
            "hard_retained_states_per_cell_cap": search["beam_width_per_dp_cell"],
            "total_signature_work_bound": plan["total_signature_work_bound"],
            "total_signature_work_cap": resources["retained_signature_certificate_cap"],
        },
        "main_search_pruned_states": exact["main_search_pruned_states"],
        "counterfactual_search_pruned_states": exact["counterfactual_search_pruned_states"],
        "result_pruned_states": search["pruned_states"],
        "mapping_result_sha256": MAPPING_RESULT_SHA256,
        "result_projection_sha256": RESULT_PROJECTION_SHA256,
        "changed_alias_report_norm_ids": list(CHANGED_ALIAS_REPORT_NORM_IDS),
        "formal_result_summary": dict(summary),
        "mapping_rerun_invocation_count": 0,
        "mapping_mutation_count": 0,
    }


def _selected_pair_projection_sha256(projection: list[dict[str, Any]]) -> str:
    encoded = json.dumps(
        projection,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_e0037_comparison(
    e0037: dict[str, Any],
    e0038: dict[str, Any],
) -> dict[str, Any]:
    """Validate the sealed diagnostic predecessor without treating it as acceptance."""

    _exact_keys(
        e0037,
        {
            "access_contract",
            "authority",
            "capture_git_commit",
            "capture_git_dirty",
            "claim_boundary",
            "dataset_role",
            "experiment_id",
            "format_version",
            "implementation_hash_ledger",
            "input_hash_ledger",
            "mapping",
            "metrics",
            "rows",
            "schema_dispositions",
            "schema_projection",
            "semantic_proposals",
            "source_structure",
            "state",
        },
        "E-0037 diagnostic mapping",
    )
    mapping = e0037.get("mapping")
    metrics = e0037.get("metrics")
    rows = e0037.get("rows")
    access = e0037.get("access_contract")
    authority = e0037.get("authority")
    input_ledger = e0037.get("input_hash_ledger")
    best_path = mapping.get("best_path") if isinstance(mapping, dict) else None
    matches = best_path.get("matches") if isinstance(best_path, dict) else None
    search = mapping.get("search") if isinstance(mapping, dict) else None
    if not isinstance(rows, list):
        raise E0038ReviewedEvaluationError("E-0037 diagnostic rows are invalid")
    status_counts = dict(
        sorted(
            Counter(
                row.get("mapping", {}).get("status") for row in rows if isinstance(row, dict)
            ).items()
        )
    )
    if (
        e0037.get("format_version") != 1
        or e0037.get("experiment_id") != "E-0037"
        or e0037.get("dataset_role") != "CALIBRATION"
        or e0037.get("state") != "MAPPING_ONLY_SEALED_BEFORE_NUMERIC_PERIOD_REVIEW_ACCESS"
        or e0037.get("capture_git_dirty") is not False
        or not isinstance(access, dict)
        or access.get("review_or_history_opened") is not False
        or access.get("qwen_result_or_rejected_raw_output_opened") is not False
        or access.get("e0030_opened") is not False
        or access.get("e0033_opened") is not False
        or access.get("e0034_opened") is not False
        or access.get("numeric_or_period_features_passed_to_mapper") is not False
        or not isinstance(authority, dict)
        or authority.get("ambiguous_best_path_may_select_report_norm_id") is not False
        or authority.get("review_or_history_authority") is not False
        or authority.get("numeric_value_or_status_authority") is not False
        or not isinstance(input_ledger, dict)
        or input_ledger.get("cdkt_workbook") != _TARGET_WORKBOOK_ARTIFACT
        or not isinstance(mapping, dict)
        or mapping.get("status") != "AMBIGUOUS_MAPPING"
        or mapping.get("automatic_selection_allowed") is not False
        or mapping.get("score_margin") != 0.1
        or not isinstance(metrics, dict)
        or metrics.get("row_count") != 64
        or metrics.get("accepted_row_count") != 0
        or metrics.get("ambiguous_row_count") != 60
        or metrics.get("unselected_row_count") != 64
        or status_counts != {"AMBIGUOUS_ACROSS_PATHS": 60, "NO_ADMISSIBLE_PAIR": 4}
        or search
        != {
            "algorithm": "ANCHORED_INTERVAL_K_BEST_MONOTONE_DP_FAIL_CLOSED",
            "beam_width_per_dp_cell": 64,
            "counterfactual_search_pruned_states": 328,
            "counterfactual_searches": 19,
            "dp_cells": 701,
            "generated_states": 9799,
            "intervals": 40,
            "main_search_pruned_states": 122,
            "pruned_states": 450,
            "retained_states": 6336,
        }
        or not isinstance(matches, list)
        or len(matches) != 58
    ):
        raise E0038ReviewedEvaluationError("E-0037 diagnostic mapping identity drifted")
    e0037_projection = [
        {"row_id": item["row_id"], "report_norm_id": item["report_norm_id"]} for item in matches
    ]
    e0038_rows = e0038["exact_mapping_bundle"]["exact_search"][
        "mapping_result_without_internal_alias_authority"
    ]["row_mappings"]
    e0038_projection = [
        {
            "row_id": item["row_id"],
            "report_norm_id": item["selected_report_norm_id"],
        }
        for item in e0038_rows
        if item["selected_report_norm_id"] is not None
    ]
    digest = _selected_pair_projection_sha256(e0037_projection)
    if (
        e0037_projection != e0038_projection
        or len(e0038_projection) != 58
        or digest != E0037_E0038_SELECTED_PAIR_PROJECTION_SHA256
        or _selected_pair_projection_sha256(e0038_projection) != digest
    ):
        raise E0038ReviewedEvaluationError("E-0037/E-0038 selected-pair parity drifted")
    return {
        "e0037_status": mapping["status"],
        "e0037_automatic_selection_allowed": mapping["automatic_selection_allowed"],
        "e0037_score_margin": mapping["score_margin"],
        "e0037_row_mapping_status_counts": status_counts,
        "e0037_search": dict(search),
        "e0038_status": "RESOLVED",
        "e0038_automatic_selection_allowed": True,
        "e0038_score_margin": 0.224488,
        "same_selected_pair_count": len(e0037_projection),
        "same_unselected_row_count": 6,
        "selected_pairs_identical": True,
        "selected_pair_projection_sha256": digest,
        "interpretation": (
            "E-0038 makes the same 58 diagnostic best-path pairs automatically decisive; "
            "it does not add new reviewed ReportNormId correctness."
        ),
    }


def extract_fixed_reviewed_identities(review: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract only row identity and reviewed ReportNormId from the frozen E-0036 result."""

    expected_keys = {
        "all_row_pairwise_agreement",
        "authority",
        "baseline_output_seal",
        "claim_boundary",
        "conditional_qwen",
        "crop_manifest",
        "dataset_role",
        "evaluation_git_commit",
        "evaluation_git_dirty",
        "experiment_id",
        "format_version",
        "human_review",
        "mapping_completed_before_human_review_registry_load",
        "numeric_row_linkage",
        "reader_evaluations",
        "request",
        "schema_graph",
        "state",
    }
    _exact_keys(review, expected_keys, "prior E-0036 reviewed evaluation")
    human_review = review.get("human_review")
    bindings = human_review.get("row_bindings") if isinstance(human_review, dict) else None
    if (
        review.get("format_version") != 1
        or review.get("experiment_id") != "E-0036"
        or review.get("dataset_role") != "CALIBRATION"
        or review.get("state") != "BASELINES_REVIEWED_QWEN_TRIGGERED"
        or review.get("mapping_completed_before_human_review_registry_load") is not True
        or not isinstance(human_review, dict)
        or human_review.get("review_id") != "HR-2026-08-06-CTG-ACB-MBB"
        or human_review.get("document_key") != "mbb-q1-2026-consolidated"
        or human_review.get("source_sha256") != _MBB_REVIEW_SOURCE_SHA256
        or human_review.get("policy") != _HUMAN_REVIEW_POLICY_ARTIFACT
        or human_review.get("dataset") != _HUMAN_REVIEW_DATASET_ARTIFACT
        or human_review.get("reviewed_row_count") != 6
        or not isinstance(bindings, list)
        or len(bindings) != 6
        or review.get("schema_graph") != _REVIEW_SCHEMA_GRAPH
    ):
        raise E0038ReviewedEvaluationError("prior reviewed-row authority drifted")
    extracted: list[dict[str, Any]] = []
    for binding in bindings:
        if not isinstance(binding, dict):
            raise E0038ReviewedEvaluationError("prior reviewed-row binding is invalid")
        sample_id = binding.get("sample_id")
        reviewed_id = binding.get("reviewed_item_id")
        visible_row_id = binding.get("visible_row_id")
        page = binding.get("page")
        row_ordinal = binding.get("row_ordinal")
        if (
            not isinstance(sample_id, str)
            or not isinstance(reviewed_id, int)
            or isinstance(reviewed_id, bool)
            or not isinstance(visible_row_id, str)
            or not isinstance(page, int)
            or isinstance(page, bool)
            or not isinstance(row_ordinal, int)
            or isinstance(row_ordinal, bool)
        ):
            raise E0038ReviewedEvaluationError("prior reviewed-row identity is invalid")
        extracted.append(
            {
                "sample_id": sample_id,
                "reviewed_report_norm_id": reviewed_id,
                "visible_row_id": visible_row_id,
                "page": page,
                "row_ordinal": row_ordinal,
            }
        )
    identities = tuple(
        (
            row["sample_id"],
            row["reviewed_report_norm_id"],
            row["visible_row_id"],
            row["page"],
            row["row_ordinal"],
        )
        for row in extracted
    )
    if identities != _FIXED_REVIEWED_IDENTITIES:
        raise E0038ReviewedEvaluationError("fixed six reviewed identities drifted")
    return extracted


def evaluate_fixed_reviewed_mapping(
    mapping: dict[str, Any],
    reviewed_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare the already-selected mapping with exactly the fixed reviewed denominator."""

    result = mapping["exact_mapping_bundle"]["exact_search"][
        "mapping_result_without_internal_alias_authority"
    ]
    all_rows = result["row_mappings"]
    by_id = {row["row_id"]: row for row in all_rows}
    if len(by_id) != 64 or len(reviewed_rows) != 6:
        raise E0038ReviewedEvaluationError("reviewed mapping denominator drifted")
    rows: list[dict[str, Any]] = []
    for reviewed in reviewed_rows:
        sample_id = reviewed["sample_id"]
        mapped = by_id.get(sample_id)
        if mapped is None:
            raise E0038ReviewedEvaluationError(f"reviewed mapping row is absent: {sample_id}")
        selected_id = mapped["selected_report_norm_id"]
        reviewed_id = reviewed["reviewed_report_norm_id"]
        rows.append(
            {
                "sample_id": sample_id,
                "visible_row_id": reviewed["visible_row_id"],
                "page": reviewed["page"],
                "row_ordinal": reviewed["row_ordinal"],
                "reviewed_report_norm_id": reviewed_id,
                "selected_report_norm_id": selected_id,
                "mapping_status": mapped["status"],
                "selected": selected_id is not None,
                "exact_report_norm_id": selected_id == reviewed_id,
                "changed_alias_target": reviewed_id in CHANGED_ALIAS_REPORT_NORM_IDS,
            }
        )
    selected = sum(row["selected"] for row in rows)
    exact = sum(row["exact_report_norm_id"] for row in rows)
    alias_coverage = sum(row["changed_alias_target"] for row in rows)
    unselected_sample_ids = {
        row["row_id"] for row in all_rows if row["selected_report_norm_id"] is None
    }
    reviewed_unselected_coverage = sum(row["sample_id"] in unselected_sample_ids for row in rows)
    status_counts = dict(sorted(Counter(row["mapping_status"] for row in rows).items()))
    evaluation = {
        "reviewed_row_count": len(rows),
        "selected_row_count": selected,
        "automatically_selected_count": selected,
        "automatically_selected_exact_count": exact,
        "unselected_row_count": len(rows) - selected,
        "abstention_count": len(rows) - selected,
        "exact_report_norm_id_count": exact,
        "wrong_report_norm_id_count": selected - exact,
        "exact_rate": exact / len(rows),
        "row_mapping_status_counts": status_counts,
        "rows": rows,
        "coverage_limits": {
            "all_mapping_source_row_count": len(all_rows),
            "source_row_reviewed_count": len(rows),
            "source_row_reviewed_rate": len(rows) / len(all_rows),
            "all_mapping_selected_row_count": sum(
                row["selected_report_norm_id"] is not None for row in all_rows
            ),
            "selected_row_reviewed_count": selected,
            "selected_row_reviewed_rate": selected
            / sum(row["selected_report_norm_id"] is not None for row in all_rows),
            "changed_alias_target_total_count": len(CHANGED_ALIAS_REPORT_NORM_IDS),
            "changed_alias_target_reviewed_count": alias_coverage,
            "changed_alias_target_reviewed_rate": (
                alias_coverage / len(CHANGED_ALIAS_REPORT_NORM_IDS)
            ),
            "all_mapping_unselected_row_count": len(unselected_sample_ids),
            "unselected_row_reviewed_count": reviewed_unselected_coverage,
            "unselected_row_reviewed_rate": (
                reviewed_unselected_coverage / len(unselected_sample_ids)
            ),
            "schema_alias_hypotheses_reviewed": False,
            "unselected_row_mechanism_reviewed": False,
        },
    }
    if (
        selected != 6
        or exact != 6
        or evaluation["automatically_selected_count"] != 6
        or evaluation["automatically_selected_exact_count"] != 6
        or evaluation["unselected_row_count"] != 0
        or evaluation["abstention_count"] != 0
        or evaluation["wrong_report_norm_id_count"] != 0
        or evaluation["exact_rate"] != 1.0
        or status_counts != _EXPECTED_REVIEWED_STATUS_COUNTS
        or alias_coverage != 0
        or reviewed_unselected_coverage != 0
        or len(unselected_sample_ids) != 6
    ):
        raise E0038ReviewedEvaluationError("pinned fixed-six reviewed outcome drifted")
    return evaluation


def _build_prior_comparison(
    review: dict[str, Any],
    e0037: dict[str, Any],
    reviewed_rows: list[dict[str, Any]],
    reviewed_e0038: dict[str, Any],
    pair_parity: dict[str, Any],
) -> dict[str, Any]:
    baseline_readers: dict[str, Any] = {}
    for reader_key in ("vietocr", "deepseek_ocr2"):
        reader = review["reader_evaluations"][reader_key]
        aggregate = reader["labels"]["aggregate"]
        mapping = reader["mapping"]
        baseline_readers[reader_key] = {
            "reader": reader["reader"],
            "label_exact_count": aggregate["exact_line_count"],
            "label_row_count": aggregate["line_count"],
            "mapping_status": mapping["status"],
            "score_margin": mapping["score_margin"],
            "reviewed_best_path_exact_count": mapping["reviewed_best_path_exact_count"],
            "reviewed_automatically_selected_exact_count": mapping[
                "reviewed_automatically_accepted_exact_count"
            ],
            "reviewed_abstention_count": mapping["reviewed_mapping_abstention_count"],
        }
    expected_baselines = {
        "vietocr": {
            "reader": "VIETOCR_VGG_TRANSFORMER",
            "label_exact_count": 3,
            "label_row_count": 6,
            "mapping_status": "AMBIGUOUS_MAPPING",
            "score_margin": 0.051282,
            "reviewed_best_path_exact_count": 6,
            "reviewed_automatically_selected_exact_count": 0,
            "reviewed_abstention_count": 6,
        },
        "deepseek_ocr2": {
            "reader": "DEEPSEEK_OCR_2",
            "label_exact_count": 1,
            "label_row_count": 6,
            "mapping_status": "AMBIGUOUS_MAPPING",
            "score_margin": 0.008494,
            "reviewed_best_path_exact_count": 6,
            "reviewed_automatically_selected_exact_count": 0,
            "reviewed_abstention_count": 6,
        },
    }
    if baseline_readers != expected_baselines:
        raise E0038ReviewedEvaluationError("E-0036 reviewed baseline comparison drifted")

    e0037_matches = e0037["mapping"]["best_path"]["matches"]
    e0037_by_id = {item["row_id"]: item["report_norm_id"] for item in e0037_matches}
    e0037_reviewed_exact = sum(
        e0037_by_id.get(row["sample_id"]) == row["reviewed_report_norm_id"] for row in reviewed_rows
    )
    if e0037_reviewed_exact != 6:
        raise E0038ReviewedEvaluationError("E-0037 fixed-six diagnostic comparison drifted")
    return {
        "same_fixed_six_reviewed_rows": True,
        "e0036_baseline_readers": baseline_readers,
        "e0037_diagnostic_best_path": {
            "mapping_status": e0037["mapping"]["status"],
            "score_margin": e0037["mapping"]["score_margin"],
            "reviewed_best_path_exact_count": e0037_reviewed_exact,
            "reviewed_automatically_selected_exact_count": 0,
            "reviewed_abstention_count": 6,
            "selected_pair_count": pair_parity["same_selected_pair_count"],
            "selected_pair_projection_sha256": pair_parity["selected_pair_projection_sha256"],
        },
        "e0038_exact_mapping": {
            "mapping_status": "RESOLVED",
            "score_margin": 0.224488,
            "reviewed_selected_exact_count": reviewed_e0038["exact_report_norm_id_count"],
            "reviewed_automatically_selected_exact_count": reviewed_e0038[
                "automatically_selected_exact_count"
            ],
            "reviewed_abstention_count": reviewed_e0038["abstention_count"],
            "selected_pair_count": pair_parity["same_selected_pair_count"],
            "selected_pair_projection_sha256": pair_parity["selected_pair_projection_sha256"],
        },
        "interpretation": (
            "E-0036 and the sealed E-0037 diagnostic best path were already 6/6 on the "
            "fixed reviewed IDs. E-0038 changes decisiveness and abstention for the same "
            "58 row-to-ID pairs; it does not create new reviewed ID correctness."
        ),
    }


def _head_bind(
    project_root: Path,
    record: Mapping[str, Any],
    *,
    name: str,
    expected_path: Path,
    reader: StableReader,
) -> None:
    try:
        _assert_tracked_record_matches_head(
            project_root,
            record,
            name=name,
            expected_path=expected_path,
            reader=reader,
        )
    except E0038ExactMappingError as exc:
        raise _fail(f"cannot bind {name} to Git HEAD", exc) from exc


def capture_e0038_reviewed_evaluation(
    project_root: Path,
    *,
    config_path: Path = CONTROL_RELATIVE_PATH,
    output_path: Path = OUTPUT_RELATIVE_PATH,
    _reader: StableReader | None = None,
) -> dict[str, Any]:
    """Validate the immutable map, then compare only the fixed six reviewed rows."""

    root = project_root.resolve()
    reader = _read_stable_file if _reader is None else _reader
    try:
        control_path = _canonical_path(root, config_path, CONTROL_RELATIVE_PATH, "review control")
        destination = _canonical_path(root, output_path, OUTPUT_RELATIVE_PATH, "review output")
        if destination.exists() or destination.is_symlink():
            raise E0038ReviewedEvaluationError(
                f"refusing to overwrite E-0038 reviewed evaluation: {destination}"
            )
        evaluation_commit = _clean_git_commit(root)
        control_stable = reader(
            root,
            control_path,
            "E-0038 reviewed evaluation control",
            maximum_size=1024 * 1024,
        )
        control = _decode_control(control_stable.payload)
        frozen, implementation = _validate_control(root, control, reader)

        # Do not move the review read above this ordered authority chain.
        seal_stable = _verified_record(
            reader,
            root,
            frozen["mapping_seal"],
            "E-0038 mapping seal",
            expected_path=MAPPING_SEAL_RELATIVE_PATH,
            maximum_size=1024 * 1024,
        )
        seal = _strict_json(seal_stable, "E-0038 mapping seal")
        _validate_mapping_seal(seal)

        registration_stable = _verified_record(
            reader,
            root,
            frozen["postseal_s3_registration"],
            "E-0038 post-seal S3 registration",
            expected_path=S3_REGISTRATION_RELATIVE_PATH,
            maximum_size=1024 * 1024,
        )
        registration = _strict_json(registration_stable, "E-0038 post-seal S3 registration")
        _validate_postseal_registration(registration, seal)

        mapping_control_stable = _verified_record(
            reader,
            root,
            frozen["mapping_control"],
            "E-0038 mapping control",
            expected_path=MAPPING_CONTROL_RELATIVE_PATH,
            maximum_size=1024 * 1024,
        )
        mapping_control = _decode_control(mapping_control_stable.payload)

        mapping_stable = _verified_record(
            reader,
            root,
            frozen["mapping_only"],
            "E-0038 mapping-only bytes",
            expected_path=MAPPING_ONLY_RELATIVE_PATH,
            maximum_size=2 * 1024 * 1024,
        )
        mapping = _strict_json(mapping_stable, "E-0038 mapping-only bytes")
        mapping_summary = _validate_mapping_payload(
            mapping,
            mapping_control,
            mapping_control_stable.artifact,
            seal,
            registration,
        )

        e0037_mapping_stable = _verified_record(
            reader,
            root,
            frozen["e0037_mapping_only"],
            "E-0037 diagnostic mapping-only bytes",
            expected_path=E0037_MAPPING_ONLY_RELATIVE_PATH,
            maximum_size=2 * 1024 * 1024,
        )
        e0037_mapping = _strict_json(e0037_mapping_stable, "E-0037 diagnostic mapping-only bytes")
        pair_parity = _validate_e0037_comparison(e0037_mapping, mapping)

        # The sole reviewed source is opened only after all sealed mapping checks pass.
        review_stable = _verified_record(
            reader,
            root,
            frozen["prior_reviewed_evaluation"],
            "pre-existing E-0036 reviewed evaluation",
            expected_path=PRIOR_REVIEW_RELATIVE_PATH,
            maximum_size=2 * 1024 * 1024,
        )
        review = _strict_json(review_stable, "pre-existing E-0036 reviewed evaluation")
        reviewed_rows = extract_fixed_reviewed_identities(review)
        reviewed_evaluation = evaluate_fixed_reviewed_mapping(mapping, reviewed_rows)
        prior_comparison = _build_prior_comparison(
            review,
            e0037_mapping,
            reviewed_rows,
            reviewed_evaluation,
            pair_parity,
        )

        payload: dict[str, Any] = {
            "identity": {
                "format_version": 1,
                "experiment_id": "E-0038",
                "dataset_role": "CALIBRATION",
                "evaluation_git_commit": evaluation_commit,
                "evaluation_git_dirty": False,
                "control": control_stable.artifact,
                "evaluator": implementation["evaluator"].artifact,
                "capture_script": implementation["capture_script"].artifact,
            },
            "state": COMPLETE_STATE,
            "input_artifacts": {
                "mapping_only": mapping_stable.artifact,
                "mapping_seal": seal_stable.artifact,
                "postseal_s3_registration": registration_stable.artifact,
                "mapping_control": mapping_control_stable.artifact,
                "e0037_mapping_only": e0037_mapping_stable.artifact,
                "prior_reviewed_evaluation": review_stable.artifact,
            },
            "pre_review_validation": {
                "validation_order": _VALIDATION_ORDER,
                "mapping_seal_validated": True,
                "postseal_s3_registration_validated": True,
                "s3_snapshot_id": S3_SNAPSHOT_ID,
                "s3_internal_restore_status": "PASS",
                "s3_isolated_hydrate_status": "PASS",
                "mapping_bytes_validated": True,
                "mapping_payload_validated_without_replay": True,
                "e0037_e0038_selected_pair_parity": pair_parity,
                **mapping_summary,
            },
            "review_access_order": {
                "mapping_seal_validated_before_review_open": True,
                "postseal_s3_registration_validated_before_review_open": True,
                "mapping_bytes_and_internal_identities_validated_before_review_open": True,
                "e0037_diagnostic_pair_parity_validated_before_review_open": True,
                "mapping_rerun_after_review_open": False,
                "mapping_mutated_after_review_open": False,
                "review_source": PRIOR_REVIEW_ARTIFACT["path"],
                "review_source_count": 1,
                "opened_input_paths": [
                    CONTROL_RELATIVE_PATH.as_posix(),
                    EVALUATOR_RELATIVE_PATH.as_posix(),
                    CAPTURE_SCRIPT_RELATIVE_PATH.as_posix(),
                    MAPPING_SEAL_RELATIVE_PATH.as_posix(),
                    S3_REGISTRATION_RELATIVE_PATH.as_posix(),
                    MAPPING_CONTROL_RELATIVE_PATH.as_posix(),
                    MAPPING_ONLY_RELATIVE_PATH.as_posix(),
                    E0037_MAPPING_ONLY_RELATIVE_PATH.as_posix(),
                    PRIOR_REVIEW_RELATIVE_PATH.as_posix(),
                ],
                "human_review_registry_loaded_directly": False,
                "review_interface_contains_numeric_fields": True,
                "numeric_fields_extracted_or_used": False,
                "separate_numeric_artifact_opened": False,
                "e0030_artifact_opened": False,
                "e0033_artifact_opened": False,
                "e0034_artifact_opened": False,
                "qwen_raw_or_rejected_output_opened": False,
                "history_or_mongodb_artifact_loaded": False,
            },
            "fixed_review_contract": dict(_REVIEW_CONTRACT),
            "review_authority_chain": {
                "human_review_policy": _HUMAN_REVIEW_POLICY_ARTIFACT,
                "human_review_dataset": _HUMAN_REVIEW_DATASET_ARTIFACT,
                "review_id": "HR-2026-08-06-CTG-ACB-MBB",
                "document_key": "mbb-q1-2026-consolidated",
                "document_source_sha256": _MBB_REVIEW_SOURCE_SHA256,
                "schema_graph": _REVIEW_SCHEMA_GRAPH,
                "target_workbook": _TARGET_WORKBOOK_ARTIFACT,
                "authority_records_opened_directly": False,
                "authority_records_bound_through_frozen_artifacts": True,
            },
            "reviewed_mapping_evaluation": reviewed_evaluation,
            "prior_comparison": prior_comparison,
            "mechanism_calibration_gate": MECHANISM_CALIBRATION_GATE,
            "conclusion": {
                "accepted_evidence": [
                    "EXACT_SEARCH_ZERO_PRUNING_MECHANICAL_EVIDENCE",
                    "FIXED_SIX_REVIEWED_ROWS_DO_NOT_CONTRADICT_SELECTED_MAPPING",
                ],
                "automatic_mapping_adoption": False,
                "schema_alias_approval": False,
                "production": False,
                "reason": (
                    "The fixed six are selected and exact, but they cover zero of two alias "
                    "targets and zero of six unselected rows."
                ),
                "next_milestone": (
                    "E-0039 schema-governed alias approval or replacement plus a "
                    "review/adjudication of the exact six unselected rows and a "
                    "review-independent unmatched-row role/acronym mechanism; numeric and "
                    "history evidence remain unused and out of scope."
                ),
            },
            "authority": {
                "dataset_role": "CALIBRATION_ONLY",
                "sealed_mapping_identity_and_s3_durability": True,
                "exact_search_zero_pruning_mechanism_evidence": True,
                "fixed_six_reviewed_non_contradiction": True,
                "mapping_accuracy_beyond_fixed_six": False,
                "schema_authority": False,
                "schema_alias_approval": False,
                "automatic_mapping_adoption": False,
                "numeric_period_or_unit": False,
                "accounting_or_excel": False,
                "history_or_mongodb": False,
                "holdout_or_production": False,
            },
            "claim_boundary": _CLAIM_BOUNDARY,
        }

        if destination.exists() or destination.is_symlink():
            raise E0038ReviewedEvaluationError(
                f"refusing to overwrite E-0038 reviewed evaluation: {destination}"
            )
        if _clean_git_commit(root) != evaluation_commit:
            raise E0038ReviewedEvaluationError(
                "Git commit changed during E-0038 reviewed evaluation"
            )
        stable_inputs = {
            "control": control_stable,
            **implementation,
            "mapping_seal": seal_stable,
            "postseal_s3_registration": registration_stable,
            "mapping_control": mapping_control_stable,
            "mapping_only": mapping_stable,
            "e0037_mapping_only": e0037_mapping_stable,
            "prior_reviewed_evaluation": review_stable,
        }
        for name, stable in stable_inputs.items():
            try:
                _assert_unchanged(reader, root, stable, f"E-0038 reviewed recheck {name}")
            except E0038ExactMappingError as exc:
                raise _fail(f"E-0038 reviewed input changed: {name}", exc) from exc
        tracked = {
            "control": (control_stable.artifact, CONTROL_RELATIVE_PATH),
            "evaluator": (implementation["evaluator"].artifact, EVALUATOR_RELATIVE_PATH),
            "capture_script": (
                implementation["capture_script"].artifact,
                CAPTURE_SCRIPT_RELATIVE_PATH,
            ),
            "mapping_seal": (seal_stable.artifact, MAPPING_SEAL_RELATIVE_PATH),
            "postseal_s3_registration": (
                registration_stable.artifact,
                S3_REGISTRATION_RELATIVE_PATH,
            ),
            "mapping_control": (
                mapping_control_stable.artifact,
                MAPPING_CONTROL_RELATIVE_PATH,
            ),
            "prior_reviewed_evaluation": (
                review_stable.artifact,
                PRIOR_REVIEW_RELATIVE_PATH,
            ),
        }
        for name, (record, path) in tracked.items():
            _head_bind(root, record, name=name, expected_path=path, reader=reader)
        if _clean_git_commit(root) != evaluation_commit:
            raise E0038ReviewedEvaluationError(
                "Git or input identity drifted before E-0038 reviewed publication"
            )
        try:
            _exclusive_publish_json(root, destination, payload)
        except E0038ExactMappingError as exc:
            raise _fail("cannot publish E-0038 reviewed evaluation", exc) from exc
        return payload
    except E0038ReviewedEvaluationError:
        raise
    except E0038ExactMappingError as exc:
        raise _fail("E-0038 reviewed evaluation failed", exc) from exc


__all__ = [
    "E0038ReviewedEvaluationError",
    "capture_e0038_reviewed_evaluation",
    "evaluate_fixed_reviewed_mapping",
    "extract_fixed_reviewed_identities",
]
