from __future__ import annotations

from bctc_ai.core.text import parse_financial_number
from bctc_ai.evaluation.semantic_geometry_fusion import (
    fuse_semantic_labels_onto_geometry_rows,
    load_semantic_geometry_fusion_config,
    semantic_geometry_fusion_to_dict,
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
    return load_semantic_geometry_fusion_config(
        project_root / "config/tables/semantic-geometry-fusion-v1.yaml"
    )


def test_fusion_uses_semantic_labels_but_preserves_fixed_geometry_cells(project_root):
    geometry = (
        _row("g0", "Tin thu lãi", ("100", "90"), note="1"),
        _row("g1", "Tin chi khác", ("(20)", "-")),
    )
    semantic = (
        _row("s0", "Tiền thu lãi", ("999", "90"), note="wrong"),
        _row("s1", "Tiền chi khác", ("(20)", "-")),
    )

    result = fuse_semantic_labels_onto_geometry_rows(geometry, semantic, _config(project_root))

    assert result.status == "FUSED_SEMANTIC_LABELS_ON_FIXED_GEOMETRY_GRID"
    assert [row.row.label for row in result.rows] == ["Tiền thu lãi", "Tiền chi khác"]
    assert result.rows[0].row.cells is geometry[0].cells
    assert result.rows[0].row.source_row_ids == ("g0",)
    assert result.rows[0].row.note_reference == "1"
    assert result.rows[0].semantic_value_fingerprint_exact is False
    assert result.automatic_acceptance is False
    assert result.confidence_effect == "NONE"


def test_fusion_repairs_verified_wrapped_label_and_shifted_values(project_root):
    geometry = (
        _row(
            "g0",
            "Tin thu đưc t góp vn ca c đông không kim soát",
            ("2.253", "854"),
        ),
        _row("g1", "C tc tr cho c đông", ("(5.210.255)", "-")),
        _row("g2", "Lưu chuyn tin thun", ("(5.009.760)", "53.518")),
    )
    semantic = (
        _row("s0", "Tiền thu được từ góp vốn của cổ đông", ("2.253", "854")),
        _row("s1", "không kiểm soát", ("(5.210.255)", "-")),
        _row("s2", "Cổ tức trả cho cổ đông"),
        _row("s3", "Lưu chuyển tiền thuần", ("(5.009.760)", "53.518")),
    )

    result = fuse_semantic_labels_onto_geometry_rows(geometry, semantic, _config(project_root))

    assert result.status == "FUSED_SEMANTIC_LABELS_ON_FIXED_GEOMETRY_GRID"
    assert [row.row.label for row in result.rows] == [
        "Tiền thu được từ góp vốn của cổ đông không kiểm soát",
        "Cổ tức trả cho cổ đông",
        "Lưu chuyển tiền thuần",
    ]
    assert len(result.overflow_repairs) == 1
    repair = result.overflow_repairs[0]
    assert repair.geometry_indices == (0, 1)
    assert repair.semantic_indices == (0, 1, 2)
    assert repair.score_gain >= 0.15
    assert result.rows[0].semantic_label_indices == (0, 1)
    assert result.rows[1].semantic_label_indices == (2,)
    assert result.rows[1].semantic_value_indices == (1,)
    assert result.rows[1].row.cells is geometry[1].cells
    assert all(row.semantic_value_fingerprint_exact for row in result.rows)
    payload = semantic_geometry_fusion_to_dict(result)
    assert payload["policy"]["semantic_values_have_output_authority"] is False
    assert payload["overflow_repairs"][0]["geometry_cells_unmodified"] is True


def test_fusion_refuses_row_surplus_without_exact_numeric_shift_evidence(project_root):
    geometry = (
        _row("g0", "Tiền thu được từ cổ đông không kiểm soát", ("10", "9")),
        _row("g1", "Cổ tức trả cho cổ đông", ("(5)", "-")),
    )
    semantic = (
        _row("s0", "Tiền thu được từ cổ đông", ("999", "9")),
        _row("s1", "không kiểm soát", ("(5)", "-")),
        _row("s2", "Cổ tức trả cho cổ đông"),
    )

    result = fuse_semantic_labels_onto_geometry_rows(geometry, semantic, _config(project_root))

    assert result.status == "UNRESOLVED_SEMANTIC_GEOMETRY_FUSION"
    assert result.rows == ()
    assert result.automatic_acceptance is False
    assert "cannot be explained" in result.unresolved_reasons[0]


def test_fusion_refuses_semantic_row_loss_instead_of_inventing_a_label(project_root):
    geometry = (
        _row("g0", "Tiền mặt", ("10", "9")),
        _row("g1", "Tiền gửi", ("20", "19")),
    )
    semantic = (_row("s0", "Tiền mặt", ("10", "9")),)

    result = fuse_semantic_labels_onto_geometry_rows(geometry, semantic, _config(project_root))

    assert result.status == "UNRESOLVED_SEMANTIC_GEOMETRY_FUSION"
    assert result.rows == ()
    assert "fewer rows" in result.unresolved_reasons[0]
