from __future__ import annotations

import copy
import hashlib
import io

import pytest
from PIL import Image, ImageDraw

from bctc_ai.evaluation import family_first_authenticated_page_region_v1 as region_v1
from bctc_ai.evaluation.family_first_authenticated_snapshot_cell_dash_v1 import (
    BINDING_KIND,
    FamilyFirstAuthenticatedSnapshotCellDashV1Error,
    build_family_first_authenticated_snapshot_cell_dash_v1,
    validate_family_first_authenticated_snapshot_cell_dash_replay_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_BBOX = [60, 15, 94, 45]


def _render(kind: str) -> bytes:
    image = Image.new("RGB", (100, 60), "white")
    draw = ImageDraw.Draw(image)
    if kind == "dash":
        draw.rectangle((73, 28, 82, 32), fill="black")
    elif kind == "degraded":
        draw.rectangle((76, 29, 77, 31), fill="black")
    elif kind != "blank":
        raise AssertionError(kind)
    stream = io.BytesIO()
    image.save(stream, format="PNG", optimize=False, compress_level=9)
    return stream.getvalue()


def _ref(label: str) -> dict[str, object]:
    payload = label.encode()
    return {
        "path": f"fixture/{label}.bin",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _fixture(kind: str = "dash", *, raw_text: str = "-") -> tuple[dict, dict, dict]:
    render = _render(kind)
    render_ref = {
        "pixel_height": 60,
        "pixel_width": 100,
        "sha256": hashlib.sha256(render).hexdigest(),
        "size_bytes": len(render),
    }
    packet_material = {
        "assurance": "AUDITED",
        "bank_provenance": "SYNTHETIC",
        "document_evidence_root_sha256": hashlib.sha256(b"document-root").hexdigest(),
        "document_id": "document-fixture",
        "document_ordinal": 3,
        "line_count": 1,
        "page_count": 5,
        "period": "ANNUAL",
        "scope": "CONSOLIDATED",
        "source_pdf_ref": _ref("source-pdf"),
        "year": 2025,
    }
    packet = {
        **packet_material,
        "packet_id": "ffdesv1:document:" + canonical_json_sha256_v1(packet_material),
    }
    line = {
        "bbox": list(_BBOX),
        "crop_ref": _ref("selected-line-crop"),
        "line_ordinal": 0,
        "numeric_recognition": {"raw_prediction": raw_text, "reader_score": 0.97},
        "sample_id": "sample-existing-numeric-cell",
        "vietocr_text": raw_text,
    }
    other_render = b"sealed-page-four"
    dimensions = [
        {
            "physical_page": 4,
            "pixel_height": 60,
            "pixel_width": 100,
            "render_sha256": hashlib.sha256(other_render).hexdigest(),
            "render_size_bytes": len(other_render),
        },
        {
            "physical_page": 5,
            "pixel_height": 60,
            "pixel_width": 100,
            "render_sha256": render_ref["sha256"],
            "render_size_bytes": render_ref["size_bytes"],
        },
    ]
    joined_pages = [
        {"lines": [], "page_sequence": 4, "page_width": 100},
        {"lines": [line], "page_sequence": 5, "page_width": 100},
    ]
    selection_material = {
        "document_id": packet["document_id"],
        "document_ordinal": 3,
        "joined_pages": joined_pages,
        "selected_page_dimensions": dimensions,
    }
    selection_id = "ffoqcv1:selection:" + canonical_json_sha256_v1(selection_material)
    snapshot_material = {
        "document_packet": packet,
        "joined_pages": joined_pages,
        "manifest_id": "ffdesv1:manifest:fixture",
        "query_selection_id": selection_id,
        "selected_page_dimensions": dimensions,
        "state": "AUTHENTICATED_IMMUTABLE_SQLITE_SELECTED_PAGE_EVIDENCE",
    }
    snapshot = {
        **snapshot_material,
        "snapshot_id": "ffdesv1:selected:" + canonical_json_sha256_v1(snapshot_material),
    }
    render_material = {
        "archive_id": "archive-fixture",
        "authority": dict(region_v1._RENDER_AUTHORITY),
        "document_ordinal": 3,
        "format_version": region_v1.RENDER_FORMAT_VERSION,
        "index_id": "index-fixture",
        "physical_page": 5,
        "plan_id": "plan-fixture",
        "render_ref": render_ref,
        "state": "AUTHENTICATED_EXACT_SOURCE_PAGE_RENDER_SNAPSHOT",
    }
    render_snapshot = {
        **render_material,
        "render_id": "ffaprv1:render:" + canonical_json_sha256_v1(render_material),
        "render_png_bytes": render,
    }
    binding = {
        "binding_kind": BINDING_KIND,
        "document_ordinal": 3,
        "local_to_physical_page": {
            "local_page_sequence": 2,
            "physical_page": 5,
        },
        "raw_pixel_bbox": list(_BBOX),
        "render_dimensions": {"pixel_height": 60, "pixel_width": 100},
        "render_id": render_snapshot["render_id"],
        "sample_id": line["sample_id"],
        "snapshot_id": snapshot["snapshot_id"],
        "source_line_index": 0,
    }
    return snapshot, render_snapshot, binding


def test_existing_selected_numeric_line_binds_exact_render_crop_and_pixel_dash() -> None:
    snapshot, render, binding = _fixture()

    evidence = build_family_first_authenticated_snapshot_cell_dash_v1(
        selected_snapshot=snapshot,
        render_snapshot=render,
        cell_binding=binding,
    )

    assert evidence["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH"
    assert evidence["normalized_value"] == 0
    assert evidence["input_binding"]["local_to_physical_page"] == {
        "local_page_sequence": 2,
        "physical_page": 5,
    }
    assert evidence["crop_binding"]["proposed_raw_pixel_bbox"] == _BBOX
    assert evidence["render_binding"]["render_id"] == render["render_id"]
    assert (
        evidence["dash_evidence"]["crop_ref"]["sha256"]
        == evidence["crop_binding"]["region_png_ref"]["sha256"]
    )
    assert evidence["authority"]["selected_snapshot_text_used_for_classification"] is False
    assert (
        validate_family_first_authenticated_snapshot_cell_dash_replay_v1(
            evidence,
            selected_snapshot=snapshot,
            render_snapshot=render,
            cell_binding=binding,
        )
        == evidence
    )


@pytest.mark.parametrize(
    ("kind", "raw_text", "classification"),
    [
        ("blank", "-", "UNRESOLVED_NOT_ONE_DASH_GLYPH"),
        ("degraded", "-", "DEGRADED_CENTERED_SHORT_MARK_CANDIDATE"),
    ],
)
def test_text_only_dash_blank_and_degraded_mark_never_become_zero(
    kind: str, raw_text: str, classification: str
) -> None:
    snapshot, render, binding = _fixture(kind, raw_text=raw_text)

    evidence = build_family_first_authenticated_snapshot_cell_dash_v1(
        selected_snapshot=snapshot,
        render_snapshot=render,
        cell_binding=binding,
    )

    assert evidence["classification"] == classification
    assert evidence["normalized_value"] is None
    assert evidence["dash_evidence"]["normalized_value"] is None


def test_detector_hole_without_stable_authenticated_proposal_fails_closed() -> None:
    snapshot, render, binding = _fixture()
    binding["binding_kind"] = "DETECTOR_HOLE_CALLER_PROPOSED_BBOX"

    with pytest.raises(
        FamilyFirstAuthenticatedSnapshotCellDashV1Error,
        match="authenticated stable geometry proposal",
    ):
        build_family_first_authenticated_snapshot_cell_dash_v1(
            selected_snapshot=snapshot,
            render_snapshot=render,
            cell_binding=binding,
        )


@pytest.mark.parametrize(
    "mutator",
    [
        lambda value: value.__setitem__("document_ordinal", 2),
        lambda value: value.__setitem__("snapshot_id", "ffdesv1:selected:forged"),
        lambda value: value.__setitem__("sample_id", "sample-forged"),
        lambda value: value.__setitem__("source_line_index", 1),
        lambda value: value["local_to_physical_page"].__setitem__("local_page_sequence", 1),
        lambda value: value["local_to_physical_page"].__setitem__("physical_page", 4),
        lambda value: value.__setitem__("raw_pixel_bbox", [61, 15, 94, 45]),
        lambda value: value.__setitem__("render_id", "ffaprv1:render:forged"),
        lambda value: value["render_dimensions"].__setitem__("pixel_width", 101),
    ],
)
def test_replay_rejects_every_cell_snapshot_page_geometry_and_render_binding_tamper(
    mutator,
) -> None:
    snapshot, render, binding = _fixture()
    evidence = build_family_first_authenticated_snapshot_cell_dash_v1(
        selected_snapshot=snapshot,
        render_snapshot=render,
        cell_binding=binding,
    )
    attacked = copy.deepcopy(binding)
    mutator(attacked)

    with pytest.raises(FamilyFirstAuthenticatedSnapshotCellDashV1Error):
        validate_family_first_authenticated_snapshot_cell_dash_replay_v1(
            evidence,
            selected_snapshot=snapshot,
            render_snapshot=render,
            cell_binding=attacked,
        )


def test_exact_replay_rejects_render_bytes_and_coordinated_record_rehash_tamper() -> None:
    snapshot, render, binding = _fixture()
    evidence = build_family_first_authenticated_snapshot_cell_dash_v1(
        selected_snapshot=snapshot,
        render_snapshot=render,
        cell_binding=binding,
    )
    attacked_render = {**render, "render_png_bytes": render["render_png_bytes"] + b"tamper"}
    with pytest.raises(FamilyFirstAuthenticatedSnapshotCellDashV1Error):
        validate_family_first_authenticated_snapshot_cell_dash_replay_v1(
            evidence,
            selected_snapshot=snapshot,
            render_snapshot=attacked_render,
            cell_binding=binding,
        )

    attacked_evidence = copy.deepcopy(evidence)
    attacked_evidence["normalized_value"] = None
    material = copy.deepcopy(attacked_evidence)
    material.pop("evidence_id")
    attacked_evidence["evidence_id"] = "ffascdv1:evidence:" + canonical_json_sha256_v1(material)
    with pytest.raises(FamilyFirstAuthenticatedSnapshotCellDashV1Error):
        validate_family_first_authenticated_snapshot_cell_dash_replay_v1(
            attacked_evidence,
            selected_snapshot=snapshot,
            render_snapshot=render,
            cell_binding=binding,
        )
