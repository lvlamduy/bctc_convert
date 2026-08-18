"""Verify annual-2025 financial-instrument carrying and fair values."""

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

FORMAT_VERSION = "ANNUAL_2025_FINANCIAL_INSTRUMENTS_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_FINANCIAL_INSTRUMENTS_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_FINANCIAL_INSTRUMENTS_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025fi8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_FINANCIAL_INSTRUMENTS_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025fi8bcv1:pixel-review:"
REVIEW_PATH = Path(
    "docs/experiments/E-0154-annual-2025-financial-instruments-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0154-annual-2025-financial-instruments-8bank-codex-verified-mapping-v1.json"
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
EXPECTED_SCAN_ID = "fifdsv1:scan:c30a561fac4a53c493a86024cd3109b241e1fad1583fa2e476a378a1e4845837"
EXPECTED_RESULT_ID: str | None = (
    "annual2025fi8bcv1:result:2d5c59e8640dee0578bc0219178a36262664ad4e7248726228bec889d798ab07"
)

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_"
    "VIETOCR_BANK_BLIND_FINANCIAL_INSTRUMENTS_BOOK_FAIR_GRAPH_VISIBLE_"
    "PDF_SOURCE_NUMERIC_CHALLENGER_EXACT_ACCOUNTING_CLOSURE_LIVE_TM_"
    "SCHEMA_ONLY_NO_EXPORT_AUTHORITY"
)

_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "detailed_table_absence_is_not_source_wide_financial_instrument_absence": True,
    "fair_value_asterisk_interpreted_as_zero": False,
    "fresh_vietocr_used_as_numeric_truth": False,
    "landscape_page_coordinates_kept_upright_and_canonical": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_annual_book_and_numeric_fair_value_cells": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_classification_columns_used_as_schema_selector": False,
    "text_similarity_alone_used_for_mapping": False,
    "unavailable_fair_value_rows_discarded": False,
    "visible_book_value_dash_may_equal_zero_only_with_pixel_binding": True,
}

_SCHEMA_EXPECTED = {
    1259: ("IV. MỘT SỐ THÔNG TIN KHÁC", None, 839),
    1305: ("Công cụ tài chính", 1259, 984),
    1306: ("Giá trị ghi sổ - Công cụ tài chính", 1305, 985),
    1307: ("Tổng tài sản tài chính", 1306, 986),
    1308: ("Tiền mặt, vàng bạc đá quý", 1306, 987),
    1309: ("Tiền gửi tại NHNN", 1306, 988),
    1310: ("Tiền gửi và cho vay các TCTD khác", 1306, 989),
    1311: ("Chứng khoán kinh doanh", 1306, 990),
    1312: ("Công cụ tài chính phái sinh và các tài sản tài chính khác", 1306, 991),
    1313: ("Cho vay khách hàng", 1306, 992),
    1314: ("Chứng khoán đầu tư", 1306, 993),
    1315: ("Đầu tư dài hạn khác", 1306, 994),
    1316: ("Các khoản phải thu", 1306, 995),
    1317: ("Các khoản lãi, phí phải thu", 1306, 996),
    1318: ("Tài sản Có khác", 1306, 997),
    1319: ("Công nợ tài chính", 1306, 998),
    1320: ("Tiền gửi và vay từ NHNN và các TCTD khác", 1306, 999),
    1321: ("Các khoản nợ chính phủ và NHNN", 1306, 1000),
    1322: ("Tiền gửi và vay các TCTD khác", 1306, 1001),
    1323: ("Tiền gửi của khách hàng", 1306, 1002),
    1324: ("Công cụ tài chính phái sinh và các khoản nợ tài chính khác", 1306, 1003),
    1325: ("Vốn tài trợ, ủy thác đầu tư, cho vay TCTD chịu rủi ro", 1306, 1004),
    1326: ("Phát hành giấy tờ có giá", 1306, 1005),
    1327: ("Các khoản lãi, phí phải trả", 1306, 1006),
    1328: ("Các khoản phải trả và công nợ khác", 1306, 1007),
    1329: ("Giá trị hợp lý - Công cụ tài chính", 1305, 1008),
    1330: ("Tổng tài sản tài chính", 1329, 1009),
    1331: ("Tiền mặt, vàng bạc đá quý", 1329, 1010),
    1332: ("Tiền gửi tại NHNN", 1329, 1011),
    1333: ("Tiền gửi và cho vay các TCTD khác", 1329, 1012),
    1334: ("Chứng khoán kinh doanh", 1329, 1013),
    1335: ("Công cụ tài chính phái sinh và các tài sản tài chính khác", 1329, 1014),
    1336: ("Cho vay khách hàng", 1329, 1015),
    1337: ("Chứng khoán đầu tư", 1329, 1016),
    1338: ("Đầu tư dài hạn khác", 1329, 1017),
    1339: ("Các khoản phải thu", 1329, 1018),
    1340: ("Các khoản lãi, phí phải thu", 1329, 1019),
    1341: ("Tài sản Có khác", 1329, 1020),
    1342: ("Công nợ tài chính", 1329, 1021),
    1343: ("Tiền gửi và vay từ NHNN và các TCTD khác", 1329, 1022),
    1344: ("Các khoản nợ chính phủ và NHNN", 1329, 1023),
    1345: ("Tiền gửi và vay các TCTD khác", 1329, 1024),
    1346: ("Tiền gửi của khách hàng", 1329, 1025),
    1347: ("Công cụ tài chính phái sinh và các khoản nợ tài chính khác", 1329, 1026),
    1348: ("Vốn tài trợ, ủy thác đầu tư, cho vay TCTD chịu rủi ro", 1329, 1027),
    1349: ("Phát hành giấy tờ có giá", 1329, 1028),
    1350: ("Các khoản lãi, phí phải trả", 1329, 1029),
    1351: ("Các khoản phải trả và công nợ khác", 1329, 1030),
}


