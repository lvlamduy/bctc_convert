from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import _authority_snapshot
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT / "scripts/experiments/"
    "build_annual_2025_provision_movement_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location("annual_2025_provision_builder_test", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def live() -> dict:
    return builder.build_live_annual_2025_provision_movement_8bank_codex_verified_mapping_v1()


def _trial(result: dict, bank: str) -> dict:
    return next(item for item in result["trials"] if item["document_provenance"] == bank)


def _lane(result: dict, bank: str, lane: str) -> dict:
    return next(
        item for item in _trial(result, bank)["verified_lane_mappings"] if item["lane"] == lane
    )


def _row(result: dict, bank: str, lane: str, role: str) -> dict:
    return next(item for item in _lane(result, bank, lane)["rows"] if item["role"] == role)


def test_annual_provision_result_verifies_all_eight_unique_regions(live: dict) -> None:
    assert live["metrics"] == {
        "accounting_equation_verified_count": 18,
        "annual_source_period_document_count": 8,
        "current_period_lane_parent_verified_count": 18,
        "current_period_role_mapping_verified_count": 79,
        "document_count": 8,
        "document_unique_region_count": 8,
        "visible_dash_verified_as_zero_count": 9,
    }
    assert [trial["document_provenance"] for trial in live["trials"]] == list(
        builder.EXPECTED_DOCUMENT_ORDER
    )
    assert [trial["verified_lane_mappings"][0]["physical_page"] for trial in live["trials"]] == [
        51,
        53,
        48,
        38,
        41,
        44,
        43,
        39,
    ]
    assert all(
        trial["source_period_status"] == "VERIFIED_SOURCE_PERIOD_ANNUAL_2025"
        for trial in live["trials"]
    )


def test_margin_provision_is_a_separate_schema_lane_for_acb_and_vpb(live: dict) -> None:
    for bank in ("ACB", "VPB"):
        lane = _lane(live, bank, "MARGIN_ADVANCE")
        assert lane["parent_mapping"]["report_norm_id"] == 6061
        assert [row["report_norm_id"] for row in lane["rows"]] == [6062, 6063, 6064, 6065]
        assert lane["accounting_check"]["status"] == "CORROBORATED_EXACT"


def test_all_nine_visible_dashes_remain_typed_before_zero_normalization(live: dict) -> None:
    rows = [
        row
        for trial in live["trials"]
        for lane in trial["verified_lane_mappings"]
        for row in lane["rows"]
        if row["pixel_value_transcription"] == "-"
    ]
    assert len(rows) == 9
    assert all(row["normalized_value"] == 0 and row["pixel_binding"] is not None for row in rows)


def test_mbb_transformer_digit_error_is_overruled_by_pixels_and_ppocrv6(live: dict) -> None:
    row = _row(live, "MBB", "GENERAL", "FX")
    assert row["pixel_value_transcription"] == "2.478"
    assert row["normalized_value"] == 2478
    assert row["source_numeric_challenger"] == {
        "raw_text": "2.478",
        "source_line_index": 49,
        "status": "UPSTREAM_NUMERIC_CHALLENGER_MATCHED_VISIBLE_PIXEL",
    }
    semantic = next(
        item
        for item in _trial(live, "MBB")["transformer_semantic_evidence"]
        if item["lane"] == "GENERAL" and item["role"] == "FX"
    )
    assert "2.476" in semantic["structural_event_vietocr_label"]


def test_every_mapped_lane_closes_exactly(live: dict) -> None:
    for trial in live["trials"]:
        for lane in trial["verified_lane_mappings"]:
            rows = {row["role"]: row["normalized_value"] for row in lane["rows"]}
            computed = rows["OPENING"] + sum(
                value for role, value in rows.items() if role not in {"OPENING", "CLOSING"}
            )
            assert computed == rows["CLOSING"]
            assert lane["accounting_check"] == {
                "computed_closing": computed,
                "printed_closing": rows["CLOSING"],
                "status": "CORROBORATED_EXACT",
            }


def test_provider_numeric_tamper_fails_before_mapping() -> None:
    base, semantic, manifest, scan, review = builder._live_core(include_review=True)
    forged = copy.deepcopy(review)
    mbb = next(item for item in forged["documents"] if item["document_provenance"] == "MBB")
    general = next(item for item in mbb["series"] if item["lane"] == "GENERAL")
    fx = next(item for item in general["rows"] if item["role"] == "FX")
    fx["pixel_value_transcription"] = "2.476"
    base._review_blueprint = lambda: copy.deepcopy(forged)
    schema_authority, schema_by_id = _authority_snapshot(builder.PROJECT_ROOT)
    with pytest.raises(base.ProvisionMovement8BankCodexVerifiedMappingV1Error, match="disagree"):
        base.build_provision_movement_8bank_codex_verified_mapping_v1(
            semantic,
            manifest,
            scan,
            forged,
            schema_authority,
            schema_by_id,
            crop_manifest_sha256=builder.EXPECTED_CROP_MANIFEST_SHA256,
            review_sha256=builder.EXPECTED_REVIEW_SHA256,
        )


def test_coordinated_result_rehash_cannot_replace_live_replay(live: dict) -> None:
    forged = copy.deepcopy(live)
    forged["trials"][0]["verified_lane_mappings"][0]["rows"][0]["independent_pixel_label"] = (
        "forged"
    )
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + canonical_json_sha256_v1(material)
    with pytest.raises(builder.Annual2025ProvisionMovement8BankError, match="replay exactly"):
        builder.validate_annual_2025_provision_movement_8bank_codex_verified_mapping_replay_v1(
            forged
        )


def test_persisted_review_and_result_equal_live_bytes(live: dict) -> None:
    base = builder._base()
    review = builder.build_annual_2025_provision_movement_pixel_review_blueprint_v1(base)
    assert (_ROOT / builder.REVIEW_PATH).read_bytes() == canonical_json_bytes_v1(review)
    assert (_ROOT / builder.RESULT_PATH).read_bytes() == canonical_json_bytes_v1(live)
