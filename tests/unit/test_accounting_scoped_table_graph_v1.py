from __future__ import annotations

import unicodedata
from copy import deepcopy

import pytest

from bctc_ai.evaluation.accounting_scoped_table_graph_v1 import (
    AccountingScopedTableGraphV1Error,
    build_accounting_scoped_table_graph_v1,
    validate_accounting_scoped_table_graph_replay_v1,
)


def _spec(
    *,
    layouts: list[str] | None = None,
    budget: int = 1,
    require_total: bool = True,
    unlabeled_gap: int = 2,
    unlabeled_jitter_ppm: int = 200_000,
    unlabeled_max: int = 8,
    unlabeled_min: int = 5,
) -> dict[str, object]:
    return {
        "continuation_aliases": ["Tiếp theo"],
        "family_id": "SYNTHETIC_SCOPED_ACCOUNTING_FAMILY",
        "format_version": "ACCOUNTING_SCOPED_TABLE_FAMILY_SPEC_V1",
        "layout_modes": layouts or ["ROLES_AS_COLUMNS", "ROLES_AS_ROWS"],
        "limits": {
            "axis_tolerance_ppm": 35_000,
            "continuation_page_budget": budget,
            "max_owner_distance_lines": 14,
            "max_role_gap_lines": 8,
            "max_wrap_lines": 3,
            "minimum_cell_row_overlap_ppm": 250_000,
            "unlabeled_total_gap_jitter_ppm": unlabeled_jitter_ppm,
            "unlabeled_total_max_gap_lines": unlabeled_gap,
            "unlabeled_total_max_numeric_columns": unlabeled_max,
            "unlabeled_total_min_numeric_columns": unlabeled_min,
        },
        "owner_aliases": [
            "Mức độ tập trung tài sản và công nợ theo khu vực địa lý",
        ],
        "require_trailing_total_for_roles_as_columns": require_total,
        "role_axis": [
            {"aliases": ["Trong nước"], "role": "DOMESTIC_TOTAL"},
            {"aliases": ["Nước ngoài"], "role": "FOREIGN_TOTAL"},
        ],
        "scope_axis": [
            {
                "aliases": ["Cho vay khách hàng"],
                "disposition": "TARGET",
                "scope_id": "EXACT_CUSTOMER_LOANS",
            },
            {
                "aliases": ["Tổng dư nợ cho vay"],
                "disposition": "HARD_VETO_BROAD",
                "scope_id": "BROAD_TOTAL_LOANS",
            },
            {
                "aliases": ["Cho vay khách hàng và các TCTD"],
                "disposition": "HARD_VETO_MIXED",
                "scope_id": "BROAD_MIXED_LOAN_POPULATION",
            },
        ],
        "structural_reset_aliases": ["Thuyết minh khác"],
        "target_scope_id": "EXACT_CUSTOMER_LOANS",
        "trailing_total_aliases": ["Tổng cộng"],
    }


def _line(
    index: int,
    text: str,
    bbox: list[int],
    source_text: str | None = None,
) -> dict[str, object]:
    return {
        "bbox": bbox,
        "source_line_index": index,
        "source_text": source_text,
        "vietocr_text": text,
    }


def _page(sequence: int, lines: list[dict[str, object]]) -> dict[str, object]:
    # Deliberately preserve caller/provider serialization, rather than visual
    # order.  The graph must sort by bbox and retain the source locators.
    return {
        "lines": lines,
        "page_height": 1_000,
        "page_sequence": sequence,
        "page_width": 1_000,
    }


def _owner_lines(offset: int = 0) -> list[dict[str, object]]:
    return [
        _line(90 + offset, "Mức độ tập trung tài sản và công nợ", [20, 20, 610, 46]),
        _line(3 + offset, "theo khu vực địa lý", [20, 50, 310, 76]),
    ]


def _row_layout_page(sequence: int = 1, period: str = "31/12/2025") -> dict[str, object]:
    return _page(
        sequence,
        [
            # Values and provider indices intentionally precede their labels.
            _line(99, "1.000", [685, 220, 755, 248], "1.000"),
            _line(7, "Nuoc ngoai", [40, 270, 190, 298]),
            *_owner_lines(),
            _line(88, period, [650, 82, 810, 108]),
            _line(11, "Tổng dư nợ cho vay", [350, 120, 555, 148]),
            # Merged/multilevel target header: another column is interleaved
            # in provider visual order between these two fragments.
            _line(12, "Cho vay", [650, 116, 790, 144]),
            _line(15, "Cho vay khách hàng và các TCTD", [810, 118, 990, 146]),
            _line(13, "khách hàng", [650, 148, 805, 176]),
            _line(14, "triệu đồng", [660, 180, 805, 206]),
            _line(4, "Trong nước", [40, 220, 190, 248]),
            _line(5, "900", [685, 270, 755, 298], "900"),
            _line(16, "Tổng cộng", [40, 320, 190, 348]),
            _line(17, "1.900", [685, 320, 755, 348], "1.900"),
        ],
    )


def _column_layout_page(
    sequence: int,
    period: str,
    *,
    include_total: bool = True,
    adjacent_domestic_only: bool = False,
    reset: bool = False,
) -> dict[str, object]:
    lines = [
        *_owner_lines(sequence * 100),
        _line(20, period, [590, 80, 830, 106]),
        _line(21, "triệu đồng", [700, 84, 845, 110]),
        _line(22, "Trong nước", [570, 120, 710, 148]),
        _line(23, "Nước ngoài", [750, 120, 890, 148]),
        _line(24, "Cho vay", [30, 178, 170, 206]),
        _line(25, "khách hàng", [30, 208, 185, 236]),
        _line(27, "800", [775, 204, 845, 232], "800"),
        _line(37, "1.700", [930, 204, 990, 232], "1.700"),
    ]
    if include_total:
        lines.append(_line(26, "Tổng cộng", [920, 120, 995, 148]))
    if adjacent_domestic_only:
        # Center proximity alone could borrow this following-row value.  Its
        # actual intersection with the target row is below the closed minimum.
        lines.append(_line(28, "700", [595, 234, 665, 262], "700"))
    else:
        lines.append(_line(28, "900", [595, 204, 665, 232], "900"))
    if reset:
        lines.append(_line(29, "Thuyết minh khác", [20, 300, 300, 328]))
    return _page(sequence, list(reversed(lines)))


def test_rows_layout_preserves_vietnamese_channels_and_hard_vetoes_broad_scope() -> None:
    result = build_accounting_scoped_table_graph_v1([_row_layout_page()], _spec())

    assert result["metrics"] == {
        "bounded_absence_count": 2,
        "complete_graph_count": 1,
        "page_count": 1,
        "partial_completion_graph_count": 0,
        "physical_segment_count": 3,
        "repeated_full_period_complement_graph_count": 0,
        "unresolved_fragment_count": 0,
    }
    exact = next(
        item
        for item in result["physical_segments"]
        if item["population_scope"]["scope_id"] == "EXACT_CUSTOMER_LOANS"
    )
    assert exact["layout_mode"] == "ROLES_AS_ROWS"
    assert exact["population_scope"]["match"]["surface_raw_nfc"] == "Cho vay khách hàng"
    assert exact["population_scope"]["match"]["source_line_indices_in_visual_order"] == [12, 13]
    assert exact["header_context"]["header_geometry"]["format_version"] == (
        "ADAPTIVE_ACCOUNTING_MULTILEVEL_HEADER_GRAPH_V1"
    )
    foreign = next(item for item in exact["role_matches"] if item["semantic_id"] == "FOREIGN_TOTAL")
    assert foreign["surface_raw_nfc"] == "Nuoc ngoai"
    assert foreign["surface_accentless"] == "nuoc ngoai"
    assert foreign["match"]["match_kind"] == "EXACT_ACCENTLESS_ALIAS"
    assert [item["source_line_index"] for item in exact["role_cells"]] == [99, 5]
    assert exact["trailing_total_match"]["surface_raw_nfc"] == "Tổng cộng"
    assert [item["source_line_index"] for item in exact["trailing_total_cells"]] == [17]
    assert {item["population_scope"]["disposition"] for item in result["bounded_absences"]} == {
        "HARD_VETO_BROAD",
        "HARD_VETO_MIXED",
    }


def test_transposed_layout_requires_row_overlap_and_closes_last_lane_at_total_header() -> None:
    result = build_accounting_scoped_table_graph_v1(
        [_column_layout_page(1, "31/12/2025", adjacent_domestic_only=True)],
        _spec(layouts=["ROLES_AS_COLUMNS"]),
    )
    segment = result["physical_segments"][0]

    assert segment["layout_mode"] == "ROLES_AS_COLUMNS"
    domestic, foreign = segment["role_cells"]
    assert domestic["role"] == "DOMESTIC_TOTAL"
    assert domestic["source_line_index"] is None
    assert domestic["status"] == "MISSING_DETECTOR_CELL_REQUIRES_AUTHENTICATED_PIXEL_REPLAY"
    assert foreign["source_line_index"] == 27
    assert foreign["row_overlap_ppm"] == 1_000_000
    # The total header is the next visible lane; the geography cell closes at
    # their midpoint, not at the page edge or an arbitrary symmetric extent.
    assert segment["axis_pixel_bounds"][-1][1] == 889
    assert segment["axis_pixel_bounds"][-1][1] < 1_000
    assert segment["trailing_total_match"]["surface_raw_nfc"] == "Tổng cộng"
    assert [item["source_line_index"] for item in segment["trailing_total_cells"]] == [37]


