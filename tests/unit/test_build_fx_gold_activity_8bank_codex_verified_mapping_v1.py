from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_fx_gold_activity_8bank_codex_verified_mapping_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_fx_gold_activity_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _result() -> dict[str, object]:
    return json.loads((_ROOT / builder.RESULT_PATH).read_text())


def test_review_separates_detailed_notes_from_negative_controls() -> None:
    review = builder._review_blueprint()
    assert [document["bank_code"] for document in review["documents"]] == [
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "VCB",
        "CTG",
        "BID",
        "VIB",
    ]
    assert [document["page_span"] for document in review["documents"]] == [
        None,
        [47, 47],
        [63, 63],
        None,
        None,
        None,
        None,
        [46, 46],
    ]


def test_persisted_result_has_exact_verified_denominator() -> None:
    result = builder._validate_result(_result())
    assert result["metrics"] == {
        "accounting_equation_verified_count": 18,
        "detailed_note_not_present_document_count": 5,
        "document_count": 8,
        "document_unique_region_count": 3,
        "fresh_vietocr_numeric_disagreement_count": 0,
        "mapping_verified_count": 23,
        "open_source_row_count": 0,
        "q1_source_period_caveat_document_count": 1,
        "verified_value_cell_count": 46,
    }


def test_combined_and_split_spot_gold_variants_do_not_double_count() -> None:
    trials = {trial["document_provenance"]: trial for trial in _result()["trials"]}
    mbb_ids = {
        item["schema_binding"]["report_norm_id"] for item in trials["MBB"]["verified_mappings"]
    }
    vpb_ids = {
        item["schema_binding"]["report_norm_id"] for item in trials["VPB"]["verified_mappings"]
    }
    vib_ids = {
        item["schema_binding"]["report_norm_id"] for item in trials["VIB"]["verified_mappings"]
    }
    assert {6026, 6027}.issubset(mbb_ids)
    assert not {1177, 1178, 1183, 1184} & mbb_ids
    assert {1177, 1178, 1183, 1184}.issubset(vpb_ids)
    assert {1177, 1183}.issubset(vib_ids)
    assert not {1178, 1184, 6026, 6027} & vib_ids


@pytest.mark.parametrize(
    "roles",
    [
        {"INCOME_SPOT_FX_AND_GOLD", "INCOME_SPOT_FX"},
        {"INCOME_SPOT_FX_AND_GOLD", "INCOME_GOLD"},
        {"EXPENSE_SPOT_FX_AND_GOLD", "EXPENSE_SPOT_FX"},
        {"EXPENSE_SPOT_FX_AND_GOLD", "EXPENSE_GOLD"},
    ],
)
def test_even_partial_combined_and_split_overlap_is_rejected(roles: set[str]) -> None:
    with pytest.raises(
        builder.FxGoldActivity8BankCodexVerifiedMappingV1Error,
        match="double counted",
    ):
        builder._assert_no_combined_split_spot_gold_overlap(roles)


def test_every_verified_value_uses_matching_independent_numeric_axis() -> None:
    values = [
        value
        for trial in _result()["trials"]
        for mapping in trial["verified_mappings"]
        for value in mapping["values"]
    ]
    assert len(values) == 46
    assert all(
        value["fresh_vietocr_numeric_status"] == "MATCHES_SOURCE_NUMERIC_CHALLENGER"
        and value["source_numeric_challenger_status"] == "MATCHED_VISIBLE_PIXEL_TRANSCRIPTION"
        for value in values
    )


def test_public_replay_rejects_coordinated_value_tamper() -> None:
    forged = copy.deepcopy(_result())
    forged["trials"][1]["verified_mappings"][0]["values"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0083:result:" + builder.canonical_json_sha256_v1(material)
    with pytest.raises(
        builder.FxGoldActivity8BankCodexVerifiedMappingV1Error,
        match="replay exactly",
    ):
        builder.validate_live_fx_gold_activity_8bank_codex_verified_mapping_v1(forged)
