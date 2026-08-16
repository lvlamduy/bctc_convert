"""Verify disclosed end-period exchange rates across the fixed eight-report panel."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import re
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
        raise RuntimeError(f"cannot load exchange-rate support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


scanner = _load(
    "exchange_rate_scan_for_verified_mapping",
    "scan_exchange_rate_full_document_vietocr_v1.py",
)
support = _load(
    "trading_securities_support_for_exchange_rate",
    "build_trading_securities_8bank_codex_verified_mapping_v1.py",
)
matcher = scanner._load_matcher()

FORMAT_VERSION = "EXCHANGE_RATE_8BANK_CODEX_VERIFIED_MAPPING_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_BANK_BLIND_EXCHANGE_"
    "RATE_GRAPH_VISIBLE_PDF_PADDLEOCR_OR_NATIVE_NUMERIC_CHALLENGER_PERIOD_"
    "UNIT_OR_DOCUMENT_VND_POLICY_GEOMETRY_AND_LIVE_TM_SCHEMA_ONLY_"
    "OUT_OF_SCHEMA_CURRENCIES_RETAINED_NO_EXPORT_AUTHORITY"
)
RESULT_PATH = Path("docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json")
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = scanner.EXPECTED_INDEX_SHA256
EXPECTED_CROP_MANIFEST_SHA256 = "a9f80cf9104af1177ba43d8a85de00b28c735223a91b663a5a79401bb038d94e"
EXPECTED_AXIS_SHA256 = scanner.EXPECTED_AXIS_SHA256
EXPECTED_SCAN_ID = "erfdsv1:scan:6d9d93df41596c681a2edaf32d0d1e8a5648f50d64450d6d72ead65b6968c67b"

_SCHEMA = {
    "USD": (5936, "USD", 1706),
    "EUR": (5937, "EUR", 1707),
    "GBP": (5938, "GBP", 1708),
    "JPY": (5939, "JPY", 1709),
    "CHF": (5940, "CHF", 1710),
    "AUD": (5941, "AUD", 1711),
    "CAD": (5942, "CAD", 1712),
    "SGD": (5943, "SGD", 1713),
    "THB": (5944, "THB", 1714),
    "SEK": (5945, "SEK", 1715),
}
_AUTHORITY = {
    "accounting_equation_applicable": False,
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "complete_pdf_scanned_for_every_document": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_visible_supported_currency_rows": True,
    "old_ocr_used_as_semantic_anchor": False,
    "out_of_schema_source_rows_discarded": False,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "text_similarity_alone_used_for_mapping": False,
    "whole_pdf_uniqueness_replayed": True,
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


class ExchangeRate8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixels, rate values, axes, or schema evidence drifted."""


def _error(message: str) -> ExchangeRate8BankCodexVerifiedMappingV1Error:
    return ExchangeRate8BankCodexVerifiedMappingV1Error(message)


def _row(
    code: str,
    label: int,
    current: int,
    current_text: str,
    comparative: int,
    comparative_text: str,
) -> dict[str, Any]:
    return {
        "code": code,
        "comparative": {"line_index": comparative, "pixel_transcription": comparative_text},
        "current": {"line_index": current, "pixel_transcription": current_text},
        "label": {"line_index": label, "pixel_transcription": code if code != "XAU" else "Vàng"},
    }


def _ref(line: int, text: str) -> dict[str, Any]:
    return {"line_index": line, "pixel_transcription": text}


def _absence(code: str) -> dict[str, Any]:
    return {
        "absence_evidence": {
            "complete_pdf_pages_scanned": True,
            "complete_region_count": 0,
            "reason": (
                "No exchange-rate disclosure region containing the exchange-rate owner, "
                "current/comparative period axes, VND/dong context or a bound VND policy link, "
                "and at least two geometrically aligned currency rows was found in the report."
            ),
            "source_scope_absence_only": True,
        },
        "bank_code": code,
        "owner": [],
        "page_sequence": None,
        "period_axis": None,
        "rows": [],
        "source_period_status": None,
        "unit_evidence": [],
    }


