from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.evaluation.gemini_json_stacked_period_accounting_family_v1 import (
    READY,
    UNRESOLVED,
    GeminiJsonStackedPeriodAccountingFamilyV1Error,
    _date_token,
    evaluate_gemini_json_stacked_period_family_region_v1,
    select_gemini_json_stacked_period_ready_candidate_v1,
)

ROOT = Path(__file__).resolve().parents[2]


def _json(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict:
    return compile_gemini_json_flat_family_specs_v1(
        _json("tm-derivative-financial-instruments-topology-v1.json"),
        _json("tm-derivative-financial-instruments-evaluation-v1.json"),
        _json("tm-derivative-financial-instruments-schema-binding-v1.json"),
    )


def _columns(period: str) -> list[dict]:
    return [
        {
            "header_path_exact": ["Tổng giá trị hợp đồng", period, "Triệu đồng"],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": ["Giá trị ghi sổ kế toán", period, "Tài sản", "Triệu đồng"],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": ["Giá trị ghi sổ kế toán", period, "Công nợ", "Triệu đồng"],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": ["Giá trị ghi sổ kế toán", period, "Giá trị thuần", "Triệu đồng"],
            "value_kind": "MONEY",
        },
    ]


def _period_table(period: str, *, contract_total: str = "35") -> dict:
    return {
        "columns": _columns(period),
        "continuation": "NONE",
        "rows": [
            {
                "hierarchy_path_exact": ["Công cụ tài chính phái sinh tiền tệ"],
                "label_exact": "Công cụ tài chính phái sinh tiền tệ",
                "row_kind": "GROUP",
                "values_exact": [None, None, None, None],
            },
            {
                "hierarchy_path_exact": [
                    "Công cụ tài chính phái sinh tiền tệ",
                    "Giao dịch kỳ hạn tiền tệ",
                ],
                "label_exact": "Giao dịch kỳ hạn tiền tệ",
                "row_kind": "ITEM",
                "values_exact": ["10", "2", "(1)", "1"],
            },
            {
                "hierarchy_path_exact": [
                    "Công cụ tài chính phái sinh tiền tệ",
                    "Giao dịch hoán đổi tiền tệ",
                ],
                "label_exact": "Giao dịch hoán đổi tiền tệ",
                "row_kind": "ITEM",
                "values_exact": ["20", None, None, None],
            },
            {
                "hierarchy_path_exact": ["Công cụ tài chính phái sinh khác"],
                "label_exact": "Công cụ tài chính phái sinh khác",
                "row_kind": "GROUP",
                "values_exact": [None, None, None, None],
            },
            {
                "hierarchy_path_exact": [
                    "Công cụ tài chính phái sinh khác",
                    "Giao dịch hoán đổi lãi suất",
                ],
                "label_exact": "Giao dịch hoán đổi lãi suất",
                "row_kind": "ITEM",
                "values_exact": ["5", "1", None, "1"],
            },
            {
                "hierarchy_path_exact": [None],
                "label_exact": None,
                "row_kind": "TOTAL",
                "values_exact": [contract_total, "3", "(1)", "2"],
            },
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }


def _separate_period_page() -> dict:
    return {
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [
                    _period_table("Tại ngày 31 tháng 12 năm 2025"),
                    _period_table("Tại ngày 31 tháng 12 năm 2024"),
                ],
                "title_exact": (
                    "CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÁC TÀI SẢN/CÔNG NỢ TÀI CHÍNH KHÁC"
                ),
            }
        ]
    }


def _evaluate(page: dict, refs: list[tuple[str, str]] | None = None) -> dict:
    return evaluate_gemini_json_stacked_period_family_region_v1(
        page_json=page,
        page_json_version_id="gfpstorev1:json:" + "a" * 64,
        physical_page=7,
        table_refs=refs or [("s1", "t1"), ("s1", "t2")],
        compiled_specs=_compiled(),
    )


