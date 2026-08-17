"""Build and verify the annual tangible-asset rotated PP-OCRv6 panel.

Pages are selected only from the complete-PDF tangible-asset graph and its
geometry-derived rotated presentation flag.  Bank names and physical page
numbers are retained as private provenance, never used as routing rules.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import importlib.util
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any

from PIL import Image, ImageChops

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = Path("output/calibration/annual-2025-tangible-fixed-assets-rotated-ppocrv6-panel-v1")
MANIFEST_PATH = OUTPUT_ROOT / "panel_manifest.json"
SEMANTIC_INDEX_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/verified-index/"
    "semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/crop_manifest.json"
)
ROTATED_RESCUE_MANIFEST_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-rotated-vietocr-rescue-v1/"
    "crop_manifest.json"
)
EXPECTED_SEMANTIC_INDEX_SHA256 = "98bb9854e699230da86538cf024ef3f4817b9e2f4dd2b2a75f46198f00e4247d"
EXPECTED_CROP_MANIFEST_SHA256 = "17d12a4d6b1dfaf0e243300757fd225b8c9cca80810a2d856efdb55a5b4ac000"
EXPECTED_ROTATED_RESCUE_MANIFEST_SHA256 = (
    "680c5981dcf0fba79b969fb33d14f15b418956d390cd541443475a4435289e45"
)
EXPECTED_SCAN_ID = "tfafdsv1:scan:3bbda7c0a4b2b6228cfeb9edbdd9209c2344fc88a8d90e8df3ce75873cb2ead2"
EXPECTED_PAGE_COUNT = 3
FORMAT_VERSION = "ANNUAL_2025_TANGIBLE_FIXED_ASSETS_ROTATED_PPOCRV6_PANEL_V1"
PROJECTION_FORMAT = "ANNUAL_2025_TANGIBLE_FIXED_ASSETS_ROTATED_PPOCRV6_VERIFIED_PROJECTION_V1"
SELECTION_RULE = "UNIQUE_COMPLETE_TANGIBLE_ASSET_REGION_AND_ROTATED_SOURCE_AXIS_TRUE"
PANEL_ID_PREFIX = "a2025tfarpv1:panel:"
PROJECTION_ID_PREFIX = "a2025tfarpv1:projection:"
INCLUDE_WORD_AXIS = False
_REF_FIELDS = {"path", "sha256", "size_bytes"}
_PAGE_FIELDS = {
    "document_ordinal",
    "line_count",
    "physical_page",
    "rotated_page_ref",
    "source_pdf_sha256",
    "source_render_ref",
    "source_semantic_line_axis_sha256",
}
_AUTHORITY = {
    "bank_filename_or_page_number_used_as_selection_rule": False,
    "fresh_vietocr_used_as_numeric_truth": False,
    "mapping_or_schema_authority": False,
    "ppocrv6_is_independent_numeric_challenger_only": True,
    "rotated_page_selected_from_generic_graph_and_geometry": True,
}


class Annual2025TangibleRotatedPPocrV6PanelError(ValueError):
    """The graph-selected rotated numeric panel or its OCR evidence drifted."""


def _error(message: str) -> Annual2025TangibleRotatedPPocrV6PanelError:
    return Annual2025TangibleRotatedPPocrV6PanelError(message)


def _load_module(name: str, relative_path: str) -> ModuleType:
    path = PROJECT_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load required module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _stable_bytes(relative_path: Path) -> bytes:
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise _error(f"artifact path is not project-relative: {relative_path}")
    path = PROJECT_ROOT / relative_path
    before = path.stat(follow_symlinks=False)
    if path.is_symlink() or not path.is_file() or before.st_nlink != 1:
        raise _error(f"artifact is not one private regular file: {relative_path}")
    payload = path.read_bytes()
    after = path.stat(follow_symlinks=False)
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise _error(f"artifact changed while read: {relative_path}")
    return payload


def _ref(path: Path, payload: bytes | None = None) -> dict[str, Any]:
    value = _stable_bytes(path) if payload is None else payload
    return {"path": path.as_posix(), "sha256": _sha256(value), "size_bytes": len(value)}


def _json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], bytes]:
    payload = _stable_bytes(path)
    if expected_sha256 is not None and _sha256(payload) != expected_sha256:
        raise _error(f"fixed JSON digest drifted: {path}")
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"cannot decode fixed JSON: {path}") from exc
    if type(value) is not dict:
        raise _error(f"fixed JSON root is not an object: {path}")
    return value, payload


def _one(items: Any, key: str, value: Any, label: str) -> dict[str, Any]:
    if type(items) is not list:
        raise _error(f"{label} axis drifted")
    matches = [item for item in items if type(item) is dict and item.get(key) == value]
    if len(matches) != 1:
        raise _error(f"{label} does not contain one {key}={value}")
    return matches[0]


def _live_selection() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    scanner = _load_module(
        "annual_tangible_rotated_panel_scanner",
        "scripts/experiments/scan_tangible_fixed_assets_full_document_vietocr_v1.py",
    )
    scanner.MATCHER_VARIANT_PROFILE = "REPORTING_PERIOD_GENERAL_V2"
    semantic_index, semantic_payload = _json(SEMANTIC_INDEX_PATH, EXPECTED_SEMANTIC_INDEX_SHA256)
    crop_manifest, crop_payload = _json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    rotated_manifest, rotated_manifest_payload = _json(
        ROTATED_RESCUE_MANIFEST_PATH, EXPECTED_ROTATED_RESCUE_MANIFEST_SHA256
    )
    scan = scanner.build_live_tangible_fixed_assets_full_document_scan_v1(SEMANTIC_INDEX_PATH)
    if scan.get("scan_id") != EXPECTED_SCAN_ID:
        raise _error("annual tangible-asset scan identity drifted")
    rescue = scanner._profile_rescue(semantic_index, scanner.DEFAULT_RESCUE_ROOT)
    if type(rescue) is not dict or type(rescue.get("samples")) is not list:
        raise _error("annual rotated semantic rescue is unavailable")
    rotated_manifest_ref = _ref(ROTATED_RESCUE_MANIFEST_PATH, rotated_manifest_payload)
    if not same_typed_json_v1(
        rescue.get("input_refs", {}).get("crop_manifest"), rotated_manifest_ref
    ):
        raise _error("semantic rescue does not authenticate its rotated crop manifest")
    if type(rotated_manifest.get("samples")) is not list:
        raise _error("rotated crop manifest sample denominator drifted")
    rescue_pages = {
        (sample["document_ordinal"], sample["physical_page"]) for sample in rescue["samples"]
    }
    selected: list[dict[str, Any]] = []
    for trial in scan["trials"]:
        matcher = trial["matcher_result"]
        if matcher["status"] != "ACCEPTED_UNIQUE_VARIANT_GRAPH" or len(matcher["regions"]) != 1:
            raise _error("one annual document lost its unique tangible-asset region")
        region = matcher["regions"][0]
        if region["layout"]["rotated_source_axis"] is not True:
            continue
        document_ordinal = trial["document_ordinal"]
        physical_page = region["owner"]["page_sequence"]
        if (document_ordinal, physical_page) not in rescue_pages:
            raise _error("rotated graph page is absent from geometry-selected rescue")
        crop_document = _one(
            crop_manifest["documents"], "document_ordinal", document_ordinal, "crop document"
        )
        crop_page = _one(crop_document["pages"], "physical_page", physical_page, "crop page")
        page_samples = [
            sample
            for sample in rescue["samples"]
            if sample["document_ordinal"] == document_ordinal
            and sample["physical_page"] == physical_page
        ]
        if len(page_samples) != crop_page["line_count"]:
            raise _error("rotated rescue does not cover the complete selected page")
        raw_rotated_samples = sorted(
            (
                sample
                for sample in rotated_manifest["samples"]
                if type(sample) is dict
                and sample.get("document_ordinal") == document_ordinal
                and sample.get("physical_page") == physical_page
            ),
            key=lambda sample: sample.get("source_line_index", -1),
        )
        page_samples = sorted(page_samples, key=lambda sample: sample.get("source_line_index", -1))
        if len(raw_rotated_samples) != crop_page["line_count"]:
            raise _error("rotated crop manifest does not cover the selected page")
        for projected, raw in zip(page_samples, raw_rotated_samples, strict=True):
            rotated_ref = raw.get("rotated_crop_ref")
            source_ref = raw.get("source_crop_ref")
            if (
                type(rotated_ref) is not dict
                or set(rotated_ref) != _REF_FIELDS
                or type(source_ref) is not dict
                or set(source_ref) != _REF_FIELDS
                or projected.get("source_line_index") != raw.get("source_line_index")
                or projected.get("source_crop_sha256") != source_ref.get("sha256")
            ):
                raise _error("semantic rescue and rotated manifest line axes drifted")
        render_ref = canonical_clone_v1(crop_page["render_binding"])
        render_payload = _stable_bytes(Path(render_ref["path"]))
        if (
            set(render_ref) != _REF_FIELDS
            or len(render_payload) != render_ref["size_bytes"]
            or _sha256(render_payload) != render_ref["sha256"]
        ):
            raise _error("source render binding drifted")
        axis_material = [
            {
                "rotated_crop_sha256": sample["rotated_crop_ref"]["sha256"],
                "source_line_index": sample["source_line_index"],
            }
            for sample in raw_rotated_samples
        ]
        selected.append(
            {
                "document_ordinal": document_ordinal,
                "line_count": crop_page["line_count"],
                "physical_page": physical_page,
                "render_payload": render_payload,
                "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                "source_render_ref": render_ref,
                "source_semantic_line_axis_sha256": canonical_json_sha256_v1(axis_material),
            }
        )
    if len(selected) != EXPECTED_PAGE_COUNT:
        raise _error("rotated tangible-asset page denominator drifted")
    refs = {
        "crop_manifest": _ref(CROP_MANIFEST_PATH, crop_payload),
        "rotated_rescue_crop_manifest": rotated_manifest_ref,
        "semantic_index": _ref(SEMANTIC_INDEX_PATH, semantic_payload),
        "structure_scan_id": EXPECTED_SCAN_ID,
    }
    return selected, refs


def _rotated_png(source_payload: bytes) -> bytes:
    try:
        with Image.open(io.BytesIO(source_payload)) as image:
            rotated = image.convert("RGB").transpose(Image.Transpose.ROTATE_270)
            buffer = io.BytesIO()
            rotated.save(buffer, format="PNG")
    except OSError as exc:
        raise _error("cannot decode source page render") from exc
    return buffer.getvalue()


def _clean_git() -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if dirty.strip():
        raise _error("rotated numeric panel requires a clean Git worktree")
    return {"commit": commit, "dirty": False}


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
                raise _error(f"refusing to overwrite existing panel: {destination}")
            raise _error(f"atomic panel publication failed with errno {code}")
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


def build_annual_2025_tangible_rotated_ppocrv6_panel_v1() -> dict[str, Any]:
    """Materialize graph-selected source and clockwise-rotated page pixels."""

    git = _clean_git()
    if (PROJECT_ROOT / OUTPUT_ROOT).exists():
        raise _error(f"refusing to overwrite existing panel: {OUTPUT_ROOT}")
    selected, input_refs = _live_selection()
    parent = PROJECT_ROOT / OUTPUT_ROOT.parent
    parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".annual-tfa-rotated-ppocr-", dir=parent))
    try:
        pages = []
        for ordinal, item in enumerate(selected, 1):
            page_root = stage / f"page-{ordinal:04d}"
            page_root.mkdir(mode=0o700)
            source_path = page_root / "source-page.png"
            rotated_path = page_root / "rotated-page.png"
            source_path.write_bytes(item["render_payload"])
            rotated_payload = _rotated_png(item["render_payload"])
            rotated_path.write_bytes(rotated_payload)
            pages.append(
                {
                    "document_ordinal": item["document_ordinal"],
                    "line_count": item["line_count"],
                    "physical_page": item["physical_page"],
                    "rotated_page_ref": _ref(
                        OUTPUT_ROOT / page_root.name / rotated_path.name, rotated_payload
                    ),
                    "source_pdf_sha256": item["source_pdf_sha256"],
                    "source_render_ref": item["source_render_ref"],
                    "source_semantic_line_axis_sha256": item["source_semantic_line_axis_sha256"],
                }
            )
        material = {
            "authority": canonical_clone_v1(_AUTHORITY),
            "format_version": FORMAT_VERSION,
            "git_binding": git,
            "input_refs": input_refs,
            "metrics": {"page_count": len(pages)},
            "pages": pages,
            "selection_rule": SELECTION_RULE,
            "state": "ROTATED_PPOCRV6_PAGE_PANEL_READY",
        }
        manifest = {
            **material,
            "panel_id": PANEL_ID_PREFIX + canonical_json_sha256_v1(material),
        }
        (stage / MANIFEST_PATH.name).write_bytes(canonical_json_bytes_v1(manifest) + b"\n")
        _publish_noreplace(stage, PROJECT_ROOT / OUTPUT_ROOT)
        return manifest
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def _validate_manifest(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value)
        != {
            "authority",
            "format_version",
            "git_binding",
            "input_refs",
            "metrics",
            "pages",
            "panel_id",
            "selection_rule",
            "state",
        }
        or value["format_version"] != FORMAT_VERSION
        or value["state"] != "ROTATED_PPOCRV6_PAGE_PANEL_READY"
        or value["selection_rule"] != SELECTION_RULE
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["pages"]) is not list
        or len(value["pages"]) != EXPECTED_PAGE_COUNT
        or not same_typed_json_v1(value["metrics"], {"page_count": EXPECTED_PAGE_COUNT})
    ):
        raise _error("rotated numeric panel manifest shape drifted")
    for page in value["pages"]:
        if type(page) is not dict or set(page) != _PAGE_FIELDS:
            raise _error("rotated numeric panel page shape drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("panel_id")
    if identity != PANEL_ID_PREFIX + canonical_json_sha256_v1(material):
        raise _error("rotated numeric panel identity drifted")
    return canonical_clone_v1(value)


def _ppocr_page(page: dict[str, Any], ordinal: int) -> dict[str, Any]:
    page_root = OUTPUT_ROOT / f"page-{ordinal:04d}"
    rotated_payload = _stable_bytes(page_root / "rotated-page.png")
    rotated_ref = page["rotated_page_ref"]
    if (
        set(rotated_ref) != _REF_FIELDS
        or len(rotated_payload) != rotated_ref["size_bytes"]
        or _sha256(rotated_payload) != rotated_ref["sha256"]
    ):
        raise _error("rotated page bytes drifted")
    source_payload = _stable_bytes(page_root / "source-page.png")
    with Image.open(io.BytesIO(source_payload)) as source_image:
        expected = source_image.convert("RGB").transpose(Image.Transpose.ROTATE_270)
    with Image.open(io.BytesIO(rotated_payload)) as actual_image:
        actual = actual_image.convert("RGB")
    if (
        expected.size != actual.size
        or ImageChops.difference(expected, actual).getbbox() is not None
    ):
        raise _error("rotated page is not the exact clockwise source transform")
    result_path = page_root / "reader-output/ocr_result.json"
    run_path = page_root / "reader-output/run_manifest.json"
    result, result_payload = _json(result_path)
    run, run_payload = _json(run_path)
    texts = result.get("rec_texts")
    scores = result.get("rec_scores")
    boxes = result.get("rec_boxes")
    words = result.get("text_word")
    word_boxes = result.get("text_word_boxes")
    runtime = run.get("runtime")
    models = runtime.get("models") if type(runtime) is dict else None
    normalized_width, normalized_height = actual.size

    def valid_word_box(value: Any) -> bool:
        return (
            type(value) is list
            and len(value) == 4
            and all(type(item) is int for item in value)
            and 0 <= value[0] < value[2] <= normalized_width
            and 0 <= value[1] < value[3] <= normalized_height
        )

    def valid_line_box(value: Any) -> bool:
        return valid_word_box(value)

    if (
        type(texts) is not list
        or type(scores) is not list
        or type(boxes) is not list
        or not len(texts) == len(scores) == len(boxes)
        or not texts
        or not all(type(text) is str for text in texts)
        or not all(type(score) is float and math.isfinite(score) for score in scores)
        or any(not valid_line_box(box) for box in boxes)
        or (
            INCLUDE_WORD_AXIS
            and (
                result.get("return_word_box") is not True
                or type(words) is not list
                or type(word_boxes) is not list
                or len(words) != len(texts)
                or len(word_boxes) != len(texts)
                or any(type(line) is not list for line in words)
                or any(type(line) is not list for line in word_boxes)
                or any(type(token) is not str for line in words for token in line)
                or any(
                    len(line_words) != len(line_boxes)
                    for line_words, line_boxes in zip(words, word_boxes, strict=True)
                )
                or any(not valid_word_box(box) for line in word_boxes for box in line)
            )
        )
        or run.get("state") != "OCR_COMPLETE"
        or run.get("dataset_role") != "CALIBRATION"
        or run.get("evidence_role") != "INDEPENDENT_GEOMETRY_PROPOSAL_ONLY"
        or run.get("input", {}).get("sha256") != rotated_ref["sha256"]
        or run.get("input", {}).get("size_bytes") != rotated_ref["size_bytes"]
        or run.get("configuration", {}).get("implicit_orientation_or_unwarp") is not False
        or run.get("configuration", {}).get("precision") != "fp32"
        or type(models) is not list
        or len(models) != 2
        or models[0].get("repo_id") != "PaddlePaddle/PP-OCRv6_medium_det"
        or models[1].get("repo_id") != "PaddlePaddle/PP-OCRv6_medium_rec"
    ):
        raise _error("rotated PP-OCRv6 result or runtime identity drifted")
    projection = {
        **canonical_clone_v1(page),
        "ocr_result_ref": _ref(result_path, result_payload),
        "rec_boxes": boxes,
        "rec_scores": scores,
        "rec_texts": texts,
        "run_manifest_ref": _ref(run_path, run_payload),
    }
    if INCLUDE_WORD_AXIS:
        projection["text_word"] = words
        projection["text_word_boxes"] = word_boxes
    return projection


def read_verified_annual_2025_tangible_rotated_ppocrv6_panel_v1() -> dict[str, Any]:
    """Replay panel selection/pixels and return the three independent OCR axes."""

    manifest, manifest_payload = _json(MANIFEST_PATH)
    supplied = _validate_manifest(manifest)
    selected, input_refs = _live_selection()
    if supplied["input_refs"] != input_refs:
        raise _error("rotated numeric panel live inputs drifted")
    for page, live in zip(supplied["pages"], selected, strict=True):
        if (
            page["document_ordinal"] != live["document_ordinal"]
            or page["physical_page"] != live["physical_page"]
            or page["line_count"] != live["line_count"]
            or page["source_pdf_sha256"] != live["source_pdf_sha256"]
            or page["source_render_ref"] != live["source_render_ref"]
            or page["source_semantic_line_axis_sha256"] != live["source_semantic_line_axis_sha256"]
        ):
            raise _error("rotated numeric panel no longer matches the live graph selection")
    pages = [_ppocr_page(page, ordinal) for ordinal, page in enumerate(supplied["pages"], 1)]
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "format_version": PROJECTION_FORMAT,
        "input_refs": {
            "panel_manifest": _ref(MANIFEST_PATH, manifest_payload),
            **input_refs,
        },
        "metrics": {
            "ocr_line_count": sum(len(page["rec_texts"]) for page in pages),
            "page_count": len(pages),
        },
        "pages": pages,
        "panel_id": supplied["panel_id"],
        "state": "ROTATED_PPOCRV6_NUMERIC_PANEL_VERIFIED",
    }
    return {
        **material,
        "projection_id": PROJECTION_ID_PREFIX + canonical_json_sha256_v1(material),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--build", action="store_true")
    action.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.build:
        value = build_annual_2025_tangible_rotated_ppocrv6_panel_v1()
        print(value["panel_id"])
    else:
        value = read_verified_annual_2025_tangible_rotated_ppocrv6_panel_v1()
        print(value["projection_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