class Annual2025FinancialInstruments8BankError(ValueError):
    """The annual graph, pixels, values, equations or live schema drifted."""


def _error(message: str) -> Annual2025FinancialInstruments8BankError:
    return Annual2025FinancialInstruments8BankError(message)


def _load_base() -> ModuleType:
    path = (
        PROJECT_ROOT
        / "scripts/experiments/build_financial_instruments_8bank_codex_verified_mapping_v1.py"
    )
    name = "annual_2025_financial_instruments_mapping_base_v1"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual financial-instruments support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _book(
    base: ModuleType,
    role: str,
    report_norm_id: int,
    page: int,
    labels: Sequence[tuple[int, str]],
    value: tuple[int, str],
    *,
    topology: str = "BOOK_TOTAL_ROW",
) -> dict[str, Any]:
    return base._mapping(
        role,
        report_norm_id,
        [(page, line, text) for line, text in labels],
        base._line(page, value[0], value[1]),
        axis_role="CARRYING_VALUE",
        topology=topology,
    )


def _fair(
    base: ModuleType,
    role: str,
    report_norm_id: int,
    page: int,
    labels: Sequence[tuple[int, str]],
    value: tuple[int, str],
) -> dict[str, Any]:
    return base._mapping(
        role,
        report_norm_id,
        [(page, line, text) for line, text in labels],
        base._line(page, value[0], value[1]),
        axis_role="FAIR_VALUE",
        topology="NUMERIC_FAIR_VALUE_EXPLICITLY_PRINTED",
    )


def _absence(code: str, reason: str) -> dict[str, Any]:
    return {
        "absence_evidence": {
            "complete_pdf_pages_scanned": True,
            "detailed_table_complete_region_count": 0,
            "reason": reason,
            "source_scope_absence_only": True,
        },
        "bank_code": code,
        "mappings": [],
        "owner": [],
        "page_span": None,
        "source_only_rows": [],
        "source_period": None,
        "unit_evidence": [],
    }


