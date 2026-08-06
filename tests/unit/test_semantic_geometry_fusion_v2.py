from __future__ import annotations

from dataclasses import replace

from bctc_ai.core.text import parse_financial_number
from bctc_ai.evaluation.semantic_geometry_fusion_v2 import (
    fuse_ordered_semantic_labels_onto_geometry_rows_v2,
    load_semantic_geometry_fusion_v2_config,
    semantic_geometry_fusion_v2_to_dict,
)
from bctc_ai.validation.reader_agreement import ReaderRow


def _row(identifier, label, values=("", ""), note=None):
    return ReaderRow(
        source_row_ids=(identifier,),
        label=label,
        note_reference=note,
        cells=tuple(parse_financial_number(value) for value in values),
    )


def _config(project_root):
    return load_semantic_geometry_fusion_v2_config(
        project_root / "config/tables/semantic-geometry-fusion-v2.yaml"
    )


def test_v2_splits_one_collapsed_semantic_label_over_two_geometry_rows(project_root):
    geometry = (
        _row("g0", "Tin chi tr cho nhân viên", ("(9)", "(8)")),
        _row("g1", "Tin thu thu nhp thc np", ("(3)", "(4)"), note="22.1"),
        _row("g2", "Lưu chuyn tin thun", ("10", "11")),
    )
    semantic = (
        _row(
            "s0",
            "Tiền chi trả cho nhân viên Tiền thu thu nhập thực nộp",
            ("(9)", "(8)"),
        ),
        _row("s1", "Lưu chuyển tiền thuần", ("(3)", "(4)")),
        _row("s2", "", ("10", "11")),
    )

    result = fuse_ordered_semantic_labels_onto_geometry_rows_v2(
        geometry, semantic, _config(project_root)
    )

    assert result.status == "FUSED_ORDERED_SEMANTIC_LABELS_ON_FIXED_GEOMETRY_GRID_V2"
    assert [item.row.label for item in result.rows] == [
        "Tiền chi trả cho nhân viên",
        "Tiền thu thu nhập thực nộp",
        "Lưu chuyển tiền thuần",
    ]
    assert result.alignment_action_counts == (
        ("EXTRA_CANDIDATE", 1),
        ("MATCH", 1),
        ("MERGE_REFERENCE", 1),
    )
    assert len(result.segmentations) == 1
    assert result.segmentations[0].action == "SPLIT_COLLAPSED_SEMANTIC_LABEL_1_TO_2"
    assert result.rows[0].row.cells is geometry[0].cells
    assert result.rows[1].row.note_reference == "22.1"
    assert result.ignored_semantic_rows[0].matching_geometry_indices == (2,)
    assert result.automatic_acceptance is False


def test_v2_merges_adjacent_semantic_label_and_value_fragments(project_root):
    geometry = (_row("g0", "Tin thu c tc và li nhun đưc chia", ("64", "35")),)
    semantic = (
        _row("s0", "Tiền thu cổ tức và lợi nhuận"),
        _row("s1", "được chia", ("64", "35")),
    )

    result = fuse_ordered_semantic_labels_onto_geometry_rows_v2(
        geometry, semantic, _config(project_root)
    )

    assert result.status == "FUSED_ORDERED_SEMANTIC_LABELS_ON_FIXED_GEOMETRY_GRID_V2"
    assert result.rows[0].row.label == "Tiền thu cổ tức và lợi nhuận được chia"
    assert result.rows[0].action == "MERGE_ADJACENT_SEMANTIC_LABEL_FRAGMENTS"
    assert result.rows[0].row.cells is geometry[0].cells
    assert result.rows[0].semantic_numeric_fingerprint_observed is True


def test_v2_trims_only_decisive_duplicate_edge_tokens(project_root):
    geometry = (_row("g0", "(Tăng)/Gim khác v tài sn hot đng", ("31", "(10)")),)
    semantic = (
        _row(
            "s0",
            "Thất các khoản (Tăng)/Giảm khác về tài sản hoạt động",
            ("31", "(10)"),
        ),
    )

    result = fuse_ordered_semantic_labels_onto_geometry_rows_v2(
        geometry, semantic, _config(project_root)
    )

    assert result.status == "FUSED_ORDERED_SEMANTIC_LABELS_ON_FIXED_GEOMETRY_GRID_V2"
    assert result.rows[0].row.label == "(Tăng)/Giảm khác về tài sản hoạt động"
    assert result.rows[0].action == "TRIM_DUPLICATE_EDGE_TOKENS"
    assert result.segmentations[0].dropped_token_indices == (0, 1, 2)
    payload = semantic_geometry_fusion_v2_to_dict(result)
    assert payload["policy"]["values_or_notes_affect_alignment"] is False
    assert payload["policy"]["semantic_values_have_output_authority"] is False


def test_v2_refuses_extra_nonempty_semantic_row(project_root):
    geometry = (_row("g0", "Tiền mặt", ("10", "9")),)
    semantic = (
        _row("s0", "Tiền mặt", ("10", "9")),
        _row("s1", "Dòng không rõ", ("10", "9")),
    )

    result = fuse_ordered_semantic_labels_onto_geometry_rows_v2(
        geometry, semantic, _config(project_root)
    )

    assert result.status == "UNRESOLVED_SEMANTIC_GEOMETRY_FUSION_V2"
    assert result.rows == ()
    assert "lacks safe" in result.unresolved_reasons[0]


def test_v2_refuses_ambiguous_collapsed_label_split(project_root):
    geometry = (
        _row("g0", "Khoản mục giống nhau", ("1", "2")),
        _row("g1", "Khoản mục giống nhau", ("3", "4")),
    )
    semantic = (_row("s0", "Khoản mục giống nhau khoản mục giống nhau", ("1", "2")),)
    strict_margin = replace(_config(project_root), minimum_split_runner_up_margin=1.0)

    result = fuse_ordered_semantic_labels_onto_geometry_rows_v2(geometry, semantic, strict_margin)

    assert result.status == "UNRESOLVED_SEMANTIC_GEOMETRY_FUSION_V2"
    assert result.rows == ()
    assert any("decisive split" in reason for reason in result.unresolved_reasons)
