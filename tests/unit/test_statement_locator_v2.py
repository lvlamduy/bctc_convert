from __future__ import annotations

import pytest

from bctc_ai.document_phase.statement_locator import (
    OCRLine,
    OCRPage,
    StatementLocatorError,
    load_statement_locator_config,
    locate_statement_pages,
)
from bctc_ai.document_phase.statement_locator_v2 import (
    classify_statement_page_v2,
    load_statement_locator_v2_config,
    locate_statement_pages_v2,
)


def _v1(project_root):
    return load_statement_locator_config(
        project_root / "config/document_phase/statement-locator-v1.yaml"
    )


def _v2(project_root):
    return load_statement_locator_v2_config(
        project_root / "config/document_phase/statement-locator-v2.yaml"
    )


def _page(page: int, *texts: str) -> OCRPage:
    return OCRPage(
        page=page,
        width=1000,
        height=1400,
        lines=tuple(
            OCRLine(
                text=text,
                bbox=(100, 40 + index * 35, 900, 65 + index * 35),
                score=0.98,
            )
            for index, text in enumerate(texts)
        ),
    )


def _suffixed_form_block() -> tuple[OCRPage, ...]:
    return (
        _page(
            1,
            "Mẫu B02a/TCTD-HN",
            "BÁO CÁO TÌNH HÌNH TÀI CHÍNH RIÊNG GIỮA NIÊN ĐỘ",
            "100",
            "200",
        ),
        _page(
            2,
            "Mẫu B02a/TCTD-HN",
            "BÁO CÁO TÌNH HÌNH TÀI CHÍNH RIÊNG GIỮA NIÊN ĐỘ (tiếp theo)",
            "300",
        ),
        _page(
            3,
            "Mẫu B02a/TCTD-HN",
            "CÁC CHỈ TIÊU NGOÀI BÁO CÁO TÌNH HÌNH TÀI CHÍNH",
            "Bảo lãnh vay vốn",
            "Cam kết giao dịch hối đoái",
        ),
        _page(
            4,
            "Mẫu B03b/TCTD-HN",
            "BÁO CÁO KẾT QUẢ HOẠT ĐNG RIÊNG GIỮA NIÊN ĐỘ",
            "400",
        ),
        _page(
            5,
            "Mẫu B04c/TCTD-HN",
            "BÁO CÁO LƯU CHUYỂN TIỀN TỆ RIÊNG GIỮA NIÊN ĐỘ",
            "Theo phương pháp trực tiếp",
            "Thu nhập lãi và các khoản thu nhập tương tự nhận được",
            "Chi phí lãi và các chi phí tương tự đã trả",
        ),
        _page(
            6,
            "Mẫu B04c/TCTD-HN",
            "BÁO CÁO LƯU CHUYỂN TIỀN TỆ RIÊNG GIỮA NIÊN ĐỘ (tiếp theo)",
        ),
        _page(
            7,
            "Mẫu B05a/TCTD-HN",
            "THUYẾT MINH BÁO CÁO TÀI CHÍNH RIÊNG GIỮA NIÊN ĐỘ",
        ),
    )


def test_v2_recovers_suffixed_form_families_and_keeps_scope_boundary(project_root):
    pages = _suffixed_form_block()

    before = locate_statement_pages(pages, _v1(project_root))
    after = locate_statement_pages_v2(pages, _v2(project_root))

    assert before["status"] == "UNRESOLVED"
    assert after["status"] == "ACCEPTED_ORDERED_STATEMENT_BLOCK"
    assert after["algorithm_revision"] == 2
    assert after["block"]["mapping_eligible_pages_by_statement_type"] == {
        "CDKT": [1, 2],
        "KQKD": [4],
        "LCTT": [5, 6],
    }
    assert after["block"]["off_balance_excluded_pages"] == [3]
    assert after["block"]["notes_boundary_page"] == 7
    assert after["cash_flow"]["method"] == "DIRECT"
    assert after["cash_flow"]["schema_branch_assignment_permitted"] is False
    page4 = next(item for item in after["page_decisions"] if item["page"] == 4)
    assert page4["form_hits"] == ("KQKD",)
    assert any("family=B03, suffix=b" in item for item in page4["evidence"])


def test_v2_long_title_containment_still_requires_table_evidence(project_root):
    config = _v2(project_root)
    narrative = _page(
        1,
        "Phạm vi công việc",
        "BÁO CÁO TÌNH HÌNH TÀI CHÍNH RIÊNG GIỮA NIÊN ĐỘ được lập theo quy định",
    )
    statement = _page(
        2,
        "BÁO CÁO TÌNH HÌNH TÀI CHÍNH RIÊNG GIỮA NIÊN ĐỘ",
        "100",
        "200",
    )

    narrative_result = classify_statement_page_v2(narrative, config)
    statement_result = classify_statement_page_v2(statement, config)

    assert narrative_result.page_type.value == "OTHER"
    assert narrative_result.mapping_eligible is False
    assert narrative_result.title_scores["CDKT"] == 1.0
    assert statement_result.page_type.value == "CDKT"
    assert statement_result.mapping_eligible is True
    assert any("core_containment" in item for item in statement_result.evidence)


def test_v2_rejects_conflicting_or_malformed_form_codes(project_root):
    config = _v2(project_root)
    conflict = _page(
        1,
        "Mẫu B02a/TCTD-HN",
        "Mẫu B03b/TCTD-HN",
        "100",
    )
    malformed = _page(2, "Mẫu B020/TCTD-HN", "100")

    conflict_result = classify_statement_page_v2(conflict, config)
    malformed_result = classify_statement_page_v2(malformed, config)

    assert conflict_result.page_type.value == "AMBIGUOUS"
    assert conflict_result.mapping_eligible is False
    assert malformed_result.form_hits == ()
    assert malformed_result.mapping_eligible is False


def test_v2_preserves_ordered_sequence_fail_closed_behavior(project_root):
    pages = (
        _page(1, "Mẫu B02a/TCTD-HN", "100"),
        _page(2, "Mẫu B04a/TCTD-HN", "200"),
        _page(3, "Mẫu B03a/TCTD-HN", "300"),
        _page(4, "Mẫu B05a/TCTD-HN", "Thuyết minh báo cáo tài chính"),
    )

    result = locate_statement_pages_v2(pages, _v2(project_root))

    assert result["status"] == "UNRESOLVED"
    assert result["candidate_count"] == 0


def test_v2_config_is_hash_bound_to_v1_gates(project_root, tmp_path):
    source = project_root / "config/document_phase/statement-locator-v2.yaml"
    drifted = tmp_path / "statement-locator-v2.yaml"
    drifted.write_text(
        source.read_text(encoding="utf-8").replace(
            "base_config_sha256: d25ff6da2a1ce48428b4ab1ac20a31b989a27849d93326ae839507dce2ff107e",
            f"base_config_sha256: {'0' * 64}",
        ),
        encoding="utf-8",
    )
    (tmp_path / "statement-locator-v1.yaml").write_text(
        (project_root / "config/document_phase/statement-locator-v1.yaml").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )

    with pytest.raises(StatementLocatorError, match="base config hash drifted"):
        load_statement_locator_v2_config(drifted)
