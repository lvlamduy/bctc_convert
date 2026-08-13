from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bctc_ai.core.atomic import atomic_write_json  # noqa: E402
from bctc_ai.core.hashing import sha256_file  # noqa: E402


class TableStructurePanelError(RuntimeError):
    pass


SOURCE_FORMAT = "MULTIBANK_TABLE_STRUCTURE_SOURCE_PANEL_V1"
GOLD_INPUT_FORMAT = "MULTIBANK_TABLE_STRUCTURE_SOURCE_GOLD_INPUT_V1"
MANIFEST_FORMAT = "MULTIBANK_TABLE_STRUCTURE_CROP_MANIFEST_V1"
REQUEST_FORMAT = "MULTIBANK_TABLE_STRUCTURE_MODEL_REQUEST_V1"
GOLD_FORMAT = "MULTIBANK_TABLE_STRUCTURE_SOURCE_GOLD_V1"
RESULT_FORMAT = "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V2"
MODEL_CATEGORY = "TABLE_STRUCTURE"
TATR_LABELS = (
    "table",
    "table column",
    "table row",
    "table column header",
    "table projected row header",
    "table spanning cell",
)
DEFAULT_SOURCE_SPEC = Path("config/experiments/multibank-table-structure-source-panel-v1.json")
DEFAULT_GOLD_INPUT = Path("config/experiments/multibank-table-structure-source-gold-input-v1.json")
DEFAULT_OUTPUT_ROOT = Path("output/development/multibank-table-structure-calibration-v1")
DEFAULT_GOLD_OUTPUT = Path("docs/experiments/multibank-table-structure-calibration-truth-v1.json")

_REF_KEYS = {"path", "sha256", "size_bytes"}
_SOURCE_KEYS = {
    "dataset_role",
    "design_checkpoint_git_commit",
    "format_version",
    "padding_pixels",
    "samples",
    "state",
}
_SOURCE_SAMPLE_KEYS = {
    "expected_source_line_count",
    "line_index_range_inclusive",
    "render_ref",
    "result_ref",
    "sample_id",
}
_GOLD_KEYS = {
    "design_checkpoint_git_commit",
    "format_version",
    "samples",
    "state",
}
_GOLD_SAMPLE_KEYS = {
    "bank",
    "column_anchor_line_groups",
    "column_excluded_line_indices",
    "control_kind",
    "expected_control_disposition",
    "expected_structural_family_merge",
    "family",
    "header_line_groups",
    "ignored_noncontent_line_indices",
    "ignored_noncontent_reason",
    "logical_rows",
    "nested_row_required",
    "numeric_lane_count",
    "optional_row_behavior",
    "physical_page",
    "projected_row_header_line_groups",
    "sample_id",
    "spanning_cells",
    "visible_unscored_dash_cells",
}
_LOGICAL_ROW_KEYS = {"line_indices", "value_line_indices_by_numeric_lane"}
_SPAN_KEYS = {"column_end", "column_start", "line_indices"}
_DASH_CELL_KEYS = {"logical_row_ordinal", "numeric_lane_ordinal", "reason"}
_OPAQUE_SAMPLE_ID = re.compile(r"^table-[0-9]{4}$")
_IGNORED_NONCONTENT_REASONS = {
    "NONE",
    "PIXEL_AUDITED_HORIZONTAL_RULE_FALSE_DETECTION",
}


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_blob(commit: str, relative_path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative_path}"],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise TableStructurePanelError(f"tracked Git blob is absent: {relative_path}")
    return result.stdout


def _resolve(path: Path | str, label: str) -> Path:
    candidate = Path(path)
    resolved = (
        candidate.resolve() if candidate.is_absolute() else (PROJECT_ROOT / candidate).resolve()
    )
    if not resolved.is_relative_to(PROJECT_ROOT.resolve()):
        raise TableStructurePanelError(f"{label} escapes project root")
    return resolved


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TableStructurePanelError(f"cannot read {label}: {path}") from exc
    if type(value) is not dict:
        raise TableStructurePanelError(f"{label} must be a JSON object")
    return value


