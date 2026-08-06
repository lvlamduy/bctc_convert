from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.text import normalize_text, retrieval_key
from bctc_ai.evaluation.financial_cells_v2 import parse_financial_number_strict_grouping
from bctc_ai.validation.reader_agreement import ReaderRow


class ReaderOutputV2Error(RuntimeError):
    pass


@dataclass(frozen=True)
class VLMTableParserConfig:
    minimum_value_columns: int
    maximum_header_scan_rows: int
    maximum_period_header_tokens: int
    minimum_body_numeric_density: float
    index_aliases: tuple[str, ...]
    label_aliases: tuple[str, ...]
    note_aliases: tuple[str, ...]
    period_context_aliases: tuple[str, ...]


@dataclass(frozen=True)
class TableColumnRoles:
    width: int
    index_column: int | None
    label_column: int
    note_column: int | None
    value_columns: tuple[int, ...]
    header_row_index: int | None
    inherited_from_table: int | None
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class ParsedVLMRowV2:
    row: ReaderRow
    row_code: str | None
    source_grid_row: int
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class ParsedVLMTableV2:
    table_index: int
    bbox: tuple[int, int, int, int]
    status: str
    roles: TableColumnRoles | None
    header: tuple[str, ...]
    context_rows: tuple[tuple[str, ...], ...]
    rows: tuple[ParsedVLMRowV2, ...]
    raw_grid: tuple[tuple[str, ...], ...]
    span_expansion_count: int
    warnings: tuple[str, ...]

    @property
    def reader_rows(self) -> tuple[ReaderRow, ...]:
        return tuple(item.row for item in self.rows)


@dataclass(frozen=True)
class ParsedVLMPageV2:
    input_path: str
    context_text: str
    tables: tuple[ParsedVLMTableV2, ...]
    unresolved_table_count: int

    @property
    def reader_rows(self) -> tuple[ReaderRow, ...]:
        return tuple(row for table in self.tables for row in table.reader_rows)


@dataclass(frozen=True)
class _HTMLCell:
    text: str
    rowspan: int
    colspan: int


class _SpanAwareTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[_HTMLCell]] = []
        self._row: list[_HTMLCell] | None = None
        self._cell_parts: list[str] | None = None
        self._rowspan = 1
        self._colspan = 1

    @staticmethod
    def _span(attrs: list[tuple[str, str | None]], name: str) -> int:
        raw = next((value for key, value in attrs if key.casefold() == name), None)
        if raw is None:
            return 1
        try:
            value = int(raw)
        except (TypeError, ValueError) as exc:
            raise ReaderOutputV2Error(f"invalid HTML {name}: {raw!r}") from exc
        if not 1 <= value <= 100:
            raise ReaderOutputV2Error(f"HTML {name} is outside the safe range: {value}")
        return value

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        if tag == "tr":
            if self._row is not None:
                raise ReaderOutputV2Error("nested HTML table rows are not supported")
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            if self._cell_parts is not None:
                raise ReaderOutputV2Error("nested HTML table cells are not supported")
            self._cell_parts = []
            self._rowspan = self._span(attrs, "rowspan")
            self._colspan = self._span(attrs, "colspan")
        elif tag == "br" and self._cell_parts is not None:
            self._cell_parts.append(" ")

    def handle_data(self, data: str) -> None:
        if self._cell_parts is not None:
            self._cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if tag in {"td", "th"} and self._cell_parts is not None and self._row is not None:
            self._row.append(
                _HTMLCell(
                    text=normalize_text(" ".join(self._cell_parts)),
                    rowspan=self._rowspan,
                    colspan=self._colspan,
                )
            )
            self._cell_parts = None
            self._rowspan = 1
            self._colspan = 1
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None


