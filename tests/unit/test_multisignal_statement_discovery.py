from __future__ import annotations

from dataclasses import replace

import pytest

from bctc_ai.document_phase.multisignal_statement_discovery import (
    discover_statement_pages,
    load_multisignal_statement_config,
)
from bctc_ai.document_phase.statement_locator import OCRLine, OCRPage, StatementLocatorError

_FORM = {
    "CDKT": "Mẫu B02a/TCTD-HN",
    "KQKD": "Mẫu B03a/TCTD-HN",
    "LCTT": "Mẫu B04a/TCTD-HN",
    "TM": "Mẫu B05a/TCTD-HN",
}
_TITLE = {
    "CDKT": "BÁO CÁO TÌNH HÌNH TÀI CHÍNH HỢP NHẤT",
    "KQKD": "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG HỢP NHẤT",
    "LCTT": "BÁO CÁO LƯU CHUYỂN TIỀN TỆ HỢP NHẤT",
    "TM": "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT",
}
_ROWS = {
    "CDKT": (
        "Tiền mặt, vàng bạc, đá quý",
        "Cho vay khách hàng",
        "Nợ phải trả",
    ),
    "KQKD": (
        "Thu nhập lãi và các khoản thu nhập tương tự",
        "Chi phí lãi và các chi phí tương tự",
        "Lợi nhuận sau thuế",
    ),
    "LCTT": (
        "Lưu chuyển tiền từ hoạt động kinh doanh",
        "Thu nhập lãi và các khoản thu nhập tương tự nhận được",
        "Chi phí lãi và các chi phí tương tự đã trả",
    ),
}


def _config(project_root):
    return load_multisignal_statement_config(
        project_root / "config/document_phase/statement-discovery-v3.yaml"
    )


def _line(text: str, x0: float, y0: float, x1: float, y1: float) -> OCRLine:
    return OCRLine(text=text, bbox=(x0, y0, x1, y1), score=0.98)


def _statement_page(
    page: int,
    page_type: str,
    *,
    form: bool = True,
    title: bool = True,
    periods: bool = True,
    units: bool = True,
    rows: tuple[str, ...] | None = None,
    row_y: tuple[float, ...] | None = None,
    axes: tuple[tuple[float, float], tuple[float, float]] = ((670, 760), (830, 920)),
    period_values: tuple[str, str] = ("31/12/2025", "31/12/2024"),
) -> OCRPage:
    lines: list[OCRLine] = []
    if form:
        lines.append(_line(_FORM[page_type], 740, 45, 920, 70))
    if title:
        lines.append(_line(_TITLE[page_type], 100, 80, 590, 110))
    lines.append(_line("tại ngày 31 tháng 12 năm 2025", 100, 120, 470, 145))
    if periods:
        lines.extend(
            (
                _line(period_values[0], axes[0][0], 165, axes[0][1], 190),
                _line(period_values[1], axes[1][0], 165, axes[1][1], 190),
            )
        )
    if units:
        lines.extend(
            (
                _line("Triệu đồng", axes[0][0], 195, axes[0][1], 220),
                _line("Triệu đồng", axes[1][0], 195, axes[1][1], 220),
            )
        )
    row_labels = rows if rows is not None else _ROWS[page_type]
    y_values = row_y if row_y is not None else tuple(280 + index * 80 for index in range(len(row_labels)))
    for index, (label, y) in enumerate(zip(row_labels, y_values, strict=True), start=1):
        lines.extend(
            (
                _line(label, 110, y, 590, y + 26),
                _line(f"{index}.000", axes[0][0], y, axes[0][1], y + 26),
                _line(f"{index + 3}.000", axes[1][0], y, axes[1][1], y + 26),
            )
        )
    return OCRPage(page=page, width=1000, height=1400, lines=tuple(lines))


