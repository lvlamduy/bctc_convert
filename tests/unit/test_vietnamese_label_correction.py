from __future__ import annotations

from dataclasses import replace

from bctc_ai.ocr.vietnamese_label_correction import (
    OrderedObservedLabel,
    VocabularyLabel,
    load_vietnamese_label_correction_config,
    propose_vietnamese_label_corrections,
    vietnamese_label_correction_to_dict,
)


def _config(project_root):
    return load_vietnamese_label_correction_config(
        project_root / "config/ocr/vietnamese-label-correction-v1.yaml"
    )


def test_full_statement_label_is_corrected_with_decisive_scoped_candidate(project_root):
    rows = (
        OrderedObservedLabel("r0", "LCTT", "LUỞU CHUYỀN TIÊN TỪ HOẶT ĐỘNG KINH DOANH"),
        OrderedObservedLabel("r1", "LCTT", "LƯU CHUYỂN TIỀN TỪ HOẠT ĐỘNG TÀI CHÍNH"),
    )
    vocabulary = (
        VocabularyLabel("LCTT", "Lưu chuyển tiền từ hoạt động kinh doanh", "id:4104"),
        VocabularyLabel("LCTT", "Lưu chuyển tiền thuần từ hoạt động kinh doanh", "id:4110"),
        VocabularyLabel("CDKT", "Lưu chuyển tiền từ hoạt động kinh doanh", "wrong-statement"),
    )

    result = propose_vietnamese_label_corrections(rows, vocabulary, _config(project_root))

    proposal = result.proposals[0]
    assert proposal.raw_label == "LUỞU CHUYỀN TIÊN TỪ HOẶT ĐỘNG KINH DOANH"
    assert proposal.corrected_label == "LƯU CHUYỂN TIỀN TỪ HOẠT ĐỘNG KINH DOANH"
    assert proposal.replacements[0].candidate_kind == "SCHEMA_FULL_LABEL"
    assert proposal.replacements[0].vocabulary_source_ids == ("id:4104",)
    assert proposal.automatic_output_authority is False
    assert proposal.automatic_schema_mapping_authority is False


def test_phrase_and_acronym_use_schema_vocabulary_plus_other_row_support(project_root):
    rows = (
        OrderedObservedLabel(
            "r0",
            "LCTT",
            "(Tăng)/Giảm tiền gửi và cấp tính dụng cho các TCDT khác",
        ),
        OrderedObservedLabel("r1", "CDKT", "Chi phí dự phòng rủi ro tín dụng"),
        OrderedObservedLabel("r2", "CDKT", "Tiền gửi tại các TCTD khác"),
        OrderedObservedLabel("r3", "KQKD", "Dự phòng rủi ro tín dụng"),
        OrderedObservedLabel("r4", "CDKT", "Cho vay các TCTD khác"),
        OrderedObservedLabel("r5", "CDKT", "Hạn mức tín dụng"),
        OrderedObservedLabel("r6", "CDKT", "Vay các TCTD khác"),
    )
    vocabulary = (
        VocabularyLabel("LCTT", "Chi phí dự phòng rủi ro tín dụng", "id:4196"),
        VocabularyLabel("LCTT", "Tiền gửi và vay các TCTD khác", "id:4179"),
    )

    result = propose_vietnamese_label_corrections(rows, vocabulary, _config(project_root))

    proposal = result.proposals[0]
    assert proposal.corrected_label == "(Tăng)/Giảm tiền gửi và cấp tín dụng cho các TCTD khác"
    assert [item.candidate_kind for item in proposal.replacements] == [
        "SCHEMA_PHRASE_WITH_DOCUMENT_SUPPORT",
        "SCHEMA_PHRASE_WITH_DOCUMENT_SUPPORT",
    ]
    assert all(item.damerau_distance == 1 for item in proposal.replacements)
    assert all(item.document_support_count >= 1 for item in proposal.replacements)


