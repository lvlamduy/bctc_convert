"""Verify annual-2025 operating-expense disclosures across eight banks.

This configures and reuses the existing operating-expense mapping/replay
implementation.  Only the annual review ledger, fixed annual evidence roots,
and current live-schema display positions differ from the earlier current-
period experiment.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.full_document_vietocr_accounting_axis_v1 import (
    EXPECTED_DOCUMENT_ORDER,
)
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import (
    _authority_snapshot,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "ANNUAL_2025_OPERATING_EXPENSE_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_OPERATING_EXPENSE_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_OPERATING_EXPENSE_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025oe8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_OPERATING_EXPENSE_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025oe8bcv1:pixel-review:"
REVIEW_RUN_ID = "E-0143"
REVIEW_PATH = Path(
    "docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-verified-mapping-v1.json"
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
EXPECTED_SCAN_ID = "oefdsv1:scan:d88785a12723b80f3acdc18e8e991298c629365b2661bd58f369df7566fb71d7"
EXPECTED_RESULT_ID = (
    "annual2025oe8bcv1:result:81d570a9f76a56547644a332aa79a75902513cd6246a7bc2da1bf0b7a0015b16"
)

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_"
    "VIETOCR_BANK_BLIND_OPERATING_EXPENSE_GRAPH_VISIBLE_PDF_UPSTREAM_"
    "PPOCRV6_NUMERIC_CHALLENGER_PERIOD_UNIT_ACCOUNTING_AND_LIVE_TM_SCHEMA_"
    "ONLY_SOURCE_SPECIFIC_ROWS_RETAINED_NO_CANONICALIZATION_EXPORT_OR_"
    "PRODUCTION_AUTHORITY"
)
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_annual_operating_expense_rows": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_numeric_challenger_and_accounting_closure_required": True,
    "text_similarity_alone_used_for_mapping": False,
    "unmapped_source_rows_discarded": False,
    "vietocr_numeric_disagreement_is_retained_not_silently_repaired": True,
    "whole_pdf_uniqueness_replayed": True,
}
_REVIEW_SAFETY = {
    "bank_page_or_filename_used_as_graph_rule": False,
    "document_or_section_unit_inheritance_recorded_explicitly": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "gemma_json_used_as_mapping_or_numeric_authority": False,
    "mapping_decided_by_text_similarity_alone": False,
    "optional_rows_required_in_every_bank": False,
    "source_parent_and_children_double_counted": False,
    "unmapped_source_rows_retained": True,
    "visible_pdf_pixels_reviewed": True,
    "whole_pdf_uniqueness_replayed": True,
}
_SCHEMA_EXPECTED = {
    1142: (
        "II. THÔNG TIN BỔ SUNG CHO CÁC KHOẢN MỤC TRÌNH BÀY TRONG BẢNG KẾT QUẢ KINH DOANH",
        None,
        686,
    ),
    1205: ("Chi phí quản lý chung (Chi phí hoạt động)", 1142, 765),
    1206: ("-Chi nộp thuế và các khoản phí, lệ phí", 1205, 766),
    1207: ("-Chi phí cho nhân viên:", 1205, 767),
    1208: ("Trong đó: + Chi lương và phụ cấp", 1205, 768),
    1209: ("+ Các khoản chi đóng góp theo lương", 1205, 769),
    1210: ("+ Chi trợ cấp", 1205, 770),
    1211: ("+ Chi khác cho nhân viên", 1205, 771),
    1212: ("-Chi về tài sản", 1205, 772),
    1213: ("Trong đó: Chi phí khấu hao", 1205, 773),
    1214: ("-Chi cho hoạt động quản lý công vụ", 1205, 774),
    1215: ("Trong đó: +Công tác phí", 1205, 775),
    1216: ("+Chi về hoạt động đoàn thể của TCTD", 1205, 776),
    1217: ("-Chi phí bảo hiểm tiền gửi của khách hàng", 1205, 777),
    1218: (
        "-Dự phòng giảm giá các khoản đầu tư dài hạn và chi phí dự phòng nợ khó đòi",
        1205,
        778,
    ),
    1219: ("-Chi phí quản lý (hoạt động) khác", 1205, 779),
    1220: ("-(Hoàn nhập)/Trích lập chi phí dự phòng cho tài sản có khác", 1205, 780),
}
_EXPECTED_PAGES = {
    "ACB": [70, 70],
    "MBB": [74, 74],
    "VPB": [72, 72],
    "HDB": [51, 51],
    "VCB": [61, 61],
    "CTG": [60, 60],
    "BID": [57, 57],
    "VIB": [52, 52],
}
_EXPECTED_MAPPING_COUNTS = {
    "ACB": 13,
    "MBB": 12,
    "VPB": 15,
    "HDB": 15,
    "VCB": 14,
    "CTG": 14,
    "BID": 13,
    "VIB": 7,
}
_EXPECTED_SOURCE_ONLY_COUNTS = {
    "ACB": 2,
    "MBB": 1,
    "VPB": 3,
    "HDB": 6,
    "VCB": 0,
    "CTG": 2,
    "BID": 0,
    "VIB": 0,
}
_EXPECTED_METRICS = {
    "accounting_equation_verified_count": 42,
    "document_count": 8,
    "document_unique_region_count": 8,
    "fresh_vietocr_numeric_disagreement_count": 4,
    "mapping_verified_count": 103,
    "open_source_row_count": 14,
    "q1_source_period_caveat_document_count": 0,
    "verified_value_cell_count": 206,
}


class Annual2025OperatingExpense8BankError(ValueError):
    """Annual operating-expense structure, pixels, numbers or schema drifted."""


def _error(message: str) -> Annual2025OperatingExpense8BankError:
    return Annual2025OperatingExpense8BankError(message)


def _load_base() -> ModuleType:
    path = (
        PROJECT_ROOT
        / "scripts/experiments/build_operating_expense_8bank_codex_verified_mapping_v1.py"
    )
    name = "annual_2025_operating_expense_mapping_base"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual operating-expense support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


base = _load_base()


def _m(
    page: int,
    report_norm_id: int,
    role: str,
    label_line: int,
    label_text: str,
    current_line: int,
    current_text: str,
    comparative_line: int,
    comparative_text: str,
    *,
    topology: str = "DIRECT_VISIBLE_ROW_TWO_ANNUAL_PERIOD_LANES",
) -> dict[str, Any]:
    return base._mapping(
        page,
        report_norm_id,
        role,
        label_line,
        label_text,
        current_line,
        current_text,
        comparative_line,
        comparative_text,
        topology=topology,
    )


def _s(
    row_id: str,
    page: int,
    role: str,
    label_line: int,
    label_text: str,
    current_line: int,
    current_text: str,
    comparative_line: int,
    comparative_text: str,
    reason: str,
) -> dict[str, Any]:
    return base._source_only(
        row_id,
        page,
        role,
        label_line,
        label_text,
        current_line,
        current_text,
        comparative_line,
        comparative_text,
        reason,
    )


def _eq(name: str, parent: str, terms: list[str]) -> dict[str, Any]:
    return base._equation(name, parent, terms)


def _doc(
    code: str,
    page: int,
    owner_line: int,
    owner_text: str,
    period_axis: list[dict[str, Any]],
    units: list[dict[str, Any]],
    mappings: list[dict[str, Any]],
    equations: list[dict[str, Any]],
    source_only_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return base._doc(
        code,
        page,
        owner_line,
        owner_text,
        period_axis,
        units,
        mappings,
        equations,
        source_only_rows or [],
        source_period="2025-12-31",
    )


def _review_documents() -> list[dict[str, Any]]:
    top = "PARENT_TOTAL_EQUALS_VISIBLE_TOP_LEVEL_ROWS"
    employee = "EMPLOYEE_PARENT_EQUALS_VISIBLE_CHILDREN"
    asset = "ASSET_PARENT_EQUALS_VISIBLE_CHILDREN"
    admin = "ADMIN_PARENT_EQUALS_VISIBLE_CHILDREN"
    documents: list[dict[str, Any]] = []

    p = 70
    documents.append(
        _doc(
            "ACB",
            p,
            5,
            "CHI PHÍ HOẠT ĐỘNG",
            [base._label(p, 6, "Năm 2025"), base._label(p, 7, "Năm 2024")],
            [base._label(p, 8, "Triệu VND"), base._label(p, 9, "Triệu VND")],
            [
                _m(
                    p,
                    1205,
                    "TOTAL",
                    5,
                    "CHI PHÍ HOẠT ĐỘNG",
                    46,
                    "10.924.359",
                    47,
                    "10.902.603",
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _m(
                    p,
                    1206,
                    "TAX",
                    10,
                    "Chi nộp thuế và các khoản phí, lệ phí",
                    11,
                    "18.891",
                    12,
                    "18.291",
                ),
                _m(p, 1207, "EMPLOYEE", 13, "Chi phí nhân viên", 14, "6.231.750", 15, "6.468.329"),
                _m(p, 1208, "SALARY", 16, "Chi lương và phụ cấp", 17, "2.462.088", 18, "2.360.339"),
                _m(
                    p,
                    1209,
                    "PAYROLL",
                    19,
                    "Các khoản chi đóng góp theo lương",
                    20,
                    "500.385",
                    21,
                    "490.936",
                ),
                _m(p, 1210, "BENEFIT", 22, "Chi trợ cấp", 23, "13.508", 24, "8.144"),
                _m(
                    p,
                    1211,
                    "OTHER_EMPLOYEE",
                    25,
                    "Chi khác cho nhân viên",
                    26,
                    "3.255.769",
                    27,
                    "3.608.910",
                ),
                _m(p, 1212, "ASSET", 28, "Chi về tài sản", 29, "1.648.010", 30, "1.645.532"),
                _m(
                    p,
                    1213,
                    "DEPRECIATION",
                    31,
                    "Chi phí khấu hao tài sản cố định",
                    32,
                    "425.500",
                    33,
                    "433.368",
                ),
                _m(
                    p,
                    1214,
                    "ADMIN",
                    37,
                    "Chi cho hoạt động quản lý",
                    38,
                    "2.382.631",
                    39,
                    "2.212.159",
                ),
                _m(
                    p,
                    1217,
                    "DEPOSIT_INSURANCE",
                    40,
                    "Chi nộp phí bảo hiểm, bảo toàn tiền gửi của khách hàng",
                    41,
                    "646.439",
                    42,
                    "574.929",
                ),
                _m(
                    p,
                    1218,
                    "LONG_TERM_PROVISION",
                    54,
                    "(Hoàn nhập)/trích lập dự phòng giảm giá đầu tư dài hạn",
                    56,
                    "(8.892)",
                    57,
                    "4.570",
                    topology="WRAPPED_LABEL_WITH_INTERVENING_NOTE_REFERENCE",
                ),
                _m(
                    p,
                    1220,
                    "OTHER_ASSET_PROVISION",
                    58,
                    "Trích lập/(hoàn nhập) dự phòng cho các tài sản Có nội bảng khác",
                    60,
                    "5.530",
                    61,
                    "(21.207)",
                    topology="WRAPPED_LABEL_WITH_INTERVENING_NOTE_REFERENCE",
                ),
            ],
            [
                _eq(
                    top,
                    "TOTAL",
                    [
                        "TAX",
                        "EMPLOYEE",
                        "ASSET",
                        "ADMIN",
                        "DEPOSIT_INSURANCE",
                        "PROVISION_TOTAL_SOURCE_ONLY",
                    ],
                ),
                _eq(employee, "EMPLOYEE", ["SALARY", "PAYROLL", "BENEFIT", "OTHER_EMPLOYEE"]),
                _eq(asset, "ASSET", ["DEPRECIATION", "OTHER_ASSET_SOURCE_ONLY"]),
                _eq(
                    "VISIBLE_PROVISION_TOTAL_EQUALS_TWO_DISCLOSED_COMPONENTS",
                    "PROVISION_TOTAL_SOURCE_ONLY",
                    ["LONG_TERM_PROVISION", "OTHER_ASSET_PROVISION"],
                ),
            ],
            [
                _s(
                    "OE-A2025-001",
                    p,
                    "OTHER_ASSET_SOURCE_ONLY",
                    34,
                    "Chi khác",
                    35,
                    "1.222.510",
                    36,
                    "1.212.164",
                    "The source-specific residual asset-cost row has no distinct live TM schema leaf and is retained without narrowing it to another expense concept.",
                ),
                _s(
                    "OE-A2025-002",
                    p,
                    "PROVISION_TOTAL_SOURCE_ONLY",
                    43,
                    "Hoàn nhập chi phí dự phòng",
                    44,
                    "(3.362)",
                    45,
                    "(16.637)",
                    "The printed aggregate provision line is retained source-only because its two separately disclosed components are mapped independently and the aggregate must not be double counted.",
                ),
            ],
        )
    )

    p = 74
    documents.append(
        _doc(
            "MBB",
            p,
            54,
            "CHI PHÍ HOẠT ĐỘNG",
            [base._label(p, 55, "Năm 2025"), base._label(p, 56, "Năm 2024")],
            [base._label(p, 57, "triệu đồng"), base._label(p, 58, "triệu đồng")],
            [
                _m(
                    p,
                    1205,
                    "TOTAL",
                    54,
                    "CHI PHÍ HOẠT ĐỘNG",
                    99,
                    "19.681.153",
                    100,
                    "17.007.250",
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _m(
                    p,
                    1206,
                    "TAX",
                    59,
                    "Chi nộp thuế và các khoản phí, lệ phí",
                    60,
                    "187.529",
                    61,
                    "156.767",
                ),
                _m(
                    p,
                    1207,
                    "EMPLOYEE",
                    62,
                    "Chi phí cho nhân viên",
                    63,
                    "11.212.709",
                    64,
                    "9.381.603",
                ),
                _m(
                    p,
                    1208,
                    "SALARY",
                    66,
                    "Chi lương và phụ cấp",
                    67,
                    "8.851.768",
                    68,
                    "7.677.049",
                    topology="CONTEXT_BOUND_CHILD_AFTER_INCLUDING_MARKER",
                ),
                _m(p, 1212, "ASSET", 69, "Chi về tài sản", 70, "3.029.987", 71, "3.156.134"),
                _m(
                    p,
                    1213,
                    "DEPRECIATION",
                    73,
                    "Khấu hao tài sản cố định",
                    74,
                    "1.159.215",
                    75,
                    "1.623.989",
                    topology="CONTEXT_BOUND_CHILD_AFTER_INCLUDING_MARKER",
                ),
                _m(
                    p,
                    1214,
                    "ADMIN",
                    79,
                    "Chi cho hoạt động quản lý công vụ",
                    80,
                    "4.652.027",
                    81,
                    "3.691.898",
                ),
                _m(
                    p,
                    1215,
                    "TRAVEL",
                    83,
                    "Công tác phí",
                    84,
                    "219.439",
                    85,
                    "194.239",
                    topology="CONTEXT_BOUND_CHILD_AFTER_INCLUDING_MARKER",
                ),
                _m(
                    p,
                    1216,
                    "UNION",
                    86,
                    "Chi về các hoạt động đoàn thể của TCTD",
                    87,
                    "29.645",
                    88,
                    "35.448",
                ),
                _m(
                    p,
                    1219,
                    "OTHER_ADMIN",
                    89,
                    "Chi khác cho hoạt động quản lý",
                    90,
                    "4.402.943",
                    91,
                    "3.462.211",
                ),
                _m(
                    p,
                    1220,
                    "OTHER_ASSET_PROVISION",
                    92,
                    "(Hoàn nhập)/trích lập các khoản dự phòng",
                    93,
                    "(126.311)",
                    94,
                    "41.874",
                ),
                _m(
                    p,
                    1217,
                    "DEPOSIT_INSURANCE",
                    95,
                    "Chi nộp phí bảo hiểm, bảo toàn tiền gửi của khách hàng",
                    97,
                    "725.212",
                    98,
                    "578.974",
                    topology="WRAPPED_LABEL_CONTINUES_ON_NEXT_LINE",
                ),
            ],
            [
                _eq(
                    top,
                    "TOTAL",
                    [
                        "TAX",
                        "EMPLOYEE",
                        "ASSET",
                        "ADMIN",
                        "OTHER_ASSET_PROVISION",
                        "DEPOSIT_INSURANCE",
                    ],
                ),
                _eq(asset, "ASSET", ["DEPRECIATION", "OTHER_ASSET_SOURCE_ONLY"]),
                _eq(admin, "ADMIN", ["TRAVEL", "UNION", "OTHER_ADMIN"]),
            ],
            [
                _s(
                    "OE-A2025-003",
                    p,
                    "OTHER_ASSET_SOURCE_ONLY",
                    76,
                    "Chi khác về tài sản",
                    77,
                    "1.870.772",
                    78,
                    "1.532.145",
                    "The source-specific residual asset-cost row has no distinct live TM schema leaf and is retained without silently merging it into depreciation.",
                ),
            ],
        )
    )

    p = 72
    documents.append(
        _doc(
            "VPB",
            p,
            5,
            "CHI PHÍ HOẠT ĐỘNG",
            [base._label(p, 6, "Năm 2025"), base._label(p, 7, "Năm 2024")],
            [base._label(p, 8, "Triệu đồng"), base._label(p, 9, "Triệu đồng")],
            [
                _m(
                    p,
                    1205,
                    "TOTAL",
                    5,
                    "CHI PHÍ HOẠT ĐỘNG",
                    75,
                    "18.630.319",
                    76,
                    "14.339.732",
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _m(p, 1206, "TAX", 10, "Chi phí thuế, lệ phí và phí", 11, "16.204", 12, "8.028"),
                _m(
                    p,
                    1207,
                    "EMPLOYEE",
                    13,
                    "Chi phí cho nhân viên",
                    14,
                    "11.202.903",
                    15,
                    "8.395.563",
                ),
                _m(
                    p,
                    1208,
                    "SALARY",
                    19,
                    "Chi lương và phụ cấp",
                    20,
                    "10.297.767",
                    21,
                    "7.616.117",
                    topology="CONTEXT_BOUND_CHILD_AFTER_INCLUDING_MARKER",
                ),
                _m(
                    p,
                    1209,
                    "PAYROLL",
                    23,
                    "Các khoản chi đóng góp theo lương",
                    24,
                    "454.803",
                    25,
                    "407.931",
                ),
                _m(p, 1210, "BENEFIT", 27, "Chi trợ cấp", 28, "178.666", 29, "159.547"),
                _m(p, 1211, "OTHER_EMPLOYEE", 31, "Chi khác", 32, "271.667", 33, "211.968"),
                _m(p, 1212, "ASSET", 35, "Chi về tài sản", 36, "2.190.530", 37, "1.957.629"),
                _m(
                    p,
                    1213,
                    "DEPRECIATION",
                    39,
                    "Khấu hao tài sản cố định",
                    40,
                    "549.588",
                    41,
                    "511.641",
                    topology="CONTEXT_BOUND_CHILD_AFTER_INCLUDING_MARKER",
                ),
                _m(
                    p,
                    1214,
                    "ADMIN",
                    45,
                    "Chi cho hoạt động quản lý công vụ",
                    46,
                    "1.778.538",
                    47,
                    "1.325.488",
                ),
                _m(
                    p,
                    1215,
                    "TRAVEL",
                    49,
                    "Chi công tác phí",
                    50,
                    "38.184",
                    51,
                    "35.153",
                    topology="CONTEXT_BOUND_CHILD_AFTER_INCLUDING_MARKER",
                ),
                _m(
                    p,
                    1216,
                    "UNION",
                    52,
                    "Chi về các hoạt động đoàn thể của TCTD",
                    53,
                    "4.130",
                    54,
                    "486",
                ),
                _m(
                    p,
                    1218,
                    "LONG_TERM_PROVISION",
                    55,
                    "(Hoàn nhập)/trích lập dự phòng rủi ro khác",
                    56,
                    "(35.830)",
                    57,
                    "37.297",
                ),
                _m(
                    p,
                    1217,
                    "DEPOSIT_INSURANCE",
                    62,
                    "Chi phí bảo hiểm tiền gửi của khách hàng",
                    63,
                    "500.858",
                    64,
                    "431.141",
                ),
                _m(
                    p,
                    1219,
                    "OTHER_ADMIN",
                    72,
                    "Chi phí hoạt động khác",
                    73,
                    "1.551.518",
                    74,
                    "1.121.013",
                ),
            ],
            [
                _eq(
                    top,
                    "TOTAL",
                    [
                        "TAX",
                        "EMPLOYEE",
                        "ASSET",
                        "ADMIN",
                        "LONG_TERM_PROVISION",
                        "DEPOSIT_INSURANCE",
                        "IT_SOURCE_ONLY",
                        "NONDEDUCTIBLE_VAT_SOURCE_ONLY",
                        "OTHER_ADMIN",
                    ],
                ),
                _eq(employee, "EMPLOYEE", ["SALARY", "PAYROLL", "BENEFIT", "OTHER_EMPLOYEE"]),
            ],
            [
                _s(
                    "OE-A2025-004",
                    p,
                    "ASSET_RENT_SOURCE_ONLY",
                    42,
                    "Chi thuê tài sản",
                    43,
                    "1.009.205",
                    44,
                    "924.119",
                    "Operating asset-rental expense is a distinct visible source child but the live TM family has no corresponding leaf.",
                ),
                _s(
                    "OE-A2025-005",
                    p,
                    "IT_SOURCE_ONLY",
                    65,
                    "Chi phí công nghệ thông tin",
                    66,
                    "1.275.072",
                    67,
                    "928.944",
                    "Operating information-technology expense is distinct in the source but has no corresponding live TM leaf.",
                ),
                _s(
                    "OE-A2025-006",
                    p,
                    "NONDEDUCTIBLE_VAT_SOURCE_ONLY",
                    68,
                    "Chi về thuế GTGT đầu vào không được khấu trừ",
                    70,
                    "150.526",
                    71,
                    "134.629",
                    "Non-deductible input VAT is a distinct wrapped source row but has no corresponding live TM leaf.",
                ),
            ],
        )
    )

    p = 51
    documents.append(
        _doc(
            "HDB",
            p,
            61,
            "CHI PHÍ HOẠT ĐỘNG",
            [base._label(p, 62, "Năm nay"), base._label(p, 63, "Năm trước")],
            [base._label(p, 64, "Triệu VND"), base._label(p, 65, "Triệu VND")],
            [
                _m(
                    p,
                    1205,
                    "TOTAL",
                    61,
                    "CHI PHÍ HOẠT ĐỘNG",
                    126,
                    "11.600.987",
                    127,
                    "11.980.755",
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _m(
                    p,
                    1206,
                    "TAX",
                    66,
                    "Chi nộp thuế và các khoản phí, lệ phí",
                    67,
                    "7.615",
                    68,
                    "342.322",
                ),
                _m(
                    p,
                    1207,
                    "EMPLOYEE",
                    69,
                    "Chi phí cho nhân viên",
                    70,
                    "6.652.127",
                    71,
                    "6.915.153",
                ),
                _m(p, 1208, "SALARY", 72, "Chi lương và phụ cấp", 73, "6.003.911", 74, "6.318.273"),
                _m(
                    p,
                    1209,
                    "PAYROLL",
                    75,
                    "Các khoản chi đóng góp theo lương",
                    76,
                    "432.671",
                    77,
                    "391.032",
                ),
                _m(p, 1210, "BENEFIT", 78, "Chi trợ cấp", 79, "78.997", 80, "69.365"),
                _m(
                    p,
                    1211,
                    "OTHER_EMPLOYEE",
                    81,
                    "Các khoản chi khác",
                    82,
                    "136.548",
                    83,
                    "136.483",
                ),
                _m(p, 1212, "ASSET", 84, "Chi về tài sản", 85, "1.279.178", 86, "1.162.046"),
                _m(
                    p,
                    1213,
                    "DEPRECIATION",
                    87,
                    "Chi phí khấu hao tài sản cố định",
                    88,
                    "252.007",
                    89,
                    "195.128",
                ),
                _m(
                    p,
                    1214,
                    "ADMIN",
                    99,
                    "Chi cho hoạt động quản lý công vụ",
                    100,
                    "3.113.127",
                    101,
                    "3.132.472",
                ),
                _m(p, 1215, "TRAVEL", 102, "Công tác phí", 103, "94.839", 104, "86.062"),
                _m(
                    p,
                    1216,
                    "UNION",
                    114,
                    "Chi phí về các hoạt động đoàn thể",
                    115,
                    "1.826",
                    116,
                    "6.311",
                ),
                _m(
                    p,
                    1219,
                    "OTHER_ADMIN",
                    117,
                    "Chi khác cho hoạt động quản lý",
                    118,
                    "1.811.497",
                    119,
                    "1.582.608",
                ),
                _m(
                    p,
                    1220,
                    "OTHER_ASSET_PROVISION",
                    120,
                    "Trích lập/(Hoàn nhập) chi phí dự phòng khác",
                    121,
                    "5.960",
                    122,
                    "(1.233)",
                ),
                _m(
                    p,
                    1217,
                    "DEPOSIT_INSURANCE",
                    123,
                    "Chi nộp phí bảo hiểm tiền gửi của khách hàng",
                    124,
                    "542.980",
                    125,
                    "429.995",
                ),
            ],
            [
                _eq(
                    top,
                    "TOTAL",
                    [
                        "TAX",
                        "EMPLOYEE",
                        "ASSET",
                        "ADMIN",
                        "OTHER_ASSET_PROVISION",
                        "DEPOSIT_INSURANCE",
                    ],
                ),
                _eq(employee, "EMPLOYEE", ["SALARY", "PAYROLL", "BENEFIT", "OTHER_EMPLOYEE"]),
                _eq(
                    asset,
                    "ASSET",
                    [
                        "DEPRECIATION",
                        "ASSET_RENT_SOURCE_ONLY",
                        "ASSET_MAINTENANCE_SOURCE_ONLY",
                        "OTHER_ASSET_SOURCE_ONLY",
                    ],
                ),
                _eq(
                    admin,
                    "ADMIN",
                    [
                        "TRAVEL",
                        "ADVERTISING_SOURCE_ONLY",
                        "CONFERENCE_SOURCE_ONLY",
                        "UTILITIES_SOURCE_ONLY",
                        "UNION",
                        "OTHER_ADMIN",
                    ],
                ),
            ],
            [
                _s(
                    "OE-A2025-007",
                    p,
                    "ASSET_RENT_SOURCE_ONLY",
                    90,
                    "Chi thuê tài sản",
                    91,
                    "520.137",
                    92,
                    "510.494",
                    "Operating asset-rental expense is retained source-only because the live TM family has no distinct leaf.",
                ),
                _s(
                    "OE-A2025-008",
                    p,
                    "ASSET_MAINTENANCE_SOURCE_ONLY",
                    93,
                    "Chi về bảo dưỡng và sửa chữa tài sản",
                    94,
                    "372.394",
                    95,
                    "300.759",
                    "Asset maintenance and repair expense is retained source-only because the live TM family has no distinct leaf.",
                ),
                _s(
                    "OE-A2025-009",
                    p,
                    "OTHER_ASSET_SOURCE_ONLY",
                    96,
                    "Chi khác về tài sản",
                    97,
                    "134.640",
                    98,
                    "155.665",
                    "The source-specific residual asset-cost row has no distinct live TM schema leaf.",
                ),
                _s(
                    "OE-A2025-010",
                    p,
                    "ADVERTISING_SOURCE_ONLY",
                    105,
                    "Chi phí quảng cáo, tiếp thị, khuyến mại",
                    106,
                    "812.322",
                    107,
                    "857.690",
                    "Advertising, marketing and promotion expense has no distinct live TM leaf.",
                ),
                _s(
                    "OE-A2025-011",
                    p,
                    "CONFERENCE_SOURCE_ONLY",
                    108,
                    "Chi phí hội nghị, lễ tân, khánh tiết",
                    109,
                    "232.505",
                    110,
                    "458.607",
                    "Conference, reception and hospitality expense has no distinct live TM leaf.",
                ),
                _s(
                    "OE-A2025-012",
                    p,
                    "UTILITIES_SOURCE_ONLY",
                    111,
                    "Chi phí điện, nước, vệ sinh cơ quan",
                    112,
                    "160.138",
                    113,
                    "141.194",
                    "Utilities and office-cleaning expense has no distinct live TM leaf.",
                ),
            ],
        )
    )

    p = 61
    documents.append(
        _doc(
            "VCB",
            p,
            8,
            "31. Chi phí hoạt động",
            [base._label(p, 9, "2025"), base._label(p, 10, "2024")],
            [base._label(p, 11, "Triệu VND"), base._label(p, 12, "Triệu VND")],
            [
                _m(
                    p,
                    1205,
                    "TOTAL",
                    8,
                    "31. Chi phí hoạt động",
                    58,
                    "25.242.799",
                    59,
                    "23.027.363",
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _m(
                    p,
                    1206,
                    "TAX",
                    13,
                    "Chi nộp thuế và các khoản phí, lệ phí",
                    14,
                    "475.707",
                    15,
                    "432.233",
                ),
                _m(
                    p,
                    1207,
                    "EMPLOYEE",
                    16,
                    "Chi phí cho nhân viên",
                    17,
                    "13.662.861",
                    18,
                    "12.271.312",
                ),
                _m(
                    p,
                    1208,
                    "SALARY",
                    21,
                    "Chi lương và phụ cấp",
                    22,
                    "12.192.970",
                    23,
                    "11.032.705",
                    topology="CONTEXT_BOUND_CHILD_AFTER_INCLUDING_MARKER",
                ),
                _m(
                    p,
                    1209,
                    "PAYROLL",
                    24,
                    "Các khoản chi đóng góp theo lương",
                    25,
                    "837.887",
                    26,
                    "701.167",
                ),
                _m(p, 1210, "BENEFIT", 28, "Chi trợ cấp", 29, "4.947", 30, "4.371"),
                _m(
                    p,
                    1211,
                    "OTHER_EMPLOYEE",
                    31,
                    "Chi khác cho nhân viên",
                    32,
                    "627.057",
                    33,
                    "533.069",
                ),
                _m(p, 1212, "ASSET", 34, "Chi về tài sản", 35, "3.826.596", 36, "3.402.747"),
                _m(
                    p,
                    1213,
                    "DEPRECIATION",
                    38,
                    "Khấu hao tài sản cố định",
                    39,
                    "1.385.698",
                    40,
                    "1.086.426",
                    topology="CONTEXT_BOUND_CHILD_AFTER_INCLUDING_MARKER",
                ),
                _m(
                    p,
                    1214,
                    "ADMIN",
                    41,
                    "Chi cho hoạt động quản lý công vụ",
                    42,
                    "6.075.037",
                    43,
                    "5.891.735",
                ),
                _m(
                    p,
                    1217,
                    "DEPOSIT_INSURANCE",
                    44,
                    "Chi nộp phí bảo hiểm, bảo toàn tiền gửi của khách hàng",
                    45,
                    "1.090.552",
                    46,
                    "993.995",
                ),
                _m(
                    p,
                    1218,
                    "LONG_TERM_PROVISION",
                    47,
                    "Hoàn nhập chi phí dự phòng giảm giá đầu tư dài hạn",
                    50,
                    "-",
                    49,
                    "(67.425)",
                    topology="WRAPPED_LABEL_CONTINUES_ON_NEXT_LINE",
                ),
                _m(
                    p,
                    1220,
                    "OTHER_ASSET_PROVISION",
                    51,
                    "Trích lập/(hoàn nhập) dự phòng rủi ro cho các tài sản Có nội bảng khác",
                    53,
                    "3.669",
                    54,
                    "(1.426)",
                    topology="WRAPPED_LABEL_CONTINUES_ON_NEXT_LINE",
                ),
                _m(
                    p,
                    1219,
                    "OTHER_ADMIN",
                    55,
                    "Chi phí hoạt động khác",
                    56,
                    "108.377",
                    57,
                    "104.192",
                ),
            ],
            [
                _eq(
                    top,
                    "TOTAL",
                    [
                        "TAX",
                        "EMPLOYEE",
                        "ASSET",
                        "ADMIN",
                        "DEPOSIT_INSURANCE",
                        "LONG_TERM_PROVISION",
                        "OTHER_ASSET_PROVISION",
                        "OTHER_ADMIN",
                    ],
                ),
                _eq(employee, "EMPLOYEE", ["SALARY", "PAYROLL", "BENEFIT", "OTHER_EMPLOYEE"]),
            ],
        )
    )

    p = 60
    documents.append(
        _doc(
            "CTG",
            p,
            5,
            "CHI PHÍ HOẠT ĐỘNG",
            [
                base._label(p, 6, "Năm tài chính kết thúc ngày"),
                base._label(p, 7, "31.12.2025"),
                base._label(p, 8, "31.12.2024"),
            ],
            [base._label(p, 9, "Triệu đồng"), base._label(p, 10, "Triệu đồng")],
            [
                _m(
                    p,
                    1205,
                    "TOTAL",
                    5,
                    "CHI PHÍ HOẠT ĐỘNG",
                    58,
                    "26.552.924",
                    59,
                    "22.545.929",
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _m(p, 1206, "TAX", 11, "Thuế và các loại phí", 12, "30.757", 13, "32.576"),
                _m(
                    p, 1207, "EMPLOYEE", 15, "Chi phí nhân viên", 16, "15.853.418", 17, "12.987.140"
                ),
                _m(
                    p,
                    1208,
                    "SALARY",
                    18,
                    "Chi lương và phụ cấp",
                    19,
                    "13.146.451",
                    20,
                    "10.920.235",
                ),
                _m(
                    p,
                    1209,
                    "PAYROLL",
                    21,
                    "Các khoản chi đóng góp theo lương",
                    22,
                    "1.127.165",
                    23,
                    "860.771",
                ),
                _m(p, 1210, "BENEFIT", 24, "Chi trợ cấp", 25, "15.588", 26, "4.432"),
                _m(
                    p,
                    1211,
                    "OTHER_EMPLOYEE",
                    27,
                    "Chi khác cho nhân viên",
                    28,
                    "1.564.214",
                    29,
                    "1.201.702",
                ),
                _m(p, 1212, "ASSET", 31, "Chi về tài sản", 32, "3.159.579", 33, "2.862.498"),
                _m(
                    p,
                    1213,
                    "DEPRECIATION",
                    34,
                    "Chi phí khấu hao TSCĐ",
                    35,
                    "1.142.641",
                    36,
                    "1.017.405",
                ),
                _m(
                    p,
                    1214,
                    "ADMIN",
                    40,
                    "Chi cho hoạt động quản lý công vụ",
                    41,
                    "6.106.835",
                    42,
                    "5.114.929",
                ),
                _m(p, 1215, "TRAVEL", 43, "Công tác phí", 44, "254.099", 45, "222.973"),
                _m(
                    p,
                    1216,
                    "UNION",
                    46,
                    "Chi về các hoạt động đoàn thể của TCTD",
                    47,
                    "32.916",
                    48,
                    "12.233",
                ),
                _m(
                    p,
                    1219,
                    "OTHER_ADMIN",
                    49,
                    "Chi khác cho hoạt động quản lý",
                    50,
                    "5.819.820",
                    51,
                    "4.879.723",
                ),
                _m(
                    p,
                    1217,
                    "DEPOSIT_INSURANCE",
                    52,
                    "Chi nộp phí bảo hiểm, bảo toàn tiền gửi của khách hàng",
                    53,
                    "1.241.157",
                    54,
                    "1.121.094",
                ),
            ],
            [
                _eq(
                    top,
                    "TOTAL",
                    [
                        "TAX",
                        "EMPLOYEE",
                        "ASSET",
                        "ADMIN",
                        "DEPOSIT_INSURANCE",
                        "GENERIC_PROVISION_SOURCE_ONLY",
                    ],
                ),
                _eq(employee, "EMPLOYEE", ["SALARY", "PAYROLL", "BENEFIT", "OTHER_EMPLOYEE"]),
                _eq(asset, "ASSET", ["DEPRECIATION", "OTHER_ASSET_SOURCE_ONLY"]),
                _eq(admin, "ADMIN", ["TRAVEL", "UNION", "OTHER_ADMIN"]),
            ],
            [
                _s(
                    "OE-A2025-013",
                    p,
                    "OTHER_ASSET_SOURCE_ONLY",
                    37,
                    "Chi khác",
                    38,
                    "2.016.938",
                    39,
                    "1.845.093",
                    "The source-specific residual asset-cost row has no distinct live TM schema leaf.",
                ),
                _s(
                    "OE-A2025-014",
                    p,
                    "GENERIC_PROVISION_SOURCE_ONLY",
                    55,
                    "Chi phí dự phòng",
                    56,
                    "161.178",
                    57,
                    "427.692",
                    "The source prints only a generic provision-expense row, so it is retained without narrowing it to either long-term-investment or other-asset provision schema leaves.",
                ),
            ],
        )
    )

    p = 57
    documents.append(
        _doc(
            "BID",
            p,
            4,
            "CHI PHÍ HOẠT ĐỘNG",
            [base._label(p, 6, "Năm nay"), base._label(p, 5, "Năm trước")],
            [base._label(p, 8, "Triệu VND"), base._label(p, 9, "Triệu VND")],
            [
                _m(
                    p,
                    1205,
                    "TOTAL",
                    4,
                    "CHI PHÍ HOẠT ĐỘNG",
                    49,
                    "30.427.752",
                    50,
                    "27.979.504",
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _m(
                    p,
                    1206,
                    "TAX",
                    10,
                    "Chi nộp thuế và các khoản phí, lệ phí",
                    11,
                    "79.038",
                    12,
                    "137.234",
                ),
                _m(
                    p,
                    1207,
                    "EMPLOYEE",
                    13,
                    "Chi phí cho nhân viên",
                    14,
                    "17.778.083",
                    15,
                    "15.998.940",
                ),
                _m(
                    p,
                    1208,
                    "SALARY",
                    16,
                    "Trong đó: Chi lương và phụ cấp",
                    17,
                    "14.506.803",
                    18,
                    "13.016.911",
                ),
                _m(
                    p,
                    1209,
                    "PAYROLL",
                    19,
                    "Các khoản chi đóng góp theo lương",
                    20,
                    "1.259.707",
                    21,
                    "1.147.432",
                ),
                _m(
                    p,
                    1211,
                    "OTHER_EMPLOYEE",
                    22,
                    "Chi khác cho nhân viên",
                    23,
                    "1.378.786",
                    24,
                    "1.300.992",
                ),
                _m(p, 1212, "ASSET", 25, "Chi về tài sản", 26, "4.646.199", 27, "4.557.413"),
                _m(
                    p,
                    1213,
                    "DEPRECIATION",
                    28,
                    "Trong đó: Khấu hao tài sản cố định",
                    29,
                    "1.280.491",
                    30,
                    "1.305.764",
                ),
                _m(
                    p,
                    1214,
                    "ADMIN",
                    31,
                    "Chi cho hoạt động quản lý công vụ",
                    32,
                    "6.434.442",
                    33,
                    "5.999.261",
                ),
                _m(p, 1215, "TRAVEL", 34, "Trong đó: Công tác phí", 35, "365.641", 36, "367.042"),
                _m(
                    p,
                    1216,
                    "UNION",
                    37,
                    "Chi hoạt động đoàn thể của TCTD",
                    38,
                    "38.381",
                    39,
                    "29.673",
                ),
                _m(
                    p,
                    1217,
                    "DEPOSIT_INSURANCE",
                    40,
                    "Chi nộp phí bảo hiểm, bảo toàn tiền gửi của khách hàng",
                    41,
                    "1.513.121",
                    42,
                    "1.317.494",
                    topology="WRAPPED_LABEL_CONTINUES_AFTER_VALUES",
                ),
                _m(
                    p,
                    1220,
                    "OTHER_ASSET_PROVISION",
                    44,
                    "(Hoàn nhập) dự phòng",
                    45,
                    "(23.131)",
                    46,
                    "(30.838)",
                    topology="WRAPPED_LABEL_CONTINUES_AFTER_VALUES",
                ),
            ],
            [
                _eq(
                    top,
                    "TOTAL",
                    [
                        "TAX",
                        "EMPLOYEE",
                        "ASSET",
                        "ADMIN",
                        "DEPOSIT_INSURANCE",
                        "OTHER_ASSET_PROVISION",
                    ],
                ),
            ],
        )
    )

    p = 52
    documents.append(
        _doc(
            "VIB",
            p,
            5,
            "CHI PHÍ HOẠT ĐỘNG",
            [base._label(p, 6, "2025"), base._label(p, 7, "2024")],
            [base._label(p, 8, "triệu đồng"), base._label(p, 9, "triệu đồng")],
            [
                _m(
                    p,
                    1205,
                    "TOTAL",
                    5,
                    "CHI PHÍ HOẠT ĐỘNG",
                    28,
                    "7.435.006",
                    29,
                    "7.211.292",
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _m(
                    p,
                    1206,
                    "TAX",
                    10,
                    "Chi nộp thuế và các khoản phí, lệ phí",
                    11,
                    "74.201",
                    12,
                    "66.023",
                ),
                _m(
                    p,
                    1207,
                    "EMPLOYEE",
                    13,
                    "Chi phí cho nhân viên",
                    14,
                    "4.956.379",
                    15,
                    "4.708.481",
                ),
                _m(p, 1212, "ASSET", 16, "Chi về tài sản", 17, "1.354.298", 18, "1.390.001"),
                _m(
                    p,
                    1213,
                    "DEPRECIATION",
                    19,
                    "Trong đó: Khấu hao tài sản cố định",
                    20,
                    "169.133",
                    21,
                    "186.535",
                ),
                _m(
                    p,
                    1214,
                    "ADMIN",
                    22,
                    "Chi cho hoạt động quản lý công vụ",
                    23,
                    "773.775",
                    24,
                    "804.696",
                ),
                _m(
                    p,
                    1217,
                    "DEPOSIT_INSURANCE",
                    25,
                    "Chi nộp phí bảo hiểm tiền gửi của khách hàng",
                    26,
                    "276.353",
                    27,
                    "242.091",
                ),
            ],
            [
                _eq(top, "TOTAL", ["TAX", "EMPLOYEE", "ASSET", "ADMIN", "DEPOSIT_INSURANCE"]),
            ],
        )
    )

    if [item["bank_code"] for item in documents] != list(EXPECTED_DOCUMENT_ORDER):
        raise _error("annual operating-expense review document order drifted")
    return documents


def _configure_base() -> None:
    settings = {
        "FORMAT_VERSION": FORMAT_VERSION,
        "REVIEW_FORMAT": REVIEW_FORMAT,
        "RESULT_STATE": RESULT_STATE,
        "RESULT_ID_PREFIX": RESULT_ID_PREFIX,
        "REVIEW_STATE": REVIEW_STATE,
        "REVIEW_ID_PREFIX": REVIEW_ID_PREFIX,
        "REVIEW_RUN_ID": REVIEW_RUN_ID,
        "ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT": False,
        "SCHEMA_FAMILY_END_DISPLAY_ORDER": 780,
        "CLAIM_BOUNDARY": CLAIM_BOUNDARY,
        "REVIEW_PATH": REVIEW_PATH,
        "RESULT_PATH": RESULT_PATH,
        "SEMANTIC_INDEX_PATH": SEMANTIC_INDEX_PATH,
        "CROP_MANIFEST_PATH": CROP_MANIFEST_PATH,
        "EXPECTED_INDEX_SHA256": EXPECTED_INDEX_SHA256,
        "EXPECTED_CROP_MANIFEST_SHA256": EXPECTED_CROP_MANIFEST_SHA256,
        "EXPECTED_AXIS_SHA256": EXPECTED_AXIS_SHA256,
        "EXPECTED_SCAN_ID": EXPECTED_SCAN_ID,
        "_SCHEMA_EXPECTED": _SCHEMA_EXPECTED,
        "_AUTHORITY": _AUTHORITY,
        "_REVIEW_SAFETY": _REVIEW_SAFETY,
        "_review_documents": _review_documents,
    }
    for name, value in settings.items():
        setattr(base, name, value)


def _review_blueprint() -> dict[str, Any]:
    _configure_base()
    return base._review_blueprint()


def _stable_json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], str]:
    payload = base.income.foundation.support._stable_bytes(path)
    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise _error(f"fixed annual JSON bytes drifted: {path}")
    value = base.income.foundation.support._strict_json(payload, path.as_posix())
    if type(value) is not dict:
        raise _error(f"fixed annual JSON root must be one object: {path}")
    return value, digest


def _live_inputs() -> dict[str, Any]:
    _configure_base()
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = base.scanner.build_live_operating_expense_full_document_scan_v1(
        SEMANTIC_INDEX_PATH
    )
    if structure_scan.get("scan_id") != EXPECTED_SCAN_ID:
        raise _error("annual operating-expense whole-document scan identity drifted")
    review, review_sha = _stable_json(REVIEW_PATH)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return {
        "crop_manifest": crop_manifest,
        "crop_manifest_sha256": crop_sha,
        "review": review,
        "review_sha256": review_sha,
        "schema_authority": schema_authority,
        "schema_by_id": schema_by_id,
        "semantic_index": semantic_index,
        "structure_scan": structure_scan,
    }


def build_live_annual_2025_operating_expense_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    _configure_base()
    result = base.build_operating_expense_8bank_codex_verified_mapping_v1(**_live_inputs())
    if result.get("result_id") != EXPECTED_RESULT_ID or not same_typed_json_v1(
        result["metrics"], _EXPECTED_METRICS
    ):
        raise _error("annual operating-expense fixed denominator metrics drifted")
    for trial in result["trials"]:
        code = trial["document_provenance"]
        if (
            trial["page_span"] != _EXPECTED_PAGES[code]
            or len(trial["verified_mappings"]) != _EXPECTED_MAPPING_COUNTS[code]
            or len(trial["verified_source_only_rows"]) != _EXPECTED_SOURCE_ONLY_COUNTS[code]
        ):
            raise _error(f"annual operating-expense trial denominator drifted: {code}")
    return result


def validate_live_annual_2025_operating_expense_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    _configure_base()
    supplied = base._validate_result(value)
    rebuilt = build_live_annual_2025_operating_expense_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("annual operating-expense verified mapping does not replay exactly")
    return supplied


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
        _write(
            RESULT_PATH,
            build_live_annual_2025_operating_expense_8bank_codex_verified_mapping_v1(),
        )
    if args.validate_result:
        result, _ = _stable_json(RESULT_PATH)
        validate_live_annual_2025_operating_expense_8bank_codex_verified_mapping_v1(result)


if __name__ == "__main__":
    main()
