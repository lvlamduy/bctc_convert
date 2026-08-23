"""Thin Family 11 adapter over the generic scoped accounting-table graph.

The shared graph owns text matching and table geometry.  This module owns only
the Family 11 vocabulary, authenticated selected-page projection, whole-
document uniqueness, and graph-neutral projections needed by the pixel and
numeric evidence stages.  Retrieval remains a shortlist: it cannot assign an
anchor's semantic role or establish an absence without this adapter.

No bank, filename, page number, reporting year, schema ID, or numeric value is
used to discover or classify a table.  Historical aliases are closed,
classified provenance below; every alias in the executable spec is asserted
to have exactly one provenance record.
"""

from __future__ import annotations

import hashlib
import stat
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.accounting_scoped_table_graph_v1 import (
    SPEC_FORMAT_VERSION,
    build_accounting_scoped_table_graph_v1,
    validate_accounting_scoped_table_graph_replay_v1,
)
from bctc_ai.evaluation.accounting_table_axes_v1 import (
    infer_document_accounting_unit_context_v1,
    infer_document_reporting_period_context_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "DOCUMENT_FORMAT_VERSION",
    "DOCUMENT_CONTEXT_FORMAT_VERSION",
    "FORMAT_VERSION",
    "FAMILY_ID",
    "LOAN_GEOGRAPHY_REGION_QUERY_SPEC_V2",
    "LOAN_GEOGRAPHY_SCOPED_TABLE_ALIAS_PROVENANCE_V1",
    "LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1",
    "LoanGeographyScopedTableAdapterV1Error",
    "build_loan_geography_scoped_graphs_v1",
    "build_loan_geography_document_context_v1",
    "build_loan_geography_region_query_spec_v2",
    "build_loan_geography_whole_document_scoped_graph_v1",
    "compare_loan_geography_sparse_full_graphs_v1",
    "project_loan_geography_numeric_input_v1",
    "project_loan_geography_visible_dash_graph_v1",
    "validate_loan_geography_document_context_replay_v1",
    "validate_loan_geography_scoped_graphs_replay_v1",
    "validate_loan_geography_whole_document_scoped_graph_replay_v1",
]


FAMILY_ID = "LOAN_GEOGRAPHIC_CLASSIFICATION"
FORMAT_VERSION = "LOAN_GEOGRAPHY_SCOPED_GRAPH_BATCH_V1"
DOCUMENT_FORMAT_VERSION = "LOAN_GEOGRAPHY_SCOPED_GRAPH_DOCUMENT_V1"
OVERLAY_FORMAT_VERSION = "LOAN_GEOGRAPHY_SCOPED_GRAPH_OVERLAY_PROJECTION_V1"
DOCUMENT_CONTEXT_FORMAT_VERSION = "LOAN_GEOGRAPHY_DOCUMENT_PERIOD_UNIT_CONTEXT_V1"
CLAIM_BOUNDARY = (
    "AUTHENTICATED_REGION_LOCAL_SHARED_SCOPED_TABLE_GRAPH_FAMILY11_SEMANTIC_"
    "ANCHOR_ASSIGNMENT_DOCUMENT_UNIQUENESS_AND_TYPED_PROJECTION_ONLY_NO_"
    "RETRIEVAL_ABSENCE_NUMERIC_ACCOUNTING_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "accounting_or_numeric_authority": False,
    "alias_provenance_is_closed_and_content_addressed": True,
    "bank_filename_page_year_or_schema_used_for_matching_or_routing": False,
    "broad_or_mixed_population_can_be_narrowed": False,
    "gemma_request_count": 0,
    "partial_semantic_candidate_is_terminal_without_shared_geometry_replay": False,
    "raw_ppocrv6_and_vietocr_surfaces_retained": True,
    "receipt_or_snapshot_self_authenticating": False,
    "retrieval_assigns_semantic_anchor_roles": False,
    "retrieval_is_mapping_or_absence_authority": False,
    "whole_document_uniqueness_required_before_release": True,
}
_TERMINAL_GRAPH_STATUS = "STRUCTURALLY_ACCEPTED_NO_NUMERIC_OR_MAPPING_AUTHORITY"
_PARTIAL_NONTERMINAL_STATUS = "SEMANTIC_AXIS_CANDIDATE_REQUIRES_SHARED_ADJACENT_GEOMETRY_REPLAY"
_DISPOSITIONS = {
    "BROAD_POPULATION_BOUNDED_ABSENCE",
    "EXACT_CUSTOMER_LOAN_GEOGRAPHY",
    "NOT_OBSERVED",
    "UNRESOLVED",
}


class LoanGeographyScopedTableAdapterV1Error(ValueError):
    """The Family 11 spec, receipt, snapshot, projection, or replay drifted."""


def _error(message: str) -> LoanGeographyScopedTableAdapterV1Error:
    return LoanGeographyScopedTableAdapterV1Error(message)


