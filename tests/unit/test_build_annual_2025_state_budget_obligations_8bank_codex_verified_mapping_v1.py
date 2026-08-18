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
    / "scripts/experiments/build_annual_2025_state_budget_obligations_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_state_budget_obligations_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def result() -> dict[str, object]:
    built = (
        builder.build_live_annual_2025_state_budget_obligations_8bank_codex_verified_mapping_v1()
    )
    persisted = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())
    assert builder._base().same_typed_json_v1(built, persisted)
    return built


def _trial(result: dict[str, object], code: str) -> dict[str, object]:
    return next(item for item in result["trials"] if item["document_provenance"] == code)


def _mapping(trial: dict[str, object], role: str) -> dict[str, object]:
    return next(item for item in trial["verified_mappings"] if item["role"] == role)


def test_all_eight_documents_are_unique_and_fully_closed(result: dict[str, object]) -> None:
    assert result["result_id"] == builder.EXPECTED_RESULT_ID
    assert result["metrics"] == {
        "accounting_equation_verified_count": 35,
        "bound_report_detailed_note_absence_count": 0,
        "document_count": 8,
        "document_unique_region_count": 8,
        "mapping_verified_count": 35,
        "open_source_row_count": 0,
        "q1_source_period_caveat_document_count": 0,
        "verified_value_cell_count": 140,
        "visible_dash_zero_count": 1,
    }
    assert [trial["page_span"] for trial in result["trials"]] == [
        [73, 73],
        [68, 68],
        [64, 64],
        [47, 47],
        [65, 65],
        [62, 62],
        [52, 52],
        [52, 52],
    ]
    assert all(trial["status"] == "VERIFIED_BY_CODEX" for trial in result["trials"])


def test_hdb_numeric_challenger_corrects_text_ocr_and_authenticates_dash(
    result: dict[str, object],
) -> None:
    hdb = _trial(result, "HDB")
    vat_opening = _mapping(hdb, "VAT")["values"][0]
    assert vat_opening["normalized_value"] == 60_055
    assert vat_opening["fresh_vietocr_numeric_proposal"] == "80.055"
    assert vat_opening["fresh_vietocr_numeric_status"] == (
        "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
    )
    closing = _mapping(hdb, "OTHER_PAYABLE")["values"][3]
    assert closing["normalized_value"] == 0
    assert closing["pixel_transcription"] == "-"
    assert closing["source_numeric_challenger_status"] == (
        "VISIBLE_AUTHENTICATED_PIXEL_DASH_NOT_DETECTED_AS_SOURCE_LINE"
    )


def test_ctg_receivable_and_payable_branches_are_netted_by_authenticated_cells(
    result: dict[str, object],
) -> None:
    ctg = _trial(result, "CTG")
    total = _mapping(ctg, "FAMILY_TOTAL")
    assert [item["normalized_value"] for item in total["values"]] == [
        3_594_736,
        11_106_895,
        -10_063_706,
        4_637_925,
    ]
    assert all(
        item["aggregation"] == "SIGNED_SUM_OF_AUTHENTICATED_SOURCE_CELLS"
        and [component["coefficient"] for component in item["aggregate_components"]] == [1, -1]
        for item in total["values"]
    )
    assert total["topology"] == ("PAYABLE_BRANCH_MINUS_RECEIVABLE_BRANCH_SIGNED_NET_MOVEMENT")


def test_closing_subcolumns_are_not_confused_with_net_schema_value(
    result: dict[str, object],
) -> None:
    vcb = _trial(result, "VCB")
    assert [
        _mapping(vcb, role)["values"][3]["normalized_value"]
        for role in (
            "FAMILY_TOTAL",
            "VAT",
            "CORPORATE_INCOME_TAX",
            "OTHER_TAX",
        )
    ] == [2_683_376, -30_295, 2_469_848, 243_823]
    assert not any(trial["verified_source_only_rows"] for trial in result["trials"])
    assert result["schema_family"]["mapped_report_norm_ids"] == [
        1269,
        1270,
        1271,
        1272,
        1278,
        1279,
    ]


def test_public_replay_rejects_coordinated_signed_aggregate_tamper(
    result: dict[str, object],
) -> None:
    forged = copy.deepcopy(result)
    value = _mapping(_trial(forged, "CTG"), "FAMILY_TOTAL")["values"][0]
    value["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + builder._base().canonical_json_sha256_v1(
        material
    )
    with pytest.raises(
        builder.Annual2025StateBudgetObligations8BankError,
        match="State-budget result ID drifted",
    ):
        builder.validate_annual_2025_state_budget_obligations_8bank_codex_verified_mapping_replay_v1(
            forged
        )
