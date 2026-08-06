from __future__ import annotations

from dataclasses import replace

import pytest

from bctc_ai.core.contracts import BoundingBox
from bctc_ai.ocr.native_text_quality_v2 import (
    NativeTextQualityV2Error,
    apply_native_text_quality_v2,
    assess_native_text_quality_v2,
    load_native_text_quality_v2_config,
)
from bctc_ai.ocr.pdf_text import PDFTextPage, PDFWord


def _config(project_root):
    return load_native_text_quality_v2_config(
        project_root / "config/ocr/native-text-quality-v2.yaml"
    )


def _word(text: str, index: int = 0) -> PDFWord:
    return PDFWord(
        raw_text=text,
        normalized_text=text.casefold(),
        bbox_points=BoundingBox(index * 20, 0, index * 20 + 15, 10),
        block_number=0,
        line_number=0,
        word_number=index,
    )


def test_legitimate_vietnamese_letters_are_not_mojibake(project_root):
    words = [
        _word(text, index)
        for index, text in enumerate(("NGÂN", "NHÂN", "LÃI", "HOÃN", "MÃ", "MÃ,"))
    ]

    result = assess_native_text_quality_v2(words, _config(project_root))

    assert result.status == "USABLE_TEXT_LAYER"
    assert result.corruption_markers == ()
    assert result.marker_counts == {}
    assert result.legitimate_vietnamese_tokens == {
        "Â": ("NGÂN", "NHÂN"),
        "Ã": ("HOÃN", "LÃI", "MÃ", "MÃ,"),
    }


def test_byte_decoding_fragments_and_replacement_character_are_corrupt(project_root):
    words = [
        _word("BÃ\u0081O", 0),
        _word("Ä‘", 1),
        _word("Æ°", 2),
        _word("á»", 3),
        _word("�", 4),
    ]

    result = assess_native_text_quality_v2(words, _config(project_root))

    assert result.status == "CORRUPT_TEXT_LAYER"
    assert "Ã\u0081" in result.corruption_markers
    assert "Ä" in result.corruption_markers
    assert "Æ" in result.corruption_markers
    assert "á»" in result.corruption_markers
    assert "�" in result.corruption_markers
    assert result.unexpected_control_count == 1
    assert result.marker_counts["U+0081"] == 1


def test_no_native_words_remains_no_text_layer(project_root):
    result = assess_native_text_quality_v2([], _config(project_root))

    assert result.status == "NO_TEXT_LAYER"
    assert result.corruption_markers == ()


def test_v2_can_reassess_a_v1_false_positive_without_changing_words(project_root):
    page = PDFTextPage(
        page=1,
        width_points=595,
        height_points=842,
        rotation=0,
        words=[_word("NGÂN"), _word("HÀNG", 1), _word("LÃI", 2)],
        text_quality="CORRUPT_TEXT_LAYER",
        corruption_markers=("Â", "Ã"),
    )

    reassessed = apply_native_text_quality_v2(page, _config(project_root))

    assert reassessed.text_quality == "USABLE_TEXT_LAYER"
    assert reassessed.corruption_markers == ()
    assert reassessed.words == page.words
    assert reassessed is not page


def test_native_text_quality_policy_drift_is_rejected(project_root, tmp_path):
    source = project_root / "config/ocr/native-text-quality-v2.yaml"
    drifted = tmp_path / "quality.yaml"
    drifted.write_text(
        source.read_text(encoding="utf-8").replace(
            'legitimate_vietnamese_letters: ["Â", "Ã"]',
            'legitimate_vietnamese_letters: ["Ã"]',
        ),
        encoding="utf-8",
    )

    with pytest.raises(NativeTextQualityV2Error, match="policy drifted"):
        load_native_text_quality_v2_config(drifted)


def test_reassessment_preserves_unrelated_page_fields(project_root):
    page = PDFTextPage(
        page=7,
        width_points=612,
        height_points=792,
        rotation=90,
        words=[_word("HOÃN")],
        text_quality="CORRUPT_TEXT_LAYER",
        corruption_markers=("Ã",),
    )

    expected = replace(page, text_quality="USABLE_TEXT_LAYER", corruption_markers=())

    assert apply_native_text_quality_v2(page, _config(project_root)) == expected