def _sha(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise TableStructurePanelError(f"{label} SHA-256 is invalid")
    return value


def _verified_ref(raw: Any, label: str) -> tuple[Path, dict[str, Any]]:
    if type(raw) is not dict or set(raw) != _REF_KEYS:
        raise TableStructurePanelError(f"{label} must be an exact object reference")
    relative = raw["path"]
    size = raw["size_bytes"]
    if type(relative) is not str or not relative or type(size) is not int or size <= 0:
        raise TableStructurePanelError(f"{label} object reference is invalid")
    expected_sha = _sha(raw["sha256"], label)
    path = _resolve(relative, label)
    if not path.is_file() or path.stat().st_size != size or sha256_file(path) != expected_sha:
        raise TableStructurePanelError(f"{label} is missing or hash-drifted")
    return path, {
        "path": path.relative_to(PROJECT_ROOT.resolve()).as_posix(),
        "sha256": expected_sha,
        "size_bytes": size,
    }


def _tracked_commit_ref(path: Path, *, commit: str, label: str) -> dict[str, Any]:
    relative = path.relative_to(PROJECT_ROOT.resolve()).as_posix()
    payload = path.read_bytes()
    if _git_blob(commit, relative) != payload:
        raise TableStructurePanelError(f"{label} differs from its exact tracked Git blob")
    return {
        "path": relative,
        "sha256": sha256_file(path),
        "size_bytes": len(payload),
    }


def _bbox(raw: Any, *, width: int, height: int, label: str) -> tuple[int, int, int, int]:
    if type(raw) is not list or len(raw) != 4 or any(type(item) is not int for item in raw):
        raise TableStructurePanelError(f"{label} bbox is invalid")
    x0, y0, x1, y1 = raw
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise TableStructurePanelError(f"{label} bbox lies outside its render")
    return x0, y0, x1, y1


def _line_boxes(
    lines: Sequence[Mapping[str, Any]], *, width: int, height: int
) -> list[tuple[int, int, int, int]]:
    """Read authenticated LINE geometry without consulting any OCR transcript."""

    return [
        _bbox(
            line.get("raw_pixel_bbox"),
            width=width,
            height=height,
            label=f"source line {index}",
        )
        for index, line in enumerate(lines)
    ]


def _union(boxes: Sequence[tuple[int, int, int, int]], *, label: str) -> tuple[int, int, int, int]:
    if not boxes:
        raise TableStructurePanelError(f"{label} has no boxes")
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def _crop_payload(image: Image.Image, bbox: tuple[int, int, int, int]) -> bytes:
    buffer = io.BytesIO()
    image.crop(bbox).save(buffer, format="PNG", optimize=False, compress_level=6)
    return buffer.getvalue()


def _indices(raw: Any, *, selected: set[int], label: str, allow_empty: bool = False) -> list[int]:
    if (
        type(raw) is not list
        or (not raw and not allow_empty)
        or any(type(index) is not int for index in raw)
        or len(set(raw)) != len(raw)
        or any(index not in selected for index in raw)
    ):
        raise TableStructurePanelError(f"{label} line indices are invalid")
    return list(raw)


def _source_to_crop(
    box: Sequence[int | float], crop_box: tuple[int, int, int, int]
) -> list[int | float]:
    return [
        box[0] - crop_box[0],
        box[1] - crop_box[1],
        box[2] - crop_box[0],
        box[3] - crop_box[1],
    ]


def _midpoint_partition_boxes(
    content_boxes: Sequence[tuple[int, int, int, int]],
    table_box: tuple[int, int, int, int],
    *,
    axis: str,
    label: str,
) -> list[tuple[int | float, int | float, int | float, int | float]]:
    """Expand ordered content boxes into official TATR row/column bands.

    Table Transformer training annotations place every internal boundary at the
    midpoint of the *gap edges*: the preceding content's far edge and the next
    content's near edge.  The first and last bands extend to the table box.
    This intentionally differs from splitting the distance between box centres.
    """

    if not content_boxes or axis not in {"row", "column"}:
        raise TableStructurePanelError(f"{label} midpoint-partition input is invalid")
    near = 1 if axis == "row" else 0
    far = 3 if axis == "row" else 2
    table_near = table_box[near]
    table_far = table_box[far]
    for ordinal, box in enumerate(content_boxes, start=1):
        if (
            box[0] < table_box[0]
            or box[1] < table_box[1]
            or box[2] > table_box[2]
            or box[3] > table_box[3]
        ):
            raise TableStructurePanelError(f"{label} content box {ordinal} leaves table bounds")
    if any(
        left[near] >= right[near]
        for left, right in zip(content_boxes, content_boxes[1:], strict=False)
    ):
        raise TableStructurePanelError(f"{label} content boxes are not strictly ordered")

    boundaries: list[int | float] = [table_near]
    boundaries.extend(
        (left[far] + right[near]) / 2
        for left, right in zip(content_boxes, content_boxes[1:], strict=False)
    )
    boundaries.append(table_far)
    if any(left >= right for left, right in zip(boundaries, boundaries[1:], strict=False)):
        raise TableStructurePanelError(f"derived {label} bands overlap or collapse")

    if axis == "row":
        return [
            (table_box[0], boundaries[index], table_box[2], boundaries[index + 1])
            for index in range(len(content_boxes))
        ]
    return [
        (boundaries[index], table_box[1], boundaries[index + 1], table_box[3])
        for index in range(len(content_boxes))
    ]


def _column_boxes(
    anchor_groups: Sequence[Sequence[int]],
    boxes: Sequence[tuple[int, int, int, int]],
    table_box: tuple[int, int, int, int],
) -> list[tuple[int | float, int | float, int | float, int | float]]:
    anchors = []
    for ordinal, group in enumerate(anchor_groups):
        anchor = _union([boxes[index] for index in group], label=f"column anchor {ordinal}")
        anchors.append(anchor)
    return _midpoint_partition_boxes(
        anchors,
        table_box,
        axis="column",
        label="gold column",
    )


def _validate_sources(source: dict[str, Any]) -> list[dict[str, Any]]:
    if set(source) != _SOURCE_KEYS:
        raise TableStructurePanelError("source panel contains non-allowlisted fields")
    if (
        source["format_version"] != SOURCE_FORMAT
        or source["dataset_role"] != "CALIBRATION"
        or source["state"] != "FROZEN_SOURCE_SELECTION_BEFORE_STRUCTURE_MODEL_ACCESS"
        or type(source["design_checkpoint_git_commit"]) is not str
        or len(source["design_checkpoint_git_commit"]) != 40
        or type(source["padding_pixels"]) is not int
        or not 0 <= source["padding_pixels"] <= 5
        or type(source["samples"]) is not list
        or not source["samples"]
    ):
        raise TableStructurePanelError("source panel identity or freeze policy is invalid")

    validated = []
    seen_ids: set[str] = set()
    seen_source_keys: set[tuple[str, int, int]] = set()
    for ordinal, raw in enumerate(source["samples"], start=1):
        if type(raw) is not dict or set(raw) != _SOURCE_SAMPLE_KEYS:
            raise TableStructurePanelError(f"source sample {ordinal} fields are invalid")
        sample_id = raw["sample_id"]
        line_range = raw["line_index_range_inclusive"]
        expected_count = raw["expected_source_line_count"]
        if (
            type(sample_id) is not str
            or _OPAQUE_SAMPLE_ID.fullmatch(sample_id) is None
            or sample_id in seen_ids
            or type(expected_count) is not int
            or expected_count <= 0
            or type(line_range) is not list
            or len(line_range) != 2
            or any(type(item) is not int for item in line_range)
            or not 0 <= line_range[0] <= line_range[1] < expected_count
        ):
            raise TableStructurePanelError(f"source sample {ordinal} selection is invalid")
        result_path, result_ref = _verified_ref(raw["result_ref"], f"{sample_id} V3 result")
        render_path, render_ref = _verified_ref(raw["render_ref"], f"{sample_id} render")
        source_key = (result_ref["sha256"], line_range[0], line_range[1])
        if source_key in seen_source_keys:
            raise TableStructurePanelError("source panel contains a duplicate crop selection")
        seen_ids.add(sample_id)
        seen_source_keys.add(source_key)

        result = _load_json(result_path, f"{sample_id} V3 result")
        lines = result.get("lines")
        binding = result.get("input_render_ref")
        if (
            result.get("format_version") != RESULT_FORMAT
            or type(lines) is not list
            or len(lines) != expected_count
            or any(type(line) is not dict for line in lines)
            or type(binding) is not dict
            or binding.get("sha256") != render_ref["sha256"]
            or binding.get("size_bytes") != render_ref["size_bytes"]
        ):
            raise TableStructurePanelError(f"{sample_id} V3 result/render binding drifted")
        validated.append(
            {
                "sample_id": sample_id,
                "line_range": tuple(line_range),
                "result": result,
                "result_ref": result_ref,
                "render_path": render_path,
                "render_ref": render_ref,
            }
        )
    return validated


def _validate_gold_input(
    gold: dict[str, Any], source_ids: Sequence[str]
) -> dict[str, dict[str, Any]]:
    if set(gold) != _GOLD_KEYS:
        raise TableStructurePanelError("source gold contains non-allowlisted fields")
    checkpoint = gold["design_checkpoint_git_commit"]
    if (
        gold["format_version"] != GOLD_INPUT_FORMAT
        or gold["state"] != "FROZEN_HUMAN_SOURCE_GOLD_BEFORE_STRUCTURE_MODEL_ACCESS"
        or type(gold["samples"]) is not list
        or type(checkpoint) is not str
        or len(checkpoint) != 40
        or any(character not in "0123456789abcdef" for character in checkpoint)
    ):
        raise TableStructurePanelError("source-gold identity or state is invalid")
    by_id: dict[str, dict[str, Any]] = {}
    for ordinal, raw in enumerate(gold["samples"], start=1):
        if type(raw) is not dict or set(raw) != _GOLD_SAMPLE_KEYS:
            raise TableStructurePanelError(f"source-gold sample {ordinal} fields are invalid")
        sample_id = raw["sample_id"]
        if type(sample_id) is not str or sample_id in by_id:
            raise TableStructurePanelError("source-gold sample IDs are invalid")
        if (
            type(raw["bank"]) is not str
            or not raw["bank"]
            or type(raw["family"]) is not str
            or not raw["family"]
            or type(raw["physical_page"]) is not int
            or raw["physical_page"] <= 0
            or type(raw["optional_row_behavior"]) is not str
            or not raw["optional_row_behavior"]
            or raw["control_kind"] not in {"POSITIVE", "HARD_CONTROL"}
            or raw["expected_control_disposition"] not in {"ACCEPT", "REJECT"}
            or (raw["control_kind"] == "POSITIVE")
            != (raw["expected_control_disposition"] == "ACCEPT")
            or type(raw["expected_structural_family_merge"]) is not bool
            or (raw["control_kind"] == "POSITIVE") != raw["expected_structural_family_merge"]
            or type(raw["numeric_lane_count"]) is not int
            or raw["numeric_lane_count"] <= 0
            or type(raw["nested_row_required"]) is not bool
            or type(raw["ignored_noncontent_line_indices"]) is not list
            or raw["ignored_noncontent_reason"] not in _IGNORED_NONCONTENT_REASONS
            or (bool(raw["ignored_noncontent_line_indices"]))
            != (raw["ignored_noncontent_reason"] == "PIXEL_AUDITED_HORIZONTAL_RULE_FALSE_DETECTION")
            or type(raw["logical_rows"]) is not list
            or not raw["logical_rows"]
            or type(raw["header_line_groups"]) is not list
            or not raw["header_line_groups"]
            or type(raw["projected_row_header_line_groups"]) is not list
            or type(raw["spanning_cells"]) is not list
            or type(raw["visible_unscored_dash_cells"]) is not list
            or type(raw["column_anchor_line_groups"]) is not list
            or len(raw["column_anchor_line_groups"]) != raw["numeric_lane_count"] + 1
        ):
            raise TableStructurePanelError(f"source-gold sample {sample_id} policy is invalid")
        by_id[sample_id] = raw
    if list(by_id) != list(source_ids):
        raise TableStructurePanelError("source selection and source-gold sample axes differ")
    return by_id


def _gold_sample(
    raw: dict[str, Any],
    *,
    boxes: Sequence[tuple[int, int, int, int]],
    selected_indices: Sequence[int],
    selected_table_box: tuple[int, int, int, int],
    crop_box: tuple[int, int, int, int],
) -> dict[str, Any]:
    selected = set(selected_indices)
    ignored = set(
        _indices(
            raw["ignored_noncontent_line_indices"],
            selected=selected,
            label="ignored noncontent",
            allow_empty=True,
        )
    )
    eligible = selected - ignored
    if selected_table_box != _union(
        [boxes[index] for index in selected], label="selected evidence table"
    ):
        raise TableStructurePanelError("selected table bbox is not the full evidence union")
    table_box = _union([boxes[index] for index in eligible], label="gold content table")
    logical_rows = raw["logical_rows"]
    row_specs: list[tuple[list[int], list[list[int]], str]] = []
    for ordinal, row in enumerate(logical_rows, start=1):
        if type(row) is not dict or set(row) != _LOGICAL_ROW_KEYS:
            raise TableStructurePanelError(f"{raw['sample_id']} logical row {ordinal} is invalid")
        lines = _indices(row["line_indices"], selected=selected, label="logical row")
        lanes = row["value_line_indices_by_numeric_lane"]
        if type(lanes) is not list or len(lanes) != raw["numeric_lane_count"]:
            raise TableStructurePanelError("logical-row numeric-lane denominator drifted")
        lane_indices = [
            _indices(value, selected=selected, label="value anchor", allow_empty=True)
            for value in lanes
        ]
        flattened = [index for lane in lane_indices for index in lane]
        if len(flattened) != len(set(flattened)) or any(index not in lines for index in flattened):
            raise TableStructurePanelError("value anchors must be unique members of their row")
        row_specs.append((lines, lane_indices, "logical"))

    visible_dash_cells = []
    visible_dash_axes: set[tuple[int, int]] = set()
    for cell in raw["visible_unscored_dash_cells"]:
        if type(cell) is not dict or set(cell) != _DASH_CELL_KEYS:
            raise TableStructurePanelError("visible unscored dash cell is invalid")
        row_ordinal = cell["logical_row_ordinal"]
        lane_ordinal = cell["numeric_lane_ordinal"]
        axis = (row_ordinal, lane_ordinal)
        if (
            type(row_ordinal) is not int
            or type(lane_ordinal) is not int
            or not 1 <= row_ordinal <= len(row_specs)
            or not 1 <= lane_ordinal <= raw["numeric_lane_count"]
            or cell["reason"] != "VISIBLE_DASH_NO_AUTHENTICATED_SOURCE_LINE"
            or axis in visible_dash_axes
            or row_specs[row_ordinal - 1][1][lane_ordinal - 1]
        ):
            raise TableStructurePanelError("visible unscored dash cell is invalid")
        visible_dash_axes.add(axis)
        visible_dash_cells.append(dict(cell))

    header_groups = [
        _indices(group, selected=selected, label="header row")
        for group in raw["header_line_groups"]
    ]
    projected_groups = [
        _indices(group, selected=selected, label="projected row header")
        for group in raw["projected_row_header_line_groups"]
    ]
    column_anchor_groups = [
        _indices(group, selected=selected, label="column anchor")
        for group in raw["column_anchor_line_groups"]
    ]
    column_excluded = _indices(
        raw["column_excluded_line_indices"],
        selected=selected,
        label="column-axis exclusion",
        allow_empty=True,
    )
    assigned_columns = [index for group in column_anchor_groups for index in group]
    if len(assigned_columns) != len(set(assigned_columns)):
        raise TableStructurePanelError("column source-line groups overlap")
    if (set(assigned_columns) | set(column_excluded)) & ignored:
        raise TableStructurePanelError("ignored noncontent leaks into column gold")
    if set(assigned_columns) & set(column_excluded):
        raise TableStructurePanelError("column exclusions overlap assigned column content")
    if set(assigned_columns) | set(column_excluded) != eligible:
        raise TableStructurePanelError("column assignments do not cover selected source content")
    header_lines = {index for group in header_groups for index in group}
    spanning_lines: set[int] = set()
    for span in raw["spanning_cells"]:
        if type(span) is not dict or set(span) != _SPAN_KEYS:
            raise TableStructurePanelError("spanning-cell spec is invalid")
        spanning_lines.update(
            _indices(span["line_indices"], selected=selected, label="spanning cell")
        )
    if spanning_lines & ignored:
        raise TableStructurePanelError("ignored noncontent leaks into spanning-cell gold")
    if any(index not in header_lines | spanning_lines for index in column_excluded):
        raise TableStructurePanelError(
            "column-axis exclusions are limited to fused headers or spanning cells"
        )
    column_boxes = _column_boxes(column_anchor_groups, boxes, table_box)

    row_id_by_spec = [f"row-{ordinal:03d}" for ordinal in range(1, len(row_specs) + 1)]
    row_entries: list[dict[str, Any]] = []
    for ordinal, group in enumerate(header_groups, start=1):
        row_entries.append(
            {
                "indices": group,
                "kind": "header",
                "object_id": f"header-row-{ordinal:03d}",
            }
        )
    for ordinal, (lines, _lanes, _kind) in enumerate(row_specs, start=1):
        row_entries.append(
            {
                "indices": lines,
                "kind": "logical",
                "object_id": row_id_by_spec[ordinal - 1],
            }
        )
    for ordinal, group in enumerate(projected_groups, start=1):
        row_entries.append(
            {
                "indices": group,
                "kind": "projected",
                "object_id": f"projected-row-{ordinal:03d}",
            }
        )

    row_line_owners: dict[int, str] = {}
    for entry in row_entries:
        for index in entry["indices"]:
            if index in row_line_owners:
                raise TableStructurePanelError("gold row source-line groups overlap")
            row_line_owners[index] = entry["object_id"]
        entry["content_box"] = _union(
            [boxes[index] for index in entry["indices"]], label="gold row content"
        )
    if set(row_line_owners) & ignored:
        raise TableStructurePanelError("ignored noncontent leaks into row gold")
    if set(row_line_owners) != eligible:
        raise TableStructurePanelError("gold row source-line groups do not partition the crop")
    row_entries.sort(
        key=lambda entry: (
            entry["content_box"][1],
            entry["content_box"][3],
            min(entry["indices"]),
        )
    )
    header_ids = [f"header-row-{ordinal:03d}" for ordinal in range(1, len(header_groups) + 1)]
    if [entry["object_id"] for entry in row_entries[: len(header_ids)]] != header_ids:
        raise TableStructurePanelError("column-header rows must be contiguous at the table top")
    row_boxes = _midpoint_partition_boxes(
        [entry["content_box"] for entry in row_entries],
        table_box,
        axis="row",
        label="gold row",
    )
    row_box_by_id = {
        entry["object_id"]: row_box for entry, row_box in zip(row_entries, row_boxes, strict=True)
    }

    objects: list[dict[str, Any]] = [
        {
            "bbox_crop_pixels_xyxy": _source_to_crop(table_box, crop_box),
            "label": "table",
            "object_id": "table-001",
        }
    ]
    for entry, row_box in zip(row_entries, row_boxes, strict=True):
        objects.append(
            {
                "bbox_crop_pixels_xyxy": _source_to_crop(row_box, crop_box),
                "label": "table row",
                "object_id": entry["object_id"],
            }
        )
    header_box = _union(
        [row_box_by_id[row_id] for row_id in header_ids], label="column header region"
    )
    objects.append(
        {
            "bbox_crop_pixels_xyxy": _source_to_crop(header_box, crop_box),
            "label": "table column header",
            "object_id": "column-header-001",
        }
    )
    for ordinal in range(1, len(projected_groups) + 1):
        row_id = f"projected-row-{ordinal:03d}"
        objects.append(
            {
                "bbox_crop_pixels_xyxy": _source_to_crop(row_box_by_id[row_id], crop_box),
                "label": "table projected row header",
                "object_id": f"projected-header-{ordinal:03d}",
            }
        )
    column_ids = []
    for ordinal, box in enumerate(column_boxes, start=1):
        object_id = f"column-{ordinal:03d}"
        column_ids.append(object_id)
        objects.append(
            {
                "bbox_crop_pixels_xyxy": _source_to_crop(box, crop_box),
                "label": "table column",
                "object_id": object_id,
            }
        )

    for ordinal, span in enumerate(raw["spanning_cells"], start=1):
        if type(span) is not dict or set(span) != _SPAN_KEYS:
            raise TableStructurePanelError("spanning-cell spec is invalid")
        lines = _indices(span["line_indices"], selected=selected, label="spanning cell")
        start = span["column_start"]
        end = span["column_end"]
        if (
            type(start) is not int
            or type(end) is not int
            or not 0 <= start <= end < len(column_boxes)
        ):
            raise TableStructurePanelError("spanning-cell column range is invalid")
        owner_ids = {row_line_owners[index] for index in lines}
        owner_positions = [
            position
            for position, entry in enumerate(row_entries)
            if entry["object_id"] in owner_ids
        ]
        if owner_positions != list(range(owner_positions[0], owner_positions[-1] + 1)):
            raise TableStructurePanelError("spanning-cell row bands are not contiguous")
        source_box = (
            column_boxes[start][0],
            row_boxes[owner_positions[0]][1],
            column_boxes[end][2],
            row_boxes[owner_positions[-1]][3],
        )
        objects.append(
            {
                "bbox_crop_pixels_xyxy": _source_to_crop(source_box, crop_box),
                "label": "table spanning cell",
                "object_id": f"spanning-cell-{ordinal:03d}",
            }
        )

    anchors = []
    source_anchored_cell_count = 0
    for row_ordinal, (_lines, lanes, _kind) in enumerate(row_specs, start=1):
        for lane_ordinal, line_indices in enumerate(lanes, start=1):
            source_anchored_cell_count += bool(line_indices)
            if len(line_indices) > 1:
                raise TableStructurePanelError(
                    "a source-anchored value cell must have exactly one source line"
                )
            for line_index in line_indices:
                anchors.append(
                    {
                        "anchor_id": f"value-anchor-{len(anchors) + 1:04d}",
                        "bbox_crop_pixels_xyxy": _source_to_crop(boxes[line_index], crop_box),
                        "expected_column_object_id": column_ids[lane_ordinal],
                        "expected_row_object_id": row_id_by_spec[row_ordinal - 1],
                        "logical_row_ordinal": row_ordinal,
                        "numeric_lane_ordinal": lane_ordinal,
                        "source_line_index": line_index,
                    }
                )

    counts = {label: sum(item["label"] == label for item in objects) for label in TATR_LABELS}
    class_coverage = {
        label: ("SCORABLE_WITH_INSTANCES" if counts[label] else "SCORABLE_ZERO_INSTANCE")
        for label in TATR_LABELS
    }
    cell_slot_count = len(row_specs) * raw["numeric_lane_count"]
    visible_dash_count = len(visible_dash_cells)
    return {
        "bank": raw["bank"],
        "class_coverage": class_coverage,
        "control_kind": raw["control_kind"],
        "expected_control_disposition": raw["expected_control_disposition"],
        "expected_structural_family_merge": raw["expected_structural_family_merge"],
        "family": raw["family"],
        "gold_content_table_source_bbox_raw_pixels": list(table_box),
        "gold_objects": objects,
        "header_row_count": len(header_groups),
        "ignored_noncontent_line_count": len(ignored),
        "ignored_noncontent_line_indices": sorted(ignored),
        "ignored_noncontent_reason": raw["ignored_noncontent_reason"],
        "logical_row_count": len(logical_rows),
        "nested_row_required": raw["nested_row_required"],
        "numeric_lane_count": raw["numeric_lane_count"],
        "optional_row_behavior": raw["optional_row_behavior"],
        "physical_page": raw["physical_page"],
        "sample_id": raw["sample_id"],
        "spanning_cell_required": bool(raw["spanning_cells"]),
        "value_anchors": anchors,
        "value_cell_coverage_summary": {
            "cell_slot_count": cell_slot_count,
            "other_unanchored_cell_count": (
                cell_slot_count - source_anchored_cell_count - visible_dash_count
            ),
            "source_anchored_value_cell_count": source_anchored_cell_count,
            "visible_unscored_dash_cell_count": visible_dash_count,
        },
        "visible_unscored_dash_cells": visible_dash_cells,
    }


def build_panel(
    *,
    source_spec_path: Path = DEFAULT_SOURCE_SPEC,
    gold_input_path: Path = DEFAULT_GOLD_INPUT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    gold_output_path: Path = DEFAULT_GOLD_OUTPUT,
) -> dict[str, Any]:
    if _git("status", "--porcelain", "--untracked-files=normal"):
        raise TableStructurePanelError("formal panel freeze requires a clean Git worktree")
    commit = _git("rev-parse", "HEAD")
    source_path = _resolve(source_spec_path, "source panel")
    gold_input_file = _resolve(gold_input_path, "source-gold input")
    source_spec_ref = _tracked_commit_ref(
        source_path,
        commit=commit,
        label="source panel",
    )
    gold_input_ref = _tracked_commit_ref(
        gold_input_file,
        commit=commit,
        label="source-gold input",
    )
    destination = _resolve(output_root, "panel output root")
    gold_output = _resolve(gold_output_path, "source-gold output")
    if destination.exists() or gold_output.exists():
        raise TableStructurePanelError("refusing to overwrite a frozen panel artifact")

    source = _load_json(source_path, "source panel")
    sources = _validate_sources(source)
    gold_input = _load_json(gold_input_file, "source-gold input")
    if gold_input.get("design_checkpoint_git_commit") != source["design_checkpoint_git_commit"]:
        raise TableStructurePanelError("source selection and source-gold checkpoint differ")
    gold_by_id = _validate_gold_input(gold_input, [sample["sample_id"] for sample in sources])

    destination.parent.mkdir(parents=True, exist_ok=True)
    gold_output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    temporary_gold = gold_output.with_name(f".{gold_output.name}.{os.getpid()}.tmp")
    try:
        crop_dir = temporary / "frozen" / "crops"
        crop_dir.mkdir(parents=True)
        final_crop_dir = destination / "frozen" / "crops"
        manifest_samples = []
        truth_samples = []
        selected_line_count = 0
        source_page_hashes: set[str] = set()
        padding = source["padding_pixels"]

        for raw in sources:
            sample_id = raw["sample_id"]
            with Image.open(raw["render_path"]) as opened:
                image = opened.convert("RGB")
            width, height = image.size
            boxes = _line_boxes(raw["result"]["lines"], width=width, height=height)
            first, last = raw["line_range"]
            selected_indices = list(range(first, last + 1))
            table_box = _union([boxes[index] for index in selected_indices], label=sample_id)
            crop_box = (
                max(0, table_box[0] - padding),
                max(0, table_box[1] - padding),
                min(width, table_box[2] + padding),
                min(height, table_box[3] + padding),
            )
            crop_payload = _crop_payload(image, crop_box)
            temporary_crop = crop_dir / f"{sample_id}.png"
            temporary_crop.write_bytes(crop_payload)
            final_crop = final_crop_dir / temporary_crop.name
            crop_sha = sha256_file(temporary_crop)
            manifest_samples.append(
                {
                    "crop_height": crop_box[3] - crop_box[1],
                    "crop_path": final_crop.relative_to(PROJECT_ROOT.resolve()).as_posix(),
                    "crop_sha256": crop_sha,
                    "crop_source_bbox_raw_pixels": list(crop_box),
                    "crop_width": crop_box[2] - crop_box[0],
                    "padding_pixels": padding,
                    "sample_id": sample_id,
                    "selected_line_count": len(selected_indices),
                    "source_line_indices": selected_indices,
                    "source_render_ref": raw["render_ref"],
                    "source_result_ref": raw["result_ref"],
                    "table_source_bbox_raw_pixels": list(table_box),
                }
            )
            truth = _gold_sample(
                gold_by_id[sample_id],
                boxes=boxes,
                selected_indices=selected_indices,
                selected_table_box=table_box,
                crop_box=crop_box,
            )
            truth["crop_ref"] = {
                "path": final_crop.relative_to(PROJECT_ROOT.resolve()).as_posix(),
                "sha256": crop_sha,
                "size_bytes": len(crop_payload),
            }
            truth_samples.append(truth)
            selected_line_count += len(selected_indices)
            source_page_hashes.add(raw["result_ref"]["sha256"])

        manifest = {
            "authority": {
                "mapping_value_period_scope_semantic_authority": False,
                "structure_proposal_only": True,
            },
            "dataset_role": "CALIBRATION",
            "design_checkpoint_git_commit": source["design_checkpoint_git_commit"],
            "format_version": MANIFEST_FORMAT,
            "git_commit": commit,
            "git_dirty": False,
            "inference_firewall": {
                "bank_family_page_control_or_expected_truth_exposed_to_model": False,
                "ocr_transcript_consulted_by_crop_selector": False,
                "role_a_schema_history_or_values_consulted_by_crop_selector": False,
            },
            "sample_count": len(manifest_samples),
            "samples": manifest_samples,
            "selected_source_line_count": selected_line_count,
            "source_page_count": len(source_page_hashes),
            "source_spec_ref": source_spec_ref,
            "state": "FROZEN_BEFORE_ANY_STRUCTURE_MODEL_INFERENCE",
        }
        temporary_manifest = temporary / "frozen" / "crop_manifest.json"
        atomic_write_json(temporary_manifest, manifest)
        final_manifest = destination / "frozen" / "crop_manifest.json"
        request = {
            "crop_manifest": {
                "path": final_manifest.relative_to(PROJECT_ROOT.resolve()).as_posix(),
                "sha256": sha256_file(temporary_manifest),
                "size_bytes": temporary_manifest.stat().st_size,
            },
            "dataset_role": "CALIBRATION",
            "evidence_role": "TABLE_STRUCTURE_PROPOSAL_ONLY",
            "format_version": REQUEST_FORMAT,
            "git_commit": commit,
            "git_dirty": False,
            "expected_structure_available_to_reader": False,
            "reference_text_available_to_reader": False,
            "sample_count": len(manifest_samples),
            "samples": [
                {
                    "category": MODEL_CATEGORY,
                    "crop_path": sample["crop_path"],
                    "crop_sha256": sample["crop_sha256"],
                    "sample_id": sample["sample_id"],
                }
                for sample in manifest_samples
            ],
            "state": "REFERENCE_BLIND_REQUEST_FROZEN",
        }
        atomic_write_json(temporary / "frozen" / "model_request.json", request)

        truth = {
            "crop_manifest": request["crop_manifest"],
            "design_checkpoint_git_commit": source["design_checkpoint_git_commit"],
            "format_version": GOLD_FORMAT,
            "gold_input_ref": gold_input_ref,
            "sample_count": len(truth_samples),
            "samples": truth_samples,
            "state": "FROZEN_BEFORE_ANY_STRUCTURE_MODEL_INFERENCE",
        }
        temporary_gold.write_text(
            json.dumps(truth, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, destination)
        os.replace(temporary_gold, gold_output)
    finally:
        shutil.rmtree(temporary, ignore_errors=True)
        temporary_gold.unlink(missing_ok=True)

    return {
        "crop_manifest": (destination / "frozen" / "crop_manifest.json")
        .relative_to(PROJECT_ROOT.resolve())
        .as_posix(),
        "model_request": (destination / "frozen" / "model_request.json")
        .relative_to(PROJECT_ROOT.resolve())
        .as_posix(),
        "sample_count": len(sources),
        "selected_source_line_count": sum(
            sample["line_range"][1] - sample["line_range"][0] + 1 for sample in sources
        ),
        "source_gold": gold_output.relative_to(PROJECT_ROOT.resolve()).as_posix(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Freeze the source-bound multi-bank table-structure calibration panel"
    )
    parser.add_argument("--source-spec", type=Path, default=DEFAULT_SOURCE_SPEC)
    parser.add_argument("--gold-input", type=Path, default=DEFAULT_GOLD_INPUT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--gold-output", type=Path, default=DEFAULT_GOLD_OUTPUT)
    args = parser.parse_args()
    print(
        json.dumps(
            build_panel(
                source_spec_path=args.source_spec,
                gold_input_path=args.gold_input,
                output_root=args.output_root,
                gold_output_path=args.gold_output,
            ),
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
