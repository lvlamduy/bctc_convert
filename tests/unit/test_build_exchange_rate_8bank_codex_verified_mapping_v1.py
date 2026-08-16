from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/experiments/build_exchange_rate_8bank_codex_verified_mapping_v1.py"


def _module():
    name = "build_exchange_rate_8bank_codex_verified_mapping_v1_test_target"
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


@pytest.mark.parametrize(
    ("surface", "decimal"),
    [
        ("26.300,00", "26300.00"),
        ("18.547.00", "18547.00"),
        ("26,286", "26286.00"),
        ("162.72", "162.72"),
        ("17.450.000", "17450000.00"),
        ("166", "166.00"),
    ],
)
def test_rate_parser_handles_document_level_separator_variants(surface: str, decimal: str) -> None:
    module = _module()
    assert module._decimal(module._rate_cents(surface)) == decimal


def test_live_result_maps_supported_rows_and_retains_every_schema_gap() -> None:
    module = _module()
    result = module.build_live_exchange_rate_8bank_codex_verified_mapping_v1()
    assert module.same_typed_json_v1(result, _result(module))
    assert result["metrics"] == {
        "detailed_table_not_present_document_count": 3,
        "document_count": 8,
        "document_unique_region_count": 5,
        "fresh_vietocr_label_disagreement_count": 0,
        "fresh_vietocr_label_fuzzy_recovery_count": 3,
        "fresh_vietocr_numeric_normalized_disagreement_count": 0,
        "fresh_vietocr_numeric_surface_disagreement_count": 2,
        "mapping_verified_count": 46,
        "out_of_schema_source_row_count": 15,
        "q1_source_period_caveat_document_count": 1,
        "verified_source_value_cell_count": 122,
        "verified_value_cell_count": 92,
    }
    assert [
        (trial["document_provenance"], trial["page_sequence"]) for trial in result["trials"]
    ] == [
        ("ACB", None),
        ("MBB", 61),
        ("VPB", 90),
        ("HDB", None),
        ("VCB", None),
        ("CTG", 61),
        ("BID", 35),
        ("VIB", 71),
    ]
    assert [
        row["gap_id"] for trial in result["trials"] for row in trial["verified_source_only_rows"]
    ] == [f"FXRATE-{index:03d}" for index in range(1, 16)]


def test_every_value_binds_pixel_source_and_fresh_transformer_without_using_fresh_numeric_truth() -> (
    None
):
    module = _module()
    result = _result(module)
    rows = [
        row
        for trial in result["trials"]
        for group in (trial["verified_mappings"], trial["verified_source_only_rows"])
        for row in group
    ]
    assert len(rows) == 61
    assert all(
        value["source_numeric_challenger_status"] == "MATCHED_VISIBLE_PIXEL_TRANSCRIPTION"
        and value["fresh_vietocr_numeric_status"] == "NORMALIZES_TO_SOURCE_NUMERIC_CHALLENGER"
        for row in rows
        for value in row["values"]
    )
    assert {
        row["code"] for trial in result["trials"] for row in trial["verified_source_only_rows"]
    } == {"CNY", "DKK", "NZD", "XAU", "NOK", "HKD", "KRW", "LAK"}


def test_q1_period_and_bid_vnd_inheritance_are_explicit() -> None:
    module = _module()
    result = _result(module)
    vp = result["trials"][2]
    bid = result["trials"][6]
    assert vp["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
    assert bid["unit_evidence"][0]["kind"] == "DOCUMENT_POLICY_VND_REFERENCE"
    assert bid["status"] == "VERIFIED_BY_CODEX_WITH_INHERITED_VND_POLICY_EVIDENCE"


def test_full_document_scan_is_unique_for_five_reports_and_bank_blind() -> None:
    module = _module()
    scan = module.scanner.build_live_exchange_rate_full_document_scan_v1()
    assert scan["scan_id"] == module.EXPECTED_SCAN_ID
    assert scan["metrics"] == {
        "bounded_table_absence_count": 3,
        "complete_region_count": 5,
        "document_count": 8,
        "document_unique_structural_match_count": 5,
        "mapping_verified_count": 0,
        "near_region_count": 5,
        "source_row_count": 61,
        "supported_schema_row_count": 46,
    }
    graph_source = (ROOT / "scripts/experiments/exchange_rate_variant_graph_v1.py").read_text()
    assert all(f'"{code}"' not in graph_source for code in module.EXPECTED_DOCUMENT_ORDER)


def test_public_exact_replay_rejects_coordinated_value_tamper() -> None:
    module = _module()
    forged = copy.deepcopy(_result(module))
    forged["trials"][1]["verified_mappings"][0]["values"][0]["normalized_value_cents"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0104:result:" + module.canonical_json_sha256_v1(material)
    with pytest.raises(
        module.ExchangeRate8BankCodexVerifiedMappingV1Error,
        match="replay exactly",
    ):
        module.validate_live_exchange_rate_8bank_codex_verified_mapping_v1(forged)


def test_typed_metric_and_authority_substitution_rejects() -> None:
    module = _module()
    result = _result(module)
    forged = copy.deepcopy(result)
    forged["metrics"]["mapping_verified_count"] = 46.0
    with pytest.raises(module.ExchangeRate8BankCodexVerifiedMappingV1Error):
        module._validate_result(forged)
    forged = copy.deepcopy(result)
    forged["authority"]["fresh_vietocr_used_as_numeric_truth"] = 0
    with pytest.raises(module.ExchangeRate8BankCodexVerifiedMappingV1Error):
        module._validate_result(forged)
