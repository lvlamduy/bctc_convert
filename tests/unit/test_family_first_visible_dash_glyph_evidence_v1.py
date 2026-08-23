from __future__ import annotations

import copy
import io

import pytest
from PIL import Image, ImageDraw

from bctc_ai.evaluation import family_first_visible_dash_glyph_evidence_v1 as dash_v1
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
        "discarded_noncentral_component_count": 0,
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


def test_compact_anti_aliased_pdf_dash_with_eighty_percent_fill_is_zero() -> None:
    def draw_dash(draw: ImageDraw.ImageDraw) -> None:
        draw.rectangle((16, 11, 23, 15), fill="black")
        for point in (
            (16, 11),
            (17, 11),
            (22, 11),
            (23, 11),
            (16, 15),
            (17, 15),
            (22, 15),
            (23, 15),
        ):
            draw.point(point, fill="white")

    evidence = build_family_first_visible_dash_glyph_evidence_v1(crop_png_bytes=_crop(draw_dash))

    assert evidence["glyph_metrics"]["component_aspect_ratio"] == 1.6
    assert evidence["glyph_metrics"]["ink_fill_ratio"] == 0.8
    assert evidence["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH"
    assert evidence["normalized_value"] == 0


def test_compact_anti_aliased_pdf_dash_with_sixty_seven_percent_fill_is_zero() -> None:
    def draw_dash(draw: ImageDraw.ImageDraw) -> None:
        draw.rectangle((16, 11, 23, 15), fill="black")
        for point in (
            (16, 11),
            (17, 11),
            (22, 11),
            (23, 11),
            (16, 15),
            (17, 15),
            (18, 15),
            (21, 15),
            (22, 15),
            (23, 15),
            (16, 12),
            (23, 12),
            (16, 14),
        ):
            draw.point(point, fill="white")

    evidence = build_family_first_visible_dash_glyph_evidence_v1(crop_png_bytes=_crop(draw_dash))

    assert evidence["glyph_metrics"]["component_aspect_ratio"] == 1.6
    assert evidence["glyph_metrics"]["ink_fill_ratio"] == 0.675
    assert evidence["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH"
    assert evidence["normalized_value"] == 0


def test_compact_connected_box_outline_is_not_a_dash() -> None:
    def draw_outline(draw: ImageDraw.ImageDraw) -> None:
        draw.rectangle((16, 11, 23, 15), outline="black", width=1)

    evidence = build_family_first_visible_dash_glyph_evidence_v1(crop_png_bytes=_crop(draw_outline))

    assert evidence["glyph_metrics"]["component_aspect_ratio"] == 1.6
    assert evidence["glyph_metrics"]["ink_fill_ratio"] == 0.55
    assert evidence["classification"] == "UNRESOLVED_NOT_ONE_DASH_GLYPH"


def test_low_resolution_compact_pdf_dash_is_zero_but_square_mark_is_not() -> None:
    compact = build_family_first_visible_dash_glyph_evidence_v1(
        crop_png_bytes=_crop(lambda draw: draw.rectangle((16, 10, 23, 15), fill="black"))
    )
    square = build_family_first_visible_dash_glyph_evidence_v1(
        crop_png_bytes=_crop(lambda draw: draw.rectangle((17, 10, 22, 15), fill="black"))
    )

    assert compact["glyph_metrics"]["component_aspect_ratio"] == 1.33333333
    assert compact["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH"
    assert compact["normalized_value"] == 0
    assert square["glyph_metrics"]["component_aspect_ratio"] == 1.0
    assert square["classification"] == "DEGRADED_CENTERED_SHORT_MARK_CANDIDATE"
    assert square["normalized_value"] is None


def test_overlapping_compact_dash_predicates_replay_with_dash_precedence() -> None:
    crop = _crop(lambda draw: draw.rectangle((16, 10, 23, 15), fill="black"))

    evidence = build_family_first_visible_dash_glyph_evidence_v1(crop_png_bytes=crop)

    assert evidence["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH"
    assert (
        validate_family_first_visible_dash_glyph_evidence_replay_v1(evidence, crop_png_bytes=crop)
        == evidence
    )


def test_tiny_noncentral_rule_artifact_does_not_hide_one_centered_dash() -> None:
    def draw_dash_and_artifact(draw: ImageDraw.ImageDraw) -> None:
        draw.rectangle((38, 39, 46, 44), fill="black")
        draw.rectangle((38, 8, 43, 8), fill="black")

    evidence = build_family_first_visible_dash_glyph_evidence_v1(
        crop_png_bytes=_crop(draw_dash_and_artifact, size=(84, 66))
    )

    assert evidence["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH"
    assert evidence["normalized_value"] == 0
    assert evidence["glyph_metrics"]["component_count"] == 1
    assert evidence["glyph_metrics"]["discarded_noncentral_component_count"] == 1


def test_separate_table_rule_and_scan_specks_do_not_hide_one_dash() -> None:
    def draw_dash_rule_and_specks(draw: ImageDraw.ImageDraw) -> None:
        draw.rectangle((77, 17, 86, 20), fill="black")
        draw.rectangle((12, 35, 91, 36), fill="black")
        draw.rectangle((26, 19, 27, 20), fill="black")
        draw.rectangle((111, 35, 115, 36), fill="black")

    evidence = build_family_first_visible_dash_glyph_evidence_v1(
        crop_png_bytes=_crop(draw_dash_rule_and_specks, size=(128, 49))
    )

    assert evidence["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH"
    assert evidence["normalized_value"] == 0
    assert evidence["glyph_metrics"]["component_bbox"] == [77, 17, 87, 21]
    assert evidence["glyph_metrics"]["discarded_noncentral_component_count"] == 3
    assert evidence["authority"]["separate_horizontal_table_rule_may_be_discarded"] is True


def test_two_plausible_dashes_remain_unresolved_even_with_table_rule() -> None:
    def draw_two_dashes_and_rule(draw: ImageDraw.ImageDraw) -> None:
        draw.rectangle((30, 31, 40, 34), fill="black")
        draw.rectangle((44, 31, 54, 34), fill="black")
        draw.rectangle((5, 50, 78, 51), fill="black")

    evidence = build_family_first_visible_dash_glyph_evidence_v1(
        crop_png_bytes=_crop(draw_two_dashes_and_rule, size=(84, 66))
    )

    assert evidence["classification"] == "UNRESOLVED_NOT_ONE_DASH_GLYPH"
    assert evidence["normalized_value"] is None


def test_tiny_centered_pdf_mark_is_only_a_degraded_candidate() -> None:
    evidence = build_family_first_visible_dash_glyph_evidence_v1(
        crop_png_bytes=_crop(lambda draw: draw.rectangle((16, 10, 17, 12), fill="black"))
    )

    assert evidence["classification"] == "DEGRADED_CENTERED_SHORT_MARK_CANDIDATE"
    assert evidence["normalized_value"] is None
    assert evidence["authority"]["degraded_short_mark_means_zero"] is False


def test_exact_aspect_1_5_antialiased_mark_remains_a_degraded_candidate() -> None:
    metrics = {
        "component_aspect_ratio": 1.5,
        "component_height_ratio": 0.21428571,
        "component_width_ratio": 0.2195122,
        "horizontal_center_displacement_ratio": 0.0,
        "ink_fill_ratio": 0.64814815,
        "vertical_center_displacement_ratio": 0.0,
    }

    assert dash_v1._is_degraded_short_mark_metrics(metrics)


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
