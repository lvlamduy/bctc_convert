from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from bctc_ai.core.contracts import BoundingBox, ObservationKind, RowType
from bctc_ai.core.text import ParsedNumber, normalize_text, parse_financial_number
from bctc_ai.tables.geometry import (
    ColumnRole,
    GeometryConfig,
    PageGeometry,
    TextRun,
    nearest_axis,
)


@dataclass(frozen=True)
class GeometryCell:
    axis_id: str
    raw_text: str
    parsed: ParsedNumber
    bbox: BoundingBox
    run_id: str
    axis_distance: float


@dataclass(frozen=True)
class StatementRow:
    row_id: str
    page: int
    row_type: RowType
    label: str
    label_boxes: tuple[BoundingBox, ...]
    note_reference: str | None
    note_bbox: BoundingBox | None
    cells: tuple[GeometryCell, ...]
    y0: float
    y1: float
    indentation: float
    warnings: tuple[str, ...]


@dataclass
class _Band:
    runs: list[TextRun]
    label_runs: list[TextRun]
    note_run: TextRun | None
    cells: list[GeometryCell]

    @property
    def y0(self) -> float:
        return min(run.bbox.y0 for run in self.runs)

    @property
    def y1(self) -> float:
        return max(run.bbox.y1 for run in self.runs)

    @property
    def y_center(self) -> float:
        return float(median((run.bbox.y0 + run.bbox.y1) / 2 for run in self.runs))


def _union(boxes: list[BoundingBox]) -> BoundingBox:
    return BoundingBox(
        min(box.x0 for box in boxes),
        min(box.y0 for box in boxes),
        max(box.x1 for box in boxes),
        max(box.y1 for box in boxes),
    )


def _bands(geometry: PageGeometry, config: GeometryConfig) -> list[_Band]:
    eligible = [
        run for run in geometry.runs if geometry.data_start_y <= run.y_center < geometry.data_end_y
    ]
    heights = [run.height for run in eligible if run.height > 0]
    median_height = float(median(heights)) if heights else 8.0
    tolerance = median_height * config.band_y_tolerance_height_factor
    grouped: list[list[TextRun]] = []
    for run in sorted(eligible, key=lambda item: (item.y_center, item.bbox.x0)):
        target = next(
            (
                group
                for group in reversed(grouped)
                if abs(run.y_center - median(item.y_center for item in group)) <= tolerance
            ),
            None,
        )
        if target is None:
            grouped.append([run])
        else:
            target.append(run)

    assignment_tolerance = geometry.edge_tolerance * config.assignment_tolerance_multiplier
    result = []
    for group in grouped:
        label_runs: list[TextRun] = []
        note_run: TextRun | None = None
        cells: list[GeometryCell] = []
        for run in sorted(group, key=lambda item: item.bbox.x0):
            axis = nearest_axis(
                run,
                geometry.axes,
                tolerance=assignment_tolerance,
                require_numeric=run.bbox.x0 < geometry.label_right_boundary,
            )
            if axis is None:
                if run.bbox.x0 < geometry.label_right_boundary:
                    label_runs.append(run)
                continue
            if axis.role is ColumnRole.NOTE_REFERENCE:
                note_run = run
            else:
                cells.append(
                    GeometryCell(
                        axis_id=axis.axis_id,
                        raw_text=run.raw_text,
                        parsed=parse_financial_number(run.normalized_text),
                        bbox=run.bbox,
                        run_id=run.run_id,
                        axis_distance=round(abs(axis.right_edge - run.bbox.x1), 6),
                    )
                )
        result.append(_Band(group, label_runs, note_run, cells))
    return result


def _first_alpha_is_lower(text: str) -> bool:
    return next((character.islower() for character in text if character.isalpha()), False)


def _uppercase_ratio(text: str) -> float:
    letters = [character for character in text if character.isalpha()]
    return sum(character.isupper() for character in letters) / max(1, len(letters))


def _should_prepend(
    candidate: _Band,
    current_label_runs: list[TextRun],
    geometry: PageGeometry,
    config: GeometryConfig,
    median_height: float,
) -> bool:
    if not candidate.label_runs or candidate.cells or candidate.note_run:
        return False
    candidate_box = _union([run.bbox for run in candidate.label_runs])
    if not current_label_runs:
        return True
    current_box = _union([run.bbox for run in current_label_runs])
    vertical_gap = current_box.y0 - candidate_box.y1
    if vertical_gap > median_height * config.maximum_wrap_gap_height_factor:
        return False
    indentation_tolerance = geometry.width_points * config.indentation_tolerance_ratio
    if abs(candidate_box.x0 - current_box.x0) > indentation_tolerance:
        return False
    candidate_text = normalize_text(" ".join(run.normalized_text for run in candidate.label_runs))
    current_text = normalize_text(" ".join(run.normalized_text for run in current_label_runs))
    available_width = max(1.0, geometry.label_right_boundary - candidate_box.x0)
    occupancy = (candidate_box.x1 - candidate_box.x0) / available_width
    punctuation_continues = candidate_text.endswith((",", "/", "-", "("))
    if _uppercase_ratio(candidate_text) >= 0.75:
        return False
    return (
        _first_alpha_is_lower(current_text)
        or occupancy >= config.preceding_line_occupancy_threshold
        or punctuation_continues
    )


