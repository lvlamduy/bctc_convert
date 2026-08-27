from __future__ import annotations

from copy import deepcopy

import pytest

from bctc_ai.evaluation.accounting_row_width_total_column_seal_v1 import (
    AccountingRowWidthTotalColumnSealV1Error,
    build_accounting_row_width_total_column_seal_v1,
    validate_accounting_row_width_total_column_seal_replay_v1,
)


def _cell(value: int | None, token: str, *, state: str | None = None) -> dict:
    resolved_state = state or (
        "BLANK" if value is None else "PRINTED_ZERO" if value == 0 else "NUMBER"
    )
    return {
        "coefficient": value,
        "source_locator": {"cell": token},
        "source_text": token,
        "state": resolved_state,
    }


def _term(row: str, column: str, multiplier: int = 1) -> dict:
    return {"column_id": column, "multiplier": multiplier, "row_id": row}


def _equation(identity: str, axis: str, terms: list[dict], row: str, column: str) -> dict:
    return {
        "axis": axis,
        "equation_id": identity,
        "result": {"column_id": column, "row_id": row},
        "terms": terms,
    }


def _row(identity: str, values: list[int | None], ordinal: int, *, kind: str = "DATA") -> dict:
    columns = ["a", "b", "unused", "total"]
    return {
        "cells": {
            column: _cell(value, "" if value is None else str(value))
            for column, value in zip(columns, values, strict=True)
        },
        "row_id": identity,
        "row_kind": kind,
        "row_ordinal": ordinal,
    }


def _shifted_table() -> dict:
    rows = [
        _row("group", [None, None, None, None], 0, kind="GROUP"),
        _row("opening", [10, 20, None, 30], 1),
        _row("movement", [2, 3, None, 5], 2),
        _row("ending", [12, 23, 35, None], 3),
    ]
    equations = [
        _equation(
            f"{row}-horizontal",
            "HORIZONTAL_ROW",
            [_term(row, "a"), _term(row, "b")],
            row,
            "total",
        )
        for row in ("opening", "movement", "ending")
    ]
    equations.extend(
        [
            _equation(
                "a-rollforward",
                "VERTICAL_ROLLFORWARD",
                [_term("opening", "a"), _term("movement", "a")],
                "ending",
                "a",
            ),
            _equation(
                "b-rollforward",
                "VERTICAL_ROLLFORWARD",
                [_term("opening", "b"), _term("movement", "b")],
                "ending",
                "b",
            ),
            _equation(
                "total-rollforward",
                "VERTICAL_ROLLFORWARD",
                [_term("opening", "total"), _term("movement", "total")],
                "ending",
                "total",
            ),
        ]
    )
    return {
        "columns": [
            {"column_id": column, "column_kind": kind, "column_ordinal": ordinal}
            for ordinal, (column, kind) in enumerate(
                [("a", "DETAIL"), ("b", "DETAIL"), ("unused", "DETAIL"), ("total", "TOTAL")]
            )
        ],
        "equations": equations,
        "period_id": "CURRENT",
        "rows": rows,
        "table_id": "fixed-asset-rollforward",
        "unit_id": "VND_MILLION",
    }


def test_unique_shifted_right_edge_is_sealed_without_mutating_raw_cells() -> None:
    source = _shifted_table()
    before = deepcopy(source)

    result = build_accounting_row_width_total_column_seal_v1(source)

    assert source == before
    assert result["status"] == "SEALED_UNIQUE_ALL_EQUATION_CLOSING_PROJECTION"
    assert result["raw_table_snapshot"]["rows"][3]["cells"]["unused"]["coefficient"] == 35
    effective = result["effective_projection"]["rows"][3]["cells"]
    assert effective["unused"] is None
    assert effective["total"]["coefficient"] == 35
    assert result["raw_table_snapshot"]["rows"][0]["cells"] == before["rows"][0]["cells"]
    receipt = result["relocation_receipts"][0]
    assert receipt["action_kind"] == "RELOCATE_RIGHTMOST_EARLIER_VALUE_TO_TOTAL"
    assert {(item["axis"], item["equation_id"]) for item in receipt["affected_equations"]} == {
        ("HORIZONTAL_ROW", "ending-horizontal"),
        ("VERTICAL_ROLLFORWARD", "total-rollforward"),
    }
    assert validate_accounting_row_width_total_column_seal_replay_v1(result, source) == result


def test_dash_and_printed_zero_remain_typed_zero_not_blank() -> None:
    source = _shifted_table()
    source["rows"][2]["cells"]["b"] = _cell(0, "-", state="DASH_ZERO")
    source["rows"][2]["cells"]["total"] = _cell(2, "2")
    source["rows"][3]["cells"]["b"] = _cell(20, "20")
    source["rows"][3]["cells"]["unused"] = _cell(32, "32")
    source["rows"][1]["cells"]["unused"] = _cell(0, "0", state="PRINTED_ZERO")
    # The printed zero is a real extra occupied cell, not an omitted blank.
    assert build_accounting_row_width_total_column_seal_v1(source)["status"] == "UNRESOLVED"
    source["rows"][1]["cells"]["unused"] = _cell(None, "")
    result = build_accounting_row_width_total_column_seal_v1(source)
    assert result["status"] == "SEALED_UNIQUE_ALL_EQUATION_CLOSING_PROJECTION"
    assert result["effective_projection"]["rows"][2]["cells"]["b"]["state"] == "DASH_ZERO"


def test_relocation_is_unresolved_if_horizontal_equation_still_needs_from_cell() -> None:
    source = _shifted_table()
    ending = next(
        equation
        for equation in source["equations"]
        if equation["equation_id"] == "ending-horizontal"
    )
    ending["terms"].append(_term("ending", "unused"))

    result = build_accounting_row_width_total_column_seal_v1(source)

    assert result["status"] == "UNRESOLVED"
    assert result["unresolved_reasons"] == ["NO_ALL_EQUATION_CLOSING_PROJECTION"]
    assert result["effective_projection"] == result["raw_table_snapshot"]


