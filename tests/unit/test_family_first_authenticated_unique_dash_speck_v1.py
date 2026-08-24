from __future__ import annotations

import copy
import hashlib
import io

import pytest
from PIL import Image, ImageDraw

from bctc_ai.evaluation import family_first_authenticated_unique_dash_speck_v1 as subject


def _png(drawer) -> bytes:
    image = Image.new("RGB", (160, 50), "white")
    drawer(ImageDraw.Draw(image))
    stream = io.BytesIO()
    image.save(stream, format="PNG", optimize=False, compress_level=9)
    return stream.getvalue()


def _real_morphology_crop() -> bytes:
    """Synthetic pixels with the exact ACB p15 component morphology."""

    def draw(draw: ImageDraw.ImageDraw) -> None:
        for y, row in enumerate(("##..", "####", ".##."), 16):
            for x, pixel in enumerate(row, 25):
                if pixel == "#":
                    draw.point((x, y), fill="black")
        for y, row in enumerate((".########.", ".#########", "##########", ".#########"), 30):
            for x, pixel in enumerate(row, 125):
                if pixel == "#":
                    draw.point((x, y), fill="black")

    return _png(draw)


def _binding(payload: bytes) -> dict:
    sha = hashlib.sha256(payload).hexdigest()
    occurrence_sha = hashlib.sha256(b"occurrence-label").hexdigest()
    parent_sha = hashlib.sha256(b"parent-label").hexdigest()
    return {
        "lane_binding": {
            "column_center": 1216.0,
            "column_ordinal": 0,
            "document_ordinal": 5,
            "index_id": "index-authenticated-fixture",
            "physical_page": 15,
            "proposed_raw_pixel_bbox": [1105, 1064, 1327, 1112],
            "recognition_raw_pixel_bbox": [1171, 1070, 1307, 1104],
            "region_id": "ffaprv1:region:" + "3" * 64,
            "region_png_ref": {"sha256": sha, "size_bytes": len(payload)},
            "render_id": "ffaprv1:render:" + "4" * 64,
            "render_ref": {
                "pixel_height": 2339,
                "pixel_width": 1654,
                "sha256": "5" * 64,
                "size_bytes": 1_111_517,
            },
            "white_border": [12, 8, 12, 8],
        },
        "occurrence_binding": {
            "document_line_ordinal": 987,
            "end_document_line_ordinal": 987,
            "end_source_line_index": 34,
            "label_match_sha256": occurrence_sha,
            "occurrence_id": "aforav2:occurrence:" + "1" * 64,
            "page_sequence": 15,
            "role": "INTERBANK_LOAN_VND",
            "role_kind": "ADDITIVE_CHILD",
            "scope_owner_occurrence_id": "aforav2:occurrence:" + "2" * 64,
            "scope_owner_role": "INTERBANK_LOAN_GROUP",
            "source_line_index": 34,
        },
        "parent_binding": {
            "document_line_ordinal": 986,
            "end_document_line_ordinal": 986,
            "end_source_line_index": 33,
            "label_match_sha256": parent_sha,
            "occurrence_id": "aforav2:occurrence:" + "2" * 64,
            "page_sequence": 15,
            "role": "INTERBANK_LOAN_GROUP",
            "role_kind": "STRUCTURAL_GROUP",
            "source_line_index": 33,
        },
        "source_row_sha256": hashlib.sha256(b"exact-source-row").hexdigest(),
        "topology_candidates_id": "aftcv2:result:" + "6" * 64,
        "topology_scan_id": "aftv1:scan:" + "7" * 64,
    }


def test_real_acb_morphology_proves_one_dash_and_one_unrelated_scan_speck() -> None:
    crop = _real_morphology_crop()
    evidence = subject.build_family_first_authenticated_unique_dash_speck_v1(
        crop_png_bytes=crop,
        input_binding=_binding(crop),
    )

    assert evidence["classification"] == subject.CLASSIFICATION
    assert evidence["normalized_value"] == 0
    assert evidence["authority"]["split_glyph_authority"] is False
    assert evidence["original_dash_evidence"]["classification"] == ("UNRESOLVED_NOT_ONE_DASH_GLYPH")
    analysis = evidence["component_analysis"]
    assert analysis["selected_component"] == {
        "aspect_ratio": 2.5,
        "bbox": [125, 30, 135, 34],
        "height": 4,
        "height_ratio": 0.08,
        "horizontal_center_displacement_ratio": 0.3125,
        "ink_fill_ratio": 0.9,
        "ink_pixel_count": 36,
        "vertical_center_displacement_ratio": 0.14,
        "width": 10,
        "width_ratio": 0.0625,
    }
    assert analysis["discarded_total_ink_pixel_count"] == 8
    assert analysis["discarded_components"][0]["bbox"] == [25, 16, 29, 19]
    assert analysis["discarded_components"][0]["horizontal_clear_gap"] == 96
    assert analysis["discarded_components"][0]["vertical_clear_gap"] == 11
    assert analysis["discarded_components"][0]["baseline_overlaps_selected"] is False
    assert evidence["isolated_dash_evidence"]["classification"] == ("VISIBLE_HORIZONTAL_DASH_GLYPH")
    assert evidence["isolated_dash_evidence"]["glyph_metrics"]["component_bbox"] == [
        16,
        11,
        26,
        15,
    ]
    assert (
        subject.validate_family_first_authenticated_unique_dash_speck_replay_v1(
            evidence,
            crop_png_bytes=crop,
            input_binding=_binding(crop),
        )
        == evidence
    )


