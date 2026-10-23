"""Notes pilot workbook: legacy TM template rows plus the dimensional view, exact readback.

* TM: the rows of the pinned ``Bank_TM_ReportNormId.v2.xlsx`` in template order;
  for every period, value / observation state / acceptance / unit / source
  reference. Only cells mapped through the crosswalk appear here; a held cell
  shows its state and acceptance with no value.
* DIMENSIONAL: every evaluated cell by (concept, axis coordinate, basis,
  period) — the cross-bank comparable view, including cells without a legacy
  ReportNormId.
* README: product label NOTES_PILOT_EXPERIMENTAL, families included, pins.

Numbers follow the PRIMARY exact-number policy; text is always literal, so no
cell can become a formula. ``verify_notes_workbook_v1`` reopens the bytes and
compares every value, type, state, unit, period and source reference.
"""

from __future__ import annotations

import hashlib
import re
from io import BytesIO
from pathlib import Path
from typing import Any

import openpyxl

from bctc_ai.export.canonical_xlsx import deterministic_workbook_bytes, set_literal_cell, workbook_has_formula
from bctc_ai.primary_statements.excel_v1 import excel_number_v1
from bctc_ai.primary_statements.source_v1 import sha256_file
from bctc_ai.schema.xlsx_reader import read_rows

NOTES_WORKBOOK_FORMAT = "NOTES_PILOT_WORKBOOK_V1"
PRODUCT_LABEL = "NOTES_PILOT_EXPERIMENTAL"
TM_TEMPLATE = "template/Bank_TM_ReportNormId.v2.xlsx"
TM_TEMPLATE_SHA256 = "64589f7ee2b025ac0bd784c13e0b0ba0aff9d46456a83fa7fe2d68a7de375115"
EXPORTED = {"ACCEPTED", "ACCEPTED_BLANK", "HOLD"}
_DIMENSIONAL_HEADER = ["family", "concept", "axis", "member", "classification_basis", "period_key", "period_basis",
                       "unit", "unit_basis", "observation_state", "value", "raw", "acceptance", "hold_reasons",
                       "report_norm_id", "label_exact", "source"]


class NotesWorkbookError(ValueError):
    """The notes workbook does not read back exactly."""


def tm_template_rows_v1(project_root: Path) -> list[tuple[int, str]]:
    path = project_root / TM_TEMPLATE
    if sha256_file(path) != TM_TEMPLATE_SHA256:
        raise NotesWorkbookError("TM template SHA-256 differs from the pinned template")
    rows = []
    for row in read_rows(path):
        raw = (row.get("B") or "").strip()
        if raw and raw != "ReportNormId":
            rows.append((int(raw), row.get("C") or ""))
    if len({rnid for rnid, _ in rows}) != len(rows):
        raise NotesWorkbookError("TM template repeats a ReportNormId")
    return rows


def _period_order(key: str) -> tuple[int, str]:
    dates = re.findall(r"\d{4}-\d{2}-\d{2}", key)
    return (0, "".join(dates)) if dates else (1, key)


def _source(cell: dict[str, Any]) -> str:
    loc = cell["locator"]
    return f"p{loc['physical_page']}/{loc['section_id']}/{loc['table_id']}/{loc['row_id']}/{loc['column_id']}@{loc['page_json_version_id']}"


def _tm_cells(cells: list[dict[str, Any]]) -> tuple[list[str], dict[tuple[int, str], dict[str, Any]]]:
    chosen: dict[tuple[int, str], dict[str, Any]] = {}
    for cell in cells:
        if cell.get("report_norm_id") is None or not cell["period_key"] or cell["acceptance"] not in EXPORTED:
            continue
        key = (cell["report_norm_id"], cell["period_key"])
        current = chosen.get(key)
        if current is None:
            chosen[key] = cell
        elif current["acceptance"] != "HOLD" and cell["acceptance"] != "HOLD":
            raise NotesWorkbookError(f"two exported cells for ReportNormId {key[0]} period {key[1]}")
        elif current["acceptance"] == "HOLD" and cell["acceptance"] != "HOLD":
            chosen[key] = cell
    keys = {period for _, period in chosen}
    dated = sorted((p for p in keys if _period_order(p)[0] == 0), key=lambda p: _period_order(p)[1], reverse=True)
    return dated + sorted(p for p in keys if _period_order(p)[0] == 1), chosen


