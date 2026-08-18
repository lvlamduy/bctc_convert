from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT
    / "scripts/experiments/build_annual_2025_interest_income_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_interest_income_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _persisted() -> dict[str, object]:
    return json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())


def test_review_covers_one_unique_annual_region_per_bank() -> None:
    review = builder.build_annual_2025_interest_income_pixel_review_blueprint_v1()
    assert [item["bank_code"] for item in review["documents"]] == [
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "VCB",
        "CTG",
        "BID",
        "VIB",
    ]
    assert [item["page_span"] for item in review["documents"]] == [
        [67, 67],
        [72, 72],
        [68, 68],
        [49, 49],
        [57, 57],
        [57, 57],
        [54, 54],
        [50, 50],
    ]
    assert all(item["source_period"] == "2025-12-31" for item in review["documents"])


def test_persisted_result_has_exact_annual_denominator_and_schema_sets() -> None:
    result = _persisted()
    assert result["metrics"] == builder._EXPECTED_METRICS
    for trial in result["trials"]:
        code = trial["document_provenance"]
        actual = {row["schema_binding"]["report_norm_id"] for row in trial["verified_mappings"]}
        assert actual == builder._EXPECTED_IDS[code]
        assert trial["status"] == "VERIFIED_BY_CODEX"
        assert trial["whole_document_uniqueness"]["status"] == "UNIQUE_FULL_MATCH"


def test_distinct_mbb_combined_loan_and_hdb_letter_of_credit_rows_are_not_narrowed() -> None:
    result = _persisted()
    mbb = next(item for item in result["trials"] if item["document_provenance"] == "MBB")
    hdb = next(item for item in result["trials"] if item["document_provenance"] == "HDB")
    combined = next(
        row for row in mbb["verified_mappings"] if row["schema_binding"]["report_norm_id"] == 6075
    )
    letter_of_credit = next(
        row for row in hdb["verified_mappings"] if row["schema_binding"]["report_norm_id"] == 6076
    )
    assert combined["label_evidence"]["pixel_transcription"] == (
        "Thu nhập lãi cho vay khách hàng và các TCTD khác"
    )
    assert {item["normalized_value"] for item in combined["values"]} == {
        70_324_550,
        54_446_408,
    }
    assert letter_of_credit["label_evidence"]["pixel_transcription"] == ("Thu phí nghiệp vụ L/C")
    assert {item["normalized_value"] for item in letter_of_credit["values"]} == {
        1_623_794,
        3_123_610,
    }


def test_hdb_visible_dash_is_bound_to_render_pixels_and_normalized_to_zero() -> None:
    hdb = next(item for item in _persisted()["trials"] if item["document_provenance"] == "HDB")
    purchased_debt = next(
        row for row in hdb["verified_mappings"] if row["schema_binding"]["report_norm_id"] == 1149
    )
    comparative = next(
        item for item in purchased_debt["values"] if item["axis_role"] == "COMPARATIVE_PERIOD"
    )
    assert comparative["normalized_value"] == 0
    assert comparative["pixel_transcription"] == "-"
    assert comparative["pixel_bbox"] == [1473, 1398, 1497, 1415]
    assert comparative["pixel_rgb_sha256"] == (
        "5b9b1268d293cfd2980052f48a7a316adcdb778a5e029ce0aedbaa8f5c9125f5"
    )
    assert comparative["fresh_vietocr_numeric_status"] == ("NO_VIETOCR_LINE_FOR_VISIBLE_DASH")


def test_every_visible_parent_and_subtotal_equation_closes_exactly() -> None:
    equations = [
        equation
        for trial in _persisted()["trials"]
        for equation in trial["verified_accounting_equations"]
    ]
    assert len(equations) == 28
    assert all(item["computed_value"] == item["visible_total"] for item in equations)
    assert all(item["status"] == "VERIFIED_EXACT" for item in equations)


def test_persisted_result_matches_exact_live_replay() -> None:
    rebuilt = builder.build_live_annual_2025_interest_income_8bank_codex_verified_mapping_v1()
    assert rebuilt == _persisted()
    assert rebuilt["result_id"] == (
        "annual2025ii8bcv1:result:9fa09b71e57307fe96c4593cddfd980522d0e4636e510f7926c4bc78a61e9aae"
    )
