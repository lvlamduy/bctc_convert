"""Seal a uniquely proved right-edge total-column projection.

The primitive consumes already typed exact money cells.  It never parses raw
money text and never overwrites its source snapshot.  A shifted right-edge
value or a duplicated total may be projected only when one and only one
projection closes every declared horizontal equation and every affected
vertical rollforward.  The equation inventory is an exact binding to an
externally pinned config/evidence authority; its self-hash detects drift but
does not authenticate that external authority.  Blank cells are unknown, not
zero.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from itertools import product
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "AccountingRowWidthTotalColumnSealV1Error",
    "build_accounting_equation_inventory_manifest_v1",
    "build_accounting_row_width_total_column_seal_v1",
    "validate_accounting_row_width_total_column_seal_replay_v1",
]


FORMAT_VERSION = "ROW_WIDTH_TOTAL_COLUMN_SEAL_V1"
CLAIM_BOUNDARY = (
    "EXACT_ORDERED_COLUMNS_UNIQUE_RIGHT_EDGE_TOTAL_AND_UNIQUE_ALL_EQUATION_"
    "CLOSURE_PROJECTION_ONLY_NO_RAW_CELL_MUTATION_BLANK_TO_ZERO_PERIOD_UNIT_"
    "TABLE_ROOT_SCHEMA_OR_MAPPING_AUTHORITY_EXTERNAL_EQUATION_CONFIG_OR_EVIDENCE_"
    "AUTHORITY_MUST_BE_CALLER_VERIFIED_NOT_SELF_AUTHENTICATED"
)
_SAFETY = {
    "blank_cell_means_zero": False,
    "dash_and_printed_zero_are_typed_exact_zero": True,
    "external_equation_authority_must_be_verified_by_caller": True,
    "family_bank_file_or_page_routing": False,
    "raw_cells_mutated": False,
    "relocation_requires_unique_all_equation_closure": True,
    "schema_or_mapping_authority": False,
    "self_hash_authenticates_external_equation_authority": False,
}

_INPUT_FIELDS = {
    "columns",
    "equation_inventory",
    "equations",
    "period_id",
    "rows",
    "table_id",
    "unit_id",
}
_COLUMN_FIELDS = {"column_id", "column_kind", "column_ordinal"}
_ROW_FIELDS = {"cells", "row_id", "row_kind", "row_ordinal"}
_CELL_FIELDS = {"coefficient", "source_locator", "source_text", "state"}
_EQUATION_FIELDS = {"axis", "equation_id", "result", "terms"}
_REFERENCE_FIELDS = {"column_id", "row_id"}
_TERM_FIELDS = {"column_id", "multiplier", "row_id"}
_INVENTORY_FIELDS = {"authority", "equation_bindings", "manifest_sha256"}
_AUTHORITY_FIELDS = {"authority_kind", "authority_ref", "authority_sha256"}
_EQUATION_BINDING_FIELDS = {
    "axis",
    "coordinate_refs",
    "equation_id",
    "equation_sha256",
}
_COORDINATE_REF_FIELDS = {"column_id", "reference_kind", "row_id"}
_RESULT_FIELDS = {
    "claim_boundary",
    "effective_projection",
    "format_version",
    "raw_table_snapshot",
    "relocation_receipts",
    "safety",
    "seal_id",
    "status",
    "unresolved_reasons",
}
_NUMERIC_STATES = {"DASH_ZERO", "NUMBER", "PRINTED_ZERO"}


class AccountingRowWidthTotalColumnSealV1Error(ValueError):
    """The typed table, equation contract, result, or replay drifted."""


def _error(message: str) -> AccountingRowWidthTotalColumnSealV1Error:
    return AccountingRowWidthTotalColumnSealV1Error(message)


def _exact_cell(value: Any, *, label: str) -> dict[str, Any]:
    """Validate one typed exact money cell without reparsing ``source_text``."""

    if (
        type(value) is not dict
        or set(value) != _CELL_FIELDS
        or value["state"] not in {*_NUMERIC_STATES, "BLANK"}
        or type(value["source_text"]) is not str
        or type(value["source_locator"]) is not dict
        or not value["source_locator"]
    ):
        raise _error(f"{label} typed exact-cell contract drifted")
    coefficient = value["coefficient"]
    state = value["state"]
    if state == "BLANK":
        if coefficient is not None:
            raise _error(f"{label} blank cell cannot carry a coefficient")
    elif type(coefficient) is not int:
        raise _error(f"{label} numeric coefficient must be one non-boolean integer")
    elif state in {"DASH_ZERO", "PRINTED_ZERO"} and coefficient != 0:
        raise _error(f"{label} typed zero must have coefficient zero")
    elif state == "NUMBER" and coefficient == 0:
        raise _error(f"{label} visible zero must be typed as DASH_ZERO or PRINTED_ZERO")
    return canonical_clone_v1(value)


def _cell_coefficient(value: Mapping[str, Any] | None) -> int | None:
    if value is None or value["state"] == "BLANK":
        return None
    coefficient = value["coefficient"]
    if type(coefficient) is not int:
        raise _error("effective numeric cell coefficient drifted")
    return coefficient


def _typed_numeric_equal(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return (
        left["state"] == right["state"]
        and left["coefficient"] == right["coefficient"]
        and left["source_text"] == right["source_text"]
    )


def _reference(value: Any, rows: set[str], columns: set[str], *, label: str) -> dict[str, str]:
    if (
        type(value) is not dict
        or set(value) != _REFERENCE_FIELDS
        or value["row_id"] not in rows
        or value["column_id"] not in columns
    ):
        raise _error(f"{label} cell reference drifted")
    return canonical_clone_v1(value)


def _is_sha256(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _equation_coordinate_refs(equation: Mapping[str, Any]) -> list[dict[str, str]]:
    refs = [
        {
            "column_id": equation["result"]["column_id"],
            "reference_kind": "RESULT",
            "row_id": equation["result"]["row_id"],
        }
    ]
    refs.extend(
        {
            "column_id": term["column_id"],
            "reference_kind": "TERM",
            "row_id": term["row_id"],
        }
        for term in equation["terms"]
    )
    return sorted(
        refs,
        key=lambda item: (item["reference_kind"], item["row_id"], item["column_id"]),
    )


def _equation_binding(equation: Any) -> dict[str, Any]:
    if (
        type(equation) is not dict
        or set(equation) != _EQUATION_FIELDS
        or equation["axis"] not in {"HORIZONTAL_ROW", "VERTICAL_ROLLFORWARD"}
        or type(equation["equation_id"]) is not str
        or not equation["equation_id"]
        or type(equation["result"]) is not dict
        or set(equation["result"]) != _REFERENCE_FIELDS
        or not all(
            type(equation["result"][field]) is str and equation["result"][field]
            for field in _REFERENCE_FIELDS
        )
        or type(equation["terms"]) is not list
        or not equation["terms"]
    ):
        raise _error("equation inventory source equation drifted")
    coordinates = {
        (equation["result"]["row_id"], equation["result"]["column_id"]),
    }
    for term in equation["terms"]:
        if (
            type(term) is not dict
            or set(term) != _TERM_FIELDS
            or type(term["row_id"]) is not str
            or not term["row_id"]
            or type(term["column_id"]) is not str
            or not term["column_id"]
            or type(term["multiplier"]) is not int
            or term["multiplier"] == 0
            or (term["row_id"], term["column_id"]) in coordinates
        ):
            raise _error("equation inventory source term drifted")
        coordinates.add((term["row_id"], term["column_id"]))
    return {
        "axis": equation["axis"],
        "coordinate_refs": _equation_coordinate_refs(equation),
        "equation_id": equation["equation_id"],
        "equation_sha256": canonical_json_sha256_v1(equation),
    }


def build_accounting_equation_inventory_manifest_v1(
    equations: Any,
    *,
    authority_kind: str,
    authority_ref: str,
    authority_sha256: str,
) -> dict[str, Any]:
    """Bind exact equations to a caller-verified config/evidence authority.

    The returned self-hash detects manifest drift.  It does not establish the
    authenticity of ``authority_ref`` or ``authority_sha256``; the caller must
    verify and pin that external authority before invoking this primitive.
    """

    if (
        authority_kind not in {"PINNED_CONFIG", "PINNED_EVIDENCE"}
        or type(authority_ref) is not str
        or not authority_ref
        or not _is_sha256(authority_sha256)
        or type(equations) is not list
        or not equations
    ):
        raise _error("external equation inventory authority contract drifted")
    bindings = sorted(
        (_equation_binding(equation) for equation in equations),
        key=lambda binding: binding["equation_id"],
    )
    equation_ids = [binding["equation_id"] for binding in bindings]
    if len(equation_ids) != len(set(equation_ids)):
        raise _error("equation inventory identifiers repeat")
    material = {
        "authority": {
            "authority_kind": authority_kind,
            "authority_ref": authority_ref,
            "authority_sha256": authority_sha256,
        },
        "equation_bindings": bindings,
    }
    return {**material, "manifest_sha256": canonical_json_sha256_v1(material)}


def _equation_inventory(value: Any, rows: set[str], columns: set[str]) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _INVENTORY_FIELDS
        or type(value["authority"]) is not dict
        or set(value["authority"]) != _AUTHORITY_FIELDS
        or value["authority"]["authority_kind"] not in {"PINNED_CONFIG", "PINNED_EVIDENCE"}
        or type(value["authority"]["authority_ref"]) is not str
        or not value["authority"]["authority_ref"]
        or not _is_sha256(value["authority"]["authority_sha256"])
        or type(value["equation_bindings"]) is not list
        or not value["equation_bindings"]
        or not _is_sha256(value["manifest_sha256"])
    ):
        raise _error("equation inventory manifest contract drifted")
    bindings = []
    equation_ids: set[str] = set()
    for raw in value["equation_bindings"]:
        if (
            type(raw) is not dict
            or set(raw) != _EQUATION_BINDING_FIELDS
            or raw["axis"] not in {"HORIZONTAL_ROW", "VERTICAL_ROLLFORWARD"}
            or type(raw["equation_id"]) is not str
            or not raw["equation_id"]
            or raw["equation_id"] in equation_ids
            or not _is_sha256(raw["equation_sha256"])
            or type(raw["coordinate_refs"]) is not list
            or len(raw["coordinate_refs"]) < 2
        ):
            raise _error("equation inventory binding drifted")
        equation_ids.add(raw["equation_id"])
        refs = []
        coordinate_ids: set[tuple[str, str]] = set()
        result_count = 0
        for ref in raw["coordinate_refs"]:
            if (
                type(ref) is not dict
                or set(ref) != _COORDINATE_REF_FIELDS
                or ref["reference_kind"] not in {"RESULT", "TERM"}
                or ref["row_id"] not in rows
                or ref["column_id"] not in columns
                or (ref["row_id"], ref["column_id"]) in coordinate_ids
            ):
                raise _error("equation inventory coordinate coverage drifted")
            coordinate_ids.add((ref["row_id"], ref["column_id"]))
            result_count += ref["reference_kind"] == "RESULT"
            refs.append(canonical_clone_v1(ref))
        expected_refs = sorted(
            refs,
            key=lambda item: (item["reference_kind"], item["row_id"], item["column_id"]),
        )
        if result_count != 1 or not same_typed_json_v1(refs, expected_refs):
            raise _error("equation inventory coordinate ordering or result coverage drifted")
        bindings.append({**canonical_clone_v1(raw), "coordinate_refs": refs})
    if bindings != sorted(bindings, key=lambda binding: binding["equation_id"]):
        raise _error("equation inventory binding order drifted")
    material = {
        "authority": canonical_clone_v1(value["authority"]),
        "equation_bindings": bindings,
    }
    if value["manifest_sha256"] != canonical_json_sha256_v1(material):
        raise _error("equation inventory manifest self-hash drifted")
    return {**material, "manifest_sha256": value["manifest_sha256"]}


def _input(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _INPUT_FIELDS
        or type(value["table_id"]) is not str
        or not value["table_id"]
        or type(value["period_id"]) is not str
        or not value["period_id"]
        or type(value["unit_id"]) is not str
        or not value["unit_id"]
        or type(value["columns"]) is not list
        or len(value["columns"]) < 2
        or type(value["rows"]) is not list
        or not value["rows"]
        or type(value["equations"]) is not list
        or not value["equations"]
    ):
        raise _error("row-width seal input fields drifted")

    columns: list[dict[str, Any]] = []
    for ordinal, raw in enumerate(value["columns"]):
        if (
            type(raw) is not dict
            or set(raw) != _COLUMN_FIELDS
            or type(raw["column_id"]) is not str
            or not raw["column_id"]
            or raw["column_ordinal"] != ordinal
            or raw["column_kind"] not in {"DETAIL", "TOTAL"}
        ):
            raise _error("ordered column contract drifted")
        columns.append(canonical_clone_v1(raw))
    column_ids = [column["column_id"] for column in columns]
    if len(column_ids) != len(set(column_ids)):
        raise _error("ordered column identifiers repeat")
    totals = [column for column in columns if column["column_kind"] == "TOTAL"]
    unique_right_edge_total = len(totals) == 1 and totals[0]["column_ordinal"] == len(columns) - 1

    rows: list[dict[str, Any]] = []
    for ordinal, raw in enumerate(value["rows"]):
        if (
            type(raw) is not dict
            or set(raw) != _ROW_FIELDS
            or type(raw["row_id"]) is not str
            or not raw["row_id"]
            or raw["row_ordinal"] != ordinal
            or raw["row_kind"] not in {"DATA", "GROUP"}
            or type(raw["cells"]) is not dict
            or set(raw["cells"]) != set(column_ids)
        ):
            raise _error("ordered row contract drifted")
        cells = {
            column_id: _exact_cell(
                raw["cells"][column_id], label=f"row {raw['row_id']} column {column_id}"
            )
            for column_id in column_ids
        }
        if raw["row_kind"] == "GROUP" and any(cell["state"] != "BLANK" for cell in cells.values()):
            raise _error("GROUP row blanks must remain typed BLANK cells")
        rows.append({**canonical_clone_v1(raw), "cells": cells})
    row_ids = [row["row_id"] for row in rows]
    if len(row_ids) != len(set(row_ids)):
        raise _error("ordered row identifiers repeat")

    row_set = set(row_ids)
    column_set = set(column_ids)
    equations: list[dict[str, Any]] = []
    equation_ids: set[str] = set()
    for raw in value["equations"]:
        if (
            type(raw) is not dict
            or set(raw) != _EQUATION_FIELDS
            or type(raw["equation_id"]) is not str
            or not raw["equation_id"]
            or raw["equation_id"] in equation_ids
            or raw["axis"] not in {"HORIZONTAL_ROW", "VERTICAL_ROLLFORWARD"}
            or type(raw["terms"]) is not list
            or not raw["terms"]
        ):
            raise _error("row-width equation contract drifted")
        equation_ids.add(raw["equation_id"])
        result = _reference(raw["result"], row_set, column_set, label="equation result")
        terms = []
        coordinates: set[tuple[str, str]] = set()
        for term in raw["terms"]:
            if (
                type(term) is not dict
                or set(term) != _TERM_FIELDS
                or type(term["multiplier"]) is not int
                or term["multiplier"] == 0
            ):
                raise _error("row-width equation term drifted")
            reference = _reference(
                {"column_id": term["column_id"], "row_id": term["row_id"]},
                row_set,
                column_set,
                label="equation term",
            )
            coordinate = (reference["row_id"], reference["column_id"])
            if coordinate in coordinates or coordinate == (
                result["row_id"],
                result["column_id"],
            ):
                raise _error("row-width equation coordinates repeat or self-reference")
            coordinates.add(coordinate)
            terms.append(canonical_clone_v1(term))
        if raw["axis"] == "HORIZONTAL_ROW":
            if (unique_right_edge_total and result["column_id"] != totals[0]["column_id"]) or any(
                term["row_id"] != result["row_id"] for term in terms
            ):
                raise _error("horizontal equation must bind one row to the unique TOTAL")
        elif any(term["column_id"] != result["column_id"] for term in terms):
            raise _error("vertical rollforward must remain in one exact column")
        equations.append(
            {
                "axis": raw["axis"],
                "equation_id": raw["equation_id"],
                "result": result,
                "terms": terms,
            }
        )
    group_ids = {row["row_id"] for row in rows if row["row_kind"] == "GROUP"}
    if any(
        equation["result"]["row_id"] in group_ids
        or any(term["row_id"] in group_ids for term in equation["terms"])
        for equation in equations
    ):
        raise _error("GROUP row blanks cannot participate in arithmetic equations")
    equation_inventory = _equation_inventory(value["equation_inventory"], row_set, column_set)
    return {
        "columns": columns,
        "equation_inventory": equation_inventory,
        "equations": equations,
        "period_id": value["period_id"],
        "rows": rows,
        "table_id": value["table_id"],
        "unit_id": value["unit_id"],
    }


def _equation_inventory_matches(table: Mapping[str, Any]) -> bool:
    expected = table["equation_inventory"]["equation_bindings"]
    actual = sorted(
        (_equation_binding(equation) for equation in table["equations"]),
        key=lambda binding: binding["equation_id"],
    )
    return same_typed_json_v1(expected, actual)


def _coordinates(table: Mapping[str, Any]) -> dict[tuple[str, str], dict[str, Any] | None]:
    return {
        (row["row_id"], column["column_id"]): canonical_clone_v1(row["cells"][column["column_id"]])
        for row in table["rows"]
        for column in table["columns"]
    }


def _equation_closes(
    equation: Mapping[str, Any],
    coordinates: Mapping[tuple[str, str], Mapping[str, Any] | None],
    column_ids: Sequence[str],
) -> bool:
    result_ref = equation["result"]
    result = _cell_coefficient(coordinates[(result_ref["row_id"], result_ref["column_id"])])
    terms = [
        (
            term["multiplier"],
            _cell_coefficient(coordinates[(term["row_id"], term["column_id"])]),
        )
        for term in equation["terms"]
    ]
    arithmetic_closes = (
        result is not None
        and all(value is not None for _, value in terms)
        and result == sum(multiplier * value for multiplier, value in terms if value is not None)
    )
    if not arithmetic_closes or equation["axis"] != "HORIZONTAL_ROW":
        return arithmetic_closes
    # Ordered width is part of the proof: a cell omitted from the declared
    # horizontal terms is structurally absent, never an uncounted value.
    row_id = result_ref["row_id"]
    occupied = {result_ref["column_id"], *(term["column_id"] for term in equation["terms"])}
    return all(
        coordinates[(row_id, column_id)] is None
        or coordinates[(row_id, column_id)]["state"] == "BLANK"
        for column_id in column_ids
        if column_id not in occupied
    )


def _action_candidates(table: Mapping[str, Any]) -> list[dict[str, Any]]:
    columns = table["columns"]
    total_id = columns[-1]["column_id"]
    horizontal_by_row = {
        equation["result"]["row_id"]: equation
        for equation in table["equations"]
        if equation["axis"] == "HORIZONTAL_ROW"
    }
    candidates = []
    for row in table["rows"]:
        if row["row_kind"] != "DATA" or row["row_id"] not in horizontal_by_row:
            continue
        total = row["cells"][total_id]
        preceding = [
            column
            for column in columns[:-1]
            if row["cells"][column["column_id"]]["state"] in _NUMERIC_STATES
        ]
        if not preceding:
            continue
        source_column = preceding[-1]
        source_ordinal = source_column["column_ordinal"]
        if any(
            row["cells"][column["column_id"]]["state"] != "BLANK"
            for column in columns[source_ordinal + 1 : -1]
        ):
            continue
        source = row["cells"][source_column["column_id"]]
        if total["state"] == "BLANK":
            kind = "RELOCATE_RIGHTMOST_EARLIER_VALUE_TO_TOTAL"
        elif _typed_numeric_equal(source, total):
            kind = "REMOVE_UNIQUE_DUPLICATED_TOTAL_SOURCE"
        else:
            continue
        candidates.append(
            {
                "action_kind": kind,
                "from": {"column_id": source_column["column_id"], "row_id": row["row_id"]},
                "to": {"column_id": total_id, "row_id": row["row_id"]},
            }
        )
    return candidates


def _apply_actions(
    raw: Mapping[tuple[str, str], Mapping[str, Any] | None],
    actions: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, str], dict[str, Any] | None]:
    effective = {coordinate: canonical_clone_v1(cell) for coordinate, cell in raw.items()}
    for action in actions:
        source = (action["from"]["row_id"], action["from"]["column_id"])
        target = (action["to"]["row_id"], action["to"]["column_id"])
        if action["action_kind"] == "RELOCATE_RIGHTMOST_EARLIER_VALUE_TO_TOTAL":
            effective[target] = canonical_clone_v1(effective[source])
        effective[source] = None
    return effective


def _affected_equations(
    action: Mapping[str, Any], table: Mapping[str, Any]
) -> list[dict[str, Any]]:
    changed = {
        (action["from"]["row_id"], action["from"]["column_id"]),
        (action["to"]["row_id"], action["to"]["column_id"]),
    }
    affected = []
    for equation in table["equations"]:
        references = {
            (equation["result"]["row_id"], equation["result"]["column_id"]),
            *((term["row_id"], term["column_id"]) for term in equation["terms"]),
        }
        if references & changed:
            affected.append(equation)
    return affected


def _action_has_authoritative_equation_frontier(
    action: Mapping[str, Any], table: Mapping[str, Any]
) -> bool:
    affected = _affected_equations(action, table)
    return any(equation["axis"] == "HORIZONTAL_ROW" for equation in affected) and any(
        equation["axis"] == "VERTICAL_ROLLFORWARD" for equation in affected
    )


def _effective_projection(
    table: Mapping[str, Any],
    coordinates: Mapping[tuple[str, str], Mapping[str, Any] | None],
) -> dict[str, Any]:
    result = canonical_clone_v1(table)
    for row in result["rows"]:
        for column in result["columns"]:
            row["cells"][column["column_id"]] = canonical_clone_v1(
                coordinates[(row["row_id"], column["column_id"])]
            )
    return result


def _receipt(
    action: Mapping[str, Any],
    table: Mapping[str, Any],
    raw: Mapping[tuple[str, str], Mapping[str, Any] | None],
    effective: Mapping[tuple[str, str], Mapping[str, Any] | None],
) -> dict[str, Any]:
    affected = [
        {
            "axis": equation["axis"],
            "equation_id": equation["equation_id"],
            "equation_sha256": canonical_json_sha256_v1(equation),
        }
        for equation in _affected_equations(action, table)
    ]
    affected.sort(key=lambda item: (item["axis"], item["equation_id"]))
    if not any(item["axis"] == "HORIZONTAL_ROW" for item in affected) or not any(
        item["axis"] == "VERTICAL_ROLLFORWARD" for item in affected
    ):
        raise _error("relocation proof lacks horizontal or affected vertical equations")
    material = {
        "action_kind": action["action_kind"],
        "affected_equations": affected,
        "equation_inventory_authority": canonical_clone_v1(
            table["equation_inventory"]["authority"]
        ),
        "equation_inventory_manifest_sha256": table["equation_inventory"]["manifest_sha256"],
        "effective_from_cell": canonical_clone_v1(
            effective[(action["from"]["row_id"], action["from"]["column_id"])]
        ),
        "effective_to_cell": canonical_clone_v1(
            effective[(action["to"]["row_id"], action["to"]["column_id"])]
        ),
        "from": canonical_clone_v1(action["from"]),
        "raw_from_cell": canonical_clone_v1(
            raw[(action["from"]["row_id"], action["from"]["column_id"])]
        ),
        "raw_to_cell": canonical_clone_v1(raw[(action["to"]["row_id"], action["to"]["column_id"])]),
        "to": canonical_clone_v1(action["to"]),
    }
    return {**material, "receipt_id": "rwtcsv1:receipt:" + canonical_json_sha256_v1(material)}


def _result(
    table: Mapping[str, Any],
    effective: Mapping[tuple[str, str], Mapping[str, Any] | None],
    actions: Sequence[Mapping[str, Any]],
    *,
    status: str,
    unresolved_reasons: Sequence[str],
) -> dict[str, Any]:
    raw = _coordinates(table)
    receipts = [_receipt(action, table, raw, effective) for action in actions]
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "effective_projection": _effective_projection(table, effective),
        "format_version": FORMAT_VERSION,
        "raw_table_snapshot": canonical_clone_v1(table),
        "relocation_receipts": receipts,
        "safety": canonical_clone_v1(_SAFETY),
        "status": status,
        "unresolved_reasons": list(unresolved_reasons),
    }
    return {**material, "seal_id": "rwtcsv1:seal:" + canonical_json_sha256_v1(material)}


def build_accounting_row_width_total_column_seal_v1(value: Any) -> dict[str, Any]:
    """Return the raw axis unchanged or one uniquely equation-proved projection."""

    table = _input(value)
    raw = _coordinates(table)
    if not _equation_inventory_matches(table):
        return _result(
            table,
            raw,
            [],
            status="UNRESOLVED",
            unresolved_reasons=["EQUATION_INVENTORY_EXACT_SET_OR_COVERAGE_MISMATCH"],
        )
    totals = [column for column in table["columns"] if column["column_kind"] == "TOTAL"]
    if len(totals) != 1 or totals[0]["column_ordinal"] != len(table["columns"]) - 1:
        return _result(
            table,
            raw,
            [],
            status="UNRESOLVED",
            unresolved_reasons=["AMBIGUOUS_OR_NON_RIGHT_EDGE_TOTAL_COLUMN_BINDING"],
        )
    data_rows = {row["row_id"] for row in table["rows"] if row["row_kind"] == "DATA"}
    horizontal_counts = Counter(
        equation["result"]["row_id"]
        for equation in table["equations"]
        if equation["axis"] == "HORIZONTAL_ROW"
    )
    if set(horizontal_counts) != data_rows or any(
        count != 1 for count in horizontal_counts.values()
    ):
        return _result(
            table,
            raw,
            [],
            status="UNRESOLVED",
            unresolved_reasons=["INCOMPLETE_AUTHORITATIVE_HORIZONTAL_EQUATION_COVERAGE"],
        )
    column_ids = [column["column_id"] for column in table["columns"]]
    if all(_equation_closes(equation, raw, column_ids) for equation in table["equations"]):
        return _result(
            table,
            raw,
            [],
            status="SEALED_EXACT_RAW_COLUMN_BINDING",
            unresolved_reasons=[],
        )

    candidates = _action_candidates(table)
    if len(candidates) > 16:
        return _result(
            table,
            raw,
            [],
            status="UNRESOLVED",
            unresolved_reasons=["CORRECTION_CANDIDATE_SEARCH_BOUND_EXCEEDED"],
        )
    by_row = {candidate["from"]["row_id"]: candidate for candidate in candidates}
    valid: list[tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any] | None]]] = []
    ordered = [by_row[row_id] for row_id in sorted(by_row)]
    for choices in product((False, True), repeat=len(ordered)):
        selected = [candidate for candidate, use in zip(ordered, choices, strict=True) if use]
        if not selected:
            continue
        if any(
            not _action_has_authoritative_equation_frontier(action, table) for action in selected
        ):
            continue
        effective = _apply_actions(raw, selected)
        if all(
            _equation_closes(equation, effective, column_ids) for equation in table["equations"]
        ):
            valid.append((selected, effective))
            if len(valid) > 1:
                break
    if len(valid) != 1:
        reason = (
            "MULTIPLE_ALL_EQUATION_CLOSING_PROJECTIONS"
            if len(valid) > 1
            else "NO_ALL_EQUATION_CLOSING_PROJECTION"
        )
        return _result(
            table,
            raw,
            [],
            status="UNRESOLVED",
            unresolved_reasons=[reason],
        )
    actions, effective = valid[0]
    return _result(
        table,
        effective,
        actions,
        status="SEALED_UNIQUE_ALL_EQUATION_CLOSING_PROJECTION",
        unresolved_reasons=[],
    )


def _validate_result(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _RESULT_FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or value["status"]
        not in {
            "SEALED_EXACT_RAW_COLUMN_BINDING",
            "SEALED_UNIQUE_ALL_EQUATION_CLOSING_PROJECTION",
            "UNRESOLVED",
        }
        or type(value["unresolved_reasons"]) is not list
        or any(type(reason) is not str or not reason for reason in value["unresolved_reasons"])
        or type(value["relocation_receipts"]) is not list
        or type(value["raw_table_snapshot"]) is not dict
        or type(value["effective_projection"]) is not dict
    ):
        raise _error("row-width total-column seal result drifted")
    if (value["status"] == "UNRESOLVED") != bool(value["unresolved_reasons"]):
        raise _error("row-width total-column status/reason contract drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("seal_id")
    if identity != "rwtcsv1:seal:" + canonical_json_sha256_v1(material):
        raise _error("row-width total-column seal identity drifted")
    return canonical_clone_v1(value)


def validate_accounting_row_width_total_column_seal_replay_v1(
    value: Any, source: Any
) -> dict[str, Any]:
    """Rebuild the seal from the source and require typed byte-equivalence."""

    persisted = _validate_result(value)
    expected = build_accounting_row_width_total_column_seal_v1(source)
    if not same_typed_json_v1(persisted, expected):
        raise _error("row-width total-column seal does not replay exactly")
    return persisted
