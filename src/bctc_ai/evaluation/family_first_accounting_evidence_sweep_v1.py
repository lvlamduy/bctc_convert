"""Generic all-filing evidence sweep after family topology discovery.

One declarative family topology and one small evaluation policy are applied to
every authenticated filing.  Complete-document VietOCR text is scanned before
provenance is exposed.  Numeric proposals and page renders are opened only for
documents with one unique complete topology region.  No trial is mapped here;
the strongest output is a replayable schema-review readiness proposal.
"""

from __future__ import annotations

from typing import Any

from bctc_ai.evaluation import accounting_family_row_axis_v1 as row_axis_v1
from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.evaluation import family_first_authenticated_page_region_v1 as render_v1
from bctc_ai.evaluation import family_first_ppocrv6_numeric_index_v3 as numeric_v3
from bctc_ai.evaluation import family_first_semantic_index_v1 as semantic_v1
from bctc_ai.evaluation.accounting_additive_table_closure_v1 import (
    build_accounting_additive_table_closure_v1,
)
from bctc_ai.evaluation.accounting_family_column_context_v1 import (
    build_accounting_family_column_context_v1,
)
from bctc_ai.evaluation.accounting_family_document_axis_join_v1 import (
    build_accounting_family_document_axis_join_v1,
    project_accounting_family_document_pages_v1,
)
from bctc_ai.evaluation.accounting_family_row_axis_v1 import (
    build_accounting_family_row_axis_v1,
)
from bctc_ai.evaluation.adaptive_accounting_table_geometry_v1 import (
    propose_missing_value_lane_regions_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "FamilyFirstAccountingEvidenceSweepV1Error",
    "build_authenticated_family_first_accounting_evidence_sweep_v1",
    "validate_authenticated_family_first_accounting_evidence_sweep_replay_v1",
]


FORMAT_VERSION = "FAMILY_FIRST_ACCOUNTING_EVIDENCE_SWEEP_V1"
EVALUATION_SPEC_FORMAT = "ACCOUNTING_FAMILY_EVALUATION_SPEC_V1"
CLAIM_BOUNDARY = (
    "AUTHENTICATED_ALL_FILING_COMPLETE_DOCUMENT_TOPOLOGY_FRESH_VIETOCR_LABEL_"
    "PPOCRV6_MEDIUM_NUMERIC_PERIOD_UNIT_AND_VISIBLE_ADDITIVE_CLOSURE_EVIDENCE_"
    "SWEEP_PROPOSAL_ONLY_NO_NOT_OBSERVED_SCHEMA_MAPPING_CANONICALIZATION_EXPORT_"
    "OR_PRODUCTION_AUTHORITY"
)
_AUTHORITY = {
    "all_authenticated_documents_scanned_for_topology": True,
    "bank_file_page_period_scope_used_for_matching_or_routing": False,
    "mapping_authority": False,
    "not_observed_authority": False,
    "numeric_authority": False,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "schema_authority": False,
    "schema_review_readiness_proposal_only": True,
}
_FIELDS = {
    "authority",
    "claim_boundary",
    "evaluation_spec",
    "family_id",
    "family_spec",
    "format_version",
    "input_indices",
    "metrics",
    "state",
    "sweep_id",
    "trials",
}
_SPEC_FIELDS = {
    "closure_policy",
    "expected_lane_unit_kinds",
    "family_id",
    "format_version",
    "period_semantics",
}
_TRIAL_FIELDS = {
    "additive_closure",
    "column_context",
    "document_axis_binding",
    "document_ordinal",
    "evidence_status",
    "private_provenance",
    "row_axis",
    "source_pdf_ref",
    "topology_scan",
    "unresolved_reasons",
}
_BINDING_FIELDS = {"document_axis_id", "metrics", "source_binding_sha256"}
_INDEX_FIELDS = {"numeric_receipt_id", "semantic_index_id"}
_METRIC_FIELDS = {
    "document_count",
    "evidence_ready_for_schema_review_count",
    "mapping_verified_count",
    "not_observed_count",
    "unique_topology_document_count",
    "unresolved_document_count",
}