def _review_documents(base: ModuleType) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = [
        _absence(
            "ACB",
            "The complete annual PDF contains a fair-value narrative stating that fair values "
            "have not been determined, but no detailed carrying/fair-value table.",
        ),
        _absence(
            "MBB",
            "The complete annual PDF contains derivative carrying-value tables but no detailed "
            "financial-instrument table with both carrying and fair values.",
        ),
    ]

    page = 94
    documents.append(
        {
            "absence_evidence": None,
            "bank_code": "VPB",
            "mappings": [
                base._mapping(
                    "FAMILY",
                    1305,
                    [(page, 5, "TÀI SẢN TÀI CHÍNH VÀ NỢ PHẢI TRẢ TÀI CHÍNH")],
                ),
                base._mapping("BOOK_BRANCH", 1306, [(page, 7, "Giá trị ghi sổ")]),
                _book(
                    base,
                    "BOOK_TOTAL_ASSETS",
                    1307,
                    page,
                    [(12, "Tổng cộng")],
                    (73, "1.260.972.164"),
                    topology="UNLABELED_ASSET_TOTAL_ROW",
                ),
                _book(
                    base,
                    "BOOK_ASSET_CASH",
                    1308,
                    page,
                    [(34, "Tiền mặt, vàng bạc, đá quý")],
                    (36, "2.774.182"),
                ),
                _book(
                    base,
                    "BOOK_ASSET_CENTRAL_BANK",
                    1309,
                    page,
                    [(38, "Tiền gửi tại Ngân hàng Nhà nước Việt Nam")],
                    (40, "13.570.476"),
                ),
                _book(
                    base,
                    "BOOK_ASSET_INTERBANK",
                    1310,
                    page,
                    [(42, "Tiền gửi và cấp tín dụng cho các Tổ chức tín dụng"), (44, "khác - gộp")],
                    (46, "186.228.938"),
                ),
                _book(
                    base,
                    "BOOK_ASSET_TRADING",
                    1311,
                    page,
                    [(48, "Chứng khoán kinh doanh - gộp")],
                    (50, "24.132.387"),
                ),
                _book(
                    base,
                    "BOOK_ASSET_LOANS",
                    1313,
                    page,
                    [(52, "Cho vay khách hàng và mua nợ - gộp")],
                    (54, "945.263.265"),
                ),
                _book(
                    base,
                    "BOOK_ASSET_INVESTMENT",
                    1314,
                    page,
                    [(56, "Chứng khoán đầu tư sẵn sàng để bán - gộp")],
                    (58, "64.462.930"),
                ),
                _book(
                    base,
                    "BOOK_ASSET_LONG_TERM",
                    1315,
                    page,
                    [(60, "Góp vốn, đầu tư dài hạn - gộp")],
                    (62, "191.960"),
                ),
                _book(
                    base,
                    "BOOK_ASSET_OTHER",
                    1318,
                    page,
                    [(64, "Tài sản tài chính khác")],
                    (68, "24.348.026"),
                ),
                _book(
                    base,
                    "BOOK_TOTAL_LIABILITIES",
                    1319,
                    page,
                    [(12, "Tổng cộng")],
                    (109, "1.069.781.836"),
                    topology="UNLABELED_LIABILITY_TOTAL_ROW",
                ),
                _book(
                    base,
                    "BOOK_LIABILITY_GOVERNMENT",
                    1321,
                    page,
                    [(74, "Các khoản nợ Chính phủ và NHNN Việt Nam")],
                    (76, "15.305"),
                ),
                _book(
                    base,
                    "BOOK_LIABILITY_INTERBANK",
                    1322,
                    page,
                    [(78, "Tiền gửi và vay các Tổ chức tài chính, Tổ chức tín"), (79, "dụng khác")],
                    (81, "295.199.519"),
                ),
                _book(
                    base,
                    "BOOK_LIABILITY_CUSTOMER",
                    1323,
                    page,
                    [(83, "Tiền gửi của khách hàng")],
                    (85, "628.044.616"),
                ),
                _book(
                    base,
                    "BOOK_LIABILITY_DERIVATIVE",
                    1324,
                    page,
                    [(87, "Công cụ tài chính phái sinh và các khoản nợ tài"), (88, "chính khác")],
                    (91, "843.382"),
                ),
                _book(
                    base,
                    "BOOK_LIABILITY_ENTRUSTED",
                    1325,
                    page,
                    [(93, "Vốn tài trợ, ủy thác đầu tư, cho vay TCTD chịu"), (94, "rủi ro")],
                    (96, "16.394"),
                ),
                _book(
                    base,
                    "BOOK_LIABILITY_ISSUED",
                    1326,
                    page,
                    [(98, "Phát hành giấy tờ có giá")],
                    (100, "107.120.653"),
                ),
                _book(
                    base,
                    "BOOK_LIABILITY_OTHER",
                    1328,
                    page,
                    [(102, "Các khoản nợ khác")],
                    (105, "38.541.967"),
                ),
                base._mapping("FAIR_BRANCH", 1329, [(page, 19, "Giá trị"), (page, 26, "hợp lý")]),
                _fair(
                    base,
                    "FAIR_ASSET_CASH",
                    1331,
                    page,
                    [(34, "Tiền mặt, vàng bạc, đá quý")],
                    (37, "2.774.182"),
                ),
            ],
            "owner": [
                base._ref(page, 5, "TÀI SẢN TÀI CHÍNH VÀ NỢ PHẢI TRẢ TÀI CHÍNH"),
                base._ref(page, 6, "Bảng sau trình bày giá trị ghi sổ và giá trị hợp lý"),
            ],
            "page_span": [page, page],
            "source_only_rows": [
                base._open_fair_group(
                    "FI-001",
                    page,
                    [
                        (110, "(*) Ngân hàng chưa xác định giá trị của khoản mục này"),
                        (111, "chưa có hướng dẫn về xác định giá trị hợp lý"),
                    ],
                    [
                        "Tiền gửi tại Ngân hàng Nhà nước Việt Nam",
                        "Tiền gửi và cấp tín dụng cho các Tổ chức tín dụng khác - gộp",
                        "Chứng khoán kinh doanh - gộp",
                        "Cho vay khách hàng và mua nợ - gộp",
                        "Chứng khoán đầu tư sẵn sàng để bán - gộp",
                        "Góp vốn, đầu tư dài hạn - gộp",
                        "Tài sản tài chính khác",
                        "Các khoản nợ Chính phủ và NHNN Việt Nam",
                        "Tiền gửi và vay các Tổ chức tài chính, Tổ chức tín dụng khác",
                        "Tiền gửi của khách hàng",
                        "Công cụ tài chính phái sinh và các khoản nợ tài chính khác",
                        "Vốn tài trợ, ủy thác đầu tư, cho vay TCTD chịu rủi ro",
                        "Phát hành giấy tờ có giá",
                        "Các khoản nợ khác",
                    ],
                ),
                base._source_control(
                    "FI-004",
                    page,
                    [(19, "Giá trị hợp lý")],
                    base._line(page, 37, "2.774.182"),
                    "ONLY_EXPLICIT_NUMERIC_FAIR_VALUE_IS_CASH;NO_PRINTED_FAIR_TOTAL",
                ),
            ],
            "source_period": "2025-12-31",
            "unit_evidence": [
                base._ref(page, 27, "Triệu đồng"),
                base._ref(page, 33, "Triệu đồng"),
            ],
        }
    )

    documents.append(
        _absence(
            "HDB",
            "The complete annual PDF contains credit-risk carrying values but no detailed table "
            "with both carrying and fair values.",
        )
    )

    owner_page = 73
    page = 74
    documents.append(
        {
            "absence_evidence": None,
            "bank_code": "VCB",
            "mappings": [
                base._mapping("FAMILY", 1305, [(owner_page, 9, "Thuyết minh công cụ tài chính")]),
                base._mapping("BOOK_BRANCH", 1306, [(page, 8, "Giá trị ghi sổ - gộp")]),
                _book(
                    base,
                    "BOOK_TOTAL_ASSETS",
                    1307,
                    page,
                    [(14, "Tổng giá trị"), (20, "ghi sổ")],
                    (78, "2.451.287.325"),
                    topology="UNLABELED_ASSET_TOTAL_ROW",
                ),
                _book(
                    base,
                    "BOOK_ASSET_CASH",
                    1308,
                    page,
                    [(32, "Tiền mặt, vàng bạc, đá quý")],
                    (34, "15.542.769"),
                ),
                _book(
                    base,
                    "BOOK_ASSET_CENTRAL_BANK",
                    1309,
                    page,
                    [(37, "Tiền gửi tại NHNN")],
                    (39, "37.445.504"),
                ),
                _book(
                    base,
                    "BOOK_ASSET_INTERBANK",
                    1310,
                    page,
                    [(42, "Tiền gửi và cho vay các TCTD khác")],
                    (44, "522.474.362"),
                ),
                _book(
                    base,
                    "BOOK_ASSET_TRADING",
                    1311,
                    page,
                    [(47, "Chứng khoán kinh doanh - gộp")],
                    (49, "11.900.000"),
                ),
                _book(
                    base,
                    "BOOK_ASSET_DERIVATIVE",
                    1312,
                    page,
                    [
                        (52, "Các công cụ tài chính phái sinh và"),
                        (53, "các tài sản tài chính khác"),
                    ],
                    (55, "374.918"),
                ),
                _book(
                    base,
                    "BOOK_ASSET_LOANS",
                    1313,
                    page,
                    [(58, "Cho vay khách hàng - gộp")],
                    (60, "1.673.525.675"),
                ),
                _book(
                    base,
                    "BOOK_ASSET_INVESTMENT",
                    1314,
                    page,
                    [(62, "Chứng khoán đầu tư - gộp")],
                    (65, "165.465.779"),
                ),
                _book(
                    base,
                    "BOOK_ASSET_LONG_TERM",
                    1315,
                    page,
                    [(67, "Góp vốn, đầu tư dài hạn - gộp")],
                    (69, "1.589.089"),
                ),
                _book(
                    base,
                    "BOOK_ASSET_OTHER",
                    1318,
                    page,
                    [(71, "Tài sản tài chính khác - gộp")],
                    (73, "22.969.229"),
                ),
                _book(
                    base,
                    "BOOK_TOTAL_LIABILITIES",
                    1319,
                    page,
                    [(79, "Nợ phải trả tài chính")],
                    (99, "2.203.819.926"),
                    topology="UNLABELED_LIABILITY_TOTAL_ROW",
                ),
                _book(
                    base,
                    "BOOK_LIABILITY_CENTRAL_AND_INTERBANK",
                    1320,
                    page,
                    [
                        (81, "Các khoản nợ Chính phủ và NHNN"),
                        (82, "và tiền gửi và vay các TCTD khác"),
                    ],
                    (84, "481.286.427"),
                ),
                _book(
                    base,
                    "BOOK_LIABILITY_CUSTOMER",
                    1323,
                    page,
                    [(87, "Tiền gửi của khách hàng")],
                    (89, "1.672.534.846"),
                ),
                _book(
                    base,
                    "BOOK_LIABILITY_ISSUED",
                    1326,
                    page,
                    [(91, "Phát hành giấy tờ có giá")],
                    (93, "27.101.221"),
                ),
                _book(
                    base,
                    "BOOK_LIABILITY_OTHER",
                    1328,
                    page,
                    [(95, "Các khoản nợ phải trả tài chính khác")],
                    (97, "22.897.432"),
                ),
                base._mapping(
                    "FAIR_BRANCH",
                    1329,
                    [
                        (owner_page, 15, "Thuyết minh về giá trị hợp lý"),
                        (page, 15, "Giá trị"),
                        (page, 21, "hợp lý"),
                    ],
                ),
                _fair(
                    base,
                    "FAIR_ASSET_CASH",
                    1331,
                    page,
                    [(32, "Tiền mặt, vàng bạc, đá quý")],
                    (35, "15.542.769"),
                ),
                _fair(
                    base,
                    "FAIR_ASSET_CENTRAL_BANK",
                    1332,
                    page,
                    [(37, "Tiền gửi tại NHNN")],
                    (40, "37.445.504"),
                ),
            ],
            "owner": [
                base._ref(owner_page, 9, "Thuyết minh công cụ tài chính"),
                base._ref(owner_page, 19, "Bảng sau trình bày giá trị ghi sổ và giá trị hợp lý"),
            ],
            "page_span": [owner_page, page],
            "source_only_rows": [
                base._open_fair_group(
                    "FI-002",
                    page,
                    [
                        (100, "(*) Do không đủ thông tin để sử dụng các kỹ thuật định giá"),
                        (101, "giá trị hợp lý không được ước tính một cách đáng tin cậy"),
                        (102, "không được thuyết minh"),
                    ],
                    [
                        "Tiền gửi và cho vay các TCTD khác",
                        "Chứng khoán kinh doanh - gộp",
                        "Các công cụ tài chính phái sinh và các tài sản tài chính khác",
                        "Cho vay khách hàng - gộp",
                        "Chứng khoán đầu tư - gộp",
                        "Góp vốn, đầu tư dài hạn - gộp",
                        "Tài sản tài chính khác - gộp",
                        "Các khoản nợ Chính phủ và NHNN và tiền gửi và vay các TCTD khác",
                        "Tiền gửi của khách hàng",
                        "Phát hành giấy tờ có giá",
                        "Các khoản nợ phải trả tài chính khác",
                    ],
                ),
                base._source_control(
                    "FI-005",
                    page,
                    [(62, "Chứng khoán đầu tư - gộp")],
                    base._line(page, 63, "22.384.962"),
                    "HELD_TO_MATURITY_COMPONENT_OF_INVESTMENT_SECURITIES",
                ),
                base._source_control(
                    "FI-006",
                    page,
                    [(62, "Chứng khoán đầu tư - gộp")],
                    base._line(page, 64, "143.080.817"),
                    "AVAILABLE_FOR_SALE_COMPONENT_OF_INVESTMENT_SECURITIES",
                ),
            ],
            "source_period": "2025-12-31",
            "unit_evidence": [
                base._ref(page, 23, "Triệu VND"),
                base._ref(page, 29, "Triệu VND"),
            ],
        }
    )

    documents.extend(
        [
            _absence(
                "CTG",
                "The complete annual PDF contains currency-risk carrying-value tables but no "
                "detailed table with both carrying and fair values.",
            ),
            _absence(
                "BID",
                "The complete annual PDF contains derivative carrying-value tables but no "
                "detailed table with both carrying and fair values.",
            ),
            _absence(
                "VIB",
                "The complete annual PDF contains credit-risk carrying-value narratives but no "
                "detailed table with both carrying and fair values.",
            ),
        ]
    )
    expected = ["ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB"]
    if [item["bank_code"] for item in documents] != expected:
        raise _error("annual financial-instruments document order drifted")
    return documents


