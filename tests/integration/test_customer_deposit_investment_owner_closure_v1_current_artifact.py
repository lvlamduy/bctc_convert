from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_customer_deposit_investment_owner_closure_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_customer_deposit_investment_owner_closure_v1_current_artifact", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
closure = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = closure
_SPEC.loader.exec_module(closure)


def test_current_owner_closure_exact_replays_all_live_inputs() -> None:
    persisted = json.loads((closure.PROJECT_ROOT / closure.OUTPUT_PATH).read_text())
    replayed = closure.validate_customer_deposit_investment_owner_closure_replay_v1(persisted)

    assert replayed["result_id"] == (
        "e0067c:result:6a483d65b962f0127fad49c64174765e2774fcbe967ef564ea2ebd72504b3ccd"
    )
    assert replayed["customer_deposit"]["closed_ledger_ids"] == ["CD-001", "CD-002"]
    assert replayed["investment_securities"]["closed_ledger_ids"] == [
        "IS-001",
        "IS-002",
    ]
    assert replayed["metrics"] == {
        "closed_ledger_entry_count": 4,
        "customer_deposit_added_mapping_count": 2,
        "investment_added_accounting_equation_count": 12,
        "investment_added_mapped_value_cell_count": 30,
        "investment_added_mapping_count": 15,
        "remaining_targeted_unresolved_count": 0,
    }
