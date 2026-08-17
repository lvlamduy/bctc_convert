"""Bank-blind variable graph for customer-loan enterprise/population tables.

This family is not one fixed row template.  The common graph admits a flat
legal-form table, a reduced legal-form subset, a two-money-lane table with a
visible dash, and a grouped presentation whose source-only population parents
close to a core subtotal before an optional margin/advance row and grand total.

The implementation deliberately reuses the already-falsified variable-table
mechanics from the loan-industry family.  Only the declarative family anchors,
roles, boundaries, and identity contract differ.  Bank, filename, note, and
page are never available to matching.  Fresh VietOCR text is anchor evidence;
pixels, numeric truth, schema mapping, and final acceptance remain downstream.
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "LoanEnterpriseVariantGraphV1Error",
    "build_loan_enterprise_variant_graph_document_v1",
    "validate_loan_enterprise_variant_graph_replay_v1",
]


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "LOAN_ENTERPRISE_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "LOAN_ENTERPRISE_OR_CUSTOMER_TYPE_CLASSIFICATION"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_CUSTOMER_LOAN_ENTERPRISE_OR_CUSTOMER_"
    "TYPE_VARIABLE_STRUCTURE_GEOMETRY_PERIOD_UNIT_TOTAL_AND_ACCOUNTING_PROPOSAL_"
    "CORROBORATION_ONLY_TEXT_IS_ANCHOR_NO_SOURCE_NUMERIC_SCHEMA_MAPPING_"
    "CANONICALIZATION_OR_EXPORT_AUTHORITY"
)

_BRANCH_ALIASES = (
    "Phân tích dư nợ cho vay theo đối tượng khách hàng và theo loại hình doanh nghiệp",
    "Phân tích dư nợ cho vay theo đối tượng khách hàng và loại hình doanh nghiệp",
    "Phân tích dư nợ cho vay theo đối tượng khách hàng",
    "Phân tích dư nợ theo đối tượng khách hàng và theo loại hình doanh nghiệp",
    "Phân tích dư nợ theo đối tượng khách hàng và loại hình doanh nghiệp",
    "Phân tích dư nợ theo đối tượng khách hàng, loại hình doanh nghiệp",
    "Phân tích dư nợ theo đối tượng khách hàng",
    "Phân tích dư nợ theo loại hình doanh nghiệp",
)

# This is the union of source-visible roles across the fixed PDFs.  The aliases
# are presentation variants of accounting roles, not bank routes.  One role is
# a population row.  It is not one legal-form child of schema parent 766, but
# the universal schema already contains the exact cross-family concept 6058.
_ROLE_ALIASES: dict[str, tuple[str, ...]] = {
    "STATE_ENTERPRISE": (
        "Công ty Nhà nước",
        "Công ty nhà nước",
        "Doanh nghiệp Nhà nước",
        "Doanh nghiệp nhà nước",
    ),
    "STATE_OWNED_SINGLE_MEMBER_LLC": (
        "Công ty TNHH MTV Vốn Nhà nước 100%",
        "Công ty TNHH MTV do Nhà nước sở hữu 100% vốn điều lệ",
        "Công ty TNHH 1 thành viên do Nhà nước sở hữu 100% vốn điều lệ",
    ),
    "STATE_CONTROLLED_MULTI_MEMBER_LLC": (
        "Công ty TNHH trên 1 Thành viên vốn Nhà nước lớn hơn 50%",
        "Công ty TNHH 2 thành viên trở lên có phần vốn góp của Nhà nước trên 50% vốn điều lệ hoặc Nhà nước giữ quyền chi phối",
    ),
    "OTHER_LLC": (
        "Công ty TNHH khác",
        "Công ty trách nhiệm hữu hạn khác",
    ),
    "STATE_CONTROLLED_JOINT_STOCK": (
        "Công ty Cổ phần Vốn Nhà nước > 50% Nhà nước chiếm cổ phần chi phối",
        "Công ty cổ phần có vốn góp của Nhà nước trên 50% vốn điều lệ hoặc tổng số cổ phần có quyền biểu quyết hoặc Nhà nước giữ quyền chi phối trong Điều lệ của công ty",
        "Công ty cổ phần có vốn cổ phần của nhà nước chiếm trên 50% vốn điều lệ hoặc tổng số cổ phần có quyền biểu quyết hoặc nhà nước giữ quyền chi phối đối với công ty trong Điều lệ của công ty",
    ),
    "OTHER_JOINT_STOCK": ("Công ty cổ phần khác",),
    "PARTNERSHIP": ("Công ty hợp danh",),
    "PRIVATE_ENTERPRISE": ("Doanh nghiệp tư nhân",),
    "FOREIGN_INVESTED_ENTERPRISE": (
        "Doanh nghiệp có vốn đầu tư nước ngoài",
        "Công ty vốn nước ngoài",
    ),
    "COOPERATIVE": (
        "Hợp tác xã và liên hiệp hợp tác xã",
        "Hợp tác xã và Liên hiệp Hợp tác xã",
    ),
    "COOPERATIVE_AND_PRIVATE_ENTERPRISE_COMBINED": (),
    "HOUSEHOLD_INDIVIDUAL": ("Hộ kinh doanh, cá nhân",),
    "ADMIN_PUBLIC_ASSOCIATION": (
        "Đơn vị hành chính sự nghiệp, Đoàn thể và hiệp hội",
        "Đơn vị hành chính sự nghiệp, Đảng, đoàn thể và hiệp hội",
        "Đơn vị hành chính sự nghiệp, đảng, đoàn thể và hiệp hội",
    ),
    "OTHER": ("Khác", "Thành phần kinh tế khác"),
    "MARGIN_AND_SECURITIES_ADVANCE": (
        "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
        "Cho vay giao dịch ký quỹ và ứng trước cho khách hàng",
        "Các khoản cho vay margin chứng khoán và ứng trước khách hàng tại MBS",
        "Các khoản cho vay margin chứng khoán và ứng trước khách hàng",
    ),
    "FOREIGN_BRANCH_LOANS_SOURCE_ONLY": ("Cho vay tại Chi nhánh và ngân hàng con nước ngoài",),
}

_SCHEMA_ELIGIBLE_ROLES = tuple(_ROLE_ALIASES)
# A recognized family parent plus one distinctive child is the smallest useful
# locator.  The shared engine exhausts every parent+child and child+child pair
# across the complete PDF before considering triples.  This changes only
# discovery: the accepted graph still retains every visible row, axis, unit,
# total, geometry and accounting check.
_MIN_SCHEMA_ROLE_COUNT = 1
_PARENT_ANCHOR_KEY = "PARENT:LOAN_ENTERPRISE_OR_CUSTOMER_TYPE_CLASSIFICATION"
_BOUNDARY_PREFIXES = (
    "phan tich chat luong",
    "phan tich du no cho vay theo chat luong",
    "phan tich du no theo thoi",
    "phan tich du no cho vay theo thoi",
    "phan tich du no cho vay theo nganh",
    "phan tich du no theo nganh",
    "du phong rui ro cho vay khach hang",
    "tien gui cua khach hang",
)
_EXTENDED_ROLE_ALIASES: dict[str, tuple[str, ...]] = {
    # Some filings print the legal form without an ``khác`` qualifier.  The
    # state-controlled forms remain separate explicit roles, so these broad
    # labels are the non-state residual legal-form leaves rather than a
    # bank-specific rewrite.
    "OTHER_LLC": ("Công ty trách nhiệm hữu hạn", "Công ty TNHH"),
    "STATE_CONTROLLED_MULTI_MEMBER_LLC": ("Công ty TNHH MTV trở lên có vốn Nhà nước trên 50%",),
    "STATE_CONTROLLED_JOINT_STOCK": (
        "Công ty cổ phần vốn Nhà nước trên 50%",
        "Công ty cổ phần có vốn góp của Nhà nước trên 50% vốn điều lệ hoặc tổng số cổ phần có quyền biểu quyết; hoặc Nhà nước giữ quyền chi phối trong Điều lệ của công ty",
    ),
    "OTHER_JOINT_STOCK": ("Công ty cổ phần",),
    "HOUSEHOLD_INDIVIDUAL": ("Cá nhân và hộ kinh doanh cá thể",),
    "ADMIN_PUBLIC_ASSOCIATION": ("Dịch vụ hành chính sự nghiệp, đoàn thể và hiệp hội",),
    "FOREIGN_BRANCH_LOANS_SOURCE_ONLY": (
        "Dư nợ tại tại chi nhánh và ngân hàng con nước ngoài",
        "Dư nợ tại chi nhánh và ngân hàng con nước ngoài",
    ),
    "MARGIN_AND_SECURITIES_ADVANCE": (
        "Các khoản cho vay giao dịch ký quỹ và ứng trước cho khách hàng",
    ),
    "COOPERATIVE_AND_PRIVATE_ENTERPRISE_COMBINED": ("Hợp tác xã và công ty tư nhân",),
}
_EXTENDED_BOUNDARY_PREFIXES = (
    # A separately headed credit population may immediately follow the
    # customer-loan enterprise table and repeat some legal-form children.  It
    # must terminate the first population instead of creating duplicate roles.
    "nghiep vu phat hanh thu tin dung tra cham",
)
_EXTENDED_BRANCH_ALIASES: tuple[str, ...] = ()
_SAFETY = {
    "bank_filename_note_or_page_used_for_inference": False,
    "blank_or_missing_companion_cells_imputed_as_zero": False,
    "complete_pdf_region_enumeration_required": True,
    "fresh_vietocr_transformer_text_required": True,
    "grouped_and_flat_presentations_share_one_role_graph": True,
    "legacy_ocr_used_for_semantic_anchors": False,
    "mapping_authority": False,
    "minimum_child_anchor_count_with_recognized_parent": _MIN_SCHEMA_ROLE_COUNT,
    "minimum_total_anchor_combination_size": 2,
    "numeric_authority": False,
    "optional_rows_required_to_keep_fixed_order": False,
    "parent_precedes_descendants_required": True,
    "pair_combinations_exhausted_before_triples": True,
    "percentage_companion_lanes_preserved": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "qwen_or_gemma_used_for_semantic_anchors": False,
    "sibling_child_order_fixed": False,
    "source_population_role_may_map_to_dedicated_cross_family_schema_item": True,
    "text_similarity_alone_can_accept": False,
    "whole_pdf_uniqueness_required": True,
}
_RESULT_FIELDS = {
    "claim_boundary",
    "family_id",
    "format_version",
    "graphs",
    "metrics",
    "near_regions",
    "result_id",
    "safety",
    "status",
    "uniqueness",
}


class LoanEnterpriseVariantGraphV1Error(ValueError):
    """The enterprise family config, complete PDF, or graph drifted."""


def _error(message: str) -> LoanEnterpriseVariantGraphV1Error:
    return LoanEnterpriseVariantGraphV1Error(message)


def _variable_population_engine() -> ModuleType:
    """Load a private instance of the proven variable-table mechanics."""

    path = PROJECT_ROOT / "scripts/experiments/loan_industry_variant_graph_v1.py"
    spec = importlib.util.spec_from_file_location(
        "loan_enterprise_variable_population_engine_v1", path
    )
    if spec is None or spec.loader is None:
        raise _error(f"cannot load variable-population graph engine: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    # This module instance is private to one build call.  Rebinding declarative
    # family data cannot affect E-0055 or another concurrent imported module.
    module._BRANCH_ALIASES = _BRANCH_ALIASES
    module._ROLE_ALIASES = _ROLE_ALIASES
    module._SCHEMA_ELIGIBLE_ROLES = _SCHEMA_ELIGIBLE_ROLES
    module._MIN_SCHEMA_ROLE_COUNT = _MIN_SCHEMA_ROLE_COUNT
    module._PARENT_ANCHOR_KEY = _PARENT_ANCHOR_KEY
    module._MAX_LABEL_WIDTH = 5
    module._MAX_OWNER_TABLE_LINE_SPAN = 180
    module._BOUNDARY_PREFIXES = _BOUNDARY_PREFIXES
    module._EXTENDED_BRANCH_ALIASES = _EXTENDED_BRANCH_ALIASES
    module._EXTENDED_BOUNDARY_PREFIXES = _EXTENDED_BOUNDARY_PREFIXES
    module._EXTENDED_ROLE_ALIASES = _EXTENDED_ROLE_ALIASES
    return module


def _enterprise_graphs(
    pages: Sequence[Mapping[str, Any]],
    *,
    enable_extended_reporting_period_variants: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    engine = _variable_population_engine()
    # The longest observed generic legal-form label wraps to six source lines.
    # Keep the historical five-line limit for the base profile and widen only
    # when the caller enables the reporting-period/layout variants.
    engine._MAX_LABEL_WIDTH = 6 if enable_extended_reporting_period_variants else 5
    try:
        normalized_pages = engine._pages(pages)
        graphs, near = engine._scan(
            normalized_pages,
            enable_extended_annual_variants=enable_extended_reporting_period_variants,
        )
        engine._attach_minimal_anchor_resolution(graphs, near)
    except Exception as exc:
        raise _error(f"variable-population graph engine rejected input: {exc}") from exc
    for graph in graphs:
        graph["branch"]["schema_concept"] = "PHAN_TICH_THEO_LOAI_HINH_DOANH_NGHIEP"
    for diagnostic in near:
        diagnostic["unresolved_reasons"] = [
            reason.replace("LOAN_INDUSTRY", "LOAN_ENTERPRISE")
            for reason in diagnostic["unresolved_reasons"]
        ]
    return canonical_clone_v1(graphs), canonical_clone_v1(near)


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("loan-enterprise graph result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["graphs"]) is not list
        or type(value["near_regions"]) is not list
    ):
        raise _error("loan-enterprise graph identity/safety drifted")
    count = len(value["graphs"])
    expected_status = (
        "ACCEPTED_UNIQUE_VARIANT_GRAPH"
        if count == 1
        else "UNRESOLVED_NO_COMPLETE_REGION"
        if count == 0
        else "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
    )
    expected_uniqueness = {
        "full_match_count": count,
        "status": (
            "UNIQUE_FULL_MATCH"
            if count == 1
            else "NO_FULL_MATCH"
            if count == 0
            else "AMBIGUOUS_MULTIPLE_FULL_MATCHES"
        ),
    }
    expected_metrics = {
        "complete_branch_table_region_count": count,
        "near_region_count": len(value["near_regions"]),
        "semantic_accounting_corroborated_lane_count": sum(
            check.get("status") == "CORROBORATED_SEMANTIC_PROPOSAL_ONLY"
            for graph in value["graphs"]
            for check in graph.get("accounting_checks", [])
        ),
        "structurally_resolved_graph_count": sum(
            graph.get("status") == "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED"
            for graph in value["graphs"]
        ),
    }
    if (
        value["status"] != expected_status
        or not same_typed_json_v1(value["uniqueness"], expected_uniqueness)
        or not same_typed_json_v1(value["metrics"], expected_metrics)
    ):
        raise _error("loan-enterprise graph status/metrics drifted")
    for graph in value["graphs"]:
        if (
            type(graph) is not dict
            or graph.get("status") != "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED"
            or type(graph.get("branch")) is not dict
            or graph["branch"].get("schema_concept") != "PHAN_TICH_THEO_LOAI_HINH_DOANH_NGHIEP"
            or type(graph.get("customer_loan_context")) is not dict
            or type(graph.get("rows")) is not list
            or len([row for row in graph["rows"] if row.get("role") in _SCHEMA_ELIGIBLE_ROLES])
            < _MIN_SCHEMA_ROLE_COUNT
            or type(graph.get("anchor_resolution")) is not dict
            or set(graph["anchor_resolution"])
            != {
                "anchor_search_scope",
                "child_priority_basis",
                "matching_region_count",
                "pair_combinations_exhausted_before_triples",
                "selected_anchor_keys",
                "selected_size",
                "status",
            }
            or type(graph.get("total")) is not list
            or not graph["total"]
            or type(graph.get("context_complete")) is not bool
            or graph["context_complete"] is not (not graph.get("unresolved_reasons"))
        ):
            raise _error("loan-enterprise graph payload drifted")
        roles = [row.get("role") for row in graph["rows"]]
        if len(roles) != len(set(roles)) or any(role not in _ROLE_ALIASES for role in roles):
            raise _error("loan-enterprise graph role axis drifted")
        resolution = graph["anchor_resolution"]
        if (
            resolution["anchor_search_scope"]
            != "ALL_COMPLETE_AND_NEAR_BRANCH_REGIONS_IN_FULL_DOCUMENT"
            or resolution["child_priority_basis"] != "SEMANTIC_MONEY_MAGNITUDE_DISCOVERY_ONLY"
            or resolution["pair_combinations_exhausted_before_triples"] is not True
            or type(resolution["matching_region_count"]) is not int
            or resolution["matching_region_count"] <= 0
            or type(resolution["selected_anchor_keys"]) is not list
            or any(type(item) is not str or not item for item in resolution["selected_anchor_keys"])
            or (
                resolution["selected_size"] is not None
                and (
                    type(resolution["selected_size"]) is not int
                    or resolution["selected_size"] not in {2, 3}
                    or resolution["selected_size"] != len(resolution["selected_anchor_keys"])
                )
            )
            or resolution["status"]
            not in {
                "UNIQUE_MINIMAL_ANCHOR_COMBINATION",
                "UNRESOLVED_NO_UNIQUE_ANCHOR_COMBINATION",
            }
        ):
            raise _error("loan-enterprise minimal anchor resolution drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "levgv1:result:" + canonical_json_sha256_v1(material):
        raise _error("loan-enterprise graph result identity drifted")
    return canonical_clone_v1(value)


def build_loan_enterprise_variant_graph_document_v1(
    pages: Sequence[Mapping[str, Any]],
    *,
    enable_extended_reporting_period_variants: bool = False,
) -> dict[str, Any]:
    """Enumerate every complete enterprise/customer-type region in one PDF."""

    graphs, near = _enterprise_graphs(
        pages,
        enable_extended_reporting_period_variants=(enable_extended_reporting_period_variants),
    )
    count = len(graphs)
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "graphs": graphs,
        "metrics": {
            "complete_branch_table_region_count": count,
            "near_region_count": len(near),
            "semantic_accounting_corroborated_lane_count": sum(
                check.get("status") == "CORROBORATED_SEMANTIC_PROPOSAL_ONLY"
                for graph in graphs
                for check in graph.get("accounting_checks", [])
            ),
            "structurally_resolved_graph_count": sum(
                graph.get("status") == "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED" for graph in graphs
            ),
        },
        "near_regions": near,
        "safety": canonical_clone_v1(_SAFETY),
        "status": (
            "ACCEPTED_UNIQUE_VARIANT_GRAPH"
            if count == 1
            else "UNRESOLVED_NO_COMPLETE_REGION"
            if count == 0
            else "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
        ),
        "uniqueness": {
            "full_match_count": count,
            "status": (
                "UNIQUE_FULL_MATCH"
                if count == 1
                else "NO_FULL_MATCH"
                if count == 0
                else "AMBIGUOUS_MULTIPLE_FULL_MATCHES"
            ),
        },
    }
    return _validate_result(
        {**material, "result_id": "levgv1:result:" + canonical_json_sha256_v1(material)}
    )


def validate_loan_enterprise_variant_graph_replay_v1(
    value: Any,
    pages: Sequence[Mapping[str, Any]],
    *,
    enable_extended_reporting_period_variants: bool = False,
) -> dict[str, Any]:
    """Exact-rebuild an enterprise graph from the complete document line axis."""

    persisted = _validate_result(value)
    rebuilt = build_loan_enterprise_variant_graph_document_v1(
        pages,
        enable_extended_reporting_period_variants=(enable_extended_reporting_period_variants),
    )
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("loan-enterprise graph does not replay exactly")
    return rebuilt
