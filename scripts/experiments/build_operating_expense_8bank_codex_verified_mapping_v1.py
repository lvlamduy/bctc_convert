"""Verify operating-expense disclosures across the fixed eight reports.

The full-document matcher supplies the unique region.  This stage binds the
visible rows to the live TM schema, challenges every printed number against
the authenticated PaddleOCR/native source axis, and verifies the accounting
closures that are actually printed.  Source rows without a distinct schema
meaning remain explicit and do not block the rest of the family.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
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


def _load_module(name: str, filename: str) -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load operating-expense support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


income = _load_module(
    "interest_income_support_for_operating_expense_mapping",
    "build_interest_income_8bank_codex_verified_mapping_v1.py",
)
scanner = _load_module(
    "operating_expense_scan_for_verified_mapping",
    "scan_operating_expense_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "OPERATING_EXPENSE_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "OPERATING_EXPENSE_8BANK_CODEX_PIXEL_REVIEW_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_BANK_BLIND_OPERATING_"
    "EXPENSE_GRAPH_VISIBLE_PDF_LABEL_PADDLEOCR_OR_NATIVE_SOURCE_NUMERIC_"
    "CHALLENGER_PERIOD_UNIT_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_UNMAPPED_"
    "SOURCE_ROWS_RETAINED_NO_CANONICALIZATION_EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0088-operating-expense-8bank-codex-pixel-review-v1.json")
RESULT_PATH = Path("docs/experiments/E-0088-operating-expense-8bank-codex-verified-mapping-v1.json")
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
EXPECTED_CROP_MANIFEST_SHA256 = "a9f80cf9104af1177ba43d8a85de00b28c735223a91b663a5a79401bb038d94e"
EXPECTED_AXIS_SHA256 = "e99873cd16a7234702d0ee6e5fa9eb37637a1a75621228381e3dbcd7c5cfdcca"
EXPECTED_SCAN_ID = "oefdsv1:scan:754a51695193ce22eeee6219f52d0542c2ab927fc78ffc2cb8e86a29d8cd0b51"

_SCHEMA_EXPECTED = {
    1142: (
        "II. THÔNG TIN BỔ SUNG CHO CÁC KHOẢN MỤC TRÌNH BÀY TRONG BẢNG KẾT QUẢ KINH DOANH",
        None,
        684,
    ),
    1205: ("Chi phí quản lý chung (Chi phí hoạt động)", 1142, 761),
    1206: ("-Chi nộp thuế và các khoản phí, lệ phí", 1205, 762),
    1207: ("-Chi phí cho nhân viên:", 1205, 763),
    1208: ("Trong đó: + Chi lương và phụ cấp", 1205, 764),
    1209: ("+ Các khoản chi đóng góp theo lương", 1205, 765),
    1210: ("+ Chi trợ cấp", 1205, 766),
    1211: ("+ Chi khác cho nhân viên", 1205, 767),
    1212: ("-Chi về tài sản", 1205, 768),
    1213: ("Trong đó: Chi phí khấu hao", 1205, 769),
    1214: ("-Chi cho hoạt động quản lý công vụ", 1205, 770),
    1215: ("Trong đó: +Công tác phí", 1205, 771),
    1216: ("+Chi về hoạt động đoàn thể của TCTD", 1205, 772),
    1217: ("-Chi phí bảo hiểm tiền gửi của khách hàng", 1205, 773),
    1218: (
        "-Dự phòng giảm giá các khoản đầu tư dài hạn và chi phí dự phòng nợ khó đòi",
        1205,
        774,
    ),
    1219: ("-Chi phí quản lý (hoạt động) khác", 1205, 775),
    1220: ("-(Hoàn nhập)/Trích lập chi phí dự phòng cho tài sản có khác", 1205, 776),
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_operating_expense_rows": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_numeric_challenger_and_accounting_closure_required": True,
    "text_similarity_alone_used_for_mapping": False,
    "unmapped_source_rows_discarded": False,
    "vietocr_numeric_disagreement_is_retained_not_silently_repaired": True,
}
_REVIEW_SAFETY = {
    "bank_page_or_filename_used_as_graph_rule": False,
    "document_or_section_unit_inheritance_recorded_explicitly": True,
    "mapping_decided_by_text_similarity_alone": False,
    "old_ocr_used_as_semantic_anchor": False,
    "optional_rows_required_in_every_bank": False,
    "paddleocr_source_axis_used_as_semantic_anchor": False,
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


class OperatingExpense8BankCodexVerifiedMappingV1Error(ValueError):
    """The fixed structure, pixel, numeric, equation or schema evidence drifted."""


def _error(message: str) -> OperatingExpense8BankCodexVerifiedMappingV1Error:
    return OperatingExpense8BankCodexVerifiedMappingV1Error(message)


def _label(page: int, line: int, text: str) -> dict[str, Any]:
    return income._label(page, line, text)


def _value(page: int, line: int, text: str) -> dict[str, Any]:
    return income._value(page, line, text)


def _mapping(
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
    topology: str = "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
) -> dict[str, Any]:
    return income._mapping(
        report_norm_id,
        role,
        _label(page, label_line, label_text),
        _value(page, current_line, current_text),
        _value(page, comparative_line, comparative_text),
        topology=topology,
    )


def _source_only(
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
    return {
        "label": _label(page, label_line, label_text),
        "reason": reason,
        "role": role,
        "row_id": row_id,
        "values": {
            "COMPARATIVE_PERIOD": _value(page, comparative_line, comparative_text),
            "CURRENT_PERIOD": _value(page, current_line, current_text),
        },
    }


def _equation(
    name: str,
    parent_role: str,
    term_roles: Sequence[str],
) -> dict[str, Any]:
    return {"name": name, "parent_role": parent_role, "term_roles": list(term_roles)}


def _doc(
    code: str,
    page: int,
    owner_line: int,
    owner_text: str,
    period_axis: Sequence[dict[str, Any]],
    units: Sequence[dict[str, Any]],
    mappings: Sequence[dict[str, Any]],
    equations: Sequence[dict[str, Any]],
    source_only_rows: Sequence[dict[str, Any]] = (),
    *,
    source_period: str = "2026-06-30",
    unit_authority: str = "LOCAL_TWO_LANE_MILLION_VND",
) -> dict[str, Any]:
    return {
        "bank_code": code,
        "equations": list(equations),
        "mappings": list(mappings),
        "owner": _label(page, owner_line, owner_text),
        "page_span": [page, page],
        "period_axis": list(period_axis),
        "presentation": "OPTIONAL_TOP_LEVEL_ROWS_WITH_CONTEXT_BOUND_CHILDREN_THEN_TOTAL",
        "source_only_rows": list(source_only_rows),
        "source_period": source_period,
        "unit_authority": unit_authority,
        "unit_evidence": list(units),
    }


def _review_documents() -> list[dict[str, Any]]:
    top = "PARENT_TOTAL_EQUALS_VISIBLE_TOP_LEVEL_ROWS"
    employee = "EMPLOYEE_PARENT_EQUALS_VISIBLE_CHILDREN"
    documents: list[dict[str, Any]] = []

    p = 25
    documents.append(
        _doc(
            "ACB",
            p,
            37,
            "CHI PHÍ HOẠT ĐỘNG",
            [_label(p, 40, "30.6.2026"), _label(p, 41, "30.6.2025")],
            [_label(p, 42, "Triệu đồng"), _label(p, 43, "Triệu đồng")],
            [
                _mapping(
                    p,
                    1205,
                    "TOTAL",
                    37,
                    "CHI PHÍ HOẠT ĐỘNG",
                    84,
                    "5.566.330",
                    85,
                    "5.428.052",
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _mapping(
                    p,
                    1206,
                    "TAX",
                    44,
                    "Chi nộp thuế và các khoản phí, lệ phí",
                    45,
                    "14.764",
                    46,
                    "10.194",
                ),
                _mapping(
                    p,
                    1207,
                    "EMPLOYEE",
                    47,
                    "Chi phí cho nhân viên",
                    48,
                    "3.409.834",
                    49,
                    "3.230.625",
                ),
                _mapping(
                    p, 1208, "SALARY", 50, "Chi lương và phụ cấp", 51, "1.275.883", 52, "1.220.981"
                ),
                _mapping(
                    p,
                    1209,
                    "PAYROLL",
                    53,
                    "Các khoản chi đóng góp theo lương",
                    54,
                    "263.096",
                    55,
                    "251.105",
                ),
                _mapping(p, 1210, "BENEFIT", 56, "Chi trợ cấp", 57, "4.638", 58, "7.065"),
                _mapping(
                    p, 1211, "OTHER_EMPLOYEE", 59, "Chi khác", 60, "1.866.217", 61, "1.751.474"
                ),
                _mapping(p, 1212, "ASSET", 62, "Chi về tài sản", 63, "828.205", 64, "807.648"),
                _mapping(
                    p,
                    1213,
                    "DEPRECIATION",
                    65,
                    "Trong đó: Khấu hao tài sản cố định",
                    66,
                    "217.038",
                    67,
                    "210.440",
                ),
                _mapping(
                    p,
                    1214,
                    "ADMIN",
                    68,
                    "Chi cho hoạt động quản lý công vụ",
                    69,
                    "1.033.135",
                    70,
                    "1.061.195",
                ),
                _mapping(p, 1215, "TRAVEL", 72, "Công tác phí", 73, "16.863", 74, "15.476"),
                _mapping(
                    p,
                    1216,
                    "UNION",
                    75,
                    "Chi về các hoạt động đoàn thể của TCTD",
                    76,
                    "787",
                    77,
                    "1.350",
                ),
                _mapping(
                    p,
                    1217,
                    "DEPOSIT_INSURANCE",
                    78,
                    "Chi nộp phí bảo hiểm, bảo toàn tiền gửi của khách hàng",
                    79,
                    "334.071",
                    80,
                    "316.124",
                ),
                _mapping(
                    p,
                    1218,
                    "PROVISION",
                    81,
                    "Chi dự phòng giảm giá đầu tư dài hạn và rủi ro tài sản khác",
                    82,
                    "(53.679)",
                    83,
                    "2.266",
                ),
            ],
            [
                _equation(
                    top,
                    "TOTAL",
                    ["TAX", "EMPLOYEE", "ASSET", "ADMIN", "DEPOSIT_INSURANCE", "PROVISION"],
                ),
                _equation(employee, "EMPLOYEE", ["SALARY", "PAYROLL", "BENEFIT", "OTHER_EMPLOYEE"]),
            ],
        )
    )

    p = 48
    documents.append(
        _doc(
            "MBB",
            p,
            14,
            "Chi phí hoạt động",
            [
                _label(p, 15, "Từ 01/01/2026"),
                _label(p, 17, "đến 30/06/2026"),
                _label(p, 16, "Từ 01/01/2025"),
                _label(p, 18, "đến 30/06/2025"),
            ],
            [_label(p, 19, "Triệu đồng"), _label(p, 20, "Triệu đồng")],
            [
                _mapping(
                    p,
                    1205,
                    "TOTAL",
                    14,
                    "Chi phí hoạt động",
                    44,
                    "9.974.361",
                    45,
                    "8.906.428",
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _mapping(
                    p,
                    1206,
                    "TAX",
                    21,
                    "Chi nộp thuế và các khoản phí, lệ phí",
                    22,
                    "143.749",
                    23,
                    "77.386",
                ),
                _mapping(
                    p, 1207, "EMPLOYEE", 24, "Chi cho nhân viên", 25, "6.027.145", 26, "5.587.422"
                ),
                _mapping(p, 1212, "ASSET", 27, "Chi về tài sản", 28, "1.657.065", 29, "1.388.523"),
                _mapping(
                    p,
                    1213,
                    "DEPRECIATION",
                    31,
                    "Chi phí khấu hao và khấu trừ",
                    32,
                    "574.246",
                    33,
                    "524.158",
                ),
                _mapping(
                    p,
                    1214,
                    "ADMIN",
                    34,
                    "Chi cho hoạt động quản lý công vụ",
                    35,
                    "1.785.806",
                    36,
                    "1.586.400",
                ),
                _mapping(
                    p,
                    1217,
                    "DEPOSIT_INSURANCE",
                    37,
                    "Chi nộp phí bảo hiểm, bảo toàn tiền gửi của khách hàng",
                    39,
                    "358.872",
                    40,
                    "338.487",
                    topology="WRAPPED_LABEL_CONTINUES_ON_NEXT_LINE",
                ),
                _mapping(
                    p,
                    1220,
                    "OTHER_ASSET_PROVISION",
                    41,
                    "(Hoàn nhập)/trích lập dự phòng khác",
                    42,
                    "1.724",
                    43,
                    "(71.790)",
                ),
            ],
            [
                _equation(
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
                )
            ],
        )
    )

    p = 65
    vpb_open = [
        _source_only(
            "OE-001",
            p,
            "ASSET_RENT",
            48,
            "Chi thuê tài sản",
            49,
            "252.846",
            50,
            "236.877",
            "No distinct live TM schema leaf represents operating asset-rental expense under Chi về tài sản.",
        ),
        _source_only(
            "OE-002",
            p,
            "IT",
            74,
            "Chi phí công nghệ thông tin",
            75,
            "246.529",
            76,
            "235.156",
            "No distinct live TM schema leaf represents operating information-technology expense.",
        ),
        _source_only(
            "OE-003",
            p,
            "NONDEDUCTIBLE_VAT",
            77,
            "Chi về thuế GTGT đầu vào không được khấu trừ",
            78,
            "44.563",
            79,
            "33.759",
            "No distinct live TM schema leaf represents non-deductible input VAT operating expense.",
        ),
    ]
    documents.append(
        _doc(
            "VPB",
            p,
            5,
            "CHI PHÍ HOẠT ĐỘNG",
            [
                _label(p, 8, "3 tháng kết thúc"),
                _label(p, 10, "ngày 31 tháng 3"),
                _label(p, 12, "năm 2026"),
                _label(p, 9, "3 tháng kết thúc"),
                _label(p, 11, "ngày 31 tháng 3"),
                _label(p, 13, "năm 2025"),
            ],
            [_label(p, 14, "Triệu đồng"), _label(p, 15, "Triệu đồng")],
            [
                _mapping(
                    p,
                    1205,
                    "TOTAL",
                    5,
                    "CHI PHÍ HOẠT ĐỘNG",
                    83,
                    "4.318.327",
                    84,
                    "4.071.964",
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _mapping(
                    p, 1206, "TAX", 16, "Chi phí thuế, lệ phí và phí", 17, "5.417", 18, "1.456"
                ),
                _mapping(
                    p,
                    1207,
                    "EMPLOYEE",
                    19,
                    "Chi phí cho nhân viên",
                    20,
                    "2.704.772",
                    21,
                    "2.704.408",
                ),
                _mapping(
                    p, 1208, "SALARY", 24, "Chi lương và phụ cấp", 25, "2.503.773", 26, "2.534.246"
                ),
                _mapping(
                    p,
                    1209,
                    "PAYROLL",
                    28,
                    "Các khoản chi đóng góp theo lương",
                    29,
                    "126.425",
                    30,
                    "112.472",
                ),
                _mapping(p, 1210, "BENEFIT", 32, "Chi trợ cấp", 33, "45.990", 34, "37.509"),
                _mapping(p, 1211, "OTHER_EMPLOYEE", 36, "Chi khác", 37, "28.584", 38, "20.181"),
                _mapping(p, 1212, "ASSET", 39, "Chi về tài sản", 40, "528.278", 41, "489.063"),
                _mapping(
                    p,
                    1213,
                    "DEPRECIATION",
                    44,
                    "Khấu hao tài sản cố định",
                    45,
                    "137.387",
                    46,
                    "130.074",
                ),
                _mapping(
                    p,
                    1214,
                    "ADMIN",
                    51,
                    "Chi cho hoạt động quản lý công vụ",
                    52,
                    "253.566",
                    53,
                    "183.898",
                ),
                _mapping(p, 1215, "TRAVEL", 56, "Chi công tác phí", 57, "5.015", 58, "4.609"),
                _mapping(
                    p,
                    1216,
                    "UNION",
                    60,
                    "Chi về các hoạt động đoàn thể của TCTD",
                    61,
                    "204",
                    62,
                    "35",
                ),
                _mapping(
                    p,
                    1218,
                    "PROVISION",
                    63,
                    "Trích lập dự phòng rủi ro khác",
                    64,
                    "494",
                    65,
                    "1.676",
                    topology="PARENT_ROW_WITH_SUPPORTING_BAD_DEBT_DETAIL",
                ),
                _mapping(
                    p,
                    1217,
                    "DEPOSIT_INSURANCE",
                    71,
                    "Chi phí bảo hiểm tiền gửi của khách hàng",
                    72,
                    "136.514",
                    73,
                    "111.875",
                ),
                _mapping(
                    p,
                    1219,
                    "OTHER_OPERATING",
                    80,
                    "Chi phí hoạt động khác",
                    81,
                    "398.194",
                    82,
                    "310.673",
                ),
            ],
            [
                _equation(
                    top,
                    "TOTAL",
                    [
                        "TAX",
                        "EMPLOYEE",
                        "ASSET",
                        "ADMIN",
                        "PROVISION",
                        "DEPOSIT_INSURANCE",
                        "IT",
                        "NONDEDUCTIBLE_VAT",
                        "OTHER_OPERATING",
                    ],
                ),
                _equation(employee, "EMPLOYEE", ["SALARY", "PAYROLL", "BENEFIT", "OTHER_EMPLOYEE"]),
            ],
            vpb_open,
            source_period="2026-03-31",
        )
    )

    p = 35
    documents.append(
        _doc(
            "HDB",
            p,
            44,
            "Chi phí hoạt động",
            [_label(p, 45, "Kỳ này"), _label(p, 46, "Kỳ trước")],
            [_label(p, 48, "Triệu VND"), _label(p, 49, "Triệu VND")],
            [
                _mapping(
                    p,
                    1205,
                    "TOTAL",
                    44,
                    "Chi phí hoạt động",
                    89,
                    "5.654.071",
                    90,
                    "5.306.552",
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _mapping(
                    p,
                    1206,
                    "TAX",
                    50,
                    "Chi nộp thuế và các khoản phí, lệ phí",
                    51,
                    "1.816",
                    52,
                    "5.627",
                ),
                _mapping(
                    p,
                    1207,
                    "EMPLOYEE",
                    53,
                    "Chi phí cho nhân viên",
                    54,
                    "3.141.599",
                    55,
                    "3.141.440",
                ),
                _mapping(
                    p, 1208, "SALARY", 56, "Chi lương và phụ cấp", 57, "2.796.934", 58, "2.791.642"
                ),
                _mapping(
                    p,
                    1209,
                    "PAYROLL",
                    59,
                    "Các khoản chi đóng góp theo lương",
                    60,
                    "219.471",
                    61,
                    "223.869",
                ),
                _mapping(p, 1210, "BENEFIT", 62, "Chi trợ cấp", 63, "18.927", 64, "55.804"),
                _mapping(
                    p, 1211, "OTHER_EMPLOYEE", 65, "Các khoản chi khác", 66, "106.267", 67, "70.125"
                ),
                _mapping(p, 1212, "ASSET", 68, "Chi về tài sản", 69, "671.134", 70, "596.234"),
                _mapping(
                    p,
                    1213,
                    "DEPRECIATION",
                    71,
                    "Trong đó: Chi phí khấu hao tài sản cố định",
                    72,
                    "147.681",
                    73,
                    "120.460",
                ),
                _mapping(
                    p,
                    1214,
                    "ADMIN",
                    74,
                    "Chi cho hoạt động quản lý công vụ",
                    75,
                    "1.504.337",
                    76,
                    "1.309.761",
                ),
                _mapping(
                    p, 1215, "TRAVEL", 77, "Trong đó: Công tác phí", 78, "34.547", 79, "38.638"
                ),
                _mapping(
                    p,
                    1216,
                    "UNION",
                    80,
                    "Chi phí về các hoạt động đoàn thể",
                    81,
                    "3.838",
                    82,
                    "348",
                ),
                _mapping(
                    p,
                    1217,
                    "DEPOSIT_INSURANCE",
                    83,
                    "Chi nộp phí bảo hiểm tiền gửi của khách hàng",
                    84,
                    "333.696",
                    85,
                    "255.276",
                ),
                _mapping(
                    p,
                    1220,
                    "OTHER_ASSET_PROVISION",
                    86,
                    "Trích lập/(Hoàn nhập) chi phí dự phòng khác",
                    87,
                    "1.489",
                    88,
                    "(1.786)",
                ),
            ],
            [
                _equation(
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
                _equation(employee, "EMPLOYEE", ["SALARY", "PAYROLL", "BENEFIT", "OTHER_EMPLOYEE"]),
            ],
        )
    )

    p = 40
    documents.append(
        _doc(
            "VCB",
            p,
            8,
            "Chi phí hoạt động",
            [
                _label(p, 11, "từ 1/1/2026"),
                _label(p, 13, "đến 30/6/2026"),
                _label(p, 12, "từ 1/1/2025"),
                _label(p, 14, "đến 30/6/2025"),
            ],
            [_label(p, 15, "Triệu VND"), _label(p, 16, "Triệu VND")],
            [
                _mapping(
                    p,
                    1205,
                    "TOTAL",
                    8,
                    "Chi phí hoạt động",
                    53,
                    "15.333.306",
                    54,
                    "11.677.169",
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _mapping(
                    p,
                    1206,
                    "TAX",
                    18,
                    "Chi nộp thuế và các khoản phí, lệ phí",
                    19,
                    "200.157",
                    20,
                    "171.510",
                ),
                _mapping(
                    p,
                    1207,
                    "EMPLOYEE",
                    21,
                    "Chi phí cho nhân viên",
                    22,
                    "8.646.554",
                    23,
                    "6.769.485",
                ),
                _mapping(
                    p, 1208, "SALARY", 25, "Chi lương và phụ cấp", 26, "7.252.625", 27, "5.995.387"
                ),
                _mapping(
                    p,
                    1209,
                    "PAYROLL",
                    28,
                    "Các khoản chi đóng góp theo lương",
                    29,
                    "487.801",
                    30,
                    "369.631",
                ),
                _mapping(p, 1210, "BENEFIT", 31, "Chi trợ cấp", 32, "4.404", 33, "2.895"),
                _mapping(
                    p,
                    1211,
                    "OTHER_EMPLOYEE",
                    34,
                    "Chi khác cho nhân viên",
                    35,
                    "901.724",
                    36,
                    "401.572",
                ),
                _mapping(p, 1212, "ASSET", 37, "Chi về tài sản", 38, "1.777.726", 39, "1.522.181"),
                _mapping(
                    p,
                    1213,
                    "DEPRECIATION",
                    41,
                    "Khấu hao tài sản cố định",
                    42,
                    "791.634",
                    43,
                    "566.013",
                ),
                _mapping(
                    p,
                    1214,
                    "ADMIN",
                    44,
                    "Chi cho hoạt động quản lý công vụ",
                    45,
                    "4.101.267",
                    46,
                    "2.642.477",
                ),
                _mapping(
                    p,
                    1217,
                    "DEPOSIT_INSURANCE",
                    47,
                    "Chi nộp phí bảo hiểm, bảo toàn tiền gửi của khách hàng",
                    48,
                    "556.438",
                    49,
                    "525.764",
                ),
                _mapping(
                    p,
                    1219,
                    "OTHER_OPERATING",
                    50,
                    "Chi phí hoạt động khác",
                    51,
                    "51.164",
                    52,
                    "45.752",
                ),
            ],
            [
                _equation(
                    top,
                    "TOTAL",
                    ["TAX", "EMPLOYEE", "ASSET", "ADMIN", "DEPOSIT_INSURANCE", "OTHER_OPERATING"],
                ),
                _equation(employee, "EMPLOYEE", ["SALARY", "PAYROLL", "BENEFIT", "OTHER_EMPLOYEE"]),
            ],
        )
    )

    p = 47
    ctg_open = [
        _source_only(
            "OE-004",
            p,
            "OTHER_ASSET",
            38,
            "Chi khác về TSCĐ",
            39,
            "807.855",
            40,
            "866.750",
            "No distinct live TM schema leaf represents other fixed-asset operating expense under Chi về tài sản.",
        ),
    ]
    documents.append(
        _doc(
            "CTG",
            p,
            4,
            "CHI PHÍ HOẠT ĐỘNG",
            [
                _label(p, 7, "từ 01/01/2026 đến"),
                _label(p, 9, "hết 30/06/2026"),
                _label(p, 8, "từ 01/01/2025 đến"),
                _label(p, 10, "hết 30/06/2025"),
            ],
            [_label(p, 11, "triệu đồng"), _label(p, 12, "triệu đồng")],
            [
                _mapping(
                    p,
                    1205,
                    "TOTAL",
                    4,
                    "CHI PHÍ HOẠT ĐỘNG",
                    62,
                    "12.616.826",
                    63,
                    "11.366.383",
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _mapping(
                    p,
                    1206,
                    "TAX",
                    13,
                    "Chi nộp thuế và các khoản phí, lệ phí",
                    14,
                    "14.324",
                    15,
                    "13.271",
                ),
                _mapping(
                    p,
                    1207,
                    "EMPLOYEE",
                    16,
                    "Chi phí cho nhân viên",
                    17,
                    "7.724.312",
                    18,
                    "6.764.361",
                ),
                _mapping(
                    p, 1208, "SALARY", 20, "Chi lương và phụ cấp", 21, "6.535.085", 22, "5.471.026"
                ),
                _mapping(
                    p,
                    1209,
                    "PAYROLL",
                    23,
                    "Các khoản chi đóng góp theo lương",
                    24,
                    "561.095",
                    25,
                    "562.498",
                ),
                _mapping(p, 1210, "BENEFIT", 26, "Chi trợ cấp", 27, "10.037", 28, "5.569"),
                _mapping(p, 1211, "OTHER_EMPLOYEE", 29, "Khác", 30, "618.095", 31, "725.268"),
                _mapping(p, 1212, "ASSET", 32, "Chi về tài sản", 33, "1.446.583", 34, "1.361.318"),
                _mapping(
                    p,
                    1213,
                    "DEPRECIATION",
                    35,
                    "Khấu hao tài sản cố định",
                    36,
                    "638.728",
                    37,
                    "494.568",
                ),
                _mapping(
                    p,
                    1214,
                    "ADMIN",
                    41,
                    "Chi cho hoạt động quản lý công vụ",
                    42,
                    "2.852.562",
                    43,
                    "2.633.176",
                ),
                _mapping(p, 1215, "TRAVEL", 45, "Công tác phí", 46, "96.913", 47, "95.545"),
                _mapping(
                    p,
                    1216,
                    "UNION",
                    48,
                    "Chi về các hoạt động đoàn thể của TCTD",
                    49,
                    "9.223",
                    50,
                    "10.127",
                ),
                _mapping(
                    p,
                    1219,
                    "OTHER_OPERATING",
                    51,
                    "Chi khác",
                    52,
                    "2.746.426",
                    53,
                    "2.527.504",
                    topology="CONTEXT_BOUND_ADMINISTRATION_OTHER_ROW",
                ),
                _mapping(
                    p,
                    1217,
                    "DEPOSIT_INSURANCE",
                    54,
                    "Chi nộp phí bảo hiểm, bảo toàn tiền gửi",
                    55,
                    "642.010",
                    56,
                    "603.811",
                ),
                _mapping(
                    p,
                    1220,
                    "OTHER_ASSET_PROVISION",
                    57,
                    "Chi phí/(Hoàn nhập) dự phòng khác",
                    59,
                    "(62.965)",
                    60,
                    "(9.554)",
                    topology="WRAPPED_LABEL_AROUND_TWO_VALUE_LANES",
                ),
            ],
            [
                _equation(
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
                _equation(employee, "EMPLOYEE", ["SALARY", "PAYROLL", "BENEFIT", "OTHER_EMPLOYEE"]),
                _equation(
                    "ASSET_PARENT_EQUALS_VISIBLE_CHILDREN", "ASSET", ["DEPRECIATION", "OTHER_ASSET"]
                ),
                _equation(
                    "ADMINISTRATION_PARENT_EQUALS_VISIBLE_CHILDREN",
                    "ADMIN",
                    ["TRAVEL", "UNION", "OTHER_OPERATING"],
                ),
            ],
            ctg_open,
        )
    )

    p = 30
    documents.append(
        _doc(
            "BID",
            p,
            5,
            "CHI PHÍ HOẠT ĐỘNG",
            [
                _label(p, 6, "Từ 01/01/2026 đến"),
                _label(p, 8, "30/06/2026"),
                _label(p, 7, "Từ 01/01/2025 đến"),
                _label(p, 9, "30/06/2025"),
            ],
            [_label(p, 53, "Đơn vị: Triệu VND")],
            [
                _mapping(
                    p,
                    1205,
                    "TOTAL",
                    5,
                    "CHI PHÍ HOẠT ĐỘNG",
                    50,
                    "14.112.685",
                    51,
                    "13.272.410",
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _mapping(
                    p,
                    1206,
                    "TAX",
                    10,
                    "Chi nộp thuế và các khoản phí, lệ phí",
                    11,
                    "114.911",
                    12,
                    "54.252",
                ),
                _mapping(
                    p,
                    1207,
                    "EMPLOYEE",
                    13,
                    "Chi phí cho nhân viên",
                    14,
                    "7.957.442",
                    15,
                    "7.424.502",
                ),
                _mapping(
                    p, 1208, "SALARY", 16, "Chi lương và phụ cấp", 17, "6.470.064", 18, "6.096.871"
                ),
                _mapping(
                    p,
                    1209,
                    "PAYROLL",
                    19,
                    "Các khoản chi đóng góp theo lương",
                    20,
                    "735.530",
                    21,
                    "600.644",
                ),
                _mapping(p, 1210, "BENEFIT", 22, "Chi trợ cấp", 23, "81.043", 24, "58.105"),
                _mapping(
                    p,
                    1211,
                    "OTHER_EMPLOYEE",
                    25,
                    "Chi khác cho nhân viên",
                    26,
                    "454.514",
                    27,
                    "457.287",
                ),
                _mapping(p, 1212, "ASSET", 28, "Chi về tài sản", 29, "2.232.771", 30, "2.014.930"),
                _mapping(
                    p,
                    1213,
                    "DEPRECIATION",
                    31,
                    "Trong đó, khấu hao tài sản cố định",
                    32,
                    "660.503",
                    33,
                    "631.552",
                ),
                _mapping(
                    p,
                    1214,
                    "ADMIN",
                    34,
                    "Chi cho hoạt động quản lý công vụ",
                    35,
                    "3.039.547",
                    36,
                    "3.047.581",
                ),
                _mapping(p, 1215, "TRAVEL", 37, "Công tác phí", 38, "146.641", 39, "146.838"),
                _mapping(
                    p,
                    1216,
                    "UNION",
                    40,
                    "Chi hoạt động đoàn thể của TCTD",
                    41,
                    "8.206",
                    42,
                    "11.225",
                ),
                _mapping(
                    p,
                    1217,
                    "DEPOSIT_INSURANCE",
                    43,
                    "Chi nộp phí bảo hiểm, bảo toàn tiền gửi của khách hàng",
                    44,
                    "762.885",
                    45,
                    "738.909",
                ),
                _mapping(
                    p,
                    1220,
                    "OTHER_ASSET_PROVISION",
                    46,
                    "Chi phí dự phòng rủi ro khác",
                    47,
                    "5.129",
                    48,
                    "(7.764)",
                    topology="WRAPPED_LABEL_CONTINUES_AFTER_VALUES",
                ),
            ],
            [
                _equation(
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
                )
            ],
            unit_authority="DOCUMENT_SECTION_MILLION_VND_INHERITED_AFTER_BOUND_TABLE",
        )
    )

    p = 46
    documents.append(
        _doc(
            "VIB",
            p,
            83,
            "CHI PHÍ HOẠT ĐỘNG",
            [
                _label(p, 84, "6 tháng đầu"),
                _label(p, 86, "năm 2026"),
                _label(p, 85, "6 tháng đầu"),
                _label(p, 87, "năm 2025"),
            ],
            [_label(p, 88, "triệu đồng"), _label(p, 89, "triệu đồng")],
            [
                _mapping(
                    p,
                    1205,
                    "TOTAL",
                    83,
                    "CHI PHÍ HOẠT ĐỘNG",
                    108,
                    "3.556.551",
                    109,
                    "3.644.650",
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _mapping(
                    p,
                    1206,
                    "TAX",
                    90,
                    "Chi nộp thuế và các khoản phí, lệ phí",
                    91,
                    "34.932",
                    92,
                    "29.836",
                ),
                _mapping(
                    p,
                    1207,
                    "EMPLOYEE",
                    93,
                    "Chi phí cho nhân viên",
                    94,
                    "2.221.055",
                    95,
                    "2.499.625",
                ),
                _mapping(p, 1212, "ASSET", 96, "Chi về tài sản", 97, "785.062", 98, "614.592"),
                _mapping(
                    p,
                    1213,
                    "DEPRECIATION",
                    99,
                    "Trong đó: Khấu hao tài sản cố định",
                    100,
                    "96.344",
                    101,
                    "81.166",
                ),
                _mapping(
                    p,
                    1214,
                    "ADMIN",
                    102,
                    "Chi cho hoạt động quản lý công vụ",
                    103,
                    "375.277",
                    104,
                    "366.348",
                ),
                _mapping(
                    p,
                    1217,
                    "DEPOSIT_INSURANCE",
                    105,
                    "Chi nộp phí bảo hiểm tiền gửi của khách hàng",
                    106,
                    "140.225",
                    107,
                    "134.249",
                ),
            ],
            [_equation(top, "TOTAL", ["TAX", "EMPLOYEE", "ASSET", "ADMIN", "DEPOSIT_INSURANCE"])],
        )
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
            "review_run_id": "E-0088",
        },
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "scan_id": EXPECTED_SCAN_ID,
        "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": EXPECTED_INDEX_SHA256,
        "state": "CODEX_PIXEL_REVIEW_COMPLETE",
    }
    return {**material, "review_id": "e0088:pixel-review:" + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("Codex operating-expense pixel review differs from the fixed ledger")
    return canonical_clone_v1(expected)


def _document(items: Any, code: str, label: str) -> dict[str, Any]:
    return income._document(items, code, label)


def _page(document: Mapping[str, Any], page_sequence: int, label: str) -> dict[str, Any]:
    return income.foundation._page(document, page_sequence, label)


def _semantic_evidence(
    axis_document: Mapping[str, Any], semantic_document: Mapping[str, Any], item: Mapping[str, Any]
) -> dict[str, Any]:
    page_number = item["page_sequence"]
    axis_page = _page(axis_document, page_number, "accounting axis")
    semantic_page = _page(semantic_document, page_number, "semantic index")
    line_index = item["line_index"]
    axis_line = income.foundation.support._axis_line(axis_page, line_index)
    semantic_line = semantic_page["lines"][line_index]
    if (
        semantic_line.get("source_line_index") != line_index
        or semantic_line.get("vietocr_text") != axis_line["vietocr_text"]
    ):
        raise _error("semantic/pixel evidence axis drifted")
    return {
        "crop_ref": canonical_clone_v1(semantic_line["crop_ref"]),
        "fresh_vietocr_proposal": axis_line["vietocr_text"],
        "line_index": line_index,
        "normalized_fresh_vietocr": normalize_vietnamese_anchor_v1(axis_line["vietocr_text"]),
        "normalized_pixel_transcription": normalize_vietnamese_anchor_v1(
            item["pixel_transcription"]
        ),
        "page_sequence": page_number,
        "pixel_transcription": item["pixel_transcription"],
        "source_bbox_raw_pixels": list(axis_line["bbox"]),
    }


def _schema_binding(item: Any, report_norm_id: int) -> dict[str, Any]:
    expected = _SCHEMA_EXPECTED.get(report_norm_id)
    if (
        expected is None
        or item is None
        or item.statement_type != "TM"
        or item.schema_id != report_norm_id
        or item.canonical_name != expected[0]
        or item.parent_id != expected[1]
        or item.display_order != expected[2]
    ):
        raise _error(f"mapping does not bind exact live TM schema row {report_norm_id}")
    return {
        "canonical_name": item.canonical_name,
        "display_order": item.display_order,
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(t["verified_accounting_equations"]) for t in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            t["whole_document_uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for t in trials
        ),
        "fresh_vietocr_numeric_disagreement_count": sum(
            value["fresh_vietocr_numeric_status"] == "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
            for trial in trials
            for collection in (trial["verified_mappings"], trial["verified_source_only_rows"])
            for mapping in collection
            for value in mapping["values"]
        ),
        "mapping_verified_count": sum(len(t["verified_mappings"]) for t in trials),
        "open_source_row_count": sum(len(t["verified_source_only_rows"]) for t in trials),
        "q1_source_period_caveat_document_count": sum(
            t["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2" for t in trials
        ),
        "verified_value_cell_count": sum(
            len(mapping["values"]) for trial in trials for mapping in trial["verified_mappings"]
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("operating-expense result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "OPERATING_EXPENSE_8BANK_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("operating-expense result identity or metrics drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or trial.get("status")
            not in {
                "VERIFIED_BY_CODEX",
                "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT_AND_UNRESOLVED_SCHEMA_ROWS",
                "VERIFIED_BY_CODEX_WITH_UNRESOLVED_SCHEMA_ROWS",
            }
            or any(
                mapping.get("status") != "VERIFIED_BY_CODEX"
                for mapping in trial.get("verified_mappings", [])
            )
            or any(
                row.get("status") != "UNRESOLVED_SCHEMA_GAP_SOURCE_ROW_RETAINED"
                for row in trial.get("verified_source_only_rows", [])
            )
        ):
            raise _error("operating-expense trial shape or status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "e0088:result:" + canonical_json_sha256_v1(material):
        raise _error("operating-expense result identity drifted")
    return canonical_clone_v1(value)


def build_operating_expense_8bank_codex_verified_mapping_v1(
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
    if (
        axis.get("semantic_axis_sha256") != EXPECTED_AXIS_SHA256
        or structure_scan.get("scan_id") != EXPECTED_SCAN_ID
        or structure_scan.get("state") != "FULL_DOCUMENT_OPERATING_EXPENSE_SCAN_COMPLETE"
        or type(crop_manifest) is not dict
    ):
        raise _error("fixed semantic axis, crop manifest, or structure scan drifted")
    trials = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        reviewed = _document(reviewed_documents, code, "pixel review")
        scan_trial = _document(structure_scan["trials"], code, "structure scan")
        axis_document = _document(axis["documents"], code, "accounting axis")
        semantic_document = _document(semantic_index["documents"], code, "semantic index")
        crop_document = _document(crop_manifest["documents"], code, "crop manifest")
        matcher = scan_trial["matcher_result"]
        if not same_typed_json_v1(
            matcher["uniqueness"], {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
        ) or not same_typed_json_v1(matcher["regions"][0]["page_span"], reviewed["page_span"]):
            raise _error("reviewed region is not the unique whole-PDF operating-expense graph")
        value_cache: dict[str, dict[str, Any]] = {}

        def verified(
            ref: Mapping[str, Any],
            *,
            value_cache: dict[str, dict[str, Any]] = value_cache,
            axis_document: Mapping[str, Any] = axis_document,
            semantic_document: Mapping[str, Any] = semantic_document,
            crop_document: Mapping[str, Any] = crop_document,
        ) -> dict[str, Any]:
            key = canonical_json_sha256_v1(ref)
            if key not in value_cache:
                page_number = ref["page_sequence"]
                axis_page = _page(axis_document, page_number, "accounting axis")
                semantic_page = _page(semantic_document, page_number, "semantic index")
                crop_page = _page(crop_document, page_number, "crop manifest")
                source_texts = income.foundation.support._source_line_axis(crop_page)
                evidence = income.foundation.support._source_value(
                    axis_page,
                    semantic_page,
                    crop_page,
                    source_texts,
                    {
                        "line_index": ref["line_index"],
                        "pixel_transcription": ref["pixel_transcription"],
                    },
                )
                try:
                    proposal_value = income.foundation.support._money(
                        evidence["fresh_vietocr_numeric_proposal"]
                    )
                except ValueError:
                    proposal_value = None
                value_cache[key] = {
                    **evidence,
                    "fresh_vietocr_numeric_status": (
                        "MATCHES_SOURCE_NUMERIC_CHALLENGER"
                        if proposal_value == evidence["normalized_value"]
                        else "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
                    ),
                    "page_sequence": page_number,
                }
            return canonical_clone_v1(value_cache[key])

        verified_mappings = []
        by_role: dict[str, dict[str, Any]] = {}
        mapped_ids = set()
        for mapping in reviewed["mappings"]:
            result_mapping = {
                "label_evidence": _semantic_evidence(
                    axis_document, semantic_document, mapping["label"]
                ),
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
            verified_mappings.append(result_mapping)
            by_role[mapping["role"]] = result_mapping
            mapped_ids.add(mapping["report_norm_id"])

        verified_source_only = []
        for row in reviewed["source_only_rows"]:
            result_row = {
                "label_evidence": _semantic_evidence(
                    axis_document, semantic_document, row["label"]
                ),
                "reason": row["reason"],
                "role": row["role"],
                "row_id": row["row_id"],
                "status": "UNRESOLVED_SCHEMA_GAP_SOURCE_ROW_RETAINED",
                "values": [
                    {"axis_role": axis_role, **verified(ref)}
                    for axis_role, ref in row["values"].items()
                ],
            }
            verified_source_only.append(result_row)
            by_role[row["role"]] = result_row

        equations = []
        for specification in reviewed["equations"]:
            parent = by_role[specification["parent_role"]]
            terms = [by_role[role] for role in specification["term_roles"]]
            for axis_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"):
                term_values = [
                    next(value for value in term["values"] if value["axis_role"] == axis_role)
                    for term in terms
                ]
                total = next(value for value in parent["values"] if value["axis_role"] == axis_role)
                computed = sum(item["normalized_value"] for item in term_values)
                if computed != total["normalized_value"]:
                    raise _error(
                        f"operating-expense equation does not close for "
                        f"{code}/{specification['name']}/{axis_role}"
                    )
                equations.append(
                    {
                        "axis_role": axis_role,
                        "computed_value": computed,
                        "name": specification["name"],
                        "parent_role": specification["parent_role"],
                        "status": "VERIFIED_EXACT",
                        "term_roles": list(specification["term_roles"]),
                        "visible_total": total["normalized_value"],
                    }
                )

        source_period_status = (
            "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            if reviewed["source_period"] == "2026-03-31"
            else "VERIFIED_SOURCE_PERIOD_Q2_2026"
        )
        has_open = bool(verified_source_only)
        if source_period_status == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2" and has_open:
            status = "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT_AND_UNRESOLVED_SCHEMA_ROWS"
        elif has_open:
            status = "VERIFIED_BY_CODEX_WITH_UNRESOLVED_SCHEMA_ROWS"
        else:
            status = "VERIFIED_BY_CODEX"
        page_number = reviewed["page_span"][0]
        semantic_page = _page(semantic_document, page_number, "semantic index")
        trials.append(
            {
                "document_ordinal": ordinal,
                "document_provenance": code,
                "mapped_report_norm_ids": sorted(mapped_ids),
                "owner_evidence": _semantic_evidence(
                    axis_document, semantic_document, reviewed["owner"]
                ),
                "page_span": reviewed["page_span"],
                "period_axis_evidence": [
                    _semantic_evidence(axis_document, semantic_document, item)
                    for item in reviewed["period_axis"]
                ],
                "presentation": reviewed["presentation"],
                "source_geometry_mode": semantic_page["geometry_mode"],
                "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                "source_period": reviewed["source_period"],
                "source_period_status": source_period_status,
                "status": status,
                "structure_graph_id": matcher["result_id"],
                "unit_authority": reviewed["unit_authority"],
                "unit_evidence": [
                    _semantic_evidence(axis_document, semantic_document, item)
                    for item in reviewed["unit_evidence"]
                ],
                "verified_accounting_equations": equations,
                "verified_mappings": verified_mappings,
                "verified_source_only_rows": verified_source_only,
                "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
            }
        )

    mapped_union = sorted(
        {
            mapping["schema_binding"]["report_norm_id"]
            for trial in trials
            for mapping in trial["verified_mappings"]
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
            "family_end_display_order": 776,
            "family_root": _schema_binding(schema_by_id.get(1205), 1205),
            "mapped_report_norm_ids": mapped_union,
            "schema_gap_source_row_count": sum(
                len(trial["verified_source_only_rows"]) for trial in trials
            ),
            "section_root": _schema_binding(schema_by_id.get(1142), 1142),
        },
        "state": "OPERATING_EXPENSE_8BANK_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "e0088:result:" + canonical_json_sha256_v1(material)}
    )


def validate_operating_expense_8bank_codex_verified_mapping_replay_v1(
    value: Any,
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
    supplied = _validate_result(value)
    rebuilt = build_operating_expense_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_manifest_sha256,
        review_sha256=review_sha256,
    )
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("operating-expense verified mapping does not replay exactly")
    return supplied


def _stable_json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], str]:
    payload = income.foundation.support._stable_bytes(path)
    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise _error(f"fixed JSON bytes drifted: {path}")
    value = income.foundation.support._strict_json(payload, path.as_posix())
    if type(value) is not dict:
        raise _error(f"fixed JSON root must be one object: {path}")
    return value, digest


def build_live_operating_expense_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_live_operating_expense_full_document_scan_v1()
    review, review_sha = _stable_json(REVIEW_PATH)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return build_operating_expense_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )


def validate_live_operating_expense_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_live_operating_expense_full_document_scan_v1()
    review, review_sha = _stable_json(REVIEW_PATH)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return validate_operating_expense_8bank_codex_verified_mapping_replay_v1(
        value,
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )


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
        _write(RESULT_PATH, build_live_operating_expense_8bank_codex_verified_mapping_v1())
    if args.validate_result:
        result, _ = _stable_json(RESULT_PATH)
        validate_live_operating_expense_8bank_codex_verified_mapping_v1(result)


if __name__ == "__main__":
    main()