def _review_documents() -> list[dict[str, Any]]:
    documents = [_absence("ACB")]
    documents.append(
        {
            "absence_evidence": None,
            "bank_code": "MBB",
            "owner": [_ref(0, "6. Tỷ giá một số ngoại tệ tại thời điểm lập báo cáo:")],
            "page_sequence": 61,
            "period_axis": {
                "comparative": [_ref(2, "31/12/2025")],
                "current": [_ref(1, "30/06/2026")],
            },
            "rows": [
                _row("USD", 5, 6, "26.300,00", 7, "26.290,00"),
                _row("EUR", 8, 9, "30.074,50", 10, "30.945,00"),
                _row("GBP", 11, 12, "34.866,50", 13, "35.443,00"),
                _row("JPY", 14, 15, "162,59", 16, "168,88"),
                _row("CHF", 17, 18, "32.660,50", 19, "33.195,00"),
                _row("AUD", 20, 21, "18.149,00", 22, "17.641,00"),
                _row("CAD", 23, 24, "18.547,00", 25, "19.250,50"),
                _row("SGD", 26, 27, "20.360,50", 28, "20.505,50"),
                _row("THB", 29, 30, "799,62", 31, "841,86"),
                _row("SEK", 32, 33, "2.727,12", 34, "2.879,53"),
            ],
            "source_period_status": "VERIFIED_SOURCE_PERIOD_Q2_2026",
            "unit_evidence": [_ref(3, "đồng"), _ref(4, "đồng")],
        }
    )
    documents.append(
        {
            "absence_evidence": None,
            "bank_code": "VPB",
            "owner": [
                _ref(10, "TỶ GIÁ MỘT SỐ LOẠI NGOẠI TỆ VÀ VÀNG SO VỚI VND VÀO THỜI ĐIỂM CUỐI KỲ KẾ"),
                _ref(11, "TOÁN"),
            ],
            "page_sequence": 90,
            "period_axis": {
                "comparative": [_ref(13, "Ngày 31 tháng"), _ref(15, "12 năm 2025")],
                "current": [_ref(12, "Ngày 31 tháng 3"), _ref(14, "năm 2026")],
            },
            "rows": [
                _row("AUD", 18, 19, "18.131", 20, "17.627"),
                _row("CAD", 21, 22, "18.923", 23, "19.224"),
                _row("CHF", 24, 25, "32.934", 26, "33.149"),
                _row("CNY", 27, 28, "3.814", 29, "3.761"),
                _row("DKK", 30, 31, "3.160", 32, "3.160"),
                _row("EUR", 33, 34, "30.298", 35, "30.982"),
                _row("GBP", 36, 37, "34.855", 38, "35.413"),
                _row("JPY", 39, 40, "166", 41, "169"),
                _row("NZD", 42, 43, "15.106", 44, "15.211"),
                _row("SEK", 45, 46, "3.078", 47, "3.078"),
                _row("SGD", 48, 49, "20.469", 50, "20.501"),
                _row("THB", 51, 52, "640", 53, "640"),
                _row("USD", 54, 55, "26.268", 56, "26.319"),
                _row("XAU", 57, 58, "17.450.000", 59, "15.355.000"),
            ],
            "source_period_status": "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2",
            "unit_evidence": [_ref(16, "VND"), _ref(17, "VND")],
        }
    )
    documents.append(_absence("HDB"))
    documents.append(_absence("VCB"))
    documents.append(
        {
            "absence_evidence": None,
            "bank_code": "CTG",
            "owner": [_ref(4, "TỶ GIÁ MỘT SỐ LOẠI NGOẠI TỆ VÀO THỜI ĐIỂM CUỐI KỲ")],
            "page_sequence": 61,
            "period_axis": {
                "comparative": [_ref(6, "31/12/2025")],
                "current": [_ref(5, "30/06/2026")],
            },
            "rows": [
                _row("USD", 9, 10, "26.307", 11, "26.295"),
                _row("EUR", 12, 13, "29.964", 14, "30.853"),
                _row("GBP", 15, 16, "34.808", 17, "35.330"),
                _row("CHF", 18, 19, "32.476", 20, "33.142"),
                _row("JPY", 21, 22, "162,09", 23, "167,90"),
                _row("SGD", 24, 25, "20.317", 26, "20.442"),
                _row("CAD", 27, 28, "18.475", 29, "19.186"),
                _row("AUD", 30, 31, "18.103", 32, "17.574"),
                _row("NZD", 33, 34, "14.873", 35, "15.164"),
                _row("THB", 36, 37, "791,67", 38, "832,78"),
                _row("SEK", 39, 40, "2.700", 41, "2.854"),
                _row("NOK", 42, 43, "2.652", 44, "2.611"),
                _row("DKK", 45, 46, "4.009", 47, "4.131"),
                _row("HKD", 48, 49, "3.355", 50, "3.378"),
                _row("CNY", 51, 52, "3.877", 53, "3.762"),
                _row("KRW", 54, 55, "17,42", 56, "18,67"),
                _row("LAK", 57, 58, "1,18", 59, "1,22"),
            ],
            "source_period_status": "VERIFIED_SOURCE_PERIOD_Q2_2026",
            "unit_evidence": [_ref(7, "đồng"), _ref(8, "đồng")],
        }
    )
    documents.append(
        {
            "absence_evidence": None,
            "bank_code": "BID",
            "owner": [_ref(5, "24. TỶ GIÁ MỘT SỐ LOẠI NGOẠI TỆ VÀO THỜI ĐIỂM CUỐI KỲ BÁO CÁO")],
            "page_sequence": 35,
            "period_axis": {
                "comparative": [_ref(8, "31/12/2025")],
                "current": [_ref(7, "30/06/2026")],
            },
            "rows": [
                _row("USD", 9, 10, "26,286", 11, "26,290"),
                _row("EUR", 12, 13, "30,203", 14, "31,046"),
                _row("GBP", 15, 16, "34,894", 17, "35,437"),
                _row("CHF", 18, 19, "32,676", 20, "33,282"),
                _row("JPY", 21, 22, "162.72", 23, "168.72"),
                _row("SGD", 24, 25, "20,350", 26, "20,449"),
                _row("CAD", 27, 28, "18,531", 29, "19,219"),
                _row("AUD", 30, 31, "18,155", 32, "17,616"),
            ],
            "source_period_status": "VERIFIED_SOURCE_PERIOD_Q2_2026",
            "unit_evidence": [
                {
                    "kind": "DOCUMENT_POLICY_VND_REFERENCE",
                    "lines": [
                        {"line_index": 33, "page_sequence": 13},
                        {"line_index": 34, "page_sequence": 13},
                        {"line_index": 35, "page_sequence": 13},
                    ],
                    "pixel_transcription": (
                        "Tài sản và công nợ có nguồn gốc ngoại tệ được quy đổi sang VNĐ theo tỷ giá "
                        "bình quân mua và bán ngoại tệ giao ngay; xem chi tiết tỷ giá tại Thuyết minh số 24."
                    ),
                }
            ],
        }
    )
    documents.append(
        {
            "absence_evidence": None,
            "bank_code": "VIB",
            "owner": [
                _ref(
                    5,
                    "TỶ GIÁ MỘT SỐ LOẠI NGOẠI TỆ SO VỚI VND TẠI THỜI ĐIỂM KẾT THÚC GIAI ĐOẠN TÀI CHÍNH",
                )
            ],
            "page_sequence": 71,
            "period_axis": {
                "comparative": [_ref(7, "31/12/2025")],
                "current": [_ref(6, "30/06/2026")],
            },
            "rows": [
                _row("AUD", 10, 11, "18.157,50", 12, "17.622,00"),
                _row("CAD", 13, 14, "18.539,50", 15, "19.241,00"),
                _row("CHF", 16, 17, "32.553,50", 18, "33.206,50"),
                _row("DKK", 19, 20, "3.951,00", 21, "4.150,00"),
                _row("EUR", 22, 23, "30.120,00", 24, "30.894,50"),
                _row("GBP", 25, 26, "34.860,50", 27, "35.401,00"),
                _row("HKD", 28, 29, "3.304,00", 30, "3.394,00"),
                _row("JPY", 31, 32, "162,36", 33, "168,46"),
                _row("NOK", 34, 35, "2.620,00", 36, "2.620,50"),
                _row("SGD", 37, 38, "20.341,50", 39, "20.481,00"),
                _row("USD", 40, 41, "26.318,00", 42, "26.288,50"),
                _row("XAU", 43, 44, "500,00", 45, "500,00"),
            ],
            "source_period_status": "VERIFIED_SOURCE_PERIOD_Q2_2026",
            "unit_evidence": [_ref(8, "đồng"), _ref(9, "đồng")],
        }
    )
    return documents


