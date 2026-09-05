from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    READY,
    compile_gemini_json_flat_family_specs_v1,
    evaluate_gemini_json_flat_family_table_v1,
)
from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import (
    evaluate_gemini_json_hierarchical_period_table_pair_v1,
)

ROOT = Path(__file__).resolve().parents[2]
RUNNER_SPEC = importlib.util.spec_from_file_location(
    "run_gemini_json_first_accounting_family_f8_adaptation_v1",
    ROOT / "scripts/experiments/run_gemini_json_first_accounting_family_v1.py",
)
assert RUNNER_SPEC is not None and RUNNER_SPEC.loader is not None
runner = importlib.util.module_from_spec(RUNNER_SPEC)
RUNNER_SPEC.loader.exec_module(runner)


def _compiled_specs() -> dict:
    topology, evaluation, schema = (
        json.loads((ROOT / path).read_text(encoding="utf-8"))
        for path in (
            "config/families/tm-loan-quality-classification-topology-v1.json",
            "config/families/tm-loan-quality-classification-evaluation-v1.json",
            "config/families/tm-loan-quality-classification-schema-binding-v1.json",
        )
    )
    return compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)


def _page(
    *,
    extra_label: str,
    extra_values: list[str],
    table_title: str = "Phân tích chất lượng nợ cho vay",
) -> dict:
    rows = [
        {
            "hierarchy_path_exact": [label],
            "label_exact": label,
            "row_kind": "ITEM",
            "values_exact": values,
        }
        for label, values in (
            ("Nhóm 1 - Nợ đủ tiêu chuẩn", ["100", "90"]),
            ("Nhóm 2 - Nợ cần chú ý", ["20", "10"]),
            ("Nhóm 3 - Nợ dưới tiêu chuẩn", ["5", "4"]),
            ("Nhóm 4 - Nợ nghi ngờ", ["3", "2"]),
            ("Nhóm 5 - Nợ có khả năng mất vốn", ["2", "1"]),
            (extra_label, extra_values),
        )
    ]
    rows.append(
        {
            "hierarchy_path_exact": [None],
            "label_exact": None,
            "row_kind": "TOTAL",
            "values_exact": ["137", "113"],
        }
    )
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [
                    {
                        "columns": [
                            {
                                "header_path_exact": ["31/12/2025", "Triệu đồng"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": ["31/12/2024", "Triệu đồng"],
                                "value_kind": "MONEY",
                            },
                        ],
                        "continuation": "NONE",
                        "rows": rows,
                        "title_exact": table_title,
                        "unit_exact": "Triệu đồng",
                    }
                ],
                "title_exact": "Cho vay khách hàng",
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _evaluate(page: dict) -> dict:
    return evaluate_gemini_json_flat_family_table_v1(
        page_json=page,
        page_json_version_id="gfpstorev1:json:" + "8" * 64,
        physical_page=23,
        section_id="s1",
        table_id="t1",
        compiled_specs=_compiled_specs(),
    )


@pytest.mark.parametrize(
    "label",
    [
        (
            "Các khoản nợ chờ xử lý đã có tài sản xiết nợ, gán nợ và nợ tồn đọng "
            "có tài sản bảo đảm"
        ),
        (
            "Các khoản nợ chờ xử lý đã có tài sản xiết nợ, gán nợ và nợ tồn đọng "
            "có tài sản đảm bảo"
        ),
        (
            "Các khoản nợ chờ xử lý đã có tài sản gán xiết nợ, gán nợ và nợ tồn đọng "
            "có tài sản bảo đảm"
        ),
    ],
)
def test_pending_processing_debt_closes_total_but_remains_source_only(label: str) -> None:
    result = _evaluate(_page(extra_label=label, extra_values=["7", "6"]))

    assert result["status"] == READY
    assert "PENDING_PROCESSING_SECURED_DEBT" not in {
        mapping["role"] for mapping in result["mappings"]
    }
    root = next(
        mapping for mapping in result["mappings"] if mapping["role"] == "LOAN_QUALITY_CLASSIFICATION"
    )
    assert [value["coefficient"] for value in root["values"]] == [137, 113]
    assert result["closure_receipt"]["equations"][-1]["component_roles"][-1] == (
        "PENDING_PROCESSING_SECURED_DEBT"
    )


def test_activity_margin_wording_maps_to_standalone_margin_schema_id() -> None:
    result = _evaluate(
        _page(
            extra_label=(
                "Các khoản cho vay hoạt động ký quỹ và cho vay hoạt động ứng trước tiền bán "
                "của khách hàng"
            ),
            extra_values=["7", "6"],
        )
    )

    assert result["status"] == READY
    margin = next(
        mapping
        for mapping in result["mappings"]
        if mapping["role"] == "STANDALONE_MARGIN_AND_SECURITIES_ADVANCE"
    )
    assert margin["report_norm_id"] == 1944
    assert [value["coefficient"] for value in margin["values"]] == [7, 6]


def test_tt31_regulatory_population_is_not_mapped_under_customer_loans() -> None:
    result = _evaluate(
        _page(
            extra_label="Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
            extra_values=["7", "6"],
            table_title=(
                "10.5 Phân tích chất lượng nợ cho vay "
                "(theo TT31/2024/TT NHNN)"
            ),
        )
    )

    assert result["status"] != READY
    assert "HARD_NEGATIVE_FAMILY_TITLE_PRESENT" in result["reasons"]


def _broad_customer_loan_table_page(
    *,
    duplicate_parent: bool = False,
    hierarchy_leak: bool = False,
) -> dict:
    parent = "Phân tích chất lượng nợ cho vay"
    rows = [
        {
            "hierarchy_path_exact": ["Cho vay theo loại hình"],
            "label_exact": "Cho vay các tổ chức kinh tế, cá nhân trong nước",
            "row_kind": "ITEM",
            "values_exact": ["999", "888"],
        },
        {
            "hierarchy_path_exact": ["Cho vay theo loại hình", "Tổng"],
            "label_exact": "Tổng",
            "row_kind": "TOTAL",
            "values_exact": ["999", "888"],
        },
        {
            "hierarchy_path_exact": [parent],
            "label_exact": parent,
            "row_kind": "GROUP",
            "values_exact": [None, None],
        },
        {
            "hierarchy_path_exact": [parent, "Chỉ tiêu"],
            "label_exact": "Chỉ tiêu",
            "row_kind": "GROUP",
            "values_exact": [None, None],
        },
    ]
    rows.extend(
        {
            "hierarchy_path_exact": [parent, label],
            "label_exact": label,
            "row_kind": "ITEM",
            "values_exact": values,
        }
        for label, values in (
            ("Nợ đủ tiêu chuẩn", ["100", "90"]),
            ("Nợ cần chú ý", ["20", "10"]),
            ("Nợ dưới tiêu chuẩn", ["5", "4"]),
            ("Nợ nghi ngờ", ["3", "2"]),
            ("Nợ có khả năng mất vốn", ["2", "1"]),
        )
    )
    if hierarchy_leak:
        rows.append(
            {
                "hierarchy_path_exact": [parent, "Khoản chưa xác định"],
                "label_exact": "Khoản chưa xác định",
                "row_kind": "ITEM",
                "values_exact": ["1", "1"],
            }
        )
    rows.extend(
        [
            {
                "hierarchy_path_exact": [parent, "Tổng"],
                "label_exact": "Tổng",
                "row_kind": "TOTAL",
                "values_exact": ["130", "107"],
            },
            {
                "hierarchy_path_exact": ["Phân tích dư nợ theo thời gian"],
                "label_exact": "Phân tích dư nợ theo thời gian",
                "row_kind": "GROUP",
                "values_exact": [None, None],
            },
            {
                "hierarchy_path_exact": ["Phân tích dư nợ theo thời gian", "Nợ ngắn hạn"],
                "label_exact": "Nợ ngắn hạn",
                "row_kind": "ITEM",
                "values_exact": ["999", "888"],
            },
        ]
    )
    if duplicate_parent:
        rows.append(
            {
                "hierarchy_path_exact": [parent],
                "label_exact": parent,
                "row_kind": "GROUP",
                "values_exact": [None, None],
            }
        )
    page = _page(
        extra_label="Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
        extra_values=["7", "6"],
        table_title="Cho vay khách hàng",
    )
    page["sections"][0]["tables"][0]["rows"] = rows
    return page


def test_unique_explicit_quality_group_slices_broad_customer_loan_table() -> None:
    result = _evaluate(_broad_customer_loan_table_page())

    assert result["status"] == READY
    assert [mapping["report_norm_id"] for mapping in result["mappings"]] == [
        746,
        747,
        748,
        749,
        750,
        751,
    ]


@pytest.mark.parametrize("mutation", ["duplicate_parent", "hierarchy_leak"])
def test_broad_customer_loan_subtree_slice_fails_closed_on_ambiguity(mutation: str) -> None:
    result = _evaluate(
        _broad_customer_loan_table_page(
            duplicate_parent=mutation == "duplicate_parent",
            hierarchy_leak=mutation == "hierarchy_leak",
        )
    )

    assert result["status"] != READY
    assert result["mappings"] == []


def test_specific_quality_title_does_not_slice_generic_customer_loan_carrier() -> None:
    page = _page(
        extra_label="Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
        extra_values=["7", "6"],
        table_title="Phân tích dư nợ cho vay theo chất lượng nợ",
    )
    delayed = (
        "Nghiệp vụ phát hành thư tín dụng trả chậm phát sinh trước ngày "
        "01 tháng 7 năm 2024"
    )
    page["sections"][0]["title_exact"] = "Thuyết minh cho vay khách hàng"
    page["sections"][0]["tables"][0]["rows"] = [
        {
            "hierarchy_path_exact": ["Cho vay khách hàng"],
            "label_exact": "Cho vay khách hàng",
            "row_kind": "SUBTOTAL",
            "values_exact": ["130", "107"],
        },
        *[
            {
                "hierarchy_path_exact": ["Cho vay khách hàng", label],
                "label_exact": label,
                "row_kind": "ITEM",
                "values_exact": values,
            }
            for label, values in (
                ("Nợ đủ tiêu chuẩn", ["100", "90"]),
                ("Nợ cần chú ý", ["20", "10"]),
                ("Nợ dưới tiêu chuẩn", ["5", "4"]),
                ("Nợ nghi ngờ", ["3", "2"]),
                ("Nợ có khả năng mất vốn", ["2", "1"]),
            )
        ],
        {
            "hierarchy_path_exact": [delayed],
            "label_exact": delayed,
            "row_kind": "SUBTOTAL",
            "values_exact": ["7", "6"],
        },
        {
            "hierarchy_path_exact": [delayed, "Nợ đủ tiêu chuẩn"],
            "label_exact": "Nợ đủ tiêu chuẩn",
            "row_kind": "ITEM",
            "values_exact": ["7", "6"],
        },
        {
            "hierarchy_path_exact": [None],
            "label_exact": None,
            "row_kind": "TOTAL",
            "values_exact": ["137", "113"],
        },
    ]

    result = _evaluate(page)

    assert result["status"] == READY
    mappings = {mapping["role"]: mapping for mapping in result["mappings"]}
    assert [value["coefficient"] for value in mappings["STANDARD"]["values"]] == [107, 96]
    assert [
        value["coefficient"]
        for value in mappings["LOAN_QUALITY_CLASSIFICATION"]["values"]
    ] == [137, 113]


def _period_table(
    values_by_row: list[list[str]],
    *,
    title: str | None = None,
    other_header: str = "Tài sản khác",
) -> dict:
    labels = [
        "Nợ đủ tiêu chuẩn",
        "Nợ cần chú ý",
        "Nợ dưới tiêu chuẩn",
        "Nợ nghi ngờ",
        "Nợ có khả năng mất vốn",
        "Tổng",
    ]
    return {
        "columns": [
            {"header_path_exact": ["Cho vay khách hàng", "Triệu VND"], "value_kind": "MONEY"},
            {"header_path_exact": [other_header, "Triệu VND"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            {
                "hierarchy_path_exact": [label],
                "label_exact": label,
                "row_kind": "TOTAL" if label == "Tổng" else "ITEM",
                "values_exact": values,
            }
            for label, values in zip(labels, values_by_row, strict=True)
        ],
        "title_exact": title,
        "unit_exact": "Triệu VND",
    }


def _period_pair_page(narratives: list[str]) -> dict:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": narratives,
                "statement_type": "NOT_APPLICABLE",
                "tables": [
                    _period_table(
                        [
                            ["100", "40"],
                            ["20", "5"],
                            ["5", "2"],
                            ["3", "1"],
                            ["2", "2"],
                            ["130", "50"],
                        ]
                    ),
                    _period_table(
                        [
                            ["90", "30"],
                            ["10", "4"],
                            ["4", "2"],
                            ["2", "1"],
                            ["1", "1"],
                            ["107", "38"],
                        ]
                    ),
                ],
                "title_exact": "Thuyết minh báo cáo tài chính quý IV năm 2025 (tiếp theo)",
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _project_period_pair(page: dict) -> dict | None:
    return evaluate_gemini_json_hierarchical_period_table_pair_v1(
        page_json=page,
        page_json_version_id="gfpstorev1:json:" + "9" * 64,
        physical_page=81,
        section_id="s1",
        table_ids=["t1", "t2"],
        compiled_specs=_compiled_specs(),
    )


def test_horizontal_period_tables_accept_unique_exact_narrative_date_pair() -> None:
    narrative = (
        "Tại ngày 31 tháng 12 năm 2025, tỷ lệ nợ xấu là 1,68% "
        "(tại ngày 31 tháng 12 năm 2024 là 1,57%). Chi tiết như sau:"
    )
    result = _project_period_pair(_period_pair_page([narrative]))

    assert result is not None and result["status"] == READY
    assert [mapping["report_norm_id"] for mapping in result["mappings"]] == [
        746,
        747,
        748,
        749,
        750,
        751,
    ]
    receipt = result["period_table_projection_receipt"]
    assert receipt["period_signatures"] == ["2025-12-31", "2024-12-31"]
    assert receipt["period_date_sources"] == [
        "SECTION_NARRATIVE_ORDERED_PERIOD_PAIR",
        "SECTION_NARRATIVE_ORDERED_PERIOD_PAIR",
    ]
    assert receipt["narrative_period_binding"]["narrative_exact"] == narrative
    assert receipt["narrative_period_binding"]["date_source_texts_exact"] == [
        "ngày 31 tháng 12 năm 2025",
        "ngày 31 tháng 12 năm 2024",
    ]
    assert result["mappings"][0]["columns"][0]["header_path_exact"][0] == (
        "ngày 31 tháng 12 năm 2025"
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "one_date",
        "three_dates",
        "reverse_dates",
        "same_date",
        "one_table_date",
        "third_table",
        "header_mismatch",
        "arithmetic_mismatch",
        "another_narrative_date",
    ],
)
def test_narrative_period_pair_fails_closed_on_ambiguous_source(mutation: str) -> None:
    narratives = [
        (
            "Tại ngày 31 tháng 12 năm 2025, tỷ lệ nợ xấu là 1,68% "
            "(tại ngày 31 tháng 12 năm 2024 là 1,57%). Chi tiết như sau:"
        )
    ]
    page = _period_pair_page(narratives)
    if mutation == "one_date":
        narratives[0] = "Tại ngày 31 tháng 12 năm 2025, chi tiết như sau."
    elif mutation == "three_dates":
        narratives[0] += " Lập ngày 1 tháng 1 năm 2025."
    elif mutation == "reverse_dates":
        narratives[0] = (
            "Tại ngày 31 tháng 12 năm 2024, tỷ lệ nợ xấu là 1,57% "
            "(tại ngày 31 tháng 12 năm 2025 là 1,68%)."
        )
    elif mutation == "same_date":
        narratives[0] = (
            "Tại ngày 31 tháng 12 năm 2025, tỷ lệ nợ xấu là 1,68% "
            "(tại ngày 31 tháng 12 năm 2025 là 1,68%)."
        )
    elif mutation == "one_table_date":
        page["sections"][0]["tables"][0]["title_exact"] = "Tại ngày 31 tháng 12 năm 2025"
    elif mutation == "third_table":
        page["sections"][0]["tables"].append(deepcopy(page["sections"][0]["tables"][1]))
    elif mutation == "header_mismatch":
        page["sections"][0]["tables"][1]["columns"][1]["header_path_exact"] = [
            "Phạm vi khác",
            "Triệu VND",
        ]
    elif mutation == "arithmetic_mismatch":
        page["sections"][0]["tables"][1]["rows"][-1]["values_exact"][1] = "39"
    else:
        narratives.append("Đơn vị được thành lập ngày 1 tháng 1 năm 2025.")

    assert _project_period_pair(page) is None


def test_incomplete_four_of_five_quality_rows_stitch_exact_adjacent_continuation() -> None:
    first_id = "gfpstorev1:json:" + "a" * 64
    second_id = "gfpstorev1:json:" + "b" * 64
    first = _period_pair_page([])
    first_table = first["sections"][0]["tables"][0]
    first["sections"][0]["tables"] = [first_table]
    first["sections"][0]["title_exact"] = "Phân tích chất lượng nợ cho vay"
    first_table["title_exact"] = "Phân tích chất lượng nợ cho vay"
    first_table["columns"] = [
        {"header_path_exact": ["Cuối kỳ"], "value_kind": "MONEY"},
        {"header_path_exact": ["Đầu kỳ"], "value_kind": "MONEY"},
    ]
    first_table["rows"] = first_table["rows"][:4]
    first_table["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    second = deepcopy(first)
    second["sections"][0]["title_exact"] = "Thuyết minh báo cáo tài chính (tiếp theo)"
    second_table = second["sections"][0]["tables"][0]
    second_table["title_exact"] = None
    second_table["columns"] = [
        {"header_path_exact": [None], "value_kind": "MONEY"},
        {"header_path_exact": [None], "value_kind": "MONEY"},
    ]
    second_table["rows"] = [
        {
            "hierarchy_path_exact": ["Nợ có khả năng mất vốn"],
            "label_exact": "Nợ có khả năng mất vốn",
            "row_kind": "ITEM",
            "values_exact": ["2", "2"],
        },
        {
            "hierarchy_path_exact": [None],
            "label_exact": None,
            "row_kind": "TOTAL",
            "values_exact": ["130", "50"],
        },
    ]
    second_table["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"
    compiled = _compiled_specs()
    base = _evaluate(first)
    assert base["status"] != READY
    assert any(
        reason.startswith("REQUIRED_ROLE_POOL_COUNT_BELOW_MINIMUM:4:5")
        for reason in base["reasons"]
    )
    region = {
        "context_pages": [{"page_json_version_id": second_id, "physical_page": 33}],
        "page_json_version_id": first_id,
        "physical_page": 32,
        "section_id": "s1",
        "source_logical_name": "bank/report.pdf",
        "table_id": "t1",
    }
    pages = {first_id: {"page_json": first}, second_id: {"page_json": second}}

    stitched = runner._adjacent_continuation_candidate_v1(
        base_candidate=base,
        region=region,
        page_by_version=pages,
        compiled_specs=compiled,
    )

    assert stitched is not None and stitched["status"] == READY
    assert [mapping["report_norm_id"] for mapping in stitched["mappings"]] == [
        746,
        747,
        748,
        749,
        750,
        751,
    ]
    region["context_pages"][0]["physical_page"] = 34
    assert (
        runner._adjacent_continuation_candidate_v1(
            base_candidate=base,
            region=region,
            page_by_version=pages,
            compiled_specs=compiled,
        )
        is None
    )
