from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    validate_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

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


def _legacy_compiled_without_root_alternatives() -> dict[str, Any]:
    evaluation = _json("tm-service-activity-evaluation-v1.json")
    evaluation.pop("root_component_role_combinations", None)
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-service-activity-topology-v1.json"),
        evaluation,
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
    return _evaluate_pages([primary, detail])


def _evaluate_pages(
    pages: list[dict[str, Any]], *, compiled: dict[str, Any] | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    records = [_record(page, ordinal=ordinal) for ordinal, page in enumerate(pages, start=1)]
    compiled = _compiled() if compiled is None else compiled
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


def _evaluate_pages_fail_closed(
    pages: list[dict[str, Any]], *, compiled: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    records = [_record(page, ordinal=ordinal) for ordinal, page in enumerate(pages, start=1)]
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    if cluster["status"] != READY:
        return cluster, None
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

def test_service_activity_primary_summary_without_detail_is_not_observed() -> None:
    page = _page(_table(_primary_rows()), primary=True)
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page, ordinal=1)], compiled_specs=_compiled()
    )
    assert cluster["status"].startswith("NOT_OBSERVED")
    assert cluster["component_regions"] == []


def test_service_activity_root_totals_without_detail_children_are_not_observed() -> None:
    income_parent = "Thu nhập từ hoạt động dịch vụ"
    expense_parent = "Chi phí hoạt động dịch vụ"
    summary_rows = [
        _row(income_parent, ["100", "80"], kind="TOTAL"),
        _row(expense_parent, ["30", "20"], kind="TOTAL"),
        _row("Lãi thuần từ hoạt động dịch vụ", ["70", "60"], kind="TOTAL"),
    ]
    pages = [
        _page(_table(_primary_rows()), primary=True),
        _page(_table(summary_rows)),
    ]
    records = [_record(page, ordinal=ordinal) for ordinal, page in enumerate(pages, start=1)]
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=_compiled()
    )
    assert cluster["status"] == NOT_OBSERVED
    assert cluster["component_regions"] == []


def test_service_activity_generic_child_alias_without_root_is_not_observed() -> None:
    page = _page(
        {
            **_table([_row("Chi phí khác", ["20", "15"])]),
            "title_exact": "Chi phí hoạt động khác",
        }
    )
    page["sections"][0]["title_exact"] = "Chi phí hoạt động khác"
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page, ordinal=1)], compiled_specs=_compiled()
    )
    assert cluster["status"].startswith("NOT_OBSERVED")
    assert cluster["component_regions"] == []


def test_service_activity_duplicate_complete_detail_population_is_unresolved() -> None:
    primary = _page(_table(_primary_rows()), primary=True)
    detail = _page(_table(_detail_rows()))
    _cluster, candidate = _evaluate_pages([primary, detail, detail])
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_service_activity_unmapped_direct_money_child_is_unresolved() -> None:
    rows = _detail_rows()
    rows.insert(
        6,
        _row(
            "Khoản dịch vụ chưa khai báo",
            ["1", "1"],
            parent="Chi phí hoạt động dịch vụ",
        ),
    )
    # Preserve both printed equations after adding the unknown direct row.
    rows[3]["values_exact"] = ["31", "21"]
    rows[-1]["values_exact"] = ["69", "59"]
    primary = _primary_rows(expense=("31", "21"), net=("69", "59"))
    _cluster, candidate = _evaluate(primary_rows=primary, detail_rows=rows)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "UNMAPPED_DIRECT_FAMILY_SOURCE_MONEY_ROW" in candidate["reasons"]


def test_service_activity_conflicting_local_money_units_are_unresolved() -> None:
    primary = _page(_table(_primary_rows()), primary=True)
    detail_table = _table(_detail_rows())
    detail_table["unit_exact"] = "Triệu đồng; Nghìn đồng"
    _cluster, candidate = _evaluate_pages([primary, _page(detail_table)])
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_service_activity_conflicting_period_evidence_is_unresolved() -> None:
    primary = _page(_table(_primary_rows()), primary=True)
    detail_table = _table(
        _detail_rows(),
        columns=[
            {
                "header_path_exact": ["Năm 2025", "Năm trước", "Triệu đồng"],
                "value_kind": "MONEY",
            },
            {"header_path_exact": ["Năm 2024", "Triệu đồng"], "value_kind": "MONEY"},
        ],
    )
    _cluster, candidate = _evaluate_pages([primary, _page(detail_table)])
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


