"""Thin Family-12 policy projection over the shared semantic-region graph.

All Vietnamese matching, owner carry/reset handling, provider-order
canonicalization, row composition, adaptive geometry, and scoped-table replay
live in ``accounting_semantic_region_graph_v1``. This adapter contributes only
the RNID-766/716 schema projection and Family-12-specific ambiguity/duplicate
dispositions. Every binding remains a proposal without mapping authority.
"""

from __future__ import annotations

import hashlib
import re
import stat
import unicodedata
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from bctc_ai.evaluation import family_first_document_evidence_store_v1 as document_store_v1
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
from bctc_ai.evaluation.authenticated_semantic_region_snapshot_v1 import (
    FamilyFirstRegionReceiptContractV2Error,
    build_authenticated_semantic_region_snapshot_v1,
    validate_authenticated_semantic_region_snapshot_replay_v1,
    validate_family_first_region_retrieval_receipt_v2,
)
from bctc_ai.evaluation.family_first_region_retrieval_v1 import (
    FamilyFirstRegionRetrievalV1Error,
    validate_replayed_authenticated_family_first_region_receipt_v2,
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
    "AUTHENTICATED_BATCH_FORMAT_VERSION",
    "FORMAT_VERSION",
    "LOAN_ENTERPRISE_FAMILY12_REGION_QUERY_SPEC_V2",
    "LOAN_ENTERPRISE_FAMILY12_REGION_QUERY_TRUST_CLOSURE_V2",
    "LoanEnterpriseFamily12GraphV1Error",
    "build_loan_enterprise_family12_graph_v1",
    "build_loan_enterprise_family12_authenticated_snapshot_graphs_v1",
    "build_loan_enterprise_family12_region_query_spec_v2",
    "validate_loan_enterprise_family12_authenticated_snapshot_graphs_replay_v1",
    "validate_loan_enterprise_family12_graph_replay_v1",
]


FORMAT_VERSION = "LOAN_ENTERPRISE_FAMILY12_GRAPH_V1"
_AUTHENTICATED_DOCUMENT_FORMAT_VERSION = "LOAN_ENTERPRISE_FAMILY12_AUTHENTICATED_SNAPSHOT_GRAPH_V1"
AUTHENTICATED_BATCH_FORMAT_VERSION = (
    "LOAN_ENTERPRISE_FAMILY12_AUTHENTICATED_SNAPSHOT_GRAPH_BATCH_V1"
)
CLAIM_BOUNDARY = (
    "RNID766_INSIDE_EXPLICIT_RNID716_SHARED_SEMANTIC_REGION_AND_GEOMETRY_"
    "PROPOSAL_ONLY_NO_NUMERIC_SCHEMA_MAPPING_GEMMA_ROUTING_OR_EXPORT_AUTHORITY"
)
_AUTHENTICATED_DOCUMENT_CLAIM_BOUNDARY = (
    "VALIDATED_FAMILY12_RETRIEVAL_OUTCOME_AND_CALLER_AUTHENTICATED_SELECTED_"
    "SNAPSHOT_BOUND_SHARED_GRAPH_PROPOSAL_ONLY_NO_NUMERIC_MAPPING_OR_SCHEMA_AUTHORITY"
)
_AUTHENTICATED_DOCUMENT_AUTHORITY = {
    "caller_authenticated_selected_snapshot_required": True,
    "mapping_authority": False,
    "numeric_authority": False,
    "receipt_self_hash_is_authentication_authority": False,
    "schema_authority": False,
    "snapshot_self_hash_is_authentication_authority": False,
}
_AUTHENTICATED_BATCH_CLAIM_BOUNDARY = (
    "ONE_PUBLIC_AUTHENTICATED_RETRIEVAL_REPLAY_THEN_COMPLETE_FAMILY12_SELECTED_"
    "SNAPSHOT_DENOMINATOR_GRAPH_PROPOSAL_ONLY_NO_NUMERIC_MAPPING_OR_SCHEMA_AUTHORITY"
)
_AUTHENTICATED_BATCH_AUTHORITY = {
    "authenticated_receipt_public_replay_required": True,
    "complete_document_denominator_required": True,
    "mapping_authority": False,
    "numeric_authority": False,
    "schema_authority": False,
    "snapshot_self_hash_is_authentication_authority": False,
}
_AUTHENTICATED_SNAPSHOT_READ_BATCH_SIZE = 16
_FOREIGN_COMPONENT = re.compile(r"\bchi nhanh\b.*\b(?:ngan hang con|cong ty con)\b.*\bnuoc ngoai\b")
_REASON_PROJECTION = {
    "EXPLICIT_OWNER_NOT_FOUND_INSIDE_CONTEXT_PAGE_BUDGET": (
        "EXPLICIT_OWNER_716_NOT_FOUND_WITHIN_TWO_PRECEDING_PAGES"
    ),
}

