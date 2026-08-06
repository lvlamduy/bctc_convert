from __future__ import annotations

import pytest

from bctc_ai.evaluation.line_recognition_metrics import (
    character_edit_metrics,
    compare_reader_scores,
    score_line,
    score_reader,
)


def test_separates_diacritic_only_and_base_character_substitutions():
    diacritic = character_edit_metrics("TÀI SẢN", "TAI SAN")
    base = character_edit_metrics("TÀI SẢN", "TÀI XẢN")

    assert diacritic.diacritic_only_error_count == 2
    assert diacritic.base_character_error_count == 0
    assert base.diacritic_only_error_count == 0
    assert base.base_character_error_count == 1


def test_normalizes_nfc_and_whitespace_but_not_diacritics():
    assert score_line("Tài   sản", "Ta\u0300i sản")["exact"] is True
    assert score_line("Tài sản", "Tai san")["exact"] is False


def test_suffix_truncation_requires_a_material_prefix_omission():
    truncated = score_line("Báo cáo tài chính hợp nhất", "Báo cáo tài chính")
    typo = score_line("Báo cáo tài chính", "Báo cáo tài chinh")

    assert truncated["suffix_truncated"] is True
    assert typo["suffix_truncated"] is False


def test_micro_metrics_and_adoption_gate_are_predeclared():
    references = [
        {
            "sample_id": "title",
            "document": "DOC",
            "category": "TITLE",
            "reference": "TÀI SẢN",
        },
        {
            "sample_id": "label",
            "document": "DOC",
            "category": "LABEL",
            "reference": "Tiền mặt",
        },
    ]
    baseline = score_reader(
        [sample | {"prediction": prediction} for sample, prediction in zip(
            references, ["TAI SAN", "Tien mat"], strict=True
        )],
        title_categories={"TITLE"},
    )
    challenger = score_reader(
        [sample | {"prediction": sample["reference"]} for sample in references],
        title_categories={"TITLE"},
    )

    comparison = compare_reader_scores(baseline, challenger)

    assert baseline["aggregate"]["character_error_rate"] == pytest.approx(4 / 15)
    assert challenger["aggregate"]["character_error_rate"] == 0
    assert comparison["adopt_as_semantic_proposal_reader"] is True
    assert comparison["numeric_period_unit_sign_geometry_mapping_authority_granted"] is False


def test_cer_gain_cannot_hide_title_regression():
    reference = [
        {
            "sample_id": "title",
            "document": "DOC",
            "category": "TITLE",
            "reference": "TÀI SẢN",
        },
        {
            "sample_id": "long",
            "document": "DOC",
            "category": "LABEL",
            "reference": "Thu nhập lãi và các khoản thu nhập tương tự",
        },
    ]
    baseline = score_reader(
        [
            reference[0] | {"prediction": "TÀI SẢN"},
            reference[1] | {"prediction": "Thu nhap lai va cac khoan thu nhap tuong tu"},
        ],
        title_categories={"TITLE"},
    )
    challenger = score_reader(
        [
            reference[0] | {"prediction": "TAI SAN"},
            reference[1] | {"prediction": reference[1]["reference"]},
        ],
        title_categories={"TITLE"},
    )

    comparison = compare_reader_scores(baseline, challenger)

    assert comparison["gates"]["strictly_lower_aggregate_cer"] is True
    assert comparison["gates"]["title_exact_line_count_not_regressed"] is False
    assert comparison["adopt_as_semantic_proposal_reader"] is False
