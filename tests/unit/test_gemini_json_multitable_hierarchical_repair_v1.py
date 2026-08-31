from copy import deepcopy

import pytest

from bctc_ai.evaluation.gemini_json_rollforward_table_repair_v1 import (
    GeminiJsonRollforwardTableRepairV1Error,
    _multitable_hierarchical_zero_observation_equations_v1,
    _multitable_hierarchical_zero_observation_target_ids_v1,
    build_rollforward_table_repair_prompt_v1,
)


def _table() -> dict:
    return {
        "columns": [
            {"header_path_exact": ["Số cuối kỳ"], "value_kind": "MONEY"},
            {"header_path_exact": ["Số đầu kỳ"], "value_kind": "MONEY"},
        ],
        "rows": [
            {"values_exact": ["10.342.310", "2.710.113"]},
            {"values_exact": [None, None]},
            {"values_exact": ["892.840", None]},
            {"values_exact": [None, "-"]},
            {"values_exact": ["26.367.799", "37.088.405"]},
            {"values_exact": [None, None]},
            {"values_exact": ["-", None]},
            {"values_exact": ["-", None]},
            {"values_exact": ["36.710.109", "39.798.518"]},
        ],
    }


def _region() -> dict:
    return {
        "page_json_version_id": "gfpstorev1:json:" + "a" * 64,
        "section_id": "s1",
        "table_id": "t1",
    }


def _source_ref(row_id: str) -> dict:
    return {
        "locator": _region(),
        "money_column_ordinals": [1, 2],
        "row_id": row_id,
    }


def _candidate() -> dict:
    return {
        "closure_receipt": {
            "equations": [
                {
                    "component_source_refs": [[_source_ref("r1")], [_source_ref("r5")]],
                    "equation_kind": (
                        "EXACT_VISIBLE_TOP_LEVEL_DIRECT_FRONTIER_EQUAL_PRINTED_TOTAL"
                    ),
                    "result_source_refs": [_source_ref("r9")],
                    "status": "EXACT",
                }
            ]
        }
    }


def test_multitable_zero_observation_targets_only_malformed_and_conditional_blanks() -> None:
    table = _table()
    assert _multitable_hierarchical_zero_observation_target_ids_v1(
        table=table,
        table_receipt={
            "parse_reasons": [],
            "unproven_conditional_zero_rows": [3, 4],
        },
    ) == ["r3:c2", "r4:c1"]

    table["rows"][2]["values_exact"] = ["-单-", None]
    assert _multitable_hierarchical_zero_observation_target_ids_v1(
        table=table,
        table_receipt={
            "parse_reasons": ["MONEY_CELL_NOT_EXACT_INTEGER:r3"],
            "unproven_conditional_zero_rows": [],
        },
    ) == ["r3:c1"]


def test_multitable_zero_observation_rejects_nonlocal_failure_and_covers_each_target() -> None:
    with pytest.raises(
        GeminiJsonRollforwardTableRepairV1Error,
        match="cannot repair this parse failure",
    ):
        _multitable_hierarchical_zero_observation_target_ids_v1(
            table=_table(),
            table_receipt={
                "parse_reasons": ["PERIOD_AXIS_AMBIGUOUS"],
                "unproven_conditional_zero_rows": [],
            },
        )

    equations = _multitable_hierarchical_zero_observation_equations_v1(
        candidate=_candidate(),
        region=_region(),
        target_ids=["r3:c2", "r4:c1"],
    )
    assert {item["result_cell_id"] for item in equations} == {"r9:c1", "r9:c2"}
    assert {
        term["cell_id"]
        for equation in equations
        for term in equation["terms"]
        if term["cell_id"] in {"r3:c2", "r4:c1"}
    } == {"r3:c2", "r4:c1"}

    foreign = deepcopy(_candidate())
    foreign["closure_receipt"]["equations"][0]["result_source_refs"][0]["locator"]["table_id"] = (
        "t2"
    )
    with pytest.raises(
        GeminiJsonRollforwardTableRepairV1Error,
        match="one exact local printed total",
    ):
        _multitable_hierarchical_zero_observation_equations_v1(
            candidate=foreign,
            region=_region(),
            target_ids=["r3:c2"],
        )


def test_multitable_repair_uses_the_shared_minimal_observation_prompt() -> None:
    prompt = build_rollforward_table_repair_prompt_v1(
        base_page_json_version_id="gfpstorev1:json:" + "b" * 64,
        target={
            "column_headers_exact": [["Số cuối kỳ"], ["Số đầu kỳ"]],
            "column_value_kinds": ["MONEY", "MONEY"],
            "row_labels_exact": ["- Vay chiết khấu, tái chiết khấu"],
            "table_title_exact": "Vay các TCTD khác",
            "target_cells": [
                {
                    "after_policy": "DASH_ZERO",
                    "cell_id": "r3:c2",
                    "change_policy": "MUST_CHANGE",
                    "column_header_exact": ["Số đầu kỳ"],
                    "evidence_kind": "UNRESOLVED_FRONTIER",
                    "row_label_exact": "- Vay chiết khấu, tái chiết khấu",
                }
            ],
            "target_id": "s1:t1",
            "unit_exact": "Triệu VND",
        },
    )
    assert "r3:c2" in prompt
    assert "DASH_ZERO" not in prompt
    assert "MUST_CHANGE" not in prompt
    assert "equation" not in prompt.lower()
