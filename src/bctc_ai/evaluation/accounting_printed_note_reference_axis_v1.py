"""Schema-blind printed note-reference/header column axis.

This primitive separates a printed ``Thuyết minh`` reference lane from the
financial body lanes using one exact page, repeated body centres, and adaptive
row affinity.  It has no family, bank, filing, period, page-number, schema, or
accounting-value routing authority.  Consumers must independently authenticate
the source snapshot and pixels before re-owning any numeric sample.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.evaluation import accounting_family_row_axis_v1 as row_v1
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.evaluation.adaptive_accounting_table_geometry_v1 import row_affinity_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FORMAT_VERSION = "ACCOUNTING_PRINTED_NOTE_REFERENCE_AXIS_V1"
CLAIM_BOUNDARY = (
    "ONE_EXACT_PAGE_SCHEMA_BLIND_PRINTED_THUYET_MINH_HEADER_AND_ADAPTIVE_ROW_"
    "AFFINITY_FINANCIAL_LANE_SEPARATION_ONLY_NO_FAMILY_BANK_FILE_PAGE_PERIOD_"
    "UNIT_SCHEMA_ACCOUNTING_OR_PIXEL_AUTHORITY"
)
READY_STATUS = "PRINTED_NOTE_REFERENCE_AXIS_BOUND_PROPOSAL_ONLY"
UNRESOLVED_STATUS = "UNRESOLVED_PRINTED_NOTE_REFERENCE_AXIS"

_AXIS_FIELDS = {
    "axis_id",
    "claim_boundary",
    "financial_column_centers",
    "format_version",
    "header",
    "input_binding",
    "rows",
    "status",
    "unresolved_reasons",
}
_HEADER_FIELDS = {"bbox", "normalized_surface", "sample_ids", "source_line_indices"}
_ROW_FIELDS = {
    "financial_sample_ids",
    "label_sample_ids",
    "note_reference",
    "note_sample_id",
    "source_line_index",
}
_INPUT_FIELDS = {
    "body_text_scale",
    "detected_column_centers",
    "lane_tolerance",
    "page_sequence",
    "page_sha256",
    "page_width",
}
_REFERENCE = re.compile(r"[1-9][0-9]{0,2}(?:\.[0-9]{1,2})?")
_ADMITTED_NUMERIC_CLASSIFICATIONS = {
    "DASH_ZERO",
    "MIXED_GROUPED_INTEGER_CANDIDATE",
    "NOISE_SUFFIXED_GROUPED_INTEGER_CANDIDATE",
    "SIGNED_NUMBER",
}
_MIN_BEST_ROW_AFFINITY_SEPARATION = 0.25


class AccountingPrintedNoteReferenceAxisV1Error(ValueError):
    """The schema-blind note-reference axis or exact replay drifted."""


def _error(message: str) -> AccountingPrintedNoteReferenceAxisV1Error:
    return AccountingPrintedNoteReferenceAxisV1Error(message)


def exact_note_reference_surface_v1(line: Mapping[str, Any]) -> str | None:
    try:
        vietocr = line["vietocr_text"].strip()
        numeric = line["numeric_recognition"]["raw_prediction"].strip()
    except (AttributeError, KeyError, TypeError):
        return None
    return vietocr if vietocr == numeric and _REFERENCE.fullmatch(vietocr) else None


def note_reference_parts_v1(surface: str) -> tuple[int, int | None]:
    if type(surface) is not str or _REFERENCE.fullmatch(surface) is None:
        raise _error("printed note reference is not one exact supported surface")
    major, separator, minor = surface.partition(".")
    return int(major), int(minor) if separator else None


def note_reference_has_local_peer_v1(
    candidate: str,
    references: Sequence[str],
) -> bool:
    major, minor = note_reference_parts_v1(candidate)
    parts = [note_reference_parts_v1(reference) for reference in references]
    if minor is None:
        return ((major - 1, None) in parts and (major + 1, None) in parts) or any(
            peer_major == major and peer_minor is not None for peer_major, peer_minor in parts
        )
    return any(
        peer_major == major and peer_minor is not None and abs(peer_minor - minor) == 1
        for peer_major, peer_minor in parts
    )


def same_visual_row_v1(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    *,
    body_text_scale: float,
) -> bool:
    try:
        affinity = row_affinity_v1(
            [left["bbox"]],
            right["bbox"],
            median_text_height=body_text_scale,
        )
        # Merely touching adjacent OCR boxes have a non-null but non-positive
        # affinity.  They are challengers, not evidence of one visual row.
        return affinity is not None and affinity > 0
    except (KeyError, TypeError, ValueError):
        return False


def _normalized_channels(line: Mapping[str, Any]) -> tuple[str, str]:
    return (
        normalize_vietnamese_anchor_v1(line["vietocr_text"]),
        normalize_vietnamese_anchor_v1(line["numeric_recognition"]["raw_prediction"]),
    )


def _surfaces_are_nonnumeric(line: Mapping[str, Any]) -> bool:
    return all(
        not any(character.isdigit() for character in surface)
        and row_v1.parse_visible_financial_numeric_token_v1(surface)["classification"]
        not in _ADMITTED_NUMERIC_CLASSIFICATIONS
        for surface in (
            line["vietocr_text"],
            line["numeric_recognition"]["raw_prediction"],
        )
    )


def _header_candidates(page: Mapping[str, Any]) -> list[dict[str, Any]]:
    lines = [
        line
        for line in page["lines"]
        if line["vietocr_text"].strip() and line["numeric_recognition"]["raw_prediction"].strip()
    ]
    candidates = []
    for line in lines:
        if _normalized_channels(line) == ("thuyet minh", "thuyet minh"):
            candidates.append({"bbox": canonical_clone_v1(line["bbox"]), "lines": [line]})
    for upper in (line for line in lines if _normalized_channels(line) == ("thuyet", "thuyet")):
        for lower in (line for line in lines if _normalized_channels(line) == ("minh", "minh")):
            upper_bbox = upper["bbox"]
            lower_bbox = lower["bbox"]
            overlap = min(upper_bbox[2], lower_bbox[2]) - max(upper_bbox[0], lower_bbox[0])
            vertical_gap = max(0, lower_bbox[1] - upper_bbox[3])
            if (
                lower_bbox[1] <= upper_bbox[1]
                or 2 * overlap < min(upper_bbox[2] - upper_bbox[0], lower_bbox[2] - lower_bbox[0])
                or vertical_gap > max(upper_bbox[3] - upper_bbox[1], lower_bbox[3] - lower_bbox[1])
            ):
                continue
            candidates.append(
                {
                    "bbox": [
                        min(upper_bbox[0], lower_bbox[0]),
                        min(upper_bbox[1], lower_bbox[1]),
                        max(upper_bbox[2], lower_bbox[2]),
                        max(upper_bbox[3], lower_bbox[3]),
                    ],
                    "lines": [upper, lower],
                }
            )
    by_samples = {
        tuple(line["sample_id"] for line in candidate["lines"]): candidate
        for candidate in candidates
    }
    return [by_samples[key] for key in sorted(key for key in by_samples)]


def _best_row_line(
    *,
    note_line: Mapping[str, Any],
    lines: Sequence[Mapping[str, Any]],
    body_text_scale: float,
) -> Mapping[str, Any] | None:
    scored = []
    for line in lines:
        affinity = row_affinity_v1(
            [note_line["bbox"]], line["bbox"], median_text_height=body_text_scale
        )
        if affinity is not None and affinity > 0:
            scored.append((affinity, line))
    if not scored:
        return None
    scored.sort(key=lambda item: (-item[0], item[1]["line_ordinal"], item[1]["sample_id"]))
    if len(scored) > 1 and scored[0][0] - scored[1][0] <= _MIN_BEST_ROW_AFFINITY_SEPARATION:
        return None
    return scored[0][1]


def _best_row_labels(
    *,
    note_line: Mapping[str, Any],
    lines: Sequence[Mapping[str, Any]],
    body_text_scale: float,
) -> list[Mapping[str, Any]]:
    scored = []
    for line in lines:
        affinity = row_affinity_v1(
            [note_line["bbox"]], line["bbox"], median_text_height=body_text_scale
        )
        if affinity is not None and affinity > 0:
            scored.append((affinity, line))
    if not scored:
        return []
    best = max(affinity for affinity, _line in scored)
    return sorted(
        (line for affinity, line in scored if best - affinity <= _MIN_BEST_ROW_AFFINITY_SEPARATION),
        key=lambda line: (line["line_ordinal"], line["sample_id"]),
    )


def _material(
    page: Mapping[str, Any],
    *,
    detected_column_centers: Sequence[float],
    lane_tolerance: float,
    body_text_scale: float,
) -> dict[str, Any]:
    page_width = page.get("page_width")
    if (
        type(page) is not dict
        or type(page.get("page_sequence")) is not int
        or page["page_sequence"] <= 0
        or type(page_width) is not int
        or page_width <= 0
        or type(page.get("lines")) is not list
        or type(detected_column_centers) not in {list, tuple}
        or len(detected_column_centers) < 2
        or any(
            type(center) is not float or not math.isfinite(center)
            for center in detected_column_centers
        )
        or list(detected_column_centers) != sorted(set(detected_column_centers))
        or type(lane_tolerance) is not float
        or not math.isfinite(lane_tolerance)
        or lane_tolerance <= 0
        or type(body_text_scale) is not float
        or not math.isfinite(body_text_scale)
        or body_text_scale <= 0
    ):
        raise _error("printed note-reference page or detected lane input drifted")
    page_sha256 = canonical_json_sha256_v1(page)
    input_binding = {
        "body_text_scale": body_text_scale,
        "detected_column_centers": list(detected_column_centers),
        "lane_tolerance": lane_tolerance,
        "page_sequence": page["page_sequence"],
        "page_sha256": page_sha256,
        "page_width": page_width,
    }
    headers = _header_candidates(page)
    if len(headers) != 1:
        return {
            "claim_boundary": CLAIM_BOUNDARY,
            "financial_column_centers": [],
            "format_version": FORMAT_VERSION,
            "header": None,
            "input_binding": input_binding,
            "rows": [],
            "status": UNRESOLVED_STATUS,
            "unresolved_reasons": ["EXACT_UNIQUE_THUYET_MINH_HEADER_NOT_ESTABLISHED"],
        }
    header = headers[0]
    header_bbox = header["bbox"]
    financial_centers = [
        center
        for center in detected_column_centers
        if math.floor(center - lane_tolerance) >= header_bbox[2]
    ]
    if len(detected_column_centers) - len(financial_centers) > 1:
        return {
            "claim_boundary": CLAIM_BOUNDARY,
            "financial_column_centers": [],
            "format_version": FORMAT_VERSION,
            "header": None,
            "input_binding": input_binding,
            "rows": [],
            "status": UNRESOLVED_STATUS,
            "unresolved_reasons": ["MULTIPLE_NONFINANCIAL_HEADER_LANES_NOT_EXCLUSIVE"],
        }
    if len(financial_centers) < 2:
        return {
            "claim_boundary": CLAIM_BOUNDARY,
            "financial_column_centers": [],
            "format_version": FORMAT_VERSION,
            "header": None,
            "input_binding": input_binding,
            "rows": [],
            "status": UNRESOLVED_STATUS,
            "unresolved_reasons": ["TWO_FINANCIAL_BODY_LANES_RIGHT_OF_HEADER_NOT_ESTABLISHED"],
        }
    first_financial_left = math.floor(financial_centers[0] - lane_tolerance)
    rows = []
    for note_line in page["lines"]:
        reference = exact_note_reference_surface_v1(note_line)
        bbox = note_line["bbox"]
        if (
            reference is None
            or bbox[1] < header_bbox[3]
            or bbox[0] < header_bbox[0]
            or bbox[2] > header_bbox[2]
            or bbox[2] > first_financial_left
            or bbox[2] - bbox[0] > header_bbox[2] - header_bbox[0]
        ):
            continue
        financial_ids = []
        for center in financial_centers:
            lane_lines = []
            for line in page["lines"]:
                parsed = row_v1.parse_visible_financial_numeric_token_v1(
                    line["numeric_recognition"]["raw_prediction"]
                )
                line_center = (line["bbox"][0] + line["bbox"][2]) / 2
                if (
                    line["sample_id"] != note_line["sample_id"]
                    and parsed["classification"] in _ADMITTED_NUMERIC_CLASSIFICATIONS
                    and line_center >= first_financial_left
                    and line["bbox"][0] > bbox[2]
                    and abs(line_center - center) <= lane_tolerance
                ):
                    lane_lines.append(line)
            selected = _best_row_line(
                note_line=note_line,
                lines=lane_lines,
                body_text_scale=body_text_scale,
            )
            if selected is None:
                financial_ids = []
                break
            financial_ids.append(selected["sample_id"])
        if not financial_ids:
            continue
        selected_ids = set(financial_ids)
        conflicting = []
        for line in page["lines"]:
            parsed = row_v1.parse_visible_financial_numeric_token_v1(
                line["numeric_recognition"]["raw_prediction"]
            )
            line_center = (line["bbox"][0] + line["bbox"][2]) / 2
            if (
                line["sample_id"] not in selected_ids
                and line["sample_id"] != note_line["sample_id"]
                and first_financial_left <= line_center <= financial_centers[-1] + lane_tolerance
                and parsed["classification"] in _ADMITTED_NUMERIC_CLASSIFICATIONS
                and same_visual_row_v1(note_line, line, body_text_scale=body_text_scale)
            ):
                conflicting.append(line)
        if conflicting:
            continue
        labels = _best_row_labels(
            note_line=note_line,
            lines=[
                line
                for line in page["lines"]
                if line["bbox"][2] <= bbox[0]
                and _surfaces_are_nonnumeric(line)
                and (
                    line["vietocr_text"].strip()
                    or line["numeric_recognition"]["raw_prediction"].strip()
                )
            ],
            body_text_scale=body_text_scale,
        )
        if not labels:
            continue
        rows.append(
            {
                "financial_sample_ids": financial_ids,
                "label_sample_ids": [line["sample_id"] for line in labels],
                "note_reference": reference,
                "note_sample_id": note_line["sample_id"],
                "source_line_index": note_line["line_ordinal"],
            }
        )
    rows.sort(key=lambda item: (item["source_line_index"], item["note_reference"]))
    reasons = []
    references = [row["note_reference"] for row in rows]
    note_ids = [row["note_sample_id"] for row in rows]
    financial_ids = [sample for row in rows for sample in row["financial_sample_ids"]]
    if len(references) != len(set(references)):
        reasons.append("NOTE_REFERENCE_SURFACES_REPEAT")
    if len(note_ids) != len(set(note_ids)):
        reasons.append("NOTE_REFERENCE_SOURCE_SAMPLES_REPEAT")
    if len(financial_ids) != len(set(financial_ids)):
        reasons.append("FINANCIAL_SOURCE_SAMPLE_ASSIGNED_TO_MULTIPLE_ROWS")
    header_record = {
        "bbox": canonical_clone_v1(header_bbox),
        "normalized_surface": "thuyet minh",
        "sample_ids": [line["sample_id"] for line in header["lines"]],
        "source_line_indices": [line["line_ordinal"] for line in header["lines"]],
    }
    return {
        "claim_boundary": CLAIM_BOUNDARY,
        "financial_column_centers": canonical_clone_v1(financial_centers),
        "format_version": FORMAT_VERSION,
        "header": header_record,
        "input_binding": input_binding,
        "rows": rows if not reasons else [],
        "status": READY_STATUS if rows and not reasons else UNRESOLVED_STATUS,
        "unresolved_reasons": reasons or ([] if rows else ["NO_COMPLETE_NOTE_REFERENCE_ROWS"]),
    }


def build_accounting_printed_note_reference_axis_v1(
    page: Mapping[str, Any],
    *,
    detected_column_centers: Sequence[float],
    lane_tolerance: float,
    body_text_scale: float,
) -> dict[str, Any]:
    material = _material(
        page,
        detected_column_centers=detected_column_centers,
        lane_tolerance=lane_tolerance,
        body_text_scale=body_text_scale,
    )
    return validate_accounting_printed_note_reference_axis_v1(
        {**material, "axis_id": "apnrav1:axis:" + canonical_json_sha256_v1(material)}
    )


def validate_accounting_printed_note_reference_axis_v1(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _AXIS_FIELDS
        or value.get("format_version") != FORMAT_VERSION
        or value.get("claim_boundary") != CLAIM_BOUNDARY
        or value.get("status") not in {READY_STATUS, UNRESOLVED_STATUS}
        or type(value.get("unresolved_reasons")) is not list
        or any(type(reason) is not str or not reason for reason in value["unresolved_reasons"])
        or (value["status"] == READY_STATUS) is bool(value["unresolved_reasons"])
        or type(value.get("input_binding")) is not dict
        or set(value["input_binding"]) != _INPUT_FIELDS
        or type(value.get("rows")) is not list
        or type(value.get("financial_column_centers")) is not list
        or any(
            type(center) is not float or not math.isfinite(center)
            for center in value["financial_column_centers"]
        )
        or value["financial_column_centers"] != sorted(set(value["financial_column_centers"]))
    ):
        raise _error("printed note-reference axis shape drifted")
    binding = value["input_binding"]
    if (
        type(binding["body_text_scale"]) is not float
        or not math.isfinite(binding["body_text_scale"])
        or binding["body_text_scale"] <= 0
        or type(binding["detected_column_centers"]) is not list
        or any(
            type(center) is not float or not math.isfinite(center)
            for center in binding["detected_column_centers"]
        )
        or binding["detected_column_centers"] != sorted(set(binding["detected_column_centers"]))
        or type(binding["lane_tolerance"]) is not float
        or not math.isfinite(binding["lane_tolerance"])
        or binding["lane_tolerance"] <= 0
        or type(binding["page_sequence"]) is not int
        or binding["page_sequence"] <= 0
        or type(binding["page_sha256"]) is not str
        or re.fullmatch(r"[0-9a-f]{64}", binding["page_sha256"]) is None
        or type(binding["page_width"]) is not int
        or binding["page_width"] <= 0
        or any(
            center not in binding["detected_column_centers"]
            for center in value["financial_column_centers"]
        )
    ):
        raise _error("printed note-reference exact input binding drifted")
    header = value["header"]
    if header is not None and (
        type(header) is not dict
        or set(header) != _HEADER_FIELDS
        or header["normalized_surface"] != "thuyet minh"
        or type(header["bbox"]) is not list
        or len(header["bbox"]) != 4
        or any(type(coordinate) is not int or coordinate < 0 for coordinate in header["bbox"])
        or header["bbox"][2] <= header["bbox"][0]
        or header["bbox"][3] <= header["bbox"][1]
        or type(header["sample_ids"]) is not list
        or not header["sample_ids"]
        or any(type(sample_id) is not str or not sample_id for sample_id in header["sample_ids"])
        or len(header["sample_ids"]) != len(set(header["sample_ids"]))
        or type(header["source_line_indices"]) is not list
        or len(header["source_line_indices"]) != len(header["sample_ids"])
        or any(
            type(line_index) is not int or line_index < 0
            for line_index in header["source_line_indices"]
        )
    ):
        raise _error("printed note-reference header shape drifted")
    for row in value["rows"]:
        if (
            type(row) is not dict
            or set(row) != _ROW_FIELDS
            or exact_note_reference_surface_v1(
                {
                    "vietocr_text": row["note_reference"],
                    "numeric_recognition": {"raw_prediction": row["note_reference"]},
                }
            )
            != row["note_reference"]
            or type(row["note_sample_id"]) is not str
            or not row["note_sample_id"]
            or type(row["source_line_index"]) is not int
            or row["source_line_index"] < 0
            or type(row["label_sample_ids"]) is not list
            or not row["label_sample_ids"]
            or any(
                type(sample_id) is not str or not sample_id for sample_id in row["label_sample_ids"]
            )
            or len(row["label_sample_ids"]) != len(set(row["label_sample_ids"]))
            or type(row["financial_sample_ids"]) is not list
            or len(row["financial_sample_ids"]) != len(value["financial_column_centers"])
            or any(
                type(sample_id) is not str or not sample_id
                for sample_id in row["financial_sample_ids"]
            )
            or len(row["financial_sample_ids"]) != len(set(row["financial_sample_ids"]))
        ):
            raise _error("printed note-reference row shape drifted")
    references = [row["note_reference"] for row in value["rows"]]
    note_ids = [row["note_sample_id"] for row in value["rows"]]
    financial_ids = [
        sample_id for row in value["rows"] for sample_id in row["financial_sample_ids"]
    ]
    if (
        value["rows"]
        != sorted(
            value["rows"],
            key=lambda row: (row["source_line_index"], row["note_reference"]),
        )
        or len(references) != len(set(references))
        or len(note_ids) != len(set(note_ids))
        or len(financial_ids) != len(set(financial_ids))
        or (
            value["status"] == READY_STATUS
            and (header is None or len(value["financial_column_centers"]) < 2 or not value["rows"])
        )
        or (value["status"] == UNRESOLVED_STATUS and value["rows"])
    ):
        raise _error("printed note-reference axis exclusivity drifted")
    material = canonical_clone_v1(value)
    axis_id = material.pop("axis_id", None)
    if axis_id != "apnrav1:axis:" + canonical_json_sha256_v1(material):
        raise _error("printed note-reference axis identity drifted")
    return canonical_clone_v1(value)


def validate_accounting_printed_note_reference_axis_replay_v1(
    value: Any,
    page: Mapping[str, Any],
    *,
    detected_column_centers: Sequence[float],
    lane_tolerance: float,
    body_text_scale: float,
) -> dict[str, Any]:
    typed = validate_accounting_printed_note_reference_axis_v1(value)
    rebuilt = build_accounting_printed_note_reference_axis_v1(
        page,
        detected_column_centers=detected_column_centers,
        lane_tolerance=lane_tolerance,
        body_text_scale=body_text_scale,
    )
    if not same_typed_json_v1(typed, rebuilt):
        raise _error("printed note-reference axis does not replay exactly")
    return typed
