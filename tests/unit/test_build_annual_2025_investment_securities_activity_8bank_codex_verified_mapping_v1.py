from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT / "scripts/experiments/"
    "build_annual_2025_investment_securities_activity_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_investment_securities_activity_8bank_codex_verified_mapping_v1",
    _PATH,
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)

_ORDER = ["ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB"]
_PAGES = [[68, 68], [73, 73], [70, 70], [50, 50], [59, 59], [59, 59], [56, 56], [51, 51]]


def _persisted() -> dict[str, object]:
    return json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())


def _review() -> dict[str, object]:
    return json.loads((builder.PROJECT_ROOT / builder.REVIEW_PATH).read_text())


def _trial(code: str) -> dict[str, object]:
    return next(item for item in _persisted()["trials"] if item["document_provenance"] == code)


def _provision(code: str) -> dict[str, object]:
    return next(
        row
        for row in _trial(code)["verified_mappings"]
        if row["schema_binding"]["report_norm_id"] == 1196
    )


def test_review_covers_one_unique_annual_region_in_every_document() -> None:
    review = _review()
    assert review["scan_id"] == builder.EXPECTED_SCAN_ID
    assert [item["bank_code"] for item in review["documents"]] == _ORDER
    assert [item["page_span"] for item in review["documents"]] == _PAGES
    assert all(item["source_period"] == "2025-12-31" for item in review["documents"])
    assert all(item["absence_evidence"] is None for item in review["documents"])


def test_persisted_result_has_exact_denominators_and_live_schema_bindings() -> None:
    result = _persisted()
    assert result["metrics"] == builder._EXPECTED_METRICS
    assert [item["document_provenance"] for item in result["trials"]] == _ORDER
    assert [item["page_span"] for item in result["trials"]] == _PAGES
    assert all(item["status"] == "VERIFIED_BY_CODEX" for item in result["trials"])
    for trial in result["trials"]:
        code = trial["document_provenance"]
        assert {
            row["schema_binding"]["report_norm_id"] for row in trial["verified_mappings"]
        } == builder._EXPECTED_REPORT_NORM_IDS[code]


def test_vpb_and_vib_multirow_provisions_are_verified_then_summed() -> None:
    vp = {item["axis_role"]: item for item in _provision("VPB")["values"]}
    vib = {item["axis_role"]: item for item in _provision("VIB")["values"]}
    assert [(item["normalized_value"], len(item["components"])) for item in vp.values()] == [
        (150_940, 2),
        (38_437, 2),
    ]
    assert [(item["normalized_value"], len(item["components"])) for item in vib.values()] == [
        (-33_586, 3),
        (1_500, 3),
    ]
    assert all(
        item["source_numeric_challenger_status"] == "SUM_OF_VERIFIED_VISIBLE_SOURCE_ROWS"
        for item in [*vp.values(), *vib.values()]
    )


def test_five_visible_dashes_are_zero_without_dropping_source_components() -> None:
    components = [
        component
        for trial in _persisted()["trials"]
        for mapping in trial["verified_mappings"]
        for value in mapping["values"]
        for component in value.get("components", [value])
    ]
    dashes = [item for item in components if item["source_line_index"] is None]
    assert len(components) == 70
    assert len(dashes) == 5
    assert all(
        item["normalized_value"] == 0
        and item["pixel_transcription"] == "-"
        and item["source_numeric_challenger_status"]
        == "VISIBLE_AUTHENTICATED_PIXEL_DASH_NOT_DETECTED_AS_SOURCE_LINE"
        for item in dashes
    )


def test_vcb_optional_provision_absence_closes_without_inventing_a_row() -> None:
    vcb = _trial("VCB")
    assert {row["schema_binding"]["report_norm_id"] for row in vcb["verified_mappings"]} == {
        1193,
        1194,
        1195,
    }
    assert all(
        item["computed_value"] in {3_616, 3_444} and item["term_report_norm_ids"] == [1194, 1195]
        for item in vcb["verified_accounting_equations"]
    )


def test_all_component_challengers_agree_and_all_sixteen_equations_close() -> None:
    result = _persisted()
    components = [
        component
        for trial in result["trials"]
        for mapping in trial["verified_mappings"]
        for value in mapping["values"]
        for component in value.get("components", [value])
    ]
    assert all(
        item["fresh_vietocr_numeric_status"] == "MATCHES_SOURCE_NUMERIC_CHALLENGER"
        for item in components
        if item["source_line_index"] is not None
    )
    assert sum(len(trial["verified_accounting_equations"]) for trial in result["trials"]) == 16


def test_exact_pins_reject_aggregate_or_schema_drift() -> None:
    tampered = copy.deepcopy(_persisted())
    provision = next(
        row
        for row in next(t for t in tampered["trials"] if t["document_provenance"] == "VPB")[
            "verified_mappings"
        ]
        if row["schema_binding"]["report_norm_id"] == 1196
    )
    provision["values"][0]["normalized_value"] += 1
    with pytest.raises(builder.Annual2025InvestmentSecuritiesActivity8BankError):
        builder._assert_result(tampered)

    tampered = copy.deepcopy(_persisted())
    tampered["metrics"]["mapping_verified_count"] += 1
    with pytest.raises(builder.Annual2025InvestmentSecuritiesActivity8BankError):
        builder._assert_result(tampered)


def test_persisted_result_exactly_live_replays() -> None:
    rebuilt = builder.build_live_annual_2025_investment_securities_activity_8bank_codex_verified_mapping_v1()
    assert rebuilt == _persisted()
    assert rebuilt["result_id"] == (
        "annual2025isa8bcv1:result:e63c7bc2305f2a7f9a9144253b48c46513c6b757c0d54dfce49a491e3ab6669c"
    )
