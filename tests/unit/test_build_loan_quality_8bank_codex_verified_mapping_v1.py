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
    PROJECT_ROOT / "scripts/experiments/build_loan_quality_8bank_codex_verified_mapping_v1.py"
)
REVIEW_PATH = PROJECT_ROOT / "docs/experiments/E-0052-loan-quality-8bank-codex-pixel-review-v1.json"
RESULT_PATH = (
    PROJECT_ROOT / "docs/experiments/E-0052-loan-quality-8bank-codex-verified-mapping-v1.json"
)


def _module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("quality_codex_mapping_v1_test", MODULE_PATH)
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
    value["result_id"] = "lq8bcv1:result:" + module.canonical_json_sha256_v1(material)


def test_fixed_review_and_result_are_closed_and_exact() -> None:
    module = _module()
    review = module._review(_json(REVIEW_PATH))
    result = module._validate_result(_json(RESULT_PATH))

    assert [bank["bank_code"] for bank in review["banks"]] == list(module.EXPECTED_DOCUMENT_ORDER)
    assert result["metrics"] == {
        "additive_source_only_population_count": 2,
        "document_count": 8,
        "document_unique_structure_count": 8,
        "mapped_item_verified_by_codex_count": 41,
        "negative_family_control_count": 16,
        "nonadditive_standard_child_verified_by_codex_count": 1,
        "source_only_total_verified_count": 8,
        "transformer_disagreement_preserved_count": 4,
        "unresolved_near_neighbour_count": 7,
        "verified_by_codex_core_row_count": 40,
    }
    assert all(
        [mapping["report_norm_id"] for mapping in trial["verified_mappings"][:5]]
        == [747, 748, 749, 750, 751]
        for trial in result["trials"]
    )
    assert (
        sum(
            mapping["report_norm_id"] == 5746
            for trial in result["trials"]
            for mapping in trial["verified_mappings"]
        )
        == 1
    )
    assert {trial["layout_mode"] for trial in result["trials"]} == {
        "HORIZONTAL_TYPED_PERIOD_LANES",
        "STACKED_PERIOD_BLOCKS_MULTI_ASSET_COLUMNS",
    }


@pytest.mark.parametrize(
    "mutator",
    (
        lambda value: value["banks"][0].__setitem__("physical_page", True),
        lambda value: value["banks"][0].__setitem__("physical_page", 18.0),
        lambda value: value["banks"][0].__setitem__("reviewer_final_status", "VERIFIED"),
        lambda value: value["banks"][7]["selected_population"].__setitem__(
            "customer_loan_column_index", 4
        ),
        lambda value: value["safety"].__setitem__(
            "transformer_numeric_proposal_used_as_pixel_truth", True
        ),
    ),
)
def test_review_rejects_type_laundering_routing_and_final_status(mutator: Any) -> None:
    module = _module()
    review = _json(REVIEW_PATH)
    mutator(review)
    with pytest.raises(module.LoanQuality8BankCodexVerifiedMappingV1Error):
        module._review(review)


def test_label_rescue_requires_pixel_role_and_explicit_disagreement() -> None:
    module = _module()
    ledger = [
        {
            "disposition": "BOUNDED_ONE_CHARACTER_INSERTION_FULL_ORDERED_TOPOLOGY_RECONCILIATION",
            "field": "LOSS_LABEL",
            "pixel_transcription": "Nợ có khả năng mất vốn",
            "semantic_proposal": "Nợ cón khả năng mất vốn",
        }
    ]

    assert module._surface_compatible(
        "Nợ cón khả năng mất vốn",
        "Nợ có khả năng mất vốn",
        module._ROLE_ALIASES["LOSS"],
        ledger,
    )
    assert not module._surface_compatible(
        "Nợ cón khả năng mất vốn",
        "Nợ có khả năng mất vốn",
        module._ROLE_ALIASES["LOSS"],
        [],
    )
    assert not module._surface_compatible(
        "Nợ đủ tiêu chuẩn",
        "Chứng khoán đủ tiêu chuẩn",
        module._ROLE_ALIASES["STANDARD"],
        [],
    )


def test_numeric_conflict_requires_explicit_pixel_disposition() -> None:
    module = _module()
    ledger = [
        {
            "disposition": "PIXEL_AND_ACCOUNTING_CLOSE_ON_PIXEL",
            "field": "VALUE",
            "pixel_transcription": "81.371.777",
            "semantic_proposal": "81.371.771",
        }
    ]

    assert module._value("81.371.771", "81.371.777", ledger) == 81_371_777
    with pytest.raises(module.LoanQuality8BankCodexVerifiedMappingV1Error):
        module._value("81.371.771", "81.371.777", [])


def test_coordinated_result_rehash_cannot_pass_public_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    exact = module._validate_result(_json(RESULT_PATH))
    tampered = copy.deepcopy(exact)
    tampered["trials"][7]["verified_mappings"][0]["independent_pixel_label"] = "FORGED"
    _rehash(module, tampered)
    monkeypatch.setattr(
        module,
        "build_live_loan_quality_8bank_codex_verified_mapping_v1",
        lambda: exact,
    )

    with pytest.raises(module.LoanQuality8BankCodexVerifiedMappingV1Error):
        module.validate_loan_quality_8bank_codex_verified_mapping_replay_v1(tampered)


def test_result_rejects_typed_metric_laundering_even_after_rehash() -> None:
    module = _module()
    tampered = _json(RESULT_PATH)
    tampered["metrics"]["document_count"] = True
    _rehash(module, tampered)

    with pytest.raises(module.LoanQuality8BankCodexVerifiedMappingV1Error):
        module._validate_result(tampered)
