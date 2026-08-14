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
    PROJECT_ROOT / "scripts/experiments/build_loan_maturity_8bank_codex_verified_mapping_v1.py"
)
REVIEW_PATH = (
    PROJECT_ROOT / "docs/experiments/E-0051-loan-maturity-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = (
    PROJECT_ROOT / "docs/experiments/E-0051-loan-maturity-8bank-codex-verified-mapping-v1.json"
)


def _module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("codex_verified_mapping_v1_test", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert type(value) is dict
    return value


def _rehash_result(module: ModuleType, value: dict[str, Any]) -> None:
    material = copy.deepcopy(value)
    material.pop("result_id")
    value["result_id"] = "lm8bcv1:result:" + module.canonical_json_sha256_v1(material)


def test_fixed_review_and_verified_result_are_closed_and_exact() -> None:
    module = _module()
    review = module._review(_json(REVIEW_PATH))
    result = module._validate_result(_json(RESULT_PATH))

    assert [bank["bank_code"] for bank in review["banks"]] == list(module.EXPECTED_DOCUMENT_ORDER)
    assert result["metrics"] == {
        "document_count": 8,
        "document_unique_structure_count": 8,
        "mapped_item_verified_by_codex_count": 26,
        "optional_margin_verified_by_codex_count": 2,
        "source_only_total_verified_count": 8,
        "transformer_disagreement_preserved_count": 5,
        "unresolved_near_neighbour_count": 14,
        "verified_by_codex_core_row_count": 24,
    }
    assert all(
        [item["report_norm_id"] for item in trial["verified_mappings"][:3]] == [753, 754, 755]
        for trial in result["trials"]
    )
    assert (
        sum(
            item["report_norm_id"] == 5747
            for trial in result["trials"]
            for item in trial["verified_mappings"]
        )
        == 2
    )
    assert all(trial["source_only_total"]["report_norm_id"] is None for trial in result["trials"])


@pytest.mark.parametrize(
    "mutator",
    (
        lambda value: value["banks"][0].__setitem__("physical_page", True),
        lambda value: value["banks"][0].__setitem__("physical_page", 18.0),
        lambda value: value["banks"][0].__setitem__("reviewer_final_status", "VERIFIED"),
        lambda value: value["safety"].__setitem__(
            "transformer_numeric_proposal_used_as_pixel_truth", True
        ),
        lambda value: value["reviewer"].__setitem__("kind", "SELF_ATTESTED"),
    ),
)
def test_review_rejects_type_laundering_authority_and_final_status(
    mutator: Any,
) -> None:
    module = _module()
    review = _json(REVIEW_PATH)
    mutator(review)
    with pytest.raises(module.LoanMaturity8BankCodexVerifiedMappingV1Error):
        module._review(review)


def test_common_surface_reconciliation_handles_enumeration_suffix_and_one_edit() -> None:
    module = _module()

    assert module._surface_compatible(
        "4. CHO VAY KHÁCH HÀNG",
        "4. CHO VAY KHÁCH HÀNG:",
        ("Cho vay khách hàng",),
    )
    assert module._surface_compatible(
        "Nợi ngắn hạn", "Nợ ngắn hạn", ("Nợ ngắn hạn", "Cho vay ngắn hạn")
    )
    assert module._surface_compatible(
        "Các khoản cho vay margin chứng khoán và ứng trước khách hàng tại MBs",
        "Các khoản cho vay margin chứng khoán và ứng trước khách hàng tại MBS",
        ("Các khoản cho vay margin chứng khoán và ứng trước khách hàng",),
    )
    assert not module._surface_compatible(
        "Phân tích chất lượng cho vay",
        "Phân tích chất lượng cho vay",
        ("Nợ ngắn hạn", "Cho vay ngắn hạn"),
    )


def test_transformer_digit_conflict_requires_explicit_pixel_disposition() -> None:
    module = _module()
    ledger = [
        {
            "disposition": "DIGIT_CONFLICT_PIXEL_AND_ACCOUNTING_CLOSE_ON_PIXEL",
            "field": "MEDIUM_TERM_COMPARATIVE_VALUE",
            "pixel_transcription": "81.371.777",
            "semantic_proposal": "81.371.771",
        }
    ]

    assert module._value("81.371.771", "81.371.777", "MONEY", ledger) == 81_371_777
    with pytest.raises(module.LoanMaturity8BankCodexVerifiedMappingV1Error):
        module._value("81.371.771", "81.371.777", "MONEY", [])


def test_coordinated_result_rehash_cannot_pass_public_exact_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    exact = module._validate_result(_json(RESULT_PATH))
    tampered = copy.deepcopy(exact)
    tampered["trials"][0]["verified_mappings"][0]["independent_pixel_label"] = "FORGED_PIXEL_TEXT"
    _rehash_result(module, tampered)
    monkeypatch.setattr(
        module,
        "build_live_loan_maturity_8bank_codex_verified_mapping_v1",
        lambda: exact,
    )

    with pytest.raises(module.LoanMaturity8BankCodexVerifiedMappingV1Error):
        module.validate_loan_maturity_8bank_codex_verified_mapping_replay_v1(tampered)


def test_result_rejects_typed_metric_laundering_even_after_rehash() -> None:
    module = _module()
    tampered = _json(RESULT_PATH)
    tampered["metrics"]["document_count"] = True
    _rehash_result(module, tampered)

    with pytest.raises(module.LoanMaturity8BankCodexVerifiedMappingV1Error):
        module._validate_result(tampered)
