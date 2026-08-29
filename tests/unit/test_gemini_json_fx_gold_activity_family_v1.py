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
    GeminiJsonMultitableHierarchicalFamilyV1Error,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
    validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "a" * 64
SOURCE_SHA256 = "b" * 64


def _json(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict[str, Any]:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-fx-gold-activity-topology-v1.json"),
        _json("tm-fx-gold-activity-evaluation-v1.json"),
        _json("tm-fx-gold-activity-schema-binding-v1.json"),
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
    rows: list[dict[str, Any]],
    *,
    columns: list[dict[str, Any]] | None = None,
    unit: str = "Triệu đồng",
) -> dict[str, Any]:
    return {
        "columns": _columns() if columns is None else columns,
        "continuation": "NONE",
        "rows": rows,
        "title_exact": "Lãi thuần từ hoạt động kinh doanh ngoại hối",
        "unit_exact": unit,
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
                "title_exact": "Lãi thuần từ hoạt động kinh doanh ngoại hối",
            }
        ],
        "status": "PRIMARY_FINANCIAL_STATEMENT" if primary else "FINANCIAL_NOTE_CONTENT",
    }


def _record(page: dict[str, Any], ordinal: int) -> dict[str, Any]:
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


def _primary_rows(net: tuple[str, str] = ("70", "60")) -> list[dict[str, Any]]:
    return [_row("Lãi thuần từ hoạt động kinh doanh ngoại hối", list(net), kind="TOTAL")]


def _detail_rows(
    *,
    expense: tuple[str, str] = ("30", "20"),
    one_child: bool = False,
    combined: bool = False,
) -> list[dict[str, Any]]:
    income_parent = "Thu nhập từ hoạt động kinh doanh ngoại hối"
    expense_parent = "Chi phí từ hoạt động kinh doanh ngoại hối"
    if combined:
        income_children = [
            _row(
                "Thu từ kinh doanh ngoại tệ giao ngay và vàng",
                ["100", "80"],
                parent=income_parent,
            )
        ]
        expense_children = [
            _row(
                "Chi về kinh doanh ngoại tệ giao ngay và vàng",
                list(expense),
                parent=expense_parent,
            )
        ]
    elif one_child:
        income_children = [
            _row("Thu từ kinh doanh ngoại tệ giao ngay", ["100", "80"], parent=income_parent)
        ]
        expense_children = [
            _row("Chi từ kinh doanh ngoại tệ giao ngay", list(expense), parent=expense_parent)
        ]
    else:
        income_children = [
            _row("Thu từ kinh doanh ngoại tệ giao ngay", ["60", "50"], parent=income_parent),
            _row(
                "Thu từ các công cụ tài chính phái sinh tiền tệ",
                ["40", "30"],
                parent=income_parent,
            ),
        ]
        negative = all(value.startswith("(") for value in expense)
        expense_children = [
            _row(
                "Chi từ kinh doanh ngoại tệ giao ngay",
                ["(10)", "(5)"] if negative else ["10", "5"],
                parent=expense_parent,
            ),
            _row(
                "Chi về các công cụ tài chính phái sinh tiền tệ",
                ["(20)", "(15)"] if negative else ["20", "15"],
                parent=expense_parent,
            ),
        ]
    return [
        _row(income_parent, ["100", "80"], kind="TOTAL"),
        *income_children,
        _row(expense_parent, list(expense), kind="TOTAL"),
        *expense_children,
        _row("Lãi thuần từ hoạt động kinh doanh ngoại hối", ["70", "60"], kind="TOTAL"),
    ]


def _coalesce(pages: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    records = [_record(page, ordinal) for ordinal, page in enumerate(pages, start=1)]
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records,
        compiled_specs=_compiled(),
    )
    return cluster, records


def _evaluate(
    *,
    detail_rows: list[dict[str, Any]],
    primary_rows: list[dict[str, Any]] | None = None,
    detail_unit: str = "Triệu đồng",
    detail_columns: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    pages = [
        _page(_table(_primary_rows() if primary_rows is None else primary_rows), primary=True),
        _page(_table(detail_rows, columns=detail_columns, unit=detail_unit)),
    ]
    return _evaluate_pages(pages)


def _evaluate_pages(pages: list[dict[str, Any]]) -> dict[str, Any]:
    cluster, records = _coalesce(pages)
    assert cluster["status"] == READY
    return evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={
            record["page_json_version_id"]: record["page_json"] for record in records
        },
        compiled_specs=_compiled(),
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            cluster["component_regions"]
        ),
    )


