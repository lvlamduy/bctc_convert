from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT / "scripts/experiments/"
    "build_annual_2025_service_activity_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_service_activity_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)

_ORDER = ["ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB"]
_PAGES = [[67, 67], [72, 72], [69, 69], [50, 50], [58, 58], [58, 58], [55, 55], [50, 50]]


def _persisted() -> dict[str, object]:
    return json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())


def _review() -> dict[str, object]:
    return json.loads((builder.PROJECT_ROOT / builder.REVIEW_PATH).read_text())


def _trial(code: str) -> dict[str, object]:
    return next(item for item in _persisted()["trials"] if item["document_provenance"] == code)


def test_review_covers_exact_unique_service_region_in_all_eight_complete_pdfs() -> None:
    review = _review()
    assert review["scan_id"] == builder.EXPECTED_SCAN_ID
    assert [item["bank_code"] for item in review["documents"]] == _ORDER
    assert [item["page_span"] for item in review["documents"]] == _PAGES
    assert all(item["source_period"] == "2025-12-31" for item in review["documents"])
    assert review["documents"][0]["presentation"] == (
        "ORDERED_INCOME_EXPENSE_SIBLING_NOTES_WITH_CROSS_PAGE_STATEMENT_NET"
    )
    assert review["documents"][3]["presentation"] == (
        "LEADING_TOTALS_GENERIC_EXPENSE_PREPOSITION_UNLABELLED_TRAILING_NET"
    )


def test_persisted_result_has_exact_denominators_and_schema_bindings() -> None:
    result = _persisted()
    assert result["metrics"] == builder._EXPECTED_METRICS
    assert [item["document_provenance"] for item in result["trials"]] == _ORDER
    assert [item["page_span"] for item in result["trials"]] == _PAGES
    for trial in result["trials"]:
        code = trial["document_provenance"]
        assert {
            row["schema_binding"]["report_norm_id"] for row in trial["verified_mappings"]
        } == builder._EXPECTED_REPORT_NORM_IDS[code]
        assert trial["whole_document_uniqueness"] == {
            "complete_region_count": 1,
            "status": "UNIQUE_FULL_MATCH",
        }


def test_all_income_expense_and_net_equations_close_exactly() -> None:
    result = _persisted()
    equations = [
        equation
        for trial in result["trials"]
        for equation in trial["verified_accounting_equations"]
    ]
    assert len(equations) == 48
    assert all(item["status"] == "CORROBORATED_EXACT" for item in equations)
    for trial in result["trials"]:
        mapped = {
            row["schema_binding"]["report_norm_id"]: {
                value["axis_role"]: value["normalized_value"] for value in row["values"]
            }
            for row in trial["verified_mappings"]
        }
        for equation in trial["verified_accounting_equations"]:
            assert (
                equation["computed_value"]
                == mapped[equation["total_report_norm_id"]][equation["period_role"]]
            )


def test_acb_sibling_notes_reconcile_positive_expense_magnitudes_to_statement_net() -> None:
    acb = _trial("ACB")
    expense = next(row for row in acb["verified_mappings"] if row["role"] == "EXPENSE_PARENT")
    net = next(row for row in acb["verified_mappings"] if row["role"] == "NET_SERVICE_ACTIVITY")
    assert expense["topology"] == "TRAILING_UNLABELED_POSITIVE_MAGNITUDE_PARENT_TOTAL"
    assert {value["page_sequence"] for value in expense["values"]} == {67}
    assert net["topology"] == "CROSS_PAGE_CONSOLIDATED_INCOME_STATEMENT_RECONCILIATION"
    assert {value["page_sequence"] for value in net["values"]} == {10}
    assert {value["axis_role"]: value["normalized_value"] for value in net["values"]} == {
        "CURRENT_PERIOD": 3_146_740,
        "COMPARATIVE_PERIOD": 3_238_785,
    }


def test_ctg_combined_rows_are_source_only_and_still_close_parent_equations() -> None:
    ctg = _trial("CTG")
    assert ctg["status"] == "VERIFIED_BY_CODEX_WITH_SOURCE_SCHEMA_GAPS"
    assert [row["gap_id"] for row in ctg["verified_source_only_rows"]] == [
        "SA-CTG-001",
        "SA-CTG-002",
    ]
    assert [
        row["label_evidence"]["pixel_transcription"] for row in ctg["verified_source_only_rows"]
    ] == [
        "Thu từ dịch vụ tư vấn, ủy thác và đại lý",
        "Chi về dịch vụ tư vấn, ủy thác và đại lý",
    ]
    assert [
        {value["axis_role"]: value["normalized_value"] for value in row["values"]}
        for row in ctg["verified_source_only_rows"]
    ] == [
        {"CURRENT_PERIOD": 965_390, "COMPARATIVE_PERIOD": 961_413},
        {"CURRENT_PERIOD": -309_758, "COMPARATIVE_PERIOD": -195_158},
    ]
    equations_with_gaps = [
        item for item in ctg["verified_accounting_equations"] if "source_only_roles" in item
    ]
    assert [item["source_only_roles"] for item in equations_with_gaps] == [
        ["INCOME_COMBINED_CONSULTING_TRUST_AGENCY"],
        ["EXPENSE_COMBINED_CONSULTING_TRUST_AGENCY"],
        ["INCOME_COMBINED_CONSULTING_TRUST_AGENCY"],
        ["EXPENSE_COMBINED_CONSULTING_TRUST_AGENCY"],
    ]


def test_fresh_vietocr_numeric_disagreements_are_retained_not_dropped() -> None:
    disagreements = []
    for trial in _persisted()["trials"]:
        for row in trial["verified_mappings"] + trial["verified_source_only_rows"]:
            for value in row["values"]:
                if value["fresh_vietocr_numeric_status"] == (
                    "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
                ):
                    disagreements.append(
                        (
                            trial["document_provenance"],
                            row["role"],
                            value["fresh_vietocr_numeric_proposal"],
                            value["pixel_transcription"],
                            value["normalized_value"],
                        )
                    )
    assert disagreements == [
        ("HDB", "EXPENSE_OTHER", "73.409)", "(73.409)", -73_409),
        ("VIB", "INCOME_INSURANCE", "993 178", "993.178", 993_178),
    ]


def test_exact_result_pins_reject_mapped_id_or_metric_drift() -> None:
    tampered = copy.deepcopy(_persisted())
    tampered["metrics"]["mapping_verified_count"] -= 1
    try:
        builder._assert_result(tampered)
    except builder.Annual2025ServiceActivity8BankError:
        pass
    else:
        raise AssertionError("annual service-activity metric drift was accepted")

    tampered = copy.deepcopy(_persisted())
    tampered["trials"][0]["verified_mappings"][0]["schema_binding"]["report_norm_id"] = 999999
    try:
        builder._assert_result(tampered)
    except builder.Annual2025ServiceActivity8BankError:
        pass
    else:
        raise AssertionError("annual service-activity schema-binding drift was accepted")


def test_persisted_result_exactly_live_replays() -> None:
    rebuilt = builder.build_live_annual_2025_service_activity_8bank_codex_verified_mapping_v1()
    assert rebuilt == _persisted()
    assert rebuilt["result_id"] == (
        "annual2025sa8bcv1:result:32d6f1dc2b7f7a32beacf78185b35e5bb70f93796abfd1f31a0b128862740efe"
    )