@pytest.mark.parametrize(
    ("income_label", "income_role", "expense_label", "expense_role"),
    [
        ("Thu dịch vụ thanh toán", "INCOME_PAYMENT", "Chi dịch vụ thanh toán", "EXPENSE_PAYMENT"),
        ("Thu dịch vụ ngân quỹ", "INCOME_TREASURY", "Chi về dịch vụ ngân quỹ", "EXPENSE_TREASURY"),
        ("Dịch vụ tư vấn", "INCOME_CONSULTING", "Dịch vụ tư vấn", "EXPENSE_CONSULTING"),
        (
            "Dịch vụ ủy thác và đại lý",
            "INCOME_TRUST_AGENCY",
            "Chi từ dịch vụ ủy thác và đại lý",
            "EXPENSE_TRUST_AGENCY",
        ),
        (
            "Dịch ủy thác và đại lý",
            "INCOME_TRUST_AGENCY",
            "Chi từ dịch vụ ủy thác và đại lý",
            "EXPENSE_TRUST_AGENCY",
        ),
        ("Dịch vụ hợp tác bảo hiểm", "INCOME_INSURANCE", "Dịch vụ bảo hiểm", "EXPENSE_INSURANCE"),
        (
            "Dịch vụ môi giới kinh doanh chứng khoán",
            "INCOME_SECURITIES",
            "Dịch vụ môi giới kinh doanh chứng khoán",
            "EXPENSE_SECURITIES",
        ),
        (
            "Thu dịch vụ thẩm định tài sản",
            "INCOME_DEBT_VALUATION",
            "Chi về cước phí, mạng viễn thông",
            "EXPENSE_TELECOM",
        ),
        ("Thu khác về dịch vụ", "INCOME_OTHER", "Chi từ dịch vụ khác", "EXPENSE_OTHER"),
    ],
)
def test_service_activity_2025_source_aliases_map_only_inside_declared_parent(
    income_label: str,
    income_role: str,
    expense_label: str,
    expense_role: str,
) -> None:
    rows = _detail_rows()
    income_index = 1 if income_role == "INCOME_PAYMENT" else 2
    expense_index = 4 if expense_role == "EXPENSE_PAYMENT" else 5
    income_values = ["60", "50"] if income_index == 1 else ["40", "30"]
    expense_values = ["10", "5"] if expense_index == 4 else ["20", "15"]
    rows[income_index] = _row(
        income_label,
        income_values,
        parent="Thu nhập từ hoạt động dịch vụ",
    )
    rows[expense_index] = _row(
        expense_label,
        expense_values,
        parent="Chi phí hoạt động dịch vụ",
    )
    _cluster, candidate = _evaluate(primary_rows=_primary_rows(), detail_rows=rows)
    assert candidate["status"] == READY
    mapped_roles = {mapping["role"] for mapping in candidate["mappings"]}
    assert income_role in mapped_roles
    assert expense_role in mapped_roles


@pytest.mark.parametrize(
    ("label", "role"),
    [
        (
            "Thu dịch vụ ngân quỹ, ủy thác và đại lý",
            "INCOME_COMBINED_TREASURY_TRUST_AGENCY_SOURCE_ONLY",
        ),
        (
            "Dịch vụ kinh doanh, dịch vụ bảo hiểm và tư vấn",
            "INCOME_COMBINED_INSURANCE_CONSULTING_SOURCE_ONLY",
        ),
        ("Dịch vụ bảo quản tài sản", "INCOME_CUSTODY_RENT_SOURCE_ONLY"),
        (
            "Thu từ cung ứng dịch vụ bảo quản tài sản, cho thuê tủ ké",
            "INCOME_CUSTODY_RENT_SOURCE_ONLY",
        ),
        (
            "Dịch vụ mua hẳn miễn truy đòi bộ chứng từ theo thư tín dụng",
            "INCOME_FORFAITING_SOURCE_ONLY",
        ),
        ("Thu phí tất toán trước hạn khoản vay", "INCOME_OTHER_SCHEMA_GAP_SOURCE_ONLY"),
    ],
)
def test_service_activity_schema_gap_rows_close_equation_without_mapping(
    label: str, role: str
) -> None:
    rows = _detail_rows()
    rows[2] = _row(
        label,
        ["40", "30"],
        parent="Thu nhập từ hoạt động dịch vụ",
    )
    _cluster, candidate = _evaluate(primary_rows=_primary_rows(), detail_rows=rows)
    assert candidate["status"] == READY
    assert role not in {mapping["role"] for mapping in candidate["mappings"]}
    source_only = candidate["closure_receipt"]["source_only_unmapped_rows"]
    assert any(
        item["declared_role"] == role and item["consumed_by_exact_equation"] for item in source_only
    )


