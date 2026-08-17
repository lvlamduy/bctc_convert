"""Verify annual-2025 investment-property movements for eight banks.

The complete-PDF matcher remains bank/page blind.  Bank and page identifiers
appear only in the post-selection evidence ledger.  ACB's two sibling source
tables are combined through the same controlled visible-cell aggregation used
for any split family presentation; no bank-specific matcher or pixel constant
is introduced.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "ANNUAL_2025_INVESTMENT_PROPERTY_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_INVESTMENT_PROPERTY_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_INVESTMENT_PROPERTY_8BANK_BOUNDED_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025ip8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_INVESTMENT_PROPERTY_CODEX_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025ip8bcv1:pixel-review:"
REVIEW_PATH = Path(
    "docs/experiments/E-0126-annual-2025-investment-property-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0126-annual-2025-investment-property-8bank-codex-verified-mapping-v1.json"
)
SEMANTIC_INDEX_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/verified-index/"
    "semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = "98bb9854e699230da86538cf024ef3f4817b9e2f4dd2b2a75f46198f00e4247d"
EXPECTED_CROP_MANIFEST_SHA256 = "17d12a4d6b1dfaf0e243300757fd225b8c9cca80810a2d856efdb55a5b4ac000"
EXPECTED_AXIS_SHA256 = "aa81f553fda69315e84b7adbda13347c25a4490b016fc9660ff4f2cd49795ce7"
EXPECTED_SCAN_ID = (
    "a2025ipfdsv1:scan:a15588de717baef8f955789ae53c136eebff2453090a27127439819376df5492"
)
SCAN_FORMAT = "ANNUAL_2025_INVESTMENT_PROPERTY_8DOCUMENT_STRUCTURE_SCAN_V1"
SCAN_ID_PREFIX = "a2025ipfdsv1:scan:"

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_"
    "VIETOCR_BANK_BLIND_REPORTING_PERIOD_GENERAL_INVESTMENT_PROPERTY_"
    "VARIANT_GRAPH_VISIBLE_PIXEL_UPSTREAM_PPOCRV6_NUMERIC_AXIS_"
    "GEOMETRY_DERIVED_DASH_CONTROLLED_SIBLING_TABLE_AGGREGATION_ACCOUNTING_"
    "AND_FAMILY_LOCAL_STABLE_TM_SCHEMA_BINDING_ONLY_NO_EXPORT_AUTHORITY"
)
_REVIEW_CHECKS = (
    "COMPLETE_PDF_UNIQUE_REGION_OR_BOUND_REPORT_ABSENCE",
    "OWNER_PRECEDES_COST_DEPRECIATION_AND_CARRYING_BRANCHES",
    "LATEST_EXPLICIT_LOCAL_REPORTING_PERIOD_SELECTED",
    "OPTIONAL_SIBLING_SOURCE_TABLES_AGGREGATED_ONCE",
    "ASSET_CLASS_COLUMNS_AND_TOTALS_BOUND",
    "MILLION_VND_UNIT_VISIBLE",
    "VISIBLE_PIXEL_LABELS_DIGITS_SIGNS_AND_DASHES",
    "UPSTREAM_PPOCRV6_NUMERIC_AXIS_MATCHES_VISIBLE_PIXEL",
    "DASH_CELL_NORMALIZED_TO_ACCOUNTING_ZERO",
    "OPENING_PLUS_MOVEMENTS_EQUALS_CLOSING",
    "COST_MINUS_DEPRECIATION_EQUALS_CARRYING_VALUE",
    "LIVE_TM_SCHEMA_ID_NAME_AND_PARENT_COMPATIBILITY",
)
_REVIEW_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "comparison_period_used_as_mapping_authority": False,
    "fresh_vietocr_used_as_numeric_truth": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": "VISIBLE_PDF_PIXELS_WITH_UPSTREAM_PPOCRV6_AND_ACCOUNTING",
    "reporting_period_dates_derived_from_pdf_not_fixed_calendar_constants": True,
    "sibling_source_tables_aggregated_only_after_independent_cell_verification": True,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "comparison_period_used_as_mapping_authority": False,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "gemma_json_used_as_mapping_or_numeric_authority": False,
    "independent_pdf_pixel_and_upstream_ppocrv6_used_for_numeric_truth": True,
    "live_tm_schema_id_name_and_parent_checked": True,
    "mapping_authority_bounded_to_two_unique_annual_investment_property_regions": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "reporting_period_dates_derived_from_pdf": True,
    "sibling_source_tables_aggregated_once_with_component_evidence": True,
    "text_similarity_alone_used_for_mapping": False,
}

_BOUNDARIES = {
    "VPB": (
        (54, "tai san co dinh vo hinh", "Tài sản cố định vô hình"),
        (55, "tai san co khac", "TÀI SẢN CÓ KHÁC"),
    ),
    "HDB": (
        (42, "tai san co dinh vo hinh", "TÀI SẢN CỐ ĐỊNH VÔ HÌNH"),
        (42, "tai san co khac", "TÀI SẢN CÓ KHÁC"),
    ),
    "VCB": (
        (49, "tai san co dinh vo hinh", "Tài sản cố định vô hình"),
        (50, "tai san co khac", "Tài sản có khác"),
    ),
    "CTG": (
        (49, "tai san co dinh vo hinh", "TÀI SẢN CỐ ĐỊNH VÔ HÌNH"),
        (50, "tai san co khac", "TÀI SẢN CÓ KHÁC"),
    ),
    "BID": (
        (48, "tai san co dinh vo hinh", "Tài sản cố định vô hình"),
        (49, "tai san co khac", "TÀI SẢN CÓ KHÁC"),
    ),
    "VIB": (
        (43, "tai san co dinh vo hinh", "TÀI SẢN CỐ ĐỊNH VÔ HÌNH"),
        (44, "tai san co khac", "TÀI SẢN CÓ KHÁC"),
    ),
}
_EXPECTED_IDS = {
    "ACB": {944, 948, 952, 955, 957, 958, 965, 5973, 5974},
    "MBB": {944, 6002, 6003, 955, 957, 6005, 965, 5973, 5974},
    "VPB": set(),
    "HDB": set(),
    "VCB": set(),
    "CTG": set(),
    "BID": set(),
    "VIB": set(),
}


class Annual2025InvestmentProperty8BankError(ValueError):
    """Annual investment-property evidence or replay drifted."""


def _error(message: str) -> Annual2025InvestmentProperty8BankError:
    return Annual2025InvestmentProperty8BankError(message)


def _load_module(name: str, relative_path: str) -> ModuleType:
    path = PROJECT_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual investment-property support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _present_document(
    base: ModuleType,
    *,
    code: str,
    page: int,
    owner_line: int,
    owner_text: str,
    axes: Sequence[tuple[int, str]],
    branches: Sequence[tuple[int, str, str]],
    mappings: Sequence[dict[str, Any]],
    equations: Sequence[dict[str, Any]],
    comparison: dict[str, Any] | None,
    unit_authority: str,
) -> dict[str, Any]:
    return {
        "absence_reason": None,
        "asset_class_axes": [
            {"line_index": line, "pixel_transcription": text} for line, text in axes
        ],
        "bank_code": code,
        "branch_bindings": [
            {"line_index": line, "pixel_transcription": text, "role": role}
            for line, text, role in branches
        ],
        "checks": {check: "PASS" for check in _REVIEW_CHECKS},
        "comparative_control": comparison,
        "disposition": "VERIFIED_INVESTMENT_PROPERTY_MOVEMENT_NOTE",
        "equations": list(equations),
        "mappings": list(mappings),
        "owner_line_index": owner_line,
        "owner_pixel_transcription": owner_text,
        "page_sequence": page,
        "source_period": "2025-12-31",
        "unit_authority": unit_authority,
    }


def _review_documents(base: ModuleType) -> list[dict[str, Any]]:
    v = base._value
    g = base._grid_dash_value

    def a(*components: dict[str, Any]) -> dict[str, Any]:
        return base._aggregate_value(components)

    term = base._term
    eq = base._equation
    mapping = base._mapping

    acb_rental_cost_open = g(15, 20)
    acb_cost_open = a(acb_rental_cost_open, v(51, "177.005"))
    acb_transfer = a(v(20, "38.967"), v(56, "48.415"))
    acb_disposal = v(60, "(114.695)")
    acb_cost_close = a(v(24, "38.967"), v(65, "110.725"))
    acb_dep_open = g(26, 29)
    acb_dep_charge = v(29, "19")
    acb_dep_close = v(32, "19")
    acb_carry_open = a(g(34, 38), v(51, "177.005"))
    acb_carry_close = a(v(38, "38.948"), v(65, "110.725"))
    acb = _present_document(
        base,
        code="ACB",
        page=57,
        owner_line=7,
        owner_text="Bất động sản đầu tư cho thuê",
        axes=(
            (8, "Quyền sử dụng đất"),
            (9, "Nhà cửa"),
            (10, "Tổng cộng"),
            (40, "Bất động sản đầu tư nắm giữ chờ tăng giá"),
            (42, "Quyền sử dụng đất"),
            (43, "Nhà cửa"),
            (44, "Tổng cộng"),
        ),
        branches=(
            (14, "Nguyên giá", "COST"),
            (25, "Hao mòn lũy kế", "ACCUMULATED_DEPRECIATION"),
            (33, "Giá trị còn lại", "CARRYING_VALUE"),
        ),
        mappings=(
            mapping(
                944,
                "COST_OPENING_TOTAL",
                (
                    (14, "Nguyên giá"),
                    (15, "Tại ngày 1 tháng 1 năm 2025"),
                    (48, "Tại ngày 1 tháng 1 năm 2025"),
                ),
                acb_cost_open,
                topology="SIBLING_SOURCE_TABLES_COST_OPENING_CONTROLLED_SUM",
            ),
            mapping(
                948,
                "COST_TRANSFER_FROM_CIP",
                (
                    (16, "Chuyển từ xây dựng cơ bản"),
                    (17, "dở dang (Thuyết minh 14.1 (ii)"),
                    (52, "Chuyển từ xây dựng cơ bản"),
                    (53, "dở dang (Thuyết minh 14.1 (ii)"),
                ),
                acb_transfer,
                topology="SIBLING_SOURCE_TABLES_TRANSFER_CONTROLLED_SUM",
            ),
            mapping(
                952,
                "COST_DISPOSAL",
                ((57, "Thanh lý"),),
                acb_disposal,
                topology="APPRECIATION_SUBTABLE_DISPOSAL_TOTAL",
            ),
            mapping(
                955,
                "COST_ENDING_TOTAL",
                ((21, "Tại ngày 31 tháng 12 năm 2025"), (62, "Tại ngày 31 tháng 12 năm 2025")),
                acb_cost_close,
                topology="SIBLING_SOURCE_TABLES_COST_ENDING_CONTROLLED_SUM",
            ),
            mapping(
                957,
                "DEPRECIATION_OPENING_TOTAL",
                ((25, "Hao mòn lũy kế"), (26, "Tại ngày 1 tháng 1 năm 2025")),
                acb_dep_open,
                topology="RENTAL_SUBTABLE_VISIBLE_DASH_TOTAL",
            ),
            mapping(
                958,
                "DEPRECIATION_CHARGE",
                ((25, "Hao mòn lũy kế"), (27, "Khấu hao trong năm")),
                acb_dep_charge,
                topology="RENTAL_SUBTABLE_DEPRECIATION_CHARGE_TOTAL",
            ),
            mapping(
                965,
                "DEPRECIATION_ENDING_TOTAL",
                ((25, "Hao mòn lũy kế"), (30, "Tại ngày 31 tháng 12 năm 2025")),
                acb_dep_close,
                topology="RENTAL_SUBTABLE_DEPRECIATION_ENDING_TOTAL",
            ),
            mapping(
                5973,
                "CARRYING_OPENING_TOTAL",
                (
                    (33, "Giá trị còn lại"),
                    (34, "Tại ngày 1 tháng 1 năm 2025"),
                    (48, "Tại ngày 1 tháng 1 năm 2025"),
                ),
                acb_carry_open,
                topology="SIBLING_SOURCE_TABLES_CARRYING_OPENING_CONTROLLED_SUM",
            ),
            mapping(
                5974,
                "CARRYING_ENDING_TOTAL",
                (
                    (33, "Giá trị còn lại"),
                    (35, "Tại ngày 31 tháng 12 năm 2025"),
                    (62, "Tại ngày 31 tháng 12 năm 2025"),
                ),
                acb_carry_close,
                topology="SIBLING_SOURCE_TABLES_CARRYING_ENDING_CONTROLLED_SUM",
            ),
        ),
        equations=(
            eq(
                "ACB_FAMILY_COST_ROLLFORWARD",
                (term(acb_cost_open), term(acb_transfer), term(acb_disposal)),
                acb_cost_close,
            ),
            eq(
                "ACB_FAMILY_DEPRECIATION_ROLLFORWARD",
                (term(acb_dep_open), term(acb_dep_charge)),
                acb_dep_close,
            ),
            eq(
                "ACB_FAMILY_OPENING_COST_LESS_DEPRECIATION",
                (term(acb_cost_open), term(acb_dep_open, -1)),
                acb_carry_open,
            ),
            eq(
                "ACB_FAMILY_CLOSING_COST_LESS_DEPRECIATION",
                (term(acb_cost_close), term(acb_dep_close, -1)),
                acb_carry_close,
            ),
            eq(
                "ACB_RENTAL_TRANSFER_ASSET_CLASS_SUM",
                (term(v(18, "37.080")), term(v(19, "1.887"))),
                v(20, "38.967"),
            ),
            eq(
                "ACB_RENTAL_COST_ENDING_ASSET_CLASS_SUM",
                (term(v(22, "37.080")), term(v(23, "1.887"))),
                v(24, "38.967"),
            ),
            eq(
                "ACB_RENTAL_DEPRECIATION_CHARGE_ASSET_CLASS_SUM",
                (term(g(27, 18)), term(v(28, "19"))),
                v(29, "19"),
            ),
            eq(
                "ACB_RENTAL_DEPRECIATION_ENDING_ASSET_CLASS_SUM",
                (term(g(30, 18)), term(v(31, "19"))),
                v(32, "19"),
            ),
            eq(
                "ACB_RENTAL_CARRYING_ENDING_ASSET_CLASS_SUM",
                (term(v(36, "37.080")), term(v(37, "1.868"))),
                v(38, "38.948"),
            ),
            eq(
                "ACB_APPRECIATION_COST_OPENING_ASSET_CLASS_SUM",
                (term(v(49, "171.133")), term(v(50, "5.872"))),
                v(51, "177.005"),
            ),
            eq(
                "ACB_APPRECIATION_TRANSFER_ASSET_CLASS_SUM",
                (term(v(54, "41.070")), term(v(55, "7.345"))),
                v(56, "48.415"),
            ),
            eq(
                "ACB_APPRECIATION_DISPOSAL_ASSET_CLASS_SUM",
                (term(v(58, "(108.823)")), term(v(59, "(5.872)"))),
                v(60, "(114.695)"),
            ),
            eq(
                "ACB_APPRECIATION_COST_ENDING_ASSET_CLASS_SUM",
                (term(v(63, "103.380")), term(v(64, "7.345"))),
                v(65, "110.725"),
            ),
        ),
        comparison=None,
        unit_authority="VISIBLE_PAGE_MILLION_VND_TOTAL_COLUMNS_ACROSS_TWO_SIBLING_TABLES",
    )

    mbb_cost_open = v(24, "260.415")
    mbb_cost_increase = v(27, "4.971")
    mbb_cost_decrease = v(31, "(10.260)")
    mbb_cost_close = v(35, "255.126")
    mbb_dep_open = v(40, "26.300")
    mbb_dep_charge = v(44, "6.145")
    mbb_dep_decrease = v(47, "(132)")
    mbb_dep_close = v(51, "32.313")
    mbb_carry_open = v(56, "234.115")
    mbb_carry_close = v(60, "222.813")
    mbb = _present_document(
        base,
        code="MBB",
        page=61,
        owner_line=10,
        owner_text="BẤT ĐỘNG SẢN ĐẦU TƯ",
        axes=(
            (12, "Nhà cửa,"),
            (14, "vật kiến trúc"),
            (13, "Quyền sử dụng"),
            (15, "đất có thời hạn"),
            (16, "Tổng cộng"),
        ),
        branches=(
            (20, "Nguyên giá", "COST"),
            (36, "Giá trị hao mòn lũy kế", "ACCUMULATED_DEPRECIATION"),
            (52, "Giá trị còn lại", "CARRYING_VALUE"),
        ),
        mappings=(
            mapping(
                944,
                "COST_OPENING_TOTAL",
                ((20, "Nguyên giá"), (21, "Số dư đầu năm")),
                mbb_cost_open,
                topology="ANNUAL_COST_OPENING_TOTAL_COLUMN",
            ),
            mapping(
                6002,
                "COST_INCREASE_TOTAL",
                ((20, "Nguyên giá"), (25, "Tăng trong năm")),
                mbb_cost_increase,
                topology="ANNUAL_COST_INCREASE_TOTAL_COLUMN",
            ),
            mapping(
                6003,
                "COST_DECREASE_TOTAL",
                ((20, "Nguyên giá"), (28, "Giảm trong năm")),
                mbb_cost_decrease,
                topology="ANNUAL_COST_DECREASE_TOTAL_COLUMN",
            ),
            mapping(
                955,
                "COST_ENDING_TOTAL",
                ((20, "Nguyên giá"), (32, "Số dư cuối năm")),
                mbb_cost_close,
                topology="ANNUAL_COST_ENDING_TOTAL_COLUMN",
            ),
            mapping(
                957,
                "DEPRECIATION_OPENING_TOTAL",
                ((36, "Giá trị hao mòn lũy kế"), (37, "Số dư đầu năm")),
                mbb_dep_open,
                topology="ANNUAL_DEPRECIATION_OPENING_TOTAL_COLUMN",
            ),
            mapping(
                6005,
                "DEPRECIATION_INCREASE_TOTAL",
                ((36, "Giá trị hao mòn lũy kế"), (41, "Khấu hao trong năm")),
                mbb_dep_charge,
                topology="ANNUAL_DEPRECIATION_INCREASE_TOTAL_COLUMN",
            ),
            mapping(
                965,
                "DEPRECIATION_ENDING_TOTAL",
                ((36, "Giá trị hao mòn lũy kế"), (48, "Số dư cuối năm")),
                mbb_dep_close,
                topology="ANNUAL_DEPRECIATION_ENDING_TOTAL_COLUMN",
            ),
            mapping(
                5973,
                "CARRYING_OPENING_TOTAL",
                ((52, "Giá trị còn lại"), (53, "Số dư đầu năm")),
                mbb_carry_open,
                topology="ANNUAL_CARRYING_OPENING_TOTAL_COLUMN",
            ),
            mapping(
                5974,
                "CARRYING_ENDING_TOTAL",
                ((52, "Giá trị còn lại"), (57, "Số dư cuối năm")),
                mbb_carry_close,
                topology="ANNUAL_CARRYING_ENDING_TOTAL_COLUMN",
            ),
        ),
        equations=(
            eq(
                "MBB_COST_ROLLFORWARD",
                (term(mbb_cost_open), term(mbb_cost_increase), term(mbb_cost_decrease)),
                mbb_cost_close,
            ),
            eq(
                "MBB_DEPRECIATION_ROLLFORWARD",
                (term(mbb_dep_open), term(mbb_dep_charge), term(mbb_dep_decrease)),
                mbb_dep_close,
            ),
            eq(
                "MBB_OPENING_COST_LESS_DEPRECIATION",
                (term(mbb_cost_open), term(mbb_dep_open, -1)),
                mbb_carry_open,
            ),
            eq(
                "MBB_CLOSING_COST_LESS_DEPRECIATION",
                (term(mbb_cost_close), term(mbb_dep_close, -1)),
                mbb_carry_close,
            ),
            eq(
                "MBB_COST_OPENING_ASSET_CLASS_SUM",
                (term(v(22, "51.835")), term(v(23, "208.580"))),
                mbb_cost_open,
            ),
            eq(
                "MBB_COST_INCREASE_VISIBLE_COMPONENT_EQUALS_TOTAL",
                (term(v(26, "4.971")),),
                mbb_cost_increase,
            ),
            eq(
                "MBB_COST_DECREASE_ASSET_CLASS_SUM",
                (term(v(29, "(1.000)")), term(v(30, "(9.260)"))),
                mbb_cost_decrease,
            ),
            eq(
                "MBB_COST_ENDING_ASSET_CLASS_SUM",
                (term(v(33, "55.806")), term(v(34, "199.320"))),
                mbb_cost_close,
            ),
            eq(
                "MBB_DEPRECIATION_OPENING_ASSET_CLASS_SUM",
                (term(v(38, "6.923")), term(v(39, "19.377"))),
                mbb_dep_open,
            ),
            eq(
                "MBB_DEPRECIATION_CHARGE_ASSET_CLASS_SUM",
                (term(v(42, "1.034")), term(v(43, "5.111"))),
                mbb_dep_charge,
            ),
            eq(
                "MBB_DEPRECIATION_DECREASE_VISIBLE_COMPONENT_EQUALS_TOTAL",
                (term(v(46, "(132)")),),
                mbb_dep_decrease,
            ),
            eq(
                "MBB_DEPRECIATION_ENDING_ASSET_CLASS_SUM",
                (term(v(49, "7.825")), term(v(50, "24.488"))),
                mbb_dep_close,
            ),
            eq(
                "MBB_CARRYING_OPENING_ASSET_CLASS_SUM",
                (term(v(54, "44.912")), term(v(55, "189.203"))),
                mbb_carry_open,
            ),
            eq(
                "MBB_CARRYING_ENDING_ASSET_CLASS_SUM",
                (term(v(58, "47.981")), term(v(59, "174.832"))),
                mbb_carry_close,
            ),
        ),
        comparison={
            "period_header_line_index": 62,
            "pixel_transcription": "Biến động của bất động sản đầu tư trong năm kết thúc ngày 31 tháng 12 năm 2024 như sau:",
            "source_period": "2024-12-31",
        },
        unit_authority="VISIBLE_PAGE_MILLION_VND_TOTAL_COLUMN",
    )

    absent_reason = (
        "Complete-PDF fresh VietOCR and adjacent-family boundary replay found no detailed "
        "investment-property movement region in this audited consolidated annual-2025 report; "
        "policy, statement and unrelated near-text hits remain negative controls."
    )
    return [
        acb,
        mbb,
        base._absent_doc("VPB", absent_reason),
        base._absent_doc("HDB", absent_reason),
        base._absent_doc("VCB", absent_reason),
        base._absent_doc("CTG", absent_reason),
        base._absent_doc("BID", absent_reason),
        base._absent_doc("VIB", absent_reason),
    ]


def _annual_metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    mappings = [mapping for trial in trials for mapping in trial["mappings"]]
    return {
        "accounting_equation_count": sum(len(trial["equations"]) for trial in trials),
        "confirmed_bound_report_absence_count": sum(
            trial["disposition"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT" for trial in trials
        ),
        "controlled_aggregate_mapping_count": sum(
            mapping["value"]["semantic_text_source"] == "CONTROLLED_SUM_OF_VISIBLE_SOURCE_CELLS"
            for mapping in mappings
        ),
        "document_count": len(trials),
        "mapping_verified_count": len(mappings),
        "open_review_item_count": 0,
        "verified_present_document_count": sum(bool(trial["mappings"]) for trial in trials),
        "visible_dash_zero_mapping_count": sum(
            mapping["value"]["normalized_pixel_transcription"] == "-" for mapping in mappings
        ),
    }


def _configure_base() -> ModuleType:
    base = _load_module(
        "annual_2025_investment_property_mapping_base",
        "scripts/experiments/build_investment_property_8bank_codex_verified_mapping_v1.py",
    )
    scanner = base.scanner
    scanner.FORMAT_VERSION = SCAN_FORMAT
    scanner.MATCHER_FORMAT = "INVESTMENT_PROPERTY_VARIANT_GRAPH_DOCUMENT_V2"
    scanner.MATCHER_VARIANT_PROFILE = "REPORTING_PERIOD_GENERAL_V2"
    scanner.SCAN_ID_PREFIX = SCAN_ID_PREFIX

    base.FORMAT_VERSION = FORMAT_VERSION
    base.REVIEW_FORMAT = REVIEW_FORMAT
    base.CLAIM_BOUNDARY = CLAIM_BOUNDARY
    base.REVIEW_PATH = REVIEW_PATH
    base.RESULT_PATH = RESULT_PATH
    base.SEMANTIC_INDEX_PATH = SEMANTIC_INDEX_PATH
    base.CROP_MANIFEST_PATH = CROP_MANIFEST_PATH
    base.EXPECTED_INDEX_SHA256 = EXPECTED_INDEX_SHA256
    base.EXPECTED_CROP_MANIFEST_SHA256 = EXPECTED_CROP_MANIFEST_SHA256
    base.EXPECTED_AXIS_SHA256 = EXPECTED_AXIS_SHA256
    base.EXPECTED_SCAN_ID = EXPECTED_SCAN_ID
    base._RESULT_STATE = RESULT_STATE
    base._RESULT_ID_PREFIX = RESULT_ID_PREFIX
    base._REVIEW_STATE = REVIEW_STATE
    base._REVIEW_ID_PREFIX = REVIEW_ID_PREFIX
    base._SOURCE_PERIOD_STATUS = (
        "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_OPENING_PERIODS"
    )
    base._REVIEW_CHECKS = tuple(_REVIEW_CHECKS)
    base._REVIEW_AUTHORITY = canonical_clone_v1(_REVIEW_AUTHORITY)
    base._AUTHORITY = canonical_clone_v1(_AUTHORITY)
    base._BOUNDARIES = dict(_BOUNDARIES)
    base._MAPPED_SCHEMA_IDS = frozenset().union(*_EXPECTED_IDS.values())
    base._review_documents = lambda: _review_documents(base)
    base._metrics = _annual_metrics
    return base


def _validate_expected_coverage(value: dict[str, Any]) -> dict[str, Any]:
    trials = value.get("trials")
    if type(trials) is not list or len(trials) != 8:
        raise _error("annual investment-property trial denominator drifted")
    for trial in trials:
        code = trial.get("document_provenance")
        actual = {mapping.get("report_norm_id") for mapping in trial.get("mappings", [])}
        if actual != _EXPECTED_IDS.get(code):
            raise _error(f"annual investment-property schema coverage drifted: {code}")
    expected_metrics = {
        "accounting_equation_count": 27,
        "confirmed_bound_report_absence_count": 6,
        "controlled_aggregate_mapping_count": 5,
        "document_count": 8,
        "mapping_verified_count": 18,
        "open_review_item_count": 0,
        "verified_present_document_count": 2,
        "visible_dash_zero_mapping_count": 1,
    }
    if value.get("metrics") != expected_metrics:
        raise _error("annual investment-property metrics drifted")
    return value


def build_annual_2025_investment_property_pixel_review_blueprint_v1() -> dict[str, Any]:
    return _configure_base()._review_blueprint()


def build_live_annual_2025_investment_property_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    try:
        return _validate_expected_coverage(
            _configure_base().build_live_investment_property_8bank_codex_verified_mapping_v1()
        )
    except Annual2025InvestmentProperty8BankError:
        raise
    except Exception as error:
        raise _error(str(error)) from error


def validate_annual_2025_investment_property_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    try:
        return _validate_expected_coverage(
            _configure_base().validate_live_investment_property_8bank_codex_verified_mapping_v1(
                value
            )
        )
    except Annual2025InvestmentProperty8BankError:
        raise
    except Exception as error:
        raise _error(str(error)) from error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--write-result", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    base = _configure_base()
    if args.write_review:
        base._write(REVIEW_PATH, base._review_blueprint())
    result = build_live_annual_2025_investment_property_8bank_codex_verified_mapping_v1()
    if args.write_result:
        base._write(RESULT_PATH, result)
    elif args.verify:
        payload = base.base.support._stable_bytes(RESULT_PATH)
        persisted = base.base.support._strict_json(payload, RESULT_PATH.as_posix())
        validate_annual_2025_investment_property_8bank_codex_verified_mapping_replay_v1(persisted)
        print(persisted["result_id"])
    else:
        sys.stdout.buffer.write(canonical_json_bytes_v1(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