def test_separate_period_tables_close_exactly_and_map_period_lanes() -> None:
    candidate = _evaluate(_separate_period_page())
    assert candidate["status"] == READY
    assert candidate["reasons"] == []
    assert len(candidate["mappings"]) == 12
    keys = {
        (item["period_role"], item["source_lane_role"], item["role"])
        for item in candidate["mappings"]
    }
    assert ("CURRENT_PERIOD", "CONTRACT_VALUE", "FORWARD_CURRENCY") in keys
    assert ("COMPARATIVE_PERIOD", "LIABILITY_CARRYING_VALUE", "FORWARD_CURRENCY") in keys
    roots = [
        equation
        for equation in candidate["closure_receipt"]["equations"]
        if equation.get("result_role") == "DERIVATIVE_FINANCIAL_INSTRUMENTS"
    ]
    assert len(roots) == 2


def test_period_can_be_carried_by_two_section_narratives() -> None:
    page = _separate_period_page()
    tables = page["sections"][0].pop("tables")
    page["sections"] = [
        {
            **page["sections"][0],
            "narratives_exact": ["Chi tiết tại ngày 31 tháng 12 năm 2025 như sau:"],
            "tables": [
                {
                    **tables[0],
                    "columns": [
                        {
                            **column,
                            "header_path_exact": [
                                value
                                for value in column["header_path_exact"]
                                if "2025" not in value
                            ],
                        }
                        for column in tables[0]["columns"]
                    ],
                }
            ],
        },
        {
            "content_kind": "FINANCIAL_NOTE",
            "narratives_exact": ["Chi tiết tại ngày 31 tháng 12 năm 2024 như sau:"],
            "statement_type": "NOT_APPLICABLE",
            "tables": [
                {
                    **tables[1],
                    "columns": [
                        {
                            **column,
                            "header_path_exact": [
                                value
                                for value in column["header_path_exact"]
                                if "2024" not in value
                            ],
                        }
                        for column in tables[1]["columns"]
                    ],
                }
            ],
            "title_exact": None,
        },
    ]
    candidate = _evaluate(page, [("s1", "t1"), ("s2", "t1")])
    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 12


def test_table_period_overrides_broader_reporting_date_in_section_title() -> None:
    page = _separate_period_page()
    page["sections"][0]["title_exact"] = (
        "THUYẾT MINH BÁO CÁO TÀI CHÍNH QUÝ II NĂM 2025 — CÔNG CỤ TÀI CHÍNH PHÁI SINH"
    )
    for table, period in zip(
        page["sections"][0]["tables"],
        ("Ngày 30 tháng 6 năm 2025", "Ngày 31 tháng 12 năm 2024"),
        strict=True,
    ):
        table["title_exact"] = period
        table["columns"] = [
            {
                **column,
                "header_path_exact": [
                    value
                    for value in column["header_path_exact"]
                    if "2025" not in value and "2024" not in value
                ],
            }
            for column in table["columns"]
        ]
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    assert {mapping["period_role"] for mapping in candidate["mappings"]} == {
        "CURRENT_PERIOD",
        "COMPARATIVE_PERIOD",
    }


def test_slash_date_preserves_exact_day_and_month_after_search_normalization() -> None:
    assert _date_token("Tại 31/03/2025")[0].isoformat() == "2025-03-31"
    assert _date_token("Tại 30/06/2026")[0].isoformat() == "2026-06-30"


def test_two_undated_tables_bind_ordered_period_narratives_in_one_section() -> None:
    page = _separate_period_page()
    section = page["sections"][0]
    section["narratives_exact"] = [
        "Chi tiết tại ngày 31 tháng 3 năm 2025 như sau:",
        "Chi tiết tại ngày 31 tháng 12 năm 2024 như sau:",
    ]
    for table in section["tables"]:
        table["columns"] = [
            {
                **column,
                "header_path_exact": [
                    value
                    for value in column["header_path_exact"]
                    if "2025" not in value and "2024" not in value
                ],
            }
            for column in table["columns"]
        ]
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    assert {mapping["period_role"] for mapping in candidate["mappings"]} == {
        "CURRENT_PERIOD",
        "COMPARATIVE_PERIOD",
    }


