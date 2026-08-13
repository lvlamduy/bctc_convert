from __future__ import annotations

import copy
import gc
import hashlib
import io
import json
import os
import pickle
import weakref
from pathlib import Path
from typing import Any, cast

import pytest
from PIL import Image

import bctc_ai.evaluation.loan_maturity_8bank_ready_panel_v1 as ready
import bctc_ai.evaluation.vietocr_all_line_freezer_v3 as freezer


def _png(width: int, height: int, color: tuple[int, int, int]) -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (width, height), color).save(
        stream, format="PNG", optimize=False, compress_level=6
    )
    return stream.getvalue()


@pytest.fixture
def live_ready(monkeypatch: pytest.MonkeyPatch):
    capability = ready.AuthenticatedLoanMaturity8BankReadyPanelV1(ready._MINT_TOKEN)
    pages = []
    renders = []
    for ordinal, count in enumerate(freezer.EXPECTED_LINE_COUNT_VECTOR, start=1):
        width, height = 48, count * 2 + 8
        pages.append(
            {
                "geometry_authority": "REPLAYED_E0044_READY_V2_CAS",
                "line_bboxes": [[1, index * 2 + 1, 12, index * 2 + 2] for index in range(count)],
                "line_count": count,
                "pixel_height": height,
                "pixel_width": width,
                "render_sha256": "0" * 64,
                "render_size_bytes": 1,
            }
        )
        renders.append(_png(width, height, (ordinal, ordinal + 1, ordinal + 2)))
    audit = {"audit_id": "lm8brpv1:audit:" + "a" * 64}

    def authenticated_state(candidate):
        if candidate is not capability:
            raise ready.LoanMaturity8BankReadyPanelV1Error("unknown or expired")
        return tuple(copy.deepcopy(pages)), tuple(bytes(item) for item in renders), audit

    monkeypatch.setattr(ready, "_authenticated_state", authenticated_state)
    return capability


def _git_binding() -> dict[str, Any]:
    return {
        "commit": "1" * 40,
        "dirty": False,
        "implementation_ref": {
            "path": "src/bctc_ai/evaluation/vietocr_all_line_freezer_v3.py",
            "sha256": "2" * 64,
            "size_bytes": 1,
        },
        "source_tree_oid": "4" * 40,
    }


def _prepare_root(tmp_path: Path) -> Path:
    (tmp_path / "output/development").mkdir(parents=True)
    return tmp_path


