from __future__ import annotations

import json
import re
import statistics
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import yaml

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import normalize_text
from bctc_ai.evaluation.financial_cells_v2 import parse_financial_number_strict_grouping
from bctc_ai.evaluation.word_box_rows import (
    OCRLine,
    VisualCellEvidence,
    WordBoxReconstructionError,
    _body_block,
    _join_financial_tokens,
    _numeric_only,
    _read_source_image,
    _source_ids,
)
from bctc_ai.evaluation.word_box_rows_v2 import (
    GeometryRowProposalV2,
    ParsedGeometryPageV2,
    WordBoxReconstructionV2Config,
    _Anchor,
    _build_anchors,
    _header_axes_v2,
    _infer_index_band,
    _nearest_anchor,
    geometry_row_v2_to_dict,
    load_word_box_reconstruction_v2_config,
)
from bctc_ai.validation.reader_agreement import ReaderRow


@dataclass(frozen=True)
class WordBoxReconstructionV3Config:
    base: WordBoxReconstructionV2Config
    source_path: Path
    maximum_period_header_stagger_line_heights: float
    header_companion_max_above_period_line_heights: float
    header_companion_max_below_period_line_heights: float
    header_companion_left_margin_line_heights: float
    roman_note_reference_enabled: bool
    ocr_confusable_roman_note_reference_enabled: bool
    dash_shape_filter_before_uniqueness: bool


def load_word_box_reconstruction_v3_config(path: Path) -> WordBoxReconstructionV3Config:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise WordBoxReconstructionError(f"cannot load word-box v3 config: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 3
        or payload.get("policy") != "STAGGERED_HEADER_ROMAN_NOTE_RULE_AWARE_DASH_V3"
    ):
        raise WordBoxReconstructionError("word-box reconstruction config must be version 3")
    base_name = payload.get("base_config")
    if not isinstance(base_name, str) or Path(base_name).name != base_name:
        raise WordBoxReconstructionError("word-box v3 base_config path is invalid")
    base_path = (path.parent / base_name).resolve()
    if not base_path.is_file() or base_path.parent != path.parent.resolve():
        raise WordBoxReconstructionError("word-box v3 base_config is absent or escapes")
    if sha256_file(base_path) != payload.get("base_config_sha256"):
        raise WordBoxReconstructionError("word-box v3 base_config hash drifted")
    positive = (
        "maximum_period_header_stagger_line_heights",
        "header_companion_max_above_period_line_heights",
        "header_companion_max_below_period_line_heights",
        "header_companion_left_margin_line_heights",
    )
    values = {}
    for name in positive:
        value = payload.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise WordBoxReconstructionError(f"invalid positive v3 setting: {name}")
        values[name] = float(value)
    if not 0.75 <= values["maximum_period_header_stagger_line_heights"] <= 2.0:
        raise WordBoxReconstructionError("word-box v3 header stagger bound is unsafe")
    boolean_names = (
        "roman_note_reference_enabled",
        "ocr_confusable_roman_note_reference_enabled",
        "dash_shape_filter_before_uniqueness",
    )
    if any(payload.get(name) is not True for name in boolean_names):
        raise WordBoxReconstructionError("word-box v3 structural safety switch drifted")
    return WordBoxReconstructionV3Config(
        base=load_word_box_reconstruction_v2_config(base_path),
        source_path=path.resolve(),
        **values,
        **{name: True for name in boolean_names},
    )


_ARABIC_NOTE_REFERENCE = re.compile(r"^\d+(?:[.]\d+)*(?:[(][0-9a-z]+[)])?$", re.IGNORECASE)
_ROMAN_NOTE_REFERENCE = re.compile(
    r"^(?:[ivxlcdm]+|[iIlL1/|]{1,8})[.]\d+(?:[.]\d+)*(?:[(][0-9a-z]+[)])?$",
    re.IGNORECASE,
)