# ``CANONICAL`` means the accounting wording itself is canonical.  A
# ``VERIFIED_HISTORICAL_VARIANT`` is admitted only as an OCR/presentation
# surface and does not redefine the canonical role.  The reference is a
# stable, human-auditable classification label; retrieval support references
# remain in its own query-spec contract.
LOAN_GEOGRAPHY_SCOPED_TABLE_ALIAS_PROVENANCE_V1 = {
    "CONTINUATION": [
        {
            "kind": "CANONICAL",
            "surface": "Tiếp theo",
            "verification_ref": "F11:CONTINUATION:CANONICAL",
        },
    ],
    "DOMESTIC_TOTAL": [
        {
            "kind": "CANONICAL",
            "surface": "Trong nước",
            "verification_ref": "F11:DOMESTIC:CANONICAL",
        },
    ],
    "EXACT_CUSTOMER_LOANS": [
        {
            "kind": "CANONICAL",
            "surface": "Cho vay khách hàng",
            "verification_ref": "F11:SCOPE:CUSTOMER_LOANS",
        },
        {
            "kind": "CANONICAL",
            "surface": "Vay khách hàng",
            "verification_ref": "F11:SCOPE:ELLIPTIC_CUSTOMER_LOANS",
        },
    ],
    "FOREIGN_TOTAL": [
        {"kind": "CANONICAL", "surface": "Nước ngoài", "verification_ref": "F11:FOREIGN:CANONICAL"},
    ],
    "GEOGRAPHIC_CONCENTRATION_OWNER": [
        {
            "kind": "CANONICAL",
            "surface": "Mức độ tập trung của tài sản, công nợ và các khoản mục ngoại bảng theo khu vực địa lý",
            "verification_ref": "F11:OWNER:ASSET_LIABILITY_OFF_BALANCE_GEOGRAPHY",
        },
        {
            "kind": "CANONICAL",
            "surface": "Mức độ tập trung của tài sản, nợ phải trả và các cam kết ngoại bảng theo khu vực địa lý",
            "verification_ref": "F11:OWNER:ASSET_PAYABLE_COMMITMENT_GEOGRAPHY",
        },
        {
            "kind": "CANONICAL",
            "surface": "Mức độ tập trung tài sản và công nợ theo khu vực địa lý",
            "verification_ref": "F11:OWNER:COMPACT_GEOGRAPHY",
        },
        {
            "kind": "CANONICAL",
            "surface": "Mức độ tập trung của tài sản, công nợ và các khoản mục ngoại bảng theo vùng",
            "verification_ref": "F11:OWNER:GEOGRAPHIC_REGION_WORDING",
        },
    ],
    "OWNER_ACCOUNTING_CONTEXT": [
        {
            "kind": "CANONICAL",
            "surface": "Tài sản",
            "verification_ref": "F11:OWNER_COMPONENT:ASSET",
        },
        {
            "kind": "CANONICAL",
            "surface": "Công nợ",
            "verification_ref": "F11:OWNER_COMPONENT:LIABILITY",
        },
        {
            "kind": "CANONICAL",
            "surface": "Nợ phải trả",
            "verification_ref": "F11:OWNER_COMPONENT:PAYABLE",
        },
        {
            "kind": "CANONICAL",
            "surface": "Khoản mục ngoại bảng",
            "verification_ref": "F11:OWNER_COMPONENT:OFF_BALANCE_ITEM",
        },
        {
            "kind": "CANONICAL",
            "surface": "Cam kết ngoại bảng",
            "verification_ref": "F11:OWNER_COMPONENT:OFF_BALANCE_COMMITMENT",
        },
    ],
    "OWNER_CONCENTRATION": [
        {
            "kind": "CANONICAL",
            "surface": "Mức độ tập trung",
            "verification_ref": "F11:OWNER_COMPONENT:CONCENTRATION",
        },
        {
            "kind": "CANONICAL",
            "surface": "Tập trung",
            "verification_ref": "F11:OWNER_COMPONENT:CONCENTRATION_ELLIPTIC",
        },
    ],
    "OWNER_GEOGRAPHY": [
        {
            "kind": "CANONICAL",
            "surface": "Khu vực địa lý",
            "verification_ref": "F11:OWNER_COMPONENT:GEOGRAPHIC_AREA",
        },
        {
            "kind": "CANONICAL",
            "surface": "Theo vùng",
            "verification_ref": "F11:OWNER_COMPONENT:REGION",
        },
    ],
    "MIXED_CUSTOMER_LOAN_SIGNAL": [
        {
            "kind": "CANONICAL",
            "surface": "Cho vay khách hàng",
            "verification_ref": "F11:MIXED_COMPONENT:CUSTOMER_LOANS",
        },
        {
            "kind": "CANONICAL",
            "surface": "Vay khách hàng",
            "verification_ref": "F11:MIXED_COMPONENT:ELLIPTIC_CUSTOMER_LOANS",
        },
    ],
    "CUSTOMER_LOAN_LANE_ACTIVITY": [
        {
            "kind": "CANONICAL",
            "surface": "Cho vay",
            "verification_ref": "F11:LANE_COMPONENT:CUSTOMER_LOAN_ACTIVITY",
        },
        {
            "kind": "CANONICAL",
            "surface": "Dư nợ",
            "verification_ref": "F11:LANE_COMPONENT:LOAN_BALANCE_ACTIVITY",
        },
        {
            "kind": "CANONICAL",
            "surface": "Nợ cho vay",
            "verification_ref": "F11:LANE_COMPONENT:LOAN_DEBT_ACTIVITY",
        },
    ],
    "CUSTOMER_LOAN_LANE_LEAF": [
        {
            "kind": "CANONICAL",
            "surface": "Khách hàng",
            "verification_ref": "F11:LANE_COMPONENT:CUSTOMER_LEAF",
        },
    ],
    "MIXED_LOAN_LANE_ACTIVITY": [
        {
            "kind": "CANONICAL",
            "surface": "Cho vay",
            "verification_ref": "F11:MIXED_LANE_COMPONENT:LOAN_ACTIVITY",
        },
        {
            "kind": "CANONICAL",
            "surface": "Dư nợ",
            "verification_ref": "F11:MIXED_LANE_COMPONENT:LOAN_BALANCE_ACTIVITY",
        },
        {
            "kind": "CANONICAL",
            "surface": "Nợ cho vay",
            "verification_ref": "F11:MIXED_LANE_COMPONENT:LOAN_DEBT_ACTIVITY",
        },
    ],
    "MIXED_POPULATION_LANE_LEAF": [
        {
            "kind": "CANONICAL",
            "surface": "TCTD",
            "verification_ref": "F11:MIXED_LANE_COMPONENT:CREDIT_INSTITUTION_ABBREVIATION",
        },
        {
            "kind": "CANONICAL",
            "surface": "Tổ chức tín dụng",
            "verification_ref": "F11:MIXED_LANE_COMPONENT:CREDIT_INSTITUTION",
        },
        {
            "kind": "CANONICAL",
            "surface": "Mua nợ",
            "verification_ref": "F11:MIXED_LANE_COMPONENT:DEBT_PURCHASE",
        },
        {
            "kind": "CANONICAL",
            "surface": "Vay tại NHNN",
            "verification_ref": "F11:MIXED_LANE_COMPONENT:CENTRAL_BANK_BORROWING",
        },
    ],
    "MIXED_POPULATION_MARKER": [
        {
            "kind": "CANONICAL",
            "surface": "TCTD",
            "verification_ref": "F11:MIXED_COMPONENT:CREDIT_INSTITUTION_ABBREVIATION",
        },
        {
            "kind": "CANONICAL",
            "surface": "Tổ chức tín dụng",
            "verification_ref": "F11:MIXED_COMPONENT:CREDIT_INSTITUTION",
        },
        {
            "kind": "CANONICAL",
            "surface": "Mua nợ",
            "verification_ref": "F11:MIXED_COMPONENT:DEBT_PURCHASE",
        },
        {
            "kind": "CANONICAL",
            "surface": "Cấp tín dụng",
            "verification_ref": "F11:MIXED_COMPONENT:CREDIT_EXTENSION",
        },
        {
            "kind": "CANONICAL",
            "surface": "Vay tại NHNN",
            "verification_ref": "F11:MIXED_COMPONENT:CENTRAL_BANK_BORROWING",
        },
    ],
    "BROAD_MIXED_LOAN_POPULATION": [
        {
            "kind": "CANONICAL",
            "surface": "Cho vay khách hàng và các TCTD",
            "verification_ref": "F11:SCOPE:MIXED_CUSTOMERS_CREDIT_INSTITUTIONS",
        },
        {
            "kind": "CANONICAL",
            "surface": "Tổng dư nợ cho vay khách hàng, mua nợ và cấp tín dụng cho các TCTD khác",
            "verification_ref": "F11:SCOPE:MIXED_LOAN_PURCHASE_CREDIT",
        },
        {
            "kind": "CANONICAL",
            "surface": "Cho vay khách hàng, mua nợ và cấp tín dụng",
            "verification_ref": "F11:SCOPE:MIXED_CUSTOMER_PURCHASE_CREDIT",
        },
    ],
    "BROAD_TOTAL_LOANS": [
        {
            "kind": "CANONICAL",
            "surface": "Tổng dư nợ cho vay",
            "verification_ref": "F11:SCOPE:TOTAL_LOAN_BALANCE",
        },
        {
            "kind": "CANONICAL",
            "surface": "Tổng dư nợ",
            "verification_ref": "F11:SCOPE:TOTAL_BALANCE",
        },
        {
            "kind": "CANONICAL",
            "surface": "Dư nợ cho vay",
            "verification_ref": "F11:SCOPE:LOAN_BALANCE",
        },
    ],
    "STRUCTURAL_RESET": [
        {
            "kind": "CANONICAL",
            "surface": "Báo cáo bộ phận theo khu vực địa lý",
            "verification_ref": "F11:RESET:SEGMENT_REPORT",
        },
        {
            "kind": "CANONICAL",
            "surface": "Báo cáo bộ phận chính yếu theo khu vực địa lý",
            "verification_ref": "F11:RESET:PRIMARY_SEGMENT_REPORT",
        },
        {
            "kind": "CANONICAL",
            "surface": "Thuyết minh khác",
            "verification_ref": "F11:RESET:NEXT_NOTE",
        },
    ],
    "TRAILING_TOTAL": [
        {"kind": "CANONICAL", "surface": "Tổng cộng", "verification_ref": "F11:TOTAL:CANONICAL"},
    ],
}


def _surfaces(key: str) -> list[str]:
    return [item["surface"] for item in LOAN_GEOGRAPHY_SCOPED_TABLE_ALIAS_PROVENANCE_V1[key]]


LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1 = {
    "continuation_aliases": _surfaces("CONTINUATION"),
    "family_id": FAMILY_ID,
    "format_version": SPEC_FORMAT_VERSION,
    "layout_modes": ["ROLES_AS_COLUMNS", "ROLES_AS_ROWS"],
    "limits": {
        "axis_tolerance_ppm": 35_000,
        "continuation_page_budget": 1,
        "max_owner_distance_lines": 18,
        "max_role_gap_lines": 10,
        "max_wrap_lines": 3,
        "minimum_cell_row_overlap_ppm": 250_000,
        "unlabeled_total_gap_jitter_ppm": 200_000,
        "unlabeled_total_max_gap_lines": 2,
        "unlabeled_total_max_numeric_columns": 8,
        "unlabeled_total_min_numeric_columns": 5,
    },
    "owner_aliases": _surfaces("GEOGRAPHIC_CONCENTRATION_OWNER"),
    "owner_component_groups": [
        {"aliases": _surfaces("OWNER_CONCENTRATION"), "component_id": "OWNER_CONCENTRATION"},
        {"aliases": _surfaces("OWNER_GEOGRAPHY"), "component_id": "OWNER_GEOGRAPHY"},
        {
            "aliases": _surfaces("OWNER_ACCOUNTING_CONTEXT"),
            "component_id": "OWNER_ACCOUNTING_CONTEXT",
        },
    ],
    "require_trailing_total_for_roles_as_columns": True,
    "role_axis": [
        {"aliases": _surfaces("DOMESTIC_TOTAL"), "role": "DOMESTIC_TOTAL"},
        {"aliases": _surfaces("FOREIGN_TOTAL"), "role": "FOREIGN_TOTAL"},
    ],
    "scope_axis": [
        {
            "aliases": _surfaces("EXACT_CUSTOMER_LOANS"),
            "disposition": "TARGET",
            "lane_component_groups": [
                {
                    "aliases": _surfaces("CUSTOMER_LOAN_LANE_ACTIVITY"),
                    "component_id": "CUSTOMER_LOAN_LANE_ACTIVITY",
                    "source": "PATH",
                },
                {
                    "aliases": _surfaces("CUSTOMER_LOAN_LANE_LEAF"),
                    "component_id": "CUSTOMER_LOAN_LANE_LEAF",
                    "source": "LEAF",
                },
            ],
            "scope_id": "EXACT_CUSTOMER_LOANS",
        },
        {
            "aliases": _surfaces("BROAD_TOTAL_LOANS"),
            "disposition": "HARD_VETO_BROAD",
            "scope_id": "BROAD_TOTAL_LOANS",
        },
        {
            "aliases": _surfaces("BROAD_MIXED_LOAN_POPULATION"),
            "disposition": "HARD_VETO_MIXED",
            "required_component_groups": [
                {
                    "aliases": _surfaces("MIXED_CUSTOMER_LOAN_SIGNAL"),
                    "component_id": "MIXED_CUSTOMER_LOAN_SIGNAL",
                },
                {
                    "aliases": _surfaces("MIXED_POPULATION_MARKER"),
                    "component_id": "MIXED_POPULATION_MARKER",
                },
            ],
            "lane_component_groups": [
                {
                    "aliases": _surfaces("MIXED_LOAN_LANE_ACTIVITY"),
                    "component_id": "MIXED_LOAN_LANE_ACTIVITY",
                    "source": "PATH",
                },
                {
                    "aliases": _surfaces("MIXED_POPULATION_LANE_LEAF"),
                    "component_id": "MIXED_POPULATION_LANE_LEAF",
                    "source": "LEAF",
                },
            ],
            "scope_id": "BROAD_MIXED_LOAN_POPULATION",
        },
    ],
    "structural_reset_aliases": _surfaces("STRUCTURAL_RESET"),
    "target_scope_id": "EXACT_CUSTOMER_LOANS",
    "trailing_total_aliases": _surfaces("TRAILING_TOTAL"),
}