def test_service_activity_source_parent_variants_are_structural_not_mapped_as_children() -> None:
    income_parent = "Thu phí dịch vụ"
    expense_parent = "Chi về dịch vụ"
    detail_rows = [
        _row(income_parent, ["100", "80"], kind="TOTAL"),
        _row("Thu dịch vụ thanh toán", ["60", "50"], parent=income_parent),
        _row("Thu dịch vụ khác", ["40", "30"], parent=income_parent),
        _row(expense_parent, ["30", "20"], kind="TOTAL"),
        _row("Chi dịch vụ thanh toán", ["10", "5"], parent=expense_parent),
        _row("Chi dịch vụ khác", ["20", "15"], parent=expense_parent),
        _row("Lãi thuần từ hoạt động dịch vụ", ["70", "60"], kind="TOTAL"),
    ]
    _cluster, candidate = _evaluate(primary_rows=_primary_rows(), detail_rows=detail_rows)
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [value["coefficient"] for value in by_role["INCOME_PARENT"]["values"]] == [
        100,
        80,
    ]
    assert [value["coefficient"] for value in by_role["EXPENSE_PARENT"]["values"]] == [
        30,
        20,
    ]


def test_service_activity_source_visible_vnd_unit_is_accepted_without_rescaling() -> None:
    columns = [
        {"header_path_exact": ["Năm 2025", "VND"], "value_kind": "MONEY"},
        {"header_path_exact": ["Năm 2024", "VND"], "value_kind": "MONEY"},
    ]
    primary_table = _table(_primary_rows(), columns=columns)
    primary_table["unit_exact"] = "VND"
    detail_table = _table(_detail_rows(), columns=columns)
    detail_table["unit_exact"] = "VND"
    _cluster, candidate = _evaluate_pages([_page(primary_table, primary=True), _page(detail_table)])
    assert candidate["status"] == READY
    assert {mapping["unit"] for mapping in candidate["mappings"]} == {"VND"}
    root = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL"
    )
    assert [value["coefficient"] for value in root["values"]] == [70, 60]


def test_service_activity_explicit_adjacent_continuation_inherits_only_blank_period_axis() -> None:
    income_parent = "Thu nhập từ hoạt động dịch vụ"
    expense_parent = "Chi phí hoạt động dịch vụ"
    first_table = _table(
        [
            _row(income_parent, ["100", "80"], kind="TOTAL"),
            _row("Thu từ dịch vụ thanh toán", ["60", "50"], parent=income_parent),
            _row("Thu nhập khác", ["40", "30"], parent=income_parent),
            _row(expense_parent, ["30", "20"], kind="TOTAL"),
        ]
    )
    first_table["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    continuation_table = _table(
        [
            _row("Chi về dịch vụ thanh toán", ["10", "5"], parent=expense_parent),
            _row("Chi phí khác", ["20", "15"], parent=expense_parent),
            _row("Lãi thuần từ hoạt động dịch vụ", ["70", "60"], kind="TOTAL"),
        ],
        columns=[
            {"header_path_exact": [None], "value_kind": "MONEY"},
            {"header_path_exact": [None], "value_kind": "MONEY"},
        ],
    )
    continuation_table.update(
        {
            "continuation": "CONTINUES_FROM_PREVIOUS_PAGE",
            "title_exact": None,
            "unit_exact": None,
        }
    )
    continuation_page = _page(continuation_table)
    continuation_page["sections"][0]["title_exact"] = None
    _cluster, candidate = _evaluate_pages(
        [_page(_table(_primary_rows()), primary=True), _page(first_table), continuation_page]
    )
    assert candidate["status"] == READY
    inherited = [
        table["lane_axis"]
        for table in candidate["closure_receipt"]["table_receipts"]
        if table["region"]["physical_page"] == 3
    ]
    assert [axis["layout_kind"] for axis in inherited] == [
        "ADJACENT_PAGE_EXPLICIT_CONTINUATION_BLANK_HEADER_AXIS"
    ]
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [value["coefficient"] for value in by_role["FAMILY_ROOT_TOTAL"]["values"]] == [70, 60]
    continuation_receipts = [
        table["adjacent_continuation_frontier_receipt"]
        for table in candidate["closure_receipt"]["table_receipts"]
        if "adjacent_continuation_frontier_receipt" in table
    ]
    assert [receipt["carrier_role"] for receipt in continuation_receipts] == ["EXPENSE_PARENT"]
    assert continuation_receipts[0]["component_roles"] == [
        "EXPENSE_PAYMENT",
        "EXPENSE_OTHER",
    ]
    assert any(
        equation["equation_kind"]
        == "EXACT_ADJACENT_CONTINUATION_DIRECT_CHILDREN_EQUAL_PRIOR_FRAGMENT_CARRIER"
        and equation["status"] == "EXACT"
        for equation in candidate["closure_receipt"]["equations"]
    )


