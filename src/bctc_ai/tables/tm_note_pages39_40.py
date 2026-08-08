"""Fixed-grid reconstruction for MBB Note 11 intangible assets on PDF pages 39-40."""

from __future__ import annotations

import re
import statistics
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import cv2
import yaml

from bctc_ai.core.contracts import BoundingBox, ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import normalize_text, parse_financial_number, retrieval_key
from bctc_ai.evaluation.word_box_rows import VisualCellEvidence
from bctc_ai.evaluation.word_box_rows_v3 import (
    _detect_visible_dash_v3,
    load_word_box_reconstruction_v3_config,
)
from bctc_ai.tables.tm_note_word_box import (
    TMNoteRowKind,
    TMNoteWordBoxError,
    _best_anchor_similarity,
    _Line,
    _load_lines,
    _numeric_only,
    _source_ids,
    _union,
)
from bctc_ai.validation.reader_agreement import ReaderRow

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_FORBIDDEN = {
    "missing_ocr_cell_as_dash_without_pixel_evidence",
    "template_labels_as_row_reconstruction_input",
    "approved_report_norm_id_assignment",
    "historical_or_mongodb_values",
    "human_review_answers",
    "dash_as_zero",
    "accounting_equations_as_value_imputation",
}
_EXPECTED_PAGE_DENOMINATORS = {
    39: (13, 10, 3, 40, 35, 5),
    40: (17, 14, 3, 56, 44, 12),
}


@dataclass(frozen=True)
class TMIntangibleAxisSpec:
    axis_id: str
    label_anchors: tuple[str, ...]


@dataclass(frozen=True)
class TMIntangibleRowSpec:
    row_key: str
    label_anchors: tuple[str, ...]
    row_kind: TMNoteRowKind
    source_role: str
    expected_observations: tuple[str, ...]


@dataclass(frozen=True)
class TMIntangiblePageSpec:
    page_number: int
    page_tag: str
    source_render_sha256: str
    source_ocr_sha256: str
    period_role: str
    period_start: date
    period_end: date
    period_type: str
    title_anchors: tuple[str, ...]
    expected_numeric_rows: int
    expected_label_only_rows: int
    rows: tuple[TMIntangibleRowSpec, ...]


@dataclass(frozen=True)
class TMNotePages3940Policy:
    source_path: Path
    document: str
    scope: str
    scope_binding: str
    source_pdf_sha256: str
    minimum_line_score: float
    minimum_anchor_similarity: float
    minimum_unit_similarity: float
    minimum_numeric_height_line_ratio: float
    numeric_row_attach_line_heights: float
    page_footer_top_ratio: float
    unit_anchors: tuple[str, ...]
    canonical_unit: str
    unit_multiplier: int
    axes: tuple[TMIntangibleAxisSpec, ...]
    dash_config: dict[str, float | int]
    dash_config_path: Path
    pages: tuple[TMIntangiblePageSpec, ...]
    forbidden_semantic_inputs: tuple[str, ...]


@dataclass(frozen=True)
class TMIntangibleAxisBinding:
    ordinal: int
    axis_id: str
    axis_right_edge: float
    raw_header_text: str
    raw_unit_text: str
    header_line_indices: tuple[int, ...]
    unit_line_index: int
    semantic_role: str
    canonical_unit: str
    unit_multiplier: int
    period_role: str
    period_start: date
    period_end: date
    period_type: str
    header_bbox: BoundingBox
    unit_bbox: BoundingBox
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class TMIntangibleLogicalRow:
    row_id: str
    page_tag: str
    page_number: int
    row_key: str
    ordinal: int
    note_number: str
    row: ReaderRow
    row_kind: TMNoteRowKind
    source_role: str
    period_role: str
    period_start: date
    period_end: date
    period_type: str
    y_anchor: float
    label_bbox: BoundingBox
    value_bboxes: tuple[BoundingBox | None, ...]
    label_line_indices: tuple[int, ...]
    value_line_indices: tuple[tuple[int, ...], ...]
    visual_cell_evidence: tuple[VisualCellEvidence | None, ...]
    mapping_approved: bool

    @property
    def financial_slot_count(self) -> int:
        return len(self.row.cells) if self.row_kind is TMNoteRowKind.NUMERIC else 0


