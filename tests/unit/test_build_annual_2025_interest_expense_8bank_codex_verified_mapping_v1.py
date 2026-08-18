from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT
    / "scripts/experiments/build_annual_2025_interest_expense_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_interest_expense_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _persisted() -> dict[str, object]:
    return json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())


def test_review_covers_one_unique_annual_region_per_bank() -> None:
    review = builder.build_annual_2025_interest_expense_pixel_review_blueprint_v1()
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
        [58, 58],
        [57, 57],
        [55, 55],
        [50, 50],
    ]
    assert all(item["source_period"] == "2025-12-31" for item in review["documents"])


def test_persisted_result_has_exact_annual_denominator_and_schema_sets() -> None:
    result = _persisted()
    assert result["metrics"] == builder._EXPECTED_METRICS
    for trial in result["trials"]:
        actual = {row["schema_binding"]["report_norm_id"] for row in trial["verified_mappings"]}
        assert actual == builder._EXPECTED_IDS[trial["document_provenance"]]
        assert trial["status"] == "VERIFIED_BY_CODEX"
        assert trial["whole_document_uniqueness"]["status"] == "UNIQUE_FULL_MATCH"
        assert trial["finance_lease_interest_disposition"] == (
            "NOT_OBSERVED_IN_BOUND_DISCLOSURE_REGION"
        )


def test_ctg_compact_labels_are_bound_only_inside_the_complete_expense_graph() -> None:
    ctg = next(item for item in _persisted()["trials"] if item["document_provenance"] == "CTG")
    labels = {
        row["schema_binding"]["report_norm_id"]: row["label_evidence"]["pixel_transcription"]
        for row in ctg["verified_mappings"]
    }
    assert labels[1152] == "Lãi tiền gửi"
    assert labels[1153] == "Lãi tiền vay"
    assert ctg["whole_document_uniqueness"] == {
        "complete_region_count": 1,
        "status": "UNIQUE_FULL_MATCH",
    }


def test_hdb_punctuation_error_keeps_raw_vietocr_and_source_numeric_value() -> None:
    hdb = next(item for item in _persisted()["trials"] if item["document_provenance"] == "HDB")
    deposit = next(
        row for row in hdb["verified_mappings"] if row["schema_binding"]["report_norm_id"] == 1152
    )
    current = next(value for value in deposit["values"] if value["axis_role"] == "CURRENT_PERIOD")
    assert current["fresh_vietocr_numeric_proposal"] == "26,150.925"
    assert current["source_numeric_challenger"] == "26.150.925"
    assert current["normalized_value"] == 26_150_925
    assert current["fresh_vietocr_numeric_status"] == "MATCHES_SOURCE_NUMERIC_CHALLENGER"


def test_vib_provider_order_does_not_detach_values_from_same_geometry_rows() -> None:
    vib = next(item for item in _persisted()["trials"] if item["document_provenance"] == "VIB")
    issued = next(
        row for row in vib["verified_mappings"] if row["schema_binding"]["report_norm_id"] == 1154
    )
    other = next(
        row for row in vib["verified_mappings"] if row["schema_binding"]["report_norm_id"] == 1156
    )
    assert issued["topology"] == "SAME_ROW_GEOMETRY_VALUE_BEFORE_PROVIDER_LABEL_ORDER"
    assert {value["normalized_value"] for value in issued["values"]} == {
        -1_553_581,
        -1_112_775,
    }
    assert {value["normalized_value"] for value in other["values"]} == {-26_770, -33_675}


def test_every_parent_equation_closes_and_persisted_result_replays() -> None:
    persisted = _persisted()
    equations = [
        equation
        for trial in persisted["trials"]
        for equation in trial["verified_accounting_equations"]
    ]
    assert len(equations) == 16
    assert all(item["computed_value"] == item["visible_total"] for item in equations)
    assert all(item["status"] == "VERIFIED_EXACT" for item in equations)
    rebuilt = builder.build_live_annual_2025_interest_expense_8bank_codex_verified_mapping_v1()
    assert rebuilt == persisted
    assert rebuilt["result_id"] == (
        "annual2025ie8bcv1:result:589f04febda44b6646d414c8ef08164c271ed31cf7f0ced1b25460a5000a5ea7"
    )