def build_notes_workbook_v1(document: dict[str, Any], cells: list[dict[str, Any]], template: list[tuple[int, str]],
                            pins: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    workbook = openpyxl.Workbook()
    readme = workbook.active
    readme.title = "README"
    notice = [("product_label", PRODUCT_LABEL),
              ("notice", "Experimental notes pilot (thuyết minh). Not a production or accepted export; only the "
                         "families listed are evaluated, every other TM row is NOT EVALUATED (not NOT_OBSERVED)."),
              ("document_plan_id", document["document_plan_id"]), ("relative_path", document["relative_path"]),
              ("source_sha256", document["source_sha256"]), ("families", ",".join(sorted({c["family"] for c in cells}))),
              ("pins", repr(sorted(pins.items())))]
    for row, (name, value) in enumerate(notice, 1):
        set_literal_cell(readme.cell(row, 1), name)
        set_literal_cell(readme.cell(row, 2), value)
    periods, chosen = _tm_cells(cells)
    sheet = workbook.create_sheet("TM")
    header = ["order", "ReportNormId", "name"]
    for period in periods:
        header += [f"{period}|value", f"{period}|state", f"{period}|acceptance", f"{period}|unit", f"{period}|source"]
    for column, text in enumerate(header, 1):
        set_literal_cell(sheet.cell(1, column), text)
    for row, (rnid, name) in enumerate(template, 2):
        sheet.cell(row, 1).value = row - 1
        sheet.cell(row, 2).value = rnid
        set_literal_cell(sheet.cell(row, 3), name)
        for position, period in enumerate(periods):
            cell = chosen.get((rnid, period))
            if cell is None:
                continue
            base = 4 + position * 5
            number, _policy = excel_number_v1(cell["value"] if cell["acceptance"] != "HOLD" else None)
            if isinstance(number, str):
                set_literal_cell(sheet.cell(row, base), number)
            else:
                sheet.cell(row, base).value = number
            for offset, text in enumerate([cell["observation_state"], cell["acceptance"], cell["unit"], _source(cell)], 1):
                set_literal_cell(sheet.cell(row, base + offset), text)
    dimensional = workbook.create_sheet("DIMENSIONAL")
    for column, text in enumerate(_DIMENSIONAL_HEADER, 1):
        set_literal_cell(dimensional.cell(1, column), text)
    for row, cell in enumerate(cells, 2):
        values = [cell["family"], cell["concept"], cell["axis"], cell["member"], cell["classification_basis"],
                  cell["period_key"], cell["period_basis"], cell["unit"], cell["unit_basis"], cell["observation_state"],
                  cell["value"], cell["raw"], cell["acceptance"], ";".join(cell["hold_reasons"]),
                  cell.get("report_norm_id"), cell["label_exact"], _source(cell)]
        for column, value in enumerate(values, 1):
            if isinstance(value, int):
                dimensional.cell(row, column).value = value
            else:
                set_literal_cell(dimensional.cell(row, column), value)
    payload = deterministic_workbook_bytes(workbook, creator="bctc-ai notes pilot v1")
    receipt = verify_notes_workbook_v1(payload, document, cells, template)
    return payload, receipt


def verify_notes_workbook_v1(payload: bytes, document: dict[str, Any], cells: list[dict[str, Any]],
                             template: list[tuple[int, str]]) -> dict[str, Any]:
    workbook = openpyxl.load_workbook(BytesIO(payload), data_only=False)
    if workbook_has_formula(workbook):
        raise NotesWorkbookError("workbook contains a formula")
    if workbook.sheetnames != ["README", "TM", "DIMENSIONAL"]:
        raise NotesWorkbookError("workbook sheet set drifted")
    if workbook["README"].cell(1, 2).value != PRODUCT_LABEL or workbook["README"].cell(3, 2).value != document["document_plan_id"]:
        raise NotesWorkbookError("README binding drifted")
    periods, chosen = _tm_cells(cells)
    sheet = workbook["TM"]
    if [sheet.cell(row, 2).value for row in range(2, sheet.max_row + 1)] != [rnid for rnid, _ in template]:
        raise NotesWorkbookError("TM template rows drifted")
    checked = 0
    for row, (rnid, _name) in enumerate(template, 2):
        for position, period in enumerate(periods):
            base = 4 + position * 5
            got = [sheet.cell(row, base + offset).value for offset in range(5)]
            cell = chosen.get((rnid, period))
            if cell is None:
                if any(value is not None for value in got):
                    raise NotesWorkbookError(f"TM {rnid} {period} has an unexpected value")
                continue
            number, _ = excel_number_v1(cell["value"] if cell["acceptance"] != "HOLD" else None)
            expected = [number, cell["observation_state"], cell["acceptance"], cell["unit"], _source(cell)]
            if got != expected or type(got[0]) is not type(number):
                raise NotesWorkbookError(f"TM {rnid} {period} does not read back exactly")
            checked += 1
    dimensional = workbook["DIMENSIONAL"]
    if dimensional.max_row - 1 != len(cells):
        raise NotesWorkbookError("DIMENSIONAL row count drifted")
    for row, cell in enumerate(cells, 2):
        got = [dimensional.cell(row, column).value for column in (2, 4, 6, 8, 11, 13, 17)]
        expected = [cell["concept"], cell["member"], cell["period_key"], cell["unit"], cell["value"], cell["acceptance"], _source(cell)]
        if got != expected:
            raise NotesWorkbookError(f"DIMENSIONAL row {row} does not read back exactly")
    return {"format_version": NOTES_WORKBOOK_FORMAT, "workbook_sha256": hashlib.sha256(payload).hexdigest(),
            "workbook_size_bytes": len(payload), "tm_cells_checked": checked, "dimensional_rows": len(cells),
            "formula_cells": 0, "status": "PASS_EXACT_READBACK"}
