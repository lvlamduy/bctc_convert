from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from bctc_ai.evaluation import (
    loan_quality_numeric_row_reconciliation_v1 as reconciliation,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_ROOT = Path(__file__).resolve().parents[2]
_CONTEXT_V1 = _ROOT / "config/schemas/loan-quality-margin-context-v1.json"
_CONTEXT_V2 = _ROOT / "config/schemas/loan-quality-margin-context-140-v2.json"
_ROLES = ("STANDARD", "SPECIAL_MENTION", "SUBSTANDARD", "DOUBTFUL", "LOSS")


def _cell(
    lane: int,
    pp: str | None,
    viet: str | None = None,
    *,
    line: int | None = None,
    page: int = 1,
) -> dict[str, Any]:
    return {
        "lane_index": lane,
        "page_sequence": page,
        "ppocrv6_surface": pp,
        "source_line_index": lane if line is None else line,
        "vietocr_surface": pp if viet is None else viet,
    }


def _row(role: str, values: list[tuple[str | None, str | None]]) -> dict[str, Any]:
    return {
        "cells": [
            _cell(lane, pp, viet, line=10 * _ROLES.index(role) + lane)
            for lane, (pp, viet) in enumerate(values)
        ],
        "label_surface": role,
        "role": role,
    }


def _total(values: list[tuple[str | None, str | None]], label: str = "Tổng") -> dict[str, Any]:
    return {
        "cells": [_cell(lane, pp, viet, line=100 + lane) for lane, (pp, viet) in enumerate(values)],
        "label_surface": label,
    }


def _horizontal_input(
    *,
    lane_types: list[str] | None = None,
    rows: list[dict[str, Any]] | None = None,
    total: dict[str, Any] | None = None,
    margin_mode: str = "NOT_OBSERVED_DO_NOT_SYNTHESIZE",
    margin: dict[str, Any] | None = None,
    parent_total: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if lane_types is None:
        lane_types = ["MONEY", "MONEY"]
    if rows is None:
        raw = (["100", "90"], ["10", "9"], ["5", "4"], ["3", "2"], ["2", "1"])
        rows = [
            _row(role, [(value, value) for value in values])
            for role, values in zip(_ROLES, raw, strict=True)
        ]
    if total is None:
        total = _total([("120", "120"), ("106", "106")])
    return {
        "format_version": reconciliation.INPUT_FORMAT_VERSION,
        "lane_types": lane_types,
        "layout_mode": "HORIZONTAL_TYPED_PERIOD_LANES",
        "margin": margin,
        "margin_mode": margin_mode,
        "parent_total": parent_total,
        "rows": rows,
        "source_id": "test:loan-quality:horizontal",
        "sparse_blocks": [],
        "total": total,
    }


def test_context_v2_preserves_v1_meanings_and_closes_live_schema() -> None:
    v1 = json.loads(_CONTEXT_V1.read_text(encoding="utf-8"))
    context = reconciliation.load_loan_quality_margin_context_140_v2(_CONTEXT_V2)

    for field in (
        "authority",
        "family",
        "included_source_disclosure",
        "standalone_item",
        "state",
    ):
        assert context[field] == v1[field]
    for field, meaning in v1["normalization_policy"].items():
        assert context["normalization_policy"][field] == meaning
    assert context["explicit_excluded_footnote"] == {
        "mapping_output_authority": True,
        "parent_report_norm_id": 746,
        "population_relation": "EXCLUDED_FROM_PRINTED_FIVE_GRADE_TOTAL",
        "role": "NONADDITIVE_EXCLUDED_DISCLOSURE",
        "standalone_report_norm_id": 1944,
    }
    assert "explicit_excluded_footnote" not in v1

    @dataclass
    class Node:
        canonical_name: str
        display_order: int
        parent_id: int | None
        scope: list[str]
        statement_type: str = "TM"

    schema = {
        schema_id: Node(name, ordinal, parent, ["SEPARATE", "CONSOLIDATED"])
        for ordinal, (schema_id, (name, parent)) in enumerate(
            reconciliation._CORE_SCHEMA.items(), 100
        )
    }
    projection = reconciliation.project_loan_quality_closed_schema_v1(schema, context)

    assert projection["nodes"][-1]["report_norm_id"] == 1944
    assert projection["nodes"][-1]["effective_parent_id"] == 746
    assert projection["nodes"][-1]["live_parent_id"] is None
    excluded = projection["presentation_bindings"][2]
    assert excluded["presentation_mode"] == "EXPLICITLY_EXCLUDED_FROM_CORE_VIA_FOOTNOTE"
    assert excluded["emit_report_norm_id"] == 1944


def test_additive_two_money_lanes_select_only_the_unique_observed_conflict() -> None:
    source = _horizontal_input(
        rows=[
            _row("STANDARD", [("100", "101"), ("90", "90")]),
            _row("SPECIAL_MENTION", [("10", "10"), ("9", "9")]),
            _row("SUBSTANDARD", [("5", "5"), ("4", "4")]),
            _row("DOUBTFUL", [("3", "3"), ("2", "2")]),
            _row("LOSS", [("2", "2"), ("1", "1")]),
        ],
        total=_total([("125", "125"), ("110", "110")]),
        margin_mode="STANDALONE_AFTER_FIVE_GRADES",
        margin=_total([("5", "5"), ("4", "4")], "Cho vay giao dịch ký quỹ"),
        parent_total=_total([("125", "125"), ("110", "110")], "Cho vay khách hàng"),
    )

    result = reconciliation.build_loan_quality_numeric_row_reconciliation_v1(source)

    assert result["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    cell = result["rows"][0]["cells"][0]
    assert cell["ppocrv6_surface"] == "100"
    assert cell["vietocr_surface"] == "101"
    assert cell["selected_value"] == 100
    assert cell["selected_readers"] == ["PPOCRV6"]
    assert cell["status"] == "SELECTED_UNIQUE_OBSERVED_VALUE_BY_EXACT_EQUATION"
    assert result["margin"]["mapping_disposition"] == "EMIT_OBSERVED_1944_AS_ADDITIVE_CHILD"
    assert result["accounting_checks"][0]["status"] == (
        "EXACT_EQUATION_UNIQUELY_SELECTED_OBSERVED_CONFLICT"
    )


def test_blank_is_not_zero_and_no_equation_backsolves_it() -> None:
    rows = [
        _row("STANDARD", [("100", "100"), ("90", "90")]),
        _row("SPECIAL_MENTION", [("", ""), ("9", "9")]),
        _row("SUBSTANDARD", [("5", "5"), ("4", "4")]),
        _row("DOUBTFUL", [("3", "3"), ("2", "2")]),
        _row("LOSS", [("2", "2"), ("1", "1")]),
    ]
    source = _horizontal_input(rows=rows, total=_total([("110", "110"), ("106", "106")]))

    result = reconciliation.build_loan_quality_numeric_row_reconciliation_v1(source)

    missing = result["rows"][1]["cells"][0]
    assert missing["selected_value"] is None
    assert missing["candidate_values"] == []
    assert result["accounting_checks"][0]["status"] == "UNRESOLVED_MISSING_OBSERVED_VALUE"
    assert result["status"] == "UNRESOLVED_OBSERVED_NUMERIC_RECONCILIATION"
    assert result["authority"]["blank_or_missing_cell_imputed_as_zero"] is False


def test_interleaved_money_percent_lanes_accept_pp_only_and_vietocr_only_cells() -> None:
    values = (
        (("100", "100"), ("97,19", "97,19"), ("90", "90"), ("96,92", "96,92")),
        (("10", "10"), ("1,33", "1,33"), ("9", "9"), ("1,67", "1,67")),
        (("5", "5"), ("0,19", ",19"), ("4", "4"), ("0,18", "0,18")),
        (("bad", "3"), ("0,20", "0,20"), ("2", "2"), ("0,27", "0,27")),
        (("2", "2"), ("1,09", "1,09"), ("1", "1"), ("0,96", "0,96")),
    )
    rows = [_row(role, list(row_values)) for role, row_values in zip(_ROLES, values, strict=True)]
    source = _horizontal_input(
        lane_types=["MONEY", "PERCENT", "MONEY", "PERCENT"],
        rows=rows,
        total=_total([("120", "120"), ("100,00", "100,00"), ("106", "106"), ("100", "100")]),
        margin_mode="INCLUDED_IN_747_VIA_5746",
        margin={
            "cells": [_cell(0, "8", "8"), _cell(2, "7", "7")],
            "label_surface": "Trong đó: cho vay giao dịch ký quỹ",
        },
        parent_total=_total(
            [("120", "120"), ("100", "100"), ("106", "106"), ("100", "100")],
            "Cho vay khách hàng",
        ),
    )

    result = reconciliation.build_loan_quality_numeric_row_reconciliation_v1(source)

    assert result["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    pp_only = result["rows"][2]["cells"][1]
    assert pp_only["selected_value"] == "0.19"
    assert pp_only["selected_readers"] == ["PPOCRV6"]
    viet_only = result["rows"][3]["cells"][0]
    assert viet_only["selected_value"] == 3
    assert viet_only["selected_readers"] == ["VIETOCR"]
    assert all(
        check["status"] == "EXACT_OBSERVED_EQUATION" for check in result["accounting_checks"]
    )


def test_excluded_footnote_is_outside_grade_total_but_closes_observed_parent() -> None:
    source = _horizontal_input(
        margin_mode="EXPLICITLY_EXCLUDED_FROM_CORE_VIA_FOOTNOTE",
        margin=_total(
            [("8", "9"), ("7", "7")],
            "Không bao gồm cho vay giao dịch ký quỹ",
        ),
        parent_total=_total([("128", "128"), ("113", "113")], "Cho vay khách hàng"),
    )

    result = reconciliation.build_loan_quality_numeric_row_reconciliation_v1(source)

    assert result["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    assert result["accounting_checks"][0]["selected_sum"] == 120
    assert result["accounting_checks"][2]["term_roles"] == [
        "PRINTED_QUALITY_TOTAL",
        "MARGIN_AND_SECURITIES_ADVANCE",
    ]
    assert result["margin"]["cells"][0]["selected_value"] == 8
    assert result["margin"]["mapping_disposition"] == (
        "EMIT_OBSERVED_1944_OUTSIDE_PRINTED_FIVE_GRADE_TOTAL"
    )


def _sparse_block(block: int, multiplier: int) -> dict[str, Any]:
    target_values = [100, 10, 5, 3, 2]
    companion_values = [150, 15, 8, 4, 3]
    rows = []
    for row_index, role in enumerate(_ROLES):
        target = target_values[row_index] * multiplier
        pp = str(target)
        viet = str(target + 1) if block == 0 and row_index == 0 else pp
        cells = [
            _cell(0, pp, viet, line=block * 100 + row_index * 10, page=2),
            _cell(
                3,
                str(companion_values[row_index] * multiplier),
                str(companion_values[row_index] * multiplier),
                line=block * 100 + row_index * 10 + 3,
                page=2,
            ),
        ]
        if row_index in {0, 2}:
            cells.insert(1, _cell(1, str((row_index + 1) * multiplier), line=50 + row_index))
        rows.append({"cells": cells, "label_surface": role, "role": role})
    return {
        "block_ordinal": block,
        "column_count": 4,
        "rows": rows,
        "target_column_index": 0,
        "total": {
            "cells": [
                _cell(0, str(120 * multiplier), line=90 + block, page=2),
                _cell(3, str(180 * multiplier), line=95 + block, page=2),
            ],
            "label_surface": "Tổng",
        },
        "total_column_index": 3,
    }


def test_vib_sparse_blocks_require_target_and_companion_without_zero_filling() -> None:
    source = {
        "format_version": reconciliation.INPUT_FORMAT_VERSION,
        "lane_types": ["MONEY", "MONEY"],
        "layout_mode": "STACKED_PERIOD_BLOCKS_MULTI_ASSET_COLUMNS",
        "margin": None,
        "margin_mode": "NOT_OBSERVED_DO_NOT_SYNTHESIZE",
        "parent_total": None,
        "rows": [],
        "source_id": "test:loan-quality:vib-sparse",
        "sparse_blocks": [_sparse_block(0, 1), _sparse_block(1, 2)],
        "total": None,
    }

    result = reconciliation.build_loan_quality_numeric_row_reconciliation_v1(source)

    assert result["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    assert [cell["selected_value"] for cell in result["rows"][0]["cells"]] == [100, 200]
    assert result["sparse_blocks"][0]["rows"][1]["missing_column_indices"] == [1, 2]
    assert any(
        check["status"] == "NOT_EVALUATED_INCOMPLETE_SPARSE_SOURCE_COLUMN"
        for check in result["accounting_checks"]
    )
    assert result["sparse_blocks"][0]["rows"][0]["cells"][0]["status"] == (
        "SELECTED_UNIQUE_OBSERVED_VALUE_BY_EXACT_EQUATION"
    )
    assert result["authority"]["sparse_absent_column_imputed_as_zero"] is False


def test_missing_required_vib_target_stays_unresolved_instead_of_becoming_zero() -> None:
    blocks = [_sparse_block(0, 1), _sparse_block(1, 2)]
    blocks[0]["rows"][0]["cells"] = [
        cell for cell in blocks[0]["rows"][0]["cells"] if cell["lane_index"] != 0
    ]
    source = {
        "format_version": reconciliation.INPUT_FORMAT_VERSION,
        "lane_types": ["MONEY", "MONEY"],
        "layout_mode": "STACKED_PERIOD_BLOCKS_MULTI_ASSET_COLUMNS",
        "margin": None,
        "margin_mode": "NOT_OBSERVED_DO_NOT_SYNTHESIZE",
        "parent_total": None,
        "rows": [],
        "source_id": "test:loan-quality:vib-missing-required-target",
        "sparse_blocks": blocks,
        "total": None,
    }

    result = reconciliation.build_loan_quality_numeric_row_reconciliation_v1(source)

    cell = result["rows"][0]["cells"][0]
    assert cell["status"] == "UNRESOLVED_MISSING_SPARSE_CELL"
    assert cell["selected_value"] is None
    assert result["accounting_checks"][0]["status"] == "UNRESOLVED_MISSING_OBSERVED_VALUE"
    assert result["status"] == "UNRESOLVED_OBSERVED_NUMERIC_RECONCILIATION"


def test_two_observed_assignments_that_both_close_remain_unresolved() -> None:
    source = _horizontal_input(
        rows=[
            _row("STANDARD", [("100", "101"), ("90", "90")]),
            _row("SPECIAL_MENTION", [("10", "10"), ("9", "9")]),
            _row("SUBSTANDARD", [("5", "5"), ("4", "4")]),
            _row("DOUBTFUL", [("3", "3"), ("2", "2")]),
            _row("LOSS", [("2", "2"), ("1", "1")]),
        ],
        total=_total([("120", "121"), ("106", "106")]),
    )

    result = reconciliation.build_loan_quality_numeric_row_reconciliation_v1(source)

    assert result["accounting_checks"][0]["exact_observed_assignment_count"] == 2
    assert result["accounting_checks"][0]["status"] == (
        "UNRESOLVED_MULTIPLE_EXACT_OBSERVED_ASSIGNMENTS"
    )
    assert result["rows"][0]["cells"][0]["selected_value"] is None
    assert result["total"]["cells"][0]["selected_value"] is None
    assert result["status"] == "UNRESOLVED_OBSERVED_NUMERIC_RECONCILIATION"


def test_replay_rejects_coordinated_selected_digit_rehash() -> None:
    source = _horizontal_input()
    result = reconciliation.build_loan_quality_numeric_row_reconciliation_v1(source)
    forged = copy.deepcopy(result)
    forged["rows"][0]["cells"][0]["selected_value"] = 101
    forged["rows"][0]["cells"][0]["candidate_values"] = [
        {"readers": ["PPOCRV6", "VIETOCR"], "value": 101}
    ]
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "lqnrrv1:result:" + canonical_json_sha256_v1(material)

    with pytest.raises(
        reconciliation.LoanQualityNumericRowReconciliationV1Error,
        match="does not replay exactly",
    ):
        reconciliation.validate_loan_quality_numeric_row_reconciliation_replay_v1(forged, source)


def test_closed_contract_rejects_bool_integer_type_confusion() -> None:
    source = _horizontal_input()
    source["rows"][0]["cells"][0]["page_sequence"] = True
    with pytest.raises(
        reconciliation.LoanQualityNumericRowReconciliationV1Error,
        match="locator drifted",
    ):
        reconciliation.validate_loan_quality_numeric_row_reconciliation_input_v1(source)

    result = reconciliation.build_loan_quality_numeric_row_reconciliation_v1(_horizontal_input())
    for field, forged_value in (
        ("component_count", True),
        ("required_for_acceptance", 1),
    ):
        forged = copy.deepcopy(result)
        forged["accounting_checks"][0][field] = forged_value
        material = copy.deepcopy(forged)
        material.pop("result_id")
        forged["result_id"] = "lqnrrv1:result:" + canonical_json_sha256_v1(material)
        with pytest.raises(
            reconciliation.LoanQualityNumericRowReconciliationV1Error,
            match="accounting check fields drifted",
        ):
            reconciliation.validate_loan_quality_numeric_row_reconciliation_v1(forged)
