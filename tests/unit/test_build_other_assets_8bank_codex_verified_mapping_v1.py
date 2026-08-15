from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_other_assets_8bank_codex_verified_mapping_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_other_assets_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def test_fixed_review_maps_sure_rows_and_retains_every_open_row() -> None:
    review = builder._review_blueprint()
    documents = {item["bank_code"]: item for item in review["documents"]}

    assert sum(len(item["mappings"]) for item in documents.values()) == 58
    assert sum(len(item["equations"]) for item in documents.values()) == 30
    assert [
        item["item_id"]
        for document in review["documents"]
        for item in document["unmapped_source_rows"]
    ] == [f"OA-{ordinal:03d}" for ordinal in range(1, 13)]
    assert {
        code
        for code, item in documents.items()
        if item["disposition"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT"
    } == {"ACB", "HDB", "VCB", "CTG", "BID"}


def test_all_reviewed_accounting_equations_close_before_artifact_build() -> None:
    for document in builder._review_blueprint()["documents"]:
        for equation in document["equations"]:
            computed = sum(
                term["multiplier"] * builder.support._money(term["pixel_transcription"])
                for term in equation["terms"]
            )
            assert computed == builder.support._money(equation["total"]["pixel_transcription"])


def test_review_rejects_coordinated_mapping_promotion() -> None:
    review = builder._review_blueprint()
    forged = copy.deepcopy(review)
    vp = next(item for item in forged["documents"] if item["bank_code"] == "VPB")
    vp["unmapped_source_rows"][0]["status"] = "VERIFIED_BY_CODEX"
    material = copy.deepcopy(forged)
    material.pop("review_id")
    forged["review_id"] = "e0073:pixel-review:" + builder.canonical_json_sha256_v1(material)

    with pytest.raises(
        builder.OtherAssets8BankCodexVerifiedMappingV1Error, match="differs from the fixed ledger"
    ):
        builder._review(forged)


def test_current_persisted_artifact_matches_live_eight_document_build() -> None:
    persisted = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())
    rebuilt = builder.build_live_other_assets_8bank_codex_verified_mapping_v1()

    assert rebuilt == persisted
    assert rebuilt["result_id"] == (
        "e0073:result:13f70a2aef91b31af106fbc0c64701856d4b8ffbde2d8a09a9e948e4df61ec94"
    )
    assert rebuilt["metrics"] == {
        "accounting_equation_verified_count": 30,
        "confirmed_bound_report_absence_count": 5,
        "document_count": 8,
        "document_unique_region_count": 3,
        "mapping_verified_count": 58,
        "open_source_row_count": 12,
        "q1_source_period_caveat_document_count": 1,
        "verified_value_cell_count": 126,
    }
