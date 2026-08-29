from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
)

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "a" * 64
SOURCE_SHA256 = "b" * 64


def _json(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict[str, Any]:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-service-activity-topology-v1.json"),
        _json("tm-service-activity-evaluation-v1.json"),
        _json("tm-service-activity-schema-binding-v1.json"),
    )


def _columns() -> list[dict[str, Any]]:
    return [
        {"header_path_exact": ["Năm 2025", "Triệu đồng"], "value_kind": "MONEY"},
        {"header_path_exact": ["Năm 2024", "Triệu đồng"], "value_kind": "MONEY"},
    ]


def _row(
    label: str | None,
    values: list[str | None],
    *,
    kind: str = "ITEM",
    parent: str | None = None,
) -> dict[str, Any]:
    return {
        "hierarchy_path_exact": [label] if parent is None else [parent, label],
        "label_exact": label,
        "row_kind": kind,
        "values_exact": values,
    }


def _table(
    rows: list[dict[str, Any]], *, columns: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    return {
        "columns": _columns() if columns is None else columns,
        "continuation": "NONE",
        "rows": rows,
        "title_exact": "Lãi thuần từ hoạt động dịch vụ",
        "unit_exact": "Triệu đồng",
    }


def _page(table: dict[str, Any], *, primary: bool = False) -> dict[str, Any]:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "PRIMARY_STATEMENT" if primary else "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "INCOME_STATEMENT" if primary else "NOT_APPLICABLE",
                "tables": [table],
                "title_exact": "Lãi thuần từ hoạt động dịch vụ",
            }
        ],
        "status": "PRIMARY_FINANCIAL_STATEMENT" if primary else "FINANCIAL_NOTE_CONTENT",
    }


def _record(page: dict[str, Any], *, ordinal: int) -> dict[str, Any]:
    return {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": "gfpstorev1:json:" + str(ordinal) * 64,
        "physical_page": ordinal,
        "selected_page_ordinal": ordinal,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }


def _primary_rows(
    *, expense: tuple[str, str] = ("30", "20"), net: tuple[str, str] = ("70", "60")
) -> list[dict[str, Any]]:
    return [
        _row("Thu nhập từ hoạt động dịch vụ", ["100", "80"]),
        _row("Chi phí hoạt động dịch vụ", list(expense)),
        _row("Lãi thuần từ hoạt động dịch vụ", list(net), kind="SUBTOTAL"),
    ]


def _detail_rows(
    *, expense: tuple[str, str] = ("30", "20"), label_only_groups: bool = False
) -> list[dict[str, Any]]:
    income_parent = "Thu nhập từ hoạt động dịch vụ"
    expense_parent = "Chi phí hoạt động dịch vụ"
    negative_expense = all(value.startswith("(") for value in expense)
    expense_payment = ["(10)", "(5)"] if negative_expense else ["10", "5"]
    expense_other = ["(20)", "(15)"] if negative_expense else ["20", "15"]
    if not label_only_groups:
        return [
            _row(income_parent, ["100", "80"], kind="TOTAL"),
            _row("Thu từ dịch vụ thanh toán", ["60", "50"], parent=income_parent),
            _row("Thu nhập khác", ["40", "30"], parent=income_parent),
            _row(expense_parent, list(expense), kind="TOTAL"),
            _row("Chi về dịch vụ thanh toán", expense_payment, parent=expense_parent),
            _row("Chi phí khác", expense_other, parent=expense_parent),
            _row("Lãi thuần từ hoạt động dịch vụ", ["70", "60"], kind="TOTAL"),
        ]
    return [
        _row(income_parent, [None, None], kind="GROUP"),
        _row("Thu từ dịch vụ thanh toán", ["60", "50"], parent=income_parent),
        _row("Thu nhập khác", ["40", "30"], parent=income_parent),
        _row(None, ["100", "80"], kind="SUBTOTAL", parent=income_parent),
        _row(expense_parent, [None, None], kind="GROUP"),
        _row("Chi về dịch vụ thanh toán", expense_payment, parent=expense_parent),
        _row("Chi phí khác", expense_other, parent=expense_parent),
        _row(None, list(expense), kind="SUBTOTAL", parent=expense_parent),
        _row("Lãi thuần từ hoạt động dịch vụ", ["70", "60"], kind="TOTAL"),
    ]


def _evaluate(
    *,
    primary_rows: list[dict[str, Any]],
    detail_rows: list[dict[str, Any]],
    primary_columns: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    primary = _page(_table(primary_rows, columns=primary_columns), primary=True)
    detail = _page(_table(detail_rows))
    records = [_record(primary, ordinal=1), _record(detail, ordinal=2)]
    compiled = _compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    assert cluster["status"] == READY
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        cluster["component_regions"]
    )
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={
            record["page_json_version_id"]: record["page_json"] for record in records
        },
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    return cluster, candidate


