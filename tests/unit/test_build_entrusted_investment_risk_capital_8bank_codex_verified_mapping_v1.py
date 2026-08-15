from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT
    / "scripts/experiments/build_entrusted_investment_risk_capital_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_entrusted_investment_risk_capital_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def test_review_has_three_present_notes_and_five_bound_report_absences() -> None:
    documents = builder._review_blueprint()["documents"]
    present = [item for item in documents if item["disposition"] == "VERIFIED_BY_CODEX"]
    absent = [item for item in documents if item["disposition"] == "NOT_OBSERVED_IN_BOUND_REPORT"]

    assert [item["bank_code"] for item in present] == ["MBB", "VPB", "VIB"]
    assert [item["bank_code"] for item in absent] == ["ACB", "HDB", "VCB", "CTG", "BID"]
    assert all(len(item["boundary_evidence"]) == 2 for item in absent)
    assert sum(len(item["mappings"]) for item in present) == 6


def test_printed_repeated_total_equations_close_exactly() -> None:
    equations = [
        equation
        for document in builder._review_blueprint()["documents"]
        for equation in document["equations"]
    ]
    assert len(equations) == 4
    for equation in equations:
        computed = sum(
            builder.foundation.support._money(term["pixel_transcription"])
            for term in equation["terms"]
        )
        assert computed == builder.foundation.support._money(
            equation["total"]["pixel_transcription"]
        )


def test_review_rejects_coordinated_absence_promotion() -> None:
    review = builder._review_blueprint()
    forged = copy.deepcopy(review)
    acb = next(item for item in forged["documents"] if item["bank_code"] == "ACB")
    acb["disposition"] = "VERIFIED_BY_CODEX"
    material = copy.deepcopy(forged)
    material.pop("review_id")
    forged["review_id"] = "e0075:pixel-review:" + builder.canonical_json_sha256_v1(material)

    with pytest.raises(
        builder.EntrustedInvestmentRiskCapital8BankCodexVerifiedMappingV1Error,
        match="differs from the fixed ledger",
    ):
        builder._review(forged)


def test_current_persisted_artifact_matches_live_eight_document_build() -> None:
    persisted = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())
    rebuilt = builder.build_live_entrusted_investment_risk_capital_8bank_codex_verified_mapping_v1()

    assert rebuilt == persisted
    assert rebuilt["result_id"] == (
        "e0075:result:0db6581faaa35546d034524d07fb58b09a0f2e8267f8a73f335fd024a10352c5"
    )
    assert rebuilt["metrics"] == {
        "accounting_equation_verified_count": 4,
        "bounded_report_absence_count": 5,
        "document_count": 8,
        "document_unique_region_count": 3,
        "mapping_verified_count": 6,
        "open_source_row_count": 0,
        "q1_source_period_caveat_document_count": 1,
        "verified_document_count": 3,
        "verified_value_cell_count": 12,
    }
