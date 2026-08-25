from __future__ import annotations

import copy

import pytest

from bctc_ai.evaluation import accounting_printed_note_reference_axis_v1 as subject
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _line(
    ordinal: int,
    text: str,
    bbox: list[int],
    *,
    numeric: str | None = None,
) -> dict[str, object]:
    return {
        "bbox": bbox,
        "line_ordinal": ordinal,
        "numeric_recognition": {"raw_prediction": text if numeric is None else numeric},
        "sample_id": f"sample-{ordinal:03d}",
        "vietocr_text": text,
    }


def _page() -> dict[str, object]:
    return {
        "lines": [
            _line(0, "Thuyết", [900, 100, 1020, 135], numeric="Thuyét"),
            _line(1, "minh", [920, 136, 1000, 170]),
            _line(2, "Tiền gửi và cho vay các TCTD khác", [300, 220, 700, 260]),
            _line(3, "5", [950, 220, 990, 260]),
            _line(4, "100.000", [1090, 220, 1250, 260]),
            _line(5, "90.000", [1330, 220, 1490, 260]),
            _line(6, "Tiền gửi tại các TCTD khác", [300, 270, 680, 310]),
            # Wider than half of the header: this is a real dotted reference,
            # not an integer-only or half-header-width special case.
            _line(7, "5.1", [930, 270, 1005, 310]),
            _line(8, "80.000", [1090, 270, 1250, 310]),
            _line(9, "70.000", [1330, 270, 1490, 310]),
            _line(10, "Cho vay các TCTD khác", [300, 320, 650, 360]),
            _line(11, "5.2", [928, 320, 1008, 360]),
            _line(12, "20.000", [1090, 320, 1250, 360]),
            _line(13, "20.000", [1330, 320, 1490, 360]),
        ],
        "page_sequence": 1,
        "page_width": 1600,
    }


def _build(page: dict[str, object] | None = None) -> dict[str, object]:
    return subject.build_accounting_printed_note_reference_axis_v1(
        _page() if page is None else page,
        detected_column_centers=[970.0, 1170.0, 1410.0],
        lane_tolerance=60.0,
        body_text_scale=40.0,
    )


def _rehash(axis: dict[str, object]) -> None:
    material = copy.deepcopy(axis)
    material.pop("axis_id")
    axis["axis_id"] = "apnrav1:axis:" + canonical_json_sha256_v1(material)


def test_shared_header_axis_projects_integer_and_dotted_references_and_replays() -> None:
    page = _page()
    axis = _build(page)

    assert axis["status"] == subject.READY_STATUS
    assert axis["unresolved_reasons"] == []
    assert axis["financial_column_centers"] == [1170.0, 1410.0]
    assert axis["header"] == {
        "bbox": [900, 100, 1020, 170],
        "normalized_surface": "thuyet minh",
        "sample_ids": ["sample-000", "sample-001"],
        "source_line_indices": [0, 1],
    }
    assert [row["note_reference"] for row in axis["rows"]] == ["5", "5.1", "5.2"]
    assert [row["label_sample_ids"] for row in axis["rows"]] == [
        ["sample-002"],
        ["sample-006"],
        ["sample-010"],
    ]
    assert (
        subject.validate_accounting_printed_note_reference_axis_replay_v1(
            axis,
            page,
            detected_column_centers=[970.0, 1170.0, 1410.0],
            lane_tolerance=60.0,
            body_text_scale=40.0,
        )
        == axis
    )
    assert set(axis["input_binding"]) == {
        "body_text_scale",
        "detected_column_centers",
        "lane_tolerance",
        "page_sequence",
        "page_sha256",
        "page_width",
    }
    assert not {"bank_provenance", "document_ordinal", "family_id", "year"}.intersection(axis)


def test_decimal_money_cell_stays_a_financial_sample_not_a_note_reference() -> None:
    page = _page()
    decimal = page["lines"][8]
    decimal["vietocr_text"] = "5.25"
    decimal["numeric_recognition"]["raw_prediction"] = "5.25"

    axis = _build(page)

    row = next(row for row in axis["rows"] if row["note_reference"] == "5.1")
    assert row["note_sample_id"] == "sample-007"
    assert "sample-008" in row["financial_sample_ids"]
    assert all(row["note_sample_id"] != "sample-008" for row in axis["rows"])


def test_digit_bearing_roman_enumeration_challenger_is_not_label_evidence() -> None:
    page = _page()
    page["lines"].append(_line(20, "11", [210, 220, 250, 260], numeric="II"))

    axis = _build(page)

    parent = next(row for row in axis["rows"] if row["note_reference"] == "5")
    assert parent["label_sample_ids"] == ["sample-002"]


