from __future__ import annotations

import copy
import errno
import fcntl
import hashlib
import json
import os
import pickle
import weakref
from pathlib import Path

import pytest

from bctc_ai.evaluation import family_first_semantic_label_archive_v1 as archive
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _plan() -> dict[str, object]:
    return {
        "documents": [
            {
                "document_ordinal": 1,
                "page_count": 1,
                "private_provenance": {
                    "bank": "OPAQUE_AFTER_JOIN",
                    "period": "Q1",
                    "scope": "CONSOLIDATED",
                    "year": 2026,
                },
                "source_pdf_ref": {
                    "path": "source.pdf",
                    "sha256": "a" * 64,
                    "size_bytes": 1,
                },
            }
        ],
        "plan_id": "ffslpv1:plan:" + "1" * 64,
    }


def _batch(crops: tuple[bytes, ...] = (b"first", b"second")) -> dict[str, object]:
    material = {
        "authority": dict(archive._BATCH_AUTHORITY),
        "format_version": archive._BATCH_FORMAT,
        "plan_id": _plan()["plan_id"],
        "sample_count": len(crops),
        "samples": [
            {
                "crop_ref": {
                    "path": (
                        "output/calibration/family-first-semantic-label-cache-v1/"
                        f"documents/document-0001/page-0001/crops/line-{offset:04d}.png"
                    ),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size_bytes": len(payload),
                },
                "sample_id": f"sample-{offset + 1:09d}",
            }
            for offset, payload in enumerate(crops)
        ],
    }
    return {**material, "batch_id": "ffslcv1:batch:" + canonical_json_sha256_v1(material)}


def _index(batch: dict[str, object]) -> dict[str, object]:
    material = {
        "authority": dict(archive._INDEX_AUTHORITY),
        "batch_id": batch["batch_id"],
        "documents": _plan()["documents"],
        "format_version": archive._INDEX_FORMAT,
        "plan_id": _plan()["plan_id"],
        "sample_count": batch["sample_count"],
        "samples": [
            {
                "document_ordinal": 1,
                "line_ordinal": offset,
                "physical_page": 1,
                "sample_id": f"sample-{offset + 1:09d}",
                "source_bbox_raw_pixels": [10, 10 + offset * 20, 100, 25 + offset * 20],
            }
            for offset in range(batch["sample_count"])
        ],
    }
    return {**material, "index_id": "ffslcv1:index:" + canonical_json_sha256_v1(material)}


def _archive_bytes(crops: tuple[bytes, ...]) -> bytes:
    payload = bytearray(archive._MAGIC)
    for crop in crops:
        payload.extend(archive._FRAME.pack(len(crop)))
        payload.extend(crop)
    return bytes(payload)


def test_batch_and_private_index_require_exact_order_type_and_opaque_paths() -> None:
    plan = _plan()
    batch = _batch()
    index = _index(batch)

    assert archive._validate_batch(batch, plan)["sample_count"] == 2
    assert archive._validate_private_index(index, batch, plan)["sample_count"] == 2

    wrong_path = copy.deepcopy(batch)
    wrong_path["samples"][0]["crop_ref"]["path"] = "vietstock_bctc/ACB/secret.pdf"
    material = copy.deepcopy(wrong_path)
    material.pop("batch_id")
    wrong_path["batch_id"] = "ffslcv1:batch:" + canonical_json_sha256_v1(material)
    wrong_index = _index(wrong_path)
    with pytest.raises(archive.FamilyFirstSemanticLabelArchiveV1Error, match="cross-link"):
        archive._validate_private_index(wrong_index, wrong_path, plan)

    bool_count = copy.deepcopy(batch)
    bool_count["sample_count"] = True
    bool_count["samples"] = bool_count["samples"][:1]
    with pytest.raises(archive.FamilyFirstSemanticLabelArchiveV1Error, match="contract"):
        archive._validate_batch(bool_count, plan)


