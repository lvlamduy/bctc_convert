"""Original-source bridge for notes tables: normalized SQL coordinates proven against the ORIGINAL page BLOB.

The normalized store (gemini_financial_page_store_v1) was built from the VALIDATED page JSON. A
pinned database authenticates its bytes, not that every normalized table/row/column/cell is a
lossless source coordinate. For each loaded table (NotesSource.load_tables):

1. the page ORIGINAL is loaded once through the existing authenticated loader
   (gemini_income_tax_source_page_loader_v1: BLOB SHA, content-ID replay, canonical two-LF
   serialization, provenance, proven lossless redundant-TEXT-column removal only), and the
   returned logical name / source SHA / physical page are bound to the selected corpus page;
2. the SQL table is compared typed-exactly (raw stored JSON, before any null/string filtering)
   with the freshly validated object - section/table metadata and ordinals, column headers/kinds,
   row labels/paths/kinds, a recomputed parent edge, and every positional cell including nulls;
3. SQL column cN is mapped to the ORIGINAL column ordinal, admitting only the loader-proven
   redundant TEXT column shift; any other difference between original and validated holds.

The bridge proves source coordinates only - never role, unit, period, basis or membership.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from bctc_ai.source_structure.contracts_v1 import same_typed_json_v1 as _same

BRIDGE_VERSION = "NOTES_ORIGINAL_SOURCE_BRIDGE_V1"
EXACT = "EXACT"
EXACT_SHIFT = "EXACT_WITH_PROVEN_TEXT_COLUMN_SHIFT"


def _sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def recompute_parents_v1(rows: list[dict[str, Any]]) -> dict[str, str | None]:
    """The store's own parent rule, recomputed from raw rows: one exact hierarchy-path parent."""

    result: dict[str, str | None] = {}
    for index, row in enumerate(rows):
        path = row.get("hierarchy_path_exact") or []
        parent_label = path[-2] if len(path) > 1 else None
        candidates = [i for i, candidate in enumerate(rows) if i != index and _same(candidate.get("label_exact"), parent_label)
                      and _same(candidate.get("hierarchy_path_exact"), path[:-1])]
        result[f"r{index + 1}"] = f"r{candidates[0] + 1}" if len(candidates) == 1 else None
    return result


def _fail(reason: str, **extra) -> dict[str, Any]:
    return {"bridge_version": BRIDGE_VERSION, "status": "MISMATCH:" + reason, **extra}