def test_transposed_layout_fails_closed_without_required_trailing_total() -> None:
    result = build_accounting_scoped_table_graph_v1(
        [_column_layout_page(1, "31/12/2025", include_total=False)],
        _spec(layouts=["ROLES_AS_COLUMNS"]),
    )

    assert result["graphs"] == []
    assert result["physical_segments"][0]["segment_status"] == "UNRESOLVED_PHYSICAL_SEGMENT"
    assert result["unresolved_fragments"][0]["unresolved_reasons"] == [
        "TRANSPOSED_TRAILING_TOTAL_HEADER_NOT_RESOLVED"
    ]


def test_adjacent_complete_pages_are_period_complements_not_partial_continuations() -> None:
    result = build_accounting_scoped_table_graph_v1(
        [
            _column_layout_page(56, "30/06/2025"),
            _column_layout_page(57, "31/12/2024"),
        ],
        _spec(layouts=["ROLES_AS_COLUMNS"]),
    )

    assert result["metrics"]["repeated_full_period_complement_graph_count"] == 1
    assert len(result["graphs"]) == 1
    graph = result["graphs"][0]
    assert graph["continuation"]["mode"] == ("ADJACENT_REPEATED_FULL_SEGMENTS_PERIOD_COMPLEMENT")
    assert graph["continuation"]["partial_table_completion"] is False
    assert graph["continuation"]["page_sequences"] == [56, 57]
    assert [item["period_lane_index"] for item in graph["segments"]] == [0, 1]
    assert [item["period_key"] for item in graph["segments"]] == ["30/06/2025", "31/12/2024"]
    for segment in graph["segments"]:
        assert {item["period_lane_index"] for item in segment["role_cells"]} == {
            segment["period_lane_index"]
        }
        assert [item["source_role_ordinal"] for item in segment["role_cells"]] == [0, 1]
        assert [item["source_value_column_ordinal"] for item in segment["role_cells"]] == [0, 1]
        assert {item["period_lane_index"] for item in segment["trailing_total_cells"]} == {
            segment["period_lane_index"]
        }


def _partial_row_page(
    sequence: int,
    role: str,
    *,
    reset: bool = False,
) -> dict[str, object]:
    role_text = "Trong nước" if role == "DOMESTIC_TOTAL" else "Nước ngoài"
    lines = [
        *_owner_lines(sequence * 100),
        _line(30, "31/12/2025", [650, 82, 810, 108]),
        _line(31, "triệu đồng", [660, 112, 810, 138]),
        _line(32, "Cho vay khách hàng", [650, 145, 835, 173]),
        _line(33, role_text, [40, 220, 190, 248]),
        _line(34, "900", [685, 220, 755, 248], "900"),
    ]
    if sequence > 1:
        lines.append(_line(35, "Tiếp theo", [20, 78, 150, 104]))
    if reset:
        lines.append(_line(36, "Thuyết minh khác", [20, 185, 300, 213]))
    return _page(sequence, list(reversed(lines)))


def test_partial_cross_page_role_deficit_closes_only_with_compatible_evidence() -> None:
    result = build_accounting_scoped_table_graph_v1(
        [
            _partial_row_page(1, "DOMESTIC_TOTAL"),
            _partial_row_page(2, "FOREIGN_TOTAL"),
        ],
        _spec(layouts=["ROLES_AS_ROWS"]),
    )

    assert result["metrics"]["partial_completion_graph_count"] == 1
    graph = result["graphs"][0]
    assert graph["continuation"]["mode"] == "ADJACENT_PARTIAL_ROLE_DEFICIT_COMPLETION"
    assert [item["observed_roles"] for item in graph["partial_fragments"]] == [
        ["DOMESTIC_TOTAL"],
        ["FOREIGN_TOTAL"],
    ]
    assert graph["resolved_period"] == "31/12/2025"
    assert all(
        item["scope_match"]["page_sequence"] == item["page_sequence"]
        for item in graph["partial_fragments"]
    )


def test_partial_completion_supports_multiple_observed_roles_in_three_role_family() -> None:
    spec = _spec(layouts=["ROLES_AS_ROWS"])
    spec["role_axis"].append({"aliases": ["Ngoài lãnh thổ"], "role": "OFFSHORE_TOTAL"})
    first = _partial_row_page(1, "DOMESTIC_TOTAL")
    first["lines"].extend(
        [
            _line(37, "Nước ngoài", [40, 270, 190, 298]),
            _line(38, "100", [685, 270, 755, 298], "100"),
        ]
    )
    second = _partial_row_page(2, "FOREIGN_TOTAL")
    for line in second["lines"]:
        if line["source_line_index"] == 33:
            line["vietocr_text"] = "Ngoài lãnh thổ"

    result = build_accounting_scoped_table_graph_v1([first, second], spec)

    assert result["metrics"]["partial_completion_graph_count"] == 1
    fragments = result["graphs"][0]["partial_fragments"]
    assert [item["observed_roles"] for item in fragments] == [
        ["DOMESTIC_TOTAL", "FOREIGN_TOTAL"],
        ["OFFSHORE_TOTAL"],
    ]


def test_structural_reset_and_budget_exhaustion_remain_explicitly_unresolved() -> None:
    reset = build_accounting_scoped_table_graph_v1(
        [
            _partial_row_page(1, "DOMESTIC_TOTAL"),
            _partial_row_page(2, "FOREIGN_TOTAL", reset=True),
        ],
        _spec(layouts=["ROLES_AS_ROWS"]),
    )
    assert reset["graphs"] == []
    assert {item["unresolved_reason"] for item in reset["unresolved_fragments"]} >= {
        "STRUCTURAL_RESET_BLOCKED_ADJACENT_COMPLETION"
    }

    exhausted = build_accounting_scoped_table_graph_v1(
        [
            _partial_row_page(1, "DOMESTIC_TOTAL"),
            _partial_row_page(2, "FOREIGN_TOTAL"),
        ],
        _spec(layouts=["ROLES_AS_ROWS"], budget=0),
    )
    assert exhausted["graphs"] == []
    assert {item["unresolved_reason"] for item in exhausted["unresolved_fragments"]} == {
        "CONTINUATION_BUDGET_EXHAUSTED_OR_NO_COMPATIBLE_ADJACENT_FRAGMENT"
    }


def test_public_replay_rejects_self_rehashed_forgery() -> None:
    pages = [_row_layout_page()]
    spec = _spec()
    result = build_accounting_scoped_table_graph_v1(pages, spec)
    assert validate_accounting_scoped_table_graph_replay_v1(result, pages, spec) == result

    forged = deepcopy(result)
    forged["metrics"]["complete_graph_count"] += 1
    material = deepcopy(forged)
    material.pop("result_id")
    from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

    forged["result_id"] = "astgv1:result:" + canonical_json_sha256_v1(material)
    with pytest.raises(AccountingScopedTableGraphV1Error, match="does not replay exactly"):
        validate_accounting_scoped_table_graph_replay_v1(forged, pages, spec)


def test_compiled_matcher_avoids_window_times_alias_edit_scan_and_persists_features() -> None:
    spec = _spec()
    broad = spec["scope_axis"][1]
    broad["aliases"].extend(
        f"Khoản mục đối chứng không liên quan chuỗi dài số {index}" for index in range(200)
    )
    result = build_accounting_scoped_table_graph_v1([_row_layout_page()], spec)
    matcher = result["matcher_metrics"]

    assert matcher["compiled_alias_count"] == 209
    assert matcher["visual_window_count"] > 0
    assert matcher["approximate_alias_comparison_count"] < matcher["visual_window_count"]
    # A naive implementation would call edit distance for every alias/window.
    assert matcher["approximate_alias_comparison_count"] < (
        matcher["compiled_alias_count"] * matcher["visual_window_count"] // 100
    )
    match = result["physical_segments"][0]["owner"]["match"]
    assert match["edit_bound"] == 0
    assert match["candidate_feature_vector"]["qgram_union_count"] > 0
    assert match["context_gates"] == {
        "complete_geometry_required": True,
        "phrase_window_allowed": True,
        "source_window_line_count": 2,
    }


def test_non_nfc_source_surface_is_rejected_instead_of_silently_rewritten() -> None:
    page = _row_layout_page()
    page["lines"][0]["vietocr_text"] = unicodedata.normalize(
        "NFD", str(page["lines"][0]["vietocr_text"])
    )
    # Use a surface which actually contains a combining mark.
    page["lines"][0]["vietocr_text"] = unicodedata.normalize("NFD", "triệu")
    with pytest.raises(AccountingScopedTableGraphV1Error, match="NFC-normalized"):
        build_accounting_scoped_table_graph_v1([page], _spec())


