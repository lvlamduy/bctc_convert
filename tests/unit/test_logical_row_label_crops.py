from __future__ import annotations

import pytest

from bctc_ai.evaluation.logical_row_label_crops import (
    LogicalRowLabelCropError,
    union_label_bbox,
)


def test_union_label_bbox_preserves_multiline_extent():
    boxes = [[10, 20, 100, 40], [12, 42, 140, 62], [900, 20, 950, 40]]

    assert union_label_bbox(boxes, [0, 1]) == (10, 20, 140, 62)


@pytest.mark.parametrize(
    ("indices", "message"),
    [
        ([], "no valid label-line"),
        ([0, 0], "repeats"),
        ([4], "out of range"),
    ],
)
def test_union_label_bbox_rejects_invalid_label_lines(indices, message):
    with pytest.raises(LogicalRowLabelCropError, match=message):
        union_label_bbox([[10, 20, 100, 40]], indices)


def test_union_label_bbox_rejects_degenerate_box():
    with pytest.raises(LogicalRowLabelCropError, match="degenerate"):
        union_label_bbox([[10, 20, 10, 40]], [0])
