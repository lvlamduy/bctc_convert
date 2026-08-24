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
from dataclasses import dataclass
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
    money_integer_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    decode_canonical_json_bytes_v1,
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
    "TOTAL_CONTROL_REQUEST_FORMAT_VERSION",
    "build_loan_geography_customer_loan_total_control_requests_v1",
    "build_loan_geography_scoped_graphs_v1",
    "build_loan_geography_document_context_v1",
    "build_loan_geography_region_query_spec_v2",
    "build_loan_geography_whole_document_scoped_graph_v1",
    "compare_loan_geography_sparse_full_graphs_v1",
    "project_loan_geography_numeric_input_v1",
    "project_loan_geography_visible_dash_graph_v1",
    "validate_loan_geography_customer_loan_total_control_requests_replay_v1",
    "validate_loan_geography_customer_loan_total_control_requests_v1",
    "validate_loan_geography_document_context_replay_v1",
    "validate_loan_geography_scoped_graphs_replay_v1",
    "validate_loan_geography_whole_document_scoped_graph_replay_v1",
]


FAMILY_ID = "LOAN_GEOGRAPHIC_CLASSIFICATION"
FORMAT_VERSION = "LOAN_GEOGRAPHY_SCOPED_GRAPH_BATCH_V1"
DOCUMENT_FORMAT_VERSION = "LOAN_GEOGRAPHY_SCOPED_GRAPH_DOCUMENT_V1"
OVERLAY_FORMAT_VERSION = "LOAN_GEOGRAPHY_SCOPED_GRAPH_OVERLAY_PROJECTION_V1"
DOCUMENT_CONTEXT_FORMAT_VERSION = "LOAN_GEOGRAPHY_DOCUMENT_PERIOD_UNIT_CONTEXT_V1"
TOTAL_CONTROL_REQUEST_FORMAT_VERSION = "LOAN_GEOGRAPHY_CUSTOMER_LOAN_TOTAL_CONTROL_REQUEST_SET_V1"
_TOTAL_CONTROL_REQUEST_STATE = "CLASSIFIED_EXACT_CUSTOMER_LOAN_TOTAL_CONTROL_REQUIREMENTS"
_TOTAL_CONTROL_REQUEST_AUTHORITY = {
    "numeric_or_mapping_authority": False,
    "source_snapshot_self_hash_is_authentication_authority": False,
    "upstream_control_public_replay_required": True,
}
_TOTAL_CONTROL_REQUEST_CLAIM_BOUNDARY = (
    "EXACT_WHOLE_DOCUMENT_FAMILY11_LANE_LOCAL_TOTAL_CLASSIFICATION_AND_"
    "CONTENT_ADDRESSED_UPSTREAM_CONTROL_REQUEST_ONLY_NO_NUMERIC_OR_MAPPING_AUTHORITY"
)
_TOTAL_CONTROL_CLASSIFICATIONS = {
    "LOCAL_LABELED_TOTAL",
    "LOCAL_UNLABELED_TOTAL_ROW",
    "STRUCTURALLY_ABSENT",
}
_UPSTREAM_TOTAL_CONTROL_FORMAT_VERSION = "CUSTOMER_LOAN_TOTAL_CONTROL_V1"
_UPSTREAM_TOTAL_CONTROL_FAMILY_ID = "CUSTOMER_LOAN_TOTAL_CONTROL"
_UPSTREAM_TOTAL_CONTROL_STATE = "EXACT_AUTHENTICATED_PRINTED_CUSTOMER_LOAN_TOTAL_CONTROL"
_UPSTREAM_TOTAL_CONTROL_MODE = "UPSTREAM_AUTHENTICATED_CUSTOMER_LOAN_TOTAL_CONTROL"
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


@dataclass(frozen=True, slots=True)
class _PreparedReceiptOutcomeV1:
    """Compact immutable worker view of one fully validated receipt outcome."""

    document_evidence_root_sha256: str
    document_id: str
    document_ordinal: int
    document_packet_id: str
    outcome_id: str
    selected_pages: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class _PreparedReceiptV1:
    """Process-local receipt proof; never a persisted or public authority."""

    canonical_payload_sha256: str
    documents: tuple[_PreparedReceiptOutcomeV1, ...]
    prepared_binding_sha256: str
    query_spec_sha256: str
    receipt_id: str
    seal: object


_PREPARED_RECEIPT_SEAL = object()


def _prepared_receipt_material(
    *,
    canonical_payload_sha256: str,
    documents: Sequence[_PreparedReceiptOutcomeV1],
    query_spec_sha256: str,
    receipt_id: str,
) -> dict[str, Any]:
    return {
        "canonical_payload_sha256": canonical_payload_sha256,
        "documents": [
            {
                "document_evidence_root_sha256": item.document_evidence_root_sha256,
                "document_id": item.document_id,
                "document_ordinal": item.document_ordinal,
                "document_packet_id": item.document_packet_id,
                "outcome_id": item.outcome_id,
                "selected_pages": list(item.selected_pages),
            }
            for item in documents
        ],
        "query_spec_sha256": query_spec_sha256,
        "receipt_id": receipt_id,
    }


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


def _validate_prepared_receipt_v1(value: _PreparedReceiptV1) -> _PreparedReceiptV1:
    if value.seal is not _PREPARED_RECEIPT_SEAL:
        raise _error("Family 11 prepared receipt seal drifted")
    material = _prepared_receipt_material(
        canonical_payload_sha256=value.canonical_payload_sha256,
        documents=value.documents,
        query_spec_sha256=value.query_spec_sha256,
        receipt_id=value.receipt_id,
    )
    if value.prepared_binding_sha256 != canonical_json_sha256_v1(material):
        raise _error("Family 11 prepared receipt binding drifted")
    expected_query = build_loan_geography_region_query_spec_v2(_PROJECT_ROOT)
    if value.query_spec_sha256 != canonical_json_sha256_v1(expected_query):
        raise _error("Family 11 prepared receipt query trust closure drifted")
    return value


