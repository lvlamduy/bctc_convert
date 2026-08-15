from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_interest_income_8bank_codex_verified_mapping_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_interest_income_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _result() -> dict[str, object]:
    return json.loads((_ROOT / builder.RESULT_PATH).read_text())


def test_review_covers_the_unique_region_in_all_eight_documents() -> None:
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
        [24, 24],
        [46, 46],
        [62, 62],
        [34, 34],
        [38, 38],
        [45, 45],
        [28, 28],
        [45, 45],
    ]
    assert review["documents"][-1]["presentation"] == "LEADING_PARENT_TOTAL_BEFORE_CHILDREN"


def test_persisted_result_has_exact_verified_denominator() -> None:
    result = builder._validate_result(_result())
    assert result["metrics"] == {
        "accounting_equation_verified_count": 28,
        "document_count": 8,
        "document_unique_region_count": 8,
        "fresh_vietocr_numeric_disagreement_count": 2,
        "mapping_verified_count": 54,
        "open_source_row_count": 0,
        "q1_source_period_caveat_document_count": 1,
        "terminal_source_numeric_challenger_document_count": 1,
        "verified_value_cell_count": 108,
    }
    assert all(
        equation["status"] == "VERIFIED_EXACT"
        for trial in result["trials"]
        for equation in trial["verified_accounting_equations"]
    )


def test_vib_dropped_leading_digits_are_not_used_as_numeric_truth() -> None:
    vib = _result()["trials"][-1]
    by_id = {
        mapping["schema_binding"]["report_norm_id"]: mapping for mapping in vib["verified_mappings"]
    }
    deposit_current = next(
        value for value in by_id[1144]["values"] if value["axis_role"] == "CURRENT_PERIOD"
    )
    securities_comparative = next(
        value for value in by_id[1146]["values"] if value["axis_role"] == "COMPARATIVE_PERIOD"
    )
    assert (
        deposit_current["fresh_vietocr_numeric_proposal"],
        deposit_current["normalized_value"],
    ) == (
        "293.978",
        1_293_978,
    )
    assert (
        securities_comparative["fresh_vietocr_numeric_proposal"],
        securities_comparative["normalized_value"],
    ) == ("357.506", 1_357_506)
    assert deposit_current["source_numeric_challenger"] == "1.293.978"
    assert securities_comparative["source_numeric_challenger"] == "1.357.506"


def test_terminal_vcb_uses_bound_provider_numeric_axis_not_vietocr_as_truth() -> None:
    vcb = _result()["trials"][4]
    assert vcb["source_geometry_mode"] == (
        "TERMINAL_EXPERIMENT_LOCAL_PROVIDER_LINE_GEOMETRY_ONLY_V1"
    )
    assert all(
        value["source_numeric_challenger_status"] == "MATCHED_VISIBLE_PIXEL_TRANSCRIPTION"
        for mapping in vcb["verified_mappings"]
        for value in mapping["values"]
    )


def test_public_replay_rejects_coordinated_value_tamper() -> None:
    forged = copy.deepcopy(_result())
    forged["trials"][0]["verified_mappings"][0]["values"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0079:result:" + builder.canonical_json_sha256_v1(material)
    with pytest.raises(
        builder.InterestIncome8BankCodexVerifiedMappingV1Error,
        match="replay exactly",
    ):
        builder.validate_live_interest_income_8bank_codex_verified_mapping_v1(forged)