def test_service_activity_cumulative_from_period_start_phrase_does_not_mean_comparative() -> None:
    columns = [
        {
            "header_path_exact": ["Lũy kế từ đầu kỳ đến", "31/12/2025", "Triệu đồng"],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": ["Lũy kế từ đầu kỳ đến", "31/12/2024", "Triệu đồng"],
            "value_kind": "MONEY",
        },
    ]
    _cluster, candidate = _evaluate(
        primary_rows=_primary_rows(),
        detail_rows=_detail_rows(),
        primary_columns=columns,
    )
    assert candidate["status"] == READY


def test_service_activity_partial_child_keeps_blank_lane_and_incomplete_control() -> None:
    income_parent = "Thu nhập từ hoạt động dịch vụ"
    detail_rows = _detail_rows()
    detail_rows[1] = _row(
        "Thu từ dịch vụ thanh toán",
        ["100", "50"],
        parent=income_parent,
    )
    detail_rows[2] = _row(
        "Dịch vụ tư vấn",
        [None, "30"],
        parent=income_parent,
    )
    _cluster, candidate = _evaluate(
        primary_rows=_primary_rows(),
        detail_rows=detail_rows,
    )
    assert candidate["status"] == READY
    consulting = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "INCOME_CONSULTING"
    )
    assert consulting["state"] == "PARTIAL_SOURCE_OBSERVATION"
    assert consulting["values"][0] == {
        "coefficient": None,
        "source_text": None,
        "state": "BLANK_SOURCE_CELL",
    }
    assert consulting["values"][1]["coefficient"] == 30
    parent_controls = [
        equation
        for equation in candidate["closure_receipt"]["equations"]
        if equation["result_source_refs"][0]["locator"]["physical_page"] == 2
        and equation["result_source_refs"][0]["row_ordinal"] == 1
    ]
    assert [equation["status"] for equation in parent_controls] == [
        "INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL"
    ]
    assert parent_controls[0]["lane_statuses"] == [
        "INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL",
        "EXACT",
    ]
    assert "BLANK_ZERO" not in json.dumps(candidate)
    assert "INFERRED_BLANK" not in json.dumps(candidate)


def test_service_activity_schema_gap_alias_without_explicit_family_graph_is_not_observed() -> None:
    table = _table([_row("Dịch vụ bảo quản tài sản", ["40", "30"])])
    table["title_exact"] = "Thông tin dịch vụ khác"
    page = _page(table)
    page["sections"][0]["title_exact"] = "Thông tin dịch vụ khác"
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page, ordinal=1)], compiled_specs=_compiled()
    )
    assert cluster["status"].startswith("NOT_OBSERVED")
    assert cluster["component_regions"] == []


def test_service_activity_related_party_view_is_excluded_from_document_graph() -> None:
    primary = _page(_table(_primary_rows()), primary=True)
    detail = _page(_table(_detail_rows()))
    related = _page(_table(_detail_rows()))
    related["sections"][0]["title_exact"] = "Giao dịch với các bên liên quan - hoạt động dịch vụ"
    related["sections"][0]["tables"][0]["title_exact"] = "Giao dịch với các bên liên quan"
    records = [
        _record(page, ordinal=ordinal)
        for ordinal, page in enumerate([primary, detail, related], start=1)
    ]
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records,
        compiled_specs=_compiled(),
    )
    assert cluster["status"] == READY
    assert {region["physical_page"] for region in cluster["component_regions"]} == {1, 2}


def test_service_activity_true_partial_blank_child_maps_blank_without_imputation() -> None:
    detail_rows = _detail_rows()
    detail_rows[0]["values_exact"] = ["60", "80"]
    detail_rows[2] = _row(
        "Dịch vụ tư vấn",
        [None, "30"],
        parent="Thu nhập từ hoạt động dịch vụ",
    )
    detail_rows[-1]["values_exact"] = ["30", "60"]
    primary_rows = _primary_rows(net=("30", "60"))
    primary_rows[0]["values_exact"] = ["60", "80"]
    _cluster, candidate = _evaluate(
        primary_rows=primary_rows,
        detail_rows=detail_rows,
    )
    assert candidate["status"] == READY
    mapping = next(item for item in candidate["mappings"] if item["role"] == "INCOME_CONSULTING")
    assert mapping["values"][0] == {
        "coefficient": None,
        "source_text": None,
        "state": "BLANK_SOURCE_CELL",
    }
    assert mapping["values"][1]["coefficient"] == 30
    observation = validate_source_observation_mapping_contract_v1(candidate)
    assert observation["violation_count"] == 0
    assert observation["partial_mapping_count"] == 1