def _base() -> ModuleType:
    base = _load_base()
    base.FORMAT_VERSION = FORMAT_VERSION
    base.REVIEW_FORMAT = REVIEW_FORMAT
    base.RESULT_STATE = RESULT_STATE
    base.RESULT_ID_PREFIX = RESULT_ID_PREFIX
    base.REVIEW_STATE = REVIEW_STATE
    base.REVIEW_ID_PREFIX = REVIEW_ID_PREFIX
    base.FAMILY_END_DISPLAY_ORDER = 1030
    base.SOURCE_PERIOD_STATUS_BY_PERIOD = {
        "2025-12-31": (
            "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
        )
    }
    base.VPB_KNOWN_FAIR_VALUE_EQUATION_NAME = (
        "ONLY_EXPLICIT_NUMERIC_FAIR_VALUE_EQUALS_CASH_FAIR_VALUE"
    )
    base.CLAIM_BOUNDARY = CLAIM_BOUNDARY
    base.REVIEW_PATH = REVIEW_PATH
    base.RESULT_PATH = RESULT_PATH
    base.SEMANTIC_INDEX_PATH = SEMANTIC_INDEX_PATH
    base.CROP_MANIFEST_PATH = CROP_MANIFEST_PATH
    base.EXPECTED_INDEX_SHA256 = EXPECTED_INDEX_SHA256
    base.EXPECTED_CROP_MANIFEST_SHA256 = EXPECTED_CROP_MANIFEST_SHA256
    base.EXPECTED_AXIS_SHA256 = EXPECTED_AXIS_SHA256
    base.EXPECTED_SCAN_ID = EXPECTED_SCAN_ID
    base.ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT = False
    base._SCHEMA_EXPECTED = dict(_SCHEMA_EXPECTED)
    base._AUTHORITY = canonical_clone_v1(_AUTHORITY)
    base._review_documents = lambda: _review_documents(base)
    return base


