from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_long_term_investments_8bank_codex_verified_mapping_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_long_term_investments_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _persisted() -> dict[str, object]:
    return json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text("utf-8"))


def test_review_preserves_eight_pdf_variants_and_q1_caveat() -> None:
    review = builder._review_blueprint()

    assert [item["bank_code"] for item in review["documents"]] == list(
        builder.EXPECTED_DOCUMENT_ORDER
    )
    assert [item["page_sequence"] for item in review["documents"]] == [
        19,
        36,
        48,
        30,
        33,
        40,
        24,
        36,
    ]
    assert review["documents"][2]["source_period"] == "2026-03-31"
    assert review["documents"][3]["mappings"][0]["values"][0] == {
        "dash_anchor_line_index": 13,
        "line_index": None,
        "period_role": "CURRENT",
        "pixel_transcription": "-",
    }


def test_persisted_result_replays_pixels_accounting_and_live_schema() -> None:
    result = builder.validate_live_long_term_investments_8bank_codex_verified_mapping_v1(
        _persisted()
    )

    assert result["result_id"] == (
        "lti8bcv1:result:8f6878e02f92b4aee73ac971601e85d331b7484c0b964acc4ee5768152574bc2"
    )
    assert result["metrics"] == {
        "accounting_equation_verified_count": 9,
        "dash_cell_normalized_to_zero_count": 1,
        "document_count": 8,
        "document_unique_region_count": 8,
        "mapping_verified_count": 29,
        "q1_source_period_caveat_document_count": 1,
        "unresolved_document_count": 0,
        "verified_value_cell_count": 58,
    }
    assert all(
        trial["whole_document_uniqueness"]["complete_region_count"] == 1
        for trial in result["trials"]
    )
    hdb_associate = result["trials"][3]["verified_mappings"][0]
    assert hdb_associate["schema_binding"]["report_norm_id"] == 6067
    assert hdb_associate["values"][0]["normalized_value"] == 0
    assert hdb_associate["values"][0]["source_numeric_challenger"] is None
    assert result["trials"][2]["status"] == "VERIFIED_BY_CODEX_WITH_SUPPLIED_SOURCE_PERIOD_CAVEAT"


def test_review_and_result_coordinated_rehashes_do_not_authenticate() -> None:
    review = builder._review_blueprint()
    forged_review = copy.deepcopy(review)
    forged_review["documents"][0]["mappings"][0]["values"][0]["pixel_transcription"] = "999"
    material = copy.deepcopy(forged_review)
    material.pop("review_id")
    forged_review["review_id"] = "e0068:pixel-review:" + builder.canonical_json_sha256_v1(material)
    with pytest.raises(builder.LongTermInvestments8BankCodexVerifiedMappingV1Error, match="review"):
        builder._review(forged_review)

    forged = copy.deepcopy(_persisted())
    forged["trials"][0]["verified_mappings"][0]["values"][0]["normalized_value"] = 999
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "lti8bcv1:result:" + builder.canonical_json_sha256_v1(material)
    with pytest.raises(builder.LongTermInvestments8BankCodexVerifiedMappingV1Error, match="replay"):
        builder.validate_live_long_term_investments_8bank_codex_verified_mapping_v1(forged)


def test_schema_extension_is_exact_and_dash_is_zero() -> None:
    authority, by_id = builder._authority_snapshot(builder.PROJECT_ROOT)
    assert authority["schema_revision"] == "UNIVERSAL_BANK_BCTC_SCHEMA@6072"
    assert builder._schema_binding(by_id[6066], 6066)["schema_parent_report_norm_id"] == 862
    assert builder._schema_binding(by_id[6067], 6067)["schema_parent_report_norm_id"] == 862
    assert builder._normalized({"pixel_transcription": "-"}) == 0