def test_horizontal_period_columns_sign_split_only_visible_signed_values() -> None:
    rows = [
        {
            "hierarchy_path_exact": ["Công cụ tài chính phái sinh tiền tệ"],
            "label_exact": "Công cụ tài chính phái sinh tiền tệ",
            "row_kind": "GROUP",
            "values_exact": [None, None, None, None],
        },
        {
            "hierarchy_path_exact": [
                "Công cụ tài chính phái sinh tiền tệ",
                "Hợp đồng kỳ hạn tiền tệ",
            ],
            "label_exact": "Hợp đồng kỳ hạn tiền tệ",
            "row_kind": "ITEM",
            "values_exact": ["10", "2", "12", "(3)"],
        },
        {
            "hierarchy_path_exact": ["Công cụ tài chính phái sinh tiền tệ", None],
            "label_exact": None,
            "row_kind": "TOTAL",
            "values_exact": ["10", "2", "12", "(3)"],
        },
    ]
    page = {
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [
                    {
                        "columns": [
                            {
                                "header_path_exact": ["31/12/2025", "Giá trị hợp đồng"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": [
                                    "31/12/2025",
                                    "Giá trị ghi sổ",
                                    "Tài sản/(Công nợ)",
                                ],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": ["31/12/2024", "Giá trị hợp đồng"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": [
                                    "31/12/2024",
                                    "Giá trị ghi sổ",
                                    "Tài sản/(Công nợ)",
                                ],
                                "value_kind": "MONEY",
                            },
                        ],
                        "continuation": "NONE",
                        "rows": rows,
                        "title_exact": None,
                        "unit_exact": "Triệu VND",
                    }
                ],
                "title_exact": "CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH",
            }
        ]
    }
    candidate = _evaluate(page, [("s1", "t1")])
    assert candidate["status"] == READY
    by_period = {
        item["period_role"]: item["report_norm_id"]
        for item in candidate["mappings"]
        if item["source_lane_role"] == "SIGNED_CARRYING_VALUE"
    }
    assert by_period == {"CURRENT_PERIOD": 662, "COMPARATIVE_PERIOD": 704}


def _relative_stacked_page(current_label: str, comparative_label: str) -> dict:
    current = _period_table("31/12/2025")
    comparative = _period_table("31/12/2024")
    columns = [
        {
            **column,
            "header_path_exact": [
                value
                for value in column["header_path_exact"]
                if "2025" not in value and "2024" not in value
            ],
        }
        for column in current["columns"]
    ]

    def marker(label: str) -> dict:
        return {
            "hierarchy_path_exact": [label],
            "label_exact": label,
            "row_kind": "HEADER",
            "values_exact": [None for _column in columns],
        }

    return {
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [
                    {
                        **current,
                        "columns": columns,
                        "rows": [
                            marker(current_label),
                            *current["rows"],
                            marker(comparative_label),
                            *comparative["rows"],
                        ],
                    }
                ],
                "title_exact": "CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH",
            }
        ]
    }


@pytest.mark.parametrize(
    ("current_label", "comparative_label"),
    [
        ("Tại ngày cuối kỳ", "Tại ngày đầu kỳ"),
        ("Số cuối quý", "Số đầu năm"),
        ("Số cuối năm", "Số đầu năm"),
        ("Số cuối năm 2025", "Số đầu năm"),
    ],
)
def test_stacked_relative_balance_period_markers_are_bounded_roles(
    current_label: str, comparative_label: str
) -> None:
    candidate = _evaluate(
        _relative_stacked_page(current_label, comparative_label),
        [("s1", "t1")],
    )
    assert candidate["status"] == READY
    assert {mapping["period_role"] for mapping in candidate["mappings"]} == {
        "CURRENT_PERIOD",
        "COMPARATIVE_PERIOD",
    }


def test_list_number_before_relative_period_is_only_presentation() -> None:
    candidate = _evaluate(
        _relative_stacked_page("1 Tại ngày cuối kỳ", "Tại ngày đầu kỳ"),
        [("s1", "t1")],
    )
    assert candidate["status"] == READY
    assert candidate["reasons"] == []


