from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_investment_securities_8bank_codex_verified_mapping_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_investment_securities_8bank_codex_verified_mapping_v1_current_artifact",
    _PATH,
)
assert _SPEC is not None and _SPEC.loader is not None
mapping = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = mapping
_SPEC.loader.exec_module(mapping)


def test_current_investment_securities_result_replays_from_all_fixed_sources() -> None:
    persisted = json.loads((mapping.PROJECT_ROOT / mapping.RESULT_PATH).read_text())
    replayed = mapping.validate_investment_securities_8bank_codex_verified_mapping_replay_v1(
        persisted
    )

    assert replayed["result_id"] == (
        "e0067:result:ba8a22afd96879f4cf44c5430cb880ce7f267ad83dc2a23f55c7b5c905ef1176"
    )
    assert replayed["metrics"] == {
        "accounting_equation_verified_count": 27,
        "dash_cell_verified_as_zero_count": 15,
        "document_count": 8,
        "document_unresolved_count": 1,
        "document_verified_count": 7,
        "mapped_value_cell_count": 168,
        "mapping_verified_count": 84,
        "unresolved_mapping_count": 2,
    }
    by_code = {trial["bank_provenance"]: trial for trial in replayed["trials"]}
    assert [
        code
        for code in mapping.EXPECTED_DOCUMENT_ORDER
        if by_code[code]["status"] == "VERIFIED_BY_CODEX"
    ] == ["ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "VIB"]
    assert by_code["BID"]["status"] == "UNRESOLVED_MAPPING"
    assert {row["report_norm_id"] for row in by_code["VIB"]["verified_mappings"]} == {
        807,
        824,
    }
    assert by_code["CTG"]["verified_accounting_equations"][-1]["role"] == (
        "CTG_CURRENT_COMBINED_NET"
    )
