from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

ROOT = Path(__file__).resolve().parents[2]
PATH = (
    ROOT
    / "scripts/experiments/build_annual_2025_interbank_funding_8bank_codex_verified_mapping_v1.py"
)
SPEC = importlib.util.spec_from_file_location("annual_2025_interbank_funding_mapping_test", PATH)
assert SPEC is not None and SPEC.loader is not None
builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = builder
SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def live() -> dict:
    return builder.build_live_annual_2025_interbank_funding_8bank_codex_verified_mapping_v1()


def _trial(result: dict, code: str) -> dict:
    return next(item for item in result["trials"] if item["document_provenance"] == code)


def _mapping(trial: dict, role: str) -> dict:
    return next(item for item in trial["verified_mappings"] if item["role"] == role)


def _numbers(mapping: dict) -> list[int]:
    return [item["normalized_value"] for item in mapping["values"]]


def test_all_eight_whole_pdfs_have_one_unique_liability_region(live: dict) -> None:
    assert live["metrics"] == {
        "accounting_equation_verified_count": 40,
        "document_count": 8,
        "document_unique_region_count": 8,
        "gemma4_bounded_numeric_conflict_rescue_count": 2,
        "mapping_verified_count": 95,
        "source_only_auxiliary_row_count": 2,
        "verified_value_cell_count": 190,
    }
    assert [item["document_provenance"] for item in live["trials"]] == list(
        builder.EXPECTED_DOCUMENT_ORDER
    )
    assert [
        (item["evidence_page_sequence_start"], item["evidence_page_sequence_stop"])
        for item in live["trials"]
    ] == [(61, 61), (64, 64), (58, 59), (44, 44), (52, 52), (51, 51), (50, 50), (45, 45)]


def test_liability_family_never_maps_to_asset_root_575(live: dict) -> None:
    ids = {
        mapping["schema_binding"]["report_norm_id"]
        for trial in live["trials"]
        for mapping in trial["verified_mappings"]
    }
    assert 575 not in ids
    assert 1040 in ids
    assert ids <= set(range(1040, 1053))
    assert live["authority"]["asset_side_root_575_used_for_mapping"] is False


def test_vpb_continuation_and_hdb_intermediate_branches_close(live: dict) -> None:
    vpb = _trial(live, "VPB")
    assert (vpb["evidence_page_sequence_start"], vpb["evidence_page_sequence_stop"]) == (58, 59)
    assert _numbers(_mapping(vpb, "BORROWING")) == [154420742, 89893212]
    assert [item["role"] for item in vpb["verified_source_only_rows"]] == ["IFC_BORROWING_DETAIL"]

    hdb = _trial(live, "HDB")
    assert _numbers(_mapping(hdb, "BORROWING_VND")) == [2710113, 4323932]
    assert _numbers(_mapping(hdb, "BORROWING_FOREIGN")) == [37088405, 20259601]
    assert _numbers(_mapping(hdb, "BORROWING")) == [39798518, 24583533]
    assert [item["role"] for item in hdb["verified_source_only_rows"]] == ["UPAS_LC_PAYABLE"]


def test_two_hdb_vietocr_digit_errors_are_bounded_not_silently_repaired(live: dict) -> None:
    hdb = _trial(live, "HDB")
    rescues = {}

    def walk(value: object) -> None:
        if isinstance(value, dict):
            rescue = value.get("gemma4_text_rescue")
            if isinstance(rescue, dict):
                rescues[rescue["crop_sha256"]] = rescue
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(hdb)
    assert set(rescues) == {
        "7f6bf47dc6a06cecfe5a6f94f30f8405de9a9f70e5c92b0d3491d5f1319142df",
        "990bc12154e28504bb18907fa3704aba1f9618516273b3ebd61d9b7d4d8ff032",
    }
    assert {item["gemma4_text"] for item in rescues.values()} == {"6.980.904", "5.816.757"}
    assert live["authority"]["gemma4_used_as_numeric_truth"] is False


def test_asset_side_cho_vay_surface_is_a_negative_control() -> None:
    index = json.loads((ROOT / builder.SEMANTIC_INDEX_PATH).read_text())
    document = copy.deepcopy(
        next(item for item in index["documents"] if item["bank_code"] == "ACB")
    )
    page = next(item for item in document["pages"] if item["physical_page"] == 61)
    for line in page["lines"]:
        if line["source_line_index"] in {5, 49}:
            line["vietocr_text"] = (
                line["vietocr_text"].replace("VAY", "CHO VAY").replace("vay", "cho vay")
            )
    scan = builder._scanner().build_annual_2025_interbank_funding_document_scan_v1(document)
    assert scan["uniqueness"] == "NO_COMPLETE_REGION"
    assert scan["metrics"]["complete_region_count"] == 0


def test_persisted_result_and_review_equal_live_rebuild(live: dict) -> None:
    assert (ROOT / builder.RESULT_PATH).read_bytes() == canonical_json_bytes_v1(live) + b"\n"
    assert (ROOT / builder.REVIEW_PATH).read_bytes() == (
        canonical_json_bytes_v1(builder._review(live)) + b"\n"
    )


def test_coordinated_rehash_cannot_pass_public_replay(
    live: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    forged = copy.deepcopy(live)
    _mapping(_trial(forged, "ACB"), "BORROWING")["values"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + canonical_json_sha256_v1(material)
    monkeypatch.setattr(
        builder,
        "build_live_annual_2025_interbank_funding_8bank_codex_verified_mapping_v1",
        lambda: live,
    )
    with pytest.raises(Exception, match="replay exactly"):
        builder.validate_annual_2025_interbank_funding_8bank_codex_verified_mapping_replay_v1(
            forged
        )
