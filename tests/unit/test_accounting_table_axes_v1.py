from __future__ import annotations

from decimal import Decimal

import pytest

from bctc_ai.evaluation.accounting_table_axes_v1 import (
    AccountingTableAxesV1Error,
    accounting_unit_surface_v1,
    center_x2_v1,
    extract_period_axis_v1,
    extract_period_observations_v1,
    extract_reporting_year_axis_v1,
    extract_row_aligned_typed_value_vector_v1,
    extract_typed_value_vector_v1,
    infer_document_accounting_unit_context_v1,
    infer_document_reporting_period_context_v1,
    is_accounting_value_surface_v1,
    is_number_like_v1,
    is_period_axis_candidate_line_v1,
    money_integer_v1,
    money_values_v1,
    percentage_values_v1,
    resolve_relative_period_axis_v1,
    unit_kind_v1,
)


def _line(
    index: int,
    text: str,
    x1: int,
    *,
    source_text: str | None = None,
    numeric_text: str | None = None,
    numeric_score: float = 0.99,
) -> dict[str, object]:
    result: dict[str, object] = {
        "bbox": [x1, 10, x1 + 80, 30],
        "source_line_index": index,
        "vietocr_text": text,
    }
    if source_text is not None:
        result["source_text"] = source_text
    if numeric_text is not None:
        result["numeric_text"] = numeric_text
        result["numeric_score"] = numeric_score
    return result


def _page(page_sequence: int, *lines: dict[str, object]) -> dict[str, object]:
    return {"lines": list(lines), "page_sequence": page_sequence}


@pytest.mark.parametrize(
    ("surface", "expected"),
    [
        ("31/12/2025", True),
        ("Ngày 31 tháng", True),
        ("12 năm 2025", True),
        ("Số cuối kỳ", True),
        ("Năm 2025", True),
        ("Cho vay khách hàng", False),
        ("1.234.567", False),
    ],
)
def test_period_axis_candidate_line_is_grammar_only(surface: str, expected: bool) -> None:
    assert is_period_axis_candidate_line_v1(_line(3, surface, 10)) is expected


def test_period_axis_supports_exact_split_and_relative_variants() -> None:
    exact, exact_kind = extract_period_axis_v1(
        [_line(7, "31/12/2025", 300), _line(6, "30/06/2026", 100)]
    )
    assert exact_kind == "LOCAL_EXACT_DATES"
    assert [item["period"] for item in exact] == ["30/06/2026", "31/12/2025"]
    assert [item["evidence_source_line_indices"] for item in exact] == [[6], [7]]

    vietnamese_full, vietnamese_full_kind = extract_period_axis_v1(
        [
            _line(13, "Tại ngày 31 tháng 12 năm 2025", 100),
            _line(12, "Tại ngày 30 tháng 06 năm 2026", 100),
        ]
    )
    assert vietnamese_full_kind == "LOCAL_EXACT_DATES"
    assert [item["period"] for item in vietnamese_full] == [
        "31/12/2025",
        "30/06/2026",
    ]

    split, split_kind = extract_period_axis_v1(
        [
            _line(11, "Năm 2025", 320),
            _line(8, "Ngày 30 tháng 06", 100),
            _line(10, "Ngày 31 tháng 12", 300),
            _line(9, "Năm 2026", 120),
        ]
    )
    assert split_kind == "LOCAL_SPLIT_DATES"
    assert [item["period"] for item in split] == ["30/06/2026", "31/12/2025"]
    assert [item["evidence_source_line_indices"] for item in split] == [
        [8, 9],
        [10, 11],
    ]

    relative, relative_kind = extract_period_axis_v1(
        [_line(4, "Số đầu kỳ", 300), _line(3, "Số cuối kỳ", 100)]
    )
    assert relative_kind == "LOCAL_RELATIVE_PERIOD_ROLES"
    assert [item["period"] for item in relative] == [
        "CURRENT_PERIOD_END",
        "COMPARATIVE_PERIOD_START",
    ]