_ADAPTER_PATH = Path("src/bctc_ai/evaluation/loan_enterprise_family12_graph_v1.py")
LOAN_ENTERPRISE_FAMILY12_REGION_QUERY_TRUST_CLOSURE_V2 = {
    "shared_semantic_engine_ref": {
        "path": "src/bctc_ai/evaluation/accounting_semantic_region_graph_v1.py",
        "sha256": "bad85c88e3b257fbc950e4d916f0efd020961d668ae15584f1e7941791f5c621",
        "size_bytes": 46_991,
    },
    "family_spec_ref": {
        "path": "src/bctc_ai/evaluation/loan_enterprise_family12_spec_v1.py",
        "sha256": "c4323276c622c6d133771ea6b6057d20c62553ae9d06a93c03fb28732a26e546",
        "size_bytes": 12_888,
    },
}


class LoanEnterpriseFamily12GraphV1Error(ValueError):
    """Family-12 projection identity or exact replay drifted."""


def _error(message: str) -> LoanEnterpriseFamily12GraphV1Error:
    return LoanEnterpriseFamily12GraphV1Error(message)


def _semantic_id(report_norm_id: int) -> str:
    return f"ROLE_{report_norm_id}"


def _stable_query_content_ref(
    project_root: Path,
    relative: Path,
    *,
    label: str,
) -> dict[str, Any]:
    path = project_root / relative
    try:
        before = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(before.st_mode):
            raise _error(f"Family-12 query {label} is not one regular nofollow file")
        payload = path.read_bytes()
        after = path.lstat()
    except OSError as error:
        raise _error(f"Family-12 query {label} cannot be read stably") from error
    before_identity = (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_size,
        before.st_mtime_ns,
    )
    after_identity = (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_size,
        after.st_mtime_ns,
    )
    if before_identity != after_identity or len(payload) != before.st_size:
        raise _error(f"Family-12 query {label} changed during stable read")
    return {
        "path": relative.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _verified_query_trust_closure(project_root: Path) -> dict[str, Any]:
    observed = {
        key: _stable_query_content_ref(
            project_root,
            Path(reference["path"]),
            label=key.replace("_", " "),
        )
        for key, reference in sorted(LOAN_ENTERPRISE_FAMILY12_REGION_QUERY_TRUST_CLOSURE_V2.items())
    }
    if not same_typed_json_v1(
        observed,
        LOAN_ENTERPRISE_FAMILY12_REGION_QUERY_TRUST_CLOSURE_V2,
    ):
        raise _error("Family-12 query spec/shared semantic trust closure drifted")
    return observed


def _query_anchor(
    anchor_id: str,
    surface: str,
    *,
    maximum_edit_distance: int,
    role: str,
    probes: Sequence[str] | None = None,
) -> dict[str, Any]:
    canonical_surface = unicodedata.normalize("NFC", " ".join(surface.split()))
    normalized_probes = probes or [normalize_vietnamese_anchor_v1(canonical_surface)]
    return {
        "anchor_id": anchor_id,
        "canonical_alias_id": anchor_id + "_CANONICAL",
        "fts_probes": sorted(
            {normalize_vietnamese_anchor_v1(probe) for probe in normalized_probes}
        ),
        "max_edit_distance": maximum_edit_distance,
        "role": role,
        "surface": canonical_surface,
        "verified_historical_variants": [],
    }


def _query_spec(project_root: Path) -> dict[str, Any]:
    """Build only a retrieval shortlist; the shared graph retains semantics."""

    _verified_query_trust_closure(project_root)
    family_spec = build_loan_enterprise_family12_spec_v1()
    owner = next(
        item for item in family_spec["context_classes"] if item["context_id"] == "OWNER_716"
    )
    anchors = [
        _query_anchor(
            "BRANCH_LOAI_HINH_DOANH_NGHIEP",
            "Loại hình doanh nghiệp",
            maximum_edit_distance=1,
            probes=["hình doanh nghiệp", "loại hình doanh nghiệp"],
            role="TARGET",
        ),
        _query_anchor(
            "BRANCH_THEO_DOI_TUONG_KHACH_HANG",
            "Theo đối tượng khách hàng",
            maximum_edit_distance=1,
            probes=["đối tượng khách hàng", "theo đối tượng khách hàng"],
            role="TARGET",
        ),
    ]
    anchors.extend(
        _query_anchor(
            f"OWNER_716_{ordinal:02d}",
            surface,
            maximum_edit_distance=0,
            role="OWNER",
        )
        for ordinal, surface in enumerate(owner["aliases"], 1)
    )
    role_surfaces = {
        child["report_norm_id"]: (
            "Thành phần kinh tế khác" if child["report_norm_id"] == 782 else child["canonical_name"]
        )
        for child in family_spec["children"]
    }
    anchors.extend(
        _query_anchor(
            f"SEMANTIC_ROLE_{report_norm_id}",
            surface,
            maximum_edit_distance=0,
            role="CONTEXT",
        )
        for report_norm_id, surface in sorted(role_surfaces.items())
    )
    branch_ids = sorted(
        item["anchor_id"] for item in anchors if item["anchor_id"].startswith("BRANCH_")
    )
    owner_ids = sorted(
        item["anchor_id"] for item in anchors if item["anchor_id"].startswith("OWNER_716_")
    )
    role_ids = sorted(
        item["anchor_id"] for item in anchors if item["anchor_id"].startswith("SEMANTIC_ROLE_")
    )
    reset_surfaces = {
        *family_spec["structural_reset_aliases"],
        "Các giao dịch với bên liên quan",
        "Các giao dịch với các bên liên quan",
        "Giao dịch tiền gửi với MB",
        "Phân tích tiền gửi khách hàng theo loại hình doanh nghiệp",
        "Phân tích tiền gửi khách hàng theo đối tượng khách hàng",
        "Theo loại hình doanh nghiệp tiền gửi",
        "Tiền gửi khách hàng",
    }
    return {
        "anchors": sorted(anchors, key=lambda item: item["anchor_id"]),
        "family_id": FAMILY_ID,
        "format_version": "FAMILY_FIRST_REGION_QUERY_SPEC_V2",
        "local_required_groups": [
            {
                "anchor_ids": role_ids,
                "group_id": "EXACT_FAMILY12_SEMANTIC_ROLE",
                "mode": "ANY",
                "page_relation": "SAME_OR_ADJACENT_PAGE",
            },
            {
                "anchor_ids": owner_ids,
                "group_id": "OWNER_716_LOCAL",
                "mode": "ANY",
                "page_relation": "SAME_OR_ADJACENT_PAGE",
            },
        ],
        "max_hit_lines": 100_000,
        "max_selected_pages_per_document": 24,
        "neighbor_pages_after": 1,
        "neighbor_pages_before": 2,
        "seed_groups": [
            {
                "anchor_ids": branch_ids,
                "group_id": "FAMILY12_SHORT_BRANCH_SEED",
                "mode": "ANY",
                "page_relation": "SAME_PAGE",
                "priority": 1,
            }
        ],
        "semantic_assignment_adapter_ref": _stable_query_content_ref(
            project_root,
            _ADAPTER_PATH,
            label="semantic assignment adapter",
        ),
        "structural_reset_fragments": sorted(
            unicodedata.normalize("NFC", " ".join(surface.split())) for surface in reset_surfaces
        ),
        "structural_reset_max_line_ordinal": 3,
        "window_line_span": 3,
        "zero_hit_policy": "FULL_DOCUMENT_FALLBACK",
    }


_PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOAN_ENTERPRISE_FAMILY12_REGION_QUERY_SPEC_V2 = _query_spec(_PROJECT_ROOT)


def build_loan_enterprise_family12_region_query_spec_v2(
    project_root: str | Path,
) -> dict[str, Any]:
    """Return the bank-blind, adapter-bound Family-12 V2 shortlist spec."""

    observed = _query_spec(Path(project_root).resolve())
    if not same_typed_json_v1(observed, LOAN_ENTERPRISE_FAMILY12_REGION_QUERY_SPEC_V2):
        raise _error("Family-12 query differs from its loaded adapter trust closure")
    from bctc_ai.evaluation.family_first_region_retrieval_v1 import (
        validate_family_first_region_query_spec_v2,
    )

    return validate_family_first_region_query_spec_v2(observed)


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


def _snapshot_projection_binding(projection: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "line_bindings_sha256": canonical_json_sha256_v1(projection["line_bindings"]),
        "metrics": canonical_clone_v1(projection["metrics"]),
        "page_bindings_sha256": canonical_json_sha256_v1(projection["page_bindings"]),
        "projection_id": projection["projection_id"],
        "region_pages_sha256": canonical_json_sha256_v1(projection["region_pages"]),
        "source_binding": canonical_clone_v1(projection["source_binding"]),
    }


def _authenticated_snapshot_graph_from_validated_receipt(
    receipt: Mapping[str, Any],
    selected_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    projection = build_authenticated_semantic_region_snapshot_v1(selected_snapshot)
    validate_authenticated_semantic_region_snapshot_replay_v1(projection, selected_snapshot)
    source = projection["source_binding"]
    ordinal = source["document_ordinal"]
    if not 1 <= ordinal <= len(receipt["documents"]):
        raise _error("Family-12 selected snapshot lies outside retrieval denominator")
    outcome = receipt["documents"][ordinal - 1]
    selected_pages = source["selected_pages"]
    receipt_manifest_id = receipt["source_binding"].get("manifest_id")
    if (
        source["manifest_id"] != receipt_manifest_id
        or outcome["document_id"] != source["document_id"]
        or outcome["document_packet_id"] != source["document_packet_id"]
        or outcome["document_evidence_root_sha256"] != source["document_evidence_root_sha256"]
        or outcome["selected_pages"] != selected_pages
        or outcome.get("document_page_count") != source["document_page_count"]
        or outcome.get("document_line_count") != source["document_line_count"]
    ):
        raise _error("Family-12 receipt/snapshot evidence binding drifted")
    if outcome.get("requires_full_document_review") is True and selected_pages != list(
        range(1, source["document_page_count"] + 1)
    ):
        raise _error("Family-12 fallback outcome is not one full selected page axis")
    graph = build_loan_enterprise_family12_graph_v1(projection["region_pages"])
    validate_loan_enterprise_family12_graph_replay_v1(graph, projection["region_pages"])
    query_id = receipt["source_binding"]["query_spec_id"]
    material = {
        "authority": canonical_clone_v1(_AUTHENTICATED_DOCUMENT_AUTHORITY),
        "claim_boundary": _AUTHENTICATED_DOCUMENT_CLAIM_BOUNDARY,
        "document_id": source["document_id"],
        "document_ordinal": ordinal,
        "evidence_binding": {
            "document_evidence_root_sha256": source["document_evidence_root_sha256"],
            "document_packet_id": source["document_packet_id"],
            "manifest_id": source["manifest_id"],
            "outcome_id": outcome["outcome_id"],
            "projection_id": projection["projection_id"],
            "query_selection_id": source["query_selection_id"],
            "query_spec_id": query_id,
            "receipt_id": receipt["receipt_id"],
            "snapshot_id": source["snapshot_id"],
        },
        "family_id": FAMILY_ID,
        "format_version": _AUTHENTICATED_DOCUMENT_FORMAT_VERSION,
        "graph": graph,
        "metrics": {
            "line_count": projection["metrics"]["line_count"],
            "page_count": projection["metrics"]["page_count"],
            "zero_line_page_count": projection["metrics"]["zero_line_page_count"],
        },
        "outcome": {
            "fallback_reason": outcome.get("fallback_reason"),
            "requires_full_document_review": outcome.get("requires_full_document_review"),
            "selected_pages": canonical_clone_v1(selected_pages),
            "selection_mode": outcome.get("selection_mode"),
        },
        "snapshot_projection_binding": _snapshot_projection_binding(projection),
        "state": "FAMILY12_AUTHENTICATED_SELECTED_SNAPSHOT_GRAPH_PROPOSAL_ONLY",
    }
    return {
        **material,
        "result_id": "lef12asv1:document:" + canonical_json_sha256_v1(material),
    }


def _authenticated_snapshot_graphs(
    capability: document_store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    retrieval_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    query = build_loan_enterprise_family12_region_query_spec_v2(_PROJECT_ROOT)
    try:
        replayed_receipt = validate_replayed_authenticated_family_first_region_receipt_v2(
            capability,
            query,
            retrieval_receipt,
        )
        receipt = validate_family_first_region_retrieval_receipt_v2(
            replayed_receipt,
            query,
            FAMILY_ID,
        )
    except (
        FamilyFirstRegionReceiptContractV2Error,
        FamilyFirstRegionRetrievalV1Error,
    ) as error:
        raise _error(str(error)) from error
    selections = tuple(
        (outcome["document_ordinal"], tuple(outcome["selected_pages"]))
        for outcome in receipt["documents"]
    )
    documents = []
    try:
        for offset in range(0, len(selections), _AUTHENTICATED_SNAPSHOT_READ_BATCH_SIZE):
            selection_batch = selections[offset : offset + _AUTHENTICATED_SNAPSHOT_READ_BATCH_SIZE]
            snapshot_batch = (
                document_store_v1.read_authenticated_family_first_documents_selected_pages_v1(
                    capability,
                    document_page_selections=selection_batch,
                )
            )
            if type(snapshot_batch) is not tuple or len(snapshot_batch) != len(selection_batch):
                raise _error("Family-12 authenticated snapshot batch axis drifted")
            for expected, selected_snapshot in zip(
                selection_batch,
                snapshot_batch,
                strict=True,
            ):
                document = _authenticated_snapshot_graph_from_validated_receipt(
                    receipt,
                    selected_snapshot,
                )
                if document["document_ordinal"] != expected[0]:
                    raise _error("Family-12 authenticated snapshot source order drifted")
                documents.append(document)
    except document_store_v1.FamilyFirstDocumentEvidenceStoreV1Error as error:
        raise _error(str(error)) from error
    if [item["document_ordinal"] for item in documents] != list(
        range(1, len(receipt["documents"]) + 1)
    ):
        raise _error("Family-12 authenticated snapshots do not cover the receipt denominator")
    graph_metrics = [document["graph"]["metrics"] for document in documents]
    projection_metrics = [document["metrics"] for document in documents]
    receipt_metrics = receipt["metrics"]
    metrics = {
        "bounded_absence_count": sum(item["bounded_absence_count"] for item in graph_metrics),
        "cross_page_owner_region_count": sum(
            item["cross_page_owner_region_count"] for item in graph_metrics
        ),
        "document_count": len(documents),
        "fallback_document_count": receipt_metrics["fallback_document_count"],
        "indexed_document_count": (len(documents) - receipt_metrics["fallback_document_count"]),
        "line_count": sum(item["line_count"] for item in projection_metrics),
        "near_region_count": sum(len(document["graph"]["near_regions"]) for document in documents),
        "page_count": sum(item["page_count"] for item in projection_metrics),
        "region_count": sum(item["region_count"] for item in graph_metrics),
        "source_only_ambiguous_row_count": sum(
            item["source_only_ambiguous_row_count"] for item in graph_metrics
        ),
        "unique_binding_proposal_count": sum(
            item["unique_binding_proposal_count"] for item in graph_metrics
        ),
        "zero_line_page_count": sum(item["zero_line_page_count"] for item in projection_metrics),
    }
    material = {
        "authority": canonical_clone_v1(_AUTHENTICATED_BATCH_AUTHORITY),
        "claim_boundary": _AUTHENTICATED_BATCH_CLAIM_BOUNDARY,
        "documents": documents,
        "evidence_binding": {
            "manifest_id": receipt["source_binding"]["manifest_id"],
            "query_spec_id": receipt["source_binding"]["query_spec_id"],
            "receipt_id": receipt["receipt_id"],
        },
        "family_id": FAMILY_ID,
        "format_version": AUTHENTICATED_BATCH_FORMAT_VERSION,
        "metrics": metrics,
        "state": "FAMILY12_AUTHENTICATED_CORPUS_GRAPH_PROPOSALS_ONLY",
    }
    return {**material, "result_id": "lef12asv1:batch:" + canonical_json_sha256_v1(material)}


def build_loan_enterprise_family12_authenticated_snapshot_graphs_v1(
    capability: document_store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    retrieval_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay once, hydrate bounded authenticated batches, and graph the denominator."""

    return _authenticated_snapshot_graphs(capability, retrieval_receipt)


def validate_loan_enterprise_family12_authenticated_snapshot_graphs_replay_v1(
    value: Any,
    capability: document_store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    retrieval_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay the authenticated receipt once and rebuild the complete batch exactly."""

    if type(value) is not dict or value.get("format_version") != AUTHENTICATED_BATCH_FORMAT_VERSION:
        raise _error("Family-12 authenticated snapshot batch identity drifted")
    material = canonical_clone_v1(value)
    result_id = material.pop("result_id", None)
    if result_id != "lef12asv1:batch:" + canonical_json_sha256_v1(material):
        raise _error("Family-12 authenticated snapshot batch content identity drifted")
    rebuilt = _authenticated_snapshot_graphs(
        capability,
        retrieval_receipt,
    )
    if not same_typed_json_v1(value, rebuilt):
        raise _error("Family-12 authenticated snapshot batch does not replay exactly")
    return rebuilt
