"""Verify detailed corporate-income-tax reconciliations across eight reports."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.full_document_vietocr_accounting_axis_v1 import (
    EXPECTED_DOCUMENT_ORDER,
    project_full_document_vietocr_accounting_axis_v1,
)
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import _authority_snapshot
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, filename: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load income-tax support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


other = _load(
    "other_activity_support_for_income_tax",
    "build_other_activity_8bank_codex_verified_mapping_v1.py",
)
scanner = _load(
    "income_tax_scan_for_verified_mapping",
    "scan_income_tax_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "INCOME_TAX_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "INCOME_TAX_8BANK_CODEX_PIXEL_REVIEW_V1"
ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT = True
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_BANK_BLIND_DETAILED_"
    "CORPORATE_INCOME_TAX_RECONCILIATION_VISIBLE_PDF_PADDLEOCR_OR_NATIVE_"
    "NUMERIC_CHALLENGER_PERIOD_UNIT_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_"
    "VISIBLE_DASH_ZERO_BLANK_NOT_ZERO_UNMAPPED_ROWS_RETAINED_NO_EXPORT_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0091-income-tax-8bank-codex-pixel-review-v1.json")
RESULT_PATH = Path("docs/experiments/E-0091-income-tax-8bank-codex-verified-mapping-v1.json")
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = other.CROP_MANIFEST_PATH
EXPECTED_INDEX_SHA256 = other.EXPECTED_INDEX_SHA256
EXPECTED_CROP_MANIFEST_SHA256 = other.EXPECTED_CROP_MANIFEST_SHA256
EXPECTED_AXIS_SHA256 = other.EXPECTED_AXIS_SHA256
EXPECTED_SCAN_ID = "itfdsv1:scan:0ec1682d31f9f98635009b13bd554c5389330f8846ef5f96dbd86606edefefb6"
EXPECTED_RESULT_ID = "e0091:result:c6560d7e03be8e1a3214bfcb8ee030a234427b9b73a190278d2a3f2af4e7d8ab"
RESULT_STATE = "INCOME_TAX_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "e0091:result:"
REVIEW_STATE = "CODEX_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "e0091:pixel-review:"
REVIEW_RUN_ID = "E-0091"
VARIANT_PROFILE = "HISTORICAL_BASELINE_V1"
FAMILY_END_DISPLAY_ORDER = 822
SOURCE_PERIOD_STATUS_BY_PERIOD = {
    "2025-12-31": "VERIFIED_SOURCE_PERIOD_ANNUAL_2025",
    "2026-03-31": "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2",
    "2026-06-30": "VERIFIED_SOURCE_PERIOD_Q2_2026",
}

_SCHEMA_EXPECTED = {
    1142: (
        "II. THÔNG TIN BỔ SUNG CHO CÁC KHOẢN MỤC TRÌNH BÀY TRONG BẢNG KẾT QUẢ KINH DOANH",
        None,
        684,
    ),
    5723: ("Chi phí thuế thu nhập hiện hành", 5727, 808),
    5724: ("Năm hiện hành", 5723, 809),
    5725: ("Chi phí/(hoàn nhập) thuế thu nhập hoãn lại", 5727, 810),
    5726: ("Chi phí/(thu nhập) thuế thu nhập hoãn lại", 5725, 811),
    5727: ("Chi phí thuế thu nhập", 1142, 812),
    5728: ("Tổng lợi nhuận theo kế toán trước thuế hợp nhất", 5731, 813),
    5729: (
        "Thu nhập không chịu thuế (bao gồm cổ tức, lợi nhuận từ các đơn vị, các khoản điều chỉnh hợp nhất không chịu thuế) và các khoản khác",
        5731,
        814,
    ),
    5730: ("Các chi phí không được khấu trừ của riêng Ngân hàng", 5731, 815),
    5731: ("Thu nhập chịu thuế TNDN ước tính tại Việt Nam", 1142, 816),
    5732: ("Chi phí thuế TNDN hiện hành riêng Ngân hàng (i)", 5737, 817),
    5733: ("Điều chỉnh trong năm cho thuế thu nhập hiện hành của các năm trước (ii)", 5737, 818),
    5734: ("Chi phí thuế TNDN chi nhánh nước ngoài (iii)", 5737, 819),
    5735: ("Chi phí thuế TNDN của các công ty con (iv)", 5737, 820),
    5736: ("Chi phí/(hoàn nhập) thuế TNDN hoãn lại (v)", 5737, 821),
    5737: ("Chi phí thuế TNDN (i+ii+iii+iv+v)", 1142, 822),
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "blank_cell_interpreted_as_zero": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "dash_zero_policy_applied_only_to_visible_source_dash": True,
    "detailed_note_absence_bounded_to_bound_report": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_income_tax_rows": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_numeric_challenger_and_accounting_closure_required": True,
    "text_similarity_alone_used_for_mapping": False,
    "unmapped_source_rows_discarded": False,
}
_REVIEW_SAFETY = {
    "bank_page_or_filename_used_as_graph_rule": False,
    "blank_cell_interpreted_as_zero": False,
    "mapping_decided_by_text_similarity_alone": False,
    "old_ocr_used_as_semantic_anchor": False,
    "only_visible_source_dash_interpreted_as_zero": True,
    "source_parent_and_children_double_counted": False,
    "unmapped_source_rows_retained": True,
    "vietocr_used_as_numeric_truth": False,
    "whole_pdf_uniqueness_replayed": True,
}
_RESULT_FIELDS = {
    "authority",
    "claim_boundary",
    "format_version",
    "input_refs",
    "metrics",
    "result_id",
    "schema_family",
    "state",
    "trials",
}


class IncomeTax8BankCodexVerifiedMappingV1Error(ValueError):
    """The tax structure, pixels, numbers, equations, or schema drifted."""


def _error(message: str) -> IncomeTax8BankCodexVerifiedMappingV1Error:
    return IncomeTax8BankCodexVerifiedMappingV1Error(message)


def _ref(page: int, line: int, text: str) -> dict[str, Any]:
    return {"line_index": line, "page_sequence": page, "pixel_transcription": text}


def _line(page: int, line: int, text: str) -> dict[str, Any]:
    return {"kind": "AUTHENTICATED_LINE", **_ref(page, line, text)}


def _sum(page: int, items: Sequence[tuple[int, str]]) -> dict[str, Any]:
    return {
        "components": [_line(page, line, text) for line, text in items],
        "kind": "AUTHENTICATED_CONTROLLED_SUM",
        "page_sequence": page,
    }


def _mapping(
    role: str,
    report_norm_id: int,
    page: int,
    labels: Sequence[tuple[int, str]],
    current: Mapping[str, Any],
    comparative: Mapping[str, Any],
    topology: str = "DIRECT_OR_WRAPPED_LABEL_TWO_PERIOD_LANES",
) -> dict[str, Any]:
    return {
        "labels": [_ref(page, line, text) for line, text in labels],
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": topology,
        "values": {
            "COMPARATIVE_PERIOD": canonical_clone_v1(comparative),
            "CURRENT_PERIOD": canonical_clone_v1(current),
        },
    }


def _source_only(
    row_id: str,
    role: str,
    page: int,
    labels: Sequence[tuple[int, str]],
    values: Mapping[str, Mapping[str, Any]],
    blank_axes: Sequence[str],
    reason: str,
) -> dict[str, Any]:
    return {
        "blank_axes": list(blank_axes),
        "labels": [_ref(page, line, text) for line, text in labels],
        "reason": reason,
        "role": role,
        "row_id": row_id,
        "values": canonical_clone_v1(values),
    }


def _equation(
    name: str,
    parent: str,
    terms: Sequence[str],
    axes: Sequence[str] = ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"),
) -> dict[str, Any]:
    return {"axes": list(axes), "name": name, "parent_role": parent, "term_roles": list(terms)}


def _absence(code: str) -> dict[str, Any]:
    return {
        "absence_evidence": {
            "complete_pdf_pages_scanned": True,
            "detailed_note_complete_region_count": 0,
            "reason": (
                "No detailed corporate-income-tax reconciliation containing profit before tax, "
                "adjustments, taxable income, period/unit axes and current tax was found in the "
                "bound report; statement tax aggregates, tax-obligation rollforwards and deferred-"
                "tax balance notes do not qualify."
            ),
            "source_scope_absence_only": True,
        },
        "bank_code": code,
        "equations": [],
        "graph_roles": [],
        "mappings": [],
        "owner": [],
        "page_span": None,
        "period_axis": [],
        "presentation": "NO_DETAILED_INCOME_TAX_RECONCILIATION_IN_BOUND_REPORT",
        "source_only_rows": [],
        "source_period": None,
        "unit_evidence": [],
    }


def _review_documents() -> list[dict[str, Any]]:
    documents = [_absence("ACB")]
    page = 50
    documents.append(
        {
            "absence_evidence": None,
            "bank_code": "MBB",
            "equations": [
                _equation(
                    "CURRENT_YEAR_EQUALS_CURRENT_TAX_PARENT",
                    "CURRENT_TAX_PARENT",
                    ["CURRENT_TAX_CURRENT_YEAR"],
                ),
                _equation(
                    "CURRENT_YEAR_EQUALS_DEFERRED_TAX_PARENT",
                    "DEFERRED_TAX_PARENT",
                    ["DEFERRED_TAX_CURRENT_YEAR"],
                ),
                _equation(
                    "CURRENT_PLUS_DEFERRED_EQUALS_TAX_SUMMARY",
                    "TOTAL_TAX_SUMMARY",
                    ["CURRENT_TAX_PARENT", "DEFERRED_TAX_PARENT"],
                ),
                _equation(
                    "PROFIT_PLUS_ADJUSTMENTS_EQUALS_TAXABLE_INCOME",
                    "TAXABLE_INCOME",
                    ["PROFIT_BEFORE_TAX", "NON_TAXABLE_AGGREGATE", "NON_DEDUCTIBLE_EXPENSE"],
                ),
                _equation(
                    "FIVE_COMPONENTS_EQUAL_TOTAL_TAX",
                    "TOTAL_TAX_COMPONENTS",
                    [
                        "CURRENT_TAX_BANK",
                        "PRIOR_PERIOD_TAX_ADJUSTMENT",
                        "FOREIGN_BRANCH_TAX",
                        "SUBSIDIARY_TAX",
                        "DEFERRED_TAX_COMPONENT",
                    ],
                ),
                _equation(
                    "SUMMARY_EQUALS_COMPONENT_TOTAL", "TOTAL_TAX_COMPONENTS", ["TOTAL_TAX_SUMMARY"]
                ),
            ],
            "graph_roles": [
                "CURRENT_TAX_EXPENSE_PARENT",
                "CURRENT_TAX_EXPENSE_CHILD",
                "DEFERRED_TAX_EXPENSE_CHILD",
                "TOTAL_TAX_EXPENSE",
                "PROFIT_BEFORE_TAX",
                "NON_TAXABLE_INCOME",
                "NON_DEDUCTIBLE_EXPENSE",
                "TAXABLE_INCOME",
                "CURRENT_TAX_BANK",
                "PRIOR_PERIOD_TAX_ADJUSTMENT",
                "CURRENT_TAX_FOREIGN_BRANCH",
                "CURRENT_TAX_SUBSIDIARIES",
                "DEFERRED_TAX_COMPONENT",
            ],
            "mappings": [
                _mapping(
                    "CURRENT_TAX_PARENT",
                    5723,
                    page,
                    [(8, "Chi phí thuế thu nhập hiện hành")],
                    _line(page, 9, "4.050.030"),
                    _line(page, 10, "3.205.483"),
                ),
                _mapping(
                    "CURRENT_TAX_CURRENT_YEAR",
                    5724,
                    page,
                    [(11, "Năm hiện hành")],
                    _line(page, 12, "4.050.030"),
                    _line(page, 13, "3.205.483"),
                ),
                _mapping(
                    "DEFERRED_TAX_PARENT",
                    5725,
                    page,
                    [(14, "Chi phí/(hoàn nhập) thuế thu nhập hoãn lại")],
                    _line(page, 15, "(9.965)"),
                    _line(page, 16, "4.248"),
                ),
                _mapping(
                    "DEFERRED_TAX_CURRENT_YEAR",
                    5726,
                    page,
                    [(17, "Chi phí/(thu nhập) thuế thu nhập hoãn lại")],
                    _line(page, 18, "(9.965)"),
                    _line(page, 19, "4.248"),
                ),
                _mapping(
                    "TOTAL_TAX_SUMMARY",
                    5727,
                    page,
                    [(20, "Chi phí thuế thu nhập")],
                    _line(page, 21, "4.040.065"),
                    _line(page, 22, "3.209.731"),
                ),
                _mapping(
                    "PROFIT_BEFORE_TAX",
                    5728,
                    page,
                    [(29, "Tổng lợi nhuận theo kế toán trước thuế hợp"), (30, "nhất")],
                    _line(page, 31, "20.188.258"),
                    _line(page, 32, "15.889.316"),
                ),
                _mapping(
                    "NON_TAXABLE_AGGREGATE",
                    5729,
                    page,
                    [
                        (34, "Thu nhập không chịu thuế (bao gồm cổ tức,"),
                        (35, "lợi nhuận từ các đơn vị, các khoản điều chỉnh"),
                        (36, "hợp nhất không chịu thuế) và các khoản khác"),
                    ],
                    _line(page, 37, "(1.713.243)"),
                    _line(page, 38, "(1.562.859)"),
                ),
                _mapping(
                    "NON_DEDUCTIBLE_EXPENSE",
                    5730,
                    page,
                    [(39, "Các chi phí không được khấu trừ của riêng"), (40, "Ngân hàng")],
                    _line(page, 41, "11.597"),
                    _line(page, 42, "30.486"),
                ),
                _mapping(
                    "TAXABLE_INCOME",
                    5731,
                    page,
                    [(43, "Thu nhập chịu thuế TNDN ước tính tại Việt"), (44, "Nam")],
                    _line(page, 45, "18.486.612"),
                    _line(page, 46, "14.356.943"),
                ),
                _mapping(
                    "CURRENT_TAX_BANK",
                    5732,
                    page,
                    [(47, "Chi phí thuế TNDN hiện hành riêng Ngân hàng (i)")],
                    _line(page, 48, "3.697.322"),
                    _line(page, 49, "2.871.389"),
                ),
                _mapping(
                    "PRIOR_PERIOD_TAX_ADJUSTMENT",
                    5733,
                    page,
                    [
                        (50, "Điều chỉnh trong năm cho thuế thu nhập hiện"),
                        (51, "hành của các năm trước (ii)"),
                    ],
                    _line(page, 52, "4.223"),
                    _line(page, 53, "14.599"),
                ),
                _mapping(
                    "FOREIGN_BRANCH_TAX",
                    5734,
                    page,
                    [(54, "Chi phí thuế TNDN chi nhánh nước ngoài (iii)")],
                    _line(page, 55, "1.457"),
                    _line(page, 56, "1.756"),
                ),
                _mapping(
                    "SUBSIDIARY_TAX",
                    5735,
                    page,
                    [(57, "Chi phí thuế TNDN của các công ty con (iv)")],
                    _line(page, 58, "347.028"),
                    _line(page, 59, "317.739"),
                ),
                _mapping(
                    "DEFERRED_TAX_COMPONENT",
                    5736,
                    page,
                    [(60, "Chi phí/(hoàn nhập) thuế TNDN hoãn lại (v)")],
                    _line(page, 61, "(9.965)"),
                    _line(page, 62, "4.248"),
                ),
                _mapping(
                    "TOTAL_TAX_COMPONENTS",
                    5737,
                    page,
                    [(63, "Chi phí thuế TNDN (i+ii+iii+iv+v)")],
                    _line(page, 64, "4.040.065"),
                    _line(page, 65, "3.209.731"),
                ),
            ],
            "owner": [_ref(page, 0, "11. Thuế thu nhập doanh nghiệp")],
            "page_span": [page, page],
            "period_axis": [
                _ref(page, 2, "Từ 01/01/2026"),
                _ref(page, 4, "đến 30/06/2026"),
                _ref(page, 3, "Từ 01/01/2025"),
                _ref(page, 5, "đến 30/06/2025"),
            ],
            "presentation": "SUMMARY_CURRENT_DEFERRED_PLUS_FULL_FIVE_COMPONENT_RECONCILIATION",
            "source_only_rows": [],
            "source_period": "2026-06-30",
            "unit_evidence": [_ref(page, 6, "Triệu đồng"), _ref(page, 7, "Triệu đồng")],
        }
    )
    page = 59
    documents.append(
        {
            "absence_evidence": None,
            "bank_code": "VPB",
            "equations": [
                _equation(
                    "PROFIT_PLUS_AGGREGATED_ADJUSTMENTS_EQUALS_TAXABLE_INCOME",
                    "TAXABLE_INCOME",
                    ["PROFIT_BEFORE_TAX", "NON_TAXABLE_AGGREGATE", "NON_DEDUCTIBLE_EXPENSE"],
                ),
                _equation(
                    "CURRENT_RATE_PLUS_PRIOR_ADJUSTMENT_EQUALS_CURRENT_TAX",
                    "CURRENT_TAX_PARENT",
                    ["CURRENT_TAX_CURRENT_YEAR", "PRIOR_PERIOD_TAX_ADJUSTMENT"],
                ),
            ],
            "graph_roles": [
                "PROFIT_BEFORE_TAX",
                "NON_TAXABLE_INCOME",
                "NON_DEDUCTIBLE_EXPENSE",
                "CONSOLIDATION_ADJUSTMENT",
                "OTHER_TAXABLE_INCOME_ADJUSTMENT",
                "TAXABLE_INCOME",
                "CURRENT_TAX_AT_RATE",
                "PRIOR_PERIOD_TAX_ADJUSTMENT",
                "CURRENT_TAX_TOTAL",
                "OTHER_CURRENT_TAX_ADJUSTMENT",
            ],
            "mappings": [
                _mapping(
                    "CURRENT_TAX_PARENT",
                    5723,
                    page,
                    [(48, "Chi phí thuế TNDN phải trả trong kỳ")],
                    _line(page, 49, "1.667.459"),
                    _line(page, 50, "1.078.750"),
                ),
                _mapping(
                    "CURRENT_TAX_CURRENT_YEAR",
                    5724,
                    page,
                    [(42, "Chi phí thuế TNDN theo thuế suất hiện hành")],
                    _line(page, 43, "1.667.457"),
                    _line(page, 44, "1.079.121"),
                ),
                _mapping(
                    "PROFIT_BEFORE_TAX",
                    5728,
                    page,
                    [(19, "Lợi nhuận thuần trước thuế TNDN")],
                    _line(page, 20, "7.920.786"),
                    _line(page, 21, "5.014.882"),
                ),
                _mapping(
                    "NON_TAXABLE_AGGREGATE",
                    5729,
                    page,
                    [
                        (24, "Thu nhập không chịu thuế"),
                        (32, "Điều chỉnh liên quan đến hợp nhất"),
                        (36, "Các khoản điều chỉnh khác"),
                    ],
                    _sum(page, [(25, "(30.625)"), (33, "488.951"), (37, "(41.831)")]),
                    _sum(page, [(26, "-"), (34, "379.309"), (38, "-")]),
                    "CONTROLLED_SUM_OF_SCHEMA_AGGREGATE_COMPONENTS",
                ),
                _mapping(
                    "NON_DEDUCTIBLE_EXPENSE",
                    5730,
                    page,
                    [(28, "Chi phí không được khấu trừ")],
                    _line(page, 29, "3"),
                    _line(page, 30, "1.416"),
                ),
                _mapping(
                    "TAXABLE_INCOME",
                    5731,
                    page,
                    [(39, "Thu nhập chịu thuế ước tính trong kỳ")],
                    _line(page, 40, "8.337.284"),
                    _line(page, 41, "5.395.607"),
                ),
                _mapping(
                    "PRIOR_PERIOD_TAX_ADJUSTMENT",
                    5733,
                    page,
                    [(45, "Điều chỉnh số thuế phải nộp các kỳ trước")],
                    _line(page, 46, "2"),
                    _line(page, 47, "(371)"),
                ),
            ],
            "owner": [
                _ref(page, 7, "Thuế thu nhập doanh nghiệp hiện hành (tiếp theo)"),
                _ref(page, 8, "Chi phí thuế TNDN trong kỳ được ước tính như sau:"),
            ],
            "page_span": [page, page],
            "period_axis": [
                _ref(page, 9, "Cho kỳ kế toán"),
                _ref(page, 11, "3 tháng kết thúc"),
                _ref(page, 13, "ngày 31 tháng 3"),
                _ref(page, 15, "năm 2026"),
                _ref(page, 10, "Cho kỳ kế toán"),
                _ref(page, 12, "3 tháng kết thúc"),
                _ref(page, 14, "ngày 31 tháng 3"),
                _ref(page, 16, "năm 2025"),
            ],
            "presentation": "Q1_CURRENT_TAX_RECONCILIATION_WITH_AGGREGATED_ADJUSTMENTS",
            "source_only_rows": [],
            "source_period": "2026-03-31",
            "unit_evidence": [_ref(page, 17, "Triệu đồng"), _ref(page, 18, "Triệu đồng")],
        }
    )
    documents.extend([_absence("HDB"), _absence("VCB"), _absence("CTG"), _absence("BID")])
    page = 48
    documents.append(
        {
            "absence_evidence": None,
            "bank_code": "VIB",
            "equations": [
                _equation(
                    "PROFIT_PLUS_ADJUSTMENTS_EQUALS_TAXABLE_INCOME",
                    "TAXABLE_INCOME",
                    ["PROFIT_BEFORE_TAX", "NON_TAXABLE_AGGREGATE", "NON_DEDUCTIBLE_EXPENSE"],
                ),
                _equation(
                    "CURRENT_RATE_EQUALS_CURRENT_TAX_WHEN_CURRENT_ADJUSTMENT_IS_BLANK",
                    "CURRENT_TAX_PARENT",
                    ["CURRENT_TAX_CURRENT_YEAR"],
                    ["CURRENT_PERIOD"],
                ),
                _equation(
                    "CURRENT_RATE_PLUS_VISIBLE_COMPARATIVE_ADJUSTMENT_EQUALS_CURRENT_TAX",
                    "CURRENT_TAX_PARENT",
                    ["CURRENT_TAX_CURRENT_YEAR", "OTHER_CURRENT_TAX_ADJUSTMENT"],
                    ["COMPARATIVE_PERIOD"],
                ),
            ],
            "graph_roles": [
                "PROFIT_BEFORE_TAX",
                "NON_TAXABLE_INCOME",
                "NON_DEDUCTIBLE_EXPENSE",
                "TAXABLE_INCOME",
                "CURRENT_TAX_AT_RATE",
                "OTHER_CURRENT_TAX_ADJUSTMENT",
                "CURRENT_TAX_TOTAL",
            ],
            "mappings": [
                _mapping(
                    "CURRENT_TAX_PARENT",
                    5723,
                    page,
                    [(35, "Tổng chi phí thuế TNDN hiện hành")],
                    _line(page, 36, "1.039.093"),
                    _line(page, 37, "1.003.421"),
                ),
                _mapping(
                    "CURRENT_TAX_CURRENT_YEAR",
                    5724,
                    page,
                    [(29, "Chi phí thuế TNDN tính trên thu nhập chịu thuế kỳ"), (30, "hiện hành")],
                    _line(page, 31, "1.039.093"),
                    _line(page, 32, "1.003.258"),
                ),
                _mapping(
                    "PROFIT_BEFORE_TAX",
                    5728,
                    page,
                    [(14, "Lợi nhuận trước thuế TNDN")],
                    _line(page, 15, "5.185.708"),
                    _line(page, 16, "5.016.354"),
                ),
                _mapping(
                    "NON_TAXABLE_AGGREGATE",
                    5729,
                    page,
                    [(17, "Thu nhập từ cổ tức không chịu thuế")],
                    _line(page, 18, "(200)"),
                    _line(page, 19, "(100)"),
                ),
                _mapping(
                    "NON_DEDUCTIBLE_EXPENSE",
                    5730,
                    page,
                    [(20, "Chi phí không được khấu trừ")],
                    _line(page, 21, "9.956"),
                    _line(page, 22, "35"),
                ),
                _mapping(
                    "TAXABLE_INCOME",
                    5731,
                    page,
                    [(23, "Thu nhập chịu thuế TNDN")],
                    _line(page, 24, "5.195.464"),
                    _line(page, 25, "5.016.289"),
                ),
            ],
            "owner": [
                _ref(
                    page,
                    6,
                    "Chi phí thuế TNDN hiện hành trong giai đoạn tài chính sáu tháng kết thúc ngày 30 tháng 06 năm",
                ),
                _ref(page, 7, "2026 và ngày 30 tháng 06 năm 2025 được ước tính như sau:"),
            ],
            "page_span": [page, page],
            "period_axis": [
                _ref(page, 8, "6 tháng đầu"),
                _ref(page, 10, "năm 2026"),
                _ref(page, 9, "6 tháng đầu"),
                _ref(page, 11, "năm 2025"),
            ],
            "presentation": "CURRENT_TAX_RECONCILIATION_WITH_ONE_COMPARATIVE_ONLY_ADJUSTMENT",
            "source_only_rows": [
                _source_only(
                    "TAX-001",
                    "OTHER_CURRENT_TAX_ADJUSTMENT",
                    page,
                    [(33, "Điều chỉnh khác")],
                    {"COMPARATIVE_PERIOD": _line(page, 34, "163")},
                    ["CURRENT_PERIOD"],
                    "The source label is broader than the prior-period adjustment leaf; its current-period cell is blank and is not interpreted as zero.",
                )
            ],
            "source_period": "2026-06-30",
            "unit_evidence": [_ref(page, 12, "triệu đồng"), _ref(page, 13, "triệu đồng")],
        }
    )
    if [item["bank_code"] for item in documents] != list(EXPECTED_DOCUMENT_ORDER):
        raise _error("review document order drifted")
    return documents


def _review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_documents(),
        "format_version": REVIEW_FORMAT,
        "reviewer": {
            "kind": "CODEX_INDEPENDENT_VISIBLE_PDF_REVIEW",
            "review_run_id": REVIEW_RUN_ID,
        },
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "scan_id": EXPECTED_SCAN_ID,
        "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": EXPECTED_INDEX_SHA256,
        "state": REVIEW_STATE,
    }
    return {**material, "review_id": REVIEW_ID_PREFIX + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("Codex income-tax pixel review differs from the fixed ledger")
    return canonical_clone_v1(expected)


def _document(items: Any, code: str, label: str) -> dict[str, Any]:
    return other._document(items, code, label)


def _page(document: Mapping[str, Any], page: int, label: str) -> dict[str, Any]:
    return other._page(document, page, label)


def _schema_binding(item: Any, report_norm_id: int) -> dict[str, Any]:
    expected = _SCHEMA_EXPECTED.get(report_norm_id)
    if (
        expected is None
        or item is None
        or item.statement_type != "TM"
        or item.schema_id != report_norm_id
        or item.canonical_name != expected[0]
        or item.parent_id != expected[1]
        or (not ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT and item.display_order != expected[2])
    ):
        raise _error(f"mapping does not bind exact live TM schema row {report_norm_id}")
    return {
        "canonical_name": item.canonical_name,
        "display_order": expected[2],
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    values = [
        value
        for trial in trials
        for group in (trial["verified_mappings"], trial["verified_source_only_rows"])
        for row in group
        for value in row["values"]
    ]
    return {
        "accounting_equation_verified_count": sum(
            len(t["verified_accounting_equations"]) for t in trials
        ),
        "detailed_note_not_present_document_count": sum(
            t["status"] == "CONFIRMED_DETAILED_NOTE_NOT_PRESENT_IN_BOUND_REPORT" for t in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            t["whole_document_uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for t in trials
        ),
        "fresh_vietocr_numeric_disagreement_count": sum(
            value.get("fresh_vietocr_numeric_status") == "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
            for value in values
        ),
        "mapping_verified_count": sum(len(t["verified_mappings"]) for t in trials),
        "open_source_row_count": sum(len(t["verified_source_only_rows"]) for t in trials),
        "q1_source_period_caveat_document_count": sum(
            t["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2" for t in trials
        ),
        "verified_value_cell_count": sum(
            len(row["values"]) for t in trials for row in t["verified_mappings"]
        ),
        "visible_source_dash_zero_component_count": sum(
            component.get("source_numeric_challenger") == "-"
            and component.get("normalized_value") == 0
            for value in values
            for component in value.get("component_evidence", [])
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("income-tax result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != RESULT_STATE
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("income-tax result identity or metrics drifted")
    allowed = {
        "CONFIRMED_DETAILED_NOTE_NOT_PRESENT_IN_BOUND_REPORT",
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT",
        "VERIFIED_BY_CODEX_WITH_UNRESOLVED_SCHEMA_ROWS",
    }
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or trial.get("status") not in allowed
            or any(
                item.get("status") != "VERIFIED_BY_CODEX"
                for item in trial.get("verified_mappings", [])
            )
            or any(
                item.get("status") != "UNRESOLVED_SCHEMA_GAP_SOURCE_ROW_RETAINED"
                for item in trial.get("verified_source_only_rows", [])
            )
        ):
            raise _error("income-tax trial shape or status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != RESULT_ID_PREFIX + canonical_json_sha256_v1(material):
        raise _error("income-tax result identity drifted")
    return canonical_clone_v1(value)


def build_income_tax_8bank_codex_verified_mapping_v1(
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    review: Any,
    schema_authority: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
    review_sha256: str,
) -> dict[str, Any]:
    reviewed_documents = _review(review)["documents"]
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    scanner.validate_income_tax_full_document_scan_replay_v1(
        structure_scan, semantic_index, variant_profile=VARIANT_PROFILE
    )
    if (
        axis.get("semantic_axis_sha256") != EXPECTED_AXIS_SHA256
        or structure_scan.get("scan_id") != EXPECTED_SCAN_ID
        or type(crop_manifest) is not dict
    ):
        raise _error("fixed semantic axis, crop manifest, or structure scan drifted")
    trials = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        reviewed = _document(reviewed_documents, code, "pixel review")
        scan_trial = _document(structure_scan["trials"], code, "structure scan")
        matcher = scan_trial["matcher_result"]
        base = {
            "document_ordinal": ordinal,
            "document_provenance": code,
            "source_pdf_sha256": scan_trial["source_pdf_sha256"],
            "structure_graph_id": matcher["result_id"],
            "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
        }
        if reviewed["absence_evidence"] is not None:
            if matcher["regions"]:
                raise _error("absent detailed income-tax note unexpectedly matched")
            trials.append(
                {
                    **base,
                    "absence_evidence": canonical_clone_v1(reviewed["absence_evidence"]),
                    "mapped_report_norm_ids": [],
                    "owner_evidence": [],
                    "page_span": None,
                    "period_axis_evidence": [],
                    "presentation": reviewed["presentation"],
                    "source_geometry_mode": None,
                    "source_period": None,
                    "source_period_status": "NOT_APPLICABLE_DETAILED_NOTE_ABSENT",
                    "status": "CONFIRMED_DETAILED_NOTE_NOT_PRESENT_IN_BOUND_REPORT",
                    "unit_evidence": [],
                    "verified_accounting_equations": [],
                    "verified_mappings": [],
                    "verified_source_only_rows": [],
                }
            )
            continue
        if not same_typed_json_v1(
            matcher["uniqueness"], {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
        ):
            raise _error("reviewed region is not the unique whole-PDF income-tax graph")
        region = matcher["regions"][0]
        if not same_typed_json_v1(region["page_span"], reviewed["page_span"]):
            raise _error("reviewed income-tax page span drifted")
        if region["layout"]["observed_roles"] != reviewed["graph_roles"]:
            raise _error("reviewed income-tax graph role axis drifted")
        axis_document = _document(axis["documents"], code, "accounting axis")
        semantic_document = _document(semantic_index["documents"], code, "semantic index")
        crop_document = _document(crop_manifest["documents"], code, "crop manifest")
        cache: dict[str, dict[str, Any]] = {}

        def verified(
            ref: Mapping[str, Any],
            *,
            cache: dict[str, dict[str, Any]] = cache,
            axis_document: Mapping[str, Any] = axis_document,
            semantic_document: Mapping[str, Any] = semantic_document,
            crop_document: Mapping[str, Any] = crop_document,
        ) -> dict[str, Any]:
            key = canonical_json_sha256_v1(ref)
            if key not in cache:
                cache[key] = other._verified_value(
                    axis_document, semantic_document, crop_document, ref
                )
            return canonical_clone_v1(cache[key])

        verified_mappings = []
        verified_source_only = []
        by_role: dict[str, dict[str, Any]] = {}
        mapped_ids = set()
        for mapping in reviewed["mappings"]:
            item = {
                "label_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, label)
                    for label in mapping["labels"]
                ],
                "role": mapping["role"],
                "schema_binding": _schema_binding(
                    schema_by_id.get(mapping["report_norm_id"]), mapping["report_norm_id"]
                ),
                "status": "VERIFIED_BY_CODEX",
                "topology": mapping["topology"],
                "values": [
                    {"axis_role": axis_role, **verified(ref)}
                    for axis_role, ref in mapping["values"].items()
                ],
            }
            verified_mappings.append(item)
            by_role[item["role"]] = item
            mapped_ids.add(mapping["report_norm_id"])
        for row in reviewed["source_only_rows"]:
            item = {
                "blank_axes": list(row["blank_axes"]),
                "label_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, label)
                    for label in row["labels"]
                ],
                "reason": row["reason"],
                "role": row["role"],
                "row_id": row["row_id"],
                "status": "UNRESOLVED_SCHEMA_GAP_SOURCE_ROW_RETAINED",
                "values": [
                    {"axis_role": axis_role, **verified(ref)}
                    for axis_role, ref in row["values"].items()
                ],
            }
            verified_source_only.append(item)
            by_role[item["role"]] = item
        equations = []
        for specification in reviewed["equations"]:
            for axis_role in specification["axes"]:
                parent = next(
                    v
                    for v in by_role[specification["parent_role"]]["values"]
                    if v["axis_role"] == axis_role
                )
                terms = [
                    next(v for v in by_role[role]["values"] if v["axis_role"] == axis_role)
                    for role in specification["term_roles"]
                ]
                computed = sum(item["normalized_value"] for item in terms)
                if computed != parent["normalized_value"]:
                    raise _error(
                        f"income-tax equation does not close for {code}/{specification['name']}/{axis_role}"
                    )
                equations.append(
                    {
                        "axis_role": axis_role,
                        "computed_value": computed,
                        "name": specification["name"],
                        "parent_role": specification["parent_role"],
                        "status": "VERIFIED_EXACT",
                        "term_roles": list(specification["term_roles"]),
                        "visible_total": parent["normalized_value"],
                    }
                )
        period_status = SOURCE_PERIOD_STATUS_BY_PERIOD.get(reviewed["source_period"])
        if period_status is None:
            raise _error("reviewed income-tax source period is unsupported")
        status = (
            "VERIFIED_BY_CODEX_WITH_UNRESOLVED_SCHEMA_ROWS"
            if verified_source_only
            else "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT"
            if period_status == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            else "VERIFIED_BY_CODEX"
        )
        page_number = reviewed["page_span"][0]
        trials.append(
            {
                **base,
                "absence_evidence": None,
                "mapped_report_norm_ids": sorted(mapped_ids),
                "owner_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, item)
                    for item in reviewed["owner"]
                ],
                "page_span": list(reviewed["page_span"]),
                "period_axis_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, item)
                    for item in reviewed["period_axis"]
                ],
                "presentation": reviewed["presentation"],
                "source_geometry_mode": _page(semantic_document, page_number, "semantic index")[
                    "geometry_mode"
                ],
                "source_period": reviewed["source_period"],
                "source_period_status": period_status,
                "status": status,
                "unit_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, item)
                    for item in reviewed["unit_evidence"]
                ],
                "verified_accounting_equations": equations,
                "verified_mappings": verified_mappings,
                "verified_source_only_rows": verified_source_only,
            }
        )
    mapped_union = sorted(
        {
            item["schema_binding"]["report_norm_id"]
            for trial in trials
            for item in trial["verified_mappings"]
        }
    )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "crop_manifest": {
                "path": CROP_MANIFEST_PATH.as_posix(),
                "sha256": crop_manifest_sha256,
            },
            "pixel_review": {"path": REVIEW_PATH.as_posix(), "sha256": review_sha256},
            "schema_authority": canonical_clone_v1(schema_authority),
            "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
            "semantic_index": {
                "path": SEMANTIC_INDEX_PATH.as_posix(),
                "sha256": EXPECTED_INDEX_SHA256,
            },
            "structure_scan_id": EXPECTED_SCAN_ID,
        },
        "metrics": _metrics(trials),
        "schema_family": {
            "family_end_display_order": FAMILY_END_DISPLAY_ORDER,
            "family_roots": [
                _schema_binding(schema_by_id.get(report_norm_id), report_norm_id)
                for report_norm_id in (5727, 5731, 5737)
            ],
            "mapped_report_norm_ids": mapped_union,
            "schema_gap_source_row_count": sum(len(t["verified_source_only_rows"]) for t in trials),
            "section_root": _schema_binding(schema_by_id.get(1142), 1142),
        },
        "state": RESULT_STATE,
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def validate_income_tax_8bank_codex_verified_mapping_replay_v1(
    value: Any, **inputs: Any
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_income_tax_8bank_codex_verified_mapping_v1(**inputs)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("income-tax verified mapping does not replay exactly")
    return supplied


def _stable_json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], str]:
    payload = other.operating.income.foundation.support._stable_bytes(path)
    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise _error(f"fixed JSON bytes drifted: {path}")
    value = other.operating.income.foundation.support._strict_json(payload, path.as_posix())
    if type(value) is not dict:
        raise _error(f"fixed JSON root must be one object: {path}")
    return value, digest


def _live_inputs() -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_live_income_tax_full_document_scan_v1(
        SEMANTIC_INDEX_PATH, variant_profile=VARIANT_PROFILE
    )
    review, review_sha = _stable_json(REVIEW_PATH)
    live_schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    if EXPECTED_RESULT_ID is None:
        schema_authority = canonical_clone_v1(live_schema_authority)
    else:
        historical_result, _ = _stable_json(RESULT_PATH)
        historical_result = _validate_result(historical_result)
        if historical_result.get("result_id") != EXPECTED_RESULT_ID:
            raise _error("fixed historical income-tax result identity drifted")
        schema_authority = canonical_clone_v1(historical_result["input_refs"]["schema_authority"])
    return {
        "semantic_index": semantic_index,
        "crop_manifest": crop_manifest,
        "structure_scan": structure_scan,
        "review": review,
        "schema_authority": schema_authority,
        "schema_by_id": schema_by_id,
        "crop_manifest_sha256": crop_sha,
        "review_sha256": review_sha,
    }


def build_live_income_tax_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    return build_income_tax_8bank_codex_verified_mapping_v1(**_live_inputs())


def validate_live_income_tax_8bank_codex_verified_mapping_v1(value: Any) -> dict[str, Any]:
    return validate_income_tax_8bank_codex_verified_mapping_replay_v1(value, **_live_inputs())


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes_v1(value))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--write-result", action="store_true")
    parser.add_argument("--validate-result", action="store_true")
    args = parser.parse_args()
    if args.write_review:
        _write(REVIEW_PATH, _review_blueprint())
    if args.write_result:
        _write(RESULT_PATH, build_live_income_tax_8bank_codex_verified_mapping_v1())
    if args.validate_result:
        result, _ = _stable_json(RESULT_PATH)
        validate_live_income_tax_8bank_codex_verified_mapping_v1(result)


if __name__ == "__main__":
    main()
