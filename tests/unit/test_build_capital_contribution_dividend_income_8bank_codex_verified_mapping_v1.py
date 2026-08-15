from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT
    / "scripts/experiments/build_capital_contribution_dividend_income_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_capital_contribution_dividend_income_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def live_inputs() -> dict[str, object]:
    return builder._live_inputs()


@pytest.fixture(scope="module")
def persisted_result() -> dict[str, object]:
    return json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())


def test_live_result_replays_all_variants_and_equations(
    live_inputs: dict[str, object], persisted_result: dict[str, object]
) -> None:
    result = builder.validate_capital_contribution_dividend_income_8bank_codex_verified_mapping_replay_v1(
        persisted_result, **live_inputs
    )
    assert result["metrics"] == {
        "accounting_equation_verified_count": 16,
        "authenticated_dash_zero_count": 5,
        "detailed_note_not_present_document_count": 1,
        "document_count": 8,
        "document_unique_region_count": 7,
        "fresh_vietocr_numeric_disagreement_count": 2,
        "mapping_verified_count": 27,
        "open_source_row_count": 0,
        "q1_source_period_caveat_document_count": 1,
        "verified_value_cell_count": 54,
    }
    assert [trial["status"] for trial in result["trials"]] == [
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT",
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX",
        "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT",
    ]


def test_vpb_dash_ocr_errors_are_source_vetoed_and_preserved_as_zero(
    persisted_result: dict[str, object],
) -> None:
    vpb = next(
        trial for trial in persisted_result["trials"] if trial["document_provenance"] == "VPB"
    )
    disagreements = [
        value
        for mapping in vpb["verified_mappings"]
        for value in mapping["values"]
        if value["fresh_vietocr_numeric_status"] == "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
    ]
    assert len(disagreements) == 2
    assert all(value["fresh_vietocr_numeric_proposal"] == "1" for value in disagreements)
    assert all(value["source_numeric_challenger"] == "-" for value in disagreements)
    assert all(value["normalized_value"] == 0 for value in disagreements)


def test_public_replay_rejects_coordinated_equation_tamper(
    live_inputs: dict[str, object], persisted_result: dict[str, object]
) -> None:
    forged = copy.deepcopy(persisted_result)
    acb = forged["trials"][0]
    acb["verified_accounting_equations"][0]["computed_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0087:result:" + builder.canonical_json_sha256_v1(material)
    with pytest.raises(
        builder.CapitalContributionDividendIncome8BankCodexVerifiedMappingV1Error,
        match="replay exactly",
    ):
        builder.validate_capital_contribution_dividend_income_8bank_codex_verified_mapping_replay_v1(
            forged, **live_inputs
        )


def test_raw_result_has_no_standalone_authority(
    persisted_result: dict[str, object],
) -> None:
    assert persisted_result["authority"]["persisted_result_self_authenticating"] is False
    assert persisted_result["authority"]["public_exact_replay_required"] is True
