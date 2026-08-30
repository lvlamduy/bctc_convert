from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import bctc_ai.evaluation.gemini_json_rollforward_table_repair_v1 as repair_subject
from bctc_ai.evaluation.gemini_json_equity_matrix_accounting_family_v1 import (
    READY,
    GeminiJsonEquityMatrixAccountingFamilyV1Error,
    build_gemini_json_equity_matrix_region_query_receipt_v1,
    classify_gemini_json_equity_matrix_table_v1,
    coalesce_gemini_json_equity_matrix_document_v1,
    compile_gemini_json_equity_matrix_family_specs_v1,
    evaluate_gemini_json_equity_matrix_family_cluster_v1,
    validate_gemini_json_equity_matrix_family_candidate_replay_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "d" * 64
SOURCE_SHA256 = "e" * 64


def _json(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict:
    return compile_gemini_json_equity_matrix_family_specs_v1(
        _json("tm-state-budget-obligations-topology-v1.json"),
        _json("tm-state-budget-obligations-evaluation-v1.json"),
        _json("tm-state-budget-obligations-schema-binding-v1.json"),
    )


def _table() -> dict:
    return {
        "columns": [
            {"header_path_exact": ["Số còn phải nộp đầu năm"], "value_kind": "MONEY"},
            {"header_path_exact": ["Số phải nộp trong kỳ"], "value_kind": "MONEY"},
            {"header_path_exact": ["Số đã nộp trong kỳ"], "value_kind": "MONEY"},
            {"header_path_exact": ["Số còn phải nộp cuối kỳ"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            {
                "hierarchy_path_exact": ["Thuế giá trị gia tăng"],
                "label_exact": "Thuế giá trị gia tăng",
                "row_kind": "ITEM",
                "values_exact": ["10", "5", "3", "12"],
            },
            {
                "hierarchy_path_exact": ["Thuế thu nhập doanh nghiệp"],
                "label_exact": "Thuế thu nhập doanh nghiệp",
                "row_kind": "ITEM",
                "values_exact": ["20", "4", "7", "17"],
            },
            {
                "hierarchy_path_exact": ["Các loại thuế khác, phí và lệ phí"],
                "label_exact": "Các loại thuế khác, phí và lệ phí",
                "row_kind": "ITEM",
                "values_exact": ["1", "2", "1", "2"],
            },
            {
                "hierarchy_path_exact": ["Tổng cộng"],
                "label_exact": "Tổng cộng",
                "row_kind": "TOTAL",
                "values_exact": ["31", "11", "11", "31"],
            },
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }


def _page(table: dict) -> dict:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [table],
                "title_exact": "Tình hình thực hiện nghĩa vụ với ngân sách nhà nước",
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _record(page: dict) -> dict:
    return {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": "gfpstorev1:json:" + "f" * 64,
        "physical_page": 1,
        "selected_page_ordinal": 1,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }


def _evaluate(table: dict | None = None) -> tuple[dict, dict, dict, dict]:
    compiled = _compiled()
    page = _page(table or _table())
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    receipt = build_gemini_json_equity_matrix_region_query_receipt_v1(
        cluster["component_regions"], owner_receipt=cluster["owner_receipt"]
    )
    candidate = evaluate_gemini_json_equity_matrix_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={_record(page)["page_json_version_id"]: page},
        compiled_specs=compiled,
        query_receipt=receipt,
        document_unit_context_evidence=cluster["document_unit_context_evidence"],
    )
    return compiled, page, cluster, candidate


def test_vector_root_and_component_rows_close_without_prompt_accounting_logic() -> None:
    compiled, _page_json, _cluster, candidate = _evaluate()
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert compiled["root_mapping_policy"].endswith("VECTOR_WITH_COMPONENT_VECTORS")
    assert set(by_role) == {
        "FAMILY_TOTAL",
        "VAT",
        "CORPORATE_INCOME_TAX",
        "OTHER_PAYABLE",
    }
    assert by_role["FAMILY_TOTAL"]["report_norm_id"] == 1269
    assert [value["coefficient"] for value in by_role["FAMILY_TOTAL"]["values"]] == [
        31,
        11,
        11,
        31,
    ]
    assert by_role["FAMILY_TOTAL"]["values"][2]["equation_multiplier"] == -1
    assert by_role["OTHER_PAYABLE"]["report_norm_id"] == 1279


def test_repair_equations_source_derive_positive_or_parenthesized_decrease_sign() -> None:
    positive = _table()
    _compiled_specs, _page_json, _cluster, positive_candidate = _evaluate(positive)
    positive_equations, _rows, _columns = repair_subject._equity_matrix_repair_equations_v1(
        table=positive,
        closure=positive_candidate["closure_receipt"],
    )
    assert {
        equation["terms"][-1]["multiplier"]
        for equation in positive_equations
        if equation["equation_id"].startswith("vertical-rollforward-")
    } == {-1}

    parenthesized = _table()
    for row in parenthesized["rows"]:
        row["values_exact"][2] = f"({row['values_exact'][2]})"
    parenthesized["rows"][0]["values_exact"][2] = "(3)借-"
    parenthesized["rows"][0]["values_exact"][3] = "null"
    _compiled_specs, _page_json, _cluster, parenthesized_candidate = _evaluate(parenthesized)
    signed_equations, _rows, _columns = repair_subject._equity_matrix_repair_equations_v1(
        table=parenthesized,
        closure=parenthesized_candidate["closure_receipt"],
    )
    assert {
        equation["terms"][-1]["multiplier"]
        for equation in signed_equations
        if equation["equation_id"].startswith("vertical-rollforward-")
    } == {1}


def test_longer_other_payable_alias_does_not_double_match_other_tax() -> None:
    classification = classify_gemini_json_equity_matrix_table_v1(
        _table(), compiled_specs=_compiled()
    )
    role = classification["component_axis"][2]
    assert role["kind"] == "MAPPED_COMPONENT"
    assert role["role"] == "OTHER_PAYABLE"
    assert role["reasons"] == []


def test_candidate_replay_rejects_forged_root_vector() -> None:
    compiled, page, cluster, candidate = _evaluate()
    forged = copy.deepcopy(candidate)
    root = next(mapping for mapping in forged["mappings"] if mapping["role"] == "FAMILY_TOTAL")
    root["report_norm_id"] = 999999
    with pytest.raises(GeminiJsonEquityMatrixAccountingFamilyV1Error, match="does not replay"):
        validate_gemini_json_equity_matrix_family_candidate_replay_v1(
            forged,
            regions=cluster["component_regions"],
            page_json_by_version={_record(page)["page_json_version_id"]: page},
            compiled_specs=compiled,
            query_receipt=build_gemini_json_equity_matrix_region_query_receipt_v1(
                cluster["component_regions"], owner_receipt=cluster["owner_receipt"]
            ),
            document_unit_context_evidence=cluster["document_unit_context_evidence"],
        )


def test_incomplete_declared_matrix_has_typed_unresolved_reason() -> None:
    table = _table()
    table["rows"] = table["rows"][:-1]
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(_page(table))], compiled_specs=_compiled()
    )
    assert cluster["status"] != READY
    assert cluster["component_regions"] == []
    assert cluster["reasons"] == ["EXACTLY_ONE_COMPONENT_GRAND_TOTAL_REQUIRED"]


def test_date_only_boundaries_and_nested_movement_headers_resolve_generically() -> None:
    table = _table()
    table["columns"] = [
        {"header_path_exact": ["1.1.2025", "Triệu VND"], "value_kind": "MONEY"},
        {
            "header_path_exact": ["Phát sinh trong kỳ", "Số phải nộp", "Triệu VND"],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": ["Phát sinh trong kỳ", "Số đã nộp", "Triệu VND"],
            "value_kind": "MONEY",
        },
        {"header_path_exact": ["30.6.2025", "Triệu VND"], "value_kind": "MONEY"},
    ]
    page = _page(table)
    compiled = _compiled()
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    candidate = evaluate_gemini_json_equity_matrix_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={_record(page)["page_json_version_id"]: page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_equity_matrix_region_query_receipt_v1(
            cluster["component_regions"], owner_receipt=cluster["owner_receipt"]
        ),
        document_unit_context_evidence=cluster["document_unit_context_evidence"],
    )
    assert candidate["status"] == READY
    assert [item["axis_role"] for item in candidate["closure_receipt"]["movement_axis"]] == [
        "OPENING",
        "INCREASE",
        "DECREASE",
        "CLOSING",
    ]


def test_mapped_group_total_is_mapped_once_and_children_close_locally() -> None:
    table = _table()
    table["rows"] = [
        table["rows"][0],
        table["rows"][1],
        {
            "hierarchy_path_exact": ["Các loại thuế khác"],
            "label_exact": "Các loại thuế khác",
            "row_kind": "GROUP",
            "values_exact": ["1", "2", "1", "2"],
        },
        {
            "hierarchy_path_exact": ["Các loại thuế khác", "Thuế môn bài"],
            "label_exact": "Thuế môn bài",
            "row_kind": "ITEM",
            "values_exact": ["-", "1", "1", "-"],
        },
        {
            "hierarchy_path_exact": ["Các loại thuế khác", "Thuế thu nhập cá nhân"],
            "label_exact": "Thuế thu nhập cá nhân",
            "row_kind": "ITEM",
            "values_exact": ["1", "1", "-", "2"],
        },
        table["rows"][2],
        {
            "hierarchy_path_exact": ["Tổng cộng"],
            "label_exact": "Tổng cộng",
            "row_kind": "TOTAL",
            "values_exact": ["32", "13", "12", "33"],
        },
    ]
    _compiled_specs, _page_json, _cluster, candidate = _evaluate(table)
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert by_role["OTHER_TAX"]["component_axis"]["kind"] == ("MAPPED_COMPONENT_GROUP_TOTAL")
    assert [value["coefficient"] for value in by_role["OTHER_TAX"]["values"]] == [1, 2, 1, 2]
    assert [value["coefficient"] for value in by_role["PERSONAL_INCOME_TAX"]["values"]] == [
        1,
        1,
        0,
        2,
    ]
    assert [value["coefficient"] for value in by_role["FAMILY_TOTAL"]["values"]] == [
        32,
        13,
        12,
        33,
    ]


def test_flattened_declared_group_hierarchy_is_recovered_without_row_kind_authority() -> None:
    table = _table()
    table["rows"] = [
        table["rows"][0],
        table["rows"][1],
        {
            "hierarchy_path_exact": ["Các loại thuế khác"],
            "label_exact": "Các loại thuế khác",
            "row_kind": "ITEM",
            "values_exact": ["1", "2", "1", "2"],
        },
        {
            "hierarchy_path_exact": ["Các loại thuế khác- Thuế môn bài"],
            "label_exact": "Thuế môn bài",
            "row_kind": "ITEM",
            "values_exact": ["-", "1", "1", "-"],
        },
        {
            "hierarchy_path_exact": ["Các loại thuế khác- Thuế thu nhập cá nhân"],
            "label_exact": "Thuế thu nhập cá nhân",
            "row_kind": "ITEM",
            "values_exact": ["1", "1", "-", "2"],
        },
        table["rows"][2],
        {
            "hierarchy_path_exact": ["Tổng cộng"],
            "label_exact": "Tổng cộng",
            "row_kind": "TOTAL",
            "values_exact": ["32", "13", "12", "33"],
        },
    ]
    _compiled_specs, _page_json, _cluster, candidate = _evaluate(table)
    group = candidate["closure_receipt"]["component_axis"][2]
    child = candidate["closure_receipt"]["component_axis"][3]
    assert candidate["status"] == READY
    assert group["kind"] == "MAPPED_COMPONENT_GROUP_TOTAL"
    assert group["hierarchy_resolution"] == {
        "child_axis_ids": ["r4", "r5"],
        "rule": "DECLARED_MAPPED_GROUP_PROMOTED_BY_FOLLOWING_DEEPER_SEMANTIC_PATHS",
    }
    assert child["semantic_path"] == ["cac loai thue khac", "thue mon bai"]
    assert next(mapping for mapping in candidate["mappings"] if mapping["role"] == "OTHER_PAYABLE")[
        "component_axis"
    ]["semantic_path"] == ["cac loai thue khac phi va le phi"]


def test_last_source_group_total_owning_full_population_is_grand_total() -> None:
    table = _table()
    parent = "Nghĩa vụ với ngân sách nhà nước"
    for row in table["rows"][:-1]:
        row["hierarchy_path_exact"] = [parent, *row["hierarchy_path_exact"]]
    table["rows"][-1]["hierarchy_path_exact"] = [parent]
    _compiled_specs, _page_json, _cluster, candidate = _evaluate(table)
    total = candidate["closure_receipt"]["component_axis"][-1]
    assert candidate["status"] == READY
    assert total["kind"] == "GRAND_TOTAL"
    assert total["hierarchy_resolution"]["source_group_prefix"] == [
        "nghia vu voi ngan sach nha nuoc"
    ]


def test_declared_disclosure_variants_do_not_fall_back_to_parent_cit_role() -> None:
    table = _table()
    table["rows"] = [
        table["rows"][0],
        table["rows"][1],
        {
            "hierarchy_path_exact": ["Thuế TNDN", "Trong đó:"],
            "label_exact": "Trong đó:",
            "row_kind": "GROUP",
            "values_exact": [None, None, None, None],
        },
        {
            "hierarchy_path_exact": ["Thuế TNDN", "Trong đó:", "Thuế TNDN của Vietcombank"],
            "label_exact": "Thuế TNDN của Vietcombank",
            "row_kind": "ITEM",
            "values_exact": ["20", "4", "7", "17"],
        },
        {
            "hierarchy_path_exact": [
                "Thuế TNDN",
                "Trong đó:",
                "Nghĩa vụ thuế năm 2008 của Vinafico đã được Ngân hàng nộp vào NSNN",
            ],
            "label_exact": "Nghĩa vụ thuế năm 2008 của Vinafico đã được Ngân hàng nộp vào NSNN",
            "row_kind": "ITEM",
            "values_exact": ["-", "-", "-", "-"],
        },
        table["rows"][2],
        table["rows"][3],
    ]
    classification = classify_gemini_json_equity_matrix_table_v1(table, compiled_specs=_compiled())
    assert classification["status"] == "MATRIX_FRAGMENT"
    assert [classification["component_axis"][index]["role"] for index in (3, 4)] == [
        "BANK_CIT_DETAIL",
        "LEGACY_VFC_TAX",
    ]


@pytest.mark.parametrize(
    "source_exact",
    [
        "Nghĩa vụ thuế năm 2008 của Vinafico đã được Ngân hàng nộp vào Ngân sách Nhà nước",
        "Nghĩa vụ thuế năm 2008 của Vinafico\nđã được Vietcombank nộp vào NSNN",
    ],
)
def test_legacy_vfc_source_variants_remain_disclosure_only(source_exact: str) -> None:
    table = _table()
    table["rows"].insert(
        2,
        {
            "hierarchy_path_exact": ["Thuế TNDN", "Trong đó:"],
            "label_exact": "Trong đó:",
            "row_kind": "GROUP",
            "values_exact": [None, None, None, None],
        },
    )
    table["rows"].insert(
        3,
        {
            "hierarchy_path_exact": ["Thuế TNDN", "Trong đó:", source_exact],
            "label_exact": source_exact,
            "row_kind": "ITEM",
            "values_exact": ["-", "-", "-", "-"],
        },
    )
    classification = classify_gemini_json_equity_matrix_table_v1(table, compiled_specs=_compiled())
    assert classification["status"] == "MATRIX_FRAGMENT"
    assert classification["component_axis"][3]["kind"] == "DISCLOSURE_COMPONENT"
    assert classification["component_axis"][3]["role"] == "LEGACY_VFC_TAX"


def test_short_explicit_state_budget_owner_is_sufficient() -> None:
    page = _page(_table())
    page["sections"][0]["title_exact"] = "33. Nghĩa vụ với Ngân sách Nhà nước"
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == READY


def test_disclosure_children_reconcile_prior_component_without_double_counting() -> None:
    table = _table()
    table["rows"] = [
        table["rows"][0],
        table["rows"][1],
        {
            "hierarchy_path_exact": ["Trong đó"],
            "label_exact": "Trong đó:",
            "row_kind": "GROUP",
            "values_exact": [None, None, None, None],
        },
        {
            "hierarchy_path_exact": ["Trong đó", "Thuế TNDN của Ngân hàng"],
            "label_exact": "Thuế TNDN của Ngân hàng",
            "row_kind": "ITEM",
            "values_exact": ["20", "3", "6", "17"],
        },
        {
            "hierarchy_path_exact": ["Trong đó", "Điều chỉnh thuế các năm trước"],
            "label_exact": "Điều chỉnh thuế các năm trước",
            "row_kind": "ITEM",
            "values_exact": ["-", "1", "1", "-"],
        },
        table["rows"][2],
        table["rows"][3],
    ]
    _compiled_specs, _page_json, _cluster, candidate = _evaluate(table)
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "FAMILY_TOTAL",
        "VAT",
        "CORPORATE_INCOME_TAX",
        "OTHER_PAYABLE",
    }
    disclosure = [
        equation
        for equation in candidate["closure_receipt"]["equations"]
        if equation["equation_kind"] == "VISIBLE_DISCLOSURE_CHILDREN_EQUAL_PRIOR_MAPPED_COMPONENT"
    ]
    assert len(disclosure) == 4
    assert all(equation["status"] == "EXACT" for equation in disclosure)


def test_unique_latest_dated_same_page_matrix_is_current_not_source_order() -> None:
    comparative = _table()
    comparative["title_exact"] = "Năm kết thúc ngày 31 tháng 12 năm 2024"
    current = copy.deepcopy(_table())
    current["title_exact"] = "Năm kết thúc ngày 31 tháng 12 năm 2025"
    page = _page(comparative)
    page["sections"][0]["tables"] = [comparative, current]
    compiled = _compiled()
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    assert cluster["component_regions"][0]["table_id"] == "t2"
    receipt = cluster["owner_receipt"]["period_selection_receipt"]
    assert receipt["current_date"] == "2025-12-31"
    assert receipt["comparative_date"] == "2024-12-31"
    assert [item["disposition"] for item in cluster["declared_table_inventory"]] == [
        "AUTHENTICATED_COMPARATIVE_MATRIX_FRAGMENT",
        "SELECTED_MATRIX_FRAGMENT",
    ]


def test_declared_duplicate_role_rows_aggregate_after_each_row_closes() -> None:
    table = _table()
    table["rows"].insert(
        3,
        {
            "hierarchy_path_exact": ["Tiền thuê đất"],
            "label_exact": "Tiền thuê đất",
            "row_kind": "ITEM",
            "values_exact": ["-", "1", "1", "-"],
        },
    )
    table["rows"][-1]["values_exact"] = ["31", "12", "12", "31"]
    _compiled_specs, _page_json, _cluster, candidate = _evaluate(table)
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    aggregate = by_role["OTHER_PAYABLE"]
    assert aggregate["component_axis"]["kind"] == "AGGREGATED_MAPPED_COMPONENT"
    assert [value["coefficient"] for value in aggregate["values"]] == [1, 3, 2, 2]
    assert all(len(value["aggregate_components"]) == 2 for value in aggregate["values"])


def test_closing_detail_columns_must_decompose_visible_net_closing() -> None:
    table = _table()
    table["columns"] = [
        table["columns"][0],
        table["columns"][1],
        table["columns"][2],
        {"header_path_exact": ["Số dư cuối kỳ", "Phải trả"], "value_kind": "MONEY"},
        {"header_path_exact": ["Số dư cuối kỳ", "Phải thu"], "value_kind": "MONEY"},
        {"header_path_exact": ["Số dư cuối kỳ", "Tổng cộng"], "value_kind": "MONEY"},
    ]
    table["rows"][0]["values_exact"] = ["10", "5", "3", "15", "(3)", "12"]
    table["rows"][1]["values_exact"] = ["20", "4", "7", "18", "(1)", "17"]
    table["rows"][2]["values_exact"] = ["1", "2", "1", "3", "(1)", "2"]
    table["rows"][3]["values_exact"] = ["31", "11", "11", "36", "(5)", "31"]
    _compiled_specs, _page_json, _cluster, candidate = _evaluate(table)
    assert candidate["status"] == READY
    assert all(len(mapping["values"]) == 4 for mapping in candidate["mappings"])
    decomposition = [
        equation
        for equation in candidate["closure_receipt"]["equations"]
        if equation["equation_kind"] == "DECLARED_SUPPLEMENTAL_MOVEMENT_DECOMPOSITION"
    ]
    assert len(decomposition) == 4
    assert all(equation["status"] == "EXACT" for equation in decomposition)


def test_dated_closing_total_with_embedded_unit_authenticates_decomposition_result() -> None:
    table = _table()
    table["columns"] = [
        {"header_path_exact": ["Số dư tại ngày 1/1/2025\nTriệu VND"], "value_kind": "MONEY"},
        {"header_path_exact": ["Số phải nộp\nTriệu VND"], "value_kind": "MONEY"},
        {"header_path_exact": ["Số đã nộp\nTriệu VND"], "value_kind": "MONEY"},
        {
            "header_path_exact": ["Số dư tại ngày 31/12/2025", "Phải trả\nTriệu VND"],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": ["Số dư tại ngày 31/12/2025", "Ứng trước\nTriệu VND"],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": ["Số dư tại ngày 31/12/2025", "Tổng cộng\nTriệu VND"],
            "value_kind": "MONEY",
        },
    ]
    table["rows"][0]["values_exact"] = ["10", "5", "3", "15", "(3)", "12"]
    table["rows"][1]["values_exact"] = ["20", "4", "7", "18", "(1)", "17"]
    table["rows"][2]["values_exact"] = ["1", "2", "1", "3", "(1)", "2"]
    table["rows"][3]["values_exact"] = ["31", "11", "11", "36", "(5)", "31"]
    _compiled_specs, _page_json, _cluster, candidate = _evaluate(table)
    assert candidate["status"] == READY


def test_paid_wording_is_a_declared_decrease_without_prompt_repair() -> None:
    table = _table()
    table["columns"][1]["header_path_exact"] = ["Phát sinh trong năm", "Phải trả"]
    table["columns"][2]["header_path_exact"] = ["Phát sinh trong năm", "Đã trả"]
    _compiled_specs, _page_json, _cluster, candidate = _evaluate(table)
    assert candidate["status"] == READY
    assert candidate["closure_receipt"]["movement_axis"][2]["axis_role"] == "DECREASE"


def test_balance_side_subheader_does_not_override_incompatible_primary_movement() -> None:
    table = _table()
    table["columns"] = [
        {"header_path_exact": ["Số đầu năm", "Phải trả"], "value_kind": "MONEY"},
        {"header_path_exact": ["Phát sinh trong năm", "Phát sinh tăng"], "value_kind": "MONEY"},
        {"header_path_exact": ["Phát sinh trong năm", "Phát sinh giảm"], "value_kind": "MONEY"},
        {"header_path_exact": ["Số cuối năm", "Phải trả"], "value_kind": "MONEY"},
    ]
    _compiled_specs, _page_json, _cluster, candidate = _evaluate(table)
    assert candidate["status"] == READY
    assert [item["axis_role"] for item in candidate["closure_receipt"]["movement_axis"]] == [
        "OPENING",
        "INCREASE",
        "DECREASE",
        "CLOSING",
    ]


def test_source_visible_business_combination_column_extends_mapping_vector() -> None:
    table = _table()
    table["columns"] = [
        table["columns"][0],
        {
            "header_path_exact": ["Phát sinh trong kỳ", "Tăng do hợp nhất kinh doanh"],
            "value_kind": "MONEY",
        },
        table["columns"][1],
        table["columns"][2],
        table["columns"][3],
    ]
    table["rows"][0]["values_exact"] = ["10", "2", "5", "3", "14"]
    table["rows"][1]["values_exact"] = ["20", "1", "4", "7", "18"]
    table["rows"][2]["values_exact"] = ["1", "-", "2", "1", "2"]
    table["rows"][3]["values_exact"] = ["31", "3", "11", "11", "34"]
    _compiled_specs, _page_json, _cluster, candidate = _evaluate(table)
    root = next(mapping for mapping in candidate["mappings"] if mapping["role"] == "FAMILY_TOTAL")
    assert candidate["status"] == READY
    assert [value["axis_role"] for value in root["values"]] == [
        "OPENING",
        "BUSINESS_COMBINATION_INCREASE",
        "INCREASE",
        "DECREASE",
        "CLOSING",
    ]
    assert [value["coefficient"] for value in root["values"]] == [31, 3, 11, 11, 34]


def _signed_branch_rows() -> tuple[list[dict], list[dict]]:
    receivable = [
        {
            "hierarchy_path_exact": ["a. Phải thu"],
            "label_exact": "a. Phải thu",
            "row_kind": "GROUP",
            "values_exact": [None, None, None, None],
        },
        {
            "hierarchy_path_exact": ["a. Phải thu", "Thuế GTGT"],
            "label_exact": "Thuế GTGT",
            "row_kind": "ITEM",
            "values_exact": ["10", "2", "1", "9"],
        },
        {
            "hierarchy_path_exact": ["a. Phải thu", "Thuế TNDN"],
            "label_exact": "Thuế TNDN",
            "row_kind": "ITEM",
            "values_exact": ["5", "1", "2", "6"],
        },
        {
            "hierarchy_path_exact": ["a. Phải thu", None],
            "label_exact": None,
            "row_kind": "SUBTOTAL",
            "values_exact": ["15", "3", "3", "15"],
        },
    ]
    payable = [
        {
            "hierarchy_path_exact": ["b. Phải trả"],
            "label_exact": "b. Phải trả",
            "row_kind": "GROUP",
            "values_exact": [None, None, None, None],
        },
        {
            "hierarchy_path_exact": ["b. Phải trả", "Thuế GTGT"],
            "label_exact": "Thuế GTGT",
            "row_kind": "ITEM",
            "values_exact": ["100", "20", "10", "110"],
        },
        {
            "hierarchy_path_exact": ["b. Phải trả", "Thuế TNDN"],
            "label_exact": "Thuế TNDN",
            "row_kind": "ITEM",
            "values_exact": ["50", "10", "5", "55"],
        },
        {
            "hierarchy_path_exact": ["b. Phải trả", "Các loại thuế khác"],
            "label_exact": "Các loại thuế khác",
            "row_kind": "ITEM",
            "values_exact": ["10", "2", "1", "11"],
        },
        {
            "hierarchy_path_exact": ["b. Phải trả", None],
            "label_exact": None,
            "row_kind": "SUBTOTAL",
            "values_exact": ["160", "32", "16", "176"],
        },
    ]
    return receivable, payable


def _signed_branch_table(rows: list[dict]) -> dict:
    table = _table()
    table["rows"] = rows
    return table


def test_signed_receivable_and_payable_branches_close_before_net_projection() -> None:
    receivable, payable = _signed_branch_rows()
    _compiled_specs, _page_json, _cluster, candidate = _evaluate(
        _signed_branch_table([*receivable, *payable])
    )
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert [value["coefficient"] for value in by_role["FAMILY_TOTAL"]["values"]] == [
        145,
        35,
        -19,
        161,
    ]
    assert [value["coefficient"] for value in by_role["VAT"]["values"]] == [
        90,
        22,
        -11,
        101,
    ]
    receipt = candidate["closure_receipt"]["signed_branch_receipt"]
    assert receipt["branch_multipliers"] == {"PAYABLE": 1, "RECEIVABLE": -1}
    assert receipt["branch_movement_multipliers"] == {
        "PAYABLE": {"CLOSING": 1, "DECREASE": -1, "INCREASE": 1, "OPENING": 1},
        "RECEIVABLE": {"CLOSING": 1, "DECREASE": 1, "INCREASE": -1, "OPENING": 1},
    }
    assert list(
        dict.fromkeys(
            equation["branch_role"]
            for equation in candidate["closure_receipt"]["equations"]
            if "branch_role" in equation
        )
    ) == ["PAYABLE", "RECEIVABLE"]


def test_same_page_signed_branch_siblings_are_one_exact_cluster() -> None:
    receivable, payable = _signed_branch_rows()
    page = _page(_signed_branch_table(receivable))
    page["sections"][0]["tables"].append(_signed_branch_table(payable))
    compiled = _compiled()
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    assert [region["table_id"] for region in cluster["component_regions"]] == ["t1", "t2"]
    candidate = evaluate_gemini_json_equity_matrix_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={_record(page)["page_json_version_id"]: page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_equity_matrix_region_query_receipt_v1(
            cluster["component_regions"], owner_receipt=cluster["owner_receipt"]
        ),
        document_unit_context_evidence=cluster["document_unit_context_evidence"],
    )
    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 4


def test_signed_branch_outer_date_columns_authenticate_opening_and_closing() -> None:
    receivable, payable = _signed_branch_rows()
    table = _signed_branch_table([*receivable, *payable])
    table["columns"] = [
        {"header_path_exact": ["1.1.2025", "Triệu đồng"], "value_kind": "MONEY"},
        {
            "header_path_exact": ["Phát sinh trong năm", "Số phải thu/ phải nộp"],
            "value_kind": "MONEY",
        },
        {"header_path_exact": ["Phát sinh trong năm", "Số đã nộp"], "value_kind": "MONEY"},
        {"header_path_exact": ["31.12.2025", "Triệu đồng"], "value_kind": "MONEY"},
    ]
    _compiled_specs, _page_json, _cluster, candidate = _evaluate(table)
    assert candidate["status"] == READY


def test_signed_branch_formula_markers_do_not_hide_movement_labels() -> None:
    receivable, payable = _signed_branch_rows()
    table = _signed_branch_table([*receivable, *payable])
    table["columns"] = [
        {"header_path_exact": ["1.1.2025\nTriệu đồng\n(a)"], "value_kind": "MONEY"},
        {
            "header_path_exact": ["Phát sinh trong kỳ", "Số phải nộp\nTriệu đồng\n(b)"],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": ["Phát sinh trong kỳ", "Số đã nộp\nTriệu đồng\n(c)"],
            "value_kind": "MONEY",
        },
        {"header_path_exact": ["30.6.2025\nTriệu đồng\n(d)=(a)+(b)-(c)"], "value_kind": "MONEY"},
    ]
    _compiled_specs, _page_json, _cluster, candidate = _evaluate(table)
    assert candidate["status"] == READY


def test_signed_branch_interior_date_does_not_become_a_balance_endpoint() -> None:
    receivable, payable = _signed_branch_rows()
    table = _signed_branch_table([*receivable, *payable])
    table["columns"] = [
        {"header_path_exact": ["1.1.2025"], "value_kind": "MONEY"},
        {"header_path_exact": ["30.6.2025", "Số phải nộp"], "value_kind": "MONEY"},
        {"header_path_exact": ["Số đã nộp"], "value_kind": "MONEY"},
        {"header_path_exact": ["31.12.2025"], "value_kind": "MONEY"},
    ]
    _compiled_specs, _page_json, _cluster, candidate = _evaluate(table)
    assert candidate["status"] != READY
    assert candidate["mappings"] == []
    assert "SIGNED_BRANCH_EXACT_PRIMARY_MOVEMENT_AXIS_REQUIRED" in candidate["reasons"]


def test_signed_branch_subtotal_mismatch_is_unresolved_without_mappings() -> None:
    receivable, payable = _signed_branch_rows()
    payable[-1]["values_exact"][0] = "161"
    _compiled_specs, _page_json, _cluster, candidate = _evaluate(
        _signed_branch_table([*receivable, *payable])
    )
    assert candidate["status"] != READY
    assert candidate["mappings"] == []
    assert "SIGNED_BRANCH_HORIZONTAL_TOTAL_MISMATCH" in candidate["reasons"]


def test_single_signed_branch_cannot_emit_a_net_family_mapping() -> None:
    _receivable, payable = _signed_branch_rows()
    page = _page(_signed_branch_table(payable))
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] != READY
    assert cluster["component_regions"] == []
    assert "SIGNED_BRANCH_EXACT_DECLARED_DOCUMENT_FRONTIER_REQUIRED" in cluster["reasons"]


