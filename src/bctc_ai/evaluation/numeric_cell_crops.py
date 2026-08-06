from __future__ import annotations

import json
import math
import os
import shutil
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import yaml

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file


class NumericCellCropError(RuntimeError):
    pass


@dataclass(frozen=True)
class NumericCellCropPolicy:
    source_path: Path
    format_version: int
    policy_name: str
    geometry_authority: str
    row_contract_experiment_id: str
    row_contract_status: str
    left_padding_line_heights: float
    right_padding_line_heights: float
    minimum_crop_height_line_heights: float
    source_value_line_bottom_padding_line_heights: float
    recognizer_input_fields: tuple[str, ...]
    forbidden_recognizer_inputs: tuple[str, ...]


def _positive(mapping: dict[str, Any], name: str) -> float:
    value = mapping.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise NumericCellCropError(f"invalid positive numeric-crop setting: {name}")
    return float(value)


def load_numeric_cell_crop_policy(path: Path) -> NumericCellCropPolicy:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise NumericCellCropError(f"cannot load numeric-cell crop policy: {path}") from exc
    horizontal = payload.get("horizontal_bounds") if isinstance(payload, dict) else None
    vertical = payload.get("vertical_bounds") if isinstance(payload, dict) else None
    encoding = payload.get("encoding") if isinstance(payload, dict) else None
    post_crop_canvas = (
        payload.get("post_crop_canvas") if isinstance(payload, dict) else None
    )
    identities = {
        (
            1,
            "FIXED_GRID_NUMERIC_CELL_CROPS_V1",
            "E0029_PP_OCRV6_FIXED_GRID",
        ): ("E-0029", "PASS_REFERENCE_BLIND_ROW_RECONSTRUCTION"),
        (
            2,
            "FIXED_GRID_NUMERIC_CELL_CROPS_V2",
            "E0033_PP_OCRV6_FIXED_GRID",
        ): ("E-0033", "PASS_REFERENCE_BLIND_NOTE_ROW_ANCHOR_SPLIT"),
    }
    identity = (
        payload.get("version") if isinstance(payload, dict) else None,
        payload.get("policy") if isinstance(payload, dict) else None,
        payload.get("geometry_authority") if isinstance(payload, dict) else None,
    )
    expected_post_crop_canvas = (
        None
        if identity[0] == 1
        else {
            "apply_when": "source_value_line_indices_nonempty",
            "bottom_padding_line_heights": 0.27,
            "fill_bgr": [255, 255, 255],
            "source_pixels_unchanged": True,
            "semantic_or_value_features_allowed": False,
        }
    )
    if (
        not isinstance(payload, dict)
        or identity not in identities
        or not isinstance(horizontal, dict)
        or horizontal.get("left_boundary") != "midpoint_between_previous_and_current_right_edges"
        or horizontal.get("first_previous_edge") != "note_axis_right_edge"
        or horizontal.get("right_boundary") != "max_axis_right_edge_source_text_or_visual_component"
        or not isinstance(vertical, dict)
        or vertical.get("boundary") != "midpoint_between_adjacent_row_anchors"
        or vertical.get("first_and_last_boundary") != "reconstructed_table_bbox"
        or not isinstance(encoding, dict)
        or encoding
        != {
            "format": "PNG",
            "preserve_source_pixels": True,
            "resize": False,
            "threshold": False,
            "deskew": False,
        }
        or post_crop_canvas != expected_post_crop_canvas
    ):
        raise NumericCellCropError("numeric-cell crop identity or geometry policy drifted")
    inputs = payload.get("recognizer_input_fields")
    forbidden = payload.get("forbidden_recognizer_inputs")
    expected_forbidden = {
        "row_label",
        "note_reference",
        "primary_ocr_text",
        "primary_ocr_value",
        "period_or_unit",
        "schema_label_or_report_norm_id",
        "historical_or_mongodb_value",
        "human_review_value",
    }
    if (
        inputs != ["crop_path"]
        or not isinstance(forbidden, list)
        or set(forbidden) != expected_forbidden
    ):
        raise NumericCellCropError("numeric recognizer input isolation drifted")
    experiment_id, contract_status = identities[identity]
    return NumericCellCropPolicy(
        source_path=path.resolve(),
        format_version=int(identity[0]),
        policy_name=str(identity[1]),
        geometry_authority=str(identity[2]),
        row_contract_experiment_id=experiment_id,
        row_contract_status=contract_status,
        left_padding_line_heights=_positive(horizontal, "left_padding_line_heights"),
        right_padding_line_heights=_positive(horizontal, "right_padding_line_heights"),
        minimum_crop_height_line_heights=_positive(vertical, "minimum_crop_height_line_heights"),
        source_value_line_bottom_padding_line_heights=(
            0.0
            if post_crop_canvas is None
            else _positive(post_crop_canvas, "bottom_padding_line_heights")
        ),
        recognizer_input_fields=("crop_path",),
        forbidden_recognizer_inputs=tuple(str(value) for value in forbidden),
    )