def load_vlm_table_parser_config(path: Path) -> VLMTableParserConfig:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("version") != 2:
        raise ReaderOutputV2Error("VLM table parser config must be version 2")
    minimum_value_columns = payload.get("minimum_value_columns")
    maximum_header_scan_rows = payload.get("maximum_header_scan_rows")
    maximum_period_header_tokens = payload.get("maximum_period_header_tokens")
    density = payload.get("minimum_body_numeric_density")
    if not isinstance(minimum_value_columns, int) or minimum_value_columns < 2:
        raise ReaderOutputV2Error("minimum_value_columns must be at least two")
    if not isinstance(maximum_header_scan_rows, int) or maximum_header_scan_rows < 1:
        raise ReaderOutputV2Error("maximum_header_scan_rows must be positive")
    if not isinstance(maximum_period_header_tokens, int) or maximum_period_header_tokens < 1:
        raise ReaderOutputV2Error("maximum_period_header_tokens must be positive")
    if not isinstance(density, (int, float)) or not 0 < float(density) <= 1:
        raise ReaderOutputV2Error("minimum_body_numeric_density must be in (0, 1]")
    raw_aliases = payload.get("column_header_aliases")
    if not isinstance(raw_aliases, dict):
        raise ReaderOutputV2Error("column_header_aliases must be a mapping")

    def aliases(name: str) -> tuple[str, ...]:
        values = raw_aliases.get(name)
        if not isinstance(values, list) or not values:
            raise ReaderOutputV2Error(f"missing {name} column aliases")
        normalized = tuple(retrieval_key(str(value)) for value in values)
        if any(not value for value in normalized):
            raise ReaderOutputV2Error(f"empty {name} column alias")
        return normalized

    raw_period_aliases = payload.get("period_context_aliases")
    if not isinstance(raw_period_aliases, list) or not raw_period_aliases:
        raise ReaderOutputV2Error("period_context_aliases must be a non-empty list")
    return VLMTableParserConfig(
        minimum_value_columns=minimum_value_columns,
        maximum_header_scan_rows=maximum_header_scan_rows,
        maximum_period_header_tokens=maximum_period_header_tokens,
        minimum_body_numeric_density=float(density),
        index_aliases=aliases("index"),
        label_aliases=aliases("label"),
        note_aliases=aliases("note"),
        period_context_aliases=tuple(retrieval_key(str(value)) for value in raw_period_aliases),
    )


def _expand_grid(rows: list[list[_HTMLCell]]) -> tuple[list[list[str]], int]:
    expanded: list[dict[int, str]] = []
    pending: dict[int, tuple[int, str]] = {}
    span_expansions = 0
    maximum_width = 0
    for source_row in rows:
        row: dict[int, str] = {}
        next_pending: dict[int, tuple[int, str]] = {}
        for column, (remaining, text) in pending.items():
            row[column] = text
            span_expansions += 1
            if remaining > 1:
                next_pending[column] = (remaining - 1, text)
        column = 0
        for cell in source_row:
            while column in row:
                column += 1
            for offset in range(cell.colspan):
                target = column + offset
                while target in row:
                    target += 1
                cell_text = cell.text if offset == 0 else ""
                row[target] = cell_text
                if offset:
                    span_expansions += 1
                if cell.rowspan > 1:
                    next_pending[target] = (cell.rowspan - 1, cell_text)
            column = max(row) + 1 if row else 0
        pending = next_pending
        maximum_width = max(maximum_width, max(row, default=-1) + 1)
        expanded.append(row)
    if pending:
        raise ReaderOutputV2Error("HTML rowspan extends beyond the final table row")
    return [
        [row.get(column, "") for column in range(maximum_width)] for row in expanded
    ], span_expansions


_YEAR = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")


def _matches_alias(text: str, aliases: tuple[str, ...]) -> bool:
    key = retrieval_key(text)
    return any(key == alias or alias in key for alias in aliases)


def _period_header_like(text: str, config: VLMTableParserConfig) -> bool:
    normalized = normalize_text(text)
    if not _YEAR.search(normalized):
        return False
    key = retrieval_key(text)
    if len(key.split()) > config.maximum_period_header_tokens:
        return False
    return (
        bool(_YEAR.fullmatch(normalized))
        or any(alias in key for alias in config.period_context_aliases)
        or bool(re.search(r"\d{1,2}\s*[/.-]\s*\d{1,2}", normalized))
    )


def _observed_financial(text: str) -> bool:
    return parse_financial_number_strict_grouping(text).observation in {
        ObservationKind.VALUE,
        ObservationKind.ZERO,
        ObservationKind.DASH,
    }


def _body_numeric_density(grid: list[list[str]], column: int, start: int) -> float:
    values = [
        row[column] for row in grid[start:] if column < len(row) and normalize_text(row[column])
    ]
    if not values:
        return 0.0
    return sum(_observed_financial(value) for value in values) / len(values)


def _first_alias_column(row: list[str], aliases: tuple[str, ...]) -> int | None:
    return next((index for index, value in enumerate(row) if _matches_alias(value, aliases)), None)


