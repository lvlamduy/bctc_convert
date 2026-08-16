from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_income_tax_8bank_codex_verified_mapping_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_income_tax_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _result() -> dict[str, object]:
    return json.loads((_ROOT / builder.RESULT_PATH).read_text())


def test_review_distinguishes_three_reconciliations_and_five_bounded_absences() -> None:
    documents = builder._review_blueprint()["documents"]
    assert [item["bank_code"] for item in documents] == [
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "VCB",
        "CTG",
        "BID",
        "VIB",
    ]
    assert [item["page_span"] for item in documents] == [
        None,
        [50, 50],
        [59, 59],
        None,
        None,
        None,
        None,
        [48, 48],
    ]


def test_persisted_result_has_exact_verified_denominator() -> None:
    result = builder._validate_result(_result())
    assert result["metrics"] == {
        "accounting_equation_verified_count": 20,
        "detailed_note_not_present_document_count": 5,
        "document_count": 8,
        "document_unique_region_count": 3,
        "fresh_vietocr_numeric_disagreement_count": 1,
        "mapping_verified_count": 28,
        "open_source_row_count": 1,
        "q1_source_period_caveat_document_count": 1,
        "verified_value_cell_count": 56,
        "visible_source_dash_zero_component_count": 2,
    }
    assert result["schema_family"]["mapped_report_norm_ids"] == list(range(5723, 5738))


def test_vpb_visible_dashes_are_zero_only_inside_controlled_aggregate() -> None:
    result = _result()
    vpb = result["trials"][2]
    aggregate = next(
        item for item in vpb["verified_mappings"] if item["role"] == "NON_TAXABLE_AGGREGATE"
    )
    comparative = next(
        value for value in aggregate["values"] if value["axis_role"] == "COMPARATIVE_PERIOD"
    )
    assert comparative["normalized_value"] == 379_309
    assert [item["normalized_value"] for item in comparative["component_evidence"]] == [
        0,
        379_309,
        0,
    ]
    assert [item["source_numeric_challenger"] for item in comparative["component_evidence"]] == [
        "-",
        "379.309",
        "-",
    ]


def test_vib_blank_current_adjustment_is_not_zero_and_stays_open() -> None:
    result = _result()
    row = result["trials"][7]["verified_source_only_rows"][0]
    assert row["row_id"] == "TAX-001"
    assert row["blank_axes"] == ["CURRENT_PERIOD"]
    assert [(value["axis_role"], value["normalized_value"]) for value in row["values"]] == [
        ("COMPARATIVE_PERIOD", 163)
    ]


def test_mbb_full_five_component_equation_closes_both_axes() -> None:
    result = _result()
    equations = [
        item
        for item in result["trials"][1]["verified_accounting_equations"]
        if item["name"] == "FIVE_COMPONENTS_EQUAL_TOTAL_TAX"
    ]
    assert [(item["axis_role"], item["visible_total"]) for item in equations] == [
        ("CURRENT_PERIOD", 4_040_065),
        ("COMPARATIVE_PERIOD", 3_209_731),
    ]


def test_public_replay_rejects_coordinated_value_tamper() -> None:
    forged = copy.deepcopy(_result())
    forged["trials"][1]["verified_mappings"][0]["values"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0091:result:" + builder.canonical_json_sha256_v1(material)
    with pytest.raises(
        builder.IncomeTax8BankCodexVerifiedMappingV1Error,
        match="replay exactly",
    ):
        builder.validate_live_income_tax_8bank_codex_verified_mapping_v1(forged)
