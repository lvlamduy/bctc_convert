from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from statistics import median
from typing import Any

import yaml

from bctc_ai.core.contracts import BoundingBox, ObservationKind
from bctc_ai.core.text import parse_financial_number, parse_unit, retrieval_key
from bctc_ai.ocr.pdf_text import PDFTextPage, PDFWord


class ColumnRole(StrEnum):
    NOTE_REFERENCE = "NOTE_REFERENCE"
    VALUE = "VALUE"


@dataclass(frozen=True)
class GeometryConfig:
    version: int
    footer_y_ratio: float
    run_separation_gap_height_factor: float
    financial_token_separation_gap_height_factor: float
    edge_tolerance_ratio: float
    minimum_edge_tolerance_points: float
    assignment_tolerance_multiplier: float
    minimum_numeric_samples: int
    value_minimum_x_ratio: float
    note_minimum_x_ratio: float
    note_header_aliases: tuple[str, ...]
    band_y_tolerance_height_factor: float
    maximum_wrap_gap_height_factor: float
    indentation_tolerance_ratio: float
    preceding_line_occupancy_threshold: float
    header_left_margin_from_value_ratio: float


@dataclass(frozen=True)
class TextRun:
    run_id: str
    raw_text: str
    normalized_text: str
    bbox: BoundingBox
    word_indices: tuple[int, ...]
    block_number: int
    line_number: int

    @property
    def x_center(self) -> float:
        return (self.bbox.x0 + self.bbox.x1) / 2

    @property
    def y_center(self) -> float:
        return (self.bbox.y0 + self.bbox.y1) / 2

    @property
    def height(self) -> float:
        return self.bbox.y1 - self.bbox.y0


@dataclass(frozen=True)
class NumericCluster:
    right_edge: float
    left_edge: float
    run_ids: tuple[str, ...]
    sample_count: int


@dataclass(frozen=True)
class ColumnAxis:
    axis_id: str
    role: ColumnRole
    right_edge: float
    left_edge: float
    sample_count: int
    source: str

    @property
    def center(self) -> float:
        return (self.left_edge + self.right_edge) / 2


@dataclass(frozen=True)
class PageGeometry:
    page: int
    width_points: float
    height_points: float
    data_start_y: float
    data_end_y: float
    label_right_boundary: float
    edge_tolerance: float
    runs: tuple[TextRun, ...]
    axes: tuple[ColumnAxis, ...]
    unit_run_ids: tuple[str, ...]
    warnings: tuple[str, ...]


def load_geometry_config(path: Path) -> GeometryConfig:
    payload: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    axis = payload.get("axis")
    row = payload.get("row")
    header = payload.get("header")
    if (
        not isinstance(payload.get("version"), int)
        or not isinstance(axis, dict)
        or not isinstance(row, dict)
        or not isinstance(header, dict)
    ):
        raise ValueError(f"invalid geometry configuration: {path}")
    aliases = axis.get("note_header_aliases")
    if not isinstance(aliases, list) or not aliases:
        raise ValueError(f"geometry configuration has no note aliases: {path}")
    config = GeometryConfig(
        version=payload["version"],
        footer_y_ratio=float(payload["footer_y_ratio"]),
        run_separation_gap_height_factor=float(axis["run_separation_gap_height_factor"]),
        financial_token_separation_gap_height_factor=float(
            axis.get(
                "financial_token_separation_gap_height_factor",
                axis["run_separation_gap_height_factor"],
            )
        ),
        edge_tolerance_ratio=float(axis["edge_tolerance_ratio"]),
        minimum_edge_tolerance_points=float(axis["minimum_edge_tolerance_points"]),
        assignment_tolerance_multiplier=float(axis["assignment_tolerance_multiplier"]),
        minimum_numeric_samples=int(axis["minimum_numeric_samples"]),
        value_minimum_x_ratio=float(axis["value_minimum_x_ratio"]),
        note_minimum_x_ratio=float(axis["note_minimum_x_ratio"]),
        note_header_aliases=tuple(str(alias) for alias in aliases),
        band_y_tolerance_height_factor=float(row["band_y_tolerance_height_factor"]),
        maximum_wrap_gap_height_factor=float(row["maximum_wrap_gap_height_factor"]),
        indentation_tolerance_ratio=float(row["indentation_tolerance_ratio"]),
        preceding_line_occupancy_threshold=float(row["preceding_line_occupancy_threshold"]),
        header_left_margin_from_value_ratio=float(header["left_margin_from_value_ratio"]),
    )
    if config.version < 1:
        raise ValueError(f"geometry configuration version must be positive: {path}")
    if not 0 < config.footer_y_ratio <= 1:
        raise ValueError(f"geometry footer ratio is outside (0, 1]: {path}")
    if not 0 < config.note_minimum_x_ratio < config.value_minimum_x_ratio < 1:
        raise ValueError(f"geometry column ratios are not ordered inside (0, 1): {path}")
    if config.minimum_numeric_samples < 1:
        raise ValueError(f"geometry minimum numeric sample count must be positive: {path}")
    positive = (
        config.run_separation_gap_height_factor,
        config.financial_token_separation_gap_height_factor,
        config.edge_tolerance_ratio,
        config.minimum_edge_tolerance_points,
        config.assignment_tolerance_multiplier,
        config.band_y_tolerance_height_factor,
        config.maximum_wrap_gap_height_factor,
        config.indentation_tolerance_ratio,
    )
    if any(value <= 0 for value in positive):
        raise ValueError(f"geometry scale/tolerance values must be positive: {path}")
    if not 0 < config.preceding_line_occupancy_threshold <= 1:
        raise ValueError(f"geometry occupancy threshold is outside (0, 1]: {path}")
    if config.header_left_margin_from_value_ratio < 0:
        raise ValueError(f"geometry header margin cannot be negative: {path}")
    return config


