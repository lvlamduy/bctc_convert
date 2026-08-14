from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SEAL_RELATIVE_PATH = Path(
    "docs/experiments/"
    "E-0046-loan-maturity-8bank-vietocr-v3-provisional-private-core-sweep-seal.json"
)
EXPECTED_SEAL_SHA256 = "00f72d7598b35155d06ca28e60d442cef6e97420f78dc6ad7fe734e2b201acc4"
EXPECTED_PAYLOAD_IDENTITY = {
    "canonical_encoding": "UTF8_JSON_SORTED_KEYS_COMPACT_NO_NAN_WITH_TRAILING_LF_V1",
    "ephemeral_capture_path": "/tmp/e0046.json",
    "payload_sha256": "dce21ce131b55e6693fb081b4ee97f0a3fb651d0feaea8792cb6f51118118881",
    "payload_size_bytes": 6_880_612,
    "payload_tracked_in_git": False,
    "seal_only_is_tracked": True,
    "sweep_id": (
        "e0046:provisional-sweep:d94b8e059570ff71362fb18a34609ae052a499b0aa5bc6f79b59eb5b9d6b564c"
    ),
}
EXPECTED_BANK_ORDER = ("ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB")
EXPECTED_METRICS = {
    "accepted_structure_count": 0,
    "bank_count": 8,
    "bound_page_count": 8,
    "independent_mapping_evaluated_count": 0,
    "independent_numeric_evaluated_count": 0,
    "native_numeric_authority_blocked_count": 1,
    "observation_ready_count": 0,
    "ordinary_structural_evaluation_count": 6,
    "schema_candidate_ready_count": 0,
    "terminal_source_blocked_count": 1,
    "verified_mapping_count": 0,
}
EXPECTED_TRIAL_SUMMARY = (
    (
        "ACB",
        1,
        18,
        "ORDINARY_V2_PRIMARY_LINES",
        ("OWNER_NOT_RESOLVED_FROM_TRANSFORMER",),
    ),
    (
        "MBB",
        2,
        31,
        "ORDINARY_V2_PRIMARY_LINES",
        ("ROW_VALUE_AXIS_ASSIGNMENT_NOT_RESOLVED",),
    ),
    (
        "VPB",
        3,
        42,
        "HYDRATED_NATIVE_PRIMARY_LINES",
        ("NATIVE_SOURCE_NUMERIC_AUTHORITY_NOT_ADMITTED",),
    ),
    (
        "HDB",
        4,
        26,
        "ORDINARY_V2_PRIMARY_LINES",
        (
            "BRANCH_NOT_RESOLVED_FROM_TRANSFORMER",
            "OWNER_NOT_RESOLVED_FROM_TRANSFORMER",
        ),
    ),
    (
        "VCB",
        5,
        31,
        "HYDRATED_TERMINAL_LINE_SUPPLEMENT",
        (
            "NUMERIC_SOURCE_LINE_AXIS_UNAVAILABLE",
            "SOURCE_PROJECTION_TERMINAL",
            "TERMINAL_SUPPLEMENT_NOT_AUTHENTICATED_PRIMARY",
        ),
    ),
    (
        "CTG",
        6,
        39,
        "ORDINARY_V2_PRIMARY_LINES",
        (
            "ORDERED_CHILDREN_NOT_RESOLVED_FROM_TRANSFORMER",
            "OWNER_NOT_RESOLVED_FROM_TRANSFORMER",
        ),
    ),
    (
        "BID",
        7,
        22,
        "ORDINARY_V2_PRIMARY_LINES",
        (
            "PER_AXIS_UNIT_SCOPE_NOT_RESOLVED",
            "ROW_VALUE_AXIS_ASSIGNMENT_NOT_RESOLVED",
        ),
    ),
    (
        "VIB",
        8,
        33,
        "ORDINARY_V2_PRIMARY_LINES",
        ("ROW_VALUE_AXIS_ASSIGNMENT_NOT_RESOLVED",),
    ),
)


class SealValidationError(ValueError):
    pass


def _reject_constant(value: str) -> None:
    raise SealValidationError(f"non-finite JSON constant is forbidden: {value}")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SealValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _decode(raw: bytes) -> dict[str, Any]:
    payload = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=_reject_constant,
    )
    if type(payload) is not dict:
        raise SealValidationError("seal root must be an object")
    return payload


def _encoded(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            indent=2,
            separators=(",", ": "),
        )
        + "\n"
    ).encode("utf-8")


