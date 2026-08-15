#!/usr/bin/env python3
"""Build and authenticate a geometry-selected rotated-line VietOCR rescue.

The full-document semantic cache contains a small set of landscape tables whose
LINE boxes are vertical in displayed-page pixel coordinates.  Their original
line crops are therefore presented sideways to VietOCR.  This experiment
selects *all* such pages by one closed geometry rule, rotates every source crop
clockwise by 90 degrees, and submits the opaque crops to the same pinned
VietOCR Transformer reader.

Bank identity, filename, page number, source text and family/schema labels are
not reader inputs and are not selection rules.  The private manifest preserves
the exact source locator and line order for later structural matching.  The
rescue grants semantic-anchor proposals only; it grants no numeric, geometry,
schema, mapping, canonicalization or export authority.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import io
import json
import math
import os
import re
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_INDEX_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/verified-index/semantic_index.json"
)
OUTPUT_ROOT = Path("output/development/full-document-rotated-vietocr-rescue-v1")
MANIFEST_PATH = OUTPUT_ROOT / "crop_manifest.json"
REQUEST_PATH = OUTPUT_ROOT / "reader_request.json"
READER_OUTPUT = OUTPUT_ROOT / "reader-output"
CONFIG_PATH = Path("config/models/vietocr-0.3.13-rtx4090.toml")
BUILDER_PATH = Path("scripts/experiments/build_full_document_rotated_vietocr_rescue_v1.py")

FORMAT_VERSION = "FULL_DOCUMENT_ROTATED_VIETOCR_RESCUE_CROP_MANIFEST_V1"
PROJECTION_FORMAT_VERSION = "FULL_DOCUMENT_ROTATED_VIETOCR_RESCUE_PROJECTION_V1"
EXPERIMENT_ID = "VIETOCR_MULTI_BANK_FAMILY_OCR_BENCHMARK_V1"
SOURCE_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
SOURCE_INDEX_SIZE = 19_265_584
SOURCE_SEMANTIC_AXIS_SHA256 = "e99873cd16a7234702d0ee6e5fa9eb37637a1a75621228381e3dbcd7c5cfdcca"
CONFIG_SHA256 = "aa007448e2ed4f940693c3b4c03ae47111cf1ed00580d13c05a41941e5094119"
WEIGHTS_SHA256 = "380512193a8b6cbf6fad80deacdc9b6939d10d473d199892fc6408d13775ea59"
MINIMUM_LINE_COUNT = 20
MINIMUM_VERTICAL_PERCENT = 85
EXPECTED_PAGE_COUNT = 15
EXPECTED_LINE_COUNT = 1_863
ROTATION = "CLOCKWISE_90_DEGREES"
_SAMPLE_RE = re.compile(r"^rotated-sample-[0-9]{8}$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_REF_FIELDS = {"path", "sha256", "size_bytes"}
_MANIFEST_FIELDS = {
    "authority",
    "format_version",
    "git_binding",
    "metrics",
    "pages",
    "samples",
    "selection_rule",
    "source_semantic_index",
    "state",
}
_PAGE_FIELDS = {
    "document_ordinal",
    "line_count",
    "physical_page",
    "sample_offset_start",
    "sample_offset_stop",
    "source_pdf",
    "source_projection",
    "vertical_line_count",
}
_SAMPLE_FIELDS = {
    "document_ordinal",
    "physical_page",
    "rotated_crop_ref",
    "rotation",
    "sample_id",
    "source_bbox_raw_pixels",
    "source_crop_ref",
    "source_line_index",
}
_REQUEST_FIELDS = {
    "crop_manifest",
    "dataset_role",
    "evidence_role",
    "experiment_id",
    "format_version",
    "git_commit",
    "git_dirty",
    "reference_text_available_to_reader",
    "sample_count",
    "samples",
    "state",
}
_REQUEST_SAMPLE_FIELDS = {"category", "crop_path", "crop_sha256", "sample_id"}
_RESULT_FIELDS = {
    "dataset_role",
    "evidence_role",
    "experiment_id",
    "format_version",
    "reference_text_available_to_reader",
    "sample_count",
    "samples",
    "state",
}
_RESULT_SAMPLE_FIELDS = {
    "category",
    "crop_path",
    "crop_sha256",
    "mean_decoded_character_probability",
    "processed_height",
    "processed_width",
    "raw_prediction",
    "sample_id",
    "wall_seconds",
}
_AUTHORITY = {
    "bank_filename_page_note_or_text_used_for_selection": False,
    "complete_geometry_selected_page_denominator": True,
    "mapping_numeric_schema_canonical_or_export_authority": False,
    "reader_received_source_text_or_provenance": False,
    "rotation_only_same_pinned_vietocr_transformer": True,
    "semantic_anchor_proposal_only": True,
}
_SELECTION_RULE = {
    "bbox_vertical_test": "2_HEIGHT_GREATER_THAN_3_WIDTH",
    "minimum_line_count": MINIMUM_LINE_COUNT,
    "minimum_vertical_line_percent": MINIMUM_VERTICAL_PERCENT,
    "selection_inputs": ["LINE_COUNT", "SOURCE_BBOX_RAW_PIXELS"],
}


class FullDocumentRotatedVietOCRRescueV1Error(RuntimeError):
    """The geometry selection, rotated crops, or VietOCR result drifted."""


def _error(message: str) -> FullDocumentRotatedVietOCRRescueV1Error:
    return FullDocumentRotatedVietOCRRescueV1Error(message)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _relative_parts(path: Path) -> tuple[str, ...]:
    if not isinstance(path, Path) or path.is_absolute() or not path.parts:
        raise _error(f"artifact path is not one safe project-relative path: {path}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise _error(f"artifact path escapes the project root: {path}")
    return tuple(path.parts)


def _stable_bytes(path: Path) -> bytes:
    parts = _relative_parts(path)
    directory_fd = os.open(PROJECT_ROOT, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in parts[:-1]:
            child_fd = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=directory_fd,
            )
            os.close(directory_fd)
            directory_fd = child_fd
        descriptor = os.open(
            parts[-1],
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=directory_fd,
        )
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                raise _error(f"artifact is not one regular file: {path}")
            chunks: list[bytes] = []
            while chunk := os.read(descriptor, 1024 * 1024):
                chunks.append(chunk)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
    finally:
        os.close(directory_fd)
    identity_before = (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_size,
        before.st_mtime_ns,
    )
    identity_after = (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_size,
        after.st_mtime_ns,
    )
    payload = b"".join(chunks)
    if identity_before != identity_after or len(payload) != before.st_size:
        raise _error(f"artifact changed while being read: {path}")
    return payload


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate key {key}")
            result[key] = value
        return result

    try:
        value = json.loads(
            payload,
            object_pairs_hook=pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise _error(f"{label} is not strict JSON") from exc
    if type(value) is not dict:
        raise _error(f"{label} root must be one object")
    return value


def _fixed_json(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = _stable_bytes(path)
    return _strict_json(payload, path.as_posix()), {
        "path": path.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _ref(value: Any, label: str) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _REF_FIELDS
        or type(value["path"]) is not str
        or not value["path"]
        or Path(value["path"]).is_absolute()
        or any(part in {"", ".", ".."} for part in Path(value["path"]).parts)
        or type(value["sha256"]) is not str
        or _SHA_RE.fullmatch(value["sha256"]) is None
        or type(value["size_bytes"]) is not int
        or value["size_bytes"] <= 0
    ):
        raise _error(f"{label} content reference drifted")
    return canonical_clone_v1(value)


def _read_ref(value: Any, label: str) -> bytes:
    reference = _ref(value, label)
    payload = _stable_bytes(Path(reference["path"]))
    if (
        len(payload) != reference["size_bytes"]
        or hashlib.sha256(payload).hexdigest() != reference["sha256"]
    ):
        raise _error(f"{label} bytes drifted")
    return payload


def _bbox(value: Any) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or value[0] < 0
        or value[1] < 0
        or value[2] <= value[0]
        or value[3] <= value[1]
    ):
        raise _error("source bbox drifted")
    return list(value)


def _is_vertical_bbox(value: Any) -> bool:
    left, top, right, bottom = _bbox(value)
    return 2 * (bottom - top) > 3 * (right - left)


def _selected_pages(index: Any) -> list[dict[str, Any]]:
    if type(index) is not dict or type(index.get("documents")) is not list:
        raise _error("source semantic index document axis drifted")
    selected: list[dict[str, Any]] = []
    previous_document = 0
    for document in index["documents"]:
        if type(document) is not dict:
            raise _error("source semantic index document drifted")
        ordinal = document.get("document_ordinal")
        pages = document.get("pages")
        source_pdf = document.get("source_pdf")
        if (
            type(ordinal) is not int
            or ordinal != previous_document + 1
            or type(pages) is not list
            or type(source_pdf) is not dict
        ):
            raise _error("source semantic index document order drifted")
        source_pdf = _ref(source_pdf, "source PDF")
        previous_page = 0
        for page in pages:
            if type(page) is not dict or type(page.get("lines")) is not list:
                raise _error("source semantic index page drifted")
            physical_page = page.get("physical_page")
            lines = page["lines"]
            if type(physical_page) is not int or physical_page != previous_page + 1:
                raise _error("source semantic index page order drifted")
            previous_page = physical_page
            vertical_count = sum(
                _is_vertical_bbox(line.get("source_bbox_raw_pixels"))
                for line in lines
                if type(line) is dict
            )
            if len(lines) >= MINIMUM_LINE_COUNT and (
                100 * vertical_count >= MINIMUM_VERTICAL_PERCENT * len(lines)
            ):
                selected.append(
                    {
                        "document_ordinal": ordinal,
                        "lines": lines,
                        "physical_page": physical_page,
                        "source_pdf": source_pdf,
                        "source_projection": canonical_clone_v1(page.get("source_projection")),
                        "vertical_line_count": vertical_count,
                    }
                )
        previous_document = ordinal
    return selected


def _rotated_png(source: bytes) -> bytes:
    try:
        with Image.open(io.BytesIO(source)) as image:
            if image.format != "PNG":
                raise _error("source crop is not PNG")
            image.load()
            rotated = image.transpose(Image.Transpose.ROTATE_270)
            output = io.BytesIO()
            rotated.save(output, format="PNG")
    except (OSError, ValueError) as exc:
        raise _error("source crop cannot be deterministically rotated") from exc
    return output.getvalue()


def _content_ref(path: Path, payload: bytes) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _write_exclusive(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _publish_noreplace(stage: Path, destination: Path) -> None:
    if stage.parent != destination.parent or stage.name == destination.name:
        raise _error("publication requires distinct sibling directories")
    parent_fd = os.open(stage.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = getattr(libc, "renameat2", None)
        if renameat2 is None:
            raise _error("atomic no-replace publication is unavailable")
        renameat2.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        renameat2.restype = ctypes.c_int
        if (
            renameat2(
                parent_fd,
                os.fsencode(stage.name),
                parent_fd,
                os.fsencode(destination.name),
                1,
            )
            != 0
        ):
            code = ctypes.get_errno()
            if code in {errno.EEXIST, errno.ENOTEMPTY}:
                raise _error(f"refusing to overwrite existing rescue: {destination}")
            raise _error(f"atomic rescue publication failed with errno {code}")
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


def _clean_git_binding() -> dict[str, Any]:
    if _git("status", "--porcelain", "--untracked-files=all"):
        raise _error("rotated VietOCR rescue build requires a clean Git worktree")
    commit = _git("rev-parse", "HEAD")
    builder = _stable_bytes(BUILDER_PATH)
    tracked = subprocess.run(
        ["git", "show", f"{commit}:{BUILDER_PATH.as_posix()}"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
    ).stdout
    if builder != tracked:
        raise _error("rotated rescue builder is not the exact committed implementation")
    return {
        "commit": commit,
        "dirty": False,
        "implementation_ref": _content_ref(BUILDER_PATH, builder),
    }


def _source_index() -> tuple[dict[str, Any], dict[str, Any]]:
    index, reference = _fixed_json(SOURCE_INDEX_PATH)
    if (reference["sha256"], reference["size_bytes"]) != (
        SOURCE_INDEX_SHA256,
        SOURCE_INDEX_SIZE,
    ):
        raise _error("fixed full-document semantic index identity drifted")
    if index.get("metrics", {}).get("semantic_axis_sha256") != SOURCE_SEMANTIC_AXIS_SHA256:
        raise _error("fixed full-document semantic axis identity drifted")
    return index, reference


def build_full_document_rotated_vietocr_rescue_v1() -> dict[str, Any]:
    """Freeze every geometry-selected rotated line for the pinned reader."""

    destination = PROJECT_ROOT / OUTPUT_ROOT
    if destination.exists():
        raise _error(f"refusing to overwrite existing rescue: {destination}")
    git_binding = _clean_git_binding()
    index, index_ref = _source_index()
    selected = _selected_pages(index)
    if len(selected) != EXPECTED_PAGE_COUNT or sum(len(page["lines"]) for page in selected) != (
        EXPECTED_LINE_COUNT
    ):
        raise _error("geometry-selected rotated page/line denominator drifted")

    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    try:
        (stage / "crops").mkdir(mode=0o700)
        manifest_samples: list[dict[str, Any]] = []
        request_samples: list[dict[str, Any]] = []
        manifest_pages: list[dict[str, Any]] = []
        cursor = 0
        for page in selected:
            start = cursor
            for expected_line_index, line in enumerate(page["lines"]):
                if type(line) is not dict or line.get("source_line_index") != expected_line_index:
                    raise _error("selected source line order drifted")
                source_ref = _ref(line.get("crop_ref"), "source line crop")
                source = _read_ref(source_ref, "source line crop")
                rotated = _rotated_png(source)
                cursor += 1
                sample_id = f"rotated-sample-{cursor:08d}"
                relative_crop = OUTPUT_ROOT / "crops" / f"{sample_id}.png"
                stage_crop = stage / "crops" / f"{sample_id}.png"
                _write_exclusive(stage_crop, rotated)
                rotated_ref = _content_ref(relative_crop, rotated)
                manifest_samples.append(
                    {
                        "document_ordinal": page["document_ordinal"],
                        "physical_page": page["physical_page"],
                        "rotated_crop_ref": rotated_ref,
                        "rotation": ROTATION,
                        "sample_id": sample_id,
                        "source_bbox_raw_pixels": _bbox(line.get("source_bbox_raw_pixels")),
                        "source_crop_ref": source_ref,
                        "source_line_index": expected_line_index,
                    }
                )
                request_samples.append(
                    {
                        "category": "ROTATED_FULL_DOCUMENT_LINE",
                        "crop_path": relative_crop.as_posix(),
                        "crop_sha256": rotated_ref["sha256"],
                        "sample_id": sample_id,
                    }
                )
            manifest_pages.append(
                {
                    "document_ordinal": page["document_ordinal"],
                    "line_count": len(page["lines"]),
                    "physical_page": page["physical_page"],
                    "sample_offset_start": start,
                    "sample_offset_stop": cursor,
                    "source_pdf": page["source_pdf"],
                    "source_projection": page["source_projection"],
                    "vertical_line_count": page["vertical_line_count"],
                }
            )
        manifest = {
            "authority": canonical_clone_v1(_AUTHORITY),
            "format_version": FORMAT_VERSION,
            "git_binding": git_binding,
            "metrics": {
                "document_count": len({page["document_ordinal"] for page in selected}),
                "line_count": cursor,
                "page_count": len(selected),
            },
            "pages": manifest_pages,
            "samples": manifest_samples,
            "selection_rule": canonical_clone_v1(_SELECTION_RULE),
            "source_semantic_index": index_ref,
            "state": "ROTATED_LINE_CROPS_FROZEN_FOR_REFERENCE_BLIND_VIETOCR",
        }
        manifest_raw = canonical_json_bytes_v1(manifest) + b"\n"
        request = {
            "crop_manifest": {
                "path": MANIFEST_PATH.as_posix(),
                "sha256": hashlib.sha256(manifest_raw).hexdigest(),
            },
            "dataset_role": "LOGIC_DEVELOPMENT_AND_CALIBRATION",
            "evidence_role": "INDEPENDENT_VIETNAMESE_SEMANTIC_PROPOSAL_ONLY",
            "experiment_id": EXPERIMENT_ID,
            "format_version": 2,
            "git_commit": git_binding["commit"],
            "git_dirty": False,
            "reference_text_available_to_reader": False,
            "sample_count": cursor,
            "samples": request_samples,
            "state": "READY_FOR_REFERENCE_BLIND_LINE_INFERENCE",
        }
        request_raw = canonical_json_bytes_v1(request) + b"\n"
        _write_exclusive(stage / "crop_manifest.json", manifest_raw)
        _write_exclusive(stage / "reader_request.json", request_raw)
        _publish_noreplace(stage, destination)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return verify_full_document_rotated_vietocr_rescue_v1(require_completed=False)


def _validate_freeze() -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    index, index_ref = _source_index()
    manifest, manifest_ref = _fixed_json(MANIFEST_PATH)
    request, request_ref = _fixed_json(REQUEST_PATH)
    if (
        type(manifest) is not dict
        or set(manifest) != _MANIFEST_FIELDS
        or manifest["format_version"] != FORMAT_VERSION
        or manifest["state"] != "ROTATED_LINE_CROPS_FROZEN_FOR_REFERENCE_BLIND_VIETOCR"
        or not same_typed_json_v1(manifest["authority"], _AUTHORITY)
        or not same_typed_json_v1(manifest["selection_rule"], _SELECTION_RULE)
        or not same_typed_json_v1(manifest["source_semantic_index"], index_ref)
        or type(manifest["pages"]) is not list
        or type(manifest["samples"]) is not list
    ):
        raise _error("rotated crop manifest identity drifted")
    selected = _selected_pages(index)
    expected_metrics = {
        "document_count": len({page["document_ordinal"] for page in selected}),
        "line_count": sum(len(page["lines"]) for page in selected),
        "page_count": len(selected),
    }
    if (
        len(selected) != EXPECTED_PAGE_COUNT
        or expected_metrics["line_count"] != EXPECTED_LINE_COUNT
        or not same_typed_json_v1(manifest["metrics"], expected_metrics)
        or len(manifest["pages"]) != len(selected)
        or len(manifest["samples"]) != EXPECTED_LINE_COUNT
    ):
        raise _error("rotated crop manifest denominator drifted")
    git_binding = manifest["git_binding"]
    if (
        type(git_binding) is not dict
        or set(git_binding) != {"commit", "dirty", "implementation_ref"}
        or type(git_binding["commit"]) is not str
        or git_binding["dirty"] is not False
    ):
        raise _error("rotated crop manifest Git binding drifted")
    builder = _read_ref(git_binding["implementation_ref"], "rescue builder")
    try:
        tracked = subprocess.run(
            ["git", "show", f"{git_binding['commit']}:{BUILDER_PATH.as_posix()}"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
        ).stdout
    except subprocess.CalledProcessError as exc:
        raise _error("rotated crop manifest run commit is unavailable") from exc
    if builder != tracked:
        raise _error("rotated crop manifest implementation binding drifted")

    cursor = 0
    for raw_page, selected_page in zip(manifest["pages"], selected, strict=True):
        if type(raw_page) is not dict or set(raw_page) != _PAGE_FIELDS:
            raise _error("rotated crop manifest page fields drifted")
        expected_page = {
            "document_ordinal": selected_page["document_ordinal"],
            "line_count": len(selected_page["lines"]),
            "physical_page": selected_page["physical_page"],
            "sample_offset_start": cursor,
            "sample_offset_stop": cursor + len(selected_page["lines"]),
            "source_pdf": selected_page["source_pdf"],
            "source_projection": selected_page["source_projection"],
            "vertical_line_count": selected_page["vertical_line_count"],
        }
        if not same_typed_json_v1(raw_page, expected_page):
            raise _error("rotated crop manifest page selection drifted")
        for line_index, source_line in enumerate(selected_page["lines"]):
            raw_sample = manifest["samples"][cursor]
            cursor += 1
            if type(raw_sample) is not dict or set(raw_sample) != _SAMPLE_FIELDS:
                raise _error("rotated crop manifest sample fields drifted")
            sample_id = f"rotated-sample-{cursor:08d}"
            if (
                raw_sample["sample_id"] != sample_id
                or _SAMPLE_RE.fullmatch(sample_id) is None
                or raw_sample["document_ordinal"] != selected_page["document_ordinal"]
                or raw_sample["physical_page"] != selected_page["physical_page"]
                or raw_sample["source_line_index"] != line_index
                or raw_sample["rotation"] != ROTATION
                or not same_typed_json_v1(
                    raw_sample["source_bbox_raw_pixels"],
                    source_line["source_bbox_raw_pixels"],
                )
                or not same_typed_json_v1(raw_sample["source_crop_ref"], source_line["crop_ref"])
            ):
                raise _error("rotated crop manifest source-line binding drifted")
            source = _read_ref(raw_sample["source_crop_ref"], "source line crop")
            expected_rotated = _rotated_png(source)
            actual_rotated = _read_ref(raw_sample["rotated_crop_ref"], "rotated line crop")
            if actual_rotated != expected_rotated:
                raise _error("rotated line crop is not the exact clockwise source transform")
    if cursor != EXPECTED_LINE_COUNT:
        raise _error("rotated crop manifest sample traversal drifted")

    if (
        type(request) is not dict
        or set(request) != _REQUEST_FIELDS
        or request["format_version"] != 2
        or request["experiment_id"] != EXPERIMENT_ID
        or request["state"] != "READY_FOR_REFERENCE_BLIND_LINE_INFERENCE"
        or request["dataset_role"] != "LOGIC_DEVELOPMENT_AND_CALIBRATION"
        or request["evidence_role"] != "INDEPENDENT_VIETNAMESE_SEMANTIC_PROPOSAL_ONLY"
        or request["git_commit"] != git_binding["commit"]
        or request["git_dirty"] is not False
        or request["reference_text_available_to_reader"] is not False
        or request["sample_count"] != EXPECTED_LINE_COUNT
        or request["crop_manifest"]
        != {"path": MANIFEST_PATH.as_posix(), "sha256": manifest_ref["sha256"]}
        or type(request["samples"]) is not list
        or len(request["samples"]) != EXPECTED_LINE_COUNT
    ):
        raise _error("rotated reader request identity drifted")
    for raw_request, raw_manifest in zip(request["samples"], manifest["samples"], strict=True):
        expected = {
            "category": "ROTATED_FULL_DOCUMENT_LINE",
            "crop_path": raw_manifest["rotated_crop_ref"]["path"],
            "crop_sha256": raw_manifest["rotated_crop_ref"]["sha256"],
            "sample_id": raw_manifest["sample_id"],
        }
        if (
            type(raw_request) is not dict
            or set(raw_request) != _REQUEST_SAMPLE_FIELDS
            or not same_typed_json_v1(raw_request, expected)
        ):
            raise _error("rotated reader request sample drifted")
    return index, manifest, request, {"manifest": manifest_ref, "request": request_ref}


def _completed_projection(
    manifest: dict[str, Any],
    request: dict[str, Any],
    refs: dict[str, Any],
) -> dict[str, Any]:
    result, result_ref = _fixed_json(READER_OUTPUT / "ocr_result.json")
    run, run_ref = _fixed_json(READER_OUTPUT / "run_manifest.json")
    if (
        type(result) is not dict
        or set(result) != _RESULT_FIELDS
        or result["format_version"] != 2
        or result["experiment_id"] != EXPERIMENT_ID
        or result["state"] != "REFERENCE_BLIND_LINE_INFERENCE_COMPLETE"
        or result["dataset_role"] != request["dataset_role"]
        or result["evidence_role"] != request["evidence_role"]
        or result["reference_text_available_to_reader"] is not False
        or result["sample_count"] != EXPECTED_LINE_COUNT
        or type(result["samples"]) is not list
        or len(result["samples"]) != EXPECTED_LINE_COUNT
    ):
        raise _error("rotated VietOCR result identity drifted")
    if (
        type(run) is not dict
        or run.get("format_version") != 2
        or run.get("experiment_id") != EXPERIMENT_ID
        or run.get("state") != "REFERENCE_BLIND_LINE_INFERENCE_COMPLETE"
        or run.get("git_commit") != request["git_commit"]
        or run.get("git_dirty") is not False
        or run.get("request")
        != {"path": REQUEST_PATH.as_posix(), "sha256": refs["request"]["sha256"]}
        or run.get("configuration", {}).get("path") != CONFIG_PATH.as_posix()
        or run.get("configuration", {}).get("sha256") != CONFIG_SHA256
        or run.get("configuration", {}).get("network_policy")
        != "PROCESS_SOCKET_CONNECT_AND_DNS_DENIED"
        or run.get("runtime", {}).get("packages", {}).get("vietocr") != "0.3.13"
        or run.get("runtime", {}).get("compute_capability") != "8.9"
        or run.get("runtime", {}).get("artifacts", {}).get("weights", {}).get("sha256")
        != WEIGHTS_SHA256
        or run.get("metrics", {}).get("sample_count") != EXPECTED_LINE_COUNT
        or type(run.get("safety")) is not dict
        or not run["safety"]
        or any(bool(value) for value in run["safety"].values())
        or run.get("artifacts", {}).get("ocr_result")
        != {
            "path": "ocr_result.json",
            "sha256": result_ref["sha256"],
            "size_bytes": result_ref["size_bytes"],
        }
    ):
        raise _error("rotated VietOCR run/model binding drifted")
    projected_samples = []
    for raw_result, raw_request, raw_manifest in zip(
        result["samples"], request["samples"], manifest["samples"], strict=True
    ):
        probability = raw_result.get("mean_decoded_character_probability")
        wall_seconds = raw_result.get("wall_seconds")
        if (
            type(raw_result) is not dict
            or set(raw_result) != _RESULT_SAMPLE_FIELDS
            or raw_result["sample_id"] != raw_request["sample_id"]
            or raw_result["category"] != raw_request["category"]
            or raw_result["crop_path"] != raw_request["crop_path"]
            or raw_result["crop_sha256"] != raw_request["crop_sha256"]
            or type(raw_result["raw_prediction"]) is not str
            or type(raw_result["processed_width"]) is not int
            or raw_result["processed_width"] <= 0
            or type(raw_result["processed_height"]) is not int
            or raw_result["processed_height"] <= 0
            or not (
                probability is None
                or (
                    type(probability) is float
                    and math.isfinite(probability)
                    and 0.0 <= probability <= 1.0
                )
            )
            or type(wall_seconds) is not float
            or not math.isfinite(wall_seconds)
            or wall_seconds < 0.0
        ):
            raise _error("rotated VietOCR result sample drifted")
        projected_samples.append(
            {
                "document_ordinal": raw_manifest["document_ordinal"],
                "mean_decoded_character_probability": probability,
                "physical_page": raw_manifest["physical_page"],
                "semantic_text": raw_result["raw_prediction"],
                "source_crop_sha256": raw_manifest["source_crop_ref"]["sha256"],
                "source_line_index": raw_manifest["source_line_index"],
            }
        )
    material = {
        "authority": {
            "bank_filename_page_note_or_text_used_for_selection": False,
            "mapping_numeric_schema_canonical_or_export_authority": False,
            "reference_text_available_to_reader": False,
            "rotation_only_same_pinned_vietocr_transformer": True,
        },
        "format_version": PROJECTION_FORMAT_VERSION,
        "input_refs": {
            "crop_manifest": refs["manifest"],
            "ocr_result": result_ref,
            "reader_request": refs["request"],
            "run_manifest": run_ref,
        },
        "metrics": canonical_clone_v1(manifest["metrics"]),
        "pages": canonical_clone_v1(manifest["pages"]),
        "samples": projected_samples,
        "source_semantic_axis_sha256": SOURCE_SEMANTIC_AXIS_SHA256,
        "state": "VERIFIED_ROTATED_VIETOCR_SEMANTIC_RESCUE_COMPLETE",
    }
    return {
        **material,
        "projection_id": "fdrrv1:projection:" + canonical_json_sha256_v1(material),
    }


def verify_full_document_rotated_vietocr_rescue_v1(
    *, require_completed: bool = True
) -> dict[str, Any]:
    """Replay every selected crop and optionally authenticate the model output."""

    _index, manifest, request, refs = _validate_freeze()
    if require_completed:
        return _completed_projection(manifest, request, refs)
    return {
        "format_version": FORMAT_VERSION,
        "manifest_ref": refs["manifest"],
        "metrics": canonical_clone_v1(manifest["metrics"]),
        "request_ref": refs["request"],
        "state": "VERIFIED_ROTATED_VIETOCR_FREEZE_READY",
    }


def read_verified_full_document_rotated_vietocr_rescue_v1() -> dict[str, Any]:
    """Return the authenticated source-line→rotated semantic proposal axis."""

    return verify_full_document_rotated_vietocr_rescue_v1(require_completed=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--build", action="store_true")
    action.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.build:
        result = build_full_document_rotated_vietocr_rescue_v1()
    elif args.verify:
        result = verify_full_document_rotated_vietocr_rescue_v1(require_completed=True)
    else:
        result = verify_full_document_rotated_vietocr_rescue_v1(require_completed=False)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
