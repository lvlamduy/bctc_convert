from __future__ import annotations

import hashlib
import io
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image, ImageDraw

from bctc_ai.evaluation import family_first_authenticated_page_region_v1 as region_v1
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _png() -> bytes:
    image = Image.new("RGB", (40, 30), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 12, 20, 14), fill="black")
    stream = io.BytesIO()
    image.save(stream, format="PNG", optimize=False, compress_level=9)
    return stream.getvalue()


def _render_record(payload: bytes) -> dict[str, object]:
    reference = {
        "pixel_height": 30,
        "pixel_width": 40,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }
    material = {
        "archive_id": "archive",
        "authority": dict(region_v1._RENDER_AUTHORITY),
        "document_ordinal": 1,
        "format_version": region_v1.RENDER_FORMAT_VERSION,
        "index_id": "index",
        "physical_page": 2,
        "plan_id": "plan",
        "render_ref": reference,
        "state": "AUTHENTICATED_EXACT_SOURCE_PAGE_RENDER_SNAPSHOT",
    }
    return {
        **material,
        "render_id": "ffaprv1:render:" + canonical_json_sha256_v1(material),
    }


def test_region_crop_is_deterministic_and_detector_independent(monkeypatch) -> None:
    render = _png()
    record = _render_record(render)
    calls: list[tuple[object, int, int]] = []

    def authenticated(capability, *, document_ordinal, physical_page):
        calls.append((capability, document_ordinal, physical_page))
        return record, render

    monkeypatch.setattr(region_v1, "_authenticated_render", authenticated)
    capability = object()
    bbox = [8, 9, 24, 18]
    first = region_v1.crop_authenticated_family_first_page_region_v1(
        capability,
        document_ordinal=1,
        physical_page=2,
        raw_pixel_bbox=bbox,
    )
    second = region_v1.crop_authenticated_family_first_page_region_v1(
        capability,
        document_ordinal=1,
        physical_page=2,
        raw_pixel_bbox=bbox,
    )

    assert calls == [(capability, 1, 2), (capability, 1, 2)]
    assert first == second
    assert first["proposed_raw_pixel_bbox"] == bbox
    recognition_bbox = first["recognition_raw_pixel_bbox"]
    assert bbox[0] <= recognition_bbox[0] <= 10
    assert recognition_bbox[2] >= 21
    assert bbox[1] <= recognition_bbox[1] <= 12
    assert recognition_bbox[3] >= 15
    assert first["ink_localization_status"] == ("GLYPH_COMPONENT_TIGHTENED_WITHIN_PROPOSED_CELL")
    assert first["region_png_ref"] == {
        "sha256": hashlib.sha256(first["region_png_bytes"]).hexdigest(),
        "size_bytes": len(first["region_png_bytes"]),
    }
    with Image.open(io.BytesIO(first["region_png_bytes"])) as crop:
        assert crop.mode == "RGB"
        assert crop.size == (
            recognition_bbox[2] - recognition_bbox[0] + 24,
            recognition_bbox[3] - recognition_bbox[1] + 16,
        )
    material = {
        key: value for key, value in first.items() if key not in {"region_id", "region_png_bytes"}
    }
    assert first["region_id"] == "ffaprv1:region:" + canonical_json_sha256_v1(material)
    bbox[0] = 0
    assert first["proposed_raw_pixel_bbox"] == [8, 9, 24, 18]
    assert first["authority"]["numeric_authority"] is False
    assert first["authority"]["detector_geometry_required"] is False


@pytest.mark.parametrize(
    "bbox",
    (
        (1, 2, 3, 4),
        [True, 2, 3, 4],
        [1.0, 2, 3, 4],
        [-1, 2, 3, 4],
        [1, 2, 1, 4],
        [1, 2, 41, 4],
        [1, 2, 3],
    ),
)
def test_region_crop_rejects_non_exact_or_out_of_bounds_bbox(monkeypatch, bbox) -> None:
    render = _png()
    monkeypatch.setattr(
        region_v1,
        "_authenticated_render",
        lambda *_args, **_kwargs: (_render_record(render), render),
    )
    with pytest.raises(
        region_v1.FamilyFirstAuthenticatedPageRegionV1Error,
        match="region bbox",
    ):
        region_v1.crop_authenticated_family_first_page_region_v1(
            object(), document_ordinal=1, physical_page=2, raw_pixel_bbox=bbox
        )


