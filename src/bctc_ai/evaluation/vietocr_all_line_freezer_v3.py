"""Deterministically freeze all 835 lines from the live eight-page READY panel.

Only a live READY-panel capability can enter this boundary.  The resulting
reader request contains opaque page/sample IDs and crop references; it never
contains source provenance, transcripts, semantic labels, or model outputs.
"""

from __future__ import annotations

import ctypes
import errno
import hashlib
import io
import json
import os
import re
import secrets
import stat
import subprocess
import weakref
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from PIL import Image, ImageOps

from bctc_ai.evaluation.loan_maturity_8bank_ready_panel_v1 import (
    EXPECTED_LINE_COUNT_VECTOR,
    EXPECTED_SAMPLE_COUNT,
    AuthenticatedLoanMaturity8BankReadyPanelV1,
    project_authenticated_loan_maturity_8bank_anonymous_batch_v1,
    read_authenticated_loan_maturity_8bank_anonymous_page_v1,
    validate_authenticated_loan_maturity_8bank_anonymous_batch_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    decode_canonical_json_bytes_v1,
    same_typed_json_v1,
)

__all__ = [
    "ARTIFACT_ROOT",
    "AuthenticatedVietOCRAllLineFreezeV3",
    "CROP_MANIFEST_FORMAT_VERSION",
    "EXPECTED_LINE_COUNT_VECTOR",
    "EXPECTED_SAMPLE_COUNT",
    "FREEZE_PROJECTION_FORMAT_VERSION",
    "READER_REQUEST_FORMAT_VERSION",
    "VietOCRAllLineFreezerV3Error",
    "assert_authenticated_vietocr_all_line_freeze_project_root_v3",
    "freeze_authenticated_vietocr_all_line_batch_v3",
    "project_authenticated_vietocr_all_line_freeze_v3",
    "read_authenticated_vietocr_all_line_snapshot_v3",
    "read_authenticated_vietocr_all_line_batch_v3",
    "read_authenticated_vietocr_all_line_crop_v3",
    "replay_authenticated_vietocr_all_line_freeze_v3",
    "validate_authenticated_vietocr_all_line_freeze_projection_v3",
]


class VietOCRAllLineFreezerV3Error(RuntimeError):
    """The authenticated anonymous all-LINE freeze cannot be established."""


CROP_MANIFEST_FORMAT_VERSION = "BCTC_AI_VIETOCR_ALL_LINE_CROP_MANIFEST_V3"
READER_REQUEST_FORMAT_VERSION = "BCTC_AI_VIETOCR_REFERENCE_BLIND_LINE_REQUEST_V3"
FREEZE_PROJECTION_FORMAT_VERSION = "BCTC_AI_VIETOCR_ALL_LINE_FREEZE_PROJECTION_V3"
EXPERIMENT_ID = "VIETOCR_VGG_TRANSFORMER_ALL_LINE_8X835_V3"
ARTIFACT_ROOT = Path("output/development/vietocr-all-line-freeze-v3")
EXPECTED_PAGE_COUNT = 8
SOURCE_PADDING = (8, 4, 8, 4)
WHITE_BORDER = (12, 8, 12, 8)
_IMPLEMENTATION_PATH = Path("src/bctc_ai/evaluation/vietocr_all_line_freezer_v3.py")
_MANIFEST_NAME = "crop_manifest.json"
_REQUEST_NAME = "reader_request.json"
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_SAMPLE_ID_RE = re.compile(r"^page-[0-9]{4}-line-[0-9]{4}$")

CROP_POLICY = {
    "deskew": False,
    "filter": False,
    "grouping": "ONE_CROP_PER_AUTHENTICATED_LINE",
    "line_order": "AUTHENTICATED_PAGE_ORDER_THEN_AUTHENTICATED_LINE_ARRAY_ORDER",
    "resize": False,
    "selection": "EVERY_AUTHENTICATED_LINE_EXACTLY_ONCE",
    "source_padding_left_top_right_bottom": list(SOURCE_PADDING),
    "threshold": False,
    "unions": False,
    "white_border_left_top_right_bottom": list(WHITE_BORDER),
}
_MANIFEST_AUTHORITY = {
    "geometry_change": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "semantic_authority": False,
    "text_recognition_authority": False,
}
_PROJECTION_AUTHORITY = {
    "crop_bytes_replay_authenticated": True,
    "live_capability_required": True,
    "model_run_authority": False,
    "raw_projection_self_authenticates": False,
    "semantic_receipt_authority": False,
}

_MANIFEST_FIELDS = {
    "authority",
    "crop_policy",
    "format_version",
    "git_binding",
    "input_batch_id",
    "line_count_vector",
    "page_count",
    "pages",
    "sample_count",
    "samples",
    "state",
}
_MANIFEST_PAGE_FIELDS = {"line_count", "page_id", "pixel_height", "pixel_width"}
_MANIFEST_SAMPLE_FIELDS = {
    "crop_height",
    "crop_path",
    "crop_sha256",
    "crop_size_bytes",
    "crop_width",
    "line_index",
    "page_id",
    "sample_id",
}
_REQUEST_FIELDS = {
    "crop_manifest",
    "dataset_role",
    "evidence_role",
    "experiment_id",
    "format_version",
    "git_commit",
    "git_dirty",
    "line_count_vector",
    "page_count",
    "reference_text_available_to_reader",
    "sample_count",
    "samples",
    "state",
}
_REQUEST_SAMPLE_FIELDS = {"crop_path", "crop_sha256", "page_id", "sample_id"}
_REF_FIELDS = {"path", "sha256", "size_bytes"}
_GIT_FIELDS = {"commit", "dirty", "implementation_ref", "source_tree_oid"}
_PROJECTION_FIELDS = {
    "authority",
    "crop_manifest_ref",
    "format_version",
    "freeze_id",
    "line_count_vector",
    "page_count",
    "reader_request_ref",
    "sample_count",
    "state",
}


def _error(message: str) -> VietOCRAllLineFreezerV3Error:
    return VietOCRAllLineFreezerV3Error(message)


def _exact(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise _error(f"{label} must contain the exact closed field set")
    return cast(dict[str, Any], value)


def _safe_relative(value: Path | str, label: str, suffix: str | None = None) -> Path:
    if type(value) is str:
        text = value
    elif isinstance(value, Path):
        text = value.as_posix()
    else:
        raise _error(f"{label} path type is invalid")
    path = Path(text)
    if (
        not text
        or "\\" in text
        or path.is_absolute()
        or text != path.as_posix()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
        or (suffix is not None and path.suffix != suffix)
    ):
        raise _error(f"{label} must be canonical project-relative POSIX")
    return path


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or _SHA_RE.fullmatch(value) is None:
        raise _error(f"{label} must be one lowercase SHA-256")
    return value


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} must be one positive integer")
    return value


def _git(root: Path, *args: str, text: bool = True) -> str | bytes:
    result = subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=text)
    return cast(str, result.stdout).strip() if text else cast(bytes, result.stdout)