def _load_json(path: Path, name: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise NumericCellCropError(f"cannot load {name}: {path}") from exc
    if not isinstance(payload, dict):
        raise NumericCellCropError(f"{name} must be an object")
    return payload


def _resolve_mapping(mapping: dict[int, Path], pages: set[int], name: str) -> dict[int, Path]:
    normalized = {int(page): path.resolve() for page, path in mapping.items()}
    if set(normalized) != pages or any(not path.is_file() for path in normalized.values()):
        raise NumericCellCropError(f"{name} does not cover the exact target pages")
    return normalized


def _contained(inner: list[float] | tuple[float, ...], outer: tuple[int, int, int, int]) -> bool:
    return (
        float(inner[0]) >= outer[0]
        and float(inner[1]) >= outer[1]
        and float(inner[2]) <= outer[2]
        and float(inner[3]) <= outer[3]
    )


def build_numeric_cell_crop_registry(
    *,
    row_contract_path: Path,
    ocr_paths_by_page: dict[int, Path],
    render_paths_by_page: dict[int, Path],
    output_directory: Path,
    policy: NumericCellCropPolicy,
) -> dict[str, Any]:
    """Crop every fixed-grid numeric cell without exposing context to the reader."""

    row_contract_path = row_contract_path.resolve()
    output_directory = output_directory.resolve()
    contract = _load_json(row_contract_path, "row contract")
    pages_raw = contract.get("after")
    if (
        contract.get("experiment_id") != policy.row_contract_experiment_id
        or contract.get("status") != policy.row_contract_status
        or not isinstance(pages_raw, list)
        or not pages_raw
    ):
        raise NumericCellCropError(
            "numeric crops require the row contract bound by the selected crop policy"
        )
    pages = {int(record["page"]) for record in pages_raw}
    ocr_paths = _resolve_mapping(ocr_paths_by_page, pages, "OCR paths")
    render_paths = _resolve_mapping(render_paths_by_page, pages, "render paths")
    if output_directory.exists():
        raise NumericCellCropError(
            f"refusing to overwrite numeric crop directory: {output_directory}"
        )
    output_directory.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{output_directory.name}.", dir=output_directory.parent)
    )
    try:
        crop_root = temporary / "crops"
        crop_root.mkdir()
        cells = []
        page_records = []
        for page_record in pages_raw:
            page = int(page_record["page"])
            image = cv2.imread(str(render_paths[page]), cv2.IMREAD_COLOR)
            if image is None:
                raise NumericCellCropError(f"cannot read render for page {page}")
            image_height, image_width = image.shape[:2]
            ocr = _load_json(ocr_paths[page], f"page {page} OCR")
            boxes = ocr.get("rec_boxes")
            if not isinstance(boxes, list):
                raise NumericCellCropError(f"page {page} OCR lacks rec_boxes")
            axes = page_record.get("axes")
            rows = page_record.get("rows")
            note_right = page_record.get("note_right_edge")
            table_bbox = page_record.get("table_bbox")
            line_height = float(page_record.get("line_height", 0))
            if (
                not isinstance(axes, list)
                or len(axes) != 2
                or not isinstance(rows, list)
                or not rows
                or not isinstance(note_right, (int, float))
                or not isinstance(table_bbox, list)
                or len(table_bbox) != 4
                or line_height <= 0
            ):
                raise NumericCellCropError(f"page {page} row geometry is incomplete")
            anchors = [float(row["geometry"]["y_anchor"]) for row in rows]
            if anchors != sorted(anchors) or len(anchors) != len(set(anchors)):
                raise NumericCellCropError(f"page {page} row anchors are not strictly ordered")
            y_boundaries = [float(table_bbox[1])]
            y_boundaries.extend(
                (left + right) / 2 for left, right in zip(anchors, anchors[1:], strict=False)
            )
            y_boundaries.append(float(table_bbox[3]))
            axis_content_right_edges = [float(axis["right_edge"]) for axis in axes]
            for row in rows:
                for axis_ordinal in range(len(axes)):
                    for line_index in row["geometry"]["value_line_indices"][axis_ordinal]:
                        axis_content_right_edges[axis_ordinal] = max(
                            axis_content_right_edges[axis_ordinal],
                            float(boxes[int(line_index)][2]),
                        )
                    visual = row["geometry"]["visual_cell_evidence"][axis_ordinal]
                    if visual is not None:
                        axis_content_right_edges[axis_ordinal] = max(
                            axis_content_right_edges[axis_ordinal],
                            float(visual["component_box"][2]),
                        )
            page_cell_count = 0
            for row_ordinal, (row, _anchor) in enumerate(zip(rows, anchors, strict=True)):
                y0 = max(0, int(math.floor(y_boundaries[row_ordinal])))
                y1 = min(image_height, int(math.ceil(y_boundaries[row_ordinal + 1])))
                if y1 - y0 < line_height * policy.minimum_crop_height_line_heights:
                    raise NumericCellCropError(
                        f"page {page} row {row_ordinal} numeric crop height is unsafe"
                    )
                previous_right = float(note_right)
                for axis_ordinal, (axis, cell) in enumerate(zip(axes, row["cells"], strict=True)):
                    axis_right = float(axis["right_edge"])
                    x0 = max(
                        0,
                        int(
                            math.floor(
                                (previous_right + axis_right) / 2
                                - line_height * policy.left_padding_line_heights
                            )
                        ),
                    )
                    x1 = min(
                        image_width,
                        int(
                            math.ceil(
                                axis_content_right_edges[axis_ordinal]
                                + line_height * policy.right_padding_line_heights
                            )
                        ),
                    )
                    crop_box = (x0, y0, x1, y1)
                    if x1 <= x0:
                        raise NumericCellCropError(
                            f"page {page} row {row_ordinal} axis {axis_ordinal} crop is empty"
                        )
                    line_indices = row["geometry"]["value_line_indices"][axis_ordinal]
                    for line_index in line_indices:
                        if not _contained(boxes[int(line_index)], crop_box):
                            raise NumericCellCropError(
                                f"page {page} cell crop clips source line {line_index}"
                            )
                    visual = row["geometry"]["visual_cell_evidence"][axis_ordinal]
                    if visual is not None and not _contained(visual["component_box"], crop_box):
                        raise NumericCellCropError(
                            f"page {page} cell crop clips visual punctuation evidence"
                        )
                    crop = image[y0:y1, x0:x1]
                    bottom_padding_pixels = (
                        int(
                            math.floor(
                                line_height
                                * policy.source_value_line_bottom_padding_line_heights
                                + 0.5
                            )
                        )
                        if line_indices
                        else 0
                    )
                    if bottom_padding_pixels:
                        crop = cv2.copyMakeBorder(
                            crop,
                            0,
                            bottom_padding_pixels,
                            0,
                            0,
                            cv2.BORDER_CONSTANT,
                            value=(255, 255, 255),
                        )
                    cell_id = f"page-{page:04d}-row-{row_ordinal:03d}-axis-{axis_ordinal + 1}"
                    relative_path = Path("crops") / f"{cell_id}.png"
                    crop_path = temporary / relative_path
                    if not cv2.imwrite(str(crop_path), crop):
                        raise NumericCellCropError(f"cannot write numeric crop {crop_path}")
                    cell_record = {
                            "cell_id": cell_id,
                            "page": page,
                            "row_ordinal": row_ordinal,
                            "axis_ordinal": axis_ordinal,
                            "axis_id": axis["axis_id"],
                            "source_row_ids": row["source_row_ids"],
                            "crop_path": relative_path.as_posix(),
                            "crop_bbox": list(crop_box),
                            "crop_size_bytes": crop_path.stat().st_size,
                            "crop_sha256": sha256_file(crop_path),
                            "source_render_path": render_paths[page].as_posix(),
                            "source_render_sha256": sha256_file(render_paths[page]),
                            "source_ocr_path": ocr_paths[page].as_posix(),
                            "source_ocr_sha256": sha256_file(ocr_paths[page]),
                            "value_line_indices": line_indices,
                            "primary_observation": cell["observation"],
                            "primary_raw_text": cell["raw_text"],
                            "primary_normalized_text": cell["normalized_text"],
                            "primary_value": cell["value"],
                            "primary_sign_evidence": cell["sign_evidence"],
                            "visual_punctuation_evidence": visual,
                            "recognizer_payload": {"crop_path": relative_path.as_posix()},
                        }
                    if policy.format_version >= 2:
                        cell_record["post_crop_canvas"] = {
                            "trigger": "SOURCE_VALUE_LINE_INDICES_NONEMPTY",
                            "bottom_padding_pixels": bottom_padding_pixels,
                            "fill_bgr": [255, 255, 255],
                            "source_pixels_unchanged": True,
                        }
                    cells.append(cell_record)
                    page_cell_count += 1
                    previous_right = axis_right
            page_records.append(
                {
                    "page": page,
                    "row_count": len(rows),
                    "cell_count": page_cell_count,
                    "render_path": render_paths[page].as_posix(),
                    "render_sha256": sha256_file(render_paths[page]),
                    "ocr_path": ocr_paths[page].as_posix(),
                    "ocr_sha256": sha256_file(ocr_paths[page]),
                }
            )
        observation_counts = Counter(cell["primary_observation"] for cell in cells)
        metrics = {
            "page_count": len(page_records),
            "row_count": sum(record["row_count"] for record in page_records),
            "cell_count": len(cells),
            "primary_observation_counts": dict(sorted(observation_counts.items())),
            "crop_line_clip_count": 0,
            "visual_evidence_clip_count": 0,
        }
        if policy.format_version >= 2:
            padding_pixels = [
                int(cell["post_crop_canvas"]["bottom_padding_pixels"]) for cell in cells
            ]
            metrics.update(
                {
                    "post_crop_padded_cell_count": sum(value > 0 for value in padding_pixels),
                    "post_crop_bottom_padding_pixel_count": sum(padding_pixels),
                }
            )
        registry = {
            "format_version": policy.format_version,
            "policy": policy.policy_name,
            "geometry_authority": policy.geometry_authority,
            "row_contract": {
                "path": row_contract_path.as_posix(),
                "sha256": sha256_file(row_contract_path),
            },
            "crop_policy": {
                "path": policy.source_path.as_posix(),
                "sha256": sha256_file(policy.source_path),
            },
            "recognizer_input_fields": list(policy.recognizer_input_fields),
            "forbidden_recognizer_inputs": list(policy.forbidden_recognizer_inputs),
            "pages": page_records,
            "metrics": metrics,
            "cells": cells,
            "reference_isolation": {
                "human_review_loaded": False,
                "historical_or_mongodb_values_loaded": False,
                "template_labels_or_report_norm_ids_loaded": False,
                "schema_mapping_invoked": False,
                "accounting_validation_invoked": False,
            },
        }
        atomic_write_json(temporary / "crop_registry.json", registry)
        os.replace(temporary, output_directory)
        return registry
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
