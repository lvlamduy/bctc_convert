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
    "build_annual_2025_investment_securities_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location("annual_2025_investment_builder_test", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def live() -> dict:
    return builder.build_live_annual_2025_investment_securities_8bank_codex_verified_mapping_v1()


def _trial(result: dict, bank: str) -> dict:
    return next(item for item in result["trials"] if item["bank_provenance"] == bank)


def test_annual_investment_maps_all_eight_unique_regions(live: dict) -> None:
    assert live["metrics"] == {
        "accounting_equation_verified_count": 72,
        "dash_cell_verified_as_zero_count": 18,
        "document_count": 8,
        "document_unresolved_count": 0,
        "document_verified_count": 8,
        "mapped_value_cell_count": 220,
        "mapping_verified_count": 110,
        "unresolved_mapping_count": 2,
    }
    assert [(trial["bank_provenance"], trial["status"]) for trial in live["trials"]] == [
        (code, "VERIFIED_BY_CODEX") for code in builder.EXPECTED_DOCUMENT_ORDER
    ]


def test_only_two_unsplittable_source_groups_remain_explicit(live: dict) -> None:
    unresolved = [
        (trial["bank_provenance"], item["source_label"], item["reason"])
        for trial in live["trials"]
        for item in trial["unresolved_items"]
    ]
    assert unresolved == [
        (
            "MBB",
            "Trái phiếu Chính phủ và trái phiếu Chính phủ bảo lãnh",
            "COMBINED_GOVERNMENT_AND_GOVERNMENT_GUARANTEED_ROW_HAS_NO_PRINTED_SPLIT",
        ),
        (
            "HDB",
            "Tín phiếu NHNN + Chứng khoán Chính phủ",
            "NHNN_BILL_AND_GOVERNMENT_BOND_REQUIRE_CONTROLLED_AGGREGATION_INTO_REPORT_NORM_ID_831",
        ),
    ]


def test_vib_tctd_components_are_controlled_aggregate_808(live: dict) -> None:
    vib = _trial(live, "VIB")
    mapping = next(item for item in vib["verified_mappings"] if item["report_norm_id"] == 808)
    assert mapping["aggregation"] == "SUM_OF_TCTD_BOND_AND_CERTIFICATE_ROWS_PER_PERIOD"
    assert [item["normalized_value"] for item in mapping["source_values"]] == [
        40_356_524,
        39_862_333,
    ]
    assert all(
        len(item["component_source_values"]) == 2
        and all(
            component["primary_numeric_challenger"]["status"]
            == "PPOCRV6_NUMERIC_CHALLENGER_MATCHED_VISIBLE_PIXEL"
            for component in item["component_source_values"]
        )
        for item in mapping["source_values"]
    )


def test_all_direct_numbers_use_ppocrv6_and_dashes_stay_typed(live: dict) -> None:
    direct_values = [
        value
        for trial in live["trials"]
        for mapping in trial["verified_mappings"]
        if mapping.get("aggregation") is None
        for value in mapping["source_values"]
    ]
    assert sum(value["source_cell_status"] == "DASH" for value in direct_values) == 18
    assert all(
        value["normalized_value"] == 0
        and value["primary_numeric_challenger"]["status"]
        == "VISIBLE_PIXEL_DASH_WITH_NO_PROVIDER_TEXT_LINE"
        for value in direct_values
        if value["source_cell_status"] == "DASH"
    )
    assert all(
        value["primary_numeric_challenger"]["status"]
        == "PPOCRV6_NUMERIC_CHALLENGER_MATCHED_VISIBLE_PIXEL"
        for value in direct_values
        if value["source_cell_status"] == "VALUE"
    )


def test_every_accounting_equation_closes(live: dict) -> None:
    for trial in live["trials"]:
        for equation in trial["verified_accounting_equations"]:
            assert sum(equation["addends"]) == equation["visible_total"]
            assert equation["computed_total"] == equation["visible_total"]


def test_pixel_number_tamper_is_rejected_by_ppocrv6() -> None:
    base = builder._base()
    semantic, manifest, scan, review, schema_authority, schema_by_id, manifest_sha, review_sha = (
        base._live_inputs()
    )
    forged = copy.deepcopy(review)
    vcb = next(item for item in forged["documents"] if item["bank_code"] == "VCB")
    government = next(
        row for page in vcb["pages"] for row in page["rows"] if row["role"] == "AFS_GOVERNMENT"
    )
    government["values"][0]["pixel_transcription"] = "60.984.051"
    base._review_blueprint = lambda: copy.deepcopy(forged)
    with pytest.raises(
        ValueError,
        match="visible pixel and PaddleOCR6 numeric challenger disagree",
    ):
        base.build_investment_securities_8bank_codex_verified_mapping_v1(
            semantic,
            manifest,
            scan,
            forged,
            schema_authority,
            schema_by_id,
            crop_manifest_sha256=manifest_sha,
            review_sha256=review_sha,
        )


def test_coordinated_result_rehash_cannot_replace_live_replay(live: dict) -> None:
    forged = copy.deepcopy(live)
    forged["trials"][4]["verified_mappings"][0]["source_values"][0][
        "independent_pixel_transcription"
    ] = "forged"
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + canonical_json_sha256_v1(material)
    with pytest.raises(Exception, match="replay exactly"):
        builder.validate_annual_2025_investment_securities_8bank_codex_verified_mapping_replay_v1(
            forged
        )


def test_persisted_review_and_result_equal_live_bytes(live: dict) -> None:
    assert (_ROOT / builder.REVIEW_PATH).read_bytes() == canonical_json_bytes_v1(
        builder.build_annual_2025_investment_securities_pixel_review_blueprint_v1()
    )
    assert (_ROOT / builder.RESULT_PATH).read_bytes() == canonical_json_bytes_v1(live)
