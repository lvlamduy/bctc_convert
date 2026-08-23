from __future__ import annotations

import copy

import pytest

from bctc_ai.evaluation.accounting_family_column_context_v1 import (
    AccountingFamilyColumnContextV1Error,
    build_accounting_family_column_context_v1,
    validate_accounting_family_column_context_replay_v1,
)
from bctc_ai.evaluation.accounting_family_row_axis_v1 import (
    build_accounting_family_row_axis_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _spec() -> dict[str, object]:
    return {
        "children": [
            {
                "aliases": ["Tiền mặt bằng VND"],
                "presence": "REQUIRED",
                "role": "CASH_VND",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "aliases": ["Tiền mặt bằng ngoại tệ"],
                "presence": "REQUIRED",
                "role": "CASH_FOREIGN",
                "role_kind": "ADDITIVE_CHILD",
            },
        ],
        "family_id": "CASH_PRECIOUS_METALS",
        "format_version": "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V1",
        "hard_negative_aliases": ["Rủi ro tiền tệ"],
        "limits": {
            "max_cluster_span_lines": 30,
            "max_continuation_pages": 1,
            "max_label_line_span": 2,
        },
        "parent": {
            "aliases": ["Tiền, kim loại quý và đá quý"],
            "resolution_mode": "EXPLICIT_ONLY",
            "role": "CASH_PRECIOUS_METALS",
        },
        "structural_reset_aliases": ["Tiền gửi tại Ngân hàng Nhà nước"],
    }


def _line(
    ordinal: int,
    text: str,
    numeric: str,
    bbox: list[int],
    *,
    page: int = 1,
) -> dict[str, object]:
    sample = (page - 1) * 100 + ordinal + 1
    return {
        "bbox": bbox,
        "crop_ref": {
            "path": f"opaque/crop-{sample:04d}.png",
            "sha256": f"{sample:064x}",
            "size_bytes": 100 + sample,
        },
        "line_ordinal": ordinal,
        "numeric_recognition": {"raw_prediction": numeric, "reader_score": 0.95},
        "sample_id": f"sample-{sample:09d}",
        "vietocr_text": text,
    }


def _page(lines: list[dict[str, object]], page: int) -> dict[str, object]:
    return {"lines": lines, "page_sequence": page, "page_width": 1000}


def _pages(*, local_unit: bool = True, conflicting_document_unit: bool = False):
    first = [
        _line(0, "Tiền, kim loại quý và đá quý", "", [30, 20, 430, 42]),
        _line(1, "31/12/2025", "", [600, 50, 700, 72]),
        _line(2, "31/12/2024", "", [800, 50, 900, 72]),
    ]
    if local_unit:
        first.append(_line(3, "Đơn vị: Triệu đồng", "", [600, 75, 900, 95]))
    first.extend(
        [
            _line(4, "Tiền mặt bằng VND", "", [50, 100, 300, 122]),
            _line(5, "100", "100", [600, 100, 700, 122]),
            _line(6, "90", "90", [800, 100, 900, 122]),
            _line(7, "Tiền mặt bằng ngoại tệ", "", [50, 150, 300, 172]),
            _line(8, "20", "20", [600, 150, 700, 172]),
            _line(9, "10", "10", [800, 150, 900, 172]),
            _line(10, "120", "120", [600, 200, 700, 222]),
            _line(11, "100", "100", [800, 200, 900, 222]),
        ]
    )
    for ordinal, line in enumerate(first):
        line["line_ordinal"] = ordinal
    second_unit = "Đơn vị: Tỷ đồng" if conflicting_document_unit else "Đơn vị: Triệu đồng"
    second = [
        _line(0, "31.12.2025", "", [600, 30, 700, 52], page=2),
        _line(1, "31.12.2024", "", [800, 30, 900, 52], page=2),
        _line(2, second_unit, "", [600, 60, 900, 82], page=2),
        _line(3, "Tiền gửi tại Ngân hàng Nhà nước", "", [30, 100, 500, 122], page=2),
    ]
    third = [
        _line(0, "31/12/2025", "", [600, 30, 700, 52], page=3),
        _line(1, "31/12/2024", "", [800, 30, 900, 52], page=3),
        _line(2, "Đơn vị: Triệu đồng", "", [600, 60, 900, 82], page=3),
    ]
    return [_page(first, 1), _page(second, 2), _page(third, 3)]


def _axis(pages):
    return build_accounting_family_row_axis_v1(pages, _spec())


def _continuation_pages(
    *, conflicting_period: bool = False, continuation_shift: int = 0
) -> list[dict[str, object]]:
    first = [
        _line(0, "Tiền, kim loại quý và đá quý", "", [30, 20, 430, 42]),
        _line(1, "31/12/2025", "", [600, 50, 700, 72]),
        _line(2, "31/12/2024", "", [800, 50, 900, 72]),
        _line(3, "Đơn vị: Triệu đồng", "", [600, 75, 900, 95]),
        _line(4, "Tiền mặt bằng VND", "", [50, 120, 300, 142]),
        _line(5, "100", "100", [600, 120, 700, 142]),
        _line(6, "90", "90", [800, 120, 900, 142]),
    ]
    comparative = "31/12/2023" if conflicting_period else "31/12/2024"
    second = [
        _line(
            0,
            "31/12/2025",
            "",
            [600 + continuation_shift, 30, 700 + continuation_shift, 52],
            page=2,
        ),
        _line(
            1, comparative, "", [800 + continuation_shift, 30, 900 + continuation_shift, 52], page=2
        ),
        _line(
            2,
            "Đơn vị: Triệu đồng",
            "",
            [600 + continuation_shift, 60, 900 + continuation_shift, 82],
            page=2,
        ),
        _line(3, "Tiền mặt bằng ngoại tệ", "", [50, 110, 300, 132], page=2),
        _line(
            4, "20", "20", [600 + continuation_shift, 110, 700 + continuation_shift, 132], page=2
        ),
        _line(
            5, "10", "10", [800 + continuation_shift, 110, 900 + continuation_shift, 132], page=2
        ),
    ]
    third = [
        _line(0, "31/12/2025", "", [600, 30, 700, 52], page=3),
        _line(1, "31/12/2024", "", [800, 30, 900, 52], page=3),
        _line(2, "Đơn vị: Triệu đồng", "", [600, 60, 900, 82], page=3),
        _line(3, "Tiền gửi tại Ngân hàng Nhà nước", "", [30, 100, 500, 122], page=3),
    ]
    return [_page(first, 1), _page(second, 2), _page(third, 3)]


def test_local_dates_and_spanning_unit_bind_to_body_columns() -> None:
    pages = _pages()
    axis = _axis(pages)
    result = build_accounting_family_column_context_v1(
        axis,
        pages,
        _spec(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY", "MONEY"],
    )

    assert result["status"] == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
    assert [item["resolved_period"] for item in result["period_axis"]] == [
        "31/12/2025",
        "31/12/2024",
    ]
    assert [item["unit_kind"] for item in result["unit_axis"]] == ["MONEY", "MONEY"]
    assert all(item["magnitude_power10"] == 6 for item in result["unit_axis"])
    assert all(
        item["projection_status"] == "LOCAL_EXPLICIT_SPANNING_UNIT_BROADCAST_TO_BODY_COLUMNS"
        for item in result["unit_axis"]
    )


def test_visual_header_and_wrapped_label_survive_provider_source_order_drift() -> None:
    pages = [
        _page(
            [
                _line(0, "Tiền, kim loại quý và đá quý", "", [30, 20, 430, 42]),
                _line(1, "31/12/2025", "", [600, 50, 700, 72]),
                _line(2, "31/12/2024", "", [800, 50, 900, 72]),
                _line(3, "Tiền mặt bằng", "", [50, 100, 300, 122]),
                # Provider source order places this visually preceding unit
                # after the first wrapped-label fragment.
                _line(4, "Đơn vị: Triệu đồng", "", [600, 75, 900, 95]),
                _line(5, "100", "100", [600, 100, 700, 122]),
                _line(6, "90", "90", [800, 100, 900, 122]),
                _line(7, "VND", "", [50, 126, 300, 148]),
                _line(8, "Tiền mặt bằng ngoại tệ", "", [50, 180, 300, 202]),
                _line(9, "20", "20", [600, 180, 700, 202]),
                _line(10, "10", "10", [800, 180, 900, 202]),
            ],
            1,
        ),
        *_pages()[1:],
    ]
    axis = _axis(pages)

    result = build_accounting_family_column_context_v1(
        axis,
        pages,
        _spec(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY", "MONEY"],
    )

    assert result["status"] == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
    assert [item["resolved_period"] for item in result["period_axis"]] == [
        "31/12/2025",
        "31/12/2024",
    ]
    assert all(item["magnitude_power10"] == 6 for item in result["unit_axis"])
    assert [item["unit_kind"] for item in result["unit_axis"]] == ["MONEY", "MONEY"]
    assert all(
        item["projection_status"] == "LOCAL_EXPLICIT_SPANNING_UNIT_BROADCAST_TO_BODY_COLUMNS"
        for item in result["unit_axis"]
    )


def test_role_deficit_continuation_reuses_compatible_columns_and_repeated_headers() -> None:
    pages = _continuation_pages()
    axis = _axis(pages)

    result = build_accounting_family_column_context_v1(
        axis,
        pages,
        _spec(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY", "MONEY"],
    )

    assert axis["topology_region"]["continuation_page_count"] == 1
    assert result["status"] == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
    assert all(
        {location["page_sequence"] for location in item["evidence_locations"]} == {1, 2}
        for item in result["period_axis"]
    )


def test_continuation_uses_nearest_header_band_when_preceding_table_is_in_lookback() -> None:
    pages = _continuation_pages()
    for line in pages[1]["lines"]:
        line["bbox"][1] += 180
        line["bbox"][3] += 180
    pages[1]["lines"][:0] = [
        _line(90, "31/12/2023", "", [600, 20, 700, 42], page=2),
        _line(91, "31/12/2022", "", [800, 20, 900, 42], page=2),
        _line(92, "Triệu đồng", "", [600, 50, 700, 72], page=2),
        _line(93, "Triệu đồng", "", [800, 50, 900, 72], page=2),
        _line(94, "999", "999", [600, 90, 700, 112], page=2),
    ]
    for ordinal, line in enumerate(pages[1]["lines"]):
        line["line_ordinal"] = ordinal
    axis = _axis(pages)

    result = build_accounting_family_column_context_v1(
        axis,
        pages,
        _spec(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY", "MONEY"],
    )

    assert result["status"] == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
    assert [item["resolved_period"] for item in result["period_axis"]] == [
        "31/12/2025",
        "31/12/2024",
    ]
    assert all(
        {location["page_sequence"] for location in item["evidence_locations"]} == {1, 2}
        for item in result["unit_axis"]
    )


def test_complete_repeated_header_allows_translated_continuation_columns() -> None:
    pages = _continuation_pages(continuation_shift=90)
    axis = _axis(pages)

    result = build_accounting_family_column_context_v1(
        axis,
        pages,
        _spec(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY", "MONEY"],
    )

    assert result["status"] == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
    assert all(
        "ROLE_DEFICIT_CONTINUATION_GEOMETRY_PROVEN_WITH_REPEATED_HEADER_CORROBORATION"
        in item["projection_status"]
        for item in [*result["period_axis"], *result["unit_axis"]]
    )

    assert axis["topology_region"]["continuation_page_count"] == 1
    assert all(
        {location["page_sequence"] for location in item["evidence_locations"]} == {1, 2}
        for item in result["period_axis"]
    )


def test_continuation_selects_one_expected_period_pair_around_narrative_date() -> None:
    pages = _continuation_pages()
    pages[1]["lines"].insert(
        0,
        _line(99, "ngày 31 tháng 12 năm 2014 của", "", [600, 4, 900, 26], page=2),
    )
    for ordinal, line in enumerate(pages[1]["lines"]):
        line["line_ordinal"] = ordinal
    axis = _axis(pages)

    result = build_accounting_family_column_context_v1(
        axis,
        pages,
        _spec(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY", "MONEY"],
    )

    assert result["status"] == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
    assert [item["resolved_period"] for item in result["period_axis"]] == [
        "31/12/2025",
        "31/12/2024",
    ]
    assert all(
        {location["page_sequence"] for location in item["evidence_locations"]} == {1, 2}
        for item in result["period_axis"]
    )


def test_continuation_conflicting_period_or_column_geometry_fails_closed() -> None:
    shifted_without_header = _continuation_pages(continuation_shift=90)
    shifted_without_header[1]["lines"] = shifted_without_header[1]["lines"][3:]
    for ordinal, line in enumerate(shifted_without_header[1]["lines"]):
        line["line_ordinal"] = ordinal
    for pages, reason in [
        (_continuation_pages(conflicting_period=True), "CROSS_PAGE_LOCAL_PERIOD_HEADER_CONFLICT"),
        (shifted_without_header, "CROSS_PAGE_BODY_COLUMN_GEOMETRY_NOT_COMPATIBLE"),
    ]:
        axis = _axis(pages)
        result = build_accounting_family_column_context_v1(
            axis,
            pages,
            _spec(),
            period_semantics="BALANCE_COMPARATIVE",
            expected_lane_unit_kinds=["MONEY", "MONEY"],
        )

        assert result["status"] == "UNRESOLVED_PERIOD_UNIT_COLUMN_CONTEXT"
        assert reason in result["unresolved_reasons"]


def test_local_period_axis_uses_same_bbox_numeric_date_challenger() -> None:
    pages = _pages()
    pages[0]["lines"][1]["vietocr_text"] = "B1 tháng 12"
    pages[0]["lines"][1]["numeric_recognition"] = {
        "raw_prediction": "31 tháng 12",
        "reader_score": 0.99,
    }
    pages[0]["lines"][2]["vietocr_text"] = "2010"
    pages[0]["lines"][2]["numeric_recognition"] = {
        "raw_prediction": "năm 2024",
        "reader_score": 0.99,
    }
    pages[0]["lines"].insert(
        2,
        _line(99, "nam 2025", "năm 2025", [600, 73, 700, 93]),
    )
    for ordinal, line in enumerate(pages[0]["lines"]):
        line["line_ordinal"] = ordinal
    axis = _axis(pages)

    result = build_accounting_family_column_context_v1(
        axis,
        pages,
        _spec(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY", "MONEY"],
    )

    assert result["status"] == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
    assert [item["resolved_period"] for item in result["period_axis"]] == [
        "31/12/2025",
        "31/12/2024",
    ]


def test_unambiguous_document_unit_can_be_inherited_when_local_unit_is_absent() -> None:
    pages = _pages(local_unit=False)
    axis = _axis(pages)
    result = build_accounting_family_column_context_v1(
        axis,
        pages,
        _spec(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY", "MONEY"],
    )

    assert result["status"] == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
    assert (
        result["document_unit_context"]["resolution"] == "REPEATED_EXPLICIT_DOCUMENT_UNIT_CONSENSUS"
    )
    assert all(
        item["projection_status"] == "UNAMBIGUOUS_EXPLICIT_DOCUMENT_UNIT_INHERITED_TO_BODY_COLUMNS"
        for item in result["unit_axis"]
    )


def test_relative_end_start_headers_resolve_from_repeated_document_dates() -> None:
    pages = _pages()
    pages[0]["lines"][1]["vietocr_text"] = "Số cuối năm"
    pages[0]["lines"][2]["vietocr_text"] = "Số đầu năm"
    axis = _axis(pages)

    result = build_accounting_family_column_context_v1(
        axis,
        pages,
        _spec(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY", "MONEY"],
    )

    assert result["status"] == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
    assert [item["resolved_period"] for item in result["period_axis"]] == [
        "31/12/2025",
        "31/12/2024",
    ]
    assert all(
        item["projection_status"] == "DOCUMENT_CONTEXT_BALANCE_COMPARATIVE_PROJECTED_TO_BODY_COLUMN"
        for item in result["period_axis"]
    )


def test_explicit_owner_selects_its_axis_between_preceding_and_nested_repetitions() -> None:
    pages = _pages()
    pages[0]["lines"] = [
        _line(0, "Số cuối kỳ", "", [600, 10, 700, 32]),
        _line(1, "Số đầu kỳ", "", [800, 10, 900, 32]),
        _line(2, "100", "100", [600, 35, 700, 57]),
        _line(3, "90", "90", [800, 35, 900, 57]),
        _line(4, "Tiền, kim loại quý và đá quý", "", [30, 80, 430, 102]),
        _line(5, "Số cuối kỳ", "", [600, 110, 700, 132]),
        _line(6, "Số đầu kỳ", "", [800, 110, 900, 132]),
        _line(7, "Đơn vị: Triệu đồng", "", [600, 135, 900, 157]),
        _line(8, "Tiểu bảng khác", "", [30, 160, 300, 182]),
        _line(9, "Số cuối kỳ", "", [600, 185, 700, 207]),
        _line(10, "Số đầu kỳ", "", [800, 185, 900, 207]),
        _line(11, "Tiền mặt bằng VND", "", [50, 220, 300, 242]),
        _line(12, "100", "100", [600, 220, 700, 242]),
        _line(13, "90", "90", [800, 220, 900, 242]),
        _line(14, "Tiền mặt bằng ngoại tệ", "", [50, 260, 300, 282]),
        _line(15, "20", "20", [600, 260, 700, 282]),
        _line(16, "10", "10", [800, 260, 900, 282]),
    ]
    for ordinal, line in enumerate(pages[0]["lines"]):
        line["line_ordinal"] = ordinal

    result = build_accounting_family_column_context_v1(
        _axis(pages),
        pages,
        _spec(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY", "MONEY"],
    )

    assert result["status"] == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
    assert [item["resolved_period"] for item in result["period_axis"]] == [
        "31/12/2025",
        "31/12/2024",
    ]
    assert [item["evidence_locations"] for item in result["period_axis"]] == [
        [{"page_sequence": 1, "source_line_index": 5}],
        [{"page_sequence": 1, "source_line_index": 6}],
    ]


@pytest.mark.parametrize(
    "qualifier",
    ["(đã kiểm toán)", "(đã được kiểm toán)", "(đã soát xét)", "Số liệu so sánh"],
)
def test_qualified_duplicate_current_date_uses_document_comparative_consensus(
    qualifier: str,
) -> None:
    pages = _pages()
    pages[0]["lines"][2]["vietocr_text"] = "31/12/2025"
    pages[0]["lines"].insert(3, _line(99, qualifier, "", [800, 73, 900, 94]))
    pages[0]["lines"].extend(
        [
            _line(95, "Tiền gửi tại Ngân hàng Nhà nước", "", [30, 240, 500, 262]),
            _line(96, "31/12/2025", "", [600, 270, 700, 292]),
            _line(97, "31/12/2024", "", [800, 270, 900, 292]),
            _line(98, "31/12/2025", "", [600, 310, 700, 332]),
            _line(94, "31/12/2024", "", [800, 310, 900, 332]),
        ]
    )
    for ordinal, line in enumerate(pages[0]["lines"]):
        line["line_ordinal"] = ordinal
    axis = _axis(pages)

    result = build_accounting_family_column_context_v1(
        axis,
        pages,
        _spec(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY", "MONEY"],
    )

    assert result["status"] == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
    assert [item["resolved_period"] for item in result["period_axis"]] == [
        "31/12/2025",
        "31/12/2024",
    ]
    comparison_evidence = result["period_axis"][1]["evidence_locations"]
    assert {item["source_line_index"] for item in comparison_evidence} == {2, 3, 15, 17}
    assert all(item["page_sequence"] == 1 for item in comparison_evidence)
    assert all(
        item["projection_status"]
        == "LOCAL_DUPLICATED_CURRENT_DATE_COMPARATIVE_QUALIFIER_BOUND_TO_DOCUMENT_CONTEXT_"
        "PROJECTED_TO_BODY_COLUMN"
        for item in result["period_axis"]
    )


def test_unqualified_duplicate_current_date_remains_unresolved() -> None:
    pages = _pages()
    pages[0]["lines"][2]["vietocr_text"] = "31/12/2025"
    axis = _axis(pages)

    result = build_accounting_family_column_context_v1(
        axis,
        pages,
        _spec(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY", "MONEY"],
    )

    assert result["status"] == "UNRESOLVED_PERIOD_UNIT_COLUMN_CONTEXT"
    assert result["period_axis"] == []
    assert "PERIOD_AXIS_NOT_BOUND_TO_EVERY_BODY_COLUMN" in result["unresolved_reasons"]


def test_qualified_duplicate_without_same_page_axis_repetition_remains_unresolved() -> None:
    pages = _pages()
    pages[0]["lines"][2]["vietocr_text"] = "31/12/2025"
    pages[0]["lines"].insert(3, _line(99, "(đã kiểm toán)", "", [800, 73, 900, 94]))
    for ordinal, line in enumerate(pages[0]["lines"]):
        line["line_ordinal"] = ordinal
    axis = _axis(pages)

    result = build_accounting_family_column_context_v1(
        axis,
        pages,
        _spec(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY", "MONEY"],
    )

    assert result["status"] == "UNRESOLVED_PERIOD_UNIT_COLUMN_CONTEXT"
    assert result["period_axis"] == []


def test_qualified_duplicate_does_not_cross_pair_dates_from_different_rows() -> None:
    pages = _pages()
    pages[0]["lines"][2]["vietocr_text"] = "31/12/2025"
    pages[0]["lines"].insert(3, _line(99, "(đã kiểm toán)", "", [800, 73, 900, 94]))
    pages[0]["lines"].extend(
        [
            _line(95, "31/12/2025", "", [600, 270, 700, 292]),
            _line(96, "31/12/2025", "", [600, 310, 700, 332]),
            _line(97, "31/12/2024", "", [800, 400, 900, 422]),
            _line(98, "31/12/2024", "", [800, 440, 900, 462]),
        ]
    )
    for ordinal, line in enumerate(pages[0]["lines"]):
        line["line_ordinal"] = ordinal
    axis = _axis(pages)

    result = build_accounting_family_column_context_v1(
        axis,
        pages,
        _spec(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY", "MONEY"],
    )

    assert result["status"] == "UNRESOLVED_PERIOD_UNIT_COLUMN_CONTEXT"
    assert result["period_axis"] == []


def test_qualified_duplicate_comparative_column_may_precede_current_column() -> None:
    pages = _pages()
    pages[0]["lines"][1]["vietocr_text"] = "31/12/2025"
    pages[0]["lines"][2]["vietocr_text"] = "31/12/2025"
    pages[0]["lines"].insert(3, _line(99, "(đã kiểm toán)", "", [600, 73, 700, 94]))
    pages[0]["lines"].extend(
        [
            _line(95, "31/12/2024", "", [600, 270, 700, 292]),
            _line(96, "31/12/2025", "", [800, 270, 900, 292]),
            _line(97, "31/12/2024", "", [600, 310, 700, 332]),
            _line(98, "31/12/2025", "", [800, 310, 900, 332]),
        ]
    )
    for ordinal, line in enumerate(pages[0]["lines"]):
        line["line_ordinal"] = ordinal
    axis = _axis(pages)

    result = build_accounting_family_column_context_v1(
        axis,
        pages,
        _spec(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY", "MONEY"],
    )

    assert result["status"] == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
    assert [item["resolved_period"] for item in result["period_axis"]] == [
        "31/12/2024",
        "31/12/2025",
    ]


def test_implied_parent_recovers_preceding_relative_headers_by_body_geometry() -> None:
    pages = _pages()
    pages[0]["lines"][0]["vietocr_text"] = "THUYẾT MINH BÁO CÁO TÀI CHÍNH"
    pages[0]["lines"][1]["vietocr_text"] = "Số cuối kỳ"
    pages[0]["lines"][2]["vietocr_text"] = "Số đầu kỳ"
    spec = _spec()
    spec["parent"]["resolution_mode"] = "EXPLICIT_OR_UNIQUE_REQUIRED_CHILD_CLUSTER"
    axis = build_accounting_family_row_axis_v1(pages, spec)

    assert axis["topology_region"]["parent_resolution"] == "IMPLIED_BY_REQUIRED_CHILD_CLUSTER"
    result = build_accounting_family_column_context_v1(
        axis,
        pages,
        spec,
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY", "MONEY"],
    )

    assert result["status"] == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
    assert [item["resolved_period"] for item in result["period_axis"]] == [
        "31/12/2025",
        "31/12/2024",
    ]
    assert [item["evidence_locations"] for item in result["period_axis"]] == [
        [{"page_sequence": 1, "source_line_index": 1}],
        [{"page_sequence": 1, "source_line_index": 2}],
    ]


def test_headers_after_label_only_structural_group_bind_to_first_value_row() -> None:
    pages = _pages()
    pages[0]["lines"] = [
        _line(0, "Tiền, kim loại quý và đá quý", "", [30, 20, 430, 42]),
        _line(1, "Dư nợ tiền mặt", "", [40, 50, 360, 72]),
        _line(2, "31/12/2025", "", [600, 80, 700, 102]),
        _line(3, "31/12/2024", "", [800, 80, 900, 102]),
        _line(4, "Đơn vị: Triệu đồng", "", [600, 105, 900, 127]),
        _line(5, "Tiền mặt bằng VND", "", [50, 140, 300, 162]),
        _line(6, "100", "100", [600, 140, 700, 162]),
        _line(7, "90", "90", [800, 140, 900, 162]),
        _line(8, "Tiền mặt bằng ngoại tệ", "", [50, 190, 300, 212]),
        _line(9, "20", "20", [600, 190, 700, 212]),
        _line(10, "10", "10", [800, 190, 900, 212]),
    ]
    spec = _spec()
    spec["children"].insert(
        0,
        {
            "aliases": ["Dư nợ tiền mặt"],
            "presence": "OPTIONAL",
            "role": "CASH_STRUCTURAL_GROUP",
            "role_kind": "SOURCE_ONLY_GROUP_PARENT",
        },
    )
    axis = build_accounting_family_row_axis_v1(pages, spec)

    assert axis["rows"][0]["role"] == "CASH_STRUCTURAL_GROUP"
    assert axis["rows"][0]["values"] == []
    result = build_accounting_family_column_context_v1(
        axis,
        pages,
        spec,
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY", "MONEY"],
    )

    assert result["status"] == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
    assert [item["resolved_period"] for item in result["period_axis"]] == [
        "31/12/2025",
        "31/12/2024",
    ]
    assert [item["unit_kind"] for item in result["unit_axis"]] == ["MONEY", "MONEY"]


def test_explicit_parent_recovers_preceding_headers_despite_one_narrative_date() -> None:
    pages = _pages()
    lines = pages[0]["lines"]
    parent = lines.pop(0)
    lines.insert(3, parent)
    lines.insert(
        0,
        _line(
            99,
            "số dư ngày 31 tháng 12 năm 2014 của ngân hàng",
            "",
            [600, 5, 900, 27],
        ),
    )
    for ordinal, line in enumerate(lines):
        line["line_ordinal"] = ordinal
    axis = _axis(pages)

    result = build_accounting_family_column_context_v1(
        axis,
        pages,
        _spec(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY", "MONEY"],
    )

    assert axis["topology_region"]["parent_resolution"] == "EXPLICIT_PARENT"
    assert result["status"] == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
    assert [item["resolved_period"] for item in result["period_axis"]] == [
        "31/12/2025",
        "31/12/2024",
    ]
    assert all(
        item["projection_status"]
        == "LOCAL_EXACT_DATES_UNIQUE_EXPECTED_HEADER_SUBSET_PROJECTED_TO_BODY_COLUMN"
        for item in result["period_axis"]
    )


def test_two_distinct_expected_period_pairs_remain_ambiguous() -> None:
    pages = _pages()
    lines = pages[0]["lines"]
    lines[1:1] = [
        _line(90, "31/12/2025", "", [600, 30, 700, 48]),
        _line(91, "31/12/2024", "", [800, 30, 900, 48]),
    ]
    for ordinal, line in enumerate(lines):
        line["line_ordinal"] = ordinal
    axis = _axis(pages)

    result = build_accounting_family_column_context_v1(
        axis,
        pages,
        _spec(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY", "MONEY"],
    )

    assert result["status"] == "UNRESOLVED_PERIOD_UNIT_COLUMN_CONTEXT"
    assert result["unresolved_reasons"] == ["PERIOD_AXIS_NOT_BOUND_TO_EVERY_BODY_COLUMN"]


def test_conflicting_document_units_fail_closed_without_local_unit() -> None:
    pages = _pages(local_unit=False, conflicting_document_unit=True)
    axis = _axis(pages)
    result = build_accounting_family_column_context_v1(
        axis,
        pages,
        _spec(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY", "MONEY"],
    )

    assert result["status"] == "UNRESOLVED_PERIOD_UNIT_COLUMN_CONTEXT"
    assert result["unit_axis"] == []
    assert "UNIT_AXIS_NOT_BOUND_TO_EVERY_BODY_COLUMN" in result["unresolved_reasons"]


def test_unit_kind_declaration_length_and_type_fail_closed() -> None:
    pages = _pages()
    axis = _axis(pages)
    result = build_accounting_family_column_context_v1(
        axis,
        pages,
        _spec(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY"],
    )
    assert result["status"] == "UNRESOLVED_PERIOD_UNIT_COLUMN_CONTEXT"
    assert (
        "DECLARED_UNIT_KIND_AXIS_LENGTH_DIFFERS_FROM_BODY_COLUMNS" in result["unresolved_reasons"]
    )

    with pytest.raises(AccountingFamilyColumnContextV1Error, match="unit-kind"):
        build_accounting_family_column_context_v1(
            axis,
            pages,
            _spec(),
            period_semantics="BALANCE_COMPARATIVE",
            expected_lane_unit_kinds=[1, 1],
        )


def test_exact_replay_rejects_period_rehash() -> None:
    pages = _pages()
    axis = _axis(pages)
    result = build_accounting_family_column_context_v1(
        axis,
        pages,
        _spec(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY", "MONEY"],
    )
    forged = copy.deepcopy(result)
    forged["period_axis"][0]["resolved_period"] = "31/12/2099"
    material = copy.deepcopy(forged)
    material.pop("column_context_id")
    forged["column_context_id"] = "afccv1:context:" + canonical_json_sha256_v1(material)

    with pytest.raises(AccountingFamilyColumnContextV1Error, match="replay exactly"):
        validate_accounting_family_column_context_replay_v1(
            forged,
            axis,
            pages,
            _spec(),
            period_semantics="BALANCE_COMPARATIVE",
            expected_lane_unit_kinds=["MONEY", "MONEY"],
        )
