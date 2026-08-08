from __future__ import annotations

from dataclasses import replace

import pytest

from bctc_ai.core.text import retrieval_key
from bctc_ai.document_phase.multisignal_statement_discovery import (
    discover_statement_pages as discover_v3,
)
from bctc_ai.document_phase.multisignal_statement_discovery import (
    load_multisignal_statement_config,
)
from bctc_ai.document_phase.multisignal_statement_discovery_v4 import (
    bounded_ordered_anchor_similarity,
    discover_statement_pages_v4,
    load_multisignal_statement_config_v4,
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
    "CDKT": ("Tiền mặt, vàng bạc, đá quý", "Cho vay khách hàng", "Nợ phải trả"),
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


def _line(text: str, x0: float, y0: float, x1: float, y1: float) -> OCRLine:
    return OCRLine(text=text, bbox=(x0, y0, x1, y1), score=0.98)


def _statement_page(page: int, page_type: str) -> OCRPage:
    lines = [
        _line(_FORM[page_type], 740, 45, 920, 70),
        _line(_TITLE[page_type], 100, 80, 620, 110),
        _line("tại ngày 31 tháng 12 năm 2025", 100, 120, 470, 145),
        _line("31/12/2025", 670, 165, 760, 190),
        _line("31/12/2024", 830, 165, 920, 190),
        _line("Triệu đồng", 670, 195, 760, 220),
        _line("Triệu đồng", 830, 195, 920, 220),
    ]
    for index, label in enumerate(_ROWS[page_type], start=1):
        y = 280 + (index - 1) * 80
        lines.extend(
            (
                _line(label, 110, y, 590, y + 26),
                _line(f"{index}.000", 670, y, 760, y + 26),
                _line(f"{index + 3}.000", 830, y, 920, y + 26),
            )
        )
    return OCRPage(page=page, width=1000, height=1400, lines=tuple(lines))


def _notes_page(page: int, embedded_text: str) -> OCRPage:
    return OCRPage(
        page=page,
        width=1000,
        height=1400,
        lines=(
            _line(_FORM["TM"], 740, 45, 920, 70),
            _line(_TITLE["TM"], 100, 80, 620, 110),
            _line("cho kỳ kết thúc ngày 31 tháng 3 năm 2026", 100, 120, 570, 145),
            _line("Đơn vị báo cáo: Ngân hàng thương mại cổ phần", 100, 185, 650, 215),
            _line("1.", 80, 245, 110, 270),
            _line("ĐẶC ĐIỂM HOẠT ĐỘNG", 140, 245, 500, 270),
            _line(embedded_text, 140, 305, 820, 335),
            _line(
                "Ngân hàng hoạt động theo giấy phép do Ngân hàng Nhà nước Việt Nam cấp.",
                140,
                350,
                900,
                380,
            ),
            _line(
                "Các hoạt động chính bao gồm huy động tiền gửi và cấp tín dụng cho khách hàng.",
                140,
                395,
                900,
                425,
            ),
        ),
    )


def _v3_config(project_root):
    return load_multisignal_statement_config(
        project_root / "config/document_phase/statement-discovery-v3.yaml"
    )


def _v4_config(project_root):
    return load_multisignal_statement_config_v4(
        project_root / "config/document_phase/statement-discovery-v4.yaml"
    )


def _block(notes: OCRPage) -> tuple[OCRPage, ...]:
    return (
        _statement_page(1, "CDKT"),
        _statement_page(2, "KQKD"),
        _statement_page(3, "LCTT"),
        notes,
    )


def test_bounded_window_recovers_ordered_ocr_corruption_without_matching_reversal(
    project_root,
):
    policy = _v4_config(project_root)["ordered_anchor_matching"]
    anchor = retrieval_key("thành lập và hoạt động")
    embedded = retrieval_key("Giáy phép thành lp và hot đng, thi hn có giá tr")
    reversed_words = retrieval_key("Giấy phép hoạt động và lập thành có giá trị")

    assert bounded_ordered_anchor_similarity(embedded, anchor, policy) > 0.92
    assert bounded_ordered_anchor_similarity(reversed_words, anchor, policy) < 0.78


def test_bounded_window_is_disabled_for_long_narrative_and_short_anchors(project_root):
    policy = _v4_config(project_root)["ordered_anchor_matching"]
    long_prose = retrieval_key(
        "Đây là một đoạn văn diễn giải rất dài về giấy phép và việc thành lp và hot đng "
        "của ngân hàng cùng nhiều thông tin không thuộc nhãn hàng cần nhận diện trong bảng"
    )
    short_anchor = retrieval_key("tổng tài sản")

    assert (
        bounded_ordered_anchor_similarity(
            long_prose, retrieval_key("thành lập và hoạt động"), policy
        )
        < 0.78
    )
    assert (
        bounded_ordered_anchor_similarity(
            retrieval_key("thông tin tong tai sn của ngân hàng"), short_anchor, policy
        )
        < 0.78
    )


def test_v4_recovers_notes_boundary_but_v3_abstains(project_root):
    notes = _notes_page(4, "Giáy phép thành lp và hot đng, thi hn có giá tr")
    pages = _block(notes)

    before = discover_v3(pages, _v3_config(project_root))
    after = discover_statement_pages_v4(pages, _v4_config(project_root))

    assert before["status"] == "UNRESOLVED"
    assert after["status"] == "ACCEPTED_MULTI_SIGNAL_STATEMENT_BLOCK"
    assert after["block"]["notes_boundary_page"] == 4
    diagnostics = after["ordered_anchor_matching"]["incremental_evidence"]
    page_4 = next(item for item in diagnostics if item["page"] == 4)
    tm = next(item for item in page_4["statement_types"] if item["statement_type"] == "TM")
    assert tm["baseline_hit_count"] == 1
    assert tm["extended_hit_count"] == 2
    assert tm["added_hits"][0]["anchor"] == "thành lập và hoạt động"


def test_native_exact_form_title_accepts_first_notes_page_without_period_or_continuation(
    project_root,
):
    notes = _notes_page(4, "Giấy phép thành lập và hoạt động của Ngân hàng")
    notes = replace(
        notes,
        lines=tuple(line for line in notes.lines if "cho kỳ kết thúc" not in line.text)
        + (
            _line("Cơ sở lập báo cáo tài chính", 140, 500, 500, 530),
            _line("Các chính sách kế toán", 140, 550, 500, 580),
        ),
    )
    pages = _block(notes)
    base = discover_statement_pages_v4(pages, _v4_config(project_root))
    assert base["status"] == "UNRESOLVED"

    native = _v4_config(project_root)
    native["policy"] = "NATIVE_TEXT_MULTI_SIGNAL_ORDERED_DOCUMENT_DISCOVERY_V1"
    native["geometry_authority"] = "PYMUPDF_NATIVE_TEXT_WORDS"
    native["geometry_evidence_source"] = "PYMUPDF_NATIVE_TEXT_GEOMETRY"
    native["notes_boundary_acceptance_override"] = {
        "policy": "EXACT_FORM_TITLE_THREE_GROUP_NOTES_BOUNDARY",
        "geometry_authority": "PYMUPDF_NATIVE_TEXT_WORDS",
        "require_form_type": "TM",
        "require_continuation_marker": False,
        "minimum_title_similarity": 0.95,
        "minimum_independent_groups": 3,
        "minimum_local_score": 6.0,
        "require_notes_anchors": True,
        "require_notes_structure": True,
    }
    accepted = discover_statement_pages_v4(pages, native)

    assert accepted["status"] == "ACCEPTED_MULTI_SIGNAL_STATEMENT_BLOCK"
    assert accepted["block"]["notes_boundary_page"] == 4
    page_4 = next(item for item in accepted["page_signals"] if item["page"] == 4)
    tm = next(item for item in page_4["candidates"] if item["page_type"] == "TM")
    assert tm["locally_accepted"] is True
    assert tm["independent_signal_groups"] == (
        "HEADER_IDENTITY",
        "NOTES_ANCHORS",
        "NOTES_STRUCTURE",
    )

    later_notes = replace(notes, page=5)
    with_second_qualifying_notes_page = discover_statement_pages_v4(
        _block(notes) + (later_notes,), native
    )
    page_5 = next(
        item for item in with_second_qualifying_notes_page["page_signals"] if item["page"] == 5
    )
    later_tm = next(item for item in page_5["candidates"] if item["page_type"] == "TM")
    assert later_tm["locally_accepted"] is False

    without_form = replace(
        notes,
        lines=tuple(line for line in notes.lines if _FORM["TM"] not in line.text),
    )
    assert discover_statement_pages_v4(_block(without_form), native)["status"] == "UNRESOLVED"

    weak_title = replace(
        notes,
        lines=tuple(
            replace(line, text="THUYẾT MINH") if line.text == _TITLE["TM"] else line
            for line in notes.lines
        ),
    )
    assert discover_statement_pages_v4(_block(weak_title), native)["status"] == "UNRESOLVED"

    pp_mutation = _v4_config(project_root)
    pp_mutation["notes_boundary_acceptance_override"] = {
        **native["notes_boundary_acceptance_override"],
        "geometry_authority": "PP_OCRV6_WORD_BOXES",
    }
    with pytest.raises(StatementLocatorError, match="override is invalid"):
        discover_statement_pages_v4(pages, pp_mutation)


def test_one_phrase_still_cannot_classify_notes_page(project_root):
    notes = _notes_page(4, "Nội dung khác không chứa neo kế toán thứ hai")
    notes = replace(
        notes,
        lines=tuple(line for line in notes.lines if "Đơn vị báo cáo" not in line.text),
    )

    result = discover_statement_pages_v4(_block(notes), _v4_config(project_root))

    assert result["status"] == "UNRESOLVED"
    page_4 = next(item for item in result["page_signals"] if item["page"] == 4)
    tm = next(item for item in page_4["candidates"] if item["page_type"] == "TM")
    assert len(tm["accounting_hits"]) < 2
    assert tm["locally_accepted"] is False


def test_v4_config_is_hash_bound_to_v3(project_root, tmp_path):
    source = project_root / "config/document_phase/statement-discovery-v4.yaml"
    drifted = tmp_path / source.name
    drifted.write_text(
        source.read_text(encoding="utf-8").replace(
            "f8188fdf53b8f3907ab89d5407bcea178fe927dfe02ccad291a79d1b5f1ba182",
            "0" * 64,
        ),
        encoding="utf-8",
    )
    base = project_root / "config/document_phase/statement-discovery-v3.yaml"
    (tmp_path / base.name).write_bytes(base.read_bytes())

    with pytest.raises(StatementLocatorError, match="base config hash drifted"):
        load_multisignal_statement_config_v4(drifted)
