"""Verify annual-2025 other payables and liabilities across eight banks."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "ANNUAL_2025_OTHER_PAYABLES_LIABILITIES_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_OTHER_PAYABLES_LIABILITIES_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_OTHER_PAYABLES_LIABILITIES_8BANK_BOUNDED_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025opl8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_OTHER_PAYABLES_LIABILITIES_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025opl8bcv1:pixel-review:"
REVIEW_RUN_ID = "E-0132"
REVIEW_PATH = Path(
    "docs/experiments/E-0132-annual-2025-other-payables-liabilities-8bank-"
    "codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0132-annual-2025-other-payables-liabilities-8bank-"
    "codex-verified-mapping-v1.json"
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
EXPECTED_SCAN_ID = "oplifdsv1:scan:4fe27fcc34af5d4bb22f6a0f2bae8a6c647a993aac03d38418a9afa17bab9cae"

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_VIETOCR_"
    "BANK_BLIND_OTHER_PAYABLES_OWNER_INTERNAL_EXTERNAL_OPTIONAL_CHILD_VISIBLE_"
    "PIXEL_UPSTREAM_PPOCRV6_DASH_ZERO_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_"
    "SOURCE_DETAILS_SUBSUMED_BY_EXACT_PRINTED_GROUPS_NO_EXPORT_AUTHORITY"
)
_REVIEW_CHECKS = (
    "COMPLETE_PDF_UNIQUE_REGION",
    "OWNER_PRECEDES_INTERNAL_EXTERNAL_AND_OPTIONAL_DIRECT_CHILDREN",
    "PAIR_FIRST_GENERIC_VARIANT_GRAPH",
    "CURRENT_2025_AND_COMPARATIVE_2024_AXES",
    "VISIBLE_LOCAL_MILLION_VND_UNIT",
    "VISIBLE_PIXEL_LABELS_DIGITS_SIGNS_AND_DASHES",
    "UPSTREAM_PPOCRV6_OR_AUTHENTICATED_PIXEL_DASH_NUMERIC_CHALLENGER",
    "NESTED_SOURCE_DETAILS_RECONCILE_TO_PRINTED_GROUP_PARENT_WHEN_EXHAUSTIVE",
    "DIRECT_CHILDREN_RECONCILE_TO_PRINTED_FAMILY_TOTAL",
    "SOURCE_DETAIL_AND_GROUP_PARENT_NOT_DOUBLE_COUNTED",
    "LIVE_TM_SCHEMA_HIERARCHY_AND_DISPLAY_ORDER",
)
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "fresh_vietocr_used_as_numeric_truth": False,
    "gemma_json_used_as_mapping_or_numeric_authority": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": "VISIBLE_PDF_PIXELS_WITH_UPSTREAM_PPOCRV6_AND_ACCOUNTING",
    "reporting_period_dates_derived_from_pdf": True,
    "source_detail_and_printed_group_parent_double_counted": False,
    "source_details_without_separate_schema_leaf_subsumed_by_verified_printed_group": True,
    "visible_bound_dash_normalized_to_zero": True,
    "unbound_visible_dash_promoted_to_zero": False,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "bounded_report_family_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "comparison_period_used_as_mapping_authority": False,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "gemma_json_used_as_mapping_or_numeric_authority": False,
    "independent_pdf_pixel_and_upstream_ppocrv6_used_for_numeric_truth": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_annual_other_payables_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "reporting_period_dates_derived_from_pdf": True,
    "source_detail_and_printed_group_parent_double_counted": False,
    "text_similarity_alone_used_for_mapping": False,
}
_SCHEMA_EXPECTED = {
    1118: ("Các khoản phải trả và công nợ khác", 560, 636),
    1119: ("Các khoản phải trả nội bộ", 1118, 637),
    1120: ("Các khoản phải trả nhân viên", 1118, 638),
    1121: ("Các khoản phải trả nội bộ khác", 1118, 639),
    1122: ("Các khoản phải trả bên ngoài", 1118, 640),
    1123: ("Thuế và các khoản phải nộp Nhà nước", 1118, 641),
    1124: ("Các khoản phải trả khác", 1118, 642),
    1125: ("Dự phòng rủi ro khác", 1118, 643),
    1126: ("Quỹ khen thưởng, phúc lợi", 1118, 644),
    1127: ("Khác", 1118, 645),
}
_EXPECTED_IDS = {
    "ACB": {1118, 1119, 1122, 1123, 1124, 1126, 1127},
    "MBB": {1118, 1119, 1122, 1123, 1126, 1127},
    "VPB": {1118, 1119, 1120, 1122, 1123, 1124, 1127},
    "HDB": {1118, 1119, 1122, 1123, 1124, 1126, 1127},
    "VCB": {1118, 1119, 1122, 1126},
    "CTG": {1118, 1119, 1122, 1123, 1124, 1126, 1127},
    "BID": {1118, 1119, 1122, 1123, 1126, 1127},
    "VIB": {1118, 1119, 1120, 1121, 1122, 1123, 1124, 1126, 1127},
}
_EXPECTED_METRICS = {
    "accounting_equation_verified_count": 32,
    "authenticated_pixel_dash_zero_count": 3,
    "document_count": 8,
    "document_unique_region_count": 8,
    "mapping_verified_count": 53,
    "open_source_row_count": 0,
    "q1_source_period_caveat_document_count": 0,
    "verified_value_cell_count": 184,
}


class Annual2025OtherPayablesLiabilities8BankError(ValueError):
    """Annual other-payables evidence, accounting, schema or replay drifted."""


def _error(message: str) -> Annual2025OtherPayablesLiabilities8BankError:
    return Annual2025OtherPayablesLiabilities8BankError(message)


def _load_base() -> ModuleType:
    path = (
        PROJECT_ROOT
        / "scripts/experiments/build_other_payables_liabilities_8bank_codex_verified_mapping_v1.py"
    )
    spec = importlib.util.spec_from_file_location("annual_2025_other_payables_base", path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load other-payables support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _tp(
    base: ModuleType,
    report_norm_id: int,
    role: str,
    page: int,
    label_line: int,
    label_text: str,
    current_line: int,
    current_text: str,
    comparative_line: int,
    comparative_text: str,
    topology: str,
    extra_label_lines: Sequence[tuple[int, str]] = (),
) -> dict[str, Any]:
    return base._two_period_mapping(
        report_norm_id,
        role,
        page,
        label_line,
        label_text,
        current_line,
        current_text,
        comparative_line,
        comparative_text,
        topology,
        [base._label(page, line, text) for line, text in extra_label_lines],
    )


def _root(
    base: ModuleType,
    page: int,
    owner_line: int,
    owner_text: str,
    current: tuple[int, str],
    comparative: tuple[int, str],
) -> dict[str, Any]:
    return _tp(
        base,
        1118,
        "FAMILY_TOTAL",
        page,
        owner_line,
        owner_text,
        current[0],
        current[1],
        comparative[0],
        comparative[1],
        "PRINTED_TOTAL_AFTER_COMPLETE_SOURCE_FAMILY",
    )


def _other_aggregate(
    base: ModuleType,
    page: int,
    labels: Sequence[tuple[int, str]],
    current: Sequence[tuple[int, str] | dict[str, Any]],
    comparative: Sequence[tuple[int, str] | dict[str, Any]],
    topology: str,
) -> dict[str, Any]:
    def refs(items: Sequence[tuple[int, str] | dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            item if type(item) is dict else base._line(page, item[0], item[1]) for item in items
        ]

    return base._mapping(
        1127,
        "OTHER_DIRECT_SOURCE_ROWS",
        [base._label(page, line, text) for line, text in labels],
        {"CURRENT": refs(current), "COMPARATIVE": refs(comparative)},
        topology,
    )


def _review_documents(base: ModuleType) -> list[dict[str, Any]]:
    label, line, eq, doc = base._label, base._line, base._equation, base._doc
    mbb_science_dash = base._dash(
        67,
        [1330, 1054, 1485, 1091],
        "ab6f72bff029f8acb0218303038f8e319af5da6d16f95aa08903a342f59706cd",
    )
    ctg_receipts_dash = base._dash(
        54,
        [1130, 1508, 1285, 1544],
        "13f194a3be76a5c41756be619338723b112bfc8c7cd2f0a3d5b9cc6da646ffca",
    )
    ctg_interbank_dash = base._dash(
        54,
        [1130, 1702, 1285, 1736],
        "f8c610255fd574c5fcae8515a81219e27553de6633b533fe8460d7621feb6ccb",
    )
    documents = [
        doc(
            "ACB",
            64,
            5,
            "CÁC KHOẢN PHẢI TRẢ VÀ CÔNG NỢ KHÁC",
            [label(64, 6, "31.12.2025"), label(64, 7, "31.12.2024")],
            [label(64, 8, "Triệu VND"), label(64, 9, "Triệu VND")],
            [
                _root(
                    base,
                    64,
                    5,
                    "CÁC KHOẢN PHẢI TRẢ VÀ CÔNG NỢ KHÁC",
                    (40, "15.891.976"),
                    (41, "14.969.111"),
                ),
                _tp(
                    base,
                    1119,
                    "INTERNAL_PAYABLE",
                    64,
                    10,
                    "Các khoản phải trả nội bộ",
                    11,
                    "941.203",
                    12,
                    "1.280.584",
                    "DIRECT_CHILD_OF_OWNER",
                ),
                _tp(
                    base,
                    1122,
                    "EXTERNAL_PAYABLE",
                    64,
                    13,
                    "Các khoản phải trả cho bên ngoài",
                    14,
                    "6.924.447",
                    15,
                    "5.125.200",
                    "PRINTED_GROUP_PARENT_WITH_EXHAUSTIVE_DETAILS_NOT_DOUBLE_COUNTED",
                    (
                        (16, "Chuyển tiền phải trả"),
                        (19, "Các khoản phải nộp Ngân sách Nhà nước"),
                        (22, "Tiền giữ hộ và đợi thanh toán"),
                        (25, "Các khoản chờ thanh toán"),
                        (28, "Phải trả khác"),
                    ),
                ),
                _tp(
                    base,
                    1123,
                    "TAX_PAYABLE",
                    64,
                    19,
                    "Các khoản phải nộp Ngân sách Nhà nước",
                    20,
                    "2.174.750",
                    21,
                    "2.582.875",
                    "DETAIL_WITHIN_EXTERNAL_PARENT",
                ),
                _tp(
                    base,
                    1124,
                    "OTHER_PAYABLE",
                    64,
                    28,
                    "Phải trả khác",
                    29,
                    "659.331",
                    30,
                    "271.632",
                    "DETAIL_WITHIN_EXTERNAL_PARENT",
                ),
                _tp(
                    base,
                    1126,
                    "WELFARE_FUND",
                    64,
                    34,
                    "Quỹ khen thưởng, phúc lợi",
                    35,
                    "817.424",
                    36,
                    "847.298",
                    "DIRECT_CHILD_OF_OWNER",
                ),
                _other_aggregate(
                    base,
                    64,
                    (
                        (16, "Chuyển tiền phải trả"),
                        (22, "Tiền giữ hộ và đợi thanh toán"),
                        (25, "Các khoản chờ thanh toán"),
                        (31, "Thu nhập chưa thực hiện"),
                        (37, "Quỹ phát triển khoa học và công nghệ"),
                    ),
                    (
                        (17, "385.590"),
                        (23, "790.590"),
                        (26, "2.914.186"),
                        (32, "5.667.622"),
                        (38, "1.541.280"),
                    ),
                    (
                        (18, "376.277"),
                        (24, "220.289"),
                        (27, "1.674.127"),
                        (33, "6.235.417"),
                        (39, "1.480.612"),
                    ),
                    "SUM_OF_SOURCE_ROWS_WITHOUT_DEDICATED_SCHEMA_LEAVES_ACROSS_EXPLICIT_GROUP_CONTEXTS_NOT_ADDED_TO_GROUP_PARENTS",
                ),
            ],
            [
                eq(
                    "EXTERNAL_DETAILS_TO_EXTERNAL_PARENT",
                    "CURRENT",
                    [
                        line(64, 17, "385.590"),
                        line(64, 20, "2.174.750"),
                        line(64, 23, "790.590"),
                        line(64, 26, "2.914.186"),
                        line(64, 29, "659.331"),
                    ],
                    line(64, 14, "6.924.447"),
                ),
                eq(
                    "EXTERNAL_DETAILS_TO_EXTERNAL_PARENT",
                    "COMPARATIVE",
                    [
                        line(64, 18, "376.277"),
                        line(64, 21, "2.582.875"),
                        line(64, 24, "220.289"),
                        line(64, 27, "1.674.127"),
                        line(64, 30, "271.632"),
                    ],
                    line(64, 15, "5.125.200"),
                ),
                eq(
                    "DIRECT_CHILDREN_TO_FAMILY_TOTAL",
                    "CURRENT",
                    [
                        line(64, 11, "941.203"),
                        line(64, 14, "6.924.447"),
                        line(64, 32, "5.667.622"),
                        line(64, 35, "817.424"),
                        line(64, 38, "1.541.280"),
                    ],
                    line(64, 40, "15.891.976"),
                ),
                eq(
                    "DIRECT_CHILDREN_TO_FAMILY_TOTAL",
                    "COMPARATIVE",
                    [
                        line(64, 12, "1.280.584"),
                        line(64, 15, "5.125.200"),
                        line(64, 33, "6.235.417"),
                        line(64, 36, "847.298"),
                        line(64, 39, "1.480.612"),
                    ],
                    line(64, 41, "14.969.111"),
                ),
            ],
            source_period="2025-12-31",
        ),
        doc(
            "MBB",
            67,
            36,
            "Các khoản phải trả và công nợ khác",
            [label(67, 37, "31/12/2025"), label(67, 38, "31/12/2024")],
            [label(67, 39, "triệu đồng"), label(67, 40, "triệu đồng")],
            [
                _root(
                    base,
                    67,
                    36,
                    "Các khoản phải trả và công nợ khác",
                    (52, "51.785.481"),
                    (53, "37.411.147"),
                ),
                _tp(
                    base,
                    1119,
                    "INTERNAL_PAYABLE",
                    67,
                    41,
                    "Các khoản phải trả nội bộ",
                    42,
                    "2.837.912",
                    43,
                    "2.033.835",
                    "DIRECT_CHILD_OF_OWNER",
                ),
                _tp(
                    base,
                    1122,
                    "EXTERNAL_PAYABLE",
                    67,
                    44,
                    "Các khoản phải trả bên ngoài",
                    45,
                    "46.371.539",
                    46,
                    "33.536.723",
                    "PRINTED_GROUP_PARENT_WITH_EXHAUSTIVE_DETAILS_NOT_DOUBLE_COUNTED",
                    (
                        (61, "Các khoản thuế phải nộp Nhà nước"),
                        (64, "Chuyển tiền phải trả"),
                        (67, "Doanh thu chờ phân bổ"),
                        (70, "Dự phòng nghiệp vụ bảo hiểm"),
                        (73, "Phải trả về dịch vụ thanh toán"),
                        (76, "Phải trả liên quan đến dịch vụ liên kết"),
                        (80, "Phải trả và ứng trước người bán"),
                        (83, "Các khoản ứng trước tiền mua giấy tờ có giá"),
                        (87, "Các khoản chờ thanh toán khác"),
                    ),
                ),
                _tp(
                    base,
                    1123,
                    "TAX_PAYABLE",
                    67,
                    61,
                    "Các khoản thuế phải nộp Nhà nước",
                    62,
                    "4.218.259",
                    63,
                    "3.574.209",
                    "DETAIL_WITHIN_EXTERNAL_PARENT",
                ),
                _tp(
                    base,
                    1126,
                    "WELFARE_FUND",
                    67,
                    49,
                    "Quỹ khen thưởng, phúc lợi",
                    50,
                    "2.076.030",
                    51,
                    "1.840.589",
                    "DIRECT_CHILD_OF_OWNER",
                ),
                _other_aggregate(
                    base,
                    67,
                    (
                        (47, "Quỹ phát triển khoa học và công nghệ"),
                        (64, "Chuyển tiền phải trả"),
                        (67, "Doanh thu chờ phân bổ"),
                        (70, "Dự phòng nghiệp vụ bảo hiểm"),
                        (73, "Phải trả về dịch vụ thanh toán"),
                        (76, "Phải trả liên quan đến dịch vụ liên kết"),
                        (80, "Phải trả và ứng trước người bán"),
                        (83, "Các khoản ứng trước tiền mua giấy tờ có giá"),
                        (87, "Các khoản chờ thanh toán khác"),
                    ),
                    (
                        (48, "500.000"),
                        (65, "1.650.895"),
                        (68, "2.438.785"),
                        (71, "18.870.565"),
                        (74, "12.413.243"),
                        (78, "184.193"),
                        (81, "393.813"),
                        (85, "2.871.166"),
                        (88, "3.330.620"),
                    ),
                    (
                        mbb_science_dash,
                        (66, "552.701"),
                        (69, "2.011.525"),
                        (72, "15.767.153"),
                        (75, "7.268.673"),
                        (79, "316.900"),
                        (82, "384.550"),
                        (86, "680.981"),
                        (89, "2.980.031"),
                    ),
                    "SUM_OF_SOURCE_ROWS_WITHOUT_DEDICATED_SCHEMA_LEAVES_ACROSS_EXPLICIT_GROUP_CONTEXTS_NOT_ADDED_TO_GROUP_PARENTS",
                ),
            ],
            [
                eq(
                    "EXTERNAL_DETAILS_TO_EXTERNAL_PARENT",
                    "CURRENT",
                    [
                        line(67, 62, "4.218.259"),
                        line(67, 65, "1.650.895"),
                        line(67, 68, "2.438.785"),
                        line(67, 71, "18.870.565"),
                        line(67, 74, "12.413.243"),
                        line(67, 78, "184.193"),
                        line(67, 81, "393.813"),
                        line(67, 85, "2.871.166"),
                        line(67, 88, "3.330.620"),
                    ],
                    line(67, 45, "46.371.539"),
                ),
                eq(
                    "EXTERNAL_DETAILS_TO_EXTERNAL_PARENT",
                    "COMPARATIVE",
                    [
                        line(67, 63, "3.574.209"),
                        line(67, 66, "552.701"),
                        line(67, 69, "2.011.525"),
                        line(67, 72, "15.767.153"),
                        line(67, 75, "7.268.673"),
                        line(67, 79, "316.900"),
                        line(67, 82, "384.550"),
                        line(67, 86, "680.981"),
                        line(67, 89, "2.980.031"),
                    ],
                    line(67, 46, "33.536.723"),
                ),
                eq(
                    "DIRECT_CHILDREN_TO_FAMILY_TOTAL",
                    "CURRENT",
                    [
                        line(67, 42, "2.837.912"),
                        line(67, 45, "46.371.539"),
                        line(67, 48, "500.000"),
                        line(67, 50, "2.076.030"),
                    ],
                    line(67, 52, "51.785.481"),
                ),
                eq(
                    "DIRECT_CHILDREN_TO_FAMILY_TOTAL",
                    "COMPARATIVE",
                    [
                        line(67, 43, "2.033.835"),
                        line(67, 46, "33.536.723"),
                        mbb_science_dash,
                        line(67, 51, "1.840.589"),
                    ],
                    line(67, 53, "37.411.147"),
                ),
            ],
            source_period="2025-12-31",
        ),
        doc(
            "VPB",
            63,
            44,
            "Các khoản phải trả và công nợ khác",
            [
                label(63, 45, "Ngày 31 tháng 12"),
                label(63, 47, "năm 2025"),
                label(63, 46, "Ngày 31 tháng 12"),
                label(63, 48, "năm 2024"),
            ],
            [label(63, 49, "Triệu đồng"), label(63, 50, "Triệu đồng")],
            [
                _root(
                    base,
                    63,
                    44,
                    "Các khoản phải trả và công nợ khác",
                    (92, "33.454.600"),
                    (93, "11.687.513"),
                ),
                _tp(
                    base,
                    1119,
                    "INTERNAL_PAYABLE",
                    63,
                    51,
                    "Các khoản phải trả nội bộ",
                    52,
                    "1.467.547",
                    53,
                    "301.509",
                    "PRINTED_GROUP_PARENT_WITH_EMPLOYEE_CHILD",
                ),
                _tp(
                    base,
                    1120,
                    "EMPLOYEE_PAYABLE",
                    63,
                    54,
                    "Phải trả nhân viên",
                    55,
                    "1.467.547",
                    56,
                    "301.509",
                    "SOLE_CHILD_OF_INTERNAL_PARENT",
                ),
                _tp(
                    base,
                    1122,
                    "EXTERNAL_PAYABLE",
                    63,
                    57,
                    "Các khoản phải trả bên ngoài",
                    58,
                    "31.987.053",
                    59,
                    "11.386.004",
                    "PRINTED_GROUP_PARENT_WITH_EXHAUSTIVE_DETAILS_NOT_DOUBLE_COUNTED",
                    (
                        (60, "Các khoản khách hàng trả trước"),
                        (63, "Doanh thu chờ phân bổ"),
                        (66, "Dự phòng nghiệp vụ bảo hiểm"),
                        (69, "Các khoản treo chờ chuyển tiền"),
                        (72, "Thuế và các khoản phải trả ngân sách Nhà nước"),
                        (76, "Phải trả về hoạt động thanh toán"),
                        (79, "Phải trả nhà cung cấp"),
                        (
                            82,
                            "Phải trả các khoản vay khách hàng của Công ty Cổ phần Chứng khoán VPBankS",
                        ),
                        (86, "Tiền giữ hộ và đợi thanh toán"),
                        (89, "Các khoản phải trả khác"),
                    ),
                ),
                _tp(
                    base,
                    1123,
                    "TAX_PAYABLE",
                    63,
                    72,
                    "Thuế và các khoản phải trả ngân sách Nhà nước",
                    74,
                    "4.712.152",
                    75,
                    "2.576.458",
                    "DETAIL_WITHIN_EXTERNAL_PARENT",
                    ((73, "Nhà nước"),),
                ),
                _tp(
                    base,
                    1124,
                    "OTHER_PAYABLE",
                    63,
                    89,
                    "Các khoản phải trả khác",
                    90,
                    "2.780.153",
                    91,
                    "1.612.617",
                    "DETAIL_WITHIN_EXTERNAL_PARENT",
                ),
                _other_aggregate(
                    base,
                    63,
                    (
                        (60, "Các khoản khách hàng trả trước"),
                        (63, "Doanh thu chờ phân bổ"),
                        (66, "Dự phòng nghiệp vụ bảo hiểm"),
                        (69, "Các khoản treo chờ chuyển tiền"),
                        (76, "Phải trả về hoạt động thanh toán"),
                        (79, "Phải trả nhà cung cấp"),
                        (
                            82,
                            "Phải trả các khoản vay khách hàng của Công ty Cổ phần Chứng khoán VPBankS",
                        ),
                        (86, "Tiền giữ hộ và đợi thanh toán"),
                    ),
                    (
                        (61, "1.275.354"),
                        (64, "1.316.346"),
                        (67, "2.538.021"),
                        (70, "531.714"),
                        (77, "3.359.249"),
                        (80, "19.000"),
                        (84, "14.582.889"),
                        (87, "872.175"),
                    ),
                    (
                        (62, "1.577.524"),
                        (65, "590.492"),
                        (68, "1.457.317"),
                        (71, "458.403"),
                        (78, "1.685.244"),
                        (81, "34.364"),
                        (85, "1.650"),
                        (88, "1.391.935"),
                    ),
                    "SUM_OF_EXTERNAL_DETAIL_ROWS_WITHOUT_DEDICATED_SCHEMA_LEAVES_NOT_ADDED_TO_EXTERNAL_PARENT",
                ),
            ],
            [
                eq(
                    "EMPLOYEE_CHILD_TO_INTERNAL_PARENT",
                    "CURRENT",
                    [line(63, 55, "1.467.547")],
                    line(63, 52, "1.467.547"),
                ),
                eq(
                    "EMPLOYEE_CHILD_TO_INTERNAL_PARENT",
                    "COMPARATIVE",
                    [line(63, 56, "301.509")],
                    line(63, 53, "301.509"),
                ),
                eq(
                    "EXTERNAL_DETAILS_TO_EXTERNAL_PARENT",
                    "CURRENT",
                    [
                        line(63, 61, "1.275.354"),
                        line(63, 64, "1.316.346"),
                        line(63, 67, "2.538.021"),
                        line(63, 70, "531.714"),
                        line(63, 74, "4.712.152"),
                        line(63, 77, "3.359.249"),
                        line(63, 80, "19.000"),
                        line(63, 84, "14.582.889"),
                        line(63, 87, "872.175"),
                        line(63, 90, "2.780.153"),
                    ],
                    line(63, 58, "31.987.053"),
                ),
                eq(
                    "EXTERNAL_DETAILS_TO_EXTERNAL_PARENT",
                    "COMPARATIVE",
                    [
                        line(63, 62, "1.577.524"),
                        line(63, 65, "590.492"),
                        line(63, 68, "1.457.317"),
                        line(63, 71, "458.403"),
                        line(63, 75, "2.576.458"),
                        line(63, 78, "1.685.244"),
                        line(63, 81, "34.364"),
                        line(63, 85, "1.650"),
                        line(63, 88, "1.391.935"),
                        line(63, 91, "1.612.617"),
                    ],
                    line(63, 59, "11.386.004"),
                ),
                eq(
                    "INTERNAL_PLUS_EXTERNAL_TO_FAMILY_TOTAL",
                    "CURRENT",
                    [line(63, 52, "1.467.547"), line(63, 58, "31.987.053")],
                    line(63, 92, "33.454.600"),
                ),
                eq(
                    "INTERNAL_PLUS_EXTERNAL_TO_FAMILY_TOTAL",
                    "COMPARATIVE",
                    [line(63, 53, "301.509"), line(63, 59, "11.386.004")],
                    line(63, 93, "11.687.513"),
                ),
            ],
            source_period="2025-12-31",
        ),
        doc(
            "HDB",
            47,
            33,
            "Các khoản phải trả và công nợ khác",
            [label(47, 34, "Số cuối năm"), label(47, 35, "Số đầu năm")],
            [label(47, 36, "Triệu VND"), label(47, 37, "Triệu VND")],
            [
                _root(
                    base,
                    47,
                    33,
                    "Các khoản phải trả và công nợ khác",
                    (63, "12.007.501"),
                    (64, "11.558.217"),
                ),
                _tp(
                    base,
                    1119,
                    "INTERNAL_PAYABLE",
                    47,
                    38,
                    "Các khoản phải trả nội bộ",
                    39,
                    "1.003.098",
                    40,
                    "1.012.394",
                    "DIRECT_CHILD_OF_OWNER",
                ),
                _tp(
                    base,
                    1122,
                    "EXTERNAL_PAYABLE",
                    47,
                    41,
                    "Các khoản phải trả cho bên ngoài",
                    42,
                    "9.475.505",
                    43,
                    "8.398.587",
                    "PRINTED_GROUP_PARENT_WITH_EXHAUSTIVE_DETAILS_NOT_DOUBLE_COUNTED",
                    (
                        (44, "Tiền giữ hộ và chờ thanh toán"),
                        (47, "Phải trả giao dịch chuyển tiền nhanh qua thẻ"),
                        (50, "Thuế và các khoản phải nộp Nhà nước"),
                        (54, "Các khoản phải trả khác"),
                    ),
                ),
                _tp(
                    base,
                    1123,
                    "TAX_PAYABLE",
                    47,
                    50,
                    "Thuế và các khoản phải nộp Nhà nước",
                    51,
                    "2.634.433",
                    52,
                    "1.074.508",
                    "DETAIL_WITHIN_EXTERNAL_PARENT",
                ),
                _tp(
                    base,
                    1124,
                    "OTHER_PAYABLE",
                    47,
                    54,
                    "Các khoản phải trả khác",
                    55,
                    "1.854.475",
                    56,
                    "1.149.745",
                    "DETAIL_WITHIN_EXTERNAL_PARENT",
                ),
                _tp(
                    base,
                    1126,
                    "WELFARE_FUND",
                    47,
                    60,
                    "Quỹ khen thưởng, phúc lợi",
                    61,
                    "61.953",
                    62,
                    "46.763",
                    "DIRECT_CHILD_OF_OWNER",
                ),
                _other_aggregate(
                    base,
                    47,
                    (
                        (44, "Tiền giữ hộ và chờ thanh toán"),
                        (47, "Phải trả giao dịch chuyển tiền nhanh qua thẻ"),
                        (57, "Doanh thu chờ phân bổ"),
                    ),
                    ((45, "816.781"), (48, "4.169.816"), (58, "1.466.945")),
                    ((46, "1.496.895"), (49, "4.677.439"), (59, "2.100.473")),
                    "SUM_OF_SOURCE_ROWS_WITHOUT_DEDICATED_SCHEMA_LEAVES_ACROSS_EXPLICIT_GROUP_CONTEXTS_NOT_ADDED_TO_GROUP_PARENTS",
                ),
            ],
            [
                eq(
                    "EXTERNAL_DETAILS_TO_EXTERNAL_PARENT",
                    "CURRENT",
                    [
                        line(47, 45, "816.781"),
                        line(47, 48, "4.169.816"),
                        line(47, 51, "2.634.433"),
                        line(47, 55, "1.854.475"),
                    ],
                    line(47, 42, "9.475.505"),
                ),
                eq(
                    "EXTERNAL_DETAILS_TO_EXTERNAL_PARENT",
                    "COMPARATIVE",
                    [
                        line(47, 46, "1.496.895"),
                        line(47, 49, "4.677.439"),
                        line(47, 52, "1.074.508"),
                        line(47, 56, "1.149.745"),
                    ],
                    line(47, 43, "8.398.587"),
                ),
                eq(
                    "DIRECT_CHILDREN_TO_FAMILY_TOTAL",
                    "CURRENT",
                    [
                        line(47, 39, "1.003.098"),
                        line(47, 42, "9.475.505"),
                        line(47, 58, "1.466.945"),
                        line(47, 61, "61.953"),
                    ],
                    line(47, 63, "12.007.501"),
                ),
                eq(
                    "DIRECT_CHILDREN_TO_FAMILY_TOTAL",
                    "COMPARATIVE",
                    [
                        line(47, 40, "1.012.394"),
                        line(47, 43, "8.398.587"),
                        line(47, 59, "2.100.473"),
                        line(47, 62, "46.763"),
                    ],
                    line(47, 64, "11.558.217"),
                ),
            ],
            source_period="2025-12-31",
        ),
        doc(
            "VCB",
            54,
            73,
            "Các khoản phải trả và công nợ khác",
            [label(54, 74, "31/12/2025"), label(54, 75, "31/12/2024")],
            [label(54, 76, "Triệu VND"), label(54, 77, "Triệu VND")],
            [
                _root(
                    base,
                    54,
                    73,
                    "Các khoản phải trả và công nợ khác",
                    (87, "21.339.972"),
                    (88, "24.112.345"),
                ),
                _tp(
                    base,
                    1119,
                    "INTERNAL_PAYABLE",
                    54,
                    78,
                    "Các khoản phải trả nội bộ",
                    79,
                    "5.618.852",
                    80,
                    "5.675.129",
                    "DIRECT_CHILD_OF_OWNER",
                ),
                _tp(
                    base,
                    1122,
                    "EXTERNAL_PAYABLE",
                    54,
                    81,
                    "Các khoản phải trả bên ngoài",
                    82,
                    "10.489.441",
                    83,
                    "13.618.090",
                    "DIRECT_CHILD_OF_OWNER",
                ),
                _tp(
                    base,
                    1126,
                    "WELFARE_FUND",
                    54,
                    84,
                    "Quỹ khen thưởng, phúc lợi",
                    85,
                    "5.231.679",
                    86,
                    "4.819.126",
                    "DIRECT_CHILD_OF_OWNER",
                ),
            ],
            [
                eq(
                    "DIRECT_CHILDREN_TO_FAMILY_TOTAL",
                    "CURRENT",
                    [
                        line(54, 79, "5.618.852"),
                        line(54, 82, "10.489.441"),
                        line(54, 85, "5.231.679"),
                    ],
                    line(54, 87, "21.339.972"),
                ),
                eq(
                    "DIRECT_CHILDREN_TO_FAMILY_TOTAL",
                    "COMPARATIVE",
                    [
                        line(54, 80, "5.675.129"),
                        line(54, 83, "13.618.090"),
                        line(54, 86, "4.819.126"),
                    ],
                    line(54, 88, "24.112.345"),
                ),
            ],
            source_period="2025-12-31",
        ),
        doc(
            "CTG",
            54,
            67,
            "CÁC KHOẢN PHẢI TRẢ VÀ CÔNG NỢ KHÁC",
            [label(54, 68, "31.12.2025"), label(54, 69, "31.12.2024")],
            [label(54, 70, "Triệu đồng"), label(54, 71, "Triệu đồng")],
            [
                _root(
                    base,
                    54,
                    67,
                    "CÁC KHOẢN PHẢI TRẢ VÀ CÔNG NỢ KHÁC",
                    (81, "26.345.997"),
                    (82, "22.102.187"),
                ),
                _tp(
                    base,
                    1119,
                    "INTERNAL_PAYABLE",
                    54,
                    72,
                    "Các khoản phải trả nội bộ",
                    73,
                    "6.033.105",
                    74,
                    "3.869.525",
                    "DIRECT_CHILD_OF_OWNER",
                ),
                _tp(
                    base,
                    1122,
                    "EXTERNAL_PAYABLE",
                    54,
                    75,
                    "Các khoản phải trả bên ngoài",
                    76,
                    "17.129.874",
                    77,
                    "14.431.977",
                    "PRINTED_GROUP_PARENT_WITH_EXHAUSTIVE_DETAILS_NOT_DOUBLE_COUNTED",
                    (
                        (88, "Các khoản thu, chi hộ các tổ chức khác"),
                        (90, "Tiền giữ hộ và chờ thanh toán"),
                        (93, "Thuế TNDN phải trả"),
                        (96, "Doanh thu chờ phân bổ"),
                        (99, "Phải trả thuế khác"),
                        (102, "Phải trả khác liên quan đến nghiệp vụ chứng khoán"),
                        (105, "Thanh toán giữa các tổ chức tín dụng"),
                        (107, "Chuyển tiền phải trả"),
                        (110, "Phải trả liên quan đến hoạt động tài trợ thương mại"),
                        (113, "Các khoản chờ thanh toán khác"),
                        (116, "Tạm ứng nhận được liên quan đến hoạt động bán nợ"),
                        (119, "Phải trả khác"),
                    ),
                ),
                base._mapping(
                    1123,
                    "TAX_PAYABLE",
                    [label(54, 93, "Thuế TNDN phải trả"), label(54, 99, "Phải trả thuế khác")],
                    {
                        "CURRENT": [line(54, 94, "4.359.642"), line(54, 100, "284.527")],
                        "COMPARATIVE": [line(54, 95, "3.337.834"), line(54, 101, "263.822")],
                    },
                    "SUM_OF_TAX_DETAIL_ROWS_WITHIN_EXTERNAL_PARENT",
                ),
                _tp(
                    base,
                    1124,
                    "OTHER_PAYABLE",
                    54,
                    119,
                    "Phải trả khác",
                    120,
                    "73.435",
                    121,
                    "69.730",
                    "DETAIL_WITHIN_EXTERNAL_PARENT",
                ),
                _other_aggregate(
                    base,
                    54,
                    (
                        (88, "Các khoản thu, chi hộ các tổ chức khác"),
                        (90, "Tiền giữ hộ và chờ thanh toán"),
                        (96, "Doanh thu chờ phân bổ"),
                        (102, "Phải trả khác liên quan đến nghiệp vụ chứng khoán"),
                        (105, "Thanh toán giữa các tổ chức tín dụng"),
                        (107, "Chuyển tiền phải trả"),
                        (110, "Phải trả liên quan đến hoạt động tài trợ thương mại"),
                        (113, "Các khoản chờ thanh toán khác"),
                        (116, "Tạm ứng nhận được liên quan đến hoạt động bán nợ"),
                    ),
                    (
                        ctg_receipts_dash,
                        (91, "68.803"),
                        (97, "4.339.380"),
                        (103, "850.684"),
                        ctg_interbank_dash,
                        (108, "731.479"),
                        (111, "6.000"),
                        (114, "6.296.762"),
                        (117, "119.162"),
                    ),
                    (
                        (89, "2.119.006"),
                        (92, "73.896"),
                        (98, "4.253.734"),
                        (104, "558.485"),
                        (106, "527.227"),
                        (109, "289.054"),
                        (112, "6.000"),
                        (115, "2.803.217"),
                        (118, "129.972"),
                    ),
                    "SUM_OF_EXTERNAL_DETAIL_ROWS_WITHOUT_DEDICATED_SCHEMA_LEAVES_NOT_ADDED_TO_EXTERNAL_PARENT",
                ),
                _tp(
                    base,
                    1126,
                    "WELFARE_FUND",
                    54,
                    78,
                    "Quỹ khen thưởng, phúc lợi",
                    79,
                    "3.183.018",
                    80,
                    "3.800.685",
                    "DIRECT_CHILD_OF_OWNER",
                ),
            ],
            [
                eq(
                    "EXTERNAL_DETAILS_TO_EXTERNAL_PARENT",
                    "CURRENT",
                    [
                        ctg_receipts_dash,
                        line(54, 91, "68.803"),
                        line(54, 94, "4.359.642"),
                        line(54, 97, "4.339.380"),
                        line(54, 100, "284.527"),
                        line(54, 103, "850.684"),
                        ctg_interbank_dash,
                        line(54, 108, "731.479"),
                        line(54, 111, "6.000"),
                        line(54, 114, "6.296.762"),
                        line(54, 117, "119.162"),
                        line(54, 120, "73.435"),
                    ],
                    line(54, 76, "17.129.874"),
                ),
                eq(
                    "EXTERNAL_DETAILS_TO_EXTERNAL_PARENT",
                    "COMPARATIVE",
                    [
                        line(54, 89, "2.119.006"),
                        line(54, 92, "73.896"),
                        line(54, 95, "3.337.834"),
                        line(54, 98, "4.253.734"),
                        line(54, 101, "263.822"),
                        line(54, 104, "558.485"),
                        line(54, 106, "527.227"),
                        line(54, 109, "289.054"),
                        line(54, 112, "6.000"),
                        line(54, 115, "2.803.217"),
                        line(54, 118, "129.972"),
                        line(54, 121, "69.730"),
                    ],
                    line(54, 77, "14.431.977"),
                ),
                eq(
                    "DIRECT_CHILDREN_TO_FAMILY_TOTAL",
                    "CURRENT",
                    [
                        line(54, 73, "6.033.105"),
                        line(54, 76, "17.129.874"),
                        line(54, 79, "3.183.018"),
                    ],
                    line(54, 81, "26.345.997"),
                ),
                eq(
                    "DIRECT_CHILDREN_TO_FAMILY_TOTAL",
                    "COMPARATIVE",
                    [
                        line(54, 74, "3.869.525"),
                        line(54, 77, "14.431.977"),
                        line(54, 80, "3.800.685"),
                    ],
                    line(54, 82, "22.102.187"),
                ),
            ],
            source_period="2025-12-31",
        ),
        doc(
            "BID",
            52,
            45,
            "CÁC KHOẢN NỢ KHÁC",
            [
                label(52, 47, "Số cuối năm"),
                label(52, 46, "Số đầu năm"),
                label(52, 48, "Trình bày lại"),
            ],
            [label(52, 49, "Triệu VND"), label(52, 50, "Triệu VND")],
            [
                _root(base, 52, 45, "CÁC KHOẢN NỢ KHÁC", (84, "59.809.064"), (85, "50.532.627")),
                _tp(
                    base,
                    1119,
                    "INTERNAL_PAYABLE",
                    52,
                    51,
                    "Các khoản phải trả nội bộ",
                    52,
                    "6.860.518",
                    53,
                    "5.104.099",
                    "DIRECT_CHILD_OF_OWNER",
                ),
                _tp(
                    base,
                    1122,
                    "EXTERNAL_PAYABLE",
                    52,
                    54,
                    "Các khoản phải trả bên ngoài",
                    55,
                    "49.888.105",
                    56,
                    "42.390.777",
                    "PRINTED_GROUP_PARENT_WITH_NONEXHAUSTIVE_TRONG_DO_DETAILS_NOT_DOUBLE_COUNTED",
                    (
                        (58, "Các khoản lãi và phí phải trả"),
                        (61, "Phải trả về xây dựng cơ bản"),
                        (65, "Thuế và các khoản phải trả khác cho ngân sách Nhà nước"),
                        (70, "Phải trả trong nghiệp vụ chứng khoán và bảo hiểm"),
                        (76, "Thuế thu nhập doanh nghiệp hoãn lại phải trả"),
                    ),
                ),
                _tp(
                    base,
                    1123,
                    "TAX_PAYABLE",
                    52,
                    65,
                    "Thuế và các khoản phải trả khác cho ngân sách Nhà nước",
                    66,
                    "4.096.156",
                    67,
                    "2.906.927",
                    "NONEXHAUSTIVE_DETAIL_WITHIN_EXTERNAL_PARENT",
                    ((68, "Nhà nước"),),
                ),
                _tp(
                    base,
                    1126,
                    "WELFARE_FUND",
                    52,
                    81,
                    "Quỹ khen thưởng, phúc lợi",
                    82,
                    "3.060.441",
                    83,
                    "3.037.751",
                    "DIRECT_CHILD_OF_OWNER",
                ),
                _other_aggregate(
                    base,
                    52,
                    (
                        (58, "Các khoản lãi và phí phải trả"),
                        (61, "Phải trả về xây dựng cơ bản"),
                        (70, "Phải trả trong nghiệp vụ chứng khoán và bảo hiểm"),
                        (76, "Thuế thu nhập doanh nghiệp hoãn lại phải trả"),
                    ),
                    ((59, "33.802.929"), (62, "147.641"), (71, "5.234.871"), (78, "65.589")),
                    ((60, "28.670.106"), (64, "165.658"), (72, "4.234.624"), (79, "79.818")),
                    "SUM_OF_NONEXHAUSTIVE_TRONG_DO_SOURCE_ROWS_WITHOUT_DEDICATED_SCHEMA_LEAVES_NOT_ADDED_TO_EXTERNAL_PARENT",
                ),
            ],
            [
                eq(
                    "DIRECT_CHILDREN_TO_FAMILY_TOTAL",
                    "CURRENT",
                    [
                        line(52, 52, "6.860.518"),
                        line(52, 55, "49.888.105"),
                        line(52, 82, "3.060.441"),
                    ],
                    line(52, 84, "59.809.064"),
                ),
                eq(
                    "DIRECT_CHILDREN_TO_FAMILY_TOTAL",
                    "COMPARATIVE",
                    [
                        line(52, 53, "5.104.099"),
                        line(52, 56, "42.390.777"),
                        line(52, 83, "3.037.751"),
                    ],
                    line(52, 85, "50.532.627"),
                ),
            ],
            source_period="2025-12-31",
        ),
        doc(
            "VIB",
            48,
            16,
            "CÁC KHOẢN NỢ KHÁC",
            [label(48, 17, "31/12/2025"), label(48, 18, "31/12/2024")],
            [label(48, 19, "triệu đồng"), label(48, 20, "triệu đồng")],
            [
                _root(base, 48, 16, "CÁC KHOẢN NỢ KHÁC", (63, "10.946.659"), (64, "9.932.816")),
                _tp(
                    base,
                    1119,
                    "INTERNAL_PAYABLE",
                    48,
                    24,
                    "Các khoản phải trả nội bộ",
                    25,
                    "431.458",
                    26,
                    "494.164",
                    "PRINTED_GROUP_PARENT_WITH_EXHAUSTIVE_DETAILS_NOT_DOUBLE_COUNTED",
                    (
                        (27, "Phải trả cán bộ, nhân viên"),
                        (30, "Quỹ khen thưởng, phúc lợi"),
                        (33, "Phải trả cổ tức cho cổ đông"),
                        (36, "Phải trả nội bộ khác"),
                    ),
                ),
                _tp(
                    base,
                    1120,
                    "EMPLOYEE_PAYABLE",
                    48,
                    27,
                    "Phải trả cán bộ, nhân viên",
                    28,
                    "233.527",
                    29,
                    "293.151",
                    "DETAIL_WITHIN_INTERNAL_PARENT",
                ),
                _tp(
                    base,
                    1121,
                    "INTERNAL_OTHER",
                    48,
                    36,
                    "Phải trả nội bộ khác",
                    37,
                    "32.390",
                    38,
                    "85.092",
                    "DETAIL_WITHIN_INTERNAL_PARENT",
                ),
                _tp(
                    base,
                    1122,
                    "EXTERNAL_PAYABLE",
                    48,
                    39,
                    "Các khoản phải trả bên ngoài",
                    40,
                    "6.162.377",
                    41,
                    "6.053.442",
                    "PRINTED_GROUP_PARENT_WITH_EXHAUSTIVE_DETAILS_NOT_DOUBLE_COUNTED",
                    (
                        (42, "Thuế và các khoản phải nộp Nhà nước"),
                        (45, "Tiền giữ hộ và đợi thanh toán"),
                        (48, "Phải trả thanh toán giữa các TCTD"),
                        (51, "Phải trả chuyển tiền chờ thanh toán"),
                        (54, "Các khoản chờ thanh toán khác"),
                        (57, "Các khoản phải trả khác"),
                    ),
                ),
                _tp(
                    base,
                    1123,
                    "TAX_PAYABLE",
                    48,
                    42,
                    "Thuế và các khoản phải nộp Nhà nước",
                    43,
                    "1.289.606",
                    44,
                    "1.367.507",
                    "DETAIL_WITHIN_EXTERNAL_PARENT",
                ),
                _tp(
                    base,
                    1124,
                    "OTHER_PAYABLE",
                    48,
                    57,
                    "Các khoản phải trả khác",
                    58,
                    "241.951",
                    59,
                    "354.049",
                    "DETAIL_WITHIN_EXTERNAL_PARENT",
                ),
                _tp(
                    base,
                    1126,
                    "WELFARE_FUND",
                    48,
                    30,
                    "Quỹ khen thưởng, phúc lợi",
                    31,
                    "158.925",
                    32,
                    "109.160",
                    "DETAIL_WITHIN_INTERNAL_PARENT",
                ),
                _other_aggregate(
                    base,
                    48,
                    (
                        (21, "Các khoản lãi, phí phải trả"),
                        (33, "Phải trả cổ tức cho cổ đông"),
                        (45, "Tiền giữ hộ và đợi thanh toán"),
                        (48, "Phải trả thanh toán giữa các TCTD"),
                        (51, "Phải trả chuyển tiền chờ thanh toán"),
                        (54, "Các khoản chờ thanh toán khác"),
                        (60, "Doanh thu chờ phân bổ"),
                    ),
                    (
                        (22, "4.298.773"),
                        (34, "6.616"),
                        (46, "20.875"),
                        (49, "620.546"),
                        (52, "248.948"),
                        (55, "3.740.451"),
                        (61, "54.051"),
                    ),
                    (
                        (23, "3.382.767"),
                        (35, "6.761"),
                        (47, "20.866"),
                        (50, "323.071"),
                        (53, "365.386"),
                        (56, "3.622.563"),
                        (62, "2.443"),
                    ),
                    "SUM_OF_SOURCE_ROWS_WITHOUT_DEDICATED_SCHEMA_LEAVES_ACROSS_EXPLICIT_GROUP_CONTEXTS_NOT_ADDED_TO_GROUP_PARENTS",
                ),
            ],
            [
                eq(
                    "INTERNAL_DETAILS_TO_INTERNAL_PARENT",
                    "CURRENT",
                    [
                        line(48, 28, "233.527"),
                        line(48, 31, "158.925"),
                        line(48, 34, "6.616"),
                        line(48, 37, "32.390"),
                    ],
                    line(48, 25, "431.458"),
                ),
                eq(
                    "INTERNAL_DETAILS_TO_INTERNAL_PARENT",
                    "COMPARATIVE",
                    [
                        line(48, 29, "293.151"),
                        line(48, 32, "109.160"),
                        line(48, 35, "6.761"),
                        line(48, 38, "85.092"),
                    ],
                    line(48, 26, "494.164"),
                ),
                eq(
                    "EXTERNAL_DETAILS_TO_EXTERNAL_PARENT",
                    "CURRENT",
                    [
                        line(48, 43, "1.289.606"),
                        line(48, 46, "20.875"),
                        line(48, 49, "620.546"),
                        line(48, 52, "248.948"),
                        line(48, 55, "3.740.451"),
                        line(48, 58, "241.951"),
                    ],
                    line(48, 40, "6.162.377"),
                ),
                eq(
                    "EXTERNAL_DETAILS_TO_EXTERNAL_PARENT",
                    "COMPARATIVE",
                    [
                        line(48, 44, "1.367.507"),
                        line(48, 47, "20.866"),
                        line(48, 50, "323.071"),
                        line(48, 53, "365.386"),
                        line(48, 56, "3.622.563"),
                        line(48, 59, "354.049"),
                    ],
                    line(48, 41, "6.053.442"),
                ),
                eq(
                    "DIRECT_CHILDREN_TO_FAMILY_TOTAL",
                    "CURRENT",
                    [
                        line(48, 22, "4.298.773"),
                        line(48, 25, "431.458"),
                        line(48, 40, "6.162.377"),
                        line(48, 61, "54.051"),
                    ],
                    line(48, 63, "10.946.659"),
                ),
                eq(
                    "DIRECT_CHILDREN_TO_FAMILY_TOTAL",
                    "COMPARATIVE",
                    [
                        line(48, 23, "3.382.767"),
                        line(48, 26, "494.164"),
                        line(48, 41, "6.053.442"),
                        line(48, 62, "2.443"),
                    ],
                    line(48, 64, "9.932.816"),
                ),
            ],
            source_period="2025-12-31",
        ),
    ]
    return documents


def _configure(base: ModuleType) -> None:
    base.FORMAT_VERSION = FORMAT_VERSION
    base.REVIEW_FORMAT = REVIEW_FORMAT
    base.RESULT_STATE = RESULT_STATE
    base.RESULT_ID_PREFIX = RESULT_ID_PREFIX
    base.REVIEW_STATE = REVIEW_STATE
    base.REVIEW_ID_PREFIX = REVIEW_ID_PREFIX
    base.REVIEW_RUN_ID = REVIEW_RUN_ID
    base.CLAIM_BOUNDARY = CLAIM_BOUNDARY
    base.REVIEW_PATH = REVIEW_PATH
    base.RESULT_PATH = RESULT_PATH
    base.SEMANTIC_INDEX_PATH = SEMANTIC_INDEX_PATH
    base.CROP_MANIFEST_PATH = CROP_MANIFEST_PATH
    base.EXPECTED_INDEX_SHA256 = EXPECTED_INDEX_SHA256
    base.EXPECTED_CROP_MANIFEST_SHA256 = EXPECTED_CROP_MANIFEST_SHA256
    base.EXPECTED_AXIS_SHA256 = EXPECTED_AXIS_SHA256
    base.EXPECTED_SCAN_ID = EXPECTED_SCAN_ID
    base._REVIEW_CHECKS = tuple(_REVIEW_CHECKS)
    base._REVIEW_SAFETY = dict(_REVIEW_SAFETY)
    base._AUTHORITY = dict(_AUTHORITY)
    base._SCHEMA_EXPECTED = dict(_SCHEMA_EXPECTED)
    base._review_documents = lambda: _review_documents(base)
    base._source_period_status = lambda source_period: (
        "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
        if source_period == "2025-12-31"
        else (_ for _ in ()).throw(_error("annual other-payables period drifted"))
    )


def _assert_result(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("metrics") != _EXPECTED_METRICS:
        raise _error("annual other-payables result metrics drifted")
    for trial in value.get("trials", []):
        actual = {row["schema_binding"]["report_norm_id"] for row in trial["verified_mappings"]}
        if actual != _EXPECTED_IDS[trial["document_provenance"]]:
            raise _error("annual other-payables mapped schema set drifted")
        if trial["unmapped_source_rows"]:
            raise _error("annual other-payables unexpectedly retained one open row")
        if trial["source_period_status"] != (
            "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
        ):
            raise _error("annual other-payables source period status drifted")
    return value


def build_annual_2025_other_payables_liabilities_pixel_review_blueprint_v1() -> dict[str, Any]:
    base = _load_base()
    _configure(base)
    return base._review_blueprint()


def build_live_annual_2025_other_payables_liabilities_8bank_codex_verified_mapping_v1() -> dict[
    str, Any
]:
    base = _load_base()
    _configure(base)
    semantic_index, _ = base._stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = base._stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    review = base._review_blueprint()
    review_sha = hashlib.sha256(canonical_json_bytes_v1(review)).hexdigest()
    scan = base.scanner.build_other_payables_liabilities_full_document_scan_v1(semantic_index)
    schema_authority, schema_by_id = base._authority_snapshot(PROJECT_ROOT)
    result = base.build_other_payables_liabilities_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )
    replayed = base.validate_other_payables_liabilities_8bank_codex_verified_mapping_replay_v1(
        result,
        semantic_index,
        crop_manifest,
        scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )
    return _assert_result(replayed)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or (REVIEW_PATH if args.write_review else RESULT_PATH)
    if args.write_review:
        output.write_bytes(
            canonical_json_bytes_v1(
                build_annual_2025_other_payables_liabilities_pixel_review_blueprint_v1()
            )
        )
    else:
        result = build_live_annual_2025_other_payables_liabilities_8bank_codex_verified_mapping_v1()
        output.write_bytes(canonical_json_bytes_v1(result))
        print(result["result_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
