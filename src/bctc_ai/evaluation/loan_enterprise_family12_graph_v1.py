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

from bctc_ai.evaluation import accounting_semantic_region_graph_v1 as semantic_region_v1
from bctc_ai.evaluation import family_first_document_evidence_store_v1 as document_store_v1
from bctc_ai.evaluation.accounting_minimal_unique_anchor_resolution_v1 import (
    build_accounting_minimal_unique_anchor_resolution_v1,
)
from bctc_ai.evaluation.accounting_scoped_table_graph_v1 import (
    SPEC_FORMAT_VERSION as SCOPED_TABLE_SPEC_FORMAT_VERSION,
)
from bctc_ai.evaluation.accounting_scoped_table_graph_v1 import (
    AccountingScopedTableGraphV1Error,
    build_accounting_scoped_table_graph_v1,
)
from bctc_ai.evaluation.accounting_semantic_region_graph_v1 import (
    SPEC_FORMAT_VERSION as SEMANTIC_SPEC_FORMAT_VERSION,
)
from bctc_ai.evaluation.accounting_semantic_region_graph_v1 import (
    AccountingSemanticRegionGraphV1Error,
    ScopedTableEnforcementV1,
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
    "DECLARED_SCHEMA_PARENT_BOUND_RNID766_OR_EXACT_RNID6058_INSIDE_EXPLICIT_"
    "RNID716_SHARED_SEMANTIC_REGION_AND_GEOMETRY_"
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
    "minimal_unique_anchor_resolver_ref": {
        "path": "src/bctc_ai/evaluation/accounting_minimal_unique_anchor_resolution_v1.py",
        "sha256": "b24b5fa936bbc4b168548e9317d124aa42af39a100a434ea5afcaa827274d640",
        "size_bytes": 10_110,
    },
    "shared_semantic_engine_ref": {
        "path": "src/bctc_ai/evaluation/accounting_semantic_region_graph_v1.py",
        "sha256": "59542b4bab1c8c27efbc4b76b50bf829865237860b6fc67b43b2e6ccead1dccc",
        "size_bytes": 72_793,
    },
    "shared_scoped_table_engine_ref": {
        "path": "src/bctc_ai/evaluation/accounting_scoped_table_graph_v1.py",
        "sha256": "347782a12e7da48d52807bf0a035e4df6727a05822b99c9566b72afe175de014",
        "size_bytes": 178_406,
    },
    "family_spec_ref": {
        "path": "src/bctc_ai/evaluation/loan_enterprise_family12_spec_v1.py",
        "sha256": "7f8951440ba768cb35dfe76a56768cb321dbfd900df1f9e3336928178328693f",
        "size_bytes": 21_726,
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


def _component_query_probes(component: Mapping[str, Any]) -> list[str]:
    probes = set()
    for alias in component["aliases"]:
        normalized = normalize_vietnamese_anchor_v1(alias)
        probes.add(normalized)
        tokens = normalized.split()
        if len(tokens) >= 4:
            probes.add(" ".join(tokens[1:]))
    return sorted(probes)


def _local_role_query_probes(surface: str, *, allow_bounded_edit: bool) -> list[str]:
    """Keep local role validation at least as inclusive as the shared row matcher."""

    normalized = normalize_vietnamese_anchor_v1(surface)
    if not allow_bounded_edit:
        return [normalized]
    # These anchors are never global seeds.  Trigram probes only make the
    # bounded local matcher reachable after one OCR edit; the full edit-distance
    # check still decides whether the occurrence is proved.
    probes = {normalized}
    probes.update(
        gram
        for index in range(len(normalized) - 2)
        if (gram := normalized[index : index + 3]).isalnum()
    )
    return sorted(probes)


def _query_spec(project_root: Path) -> dict[str, Any]:
    """Build only a retrieval shortlist; the shared graph retains semantics."""

    _verified_query_trust_closure(project_root)
    family_spec = build_loan_enterprise_family12_spec_v1()
    owner = next(
        item for item in family_spec["context_classes"] if item["context_id"] == "OWNER_716"
    )
    anchors = [
        _query_anchor(
            component["component_id"],
            component["aliases"][0],
            maximum_edit_distance=int(component["bounded_edit_on_exact_miss"]),
            probes=_component_query_probes(component),
            role="TARGET",
        )
        for component in family_spec["branch_components"]
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
    for child in family_spec["children"]:
        preferred = normalize_vietnamese_anchor_v1(
            "Thành phần kinh tế khác" if child["report_norm_id"] == 782 else child["canonical_name"]
        )
        for ordinal, surface in enumerate(child["aliases"], 1):
            # Bare ``Khác`` is intentionally too generic for retrieval.  A real
            # branchless rescue needs two distinct child roles, so its other
            # declared role remains a complete and substantially safer gate.
            if child["report_norm_id"] == 782 and normalize_vietnamese_anchor_v1(surface) == "khac":
                continue
            anchor_id = f"SEMANTIC_ROLE_{child['report_norm_id']}"
            if normalize_vietnamese_anchor_v1(surface) != preferred:
                anchor_id += f"_ALIAS_{ordinal:02d}"
            allow_bounded_edit = bool(child["bounded_edit_on_exact_miss"])
            anchors.append(
                _query_anchor(
                    anchor_id,
                    surface,
                    maximum_edit_distance=int(allow_bounded_edit),
                    probes=_local_role_query_probes(
                        surface,
                        allow_bounded_edit=allow_bounded_edit,
                    ),
                    role="CONTEXT",
                )
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
                "anchor_ids": owner_ids,
                "group_id": "FAMILY12_OWNER_SEED",
                "mode": "ANY",
                "page_relation": "SAME_PAGE",
                "priority": 2,
            },
            {
                "anchor_ids": branch_ids,
                "group_id": "FAMILY12_SHORT_BRANCH_SEED",
                "mode": "ANY",
                "page_relation": "SAME_PAGE",
                "priority": 1,
            },
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
        "branch_components": canonical_clone_v1(spec["branch_components"]),
        "context_classes": [
            {
                "aliases": canonical_clone_v1(item["aliases"]),
                "allow_token_subsequence_fence": item.get("allow_token_subsequence_fence", False),
                "context_id": item["context_id"],
                "disposition": item["disposition"],
            }
            for item in spec["context_classes"]
        ],
        "family_id": FAMILY_ID,
        "format_version": SEMANTIC_SPEC_FORMAT_VERSION,
        "limits": {
            "branch_line_span": spec["limits"]["branch_line_span"],
            "context_line_span": spec["limits"]["context_line_span"],
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
            "enforcement": ScopedTableEnforcementV1.ADVISORY_CHALLENGER.value,
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
        "structural_reset_component_aliases": canonical_clone_v1(
            spec["structural_reset_component_aliases"]
        ),
    }


def _branchless_scoped_spec(
    family_spec: Mapping[str, Any], semantic_spec: Mapping[str, Any]
) -> dict[str, Any]:
    owner = next(
        item for item in family_spec["context_classes"] if item["context_id"] == "OWNER_716"
    )
    scoped = semantic_spec["scoped_table"]
    return {
        "continuation_aliases": scoped["continuation_aliases"],
        "family_id": FAMILY_ID + "_BRANCHLESS_RESCUE",
        "format_version": SCOPED_TABLE_SPEC_FORMAT_VERSION,
        "layout_modes": ["ROLES_AS_ROWS"],
        "limits": {**scoped["limits"], "continuation_page_budget": 0},
        "owner_aliases": owner["aliases"],
        "require_trailing_total_for_roles_as_columns": False,
        "role_axis": [
            {
                "aliases": child["aliases"],
                "role": _semantic_id(child["report_norm_id"]),
            }
            for child in family_spec["children"]
        ],
        "scope_axis": [
            {
                "aliases": family_spec["branch_aliases"],
                "disposition": "TARGET",
                "lane_component_groups": [
                    {
                        "aliases": component["aliases"],
                        "component_id": component["component_id"],
                        "source": (
                            "LEAF"
                            if component["component_id"] == "BRANCH_LOAI_HINH_DOANH_NGHIEP"
                            else "PATH"
                        ),
                    }
                    for component in family_spec["branch_components"]
                ],
                "scope_id": "FAMILY12_EXPLICIT_BRANCH",
            },
            {
                "aliases": [
                    alias
                    for context in family_spec["context_classes"]
                    if context["disposition"] == "HARD_VETO"
                    for alias in context["aliases"]
                ],
                "disposition": "HARD_VETO_MIXED",
                "scope_id": "NON_FAMILY12_CONTEXT",
            },
        ],
        "structural_reset_aliases": family_spec["structural_reset_aliases"],
        "target_scope_id": "FAMILY12_EXPLICIT_BRANCH",
        "trailing_total_aliases": [],
    }


def _reset_fenced_page_intervals(
    region_pages: Sequence[Mapping[str, Any]], semantic_spec: Mapping[str, Any]
) -> list[dict[str, Any]]:
    pages = semantic_region_v1._pages(region_pages)
    parsed_spec = semantic_region_v1._spec(semantic_spec)
    plans, _comparisons, _metrics = semantic_region_v1._context_event_plan(pages, parsed_spec)
    intervals = []
    for page, plan in zip(pages, plans, strict=True):
        fences = sorted(
            (event for event in plan["events"] if event["disposition"] == "HARD_VETO"),
            key=lambda item: (item["start"], item["stop"], item["context_event_id"]),
        )
        cursor = 0
        preceding_fence_id = None
        for fence in [*fences, None]:
            stop = len(page["lines"]) if fence is None else fence["start"]
            if cursor < stop:
                intervals.append(
                    {
                        "following_fence_event_id": (
                            None if fence is None else fence["context_event_id"]
                        ),
                        "page": {**page, "lines": page["lines"][cursor:stop]},
                        "preceding_fence_event_id": preceding_fence_id,
                    }
                )
            if fence is not None:
                cursor = max(cursor, fence["stop"])
                preceding_fence_id = fence["context_event_id"]
    return intervals


def _compact_branchless_match(match: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: canonical_clone_v1(match[key])
        for key in (
            "bbox",
            "match_id",
            "page_sequence",
            "semantic_id",
            "source_line_indices_in_visual_order",
            "surface_raw_nfc",
        )
    }


def _branch_inside_scoped_structure(
    evidence: Mapping[str, Any],
    explicit_branch_indices_by_page: Mapping[int, set[int]],
) -> bool:
    """Reject the branchful table itself without hiding a separate table."""

    page_sequence = evidence["page_sequence"]
    branch_indices = explicit_branch_indices_by_page.get(page_sequence, set())
    if not branch_indices:
        return False
    owner_indices = [
        index
        for match in evidence["owner_matches"]
        if match["page_sequence"] == page_sequence
        for index in match["source_line_indices_in_visual_order"]
    ]
    role_indices = [
        index
        for match in evidence["role_matches"]
        if match["page_sequence"] == page_sequence
        for index in match["source_line_indices_in_visual_order"]
    ]
    if not owner_indices or not role_indices:
        return False
    first_role = min(role_indices)
    preceding_owners = [index for index in owner_indices if index <= first_role]
    if not preceding_owners:
        return False
    closest_owner = max(preceding_owners)
    return any(closest_owner <= index <= max(role_indices) for index in branch_indices)


def _branchless_rescue_challengers(
    region_pages: Sequence[Mapping[str, Any]],
    family_spec: Mapping[str, Any],
    semantic_spec: Mapping[str, Any],
    *,
    explicit_branch_indices_by_page: Mapping[int, set[int]],
    source_page_evidence_sha256: str,
) -> list[dict[str, Any]]:
    scoped_spec = _branchless_scoped_spec(family_spec, semantic_spec)
    child_ids = {
        _semantic_id(child["report_norm_id"]): child["report_norm_id"]
        for child in family_spec["children"]
    }
    challengers = []
    for interval in _reset_fenced_page_intervals(region_pages, semantic_spec):
        try:
            scoped = build_accounting_scoped_table_graph_v1([interval["page"]], scoped_spec)
        except AccountingScopedTableGraphV1Error as error:
            raise _error(str(error)) from error
        evidence = []
        for fragment in scoped["unresolved_fragments"]:
            owner_matches = fragment.get("owner_matches")
            if type(owner_matches) is not list:
                owner = fragment.get("owner")
                owner_matches = [owner] if type(owner) is dict else []
            role_matches = fragment.get("role_matches")
            evidence_id = fragment.get("unresolved_fragment_id") or fragment.get(
                "partial_fragment_id"
            )
            if (
                not owner_matches
                or any(owner.get("semantic_id") != "OWNER" for owner in owner_matches)
                or type(role_matches) is not list
                or type(evidence_id) is not str
            ):
                continue
            evidence.append(
                {
                    "evidence_id": evidence_id,
                    "evidence_kind": "UNRESOLVED_FRAGMENT",
                    "graph_ids": [],
                    "owner_matches": owner_matches,
                    "page_sequence": fragment["page_sequence"],
                    "role_matches": role_matches,
                    "status": "BRANCHLESS_OWNER_MULTIROLE_SCOPED_UNRESOLVED_EVIDENCE",
                }
            )
        evidence.extend(
            {
                "evidence_id": segment["segment_id"],
                "evidence_kind": "PHYSICAL_SEGMENT",
                "graph_ids": sorted(
                    graph["graph_id"]
                    for graph in scoped["graphs"]
                    if any(
                        item["segment_id"] == segment["segment_id"] for item in graph["segments"]
                    )
                ),
                "owner_matches": [segment["owner"]],
                "page_sequence": segment["page_sequences"][0],
                "role_matches": segment["role_matches"],
                "status": "BRANCHLESS_OWNER_MULTIROLE_SCOPE_DERIVED_STRUCTURE",
            }
            for segment in scoped["physical_segments"]
            if segment["owner"].get("semantic_id") == "OWNER"
        )
        for item in evidence:
            if _branch_inside_scoped_structure(item, explicit_branch_indices_by_page):
                continue
            candidate_ids = sorted(
                {
                    child_ids[match["semantic_id"]]
                    for match in item["role_matches"]
                    if match["semantic_id"] in child_ids
                }
            )
            if len(candidate_ids) < 2:
                continue
            material = {
                "candidate_child_report_norm_ids": candidate_ids,
                "disposition": "UNRESOLVED",
                "owner_matches": [
                    _compact_branchless_match(match) for match in item["owner_matches"]
                ],
                "reset_fence": {
                    "following_context_event_id": interval["following_fence_event_id"],
                    "page_sequence": item["page_sequence"],
                    "preceding_context_event_id": interval["preceding_fence_event_id"],
                    "structural_reset_can_be_crossed": scoped["safety"][
                        "structural_reset_can_be_crossed"
                    ],
                },
                "role_matches": [
                    _compact_branchless_match(match) for match in item["role_matches"]
                ],
                "shared_scoped_table_binding": {
                    **canonical_clone_v1(scoped["evidence_binding"]),
                    "evidence_id": item["evidence_id"],
                    "evidence_kind": item["evidence_kind"],
                    "graph_ids": item["graph_ids"],
                    "result_id": scoped["result_id"],
                },
                "source_page_evidence_sha256": source_page_evidence_sha256,
                "status": item["status"],
            }
            challengers.append(
                {
                    **material,
                    "challenger_id": "lef12v1:branchless:" + canonical_json_sha256_v1(material),
                }
            )
    return sorted(challengers, key=lambda item: item["challenger_id"])


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
    projected["schema_parent_report_norm_id"] = (
        children[semantic_id]["schema_parent_report_norm_id"] if semantic_id in children else None
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
            row["schema_parent_report_norm_id"] = None
            row["reason"] = "DUPLICATE_SCHEMA_ROLE_FAIL_CLOSED"
            row["status"] = "DUPLICATE_SCHEMA_ROLE_SOURCE_ONLY_AMBIGUOUS"
        if selected is None:
            continue
        material = {
            "evidence_proposal_id": selected["proposal_id"],
            "foreign_branch_or_subsidiary_component": _foreign_component(selected),
            "report_norm_id": report_norm_id,
            "schema_parent_report_norm_id": selected["schema_parent_report_norm_id"],
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
    body_limit_reached: bool | None = None,
    bindings: Sequence[Mapping[str, Any]] = (),
    geometry: Mapping[str, Any] | None = None,
    minimal_anchor_resolution: Mapping[str, Any] | None = None,
    promotion_eligible: bool | None = None,
    rows: Sequence[Mapping[str, Any]] = (),
    shared_scoped_table: Mapping[str, Any] | None = None,
    topology_candidate_id: str | None = None,
) -> dict[str, Any]:
    material = {
        "body_limit_reached": body_limit_reached,
        "branch": canonical_clone_v1(branch),
        "disposition": "UNRESOLVED",
        "minimal_unique_anchor_resolution_v1": (
            canonical_clone_v1(minimal_anchor_resolution)
            if minimal_anchor_resolution is not None
            else None
        ),
        "owner_context": canonical_clone_v1(owner),
        "promotion_eligible": promotion_eligible,
        "reason": _project_reason(reason),
        "shared_scoped_table_v1": (
            canonical_clone_v1(shared_scoped_table) if shared_scoped_table is not None else None
        ),
        "source_only_geometry_proposal": (
            canonical_clone_v1(geometry) if geometry is not None else None
        ),
        "source_only_binding_proposals": canonical_clone_v1(list(bindings)),
        "source_only_row_proposals": canonical_clone_v1(list(rows)),
        "status": "SOURCE_ONLY_NEAR_REGION_FAIL_CLOSED",
        "topology_candidate_id": topology_candidate_id,
    }
    return {**material, "near_region_id": "lef12v1:near:" + canonical_json_sha256_v1(material)}


_TOPOLOGY_PARENT_ANCHOR_ID = "PARENT_RNID_766"


def _topology_child_anchor_id(report_norm_id: int) -> str:
    return f"CHILD_RNID_{report_norm_id}"


def _topology_candidate_id(disposition: str, material: Mapping[str, Any]) -> str:
    return f"lef12v1:topology_{disposition.casefold()}:" + canonical_json_sha256_v1(material)


def _near_topology_child_anchor_ids(near: Mapping[str, Any]) -> list[str]:
    report_norm_ids = set()
    for row in near["source_only_row_proposals"]:
        report_norm_id = row["report_norm_id"]
        if type(report_norm_id) is int:
            report_norm_ids.add(report_norm_id)
            continue
        candidates = row["candidate_report_norm_ids"]
        if row["status"] == "DUPLICATE_SCHEMA_ROLE_SOURCE_ONLY_AMBIGUOUS" and len(candidates) == 1:
            report_norm_ids.add(candidates[0])
    return [_topology_child_anchor_id(item) for item in sorted(report_norm_ids)]


def _near_topology_parent_anchor_id(near: Mapping[str, Any]) -> str | None:
    owner = near["owner_context"]
    if (
        owner.get("disposition") == "EXPLICIT_OWNER_CONTEXT_ACCEPTED_FOR_PROPOSAL"
        and owner.get("report_norm_id") == PARENT_REPORT_NORM_ID
    ):
        return _TOPOLOGY_PARENT_ANCHOR_ID
    return None


def _attach_near_topology_resolution(
    near: Mapping[str, Any],
    resolution: Mapping[str, Any],
    topology_candidate_id: str | None,
) -> dict[str, Any]:
    material = canonical_clone_v1(near)
    material.pop("near_region_id")
    material["minimal_unique_anchor_resolution_v1"] = canonical_clone_v1(resolution)
    material["topology_candidate_id"] = topology_candidate_id
    return {**material, "near_region_id": "lef12v1:near:" + canonical_json_sha256_v1(material)}


def _anchorless_near_resolution() -> dict[str, Any]:
    return {
        "best_nonunique_anchor_ids": [],
        "candidate_anchor_ids": [],
        "matching_candidate_ids": [],
        "matching_count": 0,
        "parent_child_pairs_precede_child_child_pairs": True,
        "pair_combinations_exhausted_before_triples": True,
        "searched_pair_count": 0,
        "searched_triple_count": 0,
        "selected_anchor_ids": [],
        "selected_size": None,
        "status": "NOT_RUN_ANCHORLESS_NEAR_CANDIDATE",
    }


def _build(region_pages: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    family_spec = build_loan_enterprise_family12_spec_v1()
    semantic_spec = _generic_spec(family_spec)
    try:
        semantic_result = build_accounting_semantic_region_graph_v1(region_pages, semantic_spec)
    except AccountingSemanticRegionGraphV1Error as error:
        raise _error(str(error)) from error
    children = _semantic_to_child(family_spec)
    context_ids = _context_to_report_ids(family_spec)
    explicit_branch_indices_by_page: dict[int, set[int]] = {}
    for candidate in [*semantic_result["regions"], *semantic_result["near_regions"]]:
        for item in candidate["branch"]["evidence"]:
            explicit_branch_indices_by_page.setdefault(item["page_sequence"], set()).add(
                item["source_line_index"]
            )
    branchless_rescue_challengers = _branchless_rescue_challengers(
        region_pages,
        family_spec,
        semantic_spec,
        explicit_branch_indices_by_page=explicit_branch_indices_by_page,
        source_page_evidence_sha256=semantic_result["evidence_binding"][
            "canonical_page_evidence_sha256"
        ],
    )
    pending_regions = []
    near_regions = []
    for near in semantic_result["near_regions"]:
        rows = [_project_row(row, children) for row in near["source_only_row_proposals"]]
        near_regions.append(
            _near_region(
                branch=near["branch"],
                owner=_project_owner(near["owner_context"], context_ids),
                reason=near["reason"],
                body_limit_reached=near["body_limit_reached"],
                geometry=near["source_only_geometry_proposal"],
                rows=rows,
            )
        )
    for semantic_region in semantic_result["regions"]:
        owner = _project_owner(semantic_region["owner_context"], context_ids)
        rows = [_project_row(row, children) for row in semantic_region["row_proposals"]]
        bindings = _unique_bindings(rows, promotion_eligible=semantic_region["promotion_eligible"])
        if not bindings:
            shared = semantic_region["shared_scoped_table_v1"]
            if semantic_region["body_limit_reached"]:
                reason = "SEMANTIC_REGION_BODY_LIMIT_REACHED"
            elif (
                not semantic_region["promotion_eligible"]
                and shared["status"] == "SHARED_SCOPED_TABLE_FAIL_CLOSED"
            ):
                reason = shared["reason"]
            else:
                reason = "NO_UNIQUE_SCHEMA_ROW_WITH_VALUE_GEOMETRY"
            near_regions.append(
                _near_region(
                    branch=semantic_region["branch"],
                    owner=owner,
                    reason=reason,
                    body_limit_reached=semantic_region["body_limit_reached"],
                    geometry=semantic_region["adaptive_geometry_v2"],
                    promotion_eligible=semantic_region["promotion_eligible"],
                    rows=rows,
                    shared_scoped_table=shared,
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
        pending_regions.append(
            {
                **material,
                "topology_candidate_id": _topology_candidate_id("COMPLETE", material),
            }
        )
    topology_candidates = [
        {
            "candidate_id": item["topology_candidate_id"],
            "child_anchor_ids": [
                _topology_child_anchor_id(binding["report_norm_id"])
                for binding in item["binding_proposals"]
            ],
            "disposition": "COMPLETE",
            "parent_anchor_id": _TOPOLOGY_PARENT_ANCHOR_ID,
        }
        for item in pending_regions
    ]
    for near in near_regions:
        child_anchor_ids = _near_topology_child_anchor_ids(near)
        parent_anchor_id = _near_topology_parent_anchor_id(near)
        if parent_anchor_id is None and not child_anchor_ids:
            continue
        topology_candidate_id = _topology_candidate_id("NEAR", near)
        topology_candidates.append(
            {
                "candidate_id": topology_candidate_id,
                "child_anchor_ids": child_anchor_ids,
                "disposition": "NEAR",
                "parent_anchor_id": parent_anchor_id,
            }
        )
    topology_result = None
    topology_resolution_by_id = {}
    if topology_candidates:
        topology_result = build_accounting_minimal_unique_anchor_resolution_v1(
            topology_candidates,
            document_scope_id=(
                "SEMANTIC_PAGE_EVIDENCE_"
                + semantic_result["evidence_binding"]["canonical_page_evidence_sha256"]
            ),
        )
        topology_resolution_by_id = {
            item["candidate_id"]: item["resolution"] for item in topology_result["candidates"]
        }
    attached_near_regions = []
    for near in near_regions:
        if _near_topology_parent_anchor_id(near) is None and not _near_topology_child_anchor_ids(
            near
        ):
            attached_near_regions.append(
                _attach_near_topology_resolution(near, _anchorless_near_resolution(), None)
            )
            continue
        topology_candidate_id = _topology_candidate_id("NEAR", near)
        attached_near_regions.append(
            _attach_near_topology_resolution(
                near,
                topology_resolution_by_id[topology_candidate_id],
                topology_candidate_id,
            )
        )
    near_regions = attached_near_regions
    regions = []
    for pending in pending_regions:
        topology_candidate_id = pending["topology_candidate_id"]
        resolution = topology_resolution_by_id[topology_candidate_id]
        if resolution["status"] != "UNIQUE_MINIMAL_ANCHOR_COMBINATION":
            near_regions.append(
                _near_region(
                    branch=pending["branch"],
                    owner=pending["owner_context"],
                    reason=resolution["status"],
                    body_limit_reached=False,
                    bindings=pending["binding_proposals"],
                    geometry=pending["adaptive_geometry_v2"],
                    minimal_anchor_resolution=resolution,
                    promotion_eligible=True,
                    rows=pending["row_proposals"],
                    shared_scoped_table=pending["shared_scoped_table_v1"],
                    topology_candidate_id=topology_candidate_id,
                )
            )
            continue
        material = {
            **pending,
            "minimal_unique_anchor_resolution_v1": canonical_clone_v1(resolution),
        }
        regions.append(
            {**material, "region_id": "lef12v1:region:" + canonical_json_sha256_v1(material)}
        )
    bounded_absences = []
    if (
        semantic_result["metrics"]["branch_candidate_count"] == 0
        and not branchless_rescue_challengers
    ):
        bounded_absences.append(
            {
                "page_sequences": semantic_result["bounded_absences"][0]["page_sequences"],
                "reason": "NO_FAMILY12_BRANCH_IN_CALLER_BOUNDED_PAGES",
                "status": "BOUNDED_ABSENCE_NO_GLOBAL_CORPUS_CLAIM",
            }
        )
    metrics = {
        "approximate_alias_comparison_count": semantic_result["matcher_metrics"][
            "approximate_alias_comparison_count"
        ],
        "bounded_absence_count": len(bounded_absences),
        "branchless_rescue_challenger_count": len(branchless_rescue_challengers),
        "branch_candidate_count": semantic_result["metrics"]["branch_candidate_count"],
        "branch_component_fallback_candidate_count": semantic_result["metrics"][
            "branch_component_fallback_candidate_count"
        ],
        "cross_page_owner_region_count": sum(
            item["owner_context"]["page_distance"] > 0 for item in regions
        ),
        "context_event_count": semantic_result["metrics"]["context_event_count"],
        "context_event_wrapped_count": semantic_result["metrics"]["context_event_wrapped_count"],
        "region_count": len(regions),
        "minimal_anchor_collision_demoted_region_count": len(pending_regions) - len(regions),
        "minimal_anchor_anchorless_near_region_count": sum(
            item["topology_candidate_id"] is None for item in near_regions
        ),
        "minimal_anchor_topology_candidate_count": len(topology_candidates),
        "minimal_anchor_unique_complete_region_count": len(regions),
        "scoped_table_advisory_failure_region_count": semantic_result["metrics"][
            "scoped_table_advisory_failure_region_count"
        ],
        "scoped_table_required_failure_region_count": semantic_result["metrics"][
            "scoped_table_required_failure_region_count"
        ],
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
        "unresolved_region_count": len(near_regions) + len(branchless_rescue_challengers),
    }
    safety = canonical_clone_v1(family_spec["safety"])
    safety.update(
        {
            "authenticated_store_or_full_corpus_used": False,
            "branchless_owner_multirole_can_veto_bounded_absence": True,
            "branchless_rescue_grants_mapping_authority": False,
            "branchless_rescue_is_source_and_reset_fenced": True,
            "gemma_or_other_model_authority": False,
            "historical_evidence_metadata_used_for_matching": False,
            "minimal_unique_anchor_resolution_grants_mapping_authority": False,
            "minimal_unique_pair_or_triple_required_for_complete_region": True,
            "parent_child_anchor_pairs_precede_child_child_pairs": True,
            "topology_bearing_near_candidates_participate_in_collision_resolution": True,
            "owner_branch_and_child_value_geometry_required_for_binding_proposal": True,
            "single_branch_component_can_create_binding_proposal": False,
            "shared_geometry_or_scoped_graph_grants_mapping_authority": False,
            "shared_semantic_region_failure_can_promote_mapping": False,
            "source_only_near_region_is_bounded_absence": False,
            "two_role_table_without_owner_716_can_accept": False,
        }
    )
    material = {
        "bounded_absences": bounded_absences,
        "branchless_rescue_challengers": branchless_rescue_challengers,
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
        "minimal_unique_anchor_resolution_v1": topology_result,
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
            "FAMILY12_PROPOSAL_ENUMERATION_WITH_UNRESOLVED_REGIONS"
            if near_regions or branchless_rescue_challengers
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
        "branchless_rescue_challenger_count": sum(
            item["branchless_rescue_challenger_count"] for item in graph_metrics
        ),
        "branch_component_fallback_candidate_count": sum(
            item["branch_component_fallback_candidate_count"] for item in graph_metrics
        ),
        "cross_page_owner_region_count": sum(
            item["cross_page_owner_region_count"] for item in graph_metrics
        ),
        "context_event_count": sum(item["context_event_count"] for item in graph_metrics),
        "context_event_wrapped_count": sum(
            item["context_event_wrapped_count"] for item in graph_metrics
        ),
        "document_count": len(documents),
        "fallback_document_count": receipt_metrics["fallback_document_count"],
        "indexed_document_count": (len(documents) - receipt_metrics["fallback_document_count"]),
        "line_count": sum(item["line_count"] for item in projection_metrics),
        "near_region_count": sum(len(document["graph"]["near_regions"]) for document in documents),
        "minimal_anchor_collision_demoted_region_count": sum(
            item["minimal_anchor_collision_demoted_region_count"] for item in graph_metrics
        ),
        "minimal_anchor_anchorless_near_region_count": sum(
            item["minimal_anchor_anchorless_near_region_count"] for item in graph_metrics
        ),
        "minimal_anchor_topology_candidate_count": sum(
            item["minimal_anchor_topology_candidate_count"] for item in graph_metrics
        ),
        "minimal_anchor_unique_complete_region_count": sum(
            item["minimal_anchor_unique_complete_region_count"] for item in graph_metrics
        ),
        "page_count": sum(item["page_count"] for item in projection_metrics),
        "region_count": sum(item["region_count"] for item in graph_metrics),
        "scoped_table_advisory_failure_region_count": sum(
            item["scoped_table_advisory_failure_region_count"] for item in graph_metrics
        ),
        "scoped_table_required_failure_region_count": sum(
            item["scoped_table_required_failure_region_count"] for item in graph_metrics
        ),
        "source_only_ambiguous_row_count": sum(
            item["source_only_ambiguous_row_count"] for item in graph_metrics
        ),
        "unique_binding_proposal_count": sum(
            item["unique_binding_proposal_count"] for item in graph_metrics
        ),
        "unresolved_region_count": sum(item["unresolved_region_count"] for item in graph_metrics),
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
