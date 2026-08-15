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
    / "scripts/experiments/build_other_payables_liabilities_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_other_payables_liabilities_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _amount(ref: dict[str, object]) -> int:
    if ref["kind"] == "AUTHENTICATED_RENDER_PIXEL_DASH":
        return 0
    value = builder.foundation.support._money(ref["pixel_transcription"])
    assert type(value) is int
    return value * ref["multiplier"]


def test_review_covers_all_banks_and_optional_layout_variants() -> None:
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
    assert sum(len(item["mappings"]) for item in documents) == 39
    assert sum(len(item["unmapped_source_rows"]) for item in documents) == 18
    assert next(item for item in documents if item["bank_code"] == "VPB")[
        "presentation"
    ].startswith("BROAD_OTHER_LIABILITIES_OWNER_THEN_NESTED")
    assert next(item for item in documents if item["bank_code"] == "VIB")[
        "presentation"
    ].startswith("BROAD_OWNER_WITH_INTEREST_INTERNAL_AND_EXTERNAL")


def test_all_fixed_accounting_equations_close_and_acb_dashes_are_zero() -> None:
    documents = builder._review_blueprint()["documents"]
    equations = [equation for document in documents for equation in document["equations"]]
    dash_refs = [
        ref
        for document in documents
        for mapping in document["mappings"]
        for refs in mapping["values"].values()
        for ref in refs
        if ref["kind"] == "AUTHENTICATED_RENDER_PIXEL_DASH"
    ]

    assert len(equations) == 28
    assert len(dash_refs) == 2
    for equation in equations:
        assert sum(_amount(term) for term in equation["terms"]) == _amount(equation["total"])
    assert all(_amount(ref) == 0 for ref in dash_refs)


def test_review_rejects_coordinated_open_row_promotion() -> None:
    review = builder._review_blueprint()
    forged = copy.deepcopy(review)
    acb = next(item for item in forged["documents"] if item["bank_code"] == "ACB")
    acb["unmapped_source_rows"] = []
    acb["disposition"] = "VERIFIED_BY_CODEX"
    material = copy.deepcopy(forged)
    material.pop("review_id")
    forged["review_id"] = "e0077:pixel-review:" + builder.canonical_json_sha256_v1(material)

    with pytest.raises(
        builder.OtherPayablesLiabilities8BankCodexVerifiedMappingV1Error,
        match="differs from the fixed ledger",
    ):
        builder._review(forged)


def test_current_persisted_artifact_matches_live_eight_document_build() -> None:
    persisted = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())
    rebuilt = builder.build_live_other_payables_liabilities_8bank_codex_verified_mapping_v1()

    assert rebuilt == persisted
    assert rebuilt["result_id"] == (
        "e0077:result:489111c8ab70038c0004e1a8242fa2c7e96b405d3e59fdfa0b5878d9414db912"
    )
    assert rebuilt["metrics"] == {
        "accounting_equation_verified_count": 28,
        "authenticated_pixel_dash_zero_count": 2,
        "document_count": 8,
        "document_unique_region_count": 8,
        "mapping_verified_count": 39,
        "open_source_row_count": 18,
        "q1_source_period_caveat_document_count": 1,
        "verified_value_cell_count": 78,
    }
