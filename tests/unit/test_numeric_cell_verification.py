from __future__ import annotations

from copy import deepcopy

import pytest

from bctc_ai.evaluation.numeric_cell_verification import (
    NumericCellVerificationError,
    verify_numeric_cell_proposals,
)


def _cell(
    cell_id: str,
    observation: str,
    raw: str,
    value: str | None,
    sign: str | None,
    *,
    visual=None,
):
    return {
        "cell_id": cell_id,
        "page": 3,
        "row_ordinal": int(cell_id.split("-")[3]),
        "axis_ordinal": 0,
        "axis_id": "value-1",
        "crop_path": f"crops/{cell_id}.png",
        "crop_sha256": f"sha-{cell_id}",
        "primary_observation": observation,
        "primary_raw_text": raw,
        "primary_normalized_text": raw,
        "primary_value": value,
        "primary_sign_evidence": sign,
        "visual_punctuation_evidence": visual,
    }


def _prediction(cell, raw, score=0.9, status="NUMERIC_CHARACTERS_ONLY_PROPOSAL"):
    return {
        "cell_id": cell["cell_id"],
        "crop_path": f"/tmp/{cell['cell_id']}.png",
        "crop_sha256": cell["crop_sha256"],
        "proposal_status": status,
        "raw_prediction": raw,
        "reader_score": score,
    }


def _registry(cells):
    return {
        "format_version": 1,
        "policy": "FIXED_GRID_NUMERIC_CELL_CROPS_V1",
        "geometry_authority": "E0029_PP_OCRV6_FIXED_GRID",
        "metrics": {"cell_count": len(cells)},
        "cells": cells,
    }


def test_exact_value_sign_and_dash_agreement_only():
    positive = _cell("page-0003-row-001-axis-1", "VALUE", "1.234", "1234", None)
    negative = _cell(
        "page-0003-row-002-axis-1", "VALUE", "(69.380)", "-69380", "parentheses"
    )
    dash = _cell(
        "page-0003-row-003-axis-1",
        "DASH",
        "-",
        None,
        "dash",
        visual={"observation": "DASH", "component_box": [1, 2, 3, 4]},
    )
    result = verify_numeric_cell_proposals(
        _registry([positive, negative, dash]),
        [
            _prediction(positive, "1.234"),
            _prediction(negative, "(69.380)"),
            _prediction(dash, "-"),
        ],
    )

    assert [cell["verification_status"] for cell in result["cells"]] == [
        "VERIFIED_OBSERVED_VALUE",
        "VERIFIED_OBSERVED_VALUE",
        "VERIFIED_OBSERVED_DASH",
    ]
    assert [cell["normalized_numeric_value"] for cell in result["cells"]] == [
        "1234",
        "-69380",
        "0",
    ]
    assert [cell["final_value_status"] for cell in result["cells"]] == [
        "OBSERVED_VALUE",
        "OBSERVED_VALUE",
        "OBSERVED_ZERO",
    ]
    assert result["metrics"]["observed_exact_agreement_rate"] == 1.0


@pytest.mark.parametrize(
    ("primary_raw", "primary_value", "sign", "reader_raw"),
    [
        ("(69.380)", "-69380", "parentheses", "69.380)"),
        ("41.408.552", "41408552", None, "41,408.552"),
        ("2.320", "2320", None, "2.20"),
        ("(69.380)", "-69380", "parentheses", "69.380"),
    ],
)
def test_numeric_or_sign_disagreement_abstains(
    primary_raw, primary_value, sign, reader_raw
):
    cell = _cell(
        "page-0003-row-001-axis-1", "VALUE", primary_raw, primary_value, sign
    )
    result = verify_numeric_cell_proposals(
        _registry([cell]), [_prediction(cell, reader_raw)]
    )["cells"][0]

    assert result["verification_status"] == "UNRESOLVED_READER_DISAGREEMENT"
    assert result["selected_raw_value"] is None
    assert result["normalized_numeric_value"] is None
    assert result["final_value_status"] is None
    assert result["primary"]["raw_text"] == primary_raw
    assert result["challenger"]["raw_text"] == reader_raw


def test_blank_is_never_promoted_by_reader():
    blank = _cell("page-0003-row-001-axis-1", "BLANK", "", None, None)
    result = verify_numeric_cell_proposals(
        _registry([blank]), [_prediction(blank, "123")]
    )
    cell = result["cells"][0]

    assert cell["verification_status"] == "UNRESOLVED_BLANK_PENDING_ROW_SEMANTICS"
    assert cell["normalized_numeric_value"] is None
    assert cell["final_value_status"] is None
    assert result["metrics"]["blank_to_zero_or_value_promotion_count"] == 0


def test_dash_requires_reader_and_independent_pixel_evidence():
    dash = _cell("page-0003-row-001-axis-1", "DASH", "-", None, "dash")
    result = verify_numeric_cell_proposals(
        _registry([dash]), [_prediction(dash, "-")]
    )["cells"][0]

    assert result["verification_status"] == "UNRESOLVED_READER_DISAGREEMENT"
    assert result["normalized_numeric_value"] is None


def test_reader_score_does_not_change_decision():
    cell = _cell("page-0003-row-001-axis-1", "VALUE", "1.234", "1234", None)
    low = verify_numeric_cell_proposals(
        _registry([cell]), [_prediction(cell, "1.234", score=0.01)]
    )["cells"][0]
    high = verify_numeric_cell_proposals(
        _registry([cell]), [_prediction(cell, "1.234", score=0.99)]
    )["cells"][0]

    assert low["verification_status"] == high["verification_status"]
    assert low["normalized_numeric_value"] == high["normalized_numeric_value"]


def test_crop_identity_and_denominator_are_immutable():
    cell = _cell("page-0003-row-001-axis-1", "VALUE", "1.234", "1234", None)
    prediction = _prediction(cell, "1.234")
    bad_hash = deepcopy(prediction)
    bad_hash["crop_sha256"] = "wrong"

    with pytest.raises(NumericCellVerificationError, match="crop identity drifted"):
        verify_numeric_cell_proposals(_registry([cell]), [bad_hash])
    with pytest.raises(NumericCellVerificationError, match="denominator"):
        verify_numeric_cell_proposals(_registry([cell]), [])
