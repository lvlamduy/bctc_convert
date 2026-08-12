from __future__ import annotations

from copy import deepcopy

import pytest

from bctc_ai.corpus.ppocrv6_line_quarantine import (
    ALIGNED_LINE_AXES,
    LINE_QUARANTINE_LEDGER_FORMAT,
    PPOCRV6LineQuarantineError,
    build_ppocrv6_page_outlying_child_line_quarantine,
    validate_ppocrv6_page_outlying_child_line_quarantine,
)
from bctc_ai.corpus.wave1_role_b_word_box_normalization import (
    WORD_BOX_NORMALIZATION_POLICY,
    WaveOneRoleBWordBoxNormalizationError,
    normalization_policy_sha256,
)


def _authority() -> dict[str, object]:
    return {
        "policy": deepcopy(WORD_BOX_NORMALIZATION_POLICY),
        "policy_sha256": normalization_policy_sha256(WORD_BOX_NORMALIZATION_POLICY),
        "control_identity_sha256": "c" * 64,
        "normalization_producer_implementation_ledger_sha256": "d" * 64,
    }


def _polygon(box: list[int | float]) -> list[list[int | float]]:
    x0, y0, x1, y1 = box
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def _payload(
    word_box_lines: list[list[list[int | float]]],
    *,
    parent_boxes: list[list[int | float]] | None = None,
) -> dict[str, object]:
    if parent_boxes is None:
        parent_boxes = [[0, 0, 100, 100] for _line in word_box_lines]
    return {
        "dt_polys": [_polygon(box) for box in parent_boxes],
        "model_settings": {"model_name": "synthetic"},
        "page_index": 0,
        "rec_boxes": deepcopy(parent_boxes),
        "rec_polys": [_polygon(box) for box in parent_boxes],
        "rec_scores": [0.9 - index / 100 for index in range(len(word_box_lines))],
        "rec_texts": [f"line-{index}" for index in range(len(word_box_lines))],
        "return_word_box": True,
        "text_det_params": {"limit_side_len": 64},
        "text_rec_score_thresh": 0.0,
        "text_type": "general",
        "text_word": [
            [f"word-{line_index}-{word_index}" for word_index in range(len(boxes))]
            for line_index, boxes in enumerate(word_box_lines)
        ],
        "text_word_boxes": deepcopy(word_box_lines),
        "textline_orientation_angles": list(range(len(word_box_lines))),
    }