def _receipt(value: Any) -> _PreparedReceiptV1:
    if type(value) is _PreparedReceiptV1:
        return _validate_prepared_receipt_v1(value)
    if (
        type(value) is not dict
        or value.get("family_id") != FAMILY_ID
        or value.get("format_version") != "FAMILY_FIRST_REGION_RETRIEVAL_RECEIPT_V2"
        or type(value.get("receipt_id")) is not str
        or type(value.get("documents")) is not list
        or not value["documents"]
    ):
        raise _error("Family 11 retrieval receipt identity drifted")
    canonical_payload = canonical_json_bytes_v1(value)
    typed_value = decode_canonical_json_bytes_v1(canonical_payload)
    expected_query = build_loan_geography_region_query_spec_v2(_PROJECT_ROOT)
    if not same_typed_json_v1(typed_value.get("query_spec"), expected_query):
        raise _error("Family 11 receipt is not bound to the authoritative adapter query spec")
    material = dict(typed_value)
    receipt_id = material.pop("receipt_id")
    if receipt_id != "fffrrv2:receipt:" + canonical_json_sha256_v1(material):
        raise _error("Family 11 retrieval receipt content identity drifted")
    for ordinal, outcome in enumerate(typed_value["documents"], 1):
        if (
            type(outcome) is not dict
            or type(outcome.get("document_ordinal")) is not int
            or outcome.get("document_ordinal") != ordinal
            or outcome.get("coverage_status") != "PROVEN_COMPLETE_FOR_DECLARED_SPEC"
            or type(outcome.get("document_evidence_root_sha256")) is not str
            or type(outcome.get("document_id")) is not str
            or type(outcome.get("document_packet_id")) is not str
            or type(outcome.get("selected_pages")) is not list
            or any(
                type(page) is not int or page <= 0 for page in outcome.get("selected_pages", [])
            )
            or outcome["selected_pages"] != sorted(set(outcome["selected_pages"]))
            or type(outcome.get("outcome_id")) is not str
        ):
            raise _error("Family 11 retrieval outcome coverage drifted")
        outcome_material = dict(outcome)
        outcome_id = outcome_material.pop("outcome_id")
        if outcome_id != "fffrrv2:document:" + canonical_json_sha256_v1(outcome_material):
            raise _error("Family 11 retrieval outcome content identity drifted")
    documents = tuple(
        _PreparedReceiptOutcomeV1(
            document_evidence_root_sha256=outcome.get("document_evidence_root_sha256"),
            document_id=outcome.get("document_id"),
            document_ordinal=outcome["document_ordinal"],
            document_packet_id=outcome.get("document_packet_id"),
            outcome_id=outcome["outcome_id"],
            selected_pages=tuple(outcome["selected_pages"]),
        )
        for outcome in typed_value["documents"]
    )
    canonical_payload_sha256 = hashlib.sha256(canonical_payload).hexdigest()
    query_spec_sha256 = canonical_json_sha256_v1(expected_query)
    prepared_material = _prepared_receipt_material(
        canonical_payload_sha256=canonical_payload_sha256,
        documents=documents,
        query_spec_sha256=query_spec_sha256,
        receipt_id=receipt_id,
    )
    return _PreparedReceiptV1(
        canonical_payload_sha256=canonical_payload_sha256,
        documents=documents,
        prepared_binding_sha256=canonical_json_sha256_v1(prepared_material),
        query_spec_sha256=query_spec_sha256,
        receipt_id=receipt_id,
        seal=_PREPARED_RECEIPT_SEAL,
    )


def _prepare_loan_geography_receipt_v1(value: Mapping[str, Any]) -> _PreparedReceiptV1:
    """Validate and detach one raw receipt for repeated work in this process."""

    return _receipt(value)


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
    receipt: _PreparedReceiptV1,
    outcome: _PreparedReceiptOutcomeV1,
    snapshot: Mapping[str, Any],
    *,
    require_selected_axis: bool,
) -> dict[str, Any]:
    packet = snapshot["document_packet"]
    ordinal = packet["document_ordinal"]
    page_axis = [item["page_sequence"] for item in snapshot["joined_pages"]]
    if (
        outcome.document_ordinal != ordinal
        or outcome.document_id != packet["document_id"]
        or outcome.document_packet_id != packet["packet_id"]
        or outcome.document_evidence_root_sha256
        != packet.get("document_evidence_root_sha256")
        or (require_selected_axis and page_axis != list(outcome.selected_pages))
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
            "outcome_id": outcome.outcome_id,
            "receipt_id": receipt.receipt_id,
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
    outcomes = {item.document_ordinal: item for item in typed_receipt.documents}
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
            "receipt_id": typed_receipt.receipt_id,
            "source_document_count": len(typed_receipt.documents),
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
    outcome = typed_receipt.documents[ordinal - 1]
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


def _numeric_projection_axes(
    document: Mapping[str, Any],
    document_packet: Mapping[str, Any],
    *,
    document_context: Mapping[str, Any] | None,
) -> tuple[
    dict[str, Any],
    list[Mapping[str, Any]],
    list[Mapping[str, Any]],
    dict[tuple[int, int], Mapping[str, Any]],
    dict[str, Any],
    list[dict[str, Any]],
]:
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
    return overlay, segments, source_segments, locators, unit_context, period_axis


def _local_total_classification(segment: Mapping[str, Any]) -> tuple[str, str | None, str | None]:
    cells = segment.get("trailing_total_cells")
    match = segment.get("trailing_total_match")
    resolution = segment.get("trailing_total_resolution")
    if type(cells) is not list:
        raise _error("Family 11 local total cell axis drifted")
    if len(cells) == 1 and type(match) is dict and resolution is None:
        return "LOCAL_LABELED_TOTAL", cells[0].get("cell_id"), match.get("match_id")
    if (
        len(cells) == 1
        and match is None
        and type(resolution) is dict
        and resolution.get("mode") == "UNLABELED_COMPLETE_NUMERIC_TOTAL_ROW"
    ):
        return (
            "LOCAL_UNLABELED_TOTAL_ROW",
            cells[0].get("cell_id"),
            resolution.get("resolution_id"),
        )
    if not cells and match is None and resolution is None:
        return "STRUCTURALLY_ABSENT", None, None
    raise _error("Family 11 local printed-total lane classification is ambiguous")


def _exact_digest(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise _error(f"Family 11 {label} digest drifted")
    return value


def _exact_ref(value: Any, label: str) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != {"path", "sha256", "size_bytes"}
        or type(value["path"]) is not str
        or not value["path"]
        or type(value["size_bytes"]) is not int
        or value["size_bytes"] <= 0
    ):
        raise _error(f"Family 11 {label} reference drifted")
    _exact_digest(value["sha256"], label)
    return canonical_clone_v1(value)


def _exact_bbox(value: Any, label: str) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int or item < 0 for item in value)
        or not (value[0] < value[2] and value[1] < value[3])
    ):
        raise _error(f"Family 11 {label} bbox drifted")
    return list(value)


