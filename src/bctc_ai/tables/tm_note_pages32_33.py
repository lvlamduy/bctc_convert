"""Mixed amount/percentage loan-analysis reconstruction for MBB TM pages 32-33."""

from __future__ import annotations

import re
import statistics
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from rapidfuzz.fuzz import ratio

from bctc_ai.core.contracts import BoundingBox, ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import (
    normalize_text,
    parse_financial_number,
    parse_vietnamese_date,
    retrieval_key,
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
    "template_labels_as_row_reconstruction_input",
    "approved_report_norm_id_assignment",
    "historical_or_mongodb_values",
    "human_review_answers",
    "amount_percentage_equation_as_value_imputation",
    "percentage_axis_as_amount_axis",
}
_EXPECTED_DENOMINATORS = {
    32: (22, 21, 1, 84),
    33: (24, 23, 1, 92),
}


@dataclass(frozen=True)
class TMLoanAnalysisAxisSpec:
    axis_id: str
    measure_role: str
    period_role: str
    period_end: date
    unit_anchors: tuple[str, ...]
    canonical_unit: str
    unit_multiplier: int


@dataclass(frozen=True)
class TMLoanAnalysisRowSpec:
    row_key: str
    row_kind: TMNoteRowKind
    source_role: str
    label_anchors: tuple[str, ...]


@dataclass(frozen=True)
class TMLoanAnalysisPageSpec:
    page_number: int
    page_tag: str
    source_render_sha256: str
    source_ocr_sha256: str
    title_anchors: tuple[str, ...]
    expected_numeric_rows: int
    expected_label_only_rows: int
    rows: tuple[TMLoanAnalysisRowSpec, ...]


@dataclass(frozen=True)
class TMNotePages3233Policy:
    source_path: Path
    document: str
    scope: str
    scope_binding: str
    source_pdf_sha256: str
    minimum_line_score: float
    minimum_anchor_similarity: float
    minimum_header_similarity: float
    minimum_numeric_height_line_ratio: float
    numeric_cluster_line_heights: float
    label_group_final_attach_line_heights: float
    maximum_label_lines: int
    page_footer_top_ratio: float
    axes: tuple[TMLoanAnalysisAxisSpec, ...]
    pages: tuple[TMLoanAnalysisPageSpec, ...]
    forbidden_semantic_inputs: tuple[str, ...]


@dataclass(frozen=True)
class TMLoanAnalysisAxisBinding:
    ordinal: int
    axis_id: str
    axis_right_edge: float
    raw_period_text: str
    raw_unit_text: str
    period_line_index: int
    unit_line_index: int
    measure_role: str
    period_role: str
    period_end: date
    period_type: str
    canonical_unit: str
    unit_multiplier: int
    header_bbox: BoundingBox
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class TMLoanAnalysisLogicalRow:
    row_id: str
    page_tag: str
    page_number: int
    row_key: str
    ordinal: int
    note_number: str
    row: ReaderRow
    row_kind: TMNoteRowKind
    source_role: str
    y_anchor: float
    label_bbox: BoundingBox | None
    value_bboxes: tuple[BoundingBox | None, ...]
    label_line_indices: tuple[int, ...]
    value_line_indices: tuple[tuple[int, ...], ...]
    mapping_approved: bool

    @property
    def financial_slot_count(self) -> int:
        return len(self.row.cells) if self.row_kind is TMNoteRowKind.NUMERIC else 0


@dataclass(frozen=True)
class ParsedTMLoanAnalysisPage:
    input_path: str
    source_sha256: str
    source_render_sha256: str
    source_pdf_sha256: str
    page_tag: str
    page_number: int
    scope: str
    scope_binding: str
    title: str
    title_line_index: int
    axes: tuple[TMLoanAnalysisAxisBinding, ...]
    rows: tuple[TMLoanAnalysisLogicalRow, ...]
    line_height: float
    source_ocr_bbox: BoundingBox
    table_bbox: BoundingBox
    unassigned_numeric_line_indices: tuple[int, ...]
    unassigned_label_line_indices: tuple[int, ...]
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
class ParsedTMNotePages3233:
    pages: tuple[ParsedTMLoanAnalysisPage, ...]
    rows: tuple[TMLoanAnalysisLogicalRow, ...]
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


