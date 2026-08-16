#!/usr/bin/env python3
"""Freeze every authenticated line in the eight selected PDFs for VietOCR.

This builder is deliberately text-blind.  Existing OCR/native transcripts are
never inspected to select a page or line.  Every authenticated LINE geometry
in every selected document is cropped.  Native pages are deterministically
rendered at 200 dpi; terminal PP-OCR pages retain their terminal status while
their full raw line-box denominator is cropped with word subdivisions ignored.

The reader request contains only opaque sample identities and crop hashes.  A
separate manifest retains source provenance for post-run whole-document graph
replay.  Neither artifact grants numeric, schema, or mapping authority.
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
import tomllib
from pathlib import Path
from typing import Any, cast

from PIL import Image, ImageOps

from bctc_ai.corpus import wave1_role_b_full_reader_v3 as full_v3
from bctc_ai.evaluation.authenticated_line_pixel_hydration_v1 import (
    project_authenticated_line_pixel_hydration_receipt_v1,
    read_authenticated_line_pixel_hydration_envelope_v1,
    read_authenticated_line_pixel_hydration_render_v1,
    replay_authenticated_line_pixel_hydration_v1,
    validate_authenticated_line_pixel_hydration_envelope_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.source_structure.evidence_projection_v2 import (
    SourceEvidenceProjectionV2Error,
    project_authenticated_page_v2,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
E0044_PATH = Path("docs/experiments/E-0044-loan-maturity-8bank-vietocr-panel-prerequisite.json")
V3_ROOT = Path("output/development/bank-corpus-wave-1-role-b-page-reader-v1/full-v3")
SEALED_PLAN_PATH = Path(
    "output/development/bank-corpus-wave-1-role-b-page-reader-v1/wave-1-role-b-page-read-plan.json"
)
OUTPUT_ROOT = Path("output/development/loan-maturity-full-document-vietocr-v1")
VIETOCR_OUTPUT_DIRECTORY = OUTPUT_ROOT / "vietocr-transformer"
VERIFIED_INDEX_DIRECTORY = OUTPUT_ROOT / "verified-index"
VIETOCR_CONFIG_PATH = Path("config/models/vietocr-0.3.13-rtx4090.toml")
VIETOCR_READER_PATH = Path("src/bctc_ai/ocr/vietocr_line_reader.py")
VIETOCR_RUNNER_PATH = Path("scripts/models/run_vietocr_line_reader.py")
ANNUAL_2025_PREPROCESS_ROOT = Path("output/calibration/annual-2025-8bank-vietocr-v1")
ANNUAL_2025_PPOCR_ROOT = Path("output/calibration/annual-2025-8bank-ppocrv6-v1")
ANNUAL_2025_OUTPUT_ROOT = Path("output/calibration/annual-2025-8bank-full-document-vietocr-v1")
ANNUAL_2025_GEOMETRY_SELECTION_PATH = Path(
    "docs/experiments/E-0106-annual-2025-8bank-ppocrv6-geometry-selection-v1.json"
)
ANNUAL_2025_SOURCES = (
    {
        "bank_code": "ACB",
        "page_count": 100,
        "relative_path": "vietstock_bctc/ACB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf",
        "sha256": "2f79c3db9e362eee72fcdfca330359e9d9cbf510fd5fe6cdeb98dcf39deae35b",
        "size_bytes": 2_357_387,
    },
    {
        "bank_code": "MBB",
        "page_count": 103,
        "relative_path": "vietstock_bctc/MBB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf",
        "sha256": "9853cc4909dc73ddea9907465b09d7ecdb96cf6c1627f56943f3a20d14b49f80",
        "size_bytes": 10_165_066,
    },
    {
        "bank_code": "VPB",
        "page_count": 100,
        "relative_path": "vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf",
        "sha256": "f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0",
        "size_bytes": 7_578_043,
    },
    {
        "bank_code": "HDB",
        "page_count": 71,
        "relative_path": "vietstock_bctc/HDB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf",
        "sha256": "dad39b45a99747f7290d0a478af2f71f018f4adc59a590e158cdea16dd090ac3",
        "size_bytes": 5_043_254,
    },
    {
        "bank_code": "VCB",
        "page_count": 84,
        "relative_path": "vietstock_bctc/VCB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf",
        "sha256": "295f397de287f84c26dafbfa06f668604aa696a013e236253149d8547d032d1f",
        "size_bytes": 11_552_186,
    },
    {
        "bank_code": "CTG",
        "page_count": 85,
        "relative_path": "vietstock_bctc/CTG/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf",
        "sha256": "b82eeb879b667e80d0b5322969c808089fd39b83835b75dc47f9a890189fc137",
        "size_bytes": 11_853_560,
    },
    {
        "bank_code": "BID",
        "page_count": 74,
        "relative_path": "vietstock_bctc/BID/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf",
        "sha256": "415d713b18f281f97ea5416da01ddec32d20d9ad49342f3e31fc001743b8a222",
        "size_bytes": 16_399_456,
    },
    {
        "bank_code": "VIB",
        "page_count": 78,
        "relative_path": "vietstock_bctc/VIB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf",
        "sha256": "d6b96ddaaadb19a4ea1c083ceaa1a15500b742383321c2bcb7c22706509837b7",
        "size_bytes": 3_105_527,
    },
)
_ACTIVE_PROFILE = "wave1"
SOURCE_PADDING = (8, 4, 8, 4)
WHITE_BORDER = (12, 8, 12, 8)
_REF_FIELDS = {"path", "sha256", "size_bytes"}
_TERMINAL_STATUS = "UNRESOLVED_OCR_WORD_BOX_GEOMETRY"
_NATIVE_ROUTE = "CAUSAL_NATIVE_TEXT"
_NATIVE_STATUS = "CAUSAL_NATIVE_TEXT_READ_COMPLETE"
_RASTER_ROUTE = "DOMINANT_RASTER_OCR"
_RASTER_STATUS = "OCR_WORD_BOX_READ_COMPLETE"
_TERMINAL_FAILURE_REASON = "BOUNDED_WORD_BOX_NORMALIZATION_INVARIANT_FAILED"
_EXPECTED_BANK_ORDER = ("ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB")
_SAMPLE_ID_RE = re.compile(r"^sample-[0-9]{8}$")
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
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MANIFEST_FIELDS = {
    "authority",
    "documents",
    "format_version",
    "git_binding",
    "input_refs",
    "intended_reader",
    "metrics",
    "samples",
    "selection_rule",
}
_MANIFEST_DOCUMENT_FIELDS = {
    "bank_code",
    "document_manifest",
    "document_ordinal",
    "page_count",
    "pages",
    "plan_document_projection_sha256",
    "source_pdf",
}
_MANIFEST_PAGE_FIELDS = {
    "backend_ref",
    "geometry_mode",
    "hydration_receipt",
    "line_count",
    "physical_page",
    "plan_page_projection_sha256",
    "primary_line_count",
    "render_binding",
    "result_ref",
    "route",
    "sample_id_first",
    "sample_id_last",
    "sample_offset_start",
    "sample_offset_stop",
    "source_projection",
    "status",
    "supplement_line_count",
    "terminal_status_preserved",
    "v3_page_record_sha256",
}
_MANIFEST_SAMPLE_FIELDS = {
    "crop_ref",
    "document_ordinal",
    "line_axis_role",
    "line_index",
    "padded_source_bbox_raw_pixels",
    "physical_page",
    "sample_id",
    "source_bbox_raw_pixels",
}
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
_TERMINAL_BACKEND_FIELDS = {
    "claim_boundary",
    "format_version",
    "normalization_failure",
    "provider_identity_sha256",
    "raw_provider_payload",
    "render_ref",
    "request",
    "request_sha256",
    "word_box_normalization_ledger",
}
_TERMINAL_RESULT_FIELDS = {
    "backend_payload_ref",
    "claim_boundary",
    "coordinate_authority",
    "format_version",
    "input_render_ref",
    "lines",
    "metrics",
    "normalization_failure",
    "ocr_fallback_used",
    "physical_page",
    "provider_identity_sha256",
    "render_runtime_identity_sha256",
    "request",
    "request_sha256",
    "route",
    "safety",
    "source_blank_claimed",
    "source_sha256",
    "source_size_bytes",
    "status",
    "words",
}
_TERMINAL_FAILURE_FIELDS = {
    "control_identity_sha256",
    "format_version",
    "normalization_producer_implementation_ledger_sha256",
    "pixel_dimensions",
    "policy_sha256",
    "raw_payload_sha256",
    "reason",
    "status",
}
_TERMINAL_RESULT_SAFETY_FIELDS = {
    "absence_claimed",
    "bank_registry_metadata_used",
    "cells_interpreted",
    "filename_metadata_used",
    "historical_values_used",
    "mapping_used",
    "role_a_used",
    "rows_reconstructed",
    "schema_used",
    "statement_classified",
    "table_classified",
}


class FullDocumentVietOCRRequestV1Error(RuntimeError):
    """The source denominator, crop bytes, or publication contract drifted."""


def _error(message: str) -> FullDocumentVietOCRRequestV1Error:
    return FullDocumentVietOCRRequestV1Error(message)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _publish_directory_noreplace(source: Path, destination: Path) -> None:
    """Atomically publish one sibling directory with Linux RENAME_NOREPLACE."""

    if source.parent != destination.parent or source.name == destination.name:
        raise _error("no-replace publication requires distinct sibling directories")
    parent = source.parent
    parent_fd = os.open(
        parent,
        os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW,
    )
    try:
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
        if (
            renameat2(
                parent_fd,
                os.fsencode(source.name),
                parent_fd,
                os.fsencode(destination.name),
                1,
            )
            != 0
        ):
            code = ctypes.get_errno()
            if code in {errno.EEXIST, errno.ENOTEMPTY}:
                raise _error(f"refusing to overwrite existing output: {destination}")
            raise _error(f"atomic no-replace publication failed with errno {code}")
    finally:
        os.close(parent_fd)


def _stable_bytes(path: Path, label: str) -> bytes:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError as exc:
        raise _error(f"cannot open {label} nofollow: {path}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise _error(f"{label} is not a regular file")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        raise _error(f"{label} changed while being read")
    payload = b"".join(chunks)
    if len(payload) != before.st_size:
        raise _error(f"{label} size changed while being read")
    return payload


def _json(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    raw = _stable_bytes(path, label)

    return _decode_json(raw, label), raw


def _decode_json(raw: bytes, label: str) -> dict[str, Any]:
    """Decode one strict JSON object while rejecting duplicate/non-finite keys."""

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise _error(f"{label} repeats JSON key {key!r}")
            result[key] = value
        return result

    def bad_constant(value: str) -> None:
        raise _error(f"{label} contains non-finite value {value}")

    try:
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=bad_constant
        )
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
        raise _error(f"cannot decode strict {label}") from exc
    if type(value) is not dict:
        raise _error(f"{label} must be one object")
    return cast(dict[str, Any], value)


def _sha256(value: Any, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise _error(f"{label} must be one lowercase SHA-256")
    return value


def _repository_file_ref(path: Path, label: str) -> dict[str, Any]:
    raw = _stable_bytes(path, label)
    try:
        relative = path.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise _error(f"{label} lies outside the project root") from exc
    return {
        "path": relative.as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
    }


def _canonical_object_sha256(value: dict[str, Any]) -> str:
    return canonical_json_sha256_v1(value)


def _activate_profile(profile: str) -> None:
    """Select one input corpus while retaining the same crop/reader pipeline."""

    global _ACTIVE_PROFILE
    global OUTPUT_ROOT
    global VERIFIED_INDEX_DIRECTORY
    global VIETOCR_OUTPUT_DIRECTORY
    if profile not in {"wave1", "annual-2025"}:
        raise _error(f"unsupported full-document profile: {profile}")
    _ACTIVE_PROFILE = profile
    OUTPUT_ROOT = (
        ANNUAL_2025_OUTPUT_ROOT
        if profile == "annual-2025"
        else Path("output/development/loan-maturity-full-document-vietocr-v1")
    )
    VIETOCR_OUTPUT_DIRECTORY = OUTPUT_ROOT / "vietocr-transformer"
    VERIFIED_INDEX_DIRECTORY = OUTPUT_ROOT / "verified-index"


def _artifact_json_bytes_v1(value: Any) -> bytes:
    """Preserve the legacy Wave-1 framing while keeping annual artifacts canonical."""

    canonical = canonical_json_bytes_v1(value)
    return canonical if _ACTIVE_PROFILE == "annual-2025" else canonical + b"\n"


def _annual_output_ref(path: Path, label: str) -> dict[str, Any]:
    resolved = path.resolve()
    root = PROJECT_ROOT.resolve()
    if not resolved.is_relative_to(root):
        raise _error(f"{label} lies outside the project root")
    return _repository_file_ref(resolved, label)


def _annual_ppocr_line_boxes(
    payload: dict[str, Any], *, width: int, height: int
) -> list[list[int]]:
    """Validate non-word geometry and expose only ordered line boxes.

    PP-OCR word subdivisions are neither used for the blind VietOCR crop
    denominator nor exposed downstream. Their schema remains checked, but
    provider word coordinates are quarantined because they can extend a few
    pixels outside an otherwise valid rendered-page line box.
    """

    required_fields = {
        "dt_polys",
        "input_path",
        "model_settings",
        "page_index",
        "rec_boxes",
        "rec_polys",
        "rec_scores",
        "rec_texts",
        "return_word_box",
        "text_det_params",
        "text_rec_score_thresh",
        "text_type",
        "text_word",
        "text_word_boxes",
    }
    if type(payload) is not dict or set(payload) not in (
        required_fields,
        required_fields | {"textline_orientation_angles"},
    ):
        raise _error("annual PP-OCRv6 archived provider field set drifted")
    if type(payload["input_path"]) is not str or not payload["input_path"]:
        raise _error("annual PP-OCRv6 provider input path is invalid")
    schema_payload = {key: value for key, value in payload.items() if key != "input_path"}
    orientation = schema_payload.get("textline_orientation_angles")
    if orientation is None:
        if payload.get("rec_boxes") != []:
            raise _error("annual nonempty PP-OCRv6 page omitted its orientation axis")
        schema_payload["textline_orientation_angles"] = []
    elif type(orientation) is not list or len(orientation) != len(payload.get("rec_boxes", [])):
        raise _error("annual PP-OCRv6 orientation axis drifted")
    try:
        geometry = full_v3._validate_ppocrv6_schema_except_word_geometry(  # noqa: SLF001
            schema_payload,
            pixel_width=width,
            pixel_height=height,
        )
    except full_v3.WaveOneRoleBFullReaderError as exc:
        raise _error("annual PP-OCRv6 non-word provider geometry is invalid") from exc
    provider_boxes = payload.get("rec_boxes")
    if type(provider_boxes) is not list or len(provider_boxes) != geometry["line_count"]:
        raise _error("annual PP-OCRv6 line denominator drifted")
    return [
        _bbox(box, width, height, f"annual PP-OCRv6 line {line_index}")
        for line_index, box in enumerate(provider_boxes)
    ]


def _annual_document_inputs(
    source: dict[str, Any], document_ordinal: int
) -> tuple[
    bytes,
    dict[str, Any],
    bytes,
    dict[str, Any],
    bytes,
    Path,
    dict[str, Any],
    bytes,
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    bank = source["bank_code"]
    source_path = PROJECT_ROOT / source["relative_path"]
    source_raw = _stable_bytes(source_path, f"annual source PDF {bank}")
    if (
        len(source_raw) != source["size_bytes"]
        or hashlib.sha256(source_raw).hexdigest() != source["sha256"]
    ):
        raise _error(f"annual source PDF identity drifted: {bank}")
    document_id = source["sha256"][:20]
    preprocess_root = PROJECT_ROOT / ANNUAL_2025_PREPROCESS_ROOT / document_id
    preprocess, preprocess_raw = _json(
        preprocess_root / "manifest.json", f"annual preprocess manifest {bank}"
    )
    preprocess_envelope, preprocess_envelope_raw = _json(
        preprocess_root / "run_manifest.json", f"annual preprocess envelope {bank}"
    )
    preprocess_pages = preprocess.get("pages")
    if (
        preprocess.get("state") != "PREPROCESSED"
        or preprocess.get("dataset_role") != "CALIBRATION"
        or preprocess.get("source_sha256") != source["sha256"]
        or preprocess.get("code", {}).get("git_dirty") is not False
        or type(preprocess_pages) is not list
        or len(preprocess_pages) != source["page_count"]
        or preprocess_envelope
        != {
            "manifest": "manifest.json",
            "manifest_sha256": hashlib.sha256(preprocess_raw).hexdigest(),
            "source_sha256": source["sha256"],
            "state": "PREPROCESSED",
        }
    ):
        raise _error(f"annual preprocess identity/denominator drifted: {bank}")

    batch_root = PROJECT_ROOT / ANNUAL_2025_PPOCR_ROOT / bank
    batch, batch_raw = _json(batch_root / "batch_manifest.json", f"annual batch {bank}")
    batch_pages = batch.get("pages")
    renders = batch.get("renders")
    input_manifest = batch.get("input_manifest")
    batch_source = batch.get("source")
    _validate_annual_ppocr_batch_trust_closure(batch, source)
    expected_pages = list(range(1, source["page_count"] + 1))
    if (
        batch.get("state") != "OCR_COMPLETE"
        or batch.get("dataset_role") != "CALIBRATION"
        or batch.get("evidence_role") != "INDEPENDENT_GEOMETRY_PROPOSAL_ONLY"
        or batch.get("code", {}).get("dirty") is not False
        or not same_typed_json_v1(batch.get("requested_pages"), expected_pages)
        or type(batch_pages) is not list
        or type(renders) is not list
        or len(batch_pages) != source["page_count"]
        or len(renders) != source["page_count"]
        or not same_typed_json_v1(
            [page.get("page") for page in batch_pages if type(page) is dict], expected_pages
        )
        or not same_typed_json_v1(
            [render.get("page") for render in renders if type(render) is dict], expected_pages
        )
        or type(input_manifest) is not dict
        or input_manifest.get("sha256") != hashlib.sha256(preprocess_raw).hexdigest()
        or type(input_manifest.get("size_bytes")) is not int
        or input_manifest.get("size_bytes") != len(preprocess_raw)
        or type(batch_source) is not dict
        or batch_source.get("sha256") != source["sha256"]
        or type(batch_source.get("size_bytes")) is not int
        or batch_source.get("size_bytes") != source["size_bytes"]
        or batch.get("metrics", {}).get("completed_page_count") != source["page_count"]
    ):
        raise _error(f"annual PP-OCRv6 batch identity/denominator drifted: {bank}")
    if len({page.get("page") for page in batch_pages}) != len(batch_pages):
        raise _error(f"annual PP-OCRv6 batch repeats a page: {bank}")
    _validate_annual_ppocr_batch_aggregate(batch, bank=cast(str, bank))
    if document_ordinal < 1:
        raise _error("annual document ordinal must be positive")
    return (
        source_raw,
        preprocess,
        preprocess_raw,
        preprocess_envelope,
        preprocess_envelope_raw,
        batch_root,
        batch,
        batch_raw,
        cast(list[dict[str, Any]], batch_pages),
        cast(list[dict[str, Any]], renders),
    )


def _validate_annual_ppocr_batch_aggregate(batch: dict[str, Any], *, bank: str) -> None:
    """Recompute the mutable batch summary from its exact ordered page records."""

    pages = batch.get("pages")
    sessions = batch.get("sessions")
    metrics = batch.get("metrics")
    if type(pages) is not list or type(sessions) is not list or type(metrics) is not dict:
        raise _error(f"annual PP-OCRv6 batch aggregate fields drifted: {bank}")

    page_metric_fields = {
        "line_count",
        "lines_below_0_8",
        "lines_below_0_9",
        "mean_line_score",
        "minimum_line_score",
        "wall_seconds",
        "word_token_count",
    }
    line_count = 0
    word_token_count = 0
    lines_below_0_8 = 0
    lines_below_0_9 = 0
    page_wall_seconds = 0.0
    weighted_score = 0.0
    minimum_scores: list[float] = []
    for page_offset, page in enumerate(pages, 1):
        page_metrics = page.get("metrics") if type(page) is dict else None
        if type(page_metrics) is not dict or set(page_metrics) != page_metric_fields:
            raise _error(f"annual PP-OCRv6 page metrics drifted: {bank}:{page_offset}")
        count = page_metrics.get("line_count")
        words = page_metrics.get("word_token_count")
        below_0_8 = page_metrics.get("lines_below_0_8")
        below_0_9 = page_metrics.get("lines_below_0_9")
        wall_seconds = page_metrics.get("wall_seconds")
        minimum = page_metrics.get("minimum_line_score")
        mean = page_metrics.get("mean_line_score")
        if (
            type(count) is not int
            or count < 0
            or type(words) is not int
            or words < 0
            or type(below_0_8) is not int
            or not 0 <= below_0_8 <= count
            or type(below_0_9) is not int
            or not 0 <= below_0_9 <= count
            or below_0_8 > below_0_9
            or type(wall_seconds) is not float
            or not math.isfinite(wall_seconds)
            or wall_seconds < 0.0
            or (count == 0 and (minimum is not None or mean is not None))
            or (
                count > 0
                and (
                    type(minimum) is not float
                    or not math.isfinite(minimum)
                    or not 0.0 <= minimum <= 1.0
                    or type(mean) is not float
                    or not math.isfinite(mean)
                    or not 0.0 <= mean <= 1.0
                )
            )
        ):
            raise _error(f"annual PP-OCRv6 page metric values drifted: {bank}:{page_offset}")
        line_count += count
        word_token_count += words
        lines_below_0_8 += below_0_8
        lines_below_0_9 += below_0_9
        page_wall_seconds += wall_seconds
        if count:
            weighted_score += cast(float, mean) * count
            minimum_scores.append(cast(float, minimum))

    load_seconds: list[float] = []
    for session_offset, session in enumerate(sessions, 1):
        if (
            type(session) is not dict
            or set(session) != {"model_load_wall_seconds", "started_at"}
            or type(session.get("started_at")) is not str
            or not session["started_at"]
            or type(session.get("model_load_wall_seconds")) is not float
            or not math.isfinite(session["model_load_wall_seconds"])
            or session["model_load_wall_seconds"] < 0.0
        ):
            raise _error(f"annual PP-OCRv6 model-load session drifted: {bank}:{session_offset}")
        load_seconds.append(session["model_load_wall_seconds"])

    expected = {
        "completed_page_count": len(pages),
        "line_count": line_count,
        "lines_below_0_8": lines_below_0_8,
        "lines_below_0_9": lines_below_0_9,
        "mean_line_score": weighted_score / line_count if line_count else None,
        "minimum_line_score": min(minimum_scores) if minimum_scores else None,
        "model_load_session_count": len(sessions),
        "model_load_wall_seconds_total": round(sum(load_seconds), 6),
        "page_inference_wall_seconds": round(page_wall_seconds, 6),
        "word_token_count": word_token_count,
    }
    if not same_typed_json_v1(metrics, expected):
        raise _error(f"annual PP-OCRv6 batch aggregate does not recompute: {bank}")


def _validate_annual_ppocr_batch_trust_closure(
    batch: dict[str, Any], source: dict[str, Any]
) -> None:
    code = batch.get("code")
    configuration = batch.get("configuration")
    runtime = batch.get("runtime_identity")
    registration = batch.get("dataset_registration")
    input_manifest = batch.get("input_manifest")
    batch_source = batch.get("source")
    requested_pages = batch.get("requested_pages")
    renders = batch.get("renders")
    if (
        type(code) is not dict
        or set(code) != {"commit", "dirty"}
        or type(code.get("commit")) is not str
        or re.fullmatch(r"[0-9a-f]{40}", code["commit"]) is None
        or code.get("dirty") is not False
    ):
        raise _error("annual PP-OCRv6 batch code identity drifted")
    commit = cast(str, code["commit"])
    try:
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        raise _error("annual PP-OCRv6 batch commit is not an ancestor of HEAD") from exc

    tracked_paths = (
        Path("config/models/pp-ocrv6-word-box.yaml"),
        Path("scripts/models/run_ppocrv6_word_boxes_batch.py"),
        Path("scripts/models/run_ppocrv6_word_boxes.py"),
        Path("config/models/gpu-runtime.toml"),
    )
    tracked_bytes: dict[Path, bytes] = {}
    for relative in tracked_paths:
        current = _stable_bytes(PROJECT_ROOT / relative, f"annual PP-OCR trust file {relative}")
        try:
            committed = subprocess.run(
                ["git", "show", f"{commit}:{relative.as_posix()}"],
                cwd=PROJECT_ROOT,
                check=True,
                capture_output=True,
            ).stdout
        except subprocess.CalledProcessError as exc:
            raise _error(f"annual PP-OCR trust file is absent at run commit: {relative}") from exc
        if current != committed:
            raise _error(f"annual PP-OCR trust file changed after the batch: {relative}")
        tracked_bytes[relative] = current

    expected_configuration = {
        "cpu_threads": 3,
        "implicit_orientation_or_unwarp": False,
        "mkldnn": False,
        "network_policy": "PROCESS_SOCKET_CONNECT_DENIED",
        "path": tracked_paths[0].as_posix(),
        "precision": "fp32",
        "runner_path": tracked_paths[1].as_posix(),
        "runner_sha256": hashlib.sha256(tracked_bytes[tracked_paths[1]]).hexdigest(),
        "sha256": hashlib.sha256(tracked_bytes[tracked_paths[0]]).hexdigest(),
        "single_page_helper_path": tracked_paths[2].as_posix(),
        "single_page_helper_sha256": hashlib.sha256(tracked_bytes[tracked_paths[2]]).hexdigest(),
    }
    expected_runtime = {
        "compiled_with_cuda": False,
        "device": "cpu",
        "manifest_path": tracked_paths[3].as_posix(),
        "manifest_sha256": hashlib.sha256(tracked_bytes[tracked_paths[3]]).hexdigest(),
        "models": [
            {
                "key": "pp_ocrv6_medium_det",
                "repo_id": "PaddlePaddle/PP-OCRv6_medium_det",
                "revision": "8e0f56fb2ef86b461d99cfc7ac5c137738985f61",
                "weights_sha256": (
                    "85218d2e3d98f5a21c58b4220627be923a97aee5db3cc71f39536ab31ac53960"
                ),
                "weights_size_bytes": 61_960_476,
            },
            {
                "key": "pp_ocrv6_medium_rec",
                "repo_id": "PaddlePaddle/PP-OCRv6_medium_rec",
                "revision": "e5a92bcbc5cc1b494628e458d267778f0704fd7c",
                "weights_sha256": (
                    "1b01c79a914587933f615569e75de54f2e638ebb5d3f3b3c1b38c24ede8c7319"
                ),
                "weights_size_bytes": 76_465_087,
            },
        ],
        "packages": {
            "paddleocr": "3.7.0",
            "paddlepaddle": "3.3.0",
            "paddlex": "3.7.2",
        },
    }
    expected_registration = {
        "assigned_at",
        "dataset_role",
        "document_id",
        "immutable",
        "source_path",
    }
    if (
        not same_typed_json_v1(configuration, expected_configuration)
        or not same_typed_json_v1(runtime, expected_runtime)
        or type(registration) is not dict
        or set(registration) != expected_registration
        or type(registration.get("assigned_at")) is not str
        or not registration["assigned_at"]
        or registration.get("dataset_role") != "CALIBRATION"
        or registration.get("document_id") != f"sha256:{source['sha256']}"
        or registration.get("immutable") is not True
        or registration.get("source_path") != source["relative_path"]
        or not same_typed_json_v1(
            batch_source,
            {
                "path": source["relative_path"],
                "sha256": source["sha256"],
                "size_bytes": source["size_bytes"],
            },
        )
        or type(input_manifest) is not dict
        or type(requested_pages) is not list
        or type(renders) is not list
    ):
        raise _error("annual PP-OCRv6 batch trust closure drifted")

    immutable_identity = {
        "code": code,
        "configuration": configuration,
        "dataset_registration": registration,
        "dataset_role": batch.get("dataset_role"),
        "evidence_role": batch.get("evidence_role"),
        "input_manifest": input_manifest,
        "renders": renders,
        "requested_pages": requested_pages,
        "runtime_identity": runtime,
        "schema_version": batch.get("schema_version"),
        "source": batch_source,
    }
    expected_identity = hashlib.sha256(
        json.dumps(
            immutable_identity,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    if batch.get("batch_identity") != expected_identity:
        raise _error("annual PP-OCRv6 batch identity does not recompute")


def _annual_geometry_selection_payload(producer_commit: str) -> dict[str, Any]:
    if type(producer_commit) is not str or re.fullmatch(r"[0-9a-f]{40}", producer_commit) is None:
        raise _error("annual geometry selection producer commit is invalid")
    documents: list[dict[str, Any]] = []
    for document_ordinal, source in enumerate(ANNUAL_2025_SOURCES, 1):
        (
            _source_raw,
            _preprocess,
            preprocess_raw,
            _preprocess_envelope,
            preprocess_envelope_raw,
            _batch_root,
            batch,
            batch_raw,
            _batch_pages,
            _renders,
        ) = _annual_document_inputs(source, document_ordinal)
        bank = cast(str, source["bank_code"])
        documents.append(
            {
                "bank_code": bank,
                "document_ordinal": document_ordinal,
                "page_count": source["page_count"],
                "ppocr_batch_identity": batch["batch_identity"],
                "ppocr_batch_manifest": {
                    "path": (ANNUAL_2025_PPOCR_ROOT / bank / "batch_manifest.json").as_posix(),
                    "sha256": hashlib.sha256(batch_raw).hexdigest(),
                    "size_bytes": len(batch_raw),
                },
                "ppocr_line_count": batch["metrics"]["line_count"],
                "preprocess_envelope": {
                    "path": (
                        ANNUAL_2025_PREPROCESS_ROOT / source["sha256"][:20] / "run_manifest.json"
                    ).as_posix(),
                    "sha256": hashlib.sha256(preprocess_envelope_raw).hexdigest(),
                    "size_bytes": len(preprocess_envelope_raw),
                },
                "preprocess_manifest": {
                    "path": (
                        ANNUAL_2025_PREPROCESS_ROOT / source["sha256"][:20] / "manifest.json"
                    ).as_posix(),
                    "sha256": hashlib.sha256(preprocess_raw).hexdigest(),
                    "size_bytes": len(preprocess_raw),
                },
                "source_pdf": {
                    "path": source["relative_path"],
                    "sha256": source["sha256"],
                    "size_bytes": source["size_bytes"],
                },
            }
        )
    body = {
        "authority": {
            "geometry_proposal_authority": True,
            "mapping_authority": False,
            "numeric_authority": False,
            "ppocr_recognition_text_semantic_authority": False,
            "schema_authority": False,
            "vietocr_semantic_text_present": False,
        },
        "bank_order": list(_EXPECTED_BANK_ORDER),
        "claim_boundary": (
            "POST_PPOCR_FIXED_ANNUAL_2025_WHOLE_DOCUMENT_LINE_GEOMETRY_SELECTION_"
            "NO_TEXT_NUMERIC_SCHEMA_OR_MAPPING_AUTHORITY"
        ),
        "documents": documents,
        "format_version": "ANNUAL_2025_8BANK_PPOCRV6_GEOMETRY_SELECTION_V1",
        "metrics": {
            "document_count": len(documents),
            "line_count_vector": [document["ppocr_line_count"] for document in documents],
            "page_count": sum(document["page_count"] for document in documents),
            "page_count_vector": [document["page_count"] for document in documents],
            "sample_count": sum(document["ppocr_line_count"] for document in documents),
        },
        "producer_commit": producer_commit,
        "state": "FIXED_POST_PPOCR_GEOMETRY_SELECTION",
    }
    return {
        **body,
        "selection_id": f"annual-2025-ppocrv6-geometry:{canonical_json_sha256_v1(body)}",
    }


def seal_annual_2025_geometry_selection_v1() -> dict[str, Any]:
    """Create the one fixed tracked pin that must precede the VietOCR crop freeze."""

    _activate_profile("annual-2025")
    if _git("status", "--porcelain"):
        raise _error("annual geometry selection requires one clean Git worktree")
    path = PROJECT_ROOT / ANNUAL_2025_GEOMETRY_SELECTION_PATH
    if path.exists():
        raise _error(f"refusing to overwrite annual geometry selection: {path}")
    selection = _annual_geometry_selection_payload(_git("rev-parse", "HEAD"))
    raw = _artifact_json_bytes_v1(selection)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
        0o644,
    )
    try:
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise _error("annual geometry selection write made no progress")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return {
        "line_count_vector": selection["metrics"]["line_count_vector"],
        "page_count_vector": selection["metrics"]["page_count_vector"],
        "path": ANNUAL_2025_GEOMETRY_SELECTION_PATH.as_posix(),
        "selection_id": selection["selection_id"],
        "sha256": hashlib.sha256(raw).hexdigest(),
        "status": selection["state"],
    }


def _validate_annual_geometry_selection_v1() -> tuple[dict[str, Any], bytes]:
    _activate_profile("annual-2025")
    if _git("status", "--porcelain"):
        raise _error("annual geometry selection replay requires one clean Git worktree")
    path = PROJECT_ROOT / ANNUAL_2025_GEOMETRY_SELECTION_PATH
    selection, raw = _verify_canonical_json_file(path, "annual geometry selection")
    producer_commit = selection.get("producer_commit")
    expected = _annual_geometry_selection_payload(cast(str, producer_commit))
    if not same_typed_json_v1(selection, expected):
        raise _error("annual geometry selection differs from live pinned PP-OCR inputs")
    try:
        tracked = subprocess.run(
            ["git", "show", f"HEAD:{ANNUAL_2025_GEOMETRY_SELECTION_PATH.as_posix()}"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
        ).stdout
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", cast(str, producer_commit), "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        raise _error("annual geometry selection is not tracked on a valid Git descendant") from exc
    if tracked != raw:
        raise _error("annual geometry selection bytes differ from clean Git HEAD")
    return selection, raw


def _validate_annual_selection_denominator_v1(
    selection: dict[str, Any],
    *,
    page_count_vector: list[int],
    line_count_vector: list[int],
    sample_count: int,
) -> None:
    metrics = selection.get("metrics")
    expected = {
        "document_count": len(ANNUAL_2025_SOURCES),
        "line_count_vector": line_count_vector,
        "page_count": sum(page_count_vector),
        "page_count_vector": page_count_vector,
        "sample_count": sample_count,
    }
    if not same_typed_json_v1(metrics, expected):
        raise _error("annual crop denominator differs from tracked geometry selection")


def _annual_page_geometry(
    *,
    bank: str,
    batch_root: Path,
    batch: dict[str, Any],
    batch_page: dict[str, Any],
    render_record: dict[str, Any],
    physical_page: int,
) -> tuple[
    bytes,
    list[list[int]],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    if (
        type(batch_page.get("page")) is not int
        or batch_page.get("page") != physical_page
        or type(render_record.get("page")) is not int
        or render_record.get("page") != physical_page
    ):
        raise _error(f"annual page order drifted: {bank}:{physical_page}")
    render_path_value = render_record.get("path")
    if type(render_path_value) is not str:
        raise _error(f"annual render path is invalid: {bank}:{physical_page}")
    render_path = Path(render_path_value)
    if not render_path.is_absolute():
        render_path = PROJECT_ROOT / render_path
    render_ref = _annual_output_ref(render_path, f"annual render {bank}:{physical_page}")
    if (
        render_ref["sha256"] != render_record.get("sha256")
        or render_ref["size_bytes"] != render_record.get("size_bytes")
        or type(render_record.get("dpi")) is not int
        or render_record.get("dpi") != 200
    ):
        raise _error(f"annual render identity drifted: {bank}:{physical_page}")
    render_raw = _stable_bytes(render_path, f"annual render bytes {bank}:{physical_page}")
    with Image.open(io.BytesIO(render_raw)) as image:
        width, height = image.size
        image.verify()
    if (
        type(render_record.get("width_pixels")) is not int
        or render_record.get("width_pixels") != width
        or type(render_record.get("height_pixels")) is not int
        or render_record.get("height_pixels") != height
    ):
        raise _error(f"annual render dimensions drifted: {bank}:{physical_page}")

    result_value = batch_page.get("ocr_result")
    run_value = batch_page.get("run_manifest")
    if type(result_value) is not dict or type(run_value) is not dict:
        raise _error(f"annual batch page references drifted: {bank}:{physical_page}")
    result_relative = Path(str(result_value.get("path", "")))
    run_relative = Path(str(run_value.get("path", "")))
    if (
        result_relative.is_absolute()
        or run_relative.is_absolute()
        or ".." in result_relative.parts
        or ".." in run_relative.parts
    ):
        raise _error(f"annual batch page reference path is unsafe: {bank}:{physical_page}")
    result_path = batch_root / result_relative
    run_path = batch_root / run_relative
    result_ref = _annual_output_ref(result_path, f"annual PP-OCR result {bank}:{physical_page}")
    run_ref = _annual_output_ref(run_path, f"annual PP-OCR run {bank}:{physical_page}")
    if not same_typed_json_v1(result_ref, {**result_value, "path": result_ref["path"]}):
        raise _error(f"annual PP-OCR result reference drifted: {bank}:{physical_page}")
    if not same_typed_json_v1(run_ref, {**run_value, "path": run_ref["path"]}):
        raise _error(f"annual PP-OCR run reference drifted: {bank}:{physical_page}")
    result_raw = _stable_bytes(result_path, f"annual PP-OCR result bytes {bank}:{physical_page}")
    payload = _decode_json(result_raw, f"annual PP-OCR result {bank}:{physical_page}")
    boxes = _annual_ppocr_line_boxes(payload, width=width, height=height)
    run, _run_raw = _json(run_path, f"annual PP-OCR run {bank}:{physical_page}")
    run_artifact = run.get("artifacts", {}).get("ocr_result")
    if (
        type(run.get("schema_version")) is not int
        or run.get("schema_version") != 1
        or run.get("state") != "OCR_COMPLETE"
        or run.get("dataset_role") != "CALIBRATION"
        or run.get("evidence_role") != "INDEPENDENT_GEOMETRY_PROPOSAL_ONLY"
        or run.get("confidence_policy") != "NO_AUTOMATIC_TRUTH_OR_SCHEMA_PROMOTION"
        or type(run.get("page")) is not int
        or run.get("page") != physical_page
        or run.get("batch_identity") != batch.get("batch_identity")
        or not same_typed_json_v1(run.get("input"), render_record)
        or not same_typed_json_v1(run.get("code"), batch.get("code"))
        or not same_typed_json_v1(run.get("configuration"), batch.get("configuration"))
        or not same_typed_json_v1(run.get("runtime"), batch.get("runtime_identity"))
        or not same_typed_json_v1(run.get("metrics"), batch_page.get("metrics"))
        or type(run_artifact) is not dict
        or run_artifact.get("path") != result_path.name
        or run_artifact.get("sha256") != result_ref["sha256"]
        or run_artifact.get("size_bytes") != result_ref["size_bytes"]
        or batch_page.get("metrics", {}).get("line_count") != len(boxes)
    ):
        raise _error(f"annual PP-OCR run/result binding drifted: {bank}:{physical_page}")
    geometry_axis_raw = canonical_json_bytes_v1(
        [{"line_index": index, "raw_pixel_bbox": box} for index, box in enumerate(boxes)]
    )
    source_projection = {
        "batch_identity": batch["batch_identity"],
        "batch_page_projection_sha256": _canonical_object_sha256(batch_page),
        "geometry_axis_sha256": hashlib.sha256(geometry_axis_raw).hexdigest(),
        "mode": "PPOCRV6_BATCH_PROVIDER_LINE_GEOMETRY_V1",
        "provider_payload_sha256": hashlib.sha256(result_raw).hexdigest(),
    }
    return render_raw, boxes, render_ref, source_projection, result_ref, run_ref


def _validate_vietocr_transformer_config() -> dict[str, Any]:
    path = PROJECT_ROOT / VIETOCR_CONFIG_PATH
    raw = _stable_bytes(path, "VietOCR Transformer config")
    try:
        config = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise _error("VietOCR Transformer config is not valid UTF-8 TOML") from exc
    inference = config.get("inference")
    safety = config.get("safety")
    artifacts = config.get("artifacts")
    if (
        config.get("version") != 2
        or config.get("status") != "CALIBRATION_ONLY_RTX4090_VIETNAMESE_LOGICAL_ROW_LABEL_PROPOSAL"
        or config.get("model_name") != "VietOCR VGG Transformer"
        or config.get("package_version") != "0.3.13"
        or config.get("architecture") != "vgg19_bn_transformer"
        or type(inference) is not dict
        or inference.get("device") != "cuda:0"
        or inference.get("beam_search") is not False
        or inference.get("cnn_pretrained_download") is not False
        or inference.get("network_permitted") is not False
        or inference.get("reference_text_available_to_decoder") is not False
        or type(safety) is not dict
        or not safety
        or any(bool(value) for value in safety.values())
        or type(artifacts) is not dict
        or type(artifacts.get("weights")) is not dict
        or artifacts["weights"].get("sha256")
        != "380512193a8b6cbf6fad80deacdc9b6939d10d473d199892fc6408d13775ea59"
    ):
        raise _error("VietOCR config is not the pinned VGG Transformer 0.3.13 contract")
    return {
        "architecture": config["architecture"],
        "config_ref": {
            "path": VIETOCR_CONFIG_PATH.as_posix(),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw),
        },
        "model_name": config["model_name"],
        "package_version": config["package_version"],
        "weights_sha256": artifacts["weights"]["sha256"],
    }


def _verified_ref(root: Path, value: Any, label: str) -> tuple[Path, bytes, dict[str, Any]]:
    if type(value) is not dict or set(value) != _REF_FIELDS:
        raise _error(f"{label} reference fields drifted")
    path_value = value["path"]
    if (
        type(path_value) is not str
        or type(value["size_bytes"]) is not int
        or value["size_bytes"] < 0
        or type(value["sha256"]) is not str
        or _SHA256_RE.fullmatch(value["sha256"]) is None
    ):
        raise _error(f"{label} reference identity drifted")
    relative = Path(path_value)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise _error(f"{label} reference path is unsafe")
    path = root / relative
    raw = _stable_bytes(path, label)
    if len(raw) != value["size_bytes"] or hashlib.sha256(raw).hexdigest() != value["sha256"]:
        raise _error(f"{label} reference bytes drifted")
    return path, raw, dict(value)


def _project_ref_to_repository(root: Path, reference: dict[str, Any]) -> dict[str, Any]:
    path = root / reference["path"]
    return {
        "path": path.relative_to(PROJECT_ROOT).as_posix(),
        "sha256": reference["sha256"],
        "size_bytes": reference["size_bytes"],
    }


def _bbox(value: Any, width: int, height: int, label: str) -> list[int]:
    if type(value) is not list or len(value) != 4 or any(type(item) is not int for item in value):
        raise _error(f"{label} bbox fields drifted")
    box = list(value)
    if not (0 <= box[0] < box[2] <= width and 0 <= box[1] < box[3] <= height):
        raise _error(f"{label} bbox lies outside render")
    return box


def _padded(box: list[int], width: int, height: int) -> tuple[int, int, int, int]:
    left, top, right, bottom = SOURCE_PADDING
    return (
        max(0, box[0] - left),
        max(0, box[1] - top),
        min(width, box[2] + right),
        min(height, box[3] + bottom),
    )


def _raster_page(
    page_record: dict[str, Any], result: dict[str, Any]
) -> tuple[bytes, list[list[int]], dict[str, Any], dict[str, Any]]:
    if (
        page_record.get("route") != _RASTER_ROUTE
        or page_record.get("status") != _RASTER_STATUS
        or page_record.get("unresolved") is not False
        or result.get("status") != _RASTER_STATUS
    ):
        raise _error("ordinary raster page state drifted")
    _render_path, render_raw, render_ref = _verified_ref(
        PROJECT_ROOT / V3_ROOT, page_record.get("render_ref"), "raster render"
    )
    with Image.open(io.BytesIO(render_raw)) as image:
        width, height = image.size
        image.verify()
    lines = result.get("lines")
    if type(lines) is not list:
        raise _error("raster result line axis drifted")
    boxes = [
        _bbox(line.get("raw_pixel_bbox"), width, height, f"raster line {index}")
        for index, line in enumerate(lines)
        if type(line) is dict
    ]
    if len(boxes) != len(lines):
        raise _error("raster result contains a non-line record")
    try:
        projection = project_authenticated_page_v2(
            page_record=page_record,
            page_result=result,
        )
    except SourceEvidenceProjectionV2Error as exc:
        raise _error("ordinary raster source projection drifted") from exc
    return (
        render_raw,
        boxes,
        _project_ref_to_repository(PROJECT_ROOT / V3_ROOT, render_ref),
        {
            "mode": "PRIMARY_V2_PAGE_PROJECTION",
            "sha256": _canonical_object_sha256(projection),
        },
    )


def _native_hydrated_page(
    *,
    source_sha256: str,
    physical_page: int,
    page_record: dict[str, Any],
    result: dict[str, Any],
) -> tuple[bytes, list[list[int]], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Replay the sealed generic native geometry adapter.

    Native canonical coordinates require deterministic PDF rendering and the
    sealed adapter's exact outward pixel projection.  Terminal provider pixels
    are already bound to an upstream render and use the experiment-local path
    below instead.
    """

    route = page_record.get("route")
    status = page_record.get("status")
    unresolved = page_record.get("unresolved")
    if (
        route != _NATIVE_ROUTE
        or status != _NATIVE_STATUS
        or unresolved is not False
        or result.get("status") != _NATIVE_STATUS
    ):
        raise _error("native page state drifted")

    envelope, capability = replay_authenticated_line_pixel_hydration_v1(
        PROJECT_ROOT,
        source_pdf_sha256=source_sha256,
        physical_page=physical_page,
    )
    envelope = validate_authenticated_line_pixel_hydration_envelope_v1(envelope, capability)
    if read_authenticated_line_pixel_hydration_envelope_v1(capability) != envelope:
        raise _error("hydration live envelope changed across authenticated reads")
    render_raw = read_authenticated_line_pixel_hydration_render_v1(capability)
    receipt = project_authenticated_line_pixel_hydration_receipt_v1(capability)
    source_binding = envelope.get("source_binding")
    upstream = envelope.get("upstream_binding")
    render_binding = envelope.get("render_binding")
    quarantine = envelope.get("quarantine")
    if (
        type(source_binding) is not dict
        or source_binding.get("source_pdf_sha256") != source_sha256
        or source_binding.get("physical_page") != physical_page
        or type(upstream) is not dict
        or upstream.get("route") != route
        or upstream.get("status") != status
        or upstream.get("status_preserved") is not True
        or type(render_binding) is not dict
        or render_binding.get("sha256") != hashlib.sha256(render_raw).hexdigest()
        or render_binding.get("size_bytes") != len(render_raw)
        or type(quarantine) is not dict
        or quarantine.get("word_text_exposed") is not False
        or quarantine.get("word_geometry_exposed") is not False
    ):
        raise _error("hydration source/render/quarantine binding drifted")
    with Image.open(io.BytesIO(render_raw)) as image:
        width, height = image.size
        image.verify()
    lines = envelope.get("lines")
    if type(lines) is not list or not lines:
        raise _error("hydrated line denominator is empty")
    boxes: list[list[int]] = []
    for index, line in enumerate(lines):
        if type(line) is not dict or line.get("line_index") != index:
            raise _error("hydrated line order drifted")
        boxes.append(_bbox(line.get("raw_pixel_bbox"), width, height, f"hydrated line {index}"))
    projection_raw = canonical_json_bytes_v1(envelope)
    return (
        render_raw,
        boxes,
        cast(dict[str, Any], render_binding),
        {
            "envelope_id": envelope["envelope_id"],
            "format_version": envelope["format_version"],
            "mode": "NATIVE_CANONICAL_TO_DETERMINISTIC_PIXEL_ADAPTER_V1",
            "sha256": hashlib.sha256(projection_raw).hexdigest(),
            "size_bytes": len(projection_raw),
        },
        receipt,
    )


