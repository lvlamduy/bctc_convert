from __future__ import annotations

from dataclasses import dataclass

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.text import normalize_text
from bctc_ai.evaluation.reader_outputs_v2 import (
    ParsedVLMPageV2,
    ParsedVLMRowV2,
    ParsedVLMTableV2,
    ReaderOutputV2Error,
    TableColumnRoles,
    VLMTableParserConfig,
    _compatible_inherited_roles,
    _expand_grid,
    _infer_roles_from_body,
    _infer_roles_from_header,
    _parse_table_rows,
    _SpanAwareTableParser,
)
from bctc_ai.validation.reader_agreement import ReaderRow


@dataclass(frozen=True)
class RowFragmentMerge:
    table_index: int
    label_source_grid_row: int
    value_source_grid_row: int
    source_row_ids: tuple[str, ...]
    rule: str
    value_cells_unmodified: bool


@dataclass(frozen=True)
class ParsedHTMLDocumentV2:
    page: ParsedVLMPageV2
    fragment_merges: tuple[RowFragmentMerge, ...]


class _TableRangeSpanParser(_SpanAwareTableParser):
    """Add table boundaries without changing the frozen Paddle parser."""

    def __init__(self) -> None:
        super().__init__()
        self.table_row_ranges: list[tuple[int, int]] = []
        self._table_start: int | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() == "table":
            if self._table_start is not None:
                raise ReaderOutputV2Error("nested HTML tables are not supported")
            self._table_start = len(self.rows)
        super().handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.casefold()
        super().handle_endtag(tag)
        if normalized != "table":
            return
        if self._table_start is None:
            raise ReaderOutputV2Error("HTML table closes without an opening tag")
        if self._row is not None or self._cell_parts is not None:
            raise ReaderOutputV2Error("HTML table closes inside an unfinished row or cell")
        self.table_row_ranges.append((self._table_start, len(self.rows)))
        self._table_start = None


def reassemble_adjacent_label_value_fragments(
    rows: tuple[ParsedVLMRowV2, ...],
    *,
    table_index: int,
) -> tuple[tuple[ParsedVLMRowV2, ...], tuple[RowFragmentMerge, ...]]:
    """Join only an explicit adjacent label-only/value-only row pair.

    Numeric cells move as an immutable tuple; their text, sign, observation and
    parsed value are never repaired or replaced. Other wrapped labels remain
    separate so ambiguous grouping still reaches review.
    """

    merged_rows: list[ParsedVLMRowV2] = []
    evidence: list[RowFragmentMerge] = []
    index = 0
    while index < len(rows):
        label_fragment = rows[index]
        if index + 1 >= len(rows):
            merged_rows.append(label_fragment)
            break
        value_fragment = rows[index + 1]
        label_row = label_fragment.row
        value_row = value_fragment.row
        adjacent = value_fragment.source_grid_row == label_fragment.source_grid_row + 1
        same_width = len(label_row.cells) == len(value_row.cells)
        label_only = bool(label_row.label) and all(
            cell.observation is ObservationKind.BLANK for cell in label_row.cells
        )
        value_only = (
            not value_row.label
            and value_row.note_reference is None
            and value_fragment.row_code is None
            and any(cell.observation is not ObservationKind.BLANK for cell in value_row.cells)
        )
        if not (adjacent and same_width and label_only and value_only):
            merged_rows.append(label_fragment)
            index += 1
            continue
        source_ids = label_row.source_row_ids + value_row.source_row_ids
        merged_rows.append(
            ParsedVLMRowV2(
                row=ReaderRow(
                    source_row_ids=source_ids,
                    label=label_row.label,
                    note_reference=label_row.note_reference,
                    cells=value_row.cells,
                ),
                row_code=label_fragment.row_code,
                source_grid_row=label_fragment.source_grid_row,
                warnings=tuple(
                    dict.fromkeys(
                        (
                            *label_fragment.warnings,
                            *value_fragment.warnings,
                            "adjacent label-only/value-only rows reassembled; values unchanged",
                        )
                    )
                ),
            )
        )
        evidence.append(
            RowFragmentMerge(
                table_index=table_index,
                label_source_grid_row=label_fragment.source_grid_row,
                value_source_grid_row=value_fragment.source_grid_row,
                source_row_ids=source_ids,
                rule="ADJACENT_LABEL_ONLY_THEN_VALUE_ONLY_SAME_WIDTH",
                value_cells_unmodified=True,
            )
        )
        index += 2
    return tuple(merged_rows), tuple(evidence)


def parse_html_document_v2(
    raw_html: str,
    config: VLMTableParserConfig,
    *,
    page_tag: str,
    input_path: str = "",
    context_text: str = "",
    table_bboxes: tuple[tuple[int, int, int, int], ...] | None = None,
    reassemble_fragments: bool = True,
) -> ParsedHTMLDocumentV2:
    """Parse span-aware HTML tables from a semantic reader without touching frozen readers."""

    if not page_tag or ":" in page_tag:
        raise ReaderOutputV2Error("page_tag must be non-empty and cannot contain a colon")
    html_parser = _TableRangeSpanParser()
    html_parser.feed(raw_html)
    html_parser.close()
    if html_parser._table_start is not None:
        raise ReaderOutputV2Error("HTML table is not closed")
    ranges = tuple(html_parser.table_row_ranges)
    if not ranges:
        raise ReaderOutputV2Error("semantic reader output contains no complete HTML table")
    if table_bboxes is None:
        table_bboxes = tuple((0, 0, 999, 999) for _ in ranges)
    if len(table_bboxes) != len(ranges):
        raise ReaderOutputV2Error(
            "HTML table count differs from the supplied table-box proposal count"
        )

    tables: list[ParsedVLMTableV2] = []
    merges: list[RowFragmentMerge] = []
    pending_header_roles: TableColumnRoles | None = None
    pending_header_table: int | None = None
    for table_index, ((start, end), bbox) in enumerate(
        zip(ranges, table_bboxes, strict=True), start=1
    ):
        if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
            raise ReaderOutputV2Error(f"table {table_index} has a degenerate bbox")
        nonempty_source_rows = [
            row
            for row in html_parser.rows[start:end]
            if any(normalize_text(cell.text) for cell in row)
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
        rows = _parse_table_rows(grid, roles, table_index, page_tag)
        table_merges: tuple[RowFragmentMerge, ...] = ()
        if reassemble_fragments:
            rows, table_merges = reassemble_adjacent_label_value_fragments(
                rows,
                table_index=table_index,
            )
            merges.extend(table_merges)
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
        if table_merges:
            warnings.append("explicit adjacent row fragments reassembled with unchanged values")
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
    return ParsedHTMLDocumentV2(
        page=ParsedVLMPageV2(
            input_path=input_path,
            context_text=normalize_text(context_text),
            tables=tuple(tables),
            unresolved_table_count=sum(table.roles is None for table in tables),
        ),
        fragment_merges=tuple(merges),
    )
