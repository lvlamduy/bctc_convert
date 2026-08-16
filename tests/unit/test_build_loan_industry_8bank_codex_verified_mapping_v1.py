from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    PROJECT_ROOT / "scripts/experiments/build_loan_industry_8bank_codex_verified_mapping_v1.py"
)
REVIEW_PATH = (
    PROJECT_ROOT / "docs/experiments/E-0055-loan-industry-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = (
    PROJECT_ROOT / "docs/experiments/E-0055-loan-industry-8bank-codex-verified-mapping-v2.json"
)
ANNUAL_REVIEW_PATH = (
    PROJECT_ROOT
    / "docs/experiments/E-0113-annual-2025-loan-industry-8bank-codex-pixel-review-v1.json"
)
ANNUAL_RESULT_PATH = (
    PROJECT_ROOT
    / "docs/experiments/E-0113-annual-2025-loan-industry-8bank-codex-verified-mapping-v1.json"
)


def _module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "loan_industry_codex_mapping_v1_test", MODULE_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert type(value) is dict
    return value


def _rehash(
    module: ModuleType,
    value: dict[str, Any],
    prefix: str = "li8bcv2:result:",
) -> None:
    material = copy.deepcopy(value)
    material.pop("result_id")
    value["result_id"] = prefix + module.canonical_json_sha256_v1(material)


@pytest.fixture(scope="module")
def live() -> tuple[ModuleType, dict[str, Any]]:
    module = _module()
    return module, module._validate_result(_json(RESULT_PATH))


def test_live_result_is_exact_bounded_and_preserves_all_unresolved_rows(
    live: tuple[ModuleType, dict[str, Any]],
) -> None:
    module, result = live
    assert result["result_id"] == (
        "li8bcv2:result:3ac4ba987593baf8e0a03c3a1f2414dacf1008df38fc890519d72d2c9160cbdb"
    )
    assert result["metrics"] == {
        "document_count": 8,
        "document_no_complete_region_count": 3,
        "document_unique_structure_count": 5,
        "intermediate_source_only_total_verified_count": 1,
        "mapped_item_verified_by_codex_count": 80,
        "mapped_money_value_cell_count": 160,
        "mapped_percentage_corroboration_cell_count": 124,
        "negative_family_control_count": 32,
        "source_only_total_verified_count": 5,
        "transformer_disagreement_preserved_count": 16,
        "unresolved_schema_semantic_row_count": 0,
    }
    assert [trial["document_provenance"] for trial in result["trials"]] == list(
        module.EXPECTED_DOCUMENT_ORDER
    )
    assert [
        (
            trial["document_provenance"],
            trial["physical_page"],
            len(trial["verified_mappings"]),
            len(trial["unresolved_rows"]),
        )
        for trial in result["trials"]
    ] == [
        ("ACB", None, 0, 0),
        ("MBB", 33, 21, 0),
        ("VPB", 44, 22, 0),
        ("HDB", 27, 11, 0),
        ("VCB", None, 0, 0),
        ("CTG", None, 0, 0),
        ("BID", 22, 7, 0),
        ("VIB", 33, 19, 0),
    ]
    assert all(trial["whole_document_family_absence_claim"] is False for trial in result["trials"])


