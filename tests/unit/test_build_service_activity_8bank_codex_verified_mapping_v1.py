from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_service_activity_8bank_codex_verified_mapping_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_service_activity_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _result() -> dict[str, object]:
    return json.loads((_ROOT / builder.RESULT_PATH).read_text())


def test_review_separates_detailed_notes_from_negative_controls() -> None:
    review = builder._review_blueprint()
    assert [document["bank_code"] for document in review["documents"]] == [
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "VCB",
        "CTG",
        "BID",
        "VIB",
    ]
    assert [document["page_span"] for document in review["documents"]] == [
        None,
        [46, 46],
        [62, 62],
        None,
        None,
        None,
        None,
        [45, 45],
    ]


def test_persisted_result_has_exact_verified_denominator() -> None:
    result = builder._validate_result(_result())
    assert result["metrics"] == {
        "accounting_equation_verified_count": 18,
        "authenticated_pixel_dash_zero_count": 2,
        "detailed_note_not_present_document_count": 5,
        "document_count": 8,
        "document_unique_region_count": 3,
        "fresh_vietocr_numeric_disagreement_count": 0,
        "mapping_verified_count": 43,
        "open_source_row_count": 0,
        "q1_source_period_caveat_document_count": 1,
        "verified_value_cell_count": 86,
    }


def test_mbb_consulting_dashes_are_pixel_bound_zero() -> None:
    mbb = _result()["trials"][1]
    consulting = next(
        mapping
        for mapping in mbb["verified_mappings"]
        if mapping["schema_binding"]["report_norm_id"] == 5987
    )
    assert [value["normalized_value"] for value in consulting["values"]] == [0, 0]
    assert all(
        value["source_numeric_challenger_status"]
        == "VISIBLE_AUTHENTICATED_PIXEL_DASH_NOT_DETECTED_AS_SOURCE_LINE"
        for value in consulting["values"]
    )


def test_public_replay_rejects_coordinated_value_tamper() -> None:
    forged = copy.deepcopy(_result())
    forged["trials"][1]["verified_mappings"][0]["values"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0082:result:" + builder.canonical_json_sha256_v1(material)
    with pytest.raises(
        builder.ServiceActivity8BankCodexVerifiedMappingV1Error,
        match="replay exactly",
    ):
        builder.validate_live_service_activity_8bank_codex_verified_mapping_v1(forged)