def _notes_page(page: int, *, title: bool = True, form: bool = True) -> OCRPage:
    lines = []
    if form:
        lines.append(_line(_FORM["TM"], 740, 45, 920, 70))
    if title:
        lines.append(_line(_TITLE["TM"], 100, 80, 620, 110))
    lines.extend(
        (
            _line("cho năm kết thúc ngày 31 tháng 12 năm 2025", 100, 120, 570, 145),
            _line(
                "Các thuyết minh này là một bộ phận hợp thành của báo cáo tài chính kèm theo.",
                100,
                185,
                900,
                215,
            ),
            _line("1.", 80, 245, 110, 270),
            _line("THÔNG TIN VỀ NGÂN HÀNG", 140, 245, 500, 270),
            _line(
                "Ngân hàng được thành lập và hoạt động theo giấy phép do Ngân hàng Nhà nước cấp.",
                140,
                305,
                900,
                335,
            ),
            _line(
                "Các hoạt động chính bao gồm huy động tiền gửi và cấp tín dụng cho khách hàng.",
                140,
                350,
                900,
                380,
            ),
        )
    )
    return OCRPage(page=page, width=1000, height=1400, lines=tuple(lines))


def _complete_block(start: int = 1) -> tuple[OCRPage, ...]:
    return (
        _statement_page(start, "CDKT"),
        _statement_page(start + 1, "KQKD"),
        _statement_page(start + 2, "LCTT"),
        _notes_page(start + 3),
    )


def _candidate(result: dict, page: int, page_type: str) -> dict:
    record = next(item for item in result["page_signals"] if item["page"] == page)
    return next(item for item in record["candidates"] if item["page_type"] == page_type)


def test_accepts_only_structurally_complete_multi_signal_document(project_root):
    result = discover_statement_pages(_complete_block(), _config(project_root))

    assert result["status"] == "ACCEPTED_MULTI_SIGNAL_STATEMENT_BLOCK"
    assert result["block"]["mapping_eligible_pages_by_statement_type"] == {
        "CDKT": [1],
        "KQKD": [2],
        "LCTT": [3],
    }
    assert result["block"]["notes_boundary_page"] == 4
    assert result["cash_flow"]["method"] == "DIRECT"
    assert all(
        len(contract["independent_signal_groups"]) >= 4
        for contract in result["block"]["page_contracts"]
    )


def test_multiline_title_is_joined_but_still_needs_other_signal_groups(project_root):
    cdkt = _statement_page(1, "CDKT", form=False, title=False)
    split_title = (
        _line("BÁO CÁO TÌNH HÌNH", 100, 75, 440, 100),
        _line("TÀI CHÍNH HỢP NHẤT", 102, 105, 470, 130),
    )
    cdkt = replace(cdkt, lines=(*split_title, *cdkt.lines))
    pages = (
        cdkt,
        _statement_page(2, "KQKD"),
        _statement_page(3, "LCTT"),
        _notes_page(4),
    )

    result = discover_statement_pages(pages, _config(project_root))

    assert result["status"] == "ACCEPTED_MULTI_SIGNAL_STATEMENT_BLOCK"
    candidate = _candidate(result, 1, "CDKT")
    assert candidate["locally_accepted"] is True
    assert set(candidate["independent_signal_groups"]) >= {
        "HEADER_IDENTITY",
        "PERIOD_AXIS",
        "UNIT",
        "ACCOUNTING_ROWS",
        "NUMERIC_GEOMETRY",
    }


def test_one_statement_title_in_unrelated_narrative_is_weak_evidence(project_root):
    page = OCRPage(
        page=1,
        width=1000,
        height=1400,
        lines=(
            _line(_TITLE["CDKT"], 100, 80, 620, 110),
            _line(
                "Đoạn văn này chỉ mô tả trách nhiệm lập báo cáo và không phải một bảng số liệu.",
                100,
                180,
                900,
                215,
            ),
            _line(
                "Thông tin tiếp theo hoàn toàn là nội dung thuyết minh mang tính diễn giải dài.",
                100,
                235,
                900,
                270,
            ),
        ),
    )

    result = discover_statement_pages((page,), _config(project_root))

    assert result["status"] == "UNRESOLVED"
    candidate = _candidate(result, 1, "CDKT")
    assert "HEADER_IDENTITY" in candidate["independent_signal_groups"]
    assert candidate["locally_accepted"] is False