@pytest.mark.parametrize("attack", ["MISSING", "WRONG_CHANNEL", "DUPLICATE"])
def test_header_must_be_one_exact_dual_channel_axis(attack: str) -> None:
    page = _page()
    if attack == "MISSING":
        page["lines"] = page["lines"][2:]
    elif attack == "WRONG_CHANNEL":
        page["lines"][0]["numeric_recognition"]["raw_prediction"] = "Ghi chú"
    else:
        page["lines"].append(_line(20, "Thuyết minh", [700, 100, 820, 140]))

    axis = _build(page)

    assert axis["status"] == subject.UNRESOLVED_STATUS
    assert axis["rows"] == []
    assert axis["unresolved_reasons"] == ["EXACT_UNIQUE_THUYET_MINH_HEADER_NOT_ESTABLISHED"]


def test_duplicate_nonfinancial_detected_columns_fail_closed() -> None:
    axis = subject.build_accounting_printed_note_reference_axis_v1(
        _page(),
        detected_column_centers=[950.0, 1000.0, 1170.0, 1410.0],
        lane_tolerance=60.0,
        body_text_scale=40.0,
    )

    assert axis["status"] == subject.UNRESOLVED_STATUS
    assert axis["rows"] == []
    assert axis["unresolved_reasons"] == ["MULTIPLE_NONFINANCIAL_HEADER_LANES_NOT_EXCLUSIVE"]


def test_incomplete_financial_lanes_cannot_form_reference_rows() -> None:
    page = _page()
    page["lines"] = [
        line
        for line in page["lines"]
        if line["sample_id"] not in {"sample-005", "sample-009", "sample-013"}
    ]

    axis = _build(page)

    assert axis["status"] == subject.UNRESOLVED_STATUS
    assert axis["rows"] == []
    assert axis["unresolved_reasons"] == ["NO_COMPLETE_NOTE_REFERENCE_ROWS"]


def test_repeated_reference_surface_or_reused_financial_sample_fails_closed() -> None:
    repeated = _page()
    repeated["lines"][11]["vietocr_text"] = "5.1"
    repeated["lines"][11]["numeric_recognition"]["raw_prediction"] = "5.1"
    repeated_axis = _build(repeated)
    assert repeated_axis["status"] == subject.UNRESOLVED_STATUS
    assert repeated_axis["unresolved_reasons"] == ["NOTE_REFERENCE_SURFACES_REPEAT"]

    reused = _page()
    reused["lines"][12]["sample_id"] = reused["lines"][8]["sample_id"]
    reused_axis = _build(reused)
    assert reused_axis["status"] == subject.UNRESOLVED_STATUS
    assert reused_axis["unresolved_reasons"] == [
        "FINANCIAL_SOURCE_SAMPLE_ASSIGNED_TO_MULTIPLE_ROWS"
    ]


def test_best_row_affinity_rejects_near_tie_and_conflicting_financial_cell() -> None:
    tied = _page()
    tied["lines"].append(_line(20, "81.000", [1090, 270, 1250, 310]))
    tied_axis = _build(tied)
    assert "5.1" not in [row["note_reference"] for row in tied_axis["rows"]]

    conflicting = _page()
    conflicting["lines"].append(_line(20, "75.000", [1255, 270, 1325, 310]))
    conflicting_axis = _build(conflicting)
    assert "5.1" not in [row["note_reference"] for row in conflicting_axis["rows"]]


@pytest.mark.parametrize("attack", ["SOURCE", "SAMPLE", "BBOX", "HEADER", "INPUT"])
def test_coherently_rehashed_axis_tamper_fails_public_exact_replay(attack: str) -> None:
    page = _page()
    axis = _build(page)
    attacked = copy.deepcopy(axis)
    if attack == "SOURCE":
        attacked["rows"][1]["note_reference"] = "5.3"
    elif attack == "SAMPLE":
        attacked["rows"][1]["note_sample_id"] = "sample-replayed"
    elif attack == "BBOX":
        attacked["header"]["bbox"][0] += 1
    elif attack == "HEADER":
        attacked["header"]["sample_ids"].reverse()
        attacked["header"]["source_line_indices"].reverse()
    else:
        attacked["input_binding"]["page_sha256"] = "0" * 64
    _rehash(attacked)

    with pytest.raises(
        subject.AccountingPrintedNoteReferenceAxisV1Error,
        match="does not replay exactly|axis .* drifted|header shape drifted",
    ):
        subject.validate_accounting_printed_note_reference_axis_replay_v1(
            attacked,
            page,
            detected_column_centers=[970.0, 1170.0, 1410.0],
            lane_tolerance=60.0,
            body_text_scale=40.0,
        )


def test_page_tamper_fails_public_exact_replay_without_self_hash_authority() -> None:
    page = _page()
    axis = _build(page)
    attacked_page = copy.deepcopy(page)
    attacked_page["lines"][7]["bbox"][0] += 1

    with pytest.raises(
        subject.AccountingPrintedNoteReferenceAxisV1Error,
        match="does not replay exactly",
    ):
        subject.validate_accounting_printed_note_reference_axis_replay_v1(
            axis,
            attacked_page,
            detected_column_centers=[970.0, 1170.0, 1410.0],
            lane_tolerance=60.0,
            body_text_scale=40.0,
        )
