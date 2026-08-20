from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1

ROOT = Path(__file__).resolve().parents[2]
PATH = (
    ROOT / "scripts/experiments/build_annual_2025_currency_risk_8bank_codex_verified_mapping_v1.py"
)
SPEC = importlib.util.spec_from_file_location("annual_2025_currency_risk_mapping_test", PATH)
assert SPEC is not None and SPEC.loader is not None
builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = builder
SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def live() -> dict:
    return builder.build_live_annual_2025_currency_risk_8bank_codex_verified_mapping_v1()


def _trial(result: dict, bank: str) -> dict:
    return next(item for item in result["trials"] if item["document_provenance"] == bank)


def test_eight_unique_annual_regions_verify_the_supported_core(live: dict) -> None:
    assert live["metrics"] == {
        "accounting_equation_verified_count": 74,
        "authenticated_pixel_dash_zero_count": 8,
        "comparative_table_excluded_count": 4,
        "document_count": 8,
        "document_unique_region_count": 8,
        "mapping_verified_count": 155,
        "open_source_group_count": 7,
        "open_source_value_cell_count": 34,
        "rotated_ppocrv6_document_count": 1,
        "source_presentation_residual_count": 0,
        "verified_value_cell_count": 155,
    }
    assert [trial["document_provenance"] for trial in live["trials"]] == list(
        builder.EXPECTED_DOCUMENT_ORDER
    )
    assert all(
        trial["whole_document_uniqueness"]
        == {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
        for trial in live["trials"]
    )


def test_mbb_multiline_state_labels_bind_their_own_numeric_baseline(live: dict) -> None:
    mbb = _trial(live, "MBB")
    values = {
        (mapping["axis_role"], mapping["source_role"]): mapping["values"][0]["normalized_value"]
        for mapping in mbb["verified_mappings"]
    }
    assert values[("USD", "ASSET_TOTAL")] == 82_191_993
    assert values[("USD", "LIABILITY_TOTAL")] == 85_338_174
    assert values[("USD", "STATE_INTERNAL")] == -3_146_181
    assert values[("USD", "STATE_EXTERNAL")] == 933_477
    assert values[("USD", "STATE_COMBINED")] == -2_212_704
    assert mbb["verified_source_only_rows"] == []
    assert len(mbb["verified_accounting_equations"]) == 8


def test_only_explicit_unsupported_currency_axes_remain_open(live: dict) -> None:
    unresolved = {
        (trial["document_provenance"], row["axis_role"], row["reason"])
        for trial in live["trials"]
        for row in trial["verified_source_only_rows"]
    }
    assert unresolved == {
        ("ACB", "AUD", "NO_EQUIVALENT_CORE_SCHEMA_ROW"),
        ("ACB", "CAD", "NO_EQUIVALENT_CORE_SCHEMA_ROW"),
        ("ACB", "GOLD", "NO_GOLD_CURRENCY_AXIS_SCHEMA_BRANCH"),
        ("ACB", "JPY", "NO_EQUIVALENT_CORE_SCHEMA_ROW"),
        ("VPB", "GOLD", "NO_GOLD_CURRENCY_AXIS_SCHEMA_BRANCH"),
        ("HDB", "GOLD", "NO_GOLD_CURRENCY_AXIS_SCHEMA_BRANCH"),
        ("CTG", "GOLD", "NO_GOLD_CURRENCY_AXIS_SCHEMA_BRANCH"),
    }


def test_visible_dashes_are_zero_only_with_pixel_components(live: dict) -> None:
    zeroes = [
        value
        for trial in live["trials"]
        for group in (trial["verified_mappings"], trial["verified_source_only_rows"])
        for row in group
        for value in row["values"]
        if value.get("source_numeric_challenger_status") == "AUTHENTICATED_UNIQUE_VISIBLE_DASH_ZERO"
    ]
    assert len(zeroes) == 8
    assert all(value["normalized_value"] == 0 for value in zeroes)
    assert all(value["pixel_transcription"] == "-" for value in zeroes)
    assert all(value["visual_dash_evidence"]["observation"] == "DASH" for value in zeroes)


def test_bid_upright_numbers_close_and_only_bad_text_uses_gemma(live: dict) -> None:
    bid = _trial(live, "BID")
    labels = {
        mapping["source_role"]: mapping["labels"][0]
        for mapping in bid["verified_mappings"]
        if mapping["axis_role"] == "EUR"
    }
    assert "gemma4_gpu_text_rescue" not in labels["ASSET_TOTAL"]
    assert "gemma4_gpu_text_rescue" not in labels["LIABILITY_TOTAL"]
    assert "gemma4_gpu_text_rescue" not in labels["STATE_COMBINED"]
    assert labels["STATE_INTERNAL"]["gemma4_gpu_text_rescue"]["gemma4_text"] == (
        "Trạng thái tiền tệ nội bảng"
    )
    assert labels["STATE_EXTERNAL"]["gemma4_gpu_text_rescue"]["gemma4_text"] == (
        "Trạng thái tiền tệ ngoại bảng"
    )
    total = {
        mapping["source_role"]: mapping["values"][0]["normalized_value"]
        for mapping in bid["verified_mappings"]
        if mapping["axis_role"] == "TOTAL"
    }
    assert total == {
        "ASSET_TOTAL": 248_906_117,
        "LIABILITY_TOTAL": 249_975_009,
        "STATE_COMBINED": -3_573_206,
        "STATE_EXTERNAL": -2_504_314,
        "STATE_INTERNAL": -1_068_892,
    }


def test_vcb_visible_liability_scope_maps_to_approved_vnd_row(live: dict) -> None:
    vcb = _trial(live, "VCB")
    mapping = next(
        item
        for item in vcb["verified_mappings"]
        if item["axis_role"] == "VND" and item["source_role"] == "LIABILITY_TOTAL"
    )
    assert mapping["schema_binding"]["report_norm_id"] == 1418
    assert mapping["values"][0]["normalized_value"] == 1_919_020_603


def test_persisted_result_and_review_equal_live_rebuild(live: dict) -> None:
    result_bytes = (ROOT / builder.RESULT_PATH).read_bytes()
    review_bytes = (ROOT / builder.REVIEW_PATH).read_bytes()
    assert result_bytes == canonical_json_bytes_v1(live) + b"\n"
    assert review_bytes == canonical_json_bytes_v1(builder._review(live)) + b"\n"


def test_coordinated_value_rehash_cannot_pass_public_replay(
    live: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    forged = copy.deepcopy(live)
    forged["trials"][1]["verified_mappings"][0]["values"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + builder.canonical_json_sha256_v1(material)
    monkeypatch.setattr(
        builder,
        "build_live_annual_2025_currency_risk_8bank_codex_verified_mapping_v1",
        lambda: live,
    )
    with pytest.raises(Exception, match="replay exactly"):
        builder.validate_annual_2025_currency_risk_8bank_codex_verified_mapping_replay_v1(forged)
