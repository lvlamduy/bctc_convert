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
    / "scripts/experiments/build_derivative_financial_instruments_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_derivative_financial_instruments_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
mapping = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = mapping
_SPEC.loader.exec_module(mapping)


def test_fixed_review_covers_five_layouts_seven_unique_regions_and_only_schema_lanes() -> None:
    review = mapping._review_blueprint()
    positive = [document for document in review["documents"] if document["mappings"]]
    negative = [document for document in review["documents"] if not document["mappings"]]

    assert [document["bank_code"] for document in positive] == [
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "CTG",
        "BID",
        "VIB",
    ]
    assert [document["bank_code"] for document in negative] == ["VCB"]
    assert {document["layout_mode"] for document in positive} == {
        "ASSET_LIABILITY",
        "ASSET_LIABILITY_NET",
        "CONTRACT_ASSET_LIABILITY",
        "CONTRACT_INFLOW_OUTFLOW_NET",
        "CONTRACT_NET",
    }
    assert sum(len(document["mappings"]) for document in positive) == 86
    assert all(
        row["lane_role"] in {"CONTRACT_VALUE", "ASSET_CARRYING_VALUE", "LIABILITY_CARRYING_VALUE"}
        for document in positive
        for row in document["mappings"]
    )


def test_persisted_result_locks_schema_equations_and_independent_numeric_corrections() -> None:
    persisted = mapping._validate_result(
        json.loads((mapping.PROJECT_ROOT / mapping.RESULT_PATH).read_text())
    )

    assert persisted["metrics"] == {
        "accounting_equation_verified_count": 30,
        "document_count": 8,
        "document_unique_region_count": 7,
        "fresh_vietocr_numeric_disagreement_corrected_by_pixel_source_count": 2,
        "mapping_verified_count": 86,
        "q1_source_period_caveat_document_count": 1,
        "unresolved_document_count": 1,
    }
    assert all(
        equation["computed_total"] == equation["visible_total"]
        for trial in persisted["trials"]
        for equation in trial["verified_accounting_equations"]
    )
    mismatches = [
        (
            trial["document_provenance"],
            row["source_value"]["fresh_vietocr_numeric_proposal"],
            row["source_value"]["pixel_transcription"],
        )
        for trial in persisted["trials"]
        for row in trial["verified_mappings"]
        if row["source_value"]["fresh_vietocr_numeric_proposal"] is not None
        and row["source_value"]["fresh_vietocr_numeric_proposal"]
        != row["source_value"]["pixel_transcription"]
    ]
    assert mismatches == [
        ("BID", "6,270,0ss", "6,270,055"),
        ("VIB", "2.126.217", "12.126.217"),
    ]
    hdb = next(trial for trial in persisted["trials"] if trial["document_provenance"] == "HDB")
    dash_rows = [
        row
        for row in hdb["verified_mappings"]
        if row["source_value"].get("source_cell_status") == "DASH"
    ]
    assert len(dash_rows) == 11
    assert all(row["normalized_value"] == 0 for row in dash_rows)
    assert all(row["source_value"]["pixel_binding"] is not None for row in dash_rows)
    mapped_ids = {
        row["report_norm_id"] for trial in persisted["trials"] for row in trial["verified_mappings"]
    }
    assert mapped_ids <= set(range(631, 716))
    assert 634 in mapped_ids and 714 in mapped_ids