def test_two_period_row_layout_binds_header_spans_to_scope_value_lanes() -> None:
    page = _page(
        1,
        [
            *_owner_lines(200),
            _line(1, "31/12/2025", [540, 84, 690, 110]),
            _line(2, "31/12/2024", [760, 84, 910, 110]),
            _line(3, "Cho vay khách hàng", [520, 125, 710, 153]),
            _line(4, "Cho vay khách hàng", [740, 125, 930, 153]),
            _line(5, "triệu đồng", [550, 165, 690, 191]),
            _line(6, "triệu đồng", [770, 165, 910, 191]),
            _line(7, "Trong nước", [40, 220, 190, 248]),
            _line(8, "1.000", [580, 220, 660, 248], "1.000"),
            _line(9, "900", [800, 220, 870, 248], "900"),
            _line(10, "Nước ngoài", [40, 270, 190, 298]),
            _line(11, "100", [580, 270, 660, 298], "100"),
            _line(12, "90", [800, 270, 870, 298], "90"),
            _line(13, "Tổng cộng", [40, 320, 190, 348]),
            _line(14, "1.100", [580, 320, 660, 348], "1.100"),
            _line(15, "990", [800, 320, 870, 348], "990"),
        ],
    )

    result = build_accounting_scoped_table_graph_v1([page], _spec(layouts=["ROLES_AS_ROWS"]))

    assert len(result["graphs"]) == 1
    graph = result["graphs"][0]
    assert graph["continuation"]["mode"] == "SINGLE_PAGE_MULTI_PERIOD_COMPLETE_SEGMENTS"
    assert [item["period_key"] for item in graph["segments"]] == [
        "31/12/2025",
        "31/12/2024",
    ]
    assert [item["period_lane_index"] for item in graph["segments"]] == [0, 1]
    assert all(
        item["period_resolution"]
        in {
            "LOCAL_PERIOD_HEADER_SPAN_BOUND_TO_VALUE_LANE",
            "LOCAL_PERIOD_HEADER_UNIQUE_NEAREST_VALUE_LANE",
        }
        for item in graph["segments"]
    )


def test_three_adjacent_full_period_segments_chain_and_reset_breaks_chain() -> None:
    pages = [
        _column_layout_page(56, "30/06/2025"),
        _column_layout_page(57, "31/12/2024"),
        _column_layout_page(58, "30/06/2024"),
    ]
    result = build_accounting_scoped_table_graph_v1(
        pages, _spec(layouts=["ROLES_AS_COLUMNS"], budget=2)
    )
    assert len(result["graphs"]) == 1
    assert result["graphs"][0]["continuation"]["page_sequences"] == [56, 57, 58]
    assert len(result["graphs"][0]["segments"]) == 3

    reset_page = _column_layout_page(57, "31/12/2024")
    reset_page["lines"].append(_line(150, "Thuyết minh khác", [20, 75, 280, 103]))
    reset = build_accounting_scoped_table_graph_v1(
        [pages[0], reset_page, pages[2]],
        _spec(layouts=["ROLES_AS_COLUMNS"], budget=2),
    )
    assert len(reset["graphs"]) >= 2
    assert all(graph["continuation"]["page_sequences"] != [56, 57, 58] for graph in reset["graphs"])

    exhausted = build_accounting_scoped_table_graph_v1(
        pages, _spec(layouts=["ROLES_AS_COLUMNS"], budget=1)
    )
    assert exhausted["graphs"] == []
    assert exhausted["unresolved_fragments"][0]["unresolved_reason"] == (
        "ADJACENT_REPEATED_FULL_SEGMENT_CHAIN_BUDGET_EXHAUSTED"
    )


def test_one_whitespace_fusion_is_bounded_and_unrelated_compact_text_is_negative() -> None:
    fused = _row_layout_page()
    for line in fused["lines"]:
        if line["source_line_index"] == 12:
            line["vietocr_text"] = "Chovay"
    result = build_accounting_scoped_table_graph_v1([fused], _spec())
    exact = next(
        item
        for item in result["physical_segments"]
        if item["population_scope"]["scope_id"] == "EXACT_CUSTOMER_LOANS"
    )
    assert exact["population_scope"]["match"]["match"]["match_kind"] == (
        "EXACT_ONE_WHITESPACE_FUSION_OR_SPLIT_ALIAS"
    )

    unrelated = deepcopy(fused)
    for line in unrelated["lines"]:
        if line["source_line_index"] == 12:
            line["vietocr_text"] = "Chovon"
    unrelated_result = build_accounting_scoped_table_graph_v1([unrelated], _spec())
    assert all(
        item["population_scope"]["scope_id"] != "EXACT_CUSTOMER_LOANS"
        for item in unrelated_result["physical_segments"]
    )


def test_wrapped_mixed_population_poison_closes_before_target_classification() -> None:
    page = _column_layout_page(1, "31/12/2025")
    page["lines"] = [
        line for line in page["lines"] if line["source_line_index"] not in {24, 25, 27, 28, 37}
    ]
    page["lines"].extend(
        [
            _line(40, "Tổng dư nợ cho vay khách hàng,", [30, 178, 430, 206]),
            _line(41, "mua nợ và cấp tín dụng cho các", [30, 208, 450, 236]),
            _line(42, "TCTD khác", [30, 238, 200, 266]),
            _line(43, "900", [595, 238, 665, 266], "900"),
            _line(44, "800", [775, 238, 845, 266], "800"),
            _line(45, "1.700", [930, 238, 990, 266], "1.700"),
        ]
    )
    spec = _spec(layouts=["ROLES_AS_COLUMNS"])
    spec["scope_axis"][2]["aliases"].append(
        "Tổng dư nợ cho vay khách hàng, mua nợ và cấp tín dụng cho các TCTD khác"
    )
    result = build_accounting_scoped_table_graph_v1([page], spec)
    assert result["graphs"] == []
    assert {item["population_scope"]["scope_id"] for item in result["bounded_absences"]} == {
        "BROAD_MIXED_LOAN_POPULATION"
    }


def test_page_local_reset_blocks_cross_reset_join_but_not_prior_exact_table() -> None:
    poisoned = _row_layout_page()
    poisoned["lines"].append(_line(120, "Thuyết minh khác", [20, 190, 300, 215]))
    blocked = build_accounting_scoped_table_graph_v1([poisoned], _spec(layouts=["ROLES_AS_ROWS"]))
    assert blocked["graphs"] == []

    after_table = _row_layout_page()
    after_table["lines"].append(_line(121, "Thuyết minh khác", [20, 380, 300, 408]))
    retained = build_accounting_scoped_table_graph_v1(
        [after_table], _spec(layouts=["ROLES_AS_ROWS"])
    )
    assert len(retained["graphs"]) == 1


def test_detected_value_cell_is_globally_exclusive_across_overlapping_rows() -> None:
    page = _page(
        1,
        [
            *_owner_lines(300),
            _line(1, "31/12/2025", [650, 82, 810, 108]),
            _line(2, "Cho vay khách hàng", [650, 130, 835, 158]),
            _line(3, "triệu đồng", [660, 170, 805, 198]),
            _line(4, "Trong nước", [40, 220, 190, 250]),
            _line(5, "Nước ngoài", [40, 240, 190, 270]),
            _line(6, "900", [685, 235, 755, 255], "900"),
            _line(7, "Tổng cộng", [40, 300, 190, 328]),
            _line(8, "900", [685, 300, 755, 328], "900"),
        ],
    )
    result = build_accounting_scoped_table_graph_v1([page], _spec(layouts=["ROLES_AS_ROWS"]))
    cells = result["graphs"][0]["segments"][0]["role_cells"]
    assert [item["source_line_index"] for item in cells] == [None, None]


def test_far_or_equidistant_narrative_periods_do_not_bind_a_value_lane() -> None:
    far = _row_layout_page()
    for line in far["lines"]:
        if line["source_line_index"] == 88:
            line["bbox"] = [20, 82, 150, 108]
    far_result = build_accounting_scoped_table_graph_v1([far], _spec(layouts=["ROLES_AS_ROWS"]))
    far_exact = next(
        item
        for item in far_result["graphs"][0]["segments"]
        if item["population_scope"]["scope_id"] == "EXACT_CUSTOMER_LOANS"
    )
    assert far_exact["period_key"] is None
    assert far_exact["period_resolution"] == "UNRESOLVED"

    tied = _row_layout_page()
    tied["lines"] = [item for item in tied["lines"] if item["source_line_index"] != 88]
    tied["lines"].extend(
        [
            _line(188, "31/12/2025", [625, 82, 675, 108]),
            _line(189, "31/12/2024", [780, 112, 830, 138]),
        ]
    )
    tied_result = build_accounting_scoped_table_graph_v1([tied], _spec(layouts=["ROLES_AS_ROWS"]))
    tied_exact = next(
        item
        for item in tied_result["physical_segments"]
        if item["population_scope"]["scope_id"] == "EXACT_CUSTOMER_LOANS"
    )
    assert tied_exact["period_key"] is None
    assert tied_exact["period_resolution"] == "UNRESOLVED"