def _page_render(value: Any, label: str) -> dict[str, Any]:
    fields = {
        "physical_page",
        "pixel_height",
        "pixel_width",
        "render_sha256",
        "render_size_bytes",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or type(value["physical_page"]) is not int
        or value["physical_page"] <= 0
        or type(value["pixel_height"]) is not int
        or value["pixel_height"] <= 0
        or type(value["pixel_width"]) is not int
        or value["pixel_width"] <= 0
        or type(value["render_size_bytes"]) is not int
        or value["render_size_bytes"] <= 0
    ):
        raise _error(f"Family 11 {label} page-render binding drifted")
    _exact_digest(value["render_sha256"], f"{label} page render")
    return canonical_clone_v1(value)


def _source_locator(value: Any, label: str) -> dict[str, Any]:
    fields = {
        "bbox",
        "crop_ref",
        "page_render",
        "page_sequence",
        "ppocrv6_reader_score",
        "ppocrv6_surface",
        "sample_id",
        "source_line_index",
        "vietocr_transformer_surface",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error(f"Family 11 {label} source locator shape drifted")
    render = _page_render(value["page_render"], label)
    score = value["ppocrv6_reader_score"]
    if (
        type(value["page_sequence"]) is not int
        or value["page_sequence"] <= 0
        or value["page_sequence"] != render["physical_page"]
        or type(value["source_line_index"]) is not int
        or value["source_line_index"] < 0
        or type(value["sample_id"]) is not str
        or not value["sample_id"]
        or type(value["ppocrv6_surface"]) is not str
        or type(value["vietocr_transformer_surface"]) is not str
        or type(score) not in {int, float}
        or not 0 <= score <= 1
    ):
        raise _error(f"Family 11 {label} source locator identity drifted")
    bbox = _exact_bbox(value["bbox"], label)
    if bbox[2] > render["pixel_width"] or bbox[3] > render["pixel_height"]:
        raise _error(f"Family 11 {label} source locator exceeds its render")
    _exact_ref(value["crop_ref"], f"{label} crop")
    return canonical_clone_v1(value)


def _source_locator_id(value: Mapping[str, Any]) -> str:
    return "lgstv1:source-locator:" + canonical_json_sha256_v1(value)


def _request_source_locator_axis(
    document: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    renders = {
        item["physical_page"]: {
            key: canonical_clone_v1(item[key])
            for key in (
                "physical_page",
                "pixel_height",
                "pixel_width",
                "render_sha256",
                "render_size_bytes",
            )
        }
        for item in document["selected_page_bindings"]
    }
    render_axis = [_page_render(renders[page], "request source") for page in sorted(renders)]
    locator_ids = []
    for raw in document["source_line_bindings"]:
        locator = {
            **canonical_clone_v1(raw),
            "page_render": canonical_clone_v1(renders[raw["page_sequence"]]),
        }
        locator_ids.append(_source_locator_id(_source_locator(locator, "request source")))
    if len(locator_ids) != len(set(locator_ids)):
        raise _error("Family 11 request source locators repeat")
    return render_axis, sorted(locator_ids)


def _control_request_id(
    document_binding: Mapping[str, Any], graph_binding: Mapping[str, Any], lane: Mapping[str, Any]
) -> str:
    lane_material = canonical_clone_v1(lane)
    lane_material.pop("control_request_id", None)
    return "lgstv1:total-control-request:" + canonical_json_sha256_v1(
        {
            "document_binding": document_binding,
            "graph_binding": graph_binding,
            "lane": lane_material,
        }
    )


def _validated_total_control_request_set(value: Any) -> dict[str, Any]:
    fields = {
        "authority",
        "claim_boundary",
        "document_binding",
        "family_id",
        "format_version",
        "graph_binding",
        "lane_requests",
        "metrics",
        "request_set_id",
        "source_locator_ids",
        "source_page_render_bindings",
        "state",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error("Family 11 total-control request-set shape drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("request_set_id")
    if identity != "lgstv1:total-control-request-set:" + canonical_json_sha256_v1(material):
        raise _error("Family 11 total-control request-set content identity drifted")
    if (
        value["format_version"] != TOTAL_CONTROL_REQUEST_FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["state"] != _TOTAL_CONTROL_REQUEST_STATE
        or not same_typed_json_v1(value["authority"], _TOTAL_CONTROL_REQUEST_AUTHORITY)
        or value["claim_boundary"] != _TOTAL_CONTROL_REQUEST_CLAIM_BOUNDARY
    ):
        raise _error("Family 11 total-control request-set contract drifted")
    binding = value["document_binding"]
    binding_fields = {
        "document_evidence_root_sha256",
        "document_id",
        "document_ordinal",
        "document_packet_id",
        "source_locator_axis_sha256",
        "source_snapshot_id",
        "source_whole_document_graph_result_id",
    }
    if (
        type(binding) is not dict
        or set(binding) != binding_fields
        or type(binding["document_id"]) is not str
        or not binding["document_id"]
        or type(binding["document_ordinal"]) is not int
        or binding["document_ordinal"] <= 0
        or type(binding["document_packet_id"]) is not str
        or not binding["document_packet_id"]
        or type(binding["source_snapshot_id"]) is not str
        or not binding["source_snapshot_id"].startswith("ffdesv1:")
        or type(binding["source_whole_document_graph_result_id"]) is not str
        or not binding["source_whole_document_graph_result_id"].startswith("lgstv1:document:")
    ):
        raise _error("Family 11 total-control request document binding drifted")
    _exact_digest(binding["document_evidence_root_sha256"], "request document root")
    _exact_digest(binding["source_locator_axis_sha256"], "request source locator axis")
    graph_binding = value["graph_binding"]
    if (
        type(graph_binding) is not dict
        or set(graph_binding) != {"graph_id", "region_fingerprint_sha256", "segment_count"}
        or type(graph_binding["graph_id"]) is not str
        or not graph_binding["graph_id"]
        or type(graph_binding["segment_count"]) is not int
        or graph_binding["segment_count"] <= 0
    ):
        raise _error("Family 11 total-control request graph binding drifted")
    _exact_digest(graph_binding["region_fingerprint_sha256"], "request region fingerprint")
    renders = value["source_page_render_bindings"]
    if type(renders) is not list or not renders:
        raise _error("Family 11 total-control request render axis is empty")
    typed_renders = [_page_render(item, "request") for item in renders]
    if [item["physical_page"] for item in typed_renders] != list(range(1, len(typed_renders) + 1)):
        raise _error("Family 11 total-control request render axis is not the full denominator")
    locator_ids = value["source_locator_ids"]
    if (
        type(locator_ids) is not list
        or locator_ids != sorted(set(locator_ids))
        or canonical_json_sha256_v1(locator_ids) != binding["source_locator_axis_sha256"]
    ):
        raise _error("Family 11 total-control request source locator axis drifted")
    locator_prefix = "lgstv1:source-locator:"
    for locator_id in locator_ids:
        if type(locator_id) is not str or not locator_id.startswith(locator_prefix):
            raise _error("Family 11 total-control request source locator identity drifted")
        _exact_digest(
            locator_id[len(locator_prefix) :],
            "total-control request source locator identity",
        )
    lanes = value["lane_requests"]
    lane_fields = {
        "classification",
        "control_request_id",
        "graph_id",
        "lane_index",
        "local_total_cell_id",
        "local_total_evidence_id",
        "page_sequences",
        "period_end",
        "period_resolution",
        "period_role",
        "segment_id",
        "unit_context",
    }
    if type(lanes) is not list or len(lanes) != graph_binding["segment_count"]:
        raise _error("Family 11 total-control request lane axis drifted")
    periods = []
    for lane_index, lane in enumerate(lanes):
        if (
            type(lane) is not dict
            or set(lane) != lane_fields
            or lane["classification"] not in _TOTAL_CONTROL_CLASSIFICATIONS
            or lane["graph_id"] != graph_binding["graph_id"]
            or lane["lane_index"] != lane_index
            or type(lane["segment_id"]) is not str
            or not lane["segment_id"]
            or type(lane["period_end"]) is not str
            or _iso_period(lane["period_end"]) != lane["period_end"]
            or lane["period_resolution"]
            not in {"LOCAL_EXACT_DATE", "DOCUMENT_INHERITED_EXACT_DATE"}
            or lane["period_role"] not in {"CURRENT", "COMPARATIVE"}
            or type(lane["page_sequences"]) is not list
            or not lane["page_sequences"]
            or lane["page_sequences"] != sorted(set(lane["page_sequences"]))
            or any(
                type(page) is not int or page <= 0 or page > len(typed_renders)
                for page in lane["page_sequences"]
            )
        ):
            raise _error("Family 11 total-control request lane identity drifted")
        unit = lane["unit_context"]
        unit_fields = {
            "currency",
            "evidence_ref",
            "resolution_mode",
            "scale",
            "source_surface",
            "unit_kind",
        }
        if (
            type(unit) is not dict
            or set(unit) != unit_fields
            or unit["unit_kind"] != "MONEY"
            or unit["currency"] != "VND"
            or unit["resolution_mode"] not in {"LOCAL_EXACT_UNIT", "DOCUMENT_INHERITED_EXACT_UNIT"}
            or type(unit["scale"]) is not int
            or unit["scale"] != 6
            or type(unit["evidence_ref"]) is not str
            or not unit["evidence_ref"]
            or type(unit["source_surface"]) is not str
            or not unit["source_surface"]
        ):
            raise _error("Family 11 total-control request lane unit drifted")
        expected_request_id = _control_request_id(binding, graph_binding, lane)
        if lane["classification"] == "STRUCTURALLY_ABSENT":
            if (
                lane["local_total_cell_id"] is not None
                or lane["local_total_evidence_id"] is not None
                or lane["control_request_id"] != expected_request_id
            ):
                raise _error("Family 11 absent total-control request binding drifted")
        elif (
            type(lane["local_total_cell_id"]) is not str
            or not lane["local_total_cell_id"]
            or type(lane["local_total_evidence_id"]) is not str
            or not lane["local_total_evidence_id"]
            or lane["control_request_id"] is not None
        ):
            raise _error("Family 11 local total-control classification binding drifted")
        periods.append(lane["period_end"])
    if len(periods) != len(set(periods)):
        raise _error("Family 11 total-control request periods repeat")
    metrics = value["metrics"]
    expected_counts = {
        classification: sum(lane["classification"] == classification for lane in lanes)
        for classification in sorted(_TOTAL_CONTROL_CLASSIFICATIONS)
    }
    if metrics != {"classification_counts": expected_counts, "lane_count": len(lanes)}:
        raise _error("Family 11 total-control request metrics drifted")
    return canonical_clone_v1(value)


def build_loan_geography_customer_loan_total_control_requests_v1(
    whole_document: Mapping[str, Any],
    document_packet: Mapping[str, Any],
    source_snapshot: Mapping[str, Any],
    *,
    document_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify every exact lane and request controls only for absent local totals."""

    document = _validated_document_envelope(whole_document)
    snapshot = _snapshot(source_snapshot)
    packet = snapshot["document_packet"]
    page_axis = [item["page_sequence"] for item in snapshot["joined_pages"]]
    if (
        not same_typed_json_v1(document_packet, packet)
        or document.get("disposition") != "EXACT_CUSTOMER_LOAN_GEOGRAPHY"
        or document["uniqueness"]["exact_logical_graph_count"] != 1
        or document["evidence_binding"].get("snapshot_id") != snapshot["snapshot_id"]
        or document["evidence_binding"].get("document_packet_id") != packet.get("packet_id")
        or page_axis != list(range(1, packet["page_count"] + 1))
    ):
        raise _error("Family 11 total-control request requires one exact whole-document source")
    overlay, segments, source_segments, _locators, unit_context, period_axis = (
        _numeric_projection_axes(
            document,
            packet,
            document_context=document_context,
        )
    )
    graph = overlay["graphs"][0]
    document_binding = {
        "document_evidence_root_sha256": packet["document_evidence_root_sha256"],
        "document_id": packet["document_id"],
        "document_ordinal": packet["document_ordinal"],
        "document_packet_id": packet["packet_id"],
        "source_locator_axis_sha256": "",
        "source_snapshot_id": snapshot["snapshot_id"],
        "source_whole_document_graph_result_id": document["result_id"],
    }
    render_axis, locator_ids = _request_source_locator_axis(document)
    document_binding["source_locator_axis_sha256"] = canonical_json_sha256_v1(locator_ids)
    graph_binding = {
        "graph_id": graph["graph_id"],
        "region_fingerprint_sha256": canonical_json_sha256_v1(document["region_fingerprint"]),
        "segment_count": len(segments),
    }
    lanes = []
    for segment, source_segment, period in zip(segments, source_segments, period_axis, strict=True):
        classification, cell_id, evidence_id = _local_total_classification(source_segment)
        lane = {
            "classification": classification,
            "control_request_id": None,
            "graph_id": graph["graph_id"],
            "lane_index": segment["period_lane_index"],
            "local_total_cell_id": cell_id,
            "local_total_evidence_id": evidence_id,
            "page_sequences": canonical_clone_v1(segment["page_sequences"]),
            "period_end": period["period_end"],
            "period_resolution": period["resolution_mode"],
            "period_role": period["period_role"],
            "segment_id": segment["segment_id"],
            "unit_context": canonical_clone_v1(unit_context),
        }
        if classification == "STRUCTURALLY_ABSENT":
            lane["control_request_id"] = _control_request_id(document_binding, graph_binding, lane)
        lanes.append(lane)
    counts = {
        classification: sum(lane["classification"] == classification for lane in lanes)
        for classification in sorted(_TOTAL_CONTROL_CLASSIFICATIONS)
    }
    material = {
        "authority": canonical_clone_v1(_TOTAL_CONTROL_REQUEST_AUTHORITY),
        "claim_boundary": _TOTAL_CONTROL_REQUEST_CLAIM_BOUNDARY,
        "document_binding": document_binding,
        "family_id": FAMILY_ID,
        "format_version": TOTAL_CONTROL_REQUEST_FORMAT_VERSION,
        "graph_binding": graph_binding,
        "lane_requests": lanes,
        "metrics": {"classification_counts": counts, "lane_count": len(lanes)},
        "source_locator_ids": locator_ids,
        "source_page_render_bindings": render_axis,
        "state": _TOTAL_CONTROL_REQUEST_STATE,
    }
    return _validated_total_control_request_set(
        {
            **material,
            "request_set_id": "lgstv1:total-control-request-set:"
            + canonical_json_sha256_v1(material),
        }
    )


def validate_loan_geography_customer_loan_total_control_requests_v1(
    value: Any,
) -> dict[str, Any]:
    """Cheap typed handoff gate; source authentication still requires replay."""

    return _validated_total_control_request_set(value)


def validate_loan_geography_customer_loan_total_control_requests_replay_v1(
    value: Any,
    whole_document: Mapping[str, Any],
    document_packet: Mapping[str, Any],
    source_snapshot: Mapping[str, Any],
    *,
    document_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Replay the generic graph and rebuild one whole-document request set exactly."""

    persisted = _validated_total_control_request_set(value)
    document = _validated_document_envelope(whole_document)
    snapshot = _snapshot(source_snapshot)
    validate_accounting_scoped_table_graph_replay_v1(
        document["scoped_table_graph"],
        _region_pages(snapshot)[0],
        LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1,
    )
    rebuilt = build_loan_geography_customer_loan_total_control_requests_v1(
        document,
        document_packet,
        snapshot,
        document_context=document_context,
    )
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("Family 11 total-control request set does not replay exactly")
    return rebuilt


def _content_addressed_result(value: Any, prefix: str, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise _error(f"Family 11 {label} result shape drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id", None)
    if identity != prefix + canonical_json_sha256_v1(material):
        raise _error(f"Family 11 {label} result identity drifted")
    return canonical_clone_v1(value)


def _validated_upstream_total_control(value: Any) -> dict[str, Any]:
    fields = {
        "authority",
        "claim_boundary",
        "document_binding",
        "family_id",
        "format_version",
        "loan_type_graph_result",
        "loan_type_numeric_result",
        "owner_evidence",
        "period_lane",
        "requested_period_end",
        "result_id",
        "state",
        "total_control",
        "unit_evidence",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error("Family 11 upstream customer-loan total control shape drifted")
    control = _content_addressed_result(value, "cltcv1:result:", "upstream total control")
    authority = control["authority"]
    if (
        control["format_version"] != _UPSTREAM_TOTAL_CONTROL_FORMAT_VERSION
        or control["family_id"] != _UPSTREAM_TOTAL_CONTROL_FAMILY_ID
        or control["state"] != _UPSTREAM_TOTAL_CONTROL_STATE
        or type(authority) is not dict
        or authority.get("arithmetic_backsolve_used") is not False
        or authority.get("blank_or_missing_total_imputed_as_zero") is not False
        or authority.get("complete_document_unique_loan_type_graph_required") is not True
        or authority.get("local_exact_period_lane_required") is not True
        or authority.get("local_million_vnd_unit_required") is not True
        or authority.get("ppocrv6_printed_total_authority") is not True
        or authority.get("public_exact_live_replay_required") is not True
    ):
        raise _error("Family 11 upstream customer-loan total control authority drifted")
    resolved_period = _iso_period(control["requested_period_end"])
    if resolved_period is None or control["requested_period_end"].count("/") != 2:
        raise _error("Family 11 upstream customer-loan total period drifted")
    binding = control["document_binding"]
    binding_fields = {
        "document_evidence_root_sha256",
        "document_id",
        "document_ordinal",
        "document_packet_id",
        "line_count",
        "manifest_id",
        "page_count",
        "query_selection_id",
        "snapshot_id",
        "source_pdf_ref",
    }
    if (
        type(binding) is not dict
        or set(binding) != binding_fields
        or type(binding["document_id"]) is not str
        or not binding["document_id"]
        or type(binding["document_ordinal"]) is not int
        or binding["document_ordinal"] <= 0
        or type(binding["document_packet_id"]) is not str
        or not binding["document_packet_id"]
        or type(binding["line_count"]) is not int
        or binding["line_count"] < 0
        or type(binding["page_count"]) is not int
        or binding["page_count"] <= 0
        or type(binding["manifest_id"]) is not str
        or not binding["manifest_id"]
        or (
            binding["query_selection_id"] is not None
            and (
                type(binding["query_selection_id"]) is not str or not binding["query_selection_id"]
            )
        )
        or type(binding["snapshot_id"]) is not str
        or not binding["snapshot_id"].startswith("ffdesv1:")
    ):
        raise _error("Family 11 upstream customer-loan total document binding drifted")
    _exact_digest(binding["document_evidence_root_sha256"], "upstream document root")
    _exact_ref(binding["source_pdf_ref"], "upstream source PDF")
    graph_result = _content_addressed_result(
        control["loan_type_graph_result"], "ltvgv1:result:", "upstream loan-type graph"
    )
    numeric_result = _content_addressed_result(
        control["loan_type_numeric_result"],
        "ltnrrv1:result:",
        "upstream loan-type numeric",
    )
    if numeric_result.get("graph_result_id") != graph_result["result_id"]:
        raise _error("Family 11 upstream graph/numeric source binding drifted")
    owner = control["owner_evidence"]
    period = control["period_lane"]
    unit = control["unit_evidence"]
    total = control["total_control"]
    if (
        type(owner) is not dict
        or set(owner) != {"evidence", "match_kind", "surface"}
        or type(owner["match_kind"]) is not str
        or not owner["match_kind"]
        or type(owner["surface"]) is not str
        or not owner["surface"]
        or type(period) is not dict
        or set(period) != {"evidence", "lane_index", "period_end", "x_center_x2"}
        or period["period_end"] != control["requested_period_end"]
        or type(period["lane_index"]) is not int
        or period["lane_index"] < 0
        or type(period["x_center_x2"]) is not int
        or period["x_center_x2"] < 0
        or type(unit) is not dict
        or set(unit)
        != {
            "currency",
            "lane_index",
            "magnitude_power10",
            "mode",
            "normalized_surface",
            "source",
            "surface",
        }
        or unit["currency"] != "VND"
        or unit["magnitude_power10"] != 6
        or unit["mode"] != "LOCAL_PER_LANE"
        or unit["lane_index"] != period["lane_index"]
        or type(unit["surface"]) is not str
        or not unit["surface"]
        or type(total) is not dict
        or set(total)
        != {
            "accounting_corroboration",
            "lane_index",
            "lane_type",
            "parsed_value",
            "source",
            "status",
        }
        or total["lane_index"] != period["lane_index"]
        or total["lane_type"] != "MONEY"
        or total["status"] != "EXACT_PRINTED_PPOCRV6_TOTAL_CONTROL"
        or type(total["parsed_value"]) is not int
        or total["parsed_value"] < 0
    ):
        raise _error("Family 11 upstream customer-loan total semantic binding drifted")
    locator_groups = (owner["evidence"], period["evidence"])
    if any(type(group) is not list or not group for group in locator_groups):
        raise _error("Family 11 upstream customer-loan total evidence axis drifted")
    for label, group in zip(("owner", "period"), locator_groups, strict=True):
        for locator in group:
            _source_locator(locator, f"upstream {label}")
    unit_source = _source_locator(unit["source"], "upstream unit")
    total_source = _source_locator(total["source"], "upstream total")
    parsed_surface = money_integer_v1(total_source["ppocrv6_surface"])
    check = total["accounting_corroboration"]
    if (
        parsed_surface != total["parsed_value"]
        or unit_source["vietocr_transformer_surface"] != unit["surface"]
        or type(check) is not dict
        or check.get("status") != "EXACT_PP_NUMERIC_EQUATION"
        or check.get("target_total") != total["parsed_value"]
        or check.get("observed_additive_sum") != total["parsed_value"]
    ):
        raise _error("Family 11 upstream customer-loan total source/control drifted")
    graphs = graph_result.get("graphs")
    graph = graphs[0] if type(graphs) is list and len(graphs) == 1 else None
    graph_periods = graph.get("period_axis") if type(graph) is dict else None
    lane_types = graph.get("lane_types") if type(graph) is dict else None
    lane_centers = graph.get("lane_centers_x2") if type(graph) is dict else None
    if (
        type(graph) is not dict
        or graph.get("period_mode") != "LOCAL_EXACT_DATES"
        or type(graph_periods) is not list
        or type(lane_types) is not list
        or type(lane_centers) is not list
        or len(lane_types) != len(lane_centers)
        or any(type(item.get("x_center_x2")) is not int for item in graph_periods)
    ):
        raise _error("Family 11 upstream control typed period/lane axis drifted")
    money_lanes = sorted(
        (index for index, lane_type in enumerate(lane_types) if lane_type == "MONEY"),
        key=lambda index: lane_centers[index],
    )
    ordered_periods = sorted(graph_periods, key=lambda item: item["x_center_x2"])
    requested_positions = [
        index
        for index, item in enumerate(ordered_periods)
        if item.get("period") == control["requested_period_end"]
    ]
    if (
        len(money_lanes) != len(ordered_periods)
        or len(requested_positions) != 1
        or money_lanes[requested_positions[0]] != period["lane_index"]
    ):
        raise _error("Family 11 upstream control period-to-money-lane binding drifted")
    period_matches = (
        [
            item
            for item in graph_periods
            if type(item) is dict
            and item.get("period") == control["requested_period_end"]
            and item.get("x_center_x2") == period["x_center_x2"]
        ]
        if type(graph_periods) is list
        else []
    )
    graph_totals = graph.get("total") if type(graph) is dict else None
    numeric_totals = numeric_result.get("total")
    graph_total_matches = (
        [item for item in graph_totals if item.get("lane_index") == total["lane_index"]]
        if type(graph_totals) is list
        else []
    )
    numeric_total_matches = (
        [item for item in numeric_totals if item.get("lane_index") == total["lane_index"]]
        if type(numeric_totals) is list
        else []
    )
    if (
        len(period_matches) != 1
        or len(graph_total_matches) != 1
        or len(numeric_total_matches) != 1
        or graph_total_matches[0].get("source_line_index") != total_source["source_line_index"]
        or numeric_total_matches[0].get("source_line_index") != total_source["source_line_index"]
        or numeric_total_matches[0].get("parsed_value") != total["parsed_value"]
        or numeric_total_matches[0].get("ppocrv6_surface") != total_source["ppocrv6_surface"]
        or numeric_result.get("page_sequence") != graph.get("page_sequence")
    ):
        raise _error("Family 11 upstream outer/nested total control binding drifted")
    return control


def _upstream_control_locators(control: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        *control["owner_evidence"]["evidence"],
        *control["period_lane"]["evidence"],
        control["unit_evidence"]["source"],
        control["total_control"]["source"],
    ]


def _controls_for_absent_lanes(
    request_set: Mapping[str, Any] | None,
    controls: Sequence[Mapping[str, Any]],
    *,
    document: Mapping[str, Any],
    graph_id: str,
    source_segments: Sequence[Mapping[str, Any]],
    projected_segments: Sequence[Mapping[str, Any]],
    period_axis: Sequence[Mapping[str, Any]],
    unit_context: Mapping[str, Any],
) -> dict[int, tuple[dict[str, Any], dict[str, Any]]]:
    if isinstance(controls, (str, bytes, bytearray)) or not isinstance(controls, Sequence):
        raise _error("Family 11 upstream total controls must be one sequence")
    if request_set is None:
        if controls:
            raise _error("Family 11 upstream total controls lack their request set")
        absent = [
            segment["period_lane_index"]
            for segment in source_segments
            if _local_total_classification(segment)[0] == "STRUCTURALLY_ABSENT"
        ]
        if absent:
            raise _error("Family 11 printed customer-loan total is structurally absent")
        return {}
    request = _validated_total_control_request_set(request_set)
    binding = request["document_binding"]
    evidence = document["evidence_binding"]
    if (
        binding["document_id"] != document["document_id"]
        or binding["document_ordinal"] != document["document_ordinal"]
        or binding["document_packet_id"] != evidence["document_packet_id"]
        or binding["document_evidence_root_sha256"] != evidence["document_evidence_root_sha256"]
        or request["graph_binding"]["graph_id"] != graph_id
        or request["graph_binding"]["region_fingerprint_sha256"]
        != canonical_json_sha256_v1(document["region_fingerprint"])
    ):
        raise _error("Family 11 upstream total request document/root/graph binding drifted")
    if len(request["lane_requests"]) != len(source_segments):
        raise _error("Family 11 upstream total request sparse lane axis drifted")
    absent_lanes = []
    request_by_period = {}
    for source, projected, period, lane_request in zip(
        source_segments,
        projected_segments,
        period_axis,
        request["lane_requests"],
        strict=True,
    ):
        classification, cell_id, evidence_id = _local_total_classification(source)
        expected = {
            "classification": classification,
            "graph_id": graph_id,
            "lane_index": source["period_lane_index"],
            "local_total_cell_id": cell_id,
            "local_total_evidence_id": evidence_id,
            "page_sequences": projected["page_sequences"],
            "period_end": period["period_end"],
            "period_resolution": period["resolution_mode"],
            "period_role": period["period_role"],
            "segment_id": source["segment_id"],
            "unit_context": unit_context,
        }
        if any(lane_request[key] != value for key, value in expected.items()):
            raise _error("Family 11 upstream total request sparse topology drifted")
        if classification == "STRUCTURALLY_ABSENT":
            absent_lanes.append(source["period_lane_index"])
            request_by_period[period["period_end"]] = lane_request
    typed_controls = [_validated_upstream_total_control(item) for item in controls]
    control_ids = [item["result_id"] for item in typed_controls]
    control_periods = [_iso_period(item["requested_period_end"]) for item in typed_controls]
    if (
        len(control_ids) != len(set(control_ids))
        or len(control_periods) != len(set(control_periods))
        or set(control_periods) != set(request_by_period)
        or len(typed_controls) != len(absent_lanes)
    ):
        raise _error("Family 11 upstream total controls are missing, duplicate, or unused")
    locator_ids = set(request["source_locator_ids"])
    result = {}
    for control, resolved_period in zip(typed_controls, control_periods, strict=True):
        lane_request = request_by_period[resolved_period]
        control_binding = control["document_binding"]
        if (
            control_binding["document_id"] != binding["document_id"]
            or control_binding["document_ordinal"] != binding["document_ordinal"]
            or control_binding["document_packet_id"] != binding["document_packet_id"]
            or control_binding["document_evidence_root_sha256"]
            != binding["document_evidence_root_sha256"]
            or control_binding["snapshot_id"] != binding["source_snapshot_id"]
            or any(
                _source_locator_id(locator) not in locator_ids
                for locator in _upstream_control_locators(control)
            )
        ):
            raise _error("Family 11 upstream total control source snapshot/locator drifted")
        result[lane_request["lane_index"]] = (lane_request, control)
    return result


def project_loan_geography_numeric_input_v1(
    document: Mapping[str, Any],
    document_packet: Mapping[str, Any],
    *,
    document_context: Mapping[str, Any] | None = None,
    upstream_total_control_requests: Mapping[str, Any] | None = None,
    upstream_total_control_source_document: Mapping[str, Any] | None = None,
    upstream_total_control_source_snapshot: Mapping[str, Any] | None = None,
    upstream_total_controls: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Project role x period cells and printed totals; never parse a number.

    Local exact dates/units are preferred.  Missing context may be inherited
    only from the typed, replayed full-PDF period/unit context.  Document-packet
    period/year metadata never supplies an evidence ref or source surface.
    """

    document = _validated_document_envelope(document)
    if upstream_total_control_requests is not None:
        if (
            upstream_total_control_source_document is None
            or upstream_total_control_source_snapshot is None
        ):
            raise _error("Family 11 upstream total request lacks its exact full-document source")
        upstream_total_control_requests = (
            validate_loan_geography_customer_loan_total_control_requests_replay_v1(
                upstream_total_control_requests,
                upstream_total_control_source_document,
                document_packet,
                upstream_total_control_source_snapshot,
                document_context=document_context,
            )
        )
        from scripts.experiments.customer_loan_total_control_v1 import (
            validate_customer_loan_total_control_replay_v1,
        )

        replayed_controls = []
        for control in upstream_total_controls:
            requested_period = (
                control.get("requested_period_end") if type(control) is dict else None
            )
            try:
                replayed_controls.append(
                    validate_customer_loan_total_control_replay_v1(
                        control,
                        upstream_total_control_source_snapshot,
                        requested_period,
                    )
                )
            except (RuntimeError, ValueError) as exc:
                raise _error(
                    "Family 11 upstream customer-loan total control did not publicly replay"
                ) from exc
        upstream_total_controls = tuple(replayed_controls)
    elif (
        upstream_total_control_source_document is not None
        or upstream_total_control_source_snapshot is not None
    ):
        raise _error("Family 11 unused upstream total-control source was supplied")
    overlay, segments, source_segments, locators, unit_context, period_axis = (
        _numeric_projection_axes(
            document,
            document_packet,
            document_context=document_context,
        )
    )
    logical = overlay["graphs"]
    controls_by_lane = _controls_for_absent_lanes(
        upstream_total_control_requests,
        upstream_total_controls,
        document=document,
        graph_id=logical[0]["graph_id"],
        source_segments=source_segments,
        projected_segments=segments,
        period_axis=period_axis,
        unit_context=unit_context,
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

    def upstream_total_cell(
        source_segment: Mapping[str, Any],
        lane_index: int,
        lane_request: Mapping[str, Any],
        control: Mapping[str, Any],
    ) -> dict[str, Any]:
        source = control["total_control"]["source"]
        locator_id = _source_locator_id(source)
        identity_material = {
            "control_request_id": lane_request["control_request_id"],
            "control_result_id": control["result_id"],
            "graph_id": logical[0]["graph_id"],
            "lane_index": lane_index,
            "role": "PRINTED_CUSTOMER_LOAN_TOTAL",
            "segment_id": source_segment["segment_id"],
            "source_locator_id": locator_id,
        }
        return {
            "bbox": canonical_clone_v1(source["bbox"]),
            "cell_id": "lgstv1:upstream-total-cell:" + canonical_json_sha256_v1(identity_material),
            "crop_sha256": source["crop_ref"]["sha256"],
            "lane_index": lane_index,
            "lane_type": "MONEY",
            "page_sequence": source["page_sequence"],
            "ppocrv6_score": float(source["ppocrv6_reader_score"]),
            "ppocrv6_surface": source["ppocrv6_surface"],
            "sample_id": source["sample_id"],
            "source_line_index": source["source_line_index"],
            "vietocr_surface": source["vietocr_transformer_surface"],
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
        classification, _local_cell_id, _local_evidence_id = _local_total_classification(segment)
        if classification == "LOCAL_LABELED_TOTAL":
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
            control_page_sequence = segment["page_sequences"][0]
            projected_total_cell = cell(
                segment["trailing_total_cells"][0], lane, "PRINTED_CUSTOMER_LOAN_TOTAL"
            )
            upstream_evidence = {}
        elif classification == "LOCAL_UNLABELED_TOTAL_ROW":
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
            control_page_sequence = segment["page_sequences"][0]
            projected_total_cell = cell(
                segment["trailing_total_cells"][0], lane, "PRINTED_CUSTOMER_LOAN_TOTAL"
            )
            upstream_evidence = {}
        else:
            bound = controls_by_lane.get(lane)
            if bound is None:
                raise _error("Family 11 structurally absent printed total lacks upstream control")
            lane_request, control = bound
            source = control["total_control"]["source"]
            locator_id = _source_locator_id(source)
            evidence_refs = [f"line:{source['page_sequence']}:{source['source_line_index']}"]
            source_bboxes = [canonical_clone_v1(source["bbox"])]
            source_line_indices = [source["source_line_index"]]
            source_surfaces = [source["vietocr_transformer_surface"]]
            label_ref = control["result_id"]
            label_surface = None
            resolution_mode = _UPSTREAM_TOTAL_CONTROL_MODE
            row_bbox = canonical_clone_v1(source["bbox"])
            control_page_sequence = source["page_sequence"]
            projected_total_cell = upstream_total_cell(segment, lane, lane_request, control)
            upstream_evidence = {
                "control_request_id": lane_request["control_request_id"],
                "control_result_id": control["result_id"],
                "request_set_id": upstream_total_control_requests["request_set_id"],
                "source_control_graph_result_id": control["loan_type_graph_result"]["result_id"],
                "source_control_numeric_result_id": control["loan_type_numeric_result"][
                    "result_id"
                ],
                "source_document_graph_result_id": upstream_total_control_requests[
                    "document_binding"
                ]["source_whole_document_graph_result_id"],
                "source_graph_id": logical[0]["graph_id"],
                "source_locator": canonical_clone_v1(source),
                "source_locator_id": locator_id,
                "source_segment_id": segment["segment_id"],
                "source_snapshot_id": control["document_binding"]["snapshot_id"],
            }
        total_cells.append(projected_total_cell)
        total_refs.append(label_ref)
        total_surfaces.append(label_surface)
        total_control_evidence.append(
            {
                "evidence_refs": evidence_refs,
                "label_evidence_ref": label_ref,
                "label_surface": label_surface,
                "lane_index": lane,
                "page_sequence": control_page_sequence,
                "resolution_mode": resolution_mode,
                "row_bbox": row_bbox,
                "source_bboxes": source_bboxes,
                "source_line_indices": source_line_indices,
                "source_surfaces_raw_nfc": source_surfaces,
                **upstream_evidence,
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