def _terminal_polygon(
    value: Any,
    *,
    box: list[int],
    width: int,
    height: int,
    label: str,
) -> list[list[int]]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(
            type(point) is not list
            or len(point) != 2
            or any(type(coordinate) is not int for coordinate in point)
            for point in value
        )
    ):
        raise _error(f"{label} is not an exact integer quadrilateral")
    polygon = cast(list[list[int]], value)
    if any(not (0 <= point[0] <= width and 0 <= point[1] <= height) for point in polygon):
        raise _error(f"{label} lies outside render")
    if any(
        not (box[0] <= point[0] <= box[2] and box[1] <= point[1] <= box[3]) for point in polygon
    ):
        raise _error(f"{label} lies outside its provider line bbox")
    area_twice = abs(
        sum(
            polygon[index][0] * polygon[(index + 1) % 4][1]
            - polygon[(index + 1) % 4][0] * polygon[index][1]
            for index in range(4)
        )
    )
    if area_twice == 0:
        raise _error(f"{label} is degenerate")
    return [list(point) for point in polygon]


def _terminal_geometry_supplement_page(
    *,
    source_sha256: str,
    physical_page: int,
    page_record: dict[str, Any],
    result: dict[str, Any],
    result_ref: dict[str, Any],
    backend: dict[str, Any],
    backend_ref: dict[str, Any],
) -> tuple[bytes, list[list[int]], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Project every ordered provider line geometry without transcript access.

    This bounded supplement exists only because the public terminal hydration
    adapter imposes recognition-axis eligibility.  Here the denominator is the
    provider line-box axis itself; the matching polygon axis is authenticated
    and retained by hash, while recognition and word subdivisions remain
    quarantined and cannot affect selection.
    """

    if (
        page_record.get("format_version") != "BANK_CORPUS_WAVE_1_ROLE_B_FULL_PAGE_RECORD_V2"
        or page_record.get("source_sha256") != source_sha256
        or page_record.get("document_id") != f"sha256:{source_sha256}"
        or page_record.get("physical_page") != physical_page
        or page_record.get("route") != _RASTER_ROUTE
        or page_record.get("status") != _TERMINAL_STATUS
        or page_record.get("unresolved") is not True
        or page_record.get("line_axis_count") != 0
        or page_record.get("word_token_count") != 0
        or not same_typed_json_v1(page_record.get("result_ref"), result_ref)
        or not same_typed_json_v1(page_record.get("backend_payload_ref"), backend_ref)
    ):
        raise _error("terminal page record state or source binding drifted")
    if type(result) is not dict or set(result) != _TERMINAL_RESULT_FIELDS:
        raise _error("terminal result fields drifted")
    request = page_record.get("request")
    safety = result.get("safety")
    if (
        type(request) is not dict
        or result.get("format_version") != "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V3"
        or result.get("claim_boundary")
        != "SOURCE_VISIBLE_PAGE_RAW_OCR_EVIDENCE_WITH_UNRESOLVED_GEOMETRY"
        or result.get("request_sha256") != page_record.get("request_sha256")
        or not same_typed_json_v1(result.get("request"), request)
        or result.get("source_sha256") != source_sha256
        or result.get("source_size_bytes") != page_record.get("source_size_bytes")
        or result.get("physical_page") != physical_page
        or result.get("route") != _RASTER_ROUTE
        or result.get("status") != _TERMINAL_STATUS
        or result.get("provider_identity_sha256") != request.get("provider_identity_sha256")
        or result.get("render_runtime_identity_sha256")
        != request.get("render_runtime_identity_sha256")
        or not same_typed_json_v1(result.get("input_render_ref"), page_record.get("render_ref"))
        or not same_typed_json_v1(result.get("backend_payload_ref"), backend_ref)
        or result.get("lines") != []
        or result.get("words") != []
        or not same_typed_json_v1(result.get("metrics"), {"line_count": 0, "word_token_count": 0})
        or result.get("ocr_fallback_used") is not False
        or result.get("source_blank_claimed") is not False
        or type(safety) is not dict
        or set(safety) != _TERMINAL_RESULT_SAFETY_FIELDS
        or any(value is not False for value in safety.values())
    ):
        raise _error("terminal result state or source binding drifted")
    if type(backend) is not dict or set(backend) != _TERMINAL_BACKEND_FIELDS:
        raise _error("terminal backend fields drifted")
    failure = backend.get("normalization_failure")
    raw = backend.get("raw_provider_payload")
    if (
        type(failure) is not dict
        or set(failure) != _TERMINAL_FAILURE_FIELDS
        or type(raw) is not dict
        or backend.get("format_version") != "BANK_CORPUS_WAVE_1_PPOCRV6_BACKEND_PAYLOAD_V3"
        or backend.get("claim_boundary")
        != "RAW_PINNED_PROVIDER_PAYLOAD_WITH_TERMINAL_BOUNDED_WORD_BOX_GEOMETRY_FAILURE"
        or backend.get("request_sha256") != page_record.get("request_sha256")
        or not same_typed_json_v1(backend.get("request"), request)
        or backend.get("provider_identity_sha256") != request.get("provider_identity_sha256")
        or not same_typed_json_v1(backend.get("render_ref"), page_record.get("render_ref"))
        or backend.get("word_box_normalization_ledger") is not None
        or not same_typed_json_v1(failure, result.get("normalization_failure"))
        or failure.get("format_version") != "BANK_CORPUS_WAVE_1_PPOCRV6_NORMALIZATION_FAILURE_V1"
        or failure.get("status") != _TERMINAL_STATUS
        or failure.get("reason") != _TERMINAL_FAILURE_REASON
        or any(
            type(failure.get(field)) is not str or _SHA256_RE.fullmatch(failure[field]) is None
            for field in (
                "control_identity_sha256",
                "normalization_producer_implementation_ledger_sha256",
                "policy_sha256",
                "raw_payload_sha256",
            )
        )
        or failure.get("raw_payload_sha256") != canonical_json_sha256_v1(raw)
    ):
        raise _error("terminal backend/result/failure binding drifted")

    _render_path, render_raw, render_ref = _verified_ref(
        PROJECT_ROOT / V3_ROOT,
        page_record.get("render_ref"),
        f"terminal render {physical_page}",
    )
    with Image.open(io.BytesIO(render_raw)) as image:
        width, height = image.size
        image.verify()
    coordinate_authority = result.get("coordinate_authority")
    if (
        type(coordinate_authority) is not dict
        or not same_typed_json_v1(coordinate_authority.get("pixel_dimensions"), [width, height])
        or not same_typed_json_v1(failure.get("pixel_dimensions"), [width, height])
    ):
        raise _error("terminal render/coordinate dimensions drifted")

    provider_boxes = raw.get("rec_boxes")
    provider_polygons = raw.get("rec_polys")
    if (
        type(provider_boxes) is not list
        or type(provider_polygons) is not list
        or not provider_boxes
        or len(provider_boxes) != len(provider_polygons)
    ):
        raise _error("terminal provider line geometry denominator drifted")
    boxes: list[list[int]] = []
    ordered_geometry: list[dict[str, Any]] = []
    for index, (box_value, polygon_value) in enumerate(
        zip(provider_boxes, provider_polygons, strict=True)
    ):
        box = _bbox(box_value, width, height, f"terminal provider line {index}")
        polygon = _terminal_polygon(
            polygon_value,
            box=box,
            width=width,
            height=height,
            label=f"terminal provider line {index} polygon",
        )
        boxes.append(box)
        ordered_geometry.append({"rec_box": box, "rec_polygon": polygon})

    render_binding = _project_ref_to_repository(PROJECT_ROOT / V3_ROOT, render_ref)
    projected_result_ref = _project_ref_to_repository(PROJECT_ROOT / V3_ROOT, result_ref)
    projected_backend_ref = _project_ref_to_repository(PROJECT_ROOT / V3_ROOT, backend_ref)
    geometry_axis_sha256 = canonical_json_sha256_v1(ordered_geometry)
    receipt_body = {
        "claim_boundary": (
            "EXPERIMENT_LOCAL_AUTHENTICATED_PROVIDER_LINE_GEOMETRY_ONLY_"
            "NO_TEXT_WORD_NUMERIC_OR_MAPPING_AUTHORITY"
        ),
        "format_version": (
            "LOAN_MATURITY_FULL_DOCUMENT_TERMINAL_LINE_GEOMETRY_SUPPLEMENT_RECEIPT_V1"
        ),
        "geometry_binding": {
            "geometry_axis_sha256": geometry_axis_sha256,
            "provider_geometry_denominator": len(ordered_geometry),
        },
        "quarantine": {
            "provider_recognition_text_exposed": False,
            "provider_recognition_text_used_for_selection": False,
            "word_geometry_exposed": False,
            "word_text_exposed": False,
        },
        "source_binding": {
            "backend_ref": projected_backend_ref,
            "physical_page": physical_page,
            "render_ref": render_binding,
            "result_ref": projected_result_ref,
            "source_pdf_sha256": source_sha256,
            "v3_page_record_sha256": _canonical_object_sha256(page_record),
        },
        "terminal_state": {
            "public_line_axis_count": 0,
            "route": _RASTER_ROUTE,
            "status": _TERMINAL_STATUS,
            "status_preserved": True,
            "unresolved": True,
        },
        "upstream_raw_provider_payload_sha256": failure["raw_payload_sha256"],
    }
    receipt = {
        **receipt_body,
        "receipt_id": (
            f"terminal-geometry-supplement-v1:receipt:{canonical_json_sha256_v1(receipt_body)}"
        ),
    }
    receipt_raw = canonical_json_bytes_v1(receipt)
    return (
        render_raw,
        boxes,
        render_binding,
        {
            "format_version": ("LOAN_MATURITY_FULL_DOCUMENT_TERMINAL_LINE_GEOMETRY_PROJECTION_V1"),
            "geometry_axis_sha256": geometry_axis_sha256,
            "mode": "TERMINAL_EXPERIMENT_LOCAL_PROVIDER_LINE_GEOMETRY_ONLY_V1",
            "provider_geometry_denominator": len(ordered_geometry),
            "receipt_id": receipt["receipt_id"],
            "sha256": hashlib.sha256(receipt_raw).hexdigest(),
            "size_bytes": len(receipt_raw),
        },
        receipt,
    )


def validate_anonymous_reader_request_v1(payload: Any) -> list[dict[str, str]]:
    """Validate the closed reader view without consulting the private manifest."""

    if type(payload) is not dict or set(payload) != _REQUEST_FIELDS:
        raise _error("anonymous reader request fields drifted")
    manifest_ref = payload.get("crop_manifest")
    samples = payload.get("samples")
    if (
        payload.get("format_version") != 2
        or payload.get("experiment_id") != "VIETOCR_MULTI_BANK_FAMILY_OCR_BENCHMARK_V1"
        or payload.get("state") != "READY_FOR_REFERENCE_BLIND_LINE_INFERENCE"
        or payload.get("dataset_role") != "LOGIC_DEVELOPMENT_AND_CALIBRATION"
        or payload.get("evidence_role") != "INDEPENDENT_VIETNAMESE_SEMANTIC_PROPOSAL_ONLY"
        or payload.get("git_dirty") is not False
        or payload.get("reference_text_available_to_reader") is not False
        or type(payload.get("git_commit")) is not str
        or type(manifest_ref) is not dict
        or set(manifest_ref) != {"path", "sha256"}
        or type(manifest_ref.get("path")) is not str
        or _SHA256_RE.fullmatch(str(manifest_ref.get("sha256"))) is None
        or type(samples) is not list
        or len(samples) != payload.get("sample_count")
    ):
        raise _error("anonymous reader request identity or denominator drifted")
    validated: list[dict[str, str]] = []
    seen: set[str] = set()
    for offset, value in enumerate(samples, 1):
        if type(value) is not dict or set(value) != _REQUEST_SAMPLE_FIELDS:
            raise _error("anonymous reader sample fields drifted")
        sample = cast(dict[str, Any], value)
        sample_id = sample.get("sample_id")
        expected_id = f"sample-{offset:08d}"
        crop_path = sample.get("crop_path")
        if (
            sample_id != expected_id
            or _SAMPLE_ID_RE.fullmatch(str(sample_id)) is None
            or sample_id in seen
            or sample.get("category") != "FULL_DOCUMENT_AUTHENTICATED_LINE"
            or type(crop_path) is not str
            or Path(crop_path).name != f"{sample_id}.png"
            or _SHA256_RE.fullmatch(str(sample.get("crop_sha256"))) is None
        ):
            raise _error("anonymous reader sample identity/order drifted")
        path = Path(crop_path)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise _error("anonymous reader crop path is unsafe")
        seen.add(sample_id)
        validated.append({key: str(sample[key]) for key in sorted(_REQUEST_SAMPLE_FIELDS)})
    public_identifiers = [
        str(manifest_ref["path"]),
        str(payload["experiment_id"]),
        *(sample["sample_id"] for sample in validated),
        *(sample["category"] for sample in validated),
        *(sample["crop_path"] for sample in validated),
    ]
    if any(
        code.casefold() in identifier.casefold()
        for code in _EXPECTED_BANK_ORDER
        for identifier in public_identifiers
    ):
        raise _error("anonymous reader request leaks a bank identifier")
    return validated


def build_full_document_request_v1() -> dict[str, Any]:
    """Build and publish the full-document crop manifest and blind request."""

    if _git("status", "--porcelain"):
        raise _error("full-document crop freeze requires one clean Git worktree")
    git_commit = _git("rev-parse", "HEAD")
    source_tree_oid = _git("write-tree")
    destination = PROJECT_ROOT / OUTPUT_ROOT
    if destination.exists():
        raise _error(f"refusing to overwrite existing output: {destination}")
    e0044, e0044_raw = _json(PROJECT_ROOT / E0044_PATH, "E-0044 panel")
    plan, plan_raw = _json(PROJECT_ROOT / SEALED_PLAN_PATH, "sealed page-read plan")
    slots = e0044.get("slots")
    documents = plan.get("documents")
    if (
        e0044.get("bank_order") != list(_EXPECTED_BANK_ORDER)
        or type(slots) is not list
        or len(slots) != len(_EXPECTED_BANK_ORDER)
        or [slot.get("bank_code") for slot in slots if type(slot) is dict]
        != list(_EXPECTED_BANK_ORDER)
        or type(documents) is not list
    ):
        raise _error("fixed eight-document selection or sealed plan drifted")
    plan_by_sha = {item.get("sha256"): item for item in documents if type(item) is dict}
    selected_source_hashes = [slot.get("source_pdf_sha256") for slot in slots]
    if len(plan_by_sha) != len(documents) or len(set(selected_source_hashes)) != len(
        _EXPECTED_BANK_ORDER
    ):
        raise _error("sealed plan or fixed source identities are not unique")
    intended_reader = _validate_vietocr_transformer_config()
    implementation_refs = {
        "builder": _repository_file_ref(Path(__file__).resolve(), "full-document builder"),
        "reader": _repository_file_ref(PROJECT_ROOT / VIETOCR_READER_PATH, "VietOCR line reader"),
        "runner": _repository_file_ref(PROJECT_ROOT / VIETOCR_RUNNER_PATH, "VietOCR runner"),
    }

    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    try:
        crop_stage = stage / "frozen" / "crops"
        crop_stage.mkdir(parents=True)
        crop_final = destination / "frozen" / "crops"
        manifest_documents: list[dict[str, Any]] = []
        manifest_samples: list[dict[str, Any]] = []
        request_samples: list[dict[str, str]] = []
        total_line_count = 0

        for document_ordinal, slot in enumerate(slots, 1):
            if type(slot) is not dict:
                raise _error("E-0044 slot is not one object")
            source_sha = slot.get("source_pdf_sha256")
            plan_document = plan_by_sha.get(source_sha)
            if (
                type(source_sha) is not str
                or _SHA256_RE.fullmatch(source_sha) is None
                or type(plan_document) is not dict
                or plan_document.get("bank") != slot.get("bank_code")
            ):
                raise _error("selected document is absent from sealed plan")
            source_relative = Path(plan_document["relative_path"])
            if source_relative.is_absolute() or ".." in source_relative.parts:
                raise _error("selected source PDF path is unsafe")
            source_path = PROJECT_ROOT / source_relative
            source_raw = _stable_bytes(source_path, f"source PDF {document_ordinal}")
            if (
                len(source_raw) != plan_document["size_bytes"]
                or hashlib.sha256(source_raw).hexdigest() != source_sha
            ):
                raise _error("selected source PDF differs from sealed plan")
            manifest_path = PROJECT_ROOT / V3_ROOT / "documents" / f"{source_sha}.json"
            document_manifest, document_manifest_raw = _json(
                manifest_path, f"V3 document manifest {document_ordinal}"
            )
            page_records = document_manifest.get("page_records")
            if (
                document_manifest.get("source_sha256") != source_sha
                or type(page_records) is not list
                or len(page_records) != plan_document["page_count"]
                or type(plan_document.get("pages")) is not list
                or len(plan_document["pages"]) != len(page_records)
            ):
                raise _error("V3 document page denominator drifted")

            page_outputs: list[dict[str, Any]] = []
            for page_record in page_records:
                if type(page_record) is not dict:
                    raise _error("V3 page record is not one object")
                physical_page = page_record.get("physical_page")
                plan_page = plan_document["pages"][len(page_outputs)]
                if (
                    type(physical_page) is not int
                    or physical_page != len(page_outputs) + 1
                    or type(plan_page) is not dict
                    or plan_page.get("page") != physical_page
                    or plan_page.get("route") != page_record.get("route")
                    or page_record.get("source_sha256") != source_sha
                    or page_record.get("source_size_bytes") != len(source_raw)
                ):
                    raise _error("V3 physical page/source/plan sequence drifted")
                _result_path, result_raw, result_ref = _verified_ref(
                    PROJECT_ROOT / V3_ROOT,
                    page_record.get("result_ref"),
                    f"page result {document_ordinal}:{physical_page}",
                )
                _backend_path, backend_raw, backend_ref = _verified_ref(
                    PROJECT_ROOT / V3_ROOT,
                    page_record.get("backend_payload_ref"),
                    f"page backend {document_ordinal}:{physical_page}",
                )
                result = _decode_json(result_raw, f"page result {document_ordinal}:{physical_page}")
                route = page_record.get("route")
                status = page_record.get("status")
                backend = (
                    _decode_json(backend_raw, f"page backend {document_ordinal}:{physical_page}")
                    if status == _TERMINAL_STATUS
                    else None
                )
                hydration_receipt: dict[str, Any] | None = None
                if route == _NATIVE_ROUTE:
                    (
                        render_raw,
                        boxes,
                        render_binding,
                        source_projection,
                        hydration_receipt,
                    ) = _native_hydrated_page(
                        source_sha256=source_sha,
                        physical_page=physical_page,
                        page_record=page_record,
                        result=result,
                    )
                    geometry_mode = source_projection["mode"]
                    primary_line_count = page_record.get("line_axis_count")
                    supplement_line_count = 0
                elif status == _TERMINAL_STATUS:
                    (
                        render_raw,
                        boxes,
                        render_binding,
                        source_projection,
                        hydration_receipt,
                    ) = _terminal_geometry_supplement_page(
                        source_sha256=source_sha,
                        physical_page=physical_page,
                        page_record=page_record,
                        result=result,
                        result_ref=result_ref,
                        backend=cast(dict[str, Any], backend),
                        backend_ref=backend_ref,
                    )
                    geometry_mode = source_projection["mode"]
                    primary_line_count = page_record.get("line_axis_count")
                    supplement_line_count = len(boxes)
                else:
                    render_raw, boxes, render_binding, source_projection = _raster_page(
                        page_record, result
                    )
                    geometry_mode = "AUTHENTICATED_RASTER_RAW_PIXEL_PRIMARY_LINE_V2"
                    primary_line_count = len(boxes)
                    supplement_line_count = 0
                if (
                    type(primary_line_count) is not int
                    or primary_line_count < 0
                    or (status != _TERMINAL_STATUS and primary_line_count != len(boxes))
                    or (status == _TERMINAL_STATUS and primary_line_count != 0)
                ):
                    raise _error("primary/supplement line denominator drifted")

                with Image.open(io.BytesIO(render_raw)) as raw_image:
                    source_image = raw_image.convert("RGB")
                page_sample_start = len(request_samples)
                sample_ids: list[str] = []
                for line_index, box in enumerate(boxes):
                    sample_id = f"sample-{len(request_samples) + 1:08d}"
                    padded = _padded(box, source_image.width, source_image.height)
                    crop = ImageOps.expand(
                        source_image.crop(padded), border=WHITE_BORDER, fill="white"
                    )
                    crop_name = f"{sample_id}.png"
                    crop_path = crop_stage / crop_name
                    crop.save(crop_path, format="PNG", optimize=False, compress_level=6)
                    crop_raw = _stable_bytes(crop_path, f"crop {sample_id}")
                    crop_ref = {
                        "path": (crop_final / crop_name).relative_to(PROJECT_ROOT).as_posix(),
                        "sha256": hashlib.sha256(crop_raw).hexdigest(),
                        "size_bytes": len(crop_raw),
                    }
                    request_samples.append(
                        {
                            "category": "FULL_DOCUMENT_AUTHENTICATED_LINE",
                            "crop_path": crop_ref["path"],
                            "crop_sha256": crop_ref["sha256"],
                            "sample_id": sample_id,
                        }
                    )
                    manifest_samples.append(
                        {
                            "crop_ref": crop_ref,
                            "document_ordinal": document_ordinal,
                            "line_axis_role": (
                                "TERMINAL_LINE_ONLY_SUPPLEMENT"
                                if status == _TERMINAL_STATUS
                                else "PRIMARY_AUTHENTICATED_LINE"
                            ),
                            "line_index": line_index,
                            "padded_source_bbox_raw_pixels": list(padded),
                            "physical_page": physical_page,
                            "sample_id": sample_id,
                            "source_bbox_raw_pixels": list(box),
                        }
                    )
                    sample_ids.append(sample_id)
                total_line_count += len(boxes)
                page_outputs.append(
                    {
                        "backend_ref": _project_ref_to_repository(
                            PROJECT_ROOT / V3_ROOT, backend_ref
                        ),
                        "geometry_mode": geometry_mode,
                        "hydration_receipt": hydration_receipt,
                        "line_count": len(boxes),
                        "physical_page": physical_page,
                        "plan_page_projection_sha256": _canonical_object_sha256(plan_page),
                        "primary_line_count": primary_line_count,
                        "render_binding": render_binding,
                        "result_ref": _project_ref_to_repository(
                            PROJECT_ROOT / V3_ROOT, result_ref
                        ),
                        "route": route,
                        "sample_id_first": sample_ids[0] if sample_ids else None,
                        "sample_id_last": sample_ids[-1] if sample_ids else None,
                        "sample_offset_start": page_sample_start,
                        "sample_offset_stop": len(request_samples),
                        "source_projection": source_projection,
                        "status": status,
                        "supplement_line_count": supplement_line_count,
                        "terminal_status_preserved": status == _TERMINAL_STATUS,
                        "v3_page_record_sha256": _canonical_object_sha256(page_record),
                    }
                )

            manifest_documents.append(
                {
                    "bank_code": slot["bank_code"],
                    "document_manifest": {
                        "path": manifest_path.relative_to(PROJECT_ROOT).as_posix(),
                        "sha256": hashlib.sha256(document_manifest_raw).hexdigest(),
                        "size_bytes": len(document_manifest_raw),
                    },
                    "document_ordinal": document_ordinal,
                    "page_count": len(page_outputs),
                    "pages": page_outputs,
                    "plan_document_projection_sha256": _canonical_object_sha256(plan_document),
                    "source_pdf": {
                        "path": source_relative.as_posix(),
                        "sha256": source_sha,
                        "size_bytes": len(source_raw),
                    },
                }
            )

        manifest = {
            "authority": {
                "legacy_ocr_transcript_used_for_line_selection": False,
                "line_geometry_and_crop_identity_only": True,
                "mapping_authority": False,
                "numeric_authority": False,
                "ppocr_or_native_transcript_semantic_authority": False,
                "reader_request_contains_bank_page_or_text_labels": False,
                "semantic_authority": False,
                "semantic_text_source_after_run": "FRESH_VIETOCR_VGG_TRANSFORMER_0_3_13_ONLY",
                "terminal_word_geometry_or_text_exposed": False,
                "whole_document_all_line_denominator": True,
            },
            "documents": manifest_documents,
            "format_version": "LOAN_MATURITY_FULL_DOCUMENT_ALL_LINE_CROP_MANIFEST_V1",
            "git_binding": {
                "commit": git_commit,
                "dirty": False,
                "implementation_refs": implementation_refs,
                "source_tree_oid": source_tree_oid,
            },
            "input_refs": {
                "e0044": {
                    "path": E0044_PATH.as_posix(),
                    "sha256": hashlib.sha256(e0044_raw).hexdigest(),
                    "size_bytes": len(e0044_raw),
                },
                "sealed_plan": {
                    "path": SEALED_PLAN_PATH.as_posix(),
                    "sha256": hashlib.sha256(plan_raw).hexdigest(),
                    "size_bytes": len(plan_raw),
                },
            },
            "intended_reader": intended_reader,
            "metrics": {
                "document_count": len(manifest_documents),
                "line_count_vector": [
                    sum(page["line_count"] for page in item["pages"]) for item in manifest_documents
                ],
                "page_count": sum(item["page_count"] for item in manifest_documents),
                "page_count_vector": [item["page_count"] for item in manifest_documents],
                "sample_count": total_line_count,
                "terminal_page_count": sum(
                    page["terminal_status_preserved"]
                    for item in manifest_documents
                    for page in item["pages"]
                ),
            },
            "samples": manifest_samples,
            "selection_rule": {
                "line_selection": "ALL_AUTHENTICATED_LINES_NO_TEXT_FILTER",
                "source_padding_left_top_right_bottom": list(SOURCE_PADDING),
                "white_border_left_top_right_bottom": list(WHITE_BORDER),
                "deskew": False,
                "resize": False,
                "threshold": False,
                "union": False,
            },
        }
        manifest_raw = _artifact_json_bytes_v1(manifest)
        manifest_stage = stage / "crop_manifest.json"
        manifest_stage.write_bytes(manifest_raw)
        request = {
            "crop_manifest": {
                "path": (destination / "crop_manifest.json").relative_to(PROJECT_ROOT).as_posix(),
                "sha256": hashlib.sha256(manifest_raw).hexdigest(),
            },
            "dataset_role": "LOGIC_DEVELOPMENT_AND_CALIBRATION",
            "evidence_role": "INDEPENDENT_VIETNAMESE_SEMANTIC_PROPOSAL_ONLY",
            "experiment_id": "VIETOCR_MULTI_BANK_FAMILY_OCR_BENCHMARK_V1",
            "format_version": 2,
            "git_commit": git_commit,
            "git_dirty": False,
            "reference_text_available_to_reader": False,
            "sample_count": len(request_samples),
            "samples": request_samples,
            "state": "READY_FOR_REFERENCE_BLIND_LINE_INFERENCE",
        }
        validate_anonymous_reader_request_v1(request)
        request_raw = _artifact_json_bytes_v1(request)
        (stage / "request.json").write_bytes(request_raw)
        if len(manifest_samples) != total_line_count or len(request_samples) != total_line_count:
            raise _error("private/public sample denominators diverged")
        if _git("status", "--porcelain"):
            raise _error("Git worktree changed during full-document crop construction")
        if destination.exists():
            raise _error("output appeared during crop construction")
        _publish_directory_noreplace(stage, destination)
        return {
            "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
            "output_root": OUTPUT_ROOT.as_posix(),
            "page_count": manifest["metrics"]["page_count"],
            "request_sha256": hashlib.sha256(request_raw).hexdigest(),
            "sample_count": len(request_samples),
            "status": "READY_FOR_REFERENCE_BLIND_VIETOCR_TRANSFORMER",
        }
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def build_annual_2025_full_document_request_v1() -> dict[str, Any]:
    """Build the same blind VietOCR request from the audited annual-2025 corpus."""

    _activate_profile("annual-2025")
    if _git("status", "--porcelain"):
        raise _error("annual full-document crop freeze requires one clean Git worktree")
    git_commit = _git("rev-parse", "HEAD")
    source_tree_oid = _git("write-tree")
    destination = PROJECT_ROOT / OUTPUT_ROOT
    if destination.exists():
        raise _error(f"refusing to overwrite existing output: {destination}")
    geometry_selection, geometry_selection_raw = _validate_annual_geometry_selection_v1()
    if [source["bank_code"] for source in ANNUAL_2025_SOURCES] != list(_EXPECTED_BANK_ORDER) or sum(
        source["page_count"] for source in ANNUAL_2025_SOURCES
    ) != 695:
        raise _error("annual-2025 fixed source selection drifted")
    intended_reader = _validate_vietocr_transformer_config()
    implementation_refs = {
        "builder": _repository_file_ref(Path(__file__).resolve(), "full-document builder"),
        "reader": _repository_file_ref(PROJECT_ROOT / VIETOCR_READER_PATH, "VietOCR reader"),
        "runner": _repository_file_ref(PROJECT_ROOT / VIETOCR_RUNNER_PATH, "VietOCR runner"),
    }
    input_refs = {
        "geometry_selection": {
            "path": ANNUAL_2025_GEOMETRY_SELECTION_PATH.as_posix(),
            "sha256": hashlib.sha256(geometry_selection_raw).hexdigest(),
            "size_bytes": len(geometry_selection_raw),
        },
        "dataset_role_registry": _repository_file_ref(
            PROJECT_ROOT / "data/registered/dataset_roles.jsonl", "dataset-role registry"
        ),
        "source_registry": _repository_file_ref(
            PROJECT_ROOT / "data/registered/source_registry.jsonl", "source registry"
        ),
    }

    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    try:
        crop_stage = stage / "frozen" / "crops"
        crop_stage.mkdir(parents=True)
        crop_final = destination / "frozen" / "crops"
        manifest_documents: list[dict[str, Any]] = []
        manifest_samples: list[dict[str, Any]] = []
        request_samples: list[dict[str, str]] = []
        total_line_count = 0

        for document_ordinal, source in enumerate(ANNUAL_2025_SOURCES, 1):
            (
                source_raw,
                preprocess,
                preprocess_raw,
                _preprocess_envelope,
                _preprocess_envelope_raw,
                batch_root,
                batch,
                batch_raw,
                batch_pages,
                renders,
            ) = _annual_document_inputs(source, document_ordinal)
            preprocess_pages = cast(list[dict[str, Any]], preprocess["pages"])
            bank = cast(str, source["bank_code"])
            page_outputs: list[dict[str, Any]] = []
            for physical_page, (preprocess_page, batch_page, render_record) in enumerate(
                zip(preprocess_pages, batch_pages, renders, strict=True), 1
            ):
                if type(preprocess_page) is not dict:
                    raise _error(f"annual preprocess page is not an object: {bank}")
                preprocess_render = preprocess_page.get("render")
                if (
                    type(preprocess_page.get("page")) is not int
                    or preprocess_page.get("page") != physical_page
                    or type(preprocess_render) is not dict
                    or type(preprocess_render.get("page")) is not int
                    or preprocess_render.get("page") != physical_page
                    or preprocess_render.get("sha256") != render_record.get("sha256")
                    or type(preprocess_render.get("width_pixels")) is not int
                    or preprocess_render.get("width_pixels") != render_record.get("width_pixels")
                    or type(preprocess_render.get("height_pixels")) is not int
                    or preprocess_render.get("height_pixels") != render_record.get("height_pixels")
                    or type(preprocess_render.get("dpi")) is not int
                    or preprocess_render.get("dpi") != 200
                ):
                    raise _error(f"annual preprocess/batch render binding drifted: {bank}")
                (
                    render_raw,
                    boxes,
                    render_binding,
                    source_projection,
                    result_ref,
                    run_ref,
                ) = _annual_page_geometry(
                    bank=bank,
                    batch_root=batch_root,
                    batch=batch,
                    batch_page=batch_page,
                    render_record=render_record,
                    physical_page=physical_page,
                )
                with Image.open(io.BytesIO(render_raw)) as raw_image:
                    source_image = raw_image.convert("RGB")
                page_start = total_line_count
                for line_index, box in enumerate(boxes):
                    sample_id = f"sample-{total_line_count + 1:08d}"
                    padded = _padded(box, source_image.width, source_image.height)
                    crop = ImageOps.expand(
                        source_image.crop(padded), border=WHITE_BORDER, fill="white"
                    )
                    buffer = io.BytesIO()
                    crop.save(buffer, format="PNG", optimize=False, compress_level=6)
                    crop_raw = buffer.getvalue()
                    crop_name = f"{sample_id}.png"
                    crop_path = crop_stage / crop_name
                    crop_path.write_bytes(crop_raw)
                    final_path = crop_final / crop_name
                    crop_ref = {
                        "path": final_path.relative_to(PROJECT_ROOT).as_posix(),
                        "sha256": hashlib.sha256(crop_raw).hexdigest(),
                        "size_bytes": len(crop_raw),
                    }
                    manifest_samples.append(
                        {
                            "crop_ref": crop_ref,
                            "document_ordinal": document_ordinal,
                            "line_axis_role": "PRIMARY_AUTHENTICATED_LINE",
                            "line_index": line_index,
                            "padded_source_bbox_raw_pixels": list(padded),
                            "physical_page": physical_page,
                            "sample_id": sample_id,
                            "source_bbox_raw_pixels": box,
                        }
                    )
                    request_samples.append(
                        {
                            "category": "FULL_DOCUMENT_AUTHENTICATED_LINE",
                            "crop_path": crop_ref["path"],
                            "crop_sha256": crop_ref["sha256"],
                            "sample_id": sample_id,
                        }
                    )
                    total_line_count += 1
                page_outputs.append(
                    {
                        "backend_ref": run_ref,
                        "geometry_mode": source_projection["mode"],
                        "hydration_receipt": None,
                        "line_count": len(boxes),
                        "physical_page": physical_page,
                        "plan_page_projection_sha256": _canonical_object_sha256(preprocess_page),
                        "primary_line_count": len(boxes),
                        "render_binding": render_binding,
                        "result_ref": result_ref,
                        "route": _RASTER_ROUTE,
                        "sample_id_first": (f"sample-{page_start + 1:08d}" if boxes else None),
                        "sample_id_last": (f"sample-{total_line_count:08d}" if boxes else None),
                        "sample_offset_start": page_start,
                        "sample_offset_stop": total_line_count,
                        "source_projection": source_projection,
                        "status": _RASTER_STATUS,
                        "supplement_line_count": 0,
                        "terminal_status_preserved": False,
                        "v3_page_record_sha256": _canonical_object_sha256(batch_page),
                    }
                )

            manifest_documents.append(
                {
                    "bank_code": bank,
                    "document_manifest": {
                        "path": (
                            ANNUAL_2025_PREPROCESS_ROOT / source["sha256"][:20] / "manifest.json"
                        ).as_posix(),
                        "sha256": hashlib.sha256(preprocess_raw).hexdigest(),
                        "size_bytes": len(preprocess_raw),
                    },
                    "document_ordinal": document_ordinal,
                    "page_count": source["page_count"],
                    "pages": page_outputs,
                    "plan_document_projection_sha256": _canonical_object_sha256(source),
                    "source_pdf": {
                        "path": source["relative_path"],
                        "sha256": source["sha256"],
                        "size_bytes": len(source_raw),
                    },
                }
            )
            input_refs[f"ppocr_batch_{bank.casefold()}"] = {
                "path": (ANNUAL_2025_PPOCR_ROOT / bank / "batch_manifest.json").as_posix(),
                "sha256": hashlib.sha256(batch_raw).hexdigest(),
                "size_bytes": len(batch_raw),
            }

        page_count_vector = [document["page_count"] for document in manifest_documents]
        line_count_vector = [
            sum(page["line_count"] for page in document["pages"]) for document in manifest_documents
        ]
        _validate_annual_selection_denominator_v1(
            geometry_selection,
            page_count_vector=page_count_vector,
            line_count_vector=line_count_vector,
            sample_count=total_line_count,
        )
        manifest = {
            "authority": {
                "geometry_authority": "PINNED_PPOCRV6_PROVIDER_LINE_BOXES_ONLY",
                "legacy_ocr_transcript_used_for_line_selection": False,
                "mapping_authority": False,
                "numeric_authority": False,
                "ppocr_or_native_transcript_semantic_authority": False,
                "schema_authority": False,
                "semantic_authority": False,
                "semantic_text_source_after_run": "FRESH_VIETOCR_VGG_TRANSFORMER_0_3_13_ONLY",
                "terminal_word_geometry_or_text_exposed": False,
                "whole_document_all_line_denominator": True,
            },
            "documents": manifest_documents,
            "format_version": "ANNUAL_2025_8BANK_FULL_DOCUMENT_ALL_LINE_CROP_MANIFEST_V1",
            "git_binding": {
                "commit": git_commit,
                "dirty": False,
                "implementation_refs": implementation_refs,
                "source_tree_oid": source_tree_oid,
            },
            "input_refs": input_refs,
            "intended_reader": intended_reader,
            "metrics": {
                "document_count": len(manifest_documents),
                "line_count_vector": line_count_vector,
                "page_count": sum(page_count_vector),
                "page_count_vector": page_count_vector,
                "sample_count": total_line_count,
                "terminal_page_count": 0,
            },
            "samples": manifest_samples,
            "selection_rule": {
                "deskew": False,
                "line_selection": "ALL_PROVIDER_LINES_NO_TEXT_FILTER",
                "resize": False,
                "source_padding_left_top_right_bottom": list(SOURCE_PADDING),
                "threshold": False,
                "union": False,
                "white_border_left_top_right_bottom": list(WHITE_BORDER),
            },
        }
        manifest_raw = _artifact_json_bytes_v1(manifest)
        (stage / "crop_manifest.json").write_bytes(manifest_raw)
        request = {
            "crop_manifest": {
                "path": (destination / "crop_manifest.json").relative_to(PROJECT_ROOT).as_posix(),
                "sha256": hashlib.sha256(manifest_raw).hexdigest(),
            },
            "dataset_role": "LOGIC_DEVELOPMENT_AND_CALIBRATION",
            "evidence_role": "INDEPENDENT_VIETNAMESE_SEMANTIC_PROPOSAL_ONLY",
            "experiment_id": "VIETOCR_MULTI_BANK_FAMILY_OCR_BENCHMARK_V1",
            "format_version": 2,
            "git_commit": git_commit,
            "git_dirty": False,
            "reference_text_available_to_reader": False,
            "sample_count": len(request_samples),
            "samples": request_samples,
            "state": "READY_FOR_REFERENCE_BLIND_LINE_INFERENCE",
        }
        validate_anonymous_reader_request_v1(request)
        request_raw = _artifact_json_bytes_v1(request)
        (stage / "request.json").write_bytes(request_raw)
        if len(manifest_samples) != total_line_count or len(request_samples) != total_line_count:
            raise _error("annual private/public sample denominators diverged")
        if _git("status", "--porcelain"):
            raise _error("Git worktree changed during annual crop construction")
        if destination.exists():
            raise _error("annual output appeared during crop construction")
        _publish_directory_noreplace(stage, destination)
        return {
            "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
            "output_root": OUTPUT_ROOT.as_posix(),
            "page_count": 695,
            "request_sha256": hashlib.sha256(request_raw).hexdigest(),
            "sample_count": total_line_count,
            "status": "READY_FOR_REFERENCE_BLIND_VIETOCR_TRANSFORMER",
        }
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def _verify_canonical_json_file(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    value, raw = _json(path, label)
    if _artifact_json_bytes_v1(value) != raw:
        raise _error(f"{label} does not have the exact profile JSON framing")
    return value, raw


def _validate_content_ref(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _REF_FIELDS:
        raise _error(f"{label} content reference fields drifted")
    reference = cast(dict[str, Any], value)
    path_value = reference.get("path")
    if (
        type(path_value) is not str
        or Path(path_value).is_absolute()
        or ".." in Path(path_value).parts
        or type(reference.get("size_bytes")) is not int
        or reference["size_bytes"] < 0
    ):
        raise _error(f"{label} content reference identity drifted")
    _sha256(reference.get("sha256"), f"{label} hash")
    return reference


def _verify_repository_content_ref(value: Any, label: str) -> bytes:
    reference = _validate_content_ref(value, label)
    path = PROJECT_ROOT / reference["path"]
    raw = _stable_bytes(path, label)
    if (
        len(raw) != reference["size_bytes"]
        or hashlib.sha256(raw).hexdigest() != reference["sha256"]
    ):
        raise _error(f"{label} bytes drifted")
    return raw


def _load_frozen_artifacts_v1() -> tuple[dict[str, Any], bytes, dict[str, Any], bytes]:
    manifest, manifest_raw = _verify_canonical_json_file(
        PROJECT_ROOT / OUTPUT_ROOT / "crop_manifest.json", "full-document crop manifest"
    )
    request, request_raw = _verify_canonical_json_file(
        PROJECT_ROOT / OUTPUT_ROOT / "request.json", "full-document reader request"
    )
    validate_anonymous_reader_request_v1(request)
    manifest_ref = request["crop_manifest"]
    if (
        manifest_ref["path"] != (OUTPUT_ROOT / "crop_manifest.json").as_posix()
        or manifest_ref["sha256"] != hashlib.sha256(manifest_raw).hexdigest()
    ):
        raise _error("reader request does not bind the exact private crop manifest")
    return manifest, manifest_raw, request, request_raw


def verify_full_document_freeze_v1(*, replay_geometry: bool = False) -> dict[str, Any]:
    """Verify the complete eight-document page/line/crop denominator.

    ``replay_geometry=True`` replays all sealed source geometry and every crop.
    It is intentionally a clean-worktree gate because native and terminal
    hydration authority is live and replay-only.
    """

    manifest, manifest_raw, request, request_raw = _load_frozen_artifacts_v1()
    if type(manifest) is not dict or set(manifest) != _MANIFEST_FIELDS:
        raise _error("private crop manifest fields drifted")
    if manifest.get("format_version") != "LOAN_MATURITY_FULL_DOCUMENT_ALL_LINE_CROP_MANIFEST_V1":
        raise _error("private crop manifest identity drifted")
    authority = manifest.get("authority")
    intended_reader = manifest.get("intended_reader")
    metrics = manifest.get("metrics")
    documents = manifest.get("documents")
    samples = manifest.get("samples")
    if (
        type(authority) is not dict
        or authority.get("legacy_ocr_transcript_used_for_line_selection") is not False
        or authority.get("ppocr_or_native_transcript_semantic_authority") is not False
        or authority.get("whole_document_all_line_denominator") is not True
        or authority.get("terminal_word_geometry_or_text_exposed") is not False
        or authority.get("semantic_text_source_after_run")
        != "FRESH_VIETOCR_VGG_TRANSFORMER_0_3_13_ONLY"
        or intended_reader != _validate_vietocr_transformer_config()
        or type(metrics) is not dict
        or type(documents) is not list
        or type(samples) is not list
        or len(documents) != len(_EXPECTED_BANK_ORDER)
        or len(samples) != request["sample_count"]
    ):
        raise _error("private crop manifest authority/reader/denominator drifted")
    for name, expected_path in (
        ("e0044", E0044_PATH),
        ("sealed_plan", SEALED_PLAN_PATH),
    ):
        reference = manifest.get("input_refs", {}).get(name)
        if type(reference) is not dict or reference.get("path") != expected_path.as_posix():
            raise _error(f"private manifest {name} input binding drifted")
        _verify_repository_content_ref(reference, f"private manifest {name}")
    git_binding = manifest.get("git_binding")
    if type(git_binding) is not dict or git_binding.get("dirty") is not False:
        raise _error("private manifest Git binding drifted")
    implementation_refs = git_binding.get("implementation_refs")
    if type(implementation_refs) is not dict or set(implementation_refs) != {
        "builder",
        "reader",
        "runner",
    }:
        raise _error("private manifest implementation ledger drifted")
    for name, reference in implementation_refs.items():
        _verify_repository_content_ref(reference, f"private manifest {name} implementation")

    e0044, _e0044_raw = _json(PROJECT_ROOT / E0044_PATH, "replay E-0044 panel")
    plan, _plan_raw = _json(PROJECT_ROOT / SEALED_PLAN_PATH, "replay sealed plan")
    slots = e0044.get("slots")
    plan_documents = plan.get("documents")
    if type(slots) is not list or type(plan_documents) is not list:
        raise _error("replay input axes drifted")
    plan_by_sha = {value.get("sha256"): value for value in plan_documents if type(value) is dict}
    expected_crop_names: list[str] = []
    request_samples = request["samples"]
    cursor = 0
    page_count_vector: list[int] = []
    line_count_vector: list[int] = []
    terminal_page_count = 0
    for document_offset, document_value in enumerate(documents, 1):
        if type(document_value) is not dict or set(document_value) != _MANIFEST_DOCUMENT_FIELDS:
            raise _error("private manifest document fields drifted")
        document = cast(dict[str, Any], document_value)
        slot = slots[document_offset - 1]
        if type(slot) is not dict:
            raise _error("replay E-0044 slot drifted")
        source_ref = _validate_content_ref(document.get("source_pdf"), "source PDF")
        source_sha = source_ref["sha256"]
        plan_document = plan_by_sha.get(source_sha)
        pages = document.get("pages")
        if (
            document.get("document_ordinal") != document_offset
            or document.get("bank_code") != _EXPECTED_BANK_ORDER[document_offset - 1]
            or slot.get("bank_code") != document.get("bank_code")
            or slot.get("source_pdf_sha256") != source_sha
            or type(plan_document) is not dict
            or document.get("plan_document_projection_sha256")
            != _canonical_object_sha256(plan_document)
            or type(pages) is not list
            or len(pages) != document.get("page_count")
            or len(pages) != plan_document.get("page_count")
        ):
            raise _error("private manifest document binding/page denominator drifted")
        _verify_repository_content_ref(source_ref, f"source PDF {document_offset}")
        document_manifest_ref = document.get("document_manifest")
        document_manifest_raw = _verify_repository_content_ref(
            document_manifest_ref, f"V3 document manifest {document_offset}"
        )
        document_manifest = _decode_json(
            document_manifest_raw, f"V3 document manifest {document_offset}"
        )
        page_records = document_manifest.get("page_records")
        if type(page_records) is not list or len(page_records) != len(pages):
            raise _error("V3/private page denominator drifted")
        page_count_vector.append(len(pages))
        document_line_count = 0
        for page_offset, page_value in enumerate(pages, 1):
            if type(page_value) is not dict or set(page_value) != _MANIFEST_PAGE_FIELDS:
                raise _error("private manifest page fields drifted")
            page = cast(dict[str, Any], page_value)
            page_record = page_records[page_offset - 1]
            plan_page = plan_document["pages"][page_offset - 1]
            if type(page_record) is not dict:
                raise _error("V3 replay page record is not one object")
            expected_result_ref = _project_ref_to_repository(
                PROJECT_ROOT / V3_ROOT, page_record["result_ref"]
            )
            expected_backend_ref = _project_ref_to_repository(
                PROJECT_ROOT / V3_ROOT, page_record["backend_payload_ref"]
            )
            if (
                page.get("physical_page") != page_offset
                or page.get("sample_offset_start") != cursor
                or type(page.get("line_count")) is not int
                or page["line_count"] < 0
                or page.get("sample_offset_stop") != cursor + page["line_count"]
                or page.get("v3_page_record_sha256") != _canonical_object_sha256(page_record)
                or page.get("plan_page_projection_sha256") != _canonical_object_sha256(plan_page)
                or page.get("route") != page_record.get("route")
                or page.get("status") != page_record.get("status")
                or not same_typed_json_v1(page.get("result_ref"), expected_result_ref)
                or not same_typed_json_v1(page.get("backend_ref"), expected_backend_ref)
                or page.get("terminal_status_preserved")
                is not (page_record.get("status") == _TERMINAL_STATUS)
            ):
                raise _error("private manifest page/order/source binding drifted")
            result_raw = _verify_repository_content_ref(
                page.get("result_ref"), f"page result {document_offset}:{page_offset}"
            )
            backend_raw = _verify_repository_content_ref(
                page.get("backend_ref"), f"page backend {document_offset}:{page_offset}"
            )
            result = _decode_json(result_raw, f"page result {document_offset}:{page_offset}")
            backend = (
                _decode_json(backend_raw, f"page backend {document_offset}:{page_offset}")
                if page_record.get("status") == _TERMINAL_STATUS
                else None
            )
            if result.get("status") != page.get("status"):
                raise _error("private manifest/result status drifted")
            page_samples = samples[cursor : cursor + page["line_count"]]
            if page.get("sample_id_first") != (
                page_samples[0].get("sample_id") if page_samples else None
            ) or page.get("sample_id_last") != (
                page_samples[-1].get("sample_id") if page_samples else None
            ):
                raise _error("private manifest page sample endpoints drifted")
            for line_index, sample_value in enumerate(page_samples):
                if type(sample_value) is not dict or set(sample_value) != _MANIFEST_SAMPLE_FIELDS:
                    raise _error("private manifest sample fields drifted")
                sample = cast(dict[str, Any], sample_value)
                public_sample = request_samples[cursor + line_index]
                expected_id = f"sample-{cursor + line_index + 1:08d}"
                crop_ref = _validate_content_ref(sample.get("crop_ref"), "private crop")
                expected_role = (
                    "TERMINAL_LINE_ONLY_SUPPLEMENT"
                    if page["status"] == _TERMINAL_STATUS
                    else "PRIMARY_AUTHENTICATED_LINE"
                )
                if (
                    sample.get("sample_id") != expected_id
                    or sample.get("document_ordinal") != document_offset
                    or sample.get("physical_page") != page_offset
                    or sample.get("line_index") != line_index
                    or sample.get("line_axis_role") != expected_role
                    or public_sample.get("sample_id") != expected_id
                    or public_sample.get("crop_path") != crop_ref["path"]
                    or public_sample.get("crop_sha256") != crop_ref["sha256"]
                ):
                    raise _error("private/public sample correspondence drifted")
                _bbox(
                    sample.get("source_bbox_raw_pixels"),
                    10**9,
                    10**9,
                    f"private source bbox {expected_id}",
                )
                _bbox(
                    sample.get("padded_source_bbox_raw_pixels"),
                    10**9,
                    10**9,
                    f"private padded bbox {expected_id}",
                )
                _verify_repository_content_ref(crop_ref, f"crop {expected_id}")
                expected_crop_names.append(Path(crop_ref["path"]).name)

            if replay_geometry:
                if page["route"] == _NATIVE_ROUTE:
                    (
                        render_raw,
                        boxes,
                        render_binding,
                        source_projection,
                        hydration_receipt,
                    ) = _native_hydrated_page(
                        source_sha256=source_sha,
                        physical_page=page_offset,
                        page_record=page_record,
                        result=result,
                    )
                    if hydration_receipt != page.get("hydration_receipt"):
                        raise _error("hydration receipt changed during full replay")
                elif page["status"] == _TERMINAL_STATUS:
                    (
                        render_raw,
                        boxes,
                        render_binding,
                        source_projection,
                        hydration_receipt,
                    ) = _terminal_geometry_supplement_page(
                        source_sha256=source_sha,
                        physical_page=page_offset,
                        page_record=page_record,
                        result=result,
                        result_ref=page_record["result_ref"],
                        backend=cast(dict[str, Any], backend),
                        backend_ref=page_record["backend_payload_ref"],
                    )
                    if hydration_receipt != page.get("hydration_receipt"):
                        raise _error("terminal geometry receipt changed during full replay")
                else:
                    render_raw, boxes, render_binding, source_projection = _raster_page(
                        page_record, result
                    )
                    hydration_receipt = None
                if (
                    boxes != [sample["source_bbox_raw_pixels"] for sample in page_samples]
                    or render_binding != page.get("render_binding")
                    or source_projection != page.get("source_projection")
                    or hydration_receipt != page.get("hydration_receipt")
                ):
                    raise _error("source geometry/render/projection changed during full replay")
                with Image.open(io.BytesIO(render_raw)) as raw_image:
                    source_image = raw_image.convert("RGB")
                for sample, box in zip(page_samples, boxes, strict=True):
                    padded = _padded(box, source_image.width, source_image.height)
                    if list(padded) != sample["padded_source_bbox_raw_pixels"]:
                        raise _error("padded source bbox changed during full replay")
                    crop = ImageOps.expand(
                        source_image.crop(padded), border=WHITE_BORDER, fill="white"
                    )
                    buffer = io.BytesIO()
                    crop.save(buffer, format="PNG", optimize=False, compress_level=6)
                    crop_raw = buffer.getvalue()
                    if (
                        len(crop_raw) != sample["crop_ref"]["size_bytes"]
                        or hashlib.sha256(crop_raw).hexdigest() != sample["crop_ref"]["sha256"]
                    ):
                        raise _error("crop bytes changed during full source replay")

            cursor += page["line_count"]
            document_line_count += page["line_count"]
            terminal_page_count += int(page["terminal_status_preserved"])
        line_count_vector.append(document_line_count)

    crop_directory = PROJECT_ROOT / OUTPUT_ROOT / "frozen" / "crops"
    actual_crop_names = sorted(path.name for path in crop_directory.iterdir() if path.is_file())
    if actual_crop_names != sorted(expected_crop_names):
        raise _error("crop directory contains a missing or extra file")
    expected_metrics = {
        "document_count": len(_EXPECTED_BANK_ORDER),
        "line_count_vector": line_count_vector,
        "page_count": sum(page_count_vector),
        "page_count_vector": page_count_vector,
        "sample_count": cursor,
        "terminal_page_count": terminal_page_count,
    }
    if cursor != len(samples) or metrics != expected_metrics:
        raise _error("whole-document manifest metrics drifted")
    return {
        "document_count": len(documents),
        "line_count_vector": line_count_vector,
        "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "page_count": sum(page_count_vector),
        "page_count_vector": page_count_vector,
        "replay_geometry": replay_geometry,
        "request_sha256": hashlib.sha256(request_raw).hexdigest(),
        "sample_count": cursor,
        "status": "VERIFIED_FULL_DOCUMENT_VIETOCR_FREEZE",
        "terminal_page_count": terminal_page_count,
    }


def verify_annual_2025_full_document_freeze_v1(*, replay_geometry: bool = False) -> dict[str, Any]:
    """Replay the annual-2025 profile without consulting provider transcripts."""

    _activate_profile("annual-2025")
    manifest, manifest_raw, request, request_raw = _load_frozen_artifacts_v1()
    if type(manifest) is not dict or set(manifest) != _MANIFEST_FIELDS:
        raise _error("annual private crop manifest fields drifted")
    if (
        manifest.get("format_version")
        != "ANNUAL_2025_8BANK_FULL_DOCUMENT_ALL_LINE_CROP_MANIFEST_V1"
    ):
        raise _error("annual private crop manifest identity drifted")
    authority = manifest.get("authority")
    documents = manifest.get("documents")
    samples = manifest.get("samples")
    metrics = manifest.get("metrics")
    if (
        type(authority) is not dict
        or authority.get("legacy_ocr_transcript_used_for_line_selection") is not False
        or authority.get("ppocr_or_native_transcript_semantic_authority") is not False
        or authority.get("whole_document_all_line_denominator") is not True
        or authority.get("semantic_text_source_after_run")
        != "FRESH_VIETOCR_VGG_TRANSFORMER_0_3_13_ONLY"
        or manifest.get("intended_reader") != _validate_vietocr_transformer_config()
        or type(documents) is not list
        or type(samples) is not list
        or type(metrics) is not dict
        or len(documents) != len(ANNUAL_2025_SOURCES)
        or len(samples) != request["sample_count"]
    ):
        raise _error("annual manifest authority/reader/denominator drifted")
    input_refs = manifest.get("input_refs")
    expected_input_names = {
        "dataset_role_registry",
        "geometry_selection",
        "source_registry",
        *(f"ppocr_batch_{source['bank_code'].casefold()}" for source in ANNUAL_2025_SOURCES),
    }
    if type(input_refs) is not dict or set(input_refs) != expected_input_names:
        raise _error("annual manifest input ledger drifted")
    selection, selection_raw = _validate_annual_geometry_selection_v1()
    if not same_typed_json_v1(
        input_refs.get("geometry_selection"),
        {
            "path": ANNUAL_2025_GEOMETRY_SELECTION_PATH.as_posix(),
            "sha256": hashlib.sha256(selection_raw).hexdigest(),
            "size_bytes": len(selection_raw),
        },
    ):
        raise _error("annual manifest geometry selection binding drifted")
    for name, reference in input_refs.items():
        _verify_repository_content_ref(reference, f"annual manifest input {name}")
    git_binding = manifest.get("git_binding")
    implementation_refs = (
        git_binding.get("implementation_refs") if type(git_binding) is dict else None
    )
    if (
        type(git_binding) is not dict
        or git_binding.get("dirty") is not False
        or type(implementation_refs) is not dict
        or set(implementation_refs) != {"builder", "reader", "runner"}
    ):
        raise _error("annual manifest Git/implementation ledger drifted")
    for name, reference in implementation_refs.items():
        _verify_repository_content_ref(reference, f"annual {name} implementation")

    request_samples = request["samples"]
    cursor = 0
    page_count_vector: list[int] = []
    line_count_vector: list[int] = []
    expected_crop_names: list[str] = []
    for document_ordinal, (source, document_value) in enumerate(
        zip(ANNUAL_2025_SOURCES, documents, strict=True), 1
    ):
        if type(document_value) is not dict or set(document_value) != _MANIFEST_DOCUMENT_FIELDS:
            raise _error("annual private manifest document fields drifted")
        document = cast(dict[str, Any], document_value)
        (
            _source_raw,
            preprocess,
            preprocess_raw,
            _preprocess_envelope,
            _preprocess_envelope_raw,
            batch_root,
            batch,
            _batch_raw,
            batch_pages,
            renders,
        ) = _annual_document_inputs(source, document_ordinal)
        pages = document.get("pages")
        expected_source_ref = {
            "path": source["relative_path"],
            "sha256": source["sha256"],
            "size_bytes": source["size_bytes"],
        }
        expected_manifest_ref = {
            "path": (
                ANNUAL_2025_PREPROCESS_ROOT / source["sha256"][:20] / "manifest.json"
            ).as_posix(),
            "sha256": hashlib.sha256(preprocess_raw).hexdigest(),
            "size_bytes": len(preprocess_raw),
        }
        if (
            document.get("document_ordinal") != document_ordinal
            or document.get("bank_code") != source["bank_code"]
            or document.get("page_count") != source["page_count"]
            or document.get("plan_document_projection_sha256") != _canonical_object_sha256(source)
            or not same_typed_json_v1(document.get("source_pdf"), expected_source_ref)
            or not same_typed_json_v1(document.get("document_manifest"), expected_manifest_ref)
            or type(pages) is not list
            or len(pages) != source["page_count"]
        ):
            raise _error("annual document source/page binding drifted")
        _verify_repository_content_ref(expected_source_ref, f"annual source {source['bank_code']}")
        _verify_repository_content_ref(
            expected_manifest_ref, f"annual preprocess {source['bank_code']}"
        )
        preprocess_pages = cast(list[dict[str, Any]], preprocess["pages"])
        page_count_vector.append(len(pages))
        document_line_count = 0
        for physical_page, (page_value, preprocess_page, batch_page, render_record) in enumerate(
            zip(pages, preprocess_pages, batch_pages, renders, strict=True), 1
        ):
            if type(page_value) is not dict or set(page_value) != _MANIFEST_PAGE_FIELDS:
                raise _error("annual private manifest page fields drifted")
            page = cast(dict[str, Any], page_value)
            (
                render_raw,
                boxes,
                render_binding,
                source_projection,
                result_ref,
                run_ref,
            ) = _annual_page_geometry(
                bank=cast(str, source["bank_code"]),
                batch_root=batch_root,
                batch=batch,
                batch_page=batch_page,
                render_record=render_record,
                physical_page=physical_page,
            )
            line_count = len(boxes)
            if (
                page.get("physical_page") != physical_page
                or page.get("sample_offset_start") != cursor
                or page.get("sample_offset_stop") != cursor + line_count
                or page.get("line_count") != line_count
                or page.get("primary_line_count") != line_count
                or page.get("supplement_line_count") != 0
                or page.get("terminal_status_preserved") is not False
                or page.get("route") != _RASTER_ROUTE
                or page.get("status") != _RASTER_STATUS
                or page.get("geometry_mode") != source_projection["mode"]
                or page.get("hydration_receipt") is not None
                or page.get("plan_page_projection_sha256")
                != _canonical_object_sha256(preprocess_page)
                or page.get("v3_page_record_sha256") != _canonical_object_sha256(batch_page)
                or not same_typed_json_v1(page.get("render_binding"), render_binding)
                or not same_typed_json_v1(page.get("result_ref"), result_ref)
                or not same_typed_json_v1(page.get("backend_ref"), run_ref)
                or not same_typed_json_v1(page.get("source_projection"), source_projection)
            ):
                raise _error("annual page/order/provider binding drifted")
            page_samples = samples[cursor : cursor + line_count]
            if page.get("sample_id_first") != (
                page_samples[0].get("sample_id") if page_samples else None
            ) or page.get("sample_id_last") != (
                page_samples[-1].get("sample_id") if page_samples else None
            ):
                raise _error("annual page sample endpoints drifted")
            with Image.open(io.BytesIO(render_raw)) as raw_image:
                source_image = raw_image.convert("RGB")
            for line_index, (sample_value, box) in enumerate(zip(page_samples, boxes, strict=True)):
                if type(sample_value) is not dict or set(sample_value) != _MANIFEST_SAMPLE_FIELDS:
                    raise _error("annual private manifest sample fields drifted")
                sample = cast(dict[str, Any], sample_value)
                public_sample = request_samples[cursor + line_index]
                expected_id = f"sample-{cursor + line_index + 1:08d}"
                crop_ref = _validate_content_ref(sample.get("crop_ref"), "annual crop")
                padded = _padded(box, source_image.width, source_image.height)
                if (
                    sample.get("sample_id") != expected_id
                    or sample.get("document_ordinal") != document_ordinal
                    or sample.get("physical_page") != physical_page
                    or sample.get("line_index") != line_index
                    or sample.get("line_axis_role") != "PRIMARY_AUTHENTICATED_LINE"
                    or sample.get("source_bbox_raw_pixels") != box
                    or sample.get("padded_source_bbox_raw_pixels") != list(padded)
                    or public_sample.get("sample_id") != expected_id
                    or public_sample.get("crop_path") != crop_ref["path"]
                    or public_sample.get("crop_sha256") != crop_ref["sha256"]
                ):
                    raise _error("annual private/public sample correspondence drifted")
                crop_raw = _verify_repository_content_ref(crop_ref, f"annual crop {expected_id}")
                expected_crop_names.append(Path(crop_ref["path"]).name)
                if replay_geometry:
                    crop = ImageOps.expand(
                        source_image.crop(padded), border=WHITE_BORDER, fill="white"
                    )
                    buffer = io.BytesIO()
                    crop.save(buffer, format="PNG", optimize=False, compress_level=6)
                    if buffer.getvalue() != crop_raw:
                        raise _error("annual crop bytes changed during full source replay")
            cursor += line_count
            document_line_count += line_count
        line_count_vector.append(document_line_count)

    crop_directory = PROJECT_ROOT / OUTPUT_ROOT / "frozen" / "crops"
    actual_crop_names = sorted(path.name for path in crop_directory.iterdir() if path.is_file())
    if actual_crop_names != sorted(expected_crop_names):
        raise _error("annual crop directory contains a missing or extra file")
    expected_metrics = {
        "document_count": len(ANNUAL_2025_SOURCES),
        "line_count_vector": line_count_vector,
        "page_count": sum(page_count_vector),
        "page_count_vector": page_count_vector,
        "sample_count": cursor,
        "terminal_page_count": 0,
    }
    _validate_annual_selection_denominator_v1(
        selection,
        page_count_vector=page_count_vector,
        line_count_vector=line_count_vector,
        sample_count=cursor,
    )
    if cursor != len(samples) or metrics != expected_metrics:
        raise _error("annual whole-document metrics drifted")
    return {
        "document_count": len(documents),
        "line_count_vector": line_count_vector,
        "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "page_count": sum(page_count_vector),
        "page_count_vector": page_count_vector,
        "replay_geometry": replay_geometry,
        "request_sha256": hashlib.sha256(request_raw).hexdigest(),
        "sample_count": cursor,
        "status": "VERIFIED_ANNUAL_2025_FULL_DOCUMENT_VIETOCR_FREEZE",
        "terminal_page_count": 0,
    }


def _verify_active_full_document_freeze_v1(*, replay_geometry: bool) -> dict[str, Any]:
    if _ACTIVE_PROFILE == "annual-2025":
        return verify_annual_2025_full_document_freeze_v1(replay_geometry=replay_geometry)
    return verify_full_document_freeze_v1(replay_geometry=replay_geometry)


def _validate_completed_vietocr_result_v1(
    request: dict[str, Any], result: Any
) -> list[dict[str, Any]]:
    if type(result) is not dict or set(result) != _RESULT_FIELDS:
        raise _error("completed VietOCR result fields drifted")
    result = cast(dict[str, Any], result)
    result_samples = result.get("samples")
    request_samples = request["samples"]
    if (
        result.get("format_version") != request.get("format_version")
        or result.get("experiment_id") != request.get("experiment_id")
        or result.get("state") != "REFERENCE_BLIND_LINE_INFERENCE_COMPLETE"
        or result.get("dataset_role") != request.get("dataset_role")
        or result.get("evidence_role") != request.get("evidence_role")
        or result.get("reference_text_available_to_reader") is not False
        or type(result_samples) is not list
        or result.get("sample_count") != request.get("sample_count")
        or len(result_samples) != len(request_samples)
    ):
        raise _error("completed VietOCR result identity/denominator drifted")
    validated: list[dict[str, Any]] = []
    for offset, (request_sample, result_value) in enumerate(
        zip(request_samples, result_samples, strict=True), 1
    ):
        if type(result_value) is not dict or set(result_value) != _RESULT_SAMPLE_FIELDS:
            raise _error("completed VietOCR sample fields drifted")
        sample = cast(dict[str, Any], result_value)
        probability = sample.get("mean_decoded_character_probability")
        wall_seconds = sample.get("wall_seconds")
        if (
            sample.get("sample_id") != request_sample.get("sample_id")
            or sample.get("category") != request_sample.get("category")
            or sample.get("crop_path") != request_sample.get("crop_path")
            or sample.get("crop_sha256") != request_sample.get("crop_sha256")
            or sample.get("sample_id") != f"sample-{offset:08d}"
            or type(sample.get("raw_prediction")) is not str
            or type(sample.get("processed_width")) is not int
            or sample["processed_width"] <= 0
            or type(sample.get("processed_height")) is not int
            or sample["processed_height"] <= 0
            or (
                probability is not None
                and (
                    type(probability) not in {int, float}
                    or not math.isfinite(float(probability))
                    or not 0.0 <= float(probability) <= 1.0
                )
            )
            or type(wall_seconds) not in {int, float}
            or not math.isfinite(float(wall_seconds))
            or float(wall_seconds) < 0.0
        ):
            raise _error("completed VietOCR sample order/content drifted")
        # Do not discard empty strings: exact request order is the contract.
        validated.append(sample)
    return validated


def _load_verified_completed_vietocr_v1() -> tuple[
    dict[str, Any],
    bytes,
    dict[str, Any],
    bytes,
    dict[str, Any],
    bytes,
    dict[str, Any],
    bytes,
]:
    manifest, manifest_raw, request, request_raw = _load_frozen_artifacts_v1()
    result, result_raw = _json(
        PROJECT_ROOT / VIETOCR_OUTPUT_DIRECTORY / "ocr_result.json",
        "completed VietOCR result",
    )
    run_manifest, run_manifest_raw = _json(
        PROJECT_ROOT / VIETOCR_OUTPUT_DIRECTORY / "run_manifest.json",
        "completed VietOCR run manifest",
    )
    _validate_completed_vietocr_result_v1(request, result)
    request_ref = run_manifest.get("request")
    configuration = run_manifest.get("configuration")
    artifacts = run_manifest.get("artifacts")
    runtime = run_manifest.get("runtime")
    safety = run_manifest.get("safety")
    intended_reader = manifest["intended_reader"]
    if (
        run_manifest.get("format_version") != request["format_version"]
        or run_manifest.get("experiment_id") != request["experiment_id"]
        or run_manifest.get("state") != "REFERENCE_BLIND_LINE_INFERENCE_COMPLETE"
        or run_manifest.get("git_commit") != request["git_commit"]
        or run_manifest.get("git_dirty") is not False
        or type(request_ref) is not dict
        or request_ref.get("path") != (OUTPUT_ROOT / "request.json").as_posix()
        or request_ref.get("sha256") != hashlib.sha256(request_raw).hexdigest()
        or type(configuration) is not dict
        or configuration.get("path") != VIETOCR_CONFIG_PATH.as_posix()
        or configuration.get("sha256") != intended_reader["config_ref"]["sha256"]
        or configuration.get("network_policy") != "PROCESS_SOCKET_CONNECT_AND_DNS_DENIED"
        or configuration.get("cnn_pretrained_download") is not False
        or configuration.get("beam_search") is not False
        or configuration.get("reference_text_available_to_decoder") is not False
        or type(runtime) is not dict
        or runtime.get("packages", {}).get("vietocr") != "0.3.13"
        or runtime.get("artifacts", {}).get("weights", {}).get("sha256")
        != intended_reader["weights_sha256"]
        or type(safety) is not dict
        or not safety
        or any(bool(value) for value in safety.values())
        or type(artifacts) is not dict
        or set(artifacts) != {"ocr_result"}
        or artifacts["ocr_result"].get("path") != "ocr_result.json"
        or artifacts["ocr_result"].get("size_bytes") != len(result_raw)
        or artifacts["ocr_result"].get("sha256") != hashlib.sha256(result_raw).hexdigest()
        or run_manifest.get("metrics", {}).get("sample_count") != request["sample_count"]
    ):
        raise _error("completed VietOCR run/runtime/model binding drifted")
    return (
        manifest,
        manifest_raw,
        request,
        request_raw,
        result,
        result_raw,
        run_manifest,
        run_manifest_raw,
    )


def read_verified_vietocr_proposals_v1() -> dict[str, Any]:
    """Return every fresh VietOCR proposal in exact document/page/line order.

    The returned index is the matcher-facing API.  It contains all lines,
    including predictions equal to the empty string, and never exposes an
    older PP-OCR/native transcript as semantic text.
    """

    _verify_active_full_document_freeze_v1(replay_geometry=False)
    (
        manifest,
        manifest_raw,
        request,
        request_raw,
        result,
        result_raw,
        run_manifest,
        run_manifest_raw,
    ) = _load_verified_completed_vietocr_v1()
    result_samples = _validate_completed_vietocr_result_v1(request, result)
    private_samples = manifest["samples"]
    indexed_documents: list[dict[str, Any]] = []
    ordered_semantics: list[dict[str, str]] = []
    for document in manifest["documents"]:
        indexed_pages: list[dict[str, Any]] = []
        for page in document["pages"]:
            start = page["sample_offset_start"]
            stop = page["sample_offset_stop"]
            lines: list[dict[str, Any]] = []
            for private, proposal in zip(
                private_samples[start:stop], result_samples[start:stop], strict=True
            ):
                if private["sample_id"] != proposal["sample_id"]:
                    raise _error("private geometry and VietOCR proposal order diverged")
                text = proposal["raw_prediction"]
                ordered_semantics.append({"sample_id": proposal["sample_id"], "vietocr_text": text})
                lines.append(
                    {
                        "crop_ref": private["crop_ref"],
                        "line_axis_role": private["line_axis_role"],
                        "mean_decoded_character_probability": proposal[
                            "mean_decoded_character_probability"
                        ],
                        "padded_source_bbox_raw_pixels": private["padded_source_bbox_raw_pixels"],
                        "processed_height": proposal["processed_height"],
                        "processed_width": proposal["processed_width"],
                        "sample_id": proposal["sample_id"],
                        "source_bbox_raw_pixels": private["source_bbox_raw_pixels"],
                        "source_line_index": private["line_index"],
                        "vietocr_text": text,
                    }
                )
            indexed_pages.append(
                {
                    "geometry_mode": page["geometry_mode"],
                    "line_count": page["line_count"],
                    "lines": lines,
                    "physical_page": page["physical_page"],
                    "route": page["route"],
                    "source_projection": page["source_projection"],
                    "terminal_status_preserved": page["terminal_status_preserved"],
                    "upstream_status": page["status"],
                }
            )
        indexed_documents.append(
            {
                "bank_code": document["bank_code"],
                "document_ordinal": document["document_ordinal"],
                "page_count": document["page_count"],
                "pages": indexed_pages,
                "source_pdf": document["source_pdf"],
            }
        )
    semantic_axis_raw = canonical_json_bytes_v1(ordered_semantics)
    return {
        "authority": {
            "all_empty_predictions_preserved": True,
            "geometry_authority": False,
            "mapping_authority": False,
            "numeric_authority": False,
            "old_ppocr_or_native_transcript_used_as_semantic_text": False,
            "ordered_semantic_proposal_authority": True,
            "semantic_text_source": "FRESH_VIETOCR_VGG_TRANSFORMER_0_3_13",
        },
        "documents": indexed_documents,
        "format_version": (
            "ANNUAL_2025_8DOCUMENT_VIETOCR_TRANSFORMER_SEMANTIC_INDEX_V1"
            if _ACTIVE_PROFILE == "annual-2025"
            else "WAVE1_8DOCUMENT_VIETOCR_TRANSFORMER_SEMANTIC_INDEX_V1"
        ),
        "input_refs": {
            "crop_manifest": {
                "path": (OUTPUT_ROOT / "crop_manifest.json").as_posix(),
                "sha256": hashlib.sha256(manifest_raw).hexdigest(),
                "size_bytes": len(manifest_raw),
            },
            "ocr_result": {
                "path": (VIETOCR_OUTPUT_DIRECTORY / "ocr_result.json").as_posix(),
                "sha256": hashlib.sha256(result_raw).hexdigest(),
                "size_bytes": len(result_raw),
            },
            "reader_request": {
                "path": (OUTPUT_ROOT / "request.json").as_posix(),
                "sha256": hashlib.sha256(request_raw).hexdigest(),
                "size_bytes": len(request_raw),
            },
            "run_manifest": {
                "path": (VIETOCR_OUTPUT_DIRECTORY / "run_manifest.json").as_posix(),
                "sha256": hashlib.sha256(run_manifest_raw).hexdigest(),
                "size_bytes": len(run_manifest_raw),
            },
        },
        "metrics": {
            "document_count": manifest["metrics"]["document_count"],
            "empty_prediction_count": sum(
                sample["raw_prediction"] == "" for sample in result_samples
            ),
            "line_count_vector": manifest["metrics"]["line_count_vector"],
            "page_count": manifest["metrics"]["page_count"],
            "page_count_vector": manifest["metrics"]["page_count_vector"],
            "sample_count": len(result_samples),
            "semantic_axis_sha256": hashlib.sha256(semantic_axis_raw).hexdigest(),
            "terminal_page_count": manifest["metrics"]["terminal_page_count"],
        },
        "reader": {
            **manifest["intended_reader"],
            "run_git_commit": run_manifest["git_commit"],
        },
        "state": "VERIFIED_COMPLETE_ORDERED_VIETOCR_TRANSFORMER_PROPOSALS",
    }


def finalize_verified_vietocr_index_v1() -> dict[str, Any]:
    """Publish the matcher-facing semantic index once without overwriting."""

    destination = PROJECT_ROOT / VERIFIED_INDEX_DIRECTORY
    if destination.exists():
        raise _error(f"refusing to overwrite verified index: {destination}")
    index = read_verified_vietocr_proposals_v1()
    index_raw = _artifact_json_bytes_v1(index)
    receipt = {
        "format_version": (
            "ANNUAL_2025_8DOCUMENT_VIETOCR_TRANSFORMER_INDEX_RECEIPT_V1"
            if _ACTIVE_PROFILE == "annual-2025"
            else "WAVE1_8DOCUMENT_VIETOCR_TRANSFORMER_INDEX_RECEIPT_V1"
        ),
        "metrics": index["metrics"],
        "semantic_index_ref": {
            "path": (VERIFIED_INDEX_DIRECTORY / "semantic_index.json").as_posix(),
            "sha256": hashlib.sha256(index_raw).hexdigest(),
            "size_bytes": len(index_raw),
        },
        "state": "VERIFIED_INDEX_PUBLISHED_NO_OVERWRITE",
    }
    receipt_raw = _artifact_json_bytes_v1(receipt)
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    try:
        (stage / "semantic_index.json").write_bytes(index_raw)
        (stage / "verification_receipt.json").write_bytes(receipt_raw)
        if destination.exists():
            raise _error("verified index output appeared during publication")
        _publish_directory_noreplace(stage, destination)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build/verify the full eight-document VietOCR Transformer batch"
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--verify", action="store_true")
    action.add_argument("--replay", action="store_true")
    action.add_argument("--finalize", action="store_true")
    action.add_argument("--seal-annual-geometry", action="store_true")
    parser.add_argument(
        "--profile",
        choices=("wave1", "annual-2025"),
        default="wave1",
        help="reuse the same blind crop/reader pipeline on one pinned source corpus",
    )
    args = parser.parse_args()
    _activate_profile(args.profile)
    if args.seal_annual_geometry:
        if args.profile != "annual-2025":
            raise _error("annual geometry selection requires --profile annual-2025")
        output = seal_annual_2025_geometry_selection_v1()
    elif args.verify:
        output = _verify_active_full_document_freeze_v1(replay_geometry=False)
    elif args.replay:
        output = _verify_active_full_document_freeze_v1(replay_geometry=True)
    elif args.finalize:
        output = finalize_verified_vietocr_index_v1()
    elif args.profile == "annual-2025":
        output = build_annual_2025_full_document_request_v1()
    else:
        output = build_full_document_request_v1()
    print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