def test_period_axis_joins_day_only_and_month_year_header_fragments() -> None:
    axis, mode = extract_period_axis_v1(
        [
            _line(4, "Ngày 31 tháng 03 năm 2025", 100),
            _line(5, "Ngày 31 tháng", 300),
            _line(6, "12 năm 2024", 300),
        ]
    )

    assert mode == "LOCAL_SPLIT_DATES"
    assert [item["period"] for item in axis] == ["31/03/2025", "31/12/2024"]
    assert axis[1]["evidence_source_line_indices"] == [5, 6]

    interleaved, interleaved_mode = extract_period_axis_v1(
        [
            _line(57, "Ngày 30 tháng 9", 100),
            _line(58, "Ngày 31 tháng 12", 300),
            _line(59, "0", 800),
            _line(60, "IN", 800),
            _line(61, "năm 2025", 100),
            _line(62, "năm 2024", 300),
        ]
    )
    assert interleaved_mode == "LOCAL_SPLIT_DATES"
    assert [item["period"] for item in interleaved] == ["30/09/2025", "31/12/2024"]


def test_period_axis_accepts_bounded_restatement_qualifier() -> None:
    axis, mode = extract_period_axis_v1(
        [
            _line(7, "Số cuối năm", 100),
            _line(8, "Số đầu năm (Trình bày lại)", 300),
        ]
    )

    assert mode == "LOCAL_RELATIVE_PERIOD_ROLES"
    assert [item["period"] for item in axis] == [
        "CURRENT_PERIOD_END",
        "COMPARATIVE_PERIOD_START",
    ]


def test_period_axis_fails_closed_on_invalid_or_ambiguous_headers() -> None:
    assert extract_period_axis_v1([_line(1, "31/13/2025", 100), _line(2, "30/06/2026", 300)]) == (
        [],
        "UNRESOLVED",
    )
    assert extract_period_axis_v1(
        [
            _line(1, "30/06/2026", 100),
            _line(2, "31/12/2025", 300),
            _line(3, "31/12/2024", 500),
        ]
    ) == ([], "UNRESOLVED")


def test_period_observations_retain_stacked_exact_split_and_relative_blocks() -> None:
    observations = extract_period_observations_v1(
        [
            _line(3, "Tại ngày 30 tháng 06 năm 2026", 100),
            _line(10, "Ngày 31 tháng 12", 100),
            _line(11, "năm 2025", 100),
            _line(20, "Số cuối kỳ", 100),
        ]
    )
    assert [item["period"] for item in observations] == [
        "30/06/2026",
        "31/12/2025",
        "CURRENT_PERIOD_END",
    ]
    assert [item["evidence_source_line_indices"] for item in observations] == [
        [3],
        [10, 11],
        [20],
    ]


def test_period_observations_join_standalone_year_fragments() -> None:
    observations = extract_period_observations_v1(
        [
            _line(0, "Tại ngày 30 tháng 6 năm", 100),
            _line(1, "2026", 100),
            _line(2, "Giao dịch kỳ hạn tiền tệ", 100),
            _line(3, "Tại ngày 31 tháng 12 năm", 100),
            # One interleaved OCR fragment is allowed by the bounded split
            # join; the year itself must remain one standalone 20xx token.
            _line(4, "3", 900),
            _line(5, "2025", 100),
        ]
    )

    assert [item["period"] for item in observations] == ["30/06/2026", "31/12/2025"]
    assert observations[1]["evidence_source_line_indices"] == [3, 5]


def test_period_axis_uses_high_confidence_numeric_reader_only_for_date_grammar() -> None:
    axis, mode = extract_period_axis_v1(
        [
            _line(8, "81 thang 03", 100, numeric_text="31 tháng 03"),
            _line(11, "2016", 100, numeric_text="năm 2026"),
            _line(6, "31 thang 12", 300, numeric_text="31 tháng 12"),
            _line(9, "202s", 300, numeric_text="năm 2025"),
        ]
    )
    assert mode == "LOCAL_SPLIT_DATES"
    assert [item["period"] for item in axis] == ["31/03/2026", "31/12/2025"]

    low_score, low_score_mode = extract_period_axis_v1(
        [
            _line(1, "B1 tháng 12", 100, numeric_text="31 tháng 12", numeric_score=0.94),
            _line(2, "nam 2025", 100),
            _line(3, "31 tháng 12", 300),
            _line(4, "nam 2024", 300),
        ]
    )
    assert low_score == []
    assert low_score_mode == "UNRESOLVED"

    non_date, non_date_mode = extract_period_axis_v1(
        [
            _line(1, "B1 tháng 12", 100, numeric_text="not a period"),
            _line(2, "nam 2025", 100),
            _line(3, "31 tháng 12", 300),
            _line(4, "nam 2024", 300),
        ]
    )
    assert non_date == []
    assert non_date_mode == "UNRESOLVED"


