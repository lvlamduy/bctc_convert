from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT / "scripts/experiments/"
    "build_annual_2025_long_term_investments_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location("annual_2025_lti_builder_test", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def live() -> dict:
    return builder.build_live_annual_2025_long_term_investments_8bank_codex_verified_mapping_v1()


def _trial(result: dict, bank: str) -> dict:
    return next(item for item in result["trials"] if item["document_provenance"] == bank)


def test_all_eight_annual_regions_are_unique_and_verified(live: dict) -> None:
    assert live["metrics"] == {
        "accounting_equation_verified_count": 11,
        "dash_cell_normalized_to_zero_count": 1,
        "document_count": 8,
        "document_unique_region_count": 8,
        "mapping_verified_count": 28,
        "unresolved_document_count": 0,
        "verified_value_cell_count": 56,
    }
    assert [trial["document_provenance"] for trial in live["trials"]] == list(
        builder.EXPECTED_DOCUMENT_ORDER
    )
    assert all(
        trial["status"] == "VERIFIED_BY_CODEX"
        and trial["source_period_status"]
        == "VERIFIED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
        and trial["whole_document_uniqueness"]
        == {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
        for trial in live["trials"]
    )


def test_mapping_sets_match_live_schema_without_bank_specific_parser(live: dict) -> None:
    for trial in live["trials"]:
        code = trial["document_provenance"]
        ids = {item["schema_binding"]["report_norm_id"] for item in trial["verified_mappings"]}
        assert ids == builder._EXPECTED_IDS[code]
        assert all(
            value["source_numeric_challenger_status"]
            in {
                "MATCHED_VISIBLE_PIXEL_TRANSCRIPTION",
                "VISIBLE_DASH_CELL_WITH_NO_TEXT_LINE_NORMALIZED_TO_ZERO",
            }
            for item in trial["verified_mappings"]
            for value in item["values"]
        )


def test_ctg_visible_dash_is_zero_and_both_period_equations_close(live: dict) -> None:
    ctg = _trial(live, "CTG")
    provision = next(
        item
        for item in ctg["verified_mappings"]
        if item["schema_binding"]["report_norm_id"] == 5959
    )
    assert [value["normalized_value"] for value in provision["values"]] == [0, -7_291]
    assert provision["values"][0]["source_numeric_challenger_status"] == (
        "VISIBLE_DASH_CELL_WITH_NO_TEXT_LINE_NORMALIZED_TO_ZERO"
    )
    axes = ctg["verified_accounting_equations"][0]["axes"]
    assert [(axis["computed_total"], axis["visible_total"]) for axis in axes] == [
        (4_428_296, 4_428_296),
        (3_933_844, 3_933_844),
    ]


def test_vcb_continuation_page_and_carrying_values_are_bound(live: dict) -> None:
    vcb = _trial(live, "VCB")
    joint = next(
        item
        for item in vcb["verified_mappings"]
        if item["schema_binding"]["report_norm_id"] == 6066
    )
    associate = next(
        item
        for item in vcb["verified_mappings"]
        if item["schema_binding"]["report_norm_id"] == 6067
    )
    assert [value["normalized_value"] for value in joint["values"]] == [734_296, 763_736]
    assert associate["page_sequence"] == 45
    assert [value["normalized_value"] for value in associate["values"]] == [12_342, 10_440]
    assert [value["source_line_index"] for value in associate["values"]] == [28, 46]
    assert associate["fresh_vietocr_label_proposal"] == "Đầu tư vào công ty liên kết"


def test_vpb_comparative_dash_is_equation_only_not_a_fake_schema_leaf(live: dict) -> None:
    vpb = _trial(live, "VPB")
    assert [item["schema_binding"]["report_norm_id"] for item in vpb["verified_mappings"]] == [5960]
    equation = vpb["verified_accounting_equations"][0]
    assert equation["axes"][0]["component_values"] == [3_934, 185_276, 2_750]
    assert equation["axes"][1]["component_values"] == [3_934, 185_276, 0]
    assert [axis["visible_total"] for axis in equation["axes"]] == [191_960, 189_210]


def test_coordinated_result_rehash_and_wrong_mapping_fail_live_replay(live: dict) -> None:
    forged = copy.deepcopy(live)
    forged["trials"][1]["verified_mappings"][0]["values"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + canonical_json_sha256_v1(material)
    with pytest.raises(Exception, match="replay exactly"):
        builder.validate_annual_2025_long_term_investments_8bank_codex_verified_mapping_replay_v1(
            forged
        )


def test_persisted_review_and_result_equal_exact_live_bytes(live: dict) -> None:
    assert (_ROOT / builder.REVIEW_PATH).read_bytes() == canonical_json_bytes_v1(
        builder.build_annual_2025_long_term_investments_pixel_review_blueprint_v1()
    )
    assert (_ROOT / builder.RESULT_PATH).read_bytes() == canonical_json_bytes_v1(live)