def test_labeled_period_subtotal_may_print_only_a_subset_of_exact_lanes() -> None:
    page = _relative_stacked_page("Tại ngày cuối kỳ", "Tại ngày đầu kỳ")
    rows = page["sections"][0]["tables"][0]["rows"]
    rows.pop(13)
    rows.pop(6)
    for marker in (rows[0], rows[6]):
        marker["row_kind"] = "SUBTOTAL"
        marker["values_exact"] = [None, "3", "(1)", None]
    candidate = _evaluate(page, [("s1", "t1")])
    assert candidate["status"] == READY
    receipts = [
        receipt
        for receipt in candidate["closure_receipt"]["equations"]
        if receipt.get("equation_kind") == "VISIBLE_PARTIAL_PERIOD_LANE_TOTAL"
    ]
    assert len(receipts) == 2
    assert {tuple(receipt["visible_lane_roles"]) for receipt in receipts} == {
        ("ASSET_CARRYING_VALUE", "LIABILITY_CARRYING_VALUE")
    }


def test_relative_period_marker_conflict_fails_closed() -> None:
    one_role = _evaluate(
        _relative_stacked_page("Tại ngày cuối kỳ", "Số cuối kỳ"),
        [("s1", "t1")],
    )
    assert one_role["status"] == UNRESOLVED
    assert (
        "Gemini JSON stacked-period region does not expose exactly two periods"
        in one_role["reasons"]
    )

    reversed_dates = _evaluate(
        _relative_stacked_page(
            "Tại ngày cuối kỳ 31/12/2024",
            "Tại ngày đầu kỳ 31/12/2025",
        ),
        [("s1", "t1")],
    )
    assert reversed_dates["status"] == UNRESOLVED
    assert "Gemini JSON stacked-period period evidence conflicts" in reversed_dates["reasons"]


def _horizontal_date_only_page() -> dict:
    return {
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
                        "rows": [
                            {
                                "hierarchy_path_exact": ["Công cụ tài chính phái sinh tiền tệ"],
                                "label_exact": "Công cụ tài chính phái sinh tiền tệ",
                                "row_kind": "GROUP",
                                "values_exact": [None, None],
                            },
                            {
                                "hierarchy_path_exact": [
                                    "Công cụ tài chính phái sinh tiền tệ",
                                    "Hợp đồng kỳ hạn tiền tệ",
                                ],
                                "label_exact": "Hợp đồng kỳ hạn tiền tệ",
                                "row_kind": "ITEM",
                                "values_exact": ["2", "(3)"],
                            },
                            {
                                "hierarchy_path_exact": [None],
                                "label_exact": None,
                                "row_kind": "TOTAL",
                                "values_exact": ["2", "(3)"],
                            },
                        ],
                        "title_exact": None,
                        "unit_exact": "Triệu đồng",
                    }
                ],
                "title_exact": "CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH",
            }
        ]
    }


def test_horizontal_date_only_columns_use_the_unique_declared_single_lane() -> None:
    candidate = _evaluate(_horizontal_date_only_page(), [("s1", "t1")])
    assert candidate["status"] == READY
    assert {
        (mapping["period_role"], mapping["source_lane_role"]) for mapping in candidate["mappings"]
    } == {
        ("CURRENT_PERIOD", "SIGNED_CARRYING_VALUE"),
        ("COMPARATIVE_PERIOD", "SIGNED_CARRYING_VALUE"),
    }


def test_horizontal_date_only_columns_fail_when_single_lane_is_not_unique() -> None:
    compiled = _compiled()
    compiled["layout"]["allowed_lane_role_sequences"].append(["CONTRACT_VALUE"])
    candidate = evaluate_gemini_json_stacked_period_family_region_v1(
        page_json=_horizontal_date_only_page(),
        page_json_version_id="gfpstorev1:json:" + "a" * 64,
        physical_page=7,
        table_refs=[("s1", "t1")],
        compiled_specs=compiled,
    )
    assert candidate["status"] == UNRESOLVED
    assert any("column lane is unresolved" in reason for reason in candidate["reasons"])


def test_lane_sequence_and_bare_year_are_not_silently_reinterpreted() -> None:
    page = _separate_period_page()
    for table in page["sections"][0]["tables"]:
        table["columns"][0], table["columns"][1] = table["columns"][1], table["columns"][0]
        for row in table["rows"]:
            row["values_exact"][0], row["values_exact"][1] = (
                row["values_exact"][1],
                row["values_exact"][0],
            )
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert any("lane sequence is not declared" in reason for reason in candidate["reasons"])

    year = _date_token("Năm 2025")
    assert year is not None
    assert year.period_end is None
    assert year.period_year == 2025


