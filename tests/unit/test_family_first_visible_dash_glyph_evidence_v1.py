from __future__ import annotations

import copy
import io

import pytest
from PIL import Image, ImageDraw

from bctc_ai.evaluation.family_first_visible_dash_glyph_evidence_v1 import (
    FamilyFirstVisibleDashGlyphEvidenceV1Error,
    build_family_first_visible_dash_glyph_evidence_v1,
    validate_family_first_visible_dash_glyph_evidence_replay_v1,
)


def _crop(drawer=None, *, size: tuple[int, int] = (42, 27)) -> bytes:
    image = Image.new("RGB", size, "white")
    if drawer is not None:
        drawer(ImageDraw.Draw(image))
    stream = io.BytesIO()
    image.save(stream, format="PNG", optimize=False, compress_level=9)
    return stream.getvalue()


def test_single_centered_horizontal_glyph_is_typed_dash_zero() -> None:
    crop = _crop(lambda draw: draw.rectangle((16, 11, 25, 15), fill="black"))
    evidence = build_family_first_visible_dash_glyph_evidence_v1(crop_png_bytes=crop)

    assert evidence["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH"
    assert evidence["normalized_value"] == 0
    assert evidence["glyph_metrics"] == {
        "component_aspect_ratio": 2.0,
        "component_bbox": [16, 11, 26, 16],
        "component_count": 1,
        "component_height_ratio": 0.18518519,
        "component_width_ratio": 0.23809524,
        "horizontal_center_displacement_ratio": 0.0,
        "ink_fill_ratio": 1.0,
        "vertical_center_displacement_ratio": 0.0,
    }
    assert evidence["authority"]["blank_crop_means_zero"] is False
    assert evidence["authority"]["numeric_digits_authority"] is False
    assert (
        validate_family_first_visible_dash_glyph_evidence_replay_v1(evidence, crop_png_bytes=crop)
        == evidence
    )


def test_centered_solid_bar_from_embedded_pdf_dash_font_is_zero() -> None:
    crop = _crop(
        lambda draw: draw.rectangle((15, 8, 44, 17), fill="black"),
        size=(60, 27),
    )
    evidence = build_family_first_visible_dash_glyph_evidence_v1(crop_png_bytes=crop)

    assert evidence["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH"
    assert evidence["normalized_value"] == 0
    assert evidence["glyph_metrics"]["component_aspect_ratio"] >= 3.0
    assert evidence["glyph_metrics"]["component_height_ratio"] > 0.35


def test_compact_high_fill_horizontal_dash_is_zero_but_ambiguous_blob_is_not() -> None:
    compact = build_family_first_visible_dash_glyph_evidence_v1(
        crop_png_bytes=_crop(lambda draw: draw.rectangle((16, 11, 23, 15), fill="black"))
    )
    ambiguous = build_family_first_visible_dash_glyph_evidence_v1(
        crop_png_bytes=_crop(
            lambda draw: (
                draw.rectangle((16, 11, 23, 11), fill="black"),
                draw.rectangle((16, 15, 23, 15), fill="black"),
                draw.point((16, 12), fill="black"),
            )
        )
    )

    assert compact["glyph_metrics"]["component_aspect_ratio"] == 1.6
    assert compact["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH"
    assert ambiguous["classification"] == "UNRESOLVED_NOT_ONE_DASH_GLYPH"


@pytest.mark.parametrize(
    "drawer",
    (
        None,
        lambda draw: draw.rectangle((19, 6, 22, 21), fill="black"),
        lambda draw: (
            draw.rectangle((8, 12, 13, 14), fill="black"),
            draw.rectangle((28, 12, 33, 14), fill="black"),
        ),
        lambda draw: draw.rectangle((0, 13, 41, 14), fill="black"),
        lambda draw: draw.rectangle((2, 11, 11, 15), fill="black"),
    ),
)
def test_blank_digit_multiple_rule_or_off_center_glyph_remains_unresolved(drawer) -> None:
    evidence = build_family_first_visible_dash_glyph_evidence_v1(crop_png_bytes=_crop(drawer))
    assert evidence["classification"] == "UNRESOLVED_NOT_ONE_DASH_GLYPH"
    assert evidence["normalized_value"] is None


def test_replay_rejects_pixel_or_record_tamper() -> None:
    crop = _crop(lambda draw: draw.rectangle((16, 11, 25, 15), fill="black"))
    evidence = build_family_first_visible_dash_glyph_evidence_v1(crop_png_bytes=crop)

    with pytest.raises(
        FamilyFirstVisibleDashGlyphEvidenceV1Error,
        match="replay exactly",
    ):
        validate_family_first_visible_dash_glyph_evidence_replay_v1(
            evidence,
            crop_png_bytes=_crop(lambda draw: draw.rectangle((17, 11, 25, 15), fill="black")),
        )

    tampered = copy.deepcopy(evidence)
    tampered["normalized_value"] = None
    with pytest.raises(FamilyFirstVisibleDashGlyphEvidenceV1Error):
        validate_family_first_visible_dash_glyph_evidence_replay_v1(tampered, crop_png_bytes=crop)

    for mutator in (
        lambda value: value.__setitem__("normalized_value", False),
        lambda value: value["glyph_metrics"].__setitem__("component_count", True),
        lambda value: value["crop_ref"].__setitem__("size_bytes", True),
    ):
        tampered = copy.deepcopy(evidence)
        mutator(tampered)
        with pytest.raises(FamilyFirstVisibleDashGlyphEvidenceV1Error):
            validate_family_first_visible_dash_glyph_evidence_replay_v1(
                tampered, crop_png_bytes=crop
            )
