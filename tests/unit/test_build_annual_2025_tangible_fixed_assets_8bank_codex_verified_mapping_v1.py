from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT
    / "scripts/experiments/build_annual_2025_tangible_fixed_assets_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_tangible_fixed_assets_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def live() -> tuple[object, tuple[object, ...], dict[str, object]]:
    base = builder._base()
    inputs = base._live_inputs()
    result = builder._validate_expected_ids(
        base.build_tangible_fixed_assets_8bank_codex_verified_mapping_v1(*inputs)
    )
    return base, inputs, result


def test_all_eight_annual_documents_are_verified(
    live: tuple[object, tuple[object, ...], dict[str, object]],
) -> None:
    _, _, result = live

    assert result["metrics"] == {
        "accounting_equation_count": 32,
        "document_count": 8,
        "mapping_verified_count": 105,
        "rotated_original_source_numeric_disagreement_count": 30,
        "rotated_ppocrv6_verified_value_count": 36,
        "unresolved_document_count": 0,
        "verified_present_document_count": 8,
    }
    assert [trial["document_provenance"] for trial in result["trials"]] == list(
        builder.EXPECTED_DOCUMENT_ORDER
    )
    assert [trial["page_sequence"] for trial in result["trials"]] == [
        55,
        58,
        53,
        41,
        48,
        48,
        47,
        42,
    ]
    assert all(
        trial["source_period_status"] == "VERIFIED_ANNUAL_2025_CURRENT_AND_2024_OPENING_PERIODS"
        for trial in result["trials"]
    )


def test_all_rollforwards_and_carrying_equations_close_exactly(
    live: tuple[object, tuple[object, ...], dict[str, object]],
) -> None:
    _, _, result = live
    equations = [equation for trial in result["trials"] for equation in trial["equations"]]

    assert len(equations) == 32
    assert all(equation["status"] == "CORROBORATED_EXACT" for equation in equations)
    assert all(equation["computed_total"] == equation["visible_total"] for equation in equations)


def test_vib_dropped_digit_is_recovered_only_by_rotated_ppocrv6(
    live: tuple[object, tuple[object, ...], dict[str, object]],
) -> None:
    _, _, result = live
    vib = result["trials"][7]
    purchase = next(mapping for mapping in vib["mappings"] if mapping["report_norm_id"] == 871)
    value = purchase["value"]

    assert value["fresh_vietocr_proposal"] == "164.02"
    assert value["rotated_ppocrv6_challenger"] == "164.021"
    assert value["normalized_value"] == 164_021
    assert value["source_numeric_challenger_status"] == (
        "ORIGINAL_ROTATED_SOURCE_OCR_DISAGREED_RESCUED_BY_ROTATED_PPOCRV6"
    )


def test_schema_binding_ignores_unrelated_global_order_insertions(
    live: tuple[object, tuple[object, ...], dict[str, object]],
) -> None:
    base, _, _ = live
    expected_name, parent_id = builder._SCHEMA_EXPECTED[871]
    shifted = SimpleNamespace(
        canonical_name=expected_name,
        display_order=9999,
        hierarchy_level=4,
        parent_id=parent_id,
        schema_id=871,
        statement_type="TM",
    )

    binding = base._schema_binding(shifted, 871)

    assert binding["display_order"] == builder._SCHEMA_DISPLAY_ORDER_SNAPSHOT[871]
    assert binding["report_norm_id"] == 871
    assert binding["schema_parent_report_norm_id"] == 5991


def test_exact_replay_rejects_coordinated_mapping_rehash(
    live: tuple[object, tuple[object, ...], dict[str, object]],
) -> None:
    base, inputs, result = live
    forged = copy.deepcopy(result)
    forged["trials"][0]["mappings"][0]["report_norm_id"] = 999999
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + base.canonical_json_sha256_v1(material)

    with pytest.raises(
        base.TangibleFixedAssets8BankCodexVerifiedMappingV1Error,
        match="does not replay exactly",
    ):
        base.validate_tangible_fixed_assets_8bank_codex_verified_mapping_replay_v1(forged, *inputs)
