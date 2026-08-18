"""Verify trading-securities sale activity in the fixed eight reports."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from PIL import Image

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
    "fx_gold_support_for_trading_securities_mapping",
    "build_fx_gold_activity_8bank_codex_verified_mapping_v1.py",
)
scanner = _load_module(
    "trading_securities_scan_for_verified_mapping",
    "scan_trading_securities_activity_full_document_vietocr_v1.py",
)
support = foundation.service.income.foundation.support

FORMAT_VERSION = "TRADING_SECURITIES_ACTIVITY_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "TRADING_SECURITIES_ACTIVITY_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "TRADING_SECURITIES_ACTIVITY_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "e0084:result:"
REVIEW_STATE = "CODEX_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "e0084:pixel-review:"
REVIEW_RUN_ID = "E-0084"
ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT = True
SCHEMA_FAMILY_END_DISPLAY_ORDER = 746
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_BANK_BLIND_TRADING_"
    "SECURITIES_ACTIVITY_GRAPH_VISIBLE_PDF_LABEL_PADDLEOCR_OR_NATIVE_SOURCE_"
    "NUMERIC_CHALLENGER_PERIOD_UNIT_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_NO_"
    "CANONICALIZATION_EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0084-trading-securities-activity-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0084-trading-securities-activity-8bank-codex-verified-mapping-v1.json"
)
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
EXPECTED_CROP_MANIFEST_SHA256 = "a9f80cf9104af1177ba43d8a85de00b28c735223a91b663a5a79401bb038d94e"
EXPECTED_AXIS_SHA256 = "e99873cd16a7234702d0ee6e5fa9eb37637a1a75621228381e3dbcd7c5cfdcca"
EXPECTED_SCAN_ID = "tsafdsv1:scan:9d7a8f8137cb9e15559d94fa88a780b067bf08a5d4c163d15d32b9aa4e543ed1"

_SCHEMA_EXPECTED = {
    1188: ("Lãi thuần từ hoạt động mua bán chứng khoán kinh doanh", 1142, 742),
    1189: ("Thu nhập do mua bán chứng khoán kinh doanh", 1188, 743),
    1190: ("Chi phí mua bán chứng khoán kinh doanh", 1188, 744),
    1191: ("(Trích lập)/Hoàn nhập dự phòng giảm giá chứng khoán kinh doanh", 1188, 745),
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "investment_securities_activity_relabelled_as_trading_activity": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_seven_reviewed_detailed_trading_regions": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_label_alone_used_to_select_provision_family": False,
    "text_similarity_alone_used_for_mapping": False,
}
_REVIEW_SAFETY = {
    "bank_page_or_filename_used_as_graph_rule": False,
    "investment_securities_region_used_as_trading_region": False,
    "mapping_decided_by_text_similarity_alone": False,
    "old_ocr_used_as_semantic_anchor": False,
    "optional_provision_row_required_in_every_bank": False,
    "paddleocr_or_native_source_axis_used_as_semantic_anchor": False,
    "source_label_caveat_hidden": False,
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


class TradingSecuritiesActivity8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixels, numbers, equations, or TM schema drifted."""


def _error(message: str) -> TradingSecuritiesActivity8BankCodexVerifiedMappingV1Error:
    return TradingSecuritiesActivity8BankCodexVerifiedMappingV1Error(message)


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
    report_norm_id: int,
    label: tuple[int, str],
    current: dict[str, Any],
    comparative: dict[str, Any],
    topology: str,
    *,
    page: int,
) -> dict[str, Any]:
    return {
        "label": _ref(page, label[0], label[1]),
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": topology,
        "values": {"COMPARATIVE_PERIOD": comparative, "CURRENT_PERIOD": current},
    }


def _mapped_document(
    code: str,
    page: int,
    source_period: str,
    presentation: str,
    period_lines: Sequence[tuple[int, int, str]],
    unit_lines: Sequence[tuple[int, int, str]],
    mappings: Sequence[dict[str, Any]],
    *,
    source_label_caveat: str | None = None,
) -> dict[str, Any]:
    return {
        "absence_evidence": None,
        "bank_code": code,
        "mappings": list(mappings),
        "page_span": [page, page],
        "period_axis": [_ref(p, line, text) for p, line, text in period_lines],
        "presentation": presentation,
        "source_label_caveat": source_label_caveat,
        "source_period": source_period,
        "unit_evidence": [_ref(p, line, text) for p, line, text in unit_lines],
    }