def test_authenticated_render_replays_live_source_and_page(monkeypatch) -> None:
    render = _png()
    source = b"pdf"
    page_payload = b"page"
    source_ref = {
        "path": "source.pdf",
        "sha256": hashlib.sha256(source).hexdigest(),
        "size_bytes": len(source),
    }
    render_ref = {
        "pixel_height": 30,
        "pixel_width": 40,
        "sha256": hashlib.sha256(render).hexdigest(),
        "size_bytes": len(render),
    }
    page_artifact = {
        "document_ordinal": 1,
        "page_freeze": {"physical_page": 2, "render_ref": render_ref},
        "physical_page": 2,
        "plan_id": "plan",
    }
    plan = {
        "documents": [
            {
                "document_ordinal": 1,
                "page_count": 2,
                "source_pdf_ref": source_ref,
            }
        ],
        "plan_id": "plan",
        "render_policy": {"dpi": 144},
    }
    index_manifest = {"documents": [{"document_ordinal": 1}], "index_id": "index"}
    archive_manifest = {"archive_id": "archive"}
    archive_capability = object()
    root = Path("/project")
    archive_state = SimpleNamespace(root=root)
    index_state = SimpleNamespace(root=root, archive=archive_capability)
    counts = {"index": 0, "archive": 0, "page": 0, "source": 0}

    def live_index(capability):
        assert capability == "capability"
        counts["index"] += 1
        return index_state, index_manifest

    def archive_payloads(capability):
        assert capability is archive_capability
        counts["archive"] += 1
        return archive_state, archive_manifest, {}, plan, {}

    def root_bytes(_root, relative, _label):
        if str(relative).endswith("page.json"):
            counts["page"] += 1
            return page_payload
        assert str(relative) == "source.pdf"
        counts["source"] += 1
        return source

    monkeypatch.setattr(region_v1.index_v1, "_live_index", live_index)
    monkeypatch.setattr(region_v1.archive_v1, "_archive_payloads", archive_payloads)
    monkeypatch.setattr(region_v1.archive_v1, "_root_bytes", root_bytes)
    monkeypatch.setattr(region_v1.archive_v1, "_historical_cache_object", lambda *_args: {})
    monkeypatch.setattr(region_v1.archive_v1, "_page_artifact", lambda *_args: page_artifact)
    monkeypatch.setattr(region_v1.archive_v1, "_matches_ref", lambda *_args: None)
    monkeypatch.setattr(
        region_v1.freeze_v1, "_validate_page", lambda *_args: page_artifact["page_freeze"]
    )
    monkeypatch.setattr(region_v1, "_render_page", lambda *_args, **_kwargs: render)

    record, payload = region_v1._authenticated_render(
        "capability", document_ordinal=1, physical_page=2
    )
    assert payload == render
    assert record["document_ordinal"] == 1
    assert record["physical_page"] == 2
    assert record["render_ref"] == render_ref
    assert counts == {"index": 2, "archive": 2, "page": 2, "source": 2}


def test_authenticated_render_rejects_source_change_during_replay(monkeypatch) -> None:
    render = _png()
    source_ref = {
        "path": "source.pdf",
        "sha256": hashlib.sha256(b"pdf").hexdigest(),
        "size_bytes": 3,
    }
    page_artifact = {
        "document_ordinal": 1,
        "page_freeze": {
            "physical_page": 1,
            "render_ref": {
                "pixel_height": 30,
                "pixel_width": 40,
                "sha256": hashlib.sha256(render).hexdigest(),
                "size_bytes": len(render),
            },
        },
        "physical_page": 1,
        "plan_id": "plan",
    }
    plan = {
        "documents": [{"document_ordinal": 1, "page_count": 1, "source_pdf_ref": source_ref}],
        "plan_id": "plan",
        "render_policy": {"dpi": 144},
    }
    state = SimpleNamespace(root=Path("/project"), archive=object())
    archive_state = SimpleNamespace(root=state.root)
    source_reads = 0

    monkeypatch.setattr(
        region_v1.index_v1,
        "_live_index",
        lambda *_args: (state, {"documents": [{"document_ordinal": 1}], "index_id": "i"}),
    )
    monkeypatch.setattr(
        region_v1.archive_v1,
        "_archive_payloads",
        lambda *_args: (archive_state, {"archive_id": "a"}, {}, plan, {}),
    )

    def root_bytes(_root, relative, _label):
        nonlocal source_reads
        if str(relative).endswith("page.json"):
            return b"page"
        source_reads += 1
        return b"pdf" if source_reads == 1 else b"changed"

    monkeypatch.setattr(region_v1.archive_v1, "_root_bytes", root_bytes)
    monkeypatch.setattr(region_v1.archive_v1, "_historical_cache_object", lambda *_args: {})
    monkeypatch.setattr(region_v1.archive_v1, "_page_artifact", lambda *_args: page_artifact)
    monkeypatch.setattr(region_v1.archive_v1, "_matches_ref", lambda *_args: None)
    monkeypatch.setattr(
        region_v1.freeze_v1, "_validate_page", lambda *_args: page_artifact["page_freeze"]
    )
    monkeypatch.setattr(region_v1, "_render_page", lambda *_args, **_kwargs: render)

    with pytest.raises(
        region_v1.FamilyFirstAuthenticatedPageRegionV1Error,
        match="changed during render replay",
    ):
        region_v1._authenticated_render(state, document_ordinal=1, physical_page=1)