def test_service_activity_signed_root_accepts_positive_expense_presentation() -> None:
    _cluster, candidate = _evaluate(primary_rows=_primary_rows(), detail_rows=_detail_rows())
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [value["coefficient"] for value in by_role["FAMILY_ROOT_TOTAL"]["values"]] == [
        70,
        60,
    ]
    signed = [
        receipt
        for receipt in candidate["closure_receipt"]["root_component_sum_receipts"]
        if "multipliers" in receipt
    ]
    assert [receipt["multipliers"] for receipt in signed] == [[1, -1]]


def test_service_activity_signed_root_accepts_negative_expense_presentation() -> None:
    _cluster, candidate = _evaluate(
        primary_rows=_primary_rows(expense=("(30)", "(20)")),
        detail_rows=_detail_rows(expense=("(30)", "(20)")),
    )
    assert candidate["status"] == READY
    signed = [
        receipt
        for receipt in candidate["closure_receipt"]["root_component_sum_receipts"]
        if "multipliers" in receipt
    ]
    assert [receipt["multipliers"] for receipt in signed] == [[1, 1]]


def test_service_activity_signed_source_root_mismatch_is_unresolved() -> None:
    _cluster, candidate = _evaluate(
        primary_rows=_primary_rows(net=("75", "65")), detail_rows=_detail_rows()
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_service_activity_label_only_second_root_projects_after_prior_subtotal() -> None:
    _cluster, candidate = _evaluate(
        primary_rows=_primary_rows(), detail_rows=_detail_rows(label_only_groups=True)
    )
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [value["coefficient"] for value in by_role["INCOME_PARENT"]["values"]] == [100, 80]
    assert [value["coefficient"] for value in by_role["EXPENSE_PARENT"]["values"]] == [30, 20]
    projected = [
        receipt
        for table in candidate["closure_receipt"]["table_receipts"]
        for receipt in table.get("label_only_structural_group_receipts", [])
    ]
    assert [receipt["carrier_role"] for receipt in projected] == [
        "INCOME_PARENT",
        "EXPENSE_PARENT",
    ]


def test_service_activity_primary_four_column_duration_selects_cumulative_pair() -> None:
    columns = [
        {"header_path_exact": ["Quý II 2025", "Triệu đồng"], "value_kind": "MONEY"},
        {"header_path_exact": ["Quý II 2024", "Triệu đồng"], "value_kind": "MONEY"},
        {
            "header_path_exact": ["Lũy kế từ đầu năm đến cuối quý này", "Năm nay"],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": ["Lũy kế từ đầu năm đến cuối quý này", "Năm trước"],
            "value_kind": "MONEY",
        },
    ]
    primary_rows = [
        _row("Thu nhập từ hoạt động dịch vụ", ["10", "8", "100", "80"]),
        _row("Chi phí hoạt động dịch vụ", ["3", "2", "30", "20"]),
        _row("Lãi thuần từ hoạt động dịch vụ", ["7", "6", "70", "60"], kind="SUBTOTAL"),
    ]
    _cluster, candidate = _evaluate(
        primary_rows=primary_rows,
        detail_rows=_detail_rows(),
        primary_columns=columns,
    )
    assert candidate["status"] == READY
    root = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL"
    )
    assert [value["coefficient"] for value in root["values"]] == [70, 60]
    assert {tuple(ref["money_column_ordinals"]) for ref in root["source_refs"]} == {(3, 4)}


def test_service_activity_source_only_combined_row_is_equation_consumed_not_mapped() -> None:
    detail_rows = _detail_rows()
    detail_rows[2] = _row(
        "Thu từ dịch vụ tư vấn, ủy thác và đại lý",
        ["40", "30"],
        parent="Thu nhập từ hoạt động dịch vụ",
    )
    _cluster, candidate = _evaluate(primary_rows=_primary_rows(), detail_rows=detail_rows)
    assert candidate["status"] == READY
    assert "INCOME_COMBINED_CONSULTING_TRUST_AGENCY" not in {
        mapping["role"] for mapping in candidate["mappings"]
    }
    source_only = candidate["closure_receipt"]["source_only_unmapped_rows"]
    assert any(item["consumed_by_exact_equation"] for item in source_only)


def test_service_activity_partial_declared_root_graph_is_unresolved() -> None:
    page = _page(
        _table(
            [
                _row("Thu nhập từ hoạt động dịch vụ", ["100", "80"], kind="TOTAL"),
                _row(
                    "Thu từ dịch vụ thanh toán",
                    ["60", "50"],
                    parent="Thu nhập từ hoạt động dịch vụ",
                ),
                _row("Thu nhập khác", ["40", "30"], parent="Thu nhập từ hoạt động dịch vụ"),
                _row("Lãi thuần từ hoạt động dịch vụ", ["100", "80"], kind="TOTAL"),
            ]
        )
    )
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page, ordinal=1)], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
