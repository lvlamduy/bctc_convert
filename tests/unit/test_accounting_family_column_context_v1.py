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
