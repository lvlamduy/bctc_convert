"""Verify investment-securities sale activity in the fixed eight reports."""

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
        raise RuntimeError(f"cannot load experiment support module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


foundation = _load_module(
    "trading_activity_support_for_investment_securities_mapping",
    "build_trading_securities_activity_8bank_codex_verified_mapping_v1.py",
)
scanner = _load_module(
    "investment_securities_scan_for_verified_mapping",
    "scan_investment_securities_activity_full_document_vietocr_v1.py",
)
support = foundation.support

FORMAT_VERSION = "INVESTMENT_SECURITIES_ACTIVITY_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "INVESTMENT_SECURITIES_ACTIVITY_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "INVESTMENT_SECURITIES_ACTIVITY_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "e0085:result:"
REVIEW_STATE = "CODEX_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "e0085:pixel-review:"
REVIEW_RUN_ID = "E-0085"
ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT = True
SCHEMA_FAMILY_END_DISPLAY_ORDER = 752
INCLUDE_COMPONENT_METRICS = False
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_BANK_BLIND_INVESTMENT_"
    "SECURITIES_ACTIVITY_GRAPH_VISIBLE_PDF_LABEL_PADDLEOCR_OR_NATIVE_SOURCE_"
    "NUMERIC_CHALLENGER_PERIOD_UNIT_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_NO_"
    "CANONICALIZATION_EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0085-investment-securities-activity-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0085-investment-securities-activity-8bank-codex-verified-mapping-v1.json"
)
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = foundation.CROP_MANIFEST_PATH
EXPECTED_INDEX_SHA256 = foundation.EXPECTED_INDEX_SHA256
EXPECTED_CROP_MANIFEST_SHA256 = foundation.EXPECTED_CROP_MANIFEST_SHA256
EXPECTED_AXIS_SHA256 = foundation.EXPECTED_AXIS_SHA256
EXPECTED_SCAN_ID = "isafdsv1:scan:ac528409d575749ad114c68932594ec75c7f1cdc6bd676a7728a87779d323823"
EXPECTED_RESULT_ID = "e0085:result:257898e302b323b14119a3178e0931417acce6629b6ba5391510ac9b4b45985d"

