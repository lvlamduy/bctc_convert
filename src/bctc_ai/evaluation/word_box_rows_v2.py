from __future__ import annotations

import json
import re
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.text import normalize_text, retrieval_key
from bctc_ai.evaluation.financial_cells_v2 import parse_financial_number_strict_grouping
from bctc_ai.evaluation.word_box_rows import (
    GeometryAxis,
    OCRLine,
    VisualCellEvidence,
    WordBoxReconstructionError,
    _body_block,
    _cluster_by_y,
    _detect_visible_dash,
    _join_financial_tokens,
    _numeric_only,
    _read_source_image,
    _source_ids,
    load_word_box_reconstruction_config,
)
from bctc_ai.validation.reader_agreement import ReaderRow


@dataclass(frozen=True)
class WordBoxReconstructionV2Config:
    base: dict[str, float | int]
    base_path: Path
    maximum_period_header_tokens: int
    period_header_y_tolerance_line_heights: float
    period_header_minimum_x_separation_line_heights: float
    index_candidate_max_width_line_heights: float
    index_left_gap_line_heights: float
    index_minimum_repeated_rows: int
    label_candidate_min_width_line_heights: float
    structural_anchor_attach_line_heights: float
    axis_right_overrun_line_heights: float


@dataclass(frozen=True)
class GeometryIndexBand:
    right_edge: float
    supporting_line_indices: tuple[int, ...]
    header_detected: bool


@dataclass(frozen=True)
class GeometryRowProposalV2:
    row: ReaderRow
    row_code: str | None
    y_anchor: float
    index_line_indices: tuple[int, ...]
    label_line_indices: tuple[int, ...]
    note_line_indices: tuple[int, ...]
    value_line_indices: tuple[tuple[int, ...], ...]
    visual_cell_evidence: tuple[VisualCellEvidence | None, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class ParsedGeometryPageV2:
    input_path: str
    axes: tuple[GeometryAxis, ...]
    note_right_edge: float | None
    index_band: GeometryIndexBand | None
    table_bbox: tuple[float, float, float, float]
    rows: tuple[GeometryRowProposalV2, ...]
    trailing_context_rows: tuple[GeometryRowProposalV2, ...]
    line_height: float
    unassigned_numeric_line_indices: tuple[int, ...]
    excluded_after_table_line_indices: tuple[int, ...]

    @property
    def reader_rows(self) -> tuple[ReaderRow, ...]:
        return tuple(proposal.row for proposal in self.rows)


def load_word_box_reconstruction_v2_config(path: Path) -> WordBoxReconstructionV2Config:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("version") != 2:
        raise WordBoxReconstructionError("word-box reconstruction config must be version 2")
    raw_base_path = payload.get("base_config")
    if not isinstance(raw_base_path, str) or not raw_base_path:
        raise WordBoxReconstructionError("word-box v2 config has no base_config")
    base_path = (path.parent / raw_base_path).resolve()
    try:
        base_path.relative_to(path.parent.resolve())
    except ValueError as exc:
        raise WordBoxReconstructionError("word-box v2 base_config escapes its directory") from exc
    base = load_word_box_reconstruction_config(base_path)
    positive_float_fields = (
        "period_header_y_tolerance_line_heights",
        "period_header_minimum_x_separation_line_heights",
        "index_candidate_max_width_line_heights",
        "index_left_gap_line_heights",
        "label_candidate_min_width_line_heights",
        "structural_anchor_attach_line_heights",
        "axis_right_overrun_line_heights",
    )
    values: dict[str, float] = {}
    for name in positive_float_fields:
        value = payload.get(name)
        if not isinstance(value, (int, float)) or value <= 0:
            raise WordBoxReconstructionError(f"invalid positive v2 setting: {name}")
        values[name] = float(value)
    maximum_tokens = payload.get("maximum_period_header_tokens")
    minimum_rows = payload.get("index_minimum_repeated_rows")
    if not isinstance(maximum_tokens, int) or maximum_tokens < 1:
        raise WordBoxReconstructionError("maximum_period_header_tokens must be positive")
    if not isinstance(minimum_rows, int) or minimum_rows < 2:
        raise WordBoxReconstructionError("index_minimum_repeated_rows must be at least two")
    return WordBoxReconstructionV2Config(
        base=base,
        base_path=base_path,
        maximum_period_header_tokens=maximum_tokens,
        index_minimum_repeated_rows=minimum_rows,
        **values,
    )


_YEAR = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
_NOTE_REFERENCE = re.compile(r"^\d+(?:[.]\d+)*(?:\s*[(][0-9a-z]+[)])?$", re.IGNORECASE)
_INDEX_CODE = re.compile(r"^(?:\d{1,3}|[ivxlcdm]{1,8}|[a-z]|[ivxlcdm]+[.]?\d*)$", re.IGNORECASE)


def _period_header_like(line: OCRLine, config: WordBoxReconstructionV2Config) -> bool:
    normalized = normalize_text(line.text)
    return bool(_YEAR.search(normalized)) and len(retrieval_key(normalized).split()) <= (
        config.maximum_period_header_tokens
    )


def _header_axes_v2(
    lines: list[OCRLine], line_height: float, config: WordBoxReconstructionV2Config
) -> tuple[tuple[GeometryAxis, ...], list[OCRLine], float | None]:
    candidates = [line for line in lines if _period_header_like(line, config)]
    clusters = _cluster_by_y(
        candidates,
        line_height * config.period_header_y_tolerance_line_heights,
    )
    minimum_headers = int(config.base["minimum_period_headers"])
    minimum_gap = line_height * config.period_header_minimum_x_separation_line_heights
    groups = []
    for cluster in clusters:
        ordered = sorted(cluster, key=lambda line: line.x_right)
        if len(ordered) < minimum_headers:
            continue
        if (
            min(
                (
                    right.x_right - left.x_right
                    for left, right in zip(ordered, ordered[1:], strict=False)
                ),
                default=0,
            )
            < minimum_gap
        ):
            continue
        groups.append(ordered)
    if not groups:
        raise WordBoxReconstructionError("could not infer two separated period header axes")
    header_lines = min(
        groups,
        key=lambda group: (
            group[-1].x_right - group[0].x_right,
            statistics.fmean(line.y_center for line in group),
        ),
    )
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
        and any(token in retrieval_key(line.text) for token in ("thuy", "minh", "ghi chu"))
    ]
    note_right_edge = (
        statistics.median(line.x_right for line in note_candidates) if note_candidates else None
    )
    return axes, header_lines, note_right_edge


