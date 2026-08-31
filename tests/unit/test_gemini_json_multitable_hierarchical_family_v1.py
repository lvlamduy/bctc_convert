from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    NOT_OBSERVED,
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
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "a" * 64
SOURCE_SHA256 = "b" * 64
VERSION_ID = "gfpstorev1:json:" + "c" * 64


def _json(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-other-assets-topology-v1.json"),
        _json("tm-other-assets-evaluation-v1.json"),
        _json("tm-other-assets-schema-binding-v1.json"),
    )


def _government_compiled() -> dict:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-government-sbv-liabilities-topology-v1.json"),
        _json("tm-government-sbv-liabilities-evaluation-v1.json"),
        _json("tm-government-sbv-liabilities-schema-binding-v1.json"),
    )


def _entrusted_compiled() -> dict:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-entrusted-investment-risk-capital-topology-v1.json"),
        _json("tm-entrusted-investment-risk-capital-evaluation-v1.json"),
        _json("tm-entrusted-investment-risk-capital-schema-binding-v1.json"),
    )


def _interest_income_compiled() -> dict:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-interest-income-topology-v1.json"),
        _json("tm-interest-income-evaluation-v1.json"),
        _json("tm-interest-income-schema-binding-v1.json"),
    )


def _interest_expense_compiled() -> dict:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-interest-expense-topology-v1.json"),
        _json("tm-interest-expense-evaluation-v1.json"),
        _json("tm-interest-expense-schema-binding-v1.json"),
    )


def _interbank_funding_compiled() -> dict:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-interbank-funding-topology-v1.json"),
        _json("tm-interbank-funding-evaluation-v1.json"),
        _json("tm-interbank-funding-schema-binding-v1.json"),
    )


def _customer_collateral_compiled() -> dict:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-customer-collateral-held-topology-v1.json"),
        _json("tm-customer-collateral-held-evaluation-v1.json"),
        _json("tm-customer-collateral-held-schema-binding-v1.json"),
    )


def _bank_pledged_assets_compiled() -> dict:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-bank-pledged-discounted-assets-topology-v1.json"),
        _json("tm-bank-pledged-discounted-assets-evaluation-v1.json"),
        _json("tm-bank-pledged-discounted-assets-schema-binding-v1.json"),
    )


def _contingent_liabilities_compiled() -> dict:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-contingent-liabilities-commitments-topology-v1.json"),
        _json("tm-contingent-liabilities-commitments-evaluation-v1.json"),
        _json("tm-contingent-liabilities-commitments-schema-binding-v1.json"),
    )


def _columns(current: str = "31/12/2025", comparative: str = "31/12/2024") -> list[dict]:
    return [
        {"header_path_exact": [current, "Triệu đồng"], "value_kind": "MONEY"},
        {"header_path_exact": [comparative, "Triệu đồng"], "value_kind": "MONEY"},
    ]


def _row(
    label: str | None,
    values: list[str | None],
    *,
    kind: str = "ITEM",
    hierarchy: list[str | None] | None = None,
) -> dict:
    return {
        "hierarchy_path_exact": [label] if hierarchy is None else hierarchy,
        "label_exact": label,
        "row_kind": kind,
        "values_exact": values,
    }


def _table(
    title: str | None,
    rows: list[dict],
    *,
    columns: list[dict] | None = None,
    unit: str = "Triệu đồng",
) -> dict:
    return {
        "columns": _columns() if columns is None else columns,
        "continuation": "NONE",
        "rows": rows,
        "title_exact": title,
        "unit_exact": unit,
    }


def _section(
    title: str,
    *tables: dict,
    narratives: list[str] | None = None,
) -> dict:
    return {
        "content_kind": "FINANCIAL_NOTE",
        "narratives_exact": [] if narratives is None else narratives,
        "statement_type": "NOT_APPLICABLE",
        "tables": list(tables),
        "title_exact": title,
    }


def _page(*sections: dict) -> dict:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": list(sections),
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _record(page: dict) -> dict:
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


def _evaluate(page: dict) -> tuple[dict, dict, dict]:
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
    return compiled, cluster, candidate


def _evaluate_interest_income(page: dict) -> tuple[dict, dict, dict]:
    compiled = _interest_income_compiled()
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
    return compiled, cluster, candidate


def _evaluate_interest_expense(page: dict) -> tuple[dict, dict, dict]:
    compiled = _interest_expense_compiled()
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
    return compiled, cluster, candidate


def _evaluate_interbank_funding(page: dict) -> tuple[dict, dict, dict]:
    compiled = _interbank_funding_compiled()
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
    return compiled, cluster, candidate


def _evaluate_bank_pledged_assets(page: dict) -> tuple[dict, dict, dict]:
    compiled = _bank_pledged_assets_compiled()
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
    return compiled, cluster, candidate


def _evaluate_contingent_liabilities(page: dict) -> tuple[dict, dict, dict]:
    compiled = _contingent_liabilities_compiled()
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
    return compiled, cluster, candidate