def _assert_exact_keys(value: object, expected: set[str], label: str) -> None:
    if type(value) is not dict:
        raise SealValidationError(f"{label} must be an object")
    actual = set(value)
    if actual != expected:
        raise SealValidationError(
            f"{label} keys differ: missing={sorted(expected - actual)!r} "
            f"extra={sorted(actual - expected)!r}"
        )


def _validate_closed_shape(payload: dict[str, Any]) -> None:
    _assert_exact_keys(
        payload,
        {
            "artifact_identity",
            "audit",
            "bank_order",
            "claim_boundary",
            "code_identity",
            "experiment_id",
            "family_id",
            "format_version",
            "input_identities",
            "metrics",
            "performance_debt",
            "safety",
            "state",
            "trials",
        },
        "seal",
    )
    _assert_exact_keys(
        payload["artifact_identity"],
        {
            "canonical_encoding",
            "ephemeral_capture_path",
            "payload_sha256",
            "payload_size_bytes",
            "payload_tracked_in_git",
            "seal_only_is_tracked",
            "sweep_id",
        },
        "artifact_identity",
    )
    _assert_exact_keys(
        payload["audit"],
        {
            "audited_git_head",
            "correctness_or_release_blocker",
            "payload_canonical_json_with_trailing_lf",
            "payload_identity_recomputed_from_ephemeral_capture",
            "verdict",
        },
        "audit",
    )
    _assert_exact_keys(
        payload["code_identity"],
        {
            "formal_inference_commit",
            "formal_selection_commit",
            "formal_source_tree_oid",
            "formal_vietocr_freeze_commit",
            "records",
        },
        "code_identity",
    )
    for index, record in enumerate(payload["code_identity"]["records"]):
        _assert_exact_keys(record, {"capture_commit", "path", "sha256"}, f"record[{index}]")
    _assert_exact_keys(
        payload["input_identities"],
        {
            "formal_freeze",
            "formal_run_selection",
            "formal_semantic_receipt",
            "panel_selection_projection",
            "ready_anonymous_batch",
            "ready_panel_audit_receipt",
        },
        "input_identities",
    )
    input_shapes = {
        "formal_freeze": {"freeze_id", "line_count_vector", "page_count", "sample_count"},
        "formal_run_selection": {"path", "selection_id", "sha256", "size_bytes"},
        "formal_semantic_receipt": {"receipt_id", "state"},
        "panel_selection_projection": {"panel_state", "projection_id"},
        "ready_anonymous_batch": {"batch_id", "state"},
        "ready_panel_audit_receipt": {"audit_id"},
    }
    for name, keys in input_shapes.items():
        _assert_exact_keys(payload["input_identities"][name], keys, f"input_identities.{name}")
    _assert_exact_keys(payload["metrics"], set(EXPECTED_METRICS), "metrics")
    _assert_exact_keys(
        payload["performance_debt"],
        {
            "correctness_blocker",
            "logical_reads_exceeded_200_gb",
            "observed_artifact_mtime_utc",
            "observed_started_at_utc",
            "observed_wall_time_seconds_approximate",
            "required_follow_up",
            "source",
            "status",
        },
        "performance_debt",
    )
    _assert_exact_keys(
        payload["safety"],
        {
            "accepted_structure_authority",
            "accounting_truth_authority",
            "canonicalization_authority",
            "export_authority",
            "independent_mapping_verification_performed",
            "independent_numeric_verification_performed",
            "mapping_authority",
            "numeric_authority",
            "payload_self_authenticates",
            "private_core_derivation",
            "production_authority",
            "public_validation_requires_live_rebuild",
            "schema_mapping_performed",
            "value_materialization_authority",
            "verified_by_codex_claimed",
        },
        "safety",
    )
    if type(payload["trials"]) is not list or len(payload["trials"]) != 8:
        raise SealValidationError("trials must contain exactly eight objects")
    trial_keys = {
        "bank_code",
        "binding_mode",
        "independent_mapping_status",
        "independent_numeric_status",
        "observation_status",
        "page_ordinal",
        "physical_page",
        "schema_candidate_status",
        "semantic_graph_status",
        "unresolved_reasons",
        "verified_by_codex",
    }
    for index, trial in enumerate(payload["trials"]):
        _assert_exact_keys(trial, trial_keys, f"trial[{index}]")


