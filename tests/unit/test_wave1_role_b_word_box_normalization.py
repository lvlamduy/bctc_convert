from __future__ import annotations

from copy import deepcopy

import pytest

from bctc_ai.corpus.wave1_role_b_word_box_normalization import (
    NORMALIZATION_LEDGER_FORMAT,
    WORD_BOX_NORMALIZATION_POLICY,
    WaveOneRoleBWordBoxNormalizationError,
    canonical_payload_sha256,
    normalization_policy_sha256,
    normalize_ppocrv6_word_boxes,
)


def _authority() -> dict[str, object]:
    return {
        "policy": deepcopy(WORD_BOX_NORMALIZATION_POLICY),
        "policy_sha256": normalization_policy_sha256(WORD_BOX_NORMALIZATION_POLICY),
        "control_identity_sha256": "c" * 64,
        "normalization_producer_implementation_ledger_sha256": "d" * 64,
    }


def _payload(
    word_box: list[int | float],
    *,
    line_box: list[int | float],
) -> dict[str, object]:
    x0, y0, x1, y1 = line_box
    return {
        "return_word_box": True,
        "rec_texts": ["source visible"],
        "rec_scores": [0.99],
        "rec_polys": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1]]],
        "rec_boxes": [line_box],
        "text_word_boxes": [[word_box]],
        "text_word": [["source"]],
    }


def _normalize(
    payload: dict[str, object],
    *,
    width: int = 100,
    height: int = 100,
) -> tuple[dict[str, object], dict[str, object]]:
    return normalize_ppocrv6_word_boxes(
        payload,
        pixel_width=width,
        pixel_height=height,
        authority=_authority(),
    )


def test_exact_ocb_page_12_right_edge_overshoot_is_clipped_and_ledgered() -> None:
    raw = _payload(
        [1629, 1213, 1649, 1253],
        line_box=[1609, 1213, 1648, 1253],
    )
    before = deepcopy(raw)

    normalized, ledger = _normalize(raw, width=1648, height=2337)

    assert raw == before
    assert normalized["text_word_boxes"] == [[[1629, 1213, 1648, 1253]]]
    assert ledger == {
        "format_version": NORMALIZATION_LEDGER_FORMAT,
        "status": "PAGE_BOUNDARY_CLIPPED",
        "rule_id": WORD_BOX_NORMALIZATION_POLICY["rule_id"],
        "maximum_per_edge_overshoot_pixels": 1,
        "policy_sha256": normalization_policy_sha256(WORD_BOX_NORMALIZATION_POLICY),
        "control_identity_sha256": "c" * 64,
        "normalization_producer_implementation_ledger_sha256": "d" * 64,
        "pixel_dimensions": [1648, 2337],
        "raw_payload_sha256": canonical_payload_sha256(raw),
        "normalized_payload_sha256": canonical_payload_sha256(normalized),
        "correction_count": 1,
        "corrected_edge_count": 1,
        "corrections": [
            {
                "json_path": "$.text_word_boxes[0][0]",
                "line_index": 0,
                "word_index": 0,
                "raw_box": [1629, 1213, 1649, 1253],
                "normalized_box": [1629, 1213, 1648, 1253],
                "per_edge_clip_pixels": {
                    "left": 0,
                    "top": 0,
                    "right": 1,
                    "bottom": 0,
                },
                "validated_line_rec_box": [1609, 1213, 1648, 1253],
            }
        ],
    }


def test_valid_payload_records_no_change_and_byte_stable_hashes() -> None:
    raw = _payload([12, 12, 20, 20], line_box=[10, 10, 30, 30])

    normalized, ledger = _normalize(raw)

    assert normalized == raw
    assert normalized is not raw
    assert ledger["status"] == "NO_CHANGE"
    assert ledger["correction_count"] == 0
    assert ledger["corrected_edge_count"] == 0
    assert ledger["corrections"] == []
    assert ledger["raw_payload_sha256"] == ledger["normalized_payload_sha256"]
    assert ledger["raw_payload_sha256"] == canonical_payload_sha256(raw)


@pytest.mark.parametrize(
    ("raw_box", "line_box", "expected", "edge"),
    [
        ([-1, 12, 20, 20], [0, 10, 30, 30], [0, 12, 20, 20], "left"),
        ([12, -1, 20, 20], [10, 0, 30, 30], [12, 0, 20, 20], "top"),
        ([80, 12, 101, 20], [70, 10, 100, 30], [80, 12, 100, 20], "right"),
        ([12, 80, 20, 101], [10, 70, 30, 100], [12, 80, 20, 100], "bottom"),
    ],
)
def test_each_page_edge_allows_exactly_one_pixel(
    raw_box: list[int],
    line_box: list[int],
    expected: list[int],
    edge: str,
) -> None:
    normalized, ledger = _normalize(_payload(raw_box, line_box=line_box))

    assert normalized["text_word_boxes"] == [[expected]]
    assert ledger["correction_count"] == 1
    assert ledger["corrected_edge_count"] == 1
    assert ledger["corrections"][0]["per_edge_clip_pixels"][edge] == 1