def test_kernel_sealed_session_reads_ordered_immutable_chunks(tmp_path: Path) -> None:
    crops = (b"first-png", b"second-png", b"third-png")
    batch = _batch(crops)
    packed = _archive_bytes(crops)
    relative = Path("cache/crops.ffslcpack")
    path = tmp_path / relative
    path.parent.mkdir()
    path.write_bytes(packed)
    os.chmod(path, 0o444)
    reference = archive._content_ref(relative, packed)
    descriptor = archive._copy_archive_to_sealed_memfd(tmp_path, reference)
    try:
        seals = fcntl.fcntl(descriptor, archive._F_GET_SEALS)
        assert seals == (
            archive._F_SEAL_WRITE
            | archive._F_SEAL_GROW
            | archive._F_SEAL_SHRINK
            | archive._F_SEAL_SEAL
        )
        with pytest.raises(OSError) as failure:
            os.pwrite(descriptor, b"X", 0)
        assert failure.value.errno == errno.EPERM

        cap = archive.AuthenticatedFamilyFirstSemanticLabelArchiveV1(archive._MINT)
        session = archive.AuthenticatedFamilyFirstSemanticLabelReaderSessionV1(archive._MINT)
        archive._SESSIONS[session] = archive._SessionState(
            descriptor=descriptor,
            batch=batch,
            cursor=0,
            offset=len(archive._MAGIC),
            archive=cap,
        )
        first = archive.read_authenticated_family_first_semantic_label_chunk_v1(
            session, maximum_samples=2
        )
        second = archive.read_authenticated_family_first_semantic_label_chunk_v1(
            session, maximum_samples=2
        )
        assert [item["sample_id"] for item in first + second] == [
            "sample-000000001",
            "sample-000000002",
            "sample-000000003",
        ]
        assert tuple(item["crop_png_bytes"] for item in first + second) == crops
        assert (
            archive.read_authenticated_family_first_semantic_label_chunk_v1(
                session, maximum_samples=1
            )
            == ()
        )
    finally:
        os.close(descriptor)


def test_opaque_handles_reject_raw_forged_copy_and_pickle() -> None:
    for cls in (
        archive.AuthenticatedFamilyFirstSemanticLabelArchiveV1,
        archive.AuthenticatedFamilyFirstSemanticLabelReaderSessionV1,
    ):
        with pytest.raises(TypeError):
            cls()
        value = cls(archive._MINT)
        with pytest.raises(TypeError):
            copy.copy(value)
        with pytest.raises(TypeError):
            copy.deepcopy(value)
        with pytest.raises(TypeError):
            pickle.dumps(value)
        forged = object.__new__(cls)
        if cls is archive.AuthenticatedFamilyFirstSemanticLabelArchiveV1:
            with pytest.raises(archive.FamilyFirstSemanticLabelArchiveV1Error):
                archive.project_authenticated_family_first_semantic_label_archive_v1(forged)
        assert weakref.ref(value)() is value


def test_archive_manifest_is_exact_typed_and_hash_bound() -> None:
    material = {
        "archive_ref": {
            "path": archive.ARCHIVE_PATH.as_posix(),
            "sha256": "a" * 64,
            "size_bytes": 100,
        },
        "authority": dict(archive._AUTHORITY),
        "batch_id": "ffslcv1:batch:" + "b" * 64,
        "batch_ref": {
            "path": archive.BATCH_PATH.as_posix(),
            "sha256": "c" * 64,
            "size_bytes": 100,
        },
        "claim_boundary": archive._CLAIM_BOUNDARY,
        "format_version": archive.FORMAT_VERSION,
        "plan_id": "ffslpv1:plan:" + "d" * 64,
        "private_index_ref": {
            "path": archive.PRIVATE_INDEX_PATH.as_posix(),
            "sha256": "e" * 64,
            "size_bytes": 100,
        },
        "sample_count": 2,
    }
    manifest = {
        **material,
        "archive_id": "ffslav1:archive:" + canonical_json_sha256_v1(material),
    }
    assert archive._manifest(manifest) == manifest

    tampered = json.loads(json.dumps(manifest))
    tampered["sample_count"] = 3
    with pytest.raises(archive.FamilyFirstSemanticLabelArchiveV1Error, match="identity"):
        archive._manifest(tampered)


def test_archive_stage_is_removed_after_injected_sealing_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(archive, "_root", lambda _value: tmp_path)
    monkeypatch.setattr(archive, "_root_bytes", lambda *_args: b"historical")
    monkeypatch.setattr(
        archive,
        "_validate_descendant_plan",
        lambda *_args, **_kwargs: {"plan_id": _plan()["plan_id"]},
    )
    batch = _batch((b"crop",))
    monkeypatch.setattr(archive, "_historical_cache_object", lambda *_args: {})
    monkeypatch.setattr(archive, "_validate_batch", lambda *_args: batch)
    monkeypatch.setattr(archive, "_validate_private_index", lambda *_args: {})
    monkeypatch.setattr(archive, "_validate_cache_replay", lambda *_args: None)
    monkeypatch.setattr(archive, "_clean_head", lambda _root: "a" * 40)

    def fail(_root, stage, *_args):
        (stage / "partial").write_bytes(b"partial")
        raise OSError("injected archive failure")

    monkeypatch.setattr(archive, "_build_archive_stage", fail)
    with pytest.raises(OSError, match="injected"):
        archive.seal_family_first_semantic_label_archive_v1(
            tmp_path, model_cache=tmp_path / "models"
        )
    parent = tmp_path / archive.MANIFEST_PATH.parent.parent
    assert parent.is_dir()
    assert not any(path.name.startswith(".sealed-semantic-reader-v1-") for path in parent.iterdir())