def _absent(code: str, pages: Sequence[int], reason: str) -> dict[str, Any]:
    return {
        "absence_evidence": {
            "complete_pdf_pages_scanned": True,
            "detailed_trading_activity_graph_match_count": 0,
            "negative_control_pages": list(pages),
            "reason": reason,
            "source_scope_absence_only": True,
        },
        "bank_code": code,
        "mappings": [],
        "page_span": None,
        "period_axis": [],
        "presentation": "NO_DETAILED_TRADING_SECURITIES_ACTIVITY_NOTE_IN_BOUND_REPORT",
        "source_label_caveat": None,
        "source_period": None,
        "unit_evidence": [],
    }


def _four_rows(
    page: int,
    owner: tuple[int, str, int, str, int, str],
    income: tuple[int, str, int, str, int, str],
    expense: tuple[int, str, int, str, int, str],
    provision: tuple[int, str, dict[str, Any], dict[str, Any]],
    topology: str,
) -> list[dict[str, Any]]:
    return [
        _mapping(
            "NET_TRADING_SECURITIES",
            1188,
            (owner[0], owner[1]),
            _line(page, owner[2], owner[3]),
            _line(page, owner[4], owner[5]),
            topology,
            page=page,
        ),
        _mapping(
            "INCOME_TRADING_SECURITIES",
            1189,
            (income[0], income[1]),
            _line(page, income[2], income[3]),
            _line(page, income[4], income[5]),
            topology,
            page=page,
        ),
        _mapping(
            "EXPENSE_TRADING_SECURITIES",
            1190,
            (expense[0], expense[1]),
            _line(page, expense[2], expense[3]),
            _line(page, expense[4], expense[5]),
            topology,
            page=page,
        ),
        _mapping(
            "PROVISION_TRADING_SECURITIES",
            1191,
            (provision[0], provision[1]),
            provision[2],
            provision[3],
            topology,
            page=page,
        ),
    ]


