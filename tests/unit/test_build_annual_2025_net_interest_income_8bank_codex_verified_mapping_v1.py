from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT
    / "scripts/experiments/build_annual_2025_net_interest_income_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_net_interest_income_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)

_ORDER = ["ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB"]
_PAGES = [10, 13, 12, 10, 11, 11, 12, 11]
_EXPECTED_VALUES = {
    "ACB": {"CURRENT_PERIOD": 26_905_695, "COMPARATIVE_PERIOD": 27_794_702},
    "MBB": {"CURRENT_PERIOD": 51_610_117, "COMPARATIVE_PERIOD": 41_152_219},
    "VPB": {"CURRENT_PERIOD": 58_662_713, "COMPARATIVE_PERIOD": 50_002_402},
    "HDB": {"CURRENT_PERIOD": 34_746_190, "COMPARATIVE_PERIOD": 30_857_076},
    "VCB": {"CURRENT_PERIOD": 58_771_410, "COMPARATIVE_PERIOD": 55_405_735},
    "CTG": {"CURRENT_PERIOD": 66_453_245, "COMPARATIVE_PERIOD": 62_402_794},
    "BID": {"CURRENT_PERIOD": 63_295_106, "COMPARATIVE_PERIOD": 58_002_978},
    "VIB": {"CURRENT_PERIOD": 16_092_160, "COMPARATIVE_PERIOD": 16_750_412},
}


def _persisted() -> dict[str, object]:
    return json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())


def _semantic_index() -> dict[str, object]:
    return json.loads((builder.PROJECT_ROOT / builder.SEMANTIC_INDEX_PATH).read_text())


def test_review_covers_exact_statement_rows_for_all_eight_banks() -> None:
    review = builder.build_annual_2025_net_interest_income_pixel_review_blueprint_v1()
    persisted_review = json.loads((builder.PROJECT_ROOT / builder.REVIEW_PATH).read_text())
    assert persisted_review == review
    assert [item["document_provenance"] for item in review["documents"]] == _ORDER
    assert [item["page_sequence"] for item in review["documents"]] == _PAGES
    assert all(item["source_period"] == "2025-12-31" for item in review["documents"])
    assert all(
        [row["role"] for row in item["rows"]]
        == ["STATEMENT_INTEREST_INCOME", "STATEMENT_INTEREST_EXPENSE", "NET_INTEREST_INCOME"]
        for item in review["documents"]
    )


def test_bank_blind_whole_pdf_scan_finds_one_complete_statement_graph_each() -> None:
    scan = builder.build_annual_2025_net_interest_statement_scan_v1(_semantic_index())
    assert scan["metrics"] == {
        "document_count": 8,
        "document_unique_region_count": 8,
        "page_count_scanned": 695,
    }
    assert [trial["regions"][0]["page_sequence"] for trial in scan["trials"]] == _PAGES
    assert all(
        trial["uniqueness"] == {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
        for trial in scan["trials"]
    )


def test_text_anchor_without_statement_context_does_not_create_a_match() -> None:
    semantic_index = _semantic_index()
    acb = semantic_index["documents"][0]
    page = next(item for item in acb["pages"] if item["physical_page"] == 10)
    heading = next(item for item in page["lines"] if item["source_line_index"] == 2)
    heading["vietocr_text"] = "Thuyết minh báo cáo tài chính"
    scan = builder.build_annual_2025_net_interest_statement_scan_v1(semantic_index)
    assert scan["trials"][0]["regions"] == []
    assert scan["trials"][0]["uniqueness"] == {
        "complete_region_count": 0,
        "status": "UNRESOLVED_NOT_UNIQUE",
    }
    assert scan["metrics"]["document_unique_region_count"] == 7


def test_persisted_result_maps_only_5985_and_has_exact_values() -> None:
    result = _persisted()
    assert result["metrics"] == {
        "accounting_equation_verified_count": 48,
        "document_count": 8,
        "document_unique_region_count": 8,
        "fresh_vietocr_numeric_disagreement_count": 0,
        "mapping_verified_count": 8,
        "open_source_row_count": 0,
        "verified_value_cell_count": 16,
    }
    assert result["schema_family"]["mapped_report_norm_ids"] == [5985]
    assert result["schema_family"]["formula_component_report_norm_ids"] == [1143, 1151]
    for trial in result["trials"]:
        assert trial["status"] == "VERIFIED_BY_CODEX"
        assert trial["verified_mapping"]["schema_binding"]["report_norm_id"] == 5985
        assert {
            value["axis_role"]: value["normalized_value"]
            for value in trial["verified_mapping"]["values"]
        } == _EXPECTED_VALUES[trial["document_provenance"]]


def test_every_statement_tm_and_net_equation_closes_exactly() -> None:
    result = _persisted()
    equations = [
        equation
        for trial in result["trials"]
        for equation in trial["verified_accounting_equations"]
    ]
    assert len(equations) == 48
    assert all(item["computed_value"] == item["visible_total"] for item in equations)
    assert all(item["status"] == "VERIFIED_EXACT" for item in equations)
    formula_equations = [
        item for item in equations if item["name"] == "TM_5985_EQUALS_1143_PLUS_VISIBLE_SIGNED_1151"
    ]
    assert len(formula_equations) == 16
    assert all(
        item["formula_component_report_norm_ids"] == [1143, 1151] for item in formula_equations
    )


def test_vib_geometry_keeps_values_bound_when_provider_order_precedes_labels() -> None:
    vib = next(trial for trial in _persisted()["trials"] if trial["document_provenance"] == "VIB")
    assert vib["verified_mapping"]["topology"] == (
        "GEOMETRY_ROW_BINDING_WITH_PROVIDER_VALUE_BEFORE_LABEL_ORDER"
    )
    income = vib["statement_component_evidence"]["interest_income"]
    expense = vib["statement_component_evidence"]["interest_expense"]
    assert income["label_evidence"]["line_index"] == 12
    assert {value["source_line_index"] for value in income["values"]} == {10, 11}
    assert expense["label_evidence"]["line_index"] == 15
    assert {value["source_line_index"] for value in expense["values"]} == {13, 14}


def test_result_identity_rejects_uncoordinated_value_tamper() -> None:
    tampered = copy.deepcopy(_persisted())
    tampered["trials"][0]["verified_mapping"]["values"][0]["normalized_value"] += 1
    try:
        builder._validate_result(tampered)
    except builder.Annual2025NetInterestIncome8BankError:
        pass
    else:
        raise AssertionError("uncoordinated annual net-interest tamper was accepted")


def test_persisted_result_exactly_live_replays() -> None:
    persisted = _persisted()
    rebuilt = builder.build_live_annual_2025_net_interest_income_8bank_codex_verified_mapping_v1()
    assert rebuilt == persisted
    assert rebuilt["result_id"] == (
        "annual2025nii8bcv1:result:329d2f5e2604e4a1acb8223da1d7cdaf99e69e694e54647d2f4e01c60b866138"
    )