def test_render_batch_replays_live_roots_once_for_multiple_pages(monkeypatch) -> None:
    render = _png()
    source = b"pdf"
    source_ref = {
        "path": "source-1.pdf",
        "sha256": hashlib.sha256(source).hexdigest(),
        "size_bytes": len(source),
    }
    render_ref = {
        "pixel_height": 30,
        "pixel_width": 40,
        "sha256": hashlib.sha256(render).hexdigest(),
        "size_bytes": len(render),
    }
    plan = {
        "documents": [
            {
                "document_ordinal": ordinal,
                "page_count": 1,
                "source_pdf_ref": {**source_ref, "path": f"source-{ordinal}.pdf"},
            }
            for ordinal in (1, 2)
        ],
        "plan_id": "plan",
        "render_policy": {"dpi": 144},
    }
    index_manifest = {
        "documents": [{"document_ordinal": ordinal} for ordinal in (1, 2)],
        "index_id": "index",
    }
    archive_manifest = {"archive_id": "archive"}
    archive_capability = object()
    root = Path("/project")
    archive_state = SimpleNamespace(root=root)
    index_state = SimpleNamespace(root=root, archive=archive_capability)
    counts = {"index": 0, "archive": 0, "page": 0, "source": 0}

    def live_index(_capability):
        counts["index"] += 1
        return index_state, index_manifest

    def archive_payloads(_capability):
        counts["archive"] += 1
        return archive_state, archive_manifest, {}, plan, {}

    def root_bytes(_root, relative, _label):
        if str(relative).endswith("page.json"):
            counts["page"] += 1
            return b"page-1" if "document-0001" in str(relative) else b"page-2"
        counts["source"] += 1
        return source

    monkeypatch.setattr(region_v1.index_v1, "_live_index", live_index)
    monkeypatch.setattr(region_v1.archive_v1, "_archive_payloads", archive_payloads)
    monkeypatch.setattr(region_v1.archive_v1, "_root_bytes", root_bytes)
    monkeypatch.setattr(
        region_v1.archive_v1,
        "_historical_cache_object",
        lambda payload, _label: {"document_ordinal": int(payload[-1:])},
    )
    monkeypatch.setattr(
        region_v1.archive_v1,
        "_page_artifact",
        lambda value: {
            "document_ordinal": value["document_ordinal"],
            "page_freeze": {"physical_page": 1, "render_ref": render_ref},
            "physical_page": 1,
            "plan_id": "plan",
        },
    )
    monkeypatch.setattr(region_v1.archive_v1, "_matches_ref", lambda *_args: None)
    monkeypatch.setattr(region_v1.freeze_v1, "_validate_page", lambda value: value)
    monkeypatch.setattr(region_v1, "_render_page", lambda *_args, **_kwargs: render)

    snapshots = region_v1.read_authenticated_family_first_page_renders_v1(
        "capability",
        selections=(
            {"document_ordinal": 1, "physical_page": 1},
            {"document_ordinal": 2, "physical_page": 1},
        ),
    )

    assert [snapshot["document_ordinal"] for snapshot in snapshots] == [1, 2]
    assert counts == {"index": 2, "archive": 2, "page": 4, "source": 4}