def _with_row_ordinal_control(page: dict) -> dict:
    for table in page["sections"][0]["tables"]:
        table["columns"].insert(
            0,
            {
                "header_path_exact": [None],
                "value_kind": "TEXT",
            },
        )
        for row in table["rows"]:
            marker = None
            if row["label_exact"] == "Công cụ tài chính phái sinh tiền tệ":
                marker = "1"
            elif row["label_exact"] == "Công cụ tài chính phái sinh khác":
                marker = "2"
            row["values_exact"].insert(0, marker)
    return page


def test_non_money_row_ordinal_column_is_preserved_as_source_only_control() -> None:
    page = _with_row_ordinal_control(_separate_period_page())
    for table in page["sections"][0]["tables"]:
        for row in table["rows"]:
            if row["values_exact"][0] is not None:
                row["row_kind"] = "ITEM"
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    controls = [
        column
        for column in candidate["closure_receipt"]["column_axis"]
        if column["lane_role"] == "SOURCE_ONLY_CONTROL"
    ]
    assert len(controls) == 2
    assert {column["column_ordinal"] for column in controls} == {1}
    assert all(mapping["values"][0]["column_ordinal"] >= 2 for mapping in candidate["mappings"])


def test_non_money_content_column_cannot_be_discarded_as_an_ordinal() -> None:
    page = _with_row_ordinal_control(_separate_period_page())
    page["sections"][0]["tables"][0]["rows"][1]["values_exact"][0] = "narrative"
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert any(
        "non-money lane is not an ordinal control" in reason for reason in candidate["reasons"]
    )


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (
            lambda page: page["sections"][0]["tables"][0]["rows"][-1]["values_exact"].__setitem__(
                0, "36"
            ),
            "VISIBLE_FAMILY_TOTAL_NOT_EXACT_DIRECT_FRONTIER:CURRENT_PERIOD:s1:t1:r6",
        ),
        (
            lambda page: page["sections"][0]["tables"][0]["rows"].insert(
                -1,
                {
                    "hierarchy_path_exact": ["Không khai báo"],
                    "label_exact": "Không khai báo",
                    "row_kind": "ITEM",
                    "values_exact": ["1", None, None, None],
                },
            ),
            "UNMATCHED_VISIBLE_NUMERIC_ROW:s1:t1:6",
        ),
        (
            lambda page: page["sections"][0]["tables"][0]["rows"].insert(
                2,
                copy.deepcopy(page["sections"][0]["tables"][0]["rows"][1]),
            ),
            "ROLE_OCCURRENCE_COUNT_ABOVE_ONE:CURRENT_PERIOD:FORWARD_CURRENCY",
        ),
    ],
)
def test_partial_duplicate_unmatched_or_nonexact_frontiers_fail_closed(mutate, reason: str) -> None:
    page = _separate_period_page()
    mutate(page)
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert reason in candidate["reasons"]


def test_period_or_spec_drift_fails_closed() -> None:
    page = _separate_period_page()
    for table in page["sections"][0]["tables"]:
        for column in table["columns"]:
            column["header_path_exact"] = [
                value.replace("2024", "2025") for value in column["header_path_exact"]
            ]
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert (
        "Gemini JSON stacked-period region does not expose exactly two periods"
        in candidate["reasons"]
    )
    evaluation = _json("tm-derivative-financial-instruments-evaluation-v1.json")
    evaluation["closure_policy"] = "LOOSE"
    with pytest.raises(GeminiJsonStackedPeriodAccountingFamilyV1Error):
        compile_gemini_json_flat_family_specs_v1(
            _json("tm-derivative-financial-instruments-topology-v1.json"),
            evaluation,
            _json("tm-derivative-financial-instruments-schema-binding-v1.json"),
        )