_NET_ROOT_COMPONENT_ROLES = [
    "NET_PAYMENT_SOURCE_ONLY",
    "NET_TREASURY_SOURCE_ONLY",
    "NET_TRUST_AGENCY_SOURCE_ONLY",
    "NET_CONSULTING_SOURCE_ONLY",
    "NET_OTHER_SOURCE_ONLY",
]


def _net_service_rows() -> list[dict[str, Any]]:
    groups = [
        (
            "Lãi thuần từ dịch vụ thanh toán",
            ["15", "10"],
            "Thu từ dịch vụ thanh toán",
            ["20", "14"],
            "Chi về dịch vụ thanh toán",
            ["5", "4"],
        ),
        (
            "Lỗ thuần từ dịch vụ ngân quỹ",
            ["(3)", "(2)"],
            "Thu từ dịch vụ ngân quỹ",
            ["2", "3"],
            "Chi từ dịch vụ ngân quỹ",
            ["5", "5"],
        ),
        (
            "Lãi thuần từ hoạt động ủy thác và đại lý",
            ["8", "6"],
            "Thu từ hoạt động ủy thác và đại lý",
            ["10", "9"],
            "Chi từ hoạt động ủy thác và đại lý",
            ["2", "3"],
        ),
        (
            "Lãi/ (Lỗ) thuần từ hoạt động tư vấn",
            ["4", "(1)"],
            "Thu từ hoạt động tư vấn",
            ["5", "3"],
            "Chi từ hoạt động tư vấn",
            ["1", "4"],
        ),
        (
            "Lãi thuần từ hoạt động dịch vụ khác",
            ["6", "7"],
            "Thu từ hoạt động dịch vụ khác",
            ["8", "9"],
            "Chi từ hoạt động dịch vụ khác",
            ["2", "2"],
        ),
    ]
    rows = []
    for parent, net, income_label, income, expense_label, expense in groups:
        rows.extend(
            [
                _row(parent, net, kind="SUBTOTAL"),
                _row("+ " + income_label, income, parent=parent),
                _row("+ " + expense_label, expense, parent=parent),
            ]
        )
    rows.append(_row(None, ["30", "20"], kind="TOTAL"))
    return rows


def _flat_net_service_rows() -> list[dict[str, Any]]:
    """BAB standalone layout: every visible row has a one-segment source path."""
    groups = [
        (
            "Lãi thuần từ dịch vụ thanh toán",
            ["16,056", "15,970"],
            "Thu từ dịch vụ thanh toán",
            ["37,837", "34,955"],
            "Chi về dịch vụ thanh toán",
            ["21,781", "18,985"],
        ),
        (
            "Lỗ thuần từ dịch vụ ngân quỹ",
            ["(3,082)", "(3,267)"],
            "Thu từ dịch vụ ngân quỹ",
            ["1,504", "1,241"],
            "Chi từ dịch vụ ngân quỹ",
            ["4,586", "4,508"],
        ),
        (
            "Lãi thuần từ hoạt động ủy thác và đại lý",
            ["34,287", "26,501"],
            "Thu từ hoạt động ủy thác và đại lý",
            ["40,336", "30,272"],
            "Chi từ hoạt động ủy thác và đại lý",
            ["6,049", "3,771"],
        ),
        (
            "Lãi/ (Lỗ) thuần từ hoạt động tư vấn",
            ["44,062", "(842)"],
            "Thu từ hoạt động tư vấn",
            ["44,779", "4,861"],
            "Chi từ hoạt động tư vấn",
            ["717", "5,703"],
        ),
        (
            "Lãi thuần từ hoạt động dịch vụ khác",
            ["73,818", "54,408"],
            "Thu từ hoạt động dịch vụ khác",
            ["99,476", "67,211"],
            "Chi từ hoạt động dịch vụ khác",
            ["25,658", "12,803"],
        ),
    ]
    rows = []
    for parent, net, income_label, income, expense_label, expense in groups:
        rows.extend(
            [
                _row(parent, net),
                _row(income_label, income),
                _row(expense_label, expense),
            ]
        )
    rows.append(_row(None, ["165,141", "92,770"], kind="TOTAL"))
    return rows


