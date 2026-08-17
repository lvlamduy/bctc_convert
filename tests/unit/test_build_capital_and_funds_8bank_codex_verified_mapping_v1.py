from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_capital_and_funds_8bank_codex_verified_mapping_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_capital_and_funds_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _amount(ref: dict[str, object]) -> int:
    value = builder.foundation.support._money(ref["pixel_transcription"])
    assert type(value) is int
    return value * ref["multiplier"]


def test_review_covers_all_eight_banks_and_keeps_rotated_numbers_unresolved() -> None:
    documents = builder._review_blueprint()["documents"]

    assert [item["bank_code"] for item in documents] == [
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "VCB",
        "CTG",
        "BID",
        "VIB",
    ]
    assert sum(len(item["mappings"]) for item in documents) == 65
    assert sum(len(item["equations"]) for item in documents) == 20
    assert sum(len(item["unmapped_source_rows"]) for item in documents) == 10
    assert [
        item["bank_code"]
        for item in documents
        if item["disposition"] == "STRUCTURE_VERIFIED_NUMERIC_MAPPING_UNRESOLVED"
    ] == ["BID", "VIB"]


def test_all_fixed_accounting_equations_close() -> None:
    equations = [
        equation
        for document in builder._review_blueprint()["documents"]
        for equation in document["equations"]
    ]

    assert len(equations) == 20
    for equation in equations:
        assert sum(_amount(term) for term in equation["terms"]) == _amount(equation["total"])


def test_review_rejects_coordinated_rotated_numeric_promotion() -> None:
    review = builder._review_blueprint()
    forged = copy.deepcopy(review)
    bid = next(item for item in forged["documents"] if item["bank_code"] == "BID")
    bid["disposition"] = "VERIFIED_BY_CODEX"
    bid["unmapped_source_rows"] = []
    material = copy.deepcopy(forged)
    material.pop("review_id")
    forged["review_id"] = "e0078:pixel-review:" + builder.canonical_json_sha256_v1(material)

    with pytest.raises(
        builder.CapitalAndFunds8BankCodexVerifiedMappingV1Error,
        match="differs from the fixed ledger",
    ):
        builder._review(forged)


def test_current_persisted_artifact_matches_live_eight_document_build() -> None:
    persisted = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())
    rebuilt = builder.build_live_capital_and_funds_8bank_codex_verified_mapping_v1()

    assert rebuilt == persisted
    assert rebuilt["result_id"] == (
        "e0078:result:64836d56055fbb6f6aa74a0986585047520a76ca117af8a058e334d3d228db5f"
    )
    assert rebuilt["metrics"] == {
        "accounting_equation_verified_count": 20,
        "document_count": 8,
        "document_unique_region_count": 8,
        "mapping_verified_count": 65,
        "numeric_mapping_unresolved_document_count": 2,
        "open_source_row_count": 10,
        "q1_source_period_caveat_document_count": 1,
        "rotated_structural_document_count": 2,
        "verified_value_cell_count": 131,
    }


def test_result_shape_rejects_open_row_status_promotion() -> None:
    value = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())
    forged = copy.deepcopy(value)
    row = forged["trials"][2]["unmapped_source_rows"][0]
    row["status"] = "VERIFIED_BY_CODEX"
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0078:result:" + builder.canonical_json_sha256_v1(material)

    with pytest.raises(
        builder.CapitalAndFunds8BankCodexVerifiedMappingV1Error,
        match="trial shape or status drifted",
    ):
        builder._validate_result(forged)
