from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_loan_quality_margin_separation_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_loan_quality_margin_separation_v1_current_artifact", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
quality = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = quality
_SPEC.loader.exec_module(quality)


def test_current_loan_quality_margin_separation_exact_replays() -> None:
    persisted = json.loads((quality.PROJECT_ROOT / quality.OUTPUT_PATH).read_text())
    replayed = quality.validate_loan_quality_margin_separation_replay_v1(persisted)

    assert replayed["result_id"] == (
        "e0067b:result:e1f34346a27374eeb6ba767f9693e9956e471e31539ec38883ea7eab37921c50"
    )
    assert replayed["metrics"]["normalized_mapping_count"] == 43
    assert replayed["metrics"]["standalone_margin_mapping_count"] == 3
    assert replayed["metrics"]["adjusted_standard_grade_bank_count"] == 1
    assert replayed["metrics"]["double_count_count"] == 0
