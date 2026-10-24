"""Original-source bridge for notes tables: normalized SQL coordinates proven against the ORIGINAL page BLOB.

A pinned database authenticates its bytes, not that every normalized table/row/column/cell is a
lossless source coordinate. For each loaded table (NotesSource.load_tables):

1. the page ORIGINAL is loaded through the existing authenticated loader
   (gemini_income_tax_source_page_loader_v1: BLOB SHA, content-ID replay, canonical two-LF
   serialization, provenance, proven lossless redundant-TEXT-column removal only). Every loader
   failure - missing input, integrity, provenance, SQLite, unsupported transform - fails the
   run; the loader's returned logical name / source SHA / physical page must be the selected
   corpus page, else the run fails too;
2. the SQL table is compared typed-exactly (raw stored JSON, before any null/string filtering)
   with the ORIGINAL table - section/table metadata and ordinals, column headers/kinds, row
   labels/paths/kinds, a recomputed parent edge, and every positional cell including nulls.
   Equal: SQL cN is ORIGINAL column N;
3. otherwise the SQL table may equal the loader's validated table only through the single
   loader-proven redundant TEXT column removal, re-checked here column by column and row by
   row; SQL cN then maps to the ORIGINAL ordinal around the removed column. Anything else is a
   table MISMATCH (rejected, never read).

The bridge proves source coordinates only - never role, unit, period, basis or membership.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from bctc_ai.source_structure.contracts_v1 import same_typed_json_v1 as _same

BRIDGE_VERSION = "NOTES_ORIGINAL_SOURCE_BRIDGE_V2"
EXACT = "EXACT"
EXACT_SHIFT = "EXACT_WITH_PROVEN_TEXT_COLUMN_SHIFT"
_ROW_ID = re.compile(r"r([1-9][0-9]*)")
_MERGED_ROW_ID = re.compile(r"p([1-9][0-9]*):(r[1-9][0-9]*)")


def _sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _typed(value: Any) -> Any:
    """JSON-safe value that keeps the exact type (str/int/float/bool/None/list/tuple/dict) visible to a hash."""

    if type(value) in (list, tuple):
        return [type(value).__name__, [_typed(item) for item in value]]
    if type(value) is dict:
        return ["dict", sorted([key, _typed(item)] for key, item in value.items())]
    if type(value) is float:
        return ["float", value.hex()]
    if value is not None and type(value) not in (str, int, bool):
        return [type(value).__name__, repr(value)]
    return [type(value).__name__, value]


def _coordinate_of(locator: dict[str, Any]) -> tuple[Any, int | None, int | None]:
    """(VID, section ordinal, table ordinal) named by a table/fragment locator."""

    ms = re.fullmatch(r"s([1-9][0-9]*)", str(locator.get("section_id")))
    mt = re.fullmatch(r"t([1-9][0-9]*)", str(locator.get("table_id")))
    return (locator.get("page_json_version_id"), int(ms.group(1)) if ms else None, int(mt.group(1)) if mt else None)


def _proof_binds(proof: dict[str, Any], locator: dict[str, Any]) -> bool:
    """The proof was made for exactly this table (or fragment): same VID, section and table ordinal."""

    coordinate = _coordinate_of(locator)
    return None not in coordinate and (
        proof.get("page_json_version_id"), proof.get("section_ordinal"), proof.get("table_ordinal")) == coordinate


def table_fingerprint_v1(table) -> str:
    """Typed SHA-256 of every raw SQL field the bridge compares (cache binding for a proof)."""

    payload = {
        "key": list(table.key), "orders": [table.section_order, table.table_order],
        "section": _typed([table.section_title, table.content_kind, table.narratives_raw]),
        "table": _typed([table.table_title, table.unit_exact, table.continuation]),
        "columns": [_typed([c.column_id, c.ordinal, c.header_raw, c.value_kind]) for c in table.columns],
        "rows": [_typed([r.row_id, r.order, r.label, r.hierarchy_raw, r.kind, r.parent_row_id]) for r in table.rows],
        "cells": sorted([row, column, _typed(value[0])] for (row, column), value in table.cells.items()),
    }
    return _sha(payload)


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


def _compare_sql_v1(table, section: dict[str, Any], source: dict[str, Any]) -> dict[str, Any] | None:
    """None when the SQL table is exactly ``source`` (one page table object), else the first difference."""

    if not _same([section.get("title_exact"), section.get("content_kind"), section.get("narratives_exact")],
                 [table.section_title, table.content_kind, table.narratives_raw]):
        return {"reason": "SECTION_METADATA"}
    if not _same([source.get("title_exact"), source.get("unit_exact"), source.get("continuation")],
                 [table.table_title, table.unit_exact, table.continuation]):
        return {"reason": "TABLE_METADATA"}
    columns_source, rows_source = source.get("columns"), source.get("rows")
    if type(columns_source) is not list or type(rows_source) is not list:
        return {"reason": "AXIS_ABSENT"}
    columns = sorted(table.columns, key=lambda c: c.ordinal)
    if len(columns) != len(columns_source):
        return {"reason": "COLUMN_COUNT"}
    for index, (column, expected) in enumerate(zip(columns, columns_source, strict=False)):
        if (column.column_id, column.ordinal) != (f"c{index + 1}", index) or not _same(
                [column.header_raw, column.value_kind], [expected.get("header_path_exact"), expected.get("value_kind")]):
            return {"reason": "COLUMN_IDENTITY", "column_id": column.column_id}
    rows = sorted(table.rows, key=lambda r: r.order)
    if len(rows) != len(rows_source):
        return {"reason": "ROW_COUNT"}
    parents = recompute_parents_v1(rows_source)
    per_row: dict[str, int] = {}
    for row_id, _column in table.cells:
        per_row[row_id] = per_row.get(row_id, 0) + 1
    if set(per_row) - {row.row_id for row in rows}:
        return {"reason": "CELL_WITHOUT_ROW"}
    for index, (row, expected) in enumerate(zip(rows, rows_source, strict=False)):
        if (row.row_id, row.order) != (f"r{index + 1}", index) or not _same(
                [row.label, row.hierarchy_raw, row.kind],
                [expected.get("label_exact"), expected.get("hierarchy_path_exact"), expected.get("row_kind")]):
            return {"reason": "ROW_IDENTITY", "row_id": row.row_id}
        if row.parent_row_id != parents[row.row_id]:
            return {"reason": "PARENT_EDGE_NOT_RECOMPUTED", "row_id": row.row_id}
        values = expected.get("values_exact")
        if type(values) is not list or len(values) != len(columns) or per_row.get(row.row_id, 0) != len(values):
            return {"reason": "CELL_COUNT", "row_id": row.row_id}
        for column_index, value in enumerate(values):
            cell = table.cells.get((row.row_id, f"c{column_index + 1}"))
            if cell is None or not _same(cell[0], value):
                return {"reason": "CELL_VALUE", "row_id": row.row_id, "column_id": f"c{column_index + 1}"}
    return None


def _proven_shift_map_v1(original: dict[str, Any], validated: dict[str, Any], removed: Any) -> tuple[dict[str, int] | None, str]:
    """SQL column -> ORIGINAL ordinal for one removed redundant TEXT column, re-proven cell by cell."""

    ocols, orows, vcols, vrows = original.get("columns"), original.get("rows"), validated.get("columns"), validated.get("rows")
    if type(removed) is not int or type(removed) is bool or any(type(x) is not list for x in (ocols, orows, vcols, vrows)) \
            or not 1 <= removed <= len(ocols) or len(ocols) != len(vcols) + 1 \
            or ocols[removed - 1].get("value_kind") != "TEXT" or len(orows) != len(vrows):
        return None, "TEXT_SHIFT_NOT_PROVEN"
    column_map = {f"c{i + 1}": (i + 1 if i + 1 < removed else i + 2) for i in range(len(vcols))}
    if any(not _same(ocols[column_map[f"c{i + 1}"] - 1], vcol) for i, vcol in enumerate(vcols)) \
            or not _same({k: v for k, v in original.items() if k not in ("columns", "rows")},
                         {k: v for k, v in validated.items() if k not in ("columns", "rows")}):
        return None, "TEXT_SHIFT_COLUMN_DIFFERS"
    for vrow, orow in zip(vrows, orows, strict=False):
        ovalues, vvalues = orow.get("values_exact"), vrow.get("values_exact")
        if type(ovalues) is not list or type(vvalues) is not list or len(ovalues) != len(vvalues) + 1 \
                or not _same({k: v for k, v in orow.items() if k != "values_exact"}, {k: v for k, v in vrow.items() if k != "values_exact"}) \
                or any(not _same(ovalues[column_map[f"c{i + 1}"] - 1], value) for i, value in enumerate(vvalues)):
            return None, "TEXT_SHIFT_ROW_DIFFERS"
        # The removed cell must be the row's own label (or a GROUP blank): the only admitted redundancy.
        dropped = ovalues[removed - 1]
        if not (_same(dropped, orow.get("label_exact")) or (dropped is None and orow.get("row_kind") == "GROUP")):
            return None, "TEXT_SHIFT_CELL_NOT_REDUNDANT"
    return column_map, ""


def bridge_table_v1(table, original_page: dict[str, Any], validated_page: dict[str, Any],
                    changed_tables: list[dict[str, Any]]) -> dict[str, Any]:
    """Prove one SQL table (a kernel NoteTable) against its ORIGINAL (and loader-validated) page object."""

    ms, mt = re.fullmatch(r"s([1-9][0-9]*)", table.section_id), re.fullmatch(r"t([1-9][0-9]*)", table.table_id)
    if not ms or not mt or (table.section_order, table.table_order) != (int(ms.group(1)) - 1, int(mt.group(1)) - 1):
        return {"bridge_version": BRIDGE_VERSION, "status": "MISMATCH:NORMALIZED_IDS", "page_json_version_id": table.page_json_version_id}
    s, t = int(ms.group(1)), int(mt.group(1))
    base = {"bridge_version": BRIDGE_VERSION, "page_json_version_id": table.page_json_version_id, "section_ordinal": s,
            "table_ordinal": t}
    try:
        osec, vsec = original_page["sections"][s - 1], validated_page["sections"][s - 1]
        otab, vtab = osec["tables"][t - 1], vsec["tables"][t - 1]
    except (KeyError, IndexError, TypeError):
        return {**base, "status": "MISMATCH:COORDINATE_ABSENT"}
    shifts = [c for c in changed_tables if c.get("section_ordinal") == s and c.get("table_ordinal") == t]
    against_original = _compare_sql_v1(table, osec, otab)
    if against_original is None:
        status, column_map = EXACT, {f"c{i + 1}": i + 1 for i in range(len(table.columns))}
    elif len(shifts) == 1 and _compare_sql_v1(table, vsec, vtab) is None:
        column_map, failure = _proven_shift_map_v1(otab, vtab, shifts[0].get("redundant_text_column_ordinal"))
        if column_map is None:
            return {**base, "status": "MISMATCH:" + failure}
        status = EXACT_SHIFT
    else:
        reason = "MULTIPLE_COLUMN_SHIFTS" if len(shifts) > 1 else against_original.pop("reason")
        return {**base, "status": "MISMATCH:" + reason, **({} if len(shifts) > 1 else against_original)}
    return {**base, "status": status, "column_map": column_map, "row_count": len(table.rows),
            "original_table_sha256": _sha(otab), "validated_table_sha256": _sha(vtab)}


def original_cell_v1(table, locator: dict[str, Any]) -> dict[str, Any] | None:
    """ORIGINAL (VID, section, table, row, column) of an emitted cell, or None when not bijective.

    The locator must name this table (VID/section/table), an existing row key and an existing
    cell of it. A continuation-merged table maps the cell back to its own fragment first
    (canonical row key p<page>:r<n>, head column -> fragment column), then through that
    fragment's bridge, which must belong to that fragment's own VID.
    """

    row_id, column_id = locator.get("row_id"), locator.get("column_id")
    if not isinstance(row_id, str) or not isinstance(column_id, str):
        return None
    identity = table.locator()
    if any(locator.get(key) != identity[key] for key in ("page_json_version_id", "section_id", "table_id")):
        return None
    if row_id not in {row.row_id for row in table.rows} or (row_id, column_id) not in table.cells:
        return None
    if table.fragments:
        match = _MERGED_ROW_ID.fullmatch(row_id)
        if not match:
            return None
        page, own_row = int(match.group(1)), match.group(2)
        fragments = [f for f in table.fragments if f.get("physical_page") == page]
        bridges = [b for b in table.fragment_bridges if b.get("physical_page") == page]
        if len(fragments) != 1 or len(bridges) != 1 or not _proof_binds(bridges[0], fragments[0]):
            return None
        bridge, own_column = bridges[0], (table.fragment_column_maps.get(page) or {}).get(column_id)
    else:
        if not _ROW_ID.fullmatch(row_id):
            return None
        bridge, own_row, own_column = table.bridge, row_id, column_id
        if not bridge or not _proof_binds(bridge, identity):
            return None
    if not bridge or bridge.get("status") not in (EXACT, EXACT_SHIFT) or own_column not in (bridge.get("column_map") or {}):
        return None
    row_ordinal = int(own_row[1:])
    if not 1 <= row_ordinal <= (bridge.get("row_count") or 0):
        return None
    return {"page_json_version_id": bridge["page_json_version_id"], "section_ordinal": bridge["section_ordinal"],
            "table_ordinal": bridge["table_ordinal"], "row_ordinal": row_ordinal,
            "column_ordinal": bridge["column_map"][own_column], "bridge_status": bridge["status"]}
