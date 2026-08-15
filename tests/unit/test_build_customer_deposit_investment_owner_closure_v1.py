from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_customer_deposit_investment_owner_closure_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_customer_deposit_investment_owner_closure_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
closure = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = closure
_SPEC.loader.exec_module(closure)


def _persisted() -> dict[str, object]:
    return json.loads((closure.PROJECT_ROOT / closure.OUTPUT_PATH).read_text())


def test_customer_deposit_rows_close_to_live_schema_770() -> None:
    result = closure._validate(_persisted())
    deposit = result["customer_deposit"]

    assert deposit["schema_binding"] == {
        "canonical_name": "Công ty TNHH MTV (hoặc trên MTV) vốn nhà nước trên 50%",
        "display_order": 224,
        "parent_report_norm_id": 766,
        "report_norm_id": 770,
    }
    assert [
        (
            item["bank_provenance"],
            item["report_norm_id"],
            item["source_value"]["normalized_value"],
        )
        for item in deposit["resolved_mappings"]
    ] == [("VPB", 770, 64165), ("VIB", 770, 174)]
    assert deposit["post_adjudication_metrics"] == {
        "accounting_equation_verified_count": 43,
        "mapping_verified_count": 120,
        "unresolved_source_item_count": 0,
    }


def test_bid_document_unit_and_vib_tctd_aggregation_close_exactly() -> None:
    investment = closure._validate(_persisted())["investment_securities"]
    bid = investment["bid_verified_trial"]
    vib = investment["vib_808_aggregate_mapping"]

    assert bid["document_unit_evidence"]["unit"] == "Triệu VND"
    assert bid["document_unit_evidence"]["evidence"]["crop_ref"]["sha256"] == (
        "c493088359c92ec6de5329f4a4d2291f57f6c103eaf47affd639f6565f3367ec"
    )
    assert len(bid["verified_mappings"]) == 14
    assert len(bid["verified_accounting_equations"]) == 10
    assert all(
        equation["computed_total"] == equation["visible_total"]
        for equation in bid["verified_accounting_equations"]
    )
    assert bid["visible_dash_normalized_zero_count"] == 1

    assert vib["report_norm_id"] == 808
    assert [item["normalized_value"] for item in vib["source_values"]] == [
        38773550,
        40356524,
    ]
    assert [equation["addends"] for equation in vib["equations"]] == [
        [5894320, 32879230],
        [12104102, 28252422],
    ]
    assert all(
        sum(equation["addends"]) == equation["computed_total"] for equation in vib["equations"]
    )
    assert investment["post_adjudication_metrics"] == {
        "accounting_equation_verified_count": 39,
        "dash_cell_verified_as_zero_count": 16,
        "document_unresolved_count": 0,
        "document_verified_count": 8,
        "mapped_value_cell_count": 198,
        "mapping_verified_count": 99,
        "unresolved_mapping_count": 0,
    }


def test_type_poison_and_uncoordinated_content_tamper_fail_closed() -> None:
    forged = _persisted()
    forged["metrics"]["closed_ledger_entry_count"] = 4.0
    with pytest.raises(
        closure.CustomerDepositInvestmentOwnerClosureV1Error,
        match="shape, authority, or metrics",
    ):
        closure._validate(forged)

    forged = _persisted()
    forged["customer_deposit"]["resolved_mappings"][0]["source_value"]["normalized_value"] += 1
    with pytest.raises(
        closure.CustomerDepositInvestmentOwnerClosureV1Error,
        match="content identity drifted",
    ):
        closure._validate(forged)


def test_coordinated_rehash_cannot_replace_exact_live_rebuild(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    persisted = _persisted()
    forged = copy.deepcopy(persisted)
    forged["investment_securities"]["vib_808_aggregate_mapping"]["source_values"][0][
        "normalized_value"
    ] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0067c:result:" + closure.canonical_json_sha256_v1(material)

    monkeypatch.setattr(
        closure,
        "build_live_customer_deposit_investment_owner_closure_v1",
        lambda: persisted,
    )
    with pytest.raises(
        closure.CustomerDepositInvestmentOwnerClosureV1Error,
        match="does not exact-replay",
    ):
        closure.validate_customer_deposit_investment_owner_closure_replay_v1(forged)
