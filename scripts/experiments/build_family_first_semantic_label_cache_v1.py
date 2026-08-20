#!/usr/bin/env python3
"""Build the text-blind all-filing detector/crop cache for family-first OCR.

The fixed plan authenticates 140 filings and 8,947 pages.  Each document is
rendered from one immutable PDF byte snapshot, passed to the pinned PP-OCRv6
detector as an in-memory RGB array, and published atomically only after every
detected line has been deterministically cropped.  Existing recognition text
is never read.  A later reference-blind VietOCR runner consumes the batch;
numeric crops are separately reread by the pinned PP-OCRv6 recognizer.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import importlib.metadata
import io
import json
import os
import re
import shutil
import socket
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any

import fitz
import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT / "src"))

from bctc_ai.evaluation.family_first_semantic_label_freeze_v1 import (  # noqa: E402
    build_family_first_semantic_label_page_freeze_v1,
    validate_family_first_semantic_label_page_freeze_replay_v1,
)
from bctc_ai.evaluation.family_first_semantic_label_plan_v1 import (  # noqa: E402
    build_family_first_semantic_label_plan_v1,
    validate_family_first_semantic_label_plan_replay_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

OUTPUT_ROOT = Path("output/calibration/family-first-semantic-label-cache-v1")
PLAN_PATH = OUTPUT_ROOT / "plan.json"
DOCUMENT_ROOT = OUTPUT_ROOT / "documents"
READER_BATCH_PATH = OUTPUT_ROOT / "semantic-reader-batch.json"
PRIVATE_INDEX_PATH = OUTPUT_ROOT / "private-source-index.json"
_PAGE_FORMAT = "FAMILY_FIRST_SEMANTIC_LABEL_CACHE_PAGE_ARTIFACT_V1"
_DOCUMENT_FORMAT = "FAMILY_FIRST_SEMANTIC_LABEL_CACHE_DOCUMENT_ARTIFACT_V1"
_BATCH_FORMAT = "FAMILY_FIRST_SEMANTIC_LABEL_READER_BATCH_V1"
_INDEX_FORMAT = "FAMILY_FIRST_SEMANTIC_LABEL_PRIVATE_SOURCE_INDEX_V1"
_PAGE_FIELDS = {
    "artifact_id",
    "authority",
    "detector_payload",
    "document_ordinal",
    "format_version",
    "page_freeze",
    "physical_page",
    "plan_id",
}
_DOCUMENT_FIELDS = {
    "artifact_id",
    "authority",
    "document_ordinal",
    "format_version",
    "metrics",
    "page_artifact_refs",
    "plan_id",
    "source_pdf_ref",
}
_PAGE_AUTHORITY = {
    "all_detected_lines_retained": True,
    "detector_recognition_text_accessed": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "semantic_authority": False,
}
_DOCUMENT_AUTHORITY = {
    "all_pages_retained": True,
    "all_detected_lines_retained": True,
    "bank_period_scope_used_for_detection_or_line_selection": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "semantic_authority": False,
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_AT_FDCWD = -100
_RENAME_NOREPLACE = 1


class FamilyFirstSemanticLabelCacheV1Error(RuntimeError):
    """A plan, PDF, render, detector output, crop, or publication drifted."""


def _error(message: str) -> FamilyFirstSemanticLabelCacheV1Error:
    return FamilyFirstSemanticLabelCacheV1Error(message)


def _canonical_bytes(value: Any) -> bytes:
    return canonical_json_bytes_v1(value) + b"\n"


def _stable_bytes(path: Path, label: str) -> bytes:
    before = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise _error(f"{label} must be one single-link regular file")
    payload = path.read_bytes()
    after = path.stat(follow_symlinks=False)
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ) or len(payload) != before.st_size:
        raise _error(f"{label} changed while being read")
    return payload


def _strict_canonical_json(path: Path, label: str) -> dict[str, Any]:
    payload = _stable_bytes(path, label)
    return _decode_canonical_json(payload, label)


def _decode_canonical_json(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"{label} is not strict JSON") from exc
    if type(value) is not dict or payload != _canonical_bytes(value):
        raise _error(f"{label} is not one canonical JSON object")
    return value


def _write_exclusive(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o444)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise _error("exclusive artifact write made no progress")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _rename_noreplace(source: Path, destination: Path) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise _error("renameat2 is required for no-replace publication")
    renameat2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    result = renameat2(
        _AT_FDCWD,
        os.fsencode(source),
        _AT_FDCWD,
        os.fsencode(destination),
        _RENAME_NOREPLACE,
    )
    if result != 0:
        error_number = ctypes.get_errno()
        if error_number == errno.EEXIST:
            raise _error(f"artifact destination already exists: {destination}")
        raise OSError(error_number, os.strerror(error_number), destination)


def _content_ref(path: Path, payload: bytes) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _validate_ref(value: Any, label: str) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != {"path", "sha256", "size_bytes"}
        or type(value["path"]) is not str
        or not value["path"]
        or type(value["sha256"]) is not str
        or _SHA256.fullmatch(value["sha256"]) is None
        or type(value["size_bytes"]) is not int
        or value["size_bytes"] <= 0
    ):
        raise _error(f"{label} content reference drifted")
    return value


def _read_plan(model_cache: Path) -> dict[str, Any]:
    plan = _strict_canonical_json(PROJECT_ROOT / PLAN_PATH, "family-first detector plan")
    return validate_family_first_semantic_label_plan_replay_v1(
        plan,
        PROJECT_ROOT,
        model_cache=model_cache,
    )


def prepare_family_first_semantic_label_cache_v1(*, model_cache: Path) -> dict[str, Any]:
    """Create the fixed plan root once; no detector inference is performed."""

    plan = build_family_first_semantic_label_plan_v1(PROJECT_ROOT, model_cache=model_cache)
    destination = PROJECT_ROOT / OUTPUT_ROOT
    if destination.exists() or destination.is_symlink():
        raise _error("fixed family-first cache root already exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage: Path | None = Path(
        tempfile.mkdtemp(prefix=".family-first-label-plan-", dir=destination.parent)
    )
    try:
        assert stage is not None
        (stage / "documents").mkdir(mode=0o755)
        _write_exclusive(stage / "plan.json", _canonical_bytes(plan))
        _fsync_directory(stage / "documents")
        _fsync_directory(stage)
        _rename_noreplace(stage, destination)
        stage = None
        _fsync_directory(destination.parent)
    finally:
        if stage is not None and stage.exists():
            shutil.rmtree(stage)
    return plan


def _document(plan: dict[str, Any], ordinal: int) -> dict[str, Any]:
    if type(ordinal) is not int or not 1 <= ordinal <= len(plan["documents"]):
        raise _error("document ordinal lies outside the plan")
    document = plan["documents"][ordinal - 1]
    if document["document_ordinal"] != ordinal:
        raise _error("document plan order drifted")
    return document


def _source_bytes(document: dict[str, Any]) -> bytes:
    source_ref = _validate_ref(document["source_pdf_ref"], "source PDF")
    relative = Path(source_ref["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise _error("source PDF reference escapes the project root")
    payload = _stable_bytes(PROJECT_ROOT / relative, "source PDF")
    if (
        len(payload) != source_ref["size_bytes"]
        or hashlib.sha256(payload).hexdigest() != source_ref["sha256"]
    ):
        raise _error("source PDF differs from the family-first plan")
    return payload


def _render(page: fitz.Page, dpi: int) -> bytes:
    scale = dpi / 72
    pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False)
    payload = pixmap.tobytes("png")
    if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        raise _error("PyMuPDF did not produce a PNG page render")
    return payload


def _detector_payload(detector: Any, render_png_bytes: bytes) -> dict[str, Any]:
    with Image.open(io.BytesIO(render_png_bytes)) as raw:
        raw.load()
        image = np.asarray(raw.convert("RGB"))
    results = detector.predict(image, batch_size=1)
    if type(results) is not list or len(results) != 1:
        raise _error("PP-OCRv6 detector did not return exactly one page")
    wrapped = results[0].json
    if type(wrapped) is not dict or set(wrapped) != {"res"} or type(wrapped["res"]) is not dict:
        raise _error("PP-OCRv6 detector result wrapper drifted")
    return wrapped["res"]


def _page_artifact(
    *,
    plan_id: str,
    document_ordinal: int,
    physical_page: int,
    detector_payload: dict[str, Any],
    page_freeze: dict[str, Any],
) -> dict[str, Any]:
    material = {
        "authority": dict(_PAGE_AUTHORITY),
        "detector_payload": detector_payload,
        "document_ordinal": document_ordinal,
        "format_version": _PAGE_FORMAT,
        "page_freeze": page_freeze,
        "physical_page": physical_page,
        "plan_id": plan_id,
    }
    return {**material, "artifact_id": "ffslcv1:page:" + canonical_json_sha256_v1(material)}


def _validate_page_artifact(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _PAGE_FIELDS
        or value["format_version"] != _PAGE_FORMAT
        or not same_typed_json_v1(value["authority"], _PAGE_AUTHORITY)
        or type(value["document_ordinal"]) is not int
        or value["document_ordinal"] <= 0
        or type(value["physical_page"]) is not int
        or value["physical_page"] <= 0
    ):
        raise _error("semantic-label page artifact fields drifted")
    material = dict(value)
    artifact_id = material.pop("artifact_id")
    if artifact_id != "ffslcv1:page:" + canonical_json_sha256_v1(material):
        raise _error("semantic-label page artifact hash identity drifted")
    return value


def _document_artifact(
    plan: dict[str, Any], document: dict[str, Any], page_refs: list[dict[str, Any]], line_count: int
) -> dict[str, Any]:
    material = {
        "authority": dict(_DOCUMENT_AUTHORITY),
        "document_ordinal": document["document_ordinal"],
        "format_version": _DOCUMENT_FORMAT,
        "metrics": {
            "crop_count": line_count,
            "detected_line_count": line_count,
            "excluded_detected_line_count": 0,
            "page_count": len(page_refs),
        },
        "page_artifact_refs": page_refs,
        "plan_id": plan["plan_id"],
        "source_pdf_ref": document["source_pdf_ref"],
    }
    return {**material, "artifact_id": "ffslcv1:document:" + canonical_json_sha256_v1(material)}


def _validate_document_artifact(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _DOCUMENT_FIELDS
        or value["format_version"] != _DOCUMENT_FORMAT
        or not same_typed_json_v1(value["authority"], _DOCUMENT_AUTHORITY)
        or type(value["page_artifact_refs"]) is not list
    ):
        raise _error("semantic-label document artifact fields drifted")
    material = dict(value)
    artifact_id = material.pop("artifact_id")
    if artifact_id != "ffslcv1:document:" + canonical_json_sha256_v1(material):
        raise _error("semantic-label document artifact hash identity drifted")
    return value


def _model_directory(plan: dict[str, Any], model_cache: Path) -> Path:
    model = plan["detector"]
    directory = model_cache.resolve() / "official_models" / model["cache_directory"]
    for expected in model["required_files"]:
        path = directory / Path(expected["path"]).name
        payload = _stable_bytes(path, "detector executable file")
        if (
            len(payload) != expected["size_bytes"]
            or hashlib.sha256(payload).hexdigest() != expected["sha256"]
        ):
            raise _error("detector executable file drifted after plan replay")
    return directory


def _load_detector(plan: dict[str, Any], model_cache: Path) -> Any:
    if (
        importlib.metadata.version("paddlepaddle") != "3.3.0"
        or importlib.metadata.version("paddleocr") != "3.7.0"
        or importlib.metadata.version("pymupdf") != "1.28.0"
    ):
        raise _error("family-first detector package runtime drifted")
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

    def denied(*_args: Any, **_kwargs: Any) -> Any:
        raise _error("network access is forbidden during family-first detector inference")

    socket.socket.connect = denied  # type: ignore[method-assign]
    socket.create_connection = denied  # type: ignore[assignment]
    from paddleocr import TextDetection

    return TextDetection(
        model_dir=os.fspath(_model_directory(plan, model_cache)),
        device="cpu",
        enable_mkldnn=False,
    )


def _build_document_stage(
    *,
    plan: dict[str, Any],
    document: dict[str, Any],
    pdf_bytes: bytes,
    detector: Any,
    stage: Path,
) -> dict[str, Any]:
    ordinal = document["document_ordinal"]
    page_refs = []
    total_lines = 0
    with fitz.open(stream=pdf_bytes, filetype="pdf") as source:
        if source.page_count != document["page_count"]:
            raise _error("source PDF page denominator drifted before detection")
        for page_index in range(source.page_count):
            physical_page = page_index + 1
            page_directory = stage / f"page-{physical_page:04d}"
            crop_directory = page_directory / "crops"
            crop_directory.mkdir(parents=True, mode=0o755)
            render = _render(source[page_index], plan["render_policy"]["dpi"])
            provider = _detector_payload(detector, render)
            final_prefix = (
                OUTPUT_ROOT
                / "documents"
                / f"document-{ordinal:04d}"
                / f"page-{physical_page:04d}"
                / "crops"
            ).as_posix()
            page_freeze, crops = build_family_first_semantic_label_page_freeze_v1(
                render_png_bytes=render,
                detector_payload=provider,
                physical_page=physical_page,
                crop_path_prefix=final_prefix,
            )
            for line_ordinal, crop in enumerate(crops):
                _write_exclusive(crop_directory / f"line-{line_ordinal:04d}.png", crop)
            page_artifact = _validate_page_artifact(
                _page_artifact(
                    plan_id=plan["plan_id"],
                    document_ordinal=ordinal,
                    physical_page=physical_page,
                    detector_payload=provider,
                    page_freeze=page_freeze,
                )
            )
            page_bytes = _canonical_bytes(page_artifact)
            page_path = page_directory / "page.json"
            _write_exclusive(page_path, page_bytes)
            page_refs.append(
                _content_ref(
                    OUTPUT_ROOT
                    / "documents"
                    / f"document-{ordinal:04d}"
                    / f"page-{physical_page:04d}"
                    / "page.json",
                    page_bytes,
                )
            )
            total_lines += len(crops)
            _fsync_directory(crop_directory)
            _fsync_directory(page_directory)
    document_artifact = _validate_document_artifact(
        _document_artifact(plan, document, page_refs, total_lines)
    )
    _write_exclusive(stage / "document.json", _canonical_bytes(document_artifact))
    _fsync_directory(stage)
    return document_artifact


def run_family_first_semantic_label_document_v1(
    *, model_cache: Path, document_ordinal: int, detector: Any | None = None
) -> dict[str, Any]:
    """Run and atomically publish exactly one planned document."""

    plan = _read_plan(model_cache)
    document = _document(plan, document_ordinal)
    destination = PROJECT_ROOT / DOCUMENT_ROOT / f"document-{document_ordinal:04d}"
    if destination.exists() or destination.is_symlink():
        return verify_family_first_semantic_label_document_v1(
            model_cache=model_cache,
            document_ordinal=document_ordinal,
            replay_detector=False,
            detector=detector,
        )
    pdf_bytes = _source_bytes(document)
    worker = detector if detector is not None else _load_detector(plan, model_cache)
    stage: Path | None = Path(
        tempfile.mkdtemp(
            prefix=f".document-{document_ordinal:04d}-",
            dir=PROJECT_ROOT / DOCUMENT_ROOT,
        )
    )
    stage_identity = stage.stat(follow_symlinks=False)
    try:
        assert stage is not None
        artifact = _build_document_stage(
            plan=plan,
            document=document,
            pdf_bytes=pdf_bytes,
            detector=worker,
            stage=stage,
        )
        validate_family_first_semantic_label_plan_replay_v1(
            plan,
            PROJECT_ROOT,
            model_cache=model_cache,
        )
        current = stage.stat(follow_symlinks=False)
        if (current.st_dev, current.st_ino) != (stage_identity.st_dev, stage_identity.st_ino):
            raise _error("owned document stage identity changed before publication")
        _rename_noreplace(stage, destination)
        stage = None
        _fsync_directory(destination.parent)
        return artifact
    finally:
        if stage is not None and stage.exists():
            current = stage.stat(follow_symlinks=False)
            if (current.st_dev, current.st_ino) == (stage_identity.st_dev, stage_identity.st_ino):
                shutil.rmtree(stage)


def verify_family_first_semantic_label_document_v1(
    *,
    model_cache: Path,
    document_ordinal: int,
    replay_detector: bool,
    detector: Any | None = None,
) -> dict[str, Any]:
    """Replay PDF renders/crops, and optionally rerun every detector page."""

    plan = _read_plan(model_cache)
    document = _document(plan, document_ordinal)
    root = PROJECT_ROOT / DOCUMENT_ROOT / f"document-{document_ordinal:04d}"
    persisted = _validate_document_artifact(
        _strict_canonical_json(root / "document.json", "semantic-label document artifact")
    )
    if (
        persisted["plan_id"] != plan["plan_id"]
        or persisted["document_ordinal"] != document_ordinal
        or not same_typed_json_v1(persisted["source_pdf_ref"], document["source_pdf_ref"])
        or len(persisted["page_artifact_refs"]) != document["page_count"]
    ):
        raise _error("semantic-label document does not belong to the live plan")
    pdf_bytes = _source_bytes(document)
    worker = (
        detector
        if detector is not None
        else (_load_detector(plan, model_cache) if replay_detector else None)
    )
    rebuilt_refs = []
    total_lines = 0
    with fitz.open(stream=pdf_bytes, filetype="pdf") as source:
        for page_index in range(source.page_count):
            physical_page = page_index + 1
            page_root = root / f"page-{physical_page:04d}"
            page_path = page_root / "page.json"
            page_bytes = _stable_bytes(page_path, "semantic-label page artifact")
            page_artifact = _validate_page_artifact(
                _decode_canonical_json(page_bytes, "semantic-label page artifact")
            )
            if (
                page_artifact["plan_id"] != plan["plan_id"]
                or page_artifact["document_ordinal"] != document_ordinal
                or page_artifact["physical_page"] != physical_page
            ):
                raise _error("semantic-label page does not belong to its document")
            render = _render(source[page_index], plan["render_policy"]["dpi"])
            crop_bytes = tuple(
                _stable_bytes(
                    page_root / "crops" / f"line-{line['line_ordinal']:04d}.png", "line crop"
                )
                for line in page_artifact["page_freeze"]["detector_line_axis"]
            )
            final_prefix = (
                OUTPUT_ROOT
                / "documents"
                / f"document-{document_ordinal:04d}"
                / f"page-{physical_page:04d}"
                / "crops"
            ).as_posix()
            validate_family_first_semantic_label_page_freeze_replay_v1(
                page_artifact["page_freeze"],
                crop_bytes,
                render_png_bytes=render,
                detector_payload=page_artifact["detector_payload"],
                physical_page=physical_page,
                crop_path_prefix=final_prefix,
            )
            if replay_detector:
                live_provider = _detector_payload(worker, render)
                if not same_typed_json_v1(live_provider, page_artifact["detector_payload"]):
                    raise _error("live PP-OCRv6 detector replay drifted")
            rebuilt_refs.append(
                _content_ref(
                    OUTPUT_ROOT
                    / "documents"
                    / f"document-{document_ordinal:04d}"
                    / f"page-{physical_page:04d}"
                    / "page.json",
                    page_bytes,
                )
            )
            total_lines += len(crop_bytes)
    expected = _document_artifact(plan, document, rebuilt_refs, total_lines)
    if not same_typed_json_v1(persisted, expected):
        raise _error("semantic-label document artifact does not replay exactly")
    return persisted


def build_family_first_semantic_reader_batch_v1(*, model_cache: Path) -> dict[str, Any]:
    """Join every verified crop into one reference-blind ordered reader batch."""

    plan = _read_plan(model_cache)
    if (PROJECT_ROOT / READER_BATCH_PATH).exists() or (PROJECT_ROOT / PRIVATE_INDEX_PATH).exists():
        raise _error("fixed semantic reader batch or private index already exists")
    samples = []
    private_samples = []
    sample_ordinal = 0
    for document in plan["documents"]:
        ordinal = document["document_ordinal"]
        verify_family_first_semantic_label_document_v1(
            model_cache=model_cache,
            document_ordinal=ordinal,
            replay_detector=False,
        )
        document_root = PROJECT_ROOT / DOCUMENT_ROOT / f"document-{ordinal:04d}"
        for physical_page in range(1, document["page_count"] + 1):
            page = _strict_canonical_json(
                document_root / f"page-{physical_page:04d}" / "page.json",
                "semantic-label page artifact",
            )
            for crop in page["page_freeze"]["crops"]:
                sample_ordinal += 1
                sample_id = f"sample-{sample_ordinal:09d}"
                samples.append({"crop_ref": crop["crop_ref"], "sample_id": sample_id})
                private_samples.append(
                    {
                        "document_ordinal": ordinal,
                        "line_ordinal": crop["line_ordinal"],
                        "physical_page": physical_page,
                        "sample_id": sample_id,
                        "source_bbox_raw_pixels": crop["source_bbox_raw_pixels"],
                    }
                )
    batch_material = {
        "authority": {
            "bank_page_period_path_available_to_reader": False,
            "mapping_authority": False,
            "numeric_authority": False,
            "reference_text_available_to_reader": False,
            "semantic_reader_input_only": True,
        },
        "format_version": _BATCH_FORMAT,
        "plan_id": plan["plan_id"],
        "sample_count": len(samples),
        "samples": samples,
    }
    batch = {
        **batch_material,
        "batch_id": "ffslcv1:batch:" + canonical_json_sha256_v1(batch_material),
    }
    index_material = {
        "authority": {
            "private_provenance_only": True,
            "reader_access": False,
        },
        "batch_id": batch["batch_id"],
        "documents": plan["documents"],
        "format_version": _INDEX_FORMAT,
        "plan_id": plan["plan_id"],
        "sample_count": len(private_samples),
        "samples": private_samples,
    }
    index = {
        **index_material,
        "index_id": "ffslcv1:index:" + canonical_json_sha256_v1(index_material),
    }
    _write_exclusive(PROJECT_ROOT / READER_BATCH_PATH, _canonical_bytes(batch))
    _write_exclusive(PROJECT_ROOT / PRIVATE_INDEX_PATH, _canonical_bytes(index))
    _fsync_directory(PROJECT_ROOT / OUTPUT_ROOT)
    return batch


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-cache", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("prepare")
    run = subparsers.add_parser("run-document")
    run.add_argument("--document-ordinal", type=int, required=True)
    verify = subparsers.add_parser("verify-document")
    verify.add_argument("--document-ordinal", type=int, required=True)
    verify.add_argument("--replay-detector", action="store_true")
    subparsers.add_parser("build-batch")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "prepare":
        result = prepare_family_first_semantic_label_cache_v1(model_cache=args.model_cache)
    elif args.command == "run-document":
        result = run_family_first_semantic_label_document_v1(
            model_cache=args.model_cache,
            document_ordinal=args.document_ordinal,
        )
    elif args.command == "verify-document":
        result = verify_family_first_semantic_label_document_v1(
            model_cache=args.model_cache,
            document_ordinal=args.document_ordinal,
            replay_detector=args.replay_detector,
        )
    else:
        result = build_family_first_semantic_reader_batch_v1(model_cache=args.model_cache)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