def test_unique_nearby_left_stub_period_caption_binds_to_bounded_table_block() -> None:
    page = _row_layout_page()
    for line in page["lines"]:
        if line["source_line_index"] == 88:
            line["vietocr_text"] = "Tại ngày 31 tháng 12 năm 2025:"
            # Mirrors a real repeated-block edge case: the stub ends just
            # over half a lane width before the body-derived numeric lane.
            line["bbox"] = [260, 82, 478, 108]

    result = build_accounting_scoped_table_graph_v1([page], _spec(layouts=["ROLES_AS_ROWS"]))
    exact = next(
        item
        for item in result["graphs"][0]["segments"]
        if item["population_scope"]["scope_id"] == "EXACT_CUSTOMER_LOANS"
    )

    assert exact["period_key"] == "31/12/2025"
    assert exact["period_resolution"] == (
        "LOCAL_SINGLE_PERIOD_TABLE_BLOCK_CAPTION_BOUND_TO_LANE_DOMAIN"
    )


def test_unique_table_period_caption_can_bind_through_the_visible_unit_domain() -> None:
    page = _row_layout_page()
    page["page_width"] = 1_400
    page["lines"].append(_line(188, "triệu đồng", [1_050, 180, 1_190, 206]))
    for line in page["lines"]:
        if line["source_line_index"] == 88:
            line["bbox"] = [1_040, 82, 1_200, 108]

    result = build_accounting_scoped_table_graph_v1([page], _spec(layouts=["ROLES_AS_ROWS"]))
    exact = next(
        item
        for item in result["graphs"][0]["segments"]
        if item["population_scope"]["scope_id"] == "EXACT_CUSTOMER_LOANS"
    )

    assert exact["period_key"] == "31/12/2025"
    assert exact["period_resolution"] == (
        "LOCAL_SINGLE_PERIOD_TABLE_BLOCK_CAPTION_BOUND_TO_UNIT_DOMAIN"
    )

    gap_page = deepcopy(page)
    next(line for line in gap_page["lines"] if line["source_line_index"] == 88)["bbox"] = [
        870,
        82,
        980,
        108,
    ]
    gap_result = build_accounting_scoped_table_graph_v1(
        [gap_page], _spec(layouts=["ROLES_AS_ROWS"])
    )
    gap_exact = next(
        item
        for item in gap_result["physical_segments"]
        if item["population_scope"]["scope_id"] == "EXACT_CUSTOMER_LOANS"
    )
    assert gap_exact["period_key"] is None

    ambiguous_page = deepcopy(page)
    ambiguous_page["lines"].append(_line(189, "nghìn đồng", [1_050, 150, 1_190, 176]))
    ambiguous_result = build_accounting_scoped_table_graph_v1(
        [ambiguous_page], _spec(layouts=["ROLES_AS_ROWS"])
    )
    ambiguous_exact = next(
        item
        for item in ambiguous_result["physical_segments"]
        if item["population_scope"]["scope_id"] == "EXACT_CUSTOMER_LOANS"
    )
    assert ambiguous_exact["period_key"] is None


def _component_owner_spec(*, layouts: list[str]) -> dict[str, object]:
    spec = _spec(layouts=layouts)
    spec["owner_component_groups"] = [
        {"aliases": ["Mức độ tập trung", "Tập trung"], "component_id": "CONCENTRATION"},
        {"aliases": ["Khu vực địa lý", "Theo vùng"], "component_id": "GEOGRAPHY"},
        {
            "aliases": ["Tài sản", "Công nợ", "Nợ phải trả", "Cam kết ngoại bảng"],
            "component_id": "ACCOUNTING_CONTEXT",
        },
    ]
    spec["scope_axis"][2]["required_component_groups"] = [
        {"aliases": ["Cho vay khách hàng"], "component_id": "CUSTOMER_LOAN_SIGNAL"},
        {"aliases": ["TCTD", "Mua nợ", "Cấp tín dụng"], "component_id": "MIXED_MARKER"},
    ]
    spec["scope_axis"][0]["lane_component_groups"] = [
        {
            "aliases": ["Cho vay", "Dư nợ", "Nợ cho vay"],
            "component_id": "CUSTOMER_LOAN_ACTIVITY",
            "source": "PATH",
        },
        {
            "aliases": ["Khách hàng"],
            "component_id": "CUSTOMER_LOAN_LEAF",
            "source": "LEAF",
        },
    ]
    spec["scope_axis"][2]["lane_component_groups"] = [
        {
            "aliases": ["Cho vay", "Dư nợ", "Nợ cho vay"],
            "component_id": "MIXED_LOAN_ACTIVITY",
            "source": "PATH",
        },
        {
            "aliases": ["TCTD", "Mua nợ", "Cấp tín dụng"],
            "component_id": "MIXED_LANE_LEAF",
            "source": "LEAF",
        },
    ]
    return spec


def test_reordered_actual_owner_components_and_deep_scope_leaf_close_mbb_row_table() -> None:
    page = {
        "lines": [
            _line(
                1,
                "Mức độ tập trung theo khu vực địa lý của các tài sản, công nợ và các khoản mục ngoại",
                [303, 1506, 1469, 1540],
            ),
            _line(2, "bảng", [300, 1540, 377, 1576]),
            _line(
                3,
                "Tổng dư nợ cho vay khách hàng, tổng tiền gửi của khách hàng, các cam kết thư tín dụng, kinh",
                [305, 1606, 1464, 1632],
            ),
            _line(
                4,
                "doanh và đầu tư chứng khoán theo khu vực địa lý được trình bày dưới bảng tổng hợp sau:",
                [305, 1640, 1428, 1667],
            ),
            _line(5, "Tổng dư nợ cho", [438, 1696, 645, 1730]),
            _line(6, "vay khách hàng", [438, 1730, 640, 1764]),
            _line(7, "Trong nước", [234, 1781, 384, 1815]),
            _line(8, "789.700.726", [490, 1783, 645, 1810], "789.700.726"),
            _line(9, "Nước ngoài", [231, 1822, 384, 1857]),
            _line(10, "7.835.989", [514, 1820, 647, 1854], "7.835.989"),
        ],
        "page_height": 2_300,
        "page_sequence": 51,
        "page_width": 2_200,
    }

    result = build_accounting_scoped_table_graph_v1(
        [page], _component_owner_spec(layouts=["ROLES_AS_ROWS"])
    )

    assert len(result["graphs"]) == 1
    assert result["metrics"]["physical_segment_count"] == 1
    segment = result["graphs"][0]["segments"][0]
    assert segment["owner"]["match"]["match_kind"] == (
        "DECLARATIVE_REQUIRED_COMPONENT_GROUPS_IN_BOUNDED_VISUAL_WINDOW"
    )
    assert [item["component_id"] for item in segment["owner"]["match"]["component_matches"]] == [
        "CONCENTRATION",
        "GEOGRAPHY",
        "ACCOUNTING_CONTEXT",
    ]
    assert segment["population_scope"]["match"]["surface_raw_nfc"] == (
        "Tổng dư nợ cho vay khách hàng"
    )


def _actual_vib_period_page(sequence: int, period: str, *, scope_top: int) -> dict[str, object]:
    return {
        "lines": [
            _line(
                1,
                "MỨC ĐỘ TẬP TRUNG CỦA TÀI SẢN, NỢ PHẢI TRẢ VÀ CÁC CAM KẾT NGOẠI BẢNG",
                [315, 307, 1455, 353],
            ),
            _line(2, "THEO KHU VỰC ĐỊA LÝ", [317, 346, 635, 385]),
            _line(3, "Tổng cộng", [1311, 401, 1455, 451]),
            _line(4, "Trong nước", [906, 412, 1056, 446]),
            _line(5, "Nước ngoài", [1100, 412, 1253, 446]),
            _line(6, "triệu đồng", [923, 443, 1053, 480]),
            _line(7, "triệu đồng", [1120, 443, 1253, 478]),
            _line(8, "triệu đồng", [1322, 443, 1452, 478]),
            _line(9, period, [322, 451, 699, 485]),
            _line(10, "Tiền gửi tại và cho vay các TCTD khác", [332, 616, 812, 651]),
            _line(11, "118.067.865", [893, 614, 1053, 648], "118.067.865"),
            _line(12, "438.480", [1145, 612, 1253, 646], "438.480"),
            _line(13, "118.506.345", [1290, 612, 1450, 646], "118.506.345"),
            _line(14, "Cho vay khách hàng", [335, scope_top, 586, scope_top + 27]),
            _line(15, "397.083.447", [893, scope_top - 7, 1049, scope_top + 20], "397.083.447"),
            _line(16, "397.083.447", [1295, scope_top - 7, 1447, scope_top + 20], "397.083.447"),
        ],
        "page_height": 2_300,
        "page_sequence": sequence,
        "page_width": 1_500,
    }


