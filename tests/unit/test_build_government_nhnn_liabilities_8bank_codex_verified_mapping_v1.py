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
    / "scripts/experiments/build_government_nhnn_liabilities_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_government_nhnn_liabilities_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def test_fixed_review_maps_sure_rows_and_retains_every_open_row() -> None:
    review = builder._review_blueprint()
    documents = {item["bank_code"]: item for item in review["documents"]}

    assert sum(len(item["mappings"]) for item in documents.values()) == 28
    assert sum(len(item["equations"]) for item in documents.values()) == 28
    assert [
        item["item_id"]
        for document in review["documents"]
        for item in document["unmapped_source_rows"]
    ] == [f"GN-{ordinal:03d}" for ordinal in range(1, 5)]
    assert documents["BID"]["unit_authority"] == "DOCUMENT_LEVEL_MILLION_VND_INHERITED_TO_NOTE"


def test_all_reviewed_accounting_equations_close_and_dash_means_zero() -> None:
    dash_count = 0
    for document in builder._review_blueprint()["documents"]:
        for equation in document["equations"]:
            computed = sum(
                term["multiplier"] * builder.support._money(term["pixel_transcription"])
                for term in equation["terms"]
            )
            assert computed == builder.support._money(equation["total"]["pixel_transcription"])
            dash_count += sum(
                term["kind"] == "AUTHENTICATED_RENDER_PIXEL_DASH" for term in equation["terms"]
            )
    assert dash_count == 2


def test_review_rejects_coordinated_unresolved_promotion() -> None:
    review = builder._review_blueprint()
    forged = copy.deepcopy(review)
    acb = next(item for item in forged["documents"] if item["bank_code"] == "ACB")
    acb["unmapped_source_rows"][0]["status"] = "VERIFIED_BY_CODEX"
    material = copy.deepcopy(forged)
    material.pop("review_id")
    forged["review_id"] = "e0074:pixel-review:" + builder.canonical_json_sha256_v1(material)

    with pytest.raises(
        builder.GovernmentNHNNLiabilities8BankCodexVerifiedMappingV1Error,
        match="differs from the fixed ledger",
    ):
        builder._review(forged)


def test_historical_persisted_artifact_remains_byte_frozen_for_owner_closure() -> None:
    persisted = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())
    validated = builder._validate_result(persisted)

    assert validated == persisted
    assert validated["result_id"] == (
        "e0074:result:dbdaea017840adae9c66a8b7fdc69099e0ec591c7f6b351aa4d4a56fad65565e"
    )
    assert validated["metrics"] == {
        "accounting_equation_verified_count": 28,
        "authenticated_pixel_dash_zero_count": 2,
        "document_count": 8,
        "document_unique_region_count": 8,
        "mapping_verified_count": 28,
        "open_source_row_count": 4,
        "q1_source_period_caveat_document_count": 1,
        "verified_value_cell_count": 58,
    }
