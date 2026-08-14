"""Deterministically assign ordered row labels to fixed monetary lanes using geometry only.

The mechanism is deliberately narrower than an accounting observation.  It
receives already selected row-label boxes, numeric-cell boxes, and ordered lane
header boxes.  It never reads text, values, bank identity, filenames, page
numbers, schema, or history.  Source line order prevents a label whose box
slightly overlaps the next row from absorbing that next row's values.

Out-of-lane numeric companions remain explicit and make the assignment
unresolved.  A later typed multi-lane contract may admit them; this primitive
must not silently discard percentage or other parallel axes.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "CLAIM_BOUNDARY",
    "FORMAT_VERSION",
    "OrderedRowValueLaneAssignmentV1Error",
    "build_ordered_row_value_lane_assignment_v1",
    "validate_ordered_row_value_lane_assignment_replay_v1",
]


FORMAT_VERSION = "BANK_CORPUS_ORDERED_ROW_VALUE_LANE_ASSIGNMENT_V1"
CLAIM_BOUNDARY = (
    "ORDERED_ROW_LABEL_TO_FIXED_LANE_GEOMETRY_ASSIGNMENT_ONLY_"
    "OUT_OF_LANE_NUMERIC_COMPANIONS_FAIL_CLOSED_NO_SEMANTIC_NUMERIC_"
    "ACCOUNTING_GRAPH_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
RESOLVED_STATUS = "RESOLVED_ORDERED_ROW_VALUE_LANES"
UNRESOLVED_STATUS = "UNRESOLVED_ORDERED_ROW_VALUE_LANES"
_ASSIGNMENT_PREFIX = "orvla1:assignment:"
_ROLE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_ROW_FIELDS = {"bbox", "role", "source_line_index"}
_CELL_FIELDS = {"bbox", "source_line_index"}
_RESULT_FIELDS = {
    "assignment_id",
    "claim_boundary",
    "format_version",
    "input_sha256",
    "lane_centers_x2",
    "metrics",
    "rows",
    "safety",
    "status",
    "unresolved_reasons",
}
_RESULT_ROW_FIELDS = {
    "companion_numeric_source_line_indices",
    "role",
    "row_source_line_index",
    "status",
    "unresolved_reasons",
    "value_source_line_indices",
}
_METRIC_FIELDS = {
    "assigned_value_count",
    "companion_numeric_count",
    "lane_count",
    "resolved_row_count",
    "row_count",
    "unresolved_row_count",
}
_SAFETY = {
    "accounting_authority": False,
    "bank_filename_page_identity_used": False,
    "extra_numeric_lanes_silently_discarded": False,
    "geometry_and_source_line_order_only": True,
    "mapping_authority": False,
    "numeric_text_or_value_used": False,
    "output_is_accepted_graph": False,
    "schema_authority": False,
    "semantic_text_used": False,
}


class OrderedRowValueLaneAssignmentV1Error(ValueError):
    """The ordered row/lane input or deterministic replay is invalid."""


def _error(message: str) -> OrderedRowValueLaneAssignmentV1Error:
    return OrderedRowValueLaneAssignmentV1Error(message)


def _exact_mapping(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise _error(f"{label} fields drifted")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise _error(f"{label} must be one non-negative integer")
    return value


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} must be one positive integer")
    return value


def _bbox(value: Any, label: str) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or value[0] < 0
        or value[1] < 0
        or value[0] >= value[2]
        or value[1] >= value[3]
    ):
        raise _error(f"{label} must be one positive integer bbox")
    return list(value)


def _center_x2(box: Sequence[int]) -> int:
    return box[0] + box[2]


def _center_y2(box: Sequence[int]) -> int:
    return box[1] + box[3]


def _height(box: Sequence[int]) -> int:
    return box[3] - box[1]


def _validate_inputs(
    row_labels: Any,
    numeric_cells: Any,
    lane_header_bboxes: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[list[int]]]:
    if (
        isinstance(row_labels, (str, bytes, bytearray))
        or not isinstance(row_labels, Sequence)
        or not row_labels
    ):
        raise _error("row labels must be one non-empty sequence")
    if (
        isinstance(numeric_cells, (str, bytes, bytearray))
        or not isinstance(numeric_cells, Sequence)
        or not numeric_cells
    ):
        raise _error("numeric cells must be one non-empty sequence")
    if (
        isinstance(lane_header_bboxes, (str, bytes, bytearray))
        or not isinstance(lane_header_bboxes, Sequence)
        or len(lane_header_bboxes) < 2
    ):
        raise _error("lane headers must contain at least two ordered boxes")

    rows: list[dict[str, Any]] = []
    roles: set[str] = set()
    row_lines: set[int] = set()
    for index, raw in enumerate(row_labels):
        row = _exact_mapping(raw, _ROW_FIELDS, f"row label {index}")
        role = row["role"]
        if type(role) is not str or _ROLE_RE.fullmatch(role) is None or role in roles:
            raise _error("row roles must be unique uppercase identifiers")
        line = _nonnegative_int(row["source_line_index"], f"row label {index} line")
        if line in row_lines:
            raise _error("row labels repeat one source line")
        roles.add(role)
        row_lines.add(line)
        rows.append(
            {
                "role": role,
                "source_line_index": line,
                "bbox": _bbox(row["bbox"], f"row label {index} bbox"),
            }
        )

    row_y = [_center_y2(row["bbox"]) for row in rows]
    row_order = [row["source_line_index"] for row in rows]
    if row_y != sorted(row_y) or len(set(row_y)) != len(row_y):
        raise _error("row label centers must be strictly top-to-bottom")
    if row_order != sorted(row_order):
        raise _error("row label source lines must be strictly ordered")

    cells: list[dict[str, Any]] = []
    cell_lines: set[int] = set()
    for index, raw in enumerate(numeric_cells):
        cell = _exact_mapping(raw, _CELL_FIELDS, f"numeric cell {index}")
        line = _nonnegative_int(cell["source_line_index"], f"numeric cell {index} line")
        if line in cell_lines:
            raise _error("numeric cells repeat one source line")
        cell_lines.add(line)
        cells.append(
            {
                "source_line_index": line,
                "bbox": _bbox(cell["bbox"], f"numeric cell {index} bbox"),
            }
        )

    cell_order = [cell["source_line_index"] for cell in cells]
    if cell_order != sorted(cell_order):
        raise _error("numeric cell source lines must be strictly ordered")
    if row_lines & cell_lines:
        raise _error("row labels and numeric cells cannot share one source line")

    lanes = [
        _bbox(raw, f"lane header {index} bbox") for index, raw in enumerate(lane_header_bboxes)
    ]
    centers = [_center_x2(box) for box in lanes]
    if centers != sorted(centers) or len(set(centers)) != len(centers):
        raise _error("lane header centers must be strictly left-to-right")
    return rows, cells, lanes


def _input_payload(
    rows: Sequence[Mapping[str, Any]],
    cells: Sequence[Mapping[str, Any]],
    lanes: Sequence[Sequence[int]],
) -> dict[str, Any]:
    return {
        "lane_header_bboxes": [list(box) for box in lanes],
        "numeric_cells": [canonical_clone_v1(dict(cell)) for cell in cells],
        "row_labels": [canonical_clone_v1(dict(row)) for row in rows],
    }


def _vertically_admissible(row: Mapping[str, Any], cell: Mapping[str, Any]) -> bool:
    # Centers are doubled integers.  This is exactly |dy| <= 0.75 * max(height).
    center_delta_x2 = abs(_center_y2(row["bbox"]) - _center_y2(cell["bbox"]))
    return 2 * center_delta_x2 <= 3 * max(_height(row["bbox"]), _height(cell["bbox"]))


def _row_window_contains(
    rows: Sequence[Mapping[str, Any]], row_index: int, cell: Mapping[str, Any]
) -> bool:
    line = cell["source_line_index"]
    if line <= rows[row_index]["source_line_index"]:
        return False
    if row_index + 1 < len(rows) and line >= rows[row_index + 1]["source_line_index"]:
        return False
    return _vertically_admissible(rows[row_index], cell)


def _matching_lanes(cell: Mapping[str, Any], lane_centers_x2: Sequence[int]) -> list[int]:
    span_x2 = lane_centers_x2[-1] - lane_centers_x2[0]
    center_x2 = _center_x2(cell["bbox"])
    return [
        lane_index
        for lane_index, lane_center_x2 in enumerate(lane_centers_x2)
        if 4 * abs(center_x2 - lane_center_x2) <= span_x2
    ]


def _build(
    rows: Sequence[Mapping[str, Any]],
    cells: Sequence[Mapping[str, Any]],
    lanes: Sequence[Sequence[int]],
) -> dict[str, Any]:
    lane_centers_x2 = [_center_x2(box) for box in lanes]
    result_rows: list[dict[str, Any]] = []
    global_reasons: list[str] = []
    assigned_count = 0
    companion_count = 0
    resolved_count = 0

    for row_index, row in enumerate(rows):
        by_lane: dict[int, list[Mapping[str, Any]]] = {
            lane_index: [] for lane_index in range(len(lanes))
        }
        companions: list[int] = []
        row_reasons: list[str] = []
        for cell in cells:
            if not _row_window_contains(rows, row_index, cell):
                continue
            matches = _matching_lanes(cell, lane_centers_x2)
            if len(matches) == 1:
                by_lane[matches[0]].append(cell)
            elif not matches:
                companions.append(cell["source_line_index"])
            else:
                row_reasons.append("AMBIGUOUS_NUMERIC_TO_LANE_GEOMETRY")

        selected: list[int] = []
        for lane_index in range(len(lanes)):
            candidates = by_lane[lane_index]
            if not candidates:
                row_reasons.append(f"MISSING_VALUE_FOR_LANE_{lane_index}")
            elif len(candidates) > 1:
                row_reasons.append(f"DUPLICATE_VALUES_FOR_LANE_{lane_index}")
            else:
                selected.append(candidates[0]["source_line_index"])
        if companions:
            row_reasons.append("UNTYPED_NUMERIC_COMPANION_LANES")
        row_reasons = sorted(set(row_reasons))
        resolved = not row_reasons and len(selected) == len(lanes)
        if resolved:
            resolved_count += 1
            assigned_count += len(selected)
            status = "RESOLVED_ROW_VALUE_LANES"
        else:
            status = "UNRESOLVED_ROW_VALUE_LANES"
            global_reasons.extend(f"{row['role']}:{reason}" for reason in row_reasons)
        companion_count += len(companions)
        result_rows.append(
            {
                "companion_numeric_source_line_indices": sorted(companions),
                "role": row["role"],
                "row_source_line_index": row["source_line_index"],
                "status": status,
                "unresolved_reasons": row_reasons,
                "value_source_line_indices": selected if resolved else [],
            }
        )

    status = RESOLVED_STATUS if resolved_count == len(rows) else UNRESOLVED_STATUS
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_sha256": canonical_json_sha256_v1(_input_payload(rows, cells, lanes)),
        "lane_centers_x2": lane_centers_x2,
        "metrics": {
            "assigned_value_count": assigned_count,
            "companion_numeric_count": companion_count,
            "lane_count": len(lanes),
            "resolved_row_count": resolved_count,
            "row_count": len(rows),
            "unresolved_row_count": len(rows) - resolved_count,
        },
        "rows": result_rows,
        "safety": canonical_clone_v1(_SAFETY),
        "status": status,
        "unresolved_reasons": sorted(set(global_reasons)),
    }
    return {**material, "assignment_id": _ASSIGNMENT_PREFIX + canonical_json_sha256_v1(material)}


def _validate_result(value: Any) -> dict[str, Any]:
    result = _exact_mapping(value, _RESULT_FIELDS, "ordered row/value assignment")
    if (
        result["format_version"] != FORMAT_VERSION
        or result["claim_boundary"] != CLAIM_BOUNDARY
        or result["status"] not in {RESOLVED_STATUS, UNRESOLVED_STATUS}
        or type(result["rows"]) is not list
        or not result["rows"]
        or type(result["unresolved_reasons"]) is not list
        or any(type(item) is not str for item in result["unresolved_reasons"])
        or result["unresolved_reasons"] != sorted(set(result["unresolved_reasons"]))
        or not same_typed_json_v1(result["safety"], _SAFETY)
    ):
        raise _error("ordered row/value assignment contract drifted")
    if (
        type(result["input_sha256"]) is not str
        or re.fullmatch(r"[0-9a-f]{64}", result["input_sha256"]) is None
    ):
        raise _error("ordered row/value assignment input identity drifted")
    lane_centers = result["lane_centers_x2"]
    if (
        type(lane_centers) is not list
        or len(lane_centers) < 2
        or any(type(item) is not int for item in lane_centers)
        or lane_centers != sorted(lane_centers)
        or len(set(lane_centers)) != len(lane_centers)
    ):
        raise _error("ordered row/value assignment lane centers drifted")
    metrics = _exact_mapping(result["metrics"], _METRIC_FIELDS, "assignment metrics")
    for field in _METRIC_FIELDS - {"lane_count", "row_count"}:
        _nonnegative_int(metrics[field], f"assignment metrics {field}")
    _positive_int(metrics["lane_count"], "assignment metrics lane_count")
    _positive_int(metrics["row_count"], "assignment metrics row_count")
    if metrics["lane_count"] != len(lane_centers) or metrics["row_count"] != len(result["rows"]):
        raise _error("ordered row/value assignment metric denominator drifted")

    roles: set[str] = set()
    row_lines: list[int] = []
    derived_reasons: list[str] = []
    derived_resolved_count = 0
    derived_assigned_count = 0
    derived_companion_count = 0
    for index, row in enumerate(result["rows"]):
        record = _exact_mapping(row, _RESULT_ROW_FIELDS, f"assignment row {index}")
        if (
            type(record["role"]) is not str
            or _ROLE_RE.fullmatch(record["role"]) is None
            or record["role"] in roles
            or record["status"] not in {"RESOLVED_ROW_VALUE_LANES", "UNRESOLVED_ROW_VALUE_LANES"}
            or type(record["unresolved_reasons"]) is not list
            or any(type(item) is not str for item in record["unresolved_reasons"])
            or record["unresolved_reasons"] != sorted(set(record["unresolved_reasons"]))
            or type(record["value_source_line_indices"]) is not list
            or any(
                type(item) is not int or item < 0 for item in record["value_source_line_indices"]
            )
            or len(set(record["value_source_line_indices"]))
            != len(record["value_source_line_indices"])
            or type(record["companion_numeric_source_line_indices"]) is not list
            or any(
                type(item) is not int or item < 0
                for item in record["companion_numeric_source_line_indices"]
            )
            or record["companion_numeric_source_line_indices"]
            != sorted(set(record["companion_numeric_source_line_indices"]))
        ):
            raise _error("ordered row/value assignment row contract drifted")
        row_line = _nonnegative_int(
            record["row_source_line_index"], f"assignment row {index} source line"
        )
        roles.add(record["role"])
        row_lines.append(row_line)
        derived_companion_count += len(record["companion_numeric_source_line_indices"])
        if record["status"] == "RESOLVED_ROW_VALUE_LANES":
            if (
                record["unresolved_reasons"]
                or record["companion_numeric_source_line_indices"]
                or len(record["value_source_line_indices"]) != metrics["lane_count"]
                or any(item <= row_line for item in record["value_source_line_indices"])
            ):
                raise _error("resolved ordered row/value assignment is incoherent")
            derived_resolved_count += 1
            derived_assigned_count += len(record["value_source_line_indices"])
        elif not record["unresolved_reasons"] or record["value_source_line_indices"]:
            raise _error("unresolved ordered row/value assignment is incoherent")
        else:
            derived_reasons.extend(
                f"{record['role']}:{reason}" for reason in record["unresolved_reasons"]
            )

    if row_lines != sorted(row_lines) or len(set(row_lines)) != len(row_lines):
        raise _error("ordered row/value assignment output row order drifted")
    derived_unresolved_count = len(result["rows"]) - derived_resolved_count
    if not same_typed_json_v1(
        metrics,
        {
            "assigned_value_count": derived_assigned_count,
            "companion_numeric_count": derived_companion_count,
            "lane_count": len(lane_centers),
            "resolved_row_count": derived_resolved_count,
            "row_count": len(result["rows"]),
            "unresolved_row_count": derived_unresolved_count,
        },
    ):
        raise _error("ordered row/value assignment metrics are incoherent")
    expected_status = RESOLVED_STATUS if not derived_unresolved_count else UNRESOLVED_STATUS
    if result["status"] != expected_status or result["unresolved_reasons"] != sorted(
        set(derived_reasons)
    ):
        raise _error("ordered row/value assignment status is incoherent")

    material = canonical_clone_v1(result)
    identifier = material.pop("assignment_id")
    if type(identifier) is not str:
        raise _error("ordered row/value assignment identity drifted")
    if identifier != _ASSIGNMENT_PREFIX + canonical_json_sha256_v1(material):
        raise _error("ordered row/value assignment identity drifted")
    return canonical_clone_v1(result)


def build_ordered_row_value_lane_assignment_v1(
    row_labels: Sequence[Mapping[str, Any]],
    numeric_cells: Sequence[Mapping[str, Any]],
    lane_header_bboxes: Sequence[Sequence[int]],
) -> dict[str, Any]:
    """Build one deterministic geometry-only ordered row/lane assignment."""

    rows, cells, lanes = _validate_inputs(row_labels, numeric_cells, lane_header_bboxes)
    return _validate_result(_build(rows, cells, lanes))


def validate_ordered_row_value_lane_assignment_replay_v1(
    value: Any,
    row_labels: Sequence[Mapping[str, Any]],
    numeric_cells: Sequence[Mapping[str, Any]],
    lane_header_bboxes: Sequence[Sequence[int]],
) -> dict[str, Any]:
    """Rebuild from exact inputs and typed-compare one persisted assignment."""

    persisted = _validate_result(value)
    rebuilt = build_ordered_row_value_lane_assignment_v1(
        row_labels,
        numeric_cells,
        lane_header_bboxes,
    )
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("ordered row/value assignment does not replay from exact inputs")
    return canonical_clone_v1(rebuilt)
