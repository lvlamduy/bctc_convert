"""Source-only EPS and share-count reconstruction for MBB consolidated PDF page 45.

The page mixes duration and snapshot periods and three row-local units.  A
missing OCR token is never enough to infer either a printed dash or a blank:
dashes require connected-component evidence from the immutable render, while
the two registered-share cells require an independently bounded all-white
render crop.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import yaml

from bctc_ai.core.contracts import BoundingBox, ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import (
    normalize_text,
    parse_financial_number,
    parse_vietnamese_dates,
    retrieval_key,
)
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
_ROLES = ("CURRENT", "COMPARATIVE")
_REQUIRED_FORBIDDEN = {
    "missing_ocr_cell_as_dash_without_pixel_evidence",
    "missing_ocr_cell_as_blank_without_pixel_evidence",
    "header_trieu_dong_as_unit_for_share_or_eps_rows",
    "template_labels_as_row_reconstruction_input",
    "approved_report_norm_id_assignment",
    "historical_or_mongodb_values",
    "human_review_answers",
    "dash_as_zero",
    "blank_as_zero",
    "accounting_equations_as_value_imputation",
}
_EXPECTED_TABLES = (
    (
        "EARNINGS_PER_SHARE",
        "22.2",
        "DURATION",
        (
            "PROFIT_ATTRIBUTABLE_TO_BANK_SHAREHOLDERS",
            "WEIGHTED_AVERAGE_ORDINARY_SHARES",
            "BASIC_EARNINGS_PER_SHARE",
        ),
        (
            ("VALUE", "VALUE"),
            ("VALUE", "VALUE"),
            ("VALUE", "VALUE"),
        ),
        (("VND", 1_000_000), ("SHARE", 1), ("VND_PER_SHARE", 1)),
    ),
    (
        "SHARE_COUNTS",
        "22.3",
        "SNAPSHOT",
        (
            "REGISTERED_FOR_ISSUANCE",
            "SOLD_TO_PUBLIC",
            "SOLD_TO_PUBLIC_ORDINARY",
            "REPURCHASED",
            "REPURCHASED_ORDINARY",
            "REPURCHASED_PREFERRED",
            "OUTSTANDING",
            "OUTSTANDING_ORDINARY",
            "OUTSTANDING_PREFERRED",
        ),
        (
            ("BLANK", "BLANK"),
            ("VALUE", "VALUE"),
            ("VALUE", "VALUE"),
            ("DASH", "DASH"),
            ("DASH", "DASH"),
            ("DASH", "DASH"),
            ("VALUE", "VALUE"),
            ("VALUE", "VALUE"),
            ("DASH", "DASH"),
        ),
        tuple(("SHARE", 1) for _index in range(9)),
    ),
)


@dataclass(frozen=True)
class TMPage45ExpectedAxis:
    role: str
    period_start: date
    period_end: date


@dataclass(frozen=True)
class TMPage45UnitSpec:
    canonical: str
    multiplier: int
    evidence: str


@dataclass(frozen=True)
class TMPage45RowSpec:
    semantic_role: str
    label_anchors: tuple[str, ...]
    expected_label_lines: int
    expected_observations: tuple[str, ...]
    unit: TMPage45UnitSpec


@dataclass(frozen=True)
class TMPage45HeaderUnitSpec:
    anchors: tuple[str, ...]
    canonical: str
    multiplier: int


@dataclass(frozen=True)
class TMPage45TableSpec:
    table_key: str
    note_number: str
    title_anchors: tuple[str, ...]
    first_body_anchors: tuple[str, ...]
    period_type: str
    expected_axes: tuple[TMPage45ExpectedAxis, ...]
    header_unit: TMPage45HeaderUnitSpec | None
    rows: tuple[TMPage45RowSpec, ...]


@dataclass(frozen=True)
class TMPage45Policy:
    source_path: Path
    document: str
    page_number: int
    page_tag: str
    scope: str
    scope_binding: str
    source_pdf_sha256: str
    source_render_sha256: str
    source_ocr_sha256: str
    upstream_ocr_sha256: str
    minimum_line_score: float
    minimum_anchor_similarity: float
    row_value_center_tolerance_line_heights: float
    blank_search_width_line_heights: float
    blank_search_right_padding_line_heights: float
    blank_search_half_height_line_heights: float
    page_footer_top_ratio: float
    dash_config: dict[str, float | int]
    dash_config_path: Path
    tables: tuple[TMPage45TableSpec, ...]
    forbidden_semantic_inputs: tuple[str, ...]


@dataclass(frozen=True)
class TMPage45AxisBinding:
    ordinal: int
    axis_id: str
    axis_right_edge: float
    raw_header_text: str
    header_line_indices: tuple[int, ...]
    semantic_role: str
    period_start: date
    period_end: date
    period_type: str
    header_bbox: BoundingBox
    unit_line_index: int | None
    unit_bbox: BoundingBox | None
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class TMPage45BlankEvidence:
    observation: str
    source_image_path: str
    crop_box: tuple[int, int, int, int]
    minimum_intensity: int
    foreground_pixel_count: int
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class TMPage45LogicalRow:
    row_id: str
    table_key: str
    note_number: str
    ordinal: int
    row: ReaderRow
    row_kind: TMNoteRowKind
    semantic_role: str
    y_anchor: float
    label_bbox: BoundingBox
    value_bboxes: tuple[BoundingBox | None, ...]
    label_line_indices: tuple[int, ...]
    value_line_indices: tuple[tuple[int, ...], ...]
    visual_cell_evidence: tuple[VisualCellEvidence | TMPage45BlankEvidence | None, ...]
    cell_period_roles: tuple[str, ...]
    cell_period_starts: tuple[date, ...]
    cell_period_ends: tuple[date, ...]
    period_type: str
    canonical_unit: str
    unit_multiplier: int
    unit_evidence: str
    unit_source_line_indices: tuple[int, ...]
    mapping_approved: bool

    @property
    def financial_slot_count(self) -> int:
        return len(self.row.cells) if self.row_kind is TMNoteRowKind.NUMERIC else 0


@dataclass(frozen=True)
class TMPage45StructuralRow:
    row_id: str
    table_key: str
    note_number: str
    ordinal: int
    row: ReaderRow
    row_kind: TMNoteRowKind
    semantic_role: str
    label_bbox: BoundingBox
    label_line_indices: tuple[int, ...]
    mapping_approved: bool

    @property
    def financial_slot_count(self) -> int:
        return 0


TMPage45Row = TMPage45StructuralRow | TMPage45LogicalRow


@dataclass(frozen=True)
class TMPage45Table:
    ordinal: int
    table_key: str
    note_number: str
    title: str
    title_line_indices: tuple[int, ...]
    axes: tuple[TMPage45AxisBinding, ...]
    rows: tuple[TMPage45Row, ...]
    bbox: BoundingBox


@dataclass(frozen=True)
class ParsedTMPage45:
    input_path: str
    source_sha256: str
    upstream_ocr_sha256: str
    source_render_sha256: str
    source_pdf_sha256: str
    page_tag: str
    scope: str
    scope_binding: str
    tables: tuple[TMPage45Table, ...]
    rows: tuple[TMPage45Row, ...]
    line_height: float
    source_ocr_bbox: BoundingBox
    table_bbox: BoundingBox
    unassigned_numeric_line_indices: tuple[int, ...]
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
            if isinstance(row, TMPage45LogicalRow)
            for cell in row.row.cells
        )


def _anchors(payload: Any, field: str) -> tuple[str, ...]:
    if not isinstance(payload, list) or not payload:
        raise TMNoteWordBoxError(f"TM page-45 {field} anchors are invalid")
    anchors = tuple(retrieval_key(str(value)) for value in payload)
    if any(not value for value in anchors):
        raise TMNoteWordBoxError(f"TM page-45 {field} contains an empty anchor")
    return anchors


def _positive(payload: dict[str, Any], field: str) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise TMNoteWordBoxError(f"invalid positive TM page-45 setting: {field}")
    return float(value)


def _date_value(value: Any, field: str) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise TMNoteWordBoxError(f"invalid TM page-45 {field}") from exc
    raise TMNoteWordBoxError(f"invalid TM page-45 {field}")


def _unit(payload: Any, field: str) -> TMPage45UnitSpec:
    if not isinstance(payload, dict):
        raise TMNoteWordBoxError(f"TM page-45 {field} unit is absent")
    canonical = payload.get("canonical")
    multiplier = payload.get("multiplier")
    evidence = payload.get("evidence")
    if (
        not isinstance(canonical, str)
        or not canonical
        or isinstance(multiplier, bool)
        or not isinstance(multiplier, int)
        or multiplier <= 0
        or evidence not in {"TABLE_LOCAL_HEADER", "ROW_LOCAL_LABEL"}
    ):
        raise TMNoteWordBoxError(f"TM page-45 {field} unit binding is invalid")
    return TMPage45UnitSpec(canonical, multiplier, str(evidence))


def _contains_schema_key(payload: Any) -> bool:
    if isinstance(payload, dict):
        return any(
            "report_norm_id" in str(key) or _contains_schema_key(value)
            for key, value in payload.items()
        )
    if isinstance(payload, list):
        return any(_contains_schema_key(value) for value in payload)
    return False


def load_tm_page45_policy(path: Path) -> TMPage45Policy:
    """Load and validate the immutable source-only page-45 policy."""

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMNoteWordBoxError(f"cannot load TM page-45 policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE45_EPS_SHARE_DISCLOSURE_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 45
        or payload.get("page_tag") != "page-0045"
        or payload.get("scope") != "CONSOLIDATED"
    ):
        raise TMNoteWordBoxError("TM page-45 policy identity drifted")
    if _contains_schema_key(payload):
        raise TMNoteWordBoxError("TM page-45 policy must remain schema-identifier free")
    hashes = tuple(
        payload.get(field)
        for field in (
            "source_pdf_sha256",
            "source_render_sha256",
            "source_ocr_sha256",
            "upstream_ocr_sha256",
        )
    )
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMNoteWordBoxError("TM page-45 source hashes are invalid")
    threshold = payload.get("minimum_anchor_similarity")
    score = payload.get("minimum_line_score")
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1
        for value in (threshold, score)
    ):
        raise TMNoteWordBoxError("TM page-45 similarity thresholds are invalid")
    raw_tables = payload.get("tables")
    if not isinstance(raw_tables, list) or len(raw_tables) != 2:
        raise TMNoteWordBoxError("TM page-45 must define exactly two source tables")
    tables = []
    for table_index, (record, expected) in enumerate(
        zip(raw_tables, _EXPECTED_TABLES, strict=True), start=1
    ):
        if not isinstance(record, dict):
            raise TMNoteWordBoxError("TM page-45 table record is invalid")
        table_key, note_number, period_type, roles, patterns, units = expected
        if (
            record.get("table_key") != table_key
            or record.get("note_number") != note_number
            or record.get("period_type") != period_type
        ):
            raise TMNoteWordBoxError(f"TM page-45 table {table_index} identity drifted")
        raw_axes = record.get("expected_axes")
        if not isinstance(raw_axes, list) or len(raw_axes) != 2:
            raise TMNoteWordBoxError("TM page-45 table must expose exactly two axes")
        axes = []
        for axis_record, role in zip(raw_axes, _ROLES, strict=True):
            if not isinstance(axis_record, dict) or axis_record.get("role") != role:
                raise TMNoteWordBoxError("TM page-45 axis order drifted")
            axes.append(
                TMPage45ExpectedAxis(
                    role,
                    _date_value(axis_record.get("start"), "period start"),
                    _date_value(axis_record.get("end"), "period end"),
                )
            )
        header_unit_record = record.get("header_unit")
        header_unit = None
        if header_unit_record is not None:
            if not isinstance(header_unit_record, dict):
                raise TMNoteWordBoxError("TM page-45 header unit is invalid")
            canonical = header_unit_record.get("canonical")
            multiplier = header_unit_record.get("multiplier")
            if canonical != "VND" or multiplier != 1_000_000:
                raise TMNoteWordBoxError("TM page-45 visible header-unit binding drifted")
            header_unit = TMPage45HeaderUnitSpec(
                _anchors(header_unit_record.get("anchors"), "header unit"),
                canonical,
                multiplier,
            )
        if (table_index == 1) != (header_unit is not None):
            raise TMNoteWordBoxError("TM page-45 table-local unit presence drifted")
        raw_rows = record.get("rows")
        if not isinstance(raw_rows, list) or len(raw_rows) != len(roles):
            raise TMNoteWordBoxError("TM page-45 exact row denominator drifted")
        rows = []
        for row_index, (row, role, pattern, expected_unit) in enumerate(
            zip(raw_rows, roles, patterns, units, strict=True), start=1
        ):
            if not isinstance(row, dict) or row.get("semantic_role") != role:
                raise TMNoteWordBoxError("TM page-45 row identity/order drifted")
            label_count = row.get("expected_label_lines")
            observations = row.get("expected_observations")
            unit = _unit(row.get("unit"), f"row {row_index}")
            if (
                isinstance(label_count, bool)
                or not isinstance(label_count, int)
                or label_count <= 0
                or not isinstance(observations, list)
                or tuple(observations) != pattern
                or (unit.canonical, unit.multiplier) != expected_unit
            ):
                raise TMNoteWordBoxError("TM page-45 row contract drifted")
            if table_index == 1 and row_index == 1 and unit.evidence != "TABLE_LOCAL_HEADER":
                raise TMNoteWordBoxError("TM page-45 profit unit must bind to the visible header")
            if (table_index, row_index) != (1, 1) and unit.evidence != "ROW_LOCAL_LABEL":
                raise TMNoteWordBoxError("TM page-45 non-profit unit must remain row-local")
            rows.append(
                TMPage45RowSpec(
                    role,
                    _anchors(row.get("label_anchors"), f"row {row_index} label"),
                    label_count,
                    tuple(str(value) for value in observations),
                    unit,
                )
            )
        tables.append(
            TMPage45TableSpec(
                table_key,
                note_number,
                _anchors(record.get("title_anchors"), "table title"),
                _anchors(record.get("first_body_anchors"), "first body"),
                period_type,
                tuple(axes),
                header_unit,
                tuple(rows),
            )
        )
    dash_name = payload.get("dash_detector_config")
    if not isinstance(dash_name, str) or Path(dash_name).name != dash_name:
        raise TMNoteWordBoxError("TM page-45 dash detector path is invalid")
    dash_path = (path.parent / dash_name).resolve()
    if not dash_path.is_file() or sha256_file(dash_path) != payload.get(
        "dash_detector_config_sha256"
    ):
        raise TMNoteWordBoxError("TM page-45 dash detector is absent or drifted")
    forbidden = payload.get("forbidden_semantic_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMNoteWordBoxError("TM page-45 forbidden semantic inputs drifted")
    footer_ratio = _positive(payload, "page_footer_top_ratio")
    if footer_ratio >= 1:
        raise TMNoteWordBoxError("TM page-45 footer ratio must be below one")
    dash_config = load_word_box_reconstruction_v3_config(dash_path).base.base
    return TMPage45Policy(
        source_path=path,
        document=str(payload.get("document", "")),
        page_number=45,
        page_tag="page-0045",
        scope="CONSOLIDATED",
        scope_binding=str(payload.get("scope_binding", "")),
        source_pdf_sha256=str(hashes[0]),
        source_render_sha256=str(hashes[1]),
        source_ocr_sha256=str(hashes[2]),
        upstream_ocr_sha256=str(hashes[3]),
        minimum_line_score=float(score),
        minimum_anchor_similarity=float(threshold),
        row_value_center_tolerance_line_heights=_positive(
            payload, "row_value_center_tolerance_line_heights"
        ),
        blank_search_width_line_heights=_positive(payload, "blank_search_width_line_heights"),
        blank_search_right_padding_line_heights=_positive(
            payload, "blank_search_right_padding_line_heights"
        ),
        blank_search_half_height_line_heights=_positive(
            payload, "blank_search_half_height_line_heights"
        ),
        page_footer_top_ratio=footer_ratio,
        dash_config={str(key): value for key, value in dash_config.items()},
        dash_config_path=dash_path,
        tables=tuple(tables),
        forbidden_semantic_inputs=tuple(str(value) for value in forbidden),
    )


def _find_anchor(
    lines: tuple[_Line, ...] | list[_Line],
    anchors: tuple[str, ...],
    policy: TMPage45Policy,
    *,
    minimum_y: float = float("-inf"),
    maximum_y: float = float("inf"),
) -> _Line:
    candidates = [line for line in lines if minimum_y < line.y_center < maximum_y]
    if not candidates:
        raise TMNoteWordBoxError("TM page-45 anchor search has no visible candidates")
    score, selected = max(
        ((_best_anchor_similarity(line.text, anchors), line) for line in candidates),
        key=lambda item: (item[0], -item[1].y_center),
    )
    if score < policy.minimum_anchor_similarity:
        raise TMNoteWordBoxError("TM page-45 visible anchor similarity is below policy")
    return selected


def _header_groups(
    header_lines: tuple[_Line, ...], expected_count: int
) -> tuple[tuple[_Line, ...], ...]:
    date_lines = tuple(line for line in header_lines if len(parse_vietnamese_dates(line.text)) == 1)
    if len(date_lines) != expected_count:
        raise TMNoteWordBoxError("TM page-45 visible date denominator drifted")
    ordered = tuple(sorted(date_lines, key=lambda line: (line.x_center, line.y_center)))
    gaps = [
        ordered[index + 1].x_center - ordered[index].x_center for index in range(len(ordered) - 1)
    ]
    if not gaps:
        raise TMNoteWordBoxError("TM page-45 visible axes cannot be separated")
    split = max(range(len(gaps)), key=gaps.__getitem__) + 1
    groups = (ordered[:split], ordered[split:])
    if not all(groups):
        raise TMNoteWordBoxError("TM page-45 visible axes are not bijective")
    return tuple(tuple(sorted(group, key=lambda line: line.y_center)) for group in groups)


def _axes(
    lines: tuple[_Line, ...],
    title: _Line,
    first_body: _Line,
    body_end: float,
    spec: TMPage45TableSpec,
    policy: TMPage45Policy,
) -> tuple[TMPage45AxisBinding, ...]:
    header = tuple(line for line in lines if title.y_center < line.y_center < first_body.y_center)
    expected_date_lines = 4 if spec.period_type == "DURATION" else 2
    groups = _header_groups(header, expected_date_lines)
    centers = tuple(statistics.fmean(line.x_center for line in group) for group in groups)
    if centers != tuple(sorted(centers)):
        raise TMNoteWordBoxError("TM page-45 axis order is not left-to-right")
    numeric_values = tuple(
        line
        for line in lines
        if first_body.y_center - line.height <= line.y_center < body_end
        and _numeric_only(line.text)
        and parse_financial_number(line.text).observation
        in {ObservationKind.VALUE, ObservationKind.ZERO}
    )
    per_axis: list[list[_Line]] = [[] for _center in centers]
    for line in numeric_values:
        closest = min(range(len(centers)), key=lambda index: abs(line.x_center - centers[index]))
        per_axis[closest].append(line)
    if any(not group for group in per_axis):
        raise TMNoteWordBoxError("TM page-45 numeric axes lack visible value support")
    unit_lines: tuple[_Line | None, ...] = tuple(None for _center in centers)
    if spec.header_unit is not None:
        candidates = tuple(
            line
            for line in header
            if not parse_vietnamese_dates(line.text)
            and _best_anchor_similarity(line.text, spec.header_unit.anchors)
            >= policy.minimum_anchor_similarity
        )
        if len(candidates) != 2:
            raise TMNoteWordBoxError("TM page-45 visible VND-million unit denominator drifted")
        assigned: list[_Line | None] = [None, None]
        for line in candidates:
            closest = min(
                range(len(centers)), key=lambda index: abs(line.x_center - centers[index])
            )
            if assigned[closest] is not None:
                raise TMNoteWordBoxError("TM page-45 visible header units are not bijective")
            assigned[closest] = line
        unit_lines = tuple(assigned)
    result = []
    for ordinal, (group, values, expected, unit_line) in enumerate(
        zip(groups, per_axis, spec.expected_axes, unit_lines, strict=True), start=1
    ):
        visible_dates = tuple(
            parsed for line in group for parsed in parse_vietnamese_dates(line.text)
        )
        expected_dates = (
            (expected.period_start, expected.period_end)
            if spec.period_type == "DURATION"
            else (expected.period_end,)
        )
        if visible_dates != expected_dates:
            raise TMNoteWordBoxError("TM page-45 visible period drifted from policy")
        header_evidence = [*group]
        if unit_line is not None:
            header_evidence.append(unit_line)
        result.append(
            TMPage45AxisBinding(
                ordinal=ordinal,
                axis_id=f"{spec.period_type.lower()}-{expected.role.lower()}",
                axis_right_edge=float(statistics.median(line.x_right for line in values)),
                raw_header_text=normalize_text(
                    " | ".join(
                        line.text
                        for line in sorted(header_evidence, key=lambda item: item.y_center)
                    )
                ),
                header_line_indices=tuple(line.index for line in group),
                semantic_role=expected.role,
                period_start=expected.period_start,
                period_end=expected.period_end,
                period_type=spec.period_type,
                header_bbox=_union(header_evidence),
                unit_line_index=unit_line.index if unit_line is not None else None,
                unit_bbox=unit_line.bbox if unit_line is not None else None,
                evidence=(
                    "period parsed from the visible table-local header",
                    "current/comparative role bound by visible horizontal order",
                    "axis right edge derived from visible numeric OCR geometry",
                ),
            )
        )
    return tuple(result)


def _blank_evidence(
    image: np.ndarray,
    image_path: Path,
    policy: TMPage45Policy,
    *,
    axis_right_edge: float,
    row_center: float,
    line_height: float,
) -> TMPage45BlankEvidence:
    image_height, image_width = image.shape[:2]
    x0 = max(0, int(round(axis_right_edge - line_height * policy.blank_search_width_line_heights)))
    x1 = min(
        image_width,
        int(round(axis_right_edge + line_height * policy.blank_search_right_padding_line_heights)),
    )
    y0 = max(0, int(round(row_center - line_height * policy.blank_search_half_height_line_heights)))
    y1 = min(
        image_height,
        int(round(row_center + line_height * policy.blank_search_half_height_line_heights)),
    )
    if x1 <= x0 or y1 <= y0:
        raise TMNoteWordBoxError("TM page-45 registered-share blank crop is invalid")
    crop = image[y0:y1, x0:x1]
    foreground = int(np.count_nonzero(crop < 255))
    minimum = int(crop.min())
    if foreground or minimum != 255:
        raise TMNoteWordBoxError(
            "TM page-45 registered-share cell lacks all-white blank pixel evidence"
        )
    return TMPage45BlankEvidence(
        observation="BLANK",
        source_image_path=str(image_path),
        crop_box=(x0, y0, x1, y1),
        minimum_intensity=minimum,
        foreground_pixel_count=foreground,
        evidence=(
            "cell crop is bounded by the row-local label center and numeric axis",
            "immutable render crop contains no foreground pixel",
            "absence is registered as BLANK, never DASH or ZERO",
        ),
    )


def _structural_row(page_tag: str, spec: TMPage45TableSpec, title: _Line) -> TMPage45StructuralRow:
    return TMPage45StructuralRow(
        row_id=f"{page_tag}:{spec.table_key.lower()}:row-0001",
        table_key=spec.table_key,
        note_number=spec.note_number,
        ordinal=1,
        row=ReaderRow(
            source_row_ids=_source_ids(page_tag, [title]),
            label=title.text,
            note_reference=spec.note_number,
            cells=(),
        ),
        row_kind=TMNoteRowKind.LABEL_ONLY,
        semantic_role="NOTE_TITLE",
        label_bbox=title.bbox,
        label_line_indices=(title.index,),
        mapping_approved=False,
    )


def _table_rows(
    lines: tuple[_Line, ...],
    image: np.ndarray,
    image_path: Path,
    spec: TMPage45TableSpec,
    title: _Line,
    first_body: _Line,
    body_end: float,
    axes: tuple[TMPage45AxisBinding, ...],
    policy: TMPage45Policy,
    line_height: float,
) -> tuple[tuple[TMPage45Row, ...], tuple[int, ...], tuple[_Line, ...]]:
    numeric_lines = tuple(
        line
        for line in lines
        if first_body.y_center - line.height <= line.y_center < body_end
        and _numeric_only(line.text)
    )
    label_candidates = tuple(
        sorted(
            (
                line
                for line in lines
                if first_body.y_center - line.height <= line.y_center < body_end
                and not _numeric_only(line.text)
                and line.bbox.x0 < axes[0].axis_right_edge - line_height * 3
            ),
            key=lambda line: (line.y_center, line.bbox.x0, line.index),
        )
    )
    rows: list[TMPage45Row] = [_structural_row(policy.page_tag, spec, title)]
    used_labels: set[int] = set()
    used_numeric: set[int] = set()
    cursor = first_body.y_center - line_height
    table_lines: list[_Line] = [title]
    for source_ordinal, row_spec in enumerate(spec.rows, start=2):
        candidates = [
            line
            for line in label_candidates
            if line.index not in used_labels and line.y_center > cursor
        ]
        if not candidates:
            raise TMNoteWordBoxError("TM page-45 row label denominator drifted")
        matched = next(
            (
                (score, line)
                for line in candidates
                if (score := _best_anchor_similarity(line.text, row_spec.label_anchors))
                >= policy.minimum_anchor_similarity
            ),
            None,
        )
        if matched is None:
            raise TMNoteWordBoxError(
                f"TM page-45 visible row label unresolved: {row_spec.semantic_role}"
            )
        _score, anchor = matched
        start_index = label_candidates.index(anchor)
        group = tuple(
            line
            for line in label_candidates[start_index : start_index + row_spec.expected_label_lines]
            if line.index not in used_labels
        )
        if len(group) != row_spec.expected_label_lines or group[0].index != anchor.index:
            raise TMNoteWordBoxError("TM page-45 wrapped-label denominator drifted")
        if any(
            right.y_center - left.y_center > line_height * 1.25
            for left, right in zip(group, group[1:], strict=False)
        ):
            raise TMNoteWordBoxError("TM page-45 wrapped-label geometry drifted")
        used_labels.update(line.index for line in group)
        cursor = max(line.y_center for line in group)
        row_center = cursor
        nearby = [
            line
            for line in numeric_lines
            if line.index not in used_numeric
            and abs(line.y_center - row_center)
            <= line_height * policy.row_value_center_tolerance_line_heights
        ]
        per_axis: list[list[_Line]] = [[] for _axis in axes]
        axis_gap = axes[1].axis_right_edge - axes[0].axis_right_edge
        for line in nearby:
            distances = [abs(line.x_right - axis.axis_right_edge) for axis in axes]
            closest = min(range(len(axes)), key=distances.__getitem__)
            if distances[closest] <= axis_gap * 0.40:
                per_axis[closest].append(line)
        if any(len(group_lines) > 1 for group_lines in per_axis):
            raise TMNoteWordBoxError("TM page-45 cell has multiple numeric OCR lines")
        cells = []
        visual: list[VisualCellEvidence | TMPage45BlankEvidence | None] = []
        value_bboxes: list[BoundingBox | None] = []
        for axis, expected_observation, value_group in zip(
            axes, row_spec.expected_observations, per_axis, strict=True
        ):
            evidence: VisualCellEvidence | TMPage45BlankEvidence | None = None
            if expected_observation == "VALUE":
                if len(value_group) != 1:
                    raise TMNoteWordBoxError(
                        f"TM page-45 visible VALUE cell is absent: {row_spec.semantic_role}"
                    )
                cell = parse_financial_number(value_group[0].text)
                if cell.observation is not ObservationKind.VALUE:
                    raise TMNoteWordBoxError("TM page-45 finite value observation drifted")
                value_bbox: BoundingBox | None = value_group[0].bbox
            elif expected_observation == "DASH":
                if value_group and normalize_text(value_group[0].text) not in {"-", "--"}:
                    raise TMNoteWordBoxError(
                        "TM page-45 DASH cell conflicts with numeric OCR: "
                        f"{row_spec.semantic_role} {value_group[0].index}={value_group[0].text}"
                    )
                evidence = _detect_visible_dash_v3(
                    image,
                    source_image_path=image_path,
                    axis_right_edge=axis.axis_right_edge,
                    anchor_center=row_center,
                    line_height=line_height,
                    config=policy.dash_config,
                )
                if evidence is None:
                    raise TMNoteWordBoxError(
                        f"TM page-45 missing cell lacks dash pixel evidence: {row_spec.semantic_role}"
                    )
                cell = parse_financial_number("-")
                value_bbox = BoundingBox(*(float(value) for value in evidence.component_box))
            elif expected_observation == "BLANK":
                if value_group:
                    raise TMNoteWordBoxError("TM page-45 BLANK cell conflicts with numeric OCR")
                if (
                    _detect_visible_dash_v3(
                        image,
                        source_image_path=image_path,
                        axis_right_edge=axis.axis_right_edge,
                        anchor_center=row_center,
                        line_height=line_height,
                        config=policy.dash_config,
                    )
                    is not None
                ):
                    raise TMNoteWordBoxError("TM page-45 registered-share BLANK contains a dash")
                evidence = _blank_evidence(
                    image,
                    image_path,
                    policy,
                    axis_right_edge=axis.axis_right_edge,
                    row_center=row_center,
                    line_height=line_height,
                )
                cell = parse_financial_number(None)
                value_bbox = BoundingBox(*(float(value) for value in evidence.crop_box))
            else:
                raise TMNoteWordBoxError("TM page-45 unsupported expected observation")
            if cell.observation.value != expected_observation:
                raise TMNoteWordBoxError("TM page-45 observation pattern drifted")
            cells.append(cell)
            visual.append(evidence)
            value_bboxes.append(value_bbox)
            used_numeric.update(line.index for line in value_group)
        source_lines = [*group, *(line for value_group in per_axis for line in value_group)]
        unit_lines = (
            tuple(axis.unit_line_index for axis in axes if axis.unit_line_index is not None)
            if row_spec.unit.evidence == "TABLE_LOCAL_HEADER"
            else tuple(line.index for line in group)
        )
        row = TMPage45LogicalRow(
            row_id=f"{policy.page_tag}:{spec.table_key.lower()}:row-{source_ordinal:04d}",
            table_key=spec.table_key,
            note_number=spec.note_number,
            ordinal=source_ordinal,
            row=ReaderRow(
                source_row_ids=_source_ids(policy.page_tag, source_lines),
                label=normalize_text(" ".join(line.text for line in group)),
                note_reference=spec.note_number,
                cells=tuple(cells),
            ),
            row_kind=TMNoteRowKind.NUMERIC,
            semantic_role=row_spec.semantic_role,
            y_anchor=row_center,
            label_bbox=_union(group),
            value_bboxes=tuple(value_bboxes),
            label_line_indices=tuple(line.index for line in group),
            value_line_indices=tuple(
                tuple(line.index for line in value_group) for value_group in per_axis
            ),
            visual_cell_evidence=tuple(visual),
            cell_period_roles=tuple(axis.semantic_role for axis in axes),
            cell_period_starts=tuple(axis.period_start for axis in axes),
            cell_period_ends=tuple(axis.period_end for axis in axes),
            period_type=spec.period_type,
            canonical_unit=row_spec.unit.canonical,
            unit_multiplier=row_spec.unit.multiplier,
            unit_evidence=row_spec.unit.evidence,
            unit_source_line_indices=unit_lines,
            mapping_approved=False,
        )
        rows.append(row)
        table_lines.extend(source_lines)
    unassigned = tuple(
        sorted(line.index for line in numeric_lines if line.index not in used_numeric)
    )
    return tuple(rows), unassigned, tuple(table_lines)


def parse_tm_page45(
    result_path: Path,
    source_image_path: Path,
    policy: TMPage45Policy,
    *,
    page_tag: str = "page-0045",
) -> ParsedTMPage45:
    """Reconstruct page 45 without granting schema or mapping authority."""

    if page_tag != policy.page_tag:
        raise TMNoteWordBoxError("TM page-45 page tag drifted")
    if sha256_file(result_path) != policy.source_ocr_sha256:
        raise TMNoteWordBoxError("TM page-45 compact OCR fixture hash drifted")
    if sha256_file(source_image_path) != policy.source_render_sha256:
        raise TMNoteWordBoxError("TM page-45 source render hash drifted")
    image = cv2.imread(str(source_image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise TMNoteWordBoxError("TM page-45 source render cannot be decoded")
    input_path, lines, metadata = _load_lines(result_path, policy.minimum_line_score)
    if metadata != {
        "upstream_ocr_sha256": policy.upstream_ocr_sha256,
        "source_render_sha256": policy.source_render_sha256,
        "source_pdf_sha256": policy.source_pdf_sha256,
    }:
        raise TMNoteWordBoxError("TM page-45 compact OCR provenance drifted")
    line_height = float(statistics.median(line.height for line in lines))
    if line_height <= 0:
        raise TMNoteWordBoxError("TM page-45 line height is invalid")
    titles = []
    minimum_y = float("-inf")
    for spec in policy.tables:
        title = _find_anchor(lines, spec.title_anchors, policy, minimum_y=minimum_y)
        titles.append(title)
        minimum_y = title.y_center + line_height
    if tuple(title.y_center for title in titles) != tuple(
        sorted(title.y_center for title in titles)
    ):
        raise TMNoteWordBoxError("TM page-45 note order drifted")
    footer_top = image.shape[0] * policy.page_footer_top_ratio
    tables = []
    unassigned = []
    all_table_lines: list[_Line] = []
    for index, (spec, title) in enumerate(zip(policy.tables, titles, strict=True)):
        body_end = titles[index + 1].bbox.y0 if index + 1 < len(titles) else footer_top
        first_body = _find_anchor(
            lines,
            spec.first_body_anchors,
            policy,
            minimum_y=title.y_center,
            maximum_y=body_end,
        )
        axes = _axes(lines, title, first_body, body_end, spec, policy)
        rows, table_unassigned, table_lines = _table_rows(
            lines,
            image,
            source_image_path,
            spec,
            title,
            first_body,
            body_end,
            axes,
            policy,
            line_height,
        )
        header_lines = [
            line
            for line in lines
            if line.index
            in {
                line_index
                for axis in axes
                for line_index in (*axis.header_line_indices, axis.unit_line_index)
                if line_index is not None
            }
        ]
        evidence_lines = [*table_lines, *header_lines]
        tables.append(
            TMPage45Table(
                ordinal=index + 1,
                table_key=spec.table_key,
                note_number=spec.note_number,
                title=title.text,
                title_line_indices=(title.index,),
                axes=axes,
                rows=rows,
                bbox=_union(evidence_lines),
            )
        )
        unassigned.extend(table_unassigned)
        all_table_lines.extend(evidence_lines)
    footer = tuple(
        sorted(
            line.index for line in lines if line.y_center >= footer_top and _numeric_only(line.text)
        )
    )
    rows = tuple(row for table in tables for row in table.rows)
    table_bbox = BoundingBox(
        min(table.bbox.x0 for table in tables),
        min(table.bbox.y0 for table in tables),
        max(table.bbox.x1 for table in tables),
        max(table.bbox.y1 for table in tables),
    )
    result = ParsedTMPage45(
        input_path=input_path,
        source_sha256=policy.source_ocr_sha256,
        upstream_ocr_sha256=policy.upstream_ocr_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_pdf_sha256=policy.source_pdf_sha256,
        page_tag=page_tag,
        scope=policy.scope,
        scope_binding=policy.scope_binding,
        tables=tuple(tables),
        rows=rows,
        line_height=line_height,
        source_ocr_bbox=_union(lines),
        table_bbox=table_bbox,
        unassigned_numeric_line_indices=tuple(sorted(unassigned)),
        excluded_footer_numeric_line_indices=footer,
        mapping_authority=False,
        evidence=(
            "notes 22.2 and 22.3 reconstructed from immutable page-45 OCR geometry",
            "duration and snapshot axes parsed independently from each visible table header",
            "row-local VND-million, SHARE, and VND_PER_SHARE units remain distinct",
            "eight DASH cells have render component evidence and two BLANK cells have all-white crops",
            "no schema identifier or mapping authority enters the source parser",
        ),
    )
    if (
        [len(table.rows) for table in result.tables] != [4, 10]
        or len(result.rows) != 14
        or result.numeric_row_count != 12
        or result.label_only_row_count != 2
        or result.financial_slot_count != 24
        or result.observation_count(ObservationKind.VALUE) != 14
        or result.observation_count(ObservationKind.DASH) != 8
        or result.observation_count(ObservationKind.BLANK) != 2
        or result.observation_count(ObservationKind.ZERO) != 0
        or result.observation_count(ObservationKind.INVALID) != 0
        or result.unassigned_numeric_line_indices
        or result.excluded_footer_numeric_line_indices != (40,)
    ):
        raise TMNoteWordBoxError(
            "TM page-45 exact source denominator drifted: "
            f"tables={[len(table.rows) for table in result.tables]}, rows={len(result.rows)}, "
            f"numeric={result.numeric_row_count}, structural={result.label_only_row_count}, "
            f"slots={result.financial_slot_count}, value={result.observation_count(ObservationKind.VALUE)}, "
            f"dash={result.observation_count(ObservationKind.DASH)}, "
            f"blank={result.observation_count(ObservationKind.BLANK)}, "
            f"zero={result.observation_count(ObservationKind.ZERO)}, "
            f"invalid={result.observation_count(ObservationKind.INVALID)}, "
            f"unassigned={result.unassigned_numeric_line_indices}, "
            f"footer={result.excluded_footer_numeric_line_indices}"
        )
    return result


__all__ = [
    "ParsedTMPage45",
    "TMPage45AxisBinding",
    "TMPage45BlankEvidence",
    "TMPage45LogicalRow",
    "TMPage45Policy",
    "TMPage45StructuralRow",
    "TMPage45Table",
    "load_tm_page45_policy",
    "parse_tm_page45",
]
