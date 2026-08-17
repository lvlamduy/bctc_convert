from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_other_payables_project_owner_other_closure_v1.py"
_SPEC = importlib.util.spec_from_file_location("other_payables_owner_closure", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def test_closure_maps_all_e0077_open_rows_to_other_without_double_counting() -> None:
    result = builder.build_other_payables_project_owner_other_closure_v1()
    assert result["metrics"] == {
        "affected_document_count": 4,
        "closed_ledger_row_count": 18,
        "remaining_e0077_open_row_count": 0,
        "verified_source_value_component_count": 36,
    }
    assert {row["ledger_id"] for row in result["mappings"]} == {
        f"OPL-{ordinal:03d}" for ordinal in range(1, 19)
    }
    assert {row["schema_binding"]["report_norm_id"] for row in result["mappings"]} == {1127}
    assert all(
        "NONADDITIVE_BREAKDOWN" in row["project_owner_decision"] for row in result["mappings"]
    )


def test_persisted_closure_matches_live_replay_and_rejects_promotion_drift() -> None:
    persisted = json.loads((builder.PROJECT_ROOT / builder.OUTPUT_PATH).read_text())
    assert builder.validate_other_payables_project_owner_other_closure_v1(persisted) == persisted
    assert persisted["result_id"] == (
        "e0132a:result:0a08e6bc1b062da0f824783de3866993a7b85c70a1c518f2ab2cc01edaad40cb"
    )
    forged = json.loads(json.dumps(persisted))
    forged["mappings"][0]["schema_binding"]["report_norm_id"] = 1124
    material = json.loads(json.dumps(forged))
    material.pop("result_id")
    forged["result_id"] = "e0132a:result:" + builder.canonical_json_sha256_v1(material)
    with pytest.raises(
        builder.OtherPayablesProjectOwnerOtherClosureV1Error,
        match="does not replay exactly",
    ):
        builder.validate_other_payables_project_owner_other_closure_v1(forged)