def _infer_roles_from_header(
    grid: list[list[str]], config: VLMTableParserConfig
) -> TableColumnRoles | None:
    candidates: list[tuple[int, tuple[int, ...]]] = []
    for row_index, row in enumerate(grid[: config.maximum_header_scan_rows]):
        period_columns = tuple(
            index for index, value in enumerate(row) if _period_header_like(value, config)
        )
        if len(period_columns) >= config.minimum_value_columns:
            candidates.append((row_index, period_columns))
    if not candidates:
        return None
    header_row_index, value_columns = min(candidates, key=lambda item: (-len(item[1]), item[0]))
    header = grid[header_row_index]
    first_value = min(value_columns)
    index_column = _first_alias_column(header, config.index_aliases)
    note_column = _first_alias_column(header, config.note_aliases)
    label_column = _first_alias_column(header, config.label_aliases)
    excluded = set(value_columns)
    if index_column is not None:
        excluded.add(index_column)
    if note_column is not None:
        excluded.add(note_column)
    candidates_before_values = [column for column in range(first_value) if column not in excluded]
    if label_column is None:
        if not candidates_before_values:
            return None
        label_column = max(
            candidates_before_values,
            key=lambda column: (
                sum(
                    bool(normalize_text(row[column])) and not _observed_financial(row[column])
                    for row in grid[header_row_index + 1 :]
                ),
                column,
            ),
        )
    if label_column >= first_value or label_column in value_columns:
        return None
    evidence = [f"period headers in row {header_row_index}"]
    if index_column is not None:
        evidence.append("index header alias")
    if note_column is not None:
        evidence.append("note header alias")
    evidence.append(
        "label header alias"
        if _first_alias_column(header, config.label_aliases) is not None
        else "text-density label column"
    )
    return TableColumnRoles(
        width=len(header),
        index_column=index_column,
        label_column=label_column,
        note_column=note_column,
        value_columns=value_columns,
        header_row_index=header_row_index,
        inherited_from_table=None,
        evidence=tuple(evidence),
    )


def _infer_roles_from_body(
    grid: list[list[str]], config: VLMTableParserConfig
) -> TableColumnRoles | None:
    if not grid:
        return None
    width = len(grid[0])
    dense = [
        column
        for column in range(width)
        if _body_numeric_density(grid, column, 0) >= config.minimum_body_numeric_density
    ]
    runs: list[list[int]] = []
    for column in dense:
        if runs and column == runs[-1][-1] + 1:
            runs[-1].append(column)
        else:
            runs.append([column])
    eligible = [run for run in runs if len(run) >= config.minimum_value_columns]
    if not eligible:
        return None
    value_columns = tuple(max(eligible, key=lambda run: (run[-1], len(run))))
    first_value = value_columns[0]
    if first_value < 1:
        return None
    label_column = max(
        range(first_value),
        key=lambda column: (
            sum(
                bool(normalize_text(row[column])) and not _observed_financial(row[column])
                for row in grid
            ),
            column,
        ),
    )
    return TableColumnRoles(
        width=width,
        index_column=None,
        label_column=label_column,
        note_column=None,
        value_columns=value_columns,
        header_row_index=None,
        inherited_from_table=None,
        evidence=(
            "rightmost consecutive body financial-density columns",
            "text-density label column",
        ),
    )


def _compatible_inherited_roles(
    roles: TableColumnRoles | None, width: int, table_index: int
) -> TableColumnRoles | None:
    if roles is None or roles.width != width:
        return None
    return TableColumnRoles(
        width=roles.width,
        index_column=roles.index_column,
        label_column=roles.label_column,
        note_column=roles.note_column,
        value_columns=roles.value_columns,
        header_row_index=None,
        inherited_from_table=table_index,
        evidence=("nearest preceding compatible table header",),
    )


def _parse_table_rows(
    grid: list[list[str]], roles: TableColumnRoles, table_index: int
) -> tuple[ParsedVLMRowV2, ...]:
    start = roles.header_row_index + 1 if roles.header_row_index is not None else 0
    parsed: list[ParsedVLMRowV2] = []
    for grid_index, raw in enumerate(grid[start:], start=start):
        label = normalize_text(raw[roles.label_column])
        row_code = (
            normalize_text(raw[roles.index_column]) or None
            if roles.index_column is not None
            else None
        )
        note = (
            normalize_text(raw[roles.note_column]) or None
            if roles.note_column is not None
            else None
        )
        cells = tuple(
            parse_financial_number_strict_grouping(raw[column]) for column in roles.value_columns
        )
        if (
            not label
            and not note
            and not row_code
            and all(cell.observation is ObservationKind.BLANK for cell in cells)
        ):
            continue
        warnings = []
        if not label:
            warnings.append("row has structural or financial evidence but no label")
        if any(cell.observation is ObservationKind.INVALID for cell in cells):
            warnings.append("one or more value cells are invalid")
        parsed.append(
            ParsedVLMRowV2(
                row=ReaderRow(
                    source_row_ids=(f"vlm-table-{table_index}:grid-row-{grid_index:04d}",),
                    label=label,
                    note_reference=note,
                    cells=cells,
                ),
                row_code=row_code,
                source_grid_row=grid_index,
                warnings=tuple(warnings),
            )
        )
    return tuple(parsed)


