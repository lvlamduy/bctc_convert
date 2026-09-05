from __future__ import annotations

import pytest

from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    _exact_equation,
    _sum_records,
)
from bctc_ai.evaluation.source_observation_lane_math_v1 import (
    SourceObservationLaneMathError,
    additive_source_lane_receipts_v1,
    observed_source_coefficient_v1,
    partial_source_mapping_values_v1,
)


def _cell(value: int | None, state: str, source: str | None = None) -> dict:
    return {"coefficient": value, "source_text": source, "state": state}


def test_legacy_blank_zero_is_unobserved_not_numeric() -> None:
    assert (
        observed_source_coefficient_v1(
            _cell(0, "INFERRED_BLANK_ZERO_IF_EQUATION_EXACT")
        )
        is None
    )


def test_lane_math_proves_only_complete_observed_lane() -> None:
    receipts = additive_source_lane_receipts_v1(
        result_cells=[
            _cell(12, "RAW_SIGNED_INTEGER", "12"),
            _cell(9, "RAW_SIGNED_INTEGER", "9"),
        ],
        component_cell_vectors=[
            [
                _cell(7, "RAW_SIGNED_INTEGER", "7"),
                _cell(0, "BLANK_ZERO_IF_EQUATION_EXACT"),
            ],
            [
                _cell(5, "RAW_SIGNED_INTEGER", "5"),
                _cell(9, "RAW_SIGNED_INTEGER", "9"),
            ],
        ],
    )

    assert [receipt["status"] for receipt in receipts] == [
        "EXACT_OBSERVED_SOURCE_LANE",
        "COMPONENT_SOURCE_LANE_UNOBSERVED",
    ]
    assert receipts[1]["component_sum"] is None
    assert receipts[1]["residual"] is None


def test_unobserved_result_lane_cannot_be_backsolved() -> None:
    receipts = additive_source_lane_receipts_v1(
        result_cells=[_cell(None, "BLANK_SOURCE_CELL")],
        component_cell_vectors=[[_cell(3, "RAW_SIGNED_INTEGER", "3")]],
    )

    assert receipts[0]["status"] == "RESULT_SOURCE_LANE_UNOBSERVED"
    assert receipts[0]["result_coefficient"] is None


def test_bounded_rounding_applies_only_to_complete_lane() -> None:
    receipts = additive_source_lane_receipts_v1(
        result_cells=[_cell(10, "RAW_SIGNED_INTEGER", "10")],
        component_cell_vectors=[[_cell(11, "RAW_SIGNED_INTEGER", "11")]],
        maximum_absolute_residual=1,
    )

    assert receipts[0]["status"] == "BOUNDED_DISPLAY_ROUNDING_SOURCE_LANE"


def test_partial_mapping_keeps_visible_lane_and_nulls_blank_lane() -> None:
    values = partial_source_mapping_values_v1(
        [
            _cell(4, "RAW_SIGNED_INTEGER", "4"),
            _cell(0, "BLANK_ZERO_IF_EQUATION_EXACT"),
        ]
    )

    assert values == [
        _cell(4, "RAW_SIGNED_INTEGER", "4"),
        _cell(None, "BLANK_SOURCE_CELL"),
    ]


def test_all_blank_role_is_omitted() -> None:
    assert partial_source_mapping_values_v1(
        [_cell(None, "BLANK_SOURCE_CELL"), _cell(0, "BLANK_ZERO_IF_EQUATION_EXACT")]
    ) is None


def test_blank_state_cannot_hide_nonzero_or_source_text() -> None:
    with pytest.raises(SourceObservationLaneMathError, match="nonzero"):
        observed_source_coefficient_v1(_cell(1, "BLANK_SOURCE_CELL"))
    with pytest.raises(SourceObservationLaneMathError, match="source text"):
        observed_source_coefficient_v1(_cell(None, "BLANK_SOURCE_CELL", "-"))


def test_multitable_sum_and_equation_mask_legacy_blank_zero_lane() -> None:
    lane_keys = [["CURRENT_PERIOD"], ["COMPARATIVE_PERIOD"]]
    left = {
        "cells": [
            _cell(7, "RAW_SIGNED_INTEGER", "7"),
            _cell(0, "BLANK_ZERO_IF_EQUATION_EXACT"),
        ],
        "lane_keys": lane_keys,
        "role": "LEFT",
        "source_refs": [],
    }
    right = {
        "cells": [
            _cell(5, "RAW_SIGNED_INTEGER", "5"),
            _cell(9, "RAW_SIGNED_INTEGER", "9"),
        ],
        "lane_keys": lane_keys,
        "role": "RIGHT",
        "source_refs": [],
    }
    result = {
        "cells": [
            _cell(12, "RAW_SIGNED_INTEGER", "12"),
            _cell(9, "RAW_SIGNED_INTEGER", "9"),
        ],
        "lane_keys": lane_keys,
        "role": "RESULT",
        "source_refs": [],
    }

    assert _sum_records([left, right]) == [12, None]
    assert _exact_equation(kind="TEST", components=[left, right], result=result) is None
