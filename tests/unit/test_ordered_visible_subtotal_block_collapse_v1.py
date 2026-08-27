from __future__ import annotations

from copy import deepcopy

import pytest

from bctc_ai.evaluation.ordered_visible_subtotal_block_collapse_v1 import (
    OrderedVisibleSubtotalBlockCollapseV1Error,
    build_ordered_visible_subtotal_block_collapse_v1,
    validate_ordered_visible_subtotal_block_collapse_replay_v1,
)


def _cell(value: int | None, token: str | None = None, *, state: str | None = None) -> dict:
    source_text = ("" if value is None else str(value)) if token is None else token
    resolved_state = state or (
        "BLANK" if value is None else "PRINTED_ZERO" if value == 0 else "NUMBER"
    )
    return {
        "coefficient": value,
        "source_locator": {"cell": source_text or "blank"},
        "source_text": source_text,
        "state": resolved_state,
    }


def _row(
    identity: str,
    values: tuple[int | None, int | None],
    ordinal: int,
    *,
    kind: str,
    level: int,
    source_parent: str | None = "root",
    period: str = "CURRENT",
    root: str = "asset-root",
    table: str = "movement-table",
    unit: str = "VND_MILLION",
) -> dict:
    return {
        "cells": {
            "current": _cell(values[0]),
            "prior": _cell(values[1]),
        },
        "hierarchy_level": level,
        "money_lane_ids": ["current", "prior"],
        "period_id": period,
        "root_id": root,
        "row_id": identity,
        "row_kind": kind,
        "row_ordinal": ordinal,
        "source_parent_row_id": source_parent,
        "table_id": table,
        "unit_id": unit,
    }


def _four_block_source() -> dict:
    specs = [
        ("cost", (30, 3), [(10, 1), (20, 2)]),
        ("depreciation", (5, 0), [(8, 2), (-3, -2)]),
        ("carrying", (0, 0), [(0, 0), (0, 0)]),
        ("other", (12, 9), [(7, 4), (5, 5)]),
    ]
    rows = []
    for name, subtotal, children in specs:
        rows.append(_row(name, subtotal, len(rows), kind="SUBTOTAL", level=1))
        for child_ordinal, values in enumerate(children, 1):
            rows.append(
                _row(
                    f"{name}-child-{child_ordinal}",
                    values,
                    len(rows),
                    kind="DETAIL",
                    level=2,
                    # Gemini-style flattened source parent: the effective
                    # subtotal parent has not been projected yet.
                    source_parent="root",
                )
            )
    # Preserve signed-parenthesis and typed-zero evidence explicitly.
    rows[5]["cells"]["current"] = _cell(-3, "(3)")
    rows[5]["cells"]["prior"] = _cell(-2, "(2)")
    rows[6]["cells"]["current"] = _cell(0, "0", state="PRINTED_ZERO")
    rows[6]["cells"]["prior"] = _cell(0, "-", state="DASH_ZERO")
    for index in (7, 8):
        rows[index]["cells"]["current"] = _cell(0, "-", state="DASH_ZERO")
        rows[index]["cells"]["prior"] = _cell(0, "0", state="PRINTED_ZERO")
    mappings = [
        {
            "mapping_id": f"mapping-{row['row_id']}",
            "role_id": row["row_id"],
            "row_id": row["row_id"],
        }
        for row in rows
    ]
    return {
        "equation_frontiers": [
            {
                "equation_id": "cost-equation",
                "mapping_ids": ["mapping-cost"],
                "subtotal_row_id": "cost",
            },
            {
                "equation_id": "depreciation-equation",
                "mapping_ids": [
                    "mapping-depreciation-child-1",
                    "mapping-depreciation-child-2",
                ],
                "subtotal_row_id": "depreciation",
            },
        ],
        "mappings": mappings,
        "rows": rows,
    }


def test_four_flattened_parent_blocks_collapse_by_order_indent_and_exact_sum() -> None:
    source = _four_block_source()
    before = deepcopy(source)

    result = build_ordered_visible_subtotal_block_collapse_v1(source)

    assert source == before
    assert result["status"] == "COLLAPSED_EXACT_VISIBLE_SUBTOTAL_BLOCKS"
    assert len(result["block_receipts"]) == 4
    assert len(result["effective_parent_relations"]) == 8
    by_parent = {}
    for relation in result["effective_parent_relations"]:
        by_parent.setdefault(relation["effective_parent_row_id"], []).append(
            relation["child_row_id"]
        )
    assert by_parent["cost"] == ["cost-child-1", "cost-child-2"]
    assert by_parent["depreciation"] == [
        "depreciation-child-1",
        "depreciation-child-2",
    ]
    receipts = {receipt["subtotal_row_id"]: receipt for receipt in result["block_receipts"]}
    assert receipts["cost"]["selected_frontiers"][0]["selection_mode"] == ("SUBTOTAL_FRONTIER")
    assert receipts["depreciation"]["selected_frontiers"][0]["selection_mode"] == (
        "DESCENDANT_FRONTIER"
    )
    assert receipts["depreciation"]["lane_equations"][0]["child_coefficients"] == [8, -3]
    assert receipts["carrying"]["lane_equations"][0]["signed_sum"] == 0
    assert validate_ordered_visible_subtotal_block_collapse_replay_v1(result, source) == result


def test_already_correct_source_parent_is_also_accepted() -> None:
    source = _four_block_source()
    for row in source["rows"]:
        if row["row_kind"] == "DETAIL":
            row["source_parent_row_id"] = row["row_id"].rsplit("-child-", 1)[0]

    result = build_ordered_visible_subtotal_block_collapse_v1(source)

    assert result["status"] == "COLLAPSED_EXACT_VISIBLE_SUBTOTAL_BLOCKS"
    assert len(result["block_receipts"]) == 4


