"""Verify annual-2025 other-activity income, expense, and net notes.

This configures the existing whole-document family graph and exact source
numeric challenger for the eight audited consolidated annual reports.  Source
rows that are semantically the schema catch-all are combined only through an
explicit, equation-checked controlled sum.
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
FORMAT_VERSION = "ANNUAL_2025_OTHER_ACTIVITY_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_OTHER_ACTIVITY_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_OTHER_ACTIVITY_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025oa8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_OTHER_ACTIVITY_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025oa8bcv1:pixel-review:"
REVIEW_RUN_ID = "E-0145"
REVIEW_PATH = Path(
    "docs/experiments/E-0145-annual-2025-other-activity-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0145-annual-2025-other-activity-8bank-codex-verified-mapping-v1.json"
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
EXPECTED_SCAN_ID = "oafdsv1:scan:c608bd69c74ae9d2536e6b9d4d9708258471ccef342930e9b87d7b23448eb5a6"
EXPECTED_RESULT_ID = (
    "annual2025oa8bcv1:result:acdebd486d90fb869ef091c494dda455cd4e835589ff9b347a32efbecb07b49c"
)

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_"
    "VIETOCR_BANK_BLIND_OTHER_ACTIVITY_VARIANT_GRAPH_VISIBLE_PDF_"
    "UPSTREAM_PPOCRV6_NUMERIC_CHALLENGER_PERIOD_UNIT_CONTROLLED_CATCHALL_"
    "AGGREGATION_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_NO_CANONICALIZATION_"
    "EXPORT_OR_PRODUCTION_AUTHORITY"
)
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "dash_zero_policy_applied_only_to_visible_dash": True,
    "detailed_note_absence_bounded_to_bound_report": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_annual_other_activity_rows": True,
    "multiple_source_rows_aggregated_only_into_exact_catchall": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_numeric_challenger_and_accounting_closure_required": True,
    "text_similarity_alone_used_for_mapping": False,
    "unmapped_source_rows_discarded": False,
    "whole_pdf_uniqueness_replayed": True,
}
_REVIEW_SAFETY = {
    "bank_page_or_filename_used_as_graph_rule": False,
    "blank_cell_interpreted_as_zero": False,
    "catchall_source_components_double_counted": False,
    "mapping_decided_by_text_similarity_alone": False,
    "old_ocr_used_as_semantic_anchor": False,
    "only_visible_dash_interpreted_as_zero": True,
    "source_parent_and_children_double_counted": False,
    "unmapped_source_rows_retained": True,
    "vietocr_used_as_numeric_truth": False,
    "visible_pdf_pixels_reviewed": True,
    "whole_pdf_uniqueness_replayed": True,
}
_SCHEMA_EXPECTED = {
    1142: (
        "II. THÔNG TIN BỔ SUNG CHO CÁC KHOẢN MỤC TRÌNH BÀY TRONG BẢNG KẾT QUẢ KINH DOANH",
        None,
        686,
    ),
    6029: ("Lãi thuần từ hoạt động kinh doanh khác", 1142, 792),
    6030: ("Thu nhập/(Chi phí) khác", 6029, 793),
    1229: ("Thu nhập từ hoạt động khác", 1142, 794),
    1230: ("Nợ xấu đã được xử lý", 1229, 795),
    1231: ("Chuyển nhượng, thanh lý tài sản", 1229, 796),
    1232: ("Công cụ phái sinh khác", 1229, 797),
    1233: ("Thanh lý Quyền sử dụng đất và TSCĐ khác", 1229, 798),
    1234: ("Thu hồi nợ xấu,nợ đã xử lý, nợ đã xóa sổ trước đây", 1229, 799),
    1235: ("Thu từ hoạt động kinh doanh bất động sản", 1229, 800),
    1236: ("Thu từ hoạt động ủy thác", 1229, 801),
    1237: ("Thu từ nghiệp vụ mua bán nợ", 1229, 802),
    1238: ("Hoàn nhập dự phòng", 1229, 803),
    1239: ("Khác", 1229, 804),
    1240: ("Chi phí từ hoạt động khác", 1142, 805),
    1241: ("Công cụ phái sinh khác", 1240, 806),
    1242: ("Chuyển nhượng, thanh lý tài sản", 1240, 807),
    1243: ("Chi từ nghiệp vụ mua bán nợ", 1240, 808),
    1244: ("Chi công tác xã hội", 1240, 809),
    1245: ("Chi phí thu hồi nợ", 1240, 810),
    1246: ("Khác", 1240, 811),
}
_EXPECTED_PAGES = {
    "ACB": [69, 69],
    "MBB": [74, 74],
    "VPB": [71, 71],
    "HDB": [51, 51],
    "VCB": [60, 60],
    "CTG": [59, 59],
    "BID": [56, 56],
    "VIB": [51, 51],
}
_EXPECTED_MAPPING_COUNTS = {
    "ACB": 6,
    "MBB": 8,
    "VPB": 11,
    "HDB": 10,
    "VCB": 10,
    "CTG": 10,
    "BID": 9,
    "VIB": 8,
}
_EXPECTED_METRICS = {
    "accounting_equation_verified_count": 48,
    "authenticated_pixel_dash_zero_count": 0,
    "detailed_note_not_present_document_count": 0,
    "document_count": 8,
    "document_unique_region_count": 8,
    "fresh_vietocr_numeric_disagreement_count": 0,
    "mapping_verified_count": 72,
    "open_source_row_count": 0,
    "q1_source_period_caveat_document_count": 0,
    "verified_value_cell_count": 144,
}


class Annual2025OtherActivity8BankError(ValueError):
    """Annual other-activity structure, pixels, numbers, or replay drifted."""


def _error(message: str) -> Annual2025OtherActivity8BankError:
    return Annual2025OtherActivity8BankError(message)


def _load_base() -> ModuleType:
    path = (
        PROJECT_ROOT / "scripts/experiments/build_other_activity_8bank_codex_verified_mapping_v1.py"
    )
    name = "annual_2025_other_activity_mapping_base"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual other-activity support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


base = _load_base()


def _line(page: int, line: int, text: str) -> dict[str, Any]:
    return base._line(page, line, text)


def _mapping(
    role: str,
    report_norm_id: int,
    page: int,
    labels: list[tuple[int, str]],
    current: dict[str, Any],
    comparative: dict[str, Any],
    topology: str = "DIRECT_OR_WRAPPED_LABEL_TWO_ANNUAL_PERIOD_LANES",
) -> dict[str, Any]:
    return base._mapping(role, report_norm_id, page, labels, current, comparative, topology)


def _direct(
    role: str,
    report_norm_id: int,
    page: int,
    labels: list[tuple[int, str]],
    current_line: int,
    current_text: str,
    comparative_line: int,
    comparative_text: str,
    topology: str = "DIRECT_OR_WRAPPED_LABEL_TWO_ANNUAL_PERIOD_LANES",
) -> dict[str, Any]:
    return _mapping(
        role,
        report_norm_id,
        page,
        labels,
        _line(page, current_line, current_text),
        _line(page, comparative_line, comparative_text),
        topology,
    )


def _controlled(
    role: str,
    report_norm_id: int,
    page: int,
    labels: list[tuple[int, str]],
    current: list[tuple[int, str]],
    comparative: list[tuple[int, str]],
) -> dict[str, Any]:
    return _mapping(
        role,
        report_norm_id,
        page,
        labels,
        base._sum(page, current),
        base._sum(page, comparative),
        "CONTROLLED_SUM_OF_VISIBLE_SOURCE_ROWS_INTO_ONE_SCHEMA_CATCHALL",
    )


def _equation(name: str, parent: str, terms: list[str]) -> dict[str, Any]:
    return base._equation(name, parent, terms)


def _document(
    code: str,
    page: int,
    graph_roles: list[str],
    mappings: list[dict[str, Any]],
    equations: list[dict[str, Any]],
    *,
    owner_line: int,
    owner_text: str,
    period_axis: list[tuple[int, str]],
    units: list[tuple[int, str]],
    presentation: str,
) -> dict[str, Any]:
    return {
        "absence_evidence": None,
        "bank_code": code,
        "equations": equations,
        "graph_roles": graph_roles,
        "mappings": mappings,
        "owner": [base._ref(page, owner_line, owner_text)],
        "page_span": [page, page],
        "period_axis": [base._ref(page, line, text) for line, text in period_axis],
        "presentation": presentation,
        "source_only_rows": [],
        "source_period": "2025-12-31",
        "unit_evidence": [base._ref(page, line, text) for line, text in units],
    }


def _three_equations(income_terms: list[str], expense_terms: list[str]) -> list[dict[str, Any]]:
    return [
        _equation("INCOME_CHILDREN_EQUAL_INCOME_PARENT", "INCOME", income_terms),
        _equation("EXPENSE_CHILDREN_EQUAL_EXPENSE_PARENT", "EXPENSE", expense_terms),
        _equation("INCOME_PLUS_EXPENSE_EQUALS_NET", "TOTAL", ["INCOME", "EXPENSE"]),
    ]


def _review_documents() -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []

    page = 69
    documents.append(
        _document(
            "ACB",
            page,
            ["INCOME_PARENT", "DEBT_RECOVERY", "INCOME_OTHER", "EXPENSE_PARENT", "EXPENSE_OTHER"],
            [
                _direct(
                    "TOTAL",
                    6029,
                    page,
                    [(5, "LÃI THUẦN TỪ HOẠT ĐỘNG KHÁC")],
                    31,
                    "1.023.287",
                    32,
                    "623.637",
                    "TRAILING_UNLABELED_NET_TOTAL",
                ),
                _direct(
                    "INCOME",
                    1229,
                    page,
                    [(10, "Thu nhập từ hoạt động khác")],
                    20,
                    "2.228.694",
                    21,
                    "1.266.132",
                    "TRAILING_UNLABELED_INCOME_TOTAL",
                ),
                _direct(
                    "DEBT_RECOVERY",
                    1234,
                    page,
                    [(11, "Thu hồi nợ xấu đã sử dụng dự phòng để xử lý rủi ro")],
                    12,
                    "1.084.336",
                    13,
                    "740.938",
                ),
                _controlled(
                    "INCOME_OTHER",
                    1239,
                    page,
                    [(14, "Thu nhập từ hoạt động kinh doanh khác"), (17, "Thu nhập khác")],
                    [(15, "776.150"), (18, "368.208")],
                    [(16, "211.790"), (19, "313.404")],
                ),
                _direct(
                    "EXPENSE",
                    1240,
                    page,
                    [(22, "Chi phí hoạt động khác")],
                    29,
                    "(1.205.407)",
                    30,
                    "(642.495)",
                    "TRAILING_UNLABELED_EXPENSE_TOTAL",
                ),
                _controlled(
                    "EXPENSE_OTHER",
                    1246,
                    page,
                    [(23, "Chi về hoạt động kinh doanh khác"), (26, "Chi phí khác")],
                    [(24, "(1.098.516)"), (27, "(106.891)")],
                    [(25, "(494.389)"), (28, "(148.106)")],
                ),
            ],
            _three_equations(["DEBT_RECOVERY", "INCOME_OTHER"], ["EXPENSE_OTHER"]),
            owner_line=5,
            owner_text="LÃI THUẦN TỪ HOẠT ĐỘNG KHÁC",
            period_axis=[(6, "Năm 2025"), (7, "Năm 2024")],
            units=[(8, "Triệu VND"), (9, "Triệu VND")],
            presentation="GROSS_PARENTS_WITH_CONTROLLED_OTHER_SUBROWS_AND_UNLABELED_TOTALS",
        )
    )

    page = 74
    documents.append(
        _document(
            "MBB",
            page,
            [
                "INCOME_PARENT",
                "DEBT_RECOVERY",
                "INCOME_DERIVATIVE",
                "INCOME_OTHER",
                "EXPENSE_PARENT",
                "EXPENSE_DERIVATIVE",
                "EXPENSE_OTHER",
                "NET_TOTAL",
            ],
            [
                _direct(
                    "TOTAL",
                    6029,
                    page,
                    [(36, "Lãi thuần từ hoạt động khác")],
                    37,
                    "5.314.474",
                    38,
                    "3.280.820",
                    "TRAILING_LABELED_NET_TOTAL",
                ),
                _direct(
                    "INCOME",
                    1229,
                    page,
                    [(15, "Thu nhập từ hoạt động khác")],
                    16,
                    "6.479.624",
                    17,
                    "4.658.444",
                ),
                _direct(
                    "DEBT_RECOVERY",
                    1234,
                    page,
                    [(18, "Thu từ nợ xấu đã được xử lý")],
                    19,
                    "4.141.692",
                    20,
                    "2.451.560",
                ),
                _direct(
                    "INCOME_DERIVATIVE",
                    1232,
                    page,
                    [(21, "Thu từ các công cụ tài chính phái sinh khác")],
                    22,
                    "1.321.173",
                    23,
                    "1.331.187",
                ),
                _direct(
                    "INCOME_OTHER",
                    1239,
                    page,
                    [(24, "Thu nhập khác")],
                    25,
                    "1.016.759",
                    26,
                    "875.697",
                ),
                _direct(
                    "EXPENSE",
                    1240,
                    page,
                    [(27, "Chi phí cho hoạt động khác")],
                    28,
                    "(1.165.150)",
                    29,
                    "(1.377.624)",
                ),
                _direct(
                    "EXPENSE_DERIVATIVE",
                    1241,
                    page,
                    [(30, "Chi từ các công cụ phái sinh khác")],
                    31,
                    "(1.026.496)",
                    32,
                    "(1.233.581)",
                ),
                _direct(
                    "EXPENSE_OTHER",
                    1246,
                    page,
                    [(33, "Chi về hoạt động kinh doanh khác")],
                    34,
                    "(138.654)",
                    35,
                    "(144.043)",
                ),
            ],
            _three_equations(
                ["DEBT_RECOVERY", "INCOME_DERIVATIVE", "INCOME_OTHER"],
                ["EXPENSE_DERIVATIVE", "EXPENSE_OTHER"],
            ),
            owner_line=10,
            owner_text="LÃI THUẦN TỪ HOẠT ĐỘNG KHÁC",
            period_axis=[(11, "Năm 2025"), (12, "Năm 2024")],
            units=[(13, "triệu đồng"), (14, "triệu đồng")],
            presentation="GROSS_INCOME_EXPENSE_CHILDREN_THEN_LABELED_NET_TOTAL",
        )
    )

    page = 71
    documents.append(
        _document(
            "VPB",
            page,
            [
                "INCOME_PARENT",
                "INCOME_DERIVATIVE",
                "DEBT_RECOVERY",
                "INCOME_ASSET_DISPOSAL",
                "INCOME_DEBT_SALE",
                "INCOME_CONTRACT_PENALTY",
                "INCOME_OTHER",
                "EXPENSE_PARENT",
                "EXPENSE_DERIVATIVE",
                "EXPENSE_ASSET_DISPOSAL",
                "EXPENSE_OTHER",
            ],
            [
                _direct(
                    "TOTAL",
                    6029,
                    page,
                    [(5, "LÃI THUẦN TỪ HOẠT ĐỘNG KHÁC")],
                    49,
                    "6.706.160",
                    50,
                    "5.377.662",
                    "TRAILING_UNLABELED_NET_TOTAL",
                ),
                _direct(
                    "INCOME",
                    1229,
                    page,
                    [(10, "Thu nhập từ hoạt động khác")],
                    11,
                    "10.875.443",
                    12,
                    "9.559.809",
                ),
                _direct(
                    "INCOME_DERIVATIVE",
                    1232,
                    page,
                    [(13, "Thu từ các công cụ tài chính phái sinh khác")],
                    14,
                    "3.576.825",
                    15,
                    "3.583.521",
                ),
                _direct(
                    "DEBT_RECOVERY",
                    1234,
                    page,
                    [(16, "Thu từ nợ đã xử lý rủi ro")],
                    17,
                    "5.712.589",
                    18,
                    "5.574.886",
                ),
                _controlled(
                    "INCOME_ASSET_DISPOSAL",
                    1231,
                    page,
                    [(19, "Thu từ thanh lý tài sản cố định"), (22, "Thu từ thanh lý tài sản khác")],
                    [(20, "9.349"), (23, "132.161")],
                    [(21, "1.715"), (24, "34.283")],
                ),
                _direct(
                    "INCOME_DEBT_SALE",
                    1237,
                    page,
                    [(25, "Thu từ hoạt động bán nợ")],
                    26,
                    "130.634",
                    27,
                    "188.732",
                ),
                _controlled(
                    "INCOME_OTHER",
                    1239,
                    page,
                    [(28, "Thu từ phạt vi phạm hợp đồng"), (31, "Thu nhập khác")],
                    [(29, "1.359"), (32, "1.312.526")],
                    [(30, "12.317"), (33, "164.355")],
                ),
                _direct(
                    "EXPENSE",
                    1240,
                    page,
                    [(34, "Chi phí cho hoạt động khác")],
                    35,
                    "(4.169.283)",
                    36,
                    "(4.182.147)",
                ),
                _direct(
                    "EXPENSE_DERIVATIVE",
                    1241,
                    page,
                    [(37, "Chi về các công cụ tài chính phái sinh khác")],
                    38,
                    "(3.794.374)",
                    39,
                    "(3.835.275)",
                ),
                _controlled(
                    "EXPENSE_ASSET_DISPOSAL",
                    1242,
                    page,
                    [(40, "Chi về thanh lý tài sản cố định"), (43, "Chi về thanh lý tài sản khác")],
                    [(41, "(2.201)"), (44, "(115.390)")],
                    [(42, "(259)"), (45, "(27.576)")],
                ),
                _direct(
                    "EXPENSE_OTHER",
                    1246,
                    page,
                    [(46, "Chi khác")],
                    47,
                    "(257.318)",
                    48,
                    "(319.037)",
                ),
            ],
            _three_equations(
                [
                    "INCOME_DERIVATIVE",
                    "DEBT_RECOVERY",
                    "INCOME_ASSET_DISPOSAL",
                    "INCOME_DEBT_SALE",
                    "INCOME_OTHER",
                ],
                ["EXPENSE_DERIVATIVE", "EXPENSE_ASSET_DISPOSAL", "EXPENSE_OTHER"],
            ),
            owner_line=5,
            owner_text="LÃI THUẦN TỪ HOẠT ĐỘNG KHÁC",
            period_axis=[(6, "Năm 2025"), (7, "Năm 2024")],
            units=[(8, "Triệu đồng"), (9, "Triệu đồng")],
            presentation="GROSS_CHILDREN_WITH_CONTROLLED_ASSET_AND_CATCHALL_AGGREGATIONS",
        )
    )

    page = 51
    documents.append(
        _document(
            "HDB",
            page,
            [
                "INCOME_PARENT",
                "DEBT_RECOVERY",
                "INCOME_DEBT_SALE",
                "INCOME_ASSET_DISPOSAL",
                "INCOME_DERIVATIVE",
                "INCOME_OTHER",
                "EXPENSE_PARENT",
                "EXPENSE_DERIVATIVE",
                "EXPENSE_OTHER",
            ],
            [
                _direct(
                    "TOTAL",
                    6029,
                    page,
                    [(8, "LÃI THUẦN TỪ HOẠT ĐỘNG KHÁC")],
                    44,
                    "736.618",
                    45,
                    "352.581",
                    "TRAILING_UNLABELED_NET_TOTAL",
                ),
                _direct(
                    "INCOME",
                    1229,
                    page,
                    [(14, "Thu nhập từ hoạt động khác")],
                    15,
                    "1.026.156",
                    16,
                    "516.572",
                ),
                _direct(
                    "DEBT_RECOVERY",
                    1234,
                    page,
                    [(17, "Thu nhập từ nợ đã xử lý rủi ro")],
                    18,
                    "537.960",
                    19,
                    "276.551",
                ),
                _direct(
                    "INCOME_DEBT_SALE",
                    1237,
                    page,
                    [(20, "Thu từ nghiệp vụ mua bán nợ")],
                    21,
                    "208.115",
                    22,
                    "19.924",
                ),
                _direct(
                    "INCOME_ASSET_DISPOSAL",
                    1231,
                    page,
                    [(23, "Thu lãi trả chậm từ thanh lý tài sản")],
                    24,
                    "7.116",
                    25,
                    "21.519",
                ),
                _direct(
                    "INCOME_DERIVATIVE",
                    1232,
                    page,
                    [(26, "Thu từ các giao dịch phái sinh hàng hóa và lãi suất")],
                    27,
                    "49.553",
                    28,
                    "38.012",
                ),
                _direct(
                    "INCOME_OTHER",
                    1239,
                    page,
                    [(29, "Thu nhập khác")],
                    30,
                    "223.412",
                    31,
                    "160.566",
                ),
                _direct(
                    "EXPENSE",
                    1240,
                    page,
                    [(32, "Chi phí từ hoạt động khác")],
                    33,
                    "(289.538)",
                    34,
                    "(163.991)",
                ),
                _direct(
                    "EXPENSE_DERIVATIVE",
                    1241,
                    page,
                    [(35, "Chi phí từ giao dịch phái sinh hàng hóa và lãi suất")],
                    36,
                    "(40.416)",
                    37,
                    "(27.915)",
                ),
                _controlled(
                    "EXPENSE_OTHER",
                    1246,
                    page,
                    [(38, "Chi phí tài trợ khác"), (41, "Chi phí khác")],
                    [(39, "(99.191)"), (42, "(149.931)")],
                    [(40, "(95.308)"), (43, "(40.768)")],
                ),
            ],
            _three_equations(
                [
                    "DEBT_RECOVERY",
                    "INCOME_DEBT_SALE",
                    "INCOME_ASSET_DISPOSAL",
                    "INCOME_DERIVATIVE",
                    "INCOME_OTHER",
                ],
                ["EXPENSE_DERIVATIVE", "EXPENSE_OTHER"],
            ),
            owner_line=8,
            owner_text="LÃI THUẦN TỪ HOẠT ĐỘNG KHÁC",
            period_axis=[(10, "Năm nay"), (9, "Năm trước"), (11, "(Trình bày lại)")],
            units=[(12, "Triệu VND"), (13, "Triệu VND")],
            presentation="GROSS_CHILDREN_WITH_RESTATED_COMPARATIVE_AND_CONTROLLED_EXPENSE_CATCHALL",
        )
    )

    page = 60
    documents.append(
        _document(
            "VCB",
            page,
            [
                "INCOME_PARENT",
                "DEBT_RECOVERY",
                "INCOME_DERIVATIVE",
                "INCOME_OTHER",
                "EXPENSE_PARENT",
                "EXPENSE_DERIVATIVE",
                "EXPENSE_DEBT_SALE",
                "EXPENSE_SOCIAL",
                "EXPENSE_OTHER",
            ],
            [
                _direct(
                    "TOTAL",
                    6029,
                    page,
                    [(8, "29. Lãi thuần từ hoạt động khác")],
                    44,
                    "3.591.595",
                    45,
                    "2.371.703",
                    "TRAILING_UNLABELED_NET_TOTAL",
                ),
                _direct(
                    "INCOME",
                    1229,
                    page,
                    [(13, "Thu nhập từ hoạt động khác")],
                    27,
                    "5.269.108",
                    28,
                    "4.468.806",
                    "TRAILING_UNLABELED_INCOME_TOTAL",
                ),
                _direct(
                    "DEBT_RECOVERY",
                    1234,
                    page,
                    [
                        (14, "Thu nhập từ các khoản cho vay đã xử lý bằng quỹ"),
                        (16, "dự phòng rủi ro"),
                    ],
                    17,
                    "3.916.056",
                    18,
                    "3.751.009",
                ),
                _direct(
                    "INCOME_DERIVATIVE",
                    1232,
                    page,
                    [(19, "Thu từ nghiệp vụ hoán đổi lãi suất")],
                    20,
                    "919.784",
                    21,
                    "466.824",
                ),
                _direct(
                    "INCOME_OTHER",
                    1239,
                    page,
                    [(22, "Thu nhập khác")],
                    23,
                    "433.268",
                    24,
                    "250.973",
                ),
                _direct(
                    "EXPENSE",
                    1240,
                    page,
                    [(29, "Chi phí hoạt động khác")],
                    42,
                    "(1.677.513)",
                    43,
                    "(2.097.103)",
                    "TRAILING_UNLABELED_EXPENSE_TOTAL",
                ),
                _direct(
                    "EXPENSE_DERIVATIVE",
                    1241,
                    page,
                    [(30, "Chi phí cho nghiệp vụ hoán đổi lãi suất")],
                    31,
                    "(879.065)",
                    32,
                    "(557.373)",
                ),
                _direct(
                    "EXPENSE_DEBT_SALE",
                    1243,
                    page,
                    [(33, "Chi về nghiệp vụ bán nợ")],
                    34,
                    "(80)",
                    35,
                    "(99)",
                ),
                _direct(
                    "EXPENSE_SOCIAL",
                    1244,
                    page,
                    [(36, "Chi công tác xã hội")],
                    37,
                    "(494.368)",
                    38,
                    "(545.792)",
                ),
                _direct(
                    "EXPENSE_OTHER",
                    1246,
                    page,
                    [(39, "Chi phí khác")],
                    40,
                    "(304.000)",
                    41,
                    "(993.839)",
                ),
            ],
            _three_equations(
                ["DEBT_RECOVERY", "INCOME_DERIVATIVE", "INCOME_OTHER"],
                ["EXPENSE_DERIVATIVE", "EXPENSE_DEBT_SALE", "EXPENSE_SOCIAL", "EXPENSE_OTHER"],
            ),
            owner_line=8,
            owner_text="29. Lãi thuần từ hoạt động khác",
            period_axis=[(9, "2025"), (10, "2024")],
            units=[(11, "Triệu VND"), (12, "Triệu VND")],
            presentation="WRAPPED_DEBT_RECOVERY_LABEL_AND_UNLABELED_INCOME_EXPENSE_NET_TOTALS",
        )
    )

    page = 59
    documents.append(
        _document(
            "CTG",
            page,
            [
                "INCOME_PARENT",
                "DEBT_RECOVERY",
                "INCOME_ASSET_DISPOSAL",
                "INCOME_DERIVATIVE",
                "INCOME_OTHER",
                "EXPENSE_PARENT",
                "EXPENSE_DERIVATIVE",
                "EXPENSE_ASSET_DISPOSAL",
                "EXPENSE_OTHER",
            ],
            [
                _direct(
                    "TOTAL",
                    6029,
                    page,
                    [(59, "Lãi thuần")],
                    60,
                    "10.095.362",
                    61,
                    "8.418.786",
                    "TRAILING_LABELED_NET_TOTAL",
                ),
                _direct(
                    "INCOME",
                    1229,
                    page,
                    [(32, "Thu nhập từ hoạt động khác")],
                    33,
                    "11.772.802",
                    34,
                    "10.687.733",
                ),
                _direct(
                    "DEBT_RECOVERY",
                    1234,
                    page,
                    [(35, "Thu nhập từ nợ xấu đã được xử lý")],
                    36,
                    "10.001.921",
                    37,
                    "8.480.766",
                ),
                _direct(
                    "INCOME_ASSET_DISPOSAL",
                    1231,
                    page,
                    [(38, "Thu nhập từ chuyển nhượng, thanh lý tài sản")],
                    39,
                    "22.267",
                    40,
                    "15.158",
                ),
                _direct(
                    "INCOME_DERIVATIVE",
                    1232,
                    page,
                    [(41, "Thu nhập từ công cụ phái sinh khác")],
                    42,
                    "912.971",
                    43,
                    "1.111.458",
                ),
                _direct(
                    "INCOME_OTHER",
                    1239,
                    page,
                    [(44, "Thu nhập khác")],
                    45,
                    "835.643",
                    46,
                    "1.080.351",
                ),
                _direct(
                    "EXPENSE",
                    1240,
                    page,
                    [(47, "Chi phí từ hoạt động khác")],
                    48,
                    "(1.677.440)",
                    49,
                    "(2.268.947)",
                ),
                _direct(
                    "EXPENSE_DERIVATIVE",
                    1241,
                    page,
                    [(50, "Chi phí từ công cụ phái sinh khác")],
                    51,
                    "(911.366)",
                    52,
                    "(1.659.060)",
                ),
                _direct(
                    "EXPENSE_ASSET_DISPOSAL",
                    1242,
                    page,
                    [(53, "Chi phí từ chuyển nhượng, thanh lý tài sản")],
                    54,
                    "(3.861)",
                    55,
                    "(2.641)",
                ),
                _direct(
                    "EXPENSE_OTHER",
                    1246,
                    page,
                    [(56, "Chi phí khác")],
                    57,
                    "(762.213)",
                    58,
                    "(607.246)",
                ),
            ],
            _three_equations(
                ["DEBT_RECOVERY", "INCOME_ASSET_DISPOSAL", "INCOME_DERIVATIVE", "INCOME_OTHER"],
                ["EXPENSE_DERIVATIVE", "EXPENSE_ASSET_DISPOSAL", "EXPENSE_OTHER"],
            ),
            owner_line=26,
            owner_text="LÃI THUẦN TỪ HOẠT ĐỘNG KHÁC",
            period_axis=[
                (27, "Năm tài chính kết thúc ngày"),
                (28, "31.12.2025"),
                (29, "31.12.2024"),
            ],
            units=[(30, "Triệu đồng"), (31, "Triệu đồng")],
            presentation="GROSS_CHILDREN_THEN_SHORT_LABELED_NET_TOTAL",
        )
    )

    page = 56
    documents.append(
        _document(
            "BID",
            page,
            [
                "INCOME_PARENT",
                "DEBT_RECOVERY",
                "INCOME_DERIVATIVE",
                "INCOME_OTHER",
                "EXPENSE_PARENT",
                "EXPENSE_DERIVATIVE",
                "EXPENSE_SOCIAL",
                "EXPENSE_OTHER",
                "NET_TOTAL",
            ],
            [
                _direct(
                    "TOTAL",
                    6029,
                    page,
                    [(77, "Lãi thuần từ hoạt động khác")],
                    78,
                    "13.125.073",
                    79,
                    "5.024.697",
                    "TRAILING_LABELED_NET_TOTAL",
                ),
                _direct(
                    "INCOME",
                    1229,
                    page,
                    [(48, "Thu nhập từ hoạt động khác")],
                    49,
                    "16.249.579",
                    50,
                    "9.229.829",
                ),
                _direct(
                    "DEBT_RECOVERY",
                    1234,
                    page,
                    [(51, "Thu nhập từ nợ xấu đã được xử lý")],
                    52,
                    "14.773.450",
                    53,
                    "8.018.025",
                ),
                _direct(
                    "INCOME_DERIVATIVE",
                    1232,
                    page,
                    [(56, "Thu nhập về các công cụ tài chính phái sinh khác")],
                    57,
                    "1.001.035",
                    58,
                    "955.894",
                ),
                _direct(
                    "INCOME_OTHER", 1239, page, [(59, "Thu khác")], 61, "475.094", 62, "255.910"
                ),
                _direct(
                    "EXPENSE",
                    1240,
                    page,
                    [(64, "Chi phí từ hoạt động khác")],
                    65,
                    "(3.124.506)",
                    66,
                    "(4.205.132)",
                ),
                _direct(
                    "EXPENSE_DERIVATIVE",
                    1241,
                    page,
                    [(68, "Chi về các công cụ tài chính phái sinh khác")],
                    69,
                    "(1.216.821)",
                    70,
                    "(1.979.873)",
                ),
                _direct(
                    "EXPENSE_SOCIAL",
                    1244,
                    page,
                    [(71, "Chi hỗ trợ công tác xã hội")],
                    72,
                    "(394.529)",
                    73,
                    "(287.673)",
                ),
                _direct(
                    "EXPENSE_OTHER",
                    1246,
                    page,
                    [(74, "Chi về hoạt động kinh doanh khác")],
                    75,
                    "(1.513.156)",
                    76,
                    "(1.937.586)",
                ),
            ],
            _three_equations(
                ["DEBT_RECOVERY", "INCOME_DERIVATIVE", "INCOME_OTHER"],
                ["EXPENSE_DERIVATIVE", "EXPENSE_SOCIAL", "EXPENSE_OTHER"],
            ),
            owner_line=42,
            owner_text="LÃI THUẦN TỪ HOẠT ĐỘNG KHÁC",
            period_axis=[(44, "Năm nay"), (43, "Năm trước"), (45, "(Trình bày lại)")],
            units=[(46, "Triệu VND"), (47, "Triệu VND")],
            presentation="GROSS_CHILDREN_WITH_RESTATED_COMPARATIVE_THEN_LABELED_NET_TOTAL",
        )
    )

    page = 51
    documents.append(
        _document(
            "VIB",
            page,
            [
                "INCOME_PARENT",
                "INCOME_DERIVATIVE",
                "DEBT_RECOVERY",
                "INCOME_OTHER",
                "EXPENSE_PARENT",
                "EXPENSE_DERIVATIVE",
                "EXPENSE_OTHER",
                "NET_TOTAL",
            ],
            [
                _direct(
                    "TOTAL",
                    6029,
                    page,
                    [(86, "Lãi thuần từ hoạt động khác")],
                    84,
                    "1.880.913",
                    85,
                    "1.300.500",
                    "PROVIDER_ORDER_NUMBERS_PRECEDE_EXPLICIT_NET_LABEL",
                ),
                _direct(
                    "INCOME",
                    1229,
                    page,
                    [(63, "Thu nhập từ hoạt động khác")],
                    64,
                    "2.338.283",
                    65,
                    "1.518.664",
                ),
                _direct(
                    "INCOME_DERIVATIVE",
                    1232,
                    page,
                    [(66, "Thu từ các công cụ tài chính phái sinh khác")],
                    67,
                    "337.060",
                    68,
                    "215.834",
                ),
                _direct(
                    "DEBT_RECOVERY",
                    1234,
                    page,
                    [(69, "Thu hồi nợ đã xử lý rủi ro")],
                    70,
                    "1.841.868",
                    71,
                    "1.247.253",
                ),
                _direct(
                    "INCOME_OTHER", 1239, page, [(72, "Thu nhập khác")], 73, "159.355", 74, "55.577"
                ),
                _direct(
                    "EXPENSE",
                    1240,
                    page,
                    [(75, "Chi phí hoạt động khác")],
                    76,
                    "(457.370)",
                    77,
                    "(218.164)",
                ),
                _direct(
                    "EXPENSE_DERIVATIVE",
                    1241,
                    page,
                    [(78, "Chi cho các công cụ tài chính phái sinh khác")],
                    79,
                    "(364.510)",
                    80,
                    "(187.066)",
                ),
                _direct(
                    "EXPENSE_OTHER",
                    1246,
                    page,
                    [(83, "Chi phí khác")],
                    81,
                    "(92.860)",
                    82,
                    "(31.098)",
                    "PROVIDER_ORDER_NUMBERS_PRECEDE_LABEL",
                ),
            ],
            _three_equations(
                ["INCOME_DERIVATIVE", "DEBT_RECOVERY", "INCOME_OTHER"],
                ["EXPENSE_DERIVATIVE", "EXPENSE_OTHER"],
            ),
            owner_line=58,
            owner_text="LÃI THUẦN TỪ HOẠT ĐỘNG KHÁC",
            period_axis=[(59, "2025"), (60, "2024")],
            units=[(61, "triệu đồng"), (62, "triệu đồng")],
            presentation="GROSS_CHILDREN_WITH_PROVIDER_ORDER_LABEL_AFTER_NUMBERS",
        )
    )

    if [item["bank_code"] for item in documents] != list(EXPECTED_DOCUMENT_ORDER):
        raise _error("annual other-activity review document order drifted")
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
        "SCHEMA_FAMILY_END_DISPLAY_ORDER": 811,
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
    payload = base.operating.income.foundation.support._stable_bytes(path)
    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise _error(f"fixed annual JSON bytes drifted: {path}")
    value = base.operating.income.foundation.support._strict_json(payload, path.as_posix())
    if type(value) is not dict:
        raise _error(f"fixed annual JSON root must be one object: {path}")
    return value, digest


def _live_inputs() -> dict[str, Any]:
    _configure_base()
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = base.scanner.build_live_other_activity_full_document_scan_v1(
        SEMANTIC_INDEX_PATH
    )
    if structure_scan.get("scan_id") != EXPECTED_SCAN_ID:
        raise _error("annual other-activity whole-document scan identity drifted")
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


def build_live_annual_2025_other_activity_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    _configure_base()
    result = base.build_other_activity_8bank_codex_verified_mapping_v1(**_live_inputs())
    if (
        EXPECTED_RESULT_ID and result.get("result_id") != EXPECTED_RESULT_ID
    ) or not same_typed_json_v1(result["metrics"], _EXPECTED_METRICS):
        raise _error("annual other-activity fixed denominator metrics drifted")
    for trial in result["trials"]:
        code = trial["document_provenance"]
        if (
            trial["page_span"] != _EXPECTED_PAGES[code]
            or len(trial["verified_mappings"]) != _EXPECTED_MAPPING_COUNTS[code]
            or trial["verified_source_only_rows"]
            or trial["status"] != "VERIFIED_BY_CODEX"
        ):
            raise _error(f"annual other-activity trial denominator drifted: {code}")
    return result


def validate_live_annual_2025_other_activity_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    _configure_base()
    supplied = base._validate_result(value)
    rebuilt = build_live_annual_2025_other_activity_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("annual other-activity verified mapping does not replay exactly")
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
        _write(RESULT_PATH, build_live_annual_2025_other_activity_8bank_codex_verified_mapping_v1())
    if args.validate_result:
        result, _ = _stable_json(RESULT_PATH)
        validate_live_annual_2025_other_activity_8bank_codex_verified_mapping_v1(result)


if __name__ == "__main__":
    main()
