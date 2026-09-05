from __future__ import annotations

import pytest

from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    SourceObservationMappingContractError,
    audit_source_observation_mapping_contract_v1,
    validate_source_observation_mapping_contract_v1,
)


def _mapping(values: list[dict]) -> dict:
    return {"report_norm_id": 101, "role": "DETAIL", "values": values}


def test_contract_accepts_visible_dash_and_typed_partial_blank() -> None:
    artifact = {
        "trials": [
            {
                "mappings": [
                    _mapping(
                        [
                            {"coefficient": 0, "source_text": "-", "state": "DASH_ZERO"},
                            {
                                "coefficient": None,
                                "source_text": None,
                                "state": "BLANK_SOURCE_CELL",
                            },
                        ]
                    )
                ]
            }
        ]
    }

    audit = validate_source_observation_mapping_contract_v1(artifact)

    assert audit["status"] == "PASS"
    assert audit["partial_mapping_count"] == 1
    assert audit["source_blank_cell_count"] == 1


def test_contract_accepts_explicit_nonblank_derivation() -> None:
    audit = validate_source_observation_mapping_contract_v1(
        _mapping(
            [
                {
                    "coefficient": 12,
                    "source_text": None,
                    "state": "DERIVED_EXACT_SUM_OF_VISIBLE_CHILDREN",
                }
            ]
        )
    )

    assert audit["derived_cell_count"] == 1


def test_contract_accepts_composed_source_value_with_bound_row_provenance() -> None:
    mapping = _mapping(
        [
            {
                "coefficient": 12,
                "source_text": None,
                "state": "SOURCE_VISIBLE_DIRECT_PARTIAL_OPTIONAL_CUSTOMER_VIEW",
            }
        ]
    )
    mapping["source_refs"] = [
        {
            "locator": {
                "page_json_version_id": "gfpstorev1:json:" + "1" * 64,
                "table_id": "t1",
            },
            "row_id": "r1",
        }
    ]

    audit = validate_source_observation_mapping_contract_v1(mapping)

    assert audit["derived_cell_count"] == 1


def test_contract_audits_one_cell_mapping_and_composite_rollforward_role() -> None:
    artifact = {
        "report_norm_id": 785,
        "lane_role": "GENERAL",
        "movement_role": "OPENING",
        "cell": {"coefficient": 7, "source_text": "7", "state": "NUMBER"},
    }

    audit = validate_source_observation_mapping_contract_v1(artifact)

    assert audit["mapping_count"] == 1
    assert audit["cell_count"] == 1


def test_contract_accepts_source_ref_bound_cell_projection() -> None:
    artifact = {
        "report_norm_id": 870,
        "role": "COST_OPENING",
        "cell": {"coefficient": 7, "state": "NUMBER"},
        "source_refs": [
            {
                "cell": {
                    "coefficient": 7,
                    "source_text": "7",
                    "state": "NUMBER",
                    "source_locator": {"column_id": "c1"},
                },
                "row_id": "r1",
            }
        ],
    }

    audit = validate_source_observation_mapping_contract_v1(artifact)

    assert audit["mapping_count"] == 1
    assert audit["derived_cell_count"] == 1


@pytest.mark.parametrize(
    "state",
    [
        "BLANK_ZERO_IF_EQUATION_EXACT",
        "INFERRED_BLANK_ZERO_EQUATION_EXACT",
        "INFERRED_BLANK_ZERO_CROSS_PERIOD_ZERO_AND_BOUNDED_MILLION_VND_ROUNDING",
    ],
)
def test_contract_rejects_every_blank_to_zero_state(state: str) -> None:
    value = _mapping([{"coefficient": 0, "source_text": None, "state": state}])

    with pytest.raises(SourceObservationMappingContractError, match="SOURCE_BLANK"):
        validate_source_observation_mapping_contract_v1(value)


def test_contract_rejects_untyped_numeric_without_source() -> None:
    audit = audit_source_observation_mapping_contract_v1(
        _mapping([{"coefficient": 0, "source_text": None, "state": "SOURCE_VALUE"}])
    )

    assert audit["status"] == "FAILED"
    assert audit["violations"][0]["reason"] == (
        "NUMERIC_MAPPING_HAS_NO_SOURCE_OR_EXACT_DERIVATION"
    )


def test_contract_rejects_mapping_whose_every_lane_is_unobserved() -> None:
    value = _mapping(
        [
            {"coefficient": None, "source_text": None, "state": "BLANK_SOURCE_CELL"},
            {
                "coefficient": None,
                "source_text": None,
                "state": "ABSENT_SOURCE_AXIS_ROLE",
            },
        ]
    )

    with pytest.raises(SourceObservationMappingContractError, match="ALL_LANES_UNOBSERVED"):
        validate_source_observation_mapping_contract_v1(value)


def test_contract_rejects_null_cell_with_derived_numeric_state() -> None:
    value = _mapping(
        [
            {
                "coefficient": None,
                "source_text": None,
                "state": "DERIVED_EXACT_SUM_OF_VISIBLE_CHILDREN",
            }
        ]
    )

    with pytest.raises(SourceObservationMappingContractError, match="NULL_MAPPING_CELL"):
        validate_source_observation_mapping_contract_v1(value)