def test_one_notes_title_cannot_close_an_otherwise_valid_block(project_root):
    pages = (*_complete_block()[:3], _notes_page(4, form=False))
    notes = replace(
        pages[-1],
        lines=(pages[-1].lines[0],),
    )

    result = discover_statement_pages((*pages[:-1], notes), _config(project_root))

    assert result["status"] == "UNRESOLVED"
    assert _candidate(result, 4, "TM")["locally_accepted"] is False


def test_bounded_neighbor_inference_recovers_one_headerless_continuation(project_root):
    first_rows = (*_ROWS["CDKT"], "Tài sản cố định", "Vốn chủ sở hữu", "Tổng tài sản")
    first_y = (280, 390, 500, 760, 880, 1030)
    first = _statement_page(1, "CDKT", rows=first_rows, row_y=first_y)
    continuation = _statement_page(
        2,
        "CDKT",
        form=False,
        title=False,
        periods=False,
        units=False,
        rows=("Tài sản cố định", "Nợ phải trả", "Vốn chủ sở hữu"),
        row_y=(245, 330, 415),
    )
    pages = (
        first,
        continuation,
        _statement_page(3, "KQKD"),
        _statement_page(4, "LCTT"),
        _notes_page(5),
    )

    result = discover_statement_pages(pages, _config(project_root))

    assert result["status"] == "ACCEPTED_MULTI_SIGNAL_STATEMENT_BLOCK"
    contract = next(item for item in result["block"]["page_contracts"] if item["page"] == 2)
    assert contract["locally_accepted"] is False
    assert contract["inferred_from_page"] == 1
    assert contract["inference_direction"] == "FORWARD_FROM_PREVIOUS"
    assert set(contract["inference_checks"]) >= {
        "ACCOUNTING_ROWS",
        "NUMERIC_GEOMETRY",
        "SHARED_NUMERIC_AXES",
        "TABLE_EDGE_CONTINUITY",
    }


def test_neighbor_inference_abstains_when_numeric_axes_are_incompatible(project_root):
    first_rows = (*_ROWS["CDKT"], "Tài sản cố định", "Vốn chủ sở hữu", "Tổng tài sản")
    first = _statement_page(
        1,
        "CDKT",
        rows=first_rows,
        row_y=(280, 390, 500, 760, 880, 1030),
    )
    incompatible = _statement_page(
        2,
        "CDKT",
        form=False,
        title=False,
        periods=False,
        units=False,
        rows=("Tài sản cố định", "Nợ phải trả", "Vốn chủ sở hữu"),
        row_y=(245, 330, 415),
        axes=((590, 680), (700, 790)),
    )
    pages = (
        first,
        incompatible,
        _statement_page(3, "KQKD"),
        _statement_page(4, "LCTT"),
        _notes_page(5),
    )

    result = discover_statement_pages(pages, _config(project_root))

    assert result["status"] == "UNRESOLVED"
    assert _candidate(result, 2, "CDKT")["inferred_from_page"] is None


def test_neighbor_inference_abstains_when_period_axes_disagree_without_edge_continuity(
    project_root,
):
    first = _statement_page(1, "CDKT")
    mismatched_period = _statement_page(
        2,
        "CDKT",
        form=False,
        title=False,
        rows=("Tài sản cố định", "Nợ phải trả", "Vốn chủ sở hữu"),
        period_values=("31/12/2023", "31/12/2022"),
    )
    pages = (
        first,
        mismatched_period,
        _statement_page(3, "KQKD"),
        _statement_page(4, "LCTT"),
        _notes_page(5),
    )

    result = discover_statement_pages(pages, _config(project_root))

    assert result["status"] == "UNRESOLVED"
    assert _candidate(result, 2, "CDKT")["inferred_from_page"] is None


