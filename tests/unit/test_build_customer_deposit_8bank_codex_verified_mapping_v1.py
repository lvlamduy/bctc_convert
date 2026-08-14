from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = (
    _ROOT / "scripts/experiments/build_customer_deposit_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_customer_deposit_8bank_codex_verified_mapping_v1", _MODULE_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _persisted() -> dict[str, object]:
    return json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text("utf-8"))


def test_review_blueprint_preserves_boundaries_layouts_axes_and_q1_caveat() -> None:
    review = builder._review_blueprint()

    assert [item["document_provenance"] for item in review["documents"]] == list(
        builder.EXPECTED_DOCUMENT_ORDER
    )
    acb = review["documents"][0]
    assert acb["layout_variant"] == "PERIOD_STACKED_ROWS_X_CURRENCY_COLUMNS"
    assert acb["page_sequences"] == [21]
    assert acb["comparison_period_excluded"] == "31/12/2025"
    assert acb["selected_monetary_axis"].endswith("TOTAL_AND_PERCENT_COLUMNS_CHECK_ONLY")

    vpb = review["documents"][2]
    assert vpb["source_period"] == "2026-03-31"
    assert vpb["unresolved_items"][0]["source_label"].startswith("Công ty TNHH 2 thành viên")

    vib = review["documents"][7]
    assert vib["page_sequences"] == [41, 42]
    savings = next(item for item in vib["mappings"] if item["role"] == "SAVINGS")
    assert savings["additivity"] == "NONADDITIVE_SUBSET_OF_NO_TERM_AND_TERM"


def test_current_persisted_result_replays_all_eight_banks_exactly() -> None:
    result = builder.validate_customer_deposit_8bank_codex_verified_mapping_replay_v1(_persisted())

    assert result["metrics"] == {
        "accounting_equation_verified_count": 43,
        "document_count": 8,
        "document_unique_region_count": 8,
        "mapping_verified_count": 118,
        "q1_source_period_caveat_document_count": 1,
        "unresolved_source_item_count": 2,
    }
    assert [trial["status"] for trial in result["trials"]] == [
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX_WITH_SUPPLIED_SOURCE_PERIOD_CAVEAT",
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX",
    ]
    assert [trial["cluster_boundary"] for trial in result["trials"]] == [
        {
            "first_page_sequence": 21,
            "first_parent_role": "NO_TERM",
            "first_source_line_index": 13,
            "last_page_sequence": 21,
            "last_parent_role": "DEDICATED",
            "last_source_line_index": 67,
        },
        {
            "first_page_sequence": 43,
            "first_parent_role": "NO_TERM",
            "first_source_line_index": 6,
            "last_page_sequence": 43,
            "last_parent_role": "ESCROW",
            "last_source_line_index": 27,
        },
        {
            "first_page_sequence": 55,
            "first_parent_role": "NO_TERM",
            "first_source_line_index": 12,
            "last_page_sequence": 55,
            "last_parent_role": "ESCROW",
            "last_source_line_index": 45,
        },
        {
            "first_page_sequence": 31,
            "first_parent_role": "NO_TERM",
            "first_source_line_index": 33,
            "last_page_sequence": 31,
            "last_parent_role": "ESCROW",
            "last_source_line_index": 54,
        },
        {
            "first_page_sequence": 35,
            "first_parent_role": "NO_TERM",
            "first_source_line_index": 14,
            "last_page_sequence": 35,
            "last_parent_role": "ESCROW",
            "last_source_line_index": 35,
        },
        {
            "first_page_sequence": 42,
            "first_parent_role": "NO_TERM",
            "first_source_line_index": 9,
            "last_page_sequence": 42,
            "last_parent_role": "ESCROW",
            "last_source_line_index": 36,
        },
        {
            "first_page_sequence": 25,
            "first_parent_role": "NO_TERM",
            "first_source_line_index": 40,
            "last_page_sequence": 25,
            "last_parent_role": "ESCROW",
            "last_source_line_index": 67,
        },
        {
            "first_page_sequence": 41,
            "first_parent_role": "NO_TERM",
            "first_source_line_index": 12,
            "last_page_sequence": 42,
            "last_parent_role": "ESCROW",
            "last_source_line_index": 51,
        },
    ]
    assert all(
        trial["layout"]["row_order_preserved_from_pdf"] is True
        and trial["selected_axes"]["total_columns_used_as_checks_only"] is True
        and trial["selected_axes"]["percentage_axis_mapped_as_money"] is False
        for trial in result["trials"]
    )

    mbb = result["trials"][1]
    dedicated_vnd = next(
        item for item in mbb["verified_mappings"] if item["role"] == "DEDICATED_VND"
    )
    assert dedicated_vnd["report_norm_id"] == 1070
    assert dedicated_vnd["normalized_value"] == 1_707_241
    assert dedicated_vnd["aggregation"] == ("USER_DIRECTED_PARENT_VALUE_TO_VND_NO_SEPARATE_FX")
    assert {
        item["role"]: item["report_norm_id"]
        for item in mbb["verified_mappings"]
        if item["section"] == "CUSTOMER_TYPE"
    } == {"CUSTOMER_TCKT": 1084, "CUSTOMER_INDIVIDUAL": 1089}

    vib = result["trials"][7]
    state_company = next(
        item for item in vib["verified_mappings"] if item["role"] == "STATE_COMPANY"
    )
    assert state_company["normalized_value"] == 13_034_518
    assert state_company["source_values"][0]["fresh_vietocr_numeric_proposal"] == "3.034.518"
    assert state_company["source_values"][0]["source_numeric_challenger"] == "13.034.518"


def test_review_and_result_coordinated_rehashes_do_not_authenticate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    review = builder._review_blueprint()
    forged_review = copy.deepcopy(review)
    forged_review["documents"][0]["mappings"][0]["values"][0]["pixel_transcription"] = "999"
    review_material = copy.deepcopy(forged_review)
    review_material.pop("review_id")
    forged_review["review_id"] = "e0058:pixel-review:" + builder.canonical_json_sha256_v1(
        review_material
    )
    with pytest.raises(builder.CustomerDeposit8BankCodexVerifiedMappingV1Error, match="ledger"):
        builder._review(forged_review)

    persisted = _persisted()
    forged_result = copy.deepcopy(persisted)
    forged_result["trials"][0]["verified_mappings"][0]["normalized_value"] = 999
    result_material = copy.deepcopy(forged_result)
    result_material.pop("result_id")
    forged_result["result_id"] = "cd8bcv1:result:" + builder.canonical_json_sha256_v1(
        result_material
    )
    monkeypatch.setattr(
        builder,
        "build_live_customer_deposit_8bank_codex_verified_mapping_v1",
        _persisted,
    )
    with pytest.raises(builder.CustomerDeposit8BankCodexVerifiedMappingV1Error, match="replay"):
        builder.validate_customer_deposit_8bank_codex_verified_mapping_replay_v1(forged_result)


def test_money_and_typed_identity_fail_closed() -> None:
    assert builder._money("1.234.567") == 1_234_567
    with pytest.raises(builder.CustomerDeposit8BankCodexVerifiedMappingV1Error):
        builder._money("-")
    with pytest.raises(builder.CustomerDeposit8BankCodexVerifiedMappingV1Error):
        builder._money(123)