def _build(
    payload: dict[str, object],
    *,
    width: int = 100,
    height: int = 100,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    return build_ppocrv6_page_outlying_child_line_quarantine(
        payload,
        pixel_width=width,
        pixel_height=height,
        normalization_authority=_authority(),
    )


def test_equal_noop_is_typed_replayable_and_does_not_alias_or_mutate_input() -> None:
    raw = _payload([[[10, 10, 20, 20]]])
    before = deepcopy(raw)

    normalized, quarantine, normalization = _build(raw)

    assert raw == before
    assert normalized == raw
    assert normalized is not raw
    assert normalized["rec_boxes"] is not raw["rec_boxes"]
    assert quarantine == {
        "format_version": LINE_QUARANTINE_LEDGER_FORMAT,
        "status": "NO_CHANGE",
        "maximum_per_edge_overshoot_pixels": 1,
        "pixel_dimensions": [100, 100],
        "aligned_line_axes": list(ALIGNED_LINE_AXES),
        "raw_payload_sha256": quarantine["retained_payload_sha256"],
        "retained_payload_sha256": quarantine["raw_payload_sha256"],
        "raw_line_count": 1,
        "retained_line_count": 1,
        "quarantined_line_count": 0,
        "raw_word_count": 1,
        "retained_word_count": 1,
        "quarantined_word_count": 0,
        "quarantined_lines": [],
    }
    assert normalization["status"] == "NO_CHANGE"
    assert normalization["raw_payload_sha256"] == quarantine["retained_payload_sha256"]
    validate_ppocrv6_page_outlying_child_line_quarantine(
        raw,
        normalized,
        quarantine,
        normalization,
        pixel_width=100,
        pixel_height=100,
        normalization_authority=_authority(),
    )

    normalized["rec_boxes"][0][0] = 99
    assert raw == before


@pytest.mark.parametrize(
    ("raw_box", "edge"),
    [
        ([-2, 10, 20, 20], "left"),
        ([10, -2, 20, 20], "top"),
        ([80, 10, 102, 20], "right"),
        ([10, 80, 20, 102], "bottom"),
    ],
)
def test_more_than_one_pixel_on_each_edge_quarantines_the_whole_line(
    raw_box: list[int],
    edge: str,
) -> None:
    raw = _payload([[raw_box]])
    before = deepcopy(raw)

    normalized, quarantine, normalization = _build(raw)

    assert raw == before
    assert all(normalized[axis] == [] for axis in ALIGNED_LINE_AXES)
    assert quarantine["status"] == "WHOLE_LINES_QUARANTINED"
    assert quarantine["quarantined_line_count"] == 1
    assert quarantine["quarantined_word_count"] == 1
    offender = quarantine["quarantined_lines"][0]["offenders"][0]
    assert offender["per_edge_overshoot_pixels"][edge] == 2
    assert offender["reasons"] == ["PAGE_OVERSHOOT_GT_1PX"]
    assert offender["evidence"] == {
        "page_outlying": True,
        "overshoot_exceeds_maximum": True,
        "post_clip_positive": True,
        "post_clip_contained_in_parent_rec_box": True,
    }
    assert all(type(value) is bool for value in offender["evidence"].values())
    assert normalization["status"] == "NO_CHANGE"


def test_one_pixel_contained_clip_is_preserved_for_the_existing_normalizer() -> None:
    raw = _payload([[[80, 10, 101, 20]]])

    normalized, quarantine, normalization = _build(raw)

    assert quarantine["status"] == "NO_CHANGE"
    assert quarantine["quarantined_line_count"] == 0
    assert normalized["text_word_boxes"] == [[[80, 10, 100, 20]]]
    assert normalization["status"] == "PAGE_BOUNDARY_CLIPPED"
    assert normalization["correction_count"] == 1


def test_one_pixel_clip_outside_valid_parent_vetoes_the_whole_line() -> None:
    raw = _payload(
        [[[80, 10, 101, 20]]],
        parent_boxes=[[0, 0, 90, 100]],
    )

    normalized, quarantine, _normalization = _build(raw)

    assert all(normalized[axis] == [] for axis in ALIGNED_LINE_AXES)
    offender = quarantine["quarantined_lines"][0]["offenders"][0]
    assert offender["reasons"] == ["POST_CLIP_OUTSIDE_PARENT_REC_BOX"]
    assert offender["evidence"] == {
        "page_outlying": True,
        "overshoot_exceeds_maximum": False,
        "post_clip_positive": True,
        "post_clip_contained_in_parent_rec_box": False,
    }


def test_page_clip_that_becomes_nonpositive_vetoes_the_whole_line() -> None:
    raw = _payload([[[100, 10, 101, 20]]])

    normalized, quarantine, _normalization = _build(raw)

    assert all(normalized[axis] == [] for axis in ALIGNED_LINE_AXES)
    offender = quarantine["quarantined_lines"][0]["offenders"][0]
    assert offender["clipped_box"] == [100, 10, 100, 20]
    assert offender["reasons"] == ["POST_CLIP_NONPOSITIVE"]
    assert offender["evidence"]["post_clip_positive"] is False


def test_in_page_child_parent_difference_is_not_a_quarantine_trigger() -> None:
    raw = _payload(
        [[[80, 10, 90, 20]]],
        parent_boxes=[[0, 0, 70, 100]],
    )

    normalized, quarantine, normalization = _build(raw)

    assert normalized == raw
    assert quarantine["status"] == "NO_CHANGE"
    assert normalization["status"] == "NO_CHANGE"


def test_multiple_offending_children_remove_one_line_across_every_aligned_axis() -> None:
    raw = _payload(
        [
            [[10, 10, 20, 20]],
            [[-2, 10, 10, 20], [90, 10, 102, 20]],
            [[30, 30, 40, 40]],
        ]
    )
    before = deepcopy(raw)

    normalized, quarantine, _normalization = _build(raw)

    assert raw == before
    for axis in ALIGNED_LINE_AXES:
        assert normalized[axis] == [before[axis][0], before[axis][2]]
    assert quarantine["quarantined_line_count"] == 1
    assert quarantine["quarantined_word_count"] == 2
    assert [
        offender["word_index"] for offender in quarantine["quarantined_lines"][0]["offenders"]
    ] == [0, 1]
    assert quarantine["quarantined_lines"][0]["reasons"] == ["PAGE_OVERSHOOT_GT_1PX"]


@pytest.mark.parametrize("axis", ALIGNED_LINE_AXES)
def test_every_misaligned_provider_line_axis_fails_closed(axis: str) -> None:
    raw = _payload([[[10, 10, 20, 20]]])
    raw[axis].append(deepcopy(raw[axis][0]))

    with pytest.raises(PPOCRV6LineQuarantineError, match="axis lengths differ"):
        _build(raw)


@pytest.mark.parametrize(
    ("field", "invalid_box", "message"),
    [
        ("rec_boxes", [0, 0, 0, 100], "positive area"),
        ("rec_boxes", [-1, 0, 100, 100], "page-contained"),
        ("rec_boxes", [False, 0, 100, 100], "non-boolean"),
        ("text_word_boxes", [10, 10, 10, 20], "positive area"),
        ("text_word_boxes", [True, 10, 20, 20], "non-boolean"),
        ("text_word_boxes", [10, 10, float("nan"), 20], "finite"),
    ],
)
def test_invalid_parent_and_child_boxes_fail_closed(
    field: str,
    invalid_box: list[object],
    message: str,
) -> None:
    raw = _payload([[[10, 10, 20, 20]]])
    if field == "rec_boxes":
        raw[field][0] = invalid_box
    else:
        raw[field][0][0] = invalid_box

    with pytest.raises(PPOCRV6LineQuarantineError, match=message):
        _build(raw)


def test_word_text_and_box_axis_length_difference_fails_closed() -> None:
    raw = _payload([[[10, 10, 20, 20]]])
    raw["text_word"][0].append("extra")

    with pytest.raises(PPOCRV6LineQuarantineError, match="word axis lengths differ"):
        _build(raw)


@pytest.mark.parametrize(
    ("width", "height"),
    [
        (True, 100),
        (100, False),
        (100.0, 100),
        (100, 100.0),
        (0, 100),
        (100, -1),
    ],
)
def test_render_dimensions_require_typed_positive_integers(
    width: object,
    height: object,
) -> None:
    with pytest.raises(PPOCRV6LineQuarantineError, match="positive integer"):
        build_ppocrv6_page_outlying_child_line_quarantine(
            _payload([[[10, 10, 20, 20]]]),
            pixel_width=width,
            pixel_height=height,
            normalization_authority=_authority(),
        )


def test_validator_rejects_boolean_substitution_for_integer_ledger_count() -> None:
    raw = _payload([[[-2, 10, 20, 20]]])
    normalized, quarantine, normalization = _build(raw)
    drifted = deepcopy(quarantine)
    drifted["raw_line_count"] = True

    with pytest.raises(PPOCRV6LineQuarantineError, match="typed replay"):
        validate_ppocrv6_page_outlying_child_line_quarantine(
            raw,
            normalized,
            drifted,
            normalization,
            pixel_width=100,
            pixel_height=100,
            normalization_authority=_authority(),
        )


def test_retained_payload_is_always_fed_to_existing_strict_normalizer() -> None:
    raw = _payload([[[10, 10, 20, 20]]])
    authority = _authority()
    authority["control_identity_sha256"] = "not-a-hash"

    with pytest.raises(WaveOneRoleBWordBoxNormalizationError, match="authority"):
        build_ppocrv6_page_outlying_child_line_quarantine(
            raw,
            pixel_width=100,
            pixel_height=100,
            normalization_authority=authority,
        )


@pytest.mark.parametrize(
    ("axis", "invalid_value"),
    [
        ("rec_scores", 1.1),
        ("rec_texts", 7),
        ("rec_polys", [[0, 0], [100, 0], [100, 0], [0, 0]]),
        ("dt_polys", [[0, 0], [100, 0], [100, 0], [0, 0]]),
        ("textline_orientation_angles", True),
    ],
)
def test_quarantine_cannot_hide_unrelated_invalid_evidence_on_the_same_line(
    axis: str,
    invalid_value: object,
) -> None:
    raw = _payload([[[-2, 10, 20, 20]]])
    raw[axis][0] = invalid_value

    with pytest.raises(PPOCRV6LineQuarantineError):
        _build(raw)


@pytest.mark.parametrize("field", ["text_type", "model_settings"])
def test_raw_provider_field_set_fails_closed_on_missing_or_extra_fields(field: str) -> None:
    raw = _payload([[[10, 10, 20, 20]]])
    del raw[field]

    with pytest.raises(PPOCRV6LineQuarantineError, match="field set"):
        _build(raw)

    raw = _payload([[[10, 10, 20, 20]]])
    raw["unexpected"] = None
    with pytest.raises(PPOCRV6LineQuarantineError, match="field set"):
        _build(raw)
