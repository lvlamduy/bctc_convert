from bctc_ai.core.text import parse_financial_number
from bctc_ai.validation.reader_agreement import ReaderRow, align_ordered_reader_rows


def _row(identifier, label, note=None, values=()):
    return ReaderRow(
        source_row_ids=(identifier,),
        label=label,
        note_reference=note,
        cells=tuple(parse_financial_number(value) for value in values),
    )


def test_ordered_alignment_proposes_wrapped_candidate_pair_without_using_values():
    reference = (
        _row("r0", "Thu nhập lãi", "1", ("100", "90")),
        _row("r1", "Lỗ thuần từ mua bán chứng khoán kinh doanh", "2", ("(8)", "7")),
        _row("r2", "Lợi nhuận sau thuế", None, ("92", "83")),
    )
    candidate = (
        _row("c0", "Thu nhập lãi", "1", ("999", "999")),
        _row("c1", "Lỗ thuần từ mua bán chứng khoán"),
        _row("c2", "kinh doanh", "2", ("(8)", "7")),
        _row("c3", "Lỗi nhuận sau thuế", None, ("92", "83")),
    )

    aligned = align_ordered_reader_rows(reference, candidate)

    assert [step.action for step in aligned] == ["MATCH", "MERGE_CANDIDATE", "MATCH"]
    assert aligned[1].candidate_indices == (1, 2)
    assert aligned[1].candidate.label == reference[1].label
    assert aligned[0].action == "MATCH"  # deliberately mismatching numbers do not shift rows
    assert aligned[2].label_exact is False
    assert aligned[2].semantic_key_exact is True


def test_ordered_alignment_retains_extra_and_missing_rows_explicitly():
    reference = (_row("r0", "A"), _row("r1", "B"))
    candidate = (_row("c0", "A"), _row("c1", "X"))

    aligned = align_ordered_reader_rows(reference, candidate)

    assert aligned[0].action == "MATCH"
    assert {step.action for step in aligned[1:]} == {"MISSING_CANDIDATE", "EXTRA_CANDIDATE"}