def _note_like_v3(text: str, config: WordBoxReconstructionV3Config) -> bool:
    compact = normalize_text(text).replace(" ", "").strip(". ")
    if _ARABIC_NOTE_REFERENCE.fullmatch(compact):
        return True
    return bool(
        config.roman_note_reference_enabled
        and config.ocr_confusable_roman_note_reference_enabled
        and _ROMAN_NOTE_REFERENCE.fullmatch(compact)
    )


def _header_axes_v3(
    lines: list[OCRLine],
    line_height: float,
    config: WordBoxReconstructionV3Config,
) -> tuple[tuple[Any, ...], list[OCRLine], float | None, list[OCRLine]]:
    effective = replace(
        config.base,
        period_header_y_tolerance_line_heights=(config.maximum_period_header_stagger_line_heights),
    )
    axes, period_lines, note_right_edge = _header_axes_v2(lines, line_height, effective)
    minimum_center = min(line.y_center for line in period_lines)
    maximum_center = max(line.y_center for line in period_lines)
    left_limit = (
        note_right_edge
        if note_right_edge is not None
        else axes[0].right_edge - line_height * config.header_companion_left_margin_line_heights
    ) - line_height * config.header_companion_left_margin_line_heights
    header_companions = [
        line
        for line in lines
        if line.x_right >= left_limit
        and line.y_center
        >= minimum_center - line_height * config.header_companion_max_above_period_line_heights
        and line.y_center
        <= maximum_center + line_height * config.header_companion_max_below_period_line_heights
    ]
    period_indices = {line.index for line in period_lines}
    return (
        axes,
        period_lines,
        note_right_edge,
        [line for line in header_companions if line.index not in period_indices],
    )


