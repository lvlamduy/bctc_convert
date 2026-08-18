from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT / "scripts/experiments/"
    "build_annual_2025_contingent_liabilities_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_contingent_liabilities_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def result() -> dict[str, object]:
    built = builder.build_live_annual_2025_contingent_liabilities_8bank_codex_verified_mapping_v1()
    persisted = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())
    assert builder._base().same_typed_json_v1(built, persisted)
    return built


def _trial(result: dict[str, object], code: str) -> dict[str, object]:
    return next(item for item in result["trials"] if item["document_provenance"] == code)


def test_seven_unique_regions_one_bounded_absence_and_complete_schema_union(
    result: dict[str, object],
) -> None:
    assert result["result_id"] == builder.EXPECTED_RESULT_ID
    assert result["metrics"] == {
        "accounting_equation_verified_count": 46,
        "bound_report_detailed_note_absence_count": 1,
        "document_count": 8,
        "document_unique_region_count": 7,
        "mapping_verified_count": 58,
        "open_source_row_count": 13,
        "q1_source_period_caveat_document_count": 0,
        "source_only_control_row_count": 15,
        "verified_value_cell_count": 114,
    }
    assert [trial["page_span"] for trial in result["trials"]] == [
        [75, 75],
        [79, 79],
        [75, 75],
        [55, 55],
        None,
        [63, 63],
        [59, 59],
        [55, 55],
    ]
    assert result["schema_family"]["mapped_report_norm_ids"] == [
        1294,
        1295,
        1296,
        1297,
        1298,
        1299,
        1300,
        1301,
        1302,
        1303,
        1304,
        5741,
        5742,
        5743,
        5744,
    ]


def test_hdb_relative_period_axes_and_two_group_margin_variant_close(
    result: dict[str, object],
) -> None:
    hdb = _trial(result, "HDB")
    assert hdb["status"] == "VERIFIED_BY_CODEX"
    assert hdb["mapped_report_norm_ids"] == [1294, 1295, 1296, 1300, 1301, 1304]
    assert {row["row_id"] for row in hdb["verified_source_only_rows"]} == {
        "CLA-001",
        "CLA-002",
        "CLA-003",
    }
    assert {item["name"] for item in hdb["verified_accounting_equations"]} == {
        "CONTINGENT_GROUP_EQUALS_THREE_CHILDREN",
        "COMMITMENT_GROUP_EQUALS_TWO_CHILDREN",
        "TWO_INTERMEDIATE_GROUPS_MINUS_MARGIN_EQUAL_FAMILY_TOTAL",
    }
    assert all(
        item["computed_value"] == item["visible_value"]
        for item in hdb["verified_accounting_equations"]
    )


def test_bid_group_parents_and_lc_children_are_not_double_counted(
    result: dict[str, object],
) -> None:
    bid = _trial(result, "BID")
    assert bid["mapped_report_norm_ids"] == [1294, 1295, 1296, 1300, 1304]
    assert {row["row_id"] for row in bid["verified_source_only_rows"]} == {
        "CLA-004",
        "CLA-005",
        "CLA-006",
    }
    assert {item["name"] for item in bid["verified_accounting_equations"]} == {
        "GUARANTEE_GROUP_EQUALS_TWO_CHILDREN",
        "SIGHT_PLUS_DEFERRED_LC_EQUAL_PAYMENT_COMMITMENT",
        "GUARANTEE_PLUS_PAYMENT_PLUS_OTHER_EQUAL_FAMILY_TOTAL",
    }


def test_acb_and_vpb_retain_all_open_source_rows(result: dict[str, object]) -> None:
    acb = _trial(result, "ACB")
    vpb = _trial(result, "VPB")
    assert [row["row_id"] for row in acb["verified_source_only_rows"]] == [
        "CL-001",
        "CL-002",
        "CL-003",
        "CL-004",
        "CL-005",
    ]
    assert [row["row_id"] for row in vpb["verified_source_only_rows"] if row["open_mapping"]] == [
        "CL-007",
        "CL-008",
        "CL-009",
        "CL-010",
        "CL-011",
        "CL-012",
        "CL-013",
        "CL-014",
    ]


def test_vcb_is_bounded_detailed_table_absence(result: dict[str, object]) -> None:
    vcb = _trial(result, "VCB")
    assert vcb["status"] == "CONFIRMED_DETAILED_NOTE_NOT_PRESENT_IN_BOUND_REPORT"
    assert vcb["absence_evidence"]["complete_pdf_pages_scanned"] is True
    assert vcb["absence_evidence"]["source_scope_absence_only"] is True
    assert vcb["verified_mappings"] == []


def test_vib_maps_net_axis_and_retains_gross_margin_controls(
    result: dict[str, object],
) -> None:
    vib = _trial(result, "VIB")
    assert vib["mapped_report_norm_ids"] == [
        1294,
        1295,
        1300,
        1301,
        1302,
        1304,
        5741,
        5742,
    ]
    assert all(not row["open_mapping"] for row in vib["verified_source_only_rows"])
    assert any(
        item["name"] == "FAMILY_GROSS_MINUS_MARGIN_EQUALS_FAMILY_NET"
        for item in vib["verified_accounting_equations"]
    )


def test_public_replay_rejects_coordinated_open_row_promotion(
    result: dict[str, object],
) -> None:
    forged = copy.deepcopy(result)
    acb = _trial(forged, "ACB")
    row = next(row for row in acb["verified_source_only_rows"] if row["open_mapping"])
    row["open_mapping"] = False
    row["status"] = "VERIFIED_SOURCE_ONLY_ACCOUNTING_CONTROL"
    forged["metrics"]["open_source_row_count"] -= 1
    forged["metrics"]["source_only_control_row_count"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + builder._base().canonical_json_sha256_v1(
        material
    )
    with pytest.raises(
        builder.Annual2025ContingentLiabilities8BankError,
        match="contingent-liabilities result ID drifted",
    ):
        builder.validate_annual_2025_contingent_liabilities_8bank_codex_verified_mapping_replay_v1(
            forged
        )
