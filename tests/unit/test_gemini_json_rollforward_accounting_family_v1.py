from __future__ import annotations

import json
from pathlib import Path

from bctc_ai.evaluation.gemini_json_rollforward_accounting_family_v1 import (
    QUERY_RECEIPT_FORMAT_VERSION,
    READY,
    UNRESOLVED,
    compile_gemini_json_rollforward_family_specs_v1,
    evaluate_gemini_json_rollforward_family_cluster_v1,
    solve_one_unknown_rollforward_lane_v1,
)

ROOT = Path(__file__).resolve().parents[2]
VERSION_A = "gfpstorev1:json:" + "a" * 64
VERSION_B = "gfpstorev1:json:" + "b" * 64


def _json(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_text(encoding="utf-8"))


def _compiled() -> dict:
    return compile_gemini_json_rollforward_family_specs_v1(
        _json("tm-provision-movement-rollforward-topology-v1.json"),
        _json("tm-provision-movement-rollforward-evaluation-v1.json"),
        _json("tm-provision-movement-rollforward-schema-binding-v1.json"),
    )


def _cell(value: int | None) -> dict:
    return {
        "coefficient": value,
        "source_text": None if value is None else str(value),
        "state": "UNKNOWN_BLANK" if value is None else "RAW_SIGNED_INTEGER",
    }


def _movement_specs() -> list[dict]:
    return _compiled()["layout"]["movement_roles"]


def _period_table(
    period: str,
    *,
    margin_provision: str | None = "20",
    margin_use: str | None = "(10)",
    unit: str | None = "Triệu đồng",
) -> dict:
    return {
        "columns": [
            {
                "header_path_exact": ["Cho vay khách hàng", "Dự phòng chung"],
                "value_kind": "MONEY",
            },
            {
                "header_path_exact": ["Cho vay khách hàng", "Dự phòng cụ thể"],
                "value_kind": "MONEY",
            },
            {
                "header_path_exact": [
                    "Cho vay khách hàng",
                    "Dự phòng cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
                ],
                "value_kind": "MONEY",
            },
        ],
        "continuation": "NONE",
        "rows": [
            {
                "hierarchy_path_exact": ["Số dư đầu kỳ"],
                "label_exact": "Số dư đầu kỳ",
                "row_kind": "ITEM",
                "values_exact": ["100", "200", "100"],
            },
            {
                "hierarchy_path_exact": ["Trích lập dự phòng trong kỳ"],
                "label_exact": "Trích lập dự phòng trong kỳ",
                "row_kind": "ITEM",
                "values_exact": ["20", "30", margin_provision],
            },
            {
                "hierarchy_path_exact": ["Sử dụng dự phòng trong kỳ"],
                "label_exact": "Sử dụng dự phòng trong kỳ",
                "row_kind": "ITEM",
                "values_exact": ["(10)", "(15)", margin_use],
            },
            {
                "hierarchy_path_exact": ["Số dư cuối kỳ"],
                "label_exact": "Số dư cuối kỳ",
                "row_kind": "TOTAL",
                "values_exact": ["110", "215", "110"],
            },
        ],
        "title_exact": period,
        "unit_exact": unit,
    }


