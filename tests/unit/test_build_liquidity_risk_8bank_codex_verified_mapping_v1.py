from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/experiments/build_liquidity_risk_8bank_codex_verified_mapping_v1.py"


def _module():
    name = "build_liquidity_risk_8bank_codex_verified_mapping_v1_test_target"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _result(module):
    return json.loads((ROOT / module.RESULT_PATH).read_text())


def test_live_result_verifies_five_tables_bounds_two_absences_and_retains_vib() -> None:
    module = _module()
    result = module.build_live_liquidity_risk_8bank_codex_verified_mapping_v1()
    assert module.same_typed_json_v1(result, _result(module))
    assert result["metrics"] == {
        "accounting_equation_verified_count": 28,
        "detailed_table_not_present_document_count": 2,
        "document_count": 8,
        "document_unique_region_count": 6,
        "fresh_vietocr_numeric_disagreement_count": 21,
        "mapping_verified_count": 84,
        "open_source_group_count": 19,
        "open_source_value_cell_count": 52,
        "q1_source_period_caveat_document_count": 1,
        "rotated_numeric_unresolved_document_count": 1,
        "source_presentation_residual_count": 8,
        "verified_value_cell_count": 84,
    }
    assert [trial["document_provenance"] for trial in result["trials"]] == [
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "VCB",
        "CTG",
        "BID",
        "VIB",
    ]
    assert [trial["status"] for trial in result["trials"]] == [
        "CONFIRMED_DETAILED_TABLE_NOT_PRESENT_IN_BOUND_REPORT",
        "VERIFIED_BY_CODEX_WITH_RETAINED_SOURCE_GAPS",
        "VERIFIED_BY_CODEX_WITH_RETAINED_SOURCE_GAPS",
        "VERIFIED_BY_CODEX_WITH_RETAINED_SOURCE_GAPS",
        "VERIFIED_BY_CODEX_WITH_RETAINED_SOURCE_GAPS",
        "VERIFIED_BY_CODEX_WITH_RETAINED_SOURCE_GAPS",
        "CONFIRMED_DETAILED_TABLE_NOT_PRESENT_IN_BOUND_REPORT",
        "UNRESOLVED_WITH_RETAINED_SOURCE_GAPS",
    ]


def test_every_promoted_cell_participates_in_an_exact_accounting_equation() -> None:
    module = _module()
    result = _result(module)
    assert all(
        equation["computed_value"] == equation["visible_value"]
        and equation["residual"] == 0
        and equation["status"] == "VERIFIED_EXACT"
        for trial in result["trials"]
        for equation in trial["verified_accounting_equations"]
    )
    assert all(
        value["source_numeric_challenger_status"] == "MATCHED_VISIBLE_PIXEL_TRANSCRIPTION"
        for trial in result["trials"]
        for mapping in trial["verified_mappings"]
        for value in mapping["values"]
    )
    assert (
        sum(
            len(mapping["values"])
            for trial in result["trials"]
            for mapping in trial["verified_mappings"]
        )
        == 84
    )


def test_combined_and_split_overdue_variants_share_one_graph() -> None:
    module = _module()
    scan_result = module.scanner.build_live_liquidity_risk_full_document_scan_v1()
    mbb_axes = set(
        scan_result["trials"][1]["matcher_result"]["regions"][0]["layout"]["maturity_axes_observed"]
    )
    vpb_axes = set(
        scan_result["trials"][2]["matcher_result"]["regions"][0]["layout"]["maturity_axes_observed"]
    )
    assert "OVERDUE" in mbb_axes
    assert {"OVERDUE_GT3M", "OVERDUE_LE3M"} <= vpb_axes
    vpb = _result(module)["trials"][2]
    mapped_ids = {
        mapping["schema_binding"]["report_norm_id"]
        for mapping in vpb["verified_mappings"]
        if mapping["maturity_axis"] == "WITHIN_GT5Y"
    }
    assert mapped_ids == {1899, 1911, 1920}


def test_vpb_nonclosing_printed_gaps_are_retained_not_repaired() -> None:
    module = _module()
    vpb = _result(module)["trials"][2]
    assert {
        (item["maturity_axis"], item["residual"]) for item in vpb["source_presentation_residuals"]
    } == {
        ("WITHIN_LE1M", 275499),
        ("WITHIN_1_3M", 6000),
        ("WITHIN_3_12M", -6001),
        ("WITHIN_1_5Y", -275500),
    }


def test_rotated_vib_numeric_axis_and_missing_closure_stay_open() -> None:
    module = _module()
    result = _result(module)
    vib = result["trials"][7]
    assert vib["verified_mappings"] == []
    assert {row["reason"] for row in vib["verified_source_only_rows"]} == {
        "ROTATED_SOURCE_NUMERIC_AXIS_REQUIRES_INDEPENDENT_CHALLENGER"
    }
    assert [
        row["gap_id"] for trial in result["trials"] for row in trial["verified_source_only_rows"]
    ] == [f"LRISK-{index:03d}" for index in range(1, 20)]
    assert {
        trial["document_provenance"] for trial in result["trials"] if trial["absence_evidence"]
    } == {
        "ACB",
        "BID",
    }


def test_public_exact_replay_rejects_coordinated_value_tamper() -> None:
    module = _module()
    forged = copy.deepcopy(_result(module))
    forged["trials"][1]["verified_mappings"][0]["values"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0103:result:" + module.canonical_json_sha256_v1(material)
    with pytest.raises(
        module.LiquidityRisk8BankCodexVerifiedMappingV1Error,
        match="replay exactly",
    ):
        module.validate_live_liquidity_risk_8bank_codex_verified_mapping_v1(forged)


def test_typed_metric_and_authority_substitution_rejects() -> None:
    module = _module()
    result = _result(module)
    forged = copy.deepcopy(result)
    forged["metrics"]["verified_value_cell_count"] = 84.0
    with pytest.raises(module.LiquidityRisk8BankCodexVerifiedMappingV1Error):
        module._validate_result(forged)
    forged = copy.deepcopy(result)
    forged["authority"]["blank_cell_interpreted_as_zero"] = 0
    with pytest.raises(module.LiquidityRisk8BankCodexVerifiedMappingV1Error):
        module._validate_result(forged)