def test_multi_line_multi_word_corrections_are_ordered_and_corner_clipping_is_ledgered() -> None:
    raw = {
        "return_word_box": True,
        "rec_texts": ["line zero", "line one"],
        "rec_scores": [0.99, 0.98],
        "rec_polys": [
            [[0, 0], [100, 0], [100, 30], [0, 30]],
            [[0, 70], [100, 70], [100, 100], [0, 100]],
        ],
        "rec_boxes": [[0, 0, 100, 30], [0, 70, 100, 100]],
        "text_word_boxes": [
            [[10, 5, 20, 15], [80, 5, 101, 15]],
            [[-1, 80, 10, 101], [80, 80, 101, 101]],
        ],
        "text_word": [["line", "zero"], ["line", "one"]],
    }
    before = deepcopy(raw)

    normalized, ledger = _normalize(raw)

    assert raw == before
    assert normalized["text_word_boxes"] == [
        [[10, 5, 20, 15], [80, 5, 100, 15]],
        [[0, 80, 10, 100], [80, 80, 100, 100]],
    ]
    assert [
        (correction["line_index"], correction["word_index"]) for correction in ledger["corrections"]
    ] == [(0, 1), (1, 0), (1, 1)]
    assert ledger["correction_count"] == 3
    assert ledger["corrected_edge_count"] == 5
    assert ledger["corrections"][1]["per_edge_clip_pixels"] == {
        "left": 1,
        "top": 0,
        "right": 0,
        "bottom": 1,
    }


@pytest.mark.parametrize(
    ("raw_box", "line_box"),
    [
        ([-2, 12, 20, 20], [0, 10, 30, 30]),
        ([12, -2, 20, 20], [10, 0, 30, 30]),
        ([80, 12, 102, 20], [70, 10, 100, 30]),
        ([12, 80, 20, 102], [10, 70, 30, 100]),
    ],
)
def test_more_than_one_pixel_on_any_edge_fails_closed(
    raw_box: list[int],
    line_box: list[int],
) -> None:
    with pytest.raises(WaveOneRoleBWordBoxNormalizationError, match="one-pixel"):
        _normalize(_payload(raw_box, line_box=line_box))


@pytest.mark.parametrize(
    "raw_box",
    [
        [10, 10, 10, 20],
        [10, 20, 20, 20],
        [True, 10, 20, 20],
        [float("nan"), 10, 20, 20],
        [10, 10, float("inf"), 20],
    ],
)
def test_nonfinite_boolean_and_raw_degenerate_boxes_fail_closed(
    raw_box: list[int | float],
) -> None:
    with pytest.raises(WaveOneRoleBWordBoxNormalizationError):
        _normalize(_payload(raw_box, line_box=[0, 0, 30, 30]))


def test_clipping_that_makes_a_box_degenerate_fails_closed() -> None:
    with pytest.raises(WaveOneRoleBWordBoxNormalizationError, match="positive area"):
        _normalize(_payload([-1, 10, 0, 20], line_box=[0, 0, 30, 30]))


def test_corrected_box_outside_its_validated_line_fails_closed() -> None:
    raw = _payload([80, 12, 101, 20], line_box=[10, 10, 50, 30])

    with pytest.raises(WaveOneRoleBWordBoxNormalizationError, match="contained"):
        _normalize(raw)


def test_corrected_box_cannot_rely_on_an_invalid_parent_line() -> None:
    raw = _payload([80, 12, 101, 20], line_box=[70, 10, 101, 30])

    with pytest.raises(WaveOneRoleBWordBoxNormalizationError, match="Milestone-A"):
        _normalize(raw)


def test_unchanged_box_retains_existing_milestone_a_line_semantics() -> None:
    raw = _payload([70, 70, 80, 80], line_box=[10, 10, 30, 30])

    normalized, ledger = _normalize(raw)

    assert normalized == raw
    assert ledger["status"] == "NO_CHANGE"


def test_authority_policy_control_and_producer_hashes_fail_closed() -> None:
    raw = _payload([12, 12, 20, 20], line_box=[10, 10, 30, 30])
    for key, value in (
        ("policy_sha256", "0" * 64),
        ("control_identity_sha256", "not-a-hash"),
        ("normalization_producer_implementation_ledger_sha256", "not-a-hash"),
    ):
        authority = _authority()
        authority[key] = value
        with pytest.raises(WaveOneRoleBWordBoxNormalizationError, match="authority|policy"):
            normalize_ppocrv6_word_boxes(
                raw,
                pixel_width=100,
                pixel_height=100,
                authority=authority,
            )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("maximum_per_edge_overshoot_pixels", True),
        ("maximum_per_edge_overshoot_pixels", 1.0),
        ("raw_provider_payload_preserved", 1),
    ],
)
def test_adapter_rejects_typed_policy_drift_even_when_drifted_bytes_are_hashed(
    field: str,
    value: object,
) -> None:
    raw = _payload([12, 12, 20, 20], line_box=[10, 10, 30, 30])
    authority = _authority()
    authority["policy"][field] = value
    authority["policy_sha256"] = canonical_payload_sha256(authority["policy"])

    with pytest.raises(WaveOneRoleBWordBoxNormalizationError, match="policy identity"):
        normalize_ppocrv6_word_boxes(
            raw,
            pixel_width=100,
            pixel_height=100,
            authority=authority,
        )