def _note_like(text: str) -> bool:
    return bool(_NOTE_REFERENCE.fullmatch(normalize_text(text).replace(" ", "")))


def _index_like(text: str) -> bool:
    normalized = normalize_text(text).strip(".():- ")
    return bool(_INDEX_CODE.fullmatch(normalized))


def _infer_index_band(
    body: list[OCRLine],
    excluded: set[int],
    first_value_right: float,
    line_height: float,
    header_lines: list[OCRLine],
    config: WordBoxReconstructionV2Config,
) -> tuple[GeometryIndexBand | None, list[OCRLine]]:
    candidates_before_values = [
        line for line in body if line.index not in excluded and line.x_right < first_value_right
    ]
    wide_labels = [
        line
        for line in candidates_before_values
        if not _numeric_only(line.text)
        and not _index_like(line.text)
        and line.box[2] - line.box[0] >= line_height * config.label_candidate_min_width_line_heights
    ]
    if not wide_labels:
        return None, []
    maximum_width = line_height * config.index_candidate_max_width_line_heights
    minimum_gap = line_height * config.index_left_gap_line_heights
    row_pair_tolerance = line_height * config.structural_anchor_attach_line_heights
    index_lines = [
        line
        for line in candidates_before_values
        if _index_like(line.text)
        and line.box[2] - line.box[0] <= maximum_width
        and any(
            abs(label.y_center - line.y_center) <= row_pair_tolerance
            and line.x_right + minimum_gap <= label.box[0]
            for label in wide_labels
        )
    ]
    if len(index_lines) < config.index_minimum_repeated_rows:
        return None, []
    header_detected = any("stt" in retrieval_key(line.text) for line in header_lines)
    return (
        GeometryIndexBand(
            right_edge=statistics.median(line.x_right for line in index_lines),
            supporting_line_indices=tuple(line.index for line in index_lines),
            header_detected=header_detected,
        ),
        index_lines,
    )


@dataclass
class _Anchor:
    center: float
    value_lines: list[OCRLine]
    structural_lines: list[OCRLine]


def _build_anchors(
    value_lines: list[OCRLine],
    structural_lines: list[OCRLine],
    line_height: float,
    config: WordBoxReconstructionV2Config,
) -> list[_Anchor]:
    anchors = [
        _Anchor(
            center=statistics.fmean(line.y_center for line in cluster),
            value_lines=list(cluster),
            structural_lines=[],
        )
        for cluster in _cluster_by_y(
            value_lines,
            line_height * float(config.base["row_anchor_cluster_line_heights"]),
        )
    ]
    tolerance = line_height * config.structural_anchor_attach_line_heights
    for line in sorted(structural_lines, key=lambda item: item.y_center):
        if anchors:
            distances = [abs(line.y_center - anchor.center) for anchor in anchors]
            closest = min(range(len(distances)), key=distances.__getitem__)
        else:
            closest = -1
            distances = []
        if distances and distances[closest] <= tolerance:
            anchors[closest].structural_lines.append(line)
        else:
            anchors.append(_Anchor(line.y_center, [], [line]))
    return sorted(anchors, key=lambda anchor: anchor.center)


def _nearest_anchor(line: OCRLine, anchors: list[_Anchor], tolerance: float) -> int | None:
    if not anchors:
        return None
    distances = [abs(line.y_center - anchor.center) for anchor in anchors]
    closest = min(range(len(distances)), key=distances.__getitem__)
    return closest if distances[closest] <= tolerance else None


