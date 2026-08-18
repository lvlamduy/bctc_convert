from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT / "scripts/experiments/"
    "build_annual_2025_fx_gold_activity_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_fx_gold_activity_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)

_ORDER = ["ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB"]
_PAGES = [[68, 68], [73, 73], [69, 69], [50, 50], [59, 59], [58, 58], [55, 55], [51, 51]]


def _persisted() -> dict[str, object]:
    return json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())


def _review() -> dict[str, object]:
    return json.loads((builder.PROJECT_ROOT / builder.REVIEW_PATH).read_text())


def _trial(code: str) -> dict[str, object]:
    return next(item for item in _persisted()["trials"] if item["document_provenance"] == code)


def test_review_covers_one_unique_region_in_all_eight_complete_pdfs() -> None:
    review = _review()
    assert review["scan_id"] == builder.EXPECTED_SCAN_ID
    assert [item["bank_code"] for item in review["documents"]] == _ORDER
    assert [item["page_span"] for item in review["documents"]] == _PAGES
    assert all(item["source_period"] == "2025-12-31" for item in review["documents"])
    assert review["documents"][1]["presentation"] == (
        "COMBINED_SPOT_FX_GOLD_LEADING_PARENTS_LABELLED_NET"
    )
    assert review["documents"][4]["presentation"] == (
        "SPLIT_SPOT_GOLD_REVALUATION_DERIVATIVES_FX_DIFFERENCE_TRAILING_TOTALS"
    )


def test_persisted_result_has_exact_denominators_and_schema_bindings() -> None:
    result = _persisted()
    assert result["metrics"] == builder._EXPECTED_METRICS
    assert [item["document_provenance"] for item in result["trials"]] == _ORDER
    assert [item["page_span"] for item in result["trials"]] == _PAGES
    for trial in result["trials"]:
        code = trial["document_provenance"]
        assert {
            row["schema_binding"]["report_norm_id"] for row in trial["verified_mappings"]
        } == builder._EXPECTED_REPORT_NORM_IDS[code]
        assert trial["whole_document_uniqueness"] == {
            "complete_region_count": 1,
            "status": "UNIQUE_FULL_MATCH",
        }


def test_all_income_expense_and_net_equations_close_exactly() -> None:
    result = _persisted()
    equations = [
        equation
        for trial in result["trials"]
        for equation in trial["verified_accounting_equations"]
    ]
    assert len(equations) == 48
    assert all(item["status"] == "CORROBORATED_EXACT" for item in equations)
    for trial in result["trials"]:
        mapped = {
            row["schema_binding"]["report_norm_id"]: {
                value["axis_role"]: value["normalized_value"] for value in row["values"]
            }
            for row in trial["verified_mappings"]
        }
        for equation in trial["verified_accounting_equations"]:
            assert (
                equation["computed_value"]
                == mapped[equation["total_report_norm_id"]][equation["period_role"]]
            )


def test_acb_unprinted_parents_are_derived_only_from_their_visible_children() -> None:
    acb = _trial("ACB")
    income = next(row for row in acb["verified_mappings"] if row["role"] == "INCOME_PARENT")
    expense = next(row for row in acb["verified_mappings"] if row["role"] == "EXPENSE_PARENT")
    assert income["topology"] == "PARENT_VALUE_DERIVED_AS_EXACT_SUM_OF_VISIBLE_CHILDREN"
    assert expense["topology"] == "PARENT_VALUE_DERIVED_AS_EXACT_SUM_OF_VISIBLE_CHILDREN"
    assert [len(value["components"]) for value in income["values"]] == [3, 3]
    assert [len(value["components"]) for value in expense["values"]] == [3, 3]
    assert {value["axis_role"]: value["normalized_value"] for value in income["values"]} == {
        "CURRENT_PERIOD": 3_053_488,
        "COMPARATIVE_PERIOD": 2_880_293,
    }
    assert {value["axis_role"]: value["normalized_value"] for value in expense["values"]} == {
        "CURRENT_PERIOD": -1_321_602,
        "COMPARATIVE_PERIOD": -1_709_541,
    }


def test_vcb_aggregates_gold_and_derivative_revaluation_without_splitting_values() -> None:
    vcb = _trial("VCB")
    by_role = {row["role"]: row for row in vcb["verified_mappings"]}
    assert len(by_role["INCOME_GOLD"]["label_evidence"]) == 2
    assert len(by_role["INCOME_CURRENCY_DERIVATIVES"]["label_evidence"]) == 2
    assert len(by_role["EXPENSE_CURRENCY_DERIVATIVES"]["label_evidence"]) == 2
    assert {
        value["axis_role"]: value["normalized_value"] for value in by_role["INCOME_GOLD"]["values"]
    } == {"CURRENT_PERIOD": 0, "COMPARATIVE_PERIOD": 64_601}
    assert {
        value["axis_role"]: value["normalized_value"]
        for value in by_role["INCOME_CURRENCY_DERIVATIVES"]["values"]
    } == {"CURRENT_PERIOD": 4_065_343, "COMPARATIVE_PERIOD": 3_279_215}


def test_all_five_visible_dashes_are_authenticated_and_normalized_to_zero() -> None:
    dashes = [
        component
        for trial in _persisted()["trials"]
        for row in trial["verified_mappings"]
        for value in row["values"]
        for component in value["components"]
        if component["source_numeric_challenger_status"]
        == "VISIBLE_AUTHENTICATED_PIXEL_DASH_NOT_DETECTED_AS_SOURCE_LINE"
    ]
    assert len(dashes) == 5
    assert all(
        item["normalized_value"] == 0
        and item["pixel_transcription"] == "-"
        and item["source_line_index"] is None
        for item in dashes
    )


def test_combined_and_split_spot_gold_roles_never_overlap_within_one_document() -> None:
    for trial in _persisted()["trials"]:
        roles = {row["role"] for row in trial["verified_mappings"]}
        for prefix in ("INCOME", "EXPENSE"):
            if f"{prefix}_SPOT_FX_AND_GOLD" in roles:
                assert f"{prefix}_SPOT_FX" not in roles
                assert f"{prefix}_GOLD" not in roles


def test_exact_pins_reject_metric_or_schema_binding_drift() -> None:
    tampered = copy.deepcopy(_persisted())
    tampered["metrics"]["mapping_verified_count"] -= 1
    try:
        builder._assert_result(tampered)
    except builder.Annual2025FxGoldActivity8BankError:
        pass
    else:
        raise AssertionError("annual FX/gold metric drift was accepted")

    tampered = copy.deepcopy(_persisted())
    tampered["trials"][0]["verified_mappings"][0]["schema_binding"]["report_norm_id"] = 999999
    try:
        builder._assert_result(tampered)
    except builder.Annual2025FxGoldActivity8BankError:
        pass
    else:
        raise AssertionError("annual FX/gold schema-binding drift was accepted")


def test_persisted_result_exactly_live_replays() -> None:
    rebuilt = builder.build_live_annual_2025_fx_gold_activity_8bank_codex_verified_mapping_v1()
    assert rebuilt == _persisted()
    assert rebuilt["result_id"] == (
        "annual2025fxga8bcv1:result:b1b452595053e878a1ab4acfea26f4a5537612546d6b81698a712d695e5eb39d"
    )
