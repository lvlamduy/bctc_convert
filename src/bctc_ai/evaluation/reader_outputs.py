from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.text import normalize_text, parse_financial_number
from bctc_ai.mapping.scope import ScopePolicy, classify_mapping_scopes
from bctc_ai.validation.reader_agreement import ReaderRow, align_ordered_reader_rows


class ReaderOutputError(RuntimeError):
    pass


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        del attrs
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(normalize_text(" ".join(self._cell)))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None


@dataclass(frozen=True)
class ParsedVLMTable:
    table_index: int
    bbox: tuple[int, int, int, int]
    header: tuple[str, ...]
    rows: tuple[ReaderRow, ...]
    raw_rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class ParsedVLMPage:
    input_path: str
    context_text: str
    tables: tuple[ParsedVLMTable, ...]


def parse_paddle_vl_page(path: Path) -> ParsedVLMPage:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ReaderOutputError(f"cannot read PaddleOCR-VL result: {path}") from exc
    blocks = payload.get("parsing_res_list")
    if not isinstance(blocks, list):
        raise ReaderOutputError("PaddleOCR-VL result has no parsing_res_list")
    context = []
    tables = []
    for table_index, block in enumerate(
        (item for item in blocks if item.get("block_label") == "table"), start=1
    ):
        parser = _TableParser()
        parser.feed(str(block.get("block_content", "")))
        nonempty_rows = [row for row in parser.rows if any(normalize_text(cell) for cell in row)]
        if len(nonempty_rows) < 2:
            raise ReaderOutputError(f"table {table_index} has no header and body")
        width = max(len(row) for row in nonempty_rows)
        if width < 3:
            raise ReaderOutputError(f"table {table_index} has fewer than three columns")
        padded = [tuple(row + [""] * (width - len(row))) for row in nonempty_rows]
        header = padded[0]
        rows = tuple(
            ReaderRow(
                source_row_ids=(f"vlm-table-{table_index}:row-{row_index:04d}",),
                label=row[0],
                note_reference=row[1] or None,
                cells=tuple(parse_financial_number(cell) for cell in row[2:]),
            )
            for row_index, row in enumerate(padded[1:], start=1)
        )
        raw_bbox = block.get("block_bbox")
        if not isinstance(raw_bbox, list) or len(raw_bbox) != 4:
            raise ReaderOutputError(f"table {table_index} has no four-coordinate bbox")
        tables.append(
            ParsedVLMTable(
                table_index=table_index,
                bbox=tuple(int(value) for value in raw_bbox),
                header=header,
                rows=rows,
                raw_rows=tuple(padded[1:]),
            )
        )
    for block in blocks:
        if block.get("block_label") != "table":
            content = normalize_text(str(block.get("block_content", "")))
            if content:
                context.append(content)
    if not tables:
        raise ReaderOutputError("PaddleOCR-VL result contains no table")
    return ParsedVLMPage(
        input_path=str(payload.get("input_path", "")),
        context_text=normalize_text(" ".join(context)),
        tables=tuple(tables),
    )


def reader_row_to_dict(row: ReaderRow) -> dict[str, object]:
    return {
        "source_row_ids": list(row.source_row_ids),
        "label": row.label,
        "note_reference": row.note_reference,
        "cells": [
            {
                "raw_text": cell.raw_text,
                "normalized_text": cell.normalized_text,
                "value": str(cell.value) if cell.value is not None else None,
                "observation": cell.observation.value,
                "sign_evidence": cell.sign_evidence,
                "reason": cell.reason,
            }
            for cell in row.cells
        ],
    }


