from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from pathlib import Path

import yaml

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import normalize_text
from bctc_ai.evaluation.word_box_rows import (
    OCRLine,
    WordBoxReconstructionError,
    _read_source_image,
    _source_ids,
)
from bctc_ai.evaluation.word_box_rows_v2 import (
    GeometryRowProposalV2,
    ParsedGeometryPageV2,
    geometry_row_v2_to_dict,
)
from bctc_ai.evaluation.word_box_rows_v3 import (
    WordBoxReconstructionV3Config,
    _blank_or_dash_cells_v3,
    load_word_box_reconstruction_v3_config,
    parse_ppocrv6_word_box_page_v3,
)
from bctc_ai.validation.reader_agreement import ReaderRow


@dataclass(frozen=True)
class WordBoxReconstructionV4Config:
    base: WordBoxReconstructionV3Config
    source_path: Path
    maximum_note_to_value_anchor_gap_line_heights: float
    require_same_page_source_geometry: bool
    forbid_label_semantics_as_split_feature: bool
    forbid_numeric_magnitude_as_split_feature: bool
    forbid_schema_history_or_review: bool


def load_word_box_reconstruction_v4_config(path: Path) -> WordBoxReconstructionV4Config:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise WordBoxReconstructionError(f"cannot load word-box v4 config: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 4
        or payload.get("policy") != "NOTE_SEPARATED_STRUCTURAL_ANCHOR_V4"
    ):
        raise WordBoxReconstructionError("word-box reconstruction config must be version 4")
    base_name = payload.get("base_config")
    if not isinstance(base_name, str) or Path(base_name).name != base_name:
        raise WordBoxReconstructionError("word-box v4 base_config path is invalid")
    base_path = (path.parent / base_name).resolve()
    if not base_path.is_file() or base_path.parent != path.parent.resolve():
        raise WordBoxReconstructionError("word-box v4 base_config is absent or escapes")
    if sha256_file(base_path) != payload.get("base_config_sha256"):
        raise WordBoxReconstructionError("word-box v4 base_config hash drifted")
    gap = payload.get("maximum_note_to_value_anchor_gap_line_heights")
    if (
        isinstance(gap, bool)
        or not isinstance(gap, (int, float))
        or not 0.20 <= float(gap) <= 0.75
    ):
        raise WordBoxReconstructionError("word-box v4 note/value gap bound is unsafe")
    switches = (
        "require_same_page_source_geometry",
        "forbid_label_semantics_as_split_feature",
        "forbid_numeric_magnitude_as_split_feature",
        "forbid_schema_history_or_review",
    )
    if any(payload.get(name) is not True for name in switches):
        raise WordBoxReconstructionError("word-box v4 safety switch drifted")
    return WordBoxReconstructionV4Config(
        base=load_word_box_reconstruction_v3_config(base_path),
        source_path=path.resolve(),
        maximum_note_to_value_anchor_gap_line_heights=float(gap),
        **{name: True for name in switches},
    )