def test_actual_vib_period_caption_below_roles_and_adjacent_body_row_do_not_duplicate_scope() -> (
    None
):
    result = build_accounting_scoped_table_graph_v1(
        [
            _actual_vib_period_page(56, "Tại ngày 30 tháng 6 năm 2026", scope_top=660),
            _actual_vib_period_page(57, "Tại ngày 31 tháng 12 năm 2025", scope_top=655),
        ],
        _component_owner_spec(layouts=["ROLES_AS_COLUMNS"]),
    )

    assert result["metrics"]["physical_segment_count"] == 2
    assert result["metrics"]["repeated_full_period_complement_graph_count"] == 1
    assert len(result["graphs"]) == 1
    graph = result["graphs"][0]
    assert graph["continuation"]["mode"] == ("ADJACENT_REPEATED_FULL_SEGMENTS_PERIOD_COMPLEMENT")
    assert [item["period_key"] for item in graph["segments"]] == [
        "30/06/2026",
        "31/12/2025",
    ]
    assert all(
        item["population_scope"]["match"]["surface_raw_nfc"] == "Cho vay khách hàng"
        for item in graph["segments"]
    )


def test_actual_broad_scope_terminalizes_before_transposed_total_requirement() -> None:
    page = _page(
        84,
        [
            _line(
                1,
                "Mức độ tập trung theo khu vực địa lý của các tài sản, công nợ và các khoản mục ngoại bảng",
                [50, 40, 950, 68],
            ),
            _line(2, "Trong nước", [570, 120, 710, 148]),
            _line(3, "Nước ngoài", [750, 120, 890, 148]),
            _line(4, "30/06/2026", [350, 150, 510, 176]),
            _line(5, "triệu đồng", [570, 152, 710, 178]),
            _line(6, "Tổng dư nợ cho vay khách hàng, mua nợ", [30, 204, 500, 232]),
            _line(7, "900", [595, 204, 665, 232], "900"),
            _line(8, "800", [775, 204, 845, 232], "800"),
        ],
    )

    result = build_accounting_scoped_table_graph_v1(
        [page], _component_owner_spec(layouts=["ROLES_AS_COLUMNS"])
    )

    assert result["graphs"] == []
    assert result["unresolved_fragments"] == []
    assert all(
        item["population_scope"]["scope_id"] != "EXACT_CUSTOMER_LOANS"
        for item in result["physical_segments"]
    )
    assert len(result["bounded_absences"]) == 1
    absence = result["bounded_absences"][0]
    assert absence["population_scope"]["scope_id"] == "BROAD_MIXED_LOAN_POPULATION"
    assert absence["segment_status"] == "HARD_VETO_SCOPE_BOUNDED_ABSENCE"


def test_wrapped_mixed_scope_value_overlap_follows_continuation_not_prefix() -> None:
    page = _page(
        74,
        [
            _line(
                1,
                "Mức độ tập trung theo khu vực địa lý của các tài sản, công nợ và các khoản mục ngoại bảng",
                [50, 360, 1_550, 394],
            ),
            _line(2, "Trong nước", [900, 420, 1_050, 454]),
            _line(3, "Nước ngoài", [1_090, 420, 1_245, 454]),
            _line(4, "Tổng cộng", [1_280, 420, 1_430, 454]),
            _line(5, "triệu đồng", [900, 455, 1_045, 483]),
            _line(
                6,
                "Tổng dư nợ cho vay khách hàng, mưa",
                [343, 487, 776, 521],
            ),
            _line(
                7,
                "1.047.765.320",
                [1_282, 511, 1_427, 545],
                "1.047.765.320",
            ),
            _line(
                8,
                "nợ và cấp tín dụng cho các TCTD khác",
                [341, 523, 783, 557],
            ),
        ],
    )
    page["page_width"] = 1_800

    result = build_accounting_scoped_table_graph_v1(
        [page], _component_owner_spec(layouts=["ROLES_AS_COLUMNS"])
    )

    assert result["graphs"] == []
    assert result["unresolved_fragments"] == []
    assert all(
        item["population_scope"]["scope_id"] != "EXACT_CUSTOMER_LOANS"
        for item in result["physical_segments"]
    )
    assert len(result["bounded_absences"]) == 1
    absence = result["bounded_absences"][0]
    assert absence["population_scope"]["scope_id"] == "BROAD_MIXED_LOAN_POPULATION"
    assert absence["population_scope"]["match"]["source_line_indices_in_visual_order"] == [
        6,
        8,
    ]


def test_actual_multilevel_lane_leaf_resolves_customer_without_sibling_mixed_veto() -> None:
    page = {
        "lines": [
            _line(
                10,
                "Mức độ tập trung theo khu vực địa lý của tài sản, công nợ và các khoản mục ngoại bảng",
                [373, 347, 1550, 382],
            ),
            _line(11, "Tại ngày 31 tháng 12 năm 2025:", [373, 411, 778, 445]),
            _line(12, "Tổng tiền gửi, cho", [951, 473, 1180, 507]),
            _line(13, "Tổng nợ cho vay vay tại NHNN và các", [675, 500, 1185, 544]),
            _line(14, "Cam kết", [1506, 502, 1621, 539]),
            _line(15, "Công cụ tài", [1699, 505, 1855, 539]),
            _line(16, "Kinh doanh và đầu", [1867, 502, 2111, 537]),
            _line(17, "khách hàng", [739, 539, 892, 573]),
            _line(18, "TCTD khác hoạt động mua nợ", [1034, 539, 1433, 573]),
            _line(19, "ngoại bảng", [1470, 539, 1621, 573]),
            _line(20, "chính phái sinh", [1648, 537, 1848, 571]),
            _line(21, "tư chứng khoán", [1904, 537, 2113, 571]),
            _line(22, "triệu đồng", [756, 569, 890, 605]),
            _line(23, "triệu đồng", [1046, 569, 1182, 605]),
            _line(24, "triệu đồng", [1297, 569, 1431, 605]),
            _line(25, "triệu đồng", [1484, 569, 1618, 605]),
            _line(26, "triệu đồng", [1711, 569, 1848, 605]),
            _line(27, "triệu đồng", [1977, 569, 2111, 605]),
            _line(28, "Trong nước", [383, 623, 541, 660]),
            _line(29, "1.074.688.741", [704, 623, 892, 657], "1.074.688.741"),
            _line(30, "248.005.231", [1016, 623, 1180, 657], "248.005.231"),
            _line(31, "2.465.314", [1297, 623, 1433, 657], "2.465.314"),
            _line(35, "Nước ngoài", [385, 655, 541, 692]),
            _line(36, "9.330.629", [758, 655, 892, 689], "9.330.629"),
            _line(37, "3.422.017", [1046, 655, 1182, 689], "3.422.017"),
        ],
        "page_height": 2_300,
        "page_sequence": 91,
        "page_width": 2_200,
    }

    result = build_accounting_scoped_table_graph_v1(
        [page], _component_owner_spec(layouts=["ROLES_AS_ROWS"])
    )

    exact = [
        item
        for item in result["physical_segments"]
        if item["population_scope"]["scope_id"] == "EXACT_CUSTOMER_LOANS"
    ]
    assert len(exact) == 1
    segment = exact[0]
    assert segment["population_scope"]["match"]["source_line_indices_in_visual_order"] == [
        13,
        17,
    ]
    assert segment["population_scope"]["match"]["lane_axis_center_x2"] == 1_646
    assert [item["source_line_index"] for item in segment["role_cells"]] == [29, 36]
    assert segment["period_key"] == "31/12/2025"
    assert result["matcher_metrics"]["lane_approximate_alias_comparison_count"] > 0
    assert (
        result["matcher_metrics"]["approximate_alias_comparison_count"]
        >= result["matcher_metrics"]["lane_approximate_alias_comparison_count"]
    )


def _same_page_repeated_row_blocks(*, second_period: str = "31/12/2024") -> dict[str, object]:
    return _page(
        1,
        [
            *_owner_lines(500),
            _line(1, "31/12/2025", [650, 82, 810, 108]),
            _line(2, "Cho vay khách hàng", [650, 130, 835, 158]),
            _line(3, "triệu đồng", [660, 170, 805, 198]),
            _line(4, "Trong nước", [40, 220, 190, 248]),
            _line(5, "1.000", [685, 220, 755, 248], "1.000"),
            _line(6, "Nước ngoài", [40, 270, 190, 298]),
            _line(7, "100", [685, 270, 755, 298], "100"),
            _line(8, "Tổng cộng", [40, 320, 190, 348]),
            _line(9, "1.100", [685, 320, 755, 348], "1.100"),
            _line(10, second_period, [650, 362, 810, 388]),
            _line(11, "Cho vay khách hàng", [650, 400, 835, 428]),
            _line(12, "triệu đồng", [660, 432, 805, 458]),
            _line(13, "Trong nước", [40, 470, 190, 498]),
            _line(14, "900", [685, 470, 755, 498], "900"),
            _line(15, "Nước ngoài", [40, 520, 190, 548]),
            _line(16, "90", [685, 520, 755, 548], "90"),
            _line(17, "Tổng cộng", [40, 570, 190, 598]),
            _line(18, "990", [685, 570, 755, 598], "990"),
        ],
    )