def test_duplicate_component_role_within_one_signed_branch_is_unresolved() -> None:
    receivable, payable = _signed_branch_rows()
    duplicate_vat = copy.deepcopy(payable[1])
    payable.insert(-1, duplicate_vat)
    page = _page(_signed_branch_table([*receivable, *payable]))
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] != READY
    assert cluster["component_regions"] == []
    assert "DUPLICATE_MAPPED_COMPONENT_ROLE_WITHIN_SIGNED_BRANCH" in cluster["reasons"]


def test_candidate_replay_rejects_coherently_rehashed_signed_branch_receipt() -> None:
    receivable, payable = _signed_branch_rows()
    compiled, page, cluster, candidate = _evaluate(_signed_branch_table([*receivable, *payable]))
    forged = copy.deepcopy(candidate)
    forged["closure_receipt"]["signed_branch_receipt"]["branch_multipliers"]["PAYABLE"] = -1
    forged["candidate_id"] = "gjeqmfv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in forged.items() if key != "candidate_id"}
    )
    with pytest.raises(GeminiJsonEquityMatrixAccountingFamilyV1Error, match="does not replay"):
        validate_gemini_json_equity_matrix_family_candidate_replay_v1(
            forged,
            regions=cluster["component_regions"],
            page_json_by_version={_record(page)["page_json_version_id"]: page},
            compiled_specs=compiled,
            query_receipt=build_gemini_json_equity_matrix_region_query_receipt_v1(
                cluster["component_regions"], owner_receipt=cluster["owner_receipt"]
            ),
            document_unit_context_evidence=cluster["document_unit_context_evidence"],
        )
