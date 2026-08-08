"""Fixed-source TM table reconstruction for MBB consolidated PDF page 36."""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import yaml

from bctc_ai.core.contracts import BoundingBox, ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import retrieval_key
from bctc_ai.evaluation.word_box_rows_v3 import load_word_box_reconstruction_v3_config
from bctc_ai.tables.tm_note_page35 import (
    ParsedTMPage35,
    TMPage35LogicalRow,
    TMPage35Policy,
    TMPage35Table,
    TMPage35TableSpec,
    _body_end,
    _find_titles,
    _reconstruct_table,
)
from bctc_ai.tables.tm_note_word_box import (
    TMNoteWordBoxError,
    _bind_page31_axes,
    _load_lines,
    _numeric_only,
    _union,
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_FORBIDDEN = {
    "template_labels_as_row_reconstruction_input",
    "approved_report_norm_id_assignment",
    "historical_or_mongodb_values",
    "human_review_answers",
    "accounting_equations_as_value_imputation",
}

TMPage36Policy = TMPage35Policy
TMPage36LogicalRow = TMPage35LogicalRow
TMPage36Table = TMPage35Table


@dataclass(frozen=True)
class ParsedTMPage36(ParsedTMPage35):
    """Page-36 result using the shared fixed-grid row/table contracts."""


def _anchors(payload: Any, field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(payload, list) or (not payload and not allow_empty):
        raise TMNoteWordBoxError(f"TM page-36 {field} anchors are invalid")
    result = tuple(retrieval_key(str(value)) for value in payload)
    if any(not value for value in result):
        raise TMNoteWordBoxError(f"TM page-36 {field} contains an empty anchor")
    return result


def _positive(payload: dict[str, Any], field: str) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise TMNoteWordBoxError(f"invalid positive TM page-36 setting: {field}")
    return float(value)


def load_tm_page36_policy(path: Path) -> TMPage36Policy:
    """Load the immutable, source-scoped page-36 reconstruction policy."""

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMNoteWordBoxError(f"cannot load TM page-36 policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE36_FIXED_GRID_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 36
        or payload.get("page_tag") != "page-0036"
        or payload.get("scope") != "CONSOLIDATED"
    ):
        raise TMNoteWordBoxError("TM page-36 policy identity drifted")
    hashes = (
        payload.get("source_pdf_sha256"),
        payload.get("source_render_sha256"),
        payload.get("source_ocr_sha256"),
    )
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMNoteWordBoxError("TM page-36 source hashes are invalid")
    thresholds = (
        payload.get("minimum_line_score"),
        payload.get("minimum_anchor_similarity"),
        payload.get("minimum_unit_similarity"),
    )
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= float(value) <= 1
        for value in thresholds
    ):
        raise TMNoteWordBoxError("TM page-36 similarity thresholds are invalid")
    unit = payload.get("unit")
    header = payload.get("header_geometry")
    geometry = payload.get("table_geometry")
    if not all(isinstance(value, dict) for value in (unit, header, geometry)):
        raise TMNoteWordBoxError("TM page-36 geometry policy is incomplete")
    multiplier = unit.get("multiplier")
    canonical_unit = unit.get("canonical")
    if (
        isinstance(multiplier, bool)
        or not isinstance(multiplier, int)
        or multiplier <= 0
        or not isinstance(canonical_unit, str)
        or not canonical_unit
    ):
        raise TMNoteWordBoxError("TM page-36 unit binding is invalid")
    dash_name = payload.get("dash_detector_config")
    if not isinstance(dash_name, str) or Path(dash_name).name != dash_name:
        raise TMNoteWordBoxError("TM page-36 dash detector path is invalid")
    dash_path = (path.parent / dash_name).resolve()
    if not dash_path.is_file() or sha256_file(dash_path) != payload.get(
        "dash_detector_config_sha256"
    ):
        raise TMNoteWordBoxError("TM page-36 dash detector is absent or drifted")
    dash_config = load_word_box_reconstruction_v3_config(dash_path).base.base
    raw_tables = payload.get("tables")
    if not isinstance(raw_tables, list) or len(raw_tables) != 3:
        raise TMNoteWordBoxError("TM page-36 must define three visible tables")
    tables = []
    for record in raw_tables:
        if not isinstance(record, dict):
            raise TMNoteWordBoxError("TM page-36 table record is invalid")
        table_key = record.get("table_key")
        note_number = record.get("note_number")
        numeric_rows = record.get("expected_numeric_rows")
        label_rows = record.get("expected_label_only_rows")
        if (
            not isinstance(table_key, str)
            or not table_key
            or not isinstance(note_number, str)
            or not note_number
            or isinstance(numeric_rows, bool)
            or not isinstance(numeric_rows, int)
            or numeric_rows <= 0
            or isinstance(label_rows, bool)
            or not isinstance(label_rows, int)
            or label_rows < 0
        ):
            raise TMNoteWordBoxError("TM page-36 table denominator is invalid")
        tables.append(
            TMPage35TableSpec(
                table_key=table_key,
                note_number=note_number,
                title_anchors=_anchors(record.get("title_anchors"), f"{table_key} title"),
                body_end_anchors=_anchors(
                    record.get("body_end_anchors", []),
                    f"{table_key} body end",
                    allow_empty=True,
                ),
                structural_label_anchors=_anchors(
                    record.get("structural_label_anchors", []),
                    f"{table_key} structural label",
                    allow_empty=True,
                ),
                dash_label_anchors=_anchors(
                    record.get("dash_label_anchors", []),
                    f"{table_key} dash label",
                    allow_empty=True,
                ),
                expected_numeric_rows=numeric_rows,
                expected_label_only_rows=label_rows,
            )
        )
    if len({table.table_key for table in tables}) != len(tables):
        raise TMNoteWordBoxError("TM page-36 table keys are duplicated")
    forbidden = payload.get("forbidden_semantic_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMNoteWordBoxError("TM page-36 forbidden semantic inputs drifted")
    footer_ratio = _positive(geometry, "page_footer_top_ratio")
    structural_continuation = geometry.get("structural_continuation_line_heights", 0.0)
    if (
        isinstance(structural_continuation, bool)
        or not isinstance(structural_continuation, (int, float))
        or structural_continuation < 0
    ):
        raise TMNoteWordBoxError("TM page-36 structural-continuation bound is invalid")
    if footer_ratio >= 1:
        raise TMNoteWordBoxError("TM page-36 footer ratio must be below one")
    return TMPage35Policy(
        source_path=path,
        document=str(payload.get("document", "")),
        page_number=36,
        page_tag="page-0036",
        scope="CONSOLIDATED",
        scope_binding=str(payload.get("scope_binding", "")),
        source_pdf_sha256=hashes[0],
        source_render_sha256=hashes[1],
        source_ocr_sha256=hashes[2],
        minimum_line_score=float(thresholds[0]),
        minimum_anchor_similarity=float(thresholds[1]),
        minimum_unit_similarity=float(thresholds[2]),
        unit_anchors=_anchors(unit.get("anchors"), "unit"),
        canonical_unit=canonical_unit,
        unit_multiplier=multiplier,
        maximum_date_to_unit_center_distance_line_heights=_positive(
            header, "maximum_date_to_unit_center_distance_line_heights"
        ),
        minimum_axis_separation_line_heights=_positive(
            header, "minimum_axis_separation_line_heights"
        ),
        numeric_axis_max_distance_ratio=_positive(geometry, "numeric_axis_max_distance_ratio"),
        numeric_axis_right_overrun_line_heights=_positive(
            geometry, "numeric_axis_right_overrun_line_heights"
        ),
        row_anchor_cluster_line_heights=_positive(geometry, "row_anchor_cluster_line_heights"),
        label_direct_attach_line_heights=_positive(geometry, "label_direct_attach_line_heights"),
        structural_continuation_line_heights=float(structural_continuation),
        note_reference_left_gap_axis_widths=_positive(
            geometry, "note_reference_left_gap_axis_widths"
        ),
        page_footer_top_ratio=footer_ratio,
        dash_config={str(key): value for key, value in dash_config.items()},
        dash_config_path=dash_path,
        tables=tuple(tables),
        forbidden_semantic_inputs=tuple(str(value) for value in forbidden),
    )


def parse_tm_page36(
    result_path: Path,
    source_image_path: Path,
    policy: TMPage36Policy,
    *,
    page_tag: str = "page-0036",
) -> ParsedTMPage36:
    """Reconstruct all visible page-36 rows without granting mapping authority."""

    if page_tag != policy.page_tag:
        raise TMNoteWordBoxError("TM page-36 page tag drifted")
    if sha256_file(result_path) != policy.source_ocr_sha256:
        raise TMNoteWordBoxError("TM page-36 OCR artifact hash drifted")
    if sha256_file(source_image_path) != policy.source_render_sha256:
        raise TMNoteWordBoxError("TM page-36 source render hash drifted")
    source_image = cv2.imread(str(source_image_path), cv2.IMREAD_GRAYSCALE)
    if source_image is None:
        raise TMNoteWordBoxError("TM page-36 source render cannot be decoded")
    input_path, lines, _metadata = _load_lines(result_path, policy.minimum_line_score)
    line_height = float(statistics.median(line.height for line in lines))
    if line_height <= 0:
        raise TMNoteWordBoxError("TM page-36 line height is invalid")
    source_bbox = _union(lines)
    titles = _find_titles(lines, policy)
    footer_top = source_bbox.y1 * policy.page_footer_top_ratio
    tables = []
    unassigned = []
    body_ends = []
    for index, (spec, title) in enumerate(titles):
        next_title = titles[index + 1][1] if index + 1 < len(titles) else None
        table_body_end = _body_end(lines, spec, title, next_title, footer_top, policy)
        body_ends.append(table_body_end)
        axes = _bind_page31_axes(lines, title, None, table_body_end, policy, line_height)
        table, table_unassigned = _reconstruct_table(
            lines,
            spec,
            title,
            axes,
            table_body_end,
            policy,
            line_height,
            source_image,
            source_image_path,
            page_tag=page_tag,
            table_ordinal=index + 1,
        )
        tables.append(table)
        unassigned.extend(table_unassigned)
    canonical_axes = tables[0].axes
    semantic_axes = tuple(
        (
            axis.current_or_comparative,
            axis.period_end,
            axis.period_type,
            axis.canonical_unit,
            axis.unit_multiplier,
        )
        for axis in canonical_axes
    )
    if any(
        tuple(
            (
                axis.current_or_comparative,
                axis.period_end,
                axis.period_type,
                axis.canonical_unit,
                axis.unit_multiplier,
            )
            for axis in table.axes
        )
        != semantic_axes
        for table in tables[1:]
    ):
        raise TMNoteWordBoxError("TM page-36 repeated headers disagree semantically")
    rows = tuple(row for table in tables for row in table.rows)
    footer = tuple(
        sorted(
            line.index
            for line in lines
            if line.y_center >= body_ends[-1] and _numeric_only(line.text)
        )
    )
    result = ParsedTMPage36(
        input_path=input_path,
        source_sha256=policy.source_ocr_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_pdf_sha256=policy.source_pdf_sha256,
        page_tag=page_tag,
        scope=policy.scope,
        scope_binding=policy.scope_binding,
        axes=canonical_axes,
        tables=tuple(tables),
        rows=rows,
        line_height=line_height,
        source_ocr_bbox=source_bbox,
        table_bbox=BoundingBox(
            min(table.bbox.x0 for table in tables),
            min(table.bbox.y0 for table in tables),
            max(table.bbox.x1 for table in tables),
            max(table.bbox.y1 for table in tables),
        ),
        unassigned_numeric_line_indices=tuple(sorted(unassigned)),
        excluded_footer_numeric_line_indices=footer,
        mapping_authority=False,
        evidence=(
            "three local tables located from visible page-36 titles in source order",
            "two snapshot axes bound independently from every visible local header",
            "26 values reconstructed from PP-OCRv6 geometry",
            "wrapped structural heading retained separately from its first numeric child",
            "this parser grants no ReportNormId authority",
        ),
    )
    if (
        len(result.rows) != 14
        or result.numeric_row_count != 13
        or result.label_only_row_count != 1
        or result.financial_slot_count != 26
        or result.observation_count(ObservationKind.VALUE) != 26
        or result.observation_count(ObservationKind.DASH) != 0
    ):
        raise TMNoteWordBoxError("TM page-36 page denominator drifted")
    return result


__all__ = [
    "ParsedTMPage36",
    "TMPage36LogicalRow",
    "TMPage36Policy",
    "TMPage36Table",
    "load_tm_page36_policy",
    "parse_tm_page36",
]