def test_acronym_transposition_can_be_corrected_as_one_supported_token(project_root):
    rows = (
        OrderedObservedLabel("r0", "LCTT", "TCDT"),
        OrderedObservedLabel("r1", "CDKT", "TCTD"),
        OrderedObservedLabel("r2", "CDKT", "TCTD"),
        OrderedObservedLabel("r3", "CDKT", "TCTD"),
    )
    vocabulary = (VocabularyLabel("LCTT", "TCTD", "id:4179"),)

    result = propose_vietnamese_label_corrections(rows, vocabulary, _config(project_root))

    replacement = result.proposals[0].replacements[0]
    assert result.proposals[0].corrected_label == "TCTD"
    assert replacement.candidate_kind == "SCHEMA_ACRONYM_WITH_DOCUMENT_SUPPORT"
    assert replacement.damerau_distance == 1


def test_phrase_abstains_without_independent_document_support(project_root):
    rows = (
        OrderedObservedLabel("r0", "LCTT", "Cấp tính dụng cho khách hàng"),
        OrderedObservedLabel("r1", "LCTT", "Dòng tiền khác"),
    )
    vocabulary = (VocabularyLabel("LCTT", "Chi phí dự phòng rủi ro tín dụng", "id:4196"),)

    result = propose_vietnamese_label_corrections(rows, vocabulary, _config(project_root))

    assert result.proposals[0].status == "UNCHANGED_NO_DECISIVE_CANDIDATE"
    assert result.proposals[0].corrected_label == rows[0].raw_label


def test_function_word_change_is_protected_even_with_document_support(project_root):
    rows = (
        OrderedObservedLabel("r0", "LCTT", "Nhân viên và hoạt động quản lý"),
        OrderedObservedLabel("r1", "LCTT", "Sử dụng vào hoạt động đầu tư"),
        OrderedObservedLabel("r2", "LCTT", "Sử dụng vào hoạt động tài chính"),
        OrderedObservedLabel("r3", "LCTT", "Sử dụng vào hoạt động kinh doanh"),
    )
    vocabulary = (VocabularyLabel("LCTT", "Sử dụng vào hoạt động", "id:synthetic"),)

    result = propose_vietnamese_label_corrections(rows, vocabulary, _config(project_root))

    assert result.proposals[0].status == "UNCHANGED_NO_DECISIVE_CANDIDATE"
    assert result.proposals[0].corrected_label == rows[0].raw_label


def test_ambiguous_full_label_abstains_when_runner_up_margin_is_too_small(project_root):
    rows = (OrderedObservedLabel("r0", "LCTT", "Dong tien tu hoat dong"),)
    vocabulary = (
        VocabularyLabel("LCTT", "Dòng tiền từ hoạt động A", "id:a"),
        VocabularyLabel("LCTT", "Dòng tiền từ hoạt động B", "id:b"),
    )
    permissive_similarity = replace(_config(project_root), minimum_full_label_similarity=0.70)

    result = propose_vietnamese_label_corrections(rows, vocabulary, permissive_similarity)

    assert result.proposals[0].status == "UNCHANGED_NO_DECISIVE_CANDIDATE"


def test_result_contract_contains_no_numeric_or_note_authority(project_root):
    rows = (
        OrderedObservedLabel("r0", "LCTT", "LUỞU CHUYỀN TIÊN TỪ HOẶT ĐỘNG ĐẦU TƯ"),
        OrderedObservedLabel("r1", "LCTT", "Lưu chuyển tiền từ hoạt động tài chính"),
    )
    vocabulary = (
        VocabularyLabel("LCTT", "Lưu chuyển tiền từ hoạt động đầu tư", "id:4105"),
        VocabularyLabel("LCTT", "Lưu chuyển tiền thuần từ hoạt động đầu tư", "id:4111"),
    )

    result = propose_vietnamese_label_corrections(rows, vocabulary, _config(project_root))
    payload = vietnamese_label_correction_to_dict(result)

    assert payload["raw_labels_preserved"] is True
    assert payload["row_order_preserved"] is True
    assert payload["numeric_or_note_fields_present"] is False
    assert payload["automatic_output_authority"] is False
    assert payload["automatic_schema_mapping_authority"] is False
    assert [item["row_id"] for item in payload["proposals"]] == ["r0", "r1"]
