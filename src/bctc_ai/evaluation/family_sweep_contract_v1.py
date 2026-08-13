"""Fail-closed aggregate contract for one accounting family across a bank panel.

The module is orchestration/accounting only.  It does not discover pages, run a
reader, recognize a family, map schema rows, or independently verify a mapping.
It preserves the outputs of those separate authorities and makes denominator
inflation mechanically difficult: a schema candidate is never counted as an
accepted mapping and unresolved variants remain first-class trial outcomes.
"""

from __future__ import annotations

import hashlib
import re
import weakref
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import (
    validate_semantic_local_accounting_schema_candidate_replay_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    decode_canonical_json_bytes_v1,
    same_typed_json_v1,
)
from bctc_ai.source_structure.local_accounting_graph_v1 import (
    FamilySpecV1,
    local_accounting_family_spec_sha256_v1,
)
from bctc_ai.source_structure.semantic_local_accounting_graph_v2 import (
    validate_semantic_local_accounting_graph_replay_v2,
)
from bctc_ai.source_structure.semantic_statement_context_v1 import (
    validate_semantic_statement_context_replay_v1,
)

__all__ = [
    "BANK_PANEL_V1",
    "CLAIM_BOUNDARY",
    "FORMAT_VERSION_MANIFEST",
    "FORMAT_VERSION_RESULT",
    "SAFETY",
    "AuthenticatedFamilySweepTrialV1",
    "FamilySweepContractV1Error",
    "authenticate_family_sweep_trial_v1",
    "build_family_sweep_manifest_v1",
    "build_family_sweep_result_v1",
    "validate_family_sweep_manifest_v1",
    "validate_family_sweep_result_v1",
]


BANK_PANEL_V1 = ("ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB")
FORMAT_VERSION_MANIFEST = "BANK_CORPUS_ACCOUNTING_FAMILY_SWEEP_MANIFEST_V1"
FORMAT_VERSION_RESULT = "BANK_CORPUS_ACCOUNTING_FAMILY_SWEEP_RESULT_V1"
CLAIM_BOUNDARY = (
    "ONE_FAMILY_REPLAY_AUTHENTICATED_FIXED_EIGHT_BANK_SOURCE_SELECTION_AND_AGGREGATION_"
    "OF_REPLAY_AUTHENTICATED_UPSTREAM_"
    "ARTIFACT_DISPOSITIONS_ONLY_STRICT_SUBSET_ACCEPTED_VARIANTS_PRESERVED_UNRESOLVED_"
    "SCHEMA_CANDIDATES_NEVER_COUNTED_AS_VERIFIED_MAPPING_NO_PAGE_FAMILY_SOURCE_OR_"
    "PRODUCTION_EXHAUSTIVENESS_NO_CANONICALIZATION_VALUE_MATERIALIZATION_OR_EXPORT_AUTHORITY"
)
_SAFETY_ITEMS: tuple[tuple[str, bool], ...] = (
    ("bank_identity_used_for_routing", False),
    ("filename_used_for_routing", False),
    ("page_number_used_for_routing", False),
    ("bank_specific_logic_allowed", False),
    ("page_specific_logic_allowed", False),
    ("role_a_or_human_gold_used_for_role_b_inference", False),
    ("history_used_for_routing_or_acceptance", False),
    ("schema_candidate_promoted_to_mapping", False),
    ("unresolved_variant_discarded", False),
    ("statement_context_required_for_structural_aggregation", False),
    ("numeric_verification_required_for_structural_aggregation", False),
    ("source_page_exhaustiveness_claimed", False),
    ("family_occurrence_exhaustiveness_claimed", False),
    ("bank_panel_production_representativeness_claimed", False),
    ("canonicalization_authority", False),
    ("value_materialization_authority", False),
    ("export_authority", False),
    ("raw_or_serialized_trial_receipt_accepted", False),
    ("raw_or_serialized_panel_selection_projection_accepted", False),
    ("caller_bank_or_source_identity_allowed", False),
    ("persisted_manifest_self_authenticating", False),
    ("persisted_result_self_authenticating", False),
    ("opaque_live_trial_capability_required", True),
    ("opaque_live_panel_selection_capability_required", True),
)
SAFETY = dict(_SAFETY_ITEMS)

_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_TRIAL_ID_RE = re.compile(r"^trial-[0-9]{4}$")
_SOURCE_PAGE_ID_RE = re.compile(r"^ssv2:page:[0-9a-f]{64}$")
_GRAPH_ID_RE = re.compile(r"^slagv2:graph:[0-9a-f]{64}$")
_CANDIDATE_ID_RE = re.compile(r"^slascv1:candidate:[0-9a-f]{64}$")
_CONTEXT_ID_RE = re.compile(r"^sscxtv1:context:[0-9a-f]{64}$")
_VERIFICATION_ID_RE = re.compile(r"^[a-z][a-z0-9_]*:[a-z][a-z0-9_]*:[0-9a-f]{64}$")

_OBSERVATION_STATUSES = {"READY_FOR_GRAPH_V2", "UNRESOLVED"}
_GRAPH_ACCEPTED = "ACCEPTED_WITHIN_SUPPLIED_FAMILY_COLLISION_SCOPE"
_GRAPH_STATUSES = {_GRAPH_ACCEPTED, "UNRESOLVED"}
_SCHEMA_CANDIDATE_STATUSES = {
    "CANDIDATE_SET_READY",
    "UNRESOLVED_GRAPH_NOT_ACCEPTED",
    "NOT_EVALUATED",
}
_CONTEXT_STATUSES = {
    "RESOLVED_VISIBLE_PAGE_STATEMENT_CONTEXT",
    "UNRESOLVED_VISIBLE_PAGE_STATEMENT_CONTEXT",
    "NOT_EVALUATED",
}
_NUMERIC_STATUSES = {"VERIFIED", "UNRESOLVED", "NOT_EVALUATED"}
_MAPPING_STATUSES = {"VERIFIED_BY_CODEX", "UNRESOLVED", "NOT_EVALUATED"}
_ROW_VERDICTS = {"VERIFIED_BY_CODEX", "UNRESOLVED"}
_MAPPING_VERIFICATION_PROTOCOL = "CODEX_MAPPED_ITEM_VERIFICATION_V1"
_CHECK_DISPOSITIONS = {"PASS", "NOT_APPLICABLE", "FAIL"}
_REQUIRED_ROW_CHECKS = (
    "replay_authenticated_source_or_pdf_evidence",
    "exact_visible_label_and_candidate_report_norm_id",
    "parent_child_sibling_and_workbook_display_order",
    "number_sign_period_unit_and_scope",
    "applicable_arithmetic_and_accounting_checks",
    "near_neighbor_schema_collision_falsifiers",
)
_NEAR_NEIGHBOR_IDS = (5747, 1944)
_PANEL_SELECTION_FIELDS = {
    "format_version",
    "projection_id",
    "experiment_id",
    "family_id",
    "manifest_sha256",
    "manifest_size_bytes",
    "panel_state",
    "bank_order",
    "slots",
    "authority",
}
_PANEL_SELECTION_FORMAT_VERSION = "LOAN_MATURITY_8BANK_AUTHENTICATED_PANEL_SELECTION_PROJECTION_V1"
_PANEL_SELECTION_AUTHORITY = {
    "selection_provenance_only": True,
    "recognition_routing_authority": False,
    "hydration_authority": False,
    "semantic_authority": False,
    "numeric_authority": False,
    "mapping_authority": False,
    "completed_vietocr_run_authority": False,
}
_PANEL_SELECTION_STATES = {
    "BLOCKED_PENDING_COMPLETE_8_SLOT_HYDRATION",
    "READY_FOR_SINGLE_OPAQUE_8_PAGE_FREEZE",
}


class FamilySweepContractV1Error(ValueError):
    """A sweep denominator, authority boundary, or aggregate count drifted."""


_TRIAL_MINT_TOKEN = object()
_AUTHENTICATED_TRIALS: weakref.WeakKeyDictionary[
    AuthenticatedFamilySweepTrialV1, tuple[bytes, str]
] = weakref.WeakKeyDictionary()


class AuthenticatedFamilySweepTrialV1:
    """Opaque live authority minted only after exact public upstream replay."""

    __slots__ = ("__weakref__",)

    def __init__(self, token: object) -> None:
        if token is not _TRIAL_MINT_TOKEN:
            raise _error("authenticated family-sweep trials cannot be caller-constructed")

    def __copy__(self) -> None:
        raise _error("authenticated family-sweep trials cannot be copied")

    def __deepcopy__(self, _memo: object) -> None:
        raise _error("authenticated family-sweep trials cannot be deep-copied")

    def __reduce__(self) -> None:
        raise _error("authenticated family-sweep trials cannot be serialized")