def test_project_owner_adjudicated_rows_bind_exact_live_schema_ids(
    live: tuple[ModuleType, dict[str, Any]],
) -> None:
    _, result = live
    adjudicated = {
        (
            trial["document_provenance"],
            row["role"],
            row["report_norm_id"],
        )
        for trial in result["trials"]
        for row in trial["verified_mappings"]
        if row["role"]
        in {
            "TRANSPORT_STORAGE",
            "PUBLIC_ADMIN_DEFENCE_SOCIAL_SECURITY",
            "PERSONAL_HOUSING_LOANS",
            "FOREIGN_BRANCH_LOANS",
            "BROAD_SERVICES",
        }
    }
    assert adjudicated == {
        ("MBB", "TRANSPORT_STORAGE", 736),
        ("MBB", "FOREIGN_BRANCH_LOANS", 6058),
        ("VPB", "TRANSPORT_STORAGE", 736),
        ("VPB", "PUBLIC_ADMIN_DEFENCE_SOCIAL_SECURITY", 745),
        ("VPB", "PERSONAL_HOUSING_LOANS", 6059),
        ("HDB", "TRANSPORT_STORAGE", 736),
        ("BID", "BROAD_SERVICES", 6060),
        ("VIB", "TRANSPORT_STORAGE", 736),
    }
    assert all(trial["unresolved_rows"] == [] for trial in result["trials"])


def test_visible_pixel_digits_override_bad_transformer_proposals_only_in_review(
    live: tuple[ModuleType, dict[str, Any]],
) -> None:
    _, result = live
    vib = next(trial for trial in result["trials"] if trial["document_provenance"] == "VIB")
    manufacturing = next(row for row in vib["verified_mappings"] if row["role"] == "MANUFACTURING")
    construction = next(row for row in vib["verified_mappings"] if row["role"] == "CONSTRUCTION")
    assert manufacturing["money_values"][1]["semantic_proposal"] == "9.457.078"
    assert manufacturing["money_values"][1]["independent_pixel_transcription"] == "19.457.078"
    assert construction["percentage_corroboration"][1]["semantic_proposal"] == ",72"
    assert construction["percentage_corroboration"][1]["independent_pixel_transcription"] == "1,72"


@pytest.mark.parametrize(
    "mutator",
    (
        lambda value: value["documents"][1].__setitem__("physical_page", True),
        lambda value: value["documents"][1].__setitem__("schema_unresolved_roles", []),
        lambda value: value["safety"].__setitem__("mapping_decided_by_text_similarity_alone", True),
    ),
)
def test_pixel_review_rejects_type_laundering_promotion_and_unsafe_authority(
    mutator: Any,
) -> None:
    module = _module()
    review = _json(REVIEW_PATH)
    mutator(review)
    with pytest.raises(module.LoanIndustry8BankCodexVerifiedMappingV1Error):
        module._review(review)


