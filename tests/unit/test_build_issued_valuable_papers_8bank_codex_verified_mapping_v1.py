from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT / "scripts/experiments/build_issued_valuable_papers_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_issued_valuable_papers_8bank_codex_verified_mapping_v1", _PATH
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


def test_review_covers_one_unique_region_per_bank_and_general_layout_variants() -> None:
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
    assert sum(len(item["mappings"]) for item in documents) == 66
    assert sum(len(item["unmapped_source_rows"]) for item in documents) == 8
    assert {item["presentation"] for item in documents} >= {
        "SINGLE_PERIOD_BOOK_VALUE_AND_FACE_VALUE_COLUMNS",
        "TWO_ALTERNATE_VIEWS_WHOLE_FAMILY_TENOR_AND_INSTRUMENT_POPULATION",
        "VERTICAL_COMBINED_PROMISSORY_AND_BOND_PARENT_WITH_CURRENCY_TENORS",
        "HORIZONTAL_TENOR_ROWS_BY_INSTRUMENT_COLUMNS",
    }


def test_all_fixed_accounting_equations_close_and_dash_cells_are_zero() -> None:
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

    assert len(equations) == 36
    assert len(dash_refs) == 7
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
    forged["review_id"] = "e0076:pixel-review:" + builder.canonical_json_sha256_v1(material)

    with pytest.raises(
        builder.IssuedValuablePapers8BankCodexVerifiedMappingV1Error,
        match="differs from fixed ledger",
    ):
        builder._review(forged)


def test_current_persisted_artifact_matches_live_eight_document_build() -> None:
    persisted = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())
    rebuilt = builder.build_live_issued_valuable_papers_8bank_codex_verified_mapping_v1()

    assert rebuilt == persisted
    assert rebuilt["result_id"] == (
        "e0076:result:3f2e52c32b3e7a0dcbe2206354f20b3dc0e409bb9b27ee716fe6d1c85065d355"
    )
    assert rebuilt["metrics"] == {
        "accounting_equation_verified_count": 36,
        "authenticated_pixel_dash_zero_count": 4,
        "document_count": 8,
        "document_unique_region_count": 8,
        "mapping_verified_count": 66,
        "open_source_row_count": 8,
        "q1_source_period_caveat_document_count": 1,
        "verified_document_count": 8,
        "verified_value_cell_count": 124,
    }
