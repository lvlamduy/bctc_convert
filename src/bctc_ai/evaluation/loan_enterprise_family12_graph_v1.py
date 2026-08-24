"""Thin Family-12 policy projection over the shared semantic-region graph.

All Vietnamese matching, owner carry/reset handling, provider-order
canonicalization, row composition, adaptive geometry, and scoped-table replay
live in ``accounting_semantic_region_graph_v1``. This adapter contributes only
the RNID-766/716 schema projection and Family-12-specific ambiguity/duplicate
dispositions. Every binding remains a proposal without mapping authority.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.evaluation.accounting_semantic_region_graph_v1 import (
    SPEC_FORMAT_VERSION as SEMANTIC_SPEC_FORMAT_VERSION,
)
from bctc_ai.evaluation.accounting_semantic_region_graph_v1 import (
    AccountingSemanticRegionGraphV1Error,
    build_accounting_semantic_region_graph_v1,
)
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.evaluation.loan_enterprise_family12_spec_v1 import (
    FAMILY_ID,
    PARENT_REPORT_NORM_ID,
    REPORT_NORM_ID,
    build_loan_enterprise_family12_spec_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "LoanEnterpriseFamily12GraphV1Error",
    "build_loan_enterprise_family12_graph_v1",
    "validate_loan_enterprise_family12_graph_replay_v1",
]


FORMAT_VERSION = "LOAN_ENTERPRISE_FAMILY12_GRAPH_V1"
CLAIM_BOUNDARY = (
    "RNID766_INSIDE_EXPLICIT_RNID716_SHARED_SEMANTIC_REGION_AND_GEOMETRY_"
    "PROPOSAL_ONLY_NO_NUMERIC_SCHEMA_MAPPING_GEMMA_ROUTING_OR_EXPORT_AUTHORITY"
)
_FOREIGN_COMPONENT = re.compile(r"\bchi nhanh\b.*\b(?:ngan hang con|cong ty con)\b.*\bnuoc ngoai\b")
_REASON_PROJECTION = {
    "EXPLICIT_OWNER_NOT_FOUND_INSIDE_CONTEXT_PAGE_BUDGET": (
        "EXPLICIT_OWNER_716_NOT_FOUND_WITHIN_TWO_PRECEDING_PAGES"
    ),
}


class LoanEnterpriseFamily12GraphV1Error(ValueError):
    """Family-12 projection identity or exact replay drifted."""


def _error(message: str) -> LoanEnterpriseFamily12GraphV1Error:
    return LoanEnterpriseFamily12GraphV1Error(message)


def _semantic_id(report_norm_id: int) -> str:
    return f"ROLE_{report_norm_id}"


def _generic_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Project matching policy only; historical counts never enter routing."""

    ambiguities = [
        {
            "aliases": canonical_clone_v1(item["aliases"]),
            "ambiguity_id": f"SOURCE_ONLY_AMBIGUITY_{ordinal}",
            "candidate_semantic_ids": sorted(
                _semantic_id(rnid) for rnid in item["candidate_report_norm_ids"]
            ),
            "reason": item["reason"],
        }
        for ordinal, item in enumerate(spec["source_only_ambiguities"])
    ]
    return {
        "branch_aliases": canonical_clone_v1(spec["branch_aliases"]),
        "context_classes": [
            {
                "aliases": canonical_clone_v1(item["aliases"]),
                "context_id": item["context_id"],
                "disposition": item["disposition"],
            }
            for item in spec["context_classes"]
        ],
        "family_id": FAMILY_ID,
        "format_version": SEMANTIC_SPEC_FORMAT_VERSION,
        "limits": {
            "branch_line_span": spec["limits"]["branch_line_span"],
            "context_page_budget": spec["limits"]["context_page_budget"],
            "maximum_body_lines_per_page": spec["limits"]["maximum_body_lines_per_page"],
            "row_label_line_span": 3,
        },
        "required_owner_context_id": "OWNER_716",
        "row_axis": [
            {
                "aliases": canonical_clone_v1(child["aliases"]),
                "bounded_edit_on_exact_miss": child["bounded_edit_on_exact_miss"],
                "semantic_id": _semantic_id(child["report_norm_id"]),
            }
            for child in spec["children"]
        ],
        "scoped_table": {
            "continuation_aliases": ["Tiếp theo"],
            "hard_veto_scope_aliases": [
                "Giao dịch với các bên liên quan",
                "Tiền gửi của khách hàng",
            ],
            "layout_modes": ["ROLES_AS_ROWS"],
            "limits": {
                "axis_tolerance_ppm": 120_000,
                "continuation_page_budget": 0,
                "max_owner_distance_lines": 96,
                "max_role_gap_lines": 32,
                "max_wrap_lines": 3,
                "minimum_cell_row_overlap_ppm": 400_000,
                "unlabeled_total_gap_jitter_ppm": 100_000,
                "unlabeled_total_max_gap_lines": 4,
                "unlabeled_total_max_numeric_columns": 16,
                "unlabeled_total_min_numeric_columns": 2,
            },
            "require_trailing_total_for_roles_as_columns": False,
            "trailing_total_aliases": [],
        },
        "source_only_ambiguities": ambiguities,
        "structural_reset_aliases": canonical_clone_v1(spec["structural_reset_aliases"]),
    }


