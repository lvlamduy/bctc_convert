"""Verify annual-2025 ``Tài sản Có khác`` across eight banks.

The reusable complete-PDF matcher selects each region without bank, page, note
or filename routing.  The bank/page constants below are only the independently
reviewed evidence ledger after unique structural selection.  Every accepted
number is replayed from the visible PDF cell and the authenticated upstream
numeric axis; source rows without an exact schema meaning remain explicit.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import canonical_clone_v1, canonical_json_bytes_v1

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "ANNUAL_2025_OTHER_ASSETS_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_OTHER_ASSETS_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_OTHER_ASSETS_8BANK_BOUNDED_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025oa8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_OTHER_ASSETS_CODEX_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025oa8bcv1:pixel-review:"
REVIEW_RUN_ID = "E-0127"
REVIEW_PATH = Path(
    "docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json"
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
EXPECTED_SCAN_ID = "oafdsv1:scan:e49ed09de3214ff0b9549e83a58620b724fc79c3297de48ce1b1f9d45e11541a"

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_VIETOCR_"
    "BANK_BLIND_OTHER_ASSETS_VARIANT_GRAPH_VISIBLE_PDF_PIXEL_UPSTREAM_PPOCRV6_"
    "NUMERIC_AXIS_PERIOD_UNIT_PARENT_CHILD_SUBTOTAL_ROLLFORWARD_AND_LIVE_TM_"
    "SCHEMA_ONLY_UNMAPPED_SOURCE_ROWS_RETAINED_NO_EXPORT_AUTHORITY"
)
_REVIEW_CHECKS = (
    "COMPLETE_PDF_UNIQUE_REGION",
    "OWNER_PARENT_CHILD_AND_SIBLING_TOPOLOGY",
    "CROSS_PAGE_CONTINUATION_AND_SUBTABLE_VARIANTS",
    "CURRENT_2025_AND_COMPARATIVE_2024_PERIOD_AXES",
    "MILLION_VND_UNIT_VISIBLE",
    "VISIBLE_PIXEL_LABELS_DIGITS_SIGNS_AND_DASHES",
    "UPSTREAM_PPOCRV6_NUMERIC_CHALLENGER",
    "OPTIONAL_CHILDREN_NOT_REQUIRED_FOR_REGION_LOCATION",
    "PARENT_CHILD_SUBTOTAL_AND_ROLLFORWARD_ACCOUNTING",
    "LIVE_TM_SCHEMA_HIERARCHY_AND_DISPLAY_ORDER",
    "UNMAPPED_SOURCE_ROWS_RETAINED_WITHOUT_FORCED_EQUIVALENCE",
)
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "fresh_vietocr_used_as_numeric_truth": False,
    "gemma_json_used_as_mapping_or_numeric_authority": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": "VISIBLE_PDF_PIXELS_WITH_UPSTREAM_PPOCRV6_AND_ACCOUNTING",
    "reporting_period_dates_derived_from_pdf": True,
    "source_rows_without_equivalent_schema_forced_into_nearest_item": False,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "broad_corpus_or_other_report_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "comparison_period_used_as_mapping_authority": False,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "gemma_json_used_as_mapping_or_numeric_authority": False,
    "independent_pdf_pixel_and_upstream_ppocrv6_used_for_numeric_truth": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_annual_other_asset_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "reporting_period_dates_derived_from_pdf": True,
    "text_similarity_alone_used_for_mapping": False,
    "unmapped_source_rows_retained": True,
}
_EXPECTED_IDS = {
    "ACB": {967, 968, 971, 980, 987, 989, 997, 1012, 1013, 1014, 1015, 1016, 1017, 1018, 1019},
    "MBB": {967, 970, 971, 973, 978, 981, 982, 984, 985, 986, 987, 989, 994, 997, 5975, 6007},
    "VPB": {
        967,
        970,
        971,
        972,
        973,
        981,
        982,
        983,
        984,
        985,
        986,
        987,
        989,
        990,
        993,
        994,
        1018,
        1023,
        5975,
        5976,
        6007,
    },
    "HDB": {
        967,
        968,
        969,
        971,
        973,
        975,
        981,
        982,
        983,
        984,
        986,
        987,
        989,
        990,
        993,
        997,
        1018,
        1019,
        5975,
        5976,
    },
    "VCB": {
        967,
        968,
        970,
        971,
        973,
        974,
        981,
        982,
        983,
        984,
        985,
        986,
        987,
        989,
        990,
        991,
        997,
        1018,
        1019,
        5976,
        6007,
    },
    "CTG": {967, 968, 969, 971, 987, 989, 990, 997},
    "BID": {966, 967, 968, 970, 971, 973, 976, 978, 979, 982, 987, 988, 989, 993, 997, 5975},
    "VIB": {966, 967, 970, 971, 975, 981, 982, 983, 984, 985, 986, 987, 989, 990, 993, 997, 6007},
}
_EXPECTED_METRICS = {
    "accounting_equation_verified_count": 66,
    "annual_source_period_document_count": 8,
    "confirmed_bound_report_absence_count": 0,
    "document_count": 8,
    "document_unique_region_count": 8,
    "mapping_verified_count": 134,
    "open_source_row_count": 35,
    "verified_value_cell_count": 295,
}


class Annual2025OtherAssets8BankError(ValueError):
    """Annual other-assets source, numeric, schema or replay evidence drifted."""


def _error(message: str) -> Annual2025OtherAssets8BankError:
    return Annual2025OtherAssets8BankError(message)


def _load_module(name: str, relative_path: str) -> ModuleType:
    path = PROJECT_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual other-assets support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _open_row(
    base: ModuleType,
    item_id: str,
    page: int,
    label_line: int,
    label_text: str,
    current: Sequence[tuple[int, str]],
    comparative: Sequence[tuple[int, str]],
    reason: str,
) -> dict[str, Any]:
    return {
        "item_id": item_id,
        "label": base._label(page, label_line, label_text),
        "reason": reason,
        "status": "UNRESOLVED",
        "values": {
            "COMPARATIVE": [base._ref(page, *item) for item in comparative],
            "CURRENT": [base._ref(page, *item) for item in current],
        },
    }


def _present(
    base: ModuleType,
    *,
    code: str,
    owner: tuple[int, int, str],
    page_span: Sequence[int],
    mappings: Sequence[dict[str, Any]],
    equations: Sequence[dict[str, Any]],
    unresolved: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "bank_code": code,
        "checks": {check: "PASS" for check in _REVIEW_CHECKS},
        "disposition": (
            "VERIFIED_BY_CODEX_WITH_OPEN_SOURCE_ROWS" if unresolved else "VERIFIED_BY_CODEX"
        ),
        "equations": list(equations),
        "mappings": list(mappings),
        "owner": base._label(*owner),
        "page_span": list(page_span),
        "source_period": "2025-12-31",
        "unit_authority": "VISIBLE_LOCAL_MILLION_VND_CURRENT_2025_AND_COMPARATIVE_2024",
        "unmapped_source_rows": list(unresolved),
    }


def _acb_review(base: ModuleType) -> dict[str, Any]:
    d, m, r, label, e = (
        base._direct,
        base._mapping,
        base._ref,
        base._label,
        base._equation,
    )
    mappings = [
        d(967, "RECEIVABLES", 58, 7, "Các khoản phải thu", (27, "6.743.073"), (28, "4.299.649")),
        d(
            971,
            "EXTERNAL_RECEIVABLES",
            58,
            12,
            "Phải thu bên ngoài",
            (13, "5.594.255"),
            (14, "3.227.744"),
        ),
        d(
            968,
            "CONSTRUCTION_IN_PROGRESS",
            58,
            15,
            "Xây dựng cơ bản dở dang",
            (16, "806.530"),
            (17, "740.684"),
        ),
        d(980, "DIVIDEND_RECEIVABLE", 58, 24, "Cổ tức phải thu", (25, "2.100"), (26, "2.082")),
        d(
            1012,
            "CIP_OPENING",
            58,
            41,
            "Số dư đầu năm",
            (42, "740.684"),
            (43, "1.174.974"),
            "CIP_ROLLFORWARD",
        ),
        d(
            1013,
            "CIP_INCREASE",
            58,
            44,
            "Tăng trong năm",
            (45, "511.155"),
            (46, "552.821"),
            "CIP_ROLLFORWARD",
        ),
        d(
            1014,
            "CIP_TO_TANGIBLE",
            58,
            47,
            "Chuyển sang TSCĐ hữu hình",
            (48, "(235.497)"),
            (49, "(305.764)"),
            "CIP_ROLLFORWARD",
        ),
        d(
            1015,
            "CIP_TO_INTANGIBLE",
            58,
            50,
            "Chuyển sang TSCĐ vô hình",
            (51, "(122.430)"),
            (52, "(674.338)"),
            "CIP_ROLLFORWARD",
        ),
        m(
            1016,
            "CIP_TO_OTHER_ASSETS",
            [
                label(58, 53, "Chuyển sang bất động sản đầu tư"),
                label(58, 55, "Chuyển sang tài sản khác"),
            ],
            [r(58, 54, "(87.382)")],
            [r(58, 56, "(7.009)")],
            "PERIOD_SPECIFIC_NONZERO_OTHER_ASSET_TRANSFERS",
        ),
        d(
            1017,
            "CIP_ENDING",
            58,
            57,
            "Số dư cuối năm",
            (58, "806.530"),
            (59, "740.684"),
            "CIP_ROLLFORWARD",
        ),
        d(
            1018,
            "OTHER_ASSET_CREDIT_QUALITY",
            58,
            70,
            "Phân tích chất lượng tài sản Có khác được phân loại là tài sản có rủi ro tín dụng",
            (80, "14.359"),
            (81, "106.832"),
        ),
        d(1019, "GRADE_1", 58, 79, "Nhóm 1 - Nợ đủ tiêu chuẩn", (80, "14.359"), (81, "106.832")),
        d(
            987,
            "OTHER_ASSET_BRANCH",
            59,
            38,
            "Tài sản Có khác",
            (52, "1.414.349"),
            (53, "1.425.899"),
        ),
        d(989, "PREPAID_COST", 59, 43, "Chi phí chờ phân bổ", (44, "1.330.233"), (45, "1.306.644")),
        d(997, "OTHER_ASSET", 59, 49, "Tài sản khác", (50, "82.886"), (51, "119.255")),
    ]
    equations = [
        e(
            "RECEIVABLE_CHILDREN_TO_TOTAL",
            "CURRENT",
            [
                r(58, 13, "5.594.255"),
                r(58, 16, "806.530"),
                r(58, 19, "333.182"),
                r(58, 22, "7.006"),
                r(58, 25, "2.100"),
            ],
            r(58, 27, "6.743.073"),
        ),
        e(
            "RECEIVABLE_CHILDREN_TO_TOTAL",
            "COMPARATIVE",
            [
                r(58, 14, "3.227.744"),
                r(58, 17, "740.684"),
                r(58, 20, "320.464"),
                r(58, 23, "8.675"),
                r(58, 26, "2.082"),
            ],
            r(58, 28, "4.299.649"),
        ),
        e(
            "CIP_ROLLFORWARD",
            "CURRENT",
            [
                r(58, 42, "740.684"),
                r(58, 45, "511.155"),
                r(58, 48, "(235.497)"),
                r(58, 51, "(122.430)"),
                r(58, 54, "(87.382)"),
            ],
            r(58, 58, "806.530"),
        ),
        e(
            "CIP_ROLLFORWARD",
            "COMPARATIVE",
            [
                r(58, 43, "1.174.974"),
                r(58, 46, "552.821"),
                r(58, 49, "(305.764)"),
                r(58, 52, "(674.338)"),
                r(58, 56, "(7.009)"),
            ],
            r(58, 59, "740.684"),
        ),
        e(
            "OTHER_ASSET_CHILDREN_TO_TOTAL",
            "CURRENT",
            [r(59, 44, "1.330.233"), r(59, 48, "1.230"), r(59, 50, "82.886")],
            r(59, 52, "1.414.349"),
        ),
        e(
            "OTHER_ASSET_CHILDREN_TO_TOTAL",
            "COMPARATIVE",
            [r(59, 45, "1.306.644"), r(59, 51, "119.255")],
            r(59, 53, "1.425.899"),
        ),
    ]
    unresolved = [
        _open_row(
            base,
            "A2025-OA-001",
            58,
            18,
            "Các khoản tạm ứng và phải thu nội bộ",
            [(19, "333.182")],
            [(20, "320.464")],
            "One printed row combines advances and internal receivables; it cannot be split between ReportNormIds 975 and 970.",
        ),
        _open_row(
            base,
            "A2025-OA-002",
            58,
            21,
            "Phải thu Ngân sách Nhà nước",
            [(22, "7.006")],
            [(23, "8.675")],
            "The source does not state that this is tax overpayment/deductible tax, so ReportNormId 974 is not inferred.",
        ),
        _open_row(
            base,
            "A2025-OA-003",
            59,
            7,
            "Tài sản thuế thu nhập doanh nghiệp hoãn lại",
            [(14, "17.263")],
            [(15, "17.318")],
            "No exact child exists in the current TM other-assets schema family.",
        ),
        _open_row(
            base,
            "A2025-OA-004",
            59,
            46,
            "Tài sản thay thế cho việc thực hiện nghĩa vụ của bên bảo đảm",
            [(48, "1.230")],
            [],
            "The comparative cell is a visible dash; the current verifier does not promote an unbound blank geometry cell to numeric evidence.",
        ),
        _open_row(
            base,
            "A2025-OA-005",
            60,
            7,
            "Các khoản dự phòng rủi ro cho các tài sản Có nội bảng khác",
            [(22, "183.215")],
            [(23, "178.379")],
            "The 966–1023 schema family has no exact provision-balance and movement branch.",
        ),
    ]
    return _present(
        base,
        code="ACB",
        owner=(58, 5, "TÀI SẢN CÓ KHÁC"),
        page_span=(58, 60),
        mappings=mappings,
        equations=equations,
        unresolved=unresolved,
    )


def _mbb_review(base: ModuleType) -> dict[str, Any]:
    d, m, r, label, e = (
        base._direct,
        base._mapping,
        base._ref,
        base._label,
        base._equation,
    )
    mappings = [
        d(967, "RECEIVABLES", 62, 12, "Các khoản phải thu", (26, "28.125.764"), (27, "14.360.628")),
        d(
            970,
            "INTERNAL_RECEIVABLES",
            62,
            17,
            "Các khoản phải thu nội bộ",
            (18, "359.532"),
            (19, "444.741"),
        ),
        d(
            971,
            "EXTERNAL_RECEIVABLES",
            62,
            20,
            "Các khoản phải thu bên ngoài",
            (21, "26.726.578"),
            (22, "13.079.328"),
        ),
        d(
            6007,
            "CAPEX_RECEIVABLE",
            62,
            23,
            "Chi phí xây dựng cơ bản dở dang, mua sắm TSCĐ",
            (24, "1.039.654"),
            (25, "836.559"),
        ),
        d(
            973,
            "DEPOSITS_COLLATERAL",
            62,
            34,
            "Ký quỹ, thế chấp, cầm cố",
            (35, "891.504"),
            (36, "626.507"),
        ),
        d(
            5975,
            "PAYMENT_SERVICE_RECEIVABLE",
            62,
            41,
            "Phải thu liên quan đến dịch vụ thanh toán",
            (42, "1.525.624"),
            (43, "241.946"),
        ),
        d(
            978,
            "INSURANCE_SUBSIDIARY_RECEIVABLE",
            62,
            47,
            "Phải thu trong hoạt động bảo hiểm của công ty con",
            (48, "446.093"),
            (49, "368.414"),
        ),
        m(
            981,
            "OTHER_RECEIVABLE",
            [
                label(62, 55, "Các khoản phải thu từ bán nợ"),
                label(62, 58, "Các khoản phải thu bên ngoài khác"),
            ],
            [r(62, 56, "11.248.396"), r(62, 59, "1.741.948")],
            [r(62, 57, "5.852.543"), r(62, 60, "1.756.350")],
            "SUM_OF_OTHER_RECEIVABLE_SOURCES",
        ),
        d(
            982,
            "INTEREST_FEE_RECEIVABLES",
            62,
            64,
            "Các khoản lãi, phí phải thu",
            (82, "13.549.018"),
            (83, "8.918.622"),
        ),
        d(
            984,
            "DEPOSIT_INTEREST",
            62,
            70,
            "Lãi phải thu từ tiền gửi",
            (71, "275.884"),
            (72, "30.863"),
        ),
        d(
            986,
            "SECURITIES_INTEREST",
            62,
            73,
            "Lãi phải thu từ đầu tư chứng khoán",
            (74, "5.277.148"),
            (75, "4.009.194"),
        ),
        d(
            985,
            "DERIVATIVE_INTEREST",
            62,
            79,
            "Lãi phải thu từ công cụ tài chính phái sinh",
            (80, "813.255"),
            (81, "194.227"),
        ),
        d(
            987,
            "OTHER_ASSET_BRANCH",
            63,
            12,
            "Tài sản Có khác",
            (28, "7.894.091"),
            (29, "5.873.749"),
        ),
        d(
            989,
            "PREPAID_COST",
            63,
            19,
            "Chi phí trả trước chờ phân bổ khác",
            (20, "3.478.007"),
            (21, "3.066.449"),
        ),
        d(994, "REAL_ESTATE", 63, 22, "Hàng hóa bất động sản", (23, "246.495"), (24, "158.912")),
        d(997, "OTHER_ASSET", 63, 25, "Tài sản Có khác", (26, "4.169.589"), (27, "2.638.865")),
    ]
    equations = [
        e(
            "RECEIVABLE_CHILDREN_TO_TOTAL",
            "CURRENT",
            [r(62, 18, "359.532"), r(62, 21, "26.726.578"), r(62, 24, "1.039.654")],
            r(62, 26, "28.125.764"),
        ),
        e(
            "RECEIVABLE_CHILDREN_TO_TOTAL",
            "COMPARATIVE",
            [r(62, 19, "444.741"), r(62, 22, "13.079.328"), r(62, 25, "836.559")],
            r(62, 27, "14.360.628"),
        ),
        e(
            "EXTERNAL_DETAIL_TO_TOTAL",
            "CURRENT",
            [
                r(62, 35, "891.504"),
                r(62, 40, "8.046.079"),
                r(62, 42, "1.525.624"),
                r(62, 45, "129.559"),
                r(62, 48, "446.093"),
                r(62, 52, "2.697.375"),
                r(62, 56, "11.248.396"),
                r(62, 59, "1.741.948"),
            ],
            r(62, 21, "26.726.578"),
        ),
        e(
            "EXTERNAL_DETAIL_TO_TOTAL",
            "COMPARATIVE",
            [
                r(62, 36, "626.507"),
                r(62, 38, "1.412.951"),
                r(62, 43, "241.946"),
                r(62, 46, "131.858"),
                r(62, 49, "368.414"),
                r(62, 53, "2.688.759"),
                r(62, 57, "5.852.543"),
                r(62, 60, "1.756.350"),
            ],
            r(62, 22, "13.079.328"),
        ),
        e(
            "INTEREST_COMPONENTS_TO_TOTAL",
            "CURRENT",
            [
                r(62, 71, "275.884"),
                r(62, 74, "5.277.148"),
                r(62, 77, "7.182.731"),
                r(62, 80, "813.255"),
            ],
            r(62, 82, "13.549.018"),
        ),
        e(
            "INTEREST_COMPONENTS_TO_TOTAL",
            "COMPARATIVE",
            [
                r(62, 72, "30.863"),
                r(62, 75, "4.009.194"),
                r(62, 78, "4.684.338"),
                r(62, 81, "194.227"),
            ],
            r(62, 83, "8.918.622"),
        ),
        e(
            "OTHER_ASSET_CHILDREN_TO_TOTAL",
            "CURRENT",
            [r(63, 20, "3.478.007"), r(63, 23, "246.495"), r(63, 26, "4.169.589")],
            r(63, 28, "7.894.091"),
        ),
        e(
            "OTHER_ASSET_CHILDREN_TO_TOTAL",
            "COMPARATIVE",
            [
                r(63, 18, "9.523"),
                r(63, 21, "3.066.449"),
                r(63, 24, "158.912"),
                r(63, 27, "2.638.865"),
            ],
            r(63, 29, "5.873.749"),
        ),
    ]
    unresolved = [
        _open_row(
            base,
            "A2025-OA-006",
            62,
            37,
            "Phải thu liên quan đến tài trợ thương mại",
            [],
            [(38, "1.412.951")],
            "No exact child exists in the current TM other-assets family; the current cell is a visible dash.",
        ),
        _open_row(
            base,
            "A2025-OA-007",
            62,
            39,
            "Các khoản phải thu miễn truy đòi theo bộ chứng từ",
            [(40, "8.046.079")],
            [],
            "The comparative cell is a visible dash and is not promoted without bound dash geometry.",
        ),
        _open_row(
            base,
            "A2025-OA-008",
            62,
            44,
            "Các khoản tạm ứng và đặt cọc hợp đồng",
            [(45, "129.559")],
            [(46, "131.858")],
            "One source row combines ReportNormIds 975 and 973; no allocation is printed.",
        ),
        _open_row(
            base,
            "A2025-OA-009",
            62,
            50,
            "Dự phòng phí và dự phòng bồi thường nghiệp vụ nhượng tái bảo hiểm",
            [(52, "2.697.375")],
            [(53, "2.688.759")],
            "No exact child exists in the current TM other-assets family.",
        ),
        _open_row(
            base,
            "A2025-OA-010",
            62,
            76,
            "Lãi phải thu hoạt động tín dụng và phí phải thu",
            [(77, "7.182.731")],
            [(78, "4.684.338")],
            "The printed row combines credit interest and fees, so it is not narrowed to ReportNormId 983.",
        ),
        _open_row(
            base,
            "A2025-OA-011",
            63,
            17,
            "Lợi thế thương mại",
            [],
            [(18, "9.523")],
            "The current cell is a visible dash and the row is not promoted without bound dash geometry.",
        ),
        _open_row(
            base,
            "A2025-OA-012",
            63,
            31,
            "Dự phòng rủi ro cho các tài sản Có nội bảng khác",
            [(44, "71.730")],
            [(45, "193.424")],
            "The 966–1023 schema family has no exact provision-balance and movement branch.",
        ),
    ]
    return _present(
        base,
        code="MBB",
        owner=(62, 10, "TÀI SẢN CÓ KHÁC"),
        page_span=(62, 63),
        mappings=mappings,
        equations=equations,
        unresolved=unresolved,
    )


def _vpb_review(base: ModuleType) -> dict[str, Any]:
    d, m, r, label, e = (
        base._direct,
        base._mapping,
        base._ref,
        base._label,
        base._equation,
    )
    mappings = [
        d(967, "RECEIVABLES", 55, 7, "Các khoản phải thu", (57, "17.522.681"), (58, "6.515.935")),
        d(
            970,
            "INTERNAL_RECEIVABLES",
            55,
            15,
            "Các khoản phải thu nội bộ",
            (16, "571.962"),
            (17, "281.942"),
        ),
        d(
            971,
            "EXTERNAL_RECEIVABLES",
            55,
            18,
            "Các khoản phải thu bên ngoài",
            (19, "11.432.753"),
            (20, "6.143.905"),
        ),
        m(
            5976,
            "WITHOUT_RECOURSE_DOCUMENT_RECEIVABLE",
            [
                label(
                    55,
                    21,
                    "Mua hẳn miễn truy đòi bộ chứng từ theo thư tín dụng do chính VPBank phát hành",
                ),
                label(
                    55,
                    25,
                    "Mua hẳn miễn truy đòi bộ chứng từ theo thư tín dụng do TCTD khác phát hành",
                ),
            ],
            [r(55, 23, "3.197.773"), r(55, 27, "87.709")],
            [r(55, 24, "162.855")],
            "SUM_OF_TWO_DOCUMENT_RECEIVABLE_VARIANTS",
        ),
        m(
            973,
            "DEPOSITS_COLLATERAL",
            [
                label(55, 28, "Ký quỹ và khoản phải thu hợp đồng tương lai trái phiếu Chính phủ"),
                label(55, 32, "Đặt cọc theo các hợp đồng kinh tế"),
            ],
            [r(55, 30, "36.061"), r(55, 33, "2.163.423")],
            [r(55, 31, "21.168"), r(55, 34, "1.365.794")],
            "SUM_OF_COLLATERAL_AND_ECONOMIC_CONTRACT_DEPOSITS",
        ),
        d(
            5975,
            "PAYMENT_SERVICE_RECEIVABLE",
            55,
            38,
            "Phải thu về hoạt động thanh toán",
            (39, "2.169.215"),
            (40, "1.414.058"),
        ),
        d(
            972,
            "ADVANCE_TO_SUPPLIER",
            55,
            41,
            "Tạm ứng nhà cung cấp",
            (42, "400.932"),
            (43, "363.998"),
        ),
        d(
            981,
            "OTHER_RECEIVABLE",
            55,
            48,
            "Phải thu bên ngoài khác",
            (49, "1.612.712"),
            (50, "2.213.943"),
        ),
        m(
            6007,
            "CAPEX_RECEIVABLE",
            [label(55, 51, "Mua sắm tài sản cố định"), label(55, 54, "Xây dựng cơ bản dở dang")],
            [r(55, 52, "5.474.874"), r(55, 55, "43.092")],
            [r(55, 53, "85.071"), r(55, 56, "5.017")],
            "SUM_OF_CAPEX_COMPONENTS",
        ),
        d(
            1018,
            "OTHER_ASSET_CREDIT_QUALITY",
            55,
            59,
            "Phân tích chất lượng tài sản Có khác được phân loại là tài sản có rủi ro tín dụng",
            (73, "171.786"),
            (74, "84.077"),
        ),
        d(1023, "GRADE_5", 55, 70, "Nợ có khả năng mất vốn", (71, "84.077"), (72, "84.077")),
        d(
            982,
            "INTEREST_FEE_RECEIVABLES",
            56,
            7,
            "Các khoản lãi, phí phải thu",
            (31, "14.279.226"),
            (32, "8.384.069"),
        ),
        d(
            984,
            "DEPOSIT_INTEREST",
            56,
            14,
            "Lãi phải thu từ tiền gửi",
            (15, "112.249"),
            (16, "52.297"),
        ),
        m(
            986,
            "OTHER_INTEREST_AND_FEES",
            [
                label(56, 17, "Lãi phải thu từ đầu tư chứng khoán"),
                label(56, 23, "Lãi phải thu từ hoạt động mua nợ"),
                label(56, 28, "Phí phải thu"),
            ],
            [r(56, 18, "1.262.447"), r(56, 24, "718"), r(56, 29, "830.843")],
            [r(56, 19, "1.024.712"), r(56, 30, "369.608")],
            "SUM_OF_OTHER_INTEREST_AND_FEE_SOURCES",
        ),
        d(
            983,
            "CREDIT_INTEREST",
            56,
            20,
            "Lãi phải thu từ hoạt động tín dụng",
            (21, "10.755.619"),
            (22, "6.051.730"),
        ),
        d(
            985,
            "DERIVATIVE_INTEREST",
            56,
            25,
            "Lãi phải thu từ công cụ tài chính phái sinh",
            (26, "1.317.350"),
            (27, "885.722"),
        ),
        d(
            987,
            "OTHER_ASSET_BRANCH",
            56,
            34,
            "Tài sản Có khác",
            (59, "6.381.713"),
            (60, "6.547.735"),
        ),
        d(990, "MATERIAL", 56, 41, "Vật liệu", (42, "28.999"), (43, "11.637")),
        d(
            989,
            "PREPAID_COST",
            56,
            44,
            "Chi phí trả trước chờ phân bổ",
            (45, "5.783.367"),
            (46, "5.901.310"),
        ),
        d(
            993,
            "COLLATERAL_ASSET",
            56,
            47,
            "Tài sản bảo đảm nhận thay thế cho việc thực hiện nghĩa vụ của bên bảo đảm",
            (50, "568.108"),
            (51, "593.478"),
        ),
        d(
            994,
            "COLLATERAL_REAL_ESTATE",
            56,
            52,
            "Trong đó: Bất động sản",
            (53, "568.108"),
            (54, "593.478"),
        ),
    ]
    equations = [
        e(
            "RECEIVABLE_CHILDREN_TO_TOTAL",
            "CURRENT",
            [
                r(55, 16, "571.962"),
                r(55, 19, "11.432.753"),
                r(55, 52, "5.474.874"),
                r(55, 55, "43.092"),
            ],
            r(55, 57, "17.522.681"),
        ),
        e(
            "RECEIVABLE_CHILDREN_TO_TOTAL",
            "COMPARATIVE",
            [r(55, 17, "281.942"), r(55, 20, "6.143.905"), r(55, 53, "85.071"), r(55, 56, "5.017")],
            r(55, 58, "6.515.935"),
        ),
        e(
            "EXTERNAL_DETAIL_TO_TOTAL",
            "CURRENT",
            [
                r(55, 23, "3.197.773"),
                r(55, 27, "87.709"),
                r(55, 30, "36.061"),
                r(55, 33, "2.163.423"),
                r(55, 36, "453.295"),
                r(55, 39, "2.169.215"),
                r(55, 42, "400.932"),
                r(55, 46, "1.311.633"),
                r(55, 49, "1.612.712"),
            ],
            r(55, 19, "11.432.753"),
        ),
        e(
            "EXTERNAL_DETAIL_TO_TOTAL",
            "COMPARATIVE",
            [
                r(55, 24, "162.855"),
                r(55, 31, "21.168"),
                r(55, 34, "1.365.794"),
                r(55, 37, "84.077"),
                r(55, 40, "1.414.058"),
                r(55, 43, "363.998"),
                r(55, 47, "518.012"),
                r(55, 50, "2.213.943"),
            ],
            r(55, 20, "6.143.905"),
        ),
        e(
            "QUALITY_GRADES_TO_TOTAL",
            "CURRENT",
            [r(55, 69, "87.709"), r(55, 71, "84.077")],
            r(55, 73, "171.786"),
        ),
        e("QUALITY_GRADES_TO_TOTAL", "COMPARATIVE", [r(55, 72, "84.077")], r(55, 74, "84.077")),
        e(
            "INTEREST_COMPONENTS_TO_TOTAL",
            "CURRENT",
            [
                r(56, 15, "112.249"),
                r(56, 18, "1.262.447"),
                r(56, 21, "10.755.619"),
                r(56, 24, "718"),
                r(56, 26, "1.317.350"),
                r(56, 29, "830.843"),
            ],
            r(56, 31, "14.279.226"),
        ),
        e(
            "INTEREST_COMPONENTS_TO_TOTAL",
            "COMPARATIVE",
            [
                r(56, 16, "52.297"),
                r(56, 19, "1.024.712"),
                r(56, 22, "6.051.730"),
                r(56, 27, "885.722"),
                r(56, 30, "369.608"),
            ],
            r(56, 32, "8.384.069"),
        ),
        e(
            "OTHER_ASSET_CHILDREN_TO_TOTAL",
            "CURRENT",
            [r(56, 42, "28.999"), r(56, 45, "5.783.367"), r(56, 50, "568.108"), r(56, 56, "1.239")],
            r(56, 59, "6.381.713"),
        ),
        e(
            "OTHER_ASSET_CHILDREN_TO_TOTAL",
            "COMPARATIVE",
            [
                r(56, 43, "11.637"),
                r(56, 46, "5.901.310"),
                r(56, 51, "593.478"),
                r(56, 58, "41.310"),
            ],
            r(56, 60, "6.547.735"),
        ),
    ]
    unresolved = [
        _open_row(
            base,
            "A2025-OA-013",
            55,
            35,
            "Phải thu bán tài sản tài chính",
            [(36, "453.295")],
            [(37, "84.077")],
            "The source meaning is broader than ReportNormId 976, which is specifically sale of securities.",
        ),
        _open_row(
            base,
            "A2025-OA-014",
            55,
            44,
            "Dự phòng phí và bồi thường nghiệp vụ nhượng tái bảo hiểm",
            [(46, "1.311.633")],
            [(47, "518.012")],
            "No exact child exists in the current TM other-assets family.",
        ),
        _open_row(
            base,
            "A2025-OA-015",
            55,
            68,
            "Nợ đủ tiêu chuẩn",
            [(69, "87.709")],
            [],
            "The comparative cell is a visible dash and is not promoted without bound dash geometry.",
        ),
        _open_row(
            base,
            "A2025-OA-016",
            56,
            55,
            "Tài sản có khác",
            [(56, "1.239")],
            [],
            "The comparative cell is a visible dash and is not promoted without bound dash geometry.",
        ),
        _open_row(
            base,
            "A2025-OA-017",
            56,
            57,
            "Lợi thế thương mại",
            [],
            [(58, "41.310")],
            "The current cell is a visible dash and is not promoted without bound dash geometry.",
        ),
        _open_row(
            base,
            "A2025-OA-018",
            57,
            7,
            "Dự phòng rủi ro cho các tài sản Có nội bảng khác",
            [(32, "190.401")],
            [(33, "226.231")],
            "The 966–1023 schema family has no exact provision-balance and movement branch.",
        ),
    ]
    return _present(
        base,
        code="VPB",
        owner=(55, 5, "TÀI SẢN CÓ KHÁC"),
        page_span=(55, 57),
        mappings=mappings,
        equations=equations,
        unresolved=unresolved,
    )


def _hdb_review(base: ModuleType) -> dict[str, Any]:
    d, m, r, label, e = (
        base._direct,
        base._mapping,
        base._ref,
        base._label,
        base._equation,
    )
    mappings = [
        d(
            967,
            "RECEIVABLES",
            42,
            88,
            "Các khoản phải thu",
            (106, "22.309.755"),
            (107, "46.334.855"),
        ),
        d(
            968,
            "CONSTRUCTION_IN_PROGRESS",
            42,
            94,
            "Chi phí xây dựng cơ bản dở dang",
            (95, "1.648.644"),
            (96, "1.710.680"),
        ),
        d(
            969,
            "FIXED_ASSET_PURCHASE",
            42,
            97,
            "Mua sắm tài sản cố định",
            (98, "890.467"),
            (99, "690.030"),
        ),
        d(
            971,
            "EXTERNAL_RECEIVABLES",
            42,
            100,
            "Các khoản phải thu bên ngoài",
            (101, "19.402.778"),
            (102, "43.775.610"),
        ),
        m(
            5976,
            "WITHOUT_RECOURSE_DOCUMENT_RECEIVABLE",
            [
                label(
                    43,
                    14,
                    "Phải thu từ nghiệp vụ mua hẳn miễn truy đòi bộ chứng từ do Ngân hàng phát hành",
                ),
                label(
                    43,
                    18,
                    "Phải thu từ nghiệp vụ mua hẳn miễn truy đòi bộ chứng từ do TCTD khác phát hành",
                ),
            ],
            [r(43, 15, "8.827.683"), r(43, 19, "3.593.764")],
            [r(43, 16, "33.641.885"), r(43, 20, "3.610.437")],
            "SUM_OF_TWO_DOCUMENT_RECEIVABLE_VARIANTS",
        ),
        d(
            5975,
            "PAYMENT_SERVICE_RECEIVABLE",
            43,
            22,
            "Phải thu tổ chức thẻ",
            (23, "5.621.500"),
            (24, "5.652.930"),
        ),
        d(973, "DEPOSITS_COLLATERAL", 43, 25, "Ký quỹ, đặt cọc", (26, "111.545"), (27, "104.716")),
        d(
            975,
            "ADVANCE",
            43,
            28,
            "Tạm ứng chi phí xử lý tài sản đảm bảo",
            (29, "149.591"),
            (30, "93.442"),
        ),
        d(981, "OTHER_RECEIVABLE", 43, 33, "Khác", (34, "1.098.695"), (35, "467.200")),
        d(
            982,
            "INTEREST_FEE_RECEIVABLES",
            43,
            38,
            "Các khoản lãi, phí phải thu",
            (64, "6.221.116"),
            (65, "5.383.522"),
        ),
        d(
            983,
            "CREDIT_INTEREST",
            43,
            43,
            "Lãi phải thu từ hoạt động tín dụng",
            (44, "4.339.475"),
            (45, "3.754.327"),
        ),
        d(
            984,
            "DEPOSIT_INTEREST",
            43,
            56,
            "Lãi phải thu từ tiền gửi",
            (57, "248.627"),
            (58, "121.651"),
        ),
        m(
            986,
            "OTHER_INTEREST_AND_FEES",
            [
                label(43, 46, "Lãi phải thu từ đầu tư chứng khoán"),
                label(43, 49, "Phí phải thu từ nghiệp vụ L/C"),
                label(43, 52, "Phí phải thu từ nghiệp vụ mua hẳn miễn truy đòi bộ chứng từ"),
                label(43, 59, "Lãi phải thu từ nghiệp vụ mua nợ"),
                label(43, 61, "Lãi và phí phải thu khác"),
            ],
            [
                r(43, 47, "1.294.068"),
                r(43, 50, "33.563"),
                r(43, 53, "66.035"),
                r(43, 60, "117.410"),
                r(43, 62, "121.938"),
            ],
            [
                r(43, 48, "521.369"),
                r(43, 51, "592.308"),
                r(43, 54, "259.889"),
                r(43, 63, "133.978"),
            ],
            "SUM_OF_OTHER_INTEREST_AND_FEE_SOURCES",
        ),
        d(
            987,
            "OTHER_ASSET_BRANCH",
            43,
            67,
            "Tài sản Có khác",
            (89, "11.119.977"),
            (90, "4.216.206"),
        ),
        m(
            989,
            "PREPAID_COST",
            [
                label(43, 73, "Tạm ứng cho khoản tiền gửi, tiết kiệm lãi trả trước"),
                label(43, 76, "Chi phí trả trước chờ phân bổ"),
            ],
            [r(43, 74, "5.084.540"), r(43, 77, "5.645.476")],
            [r(43, 75, "1.981.418"), r(43, 78, "1.849.528")],
            "SUM_OF_PREPAID_SOURCE_VARIANTS",
        ),
        d(
            993,
            "COLLATERAL_ASSET",
            43,
            79,
            "Tài sản bảo đảm đã chuyển quyền sở hữu cho TCTD chờ xử lý",
            (80, "229.044"),
            (81, "229.044"),
        ),
        d(990, "MATERIAL", 43, 83, "Vật liệu và công cụ", (84, "157.467"), (85, "152.766")),
        d(997, "OTHER_ASSET", 43, 86, "Tài sản Có khác", (87, "3.450"), (88, "3.450")),
        d(
            1018,
            "OTHER_ASSET_CREDIT_QUALITY",
            44,
            8,
            "Phân tích chất lượng tài sản Có khác được phân loại là tài sản có rủi ro tín dụng",
            (17, "3.593.764"),
            (18, "3.610.437"),
        ),
        d(1019, "GRADE_1", 44, 14, "Nợ đủ tiêu chuẩn", (15, "3.593.764"), (16, "3.610.437")),
    ]
    equations = [
        e(
            "RECEIVABLE_CHILDREN_TO_TOTAL",
            "CURRENT",
            [
                r(42, 95, "1.648.644"),
                r(42, 98, "890.467"),
                r(42, 101, "19.402.778"),
                r(42, 104, "367.866"),
            ],
            r(42, 106, "22.309.755"),
        ),
        e(
            "RECEIVABLE_CHILDREN_TO_TOTAL",
            "COMPARATIVE",
            [
                r(42, 96, "1.710.680"),
                r(42, 99, "690.030"),
                r(42, 102, "43.775.610"),
                r(42, 105, "158.535"),
            ],
            r(42, 107, "46.334.855"),
        ),
        e(
            "EXTERNAL_DETAIL_TO_TOTAL",
            "CURRENT",
            [
                r(43, 15, "8.827.683"),
                r(43, 19, "3.593.764"),
                r(43, 23, "5.621.500"),
                r(43, 26, "111.545"),
                r(43, 29, "149.591"),
                r(43, 34, "1.098.695"),
            ],
            r(42, 101, "19.402.778"),
        ),
        e(
            "EXTERNAL_DETAIL_TO_TOTAL",
            "COMPARATIVE",
            [
                r(43, 16, "33.641.885"),
                r(43, 20, "3.610.437"),
                r(43, 24, "5.652.930"),
                r(43, 27, "104.716"),
                r(43, 30, "93.442"),
                r(43, 32, "205.000"),
                r(43, 35, "467.200"),
            ],
            r(42, 102, "43.775.610"),
        ),
        e(
            "INTEREST_COMPONENTS_TO_TOTAL",
            "CURRENT",
            [
                r(43, 44, "4.339.475"),
                r(43, 47, "1.294.068"),
                r(43, 50, "33.563"),
                r(43, 53, "66.035"),
                r(43, 57, "248.627"),
                r(43, 60, "117.410"),
                r(43, 62, "121.938"),
            ],
            r(43, 64, "6.221.116"),
        ),
        e(
            "INTEREST_COMPONENTS_TO_TOTAL",
            "COMPARATIVE",
            [
                r(43, 45, "3.754.327"),
                r(43, 48, "521.369"),
                r(43, 51, "592.308"),
                r(43, 54, "259.889"),
                r(43, 58, "121.651"),
                r(43, 63, "133.978"),
            ],
            r(43, 65, "5.383.522"),
        ),
        e(
            "OTHER_ASSET_CHILDREN_TO_TOTAL",
            "CURRENT",
            [
                r(43, 74, "5.084.540"),
                r(43, 77, "5.645.476"),
                r(43, 80, "229.044"),
                r(43, 84, "157.467"),
                r(43, 87, "3.450"),
            ],
            r(43, 89, "11.119.977"),
        ),
        e(
            "OTHER_ASSET_CHILDREN_TO_TOTAL",
            "COMPARATIVE",
            [
                r(43, 75, "1.981.418"),
                r(43, 78, "1.849.528"),
                r(43, 81, "229.044"),
                r(43, 85, "152.766"),
                r(43, 88, "3.450"),
            ],
            r(43, 90, "4.216.206"),
        ),
        e("QUALITY_GRADES_TO_TOTAL", "CURRENT", [r(44, 15, "3.593.764")], r(44, 17, "3.593.764")),
        e(
            "QUALITY_GRADES_TO_TOTAL",
            "COMPARATIVE",
            [r(44, 16, "3.610.437")],
            r(44, 18, "3.610.437"),
        ),
    ]
    unresolved = [
        _open_row(
            base,
            "A2025-OA-019",
            42,
            103,
            "Các khoản tạm ứng và phải thu nội bộ",
            [(104, "367.866")],
            [(105, "158.535")],
            "One printed row combines advances and internal receivables; it cannot be split between ReportNormIds 975 and 970.",
        ),
        _open_row(
            base,
            "A2025-OA-020",
            43,
            31,
            "Phải thu từ thanh lý TSCĐ",
            [],
            [(32, "205.000")],
            "The current cell is a visible dash; no exact schema child exists and the row is not forced into other receivables.",
        ),
        _open_row(
            base,
            "A2025-OA-021",
            44,
            20,
            "Dự phòng rủi ro các tài sản Có nội bảng khác",
            [(26, "54.215")],
            [(27, "46.926")],
            "The 966–1023 schema family has no exact provision-balance and movement branch.",
        ),
    ]
    return _present(
        base,
        code="HDB",
        owner=(42, 86, "TÀI SẢN CÓ KHÁC"),
        page_span=(42, 44),
        mappings=mappings,
        equations=equations,
        unresolved=unresolved,
    )


def _vcb_review(base: ModuleType) -> dict[str, Any]:
    d, m, r, label, e = (
        base._direct,
        base._mapping,
        base._ref,
        base._label,
        base._equation,
    )
    mappings = [
        d(967, "RECEIVABLES", 50, 11, "Các khoản phải thu", (24, "17.577.148"), (25, "14.040.294")),
        d(
            970,
            "INTERNAL_RECEIVABLES",
            50,
            17,
            "Các khoản phải thu nội bộ",
            (18, "2.095.502"),
            (19, "1.019.327"),
        ),
        d(
            971,
            "EXTERNAL_RECEIVABLES",
            50,
            20,
            "Các khoản phải thu bên ngoài",
            (21, "15.481.646"),
            (22, "13.020.967"),
        ),
        d(
            6007,
            "CAPEX_RECEIVABLE",
            50,
            33,
            "Tạm ứng mua sắm tài sản cố định",
            (34, "4.955.332"),
            (35, "978.017"),
        ),
        m(
            974,
            "TAX_OVERPAYMENT_DEDUCTIBLE",
            [
                label(50, 39, "Thuế thu nhập doanh nghiệp nộp thừa"),
                label(50, 42, "Thuế giá trị gia tăng được khấu trừ"),
                label(50, 45, "Tạm ứng thuế khác"),
            ],
            [r(50, 40, "492.462"), r(50, 43, "100.407"), r(50, 46, "2")],
            [r(50, 41, "490.936"), r(50, 44, "31.827"), r(50, 47, "2")],
            "SUM_OF_VISIBLE_TAX_RECEIVABLES",
        ),
        d(
            968,
            "CONSTRUCTION_IN_PROGRESS",
            50,
            48,
            "Chi phí xây dựng cơ bản dở dang",
            (49, "410.794"),
            (50, "339.472"),
        ),
        d(
            5976,
            "WITHOUT_RECOURSE_DOCUMENT_RECEIVABLE",
            50,
            51,
            "Phải thu trong hoạt động mua hẳn miễn truy đòi bộ chứng từ theo thư tín dụng",
            (53, "7.860.768"),
            (54, "9.453.064"),
        ),
        d(
            981,
            "OTHER_RECEIVABLE",
            50,
            55,
            "Các khoản phải thu khác",
            (56, "1.384.964"),
            (57, "1.341.510"),
        ),
        d(
            1018,
            "OTHER_ASSET_CREDIT_QUALITY",
            51,
            9,
            "Phân tích chất lượng các khoản phải thu trong hoạt động mua hẳn miễn truy đòi",
            (20, "1.588.195"),
            (21, "398.026"),
        ),
        d(1019, "GRADE_1", 51, 16, "Nợ đủ tiêu chuẩn", (17, "1.588.195"), (18, "398.026")),
        d(
            982,
            "INTEREST_FEE_RECEIVABLES",
            51,
            24,
            "Các khoản lãi, phí phải thu",
            (46, "10.007.221"),
            (47, "8.868.303"),
        ),
        d(
            983,
            "CREDIT_INTEREST",
            51,
            31,
            "Từ cho vay khách hàng",
            (32, "4.686.096"),
            (33, "3.914.946"),
        ),
        d(
            984,
            "DEPOSIT_INTEREST",
            51,
            34,
            "Từ tiền gửi và cho vay các TCTD khác",
            (35, "884.249"),
            (36, "827.030"),
        ),
        m(
            986,
            "OTHER_INTEREST_AND_FEES",
            [label(51, 37, "Từ các khoản chứng khoán đầu tư"), label(51, 43, "Phí phải thu")],
            [r(51, 38, "3.858.648"), r(51, 44, "63.815")],
            [r(51, 39, "3.786.511"), r(51, 45, "7.793")],
            "SUM_OF_OTHER_INTEREST_AND_FEE_SOURCES",
        ),
        d(
            985,
            "DERIVATIVE_INTEREST",
            51,
            40,
            "Từ các giao dịch phái sinh",
            (41, "514.413"),
            (42, "332.023"),
        ),
        d(
            987,
            "OTHER_ASSET_BRANCH",
            51,
            59,
            "Tài sản Có khác",
            (79, "5.951.102"),
            (80, "6.516.040"),
        ),
        d(
            973,
            "RENT_DEPOSIT",
            51,
            64,
            "Đặt cọc tiền thuê nhà, thuê tài sản cố định",
            (65, "829.246"),
            (66, "897.829"),
        ),
        d(990, "MATERIAL", 51, 67, "Vật liệu", (68, "163.330"), (69, "188.120")),
        d(
            991,
            "PAYMENT_ADVANCE",
            51,
            70,
            "Tạm ứng thanh toán thẻ",
            (71, "1.808.814"),
            (72, "1.607.952"),
        ),
        d(
            989,
            "PREPAID_COST",
            51,
            73,
            "Tiền thuê đất trả tiền trước một lần",
            (74, "830.140"),
            (75, "852.773"),
        ),
        d(997, "OTHER_ASSET", 51, 76, "Tài sản Có khác", (77, "2.319.572"), (78, "2.969.366")),
    ]
    equations = [
        e(
            "INTERNAL_PLUS_EXTERNAL_TO_RECEIVABLES",
            "CURRENT",
            [r(50, 18, "2.095.502"), r(50, 21, "15.481.646")],
            r(50, 24, "17.577.148"),
        ),
        e(
            "INTERNAL_PLUS_EXTERNAL_TO_RECEIVABLES",
            "COMPARATIVE",
            [r(50, 19, "1.019.327"), r(50, 22, "13.020.967")],
            r(50, 25, "14.040.294"),
        ),
        e(
            "EXTERNAL_DETAIL_TO_TOTAL",
            "CURRENT",
            [
                r(50, 34, "4.955.332"),
                r(50, 37, "276.917"),
                r(50, 40, "492.462"),
                r(50, 43, "100.407"),
                r(50, 46, "2"),
                r(50, 49, "410.794"),
                r(50, 53, "7.860.768"),
                r(50, 56, "1.384.964"),
            ],
            r(50, 21, "15.481.646"),
        ),
        e(
            "EXTERNAL_DETAIL_TO_TOTAL",
            "COMPARATIVE",
            [
                r(50, 35, "978.017"),
                r(50, 38, "386.139"),
                r(50, 41, "490.936"),
                r(50, 44, "31.827"),
                r(50, 47, "2"),
                r(50, 50, "339.472"),
                r(50, 54, "9.453.064"),
                r(50, 57, "1.341.510"),
            ],
            r(50, 22, "13.020.967"),
        ),
        e("QUALITY_GRADES_TO_TOTAL", "CURRENT", [r(51, 17, "1.588.195")], r(51, 20, "1.588.195")),
        e("QUALITY_GRADES_TO_TOTAL", "COMPARATIVE", [r(51, 18, "398.026")], r(51, 21, "398.026")),
        e(
            "INTEREST_COMPONENTS_TO_TOTAL",
            "CURRENT",
            [
                r(51, 32, "4.686.096"),
                r(51, 35, "884.249"),
                r(51, 38, "3.858.648"),
                r(51, 41, "514.413"),
                r(51, 44, "63.815"),
            ],
            r(51, 46, "10.007.221"),
        ),
        e(
            "INTEREST_COMPONENTS_TO_TOTAL",
            "COMPARATIVE",
            [
                r(51, 33, "3.914.946"),
                r(51, 36, "827.030"),
                r(51, 39, "3.786.511"),
                r(51, 42, "332.023"),
                r(51, 45, "7.793"),
            ],
            r(51, 47, "8.868.303"),
        ),
        e(
            "OTHER_ASSET_CHILDREN_TO_TOTAL",
            "CURRENT",
            [
                r(51, 65, "829.246"),
                r(51, 68, "163.330"),
                r(51, 71, "1.808.814"),
                r(51, 74, "830.140"),
                r(51, 77, "2.319.572"),
            ],
            r(51, 79, "5.951.102"),
        ),
        e(
            "OTHER_ASSET_CHILDREN_TO_TOTAL",
            "COMPARATIVE",
            [
                r(51, 66, "897.829"),
                r(51, 69, "188.120"),
                r(51, 72, "1.607.952"),
                r(51, 75, "852.773"),
                r(51, 78, "2.969.366"),
            ],
            r(51, 80, "6.516.040"),
        ),
    ]
    unresolved = [
        _open_row(
            base,
            "A2025-OA-022",
            50,
            36,
            "Phải thu từ ngân sách Nhà nước về hỗ trợ lãi suất",
            [(37, "276.917")],
            [(38, "386.139")],
            "The source is a government-budget receivable, not a receivable from the State Bank under ReportNormId 979.",
        ),
        _open_row(
            base,
            "A2025-OA-023",
            51,
            49,
            "Tài sản thuế thu nhập hoãn lại",
            [(56, "13.072")],
            [(57, "991.748")],
            "No exact child exists in the current TM other-assets schema family.",
        ),
        _open_row(
            base,
            "A2025-OA-024",
            51,
            81,
            "Các khoản dự phòng rủi ro cho các tài sản Có nội bảng khác",
            [(82, "(17.706)")],
            [(83, "(14.037)")],
            "The 966–1023 schema family has no exact provision-balance and movement branch.",
        ),
    ]
    return _present(
        base,
        code="VCB",
        owner=(50, 9, "Tài sản Có khác"),
        page_span=(50, 52),
        mappings=mappings,
        equations=equations,
        unresolved=unresolved,
    )


def _ctg_review(base: ModuleType) -> dict[str, Any]:
    d, r, e = base._direct, base._ref, base._equation
    mappings = [
        d(967, "RECEIVABLES", 50, 8, "Các khoản phải thu", (27, "33.305.817"), (28, "27.766.899")),
        d(
            968,
            "CONSTRUCTION_IN_PROGRESS",
            50,
            14,
            "Chi phí xây dựng cơ bản dở dang",
            (15, "5.593.474"),
            (16, "5.678.511"),
        ),
        d(
            969,
            "FIXED_ASSET_MAJOR_REPAIR",
            50,
            17,
            "Mua sắm sửa chữa lớn TSCĐ",
            (18, "1.308.383"),
            (19, "1.159.331"),
        ),
        d(
            971,
            "EXTERNAL_RECEIVABLES",
            50,
            21,
            "Phải thu bên ngoài",
            (22, "26.072.668"),
            (23, "20.722.772"),
        ),
        d(
            987,
            "OTHER_ASSET_BRANCH",
            50,
            49,
            "Tài sản Có khác",
            (63, "5.262.441"),
            (64, "3.715.565"),
        ),
        d(990, "MATERIAL", 50, 54, "Vật liệu và công cụ", (55, "202.374"), (56, "316.109")),
        d(
            989,
            "PREPAID_COST",
            50,
            57,
            "Chi phí trả trước chờ phân bổ",
            (58, "3.468.820"),
            (59, "3.382.712"),
        ),
        d(997, "OTHER_ASSET", 50, 60, "Tài sản có khác", (61, "1.591.247"), (62, "16.744")),
    ]
    equations = [
        e(
            "RECEIVABLE_CHILDREN_TO_TOTAL",
            "CURRENT",
            [
                r(50, 15, "5.593.474"),
                r(50, 18, "1.308.383"),
                r(50, 22, "26.072.668"),
                r(50, 25, "331.292"),
            ],
            r(50, 27, "33.305.817"),
        ),
        e(
            "RECEIVABLE_CHILDREN_TO_TOTAL",
            "COMPARATIVE",
            [
                r(50, 16, "5.678.511"),
                r(50, 19, "1.159.331"),
                r(50, 23, "20.722.772"),
                r(50, 26, "206.285"),
            ],
            r(50, 28, "27.766.899"),
        ),
        e(
            "OTHER_ASSET_CHILDREN_TO_TOTAL",
            "CURRENT",
            [r(50, 55, "202.374"), r(50, 58, "3.468.820"), r(50, 61, "1.591.247")],
            r(50, 63, "5.262.441"),
        ),
        e(
            "OTHER_ASSET_CHILDREN_TO_TOTAL",
            "COMPARATIVE",
            [r(50, 56, "316.109"), r(50, 59, "3.382.712"), r(50, 62, "16.744")],
            r(50, 64, "3.715.565"),
        ),
    ]
    unresolved = [
        _open_row(
            base,
            "A2025-OA-025",
            50,
            24,
            "Các khoản tạm ứng và phải thu nội bộ",
            [(25, "331.292")],
            [(26, "206.285")],
            "One printed row combines advances and internal receivables; it cannot be split between ReportNormIds 975 and 970.",
        ),
        _open_row(
            base,
            "A2025-OA-026",
            50,
            66,
            "Các khoản dự phòng rủi ro cho các tài sản Có nội bảng khác",
            [(82, "108.723")],
            [(83, "106.441")],
            "The 966–1023 schema family has no exact provision-balance and movement branch.",
        ),
    ]
    return _present(
        base,
        code="CTG",
        owner=(50, 6, "TÀI SẢN CÓ KHÁC"),
        page_span=(50, 51),
        mappings=mappings,
        equations=equations,
        unresolved=unresolved,
    )


def _bid_review(base: ModuleType) -> dict[str, Any]:
    d, r, e = base._direct, base._ref, base._equation
    mappings = [
        d(
            966,
            "OTHER_ASSETS_ROOT_NET",
            49,
            4,
            "TÀI SẢN CÓ KHÁC",
            (47, "65.645.533"),
            (48, "52.885.724"),
            "VISIBLE_FAMILY_NET_TOTAL",
        ),
        d(967, "RECEIVABLES", 49, 10, "Các khoản phải thu", (11, "32.944.317"), (12, "25.773.422")),
        d(
            968,
            "CONSTRUCTION_IN_PROGRESS",
            49,
            14,
            "Chi phí xây dựng cơ bản dở dang",
            (15, "875.702"),
            (16, "1.028.397"),
        ),
        d(
            982,
            "INTEREST_FEE_RECEIVABLES",
            49,
            22,
            "Các khoản lãi, phí phải thu",
            (23, "28.145.159"),
            (24, "23.146.980"),
        ),
        d(
            987,
            "OTHER_ASSET_BRANCH",
            49,
            28,
            "Tài sản Có khác",
            (29, "4.736.845"),
            (30, "4.242.266"),
        ),
        d(
            988,
            "ENTRUSTED_INVESTMENT",
            49,
            31,
            "Các hợp đồng ủy thác đầu tư",
            (32, "82.960"),
            (33, "82.960"),
        ),
        d(989, "PREPAID_COST", 49, 34, "Chi phí chờ phân bổ", (35, "2.092.370"), (36, "2.220.210")),
        d(
            993,
            "COLLATERAL_ASSET",
            49,
            37,
            "Tài sản gán nợ chờ xử lý",
            (38, "55.420"),
            (39, "55.420"),
        ),
        d(997, "OTHER_ASSET", 49, 40, "Tài sản Có khác", (41, "2.506.095"), (42, "1.883.676")),
        d(
            970,
            "INTERNAL_RECEIVABLES",
            49,
            82,
            "Các khoản phải thu nội bộ",
            (83, "917.127"),
            (84, "592.904"),
        ),
        d(
            971,
            "EXTERNAL_RECEIVABLES",
            49,
            85,
            "Các khoản phải thu bên ngoài",
            (86, "31.151.488"),
            (87, "24.152.121"),
        ),
        d(
            5975,
            "PAYMENT_SERVICE_RECEIVABLE",
            49,
            89,
            "Phải thu trung gian thanh toán",
            (90, "2.972.925"),
            (91, "1.236.204"),
        ),
        d(
            973,
            "DEPOSITS_COLLATERAL",
            49,
            92,
            "Ký quỹ, thế chấp, đặt cọc",
            (93, "784.710"),
            (94, "588.562"),
        ),
        d(
            979,
            "STATE_BANK_RECEIVABLE",
            49,
            98,
            "Phải thu từ NHNN về cho vay hỗ trợ lãi suất",
            (99, "265.624"),
            (100, "275.708"),
        ),
        d(
            978,
            "INSURANCE_SUBSIDIARY_RECEIVABLE",
            49,
            101,
            "Phải thu khách hàng trong hoạt động bảo hiểm của BIC",
            (102, "475.716"),
            (103, "289.034"),
        ),
        d(
            976,
            "SECURITIES_SALE_RECEIVABLE",
            49,
            105,
            "Phải thu trong hoạt động giao dịch chứng khoán của BSC",
            (106, "4.265"),
            (107, "1.501"),
        ),
    ]
    equations = [
        e(
            "FAMILY_COMPONENTS_LESS_PROVISION_TO_NET_TOTAL",
            "CURRENT",
            [
                r(49, 11, "32.944.317"),
                r(49, 23, "28.145.159"),
                r(49, 26, "27.682"),
                r(49, 29, "4.736.845"),
                r(49, 44, "(208.470)"),
            ],
            r(49, 47, "65.645.533"),
        ),
        e(
            "FAMILY_COMPONENTS_LESS_PROVISION_TO_NET_TOTAL",
            "COMPARATIVE",
            [
                r(49, 12, "25.773.422"),
                r(49, 24, "23.146.980"),
                r(49, 27, "27.056"),
                r(49, 30, "4.242.266"),
                r(49, 45, "(304.000)"),
            ],
            r(49, 48, "52.885.724"),
        ),
        e(
            "RECEIVABLE_SUBBRANCHES_TO_TOTAL",
            "CURRENT",
            [r(49, 15, "875.702"), r(49, 19, "32.068.615")],
            r(49, 11, "32.944.317"),
        ),
        e(
            "RECEIVABLE_SUBBRANCHES_TO_TOTAL",
            "COMPARATIVE",
            [r(49, 16, "1.028.397"), r(49, 20, "24.745.025")],
            r(49, 12, "25.773.422"),
        ),
        e(
            "INTERNAL_PLUS_EXTERNAL_TO_OTHER_RECEIVABLES",
            "CURRENT",
            [r(49, 83, "917.127"), r(49, 86, "31.151.488")],
            r(49, 19, "32.068.615"),
        ),
        e(
            "INTERNAL_PLUS_EXTERNAL_TO_OTHER_RECEIVABLES",
            "COMPARATIVE",
            [r(49, 84, "592.904"), r(49, 87, "24.152.121")],
            r(49, 20, "24.745.025"),
        ),
        e(
            "OTHER_ASSET_CHILDREN_TO_TOTAL",
            "CURRENT",
            [
                r(49, 32, "82.960"),
                r(49, 35, "2.092.370"),
                r(49, 38, "55.420"),
                r(49, 41, "2.506.095"),
            ],
            r(49, 29, "4.736.845"),
        ),
        e(
            "OTHER_ASSET_CHILDREN_TO_TOTAL",
            "COMPARATIVE",
            [
                r(49, 33, "82.960"),
                r(49, 36, "2.220.210"),
                r(49, 39, "55.420"),
                r(49, 42, "1.883.676"),
            ],
            r(49, 30, "4.242.266"),
        ),
    ]
    unresolved = [
        _open_row(
            base,
            "A2025-OA-027",
            49,
            18,
            "Các khoản phải thu khác",
            [(19, "32.068.615")],
            [(20, "24.745.025")],
            "This source group contains internal and external receivables and is not the narrow ReportNormId 981 leaf.",
        ),
        _open_row(
            base,
            "A2025-OA-028",
            49,
            25,
            "Tài sản thuế thu nhập doanh nghiệp hoãn lại",
            [(26, "27.682")],
            [(27, "27.056")],
            "No exact child exists in the current TM other-assets schema family.",
        ),
        _open_row(
            base,
            "A2025-OA-029",
            49,
            43,
            "Dự phòng rủi ro cho các tài sản Có nội bảng khác",
            [(44, "(208.470)")],
            [(45, "(304.000)")],
            "The 966–1023 schema family has no exact provision-balance and movement branch.",
        ),
        _open_row(
            base,
            "A2025-OA-030",
            49,
            95,
            "Phải thu trong nghiệp vụ tài trợ thương mại",
            [(96, "24.852.386")],
            [(97, "19.883.511")],
            "No exact child exists in the current TM other-assets family.",
        ),
    ]
    return _present(
        base,
        code="BID",
        owner=(49, 4, "TÀI SẢN CÓ KHÁC"),
        page_span=(49, 50),
        mappings=mappings,
        equations=equations,
        unresolved=unresolved,
    )


def _vib_review(base: ModuleType) -> dict[str, Any]:
    d, r, e = base._direct, base._ref, base._equation
    mappings = [
        d(
            966,
            "OTHER_ASSETS_ROOT_NET",
            44,
            5,
            "TÀI SẢN CÓ KHÁC",
            (50, "9.951.086"),
            (51, "5.663.284"),
            "VISIBLE_FAMILY_NET_TOTAL",
        ),
        d(967, "RECEIVABLES", 44, 10, "Các khoản phải thu", (11, "4.017.129"), (12, "1.952.684")),
        d(
            970,
            "INTERNAL_RECEIVABLES",
            44,
            13,
            "Các khoản phải thu nội bộ",
            (14, "430.070"),
            (15, "352.414"),
        ),
        d(
            971,
            "EXTERNAL_RECEIVABLES",
            44,
            16,
            "Các khoản phải thu bên ngoài",
            (17, "3.587.059"),
            (18, "1.600.270"),
        ),
        d(
            975,
            "ADVANCE",
            44,
            25,
            "Tạm ứng chi phí xử lý tài sản bảo đảm",
            (26, "7.448"),
            (27, "9.011"),
        ),
        d(
            981,
            "OTHER_RECEIVABLE",
            44,
            31,
            "Các khoản phải thu khác từ bên ngoài",
            (32, "1.370.000"),
            (33, "667.749"),
        ),
        d(
            6007,
            "CAPEX_RECEIVABLE",
            44,
            34,
            "Chi phí mua sắm tài sản cố định và xây dựng cơ bản dở dang",
            (36, "884.906"),
            (37, "737.714"),
        ),
        d(
            982,
            "INTEREST_FEE_RECEIVABLES",
            44,
            38,
            "Các khoản lãi, phí phải thu",
            (39, "3.902.271"),
            (40, "2.572.270"),
        ),
        d(
            987,
            "OTHER_ASSET_BRANCH",
            44,
            41,
            "Tài sản Có khác",
            (42, "2.030.721"),
            (43, "1.137.572"),
        ),
        d(
            984,
            "DEPOSIT_INTEREST",
            44,
            59,
            "Lãi phải thu từ tiền gửi",
            (60, "24.385"),
            (61, "22.249"),
        ),
        d(
            986,
            "SECURITIES_INTEREST",
            44,
            62,
            "Lãi phải thu từ đầu tư chứng khoán",
            (63, "1.212.355"),
            (64, "936.478"),
        ),
        d(
            983,
            "CREDIT_INTEREST",
            44,
            65,
            "Lãi phải thu từ hoạt động tín dụng",
            (66, "2.091.737"),
            (67, "1.469.061"),
        ),
        d(
            985,
            "DERIVATIVE_INTEREST",
            44,
            68,
            "Lãi phải thu từ công cụ tài chính phái sinh",
            (69, "573.794"),
            (70, "144.482"),
        ),
        d(990, "MATERIAL", 44, 78, "Vật liệu", (79, "19.197"), (80, "14.167")),
        d(
            993,
            "COLLATERAL_ASSET",
            44,
            81,
            "Tài sản gán nợ đã chuyển quyền sở hữu cho TCTD chờ xử lý",
            (83, "106.184"),
            (84, "69.474"),
        ),
        d(989, "PREPAID_COST", 44, 85, "Chi phí trả trước", (86, "1.036.984"), (87, "913.644")),
        d(997, "OTHER_ASSET", 44, 88, "Tài sản có khác", (89, "868.356"), (90, "140.287")),
    ]
    equations = [
        e(
            "FAMILY_COMPONENTS_LESS_PROVISION_TO_NET_TOTAL",
            "CURRENT",
            [
                r(44, 11, "4.017.129"),
                r(44, 39, "3.902.271"),
                r(44, 42, "2.030.721"),
                r(44, 45, "965"),
            ],
            r(44, 50, "9.951.086"),
        ),
        e(
            "FAMILY_COMPONENTS_LESS_PROVISION_TO_NET_TOTAL",
            "COMPARATIVE",
            [
                r(44, 12, "1.952.684"),
                r(44, 40, "2.572.270"),
                r(44, 43, "1.137.572"),
                r(44, 46, "1.002"),
                r(44, 48, "(244)"),
            ],
            r(44, 51, "5.663.284"),
        ),
        e(
            "INTERNAL_PLUS_EXTERNAL_TO_RECEIVABLES",
            "CURRENT",
            [r(44, 14, "430.070"), r(44, 17, "3.587.059")],
            r(44, 11, "4.017.129"),
        ),
        e(
            "INTERNAL_PLUS_EXTERNAL_TO_RECEIVABLES",
            "COMPARATIVE",
            [r(44, 15, "352.414"), r(44, 18, "1.600.270")],
            r(44, 12, "1.952.684"),
        ),
        e(
            "EXTERNAL_DETAIL_TO_TOTAL",
            "CURRENT",
            [
                r(44, 20, "36.602"),
                r(44, 23, "738.924"),
                r(44, 26, "7.448"),
                r(44, 29, "549.179"),
                r(44, 32, "1.370.000"),
                r(44, 36, "884.906"),
            ],
            r(44, 17, "3.587.059"),
        ),
        e(
            "EXTERNAL_DETAIL_TO_TOTAL",
            "COMPARATIVE",
            [
                r(44, 21, "35.874"),
                r(44, 24, "32.563"),
                r(44, 27, "9.011"),
                r(44, 30, "117.359"),
                r(44, 33, "667.749"),
                r(44, 37, "737.714"),
            ],
            r(44, 18, "1.600.270"),
        ),
        e(
            "INTEREST_COMPONENTS_TO_TOTAL",
            "CURRENT",
            [
                r(44, 60, "24.385"),
                r(44, 63, "1.212.355"),
                r(44, 66, "2.091.737"),
                r(44, 69, "573.794"),
            ],
            r(44, 39, "3.902.271"),
        ),
        e(
            "INTEREST_COMPONENTS_TO_TOTAL",
            "COMPARATIVE",
            [
                r(44, 61, "22.249"),
                r(44, 64, "936.478"),
                r(44, 67, "1.469.061"),
                r(44, 70, "144.482"),
            ],
            r(44, 40, "2.572.270"),
        ),
        e(
            "OTHER_ASSET_CHILDREN_TO_TOTAL",
            "CURRENT",
            [
                r(44, 79, "19.197"),
                r(44, 83, "106.184"),
                r(44, 86, "1.036.984"),
                r(44, 89, "868.356"),
            ],
            r(44, 42, "2.030.721"),
        ),
        e(
            "OTHER_ASSET_CHILDREN_TO_TOTAL",
            "COMPARATIVE",
            [r(44, 80, "14.167"), r(44, 84, "69.474"), r(44, 87, "913.644"), r(44, 90, "140.287")],
            r(44, 43, "1.137.572"),
        ),
    ]
    unresolved = [
        _open_row(
            base,
            "A2025-OA-031",
            44,
            19,
            "Phải thu từ Ngân sách Nhà nước",
            [(20, "36.602")],
            [(21, "35.874")],
            "The source does not state that this is tax overpayment/deductible tax or a State Bank receivable.",
        ),
        _open_row(
            base,
            "A2025-OA-032",
            44,
            22,
            "Phải thu từ hoạt động tài trợ thương mại",
            [(23, "738.924")],
            [(24, "32.563")],
            "No exact child exists in the current TM other-assets family.",
        ),
        _open_row(
            base,
            "A2025-OA-033",
            44,
            28,
            "Phải thu hoa hồng bảo hiểm",
            [(29, "549.179")],
            [(30, "117.359")],
            "The source does not identify the counterparty as an insurance subsidiary required by ReportNormId 978.",
        ),
        _open_row(
            base,
            "A2025-OA-034",
            44,
            44,
            "Tài sản thuế TNDN hoãn lại",
            [(45, "965")],
            [(46, "1.002")],
            "No exact child exists in the current TM other-assets schema family.",
        ),
        _open_row(
            base,
            "A2025-OA-035",
            44,
            47,
            "Các khoản dự phòng rủi ro cho các tài sản Có nội bảng khác",
            [],
            [(48, "(244)")],
            "The current cell is a visible dash and the 966–1023 family has no exact provision branch.",
        ),
    ]
    return _present(
        base,
        code="VIB",
        owner=(44, 5, "TÀI SẢN CÓ KHÁC"),
        page_span=(44, 45),
        mappings=mappings,
        equations=equations,
        unresolved=unresolved,
    )


def _review_documents(base: ModuleType) -> list[dict[str, Any]]:
    return [
        _acb_review(base),
        _mbb_review(base),
        _vpb_review(base),
        _hdb_review(base),
        _vcb_review(base),
        _ctg_review(base),
        _bid_review(base),
        _vib_review(base),
    ]


def _annual_metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "annual_source_period_document_count": sum(
            trial["source_period"] == "2025-12-31" for trial in trials
        ),
        "confirmed_bound_report_absence_count": sum(
            trial["status"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT" for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"]["complete_region_count"] == 1 for trial in trials
        ),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "open_source_row_count": sum(len(trial["unmapped_source_rows"]) for trial in trials),
        "verified_value_cell_count": sum(
            len(value["components"])
            for trial in trials
            for mapping in trial["verified_mappings"]
            for value in mapping["values"]
        ),
    }


def _configure_base() -> ModuleType:
    base = _load_module(
        "annual_2025_other_assets_mapping_base",
        "scripts/experiments/build_other_assets_8bank_codex_verified_mapping_v1.py",
    )
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
    base._REVIEW_RUN_ID = REVIEW_RUN_ID
    base._REVIEW_CHECKS = tuple(_REVIEW_CHECKS)
    base._REVIEW_SAFETY = canonical_clone_v1(_REVIEW_SAFETY)
    base._AUTHORITY = canonical_clone_v1(_AUTHORITY)
    base._SCHEMA_EXPECTED.update(
        {
            968: ("Chi phí xây dựng cơ bản dở dang", 967),
            969: ("Mua sắm sửa chữa lớn TSCĐ", 967),
            974: ("+Thuế nộp thừa, được khấu trừ", 967),
            976: ("+Phải thu từ bán chứng khoán", 967),
            978: ("+Phải thu từ Công ty Bảo hiểm là công ty con", 967),
            979: ("+Phải thu từ NHNN Việt Nam", 967),
            980: ("+Cổ tức phải thu", 967),
            988: ("-Ủy thác đầu tư", 987),
            991: ("-Thanh toán", 987),
            1011: ("Biến động chi phí XDCB dở dang", 966),
            1012: ("Số dư đầu năm", 1011),
            1013: ("Tăng trong năm", 1011),
            1014: ("Chuyển sang TSCĐ hữu hình", 1011),
            1015: ("Chuyển sang TSCĐ vô hình", 1011),
            1016: ("Chuyển sang tài sản khác", 1011),
            1017: ("Số dư cuối năm", 1011),
        }
    )
    base._review_documents = lambda: _review_documents(base)
    base._metrics = _annual_metrics
    base._source_period_status = lambda source_period: (
        "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
        if source_period == "2025-12-31"
        else (_ for _ in ()).throw(_error("annual other-assets source period drifted"))
    )
    return base


def _validate_expected_coverage(value: dict[str, Any]) -> dict[str, Any]:
    trials = value.get("trials")
    if type(trials) is not list or len(trials) != 8:
        raise _error("annual other-assets trial denominator drifted")
    if any(
        trial.get("source_period") != "2025-12-31"
        or trial.get("source_period_status")
        != "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
        or trial.get("whole_document_uniqueness", {}).get("complete_region_count") != 1
        or trial.get("status") == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT"
        for trial in trials
    ):
        raise _error("annual other-assets source period or unique-region coverage drifted")
    for trial in trials:
        code = trial["document_provenance"]
        actual = {
            mapping["schema_binding"]["report_norm_id"] for mapping in trial["verified_mappings"]
        }
        if actual != _EXPECTED_IDS[code]:
            raise _error(f"annual other-assets schema coverage drifted: {code}")
    if value.get("metrics") != _EXPECTED_METRICS:
        raise _error("annual other-assets metrics drifted")
    return value


def build_annual_2025_other_assets_pixel_review_blueprint_v1() -> dict[str, Any]:
    return _configure_base()._review_blueprint()


def build_live_annual_2025_other_assets_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    try:
        return _validate_expected_coverage(
            _configure_base().build_live_other_assets_8bank_codex_verified_mapping_v1()
        )
    except Annual2025OtherAssets8BankError:
        raise
    except Exception as error:
        raise _error(str(error)) from error


def validate_annual_2025_other_assets_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    try:
        return _validate_expected_coverage(
            _configure_base().validate_live_other_assets_8bank_codex_verified_mapping_v1(value)
        )
    except Annual2025OtherAssets8BankError:
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
    result = build_live_annual_2025_other_assets_8bank_codex_verified_mapping_v1()
    if args.write_result:
        base._write(RESULT_PATH, result)
    elif args.verify:
        payload = base.support._stable_bytes(RESULT_PATH)
        persisted = base.support._strict_json(payload, RESULT_PATH.as_posix())
        validate_annual_2025_other_assets_8bank_codex_verified_mapping_replay_v1(persisted)
        print(persisted["result_id"])
    else:
        sys.stdout.buffer.write(canonical_json_bytes_v1(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