def test_compensating_row_level_net_errors_fail_even_when_family_total_closes() -> None:
    page = _separate_period_page()
    first = page["sections"][0]["tables"][0]["rows"][1]["values_exact"]
    second = page["sections"][0]["tables"][0]["rows"][2]["values_exact"]
    # Preserve the visible family total by compensating the two child NET
    # cells.  Each row-local accounting relation must still reject the JSON.
    first[3] = "2"
    second[3] = "(1)"
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert any(
        reason.startswith("VISIBLE_LANE_EQUATION_NOT_EXACT:CURRENT_PERIOD:s1:t1:r")
        for reason in candidate["reasons"]
    )


def test_zero_component_can_match_equivalent_declared_lane_equations() -> None:
    page = _separate_period_page()
    row = page["sections"][0]["tables"][0]["rows"][4]
    row["values_exact"] = ["5", "1", "0", "1"]
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    receipts = [
        receipt
        for receipt in candidate["closure_receipt"]["equations"]
        if receipt.get("row_id") == "s1:t1:r5"
    ]
    assert len(receipts) == 1
    assert len(receipts[0]["matching_alternatives"]) == 2


def test_exhaustive_visible_frontier_can_close_without_a_printed_family_total() -> None:
    page = _separate_period_page()
    for table in page["sections"][0]["tables"]:
        table["rows"].pop()
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    roots = [
        receipt
        for receipt in candidate["closure_receipt"]["equations"]
        if receipt.get("result_role") == "DERIVATIVE_FINANCIAL_INSTRUMENTS"
    ]
    assert {receipt["result_carrier"] for receipt in roots} == {
        "NOT_PRINTED_EXHAUSTIVE_VISIBLE_DIRECT_FRONTIER"
    }


def test_ordered_declared_owner_recovers_flattened_noisy_hierarchy() -> None:
    page = _separate_period_page()
    for table in page["sections"][0]["tables"]:
        for row in table["rows"]:
            if row["label_exact"] in {
                "Giao dịch kỳ hạn tiền tệ",
                "Giao dịch hoán đổi tiền tệ",
            }:
                row["hierarchy_path_exact"] = [
                    "Công cụ tài chính phái sinh tiền tệ Bài khoản mục con " + row["label_exact"]
                ]
            elif row["label_exact"] == "Giao dịch hoán đổi lãi suất":
                row["hierarchy_path_exact"] = [
                    "Công cụ tài chính phái sinh khác 运行时 " + row["label_exact"]
                ]
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    inferred = [
        binding
        for equation in candidate["closure_receipt"]["equations"]
        for binding in equation.get("component_bindings", [])
        if binding["owner_binding_kind"] == "ORDERED_NEAREST_PRECEDING_DECLARED_STRUCTURAL_GROUP"
    ]
    assert {binding["role"] for binding in inferred} == {
        "CURRENCY_SWAP",
        "FORWARD_CURRENCY",
        "INTEREST_RATE_SWAP",
    }


def test_exact_foreign_exchange_and_abbreviated_interest_group_aliases() -> None:
    page = _separate_period_page()
    for table in page["sections"][0]["tables"]:
        currency_swap = table["rows"][2]
        currency_swap["label_exact"] = "Giao dịch hoán đổi ngoại tệ"
        currency_swap["hierarchy_path_exact"][-1] = currency_swap["label_exact"]
        interest_group = table["rows"][3]
        interest_group["label_exact"] = "Công cụ TC phái sinh lãi suất"
        interest_group["hierarchy_path_exact"] = [interest_group["label_exact"]]
        table["rows"][4]["hierarchy_path_exact"][0] = interest_group["label_exact"]
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    assert candidate["reasons"] == []


def test_period_labeled_subtotal_is_a_family_total_not_an_unmatched_row() -> None:
    page = _separate_period_page()
    for table, period in zip(
        page["sections"][0]["tables"],
        ("Tại ngày 31/12/2025", "Tại ngày 31/12/2024"),
        strict=True,
    ):
        total = table["rows"][-1]
        total["hierarchy_path_exact"] = [period]
        total["label_exact"] = period
        total["row_kind"] = "SUBTOTAL"
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    assert not any(
        reason.startswith("UNMATCHED_VISIBLE_NUMERIC_ROW") for reason in candidate["reasons"]
    )