def _page(*tables: dict) -> dict:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": ["Biến động số dư dự phòng rủi ro cho vay khách hàng như sau:"],
                "statement_type": "NOT_APPLICABLE",
                "tables": list(tables),
                "title_exact": "Dự phòng rủi ro cho vay khách hàng",
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _lane_table(title: str | None = None) -> dict:
    return {
        "columns": [
            {"header_path_exact": ["31/12/2025", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["31/12/2024", "Triệu đồng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            {
                "hierarchy_path_exact": ["Số dư đầu kỳ"],
                "label_exact": "Số dư đầu kỳ",
                "row_kind": "ITEM",
                "values_exact": ["100", "90"],
            },
            {
                "hierarchy_path_exact": ["Trích lập"],
                "label_exact": "Trích lập",
                "row_kind": "ITEM",
                "values_exact": ["20", "15"],
            },
            {
                "hierarchy_path_exact": ["Sử dụng dự phòng trong kỳ"],
                "label_exact": "Sử dụng dự phòng trong kỳ",
                "row_kind": "ITEM",
                "values_exact": ["(10)", "(5)"],
            },
            {
                "hierarchy_path_exact": ["Số dư cuối kỳ"],
                "label_exact": "Số dư cuối kỳ",
                "row_kind": "TOTAL",
                "values_exact": ["110", "100"],
            },
        ],
        "title_exact": title,
        "unit_exact": "Triệu đồng",
    }


def _lane_page(narratives: list[str], *tables: dict) -> dict:
    page = _page(*tables)
    page["sections"][0]["narratives_exact"] = narratives
    return page


def _stacked_table() -> dict:
    table = _period_table("Biến động dự phòng rủi ro cho vay khách hàng")
    table["rows"] = [
        {
            "hierarchy_path_exact": ["Tại ngày 1 tháng 1 năm 2024"],
            "label_exact": "Tại ngày 1 tháng 1 năm 2024",
            "row_kind": "ITEM",
            "values_exact": ["90", "190", "90"],
        },
        {
            "hierarchy_path_exact": ["Trích lập"],
            "label_exact": "Trích lập",
            "row_kind": "ITEM",
            "values_exact": ["10", "10", "10"],
        },
        {
            "hierarchy_path_exact": ["Tại ngày 31 tháng 12 năm 2024"],
            "label_exact": "Tại ngày 31 tháng 12 năm 2024",
            "row_kind": "TOTAL",
            "values_exact": ["100", "200", "100"],
        },
        {
            "hierarchy_path_exact": ["Trích lập"],
            "label_exact": "Trích lập",
            "row_kind": "ITEM",
            "values_exact": ["10", "15", "10"],
        },
        {
            "hierarchy_path_exact": ["Tại ngày 31 tháng 12 năm 2025"],
            "label_exact": "Tại ngày 31 tháng 12 năm 2025",
            "row_kind": "TOTAL",
            "values_exact": ["110", "215", "110"],
        },
    ]
    return table


def _evaluate(
    page: dict,
    *,
    refs: list[dict] | None = None,
    pages: dict[str, dict] | None = None,
) -> dict:
    refs = refs or [
        {
            "page_json_version_id": VERSION_A,
            "physical_page": 7,
            "section_id": "s1",
            "table_id": "t1",
        },
        {
            "page_json_version_id": VERSION_A,
            "physical_page": 7,
            "section_id": "s1",
            "table_id": "t2",
        },
    ]
    return evaluate_gemini_json_rollforward_family_cluster_v1(
        regions=refs,
        page_json_by_version=pages or {VERSION_A: page},
        compiled_specs=_compiled(),
        query_receipt={
            "exact_region_count": len(refs),
            "format_version": QUERY_RECEIPT_FORMAT_VERSION,
        },
    )


def test_one_unknown_is_solved_only_by_one_full_rank_lane_equation() -> None:
    solution = solve_one_unknown_rollforward_lane_v1(
        {
            "OPENING_BALANCE_ROW": _cell(100),
            "PROVISION_OR_REVERSAL_ROW": _cell(None),
            "USE_MOVEMENT_ROW": _cell(-10),
            "CLOSING_BALANCE_ROW": _cell(110),
        },
        movement_specs=_movement_specs(),
    )

    assert solution == {
        "equation_rank": 1,
        "inferred_coefficient": 20,
        "inferred_role": "PROVISION_OR_REVERSAL_ROW",
        "residual": 0,
        "status": "EXACT_ONE_UNKNOWN_INFERRED",
        "unknown_roles": ["PROVISION_OR_REVERSAL_ROW"],
    }


def test_two_unknowns_are_rank_deficient_and_never_coerced_to_zero() -> None:
    solution = solve_one_unknown_rollforward_lane_v1(
        {
            "OPENING_BALANCE_ROW": _cell(100),
            "PROVISION_OR_REVERSAL_ROW": _cell(None),
            "USE_MOVEMENT_ROW": _cell(None),
            "CLOSING_BALANCE_ROW": _cell(100),
        },
        movement_specs=_movement_specs(),
    )

    assert solution["status"] == "RANK_DEFICIENT_MULTIPLE_UNKNOWNS"
    assert solution["unknown_roles"] == [
        "PROVISION_OR_REVERSAL_ROW",
        "USE_MOVEMENT_ROW",
    ]
    assert "inferred_coefficient" not in solution


def test_absent_optional_row_is_not_an_unknown_cell() -> None:
    solution = solve_one_unknown_rollforward_lane_v1(
        {
            "OPENING_BALANCE_ROW": _cell(100),
            "PROVISION_OR_REVERSAL_ROW": _cell(10),
            "CLOSING_BALANCE_ROW": _cell(110),
        },
        movement_specs=_movement_specs(),
    )

    assert solution["status"] == "EXACT"
    assert solution["residual"] == 0


def test_one_unknown_table_cell_is_inferred_and_ready() -> None:
    candidate = _evaluate(
        _page(
            _period_table("Tại ngày 31 tháng 12 năm 2025", margin_provision=None),
            _period_table("Tại ngày 31 tháng 12 năm 2024"),
        )
    )

    assert candidate["status"] == READY
    assert candidate["reasons"] == []
    inferred = [mapping for mapping in candidate["mappings"] if mapping["report_norm_id"] == 6063]
    assert len(inferred) == 1
    assert inferred[0]["cell"]["coefficient"] == 20
    assert inferred[0]["cell"]["state"] == "INFERRED_ONE_UNKNOWN_FULL_RANK"


def test_comparative_multiple_unknowns_veto_every_mapping() -> None:
    candidate = _evaluate(
        _page(
            _period_table("Tại ngày 31 tháng 12 năm 2025"),
            _period_table(
                "Tại ngày 31 tháng 12 năm 2024",
                margin_provision=None,
                margin_use=None,
            ),
        )
    )

    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert any(
        reason == "ROLLFORWARD_LANE_EQUATION_RANK_DEFICIENT_MULTIPLE_UNKNOWNS:"
        "COMPARATIVE_PERIOD:MARGIN_ADVANCE_PROVISION_LANE"
        for reason in candidate["reasons"]
    )
    assert {vector["period_role"] for vector in candidate["closure_receipt"]["role_vectors"]} == {
        "CURRENT_PERIOD",
        "COMPARATIVE_PERIOD",
    }


def test_comparative_equation_mismatch_vetoes_current_period_mappings() -> None:
    comparative = _period_table("Tại ngày 31 tháng 12 năm 2024")
    comparative["rows"][-1]["values_exact"][0] = "111"
    candidate = _evaluate(
        _page(
            _period_table("Tại ngày 31 tháng 12 năm 2025"),
            comparative,
        )
    )

    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert (
        "ROLLFORWARD_LANE_EQUATION_MISMATCH:COMPARATIVE_PERIOD:GENERAL_PROVISION_LANE"
    ) in candidate["reasons"]


def test_money_unit_must_match_across_both_periods() -> None:
    candidate = _evaluate(
        _page(
            _period_table("Tại ngày 31 tháng 12 năm 2025", unit="Triệu đồng"),
            _period_table("Tại ngày 31 tháng 12 năm 2024", unit="Tỷ đồng"),
        )
    )

    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "ROLLFORWARD_MONEY_UNIT_MISMATCH_ACROSS_PERIODS_OR_COMPONENTS" in candidate["reasons"]


def test_optional_lane_population_must_be_identical_across_periods() -> None:
    comparative = _period_table("Tại ngày 31 tháng 12 năm 2024")
    comparative["columns"].pop()
    for row in comparative["rows"]:
        row["values_exact"].pop()
    candidate = _evaluate(
        _page(
            _period_table("Tại ngày 31 tháng 12 năm 2025"),
            comparative,
        )
    )

    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "ROLLFORWARD_LANE_POPULATION_MISMATCH_ACROSS_PERIODS" in candidate["reasons"]


def test_two_unknown_margin_cells_withhold_every_authoritative_mapping() -> None:
    candidate = _evaluate(
        _page(
            _period_table(
                "Tại ngày 31 tháng 12 năm 2025",
                margin_provision=None,
                margin_use=None,
            ),
            _period_table("Tại ngày 31 tháng 12 năm 2024"),
        )
    )

    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["closure_receipt"]["potential_mapping_count"] == 10
    assert any(
        reason == "ROLLFORWARD_LANE_EQUATION_RANK_DEFICIENT_MULTIPLE_UNKNOWNS:"
        "MARGIN_ADVANCE_PROVISION_LANE"
        for reason in candidate["reasons"]
    )
    frontier = candidate["closure_receipt"]["unresolved_frontiers"][0]
    assert frontier["unknown_roles"] == [
        "PROVISION_OR_REVERSAL_ROW",
        "USE_MOVEMENT_ROW",
    ]


def test_missing_bound_money_unit_is_unresolved_and_withholds_mappings() -> None:
    candidate = _evaluate(
        _page(
            _period_table("Tại ngày 31 tháng 12 năm 2025", unit=None),
            _period_table("Tại ngày 31 tháng 12 năm 2024", unit=None),
        )
    )

    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "ROLLFORWARD_MONEY_UNIT_NOT_VISIBLE" in candidate["reasons"]


def test_ordered_local_narratives_bind_transposed_lane_tables() -> None:
    candidate = _evaluate(
        _lane_page(
            [
                "Biến động dự phòng chung cho các khoản cho vay khách hàng như sau:",
                "Biến động dự phòng cụ thể cho các khoản cho vay khách hàng như sau:",
            ],
            _lane_table(),
            _lane_table(),
        )
    )

    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 8


def test_swapped_or_extra_narrative_axis_is_not_arbitrarily_assigned() -> None:
    for narratives in (
        [
            "Biến động dự phòng cụ thể cho các khoản cho vay khách hàng như sau:",
            "Biến động dự phòng chung cho các khoản cho vay khách hàng như sau:",
        ],
        [
            "Biến động dự phòng chung cho các khoản cho vay khách hàng như sau:",
            "Biến động dự phòng cụ thể cho các khoản cho vay khách hàng như sau:",
            "Dự phòng cho vay giao dịch ký quỹ và ứng trước",
        ],
    ):
        candidate = _evaluate(_lane_page(narratives, _lane_table(), _lane_table()))
        assert candidate["status"] == UNRESOLVED
        assert candidate["mappings"] == []
        assert "ROLLFORWARD_LOCAL_LANE_ASSIGNMENT_NOT_UNIQUE" in candidate["reasons"]


def test_reset_fence_blocks_narrative_lane_carry() -> None:
    candidate = _evaluate(
        _lane_page(
            [
                "Biến động dự phòng chung cho các khoản cho vay khách hàng như sau:",
                "Thư tín dụng",
                "Biến động dự phòng cụ thể cho các khoản cho vay khách hàng như sau:",
            ],
            _lane_table(),
            _lane_table(),
        )
    )

    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_adjacent_component_can_inherit_one_bounded_reset_fenced_owner_context() -> None:
    current = _page(_period_table("31/12/2025"))
    comparative = _page(_period_table("31/12/2024"))
    comparative_section = comparative["sections"][0]
    comparative_section["title_exact"] = "Bảng biến động dự phòng (tiếp theo)"
    comparative_section["narratives_exact"] = ["Tiếp theo trang trước"]
    for column in comparative_section["tables"][0]["columns"]:
        column["header_path_exact"] = [column["header_path_exact"][-1]]
    refs = [
        {
            "page_json_version_id": VERSION_A,
            "physical_page": 7,
            "section_id": "s1",
            "table_id": "t1",
        },
        {
            "page_json_version_id": VERSION_B,
            "physical_page": 8,
            "section_id": "s1",
            "table_id": "t1",
        },
    ]

    candidate = _evaluate(
        current,
        refs=refs,
        pages={VERSION_A: current, VERSION_B: comparative},
    )

    assert candidate["status"] == READY
    population = candidate["closure_receipt"]["population_receipt"]
    assert population["binding_kind"] == "BOUNDED_SELECTED_COMPONENT_OWNER_CONTINUATION"
    assert population["reset_fence_receipt"]["status"] == "RESET_FENCE_CLEAR"


def test_bounded_owner_continuation_stops_at_an_intervening_reset() -> None:
    current = _page(_period_table("31/12/2025"))
    comparative = _page(_period_table("31/12/2024"))
    target = comparative["sections"][0]
    target["title_exact"] = "Bảng biến động dự phòng (tiếp theo)"
    target["narratives_exact"] = ["Tiếp theo trang trước"]
    for column in target["tables"][0]["columns"]:
        column["header_path_exact"] = [column["header_path_exact"][-1]]
    comparative["sections"].insert(
        0,
        {
            "content_kind": "FINANCIAL_NOTE",
            "narratives_exact": ["Thư tín dụng"],
            "statement_type": "NOT_APPLICABLE",
            "tables": [],
            "title_exact": "Nghiệp vụ phát hành thư tín dụng",
        },
    )
    refs = [
        {
            "page_json_version_id": VERSION_A,
            "physical_page": 7,
            "section_id": "s1",
            "table_id": "t1",
        },
        {
            "page_json_version_id": VERSION_B,
            "physical_page": 8,
            "section_id": "s2",
            "table_id": "t1",
        },
    ]

    candidate = _evaluate(
        current,
        refs=refs,
        pages={VERSION_A: current, VERSION_B: comparative},
    )

    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "ROLLFORWARD_BOUNDED_OWNER_CONTINUATION_RESET_FENCE_VIOLATED" in candidate["reasons"]


def test_shared_endpoint_stacked_blocks_require_full_exact_equations() -> None:
    candidate = _evaluate(
        _page(_stacked_table()),
        refs=[
            {
                "page_json_version_id": VERSION_A,
                "physical_page": 7,
                "section_id": "s1",
                "table_id": "t1",
            }
        ],
    )

    assert candidate["status"] == READY
    assert candidate["closure_receipt"]["orientation"] == "STACKED_PERIOD_BLOCKS"
    assert len(candidate["closure_receipt"]["endpoint_continuity_receipts"]) == 3
    for receipt in candidate["closure_receipt"]["endpoint_continuity_receipts"]:
        assert receipt["previous_closing"]["locator"]
        assert receipt["next_opening"]["locator"]
        assert receipt["previous_closing"]["cell"] == receipt["next_opening"]["cell"]


def test_shared_endpoint_stacked_blocks_cannot_run_backwards() -> None:
    table = _stacked_table()
    for row_index, period in (
        (2, "Tại ngày 31 tháng 12 năm 2025"),
        (4, "Tại ngày 31 tháng 12 năm 2024"),
    ):
        table["rows"][row_index]["label_exact"] = period
        table["rows"][row_index]["hierarchy_path_exact"] = [period]
    candidate = _evaluate(
        _page(table),
        refs=[
            {
                "page_json_version_id": VERSION_A,
                "physical_page": 7,
                "section_id": "s1",
                "table_id": "t1",
            }
        ],
    )

    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert any(
        reason.startswith("ROLLFORWARD_SHARED_ENDPOINT_CONTINUITY_INVALID:")
        for reason in candidate["reasons"]
    )


def test_partial_block_and_duplicate_endpoint_are_terminal_unknowns() -> None:
    for mutation in ("PARTIAL", "DUPLICATE_ENDPOINT"):
        current = _period_table("31/12/2025")
        if mutation == "PARTIAL":
            current["rows"] = current["rows"][:-1]
        else:
            current["rows"].append(dict(current["rows"][-1]))
        candidate = _evaluate(_page(current, _period_table("31/12/2024")))
        assert candidate["status"] == UNRESOLVED
        assert candidate["mappings"] == []
        assert "ROLLFORWARD_COMPONENT_TABLE_STRUCTURE_INVALID" in candidate["reasons"]


def test_adjacent_period_tables_are_bounded_and_wrong_period_is_unresolved() -> None:
    refs = [
        {
            "page_json_version_id": VERSION_A,
            "physical_page": 7,
            "section_id": "s1",
            "table_id": "t1",
        },
        {
            "page_json_version_id": VERSION_B,
            "physical_page": 8,
            "section_id": "s1",
            "table_id": "t1",
        },
    ]
    current = _page(_period_table("31/12/2025"))
    comparative = _page(_period_table("31/12/2024"))
    ready = _evaluate(
        current,
        refs=refs,
        pages={VERSION_A: current, VERSION_B: comparative},
    )
    assert ready["status"] == READY

    wrong = _page(_period_table("31/12/2025"))
    unresolved = _evaluate(
        current,
        refs=refs,
        pages={VERSION_A: current, VERSION_B: wrong},
    )
    assert unresolved["status"] == UNRESOLVED
    assert unresolved["mappings"] == []
    assert "ROLLFORWARD_EXACT_TWO_PERIOD_AXIS_NOT_RESOLVED" in unresolved["reasons"]


def test_date_style_opening_endpoint_needs_ordered_complete_topology() -> None:
    def dated(period_end: str, opening: str) -> dict:
        table = _period_table(period_end)
        table["rows"][0]["label_exact"] = opening
        table["rows"][0]["hierarchy_path_exact"] = [opening]
        table["rows"][-1]["label_exact"] = period_end
        table["rows"][-1]["hierarchy_path_exact"] = [period_end]
        return table

    candidate = _evaluate(
        _page(
            dated("Số dư tại ngày 30 tháng 6 năm 2025", "Số dư tại ngày 31 tháng 12 năm 2024"),
            dated("Số dư tại ngày 30 tháng 6 năm 2024", "Số dư tại ngày 31 tháng 12 năm 2023"),
        )
    )
    assert candidate["status"] == READY
