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


def _rehash(module: ModuleType, value: dict[str, Any]) -> None:
    material = copy.deepcopy(value)
    material.pop("result_id")
    value["result_id"] = "li8bcv1:result:" + module.canonical_json_sha256_v1(material)


@pytest.fixture(scope="module")
def live() -> tuple[ModuleType, dict[str, Any]]:
    module = _module()
    return module, module.build_live_loan_industry_8bank_codex_verified_mapping_v1()


def test_live_result_is_exact_bounded_and_preserves_all_unresolved_rows(
    live: tuple[ModuleType, dict[str, Any]],
) -> None:
    module, result = live
    assert result["result_id"] == (
        "li8bcv1:result:a7435794e8639f9aa53ada040d13abddf966b91ab839a9aa1391bf2cdba52c58"
    )
    assert result["metrics"] == {
        "document_count": 8,
        "document_no_complete_region_count": 3,
        "document_unique_structure_count": 5,
        "intermediate_source_only_total_verified_count": 1,
        "mapped_item_verified_by_codex_count": 72,
        "mapped_money_value_cell_count": 144,
        "mapped_percentage_corroboration_cell_count": 112,
        "negative_family_control_count": 32,
        "source_only_total_verified_count": 5,
        "transformer_disagreement_preserved_count": 16,
        "unresolved_schema_semantic_row_count": 8,
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
        ("MBB", 33, 19, 2),
        ("VPB", 44, 19, 3),
        ("HDB", 27, 10, 1),
        ("VCB", None, 0, 0),
        ("CTG", None, 0, 0),
        ("BID", 22, 6, 1),
        ("VIB", 33, 18, 1),
    ]
    assert all(trial["whole_document_family_absence_claim"] is False for trial in result["trials"])


def test_unresolved_rows_are_semantic_scope_conflicts_not_fuzzy_failures(
    live: tuple[ModuleType, dict[str, Any]],
) -> None:
    _, result = live
    unresolved = {
        (
            trial["document_provenance"],
            row["role"],
            row["candidate_report_norm_id"],
            row["status"],
        )
        for trial in result["trials"]
        for row in trial["unresolved_rows"]
    }
    assert unresolved == {
        (
            "MBB",
            "TRANSPORT_STORAGE",
            736,
            "UNRESOLVED_SOURCE_TRANSPORT_ROW_NOT_EQUIVALENT_TO_COMBINED_TRANSPORT_AND_INFORMATION_SCHEMA_ROW",
        ),
        (
            "MBB",
            "FOREIGN_BRANCH_LOANS",
            None,
            "UNRESOLVED_GEOGRAPHIC_BRANCH_POPULATION_NOT_ONE_INDUSTRY_SCHEMA_CHILD",
        ),
        (
            "VPB",
            "TRANSPORT_STORAGE",
            736,
            "UNRESOLVED_SOURCE_TRANSPORT_ROW_NOT_EQUIVALENT_TO_COMBINED_TRANSPORT_AND_INFORMATION_SCHEMA_ROW",
        ),
        (
            "VPB",
            "PUBLIC_ADMIN_DEFENCE_SOCIAL_SECURITY",
            744,
            "UNRESOLVED_PUBLIC_ADMINISTRATION_NOT_EQUIVALENT_TO_INTERNATIONAL_ORGANIZATIONS",
        ),
        (
            "VPB",
            "PERSONAL_HOUSING_LOANS",
            None,
            "UNRESOLVED_NO_EXACT_INDUSTRY_CHILD_FOR_PERSONAL_HOUSING_LOAN_POPULATION",
        ),
        (
            "HDB",
            "TRANSPORT_STORAGE",
            736,
            "UNRESOLVED_SOURCE_TRANSPORT_ROW_NOT_EQUIVALENT_TO_COMBINED_TRANSPORT_AND_INFORMATION_SCHEMA_ROW",
        ),
        (
            "BID",
            "BROAD_SERVICES",
            739,
            "UNRESOLVED_BROAD_SERVICES_NOT_EQUIVALENT_TO_PERSONAL_AND_COMMUNITY_SERVICES",
        ),
        (
            "VIB",
            "TRANSPORT_STORAGE",
            736,
            "UNRESOLVED_SOURCE_TRANSPORT_ROW_NOT_EQUIVALENT_TO_COMBINED_TRANSPORT_AND_INFORMATION_SCHEMA_ROW",
        ),
    }


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

    promoted = copy.deepcopy(exact)
    promoted["trials"][1]["unresolved_rows"][0]["status"] = "VERIFIED_BY_CODEX"
    _rehash(module, promoted)
    with pytest.raises(module.LoanIndustry8BankCodexVerifiedMappingV1Error):
        module.validate_loan_industry_8bank_codex_verified_mapping_replay_v1(promoted)


def test_result_rejects_typed_metric_laundering_even_after_rehash(
    live: tuple[ModuleType, dict[str, Any]],
) -> None:
    module, exact = live
    tampered = copy.deepcopy(exact)
    tampered["metrics"]["document_count"] = 8.0
    _rehash(module, tampered)
    with pytest.raises(module.LoanIndustry8BankCodexVerifiedMappingV1Error):
        module._validate_result(tampered)