def test_every_data_row_requires_one_authoritative_horizontal_equation() -> None:
    source = _shifted_table()
    source["equations"] = [
        equation
        for equation in source["equations"]
        if equation["equation_id"] != "movement-horizontal"
    ]

    result = build_accounting_row_width_total_column_seal_v1(source)

    assert result["status"] == "UNRESOLVED"
    assert result["unresolved_reasons"] == ["INCOMPLETE_AUTHORITATIVE_HORIZONTAL_EQUATION_COVERAGE"]
    assert result["relocation_receipts"] == []

    duplicated = _shifted_table()
    extra = deepcopy(
        next(
            equation
            for equation in duplicated["equations"]
            if equation["equation_id"] == "movement-horizontal"
        )
    )
    extra["equation_id"] = "movement-horizontal-duplicate"
    duplicated["equations"].append(extra)
    duplicate_result = build_accounting_row_width_total_column_seal_v1(duplicated)
    assert duplicate_result["status"] == "UNRESOLVED"
    assert duplicate_result["unresolved_reasons"] == [
        "INCOMPLETE_AUTHORITATIVE_HORIZONTAL_EQUATION_COVERAGE"
    ]


def test_correction_without_an_affected_vertical_inventory_is_unresolved() -> None:
    source = _shifted_table()
    source["rows"] = [_row("only", [10, 20, 30, None], 0)]
    source["equations"] = [
        _equation(
            "only-horizontal",
            "HORIZONTAL_ROW",
            [_term("only", "a"), _term("only", "b")],
            "only",
            "total",
        )
    ]

    result = build_accounting_row_width_total_column_seal_v1(source)

    assert result["status"] == "UNRESOLVED"
    assert result["relocation_receipts"] == []


def test_one_unit_vertical_mismatch_vetoes_otherwise_plausible_shift() -> None:
    source = _shifted_table()
    source["rows"][3]["cells"]["a"] = _cell(13, "13")

    assert build_accounting_row_width_total_column_seal_v1(source)["status"] == "UNRESOLVED"


def test_unique_duplicated_total_is_removed_only_by_all_equation_closure() -> None:
    source = _shifted_table()
    source["rows"][3]["cells"]["total"] = _cell(35, "35")

    result = build_accounting_row_width_total_column_seal_v1(source)

    assert result["status"] == "SEALED_UNIQUE_ALL_EQUATION_CLOSING_PROJECTION"
    assert result["relocation_receipts"][0]["action_kind"] == (
        "REMOVE_UNIQUE_DUPLICATED_TOTAL_SOURCE"
    )
    assert result["effective_projection"]["rows"][3]["cells"]["unused"] is None
    assert result["effective_projection"]["rows"][3]["cells"]["total"]["coefficient"] == 35


def test_duplicate_looking_legitimate_component_is_not_removed() -> None:
    source = _shifted_table()
    source["rows"] = [_row("only", [10, -10, 40, 40], 0)]
    source["equations"] = [
        _equation(
            "only-horizontal",
            "HORIZONTAL_ROW",
            [_term("only", "a"), _term("only", "b"), _term("only", "unused")],
            "only",
            "total",
        )
    ]

    result = build_accounting_row_width_total_column_seal_v1(source)

    assert result["status"] == "SEALED_EXACT_RAW_COLUMN_BINDING"
    assert result["relocation_receipts"] == []
    assert result["effective_projection"] == result["raw_table_snapshot"]


def test_multiple_unowned_duplicate_total_values_are_unresolved() -> None:
    source = _shifted_table()
    source["rows"] = [_row("only", [30, 30, 30, 30], 0)]
    source["equations"] = [
        _equation(
            "only-horizontal",
            "HORIZONTAL_ROW",
            [_term("only", "a")],
            "only",
            "total",
        )
    ]

    result = build_accounting_row_width_total_column_seal_v1(source)

    assert result["status"] == "UNRESOLVED"
    assert result["unresolved_reasons"] == ["NO_ALL_EQUATION_CLOSING_PROJECTION"]
    assert result["relocation_receipts"] == []


def test_two_plausible_shifted_values_without_unique_structural_presence_are_unresolved() -> None:
    source = _shifted_table()
    source["rows"] = [_row("only", [30, 30, 30, None], 0)]
    source["equations"] = [
        _equation(
            "only-horizontal",
            "HORIZONTAL_ROW",
            [_term("only", "a")],
            "only",
            "total",
        )
    ]

    result = build_accounting_row_width_total_column_seal_v1(source)

    assert result["status"] == "UNRESOLVED"
    assert result["effective_projection"] == result["raw_table_snapshot"]


def test_two_possible_total_bindings_are_unresolved_without_projection() -> None:
    source = _shifted_table()
    source["columns"][-2]["column_kind"] = "TOTAL"
    result = build_accounting_row_width_total_column_seal_v1(source)
    assert result["status"] == "UNRESOLVED"
    assert result["unresolved_reasons"] == ["AMBIGUOUS_OR_NON_RIGHT_EDGE_TOTAL_COLUMN_BINDING"]
    assert result["effective_projection"] == result["raw_table_snapshot"]


def test_tampered_receipt_does_not_replay() -> None:
    source = _shifted_table()
    result = build_accounting_row_width_total_column_seal_v1(source)
    result["relocation_receipts"][0]["action_kind"] = "FORGED"
    with pytest.raises(AccountingRowWidthTotalColumnSealV1Error):
        validate_accounting_row_width_total_column_seal_replay_v1(result, source)
