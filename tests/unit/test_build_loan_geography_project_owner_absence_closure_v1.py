from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_loan_geography_project_owner_absence_closure_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_loan_geography_project_owner_absence_closure_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
closure = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = closure
_SPEC.loader.exec_module(closure)


def _persisted() -> dict[str, object]:
    return json.loads((closure.PROJECT_ROOT / closure.OUTPUT_PATH).read_text())


def test_owner_closure_preserves_broader_tables_as_six_absences() -> None:
    result = closure._validate(_persisted())
    by_bank = {decision["bank_provenance"]: decision for decision in result["decisions"]}

    assert list(by_bank) == ["ACB", "VPB", "HDB", "VCB", "CTG", "BID"]
    assert result["verified_present_banks"] == ["MBB", "VIB"]
    assert all(
        decision["status"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT"
        for decision in by_bank.values()
    )
    assert by_bank["VCB"]["source_scope_equations"] == []
    assert by_bank["VCB"]["source_surface_disposition"] == (
        "GEOGRAPHIC_SEGMENT_REPORT_NOT_CUSTOMER_LOAN_GEOGRAPHY"
    )
    assert {
        bank: decision["source_scope_equations"][0]["difference"]
        for bank, decision in by_bank.items()
        if bank != "VCB"
    } == {
        "ACB": 6392840,
        "VPB": 6848104,
        "HDB": 11439915,
        "CTG": 20241550,
        "BID": 12677150,
    }


def test_metrics_and_authority_keep_absence_report_bounded() -> None:
    result = closure._validate(_persisted())

    assert result["metrics"] == {
        "confirmed_absence_count": 6,
        "open_geography_review_count": 0,
        "verified_document_count": 2,
        "verified_mapping_count": 4,
    }
    assert result["authority"]["confirmed_absence_bounded_to_supplied_reports"] is True
    assert result["authority"]["other_report_or_broad_corpus_absence_authority"] is False
    assert result["authority"]["broader_total_loan_geography_relabelled_or_narrowed"] is False


def test_type_poison_and_coordinated_rehash_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forged = _persisted()
    forged["metrics"]["confirmed_absence_count"] = 6.0
    with pytest.raises(
        closure.LoanGeographyProjectOwnerAbsenceClosureV1Error,
        match="shape, authority, order, or metrics",
    ):
        closure._validate(forged)

    persisted = _persisted()
    forged = copy.deepcopy(persisted)
    forged["decisions"][0]["source_scope_equations"][0]["difference"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0067d:result:" + closure.canonical_json_sha256_v1(material)
    monkeypatch.setattr(closure, "_build", lambda: persisted)
    with pytest.raises(
        closure.LoanGeographyProjectOwnerAbsenceClosureV1Error,
        match="does not exact-replay",
    ):
        closure.validate_loan_geography_project_owner_absence_closure_replay_v1(forged)
