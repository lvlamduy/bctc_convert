#!/usr/bin/env python3
"""Build the E-0046 provisional loan-maturity eight-bank sweep.

This is a post-run experiment adapter.  It reconstructs the exact live READY,
freeze, selected VietOCR V3 receipt, and finalized Wave-1 V3 source stream;
binds all eight fixed pages through the generic V3 page adapter; and evaluates
only the structural/schema-candidate frontier currently admitted by source
authority.  Independent numeric verification and schema mapping are always
``NOT_EVALUATED`` here, so this artifact can never claim final verification.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import vietocr_semantic_page_binding_v3 as binding_v3

from bctc_ai.evaluation import loan_maturity_8bank_panel_prerequisite_v1 as panel_v1
from bctc_ai.evaluation import vietocr_all_line_freezer_v3 as freezer_v3
from bctc_ai.evaluation.authenticated_line_pixel_hydration_v1 import (
    AuthenticatedLinePixelHydrationReceiptV1,
    replay_authenticated_line_pixel_hydration_v1,
)
from bctc_ai.evaluation.loan_maturity_8bank_panel_prerequisite_v1 import (
    BANK_ORDER,
    AuthenticatedLoanMaturity8BankPanelPrerequisiteV1,
    project_authenticated_loan_maturity_8bank_panel_selection_v1,
    replay_loan_maturity_8bank_panel_prerequisite_v1,
)
from bctc_ai.evaluation.loan_maturity_8bank_ready_panel_v1 import (
    AuthenticatedLoanMaturity8BankReadyPanelV1,
    compose_authenticated_loan_maturity_8bank_ready_panel_v1,
)
from bctc_ai.evaluation.vietocr_all_line_freezer_v3 import (
    ARTIFACT_ROOT,
    AuthenticatedVietOCRAllLineFreezeV3,
    project_authenticated_vietocr_all_line_freeze_v3,
    replay_authenticated_vietocr_all_line_freeze_v3,
)
from bctc_ai.mapping import semantic_local_accounting_schema_candidate_v1 as schema_v1
from bctc_ai.source_structure import semantic_local_accounting_graph_v2 as graph_v2
from bctc_ai.source_structure import semantic_local_accounting_observation_v2 as observation_v2
from bctc_ai.source_structure import vietocr_semantic_receipt_v3 as receipt_v3
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.source_structure.contracts_v2 import validate_source_evidence_projection_v2
from bctc_ai.source_structure.evidence_projection_v2 import project_authenticated_page_v2
from bctc_ai.source_structure.finalized_v3_survey_stream_v1 import (
    FINALIZED_V3_SURVEY_AUTHORITY_V1,
    open_finalized_v3_survey_stream_v1,
)
from bctc_ai.source_structure.local_accounting_graph_v1 import (
    LOAN_MATURITY_BUCKETS_SPEC_V1,
    LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    local_accounting_family_spec_sha256_v1,
)
from bctc_ai.source_structure.vietnamese_semantic_surface_v1 import (
    compile_vietnamese_family_alias_index_v1,
)
from bctc_ai.source_structure.vietocr_semantic_receipt_v3 import (
    AuthenticatedVietOCRSemanticReceiptV3,
    authenticate_tracked_vietocr_all_line_run_v3,
    build_authenticated_vietocr_semantic_receipt_v3,
    project_authenticated_vietocr_semantic_receipt_v3,
)

__all__ = [
    "FORMAT_VERSION",
    "build_loan_maturity_8bank_v3_provisional_sweep",
    "validate_loan_maturity_8bank_v3_provisional_sweep",
]


FORMAT_VERSION = "E0046_LOAN_MATURITY_8BANK_V3_PROVISIONAL_SWEEP_V1"
EXPERIMENT_ID = "E-0046"
STATE = "PROVISIONAL_STRUCTURE_SWEEP_COMPLETE_INDEPENDENT_VERIFICATION_NOT_EVALUATED"
CLAIM_BOUNDARY = (
    "EXACT_E0044_EIGHT_PAGE_SOURCE_AND_SELECTED_VIETOCR_V3_STRUCTURAL_SWEEP_"
    "SCHEMA_CANDIDATES_ONLY_NO_INDEPENDENT_NUMERIC_VERIFICATION_NO_SCHEMA_MAPPING_"
    "NO_ACCOUNTING_ACCEPTANCE_CANONICALIZATION_VALUE_MATERIALIZATION_OR_EXPORT_AUTHORITY"
)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
E0044_PATH = Path("docs/experiments/E-0044-loan-maturity-8bank-vietocr-panel-prerequisite.json")
VPB_SOURCE_SHA256 = "614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde"
VCB_SOURCE_SHA256 = "fb0bc8ebbad76c175e61f7c2a7b78ae67608623a8d715d5470a08dbac00ff223"
_FAMILY_SPECS = (
    LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    LOAN_MATURITY_BUCKETS_SPEC_V1,
)
_FAMILY_SPEC_SHA256 = local_accounting_family_spec_sha256_v1(LOAN_MATURITY_BUCKETS_SPEC_V1)
_COLLISION_SCOPE = {
    spec.family_id: local_accounting_family_spec_sha256_v1(spec) for spec in _FAMILY_SPECS
}
_NATIVE_REASON = "NATIVE_SOURCE_NUMERIC_AUTHORITY_NOT_ADMITTED"
_TERMINAL_REASONS = (
    "NUMERIC_SOURCE_LINE_AXIS_UNAVAILABLE",
    "SOURCE_PROJECTION_TERMINAL",
    "TERMINAL_SUPPLEMENT_NOT_AUTHENTICATED_PRIMARY",
)
_ORDINARY_MODE = "ORDINARY_V2_PRIMARY_LINES"
_NATIVE_MODE = "HYDRATED_NATIVE_PRIMARY_LINES"
_TERMINAL_MODE = "HYDRATED_TERMINAL_LINE_SUPPLEMENT"
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_SAFETY = {
    "bank_code_is_post_selection_provenance_only": True,
    "bank_identity_used_for_recognition_or_acceptance": False,
    "filename_used_for_recognition_or_acceptance": False,
    "generic_page_binding_used_for_all_eight_pages": True,
    "independent_numeric_verification_performed": False,
    "persisted_artifact_self_authenticating": False,
    "private_core_derivation": True,
    "public_upstream_replay_authenticated": False,
    "schema_candidate_promoted_to_mapping": False,
    "schema_mapping_performed": False,
    "source_page_or_family_exhaustiveness_claimed": False,
    "verified_mapping_claimed": False,
}
_NOT_EVALUATED_CONTEXT = {
    "artifact_sha256": None,
    "context_id": None,
    "status": "NOT_EVALUATED",
    "unresolved_reasons": [],
}
_NOT_EVALUATED_NUMERIC = {
    "artifact_sha256": None,
    "status": "NOT_EVALUATED",
    "unresolved_cell_count": 0,
    "verification_id": None,
    "verified_cell_count": 0,
}
_NOT_EVALUATED_MAPPING = {
    "artifact_sha256": None,
    "near_neighbor_verdicts": [],
    "protocol_id": None,
    "rows": [],
    "schema_candidate_set_id": None,
    "semantic_graph_id": None,
    "status": "NOT_EVALUATED",
    "verification_id": None,
}
_TRIAL_FIELDS = {
    "bank_provenance",
    "independent_numeric_source_verification",
    "independent_schema_mapping_verification",
    "observation_candidate",
    "provisional_disposition",
    "schema_candidate",
    "selection_provenance",
    "semantic_graph",
    "semantic_page_binding",
    "source_projection",
    "statement_context",
    "trial_id",
}
_PROVISIONAL_DISPOSITION_FIELDS = {
    "binding_mode",
    "independent_mapping_status",
    "independent_numeric_status",
    "observation_status",
    "schema_candidate_status",
    "semantic_graph_status",
    "unresolved_reasons",
}
_SELECTION_PROVENANCE_FIELDS = {
    "page_ordinal",
    "physical_page",
    "source_pdf_sha256",
}
_RECEIPT_PROJECTION_FIELDS = {
    "authority",
    "claim_boundary",
    "experiment_id",
    "format_version",
    "freeze_id",
    "line_count_vector",
    "page_count",
    "receipt_id",
    "result_id",
    "run_id",
    "sample_count",
    "selection_id",
    "state",
}


class E0046ProvisionalSweepError(RuntimeError):
    """The fixed live E-0046 provisional sweep cannot be reproduced exactly."""


def _error(message: str) -> E0046ProvisionalSweepError:
    return E0046ProvisionalSweepError(message)


@dataclass(frozen=True, slots=True)
class _LiveRoots:
    prerequisite: AuthenticatedLoanMaturity8BankPanelPrerequisiteV1
    ready: AuthenticatedLoanMaturity8BankReadyPanelV1
    freeze: AuthenticatedVietOCRAllLineFreezeV3
    receipt: AuthenticatedVietOCRSemanticReceiptV3
    hydrations: tuple[AuthenticatedLinePixelHydrationReceiptV1, ...]
    panel_selection: dict[str, Any]
    freeze_projection: dict[str, Any]
    receipt_projection: dict[str, Any]


def _live_roots(project_root: Path) -> _LiveRoots:
    root = project_root.resolve()
    _panel, prerequisite = replay_loan_maturity_8bank_panel_prerequisite_v1(root, E0044_PATH)
    _vpb_envelope, vpb = replay_authenticated_line_pixel_hydration_v1(
        root,
        source_pdf_sha256=VPB_SOURCE_SHA256,
        physical_page=42,
    )
    _vcb_envelope, vcb = replay_authenticated_line_pixel_hydration_v1(
        root,
        source_pdf_sha256=VCB_SOURCE_SHA256,
        physical_page=31,
    )
    hydrations = (vcb, vpb)
    _audit, ready = compose_authenticated_loan_maturity_8bank_ready_panel_v1(
        root,
        E0044_PATH,
        prerequisite,
        hydrations,
    )
    _freeze_projection, freeze = replay_authenticated_vietocr_all_line_freeze_v3(
        root,
        ARTIFACT_ROOT,
        ready,
    )
    run = authenticate_tracked_vietocr_all_line_run_v3(root, freeze)
    receipt = build_authenticated_vietocr_semantic_receipt_v3(run)
    return _LiveRoots(
        prerequisite=prerequisite,
        ready=ready,
        freeze=freeze,
        receipt=receipt,
        hydrations=hydrations,
        panel_selection=project_authenticated_loan_maturity_8bank_panel_selection_v1(prerequisite),
        freeze_projection=project_authenticated_vietocr_all_line_freeze_v3(freeze),
        receipt_projection=project_authenticated_vietocr_semantic_receipt_v3(receipt),
    )


def _finalized_authority_projection() -> dict[str, Any]:
    projection = asdict(FINALIZED_V3_SURVEY_AUTHORITY_V1)
    projection["document_ids"] = list(projection["document_ids"])
    return projection


def _selected_source_projections(
    project_root: Path,
    panel_selection: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    slots = panel_selection["slots"]
    expected = {
        (slot["source_pdf_sha256"], slot["physical_page"]): ordinal
        for ordinal, slot in enumerate(slots)
    }
    if len(expected) != 8:
        raise _error("panel selection does not contain eight unique source locators")
    selected: dict[int, dict[str, Any]] = {}
    with open_finalized_v3_survey_stream_v1(project_root) as stream:
        for page in stream:
            record = page.page_record
            key = (record["source_sha256"], record["physical_page"])
            ordinal = expected.get(key)
            if ordinal is None:
                continue
            if ordinal in selected:
                raise _error("finalized V3 stream repeats one selected source locator")
            projection = project_authenticated_page_v2(
                page_record=record,
                page_result=page.page_result,
            )
            locator = projection["source_locator"]
            if locator["source_sha256"] != key[0] or locator["physical_page"] != key[1]:
                raise _error("selected V2 projection locator differs from finalized stream")
            selected[ordinal] = projection
    if set(selected) != set(range(8)):
        missing = sorted(set(range(8)) - set(selected))
        raise _error(f"finalized V3 stream lacks selected slot ordinals {missing}")
    return tuple(selected[ordinal] for ordinal in range(8))


def _unresolved_observation(
    source: dict[str, Any],
    binding: dict[str, Any],
    reasons: list[str],
) -> dict[str, Any]:
    if not reasons or reasons != sorted(set(reasons)):
        raise _error("provisional unresolved observation reasons are not a nonempty set")
    return {
        "format_version": observation_v2.FORMAT_VERSION,
        "claim_boundary": observation_v2.CLAIM_BOUNDARY,
        "source_local_page_id": source["source_local_page_id"],
        "source_projection_sha256": canonical_json_sha256_v1(source),
        "semantic_page_binding_sha256": canonical_json_sha256_v1(binding),
        "family_id": LOAN_MATURITY_BUCKETS_SPEC_V1.family_id,
        "family_spec_sha256": _FAMILY_SPEC_SHA256,
        "supplied_family_collision_scope_spec_sha256_by_id": dict(sorted(_COLLISION_SCOPE.items())),
        "status": "UNRESOLVED",
        "candidate_regions": [],
        "unresolved_reasons": reasons,
        "readiness": {
            "accentless_candidates_promoted_by_topology": False,
            "complete_topology_count": 0,
            "globally_collision_free_claimed": False,
            "graph_v1_accepted": False,
            "ready_within_supplied_family_collision_scope": False,
            "unique_complete_topology": False,
        },
        "safety": canonical_clone_v1(observation_v2.SAFETY),
    }


def _not_evaluated_dispositions() -> dict[str, dict[str, Any]]:
    return {
        "statement_context": canonical_clone_v1(_NOT_EVALUATED_CONTEXT),
        "independent_numeric_source_verification": canonical_clone_v1(_NOT_EVALUATED_NUMERIC),
        "independent_schema_mapping_verification": canonical_clone_v1(_NOT_EVALUATED_MAPPING),
    }


def _trial(
    *,
    ordinal: int,
    selection_slot: dict[str, Any],
    source: dict[str, Any],
    roots: _LiveRoots,
    alias_index: Any,
    schema_authority: dict[str, Any],
    schema_by_id: dict[int, Any],
) -> dict[str, Any]:
    capability = binding_v3.bind_authenticated_vietocr_semantic_page_v3(
        source,
        roots.ready,
        roots.freeze,
        roots.receipt,
        roots.hydrations,
    )
    binding = binding_v3.project_authenticated_vietocr_semantic_page_binding_v3(capability)
    binding_v3.validate_authenticated_vietocr_semantic_page_binding_v3(binding, capability)
    mode = binding["binding_mode"]
    if mode == _ORDINARY_MODE:
        observation = observation_v2._candidate_payload(
            source,
            binding,
            LOAN_MATURITY_BUCKETS_SPEC_V1,
            alias_index,
        )
    elif mode == _NATIVE_MODE:
        observation = _unresolved_observation(source, binding, [_NATIVE_REASON])
    elif mode == _TERMINAL_MODE:
        observation = _unresolved_observation(source, binding, sorted(_TERMINAL_REASONS))
    else:
        raise _error("generic V3 page binding returned an unsupported mode")
    graph = graph_v2._build_from_observation(
        observation,
        LOAN_MATURITY_BUCKETS_SPEC_V1,
        _FAMILY_SPECS,
    )
    schema_candidate = schema_v1._validate_payload(
        schema_v1._build_payload(graph, schema_authority, schema_by_id)
    )
    locator = source["source_locator"]
    if (
        locator["source_sha256"] != selection_slot["source_pdf_sha256"]
        or locator["physical_page"] != selection_slot["physical_page"]
        or binding["page_ordinal"] != ordinal
    ):
        raise _error("trial source/binding differs from fixed selection ordinal")
    return {
        "trial_id": f"trial-{ordinal:04d}",
        "bank_provenance": selection_slot["bank_code"],
        "selection_provenance": {
            "page_ordinal": ordinal,
            "physical_page": selection_slot["physical_page"],
            "source_pdf_sha256": selection_slot["source_pdf_sha256"],
        },
        "source_projection": canonical_clone_v1(source),
        "semantic_page_binding": binding,
        "observation_candidate": observation,
        "semantic_graph": graph,
        "schema_candidate": schema_candidate,
        **_not_evaluated_dispositions(),
        "provisional_disposition": {
            "binding_mode": mode,
            "observation_status": observation["status"],
            "semantic_graph_status": graph["status"],
            "schema_candidate_status": schema_candidate["status"],
            "independent_numeric_status": "NOT_EVALUATED",
            "independent_mapping_status": "NOT_EVALUATED",
            "unresolved_reasons": canonical_clone_v1(observation["unresolved_reasons"]),
        },
    }


def _metrics(trials: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "bank_count": len(trials),
        "bound_page_count": sum(
            trial["semantic_page_binding"]["metrics"]["all_ready_lines_bound_once"] is True
            for trial in trials
        ),
        "ordinary_structural_evaluation_count": sum(
            trial["semantic_page_binding"]["binding_mode"] == _ORDINARY_MODE for trial in trials
        ),
        "native_numeric_authority_blocked_count": sum(
            trial["semantic_page_binding"]["binding_mode"] == _NATIVE_MODE for trial in trials
        ),
        "terminal_source_blocked_count": sum(
            trial["semantic_page_binding"]["binding_mode"] == _TERMINAL_MODE for trial in trials
        ),
        "observation_ready_count": sum(
            trial["observation_candidate"]["status"] == "READY_FOR_GRAPH_V2" for trial in trials
        ),
        "accepted_structure_count": sum(
            trial["semantic_graph"]["status"] == "ACCEPTED_WITHIN_SUPPLIED_FAMILY_COLLISION_SCOPE"
            for trial in trials
        ),
        "schema_candidate_ready_count": sum(
            trial["schema_candidate"]["status"] == "CANDIDATE_SET_READY" for trial in trials
        ),
        "independent_numeric_evaluated_count": 0,
        "independent_mapping_evaluated_count": 0,
        "verified_mapping_count": 0,
    }


def _build_payload(project_root: Path) -> dict[str, Any]:
    if not isinstance(project_root, Path):
        raise _error("E-0046 project root must be one pathlib Path")
    root = project_root.resolve()
    roots = _live_roots(root)
    sources = _selected_source_projections(root, roots.panel_selection)
    alias_index = compile_vietnamese_family_alias_index_v1(_FAMILY_SPECS)
    schema_authority, schema_by_id = schema_v1._authority_snapshot(root)
    trials = [
        _trial(
            ordinal=ordinal,
            selection_slot=slot,
            source=source,
            roots=roots,
            alias_index=alias_index,
            schema_authority=schema_authority,
            schema_by_id=schema_by_id,
        )
        for ordinal, (slot, source) in enumerate(
            zip(roots.panel_selection["slots"], sources, strict=True),
            start=1,
        )
    ]
    payload = {
        "format_version": FORMAT_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "state": STATE,
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": LOAN_MATURITY_BUCKETS_SPEC_V1.family_id,
        "family_spec_sha256": _FAMILY_SPEC_SHA256,
        "supplied_family_collision_scope_spec_sha256_by_id": dict(sorted(_COLLISION_SCOPE.items())),
        "bank_order": list(BANK_ORDER),
        "input_authority": {
            "finalized_v3_survey": _finalized_authority_projection(),
            "panel_selection": roots.panel_selection,
            "freeze_projection": roots.freeze_projection,
            "semantic_receipt_projection": roots.receipt_projection,
        },
        "trials": trials,
        "metrics": _metrics(trials),
        "safety": canonical_clone_v1(_SAFETY),
    }
    payload["sweep_id"] = "e0046:provisional-sweep:" + canonical_json_sha256_v1(payload)
    return payload


def build_loan_maturity_8bank_v3_provisional_sweep(project_root: Path) -> dict[str, Any]:
    """Build and independently replay the exact live provisional sweep."""

    payload = _build_payload(project_root)
    return validate_loan_maturity_8bank_v3_provisional_sweep(payload, project_root)


def _contains_forbidden_verified_claim(value: Any) -> bool:
    if type(value) is str:
        return value == "VERIFIED_BY_CODEX"
    if type(value) is list:
        return any(_contains_forbidden_verified_claim(item) for item in value)
    if type(value) is dict:
        return any(
            _contains_forbidden_verified_claim(key) or _contains_forbidden_verified_claim(item)
            for key, item in value.items()
        )
    return False


def _validate_receipt_projection(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RECEIPT_PROJECTION_FIELDS:
        raise _error("E-0046 semantic receipt projection fields drifted")
    receipt = value
    if (
        receipt["format_version"] != receipt_v3.RECEIPT_FORMAT_VERSION
        or receipt["experiment_id"] != receipt_v3.EXPERIMENT_ID
        or receipt["state"] != receipt_v3.RECEIPT_STATE
        or receipt["claim_boundary"] != receipt_v3.CLAIM_BOUNDARY
        or not same_typed_json_v1(receipt["authority"], receipt_v3._SAFETY_RECEIPT)
        or type(receipt["page_count"]) is not int
        or receipt["page_count"] != 8
        or type(receipt["sample_count"]) is not int
        or receipt["sample_count"] != 835
        or not same_typed_json_v1(
            receipt["line_count_vector"], list(receipt_v3.EXPECTED_LINE_COUNT_VECTOR)
        )
    ):
        raise _error("E-0046 semantic receipt projection identity drifted")
    for field, prefix in (
        ("freeze_id", "voalfv3:freeze:"),
        ("receipt_id", "voalsrv3:receipt:"),
        ("result_id", "voalrv3:result:"),
        ("run_id", "voalrv3:run:"),
        ("selection_id", "voalsv3:selection:"),
    ):
        identifier = receipt[field]
        if (
            type(identifier) is not str
            or not identifier.startswith(prefix)
            or _SHA_RE.fullmatch(identifier.removeprefix(prefix)) is None
        ):
            raise _error(f"E-0046 semantic receipt {field} drifted")
    material = canonical_clone_v1(receipt)
    identifier = material.pop("receipt_id")
    if identifier != "voalsrv3:receipt:" + canonical_json_sha256_v1(material):
        raise _error("E-0046 semantic receipt content identity drifted")
    return canonical_clone_v1(receipt)


def _validate_sweep_shape(value: Any) -> dict[str, Any]:
    """Validate closed shape before live construction replay."""

    fields = {
        "bank_order",
        "claim_boundary",
        "experiment_id",
        "family_id",
        "family_spec_sha256",
        "format_version",
        "input_authority",
        "metrics",
        "safety",
        "state",
        "supplied_family_collision_scope_spec_sha256_by_id",
        "sweep_id",
        "trials",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error("E-0046 provisional sweep fields drifted")
    sweep = value
    if (
        sweep["format_version"] != FORMAT_VERSION
        or sweep["experiment_id"] != EXPERIMENT_ID
        or sweep["state"] != STATE
        or sweep["claim_boundary"] != CLAIM_BOUNDARY
        or sweep["family_id"] != LOAN_MATURITY_BUCKETS_SPEC_V1.family_id
        or sweep["family_spec_sha256"] != _FAMILY_SPEC_SHA256
        or not same_typed_json_v1(
            sweep["supplied_family_collision_scope_spec_sha256_by_id"],
            dict(sorted(_COLLISION_SCOPE.items())),
        )
        or not same_typed_json_v1(sweep["bank_order"], list(BANK_ORDER))
        or not same_typed_json_v1(sweep["safety"], _SAFETY)
        or _contains_forbidden_verified_claim(sweep)
    ):
        raise _error("E-0046 provisional identity, family, or safety boundary drifted")
    authority = sweep["input_authority"]
    if type(authority) is not dict or set(authority) != {
        "finalized_v3_survey",
        "panel_selection",
        "freeze_projection",
        "semantic_receipt_projection",
    }:
        raise _error("E-0046 input authority fields drifted")
    if not same_typed_json_v1(authority["finalized_v3_survey"], _finalized_authority_projection()):
        raise _error("E-0046 finalized V3 survey authority drifted")
    selection = panel_v1._validate_selection_projection_shape_v1(authority["panel_selection"])
    slots = selection["slots"]
    if selection["panel_state"] != panel_v1.READY_PANEL or len(slots) != 8:
        raise _error("E-0046 panel selection slots drifted")
    for slot in slots:
        expected_page, expected_sha = panel_v1.EXPECTED_LOCATORS[slot["bank_code"]]
        if slot["physical_page"] != expected_page or slot["source_pdf_sha256"] != expected_sha:
            raise _error("E-0046 fixed eight-source locator set drifted")
    freeze = freezer_v3._validate_projection(authority["freeze_projection"], ARTIFACT_ROOT)
    receipt = _validate_receipt_projection(authority["semantic_receipt_projection"])
    if (
        type(freeze) is not dict
        or type(receipt) is not dict
        or receipt.get("freeze_id") != freeze.get("freeze_id")
        or receipt.get("sample_count") != 835
    ):
        raise _error("E-0046 freeze/semantic receipt lineage drifted")
    trials = sweep["trials"]
    if type(trials) is not list or len(trials) != 8:
        raise _error("E-0046 trial denominator drifted")
    expected_modes = (
        _ORDINARY_MODE,
        _ORDINARY_MODE,
        _NATIVE_MODE,
        _ORDINARY_MODE,
        _TERMINAL_MODE,
        _ORDINARY_MODE,
        _ORDINARY_MODE,
        _ORDINARY_MODE,
    )
    ready_batch_ids: set[str] = set()
    for ordinal, (trial, bank, slot, expected_mode, expected_line_count) in enumerate(
        zip(
            trials,
            BANK_ORDER,
            slots,
            expected_modes,
            freezer_v3.EXPECTED_LINE_COUNT_VECTOR,
            strict=True,
        ),
        start=1,
    ):
        if type(trial) is not dict or set(trial) != _TRIAL_FIELDS:
            raise _error("E-0046 trial fields drifted")
        if trial["trial_id"] != f"trial-{ordinal:04d}":
            raise _error("E-0046 trial identity/order drifted")
        if trial["bank_provenance"] != bank or slot["bank_code"] != bank:
            raise _error("E-0046 bank provenance order drifted")
        provenance = trial["selection_provenance"]
        if (
            type(provenance) is not dict
            or set(provenance) != _SELECTION_PROVENANCE_FIELDS
            or provenance["page_ordinal"] != ordinal
            or provenance["physical_page"] != slot["physical_page"]
            or provenance["source_pdf_sha256"] != slot["source_pdf_sha256"]
        ):
            raise _error("E-0046 trial selection provenance drifted")
        source = validate_source_evidence_projection_v2(trial["source_projection"])
        binding = binding_v3._validate_binding_shape(trial["semantic_page_binding"])
        observation = trial["observation_candidate"]
        graph = graph_v2._validate_graph_shape(trial["semantic_graph"])
        candidate = schema_v1._validate_payload(trial["schema_candidate"])
        disposition = trial["provisional_disposition"]
        ready_batch_ids.add(binding["ready_batch_id"])
        if (
            type(observation) is not dict
            or observation.get("family_id") != LOAN_MATURITY_BUCKETS_SPEC_V1.family_id
            or observation.get("family_spec_sha256") != _FAMILY_SPEC_SHA256
            or observation.get("unresolved_reasons")
            != sorted(set(observation.get("unresolved_reasons", [])))
            or observation.get("source_projection_sha256") != canonical_json_sha256_v1(source)
            or observation.get("semantic_page_binding_sha256") != canonical_json_sha256_v1(binding)
            or graph["observation_candidate_sha256"] != canonical_json_sha256_v1(observation)
            or candidate["semantic_graph_sha256"] != canonical_json_sha256_v1(graph)
            or candidate["semantic_graph_id"] != graph["graph_id"]
            or source["source_locator"]["source_sha256"] != slot["source_pdf_sha256"]
            or source["source_locator"]["physical_page"] != slot["physical_page"]
            or binding["source_projection_sha256"] != canonical_json_sha256_v1(source)
            or binding["page_ordinal"] != ordinal
            or binding["binding_mode"] != expected_mode
            or binding["freeze_id"] != freeze["freeze_id"]
            or binding["semantic_receipt_id"] != receipt["receipt_id"]
            or binding["metrics"]["ready_line_count"] != expected_line_count
            or type(disposition) is not dict
            or set(disposition) != _PROVISIONAL_DISPOSITION_FIELDS
            or disposition["binding_mode"] != binding["binding_mode"]
            or disposition["observation_status"] != observation.get("status")
            or disposition["semantic_graph_status"] != graph["status"]
            or disposition["schema_candidate_status"] != candidate["status"]
            or disposition["independent_numeric_status"] != "NOT_EVALUATED"
            or disposition["independent_mapping_status"] != "NOT_EVALUATED"
            or not same_typed_json_v1(
                disposition["unresolved_reasons"], observation["unresolved_reasons"]
            )
        ):
            raise _error("E-0046 trial source/binding/structure/schema chain drifted")
        mode = binding["binding_mode"]
        if (mode == _NATIVE_MODE and observation["unresolved_reasons"] != [_NATIVE_REASON]) or (
            mode == _TERMINAL_MODE
            and observation["unresolved_reasons"] != sorted(_TERMINAL_REASONS)
        ):
            raise _error("E-0046 hydrated source disposition drifted")
        if mode in {_NATIVE_MODE, _TERMINAL_MODE}:
            reasons = [_NATIVE_REASON] if mode == _NATIVE_MODE else sorted(_TERMINAL_REASONS)
            if (
                not same_typed_json_v1(
                    observation, _unresolved_observation(source, binding, reasons)
                )
                or graph["status"] != "UNRESOLVED"
                or graph["nodes"] != []
                or graph["edges"] != []
                or graph["arithmetic"] is not None
                or candidate["status"] != "UNRESOLVED_GRAPH_NOT_ACCEPTED"
            ):
                raise _error("E-0046 hydrated trial escaped exact unresolved state")
        for name, expected in _not_evaluated_dispositions().items():
            if not same_typed_json_v1(trial[name], expected):
                raise _error(f"E-0046 trial {name} escaped NOT_EVALUATED")
    if len(ready_batch_ids) != 1:
        raise _error("E-0046 trials do not share one READY batch")
    expected_metrics = _metrics(trials)
    fixed_metrics = {
        "bank_count": 8,
        "bound_page_count": 8,
        "ordinary_structural_evaluation_count": 6,
        "native_numeric_authority_blocked_count": 1,
        "terminal_source_blocked_count": 1,
        "independent_numeric_evaluated_count": 0,
        "independent_mapping_evaluated_count": 0,
        "verified_mapping_count": 0,
    }
    if not same_typed_json_v1(sweep["metrics"], expected_metrics) or any(
        expected_metrics[field] != expected for field, expected in fixed_metrics.items()
    ):
        raise _error("E-0046 provisional sweep metrics drifted")
    material = canonical_clone_v1(sweep)
    identifier = material.pop("sweep_id")
    if (
        type(identifier) is not str
        or not identifier.startswith("e0046:provisional-sweep:")
        or _SHA_RE.fullmatch(identifier.removeprefix("e0046:provisional-sweep:")) is None
        or identifier != "e0046:provisional-sweep:" + canonical_json_sha256_v1(material)
    ):
        raise _error("E-0046 provisional sweep content identity drifted")
    return canonical_clone_v1(sweep)


def validate_loan_maturity_8bank_v3_provisional_sweep(
    value: Any,
    project_root: Path,
) -> dict[str, Any]:
    """Replay construction from live roots and require exact persisted equality."""

    if not isinstance(project_root, Path):
        raise _error("E-0046 validation project root must be one pathlib Path")
    persisted = _validate_sweep_shape(value)
    rebuilt = _build_payload(project_root.resolve())
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("E-0046 provisional sweep does not replay from live authorities")
    return canonical_clone_v1(persisted)


def main() -> None:
    print(
        canonical_json_bytes_v1(
            build_loan_maturity_8bank_v3_provisional_sweep(PROJECT_ROOT)
        ).decode("utf-8")
    )


if __name__ == "__main__":
    main()