def _review_documents() -> list[dict[str, Any]]:
    trailing = "INCOME_EXPENSE_PROVISION_THEN_UNLABELLED_NET_TWO_PERIOD_LANES"
    return [
        _mapped_document(
            "ACB",
            24,
            "2026-06-30",
            trailing,
            [(24, 61, "Đến"), (24, 62, "Đến"), (24, 63, "30.6.2026"), (24, 64, "30.6.2025")],
            [(24, 65, "Triệu đồng"), (24, 66, "Triệu đồng")],
            _four_rows(
                24,
                (
                    60,
                    "LÃI/(LỖ) THUẦN TỪ MUA BÁN CHỨNG KHOÁN KINH DOANH",
                    77,
                    "226.898",
                    78,
                    "60.389",
                ),
                (67, "Thu nhập từ mua bán chứng khoán kinh doanh", 68, "365.141", 69, "218.552"),
                (70, "Chi phí về mua bán chứng khoán kinh doanh", 71, "(129.873)", 72, "(104.457)"),
                (
                    73,
                    "Hoàn nhập/(Trích lập) dự phòng rủi ro chứng khoán kinh doanh",
                    _line(24, 75, "(8.370)"),
                    _line(24, 76, "(53.706)"),
                ),
                trailing,
            ),
        ),
        _mapped_document(
            "MBB",
            47,
            "2026-06-30",
            "WRAPPED_INNER_OWNER_UNDER_SHARED_TRADING_AND_INVESTMENT_UMBRELLA",
            [
                (47, 31, "Từ 01/01/2026"),
                (47, 32, "Từ 01/01/2025"),
                (47, 33, "đến 30/06/2026"),
                (47, 34, "đến 30/06/2025"),
            ],
            [(47, 35, "Triệu đồng"), (47, 36, "Triệu đồng")],
            _four_rows(
                47,
                (
                    37,
                    "Lãi/(lỗ) thuần từ mua bán chứng khoán kinh doanh",
                    49,
                    "249.524",
                    50,
                    "415.700",
                ),
                (39, "Thu nhập từ mua bán chứng khoán kinh doanh", 40, "630.564", 41, "580.842"),
                (42, "Chi về mua bán chứng khoán kinh doanh", 43, "(385.263)", 44, "(132.711)"),
                (
                    45,
                    "(Trích lập)/hoàn nhập dự phòng rủi ro chứng khoán kinh doanh",
                    _line(47, 47, "4.223"),
                    _line(47, 48, "(32.431)"),
                ),
                "WRAPPED_INNER_OWNER_UNDER_SHARED_TRADING_AND_INVESTMENT_UMBRELLA",
            ),
        ),
        _mapped_document(
            "VPB",
            63,
            "2026-03-31",
            "Q1_THREE_MONTH_DURATION_WITH_WRAPPED_PERIOD_HEADERS",
            [
                (63, 44, "Cho kỳ kế toán"),
                (63, 45, "Cho kỳ kế toán"),
                (63, 48, "ngày 31 tháng 3"),
                (63, 49, "ngày 31 tháng 3"),
                (63, 50, "năm 2026"),
                (63, 51, "năm 2025"),
            ],
            [(63, 52, "Triệu đồng"), (63, 53, "Triệu đồng")],
            _four_rows(
                63,
                (43, "LÃI THUẦN TỪ MUA BÁN CHỨNG KHOÁN KINH DOANH", 64, "(224.125)", 65, "184.151"),
                (54, "Thu nhập từ mua bán chứng khoán kinh doanh", 55, "438.077", 56, "259.883"),
                (57, "Chi phí về mua bán chứng khoán kinh doanh", 58, "(318.313)", 59, "(8.090)"),
                (
                    60,
                    "Trích lập dự phòng chứng khoán kinh doanh",
                    _line(63, 62, "(343.889)"),
                    _line(63, 63, "(67.642)"),
                ),
                "Q1_THREE_MONTH_DURATION_WITH_WRAPPED_PERIOD_HEADERS",
            ),
        ),
        _mapped_document(
            "HDB",
            34,
            "2026-06-30",
            "VISIBLE_COMPARATIVE_DASH_AND_SOURCE_LABEL_CAVEAT",
            [(34, 95, "Kỳ này"), (34, 96, "Kỳ trước")],
            [(34, 97, "Triệu VND"), (34, 98, "Triệu VND")],
            _four_rows(
                34,
                (
                    94,
                    "(Lỗ)/Lãi thuần từ hoạt động mua bán chứng khoán kinh doanh",
                    107,
                    "(63.114)",
                    108,
                    "630.635",
                ),
                (99, "Thu nhập từ mua bán chứng khoán kinh doanh", 100, "205.951", 101, "648.456"),
                (
                    102,
                    "Chi phí về mua bán chứng khoán kinh doanh",
                    103,
                    "(90.303)",
                    104,
                    "(17.821)",
                ),
                (
                    105,
                    "Trích lập dự phòng rủi ro chứng khoán đầu tư",
                    _line(34, 106, "(178.762)"),
                    _dash(
                        34,
                        [1495, 2122, 1515, 2140],
                        "14be48364aeceeea4d1b349652f3da5eeb20bafecb2ed6f65f79415f64cff6e9",
                    ),
                ),
                "VISIBLE_COMPARATIVE_DASH_AND_SOURCE_LABEL_CAVEAT",
            ),
            source_label_caveat=(
                "The PDF visibly labels the provision row as investment securities inside the "
                "trading-securities owner block; owner containment, row position, two-period lanes, "
                "and both exact net equations bind it to the trading activity graph."
            ),
        ),
        _mapped_document(
            "VCB",
            39,
            "2026-06-30",
            trailing,
            [
                (39, 35, "từ 1/1/2026"),
                (39, 36, "từ 1/1/2025"),
                (39, 37, "đến 30/6/2026"),
                (39, 38, "đến 30/6/2025"),
            ],
            [(39, 39, "Triệu VND"), (39, 40, "Triệu VND")],
            _four_rows(
                39,
                (32, "Lãi thuần từ mua bán chứng khoán kinh doanh", 51, "87.745", 52, "33.863"),
                (42, "Thu nhập từ mua bán chứng khoán kinh doanh", 43, "159.606", 44, "81.123"),
                (45, "Chi phí về mua bán chứng khoán kinh doanh", 46, "(41.401)", 47, "(40.592)"),
                (
                    48,
                    "Trích lập dự phòng giảm giá chứng khoán kinh doanh",
                    _line(39, 49, "(30.460)"),
                    _line(39, 50, "(6.668)"),
                ),
                trailing,
            ),
        ),
        _mapped_document(
            "CTG",
            45,
            "2026-06-30",
            "PROVISION_VALUES_PRECEDE_LABEL_THEN_LABELLED_NET",
            [
                (45, 67, "từ 01/01/2026 đến"),
                (45, 68, "từ 01/01/2025 đến"),
                (45, 69, "hết 30/06/2026"),
                (45, 70, "hết 30/06/2025"),
            ],
            [(45, 71, "triệu đồng"), (45, 72, "triệu đồng")],
            _four_rows(
                45,
                (
                    82,
                    "Lãi từ hoạt động mua bán chứng khoán kinh doanh",
                    83,
                    "59.310",
                    84,
                    "451.414",
                ),
                (73, "Thu nhập từ mua bán chứng khoán kinh doanh", 74, "73.722", 75, "395.757"),
                (76, "Chi phí về mua bán chứng khoán kinh doanh", 77, "(3.138)", 78, "(18.875)"),
                (
                    81,
                    "Hoàn nhập dự phòng giảm giá chứng khoán kinh doanh",
                    _line(45, 79, "(11.274)"),
                    _line(45, 80, "74.532"),
                ),
                "PROVISION_VALUES_PRECEDE_LABEL_THEN_LABELLED_NET",
            ),
        ),
        _mapped_document(
            "BID",
            29,
            "2026-06-30",
            "DOCUMENT_SECTION_UNIT_INHERITED_FROM_PRECEDING_PAGE",
            [
                (29, 25, "Từ 01/01/2026 đến"),
                (29, 26, "Từ 01/01/2025 đến"),
                (29, 27, "30/06/2026"),
                (29, 28, "30/06/2025"),
            ],
            [(28, 58, "Đơn vị: Triệu VND")],
            _four_rows(
                29,
                (
                    24,
                    "LÃI/LỖ THUẦN TỪ MUA BÁN CHỨNG KHOÁN KINH DOANH",
                    39,
                    "109,012",
                    40,
                    "261,299",
                ),
                (29, "Thu nhập từ mua bán chứng khoán kinh doanh", 30, "439,943", 31, "470,573"),
                (32, "Chi phí về mua bán chứng khoán kinh doanh", 33, "(305,358)", 34, "(210,908)"),
                (
                    35,
                    "(Chi phí)/Hoàn nhập dự phòng rủi ro chứng khoán kinh doanh",
                    _line(29, 36, "(25,573)"),
                    _line(29, 37, "1,634"),
                ),
                "DOCUMENT_SECTION_UNIT_INHERITED_FROM_PRECEDING_PAGE",
            ),
        ),
        _absent(
            "VIB",
            [46],
            "The full report contains a detailed investment-securities activity region on page 46 but no detailed trading-securities income/expense graph; the investment region is a distinct family control.",
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
        raise _error("Codex trading-securities pixel review differs from the fixed ledger")
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


def _pixel_dash_value(crop_page: Mapping[str, Any], ref: Mapping[str, Any]) -> dict[str, Any]:
    payload = support._artifact_bytes(crop_page.get("render_binding"), "page render")
    image = Image.open(io.BytesIO(payload)).convert("RGB")
    left, top, right, bottom = ref["bbox"]
    if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
        raise _error("authenticated pixel dash bbox is out of bounds")
    digest = hashlib.sha256(image.crop((left, top, right, bottom)).tobytes()).hexdigest()
    if digest != ref["pixel_rgb_sha256"]:
        raise _error("authenticated pixel dash crop drifted")
    return {
        "fresh_vietocr_numeric_proposal": None,
        "fresh_vietocr_numeric_status": "NO_SEMANTIC_LINE_FOR_VISIBLE_DASH",
        "normalized_value": 0,
        "page_sequence": ref["page_sequence"],
        "pixel_bbox": list(ref["bbox"]),
        "pixel_rgb_sha256": digest,
        "pixel_transcription": "-",
        "render_ref": canonical_clone_v1(crop_page["render_binding"]),
        "source_line_index": None,
        "source_numeric_challenger": None,
        "source_numeric_challenger_status": (
            "VISIBLE_AUTHENTICATED_PIXEL_DASH_NOT_DETECTED_AS_SOURCE_LINE"
        ),
    }


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "authenticated_pixel_dash_zero_count": sum(
            value.get("source_numeric_challenger_status")
            == "VISIBLE_AUTHENTICATED_PIXEL_DASH_NOT_DETECTED_AS_SOURCE_LINE"
            for trial in trials
            for mapping in trial["verified_mappings"]
            for value in mapping["values"]
        ),
        "detailed_note_not_present_document_count": sum(
            trial["status"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT" for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for trial in trials
        ),
        "fresh_vietocr_numeric_disagreement_count": sum(
            value.get("fresh_vietocr_numeric_status") == "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
            for trial in trials
            for mapping in trial["verified_mappings"]
            for value in mapping["values"]
        ),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "open_source_row_count": 0,
        "q1_source_period_caveat_document_count": sum(
            trial["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            for trial in trials
        ),
        "source_label_caveat_mapping_count": sum(
            trial["source_label_caveat"] is not None for trial in trials
        ),
        "verified_value_cell_count": sum(
            len(mapping["values"]) for trial in trials for mapping in trial["verified_mappings"]
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("trading-securities result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != RESULT_STATE
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("trading-securities result identity or metrics drifted")
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
            raise _error("trading-securities trial shape or status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != RESULT_ID_PREFIX + canonical_json_sha256_v1(material):
        raise _error("trading-securities result identity drifted")
    return canonical_clone_v1(value)


def _equations(by_role: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for axis_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"):

        def value(role: str, *, axis_role: str = axis_role) -> Mapping[str, Any]:
            return next(item for item in by_role[role]["values"] if item["axis_role"] == axis_role)

        term_roles = ["INCOME_TRADING_SECURITIES", "EXPENSE_TRADING_SECURITIES"]
        if "PROVISION_TRADING_SECURITIES" in by_role:
            term_roles.append("PROVISION_TRADING_SECURITIES")
        terms = [value(role) for role in term_roles]
        total = value("NET_TRADING_SECURITIES")
        computed = sum(term["normalized_value"] for term in terms)
        if computed != total["normalized_value"]:
            raise _error(f"trading-securities net equation does not close: {axis_role}")
        result.append(
            {
                "computed_value": computed,
                "equation": (
                    "INCOME_PLUS_EXPENSE_PLUS_PROVISION_EQUALS_NET_TRADING_ACTIVITY"
                    if "PROVISION_TRADING_SECURITIES" in by_role
                    else "INCOME_PLUS_EXPENSE_EQUALS_NET_TRADING_ACTIVITY"
                ),
                "period_role": axis_role,
                "status": "CORROBORATED_EXACT",
                "term_report_norm_ids": [
                    by_role[role]["schema_binding"]["report_norm_id"] for role in term_roles
                ],
                "total_report_norm_id": 1188,
            }
        )
    return result


def _source_period_status(source_period: str) -> str:
    return (
        "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
        if source_period == "2026-03-31"
        else "VERIFIED_SOURCE_PERIOD_Q2_2026"
    )


def build_trading_securities_activity_8bank_codex_verified_mapping_v1(
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
                raise _error("absent detailed trading-securities note unexpectedly matched")
            trials.append(
                {
                    **base,
                    "absence_evidence": canonical_clone_v1(reviewed["absence_evidence"]),
                    "page_span": None,
                    "period_evidence": [],
                    "presentation": reviewed["presentation"],
                    "source_label_caveat": None,
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
            raise _error("reviewed region is not the unique whole-PDF trading graph")
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
            for axis_role, ref in mapping["values"].items():
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
                    evidence = {
                        **evidence,
                        "fresh_vietocr_numeric_status": (
                            "MATCHES_SOURCE_NUMERIC_CHALLENGER"
                            if proposal == evidence["normalized_value"]
                            else "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
                        ),
                        "page_sequence": ref["page_sequence"],
                    }
                elif ref["kind"] == "AUTHENTICATED_RENDER_PIXEL_DASH":
                    evidence = _pixel_dash_value(crop_page, ref)
                else:
                    raise _error("trading-securities value reference kind drifted")
                values.append({"axis_role": axis_role, **evidence})
            verified_mappings.append(
                {
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
            )
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
                "source_label_caveat": reviewed["source_label_caveat"],
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
            "family_root_report_norm_id": 1188,
            "mapped_report_norm_ids": sorted(_SCHEMA_EXPECTED),
            "unobserved_optional_report_norm_ids": [1192],
        },
        "state": RESULT_STATE,
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def validate_trading_securities_activity_8bank_codex_verified_mapping_replay_v1(
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
    rebuilt = build_trading_securities_activity_8bank_codex_verified_mapping_v1(
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
        raise _error("trading-securities verified mapping does not replay exactly")
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


def build_live_trading_securities_activity_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_live_trading_securities_activity_full_document_scan_v1()
    review, review_sha = _stable_json(REVIEW_PATH)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return build_trading_securities_activity_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )


def validate_live_trading_securities_activity_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_live_trading_securities_activity_full_document_scan_v1()
    review, review_sha = _stable_json(REVIEW_PATH)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return validate_trading_securities_activity_8bank_codex_verified_mapping_replay_v1(
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
            RESULT_PATH, build_live_trading_securities_activity_8bank_codex_verified_mapping_v1()
        )
    if args.validate_result:
        result, _ = _stable_json(RESULT_PATH)
        validate_live_trading_securities_activity_8bank_codex_verified_mapping_v1(result)


if __name__ == "__main__":
    main()