def test_service_activity_legacy_two_parent_path_is_byte_and_semantic_stable() -> None:
    legacy_evaluation = _json("tm-service-activity-evaluation-v1.json")
    legacy_evaluation.pop("root_component_role_combinations", None)
    assert canonical_json_sha256_v1(legacy_evaluation) == (
        "520deb2de5636a3fb5b36472b99b92add552f1cbbd2dd8c4fed4515c1a0de352"
    )
    compiled = _legacy_compiled_without_root_alternatives()
    _cluster, candidate = _evaluate_pages(
        [
            _page(_table(_primary_rows()), primary=True),
            _page(_table(_detail_rows())),
        ],
        compiled=compiled,
    )
    assert candidate["status"] == READY
    assert canonical_json_sha256_v1(candidate) == (
        "7a0d8977f5a6ba915f6c44d20a90adbdc56868df055d0788b9f92e81d627c5a5"
    )
    signed = [
        receipt
        for receipt in candidate["closure_receipt"]["root_component_sum_receipts"]
        if "multipliers" in receipt
    ]
    assert [receipt["component_roles"] for receipt in signed] == [
        ["INCOME_PARENT", "EXPENSE_PARENT"]
    ]
    assert [receipt["multipliers"] for receipt in signed] == [[1, -1]]


@pytest.mark.parametrize(
    "failure_kind",
    [
        "NON_LIST",
        "DECLARATION_EXTRA_KEY",
        "FIRST_ROLES_OR_ORDER_DIFFERS_FROM_LEGACY",
        "FIRST_EQUATION_POLICY_DIFFERS_FROM_LEGACY",
        "DUPLICATE_ROLE",
        "UNKNOWN_ROLE",
        "SHARED_ROLE_CONFLICTING_COMPONENT_FRONTIER_POLICY",
    ],
)
def test_service_activity_root_component_alternative_spec_fails_closed(
    failure_kind: str,
) -> None:
    evaluation = _json("tm-service-activity-evaluation-v1.json")
    declarations = evaluation["root_component_role_combinations"]
    if failure_kind == "NON_LIST":
        evaluation["root_component_role_combinations"] = {}
    elif failure_kind == "DECLARATION_EXTRA_KEY":
        declarations[1]["undeclared"] = True
    elif failure_kind == "FIRST_ROLES_OR_ORDER_DIFFERS_FROM_LEGACY":
        declarations[0]["roles"] = ["EXPENSE_PARENT", "INCOME_PARENT"]
    elif failure_kind == "FIRST_EQUATION_POLICY_DIFFERS_FROM_LEGACY":
        declarations[0]["equation_policy"] = "DECLARED_DIRECT_SUM"
    elif failure_kind == "DUPLICATE_ROLE":
        declarations[1]["roles"][1] = declarations[1]["roles"][0]
    elif failure_kind == "UNKNOWN_ROLE":
        declarations[1]["roles"][1] = "UNDECLARED_ROLE"
    else:
        declarations.append(
            {
                "component_frontier_equation_policy": (
                    "UNIQUE_DECLARED_SIGN_ORIENTATION_FIRST_COMPONENT_POSITIVE"
                ),
                "equation_policy": "DECLARED_DIRECT_SUM",
                "roles": ["INCOME_PARENT", *_NET_ROOT_COMPONENT_ROLES],
            }
        )
    with pytest.raises(ValueError):
        compile_gemini_json_multitable_hierarchical_family_specs_v1(
            _json("tm-service-activity-topology-v1.json"),
            evaluation,
            _json("tm-service-activity-schema-binding-v1.json"),
        )


def test_service_activity_leading_child_continuation_scope_is_exact_opt_in() -> None:
    assert _compiled()["continuation_leading_child_scope_policy"] == (
        "EXACT_PRIOR_ROOT_CARRIER_SCOPES_CONSECUTIVE_RECEIVER_PREFIX"
    )
    evaluation = _json("tm-service-activity-evaluation-v1.json")
    evaluation["continuation_leading_child_scope_policy"] = "UNDECLARED_SCOPE_POLICY"
    with pytest.raises(ValueError):
        compile_gemini_json_multitable_hierarchical_family_specs_v1(
            _json("tm-service-activity-topology-v1.json"),
            evaluation,
            _json("tm-service-activity-schema-binding-v1.json"),
        )


