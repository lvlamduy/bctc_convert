from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_project_owner_tm_adjudications_v1.py"
_SPEC = importlib.util.spec_from_file_location("build_project_owner_tm_adjudications_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
adjudication = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = adjudication
_SPEC.loader.exec_module(adjudication)


def _persisted() -> dict[str, object]:
    return json.loads((adjudication.PROJECT_ROOT / adjudication.OUTPUT_PATH).read_text())


def test_persisted_adjudication_has_exact_mapping_absences_and_hierarchy() -> None:
    result = adjudication._validate(_persisted())
    by_id = {decision["decision_id"]: decision for decision in result["decisions"]}

    mbb = by_id["CBD-MBB-574"]
    assert mbb["mapping"]["report_norm_id"] == 574
    assert mbb["mapping"]["normalized_value"] == 934855 + 1213504 == 2148359
    assert mbb["reconciliation"] == {
        "computed_total": 27417370,
        "other_deposits": 2148359,
        "visible_family_total": 27417370,
        "vietnam_deposits": 25269011,
    }
    assert {
        decision_id
        for decision_id, decision in by_id.items()
        if decision["status"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT"
    } == {"IDL-HDB-ABSENCE", "IDL-VCB-ABSENCE", "DFI-VCB-ABSENCE"}
    assert by_id["SEC-VIB-804-805"]["hierarchy"] == {
        "family_children": [805, 829, 853, 859],
        "first_child_report_norm_id": 805,
        "last_descendant_report_norm_id": 861,
        "next_family_report_norm_id": 862,
    }


def test_typed_authority_and_content_tamper_fail_closed() -> None:
    forged = _persisted()
    forged["authority"]["project_owner_decisions_required"] = 1
    with pytest.raises(
        adjudication.ProjectOwnerTMAdjudicationsV1Error,
        match="identity or metrics",
    ):
        adjudication._validate(forged)

    forged = _persisted()
    forged["decisions"][0]["mapping"]["normalized_value"] += 1
    with pytest.raises(
        adjudication.ProjectOwnerTMAdjudicationsV1Error,
        match="content identity drifted",
    ):
        adjudication._validate(forged)


def test_coordinated_rehash_cannot_replace_live_replay(monkeypatch: pytest.MonkeyPatch) -> None:
    persisted = _persisted()
    forged = copy.deepcopy(persisted)
    forged["decisions"][0]["mapping"]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("adjudication_id")
    forged["adjudication_id"] = "e0067a:adjudication:" + adjudication.canonical_json_sha256_v1(
        material
    )
    monkeypatch.setattr(
        adjudication,
        "build_live_project_owner_tm_adjudications_v1",
        lambda: persisted,
    )
    with pytest.raises(
        adjudication.ProjectOwnerTMAdjudicationsV1Error,
        match="does not exact-replay",
    ):
        adjudication.validate_project_owner_tm_adjudications_replay_v1(forged)