@dataclass(frozen=True)
class ParsedTMIntangiblePage:
    input_path: str
    source_sha256: str
    source_render_sha256: str
    source_pdf_sha256: str
    page_tag: str
    page_number: int
    scope: str
    scope_binding: str
    period_role: str
    period_start: date
    period_end: date
    period_type: str
    title: str
    title_line_index: int
    title_bbox: BoundingBox
    axes: tuple[TMIntangibleAxisBinding, ...]
    rows: tuple[TMIntangibleLogicalRow, ...]
    line_height: float
    source_ocr_bbox: BoundingBox
    table_bbox: BoundingBox
    unassigned_numeric_line_indices: tuple[int, ...]
    excluded_artifact_numeric_line_indices: tuple[int, ...]
    excluded_footer_numeric_line_indices: tuple[int, ...]
    mapping_authority: bool
    evidence: tuple[str, ...]

    @property
    def numeric_row_count(self) -> int:
        return sum(row.row_kind is TMNoteRowKind.NUMERIC for row in self.rows)

    @property
    def label_only_row_count(self) -> int:
        return sum(row.row_kind is TMNoteRowKind.LABEL_ONLY for row in self.rows)

    @property
    def financial_slot_count(self) -> int:
        return sum(row.financial_slot_count for row in self.rows)

    def observation_count(self, observation: ObservationKind) -> int:
        return sum(
            cell.observation is observation
            for row in self.rows
            if row.row_kind is TMNoteRowKind.NUMERIC
            for cell in row.row.cells
        )


@dataclass(frozen=True)
class ParsedTMNotePages3940:
    pages: tuple[ParsedTMIntangiblePage, ...]
    rows: tuple[TMIntangibleLogicalRow, ...]
    scope: str
    source_pdf_sha256: str
    mapping_authority: bool
    evidence: tuple[str, ...]

    @property
    def numeric_row_count(self) -> int:
        return sum(page.numeric_row_count for page in self.pages)

    @property
    def label_only_row_count(self) -> int:
        return sum(page.label_only_row_count for page in self.pages)

    @property
    def financial_slot_count(self) -> int:
        return sum(page.financial_slot_count for page in self.pages)

    def observation_count(self, observation: ObservationKind) -> int:
        return sum(page.observation_count(observation) for page in self.pages)


def _anchors(payload: Any, field: str) -> tuple[str, ...]:
    if not isinstance(payload, list) or not payload:
        raise TMNoteWordBoxError(f"TM pages39-40 {field} anchors are invalid")
    anchors = tuple(retrieval_key(str(value)) for value in payload)
    if any(not anchor for anchor in anchors):
        raise TMNoteWordBoxError(f"TM pages39-40 {field} contains an empty anchor")
    return anchors


def _probability(payload: dict[str, Any], field: str) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= float(value) <= 1:
        raise TMNoteWordBoxError(f"TM pages39-40 {field} is invalid")
    return float(value)


def _positive(payload: dict[str, Any], field: str) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise TMNoteWordBoxError(f"TM pages39-40 {field} must be positive")
    return float(value)


def _date(value: Any, field: str) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise TMNoteWordBoxError(f"TM pages39-40 {field} is invalid") from exc
    raise TMNoteWordBoxError(f"TM pages39-40 {field} is invalid")