def _unlabeled_complete_total_page(
    *,
    numeric_column_count: int = 5,
    target_bbox: list[int] | None = None,
    target_surface: str = "1.100",
) -> dict[str, object]:
    target_bbox = target_bbox or [640, 310, 720, 338]
    target_center = (target_bbox[0] + target_bbox[2]) // 2
    total_top = target_bbox[1]
    row_height = target_bbox[3] - target_bbox[1]
    foreign_bottom = total_top - max(2, row_height // 3)
    foreign_top = foreign_bottom - row_height
    domestic_bottom = foreign_top - max(8, row_height // 2)
    domestic_top = domestic_bottom - row_height
    owner_top = max(20, domestic_top - 250)
    period_top = max(owner_top + 62, domestic_top - 190)
    scope_top = max(period_top + 38, domestic_top - 140)
    unit_top = max(scope_top + 40, domestic_top - 90)
    target_lane = numeric_column_count // 2
    axis_centers = [
        target_center + (lane - target_lane) * 180 for lane in range(numeric_column_count)
    ]
    width = min(130, max(50, target_bbox[2] - target_bbox[0]))
    lines: list[dict[str, object]] = [
        _line(
            90,
            "Mức độ tập trung tài sản và công nợ",
            [20, owner_top, 610, owner_top + 26],
        ),
        _line(3, "theo khu vực địa lý", [20, owner_top + 30, 310, owner_top + 56]),
        _line(
            88,
            "31/12/2025",
            [target_center - 100, period_top, target_center + 100, period_top + 26],
        ),
        _line(
            11,
            "Cho vay khách hàng",
            [target_center - 110, scope_top, target_center + 110, scope_top + 28],
        ),
        _line(
            14,
            "triệu đồng",
            [target_center - 90, unit_top, target_center + 90, unit_top + 28],
        ),
        _line(4, "Trong nước", [40, domestic_top, 190, domestic_bottom]),
        _line(7, "Nước ngoài", [40, foreign_top, 190, foreign_bottom]),
    ]
    for lane, center in enumerate(axis_centers):
        left = center - width // 2
        right = center + width // 2
        lines.extend(
            [
                _line(20 + lane, str(1_000 + lane), [left, domestic_top, right, domestic_bottom]),
                _line(30 + lane, str(100 + lane), [left, foreign_top, right, foreign_bottom]),
                _line(
                    40 + lane,
                    target_surface if lane == target_lane else str(1_100 + lane),
                    target_bbox
                    if lane == target_lane
                    else [left, total_top, right, target_bbox[3]],
                ),
            ]
        )
    return {
        "lines": list(reversed(lines)),
        "page_height": max(1_000, target_bbox[3] + 100),
        "page_sequence": 1,
        "page_width": max(1_500, axis_centers[-1] + width),
    }


def test_numeric_only_complete_total_row_is_bound_without_inventing_a_label() -> None:
    result = build_accounting_scoped_table_graph_v1(
        [_unlabeled_complete_total_page()], _spec(layouts=["ROLES_AS_ROWS"])
    )

    assert len(result["graphs"]) == 1
    segment = result["graphs"][0]["segments"][0]
    assert segment["trailing_total_match"] is None
    resolution = segment["trailing_total_resolution"]
    assert resolution["mode"] == "UNLABELED_COMPLETE_NUMERIC_TOTAL_ROW"
    assert resolution["row_bbox"] == [280, 310, 1080, 338]
    assert resolution["target_body_axis_ordinal"] == 2
    assert resolution["target_role_cell_axis_center_x2"] == 1_360
    assert resolution["target_role_cell_source_ordinals"] == [0, 1]
    assert {item["value_axis_center_x2"] for item in segment["role_cells"]} == {1_360}
    assert [item["source_line_index"] for item in resolution["row_evidence"]] == [
        40,
        41,
        42,
        43,
        44,
    ]
    assert [item["vietocr_raw_nfc_surface"] for item in segment["trailing_total_cells"]] == [
        "1.100"
    ]


@pytest.mark.parametrize(
    ("column_count", "target_bbox"),
    [
        (3, [640, 310, 720, 338]),
        (9, [1_040, 310, 1_120, 338]),
    ],
)
def test_unlabeled_total_quorum_is_declarative_for_other_table_families(
    column_count: int, target_bbox: list[int]
) -> None:
    spec = _spec(
        layouts=["ROLES_AS_ROWS"],
        unlabeled_min=column_count,
        unlabeled_max=column_count,
    )
    page = _unlabeled_complete_total_page(
        numeric_column_count=column_count,
        target_bbox=target_bbox,
    )

    result = build_accounting_scoped_table_graph_v1([page], spec)

    segment = result["graphs"][0]["segments"][0]
    resolution = segment["trailing_total_resolution"]
    assert len(resolution["body_axis_centers_x2"]) == column_count
    assert len(resolution["row_evidence"]) == column_count
    assert resolution["target_body_axis_ordinal"] == column_count // 2


def test_unlabeled_total_gap_is_declarative_for_other_table_families() -> None:
    page = _unlabeled_complete_total_page()
    for line in page["lines"]:
        if 40 <= line["source_line_index"] <= 44:
            line["bbox"][1] += 15
            line["bbox"][3] += 15

    accepted = build_accounting_scoped_table_graph_v1(
        [page], _spec(layouts=["ROLES_AS_ROWS"], unlabeled_gap=2)
    )
    rejected = build_accounting_scoped_table_graph_v1(
        [page], _spec(layouts=["ROLES_AS_ROWS"], unlabeled_gap=1)
    )

    assert accepted["graphs"][0]["segments"][0]["trailing_total_resolution"] is not None
    assert rejected["graphs"][0]["segments"][0]["trailing_total_resolution"] is None


@pytest.mark.parametrize(("shift", "accepted"), [(24, True), (25, False)])
def test_unlabeled_total_gap_jitter_has_one_closed_bbox_boundary(
    shift: int, accepted: bool
) -> None:
    page = _unlabeled_complete_total_page()
    for line in page["lines"]:
        if 40 <= line["source_line_index"] <= 44:
            line["bbox"][1] += shift
            line["bbox"][3] += shift

    result = build_accounting_scoped_table_graph_v1(
        [page],
        _spec(
            layouts=["ROLES_AS_ROWS"],
            unlabeled_gap=2,
            unlabeled_jitter_ppm=200_000,
        ),
    )

    resolution = result["graphs"][0]["segments"][0]["trailing_total_resolution"]
    assert (resolution is not None) is accepted


def test_structural_stop_before_remains_exact_with_gap_jitter() -> None:
    page = _unlabeled_complete_total_page()
    for line in page["lines"]:
        if 40 <= line["source_line_index"] <= 44:
            line["bbox"][1] += 24
            line["bbox"][3] += 24
    # The candidate row ends at y=362.  This reset starts exactly one pixel
    # before it and must fence the row even though the role-gap jitter admits it.
    page["lines"].append(_line(85, "Thuyết minh khác", [20, 361, 250, 387]))

    result = build_accounting_scoped_table_graph_v1(
        [page], _spec(layouts=["ROLES_AS_ROWS"], unlabeled_jitter_ppm=200_000)
    )

    segment = result["graphs"][0]["segments"][0]
    assert segment["trailing_total_resolution"] is None
    assert segment["trailing_total_cells"] == []


@pytest.mark.parametrize(
    ("header", "top", "bottom"),
    [
        ("Bảng phân tích hoàn toàn khác", 303, 316),
        ("Mức độ tập trung tài sản và", 303, 316),
        ("1", 303, 316),
        ("Bảng phân tích hoàn toàn khác", 301, 316),
        ("Bảng phân tích hoàn toàn khác", 300, 316),
        ("Bảng phân tích hoàn toàn khác", 303, 321),
        ("Bảng phân tích hoàn toàn khác", 303, 324),
    ],
)
def test_tight_intervening_visible_line_fences_following_complete_numeric_row(
    header: str, top: int, bottom: int
) -> None:
    page = _unlabeled_complete_total_page()
    for line in page["lines"]:
        if 40 <= line["source_line_index"] <= 44:
            line["bbox"][1] += 10
            line["bbox"][3] += 10
    page["lines"].append(_line(85, header, [20, top, 250, bottom]))

    result = build_accounting_scoped_table_graph_v1([page], _spec(layouts=["ROLES_AS_ROWS"]))

    segment = result["graphs"][0]["segments"][0]
    assert segment["trailing_total_match"] is None
    assert segment["trailing_total_resolution"] is None
    assert segment["trailing_total_cells"] == []


def test_ordinary_tight_spacing_and_empty_visual_decoration_preserve_total_row() -> None:
    spec = _spec(layouts=["ROLES_AS_ROWS"])
    ordinary = _unlabeled_complete_total_page()
    decorated = _unlabeled_complete_total_page()
    for page in (ordinary, decorated):
        for line in page["lines"]:
            if 40 <= line["source_line_index"] <= 44:
                line["bbox"][1] += 10
                line["bbox"][3] += 10
    decorated["lines"].append(_line(85, "", [20, 303, 250, 316]))

    ordinary_result = build_accounting_scoped_table_graph_v1([ordinary], spec)
    decorated_result = build_accounting_scoped_table_graph_v1([decorated], spec)

    assert ordinary_result["graphs"][0]["segments"][0]["trailing_total_resolution"] is not None
    assert decorated_result["graphs"][0]["segments"][0]["trailing_total_resolution"] is not None


def test_proven_role_body_value_jitter_is_not_an_intervening_row() -> None:
    page = _unlabeled_complete_total_page()
    for line in page["lines"]:
        if 40 <= line["source_line_index"] <= 44:
            line["bbox"][1] += 10
            line["bbox"][3] += 10
    foreign_body_value = next(line for line in page["lines"] if line["source_line_index"] == 30)
    foreign_body_value["bbox"][3] += 2

    result = build_accounting_scoped_table_graph_v1([page], _spec(layouts=["ROLES_AS_ROWS"]))

    assert result["graphs"][0]["segments"][0]["trailing_total_resolution"] is not None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("unlabeled_total_min_numeric_columns", True),
        ("unlabeled_total_max_numeric_columns", True),
        ("unlabeled_total_max_gap_lines", True),
        ("unlabeled_total_gap_jitter_ppm", True),
        ("unlabeled_total_min_numeric_columns", 1),
        ("unlabeled_total_max_numeric_columns", 33),
        ("unlabeled_total_max_gap_lines", 0),
        ("unlabeled_total_max_gap_lines", 9),
        ("unlabeled_total_gap_jitter_ppm", -1),
        ("unlabeled_total_gap_jitter_ppm", 500_001),
    ],
)
def test_unlabeled_total_limits_reject_bool_or_values_outside_closed_bounds(
    field: str, value: object
) -> None:
    spec = _spec(layouts=["ROLES_AS_ROWS"])
    spec["limits"][field] = value

    with pytest.raises(
        AccountingScopedTableGraphV1Error,
        match="limits exceed|positive.*integer|nonnegative.*integer",
    ):
        build_accounting_scoped_table_graph_v1([_row_layout_page()], spec)


