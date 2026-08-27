"""Collapse exact visible subtotal blocks without mutating source rows.

A block is one visible subtotal followed immediately by at least two direct,
more-indented children.  Every typed MONEY lane must close exactly using the
signed integer coefficients.  The output contains only effective-parent and
block receipts; subtotal and child mappings may coexist, while each declared
equation frontier must consume exactly the subtotal or exactly all children.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from bctc_ai.evaluation.accounting_row_width_total_column_seal_v1 import (
    AccountingRowWidthTotalColumnSealV1Error,
    _cell_coefficient,
    _exact_cell,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "OrderedVisibleSubtotalBlockCollapseV1Error",
    "build_ordered_visible_subtotal_block_collapse_v1",
    "validate_ordered_visible_subtotal_block_collapse_replay_v1",
]


FORMAT_VERSION = "ORDERED_VISIBLE_SUBTOTAL_BLOCK_COLLAPSE_V1"
CLAIM_BOUNDARY = (
    "CONTIGUOUS_VISIBLE_SUBTOTAL_AND_DIRECT_CHILD_EXACT_ALL_MONEY_LANE_COLLAPSE_"
    "WITH_SINGLE_EQUATION_FRONTIER_ONLY_NO_SOURCE_MUTATION_CROSS_TABLE_ROOT_"
    "PERIOD_UNIT_REUSE_SCHEMA_OR_MAPPING_AUTHORITY"
)
_SAFETY = {
    "blank_cell_means_zero": False,
    "cross_root_period_unit_or_table_collapse": False,
    "family_bank_file_or_page_routing": False,
    "signed_integer_money_arithmetic": True,
    "source_rows_mutated": False,
    "subtotal_and_descendants_double_consumed": False,
}

_INPUT_FIELDS = {"equation_frontiers", "mappings", "rows"}
_ROW_FIELDS = {
    "cells",
    "hierarchy_level",
    "money_lane_ids",
    "source_parent_row_id",
    "period_id",
    "root_id",
    "row_id",
    "row_kind",
    "row_ordinal",
    "table_id",
    "unit_id",
}
_MAPPING_FIELDS = {"mapping_id", "role_id", "row_id"}
_FRONTIER_FIELDS = {"equation_id", "mapping_ids", "subtotal_row_id"}
_RESULT_FIELDS = {
    "block_receipts",
    "claim_boundary",
    "collapse_id",
    "effective_parent_relations",
    "format_version",
    "input_axis_sha256",
    "safety",
    "status",
    "unresolved_reasons",
}


class OrderedVisibleSubtotalBlockCollapseV1Error(ValueError):
    """The ordered row axis, selected frontier, result, or replay drifted."""


def _error(message: str) -> OrderedVisibleSubtotalBlockCollapseV1Error:
    return OrderedVisibleSubtotalBlockCollapseV1Error(message)


def _nonempty_string(value: Any) -> bool:
    return type(value) is str and bool(value)


def _input(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _INPUT_FIELDS
        or type(value["rows"]) is not list
        or not value["rows"]
        or type(value["mappings"]) is not list
        or type(value["equation_frontiers"]) is not list
    ):
        raise _error("ordered subtotal-collapse input fields drifted")

    rows = []
    row_ids: set[str] = set()
    for ordinal, raw in enumerate(value["rows"]):
        if (
            type(raw) is not dict
            or set(raw) != _ROW_FIELDS
            or not _nonempty_string(raw["row_id"])
            or raw["row_id"] in row_ids
            or raw["row_ordinal"] != ordinal
            or raw["row_kind"] not in {"DETAIL", "PEER", "RESET", "SUBTOTAL"}
            or type(raw["hierarchy_level"]) is not int
            or raw["hierarchy_level"] < 0
            or (
                raw["source_parent_row_id"] is not None
                and not _nonempty_string(raw["source_parent_row_id"])
            )
            or any(
                not _nonempty_string(raw[field])
                for field in ("period_id", "root_id", "table_id", "unit_id")
            )
            or type(raw["money_lane_ids"]) is not list
            or not raw["money_lane_ids"]
            or any(not _nonempty_string(lane) for lane in raw["money_lane_ids"])
            or len(raw["money_lane_ids"]) != len(set(raw["money_lane_ids"]))
            or type(raw["cells"]) is not dict
            or set(raw["cells"]) != set(raw["money_lane_ids"])
        ):
            raise _error("ordered subtotal-collapse row contract drifted")
        row_ids.add(raw["row_id"])
        try:
            cells = {
                lane: _exact_cell(
                    raw["cells"][lane], label=f"row {raw['row_id']} MONEY lane {lane}"
                )
                for lane in raw["money_lane_ids"]
            }
        except AccountingRowWidthTotalColumnSealV1Error as exc:
            raise _error("ordered subtotal-collapse typed MONEY cell drifted") from exc
        rows.append({**canonical_clone_v1(raw), "cells": cells})

    mappings = []
    mapping_ids: set[str] = set()
    for raw in value["mappings"]:
        if (
            type(raw) is not dict
            or set(raw) != _MAPPING_FIELDS
            or not _nonempty_string(raw["mapping_id"])
            or raw["mapping_id"] in mapping_ids
            or not _nonempty_string(raw["role_id"])
            or raw["row_id"] not in row_ids
        ):
            raise _error("ordered subtotal-collapse mapping contract drifted")
        mapping_ids.add(raw["mapping_id"])
        mappings.append(canonical_clone_v1(raw))

    frontiers = []
    frontier_keys: set[tuple[str, str]] = set()
    for raw in value["equation_frontiers"]:
        if (
            type(raw) is not dict
            or set(raw) != _FRONTIER_FIELDS
            or not _nonempty_string(raw["equation_id"])
            or raw["subtotal_row_id"] not in row_ids
            or type(raw["mapping_ids"]) is not list
            or not raw["mapping_ids"]
            or any(mapping_id not in mapping_ids for mapping_id in raw["mapping_ids"])
            or len(raw["mapping_ids"]) != len(set(raw["mapping_ids"]))
            or (raw["equation_id"], raw["subtotal_row_id"]) in frontier_keys
        ):
            raise _error("ordered subtotal-collapse equation frontier drifted")
        frontier_keys.add((raw["equation_id"], raw["subtotal_row_id"]))
        frontiers.append(canonical_clone_v1(raw))
    return {"equation_frontiers": frontiers, "mappings": mappings, "rows": rows}


def _same_context(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return all(
        left[field] == right[field] for field in ("table_id", "root_id", "period_id", "unit_id")
    )


def _unresolved(source: dict[str, Any], reasons: list[str]) -> dict[str, Any]:
    return _result(source, [], [], status="UNRESOLVED", unresolved_reasons=sorted(set(reasons)))


def _raw_parent_graph_reasons(source: dict[str, Any]) -> list[str]:
    rows_by_id = {row["row_id"]: row for row in source["rows"]}
    reasons = []
    for row in source["rows"]:
        parent_id = row["source_parent_row_id"]
        if parent_id is None or parent_id not in rows_by_id:
            continue
        if parent_id == row["row_id"]:
            reasons.append("RAW_PARENT_SELF_REFERENCE_VETO")
            continue
        parent = rows_by_id[parent_id]
        if (
            parent["row_ordinal"] >= row["row_ordinal"]
            or parent["hierarchy_level"] >= row["hierarchy_level"]
        ):
            reasons.append("RAW_PARENT_DESCENDANT_OR_ORDER_INVERSION_VETO")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(row_id: str) -> None:
        if row_id in visited:
            return
        if row_id in visiting:
            reasons.append("RAW_PARENT_CYCLE_VETO")
            return
        visiting.add(row_id)
        parent_id = rows_by_id[row_id]["source_parent_row_id"]
        if parent_id in rows_by_id:
            visit(parent_id)
        visiting.remove(row_id)
        visited.add(row_id)

    for row_id in rows_by_id:
        visit(row_id)
    return reasons


def _discover_blocks(source: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    rows = source["rows"]
    blocks = []
    reasons: list[str] = _raw_parent_graph_reasons(source)
    for index, subtotal in enumerate(rows):
        if subtotal["row_kind"] != "SUBTOTAL":
            continue
        children = []
        observed_parent_modes = []
        cursor = index + 1
        while cursor < len(rows):
            candidate = rows[cursor]
            if candidate["row_kind"] in {"PEER", "RESET", "SUBTOTAL"}:
                break
            if candidate["row_kind"] != "DETAIL":
                break
            if candidate["hierarchy_level"] <= subtotal["hierarchy_level"]:
                if candidate["source_parent_row_id"] in {
                    subtotal["row_id"],
                    subtotal["source_parent_row_id"],
                }:
                    reasons.append("HIERARCHY_OR_INDENT_MARKER_MISMATCH")
                break
            if candidate["hierarchy_level"] != subtotal["hierarchy_level"] + 1:
                reasons.append("DIRECT_CHILD_DEPTH_MUST_EQUAL_SUBTOTAL_DEPTH_PLUS_ONE")
                break
            if candidate["source_parent_row_id"] == subtotal["row_id"]:
                parent_mode = "ALREADY_CORRECT_DIRECT_PARENT"
            elif (
                subtotal["source_parent_row_id"] is not None
                and candidate["source_parent_row_id"] == subtotal["source_parent_row_id"]
            ):
                parent_mode = "CONSISTENT_FLATTENED_EXTERNAL_PARENT"
            else:
                reasons.append("AMBIGUOUS_VISIBLE_CHILD_PARENT_MARKER_VETO")
                break
            if not _same_context(subtotal, candidate):
                reasons.append("CROSS_TABLE_ROOT_PERIOD_OR_UNIT_CHILD_VETO")
                break
            children.append(candidate)
            observed_parent_modes.append(parent_mode)
            cursor += 1
        if children and any(
            row["source_parent_row_id"] == subtotal["row_id"] for row in rows[cursor:]
        ):
            reasons.append("NONCONTIGUOUS_CHILD_AFTER_PEER_OR_RESET_VETO")
        if len(children) == 1:
            reasons.append("SUBTOTAL_REQUIRES_AT_LEAST_TWO_CONTIGUOUS_CHILDREN")
        if len(children) < 2:
            continue
        parent_modes = set(observed_parent_modes)
        if len(parent_modes) != 1:
            reasons.append("MIXED_RAW_PARENT_PROJECTION_MODES_VETO")
            continue
        if any(child["money_lane_ids"] != subtotal["money_lane_ids"] for child in children):
            reasons.append("MONEY_LANE_AXIS_MISMATCH")
            continue
        lane_equations = []
        arithmetic_ok = True
        for lane in subtotal["money_lane_ids"]:
            subtotal_value = _cell_coefficient(subtotal["cells"][lane])
            child_values = [_cell_coefficient(child["cells"][lane]) for child in children]
            if subtotal_value is None or any(value is None for value in child_values):
                reasons.append("BLANK_OR_UNKNOWN_MONEY_CELL_CANNOT_CLOSE_SUBTOTAL")
                arithmetic_ok = False
                continue
            signed_sum = sum(value for value in child_values if value is not None)
            if signed_sum != subtotal_value:
                reasons.append("VISIBLE_SUBTOTAL_SIGNED_SUM_MISMATCH")
                arithmetic_ok = False
                continue
            lane_equations.append(
                {
                    "child_coefficients": child_values,
                    "lane_id": lane,
                    "signed_sum": signed_sum,
                    "subtotal_coefficient": subtotal_value,
                }
            )
        if arithmetic_ok:
            blocks.append(
                {
                    "children": children,
                    "lane_equations": lane_equations,
                    "parent_projection_mode": next(iter(parent_modes)),
                    "subtotal": subtotal,
                }
            )
    memberships = Counter(
        row["row_id"] for block in blocks for row in [block["subtotal"], *block["children"]]
    )
    if any(count > 1 for count in memberships.values()):
        reasons.append("ROW_REUSED_ACROSS_COLLAPSED_BLOCKS_VETO")
    return blocks, reasons


def _bind_frontiers(
    source: dict[str, Any], blocks: list[dict[str, Any]]
) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    mappings = {mapping["mapping_id"]: mapping for mapping in source["mappings"]}
    blocks_by_subtotal = {block["subtotal"]["row_id"]: block for block in blocks}
    selected_by_subtotal: dict[str, list[dict[str, Any]]] = {
        subtotal_id: [] for subtotal_id in blocks_by_subtotal
    }
    reasons: list[str] = []
    mapping_pairs = Counter(
        (mapping["row_id"], mapping["role_id"]) for mapping in mappings.values()
    )
    if any(count > 1 for count in mapping_pairs.values()):
        reasons.append("DUPLICATE_SOURCE_ROW_ROLE_MAPPING_VETO")
    globally_used: set[tuple[str, str]] = set()
    for frontier in source["equation_frontiers"]:
        subtotal_id = frontier["subtotal_row_id"]
        block = blocks_by_subtotal.get(subtotal_id)
        if block is None:
            reasons.append("SELECTED_FRONTIER_HAS_NO_EXACT_COLLAPSIBLE_BLOCK")
            continue
        selected_pairs = {
            (mappings[mapping_id]["row_id"], mappings[mapping_id]["role_id"])
            for mapping_id in frontier["mapping_ids"]
        }
        if any(pair in globally_used for pair in selected_pairs):
            reasons.append("SOURCE_ROW_ROLE_REUSED_ACROSS_SELECTED_FRONTIERS_VETO")
            continue
        globally_used.update(selected_pairs)
        selected_rows = [mappings[mapping_id]["row_id"] for mapping_id in frontier["mapping_ids"]]
        counts = Counter(selected_rows)
        child_ids = [child["row_id"] for child in block["children"]]
        if counts == Counter({subtotal_id: 1}):
            mode = "SUBTOTAL_FRONTIER"
        elif counts == Counter({child_id: 1 for child_id in child_ids}):
            mode = "DESCENDANT_FRONTIER"
        else:
            reasons.append("SUBTOTAL_DESCENDANT_MIXED_PARTIAL_OR_DOUBLE_CONSUMPTION_VETO")
            continue
        selected_by_subtotal[subtotal_id].append(
            {
                "equation_id": frontier["equation_id"],
                "mapping_ids": canonical_clone_v1(frontier["mapping_ids"]),
                "selection_mode": mode,
            }
        )
    if any(len(frontiers) != 1 for frontiers in selected_by_subtotal.values()):
        reasons.append("BLOCK_REQUIRES_EXACTLY_ONE_SELECTED_EQUATION_FRONTIER")
    return selected_by_subtotal, reasons


def _receipts(
    blocks: list[dict[str, Any]], selected: dict[str, list[dict[str, Any]]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    receipts = []
    relations = []
    for block in blocks:
        subtotal = block["subtotal"]
        children = block["children"]
        context = {
            field: subtotal[field] for field in ("period_id", "root_id", "table_id", "unit_id")
        }
        material = {
            "child_row_ids": [child["row_id"] for child in children],
            "context": context,
            "lane_equations": canonical_clone_v1(block["lane_equations"]),
            "ordered_row_span": [subtotal["row_ordinal"], children[-1]["row_ordinal"]],
            "parent_projection_mode": block["parent_projection_mode"],
            "selected_frontiers": canonical_clone_v1(selected[subtotal["row_id"]]),
            "source_row_sha256s": [canonical_json_sha256_v1(row) for row in [subtotal, *children]],
            "subtotal_row_id": subtotal["row_id"],
        }
        block_id = "ovsbcv1:block:" + canonical_json_sha256_v1(material)
        receipts.append({**material, "block_id": block_id})
        relations.extend(
            {
                "block_id": block_id,
                "child_row_id": child["row_id"],
                "effective_parent_row_id": subtotal["row_id"],
                "raw_source_parent_row_id": child["source_parent_row_id"],
            }
            for child in children
        )
    return receipts, relations


def _result(
    source: dict[str, Any],
    receipts: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    *,
    status: str,
    unresolved_reasons: list[str],
) -> dict[str, Any]:
    material = {
        "block_receipts": canonical_clone_v1(receipts),
        "claim_boundary": CLAIM_BOUNDARY,
        "effective_parent_relations": canonical_clone_v1(relations),
        "format_version": FORMAT_VERSION,
        "input_axis_sha256": canonical_json_sha256_v1(source),
        "safety": canonical_clone_v1(_SAFETY),
        "status": status,
        "unresolved_reasons": canonical_clone_v1(unresolved_reasons),
    }
    return {**material, "collapse_id": "ovsbcv1:collapse:" + canonical_json_sha256_v1(material)}


def build_ordered_visible_subtotal_block_collapse_v1(value: Any) -> dict[str, Any]:
    """Build exact block and effective-parent receipts from an ordered row axis."""

    source = _input(value)
    blocks, reasons = _discover_blocks(source)
    if reasons:
        return _unresolved(source, reasons)
    selected, frontier_reasons = _bind_frontiers(source, blocks)
    if frontier_reasons:
        return _unresolved(source, frontier_reasons)
    receipts, relations = _receipts(blocks, selected)
    return _result(
        source,
        receipts,
        relations,
        status=("COLLAPSED_EXACT_VISIBLE_SUBTOTAL_BLOCKS" if receipts else "NO_ELIGIBLE_BLOCK"),
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
        not in {"COLLAPSED_EXACT_VISIBLE_SUBTOTAL_BLOCKS", "NO_ELIGIBLE_BLOCK", "UNRESOLVED"}
        or type(value["input_axis_sha256"]) is not str
        or len(value["input_axis_sha256"]) != 64
        or type(value["block_receipts"]) is not list
        or type(value["effective_parent_relations"]) is not list
        or type(value["unresolved_reasons"]) is not list
        or any(type(reason) is not str or not reason for reason in value["unresolved_reasons"])
    ):
        raise _error("ordered subtotal-collapse result drifted")
    if (value["status"] == "UNRESOLVED") != bool(value["unresolved_reasons"]):
        raise _error("ordered subtotal-collapse status/reason contract drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("collapse_id")
    if identity != "ovsbcv1:collapse:" + canonical_json_sha256_v1(material):
        raise _error("ordered subtotal-collapse identity drifted")
    return canonical_clone_v1(value)


def validate_ordered_visible_subtotal_block_collapse_replay_v1(
    value: Any, source: Any
) -> dict[str, Any]:
    """Rebuild the collapse receipt and require typed byte-equivalence."""

    persisted = _validate_result(value)
    expected = build_ordered_visible_subtotal_block_collapse_v1(source)
    if not same_typed_json_v1(persisted, expected):
        raise _error("ordered subtotal-collapse result does not replay exactly")
    return persisted