def test_fx_gold_split_rows_close_signed_root() -> None:
    candidate = _evaluate(detail_rows=_detail_rows())
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert set(by_role) >= {
        "INCOME_PARENT",
        "INCOME_SPOT_FX",
        "INCOME_CURRENCY_DERIVATIVES",
        "EXPENSE_PARENT",
        "EXPENSE_SPOT_FX",
        "EXPENSE_CURRENCY_DERIVATIVES",
        "FAMILY_ROOT_TOTAL",
    }
    assert [cell["coefficient"] for cell in by_role["FAMILY_ROOT_TOTAL"]["values"]] == [70, 60]


def test_fx_gold_combined_spot_and_gold_rows_remain_combined_schema_roles() -> None:
    candidate = _evaluate(detail_rows=_detail_rows(combined=True))
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert by_role["INCOME_SPOT_FX_AND_GOLD"]["report_norm_id"] == 6026
    assert by_role["EXPENSE_SPOT_FX_AND_GOLD"]["report_norm_id"] == 6027
    assert "INCOME_SPOT_FX" not in by_role
    assert "INCOME_GOLD" not in by_role


def test_fx_gold_single_declared_child_per_explicit_root_is_evaluated() -> None:
    candidate = _evaluate(detail_rows=_detail_rows(one_child=True))
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} >= {
        "INCOME_SPOT_FX",
        "EXPENSE_SPOT_FX",
        "FAMILY_ROOT_TOTAL",
    }


def test_fx_gold_lai_lo_source_vocabulary_maps_to_income_expense_graph() -> None:
    income_parent = "Lãi từ hoạt động kinh doanh ngoại hối"
    expense_parent = "Lỗ từ hoạt động kinh doanh ngoại hối"
    candidate = _evaluate(
        detail_rows=[
            _row(income_parent, ["100", "80"], kind="SUBTOTAL"),
            _row("Lãi từ kinh doanh ngoại tệ giao ngay", ["60", "50"], parent=income_parent),
            _row(
                "Lãi từ các công cụ tài chính phái sinh tiền tệ",
                ["40", "30"],
                parent=income_parent,
            ),
            _row(expense_parent, ["(30)", "(20)"], kind="SUBTOTAL"),
            _row("Lỗ từ kinh doanh ngoại tệ giao ngay", ["(10)", "(5)"], parent=expense_parent),
            _row(
                "Lỗ từ các công cụ tài chính phái sinh tiền tệ",
                ["(20)", "(15)"],
                parent=expense_parent,
            ),
            _row("Lãi thuần từ hoạt động kinh doanh ngoại hối", ["70", "60"], kind="TOTAL"),
        ]
    )
    assert candidate["status"] == READY


def test_fx_gold_negative_expense_presentation_closes_without_sign_rewrite() -> None:
    candidate = _evaluate(
        detail_rows=_detail_rows(expense=("(30)", "(20)")),
        primary_rows=_primary_rows(),
    )
    assert candidate["status"] == READY
    signed = [
        receipt
        for receipt in candidate["closure_receipt"]["root_component_sum_receipts"]
        if "multipliers" in receipt
    ]
    assert [receipt["multipliers"] for receipt in signed] == [[1, 1]]