def _blank_or_dash_cells(
    axes: tuple[GeometryAxis, ...],
    per_axis: list[list[OCRLine]],
    *,
    source_image,
    source_image_path: Path | None,
    anchor_center: float,
    line_height: float,
    base_config: dict[str, float | int],
) -> tuple[tuple[Any, ...], tuple[VisualCellEvidence | None, ...]]:
    cells = []
    evidence_records: list[VisualCellEvidence | None] = []
    for axis, items in zip(axes, per_axis, strict=True):
        cell = parse_financial_number_strict_grouping(_join_financial_tokens(items))
        evidence = None
        if not items and source_image is not None and source_image_path is not None:
            evidence = _detect_visible_dash(
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


def parse_ppocrv6_word_box_page_v2(
    result_path: Path,
    config: WordBoxReconstructionV2Config,
    *,
    page_tag: str,
    source_image_path: Path | None = None,
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
        if float(score) < float(config.base["minimum_line_score"]):
            continue
        lines.append(OCRLine(index, normalize_text(str(text)), float(score), parsed_box))
    if not lines:
        raise WordBoxReconstructionError("PP-OCRv6 result contains no accepted lines")
    source_image = _read_source_image(source_image_path)
    line_height = statistics.median(line.height for line in lines)
    axes, header_lines, note_right_edge = _header_axes_v2(lines, line_height, config)
    body_start = max(line.box[3] for line in header_lines) + line_height * float(
        config.base["body_start_line_heights_after_period_header"]
    )
    body, after_table = _body_block(
        lines,
        body_start,
        line_height,
        float(config.base["table_block_gap_line_heights"]),
    )

    axis_positions = [axis.right_edge for axis in axes]
    all_positions = ([note_right_edge] if note_right_edge is not None else []) + axis_positions
    gaps = [right - left for left, right in zip(all_positions, all_positions[1:], strict=False)]
    if not gaps or min(gaps) <= 0:
        raise WordBoxReconstructionError("inferred note/value axes are not strictly ordered")
    maximum_axis_distance = statistics.median(gaps) * float(
        config.base["axis_right_edge_max_distance_ratio"]
    )
    value_assignments: dict[str, list[OCRLine]] = {axis.axis_id: [] for axis in axes}
    note_lines: list[OCRLine] = []
    numeric_candidates: list[OCRLine] = []
    for line in body:
        if note_right_edge is not None and _note_like(line.text):
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
                <= axes[closest].right_edge + line_height * config.axis_right_overrun_line_heights
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
        config,
    )
    assigned_numeric_indices = {line.index for line in value_lines + note_lines + index_lines}
    unassigned_numeric = [
        line for line in numeric_candidates if line.index not in assigned_numeric_indices
    ]
    anchors = _build_anchors(value_lines, note_lines + index_lines, line_height, config)
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
    direct_tolerance = line_height * float(config.base["label_direct_attach_line_heights"])
    below_tolerance = line_height * float(config.base["label_below_anchor_tolerance_line_heights"])
    for line in label_lines:
        eligible = [
            index
            for index, center in enumerate(anchor_centers)
            if center >= line.y_center - below_tolerance
            and center - line.y_center <= direct_tolerance
        ]
        if eligible:
            label_assignment[line.index] = eligible[0]

    wrap_tolerance = line_height * float(config.base["wrapped_label_center_gap_line_heights"])
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

    structural_tolerance = line_height * config.structural_anchor_attach_line_heights
    index_assignment: dict[int, int] = {}
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
    proposals: list[GeometryRowProposalV2] = []
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
        cells, visual_evidence = _blank_or_dash_cells(
            axes,
            per_axis,
            source_image=source_image,
            source_image_path=source_image_path,
            anchor_center=anchor.center,
            line_height=line_height,
            base_config=config.base,
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
                <= index_band.right_edge + line_height * config.index_left_gap_line_heights
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

    trailing_context: list[GeometryRowProposalV2] = []
    for line in label_lines:
        if line.index in label_assignment:
            continue
        cells, visual_evidence = _blank_or_dash_cells(
            axes,
            [[] for _axis in axes],
            source_image=source_image,
            source_image_path=source_image_path,
            anchor_center=line.y_center,
            line_height=line_height,
            base_config=config.base,
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


def geometry_row_v2_to_dict(proposal: GeometryRowProposalV2) -> dict[str, Any]:
    return {
        "source_row_ids": list(proposal.row.source_row_ids),
        "row_code": proposal.row_code,
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
            "index_line_indices": list(proposal.index_line_indices),
            "label_line_indices": list(proposal.label_line_indices),
            "note_line_indices": list(proposal.note_line_indices),
            "value_line_indices": [list(items) for items in proposal.value_line_indices],
            "visual_cell_evidence": [
                None
                if evidence is None
                else {
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
                for evidence in proposal.visual_cell_evidence
            ],
        },
        "warnings": list(proposal.warnings),
    }