def reader_row_from_dict(record: dict[str, object]) -> ReaderRow:
    raw_cells = record.get("cells")
    if not isinstance(raw_cells, list):
        raise ReaderOutputError("serialized reader row has no cells")
    cells = tuple(parse_financial_number(str(cell.get("raw_text", ""))) for cell in raw_cells)
    for raw_cell, parsed in zip(raw_cells, cells, strict=True):
        if raw_cell.get("observation") != parsed.observation.value:
            raise ReaderOutputError("serialized reader cell observation drift")
        expected_value = raw_cell.get("value")
        actual_value = str(parsed.value) if parsed.value is not None else None
        if expected_value != actual_value:
            raise ReaderOutputError("serialized reader cell value drift")
    source_ids = record.get("source_row_ids")
    if not isinstance(source_ids, list) or not source_ids:
        raise ReaderOutputError("serialized reader row has no source IDs")
    return ReaderRow(
        source_row_ids=tuple(str(value) for value in source_ids),
        label=str(record.get("label", "")),
        note_reference=(
            str(record["note_reference"]) if record.get("note_reference") is not None else None
        ),
        cells=cells,
    )


def _cell_comparison(
    reference,
    candidate,
    *,
    reference_present: bool,
    candidate_present: bool,
) -> dict[str, object]:
    exact = (
        reference.observation is candidate.observation and reference.value == candidate.value
    )
    return {
        "reference_raw": reference.raw_text,
        "candidate_raw": candidate.raw_text,
        "reference_observation": reference.observation.value,
        "candidate_observation": candidate.observation.value,
        "reference_value": str(reference.value) if reference.value is not None else None,
        "candidate_value": str(candidate.value) if candidate.value is not None else None,
        "reference_reason": reference.reason,
        "candidate_reason": candidate.reason,
        "reference_present": reference_present,
        "candidate_present": candidate_present,
        "exact": exact,
    }


def _escalation(record: dict[str, object]) -> str:
    if record["action"] not in {"MATCH", "MERGE_CANDIDATE"}:
        return "TABLE_RECONSTRUCTION_REVIEW"
    if not record.get("cell_width_exact", True):
        return "CELL_AXIS_RECONSTRUCTION_AND_REREAD"
    cells = record.get("cells", [])
    if any(cell["candidate_observation"] == ObservationKind.INVALID.value for cell in cells):
        return "TARGETED_NUMERIC_REREAD_INVALID_CELL"
    if any(not cell["exact"] for cell in cells):
        return "TARGETED_NUMERIC_REREAD_DISAGREEMENT"
    if record.get("note_exact") is False:
        return "NOTE_REFERENCE_REREAD"
    if record.get("label_exact") is False:
        return "LABEL_REREAD_OR_STRUCTURAL_REVIEW"
    return "CORROBORATED_NO_CONFIDENCE_PROMOTION"


