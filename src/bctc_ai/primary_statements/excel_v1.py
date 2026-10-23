"""Deterministic PRIMARY_ONLY workbook export with exact readback verification.

Rows follow the pinned template workbooks (ReportNormId + name, template
order) for CDKT, KQKD and LCTT. Each period lane contributes value, state,
acceptance, unit and source-reference columns; every exported cell is also
listed in PROVENANCE with its locator and hold reasons. Numbers are written as
Excel numbers only when the stored double is exactly the source decimal
(integers below 2**53, or decimals that round-trip within 15 significant
digits); otherwise the exact decimal text is written and flagged. Source text
is always a literal string, so no cell can become a formula.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Any

import openpyxl

from bctc_ai.export.canonical_xlsx import (
    deterministic_workbook_bytes,
    set_literal_cell,
    workbook_has_formula,
)
from bctc_ai.primary_statements.catalog_v1 import PRIMARY_STATEMENTS, PrimaryCatalog
from bctc_ai.schema.xlsx_reader import read_rows

EXCEL_FORMAT_VERSION = "PRIMARY_ONLY_WORKBOOK_V1"
CREATOR = "bctc-ai primary-statements v1"
_MAX_EXACT_INT = 2 ** 53


class PrimaryWorkbookError(ValueError):
    """The workbook does not read back exactly."""


def template_rows_v1(project_root: Path, catalog: PrimaryCatalog) -> dict[str, list[tuple[int, str]]]:
    """(ReportNormId, template name) in template order, verified against the registry."""

    rows = {}
    for statement in PRIMARY_STATEMENTS:
        path = project_root / f"template/Bank_{statement}_ReportNormId.v2.xlsx"
        found = []
        for row in read_rows(path):
            raw_id = (row.get("B") or "").strip()
            if raw_id and raw_id != "ReportNormId":
                found.append((int(raw_id), row.get("C") or ""))
        if [rnid for rnid, _ in found] != catalog.statements[statement].ordered_ids:
            raise PrimaryWorkbookError(f"{statement} template order differs from the schema registry")
        rows[statement] = found
    return rows


def excel_number_v1(value: str | None) -> tuple[object, str]:
    """Excel representation of an exact decimal text and its policy."""

    if value is None:
        return None, "NO_VALUE"
    decimal = Decimal(value)
    if decimal == decimal.to_integral_value():
        integer = int(decimal)
        if abs(integer) < _MAX_EXACT_INT:
            return integer, "EXCEL_INTEGER_EXACT"
        return value, "EXACT_TEXT_INTEGER_BEYOND_DOUBLE_PRECISION"
    as_float = float(decimal)
    if Decimal(repr(as_float)) == decimal and len(decimal.as_tuple().digits) <= 15:
        return as_float, "EXCEL_DECIMAL_ROUND_TRIP_EXACT"
    return value, "EXACT_TEXT_DECIMAL_NOT_REPRESENTABLE"


def _lane_columns(result: dict[str, Any], statement: str) -> list[dict[str, Any]]:
    lanes = []
    for instance in result["instances"]:
        if instance["statement"] != statement or instance["presentation_role"] != "PRIMARY":
            continue
        for lane in instance["lanes"]:
            lanes.append({"instance_key": instance["instance_key"], "lane": lane["lane"],
                          "period_key": (lane["period"] or {}).get("key"), "header_text": lane["header_text"],
                          "unit": lane["unit"], "scope": instance["scope"]})
    return lanes


def _source_ref(cell: dict[str, Any]) -> str:
    loc = cell["locator"]
    return (f"p{loc['physical_page']}/s{loc['section_ordinal']}/t{loc['table_ordinal']}/r{loc['row_ordinal']}"
            f"/c{loc['column_ordinal']}@{loc['page_json_version_id']}")


def _sheets_v1(result: dict[str, Any], template: dict[str, list[tuple[int, str]]]) -> tuple[dict[str, list[list[Any]]], dict]:
    """The one projection the writer and the verifier both use: every emitted cell of every sheet (Codex 0226)."""

    sheets: dict[str, list[list[Any]]] = {"README": [
        ["product_label", result["product_label"]],
        ["notice", result["product_notice"]],
        ["format_version", EXCEL_FORMAT_VERSION],
        ["result_id", result["result_id"]],
        ["document", json.dumps(result["document"], ensure_ascii=False, sort_keys=True)],
        ["corpus", json.dumps(result["corpus"], ensure_ascii=False, sort_keys=True)],
        ["pins", json.dumps(result["pins"], ensure_ascii=False, sort_keys=True)],
    ]}
    cells_by_key = {}
    for cell in result["cells"]:
        cells_by_key[(cell["statement"], cell["instance_key"], cell["lane"], cell["report_norm_id"])] = cell
    status_by_key = {}
    for item in result["item_status"]:
        status_by_key.setdefault((item["statement"], item["report_norm_id"]), []).append(
            f"{item['instance_key']}:{item['status']}"
        )
    expected_values: dict[tuple[str, int, int], tuple[object, str]] = {}
    for statement in PRIMARY_STATEMENTS:
        lanes = _lane_columns(result, statement)
        header = ["DisplayOrder", "ReportNormId", "ReportNormName", "ItemStatus"]
        for lane in lanes:
            label = f"{lane['instance_key']}#L{lane['lane']}|{lane['period_key']}|{lane['scope']}"
            header += [f"VALUE|{label}", f"STATE|{label}", f"ACCEPTANCE|{label}", f"UNIT|{label}", f"SOURCE|{label}"]
        rows: list[list[Any]] = [header]
        for order, (rnid, name) in enumerate(template[statement]):
            row_index = order + 2
            values: list[object] = [order, rnid, name, ";".join(status_by_key.get((statement, rnid), ["NOT_EVALUATED_NO_STATEMENT"]))]
            for lane in lanes:
                cell = cells_by_key.get((statement, lane["instance_key"], lane["lane"], rnid))
                if cell is None:
                    values += [None, None, None, None, None]
                    continue
                number, policy = excel_number_v1(cell["value"])
                values += [number, cell["observation_state"], cell["acceptance"], cell["unit"], _source_ref(cell)]
                expected_values[(statement, row_index, len(values) - 4)] = (number, policy)
            rows.append(values)
        sheets[statement] = rows
    provenance = [["statement", "scope", "report_norm_id", "period_key", "lane", "instance_key", "value_text",
                   "excel_number_policy", "observation_state", "acceptance", "hold_reasons", "unit", "raw_text",
                   "label_exact", "row_uid", "source_ref", "numeric_policy"]]
    for cell in result["cells"]:
        _, policy = excel_number_v1(cell["value"])
        provenance.append([cell["statement"], cell["scope"], cell["report_norm_id"], cell["period_key"], cell["lane"],
                           cell["instance_key"], cell["value"], policy, cell["observation_state"], cell["acceptance"],
                           json.dumps(cell["hold_reasons"], ensure_ascii=False), cell["unit"], cell["raw"], cell["label_exact"],
                           cell["row_uid"], _source_ref(cell), cell["numeric_policy"]])
    sheets["PROVENANCE"] = provenance
    source_rows = [["instance_key", "statement", "presentation_role", "row_uid", "label_exact", "disposition", "reason",
                    "report_norm_id", "raw_cells"]]
    for instance in result["instances"]:
        for row in instance["source_rows"]:
            source_rows.append([instance["instance_key"], instance["statement"], instance["presentation_role"], row["row_uid"],
                                row["label_exact"], row["disposition"], row["reason"], row["report_norm_id"],
                                json.dumps([cell["raw"] for cell in row["cells"]], ensure_ascii=False)])
    sheets["SOURCE_ROWS"] = source_rows
    checks = [["instance_key", "equation_id", "lane", "period_key", "status", "reason", "left", "right", "residual"]]
    for instance in result["instances"]:
        for check in instance["validations"]:
            checks.append([instance["instance_key"], check["equation_id"], check["lane"], check["period_key"],
                           check["status"], check["reason"], check["left"], check["right"], check["residual"]])
    sheets["VALIDATION"] = checks
    return sheets, expected_values


_SHEET_ORDER = ["README", *PRIMARY_STATEMENTS, "PROVENANCE", "SOURCE_ROWS", "VALIDATION"]


def build_workbook_v1(result: dict[str, Any], template: dict[str, list[tuple[int, str]]]) -> tuple[bytes, dict[str, Any]]:
    workbook = openpyxl.Workbook()
    sheets, expected_values = _sheets_v1(result, template)
    for position, name in enumerate(_SHEET_ORDER):
        sheet = workbook.active if position == 0 else workbook.create_sheet(name)
        sheet.title = name
        for r, row in enumerate(sheets[name], 1):
            for c, value in enumerate(row, 1):
                set_literal_cell(sheet.cell(r, c), value)  # every position, as before; text never becomes a formula
    payload = deterministic_workbook_bytes(workbook, creator=CREATOR)
    plan = {"expected_values": expected_values}
    return payload, plan


def _as_read(value: Any) -> Any:
    """What a written value reads back as: openpyxl writes an empty string as a value-less cell (None)."""

    return None if value == "" else value


def verify_workbook_v1(payload: bytes, result: dict[str, Any], template: dict[str, list[tuple[int, str]]]) -> dict[str, Any]:
    """Every emitted cell of every sheet (README, the three statement grids with header / order / name / ItemStatus /
    every lane column, PROVENANCE, SOURCE_ROWS, VALIDATION) reads back with its exact value AND type; any non-empty
    cell outside that grid is extra data (Codex 0226). Cosmetic empty or styled cells are not a layout proof."""

    workbook = openpyxl.load_workbook(BytesIO(payload), data_only=False)
    if workbook_has_formula(workbook):
        raise PrimaryWorkbookError("workbook contains a formula")
    if workbook.sheetnames != _SHEET_ORDER:
        raise PrimaryWorkbookError("workbook sheet set drifted")
    sheets, expected_values = _sheets_v1(result, template)
    compared = 0
    for name in _SHEET_ORDER:
        sheet, rows = workbook[name], sheets[name]
        for r, row in enumerate(rows, 1):
            for c, value in enumerate(row, 1):
                got, expected = sheet.cell(r, c).value, _as_read(value)
                if type(got) is not type(expected) or got != expected:
                    raise PrimaryWorkbookError(f"{name}!R{r}C{c} does not read back exactly")
                compared += 1
        for line in sheet.iter_rows():
            for cell in line:
                if cell.value is not None and (cell.row > len(rows) or cell.column > len(rows[cell.row - 1])):
                    raise PrimaryWorkbookError(f"{name}!R{cell.row}C{cell.column} is extra data")
    cells_by_key = {(c["statement"], c["instance_key"], c["lane"], c["report_norm_id"]): c for c in result["cells"]}
    checked_values = 0
    for statement in PRIMARY_STATEMENTS:
        sheet = workbook[statement]
        for row_index, (rnid, _name) in enumerate(template[statement], 2):
            for position, lane in enumerate(_lane_columns(result, statement)):
                cell = cells_by_key.get((statement, lane["instance_key"], lane["lane"], rnid))
                if cell is None:
                    continue
                got = sheet.cell(row_index, 5 + position * 5).value
                if cell["value"] is not None and not isinstance(got, str) and Decimal(repr(got)) != Decimal(cell["value"]):
                    raise PrimaryWorkbookError(f"{statement}/{rnid} lost numeric precision")
                checked_values += 1
    if checked_values != len(expected_values):
        raise PrimaryWorkbookError("statement value cells differ from the export plan")
    return {
        "format_version": EXCEL_FORMAT_VERSION,
        "workbook_sha256": hashlib.sha256(payload).hexdigest(),
        "workbook_size_bytes": len(payload),
        "result_id": result["result_id"],
        "checked_value_cells": checked_values,
        "provenance_rows": len(result["cells"]),
        "grid_positions_compared": compared,
        "readback_scope": "EVERY_EMITTED_CELL_TYPED_NO_EXTRA_DATA",
        "formula_cells": 0,
        "status": "PASS_EXACT_READBACK",
    }