def test_fx_gold_source_visible_net_mismatch_is_unresolved() -> None:
    candidate = _evaluate(
        detail_rows=_detail_rows(),
        primary_rows=_primary_rows(net=("71", "61")),
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_fx_gold_duplicate_complete_detail_population_is_unresolved() -> None:
    detail = _page(_table(_detail_rows()))
    candidate = _evaluate_pages([_page(_table(_primary_rows()), primary=True), detail, detail])
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_fx_gold_unmapped_direct_money_child_is_unresolved() -> None:
    rows = _detail_rows()
    rows.insert(
        6,
        _row(
            "Khoản kinh doanh ngoại hối chưa khai báo",
            ["1", "1"],
            parent="Chi phí từ hoạt động kinh doanh ngoại hối",
        ),
    )
    rows[3]["values_exact"] = ["31", "21"]
    rows[-1]["values_exact"] = ["69", "59"]
    candidate = _evaluate(
        detail_rows=rows,
        primary_rows=_primary_rows(net=("69", "59")),
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "UNMAPPED_DIRECT_FAMILY_SOURCE_MONEY_ROW" in candidate["reasons"]


def test_fx_gold_primary_source_result_without_detail_is_not_observed() -> None:
    cluster, _records = _coalesce([_page(_table(_primary_rows()), primary=True)])
    assert cluster["status"] == NOT_OBSERVED
    assert cluster["component_regions"] == []


def test_fx_gold_partial_detail_root_graph_is_unresolved() -> None:
    income_parent = "Thu nhập từ hoạt động kinh doanh ngoại hối"
    partial = [
        _row(income_parent, ["100", "80"], kind="TOTAL"),
        _row("Thu từ kinh doanh ngoại tệ giao ngay", ["100", "80"], parent=income_parent),
        _row("Lãi thuần từ hoạt động kinh doanh ngoại hối", ["100", "80"], kind="TOTAL"),
    ]
    cluster, _records = _coalesce(
        [_page(_table(_primary_rows(net=("100", "80"))), primary=True), _page(_table(partial))]
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []


def test_fx_gold_generic_other_rows_without_explicit_root_are_not_observed() -> None:
    page = _page(_table([_row("Chi khác", ["20", "15"])]))
    page["sections"][0]["title_exact"] = "Chi phí hoạt động khác"
    page["sections"][0]["tables"][0]["title_exact"] = "Chi phí hoạt động khác"
    cluster, _records = _coalesce([page])
    assert cluster["status"] == NOT_OBSERVED


def test_fx_gold_root_row_inside_foreign_dimension_table_is_not_a_detail_signal() -> None:
    table = _table(
        [
            _row("Lãi thuần từ hoạt động kinh doanh ngoại hối", ["10", "8"]),
            _row("Lãi thuần từ hoạt động dịch vụ", ["20", "15"]),
        ]
    )
    table["title_exact"] = "Mức độ tập trung theo khu vực địa lý"
    page = _page(table)
    page["sections"][0]["title_exact"] = "Mức độ tập trung theo khu vực địa lý"
    cluster, _records = _coalesce([page])
    assert cluster["status"] == NOT_OBSERVED


def test_fx_gold_conflicting_unit_and_period_evidence_fail_closed() -> None:
    unit_candidate = _evaluate(
        detail_rows=_detail_rows(),
        detail_unit="Triệu đồng; Nghìn đồng",
    )
    assert unit_candidate["status"] == UNRESOLVED
    assert unit_candidate["mappings"] == []
    period_candidate = _evaluate(
        detail_rows=_detail_rows(),
        detail_columns=[
            {"header_path_exact": ["Năm 2025", "Năm trước", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Năm 2024", "Triệu đồng"], "value_kind": "MONEY"},
        ],
    )
    assert period_candidate["status"] == UNRESOLVED
    assert period_candidate["mappings"] == []


def test_fx_gold_candidate_replay_rejects_coherent_signed_root_receipt_drift() -> None:
    pages = [
        _page(_table(_primary_rows()), primary=True),
        _page(_table(_detail_rows())),
    ]
    cluster, records = _coalesce(pages)
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        cluster["component_regions"]
    )
    page_json_by_version = {
        record["page_json_version_id"]: record["page_json"] for record in records
    }
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version=page_json_by_version,
        compiled_specs=_compiled(),
        query_receipt=receipt,
    )
    forged = copy.deepcopy(candidate)
    forged["closure_receipt"]["root_component_sum_receipts"][0]["multipliers"] = [1, 1]
    forged["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in forged.items() if key != "candidate_id"}
    )
    with pytest.raises(
        GeminiJsonMultitableHierarchicalFamilyV1Error,
        match="candidate replay drifted",
    ):
        validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
            forged,
            regions=cluster["component_regions"],
            page_json_by_version=page_json_by_version,
            compiled_specs=_compiled(),
            query_receipt=receipt,
        )