def test_reporting_year_axis_uses_latest_of_exactly_two_visible_years() -> None:
    axis, mode = extract_reporting_year_axis_v1(
        [_line(7, "31/12/2024", 300), _line(6, "31/12/2025", 100)]
    )

    assert mode == "VISIBLE_TWO_YEAR_REPORTING_AXIS"
    assert [(item["role"], item["year"]) for item in axis] == [
        ("COMPARATIVE_PERIOD", 2024),
        ("CURRENT_PERIOD", 2025),
    ]
    assert extract_reporting_year_axis_v1(
        [
            _line(1, "31/12/2025", 100),
            _line(2, "31/12/2024", 300),
            _line(3, "narrative 2023", 500),
        ]
    ) == ([], "UNRESOLVED")


def test_document_period_context_resolves_annual_variants_and_ignores_one_off_future_date() -> None:
    context = infer_document_reporting_period_context_v1(
        [
            _page(
                1,
                _line(1, "Tại ngày 31/12/2025", 100),
                _line(2, "Tại ngày 31/12/2024", 300),
            ),
            _page(
                2,
                _line(1, "31. 12. 2025", 100),
                _line(2, "31.12.2024", 300),
            ),
            _page(
                3,
                _line(1, "Ngày 31 tháng 12 năm 2025", 100),
                _line(2, "Ngày 31 tháng 12 năm 2024", 300),
            ),
            _page(
                4,
                _line(1, "31-12-2025", 100),
                _line(2, "Ngày 1 tháng 1 năm 2025", 300),
                _line(3, "Ngày 1 tháng 1 năm 2024", 500),
            ),
            _page(5, _line(1, "Báo cáo ký ngày 31/03/2026", 100)),
        ]
    )

    assert context["resolution"] == "DOMINANT_REPEATED_FULL_DATE_CONSENSUS"
    assert context["period_kind"] == "ANNUAL"
    assert context["reporting_year"] == 2025
    assert context["current_period_end"] == "31/12/2025"
    assert context["current_period_start"] == "01/01/2025"
    assert context["balance_comparative_period_end"] == "31/12/2024"
    assert context["flow_comparative_period_end"] == "31/12/2024"
    assert context["flow_comparative_period_start"] == "01/01/2024"
    assert context["supporting_page_count"] == 4


def test_document_period_context_resolves_half_year_balance_and_flow_axes() -> None:
    context = infer_document_reporting_period_context_v1(
        [
            _page(
                1,
                _line(1, "30/06/2026", 100),
                _line(2, "31/12/2025", 300),
            ),
            _page(
                2,
                _line(1, "Ngày 30 tháng 6 năm 2026", 100),
                _line(2, "Ngày 31 tháng 12 năm 2025", 300),
            ),
            _page(
                3,
                _line(1, "30.06.2026", 100),
                _line(2, "30.06.2025", 300),
                _line(3, "01.01.2026", 500),
                _line(4, "01.01.2025", 700),
            ),
        ]
    )

    assert context["period_kind"] == "HALF_YEAR_OR_SECOND_QUARTER"
    assert context["current_period_end"] == "30/06/2026"
    assert context["balance_comparative_period_end"] == "31/12/2025"
    assert context["flow_comparative_period_end"] == "30/06/2025"
    assert context["current_period_start"] == "01/01/2026"
    assert context["flow_comparative_period_start"] == "01/01/2025"


def test_document_period_context_supports_split_dates_and_fails_closed_without_repetition() -> None:
    context = infer_document_reporting_period_context_v1(
        [
            _page(
                1,
                _line(1, "Ngày 31 tháng 12", 100),
                _line(2, "Năm 2025", 100),
            ),
            _page(2, _line(1, "31 tháng 12 năm 2025", 100)),
        ]
    )
    assert context["current_period_end"] == "31/12/2025"
    assert context["supporting_page_count"] == 2

    unresolved = infer_document_reporting_period_context_v1([_page(1, _line(1, "31/12/2025", 100))])
    assert unresolved["resolution"] == "UNRESOLVED_NO_REPEATED_REPORTING_END_DATE"
    assert unresolved["current_period_end"] is None