def bridge_table_v1(table, validated_page: dict[str, Any], original_page: dict[str, Any],
                    changed_tables: list[dict[str, Any]]) -> dict[str, Any]:
    """Prove one SQL table (a kernel NoteTable) against its validated and ORIGINAL page objects."""

    ms, mt = re.fullmatch(r"s([1-9][0-9]*)", table.section_id), re.fullmatch(r"t([1-9][0-9]*)", table.table_id)
    if not ms or not mt or (table.section_order, table.table_order) != (int(ms.group(1)) - 1, int(mt.group(1)) - 1):
        return _fail("NORMALIZED_IDS")
    s, t = int(ms.group(1)), int(mt.group(1))
    base = {"page_json_version_id": table.page_json_version_id, "section_ordinal": s, "table_ordinal": t}
    try:
        vsec, osec = validated_page["sections"][s - 1], original_page["sections"][s - 1]
        vtab, otab = vsec["tables"][t - 1], osec["tables"][t - 1]
    except (KeyError, IndexError, TypeError):
        return _fail("COORDINATE_ABSENT", **base)
    if not _same([vsec.get("title_exact"), vsec.get("content_kind"), vsec.get("narratives_exact")],
                 [table.section_title, table.content_kind, table.narratives_raw]):
        return _fail("SECTION_METADATA", **base)
    if not _same([vtab.get("title_exact"), vtab.get("unit_exact"), vtab.get("continuation")],
                 [table.table_title, table.unit_exact, table.continuation]):
        return _fail("TABLE_METADATA", **base)
    vcols, vrows = vtab.get("columns"), vtab.get("rows")
    if type(vcols) is not list or type(vrows) is not list:
        return _fail("AXIS_ABSENT", **base)
    columns = sorted(table.columns, key=lambda c: c.ordinal)
    if len(columns) != len(vcols):
        return _fail("COLUMN_COUNT", **base)
    for index, (column, vcol) in enumerate(zip(columns, vcols)):
        if (column.column_id, column.ordinal) != (f"c{index + 1}", index) \
                or not _same([column.header_raw, column.value_kind], [vcol.get("header_path_exact"), vcol.get("value_kind")]):
            return _fail("COLUMN_IDENTITY", column_id=column.column_id, **base)
    rows = sorted(table.rows, key=lambda r: r.order)
    if len(rows) != len(vrows):
        return _fail("ROW_COUNT", **base)
    parents = recompute_parents_v1(vrows)
    per_row_cells: dict[str, int] = {}
    for row_id, _column in table.cells:
        per_row_cells[row_id] = per_row_cells.get(row_id, 0) + 1
    if set(per_row_cells) - {row.row_id for row in rows}:
        return _fail("CELL_WITHOUT_ROW", **base)
    for index, (row, vrow) in enumerate(zip(rows, vrows)):
        if (row.row_id, row.order) != (f"r{index + 1}", index) or not _same(
                [row.label, row.hierarchy_raw, row.kind],
                [vrow.get("label_exact"), vrow.get("hierarchy_path_exact"), vrow.get("row_kind")]):
            return _fail("ROW_IDENTITY", row_id=row.row_id, **base)
        if row.parent_row_id != parents[row.row_id]:
            return _fail("PARENT_EDGE_NOT_RECOMPUTED", row_id=row.row_id, **base)
        values = vrow.get("values_exact")
        if type(values) is not list or len(values) != len(vcols) or per_row_cells.get(row.row_id, 0) != len(values):
            return _fail("CELL_COUNT", row_id=row.row_id, **base)
        for column_index, value in enumerate(values):
            cell = table.cells.get((row.row_id, f"c{column_index + 1}"))
            if cell is None or not _same(cell[0], value):
                return _fail("CELL_VALUE", row_id=row.row_id, column_id=f"c{column_index + 1}", **base)
    shifts = [c for c in changed_tables if c.get("section_ordinal") == s and c.get("table_ordinal") == t]
    if len(shifts) > 1:
        return _fail("MULTIPLE_COLUMN_SHIFTS", **base)
    removed = shifts[0].get("redundant_text_column_ordinal") if shifts else None
    ocols, orows = otab.get("columns"), otab.get("rows")
    if removed is None:
        if not _same(otab, vtab):
            return _fail("UNPROVEN_ORIGINAL_TRANSFORM", **base)
        column_map = {f"c{i + 1}": i + 1 for i in range(len(vcols))}
    else:
        if type(removed) is not int or type(ocols) is not list or type(orows) is not list \
                or not 1 <= removed <= len(ocols) or len(ocols) != len(vcols) + 1 \
                or ocols[removed - 1].get("value_kind") != "TEXT" or len(orows) != len(vrows):
            return _fail("TEXT_SHIFT_NOT_PROVEN", **base)
        column_map = {f"c{i + 1}": (i + 1 if i + 1 < removed else i + 2) for i in range(len(vcols))}
        if any(not _same(ocols[column_map[f"c{i + 1}"] - 1], vcol) for i, vcol in enumerate(vcols)) \
                or not _same({k: v for k, v in otab.items() if k not in ("columns", "rows")},
                             {k: v for k, v in vtab.items() if k not in ("columns", "rows")}):
            return _fail("TEXT_SHIFT_COLUMN_DIFFERS", **base)
        for vrow, orow in zip(vrows, orows):
            ovalues = orow.get("values_exact")
            if not _same({k: v for k, v in orow.items() if k != "values_exact"},
                         {k: v for k, v in vrow.items() if k != "values_exact"}) \
                    or type(ovalues) is not list or len(ovalues) != len(vrow["values_exact"]) + 1 \
                    or any(not _same(ovalues[column_map[f"c{i + 1}"] - 1], value) for i, value in enumerate(vrow["values_exact"])):
                return _fail("TEXT_SHIFT_ROW_DIFFERS", **base)
    return {"bridge_version": BRIDGE_VERSION, "status": EXACT_SHIFT if removed else EXACT, **base,
            "column_map": column_map, "original_table_sha256": _sha(otab), "validated_table_sha256": _sha(vtab)}


def original_cell_v1(table, locator: dict[str, Any]) -> dict[str, Any] | None:
    """ORIGINAL (VID, section, table, row, column) of an emitted cell, or None when not bijective.

    A continuation-merged table maps the cell back to its own fragment first (row id prefix
    p<page>:, head column -> fragment column), then through that fragment's bridge.
    """

    row_id, column_id = locator.get("row_id"), locator.get("column_id")
    if not isinstance(row_id, str) or not isinstance(column_id, str):
        return None
    if table.fragments:
        match = re.fullmatch(r"p([0-9]+):(r[1-9][0-9]*)", row_id)
        if not match:
            return None
        page, own_row = int(match.group(1)), match.group(2)
        bridges = [b for b in table.fragment_bridges if b.get("physical_page") == page]
        bridge = bridges[0] if len(bridges) == 1 else None
        own_column = (table.fragment_column_maps.get(page) or {}).get(column_id)
    else:
        bridge, own_row, own_column = table.bridge, row_id, column_id
        if not re.fullmatch(r"r[1-9][0-9]*", own_row):
            return None
    if not bridge or bridge.get("status") not in (EXACT, EXACT_SHIFT) or own_column not in (bridge.get("column_map") or {}):
        return None
    return {"page_json_version_id": bridge["page_json_version_id"], "section_ordinal": bridge["section_ordinal"],
            "table_ordinal": bridge["table_ordinal"], "row_ordinal": int(own_row[1:]),
            "column_ordinal": bridge["column_map"][own_column], "bridge_status": bridge["status"]}
