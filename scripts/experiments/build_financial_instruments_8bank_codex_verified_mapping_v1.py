"""Verify financial-instrument carrying and fair values across eight reports."""

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
        raise RuntimeError(f"cannot load financial-instruments support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


other = _load(
    "other_activity_support_for_financial_instruments",
    "build_other_activity_8bank_codex_verified_mapping_v1.py",
)
scanner = _load(
    "financial_instruments_scan_for_verified_mapping",
    "scan_financial_instruments_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "FINANCIAL_INSTRUMENTS_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "FINANCIAL_INSTRUMENTS_8BANK_CODEX_PIXEL_REVIEW_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_BANK_BLIND_FINANCIAL_"
    "INSTRUMENTS_BOOK_FAIR_GRAPH_VISIBLE_PDF_SOURCE_NUMERIC_CHALLENGER_"
    "EXACT_ACCOUNTING_CLOSURE_LIVE_TM_SCHEMA_ONLY_NO_EXPORT_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0099-financial-instruments-8bank-codex-pixel-review-v1.json")
RESULT_PATH = Path(
    "docs/experiments/E-0099-financial-instruments-8bank-codex-verified-mapping-v1.json"
)
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = other.CROP_MANIFEST_PATH
EXPECTED_INDEX_SHA256 = other.EXPECTED_INDEX_SHA256
EXPECTED_CROP_MANIFEST_SHA256 = other.EXPECTED_CROP_MANIFEST_SHA256
EXPECTED_AXIS_SHA256 = other.EXPECTED_AXIS_SHA256
EXPECTED_SCAN_ID = "fifdsv1:scan:284c3afb8824fc30720b040a77436f80341967b486a781ad95ffdbdd34d956c6"

_SCHEMA_EXPECTED = {
    1259: ("IV. MỘT SỐ THÔNG TIN KHÁC", None, 835),
    1305: ("Công cụ tài chính", 1259, 980),
    1306: ("Giá trị ghi sổ - Công cụ tài chính", 1305, 981),
    1307: ("Tổng tài sản tài chính", 1306, 982),
    1308: ("Tiền mặt, vàng bạc đá quý", 1306, 983),
    1309: ("Tiền gửi tại NHNN", 1306, 984),
    1310: ("Tiền gửi và cho vay các TCTD khác", 1306, 985),
    1311: ("Chứng khoán kinh doanh", 1306, 986),
    1312: ("Công cụ tài chính phái sinh và các tài sản tài chính khác", 1306, 987),
    1313: ("Cho vay khách hàng", 1306, 988),
    1314: ("Chứng khoán đầu tư", 1306, 989),
    1315: ("Đầu tư dài hạn khác", 1306, 990),
    1316: ("Các khoản phải thu", 1306, 991),
    1317: ("Các khoản lãi, phí phải thu", 1306, 992),
    1318: ("Tài sản Có khác", 1306, 993),
    1319: ("Công nợ tài chính", 1306, 994),
    1320: ("Tiền gửi và vay từ NHNN và các TCTD khác", 1306, 995),
    1321: ("Các khoản nợ chính phủ và NHNN", 1306, 996),
    1322: ("Tiền gửi và vay các TCTD khác", 1306, 997),
    1323: ("Tiền gửi của khách hàng", 1306, 998),
    1324: ("Công cụ tài chính phái sinh và các khoản nợ tài chính khác", 1306, 999),
    1325: ("Vốn tài trợ, ủy thác đầu tư, cho vay TCTD chịu rủi ro", 1306, 1000),
    1326: ("Phát hành giấy tờ có giá", 1306, 1001),
    1327: ("Các khoản lãi, phí phải trả", 1306, 1002),
    1328: ("Các khoản phải trả và công nợ khác", 1306, 1003),
    1329: ("Giá trị hợp lý - Công cụ tài chính", 1305, 1004),
    1330: ("Tổng tài sản tài chính", 1329, 1005),
    1331: ("Tiền mặt, vàng bạc đá quý", 1329, 1006),
    1332: ("Tiền gửi tại NHNN", 1329, 1007),
    1333: ("Tiền gửi và cho vay các TCTD khác", 1329, 1008),
    1334: ("Chứng khoán kinh doanh", 1329, 1009),
    1335: ("Công cụ tài chính phái sinh và các tài sản tài chính khác", 1329, 1010),
    1336: ("Cho vay khách hàng", 1329, 1011),
    1337: ("Chứng khoán đầu tư", 1329, 1012),
    1338: ("Đầu tư dài hạn khác", 1329, 1013),
    1339: ("Các khoản phải thu", 1329, 1014),
    1340: ("Các khoản lãi, phí phải thu", 1329, 1015),
    1341: ("Tài sản Có khác", 1329, 1016),
    1342: ("Công nợ tài chính", 1329, 1017),
    1343: ("Tiền gửi và vay từ NHNN và các TCTD khác", 1329, 1018),
    1344: ("Các khoản nợ chính phủ và NHNN", 1329, 1019),
    1345: ("Tiền gửi và vay các TCTD khác", 1329, 1020),
    1346: ("Tiền gửi của khách hàng", 1329, 1021),
    1347: ("Công cụ tài chính phái sinh và các khoản nợ tài chính khác", 1329, 1022),
    1348: ("Vốn tài trợ, ủy thác đầu tư, cho vay TCTD chịu rủi ro", 1329, 1023),
    1349: ("Phát hành giấy tờ có giá", 1329, 1024),
    1350: ("Các khoản lãi, phí phải trả", 1329, 1025),
    1351: ("Các khoản phải trả và công nợ khác", 1329, 1026),
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "detailed_table_absence_is_not_source_wide_financial_instrument_absence": True,
    "fair_value_asterisk_interpreted_as_zero": False,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_book_and_numeric_fair_value_cells": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_classification_columns_used_as_schema_selector": False,
    "text_similarity_alone_used_for_mapping": False,
    "unavailable_fair_value_rows_discarded": False,
    "visible_book_value_dash_may_equal_zero_only_with_pixel_binding": True,
}
_FIELDS = {
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


class FinancialInstruments8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixels, values, axes, schema or result drifted."""


def _error(message: str) -> FinancialInstruments8BankCodexVerifiedMappingV1Error:
    return FinancialInstruments8BankCodexVerifiedMappingV1Error(message)


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


def _dash(page: int, bbox: Sequence[int], rgb_sha256: str) -> dict[str, Any]:
    return {
        "bbox_raw_pixels": list(bbox),
        "kind": "AUTHENTICATED_RENDER_PIXEL_DASH",
        "page_sequence": page,
        "pixel_rgb_sha256": rgb_sha256,
        "pixel_transcription": "-",
    }


def _mapping(
    role: str,
    report_norm_id: int,
    labels: Sequence[tuple[int, int, str]],
    value: Mapping[str, Any] | None = None,
    *,
    axis_role: str | None = None,
    topology: str = "ROW_TO_SINGLE_SCHEMA_VALUE",
) -> dict[str, Any]:
    if (value is None) != (axis_role is None):
        raise _error("mapping value and axis role must be supplied together")
    return {
        "labels": [_ref(page, line, text) for page, line, text in labels],
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": topology,
        "values": [] if value is None else [{"axis_role": axis_role, **canonical_clone_v1(value)}],
    }


def _open_fair_group(
    row_id: str,
    page: int,
    footnote: Sequence[tuple[int, str]],
    affected_source_labels: Sequence[str],
) -> dict[str, Any]:
    return {
        "affected_source_labels": list(affected_source_labels),
        "labels": [_ref(page, line, text) for line, text in footnote],
        "open_mapping": True,
        "reason": "SOURCE_EXPLICITLY_MARKS_FAIR_VALUE_UNAVAILABLE;_ASTERISK_IS_NOT_ZERO",
        "row_id": row_id,
        "values": [],
    }


def _source_control(
    row_id: str,
    page: int,
    labels: Sequence[tuple[int, str]],
    value: Mapping[str, Any],
    reason: str,
) -> dict[str, Any]:
    return {
        "affected_source_labels": [],
        "labels": [_ref(page, line, text) for line, text in labels],
        "open_mapping": False,
        "reason": reason,
        "row_id": row_id,
        "values": [{"axis_role": "SOURCE_CONTROL", **canonical_clone_v1(value)}],
    }


def _absence(code: str) -> dict[str, Any]:
    return {
        "absence_evidence": {
            "complete_pdf_pages_scanned": True,
            "detailed_table_complete_region_count": 0,
            "reason": (
                "No detailed financial-instrument table with a bound family owner, both carrying-value "
                "and fair-value headers, unit, and deep financial-asset/liability rows was found in the "
                "bound report; policy, currency, interest-rate and liquidity-risk tables do not qualify."
            ),
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


def _book(
    role: str,
    report_norm_id: int,
    page: int,
    label: tuple[int, str],
    value: Mapping[str, Any],
    *,
    topology: str = "BOOK_TOTAL_ROW",
) -> dict[str, Any]:
    return _mapping(
        role,
        report_norm_id,
        [(page, label[0], label[1])],
        value,
        axis_role="CARRYING_VALUE",
        topology=topology,
    )


def _fair(
    role: str,
    report_norm_id: int,
    page: int,
    label: tuple[int, str],
    value: Mapping[str, Any],
) -> dict[str, Any]:
    return _mapping(
        role,
        report_norm_id,
        [(page, label[0], label[1])],
        value,
        axis_role="FAIR_VALUE",
        topology="NUMERIC_FAIR_VALUE_EXPLICITLY_PRINTED",
    )


def _review_documents() -> list[dict[str, Any]]:
    documents = [_absence("ACB"), _absence("MBB")]
    page = 86
    documents.append(
        {
            "absence_evidence": None,
            "bank_code": "VPB",
            "mappings": [
                _mapping("FAMILY", 1305, [(page, 5, "TÀI SẢN TÀI CHÍNH VÀ NỢ PHẢI TRẢ TÀI CHÍNH")]),
                _mapping("BOOK_BRANCH", 1306, [(page, 7, "Giá trị ghi sổ")]),
                _book(
                    "BOOK_TOTAL_ASSETS",
                    1307,
                    page,
                    (19, "Tổng cộng giá trị ghi sổ"),
                    _line(page, 76, "1.374.815.071"),
                    topology="UNLABELED_ASSET_TOTAL_ROW",
                ),
                _book(
                    "BOOK_ASSET_CASH",
                    1308,
                    page,
                    (35, "Tiền mặt, vàng bạc, đá quý"),
                    _line(page, 37, "4.065.152"),
                ),
                _book(
                    "BOOK_ASSET_CENTRAL_BANK",
                    1309,
                    page,
                    (39, "Tiền gửi tại NHNN Việt Nam"),
                    _line(page, 41, "14.817.329"),
                ),
                _book(
                    "BOOK_ASSET_INTERBANK",
                    1310,
                    page,
                    (43, "Tiền gửi và cấp tín dụng cho các TCTD khác"),
                    _line(page, 46, "195.016.578"),
                ),
                _book(
                    "BOOK_ASSET_TRADING",
                    1311,
                    page,
                    (48, "Chứng khoán kinh doanh (gộp)"),
                    _line(page, 50, "25.406.906"),
                ),
                _book(
                    "BOOK_ASSET_LOANS",
                    1313,
                    page,
                    (52, "Cho vay khách hàng và mua nợ (gộp)"),
                    _line(page, 54, "1.041.835.920"),
                ),
                _book(
                    "BOOK_ASSET_INVESTMENT",
                    1314,
                    page,
                    (56, "Chứng khoán đầu tư sẵn sàng để bán (gộp)"),
                    _line(page, 58, "65.860.200"),
                ),
                _book(
                    "BOOK_ASSET_LONG_TERM",
                    1315,
                    page,
                    (60, "Góp vốn, đầu tư dài hạn (gộp)"),
                    _line(page, 62, "191.960"),
                ),
                _book(
                    "BOOK_ASSET_OTHER",
                    1318,
                    page,
                    (64, "Tài sản tài chính khác"),
                    _line(page, 69, "27.621.026"),
                ),
                _book(
                    "BOOK_TOTAL_LIABILITIES",
                    1319,
                    page,
                    (26, "Tổng cộng giá trị ghi sổ"),
                    _line(page, 114, "1.179.332.205"),
                    topology="UNLABELED_LIABILITY_TOTAL_ROW",
                ),
                _book(
                    "BOOK_LIABILITY_GOVERNMENT",
                    1321,
                    page,
                    (78, "Các khoản nợ Chính phủ, NHNN Việt Nam"),
                    _line(page, 80, "1.063.456"),
                ),
                _book(
                    "BOOK_LIABILITY_INTERBANK",
                    1322,
                    page,
                    (82, "Tiền gửi và vay các TCTC, TCTD khác"),
                    _line(page, 84, "311.527.853"),
                ),
                _book(
                    "BOOK_LIABILITY_CUSTOMER",
                    1323,
                    page,
                    (86, "Tiền gửi của khách hàng"),
                    _line(page, 88, "682.719.373"),
                ),
                _book(
                    "BOOK_LIABILITY_DERIVATIVE",
                    1324,
                    page,
                    (90, "Công cụ tài chính phái sinh và các khoản nợ tài chính khác"),
                    _line(page, 93, "1.025.252"),
                ),
                _book(
                    "BOOK_LIABILITY_ENTRUSTED",
                    1325,
                    page,
                    (95, "Vốn tài trợ, ủy thác đầu tư, cho vay TCTD chịu rủi ro"),
                    _line(page, 98, "38.296"),
                ),
                _book(
                    "BOOK_LIABILITY_ISSUED",
                    1326,
                    page,
                    (100, "Phát hành giấy tờ có giá"),
                    _line(page, 102, "138.840.016"),
                ),
                _book(
                    "BOOK_LIABILITY_OTHER",
                    1328,
                    page,
                    (104, "Các khoản nợ khác"),
                    _line(page, 107, "44.117.959"),
                ),
                _mapping("FAIR_BRANCH", 1329, [(page, 20, "Giá trị hợp lý")]),
                _fair(
                    "FAIR_ASSET_CASH",
                    1331,
                    page,
                    (35, "Tiền mặt, vàng bạc, đá quý"),
                    _line(page, 38, "4.065.152"),
                ),
            ],
            "owner": [_ref(page, 5, "TÀI SẢN TÀI CHÍNH VÀ NỢ PHẢI TRẢ TÀI CHÍNH")],
            "page_span": [86, 86],
            "source_only_rows": [
                _open_fair_group(
                    "FI-001",
                    page,
                    [
                        (
                            116,
                            "(*) Giá trị hợp lý của các tài sản tài chính này không thể xác định được",
                        ),
                        (117, "giá trị hợp lý của các công cụ tài chính"),
                    ],
                    [
                        "Tiền gửi tại NHNN Việt Nam",
                        "Tiền gửi và cấp tín dụng cho các TCTD khác",
                        "Chứng khoán kinh doanh (gộp)",
                        "Cho vay khách hàng và mua nợ (gộp)",
                        "Chứng khoán đầu tư sẵn sàng để bán (gộp)",
                        "Góp vốn, đầu tư dài hạn (gộp)",
                        "Tài sản tài chính khác",
                        "Các khoản nợ Chính phủ, NHNN Việt Nam",
                        "Tiền gửi và vay các TCTC, TCTD khác",
                        "Tiền gửi của khách hàng",
                        "Công cụ tài chính phái sinh và các khoản nợ tài chính khác",
                        "Vốn tài trợ, ủy thác đầu tư, cho vay TCTD chịu rủi ro",
                        "Phát hành giấy tờ có giá",
                        "Các khoản nợ khác",
                    ],
                ),
                _source_control(
                    "FI-004",
                    page,
                    [(20, "Giá trị hợp lý")],
                    _line(page, 77, "4.065.152"),
                    "PRINTED_KNOWN_FAIR_VALUE_SUBTOTAL_IS_NOT_COMPLETE_SCHEMA_TOTAL",
                ),
            ],
            "source_period": "2026-03-31",
            "unit_evidence": [_ref(page, 33, "Triệu đồng"), _ref(page, 34, "Triệu đồng")],
        }
    )
    documents.append(_absence("HDB"))
    page = 45
    documents.append(
        {
            "absence_evidence": None,
            "bank_code": "VCB",
            "mappings": [
                _mapping("FAMILY", 1305, [(44, 8, "24. Thuyết minh công cụ tài chính")]),
                _mapping("BOOK_BRANCH", 1306, [(page, 7, "Giá trị ghi sổ - gộp")]),
                _book(
                    "BOOK_TOTAL_ASSETS",
                    1307,
                    page,
                    (14, "Tổng cộng giá trị ghi sổ (gộp)"),
                    _line(page, 75, "2.664.790.415"),
                    topology="UNLABELED_ASSET_TOTAL_ROW",
                ),
                _book(
                    "BOOK_ASSET_CASH",
                    1308,
                    page,
                    (31, "Tiền mặt, vàng bạc, đá quý"),
                    _line(page, 33, "14.602.141"),
                ),
                _book(
                    "BOOK_ASSET_CENTRAL_BANK",
                    1309,
                    page,
                    (36, "Tiền gửi tại NHNN"),
                    _line(page, 38, "73.064.279"),
                ),
                _book(
                    "BOOK_ASSET_INTERBANK",
                    1310,
                    page,
                    (41, "Tiền gửi tại và cho vay các tổ chức tín dụng khác"),
                    _line(page, 43, "620.660.924"),
                ),
                _book(
                    "BOOK_ASSET_TRADING",
                    1311,
                    page,
                    (47, "Chứng khoán kinh doanh - gộp"),
                    _line(page, 49, "20.257.419"),
                ),
                _book(
                    "BOOK_ASSET_DERIVATIVE",
                    1312,
                    page,
                    (51, "Các công cụ tài chính phái sinh và các khoản nợ tài chính"),
                    _line(page, 53, "811.319"),
                ),
                _book(
                    "BOOK_ASSET_LOANS",
                    1313,
                    page,
                    (55, "Cho vay khách hàng - gộp"),
                    _line(page, 57, "1.758.168.065"),
                ),
                _book(
                    "BOOK_ASSET_INVESTMENT",
                    1314,
                    page,
                    (59, "Chứng khoán đầu tư - gộp"),
                    _line(page, 62, "155.756.799"),
                ),
                _book(
                    "BOOK_ASSET_LONG_TERM",
                    1315,
                    page,
                    (65, "Góp vốn, đầu tư dài hạn - gộp"),
                    _line(page, 67, "1.589.089"),
                ),
                _book(
                    "BOOK_ASSET_OTHER",
                    1318,
                    page,
                    (69, "Tài sản tài chính khác - gộp"),
                    _line(page, 71, "19.880.380"),
                ),
                _book(
                    "BOOK_TOTAL_LIABILITIES",
                    1319,
                    page,
                    (77, "Nợ phải trả tài chính"),
                    _line(page, 105, "2.394.314.531"),
                    topology="UNLABELED_LIABILITY_TOTAL_ROW",
                ),
                _book(
                    "BOOK_LIABILITY_CENTRAL_AND_INTERBANK",
                    1320,
                    page,
                    (78, "Tiền gửi của và vay từ NHNN và các tổ chức tín dụng khác"),
                    _line(page, 80, "597.746.951"),
                ),
                _book(
                    "BOOK_LIABILITY_CUSTOMER",
                    1323,
                    page,
                    (84, "Tiền gửi của khách hàng"),
                    _line(page, 86, "1.728.820.567"),
                ),
                _book(
                    "BOOK_LIABILITY_ENTRUSTED",
                    1325,
                    page,
                    (89, "Vốn tài trợ, ủy thác đầu tư, cho vay tổ chức tín dụng chịu rủi ro"),
                    _line(page, 91, "5"),
                ),
                _book(
                    "BOOK_LIABILITY_ISSUED",
                    1326,
                    page,
                    (92, "Phát hành giấy tờ có giá"),
                    _line(page, 94, "39.345.465"),
                ),
                _book(
                    "BOOK_LIABILITY_OTHER",
                    1328,
                    page,
                    (98, "Các khoản nợ phải trả tài chính khác"),
                    _line(page, 100, "28.401.543"),
                ),
                _mapping(
                    "FAIR_BRANCH",
                    1329,
                    [(44, 12, "(b) Thuyết minh về giá trị hợp lý"), (page, 15, "Giá trị hợp lý")],
                ),
                _fair(
                    "FAIR_ASSET_CASH",
                    1331,
                    page,
                    (31, "Tiền mặt, vàng bạc, đá quý"),
                    _line(page, 34, "14.602.141"),
                ),
                _fair(
                    "FAIR_ASSET_CENTRAL_BANK",
                    1332,
                    page,
                    (36, "Tiền gửi tại NHNN"),
                    _line(page, 39, "73.064.279"),
                ),
            ],
            "owner": [
                _ref(44, 8, "24. Thuyết minh công cụ tài chính"),
                _ref(44, 15, "Bảng sau trình bày giá trị ghi sổ và giá trị hợp lý"),
            ],
            "page_span": [44, 45],
            "source_only_rows": [
                _open_fair_group(
                    "FI-002",
                    page,
                    [
                        (108, "(*) Do không đủ thông tin để sử dụng các kỹ thuật định giá"),
                        (109, "đáng tin cậy và do đó, không được thuyết minh"),
                    ],
                    [
                        "Tiền gửi tại và cho vay các tổ chức tín dụng khác",
                        "Chứng khoán kinh doanh - gộp",
                        "Các công cụ tài chính phái sinh và các khoản nợ tài chính",
                        "Cho vay khách hàng - gộp",
                        "Chứng khoán đầu tư - gộp",
                        "Góp vốn, đầu tư dài hạn - gộp",
                        "Tài sản tài chính khác - gộp",
                        "Tiền gửi của và vay từ NHNN và các tổ chức tín dụng khác",
                        "Tiền gửi của khách hàng",
                        "Vốn tài trợ, ủy thác đầu tư, cho vay tổ chức tín dụng chịu rủi ro",
                        "Phát hành giấy tờ có giá",
                        "Các khoản nợ phải trả tài chính khác",
                    ],
                ),
                _source_control(
                    "FI-005",
                    page,
                    [(59, "Chứng khoán đầu tư - gộp")],
                    _line(page, 60, "26.151.991"),
                    "HELD_TO_MATURITY_COMPONENT_OF_INVESTMENT_SECURITIES",
                ),
                _source_control(
                    "FI-006",
                    page,
                    [(59, "Chứng khoán đầu tư - gộp")],
                    _line(page, 61, "129.604.808"),
                    "AVAILABLE_FOR_SALE_COMPONENT_OF_INVESTMENT_SECURITIES",
                ),
            ],
            "source_period": "2026-06-30",
            "unit_evidence": [_ref(page, 27, "Triệu VND"), _ref(page, 28, "Triệu VND")],
        }
    )
    page = 51
    documents.append(
        {
            "absence_evidence": None,
            "bank_code": "CTG",
            "mappings": [
                _mapping(
                    "FAMILY", 1305, [(page, 4, "Phân loại tài sản tài chính và công nợ tài chính")]
                ),
                _mapping("BOOK_BRANCH", 1306, [(page, 6, "Giá trị ghi sổ")]),
                _book(
                    "BOOK_TOTAL_ASSETS",
                    1307,
                    page,
                    (14, "Tổng cộng giá trị ghi sổ"),
                    _line(page, 74, "2.980.922.753"),
                    topology="UNLABELED_ASSET_TOTAL_ROW",
                ),
                _book(
                    "BOOK_ASSET_CASH",
                    1308,
                    page,
                    (31, "Tiền mặt, vàng bạc, đá quý"),
                    _line(page, 33, "12.998.380"),
                ),
                _book(
                    "BOOK_ASSET_CENTRAL_BANK",
                    1309,
                    page,
                    (37, "Tiền gửi tại NHNN"),
                    _line(page, 35, "18.553.436"),
                ),
                _book(
                    "BOOK_ASSET_INTERBANK",
                    1310,
                    page,
                    (39, "Tiền gửi tại và cho vay các TCTD khác"),
                    _line(page, 40, "553.189.148"),
                ),
                _book(
                    "BOOK_ASSET_TRADING",
                    1311,
                    page,
                    (45, "Chứng khoán kinh doanh"),
                    _line(page, 43, "4.182.206"),
                ),
                _book(
                    "BOOK_ASSET_DERIVATIVE",
                    1312,
                    page,
                    (47, "Các công cụ tài chính phái sinh và các tài sản tài chính"),
                    _dash(
                        page,
                        [2958, 1238, 2985, 1258],
                        "18b6b8081196d713c1f4e836ea882ebfc8836f7cf95d9a5f6e99b3b38104d852",
                    ),
                ),
                _book(
                    "BOOK_ASSET_LOANS",
                    1313,
                    page,
                    (53, "Cho vay khách hàng"),
                    _line(page, 51, "2.092.707.758"),
                ),
                _book(
                    "BOOK_ASSET_INVESTMENT",
                    1314,
                    page,
                    (57, "Chứng khoán sẵn sàng để bán"),
                    _sum(page, [(55, "176.831.104"), (58, "50.825.806")]),
                    topology="CONTROLLED_SUM_OF_AFS_AND_HTM_ROWS",
                ),
                _book(
                    "BOOK_ASSET_LONG_TERM",
                    1315,
                    page,
                    (62, "Đầu tư dài hạn khác"),
                    _line(page, 64, "234.462"),
                ),
                _book(
                    "BOOK_ASSET_OTHER",
                    1318,
                    page,
                    (68, "Tài sản tài chính khác"),
                    _line(page, 66, "71.400.453"),
                ),
                _book(
                    "BOOK_TOTAL_LIABILITIES",
                    1319,
                    page,
                    (14, "Tổng cộng giá trị ghi sổ"),
                    _line(page, 107, "2.756.023.081"),
                    topology="UNLABELED_LIABILITY_TOTAL_ROW",
                ),
                _book(
                    "BOOK_LIABILITY_GOVERNMENT",
                    1321,
                    page,
                    (78, "Các khoản nợ Chính phủ và NHNN"),
                    _line(page, 76, "194.570.607"),
                ),
                _book(
                    "BOOK_LIABILITY_INTERBANK",
                    1322,
                    page,
                    (79, "Tiền gửi và vay các TCTD khác"),
                    _line(page, 81, "472.518.030"),
                ),
                _book(
                    "BOOK_LIABILITY_CUSTOMER",
                    1323,
                    page,
                    (83, "Tiền gửi của khách hàng"),
                    _line(page, 85, "1.890.809.553"),
                ),
                _book(
                    "BOOK_LIABILITY_DERIVATIVE",
                    1324,
                    page,
                    (87, "Các công cụ tài chính phái sinh và các tài sản tài chính"),
                    _line(page, 88, "88.817"),
                ),
                _book(
                    "BOOK_LIABILITY_ENTRUSTED",
                    1325,
                    page,
                    (92, "Vốn tài trợ, ủy thác đầu tư, cho vay tổ chức tín dụng chịu rủi ro"),
                    _line(page, 94, "2.054.621"),
                ),
                _book(
                    "BOOK_LIABILITY_ISSUED",
                    1326,
                    page,
                    (100, "Phát hành giấy tờ có giá"),
                    _line(page, 98, "142.990.024"),
                ),
                _book(
                    "BOOK_LIABILITY_OTHER",
                    1328,
                    page,
                    (103, "Các khoản nợ tài chính khác"),
                    _line(page, 101, "52.991.429"),
                ),
                _mapping("FAIR_BRANCH", 1329, [(page, 15, "Giá trị hợp lý")]),
                _fair(
                    "FAIR_ASSET_CASH",
                    1331,
                    page,
                    (31, "Tiền mặt, vàng bạc, đá quý"),
                    _line(page, 34, "12.998.380"),
                ),
            ],
            "owner": [_ref(page, 4, "Phân loại tài sản tài chính và công nợ tài chính")],
            "page_span": [51, 51],
            "source_only_rows": [
                _open_fair_group(
                    "FI-003",
                    page,
                    [
                        (108, "(*) Ngân hàng chưa đánh giá giá trị hợp lý"),
                        (109, "chưa có hướng dẫn cụ thể về việc xác định giá trị hợp lý"),
                    ],
                    [
                        "Tiền gửi tại NHNN",
                        "Tiền gửi tại và cho vay các TCTD khác",
                        "Chứng khoán kinh doanh",
                        "Các công cụ tài chính phái sinh và các tài sản tài chính",
                        "Cho vay khách hàng",
                        "Chứng khoán sẵn sàng để bán",
                        "Chứng khoán giữ đến ngày đáo hạn",
                        "Đầu tư dài hạn khác",
                        "Tài sản tài chính khác",
                        "Các khoản nợ Chính phủ và NHNN",
                        "Tiền gửi và vay các TCTD khác",
                        "Tiền gửi của khách hàng",
                        "Các công cụ tài chính phái sinh và các tài sản tài chính",
                        "Vốn tài trợ, ủy thác đầu tư, cho vay tổ chức tín dụng chịu rủi ro",
                        "Phát hành giấy tờ có giá",
                        "Các khoản nợ tài chính khác",
                    ],
                )
            ],
            "source_period": "2026-06-30",
            "unit_evidence": [_ref(page, 5, "Đơn vị: triệu đồng"), _ref(page, 30, "triệu đồng")],
        }
    )
    documents.extend([_absence("BID"), _absence("VIB")])
    return documents


def _review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_documents(),
        "format_version": REVIEW_FORMAT,
        "state": "FINANCIAL_INSTRUMENTS_PIXEL_REVIEW_COMPLETE",
    }
    return {**material, "review_id": "e0099:pixel-review:" + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("financial-instruments pixel review drifted")
    return canonical_clone_v1(value)


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(t["verified_accounting_equations"]) for t in trials
        ),
        "authenticated_pixel_dash_zero_count": sum(
            value.get("source_numeric_challenger_status")
            == "VISIBLE_AUTHENTICATED_PIXEL_DASH_NOT_DETECTED_AS_SOURCE_LINE"
            for trial in trials
            for mapping in trial["verified_mappings"]
            for value in mapping["values"]
        ),
        "bound_report_detailed_table_absence_count": sum(
            t["status"] == "CONFIRMED_DETAILED_TABLE_NOT_PRESENT_IN_BOUND_REPORT" for t in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(t["page_span"] is not None for t in trials),
        "mapping_verified_count": sum(len(t["verified_mappings"]) for t in trials),
        "open_fair_value_group_count": sum(
            sum(row["open_mapping"] for row in t["verified_source_only_rows"]) for t in trials
        ),
        "q1_source_period_caveat_document_count": sum(
            t["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2" for t in trials
        ),
        "source_only_control_row_count": sum(
            sum(not row["open_mapping"] for row in t["verified_source_only_rows"]) for t in trials
        ),
        "verified_value_cell_count": sum(
            len(mapping["values"]) for t in trials for mapping in t["verified_mappings"]
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("financial-instruments result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "FINANCIAL_INSTRUMENTS_8BANK_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("financial-instruments result identity drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "e0099:result:" + canonical_json_sha256_v1(material):
        raise _error("financial-instruments result ID drifted")
    return canonical_clone_v1(value)


def _value(row: Mapping[str, Any]) -> int:
    if len(row["values"]) != 1:
        raise _error("financial-instruments equation row is not single-valued")
    return row["values"][0]["normalized_value"]


def _equation(name: str, computed: int, visible: int) -> dict[str, Any]:
    if computed != visible:
        raise _error(f"financial-instruments accounting equation does not close: {name}")
    return {
        "computed_value": computed,
        "name": name,
        "status": "VERIFIED_EXACT",
        "visible_value": visible,
    }


def build_financial_instruments_8bank_codex_verified_mapping_v1(
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
    scanner.validate_financial_instruments_full_document_scan_replay_v1(
        structure_scan, semantic_index
    )
    if (
        axis["semantic_axis_sha256"] != EXPECTED_AXIS_SHA256
        or structure_scan["scan_id"] != EXPECTED_SCAN_ID
    ):
        raise _error("financial-instruments fixed inputs drifted")
    trials = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        reviewed = other._document(reviewed_documents, code, "pixel review")
        scan_trial = other._document(structure_scan["trials"], code, "structure scan")
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
                raise _error("absent detailed financial-instruments table unexpectedly matched")
            trials.append(
                {
                    **base,
                    "absence_evidence": canonical_clone_v1(reviewed["absence_evidence"]),
                    "mapped_report_norm_ids": [],
                    "owner_evidence": [],
                    "page_span": None,
                    "source_period": None,
                    "source_period_status": "NOT_APPLICABLE_DETAILED_TABLE_ABSENT",
                    "status": "CONFIRMED_DETAILED_TABLE_NOT_PRESENT_IN_BOUND_REPORT",
                    "unit_evidence": [],
                    "verified_accounting_equations": [],
                    "verified_mappings": [],
                    "verified_source_only_rows": [],
                }
            )
            continue
        if (
            matcher["uniqueness"] != {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
            or matcher["regions"][0]["page_span"] != reviewed["page_span"]
        ):
            raise _error("reviewed financial-instruments region is not unique")
        axis_document = other._document(axis["documents"], code, "accounting axis")
        semantic_document = other._document(semantic_index["documents"], code, "semantic index")
        crop_document = other._document(crop_manifest["documents"], code, "crop manifest")

        def verified_values(
            items: Sequence[Mapping[str, Any]],
            axis_document: Mapping[str, Any] = axis_document,
            semantic_document: Mapping[str, Any] = semantic_document,
            crop_document: Mapping[str, Any] = crop_document,
        ) -> list[dict[str, Any]]:
            return [
                {
                    "axis_role": item["axis_role"],
                    **other._verified_value(axis_document, semantic_document, crop_document, item),
                }
                for item in items
            ]

        mappings = [
            {
                "label_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, ref)
                    for ref in mapping["labels"]
                ],
                "role": mapping["role"],
                "schema_binding": _schema_binding(
                    schema_by_id.get(mapping["report_norm_id"]), mapping["report_norm_id"]
                ),
                "status": "VERIFIED_BY_CODEX"
                if mapping["values"]
                else "VERIFIED_BY_CODEX_STRUCTURAL_ONLY",
                "topology": mapping["topology"],
                "values": verified_values(mapping["values"]),
            }
            for mapping in reviewed["mappings"]
        ]
        source_only = [
            {
                "affected_source_labels": list(row["affected_source_labels"]),
                "label_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, ref)
                    for ref in row["labels"]
                ],
                "open_mapping": row["open_mapping"],
                "reason": row["reason"],
                "row_id": row["row_id"],
                "status": "OPEN_UNAVAILABLE_FAIR_VALUE_NOT_ZERO"
                if row["open_mapping"]
                else "VERIFIED_SOURCE_ONLY_ACCOUNTING_CONTROL",
                "values": verified_values(row["values"]),
            }
            for row in reviewed["source_only_rows"]
        ]
        by_role = {mapping["role"]: mapping for mapping in mappings}
        by_row = {row["row_id"]: row for row in source_only}
        asset_roles = [
            role
            for role in (
                "BOOK_ASSET_CASH",
                "BOOK_ASSET_CENTRAL_BANK",
                "BOOK_ASSET_INTERBANK",
                "BOOK_ASSET_TRADING",
                "BOOK_ASSET_DERIVATIVE",
                "BOOK_ASSET_LOANS",
                "BOOK_ASSET_INVESTMENT",
                "BOOK_ASSET_LONG_TERM",
                "BOOK_ASSET_OTHER",
            )
            if role in by_role
        ]
        liability_roles = [
            role
            for role in (
                "BOOK_LIABILITY_CENTRAL_AND_INTERBANK",
                "BOOK_LIABILITY_GOVERNMENT",
                "BOOK_LIABILITY_INTERBANK",
                "BOOK_LIABILITY_CUSTOMER",
                "BOOK_LIABILITY_DERIVATIVE",
                "BOOK_LIABILITY_ENTRUSTED",
                "BOOK_LIABILITY_ISSUED",
                "BOOK_LIABILITY_OTHER",
            )
            if role in by_role
        ]
        equations = [
            _equation(
                "VISIBLE_BOOK_ASSET_ROWS_EQUAL_TOTAL_FINANCIAL_ASSETS",
                sum(_value(by_role[role]) for role in asset_roles),
                _value(by_role["BOOK_TOTAL_ASSETS"]),
            ),
            _equation(
                "VISIBLE_BOOK_LIABILITY_ROWS_EQUAL_TOTAL_FINANCIAL_LIABILITIES",
                sum(_value(by_role[role]) for role in liability_roles),
                _value(by_role["BOOK_TOTAL_LIABILITIES"]),
            ),
            _equation(
                "EXPLICIT_CASH_FAIR_VALUE_EQUALS_CASH_CARRYING_VALUE",
                _value(by_role["FAIR_ASSET_CASH"]),
                _value(by_role["BOOK_ASSET_CASH"]),
            ),
        ]
        if code == "VPB":
            equations.append(
                _equation(
                    "PRINTED_KNOWN_FAIR_VALUE_SUBTOTAL_EQUALS_ONLY_NUMERIC_FAIR_VALUE",
                    _value(by_row["FI-004"]),
                    _value(by_role["FAIR_ASSET_CASH"]),
                )
            )
        if code == "VCB":
            equations.extend(
                [
                    _equation(
                        "EXPLICIT_CENTRAL_BANK_FAIR_VALUE_EQUALS_CARRYING_VALUE",
                        _value(by_role["FAIR_ASSET_CENTRAL_BANK"]),
                        _value(by_role["BOOK_ASSET_CENTRAL_BANK"]),
                    ),
                    _equation(
                        "HTM_PLUS_AFS_EQUAL_PRINTED_INVESTMENT_SECURITIES_TOTAL",
                        _value(by_row["FI-005"]) + _value(by_row["FI-006"]),
                        _value(by_role["BOOK_ASSET_INVESTMENT"]),
                    ),
                ]
            )
        period_status = (
            "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            if reviewed["source_period"] == "2026-03-31"
            else "VERIFIED_SOURCE_PERIOD_Q2_2026"
        )
        trials.append(
            {
                **base,
                "absence_evidence": None,
                "mapped_report_norm_ids": sorted(
                    {mapping["schema_binding"]["report_norm_id"] for mapping in mappings}
                ),
                "owner_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, ref)
                    for ref in reviewed["owner"]
                ],
                "page_span": list(reviewed["page_span"]),
                "source_period": reviewed["source_period"],
                "source_period_status": period_status,
                "status": "VERIFIED_BY_CODEX_WITH_OPEN_UNAVAILABLE_FAIR_VALUES",
                "unit_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, ref)
                    for ref in reviewed["unit_evidence"]
                ],
                "verified_accounting_equations": equations,
                "verified_mappings": mappings,
                "verified_source_only_rows": source_only,
            }
        )
    mapped_union = sorted(
        {
            mapping["schema_binding"]["report_norm_id"]
            for t in trials
            for mapping in t["verified_mappings"]
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
            "family_end_display_order": 1026,
            "family_root": _schema_binding(schema_by_id.get(1305), 1305),
            "mapped_report_norm_ids": mapped_union,
            "section_root": _schema_binding(schema_by_id.get(1259), 1259),
        },
        "state": "FINANCIAL_INSTRUMENTS_8BANK_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "e0099:result:" + canonical_json_sha256_v1(material)}
    )


def _stable_json(path: Path) -> tuple[dict[str, Any], str]:
    support = scanner._support()._support()
    raw = support._stable_bytes(path)
    return support._strict_json(raw, path.as_posix()), hashlib.sha256(raw).hexdigest()


def _live_inputs() -> dict[str, Any]:
    semantic_index, index_sha = _stable_json(SEMANTIC_INDEX_PATH)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH)
    review, review_sha = _stable_json(REVIEW_PATH)
    if index_sha != EXPECTED_INDEX_SHA256 or crop_sha != EXPECTED_CROP_MANIFEST_SHA256:
        raise _error("financial-instruments fixed input hash drifted")
    scan = scanner.build_financial_instruments_full_document_scan_v1(semantic_index)
    authority, by_id = _authority_snapshot(PROJECT_ROOT)
    for report_norm_id, (name, parent, display_order) in _SCHEMA_EXPECTED.items():
        item = by_id.get(report_norm_id)
        if (
            item is None
            or item.canonical_name != name
            or item.parent_id != parent
            or item.display_order != display_order
            or item.statement_type != "TM"
        ):
            raise _error(f"financial-instruments live schema drifted: {report_norm_id}")
    return {
        "crop_manifest": crop_manifest,
        "crop_manifest_sha256": crop_sha,
        "review": review,
        "review_sha256": review_sha,
        "schema_authority": authority,
        "schema_by_id": by_id,
        "semantic_index": semantic_index,
        "structure_scan": scan,
    }


def build_live_financial_instruments_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    return build_financial_instruments_8bank_codex_verified_mapping_v1(**_live_inputs())


def validate_live_financial_instruments_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_live_financial_instruments_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("financial-instruments result does not replay exactly")
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
        _write(RESULT_PATH, build_live_financial_instruments_8bank_codex_verified_mapping_v1())
    if args.validate_result:
        value, _ = _stable_json(RESULT_PATH)
        validate_live_financial_instruments_8bank_codex_verified_mapping_v1(value)


if __name__ == "__main__":
    main()