def _review_id() -> str:
    material = {
        "documents": _review_documents(),
        "reviewer": {"kind": "CODEX_INDEPENDENT_VISIBLE_PDF_REVIEW", "review_run_id": "E-0104"},
        "scan_id": EXPECTED_SCAN_ID,
    }
    return "e0104:pixel-review:" + canonical_json_sha256_v1(material)


def _document(items: Any, code: str, label: str) -> dict[str, Any]:
    return support._document_by_code(items, code, label)


def _page(document: Mapping[str, Any], page: int, label: str) -> dict[str, Any]:
    return support._page_by_number(document, page, label)


def _rate_cents(value: Any) -> int:
    if type(value) is not str or value != value.strip() or not value:
        raise _error(f"visible exchange-rate transcription is invalid: {value!r}")
    if re.fullmatch(r"[0-9]+(?:[.,][0-9]+)*", value) is None:
        raise _error(f"visible exchange-rate digits drifted: {value!r}")
    groups = re.split(r"[.,]", value)
    separators = re.findall(r"[.,]", value)
    if not separators:
        return int(groups[0]) * 100
    decimal = len(groups[-1]) in {1, 2}
    if decimal:
        whole = "".join(groups[:-1])
        fraction = groups[-1].ljust(2, "0")
        return int(whole) * 100 + int(fraction)
    if any(len(group) != 3 for group in groups[1:]):
        raise _error(f"exchange-rate separator grouping drifted: {value!r}")
    return int("".join(groups)) * 100


