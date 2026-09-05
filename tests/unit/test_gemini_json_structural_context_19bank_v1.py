from bctc_ai.evaluation.gemini_json_structural_context_v1 import (
    family_anchor_lookup_forms_v1,
)


def test_family_anchor_lookup_forms_cover_separator_attached_to_grade_number() -> None:
    forms = family_anchor_lookup_forms_v1(["Nhóm 1 Nợ đủ tiêu chuẩn"])

    assert "nhom 1- no du tieu chuan" in forms
    assert "nhom 1– no du tieu chuan" in forms