def parse_paddle_vl_page_v2(path: Path, config: VLMTableParserConfig) -> ParsedVLMPageV2:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ReaderOutputV2Error(f"cannot read PaddleOCR-VL result: {path}") from exc
    blocks = payload.get("parsing_res_list")
    if not isinstance(blocks, list):
        raise ReaderOutputV2Error("PaddleOCR-VL result has no parsing_res_list")
    tables: list[ParsedVLMTableV2] = []
    context: list[str] = []
    pending_header_roles: TableColumnRoles | None = None
    pending_header_table: int | None = None
    table_index = 0
    for block in blocks:
        if not isinstance(block, dict):
            raise ReaderOutputV2Error("PaddleOCR-VL parsing block is not an object")
        if block.get("block_label") != "table":
            content = normalize_text(str(block.get("block_content", "")))
            if content:
                context.append(content)
            continue
        table_index += 1
        raw_bbox = block.get("block_bbox")
        if not isinstance(raw_bbox, list) or len(raw_bbox) != 4:
            raise ReaderOutputV2Error(f"table {table_index} has no four-coordinate bbox")
        bbox = tuple(int(value) for value in raw_bbox)
        if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
            raise ReaderOutputV2Error(f"table {table_index} has a degenerate bbox")
        html_parser = _SpanAwareTableParser()
        html_parser.feed(str(block.get("block_content", "")))
        nonempty_source_rows = [
            row for row in html_parser.rows if any(normalize_text(cell.text) for cell in row)
        ]
        if not nonempty_source_rows:
            pending_header_roles = None
            pending_header_table = None
            tables.append(
                ParsedVLMTableV2(
                    table_index=table_index,
                    bbox=bbox,
                    status="UNRESOLVED_EMPTY_TABLE",
                    roles=None,
                    header=(),
                    context_rows=(),
                    rows=(),
                    raw_grid=(),
                    span_expansion_count=0,
                    warnings=("table contains no non-empty HTML row",),
                )
            )
            continue
        grid, span_count = _expand_grid(nonempty_source_rows)
        roles = _infer_roles_from_header(grid, config)
        if roles is None:
            roles = _compatible_inherited_roles(
                pending_header_roles,
                len(grid[0]),
                pending_header_table or 0,
            )
            if roles is None:
                roles = _infer_roles_from_body(grid, config)
        if roles is None:
            pending_header_roles = None
            pending_header_table = None
            tables.append(
                ParsedVLMTableV2(
                    table_index=table_index,
                    bbox=bbox,
                    status="UNRESOLVED_COLUMN_ROLES",
                    roles=None,
                    header=(),
                    context_rows=(),
                    rows=(),
                    raw_grid=tuple(tuple(row) for row in grid),
                    span_expansion_count=span_count,
                    warnings=("column roles could not be inferred without guessing",),
                )
            )
            continue
        header = tuple(grid[roles.header_row_index]) if roles.header_row_index is not None else ()
        context_end = roles.header_row_index if roles.header_row_index is not None else 0
        context_rows = tuple(tuple(row) for row in grid[:context_end])
        for row in context_rows:
            content = normalize_text(" ".join(cell for cell in row if cell))
            if content:
                context.append(content)
        if roles.header_row_index is not None:
            header_label = normalize_text(header[roles.label_column])
            if header_label and not _matches_alias(header_label, config.label_aliases):
                context.append(header_label)
        rows = _parse_table_rows(grid, roles, table_index)
        status = "HEADER_ONLY" if not rows else "PARSED"
        if status == "HEADER_ONLY" and roles.inherited_from_table is None:
            pending_header_roles = roles
            pending_header_table = table_index
        else:
            pending_header_roles = None
            pending_header_table = None
        warnings = []
        if roles.inherited_from_table is not None:
            warnings.append("column roles inherited from the nearest compatible preceding table")
        if span_count:
            warnings.append("HTML row/column spans expanded without splitting cell text")
        tables.append(
            ParsedVLMTableV2(
                table_index=table_index,
                bbox=bbox,
                status=status,
                roles=roles,
                header=header,
                context_rows=context_rows,
                rows=rows,
                raw_grid=tuple(tuple(row) for row in grid),
                span_expansion_count=span_count,
                warnings=tuple(warnings),
            )
        )
    if not tables:
        raise ReaderOutputV2Error("PaddleOCR-VL result contains no table block")
    return ParsedVLMPageV2(
        input_path=str(payload.get("input_path", "")),
        context_text=normalize_text(" ".join(context)),
        tables=tuple(tables),
        unresolved_table_count=sum(table.roles is None for table in tables),
    )


def table_roles_to_dict(roles: TableColumnRoles | None) -> dict[str, Any] | None:
    if roles is None:
        return None
    return {
        "width": roles.width,
        "index_column": roles.index_column,
        "label_column": roles.label_column,
        "note_column": roles.note_column,
        "value_columns": list(roles.value_columns),
        "header_row_index": roles.header_row_index,
        "inherited_from_table": roles.inherited_from_table,
        "evidence": list(roles.evidence),
    }