class FamilyFirstAccountingEvidenceSweepV1Error(ValueError):
    """The capabilities, family policy, source join, gate, or replay drifted."""


def _error(message: str) -> FamilyFirstAccountingEvidenceSweepV1Error:
    return FamilyFirstAccountingEvidenceSweepV1Error(message)


def _evaluation_spec(value: Any, family_id: str) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _SPEC_FIELDS
        or value["format_version"] != EVALUATION_SPEC_FORMAT
        or value["family_id"] != family_id
        or value["period_semantics"] not in {"BALANCE_COMPARATIVE", "CURRENT_ROLLFORWARD"}
        or value["closure_policy"]
        not in {
            "CORROBORATE_IF_VISIBLE",
            "REQUIRE_EXACT_UNIQUE_VISIBLE_TRAILING_TOTAL",
        }
        or type(value["expected_lane_unit_kinds"]) is not list
        or not value["expected_lane_unit_kinds"]
        or any(item not in {"MONEY", "PERCENT"} for item in value["expected_lane_unit_kinds"])
    ):
        raise _error("family evaluation specification drifted")
    return canonical_clone_v1(value)


def _blind_pages(document: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "lines": [
                {
                    "bbox": canonical_clone_v1(line["source_bbox_raw_pixels"]),
                    "source_line_index": line["line_ordinal"],
                    "source_text": None,
                    "vietocr_text": line["vietocr_text"],
                }
                for line in page["lines"]
            ],
            "page_sequence": page["physical_page"],
        }
        for page in document["pages"]
    ]


def _region_pages(document: dict[str, Any], region: dict[str, Any]) -> tuple[int, ...]:
    start = region["cluster_start_document_line_ordinal"]
    stop = region["cluster_end_document_line_ordinal_exclusive"]
    offset = 0
    pages = []
    for page in document["pages"]:
        page_stop = offset + page["line_count"]
        if offset < stop and page_stop > start:
            pages.append(page["physical_page"])
        offset = page_stop
    if not pages:
        raise _error("unique topology region retained no source page")
    return tuple(pages)


def _axis_binding(document_axis: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_axis_id": document_axis["document_axis_id"],
        "metrics": canonical_clone_v1(document_axis["metrics"]),
        "source_binding_sha256": document_axis["source_binding_sha256"],
    }


def _visible_dash_rescue_inputs(
    semantic_capability: Any,
    *,
    document_ordinal: int,
    joined_pages: list[dict[str, Any]],
    row_axis: dict[str, Any],
    render_snapshots: tuple[dict[str, Any], ...],
) -> tuple[dict[str, Any], ...]:
    region = row_axis["topology_region"]
    if region is None:
        return ()
    by_page = {page["page_sequence"]: page for page in joined_pages}
    heights = {
        snapshot["physical_page"]: snapshot["render_ref"]["pixel_height"]
        for snapshot in render_snapshots
    }
    region_lines = row_axis_v1._region_lines(joined_pages, region)
    rescues = []
    for row in row_axis["rows"]:
        if not row["missing_column_ordinals"]:
            continue
        match = row["label_match"]
        page_sequence = match["page_sequence"]
        page = by_page[page_sequence]
        page_height = heights.get(page_sequence)
        if type(page["page_width"]) is not int or type(page_height) is not int:
            raise _error("missing-lane page lacks authenticated render dimensions")
        label_boxes = [
            line["bbox"]
            for line in page["lines"]
            if match["source_line_index"] <= line["line_ordinal"] <= match["end_source_line_index"]
        ]
        proposals = propose_missing_value_lane_regions_v1(
            region_lines[page_sequence],
            label_boxes=label_boxes,
            is_numeric=row_axis_v1._is_numeric,
            page_width=page["page_width"],
            page_height=page_height,
            retain_singleton_columns=True,
        )
        by_lane = {proposal["column_ordinal"]: proposal for proposal in proposals}
        for lane in row["missing_column_ordinals"]:
            proposal = by_lane.get(lane)
            if proposal is None:
                continue
            crop = render_v1.crop_authenticated_family_first_page_region_v1(
                semantic_capability,
                document_ordinal=document_ordinal,
                physical_page=page_sequence,
                raw_pixel_bbox=proposal["raw_pixel_bbox"],
            )
            rescues.append(
                {
                    "column_ordinal": lane,
                    "page_sequence": page_sequence,
                    "region": crop,
                    "role": row["role"],
                }
            )
    return tuple(rescues)


