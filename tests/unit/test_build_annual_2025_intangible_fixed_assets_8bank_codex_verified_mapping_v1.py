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
    / "scripts/experiments/build_annual_2025_intangible_fixed_assets_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_intangible_fixed_assets_8bank_codex_verified_mapping_v1",
    _PATH,
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def live() -> dict[str, object]:
    return builder.build_live_annual_2025_intangible_fixed_assets_8bank_codex_verified_mapping_v1()


def test_all_eight_annual_regions_are_verified_without_open_rows(
    live: dict[str, object],
) -> None:
    assert live["metrics"] == {
        "accounting_equation_count": 32,
        "document_count": 8,
        "inline_disclosure_value_count": 3,
        "mapping_verified_count": 107,
        "open_review_item_count": 0,
        "rotated_semantic_rescue_line_count": 3338,
        "source_ppocrv6_numeric_match_count": 107,
        "verified_present_document_count": 8,
    }
    assert [(trial["document_provenance"], trial["page_sequence"]) for trial in live["trials"]] == [
        ("ACB", 56),
        ("MBB", 60),
        ("VPB", 54),
        ("HDB", 42),
        ("VCB", 49),
        ("CTG", 49),
        ("BID", 48),
        ("VIB", 43),
    ]
    assert all(
        trial["source_period"] == "2025-12-31"
        and trial["source_period_status"]
        == "VERIFIED_AUDITED_ANNUAL_2025_CURRENT_AND_2024_OPENING_PERIODS"
        for trial in live["trials"]
    )


def test_all_rollforwards_and_carrying_values_close_exactly(
    live: dict[str, object],
) -> None:
    equations = [equation for trial in live["trials"] for equation in trial["equations"]]
    assert len(equations) == 32
    assert all(equation["status"] == "CORROBORATED_EXACT" for equation in equations)
    assert all(equation["computed_total"] == equation["visible_total"] for equation in equations)


def test_ppocrv6_numeric_axis_catches_ctg_vietocr_digit_error(
    live: dict[str, object],
) -> None:
    ctg = next(trial for trial in live["trials"] if trial["document_provenance"] == "CTG")
    disposal = next(mapping for mapping in ctg["mappings"] if mapping["report_norm_id"] == 925)

    assert disposal["value"]["fresh_vietocr_proposal"] == "(65.998)"
    assert disposal["value"]["source_numeric_challenger"] == "(85.998)"
    assert disposal["value"]["normalized_value"] == -85_998
    assert disposal["value"]["source_numeric_challenger_status"] == (
        "MATCHED_VISIBLE_PIXEL_TRANSCRIPTION"
    )


def test_fully_amortized_disclosures_are_bound_for_every_bank(
    live: dict[str, object],
) -> None:
    disclosures = [
        (trial["document_provenance"], mapping["value"]["normalized_value"])
        for trial in live["trials"]
        for mapping in trial["mappings"]
        if mapping["report_norm_id"] == 6069
    ]

    assert disclosures == [
        ("ACB", 536_070),
        ("MBB", 2_667_798),
        ("VPB", 1_158_286),
        ("HDB", 351_964),
        ("VCB", 1_888_216),
        ("CTG", 2_295_278),
        ("BID", 1_760_913),
        ("VIB", 297_661),
    ]


def test_every_mapping_is_family_local_schema_bound(live: dict[str, object]) -> None:
    mappings = [mapping for trial in live["trials"] for mapping in trial["mappings"]]
    assert all(mapping["final_status"] == "VERIFIED_BY_CODEX" for mapping in mappings)
    assert all(
        mapping["schema_binding"]["report_norm_id"] == mapping["report_norm_id"]
        for mapping in mappings
    )
    assert live["input_refs"]["schema_authority"] == builder._SCHEMA_AUTHORITY


def test_exact_replay_rejects_coordinated_mapping_rehash(live: dict[str, object]) -> None:
    forged = copy.deepcopy(live)
    forged["trials"][0]["mappings"][0]["value"]["normalized_value"] += 1
    base = builder._configure_base()
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + base.canonical_json_sha256_v1(material)

    with pytest.raises(builder.Annual2025IntangibleFixedAssets8BankError):
        builder.validate_annual_2025_intangible_fixed_assets_8bank_codex_verified_mapping_replay_v1(
            forged
        )


def test_persisted_review_and_result_equal_live_bytes(live: dict[str, object]) -> None:
    persisted_review = json.loads((builder.PROJECT_ROOT / builder.REVIEW_PATH).read_text("utf-8"))
    persisted_result = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text("utf-8"))

    assert (
        persisted_review
        == builder.build_annual_2025_intangible_fixed_assets_pixel_review_blueprint_v1()
    )
    assert persisted_result == live