def _error(message: str) -> FamilySweepContractV1Error:
    return FamilySweepContractV1Error(message)


def _fixed_safety() -> dict[str, bool]:
    return dict(_SAFETY_ITEMS)


def _exact_dict(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise _error(f"{label} fields drifted")
    return value


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or _SHA_RE.fullmatch(value) is None:
        raise _error(f"{label} is not a lowercase SHA-256")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise _error(f"{label} is not a nonnegative integer")
    return value


def _identity(value: Any, pattern: re.Pattern[str], label: str) -> str:
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise _error(f"{label} identity drifted")
    return value


def _manifest_without_id(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: canonical_clone_v1(item) for key, item in value.items() if key != "manifest_id"}


def _result_without_id(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: canonical_clone_v1(item) for key, item in value.items() if key != "result_id"}


def _project_panel_selection(panel_selection_authority: Any) -> dict[str, Any]:
    """Consume the panel module's live capability; raw projections have no path."""

    from bctc_ai.evaluation.loan_maturity_8bank_panel_prerequisite_v1 import (
        project_authenticated_loan_maturity_8bank_panel_selection_v1,
    )

    return project_authenticated_loan_maturity_8bank_panel_selection_v1(panel_selection_authority)


def _replay_panel_selection(panel_selection_authority: Any) -> dict[str, Any]:
    try:
        projected = _project_panel_selection(panel_selection_authority)
    except ValueError as exc:
        raise _error("family sweep requires exact live panel selection replay") from exc
    return _validate_panel_selection_projection(projected)


def _validate_panel_selection_projection(value: Any) -> dict[str, Any]:
    selection = _exact_dict(value, _PANEL_SELECTION_FIELDS, "panel selection authority")
    if (
        selection["format_version"] != _PANEL_SELECTION_FORMAT_VERSION
        or type(selection["projection_id"]) is not str
        or re.fullmatch(r"lm8bpsv1:projection:[0-9a-f]{64}", selection["projection_id"]) is None
        or selection["experiment_id"] != "E-0044"
        or selection["family_id"] != "LOAN_MATURITY_BUCKETS"
        or not same_typed_json_v1(selection["bank_order"], list(BANK_PANEL_V1))
    ):
        raise _error("panel selection identity or fixed bank order drifted")
    expected_projection_id = "lm8bpsv1:projection:" + canonical_json_sha256_v1(
        {key: item for key, item in selection.items() if key != "projection_id"}
    )
    if selection["projection_id"] != expected_projection_id:
        raise _error("panel selection projection identity drifted")
    _sha(selection["manifest_sha256"], "panel selection manifest")
    if type(selection["manifest_size_bytes"]) is not int or selection["manifest_size_bytes"] <= 0:
        raise _error("panel selection manifest size drifted")
    if selection["panel_state"] not in _PANEL_SELECTION_STATES:
        raise _error("panel selection state drifted")
    if not same_typed_json_v1(selection["authority"], _PANEL_SELECTION_AUTHORITY):
        raise _error("panel selection authority boundary drifted")
    slots = selection["slots"]
    if type(slots) is not list or [item.get("bank_code") for item in slots] != list(BANK_PANEL_V1):
        raise _error("panel selection slots differ from the fixed bank panel")
    seen_sources: set[str] = set()
    for slot in slots:
        _exact_dict(
            slot,
            {"bank_code", "source_pdf_sha256", "physical_page"},
            "panel selection slot",
        )
        source_sha = _sha(slot["source_pdf_sha256"], "panel selection source PDF")
        if source_sha in seen_sources:
            raise _error("panel selection must bind eight distinct bank source PDFs")
        seen_sources.add(source_sha)
        if type(slot["physical_page"]) is not int or slot["physical_page"] <= 0:
            raise _error("panel selection physical page drifted")
    return canonical_clone_v1(selection)


def build_family_sweep_manifest_v1(
    family_spec: FamilySpecV1,
    family_specs_for_collision_scope: Sequence[FamilySpecV1],
    bank_trial_plans: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    panel_selection_authority: Any,
) -> dict[str, Any]:
    """Freeze one family and exact trial denominator for the fixed bank panel."""

    panel_selection = _replay_panel_selection(panel_selection_authority)
    if type(family_spec) is not FamilySpecV1:
        raise _error("sweep target must be one exact FamilySpecV1")
    if panel_selection["family_id"] != family_spec.family_id:
        raise _error("panel selection authority belongs to another accounting family")
    if (
        isinstance(family_specs_for_collision_scope, (str, bytes, bytearray))
        or not isinstance(family_specs_for_collision_scope, Sequence)
        or not family_specs_for_collision_scope
        or any(type(spec) is not FamilySpecV1 for spec in family_specs_for_collision_scope)
    ):
        raise _error("collision scope must be a non-empty FamilySpecV1 sequence")
    scope = {
        spec.family_id: local_accounting_family_spec_sha256_v1(spec)
        for spec in family_specs_for_collision_scope
    }
    if len(scope) != len(family_specs_for_collision_scope):
        raise _error("collision scope repeats a family identity")
    target_sha = local_accounting_family_spec_sha256_v1(family_spec)
    if scope.get(family_spec.family_id) != target_sha:
        raise _error("target family is absent or hash-drifted in collision scope")
    if type(bank_trial_plans) is not dict or tuple(bank_trial_plans) != BANK_PANEL_V1:
        raise _error("sweep manifest requires the exact ordered eight-bank panel")

    bank_entries: list[dict[str, Any]] = []
    seen_trial_ids: set[str] = set()
    seen_source_locators: set[tuple[str, int, int, str]] = set()
    selection_by_bank = {slot["bank_code"]: slot for slot in panel_selection["slots"]}
    for bank in BANK_PANEL_V1:
        selected = selection_by_bank[bank]
        plans = bank_trial_plans[bank]
        if isinstance(plans, (str, bytes, bytearray)) or not isinstance(plans, Sequence):
            raise _error(f"{bank} trial plans must be one sequence")
        trials: list[dict[str, Any]] = []
        for raw in plans:
            plan = _exact_dict(
                raw,
                {
                    "trial_id",
                    "source_size_bytes",
                    "source_local_page_id",
                },
                f"{bank} trial plan",
            )
            trial_id = _identity(plan["trial_id"], _TRIAL_ID_RE, "trial")
            if trial_id in seen_trial_ids:
                raise _error("trial identities must be globally unique within a sweep")
            seen_trial_ids.add(trial_id)
            if type(plan["source_size_bytes"]) is not int or plan["source_size_bytes"] <= 0:
                raise _error("source size must be positive")
            _identity(plan["source_local_page_id"], _SOURCE_PAGE_ID_RE, "source page")
            source_locator = (
                selected["source_pdf_sha256"],
                plan["source_size_bytes"],
                selected["physical_page"],
                plan["source_local_page_id"],
            )
            if source_locator in seen_source_locators:
                raise _error("source locators must be globally unique across bank slots")
            seen_source_locators.add(source_locator)
            trials.append(
                {
                    "trial_id": trial_id,
                    "source_sha256": selected["source_pdf_sha256"],
                    "source_size_bytes": plan["source_size_bytes"],
                    "physical_page": selected["physical_page"],
                    "source_local_page_id": plan["source_local_page_id"],
                }
            )
        bank_entries.append({"bank": bank, "trials": trials})

    payload = {
        "format_version": FORMAT_VERSION_MANIFEST,
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": family_spec.family_id,
        "family_spec_sha256": target_sha,
        "panel_selection_authority": panel_selection,
        "supplied_family_collision_scope_spec_sha256_by_id": dict(sorted(scope.items())),
        "bank_panel": list(BANK_PANEL_V1),
        "banks": bank_entries,
        "metrics": {
            "panel_bank_count": len(BANK_PANEL_V1),
            "planned_bank_count": sum(bool(item["trials"]) for item in bank_entries),
            "planned_trial_count": sum(len(item["trials"]) for item in bank_entries),
        },
        "safety": _fixed_safety(),
    }
    payload["manifest_id"] = "fsv1:manifest:" + canonical_json_sha256_v1(payload)
    return _validate_family_sweep_manifest_shape_v1(payload, panel_selection)


def _validate_family_sweep_manifest_shape_v1(
    value: Any, panel_selection: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate the manifest against an already replay-authenticated selection."""

    manifest = _exact_dict(
        value,
        {
            "format_version",
            "claim_boundary",
            "manifest_id",
            "family_id",
            "family_spec_sha256",
            "panel_selection_authority",
            "supplied_family_collision_scope_spec_sha256_by_id",
            "bank_panel",
            "banks",
            "metrics",
            "safety",
        },
        "family sweep manifest",
    )
    if (
        manifest["format_version"] != FORMAT_VERSION_MANIFEST
        or manifest["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(manifest["safety"], _fixed_safety())
        or manifest["bank_panel"] != list(BANK_PANEL_V1)
        or not same_typed_json_v1(manifest["panel_selection_authority"], panel_selection)
    ):
        raise _error("family sweep manifest policy drifted")
    if (
        type(manifest["family_id"]) is not str
        or not manifest["family_id"]
        or manifest["family_id"] != panel_selection["family_id"]
    ):
        raise _error("manifest family identity drifted")
    family_sha = _sha(manifest["family_spec_sha256"], "manifest family spec")
    scope = manifest["supplied_family_collision_scope_spec_sha256_by_id"]
    if (
        type(scope) is not dict
        or not scope
        or list(scope) != sorted(scope)
        or any(type(key) is not str or not key for key in scope)
        or any(type(item) is not str or _SHA_RE.fullmatch(item) is None for item in scope.values())
        or scope.get(manifest["family_id"]) != family_sha
    ):
        raise _error("manifest collision-scope identity drifted")
    banks = manifest["banks"]
    if type(banks) is not list or [item.get("bank") for item in banks] != list(BANK_PANEL_V1):
        raise _error("manifest bank slots differ from the fixed panel")
    seen: set[str] = set()
    seen_source_locators: set[tuple[str, int, int, str]] = set()
    planned_bank_count = 0
    planned_trial_count = 0
    selection_by_bank = {slot["bank_code"]: slot for slot in panel_selection["slots"]}
    for bank_entry in banks:
        _exact_dict(bank_entry, {"bank", "trials"}, "manifest bank entry")
        trials = bank_entry["trials"]
        if type(trials) is not list:
            raise _error("manifest bank trials are not one sequence")
        planned_bank_count += bool(trials)
        planned_trial_count += len(trials)
        for trial in trials:
            _exact_dict(
                trial,
                {
                    "trial_id",
                    "source_sha256",
                    "source_size_bytes",
                    "physical_page",
                    "source_local_page_id",
                },
                "manifest trial",
            )
            trial_id = _identity(trial["trial_id"], _TRIAL_ID_RE, "manifest trial")
            if trial_id in seen:
                raise _error("manifest repeats a trial identity")
            seen.add(trial_id)
            _sha(trial["source_sha256"], "manifest source")
            _identity(trial["source_local_page_id"], _SOURCE_PAGE_ID_RE, "manifest source page")
            if (
                type(trial["source_size_bytes"]) is not int
                or trial["source_size_bytes"] <= 0
                or type(trial["physical_page"]) is not int
                or trial["physical_page"] <= 0
            ):
                raise _error("manifest source locator drifted")
            selected = selection_by_bank[bank_entry["bank"]]
            if (
                trial["source_sha256"] != selected["source_pdf_sha256"]
                or trial["physical_page"] != selected["physical_page"]
            ):
                raise _error("manifest bank/source/page differs from authenticated panel selection")
            source_locator = (
                trial["source_sha256"],
                trial["source_size_bytes"],
                trial["physical_page"],
                trial["source_local_page_id"],
            )
            if source_locator in seen_source_locators:
                raise _error("manifest repeats a source locator across bank slots")
            seen_source_locators.add(source_locator)
    metrics = _exact_dict(
        manifest["metrics"],
        {"panel_bank_count", "planned_bank_count", "planned_trial_count"},
        "manifest metrics",
    )
    if not same_typed_json_v1(
        metrics,
        {
            "panel_bank_count": len(BANK_PANEL_V1),
            "planned_bank_count": planned_bank_count,
            "planned_trial_count": planned_trial_count,
        },
    ):
        raise _error("manifest metrics drifted")
    expected_id = "fsv1:manifest:" + canonical_json_sha256_v1(_manifest_without_id(manifest))
    if manifest["manifest_id"] != expected_id:
        raise _error("manifest identity drifted")
    return canonical_clone_v1(manifest)


def validate_family_sweep_manifest_v1(
    value: Any, *, panel_selection_authority: Any
) -> dict[str, Any]:
    """Replay the live panel selection and validate one persisted manifest."""

    selection = _replay_panel_selection(panel_selection_authority)
    return _validate_family_sweep_manifest_shape_v1(value, selection)


def _validate_structural_refs(
    receipt: Mapping[str, Any], plan: Mapping[str, Any], manifest: Mapping[str, Any]
) -> tuple[bool, dict[str, Any], dict[str, Any]]:
    observation = _exact_dict(
        receipt["observation"],
        {"artifact_sha256", "status", "unresolved_reasons"},
        "trial observation",
    )
    _sha(observation["artifact_sha256"], "observation")
    if observation["status"] not in _OBSERVATION_STATUSES:
        raise _error("observation disposition drifted")
    if (
        type(observation["unresolved_reasons"]) is not list
        or observation["unresolved_reasons"] != sorted(set(observation["unresolved_reasons"]))
        or any(
            type(reason) is not str or not reason for reason in observation["unresolved_reasons"]
        )
        or (observation["status"] == "UNRESOLVED") != bool(observation["unresolved_reasons"])
    ):
        raise _error("observation unresolved reasons drifted")
    graph = _exact_dict(
        receipt["semantic_graph"],
        {
            "graph_id",
            "artifact_sha256",
            "status",
            "accepted_counts",
            "unresolved_reasons",
        },
        "trial semantic graph",
    )
    _identity(graph["graph_id"], _GRAPH_ID_RE, "semantic graph")
    _sha(graph["artifact_sha256"], "semantic graph")
    if graph["status"] not in _GRAPH_STATUSES:
        raise _error("semantic graph disposition drifted")
    accepted_counts = _exact_dict(
        graph["accepted_counts"],
        {"TABLE", "LOGICAL_ROW", "VALUE_POSITION", "AXIS", "HIERARCHY"},
        "semantic graph accepted counts",
    )
    for key, value in accepted_counts.items():
        _nonnegative_int(value, f"semantic graph {key} count")
    reasons = graph["unresolved_reasons"]
    if (
        type(reasons) is not list
        or reasons != sorted(set(reasons))
        or any(type(reason) is not str or not reason for reason in reasons)
    ):
        raise _error("semantic graph unresolved reasons drifted")
    accepted = graph["status"] == _GRAPH_ACCEPTED
    if accepted:
        if (
            observation["status"] != "READY_FOR_GRAPH_V2"
            or reasons
            or any(
                accepted_counts[key] <= 0
                for key in ("TABLE", "LOGICAL_ROW", "VALUE_POSITION", "AXIS")
            )
        ):
            raise _error("accepted graph is not backed by one ready nonempty strict subset")
    elif observation["status"] != "UNRESOLVED" or any(accepted_counts.values()) or not reasons:
        raise _error("unresolved graph persisted accepted structure or lost reasons")
    if (
        receipt["source_sha256"] != plan["source_sha256"]
        or receipt["source_size_bytes"] != plan["source_size_bytes"]
        or receipt["physical_page"] != plan["physical_page"]
        or receipt["source_local_page_id"] != plan["source_local_page_id"]
        or receipt["family_id"] != manifest["family_id"]
        or receipt["family_spec_sha256"] != manifest["family_spec_sha256"]
        or receipt["supplied_family_collision_scope_spec_sha256_by_id"]
        != manifest["supplied_family_collision_scope_spec_sha256_by_id"]
    ):
        raise _error("trial receipt differs from its frozen source/family plan")
    _sha(receipt["source_projection_sha256"], "source projection")
    _sha(receipt["semantic_page_binding_sha256"], "semantic page binding")
    return accepted, observation, graph


def _validate_schema_candidate(value: Any, *, accepted: bool) -> tuple[dict[str, Any], int]:
    candidate = _exact_dict(
        value,
        {"candidate_set_id", "artifact_sha256", "status", "candidate_role_count"},
        "schema candidate",
    )
    if candidate["status"] not in _SCHEMA_CANDIDATE_STATUSES:
        raise _error("schema candidate disposition drifted")
    count = _nonnegative_int(candidate["candidate_role_count"], "schema candidate role")
    if candidate["status"] == "NOT_EVALUATED":
        if (
            candidate["candidate_set_id"] is not None
            or candidate["artifact_sha256"] is not None
            or count
        ):
            raise _error("non-evaluated schema candidate carries candidate authority")
    else:
        _identity(candidate["candidate_set_id"], _CANDIDATE_ID_RE, "schema candidate")
        _sha(candidate["artifact_sha256"], "schema candidate")
    if candidate["status"] == "CANDIDATE_SET_READY":
        if not accepted or count <= 0:
            raise _error("ready schema candidate is not downstream of an accepted graph")
    elif count:
        raise _error("unready schema candidate persisted candidate rows")
    if accepted and candidate["status"] == "UNRESOLVED_GRAPH_NOT_ACCEPTED":
        raise _error("accepted graph was relabelled as graph-not-accepted schema candidate")
    if not accepted and candidate["status"] == "CANDIDATE_SET_READY":
        raise _error("unresolved graph was promoted to a ready schema candidate")
    return candidate, count


def _validate_optional_dispositions(
    receipt: Mapping[str, Any], *, accepted: bool
) -> tuple[dict[str, Any], dict[str, Any]]:
    context = _exact_dict(
        receipt["statement_context"],
        {"context_id", "artifact_sha256", "status", "unresolved_reasons"},
        "statement context",
    )
    if context["status"] not in _CONTEXT_STATUSES:
        raise _error("statement context disposition drifted")
    if context["status"] == "NOT_EVALUATED":
        if context["context_id"] is not None or context["artifact_sha256"] is not None:
            raise _error("non-evaluated context carries an artifact")
    else:
        _identity(context["context_id"], _CONTEXT_ID_RE, "statement context")
        _sha(context["artifact_sha256"], "statement context")
    if (
        type(context["unresolved_reasons"]) is not list
        or context["unresolved_reasons"] != sorted(set(context["unresolved_reasons"]))
        or any(type(reason) is not str or not reason for reason in context["unresolved_reasons"])
    ):
        raise _error("statement context unresolved reasons drifted")
    if context["status"] == "UNRESOLVED_VISIBLE_PAGE_STATEMENT_CONTEXT":
        if not context["unresolved_reasons"]:
            raise _error("unresolved context lacks reasons")
    elif context["unresolved_reasons"]:
        raise _error("resolved/non-evaluated context carries unresolved reasons")

    numeric = _exact_dict(
        receipt["independent_numeric_source_verification"],
        {
            "verification_id",
            "artifact_sha256",
            "status",
            "verified_cell_count",
            "unresolved_cell_count",
        },
        "independent numeric/source verification",
    )
    if numeric["status"] not in _NUMERIC_STATUSES:
        raise _error("numeric/source verification disposition drifted")
    verified = _nonnegative_int(numeric["verified_cell_count"], "verified numeric cell")
    unresolved = _nonnegative_int(numeric["unresolved_cell_count"], "unresolved numeric cell")
    if numeric["status"] == "NOT_EVALUATED":
        if (
            numeric["verification_id"] is not None
            or numeric["artifact_sha256"] is not None
            or verified
            or unresolved
        ):
            raise _error("non-evaluated numeric verification carries authority")
    else:
        _identity(numeric["verification_id"], _VERIFICATION_ID_RE, "numeric verification")
        _sha(numeric["artifact_sha256"], "numeric verification")
        if not accepted:
            raise _error("numeric verification cannot attach to an unresolved zero-structure graph")
        if numeric["status"] == "VERIFIED" and (verified <= 0 or unresolved):
            raise _error("verified numeric disposition is not exact and complete")
        if numeric["status"] == "UNRESOLVED" and unresolved <= 0:
            raise _error("unresolved numeric disposition lacks unresolved cells")
    return context, numeric


def _validate_independent_mapping(
    value: Any,
    *,
    accepted: bool,
    candidate: Mapping[str, Any],
    graph: Mapping[str, Any],
) -> tuple[dict[str, Any], int, int, int, int]:
    mapping = _exact_dict(
        value,
        {
            "protocol_id",
            "verification_id",
            "artifact_sha256",
            "status",
            "semantic_graph_id",
            "schema_candidate_set_id",
            "rows",
            "near_neighbor_verdicts",
        },
        "independent schema mapping verification",
    )
    status = mapping["status"]
    if status not in _MAPPING_STATUSES:
        raise _error("independent mapping verification disposition drifted")
    rows = mapping["rows"]
    if type(rows) is not list:
        raise _error("independent mapping rows are not one sequence")
    near_neighbors = mapping["near_neighbor_verdicts"]
    if type(near_neighbors) is not list:
        raise _error("independent mapping near-neighbor verdicts are not one sequence")
    if status == "NOT_EVALUATED":
        if (
            mapping["protocol_id"] is not None
            or any(
                mapping[key] is not None
                for key in (
                    "verification_id",
                    "artifact_sha256",
                    "semantic_graph_id",
                    "schema_candidate_set_id",
                )
            )
            or rows
            or near_neighbors
        ):
            raise _error("non-evaluated independent mapping carries mapping authority")
        return mapping, 0, 0, 0, 0
    if mapping["protocol_id"] != _MAPPING_VERIFICATION_PROTOCOL:
        raise _error("independent mapping verifier protocol drifted")
    _identity(mapping["verification_id"], _VERIFICATION_ID_RE, "mapping verification")
    _sha(mapping["artifact_sha256"], "mapping verification")
    if (
        not accepted
        or candidate["status"] != "CANDIDATE_SET_READY"
        or mapping["semantic_graph_id"] != graph["graph_id"]
        or mapping["schema_candidate_set_id"] != candidate["candidate_set_id"]
    ):
        raise _error("mapping verification is not bound to its accepted graph and candidate set")
    if [item.get("report_norm_id") for item in near_neighbors] != list(_NEAR_NEIGHBOR_IDS):
        raise _error("independent mapping near-neighbor denominator drifted")
    for neighbor in near_neighbors:
        _exact_dict(
            neighbor,
            {
                "report_norm_id",
                "status",
                "disposition",
                "whole_document_absence_claim",
            },
            "independent mapping near-neighbor verdict",
        )
        if (
            type(neighbor["report_norm_id"]) is not int
            or neighbor["status"] != "UNRESOLVED"
            or type(neighbor["disposition"]) is not str
            or not neighbor["disposition"]
            or neighbor["whole_document_absence_claim"] is not False
        ):
            raise _error("independent mapping near-neighbor verdict drifted")
    seen_nodes: set[str] = set()
    verified_count = 0
    verified_source_only_count = 0
    unresolved_count = 0
    for row in rows:
        _exact_dict(
            row,
            {
                "graph_node_id",
                "typed_role",
                "candidate_report_norm_id",
                "verified_report_norm_id",
                "source_only_total",
                "verifier_evidence_projection",
                "verdict",
                "unresolved_reasons",
            },
            "independent mapping row",
        )
        if type(row["graph_node_id"]) is not str or not row["graph_node_id"]:
            raise _error("independent mapping row graph-node identity drifted")
        if row["graph_node_id"] in seen_nodes:
            raise _error("independent mapping repeats a graph row")
        seen_nodes.add(row["graph_node_id"])
        if type(row["typed_role"]) is not str or not row["typed_role"]:
            raise _error("independent mapping typed role drifted")
        if type(row["source_only_total"]) is not bool:
            raise _error("source-only total flag drifted")
        if row["verdict"] not in _ROW_VERDICTS:
            raise _error("independent mapping row verdict drifted")
        checks = _exact_dict(
            row["verifier_evidence_projection"],
            set(_REQUIRED_ROW_CHECKS),
            "mapping verifier evidence projection",
        )
        if any(disposition not in _CHECK_DISPOSITIONS for disposition in checks.values()):
            raise _error("mapping verifier evidence projection disposition drifted")
        reasons = row["unresolved_reasons"]
        if (
            type(reasons) is not list
            or reasons != sorted(set(reasons))
            or any(type(reason) is not str or not reason for reason in reasons)
        ):
            raise _error("mapping row unresolved reasons drifted")
        candidate_id = row["candidate_report_norm_id"]
        verified_id = row["verified_report_norm_id"]
        if row["source_only_total"]:
            if row["typed_role"] != "TOTAL" or candidate_id is not None or verified_id is not None:
                raise _error("source-only TOTAL must retain a null ReportNormId")
            if row["verdict"] == "VERIFIED_BY_CODEX":
                if "FAIL" in checks.values() or reasons:
                    raise _error("verified source-only TOTAL failed its verifier projection")
                verified_source_only_count += 1
            else:
                if not reasons:
                    raise _error("unresolved source-only TOTAL lacks reasons")
                unresolved_count += 1
            continue
        if type(candidate_id) is not int or candidate_id <= 0:
            raise _error("mapping row lacks one candidate ReportNormId")
        if row["verdict"] == "VERIFIED_BY_CODEX":
            if (
                type(verified_id) is not int
                or verified_id != candidate_id
                or any(disposition != "PASS" for disposition in checks.values())
                or reasons
            ):
                raise _error("VERIFIED_BY_CODEX row lacks the complete independent evidence gate")
            verified_count += 1
        else:
            if verified_id is not None or not reasons:
                raise _error("UNRESOLVED mapping row fabricated a verified ReportNormId")
            unresolved_count += 1
    if status == "VERIFIED_BY_CODEX":
        if verified_count <= 0 or unresolved_count:
            raise _error("trial-level VERIFIED_BY_CODEX requires every mapping row to verify")
    elif unresolved_count <= 0:
        raise _error("trial-level UNRESOLVED mapping lacks an unresolved row")
    return (
        mapping,
        verified_count,
        verified_source_only_count,
        unresolved_count,
        len(near_neighbors),
    )


def _replay_independent_mapping(
    value: Any, request_receipt: Any, review_receipt: Any
) -> dict[str, Any]:
    """Keep the verifier import lazy while preserving its exact opaque API."""

    from bctc_ai.mapping.codex_mapped_item_verification_v1 import (
        validate_codex_mapped_item_verification_replay_v1,
    )

    return validate_codex_mapped_item_verification_replay_v1(value, request_receipt, review_receipt)


def _require_current_mapping_input_identities(
    verification: Mapping[str, Any],
    *,
    graph: Mapping[str, Any],
    candidate: Mapping[str, Any],
    context: Mapping[str, Any],
    source_projection: Mapping[str, Any],
    semantic_page_binding: Mapping[str, Any],
) -> None:
    """Refuse a valid verifier receipt replayed against a different trial frontier."""

    identities = _exact_dict(
        verification.get("input_identities"),
        {
            "semantic_graph",
            "schema_candidate",
            "statement_context",
            "source_projection_sha256",
            "semantic_page_binding_sha256",
            "numeric_verification",
        },
        "mapped-item verifier input identities",
    )
    expected_objects = {
        "semantic_graph": {
            "graph_id": graph["graph_id"],
            "sha256": canonical_json_sha256_v1(graph),
        },
        "schema_candidate": {
            "candidate_set_id": candidate["candidate_set_id"],
            "sha256": canonical_json_sha256_v1(candidate),
        },
        "statement_context": {
            "context_id": context["context_id"],
            "sha256": canonical_json_sha256_v1(context),
        },
    }
    if any(
        not same_typed_json_v1(identities[name], expected)
        for name, expected in expected_objects.items()
    ) or not same_typed_json_v1(
        {
            "source_projection_sha256": identities["source_projection_sha256"],
            "semantic_page_binding_sha256": identities["semantic_page_binding_sha256"],
        },
        {
            "source_projection_sha256": canonical_json_sha256_v1(source_projection),
            "semantic_page_binding_sha256": canonical_json_sha256_v1(semantic_page_binding),
        },
    ):
        raise _error(
            "mapped-item verifier is not bound to the current graph, candidate, context, and page"
        )


def _check_projection_for_verdict(
    verdict: Mapping[str, Any], *, source_only: bool
) -> dict[str, str]:
    failed = set(verdict["failed_check_ids"])

    def disposition(*check_ids: str) -> str:
        return "FAIL" if failed.intersection(check_ids) else "PASS"

    return {
        "replay_authenticated_source_or_pdf_evidence": disposition(
            "SOURCE_BYTES_AND_PAGE",
            "AUTHENTICATED_PIXEL_BINDING",
            "ROLE_A_FIREWALL",
            "OWNER_BRANCH_LOCALITY",
            "PROVENANCE_COMPLETENESS",
        ),
        "exact_visible_label_and_candidate_report_norm_id": (
            "NOT_APPLICABLE"
            if source_only
            else disposition(
                "ROW_LABEL_TYPED_ROLE",
                "SCHEMA_SINGLETON_AND_MAPPING_ELIGIBILITY",
                "NO_DUPLICATE_ROLE_OR_ID",
            )
        ),
        "parent_child_sibling_and_workbook_display_order": (
            "NOT_APPLICABLE"
            if source_only
            else disposition(
                "OWNER_BRANCH_LOCALITY",
                "SCHEMA_NAMESPACE_PARENT_ANCESTOR",
                "SIBLING_DISPLAY_ORDER",
                "NO_DUPLICATE_ROLE_OR_ID",
            )
        ),
        "number_sign_period_unit_and_scope": disposition(
            "STATEMENT_TYPE_SCOPE",
            "AXIS_PERIOD_IDENTITY_AND_ORDER",
            "PER_AXIS_UNIT_SCOPE",
            "ROW_VALUE_GEOMETRY",
            "NUMERIC_DIGIT_AND_SIGN_AGREEMENT",
            "TOTAL_SCOPE",
        ),
        "applicable_arithmetic_and_accounting_checks": disposition(
            "OPTIONAL_ROW_POPULATION_BOUNDARY",
            "ARITHMETIC_CLOSURE",
        ),
        "near_neighbor_schema_collision_falsifiers": (
            "NOT_APPLICABLE" if source_only else disposition("NO_DUPLICATE_ROLE_OR_ID")
        ),
    }


def _project_replayed_mapping(
    verification: Mapping[str, Any],
    graph: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    source = verification["source_authority"]
    if (
        verification["format_version"] != _MAPPING_VERIFICATION_PROTOCOL
        or verification["family_id"] != graph["family_id"]
        or source["source_local_page_id"] != graph["source_local_page_id"]
        or source["source_projection_sha256"] != graph["source_projection_sha256"]
    ):
        raise _error("independent mapping verifier belongs to another graph/source")
    graph_rows = {
        node["node_id"]: node["attributes"]["row_role"]
        for node in graph["nodes"]
        if node["kind"] == "LOGICAL_ROW"
    }
    graph_values = {
        (node["attributes"]["row_role"], node["attributes"]["axis_index"]): node["attributes"]
        for node in graph["nodes"]
        if node["kind"] == "VALUE_POSITION"
    }
    candidate_by_role = {item["typed_role"]: item for item in candidate["role_candidates"]}
    rows: list[dict[str, Any]] = []
    for verdict in verification["item_verdicts"]:
        role = verdict["typed_role"]
        source_only = verdict["claim_kind"] == "SOURCE_ONLY_VALIDATION"
        if graph_rows.get(verdict["row_graph_node_id"]) != role:
            raise _error("mapped-item verifier row differs from the replayed semantic graph")
        values = verdict["values"]
        if type(values) is not list or [item.get("axis_index") for item in values] != [0, 1]:
            raise _error("mapped-item verifier value frontier drifted")
        for value in values:
            graph_value = graph_values.get((role, value["axis_index"]))
            if graph_value is None or any(
                value[field] != graph_value[field]
                for field in ("raw_text", "normalized_decimal", "state")
            ):
                raise _error("mapped-item verifier values differ from the replayed graph")
        role_candidate = candidate_by_role.get(role)
        candidate_ids = (
            role_candidate.get("candidate_report_norm_ids")
            if type(role_candidate) is dict
            else None
        )
        if source_only:
            if role != "TOTAL" or candidate_ids != [] or verdict["report_norm_id"] is not None:
                raise _error("source-only verifier row differs from the schema candidate seam")
        elif candidate_ids != [verdict["report_norm_id"]]:
            raise _error("mapped verifier ReportNormId differs from the schema candidate seam")
        verified = verdict["status"] == "VERIFIED_BY_CODEX"
        reasons = sorted(set(verdict["failed_check_ids"]))
        if not verified and not reasons:
            reasons = ["INDEPENDENT_CODEX_ITEM_GATE_UNRESOLVED"]
        rows.append(
            {
                "graph_node_id": verdict["row_graph_node_id"],
                "typed_role": role,
                "candidate_report_norm_id": None if source_only else verdict["report_norm_id"],
                "verified_report_norm_id": (
                    None if source_only or not verified else verdict["report_norm_id"]
                ),
                "source_only_total": source_only,
                "verifier_evidence_projection": _check_projection_for_verdict(
                    verdict, source_only=source_only
                ),
                "verdict": verdict["status"],
                "unresolved_reasons": reasons,
            }
        )
    metrics = verification["metrics"]
    projected_metrics = {
        "verified_schema_mapped_row_count": sum(
            not row["source_only_total"] and row["verdict"] == "VERIFIED_BY_CODEX" for row in rows
        ),
        "verified_source_only_validation_count": sum(
            row["source_only_total"] and row["verdict"] == "VERIFIED_BY_CODEX" for row in rows
        ),
        "unresolved_schema_mapping_row_count": sum(row["verdict"] == "UNRESOLVED" for row in rows),
        "unresolved_near_neighbor_count": len(verification["near_neighbour_verdicts"]),
    }
    if projected_metrics != {
        "verified_schema_mapped_row_count": metrics["verified_mapped_row_count"],
        "verified_source_only_validation_count": metrics["verified_source_only_validation_count"],
        "unresolved_schema_mapping_row_count": metrics["unresolved_item_count"],
        "unresolved_near_neighbor_count": metrics["unresolved_near_neighbour_count"],
    }:
        raise _error("mapped-item verifier metrics differ from its exact item frontier")
    status = (
        "UNRESOLVED"
        if projected_metrics["unresolved_schema_mapping_row_count"]
        else "VERIFIED_BY_CODEX"
    )
    mapping = {
        "protocol_id": verification["format_version"],
        "verification_id": verification["verification_id"],
        "artifact_sha256": canonical_json_sha256_v1(verification),
        "status": status,
        "semantic_graph_id": graph["graph_id"],
        "schema_candidate_set_id": candidate["candidate_set_id"],
        "rows": rows,
        "near_neighbor_verdicts": [
            {
                "report_norm_id": item["report_norm_id"],
                "status": item["status"],
                "disposition": item["disposition"],
                "whole_document_absence_claim": item["whole_document_absence_claim"],
            }
            for item in verification["near_neighbour_verdicts"]
        ],
    }
    numeric_failure_ids = {
        "SOURCE_BYTES_AND_PAGE",
        "AUTHENTICATED_PIXEL_BINDING",
        "AXIS_PERIOD_IDENTITY_AND_ORDER",
        "PER_AXIS_UNIT_SCOPE",
        "ROW_VALUE_GEOMETRY",
        "NUMERIC_DIGIT_AND_SIGN_AGREEMENT",
        "TOTAL_SCOPE",
    }
    verified_cells = 0
    unresolved_cells = 0
    for verdict in verification["item_verdicts"]:
        cell_count = len(verdict["values"])
        if numeric_failure_ids.intersection(verdict["failed_check_ids"]):
            unresolved_cells += cell_count
        else:
            verified_cells += cell_count
    numeric = {
        "verification_id": verification["verification_id"],
        "artifact_sha256": canonical_json_sha256_v1(verification),
        "status": "VERIFIED" if verified_cells > 0 and unresolved_cells == 0 else "UNRESOLVED",
        "verified_cell_count": verified_cells,
        "unresolved_cell_count": unresolved_cells,
    }
    if numeric["verified_cell_count"] + numeric["unresolved_cell_count"] <= 0:
        raise _error("mapped-item verifier source/numeric projection drifted")
    return mapping, numeric


def _normalize_trial_receipt(
    raw: Any, plan: Mapping[str, Any], manifest: Mapping[str, Any]
) -> dict[str, Any]:
    receipt = _exact_dict(
        raw,
        {
            "trial_id",
            "bank",
            "family_id",
            "family_spec_sha256",
            "supplied_family_collision_scope_spec_sha256_by_id",
            "source_sha256",
            "source_size_bytes",
            "physical_page",
            "source_local_page_id",
            "source_projection_sha256",
            "semantic_page_binding_sha256",
            "observation",
            "semantic_graph",
            "schema_candidate",
            "statement_context",
            "independent_numeric_source_verification",
            "independent_schema_mapping_verification",
        },
        "family sweep trial receipt",
    )
    accepted, observation, graph = _validate_structural_refs(receipt, plan, manifest)
    candidate, candidate_count = _validate_schema_candidate(
        receipt["schema_candidate"], accepted=accepted
    )
    context, numeric = _validate_optional_dispositions(receipt, accepted=accepted)
    (
        mapping,
        verified_mapping_count,
        verified_source_only_count,
        unresolved_mapping_count,
        unresolved_near_neighbor_count,
    ) = _validate_independent_mapping(
        receipt["independent_schema_mapping_verification"],
        accepted=accepted,
        candidate=candidate,
        graph=graph,
    )
    normalized = canonical_clone_v1(receipt)
    normalized.update(
        {
            "observation": canonical_clone_v1(observation),
            "semantic_graph": canonical_clone_v1(graph),
            "schema_candidate": canonical_clone_v1(candidate),
            "statement_context": canonical_clone_v1(context),
            "independent_numeric_source_verification": canonical_clone_v1(numeric),
            "independent_schema_mapping_verification": canonical_clone_v1(mapping),
            "aggregate_counts": {
                "schema_candidate_role_count": candidate_count,
                "verified_schema_mapped_row_count": verified_mapping_count,
                "verified_source_only_validation_count": verified_source_only_count,
                "unresolved_schema_mapping_row_count": unresolved_mapping_count,
                "unresolved_near_neighbor_count": unresolved_near_neighbor_count,
            },
        }
    )
    return normalized


def authenticate_family_sweep_trial_v1(
    manifest_value: Any,
    *,
    panel_selection_authority: Any,
    trial_id: str,
    bank: str,
    project_root: Path,
    semantic_graph_v2: Any,
    source_projection_v2: Any,
    semantic_page_binding_v2: Any,
    authenticated_transformer_receipt_v2: Any,
    family_spec: FamilySpecV1,
    family_specs_for_collision_scope: Sequence[FamilySpecV1],
    schema_candidate_v1: Any | None = None,
    statement_context_v1: Any | None = None,
    mapped_item_verification_v1: Any | None = None,
    mapped_item_request_receipt_v1: Any | None = None,
    mapped_item_review_receipt_v1: Any | None = None,
) -> AuthenticatedFamilySweepTrialV1:
    """Replay exact upstream contracts and mint one non-serializable trial authority.

    Statement context is optional because it is a separate disposition and is
    not a structural gate. Mapping counts are admitted only when the persisted
    mapped-item result and both opaque request/review receipts are supplied
    together and exact replay succeeds. Hashes or protocol labels alone have
    no admission path.
    """

    manifest = validate_family_sweep_manifest_v1(
        manifest_value, panel_selection_authority=panel_selection_authority
    )
    planned = [
        (entry["bank"], plan)
        for entry in manifest["banks"]
        for plan in entry["trials"]
        if plan["trial_id"] == trial_id
    ]
    if len(planned) != 1 or planned[0][0] != bank:
        raise _error("authenticated trial must match one exact frozen bank/trial slot")
    planned_bank, plan = planned[0]
    if type(family_spec) is not FamilySpecV1:
        raise _error("authenticated trial requires one exact FamilySpecV1")
    mapping_inputs = (
        mapped_item_verification_v1,
        mapped_item_request_receipt_v1,
        mapped_item_review_receipt_v1,
    )
    if any(item is not None for item in mapping_inputs) and not all(
        item is not None for item in mapping_inputs
    ):
        raise _error("independent mapping replay requires its result and both opaque receipts")
    if mapped_item_verification_v1 is not None and statement_context_v1 is None:
        raise _error("independent mapping replay requires exact visible statement context")
    try:
        graph = validate_semantic_local_accounting_graph_replay_v2(
            semantic_graph_v2,
            source_projection_v2,
            semantic_page_binding_v2,
            authenticated_transformer_receipt_v2,
            family_spec,
            family_specs_for_collision_scope,
        )
        candidate = (
            None
            if schema_candidate_v1 is None
            else validate_semantic_local_accounting_schema_candidate_replay_v1(
                schema_candidate_v1,
                project_root,
                graph,
                source_projection_v2,
                semantic_page_binding_v2,
                authenticated_transformer_receipt_v2,
                family_spec,
                family_specs_for_collision_scope,
            )
        )
        context = (
            None
            if statement_context_v1 is None
            else validate_semantic_statement_context_replay_v1(
                statement_context_v1,
                source_projection_v2,
                semantic_page_binding_v2,
                authenticated_transformer_receipt_v2,
            )
        )
        mapped_verification = (
            None
            if mapped_item_verification_v1 is None
            else _replay_independent_mapping(
                mapped_item_verification_v1,
                mapped_item_request_receipt_v1,
                mapped_item_review_receipt_v1,
            )
        )
    except ValueError as exc:
        raise _error("family-sweep trial failed exact public upstream replay") from exc

    if type(source_projection_v2) is not dict:
        raise _error("replayed trial source projection is not one exact object")
    locator = _exact_dict(
        source_projection_v2.get("source_locator"),
        {"source_sha256", "source_size_bytes", "physical_page", "request_sha256"},
        "replayed source locator",
    )
    expected_locator = {
        "source_sha256": plan["source_sha256"],
        "source_size_bytes": plan["source_size_bytes"],
        "physical_page": plan["physical_page"],
    }
    if (
        {key: locator[key] for key in expected_locator} != expected_locator
        or graph["source_local_page_id"] != plan["source_local_page_id"]
        or graph["source_projection_sha256"] != canonical_json_sha256_v1(source_projection_v2)
        or graph["semantic_page_binding_sha256"]
        != canonical_json_sha256_v1(semantic_page_binding_v2)
        or graph["family_id"] != manifest["family_id"]
        or graph["family_spec_sha256"] != manifest["family_spec_sha256"]
        or graph["supplied_family_collision_scope_spec_sha256_by_id"]
        != manifest["supplied_family_collision_scope_spec_sha256_by_id"]
    ):
        raise _error("replayed graph/source differs from its frozen sweep plan")

    accepted = graph["status"] == _GRAPH_ACCEPTED
    observation = {
        "artifact_sha256": graph["observation_candidate_sha256"],
        "status": "READY_FOR_GRAPH_V2" if accepted else "UNRESOLVED",
        "unresolved_reasons": canonical_clone_v1(graph["unresolved_reasons"]),
    }
    graph_projection = {
        "graph_id": graph["graph_id"],
        "artifact_sha256": canonical_json_sha256_v1(graph),
        "status": graph["status"],
        "accepted_counts": canonical_clone_v1(graph["metrics"]["accepted_counts"]),
        "unresolved_reasons": canonical_clone_v1(graph["unresolved_reasons"]),
    }
    candidate_projection = (
        {
            "candidate_set_id": None,
            "artifact_sha256": None,
            "status": "NOT_EVALUATED",
            "candidate_role_count": 0,
        }
        if candidate is None
        else {
            "candidate_set_id": candidate["candidate_set_id"],
            "artifact_sha256": canonical_json_sha256_v1(candidate),
            "status": candidate["status"],
            "candidate_role_count": candidate["metrics"]["candidate_role_count"],
        }
    )
    context_projection = (
        {
            "context_id": None,
            "artifact_sha256": None,
            "status": "NOT_EVALUATED",
            "unresolved_reasons": [],
        }
        if context is None
        else {
            "context_id": context["context_id"],
            "artifact_sha256": canonical_json_sha256_v1(context),
            "status": context["status"],
            "unresolved_reasons": canonical_clone_v1(context["unresolved_reasons"]),
        }
    )
    if mapped_verification is None:
        mapping_projection = {
            "protocol_id": None,
            "verification_id": None,
            "artifact_sha256": None,
            "status": "NOT_EVALUATED",
            "semantic_graph_id": None,
            "schema_candidate_set_id": None,
            "rows": [],
            "near_neighbor_verdicts": [],
        }
        numeric_projection = {
            "verification_id": None,
            "artifact_sha256": None,
            "status": "NOT_EVALUATED",
            "verified_cell_count": 0,
            "unresolved_cell_count": 0,
        }
    else:
        if candidate is None:
            raise _error("independent mapping verifier requires a replayed schema candidate")
        if context is None:
            raise _error("independent mapping verifier requires a replayed statement context")
        _require_current_mapping_input_identities(
            mapped_verification,
            graph=graph,
            candidate=candidate,
            context=context,
            source_projection=source_projection_v2,
            semantic_page_binding=semantic_page_binding_v2,
        )
        mapped_source = mapped_verification["source_authority"]
        mapped_pdf = mapped_source["source_pdf"]
        if (
            mapped_pdf["sha256"] != plan["source_sha256"]
            or mapped_pdf["size_bytes"] != plan["source_size_bytes"]
            or mapped_source["physical_page"] != plan["physical_page"]
        ):
            raise _error("independent mapping verifier differs from the frozen source plan")
        mapping_projection, numeric_projection = _project_replayed_mapping(
            mapped_verification, graph, candidate
        )
    raw = {
        "trial_id": trial_id,
        "bank": planned_bank,
        "family_id": manifest["family_id"],
        "family_spec_sha256": manifest["family_spec_sha256"],
        "supplied_family_collision_scope_spec_sha256_by_id": canonical_clone_v1(
            manifest["supplied_family_collision_scope_spec_sha256_by_id"]
        ),
        "source_sha256": plan["source_sha256"],
        "source_size_bytes": plan["source_size_bytes"],
        "physical_page": plan["physical_page"],
        "source_local_page_id": plan["source_local_page_id"],
        "source_projection_sha256": graph["source_projection_sha256"],
        "semantic_page_binding_sha256": graph["semantic_page_binding_sha256"],
        "observation": observation,
        "semantic_graph": graph_projection,
        "schema_candidate": candidate_projection,
        "statement_context": context_projection,
        "independent_numeric_source_verification": numeric_projection,
        "independent_schema_mapping_verification": mapping_projection,
    }
    normalized = _normalize_trial_receipt(raw, plan, manifest)
    return _mint_authenticated_trial(manifest, normalized)


def _mint_authenticated_trial(
    manifest: Mapping[str, Any], normalized_trial: Mapping[str, Any]
) -> AuthenticatedFamilySweepTrialV1:
    stored = {
        "manifest_id": manifest["manifest_id"],
        "manifest_sha256": canonical_json_sha256_v1(manifest),
        "trial": canonical_clone_v1(normalized_trial),
    }
    payload = canonical_json_bytes_v1(stored)
    receipt = AuthenticatedFamilySweepTrialV1(_TRIAL_MINT_TOKEN)
    _AUTHENTICATED_TRIALS[receipt] = (payload, hashlib.sha256(payload).hexdigest())
    return receipt


def _authenticated_trial_payload(
    receipt: AuthenticatedFamilySweepTrialV1,
) -> dict[str, Any]:
    if type(receipt) is not AuthenticatedFamilySweepTrialV1:
        raise _error("family sweep aggregation requires exact opaque trial capabilities")
    stored = _AUTHENTICATED_TRIALS.get(receipt)
    if stored is None:
        raise _error("authenticated family-sweep trial is unknown or expired")
    payload, expected_sha256 = stored
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise _error("authenticated family-sweep trial bytes drifted")
    decoded = decode_canonical_json_bytes_v1(payload)
    return _exact_dict(
        decoded,
        {"manifest_id", "manifest_sha256", "trial"},
        "authenticated family-sweep trial payload",
    )


def _bank_disposition(trials: Sequence[Mapping[str, Any]], planned_count: int) -> str:
    if planned_count == 0:
        return "NOT_EVALUATED"
    if len(trials) != planned_count:
        return "PARTIALLY_EVALUATED"
    if any(trial["semantic_graph"]["status"] == _GRAPH_ACCEPTED for trial in trials):
        return "HAS_ACCEPTED_STRICT_SUBSET"
    return "UNRESOLVED_ONLY"


def _aggregate_metrics(banks: Sequence[Mapping[str, Any]], planned_trials: int) -> dict[str, Any]:
    trials = [trial for bank in banks for trial in bank["trials"]]
    accepted = [trial for trial in trials if trial["semantic_graph"]["status"] == _GRAPH_ACCEPTED]
    unresolved = [trial for trial in trials if trial["semantic_graph"]["status"] == "UNRESOLVED"]
    structure = {
        key: sum(trial["semantic_graph"]["accepted_counts"][key] for trial in trials)
        for key in ("TABLE", "LOGICAL_ROW", "VALUE_POSITION", "AXIS", "HIERARCHY")
    }
    candidate_rows = sum(
        trial["aggregate_counts"]["schema_candidate_role_count"] for trial in trials
    )
    verified_rows = sum(
        trial["aggregate_counts"]["verified_schema_mapped_row_count"] for trial in trials
    )
    verified_source_only = sum(
        trial["aggregate_counts"]["verified_source_only_validation_count"] for trial in trials
    )
    unresolved_rows = sum(
        trial["aggregate_counts"]["unresolved_schema_mapping_row_count"] for trial in trials
    )
    unresolved_near_neighbors = sum(
        trial["aggregate_counts"]["unresolved_near_neighbor_count"] for trial in trials
    )
    planned_bank_count = sum(bank["planned_trial_count"] > 0 for bank in banks)
    evaluated_bank_count = sum(
        bank["disposition"] in {"HAS_ACCEPTED_STRICT_SUBSET", "UNRESOLVED_ONLY"} for bank in banks
    )
    return {
        "panel_bank_count": len(BANK_PANEL_V1),
        "planned_bank_count": planned_bank_count,
        "evaluated_bank_count": evaluated_bank_count,
        "unevaluated_or_partial_bank_count": len(BANK_PANEL_V1) - evaluated_bank_count,
        "planned_trial_count": planned_trials,
        "evaluated_trial_count": len(trials),
        "unevaluated_trial_count": planned_trials - len(trials),
        "accepted_strict_subset_trial_count": len(accepted),
        "unresolved_trial_count": len(unresolved),
        "bank_disposition_counts": dict(
            sorted(Counter(bank["disposition"] for bank in banks).items())
        ),
        "accepted_structure_counts": structure,
        "schema_candidate_role_count": candidate_rows,
        "independently_verified_schema_mapped_row_count": verified_rows,
        "verified_source_only_validation_count": verified_source_only,
        "unresolved_schema_mapping_row_count": unresolved_rows,
        "unresolved_near_neighbor_count": unresolved_near_neighbors,
        "resolved_statement_context_trial_count": sum(
            trial["statement_context"]["status"] == "RESOLVED_VISIBLE_PAGE_STATEMENT_CONTEXT"
            for trial in trials
        ),
        "verified_numeric_source_trial_count": sum(
            trial["independent_numeric_source_verification"]["status"] == "VERIFIED"
            for trial in trials
        ),
        "schema_candidate_counted_as_verified_mapping_count": 0,
    }


def _build_family_sweep_result_v1(
    manifest_value: Any,
    trial_receipts: Sequence[AuthenticatedFamilySweepTrialV1],
    *,
    panel_selection_authority: Any,
) -> dict[str, Any]:
    manifest = validate_family_sweep_manifest_v1(
        manifest_value, panel_selection_authority=panel_selection_authority
    )
    if isinstance(trial_receipts, (str, bytes, bytearray)) or not isinstance(
        trial_receipts, Sequence
    ):
        raise _error("trial receipts must be one sequence")
    plan_by_id: dict[str, tuple[str, Mapping[str, Any]]] = {
        trial["trial_id"]: (bank["bank"], trial)
        for bank in manifest["banks"]
        for trial in bank["trials"]
    }
    receipt_by_id: dict[str, dict[str, Any]] = {}
    for authenticated in trial_receipts:
        stored = _authenticated_trial_payload(authenticated)
        if stored["manifest_id"] != manifest["manifest_id"] or stored[
            "manifest_sha256"
        ] != canonical_json_sha256_v1(manifest):
            raise _error("authenticated trial belongs to another sweep manifest")
        raw = stored["trial"]
        if type(raw) is not dict:
            raise _error("authenticated trial payload is not one object")
        trial_id = raw.get("trial_id")
        if trial_id not in plan_by_id or trial_id in receipt_by_id:
            raise _error("trial receipt is unplanned or duplicated")
        bank, plan = plan_by_id[trial_id]
        if raw.get("bank") != bank:
            raise _error("bank is provenance only and must match the frozen trial slot")
        raw_projection = canonical_clone_v1(raw)
        stored_counts = raw_projection.pop("aggregate_counts", None)
        normalized = _normalize_trial_receipt(raw_projection, plan, manifest)
        if not same_typed_json_v1(stored_counts, normalized["aggregate_counts"]):
            raise _error("authenticated trial aggregate projection drifted")
        receipt_by_id[trial_id] = normalized

    banks: list[dict[str, Any]] = []
    for bank_entry in manifest["banks"]:
        trials = [
            receipt_by_id[plan["trial_id"]]
            for plan in bank_entry["trials"]
            if plan["trial_id"] in receipt_by_id
        ]
        banks.append(
            {
                "bank": bank_entry["bank"],
                "planned_trial_count": len(bank_entry["trials"]),
                "evaluated_trial_count": len(trials),
                "disposition": _bank_disposition(trials, len(bank_entry["trials"])),
                "trials": trials,
            }
        )
    metrics = _aggregate_metrics(banks, manifest["metrics"]["planned_trial_count"])
    payload = {
        "format_version": FORMAT_VERSION_RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "status": (
            "COMPLETE_FIXED_PANEL_SWEEP"
            if metrics["unevaluated_trial_count"] == 0
            and metrics["evaluated_bank_count"] == len(BANK_PANEL_V1)
            else "PARTIAL_FIXED_PANEL_SWEEP"
        ),
        "manifest_id": manifest["manifest_id"],
        "manifest_sha256": canonical_json_sha256_v1(manifest),
        "family_id": manifest["family_id"],
        "family_spec_sha256": manifest["family_spec_sha256"],
        "supplied_family_collision_scope_spec_sha256_by_id": canonical_clone_v1(
            manifest["supplied_family_collision_scope_spec_sha256_by_id"]
        ),
        "bank_panel": list(BANK_PANEL_V1),
        "banks": banks,
        "metrics": metrics,
        "safety": _fixed_safety(),
    }
    payload["result_id"] = "fsv1:result:" + canonical_json_sha256_v1(payload)
    return payload


def build_family_sweep_result_v1(
    manifest_value: Any,
    trial_receipts: Sequence[AuthenticatedFamilySweepTrialV1],
    *,
    panel_selection_authority: Any,
) -> dict[str, Any]:
    """Aggregate only live replay-authenticated trials; raw dictionaries are refused."""

    result = _build_family_sweep_result_v1(
        manifest_value,
        trial_receipts,
        panel_selection_authority=panel_selection_authority,
    )
    manifest = validate_family_sweep_manifest_v1(
        manifest_value, panel_selection_authority=panel_selection_authority
    )
    return _validate_family_sweep_result_shape_v1(result, manifest)


def _validate_family_sweep_result_shape_v1(
    value: Any, manifest: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate result shape and authority binding without recursive replay."""

    result = _exact_dict(
        value,
        {
            "format_version",
            "claim_boundary",
            "result_id",
            "status",
            "manifest_id",
            "manifest_sha256",
            "family_id",
            "family_spec_sha256",
            "supplied_family_collision_scope_spec_sha256_by_id",
            "bank_panel",
            "banks",
            "metrics",
            "safety",
        },
        "family sweep result",
    )
    if (
        result["format_version"] != FORMAT_VERSION_RESULT
        or result["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(result["safety"], _fixed_safety())
        or result["bank_panel"] != list(BANK_PANEL_V1)
        or result["manifest_id"] != manifest["manifest_id"]
        or result["manifest_sha256"] != canonical_json_sha256_v1(manifest)
        or result["family_id"] != manifest["family_id"]
        or result["family_spec_sha256"] != manifest["family_spec_sha256"]
        or not same_typed_json_v1(
            result["supplied_family_collision_scope_spec_sha256_by_id"],
            manifest["supplied_family_collision_scope_spec_sha256_by_id"],
        )
    ):
        raise _error("family sweep result authority binding drifted")
    if type(result["banks"]) is not list or [item.get("bank") for item in result["banks"]] != list(
        BANK_PANEL_V1
    ):
        raise _error("result bank slots differ from the fixed panel")
    expected_id = "fsv1:result:" + canonical_json_sha256_v1(_result_without_id(result))
    if result["result_id"] != expected_id:
        raise _error("family sweep result identity drifted")
    return canonical_clone_v1(result)


def validate_family_sweep_result_v1(
    value: Any,
    manifest_value: Any,
    trial_receipts: Sequence[AuthenticatedFamilySweepTrialV1],
    *,
    panel_selection_authority: Any,
) -> dict[str, Any]:
    """Rebuild from exact live trial capabilities; persisted bytes are not self-authenticating."""

    manifest = validate_family_sweep_manifest_v1(
        manifest_value, panel_selection_authority=panel_selection_authority
    )
    result = _validate_family_sweep_result_shape_v1(value, manifest)
    for bank in result["banks"]:
        _exact_dict(
            bank,
            {"bank", "planned_trial_count", "evaluated_trial_count", "disposition", "trials"},
            "result bank entry",
        )
        if type(bank["trials"]) is not list:
            raise _error("result bank trials are not one sequence")
        for trial in bank["trials"]:
            if type(trial) is not dict or "aggregate_counts" not in trial:
                raise _error("result trial lacks aggregate-only counts")
    rebuilt = _build_family_sweep_result_v1(
        manifest,
        trial_receipts,
        panel_selection_authority=panel_selection_authority,
    )
    if not same_typed_json_v1(result, rebuilt):
        raise _error("family sweep result does not replay from exact trial receipts")
    return canonical_clone_v1(result)