def _assert_closed_alias_provenance() -> None:
    expected = {
        "CONTINUATION": LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1["continuation_aliases"],
        "GEOGRAPHIC_CONCENTRATION_OWNER": LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1["owner_aliases"],
        **{
            item["component_id"]: item["aliases"]
            for item in LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1["owner_component_groups"]
        },
        "STRUCTURAL_RESET": LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1["structural_reset_aliases"],
        "TRAILING_TOTAL": LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1["trailing_total_aliases"],
        **{
            item["role"]: item["aliases"]
            for item in LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1["role_axis"]
        },
        **{
            item["scope_id"]: item["aliases"]
            for item in LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1["scope_axis"]
        },
        **{
            component["component_id"]: component["aliases"]
            for scope in LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1["scope_axis"]
            for component in scope.get("required_component_groups", [])
        },
        **{
            component["component_id"]: component["aliases"]
            for scope in LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1["scope_axis"]
            for component in scope.get("lane_component_groups", [])
        },
    }
    if set(expected) != set(LOAN_GEOGRAPHY_SCOPED_TABLE_ALIAS_PROVENANCE_V1):
        raise RuntimeError("Family 11 alias provenance semantic axis drifted")
    for semantic_id, surfaces in expected.items():
        records = LOAN_GEOGRAPHY_SCOPED_TABLE_ALIAS_PROVENANCE_V1[semantic_id]
        if (
            [item.get("surface") for item in records] != surfaces
            or any(set(item) != {"kind", "surface", "verification_ref"} for item in records)
            or any(
                item["kind"] not in {"CANONICAL", "VERIFIED_HISTORICAL_VARIANT"} for item in records
            )
            or any(
                type(item["verification_ref"]) is not str or not item["verification_ref"]
                for item in records
            )
        ):
            raise RuntimeError(f"Family 11 alias provenance is not closed: {semantic_id}")


_assert_closed_alias_provenance()
ALIAS_PROVENANCE_ID = "lgstv1:aliases:" + canonical_json_sha256_v1(
    LOAN_GEOGRAPHY_SCOPED_TABLE_ALIAS_PROVENANCE_V1
)
SPEC_ID = "lgstv1:spec:" + canonical_json_sha256_v1(LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1)


