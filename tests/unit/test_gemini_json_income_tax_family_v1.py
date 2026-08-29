from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    GeminiJsonMultitableHierarchicalFamilyV1Error,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    classify_gemini_json_multitable_hierarchical_table_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
    validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1,
)

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "a" * 64
VERSION_ID = "gfpstorev1:json:" + "b" * 64
SOURCE_SHA256 = "c" * 64
OWNER = "Chi phí thuế thu nhập doanh nghiệp"


def _json(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict[str, Any]:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-income-tax-topology-v1.json"),
        _json("tm-income-tax-evaluation-v1.json"),
        _json("tm-income-tax-schema-binding-v1.json"),
    )


def _row(
    label: str | None,
    current: str | None,
    comparative: str | None,
    *,
    kind: str = "ITEM",
) -> dict[str, Any]:
    return {
        "hierarchy_path_exact": [] if label is None else [label],
        "label_exact": label,
        "row_kind": kind,
        "values_exact": [current, comparative],
    }


def _canonical_rows() -> list[dict[str, Any]]:
    return [
        _row("Tổng lợi nhuận kế toán trước thuế", "100", "80"),
        _row("Điều chỉnh khác", "(10)", "(8)"),
        _row("Lợi nhuận trước thuế của Ngân hàng mẹ", "90", "72"),
        _row("Chi phí không được khấu trừ", "5", "3"),
        _row("Thu nhập chịu thuế", "95", "75"),
        _row("Thuế suất thuế TNDN", "20%", "20%"),
        _row("Chi phí thuế TNDN hiện hành ước tính của Ngân hàng mẹ", "19", "15"),
        _row("Thuế TNDN của chi nhánh nước ngoài", "1", None),
        _row("Chi phí thuế TNDN trong kỳ", "20", "15"),
        _row("Chi phí thuế TNDN hiện hành", "20", "15"),
        _row("Điều chỉnh khác", "1", "2"),
    ]


def _table(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "columns": [
            {"header_path_exact": ["Năm 2026", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Năm 2025", "Triệu đồng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": rows,
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }


def _page(
    rows: list[dict[str, Any]],
    *,
    owner: str | None = OWNER,
    tables: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": tables if tables is not None else [_table(rows)],
                "title_exact": owner,
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _record(page: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": VERSION_ID,
        "physical_page": 1,
        "selected_page_ordinal": 1,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }


def _evaluate(page: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    compiled = _compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        cluster["component_regions"]
    )
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    return candidate, cluster, receipt


def test_income_tax_config_binds_schema_and_generic_stage_policy() -> None:
    compiled = _compiled()
    assert compiled["topology"]["family_id"] == "INCOME_TAX"
    assert compiled["schema"]["family_root_report_norm_id"] == 5727
    assert set(compiled["bindings"].values()) == set(range(5723, 5738)) - {5727}
    assert [item["scope_id"] for item in compiled["ordered_role_scopes"]] == [
        "TAXABLE_INCOME_RECONCILIATION",
        "CURRENT_TAX_EXPENSE",
    ]


def test_item_typed_results_stages_percentage_and_blank_close_locally() -> None:
    page = _page(_canonical_rows())
    candidate, cluster, receipt = _evaluate(page)
    assert candidate["status"] == READY
    assert {mapping["report_norm_id"] for mapping in candidate["mappings"]} == {
        5723,
        5728,
        5729,
        5730,
        5731,
        5732,
        5734,
    }
    table_receipt = candidate["closure_receipt"]["table_receipts"][0]
    assert len(table_receipt["non_money_metric_source_rows"]) == 1
    assert {
        item["row_ordinal"]
        for item in table_receipt["classification"]["outside_ordered_role_scope_rows"]
    } == {10, 11}
    assert len(candidate["closure_receipt"]["equations"]) == 3
    non_taxable = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "NON_TAXABLE_AGGREGATE"
    )
    assert non_taxable["row_id"] == "r2"
    assert non_taxable["state"] == (
        "SOURCE_VALIDATION_ROLE_PROJECTED_TO_MAPPED_ROLE_AFTER_ORDERED_STAGE_EXACT_EQUATION_CLOSURE"
    )
    assert table_receipt["ordered_role_scope_projection_receipts"] == [
        {
            "projected_source_refs": non_taxable["source_refs"],
            "rule": (
                "VALIDATION_ROLE_PROJECTS_TO_DECLARED_MAPPED_AGGREGATE_ONLY_"
                "INSIDE_ONE_ORDERED_STAGE_AFTER_EXACT_EQUATION_CONSUMPTION"
            ),
            "scope_id": "TAXABLE_INCOME_RECONCILIATION",
            "source_role": "SOURCE_ONLY_EQUATION_COMPONENT",
            "target_role": "NON_TAXABLE_AGGREGATE",
        }
    ]
    foreign = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "FOREIGN_BRANCH_TAX"
    )
    assert [value["coefficient"] for value in foreign["values"]] == [1, 0]
    validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
        candidate,
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=_compiled(),
        query_receipt=receipt,
    )


def test_unique_required_role_table_supplies_generic_owner_fallback() -> None:
    page = _page(_canonical_rows(), owner=None)
    candidate, cluster, _receipt = _evaluate(page)
    assert candidate["status"] == READY
    assert cluster["owner_receipt"]["alias"] == "DECLARED_REQUIRED_ROLE_TABLE"


def test_duplicate_complete_role_tables_without_owner_are_unresolved() -> None:
    page = _page(
        [],
        owner=None,
        tables=[_table(_canonical_rows()), _table(deepcopy(_canonical_rows()))],
    )
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []


def test_incomplete_role_population_without_owner_is_not_observed() -> None:
    page = _page([_row("Lợi nhuận trước thuế", "100", "80")], owner=None)
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] != READY
    assert cluster["component_regions"] == []