def _freeze(tmp_path: Path, live_ready, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(freezer, "_clean_git_binding", lambda _root: _git_binding())
    monkeypatch.setattr(freezer, "_git_commit_is_ancestor", lambda *_args: True)
    return freezer.freeze_authenticated_vietocr_all_line_batch_v3(
        _prepare_root(tmp_path), freezer.ARTIFACT_ROOT, live_ready
    )


def test_positive_freeze_replay_exact_vector_policy_and_firewall(
    tmp_path: Path, live_ready, monkeypatch: pytest.MonkeyPatch
) -> None:
    projection, capability = _freeze(tmp_path, live_ready, monkeypatch)

    assert projection["line_count_vector"] == [85, 109, 110, 101, 91, 88, 87, 164]
    assert projection["sample_count"] == 835
    assert projection["authority"]["crop_bytes_replay_authenticated"] is True
    assert projection["authority"]["raw_projection_self_authenticates"] is False
    manifest = json.loads(
        (tmp_path / freezer.ARTIFACT_ROOT / "frozen/crop_manifest.json").read_text()
    )
    request = json.loads(
        (tmp_path / freezer.ARTIFACT_ROOT / "frozen/reader_request.json").read_text()
    )
    assert manifest["crop_policy"] == freezer.CROP_POLICY
    assert manifest["sample_count"] == len(manifest["samples"]) == 835
    assert [page["line_count"] for page in manifest["pages"]] == list(
        freezer.EXPECTED_LINE_COUNT_VECTOR
    )
    assert manifest["input_batch_id"].startswith("lm8brpv1:batch:")
    assert request["sample_count"] == len(request["samples"]) == 835
    assert request["samples"][0]["sample_id"] == "page-0001-line-0000"
    assert request["samples"][-1]["sample_id"] == "page-0008-line-0163"
    serialized = json.dumps({"m": manifest, "r": request, "p": projection}).lower()
    for forbidden in (
        '"bank',
        '"family',
        '"source_pdf',
        '"physical_page',
        '"raw_text',
        '"transcript',
        '"adapter',
    ):
        assert forbidden not in serialized

    replayed, replay_capability = freezer.replay_authenticated_vietocr_all_line_freeze_v3(
        tmp_path, freezer.ARTIFACT_ROOT, live_ready
    )
    assert replayed == projection
    assert freezer.project_authenticated_vietocr_all_line_freeze_v3(capability) == projection
    assert freezer.project_authenticated_vietocr_all_line_freeze_v3(replay_capability) == projection
    for ordinal in (1, 418, 835):
        payload = freezer.read_authenticated_vietocr_all_line_crop_v3(capability, ordinal)
        assert type(payload) is bytes
        assert (
            hashlib.sha256(payload).hexdigest() == manifest["samples"][ordinal - 1]["crop_sha256"]
        )
    batch_snapshots = freezer.read_authenticated_vietocr_all_line_batch_v3(capability)
    assert len(batch_snapshots) == 835
    assert batch_snapshots[0]["sample_id"] == "page-0001-line-0000"
    assert batch_snapshots[-1]["sample_id"] == "page-0008-line-0163"
    assert type(batch_snapshots[417]["crop_png_bytes"]) is bytes


def test_requires_live_ready_and_freeze_capabilities(
    tmp_path: Path, live_ready, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(freezer, "_clean_git_binding", lambda _root: _git_binding())
    monkeypatch.setattr(freezer, "_git_commit_is_ancestor", lambda *_args: True)
    root = _prepare_root(tmp_path)
    forged_ready = object.__new__(ready.AuthenticatedLoanMaturity8BankReadyPanelV1)
    with pytest.raises(Exception, match="unknown|expired"):
        freezer.freeze_authenticated_vietocr_all_line_batch_v3(
            root, freezer.ARTIFACT_ROOT, forged_ready
        )
    with pytest.raises(freezer.VietOCRAllLineFreezerV3Error, match="exact live"):
        freezer.freeze_authenticated_vietocr_all_line_batch_v3(
            root, freezer.ARTIFACT_ROOT, cast(Any, {"sample_count": 835})
        )
    forged_freeze = object.__new__(freezer.AuthenticatedVietOCRAllLineFreezeV3)
    with pytest.raises(freezer.VietOCRAllLineFreezerV3Error, match="unknown or expired"):
        freezer.read_authenticated_vietocr_all_line_crop_v3(forged_freeze, 1)
    with pytest.raises(freezer.VietOCRAllLineFreezerV3Error, match="caller-constructed"):
        freezer.AuthenticatedVietOCRAllLineFreezeV3(object())


def test_capability_is_uncopyable_and_keeps_strong_ready_reference(
    tmp_path: Path, live_ready, monkeypatch: pytest.MonkeyPatch
) -> None:
    _projection, capability = _freeze(tmp_path, live_ready, monkeypatch)
    reference = weakref.ref(live_ready)
    del live_ready
    gc.collect()
    assert reference() is not None
    for operation in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(freezer.VietOCRAllLineFreezerV3Error):
            operation(capability)


@pytest.mark.parametrize("ordinal", [1, 418, 835])
def test_coherent_crop_tamper_still_fails_live_recomputation(
    tmp_path: Path, live_ready, monkeypatch: pytest.MonkeyPatch, ordinal: int
) -> None:
    _projection, _capability = _freeze(tmp_path, live_ready, monkeypatch)
    manifest_path = tmp_path / freezer.ARTIFACT_ROOT / "frozen/crop_manifest.json"
    request_path = tmp_path / freezer.ARTIFACT_ROOT / "frozen/reader_request.json"
    manifest = json.loads(manifest_path.read_text())
    request = json.loads(request_path.read_text())
    sample = manifest["samples"][ordinal - 1]
    crop_path = tmp_path / sample["crop_path"]
    altered = _png(sample["crop_width"], sample["crop_height"], (240, 1, 2))
    crop_path.chmod(0o644)
    crop_path.write_bytes(altered)
    sample["crop_sha256"] = hashlib.sha256(altered).hexdigest()
    sample["crop_size_bytes"] = len(altered)
    request["samples"][ordinal - 1]["crop_sha256"] = sample["crop_sha256"]
    manifest_path.chmod(0o644)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    request["crop_manifest"]["sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    request["crop_manifest"]["size_bytes"] = manifest_path.stat().st_size
    request_path.chmod(0o644)
    request_path.write_text(json.dumps(request, indent=2, sort_keys=True) + "\n")

    with pytest.raises(freezer.VietOCRAllLineFreezerV3Error, match="recomputation"):
        freezer.replay_authenticated_vietocr_all_line_freeze_v3(
            tmp_path, freezer.ARTIFACT_ROOT, live_ready
        )


def test_snapshot_accessor_survives_disk_deletion_but_explicit_replay_fails(
    tmp_path: Path, live_ready, monkeypatch: pytest.MonkeyPatch
) -> None:
    _projection, capability = _freeze(tmp_path, live_ready, monkeypatch)
    before = freezer.read_authenticated_vietocr_all_line_crop_v3(capability, 418)
    manifest = json.loads(
        (tmp_path / freezer.ARTIFACT_ROOT / "frozen/crop_manifest.json").read_text()
    )
    crop = tmp_path / manifest["samples"][417]["crop_path"]
    crop.unlink()
    # The immutable accessor validates the live READY snapshot, not mutable disk.
    assert freezer.read_authenticated_vietocr_all_line_crop_v3(capability, 418) == before
    with pytest.raises(freezer.VietOCRAllLineFreezerV3Error):
        freezer.replay_authenticated_vietocr_all_line_freeze_v3(
            tmp_path, freezer.ARTIFACT_ROOT, live_ready
        )


def test_staging_failure_leaves_no_final_or_stage(
    tmp_path: Path, live_ready, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _prepare_root(tmp_path)
    monkeypatch.setattr(freezer, "_clean_git_binding", lambda _root: _git_binding())
    monkeypatch.setattr(freezer, "_git_commit_is_ancestor", lambda *_args: True)
    original = freezer._exclusive_write_fd
    calls = 0

    def fail_middle(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 418:
            raise freezer.VietOCRAllLineFreezerV3Error("injected staging failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(freezer, "_exclusive_write_fd", fail_middle)
    before_fds = len(os.listdir("/proc/self/fd"))
    with pytest.raises(freezer.VietOCRAllLineFreezerV3Error, match="injected"):
        freezer.freeze_authenticated_vietocr_all_line_batch_v3(
            root, freezer.ARTIFACT_ROOT, live_ready
        )
    assert not (root / freezer.ARTIFACT_ROOT).exists()
    assert not list((root / "output/development").glob(".vietocr-freeze-v3-stage-*"))
    assert len(os.listdir("/proc/self/fd")) == before_fds


def test_staging_container_open_failure_removes_new_empty_stage(
    tmp_path: Path, live_ready, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _prepare_root(tmp_path)
    monkeypatch.setattr(freezer, "_clean_git_binding", lambda _root: _git_binding())
    monkeypatch.setattr(freezer, "_git_commit_is_ancestor", lambda *_args: True)
    original = freezer.os.open

    def fail_new_stage(name, flags, *args, **kwargs):
        if isinstance(name, str) and name.startswith(".vietocr-freeze-v3-stage-"):
            raise OSError(24, "injected EMFILE")
        return original(name, flags, *args, **kwargs)

    monkeypatch.setattr(freezer.os, "open", fail_new_stage)
    with pytest.raises(OSError, match="injected EMFILE"):
        freezer.freeze_authenticated_vietocr_all_line_batch_v3(
            root, freezer.ARTIFACT_ROOT, live_ready
        )
    assert not (root / freezer.ARTIFACT_ROOT).exists()
    assert not list((root / "output/development").glob(".vietocr-freeze-v3-stage-*"))


def test_existing_destination_and_posixpath_bool_ordinals_are_rejected_safely(
    tmp_path: Path, live_ready, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _prepare_root(tmp_path)
    destination = root / freezer.ARTIFACT_ROOT
    destination.mkdir()
    sentinel = destination / "sentinel"
    sentinel.write_bytes(b"keep")
    monkeypatch.setattr(freezer, "_clean_git_binding", lambda _root: _git_binding())
    with pytest.raises(freezer.VietOCRAllLineFreezerV3Error, match="replace"):
        freezer.freeze_authenticated_vietocr_all_line_batch_v3(
            root, freezer.ARTIFACT_ROOT, live_ready
        )
    assert sentinel.read_bytes() == b"keep"
    assert freezer._safe_relative(Path("generated/freeze"), "output") == Path("generated/freeze")
    with pytest.raises(freezer.VietOCRAllLineFreezerV3Error):
        freezer._safe_relative(Path("../escape"), "output")
    with pytest.raises(freezer.VietOCRAllLineFreezerV3Error, match="fixed"):
        freezer.freeze_authenticated_vietocr_all_line_batch_v3(
            root, Path("output/development/ACB/loan_maturity"), live_ready
        )


def test_git_drift_after_publication_removes_only_owned_output(
    tmp_path: Path, live_ready, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _prepare_root(tmp_path)
    calls = 0

    def binding(_root):
        nonlocal calls
        calls += 1
        value = _git_binding()
        if calls >= 3:
            value["source_tree_oid"] = "3" * 40
        return value

    monkeypatch.setattr(freezer, "_clean_git_binding", binding)
    monkeypatch.setattr(freezer, "_git_commit_is_ancestor", lambda *_args: True)
    with pytest.raises(freezer.VietOCRAllLineFreezerV3Error, match="Git"):
        freezer.freeze_authenticated_vietocr_all_line_batch_v3(
            root, freezer.ARTIFACT_ROOT, live_ready
        )
    assert not (root / freezer.ARTIFACT_ROOT).exists()
    assert not freezer._AUTHENTICATED_FREEZES


def test_clean_descendant_replay_requires_ancestry_and_unchanged_source_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    frozen = _git_binding()
    descendant = copy.deepcopy(frozen)
    descendant["commit"] = "5" * 40
    monkeypatch.setattr(freezer, "_clean_git_binding", lambda _root: descendant)
    monkeypatch.setattr(freezer, "_git_commit_is_ancestor", lambda *_args: True)
    freezer._assert_git_binding(tmp_path, frozen, "at clean descendant")

    monkeypatch.setattr(freezer, "_git_commit_is_ancestor", lambda *_args: False)
    with pytest.raises(freezer.VietOCRAllLineFreezerV3Error, match="ancestor"):
        freezer._assert_git_binding(tmp_path, frozen, "at unrelated commit")

    descendant["source_tree_oid"] = "6" * 40
    monkeypatch.setattr(freezer, "_git_commit_is_ancestor", lambda *_args: True)
    with pytest.raises(freezer.VietOCRAllLineFreezerV3Error, match="implementation"):
        freezer._assert_git_binding(tmp_path, frozen, "after source drift")


def test_batch_accessor_rejects_git_source_tree_drift(
    tmp_path: Path, live_ready, monkeypatch: pytest.MonkeyPatch
) -> None:
    _projection, capability = _freeze(tmp_path, live_ready, monkeypatch)
    drifted = _git_binding()
    drifted["source_tree_oid"] = "7" * 40
    monkeypatch.setattr(freezer, "_clean_git_binding", lambda _root: drifted)
    with pytest.raises(freezer.VietOCRAllLineFreezerV3Error, match="implementation"):
        freezer.read_authenticated_vietocr_all_line_batch_v3(capability)


def test_publication_uses_validated_parent_dirfd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = tmp_path / "parent"
    parent.mkdir()
    stage = parent / ".stage"
    stage.mkdir()
    descriptor = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
    captured: list[tuple[int, bytes, int, bytes, int]] = []

    class _Rename:
        argtypes = None
        restype = None

        def __call__(self, source_fd, source, target_fd, target, flags):
            captured.append((source_fd, source, target_fd, target, flags))
            os.rename(source.decode(), target.decode(), src_dir_fd=source_fd, dst_dir_fd=target_fd)
            return 0

    class _LibC:
        renameat2 = _Rename()

    monkeypatch.setattr(freezer.ctypes, "CDLL", lambda *_args, **_kwargs: _LibC())
    try:
        freezer._rename_noreplace(descriptor, stage.name, descriptor, "final")
    finally:
        os.close(descriptor)
    assert captured == [(captured[0][0], b".stage", captured[0][0], b"final", 1)]
    assert (parent / "final").is_dir()


def test_publish_source_is_private_container_fd_not_shared_parent(
    tmp_path: Path, live_ready, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _prepare_root(tmp_path)
    monkeypatch.setattr(freezer, "_clean_git_binding", lambda _root: _git_binding())
    monkeypatch.setattr(freezer, "_git_commit_is_ancestor", lambda *_args: True)
    original = freezer._rename_noreplace
    observed: list[tuple[int, int, str]] = []

    def capture(source_fd, source_name, target_fd, target_name):
        if target_name == freezer.ARTIFACT_ROOT.name:
            observed.append((source_fd, target_fd, source_name))
            assert source_fd != target_fd
            assert source_name == "tree"
        return original(source_fd, source_name, target_fd, target_name)

    monkeypatch.setattr(freezer, "_rename_noreplace", capture)
    freezer.freeze_authenticated_vietocr_all_line_batch_v3(root, freezer.ARTIFACT_ROOT, live_ready)
    assert len(observed) == 1
