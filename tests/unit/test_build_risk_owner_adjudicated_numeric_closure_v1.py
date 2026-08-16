from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/experiments/build_risk_owner_adjudicated_numeric_closure_v1.py"


def _load():
    spec = importlib.util.spec_from_file_location("risk_owner_adjudicated_closure_test", SOURCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _mapping(family: dict, bank: str, axis: str, role: str) -> dict:
    matches = [
        row
        for row in family["verified_mappings"]
        if row["bank_code"] == bank and row["axis_role"] == axis and row["source_role"] == role
    ]
    assert len(matches) == 1
    return matches[0]


def test_build_closes_currency_and_all_interest_rate_gaps() -> None:
    module = _load()
    result = module.build_live_risk_owner_adjudicated_numeric_closure_v1()

    assert result["metrics"] == {
        "closed_gap_count": 49,
        "currency_full_verified_mapping_count": 120,
        "currency_full_verified_value_cell_count": 136,
        "currency_remaining_gap_count": 3,
        "full_verified_accounting_equation_count": 210,
        "interest_rate_full_verified_mapping_count": 234,
        "interest_rate_full_verified_value_cell_count": 279,
        "interest_rate_remaining_gap_count": 0,
        "liquidity_full_verified_mapping_count": 129,
        "liquidity_full_verified_value_cell_count": 153,
        "liquidity_remaining_gap_count": 4,
        "new_verified_accounting_equation_count": 80,
        "new_verified_mapping_count": 147,
        "new_verified_value_cell_count": 216,
        "remaining_gap_count": 7,
    }
    currency = result["family_closures"]["CURRENCY_RISK"]
    assert currency["remaining_gap_ids"] == ["CRISK-002", "CRISK-007", "CRISK-009"]
    assert [row["residual"] for row in currency["source_presentation_residuals"]] == [-1, -1]

    interest = result["family_closures"]["INTEREST_RATE_RISK"]
    assert interest["remaining_gap_ids"] == []
    assert len(interest["verified_mappings"]) == 85
    assert len(interest["verified_accounting_equations"]) == 54


def test_vib_rotated_matrices_are_complete_and_exact() -> None:
    module = _load()
    result = module.build_live_risk_owner_adjudicated_numeric_closure_v1()
    interest = result["family_closures"]["INTEREST_RATE_RISK"]
    liquidity = result["family_closures"]["LIQUIDITY_RISK"]

    ir_row = _mapping(interest, "VIB", "WITHIN_LE1M", "STATE_COMBINED")
    assert [(value["period_axis"], value["normalized_value"]) for value in ir_row["values"]] == [
        ("CURRENT", -39_508_044),
        ("COMPARATIVE", -96_064_408),
    ]
    assert len([row for row in interest["verified_mappings"] if row["bank_code"] == "VIB"]) == 45
    assert (
        len([row for row in interest["verified_accounting_equations"] if row["bank_code"] == "VIB"])
        == 36
    )

    lr_row = _mapping(liquidity, "VIB", "TOTAL", "NET_LIQUIDITY_GAP")
    assert [(value["period_axis"], value["normalized_value"]) for value in lr_row["values"]] == [
        ("CURRENT", 52_901_085),
        ("COMPARATIVE", 51_763_804),
    ]
    assert len([row for row in liquidity["verified_mappings"] if row["bank_code"] == "VIB"]) == 24
    assert (
        len(
            [row for row in liquidity["verified_accounting_equations"] if row["bank_code"] == "VIB"]
        )
        == 16
    )
    assert liquidity["remaining_gap_ids"] == [
        "LRISK-002",
        "LRISK-003",
        "LRISK-004",
        "LRISK-005",
    ]


def test_exact_replay_rejects_value_and_typed_metric_tamper() -> None:
    module = _load()
    result = module.build_live_risk_owner_adjudicated_numeric_closure_v1()
    module.validate_risk_owner_adjudicated_numeric_closure_replay_v1(result)

    changed = copy.deepcopy(result)
    changed["family_closures"]["LIQUIDITY_RISK"]["verified_mappings"][-1]["values"][-1][
        "normalized_value"
    ] += 1
    with pytest.raises(module.RiskOwnerAdjudicatedClosureV1Error):
        module.validate_risk_owner_adjudicated_numeric_closure_replay_v1(changed)

    changed = copy.deepcopy(result)
    changed["metrics"]["remaining_gap_count"] = 7.0
    with pytest.raises(module.RiskOwnerAdjudicatedClosureV1Error):
        module.validate_risk_owner_adjudicated_numeric_closure_replay_v1(changed)


def test_crop_byte_drift_fails_before_numeric_promotion(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load()
    original = module._stable_bytes
    target = Path(
        "output/development/loan-maturity-full-document-vietocr-v1/frozen/crops/sample-00033355.png"
    )

    def tampered(path: Path) -> bytes:
        payload = original(path)
        return payload + b"x" if path == target else payload

    monkeypatch.setattr(module, "_stable_bytes", tampered)
    with pytest.raises(module.RiskOwnerAdjudicatedClosureV1Error):
        module.build_live_risk_owner_adjudicated_numeric_closure_v1()


def test_persisted_result_exact_replays_live_inputs() -> None:
    module = _load()
    payload = module._strict_json(
        module._stable_bytes(module.OUTPUT_PATH), module.OUTPUT_PATH.as_posix()
    )
    assert module.validate_risk_owner_adjudicated_numeric_closure_replay_v1(payload) == payload