def _summary_page() -> dict:
    receivables = _table(
        "Các khoản phải thu",
        [
            _row("Các khoản phải thu", ["100", "80"], kind="GROUP"),
            _row(
                "Các khoản phải thu bên ngoài",
                ["60", "50"],
                hierarchy=["Các khoản phải thu", "Các khoản phải thu bên ngoài"],
            ),
            _row(
                "Xây dựng cơ bản dở dang",
                ["30", "20"],
                hierarchy=["Các khoản phải thu", "Xây dựng cơ bản dở dang"],
            ),
            _row(
                "Khoản nguồn chỉ đọc",
                ["10", "10"],
                hierarchy=["Các khoản phải thu", "Khoản nguồn chỉ đọc"],
            ),
            _row(None, ["100", "80"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    other = _table(
        "Tài sản Có khác",
        [
            _row("Tài sản Có khác", ["30", "20"], kind="GROUP"),
            _row(
                "Chi phí trả trước",
                ["30", "20"],
                hierarchy=["Tài sản Có khác", "Chi phí trả trước"],
            ),
            _row(None, ["30", "20"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    return _page(_section("14. TÀI SẢN CÓ KHÁC", receivables, other))


def test_multitable_source_only_rows_are_retained_but_not_forced_into_schema() -> None:
    _compiled_specs, _cluster, candidate = _evaluate(_summary_page())
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert set(by_role) == {
        "CONSTRUCTION_IN_PROGRESS",
        "EXTERNAL_RECEIVABLES",
        "OTHER_ASSET_BRANCH",
        "PREPAID_COST",
        "RECEIVABLES",
    }
    assert [cell["coefficient"] for cell in by_role["RECEIVABLES"]["values"]] == [
        100,
        80,
    ]
    source_only = candidate["closure_receipt"]["source_only_unmapped_rows"]
    assert len(source_only) == 1
    assert source_only[0]["consumed_by_exact_equation"] is True


def test_same_section_previous_family_table_is_excluded_before_first_anchor() -> None:
    prior = _table(
        None,
        [
            _row("Số dư đầu năm", ["10", "8"]),
            _row("Số dư cuối năm", ["9", "7"]),
        ],
        columns=[
            {"header_path_exact": ["Nguyên giá", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Hao mòn", "Triệu đồng"], "value_kind": "MONEY"},
        ],
    )
    page = _summary_page()
    page["sections"][0]["narratives_exact"] = [
        "13. Tài sản cố định vô hình",
        "14. TÀI SẢN CÓ KHÁC",
    ]
    page["sections"][0]["tables"].insert(0, prior)
    _compiled_specs, cluster, candidate = _evaluate(page)
    assert candidate["status"] == READY
    dispositions = [item["disposition"] for item in cluster["declared_money_table_inventory"]]
    assert dispositions.count("EXCLUDED_PRE_OWNER_SAME_SECTION_TABLE") == 1


def test_duplicate_role_siblings_sum_but_nested_trong_do_uses_carrier_once() -> None:
    table = _table(
        "Các khoản phải thu",
        [
            _row("Các khoản phải thu bên ngoài", ["100", "80"], kind="GROUP"),
            _row(
                "Mua hẳn miễn truy đòi bộ chứng từ theo thư tín dụng",
                ["70", "50"],
                hierarchy=[
                    "Các khoản phải thu bên ngoài",
                    "Mua hẳn miễn truy đòi bộ chứng từ theo thư tín dụng",
                ],
            ),
            _row(
                "Trong đó: Mua hẳn miễn truy đòi bộ chứng từ theo thư tín dụng do TCTD khác phát hành",
                ["10", "5"],
                hierarchy=[
                    "Các khoản phải thu bên ngoài",
                    "Mua hẳn miễn truy đòi bộ chứng từ theo thư tín dụng",
                    "Trong đó: Mua hẳn miễn truy đòi bộ chứng từ theo thư tín dụng do TCTD khác phát hành",
                ],
            ),
            _row(
                "Khoản nguồn khác",
                ["30", "30"],
                hierarchy=["Các khoản phải thu bên ngoài", "Khoản nguồn khác"],
            ),
            _row(None, ["100", "80"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    page = _page(_section("TÀI SẢN CÓ KHÁC", table))
    _compiled_specs, _cluster, candidate = _evaluate(page)
    mapping = next(
        item
        for item in candidate["mappings"]
        if item["role"] == "WITHOUT_RECOURSE_DOCUMENT_RECEIVABLE"
    )
    assert [cell["coefficient"] for cell in mapping["values"]] == [70, 50]
    assert {item["row_id"] for item in mapping["source_refs"]} == {"r2"}

    sibling = copy.deepcopy(page)
    rows = sibling["sections"][0]["tables"][0]["rows"]
    rows[1:3] = [
        _row(
            "Mua hẳn miễn truy đòi bộ chứng từ theo thư tín dụng do ngân hàng phát hành",
            ["40", "30"],
            hierarchy=["Các khoản phải thu bên ngoài", "Loại một"],
        ),
        _row(
            "Mua hẳn miễn truy đòi bộ chứng từ theo thư tín dụng do TCTD khác phát hành",
            ["30", "20"],
            hierarchy=["Các khoản phải thu bên ngoài", "Loại hai"],
        ),
    ]
    _compiled_specs, _cluster, candidate = _evaluate(sibling)
    mapping = next(
        item
        for item in candidate["mappings"]
        if item["role"] == "WITHOUT_RECOURSE_DOCUMENT_RECEIVABLE"
    )
    assert [cell["coefficient"] for cell in mapping["values"]] == [70, 50]
    assert {item["row_id"] for item in mapping["source_refs"]} == {"r2", "r3"}


def test_distinct_labels_in_separate_tables_sum_for_configured_additive_role() -> None:
    first = _table(
        None,
        [_row("Tạm ứng cho khoản tiền gửi, tiết kiệm lãi trả trước", ["20", "10"])],
    )
    second = _table(
        None,
        [_row("Chi phí trả trước chờ phân bổ", ["30", "25"])],
    )
    page = _page(
        _section("Các khoản phải thu", first),
        _section("TÀI SẢN CÓ KHÁC", second),
    )
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == READY
    mapping = next(item for item in candidate["mappings"] if item["role"] == "PREPAID_COST")
    assert [cell["coefficient"] for cell in mapping["values"]] == [50, 35]
    receipts = candidate["closure_receipt"]["cluster_aggregation_receipts"]
    assert len(receipts) == 1
    assert receipts[0]["role"] == "PREPAID_COST"
    assert receipts[0]["rule"] == (
        "CONFIGURED_ROLE_DISTINCT_VISIBLE_LABELS_DISTINCT_TABLES_DIRECT_SUM"
    )


def test_repeated_same_label_across_tables_is_not_assumed_additive() -> None:
    first = _table(None, [_row("Chi phí trả trước", ["20", "10"])])
    second = _table(None, [_row("Chi phí trả trước", ["30", "25"])])
    page = _page(
        _section("Các khoản phải thu", first),
        _section("TÀI SẢN CÓ KHÁC", second),
    )
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert not candidate["closure_receipt"]["cluster_aggregation_receipts"]
    assert candidate["reasons"] == [
        "CONFLICTING_SOURCE_VALUES_FOR_ROLE_LANE:PREPAID_COST:COMPARATIVE_PERIOD",
        "CONFLICTING_SOURCE_VALUES_FOR_ROLE_LANE:PREPAID_COST:CURRENT_PERIOD",
    ]


def test_distinct_valuation_bases_are_selected_not_summed() -> None:
    first = _table(
        None,
        [_row("Tạm ứng cho khoản tiền gửi, tiết kiệm lãi trả trước", ["20", "10"])],
    )
    carrying_columns = [
        {
            "header_path_exact": ["31/12/2025", "Giá trị ghi sổ", "Triệu đồng"],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": ["31/12/2024", "Giá trị ghi sổ", "Triệu đồng"],
            "value_kind": "MONEY",
        },
    ]
    second = _table(
        None,
        [_row("Chi phí trả trước chờ phân bổ", ["30", "25"])],
        columns=carrying_columns,
    )
    page = _page(
        _section("Các khoản phải thu", first),
        _section("TÀI SẢN CÓ KHÁC", second),
    )
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == READY
    mapping = next(item for item in candidate["mappings"] if item["role"] == "PREPAID_COST")
    assert [cell["coefficient"] for cell in mapping["values"]] == [30, 25]
    assert not candidate["closure_receipt"]["cluster_aggregation_receipts"]


def test_distinct_role_rows_aggregate_per_ordered_one_period_lane() -> None:
    current = [{"header_path_exact": ["31/12/2025", "Triệu đồng"], "value_kind": "MONEY"}]
    comparative = [{"header_path_exact": ["31/12/2024", "Triệu đồng"], "value_kind": "MONEY"}]
    tables = [
        _table(
            None,
            [
                _row("Tạm ứng cho khoản tiền gửi, tiết kiệm lãi trả trước", ["20"]),
                _row("Khoản nguồn chỉ đọc", ["0"]),
            ],
            columns=current,
        ),
        _table(
            None,
            [
                _row("Chi phí trả trước chờ phân bổ", ["30"]),
                _row("Khoản nguồn chỉ đọc", ["0"]),
            ],
            columns=current,
        ),
        _table(
            None,
            [
                _row("Tạm ứng cho khoản tiền gửi, tiết kiệm lãi trả trước", ["10"]),
                _row("Khoản nguồn chỉ đọc", ["0"]),
            ],
            columns=comparative,
        ),
        _table(
            None,
            [
                _row("Chi phí trả trước chờ phân bổ", ["25"]),
                _row("Khoản nguồn chỉ đọc", ["0"]),
            ],
            columns=comparative,
        ),
    ]
    _compiled_specs, _cluster, candidate = _evaluate(_page(_section("TÀI SẢN CÓ KHÁC", *tables)))
    assert candidate["status"] == READY
    mapping = next(item for item in candidate["mappings"] if item["role"] == "PREPAID_COST")
    assert [cell["coefficient"] for cell in mapping["values"]] == [50, 35]
    receipts = candidate["closure_receipt"]["cluster_aggregation_receipts"]
    assert [receipt["coefficients"] for receipt in receipts] == [[50], [35]]
    assert [receipt["lane_keys"] for receipt in receipts] == [
        [["DATE", "2025-12-31"]],
        [["DATE", "2024-12-31"]],
    ]


def test_ordered_bare_year_tables_resolve_without_fabricating_dates() -> None:
    current = [{"header_path_exact": ["2025", "Triệu đồng"], "value_kind": "MONEY"}]
    comparative = [{"header_path_exact": ["2024", "Triệu đồng"], "value_kind": "MONEY"}]

    def component(label: str, value: str, columns: list[dict]) -> dict:
        return _table(
            None,
            [_row(label, [value]), _row("Khoản nguồn chỉ đọc", ["0"])],
            columns=columns,
        )

    tables = [
        component("Tạm ứng cho khoản tiền gửi, tiết kiệm lãi trả trước", "20", current),
        component("Chi phí trả trước chờ phân bổ", "30", current),
        component("Tạm ứng cho khoản tiền gửi, tiết kiệm lãi trả trước", "10", comparative),
        component("Chi phí trả trước chờ phân bổ", "25", comparative),
    ]
    _compiled_specs, _cluster, candidate = _evaluate(_page(_section("TÀI SẢN CÓ KHÁC", *tables)))
    assert candidate["status"] == READY
    mapping = next(item for item in candidate["mappings"] if item["role"] == "PREPAID_COST")
    assert [cell["coefficient"] for cell in mapping["values"]] == [50, 35]
    receipts = candidate["closure_receipt"]["cluster_aggregation_receipts"]
    assert [receipt["lane_keys"] for receipt in receipts] == [
        [["BARE_YEAR", "2025"]],
        [["BARE_YEAR", "2024"]],
    ]


def test_document_period_axis_cannot_mix_full_dates_and_bare_years() -> None:
    dated = [{"header_path_exact": ["31/12/2025", "Triệu đồng"], "value_kind": "MONEY"}]
    bare = [{"header_path_exact": ["2024", "Triệu đồng"], "value_kind": "MONEY"}]
    first = _table(
        None,
        [_row("Chi phí trả trước", ["20"]), _row("Khoản nguồn chỉ đọc", ["0"])],
        columns=dated,
    )
    second = _table(
        None,
        [_row("Chi phí trả trước", ["10"]), _row("Khoản nguồn chỉ đọc", ["0"])],
        columns=bare,
    )
    _compiled_specs, _cluster, candidate = _evaluate(
        _page(_section("TÀI SẢN CÓ KHÁC", first, second))
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["reasons"] == ["DOCUMENT_MAPPING_PERIOD_AXIS_MIXES_DATE_AND_BARE_YEAR"]


def test_declared_derived_role_projects_each_ordered_one_period_lane() -> None:
    current = [{"header_path_exact": ["31/12/2025", "Triệu đồng"], "value_kind": "MONEY"}]
    comparative = [{"header_path_exact": ["31/12/2024", "Triệu đồng"], "value_kind": "MONEY"}]

    def component(label: str, value: str, columns: list[dict]) -> dict:
        return _table(
            None,
            [_row(label, [value]), _row("Khoản nguồn chỉ đọc", ["0"])],
            columns=columns,
        )

    tables = [
        component("Mua sắm tài sản cố định", "20", current),
        component("Chi phí xây dựng cơ bản dở dang", "30", current),
        component("Mua sắm tài sản cố định", "10", comparative),
        component("Chi phí xây dựng cơ bản dở dang", "25", comparative),
    ]
    _compiled_specs, _cluster, candidate = _evaluate(_page(_section("TÀI SẢN CÓ KHÁC", *tables)))
    assert candidate["status"] == READY
    mapping = next(item for item in candidate["mappings"] if item["role"] == "CAPEX_RECEIVABLE")
    assert [cell["coefficient"] for cell in mapping["values"]] == [50, 35]
    receipts = candidate["closure_receipt"]["derived_role_receipts"]
    assert [receipt["coefficients"] for receipt in receipts] == [[50], [35]]


def test_blank_zero_in_duplicate_role_requires_exact_source_equation() -> None:
    table = _table(
        None,
        [
            _row("Chi phí trả trước", [None, None]),
            _row("Chi phí trả trước chờ phân bổ", ["10", "8"]),
        ],
    )
    _compiled_specs, _cluster, candidate = _evaluate(_page(_section("TÀI SẢN CÓ KHÁC", table)))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["reasons"] == ["UNPROVEN_CONDITIONAL_BLANK_ZERO_SOURCE_ROW"]
    assert candidate["closure_receipt"]["table_receipts"][0]["unproven_conditional_zero_rows"] == [
        1
    ]

    closed = copy.deepcopy(table)
    closed["rows"].append(_row(None, ["10", "8"], kind="TOTAL", hierarchy=[None]))
    _compiled_specs, _cluster, candidate = _evaluate(_page(_section("TÀI SẢN CÓ KHÁC", closed)))
    assert candidate["status"] == READY
    mapping = next(item for item in candidate["mappings"] if item["role"] == "PREPAID_COST")
    assert [cell["coefficient"] for cell in mapping["values"]] == [10, 8]
    assert not candidate["closure_receipt"]["table_receipts"][0]["unproven_conditional_zero_rows"]


def test_all_blank_structural_group_is_not_mapped_as_zero() -> None:
    table = _table(
        None,
        [
            _row("Tài sản Có khác", [None, None], kind="GROUP"),
            _row(
                "Vật liệu",
                ["10", "8"],
                hierarchy=["Tài sản Có khác", "Vật liệu"],
            ),
            _row(None, ["10", "8"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    _compiled_specs, _cluster, candidate = _evaluate(_page(_section("TÀI SẢN CÓ KHÁC", table)))
    assert candidate["status"] == READY
    mapping = next(item for item in candidate["mappings"] if item["role"] == "OTHER_ASSET_BRANCH")
    assert [cell["coefficient"] for cell in mapping["values"]] == [10, 8]
    assert all(cell["state"] != "INFERRED_CONDITIONAL_BLANK_ZERO" for cell in mapping["values"])


def test_ambiguous_declared_row_inside_selected_owner_fence_fails_closed() -> None:
    ambiguous = _table(None, [_row("Khác", ["10", "8"])])
    valid = _table(None, [_row("Chi phí trả trước", ["20", "15"])])
    page = _page(_section("TÀI SẢN CÓ KHÁC", ambiguous, valid))
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["reasons"] == ["AMBIGUOUS_DECLARED_SOURCE_ROW_ROLE"]
    classification = candidate["closure_receipt"]["table_receipts"][0]["classification"]
    assert classification["ambiguous_rows"] == [
        {
            "matched_roles": ["OTHER_MISC_ASSET", "OTHER_RECEIVABLE"],
            "row_ordinal": 1,
        }
    ]


def test_context_total_corroboration_is_not_summed_as_a_second_observation() -> None:
    summary = _table(
        "Các khoản phải thu",
        [
            _row("Các khoản phải thu khác", ["70", "60"]),
            _row(None, ["70", "60"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    detail = _table(
        None,
        [
            _row("Ký quỹ, đặt cọc", ["40", "30"]),
            _row("Thuế nộp thừa, được khấu trừ", ["30", "30"]),
            _row(None, ["70", "60"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    page = _page(_section("TÀI SẢN CÓ KHÁC", summary, detail))
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == READY
    mapping = next(item for item in candidate["mappings"] if item["role"] == "OTHER_RECEIVABLE")
    assert [cell["coefficient"] for cell in mapping["values"]] == [70, 60]
    assert not candidate["closure_receipt"]["cluster_aggregation_receipts"]


def test_collateral_detail_title_overrides_outer_other_asset_context() -> None:
    compiled = _compiled()
    table = _table(
        (
            "Tài sản thay thế cho việc thực hiện nghĩa vụ của bên bảo đảm đã chuyển "
            "quyền sở hữu cho TCTD chờ xử lý:"
        ),
        [_row("Bất động sản", ["1.230", "-"])],
    )
    section = _section("TÀI SẢN CÓ KHÁC", table)
    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        _page(section), section, table, compiled_specs=compiled
    )
    assert classification["context_roles"] == ["COLLATERAL_ASSET"]
    assert [(item["row_ordinal"], item["role"]) for item in classification["role_hits"]] == [
        (1, "REAL_ESTATE")
    ]


def test_table_local_period_dates_normalize_to_one_mapping_lane_axis() -> None:
    page = _summary_page()
    page["sections"][0]["tables"][1]["columns"] = _columns("30/06/2025", "30/06/2024")
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == READY
    source_axes = {
        tuple(tuple(item) for item in receipt["lane_axis"]["source_lane_keys"])
        for receipt in candidate["closure_receipt"]["table_receipts"]
    }
    assert source_axes == {
        (("DATE", "2025-12-31"), ("DATE", "2024-12-31")),
        (("DATE", "2025-06-30"), ("DATE", "2024-06-30")),
    }


def test_typed_provision_control_is_inventoried_but_not_selected() -> None:
    page = _summary_page()
    page["sections"][0]["tables"].append(
        _table(
            "Biến động quỹ dự phòng rủi ro tài sản Có khác",
            [
                _row("Số dư đầu năm", ["10", "8"]),
                _row("Số dư cuối năm", ["12", "10"]),
            ],
        )
    )
    _compiled_specs, cluster, candidate = _evaluate(page)
    assert candidate["status"] == READY
    assert any(
        item["classification"]["typed_control_disposition"]
        == "OTHER_ASSET_PROVISION_MOVEMENT_CONTROL"
        and item["disposition"] == "EXCLUDED_TYPED_CONTROL"
        for item in cluster["declared_money_table_inventory"]
    )


def test_candidate_exact_replay_rejects_coherent_source_receipt_drift() -> None:
    compiled, cluster, candidate = _evaluate(_summary_page())
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        cluster["component_regions"]
    )
    forged = copy.deepcopy(candidate)
    forged["closure_receipt"]["table_receipts"][0]["source_only_rows"][0][
        "consumed_by_exact_equation"
    ] = False
    with pytest.raises(
        GeminiJsonMultitableHierarchicalFamilyV1Error,
        match="candidate replay drifted",
    ):
        validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
            forged,
            regions=cluster["component_regions"],
            page_json_by_version={VERSION_ID: _summary_page()},
            compiled_specs=compiled,
            query_receipt=receipt,
        )


def test_conflicting_period_header_fails_closed_without_mappings() -> None:
    page = _summary_page()
    page["sections"][0]["tables"][0]["columns"][0]["header_path_exact"] = [
        "31/12/2025",
        "30/06/2025",
        "Triệu đồng",
    ]
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_nested_specific_role_beats_broad_structural_prefix_with_note_suffix() -> None:
    compiled = _compiled()
    table = _table(
        None,
        [
            _row("Các khoản phải thu", ["100", "80"], kind="GROUP"),
            _row(
                "- Các khoản phải thu khác\n(Thuyết minh số 15.2)",
                ["100", "80"],
                hierarchy=["Các khoản phải thu", "- Các khoản phải thu khác"],
            ),
            _row(None, ["100", "80"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    section = _section("TÀI SẢN CÓ KHÁC", table)
    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        _page(section), section, table, compiled_specs=compiled
    )
    assert [(item["row_ordinal"], item["role"]) for item in classification["role_hits"]] == [
        (1, "RECEIVABLES"),
        (2, "OTHER_RECEIVABLE"),
    ]


def test_anchored_inner_population_overrides_outer_continuation_heading() -> None:
    compiled = _compiled()
    table = _table(
        None,
        [
            _row("Nợ đủ tiêu chuẩn", ["70", "50"]),
            _row(None, ["70", "50"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    section = _section("Các khoản phải thu (tiếp theo)", table)
    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        _page(section), section, table, compiled_specs=compiled
    )
    assert classification["context_roles"] == ["CREDIT_RISK_QUALITY"]
    assert classification["role_hits"][0]["role"] == "GRADE_1"


def test_explicit_table_context_total_beats_row_population_detail_total() -> None:
    summary = _table(
        "Các khoản phải thu",
        [
            _row("Các khoản phải thu nội bộ", ["30", "20"]),
            _row("Các khoản phải thu bên ngoài", ["70", "60"]),
            _row(None, ["100", "80"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    detail = _table(
        None,
        [
            _row("Ký quỹ, đặt cọc", ["40", "30"]),
            _row("Các khoản phải thu khác", ["30", "30"]),
            _row(None, ["70", "60"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    page = _page(_section("TÀI SẢN CÓ KHÁC (tiếp theo)", summary, detail))
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == READY
    receivables = next(item for item in candidate["mappings"] if item["role"] == "RECEIVABLES")
    assert [cell["coefficient"] for cell in receivables["values"]] == [100, 80]


def test_contiguous_same_page_root_component_before_explicit_owner_is_included() -> None:
    receivables = _table(
        None,
        [
            _row("Các khoản phải thu nội bộ", ["30", "20"]),
            _row("Các khoản phải thu bên ngoài", ["70", "60"]),
            _row(None, ["100", "80"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    other = _table(
        None,
        [
            _row("Chi phí trả trước", ["40", "30"]),
            _row("Tài sản Có khác", ["10", "10"]),
            _row(None, ["50", "40"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    page = _page(
        _section("Các khoản phải thu", receivables),
        _section("Tài sản Có khác", other),
    )
    _compiled_specs, cluster, candidate = _evaluate(page)
    assert candidate["status"] == READY
    assert cluster["owner_receipt"]["leading_component_positions"] == [[1, 1, 1]]
    assert {item["role"] for item in candidate["mappings"]} >= {
        "RECEIVABLES",
        "OTHER_ASSET_BRANCH",
    }


def test_source_outline_number_ends_owner_scope_without_family_specific_reset_alias() -> None:
    family = _table(
        None,
        [
            _row("Các khoản phải thu", ["70", "60"]),
            _row("Tài sản Có khác", ["30", "20"]),
            _row(None, ["100", "80"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    unrelated = _table(
        None,
        [
            _row("Thu nhập lãi", ["999", "888"]),
            _row(None, ["999", "888"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    page = _page(
        _section("24. TÀI SẢN CÓ KHÁC", family),
        _section("25. THU NHẬP LÃI THUẦN", unrelated),
    )
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == READY
    assert [(item["section_id"], item["table_id"]) for item in cluster["component_regions"]] == [
        ("s1", "t1")
    ]
    assert cluster["owner_receipt"]["outline_top_level_number"] == 24


def test_source_outline_subheading_with_same_top_level_remains_inside_owner_scope() -> None:
    summary = _table(
        "24.1 Các khoản phải thu",
        [
            _row("Các khoản phải thu", ["70", "60"]),
            _row(None, ["70", "60"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    sibling = _table(
        "24.2 Tài sản Có khác",
        [
            _row("Tài sản Có khác", ["30", "20"]),
            _row(None, ["30", "20"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    page = _page(_section("24. TÀI SẢN CÓ KHÁC", summary, sibling))
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == READY
    assert [(item["section_id"], item["table_id"]) for item in cluster["component_regions"]] == [
        ("s1", "t1"),
        ("s1", "t2"),
    ]


def test_titleless_detail_total_is_corroborated_by_visible_child_carrier() -> None:
    summary = _table(
        None,
        [
            _row("Các khoản phải thu nội bộ", ["30", "20"]),
            _row("Các khoản phải thu bên ngoài", ["70", "60"]),
            _row(None, ["100", "80"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    detail = _table(
        None,
        [
            _row("Ký quỹ, đặt cọc", ["40", "30"]),
            _row("Các khoản phải thu khác", ["30", "30"]),
            _row(None, ["70", "60"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    other = _table(
        None,
        [
            _row("Chi phí trả trước", ["40", "30"]),
            _row("Tài sản Có khác", ["10", "10"]),
            _row(None, ["50", "40"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    page = _page(
        _section("Các khoản phải thu", summary, detail),
        _section("Tài sản Có khác", other),
    )
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == READY
    receipts = candidate["closure_receipt"]["context_total_corroboration_receipts"]
    assert len(receipts) == 1
    assert receipts[0]["coefficients"] == [70, 60]
    assert receipts[0]["context_role"] == "RECEIVABLES"
    assert receipts[0]["resolved_role"] == "EXTERNAL_RECEIVABLES"
    assert receipts[0]["rule"] == "DIFFERENT_TABLE_EXACT_ALL_LANE_VISIBLE_DECLARED_CHILD_CARRIER"


def test_conflicting_declared_money_units_fail_closed_without_mappings() -> None:
    page = _summary_page()
    page["sections"][0]["tables"][0]["unit_exact"] = "Triệu đồng / Nghìn đồng"
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    first = candidate["closure_receipt"]["table_receipts"][0]
    assert (
        "MULTIPLE_CONFLICTING_DECLARED_MONEY_UNITS_ON_ONE_SURFACE" in first["unit_axis"]["reasons"]
    )


def test_role_unit_override_axis_must_be_a_list() -> None:
    evaluation = _json("tm-other-assets-evaluation-v1.json")
    evaluation["role_unit_overrides"] = {"GOODWILL_ALLOCATION_YEARS": "YEARS"}
    with pytest.raises(
        GeminiJsonMultitableHierarchicalFamilyV1Error,
        match="evaluation spec is invalid",
    ):
        compile_gemini_json_multitable_hierarchical_family_specs_v1(
            _json("tm-other-assets-topology-v1.json"),
            evaluation,
            _json("tm-other-assets-schema-binding-v1.json"),
        )


def test_declared_role_equation_projects_exact_visible_component_sum() -> None:
    table = _table(
        "Các khoản phải thu",
        [
            _row("Mua sắm tài sản cố định", ["30", "20"]),
            _row("Xây dựng cơ bản dở dang", ["10", "5"]),
            _row(None, ["40", "25"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    _compiled_specs, _cluster, candidate = _evaluate(_page(_section("TÀI SẢN CÓ KHÁC", table)))
    capex = next(item for item in candidate["mappings"] if item["role"] == "CAPEX_RECEIVABLE")
    assert [cell["coefficient"] for cell in capex["values"]] == [40, 25]
    assert capex["state"] == "DECLARED_ROLE_DERIVED_FROM_EXACT_VISIBLE_COMPONENT_SUM"
    receipt = candidate["closure_receipt"]["derived_role_receipts"]
    assert [(item["component_roles"], item["result_role"]) for item in receipt] == [
        (["FIXED_ASSET_PURCHASE_REPAIR", "CONSTRUCTION_IN_PROGRESS"], "CAPEX_RECEIVABLE")
    ]


def test_repeated_structural_label_uses_hierarchy_parent_and_prefixed_child() -> None:
    table = _table(
        None,
        [
            _row("Tài sản Có khác", ["30", "20"]),
            _row(
                "- Chi phí trả trước",
                ["20", "15"],
                hierarchy=["Tài sản Có khác", "- Chi phí trả trước"],
            ),
            _row(
                "- Tài sản Có khác",
                ["10", "5"],
                hierarchy=["Tài sản Có khác", "- Tài sản Có khác"],
            ),
            _row(None, ["30", "20"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    _compiled_specs, _cluster, candidate = _evaluate(_page(_section("TÀI SẢN CÓ KHÁC", table)))
    by_role = {item["role"]: item for item in candidate["mappings"]}
    assert [cell["coefficient"] for cell in by_role["OTHER_ASSET_BRANCH"]["values"]] == [
        30,
        20,
    ]
    assert [cell["coefficient"] for cell in by_role["OTHER_ASSET"]["values"]] == [10, 5]


def test_ordered_subtotal_dash_children_and_subset_close_root_without_hierarchy_echo() -> None:
    table = _table(
        None,
        [
            _row("Các khoản phải thu", ["100", "80"], kind="SUBTOTAL"),
            _row("Các khoản phải thu nội bộ", ["30", "20"]),
            _row("Các khoản phải thu bên ngoài", ["70", "60"]),
            _row("- Ký quỹ", ["70", "60"]),
            _row(
                "Trong đó: khoản theo dõi riêng",
                ["5", "4"],
                hierarchy=[
                    "Các khoản phải thu bên ngoài",
                    "- Ký quỹ",
                    "Trong đó: khoản theo dõi riêng",
                ],
            ),
            _row("Các khoản lãi, phí phải thu", ["20", "10"]),
            _row("Tài sản Có khác (ii)", ["10", "5"]),
            _row(None, ["130", "95"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    _compiled_specs, _cluster, candidate = _evaluate(_page(_section("TÀI SẢN CÓ KHÁC", table)))
    assert candidate["status"] == READY
    root = next(item for item in candidate["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL")
    assert [cell["coefficient"] for cell in root["values"]] == [130, 95]
    kinds = {item["equation_kind"] for item in candidate["closure_receipt"]["equations"]}
    assert "EXACT_CONTIGUOUS_DASH_CHILDREN_EQUAL_VISIBLE_CARRIER" in kinds
    assert "EXACT_ORDERED_PREFIX_CHILDREN_EQUAL_VISIBLE_SUBTOTAL" in kinds


def test_detail_context_walks_unique_declared_parent_before_global_scopes() -> None:
    table = _table(
        "Các khoản phải thu bên ngoài",
        [
            _row("Khác", ["30", "20"]),
            _row(None, ["30", "20"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    compiled = _compiled()
    section = _section("TÀI SẢN CÓ KHÁC", table)
    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        _page(section), section, table, compiled_specs=compiled
    )
    assert classification["context_roles"] == ["EXTERNAL_RECEIVABLES"]
    assert [(item["row_ordinal"], item["role"]) for item in classification["role_hits"]] == [
        (1, "OTHER_RECEIVABLE")
    ]


def test_hard_negative_heading_ends_owner_fence_before_following_money_table() -> None:
    page = _summary_page()
    page["sections"].append(
        _section(
            "18. CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NHNN",
            _table(
                None,
                [
                    _row("Vay NHNN", ["900", "800"]),
                    _row(None, ["900", "800"], kind="TOTAL", hierarchy=[None]),
                ],
            ),
        )
    )
    _compiled_specs, cluster, candidate = _evaluate(page)
    assert candidate["status"] == READY
    assert all(region["section_id"] == "s1" for region in cluster["component_regions"])
    following = next(
        item for item in cluster["declared_money_table_inventory"] if item["section_id"] == "s2"
    )
    assert following["disposition"] == "OUTSIDE_SELECTED_OWNER_FENCE"


def test_owner_surface_policy_ignores_accounting_policy_narrative_and_stops_at_reset() -> None:
    policy_table = _table(
        None,
        [
            _row("Bằng VND", ["900", "800"]),
            _row(None, ["900", "800"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    family_table = _table(
        None,
        [
            _row("Vay Ngân hàng Nhà nước", ["100", "80"], kind="GROUP"),
            _row(
                "Vay theo hồ sơ tín dụng",
                ["100", "80"],
                hierarchy=["Vay Ngân hàng Nhà nước", "Vay theo hồ sơ tín dụng"],
            ),
            _row(None, ["100", "80"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    following_table = _table(
        None,
        [
            _row("Bằng VND", ["700", "600"]),
            _row(None, ["700", "600"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    policy_page = _page(
        _section(
            "Chính sách kế toán",
            policy_table,
            narratives=[
                "(n) Các khoản nợ Chính phủ và Ngân hàng Nhà nước\n"
                "Các khoản nợ được ghi nhận theo giá gốc."
            ],
        )
    )
    family_page = _page(
        _section("14. CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NGÂN HÀNG NHÀ NƯỚC", family_table),
        _section(
            "THUYẾT MINH BÁO CÁO TÀI CHÍNH (tiếp theo)\n15. TIỀN GỬI VÀ VAY CÁC TCTD KHÁC",
            following_table,
        ),
    )
    compiled = _government_compiled()
    policy_record = _record(policy_page)
    family_record = _record(family_page)
    family_record.update(
        {
            "page_json_version_id": "gfpstorev1:json:" + "d" * 64,
            "physical_page": 2,
            "selected_page_ordinal": 2,
        }
    )
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[policy_record, family_record], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    assert [
        (item["physical_page"], item["section_id"], item["table_id"])
        for item in cluster["component_regions"]
    ] == [(2, "s1", "t1")]
    dispositions = {
        (item["physical_page"], item["section_id"], item["table_id"]): item["disposition"]
        for item in cluster["declared_money_table_inventory"]
    }
    assert dispositions[(1, "s1", "t1")] == "OUTSIDE_SELECTED_OWNER_FENCE"
    assert dispositions[(2, "s2", "t1")] == "OUTSIDE_SELECTED_OWNER_FENCE"


def test_default_owner_surface_policy_preserves_narrative_owner_evidence() -> None:
    page = _summary_page()
    page["sections"][0]["title_exact"] = "Chính sách kế toán"
    page["sections"][0]["narratives_exact"] = ["14. TÀI SẢN CÓ KHÁC"]
    _compiled_specs, cluster, candidate = _evaluate(page)
    assert cluster["status"] == READY
    assert candidate["status"] == READY


def test_owner_or_exact_source_result_accepts_explicit_row_owned_population() -> None:
    table = _table(
        None,
        [
            _row("Của khách hàng", ["100", "80"], kind="GROUP"),
            _row(
                "Bất động sản",
                ["60", "50"],
                hierarchy=["Của khách hàng", "Bất động sản"],
            ),
            _row(
                "Tài sản khác",
                ["40", "30"],
                hierarchy=["Của khách hàng", "Tài sản khác"],
            ),
        ],
    )
    page = _page(_section("18. Tài sản bảo đảm", table))
    compiled = _customer_collateral_compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    assert cluster["owner_receipt"]["alias"] == "EXACT_SOURCE_RESULT_ROW"
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            cluster["component_regions"]
        ),
    )
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "FAMILY_ROOT_TOTAL",
        "OTHER_COLLATERAL",
        "REAL_ESTATE",
    }


def test_owner_or_exact_source_result_accepts_surface_owned_flat_population() -> None:
    table = _table(
        None,
        [
            _row("Bất động sản", ["60", "50"]),
            _row("Tài sản khác", ["40", "30"]),
            _row(None, ["100", "80"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    page = _page(
        _section(
            "18. Tài sản bảo đảm",
            table,
            narratives=[
                "Bảng dưới đây trình bày giá trị sổ sách của tài sản thế chấp của khách hàng"
            ],
        )
    )
    compiled = _customer_collateral_compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    assert not any(
        item["classification"].get("family_root_row_ordinals")
        for item in cluster["declared_money_table_inventory"]
    )
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            cluster["component_regions"]
        ),
    )
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "FAMILY_ROOT_TOTAL",
        "OTHER_COLLATERAL",
        "REAL_ESTATE",
    }


def test_table_title_owner_is_local_and_does_not_absorb_preceding_population() -> None:
    preceding = _table(
        None,
        [
            _row("Bất động sản", ["600", "500"]),
            _row("Tài sản khác", ["400", "300"]),
            _row(None, ["1000", "800"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    target = _table(
        "Mô tả và giá trị ghi sổ của tài sản đảm bảo",
        [
            _row("Bất động sản", ["60", "50"]),
            _row("Tài sản khác", ["40", "30"]),
            _row(None, ["100", "80"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    page = _page(_section("18. Rủi ro tín dụng", preceding, target))
    compiled = _customer_collateral_compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    assert [(item["section_id"], item["table_id"]) for item in cluster["component_regions"]] == [
        ("s1", "t2")
    ]


def test_source_result_population_excludes_non_result_sibling_tables() -> None:
    target = _table(
        None,
        [
            _row("Bất động sản", ["60", "50"]),
            _row("Động sản", ["20", "10"]),
            _row("Giấy tờ có giá", ["10", "10"]),
            _row("Tài sản khác", ["10", "10"]),
            _row(None, ["100", "80"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    other_credit_institution = _table(
        None,
        [_row("Giấy tờ có giá", ["7", "6"])],
    )
    page = _page(
        _section(
            "39. Loại hình và giá trị sổ sách tài sản thế chấp",
            target,
            other_credit_institution,
            narratives=[
                "Giá trị sổ sách của tài sản thế chấp của khách hàng tại thời điểm cuối kỳ",
                "Tài sản, giấy tờ có giá nhận thế chấp của TCTD khác tại thời điểm cuối kỳ",
            ],
        )
    )
    compiled = _customer_collateral_compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    assert [item["table_id"] for item in cluster["component_regions"]] == ["t1"]
    dispositions = {
        item["table_id"]: item["disposition"] for item in cluster["declared_money_table_inventory"]
    }
    assert dispositions["t2"] == "EXCLUDED_NON_SOURCE_RESULT_MONEY_TABLE_INSIDE_OWNER_FENCE"


def test_customer_collateral_bank_owned_table_title_is_a_typed_local_exclusion() -> None:
    target = _table(
        None,
        [
            _row("Bất động sản", ["60", "50"]),
            _row("Tài sản khác", ["40", "30"]),
            _row(None, ["100", "80"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    bank_owned = _table(
        "Tài sản, GTCG đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu",
        [
            _row("Bất động sản", ["600", "500"]),
            _row("Tài sản khác", ["400", "300"]),
            _row(None, ["1000", "800"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    page = _page(
        _section(
            "39. Loại hình và giá trị sổ sách tài sản thế chấp",
            target,
            bank_owned,
            narratives=["Giá trị sổ sách của tài sản thế chấp của khách hàng"],
        )
    )
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=_customer_collateral_compiled()
    )
    assert cluster["status"] == READY
    assert [item["table_id"] for item in cluster["component_regions"]] == ["t1"]
    inventory = {item["table_id"]: item for item in cluster["declared_money_table_inventory"]}
    assert inventory["t2"]["disposition"] == "EXCLUDED_TYPED_CONTROL"
    assert (
        inventory["t2"]["classification"]["typed_control_disposition"]
        == "BANK_OWNED_COLLATERAL_OUTSIDE_FAMILY"
    )


def test_multiple_source_result_populations_inside_one_owner_fence_are_unresolved() -> None:
    def population(multiplier: int) -> dict:
        return _table(
            None,
            [
                _row("Bất động sản", [str(60 * multiplier), str(50 * multiplier)]),
                _row("Tài sản khác", [str(40 * multiplier), str(30 * multiplier)]),
                _row(
                    None,
                    [str(100 * multiplier), str(80 * multiplier)],
                    kind="TOTAL",
                    hierarchy=[None],
                ),
            ],
        )

    page = _page(
        _section(
            "39. Loại hình và giá trị sổ sách tài sản thế chấp",
            population(1),
            population(10),
            narratives=["Giá trị sổ sách của tài sản thế chấp của khách hàng"],
        )
    )
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=_customer_collateral_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert cluster["reasons"] == ["MULTIPLE_SOURCE_RESULT_POPULATIONS_INSIDE_OWNER_FENCE"]


def test_owner_without_source_result_population_is_not_observed() -> None:
    page = _page(
        _section(
            "39. Loại hình và giá trị sổ sách tài sản thế chấp",
            _table(
                None,
                [
                    _row("Bất động sản", ["60", "50"]),
                    _row("Tài sản khác", ["40", "30"]),
                ],
            ),
            narratives=["Giá trị sổ sách của tài sản thế chấp của khách hàng"],
        )
    )
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=_customer_collateral_compiled()
    )
    assert cluster["status"] == NOT_OBSERVED
    assert cluster["component_regions"] == []
    assert cluster["reasons"] == []


def test_customer_collateral_equation_mismatch_emits_no_mapping() -> None:
    table = _table(
        None,
        [
            _row("Bất động sản", ["60", "50"]),
            _row("Tài sản khác", ["40", "30"]),
            _row(None, ["101", "80"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    page = _page(
        _section(
            "39. Loại hình và giá trị sổ sách tài sản thế chấp",
            table,
            narratives=["Giá trị sổ sách của tài sản thế chấp của khách hàng"],
        )
    )
    compiled = _customer_collateral_compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            cluster["component_regions"]
        ),
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "SOURCE_RESULT_TOTAL_NOT_PROVEN_BY_EXACT_EQUATION" in candidate["reasons"]


def test_customer_collateral_residual_rows_aggregate_only_after_exact_root_closure() -> None:
    table = _table(
        None,
        [
            _row("Của khách hàng", ["100", "80"], kind="GROUP"),
            _row(
                "Bất động sản",
                ["60", "50"],
                hierarchy=["Của khách hàng", "Bất động sản"],
            ),
            _row(
                "Quyền khai thác tài sản",
                ["10", "5"],
                hierarchy=["Của khách hàng", "Quyền khai thác tài sản"],
            ),
            _row(
                "Tài sản khác",
                ["30", "25"],
                hierarchy=["Của khách hàng", "Tài sản khác"],
            ),
        ],
    )
    page = _page(_section("18. Tài sản bảo đảm", table))
    compiled = _customer_collateral_compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            cluster["component_regions"]
        ),
    )
    assert candidate["status"] == READY
    other = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "OTHER_COLLATERAL"
    )
    assert [value["coefficient"] for value in other["values"]] == [40, 30]
    assert {source_ref["row_id"] for source_ref in other["source_refs"]} == {"r3", "r4"}


def test_owner_surface_policy_rejects_unknown_surface_kind() -> None:
    evaluation = _json("tm-government-sbv-liabilities-evaluation-v1.json")
    evaluation["owner_surface_kinds"] = ["PAGE_NARRATIVE"]
    with pytest.raises(
        GeminiJsonMultitableHierarchicalFamilyV1Error,
        match="owner surface kinds are invalid",
    ):
        compile_gemini_json_multitable_hierarchical_family_specs_v1(
            _json("tm-government-sbv-liabilities-topology-v1.json"),
            evaluation,
            _json("tm-government-sbv-liabilities-schema-binding-v1.json"),
        )


def test_label_only_structural_groups_project_only_after_terminal_total_closure() -> None:
    table = _table(
        None,
        [
            _row("Vay NHNN", [None, None], kind="GROUP"),
            _row(
                "Vay cầm cố giấy tờ có giá",
                ["31", "8"],
                hierarchy=["Vay NHNN", "Vay cầm cố giấy tờ có giá"],
            ),
            _row("Tiền gửi của Kho bạc Nhà nước", [None, None], kind="GROUP"),
            _row(
                "Tiền gửi bằng đồng Việt Nam",
                ["2", "1"],
                hierarchy=[
                    "Tiền gửi của Kho bạc Nhà nước",
                    "Tiền gửi bằng đồng Việt Nam",
                ],
            ),
            _row("Các khoản nợ khác", [None, None], kind="GROUP"),
            _row(
                "Giao dịch bán và mua lại trái phiếu Chính phủ với Kho bạc Nhà nước",
                ["3", "0"],
                hierarchy=[
                    "Các khoản nợ khác",
                    "Giao dịch bán và mua lại trái phiếu Chính phủ với Kho bạc Nhà nước",
                ],
            ),
            _row(None, ["36", "9"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    page = _page(_section("15. Các khoản nợ Chính phủ và NHNN", table))
    compiled = _government_compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            cluster["component_regions"]
        ),
    )
    assert candidate["status"] == READY
    by_role = {item["role"]: item for item in candidate["mappings"]}
    assert [cell["coefficient"] for cell in by_role["CENTRAL_BANK_LOAN"]["values"]] == [
        31,
        8,
    ]
    assert [cell["coefficient"] for cell in by_role["TREASURY_PAYMENT_DEPOSIT"]["values"]] == [2, 1]
    assert [cell["coefficient"] for cell in by_role["FAMILY_ROOT_TOTAL"]["values"]] == [
        36,
        9,
    ]
    projections = candidate["closure_receipt"]["table_receipts"][0][
        "label_only_structural_group_receipts"
    ]
    assert [(item["carrier_row_ordinal"], item["child_row_ordinal"]) for item in projections] == [
        (1, 2),
        (3, 4),
        (5, 6),
    ]


def test_intermediate_total_is_not_root_and_complete_top_level_sum_derives_root() -> None:
    table = _table(
        None,
        [
            _row("Vay NHNN", ["7", "9"]),
            _row(
                "Vay theo hồ sơ tín dụng",
                ["2", "3"],
                hierarchy=["Vay NHNN", "Vay theo hồ sơ tín dụng"],
            ),
            _row(
                "Vay chiết khấu các giấy tờ có giá",
                ["5", "6"],
                hierarchy=["Vay NHNN", "Vay chiết khấu các giấy tờ có giá"],
            ),
            _row("Tiền gửi của Kho bạc Nhà nước", ["134", "145"]),
            _row(
                "Bằng VND",
                ["134", "145"],
                hierarchy=["Tiền gửi của Kho bạc Nhà nước", "Bằng VND"],
            ),
            _row(None, ["141", "154"], kind="TOTAL", hierarchy=[None]),
            _row(
                "Giao dịch bán và mua lại trái phiếu Chính phủ với Kho bạc Nhà nước",
                ["3", "0"],
                kind="TOTAL",
            ),
        ],
    )
    page = _page(_section("15. Các khoản nợ Chính phủ và NHNN", table))
    compiled = _government_compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            cluster["component_regions"]
        ),
    )
    assert candidate["status"] == READY
    root = next(item for item in candidate["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL")
    assert [cell["coefficient"] for cell in root["values"]] == [144, 154]
    assert root["state"] == "DECLARED_FAMILY_ROOT_DERIVED_FROM_COMPLETE_TOP_LEVEL_COMPONENT_SUM"
    assert candidate["closure_receipt"]["root_component_sum_receipts"][0]["component_roles"] == [
        "CENTRAL_BANK_LOAN",
        "TREASURY_PAYMENT_DEPOSIT",
        "OTHER_LIABILITY",
    ]
    forged = copy.deepcopy(candidate)
    forged["closure_receipt"]["root_component_sum_receipts"][0]["coefficients"][0] += 1
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
            page_json_by_version={VERSION_ID: page},
            compiled_specs=compiled,
            query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
                cluster["component_regions"]
            ),
        )


def test_label_only_structural_group_policy_rejects_unknown_value() -> None:
    evaluation = _json("tm-government-sbv-liabilities-evaluation-v1.json")
    evaluation["label_only_structural_group_policy"] = "INFER_FROM_LABEL"
    with pytest.raises(
        GeminiJsonMultitableHierarchicalFamilyV1Error,
        match="label-only structural group policy is invalid",
    ):
        compile_gemini_json_multitable_hierarchical_family_specs_v1(
            _json("tm-government-sbv-liabilities-topology-v1.json"),
            evaluation,
            _json("tm-government-sbv-liabilities-schema-binding-v1.json"),
        )


@pytest.mark.parametrize("root_row_kind", ["ITEM", "TOTAL"])
def test_exact_owner_row_plus_total_maps_structural_family_root(root_row_kind: str) -> None:
    table = _table(
        None,
        [
            _row("Các khoản nợ Chính phủ và NHNN", ["100", "80"], kind=root_row_kind),
            _row(None, ["100", "80"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    page = _page(_section("15. Các khoản nợ Chính phủ và NHNN", table))
    compiled = _government_compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    assert cluster["component_regions"][0]["component_roles"] == []
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            cluster["component_regions"]
        ),
    )
    assert candidate["status"] == READY
    root = next(item for item in candidate["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL")
    assert root["report_norm_id"] == 1024
    assert [cell["coefficient"] for cell in root["values"]] == [100, 80]


def test_explicit_hierarchy_parent_blocks_currency_leaf_from_wrong_structural_group() -> None:
    table = _table(
        None,
        [
            _row("Tiền gửi của Bộ Tài chính", ["30", "20"], kind="GROUP"),
            _row(
                "- Bằng VND",
                ["30", "20"],
                hierarchy=["Tiền gửi của Bộ Tài chính", "- Bằng VND"],
            ),
            _row("Tiền gửi thanh toán của Kho bạc Nhà nước", ["70", "60"], kind="GROUP"),
            _row(
                "- Bằng VND",
                ["40", "30"],
                hierarchy=["Tiền gửi thanh toán của Kho bạc Nhà nước", "- Bằng VND"],
            ),
            _row(
                "- Bằng ngoại tệ",
                ["30", "30"],
                hierarchy=["Tiền gửi thanh toán của Kho bạc Nhà nước", "- Bằng ngoại tệ"],
            ),
            _row(None, ["100", "80"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    page = _page(_section("15. Các khoản nợ Chính phủ và NHNN", table))
    compiled = _government_compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            cluster["component_regions"]
        ),
    )
    assert candidate["status"] == READY
    by_role = {item["role"]: item for item in candidate["mappings"]}
    assert [cell["coefficient"] for cell in by_role["MINISTRY_FINANCE_DEPOSIT"]["values"]] == [
        30,
        20,
    ]
    assert [cell["coefficient"] for cell in by_role["TREASURY_PAYMENT_VND"]["values"]] == [
        40,
        30,
    ]
    assert [cell["coefficient"] for cell in by_role["TREASURY_PAYMENT_FOREIGN"]["values"]] == [
        30,
        30,
    ]


def test_canonical_top_level_frontier_proves_blank_zero_without_mixed_depth() -> None:
    table = _table(
        None,
        [
            _row("Vay NHNN", ["12", "9"], kind="SUBTOTAL"),
            _row(
                "Vay theo hồ sơ tín dụng",
                ["2", "1"],
                hierarchy=["Vay NHNN", "Vay theo hồ sơ tín dụng"],
            ),
            _row(
                "Vay chiết khấu các giấy tờ có giá",
                ["10", "8"],
                hierarchy=["Vay NHNN", "Vay chiết khấu các giấy tờ có giá"],
            ),
            _row("Tiền gửi của KBNN", ["20", "18"], kind="SUBTOTAL"),
            _row(
                "Tiền gửi bằng đồng Việt Nam",
                ["20", "18"],
                hierarchy=["Tiền gửi của KBNN", "Tiền gửi bằng đồng Việt Nam"],
            ),
            _row(
                "Giao dịch bán và mua lại trái phiếu Chính phủ với Kho bạc Nhà nước",
                ["3", None],
            ),
            _row(None, ["35", "27"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    page = _page(_section("15. Các khoản nợ Chính phủ và NHNN", table))
    compiled = _government_compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            cluster["component_regions"]
        ),
    )
    assert candidate["status"] == READY
    other = next(item for item in candidate["mappings"] if item["role"] == "OTHER_LIABILITY")
    assert [cell["coefficient"] for cell in other["values"]] == [3, 0]
    assert other["values"][1]["state"] == "INFERRED_BLANK_ZERO_IF_EQUATION_EXACT"
    root_equation = next(
        item
        for item in candidate["closure_receipt"]["equations"]
        if item["equation_kind"] == "EXACT_VISIBLE_TOP_LEVEL_DIRECT_FRONTIER_EQUAL_PRINTED_TOTAL"
    )
    assert [ref[0]["row_id"] for ref in root_equation["component_source_refs"]] == [
        "r1",
        "r4",
        "r6",
    ]


def test_derived_role_equation_rejects_duplicate_component_roles() -> None:
    evaluation = _json("tm-other-assets-evaluation-v1.json")
    evaluation["derived_role_equations"][0]["component_roles"] = [
        "CONSTRUCTION_IN_PROGRESS",
        "CONSTRUCTION_IN_PROGRESS",
    ]
    with pytest.raises(
        GeminiJsonMultitableHierarchicalFamilyV1Error,
        match="derived role equation is invalid",
    ):
        compile_gemini_json_multitable_hierarchical_family_specs_v1(
            _json("tm-other-assets-topology-v1.json"),
            evaluation,
            _json("tm-other-assets-schema-binding-v1.json"),
        )


def test_self_contained_scoped_children_close_entrusted_international_branch() -> None:
    table = _table(
        None,
        [
            _row(
                "Vốn nhận từ Ngân hàng Hợp tác Quốc tế Nhật Bản bằng Đồng Việt Nam (i)",
                ["8", "15"],
            ),
            _row(
                "Vốn nhận từ Ngân hàng Hợp tác Quốc tế Nhật Bản bằng ngoại tệ (ii)",
                ["11", "13"],
            ),
            _row(None, ["19", "28"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    page = _page(
        _section(
            "18. VỐN TÀI TRỢ, ỦY THÁC ĐẦU TƯ, CHO VAY TỔ CHỨC TÍN DỤNG CHỊU RỦI RO",
            table,
        )
    )
    compiled = _entrusted_compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            cluster["component_regions"]
        ),
    )
    assert candidate["status"] == READY
    by_role = {item["role"]: item for item in candidate["mappings"]}
    assert set(by_role) == {
        "DIRECT_INTERNATIONAL_ORGANIZATION",
        "DIRECT_INTERNATIONAL_ORGANIZATION_FOREIGN_CURRENCY",
        "DIRECT_INTERNATIONAL_ORGANIZATION_VND",
        "FAMILY_ROOT_TOTAL",
    }
    assert [cell["coefficient"] for cell in by_role["FAMILY_ROOT_TOTAL"]["values"]] == [
        19,
        28,
    ]


def test_generic_currency_rows_cannot_claim_entrusted_structural_scope() -> None:
    table = _table(
        "Thuyết minh theo loại tiền gửi",
        [
            _row("Tiền gửi không kỳ hạn", ["20", "10"], kind="GROUP"),
            _row("- Bằng VND", ["12", "6"]),
            _row("- Bằng ngoại tệ", ["8", "4"]),
            _row(None, ["20", "10"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        _page(_section("TIỀN GỬI CỦA KHÁCH HÀNG", table)),
        _section("TIỀN GỬI CỦA KHÁCH HÀNG", table),
        table,
        compiled_specs=_entrusted_compiled(),
    )
    assert classification["role_hits"] == []
    assert classification["family_presence_anchor_visible"] is False


def test_label_only_group_projects_exact_multi_child_frontier_after_total_closure() -> None:
    table = _table(
        None,
        [
            _row(
                "Vốn nhận tài trợ, ủy thác đầu tư, cho vay bằng ngoại tệ",
                [None, None],
                kind="GROUP",
            ),
            _row(
                "Chương trình A",
                ["3", "4"],
                hierarchy=[
                    "Vốn nhận tài trợ, ủy thác đầu tư, cho vay bằng ngoại tệ",
                    "Chương trình A",
                ],
            ),
            _row(
                "Chương trình B",
                ["5", "6"],
                hierarchy=[
                    "Vốn nhận tài trợ, ủy thác đầu tư, cho vay bằng ngoại tệ",
                    "Chương trình B",
                ],
            ),
            _row(None, ["8", "10"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    page = _page(_section("21. VỐN TÀI TRỢ, ỦY THÁC ĐẦU TƯ, CHO VAY TCTD CHỊU RỦI RO", table))
    compiled = _entrusted_compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        cluster["component_regions"]
    )
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    assert candidate["status"] == READY
    by_role = {item["role"]: item for item in candidate["mappings"]}
    assert [
        cell["coefficient"] for cell in by_role["FOREIGN_CURRENCY_RECEIVED_SOURCE"]["values"]
    ] == [8, 10]
    projection = candidate["closure_receipt"]["table_receipts"][0][
        "label_only_structural_group_receipts"
    ][0]
    assert projection["child_row_ordinals"] == [2, 3]

    forged = copy.deepcopy(candidate)
    forged["closure_receipt"]["table_receipts"][0]["label_only_structural_group_receipts"][0][
        "child_row_ordinals"
    ] = [2]
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
            page_json_by_version={VERSION_ID: page},
            compiled_specs=compiled,
            query_receipt=receipt,
        )

    broken = copy.deepcopy(page)
    broken["sections"][0]["tables"][0]["rows"][-1]["values_exact"][0] = "9"
    broken_cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(broken)], compiled_specs=compiled
    )
    broken_candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=broken_cluster["component_regions"],
        page_json_by_version={VERSION_ID: broken},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            broken_cluster["component_regions"]
        ),
    )
    assert broken_candidate["status"] == UNRESOLVED


def _interest_duration_columns(
    current: str = "Từ ngày 01/01/2025 đến ngày 31/03/2025",
    comparative: str = "Từ ngày 01/01/2024 đến ngày 31/03/2024",
) -> list[dict]:
    return [
        {"header_path_exact": [current, "Triệu đồng"], "value_kind": "MONEY"},
        {"header_path_exact": [comparative, "Triệu đồng"], "value_kind": "MONEY"},
    ]


def test_interest_income_combined_table_scopes_exact_family_root_subtree() -> None:
    root = "Thu nhập lãi và các khoản thu nhập tương tự"
    table = _table(
        "Thu nhập lãi thuần",
        [
            _row(root, [None, None], kind="GROUP", hierarchy=[root]),
            _row(
                "Thu nhập lãi tiền gửi",
                ["10", "8"],
                hierarchy=[root, "Thu nhập lãi tiền gửi"],
            ),
            _row(
                "Thu nhập lãi cho vay khách hàng",
                ["20", "12"],
                hierarchy=[root, "Thu nhập lãi cho vay khách hàng"],
            ),
            _row(None, ["30", "20"], kind="SUBTOTAL", hierarchy=[root, None]),
            _row(
                "Chi phí lãi và các chi phí tương tự",
                [None, None],
                kind="GROUP",
            ),
            _row("Chi lãi tiền gửi", ["(broken:source)", "(9)"], hierarchy=["Chi phí"]),
            _row("Thu nhập lãi thuần", ["15", "11"], kind="TOTAL"),
        ],
        columns=_interest_duration_columns(),
    )
    compiled_specs, cluster, candidate = _evaluate_interest_income(
        _page(_section("Thuyết minh", table))
    )
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "CUSTOMER_LOAN_INTEREST",
        "DEPOSIT_INTEREST",
        "FAMILY_ROOT_TOTAL",
    }
    receipt = candidate["closure_receipt"]["table_receipts"][0]
    assert [item["row_ordinal"] for item in receipt["outside_family_root_rows"]] == [5, 6, 7]

    forged = copy.deepcopy(candidate)
    forged["closure_receipt"]["table_receipts"][0]["outside_family_root_rows"][0]["row"][
        "label_exact"
    ] = "Coherent source receipt drift"
    forged["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in forged.items() if key != "candidate_id"}
    )
    page = _page(_section("Thuyết minh", table))
    query_receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        cluster["component_regions"]
    )
    with pytest.raises(
        GeminiJsonMultitableHierarchicalFamilyV1Error,
        match="candidate replay drifted",
    ):
        validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
            forged,
            regions=cluster["component_regions"],
            page_json_by_version={VERSION_ID: page},
            compiled_specs=compiled_specs,
            query_receipt=query_receipt,
        )


def test_interest_income_flat_leading_root_uses_bounded_ordered_children() -> None:
    root = "Thu nhập lãi và các khoản thu nhập tương tự"
    table = _table(
        "Thu nhập lãi thuần",
        [
            _row(root, ["30", "20"], kind="TOTAL", hierarchy=[root]),
            _row("Thu nhập lãi tiền gửi", ["10", "8"]),
            _row("Thu nhập lãi cho vay khách hàng", ["20", "12"]),
            _row("Chi phí lãi và các chi phí tương tự", ["(7)", "(5)"], kind="TOTAL"),
            _row("Chi lãi tiền gửi", ["(7)", "(5)"]),
            _row("Thu nhập lãi thuần", ["23", "15"], kind="TOTAL"),
        ],
        columns=_interest_duration_columns(),
    )
    _compiled_specs, _cluster, candidate = _evaluate_interest_income(
        _page(_section("Thuyết minh", table))
    )
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "CUSTOMER_LOAN_INTEREST",
        "DEPOSIT_INTEREST",
        "FAMILY_ROOT_TOTAL",
    }
    root_mapping = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL"
    )
    assert [value["coefficient"] for value in root_mapping["values"]] == [30, 20]


def test_interest_income_unmapped_direct_money_child_is_unresolved() -> None:
    root = "Thu nhập lãi và các khoản thu nhập tương tự"
    table = _table(
        "Thu nhập lãi thuần",
        [
            _row(root, [None, None], kind="GROUP", hierarchy=[root]),
            _row(
                "Thu nhập lãi tiền gửi",
                ["10", "8"],
                hierarchy=[root, "Thu nhập lãi tiền gửi"],
            ),
            _row(
                "Khoản thu nhập lãi chưa có schema binding",
                ["5", "4"],
                hierarchy=[root, "Khoản thu nhập lãi chưa có schema binding"],
            ),
            _row(None, ["15", "12"], kind="SUBTOTAL", hierarchy=[root, None]),
        ],
        columns=_interest_duration_columns(),
    )
    _compiled_specs, _cluster, candidate = _evaluate_interest_income(
        _page(_section("Thuyết minh", table))
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "UNMAPPED_DIRECT_FAMILY_SOURCE_MONEY_ROW" in candidate["reasons"]


def test_inactive_sibling_money_table_is_inventoried_without_becoming_family_population() -> None:
    owner = "Tiền gửi và vay các TCTD khác"
    active = _table(
        owner,
        [
            _row(owner, [None, None], kind="GROUP", hierarchy=[owner]),
            _row(
                "Tiền gửi các TCTD khác",
                ["10", "8"],
                kind="SUBTOTAL",
                hierarchy=[owner, "Tiền gửi các TCTD khác"],
            ),
            _row(
                "Tiền gửi không kỳ hạn",
                ["4", "3"],
                hierarchy=[owner, "Tiền gửi các TCTD khác", "Tiền gửi không kỳ hạn"],
            ),
            _row(
                "Tiền gửi có kỳ hạn",
                ["6", "5"],
                hierarchy=[owner, "Tiền gửi các TCTD khác", "Tiền gửi có kỳ hạn"],
            ),
            _row(
                "Vay các TCTD khác",
                ["5", "4"],
                hierarchy=[owner, "Vay các TCTD khác"],
            ),
            _row(None, ["15", "12"], kind="TOTAL", hierarchy=[owner, None]),
        ],
    )
    unrelated = _table(
        "Tài sản bảo đảm cho các khoản vay",
        [
            _row("Tiền gửi có kỳ hạn tại các TCTD khác", ["2", "1"]),
            _row("Chứng khoán đầu tư", ["3", "2"]),
        ],
    )
    _compiled_specs, cluster, candidate = _evaluate_interbank_funding(
        _page(_section(owner, active, unrelated))
    )
    assert len(cluster["component_regions"]) == 2
    assert candidate["status"] == READY
    assert not candidate["reasons"]
    assert {
        "DEMAND_DEPOSIT",
        "TERM_DEPOSIT",
        "DEPOSIT_PARENT",
        "BORROWING",
    } <= {mapping["role"] for mapping in candidate["mappings"]}
    assert len(candidate["closure_receipt"]["table_receipts"]) == 2
    assert {
        row["source_ref"]["locator"]["table_id"]
        for row in candidate["closure_receipt"]["source_only_unmapped_rows"]
    } == {"t1"}


def test_extra_money_row_in_active_interbank_population_remains_unresolved() -> None:
    owner = "Tiền gửi và vay các TCTD khác"
    active = _table(
        owner,
        [
            _row(owner, [None, None], kind="GROUP", hierarchy=[owner]),
            _row(
                "Tiền gửi các TCTD khác",
                ["10", "8"],
                kind="SUBTOTAL",
                hierarchy=[owner, "Tiền gửi các TCTD khác"],
            ),
            _row(
                "Tiền gửi không kỳ hạn",
                ["4", "3"],
                hierarchy=[owner, "Tiền gửi các TCTD khác", "Tiền gửi không kỳ hạn"],
            ),
            _row(
                "Tiền gửi có kỳ hạn",
                ["6", "5"],
                hierarchy=[owner, "Tiền gửi các TCTD khác", "Tiền gửi có kỳ hạn"],
            ),
            _row(
                "Vay các TCTD khác",
                ["5", "4"],
                hierarchy=[owner, "Vay các TCTD khác"],
            ),
            _row(
                "Khoản vay chưa có schema binding",
                ["1", "1"],
                hierarchy=[owner, "Khoản vay chưa có schema binding"],
            ),
            _row(None, ["16", "13"], kind="TOTAL", hierarchy=[owner, None]),
        ],
    )
    _compiled_specs, _cluster, candidate = _evaluate_interbank_funding(
        _page(_section(owner, active))
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "UNMAPPED_DIRECT_FAMILY_SOURCE_MONEY_ROW" in candidate["reasons"]


def _interbank_compound_row_page(*, comparative_value: str = "1\n5") -> dict:
    owner = "Tiền gửi và vay các TCTD khác"
    deposit = "Tiền gửi của các TCTD khác"
    borrowing = "Vay các TCTD khác"
    borrowing_vnd = "Bằng VND"
    compound_label = "Vay chiết khấu giấy tờ có giá\nVay cầm cố"
    return _page(
        _section(
            owner,
            _table(
                owner,
                [
                    _row(owner, [None, None], kind="GROUP", hierarchy=[owner]),
                    _row(
                        deposit,
                        ["10", "8"],
                        kind="SUBTOTAL",
                        hierarchy=[owner, deposit],
                    ),
                    _row(
                        "Tiền gửi không kỳ hạn",
                        ["4", "3"],
                        hierarchy=[owner, deposit, "Tiền gửi không kỳ hạn"],
                    ),
                    _row(
                        "Tiền gửi có kỳ hạn",
                        ["6", "5"],
                        hierarchy=[owner, deposit, "Tiền gửi có kỳ hạn"],
                    ),
                    _row(
                        borrowing,
                        ["12", "10"],
                        kind="SUBTOTAL",
                        hierarchy=[owner, borrowing],
                    ),
                    _row(
                        borrowing_vnd,
                        ["7", "6"],
                        kind="SUBTOTAL",
                        hierarchy=[owner, borrowing, borrowing_vnd],
                    ),
                    _row(
                        compound_label,
                        ["2\n5", comparative_value],
                        hierarchy=[owner, borrowing, f"{borrowing_vnd}\n{compound_label}"],
                    ),
                    _row(
                        "Bằng ngoại tệ",
                        ["5", "4"],
                        hierarchy=[owner, borrowing, "Bằng ngoại tệ"],
                    ),
                    _row(None, ["22", "18"], kind="TOTAL", hierarchy=[owner, None]),
                ],
            ),
        )
    )


def test_exact_line_aligned_compound_source_row_projects_distinct_declared_roles() -> None:
    _compiled_specs, _cluster, candidate = _evaluate_interbank_funding(
        _interbank_compound_row_page()
    )
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [cell["coefficient"] for cell in by_role["BORROWING_VND_DISCOUNT"]["values"]] == [2, 1]
    assert [cell["coefficient"] for cell in by_role["BORROWING_VND_COLLATERAL"]["values"]] == [5, 5]
    assert {ref["row_id"] for ref in by_role["BORROWING_VND_DISCOUNT"]["source_refs"]} == {
        "r7#line1"
    }
    assert {ref["row_id"] for ref in by_role["BORROWING_VND_COLLATERAL"]["source_refs"]} == {
        "r7#line2"
    }
    receipt = candidate["closure_receipt"]["table_receipts"][0]["classification"]
    assert len(receipt["compound_row_projection_receipts"]) == 1
    assert receipt["compound_row_projection_receipts"][0]["projected_roles"] == [
        "BORROWING_VND_DISCOUNT",
        "BORROWING_VND_COLLATERAL",
    ]


def test_compound_source_row_with_incomplete_value_axis_stays_raw_and_fails_closed() -> None:
    _compiled_specs, _cluster, candidate = _evaluate_interbank_funding(
        _interbank_compound_row_page(comparative_value="6")
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert not candidate["closure_receipt"]["table_receipts"][0]["classification"].get(
        "compound_row_projection_receipts"
    )


def test_direct_disclosure_prefix_uses_nearest_preceding_structural_scope() -> None:
    owner = "Tiền gửi và vay các TCTD khác"
    borrowing = "Vay các TCTD khác"
    table = _table(
        owner,
        [
            _row(borrowing, ["12", "10"], kind="SUBTOTAL", hierarchy=[borrowing]),
            _row("Bằng VND", ["7", "6"], kind="SUBTOTAL", hierarchy=[borrowing, "Bằng VND"]),
            _row(
                "Trong đó: Vay chiết khấu, tái chiết khấu",
                ["2", "1"],
                hierarchy=[borrowing, "Trong đó: Vay chiết khấu, tái chiết khấu"],
            ),
            _row(
                "Bằng ngoại tệ",
                ["5", "4"],
                hierarchy=[borrowing, "Bằng ngoại tệ"],
            ),
        ],
    )
    section = _section(owner, table)
    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        _page(section), section, table, compiled_specs=_interbank_funding_compiled()
    )
    assert (3, "BORROWING_VND_DISCOUNT") in [
        (hit["row_ordinal"], hit["role"]) for hit in classification["role_hits"]
    ]
    assert any(
        receipt["row_ordinal"] == 3
        and receipt["rule"]
        == "NEAREST_PRECEDING_DECLARED_STRUCTURAL_ROLE_PLUS_EXACT_DISCLOSURE_PREFIX_SCOPES_CHILD"
        for receipt in classification["hierarchy_path_scope_resolutions"]
    )


def test_section_context_scopes_only_noncontrol_table_among_typed_control_siblings() -> None:
    borrowing = "Vay các tổ chức tài chính, tổ chức tín dụng khác"
    active = _table(
        None,
        [
            _row("Bằng VND", ["7", "6"]),
            _row(
                "Trong đó: vay chiết khấu giấy tờ có giá",
                ["2", "1"],
                hierarchy=["Bằng VND", "Trong đó: vay chiết khấu giấy tờ có giá"],
            ),
            _row("Bằng ngoại tệ", ["5", "4"]),
            _row(None, ["12", "10"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    control = _table(
        None,
        [_row("Đến 6 tháng", ["12", "10"]), _row(None, ["12", "10"], kind="TOTAL")],
    )
    section = _section(borrowing, active, control)
    compiled = _interbank_funding_compiled()
    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        _page(section), section, active, compiled_specs=compiled
    )
    assert classification["context_roles"] == ["BORROWING"]
    assert not classification["ambiguous_rows"]
    assert [(hit["row_ordinal"], hit["role"]) for hit in classification["role_hits"]] == [
        (1, "BORROWING_VND"),
        (2, "BORROWING_VND_DISCOUNT"),
        (3, "BORROWING_FOREIGN"),
    ]
    control_classification = classify_gemini_json_multitable_hierarchical_table_v1(
        _page(section), section, control, compiled_specs=compiled
    )
    assert control_classification["typed_control_disposition"] == (
        "BORROWING_ORIGINAL_MATURITY_SCHEDULE_OUTSIDE_FAMILY_VALUE_POPULATION"
    )


def test_section_context_ignores_percentage_sibling_when_scoping_sole_money_table() -> None:
    borrowing = "Vay các tổ chức tín dụng khác"
    active = _table(
        None,
        [
            _row("Bằng VND", ["7", "6"]),
            _row("Bằng ngoại tệ", ["5", "4"]),
            _row(None, ["12", "10"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    rate = _table(
        None,
        [_row("Tiền vay bằng VND", ["6,3", "4,1"])],
        columns=[
            {"header_path_exact": ["31/12/2025", "%"], "value_kind": "PERCENT"},
            {"header_path_exact": ["31/12/2024", "%"], "value_kind": "PERCENT"},
        ],
        unit="%",
    )
    section = _section(borrowing, active, rate)
    compiled = _interbank_funding_compiled()
    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        _page(section), section, active, compiled_specs=compiled
    )
    assert classification["context_roles"] == ["BORROWING"]
    assert [(hit["row_ordinal"], hit["role"]) for hit in classification["role_hits"]] == [
        (1, "BORROWING_VND"),
        (2, "BORROWING_FOREIGN"),
    ]


def test_nested_label_only_interbank_groups_bind_their_printed_subtotals() -> None:
    owner = "Tiền gửi và vay các TCTD khác"
    deposit = "Tiền gửi của các TCTD khác"
    demand = "Tiền gửi không kỳ hạn"
    term = "Tiền gửi có kỳ hạn"
    borrowing = "Vay các TCTD khác"
    table = _table(
        owner,
        [
            _row(deposit, [None, None], kind="GROUP", hierarchy=[deposit]),
            _row(demand, [None, None], kind="GROUP", hierarchy=[deposit, demand]),
            _row("- Bằng VND", ["5", "3"], hierarchy=[deposit, demand, "- Bằng VND"]),
            _row(
                "- Bằng ngoại tệ",
                ["1", "1"],
                hierarchy=[deposit, demand, "- Bằng ngoại tệ"],
            ),
            _row(None, ["6", "4"], kind="SUBTOTAL", hierarchy=[deposit, demand, None]),
            _row(term, [None, None], kind="GROUP", hierarchy=[deposit, term]),
            _row("- Bằng VND", ["10", "8"], hierarchy=[deposit, term, "- Bằng VND"]),
            _row(
                "- Bằng ngoại tệ",
                ["2", "1"],
                hierarchy=[deposit, term, "- Bằng ngoại tệ"],
            ),
            _row(None, ["12", "9"], kind="SUBTOTAL", hierarchy=[deposit, term, None]),
            _row(
                "Tổng tiền gửi của các TCTD khác",
                ["18", "13"],
                kind="TOTAL",
                hierarchy=[deposit, "Tổng tiền gửi của các TCTD khác"],
            ),
            _row(borrowing, [None, None], kind="GROUP", hierarchy=[borrowing]),
            _row("Bằng VND", ["7", "6"], hierarchy=[borrowing, "Bằng VND"]),
            _row("Bằng ngoại tệ", ["3", "2"], hierarchy=[borrowing, "Bằng ngoại tệ"]),
            _row(
                "Tổng vay các TCTD khác",
                ["10", "8"],
                kind="TOTAL",
                hierarchy=[borrowing, "Tổng vay các TCTD khác"],
            ),
            _row(
                "Tổng tiền gửi và vay các TCTD khác",
                ["28", "21"],
                kind="TOTAL",
                hierarchy=["Tổng tiền gửi và vay các TCTD khác"],
            ),
        ],
    )
    _compiled_specs, _cluster, candidate = _evaluate_interbank_funding(
        _page(_section(owner, table))
    )
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [cell["coefficient"] for cell in by_role["DEMAND_DEPOSIT"]["values"]] == [6, 4]
    assert [cell["coefficient"] for cell in by_role["TERM_DEPOSIT"]["values"]] == [12, 9]
    assert [cell["coefficient"] for cell in by_role["DEPOSIT_PARENT"]["values"]] == [18, 13]
    assert [cell["coefficient"] for cell in by_role["BORROWING"]["values"]] == [10, 8]
    assert [cell["coefficient"] for cell in by_role["FAMILY_ROOT_TOTAL"]["values"]] == [28, 21]


def test_compound_numbered_table_owner_includes_following_same_outline_branch() -> None:
    deposit = _table(
        "19. TIỀN GỬI VÀ VAY CÁC TCTD KHÁC\n19.1. Tiền gửi của các TCTD khác",
        [
            _row("Tiền gửi không kỳ hạn", ["4", "3"]),
            _row("Tiền gửi có kỳ hạn", ["6", "5"]),
            _row(None, ["10", "8"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    borrowing = _table(
        "19.2. Vay các TCTD khác",
        [
            _row("Phải trả về nghiệp vụ UPAS L/C", ["5", "4"], kind="GROUP"),
            _row(
                "Bằng VND",
                ["2", "1"],
                hierarchy=["Phải trả về nghiệp vụ UPAS L/C唯Bằng VND"],
            ),
            _row(
                "Bằng ngoại tệ",
                ["3", "3"],
                hierarchy=["Phải trả về nghiệp vụ UPAS L/C唯Bằng ngoại tệ"],
            ),
            _row("Vay các TCTD khác", ["7", "6"], kind="GROUP"),
            _row("Bằng VND", ["4", "2"], hierarchy=["Vay các TCTD khác", "Bằng VND"]),
            _row(
                "Bằng ngoại tệ",
                ["3", "4"],
                hierarchy=["Vay các TCTD khác", "Bằng ngoại tệ"],
            ),
            _row(None, ["12", "10"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    reset = _table(
        "20. Chứng khoán kinh doanh",
        [_row("Khoản mục khác", ["99", "88"])],
    )
    page = _page(_section("Thuyết minh", deposit, borrowing, reset))
    _compiled_specs, cluster, candidate = _evaluate_interbank_funding(page)
    assert cluster["status"] == READY
    assert [
        (region["section_id"], region["table_id"]) for region in cluster["component_regions"]
    ] == [
        ("s1", "t1"),
        ("s1", "t2"),
    ]
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [cell["coefficient"] for cell in by_role["BORROWING"]["values"]] == [12, 10]
    assert [cell["coefficient"] for cell in by_role["BORROWING_VND"]["values"]] == [6, 3]
    assert [cell["coefficient"] for cell in by_role["BORROWING_FOREIGN"]["values"]] == [6, 7]
    assert [cell["coefficient"] for cell in by_role["FAMILY_ROOT_TOTAL"]["values"]] == [22, 18]


def test_same_outline_typed_control_narrative_does_not_cut_active_balance_table() -> None:
    deposit = _table(
        None,
        [
            _row("Tiền gửi không kỳ hạn", ["4", "3"]),
            _row("Tiền gửi có kỳ hạn", ["6", "5"]),
            _row(None, ["10", "8"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    borrowing = _table(
        None,
        [
            _row("Bằng VND", ["7", "6"]),
            _row("Bằng ngoại tệ", ["5", "4"]),
            _row(None, ["12", "10"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    rate_control = _table(
        None,
        [
            _row("Đến 6 tháng", ["12", "10"]),
            _row(None, ["12", "10"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    page = _page(
        _section("18. TIỀN GỬI VÀ VAY CÁC TCTD KHÁC"),
        _section("18.1 Tiền gửi của các TCTD khác", deposit),
        _section(
            "18.2 Vay các TCTD khác",
            borrowing,
            rate_control,
            narratives=["Mức lãi suất tiền gửi và tiền vay vào thời điểm cuối kỳ"],
        ),
        _section("19. TIỀN GỬI CỦA KHÁCH HÀNG"),
    )
    _compiled_specs, cluster, candidate = _evaluate_interbank_funding(page)
    assert [(item["section_id"], item["table_id"]) for item in cluster["component_regions"]] == [
        ("s2", "t1"),
        ("s3", "t1"),
    ]
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [cell["coefficient"] for cell in by_role["BORROWING"]["values"]] == [12, 10]
    assert [cell["coefficient"] for cell in by_role["FAMILY_ROOT_TOTAL"]["values"]] == [
        22,
        18,
    ]


def test_flattened_label_only_paths_use_contiguous_declared_child_graph() -> None:
    owner = "Tiền gửi và vay các TCTD khác"
    table = _table(
        owner,
        [
            _row("Tiền gửi không kỳ hạn", [None, None], kind="GROUP"),
            _row("Bằng VND", ["4", "3"], hierarchy=["Tiền gửi không kỳ hạn-Bằng VND"]),
            _row(
                "Bằng ngoại tệ",
                ["1", "1"],
                hierarchy=["Tiền gửi không kỳ hạn-Bằng ngoại tệ"],
            ),
            _row("Tiền gửi có kỳ hạn", [None, None], kind="GROUP"),
            _row("Bằng VND", ["6", "5"], hierarchy=["Tiền gửi có kỳ hạn-Bằng VND"]),
            _row(
                "Bằng ngoại tệ",
                ["2", "1"],
                hierarchy=["Tiền gửi có kỳ hạn-Bằng ngoại tệ"],
            ),
            _row("Vay các TCTD khác", [None, None], kind="GROUP"),
            _row("Bằng VND", ["7", "6"], hierarchy=["Vay các TCTD khác-Bằng VND"]),
            _row(
                "Bằng ngoại tệ",
                ["3", "2"],
                hierarchy=["Vay các TCTD khác-Bằng ngoại tệ"],
            ),
            _row(None, ["23", "18"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    _compiled_specs, _cluster, candidate = _evaluate_interbank_funding(
        _page(_section(owner, table))
    )
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [cell["coefficient"] for cell in by_role["DEMAND_DEPOSIT"]["values"]] == [5, 4]
    assert [cell["coefficient"] for cell in by_role["TERM_DEPOSIT"]["values"]] == [8, 6]
    assert [cell["coefficient"] for cell in by_role["BORROWING"]["values"]] == [10, 8]
    assert [cell["coefficient"] for cell in by_role["FAMILY_ROOT_TOTAL"]["values"]] == [
        23,
        18,
    ]


def test_nonadditive_disclosures_do_not_enter_context_total_frontier() -> None:
    owner = "Tiền gửi và vay các TCTD khác"
    deposit = _table(
        None,
        [
            _row("Tiền gửi không kỳ hạn", ["4", "3"]),
            _row("Tiền gửi có kỳ hạn", ["6", "5"]),
            _row(None, ["10", "8"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    borrowing = _table(
        None,
        [
            _row("Bằng VND", ["7", "6"]),
            _row("Trong đó:", [None, None], kind="GROUP"),
            _row(
                "Vay chiết khấu, tái chiết khấu",
                ["2", "1"],
                hierarchy=["Trong đó:", "Vay chiết khấu, tái chiết khấu"],
            ),
            _row("Bằng ngoại tệ", ["5", "4"]),
            _row(None, ["12", "10"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    page = _page(
        _section(owner),
        _section("8.1 Tiền gửi của các TCTD khác", deposit),
        _section("8.2 Vay các TCTD khác", borrowing),
    )
    _compiled_specs, _cluster, candidate = _evaluate_interbank_funding(page)
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [cell["coefficient"] for cell in by_role["BORROWING"]["values"]] == [12, 10]
    assert [cell["coefficient"] for cell in by_role["BORROWING_VND_DISCOUNT"]["values"]] == [2, 1]


def test_partial_top_level_component_cannot_synthesize_family_root() -> None:
    table = _table(
        None,
        [
            _row("Tiền gửi không kỳ hạn", ["4", "3"]),
            _row("Tiền gửi có kỳ hạn", ["6", "5"]),
            _row(None, ["10", "8"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    section = _section("18.1 Tiền gửi của các TCTD khác", table)
    page = _page(section)
    compiled = _interbank_funding_compiled()
    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        page, section, table, compiled_specs=compiled
    )
    region = {
        "component_roles": sorted(
            {
                *(hit["role"] for hit in classification["role_hits"]),
                *classification["context_roles"],
            }
        ),
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "fragment_ordinal": 1,
        "page_json_version_id": VERSION_ID,
        "physical_page": 1,
        "section_id": "s1",
        "selected_page_ordinal": 1,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
        "table_id": "t1",
    }
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=[region],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1([region]),
    )
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "DEMAND_DEPOSIT",
        "DEPOSIT_PARENT",
        "TERM_DEPOSIT",
    }
    assert candidate["closure_receipt"]["root_component_sum_receipts"] == []


def test_extended_structural_borrowing_label_is_declaratively_classified() -> None:
    owner = "Tiền gửi và vay các TCTD khác"
    table = _table(
        None,
        [
            _row("Tiền gửi không kỳ hạn", [None, None], kind="GROUP"),
            _row(
                "Bằng VND",
                ["4", "3"],
                hierarchy=["Tiền gửi không kỳ hạn", "Bằng VND"],
            ),
            _row(
                "Bằng ngoại tệ",
                ["1", "1"],
                hierarchy=["Tiền gửi không kỳ hạn", "Bằng ngoại tệ"],
            ),
            _row("Tiền gửi có kỳ hạn", [None, None], kind="GROUP"),
            _row(
                "Bằng VND",
                ["6", "5"],
                hierarchy=["Tiền gửi có kỳ hạn", "Bằng VND"],
            ),
            _row(
                "Bằng ngoại tệ",
                ["2", "1"],
                hierarchy=["Tiền gửi có kỳ hạn", "Bằng ngoại tệ"],
            ),
            _row(None, ["13", "10"], kind="SUBTOTAL", hierarchy=[None]),
            _row("Vay các TCTD khác", [None, None], kind="GROUP"),
            _row("Bằng VND", ["3", "2"], hierarchy=["Vay các TCTD khác", "Bằng VND"]),
            _row("Trong đó:", [None, None], kind="GROUP"),
            _row(
                "Vay chiết khấu, tái chiết khấu",
                ["1", "1"],
                hierarchy=["Vay các TCTD khác", "Trong đó:", "Vay chiết khấu, tái chiết khấu"],
            ),
            _row(
                'Vay các TCTD, tổ chức tài chính ("TCTC") khác',
                [None, None],
                kind="GROUP",
            ),
            _row(
                "Bằng ngoại tệ",
                ["2", "2"],
                hierarchy=[
                    'Vay các TCTD, tổ chức tài chính ("TCTC") khác',
                    "Bằng ngoại tệ",
                ],
            ),
            _row(None, ["5", "4"], kind="SUBTOTAL", hierarchy=[None]),
            _row(None, ["18", "14"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    section = _section(owner, table)
    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        _page(section),
        section,
        table,
        compiled_specs=_interbank_funding_compiled(),
    )
    assert (12, "BORROWING") in [
        (hit["row_ordinal"], hit["role"]) for hit in classification["role_hits"]
    ]


@pytest.mark.parametrize(
    ("current_header", "expected_reason"),
    [
        (
            "Từ ngày 01/01/2025 đến ngày 31/03/2025; đối chiếu ngày 30/06/2025",
            "TOO_MANY_DURATION_DATES_IN_MONEY_COLUMN:c1",
        ),
        (
            "Năm kết thúc 31/12/2025; ngày phê duyệt 30/03/2025",
            "MULTIPLE_UNGOVERNED_DATES_IN_MONEY_COLUMN:c1",
        ),
        (
            "Từ ngày 31/03/2025 đến ngày 01/01/2025",
            "INVALID_DURATION_DATE_RANGE_IN_MONEY_COLUMN:c1",
        ),
        (
            "Kỳ kết thúc ngày 31/03/2025; năm 2024",
            "DATE_AND_UNBOUND_BARE_YEAR_CONFLICT:c1",
        ),
        ("Năm 2025; năm trước", "DATE_SEMANTIC_PERIOD_CONFLICT:c1"),
        ("6 tháng đầu năm 2025; năm trước", "DATE_SEMANTIC_PERIOD_CONFLICT:c1"),
    ],
)
def test_interest_income_duration_period_conflicts_fail_closed(
    current_header: str, expected_reason: str
) -> None:
    table = _table(
        "Thu nhập lãi và các khoản thu nhập tương tự",
        [
            _row("Thu nhập lãi tiền gửi", ["10", "8"]),
            _row("Thu nhập lãi cho vay khách hàng", ["5", "4"]),
            _row(None, ["15", "12"], kind="TOTAL", hierarchy=[None]),
        ],
        columns=_interest_duration_columns(current=current_header),
    )
    _compiled_specs, _cluster, candidate = _evaluate_interest_income(
        _page(_section("Thuyết minh", table))
    )
    assert candidate["status"] == UNRESOLVED
    lane_axis = candidate["closure_receipt"]["table_receipts"][0]["lane_axis"]
    assert expected_reason in lane_axis["reasons"]


def test_interest_income_months_from_year_is_duration_not_opening_alias() -> None:
    table = _table(
        "Thu nhập lãi và các khoản thu nhập tương tự",
        [
            _row("Thu nhập lãi tiền gửi", ["10", "8"]),
            _row("Thu nhập lãi cho vay khách hàng", ["5", "4"]),
            _row(None, ["15", "12"], kind="TOTAL", hierarchy=[None]),
        ],
        columns=_interest_duration_columns(
            current="6 tháng đầu năm 2025",
            comparative="6 tháng đầu năm 2024",
        ),
    )
    _compiled_specs, _cluster, candidate = _evaluate_interest_income(
        _page(_section("Thuyết minh", table))
    )
    assert candidate["status"] == READY
    lane_axis = candidate["closure_receipt"]["table_receipts"][0]["lane_axis"]
    assert lane_axis["source_lane_keys"] == [
        ["DURATION_BARE_YEAR", "2025"],
        ["DURATION_BARE_YEAR", "2024"],
    ]


def test_interest_income_item_root_does_not_capture_adjacent_flat_items() -> None:
    root = "Thu nhập lãi và các khoản thu nhập tương tự"
    table = _table(
        "Thu nhập lãi thuần",
        [
            _row(root, ["30", "20"], kind="ITEM", hierarchy=[root]),
            _row("Thu nhập lãi tiền gửi", ["10", "8"]),
            _row("Thu nhập lãi cho vay khách hàng", ["20", "12"]),
        ],
        columns=_interest_duration_columns(),
    )
    _compiled_specs, _cluster, candidate = _evaluate_interest_income(
        _page(_section("Thuyết minh", table))
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    receipt = candidate["closure_receipt"]["table_receipts"][0]
    assert receipt["family_root_population_receipt"]["flat_item_row_ordinals"] == []


@pytest.mark.parametrize(
    ("securities", "root", "expected_status"), [("35", "45", READY), ("36", "46", UNRESOLVED)]
)
def test_interest_income_source_group_must_equal_declared_components(
    securities: str, root: str, expected_status: str
) -> None:
    family_root = "Thu nhập lãi và các khoản thu nhập tương tự"
    securities_root = "Thu lãi từ kinh doanh, đầu tư chứng khoán nợ"
    table = _table(
        "Thu nhập lãi thuần",
        [
            _row(family_root, [root, root], kind="GROUP", hierarchy=[family_root]),
            _row(
                "Thu nhập lãi tiền gửi",
                ["10", "10"],
                hierarchy=[family_root, "Thu nhập lãi tiền gửi"],
            ),
            _row(
                securities_root,
                [securities, securities],
                kind="GROUP",
                hierarchy=[family_root, securities_root],
            ),
            _row(
                "Thu lãi từ chứng khoán kinh doanh",
                ["15", "15"],
                hierarchy=[family_root, securities_root, "Thu lãi từ chứng khoán kinh doanh"],
            ),
            _row(
                "Thu lãi từ chứng khoán đầu tư",
                ["20", "20"],
                hierarchy=[family_root, securities_root, "Thu lãi từ chứng khoán đầu tư"],
            ),
            _row(None, [root, root], kind="SUBTOTAL", hierarchy=[family_root, None]),
        ],
        columns=_interest_duration_columns(),
    )
    _compiled_specs, _cluster, candidate = _evaluate_interest_income(
        _page(_section("Thuyết minh", table))
    )
    assert candidate["status"] == expected_status
    if expected_status == READY:
        assert any(
            equation["equation_kind"] == "EXACT_DECLARED_SOURCE_RESULT_EQUALS_VISIBLE_COMPONENT_SUM"
            for equation in candidate["closure_receipt"]["equations"]
        )
    else:
        assert candidate["mappings"] == []
        assert (
            "DECLARED_SOURCE_RESULT_COMPONENT_EQUATION_MISMATCH:SECURITIES_INTEREST"
            in candidate["reasons"]
        )


def test_interest_expense_group_root_owns_only_following_flat_rows() -> None:
    income_root = "Thu nhập lãi và các khoản thu nhập tương tự"
    expense_root = "Chi phí lãi và các chi phí tương tự"
    table = _table(
        "Thu nhập lãi thuần",
        [
            _row(income_root, [None, None], kind="GROUP", hierarchy=[income_root]),
            _row("Thu nhập lãi tiền gửi", ["9", "7"]),
            _row(None, ["9", "7"], kind="SUBTOTAL", hierarchy=[income_root, None]),
            _row(expense_root, [None, None], kind="GROUP", hierarchy=[expense_root]),
            _row("Chi phí lãi tiền gửi", ["4", "3"]),
            _row("Chi phí lãi tiền vay", ["2", "1"]),
            _row("Chi phí lãi phát hành giấy tờ có giá", ["1", "1"]),
            _row("Chi phí hoạt động tín dụng khác", ["1", "1"]),
            _row(None, ["8", "6"], kind="SUBTOTAL", hierarchy=[expense_root, None]),
            _row("Thu nhập lãi thuần", ["1", "1"], kind="TOTAL"),
        ],
        columns=_interest_duration_columns(),
    )
    _compiled_specs, _cluster, candidate = _evaluate_interest_expense(
        _page(_section("Thuyết minh", table))
    )
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "BORROWING_INTEREST",
        "DEPOSIT_INTEREST",
        "FAMILY_ROOT_TOTAL",
        "ISSUED_PAPER_INTEREST",
        "OTHER_CREDIT_EXPENSE",
    }
    receipt = candidate["closure_receipt"]["table_receipts"][0]
    assert receipt["family_root_population_receipt"]["flat_item_row_ordinals"] == [5, 6, 7, 8]
    assert [item["row_ordinal"] for item in receipt["outside_family_root_rows"]] == [1, 2, 3, 10]


def test_interest_expense_subtotal_selects_its_declared_child_side() -> None:
    income_root = "Thu nhập lãi và các khoản thu nhập tương tự"
    expense_root = "Chi phí lãi và các chi phí tương tự"
    table = _table(
        "Thu nhập lãi thuần",
        [
            _row(income_root, ["9", "7"], kind="SUBTOTAL", hierarchy=[income_root]),
            _row(
                "Thu nhập lãi tiền gửi",
                ["4", "3"],
                hierarchy=[income_root, "Thu nhập lãi tiền gửi"],
            ),
            _row(
                "Thu nhập lãi cho vay",
                ["5", "4"],
                hierarchy=[income_root, "Thu nhập lãi cho vay"],
            ),
            _row(expense_root, ["-8", "-6"], kind="SUBTOTAL", hierarchy=[expense_root]),
            _row(
                "Chi phí lãi tiền gửi",
                ["-4", "-3"],
                hierarchy=[expense_root, "Chi phí lãi tiền gửi"],
            ),
            _row(
                "Chi phí lãi tiền vay",
                ["-2", "-1"],
                hierarchy=[expense_root, "Chi phí lãi tiền vay"],
            ),
            _row(
                "Chi phí phát hành giấy tờ có giá",
                ["-1", "-1"],
                hierarchy=[expense_root, "Chi phí phát hành giấy tờ có giá"],
            ),
            _row(
                "Chi phí hoạt động tín dụng khác",
                ["-1", "-1"],
                hierarchy=[expense_root, "Chi phí hoạt động tín dụng khác"],
            ),
            _row("Thu nhập lãi thuần", ["1", "1"], kind="TOTAL"),
        ],
        columns=_interest_duration_columns(),
    )
    _compiled_specs, _cluster, candidate = _evaluate_interest_expense(
        _page(_section("Thuyết minh", table))
    )
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "BORROWING_INTEREST",
        "DEPOSIT_INTEREST",
        "FAMILY_ROOT_TOTAL",
        "ISSUED_PAPER_INTEREST",
        "OTHER_CREDIT_EXPENSE",
    }
    receipt = candidate["closure_receipt"]["table_receipts"][0]
    assert receipt["family_root_population_receipt"]["flat_item_row_ordinals"] == [5, 6, 7, 8]
    assert [item["row_ordinal"] for item in receipt["outside_family_root_rows"]] == [1, 2, 3, 9]


@pytest.mark.parametrize(
    ("current_root", "expected_status"),
    [("-8000000", READY), ("-8000001", UNRESOLVED)],
)
def test_interest_expense_colon_group_separator_requires_exact_root_equation(
    current_root: str, expected_status: str
) -> None:
    expense_root = "Chi phí lãi và các chi phí tương tự"
    table = _table(
        expense_root,
        [
            _row(
                expense_root,
                [current_root, "-6"],
                kind="SUBTOTAL",
                hierarchy=[expense_root],
            ),
            _row(
                "Chi phí lãi tiền gửi",
                ["(4.000:000)", "-3"],
                hierarchy=[expense_root, "Chi phí lãi tiền gửi"],
            ),
            _row(
                "Chi phí lãi tiền vay",
                ["-2000000", "-1"],
                hierarchy=[expense_root, "Chi phí lãi tiền vay"],
            ),
            _row(
                "Chi phí phát hành giấy tờ có giá",
                ["-1000000", "-1"],
                hierarchy=[expense_root, "Chi phí phát hành giấy tờ có giá"],
            ),
            _row(
                "Chi phí hoạt động tín dụng khác",
                ["-1000000", "-1"],
                hierarchy=[expense_root, "Chi phí hoạt động tín dụng khác"],
            ),
        ],
        columns=_interest_duration_columns(),
    )
    _compiled_specs, _cluster, candidate = _evaluate_interest_expense(
        _page(_section("Thuyết minh", table))
    )
    assert candidate["status"] == expected_status
    if expected_status == READY:
        deposit = next(
            mapping for mapping in candidate["mappings"] if mapping["role"] == "DEPOSIT_INTEREST"
        )
        assert deposit["values"][0] == {
            "coefficient": -4000000,
            "source_text": "(4.000:000)",
            "state": "INFERRED_COLON_GROUP_SEPARATOR_INTEGER_IF_EQUATION_EXACT",
        }
    else:
        assert candidate["mappings"] == []


def test_interest_expense_subtotal_does_not_hide_declared_role_on_other_side() -> None:
    expense_root = "Chi phí lãi và các chi phí tương tự"
    table = _table(
        expense_root,
        [
            _row("Chi phí lãi tiền gửi", ["-4", "-3"]),
            _row(expense_root, ["-8", "-6"], kind="SUBTOTAL", hierarchy=[expense_root]),
            _row(
                "Chi phí lãi tiền gửi",
                ["-4", "-3"],
                hierarchy=[expense_root, "Chi phí lãi tiền gửi"],
            ),
            _row(
                "Chi phí lãi tiền vay",
                ["-2", "-1"],
                hierarchy=[expense_root, "Chi phí lãi tiền vay"],
            ),
            _row(
                "Chi phí phát hành giấy tờ có giá",
                ["-1", "-1"],
                hierarchy=[expense_root, "Chi phí phát hành giấy tờ có giá"],
            ),
            _row(
                "Chi phí hoạt động tín dụng khác",
                ["-1", "-1"],
                hierarchy=[expense_root, "Chi phí hoạt động tín dụng khác"],
            ),
        ],
        columns=_interest_duration_columns(),
    )
    _compiled_specs, _cluster, candidate = _evaluate_interest_expense(
        _page(_section("Thuyết minh", table))
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "DUPLICATE_ROLE_SOURCE_ROWS_NOT_ALL_EQUATION_CONSUMED" in candidate["reasons"]


def test_bank_pledged_flat_validation_roles_project_to_other_after_exact_total() -> None:
    table = _table(
        "Tài sản, GTCG đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu",
        [
            _row(
                "Giấy tờ có giá đưa đi thế chấp, cầm cố "
                "(Thuyết minh số 8.1 và thuyết minh số 13.1)",
                ["60", "50"],
            ),
            _row("Giấy tờ có giá bán và cam kết mua lại", ["20", "10"]),
            _row("Tài sản khác đưa đi thế chấp, cầm cố", ["10", "5"]),
            _row(None, ["90", "65"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    _compiled_specs, _cluster, candidate = _evaluate_bank_pledged_assets(
        _page(_section("Thuyết minh", table))
    )
    assert candidate["status"] == READY
    other = next(mapping for mapping in candidate["mappings"] if mapping["role"] == "OTHER_ASSETS")
    assert [value["coefficient"] for value in other["values"]] == [90, 65]
    assert {source_ref["row_id"] for source_ref in other["source_refs"]} == {
        "r1",
        "r2",
        "r3",
    }
    receipts = candidate["closure_receipt"]["table_receipts"][0][
        "validation_role_leaf_projection_receipts"
    ]
    assert {receipt["source_role"] for receipt in receipts} == {
        "PLEDGED_VALUABLE_PAPERS_SOURCE",
        "REPO_VALUABLE_PAPERS_SOURCE",
    }


def test_bank_pledged_parent_stays_validation_only_and_ordered_repo_projects_to_investment() -> (
    None
):
    parent = "Giấy tờ có giá đưa đi thế chấp, cầm cố"
    table = _table(
        "Tài sản, giấy tờ có giá đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu",
        [
            _row(parent, ["60", "50"]),
            _row("Trong đó:", [None, None], kind="GROUP", hierarchy=["Trong đó:"]),
            _row(
                "- Giấy tờ có giá thuộc chứng khoán kinh doanh",
                ["20", "10"],
                hierarchy=[
                    "Trong đó: Các khoản chi tiết",
                    "- Giấy tờ có giá thuộc chứng khoán kinh doanh",
                ],
            ),
            _row(
                "- Giấy tờ có giá thuộc chứng khoán đầu tư",
                ["40", "40"],
                hierarchy=[
                    "Trong đó: Các khoản chi tiết",
                    "- Giấy tờ có giá thuộc chứng khoán đầu tư",
                ],
            ),
            _row("Giấy tờ có giá bán và cam kết mua lại", ["15", "10"]),
            _row("Tài sản khác đưa đi thế chấp, cầm cố", ["5", "5"]),
            _row(None, ["80", "65"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    _compiled_specs, _cluster, candidate = _evaluate_bank_pledged_assets(
        _page(_section("Thuyết minh", table))
    )
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [value["coefficient"] for value in by_role["TRADING_SECURITIES"]["values"]] == [
        20,
        10,
    ]
    assert [value["coefficient"] for value in by_role["INVESTMENT_SECURITIES"]["values"]] == [
        55,
        50,
    ]
    assert [value["coefficient"] for value in by_role["OTHER_ASSETS"]["values"]] == [5, 5]
    mapped_source_rows = {
        source_ref["row_id"]
        for mapping in candidate["mappings"]
        for source_ref in mapping["source_refs"]
    }
    assert "r1" not in mapped_source_rows
    assert "r5" in mapped_source_rows

    # A printed total that counts both a visible carrier and its disclosed
    # ``Trong đó`` children is retained only through the explicit source-
    # contradiction receipt. Child mappings still use the non-overlapping
    # hierarchy; the engine neither silently fixes nor double-maps the parent.
    table["rows"][-1]["values_exact"] = ["140", "115"]
    double_counted_page = _page(_section("Thuyết minh", table))
    compiled_specs, cluster, double_counted = _evaluate_bank_pledged_assets(double_counted_page)
    assert double_counted["status"] == READY
    double_counted_by_role = {mapping["role"]: mapping for mapping in double_counted["mappings"]}
    assert [
        value["coefficient"] for value in double_counted_by_role["FAMILY_ROOT_TOTAL"]["values"]
    ] == [140, 115]
    assert (
        len(
            double_counted["closure_receipt"]["table_receipts"][0][
                "source_hierarchy_overlap_total_receipts"
            ]
        )
        == 1
    )

    forged = copy.deepcopy(double_counted)
    forged["closure_receipt"]["table_receipts"][0]["source_hierarchy_overlap_total_receipts"][0][
        "overlap_edges"
    ][0]["child_row_ordinal"] = 6
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
            page_json_by_version={VERSION_ID: double_counted_page},
            compiled_specs=compiled_specs,
            query_receipt=(
                build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
                    cluster["component_regions"]
                )
            ),
        )

    table["rows"][-1]["values_exact"] = ["141", "115"]
    _compiled_specs, _cluster, unexplained = _evaluate_bank_pledged_assets(
        _page(_section("Thuyết minh", table))
    )
    assert unexplained["status"] == UNRESOLVED
    assert unexplained["mappings"] == []

    # The overlap exception cannot hide a mapped parent: only an explicitly
    # validation-only carrier may coexist with its mapped detail frontier.
    table["rows"][0]["label_exact"] = "Tài sản khác"
    table["rows"][0]["hierarchy_path_exact"] = ["Tài sản khác"]
    table["rows"][-1]["values_exact"] = ["140", "115"]
    _compiled_specs, _cluster, mapped_parent = _evaluate_bank_pledged_assets(
        _page(_section("Thuyết minh", table))
    )
    assert mapped_parent["status"] == UNRESOLVED
    assert mapped_parent["mappings"] == []


def test_bank_pledged_unaliased_rows_project_only_from_exact_source_total_frontier() -> None:
    table = _table(
        "Tài sản, GTCG đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu",
        [
            _row("Tiền gửi có kỳ hạn tại TCTD khác", ["60", "50"]),
            _row("Chứng khoán đầu tư", ["30", "20"]),
            _row(None, ["90", "70"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    _compiled_specs, _cluster, candidate = _evaluate_bank_pledged_assets(
        _page(_section("Thuyết minh", table))
    )
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [value["coefficient"] for value in by_role["INVESTMENT_SECURITIES"]["values"]] == [
        30,
        20,
    ]
    assert [value["coefficient"] for value in by_role["OTHER_ASSETS"]["values"]] == [60, 50]

    table["rows"][-1]["values_exact"] = ["91", "70"]
    _compiled_specs, _cluster, mismatch = _evaluate_bank_pledged_assets(
        _page(_section("Thuyết minh", table))
    )
    assert mismatch["status"] == UNRESOLVED
    assert mismatch["mappings"] == []


def test_bank_pledged_exact_owner_whole_table_accepts_unaliased_terminal_frontier() -> None:
    table = _table(
        "Tài sản, GTCG đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu",
        [
            _row("Trái phiếu đặc biệt do tổ chức khác phát hành", ["60", "50"]),
            _row("Công cụ nợ chưa niêm yết", ["30", "20"]),
            _row(None, ["90", "70"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    _compiled_specs, cluster, candidate = _evaluate_bank_pledged_assets(
        _page(_section("Thuyết minh", table))
    )
    assert cluster["status"] == READY
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [value["coefficient"] for value in by_role["OTHER_ASSETS"]["values"]] == [
        90,
        70,
    ]
    assert [value["coefficient"] for value in by_role["FAMILY_ROOT_TOTAL"]["values"]] == [
        90,
        70,
    ]

    table["rows"][-1]["values_exact"] = ["91", "70"]
    _compiled_specs, _cluster, mismatch = _evaluate_bank_pledged_assets(
        _page(_section("Thuyết minh", table))
    )
    assert mismatch["status"] == UNRESOLVED
    assert mismatch["mappings"] == []


def test_bank_pledged_exact_owner_single_declared_root_component_derives_root() -> None:
    table = _table(
        "Tài sản, GTCG đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu",
        [_row("Giấy tờ có giá", ["60", "50"])],
    )
    _compiled_specs, cluster, candidate = _evaluate_bank_pledged_assets(
        _page(_section("Thuyết minh", table))
    )
    assert cluster["status"] == READY
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [value["coefficient"] for value in by_role["OTHER_ASSETS"]["values"]] == [
        60,
        50,
    ]
    assert [value["coefficient"] for value in by_role["FAMILY_ROOT_TOTAL"]["values"]] == [
        60,
        50,
    ]

    ownerless = _table(None, [_row("Giấy tờ có giá", ["60", "50"])])
    compiled = _bank_pledged_assets_compiled()
    not_observed = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(_page(_section("Thuyết minh", ownerless)))],
        compiled_specs=compiled,
    )
    assert not_observed["status"] == NOT_OBSERVED


def test_bank_pledged_validation_leaf_without_exact_source_total_is_unresolved() -> None:
    table = _table(
        "Tài sản, GTCG đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu",
        [_row("Giấy tờ có giá đưa đi thế chấp, cầm cố", ["60", "50"])],
    )
    _compiled_specs, _cluster, candidate = _evaluate_bank_pledged_assets(
        _page(_section("Thuyết minh", table))
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_bank_pledged_projection_policies_reject_invalid_declarations() -> None:
    evaluation = _json("tm-bank-pledged-discounted-assets-evaluation-v1.json")
    evaluation["equation_consumed_unmatched_residual_anchor_policy"] = "VALUE_SEARCH"
    with pytest.raises(
        GeminiJsonMultitableHierarchicalFamilyV1Error,
        match="unmatched residual anchor policy is invalid",
    ):
        compile_gemini_json_multitable_hierarchical_family_specs_v1(
            _json("tm-bank-pledged-discounted-assets-topology-v1.json"),
            evaluation,
            _json("tm-bank-pledged-discounted-assets-schema-binding-v1.json"),
        )

    evaluation = _json("tm-bank-pledged-discounted-assets-evaluation-v1.json")
    evaluation["owner_complete_population_policy"] = "VALUE_SELECTED_COMPLETE_TABLE"
    with pytest.raises(
        GeminiJsonMultitableHierarchicalFamilyV1Error,
        match="owner-complete population policy is invalid",
    ):
        compile_gemini_json_multitable_hierarchical_family_specs_v1(
            _json("tm-bank-pledged-discounted-assets-topology-v1.json"),
            evaluation,
            _json("tm-bank-pledged-discounted-assets-schema-binding-v1.json"),
        )

    evaluation = _json("tm-bank-pledged-discounted-assets-evaluation-v1.json")
    evaluation["source_hierarchy_overlap_total_policy"] = "SEARCH_OVERLAPPING_VALUES"
    with pytest.raises(
        GeminiJsonMultitableHierarchicalFamilyV1Error,
        match="source hierarchy overlap policy is invalid",
    ):
        compile_gemini_json_multitable_hierarchical_family_specs_v1(
            _json("tm-bank-pledged-discounted-assets-topology-v1.json"),
            evaluation,
            _json("tm-bank-pledged-discounted-assets-schema-binding-v1.json"),
        )

    evaluation = _json("tm-bank-pledged-discounted-assets-evaluation-v1.json")
    evaluation["validation_role_leaf_projections"][0]["target_role"] = (
        "PLEDGED_VALUABLE_PAPERS_SOURCE"
    )
    with pytest.raises(
        GeminiJsonMultitableHierarchicalFamilyV1Error,
        match="validation leaf projection is invalid",
    ):
        compile_gemini_json_multitable_hierarchical_family_specs_v1(
            _json("tm-bank-pledged-discounted-assets-topology-v1.json"),
            evaluation,
            _json("tm-bank-pledged-discounted-assets-schema-binding-v1.json"),
        )


def _contingent_multi_metric_page() -> dict:
    columns = [
        {
            "header_path_exact": [
                "31/12/2025",
                "Triệu đồng",
                "Giá trị theo hợp đồng gộp",
            ],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": ["31/12/2025", "Triệu đồng", "Tiền gửi ký quỹ"],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": [
                "31/12/2025",
                "Triệu đồng",
                "Giá trị theo hợp đồng thuần",
            ],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": [
                "31/12/2024",
                "Triệu đồng",
                "Giá trị theo hợp đồng gộp",
            ],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": ["31/12/2024", "Triệu đồng", "Tiền gửi ký quỹ"],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": [
                "31/12/2024",
                "Triệu đồng",
                "Giá trị theo hợp đồng thuần",
            ],
            "value_kind": "MONEY",
        },
    ]
    table = _table(
        None,
        [
            _row("Cam kết giao dịch hối đoái", ["100", None, "100", "80", None, "80"]),
            _row("Cam kết trong nghiệp vụ thư tín dụng", ["22", "2", "20", "16", "1", "15"]),
            _row("Bảo lãnh khác", ["11", "1", "10", "9", "1", "8"]),
            _row("Các cam kết khác", ["5", "-", "5", "7", "-", "7"]),
            _row(None, ["138", "3", "135", "112", "2", "110"], kind="TOTAL"),
        ],
        columns=columns,
    )
    return _page(
        _section(
            "Nghĩa vụ nợ tiềm ẩn và các cam kết đưa ra",
            table,
        )
    )


def test_declared_multi_metric_lane_maps_only_exact_result_metric() -> None:
    page = _contingent_multi_metric_page()
    compiled, cluster, candidate = _evaluate_contingent_liabilities(page)
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [cell["coefficient"] for cell in by_role["LETTER_OF_CREDIT"]["values"]] == [
        20,
        15,
    ]
    assert [cell["coefficient"] for cell in by_role["GUARANTEE_OTHER"]["values"]] == [
        10,
        8,
    ]
    assert [cell["coefficient"] for cell in by_role["FAMILY_ROOT_TOTAL"]["values"]] == [
        135,
        110,
    ]
    table_receipt = candidate["closure_receipt"]["table_receipts"][0]
    assert table_receipt["lane_axis"]["money_column_ordinals"] == [3, 6]
    metric_equations = [
        equation
        for equation in candidate["closure_receipt"]["equations"]
        if equation["equation_kind"]
        == "EXACT_DECLARED_SOURCE_MULTI_METRIC_ROW_EQUATION_SELECTS_RESULT_LANE"
    ]
    assert len(metric_equations) == 10
    assert {equation["status"] for equation in metric_equations} == {"EXACT"}

    validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
        candidate,
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            cluster["component_regions"]
        ),
    )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda table: table["rows"][1]["values_exact"].__setitem__(2, "21"),
        lambda table: table["columns"][1]["header_path_exact"].__setitem__(
            2, "Giá trị theo hợp đồng gộp"
        ),
        lambda table: table["columns"][1]["header_path_exact"].append(
            "Giá trị theo hợp đồng thuần"
        ),
    ],
)
def test_declared_multi_metric_lane_fails_closed_on_equation_or_axis_drift(mutate) -> None:
    page = _contingent_multi_metric_page()
    table = page["sections"][0]["tables"][0]
    mutate(table)
    _compiled_specs, _cluster, candidate = _evaluate_contingent_liabilities(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_declared_multi_metric_policy_does_not_change_ordinary_two_period_table() -> None:
    table = _table(
        None,
        [
            _row("Cam kết giao dịch hối đoái", ["100", "80"]),
            _row("Cam kết trong nghiệp vụ thư tín dụng", ["20", "15"]),
            _row("Bảo lãnh khác", ["10", "8"]),
            _row("Các cam kết khác", ["5", "7"]),
            _row(None, ["135", "110"], kind="TOTAL"),
        ],
    )
    page = _page(
        _section(
            "Nghĩa vụ nợ tiềm ẩn và các cam kết đưa ra",
            table,
        )
    )
    _compiled_specs, _cluster, candidate = _evaluate_contingent_liabilities(page)
    assert candidate["status"] == READY
    assert candidate["closure_receipt"]["table_receipts"][0]["lane_axis"][
        "money_column_ordinals"
    ] == [1, 2]


def test_multi_metric_sign_rejects_boolean_disguised_as_integer() -> None:
    evaluation = _json("tm-contingent-liabilities-commitments-evaluation-v1.json")
    evaluation["multi_metric_lane_equation"]["component_terms"][0]["sign"] = True
    with pytest.raises(
        GeminiJsonMultitableHierarchicalFamilyV1Error,
        match="metric component term is invalid",
    ):
        compile_gemini_json_multitable_hierarchical_family_specs_v1(
            _json("tm-contingent-liabilities-commitments-topology-v1.json"),
            evaluation,
            _json("tm-contingent-liabilities-commitments-schema-binding-v1.json"),
        )


def _contingent_signed_context_page() -> dict:
    table = _table(
        None,
        [
            _row("Bảo lãnh vay vốn", ["5", "4"]),
            _row("Cam kết trong nghiệp vụ L/C", ["20", "15"]),
            _row("Cam kết trong nghiệp vụ L/C", ["22", "16"]),
            _row("- Trừ: Tiền ký quỹ", ["(2)", "(1)"]),
            _row("Bảo lãnh khác", ["10", "8"]),
            _row("- Cam kết bảo lãnh khác", ["11", "9"]),
            _row("- Trừ: Tiền ký quỹ", ["(1)", "(1)"]),
            _row("Các cam kết khác", ["5", "7"]),
            _row(None, ["40", "34"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    return _page(
        _section(
            "Nghĩa vụ nợ tiềm ẩn và các cam kết đưa ra",
            table,
        )
    )


def test_signed_context_frontier_maps_net_carrier_without_double_counting() -> None:
    page = _contingent_signed_context_page()
    compiled, cluster, candidate = _evaluate_contingent_liabilities(page)
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [cell["coefficient"] for cell in by_role["LETTER_OF_CREDIT"]["values"]] == [
        20,
        15,
    ]
    assert [cell["coefficient"] for cell in by_role["GUARANTEE_OTHER"]["values"]] == [
        10,
        8,
    ]
    assert [cell["coefficient"] for cell in by_role["FAMILY_ROOT_TOTAL"]["values"]] == [
        40,
        34,
    ]
    receipts = candidate["closure_receipt"]["table_receipts"][0]["signed_context_frontier_receipts"]
    assert [receipt["carrier_role"] for receipt in receipts] == [
        "LETTER_OF_CREDIT",
        "GUARANTEE_OTHER",
    ]
    validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
        candidate,
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            cluster["component_regions"]
        ),
    )

    page["sections"][0]["tables"][0]["rows"][3]["values_exact"][0] = "(3)"
    _compiled_specs, _cluster, mismatch = _evaluate_contingent_liabilities(page)
    assert mismatch["status"] == UNRESOLVED
    assert mismatch["mappings"] == []


@pytest.mark.parametrize(
    "mutation",
    (
        "DUPLICATE_ADJUSTMENT",
        "POSITIVE_ADJUSTMENT",
        "THIRD_CARRIER",
        "REORDERED_FRONTIER",
        "INTERVENING_UNDECLARED_ROW",
    ),
)
def test_signed_context_frontier_fails_closed_on_ambiguous_source_shapes(
    mutation: str,
) -> None:
    page = _contingent_signed_context_page()
    rows = page["sections"][0]["tables"][0]["rows"]
    if mutation == "DUPLICATE_ADJUSTMENT":
        rows.insert(4, _row("- Trừ: Tiền ký quỹ", ["(1)", "(1)"]))
    elif mutation == "POSITIVE_ADJUSTMENT":
        rows[3]["values_exact"] = ["2", "1"]
    elif mutation == "THIRD_CARRIER":
        rows.insert(3, _row("Cam kết trong nghiệp vụ L/C", ["23", "17"]))
    elif mutation == "REORDERED_FRONTIER":
        rows[2], rows[3] = rows[3], rows[2]
    else:
        rows.insert(3, _row("Khoản mục ngoại lai", ["1", "1"]))

    compiled = _contingent_liabilities_compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    if cluster["status"] != READY:
        assert cluster["component_regions"] == []
        return
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            cluster["component_regions"]
        ),
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_exact_owner_complete_role_frontier_excludes_following_unrelated_money_table() -> None:
    family = _table(
        None,
        [
            _row("Bảo lãnh vay vốn", ["5", "4"]),
            _row("Cam kết trong nghiệp vụ L/C", ["20", "15"]),
            _row("Bảo lãnh khác", ["10", "8"]),
            _row("Các cam kết khác", ["5", "7"]),
        ],
    )
    unrelated = _table(
        None,
        [
            _row("Đến 1 năm", ["3", "2"]),
            _row("Trên 1 năm", ["4", "3"]),
            _row(None, ["7", "5"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    page = _page(
        _section("Nghĩa vụ nợ tiềm ẩn và các cam kết đưa ra", family),
        _section("Cam kết thuê hoạt động", unrelated),
    )
    _compiled_specs, cluster, candidate = _evaluate_contingent_liabilities(page)
    assert cluster["status"] == READY
    assert [(item["section_id"], item["table_id"]) for item in cluster["component_regions"]] == [
        ("s1", "t1")
    ]
    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 4


@pytest.mark.parametrize(
    "mutation",
    ("UNBOUND_ROW", "MISSING_REQUIRED_ROLE", "SECOND_COMPLETE_TABLE"),
)
def test_exact_owner_complete_role_frontier_fails_closed_when_not_unique_or_complete(
    mutation: str,
) -> None:
    family = _table(
        None,
        [
            _row("Bảo lãnh vay vốn", ["5", "4"]),
            _row("Cam kết trong nghiệp vụ L/C", ["20", "15"]),
            _row("Bảo lãnh khác", ["10", "8"]),
            _row("Các cam kết khác", ["5", "7"]),
        ],
    )
    tables = [family]
    if mutation == "UNBOUND_ROW":
        family["rows"].append(_row("Khoản mục ngoại lai", ["1", "1"]))
    elif mutation == "MISSING_REQUIRED_ROLE":
        family["rows"].pop(2)
    else:
        tables.append(copy.deepcopy(family))
    page = _page(_section("Nghĩa vụ nợ tiềm ẩn và các cam kết đưa ra", *tables))
    compiled = _contingent_liabilities_compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    if cluster["status"] != READY:
        assert cluster["component_regions"] == []
        return
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            cluster["component_regions"]
        ),
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def _contingent_unlabeled_group_subtotals_page() -> dict:
    table = _table(
        None,
        [
            _row("Nghĩa vụ tiềm ẩn", [None, None], kind="GROUP"),
            _row(
                "Bảo lãnh vay vốn",
                ["5", "4"],
                hierarchy=["Nghĩa vụ tiềm ẩn", "Bảo lãnh vay vốn"],
            ),
            _row(
                "Cam kết trong nghiệp vụ L/C",
                ["20", "15"],
                hierarchy=["Nghĩa vụ tiềm ẩn", "Cam kết trong nghiệp vụ L/C"],
            ),
            _row(
                "Bảo lãnh khác",
                ["10", "8"],
                hierarchy=["Nghĩa vụ tiềm ẩn", "Bảo lãnh khác"],
            ),
            _row(None, ["35", "27"], kind="SUBTOTAL", hierarchy=["Nghĩa vụ tiềm ẩn", None]),
            _row("Các cam kết đưa ra", [None, None], kind="GROUP"),
            _row(
                "Cam kết giao dịch hối đoái",
                ["30", "20"],
                hierarchy=["Các cam kết đưa ra", "Cam kết giao dịch hối đoái"],
            ),
            _row(
                "Các cam kết khác",
                ["5", "7"],
                hierarchy=["Các cam kết đưa ra", "Các cam kết khác"],
            ),
            _row(None, ["35", "27"], kind="SUBTOTAL", hierarchy=["Các cam kết đưa ra", None]),
            _row(None, ["70", "54"], kind="TOTAL", hierarchy=[None]),
        ],
    )
    return _page(_section("Nghĩa vụ nợ tiềm ẩn và các cam kết đưa ra", table))


def test_unlabeled_group_subtotals_close_terminal_family_total() -> None:
    _compiled_specs, _cluster, candidate = _evaluate_contingent_liabilities(
        _contingent_unlabeled_group_subtotals_page()
    )
    assert candidate["status"] == READY
    equation_kinds = {
        equation["equation_kind"] for equation in candidate["closure_receipt"]["equations"]
    }
    root = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL"
    )
    assert [value["coefficient"] for value in root["values"]] == [70, 54]
    assert {source_ref["row_id"] for source_ref in root["source_refs"]} == {"r10"}
    assert "EXACT_LABEL_ONLY_GROUP_DIRECT_CHILDREN_EQUAL_UNLABELED_SUBTOTAL" in equation_kinds
    assert "EXACT_CLOSED_STRUCTURAL_GROUP_SUBTOTALS_EQUAL_TERMINAL_TOTAL" in equation_kinds


@pytest.mark.parametrize(
    "mutation",
    ("INCOMPLETE_GROUP", "CONFLICTING_SUBTOTAL", "DUPLICATE_SUBTOTAL"),
)
def test_unlabeled_group_subtotals_fail_closed_when_frontier_is_not_exact(
    mutation: str,
) -> None:
    page = _contingent_unlabeled_group_subtotals_page()
    rows = page["sections"][0]["tables"][0]["rows"]
    if mutation == "INCOMPLETE_GROUP":
        rows.pop(2)
    elif mutation == "CONFLICTING_SUBTOTAL":
        rows[4]["values_exact"][0] = "36"
    else:
        rows.insert(
            5, _row(None, ["35", "27"], kind="SUBTOTAL", hierarchy=["Nghĩa vụ tiềm ẩn", None])
        )
    _compiled_specs, _cluster, candidate = _evaluate_contingent_liabilities(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    if mutation == "DUPLICATE_SUBTOTAL":
        assert candidate["reasons"] == ["UNLABELED_STRUCTURAL_SUBTOTAL_NOT_UNIQUE"]
        assert candidate["closure_receipt"]["table_receipts"][0][
            "ambiguous_unlabeled_structural_subtotals"
        ] == [
            {
                "hierarchy_path_normalized": ["nghia vu tiem an"],
                "row_ordinals": [5, 6],
            }
        ]
