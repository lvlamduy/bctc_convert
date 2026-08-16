from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    PROJECT_ROOT
    / "scripts/experiments/build_annual_2025_loan_quality_8bank_codex_verified_mapping_v1.py"
)
REVIEW = (
    PROJECT_ROOT
    / "docs/experiments/E-0114-annual-2025-loan-quality-8bank-codex-pixel-review-v1.json"
)
RESULT = (
    PROJECT_ROOT
    / "docs/experiments/E-0114-annual-2025-loan-quality-8bank-codex-verified-mapping-v1.json"
)


def _module():
    spec = importlib.util.spec_from_file_location("annual_2025_quality_mapping_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _rehash(value: dict) -> None:
    material = copy.deepcopy(value)
    material.pop("result_id")
    value["result_id"] = "annual2025lq8bcv1:result:" + canonical_json_sha256_v1(material)


def test_annual_review_and_result_finish_all_eight_quality_tables() -> None:
    module = _module()
    review = module._review(_json(REVIEW))
    result = module._validate_result(_json(RESULT))

    assert [bank["physical_page"] for bank in review["banks"]] == [
        50,
        51,
        45,
        36,
        39,
        43,
        42,
        66,
    ]
    assert result["metrics"] == {
        "accounting_equation_count": 16,
        "document_count": 8,
        "document_unique_structure_count": 8,
        "mapped_item_verified_by_codex_count": 43,
        "mapped_money_value_cell_count": 86,
        "mapped_percentage_corroboration_cell_count": 10,
        "negative_family_control_count": 16,
        "source_only_total_verified_count": 8,
        "standalone_margin_mapping_count": 3,
        "transformer_disagreement_preserved_count": 14,
        "unresolved_mapping_count": 0,
    }
    assert all(trial["status"] == "SCHEMA_MAPPING_VERIFIED_BY_CODEX" for trial in result["trials"])
    assert [
        trial["document_provenance"]
        for trial in result["trials"]
        if any(mapping["report_norm_id"] == 1944 for mapping in trial["verified_mappings"])
    ] == ["ACB", "MBB", "VPB"]


def test_annual_hdb_and_vib_variants_keep_their_true_population_boundaries() -> None:
    result = _module()._validate_result(_json(RESULT))
    hdb = result["trials"][3]
    vib = result["trials"][7]

    assert hdb["source_only_total"]["values"][1]["independent_pixel_transcription"] == (
        "431.306.069"
    )
    assert hdb["excluded_adjacent_population"] == {
        "pixel_label": (
            "Nghiệp vụ phát hành thư tín dụng trả chậm phát sinh trước ngày 01 tháng 7 năm 2024"
        ),
        "reason": ("SEPARATE_ADJACENT_CREDIT_POPULATION_OUTSIDE_CUSTOMER_LOAN_FIVE_GRADE_CORE"),
        "visible_values": ["-", "11.178.772"],
    }
    assert vib["layout_mode"] == "STACKED_PERIOD_BLOCKS_MULTI_ASSET_COLUMNS"
    assert [
        mapping["money_values"][0]["independent_pixel_transcription"]
        for mapping in vib["verified_mappings"]
    ] == ["361.491.090", "9.146.241", "2.149.202", "2.824.185", "6.361.298"]
    assert vib["source_only_total"]["values"][0]["independent_pixel_transcription"] == (
        "381.972.016"
    )


def test_annual_bid_percentage_lanes_are_corroboration_not_mapping_rows() -> None:
    result = _module()._validate_result(_json(RESULT))
    bid = result["trials"][6]

    assert len(bid["percentage_equations"]) == 2
    assert [item["computed_total"] for item in bid["percentage_equations"]] == [
        "100.00",
        "100.00",
    ]
    assert all(
        len(mapping["percentage_corroboration"]) == 2 for mapping in bid["verified_mappings"]
    )


def test_annual_review_and_coordinated_result_tamper_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    review = _json(REVIEW)
    review["banks"][3]["source_only_total"][1] = "442.484.841"
    with pytest.raises(
        module.Annual2025LoanQuality8BankCodexVerifiedMappingV1Error,
        match="fixed pixel ledger",
    ):
        module._review(review)

    exact = module._validate_result(_json(RESULT))
    monkeypatch.setattr(
        module,
        "build_live_annual_2025_loan_quality_8bank_codex_verified_mapping_v1",
        lambda: exact,
    )
    tampered = copy.deepcopy(exact)
    tampered["trials"][0]["verified_mappings"][0]["money_values"][0][
        "independent_pixel_transcription"
    ] = "660.272.035"
    _rehash(tampered)
    with pytest.raises(
        module.Annual2025LoanQuality8BankCodexVerifiedMappingV1Error,
        match="does not replay exactly",
    ):
        module.validate_annual_2025_loan_quality_8bank_codex_verified_mapping_replay_v1(tampered)


def test_annual_persisted_result_exactly_replays_all_live_inputs() -> None:
    module = _module()
    persisted = _json(RESULT)

    assert (
        module.validate_annual_2025_loan_quality_8bank_codex_verified_mapping_replay_v1(persisted)
        == persisted
    )