def load_tm_note_pages39_40_policy(path: Path) -> TMNotePages3940Policy:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMNoteWordBoxError(f"cannot load TM pages39-40 policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGES39_40_INTANGIBLE_FIXED_GRID_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("scope") != "CONSOLIDATED"
    ):
        raise TMNoteWordBoxError("TM pages39-40 policy identity drifted")
    source_pdf_sha256 = payload.get("source_pdf_sha256")
    if not isinstance(source_pdf_sha256, str) or not _SHA256.fullmatch(source_pdf_sha256):
        raise TMNoteWordBoxError("TM pages39-40 source PDF hash is invalid")
    unit = payload.get("unit")
    if not isinstance(unit, dict):
        raise TMNoteWordBoxError("TM pages39-40 unit policy is absent")
    multiplier = unit.get("multiplier")
    canonical_unit = unit.get("canonical")
    if (
        isinstance(multiplier, bool)
        or not isinstance(multiplier, int)
        or multiplier <= 0
        or not isinstance(canonical_unit, str)
        or not canonical_unit
    ):
        raise TMNoteWordBoxError("TM pages39-40 unit binding is invalid")
    raw_axes = payload.get("axes")
    if not isinstance(raw_axes, list) or len(raw_axes) != 4:
        raise TMNoteWordBoxError("TM pages39-40 must define four visible asset axes")
    axes = []
    for record in raw_axes:
        if not isinstance(record, dict) or not isinstance(record.get("axis_id"), str):
            raise TMNoteWordBoxError("TM pages39-40 axis record is invalid")
        axes.append(
            TMIntangibleAxisSpec(
                axis_id=record["axis_id"],
                label_anchors=_anchors(record.get("label_anchors"), "axis label"),
            )
        )
    if [axis.axis_id for axis in axes] != [
        "FINITE_LAND_USE_RIGHTS",
        "COMPUTER_SOFTWARE",
        "OTHER_INTANGIBLE_ASSETS",
        "TOTAL",
    ]:
        raise TMNoteWordBoxError("TM pages39-40 asset-axis order drifted")
    dash_name = payload.get("dash_detector_config")
    if not isinstance(dash_name, str) or Path(dash_name).name != dash_name:
        raise TMNoteWordBoxError("TM pages39-40 dash detector path is invalid")
    dash_path = (path.parent / dash_name).resolve()
    if not dash_path.is_file() or sha256_file(dash_path) != payload.get(
        "dash_detector_config_sha256"
    ):
        raise TMNoteWordBoxError("TM pages39-40 dash detector is absent or drifted")
    dash_config = load_word_box_reconstruction_v3_config(dash_path).base.base
    raw_pages = payload.get("pages")
    if not isinstance(raw_pages, list) or len(raw_pages) != 2:
        raise TMNoteWordBoxError("TM pages39-40 must define exactly two pages")
    pages = []
    for page_record in raw_pages:
        if not isinstance(page_record, dict):
            raise TMNoteWordBoxError("TM pages39-40 page record is invalid")
        page_number = page_record.get("page_number")
        page_tag = page_record.get("page_tag")
        render_hash = page_record.get("source_render_sha256")
        ocr_hash = page_record.get("source_ocr_sha256")
        numeric_rows = page_record.get("expected_numeric_rows")
        label_rows = page_record.get("expected_label_only_rows")
        if (
            page_number not in {39, 40}
            or page_tag != f"page-{page_number:04d}"
            or not isinstance(render_hash, str)
            or not _SHA256.fullmatch(render_hash)
            or not isinstance(ocr_hash, str)
            or not _SHA256.fullmatch(ocr_hash)
            or isinstance(numeric_rows, bool)
            or not isinstance(numeric_rows, int)
            or isinstance(label_rows, bool)
            or not isinstance(label_rows, int)
        ):
            raise TMNoteWordBoxError("TM pages39-40 page identity is invalid")
        raw_rows = page_record.get("rows")
        if not isinstance(raw_rows, list) or len(raw_rows) != numeric_rows + label_rows:
            raise TMNoteWordBoxError("TM pages39-40 row denominator is invalid")
        rows = []
        for row_record in raw_rows:
            if not isinstance(row_record, dict):
                raise TMNoteWordBoxError("TM pages39-40 row record is invalid")
            row_key = row_record.get("row_key")
            source_role = row_record.get("source_role")
            observations = row_record.get("expected_observations")
            try:
                row_kind = TMNoteRowKind(str(row_record.get("row_kind")))
            except ValueError as exc:
                raise TMNoteWordBoxError("TM pages39-40 row kind is invalid") from exc
            if (
                not isinstance(row_key, str)
                or not row_key
                or not isinstance(source_role, str)
                or not source_role
                or not isinstance(observations, list)
                or len(observations) != 4
                or any(value not in {"VALUE", "DASH", "BLANK"} for value in observations)
                or (row_kind is TMNoteRowKind.LABEL_ONLY and set(observations) != {"BLANK"})
                or (row_kind is TMNoteRowKind.NUMERIC and "BLANK" in observations)
            ):
                raise TMNoteWordBoxError("TM pages39-40 row specification is invalid")
            rows.append(
                TMIntangibleRowSpec(
                    row_key=row_key,
                    label_anchors=_anchors(row_record.get("label_anchors"), "row label"),
                    row_kind=row_kind,
                    source_role=source_role,
                    expected_observations=tuple(str(value) for value in observations),
                )
            )
        if len({row.row_key for row in rows}) != len(rows):
            raise TMNoteWordBoxError("TM pages39-40 row keys are duplicated within a page")
        pages.append(
            TMIntangiblePageSpec(
                page_number=page_number,
                page_tag=page_tag,
                source_render_sha256=render_hash,
                source_ocr_sha256=ocr_hash,
                period_role=str(page_record.get("period_role")),
                period_start=_date(page_record.get("period_start"), "period start"),
                period_end=_date(page_record.get("period_end"), "period end"),
                period_type=str(page_record.get("period_type")),
                title_anchors=_anchors(page_record.get("title_anchors"), "title"),
                expected_numeric_rows=numeric_rows,
                expected_label_only_rows=label_rows,
                rows=tuple(rows),
            )
        )
    if [page.page_number for page in pages] != [39, 40] or [page.period_role for page in pages] != [
        "CURRENT",
        "COMPARATIVE",
    ]:
        raise TMNoteWordBoxError("TM pages39-40 page order or period role drifted")
    forbidden = payload.get("forbidden_semantic_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMNoteWordBoxError("TM pages39-40 forbidden semantic inputs drifted")
    footer_ratio = _probability(payload, "page_footer_top_ratio")
    if footer_ratio <= 0.5:
        raise TMNoteWordBoxError("TM pages39-40 footer bound is too broad")
    return TMNotePages3940Policy(
        source_path=path,
        document=str(payload.get("document", "")),
        scope="CONSOLIDATED",
        scope_binding=str(payload.get("scope_binding", "")),
        source_pdf_sha256=source_pdf_sha256,
        minimum_line_score=_probability(payload, "minimum_line_score"),
        minimum_anchor_similarity=_probability(payload, "minimum_anchor_similarity"),
        minimum_unit_similarity=_probability(payload, "minimum_unit_similarity"),
        minimum_numeric_height_line_ratio=_positive(payload, "minimum_numeric_height_line_ratio"),
        numeric_row_attach_line_heights=_positive(payload, "numeric_row_attach_line_heights"),
        page_footer_top_ratio=footer_ratio,
        unit_anchors=_anchors(unit.get("anchors"), "unit"),
        canonical_unit=canonical_unit,
        unit_multiplier=multiplier,
        axes=tuple(axes),
        dash_config={str(key): value for key, value in dash_config.items()},
        dash_config_path=dash_path,
        pages=tuple(pages),
        forbidden_semantic_inputs=tuple(str(value) for value in forbidden),
    )


def _find_title(lines: tuple[_Line, ...], spec: TMIntangiblePageSpec, threshold: float) -> _Line:
    candidates = sorted(
        ((_best_anchor_similarity(line.text, spec.title_anchors), line) for line in lines),
        key=lambda item: (-item[0], item[1].y_center, item[1].index),
    )
    if not candidates or candidates[0][0] < threshold:
        raise TMNoteWordBoxError(f"TM {spec.page_tag} Note 11 title is unresolved")
    return candidates[0][1]


def _bind_axes(
    lines: tuple[_Line, ...],
    spec: TMIntangiblePageSpec,
    policy: TMNotePages3940Policy,
    title: _Line,
    line_height: float,
) -> tuple[TMIntangibleAxisBinding, ...]:
    units = sorted(
        (
            line
            for line in lines
            if title.y_center < line.y_center < title.y_center + line_height * 7
            and _best_anchor_similarity(line.text, policy.unit_anchors)
            >= policy.minimum_unit_similarity
        ),
        key=lambda line: line.x_right,
    )
    if len(units) != 4:
        raise TMNoteWordBoxError(f"TM {spec.page_tag} must expose four local unit axes")
    edges = [line.x_right for line in units]
    if any(right - left < line_height * 5 for left, right in zip(edges, edges[1:], strict=False)):
        raise TMNoteWordBoxError(f"TM {spec.page_tag} asset axes overlap")
    boundaries = [
        float("-inf"),
        *(statistics.fmean((left, right)) for left, right in zip(edges, edges[1:], strict=False)),
        float("inf"),
    ]
    header_candidates = [
        line
        for line in lines
        if title.y_center < line.y_center < max(unit.y_center for unit in units)
        and line.index not in {unit.index for unit in units}
        and not _numeric_only(line.text)
    ]
    result = []
    for ordinal, (axis_spec, unit) in enumerate(zip(policy.axes, units, strict=True), start=1):
        group = sorted(
            (
                line
                for line in header_candidates
                if boundaries[ordinal - 1] < line.x_center <= boundaries[ordinal]
            ),
            key=lambda line: (line.y_center, line.bbox.x0, line.index),
        )
        raw_header = normalize_text(" ".join(line.text for line in group))
        if not group or _best_anchor_similarity(raw_header, axis_spec.label_anchors) < (
            policy.minimum_anchor_similarity
        ):
            raise TMNoteWordBoxError(
                f"TM {spec.page_tag} asset header is unresolved: {axis_spec.axis_id}"
            )
        result.append(
            TMIntangibleAxisBinding(
                ordinal=ordinal,
                axis_id=f"{spec.page_tag}:asset-axis-{ordinal}",
                axis_right_edge=unit.x_right,
                raw_header_text=raw_header,
                raw_unit_text=unit.text,
                header_line_indices=tuple(line.index for line in group),
                unit_line_index=unit.index,
                semantic_role=axis_spec.axis_id,
                canonical_unit=policy.canonical_unit,
                unit_multiplier=policy.unit_multiplier,
                period_role=spec.period_role,
                period_start=spec.period_start,
                period_end=spec.period_end,
                period_type=spec.period_type,
                header_bbox=_union([*group, unit]),
                unit_bbox=unit.bbox,
                evidence=(
                    "visible Note 11 asset-class header",
                    "visible page-local Triệu đồng unit",
                    "axis right edge bound from the local unit geometry",
                ),
            )
        )
    return tuple(result)


def _select_row_labels(
    lines: tuple[_Line, ...],
    spec: TMIntangiblePageSpec,
    axes: tuple[TMIntangibleAxisBinding, ...],
    policy: TMNotePages3940Policy,
    body_start: float,
    footer_top: float,
) -> tuple[_Line, ...]:
    axis_gap = statistics.median(
        axes[index + 1].axis_right_edge - axes[index].axis_right_edge
        for index in range(len(axes) - 1)
    )
    label_right = axes[0].axis_right_edge - axis_gap * 0.35
    candidates = [
        line
        for line in lines
        if body_start < line.y_center < footer_top
        and line.x_right < label_right
        and not _numeric_only(line.text)
    ]
    selected = []
    used: set[int] = set()
    previous_y = body_start
    for row_spec in spec.rows:
        matching = [
            line
            for line in candidates
            if line.index not in used
            and line.y_center > previous_y
            and _best_anchor_similarity(line.text, row_spec.label_anchors)
            >= policy.minimum_anchor_similarity
        ]
        if not matching:
            raise TMNoteWordBoxError(
                f"TM {spec.page_tag} row label is unresolved: {row_spec.row_key}"
            )
        label = min(matching, key=lambda line: (line.y_center, line.index))
        selected.append(label)
        used.add(label.index)
        previous_y = label.y_center
    return tuple(selected)


def _parse_page(
    result_path: Path,
    source_image_path: Path,
    spec: TMIntangiblePageSpec,
    policy: TMNotePages3940Policy,
) -> ParsedTMIntangiblePage:
    if sha256_file(result_path) != spec.source_ocr_sha256:
        raise TMNoteWordBoxError(f"TM {spec.page_tag} OCR artifact hash drifted")
    if sha256_file(source_image_path) != spec.source_render_sha256:
        raise TMNoteWordBoxError(f"TM {spec.page_tag} source render hash drifted")
    source_image = cv2.imread(str(source_image_path), cv2.IMREAD_GRAYSCALE)
    if source_image is None:
        raise TMNoteWordBoxError(f"TM {spec.page_tag} render cannot be decoded")
    input_path, lines, _metadata = _load_lines(result_path, policy.minimum_line_score)
    line_height = float(statistics.median(line.height for line in lines))
    if line_height <= 0:
        raise TMNoteWordBoxError(f"TM {spec.page_tag} line height is invalid")
    source_bbox = _union(lines)
    title = _find_title(lines, spec, policy.minimum_anchor_similarity)
    axes = _bind_axes(lines, spec, policy, title, line_height)
    body_start = max(axis.unit_bbox.y1 for axis in axes)
    footer_top = source_bbox.y1 * policy.page_footer_top_ratio
    labels = _select_row_labels(lines, spec, axes, policy, body_start, footer_top)
    body_end = labels[-1].y_center + line_height * policy.numeric_row_attach_line_heights
    minimum_numeric_height = line_height * policy.minimum_numeric_height_line_ratio
    numeric_in_body = [
        line for line in lines if body_start < line.y_center < body_end and _numeric_only(line.text)
    ]
    artifact_numeric = tuple(
        sorted(line.index for line in numeric_in_body if line.height < minimum_numeric_height)
    )
    eligible_numeric = [line for line in numeric_in_body if line.height >= minimum_numeric_height]
    numeric_groups: list[list[_Line]] = []
    for line in sorted(
        eligible_numeric, key=lambda item: (item.y_center, item.x_right, item.index)
    ):
        if (
            not numeric_groups
            or line.y_center - statistics.fmean(item.y_center for item in numeric_groups[-1])
            > line_height * 0.45
        ):
            numeric_groups.append([line])
        else:
            numeric_groups[-1].append(line)
    if len(numeric_groups) != spec.expected_numeric_rows:
        raise TMNoteWordBoxError(
            f"TM {spec.page_tag} numeric-row geometry drifted: {len(numeric_groups)} groups"
        )
    axis_gap = statistics.median(
        axes[index + 1].axis_right_edge - axes[index].axis_right_edge
        for index in range(len(axes) - 1)
    )
    used_numeric: set[int] = set()
    rows = []
    numeric_group_index = 0
    for ordinal, (row_spec, label) in enumerate(zip(spec.rows, labels, strict=True), start=1):
        if row_spec.row_kind is TMNoteRowKind.LABEL_ONLY:
            cells = tuple(parse_financial_number(None) for _axis in axes)
            rows.append(
                TMIntangibleLogicalRow(
                    row_id=f"{spec.page_tag}:intangible:row-{ordinal:04d}",
                    page_tag=spec.page_tag,
                    page_number=spec.page_number,
                    row_key=row_spec.row_key,
                    ordinal=ordinal,
                    note_number="11",
                    row=ReaderRow(
                        source_row_ids=_source_ids(spec.page_tag, [label]),
                        label=label.text,
                        note_reference="11",
                        cells=cells,
                    ),
                    row_kind=TMNoteRowKind.LABEL_ONLY,
                    source_role=row_spec.source_role,
                    period_role=spec.period_role,
                    period_start=spec.period_start,
                    period_end=spec.period_end,
                    period_type=spec.period_type,
                    y_anchor=label.y_center,
                    label_bbox=label.bbox,
                    value_bboxes=tuple(None for _axis in axes),
                    label_line_indices=(label.index,),
                    value_line_indices=tuple(() for _axis in axes),
                    visual_cell_evidence=tuple(None for _axis in axes),
                    mapping_approved=False,
                )
            )
            continue
        group = numeric_groups[numeric_group_index]
        numeric_group_index += 1
        group_center = float(statistics.median(line.y_center for line in group))
        if (
            abs(group_center - label.y_center)
            > line_height * policy.numeric_row_attach_line_heights
        ):
            raise TMNoteWordBoxError(
                f"TM {spec.page_tag} label/value geometry drifted: {row_spec.row_key}"
            )
        per_axis: list[list[_Line]] = [[] for _axis in axes]
        for line in group:
            distances = [abs(line.x_right - axis.axis_right_edge) for axis in axes]
            closest = min(range(len(axes)), key=distances.__getitem__)
            if distances[closest] > axis_gap * 0.35 or per_axis[closest]:
                raise TMNoteWordBoxError(
                    f"TM {spec.page_tag} numeric axis is ambiguous: {row_spec.row_key}"
                )
            per_axis[closest].append(line)
        selected_numeric = [line for group in per_axis for line in group]
        if not selected_numeric:
            raise TMNoteWordBoxError(f"TM {spec.page_tag} numeric row is empty: {row_spec.row_key}")
        row_center = group_center
        cells = []
        value_bboxes = []
        visual = []
        for axis, group in zip(axes, per_axis, strict=True):
            evidence = None
            if not group:
                evidence = _detect_visible_dash_v3(
                    source_image,
                    source_image_path=source_image_path,
                    axis_right_edge=axis.axis_right_edge,
                    anchor_center=row_center,
                    line_height=line_height,
                    config=policy.dash_config,
                )
                if evidence is None:
                    raise TMNoteWordBoxError(
                        f"TM {spec.page_tag} missing cell lacks dash pixels: {row_spec.row_key}"
                    )
                cells.append(parse_financial_number("-"))
                value_bboxes.append(BoundingBox(*evidence.component_box))
            else:
                used_numeric.add(group[0].index)
                cells.append(parse_financial_number(group[0].text))
                value_bboxes.append(group[0].bbox)
            visual.append(evidence)
        observations = tuple(cell.observation.value for cell in cells)
        if observations != row_spec.expected_observations:
            raise TMNoteWordBoxError(
                f"TM {spec.page_tag} observation pattern drifted for {row_spec.row_key}: "
                f"{observations}"
            )
        source_lines = [label, *selected_numeric]
        rows.append(
            TMIntangibleLogicalRow(
                row_id=f"{spec.page_tag}:intangible:row-{ordinal:04d}",
                page_tag=spec.page_tag,
                page_number=spec.page_number,
                row_key=row_spec.row_key,
                ordinal=ordinal,
                note_number="11",
                row=ReaderRow(
                    source_row_ids=_source_ids(spec.page_tag, source_lines),
                    label=label.text,
                    note_reference="11",
                    cells=tuple(cells),
                ),
                row_kind=TMNoteRowKind.NUMERIC,
                source_role=row_spec.source_role,
                period_role=spec.period_role,
                period_start=spec.period_start,
                period_end=spec.period_end,
                period_type=spec.period_type,
                y_anchor=row_center,
                label_bbox=label.bbox,
                value_bboxes=tuple(value_bboxes),
                label_line_indices=(label.index,),
                value_line_indices=tuple(tuple(line.index for line in group) for group in per_axis),
                visual_cell_evidence=tuple(visual),
                mapping_approved=False,
            )
        )
    unassigned = tuple(
        sorted(line.index for line in eligible_numeric if line.index not in used_numeric)
    )
    footer = tuple(
        sorted(
            line.index for line in lines if line.y_center >= footer_top and _numeric_only(line.text)
        )
    )
    table_lines = [title]
    table_lines.extend(
        line
        for axis in axes
        for line in lines
        if line.index in {*axis.header_line_indices, axis.unit_line_index}
    )
    used_indices = {
        int(source_id.rsplit("-", 1)[-1]) for row in rows for source_id in row.row.source_row_ids
    }
    table_lines.extend(line for line in lines if line.index in used_indices)
    result = ParsedTMIntangiblePage(
        input_path=input_path,
        source_sha256=spec.source_ocr_sha256,
        source_render_sha256=spec.source_render_sha256,
        source_pdf_sha256=policy.source_pdf_sha256,
        page_tag=spec.page_tag,
        page_number=spec.page_number,
        scope=policy.scope,
        scope_binding=policy.scope_binding,
        period_role=spec.period_role,
        period_start=spec.period_start,
        period_end=spec.period_end,
        period_type=spec.period_type,
        title=title.text,
        title_line_index=title.index,
        title_bbox=title.bbox,
        axes=axes,
        rows=tuple(rows),
        line_height=line_height,
        source_ocr_bbox=source_bbox,
        table_bbox=_union(table_lines),
        unassigned_numeric_line_indices=unassigned,
        excluded_artifact_numeric_line_indices=artifact_numeric,
        excluded_footer_numeric_line_indices=footer,
        mapping_authority=False,
        evidence=(
            "visible Note 11 title and four page-local asset-class headers",
            "numeric cells reconstructed from PP-OCRv6 word-box geometry",
            "OCR-missing dashes accepted only with constrained render-pixel evidence",
            "dash observations remain distinct from numeric zero",
            "this parser grants no ReportNormId authority",
        ),
    )
    denominator = (
        len(result.rows),
        result.numeric_row_count,
        result.label_only_row_count,
        result.financial_slot_count,
        result.observation_count(ObservationKind.VALUE),
        result.observation_count(ObservationKind.DASH),
    )
    if denominator != _EXPECTED_PAGE_DENOMINATORS[spec.page_number] or unassigned:
        raise TMNoteWordBoxError(
            f"TM {spec.page_tag} source denominator drifted: {denominator}, unassigned={unassigned}"
        )
    if any(
        cell.observation is ObservationKind.DASH and (cell.value is not None or evidence is None)
        for row in result.rows
        for cell, evidence in zip(row.row.cells, row.visual_cell_evidence, strict=True)
    ):
        raise TMNoteWordBoxError(f"TM {spec.page_tag} dash provenance drifted")
    return result


def parse_tm_note_pages39_40(
    inputs: Mapping[int, tuple[Path, Path]], policy: TMNotePages3940Policy
) -> ParsedTMNotePages3940:
    if set(inputs) != {39, 40}:
        raise TMNoteWordBoxError("TM pages39-40 inputs must contain exactly pages 39 and 40")
    pages = tuple(
        _parse_page(inputs[spec.page_number][0], inputs[spec.page_number][1], spec, policy)
        for spec in policy.pages
    )
    rows = tuple(row for page in pages for row in page.rows)
    result = ParsedTMNotePages3940(
        pages=pages,
        rows=rows,
        scope=policy.scope,
        source_pdf_sha256=policy.source_pdf_sha256,
        mapping_authority=False,
        evidence=(
            "two independently hashed PDF renders and PP-OCRv6 word-box fixtures",
            "Q1 2026 and FY2025 Note 11 panels remain separate period observations",
            "source denominator is 30 logical rows and 96 numeric/status slots",
        ),
    )
    if (
        len(result.rows) != 30
        or result.numeric_row_count != 24
        or result.label_only_row_count != 6
        or result.financial_slot_count != 96
        or result.observation_count(ObservationKind.VALUE) != 79
        or result.observation_count(ObservationKind.DASH) != 17
    ):
        raise TMNoteWordBoxError("TM pages39-40 combined denominator drifted")
    return result


__all__ = [
    "ParsedTMIntangiblePage",
    "ParsedTMNotePages3940",
    "TMIntangibleAxisBinding",
    "TMIntangibleLogicalRow",
    "TMIntangiblePageSpec",
    "TMIntangibleRowSpec",
    "TMNotePages3940Policy",
    "load_tm_note_pages39_40_policy",
    "parse_tm_note_pages39_40",
]