def test_coordinated_digit_and_status_rehash_fail_public_replay(
    live: tuple[ModuleType, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    module, exact = live
    monkeypatch.setattr(
        module,
        "build_live_loan_industry_8bank_codex_verified_mapping_v1",
        lambda: exact,
    )

    digit = copy.deepcopy(exact)
    digit["trials"][7]["verified_mappings"][2]["money_values"][1][
        "independent_pixel_transcription"
    ] = "9.457.078"
    _rehash(module, digit)
    with pytest.raises(module.LoanIndustry8BankCodexVerifiedMappingV1Error, match="replay exactly"):
        module.validate_loan_industry_8bank_codex_verified_mapping_replay_v1(digit)

    relabel = copy.deepcopy(exact)
    transport = next(
        row
        for row in relabel["trials"][1]["verified_mappings"]
        if row["role"] == "TRANSPORT_STORAGE"
    )
    transport["report_norm_id"] = 739
    _rehash(module, relabel)
    with pytest.raises(module.LoanIndustry8BankCodexVerifiedMappingV1Error):
        module.validate_loan_industry_8bank_codex_verified_mapping_replay_v1(relabel)


def test_result_rejects_typed_metric_laundering_even_after_rehash(
    live: tuple[ModuleType, dict[str, Any]],
) -> None:
    module, exact = live
    tampered = copy.deepcopy(exact)
    tampered["metrics"]["document_count"] = 8.0
    _rehash(module, tampered)
    with pytest.raises(module.LoanIndustry8BankCodexVerifiedMappingV1Error):
        module._validate_result(tampered)


def test_persisted_v2_result_exactly_matches_live_replay(
    live: tuple[ModuleType, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    module, exact = live
    persisted = _json(RESULT_PATH)
    assert persisted == exact
    monkeypatch.setattr(
        module,
        "build_live_loan_industry_8bank_codex_verified_mapping_v1",
        lambda: persisted,
    )
    assert (
        module.validate_loan_industry_8bank_codex_verified_mapping_replay_v1(persisted) == persisted
    )


def test_annual_2025_review_and_result_cover_seven_unique_tables() -> None:
    module = _module()
    review = module._review(_json(ANNUAL_REVIEW_PATH), "annual-2025")
    result = module._validate_result(_json(ANNUAL_RESULT_PATH), "annual-2025")

    assert [document["physical_page"] for document in review["documents"]] == [
        51,
        52,
        47,
        37,
        40,
        None,
        42,
        38,
    ]
    assert result["input_refs"]["structure_scan_id"] == module.ANNUAL_2025_EXPECTED_SCAN_ID
    assert result["metrics"] == {
        "document_count": 8,
        "document_no_complete_region_count": 1,
        "document_unique_structure_count": 7,
        "intermediate_source_only_total_verified_count": 0,
        "mapped_item_verified_by_codex_count": 101,
        "mapped_money_value_cell_count": 202,
        "mapped_percentage_corroboration_cell_count": 138,
        "negative_family_control_count": 32,
        "source_only_total_verified_count": 7,
        "transformer_disagreement_preserved_count": 45,
        "unresolved_schema_semantic_row_count": 1,
    }
    assert [len(trial["verified_mappings"]) for trial in result["trials"]] == [
        13,
        21,
        22,
        11,
        8,
        0,
        7,
        19,
    ]
    assert result["trials"][5]["status"] == (
        "UNRESOLVED_NO_COMPLETE_REGION_IN_EXACT_FRESH_VIETOCR_SCAN"
    )
    assert result["trials"][5]["whole_document_family_absence_claim"] is False
    assert result["trials"][4]["unresolved_rows"] == [
        {
            "candidate_report_norm_id": None,
            "independent_pixel_label": "Thương mại, dịch vụ",
            "role": "COMBINED_TRADE_SERVICES",
            "semantic_proposal_label": "Thương mại, dịch vụ",
            "status": "UNRESOLVED_COMBINED_TRADE_AND_SERVICES_NOT_SPLITTABLE_IN_SOURCE",
            "values": result["trials"][4]["unresolved_rows"][0]["values"],
            "whole_document_absence_claim": False,
        }
    ]


def test_annual_2025_review_and_result_tamper_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    review = _json(ANNUAL_REVIEW_PATH)
    review["documents"][1]["transformer_disagreements"][1]["pixel_transcription"] = "4.11"
    with pytest.raises(
        module.LoanIndustry8BankCodexVerifiedMappingV1Error,
        match="fixed pixel ledger",
    ):
        module._review(review, "annual-2025")

    exact = module._validate_result(_json(ANNUAL_RESULT_PATH), "annual-2025")
    monkeypatch.setattr(
        module,
        "build_live_annual_2025_loan_industry_8bank_codex_verified_mapping_v1",
        lambda: exact,
    )
    tampered = copy.deepcopy(exact)
    tampered["trials"][4]["unresolved_rows"][0]["candidate_report_norm_id"] = 733
    _rehash(module, tampered, "annual2025li8bcv1:result:")
    with pytest.raises(module.LoanIndustry8BankCodexVerifiedMappingV1Error):
        module.validate_annual_2025_loan_industry_8bank_codex_verified_mapping_replay_v1(tampered)


def test_annual_2025_persisted_result_exactly_replays_live_inputs() -> None:
    module = _module()
    persisted = _json(ANNUAL_RESULT_PATH)

    assert (
        module.validate_annual_2025_loan_industry_8bank_codex_verified_mapping_replay_v1(persisted)
        == persisted
    )