def test_service_activity_unique_complete_net_root_alternative_closes_every_lane() -> None:
    _cluster, candidate = _evaluate_pages([_page(_table(_net_service_rows()))])
    assert candidate["status"] == READY
    mapped_roles = {mapping["role"] for mapping in candidate["mappings"]}
    assert mapped_roles == {
        "EXPENSE_CONSULTING",
        "EXPENSE_OTHER",
        "EXPENSE_PAYMENT",
        "EXPENSE_TREASURY",
        "EXPENSE_TRUST_AGENCY",
        "FAMILY_ROOT_TOTAL",
        "INCOME_CONSULTING",
        "INCOME_OTHER",
        "INCOME_PAYMENT",
        "INCOME_TREASURY",
        "INCOME_TRUST_AGENCY",
    }
    root = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL"
    )
    assert [value["coefficient"] for value in root["values"]] == [30, 20]
    signed = [
        receipt
        for receipt in candidate["closure_receipt"]["root_component_sum_receipts"]
        if "multipliers" in receipt
    ]
    assert [receipt["component_roles"] for receipt in signed] == [_NET_ROOT_COMPONENT_ROLES]
    assert [receipt["multipliers"] for receipt in signed] == [[1, 1, 1, 1, 1]]
    net_frontiers = [
        equation
        for equation in candidate["closure_receipt"]["equations"]
        if equation.get("component_frontier_role") in _NET_ROOT_COMPONENT_ROLES
    ]
    assert len(net_frontiers) == 5
    assert {tuple(equation["multipliers"]) for equation in net_frontiers} == {(1, -1)}
    assert all(equation["status"] == "EXACT" for equation in net_frontiers)
    assert not mapped_roles.intersection(_NET_ROOT_COMPONENT_ROLES)


def test_service_activity_flat_net_alternative_uses_bounded_parent_child_source_order() -> None:
    _cluster, candidate = _evaluate_pages([_page(_table(_flat_net_service_rows()))])
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "EXPENSE_CONSULTING",
        "EXPENSE_OTHER",
        "EXPENSE_PAYMENT",
        "EXPENSE_TREASURY",
        "EXPENSE_TRUST_AGENCY",
        "FAMILY_ROOT_TOTAL",
        "INCOME_CONSULTING",
        "INCOME_OTHER",
        "INCOME_PAYMENT",
        "INCOME_TREASURY",
        "INCOME_TRUST_AGENCY",
    }
    equations = candidate["closure_receipt"]["equations"]
    net_frontiers = [
        equation
        for equation in equations
        if equation.get("component_frontier_role") in _NET_ROOT_COMPONENT_ROLES
    ]
    assert [equation["component_frontier_role"] for equation in net_frontiers] == (
        _NET_ROOT_COMPONENT_ROLES
    )
    assert [equation["multipliers"] for equation in net_frontiers] == [[1, -1]] * 5
    assert all(equation["status"] == "EXACT" for equation in net_frontiers)
    root_receipt = next(
        receipt
        for receipt in candidate["closure_receipt"]["root_component_sum_receipts"]
        if receipt.get("component_roles") == _NET_ROOT_COMPONENT_ROLES
    )
    assert root_receipt["multipliers"] == [1, 1, 1, 1, 1]


def test_service_activity_flat_net_context_does_not_cross_next_parent_boundary() -> None:
    rows = _flat_net_service_rows()
    displaced_expense = rows.pop(2)
    rows.insert(5, displaced_expense)
    cluster, candidate = _evaluate_pages_fail_closed(
        [_page(_table(rows))], compiled=_compiled()
    )
    assert cluster["status"] == UNRESOLVED or (
        candidate is not None
        and candidate["status"] == UNRESOLVED
        and candidate["mappings"] == []
    )


@pytest.mark.parametrize(
    "failure_kind",
    ["INCOMPLETE", "TWO_ALTERNATIVES", "BLANK_LANE", "ROOT_MISMATCH"],
)
def test_service_activity_root_alternatives_fail_closed(failure_kind: str) -> None:
    rows = _net_service_rows()
    if failure_kind == "INCOMPLETE":
        del rows[12:15]
    elif failure_kind == "TWO_ALTERNATIVES":
        rows[-1:-1] = [
            _row("Thu nhập từ hoạt động dịch vụ", ["50", "35"], kind="SUBTOTAL"),
            _row("Chi phí hoạt động dịch vụ", ["20", "15"], kind="SUBTOTAL"),
        ]
    elif failure_kind == "BLANK_LANE":
        rows[12]["values_exact"][1] = None
    else:
        rows[-1]["values_exact"][0] = "31"
    cluster, candidate = _evaluate_pages_fail_closed([_page(_table(rows))], compiled=_compiled())
    assert cluster["status"] == UNRESOLVED or (
        candidate is not None and candidate["status"] == UNRESOLVED and candidate["mappings"] == []
    )