def test_unlabeled_total_limit_axis_requires_all_fields_and_ordered_quorum() -> None:
    for field in ("unlabeled_total_max_gap_lines", "unlabeled_total_gap_jitter_ppm"):
        missing = _spec(layouts=["ROLES_AS_ROWS"])
        missing["limits"].pop(field)
        with pytest.raises(AccountingScopedTableGraphV1Error, match="limits drifted"):
            build_accounting_scoped_table_graph_v1([_row_layout_page()], missing)

    reversed_quorum = _spec(layouts=["ROLES_AS_ROWS"], unlabeled_min=9, unlabeled_max=8)
    with pytest.raises(AccountingScopedTableGraphV1Error, match="limits exceed"):
        build_accounting_scoped_table_graph_v1([_row_layout_page()], reversed_quorum)


@pytest.mark.parametrize(
    ("target_bbox", "surface"),
    [
        ([780, 756, 943, 791], "686.777.352"),
        ([775, 1187, 938, 1222], "580.686.248"),
        ([750, 785, 911, 818], "633.748.683"),
        ([748, 1215, 908, 1248], "580.686.248"),
        ([730, 785, 892, 818], "619.850.276"),
        ([728, 1215, 890, 1248], "569.734.624"),
        ([704, 706, 892, 741], "1.084.019.370"),
        ([726, 1076, 892, 1110], "776.657.846"),
        ([912, 731, 1092, 758], "1.031.103.706"),
        ([931, 1105, 1094, 1132], "734.594.094"),
        ([739, 706, 899, 733], "879.888.513"),
        ([736, 1071, 902, 1105], "776.657.846"),
        ([926, 726, 1092, 761], "830.744.526"),
        ([926, 1098, 1092, 1132], "734.594.094"),
        ([726, 719, 912, 753], "1.227.554.477"),
        ([724, 1088, 912, 1122], "1.084.019.370"),
        ([890, 719, 1075, 753], "1.172.763.521"),
        ([892, 1130, 1072, 1157], "1.031.103.706"),
    ],
)
def test_observed_local_total_bbox_and_raw_surface_variants_are_retained(
    target_bbox: list[int], surface: str
) -> None:
    result = build_accounting_scoped_table_graph_v1(
        [_unlabeled_complete_total_page(target_bbox=target_bbox, target_surface=surface)],
        _spec(layouts=["ROLES_AS_ROWS"]),
    )

    assert len(result["graphs"]) == 1
    segment = result["graphs"][0]["segments"][0]
    total = segment["trailing_total_cells"]
    assert len(total) == 1
    assert total[0]["bbox"] == target_bbox
    assert total[0]["vietocr_raw_nfc_surface"] == surface
    assert segment["trailing_total_resolution"]["row_evidence"][2]["bbox"] == target_bbox


def test_unlabeled_total_geometry_rejects_labels_incomplete_or_competing_rows() -> None:
    spec = _spec(layouts=["ROLES_AS_ROWS"])

    labeled = _unlabeled_complete_total_page()
    labeled["lines"].append(_line(60, "Diễn giải", [20, 310, 190, 338]))
    labeled_result = build_accounting_scoped_table_graph_v1([labeled], spec)
    assert labeled_result["graphs"][0]["segments"][0]["trailing_total_cells"] == []

    incomplete = _unlabeled_complete_total_page()
    incomplete["lines"] = [
        line for line in incomplete["lines"] if line["source_line_index"] not in {40, 41, 43, 44}
    ]
    incomplete_result = build_accounting_scoped_table_graph_v1([incomplete], spec)
    assert incomplete_result["graphs"][0]["segments"][0]["trailing_total_cells"] == []

    dash = _unlabeled_complete_total_page()
    next(line for line in dash["lines"] if line["source_line_index"] == 41)["vietocr_text"] = "-"
    dash_result = build_accounting_scoped_table_graph_v1([dash], spec)
    assert dash_result["graphs"][0]["segments"][0]["trailing_total_cells"] == []

    blank = _unlabeled_complete_total_page()
    next(line for line in blank["lines"] if line["source_line_index"] == 41)["vietocr_text"] = ""
    blank_result = build_accounting_scoped_table_graph_v1([blank], spec)
    assert blank_result["graphs"][0]["segments"][0]["trailing_total_cells"] == []

    drift = _unlabeled_complete_total_page()
    shifted = next(line for line in drift["lines"] if line["source_line_index"] == 44)
    shifted["bbox"][0] += 90
    shifted["bbox"][2] += 90
    drift_result = build_accounting_scoped_table_graph_v1([drift], spec)
    assert drift_result["graphs"][0]["segments"][0]["trailing_total_cells"] == []

    competing = _unlabeled_complete_total_page()
    for lane, line in enumerate(
        sorted(
            [item for item in competing["lines"] if 40 <= item["source_line_index"] <= 44],
            key=lambda item: item["bbox"][0],
        )
    ):
        competing["lines"].append(
            _line(70 + lane, str(2_000 + lane), [line["bbox"][0], 332, line["bbox"][2], 356])
        )
    competing_result = build_accounting_scoped_table_graph_v1([competing], spec)
    assert competing_result["graphs"][0]["segments"][0]["trailing_total_cells"] == []

    duplicate_target = _unlabeled_complete_total_page()
    duplicate_target["lines"].append(_line(81, "Cho vay khách hàng", [850, 120, 1070, 148]))
    duplicate_result = build_accounting_scoped_table_graph_v1([duplicate_target], spec)
    assert all(
        item["trailing_total_resolution"] is None
        for item in duplicate_result["physical_segments"]
        if item["population_scope"]["disposition"] == "TARGET"
    )


def test_missing_current_total_does_not_borrow_next_period_unlabeled_row() -> None:
    lines: list[dict[str, object]] = [
        *_owner_lines(900),
        _line(1, "31/12/2025", [650, 82, 810, 108]),
        _line(2, "Cho vay khách hàng", [570, 120, 790, 148]),
        _line(3, "triệu đồng", [650, 160, 810, 188]),
        _line(4, "Trong nước", [40, 220, 190, 248]),
        _line(5, "Nước ngoài", [40, 270, 190, 298]),
        _line(20, "31/12/2024", [650, 322, 810, 348]),
        _line(21, "Cho vay khách hàng", [570, 360, 790, 388]),
        _line(22, "triệu đồng", [650, 400, 810, 428]),
        _line(23, "Trong nước", [40, 460, 190, 488]),
        _line(24, "Nước ngoài", [40, 510, 190, 538]),
    ]
    for lane, center in enumerate([320, 500, 680, 860, 1040]):
        left, right = center - 55, center + 55
        lines.extend(
            [
                _line(30 + lane, str(1_000 + lane), [left, 220, right, 248]),
                _line(40 + lane, str(100 + lane), [left, 270, right, 298]),
                _line(50 + lane, str(900 + lane), [left, 460, right, 488]),
                _line(60 + lane, str(90 + lane), [left, 510, right, 538]),
                _line(70 + lane, str(990 + lane), [left, 550, right, 578]),
            ]
        )
    page = _page(1, list(reversed(lines)))
    page["page_width"] = 1_300
    spec = _spec(layouts=["ROLES_AS_ROWS"])
    spec["limits"]["max_role_gap_lines"] = 6

    result = build_accounting_scoped_table_graph_v1([page], spec)

    assert len(result["graphs"]) == 1
    assert len(result["graphs"][0]["segments"]) == 2
    current, comparative = result["graphs"][0]["segments"]
    assert current["period_key"] == "31/12/2025"
    assert current["trailing_total_match"] is None
    assert current["trailing_total_resolution"] is None
    assert current["trailing_total_cells"] == []
    assert comparative["period_key"] == "31/12/2024"
    assert comparative["trailing_total_resolution"]["mode"] == (
        "UNLABELED_COMPLETE_NUMERIC_TOTAL_ROW"
    )