def test_money_parser_ignores_outer_whitespace_but_preserves_raw_source_text() -> None:
    page = _separate_period_page()
    page["sections"][0]["tables"][0]["rows"][1]["values_exact"][0] = " 10 "
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    mapping = next(
        mapping
        for mapping in candidate["mappings"]
        if mapping["period_role"] == "CURRENT_PERIOD"
        and mapping["role"] == "FORWARD_CURRENCY"
        and mapping["source_lane_role"] == "CONTRACT_VALUE"
    )
    assert mapping["values"][0]["coefficient"] == 10
    assert mapping["values"][0]["source_text"] == " 10 "


def test_labeled_total_is_root_while_separate_net_row_is_presentation_only() -> None:
    page = _separate_period_page()
    for table in page["sections"][0]["tables"]:
        total = table["rows"][-1]
        total["label_exact"] = "Tổng cộng"
        total["hierarchy_path_exact"] = ["Tổng cộng"]
        table["rows"].append(
            {
                "hierarchy_path_exact": ["Số thuần"],
                "label_exact": "Số thuần",
                "row_kind": "TOTAL",
                "values_exact": [None, None, None, "2"],
            }
        )
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    assert all(
        receipt.get("result_carrier") != "NOT_PRINTED_EXHAUSTIVE_VISIBLE_DIRECT_FRONTIER"
        for receipt in candidate["closure_receipt"]["equations"]
        if receipt.get("result_role") == "DERIVATIVE_FINANCIAL_INSTRUMENTS"
    )


def test_labeled_subtotal_is_visible_root_before_separate_net_presentation() -> None:
    page = _separate_period_page()
    for table in page["sections"][0]["tables"]:
        total = table["rows"][-1]
        total["label_exact"] = "Tổng cộng"
        total["hierarchy_path_exact"] = ["Công cụ tài chính phái sinh", "Tổng cộng"]
        total["row_kind"] = "SUBTOTAL"
        table["rows"].append(
            {
                "hierarchy_path_exact": ["Công cụ tài chính phái sinh", "Số thuần"],
                "label_exact": "Số thuần",
                "row_kind": "SUBTOTAL",
                "values_exact": [None, None, None, "2"],
            }
        )
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    assert candidate["reasons"] == []


def test_net_magnitude_may_be_presented_on_its_exact_asset_or_liability_side() -> None:
    page = _separate_period_page()
    for table in page["sections"][0]["tables"]:
        total = table["rows"][-1]
        total["label_exact"] = "Tổng cộng"
        total["hierarchy_path_exact"] = ["Tổng cộng"]
        table["rows"].append(
            {
                "hierarchy_path_exact": ["Giá trị thuần"],
                "label_exact": "Giá trị thuần",
                "row_kind": "TOTAL",
                "values_exact": [None, "2", None, None],
            }
        )
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    receipts = [
        receipt
        for receipt in candidate["closure_receipt"]["equations"]
        if receipt.get("equation_kind") == "VISIBLE_NET_PRESENTATION_EQUATION"
    ]
    assert len(receipts) == 2
    assert {receipt["matching_alternative"]["binding_kind"] for receipt in receipts} == {
        "ASSET_LIABILITY_SIDE_PLACED_MAGNITUDE"
    }


def test_zero_component_preserves_all_equivalent_net_presentation_equations() -> None:
    page = _separate_period_page()
    for table in page["sections"][0]["tables"]:
        table["rows"][1]["values_exact"] = ["10", "2", None, "2"]
        total = table["rows"][-1]
        total["label_exact"] = "Tổng cộng"
        total["hierarchy_path_exact"] = ["Tổng cộng"]
        total["values_exact"] = ["35", "3", None, "3"]
        table["rows"].append(
            {
                "hierarchy_path_exact": ["Số thuần"],
                "label_exact": "Số thuần",
                "row_kind": "TOTAL",
                "values_exact": [None, "3", None, None],
            }
        )
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    receipts = [
        receipt
        for receipt in candidate["closure_receipt"]["equations"]
        if receipt.get("equation_kind") == "VISIBLE_NET_PRESENTATION_EQUATION"
    ]
    assert len(receipts) == 2
    assert all(len(receipt["matching_alternatives"]) == 2 for receipt in receipts)
    assert {
        alternative["computed_signed_value"]
        for receipt in receipts
        for alternative in receipt["matching_alternatives"]
    } == {3}