def _stable_nofollow_bytes(root: Path, relative: Path | str, label: str) -> bytes:
    path = _safe_relative(relative, label)
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    file_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    current = os.open(root, directory_flags)
    descriptor: int | None = None
    try:
        for part in path.parts[:-1]:
            following = os.open(part, directory_flags, dir_fd=current)
            os.close(current)
            current = following
        descriptor = os.open(path.parts[-1], file_flags, dir_fd=current)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise _error(f"{label} is not a regular file")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        after = os.fstat(descriptor)
        identity = lambda item: (  # noqa: E731
            item.st_dev,
            item.st_ino,
            item.st_mode,
            item.st_size,
            item.st_mtime_ns,
            item.st_ctime_ns,
        )
        if identity(before) != identity(after):
            raise _error(f"{label} changed during stable read")
        payload = b"".join(chunks)
        if len(payload) != before.st_size:
            raise _error(f"{label} stable-read size drifted")
        return payload
    except OSError as exc:
        raise _error(f"cannot stably read nofollow {label}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(current)


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    def reject_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise _error(f"{label} contains duplicate key")
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=reject_duplicate,
            parse_constant=lambda value: (_ for _ in ()).throw(_error(f"nonfinite {value}")),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise _error(f"cannot decode {label} as strict JSON") from exc
    if type(value) is not dict:
        raise _error(f"{label} must be one JSON object")
    return cast(dict[str, Any], value)


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def _file_ref(path: Path, payload: bytes) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _validate_ref(value: Any, expected_path: Path, label: str) -> dict[str, Any]:
    reference = _exact(value, _REF_FIELDS, label)
    path = _safe_relative(reference["path"], f"{label} path")
    if path != expected_path:
        raise _error(f"{label} path identity drifted")
    _sha(reference["sha256"], f"{label} hash")
    _positive_int(reference["size_bytes"], f"{label} size")
    return canonical_clone_v1(reference)


def _clean_git_binding(root: Path) -> dict[str, Any]:
    try:
        status = _git(root, "status", "--porcelain", "--untracked-files=all")
        commit = _git(root, "rev-parse", "HEAD")
        source_tree_oid = _git(root, "rev-parse", "HEAD:src/bctc_ai")
    except (OSError, subprocess.CalledProcessError) as exc:
        raise _error("cannot establish clean Git implementation identity") from exc
    if status != "":
        raise _error("formal all-LINE freeze requires one clean Git worktree")
    if (
        type(commit) is not str
        or _COMMIT_RE.fullmatch(commit) is None
        or type(source_tree_oid) is not str
        or _COMMIT_RE.fullmatch(source_tree_oid) is None
    ):
        raise _error("Git commit identity is invalid")
    implementation = _stable_nofollow_bytes(root, _IMPLEMENTATION_PATH, "freezer implementation")
    try:
        committed = _git(
            root,
            "show",
            f"{commit}:{_IMPLEMENTATION_PATH.as_posix()}",
            text=False,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise _error("freezer implementation is not tracked by the clean commit") from exc
    if type(committed) is not bytes or committed != implementation:
        raise _error("freezer implementation bytes differ from the clean commit")
    return {
        "commit": commit,
        "dirty": False,
        "implementation_ref": _file_ref(_IMPLEMENTATION_PATH, implementation),
        "source_tree_oid": source_tree_oid,
    }


def _git_commit_is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    try:
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        return False
    return True


def _assert_git_binding(root: Path, expected: dict[str, Any], label: str) -> None:
    """Allow clean descendants only when the frozen implementation is unchanged."""

    current = _clean_git_binding(root)
    if (
        not same_typed_json_v1(current["implementation_ref"], expected["implementation_ref"])
        or current["source_tree_oid"] != expected["source_tree_oid"]
    ):
        raise _error(f"Git implementation identity changed {label}")
    if not _git_commit_is_ancestor(root, expected["commit"], current["commit"]):
        raise _error(f"Git freeze commit is not an ancestor of the clean replay commit {label}")


def _resolve_root(project_root: Path) -> Path:
    if not isinstance(project_root, Path):
        raise _error("project root must be one pathlib Path")
    try:
        root = project_root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise _error("project root cannot be resolved") from exc
    if not root.is_dir():
        raise _error("project root is not a directory")
    return root


def _validate_output_parent(root: Path, output_root: Path) -> Path:
    relative = _safe_relative(output_root, "freeze output root")
    if relative != ARTIFACT_ROOT:
        raise _error("formal all-LINE freeze output root is fixed and provenance-opaque")
    parent_relative = relative.parent
    if parent_relative == Path("."):
        parent = root
    else:
        try:
            parent = (root / parent_relative).resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise _error("freeze output parent must already exist") from exc
        if not parent.is_relative_to(root) or not parent.is_dir():
            raise _error("freeze output parent escapes project root")
        cursor = root
        for part in parent_relative.parts:
            cursor = cursor / part
            try:
                if stat.S_ISLNK(cursor.lstat().st_mode):
                    raise _error("freeze output parent contains a symlink")
            except OSError as exc:
                raise _error("cannot inspect freeze output parent") from exc
    return relative


def _png_rgb(payload: bytes, label: str) -> Image.Image:
    if type(payload) is not bytes:
        raise _error(f"{label} render must be immutable bytes")
    try:
        with Image.open(io.BytesIO(payload)) as image:
            if image.format != "PNG":
                raise _error(f"{label} is not PNG")
            image.load()
            result = image.convert("RGB")
    except (OSError, ValueError) as exc:
        raise _error(f"{label} is not readable PNG") from exc
    if result.width <= 0 or result.height <= 0:
        raise _error(f"{label} dimensions are invalid")
    return result


def _bbox(value: Any, width: int, height: int, label: str) -> tuple[int, int, int, int]:
    if type(value) is not list or len(value) != 4 or any(type(item) is not int for item in value):
        raise _error(f"{label} is not one integer pixel bbox")
    x0, y0, x1, y1 = value
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise _error(f"{label} lies outside its authenticated render")
    return x0, y0, x1, y1


def _crop_bytes(image: Image.Image, bbox: tuple[int, int, int, int]) -> tuple[bytes, int, int]:
    left, top, right, bottom = SOURCE_PADDING
    padded = (
        max(0, bbox[0] - left),
        max(0, bbox[1] - top),
        min(image.width, bbox[2] + right),
        min(image.height, bbox[3] + bottom),
    )
    crop = ImageOps.expand(image.crop(padded), border=WHITE_BORDER, fill="white")
    stream = io.BytesIO()
    crop.save(stream, format="PNG", optimize=False, compress_level=6)
    return stream.getvalue(), crop.width, crop.height


def _collect_ready(
    capability: AuthenticatedLoanMaturity8BankReadyPanelV1,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    if type(capability) is not AuthenticatedLoanMaturity8BankReadyPanelV1:
        raise _error("all-LINE freeze requires one exact live READY-panel capability")
    batch = project_authenticated_loan_maturity_8bank_anonymous_batch_v1(capability)
    validate_authenticated_loan_maturity_8bank_anonymous_batch_v1(batch, capability)
    if (
        batch.get("page_count") != EXPECTED_PAGE_COUNT
        or batch.get("line_count_vector") != list(EXPECTED_LINE_COUNT_VECTOR)
        or batch.get("sample_count") != EXPECTED_SAMPLE_COUNT
        or type(batch.get("batch_id")) is not str
        or not batch["batch_id"].startswith("lm8brpv1:batch:")
        or _SHA_RE.fullmatch(batch["batch_id"].removeprefix("lm8brpv1:batch:")) is None
    ):
        raise _error("live READY-panel exact batch identity or denominator drifted")
    pages: list[dict[str, Any]] = []
    page_fields = {
        "line_bboxes",
        "line_count",
        "page_id",
        "page_ordinal",
        "pixel_height",
        "pixel_width",
        "render_png_bytes",
    }
    for ordinal, expected_count in enumerate(EXPECTED_LINE_COUNT_VECTOR, start=1):
        page = read_authenticated_loan_maturity_8bank_anonymous_page_v1(capability, ordinal)
        if type(page) is not dict or set(page) != page_fields:
            raise _error(f"anonymous READY page {ordinal:04d} field set drifted")
        width = _positive_int(page["pixel_width"], f"page {ordinal:04d} width")
        height = _positive_int(page["pixel_height"], f"page {ordinal:04d} height")
        render = page["render_png_bytes"]
        image = _png_rgb(render, f"page {ordinal:04d} render")
        boxes = page["line_bboxes"]
        if (
            page["page_id"] != f"page-{ordinal:04d}"
            or type(page["page_ordinal"]) is not int
            or page["page_ordinal"] != ordinal
            or type(page["line_count"]) is not int
            or page["line_count"] != expected_count
            or type(boxes) is not list
            or len(boxes) != expected_count
            or image.size != (width, height)
        ):
            raise _error(f"anonymous READY page {ordinal:04d} identity/denominator drifted")
        validated_boxes = [
            list(_bbox(box, width, height, f"page {ordinal:04d} line {index:04d}"))
            for index, box in enumerate(boxes)
        ]
        pages.append(
            {
                "line_bboxes": validated_boxes,
                "line_count": expected_count,
                "page_id": page["page_id"],
                "page_ordinal": ordinal,
                "pixel_height": height,
                "pixel_width": width,
                "render_png_bytes": bytes(render),
            }
        )
    return canonical_clone_v1(batch), tuple(pages)


def _build_crop_payloads(
    pages: tuple[dict[str, Any], ...], output_root: Path
) -> tuple[tuple[bytes, ...], list[dict[str, Any]], list[dict[str, Any]]]:
    crop_payloads: list[bytes] = []
    page_records: list[dict[str, Any]] = []
    sample_records: list[dict[str, Any]] = []
    for page, expected_count in zip(pages, EXPECTED_LINE_COUNT_VECTOR, strict=True):
        image = _png_rgb(page["render_png_bytes"], f"{page['page_id']} render")
        page_records.append(
            {
                "line_count": expected_count,
                "page_id": page["page_id"],
                "pixel_height": page["pixel_height"],
                "pixel_width": page["pixel_width"],
            }
        )
        for line_index, raw_bbox in enumerate(page["line_bboxes"]):
            bbox = _bbox(
                raw_bbox,
                page["pixel_width"],
                page["pixel_height"],
                f"{page['page_id']} line {line_index:04d}",
            )
            sample_id = f"{page['page_id']}-line-{line_index:04d}"
            crop, width, height = _crop_bytes(image, bbox)
            crop_path = output_root / "frozen/crops" / f"{sample_id}.png"
            crop_payloads.append(crop)
            sample_records.append(
                {
                    "crop_height": height,
                    "crop_path": crop_path.as_posix(),
                    "crop_sha256": hashlib.sha256(crop).hexdigest(),
                    "crop_size_bytes": len(crop),
                    "crop_width": width,
                    "line_index": line_index,
                    "page_id": page["page_id"],
                    "sample_id": sample_id,
                }
            )
    if len(crop_payloads) != EXPECTED_SAMPLE_COUNT or len(sample_records) != EXPECTED_SAMPLE_COUNT:
        raise _error("not every authenticated READY line was cropped exactly once")
    return tuple(crop_payloads), page_records, sample_records


def _build_artifacts(
    *,
    batch: dict[str, Any],
    pages: tuple[dict[str, Any], ...],
    output_root: Path,
    git_binding: dict[str, Any],
) -> tuple[dict[str, Any], bytes, dict[str, Any], bytes, tuple[bytes, ...]]:
    crops, page_records, samples = _build_crop_payloads(pages, output_root)
    manifest = {
        "authority": canonical_clone_v1(_MANIFEST_AUTHORITY),
        "crop_policy": canonical_clone_v1(CROP_POLICY),
        "format_version": CROP_MANIFEST_FORMAT_VERSION,
        "git_binding": canonical_clone_v1(git_binding),
        "input_batch_id": batch["batch_id"],
        "line_count_vector": list(EXPECTED_LINE_COUNT_VECTOR),
        "page_count": EXPECTED_PAGE_COUNT,
        "pages": page_records,
        "sample_count": EXPECTED_SAMPLE_COUNT,
        "samples": samples,
        "state": "FROZEN_BEFORE_ANY_SEMANTIC_MODEL_INFERENCE",
    }
    manifest = _validate_manifest(manifest, output_root, batch["batch_id"])
    manifest_payload = _json_bytes(manifest)
    manifest_path = output_root / "frozen" / _MANIFEST_NAME
    request = {
        "crop_manifest": _file_ref(manifest_path, manifest_payload),
        "dataset_role": "LOGIC_DEVELOPMENT_AND_CALIBRATION",
        "evidence_role": "INDEPENDENT_VIETNAMESE_SEMANTIC_PROPOSAL_ONLY",
        "experiment_id": EXPERIMENT_ID,
        "format_version": READER_REQUEST_FORMAT_VERSION,
        "git_commit": git_binding["commit"],
        "git_dirty": False,
        "line_count_vector": list(EXPECTED_LINE_COUNT_VECTOR),
        "page_count": EXPECTED_PAGE_COUNT,
        "reference_text_available_to_reader": False,
        "sample_count": EXPECTED_SAMPLE_COUNT,
        "samples": [
            {
                "crop_path": sample["crop_path"],
                "crop_sha256": sample["crop_sha256"],
                "page_id": sample["page_id"],
                "sample_id": sample["sample_id"],
            }
            for sample in samples
        ],
        "state": "READY_FOR_REFERENCE_BLIND_LINE_INFERENCE",
    }
    request = _validate_request(request, manifest, manifest_payload, output_root)
    return manifest, manifest_payload, request, _json_bytes(request), crops


def _validate_git_shape(value: Any) -> dict[str, Any]:
    binding = _exact(value, _GIT_FIELDS, "freeze Git binding")
    commit = binding["commit"]
    if (
        type(commit) is not str
        or _COMMIT_RE.fullmatch(commit) is None
        or binding["dirty"] is not False
        or type(binding["source_tree_oid"]) is not str
        or _COMMIT_RE.fullmatch(binding["source_tree_oid"]) is None
    ):
        raise _error("freeze Git identity drifted")
    reference = _validate_ref(
        binding["implementation_ref"], _IMPLEMENTATION_PATH, "freezer implementation ref"
    )
    return {
        "commit": commit,
        "dirty": False,
        "implementation_ref": reference,
        "source_tree_oid": binding["source_tree_oid"],
    }


def _validate_manifest(value: Any, output_root: Path, expected_batch_id: str) -> dict[str, Any]:
    manifest = _exact(value, _MANIFEST_FIELDS, "crop manifest")
    if (
        manifest["format_version"] != CROP_MANIFEST_FORMAT_VERSION
        or manifest["state"] != "FROZEN_BEFORE_ANY_SEMANTIC_MODEL_INFERENCE"
        or not same_typed_json_v1(manifest["authority"], _MANIFEST_AUTHORITY)
        or not same_typed_json_v1(manifest["crop_policy"], CROP_POLICY)
        or manifest["input_batch_id"] != expected_batch_id
        or type(manifest["page_count"]) is not int
        or manifest["page_count"] != EXPECTED_PAGE_COUNT
        or not same_typed_json_v1(manifest["line_count_vector"], list(EXPECTED_LINE_COUNT_VECTOR))
        or type(manifest["sample_count"]) is not int
        or manifest["sample_count"] != EXPECTED_SAMPLE_COUNT
    ):
        raise _error("crop manifest identity, input batch, policy, or denominator drifted")
    manifest["git_binding"] = _validate_git_shape(manifest["git_binding"])
    pages = manifest["pages"]
    if type(pages) is not list or len(pages) != EXPECTED_PAGE_COUNT:
        raise _error("crop manifest must preserve exactly eight anonymous pages")
    for ordinal, (page, expected_count) in enumerate(
        zip(pages, EXPECTED_LINE_COUNT_VECTOR, strict=True), start=1
    ):
        page = _exact(page, _MANIFEST_PAGE_FIELDS, f"manifest page {ordinal:04d}")
        if (
            page["page_id"] != f"page-{ordinal:04d}"
            or type(page["line_count"]) is not int
            or page["line_count"] != expected_count
        ):
            raise _error(f"manifest page {ordinal:04d} order or denominator drifted")
        _positive_int(page["pixel_width"], f"manifest page {ordinal:04d} width")
        _positive_int(page["pixel_height"], f"manifest page {ordinal:04d} height")
    samples = manifest["samples"]
    if type(samples) is not list or len(samples) != EXPECTED_SAMPLE_COUNT:
        raise _error("crop manifest sample denominator drifted")
    ordinal = 0
    for page_number, expected_count in enumerate(EXPECTED_LINE_COUNT_VECTOR, start=1):
        page_id = f"page-{page_number:04d}"
        for line_index in range(expected_count):
            sample = _exact(samples[ordinal], _MANIFEST_SAMPLE_FIELDS, f"sample {ordinal:04d}")
            sample_id = f"{page_id}-line-{line_index:04d}"
            expected_path = output_root / "frozen/crops" / f"{sample_id}.png"
            if (
                sample["page_id"] != page_id
                or sample["sample_id"] != sample_id
                or type(sample["sample_id"]) is not str
                or _SAMPLE_ID_RE.fullmatch(sample["sample_id"]) is None
                or type(sample["line_index"]) is not int
                or sample["line_index"] != line_index
                or _safe_relative(sample["crop_path"], f"sample {ordinal:04d} path", ".png")
                != expected_path
            ):
                raise _error(f"sample {ordinal:04d} order, ID, or path drifted")
            _sha(sample["crop_sha256"], f"sample {ordinal:04d} crop")
            for field in ("crop_size_bytes", "crop_width", "crop_height"):
                _positive_int(sample[field], f"sample {ordinal:04d} {field}")
            ordinal += 1
    if ordinal != EXPECTED_SAMPLE_COUNT:
        raise _error("manifest does not select every READY line exactly once")
    return canonical_clone_v1(manifest)


def _validate_request(
    value: Any,
    manifest: dict[str, Any],
    manifest_payload: bytes,
    output_root: Path,
) -> dict[str, Any]:
    request = _exact(value, _REQUEST_FIELDS, "anonymous reader request")
    manifest_path = output_root / "frozen" / _MANIFEST_NAME
    reference = _validate_ref(
        request["crop_manifest"], manifest_path, "reader crop-manifest reference"
    )
    if (
        reference["sha256"] != hashlib.sha256(manifest_payload).hexdigest()
        or reference["size_bytes"] != len(manifest_payload)
        or request["format_version"] != READER_REQUEST_FORMAT_VERSION
        or request["experiment_id"] != EXPERIMENT_ID
        or request["state"] != "READY_FOR_REFERENCE_BLIND_LINE_INFERENCE"
        or request["dataset_role"] != "LOGIC_DEVELOPMENT_AND_CALIBRATION"
        or request["evidence_role"] != "INDEPENDENT_VIETNAMESE_SEMANTIC_PROPOSAL_ONLY"
        or request["git_commit"] != manifest["git_binding"]["commit"]
        or request["git_dirty"] is not False
        or request["reference_text_available_to_reader"] is not False
        or type(request["page_count"]) is not int
        or request["page_count"] != EXPECTED_PAGE_COUNT
        or not same_typed_json_v1(request["line_count_vector"], list(EXPECTED_LINE_COUNT_VECTOR))
        or type(request["sample_count"]) is not int
        or request["sample_count"] != EXPECTED_SAMPLE_COUNT
    ):
        raise _error("anonymous reader request identity, role, binding, or denominator drifted")
    samples = request["samples"]
    if type(samples) is not list or len(samples) != EXPECTED_SAMPLE_COUNT:
        raise _error("anonymous reader request sample denominator drifted")
    for ordinal, (sample, manifest_sample) in enumerate(
        zip(samples, manifest["samples"], strict=True)
    ):
        sample = _exact(sample, _REQUEST_SAMPLE_FIELDS, f"reader sample {ordinal:04d}")
        expected = {
            "crop_path": manifest_sample["crop_path"],
            "crop_sha256": manifest_sample["crop_sha256"],
            "page_id": manifest_sample["page_id"],
            "sample_id": manifest_sample["sample_id"],
        }
        if not same_typed_json_v1(sample, expected):
            raise _error(f"reader sample {ordinal:04d} differs from its frozen crop")
    return canonical_clone_v1(request)


def _projection(
    output_root: Path, manifest_payload: bytes, request_payload: bytes
) -> dict[str, Any]:
    value = {
        "authority": canonical_clone_v1(_PROJECTION_AUTHORITY),
        "crop_manifest_ref": _file_ref(output_root / "frozen" / _MANIFEST_NAME, manifest_payload),
        "format_version": FREEZE_PROJECTION_FORMAT_VERSION,
        "line_count_vector": list(EXPECTED_LINE_COUNT_VECTOR),
        "page_count": EXPECTED_PAGE_COUNT,
        "reader_request_ref": _file_ref(output_root / "frozen" / _REQUEST_NAME, request_payload),
        "sample_count": EXPECTED_SAMPLE_COUNT,
        "state": "FROZEN_READY_NO_MODEL_RUN",
    }
    value["freeze_id"] = (
        "voalfv3:freeze:" + hashlib.sha256(canonical_json_bytes_v1(value)).hexdigest()
    )
    return _validate_projection(value, output_root)


def _validate_projection(value: Any, output_root: Path) -> dict[str, Any]:
    projection = _exact(value, _PROJECTION_FIELDS, "freeze projection")
    identifier = projection["freeze_id"]
    if (
        projection["format_version"] != FREEZE_PROJECTION_FORMAT_VERSION
        or projection["state"] != "FROZEN_READY_NO_MODEL_RUN"
        or not same_typed_json_v1(projection["authority"], _PROJECTION_AUTHORITY)
        or type(projection["page_count"]) is not int
        or projection["page_count"] != EXPECTED_PAGE_COUNT
        or not same_typed_json_v1(projection["line_count_vector"], list(EXPECTED_LINE_COUNT_VECTOR))
        or type(projection["sample_count"]) is not int
        or projection["sample_count"] != EXPECTED_SAMPLE_COUNT
        or type(identifier) is not str
        or not identifier.startswith("voalfv3:freeze:")
        or _SHA_RE.fullmatch(identifier.removeprefix("voalfv3:freeze:")) is None
    ):
        raise _error("freeze projection identity, authority, or denominator drifted")
    _validate_ref(
        projection["crop_manifest_ref"],
        output_root / "frozen" / _MANIFEST_NAME,
        "projection crop-manifest reference",
    )
    _validate_ref(
        projection["reader_request_ref"],
        output_root / "frozen" / _REQUEST_NAME,
        "projection reader-request reference",
    )
    payload = canonical_clone_v1(projection)
    actual = payload.pop("freeze_id")
    expected = "voalfv3:freeze:" + hashlib.sha256(canonical_json_bytes_v1(payload)).hexdigest()
    if actual != expected:
        raise _error("freeze projection content identity drifted")
    return canonical_clone_v1(projection)


def _validate_reader_firewall(
    manifest: dict[str, Any], request: dict[str, Any], projection: dict[str, Any]
) -> None:
    serialized = json.dumps(
        {"manifest": manifest, "projection": projection, "request": request},
        ensure_ascii=False,
        sort_keys=True,
    ).lower()
    forbidden = (
        '"adapter',
        '"bank',
        '"family',
        '"filename',
        '"physical_page',
        '"raw_text',
        '"receipt',
        '"result_ref',
        '"source_pdf',
        '"transcript',
    )
    if any(token in serialized for token in forbidden):
        raise _error("anonymous freezer artifacts expose forbidden provenance or transcript data")


def _validate_crop_payloads(manifest: dict[str, Any], crop_payloads: tuple[bytes, ...]) -> None:
    if type(crop_payloads) is not tuple or len(crop_payloads) != EXPECTED_SAMPLE_COUNT:
        raise _error("crop-byte snapshot denominator drifted")
    for ordinal, (sample, payload) in enumerate(
        zip(manifest["samples"], crop_payloads, strict=True)
    ):
        if type(payload) is not bytes:
            raise _error(f"crop {ordinal:04d} snapshot is not immutable bytes")
        image = _png_rgb(payload, f"crop {ordinal:04d}")
        if (
            hashlib.sha256(payload).hexdigest() != sample["crop_sha256"]
            or len(payload) != sample["crop_size_bytes"]
            or image.size != (sample["crop_width"], sample["crop_height"])
        ):
            raise _error(f"crop {ordinal:04d} bytes differ from manifest identity")


def _open_directory(root: Path, relative: Path, label: str) -> int:
    path = _safe_relative(relative, label)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    current = os.open(root, flags)
    try:
        for part in path.parts:
            following = os.open(part, flags, dir_fd=current)
            os.close(current)
            current = following
        return current
    except OSError as exc:
        os.close(current)
        raise _error(f"cannot open nofollow {label} directory") from exc


def _exclusive_write_fd(parent_fd: int, name: str, payload: bytes, label: str) -> None:
    if type(name) is not str or not name or "/" in name or "\\" in name:
        raise _error(f"{label} filename is invalid")
    descriptor = os.open(
        name,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0),
        0o444,
        dir_fd=parent_fd,
    )
    try:
        view = memoryview(payload)
        offset = 0
        while offset < len(view):
            written = os.write(descriptor, view[offset:])
            if written <= 0:
                raise _error(f"short write for {label}")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    replay = os.open(
        name,
        os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
        dir_fd=parent_fd,
    )
    try:
        chunks: list[bytes] = []
        while chunk := os.read(replay, 1024 * 1024):
            chunks.append(chunk)
        if b"".join(chunks) != payload:
            raise _error(f"{label} bytes drifted after exclusive write")
    finally:
        os.close(replay)


def _rename_noreplace(source_fd: int, source_name: str, target_fd: int, target_name: str) -> None:
    """Atomically rename one dirfd-relative entry without replacing the target."""

    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise _error("atomic no-replace directory publication is unavailable")
    renameat2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    result = renameat2(
        source_fd,
        os.fsencode(source_name),
        target_fd,
        os.fsencode(target_name),
        1,
    )
    if result != 0:
        code = ctypes.get_errno()
        if code in {errno.EEXIST, errno.ENOTEMPTY}:
            raise _error("refusing to replace an existing freeze output")
        raise _error(f"atomic no-replace publication failed with errno {code}")


def _named_identity(parent_fd: int, name: str) -> tuple[int, int]:
    value = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    return value.st_dev, value.st_ino


def _delete_directory_contents(directory_fd: int, label: str) -> None:
    """Delete only regular files/directories reached through a held directory fd."""

    for name in os.listdir(directory_fd):
        before = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        identity = (before.st_dev, before.st_ino)
        if stat.S_ISDIR(before.st_mode):
            child_fd = os.open(
                name,
                os.O_RDONLY
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_DIRECTORY", 0)
                | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=directory_fd,
            )
            try:
                opened = os.fstat(child_fd)
                if (opened.st_dev, opened.st_ino) != identity:
                    raise _error(f"{label} directory inode changed before cleanup")
                _delete_directory_contents(child_fd, label)
            finally:
                os.close(child_fd)
            if _named_identity(directory_fd, name) != identity:
                raise _error(f"{label} directory inode changed during cleanup")
            os.rmdir(name, dir_fd=directory_fd)
        elif stat.S_ISREG(before.st_mode):
            file_fd = os.open(
                name,
                os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=directory_fd,
            )
            try:
                opened = os.fstat(file_fd)
                if (opened.st_dev, opened.st_ino) != identity:
                    raise _error(f"{label} file inode changed before cleanup")
            finally:
                os.close(file_fd)
            if _named_identity(directory_fd, name) != identity:
                raise _error(f"{label} file inode changed during cleanup")
            os.unlink(name, dir_fd=directory_fd)
        else:
            raise _error(f"{label} contains an unexpected filesystem object")


def _unlink_owned_tree(parent_fd: int, name: str, identity: tuple[int, int], label: str) -> bool:
    """Remove only the exact directory inode through held descriptors."""

    try:
        directory_fd = os.open(
            name,
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
    except OSError:
        return False
    try:
        opened = os.fstat(directory_fd)
        if (opened.st_dev, opened.st_ino) != identity or _named_identity(
            parent_fd, name
        ) != identity:
            return False
        _delete_directory_contents(directory_fd, label)
        if _named_identity(parent_fd, name) != identity:
            return False
        os.rmdir(name, dir_fd=parent_fd)
        os.fsync(parent_fd)
        return True
    finally:
        os.close(directory_fd)


@dataclass(frozen=True)
class _Stage:
    container_name: str
    container_fd: int
    tree_fd: int
    tree_identity: tuple[int, int]


def _stage_artifacts(
    parent_fd: int,
    manifest_payload: bytes,
    request_payload: bytes,
    crop_payloads: tuple[bytes, ...],
    manifest: dict[str, Any],
) -> _Stage:
    container_name = f".vietocr-freeze-v3-stage-{secrets.token_hex(16)}"
    os.mkdir(container_name, 0o700, dir_fd=parent_fd)
    container_identity = _named_identity(parent_fd, container_name)
    try:
        container_fd = os.open(
            container_name,
            os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
    except BaseException:
        # Nothing has been written before this descriptor opens.  Remove only
        # the empty directory inode that this call just created; if its name
        # was concurrently replaced, preserve the replacement fail-closed.
        try:
            if _named_identity(parent_fd, container_name) == container_identity:
                os.rmdir(container_name, dir_fd=parent_fd)
                os.fsync(parent_fd)
        except OSError:
            # Preserve the original descriptor-open failure. A concurrent
            # namespace change is intentionally never followed or deleted.
            pass
        raise
    tree_fd: int | None = None
    frozen_fd: int | None = None
    crops_fd: int | None = None
    try:
        os.mkdir("tree", 0o700, dir_fd=container_fd)
        tree_fd = os.open(
            "tree",
            os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=container_fd,
        )
        tree_stat = os.fstat(tree_fd)
        tree_identity = (tree_stat.st_dev, tree_stat.st_ino)
        os.mkdir("frozen", 0o755, dir_fd=tree_fd)
        frozen_fd = os.open(
            "frozen",
            os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=tree_fd,
        )
        os.mkdir("crops", 0o755, dir_fd=frozen_fd)
        crops_fd = os.open(
            "crops",
            os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=frozen_fd,
        )
        for sample, payload in zip(manifest["samples"], crop_payloads, strict=True):
            _exclusive_write_fd(
                crops_fd,
                Path(sample["crop_path"]).name,
                payload,
                f"staged crop {sample['sample_id']}",
            )
        _exclusive_write_fd(frozen_fd, _MANIFEST_NAME, manifest_payload, "crop manifest")
        _exclusive_write_fd(frozen_fd, _REQUEST_NAME, request_payload, "reader request")
        os.fsync(crops_fd)
        os.fsync(frozen_fd)
        os.fsync(tree_fd)
        os.close(crops_fd)
        crops_fd = None
        os.close(frozen_fd)
        frozen_fd = None
        os.fsync(parent_fd)
        return _Stage(container_name, container_fd, tree_fd, tree_identity)
    except BaseException:
        if crops_fd is not None:
            os.close(crops_fd)
        if frozen_fd is not None:
            os.close(frozen_fd)
        if tree_fd is not None:
            os.close(tree_fd)
        os.close(container_fd)
        identity = _named_identity(parent_fd, container_name)
        _unlink_owned_tree(parent_fd, container_name, identity, "failed stage cleanup")
        raise


def _read_fd_bytes(parent_fd: int, name: str, label: str) -> bytes:
    descriptor = os.open(
        name,
        os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
        dir_fd=parent_fd,
    )
    try:
        before = os.fstat(descriptor)
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        after = os.fstat(descriptor)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise _error(f"{label} changed during fd replay")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _verify_staged_snapshot(
    stage: _Stage,
    manifest_payload: bytes,
    request_payload: bytes,
    crop_payloads: tuple[bytes, ...],
    manifest: dict[str, Any],
) -> None:
    frozen_fd = os.open(
        "frozen",
        os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
        dir_fd=stage.tree_fd,
    )
    crops_fd = os.open(
        "crops",
        os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
        dir_fd=frozen_fd,
    )
    try:
        if _read_fd_bytes(frozen_fd, _MANIFEST_NAME, "staged manifest") != manifest_payload or (
            _read_fd_bytes(frozen_fd, _REQUEST_NAME, "staged request") != request_payload
        ):
            raise _error("staged manifest or request bytes drifted")
        crop_names = os.listdir(crops_fd)
        expected_names = [Path(sample["crop_path"]).name for sample in manifest["samples"]]
        if sorted(crop_names) != sorted(expected_names) or len(crop_names) != EXPECTED_SAMPLE_COUNT:
            raise _error("staged crop directory has missing, duplicate, or extra files")
        for sample, expected in zip(manifest["samples"], crop_payloads, strict=True):
            actual = _read_fd_bytes(
                crops_fd, Path(sample["crop_path"]).name, f"staged crop {sample['sample_id']}"
            )
            if actual != expected:
                raise _error(f"staged crop {sample['sample_id']} bytes drifted")
    finally:
        os.close(crops_fd)
        os.close(frozen_fd)


def _crop_directory_names(root: Path, output_root: Path) -> list[str]:
    directory = _open_directory(root, output_root / "frozen/crops", "published crops")
    try:
        names = os.listdir(directory)
    except OSError as exc:
        raise _error("cannot list published crop directory") from exc
    finally:
        os.close(directory)
    if any(type(name) is not str or not name or "/" in name or "\\" in name for name in names):
        raise _error("published crop directory contains a noncanonical name")
    return names


def _replay_artifacts(
    root: Path,
    output_root: Path,
    ready_capability: AuthenticatedLoanMaturity8BankReadyPanelV1,
) -> tuple[
    dict[str, Any],
    bytes,
    dict[str, Any],
    bytes,
    tuple[bytes, ...],
    dict[str, Any],
    dict[str, Any],
]:
    batch, pages = _collect_ready(ready_capability)
    manifest_relative = output_root / "frozen" / _MANIFEST_NAME
    request_relative = output_root / "frozen" / _REQUEST_NAME
    manifest_payload = _stable_nofollow_bytes(root, manifest_relative, "crop manifest")
    request_payload = _stable_nofollow_bytes(root, request_relative, "reader request")
    manifest = _validate_manifest(
        _strict_json(manifest_payload, "crop manifest"), output_root, batch["batch_id"]
    )
    git_binding = manifest["git_binding"]
    _assert_git_binding(root, git_binding, "during artifact replay")
    request = _validate_request(
        _strict_json(request_payload, "reader request"),
        manifest,
        manifest_payload,
        output_root,
    )
    (
        expected_manifest,
        expected_manifest_payload,
        expected_request,
        expected_request_payload,
        expected_crops,
    ) = _build_artifacts(
        batch=batch,
        pages=pages,
        output_root=output_root,
        git_binding=git_binding,
    )
    if (
        manifest_payload != expected_manifest_payload
        or request_payload != expected_request_payload
        or not same_typed_json_v1(manifest, expected_manifest)
        or not same_typed_json_v1(request, expected_request)
    ):
        raise _error("published manifest/request differ from live READY recomputation")
    expected_names = [Path(sample["crop_path"]).name for sample in manifest["samples"]]
    actual_names = _crop_directory_names(root, output_root)
    if sorted(actual_names) != sorted(expected_names) or len(actual_names) != EXPECTED_SAMPLE_COUNT:
        raise _error("published crop directory has missing, duplicate, or extra files")
    actual_crops: list[bytes] = []
    for sample, recomputed in zip(manifest["samples"], expected_crops, strict=True):
        actual = _stable_nofollow_bytes(root, sample["crop_path"], sample["sample_id"])
        if (
            actual != recomputed
            or hashlib.sha256(actual).hexdigest() != sample["crop_sha256"]
            or len(actual) != sample["crop_size_bytes"]
        ):
            raise _error(f"published crop {sample['sample_id']} differs from live recomputation")
        actual_crops.append(actual)
    if (
        _stable_nofollow_bytes(root, manifest_relative, "final crop manifest") != manifest_payload
        or _stable_nofollow_bytes(root, request_relative, "final reader request") != request_payload
    ):
        raise _error("published manifest/request changed during full crop replay")
    projection = _projection(output_root, manifest_payload, request_payload)
    _validate_reader_firewall(manifest, request, projection)
    _validate_crop_payloads(manifest, tuple(actual_crops))
    return (
        manifest,
        manifest_payload,
        request,
        request_payload,
        tuple(actual_crops),
        projection,
        batch,
    )


_MINT_TOKEN = object()


class AuthenticatedVietOCRAllLineFreezeV3:
    """Opaque live authority over one exact 835-crop freeze."""

    __slots__ = ("__weakref__",)

    def __init__(self, token: object) -> None:
        if token is not _MINT_TOKEN:
            raise _error("authenticated all-LINE freeze cannot be caller-constructed")

    def __copy__(self) -> None:
        raise _error("authenticated all-LINE freeze cannot be copied")

    def __deepcopy__(self, _memo: object) -> None:
        raise _error("authenticated all-LINE freeze cannot be deep-copied")

    def __reduce__(self) -> None:
        raise _error("authenticated all-LINE freeze cannot be serialized")

    def __reduce_ex__(self, _protocol: int) -> None:
        raise _error("authenticated all-LINE freeze cannot be serialized")


@dataclass(frozen=True)
class _AuthenticatedFreezeState:
    root: Path
    output_root: Path
    ready_capability: AuthenticatedLoanMaturity8BankReadyPanelV1
    ready_batch_payload: bytes
    ready_batch_digest: str
    manifest_payload: bytes
    manifest_digest: str
    request_payload: bytes
    request_digest: str
    projection_payload: bytes
    projection_digest: str
    crop_payloads: tuple[bytes, ...]
    crop_digests: tuple[str, ...]


_AUTHENTICATED_FREEZES: weakref.WeakKeyDictionary[
    AuthenticatedVietOCRAllLineFreezeV3, _AuthenticatedFreezeState
] = weakref.WeakKeyDictionary()


def _mint(
    *,
    root: Path,
    output_root: Path,
    ready_capability: AuthenticatedLoanMaturity8BankReadyPanelV1,
    ready_batch: dict[str, Any],
    manifest_payload: bytes,
    request_payload: bytes,
    projection: dict[str, Any],
    crop_payloads: tuple[bytes, ...],
) -> AuthenticatedVietOCRAllLineFreezeV3:
    ready_batch_payload = canonical_json_bytes_v1(ready_batch)
    projection_payload = canonical_json_bytes_v1(projection)
    capability = AuthenticatedVietOCRAllLineFreezeV3(_MINT_TOKEN)
    _AUTHENTICATED_FREEZES[capability] = _AuthenticatedFreezeState(
        root=root,
        output_root=output_root,
        ready_capability=ready_capability,
        ready_batch_payload=ready_batch_payload,
        ready_batch_digest=hashlib.sha256(ready_batch_payload).hexdigest(),
        manifest_payload=bytes(manifest_payload),
        manifest_digest=hashlib.sha256(manifest_payload).hexdigest(),
        request_payload=bytes(request_payload),
        request_digest=hashlib.sha256(request_payload).hexdigest(),
        projection_payload=projection_payload,
        projection_digest=hashlib.sha256(projection_payload).hexdigest(),
        crop_payloads=tuple(bytes(payload) for payload in crop_payloads),
        crop_digests=tuple(hashlib.sha256(payload).hexdigest() for payload in crop_payloads),
    )
    return capability


def _validated_state(
    capability: AuthenticatedVietOCRAllLineFreezeV3,
) -> tuple[_AuthenticatedFreezeState, dict[str, Any], dict[str, Any]]:
    if type(capability) is not AuthenticatedVietOCRAllLineFreezeV3:
        raise _error("freeze authority requires one exact live opaque capability")
    state = _AUTHENTICATED_FREEZES.get(capability)
    if state is None:
        raise _error("authenticated all-LINE freeze capability is unknown or expired")
    if (
        hashlib.sha256(state.ready_batch_payload).hexdigest() != state.ready_batch_digest
        or hashlib.sha256(state.manifest_payload).hexdigest() != state.manifest_digest
        or hashlib.sha256(state.request_payload).hexdigest() != state.request_digest
        or hashlib.sha256(state.projection_payload).hexdigest() != state.projection_digest
        or len(state.crop_payloads) != EXPECTED_SAMPLE_COUNT
        or tuple(hashlib.sha256(payload).hexdigest() for payload in state.crop_payloads)
        != state.crop_digests
    ):
        raise _error("authenticated all-LINE freeze in-memory bytes drifted")
    try:
        stored_batch = cast(
            dict[str, Any], decode_canonical_json_bytes_v1(state.ready_batch_payload)
        )
        stored_projection = _validate_projection(
            decode_canonical_json_bytes_v1(state.projection_payload), state.output_root
        )
    except (TypeError, ValueError) as exc:
        raise _error("authenticated freeze canonical bytes cannot be decoded") from exc
    manifest = _validate_manifest(
        _strict_json(state.manifest_payload, "authenticated manifest snapshot"),
        state.output_root,
        stored_batch["batch_id"],
    )
    request = _validate_request(
        _strict_json(state.request_payload, "authenticated request snapshot"),
        manifest,
        state.manifest_payload,
        state.output_root,
    )
    _assert_git_binding(state.root, manifest["git_binding"], "before crop snapshot access")
    live_batch, live_pages = _collect_ready(state.ready_capability)
    if not same_typed_json_v1(live_batch, stored_batch):
        raise _error("live READY-panel batch changed after freeze")
    (
        recomputed_manifest,
        recomputed_manifest_payload,
        recomputed_request,
        recomputed_request_payload,
        recomputed_crops,
    ) = _build_artifacts(
        batch=live_batch,
        pages=live_pages,
        output_root=state.output_root,
        git_binding=manifest["git_binding"],
    )
    if (
        state.manifest_payload != recomputed_manifest_payload
        or state.request_payload != recomputed_request_payload
        or state.crop_payloads != recomputed_crops
        or not same_typed_json_v1(manifest, recomputed_manifest)
        or not same_typed_json_v1(request, recomputed_request)
        or not same_typed_json_v1(
            stored_projection,
            _projection(state.output_root, state.manifest_payload, state.request_payload),
        )
    ):
        raise _error("authenticated freeze differs from live READY pixel recomputation")
    _validate_crop_payloads(manifest, state.crop_payloads)
    _validate_reader_firewall(manifest, request, stored_projection)
    return state, stored_projection, manifest


def assert_authenticated_vietocr_all_line_freeze_project_root_v3(
    project_root: Path,
    capability: AuthenticatedVietOCRAllLineFreezeV3,
) -> None:
    """Require a live freeze capability to belong to this exact Git root."""

    root = _resolve_root(project_root)
    state, _projection, _manifest = _validated_state(capability)
    if state.root != root:
        raise _error("authenticated freeze capability belongs to another project root")


def freeze_authenticated_vietocr_all_line_batch_v3(
    project_root: Path,
    output_root: Path,
    ready_capability: AuthenticatedLoanMaturity8BankReadyPanelV1,
) -> tuple[dict[str, Any], AuthenticatedVietOCRAllLineFreezeV3]:
    """Build and atomically publish one exact anonymous 835-crop batch."""

    root = _resolve_root(project_root)
    output_relative = _validate_output_parent(root, output_root)
    destination = root / output_relative
    if os.path.lexists(destination):
        raise _error("refusing to replace an existing freeze output")
    git_binding = _clean_git_binding(root)
    batch, pages = _collect_ready(ready_capability)
    manifest, manifest_payload, request, request_payload, crop_payloads = _build_artifacts(
        batch=batch,
        pages=pages,
        output_root=output_relative,
        git_binding=git_binding,
    )
    projection = _projection(output_relative, manifest_payload, request_payload)
    _validate_crop_payloads(manifest, crop_payloads)
    _validate_reader_firewall(manifest, request, projection)

    stage: _Stage | None = None
    published_identity: tuple[int, int] | None = None
    parent_fd = _open_directory(root, output_relative.parent, "freeze output parent")
    try:
        stage = _stage_artifacts(
            parent_fd,
            manifest_payload,
            request_payload,
            crop_payloads,
            manifest,
        )
        _verify_staged_snapshot(
            stage,
            manifest_payload,
            request_payload,
            crop_payloads,
            manifest,
        )
        _assert_git_binding(root, git_binding, "before atomic publication")
        _rename_noreplace(stage.container_fd, "tree", parent_fd, destination.name)
        # The rename succeeded: rollback now owns only the originally captured inode.
        published_identity = stage.tree_identity
        published = os.stat(destination.name, dir_fd=parent_fd, follow_symlinks=False)
        if (published.st_dev, published.st_ino) != stage.tree_identity:
            raise _error("published freeze inode differs from staged authority")
        os.close(stage.tree_fd)
        os.close(stage.container_fd)
        os.rmdir(stage.container_name, dir_fd=parent_fd)
        stage = None
        os.fsync(parent_fd)
        _assert_git_binding(root, git_binding, "after atomic publication")
        (
            replayed_manifest,
            replayed_manifest_payload,
            replayed_request,
            replayed_request_payload,
            replayed_crops,
            replayed_projection,
            replayed_batch,
        ) = _replay_artifacts(root, output_relative, ready_capability)
        if (
            replayed_manifest_payload != manifest_payload
            or replayed_request_payload != request_payload
            or replayed_crops != crop_payloads
            or not same_typed_json_v1(replayed_manifest, manifest)
            or not same_typed_json_v1(replayed_request, request)
            or not same_typed_json_v1(replayed_projection, projection)
            or not same_typed_json_v1(replayed_batch, batch)
        ):
            raise _error("published freeze differs from its pre-publication snapshot")
        _assert_git_binding(root, git_binding, "immediately before authority mint")
        capability = _mint(
            root=root,
            output_root=output_relative,
            ready_capability=ready_capability,
            ready_batch=batch,
            manifest_payload=manifest_payload,
            request_payload=request_payload,
            projection=projection,
            crop_payloads=crop_payloads,
        )
        _validated_state(capability)
        return canonical_clone_v1(projection), capability
    except BaseException:
        if published_identity is not None:
            _unlink_owned_tree(
                parent_fd, destination.name, published_identity, "published freeze cleanup"
            )
        raise
    finally:
        if stage is not None:
            os.close(stage.tree_fd)
            os.close(stage.container_fd)
            identity = _named_identity(parent_fd, stage.container_name)
            _unlink_owned_tree(parent_fd, stage.container_name, identity, "staged freeze cleanup")
        os.close(parent_fd)


def replay_authenticated_vietocr_all_line_freeze_v3(
    project_root: Path,
    output_root: Path,
    ready_capability: AuthenticatedLoanMaturity8BankReadyPanelV1,
) -> tuple[dict[str, Any], AuthenticatedVietOCRAllLineFreezeV3]:
    """Replay every artifact and recompute every crop from the live READY panel."""

    root = _resolve_root(project_root)
    output_relative = _validate_output_parent(root, output_root)
    (
        manifest,
        manifest_payload,
        _request,
        request_payload,
        crop_payloads,
        projection,
        batch,
    ) = _replay_artifacts(root, output_relative, ready_capability)
    git_binding = manifest["git_binding"]
    _assert_git_binding(root, git_binding, "immediately before replay authority mint")
    capability = _mint(
        root=root,
        output_root=output_relative,
        ready_capability=ready_capability,
        ready_batch=batch,
        manifest_payload=manifest_payload,
        request_payload=request_payload,
        projection=projection,
        crop_payloads=crop_payloads,
    )
    _validated_state(capability)
    return canonical_clone_v1(projection), capability


def project_authenticated_vietocr_all_line_freeze_v3(
    capability: AuthenticatedVietOCRAllLineFreezeV3,
) -> dict[str, Any]:
    """Project exact artifact refs after live and on-disk replay."""

    state, projection, _manifest = _validated_state(capability)
    replayed = _replay_artifacts(state.root, state.output_root, state.ready_capability)
    if (
        replayed[1] != state.manifest_payload
        or replayed[3] != state.request_payload
        or replayed[4] != state.crop_payloads
        or not same_typed_json_v1(replayed[5], projection)
    ):
        raise _error("published freeze drifted from its authenticated snapshots")
    return canonical_clone_v1(projection)


def validate_authenticated_vietocr_all_line_freeze_projection_v3(
    value: Any,
    capability: AuthenticatedVietOCRAllLineFreezeV3,
) -> dict[str, Any]:
    """Bind a descriptive projection to the exact live freeze capability."""

    state, _projection_value, _manifest = _validated_state(capability)
    candidate = _validate_projection(value, state.output_root)
    expected = project_authenticated_vietocr_all_line_freeze_v3(capability)
    if not same_typed_json_v1(candidate, expected):
        raise _error("freeze projection differs from its live capability")
    return candidate


def read_authenticated_vietocr_all_line_crop_v3(
    capability: AuthenticatedVietOCRAllLineFreezeV3,
    crop_ordinal: int,
) -> bytes:
    """Return immutable capability-held crop bytes; never reopen the crop path."""

    if type(crop_ordinal) is not int or not 1 <= crop_ordinal <= EXPECTED_SAMPLE_COUNT:
        raise _error("crop ordinal must be one integer from 1 through 835")
    state, _projection_value, _manifest = _validated_state(capability)
    payload = state.crop_payloads[crop_ordinal - 1]
    if (
        type(payload) is not bytes
        or hashlib.sha256(payload).hexdigest() != state.crop_digests[crop_ordinal - 1]
    ):
        raise _error("authenticated crop snapshot bytes drifted")
    return bytes(payload)


def read_authenticated_vietocr_all_line_batch_v3(
    capability: AuthenticatedVietOCRAllLineFreezeV3,
) -> tuple[dict[str, Any], ...]:
    """Validate once, then return all ordered immutable crops to the reader."""

    state, _projection_value, manifest = _validated_state(capability)
    samples: list[dict[str, Any]] = []
    for sample, payload, digest in zip(
        manifest["samples"], state.crop_payloads, state.crop_digests, strict=True
    ):
        if type(payload) is not bytes or hashlib.sha256(payload).hexdigest() != digest:
            raise _error("authenticated crop batch snapshot bytes drifted")
        samples.append(
            {
                "crop_png_bytes": bytes(payload),
                "crop_sha256": sample["crop_sha256"],
                "page_id": sample["page_id"],
                "sample_id": sample["sample_id"],
            }
        )
    if len(samples) != EXPECTED_SAMPLE_COUNT:
        raise _error("authenticated crop batch denominator drifted")
    return tuple(samples)


def read_authenticated_vietocr_all_line_snapshot_v3(
    capability: AuthenticatedVietOCRAllLineFreezeV3,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    """Return one atomic projection-and-byte snapshot for the formal reader."""

    state, projection, manifest = _validated_state(capability)
    samples: list[dict[str, Any]] = []
    for sample, payload, digest in zip(
        manifest["samples"], state.crop_payloads, state.crop_digests, strict=True
    ):
        if type(payload) is not bytes or hashlib.sha256(payload).hexdigest() != digest:
            raise _error("authenticated reader snapshot crop bytes drifted")
        samples.append(
            {
                "crop_png_bytes": bytes(payload),
                "crop_sha256": sample["crop_sha256"],
                "page_id": sample["page_id"],
                "sample_id": sample["sample_id"],
            }
        )
    if len(samples) != EXPECTED_SAMPLE_COUNT:
        raise _error("authenticated reader snapshot denominator drifted")
    return canonical_clone_v1(projection), tuple(samples)