def test_document_period_context_supports_split_day_and_month_year_fragments() -> None:
    context = infer_document_reporting_period_context_v1(
        [
            _page(
                1,
                _line(1, "Ngày 31 tháng", 100),
                _line(2, "12 năm 2025", 100),
            ),
            _page(2, _line(1, "31/12/2025", 100)),
        ]
    )

    assert context["current_period_end"] == "31/12/2025"
    assert context["supporting_page_count"] == 2


def test_document_period_context_prefers_repeated_numeric_date_challenger() -> None:
    pages = [
        _page(
            page_sequence,
            _line(
                1,
                "Tại ngày 30/06/2626",
                100,
                numeric_text="Tại ngày 30/06/2026",
            ),
            _line(2, "31/12/2025", 300, numeric_text="31/12/2025"),
        )
        for page_sequence in range(1, 4)
    ]
    context = infer_document_reporting_period_context_v1(pages)
    assert context["current_period_end"] == "30/06/2026"
    assert context["balance_comparative_period_end"] == "31/12/2025"


def test_document_period_context_rejects_out_of_domain_systematic_ocr_year_error() -> None:
    pages = [
        _page(
            page_sequence,
            _line(1, "30/06/2026", 100),
            *([_line(2, "30/06/2626", 300)] if page_sequence in {1, 2, 3} else []),
            _line(3, "31/12/2025", 500),
        )
        for page_sequence in range(1, 13)
    ]
    context = infer_document_reporting_period_context_v1(pages)
    assert context["current_period_end"] == "30/06/2026"
    assert context["balance_comparative_period_end"] == "31/12/2025"
    assert context["supporting_page_count"] == 12


def test_document_period_context_rejects_frequent_old_legal_footer_date() -> None:
    pages = [
        _page(
            page_sequence,
            _line(1, "Giấy phép ngày 31/12/2014", 100),
            *([_line(2, "Tại ngày 30/06/2026", 300)] if page_sequence in {5, 6} else []),
            *([_line(3, "Báo cáo ký ngày 31/03/2027", 500)] if page_sequence == 1 else []),
        )
        for page_sequence in range(1, 7)
    ]

    context = infer_document_reporting_period_context_v1(pages)

    assert context["current_period_end"] == "30/06/2026"
    assert context["period_kind"] == "HALF_YEAR_OR_SECOND_QUARTER"
    assert context["supporting_page_count"] == 2


def test_relative_period_axis_uses_declared_balance_or_rollforward_semantics() -> None:
    context = infer_document_reporting_period_context_v1(
        [
            _page(
                1,
                _line(1, "31/12/2025", 100),
                _line(2, "31/12/2024", 300),
                _line(3, "01/01/2025", 500),
            ),
            _page(
                2,
                _line(1, "Ngày 31 tháng 12 năm 2025", 100),
                _line(2, "Ngày 31 tháng 12 năm 2024", 300),
            ),
        ]
    )
    relative_axis, mode = extract_period_axis_v1(
        [_line(7, "Số cuối kỳ", 100), _line(8, "Số đầu kỳ", 300)]
    )
    assert mode == "LOCAL_RELATIVE_PERIOD_ROLES"

    balance, balance_mode = resolve_relative_period_axis_v1(
        relative_axis, context, period_semantics="BALANCE_COMPARATIVE"
    )
    assert balance_mode == "DOCUMENT_CONTEXT_BALANCE_COMPARATIVE"
    assert [(item["resolved_role"], item["resolved_period"]) for item in balance] == [
        ("CURRENT_PERIOD_END", "31/12/2025"),
        ("BALANCE_COMPARATIVE_PERIOD_END", "31/12/2024"),
    ]

    rollforward, rollforward_mode = resolve_relative_period_axis_v1(
        relative_axis, context, period_semantics="CURRENT_ROLLFORWARD"
    )
    assert rollforward_mode == "DOCUMENT_CONTEXT_CURRENT_ROLLFORWARD"
    assert [(item["resolved_role"], item["resolved_period"]) for item in rollforward] == [
        ("CURRENT_PERIOD_END", "31/12/2025"),
        ("CURRENT_PERIOD_START", "01/01/2025"),
    ]