def test_deferred_tax_balance_surface_is_typed_control() -> None:
    page = _page(
        [
            _row("Tài sản thuế thu nhập hoãn lại", None, None, kind="GROUP"),
            _row("Số dư cuối kỳ", "10", "8", kind="TOTAL"),
        ],
        owner="34.2 Thuế thu nhập doanh nghiệp hoãn lại",
    )
    section = page["sections"][0]
    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        page, section, section["tables"][0], compiled_specs=_compiled()
    )
    assert classification["typed_control_disposition"] == (
        "DEFERRED_TAX_BALANCE_CONTROL_OUTSIDE_INCOME_TAX_EXPENSE"
    )


def test_deferred_expense_context_maps_only_exact_printed_net_total() -> None:
    page = _page(_canonical_rows())
    deferred_rows = [
        _row(
            "Chi phí thuế thu nhập doanh nghiệp hoãn lại phát sinh từ hoàn nhập "
            "tài sản thuế thu nhập hoãn lại",
            "14.913",
            "33.594",
        ),
        _row(
            "Thu nhập thuế thu nhập doanh nghiệp hoãn lại phát sinh từ các khoản "
            "chênh lệch tạm thời được khấu trừ",
            "(14.858)",
            "(17.190)",
        ),
        _row(None, "55", "16.404", kind="TOTAL"),
    ]
    page["sections"].append(
        {
            "content_kind": "FINANCIAL_NOTE",
            "narratives_exact": [],
            "statement_type": "NOT_APPLICABLE",
            "tables": [_table(deferred_rows)],
            "title_exact": "33.2 Chi phí thuế thu nhập doanh nghiệp hoãn lại",
        }
    )
    candidate, _cluster, _receipt = _evaluate(page)
    mapping = next(item for item in candidate["mappings"] if item["role"] == "DEFERRED_TAX_NET")
    assert mapping["row_id"] == "r3"
    assert mapping["source_refs"][0]["label_exact"] is None
    assert [value["coefficient"] for value in mapping["values"]] == [55, 16_404]
    deferred_receipt = candidate["closure_receipt"]["table_receipts"][1]
    assert deferred_receipt["classification"]["typed_control_disposition"] is None
    assert deferred_receipt["classification"]["typed_control_override_receipts"] == [
        {
            "control_disposition": ("DEFERRED_TAX_BALANCE_CONTROL_OUTSIDE_INCOME_TAX_EXPENSE"),
            "declared_roles": ["DEFERRED_TAX_NET"],
            "rule": "DECLARED_ROLE_EXPLICITLY_OVERRIDES_BROAD_CONTROL_SURFACE",
        }
    ]
    assert len(deferred_receipt["source_only_rows"]) == 2
    assert all(item["consumed_by_exact_equation"] for item in deferred_receipt["source_only_rows"])


def test_candidate_replay_rejects_stage_receipt_tamper() -> None:
    page = _page(_canonical_rows())
    candidate, cluster, receipt = _evaluate(page)
    candidate["closure_receipt"]["table_receipts"][0]["classification"][
        "outside_ordered_role_scope_rows"
    ][0]["row_ordinal"] = 999
    with pytest.raises(GeminiJsonMultitableHierarchicalFamilyV1Error):
        validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
            candidate,
            regions=cluster["component_regions"],
            page_json_by_version={VERSION_ID: page},
            compiled_specs=_compiled(),
            query_receipt=receipt,
        )


def test_candidate_replay_rejects_ordered_projection_receipt_tamper() -> None:
    page = _page(_canonical_rows())
    candidate, cluster, receipt = _evaluate(page)
    candidate["closure_receipt"]["table_receipts"][0]["ordered_role_scope_projection_receipts"][0][
        "target_role"
    ] = "NON_DEDUCTIBLE_EXPENSE"
    with pytest.raises(GeminiJsonMultitableHierarchicalFamilyV1Error):
        validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
            candidate,
            regions=cluster["component_regions"],
            page_json_by_version={VERSION_ID: page},
            compiled_specs=_compiled(),
            query_receipt=receipt,
        )
