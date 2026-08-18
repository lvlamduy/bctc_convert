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
    / "scripts/experiments/build_annual_2025_bank_pledged_assets_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_bank_pledged_assets_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def result() -> dict[str, object]:
    built = builder.build_live_annual_2025_bank_pledged_assets_8bank_codex_verified_mapping_v1()
    persisted = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())
    assert builder._base().same_typed_json_v1(built, persisted)
    return built


def _trial(result: dict[str, object], code: str) -> dict[str, object]:
    return next(item for item in result["trials"] if item["document_provenance"] == code)


def _mapping(trial: dict[str, object], role: str) -> dict[str, object]:
    return next(item for item in trial["verified_mappings"] if item["role"] == role)


def test_five_unique_regions_three_absences_and_complete_schema_union(
    result: dict[str, object],
) -> None:
    assert result["result_id"] == builder.EXPECTED_RESULT_ID
    assert result["metrics"] == {
        "accounting_equation_verified_count": 10,
        "bound_report_detailed_note_absence_count": 3,
        "document_count": 8,
        "document_unique_region_count": 5,
        "mapping_verified_count": 13,
        "open_source_row_count": 0,
        "q1_source_period_caveat_document_count": 0,
        "source_hierarchy_double_count_contradiction_document_count": 0,
        "source_presentation_reconciliation_count": 0,
        "verified_value_cell_count": 26,
    }
    assert [trial["page_span"] for trial in result["trials"]] == [
        [74, 74],
        [78, 78],
        [74, 74],
        None,
        None,
        [63, 63],
        None,
        [54, 54],
    ]
    assert result["schema_family"]["mapped_report_norm_ids"] == list(range(1289, 1294))
    assert result["authority"]["bank_filename_note_or_page_used_as_matching_rule"] is False


def test_acb_pixel_dashes_are_zero_and_four_children_close_the_parent(
    result: dict[str, object],
) -> None:
    acb = _trial(result, "ACB")
    trading_comparative = _mapping(acb, "TRADING_SECURITIES")["values"][1]
    fixed_current = _mapping(acb, "FIXED_ASSETS")["values"][0]
    for value in (trading_comparative, fixed_current):
        assert value["normalized_value"] == 0
        assert value["pixel_transcription"] == "-"
        assert value["fresh_vietocr_numeric_status"] == "NO_SEMANTIC_LINE_FOR_VISIBLE_DASH"
        assert value["source_numeric_challenger_status"] == (
            "VISIBLE_AUTHENTICATED_PIXEL_DASH_NOT_DETECTED_AS_SOURCE_LINE"
        )
    assert len(acb["verified_mappings"]) - 1 == 4
    assert all(
        item["computed_value"] == item["visible_value"]
        for item in acb["verified_accounting_equations"]
    )


def test_mbb_owner_plus_one_child_is_a_complete_unique_variant(
    result: dict[str, object],
) -> None:
    mbb = _trial(result, "MBB")
    assert mbb["status"] == "VERIFIED_BY_CODEX"
    assert mbb["mapped_report_norm_ids"] == [1289, 1293]
    assert [item["normalized_value"] for item in _mapping(mbb, "OTHER_ASSETS")["values"]] == [
        4_508_464,
        12_260_320,
    ]
    assert all(
        item["computed_value"] == item["visible_value"]
        for item in mbb["verified_accounting_equations"]
    )


def test_vpb_ctg_vib_use_authenticated_controlled_catchall_sums(
    result: dict[str, object],
) -> None:
    expected = {
        "VPB": ([19_709_750, 13_644_923], [3, 3]),
        "CTG": ([17_256_980, 20_381_856], [2, 2]),
        "VIB": ([29_745_000, 37_958_207], [2, 2]),
    }
    for code, (values, component_counts) in expected.items():
        trial = _trial(result, code)
        other = _mapping(trial, "OTHER_ASSETS")
        assert [item["normalized_value"] for item in other["values"]] == values
        assert [len(item["component_evidence"]) for item in other["values"]] == component_counts
        assert all(
            item["computed_value"] == item["visible_value"]
            for item in trial["verified_accounting_equations"]
        )
    ctg_comparative = _mapping(_trial(result, "CTG"), "OTHER_ASSETS")["values"][1]
    assert ctg_comparative["component_evidence"][1]["pixel_transcription"] == "-"
    assert ctg_comparative["source_numeric_challenger"].endswith(" + -")


def test_hdb_vcb_bid_are_bounded_detailed_note_absences(
    result: dict[str, object],
) -> None:
    for code in ("HDB", "VCB", "BID"):
        trial = _trial(result, code)
        assert trial["status"] == "CONFIRMED_DETAILED_NOTE_NOT_PRESENT_IN_BOUND_REPORT"
        assert trial["absence_evidence"]["complete_pdf_pages_scanned"] is True
        assert trial["verified_mappings"] == []


def test_public_replay_rejects_coordinated_catchall_promotion(
    result: dict[str, object],
) -> None:
    forged = copy.deepcopy(result)
    _mapping(_trial(forged, "MBB"), "OTHER_ASSETS")["schema_binding"]["report_norm_id"] = 1291
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + builder._base().canonical_json_sha256_v1(
        material
    )
    with pytest.raises(
        builder.Annual2025BankPledgedAssets8BankError,
        match="bank-pledged-assets result ID drifted",
    ):
        builder.validate_annual_2025_bank_pledged_assets_8bank_codex_verified_mapping_replay_v1(
            forged
        )