def _dash_component_evidence(
    crop: np.ndarray,
    *,
    threshold: float,
    x0: int,
    y0: int,
    component: tuple[int, int, int, int, int],
    source_image_path: Path,
    crop_box: tuple[int, int, int, int],
    axis_right_edge: float,
    anchor_center: float,
    line_height: float,
    config: dict[str, float | int],
) -> VisualCellEvidence | None:
    component_x, component_y, width, height, area = component
    width_ratio = width / line_height
    height_ratio = height / line_height
    aspect_ratio = width / height
    fill_ratio = area / (width * height)
    absolute_right = x0 + component_x + width
    right_offset = axis_right_edge - absolute_right
    absolute_center_y = y0 + component_y + height / 2
    component_pixels = crop[component_y : component_y + height, component_x : component_x + width]
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
        and abs(absolute_center_y - anchor_center)
        <= line_height * float(config["dash_component_center_tolerance_line_heights"])
    ):
        return None
    return VisualCellEvidence(
        observation="DASH",
        source_image_path=str(source_image_path),
        crop_box=crop_box,
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


def _detect_visible_dash_v3(
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
    threshold, foreground = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    component_count, _, stats, _ = cv2.connectedComponentsWithStats(foreground, 8)
    minimum_area = line_height**2 * float(config["dash_min_component_area_line_heights_squared"])
    candidates = []
    for index in range(1, component_count):
        component = tuple(int(value) for value in stats[index])
        if component[4] < minimum_area:
            continue
        evidence = _dash_component_evidence(
            crop,
            threshold=threshold,
            x0=x0,
            y0=y0,
            component=component,
            source_image_path=source_image_path,
            crop_box=(x0, y0, x1, y1),
            axis_right_edge=axis_right_edge,
            anchor_center=anchor_center,
            line_height=line_height,
            config=config,
        )
        if evidence is not None:
            candidates.append(evidence)
    return candidates[0] if len(candidates) == 1 else None


def _blank_or_dash_cells_v3(
    axes: tuple[Any, ...],
    per_axis: list[list[OCRLine]],
    *,
    source_image: np.ndarray | None,
    source_image_path: Path | None,
    anchor_center: float,
    line_height: float,
    base_config: dict[str, float | int],
) -> tuple[tuple[Any, ...], tuple[VisualCellEvidence | None, ...]]:
    cells = []
    evidence_records = []
    for axis, items in zip(axes, per_axis, strict=True):
        cell = parse_financial_number_strict_grouping(_join_financial_tokens(items))
        evidence = None
        if not items and source_image is not None and source_image_path is not None:
            evidence = _detect_visible_dash_v3(
                source_image,
                source_image_path=source_image_path,
                axis_right_edge=axis.right_edge,
                anchor_center=anchor_center,
                line_height=line_height,
                config=base_config,
            )
            if evidence is not None:
                cell = parse_financial_number_strict_grouping("-")
        cells.append(cell)
        evidence_records.append(evidence)
    return tuple(cells), tuple(evidence_records)


def _build_anchors_with_bounded_note_distance(
    value_lines: list[OCRLine],
    note_lines: list[OCRLine],
    index_lines: list[OCRLine],
    line_height: float,
    config: WordBoxReconstructionV3Config,
    note_attach_line_heights: float,
) -> list[_Anchor]:
    """Keep a distant note row independent from the following value row.

    V3 used the same broad structural tolerance for row indices and note
    references. A note one full line above a numeric row could therefore merge
    its label-only row into the following valued row. V4 supplies a tighter,
    explicit note-to-value bound while preserving the V3 anchor behavior for
    indices and all close note references.
    """

    anchors = _build_anchors(value_lines, index_lines, line_height, config.base)
    tolerance = line_height * note_attach_line_heights
    for line in sorted(note_lines, key=lambda item: item.y_center):
        distances = [abs(line.y_center - anchor.center) for anchor in anchors]
        if distances:
            closest = min(range(len(distances)), key=distances.__getitem__)
        else:
            closest = -1
        if distances and distances[closest] <= tolerance:
            anchors[closest].structural_lines.append(line)
        else:
            anchors.append(_Anchor(line.y_center, [], [line]))
    return sorted(anchors, key=lambda anchor: anchor.center)


def parse_ppocrv6_word_box_page_v3(
    result_path: Path,
    config: WordBoxReconstructionV3Config,
    *,
    page_tag: str,
    source_image_path: Path | None = None,
    note_to_value_anchor_attach_line_heights: float | None = None,
) -> ParsedGeometryPageV2:
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
    for index, (text, score, box) in enumerate(zip(raw_texts, raw_scores, raw_boxes, strict=True)):
        if not isinstance(box, list) or len(box) != 4:
            raise WordBoxReconstructionError(f"line {index} has no four-coordinate box")
        parsed_box = tuple(float(value) for value in box)
        if parsed_box[2] <= parsed_box[0] or parsed_box[3] <= parsed_box[1]:
            raise WordBoxReconstructionError(f"line {index} has a degenerate box")
        if float(score) < float(config.base.base["minimum_line_score"]):
            continue
        lines.append(OCRLine(index, normalize_text(str(text)), float(score), parsed_box))
    if not lines:
        raise WordBoxReconstructionError("PP-OCRv6 result contains no accepted lines")
    source_image = _read_source_image(source_image_path)
    line_height = statistics.median(line.height for line in lines)
    axes, header_lines, note_right_edge, header_companions = _header_axes_v3(
        lines, line_height, config
    )
    body_start = max(line.box[3] for line in [*header_lines, *header_companions]) + (
        line_height * float(config.base.base["body_start_line_heights_after_period_header"])
    )
    body, after_table = _body_block(
        lines,
        body_start,
        line_height,
        float(config.base.base["table_block_gap_line_heights"]),
    )

    axis_positions = [axis.right_edge for axis in axes]
    all_positions = ([note_right_edge] if note_right_edge is not None else []) + axis_positions
    gaps = [right - left for left, right in zip(all_positions, all_positions[1:], strict=False)]
    if not gaps or min(gaps) <= 0:
        raise WordBoxReconstructionError("inferred note/value axes are not strictly ordered")
    maximum_axis_distance = statistics.median(gaps) * float(
        config.base.base["axis_right_edge_max_distance_ratio"]
    )
    value_assignments: dict[str, list[OCRLine]] = {axis.axis_id: [] for axis in axes}
    note_lines = []
    numeric_candidates = []
    for line in body:
        if note_right_edge is not None and _note_like_v3(line.text, config):
            if abs(line.x_right - note_right_edge) <= maximum_axis_distance:
                note_lines.append(line)
                continue
        if _numeric_only(line.text):
            numeric_candidates.append(line)
            distances = [abs(line.x_right - axis.right_edge) for axis in axes]
            closest = min(range(len(distances)), key=distances.__getitem__)
            if (
                distances[closest] <= maximum_axis_distance
                and line.x_right
                <= axes[closest].right_edge
                + line_height * config.base.axis_right_overrun_line_heights
            ):
                value_assignments[axes[closest].axis_id].append(line)

    value_lines = [line for axis in axes for line in value_assignments[axis.axis_id]]
    excluded_for_index = {line.index for line in value_lines + note_lines}
    index_band, index_lines = _infer_index_band(
        body,
        excluded_for_index,
        axes[0].right_edge,
        line_height,
        header_lines,
        config.base,
    )
    assigned_numeric_indices = {line.index for line in value_lines + note_lines + index_lines}
    unassigned_numeric = [
        line for line in numeric_candidates if line.index not in assigned_numeric_indices
    ]
    anchors = (
        _build_anchors(value_lines, note_lines + index_lines, line_height, config.base)
        if note_to_value_anchor_attach_line_heights is None
        else _build_anchors_with_bounded_note_distance(
            value_lines,
            note_lines,
            index_lines,
            line_height,
            config,
            note_to_value_anchor_attach_line_heights,
        )
    )
    anchor_centers = [anchor.center for anchor in anchors]

    excluded_label_indices = {
        line.index for line in value_lines + note_lines + index_lines + unassigned_numeric
    }
    label_lines = [
        line
        for line in body
        if line.index not in excluded_label_indices
        and not _numeric_only(line.text)
        and line.x_right < axes[0].right_edge
    ]
    label_assignment: dict[int, int] = {}
    direct_tolerance = line_height * float(config.base.base["label_direct_attach_line_heights"])
    below_tolerance = line_height * float(
        config.base.base["label_below_anchor_tolerance_line_heights"]
    )
    for line in label_lines:
        eligible = [
            index
            for index, center in enumerate(anchor_centers)
            if center >= line.y_center - below_tolerance
            and center - line.y_center <= direct_tolerance
        ]
        if eligible:
            label_assignment[line.index] = eligible[0]

    wrap_tolerance = line_height * float(config.base.base["wrapped_label_center_gap_line_heights"])
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
                if not any(
                    low < center < high
                    for index, center in enumerate(anchor_centers)
                    if index != anchor_index
                ):
                    label_assignment[line.index] = anchor_index
                    changed = True

    structural_tolerance = line_height * config.base.structural_anchor_attach_line_heights
    index_assignment = {}
    for index_line in index_lines:
        paired_labels = [
            line
            for line in label_lines
            if line.index in label_assignment
            and line.box[0] > index_line.x_right
            and abs(line.y_center - index_line.y_center) <= structural_tolerance
        ]
        if paired_labels:
            paired = min(
                paired_labels,
                key=lambda line: (abs(line.y_center - index_line.y_center), line.box[0]),
            )
            index_assignment[index_line.index] = label_assignment[paired.index]
            continue
        nearest = _nearest_anchor(index_line, anchors, structural_tolerance)
        if nearest is not None:
            index_assignment[index_line.index] = nearest

    proposals = []
    for anchor_index, anchor in enumerate(anchors):
        labels = sorted(
            (line for line in label_lines if label_assignment.get(line.index) == anchor_index),
            key=lambda line: (line.y_center, line.box[0]),
        )
        codes = sorted(
            (line for line in index_lines if index_assignment.get(line.index) == anchor_index),
            key=lambda line: line.box[0],
        )
        notes = sorted(
            (
                line
                for line in note_lines
                if _nearest_anchor(line, anchors, structural_tolerance) == anchor_index
            ),
            key=lambda line: line.box[0],
        )
        per_axis = [
            sorted(
                (line for line in value_assignments[axis.axis_id] if line in anchor.value_lines),
                key=lambda line: line.box[0],
            )
            for axis in axes
        ]
        cells, visual_evidence = _blank_or_dash_cells_v3(
            axes,
            per_axis,
            source_image=source_image,
            source_image_path=source_image_path,
            anchor_center=anchor.center,
            line_height=line_height,
            base_config=config.base.base,
        )
        label = normalize_text(" ".join(line.text for line in labels))
        row_code = normalize_text(" ".join(line.text for line in codes)) or None
        if row_code is None and index_band is not None and labels:
            first_label_left = min(line.box[0] for line in labels)
            prefix_match = re.fullmatch(
                r"([0-9]{1,3}|[IVXLCDM]{1,8}|[A-Z])\s+(.+)",
                label,
            )
            if (
                prefix_match is not None
                and first_label_left
                <= index_band.right_edge + line_height * config.base.index_left_gap_line_heights
            ):
                row_code = prefix_match.group(1)
                label = normalize_text(prefix_match.group(2))
        note_reference = normalize_text(" ".join(line.text for line in notes)) or None
        source_lines = codes + labels + notes + [line for items in per_axis for line in items]
        warnings = []
        if not label:
            warnings.append("structural or financial row has no attached label line")
        if any(len(items) > 1 for items in per_axis):
            warnings.append("multiple visible OCR tokens reconstructed in one financial cell")
        if any(cell.observation is ObservationKind.INVALID for cell in cells):
            warnings.append("one or more reconstructed cells are invalid")
        if any(evidence is not None for evidence in visual_evidence):
            warnings.append("OCR-blank cell recovered as DASH from constrained pixel evidence")
        proposals.append(
            GeometryRowProposalV2(
                row=ReaderRow(
                    source_row_ids=_source_ids(page_tag, source_lines),
                    label=label,
                    note_reference=note_reference,
                    cells=cells,
                ),
                row_code=row_code,
                y_anchor=anchor.center,
                index_line_indices=tuple(line.index for line in codes),
                label_line_indices=tuple(line.index for line in labels),
                note_line_indices=tuple(line.index for line in notes),
                value_line_indices=tuple(tuple(line.index for line in items) for items in per_axis),
                visual_cell_evidence=visual_evidence,
                warnings=tuple(warnings),
            )
        )

    trailing_context = []
    for line in label_lines:
        if line.index in label_assignment:
            continue
        cells, visual_evidence = _blank_or_dash_cells_v3(
            axes,
            [[] for _axis in axes],
            source_image=source_image,
            source_image_path=source_image_path,
            anchor_center=line.y_center,
            line_height=line_height,
            base_config=config.base.base,
        )
        proposal = GeometryRowProposalV2(
            row=ReaderRow(
                source_row_ids=_source_ids(page_tag, [line]),
                label=line.text,
                note_reference=None,
                cells=cells,
            ),
            row_code=None,
            y_anchor=line.y_center,
            index_line_indices=(),
            label_line_indices=(line.index,),
            note_line_indices=(),
            value_line_indices=tuple(() for _axis in axes),
            visual_cell_evidence=visual_evidence,
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
    return ParsedGeometryPageV2(
        input_path=str(payload.get("input_path", "")),
        axes=axes,
        note_right_edge=note_right_edge,
        index_band=index_band,
        table_bbox=table_bbox,
        rows=tuple(proposals),
        trailing_context_rows=tuple(trailing_context),
        line_height=line_height,
        unassigned_numeric_line_indices=tuple(
            line.index for line in sorted(unassigned_numeric, key=lambda line: line.index)
        ),
        excluded_after_table_line_indices=tuple(sorted(line.index for line in after_table)),
    )


geometry_row_v3_to_dict = geometry_row_v2_to_dict