def test_render_reference_requires_exact_types() -> None:
    reference = {
        "pixel_height": 1,
        "pixel_width": 1,
        "sha256": "0" * 64,
        "size_bytes": 1,
    }
    assert region_v1._render_reference(reference) == reference
    for field, invalid in (
        ("pixel_height", True),
        ("pixel_width", 1.0),
        ("sha256", "A" * 64),
        ("size_bytes", True),
    ):
        forged = {**reference, field: invalid}
        with pytest.raises(region_v1.FamilyFirstAuthenticatedPageRegionV1Error):
            region_v1._render_reference(forged)


def test_blank_proposed_cell_is_not_manufactured_into_a_glyph() -> None:
    image = Image.new("RGB", (40, 30), "white")
    proposed = [8, 9, 24, 18]
    recognition, status = region_v1._foreground_recognition_bbox(image, proposed)
    assert recognition == proposed
    assert status == "NO_GLYPH_COMPONENT_FULL_PROPOSED_CELL_PRESERVED"


def test_foreground_localization_discards_split_edge_table_rule_but_keeps_dash() -> None:
    image = Image.new("RGB", (160, 50), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((124, 21, 131, 24), fill="black")
    draw.line((12, 42, 57, 42), fill="black", width=1)
    draw.line((59, 42, 147, 42), fill="black", width=1)

    recognition, status = region_v1._foreground_recognition_bbox(image, [10, 5, 150, 46])

    assert status == "GLYPH_COMPONENT_TIGHTENED_WITHIN_PROPOSED_CELL"
    assert recognition[1] <= 21
    assert recognition[3] < 42
    assert recognition[0] <= 124 < 132 <= recognition[2]


def test_foreground_localization_discards_widely_fragmented_rule_and_scan_specks() -> None:
    image = Image.new("RGB", (200, 58), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((119, 27, 128, 30), fill="black")
    for x, y in ((35, 18), (90, 19), (174, 11), (58, 41)):
        draw.rectangle((x, y, x + 2, y + 2), fill="black")
    draw.line((12, 47, 28, 47), fill="black", width=1)
    draw.line((76, 47, 88, 47), fill="black", width=1)
    draw.line((101, 47, 107, 47), fill="black", width=1)

    recognition, status = region_v1._foreground_recognition_bbox(
        image, [0, 0, image.width, image.height]
    )

    assert status == "GLYPH_COMPONENT_TIGHTENED_WITHIN_PROPOSED_CELL"
    assert recognition[0] <= 119 < 129 <= recognition[2]
    assert recognition[1] <= 27 < 31 <= recognition[3]
    assert recognition[3] < 41


def test_foreground_localization_does_not_discard_a_lone_table_rule_into_blank() -> None:
    image = Image.new("RGB", (160, 50), "white")
    ImageDraw.Draw(image).line((12, 42, 147, 42), fill="black", width=1)
    proposed = [10, 5, 150, 46]

    recognition, status = region_v1._foreground_recognition_bbox(image, proposed)

    assert status == "NO_GLYPH_COMPONENT_FULL_PROPOSED_CELL_PRESERVED"
    assert recognition == proposed


def test_page_render_batch_selection_is_exact_unique_and_source_ordered() -> None:
    valid = ({"document_ordinal": 1, "physical_page": 2},)
    assert region_v1._render_selections(valid) == ((1, 2),)
    for value in (
        [valid[0]],
        ({**valid[0], "bank": "ACB"},),
        ({"document_ordinal": True, "physical_page": 2},),
        (valid[0], valid[0]),
    ):
        with pytest.raises(region_v1.FamilyFirstAuthenticatedPageRegionV1Error):
            region_v1._render_selections(value)


def test_render_snapshot_crop_rejects_coherent_record_with_changed_bytes() -> None:
    render = _png()
    snapshot = {**_render_record(render), "render_png_bytes": render}
    region_v1._crop_authenticated_family_first_page_render_snapshot_v1(
        snapshot, raw_pixel_bbox=[8, 9, 24, 18]
    )
    attacked = {**snapshot, "render_png_bytes": render + b"tamper"}
    with pytest.raises(region_v1.FamilyFirstAuthenticatedPageRegionV1Error, match="snapshot bytes"):
        region_v1._crop_authenticated_family_first_page_render_snapshot_v1(
            attacked, raw_pixel_bbox=[8, 9, 24, 18]
        )
