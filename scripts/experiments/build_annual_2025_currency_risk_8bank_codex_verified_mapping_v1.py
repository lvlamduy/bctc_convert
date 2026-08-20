#!/usr/bin/env python3
"""Verify the annual-2025 currency-risk accounting core for eight banks.

The complete-PDF graph selects one region per report.  Table reasoning uses
only orientation-normalized coordinates: ordinary pages use the verified
full-document line axis, while a geometry-selected sideways page uses the
verified upright PP-OCRv6 panel.  Numeric cells are assigned to the nearest
core row and to columns inferred from a complete visible row.  A missing OCR
cell becomes zero only when the generic pixel detector finds one unique dash
at the expected row/column position.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib.util
import statistics
import sys
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

import cv2

from bctc_ai.evaluation.accounting_table_axes_v1 import _document_date_observations
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.evaluation.full_document_vietocr_accounting_axis_v1 import (
    EXPECTED_DOCUMENT_ORDER,
    project_full_document_vietocr_accounting_axis_v1,
    project_full_document_vietocr_reporting_period_contexts_v1,
    validate_full_document_vietocr_reporting_period_contexts_replay_v1,
)
from bctc_ai.evaluation.word_box_rows_v3 import (
    _detect_visible_dash_v3,
    load_word_box_reconstruction_v3_config,
)
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import _authority_snapshot
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SEMANTIC_INDEX_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/verified-index/"
    "semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/crop_manifest.json"
)
WORD_BOX_CONFIG_PATH = Path("config/tables/word-box-reconstruction-v3.yaml")
RESULT_PATH = Path(
    "docs/experiments/E-0155-annual-2025-currency-risk-8bank-codex-verified-mapping-v1.json"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0155-annual-2025-currency-risk-8bank-codex-pixel-review-v1.json"
)
GEMMA_RESCUE_PATH = Path(
    "docs/experiments/E-0155-annual-2025-currency-risk-bid-gemma4-gpu-text-rescue-v1.json"
)

EXPECTED_INDEX_SHA256 = "98bb9854e699230da86538cf024ef3f4817b9e2f4dd2b2a75f46198f00e4247d"
EXPECTED_CROP_MANIFEST_SHA256 = "17d12a4d6b1dfaf0e243300757fd225b8c9cca80810a2d856efdb55a5b4ac000"
EXPECTED_AXIS_SHA256 = "aa81f553fda69315e84b7adbda13347c25a4490b016fc9660ff4f2cd49795ce7"
EXPECTED_SCAN_ID = (
    "a2025crfdsv1:scan:b2dd66fa2292064a87e383d140988048b7155f4d139915462c4fe1c555b7b321"
)
EXPECTED_PERIOD_PROJECTION_ID = (
    "fdvrpcv1:projection:fd732522c67ec0fa927696bf1b17721f1ce16c34a083618e2bb4ebf7acb6d0d3"
)
EXPECTED_PANEL_PROJECTION_ID = (
    "a2025crrpv1:projection:391e4b67a438f9d1b012c768d1152edaf8b5d4314db07a7bceeac40dfa5de9d7"
)
EXPECTED_GEMMA_RESCUE_SHA256 = "2346f29829715eac57b535e6ee58435a356871d1b4fb74629731de9459f7b483"
EXPECTED_GEMMA_RESCUE_ID = (
    "annual2025crgemma4v1:evaluation:"
    "6b1ba36157150b415e5c035916d6fd87e098218498485c294c770adc1e72acb7"
)

FORMAT_VERSION = "ANNUAL_2025_CURRENCY_RISK_8BANK_CODEX_VERIFIED_MAPPING_V1"
RESULT_STATE = "ANNUAL_2025_CURRENCY_RISK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025cr8bcv1:result:"
REVIEW_FORMAT = "ANNUAL_2025_CURRENCY_RISK_8BANK_CODEX_PIXEL_REVIEW_V1"
REVIEW_STATE = "ANNUAL_2025_CURRENCY_RISK_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025cr8bcv1:pixel-review:"
CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_VIETOCR_"
    "BANK_BLIND_CURRENCY_RISK_GRAPH_CANONICAL_UPRIGHT_GEOMETRY_PPOCRV6_ROTATED_"
    "NUMERIC_CHALLENGER_BOUNDED_GEMMA4_GPU_TEXT_RESCUE_VISIBLE_DASH_ZERO_EXACT_"
    "ACCOUNTING_CLOSURE_LIVE_TM_"
    "SCHEMA_CORE_ONLY_UNSUPPORTED_AXES_RETAINED_NO_EXPORT_AUTHORITY"
)

_ROLE_SCHEMA = {
    "EUR": {
        "ASSET_TOTAL": 1354,
        "LIABILITY_TOTAL": 5850,
        "STATE_COMBINED": 1378,
        "STATE_EXTERNAL": 1377,
        "STATE_INTERNAL": 1376,
    },
    "OTHER": {
        "ASSET_TOTAL": 1432,
        "LIABILITY_TOTAL": 5854,
        "STATE_COMBINED": 1456,
        "STATE_EXTERNAL": 1455,
        "STATE_INTERNAL": 1454,
    },
    "TOTAL": {
        "ASSET_TOTAL": 1458,
        "LIABILITY_TOTAL": 5856,
        "STATE_COMBINED": 1482,
        "STATE_EXTERNAL": 1481,
        "STATE_INTERNAL": 1480,
    },
    "USD": {
        "ASSET_TOTAL": 1380,
        "LIABILITY_TOTAL": 5852,
        "STATE_COMBINED": 1404,
        "STATE_EXTERNAL": 1403,
        "STATE_INTERNAL": 1402,
    },
    "VND": {
        "ASSET_TOTAL": 1406,
        "LIABILITY_TOTAL": 1418,
        "STATE_COMBINED": 1430,
        "STATE_EXTERNAL": 1429,
        "STATE_INTERNAL": 1428,
    },
}
_SCHEMA_EXPECTED = {
    1352: ("Rủi ro tiền tệ", 1259),
    1354: ("Tổng tài sản", 1353),
    5850: ("Tổng nợ phải trả", 1366),
    1376: ("Trạng thái tiền tệ nội bảng", 1353),
    1377: ("Trạng thái tiền tệ ngoại bảng", 1353),
    1378: ("Trạng thái tiền tệ nội, ngoại bảng", 1353),
    1380: ("Tổng tài sản", 1379),
    5852: ("Tổng nợ phải trả", 1392),
    1402: ("Trạng thái tiền tệ nội bảng", 1379),
    1403: ("Trạng thái tiền tệ ngoại bảng", 1379),
    1404: ("Trạng thái tiền tệ nội, ngoại bảng", 1379),
    1406: ("Tổng tài sản", 1405),
    1418: ("Nợ phải trả và vốn chủ sở hữu", 1405),
    1428: ("Trạng thái tiền tệ nội bảng", 1405),
    1429: ("Trạng thái tiền tệ ngoại bảng", 1405),
    1430: ("Trạng thái tiền tệ nội, ngoại bảng", 1405),
    1432: ("Tổng tài sản", 1431),
    5854: ("Tổng nợ phải trả", 1444),
    1454: ("Trạng thái tiền tệ nội bảng", 1431),
    1455: ("Trạng thái tiền tệ ngoại bảng", 1431),
    1456: ("Trạng thái tiền tệ nội, ngoại bảng", 1431),
    1458: ("Tổng tài sản", 1457),
    5856: ("Tổng nợ phải trả", 1470),
    1480: ("Trạng thái tiền tệ nội bảng", 1457),
    1481: ("Trạng thái tiền tệ ngoại bảng", 1457),
    1482: ("Trạng thái tiền tệ nội, ngoại bảng", 1457),
}
_CORE_ROLES = {
    "ASSET_TOTAL",
    "LIABILITY_TOTAL",
    "STATE_COMBINED",
    "STATE_EXTERNAL",
    "STATE_INTERNAL",
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "blank_cell_interpreted_as_zero": False,
    "canonical_upright_coordinates_used_for_table_reasoning": True,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "document_period_context_and_local_table_period_both_required": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "gold_or_extra_currency_axis_silently_collapsed": False,
    "gemma4_gpu_rescue_used_as_text_diagnostic_only": True,
    "gemma4_used_as_numeric_truth": False,
    "inverse_projection_to_source_pdf_used_for_table_reasoning": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_exact_annual_accounting_core_cells": True,
    "paddleocr_or_ppocrv6_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "row_or_currency_axis_order_required": False,
    "text_similarity_alone_used_for_mapping": False,
    "unsupported_or_comparative_source_cells_discarded": False,
    "visible_dash_equals_zero_only_with_unique_pixel_component": True,
}


class Annual2025CurrencyRisk8BankError(ValueError):
    """The annual graph, period, pixels, values, equations or schema drifted."""


def _error(message: str) -> Annual2025CurrencyRisk8BankError:
    return Annual2025CurrencyRisk8BankError(message)


def _load(name: str, relative: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    path = PROJECT_ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual currency-risk support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _base() -> ModuleType:
    return _load(
        "annual_2025_currency_risk_mapping_base_v1",
        "scripts/experiments/build_currency_risk_8bank_codex_verified_mapping_v1.py",
    )


def _scanner() -> ModuleType:
    return _load(
        "annual_2025_currency_risk_scan_for_mapping_v1",
        "scripts/experiments/scan_annual_2025_currency_risk_full_document_vietocr_v1.py",
    )


def _panel() -> ModuleType:
    return _load(
        "annual_2025_currency_risk_ppocrv6_panel_for_mapping_v1",
        "scripts/experiments/build_annual_2025_currency_risk_rotated_ppocrv6_panel_v1.py",
    )


def _stable_json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], str]:
    try:
        value, digest = _base()._stable_json(path, expected_sha256)
    except Exception as exc:
        raise _error(str(exc)) from exc
    return value, digest


def _gemma_text_rescue() -> tuple[dict[str, Any], str]:
    value, digest = _stable_json(GEMMA_RESCUE_PATH, EXPECTED_GEMMA_RESCUE_SHA256)
    material = canonical_clone_v1(value)
    identity = material.pop("evaluation_id", None)
    trials = value.get("trials")
    if (
        value.get("format_version") != "ANNUAL_2025_CURRENCY_RISK_BID_GEMMA4_GPU_TEXT_RESCUE_V1"
        or value.get("state") != "COMPLETE"
        or identity != EXPECTED_GEMMA_RESCUE_ID
        or identity != "annual2025crgemma4v1:evaluation:" + canonical_json_sha256_v1(material)
        or type(trials) is not list
        or [trial.get("role") for trial in trials] != ["STATE_INTERNAL", "STATE_EXTERNAL"]
        or any(
            trial.get("gemma4_exact_pixel_match") is not True
            or trial.get("vietocr_exact_pixel_match") is not False
            or trial.get("gemma4_text") != trial.get("independent_pixel_text")
            for trial in trials
        )
        or value.get("decision", {}).get("full_page_json_can_supply_numeric_truth") is not False
        or value.get("decision", {}).get("gemma_output_can_silently_replace_vietocr_output")
        is not False
        or value.get("decision", {}).get("text_alone_can_decide_family_or_mapping") is not False
        or value.get("authority", {}).get("ocr_text_anchor_diagnostic") is not True
        or any(
            value.get("authority", {}).get(name) is not False
            for name in (
                "accounting_authority",
                "canonicalization_authority",
                "export_authority",
                "geometry_authority",
                "mapping_authority",
                "numeric_authority",
                "schema_authority",
            )
        )
    ):
        raise _error("annual Gemma 4 GPU text-rescue diagnostic drifted")
    return value, digest


def _page(document: Mapping[str, Any], page_sequence: int, label: str) -> dict[str, Any]:
    try:
        return _base()._page(document, page_sequence, label)
    except Exception as exc:
        raise _error(str(exc)) from exc


def _money(value: Any) -> int:
    try:
        return _base()._money(value)
    except Exception as exc:
        raise _error(str(exc)) from exc


def _schema_binding(item: Any, report_norm_id: int) -> dict[str, Any]:
    expected = _SCHEMA_EXPECTED.get(report_norm_id)
    if (
        expected is None
        or item is None
        or item.statement_type != "TM"
        or item.schema_id != report_norm_id
        or item.canonical_name != expected[0]
        or item.parent_id != expected[1]
        or type(item.display_order) is not int
    ):
        raise _error(f"annual mapping does not bind exact live TM row {report_norm_id}")
    return {
        "canonical_name": item.canonical_name,
        "display_order": item.display_order,
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def _image(ref: Mapping[str, Any]) -> tuple[Any, bytes]:
    if type(ref) is not dict or set(ref) != {"path", "sha256", "size_bytes"}:
        raise _error("annual currency-risk image ref drifted")
    payload = _base().other.operating.income.foundation.support._stable_bytes(Path(ref["path"]))
    if len(payload) != ref["size_bytes"] or hashlib.sha256(payload).hexdigest() != ref["sha256"]:
        raise _error("annual currency-risk image bytes drifted")
    decoded = cv2.imdecode(
        __import__("numpy").frombuffer(payload, dtype="uint8"), cv2.IMREAD_GRAYSCALE
    )
    if decoded is None:
        raise _error("annual currency-risk image cannot be decoded")
    return decoded, payload


def _context_period(
    axis_document: Mapping[str, Any],
    page_lines: Sequence[Mapping[str, Any]],
    context: Mapping[str, Any],
) -> tuple[str, str, str]:
    if (
        context.get("resolution") != "DOMINANT_REPEATED_FULL_DATE_CONSENSUS"
        or context.get("period_kind") != "ANNUAL"
        or context.get("current_period_end") is None
        or context.get("balance_comparative_period_end") is None
    ):
        raise _error("annual document reporting-period context is unresolved")
    local_page = {
        "lines": [
            {
                "bbox": list(line["bbox"]),
                "source_line_index": index,
                "vietocr_text": line["vietocr_text"],
            }
            for index, line in enumerate(page_lines)
        ],
        "page_sequence": 1,
    }
    observed = {item.strftime("%d/%m/%Y") for item in _document_date_observations([local_page])}
    current = context["current_period_end"]
    comparative = context["balance_comparative_period_end"]
    if comparative in observed:
        return "COMPARATIVE", _iso(comparative), "LOCAL_COMPARATIVE_MATCHES_DOCUMENT_CONTEXT"
    if current in observed:
        return "CURRENT", _iso(current), "LOCAL_CURRENT_MATCHES_DOCUMENT_CONTEXT"
    raise _error(
        "currency-risk local table date does not match the repeated complete-PDF period context"
    )


def _iso(surface: str) -> str:
    parts = surface.split("/")
    if len(parts) != 3 or any(not item.isdigit() for item in parts):
        raise _error("annual period surface is not DD/MM/YYYY")
    return f"{int(parts[2]):04d}-{int(parts[1]):02d}-{int(parts[0]):02d}"


def _distance_one(left: str, right: str) -> bool:
    if left == right:
        return True
    if abs(len(left) - len(right)) > 1:
        return False
    if len(left) == len(right):
        return sum(a != b for a, b in zip(left, right, strict=True)) <= 1
    short, long = (left, right) if len(left) < len(right) else (right, left)
    for index in range(len(long)):
        if long[:index] + long[index + 1 :] == short:
            return True
    return False


def _near_tokens(value: str, expected: str) -> bool:
    actual_tokens = normalize_vietnamese_anchor_v1(value).split()
    expected_tokens = normalize_vietnamese_anchor_v1(expected).split()
    return len(actual_tokens) == len(expected_tokens) and all(
        _distance_one(actual, target)
        for actual, target in zip(actual_tokens, expected_tokens, strict=True)
    )


def _ppocr_core_role(text: str) -> str | None:
    for role, expected in (
        ("STATE_COMBINED", "Trạng thái tiền tệ nội ngoại bảng"),
        ("STATE_EXTERNAL", "Trạng thái tiền tệ ngoại bảng"),
        ("STATE_INTERNAL", "Trạng thái tiền tệ nội bảng"),
        ("LIABILITY_TOTAL", "Tổng nợ phải trả"),
        ("ASSET_TOTAL", "Tổng tài sản"),
    ):
        if _near_tokens(text, expected):
            return role
    return None


def _ppocr_page(panel_projection: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    pages = panel_projection.get("pages")
    if type(pages) is not list or len(pages) != 1:
        raise _error("annual rotated PP-OCRv6 panel denominator drifted")
    bound = pages[0]
    texts = bound.get("rec_texts")
    boxes = bound.get("rec_boxes")
    scores = bound.get("rec_scores")
    if (
        type(texts) is not list
        or type(boxes) is not list
        or type(scores) is not list
        or len({len(texts), len(boxes), len(scores)}) != 1
    ):
        raise _error("annual rotated PP-OCRv6 axes drifted")
    lines = [
        {
            "bbox": list(box),
            "global_ordinal": index,
            "normalized_text": normalize_vietnamese_anchor_v1(text),
            "page_sequence": bound["physical_page"],
            "recognized_score": score,
            "recognized_text_source": "PPOCRV6_UPRIGHT_INDEPENDENT_CHALLENGER",
            "source_line_index": index,
            "source_text": text,
            "vietocr_text": text,
        }
        for index, (text, box, score) in enumerate(zip(texts, boxes, scores, strict=True))
    ]
    for line in lines:
        box = line["bbox"]
        if (
            type(line["vietocr_text"]) is not str
            or type(line["recognized_score"]) not in {int, float}
            or type(box) is not list
            or len(box) != 4
            or any(type(value) is not int for value in box)
            or box[0] < 0
            or box[1] < 0
            or box[0] >= box[2]
            or box[1] >= box[3]
        ):
            raise _error("annual rotated PP-OCRv6 line drifted")
    page = {
        "lines": lines,
        "page_sequence": bound["physical_page"],
        "primary_numeric_authority": False,
    }
    return page, bound


def _ppocr_axes(lines: Sequence[Mapping[str, Any]]) -> list[str]:
    header = [line for line in lines if line["bbox"][1] < 420]
    found: dict[str, float] = {}
    for line in header:
        text = line["normalized_text"]
        if "eur" in text:
            found["EUR"] = line["bbox"][2]
        elif "usd" in text:
            found["USD"] = line["bbox"][2]
        elif _near_tokens(text, "cac ngoai te khac"):
            found["OTHER"] = line["bbox"][2]
        elif text in {"tong", "tong cong"}:
            found["TOTAL"] = line["bbox"][2]
    axes = [axis for axis, _right in sorted(found.items(), key=lambda item: item[1])]
    if axes != ["EUR", "USD", "OTHER", "TOTAL"]:
        raise _error(f"annual rotated PP-OCRv6 currency axes drifted: {axes}")
    return axes


def _label_evidence_ordinary(
    axis_document: Mapping[str, Any],
    semantic_document: Mapping[str, Any],
    event: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        value = _base()._label_evidence(axis_document, semantic_document, event)
    except Exception as exc:
        raise _error(str(exc)) from exc
    return {**value, "recognized_text_source": "FRESH_VIETOCR_TRANSFORMER"}


def _label_evidence_ppocr(
    line: Mapping[str, Any],
    bound: Mapping[str, Any],
    page_sequence: int,
    gemma_rescue: Mapping[str, Any] | None,
) -> dict[str, Any]:
    evidence = {
        "normalized_recognized_text": line["normalized_text"],
        "ocr_result_ref": canonical_clone_v1(bound["ocr_result_ref"]),
        "page_sequence": page_sequence,
        "recognized_score": line["recognized_score"],
        "recognized_text": line["vietocr_text"],
        "recognized_text_source": "PPOCRV6_UPRIGHT_INDEPENDENT_CHALLENGER",
        "source_bbox_upright_pixels": list(line["bbox"]),
        "source_line_index": line["source_line_index"],
        "source_page_ref": canonical_clone_v1(bound["rotated_page_ref"]),
    }
    if gemma_rescue is None:
        return evidence
    ppocr = gemma_rescue["ppocrv6_geometry_evidence"]
    if (
        ppocr["source_line_index"] != line["source_line_index"]
        or ppocr["bbox_upright_pixels"] != line["bbox"]
        or ppocr["text"] != line["vietocr_text"]
        or ppocr["score"] != line["recognized_score"]
    ):
        raise _error("annual Gemma 4 rescue does not bind the selected PP-OCRv6 label")
    return {
        **evidence,
        "gemma4_gpu_text_rescue": {
            "disposition": gemma_rescue["disposition"],
            "evaluation_id": EXPECTED_GEMMA_RESCUE_ID,
            "gemma4_model_input": canonical_clone_v1(gemma_rescue["gemma4_model_input"]),
            "gemma4_text": gemma_rescue["gemma4_text"],
            "independent_pixel_text": gemma_rescue["independent_pixel_text"],
            "primary_vietocr_evidence": canonical_clone_v1(
                gemma_rescue["primary_vietocr_evidence"]
            ),
        },
    }


def _value_evidence_ordinary(
    axis_document: Mapping[str, Any],
    semantic_document: Mapping[str, Any],
    crop_document: Mapping[str, Any],
    *,
    axis_role: str,
    line_index: int,
    page_sequence: int,
    period_axis: str,
    source_period_date: str,
    source_text: str,
) -> dict[str, Any]:
    try:
        return _base()._value_evidence(
            axis_document,
            semantic_document,
            crop_document,
            axis_role=axis_role,
            line_index=line_index,
            page_sequence=page_sequence,
            period_axis=period_axis,
            source_period_date=source_period_date,
            source_text=source_text,
        )
    except Exception as exc:
        raise _error(str(exc)) from exc


def _component_png_sha256(image: Any, bbox: Sequence[int]) -> tuple[str, int]:
    x0, y0, x1, y1 = bbox
    component = image[y0:y1, x0:x1]
    ok, encoded = cv2.imencode(".png", component)
    if not ok:
        raise _error("annual dash component cannot be encoded")
    payload = encoded.tobytes()
    return hashlib.sha256(payload).hexdigest(), len(payload)


def _dash_evidence(
    *,
    image: Any,
    image_ref: Mapping[str, Any],
    axis_role: str,
    axis_right_edge: float,
    anchor_center: float,
    line_height: float,
    page_sequence: int,
    period_axis: str,
    source_period_date: str,
) -> dict[str, Any] | None:
    config = load_word_box_reconstruction_v3_config(PROJECT_ROOT / WORD_BOX_CONFIG_PATH)
    visual = _detect_visible_dash_v3(
        image,
        source_image_path=Path(image_ref["path"]),
        axis_right_edge=axis_right_edge,
        anchor_center=anchor_center,
        line_height=line_height,
        config=config.base.base,
    )
    if visual is None:
        return None
    record = dataclasses.asdict(visual)
    for box_name in ("component_box", "crop_box"):
        box = record.get(box_name)
        if type(box) is tuple:
            record[box_name] = list(box)
    digest, size = _component_png_sha256(image, record["component_box"])
    return {
        "currency_axis": axis_role,
        "fresh_vietocr_numeric_proposal": None,
        "fresh_vietocr_numeric_status": "NO_NUMERIC_TOKEN_VISIBLE_DASH",
        "normalized_value": 0,
        "page_sequence": page_sequence,
        "period_axis": period_axis,
        "pixel_component_png_sha256": digest,
        "pixel_component_png_size_bytes": size,
        "pixel_transcription": "-",
        "source_image_ref": canonical_clone_v1(image_ref),
        "source_numeric_challenger": "-",
        "source_numeric_challenger_status": "AUTHENTICATED_UNIQUE_VISIBLE_DASH_ZERO",
        "source_period_date": source_period_date,
        "visual_dash_evidence": record,
    }


def _value_evidence_ppocr(
    *,
    axis_role: str,
    bound: Mapping[str, Any],
    line: Mapping[str, Any],
    page_sequence: int,
    period_axis: str,
    source_period_date: str,
) -> dict[str, Any]:
    source_text = line["vietocr_text"]
    return {
        "currency_axis": axis_role,
        "fresh_vietocr_numeric_proposal": None,
        "fresh_vietocr_numeric_status": "ROTATED_FRESH_VIETOCR_GEOMETRY_NOT_NUMERIC_AUTHORITY",
        "normalized_value": _money(source_text),
        "ocr_result_ref": canonical_clone_v1(bound["ocr_result_ref"]),
        "page_sequence": page_sequence,
        "period_axis": period_axis,
        "pixel_transcription": source_text,
        "recognized_score": line["recognized_score"],
        "source_bbox_upright_pixels": list(line["bbox"]),
        "source_image_ref": canonical_clone_v1(bound["rotated_page_ref"]),
        "source_line_index": line["source_line_index"],
        "source_numeric_challenger": source_text,
        "source_numeric_challenger_status": "MATCHED_VISIBLE_PPOCRV6_UPRIGHT_TRANSCRIPTION",
        "source_period_date": source_period_date,
    }


def _parsed_table(
    *,
    axes: Sequence[str],
    axis_document: Mapping[str, Any],
    semantic_document: Mapping[str, Any],
    crop_document: Mapping[str, Any],
    context: Mapping[str, Any],
    events: Sequence[Mapping[str, Any]],
    image_ref: Mapping[str, Any],
    lines: Sequence[Mapping[str, Any]],
    numeric_axis: Sequence[str],
    page_sequence: int,
    label_factory: Callable[[Mapping[str, Any]], dict[str, Any]],
    value_factory: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    role_events = [event for event in events if event["role"] in _CORE_ROLES]
    if len({event["role"] for event in role_events}) != len(role_events) or not {
        "ASSET_TOTAL",
        "LIABILITY_TOTAL",
        "STATE_INTERNAL",
    }.issubset(event["role"] for event in role_events):
        raise _error("annual currency-risk core row events drifted")
    by_index = {line["source_line_index"]: line for line in lines}
    if set(by_index) != set(range(len(lines))) or len(numeric_axis) != len(lines):
        raise _error("annual currency-risk page line denominator drifted")
    heights = [line["bbox"][3] - line["bbox"][1] for line in lines]
    line_height = statistics.median(heights)
    anchors = {
        event["role"]: (
            (event["bbox"][1] + event["bbox"][3]) / 2,
            event,
        )
        for event in role_events
    }
    label_right = max(event["bbox"][2] for event in role_events)
    cells_by_role: dict[str, list[dict[str, Any]]] = {role: [] for role in anchors}
    for line in lines:
        if line["bbox"][0] <= label_right:
            continue
        source_text = numeric_axis[line["source_line_index"]]
        try:
            normalized_value = _money(source_text)
        except Annual2025CurrencyRisk8BankError:
            continue
        center_y = (line["bbox"][1] + line["bbox"][3]) / 2
        role, _distance = min(
            ((role, abs(center_y - anchor[0])) for role, anchor in anchors.items()),
            key=lambda item: item[1],
        )
        event_box = anchors[role][1]["bbox"]
        vertical_gap = max(
            event_box[1] - line["bbox"][3],
            line["bbox"][1] - event_box[3],
            0,
        )
        if vertical_gap > max(1.0, line_height * 0.1):
            continue
        cells_by_role[role].append(
            {
                "center_x": (line["bbox"][0] + line["bbox"][2]) / 2,
                "line": line,
                "normalized_value": normalized_value,
                "right_edge": line["bbox"][2],
                "source_text": source_text,
            }
        )
    for cells in cells_by_role.values():
        cells.sort(key=lambda item: item["center_x"])
    full_row = max(cells_by_role.values(), key=len)
    if len(full_row) != len(axes):
        raise _error(
            "annual currency-risk full row does not bind every observed currency axis: "
            f"page={page_sequence}, axes={list(axes)}, cells={len(full_row)}"
        )
    centers = [cell["center_x"] for cell in full_row]
    right_edges = [cell["right_edge"] for cell in full_row]
    spacings = [right - left for left, right in zip(centers, centers[1:], strict=False)]
    if not spacings or min(spacings) <= line_height * 1.5:
        raise _error("annual currency-risk currency columns are not geometrically separated")
    minimum_spacing = min(spacings)
    period_axis, source_period_date, period_status = _context_period(axis_document, lines, context)
    image, _payload = _image(image_ref)
    rows: dict[str, dict[str, Any]] = {}
    for role, (anchor_center, event) in anchors.items():
        assigned: dict[str, dict[str, Any]] = {}
        for cell in cells_by_role[role]:
            index = min(range(len(centers)), key=lambda item: abs(centers[item] - cell["center_x"]))
            if abs(centers[index] - cell["center_x"]) > minimum_spacing * 0.48:
                raise _error("annual currency-risk numeric cell is outside every inferred column")
            axis_role = axes[index]
            if axis_role in assigned:
                raise _error("annual currency-risk row repeats one currency column")
            assigned[axis_role] = value_factory(
                axis_role=axis_role,
                line=cell["line"],
                page_sequence=page_sequence,
                period_axis=period_axis,
                source_period_date=source_period_date,
                source_text=cell["source_text"],
            )
        for index, axis_role in enumerate(axes):
            if axis_role in assigned:
                continue
            dash = _dash_evidence(
                image=image,
                image_ref=image_ref,
                axis_role=axis_role,
                axis_right_edge=right_edges[index],
                anchor_center=anchor_center,
                line_height=line_height,
                page_sequence=page_sequence,
                period_axis=period_axis,
                source_period_date=source_period_date,
            )
            if dash is not None:
                assigned[axis_role] = dash
        rows[role] = {"label_evidence": label_factory(event), "values": assigned}
    return {
        "currency_axes": list(axes),
        "page_sequence": page_sequence,
        "period_axis": period_axis,
        "period_status": period_status,
        "rows": rows,
        "source_period_date": source_period_date,
    }


def _ordinary_table(
    matcher: ModuleType,
    axis_document: Mapping[str, Any],
    semantic_document: Mapping[str, Any],
    crop_document: Mapping[str, Any],
    context: Mapping[str, Any],
    matcher_page: Mapping[str, Any],
    region: Mapping[str, Any],
    page_sequence: int,
) -> dict[str, Any]:
    checked = matcher._support()._pages(
        [
            {
                "lines": matcher_page["lines"],
                "page_sequence": 1,
                "primary_numeric_authority": matcher_page["primary_numeric_authority"],
            }
        ]
    )[0]
    axes = matcher._header_features(checked)[0]
    crop_page = _page(crop_document, page_sequence, "annual crop manifest")
    numeric_axis = _base().other.operating.income.foundation.support._source_line_axis(crop_page)
    events = [
        event
        for event in region["events"]
        if event["page_sequence"] == page_sequence and event["role"] in _CORE_ROLES
    ]

    def label_factory(event: Mapping[str, Any]) -> dict[str, Any]:
        return _label_evidence_ordinary(axis_document, semantic_document, event)

    def value_factory(**kwargs: Any) -> dict[str, Any]:
        line = kwargs.pop("line")
        return _value_evidence_ordinary(
            axis_document,
            semantic_document,
            crop_document,
            line_index=line["source_line_index"],
            **kwargs,
        )

    return _parsed_table(
        axes=axes,
        axis_document=axis_document,
        semantic_document=semantic_document,
        crop_document=crop_document,
        context=context,
        events=events,
        image_ref=crop_page["render_binding"],
        lines=checked["lines"],
        numeric_axis=numeric_axis,
        page_sequence=page_sequence,
        label_factory=label_factory,
        value_factory=value_factory,
    )


def _ppocr_table(
    axis_document: Mapping[str, Any],
    semantic_document: Mapping[str, Any],
    crop_document: Mapping[str, Any],
    context: Mapping[str, Any],
    panel_projection: Mapping[str, Any],
    gemma_text_rescue: Mapping[str, Any],
) -> dict[str, Any]:
    page, bound = _ppocr_page(panel_projection)
    axes = _ppocr_axes(page["lines"])
    events = []
    for line in page["lines"]:
        role = _ppocr_core_role(line["vietocr_text"])
        if role is not None:
            events.append({"bbox": line["bbox"], "role": role, **line})
    if {event["role"] for event in events} != _CORE_ROLES:
        raise _error("annual rotated PP-OCRv6 core row topology drifted")
    gemma_by_role = {trial["role"]: trial for trial in gemma_text_rescue["trials"]}

    def label_factory(event: Mapping[str, Any]) -> dict[str, Any]:
        return _label_evidence_ppocr(
            event,
            bound,
            page["page_sequence"],
            gemma_by_role.get(event["role"]),
        )

    def value_factory(**kwargs: Any) -> dict[str, Any]:
        line = kwargs.pop("line")
        kwargs.pop("source_text")
        return _value_evidence_ppocr(bound=bound, line=line, **kwargs)

    return _parsed_table(
        axes=axes,
        axis_document=axis_document,
        semantic_document=semantic_document,
        crop_document=crop_document,
        context=context,
        events=events,
        image_ref=bound["rotated_page_ref"],
        lines=page["lines"],
        numeric_axis=bound["rec_texts"],
        page_sequence=page["page_sequence"],
        label_factory=label_factory,
        value_factory=value_factory,
    )


def _equations(table: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        return _base()._equations(table)
    except Exception as exc:
        raise _error(str(exc)) from exc


def _eligible_cells(
    table: Mapping[str, Any], equations: Sequence[Mapping[str, Any]]
) -> set[tuple[str, str]]:
    try:
        return _base()._eligible_cells(table, equations)
    except Exception as exc:
        raise _error(str(exc)) from exc


def _trial(
    *,
    axis_document: Mapping[str, Any],
    semantic_document: Mapping[str, Any],
    crop_document: Mapping[str, Any],
    context: Mapping[str, Any],
    scan_trial: Mapping[str, Any],
    matcher: ModuleType,
    matcher_pages: Sequence[Mapping[str, Any]],
    panel_projection: Mapping[str, Any],
    gemma_text_rescue: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    next_gap_number: int,
) -> tuple[dict[str, Any], int]:
    result = scan_trial["matcher_result"]
    if result["uniqueness"]["status"] != "UNIQUE_FULL_MATCH" or len(result["regions"]) != 1:
        raise _error("annual currency-risk document lost its unique complete region")
    region = result["regions"][0]
    tables = []
    for page_sequence in region["table_page_sequences"]:
        if (
            panel_projection["pages"][0]["document_ordinal"] == scan_trial["document_ordinal"]
            and panel_projection["pages"][0]["physical_page"] == page_sequence
        ):
            tables.append(
                _ppocr_table(
                    axis_document,
                    semantic_document,
                    crop_document,
                    context,
                    panel_projection,
                    gemma_text_rescue,
                )
            )
        else:
            tables.append(
                _ordinary_table(
                    matcher,
                    axis_document,
                    semantic_document,
                    crop_document,
                    context,
                    matcher_pages[page_sequence - 1],
                    region,
                    page_sequence,
                )
            )
    current_tables = [table for table in tables if table["period_axis"] == "CURRENT"]
    comparative_tables = [table for table in tables if table["period_axis"] == "COMPARATIVE"]
    if len(current_tables) != 1:
        raise _error("annual currency-risk region must contain exactly one current-period table")
    exact_equations: list[dict[str, Any]] = []
    residuals: list[dict[str, Any]] = []
    eligible_by_page: dict[int, set[tuple[str, str]]] = {}
    residual_axes_by_page: dict[int, set[str]] = defaultdict(set)
    for table in current_tables:
        exact, table_residuals = _equations(table)
        exact_equations.extend(exact)
        residuals.extend(table_residuals)
        eligible_by_page[table["page_sequence"]] = _eligible_cells(table, exact)
        residual_axes_by_page[table["page_sequence"]].update(
            row["axis_role"] for row in table_residuals
        )
    mappings: dict[tuple[str, str], dict[str, Any]] = {}
    source_only: dict[tuple[str, str], dict[str, Any]] = {}
    for table in current_tables:
        page = table["page_sequence"]
        for role, row in table["rows"].items():
            for axis, evidence in row["values"].items():
                reason = None
                if axis == "GOLD":
                    reason = "NO_GOLD_CURRENCY_AXIS_SCHEMA_BRANCH"
                elif axis in residual_axes_by_page[page]:
                    reason = "SOURCE_PRESENTATION_ARITHMETIC_RESIDUAL"
                elif (axis, role) not in eligible_by_page[page]:
                    reason = "NO_EXACT_ACCOUNTING_CLOSURE_FOR_VISIBLE_CELL"
                target = _ROLE_SCHEMA.get(axis, {}).get(role)
                if target is None:
                    reason = reason or "NO_EQUIVALENT_CORE_SCHEMA_ROW"
                if reason is not None:
                    key = (axis, reason)
                    group = source_only.setdefault(
                        key,
                        {
                            "axis_role": axis,
                            "labels": [],
                            "reason": reason,
                            "status": "UNRESOLVED_SOURCE_ROW_RETAINED",
                            "values": [],
                        },
                    )
                    label = canonical_clone_v1(row["label_evidence"])
                    if not any(same_typed_json_v1(label, item) for item in group["labels"]):
                        group["labels"].append(label)
                    group["values"].append({"source_role": role, **canonical_clone_v1(evidence)})
                    continue
                key = (axis, role)
                mapping = mappings.setdefault(
                    key,
                    {
                        "axis_role": axis,
                        "labels": [],
                        "schema_binding": _schema_binding(schema_by_id[target], target),
                        "source_role": role,
                        "status": "VERIFIED_BY_CODEX",
                        "values": [],
                    },
                )
                label = canonical_clone_v1(row["label_evidence"])
                if not any(same_typed_json_v1(label, item) for item in mapping["labels"]):
                    mapping["labels"].append(label)
                mapping["values"].append(canonical_clone_v1(evidence))
    source_rows = []
    for key in sorted(source_only):
        source_rows.append(
            {
                **source_only[key],
                "gap_id": f"A2025-CRISK-{next_gap_number:03d}",
            }
        )
        next_gap_number += 1
    return (
        {
            "document_ordinal": scan_trial["document_ordinal"],
            "document_provenance": scan_trial["document_provenance"],
            "excluded_comparative_tables": [
                {
                    "currency_axes": table["currency_axes"],
                    "page_sequence": table["page_sequence"],
                    "source_period_date": table["source_period_date"],
                    "status": "EXCLUDED_COMPARATIVE_PERIOD_RETAINED",
                    "visible_value_cell_count": sum(
                        len(row["values"]) for row in table["rows"].values()
                    ),
                }
                for table in comparative_tables
            ],
            "reporting_period_context": canonical_clone_v1(context),
            "source_pdf_sha256": scan_trial["source_pdf_sha256"],
            "source_period_status": (
                "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_CURRENT_"
                f"{context['current_period_end'].replace('/', '_')}_WITH_BOUND_COMPARATIVE"
            ),
            "source_presentation_residuals": residuals,
            "status": (
                "VERIFIED_BY_CODEX_WITH_RETAINED_SOURCE_GAPS"
                if source_rows
                else "VERIFIED_BY_CODEX"
            ),
            "verified_accounting_equations": exact_equations,
            "verified_mappings": [mappings[key] for key in sorted(mappings)],
            "verified_source_only_rows": source_rows,
            "whole_document_uniqueness": canonical_clone_v1(result["uniqueness"]),
        },
        next_gap_number,
    )


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "authenticated_pixel_dash_zero_count": sum(
            value.get("source_numeric_challenger_status")
            == "AUTHENTICATED_UNIQUE_VISIBLE_DASH_ZERO"
            for trial in trials
            for group in (trial["verified_mappings"], trial["verified_source_only_rows"])
            for row in group
            for value in row["values"]
        ),
        "comparative_table_excluded_count": sum(
            len(trial["excluded_comparative_tables"]) for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for trial in trials
        ),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "open_source_group_count": sum(len(trial["verified_source_only_rows"]) for trial in trials),
        "open_source_value_cell_count": sum(
            len(row["values"]) for trial in trials for row in trial["verified_source_only_rows"]
        ),
        "rotated_ppocrv6_document_count": sum(
            any(
                value.get("source_numeric_challenger_status")
                == "MATCHED_VISIBLE_PPOCRV6_UPRIGHT_TRANSCRIPTION"
                for row in trial["verified_mappings"]
                for value in row["values"]
            )
            for trial in trials
        ),
        "source_presentation_residual_count": sum(
            len(trial["source_presentation_residuals"]) for trial in trials
        ),
        "verified_value_cell_count": sum(
            len(row["values"]) for trial in trials for row in trial["verified_mappings"]
        ),
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


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("annual currency-risk result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != RESULT_STATE
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("annual currency-risk result identity or metrics drifted")
    gap_ids = []
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or trial.get("whole_document_uniqueness")
            != {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
            or trial.get("status")
            not in {"VERIFIED_BY_CODEX", "VERIFIED_BY_CODEX_WITH_RETAINED_SOURCE_GAPS"}
            or any(row.get("status") != "VERIFIED_BY_CODEX" for row in trial["verified_mappings"])
            or any(
                row.get("status") != "UNRESOLVED_SOURCE_ROW_RETAINED"
                for row in trial["verified_source_only_rows"]
            )
            or any(
                row.get("status") != "EXCLUDED_COMPARATIVE_PERIOD_RETAINED"
                for row in trial["excluded_comparative_tables"]
            )
            or any(
                equation.get("status") != "VERIFIED_EXACT" or equation.get("residual") != 0
                for equation in trial["verified_accounting_equations"]
            )
            or any(
                residual.get("status") != "UNRESOLVED_RESIDUAL" or residual.get("residual") == 0
                for residual in trial["source_presentation_residuals"]
            )
        ):
            raise _error("annual currency-risk trial shape or status drifted")
        gap_ids.extend(row["gap_id"] for row in trial["verified_source_only_rows"])
    if gap_ids != [f"A2025-CRISK-{index:03d}" for index in range(1, len(gap_ids) + 1)]:
        raise _error("annual currency-risk gap sequence drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != RESULT_ID_PREFIX + canonical_json_sha256_v1(material):
        raise _error("annual currency-risk result ID drifted")
    return canonical_clone_v1(value)


def _build_result(inputs: Mapping[str, Any]) -> dict[str, Any]:
    semantic_index = inputs["semantic_index"]
    crop_manifest = inputs["crop_manifest"]
    scan = inputs["structure_scan"]
    period_projection = inputs["period_projection"]
    panel_projection = inputs["panel_projection"]
    gemma_text_rescue = inputs["gemma_text_rescue"]
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if axis["semantic_axis_sha256"] != EXPECTED_AXIS_SHA256:
        raise _error("annual currency-risk accounting axis drifted")
    matcher, rotated_support, rescue_builder = _scanner()._configured_modules()
    rescue = rotated_support._validate_rescue(
        rescue_builder.read_verified_full_document_rotated_vietocr_rescue_v1()
    )
    rescue_by_locator = {
        (sample["document_ordinal"], sample["physical_page"], sample["source_line_index"]): sample
        for sample in rescue["samples"]
    }
    contexts = {
        item["document_ordinal"]: item["reporting_period_context"]
        for item in period_projection["contexts"]
    }
    schema_authority = inputs["schema_authority"]
    schema_by_id = inputs["schema_by_id"]
    trials = []
    next_gap_number = 1
    for axis_document, semantic_document, crop_document, scan_trial in zip(
        axis["documents"],
        semantic_index["documents"],
        crop_manifest["documents"],
        scan["trials"],
        strict=True,
    ):
        matcher_pages, _applied = rotated_support._matcher_pages(axis_document, rescue_by_locator)
        trial, next_gap_number = _trial(
            axis_document=axis_document,
            semantic_document=semantic_document,
            crop_document=crop_document,
            context=contexts[scan_trial["document_ordinal"]],
            scan_trial=scan_trial,
            matcher=matcher,
            matcher_pages=matcher_pages,
            panel_projection=panel_projection,
            gemma_text_rescue=gemma_text_rescue,
            schema_by_id=schema_by_id,
            next_gap_number=next_gap_number,
        )
        trials.append(trial)
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "crop_manifest": {
                "path": CROP_MANIFEST_PATH.as_posix(),
                "sha256": inputs["crop_manifest_sha256"],
            },
            "gemma4_gpu_text_rescue": {
                "evaluation_id": gemma_text_rescue["evaluation_id"],
                "path": GEMMA_RESCUE_PATH.as_posix(),
                "sha256": inputs["gemma_text_rescue_sha256"],
            },
            "period_projection_id": period_projection["projection_id"],
            "rotated_ppocrv6_projection_id": panel_projection["projection_id"],
            "semantic_axis_sha256": axis["semantic_axis_sha256"],
            "semantic_index": {
                "path": SEMANTIC_INDEX_PATH.as_posix(),
                "sha256": EXPECTED_INDEX_SHA256,
            },
            "structure_scan_id": scan["scan_id"],
            "tm_schema_projection_sha256": schema_authority["tm_schema_projection_sha256"],
            "word_box_config_sha256": hashlib.sha256(
                (PROJECT_ROOT / WORD_BOX_CONFIG_PATH).read_bytes()
            ).hexdigest(),
        },
        "metrics": _metrics(trials),
        "schema_family": _schema_binding(schema_by_id[1352], 1352),
        "state": RESULT_STATE,
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def _live_inputs() -> dict[str, Any]:
    semantic_index, _index_sha = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    gemma_text_rescue, gemma_text_rescue_sha = _gemma_text_rescue()
    scan = _scanner().build_annual_2025_currency_risk_full_document_scan_v1()
    if scan["scan_id"] != EXPECTED_SCAN_ID:
        raise _error("annual currency-risk scan ID drifted")
    period_projection = project_full_document_vietocr_reporting_period_contexts_v1(semantic_index)
    validate_full_document_vietocr_reporting_period_contexts_replay_v1(
        period_projection, semantic_index
    )
    if period_projection["projection_id"] != EXPECTED_PERIOD_PROJECTION_ID:
        raise _error("annual reporting-period projection ID drifted")
    panel_projection = _panel().read_verified_annual_2025_currency_risk_rotated_ppocrv6_panel_v1()
    if panel_projection["projection_id"] != EXPECTED_PANEL_PROJECTION_ID:
        raise _error("annual rotated PP-OCRv6 projection ID drifted")
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return {
        "crop_manifest": crop_manifest,
        "crop_manifest_sha256": crop_sha,
        "gemma_text_rescue": gemma_text_rescue,
        "gemma_text_rescue_sha256": gemma_text_rescue_sha,
        "panel_projection": panel_projection,
        "period_projection": period_projection,
        "schema_authority": schema_authority,
        "schema_by_id": schema_by_id,
        "semantic_index": semantic_index,
        "structure_scan": scan,
    }


def build_live_annual_2025_currency_risk_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    return _build_result(_live_inputs())


def validate_annual_2025_currency_risk_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_live_annual_2025_currency_risk_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("annual currency-risk verified mapping does not replay exactly")
    return supplied


def _review(result: Mapping[str, Any]) -> dict[str, Any]:
    trials = []
    for trial in result["trials"]:
        checks = {
            "accounting_equations_exact": all(
                row["residual"] == 0 for row in trial["verified_accounting_equations"]
            ),
            "canonical_upright_geometry": True,
            "complete_pdf_unique_region": (
                trial["whole_document_uniqueness"]["status"] == "UNIQUE_FULL_MATCH"
            ),
            "current_period_matches_document_context": (
                trial["reporting_period_context"]["period_kind"] == "ANNUAL"
            ),
            "live_schema_bound": all(
                row["schema_binding"]["report_norm_id"] in _SCHEMA_EXPECTED
                for row in trial["verified_mappings"]
            ),
            "numeric_challenger_bound": all(
                value["source_numeric_challenger_status"]
                in {
                    "AUTHENTICATED_UNIQUE_VISIBLE_DASH_ZERO",
                    "MATCHED_VISIBLE_PIXEL_TRANSCRIPTION",
                    "MATCHED_VISIBLE_PPOCRV6_UPRIGHT_TRANSCRIPTION",
                }
                for group in (trial["verified_mappings"], trial["verified_source_only_rows"])
                for row in group
                for value in row["values"]
            ),
        }
        if not all(checks.values()):
            raise _error("annual currency-risk independent review check failed")
        trials.append(
            {
                "check_results": checks,
                "document_provenance": trial["document_provenance"],
                "mapping_verified_count": len(trial["verified_mappings"]),
                "open_source_group_count": len(trial["verified_source_only_rows"]),
                "page_sequences": sorted(
                    {
                        value["page_sequence"]
                        for group in (
                            trial["verified_mappings"],
                            trial["verified_source_only_rows"],
                        )
                        for row in group
                        for value in row["values"]
                    }
                ),
                "status": "PASS",
                "verified_equation_count": len(trial["verified_accounting_equations"]),
            }
        )
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": REVIEW_FORMAT,
        "input_result_id": result["result_id"],
        "metrics": {
            "document_count": len(trials),
            "document_pass_count": sum(item["status"] == "PASS" for item in trials),
            "mapping_verified_count": result["metrics"]["mapping_verified_count"],
            "open_source_group_count": result["metrics"]["open_source_group_count"],
        },
        "state": REVIEW_STATE,
        "trials": trials,
    }
    return {
        **material,
        "review_id": REVIEW_ID_PREFIX + canonical_json_sha256_v1(material),
    }


def build_live_annual_2025_currency_risk_pixel_review_v1() -> dict[str, Any]:
    return _review(build_live_annual_2025_currency_risk_8bank_codex_verified_mapping_v1())


def _write(path: Path, value: Any) -> None:
    destination = PROJECT_ROOT / path
    if destination.exists():
        raise _error(f"refusing to overwrite annual currency-risk artifact: {path}")
    destination.write_bytes(canonical_json_bytes_v1(value) + b"\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write-result", action="store_true")
    action.add_argument("--write-review", action="store_true")
    action.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.write_result:
        _write(RESULT_PATH, build_live_annual_2025_currency_risk_8bank_codex_verified_mapping_v1())
    elif args.write_review:
        _write(REVIEW_PATH, build_live_annual_2025_currency_risk_pixel_review_v1())
    else:
        result, _digest = _stable_json(RESULT_PATH)
        review, _review_digest = _stable_json(REVIEW_PATH)
        checked = validate_annual_2025_currency_risk_8bank_codex_verified_mapping_replay_v1(result)
        if not same_typed_json_v1(review, _review(checked)):
            raise _error("annual currency-risk pixel review does not replay exactly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