def build_annual_2025_financial_instruments_pixel_review_blueprint_v1() -> dict[str, Any]:
    return _base()._review_blueprint()


def _check_expected_result(value: Mapping[str, Any]) -> None:
    if EXPECTED_RESULT_ID is not None and value.get("result_id") != EXPECTED_RESULT_ID:
        raise _error("annual financial-instruments expected result ID drifted")


def build_live_annual_2025_financial_instruments_8bank_codex_verified_mapping_v1() -> dict[
    str, Any
]:
    try:
        value = _base().build_live_financial_instruments_8bank_codex_verified_mapping_v1()
        _check_expected_result(value)
        return value
    except Annual2025FinancialInstruments8BankError:
        raise
    except Exception as exc:
        raise _error(str(exc)) from exc


def validate_annual_2025_financial_instruments_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    try:
        checked = _base().validate_live_financial_instruments_8bank_codex_verified_mapping_v1(value)
        _check_expected_result(checked)
        return checked
    except Annual2025FinancialInstruments8BankError:
        raise
    except Exception as exc:
        raise _error(str(exc)) from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--write-result", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if sum((args.write_review, args.write_result, args.verify)) != 1:
        parser.error("choose exactly one action")
    if args.write_review:
        REVIEW_PATH.write_bytes(
            canonical_json_bytes_v1(
                build_annual_2025_financial_instruments_pixel_review_blueprint_v1()
            )
        )
        return 0
    if args.write_result:
        RESULT_PATH.write_bytes(
            canonical_json_bytes_v1(
                build_live_annual_2025_financial_instruments_8bank_codex_verified_mapping_v1()
            )
        )
        return 0
    value, _ = _base()._stable_json(RESULT_PATH)
    validate_annual_2025_financial_instruments_8bank_codex_verified_mapping_replay_v1(value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
