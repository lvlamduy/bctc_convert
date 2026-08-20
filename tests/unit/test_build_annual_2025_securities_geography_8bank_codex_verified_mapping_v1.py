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
    ROOT / "scripts/experiments/"
    "build_annual_2025_securities_geography_8bank_codex_verified_mapping_v1.py"
)
SPEC = importlib.util.spec_from_file_location("annual_2025_securities_geography_test", PATH)
assert SPEC is not None and SPEC.loader is not None
builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = builder
SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def live() -> dict:
    return builder.build_live_annual_2025_securities_geography_8bank_codex_verified_mapping_v1()


def _trial(result: dict, code: str) -> dict:
    return next(item for item in result["trials"] if item["document_provenance"] == code)


def _mapping(trial: dict, role: str) -> dict:
    return next(item for item in trial["verified_mappings"] if item["semantic_role"] == role)


def _numbers(mapping: dict) -> list[int]:
    return [item["normalized_value"] for item in mapping["values"]]


def test_whole_pdf_scan_finds_six_unique_regions_and_two_absences(live: dict) -> None:
    assert live["metrics"] == {
        "accounting_equation_verified_count": 15,
        "bounded_report_absence_document_count": 2,
        "dash_cell_verified_as_zero_count": 5,
        "document_count": 8,
        "document_unique_region_count": 6,
        "mapping_verified_count": 12,
        "verified_value_cell_count": 18,
    }
    assert [item["document_provenance"] for item in live["trials"]] == list(
        builder.EXPECTED_DOCUMENT_ORDER
    )
    assert {
        item["document_provenance"]: item["scan"]["candidate_page_groups"]
        for item in live["trials"]
    } == {
        "ACB": [[77]],
        "MBB": [[91]],
        "VPB": [[81]],
        "HDB": [[60]],
        "VCB": [],
        "CTG": [],
        "BID": [[63]],
        "VIB": [[59, 60]],
    }
    assert [_trial(live, code)["status"] for code in ("VCB", "CTG")] == [
        "NOT_OBSERVED_IN_BOUND_REPORT",
        "NOT_OBSERVED_IN_BOUND_REPORT",
    ]


def test_geographic_values_and_gross_owner_reconciliations_are_exact(live: dict) -> None:
    expected = {
        "ACB": ([150819498, 125119331], [64226, 0], 150883724),
        "MBB": ([230449032, 217995033], [51179, 57261], 230500211),
        "VPB": ([88595317], [0], 88595317),
        "HDB": ([77435184], [0], 77435184),
        "BID": ([313930664], [1765075], 315695739),
        "VIB": ([51149531, 50388192], [0, 0], 51149531),
    }
    for code, (domestic, foreign, current_total) in expected.items():
        trial = _trial(live, code)
        assert _numbers(_mapping(trial, "DOMESTIC")) == domestic
        assert _numbers(_mapping(trial, "FOREIGN")) == foreign
        owner = next(
            item
            for item in trial["verified_accounting_equations"]
            if item["name"] == "TRADING_PLUS_INVESTMENT_GROSS_EQUALS_GEOGRAPHIC_TOTAL"
        )
        assert owner["computed_total"] == current_total
        assert owner["status"] == "CORROBORATED_EXACT"


def test_dash_is_zero_only_with_explicit_pixel_geometry(live: dict) -> None:
    dash_values = [
        value
        for trial in live["trials"]
        for mapping in trial["verified_mappings"]
        for value in mapping["values"]
        if value["source_cell_status"] == "DASH"
    ]
    assert len(dash_values) == 5
    assert all(value["normalized_value"] == 0 for value in dash_values)
    assert all(value["pixel_transcription"] == "-" for value in dash_values)
    assert all(value["value_event"] is None for value in dash_values)
    assert all(
        isinstance(value["dash_pixel_bbox"], list) and len(value["dash_pixel_bbox"]) == 4
        for value in dash_values
    )
    assert live["authority"]["blank_cell_treated_as_zero"] is False


def test_mapping_is_bounded_to_family_rows_and_related_parties_are_excluded(
    live: dict,
) -> None:
    ids = {
        mapping["report_norm_id"]
        for trial in live["trials"]
        for mapping in trial["verified_mappings"]
    }
    assert ids == {5760, 5761}
    assert live["schema_family"]["report_norm_id"] == 5759
    assert live["authority"]["related_party_family_mapped"] is False
    assert "5750" not in json.dumps(live, ensure_ascii=False)


def test_segment_report_is_a_negative_control_not_a_mapping_candidate() -> None:
    document = {
        "pages": [
            {
                "physical_page": 1,
                "lines": [
                    {"vietocr_text": text}
                    for text in (
                        "Báo cáo bộ phận",
                        "Khu vực địa lý",
                        "Chứng khoán đầu tư",
                        "Trong nước",
                        "Nước ngoài",
                    )
                ],
            }
        ]
    }
    scan = builder._scan_document(document)
    assert scan["status"] == "BOUNDED_REPORT_ABSENCE"
    assert scan["candidate_page_groups"] == []
    assert scan["near_segment_negative_control_pages"] == [1]


def test_persisted_result_equals_live_rebuild(live: dict) -> None:
    assert (ROOT / builder.RESULT_PATH).read_bytes() == canonical_json_bytes_v1(live)


def test_coordinated_rehash_cannot_pass_public_replay(
    live: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    forged = copy.deepcopy(live)
    _mapping(_trial(forged, "ACB"), "DOMESTIC")["values"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_PREFIX + canonical_json_sha256_v1(material)
    monkeypatch.setattr(
        builder,
        "build_live_annual_2025_securities_geography_8bank_codex_verified_mapping_v1",
        lambda: live,
    )
    with pytest.raises(Exception, match="exact-replay"):
        builder.validate_annual_2025_securities_geography_8bank_codex_verified_mapping_replay_v1(
            forged
        )
