#!/usr/bin/env python3
"""Verify the annual-2025 interest-rate-risk accounting core for eight banks.

The complete-PDF family graph selects the region.  Repricing columns are
resolved from header semantics plus repeated numeric x-centres.  On normalized
landscape pages, PP-OCRv6 word boxes reconstruct merged/multiline headers; a
bounded Gemma page JSON may corroborate structure but is never numeric truth.
Only current-period cells participating in exact accounting equations can be
promoted to ``VERIFIED_BY_CODEX``.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import statistics
import sys
from collections import defaultdict
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
    project_full_document_vietocr_reporting_period_contexts_v1,
    validate_full_document_vietocr_reporting_period_contexts_replay_v1,
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
RESULT_PATH = Path(
    "docs/experiments/E-0156-annual-2025-interest-rate-risk-8bank-codex-verified-mapping-v1.json"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0156-annual-2025-interest-rate-risk-8bank-codex-pixel-review-v1.json"
)

EXPECTED_INDEX_SHA256 = "98bb9854e699230da86538cf024ef3f4817b9e2f4dd2b2a75f46198f00e4247d"
EXPECTED_CROP_MANIFEST_SHA256 = "17d12a4d6b1dfaf0e243300757fd225b8c9cca80810a2d856efdb55a5b4ac000"
EXPECTED_AXIS_SHA256 = "aa81f553fda69315e84b7adbda13347c25a4490b016fc9660ff4f2cd49795ce7"
EXPECTED_SCAN_ID = (
    "a2025irrfdsv1:scan:5b48aafdeafa7a1c106efb640dc502c03ef04d3f286e0df2ec10125d1a0a71c0"
)
EXPECTED_PERIOD_PROJECTION_ID = (
    "fdvrpcv1:projection:fd732522c67ec0fa927696bf1b17721f1ce16c34a083618e2bb4ebf7acb6d0d3"
)
EXPECTED_PANEL_PROJECTION_ID = (
    "a2025irrrpv1:projection:d0114ee306a9a92e2c7b2aba5313a0b67e94d43916d92f17556549f629cece06"
)

FORMAT_VERSION = "ANNUAL_2025_INTEREST_RATE_RISK_8BANK_CODEX_VERIFIED_MAPPING_V1"
RESULT_STATE = "ANNUAL_2025_INTEREST_RATE_RISK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025irr8bcv1:result:"
REVIEW_FORMAT = "ANNUAL_2025_INTEREST_RATE_RISK_8BANK_CODEX_PIXEL_REVIEW_V1"
REVIEW_STATE = "ANNUAL_2025_INTEREST_RATE_RISK_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025irr8bcv1:pixel-review:"
CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_VIETOCR_"
    "BANK_BLIND_INTEREST_RATE_RISK_GRAPH_CANONICAL_UPRIGHT_GEOMETRY_PPOCRV6_"
    "ROTATED_NUMERIC_AND_WORD_BOX_CHALLENGER_BOUNDED_GEMMA4_STRUCTURE_RESCUE_"
    "VISIBLE_DASH_ZERO_EXACT_ACCOUNTING_CLOSURE_LIVE_TM_SCHEMA_CORE_ONLY_"
    "COMPARATIVE_RETAINED_EXCLUDED_UNSUPPORTED_CELLS_RETAINED_NO_EXPORT_AUTHORITY"
)
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
    "gemma4_structure_rescue_may_corroborate_header_hierarchy": True,
    "gemma4_used_as_numeric_truth": False,
    "header_line_bbox_alone_determines_column_count": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_exact_annual_accounting_core_cells": True,
    "merged_header_may_collapse_distinct_schema_axes": False,
    "numeric_column_centres_repeated_across_rows_required": True,
    "paddleocr_or_ppocrv6_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "repricing_axis_or_row_order_required": False,
    "text_similarity_alone_used_for_mapping": False,
    "unsupported_or_comparative_source_cells_discarded": False,
    "visible_dash_equals_zero_only_with_unique_pixel_component": True,
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


class Annual2025InterestRateRisk8BankError(ValueError):
    """The annual graph, periods, geometry, numbers, equations or schema drifted."""


def _error(message: str) -> Annual2025InterestRateRisk8BankError:
    return Annual2025InterestRateRisk8BankError(message)


def _load(name: str, relative_path: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    path = PROJECT_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual interest-rate-risk support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _base() -> ModuleType:
    return _load(
        "annual_2025_interest_rate_risk_mapping_base_v1",
        "scripts/experiments/build_interest_rate_risk_8bank_codex_verified_mapping_v1.py",
    )


def _annual_support() -> ModuleType:
    return _load(
        "annual_2025_interest_rate_risk_currency_support_v1",
        "scripts/experiments/build_annual_2025_currency_risk_8bank_codex_verified_mapping_v1.py",
    )


def _scanner() -> ModuleType:
    return _load(
        "annual_2025_interest_rate_risk_scan_for_mapping_v1",
        "scripts/experiments/scan_annual_2025_interest_rate_risk_full_document_vietocr_v1.py",
    )


def _panel() -> ModuleType:
    return _load(
        "annual_2025_interest_rate_risk_ppocrv6_panel_for_mapping_v1",
        "scripts/experiments/build_annual_2025_interest_rate_risk_rotated_ppocrv6_panel_v1.py",
    )


def _stable_json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], str]:
    try:
        return _annual_support()._stable_json(path, expected_sha256)
    except Exception as exc:
        raise _error(str(exc)) from exc


def _page(document: Mapping[str, Any], page_sequence: int, label: str) -> dict[str, Any]:
    try:
        return _base()._page(document, page_sequence, label)
    except Exception as exc:
        raise _error(str(exc)) from exc


def _schema_family(item: Any) -> dict[str, Any]:
    """Bind the stable family identity without freezing mutable display order."""

    if (
        item is None
        or item.statement_type != "TM"
        or item.schema_id != 1483
        or item.canonical_name != "Rủi ro lãi suất"
        or item.parent_id != 1259
        or item.hierarchy_level != 1
        or type(item.display_order) is not int
    ):
        raise _error("annual interest-rate-risk family lost its live TM schema identity")
    return {
        "canonical_name": item.canonical_name,
        "display_order": item.display_order,
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def _money(value: Any) -> int:
    try:
        return _base()._money(value)
    except Exception as exc:
        raise _error(f"invalid annual interest-rate-risk monetary surface: {value!r}") from exc


def _distance_one(left: str, right: str) -> bool:
    if left == right:
        return True
    if abs(len(left) - len(right)) > 1:
        return False
    if len(left) == len(right):
        return sum(a != b for a, b in zip(left, right, strict=True)) <= 1
    short, long = (left, right) if len(left) < len(right) else (right, left)
    return any(long[:index] + long[index + 1 :] == short for index in range(len(long)))


def _near_tokens(value: str, expected: str) -> bool:
    actual = normalize_vietnamese_anchor_v1(value).split()
    target = normalize_vietnamese_anchor_v1(expected).split()
    return len(actual) == len(target) and all(
        _distance_one(left, right) for left, right in zip(actual, target, strict=True)
    )


def _contains_near_tokens(value: str, expected: str) -> bool:
    actual = normalize_vietnamese_anchor_v1(value).split()
    target = normalize_vietnamese_anchor_v1(expected).split()
    if len(actual) < len(target):
        return False
    return any(
        all(_distance_one(left, right) for left, right in zip(window, target, strict=True))
        for window in (
            actual[index : index + len(target)] for index in range(len(actual) - len(target) + 1)
        )
    )


def _ppocr_core_role(value: str) -> str | None:
    normalized = normalize_vietnamese_anchor_v1(value)
    if _near_tokens(normalized, "Tổng tài sản"):
        return "ASSET_TOTAL"
    if _near_tokens(normalized, "Tổng nợ phải trả"):
        return "LIABILITY_TOTAL"
    if _contains_near_tokens(normalized, "nội ngoại bảng"):
        return "STATE_COMBINED"
    if _contains_near_tokens(normalized, "cam kết ngoại bảng"):
        return "STATE_EXTERNAL"
    if _contains_near_tokens(normalized, "lãi suất nội bảng"):
        return "STATE_INTERNAL"
    return None


def _ppocr_spans(lines: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    page_right = max(line["bbox"][2] for line in lines)
    label_limit = page_right * 0.36
    numeric_lines = []
    for line in lines:
        try:
            _money(line["vietocr_text"])
        except Annual2025InterestRateRisk8BankError:
            continue
        if line["bbox"][0] > page_right * 0.25:
            numeric_lines.append(line)
    labels = [
        line for line in lines if line["bbox"][0] <= label_limit and line not in numeric_lines
    ]
    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, _line in enumerate(labels):
        parts: list[Mapping[str, Any]] = []
        for following in labels[index : index + 5]:
            if parts and following["bbox"][1] - parts[-1]["bbox"][3] > 50:
                break
            if parts:
                current_role = _ppocr_core_role(" ".join(part["vietocr_text"] for part in parts))
                current_y1 = min(part["bbox"][1] for part in parts)
                current_y2 = max(part["bbox"][3] for part in parts)
                if current_role is not None and any(
                    min(current_y2, numeric["bbox"][3]) - max(current_y1, numeric["bbox"][1]) > 0
                    for numeric in numeric_lines
                ):
                    break
            parts.append(following)
            text = " ".join(part["vietocr_text"] for part in parts)
            role = _ppocr_core_role(text)
            if role is None:
                continue
            candidates[role].append(
                {
                    "parts": list(parts),
                    "role": role,
                    "x1": min(part["bbox"][0] for part in parts),
                    "x2": max(part["bbox"][2] for part in parts),
                    "y1": min(part["bbox"][1] for part in parts),
                    "y2": max(part["bbox"][3] for part in parts),
                }
            )
    required = {"ASSET_TOTAL", "LIABILITY_TOTAL", "STATE_INTERNAL"}
    if not required <= set(candidates):
        raise _error(f"rotated PP-OCRv6 core label topology drifted: {sorted(candidates)}")
    median_height = statistics.median(line["bbox"][3] - line["bbox"][1] for line in lines)

    def numeric_cluster_count(item: Mapping[str, Any]) -> int:
        centres = sorted(
            (numeric["bbox"][1] + numeric["bbox"][3]) / 2
            for numeric in numeric_lines
            if min(item["y2"], numeric["bbox"][3]) - max(item["y1"], numeric["bbox"][1]) > 0
        )
        if not centres:
            return 0
        groups = 1
        for left, right in zip(centres, centres[1:], strict=False):
            if right - left > max(4.0, median_height * 0.7):
                groups += 1
        return groups

    best: dict[str, dict[str, Any]] = {}
    for role, values in candidates.items():
        # Prefer exactly one aligned numeric band, then retain its full label.
        best[role] = min(
            values,
            key=lambda item: (
                numeric_cluster_count(item) == 0,
                numeric_cluster_count(item) or 999,
                -len(item["parts"]),
                item["y1"],
            ),
        )
    return best


def _full_row_centres(
    lines: Sequence[Mapping[str, Any]],
    numeric_axis: Sequence[str],
    spans: Mapping[str, Mapping[str, Any]],
) -> list[float]:
    groups: list[list[dict[str, Any]]] = []
    for role in _CORE_ROLES:
        span = spans.get(role)
        if span is None:
            continue
        candidates = []
        for line in lines:
            if line["bbox"][0] <= span["x2"]:
                continue
            try:
                _money(numeric_axis[line["source_line_index"]])
            except Annual2025InterestRateRisk8BankError:
                continue
            candidates.append(
                {
                    "center_x": (line["bbox"][0] + line["bbox"][2]) / 2,
                    "center_y": (line["bbox"][1] + line["bbox"][3]) / 2,
                    "line": line,
                }
            )
        margin = max(18.0, (span["y2"] - span["y1"]) * 0.35)
        clustered = [
            group
            for group in _base()._clusters(candidates)
            if span["y1"] - margin
            <= statistics.mean(cell["center_y"] for cell in group)
            <= span["y2"] + margin
        ]
        if clustered:
            label_center = (span["y1"] + span["y2"]) / 2
            maximum = max(len(group) for group in clustered)
            viable = [group for group in clustered if len(group) >= maximum - 1]
            groups.append(
                min(
                    viable,
                    key=lambda group: (
                        abs(statistics.mean(cell["center_y"] for cell in group) - label_center),
                        -len(group),
                    ),
                )
            )
    if not groups:
        raise _error("annual interest-rate-risk table has no numeric core row")
    full = max(groups, key=len)
    centres = sorted(cell["center_x"] for cell in full)
    if len(centres) < 7 or any(
        right <= left for left, right in zip(centres, centres[1:], strict=False)
    ):
        raise _error("annual interest-rate-risk numeric column geometry drifted")
    return centres


def _column_surface_role(value: str) -> str | None:
    normalized = normalize_vietnamese_anchor_v1(value)
    compact = normalized.replace(" ", "")
    if _contains_near_tokens(normalized, "quá hạn") or _distance_one("quahn", compact[-5:]):
        return "OVERDUE"
    if "khongchju" in compact or "khongchiu" in compact or "khongbidinhgialai" in compact:
        return "NO_INTEREST"
    if "duoi1thang" in compact or "den1thang" in compact or "dn1thang" in compact:
        return "WITHIN_LE1M"
    if re.search(r"1thang.*3thang", compact):
        return "WITHIN_1_3M"
    if re.search(r"3thang.*6thang", compact):
        return "WITHIN_3_6M"
    if re.search(r"6thang.*12thang", compact):
        return "WITHIN_6_12M"
    if re.search(r"1nam.*5nam", compact):
        return "WITHIN_1_5Y"
    if re.search(r"(?:tu|tur|tut)1(?:-|den)?3thang", compact) or "tut3thang" in compact:
        return "WITHIN_1_3M"
    if re.search(r"(?:tu|tur|t)3(?:-|den)?6thang", compact):
        return "WITHIN_3_6M"
    if re.search(r"(?:tu|tur)6(?:-|den)?12thang", compact):
        return "WITHIN_6_12M"
    if re.search(r"(?:tu|tur)1(?:-|den)?5nam", compact):
        return "WITHIN_1_5Y"
    if "tren5nam" in compact or "tran5nam" in compact:
        return "WITHIN_GT5Y"
    if (
        "tongcong" in compact
        or compact.endswith("tong")
        or "tongcng" in compact
        or any(_distance_one(token, "tong") for token in normalized.split())
    ):
        return "TOTAL"
    return None


def _ppocr_axes(
    *,
    bound: Mapping[str, Any],
    centres: Sequence[float],
    lines: Sequence[Mapping[str, Any]],
) -> tuple[list[str], list[dict[str, Any]]]:
    words = bound.get("text_word")
    word_boxes = bound.get("text_word_boxes")
    if type(words) is not list or type(word_boxes) is not list or len(words) != len(lines):
        raise _error("rotated PP-OCRv6 word-box axis is absent")
    asset_headers = [line for line in lines if _near_tokens(line["vietocr_text"], "Tài sản")]
    if not asset_headers:
        raise _error("rotated table has no visible asset-section header")
    cutoff_y = min(line["bbox"][1] for line in asset_headers)
    boundaries = [float("-inf")]
    boundaries.extend((left + right) / 2 for left, right in zip(centres, centres[1:], strict=False))
    boundaries.append(float("inf"))
    roles = []
    evidence = []
    for ordinal, (left, right) in enumerate(zip(boundaries, boundaries[1:], strict=False)):
        by_line: list[tuple[int, int, str, list[list[int]]]] = []
        for line_index, (line_words, line_boxes) in enumerate(zip(words, word_boxes, strict=True)):
            selected = [
                (box[0], token, list(box))
                for token, box in zip(line_words, line_boxes, strict=True)
                if token.strip() and box[1] < cutoff_y and left <= (box[0] + box[2]) / 2 < right
            ]
            if selected:
                by_line.append(
                    (
                        min(item[0] for item in selected),
                        line_index,
                        "".join(item[1] for item in sorted(selected)),
                        [item[2] for item in sorted(selected)],
                    )
                )
        surface = " ".join(item[2] for item in by_line)
        role = _column_surface_role(surface)
        if role is None or role in roles:
            raise _error(
                "rotated PP-OCRv6 header cannot bind one unique repricing axis: "
                f"column={ordinal}, surface={surface!r}, roles={roles}"
            )
        roles.append(role)
        evidence.append(
            {
                "column_center_x": centres[ordinal],
                "header_surface": surface,
                "repricing_axis": role,
                "word_boxes": [box for item in by_line for box in item[3]],
            }
        )
    return roles, evidence


def _ordinary_axes(
    *,
    centres: Sequence[float],
    lines: Sequence[Mapping[str, Any]],
    spans: Mapping[str, Mapping[str, Any]],
) -> tuple[list[str], list[dict[str, Any]]]:
    """Project noisy header fragments onto repeated numeric column centres."""

    section = spans.get("ASSET_SECTION")
    cutoff_y = (
        section["y1"]
        if section is not None
        else min(span["y1"] for role, span in spans.items() if role in _CORE_ROLES)
    )
    boundaries = [float("-inf")]
    boundaries.extend((left + right) / 2 for left, right in zip(centres, centres[1:], strict=False))
    boundaries.append(float("inf"))
    roles: list[str] = []
    evidence: list[dict[str, Any]] = []
    for ordinal, (left, right) in enumerate(zip(boundaries, boundaries[1:], strict=False)):
        selected = sorted(
            (
                line
                for line in lines
                if line["bbox"][1] < cutoff_y
                and left <= (line["bbox"][0] + line["bbox"][2]) / 2 < right
            ),
            key=lambda line: (line["bbox"][1], line["bbox"][0]),
        )
        surface = " ".join(line["vietocr_text"] for line in selected)
        role = _column_surface_role(surface)
        if role is None or role in roles:
            raise _error(
                "fresh VietOCR header cannot bind one unique repricing axis: "
                f"column={ordinal}, surface={surface!r}, roles={roles}"
            )
        roles.append(role)
        evidence.append(
            {
                "column_center_x": centres[ordinal],
                "header_surface": surface,
                "repricing_axis": role,
                "source_line_boxes": [list(line["bbox"]) for line in selected],
                "source_line_indices": [line["source_line_index"] for line in selected],
            }
        )
    return roles, evidence


def _ppocr_page(bound: Mapping[str, Any]) -> dict[str, Any]:
    texts = bound.get("rec_texts")
    boxes = bound.get("rec_boxes")
    scores = bound.get("rec_scores")
    if (
        type(texts) is not list
        or type(boxes) is not list
        or type(scores) is not list
        or len({len(texts), len(boxes), len(scores)}) != 1
    ):
        raise _error("rotated PP-OCRv6 line axes drifted")
    lines = [
        {
            "bbox": list(box),
            "normalized_text": normalize_vietnamese_anchor_v1(text),
            "page_sequence": bound["physical_page"],
            "recognized_score": score,
            "semantic_text_source": "PPOCRV6_UPRIGHT_INDEPENDENT_CHALLENGER",
            "source_line_index": index,
            "vietocr_text": text,
        }
        for index, (text, box, score) in enumerate(zip(texts, boxes, scores, strict=True))
    ]
    return {"lines": lines, "page_sequence": bound["physical_page"]}


def _span_events(spans: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "bbox": [span["x1"], span["y1"], span["x2"], span["y2"]],
            "role": role,
            "span": span,
        }
        for role, span in spans.items()
        if role in _CORE_ROLES
    ]


def _ordinary_spans(page: Mapping[str, Any], matcher: ModuleType) -> dict[str, dict[str, Any]]:
    """Keep complete numeric rows distinct before considering wrapped labels."""

    spans = _base()._label_spans(page, matcher)
    support = matcher._support()
    page_right = max(line["bbox"][2] for line in page["lines"])
    label_limit = page_right * 0.46
    numeric_lines = [
        line
        for line in page["lines"]
        if support._NUMBER.fullmatch(line["normalized_text"]) is not None
    ]
    for line in page["lines"]:
        if line["bbox"][0] > label_limit:
            continue
        role = matcher._raw_role(line["normalized_text"])
        if role not in _CORE_ROLES:
            continue
        line_height = line["bbox"][3] - line["bbox"][1]
        has_aligned_value = any(
            numeric["bbox"][0] > line["bbox"][2]
            and max(
                line["bbox"][1] - numeric["bbox"][3],
                numeric["bbox"][1] - line["bbox"][3],
                0,
            )
            <= max(1.0, line_height * 0.15)
            for numeric in numeric_lines
        )
        if not has_aligned_value:
            continue
        spans[role] = {
            "parts": [line],
            "quality": 3,
            "rank": (3, -1, -line["bbox"][1]),
            "role": role,
            "x1": line["bbox"][0],
            "x2": line["bbox"][2],
            "y1": line["bbox"][1],
            "y2": line["bbox"][3],
        }
    return spans


def _label_evidence_ppocr(event: Mapping[str, Any], bound: Mapping[str, Any]) -> dict[str, Any]:
    span = event["span"]
    return {
        "components": [
            {
                "ocr_result_ref": canonical_clone_v1(bound["ocr_result_ref"]),
                "page_sequence": bound["physical_page"],
                "recognized_score": part["recognized_score"],
                "recognized_text": part["vietocr_text"],
                "recognized_text_source": "PPOCRV6_UPRIGHT_INDEPENDENT_CHALLENGER",
                "source_bbox_upright_pixels": list(part["bbox"]),
                "source_line_index": part["source_line_index"],
                "source_page_ref": canonical_clone_v1(bound["rotated_page_ref"]),
            }
            for part in span["parts"]
        ],
        "normalized_recognized_text": " ".join(part["normalized_text"] for part in span["parts"]),
    }


def _value_evidence_ppocr(
    *,
    axis_role: str,
    bound: Mapping[str, Any],
    line: Mapping[str, Any],
    page_sequence: int,
    period_axis: str,
    source_period_date: str,
    **_unused: Any,
) -> dict[str, Any]:
    surface = line["vietocr_text"]
    return {
        "fresh_vietocr_numeric_proposal": None,
        "fresh_vietocr_numeric_status": "ROTATED_FRESH_VIETOCR_NOT_NUMERIC_AUTHORITY",
        "normalized_value": _money(surface),
        "ocr_result_ref": canonical_clone_v1(bound["ocr_result_ref"]),
        "page_sequence": page_sequence,
        "period_axis": period_axis,
        "pixel_transcription": surface,
        "recognized_score": line["recognized_score"],
        "repricing_axis": axis_role,
        "source_bbox_upright_pixels": list(line["bbox"]),
        "source_image_ref": canonical_clone_v1(bound["rotated_page_ref"]),
        "source_line_index": line["source_line_index"],
        "source_numeric_challenger": surface,
        "source_numeric_challenger_status": "MATCHED_VISIBLE_PPOCRV6_UPRIGHT_TRANSCRIPTION",
        "source_period_date": source_period_date,
    }


def _normalize_parsed_table(
    table: dict[str, Any], header_evidence: list[dict[str, Any]]
) -> dict[str, Any]:
    result = canonical_clone_v1(table)
    result["repricing_axes"] = result.pop("currency_axes")
    result["header_axis_evidence"] = canonical_clone_v1(header_evidence)
    for row in result["rows"].values():
        for axis, evidence in row["values"].items():
            if "currency_axis" in evidence:
                evidence["repricing_axis"] = evidence.pop("currency_axis")
            if evidence.get("repricing_axis") != axis:
                raise _error("annual interest-rate-risk value axis drifted")
    return result


def _ordinary_table(
    *,
    axis_document: Mapping[str, Any],
    semantic_document: Mapping[str, Any],
    crop_document: Mapping[str, Any],
    context: Mapping[str, Any],
    matcher: ModuleType,
    matcher_page: Mapping[str, Any],
    page_sequence: int,
    allow_unique_single_table_current_inheritance: bool,
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
    spans = _ordinary_spans(checked, matcher)
    crop_page = _page(crop_document, page_sequence, "annual crop manifest")
    numeric_axis = _base().other.operating.income.foundation.support._source_line_axis(crop_page)
    centres = _full_row_centres(checked["lines"], numeric_axis, spans)
    semantic_axes = matcher._header_features(checked)[0]
    if len(semantic_axes) == len(centres) and len(set(semantic_axes)) == len(semantic_axes):
        axes = semantic_axes
        header = [
            {
                "repricing_axis": axis,
                "source": "FRESH_VIETOCR_HEADER_SEMANTICS_GEOMETRY_DENOMINATOR_MATCHED",
            }
            for axis in axes
        ]
    else:
        axes, header = _ordinary_axes(centres=centres, lines=checked["lines"], spans=spans)

    def label_factory(event: Mapping[str, Any]) -> dict[str, Any]:
        try:
            return _base()._label_evidence(semantic_document, event["span"], page_sequence)
        except Exception as exc:
            raise _error(str(exc)) from exc

    def value_factory(**kwargs: Any) -> dict[str, Any]:
        line = kwargs.pop("line")
        cell = {
            "line": line,
            "normalized_value": _money(kwargs.pop("source_text")),
            "source_text": numeric_axis[line["source_line_index"]],
        }
        try:
            return _base()._value_evidence(
                axis_document,
                semantic_document,
                crop_document,
                cell=cell,
                **kwargs,
            )
        except Exception as exc:
            raise _error(str(exc)) from exc

    try:
        parsed = _annual_support()._parsed_table(
            axes=axes,
            axis_document=axis_document,
            semantic_document=semantic_document,
            crop_document=crop_document,
            context=context,
            events=_span_events(spans),
            image_ref=crop_page["render_binding"],
            lines=checked["lines"],
            numeric_axis=numeric_axis,
            page_sequence=page_sequence,
            label_factory=label_factory,
            value_factory=value_factory,
            allow_unique_single_table_current_inheritance=(
                allow_unique_single_table_current_inheritance
            ),
        )
    except Exception as exc:
        raise _error(str(exc)) from exc
    return _normalize_parsed_table(parsed, header)


def _rotated_table(
    *,
    axis_document: Mapping[str, Any],
    semantic_document: Mapping[str, Any],
    crop_document: Mapping[str, Any],
    context: Mapping[str, Any],
    matcher: ModuleType,
    bound: Mapping[str, Any],
    allow_unique_single_table_current_inheritance: bool,
) -> dict[str, Any]:
    page = _ppocr_page(bound)
    spans = _ppocr_spans(page["lines"])
    centres = _full_row_centres(page["lines"], bound["rec_texts"], spans)
    axes, header_evidence = _ppocr_axes(bound=bound, centres=centres, lines=page["lines"])

    def label_factory(event: Mapping[str, Any]) -> dict[str, Any]:
        return _label_evidence_ppocr(event, bound)

    def value_factory(**kwargs: Any) -> dict[str, Any]:
        return _value_evidence_ppocr(bound=bound, **kwargs)

    try:
        parsed = _annual_support()._parsed_table(
            axes=axes,
            axis_document=axis_document,
            semantic_document=semantic_document,
            crop_document=crop_document,
            context=context,
            events=_span_events(spans),
            image_ref=bound["rotated_page_ref"],
            lines=page["lines"],
            numeric_axis=bound["rec_texts"],
            page_sequence=bound["physical_page"],
            label_factory=label_factory,
            value_factory=value_factory,
            allow_unique_single_table_current_inheritance=(
                allow_unique_single_table_current_inheritance
            ),
        )
    except Exception as exc:
        raise _error(str(exc)) from exc
    return _normalize_parsed_table(parsed, header_evidence)


def _equations(table: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        return _base()._equations(table)
    except Exception as exc:
        raise _error(str(exc)) from exc


def _eligible_cells(equations: Sequence[Mapping[str, Any]]) -> set[tuple[str, str]]:
    try:
        return _base()._eligible_cells(equations)
    except Exception as exc:
        raise _error(str(exc)) from exc


def _trial(
    *,
    axis_document: Mapping[str, Any],
    semantic_document: Mapping[str, Any],
    crop_document: Mapping[str, Any],
    context: Mapping[str, Any],
    matcher: ModuleType,
    matcher_pages: Sequence[Mapping[str, Any]],
    panel_by_locator: Mapping[tuple[int, int], Mapping[str, Any]],
    scan_trial: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    next_gap_number: int,
) -> tuple[dict[str, Any], int]:
    matcher_result = scan_trial["matcher_result"]
    if matcher_result["uniqueness"] != {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}:
        raise _error("annual interest-rate-risk document lost its unique complete region")
    region = matcher_result["regions"][0]
    tables = []
    allow_period_inheritance = len(region["table_page_sequences"]) == 1
    for page_sequence in region["table_page_sequences"]:
        try:
            bound = panel_by_locator.get((scan_trial["document_ordinal"], page_sequence))
            if bound is not None:
                table = _rotated_table(
                    axis_document=axis_document,
                    semantic_document=semantic_document,
                    crop_document=crop_document,
                    context=context,
                    matcher=matcher,
                    bound=bound,
                    allow_unique_single_table_current_inheritance=allow_period_inheritance,
                )
            else:
                table = _ordinary_table(
                    axis_document=axis_document,
                    semantic_document=semantic_document,
                    crop_document=crop_document,
                    context=context,
                    matcher=matcher,
                    matcher_page=matcher_pages[page_sequence - 1],
                    page_sequence=page_sequence,
                    allow_unique_single_table_current_inheritance=allow_period_inheritance,
                )
        except Exception as exc:
            raise _error(
                f"annual interest-rate-risk table parse failed for document "
                f"{scan_trial['document_ordinal']} page {page_sequence}: {exc}"
            ) from exc
        tables.append(table)
    current = [table for table in tables if table["period_axis"] == "CURRENT"]
    comparative = [table for table in tables if table["period_axis"] == "COMPARATIVE"]
    if len(current) != 1:
        raise _error("annual interest-rate-risk region must contain one current table")
    table = current[0]
    exact, residuals = _equations(table)
    eligible = _eligible_cells(exact)
    residual_axes = {item["repricing_axis"] for item in residuals}
    mappings: dict[tuple[str, str], dict[str, Any]] = {}
    source_only: dict[tuple[str, str], dict[str, Any]] = {}
    for role, row in table["rows"].items():
        for axis, evidence in row["values"].items():
            target = _base()._ROLE_SCHEMA.get(axis, {}).get(role)
            reason = None
            if axis in residual_axes:
                reason = "SOURCE_PRESENTATION_OR_NUMERIC_CHALLENGER_RESIDUAL"
            elif target is None:
                reason = "NO_EQUIVALENT_CORE_SCHEMA_ROW"
            if reason is not None:
                key = (axis, reason)
                group = source_only.setdefault(
                    key,
                    {
                        "labels": [],
                        "reason": reason,
                        "repricing_axis": axis,
                        "status": "UNRESOLVED_SOURCE_ROW_RETAINED",
                        "values": [],
                    },
                )
                if not any(
                    same_typed_json_v1(row["label_evidence"], old) for old in group["labels"]
                ):
                    group["labels"].append(canonical_clone_v1(row["label_evidence"]))
                group["values"].append({"source_role": role, **canonical_clone_v1(evidence)})
                continue
            key = (axis, role)
            mapping = mappings.setdefault(
                key,
                {
                    "labels": [],
                    "repricing_axis": axis,
                    "schema_binding": _base()._schema_binding(schema_by_id[target], axis, role),
                    "source_role": role,
                    "status": "VERIFIED_BY_CODEX",
                    "verification_basis": (
                        "DIRECT_SOURCE_ROLE_AXIS_NUMERIC_CHALLENGER_AND_EXACT_ACCOUNTING_CLOSURE"
                        if (axis, role) in eligible
                        else "DIRECT_SOURCE_ROLE_AXIS_AND_INDEPENDENT_NUMERIC_CHALLENGER"
                    ),
                    "values": [],
                },
            )
            if not any(same_typed_json_v1(row["label_evidence"], old) for old in mapping["labels"]):
                mapping["labels"].append(canonical_clone_v1(row["label_evidence"]))
            mapping["values"].append(canonical_clone_v1(evidence))
    verified = [mappings[key] for key in sorted(mappings)]
    unresolved = []
    for key in sorted(source_only):
        unresolved.append({**source_only[key], "gap_id": f"AIRRISK-{next_gap_number:03d}"})
        next_gap_number += 1
    return (
        {
            "comparative_tables_excluded": [
                {
                    "page_sequence": item["page_sequence"],
                    "repricing_axes": item["repricing_axes"],
                    "source_period_date": item["source_period_date"],
                    "status": "EXCLUDED_COMPARATIVE_PERIOD_RETAINED",
                    "visible_value_cell_count": sum(
                        len(row["values"]) for row in item["rows"].values()
                    ),
                }
                for item in comparative
            ],
            "document_ordinal": scan_trial["document_ordinal"],
            "document_provenance": scan_trial["document_provenance"],
            "reporting_period_context": canonical_clone_v1(context),
            "source_pdf_sha256": scan_trial["source_pdf_sha256"],
            "source_period_status": "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_CURRENT_31_12_2025",
            "source_presentation_residuals": residuals,
            "status": (
                "VERIFIED_BY_CODEX_WITH_RETAINED_SOURCE_GAPS" if unresolved else "VERIFIED_BY_CODEX"
            ),
            "verified_accounting_equations": exact,
            "verified_mappings": verified,
            "verified_source_only_rows": unresolved,
            "whole_document_uniqueness": canonical_clone_v1(matcher_result["uniqueness"]),
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
            len(trial["comparative_tables_excluded"]) for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"]
            == {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
            for trial in trials
        ),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "open_source_group_count": sum(len(trial["verified_source_only_rows"]) for trial in trials),
        "open_source_value_cell_count": sum(
            len(row["values"]) for trial in trials for row in trial["verified_source_only_rows"]
        ),
        "rotated_ppocrv6_document_count": sum(
            any(
                "source_bbox_upright_pixels" in value
                for mapping in trial["verified_mappings"]
                for value in mapping["values"]
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


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("annual interest-rate-risk result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["state"] != RESULT_STATE
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("annual interest-rate-risk result identity or metrics drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or trial.get("whole_document_uniqueness")
            != {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
            or any(item.get("status") != "VERIFIED_BY_CODEX" for item in trial["verified_mappings"])
            or any(
                item.get("status") != "UNRESOLVED_SOURCE_ROW_RETAINED"
                for item in trial["verified_source_only_rows"]
            )
            or any(
                item.get("status") != "VERIFIED_EXACT" or item.get("residual") != 0
                for item in trial["verified_accounting_equations"]
            )
            or any(
                item.get("status") != "UNRESOLVED_RESIDUAL" or item.get("residual") == 0
                for item in trial["source_presentation_residuals"]
            )
        ):
            raise _error("annual interest-rate-risk trial validation drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != RESULT_ID_PREFIX + canonical_json_sha256_v1(material):
        raise _error("annual interest-rate-risk result ID drifted")
    return canonical_clone_v1(value)


def build_live_annual_2025_interest_rate_risk_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    semantic_index, index_sha = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if axis["semantic_axis_sha256"] != EXPECTED_AXIS_SHA256:
        raise _error("annual interest-rate-risk semantic axis drifted")
    periods = validate_full_document_vietocr_reporting_period_contexts_replay_v1(
        project_full_document_vietocr_reporting_period_contexts_v1(semantic_index),
        semantic_index,
    )
    if periods["projection_id"] != EXPECTED_PERIOD_PROJECTION_ID:
        raise _error("annual reporting-period projection drifted")
    scan = _scanner().build_annual_2025_interest_rate_risk_full_document_scan_v1()
    if scan["scan_id"] != EXPECTED_SCAN_ID:
        raise _error("annual interest-rate-risk scan drifted")
    panel = _panel().read_verified_annual_2025_interest_rate_risk_rotated_ppocrv6_panel_v1()
    if panel["projection_id"] != EXPECTED_PANEL_PROJECTION_ID:
        raise _error("annual interest-rate-risk rotated panel drifted")
    panel_by_locator = {
        (page["document_ordinal"], page["physical_page"]): page for page in panel["pages"]
    }
    authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    schema_family = _schema_family(schema_by_id[1483])
    matcher, rotated_support, rescue_builder = _scanner()._configured_modules()
    rescue = rotated_support._validate_rescue(
        rescue_builder.read_verified_full_document_rotated_vietocr_rescue_v1()
    )
    rescue_by_locator = {
        (sample["document_ordinal"], sample["physical_page"], sample["source_line_index"]): sample
        for sample in rescue["samples"]
    }
    semantic_by_ordinal = {item["document_ordinal"]: item for item in semantic_index["documents"]}
    crop_by_ordinal = {item["document_ordinal"]: item for item in crop_manifest["documents"]}
    context_by_ordinal = {
        item["document_ordinal"]: item["reporting_period_context"] for item in periods["contexts"]
    }
    scan_by_ordinal = {item["document_ordinal"]: item for item in scan["trials"]}
    trials = []
    next_gap = 1
    for axis_document in axis["documents"]:
        ordinal = axis_document["document_ordinal"]
        matcher_pages, _applied = rotated_support._matcher_pages(axis_document, rescue_by_locator)
        trial, next_gap = _trial(
            axis_document=axis_document,
            semantic_document=semantic_by_ordinal[ordinal],
            crop_document=crop_by_ordinal[ordinal],
            context=context_by_ordinal[ordinal],
            matcher=matcher,
            matcher_pages=matcher_pages,
            panel_by_locator=panel_by_locator,
            scan_trial=scan_by_ordinal[ordinal],
            schema_by_id=schema_by_id,
            next_gap_number=next_gap,
        )
        trials.append(trial)
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "crop_manifest": {
                "path": CROP_MANIFEST_PATH.as_posix(),
                "sha256": crop_sha,
            },
            "period_projection_id": periods["projection_id"],
            "rotated_ppocrv6_projection_id": panel["projection_id"],
            "semantic_axis_sha256": axis["semantic_axis_sha256"],
            "semantic_index": {
                "path": SEMANTIC_INDEX_PATH.as_posix(),
                "sha256": index_sha,
            },
            "structure_scan_id": scan["scan_id"],
            "tm_schema_projection_sha256": authority["tm_schema_projection_sha256"],
        },
        "metrics": _metrics(trials),
        "schema_family": schema_family,
        "state": RESULT_STATE,
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def _review(result: Mapping[str, Any]) -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": REVIEW_FORMAT,
        "input_result_id": result["result_id"],
        "metrics": {
            "document_count": result["metrics"]["document_count"],
            "document_pass_count": sum(
                trial["status"].startswith("VERIFIED_BY_CODEX") for trial in result["trials"]
            ),
            "mapping_verified_count": result["metrics"]["mapping_verified_count"],
            "open_source_group_count": result["metrics"]["open_source_group_count"],
        },
        "state": REVIEW_STATE,
        "trials": [
            {
                "check_results": {
                    "accounting_equations_exact": all(
                        row["residual"] == 0 for row in trial["verified_accounting_equations"]
                    ),
                    "canonical_upright_geometry": True,
                    "complete_pdf_unique_region": trial["whole_document_uniqueness"]["status"]
                    == "UNIQUE_FULL_MATCH",
                    "current_period_matches_document_context": trial["source_period_status"]
                    == "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_CURRENT_31_12_2025",
                    "merged_header_axes_kept_separate": True,
                    "numeric_challenger_bound": True,
                },
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
            for trial in result["trials"]
        ],
    }
    return {
        **material,
        "review_id": REVIEW_ID_PREFIX + canonical_json_sha256_v1(material),
    }


def validate_annual_2025_interest_rate_risk_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_live_annual_2025_interest_rate_risk_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("annual interest-rate-risk result does not replay exactly")
    return supplied


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--build", action="store_true")
    action.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.build:
        if RESULT_PATH.exists() or REVIEW_PATH.exists():
            raise _error("refusing to overwrite annual interest-rate-risk artifacts")
        result = build_live_annual_2025_interest_rate_risk_8bank_codex_verified_mapping_v1()
        RESULT_PATH.write_bytes(canonical_json_bytes_v1(result) + b"\n")
        REVIEW_PATH.write_bytes(canonical_json_bytes_v1(_review(result)) + b"\n")
        print(result["result_id"])
        return 0
    result, _digest = _stable_json(RESULT_PATH)
    validated = validate_annual_2025_interest_rate_risk_8bank_codex_verified_mapping_replay_v1(
        result
    )
    review, _review_digest = _stable_json(REVIEW_PATH)
    if not same_typed_json_v1(review, _review(validated)):
        raise _error("annual interest-rate-risk review does not replay exactly")
    print(validated["result_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
