from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT
    / "scripts/experiments/build_annual_2025_loan_geography_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_loan_geography_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def live_result() -> dict[str, object]:
    return builder.build_live_annual_2025_loan_geography_8bank_codex_verified_mapping_v1()


def test_live_result_maps_three_unique_regions_and_binds_five_absences(
    live_result: dict[str, object],
) -> None:
    assert live_result["metrics"] == {
        "accounting_equation_count": 6,
        "bounded_report_absence_count": 5,
        "broad_scope_negative_control_count": 3,
        "document_count": 8,
        "document_unique_mapping_region_count": 3,
        "mapped_item_verified_by_codex_count": 6,
        "mapped_money_value_cell_count": 12,
        "transformer_numeric_disagreement_count": 0,
        "unresolved_mapping_count": 0,
    }
    trials = live_result["trials"]
    assert isinstance(trials, list)
    assert [trial["bank_code"] for trial in trials] == list(builder.EXPECTED_DOCUMENT_ORDER)
    assert [trial["bank_code"] for trial in trials if trial["status"] == "VERIFIED_BY_CODEX"] == [
        "ACB",
        "MBB",
        "VIB",
    ]


def test_mapped_rows_close_to_customer_loan_owner_and_preserve_visible_dash(
    live_result: dict[str, object],
) -> None:
    trials = {trial["bank_code"]: trial for trial in live_result["trials"]}
    assert trials["MBB"]["accounting_equations"] == [
        {
            "computed_total": 1_084_019_370,
            "customer_loan_owner_total": 1_084_019_370,
            "domestic": 1_074_688_741,
            "foreign": 9_330_629,
            "period": "2025-12-31",
            "visible_total": 1_084_019_370,
        },
        {
            "computed_total": 776_657_846,
            "customer_loan_owner_total": 776_657_846,
            "domestic": 769_363_498,
            "foreign": 7_294_348,
            "period": "2024-12-31",
            "visible_total": 776_657_846,
        },
    ]
    for bank in ("ACB", "VIB"):
        foreign = next(
            item for item in trials[bank]["mapped_items"] if item["report_norm_id"] == 765
        )
        assert [value["source_cell_status"] for value in foreign["source_values"]] == [
            "DASH",
            "DASH",
        ]
        assert [value["normalized_value"] for value in foreign["source_values"]] == [0, 0]


def test_broader_loan_geography_is_a_negative_control_not_a_mapping(
    live_result: dict[str, object],
) -> None:
    trials = {trial["bank_code"]: trial for trial in live_result["trials"]}
    for bank in ("VPB", "HDB", "BID"):
        trial = trials[bank]
        assert trial["status"] == "VERIFIED_NOT_OBSERVED_IN_BOUND_REPORT"
        assert trial["near_region_count"] == 1
        assert trial["near_broader_region"] is not None
        assert trial["report_norm_ids_not_observed"] == [759, 5752, 765]
    for bank in ("VCB", "CTG"):
        assert trials[bank]["near_region_count"] == 0
        assert trials[bank]["near_broader_region"] is None


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
    tampered_review["banks"][0]["periods"][0]["cells"][1]["pixel_value"] = "0"
    with pytest.raises(builder.Annual2025LoanGeography8BankError):
        builder._validate_review(tampered_review, semantic, manifest)

    forged = copy.deepcopy(live_result)
    forged["trials"][0]["mapped_items"][0]["report_norm_id"] = 999999
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "annual2025lg8bcv1:result:" + canonical_json_sha256_v1(material)
    with pytest.raises(builder.Annual2025LoanGeography8BankError):
        builder._validate_result(forged)