@pytest.mark.parametrize(
    ("surface", "bbox"),
    [
        ("31/12/2024", [300, 303, 500, 329]),
        ("triệu đồng", [300, 303, 500, 329]),
        ("Thuyết minh khác", [20, 303, 250, 329]),
        ("Mức độ tập trung tài sản và công nợ", [20, 303, 610, 329]),
    ],
)
def test_next_header_or_structural_boundary_fences_unlabeled_total(
    surface: str, bbox: list[int]
) -> None:
    page = _unlabeled_complete_total_page()
    for line in page["lines"]:
        if 40 <= line["source_line_index"] <= 44:
            line["bbox"][1] += 35
            line["bbox"][3] += 35
    page["lines"].append(_line(80, surface, bbox))

    result = build_accounting_scoped_table_graph_v1([page], _spec(layouts=["ROLES_AS_ROWS"]))

    assert result["graphs"][0]["segments"][0]["trailing_total_cells"] == []


def test_same_page_repeated_full_blocks_group_only_for_distinct_compatible_periods() -> None:
    spec = _spec(layouts=["ROLES_AS_ROWS"])
    spec["limits"]["max_role_gap_lines"] = 4
    result = build_accounting_scoped_table_graph_v1([_same_page_repeated_row_blocks()], spec)

    assert len(result["graphs"]) == 1
    assert result["graphs"][0]["continuation"]["mode"] == (
        "SINGLE_PAGE_MULTI_PERIOD_COMPLETE_SEGMENTS"
    )
    assert [item["period_key"] for item in result["graphs"][0]["segments"]] == [
        "31/12/2025",
        "31/12/2024",
    ]
    current = result["graphs"][0]["segments"][0]
    assert current["trailing_total_match"]["source_line_indices_in_visual_order"] == [8]

    duplicate = build_accounting_scoped_table_graph_v1(
        [_same_page_repeated_row_blocks(second_period="31/12/2025")], spec
    )
    assert len(duplicate["graphs"]) == 2

    unit_conflict_page = _same_page_repeated_row_blocks()
    next(line for line in unit_conflict_page["lines"] if line["source_line_index"] == 12)[
        "vietocr_text"
    ] = "nghìn đồng"
    unit_conflict = build_accounting_scoped_table_graph_v1([unit_conflict_page], spec)
    assert len(unit_conflict["graphs"]) == 2

    axis_drift_page = _same_page_repeated_row_blocks()
    for line in axis_drift_page["lines"]:
        if line["source_line_index"] in {10, 11, 12, 14, 16, 18}:
            line["bbox"][0] -= 200
            line["bbox"][2] -= 200
    axis_drift = build_accounting_scoped_table_graph_v1([axis_drift_page], spec)
    assert len(axis_drift["graphs"]) == 2

    role_axis_drift_page = _same_page_repeated_row_blocks()
    for line in role_axis_drift_page["lines"]:
        if line["source_line_index"] in {13, 15}:
            line["bbox"][0] += 100
            line["bbox"][2] += 100
    role_axis_drift = build_accounting_scoped_table_graph_v1([role_axis_drift_page], spec)
    assert len(role_axis_drift["graphs"]) == 1
    assert len(role_axis_drift["graphs"][0]["segments"]) == 1

    distant_page = _same_page_repeated_row_blocks()
    for line in distant_page["lines"]:
        if 10 <= line["source_line_index"] <= 18:
            line["bbox"][1] += 300
            line["bbox"][3] += 300
    distant = build_accounting_scoped_table_graph_v1([distant_page], spec)
    assert len(distant["graphs"]) == 1
    assert len(distant["graphs"][0]["segments"]) == 1

    reset_page = _same_page_repeated_row_blocks()
    reset_page["lines"].append(_line(30, "Thuyết minh khác", [20, 350, 300, 378]))
    reset = build_accounting_scoped_table_graph_v1([reset_page], spec)
    assert len(reset["graphs"]) == 1
    assert len(reset["graphs"][0]["segments"]) == 1

    unrelated_page = _same_page_repeated_row_blocks()
    unrelated_page["lines"].extend(
        [
            _line(31, "Mức độ tập trung tài sản và công nợ", [20, 304, 610, 330]),
            _line(32, "theo khu vực địa lý", [20, 332, 310, 358]),
        ]
    )
    unrelated = build_accounting_scoped_table_graph_v1([unrelated_page], spec)
    assert len(unrelated["graphs"]) == 2


def test_inherited_repeated_block_owner_keeps_noisy_leaf_on_verified_header_path() -> None:
    page = _same_page_repeated_row_blocks()
    for line in page["lines"]:
        if line["source_line_index"] == 11:
            line["vietocr_text"] = "Tổng nợ cho vay"
        elif line["source_line_index"] == 12:
            line["bbox"] = [660, 460, 805, 486]
        elif line["source_line_index"] in {13, 14, 15, 16, 17, 18}:
            line["bbox"][1] += 50
            line["bbox"][3] += 50
    page["lines"].append(
        _line(
            19,
            "? khách hạng",
            [650, 430, 835, 456],
            "KHÔNG ĐƯỢC DÙNG LÀM SEMANTIC",
        )
    )
    spec = _component_owner_spec(layouts=["ROLES_AS_ROWS"])
    spec["limits"]["max_role_gap_lines"] = 4

    result = build_accounting_scoped_table_graph_v1([page], spec)

    assert len(result["graphs"]) == 1
    graph = result["graphs"][0]
    assert len(graph["segments"]) == 2
    comparative = next(item for item in graph["segments"] if item["period_key"] == "31/12/2024")
    match = comparative["population_scope"]["match"]
    assert match["scope_resolution"] == (
        "MULTILEVEL_HEADER_GRAPH_ANCESTOR_PATH_AND_DEEPEST_LANE_LEAF"
    )
    assert match["header_leaf_source_line_indices"] == [19]
    assert match["surface_raw_nfc"] == "Tổng nợ cho vay ? khách hạng"
    assert "KHÔNG ĐƯỢC DÙNG" not in match["surface_raw_nfc"]


def test_prior_row_block_does_not_borrow_next_block_total_column_header() -> None:
    page = _same_page_repeated_row_blocks()
    page["lines"] = [line for line in page["lines"] if line["source_line_index"] not in {8, 9}]
    page["lines"].append(_line(20, "Tổng cộng", [850, 396, 990, 424]))
    spec = _spec(layouts=["ROLES_AS_ROWS"])
    spec["limits"]["max_role_gap_lines"] = 10

    result = build_accounting_scoped_table_graph_v1([page], spec)

    assert len(result["graphs"]) == 1
    assert len(result["graphs"][0]["segments"]) == 2
    current = next(
        item for item in result["graphs"][0]["segments"] if item["period_key"] == "31/12/2025"
    )
    assert current["trailing_total_match"] is None


def test_stacked_transposed_blocks_fence_each_scope_before_the_next_role_header() -> None:
    page = _page(
        1,
        [
            *_owner_lines(700),
            _line(1, "31/12/2025", [350, 82, 510, 108]),
            _line(2, "Trong nước", [570, 120, 710, 148]),
            _line(3, "Nước ngoài", [750, 120, 890, 148]),
            _line(4, "Tổng cộng", [920, 120, 995, 148]),
            _line(5, "triệu đồng", [570, 152, 710, 178]),
            _line(6, "Tổng dư nợ cho vay", [30, 204, 300, 232]),
            _line(7, "900", [595, 204, 665, 232], "900"),
            _line(8, "800", [775, 204, 845, 232], "800"),
            _line(9, "1.700", [930, 204, 990, 232], "1.700"),
            _line(10, "31/12/2024", [350, 362, 510, 388]),
            _line(11, "Trong nước", [570, 400, 710, 428]),
            _line(12, "Nước ngoài", [750, 400, 890, 428]),
            _line(13, "Tổng cộng", [920, 400, 995, 428]),
            _line(14, "triệu đồng", [570, 432, 710, 458]),
            _line(15, "Tổng dư nợ cho vay", [30, 484, 300, 512]),
            _line(16, "700", [595, 484, 665, 512], "700"),
            _line(17, "600", [775, 484, 845, 512], "600"),
            _line(18, "1.300", [930, 484, 990, 512], "1.300"),
        ],
    )

    result = build_accounting_scoped_table_graph_v1([page], _spec(layouts=["ROLES_AS_COLUMNS"]))

    assert len(result["bounded_absences"]) == 2
    assert result["metrics"]["physical_segment_count"] == 2
    assert [
        item["population_scope"]["match"]["source_line_indices_in_visual_order"]
        for item in result["bounded_absences"]
    ] == [[6], [15]]