def test_relative_period_axis_accepts_year_end_and_year_start_surfaces() -> None:
    axis, mode = extract_period_axis_v1([_line(7, "Số cuối năm", 100), _line(8, "Số đầu năm", 300)])

    assert mode == "LOCAL_RELATIVE_PERIOD_ROLES"
    assert [(item["period"], item["evidence_source_line_indices"]) for item in axis] == [
        ("CURRENT_PERIOD_END", [7]),
        ("COMPARATIVE_PERIOD_START", [8]),
    ]


def test_relative_period_axis_fails_closed_without_document_start_or_comparison() -> None:
    context = infer_document_reporting_period_context_v1(
        [
            _page(1, _line(1, "31/12/2025", 100)),
            _page(2, _line(1, "31.12.2025", 100)),
        ]
    )
    relative_axis, _mode = extract_period_axis_v1(
        [_line(7, "Số cuối kỳ", 100), _line(8, "Số đầu kỳ", 300)]
    )

    assert resolve_relative_period_axis_v1(
        relative_axis, context, period_semantics="BALANCE_COMPARATIVE"
    ) == ([], "UNRESOLVED")
    assert resolve_relative_period_axis_v1(
        relative_axis, context, period_semantics="CURRENT_ROLLFORWARD"
    ) == ([], "UNRESOLVED")


def test_units_and_numeric_surfaces_are_generic_and_typed() -> None:
    assert unit_kind_v1("Đơn vị: Triệu đồng") == "MONEY"
    # A diacritic-only VietOCR substitution must normalize to the same unit
    # surface while the immutable raw prediction remains available upstream.
    assert accounting_unit_surface_v1("triệu đóng") == {
        "currency": "VND",
        "magnitude_power10": 6,
        "normalized_surface": "trieu dong",
        "unit_kind": "MONEY",
    }
    assert unit_kind_v1("Triệu VND") == "MONEY"
    assert unit_kind_v1("Tỷ lệ %") == "PERCENT"
    assert accounting_unit_surface_v1("Tỷ lệ nợ xấu 2%") is None
    assert unit_kind_v1("Tỷ đồng") == "MONEY"
    assert accounting_unit_surface_v1("Đơn vị tính: nghìn VND") == {
        "currency": "VND",
        "magnitude_power10": 3,
        "normalized_surface": "don vi tinh nghin vnd",
        "unit_kind": "MONEY",
    }

    assert is_number_like_v1("(1.210.726.423)") is True
    assert is_number_like_v1("49,50%") is True
    assert is_number_like_v1("-") is False
    assert is_accounting_value_surface_v1("-") is True
    assert is_accounting_value_surface_v1("–") is True
    assert is_accounting_value_surface_v1("") is False
    assert money_integer_v1("1.210.726.423") == 1_210_726_423
    assert money_integer_v1("(35.170)") == -35_170
    assert money_integer_v1("-112,995") == -112_995
    assert money_integer_v1("49,50%") is None


def test_document_unit_context_uses_explicit_consensus_without_bank_or_file_routing() -> None:
    context = infer_document_accounting_unit_context_v1(
        [
            _page(1, _line(1, "Đơn vị tính: Triệu đồng", 100)),
            _page(2, _line(1, "Triệu VND", 100)),
            _page(3, _line(1, "Khoản tiền đồng thời được đối chiếu", 100)),
        ]
    )

    assert context["resolution"] == "REPEATED_EXPLICIT_DOCUMENT_UNIT_CONSENSUS"
    assert context["unit_kind"] == "MONEY"
    assert context["currency"] == "VND"
    assert context["magnitude_power10"] == 6
    assert context["supporting_page_count"] == 2
    assert [item["page_sequence"] for item in context["evidence"]] == [1, 2]


def test_document_unit_context_fails_closed_on_conflicting_scales() -> None:
    context = infer_document_accounting_unit_context_v1(
        [
            _page(1, _line(1, "Đơn vị: Triệu đồng", 100)),
            _page(2, _line(1, "Đơn vị: Tỷ đồng", 100)),
        ]
    )

    assert context["resolution"] == "UNRESOLVED_CONFLICTING_EXPLICIT_DOCUMENT_UNITS"
    assert context["unit_kind"] is None
    assert context["magnitude_power10"] is None
    assert len(context["evidence"]) == 2


