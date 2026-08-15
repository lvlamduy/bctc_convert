from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT / "scripts/experiments/build_combined_securities_net_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_combined_securities_net_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def live_inputs() -> dict[str, object]:
    return builder._live_inputs()


@pytest.fixture(scope="module")
def persisted_result() -> dict[str, object]:
    return json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())


def test_live_result_replays_and_binds_two_component_equations(
    live_inputs: dict[str, object], persisted_result: dict[str, object]
) -> None:
    result = builder.validate_combined_securities_net_8bank_codex_verified_mapping_replay_v1(
        persisted_result, **live_inputs
    )
    assert result["metrics"] == {
        "accounting_equation_verified_count": 2,
        "combined_net_not_present_document_count": 7,
        "document_count": 8,
        "document_unique_region_count": 1,
        "mapping_verified_count": 1,
        "open_source_row_count": 0,
        "verified_value_cell_count": 2,
    }
    mapped = next(trial for trial in result["trials"] if trial["status"] == "VERIFIED_BY_CODEX")
    assert mapped["document_provenance"] == "MBB"
    assert [
        (equation["period_role"], equation["component_values"], equation["computed_value"])
        for equation in mapped["verified_accounting_equations"]
    ] == [
        ("CURRENT_PERIOD", [249_524, 3_587], 253_111),
        ("COMPARATIVE_PERIOD", [415_700, 1_295_273], 1_710_973),
    ]


def test_public_replay_rejects_coordinated_equation_tamper(
    live_inputs: dict[str, object], persisted_result: dict[str, object]
) -> None:
    forged = copy.deepcopy(persisted_result)
    mapped = next(trial for trial in forged["trials"] if trial["status"] == "VERIFIED_BY_CODEX")
    mapped["verified_accounting_equations"][0]["computed_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0086:result:" + builder.canonical_json_sha256_v1(material)
    with pytest.raises(
        builder.CombinedSecuritiesNet8BankCodexVerifiedMappingV1Error, match="replay exactly"
    ):
        builder.validate_combined_securities_net_8bank_codex_verified_mapping_replay_v1(
            forged, **live_inputs
        )


def test_raw_result_explicitly_has_no_self_authentication_authority(
    persisted_result: dict[str, object], live_inputs: dict[str, object]
) -> None:
    assert persisted_result["authority"]["persisted_result_self_authenticating"] is False
    assert persisted_result["authority"]["public_exact_replay_required"] is True
    assert builder._validate_result(persisted_result)["result_id"] == persisted_result["result_id"]
    assert live_inputs["structure_scan"]["metrics"]["complete_region_count"] == 1