@pytest.mark.parametrize(
    "drawer",
    [
        # Equals sign: two material horizontal marks.
        lambda draw: (
            draw.rectangle((25, 19, 34, 22), fill="black"),
            draw.rectangle((125, 29, 134, 32), fill="black"),
        ),
        # Minus-number: the disconnected digit is not tiny discardable ink.
        lambda draw: (
            draw.rectangle((125, 28, 134, 31), fill="black"),
            draw.rectangle((25, 12, 31, 37), fill="black"),
        ),
        # Decimal/dot on the same baseline cannot be called scan noise.
        lambda draw: (
            draw.rectangle((125, 29, 134, 32), fill="black"),
            draw.rectangle((25, 29, 27, 31), fill="black"),
        ),
        # Colon: no materially wide dash component.
        lambda draw: (
            draw.rectangle((77, 17, 80, 20), fill="black"),
            draw.rectangle((77, 30, 80, 33), fill="black"),
        ),
        # Connected digit/letter-shaped ink plus a distant speck.
        lambda draw: (
            draw.rectangle((125, 18, 134, 31), fill="black"),
            draw.rectangle((125, 18, 139, 21), fill="black"),
            draw.rectangle((25, 8, 27, 10), fill="black"),
        ),
        # Vertically off-center dash.
        lambda draw: (
            draw.rectangle((125, 9, 134, 12), fill="black"),
            draw.rectangle((25, 30, 27, 32), fill="black"),
        ),
        # A second horizontal mark on another row is not a speck.
        lambda draw: (
            draw.rectangle((25, 16, 34, 19), fill="black"),
            draw.rectangle((125, 30, 134, 33), fill="black"),
        ),
        # Two fragments are never joined into a split glyph.
        lambda draw: (
            draw.rectangle((55, 24, 58, 26), fill="black"),
            draw.rectangle((101, 24, 104, 26), fill="black"),
        ),
        # A near-baseline speck fails the required clear vertical gap.
        lambda draw: (
            draw.rectangle((125, 29, 134, 32), fill="black"),
            draw.rectangle((25, 24, 27, 26), fill="black"),
        ),
    ],
    ids=[
        "equals",
        "minus-number",
        "decimal-dot-baseline",
        "colon",
        "connected-digit",
        "off-center",
        "multiple-rows",
        "split-fragments",
        "near-baseline-speck",
    ],
)
def test_ambiguous_or_numeric_multi_component_crops_fail_closed(drawer) -> None:
    crop = _png(drawer)
    with pytest.raises(subject.FamilyFirstAuthenticatedUniqueDashSpeckV1Error):
        subject.build_family_first_authenticated_unique_dash_speck_v1(
            crop_png_bytes=crop,
            input_binding=_binding(crop),
        )


@pytest.mark.parametrize(
    "mutator",
    [
        lambda value: value["component_analysis"]["selected_component"].__setitem__(
            "ink_pixel_count", 35
        ),
        lambda value: value["component_analysis"].__setitem__("discarded_total_ink_pixel_count", 7),
        lambda value: value["input_binding"]["occurrence_binding"].__setitem__(
            "occurrence_id", "aforav2:occurrence:" + "8" * 64
        ),
        lambda value: value["input_binding"]["parent_binding"].__setitem__(
            "role", "ANOTHER_PARENT"
        ),
        lambda value: value["input_binding"]["lane_binding"].__setitem__("column_ordinal", 1),
        lambda value: value["input_binding"]["lane_binding"][
            "recognition_raw_pixel_bbox"
        ].__setitem__(0, 1170),
        lambda value: value["isolated_crop_ref"].__setitem__("sha256", "0" * 64),
    ],
    ids=[
        "selected-ink",
        "discarded-ink-budget",
        "occurrence",
        "parent",
        "lane",
        "recognition-bbox",
        "isolated-crop-hash",
    ],
)
def test_receipt_field_tampering_rejects_even_before_full_pixel_replay(mutator) -> None:
    crop = _real_morphology_crop()
    evidence = subject.build_family_first_authenticated_unique_dash_speck_v1(
        crop_png_bytes=crop,
        input_binding=_binding(crop),
    )
    attacked = copy.deepcopy(evidence)
    mutator(attacked)
    with pytest.raises(subject.FamilyFirstAuthenticatedUniqueDashSpeckV1Error):
        subject._validate(attacked)


def test_coherently_rehashed_binding_or_pixel_tamper_fails_exact_replay() -> None:
    crop = _real_morphology_crop()
    binding = _binding(crop)
    evidence = subject.build_family_first_authenticated_unique_dash_speck_v1(
        crop_png_bytes=crop,
        input_binding=binding,
    )

    changed_binding = copy.deepcopy(binding)
    changed_binding["source_row_sha256"] = "9" * 64
    with pytest.raises(
        subject.FamilyFirstAuthenticatedUniqueDashSpeckV1Error,
        match="does not replay exactly",
    ):
        subject.validate_family_first_authenticated_unique_dash_speck_replay_v1(
            evidence,
            crop_png_bytes=crop,
            input_binding=changed_binding,
        )

    changed_pixels = bytearray(crop)
    changed_pixels[-12] ^= 1
    with pytest.raises(subject.FamilyFirstAuthenticatedUniqueDashSpeckV1Error):
        subject.validate_family_first_authenticated_unique_dash_speck_replay_v1(
            evidence,
            crop_png_bytes=bytes(changed_pixels),
            input_binding=binding,
        )


def test_binding_contract_contains_no_bank_file_year_period_or_expected_value_route() -> None:
    crop = _real_morphology_crop()
    evidence = subject.build_family_first_authenticated_unique_dash_speck_v1(
        crop_png_bytes=crop,
        input_binding=_binding(crop),
    )
    serialized_keys = str(sorted(evidence["input_binding"])).lower()
    for forbidden in ("bank", "file", "year", "period", "expected"):
        assert forbidden not in serialized_keys
