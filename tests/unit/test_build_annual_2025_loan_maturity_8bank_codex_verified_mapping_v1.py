from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = (
    _ROOT / "scripts/experiments/build_annual_2025_loan_maturity_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_loan_maturity_8bank_codex_verified_mapping_v1", _MODULE_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def live_result() -> dict[str, object]:
    return builder.build_live_annual_2025_loan_maturity_8bank_codex_verified_mapping_v1()


def test_live_annual_result_maps_all_eight_unique_three_bucket_graphs(
    live_result: dict[str, object],
) -> None:
    assert live_result["state"] == ("ANNUAL_2025_LOAN_MATURITY_8BANK_CODEX_VERIFICATION_COMPLETE")
    assert live_result["metrics"] == {
        "accounting_equation_count": 26,
        "additional_source_population_count": 1,
        "document_count": 8,
        "document_unique_structure_count": 8,
        "mapped_item_verified_by_codex_count": 26,
        "mapped_money_value_cell_count": 52,
        "mapped_optional_margin_count": 2,
        "mapped_percentage_corroboration_cell_count": 8,
        "source_only_total_verified_count": 8,
        "transformer_disagreement_preserved_count": 9,
        "unresolved_mapping_count": 0,
    }
    trials = live_result["trials"]
    assert isinstance(trials, list)
    assert [trial["bank_code"] for trial in trials] == list(builder.EXPECTED_DOCUMENT_ORDER)
    assert all(
        [item["report_norm_id"] for item in trial["mapped_items"]] == [753, 754, 755]
        for trial in trials
    )
    assert [trial["bank_code"] for trial in trials if trial["optional_margin_mapping"]] == [
        "MBB",
        "VPB",
    ]
    assert [trial["bank_code"] for trial in trials if trial["additional_source_population"]] == [
        "HDB"
    ]


def test_fixed_review_rejects_pixel_or_accounting_drift() -> None:
    review = builder._review_blueprint()
    tampered = copy.deepcopy(review)
    tampered["banks"][7]["rows"][2][2][0] = "179.312.938"
    with pytest.raises(builder.Annual2025LoanMaturity8BankError):
        builder._review(tampered)


def test_coordinated_result_rehash_cannot_change_schema_mapping(
    live_result: dict[str, object],
) -> None:
    tampered = copy.deepcopy(live_result)
    tampered["trials"][0]["mapped_items"][0]["report_norm_id"] = 999999
    material = copy.deepcopy(tampered)
    material.pop("result_id")
    tampered["result_id"] = "annual2025lm8bcv1:result:" + canonical_json_sha256_v1(material)
    with pytest.raises(builder.Annual2025LoanMaturity8BankError):
        builder._validate_result(tampered)


def test_dash_is_zero_only_in_the_reviewed_numeric_lane() -> None:
    assert builder._money("-") == 0
    assert builder._money("–") == 0
    assert builder._money("11.178.772") == 11_178_772
    assert builder._compatible_text("Nợ trùng hạn", "Nợ trung hạn") is True
