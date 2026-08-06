from __future__ import annotations

from dataclasses import replace

import pytest

from bctc_ai.document_phase.multisignal_statement_discovery import (
    discover_statement_pages,
    load_multisignal_statement_config,
)
from bctc_ai.document_phase.statement_locator import OCRLine, OCRPage
from bctc_ai.ocr.semantic_line_fusion import (
    SemanticFieldRole,
    SemanticLineFusionError,
    SemanticLineProposal,
    fuse_semantic_line_proposals,
    load_semantic_line_fusion_config,
)

_CROP_SHA256 = "a" * 64


def _line(text: str, y: float, *, x: float = 100) -> OCRLine:
    return OCRLine(text=text, bbox=(x, y, x + 500, y + 30), score=0.73)


def _page(*texts: str) -> OCRPage:
    return OCRPage(
        page=1,
        width=1000,
        height=1400,
        lines=tuple(_line(text, 80 + index * 60) for index, text in enumerate(texts)),
    )


def _config(project_root):
    return load_semantic_line_fusion_config(
        project_root / "config/ocr/semantic-line-fusion-v1.yaml"
    )


def _proposal(
    page: OCRPage,
    index: int,
    text: str,
    *,
    proposal_id: str = "proposal-1",
    role: SemanticFieldRole = SemanticFieldRole.TITLE,
    reader: str = "DEEPSEEK_OCR_2",
    score: float | None = None,
) -> SemanticLineProposal:
    source = page.lines[index]
    return SemanticLineProposal(
        proposal_id=proposal_id,
        reader=reader,
        page=page.page,
        source_line_indices=(index,),
        source_texts=(source.text,),
        source_bboxes=(source.bbox,),
        field_role=role,
        raw_proposal_text=text,
        crop_sha256=_CROP_SHA256,
        reader_score=score,
    )


def test_emits_semantic_title_on_exact_source_box_without_confidence_promotion(project_root):
    geometry = _page("BÁO CÁO TINH HINH TÀI CHÍNH HOP NHÁT")
    proposal = _proposal(
        geometry,
        0,
        "BÁO CÁO TÌNH HÌNH TÀI CHÍNH HỢP NHẤT",
        score=0.01,
    )

    result = fuse_semantic_line_proposals((geometry,), (proposal,), _config(project_root))

    assert result.emitted_count == 1
    assert result.rejected_count == 0
    assert result.semantic_pages[0].lines == (
        OCRLine(
            text="BÁO CÁO TÌNH HÌNH TÀI CHÍNH HỢP NHẤT",
            bbox=geometry.lines[0].bbox,
            score=0.01,
        ),
    )
    assert result.geometry_pages_unchanged is True
    assert result.numeric_period_unit_sign_authority is False
    assert result.statement_scope_mapping_truth_authority is False
    assert result.decisions[0].confidence_effect.startswith("NONE_")
    assert result.decisions[0].automatic_authority is False


def test_logical_row_proposal_uses_only_union_of_immutable_source_boxes(project_root):
    geometry = _page("Các khoản phải thu", "từ khách hàng và đối tác")
    first, second = geometry.lines
    proposal = SemanticLineProposal(
        proposal_id="wrapped-label",
        reader="DEEPSEEK_OCR_2",
        page=1,
        source_line_indices=(0, 1),
        source_texts=(first.text, second.text),
        source_bboxes=(first.bbox, second.bbox),
        field_role=SemanticFieldRole.READING_ORDER_LABEL_GROUP,
        raw_proposal_text="Các khoản phải thu từ khách hàng và đối tác",
        crop_sha256=_CROP_SHA256,
    )

    result = fuse_semantic_line_proposals((geometry,), (proposal,), _config(project_root))

    assert result.semantic_pages[0].lines[0].bbox == (
        min(first.bbox[0], second.bbox[0]),
        min(first.bbox[1], second.bbox[1]),
        max(first.bbox[2], second.bbox[2]),
        max(first.bbox[3], second.bbox[3]),
    )
    assert result.decisions[0].geometry_effect == (
        "DERIVED_UNION_OF_IMMUTABLE_PP_OCRV6_SOURCE_BOXES"
    )
    assert geometry.lines == (first, second)


