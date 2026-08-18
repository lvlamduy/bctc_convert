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
    / "scripts/experiments/build_annual_2025_customer_collateral_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_customer_collateral_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def result() -> dict[str, object]:
    built = builder.build_live_annual_2025_customer_collateral_8bank_codex_verified_mapping_v1()
    persisted = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())
    assert builder._base().same_typed_json_v1(built, persisted)
    return built


def _trial(result: dict[str, object], code: str) -> dict[str, object]:
    return next(item for item in result["trials"] if item["document_provenance"] == code)


def _mapping(trial: dict[str, object], role: str) -> dict[str, object]:
    return next(item for item in trial["verified_mappings"] if item["role"] == role)


def test_four_unique_regions_four_absences_and_complete_schema_union(
    result: dict[str, object],
) -> None:
    assert result["result_id"] == builder.EXPECTED_RESULT_ID
    assert result["metrics"] == {
        "accounting_equation_verified_count": 10,
        "bound_report_detailed_note_absence_count": 4,
        "document_count": 8,
        "document_unique_region_count": 4,
        "mapping_verified_count": 25,
        "open_source_row_count": 0,
        "q1_source_period_caveat_document_count": 0,
        "verified_value_cell_count": 50,
    }
    assert [trial["page_span"] for trial in result["trials"]] == [
        [74, 74],
        None,
        [74, 74],
        [54, 54],
        None,
        None,
        None,
        [54, 54],
    ]
    assert result["schema_family"]["mapped_report_norm_ids"] == list(range(1280, 1289))


def test_acb_nested_enterprise_paper_detail_is_not_double_counted(
    result: dict[str, object],
) -> None:
    acb = _trial(result, "ACB")
    detail = _mapping(acb, "VALUABLE_PAPERS_ENTERPRISE_ISSUER_DETAIL")
    assert detail["family_total_contribution"] == "NON_ADDITIVE_NESTED_DETAIL"
    assert detail["equality_parent_role"] == "VALUABLE_PAPERS"
    assert [item["addend_count"] for item in acb["verified_accounting_equations"][:2]] == [5, 5]
    assert [item["name"] for item in acb["verified_accounting_equations"][2:]] == [
        "VISIBLE_NESTED_DETAIL_EQUALS_VISIBLE_PARENT",
        "VISIBLE_NESTED_DETAIL_EQUALS_VISIBLE_PARENT",
    ]


def test_hdb_relative_period_variant_uses_numeric_challenger_for_dropped_digit(
    result: dict[str, object],
) -> None:
    hdb = _trial(result, "HDB")
    comparative = _mapping(hdb, "REAL_ESTATE")["values"][1]
    assert comparative["fresh_vietocr_numeric_proposal"] == "368.639.341"
    assert comparative["source_numeric_challenger"] == "388.639.341"
    assert comparative["normalized_value"] == 388_639_341
    assert comparative["fresh_vietocr_numeric_status"] == (
        "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
    )
    assert _mapping(hdb, "FAMILY_TOTAL")["values"][1]["normalized_value"] == 706_190_899


def test_vib_other_leaf_is_one_controlled_sum_and_closes_the_parent(
    result: dict[str, object],
) -> None:
    vib = _trial(result, "VIB")
    other = _mapping(vib, "OTHER_COLLATERAL")
    assert [item["normalized_value"] for item in other["values"]] == [153_501_606, 89_360_520]
    assert all(
        item["source_numeric_challenger_status"]
        == "CONTROLLED_SUM_OF_AUTHENTICATED_SOURCE_NUMERIC_LINES"
        and len(item["component_evidence"]) == 4
        for item in other["values"]
    )
    assert all(
        equation["computed_value"] == equation["visible_value"]
        for equation in vib["verified_accounting_equations"]
    )


def test_mbb_vcb_ctg_bid_are_bounded_detailed_note_absences(
    result: dict[str, object],
) -> None:
    for code in ("MBB", "VCB", "CTG", "BID"):
        trial = _trial(result, code)
        assert trial["status"] == "CONFIRMED_DETAILED_NOTE_NOT_PRESENT_IN_BOUND_REPORT"
        assert trial["absence_evidence"]["complete_pdf_pages_scanned"] is True
        assert trial["verified_mappings"] == []


def test_public_replay_rejects_coordinated_nested_double_count_tamper(
    result: dict[str, object],
) -> None:
    forged = copy.deepcopy(result)
    detail = _mapping(_trial(forged, "ACB"), "VALUABLE_PAPERS_ENTERPRISE_ISSUER_DETAIL")
    detail["family_total_contribution"] = "ADDITIVE"
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + builder._base().canonical_json_sha256_v1(
        material
    )
    with pytest.raises(
        builder.Annual2025CustomerCollateral8BankError,
        match="customer-collateral result ID drifted",
    ):
        builder.validate_annual_2025_customer_collateral_8bank_codex_verified_mapping_replay_v1(
            forged
        )