def test_parent_sensitive_cost_and_depreciation_children_never_cross() -> None:
    source = _four_block_source()
    result = build_ordered_visible_subtotal_block_collapse_v1(source)
    relations = {
        relation["child_row_id"]: relation["effective_parent_row_id"]
        for relation in result["effective_parent_relations"]
    }
    assert relations["cost-child-2"] == "cost"
    assert relations["depreciation-child-1"] == "depreciation"


def test_blank_child_does_not_turn_an_exact_zero_subtotal_into_a_closure() -> None:
    source = _four_block_source()
    source["rows"][7]["cells"]["current"] = _cell(None)

    result = build_ordered_visible_subtotal_block_collapse_v1(source)

    assert result["status"] == "UNRESOLVED"
    assert "BLANK_OR_UNKNOWN_MONEY_CELL_CANNOT_CLOSE_SUBTOTAL" in result["unresolved_reasons"]
    assert result["block_receipts"] == []


def test_one_unit_signed_sum_mismatch_is_unresolved() -> None:
    source = _four_block_source()
    source["rows"][2]["cells"]["prior"] = _cell(3)
    result = build_ordered_visible_subtotal_block_collapse_v1(source)
    assert result["status"] == "UNRESOLVED"
    assert "VISIBLE_SUBTOTAL_SIGNED_SUM_MISMATCH" in result["unresolved_reasons"]


@pytest.mark.parametrize(
    "field,replacement",
    [
        ("table_id", "other-table"),
        ("root_id", "other-root"),
        ("period_id", "PRIOR"),
        ("unit_id", "VND"),
    ],
)
def test_cross_context_child_is_unresolved(field: str, replacement: str) -> None:
    source = _four_block_source()
    source["rows"][1][field] = replacement
    result = build_ordered_visible_subtotal_block_collapse_v1(source)
    assert result["status"] == "UNRESOLVED"
    assert "CROSS_TABLE_ROOT_PERIOD_OR_UNIT_CHILD_VETO" in result["unresolved_reasons"]


def test_subtotal_and_descendants_may_all_be_mapped_but_not_double_consumed() -> None:
    source = _four_block_source()
    source["equation_frontiers"][0]["mapping_ids"] = [
        "mapping-cost",
        "mapping-cost-child-1",
        "mapping-cost-child-2",
    ]

    result = build_ordered_visible_subtotal_block_collapse_v1(source)

    assert result["status"] == "UNRESOLVED"
    assert (
        "SUBTOTAL_DESCENDANT_MIXED_PARTIAL_OR_DOUBLE_CONSUMPTION_VETO"
        in result["unresolved_reasons"]
    )


def test_partial_descendant_frontier_and_mapping_reuse_are_unresolved() -> None:
    partial = _four_block_source()
    partial["equation_frontiers"][0]["mapping_ids"] = ["mapping-cost-child-1"]
    assert build_ordered_visible_subtotal_block_collapse_v1(partial)["status"] == "UNRESOLVED"

    reused = _four_block_source()
    reused["equation_frontiers"].append(
        {
            "equation_id": "cost-equation-2",
            "mapping_ids": ["mapping-cost"],
            "subtotal_row_id": "cost",
        }
    )
    result = build_ordered_visible_subtotal_block_collapse_v1(reused)
    assert result["status"] == "UNRESOLVED"
    assert "MAPPING_REUSED_ACROSS_SELECTED_FRONTIERS_VETO" in result["unresolved_reasons"]


def test_peer_reset_and_flat_indent_do_not_create_an_effective_parent() -> None:
    source = _four_block_source()
    source["rows"] = source["rows"][:3]
    source["rows"][1]["row_kind"] = "PEER"
    source["rows"][2]["hierarchy_level"] = 1
    for ordinal, row in enumerate(source["rows"]):
        row["row_ordinal"] = ordinal
    source["mappings"] = [
        mapping
        for mapping in source["mappings"]
        if mapping["row_id"] in {row["row_id"] for row in source["rows"]}
    ]
    source["equation_frontiers"] = []

    result = build_ordered_visible_subtotal_block_collapse_v1(source)

    assert result["status"] == "NO_ELIGIBLE_BLOCK"
    assert result["effective_parent_relations"] == []


def test_deeper_indented_child_with_ambiguous_source_parent_is_unresolved() -> None:
    source = _four_block_source()
    source["rows"][1]["source_parent_row_id"] = "unrelated-parent"

    result = build_ordered_visible_subtotal_block_collapse_v1(source)

    assert result["status"] == "UNRESOLVED"
    assert "AMBIGUOUS_VISIBLE_CHILD_PARENT_MARKER_VETO" in result["unresolved_reasons"]


def test_noncontiguous_exact_child_after_peer_is_unresolved() -> None:
    source = _four_block_source()
    source["rows"][1]["source_parent_row_id"] = "cost"
    source["rows"][2]["row_kind"] = "PEER"
    source["rows"][2]["source_parent_row_id"] = "root"
    source["rows"][4]["source_parent_row_id"] = "cost"

    result = build_ordered_visible_subtotal_block_collapse_v1(source)

    assert result["status"] == "UNRESOLVED"
    assert "NONCONTIGUOUS_CHILD_AFTER_PEER_OR_RESET_VETO" in result["unresolved_reasons"]


def test_tampered_block_receipt_does_not_replay() -> None:
    source = _four_block_source()
    result = build_ordered_visible_subtotal_block_collapse_v1(source)
    result["block_receipts"][0]["child_row_ids"].reverse()
    with pytest.raises(OrderedVisibleSubtotalBlockCollapseV1Error):
        validate_ordered_visible_subtotal_block_collapse_replay_v1(result, source)