def _unresolved_reasons(
    row_axis: dict[str, Any],
    column_context: dict[str, Any],
    closure: dict[str, Any],
    policy: dict[str, Any],
) -> list[str]:
    reasons = []
    if row_axis["status"] != "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY":
        reasons.append("VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE")
    if column_context["status"] != "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY":
        reasons.extend(
            f"COLUMN_CONTEXT:{reason}" for reason in column_context["unresolved_reasons"]
        )
    if (
        policy["closure_policy"] == "REQUIRE_EXACT_UNIQUE_VISIBLE_TRAILING_TOTAL"
        and closure["status"] != "CORROBORATED_EXACT_UNIQUE_TRAILING_TOTAL"
    ):
        reasons.extend(f"ADDITIVE_CLOSURE:{reason}" for reason in closure["unresolved_reasons"])
    elif (
        policy["closure_policy"] == "CORROBORATE_IF_VISIBLE"
        and closure["metrics"]["visible_trailing_candidate_count"] > 0
        and closure["status"] != "CORROBORATED_EXACT_UNIQUE_TRAILING_TOTAL"
    ):
        reasons.extend(
            f"VISIBLE_ADDITIVE_CLOSURE_VETO:{reason}" for reason in closure["unresolved_reasons"]
        )
    return reasons


