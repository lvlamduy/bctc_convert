from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1

ROOT = Path(__file__).resolve().parents[2]
PATH = (
    ROOT / "scripts/experiments/"
    "build_annual_2025_interest_rate_risk_8bank_codex_verified_mapping_v1.py"
)
SPEC = importlib.util.spec_from_file_location("annual_2025_interest_rate_risk_mapping_test", PATH)
assert SPEC is not None and SPEC.loader is not None
builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = builder
SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def live() -> dict:
    return builder.build_live_annual_2025_interest_rate_risk_8bank_codex_verified_mapping_v1()


def _trial(result: dict, bank: str) -> dict:
    return next(item for item in result["trials"] if item["document_provenance"] == bank)


def test_eight_unique_annual_regions_verify_the_exact_core(live: dict) -> None:
    assert live["metrics"] == {
        "accounting_equation_verified_count": 87,
        "authenticated_pixel_dash_zero_count": 10,
        "comparative_table_excluded_count": 4,
        "document_count": 8,
        "document_unique_region_count": 8,
        "mapping_verified_count": 280,
        "open_source_group_count": 1,
        "open_source_value_cell_count": 5,
        "rotated_ppocrv6_document_count": 3,
        "source_presentation_residual_count": 1,
        "verified_value_cell_count": 280,
    }
    assert [trial["document_provenance"] for trial in live["trials"]] == list(
        builder.EXPECTED_DOCUMENT_ORDER
    )
    assert all(
        trial["whole_document_uniqueness"]
        == {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
        for trial in live["trials"]
    )


def test_ctg_merged_header_keeps_overdue_and_no_interest_separate(live: dict) -> None:
    ctg = _trial(live, "CTG")
    by_axis: dict[str, set[str]] = {}
    for mapping in ctg["verified_mappings"]:
        by_axis.setdefault(mapping["repricing_axis"], set()).add(mapping["source_role"])
    assert list(sorted(by_axis)) == sorted(
        [
            "OVERDUE",
            "NO_INTEREST",
            "WITHIN_LE1M",
            "WITHIN_1_3M",
            "WITHIN_3_6M",
            "WITHIN_6_12M",
            "WITHIN_1_5Y",
            "WITHIN_GT5Y",
            "TOTAL",
        ]
    )
    assert by_axis["OVERDUE"] == {"ASSET_TOTAL", "LIABILITY_TOTAL", "STATE_INTERNAL"}
    assert by_axis["NO_INTEREST"] == {"ASSET_TOTAL", "LIABILITY_TOTAL", "STATE_INTERNAL"}
    assert ctg["verified_source_only_rows"] == []
    assert ctg["source_presentation_residuals"] == []


def test_header_ocr_noise_cannot_change_the_geometry_denominator() -> None:
    assert builder._column_surface_role("Tứt-3 tháng") == "WITHIN_1_3M"
    assert builder._column_surface_role("Tù trên 3tháng dén6tháng") == "WITHIN_3_6M"
    assert builder._column_surface_role("Trần 5 năm") == "WITHIN_GT5Y"
    assert builder._column_surface_role("B05/TCTD-HN Tóng TriuVND") == "TOTAL"


def test_bid_missing_external_row_is_not_invented(live: dict) -> None:
    bid = _trial(live, "BID")
    assert len(bid["verified_mappings"]) == 36
    assert {mapping["source_role"] for mapping in bid["verified_mappings"]} == {
        "ASSET_TOTAL",
        "LIABILITY_TOTAL",
        "STATE_COMBINED",
        "STATE_INTERNAL",
    }
    assert bid["verified_source_only_rows"] == []
    combined = [
        mapping
        for mapping in bid["verified_mappings"]
        if mapping["source_role"] == "STATE_COMBINED"
    ]
    assert len(combined) == 9
    assert all(
        mapping["verification_basis"]
        == "DIRECT_SOURCE_ROLE_AXIS_AND_INDEPENDENT_NUMERIC_CHALLENGER"
        for mapping in combined
    )


def test_visible_dashes_are_zero_only_with_authenticated_components(live: dict) -> None:
    zeroes = [
        value
        for trial in live["trials"]
        for group in (trial["verified_mappings"], trial["verified_source_only_rows"])
        for row in group
        for value in row["values"]
        if value.get("source_numeric_challenger_status") == "AUTHENTICATED_UNIQUE_VISIBLE_DASH_ZERO"
    ]
    assert len(zeroes) == 10
    assert all(value["normalized_value"] == 0 for value in zeroes)
    assert all(value["pixel_transcription"] == "-" for value in zeroes)
    assert all(value["visual_dash_evidence"]["observation"] == "DASH" for value in zeroes)


def test_one_source_residual_remains_unresolved(live: dict) -> None:
    residuals = [
        (trial["document_provenance"], residual)
        for trial in live["trials"]
        for residual in trial["source_presentation_residuals"]
    ]
    assert len(residuals) == 1
    bank, residual = residuals[0]
    assert bank == "VPB"
    assert residual["status"] == "UNRESOLVED_RESIDUAL"
    assert residual["residual"] != 0


def test_persisted_result_and_review_equal_live_rebuild(live: dict) -> None:
    result_bytes = (ROOT / builder.RESULT_PATH).read_bytes()
    review_bytes = (ROOT / builder.REVIEW_PATH).read_bytes()
    assert result_bytes == canonical_json_bytes_v1(live) + b"\n"
    assert review_bytes == canonical_json_bytes_v1(builder._review(live)) + b"\n"


def test_coordinated_rehash_cannot_pass_public_replay(
    live: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    forged = copy.deepcopy(live)
    forged["trials"][5]["verified_mappings"][0]["values"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + builder.canonical_json_sha256_v1(material)
    monkeypatch.setattr(
        builder,
        "build_live_annual_2025_interest_rate_risk_8bank_codex_verified_mapping_v1",
        lambda: live,
    )
    with pytest.raises(Exception, match="replay exactly"):
        builder.validate_annual_2025_interest_rate_risk_8bank_codex_verified_mapping_replay_v1(
            forged
        )