def _decimal(cents: int) -> str:
    return f"{cents // 100}.{cents % 100:02d}"


def _axis_line(page: Mapping[str, Any], index: int) -> dict[str, Any]:
    lines = page.get("lines")
    if type(lines) is not list or not 0 <= index < len(lines):
        raise _error("fresh semantic line index drifted")
    line = lines[index]
    if type(line) is not dict or line.get("source_line_index") != index:
        raise _error("fresh semantic line identity drifted")
    return line


def _bound_line(
    axis_page: Mapping[str, Any],
    semantic_page: Mapping[str, Any],
    crop_page: Mapping[str, Any],
    source_axis: Sequence[str],
    line_index: int,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    axis = _axis_line(axis_page, line_index)
    semantic = _axis_line(semantic_page, line_index)
    if (
        semantic.get("vietocr_text") != axis.get("vietocr_text")
        or type(semantic.get("crop_ref")) is not dict
        or type(semantic.get("sample_id")) is not str
        or not 0 <= line_index < len(source_axis)
    ):
        raise _error("semantic/crop/source line binding drifted")
    first = crop_page.get("sample_offset_start")
    stop = crop_page.get("sample_offset_stop")
    if type(first) is not int or type(stop) is not int:
        raise _error("crop page sample offsets drifted")
    ordinal = first + line_index + 1
    sample_id = f"sample-{ordinal:08d}"
    crop_ref = semantic["crop_ref"]
    if (
        semantic["sample_id"] != sample_id
        or not first <= ordinal - 1 < stop
        or type(crop_ref.get("path")) is not str
        or not crop_ref["path"].endswith(f"/{sample_id}.png")
    ):
        raise _error("crop sample identity drifted")
    return axis, semantic, source_axis[line_index]


def _source_code(value: str) -> str | None:
    if matcher._accentless(value).startswith("vang"):
        return "XAU"
    token = re.sub(r"[^A-Za-z]", "", value).upper()
    return token if token in matcher.KNOWN_SOURCE_CODES else None


def _label_evidence(
    axis_page: Mapping[str, Any],
    semantic_page: Mapping[str, Any],
    crop_page: Mapping[str, Any],
    source_axis: Sequence[str],
    row: Mapping[str, Any],
) -> dict[str, Any]:
    ref = row["label"]
    axis, semantic, source_text = _bound_line(
        axis_page, semantic_page, crop_page, source_axis, ref["line_index"]
    )
    expected = row["code"]
    if (
        _source_code(source_text) != expected
        or _source_code(ref["pixel_transcription"]) != expected
    ):
        raise _error("visible pixel/source currency label disagrees with reviewed code")
    fresh_match = matcher._code(axis)
    return {
        "crop_ref": canonical_clone_v1(semantic["crop_ref"]),
        "fresh_vietocr_label": axis["vietocr_text"],
        "fresh_vietocr_label_status": (
            fresh_match[1]
            if fresh_match is not None and fresh_match[0] == expected
            else "DISAGREES"
        ),
        "pixel_transcription": ref["pixel_transcription"],
        "source_label_challenger": source_text,
        "source_line_index": ref["line_index"],
    }


def _value_evidence(
    axis_page: Mapping[str, Any],
    semantic_page: Mapping[str, Any],
    crop_page: Mapping[str, Any],
    source_axis: Sequence[str],
    ref: Mapping[str, Any],
) -> dict[str, Any]:
    axis, semantic, source_text = _bound_line(
        axis_page, semantic_page, crop_page, source_axis, ref["line_index"]
    )
    expected = _rate_cents(ref["pixel_transcription"])
    if _rate_cents(source_text) != expected:
        raise _error("visible pixel rate and source numeric challenger disagree")
    try:
        fresh = _rate_cents(axis["vietocr_text"])
    except ExchangeRate8BankCodexVerifiedMappingV1Error:
        fresh = None
    return {
        "crop_ref": canonical_clone_v1(semantic["crop_ref"]),
        "fresh_vietocr_numeric_proposal": axis["vietocr_text"],
        "fresh_vietocr_numeric_status": (
            "NORMALIZES_TO_SOURCE_NUMERIC_CHALLENGER" if fresh == expected else "DISAGREES"
        ),
        "fresh_vietocr_surface_status": (
            "EXACT_SOURCE_SURFACE" if axis["vietocr_text"] == source_text else "SURFACE_DIFFERS"
        ),
        "normalized_decimal": _decimal(expected),
        "normalized_value_cents": expected,
        "pixel_transcription": ref["pixel_transcription"],
        "source_line_index": ref["line_index"],
        "source_numeric_challenger": source_text,
        "source_numeric_challenger_status": "MATCHED_VISIBLE_PIXEL_TRANSCRIPTION",
    }


def _schema_binding(item: Any, code: str) -> dict[str, Any]:
    schema_id, name, display_order = _SCHEMA[code]
    if (
        item is None
        or item.statement_type != "TM"
        or item.schema_id != schema_id
        or item.canonical_name != name
        or item.parent_id != 5935
        or item.hierarchy_level != 2
        or item.display_order != display_order
    ):
        raise _error(f"exchange-rate mapping does not bind live schema row for {code}")
    return {
        "canonical_name": item.canonical_name,
        "display_order": item.display_order,
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def _schema_family(item: Any) -> dict[str, Any]:
    if (
        item is None
        or item.statement_type != "TM"
        or item.schema_id != 5935
        or item.canonical_name != "Tỷ giá một số ngoại tệ tại thời điểm lập báo cáo"
        or item.parent_id != 1259
        or item.hierarchy_level != 1
        or item.display_order != 1705
    ):
        raise _error("exchange-rate schema family root drifted")
    return {
        "canonical_name": item.canonical_name,
        "display_order": item.display_order,
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    mappings = [item for trial in trials for item in trial["verified_mappings"]]
    source_only = [item for trial in trials for item in trial["verified_source_only_rows"]]
    all_rows = [*mappings, *source_only]
    return {
        "detailed_table_not_present_document_count": sum(
            trial["status"] == "CONFIRMED_DETAILED_TABLE_NOT_PRESENT_IN_BOUND_REPORT"
            for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for trial in trials
        ),
        "fresh_vietocr_label_disagreement_count": sum(
            row["label_evidence"]["fresh_vietocr_label_status"] == "DISAGREES" for row in all_rows
        ),
        "fresh_vietocr_label_fuzzy_recovery_count": sum(
            row["label_evidence"]["fresh_vietocr_label_status"]
            == "UNIQUE_EDIT_DISTANCE_ONE_FRESH_VIETOCR_CODE"
            for row in all_rows
        ),
        "fresh_vietocr_numeric_normalized_disagreement_count": sum(
            value["fresh_vietocr_numeric_status"] == "DISAGREES"
            for row in all_rows
            for value in row["values"]
        ),
        "fresh_vietocr_numeric_surface_disagreement_count": sum(
            value["fresh_vietocr_surface_status"] == "SURFACE_DIFFERS"
            for row in all_rows
            for value in row["values"]
        ),
        "mapping_verified_count": len(mappings),
        "out_of_schema_source_row_count": len(source_only),
        "q1_source_period_caveat_document_count": sum(
            trial["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            for trial in trials
        ),
        "verified_source_value_cell_count": sum(len(row["values"]) for row in all_rows),
        "verified_value_cell_count": sum(len(row["values"]) for row in mappings),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("exchange-rate result fields drifted")
    trials = value["trials"]
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "EXCHANGE_RATE_8BANK_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(trials) is not list
        or len(trials) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(trials))
    ):
        raise _error("exchange-rate result identity or metrics drifted")
    allowed = {
        "CONFIRMED_DETAILED_TABLE_NOT_PRESENT_IN_BOUND_REPORT",
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX_WITH_INHERITED_VND_POLICY_EVIDENCE",
        "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT_AND_UNRESOLVED_SCHEMA_ROWS",
        "VERIFIED_BY_CODEX_WITH_UNRESOLVED_SCHEMA_ROWS",
    }
    for ordinal, (trial, code) in enumerate(zip(trials, EXPECTED_DOCUMENT_ORDER, strict=True), 1):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or trial.get("status") not in allowed
            or any(item.get("status") != "VERIFIED_BY_CODEX" for item in trial["verified_mappings"])
            or any(
                item.get("status") != "UNRESOLVED_SCHEMA_GAP_SOURCE_ROW_RETAINED"
                for item in trial["verified_source_only_rows"]
            )
        ):
            raise _error("exchange-rate trial shape or status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "e0104:result:" + canonical_json_sha256_v1(material):
        raise _error("exchange-rate result ID drifted")
    return canonical_clone_v1(value)


def build_exchange_rate_8bank_codex_verified_mapping_v1(
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    schema_authority: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
) -> dict[str, Any]:
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    scanner.validate_exchange_rate_full_document_scan_replay_v1(structure_scan, semantic_index)
    if (
        axis.get("semantic_axis_sha256") != EXPECTED_AXIS_SHA256
        or structure_scan.get("scan_id") != EXPECTED_SCAN_ID
        or type(crop_manifest) is not dict
        or crop_manifest_sha256 != EXPECTED_CROP_MANIFEST_SHA256
    ):
        raise _error("fixed exchange-rate input authority drifted")
    reviewed_documents = _review_documents()
    trials = []
    gap_counter = 0
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        review = next(item for item in reviewed_documents if item["bank_code"] == code)
        scan_trial = _document(structure_scan["trials"], code, "structure scan")
        matcher_result = scan_trial["matcher_result"]
        common = {
            "document_ordinal": ordinal,
            "document_provenance": code,
            "source_pdf_sha256": scan_trial["source_pdf_sha256"],
        }
        if review["absence_evidence"] is not None:
            if matcher_result["metrics"]["complete_region_count"] != 0:
                raise _error("reviewed exchange-rate absence conflicts with full-document scan")
            trials.append(
                {
                    **common,
                    "absence_evidence": canonical_clone_v1(review["absence_evidence"]),
                    "owner": [],
                    "page_sequence": None,
                    "period_axis": None,
                    "source_period_status": None,
                    "status": "CONFIRMED_DETAILED_TABLE_NOT_PRESENT_IN_BOUND_REPORT",
                    "unit_evidence": [],
                    "verified_mappings": [],
                    "verified_source_only_rows": [],
                    "whole_document_uniqueness": canonical_clone_v1(matcher_result["uniqueness"]),
                }
            )
            continue
        complete = [item for item in matcher_result["regions"] if item["status"] == "COMPLETE"]
        if len(complete) != 1 or complete[0]["page_sequence"] != review["page_sequence"]:
            raise _error("reviewed exchange-rate region is not the unique structural match")
        region = complete[0]
        expected_rows = [
            {
                "code": row["code"],
                "comparative_line_index": row["comparative"]["line_index"],
                "current_line_index": row["current"]["line_index"],
                "label_line_index": row["label"]["line_index"],
                "supported_schema_code": row["code"] in _SCHEMA,
            }
            for row in review["rows"]
        ]
        actual_rows = [{key: row[key] for key in expected_rows[0]} for row in region["rows"]]
        if not same_typed_json_v1(actual_rows, expected_rows):
            raise _error("exchange-rate full-document graph and pixel review row axes differ")
        axis_document = _document(axis["documents"], code, "accounting axis")
        semantic_document = next(
            item for item in semantic_index["documents"] if item.get("bank_code") == code
        )
        crop_document = next(
            item for item in crop_manifest["documents"] if item.get("bank_code") == code
        )
        page_number = review["page_sequence"]
        axis_page = _page(axis_document, page_number, "accounting axis")
        semantic_page = _page(semantic_document, page_number, "semantic index")
        crop_page = _page(crop_document, page_number, "crop manifest")
        source_axis = support._source_line_axis(crop_page)
        mappings = []
        source_only = []
        for row in review["rows"]:
            label_evidence = _label_evidence(axis_page, semantic_page, crop_page, source_axis, row)
            values = [
                {
                    "axis": "CURRENT_PERIOD",
                    **_value_evidence(
                        axis_page, semantic_page, crop_page, source_axis, row["current"]
                    ),
                },
                {
                    "axis": "COMPARATIVE_PERIOD",
                    **_value_evidence(
                        axis_page, semantic_page, crop_page, source_axis, row["comparative"]
                    ),
                },
            ]
            if row["code"] in _SCHEMA:
                schema_id = _SCHEMA[row["code"]][0]
                mappings.append(
                    {
                        "code": row["code"],
                        "label_evidence": label_evidence,
                        "schema_binding": _schema_binding(schema_by_id.get(schema_id), row["code"]),
                        "status": "VERIFIED_BY_CODEX",
                        "values": values,
                    }
                )
            else:
                gap_counter += 1
                source_only.append(
                    {
                        "code": row["code"],
                        "gap_id": f"FXRATE-{gap_counter:03d}",
                        "label_evidence": label_evidence,
                        "reason": "NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD",
                        "status": "UNRESOLVED_SCHEMA_GAP_SOURCE_ROW_RETAINED",
                        "values": values,
                    }
                )
        if code == "VPB":
            status = "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT_AND_UNRESOLVED_SCHEMA_ROWS"
        elif code == "BID":
            status = "VERIFIED_BY_CODEX_WITH_INHERITED_VND_POLICY_EVIDENCE"
        elif source_only:
            status = "VERIFIED_BY_CODEX_WITH_UNRESOLVED_SCHEMA_ROWS"
        else:
            status = "VERIFIED_BY_CODEX"
        trials.append(
            {
                **common,
                "absence_evidence": None,
                "owner": canonical_clone_v1(review["owner"]),
                "page_sequence": page_number,
                "period_axis": canonical_clone_v1(review["period_axis"]),
                "source_period_status": review["source_period_status"],
                "status": status,
                "unit_evidence": canonical_clone_v1(review["unit_evidence"]),
                "verified_mappings": mappings,
                "verified_source_only_rows": source_only,
                "whole_document_uniqueness": canonical_clone_v1(matcher_result["uniqueness"]),
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
            "pixel_review_id": _review_id(),
            "semantic_axis_sha256": axis["semantic_axis_sha256"],
            "semantic_index": {
                "path": SEMANTIC_INDEX_PATH.as_posix(),
                "sha256": EXPECTED_INDEX_SHA256,
            },
            "structure_scan_id": structure_scan["scan_id"],
            "tm_schema_projection_sha256": schema_authority["tm_schema_projection_sha256"],
        },
        "metrics": _metrics(trials),
        "schema_family": _schema_family(schema_by_id.get(5935)),
        "state": "EXCHANGE_RATE_8BANK_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "e0104:result:" + canonical_json_sha256_v1(material)}
    )


def validate_exchange_rate_8bank_codex_verified_mapping_replay_v1(
    value: Any,
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    schema_authority: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_exchange_rate_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_manifest_sha256,
    )
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("exchange-rate verified mapping does not replay exactly")
    return supplied


def _stable_json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], str]:
    payload = support._stable_bytes(path)
    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise _error(f"fixed JSON bytes drifted: {path}")
    value = support._strict_json(payload, path.as_posix())
    if type(value) is not dict:
        raise _error("fixed JSON root must be one object")
    return value, digest


def _live_inputs() -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_exchange_rate_full_document_scan_v1(semantic_index)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return {
        "crop_manifest": crop_manifest,
        "crop_manifest_sha256": crop_sha,
        "schema_authority": schema_authority,
        "schema_by_id": schema_by_id,
        "semantic_index": semantic_index,
        "structure_scan": structure_scan,
    }


def build_live_exchange_rate_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    return build_exchange_rate_8bank_codex_verified_mapping_v1(**_live_inputs())


def validate_live_exchange_rate_8bank_codex_verified_mapping_v1(value: Any) -> dict[str, Any]:
    return validate_exchange_rate_8bank_codex_verified_mapping_replay_v1(value, **_live_inputs())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-result", action="store_true")
    parser.add_argument("--validate-result", action="store_true")
    args = parser.parse_args()
    if args.write_result == args.validate_result:
        parser.error("choose exactly one of --write-result or --validate-result")
    if args.write_result:
        destination = PROJECT_ROOT / RESULT_PATH
        if destination.exists():
            raise _error(f"refusing to overwrite existing exchange-rate result: {RESULT_PATH}")
        destination.write_bytes(
            canonical_json_bytes_v1(build_live_exchange_rate_8bank_codex_verified_mapping_v1())
        )
        return
    result, _ = _stable_json(RESULT_PATH)
    validate_live_exchange_rate_8bank_codex_verified_mapping_v1(result)


if __name__ == "__main__":
    main()