def _anchors(payload: Any, field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(payload, list) or (not payload and not allow_empty):
        raise TMNoteWordBoxError(f"TM pages32-33 {field} anchors are invalid")
    anchors = tuple(retrieval_key(str(value)) for value in payload)
    if any(not anchor for anchor in anchors):
        raise TMNoteWordBoxError(f"TM pages32-33 {field} contains an empty anchor")
    return anchors


def _probability(payload: dict[str, Any], field: str) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= float(value) <= 1:
        raise TMNoteWordBoxError(f"TM pages32-33 {field} is invalid")
    return float(value)


def _positive(payload: dict[str, Any], field: str) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise TMNoteWordBoxError(f"TM pages32-33 {field} must be positive")
    return float(value)


def _date(value: Any, field: str) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise TMNoteWordBoxError(f"TM pages32-33 {field} is invalid") from exc
    raise TMNoteWordBoxError(f"TM pages32-33 {field} is invalid")


def load_tm_note_pages32_33_policy(path: Path) -> TMNotePages3233Policy:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMNoteWordBoxError(f"cannot load TM pages32-33 policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGES32_33_LOAN_ANALYSIS_GRID_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("scope") != "CONSOLIDATED"
    ):
        raise TMNoteWordBoxError("TM pages32-33 policy identity drifted")
    source_pdf_sha256 = payload.get("source_pdf_sha256")
    if not isinstance(source_pdf_sha256, str) or not _SHA256.fullmatch(source_pdf_sha256):
        raise TMNoteWordBoxError("TM pages32-33 source PDF hash is invalid")
    raw_axes = payload.get("axes")
    if not isinstance(raw_axes, list) or len(raw_axes) != 4:
        raise TMNoteWordBoxError("TM pages32-33 must define four amount/percentage axes")
    axes = []
    for record in raw_axes:
        if not isinstance(record, dict):
            raise TMNoteWordBoxError("TM pages32-33 axis record is invalid")
        axis_id = record.get("axis_id")
        measure_role = record.get("measure_role")
        period_role = record.get("period_role")
        canonical_unit = record.get("canonical_unit")
        multiplier = record.get("unit_multiplier")
        raw_unit_anchors = record.get("unit_anchors")
        if (
            not isinstance(axis_id, str)
            or measure_role not in {"AMOUNT", "PERCENTAGE"}
            or period_role not in {"CURRENT", "COMPARATIVE"}
            or canonical_unit not in {"VND", "PERCENT"}
            or isinstance(multiplier, bool)
            or not isinstance(multiplier, int)
            or multiplier <= 0
            or not isinstance(raw_unit_anchors, list)
            or not raw_unit_anchors
        ):
            raise TMNoteWordBoxError("TM pages32-33 axis binding is invalid")
        unit_anchors = tuple(normalize_text(str(value)) for value in raw_unit_anchors)
        axes.append(
            TMLoanAnalysisAxisSpec(
                axis_id=axis_id,
                measure_role=measure_role,
                period_role=period_role,
                period_end=_date(record.get("period_end"), "axis period end"),
                unit_anchors=unit_anchors,
                canonical_unit=canonical_unit,
                unit_multiplier=multiplier,
            )
        )
    if [(axis.measure_role, axis.period_role) for axis in axes] != [
        ("AMOUNT", "CURRENT"),
        ("PERCENTAGE", "CURRENT"),
        ("AMOUNT", "COMPARATIVE"),
        ("PERCENTAGE", "COMPARATIVE"),
    ]:
        raise TMNoteWordBoxError("TM pages32-33 axis order drifted")
    raw_pages = payload.get("pages")
    if not isinstance(raw_pages, list) or len(raw_pages) != 2:
        raise TMNoteWordBoxError("TM pages32-33 must define exactly two pages")
    pages = []
    for record in raw_pages:
        if not isinstance(record, dict):
            raise TMNoteWordBoxError("TM pages32-33 page record is invalid")
        page_number = record.get("page_number")
        page_tag = record.get("page_tag")
        render_hash = record.get("source_render_sha256")
        ocr_hash = record.get("source_ocr_sha256")
        numeric_rows = record.get("expected_numeric_rows")
        label_rows = record.get("expected_label_only_rows")
        if (
            page_number not in {32, 33}
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
            raise TMNoteWordBoxError("TM pages32-33 page identity is invalid")
        raw_rows = record.get("rows")
        if not isinstance(raw_rows, list) or len(raw_rows) != numeric_rows + label_rows:
            raise TMNoteWordBoxError("TM pages32-33 row denominator is invalid")
        rows = []
        for row_record in raw_rows:
            if not isinstance(row_record, dict):
                raise TMNoteWordBoxError("TM pages32-33 row record is invalid")
            try:
                row_kind = TMNoteRowKind(str(row_record.get("row_kind")))
            except ValueError as exc:
                raise TMNoteWordBoxError("TM pages32-33 row kind is invalid") from exc
            row_key = row_record.get("row_key")
            source_role = row_record.get("source_role")
            if not isinstance(row_key, str) or not row_key or not isinstance(source_role, str):
                raise TMNoteWordBoxError("TM pages32-33 row identity is invalid")
            rows.append(
                TMLoanAnalysisRowSpec(
                    row_key=row_key,
                    row_kind=row_kind,
                    source_role=source_role,
                    label_anchors=_anchors(
                        row_record.get("label_anchors"), "row label", allow_empty=True
                    ),
                )
            )
        if len({row.row_key for row in rows}) != len(rows):
            raise TMNoteWordBoxError("TM pages32-33 row keys are duplicated")
        pages.append(
            TMLoanAnalysisPageSpec(
                page_number=page_number,
                page_tag=page_tag,
                source_render_sha256=render_hash,
                source_ocr_sha256=ocr_hash,
                title_anchors=_anchors(record.get("title_anchors"), "title"),
                expected_numeric_rows=numeric_rows,
                expected_label_only_rows=label_rows,
                rows=tuple(rows),
            )
        )
    if [page.page_number for page in pages] != [32, 33]:
        raise TMNoteWordBoxError("TM pages32-33 page order drifted")
    forbidden = payload.get("forbidden_semantic_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMNoteWordBoxError("TM pages32-33 forbidden semantic inputs drifted")
    maximum_label_lines = payload.get("maximum_label_lines")
    if (
        isinstance(maximum_label_lines, bool)
        or not isinstance(maximum_label_lines, int)
        or maximum_label_lines < 1
    ):
        raise TMNoteWordBoxError("TM pages32-33 maximum label lines is invalid")
    footer_ratio = _probability(payload, "page_footer_top_ratio")
    if footer_ratio < 0.75:
        raise TMNoteWordBoxError("TM pages32-33 footer bound is too broad")
    return TMNotePages3233Policy(
        source_path=path,
        document=str(payload.get("document", "")),
        scope="CONSOLIDATED",
        scope_binding=str(payload.get("scope_binding", "")),
        source_pdf_sha256=source_pdf_sha256,
        minimum_line_score=_probability(payload, "minimum_line_score"),
        minimum_anchor_similarity=_probability(payload, "minimum_anchor_similarity"),
        minimum_header_similarity=_probability(payload, "minimum_header_similarity"),
        minimum_numeric_height_line_ratio=_positive(payload, "minimum_numeric_height_line_ratio"),
        numeric_cluster_line_heights=_positive(payload, "numeric_cluster_line_heights"),
        label_group_final_attach_line_heights=_positive(
            payload, "label_group_final_attach_line_heights"
        ),
        maximum_label_lines=maximum_label_lines,
        page_footer_top_ratio=footer_ratio,
        axes=tuple(axes),
        pages=tuple(pages),
        forbidden_semantic_inputs=tuple(str(value) for value in forbidden),
    )


def _find_title(lines: tuple[_Line, ...], spec: TMLoanAnalysisPageSpec, threshold: float) -> _Line:
    candidates = sorted(
        ((_best_anchor_similarity(line.text, spec.title_anchors), line) for line in lines),
        key=lambda item: (-item[0], item[1].y_center, item[1].index),
    )
    if not candidates or candidates[0][0] < threshold:
        raise TMNoteWordBoxError(f"TM {spec.page_tag} loan-analysis title is unresolved")
    return candidates[0][1]


def _unit_matches(line: _Line, spec: TMLoanAnalysisAxisSpec, threshold: float) -> bool:
    if spec.measure_role == "PERCENTAGE":
        return line.text.strip() == "%"
    anchors = tuple(retrieval_key(value) for value in spec.unit_anchors)
    return _best_anchor_similarity(line.text, anchors) >= threshold


def _bind_axes(
    lines: tuple[_Line, ...],
    page_spec: TMLoanAnalysisPageSpec,
    policy: TMNotePages3233Policy,
    title: _Line,
    line_height: float,
) -> tuple[TMLoanAnalysisAxisBinding, ...]:
    header_lines = [
        line for line in lines if title.y_center < line.y_center < title.y_center + line_height * 6
    ]
    unit_lines = sorted(
        (
            line
            for line in header_lines
            if line.text.strip() == "%"
            or _best_anchor_similarity(line.text, ("trieu dong",))
            >= policy.minimum_header_similarity
        ),
        key=lambda line: line.x_right,
    )
    if len(unit_lines) != 4:
        raise TMNoteWordBoxError(f"TM {page_spec.page_tag} must expose four mixed-unit axes")
    date_lines = sorted(
        (line for line in header_lines if parse_vietnamese_date(line.text) is not None),
        key=lambda line: line.x_center,
    )
    if len(date_lines) != 2:
        raise TMNoteWordBoxError(f"TM {page_spec.page_tag} must expose two snapshot dates")
    result = []
    for ordinal, (axis_spec, unit_line) in enumerate(
        zip(policy.axes, unit_lines, strict=True), start=1
    ):
        if not _unit_matches(unit_line, axis_spec, policy.minimum_header_similarity):
            raise TMNoteWordBoxError(f"TM {page_spec.page_tag} mixed-unit axis order drifted")
        matching_dates = [
            line for line in date_lines if parse_vietnamese_date(line.text) == axis_spec.period_end
        ]
        if len(matching_dates) != 1:
            raise TMNoteWordBoxError(f"TM {page_spec.page_tag} axis date is unresolved")
        date_line = matching_dates[0]
        parsed_date = parse_vietnamese_date(date_line.text)
        if parsed_date != axis_spec.period_end:
            raise TMNoteWordBoxError(f"TM {page_spec.page_tag} axis date drifted")
        result.append(
            TMLoanAnalysisAxisBinding(
                ordinal=ordinal,
                axis_id=f"{page_spec.page_tag}:loan-axis-{ordinal}",
                axis_right_edge=unit_line.x_right,
                raw_period_text=date_line.text,
                raw_unit_text=unit_line.text,
                period_line_index=date_line.index,
                unit_line_index=unit_line.index,
                measure_role=axis_spec.measure_role,
                period_role=axis_spec.period_role,
                period_end=axis_spec.period_end,
                period_type="SNAPSHOT",
                canonical_unit=axis_spec.canonical_unit,
                unit_multiplier=axis_spec.unit_multiplier,
                header_bbox=_union((date_line, unit_line)),
                evidence=(
                    "visible page-local snapshot date",
                    "visible amount or percentage unit",
                    "axis right edge inferred from local header geometry",
                ),
            )
        )
    if any(
        right.axis_right_edge <= left.axis_right_edge
        for left, right in zip(result, result[1:], strict=False)
    ):
        raise TMNoteWordBoxError(f"TM {page_spec.page_tag} axis geometry overlaps")
    return tuple(result)


def _label_similarity(text: str, anchors: tuple[str, ...]) -> float:
    key = retrieval_key(text)
    return max((ratio(key, anchor) / 100 for anchor in anchors), default=0.0)


def _select_label_group(
    label_lines: list[_Line],
    *,
    anchors: tuple[str, ...],
    target_y: float,
    used: set[int],
    minimum_y: float,
    line_height: float,
    policy: TMNotePages3233Policy,
) -> tuple[_Line, ...]:
    available = [
        line
        for line in label_lines
        if line.index not in used
        and line.y_center > minimum_y
        and line.y_center <= target_y + line_height * policy.label_group_final_attach_line_heights
    ]
    proposals = []
    for end in range(len(available)):
        if (
            abs(available[end].y_center - target_y)
            > line_height * policy.label_group_final_attach_line_heights
        ):
            continue
        for length in range(1, min(policy.maximum_label_lines, end + 1) + 1):
            group = available[end - length + 1 : end + 1]
            if any(
                later.y_center - earlier.y_center > line_height * 1.15
                for earlier, later in zip(group, group[1:], strict=False)
            ):
                continue
            text = normalize_text(" ".join(line.text for line in group))
            proposals.append(
                (
                    _label_similarity(text, anchors),
                    abs(group[-1].y_center - target_y),
                    -len(group),
                    group,
                )
            )
    if not proposals:
        raise TMNoteWordBoxError("TM pages32-33 visible label group is unresolved")
    score, _distance, _negative_length, group = max(
        proposals, key=lambda item: (item[0], -item[1], -item[2])
    )
    if score < policy.minimum_anchor_similarity:
        raise TMNoteWordBoxError(f"TM pages32-33 label similarity is insufficient: {score:.3f}")
    return tuple(group)


def _parse_page(
    result_path: Path,
    source_image_path: Path,
    page_spec: TMLoanAnalysisPageSpec,
    policy: TMNotePages3233Policy,
) -> ParsedTMLoanAnalysisPage:
    if sha256_file(result_path) != page_spec.source_ocr_sha256:
        raise TMNoteWordBoxError(f"TM {page_spec.page_tag} OCR artifact hash drifted")
    if sha256_file(source_image_path) != page_spec.source_render_sha256:
        raise TMNoteWordBoxError(f"TM {page_spec.page_tag} source render hash drifted")
    input_path, lines, _metadata = _load_lines(result_path, policy.minimum_line_score)
    line_height = float(statistics.median(line.height for line in lines))
    if line_height <= 0:
        raise TMNoteWordBoxError(f"TM {page_spec.page_tag} line height is invalid")
    source_bbox = _union(lines)
    footer_top = source_bbox.y1 * policy.page_footer_top_ratio
    title = _find_title(lines, page_spec, policy.minimum_anchor_similarity)
    axes = _bind_axes(lines, page_spec, policy, title, line_height)
    body_start = max(axis.header_bbox.y1 for axis in axes)
    minimum_numeric_height = line_height * policy.minimum_numeric_height_line_ratio
    numeric_in_body = [
        line
        for line in lines
        if body_start < line.y_center < footer_top and _numeric_only(line.text)
    ]
    artifact_numeric = tuple(
        sorted(line.index for line in numeric_in_body if line.height < minimum_numeric_height)
    )
    numeric = [line for line in numeric_in_body if line.height >= minimum_numeric_height]
    numeric_groups: list[list[_Line]] = []
    for line in sorted(numeric, key=lambda item: (item.y_center, item.x_right, item.index)):
        if (
            not numeric_groups
            or line.y_center - statistics.fmean(item.y_center for item in numeric_groups[-1])
            > line_height * policy.numeric_cluster_line_heights
        ):
            numeric_groups.append([line])
        else:
            numeric_groups[-1].append(line)
    if len(numeric_groups) != page_spec.expected_numeric_rows or any(
        len(group) != 4 for group in numeric_groups
    ):
        raise TMNoteWordBoxError(
            f"TM {page_spec.page_tag} numeric grid drifted: "
            f"{len(numeric_groups)} groups / {[len(group) for group in numeric_groups]}"
        )
    axis_gap = min(
        right.axis_right_edge - left.axis_right_edge
        for left, right in zip(axes, axes[1:], strict=False)
    )
    per_group_axes = []
    for group in numeric_groups:
        per_axis: list[list[_Line]] = [[] for _axis in axes]
        for line in group:
            distances = [abs(line.x_right - axis.axis_right_edge) for axis in axes]
            closest = min(range(len(axes)), key=distances.__getitem__)
            if distances[closest] > axis_gap * 0.45 or per_axis[closest]:
                raise TMNoteWordBoxError(f"TM {page_spec.page_tag} numeric axis is ambiguous")
            per_axis[closest].append(line)
        if any(len(group) != 1 for group in per_axis):
            raise TMNoteWordBoxError(f"TM {page_spec.page_tag} numeric row is incomplete")
        per_group_axes.append(per_axis)
    label_right = axes[0].axis_right_edge - axis_gap * 0.35
    label_lines = sorted(
        (
            line
            for line in lines
            if body_start < line.y_center < footer_top
            and line.x_right < label_right
            and not _numeric_only(line.text)
        ),
        key=lambda line: (line.y_center, line.bbox.x0, line.index),
    )
    used_labels: set[int] = set()
    used_numeric: set[int] = set()
    rows = []
    numeric_index = 0
    minimum_label_y = body_start
    for ordinal, row_spec in enumerate(page_spec.rows, start=1):
        if row_spec.row_kind is TMNoteRowKind.LABEL_ONLY:
            target_y = statistics.fmean(line.y_center for line in numeric_groups[0])
            labels = _select_label_group(
                label_lines,
                anchors=row_spec.label_anchors,
                target_y=target_y,
                used=used_labels,
                minimum_y=minimum_label_y,
                line_height=line_height,
                policy=policy,
            )
            used_labels.update(line.index for line in labels)
            minimum_label_y = labels[-1].y_center
            cells = tuple(parse_financial_number(None) for _axis in axes)
            rows.append(
                TMLoanAnalysisLogicalRow(
                    row_id=f"{page_spec.page_tag}:loan-analysis:row-{ordinal:04d}",
                    page_tag=page_spec.page_tag,
                    page_number=page_spec.page_number,
                    row_key=row_spec.row_key,
                    ordinal=ordinal,
                    note_number="5",
                    row=ReaderRow(
                        source_row_ids=_source_ids(page_spec.page_tag, list(labels)),
                        label=normalize_text(" ".join(line.text for line in labels)),
                        note_reference="5",
                        cells=cells,
                    ),
                    row_kind=TMNoteRowKind.LABEL_ONLY,
                    source_role=row_spec.source_role,
                    y_anchor=statistics.fmean(line.y_center for line in labels),
                    label_bbox=_union(labels),
                    value_bboxes=tuple(None for _axis in axes),
                    label_line_indices=tuple(line.index for line in labels),
                    value_line_indices=tuple(() for _axis in axes),
                    mapping_approved=False,
                )
            )
            continue
        group = numeric_groups[numeric_index]
        per_axis = per_group_axes[numeric_index]
        numeric_index += 1
        row_center = float(statistics.median(line.y_center for line in group))
        labels: tuple[_Line, ...] = ()
        if row_spec.label_anchors:
            labels = _select_label_group(
                label_lines,
                anchors=row_spec.label_anchors,
                target_y=row_center,
                used=used_labels,
                minimum_y=minimum_label_y,
                line_height=line_height,
                policy=policy,
            )
            used_labels.update(line.index for line in labels)
            minimum_label_y = labels[-1].y_center
        cells = tuple(parse_financial_number(axis_lines[0].text) for axis_lines in per_axis)
        if any(
            cell.observation not in {ObservationKind.VALUE, ObservationKind.ZERO} for cell in cells
        ):
            raise TMNoteWordBoxError(f"TM {page_spec.page_tag} has a non-finite table cell")
        source_lines = [*labels, *group]
        used_numeric.update(line.index for line in group)
        rows.append(
            TMLoanAnalysisLogicalRow(
                row_id=f"{page_spec.page_tag}:loan-analysis:row-{ordinal:04d}",
                page_tag=page_spec.page_tag,
                page_number=page_spec.page_number,
                row_key=row_spec.row_key,
                ordinal=ordinal,
                note_number="5",
                row=ReaderRow(
                    source_row_ids=_source_ids(page_spec.page_tag, source_lines),
                    label=normalize_text(" ".join(line.text for line in labels)),
                    note_reference="5",
                    cells=cells,
                ),
                row_kind=TMNoteRowKind.NUMERIC,
                source_role=row_spec.source_role,
                y_anchor=row_center,
                label_bbox=_union(labels) if labels else None,
                value_bboxes=tuple(axis_lines[0].bbox for axis_lines in per_axis),
                label_line_indices=tuple(line.index for line in labels),
                value_line_indices=tuple((axis_lines[0].index,) for axis_lines in per_axis),
                mapping_approved=False,
            )
        )
    unassigned_numeric = tuple(
        sorted(line.index for line in numeric if line.index not in used_numeric)
    )
    unassigned_labels = tuple(
        sorted(line.index for line in label_lines if line.index not in used_labels)
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
        if line.index in {axis.period_line_index, axis.unit_line_index}
    )
    used_indices = {
        int(source_id.rsplit("-", 1)[-1]) for row in rows for source_id in row.row.source_row_ids
    }
    table_lines.extend(line for line in lines if line.index in used_indices)
    result = ParsedTMLoanAnalysisPage(
        input_path=input_path,
        source_sha256=page_spec.source_ocr_sha256,
        source_render_sha256=page_spec.source_render_sha256,
        source_pdf_sha256=policy.source_pdf_sha256,
        page_tag=page_spec.page_tag,
        page_number=page_spec.page_number,
        scope=policy.scope,
        scope_binding=policy.scope_binding,
        title=title.text,
        title_line_index=title.index,
        axes=axes,
        rows=tuple(rows),
        line_height=line_height,
        source_ocr_bbox=source_bbox,
        table_bbox=_union(table_lines),
        unassigned_numeric_line_indices=unassigned_numeric,
        unassigned_label_line_indices=unassigned_labels,
        excluded_artifact_numeric_line_indices=artifact_numeric,
        excluded_footer_numeric_line_indices=footer,
        mapping_authority=False,
        evidence=(
            "visible loan-analysis title and local mixed amount/percentage headers",
            "logical rows reconstructed from PP-OCRv6 numeric clusters and visible label groups",
            "amount and percentage cells remain distinct typed axes",
            "this parser grants no ReportNormId authority",
        ),
    )
    denominator = (
        len(result.rows),
        result.numeric_row_count,
        result.label_only_row_count,
        result.financial_slot_count,
    )
    if (
        denominator != _EXPECTED_DENOMINATORS[page_spec.page_number]
        or result.observation_count(ObservationKind.VALUE)
        + result.observation_count(ObservationKind.ZERO)
        != result.financial_slot_count
        or unassigned_numeric
        or unassigned_labels
    ):
        raise TMNoteWordBoxError(
            f"TM {page_spec.page_tag} source denominator drifted: {denominator}, "
            f"numeric={unassigned_numeric}, labels={unassigned_labels}"
        )
    return result


def parse_tm_note_pages32_33(
    inputs: Mapping[int, tuple[Path, Path]], policy: TMNotePages3233Policy
) -> ParsedTMNotePages3233:
    if set(inputs) != {32, 33}:
        raise TMNoteWordBoxError("TM pages32-33 inputs must contain exactly pages 32 and 33")
    pages = tuple(
        _parse_page(inputs[spec.page_number][0], inputs[spec.page_number][1], spec, policy)
        for spec in policy.pages
    )
    rows = tuple(row for page in pages for row in page.rows)
    result = ParsedTMNotePages3233(
        pages=pages,
        rows=rows,
        scope=policy.scope,
        source_pdf_sha256=policy.source_pdf_sha256,
        mapping_authority=False,
        evidence=(
            "two independently hashed source renders and PP-OCRv6 fixtures",
            "46 logical rows and 176 amount/percentage observations",
            "snapshot, scope, unit and measure roles bound before mapping",
        ),
    )
    if (
        len(result.rows) != 46
        or result.numeric_row_count != 44
        or result.label_only_row_count != 2
        or result.financial_slot_count != 176
        or result.observation_count(ObservationKind.VALUE) != 174
        or result.observation_count(ObservationKind.ZERO) != 2
    ):
        raise TMNoteWordBoxError("TM pages32-33 combined denominator drifted")
    return result


__all__ = [
    "ParsedTMLoanAnalysisPage",
    "ParsedTMNotePages3233",
    "TMLoanAnalysisAxisBinding",
    "TMLoanAnalysisLogicalRow",
    "TMNotePages3233Policy",
    "load_tm_note_pages32_33_policy",
    "parse_tm_note_pages32_33",
]
