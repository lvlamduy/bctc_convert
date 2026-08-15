from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_loan_geography_project_owner_absence_closure_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_loan_geography_project_owner_absence_closure_v1_current_artifact", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
closure = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = closure
_SPEC.loader.exec_module(closure)


def test_current_geography_owner_closure_exact_replays_e0065() -> None:
    persisted = json.loads((closure.PROJECT_ROOT / closure.OUTPUT_PATH).read_text())
    replayed = closure.validate_loan_geography_project_owner_absence_closure_replay_v1(persisted)

    assert replayed["result_id"] == (
        "e0067d:result:988956d8942f73a865b82f827cf89f8697407cf77515e62dd31d331440851ff0"
    )
    assert replayed["verified_present_banks"] == ["MBB", "VIB"]
    assert replayed["metrics"]["open_geography_review_count"] == 0
