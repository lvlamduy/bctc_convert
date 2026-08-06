from __future__ import annotations

from pathlib import Path

import pytest

from bctc_ai.document_phase.statement_locator import (
    OCRLine,
    OCRPage,
    StatementLocatorError,
    classify_statement_page,
    load_statement_locator_config,
    locate_statement_pages,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _config():
    return load_statement_locator_config(
        PROJECT_ROOT / "config/document_phase/statement-locator-v1.yaml"
    )


def _page(page: int, *texts: str) -> OCRPage:
    lines = tuple(
        OCRLine(text=text, bbox=(100, 40 + index * 35, 900, 65 + index * 35), score=0.98)
        for index, text in enumerate(texts)
    )
    return OCRPage(page=page, width=1000, height=1400, lines=lines)


def test_form_order_locates_block_and_excludes_off_balance_page():
    pages = (
        _page(
            1,
            "MỤC LỤC",
            "Báo cáo tình hình tài chính",
            "Báo cáo kết quả hoạt động",
            "Báo cáo lưu chuyển tiền tệ",
            "Thuyết minh báo cáo tài chính",
        ),
        _page(2, "BÁO CÁO KIỂM TOÁN ĐỘC LẬP", "Báo cáo tình hình tài chính"),
        _page(3, "Mẫu B02/TCTD-HN", "BÁO CÁO TÌNH HÌNH TÀI CHÍNH"),
        _page(4, "Mẫu B02/TCTD-HN", "BÁO CÁO TÌNH HÌNH TÀI CHÍNH (tiếp theo)"),
        _page(
            5,
            "Mẫu B02/TCTD-HN",
            "CÁC CHỈ TIÊU NGOÀI BÁO CÁO TÌNH HÌNH TÀI CHÍNH",
            "Bảo lãnh vay vốn",
            "Cam kết giao dịch hối đoái",
        ),
        _page(6, "Mẫu B03/TCTD-HN", "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG"),
        _page(
            7,
            "Mẫu B04/TCTD-HN",
            "BÁO CÁO LƯU CHUYỂN TIỀN TỆ",
            "Phương pháp trực tiếp",
            "Thu nhập lãi và các khoản thu nhập tương tự nhận được",
            "Chi phí lãi và các chi phí tương tự đã trả",
        ),
        _page(8, "Mẫu B04/TCTD-HN", "BÁO CÁO LƯU CHUYỂN TIỀN TỆ (tiếp theo)"),
        _page(9, "Mẫu B05/TCTD-HN", "THUYẾT MINH BÁO CÁO TÀI CHÍNH"),
    )

    result = locate_statement_pages(pages, _config())

    assert result["status"] == "ACCEPTED_ORDERED_STATEMENT_BLOCK"
    assert result["block"]["start_page"] == 3
    assert result["block"]["end_page"] == 8
    assert result["block"]["notes_boundary_page"] == 9
    assert result["block"]["recognized_pages_by_statement_form"] == {
        "CDKT": [3, 4, 5],
        "KQKD": [6],
        "LCTT": [7, 8],
    }
    assert result["block"]["mapping_eligible_pages_by_statement_type"] == {
        "CDKT": [3, 4],
        "KQKD": [6],
        "LCTT": [7, 8],
    }
    assert result["block"]["off_balance_excluded_pages"] == [5]
    assert 5 not in result["block"]["mapping_eligible_pages"]
    contracts = {row["page"]: row for row in result["block"]["page_contracts"]}
    assert contracts[4]["continuation_to_page"] is None
    assert contracts[5]["continuation_from_page"] is None
    assert result["cash_flow"]["method"] == "DIRECT"
    assert result["cash_flow"]["schema_branch_assignment_permitted"] is False


def test_fuzzy_titles_locate_non_form_statement_block():
    pages = (
        _page(1, "Báo cáo tinh hình tài chính hợp nhất", "100", "200"),
        _page(2, "Báo cáo tinh hình tài chính hợp nhất tiếp theo", "300", "400"),
        _page(3, "Báo cáo kt qua hot đng hợp nhất", "500", "600"),
        _page(
            4,
            "Báo cáo lru chuyn tin t hợp nhất",
            "Phuong pháp trc tip",
            "700",
            "800",
        ),
        _page(5, "Thuyt minh báo cáo tài chính hợp nhất"),
    )

    result = locate_statement_pages(pages, _config())

    assert result["status"] == "ACCEPTED_ORDERED_STATEMENT_BLOCK"
    assert result["block"]["mapping_eligible_pages_by_statement_type"] == {
        "CDKT": [1, 2],
        "KQKD": [3],
        "LCTT": [4],
    }


def test_contents_and_audit_mentions_do_not_become_statement_pages():
    config = _config()
    contents = _page(
        1,
        "MC LC",
        "Báo cáo tình hình tài chính",
        "Báo cáo kết quả hoạt động",
        "Báo cáo lưu chuyển tiền tệ",
        "Thuyết minh báo cáo tài chính",
    )
    audit = _page(
        2,
        "BÁO CÁO KIỂM TOÁN ĐỘC LẬP",
        "bao gồm báo cáo tình hình tài chính và báo cáo kết quả hoạt động",
    )

    assert classify_statement_page(contents, config).page_type.value == "TABLE_OF_CONTENTS"
    assert classify_statement_page(audit, config).page_type.value == "AUDIT_REPORT"

    contents_with_form_code = _page(
        3,
        "MỤC LỤC",
        "Mẫu B02/TCTD-HN",
        "Báo cáo tình hình tài chính ........ 8",
    )
    assert (
        classify_statement_page(contents_with_form_code, config).page_type.value
        == "TABLE_OF_CONTENTS"
    )


def test_narrative_statement_mentions_do_not_start_a_statement_block():
    config = _config()
    audit_continuation = _page(
        7,
        "Theo ý kiến của chúng tôi",
        "báo cáo tài chính hợp nhất phản ánh trung thực tình hình tài chính hợp nhất",
        "Ngân hàng lập và trình bày báo cáo tài chính hợp nhất.",
    )

    decision = classify_statement_page(audit_continuation, config)

    assert decision.page_type.value in {"AMBIGUOUS", "OTHER"}
    assert decision.mapping_eligible is False


def test_unknown_page_inside_statement_sequence_is_not_silently_skipped():
    pages = (
        _page(1, "Mẫu B02/TCTD-HN", "Báo cáo tình hình tài chính"),
        _page(2, "Nội dung không xác định"),
        _page(3, "Mẫu B03/TCTD-HN", "Báo cáo kết quả hoạt động"),
        _page(4, "Mẫu B04/TCTD-HN", "Báo cáo lưu chuyển tiền tệ"),
        _page(5, "Mẫu B05/TCTD-HN", "Thuyết minh báo cáo tài chính"),
    )

    result = locate_statement_pages(pages, _config())

    assert result["status"] == "UNRESOLVED"
    assert result["candidate_count"] == 0


def test_form_anchored_start_outranks_preceding_title_only_candidate():
    pages = (
        _page(1, "Báo cáo tình hình tài chính", "100", "200"),
        _page(2, "Mẫu B02/TCTD-HN", "Báo cáo tình hình tài chính", "300", "400"),
        _page(3, "Mẫu B03/TCTD-HN", "Báo cáo kết quả hoạt động"),
        _page(4, "Mẫu B04/TCTD-HN", "Báo cáo lưu chuyển tiền tệ"),
        _page(5, "Mẫu B05/TCTD-HN", "Thuyết minh báo cáo tài chính"),
    )

    result = locate_statement_pages(pages, _config())

    assert result["status"] == "ACCEPTED_ORDERED_STATEMENT_BLOCK"
    assert result["candidate_count"] == 2
    assert result["block"]["start_page"] == 2
    assert result["runner_up_margin"] > 1


@pytest.mark.parametrize(
    ("old", "new", "message"),
    (
        (
            "max_interstitial_pages: 0",
            "max_interstitial_pages: 1",
            "silently skip",
        ),
        (
            "schema_branch_assignment_permitted: false",
            "schema_branch_assignment_permitted: true",
            "fail-closed",
        ),
    ),
)
def test_config_cannot_weaken_fail_closed_gates(tmp_path, old, new, message):
    source = PROJECT_ROOT / "config/document_phase/statement-locator-v1.yaml"
    weakened = tmp_path / "weakened.yaml"
    weakened.write_text(source.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")

    with pytest.raises(StatementLocatorError, match=message):
        load_statement_locator_config(weakened)


def test_order_regression_or_missing_notes_boundary_fails_closed():
    pages = (
        _page(1, "Mẫu B02/TCTD-HN", "Báo cáo tình hình tài chính"),
        _page(2, "Mẫu B04/TCTD-HN", "Báo cáo lưu chuyển tiền tệ"),
        _page(3, "Mẫu B03/TCTD-HN", "Báo cáo kết quả hoạt động"),
    )

    result = locate_statement_pages(pages, _config())

    assert result["status"] == "UNRESOLVED"
    assert result["errors"] == ["no complete ordered CDKT->KQKD->LCTT->TM block"]


def test_indirect_cash_flow_uses_ordered_anchors():
    pages = (
        _page(1, "Mẫu B02/TCTD-HN", "Báo cáo tình hình tài chính"),
        _page(2, "Mẫu B03/TCTD-HN", "Báo cáo kết quả hoạt động"),
        _page(
            3,
            "Mẫu B04/TCTD-HN",
            "Báo cáo lưu chuyển tiền tệ",
            "Phương pháp gián tiếp",
            "Lợi nhuận trước thuế",
            "Điều chỉnh cho các khoản",
        ),
        _page(4, "Mẫu B05/TCTD-HN", "Thuyết minh báo cáo tài chính"),
    )

    result = locate_statement_pages(pages, _config())

    assert result["cash_flow"]["method"] == "INDIRECT"
    assert result["cash_flow"]["evidence"]["indirect"]["ordered_row_sequence"]["complete"] is True


def test_cash_flow_sequence_optimizes_complete_order_instead_of_greedy_anchor():
    pages = (
        _page(1, "Mẫu B02/TCTD-HN", "Báo cáo tình hình tài chính"),
        _page(2, "Mẫu B03/TCTD-HN", "Báo cáo kết quả hoạt động"),
        _page(
            3,
            "Mẫu B04/TCTD-HN",
            "Thu nhp lãi và các khon thu nhp tuong t nhn đuc",
            "Chi phí lãi và các chi phí tương tự đã trả",
            "Thu nhập lãi và các khoản thu nhập tương tự nhận được",
        ),
        _page(4, "Mẫu B05/TCTD-HN", "Thuyết minh báo cáo tài chính"),
    )

    result = locate_statement_pages(pages, _config())
    sequence = result["cash_flow"]["evidence"]["direct"]["ordered_row_sequence"]

    assert result["cash_flow"]["method"] == "DIRECT"
    assert sequence["complete"] is True
    assert [match["line_index"] for match in sequence["matches"]] == [1, 2]


def test_cash_flow_conflict_and_noncontiguous_input_fail_closed():
    pages = (
        _page(1, "Mẫu B02/TCTD-HN"),
        _page(2, "Mẫu B03/TCTD-HN"),
        _page(
            3,
            "Mẫu B04/TCTD-HN",
            "Phương pháp trực tiếp",
            "Phương pháp gián tiếp",
            "Thu nhập lãi và các khoản thu nhập tương tự nhận được",
            "Chi phí lãi và các chi phí tương tự đã trả",
            "Lợi nhuận trước thuế",
            "Điều chỉnh cho các khoản",
        ),
        _page(4, "Mẫu B05/TCTD-HN"),
    )
    assert locate_statement_pages(pages, _config())["cash_flow"]["method"] == "CONFLICT"

    with pytest.raises(StatementLocatorError, match="contiguous"):
        locate_statement_pages((pages[0], pages[2]), _config())