def test_bounded_backward_inference_requires_visible_table_edge_and_rows(project_root):
    earlier_rows = (*_ROWS["CDKT"], "Tài sản cố định", "Vốn chủ sở hữu", "Tổng tài sản")
    headerless_start = _statement_page(
        1,
        "CDKT",
        form=False,
        title=False,
        periods=False,
        units=False,
        rows=earlier_rows,
        row_y=(280, 390, 500, 760, 880, 1030),
    )
    confident_next = _statement_page(
        2,
        "CDKT",
        rows=("Tài sản cố định", "Nợ phải trả", "Vốn chủ sở hữu"),
        row_y=(245, 330, 415),
    )
    pages = (
        headerless_start,
        confident_next,
        _statement_page(3, "KQKD"),
        _statement_page(4, "LCTT"),
        _notes_page(5),
    )

    result = discover_statement_pages(pages, _config(project_root))

    assert result["status"] == "ACCEPTED_MULTI_SIGNAL_STATEMENT_BLOCK"
    contract = next(item for item in result["block"]["page_contracts"] if item["page"] == 1)
    assert contract["inferred_from_page"] == 2
    assert contract["inference_direction"] == "BACKWARD_FROM_NEXT"
    assert "TABLE_EDGE_CONTINUITY" in contract["inference_checks"]


def test_off_balance_page_is_recognized_but_never_mapping_eligible(project_root):
    off_balance = _statement_page(
        2,
        "CDKT",
        rows=("Bảo lãnh vay vốn", "Cam kết giao dịch hối đoái", "Tài sản và chứng từ khác"),
    )
    pages = (
        _statement_page(1, "CDKT"),
        off_balance,
        _statement_page(3, "KQKD"),
        _statement_page(4, "LCTT"),
        _notes_page(5),
    )

    result = discover_statement_pages(pages, _config(project_root))

    assert result["status"] == "ACCEPTED_MULTI_SIGNAL_STATEMENT_BLOCK"
    assert result["block"]["off_balance_excluded_pages"] == [2]
    assert result["block"]["mapping_eligible_pages_by_statement_type"]["CDKT"] == [1]


def test_semantic_reader_cannot_create_numeric_geometry(project_root):
    geometry = OCRPage(
        page=1,
        width=1000,
        height=1400,
        lines=(_line("Ảnh mờ không có ô số được PP-OCRv6 xác nhận", 100, 300, 700, 335),),
    )
    semantic = _statement_page(1, "CDKT")

    result = discover_statement_pages(
        (geometry,), _config(project_root), semantic_pages=(semantic,)
    )

    assert result["status"] == "UNRESOLVED"
    candidate = _candidate(result, 1, "CDKT")
    assert "HEADER_IDENTITY" in candidate["independent_signal_groups"]
    assert "ACCOUNTING_ROWS" in candidate["independent_signal_groups"]
    assert "NUMERIC_GEOMETRY" not in candidate["independent_signal_groups"]
    assert candidate["locally_accepted"] is False


def test_equal_complete_blocks_abstain_on_document_runner_up_margin(project_root):
    pages = (*_complete_block(1), *_complete_block(5))

    result = discover_statement_pages(pages, _config(project_root))

    assert result["status"] == "UNRESOLVED"
    assert result["candidate_path_count"] >= 2
    assert result["runner_up_margin"] == 0.0


def test_v3_config_is_hash_bound_to_header_candidate_policy(project_root, tmp_path):
    source = project_root / "config/document_phase/statement-discovery-v3.yaml"
    drifted = tmp_path / source.name
    drifted.write_text(
        source.read_text(encoding="utf-8").replace(
            "503f3fdb62dd5dcd1a460200750edfe18d7cf50039b62278666e572c6cccb730",
            "0" * 64,
        ),
        encoding="utf-8",
    )
    base = project_root / "config/document_phase/statement-locator-v2.yaml"
    (tmp_path / base.name).write_bytes(base.read_bytes())
    v1 = project_root / "config/document_phase/statement-locator-v1.yaml"
    (tmp_path / v1.name).write_bytes(v1.read_bytes())

    with pytest.raises(StatementLocatorError, match="header config hash drifted"):
        load_multisignal_statement_config(drifted)
