from __future__ import annotations

import json
import re
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import yaml

from bctc_ai.core.text import normalize_text, parse_financial_number, retrieval_key
from bctc_ai.validation.reader_agreement import ReaderRow


class WordBoxReconstructionError(RuntimeError):
    pass


@dataclass(frozen=True)
class OCRLine:
    index: int
    text: str
    score: float
    box: tuple[float, float, float, float]

    @property
    def x_right(self) -> float:
        return self.box[2]

    @property
    def y_center(self) -> float:
        return (self.box[1] + self.box[3]) / 2

    @property
    def height(self) -> float:
        return self.box[3] - self.box[1]


@dataclass(frozen=True)
class GeometryAxis:
    axis_id: str
    raw_header: str
    right_edge: float
    header_line_index: int


@dataclass(frozen=True)
class VisualCellEvidence:
    observation: str
    source_image_path: str
    crop_box: tuple[int, int, int, int]
    component_box: tuple[int, int, int, int]
    threshold: float
    foreground_contrast: float
    width_line_heights: float
    height_line_heights: float
    aspect_ratio: float
    fill_ratio: float


@dataclass(frozen=True)
class GeometryRowProposal:
    row: ReaderRow
    y_anchor: float
    label_line_indices: tuple[int, ...]
    note_line_indices: tuple[int, ...]
    value_line_indices: tuple[tuple[int, ...], ...]
    visual_cell_evidence: tuple[VisualCellEvidence | None, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class ParsedGeometryPage:
    input_path: str
    axes: tuple[GeometryAxis, ...]
    note_right_edge: float | None
    table_bbox: tuple[float, float, float, float]
    rows: tuple[GeometryRowProposal, ...]
    trailing_context_rows: tuple[GeometryRowProposal, ...]
    line_height: float
    unassigned_numeric_line_indices: tuple[int, ...]
    excluded_after_table_line_indices: tuple[int, ...]


def load_word_box_reconstruction_config(path: Path) -> dict[str, float | int]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise WordBoxReconstructionError("word-box reconstruction config must be version 1")
    required_positive = (
        "minimum_period_headers",
        "body_start_line_heights_after_period_header",
        "table_block_gap_line_heights",
        "axis_right_edge_max_distance_ratio",
        "row_anchor_cluster_line_heights",
        "label_direct_attach_line_heights",
        "label_below_anchor_tolerance_line_heights",
        "wrapped_label_center_gap_line_heights",
        "note_attach_line_heights",
        "dash_search_width_line_heights",
        "dash_search_right_padding_line_heights",
        "dash_search_half_height_line_heights",
        "dash_component_center_tolerance_line_heights",
        "dash_min_width_line_heights",
        "dash_max_width_line_heights",
        "dash_min_height_line_heights",
        "dash_max_height_line_heights",
        "dash_min_aspect_ratio",
        "dash_min_fill_ratio",
        "dash_min_component_area_line_heights_squared",
        "dash_min_foreground_contrast",
    )
    for key in required_positive:
        value = payload.get(key)
        if not isinstance(value, (int, float)) or value <= 0:
            raise WordBoxReconstructionError(f"invalid positive reconstruction setting: {key}")
    minimum_score = payload.get("minimum_line_score")
    if not isinstance(minimum_score, (int, float)) or not 0 <= minimum_score <= 1:
        raise WordBoxReconstructionError("minimum_line_score must be between zero and one")
    return payload


_OCR_DASH_ALIASES = frozenset({"一", "―", "﹣", "－", "ー", "━", "─"})


def _normalize_numeric_ocr_token(text: str) -> str:
    normalized = normalize_text(text)
    return "-" if normalized in _OCR_DASH_ALIASES else normalized


def _period_like(text: str) -> bool:
    normalized = normalize_text(text)
    years = [int(value) for value in re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", normalized)]
    if not years:
        return False
    return bool(re.fullmatch(r"[\d\s./-]+", normalized))


def _numeric_only(text: str) -> bool:
    normalized = _normalize_numeric_ocr_token(text)
    if not normalized:
        return False
    if any(character.isalpha() for character in normalized):
        return False
    return bool(re.fullmatch(r"[\d\s.,()\-–—+]+", normalized))


def _cluster_by_y(lines: list[OCRLine], tolerance: float) -> list[list[OCRLine]]:
    clusters: list[list[OCRLine]] = []
    for line in sorted(lines, key=lambda item: (item.y_center, item.box[0])):
        if not clusters:
            clusters.append([line])
            continue
        center = statistics.fmean(item.y_center for item in clusters[-1])
        if abs(line.y_center - center) <= tolerance:
            clusters[-1].append(line)
        else:
            clusters.append([line])
    return clusters


def _header_axes(
    lines: list[OCRLine], line_height: float, minimum_headers: int
) -> tuple[tuple[GeometryAxis, ...], list[OCRLine], float | None]:
    candidates = [line for line in lines if _period_like(line.text)]
    clusters = _cluster_by_y(candidates, line_height * 0.6)
    header_groups = [cluster for cluster in clusters if len(cluster) >= minimum_headers]
    if not header_groups:
        raise WordBoxReconstructionError("could not infer at least two period header axes")
    header_lines = min(header_groups, key=lambda group: statistics.fmean(x.y_center for x in group))
    header_lines = sorted(header_lines, key=lambda line: line.x_right)
    axes = tuple(
        GeometryAxis(
            axis_id=f"value-{index}",
            raw_header=line.text,
            right_edge=line.x_right,
            header_line_index=line.index,
        )
        for index, line in enumerate(header_lines, start=1)
    )
    header_center = statistics.fmean(line.y_center for line in header_lines)
    note_candidates = [
        line
        for line in lines
        if line.x_right < axes[0].right_edge
        and abs(line.y_center - header_center) <= line_height * 1.6
        and any(token in retrieval_key(line.text) for token in ("thuy", "minh"))
    ]
    note_right_edge = (
        statistics.median(line.x_right for line in note_candidates) if note_candidates else None
    )
    return axes, header_lines, note_right_edge


def _body_block(
    lines: list[OCRLine], body_start: float, line_height: float, gap_ratio: float
) -> tuple[list[OCRLine], list[OCRLine]]:
    candidates = sorted(
        (line for line in lines if line.y_center >= body_start),
        key=lambda line: (line.box[1], line.box[0]),
    )
    if not candidates:
        raise WordBoxReconstructionError("no OCR lines remain below the inferred header")
    body = [candidates[0]]
    maximum_bottom = candidates[0].box[3]
    split_index = len(candidates)
    for index, line in enumerate(candidates[1:], start=1):
        if line.box[1] - maximum_bottom > line_height * gap_ratio:
            split_index = index
            break
        body.append(line)
        maximum_bottom = max(maximum_bottom, line.box[3])
    return body, candidates[split_index:]


def _join_financial_tokens(lines: list[OCRLine]) -> str | None:
    if not lines:
        return None
    ordered = sorted(lines, key=lambda line: line.box[0])
    texts = [_normalize_numeric_ocr_token(line.text) for line in ordered]
    punctuation = {"(", ")", "-", "–", "—", "+"}
    substantive = [text for text in texts if text not in punctuation]
    if len(substantive) == 1:
        return "".join(texts)
    return " ".join(texts)


def _source_ids(page_tag: str, lines: list[OCRLine]) -> tuple[str, ...]:
    return tuple(f"{page_tag}:line-{line.index:04d}" for line in sorted(lines, key=lambda x: x.index))


def _read_source_image(path: Path | None) -> np.ndarray | None:
    if path is None:
        return None
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise WordBoxReconstructionError(f"cannot read sealed source image: {path}")
    return image


def _detect_visible_dash(
    image: np.ndarray,
    *,
    source_image_path: Path,
    axis_right_edge: float,
    anchor_center: float,
    line_height: float,
    config: dict[str, float | int],
) -> VisualCellEvidence | None:
    image_height, image_width = image.shape[:2]
    x0 = max(
        0,
        int(round(axis_right_edge - line_height * float(config["dash_search_width_line_heights"]))),
    )
    x1 = min(
        image_width,
        int(
            round(
                axis_right_edge
                + line_height * float(config["dash_search_right_padding_line_heights"])
            )
        ),
    )
    half_height = line_height * float(config["dash_search_half_height_line_heights"])
    y0 = max(0, int(round(anchor_center - half_height)))
    y1 = min(image_height, int(round(anchor_center + half_height)))
    if x1 <= x0 or y1 <= y0:
        return None
    crop = image[y0:y1, x0:x1]
    threshold, foreground = cv2.threshold(
        crop, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
    )
    component_count, _, stats, _ = cv2.connectedComponentsWithStats(foreground, 8)
    minimum_area = line_height**2 * float(
        config["dash_min_component_area_line_heights_squared"]
    )
    center_tolerance = line_height * float(
        config["dash_component_center_tolerance_line_heights"]
    )
    components = []
    for index in range(1, component_count):
        component = tuple(int(value) for value in stats[index])
        component_x, component_y, width, height, area = component
        absolute_center_y = y0 + component_y + height / 2
        if area >= minimum_area and abs(absolute_center_y - anchor_center) <= center_tolerance:
            components.append(component)
    if len(components) != 1:
        return None
    component_x, component_y, width, height, area = components[0]
    width_ratio = width / line_height
    height_ratio = height / line_height
    aspect_ratio = width / height
    fill_ratio = area / (width * height)
    absolute_right = x0 + component_x + width
    right_offset = axis_right_edge - absolute_right
    absolute_center_y = y0 + component_y + height / 2
    component_pixels = crop[
        component_y : component_y + height, component_x : component_x + width
    ]
    foreground_contrast = float(np.median(crop) - np.mean(component_pixels))
    if not (
        float(config["dash_min_width_line_heights"])
        <= width_ratio
        <= float(config["dash_max_width_line_heights"])
        and float(config["dash_min_height_line_heights"])
        <= height_ratio
        <= float(config["dash_max_height_line_heights"])
        and aspect_ratio >= float(config["dash_min_aspect_ratio"])
        and fill_ratio >= float(config["dash_min_fill_ratio"])
        and foreground_contrast >= float(config["dash_min_foreground_contrast"])
        and -line_height * float(config["dash_search_right_padding_line_heights"])
        <= right_offset
        <= line_height * float(config["dash_search_width_line_heights"])
        and abs(absolute_center_y - anchor_center) <= center_tolerance
    ):
        return None
    return VisualCellEvidence(
        observation="DASH",
        source_image_path=str(source_image_path),
        crop_box=(x0, y0, x1, y1),
        component_box=(
            x0 + component_x,
            y0 + component_y,
            x0 + component_x + width,
            y0 + component_y + height,
        ),
        threshold=float(threshold),
        foreground_contrast=round(foreground_contrast, 6),
        width_line_heights=round(width_ratio, 6),
        height_line_heights=round(height_ratio, 6),
        aspect_ratio=round(aspect_ratio, 6),
        fill_ratio=round(fill_ratio, 6),
    )


def parse_ppocrv6_word_box_page(
    result_path: Path,
    config: dict[str, float | int],
    *,
    page_tag: str,
    source_image_path: Path | None = None,
) -> ParsedGeometryPage:
    try:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise WordBoxReconstructionError(f"cannot read PP-OCRv6 result: {result_path}") from exc
    raw_texts = payload.get("rec_texts")
    raw_scores = payload.get("rec_scores")
    raw_boxes = payload.get("rec_boxes")
    if not all(isinstance(value, list) for value in (raw_texts, raw_scores, raw_boxes)):
        raise WordBoxReconstructionError("PP-OCRv6 result lacks text, score, or box axes")
    if len({len(raw_texts), len(raw_scores), len(raw_boxes)}) != 1:
        raise WordBoxReconstructionError("PP-OCRv6 result axes have different lengths")
    lines = []
    for index, (text, score, box) in enumerate(
        zip(raw_texts, raw_scores, raw_boxes, strict=True)
    ):
        if not isinstance(box, list) or len(box) != 4:
            raise WordBoxReconstructionError(f"line {index} has no four-coordinate box")
        parsed_box = tuple(float(value) for value in box)
        if parsed_box[2] <= parsed_box[0] or parsed_box[3] <= parsed_box[1]:
            raise WordBoxReconstructionError(f"line {index} has a degenerate box")
        if float(score) < float(config["minimum_line_score"]):
            continue
        lines.append(OCRLine(index, normalize_text(str(text)), float(score), parsed_box))
    if not lines:
        raise WordBoxReconstructionError("PP-OCRv6 result contains no accepted lines")
    source_image = _read_source_image(source_image_path)
    line_height = statistics.median(line.height for line in lines)
    axes, header_lines, note_right_edge = _header_axes(
        lines, line_height, int(config["minimum_period_headers"])
    )
    body_start = max(line.box[3] for line in header_lines) + line_height * float(
        config["body_start_line_heights_after_period_header"]
    )
    body, after_table = _body_block(
        lines,
        body_start,
        line_height,
        float(config["table_block_gap_line_heights"]),
    )

    axis_positions = [axis.right_edge for axis in axes]
    all_positions = ([note_right_edge] if note_right_edge is not None else []) + axis_positions
    position_gaps = [
        right - left for left, right in zip(all_positions, all_positions[1:], strict=False)
    ]
    if not position_gaps or min(position_gaps) <= 0:
        raise WordBoxReconstructionError("inferred note/value axes are not strictly ordered")
    typical_axis_gap = statistics.median(position_gaps)
    maximum_axis_distance = typical_axis_gap * float(
        config["axis_right_edge_max_distance_ratio"]
    )
    position_labels = (["note"] if note_right_edge is not None else []) + [
        axis.axis_id for axis in axes
    ]
    assignments: dict[str, list[OCRLine]] = {label: [] for label in position_labels}
    unassigned_numeric = []
    for line in body:
        if not _numeric_only(line.text):
            continue
        distances = [abs(line.x_right - position) for position in all_positions]
        closest = min(range(len(distances)), key=distances.__getitem__)
        if distances[closest] <= maximum_axis_distance:
            assignments[position_labels[closest]].append(line)
        else:
            unassigned_numeric.append(line)

    value_lines = [line for axis in axes for line in assignments[axis.axis_id]]
    anchor_clusters = _cluster_by_y(
        value_lines, line_height * float(config["row_anchor_cluster_line_heights"])
    )
    anchor_centers = [statistics.fmean(line.y_center for line in cluster) for cluster in anchor_clusters]
    label_lines = [
        line
        for line in body
        if line not in value_lines
        and line not in assignments.get("note", [])
        and line not in unassigned_numeric
        and not _numeric_only(line.text)
        and line.x_right < axes[0].right_edge
    ]
    label_assignment: dict[int, int] = {}
    direct_tolerance = line_height * float(config["label_direct_attach_line_heights"])
    below_anchor_tolerance = line_height * float(
        config["label_below_anchor_tolerance_line_heights"]
    )
    for line in label_lines:
        if not anchor_centers:
            break
        eligible = [
            index
            for index, center in enumerate(anchor_centers)
            if center >= line.y_center - below_anchor_tolerance
            and center - line.y_center <= direct_tolerance
        ]
        if eligible:
            label_assignment[line.index] = eligible[0]

    wrap_tolerance = line_height * float(config["wrapped_label_center_gap_line_heights"])
    ordered_labels = sorted(label_lines, key=lambda line: line.y_center)
    changed = True
    while changed:
        changed = False
        for position, line in enumerate(ordered_labels):
            if line.index in label_assignment:
                continue
            neighbors = []
            if position:
                neighbors.append(ordered_labels[position - 1])
            if position + 1 < len(ordered_labels):
                neighbors.append(ordered_labels[position + 1])
            candidates = {
                label_assignment[neighbor.index]
                for neighbor in neighbors
                if neighbor.index in label_assignment
                and abs(neighbor.y_center - line.y_center) <= wrap_tolerance
            }
            if len(candidates) == 1:
                anchor_index = next(iter(candidates))
                low, high = sorted((line.y_center, anchor_centers[anchor_index]))
                if not any(low < center < high for center in anchor_centers if center != anchor_centers[anchor_index]):
                    label_assignment[line.index] = anchor_index
                    changed = True

    note_assignment: dict[int, int] = {}
    note_tolerance = line_height * float(config["note_attach_line_heights"])
    for line in assignments.get("note", []):
        if not anchor_centers:
            unassigned_numeric.append(line)
            continue
        distances = [abs(line.y_center - center) for center in anchor_centers]
        closest = min(range(len(distances)), key=distances.__getitem__)
        if distances[closest] <= note_tolerance:
            note_assignment[line.index] = closest
        else:
            unassigned_numeric.append(line)

    proposals: list[GeometryRowProposal] = []
    for anchor_index, (anchor_center, cluster) in enumerate(
        zip(anchor_centers, anchor_clusters, strict=True)
    ):
        labels = sorted(
            (line for line in label_lines if label_assignment.get(line.index) == anchor_index),
            key=lambda line: (line.y_center, line.box[0]),
        )
        notes = sorted(
            (
                line
                for line in assignments.get("note", [])
                if note_assignment.get(line.index) == anchor_index
            ),
            key=lambda line: line.box[0],
        )
        per_axis = [
            sorted(
                (
                    line
                    for line in assignments[axis.axis_id]
                    if line in cluster
                ),
                key=lambda line: line.box[0],
            )
            for axis in axes
        ]
        label = normalize_text(" ".join(line.text for line in labels))
        note_reference = normalize_text(" ".join(line.text for line in notes)) or None
        cells = []
        visual_cell_evidence: list[VisualCellEvidence | None] = []
        for axis, items in zip(axes, per_axis, strict=True):
            cell = parse_financial_number(_join_financial_tokens(items))
            evidence = None
            if not items and source_image is not None and source_image_path is not None:
                evidence = _detect_visible_dash(
                    source_image,
                    source_image_path=source_image_path,
                    axis_right_edge=axis.right_edge,
                    anchor_center=anchor_center,
                    line_height=line_height,
                    config=config,
                )
                if evidence is not None:
                    cell = parse_financial_number("-")
            cells.append(cell)
            visual_cell_evidence.append(evidence)
        source_lines = labels + notes + [line for items in per_axis for line in items]
        warnings = []
        if not labels:
            warnings.append("financial row has no attached label line")
        if any(len(items) > 1 for items in per_axis):
            warnings.append("multiple visible OCR tokens reconstructed in one financial cell")
        if any(evidence is not None for evidence in visual_cell_evidence):
            warnings.append("OCR-blank cell recovered as DASH from constrained pixel evidence")
        proposals.append(
            GeometryRowProposal(
                row=ReaderRow(
                    source_row_ids=_source_ids(page_tag, source_lines),
                    label=label,
                    note_reference=note_reference,
                    cells=tuple(cells),
                ),
                y_anchor=anchor_center,
                label_line_indices=tuple(line.index for line in labels),
                note_line_indices=tuple(line.index for line in notes),
                value_line_indices=tuple(
                    tuple(line.index for line in items) for items in per_axis
                ),
                visual_cell_evidence=tuple(visual_cell_evidence),
                warnings=tuple(warnings),
            )
        )

    trailing_context: list[GeometryRowProposal] = []
    for line in label_lines:
        if line.index in label_assignment:
            continue
        proposal = GeometryRowProposal(
                row=ReaderRow(
                    source_row_ids=_source_ids(page_tag, [line]),
                    label=line.text,
                    note_reference=None,
                    cells=(),
                ),
                y_anchor=line.y_center,
                label_line_indices=(line.index,),
                note_line_indices=(),
                value_line_indices=tuple(() for _ in axes),
                visual_cell_evidence=tuple(None for _ in axes),
                warnings=("label-only row retained without structural merge",),
            )
        if anchor_centers and line.y_center > anchor_centers[-1]:
            trailing_context.append(proposal)
        else:
            proposals.append(proposal)
    proposals.sort(key=lambda proposal: proposal.y_anchor)
    trailing_context.sort(key=lambda proposal: proposal.y_anchor)
    table_line_indices = {
        int(source_id.rsplit("-", 1)[-1])
        for proposal in proposals
        for source_id in proposal.row.source_row_ids
    }
    table_lines = [line for line in body if line.index in table_line_indices]
    if not table_lines:
        raise WordBoxReconstructionError("no line evidence remains in the reconstructed table")
    table_bbox = (
        min(line.box[0] for line in table_lines),
        min(line.box[1] for line in table_lines),
        max(line.box[2] for line in table_lines),
        max(line.box[3] for line in table_lines),
    )
    return ParsedGeometryPage(
        input_path=str(payload.get("input_path", "")),
        axes=axes,
        note_right_edge=note_right_edge,
        table_bbox=table_bbox,
        rows=tuple(proposals),
        trailing_context_rows=tuple(trailing_context),
        line_height=line_height,
        unassigned_numeric_line_indices=tuple(
            line.index for line in sorted(unassigned_numeric, key=lambda line: line.index)
        ),
        excluded_after_table_line_indices=tuple(sorted(line.index for line in after_table)),
    )


def geometry_row_to_dict(proposal: GeometryRowProposal) -> dict[str, Any]:
    return {
        "source_row_ids": list(proposal.row.source_row_ids),
        "label": proposal.row.label,
        "note_reference": proposal.row.note_reference,
        "cells": [
            {
                "raw_text": cell.raw_text,
                "normalized_text": cell.normalized_text,
                "value": str(cell.value) if cell.value is not None else None,
                "observation": cell.observation.value,
                "sign_evidence": cell.sign_evidence,
                "reason": cell.reason,
            }
            for cell in proposal.row.cells
        ],
        "geometry": {
            "y_anchor": proposal.y_anchor,
            "label_line_indices": list(proposal.label_line_indices),
            "note_line_indices": list(proposal.note_line_indices),
            "value_line_indices": [list(indices) for indices in proposal.value_line_indices],
            "visual_cell_evidence": [
                (
                    {
                        "observation": evidence.observation,
                        "source_image_path": evidence.source_image_path,
                        "crop_box": list(evidence.crop_box),
                        "component_box": list(evidence.component_box),
                        "threshold": evidence.threshold,
                        "foreground_contrast": evidence.foreground_contrast,
                        "width_line_heights": evidence.width_line_heights,
                        "height_line_heights": evidence.height_line_heights,
                        "aspect_ratio": evidence.aspect_ratio,
                        "fill_ratio": evidence.fill_ratio,
                    }
                    if evidence is not None
                    else None
                )
                for evidence in proposal.visual_cell_evidence
            ],
        },
        "warnings": list(proposal.warnings),
    }