def test_review_tamper_bool_poison_and_coordinated_result_rehash_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forged_review = mapping._review_blueprint()
    forged_review["documents"][0]["mappings"][0]["pixel_value"] = "7.897.726"
    with pytest.raises(
        mapping.DerivativeFinancialInstruments8BankCodexVerifiedMappingV1Error,
        match="differs from fixed ledger",
    ):
        mapping._review(forged_review)

    persisted = json.loads((mapping.PROJECT_ROOT / mapping.RESULT_PATH).read_text())
    poisoned = copy.deepcopy(persisted)
    poisoned["authority"]["contract_asset_and_liability_schema_axes_only"] = 1
    with pytest.raises(
        mapping.DerivativeFinancialInstruments8BankCodexVerifiedMappingV1Error,
        match="identity or metrics",
    ):
        mapping._validate_result(poisoned)

    forged = copy.deepcopy(persisted)
    forged["trials"][0]["verified_mappings"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "dfi8bcv1:result:" + mapping.canonical_json_sha256_v1(material)
    monkeypatch.setattr(
        mapping.scanner,
        "validate_derivative_financial_instruments_full_document_scan_replay_v1",
        lambda *_: None,
    )
    monkeypatch.setattr(
        mapping,
        "build_derivative_financial_instruments_8bank_codex_verified_mapping_v1",
        lambda *args, **kwargs: persisted,
    )
    with pytest.raises(
        mapping.DerivativeFinancialInstruments8BankCodexVerifiedMappingV1Error,
        match="replay exactly",
    ):
        mapping.validate_derivative_financial_instruments_8bank_codex_verified_mapping_replay_v1(
            forged,
            {},
            {},
            {},
            {},
            {},
            {},
            crop_manifest_sha256="a" * 64,
            review_sha256="b" * 64,
        )


def test_annual_2025_review_covers_seven_unique_regions_four_lane_headers_and_dashes() -> None:
    review = mapping._annual_2025_review_blueprint()
    positive = [document for document in review["documents"] if document["mappings"]]
    negative = [document for document in review["documents"] if not document["mappings"]]

    assert [document["bank_code"] for document in positive] == [
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "CTG",
        "BID",
        "VIB",
    ]
    assert [document["bank_code"] for document in negative] == ["VCB"]
    assert negative[0]["whole_document_family_absence_claim"] is True
    assert {document["layout_mode"] for document in positive} == {
        "ASSET_LIABILITY_NET",
        "CONTRACT_ASSET_LIABILITY",
        "CONTRACT_ASSET_LIABILITY_NET",
        "CONTRACT_INFLOW_OUTFLOW_NET",
        "CONTRACT_NET",
    }
    rows = [row for document in positive for row in document["mappings"]]
    assert len(rows) == 100
    assert sum(row["value_line_index"] is None for row in rows) == 24
    assert all(
        row["lane_role"] in {"CONTRACT_VALUE", "ASSET_CARRYING_VALUE", "LIABILITY_CARRYING_VALUE"}
        for row in rows
    )


def test_annual_2025_persisted_result_closes_equations_and_corrects_mbb_digit() -> None:
    persisted = mapping._validate_annual_2025_result(
        json.loads((mapping.PROJECT_ROOT / mapping.ANNUAL_2025_RESULT_PATH).read_text())
    )

    assert persisted["metrics"] == {
        "accounting_equation_verified_count": 62,
        "authenticated_pixel_dash_zero_count": 24,
        "bound_report_absence_document_count": 1,
        "document_count": 8,
        "document_unique_region_count": 7,
        "fresh_vietocr_numeric_disagreement_corrected_by_pixel_source_count": 1,
        "mapping_verified_count": 100,
        "unresolved_document_count": 0,
    }
    mbb = next(trial for trial in persisted["trials"] if trial["document_provenance"] == "MBB")
    assert mbb["fresh_vietocr_numeric_disagreement_line_indices"] == [50]
    assert all(
        equation["computed_total"] == equation["visible_total"]
        for trial in persisted["trials"]
        for equation in trial["verified_accounting_equations"]
    )
    dash_rows = [
        row
        for trial in persisted["trials"]
        for row in trial["verified_mappings"]
        if row["source_value"]["source_numeric_challenger_status"].startswith(
            "VISIBLE_AUTHENTICATED_PIXEL_DASH"
        )
    ]
    assert len(dash_rows) == 24
    assert all(row["normalized_value"] == 0 for row in dash_rows)


def test_annual_2025_review_and_coordinated_result_tamper_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forged_review = mapping._annual_2025_review_blueprint()
    forged_review["documents"][0]["mappings"][0]["pixel_value"] = "3.646.094"
    with pytest.raises(
        mapping.DerivativeFinancialInstruments8BankCodexVerifiedMappingV1Error,
        match="differs from fixed ledger",
    ):
        mapping._annual_2025_review(forged_review)

    persisted = json.loads((mapping.PROJECT_ROOT / mapping.ANNUAL_2025_RESULT_PATH).read_text())
    forged = copy.deepcopy(persisted)
    forged["trials"][0]["verified_mappings"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "annual2025dfi8bcv1:result:" + mapping.canonical_json_sha256_v1(material)
    monkeypatch.setattr(
        mapping,
        "build_live_annual_2025_derivative_financial_instruments_8bank_codex_verified_mapping_v1",
        lambda: persisted,
    )
    with pytest.raises(
        mapping.DerivativeFinancialInstruments8BankCodexVerifiedMappingV1Error,
        match="does not replay exactly",
    ):
        mapping.validate_annual_2025_derivative_financial_instruments_8bank_codex_verified_mapping_replay_v1(
            forged
        )