def reconstruct_statement_rows(
    geometry: PageGeometry,
    config: GeometryConfig,
    *,
    table_id: str | None = None,
) -> list[StatementRow]:
    bands = _bands(geometry, config)
    if not bands:
        return []
    heights = [run.height for band in bands for run in band.runs if run.height > 0]
    median_height = float(median(heights)) if heights else 8.0
    consumed: set[int] = set()
    provisional: list[tuple[float, StatementRow]] = []
    table_prefix = table_id or f"page-{geometry.page}"

    for band_index, band in enumerate(bands):
        if not band.cells:
            continue
        label_runs = list(band.label_runs)
        attached_indices: list[int] = []
        candidate_index = band_index - 1
        while candidate_index >= 0 and candidate_index not in consumed:
            candidate = bands[candidate_index]
            if any(previous.cells for previous in bands[candidate_index + 1 : band_index]):
                break
            if not _should_prepend(
                candidate,
                label_runs,
                geometry,
                config,
                median_height,
            ):
                break
            label_runs = candidate.label_runs + label_runs
            attached_indices.append(candidate_index)
            candidate_index -= 1
        consumed.update(attached_indices)
        consumed.add(band_index)
        label = normalize_text(" ".join(run.normalized_text for run in label_runs))
        warnings = []
        if not label:
            warnings.append("numeric row has no attached label")
        if len({cell.axis_id for cell in band.cells}) != len(band.cells):
            warnings.append("several numeric runs assigned to one value axis")
        if any(cell.parsed.observation is ObservationKind.INVALID for cell in band.cells):
            warnings.append("axis-aligned cell text is not a valid financial number")
        all_boxes = [run.bbox for run in label_runs] + [cell.bbox for cell in band.cells]
        if band.note_run:
            all_boxes.append(band.note_run.bbox)
        row_type = (
            RowType.TOTAL_ROW if label and _uppercase_ratio(label) >= 0.75 else RowType.DATA_ROW
        )
        provisional.append(
            (
                min(box.y0 for box in all_boxes),
                StatementRow(
                    row_id="",
                    page=geometry.page,
                    row_type=row_type,
                    label=label,
                    label_boxes=tuple(run.bbox for run in label_runs),
                    note_reference=band.note_run.normalized_text if band.note_run else None,
                    note_bbox=band.note_run.bbox if band.note_run else None,
                    cells=tuple(sorted(band.cells, key=lambda cell: cell.bbox.x0)),
                    y0=min(box.y0 for box in all_boxes),
                    y1=max(box.y1 for box in all_boxes),
                    indentation=min((run.bbox.x0 for run in label_runs), default=0.0),
                    warnings=tuple(warnings),
                ),
            )
        )

    for band_index, band in enumerate(bands):
        if band_index in consumed or not band.label_runs or band.cells:
            continue
        label = normalize_text(" ".join(run.normalized_text for run in band.label_runs))
        label_box = _union([run.bbox for run in band.label_runs])
        provisional.append(
            (
                label_box.y0,
                StatementRow(
                    row_id="",
                    page=geometry.page,
                    row_type=RowType.SECTION_HEADER,
                    label=label,
                    label_boxes=tuple(run.bbox for run in band.label_runs),
                    note_reference=band.note_run.normalized_text if band.note_run else None,
                    note_bbox=band.note_run.bbox if band.note_run else None,
                    cells=(),
                    y0=label_box.y0,
                    y1=label_box.y1,
                    indentation=label_box.x0,
                    warnings=("label-only row retained for ordered context",),
                ),
            )
        )

    rows = []
    for index, (_, row) in enumerate(sorted(provisional, key=lambda item: item[0]), start=1):
        rows.append(
            StatementRow(
                row_id=f"{table_prefix}:row-{index:04d}",
                page=row.page,
                row_type=row.row_type,
                label=row.label,
                label_boxes=row.label_boxes,
                note_reference=row.note_reference,
                note_bbox=row.note_bbox,
                cells=row.cells,
                y0=row.y0,
                y1=row.y1,
                indentation=row.indentation,
                warnings=row.warnings,
            )
        )
    return rows
