from __future__ import annotations

from decimal import Decimal

import pytest

from bctc_ai.core.contracts import ObservationKind, ValueStatus
from bctc_ai.values.normalization import normalize_financial_cell


def test_visible_dash_preserves_raw_and_normalizes_to_observed_zero():
    result = normalize_financial_cell(
        "–",
        row_visible=True,
        cell_geometry_verified=True,
        table_structure_verified=True,
    )
    assert result.raw_value == "–"
    assert result.normalized_numeric_value == Decimal(0)
    assert result.normalized_value == "0"
    assert result.observation is ObservationKind.DASH
    assert result.value_status is ValueStatus.OBSERVED_ZERO


def test_verified_empty_numeric_cell_is_zero_but_unverified_blank_is_ambiguous():
    verified = normalize_financial_cell(
        "",
        row_visible=True,
        cell_geometry_verified=True,
        table_structure_verified=True,
    )
    assert verified.observation is ObservationKind.BLANK
    assert verified.normalized_numeric_value == Decimal(0)
    assert verified.value_status is ValueStatus.OBSERVED_ZERO

    unverified = normalize_financial_cell(
        "",
        row_visible=True,
        cell_geometry_verified=False,
        table_structure_verified=True,
    )
    assert unverified.normalized_numeric_value is None
    assert unverified.value_status is ValueStatus.AMBIGUOUS_MAPPING


def test_parentheses_preserve_raw_and_normalize_negative_amount():
    result = normalize_financial_cell(
        "(3.801.708)",
        row_visible=True,
        cell_geometry_verified=True,
        table_structure_verified=True,
    )
    assert result.raw_value == "(3.801.708)"
    assert result.normalized_numeric_value == Decimal("-3801708")
    assert result.observation is ObservationKind.VALUE
    assert result.value_status is ValueStatus.OBSERVED_VALUE


def test_absent_row_never_becomes_zero():
    result = normalize_financial_cell(
        None,
        row_visible=False,
        cell_geometry_verified=False,
        table_structure_verified=False,
    )
    assert result.normalized_numeric_value is None
    assert result.observation is None
    assert result.value_status is ValueStatus.NOT_OBSERVED
    with pytest.raises(ValueError, match="absent row"):
        normalize_financial_cell(
            "-",
            row_visible=False,
            cell_geometry_verified=False,
            table_structure_verified=False,
        )


def test_scope_and_reference_are_distinct_from_mapping_failure():
    outside = normalize_financial_cell(
        "115.147.331",
        row_visible=True,
        cell_geometry_verified=True,
        table_structure_verified=True,
        target_template_in_scope=False,
    )
    assert outside.normalized_numeric_value == Decimal("115147331")
    assert outside.value_status is ValueStatus.OUT_OF_SCOPE_FOR_TARGET_TEMPLATE

    no_reference = normalize_financial_cell(
        "34.339",
        row_visible=True,
        cell_geometry_verified=True,
        table_structure_verified=True,
        reference_available=False,
    )
    assert no_reference.normalized_numeric_value == Decimal("34339")
    assert no_reference.value_status is ValueStatus.REFERENCE_NOT_YET_BUILT