def _adapter_content_ref(project_root: Path) -> dict[str, Any]:
    relative = Path("src/bctc_ai/evaluation/loan_geography_scoped_table_adapter_v1.py")
    path = project_root / relative
    before = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(before.st_mode):
        raise _error("Family 11 semantic adapter is not one regular nofollow file")
    payload = path.read_bytes()
    after = path.lstat()
    identity = lambda item: (  # noqa: E731
        item.st_dev,
        item.st_ino,
        item.st_mode,
        item.st_size,
        item.st_mtime_ns,
    )
    if identity(before) != identity(after) or len(payload) != before.st_size:
        raise _error("Family 11 semantic adapter changed during stable read")
    return {
        "path": relative.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _query_spec(project_root: Path) -> dict[str, Any]:
    return {
        "anchors": [
            {
                "anchor_id": "CUSTOMER_LOAN",
                "canonical_alias_id": "CUSTOMER_LOAN_CANONICAL",
                "fts_probes": ["cho vay", "khach hang"],
                "max_edit_distance": 1,
                "role": "TARGET",
                "surface": "Cho vay khách hàng",
                "verified_historical_variants": [],
            },
            {
                "anchor_id": "DOMESTIC",
                "canonical_alias_id": "DOMESTIC_CANONICAL",
                "fts_probes": ["trong nuoc"],
                "max_edit_distance": 1,
                "role": "CONTEXT",
                "surface": "Trong nước",
                "verified_historical_variants": [],
            },
            {
                "anchor_id": "FOREIGN",
                "canonical_alias_id": "FOREIGN_CANONICAL",
                "fts_probes": ["nuoc ngoai"],
                "max_edit_distance": 1,
                "role": "CONTEXT",
                "surface": "Nước ngoài",
                "verified_historical_variants": [],
            },
            {
                "anchor_id": "GEOGRAPHIC_AREA",
                "canonical_alias_id": "GEOGRAPHIC_AREA_CANONICAL",
                "fts_probes": ["khu vuc dia ly"],
                "max_edit_distance": 1,
                "role": "OWNER",
                "surface": "Khu vực địa lý",
                "verified_historical_variants": [],
            },
            {
                "anchor_id": "GEOGRAPHIC_CONCENTRATION",
                "canonical_alias_id": "GEOGRAPHIC_CONCENTRATION_CANONICAL",
                "fts_probes": ["muc do tap trung"],
                "max_edit_distance": 1,
                "role": "OWNER",
                "surface": "Mức độ tập trung",
                "verified_historical_variants": [],
            },
            {
                "anchor_id": "LOAN_BALANCE",
                "canonical_alias_id": "LOAN_BALANCE_CANONICAL",
                "fts_probes": ["du no"],
                "max_edit_distance": 0,
                "role": "TARGET",
                "surface": "Dư nợ",
                "verified_historical_variants": [],
            },
            {
                "anchor_id": "LOAN_GENERIC",
                "canonical_alias_id": "LOAN_GENERIC_CANONICAL",
                "fts_probes": ["cho vay"],
                "max_edit_distance": 0,
                "role": "TARGET",
                "surface": "Cho vay",
                "verified_historical_variants": [],
            },
        ],
        "family_id": FAMILY_ID,
        "format_version": "FAMILY_FIRST_REGION_QUERY_SPEC_V2",
        "local_required_groups": [
            {
                "anchor_ids": ["DOMESTIC", "FOREIGN"],
                "group_id": "GEOGRAPHIC_AXIS",
                "mode": "ALL",
                "page_relation": "SAME_OR_ADJACENT_PAGE",
            },
            {
                "anchor_ids": ["GEOGRAPHIC_AREA", "GEOGRAPHIC_CONCENTRATION"],
                "group_id": "GEOGRAPHIC_OWNER_SCOPE",
                "mode": "ANY",
                "page_relation": "SAME_OR_ADJACENT_PAGE",
            },
            {
                "anchor_ids": ["CUSTOMER_LOAN", "LOAN_BALANCE", "LOAN_GENERIC"],
                "group_id": "LOAN_POPULATION_SCOPE",
                "mode": "ANY",
                "page_relation": "SAME_OR_ADJACENT_PAGE",
            },
        ],
        "max_hit_lines": 100_000,
        "max_selected_pages_per_document": 50,
        "neighbor_pages_after": 1,
        "neighbor_pages_before": 1,
        "seed_groups": [
            {
                "anchor_ids": ["DOMESTIC", "FOREIGN"],
                "group_id": "DOMESTIC_FOREIGN_FALLBACK",
                "mode": "ALL",
                "page_relation": "SAME_OR_ADJACENT_PAGE",
                "priority": 2,
            },
            {
                "anchor_ids": ["GEOGRAPHIC_AREA", "GEOGRAPHIC_CONCENTRATION"],
                "group_id": "GEOGRAPHY_OWNER_PRIMARY",
                "mode": "ANY",
                "page_relation": "SAME_OR_ADJACENT_PAGE",
                "priority": 1,
            },
        ],
        "semantic_assignment_adapter_ref": _adapter_content_ref(project_root),
        "structural_reset_fragments": [
            "bao cao bo phan chinh yeu theo khu vuc dia ly",
            "bao cao bo phan theo khu vuc dia ly",
        ],
        "structural_reset_max_line_ordinal": 3,
        "window_line_span": 3,
        "zero_hit_policy": "FULL_DOCUMENT_FALLBACK",
    }


_PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOAN_GEOGRAPHY_REGION_QUERY_SPEC_V2 = _query_spec(_PROJECT_ROOT)


def build_loan_geography_region_query_spec_v2(project_root: str | Path) -> dict[str, Any]:
    """Return the one adapter-bound V2 retrieval shortlist specification."""

    root = Path(project_root).resolve()
    observed = _query_spec(root)
    if not same_typed_json_v1(observed, LOAN_GEOGRAPHY_REGION_QUERY_SPEC_V2):
        raise _error("Family 11 query spec differs from its loaded adapter trust closure")
    # Import lazily so the generic adapter remains usable without initializing
    # the authenticated retrieval subsystem.
    from bctc_ai.evaluation.family_first_region_retrieval_v1 import (
        validate_family_first_region_query_spec_v2,
    )

    return validate_family_first_region_query_spec_v2(observed)


def _content_address(value: Mapping[str, Any], *, prefix: str) -> dict[str, Any]:
    material = canonical_clone_v1(value)
    return {**material, "result_id": prefix + canonical_json_sha256_v1(material)}


def _receipt(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or value.get("family_id") != FAMILY_ID
        or value.get("format_version") != "FAMILY_FIRST_REGION_RETRIEVAL_RECEIPT_V2"
        or type(value.get("receipt_id")) is not str
        or type(value.get("documents")) is not list
        or not value["documents"]
    ):
        raise _error("Family 11 retrieval receipt identity drifted")
    expected_query = build_loan_geography_region_query_spec_v2(_PROJECT_ROOT)
    if not same_typed_json_v1(value.get("query_spec"), expected_query):
        raise _error("Family 11 receipt is not bound to the authoritative adapter query spec")
    material = canonical_clone_v1(value)
    receipt_id = material.pop("receipt_id")
    if receipt_id != "fffrrv2:receipt:" + canonical_json_sha256_v1(material):
        raise _error("Family 11 retrieval receipt content identity drifted")
    for ordinal, outcome in enumerate(value["documents"], 1):
        if (
            type(outcome) is not dict
            or outcome.get("document_ordinal") != ordinal
            or outcome.get("coverage_status") != "PROVEN_COMPLETE_FOR_DECLARED_SPEC"
            or type(outcome.get("selected_pages")) is not list
            or outcome["selected_pages"] != sorted(set(outcome["selected_pages"]))
            or type(outcome.get("outcome_id")) is not str
        ):
            raise _error("Family 11 retrieval outcome coverage drifted")
        outcome_material = canonical_clone_v1(outcome)
        outcome_id = outcome_material.pop("outcome_id")
        if outcome_id != "fffrrv2:document:" + canonical_json_sha256_v1(outcome_material):
            raise _error("Family 11 retrieval outcome content identity drifted")
    return canonical_clone_v1(value)


def _snapshot(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or type(value.get("snapshot_id")) is not str
        or type(value.get("document_packet")) is not dict
        or type(value.get("joined_pages")) is not list
        or not value["joined_pages"]
        or type(value.get("selected_page_dimensions")) is not list
    ):
        raise _error("Family 11 selected-page snapshot shape drifted")
    material = canonical_clone_v1(value)
    snapshot_id = material.pop("snapshot_id")
    if snapshot_id != "ffdesv1:selected:" + canonical_json_sha256_v1(material):
        raise _error("Family 11 selected-page snapshot content identity drifted")
    packet = value["document_packet"]
    if (
        type(packet.get("document_ordinal")) is not int
        or type(packet.get("document_id")) is not str
        or type(packet.get("packet_id")) is not str
        or type(packet.get("page_count")) is not int
        or type(packet.get("line_count")) is not int
    ):
        raise _error("Family 11 document packet identity drifted")
    dimensions = value["selected_page_dimensions"]
    pages = value["joined_pages"]
    if len(dimensions) != len(pages):
        raise _error("Family 11 selected-page dimensions differ from joined pages")
    page_ids = [page.get("page_sequence") for page in pages]
    dimension_ids = [item.get("physical_page") for item in dimensions]
    if (
        page_ids != sorted(set(page_ids))
        or page_ids != dimension_ids
        or any(type(page_id) is not int or page_id <= 0 for page_id in page_ids)
    ):
        raise _error("Family 11 original physical page axis drifted")
    return canonical_clone_v1(value)


def _region_pages(
    snapshot: Mapping[str, Any], *, include_empty: bool = False
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    dimensions = {item["physical_page"]: item for item in snapshot["selected_page_dimensions"]}
    pages = []
    locators = []
    seen: set[tuple[int, int]] = set()
    for raw_page in snapshot["joined_pages"]:
        page_sequence = raw_page["page_sequence"]
        dimension = dimensions[page_sequence]
        page_width = raw_page.get("page_width")
        if page_width != dimension.get("pixel_width"):
            raise _error("Family 11 OCR/render page width binding drifted")
        lines = []
        for raw_line in raw_page.get("lines", []):
            source_index = raw_line.get("line_ordinal")
            numeric = raw_line.get("numeric_recognition")
            if (
                type(source_index) is not int
                or source_index < 0
                or (page_sequence, source_index) in seen
                or type(raw_line.get("bbox")) is not list
                or type(raw_line.get("vietocr_text")) is not str
                or raw_line["vietocr_text"]
                != unicodedata.normalize("NFC", raw_line["vietocr_text"])
                or type(numeric) is not dict
                or type(numeric.get("raw_prediction")) is not str
                or type(numeric.get("reader_score")) not in {int, float}
            ):
                raise _error("Family 11 selected-page line evidence drifted")
            seen.add((page_sequence, source_index))
            lines.append(
                {
                    "bbox": canonical_clone_v1(raw_line["bbox"]),
                    "source_line_index": source_index,
                    "source_text": numeric["raw_prediction"],
                    "vietocr_text": raw_line["vietocr_text"],
                }
            )
            locators.append(
                {
                    "bbox": canonical_clone_v1(raw_line["bbox"]),
                    "crop_ref": canonical_clone_v1(raw_line.get("crop_ref")),
                    "page_sequence": page_sequence,
                    "ppocrv6_reader_score": float(numeric["reader_score"]),
                    "ppocrv6_surface": numeric["raw_prediction"],
                    "sample_id": raw_line.get("sample_id"),
                    "source_line_index": source_index,
                    "vietocr_transformer_surface": raw_line["vietocr_text"],
                }
            )
        if lines or include_empty:
            pages.append(
                {
                    "lines": lines,
                    "page_height": dimension["pixel_height"],
                    "page_sequence": page_sequence,
                    "page_width": page_width,
                }
            )
    return pages, sorted(
        locators, key=lambda item: (item["page_sequence"], item["source_line_index"])
    )


def _context_pages(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    pages, _locators = _region_pages(snapshot, include_empty=True)
    return [
        {
            "lines": [
                {
                    "bbox": canonical_clone_v1(line["bbox"]),
                    "source_line_index": line["source_line_index"],
                    "vietocr_text": line["vietocr_text"],
                }
                for line in page["lines"]
            ],
            "page_sequence": page["page_sequence"],
        }
        for page in pages
    ]


def build_loan_geography_document_context_v1(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Derive PDF-internal period/unit context from one full document snapshot."""

    typed = _snapshot(snapshot)
    packet = typed["document_packet"]
    pages = _context_pages(typed)
    if [item["page_sequence"] for item in pages] != list(range(1, packet["page_count"] + 1)):
        raise _error("Family 11 document context requires one complete physical page axis")
    period = infer_document_reporting_period_context_v1(pages)
    unit = infer_document_accounting_unit_context_v1(pages)
    line_index = {
        (page["page_sequence"], line["source_line_index"]): line["vietocr_text"]
        for page in pages
        for line in page["lines"]
    }
    current_period_evidence = []
    current_period = period.get("current_period_end")
    for observed in period.get("observed_dates", []):
        if observed.get("date") != current_period:
            continue
        for evidence in observed.get("evidence", []):
            page_sequence = evidence.get("page_sequence")
            source_indices = evidence.get("source_line_indices")
            if (
                type(page_sequence) is not int
                or type(source_indices) is not list
                or not source_indices
                or any(type(index) is not int for index in source_indices)
            ):
                raise _error("Family 11 document-period evidence binding drifted")
            keys = [(page_sequence, index) for index in source_indices]
            if any(key not in line_index for key in keys):
                raise _error("Family 11 document-period source line is absent")
            current_period_evidence.append(
                {
                    "evidence_refs": [f"line:{page_sequence}:{index}" for index in source_indices],
                    "page_sequence": page_sequence,
                    "source_line_indices": canonical_clone_v1(source_indices),
                    "source_surfaces_raw_nfc": [line_index[key] for key in keys],
                }
            )
    material = {
        "claim_boundary": (
            "PDF_INTERNAL_REPEATED_PERIOD_AND_EXPLICIT_UNIT_CONTEXT_PROPOSAL_ONLY_"
            "NO_PACKET_FILENAME_YEAR_BANK_NUMERIC_MAPPING_OR_SCHEMA_AUTHORITY"
        ),
        "document_evidence_root_sha256": packet["document_evidence_root_sha256"],
        "document_id": packet["document_id"],
        "document_packet_id": packet["packet_id"],
        "format_version": DOCUMENT_CONTEXT_FORMAT_VERSION,
        "current_period_evidence": current_period_evidence,
        "period_context": period,
        "snapshot_id": typed["snapshot_id"],
        "state": "FULL_DOCUMENT_PDF_INTERNAL_CONTEXT_PROPOSAL",
        "unit_context": unit,
    }
    return _content_address(material, prefix="lgstv1:document-context:")


def _document_context(
    value: Any, *, document: Mapping[str, Any], document_packet: Mapping[str, Any]
) -> dict[str, Any]:
    if (
        type(value) is not dict
        or value.get("format_version") != DOCUMENT_CONTEXT_FORMAT_VERSION
        or value.get("document_id") != document.get("document_id")
        or value.get("document_id") != document_packet.get("document_id")
        or value.get("document_packet_id") != document_packet.get("packet_id")
        or value.get("document_evidence_root_sha256")
        != document_packet.get("document_evidence_root_sha256")
    ):
        raise _error("Family 11 PDF-internal document context binding drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id", None)
    if identity != "lgstv1:document-context:" + canonical_json_sha256_v1(material):
        raise _error("Family 11 PDF-internal document context identity drifted")
    return canonical_clone_v1(value)


def validate_loan_geography_document_context_replay_v1(
    value: Any, snapshot: Mapping[str, Any]
) -> dict[str, Any]:
    """Recompute PDF-internal period/unit features from the full snapshot."""

    rebuilt = build_loan_geography_document_context_v1(snapshot)
    packet = snapshot["document_packet"]
    _document_context(
        value, document={"document_id": packet["document_id"]}, document_packet=packet
    )
    if not same_typed_json_v1(value, rebuilt):
        raise _error("Family 11 PDF-internal document context does not replay exactly")
    return rebuilt


def _match_provenance_bindings(scoped: Mapping[str, Any]) -> list[dict[str, Any]]:
    semantic_key = {
        "CONTINUATION": "CONTINUATION",
        "DOMESTIC_TOTAL": "DOMESTIC_TOTAL",
        "EXACT_CUSTOMER_LOANS": "EXACT_CUSTOMER_LOANS",
        "FOREIGN_TOTAL": "FOREIGN_TOTAL",
        "OWNER": "GEOGRAPHIC_CONCENTRATION_OWNER",
        "BROAD_MIXED_LOAN_POPULATION": "BROAD_MIXED_LOAN_POPULATION",
        "BROAD_TOTAL_LOANS": "BROAD_TOTAL_LOANS",
        "STRUCTURAL_RESET": "STRUCTURAL_RESET",
        "TRAILING_TOTAL": "TRAILING_TOTAL",
    }
    provenance = {
        (semantic_id, item["surface"]): item
        for semantic_id, records in LOAN_GEOGRAPHY_SCOPED_TABLE_ALIAS_PROVENANCE_V1.items()
        for item in records
    }
    selected: dict[str, dict[str, Any]] = {}

    def visit(value: Any) -> None:
        if type(value) is dict:
            composite = value.get("match")
            if (
                type(value.get("match_id")) is str
                and type(value.get("semantic_id")) is str
                and type(composite) is dict
                and composite.get("match_kind")
                == "DECLARATIVE_REQUIRED_COMPONENT_GROUPS_IN_BOUNDED_VISUAL_WINDOW"
                and type(composite.get("component_matches")) is list
            ):
                component_bindings = []
                for component in composite["component_matches"]:
                    if (
                        type(component) is not dict
                        or type(component.get("component_id")) is not str
                        or type(component.get("match")) is not dict
                        or type(component["match"].get("alias_raw_nfc")) is not str
                    ):
                        raise _error("Family 11 component match provenance drifted")
                    record = provenance.get(
                        (component["component_id"], component["match"]["alias_raw_nfc"])
                    )
                    if record is None:
                        raise _error("Family 11 matched component alias lacks closed provenance")
                    component_bindings.append(
                        {
                            "alias_kind": record["kind"],
                            "alias_surface": record["surface"],
                            "component_id": component["component_id"],
                            "shared_alias_id": component["match"]["alias_id"],
                            "shared_match_kind": component["match"]["match_kind"],
                            "verification_ref": record["verification_ref"],
                        }
                    )
                binding = {
                    "adapter_semantic_id": semantic_key.get(value["semantic_id"]),
                    "alias_kind": "DECLARATIVE_REQUIRED_COMPONENT_GROUPS",
                    "alias_surface": value["surface_raw_nfc"],
                    "component_alias_bindings": component_bindings,
                    "match_id": value["match_id"],
                    "shared_alias_id": composite["alias_id"],
                    "shared_match_kind": composite["match_kind"],
                    "verification_ref": "COMPOSITION_OF_CLOSED_CANONICAL_COMPONENT_BINDINGS",
                }
                selected[value["match_id"]] = binding
            elif (
                type(value.get("match_id")) is str
                and type(value.get("semantic_id")) is str
                and type(value.get("match")) is dict
                and type(value["match"].get("alias_raw_nfc")) is str
            ):
                adapter_semantic = semantic_key.get(value["semantic_id"])
                record = provenance.get((adapter_semantic, value["match"]["alias_raw_nfc"]))
                if record is None:
                    raise _error("Family 11 matched alias lacks closed provenance")
                binding = {
                    "adapter_semantic_id": adapter_semantic,
                    "alias_kind": record["kind"],
                    "alias_surface": record["surface"],
                    "match_id": value["match_id"],
                    "shared_alias_id": value["match"]["alias_id"],
                    "shared_match_kind": value["match"]["match_kind"],
                    "verification_ref": record["verification_ref"],
                }
                prior = selected.get(value["match_id"])
                if prior is not None and not same_typed_json_v1(prior, binding):
                    raise _error("Family 11 match provenance binding conflicts")
                selected[value["match_id"]] = binding
            for item in value.values():
                visit(item)
        elif type(value) is list:
            for item in value:
                visit(item)

    visit(scoped)
    return sorted(selected.values(), key=lambda item: item["match_id"])


def _structural_segment_fingerprint(segment: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "axis_centers_x2": canonical_clone_v1(segment["axis_centers_x2"]),
        "axis_pixel_bounds": canonical_clone_v1(segment["axis_pixel_bounds"]),
        "header_context": canonical_clone_v1(segment["header_context"]),
        "layout_mode": segment["layout_mode"],
        "owner": canonical_clone_v1(segment["owner"]),
        "page_sequences": canonical_clone_v1(segment["page_sequences"]),
        "period_key": segment["period_key"],
        "period_lane_index": segment.get("period_lane_index"),
        "period_resolution": segment["period_resolution"],
        "population_scope": canonical_clone_v1(segment["population_scope"]),
        "role_cells": canonical_clone_v1(segment["role_cells"]),
        "role_matches": canonical_clone_v1(segment["role_matches"]),
        "segment_status": segment["segment_status"],
        "trailing_total_cells": canonical_clone_v1(segment["trailing_total_cells"]),
        "trailing_total_match": canonical_clone_v1(segment["trailing_total_match"]),
        "trailing_total_resolution": canonical_clone_v1(segment["trailing_total_resolution"]),
        "unresolved_reasons": canonical_clone_v1(segment["unresolved_reasons"]),
    }


def _region_fingerprint(disposition: str, scoped: Mapping[str, Any]) -> dict[str, Any]:
    if disposition == "EXACT_CUSTOMER_LOAN_GEOGRAPHY":
        regions = [
            {
                "continuation": canonical_clone_v1(graph["continuation"]),
                "segments": sorted(
                    [_structural_segment_fingerprint(item) for item in graph["segments"]],
                    key=canonical_json_sha256_v1,
                ),
            }
            for graph in scoped["graphs"]
            if graph.get("status") == _TERMINAL_GRAPH_STATUS
        ]
    elif disposition == "BROAD_POPULATION_BOUNDED_ABSENCE":
        regions = [_structural_segment_fingerprint(item) for item in scoped["bounded_absences"]]
    else:
        regions = []
    regions = sorted(regions, key=lambda item: canonical_json_sha256_v1(item))
    return {
        "disposition": disposition,
        "partial": any(
            graph.get("status") == _PARTIAL_NONTERMINAL_STATUS for graph in scoped["graphs"]
        ),
        "regions": regions,
    }


def _validated_document_envelope(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or value.get("format_version") != DOCUMENT_FORMAT_VERSION
        or value.get("family_id") != FAMILY_ID
        or value.get("disposition") not in _DISPOSITIONS
    ):
        raise _error("Family 11 document graph envelope drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id", None)
    if identity != "lgstv1:document:" + canonical_json_sha256_v1(material):
        raise _error("Family 11 document graph content identity drifted")
    fingerprint = _region_fingerprint(value["disposition"], value["scoped_table_graph"])
    if not same_typed_json_v1(fingerprint, value["region_fingerprint"]):
        raise _error("Family 11 document structural fingerprint drifted")
    accepted = [
        graph
        for graph in value["scoped_table_graph"]["graphs"]
        if graph.get("status") == _TERMINAL_GRAPH_STATUS
    ]
    if not same_typed_json_v1(accepted, value["graphs"]):
        raise _error("Family 11 document accepted graph projection drifted")
    return canonical_clone_v1(value)


def _document(
    receipt: Mapping[str, Any],
    outcome: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    *,
    require_selected_axis: bool,
) -> dict[str, Any]:
    packet = snapshot["document_packet"]
    ordinal = packet["document_ordinal"]
    page_axis = [item["page_sequence"] for item in snapshot["joined_pages"]]
    if (
        outcome["document_ordinal"] != ordinal
        or outcome.get("document_id") != packet["document_id"]
        or outcome.get("document_packet_id") != packet["packet_id"]
        or outcome.get("document_evidence_root_sha256")
        != packet.get("document_evidence_root_sha256")
        or (require_selected_axis and page_axis != outcome["selected_pages"])
        or (not require_selected_axis and page_axis != list(range(1, packet["page_count"] + 1)))
    ):
        raise _error("Family 11 receipt/snapshot document or page binding drifted")
    pages, locators = _region_pages(snapshot)
    scoped = build_accounting_scoped_table_graph_v1(pages, LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1)
    accepted = [
        graph for graph in scoped["graphs"] if graph.get("status") == _TERMINAL_GRAPH_STATUS
    ]
    nonterminal = [
        graph for graph in scoped["graphs"] if graph.get("status") != _TERMINAL_GRAPH_STATUS
    ]
    unresolved = [*scoped["unresolved_fragments"]]
    if len(accepted) == 1 and not nonterminal and not unresolved:
        disposition = "EXACT_CUSTOMER_LOAN_GEOGRAPHY"
    elif len(accepted) > 1:
        disposition = "UNRESOLVED"
        unresolved.append({"unresolved_reason": "MULTIPLE_EXACT_CUSTOMER_LOAN_REGIONS"})
    elif nonterminal or unresolved:
        disposition = "UNRESOLVED"
    elif scoped["bounded_absences"]:
        disposition = "BROAD_POPULATION_BOUNDED_ABSENCE"
    else:
        disposition = "NOT_OBSERVED"
    fingerprint = _region_fingerprint(disposition, scoped)
    provenance_bindings = _match_provenance_bindings(scoped)
    dimensions = {item["physical_page"]: item for item in snapshot["selected_page_dimensions"]}
    material = {
        "alias_provenance_id": ALIAS_PROVENANCE_ID,
        "bounded_absences": canonical_clone_v1(scoped["bounded_absences"]),
        "claim_boundary": CLAIM_BOUNDARY,
        "disposition": disposition,
        "document_id": packet["document_id"],
        "document_ordinal": ordinal,
        "evidence_binding": {
            "document_id": packet["document_id"],
            "document_evidence_root_sha256": packet["document_evidence_root_sha256"],
            "document_ordinal": ordinal,
            "document_packet_id": packet["packet_id"],
            "outcome_id": outcome["outcome_id"],
            "receipt_id": receipt["receipt_id"],
            "snapshot_id": snapshot["snapshot_id"],
        },
        "family_id": FAMILY_ID,
        "format_version": DOCUMENT_FORMAT_VERSION,
        "graphs": canonical_clone_v1(accepted),
        "matcher_metrics": canonical_clone_v1(scoped["matcher_metrics"]),
        "match_provenance_bindings": provenance_bindings,
        "region_fingerprint": fingerprint,
        "scoped_table_graph": scoped,
        "selected_page_bindings": [
            {
                "line_count": len(page["lines"]),
                "physical_page": page["page_sequence"],
                "pixel_height": dimensions[page["page_sequence"]]["pixel_height"],
                "pixel_width": dimensions[page["page_sequence"]]["pixel_width"],
                "render_sha256": dimensions[page["page_sequence"]]["render_sha256"],
                "render_size_bytes": dimensions[page["page_sequence"]]["render_size_bytes"],
            }
            for page in snapshot["joined_pages"]
        ],
        "source_line_bindings": locators,
        "spec_id": SPEC_ID,
        "status": (
            "STRUCTURALLY_RESOLVED_NO_NUMERIC_OR_MAPPING_AUTHORITY"
            if disposition != "UNRESOLVED"
            else "UNRESOLVED_STRUCTURE"
        ),
        "uniqueness": {
            "exact_logical_graph_count": len(accepted),
            "multiple_identical_region_count": max(
                0,
                len(accepted)
                - len({canonical_json_sha256_v1(item) for item in fingerprint["regions"]}),
            ),
            "partial_nonterminal_graph_count": len(nonterminal),
            "physical_region_count": scoped["metrics"]["physical_segment_count"],
        },
        "unresolved_candidates": canonical_clone_v1(unresolved),
    }
    return _content_address(material, prefix="lgstv1:document:")


def build_loan_geography_scoped_graphs_v1(
    receipt: Mapping[str, Any], selected_pages: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Build Family 11 document graphs from one receipt and snapshot batch.

    ``selected_pages`` may be a source-ordered streaming subset of receipt
    documents.  Every supplied snapshot must bind exactly the selected pages
    declared by its receipt outcome; a corpus seal separately requires all
    receipt documents.
    """

    typed_receipt = _receipt(receipt)
    if (
        isinstance(selected_pages, (str, bytes, bytearray))
        or not isinstance(selected_pages, Sequence)
        or not selected_pages
    ):
        raise _error("Family 11 selected-page snapshot batch drifted")
    snapshots = [_snapshot(item) for item in selected_pages]
    ordinals = [item["document_packet"]["document_ordinal"] for item in snapshots]
    if ordinals != sorted(set(ordinals)):
        raise _error("Family 11 snapshot document axis must be sorted and unique")
    outcomes = {item["document_ordinal"]: item for item in typed_receipt["documents"]}
    documents = [
        _document(typed_receipt, outcomes[ordinal], snapshot, require_selected_axis=True)
        for ordinal, snapshot in zip(ordinals, snapshots, strict=True)
    ]
    counts = {disposition: 0 for disposition in sorted(_DISPOSITIONS)}
    for document in documents:
        counts[document["disposition"]] += 1
    material = {
        "alias_provenance": canonical_clone_v1(LOAN_GEOGRAPHY_SCOPED_TABLE_ALIAS_PROVENANCE_V1),
        "alias_provenance_id": ALIAS_PROVENANCE_ID,
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": documents,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "metrics": {
            "document_count": len(documents),
            "disposition_counts": counts,
            "gemma_request_count": 0,
            "multiple_identical_region_count": sum(
                item["uniqueness"]["multiple_identical_region_count"] for item in documents
            ),
            "selected_line_count": sum(
                len(page["lines"]) for snapshot in snapshots for page in snapshot["joined_pages"]
            ),
            "selected_page_count": sum(len(item["joined_pages"]) for item in snapshots),
        },
        "receipt_binding": {
            "receipt_id": typed_receipt["receipt_id"],
            "source_document_count": len(typed_receipt["documents"]),
        },
        "safety": canonical_clone_v1(_SAFETY),
        "spec": canonical_clone_v1(LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1),
        "spec_id": SPEC_ID,
        "state": "REPLAYABLE_STREAMING_DOCUMENT_BATCH",
    }
    return _content_address(material, prefix="lgstv1:batch:")


def build_loan_geography_whole_document_scoped_graph_v1(
    receipt: Mapping[str, Any], snapshot: Mapping[str, Any]
) -> dict[str, Any]:
    """Build one direct whole-document uniqueness oracle with the same adapter."""

    typed_receipt = _receipt(receipt)
    typed_snapshot = _snapshot(snapshot)
    ordinal = typed_snapshot["document_packet"]["document_ordinal"]
    outcome = typed_receipt["documents"][ordinal - 1]
    return _document(typed_receipt, outcome, typed_snapshot, require_selected_axis=False)


def validate_loan_geography_whole_document_scoped_graph_replay_v1(
    value: Any,
    receipt: Mapping[str, Any],
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild one direct full-document graph and replay its generic core."""

    _validated_document_envelope(value)
    rebuilt = build_loan_geography_whole_document_scoped_graph_v1(receipt, snapshot)
    if not same_typed_json_v1(value, rebuilt):
        raise _error("Family 11 whole-document graph does not replay exactly")
    typed_snapshot = _snapshot(snapshot)
    validate_accounting_scoped_table_graph_replay_v1(
        rebuilt["scoped_table_graph"],
        _region_pages(typed_snapshot)[0],
        LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1,
    )
    return rebuilt


def validate_loan_geography_scoped_graphs_replay_v1(
    value: Any,
    receipt: Mapping[str, Any],
    selected_pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Rebuild the adapter batch exactly; self-rehashing is insufficient."""

    if type(value) is not dict or value.get("format_version") != FORMAT_VERSION:
        raise _error("Family 11 adapter batch identity drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id", None)
    if identity != "lgstv1:batch:" + canonical_json_sha256_v1(material):
        raise _error("Family 11 adapter batch content identity drifted")
    rebuilt = build_loan_geography_scoped_graphs_v1(receipt, selected_pages)
    if not same_typed_json_v1(value, rebuilt):
        raise _error("Family 11 adapter batch does not replay exactly")
    for document, snapshot in zip(rebuilt["documents"], selected_pages, strict=True):
        validate_accounting_scoped_table_graph_replay_v1(
            document["scoped_table_graph"],
            _region_pages(snapshot)[0],
            LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1,
        )
    return rebuilt


def compare_loan_geography_sparse_full_graphs_v1(
    sparse_document: Mapping[str, Any],
    whole_document: Mapping[str, Any],
    *,
    whole_document_line_count: int,
    whole_document_page_count: int,
) -> dict[str, Any]:
    """Require identical disposition and exact visual-region fingerprint."""

    sparse_document = _validated_document_envelope(sparse_document)
    whole_document = _validated_document_envelope(whole_document)
    if (
        sparse_document["document_id"] != whole_document["document_id"]
        or sparse_document["disposition"] != whole_document["disposition"]
        or not same_typed_json_v1(
            sparse_document["region_fingerprint"], whole_document["region_fingerprint"]
        )
    ):
        raise _error("Family 11 sparse/full structural result is not equivalent")
    if (
        type(whole_document_line_count) is not int
        or whole_document_line_count < 0
        or type(whole_document_page_count) is not int
        or whole_document_page_count <= 0
    ):
        raise _error("Family 11 whole-document denominator drifted")
    return {
        "disposition": sparse_document["disposition"],
        "sparse_graph_result_id": sparse_document["result_id"],
        "sparse_region_fingerprint": canonical_clone_v1(sparse_document["region_fingerprint"]),
        "status": "EXACT_SPARSE_TO_WHOLE_DOCUMENT_STRUCTURE_EQUIVALENCE",
        "whole_document_graph_result_id": whole_document["result_id"],
        "whole_document_line_count": whole_document_line_count,
        "whole_document_page_count": whole_document_page_count,
        "whole_document_region_fingerprint": canonical_clone_v1(
            whole_document["region_fingerprint"]
        ),
    }


def _iso_period(value: str | None) -> str | None:
    if type(value) is not str:
        return None
    for pattern in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return (
                date.fromisoformat(value).isoformat()
                if pattern == "%Y-%m-%d"
                else datetime.strptime(value, pattern).date().isoformat()
            )
        except ValueError:
            continue
    return None


def _context_current_period(context: Mapping[str, Any]) -> str | None:
    period = context["period_context"]
    if (
        period.get("resolution") != "DOMINANT_REPEATED_FULL_DATE_CONSENSUS"
        or type(period.get("supporting_page_count")) is not int
        or period["supporting_page_count"] < 2
    ):
        return None
    return _iso_period(period.get("current_period_end"))


def _locator_index(document: Mapping[str, Any]) -> dict[tuple[int, int], Mapping[str, Any]]:
    return {
        (item["page_sequence"], item["source_line_index"]): item
        for item in document["source_line_bindings"]
    }


def _ordered_period_segments(value: Any, *, label: str) -> list[Mapping[str, Any]]:
    if type(value) is not list or not value:
        raise _error(f"Family 11 {label} segment axis is empty")
    lanes = [item.get("period_lane_index") for item in value if type(item) is dict]
    if (
        len(lanes) != len(value)
        or any(type(lane) is not int or lane < 0 for lane in lanes)
        or sorted(lanes) != list(range(len(value)))
    ):
        raise _error(f"Family 11 {label} period lanes must be unique and contiguous")
    return sorted(value, key=lambda item: item["period_lane_index"])


def _raw_local_period_evidence(
    segment: Mapping[str, Any],
    *,
    locators: Mapping[tuple[int, int], Mapping[str, Any]],
    resolved_period: str,
) -> tuple[str, str]:
    observations = [
        item
        for item in segment["header_context"]["period_observations"]
        if _iso_period(item.get("period")) == resolved_period
    ]
    if not observations:
        raise _error("Family 11 local period lacks its raw header evidence")
    selected: dict[tuple[int, int], Mapping[str, Any]] = {}
    for observation in observations:
        indices = observation.get("evidence_source_line_indices")
        if (
            type(indices) is not list
            or not indices
            or any(type(index) is not int or index < 0 for index in indices)
        ):
            raise _error("Family 11 local period evidence axis drifted")
        for source_index in indices:
            candidates = [
                (page_sequence, locators[(page_sequence, source_index)])
                for page_sequence in segment["page_sequences"]
                if (page_sequence, source_index) in locators
            ]
            if len(candidates) != 1:
                raise _error("Family 11 local period source line is ambiguous")
            page_sequence, locator = candidates[0]
            selected[(page_sequence, source_index)] = locator
    ordered = sorted(
        selected.items(),
        key=lambda item: (
            item[0][0],
            item[1]["bbox"][1],
            item[1]["bbox"][0],
            item[0][1],
        ),
    )
    refs = [f"line:{page}:{index}" for (page, index), _locator in ordered]
    surfaces = [locator["vietocr_transformer_surface"] for _key, locator in ordered]
    if any(type(surface) is not str or not surface for surface in surfaces):
        raise _error("Family 11 local period raw surface drifted")
    return "|".join(refs), " | ".join(surfaces)


def _raw_inherited_period_evidence(
    context: Mapping[str, Any], *, resolved_period: str
) -> tuple[str, str]:
    if _iso_period(context["period_context"].get("current_period_end")) != resolved_period:
        raise _error("Family 11 inherited period/context date drifted")
    records = context.get("current_period_evidence")
    if type(records) is not list or not records:
        raise _error("Family 11 inherited period lacks bounded raw PDF evidence")
    flattened = []
    for record in records:
        refs = record.get("evidence_refs") if type(record) is dict else None
        surfaces = record.get("source_surfaces_raw_nfc") if type(record) is dict else None
        if (
            type(refs) is not list
            or type(surfaces) is not list
            or not refs
            or len(refs) != len(surfaces)
            or any(type(ref) is not str or not ref for ref in refs)
            or any(type(surface) is not str or not surface for surface in surfaces)
        ):
            raise _error("Family 11 inherited period raw evidence drifted")
        flattened.extend(zip(refs, surfaces, strict=True))
    return (
        "|".join(ref for ref, _surface in flattened),
        " | ".join(surface for _ref, surface in flattened),
    )


def _line_projection(match: Mapping[str, Any]) -> dict[str, Any]:
    return canonical_clone_v1(match)


def project_loan_geography_visible_dash_graph_v1(
    document: Mapping[str, Any],
    document_packet: Mapping[str, Any],
    *,
    document_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project an exact document graph to the existing pixel-overlay contract."""

    document = _validated_document_envelope(document)
    if (
        document.get("disposition") != "EXACT_CUSTOMER_LOAN_GEOGRAPHY"
        or document.get("document_id") != document_packet.get("document_id")
        or document["uniqueness"]["exact_logical_graph_count"] != 1
    ):
        raise _error("Family 11 dash projection requires one exact document graph")
    typed_context = (
        _document_context(document_context, document=document, document_packet=document_packet)
        if document_context is not None
        else None
    )
    locators = _locator_index(document)
    projected_graphs = []
    for graph in document["graphs"]:
        projected_segments = []
        ordered_segments = _ordered_period_segments(graph["segments"], label="overlay source")
        for segment in ordered_segments:
            resolved = _iso_period(segment.get("period_key"))
            resolution = "LOCAL_EXACT_DATE"
            if resolved is None and len(ordered_segments) == 1:
                resolved = (
                    _context_current_period(typed_context) if typed_context is not None else None
                )
                resolution = "DOCUMENT_INHERITED_EXACT_DATE"
            if resolved is None:
                raise _error("Family 11 dash projection period remains unresolved")
            if typed_context is not None and resolution == "LOCAL_EXACT_DATE":
                period_context = typed_context["period_context"]
                allowed = {
                    parsed
                    for raw in (
                        period_context.get("current_period_end"),
                        period_context.get("balance_comparative_period_end"),
                    )
                    if (parsed := _iso_period(raw)) is not None
                }
                if (
                    period_context.get("resolution") == "DOMINANT_REPEATED_FULL_DATE_CONSENSUS"
                    and allowed
                    and resolved not in allowed
                ):
                    raise _error(
                        "Family 11 local period conflicts with PDF-internal document context"
                    )
            lane = segment["period_lane_index"]
            period_role = "CURRENT" if lane == 0 else "COMPARATIVE"
            cells = []
            for raw in segment["role_cells"]:
                source_index = raw["source_line_index"]
                locator = (
                    locators.get((raw["page_sequence"], source_index))
                    if type(source_index) is int
                    else None
                )
                material = {
                    "bbox": canonical_clone_v1(raw["bbox"]),
                    "coordinate_space": "OCR_PAGE_PIXEL_COORDINATES_BOUND_TO_RECEIPT_RENDER",
                    "crop_ref": canonical_clone_v1(locator.get("crop_ref")) if locator else None,
                    "expected_pixel_bbox": canonical_clone_v1(raw["expected_pixel_bbox"]),
                    "lane_index": lane,
                    "lane_type": "MONEY",
                    "page_sequence": raw["page_sequence"],
                    "period_role": period_role,
                    "ppocrv6_reader_score": locator.get("ppocrv6_reader_score")
                    if locator
                    else None,
                    "ppocrv6_surface": locator.get("ppocrv6_surface") if locator else None,
                    "resolved_period": resolved,
                    "role": raw["role"],
                    "sample_id": locator.get("sample_id") if locator else None,
                    "source_geography_ordinal": raw["source_role_ordinal"],
                    "source_line_index": source_index,
                    "status": (
                        "MISSING_DETECTOR_CELL_REQUIRES_AUTHENTICATED_PIXEL_EVIDENCE"
                        if source_index is None
                        else "BOUND_PPOCRV6_CELL_PROPOSAL_NO_NUMERIC_AUTHORITY"
                    ),
                    "vietocr_transformer_surface": raw["vietocr_raw_nfc_surface"]
                    if source_index is not None
                    else None,
                    "x_center_x2": raw["value_axis_center_x2"],
                }
                cells.append(
                    {
                        **material,
                        "graph_cell_id": raw["cell_id"],
                    }
                )
            roles = {item["semantic_id"]: item for item in segment["role_matches"]}
            projected = {
                "geography_axis": {
                    "domestic": _line_projection(roles["DOMESTIC_TOTAL"]),
                    "foreign": _line_projection(roles["FOREIGN_TOTAL"]),
                },
                "layout": (
                    "GEOGRAPHY_ROWS_ACCOUNTING_FAMILY_COLUMNS"
                    if segment["layout_mode"] == "ROLES_AS_ROWS"
                    else "GEOGRAPHY_COLUMNS_ACCOUNTING_FAMILY_ROWS"
                ),
                "page_sequences": canonical_clone_v1(segment["page_sequences"]),
                "period_headings": canonical_clone_v1(
                    segment["header_context"]["period_observations"]
                ),
                "period_key": segment.get("period_key") or resolved,
                "period_lane_index": lane,
                "period_resolution": resolution,
                "period_role": period_role,
                "population_scope": "EXACT_CUSTOMER_LOANS",
                "resolved_period": resolved,
                "role_cells": cells,
                "scope_axis": canonical_clone_v1(segment["population_scope"]["match"]),
                "segment_id": segment["segment_id"],
                "trailing_total_cells": canonical_clone_v1(segment["trailing_total_cells"]),
                "trailing_total_resolution": canonical_clone_v1(
                    segment["trailing_total_resolution"]
                ),
                "unit_headings": canonical_clone_v1(segment["header_context"]["unit_evidence"]),
            }
            projected_segments.append(projected)
        graph_material = {
            "continuation": canonical_clone_v1(graph["continuation"]),
            "layout_modes": sorted({item["layout"] for item in projected_segments}),
            "segments": projected_segments,
            "status": "STRUCTURALLY_ACCEPTED_NO_NUMERIC_AUTHORITY",
        }
        projected_graphs.append({**graph_material, "graph_id": graph["graph_id"]})
    material = {
        "claim_boundary": "EXACT_FAMILY11_SHARED_GRAPH_TO_PIXEL_OVERLAY_SHAPE_ONLY_NO_NUMERIC_AUTHORITY",
        "document_context_result_id": (
            typed_context["result_id"] if typed_context is not None else None
        ),
        "evidence_binding": canonical_clone_v1(document["evidence_binding"]),
        "family_id": FAMILY_ID,
        "format_version": OVERLAY_FORMAT_VERSION,
        "graphs": projected_graphs,
        "match_provenance_bindings": canonical_clone_v1(document["match_provenance_bindings"]),
        "source_document_graph_result_id": document["result_id"],
        "status": "EXACT_GRAPH_PROJECTED_FOR_AUTHENTICATED_PIXEL_OVERLAY",
    }
    return _content_address(material, prefix="lgstv1:overlay:")


def project_loan_geography_numeric_input_v1(
    document: Mapping[str, Any],
    document_packet: Mapping[str, Any],
    *,
    document_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project role x period cells and printed totals; never parse a number.

    Local exact dates/units are preferred.  Missing context may be inherited
    only from the typed, replayed full-PDF period/unit context.  Document-packet
    period/year metadata never supplies an evidence ref or source surface.
    """

    overlay = project_loan_geography_visible_dash_graph_v1(
        document, document_packet, document_context=document_context
    )
    logical = overlay["graphs"]
    if len(logical) != 1:
        raise _error("Family 11 numeric projection requires one logical graph")
    segments = _ordered_period_segments(logical[0]["segments"], label="numeric overlay")
    source_segments = _ordered_period_segments(
        document["graphs"][0]["segments"], label="numeric source"
    )
    if [item["segment_id"] for item in segments] != [
        item["segment_id"] for item in source_segments
    ]:
        raise _error("Family 11 source/overlay period lane binding drifted")
    locators = _locator_index(document)
    typed_context = (
        _document_context(document_context, document=document, document_packet=document_packet)
        if document_context is not None
        else None
    )
    local_unit_records = [
        item for segment in source_segments for item in segment["header_context"]["unit_evidence"]
    ]
    if local_unit_records:
        local_keys = {
            (item.get("unit_kind"), item.get("currency"), item.get("magnitude_power10"))
            for item in local_unit_records
        }
        required_key = ("MONEY", "VND", 6)
        if local_keys != {required_key} or any(
            segment["header_context"].get("unit_evidence")
            and segment["header_context"].get("unit_resolution")
            != {
                "currency": "VND",
                "magnitude_power10": 6,
                "unit_kind": "MONEY",
            }
            for segment in source_segments
        ):
            raise _error("Family 11 local unit evidence conflicts or is not exact million-VND")
        unit_evidence = min(
            (item["evidence"] for item in local_unit_records),
            key=lambda item: (item["page_sequence"], item["source_line_index"]),
        )
        unit_context = {
            "currency": "VND",
            "evidence_ref": f"line:{unit_evidence['page_sequence']}:{unit_evidence['source_line_index']}",
            "resolution_mode": "LOCAL_EXACT_UNIT",
            "scale": 6,
            "source_surface": unit_evidence["vietocr_raw_nfc_surface"],
            "unit_kind": "MONEY",
        }
    else:
        inherited = typed_context["unit_context"] if typed_context is not None else {}
        evidence = inherited.get("evidence")
        if (
            inherited.get("resolution") != "REPEATED_EXPLICIT_DOCUMENT_UNIT_CONSENSUS"
            or inherited.get("unit_kind") != "MONEY"
            or inherited.get("currency") != "VND"
            or inherited.get("magnitude_power10") != 6
            or type(inherited.get("supporting_page_count")) is not int
            or inherited["supporting_page_count"] < 2
            or type(evidence) is not list
            or not evidence
        ):
            raise _error("Family 11 exact million-VND unit remains unresolved")
        unit_context = {
            "currency": "VND",
            "evidence_ref": typed_context["result_id"],
            "resolution_mode": "DOCUMENT_INHERITED_EXACT_UNIT",
            "scale": 6,
            "source_surface": evidence[0]["surface"],
            "unit_kind": "MONEY",
        }
    period_axis = []
    for segment, source_segment in zip(segments, source_segments, strict=True):
        if segment["period_resolution"] == "LOCAL_EXACT_DATE":
            evidence_ref, source_surface = _raw_local_period_evidence(
                source_segment,
                locators=locators,
                resolved_period=segment["resolved_period"],
            )
        elif segment["period_resolution"] == "DOCUMENT_INHERITED_EXACT_DATE":
            if typed_context is None:
                raise _error("Family 11 inherited period lacks PDF-internal document context")
            evidence_ref, source_surface = _raw_inherited_period_evidence(
                typed_context, resolved_period=segment["resolved_period"]
            )
        else:
            raise _error("Family 11 period resolution mode drifted")
        period_axis.append(
            {
                "evidence_ref": evidence_ref,
                "lane_index": segment["period_lane_index"],
                "lane_type": "MONEY",
                "period_end": segment["resolved_period"],
                "period_role": segment["period_role"],
                "resolution_mode": segment["period_resolution"],
                "source_surface": source_surface,
            }
        )

    def cell(raw: Mapping[str, Any], lane_index: int, role: str) -> dict[str, Any]:
        source_index = raw.get("source_line_index")
        locator = (
            locators.get((raw["page_sequence"], source_index))
            if type(source_index) is int
            else None
        )
        crop = locator.get("crop_ref") if locator else None
        return {
            "bbox": canonical_clone_v1(raw.get("bbox")),
            "cell_id": raw["cell_id"],
            "crop_sha256": crop.get("sha256") if type(crop) is dict else None,
            "lane_index": lane_index,
            "lane_type": "MONEY",
            "page_sequence": raw["page_sequence"],
            "ppocrv6_score": locator.get("ppocrv6_reader_score") if locator else None,
            "ppocrv6_surface": locator.get("ppocrv6_surface") if locator else None,
            "sample_id": locator.get("sample_id") if locator else None,
            "source_line_index": source_index,
            "vietocr_surface": raw.get("vietocr_raw_nfc_surface")
            if source_index is not None
            else None,
        }

    rows = []
    for role in ("DOMESTIC_TOTAL", "FOREIGN_TOTAL"):
        cells = []
        label_refs = []
        label_surfaces = []
        for segment in source_segments:
            lane = segment["period_lane_index"]
            raw = next(item for item in segment["role_cells"] if item["role"] == role)
            cells.append(cell(raw, lane, role))
            label = next(item for item in segment["role_matches"] if item["semantic_id"] == role)
            label_refs.append(label["match_id"])
            label_surfaces.append(label["surface_raw_nfc"])
        rows.append(
            {
                "cells": cells,
                "label_evidence_ref": "|".join(label_refs),
                "label_surface": " | ".join(label_surfaces),
                "role": role,
            }
        )
    total_cells = []
    total_refs = []
    total_surfaces = []
    total_control_evidence = []
    for segment in source_segments:
        lane = segment["period_lane_index"]
        total_match = segment["trailing_total_match"]
        total_resolution = segment["trailing_total_resolution"]
        if len(segment["trailing_total_cells"]) != 1:
            raise _error("Family 11 printed customer-loan total is unresolved")
        if total_match is not None and total_resolution is None:
            row_evidence = total_match["line_evidence"]
            evidence_refs = [
                f"line:{item['page_sequence']}:{item['source_line_index']}" for item in row_evidence
            ]
            source_bboxes = [canonical_clone_v1(item["bbox"]) for item in row_evidence]
            source_line_indices = [item["source_line_index"] for item in row_evidence]
            source_surfaces = [item["vietocr_raw_nfc_surface"] for item in row_evidence]
            label_ref = total_match["match_id"]
            label_surface = total_match["surface_raw_nfc"]
            resolution_mode = "LOCAL_LABELED_TOTAL"
            row_bbox = canonical_clone_v1(total_match["bbox"])
        elif (
            total_match is None
            and type(total_resolution) is dict
            and total_resolution.get("mode") == "UNLABELED_COMPLETE_NUMERIC_TOTAL_ROW"
        ):
            row_evidence = total_resolution["row_evidence"]
            evidence_refs = [
                f"line:{item['page_sequence']}:{item['source_line_index']}" for item in row_evidence
            ]
            source_bboxes = [canonical_clone_v1(item["bbox"]) for item in row_evidence]
            source_line_indices = [item["source_line_index"] for item in row_evidence]
            source_surfaces = [item["vietocr_raw_nfc_surface"] for item in row_evidence]
            label_ref = total_resolution["resolution_id"]
            label_surface = None
            resolution_mode = "LOCAL_UNLABELED_TOTAL_ROW"
            row_bbox = canonical_clone_v1(total_resolution["row_bbox"])
        else:
            raise _error("Family 11 printed customer-loan total provenance is unresolved")
        total_cells.append(
            cell(segment["trailing_total_cells"][0], lane, "PRINTED_CUSTOMER_LOAN_TOTAL")
        )
        total_refs.append(label_ref)
        total_surfaces.append(label_surface)
        total_control_evidence.append(
            {
                "evidence_refs": evidence_refs,
                "label_evidence_ref": label_ref,
                "label_surface": label_surface,
                "lane_index": lane,
                "page_sequence": segment["page_sequences"][0],
                "resolution_mode": resolution_mode,
                "row_bbox": row_bbox,
                "source_bboxes": source_bboxes,
                "source_line_indices": source_line_indices,
                "source_surfaces_raw_nfc": source_surfaces,
            }
        )
    mode = (
        "REPEATED_FULL_SEGMENT_ONE_PERIOD_PER_PAGE"
        if document["graphs"][0]["continuation"]["mode"]
        == "ADJACENT_REPEATED_FULL_SEGMENTS_PERIOD_COMPLEMENT"
        else "SINGLE_PAGE_GEOGRAPHY_ROWS_ACCOUNTING_COLUMNS"
        if source_segments[0]["layout_mode"] == "ROLES_AS_ROWS"
        else "SINGLE_PAGE_GEOGRAPHY_COLUMNS_ACCOUNTING_ROWS"
    )
    aggregate_total_surface = (
        " | ".join(total_surfaces)
        if all(type(surface) is str for surface in total_surfaces)
        else None
    )
    return {
        "family_id": FAMILY_ID,
        "format_version": "LOAN_GEOGRAPHY_NUMERIC_RECONCILIATION_INPUT_V1",
        "known_nested_domestic_roles_outside_contract": [
            "HO_CHI_MINH_CITY",
            "MEKONG_DELTA",
            "CENTRAL_AND_CENTRAL_HIGHLANDS",
            "NORTH",
            "SOUTHEAST",
        ],
        "lane_types": ["MONEY"] * len(segments),
        "mapped_rows": rows,
        "period_axis": period_axis,
        "presentation_mode": mode,
        "printed_customer_loan_total": {
            "cells": total_cells,
            "control_evidence": total_control_evidence,
            "label_evidence_ref": "|".join(total_refs),
            "label_surface": aggregate_total_surface,
            "role": "PRINTED_CUSTOMER_LOAN_TOTAL",
        },
        "region_id": logical[0]["graph_id"],
        "source_id": overlay["result_id"],
        "structure_challenger_refs": [],
        "unit_context": unit_context,
    }
