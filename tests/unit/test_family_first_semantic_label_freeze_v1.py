from __future__ import annotations

import copy
import io

import pytest
from PIL import Image

from bctc_ai.evaluation.family_first_semantic_label_freeze_v1 import (
    FamilyFirstSemanticLabelFreezeV1Error,
    build_family_first_semantic_label_page_freeze_v1,
    project_ordered_detector_line_axis_v1,
    validate_family_first_semantic_label_page_freeze_replay_v1,
)


def _render() -> bytes:
    image = Image.new("RGB", (120, 100), color=(210, 220, 230))
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def _detector() -> dict[str, object]:
    return {
        "dt_polys": [
            [[70, 40], [110, 40], [110, 55], [70, 55]],
            [[5, 10], [55, 10], [55, 25], [5, 25]],
            [[5, 40], [55, 40], [55, 55], [5, 55]],
        ],
        "dt_scores": [0.8, 0.9, 0.7],
        "input_path": "ignored-provider-path.png",
        "page_index": None,
    }


def test_all_detector_lines_are_ordered_by_rows_then_columns_and_cropped() -> None:
    record, crops = build_family_first_semantic_label_page_freeze_v1(
        render_png_bytes=_render(),
        detector_payload=_detector(),
        physical_page=7,
        crop_path_prefix="output/family-first/document-0001/page-0007/crops",
    )

    assert [item["detector_index"] for item in record["detector_line_axis"]] == [1, 2, 0]
    assert [item["line_ordinal"] for item in record["detector_line_axis"]] == [0, 1, 2]
    assert record["metrics"] == {
        "crop_count": 3,
        "detected_line_count": 3,
        "excluded_detected_line_count": 0,
    }
    assert len(crops) == 3
    assert all(item.startswith(b"\x89PNG\r\n\x1a\n") for item in crops)
    assert all(Image.open(io.BytesIO(item)).mode == "RGB" for item in crops)
    assert record["crops"][0]["padded_source_bbox_raw_pixels"] == [0, 6, 63, 29]
    assert record["authority"]["detector_recognition_text_accessed"] is False
    assert record["authority"]["bank_file_page_period_family_used_for_line_selection"] is False

    assert (
        validate_family_first_semantic_label_page_freeze_replay_v1(
            record,
            crops,
            render_png_bytes=_render(),
            detector_payload=_detector(),
            physical_page=7,
            crop_path_prefix="output/family-first/document-0001/page-0007/crops",
        )
        == record
    )


def test_numeric_or_right_side_lines_are_not_geometry_filtered() -> None:
    axis = project_ordered_detector_line_axis_v1(_detector(), pixel_width=120, pixel_height=100)

    assert len(axis) == 3
    assert any(item["raw_pixel_bbox"][0] == 70 for item in axis)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload["dt_polys"][0].__setitem__(0, [False, 1]),
        lambda payload: payload["dt_polys"][0].__setitem__(0, [-1, 1]),
        lambda payload: payload["dt_polys"].__setitem__(
            0,
            [[70, 40], [80, 40], [90, 40], [100, 40]],
        ),
        lambda payload: payload["dt_scores"].__setitem__(0, float("nan")),
        lambda payload: payload.update({"rec_texts": ["forbidden"]}),
    ],
)
def test_malformed_or_recognition_bearing_detector_payload_fails_closed(mutation) -> None:
    payload = copy.deepcopy(_detector())
    mutation(payload)

    with pytest.raises(FamilyFirstSemanticLabelFreezeV1Error):
        project_ordered_detector_line_axis_v1(payload, pixel_width=120, pixel_height=100)


def test_crop_or_record_tamper_fails_exact_replay() -> None:
    record, crops = build_family_first_semantic_label_page_freeze_v1(
        render_png_bytes=_render(),
        detector_payload=_detector(),
        physical_page=1,
        crop_path_prefix="output/family-first/document-0001/page-0001/crops",
    )
    tampered_record = copy.deepcopy(record)
    tampered_record["detector_line_axis"][0]["detector_score"] = 0.1
    tampered_crops = (crops[0] + b"x", *crops[1:])

    with pytest.raises(FamilyFirstSemanticLabelFreezeV1Error):
        validate_family_first_semantic_label_page_freeze_replay_v1(
            tampered_record,
            crops,
            render_png_bytes=_render(),
            detector_payload=_detector(),
            physical_page=1,
            crop_path_prefix="output/family-first/document-0001/page-0001/crops",
        )
    with pytest.raises(FamilyFirstSemanticLabelFreezeV1Error, match="replay exactly"):
        validate_family_first_semantic_label_page_freeze_replay_v1(
            record,
            tampered_crops,
            render_png_bytes=_render(),
            detector_payload=_detector(),
            physical_page=1,
            crop_path_prefix="output/family-first/document-0001/page-0001/crops",
        )