def _semantic_to_child(spec: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {_semantic_id(child["report_norm_id"]): child for child in spec["children"]}


def _context_to_report_ids(spec: Mapping[str, Any]) -> dict[str, list[int]]:
    return {
        item["context_id"]: canonical_clone_v1(item["report_norm_ids"])
        for item in spec["context_classes"]
    }


def _project_reason(reason: str) -> str:
    return _REASON_PROJECTION.get(reason, reason)


def _project_owner(
    owner: Mapping[str, Any], context_report_ids: Mapping[str, Sequence[int]]
) -> dict[str, Any]:
    projected = canonical_clone_v1(owner)
    if "reason" in projected:
        projected["reason"] = _project_reason(projected["reason"])
    context_id = projected.get("context_id")
    if context_id == "OWNER_716" and projected.get("disposition") == (
        "EXPLICIT_OWNER_CONTEXT_ACCEPTED_FOR_PROPOSAL"
    ):
        projected["report_norm_id"] = PARENT_REPORT_NORM_ID
    closest = projected.get("closest_context_event")
    if type(closest) is dict:
        closest["report_norm_ids"] = canonical_clone_v1(
            context_report_ids.get(closest["context_id"], [])
        )
    return projected


def _project_row(
    row: Mapping[str, Any], children: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    semantic_id = row["semantic_id"]
    candidate_ids = [
        children[item]["report_norm_id"]
        for item in row["candidate_semantic_ids"]
        if item in children
    ]
    projected = {
        key: canonical_clone_v1(value)
        for key, value in row.items()
        if key not in {"candidate_semantic_ids", "semantic_id"}
    }
    projected["candidate_report_norm_ids"] = sorted(set(candidate_ids))
    projected["report_norm_id"] = (
        children[semantic_id]["report_norm_id"] if semantic_id in children else None
    )
    if semantic_id in children:
        projected["binding_class"] = children[semantic_id]["binding_class"]
    if projected["status"] == "SEMANTIC_ROW_TEXT_AND_GEOMETRY_PROPOSAL_REQUIRES_REPLAY":
        projected["status"] = "SCHEMA_ROW_TEXT_AND_GEOMETRY_PROPOSAL_REQUIRES_REPLAY"
    return projected


def _foreign_component(row: Mapping[str, Any]) -> bool:
    return bool(_FOREIGN_COMPONENT.search(normalize_vietnamese_anchor_v1(row["surface"])))


def _unique_bindings(
    rows: list[dict[str, Any]], *, promotion_eligible: bool
) -> list[dict[str, Any]]:
    if not promotion_eligible:
        return []
    eligible = [
        row
        for row in rows
        if row["report_norm_id"] is not None
        and row["status"] == "SCHEMA_ROW_TEXT_AND_GEOMETRY_PROPOSAL_REQUIRES_REPLAY"
    ]
    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in eligible:
        grouped.setdefault(row["report_norm_id"], []).append(row)
    bindings = []
    for report_norm_id in sorted(grouped):
        candidates = grouped[report_norm_id]
        if len(candidates) == 1:
            selected = candidates[0]
        elif report_norm_id == 782 and sum(_foreign_component(row) for row in candidates) == 1:
            selected = next(row for row in candidates if _foreign_component(row))
        else:
            selected = None
        for row in candidates:
            if row is selected:
                continue
            row["candidate_report_norm_ids"] = [report_norm_id]
            row["report_norm_id"] = None
            row["reason"] = "DUPLICATE_SCHEMA_ROLE_FAIL_CLOSED"
            row["status"] = "DUPLICATE_SCHEMA_ROLE_SOURCE_ONLY_AMBIGUOUS"
        if selected is None:
            continue
        material = {
            "evidence_proposal_id": selected["proposal_id"],
            "foreign_branch_or_subsidiary_component": _foreign_component(selected),
            "report_norm_id": report_norm_id,
            "status": "UNIQUE_SCHEMA_BINDING_PROPOSAL_NO_MAPPING_AUTHORITY",
        }
        bindings.append(
            {**material, "binding_id": "lef12v1:binding:" + canonical_json_sha256_v1(material)}
        )
    return bindings


def _near_region(
    *,
    branch: Mapping[str, Any],
    owner: Mapping[str, Any],
    reason: str,
    geometry: Mapping[str, Any] | None = None,
    rows: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    material = {
        "branch": canonical_clone_v1(branch),
        "owner_context": canonical_clone_v1(owner),
        "reason": _project_reason(reason),
        "source_only_geometry_proposal": (
            canonical_clone_v1(geometry) if geometry is not None else None
        ),
        "source_only_row_proposals": canonical_clone_v1(list(rows)),
        "status": "SOURCE_ONLY_NEAR_REGION_FAIL_CLOSED",
    }
    return {**material, "near_region_id": "lef12v1:near:" + canonical_json_sha256_v1(material)}


def _build(region_pages: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    family_spec = build_loan_enterprise_family12_spec_v1()
    semantic_spec = _generic_spec(family_spec)
    try:
        semantic_result = build_accounting_semantic_region_graph_v1(region_pages, semantic_spec)
    except AccountingSemanticRegionGraphV1Error as error:
        raise _error(str(error)) from error
    children = _semantic_to_child(family_spec)
    context_ids = _context_to_report_ids(family_spec)
    regions = []
    near_regions = []
    for near in semantic_result["near_regions"]:
        near_regions.append(
            _near_region(
                branch=near["branch"],
                owner=_project_owner(near["owner_context"], context_ids),
                reason=near["reason"],
            )
        )
    for semantic_region in semantic_result["regions"]:
        owner = _project_owner(semantic_region["owner_context"], context_ids)
        rows = [_project_row(row, children) for row in semantic_region["row_proposals"]]
        bindings = _unique_bindings(rows, promotion_eligible=semantic_region["promotion_eligible"])
        if not bindings:
            reason = (
                "SHARED_SCOPED_TABLE_FAIL_CLOSED"
                if not semantic_region["promotion_eligible"]
                else "NO_UNIQUE_SCHEMA_ROW_WITH_VALUE_GEOMETRY"
            )
            near_regions.append(
                _near_region(
                    branch=semantic_region["branch"],
                    owner=owner,
                    reason=reason,
                    geometry=semantic_region["adaptive_geometry_v2"],
                    rows=rows,
                )
            )
            continue
        material = {
            "adaptive_geometry_v2": semantic_region["adaptive_geometry_v2"],
            "binding_proposals": bindings,
            "branch": semantic_region["branch"],
            "owner_context": owner,
            "row_proposals": rows,
            "shared_scoped_table_v1": semantic_region["shared_scoped_table_v1"],
            "status": "FAMILY12_STRUCTURAL_PROPOSAL_REQUIRES_NUMERIC_AND_SCHEMA_REPLAY",
        }
        regions.append(
            {**material, "region_id": "lef12v1:region:" + canonical_json_sha256_v1(material)}
        )
    bounded_absences = []
    if semantic_result["metrics"]["branch_candidate_count"] == 0:
        bounded_absences.append(
            {
                "page_sequences": semantic_result["bounded_absences"][0]["page_sequences"],
                "reason": "NO_FAMILY12_BRANCH_IN_CALLER_BOUNDED_PAGES",
                "status": "BOUNDED_ABSENCE_NO_GLOBAL_CORPUS_CLAIM",
            }
        )
    bounded_absences.extend(
        {
            "near_region_id": item["near_region_id"],
            "reason": item["reason"],
            "status": "BOUNDED_ABSENCE_FROM_ACCEPTED_FAMILY12_REGION",
        }
        for item in near_regions
    )
    metrics = {
        "approximate_alias_comparison_count": semantic_result["matcher_metrics"][
            "approximate_alias_comparison_count"
        ],
        "bounded_absence_count": len(bounded_absences),
        "branch_candidate_count": semantic_result["metrics"]["branch_candidate_count"],
        "cross_page_owner_region_count": sum(
            item["owner_context"]["page_distance"] > 0 for item in regions
        ),
        "region_count": len(regions),
        "source_only_ambiguous_row_count": sum(
            row["status"].endswith("AMBIGUOUS")
            for region in regions
            for row in region["row_proposals"]
        )
        + sum(
            row["status"].endswith("AMBIGUOUS")
            for near in near_regions
            for row in near["source_only_row_proposals"]
        ),
        "unique_binding_proposal_count": sum(
            len(region["binding_proposals"]) for region in regions
        ),
    }
    safety = canonical_clone_v1(family_spec["safety"])
    safety.update(
        {
            "authenticated_store_or_full_corpus_used": False,
            "gemma_or_other_model_authority": False,
            "historical_evidence_metadata_used_for_matching": False,
            "shared_geometry_or_scoped_graph_grants_mapping_authority": False,
            "shared_semantic_region_failure_can_promote_mapping": False,
            "two_role_table_without_owner_716_can_accept": False,
        }
    )
    material = {
        "bounded_absences": bounded_absences,
        "claim_boundary": CLAIM_BOUNDARY,
        "evidence_binding": {
            "canonical_page_evidence_sha256": semantic_result["evidence_binding"][
                "canonical_page_evidence_sha256"
            ],
            "family_spec_id": "lef12v1:spec:" + canonical_json_sha256_v1(family_spec),
            "shared_semantic_region_result_id": semantic_result["result_id"],
        },
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "historical_evidence_summary": family_spec["historical_evidence_summary"],
        "metrics": metrics,
        "near_regions": near_regions,
        "parent_report_norm_id": PARENT_REPORT_NORM_ID,
        "regions": sorted(
            regions,
            key=lambda item: (
                item["branch"]["page_sequence"],
                item["branch"]["evidence"][0]["bbox"][1],
                item["region_id"],
            ),
        ),
        "report_norm_id": REPORT_NORM_ID,
        "safety": safety,
        "status": (
            "FAMILY12_PROPOSAL_ENUMERATION_WITH_UNRESOLVED_NEAR_REGIONS"
            if near_regions
            else "FAMILY12_PROPOSAL_ENUMERATION"
        ),
    }
    return {**material, "result_id": "lef12v1:result:" + canonical_json_sha256_v1(material)}


def build_loan_enterprise_family12_graph_v1(
    region_pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Project shared semantic-region evidence into Family-12 RNID proposals."""

    return _build(region_pages)


def validate_loan_enterprise_family12_graph_replay_v1(
    value: Any, region_pages: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Rebuild the shared graph and Family-12 policy projection exactly."""

    if type(value) is not dict or value.get("format_version") != FORMAT_VERSION:
        raise _error("Family-12 graph result identity drifted")
    identity = value.get("result_id")
    if type(identity) is not str:
        raise _error("Family-12 graph result ID drifted")
    material = canonical_clone_v1(value)
    material.pop("result_id", None)
    if identity != "lef12v1:result:" + canonical_json_sha256_v1(material):
        raise _error("Family-12 graph content identity drifted")
    rebuilt = _build(region_pages)
    if not same_typed_json_v1(value, rebuilt):
        raise _error("Family-12 graph does not replay exactly")
    return rebuilt