def test_negative_net_may_retain_its_visible_sign_on_the_liability_side() -> None:
    page = _separate_period_page()
    for table in page["sections"][0]["tables"]:
        first = table["rows"][1]["values_exact"]
        second = table["rows"][2]["values_exact"]
        other = table["rows"][4]["values_exact"]
        total = table["rows"][-1]
        first[1:] = [None, "(2)", "(2)"]
        second[1:] = [None, None, None]
        other[1:] = [None, None, None]
        total["values_exact"][1:] = [None, "(2)", "(2)"]
        total["label_exact"] = "Tổng cộng"
        total["hierarchy_path_exact"] = ["Tổng cộng"]
        table["rows"].append(
            {
                "hierarchy_path_exact": ["Số thuần"],
                "label_exact": "Số thuần",
                "row_kind": "TOTAL",
                "values_exact": [None, None, "(2)", None],
            }
        )
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    receipts = [
        receipt
        for receipt in candidate["closure_receipt"]["equations"]
        if receipt.get("equation_kind") == "VISIBLE_NET_PRESENTATION_EQUATION"
    ]
    assert len(receipts) == 2
    assert {receipt["matching_alternative"]["binding_kind"] for receipt in receipts} == {
        "ASSET_LIABILITY_SIDE_PLACED_SIGNED_VALUE"
    }


@pytest.mark.parametrize(
    "presentation_values",
    [
        [None, None, "2", None],  # positive net printed on the liability side
        [None, "3", None, None],  # wrong magnitude on the otherwise correct side
    ],
)
def test_side_placed_net_rejects_wrong_side_or_nonexact_magnitude(
    presentation_values: list[str | None],
) -> None:
    page = _separate_period_page()
    for table in page["sections"][0]["tables"]:
        total = table["rows"][-1]
        total["label_exact"] = "Tổng cộng"
        total["hierarchy_path_exact"] = ["Tổng cộng"]
        table["rows"].append(
            {
                "hierarchy_path_exact": ["Giá trị thuần"],
                "label_exact": "Giá trị thuần",
                "row_kind": "TOTAL",
                "values_exact": presentation_values,
            }
        )
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert any(
        reason.startswith("PRESENTATION_NET_ROW_NOT_ONE_EXACT_LANE_EQUATION:")
        for reason in candidate["reasons"]
    )


def test_selector_and_sweep_replay_do_not_hide_ambiguity() -> None:
    candidate = _evaluate(_separate_period_page())
    richer = copy.deepcopy(candidate)
    richer["candidate_id"] = "gjfafcv1:candidate:" + "b" * 64
    assert (
        select_gemini_json_stacked_period_ready_candidate_v1(
            [candidate], compiled_specs=_compiled()
        )
        == candidate
    )
    assert (
        select_gemini_json_stacked_period_ready_candidate_v1(
            [candidate, richer], compiled_specs=_compiled()
        )
        is None
    )
    trial = {
        "candidate_count": 1,
        "candidates": [candidate],
        "document_ordinal": 1,
        "mappings": candidate["mappings"],
        "reasons": [],
        "selected_candidate_id": candidate["candidate_id"],
        "source_logical_name": "one.pdf",
        "source_sha256": "c" * 64,
        "status": READY,
    }
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "d" * 64,
        topology_spec=_json("tm-derivative-financial-instruments-topology-v1.json"),
        evaluation_spec=_json("tm-derivative-financial-instruments-evaluation-v1.json"),
        schema_binding_spec=_json("tm-derivative-financial-instruments-schema-binding-v1.json"),
        trials=[trial],
    )
    assert validate_gemini_json_flat_family_sweep_v1(sweep) == sweep
    forged = copy.deepcopy(sweep)
    forged["trials"][0]["mappings"][0]["values"][0]["coefficient"] += 1
    with pytest.raises(ValueError):
        validate_gemini_json_flat_family_sweep_v1(forged)