def _union(boxes: list[BoundingBox]) -> BoundingBox:
    return BoundingBox(
        min(box.x0 for box in boxes),
        min(box.y0 for box in boxes),
        max(box.x1 for box in boxes),
        max(box.y1 for box in boxes),
    )


def _split_line_words(
    members: list[tuple[int, PDFWord]],
    *,
    gap_height_factor: float,
    financial_gap_height_factor: float,
) -> list[list[tuple[int, PDFWord]]]:
    ordered = sorted(
        members,
        key=lambda member: (member[1].word_number, member[1].bbox_points.x0),
    )
    if not ordered:
        return []
    heights = [
        word.bbox_points.y1 - word.bbox_points.y0
        for _, word in ordered
        if word.bbox_points.y1 > word.bbox_points.y0
    ]
    line_height = float(median(heights)) if heights else 8.0
    maximum_inline_gap = line_height * gap_height_factor
    segments: list[list[tuple[int, PDFWord]]] = [[ordered[0]]]
    for member in ordered[1:]:
        previous_word = segments[-1][-1][1]
        horizontal_gap = member[1].bbox_points.x0 - previous_word.bbox_points.x1
        previous_observation = parse_financial_number(
            previous_word.normalized_text
        ).observation
        current_observation = parse_financial_number(member[1].normalized_text).observation
        independent_financial_tokens = (
            previous_observation
            in {ObservationKind.VALUE, ObservationKind.ZERO, ObservationKind.DASH}
            and current_observation
            in {ObservationKind.VALUE, ObservationKind.ZERO, ObservationKind.DASH}
            and horizontal_gap >= line_height * financial_gap_height_factor
        )
        if horizontal_gap > maximum_inline_gap or independent_financial_tokens:
            segments.append([member])
        else:
            segments[-1].append(member)
    return segments


def build_text_runs(
    words: list[PDFWord],
    *,
    gap_height_factor: float = 2.0,
    financial_gap_height_factor: float = 0.5,
) -> list[TextRun]:
    if gap_height_factor <= 0 or financial_gap_height_factor <= 0:
        raise ValueError("gap factors must be positive")
    grouped: dict[tuple[int, int], list[tuple[int, PDFWord]]] = {}
    for index, word in enumerate(words):
        grouped.setdefault((word.block_number, word.line_number), []).append((index, word))
    runs = []
    for (block_number, line_number), members in grouped.items():
        segments = _split_line_words(
            members,
            gap_height_factor=gap_height_factor,
            financial_gap_height_factor=financial_gap_height_factor,
        )
        for segment_index, segment in enumerate(segments, start=1):
            member_words = [member[1] for member in segment]
            runs.append(
                TextRun(
                    run_id=f"b{block_number}:l{line_number}:s{segment_index}",
                    raw_text=" ".join(word.raw_text for word in member_words),
                    normalized_text=" ".join(word.normalized_text for word in member_words),
                    bbox=_union([word.bbox_points for word in member_words]),
                    word_indices=tuple(member[0] for member in segment),
                    block_number=block_number,
                    line_number=line_number,
                )
            )
    return sorted(runs, key=lambda run: (run.bbox.y0, run.bbox.x0, run.run_id))