def _validate_seal(payload: dict[str, Any]) -> None:
    _validate_closed_shape(payload)
    if payload["artifact_identity"] != EXPECTED_PAYLOAD_IDENTITY:
        raise SealValidationError("payload identity differs from audited E0046 capture")
    if tuple(payload["bank_order"]) != EXPECTED_BANK_ORDER:
        raise SealValidationError("bank order differs from fixed E0046 panel")
    if payload["metrics"] != EXPECTED_METRICS:
        raise SealValidationError("metrics differ from the audited fail-closed result")
    trials = tuple(
        (
            trial["bank_code"],
            trial["page_ordinal"],
            trial["physical_page"],
            trial["binding_mode"],
            tuple(trial["unresolved_reasons"]),
        )
        for trial in payload["trials"]
    )
    if trials != EXPECTED_TRIAL_SUMMARY:
        raise SealValidationError("trial page, mode, or blocker summary differs")
    if any(
        trial["observation_status"] != "UNRESOLVED"
        or trial["semantic_graph_status"] != "UNRESOLVED"
        or trial["schema_candidate_status"] != "UNRESOLVED_GRAPH_NOT_ACCEPTED"
        or trial["independent_numeric_status"] != "NOT_EVALUATED"
        or trial["independent_mapping_status"] != "NOT_EVALUATED"
        or trial["verified_by_codex"] is not False
        for trial in payload["trials"]
    ):
        raise SealValidationError("a fail-closed trial was promoted")
    safety = payload["safety"]
    if safety["private_core_derivation"] is not True:
        raise SealValidationError("private-core derivation marker is required")
    if safety["public_validation_requires_live_rebuild"] is not True:
        raise SealValidationError("live public rebuild requirement is required")
    if any(
        safety[key] is not False
        for key in safety
        if key not in {"private_core_derivation", "public_validation_requires_live_rebuild"}
    ):
        raise SealValidationError("the seal cannot grant mapping, numeric, or export authority")
    if hashlib.sha256(_encoded(payload)).hexdigest() != EXPECTED_SEAL_SHA256:
        raise SealValidationError("seal content hash differs from the audited closed payload")


def _load_formal_seal() -> tuple[bytes, dict[str, Any]]:
    raw = (REPOSITORY_ROOT / SEAL_RELATIVE_PATH).read_bytes()
    return raw, _decode(raw)


def test_formal_seal_is_canonical_closed_shape_and_hash_bound() -> None:
    raw, payload = _load_formal_seal()

    assert raw == _encoded(payload)
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_SEAL_SHA256
    _validate_seal(payload)


def test_seal_pins_capture_commit_code_and_formal_selection_bytes() -> None:
    _, payload = _load_formal_seal()

    for record in payload["code_identity"]["records"]:
        captured = subprocess.check_output(
            ["git", "show", f"{record['capture_commit']}:{record['path']}"],
            cwd=REPOSITORY_ROOT,
        )
        assert hashlib.sha256(captured).hexdigest() == record["sha256"]

    selection = payload["input_identities"]["formal_run_selection"]
    selection_bytes = (REPOSITORY_ROOT / selection["path"]).read_bytes()
    assert len(selection_bytes) == selection["size_bytes"]
    assert hashlib.sha256(selection_bytes).hexdigest() == selection["sha256"]

    audited_head = payload["audit"]["audited_git_head"]
    source_tree_oid = subprocess.check_output(
        ["git", "rev-parse", f"{audited_head}:src/bctc_ai"],
        cwd=REPOSITORY_ROOT,
        text=True,
    ).strip()
    assert source_tree_oid == payload["code_identity"]["formal_source_tree_oid"]


def _tamper_payload_hash(payload: dict[str, Any]) -> None:
    payload["artifact_identity"]["payload_sha256"] = "0" * 64


def _tamper_metric(payload: dict[str, Any]) -> None:
    payload["metrics"]["accepted_structure_count"] = 1


def _tamper_trial_promotion(payload: dict[str, Any]) -> None:
    payload["trials"][1]["verified_by_codex"] = True


def _tamper_trial_blocker(payload: dict[str, Any]) -> None:
    payload["trials"][4]["unresolved_reasons"].pop()


def _tamper_authority(payload: dict[str, Any]) -> None:
    payload["safety"]["mapping_authority"] = True


def _tamper_shape(payload: dict[str, Any]) -> None:
    payload["unexpected_claim"] = True


@pytest.mark.parametrize(
    "mutator",
    (
        _tamper_payload_hash,
        _tamper_metric,
        _tamper_trial_promotion,
        _tamper_trial_blocker,
        _tamper_authority,
        _tamper_shape,
    ),
)
def test_tampered_seal_is_rejected(mutator: Callable[[dict[str, Any]], None]) -> None:
    _, payload = _load_formal_seal()
    mutated = copy.deepcopy(payload)
    mutator(mutated)

    with pytest.raises(SealValidationError):
        _validate_seal(mutated)