def _trial(
    semantic_capability: Any,
    numeric_capability: Any,
    document: dict[str, Any],
    topology_scan: dict[str, Any],
    family_spec: dict[str, Any],
    evaluation_spec: dict[str, Any],
) -> dict[str, Any]:
    base = {
        "document_ordinal": document["document_ordinal"],
        "private_provenance": canonical_clone_v1(document["private_provenance"]),
        "source_pdf_ref": canonical_clone_v1(document["source_pdf_ref"]),
        "topology_scan": topology_scan,
    }
    if topology_scan["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY":
        return {
            **base,
            "additive_closure": None,
            "column_context": None,
            "document_axis_binding": None,
            "evidence_status": "NOT_OBSERVED_PROPOSAL_ONLY",
            "row_axis": None,
            "unresolved_reasons": [],
        }
    if topology_scan["status"] != "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL":
        return {
            **base,
            "additive_closure": None,
            "column_context": None,
            "document_axis_binding": None,
            "evidence_status": "UNRESOLVED_NO_UNIQUE_COMPLETE_TOPOLOGY",
            "row_axis": None,
            "unresolved_reasons": [topology_scan["status"]],
        }
    region = topology_scan["regions"][0]
    pages = _region_pages(document, region)
    render_snapshots = tuple(
        render_v1.read_authenticated_family_first_page_render_v1(
            semantic_capability,
            document_ordinal=document["document_ordinal"],
            physical_page=page,
        )
        for page in pages
    )
    numeric_document = numeric_v3.read_authenticated_family_first_ppocrv6_numeric_document_v3(
        numeric_capability,
        document_ordinal=document["document_ordinal"],
    )
    document_axis = build_accounting_family_document_axis_join_v1(
        document,
        numeric_document,
        selected_page_render_snapshots=render_snapshots,
    )
    joined_pages = project_accounting_family_document_pages_v1(document_axis)
    base_row_axis = build_accounting_family_row_axis_v1(joined_pages, family_spec)
    dash_rescues = _visible_dash_rescue_inputs(
        semantic_capability,
        document_ordinal=document["document_ordinal"],
        joined_pages=joined_pages,
        row_axis=base_row_axis,
        render_snapshots=render_snapshots,
    )
    row_axis = build_accounting_family_row_axis_v1(
        joined_pages,
        family_spec,
        visible_dash_rescues=dash_rescues,
    )
    column_context = build_accounting_family_column_context_v1(
        row_axis,
        joined_pages,
        family_spec,
        period_semantics=evaluation_spec["period_semantics"],
        expected_lane_unit_kinds=evaluation_spec["expected_lane_unit_kinds"],
        visible_dash_rescues=dash_rescues,
    )
    closure = build_accounting_additive_table_closure_v1(
        row_axis,
        joined_pages,
        family_spec,
        visible_dash_rescues=dash_rescues,
    )
    reasons = _unresolved_reasons(row_axis, column_context, closure, evaluation_spec)
    return {
        **base,
        "additive_closure": closure,
        "column_context": column_context,
        "document_axis_binding": _axis_binding(document_axis),
        "evidence_status": (
            "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
            if not reasons
            else "UNRESOLVED_EVIDENCE_GATES"
        ),
        "row_axis": row_axis,
        "unresolved_reasons": reasons,
    }


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    ready = sum(
        trial["evidence_status"] == "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
        for trial in trials
    )
    unique = sum(
        trial["topology_scan"]["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL" for trial in trials
    )
    not_observed = sum(trial["evidence_status"] == "NOT_OBSERVED_PROPOSAL_ONLY" for trial in trials)
    return {
        "document_count": len(trials),
        "evidence_ready_for_schema_review_count": ready,
        "mapping_verified_count": 0,
        "not_observed_count": not_observed,
        "unique_topology_document_count": unique,
        "unresolved_document_count": len(trials) - ready - not_observed,
    }


def _validate(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "ALL_FILING_ACCOUNTING_EVIDENCE_SWEEP_COMPLETE_PROPOSAL_ONLY"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["family_id"]) is not str
        or not value["family_id"]
        or type(value["family_spec"]) is not dict
        or set(value["family_spec"]) != {"sha256", "value"}
        or value["family_spec"]["sha256"] != canonical_json_sha256_v1(value["family_spec"]["value"])
        or type(value["evaluation_spec"]) is not dict
        or set(value["evaluation_spec"]) != {"sha256", "value"}
        or value["evaluation_spec"]["sha256"]
        != canonical_json_sha256_v1(value["evaluation_spec"]["value"])
        or type(value["input_indices"]) is not dict
        or set(value["input_indices"]) != _INDEX_FIELDS
        or any(type(item) is not str or not item for item in value["input_indices"].values())
        or not value["input_indices"]["numeric_receipt_id"].startswith("ffpniv3:receipt:")
        or not value["input_indices"]["semantic_index_id"].startswith("ffsiv1:index:")
        or type(value["trials"]) is not list
    ):
        raise _error("family-first accounting evidence sweep shape drifted")
    for ordinal, trial in enumerate(value["trials"], 1):
        if (
            type(trial) is not dict
            or set(trial) != _TRIAL_FIELDS
            or trial["document_ordinal"] != ordinal
            or type(trial["private_provenance"]) is not dict
            or type(trial["source_pdf_ref"]) is not dict
            or type(trial["topology_scan"]) is not dict
            or type(trial["evidence_status"]) is not str
            or type(trial["unresolved_reasons"]) is not list
            or any(type(reason) is not str or not reason for reason in trial["unresolved_reasons"])
        ):
            raise _error("family-first accounting evidence trial axis drifted")
        if trial["document_axis_binding"] is not None and (
            type(trial["document_axis_binding"]) is not dict
            or set(trial["document_axis_binding"]) != _BINDING_FIELDS
        ):
            raise _error("family-first document-axis binding drifted")
    if (
        type(value["metrics"]) is not dict
        or set(value["metrics"]) != _METRIC_FIELDS
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("family-first accounting evidence sweep metrics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("sweep_id")
    if identity != "ffaesv1:sweep:" + canonical_json_sha256_v1(material):
        raise _error("family-first accounting evidence sweep identity drifted")
    return canonical_clone_v1(value)


def build_authenticated_family_first_accounting_evidence_sweep_v1(
    semantic_index_capability: semantic_v1.AuthenticatedFamilyFirstSemanticIndexV1,
    numeric_index_capability: numeric_v3.AuthenticatedFamilyFirstPPocrV6NumericIndexV3,
    family_spec: Any,
    evaluation_spec: Any,
) -> dict[str, Any]:
    """Apply one generic family policy to every authenticated filing."""

    try:
        compiled = topology_v1._spec(family_spec)
    except (ValueError, RuntimeError) as exc:
        raise _error("family topology specification drifted") from exc
    policy = _evaluation_spec(evaluation_spec, compiled["family_id"])
    try:
        semantic_projection = semantic_v1.project_authenticated_family_first_semantic_index_v1(
            semantic_index_capability
        )
        numeric_projection = numeric_v3.project_authenticated_family_first_ppocrv6_numeric_index_v3(
            numeric_index_capability
        )
    except (ValueError, RuntimeError) as exc:
        raise _error("family-first accounting sweep inputs are not authenticated") from exc
    semantic_metrics = semantic_projection["metrics"]
    numeric_metrics = numeric_projection["metrics"]
    for key in ("document_count", "page_count", "sample_count"):
        if (
            type(semantic_metrics[key]) is not int
            or type(numeric_metrics[key]) is not int
            or semantic_metrics[key] != numeric_metrics[key]
        ):
            raise _error("semantic and numeric index denominators differ")
    trials = []
    for document_ordinal in range(1, semantic_metrics["document_count"] + 1):
        document = semantic_v1.read_authenticated_family_first_semantic_document_v1(
            semantic_index_capability, document_ordinal=document_ordinal
        )
        topology_scan = topology_v1.build_accounting_family_topology_scan_v1(
            _blind_pages(document), family_spec
        )
        trials.append(
            _trial(
                semantic_index_capability,
                numeric_index_capability,
                document,
                topology_scan,
                family_spec,
                policy,
            )
        )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "evaluation_spec": {
            "sha256": canonical_json_sha256_v1(policy),
            "value": policy,
        },
        "family_id": compiled["family_id"],
        "family_spec": {
            "sha256": canonical_json_sha256_v1(family_spec),
            "value": canonical_clone_v1(family_spec),
        },
        "format_version": FORMAT_VERSION,
        "input_indices": {
            "numeric_receipt_id": numeric_projection["receipt_id"],
            "semantic_index_id": semantic_projection["index_id"],
        },
        "metrics": _metrics(trials),
        "state": "ALL_FILING_ACCOUNTING_EVIDENCE_SWEEP_COMPLETE_PROPOSAL_ONLY",
        "trials": trials,
    }
    return _validate(
        {**material, "sweep_id": "ffaesv1:sweep:" + canonical_json_sha256_v1(material)}
    )


def validate_authenticated_family_first_accounting_evidence_sweep_replay_v1(
    value: Any,
    semantic_index_capability: semantic_v1.AuthenticatedFamilyFirstSemanticIndexV1,
    numeric_index_capability: numeric_v3.AuthenticatedFamilyFirstPPocrV6NumericIndexV3,
    family_spec: Any,
    evaluation_spec: Any,
) -> dict[str, Any]:
    """Exact-rebuild the persisted all-filing evidence proposal."""

    persisted = _validate(value)
    expected = build_authenticated_family_first_accounting_evidence_sweep_v1(
        semantic_index_capability,
        numeric_index_capability,
        family_spec,
        evaluation_spec,
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("family-first accounting evidence sweep does not replay exactly")
    return persisted