def test_value_vector_uses_geometry_and_preserves_money_percent_lanes() -> None:
    vector = extract_typed_value_vector_v1(
        [
            _line(40, "100.00", 700, source_text="100,00"),
            _line(38, "448.407.905", 500, source_text="448.407.905"),
            _line(37, "49.50", 300, source_text="49,50"),
            _line(36, "603.040.884", 100, source_text="603.040.884"),
        ],
        ["MONEY", "PERCENT", "MONEY", "PERCENT"],
        primary_numeric_authority=True,
    )
    assert vector is not None
    assert [item["source_line_index"] for item in vector] == [36, 37, 38, 40]
    assert money_values_v1(vector) == [603_040_884, 448_407_905]
    assert percentage_values_v1(vector) == [Decimal("49.50"), Decimal("100.00")]

    semantic_only = extract_typed_value_vector_v1(
        [_line(1, "81.371.771", 100, source_text="81.371.777")],
        ["MONEY"],
        primary_numeric_authority=False,
    )
    assert semantic_only is not None
    assert semantic_only[0]["surface"] == "81.371.771"
    assert semantic_only[0]["source_authoritative"] is False
    assert money_values_v1(semantic_only) is None


def test_value_vector_rejects_hidden_extra_or_missing_lanes() -> None:
    rows = [_line(1, "100", 100), _line(2, "50", 300)]
    assert extract_typed_value_vector_v1(rows, ["MONEY"], primary_numeric_authority=True) is None
    assert (
        extract_typed_value_vector_v1(
            rows,
            ["MONEY", "PERCENT", "MONEY"],
            primary_numeric_authority=True,
        )
        is None
    )


def test_value_vector_uses_primary_numeric_surface_when_semantic_reader_is_malformed() -> None:
    vector = extract_typed_value_vector_v1(
        [_line(1, "1,99,589,394", 100, source_text="1,992,589,394")],
        ["MONEY"],
        primary_numeric_authority=True,
    )

    assert vector is not None
    assert vector[0]["semantic_surface"] == "1,99,589,394"
    assert vector[0]["surface"] == "1,992,589,394"
    assert vector[0]["source_authoritative"] is True
    assert money_values_v1(vector) == [1_992_589_394]


def test_row_aligned_vector_uses_visual_geometry_and_splits_exact_merged_cells() -> None:
    merged = _line(9, "", 100, source_text="603.040.884 587.136.924")
    merged["bbox"] = [100, 10, 420, 30]

    vector = extract_row_aligned_typed_value_vector_v1(
        [
            _line(2, "narrative", 120),
            merged,
            _line(1, "999", 700, source_text="999") | {"bbox": [700, 100, 780, 120]},
        ],
        [0, 10, 80, 30],
        ["MONEY", "MONEY"],
        [300, 700],
        primary_numeric_authority=True,
    )

    assert vector is not None
    assert [item["lane_index"] for item in vector] == [0, 1]
    assert [item["source_line_index"] for item in vector] == [9, 9]
    assert money_values_v1(vector) == [603_040_884, 587_136_924]


def test_row_aligned_vector_excludes_detached_numeric_footnote_marker() -> None:
    annotated = _line(9, "3 525.394.779", 300, source_text="3 525.394.779")
    annotated["bbox"] = [300, 10, 420, 30]

    vector = extract_row_aligned_typed_value_vector_v1(
        [
            _line(8, "103.061.873", 100, source_text="103.061.873"),
            annotated,
        ],
        [0, 10, 80, 30],
        ["MONEY", "MONEY"],
        [280, 700],
        primary_numeric_authority=True,
    )

    assert vector is not None
    assert [item["source_line_index"] for item in vector] == [8, 9]
    assert [item["semantic_surface"] for item in vector] == ["103.061.873", "525.394.779"]
    assert money_values_v1(vector) == [103_061_873, 525_394_779]


