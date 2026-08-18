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
    / "scripts/experiments/build_annual_2025_credit_risk_provision_expense_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_credit_risk_provision_expense_8bank_codex_verified_mapping_v1",
    _PATH,
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def result() -> dict[str, object]:
    built = builder.build_live_annual_2025_credit_risk_provision_expense_8bank_codex_verified_mapping_v1()
    persisted = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())
    assert builder.same_typed_json_v1(built, persisted)
    return built


def test_exact_annual_denominator_unique_pages_and_bounded_absences(
    result: dict[str, object],
) -> None:
    assert result["metrics"] == builder._EXPECTED_METRICS
    assert [trial["document_provenance"] for trial in result["trials"]] == list(
        builder.EXPECTED_DOCUMENT_ORDER
    )
    assert [trial["page_span"] for trial in result["trials"]] == list(
        builder._EXPECTED_PAGES.values()
    )
    assert [len(trial["verified_mappings"]) for trial in result["trials"]] == list(
        builder._EXPECTED_MAPPING_COUNTS.values()
    )
    absent = [
        trial["document_provenance"]
        for trial in result["trials"]
        if trial["status"] == "CONFIRMED_DETAILED_NOTE_NOT_PRESENT_IN_BOUND_REPORT"
    ]
    assert absent == ["HDB", "CTG", "BID"]
    assert all(
        trial["whole_document_uniqueness"]
        == (
            {"complete_region_count": 0, "status": "NOT_UNIQUE_FULL_MATCH"}
            if trial["document_provenance"] in absent
            else {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
        )
        for trial in result["trials"]
    )


def test_controlled_catchall_aggregation_is_exact_and_not_double_counted(
    result: dict[str, object],
) -> None:
    expected = {
        "VPB": {
            "components": ["MARGIN_LOAN", "OTHER_RISK_ASSET"],
            "values": {"CURRENT_PERIOD": 77852, "COMPARATIVE_PERIOD": 69001},
        },
        "VCB": {
            "components": [
                "UNLISTED_CORPORATE_BOND_GENERAL",
                "UNLISTED_CORPORATE_BOND_SPECIFIC",
            ],
            "values": {"CURRENT_PERIOD": 3115523, "COMPARATIVE_PERIOD": 133932},
        },
    }
    for code, specification in expected.items():
        trial = next(item for item in result["trials"] if item["document_provenance"] == code)
        mapping = next(
            item for item in trial["verified_mappings"] if item["role"] == "OTHER_RISK_CATCHALL"
        )
        assert mapping["schema_binding"]["report_norm_id"] == 1228
        assert [item["role"] for item in mapping["source_components"]] == specification[
            "components"
        ]
        assert {item["axis_role"]: item["normalized_value"] for item in mapping["values"]} == (
            specification["values"]
        )
        assert all(
            value["derivation"] == "SUM_OF_VISIBLE_VERIFIED_SOURCE_COMPONENTS"
            for value in mapping["values"]
        )
    assert all(not trial["verified_source_only_rows"] for trial in result["trials"])


def test_visible_vpb_dash_is_zero_and_all_detected_numerics_match_source(
    result: dict[str, object],
) -> None:
    vpb = next(trial for trial in result["trials"] if trial["document_provenance"] == "VPB")
    catchall = next(
        mapping for mapping in vpb["verified_mappings"] if mapping["role"] == "OTHER_RISK_CATCHALL"
    )
    other = next(
        component
        for component in catchall["source_components"]
        if component["role"] == "OTHER_RISK_ASSET"
    )
    current = next(value for value in other["values"] if value["axis_role"] == "CURRENT_PERIOD")
    assert current["pixel_transcription"] == "-"
    assert current["normalized_value"] == 0
    assert current["source_line_index"] is None
    assert result["metrics"]["fresh_vietocr_numeric_disagreement_count"] == 0


def test_all_visible_accounting_equations_close(result: dict[str, object]) -> None:
    equations = [
        equation
        for trial in result["trials"]
        for equation in trial["verified_accounting_equations"]
    ]
    assert len(equations) == 12
    assert all(
        equation["status"] == "VERIFIED_EXACT"
        and equation["computed_value"] == equation["visible_total"]
        for equation in equations
    )


def test_schema_bindings_use_live_1221_family_positions(result: dict[str, object]) -> None:
    bindings = {
        mapping["schema_binding"]["report_norm_id"]: mapping["schema_binding"]
        for trial in result["trials"]
        for mapping in trial["verified_mappings"]
    }
    assert bindings[1221]["display_order"] == 781
    assert bindings[1228]["display_order"] == 791
    assert all(
        binding["schema_parent_report_norm_id"] == 1221
        for report_norm_id, binding in bindings.items()
        if report_norm_id != 1221
    )


def test_public_validator_rejects_coordinated_aggregate_tamper(
    result: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    forged = copy.deepcopy(result)
    vpb = next(trial for trial in forged["trials"] if trial["document_provenance"] == "VPB")
    aggregate = next(
        mapping for mapping in vpb["verified_mappings"] if mapping["role"] == "OTHER_RISK_CATCHALL"
    )
    aggregate["values"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + builder.base.canonical_json_sha256_v1(material)
    monkeypatch.setattr(
        builder,
        "build_live_annual_2025_credit_risk_provision_expense_8bank_codex_verified_mapping_v1",
        lambda: result,
    )
    with pytest.raises(
        builder.Annual2025CreditRiskProvisionExpense8BankError,
        match="does not replay exactly",
    ):
        builder.validate_live_annual_2025_credit_risk_provision_expense_8bank_codex_verified_mapping_v1(
            forged
        )