def parse_ppocrv6_word_box_page_v4(
    result_path: Path,
    config: WordBoxReconstructionV4Config,
    *,
    page_tag: str,
    source_image_path: Path | None = None,
) -> ParsedGeometryPageV2:
    parsed = parse_ppocrv6_word_box_page_v3(
        result_path,
        config.base,
        page_tag=page_tag,
        source_image_path=source_image_path,
    )
    try:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WordBoxReconstructionError(f"cannot read PP-OCRv6 result: {result_path}") from exc
    raw_texts = payload.get("rec_texts")
    raw_scores = payload.get("rec_scores")
    raw_boxes = payload.get("rec_boxes")
    if not all(isinstance(value, list) for value in (raw_texts, raw_scores, raw_boxes)):
        raise WordBoxReconstructionError("PP-OCRv6 result lacks text, score, or box axes")
    if len({len(raw_texts), len(raw_scores), len(raw_boxes)}) != 1:
        raise WordBoxReconstructionError("PP-OCRv6 result axes have different lengths")
    source_lines: dict[int, OCRLine] = {}
    for index, (text, score, box) in enumerate(
        zip(raw_texts, raw_scores, raw_boxes, strict=True)
    ):
        if not isinstance(box, list) or len(box) != 4:
            raise WordBoxReconstructionError(f"line {index} has no four-coordinate box")
        parsed_box = tuple(float(value) for value in box)
        if parsed_box[2] <= parsed_box[0] or parsed_box[3] <= parsed_box[1]:
            raise WordBoxReconstructionError(f"line {index} has a degenerate box")
        if float(score) >= float(config.base.base.base["minimum_line_score"]):
            source_lines[index] = OCRLine(
                index, normalize_text(str(text)), float(score), parsed_box
            )

    source_image = _read_source_image(source_image_path)
    rows: list[GeometryRowProposalV2] = []
    for proposal in parsed.rows:
        label_indices = proposal.label_line_indices
        note_indices = proposal.note_line_indices
        value_indices = tuple(
            index for axis_indices in proposal.value_line_indices for index in axis_indices
        )
        if (
            len(label_indices) < 2
            or not note_indices
            or not value_indices
            or proposal.index_line_indices
            or proposal.row_code is not None
        ):
            rows.append(proposal)
            continue
        try:
            label_lines = [source_lines[index] for index in label_indices]
            note_lines = [source_lines[index] for index in note_indices]
            value_lines = [source_lines[index] for index in value_indices]
        except KeyError as exc:
            raise WordBoxReconstructionError(
                "V4 split source line was filtered after V3 reconstruction"
            ) from exc
        note_center = statistics.fmean(line.y_center for line in note_lines)
        value_center = statistics.fmean(line.y_center for line in value_lines)
        gap = abs(note_center - value_center)
        if gap <= (
            parsed.line_height * config.maximum_note_to_value_anchor_gap_line_heights
        ):
            rows.append(proposal)
            continue
        note_labels = [
            line
            for line in label_lines
            if abs(line.y_center - note_center) < abs(line.y_center - value_center)
        ]
        value_labels = [line for line in label_lines if line not in note_labels]
        if not note_labels or not value_labels:
            rows.append(proposal)
            continue

        empty_axis_lines = [[] for _axis in parsed.axes]
        note_cells, note_visual = _blank_or_dash_cells_v3(
            parsed.axes,
            empty_axis_lines,
            source_image=source_image,
            source_image_path=source_image_path,
            anchor_center=note_center,
            line_height=parsed.line_height,
            base_config=config.base.base.base,
        )
        note_warnings = ["distant note row separated before following value anchor"]
        if any(evidence is not None for evidence in note_visual):
            note_warnings.append(
                "OCR-blank cell recovered as DASH from constrained pixel evidence"
            )
        rows.append(
            GeometryRowProposalV2(
                row=ReaderRow(
                    source_row_ids=_source_ids(page_tag, note_labels + note_lines),
                    label=normalize_text(" ".join(line.text for line in note_labels)),
                    note_reference=normalize_text(
                        " ".join(line.text for line in note_lines)
                    )
                    or None,
                    cells=note_cells,
                ),
                row_code=None,
                y_anchor=note_center,
                index_line_indices=(),
                label_line_indices=tuple(line.index for line in note_labels),
                note_line_indices=tuple(line.index for line in note_lines),
                value_line_indices=tuple(() for _axis in parsed.axes),
                visual_cell_evidence=note_visual,
                warnings=tuple(note_warnings),
            )
        )
        per_axis_source_lines = [
            [source_lines[index] for index in axis_indices]
            for axis_indices in proposal.value_line_indices
        ]
        rows.append(
            GeometryRowProposalV2(
                row=ReaderRow(
                    source_row_ids=_source_ids(
                        page_tag,
                        value_labels
                        + [line for axis_lines in per_axis_source_lines for line in axis_lines],
                    ),
                    label=normalize_text(" ".join(line.text for line in value_labels)),
                    note_reference=None,
                    cells=proposal.row.cells,
                ),
                row_code=None,
                y_anchor=proposal.y_anchor,
                index_line_indices=(),
                label_line_indices=tuple(line.index for line in value_labels),
                note_line_indices=(),
                value_line_indices=proposal.value_line_indices,
                visual_cell_evidence=proposal.visual_cell_evidence,
                warnings=("value row separated from distant note anchor",),
            )
        )
    rows.sort(key=lambda row: row.y_anchor)
    if any(
        cell.observation is ObservationKind.INVALID for row in rows for cell in row.row.cells
    ):
        # Preserve V3 invalid observations, but never let the V4 split create one.
        v3_invalid = sum(
            cell.observation is ObservationKind.INVALID
            for row in parsed.rows
            for cell in row.row.cells
        )
        v4_invalid = sum(
            cell.observation is ObservationKind.INVALID for row in rows for cell in row.row.cells
        )
        if v4_invalid > v3_invalid:
            raise WordBoxReconstructionError("V4 note-row split introduced an invalid cell")
    return ParsedGeometryPageV2(
        input_path=parsed.input_path,
        axes=parsed.axes,
        note_right_edge=parsed.note_right_edge,
        index_band=parsed.index_band,
        table_bbox=parsed.table_bbox,
        rows=tuple(rows),
        trailing_context_rows=parsed.trailing_context_rows,
        line_height=parsed.line_height,
        unassigned_numeric_line_indices=parsed.unassigned_numeric_line_indices,
        excluded_after_table_line_indices=parsed.excluded_after_table_line_indices,
    )


geometry_row_v4_to_dict = geometry_row_v2_to_dict


__all__ = [
    "WordBoxReconstructionV4Config",
    "geometry_row_v4_to_dict",
    "load_word_box_reconstruction_v4_config",
    "parse_ppocrv6_word_box_page_v4",
]