def test_row_aligned_vector_deduplicates_overlapping_detector_seam_suffix() -> None:
    lane0 = _line(1, "324.009.713", 300, source_text="324.009.713") | {"bbox": [300, 10, 380, 30]}
    lane1 = _line(2, "8.846", 400, source_text="8.846") | {"bbox": [400, 10, 450, 30]}
    lane2 = _line(3, "40.104.713", 500, source_text="40.104.713") | {"bbox": [500, 10, 600, 30]}
    merged = _line(
        4,
        "3 104.640.972 468.764.244",
        590,
        source_text="3 104.640.972 468.764.244",
    ) | {"bbox": [590, 10, 820, 30]}

    vector = extract_row_aligned_typed_value_vector_v1(
        [lane0, lane1, lane2, merged],
        [0, 10, 250, 30],
        ["MONEY"] * 5,
        [680, 850, 1100, 1300, 1550],
        primary_numeric_authority=True,
    )

    assert vector is not None
    assert [item["source_line_index"] for item in vector] == [1, 2, 3, 4, 4]
    assert money_values_v1(vector) == [
        324_009_713,
        8_846,
        40_104_713,
        104_640_972,
        468_764_244,
    ]


def test_row_aligned_vector_rejects_duplicate_or_geometrically_ambiguous_cells() -> None:
    duplicate = [
        _line(1, "100", 100, source_text="100"),
        _line(2, "101", 110, source_text="101"),
        _line(3, "200", 300, source_text="200"),
    ]
    assert (
        extract_row_aligned_typed_value_vector_v1(
            duplicate,
            [0, 10, 80, 30],
            ["MONEY", "MONEY"],
            [280, 680],
            primary_numeric_authority=True,
        )
        is None
    )


def test_row_aligned_vector_selects_nearest_baseline_when_rows_overlap() -> None:
    prior_left = _line(1, "100", 100, source_text="100") | {"bbox": [100, 10, 180, 35]}
    prior_right = _line(2, "200", 300, source_text="200") | {"bbox": [300, 10, 380, 35]}
    current_left = _line(3, "101", 100, source_text="101") | {"bbox": [100, 35, 180, 60]}
    current_right = _line(4, "201", 300, source_text="201") | {"bbox": [300, 35, 380, 60]}

    vector = extract_row_aligned_typed_value_vector_v1(
        [prior_left, prior_right, current_left, current_right],
        [0, 30, 80, 58],
        ["MONEY", "MONEY"],
        [280, 680],
        primary_numeric_authority=True,
    )

    assert vector is not None
    assert [item["source_line_index"] for item in vector] == [3, 4]
    assert money_values_v1(vector) == [101, 201]


@pytest.mark.parametrize(
    ("operation", "message"),
    [
        (lambda: center_x2_v1(_line(1, "x", 10) | {"bbox": [True, 0, 2, 2]}), "bbox"),
        (
            lambda: extract_period_axis_v1(
                [_line(1, "30/06/2026", 10) | {"source_line_index": True}]
            ),
            "source line index",
        ),
        (
            lambda: infer_document_reporting_period_context_v1(
                [_page(True, _line(1, "31/12/2025", 10))]
            ),
            "page identity",
        ),
        (
            lambda: infer_document_reporting_period_context_v1(
                [
                    _page(
                        1,
                        _line(1, "31/12/2025", 10),
                        _line(1, "31/12/2024", 100),
                    )
                ]
            ),
            "line axis repeats",
        ),
        (
            lambda: infer_document_reporting_period_context_v1(1),
            "sequence of page records",
        ),
        (
            lambda: resolve_relative_period_axis_v1([], {}, period_semantics="BANK_SPECIFIC"),
            "accounting semantics",
        ),
        (lambda: is_number_like_v1(1), "exact string"),
        (
            lambda: extract_typed_value_vector_v1(
                [_line(1, "100", 10)],
                "MONEY",
                primary_numeric_authority=True,
            ),
            "lane declaration",
        ),
        (
            lambda: extract_typed_value_vector_v1(
                [_line(1, "100", 10)],
                ["MONEY"],
                primary_numeric_authority=1,
            ),
            "authority flag",
        ),
    ],
)
def test_axes_helpers_reject_type_smuggling(operation: object, message: str) -> None:
    with pytest.raises(AccountingTableAxesV1Error, match=message):
        operation()