def _explicit_header_continuation_pages(
    shape: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    headers = [
        {"header_path_exact": ["Kỳ này"], "value_kind": "MONEY"},
        {"header_path_exact": ["Kỳ trước"], "value_kind": "MONEY"},
    ]
    income_parent = "Thu nhập từ hoạt động dịch vụ"
    expense_parent = "Chi phí hoạt động dịch vụ"
    first_rows = [
        _row(income_parent, ["100", "80"], kind="GROUP"),
        _row("Dịch vụ thanh toán", ["60", "50"], parent=income_parent),
        _row("Dịch vụ Ngân quỹ", ["10", "5"], parent=income_parent),
    ]
    if shape == "KLB_ROOT_COMPONENT_SPLIT":
        first_rows.append(_row("Thu nhập khác", ["30", "25"], parent=income_parent))
        second_rows = [
            _row(expense_parent, ["30", "20"], kind="GROUP"),
            _row("Chi dịch vụ thanh toán", ["10", "5"], parent=expense_parent),
            _row("Chi dịch vụ khác", ["20", "15"], parent=expense_parent),
            _row("Lãi/lỗ thuần từ hoạt động dịch vụ", ["70", "60"], kind="TOTAL"),
        ]
    else:
        second_rows = [
            _row("- Dịch vụ ủy thác", ["20", "15"]),
            _row("- Dịch vụ khác", ["10", "10"]),
            _row("Chi về dịch vụ", ["30", "20"], kind="SUBTOTAL"),
            _row("- Dịch vụ thanh toán", ["10", "5"]),
            _row("- Dịch vụ Ngân quỹ", ["1", "2"]),
            _row("- Dịch vụ khác", ["19", "13"]),
            _row("Lãi thuần từ hoạt động dịch vụ", ["70", "60"], kind="TOTAL"),
        ]
    first_table = _table(first_rows, columns=copy.deepcopy(headers))
    first_table.update(
        {
            "continuation": "CONTINUES_ON_NEXT_PAGE",
            "title_exact": None,
            "unit_exact": None,
        }
    )
    second_table = _table(second_rows, columns=copy.deepcopy(headers))
    second_table.update(
        {
            "continuation": "CONTINUES_FROM_PREVIOUS_PAGE",
            "title_exact": None,
            "unit_exact": None,
        }
    )
    first_page = _page(first_table)
    first_page["sections"][0]["title_exact"] = "26. Lãi thuần từ hoạt động dịch vụ"
    second_page = _page(second_table)
    second_page["sections"][0]["title_exact"] = None
    return first_page, second_page


@pytest.mark.parametrize("shape", ["KLB_ROOT_COMPONENT_SPLIT", "VAB_PARENT_CHILD_SUFFIX"])
def test_service_activity_explicit_equivalent_header_continuation_is_one_population(
    shape: str,
) -> None:
    pages = _explicit_header_continuation_pages(shape)
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page, ordinal=index) for index, page in enumerate(pages, 1)],
        compiled_specs=_legacy_compiled_without_root_alternatives(),
    )
    assert cluster["status"] == READY
    assert [region["physical_page"] for region in cluster["component_regions"]] == [1, 2]
    receipts = cluster["owner_receipt"]["explicit_adjacent_continuation_receipts"]
    assert len(receipts) == 1
    assert receipts[0]["header_axis_rule"] == "EXACT_EQUIVALENT_EXPLICIT_PERIOD_AXIS_NO_MUTATION"


@pytest.mark.parametrize(
    "failure_kind",
    [
        "CONFLICTING_EXPLICIT_AXIS",
        "REVERSED_EXPLICIT_AXIS",
        "AMBIGUOUS_PREDECESSORS",
        "NONADJACENT",
    ],
)
def test_service_activity_explicit_header_continuation_fails_closed(
    failure_kind: str,
) -> None:
    first_page, second_page = _explicit_header_continuation_pages("KLB_ROOT_COMPONENT_SPLIT")
    second_ordinal = 2
    if failure_kind == "CONFLICTING_EXPLICIT_AXIS":
        second_page["sections"][0]["tables"][0]["columns"][1]["header_path_exact"] = ["Kỳ khác"]
    elif failure_kind == "REVERSED_EXPLICIT_AXIS":
        columns = second_page["sections"][0]["tables"][0]["columns"]
        columns[0], columns[1] = columns[1], columns[0]
    elif failure_kind == "AMBIGUOUS_PREDECESSORS":
        first_page["sections"][0]["tables"].append(
            copy.deepcopy(first_page["sections"][0]["tables"][0])
        )
    elif failure_kind == "NONADJACENT":
        second_ordinal = 3
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(first_page, ordinal=1), _record(second_page, ordinal=second_ordinal)],
        compiled_specs=_legacy_compiled_without_root_alternatives(),
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
