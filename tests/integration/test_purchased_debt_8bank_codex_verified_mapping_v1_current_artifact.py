from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_purchased_debt_8bank_codex_verified_mapping_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_purchased_debt_8bank_codex_verified_mapping_v1_current_artifact",
    _PATH,
)
assert _SPEC is not None and _SPEC.loader is not None
mapping = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = mapping
_SPEC.loader.exec_module(mapping)


def test_current_purchased_debt_result_replays_from_all_fixed_sources() -> None:
    persisted = json.loads((mapping.PROJECT_ROOT / mapping.RESULT_PATH).read_text())
    replayed = mapping.validate_purchased_debt_8bank_codex_verified_mapping_replay_v1(persisted)

    assert replayed["result_id"] == (
        "e0066:result:79e15086c88ca9283d450955da737a620012679f36071e39dce9a63962c76a3b"
    )
    assert replayed["metrics"] == {
        "accounting_equation_verified_count": 19,
        "core_accounting_equation_verified_count": 16,
        "dash_cell_verified_as_zero_count": 5,
        "document_count": 8,
        "document_not_observed_count": 4,
        "document_verified_count": 4,
        "mapped_value_cell_count": 34,
        "mapping_verified_count": 17,
        "optional_check_equation_count": 3,
        "unresolved_mapping_count": 0,
    }
    by_code = {trial["bank_provenance"]: trial for trial in replayed["trials"]}
    assert [
        code
        for code in mapping.EXPECTED_DOCUMENT_ORDER
        if by_code[code]["status"] == "VERIFIED_BY_CODEX"
    ] == ["MBB", "VPB", "HDB", "VIB"]
    assert all(
        trial["family_boundary"]["next_family_boundary"]["independent_pixel_transcription"]
        in {"Chứng khoán đầu tư", "CHỨNG KHOÁN ĐẦU TƯ", "CHỨNG KHOÁN ĐẦU TƯ SẴN SÀNG ĐỂ BÁN"}
        for trial in by_code.values()
        if trial["status"] == "VERIFIED_BY_CODEX"
    )