@pytest.mark.parametrize(
    ("source", "proposal_text", "role", "reason"),
    [
        ("1.234.567", "1.234.567", SemanticFieldRole.LABEL, "SOURCE_IS_NUMERIC"),
        (
            "Ngày 31 tháng 12 năm 2025",
            "Ngày 31 tháng 12 năm 2025",
            SemanticFieldRole.TITLE,
            "SOURCE_IS_PERIOD",
        ),
        ("Đơn vị tính: Triệu đồng", "Triệu đồng", SemanticFieldRole.SECTION, "SOURCE_IS_UNIT"),
        ("Tài sản", "Tài sản 2025", SemanticFieldRole.LABEL, "PROPOSAL_IS_PERIOD"),
    ],
)
def test_rejects_numeric_period_and_unit_fields_even_at_high_reader_score(
    project_root, source, proposal_text, role, reason
):
    geometry = _page(source)
    proposal = _proposal(geometry, 0, proposal_text, role=role, score=0.9999)

    result = fuse_semantic_line_proposals((geometry,), (proposal,), _config(project_root))

    assert result.emitted_count == 0
    assert result.rejected_count == 1
    assert reason in result.decisions[0].reason
    assert result.semantic_pages[0].lines == ()


def test_does_not_confuse_co_dong_with_a_monetary_unit(project_root):
    geometry = _page("Lợi ích của cổ đông không kiểm soát")
    proposal = _proposal(
        geometry,
        0,
        "Lợi ích cổ đông không kiểm soát",
        role=SemanticFieldRole.LABEL,
    )

    result = fuse_semantic_line_proposals((geometry,), (proposal,), _config(project_root))

    assert result.emitted_count == 1


def test_allows_only_source_verified_form_code_family(project_root):
    geometry = _page("Mẫu B02a/TCTD-HN")
    accepted = _proposal(
        geometry,
        0,
        "Mẫu B02/TCTD-HN",
        role=SemanticFieldRole.FORM_CODE,
        proposal_id="same-family",
    )
    wrong_family = replace(
        accepted,
        proposal_id="wrong-family",
        raw_proposal_text="Mẫu B03/TCTD-HN",
        reader="VIETOCR_CHALLENGER",
    )

    result = fuse_semantic_line_proposals(
        (geometry,), (accepted, wrong_family), _config(project_root)
    )

    assert result.emitted_count == 1
    assert result.decisions[0].status == "SEMANTIC_PROPOSAL_EMITTED"
    assert result.decisions[1].reason == "FORM_CODE_FAMILY_NOT_SOURCE_VERIFIED"


@pytest.mark.parametrize(
    ("proposal_text", "reason"),
    [
        ("Báo cáo tài chính", "SUFFIX_TRUNCATED"),
        ("```text\nBáo cáo tài chính hợp nhất\n```", "MARKDOWN_OR_LAYOUT"),
        ("", "EMPTY_OR_NON_TEXTUAL"),
    ],
)
def test_rejects_truncated_serialized_or_empty_reader_output(
    project_root, proposal_text, reason
):
    geometry = _page("Báo cáo tài chính hợp nhất")
    proposal = _proposal(geometry, 0, proposal_text)

    result = fuse_semantic_line_proposals((geometry,), (proposal,), _config(project_root))

    assert result.rejected_count == 1
    assert reason in result.decisions[0].reason


def test_fails_closed_on_source_text_or_bbox_drift(project_root):
    geometry = _page("Tài sản")
    proposal = _proposal(geometry, 0, "TÀI SẢN")

    with pytest.raises(SemanticLineFusionError, match="source text/bbox drifted"):
        fuse_semantic_line_proposals(
            (geometry,),
            (replace(proposal, source_texts=("Tài sản khác",)),),
            _config(project_root),
        )


def test_fails_closed_on_competing_same_reader_target(project_root):
    geometry = _page("Tài sản")
    first = _proposal(geometry, 0, "TÀI SẢN", proposal_id="first")
    second = replace(first, proposal_id="second", raw_proposal_text="Tài sản")

    with pytest.raises(SemanticLineFusionError, match="competing proposals"):
        fuse_semantic_line_proposals((geometry,), (first, second), _config(project_root))


def test_adapter_semantics_cannot_create_numeric_geometry_for_locator(project_root):
    geometry = _page("BÁO CÁO TINH HINH TÀI CHÍNH HOP NHÁT")
    proposal = _proposal(
        geometry,
        0,
        "BÁO CÁO TÌNH HÌNH TÀI CHÍNH HỢP NHẤT",
    )
    fused = fuse_semantic_line_proposals((geometry,), (proposal,), _config(project_root))
    locator_config = load_multisignal_statement_config(
        project_root / "config/document_phase/statement-discovery-v3.yaml"
    )

    result = discover_statement_pages(
        (geometry,), locator_config, semantic_pages=fused.semantic_pages
    )

    assert result["status"] == "UNRESOLVED"
    record = result["page_signals"][0]
    assert record["numeric_geometry"]["passes"] is False
    assert any(
        "HEADER_IDENTITY" in candidate["independent_signal_groups"]
        for candidate in record["candidates"]
    )
