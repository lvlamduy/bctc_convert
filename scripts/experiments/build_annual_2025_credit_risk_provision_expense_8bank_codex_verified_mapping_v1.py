"""Verify annual-2025 credit-risk provision expense notes across eight banks.

The module configures and reuses the existing credit-risk provision expense
scanner, pixel/source challenger and mapping replay.  It adds only annual
period evidence and the generic controlled aggregation needed when several
visible source rows belong to the single schema catch-all ``Dự phòng khác``.
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
FORMAT_VERSION = "ANNUAL_2025_CREDIT_RISK_PROVISION_EXPENSE_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_CREDIT_RISK_PROVISION_EXPENSE_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_CREDIT_RISK_PROVISION_EXPENSE_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025crpe8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_CREDIT_RISK_PROVISION_EXPENSE_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025crpe8bcv1:pixel-review:"
REVIEW_RUN_ID = "E-0144"
REVIEW_PATH = Path(
    "docs/experiments/E-0144-annual-2025-credit-risk-provision-expense-8bank-"
    "codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0144-annual-2025-credit-risk-provision-expense-8bank-"
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
EXPECTED_SCAN_ID = "crpefdsv1:scan:ce4b61010b2c56efd36d3c471b70742a7e82990088ae6fecbd9e11c8b4bcde2f"
EXPECTED_RESULT_ID = (
    "annual2025crpe8bcv1:result:9c154bb6e05ba6b3e9d41f4457b51c56a3a4a552b8381c7ce1b6117579b83941"
)

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_"
    "VIETOCR_BANK_BLIND_DETAILED_CREDIT_RISK_PROVISION_EXPENSE_GRAPH_"
    "VISIBLE_PDF_UPSTREAM_PPOCRV6_NUMERIC_CHALLENGER_PERIOD_UNIT_"
    "CONTROLLED_CATCHALL_AGGREGATION_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_"
    "NO_CANONICALIZATION_EXPORT_OR_PRODUCTION_AUTHORITY"
)
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "dash_zero_policy_applied_only_to_visible_dash": True,
    "detailed_note_absence_bounded_to_bound_report": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_annual_provision_expense_rows": True,
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
    1221: ("Chi phí dự phòng rủi ro tín dụng", 1142, 781),
    6032: ("Chi phí/(Hoàn nhập) dự phòng rủi ro cho vay TCTD", 1221, 782),
    6031: ("Chi phí/(Hoàn nhập) dự phòng rủi ro cho vay khách hàng", 1221, 785),
    1224: ("Trích lập dự phòng chung cho vay khách hàng", 1221, 786),
    1225: ("Trích lập dự phòng cụ thể cho vay khách hàng", 1221, 787),
    6033: ("Chi phí/(Hoàn nhập) dự phòng mua nợ", 1221, 788),
    1226: ("Trích lập dự phòng trái phiếu đặc biệt VAMC", 1221, 789),
    1227: ("Hoàn nhập dự phòng rủi ro cho các cam kết ngoại bảng", 1221, 790),
    1228: ("Dự phòng khác", 1221, 791),
}
_EXPECTED_PAGES = {
    "ACB": [70, 70],
    "MBB": [75, 75],
    "VPB": [73, 73],
    "HDB": None,
    "VCB": [61, 61],
    "CTG": None,
    "BID": None,
    "VIB": [52, 52],
}
_EXPECTED_MAPPING_COUNTS = {
    "ACB": 4,
    "MBB": 6,
    "VPB": 4,
    "HDB": 0,
    "VCB": 5,
    "CTG": 0,
    "BID": 0,
    "VIB": 6,
}
_EXPECTED_METRICS = {
    "accounting_equation_verified_count": 12,
    "authenticated_pixel_dash_zero_count": 1,
    "detailed_note_not_present_document_count": 3,
    "document_count": 8,
    "document_unique_region_count": 5,
    "fresh_vietocr_numeric_disagreement_count": 0,
    "mapping_verified_count": 25,
    "open_source_row_count": 0,
    "q1_source_period_caveat_document_count": 0,
    "verified_value_cell_count": 50,
}


class Annual2025CreditRiskProvisionExpense8BankError(ValueError):
    """Annual provision-expense evidence or replay drifted."""


def _error(message: str) -> Annual2025CreditRiskProvisionExpense8BankError:
    return Annual2025CreditRiskProvisionExpense8BankError(message)


def _load_base() -> ModuleType:
    path = (
        PROJECT_ROOT
        / "scripts/experiments/build_credit_risk_provision_expense_8bank_codex_verified_mapping_v1.py"
    )
    name = "annual_2025_credit_risk_provision_expense_mapping_base"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual provision-expense support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


base = _load_base()


def _mapping(
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
    return base._mapping(
        role,
        report_norm_id,
        page,
        labels,
        base._line(page, current_line, current_text),
        base._line(page, comparative_line, comparative_text),
        topology,
    )


def _component(
    role: str,
    page: int,
    labels: list[tuple[int, str]],
    current: dict[str, Any],
    comparative: dict[str, Any],
) -> dict[str, Any]:
    return {
        "labels": [base._ref(page, line, text) for line, text in labels],
        "role": role,
        "values": {"COMPARATIVE_PERIOD": comparative, "CURRENT_PERIOD": current},
    }


def _aggregate(
    role: str,
    report_norm_id: int,
    components: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "aggregation_components": components,
        "labels": [],
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": "CONTROLLED_SUM_OF_VISIBLE_SOURCE_ROWS_INTO_ONE_SCHEMA_CATCHALL",
    }


def _equation(name: str, parent: str, terms: list[str]) -> dict[str, Any]:
    return base._equation(name, parent, terms)


def _annual_document(
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


def _review_documents() -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []

    page = 70
    documents.append(
        _annual_document(
            "ACB",
            page,
            ["CUSTOMER_LOAN_PROVISION", "GENERAL_PROVISION"],
            [
                _mapping(
                    "TOTAL",
                    1221,
                    page,
                    [(65, "CHI PHÍ DỰ PHÒNG RỦI RO TÍN DỤNG")],
                    82,
                    "3.334.748",
                    83,
                    "1.606.285",
                    "TRAILING_UNLABELED_TOTAL",
                ),
                _mapping(
                    "GENERAL",
                    1224,
                    page,
                    [
                        (70, "Trích lập dự phòng chung cho vay khách hàng"),
                        (71, "(Thuyết minh 9.7)"),
                    ],
                    72,
                    "743.174",
                    73,
                    "646.754",
                ),
                _mapping(
                    "SPECIFIC",
                    1225,
                    page,
                    [
                        (74, "Trích lập dự phòng cụ thể cho vay khách hàng"),
                        (75, "(Thuyết minh 9.7)"),
                    ],
                    76,
                    "2.592.268",
                    77,
                    "958.730",
                ),
                _mapping(
                    "OTHER_RISK",
                    1228,
                    page,
                    [
                        (78, "(Hoàn nhập)/trích lập dự phòng chung cho khoản phải thu được"),
                        (79, "phân loại là tài sản có rủi ro tín dụng (Thuyết minh 14.4)"),
                    ],
                    80,
                    "(694)",
                    81,
                    "801",
                ),
            ],
            [
                _equation(
                    "VISIBLE_COMPONENTS_EQUAL_TRAILING_TOTAL",
                    "TOTAL",
                    ["GENERAL", "SPECIFIC", "OTHER_RISK"],
                )
            ],
            owner_line=65,
            owner_text="CHI PHÍ DỰ PHÒNG RỦI RO TÍN DỤNG",
            period_axis=[(66, "Năm 2025"), (67, "Năm 2024")],
            units=[(68, "Triệu VND"), (69, "Triệu VND")],
            presentation="GENERAL_SPECIFIC_AND_OTHER_COMPONENTS_THEN_TRAILING_TOTAL",
        )
    )

    page = 75
    documents.append(
        _annual_document(
            "MBB",
            page,
            [
                "CUSTOMER_LOAN_PROVISION",
                "INTERBANK_PROVISION",
                "PURCHASED_DEBT_PROVISION",
                "COMMITMENT_PROVISION",
                "OTHER_RISK_PROVISION",
            ],
            [
                _mapping(
                    "TOTAL",
                    1221,
                    page,
                    [(10, "CHI PHÍ DỰ PHÒNG RỦI RO TÍN DỤNG")],
                    32,
                    "13.743.504",
                    33,
                    "9.576.644",
                    "TRAILING_UNLABELED_TOTAL",
                ),
                _mapping(
                    "CUSTOMER",
                    6031,
                    page,
                    [
                        (15, "Trích lập dự phòng rủi ro cho vay khách hàng trong"),
                        (16, "năm (Thuyết minh 10)"),
                    ],
                    17,
                    "13.690.356",
                    18,
                    "9.534.768",
                ),
                _mapping(
                    "INTERBANK",
                    6032,
                    page,
                    [
                        (19, "Trích lập dự phòng rủi ro cho vay TCTD trong năm"),
                        (20, "(Thuyết minh 7)"),
                    ],
                    21,
                    "2.992",
                    22,
                    "150",
                ),
                _mapping(
                    "PURCHASED_DEBT",
                    6033,
                    page,
                    [(23, "Trích lập dự phòng mua nợ")],
                    24,
                    "66.949",
                    25,
                    "65.093",
                ),
                _mapping(
                    "COMMITMENT",
                    1227,
                    page,
                    [(26, "Trích lập dự phòng với các cam kết đưa ra")],
                    27,
                    "1.088",
                    28,
                    "9",
                ),
                _mapping(
                    "OTHER_RISK",
                    1228,
                    page,
                    [(29, "Hoàn nhập dự phòng rủi ro cho các khoản rủi ro khác")],
                    30,
                    "(17.881)",
                    31,
                    "(23.376)",
                ),
            ],
            [
                _equation(
                    "VISIBLE_COMPONENTS_EQUAL_TRAILING_TOTAL",
                    "TOTAL",
                    ["CUSTOMER", "INTERBANK", "PURCHASED_DEBT", "COMMITMENT", "OTHER_RISK"],
                )
            ],
            owner_line=10,
            owner_text="CHI PHÍ DỰ PHÒNG RỦI RO TÍN DỤNG",
            period_axis=[(11, "Năm 2025"), (12, "Năm 2024")],
            units=[(13, "triệu đồng"), (14, "triệu đồng")],
            presentation="OPTIONAL_COMPONENT_ROWS_THEN_TRAILING_TOTAL",
        )
    )

    page = 73
    vp_other = _aggregate(
        "OTHER_RISK_CATCHALL",
        1228,
        [
            _component(
                "MARGIN_LOAN",
                page,
                [
                    (17, "Chi phí dự phòng cho vay giao dịch ký quỹ và"),
                    (19, "ứng trước (Thuyết minh số 11)"),
                ],
                base._line(page, 20, "77.852"),
                base._line(page, 21, "32.323"),
            ),
            _component(
                "OTHER_RISK_ASSET",
                page,
                [
                    (28, "Chi phí dự phòng rủi ro cho tài sản có rủi ro tín"),
                    (30, "dụng khác (Thuyết minh số 16.4)"),
                ],
                base._dash(
                    page,
                    [1177, 785, 1188, 793],
                    "4011632f1638d81513c0bf0725846c5377e2799dbcc1a2a39ebdbc5a4298c049",
                ),
                base._line(page, 31, "36.678"),
            ),
        ],
    )
    documents.append(
        _annual_document(
            "VPB",
            page,
            ["CUSTOMER_LOAN_PROVISION", "MARGIN_LOAN_PROVISION"],
            [
                _mapping(
                    "TOTAL",
                    1221,
                    page,
                    [(5, "CHI PHÍ DỰ PHÒNG RỦI RO TÍN DỤNG")],
                    32,
                    "25.398.549",
                    33,
                    "27.902.624",
                    "TRAILING_UNLABELED_TOTAL",
                ),
                _mapping(
                    "CUSTOMER",
                    6031,
                    page,
                    [
                        (11, "Chi phí dự phòng rủi ro cho vay khách hàng"),
                        (13, "(Thuyết minh số 11)"),
                    ],
                    14,
                    "25.316.529",
                    15,
                    "27.833.789",
                ),
                _mapping(
                    "PURCHASED_DEBT",
                    6033,
                    page,
                    [
                        (23, "Chi phí/(Hoàn nhập) dự phòng rủi ro hoạt động"),
                        (25, "mua nợ (Thuyết minh số 12)"),
                    ],
                    26,
                    "4.168",
                    27,
                    "(166)",
                ),
                vp_other,
            ],
            [
                _equation(
                    "VISIBLE_COMPONENTS_EQUAL_TRAILING_TOTAL",
                    "TOTAL",
                    ["CUSTOMER", "PURCHASED_DEBT", "OTHER_RISK_CATCHALL"],
                )
            ],
            owner_line=5,
            owner_text="CHI PHÍ DỰ PHÒNG RỦI RO TÍN DỤNG",
            period_axis=[(6, "Năm 2025"), (7, "Năm 2024"), (8, "(Trình bày lại)")],
            units=[(9, "Triệu đồng"), (10, "Triệu đồng")],
            presentation="OPTIONAL_COMPONENT_ROWS_WITH_CONTROLLED_OTHER_CATCHALL_THEN_TOTAL",
        )
    )

    documents.append(base._absence("HDB"))

    page = 61
    vcb_other = _aggregate(
        "OTHER_RISK_CATCHALL",
        1228,
        [
            _component(
                "UNLISTED_CORPORATE_BOND_GENERAL",
                page,
                [
                    (77, "Dự phòng chung cho trái phiếu doanh nghiệp chưa niêm yết"),
                    (78, "Hoàn nhập dự phòng cho chứng khoán đầu tư giữ đến ngày"),
                    (79, "đáo hạn (Thuyết minh 11(b))"),
                ],
                base._line(page, 80, "(12.599)"),
                base._line(page, 81, "(9.068)"),
            ),
            _component(
                "UNLISTED_CORPORATE_BOND_SPECIFIC",
                page,
                [
                    (82, "Dự phòng cụ thể cho trái phiếu doanh nghiệp chưa niêm yết"),
                    (83, "Trích lập dự phòng cho chứng khoán đầu tư giữ đến ngày"),
                    (84, "đáo hạn (Thuyết minh 11(b))"),
                ],
                base._line(page, 85, "3.128.122"),
                base._line(page, 86, "143.000"),
            ),
        ],
    )
    documents.append(
        _annual_document(
            "VCB",
            page,
            ["CUSTOMER_LOAN_PROVISION", "GENERAL_PROVISION", "SPECIFIC_PROVISION"],
            [
                _mapping(
                    "TOTAL",
                    1221,
                    page,
                    [(60, "32. Chi phí dự phòng rủi ro tín dụng")],
                    87,
                    "3.192.186",
                    88,
                    "3.314.998",
                    "TRAILING_UNLABELED_TOTAL",
                ),
                _mapping(
                    "INTERBANK",
                    6032,
                    page,
                    [
                        (65, "Dự phòng rủi ro tiền gửi và cho vay các TCTD khác"),
                        (66, "Hoàn nhập dự phòng (Thuyết minh 6)"),
                    ],
                    67,
                    "(1.000.000)",
                    68,
                    "(4.675.925)",
                ),
                _mapping(
                    "GENERAL",
                    1224,
                    page,
                    [
                        (69, "Dự phòng chung cho vay khách hàng"),
                        (70, "Trích lập dự phòng (Thuyết minh 10)"),
                    ],
                    71,
                    "1.733.057",
                    72,
                    "1.319.289",
                ),
                _mapping(
                    "SPECIFIC",
                    1225,
                    page,
                    [
                        (73, "Dự phòng cụ thể cho vay khách hàng"),
                        (74, "(Hoàn nhập)/Trích lập dự phòng (Thuyết minh 10)"),
                    ],
                    75,
                    "(656.394)",
                    76,
                    "6.537.702",
                ),
                vcb_other,
            ],
            [
                _equation(
                    "VISIBLE_COMPONENTS_EQUAL_TRAILING_TOTAL",
                    "TOTAL",
                    ["INTERBANK", "GENERAL", "SPECIFIC", "OTHER_RISK_CATCHALL"],
                )
            ],
            owner_line=60,
            owner_text="32. Chi phí dự phòng rủi ro tín dụng",
            period_axis=[(61, "2025"), (62, "2024")],
            units=[(63, "Triệu VND"), (64, "Triệu VND")],
            presentation="INTERBANK_CUSTOMER_AND_CONTROLLED_BOND_CATCHALL_THEN_TOTAL",
        )
    )

    documents.extend([base._absence("CTG"), base._absence("BID")])

    page = 52
    documents.append(
        _annual_document(
            "VIB",
            page,
            [
                "CUSTOMER_LOAN_PROVISION",
                "GENERAL_PROVISION",
                "SPECIFIC_PROVISION",
                "PURCHASED_DEBT_PROVISION",
                "NONADDITIVE_DETAIL",
                "TRADE_FINANCE_RECEIVABLE_PROVISION",
            ],
            [
                _mapping(
                    "TOTAL",
                    1221,
                    page,
                    [(31, "CHI PHÍ DỰ PHÒNG RỦI RO TÍN DỤNG")],
                    60,
                    "3.467.019",
                    61,
                    "4.353.458",
                    "TRAILING_UNLABELED_TOTAL",
                ),
                _mapping(
                    "CUSTOMER",
                    6031,
                    page,
                    [(36, "Biến động dự phòng rủi ro cho vay khách hàng")],
                    37,
                    "3.467.296",
                    38,
                    "4.364.409",
                ),
                _mapping(
                    "GENERAL",
                    1224,
                    page,
                    [(39, "Trích lập dự phòng chung")],
                    40,
                    "434.989",
                    41,
                    "400.986",
                ),
                _mapping(
                    "SPECIFIC",
                    1225,
                    page,
                    [(42, "Trích lập dự phòng cụ thể")],
                    43,
                    "3.032.307",
                    44,
                    "3.963.423",
                ),
                _mapping(
                    "PURCHASED_DEBT",
                    6033,
                    page,
                    [(45, "Biến động dự phòng rủi ro hoạt động mua nợ")],
                    46,
                    "(33)",
                    47,
                    "(131)",
                ),
                _mapping(
                    "TRADE_FINANCE",
                    1228,
                    page,
                    [
                        (51, "Biến động dự phòng rủi ro các khoản phải thu từ"),
                        (52, "hoạt động tài trợ thương mại"),
                    ],
                    53,
                    "(244)",
                    54,
                    "(10.820)",
                ),
            ],
            [
                _equation(
                    "GENERAL_PLUS_SPECIFIC_EQUALS_CUSTOMER", "CUSTOMER", ["GENERAL", "SPECIFIC"]
                ),
                _equation(
                    "VISIBLE_COMPONENTS_EQUAL_TRAILING_TOTAL",
                    "TOTAL",
                    ["CUSTOMER", "PURCHASED_DEBT", "TRADE_FINANCE"],
                ),
            ],
            owner_line=31,
            owner_text="CHI PHÍ DỰ PHÒNG RỦI RO TÍN DỤNG",
            period_axis=[(32, "2025"), (33, "2024")],
            units=[(34, "triệu đồng"), (35, "triệu đồng")],
            presentation="PARENT_WITH_GENERAL_SPECIFIC_CHILDREN_AND_NONADDITIVE_DETAIL_ROWS",
        )
    )

    if [item["bank_code"] for item in documents] != list(EXPECTED_DOCUMENT_ORDER):
        raise _error("annual provision-expense review document order drifted")
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
        "SCHEMA_FAMILY_END_DISPLAY_ORDER": 791,
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
    structure_scan = base.scanner.build_live_credit_risk_provision_expense_full_document_scan_v1(
        SEMANTIC_INDEX_PATH
    )
    if structure_scan.get("scan_id") != EXPECTED_SCAN_ID:
        raise _error("annual provision-expense whole-document scan identity drifted")
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


def build_live_annual_2025_credit_risk_provision_expense_8bank_codex_verified_mapping_v1() -> dict[
    str, Any
]:
    _configure_base()
    result = base.build_credit_risk_provision_expense_8bank_codex_verified_mapping_v1(
        **_live_inputs()
    )
    if (
        EXPECTED_RESULT_ID and result.get("result_id") != EXPECTED_RESULT_ID
    ) or not same_typed_json_v1(result["metrics"], _EXPECTED_METRICS):
        raise _error("annual provision-expense fixed denominator metrics drifted")
    for trial in result["trials"]:
        code = trial["document_provenance"]
        if (
            trial["page_span"] != _EXPECTED_PAGES[code]
            or len(trial["verified_mappings"]) != _EXPECTED_MAPPING_COUNTS[code]
            or trial["verified_source_only_rows"]
        ):
            raise _error(f"annual provision-expense trial denominator drifted: {code}")
    return result


def validate_live_annual_2025_credit_risk_provision_expense_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    _configure_base()
    supplied = base._validate_result(value)
    rebuilt = build_live_annual_2025_credit_risk_provision_expense_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("annual provision-expense verified mapping does not replay exactly")
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
            build_live_annual_2025_credit_risk_provision_expense_8bank_codex_verified_mapping_v1(),
        )
    if args.validate_result:
        result, _ = _stable_json(RESULT_PATH)
        validate_live_annual_2025_credit_risk_provision_expense_8bank_codex_verified_mapping_v1(
            result
        )


if __name__ == "__main__":
    main()
