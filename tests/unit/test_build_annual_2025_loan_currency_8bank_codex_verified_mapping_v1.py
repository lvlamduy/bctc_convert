from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT / "scripts/experiments/build_annual_2025_loan_currency_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_loan_currency_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def live_result() -> dict[str, object]:
    return builder.build_live_annual_2025_loan_currency_8bank_codex_verified_mapping_v1()


def test_live_result_maps_two_unique_regions_and_binds_six_absences(
    live_result: dict[str, object],
) -> None:
    assert live_result["metrics"] == {
        "accounting_equation_count": 8,
        "bounded_report_absence_count": 6,
        "document_count": 8,
        "document_unique_mapping_region_count": 2,
        "mapped_item_verified_by_codex_count": 4,
        "mapped_money_value_cell_count": 8,
        "source_only_additional_population_count": 1,
        "transformer_numeric_disagreement_count": 2,
        "unresolved_mapping_count": 0,
    }
    trials = live_result["trials"]
    assert isinstance(trials, list)
    assert [trial["bank_code"] for trial in trials] == list(builder.EXPECTED_DOCUMENT_ORDER)
    assert [trial["bank_code"] for trial in trials if trial["status"] == "VERIFIED_BY_CODEX"] == [
        "ACB",
        "HDB",
    ]
    assert all(
        trial["report_norm_ids_not_observed"] == [756, 757, 758]
        for trial in trials
        if trial["status"] == "VERIFIED_NOT_OBSERVED_IN_BOUND_REPORT"
    )


def test_hdb_primary_numeric_axis_and_pixels_override_two_transformer_digits(
    live_result: dict[str, object],
) -> None:
    hdb = next(trial for trial in live_result["trials"] if trial["bank_code"] == "HDB")
    assert hdb["mapped_items"][0]["source_values"] == ["527.584.876", "418.599.063"]
    assert hdb["source_only_total"] == {
        "core_total": ["546.370.779", "431.306.069"],
        "grand_total": ["546.370.779", "442.484.841"],
        "status": "VERIFIED_SOURCE_ONLY_NO_REPORT_NORM_ID",
    }
    assert hdb["additional_source_population"]["pixel_values"] == ["-", "11.178.772"]
    assert len(hdb["transformer_disagreements"]) == 2


def test_fixed_review_and_coordinated_result_rehash_fail_closed(
    live_result: dict[str, object],
) -> None:
    semantic = builder._strict_json(
        builder._fixed_bytes(builder.SEMANTIC_INDEX_PATH, builder.EXPECTED_INDEX_SHA256),
        "semantic",
    )
    manifest = builder._strict_json(
        builder._fixed_bytes(builder.CROP_MANIFEST_PATH, builder.EXPECTED_CROP_MANIFEST_SHA256),
        "manifest",
    )
    review = builder._review_blueprint(semantic, manifest)
    tampered_review = copy.deepcopy(review)
    tampered_review["banks"][3]["rows"][0]["pixel_values"][1] = "418.599.083"
    with pytest.raises(builder.Annual2025LoanCurrency8BankError):
        builder._validate_review(tampered_review, semantic, manifest)

    forged = copy.deepcopy(live_result)
    forged["trials"][0]["mapped_items"][0]["report_norm_id"] = 999999
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "annual2025lcbcv1:result:" + canonical_json_sha256_v1(material)
    with pytest.raises(builder.Annual2025LoanCurrency8BankError):
        builder._validate_result(forged)