def _is_numeric_run(run: TextRun) -> bool:
    parsed = parse_financial_number(run.normalized_text)
    return parsed.observation in {
        ObservationKind.VALUE,
        ObservationKind.ZERO,
        ObservationKind.DASH,
    }


def _cluster_numeric_runs(runs: list[TextRun], tolerance: float) -> list[NumericCluster]:
    clusters: list[list[TextRun]] = []
    for run in sorted(runs, key=lambda item: item.bbox.x1):
        target = next(
            (
                cluster
                for cluster in clusters
                if abs(run.bbox.x1 - median(item.bbox.x1 for item in cluster)) <= tolerance
            ),
            None,
        )
        if target is None:
            clusters.append([run])
        else:
            target.append(run)
    return [
        NumericCluster(
            right_edge=float(median(run.bbox.x1 for run in cluster)),
            left_edge=float(median(run.bbox.x0 for run in cluster)),
            run_ids=tuple(run.run_id for run in cluster),
            sample_count=len(cluster),
        )
        for cluster in clusters
    ]


def _deduplicate_axes(axes: list[ColumnAxis], tolerance: float) -> list[ColumnAxis]:
    result: list[ColumnAxis] = []
    for axis in sorted(axes, key=lambda item: item.right_edge):
        if result and abs(axis.right_edge - result[-1].right_edge) <= tolerance:
            previous = result[-1]
            result[-1] = ColumnAxis(
                axis_id=previous.axis_id,
                role=previous.role,
                right_edge=float(median((previous.right_edge, axis.right_edge))),
                left_edge=float(median((previous.left_edge, axis.left_edge))),
                sample_count=max(previous.sample_count, axis.sample_count),
                source=f"{previous.source}+{axis.source}",
            )
        else:
            result.append(axis)
    return result


