from __future__ import annotations

from bctc_ai.core.text import parse_financial_number
from bctc_ai.evaluation.structural_fusion_v2 import (
    StructuredReaderRow,
    compare_structural_readers_v2,
)
from bctc_ai.mapping.scope import load_scope_policy
from bctc_ai.validation.reader_agreement import ReaderRow


def _item(identifier, label, values, *, code=None, note=None):
    return StructuredReaderRow(
        row=ReaderRow(
            source_row_ids=(identifier,),
            label=label,
            note_reference=note,
            cells=tuple(parse_financial_number(value) for value in values),
        ),
        row_code=code,
    )


def _compare(project_root, role_b, role_c, *, eligible=True, context=""):
    return compare_structural_readers_v2(
        role_b,
        role_c,
        statement_type="CDKT",
        page_mapping_eligible=eligible,
        upstream_scope_reason="frozen page contract",
        scope_policy=load_scope_policy(project_root / "config/mapping/scope_exclusions.yaml"),
        role_b_context_text=context,
        role_c_context_text=context,
    )


def test_structural_fusion_alignment_is_unchanged_by_numeric_disagreement(project_root):
    role_b = (
        _item("b1", "Tiền mặt", ("100", "90"), code="I"),
        _item("b2", "Tiền gửi", ("200", "180"), code="II"),
    )
    agreeing = (
        _item("c1", "Tiền mặt", ("100", "90"), code="I"),
        _item("c2", "Tiền gửi", ("200", "180"), code="II"),
    )
    disagreeing = (
        _item("c1", "Tiền mặt", ("999", "90"), code="I"),
        _item("c2", "Tiền gửi", ("200", "180"), code="II"),
    )

    first = _compare(project_root, role_b, agreeing)
    second = _compare(project_root, role_b, disagreeing)

    assert [record["action"] for record in first["alignment"]] == ["MATCH", "MATCH"]
    assert [record["action"] for record in second["alignment"]] == ["MATCH", "MATCH"]
    assert first["policy"]["values_or_notes_affect_alignment"] is False
    assert first["counts"]["exact_paired_cells"] == 4
    assert second["counts"]["exact_paired_cells"] == 3
    assert second["alignment"][0]["escalation"] == "TARGETED_NUMERIC_DISAGREEMENT_REREAD"


def test_structural_fusion_upstream_off_balance_scope_excludes_every_unit(project_root):
    rows = (
        _item("r1", "Bảo lãnh vay vốn", ("10", "9"), code="1"),
        _item("r2", "Cam kết giao dịch hối đoái", ("20", "18"), code="2"),
    )

    result = _compare(
        project_root,
        rows,
        rows,
        eligible=False,
        context="CÁC CHỈ TIÊU NGOÀI BÁO CÁO TÌNH HÌNH TÀI CHÍNH",
    )

    assert result["counts"]["mapping_eligible_alignment_units"] == 0
    assert result["counts"]["mapping_excluded_alignment_units"] == 2
    assert all(not record["scope"]["mapping_eligible"] for record in result["alignment"])


def test_structural_fusion_retains_role_b_truncation_as_missing_evidence(project_root):
    role_b = (_item("b1", "Tiền mặt", ("100", "90")),)
    role_c = (
        _item("c1", "Tiền mặt", ("100", "90")),
        _item("c2", "Tiền gửi", ("200", "180")),
    )

    result = _compare(project_root, role_b, role_c)

    assert result["counts"]["alignment_actions"] == {"EXTRA_CANDIDATE": 1, "MATCH": 1}
    missing = next(
        record for record in result["alignment"] if record["action"] == "EXTRA_CANDIDATE"
    )
    assert missing["escalation"] == "ROLE_B_MISSING_OR_TRUNCATED_ROW_REREAD"
    assert missing["automatic_acceptance"] is False
    assert missing["confidence_effect"] == "NONE"