def compare_reader_rows(
    reference_rows: tuple[ReaderRow, ...],
    candidate_rows: tuple[ReaderRow, ...],
    *,
    statement_type: str,
    scope_policy: ScopePolicy,
    candidate_context_text: str = "",
) -> dict[str, object]:
    alignment = align_ordered_reader_rows(reference_rows, candidate_rows)
    records = []
    for step in alignment:
        record: dict[str, object] = {
            "action": step.action,
            "reference_indices": list(step.reference_indices),
            "candidate_indices": list(step.candidate_indices),
            "reference_label": step.reference.label if step.reference else None,
            "candidate_label": step.candidate.label if step.candidate else None,
            "semantic_similarity": step.semantic_similarity,
            "label_exact": step.label_exact,
            "semantic_key_exact": step.semantic_key_exact,
            "confidence_effect": "NO_PROMOTION",
        }
        if (
            step.action in {"MATCH", "MERGE_CANDIDATE"}
            and step.reference is not None
            and step.candidate is not None
        ):
            width = max(len(step.reference.cells), len(step.candidate.cells))
            cells = []
            for index in range(width):
                reference_cell = (
                    step.reference.cells[index]
                    if index < len(step.reference.cells)
                    else parse_financial_number(None)
                )
                candidate_cell = (
                    step.candidate.cells[index]
                    if index < len(step.candidate.cells)
                    else parse_financial_number(None)
                )
                cells.append(
                    _cell_comparison(
                        reference_cell,
                        candidate_cell,
                        reference_present=index < len(step.reference.cells),
                        candidate_present=index < len(step.candidate.cells),
                    )
                )
            reference_has_observation = any(
                cell.observation is not ObservationKind.BLANK for cell in step.reference.cells
            )
            candidate_has_observation = any(
                cell.observation is not ObservationKind.BLANK for cell in step.candidate.cells
            )
            record.update(
                reference_note=step.reference.note_reference,
                candidate_note=step.candidate.note_reference,
                note_exact=step.reference.note_reference == step.candidate.note_reference,
                cell_width_exact=(
                    len(step.reference.cells) == len(step.candidate.cells)
                    or not (reference_has_observation or candidate_has_observation)
                ),
                cells=cells,
            )
        record["escalation"] = _escalation(record)
        records.append(record)

    matched = [
        record
        for record in records
        if record["action"] in {"MATCH", "MERGE_CANDIDATE"}
        and record["label_exact"] is not None
    ]
    reference_financial_indices = {
        index
        for index, row in enumerate(reference_rows)
        if any(cell.observation is not ObservationKind.BLANK for cell in row.cells)
    }
    covered_reference_financial_indices = {
        int(index)
        for record in matched
        for index in record["reference_indices"]
        if int(index) in reference_financial_indices
    }
    financial = [
        record
        for record in matched
        if any(
            cell["reference_observation"] != ObservationKind.BLANK.value
            for cell in record.get("cells", [])
        )
    ]
    cells = [cell for record in financial for cell in record.get("cells", [])]
    reference_cells = [cell for cell in cells if cell["reference_present"]]
    note_records = [
        record
        for record in matched
        if record.get("reference_note") is not None or record.get("candidate_note") is not None
    ]
    scopes = classify_mapping_scopes(
        [(statement_type, row.label) for row in candidate_rows],
        scope_policy,
        initial_section_label=candidate_context_text,
    )
    scope_records = [
        {
            "row_id": row.source_row_ids[0],
            "label": row.label,
            "allowed": decision.allowed,
            "detected_section": decision.detected_section,
            "inherited_from_section": decision.inherited_from_section,
            "reason": decision.reason,
        }
        for row, decision in zip(candidate_rows, scopes, strict=True)
    ]
    escalations = Counter(str(record["escalation"]) for record in records)
    return {
        "counts": {
            "reference_rows": len(reference_rows),
            "candidate_rows": len(candidate_rows),
            "alignment_actions": dict(
                sorted(Counter(str(record["action"]) for record in records).items())
            ),
            "structurally_comparable_rows": len(matched),
            "source_exact_labels": sum(record["label_exact"] is True for record in matched),
            "semantic_key_exact_labels": sum(
                record["semantic_key_exact"] is True for record in matched
            ),
            "reference_financial_rows": len(reference_financial_indices),
            "covered_reference_financial_rows": len(
                covered_reference_financial_indices
            ),
            "exact_reference_financial_rows": sum(
                record.get("cell_width_exact") is True
                and all(
                    cell["exact"]
                    for cell in record.get("cells", [])
                    if cell["reference_present"]
                )
                for record in financial
            ),
            "reference_financial_cells": sum(
                len(reference_rows[index].cells) for index in reference_financial_indices
            ),
            "compared_reference_financial_cells": len(reference_cells),
            "exact_reference_financial_cells": sum(
                cell["exact"] for cell in reference_cells
            ),
            "candidate_invalid_cells": sum(
                cell["candidate_observation"] == ObservationKind.INVALID.value for cell in cells
            ),
            "note_rows": len(note_records),
            "exact_note_references": sum(record.get("note_exact") is True for record in note_records),
            "scope_allowed_candidate_rows": sum(record["allowed"] for record in scope_records),
            "scope_excluded_candidate_rows": sum(not record["allowed"] for record in scope_records),
            "escalations": dict(sorted(escalations.items())),
        },
        "scope": scope_records,
        "alignment": records,
    }