def analyze_page_geometry(page: PDFTextPage, config: GeometryConfig) -> PageGeometry:
    if page.text_quality != "USABLE_TEXT_LAYER":
        raise ValueError(f"page {page.page} has no usable native text geometry")
    runs = build_text_runs(
        page.words,
        gap_height_factor=config.run_separation_gap_height_factor,
        financial_gap_height_factor=config.financial_token_separation_gap_height_factor,
    )
    heights = [run.height for run in runs if run.height > 0]
    median_height = float(median(heights)) if heights else 8.0
    edge_tolerance = max(
        config.minimum_edge_tolerance_points,
        page.width_points * config.edge_tolerance_ratio,
    )
    data_end_y = page.height_points * config.footer_y_ratio
    unit_runs = [
        run
        for run in runs
        if run.bbox.x0 >= page.width_points * config.note_minimum_x_ratio
        and parse_unit(run.normalized_text).canonical is not None
        and run.bbox.y1 < data_end_y
    ]
    warnings: list[str] = []
    if unit_runs:
        data_start_y = max(run.bbox.y1 for run in unit_runs) + median_height * 0.35
    else:
        data_start_y = page.height_points * 0.12
        warnings.append("unit header not found; data start uses conservative fallback")

    numeric_runs = [
        run
        for run in runs
        if data_start_y <= run.y_center < data_end_y
        and run.bbox.x1 >= page.width_points * config.note_minimum_x_ratio
        and _is_numeric_run(run)
    ]
    clusters = _cluster_numeric_runs(numeric_runs, edge_tolerance)
    value_axes: list[ColumnAxis] = [
        ColumnAxis(
            axis_id=f"value-cluster-{cluster_index}",
            role=ColumnRole.VALUE,
            right_edge=cluster.right_edge,
            left_edge=cluster.left_edge,
            sample_count=cluster.sample_count,
            source="numeric-cluster",
        )
        for cluster_index, cluster in enumerate(clusters, start=1)
        if cluster.right_edge >= page.width_points * config.value_minimum_x_ratio
        and cluster.sample_count >= config.minimum_numeric_samples
    ]
    for unit_index, unit_run in enumerate(sorted(unit_runs, key=lambda run: run.bbox.x1), start=1):
        if unit_run.bbox.x1 < page.width_points * config.value_minimum_x_ratio:
            continue
        closest = min(
            clusters,
            key=lambda cluster: abs(cluster.right_edge - unit_run.bbox.x1),
            default=None,
        )
        if closest is None or abs(closest.right_edge - unit_run.bbox.x1) > edge_tolerance * 2:
            continue
        value_axes.append(
            ColumnAxis(
                axis_id=f"value-unit-{unit_index}",
                role=ColumnRole.VALUE,
                right_edge=closest.right_edge,
                left_edge=closest.left_edge,
                sample_count=closest.sample_count,
                source=f"unit-header:{unit_run.run_id}+numeric-cluster",
            )
        )
    if not value_axes:
        raise ValueError(f"page {page.page} has no defensible value-column axes")
    value_axes = _deduplicate_axes(value_axes, edge_tolerance)
    value_axes = [
        ColumnAxis(
            axis_id=f"value-{index}",
            role=axis.role,
            right_edge=axis.right_edge,
            left_edge=axis.left_edge,
            sample_count=axis.sample_count,
            source=axis.source,
        )
        for index, axis in enumerate(value_axes, start=1)
    ]
    if not unit_runs:
        warnings.append("value axes inferred without a visible unit header")

    first_value = min(value_axes, key=lambda axis: axis.right_edge)
    note_alias_keys = tuple(retrieval_key(alias) for alias in config.note_header_aliases)
    note_header_runs = [
        run
        for run in runs
        if run.bbox.y1 < data_start_y
        and run.bbox.x0 >= page.width_points * config.note_minimum_x_ratio
        and any(
            alias in retrieval_key(run.normalized_text)
            or retrieval_key(run.normalized_text) in alias
            for alias in note_alias_keys
        )
    ]
    note_candidates = [
        cluster
        for cluster in clusters
        if page.width_points * config.note_minimum_x_ratio
        <= cluster.right_edge
        < first_value.left_edge - edge_tolerance
    ]
    note_axis: ColumnAxis | None = None
    if note_candidates:
        if note_header_runs:
            note_seed = max(run.bbox.x1 for run in note_header_runs)
            selected_note = min(
                note_candidates,
                key=lambda cluster: abs(cluster.right_edge - note_seed),
            )
            note_source = "note-header+numeric-cluster"
        else:
            selected_note = max(
                note_candidates,
                key=lambda cluster: (cluster.sample_count, cluster.right_edge),
            )
            note_source = "numeric-cluster"
        note_axis = ColumnAxis(
            axis_id="note-reference",
            role=ColumnRole.NOTE_REFERENCE,
            right_edge=selected_note.right_edge,
            left_edge=selected_note.left_edge,
            sample_count=selected_note.sample_count,
            source=note_source,
        )
    axes = ([note_axis] if note_axis else []) + value_axes
    if note_axis:
        label_right_boundary = note_axis.left_edge - edge_tolerance * 0.5
    else:
        label_right_boundary = first_value.left_edge - page.width_points * 0.06
        warnings.append("note-reference axis not observed")
    return PageGeometry(
        page=page.page,
        width_points=page.width_points,
        height_points=page.height_points,
        data_start_y=data_start_y,
        data_end_y=data_end_y,
        label_right_boundary=label_right_boundary,
        edge_tolerance=edge_tolerance,
        runs=tuple(runs),
        axes=tuple(axes),
        unit_run_ids=tuple(run.run_id for run in unit_runs),
        warnings=tuple(warnings),
    )


def nearest_axis(
    run: TextRun,
    axes: tuple[ColumnAxis, ...],
    *,
    tolerance: float,
    require_numeric: bool = True,
) -> ColumnAxis | None:
    if require_numeric and not _is_numeric_run(run):
        return None
    axis = min(axes, key=lambda candidate: abs(candidate.right_edge - run.bbox.x1), default=None)
    if axis is None or abs(axis.right_edge - run.bbox.x1) > tolerance:
        return None
    return axis
