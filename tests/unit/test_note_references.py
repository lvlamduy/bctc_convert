from __future__ import annotations

from bctc_ai.axes.note_references import extract_note_references


def test_note_reference_is_extracted_as_foreign_key():
    references = extract_note_references("Cho vay khách hàng — Thuyết minh số 12.3")
    assert [reference.notes_section for reference in references] == ["12.3"]
