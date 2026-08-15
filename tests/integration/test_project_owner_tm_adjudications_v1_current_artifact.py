from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_project_owner_tm_adjudications_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_project_owner_tm_adjudications_v1_current_artifact", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
adjudication = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = adjudication
_SPEC.loader.exec_module(adjudication)


def test_current_project_owner_adjudication_exact_replays() -> None:
    persisted = json.loads((adjudication.PROJECT_ROOT / adjudication.OUTPUT_PATH).read_text())
    replayed = adjudication.validate_project_owner_tm_adjudications_replay_v1(persisted)

    assert replayed["adjudication_id"] == (
        "e0067a:adjudication:0ebc6ffcad1d5d89fe049c56e2daf01cb8db65e1cc5715b6a74ff4783e706725"
    )
    assert replayed["metrics"] == {
        "confirmed_absence_count": 3,
        "decision_count": 5,
        "hierarchy_confirmation_count": 1,
        "new_mapping_count": 1,
        "source_component_count": 2,
    }