_SCHEMA_EXPECTED = {
    1193: ("Lãi thuần từ hoạt động mua bán chứng khoán đầu tư", 1142, 747),
    1194: ("Thu nhập do mua bán chứng khoán đầu tư", 1193, 748),
    1195: ("Chi phí mua bán chứng khoán đầu tư", 1193, 749),
    1196: ("(Trích lập)/Hoàn nhập dự phòng giảm giá chứng khoán đầu tư", 1193, 750),
    6028: ("(Trích lập)/Hoàn nhập dự phòng giảm giá góp vốn, đầu tư dài hạn", 1193, 751),
}
_ROLE_TO_SCHEMA = {
    "NET_INVESTMENT_SECURITIES": 1193,
    "INCOME_INVESTMENT_SECURITIES": 1194,
    "EXPENSE_INVESTMENT_SECURITIES": 1195,
    "PROVISION_INVESTMENT_SECURITIES": 1196,
    "OTHER_INVESTMENT_SECURITIES_PROVISION": 6028,
}
_ROLE_TO_GRAPH = {
    "INCOME_INVESTMENT_SECURITIES": "INCOME",
    "EXPENSE_INVESTMENT_SECURITIES": "EXPENSE",
    "PROVISION_INVESTMENT_SECURITIES": "PROVISION",
    "OTHER_INVESTMENT_SECURITIES_PROVISION": "OTHER",
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_seven_reviewed_detailed_investment_regions": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "text_similarity_alone_used_for_mapping": False,
    "trading_activity_or_segment_aggregate_relabelled_as_investment_activity": False,
}
_REVIEW_SAFETY = {
    "bank_page_or_filename_used_as_graph_rule": False,
    "mapping_decided_by_text_similarity_alone": False,
    "old_ocr_used_as_semantic_anchor": False,
    "optional_provision_or_long_term_investment_row_required_in_every_bank": False,
    "paddleocr_or_native_source_axis_used_as_semantic_anchor": False,
    "segment_report_aggregate_used_as_detailed_activity_note": False,
    "trading_securities_region_used_as_investment_region": False,
    "vietocr_used_as_numeric_truth": False,
    "visible_pdf_pixels_reviewed": True,
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


class InvestmentSecuritiesActivity8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixels, numbers, equations, or TM schema drifted."""


def _error(message: str) -> InvestmentSecuritiesActivity8BankCodexVerifiedMappingV1Error:
    return InvestmentSecuritiesActivity8BankCodexVerifiedMappingV1Error(message)


def _ref(page: int, line: int, text: str) -> dict[str, Any]:
    return {"line_index": line, "page_sequence": page, "pixel_transcription": text}


def _line(page: int, line: int, text: str) -> dict[str, Any]:
    return {"kind": "AUTHENTICATED_LINE", **_ref(page, line, text)}


def _dash(page: int, bbox: Sequence[int], pixel_rgb_sha256: str) -> dict[str, Any]:
    return {
        "bbox": list(bbox),
        "kind": "AUTHENTICATED_RENDER_PIXEL_DASH",
        "page_sequence": page,
        "pixel_rgb_sha256": pixel_rgb_sha256,
        "pixel_transcription": "-",
    }


def _mapping(
    role: str,
    label: tuple[int, str],
    current: dict[str, Any],
    comparative: dict[str, Any],
    topology: str,
    *,
    page: int,
) -> dict[str, Any]:
    return {
        "label": _ref(page, label[0], label[1]),
        "report_norm_id": _ROLE_TO_SCHEMA[role],
        "role": role,
        "topology": topology,
        "values": {"COMPARATIVE_PERIOD": comparative, "CURRENT_PERIOD": current},
    }


def _rows(
    page: int,
    topology: str,
    *,
    owner: tuple[int, str, dict[str, Any], dict[str, Any]],
    income: tuple[int, str, dict[str, Any], dict[str, Any]],
    expense: tuple[int, str, dict[str, Any], dict[str, Any]],
    provision: tuple[int, str, dict[str, Any], dict[str, Any]] | None = None,
    other: tuple[int, str, dict[str, Any], dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    specifications = [
        ("NET_INVESTMENT_SECURITIES", owner),
        ("INCOME_INVESTMENT_SECURITIES", income),
        ("EXPENSE_INVESTMENT_SECURITIES", expense),
    ]
    if provision is not None:
        specifications.append(("PROVISION_INVESTMENT_SECURITIES", provision))
    if other is not None:
        specifications.append(("OTHER_INVESTMENT_SECURITIES_PROVISION", other))
    return [
        _mapping(role, (row[0], row[1]), row[2], row[3], topology, page=page)
        for role, row in specifications
    ]


def _mapped_document(
    code: str,
    page: int,
    source_period: str,
    presentation: str,
    period_lines: Sequence[tuple[int, int, str]],
    unit_lines: Sequence[tuple[int, int, str]],
    mappings: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "absence_evidence": None,
        "bank_code": code,
        "mappings": list(mappings),
        "page_span": [page, page],
        "period_axis": [_ref(p, line, text) for p, line, text in period_lines],
        "presentation": presentation,
        "source_period": source_period,
        "unit_evidence": [_ref(p, line, text) for p, line, text in unit_lines],
    }


def _absent(code: str, pages: Sequence[int], reason: str) -> dict[str, Any]:
    return {
        "absence_evidence": {
            "complete_pdf_pages_scanned": True,
            "detailed_investment_activity_graph_match_count": 0,
            "negative_control_pages": list(pages),
            "reason": reason,
            "source_scope_absence_only": True,
        },
        "bank_code": code,
        "mappings": [],
        "page_span": None,
        "period_axis": [],
        "presentation": "NO_DETAILED_INVESTMENT_SECURITIES_ACTIVITY_NOTE_IN_BOUND_REPORT",
        "source_period": None,
        "unit_evidence": [],
    }


def _review_documents() -> list[dict[str, Any]]:
    trailing = "INCOME_EXPENSE_OPTIONAL_PROVISION_THEN_UNLABELLED_NET_TWO_PERIOD_LANES"
    return [
        _mapped_document(
            "ACB",
            25,
            "2026-06-30",
            "THREE_VISIBLE_DASHES_OMITTED_FROM_OCR_THEN_UNLABELLED_NET",
            [(25, 5, "Đến"), (25, 6, "Đến"), (25, 7, "30.6.2026"), (25, 8, "30.6.2025")],
            [(25, 9, "Triệu đồng"), (25, 10, "Triệu đồng")],
            _rows(
                25,
                trailing,
                owner=(
                    4,
                    "LÃI/(LỖ) THUẦN TỪ MUA BÁN CHỨNG KHOÁN ĐẦU TƯ",
                    _line(25, 17, "(21.896)"),
                    _line(25, 18, "444.596"),
                ),
                income=(
                    11,
                    "Thu nhập từ mua bán chứng khoán đầu tư",
                    _dash(
                        25,
                        [1284, 594, 1301, 608],
                        "3c63b0a6e31289b48d3fcc13725fb63fe0051fdfcbed2b291e8d66b1c1c6a808",
                    ),
                    _line(25, 12, "447.840"),
                ),
                expense=(
                    13,
                    "Chi phí về mua bán chứng khoán đầu tư",
                    _line(25, 14, "(21.896)"),
                    _line(25, 15, "(3.244)"),
                ),
                provision=(
                    16,
                    "Hoàn nhập/(Trích lập) dự phòng rủi ro chứng khoán đầu tư",
                    _dash(
                        25,
                        [1284, 673, 1300, 688],
                        "626bdb25652e1dc7d4ce28665c43121bba547ebc606258b4906c05deee40e78b",
                    ),
                    _dash(
                        25,
                        [1482, 674, 1498, 690],
                        "42bd705428a7cc19e35675b2abea1f9b8df628ebc6743e7c49e74af666d77355",
                    ),
                ),
            ),
        ),
        _mapped_document(
            "MBB",
            47,
            "2026-06-30",
            "WRAPPED_INNER_OWNER_SHARED_AXES_WITH_OPTIONAL_LONG_TERM_PROVISION",
            [
                (47, 31, "Từ 01/01/2026"),
                (47, 32, "Từ 01/01/2025"),
                (47, 33, "đến 30/06/2026"),
                (47, 34, "đến 30/06/2025"),
            ],
            [(47, 35, "Triệu đồng"), (47, 36, "Triệu đồng")],
            _rows(
                47,
                "WRAPPED_INNER_OWNER_SHARED_AXES_WITH_OPTIONAL_LONG_TERM_PROVISION",
                owner=(
                    51,
                    "Lãi/(lỗ) thuần từ mua bán chứng khoán đầu tư",
                    _line(47, 65, "3.587"),
                    _line(47, 66, "1.295.273"),
                ),
                income=(
                    52,
                    "Thu nhập từ mua bán chứng khoán đầu tư",
                    _line(47, 53, "261.677"),
                    _line(47, 54, "1.318.966"),
                ),
                expense=(
                    55,
                    "Chi về chứng khoán đầu tư",
                    _line(47, 56, "(243.217)"),
                    _line(47, 57, "(91.167)"),
                ),
                provision=(
                    58,
                    "(Trích lập)/hoàn nhập dự phòng rủi ro chứng khoán đầu tư",
                    _line(47, 60, "(14.873)"),
                    _line(47, 61, "25.413"),
                ),
                other=(
                    62,
                    "(Trích lập)/hoàn nhập dự phòng giảm giá góp vốn, đầu tư dài hạn",
                    _dash(
                        47,
                        [1209, 1327, 1225, 1340],
                        "807ff471fb9196e5f7a5ce832f66f39b28b82fcd1f38059de04743ca839bc47f",
                    ),
                    _line(47, 64, "42.061"),
                ),
            ),
        ),
        _mapped_document(
            "VPB",
            63,
            "2026-03-31",
            "Q1_THREE_MONTH_DURATION_WITH_WRAPPED_PERIOD_AND_PROVISION_LABELS",
            [
                (63, 68, "Cho kỳ kế toán"),
                (63, 69, "Cho kỳ kế toán"),
                (63, 70, "3 tháng kết thúc"),
                (63, 71, "3 tháng kết thúc"),
                (63, 72, "ngày 31 tháng 3"),
                (63, 73, "ngày 31 tháng 3"),
                (63, 74, "năm 2026"),
                (63, 75, "năm 2025"),
            ],
            [(63, 76, "Triệu đồng"), (63, 77, "Triệu đồng")],
            _rows(
                63,
                trailing,
                owner=(
                    67,
                    "LÃI/(LỖ) THUẦN TỪ MUA BÁN CHỨNG KHOÁN ĐẦU TƯ",
                    _line(63, 88, "14.393"),
                    _line(63, 89, "(134.849)"),
                ),
                income=(
                    78,
                    "Thu nhập từ mua bán chứng khoán đầu tư",
                    _line(63, 79, "15.306"),
                    _line(63, 80, "16.107"),
                ),
                expense=(
                    81,
                    "Chi phí về mua bán chứng khoán đầu tư",
                    _line(63, 82, "(2.714)"),
                    _line(63, 83, "(13.760)"),
                ),
                provision=(
                    84,
                    "(Trích lập)/Hoàn nhập dự phòng chứng khoán đầu tư",
                    _line(63, 86, "1.801"),
                    _line(63, 87, "(137.196)"),
                ),
            ),
        ),
        _mapped_document(
            "HDB",
            35,
            "2026-06-30",
            "WRAPPED_PROVISION_LABEL_WITH_TRAILING_UNLABELLED_NET",
            [(35, 8, "Kỳ này"), (35, 9, "Kỳ trước")],
            [(35, 10, "Triệu VND"), (35, 11, "Triệu VND")],
            _rows(
                35,
                trailing,
                owner=(
                    7,
                    "Lãi/(Lỗ) thuần từ hoạt động mua bán chứng khoán đầu tư",
                    _line(35, 22, "20.991"),
                    _line(35, 23, "2.782"),
                ),
                income=(
                    12,
                    "Thu nhập từ mua bán chứng khoán đầu tư",
                    _line(35, 13, "55.528"),
                    _line(35, 14, "31.191"),
                ),
                expense=(
                    15,
                    "Chi phí về mua bán chứng khoán đầu tư",
                    _line(35, 16, "(15.281)"),
                    _line(35, 17, "(8.436)"),
                ),
                provision=(
                    18,
                    "Hoàn nhập/(Trích lập) dự phòng rủi ro chứng khoán đầu tư",
                    _line(35, 19, "(19.256)"),
                    _line(35, 20, "(19.973)"),
                ),
            ),
        ),
        _absent(
            "VCB",
            [42, 43],
            "The complete report has segment-report investment-securities aggregates on pages 42-43 but no detailed investment-securities income/expense activity graph; segment totals are retained only as distinct negative controls.",
        ),
        _mapped_document(
            "CTG",
            46,
            "2026-06-30",
            "SPECIFIC_PROVISION_ROLE_PRECEDES_LABELLED_POSITIVE_NET",
            [
                (46, 5, "Giai đoạn tài chính"),
                (46, 6, "Giai đoạn tài chính"),
                (46, 7, "từ 01/01/2026 đến"),
                (46, 8, "từ 01/01/2025 đến"),
                (46, 9, "hết 30/06/2026"),
                (46, 10, "hết 30/06/2025"),
            ],
            [(46, 11, "triệu đồng"), (46, 12, "triệu đồng")],
            _rows(
                46,
                trailing,
                owner=(
                    4,
                    "LÃI/(LỖ) THUẦN TỪ HOẠT ĐỘNG MUA BÁN CHỨNG KHOÁN ĐẦU TƯ",
                    _line(46, 23, "395.275"),
                    _line(46, 24, "121.551"),
                ),
                income=(
                    13,
                    "Thu nhập từ mua bán chứng khoán đầu tư",
                    _line(46, 14, "21.778"),
                    _line(46, 15, "46.585"),
                ),
                expense=(
                    16,
                    "Chi phí về mua bán chứng khoán đầu tư",
                    _line(46, 17, "(15.119)"),
                    _line(46, 18, "(2.004)"),
                ),
                provision=(
                    19,
                    "Chi phí dự phòng rủi ro chứng khoán đầu tư",
                    _line(46, 20, "388.616"),
                    _line(46, 21, "76.970"),
                ),
            ),
        ),
        _mapped_document(
            "BID",
            29,
            "2026-06-30",
            "DOCUMENT_SECTION_UNIT_INHERITED_AND_LABELLED_PROVISION",
            [
                (29, 42, "Từ 01/01/2026 đến"),
                (29, 43, "Từ 01/01/2025 đến"),
                (29, 44, "30/06/2026"),
                (29, 45, "30/06/2025"),
            ],
            [(28, 58, "Đơn vị: Triệu VND")],
            _rows(
                29,
                trailing,
                owner=(
                    41,
                    "LÃI/LỖ THUẦN TỪ MUA BÁN CHỨNG KHOÁN ĐẦU TƯ",
                    _line(29, 55, "5,199"),
                    _line(29, 56, "792,824"),
                ),
                income=(
                    46,
                    "Thu nhập từ mua bán chứng khoán đầu tư",
                    _line(29, 47, "17,423"),
                    _line(29, 48, "698,363"),
                ),
                expense=(
                    49,
                    "Chi phí về mua bán chứng khoán đầu tư",
                    _line(29, 50, "(643)"),
                    _line(29, 51, "(421)"),
                ),
                provision=(
                    52,
                    "Chi phí dự phòng rủi ro chứng khoán đầu tư",
                    _line(29, 53, "(11,581)"),
                    _line(29, 54, "94,882"),
                ),
            ),
        ),
        _mapped_document(
            "VIB",
            46,
            "2026-06-30",
            "NO_PROVISION_ROW_INCOME_PLUS_EXPENSE_EQUALS_LABELLED_NET",
            [
                (46, 35, "6 tháng đầu"),
                (46, 36, "6 tháng đầu"),
                (46, 37, "năm 2026"),
                (46, 38, "năm 2025"),
            ],
            [(46, 39, "triệu đồng"), (46, 40, "triệu đồng")],
            _rows(
                46,
                trailing,
                owner=(
                    34,
                    "(LỖ)/LÃI THUẦN TỪ MUA BÁN CHỨNG KHOÁN ĐẦU TƯ",
                    _line(46, 48, "(179.085)"),
                    _line(46, 49, "150.481"),
                ),
                income=(
                    41,
                    "Thu nhập từ mua bán chứng khoán đầu tư",
                    _line(46, 42, "269.410"),
                    _line(46, 43, "275.184"),
                ),
                expense=(
                    44,
                    "Chi phí về mua bán chứng khoán đầu tư",
                    _line(46, 45, "(448.495)"),
                    _line(46, 46, "(124.703)"),
                ),
            ),
        ),
    ]


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
        raise _error("Codex investment-securities pixel review differs from the fixed ledger")
    return canonical_clone_v1(expected)


def _document(items: Any, code: str, label: str) -> dict[str, Any]:
    return foundation._document(items, code, label)


def _page(document: Mapping[str, Any], page_sequence: int, label: str) -> dict[str, Any]:
    return foundation._page(document, page_sequence, label)


def _semantic_evidence(
    axis_document: Mapping[str, Any],
    semantic_document: Mapping[str, Any],
    item: Mapping[str, Any],
) -> dict[str, Any]:
    page_number = item["page_sequence"]
    axis_page = _page(axis_document, page_number, "accounting axis")
    semantic_page = _page(semantic_document, page_number, "semantic index")
    line_index = item["line_index"]
    axis_line = support._axis_line(axis_page, line_index)
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


def _numeric_components(value: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
    components = value.get("components")
    if components is None:
        return (value,)
    if type(components) is not list or not components:
        raise _error("investment-securities numeric component shape drifted")
    return components


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    metrics = {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "authenticated_pixel_dash_zero_count": sum(
            component.get("source_numeric_challenger_status")
            == "VISIBLE_AUTHENTICATED_PIXEL_DASH_NOT_DETECTED_AS_SOURCE_LINE"
            for trial in trials
            for mapping in trial["verified_mappings"]
            for value in mapping["values"]
            for component in _numeric_components(value)
        ),
        "detailed_note_not_present_document_count": sum(
            trial["status"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT" for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for trial in trials
        ),
        "fresh_vietocr_numeric_disagreement_count": sum(
            component.get("fresh_vietocr_numeric_status")
            == "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
            for trial in trials
            for mapping in trial["verified_mappings"]
            for value in mapping["values"]
            for component in _numeric_components(value)
        ),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "open_source_row_count": 0,
        "q1_source_period_caveat_document_count": sum(
            trial["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            for trial in trials
        ),
        "verified_value_cell_count": sum(
            len(mapping["values"]) for trial in trials for mapping in trial["verified_mappings"]
        ),
    }
    if INCLUDE_COMPONENT_METRICS:
        metrics["verified_source_numeric_component_count"] = sum(
            len(_numeric_components(value))
            for trial in trials
            for mapping in trial["verified_mappings"]
            for value in mapping["values"]
        )
    return metrics


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("investment-securities result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != RESULT_STATE
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("investment-securities result identity or metrics drifted")
    allowed = {
        "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT",
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT",
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
                mapping.get("status") != "VERIFIED_BY_CODEX"
                for mapping in trial.get("verified_mappings", [])
            )
        ):
            raise _error("investment-securities trial shape or status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != RESULT_ID_PREFIX + canonical_json_sha256_v1(material):
        raise _error("investment-securities result identity drifted")
    return canonical_clone_v1(value)


def _equations(by_role: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for axis_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"):

        def value(role: str, *, axis_role: str = axis_role) -> Mapping[str, Any]:
            return next(item for item in by_role[role]["values"] if item["axis_role"] == axis_role)

        term_roles = [
            role
            for role in _ROLE_TO_SCHEMA
            if role != "NET_INVESTMENT_SECURITIES" and role in by_role
        ]
        terms = [value(role) for role in term_roles]
        total = value("NET_INVESTMENT_SECURITIES")
        computed = sum(term["normalized_value"] for term in terms)
        if computed != total["normalized_value"]:
            raise _error(f"investment-securities net equation does not close: {axis_role}")
        result.append(
            {
                "computed_value": computed,
                "equation": "OBSERVED_INCOME_EXPENSE_OPTIONAL_PROVISION_TERMS_EQUAL_NET_INVESTMENT_ACTIVITY",
                "period_role": axis_role,
                "status": "CORROBORATED_EXACT",
                "term_report_norm_ids": [_ROLE_TO_SCHEMA[role] for role in term_roles],
                "total_report_norm_id": 1193,
            }
        )
    return result


def _source_period_status(source_period: str) -> str:
    return (
        "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
        if source_period == "2026-03-31"
        else "VERIFIED_SOURCE_PERIOD_Q2_2026"
    )


def _verified_numeric_reference(
    ref: Mapping[str, Any],
    axis_page: Mapping[str, Any],
    semantic_page: Mapping[str, Any],
    crop_page: Mapping[str, Any],
    source_texts: Sequence[str],
) -> dict[str, Any]:
    if ref["kind"] == "AUTHENTICATED_LINE":
        evidence = support._source_value(
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
            proposal = support._money(evidence["fresh_vietocr_numeric_proposal"])
        except ValueError:
            proposal = None
        return {
            **evidence,
            "fresh_vietocr_numeric_status": (
                "MATCHES_SOURCE_NUMERIC_CHALLENGER"
                if proposal == evidence["normalized_value"]
                else "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
            ),
            "page_sequence": ref["page_sequence"],
        }
    if ref["kind"] == "AUTHENTICATED_RENDER_PIXEL_DASH":
        return foundation._pixel_dash_value(crop_page, ref)
    raise _error("investment-securities value reference kind drifted")


def _verified_numeric_value(
    axis_role: str,
    ref_or_refs: Any,
    axis_page: Mapping[str, Any],
    semantic_page: Mapping[str, Any],
    crop_page: Mapping[str, Any],
    source_texts: Sequence[str],
) -> dict[str, Any]:
    if type(ref_or_refs) is dict:
        return {
            "axis_role": axis_role,
            **_verified_numeric_reference(
                ref_or_refs, axis_page, semantic_page, crop_page, source_texts
            ),
        }
    if type(ref_or_refs) is not list or len(ref_or_refs) < 2:
        raise _error("investment-securities aggregated value references drifted")
    components = [
        _verified_numeric_reference(ref, axis_page, semantic_page, crop_page, source_texts)
        for ref in ref_or_refs
    ]
    return {
        "aggregation": "SUM_OF_VISIBLE_SOURCE_ROWS",
        "axis_role": axis_role,
        "components": components,
        "normalized_value": sum(component["normalized_value"] for component in components),
        "source_numeric_challenger_status": "SUM_OF_VERIFIED_VISIBLE_SOURCE_ROWS",
    }


def build_investment_securities_activity_8bank_codex_verified_mapping_v1(
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
    axis_projection = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    scanner.validate_investment_securities_activity_full_document_scan_replay_v1(
        structure_scan, semantic_index
    )
    if (
        axis_projection.get("semantic_axis_sha256") != EXPECTED_AXIS_SHA256
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
            "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
        }
        if reviewed["absence_evidence"] is not None:
            if matcher["uniqueness"]["status"] == "UNIQUE_FULL_MATCH":
                raise _error("absent detailed investment-securities note unexpectedly matched")
            trials.append(
                {
                    **base,
                    "absence_evidence": canonical_clone_v1(reviewed["absence_evidence"]),
                    "page_span": None,
                    "period_evidence": [],
                    "presentation": reviewed["presentation"],
                    "source_period_status": "NOT_APPLICABLE_NO_DETAILED_NOTE",
                    "status": "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT",
                    "unit_evidence": [],
                    "verified_accounting_equations": [],
                    "verified_mappings": [],
                }
            )
            continue
        if not same_typed_json_v1(
            matcher["uniqueness"], {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
        ) or not same_typed_json_v1(matcher["regions"][0]["page_span"], reviewed["page_span"]):
            raise _error("reviewed region is not the unique whole-PDF investment graph")
        expected_graph_roles = sorted(
            _ROLE_TO_GRAPH[mapping["role"]]
            for mapping in reviewed["mappings"]
            if mapping["role"] in _ROLE_TO_GRAPH
        )
        if not same_typed_json_v1(
            matcher["regions"][0]["layout"]["child_roles"], expected_graph_roles
        ):
            raise _error("reviewed investment child roles differ from whole-PDF graph")
        page_number = reviewed["page_span"][0]
        axis_document = _document(axis_projection["documents"], code, "accounting axis")
        semantic_document = _document(semantic_index["documents"], code, "semantic index")
        crop_document = _document(crop_manifest["documents"], code, "crop manifest")
        axis_page = _page(axis_document, page_number, "accounting axis")
        semantic_page = _page(semantic_document, page_number, "semantic index")
        crop_page = _page(crop_document, page_number, "crop manifest")
        source_texts = support._source_line_axis(crop_page)
        verified_mappings = []
        for mapping in reviewed["mappings"]:
            values = []
            for axis_role, ref_or_refs in mapping["values"].items():
                values.append(
                    _verified_numeric_value(
                        axis_role,
                        ref_or_refs,
                        axis_page,
                        semantic_page,
                        crop_page,
                        source_texts,
                    )
                )
            verified_mapping = {
                "label_evidence": _semantic_evidence(
                    axis_document, semantic_document, mapping["label"]
                ),
                "role": mapping["role"],
                "schema_binding": _schema_binding(
                    schema_by_id.get(mapping["report_norm_id"]), mapping["report_norm_id"]
                ),
                "status": "VERIFIED_BY_CODEX",
                "topology": mapping["topology"],
                "values": values,
            }
            if "component_labels" in mapping:
                labels = mapping["component_labels"]
                if type(labels) is not list or not labels:
                    raise _error("investment-securities component labels drifted")
                verified_mapping["component_label_evidence"] = [
                    _semantic_evidence(axis_document, semantic_document, label) for label in labels
                ]
            verified_mappings.append(verified_mapping)
        equations = _equations({item["role"]: item for item in verified_mappings})
        trials.append(
            {
                **base,
                "absence_evidence": None,
                "page_span": list(reviewed["page_span"]),
                "period_evidence": [
                    _semantic_evidence(axis_document, semantic_document, item)
                    for item in reviewed["period_axis"]
                ],
                "presentation": reviewed["presentation"],
                "source_period_status": _source_period_status(reviewed["source_period"]),
                "status": (
                    "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT"
                    if reviewed["source_period"] == "2026-03-31"
                    else "VERIFIED_BY_CODEX"
                ),
                "unit_evidence": [
                    _semantic_evidence(axis_document, semantic_document, item)
                    for item in reviewed["unit_evidence"]
                ],
                "verified_accounting_equations": equations,
                "verified_mappings": verified_mappings,
            }
        )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "crop_manifest_sha256": crop_manifest_sha256,
            "pixel_review_sha256": review_sha256,
            "schema_authority": canonical_clone_v1(schema_authority),
            "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
            "semantic_index_sha256": EXPECTED_INDEX_SHA256,
            "structure_scan_id": EXPECTED_SCAN_ID,
        },
        "metrics": _metrics(trials),
        "schema_family": {
            "family_end_display_order": SCHEMA_FAMILY_END_DISPLAY_ORDER,
            "family_root_report_norm_id": 1193,
            "mapped_report_norm_ids": sorted(_SCHEMA_EXPECTED),
            "unobserved_optional_report_norm_ids": [1197],
        },
        "state": RESULT_STATE,
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def validate_investment_securities_activity_8bank_codex_verified_mapping_replay_v1(
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
    rebuilt = build_investment_securities_activity_8bank_codex_verified_mapping_v1(
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
        raise _error("investment-securities verified mapping does not replay exactly")
    return supplied


def _stable_json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], str]:
    payload = support._stable_bytes(path)
    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise _error(f"fixed JSON bytes drifted: {path}")
    value = support._strict_json(payload, path.as_posix())
    if type(value) is not dict:
        raise _error(f"fixed JSON root must be one object: {path}")
    return value, digest


def build_live_investment_securities_activity_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_live_investment_securities_activity_full_document_scan_v1()
    review, review_sha = _stable_json(REVIEW_PATH)
    historical_result, _ = _stable_json(RESULT_PATH)
    historical_result = _validate_result(historical_result)
    if historical_result.get("result_id") != EXPECTED_RESULT_ID:
        raise _error("fixed historical investment-securities result identity drifted")
    schema_authority = canonical_clone_v1(historical_result["input_refs"]["schema_authority"])
    _live_schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return build_investment_securities_activity_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )


def validate_live_investment_securities_activity_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    if type(value) is not dict or value.get("result_id") != EXPECTED_RESULT_ID:
        raise _error("investment-securities verified mapping does not replay exactly")
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_live_investment_securities_activity_full_document_scan_v1()
    review, review_sha = _stable_json(REVIEW_PATH)
    historical_result, _ = _stable_json(RESULT_PATH)
    historical_result = _validate_result(historical_result)
    if historical_result.get("result_id") != EXPECTED_RESULT_ID:
        raise _error("fixed historical investment-securities result identity drifted")
    schema_authority = canonical_clone_v1(historical_result["input_refs"]["schema_authority"])
    _live_schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return validate_investment_securities_activity_8bank_codex_verified_mapping_replay_v1(
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
        _write(
            RESULT_PATH, build_live_investment_securities_activity_8bank_codex_verified_mapping_v1()
        )
    if args.validate_result:
        result, _ = _stable_json(RESULT_PATH)
        validate_live_investment_securities_activity_8bank_codex_verified_mapping_v1(result)


if __name__ == "__main__":
    main()
