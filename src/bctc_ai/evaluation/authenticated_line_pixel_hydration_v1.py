"""Authenticate source-line geometry before deterministic pixel crop hydration.

This adapter is intentionally recognition-blind.  It accepts only two source
states already present in the finalized Wave-1 V3 authority:

* complete causal-native line geometry without an upstream raster; and
* terminal PP-OCR line geometry whose word subdivisions remain quarantined.

The adapter never changes the upstream route or status, never exposes source
text, and never invokes an OCR provider.  Its only positive claim is that each
emitted line has an authenticated bounding box on one exact deterministic page
render.  A returned JSON envelope is descriptive only; downstream authority
requires the live opaque capability minted by the replay entry point.
"""

from __future__ import annotations

import copy
import hashlib
import os
import re
import stat
import weakref
from dataclasses import dataclass
from fractions import Fraction
from math import ceil, floor, isfinite
from pathlib import Path
from typing import Any, cast

import fitz

from bctc_ai.corpus import wave1_role_b_full_reader_v3 as full_v3
from bctc_ai.corpus import wave1_role_b_sentinel as sentinel
from bctc_ai.corpus.wave1_role_b_word_box_normalization import (
    WORD_BOX_NORMALIZATION_POLICY,
    WaveOneRoleBWordBoxNormalizationError,
    canonical_payload_sha256,
    normalization_policy_sha256,
    normalize_ppocrv6_word_boxes,
)
from bctc_ai.ocr.causal_native_text_evidence_v2 import (
    CausalNativeTextEvidenceError,
    validate_causal_native_text_evidence_v2_envelopes,
)
from bctc_ai.rendering.page_reader import (
    PageReaderRenderError,
    apply_rational_matrix,
    public_coordinate_authority,
    render_composited_displayed_page,
    transform_pixel_polygon_to_unrotated_mpt,
)
from bctc_ai.source_structure import finalized_v3_survey_stream_v1 as survey_v3
from bctc_ai.source_structure.contracts_v1 import (
    SourceStructureContractError,
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    decode_canonical_json_bytes_v1,
    same_typed_json_v1,
)
from bctc_ai.source_structure.evidence_projection_v2 import (
    SourceEvidenceProjectionV2Error,
    project_authenticated_page_v2,
)

__all__ = [
    "AuthenticatedLinePixelHydrationReceiptV1",
    "AuthenticatedLinePixelHydrationV1Error",
    "ENVELOPE_FORMAT_VERSION",
    "RECEIPT_FORMAT_VERSION",
    "project_authenticated_line_pixel_hydration_receipt_v1",
    "read_authenticated_line_pixel_hydration_envelope_v1",
    "read_authenticated_line_pixel_hydration_render_v1",
    "replay_authenticated_line_pixel_hydration_v1",
    "validate_authenticated_line_pixel_hydration_envelope_v1",
    "validate_line_pixel_hydration_envelope_v1",
]


class AuthenticatedLinePixelHydrationV1Error(RuntimeError):
    """The geometry-only hydration authority cannot be established exactly."""


ENVELOPE_FORMAT_VERSION = "BCTC_AI_AUTHENTICATED_LINE_PIXEL_HYDRATION_ENVELOPE_V1"
RECEIPT_FORMAT_VERSION = "BCTC_AI_AUTHENTICATED_LINE_PIXEL_HYDRATION_RECEIPT_V1"
_CLAIM_BOUNDARY = (
    "AUTHENTICATED_SOURCE_LINE_GEOMETRY_ON_EXACT_DETERMINISTIC_PAGE_RENDER_ONLY_"
    "NO_TEXT_SEMANTIC_NUMERIC_OR_MAPPING_AUTHORITY"
)
_ENVELOPE_ID_PREFIX = "alpghv1:envelope:"
_RECEIPT_ID_PREFIX = "alpghv1:receipt:"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_OBJECT_REF_FIELDS = {"path", "sha256", "size_bytes"}

_NATIVE_RESULT_FORMAT = "BANK_CORPUS_WAVE_1_ROLE_B_CAUSAL_NATIVE_PAGE_READ_RESULT_V2"
_OCR_TERMINAL_RESULT_FORMAT = "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V3"
_NATIVE_ROUTE = "CAUSAL_NATIVE_TEXT"
_OCR_ROUTE = "DOMINANT_RASTER_OCR"
_NATIVE_STATUS = "CAUSAL_NATIVE_TEXT_READ_COMPLETE"
_OCR_TERMINAL_STATUS = "UNRESOLVED_OCR_WORD_BOX_GEOMETRY"
_NORMALIZATION_FAILURE_REASON = "BOUNDED_WORD_BOX_NORMALIZATION_INVARIANT_FAILED"

_NATIVE_ADAPTER_ID = "NATIVE_CANONICAL_MPT_TO_DETERMINISTIC_200_DPI_PIXEL_V1"
_TERMINAL_ADAPTER_ID = "TERMINAL_PPOCRV6_LINE_GEOMETRY_WORD_QUARANTINE_V1"
_NATIVE_STATE = (
    _NATIVE_RESULT_FORMAT,
    "BANK_CORPUS_WAVE_1_CAUSAL_NATIVE_BACKEND_PAYLOAD_V2",
    _NATIVE_ROUTE,
    _NATIVE_STATUS,
    "RENDER_ABSENT",
    "POSITIVE_PUBLIC_LINE_DENOMINATOR",
    False,
)
_TERMINAL_STATE = (
    _OCR_TERMINAL_RESULT_FORMAT,
    "BANK_CORPUS_WAVE_1_PPOCRV6_BACKEND_PAYLOAD_V3",
    _OCR_ROUTE,
    _OCR_TERMINAL_STATUS,
    "RENDER_PRESENT",
    "ZERO_PUBLIC_LINE_DENOMINATOR",
    True,
)

_ENVELOPE_FIELDS = {
    "adapter_id",
    "authority",
    "claim_boundary",
    "coordinate_authority",
    "envelope_id",
    "finalized_v3_authority",
    "format_version",
    "lines",
    "metrics",
    "quarantine",
    "render_binding",
    "source_binding",
    "source_state",
    "upstream_binding",
}
_SOURCE_STATE_FIELDS = {
    "backend_format_version",
    "public_line_denominator_state",
    "render_binding_state",
    "result_format_version",
    "route",
    "status",
    "unresolved",
}
_FINALIZED_AUTHORITY_FIELDS = {
    "aggregate_artifact_ref",
    "aggregate_identity_sha256",
    "control_artifact_ref",
    "control_identity_sha256",
    "document_count",
    "request_count",
    "sealed_plan_ref",
}
_SOURCE_BINDING_FIELDS = {
    "document_id",
    "physical_page",
    "plan_document_binding_sha256",
    "plan_page_binding_sha256",
    "request_sha256",
    "source_pdf_sha256",
    "source_size_bytes",
}
_UPSTREAM_BINDING_FIELDS = {
    "backend_payload_ref",
    "line_text_axis_sha256",
    "page_record_format_version",
    "page_record_sha256",
    "raw_provider_payload_sha256",
    "render_ref",
    "request_ordinal",
    "result_format_version",
    "result_ref",
    "route",
    "status",
    "status_preserved",
    "unresolved",
}
_RENDER_BINDING_FIELDS = {
    "dpi",
    "origin",
    "pixel_height",
    "pixel_width",
    "render_profile",
    "sha256",
    "size_bytes",
    "upstream_render_ref",
}
_LINE_FIELDS = {
    "canonical_bbox_mpt",
    "line_index",
    "raw_pixel_bbox",
    "source_geometry_sha256",
}
_METRIC_FIELDS = {
    "authenticated_source_line_axis_count",
    "emitted_line_count",
    "excluded_line_count",
    "upstream_public_line_axis_count",
}
_QUARANTINE_FIELDS = {
    "source_word_axis_count",
    "terminal_word_geometry_failure_preserved",
    "word_axis_sha256",
    "word_geometry_exposed",
    "word_text_exposed",
}
_AUTHORITY_FIELDS = {
    "bank_identity_used_for_routing",
    "filename_identity_used_for_routing",
    "geometry_only_authority",
    "line_pixel_geometry_authority",
    "mapping_authority",
    "network_used",
    "numeric_authority",
    "ocr_model_invoked",
    "ppocr_transcript_semantic_authority",
    "recognition_authority",
    "schema_authority",
    "semantic_authority",
    "source_path_used_for_routing",
    "upstream_status_preserved",
}
_AUTHORITY = {
    "bank_identity_used_for_routing": False,
    "filename_identity_used_for_routing": False,
    "geometry_only_authority": True,
    "line_pixel_geometry_authority": True,
    "mapping_authority": False,
    "network_used": False,
    "numeric_authority": False,
    "ocr_model_invoked": False,
    "ppocr_transcript_semantic_authority": False,
    "recognition_authority": False,
    "schema_authority": False,
    "semantic_authority": False,
    "source_path_used_for_routing": False,
    "upstream_status_preserved": True,
}

_RECEIPT_FIELDS = {
    "adapter_id",
    "authority",
    "claim_boundary",
    "emitted_line_count",
    "envelope_ref",
    "format_version",
    "line_axis_sha256",
    "receipt_id",
    "render_ref",
    "source_locator",
    "upstream_backend_ref",
    "upstream_result_ref",
    "upstream_status",
}
_RECEIPT_AUTHORITY_FIELDS = {
    "geometry_only_authority",
    "live_capability_required",
    "raw_envelope_self_authenticates",
    "raw_receipt_self_authenticates",
    "recognition_authority",
    "semantic_or_numeric_authority",
}
_RECEIPT_AUTHORITY = {
    "geometry_only_authority": True,
    "live_capability_required": True,
    "raw_envelope_self_authenticates": False,
    "raw_receipt_self_authenticates": False,
    "recognition_authority": False,
    "semantic_or_numeric_authority": False,
}
_CONTENT_REF_FIELDS = {"sha256", "size_bytes"}
_SOURCE_LOCATOR_FIELDS = {"physical_page", "source_pdf_sha256", "source_size_bytes"}

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
_NORMALIZATION_FAILURE_FIELDS = {
    "control_identity_sha256",
    "format_version",
    "normalization_producer_implementation_ledger_sha256",
    "pixel_dimensions",
    "policy_sha256",
    "raw_payload_sha256",
    "reason",
    "status",
}


def _error(message: str) -> AuthenticatedLinePixelHydrationV1Error:
    return AuthenticatedLinePixelHydrationV1Error(message)


def _exact_dict(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise _error(f"{label} must contain the exact closed field set")
    return cast(dict[str, Any], value)


def _sha256(value: Any, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise _error(f"{label} is not one exact lowercase SHA-256")
    return value


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} must be one positive integer")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise _error(f"{label} must be one nonnegative integer")
    return value


def _content_ref(value: Any, label: str) -> dict[str, Any]:
    reference = _exact_dict(value, _CONTENT_REF_FIELDS, label)
    _sha256(reference["sha256"], f"{label} hash")
    _positive_int(reference["size_bytes"], f"{label} size")
    return canonical_clone_v1(reference)


def _object_ref(value: Any, label: str, suffix: str = ".json") -> dict[str, Any]:
    reference = _exact_dict(value, _OBJECT_REF_FIELDS, label)
    digest = _sha256(reference["sha256"], f"{label} hash")
    _positive_int(reference["size_bytes"], f"{label} size")
    expected_path = f"objects/sha256/{digest[:2]}/{digest}{suffix}"
    if reference["path"] != expected_path:
        raise _error(f"{label} is not a canonical V3 CAS reference")
    return canonical_clone_v1(reference)


def _canonical_bytes(value: Any) -> bytes:
    try:
        return canonical_json_bytes_v1(value)
    except SourceStructureContractError as exc:
        raise _error("value is not finite canonical JSON") from exc


def _strict_canonical_json(payload: bytes, label: str) -> dict[str, Any]:
    if type(payload) is not bytes or not payload:
        raise _error(f"{label} must be nonempty exact bytes")
    try:
        value = decode_canonical_json_bytes_v1(payload)
    except SourceStructureContractError as exc:
        raise _error(f"{label} is not strict UTF-8 JSON") from exc
    if type(value) is not dict or _canonical_bytes(value) != payload:
        raise _error(f"{label} is not one canonical JSON object")
    return cast(dict[str, Any], value)


def _safe_relative_path(value: Any, label: str, suffix: str) -> Path:
    if type(value) is not str or not value or "\\" in value:
        raise _error(f"{label} is not a canonical project-relative POSIX path")
    path = Path(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.suffix.casefold() != suffix.casefold()
    ):
        raise _error(f"{label} is not a canonical project-relative POSIX path")
    return path


def _stable_nofollow_bytes(root: Path, relative: Path | str, label: str) -> bytes:
    text = relative.as_posix() if isinstance(relative, Path) else relative
    path = _safe_relative_path(text, label, Path(text).suffix)
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    file_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        current = os.open(root, directory_flags)
    except OSError as exc:
        raise _error(f"cannot open project root for {label}") from exc
    descriptor: int | None = None
    try:
        for part in path.parts[:-1]:
            following = os.open(part, directory_flags, dir_fd=current)
            os.close(current)
            current = following
        descriptor = os.open(path.parts[-1], file_flags, dir_fd=current)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise _error(f"{label} is not one regular single-link file")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        after = os.fstat(descriptor)

        def identity(item: os.stat_result) -> tuple[int, int, int, int, int, int]:
            return (
                item.st_dev,
                item.st_ino,
                item.st_mode,
                item.st_size,
                item.st_mtime_ns,
                item.st_ctime_ns,
            )

        payload = b"".join(chunks)
        if identity(before) != identity(after) or len(payload) != before.st_size:
            raise _error(f"{label} changed during stable nofollow read")
        return payload
    except OSError as exc:
        raise _error(f"cannot stably read nofollow {label}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(current)


def _source_state(
    page_record: dict[str, Any], page_result: dict[str, Any], backend: dict[str, Any]
) -> tuple[Any, ...]:
    line_count = page_record.get("line_axis_count")
    denominator_state = (
        "POSITIVE_PUBLIC_LINE_DENOMINATOR"
        if type(line_count) is int and line_count > 0
        else "ZERO_PUBLIC_LINE_DENOMINATOR"
        if line_count == 0
        else "INVALID_PUBLIC_LINE_DENOMINATOR"
    )
    return (
        page_result.get("format_version"),
        backend.get("format_version"),
        page_record.get("route"),
        page_record.get("status"),
        "RENDER_ABSENT" if page_record.get("render_ref") is None else "RENDER_PRESENT",
        denominator_state,
        page_record.get("unresolved"),
    )


def _adapter_for_source_state(state: tuple[Any, ...]) -> str:
    if len(state) != 7 or type(state[6]) is not bool:
        raise _error("finalized source-state tuple has no admitted geometry hydration adapter")
    if state == _NATIVE_STATE:
        return _NATIVE_ADAPTER_ID
    if state == _TERMINAL_STATE:
        return _TERMINAL_ADAPTER_ID
    raise _error("finalized source-state tuple has no admitted geometry hydration adapter")


def _source_state_payload(state: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "result_format_version": state[0],
        "backend_format_version": state[1],
        "route": state[2],
        "status": state[3],
        "render_binding_state": state[4],
        "public_line_denominator_state": state[5],
        "unresolved": state[6],
    }


def _rect_mpt(rectangle: Any) -> list[int]:
    return [
        int(round(float(rectangle.x0) * 1_000)),
        int(round(float(rectangle.y0) * 1_000)),
        int(round(float(rectangle.x1) * 1_000)),
        int(round(float(rectangle.y1) * 1_000)),
    ]


def _plan_document_binding(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": document.get("document_id"),
        "page_count": document.get("page_count"),
        "request_set_sha256": document.get("request_set_sha256"),
        "sha256": document.get("sha256"),
        "size_bytes": document.get("size_bytes"),
    }


def _validate_plan_and_select_source(
    plan: dict[str, Any],
    *,
    source_pdf_sha256: str,
    physical_page: int,
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    if (
        plan.get("format_version") != "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_PLAN_V1"
        or plan.get("status") != "READY_FOR_ROLE_B_PAGE_READ_EXECUTION"
        or plan.get("claim_boundary") != "SOURCE_VISIBLE_PAGE_TEXT_AND_GEOMETRY_EVIDENCE_ONLY"
        or plan.get("execution_plan_sha256") != sentinel.EXECUTION_PLAN_SHA256
        or plan.get("selection_receipt_sha256") != sentinel.SELECTION_RECEIPT_SHA256
        or plan.get("sentinel_sha256") != sentinel.SENTINEL_SHA256
        or plan.get("route_plan_sha256")
        != "82b4b387754060419da37a1616336bf32d6a9248945cfc3974b936dbeace609d"
        or type(plan.get("documents")) is not list
    ):
        raise _error("sealed plan authority drifted")
    matches = [
        item
        for item in plan["documents"]
        if type(item) is dict and item.get("sha256") == source_pdf_sha256
    ]
    if len(matches) != 1:
        raise _error("source identity is not unique in the sealed plan")
    document = cast(dict[str, Any], matches[0])
    if (
        document.get("document_id") != f"sha256:{source_pdf_sha256}"
        or type(document.get("size_bytes")) is not int
        or document["size_bytes"] <= 0
        or type(document.get("page_count")) is not int
        or document["page_count"] <= 0
        or type(document.get("pages")) is not list
        or len(document["pages"]) != document["page_count"]
        or type(document.get("request_set_sha256")) is not str
    ):
        raise _error("sealed plan source-document binding drifted")
    _sha256(document["request_set_sha256"], "sealed plan request-set identity")
    pages = [
        item
        for item in document["pages"]
        if type(item) is dict and item.get("page") == physical_page
    ]
    if len(pages) != 1:
        raise _error("physical page is not unique in the sealed plan source")
    page = cast(dict[str, Any], pages[0])
    source_path = _safe_relative_path(document.get("relative_path"), "source PDF", ".pdf")
    return canonical_clone_v1(document), canonical_clone_v1(page), source_path


def _validate_source_page(
    source_payload: bytes,
    *,
    plan_document: dict[str, Any],
    plan_page: dict[str, Any],
    page_record: dict[str, Any],
    dpi: int,
) -> tuple[bytes, int, int, dict[str, Any]]:
    if (
        len(source_payload) != page_record["source_size_bytes"]
        or hashlib.sha256(source_payload).hexdigest() != page_record["source_sha256"]
        or plan_document["sha256"] != page_record["source_sha256"]
        or plan_document["size_bytes"] != page_record["source_size_bytes"]
        or plan_document["document_id"] != page_record["document_id"]
        or not same_typed_json_v1(plan_page.get("request"), page_record["request"])
        or plan_page.get("request_sha256") != page_record["request_sha256"]
        or plan_page.get("page") != page_record["physical_page"]
        or plan_page.get("route") != page_record["route"]
    ):
        raise _error("source/plan/finalized page binding drifted")
    try:
        document = fitz.open(stream=source_payload, filetype="pdf")
    except (RuntimeError, ValueError, TypeError) as exc:
        raise _error("authenticated source bytes are not a readable PDF") from exc
    try:
        if document.needs_pass or document.page_count != plan_document["page_count"]:
            raise _error("authenticated source PDF page accounting drifted")
        page = document.load_page(page_record["physical_page"] - 1)
        expected_geometry = {
            "crop_box_mpt": _rect_mpt(page.cropbox),
            "effective_rect_mpt": _rect_mpt(page.rect),
            "media_box_mpt": _rect_mpt(page.mediabox),
            "pdf_rotation_degrees": int(page.rotation),
        }
        if any(
            not same_typed_json_v1(plan_page.get(field), expected)
            for field, expected in expected_geometry.items()
        ):
            raise _error("authenticated source PDF page geometry drifted from the sealed plan")
        first = render_composited_displayed_page(page, dpi=dpi)
        second = render_composited_displayed_page(page, dpi=dpi)
        if (
            first.payload != second.payload
            or first.sha256 != second.sha256
            or first.size_bytes != second.size_bytes
            or first.pixel_width != second.pixel_width
            or first.pixel_height != second.pixel_height
            or not same_typed_json_v1(
                public_coordinate_authority(first.coordinate_authority),
                public_coordinate_authority(second.coordinate_authority),
            )
        ):
            raise _error("source PDF render is not deterministic within replay")
        return (
            first.payload,
            first.pixel_width,
            first.pixel_height,
            first.coordinate_authority,
        )
    except (IndexError, PageReaderRenderError, RuntimeError) as exc:
        if isinstance(exc, AuthenticatedLinePixelHydrationV1Error):
            raise
        raise _error("authenticated source PDF page could not be rendered") from exc
    finally:
        document.close()


def _bbox_polygon(box: list[int]) -> list[list[int]]:
    return [
        [box[0], box[1]],
        [box[2], box[1]],
        [box[2], box[3]],
        [box[0], box[3]],
    ]


def _canonical_bbox_from_pixel_box(
    box: list[int], coordinate_authority: dict[str, Any]
) -> list[int]:
    polygon = transform_pixel_polygon_to_unrotated_mpt(_bbox_polygon(box), coordinate_authority)
    return [
        min(point[0] for point in polygon),
        min(point[1] for point in polygon),
        max(point[0] for point in polygon),
        max(point[1] for point in polygon),
    ]


def _validate_canonical_bbox(value: Any, width: int, height: int, label: str) -> list[int]:
    if type(value) is not list or len(value) != 4 or any(type(item) is not int for item in value):
        raise _error(f"{label} must be one exact integer bbox")
    box = cast(list[int], value)
    if not (0 <= box[0] < box[2] <= width and 0 <= box[1] < box[3] <= height):
        raise _error(f"{label} lies outside its canonical page")
    return list(box)


def _native_pixel_box(
    canonical_box: list[int],
    *,
    coordinate_authority: dict[str, Any],
    pixel_width: int,
    pixel_height: int,
) -> list[int]:
    matrix = coordinate_authority.get("_unrotated_to_pixel_matrix")
    inverse = coordinate_authority.get("_pixel_to_unrotated_matrix")
    if not isinstance(matrix, tuple) or not isinstance(inverse, tuple):
        raise _error("native hydration lacks in-memory exact coordinate matrices")
    transformed = [
        apply_rational_matrix(matrix, point[0], point[1]) for point in _bbox_polygon(canonical_box)
    ]
    pixel_box = [
        floor(min(point[0] for point in transformed)),
        floor(min(point[1] for point in transformed)),
        ceil(max(point[0] for point in transformed)),
        ceil(max(point[1] for point in transformed)),
    ]
    if not (
        0 <= pixel_box[0] < pixel_box[2] <= pixel_width
        and 0 <= pixel_box[1] < pixel_box[3] <= pixel_height
    ):
        raise _error("outward native line pixel box lies outside its exact render")
    reverse = [
        apply_rational_matrix(inverse, point[0], point[1]) for point in _bbox_polygon(pixel_box)
    ]
    bounds = [
        min(point[0] for point in reverse),
        min(point[1] for point in reverse),
        max(point[0] for point in reverse),
        max(point[1] for point in reverse),
    ]
    if not (
        bounds[0] <= Fraction(canonical_box[0])
        and bounds[1] <= Fraction(canonical_box[1])
        and bounds[2] >= Fraction(canonical_box[2])
        and bounds[3] >= Fraction(canonical_box[3])
    ):
        raise _error("outward native line pixel box does not enclose source geometry")
    return pixel_box


def _native_geometry_lines(
    result: dict[str, Any],
    *,
    coordinate_authority: dict[str, Any],
    pixel_width: int,
    pixel_height: int,
) -> tuple[list[dict[str, Any]], str, int, str]:
    lines = result.get("lines")
    words = result.get("words")
    if type(lines) is not list or type(words) is not list or not lines:
        raise _error("native source has no positive authenticated line denominator")
    unrotated = coordinate_authority.get("unrotated_dimensions_mpt")
    if (
        type(unrotated) is not list
        or len(unrotated) != 2
        or any(type(value) is not int or value <= 0 for value in unrotated)
    ):
        raise _error("native render canonical dimensions drifted")
    emitted = []
    hidden_text = []
    for index, line_value in enumerate(lines):
        if type(line_value) is not dict:
            raise _error("native line axis contains a non-object")
        line = cast(dict[str, Any], line_value)
        text = line.get("raw_text")
        if type(text) is not str or text == "":
            raise _error("native line denominator contains an empty or non-string line")
        canonical_box = _validate_canonical_bbox(
            line.get("canonical_bbox_mpt"), unrotated[0], unrotated[1], f"native line {index}"
        )
        pixel_box = _native_pixel_box(
            canonical_box,
            coordinate_authority=coordinate_authority,
            pixel_width=pixel_width,
            pixel_height=pixel_height,
        )
        source_geometry = {
            "block_number": line.get("block_number"),
            "canonical_bbox_mpt": canonical_box,
            "line_number": line.get("line_number"),
        }
        if any(type(source_geometry[key]) is not int for key in ("block_number", "line_number")):
            raise _error("native source line identity drifted")
        emitted.append(
            {
                "canonical_bbox_mpt": canonical_box,
                "line_index": index,
                "raw_pixel_bbox": pixel_box,
                "source_geometry_sha256": canonical_json_sha256_v1(source_geometry),
            }
        )
        hidden_text.append(text)
    return (
        emitted,
        canonical_json_sha256_v1(hidden_text),
        len(words),
        canonical_json_sha256_v1(words),
    )


def _finite_number(value: Any, label: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise _error(f"{label} must be one finite non-boolean number")
    return value


def _terminal_raw_axes(
    raw: dict[str, Any], *, pixel_width: int, pixel_height: int
) -> tuple[list[dict[str, Any]], str, int, str]:
    required_axes = (
        "rec_texts",
        "rec_scores",
        "rec_polys",
        "rec_boxes",
        "text_word_boxes",
        "text_word",
    )
    if raw.get("return_word_box") is not True or any(
        type(raw.get(field)) is not list for field in required_axes
    ):
        raise _error("terminal raw PP line axes are absent")
    counts = {field: len(raw[field]) for field in required_axes}
    if len(set(counts.values())) != 1 or counts["rec_texts"] <= 0:
        raise _error("terminal raw PP line axes are empty or misaligned")
    try:
        validated = full_v3._validate_ppocrv6_schema_except_word_geometry(  # noqa: SLF001
            raw,
            pixel_width=pixel_width,
            pixel_height=pixel_height,
        )
    except full_v3.WaveOneRoleBFullReaderError as exc:
        raise _error("terminal raw PP payload has a non-word-geometry failure") from exc
    sanitized = copy.deepcopy(raw)
    hidden_words = []
    for line_index in range(counts["rec_texts"]):
        line_box = raw["rec_boxes"][line_index]
        boxes = raw["text_word_boxes"][line_index]
        words = raw["text_word"][line_index]
        if (
            type(line_box) is not list
            or len(line_box) != 4
            or type(boxes) is not list
            or type(words) is not list
            or len(boxes) != len(words)
        ):
            raise _error("terminal quarantined subdivision axes are malformed")
        replacements = []
        for word_index, (box, word) in enumerate(zip(boxes, words, strict=True)):
            if type(word) is not str or type(box) is not list or len(box) != 4:
                raise _error("terminal quarantined subdivision schema drifted")
            coordinates = [
                _finite_number(item, f"terminal word box {line_index}:{word_index}") for item in box
            ]
            if not coordinates[0] < coordinates[2] or not coordinates[1] < coordinates[3]:
                raise _error("terminal quarantined word box is not positive")
            replacements.append(copy.deepcopy(line_box))
        sanitized["text_word_boxes"][line_index] = replacements
        hidden_words.append([copy.deepcopy(words), copy.deepcopy(boxes)])
    if validated["line_count"] != counts["rec_texts"]:
        raise _error("terminal raw PP validated line accounting drifted")
    hidden_text = raw["rec_texts"]
    if any(type(text) is not str or text == "" for text in hidden_text):
        raise _error("terminal raw PP source does not preserve its full nonempty denominator")
    return (
        sanitized,
        canonical_json_sha256_v1(hidden_text),
        sum(len(line) for line in raw["text_word"]),
        canonical_json_sha256_v1(hidden_words),
    )


def _terminal_geometry_lines(
    raw: dict[str, Any],
    *,
    coordinate_authority: dict[str, Any],
    pixel_width: int,
    pixel_height: int,
) -> tuple[list[dict[str, Any]], str, int, str]:
    _sanitized, line_text_hash, word_count, word_hash = _terminal_raw_axes(
        raw, pixel_width=pixel_width, pixel_height=pixel_height
    )
    unrotated = coordinate_authority.get("unrotated_dimensions_mpt")
    if (
        type(unrotated) is not list
        or len(unrotated) != 2
        or any(type(value) is not int or value <= 0 for value in unrotated)
    ):
        raise _error("terminal coordinate authority dimensions drifted")
    emitted = []
    for index, (box_value, polygon_value) in enumerate(
        zip(raw["rec_boxes"], raw["rec_polys"], strict=True)
    ):
        if (
            type(box_value) is not list
            or len(box_value) != 4
            or any(type(item) is not int for item in box_value)
        ):
            raise _error("terminal line bbox is not an exact integer pixel bbox")
        box = cast(list[int], box_value)
        if not (0 <= box[0] < box[2] <= pixel_width and 0 <= box[1] < box[3] <= pixel_height):
            raise _error("terminal line bbox lies outside its authenticated render")
        if (
            type(polygon_value) is not list
            or len(polygon_value) != 4
            or any(
                type(point) is not list
                or len(point) != 2
                or any(type(item) is not int for item in point)
                for point in polygon_value
            )
        ):
            raise _error("terminal line polygon is not an exact integer quadrilateral")
        polygon = cast(list[list[int]], polygon_value)
        canonical_box = _canonical_bbox_from_pixel_box(box, coordinate_authority)
        canonical_polygon = transform_pixel_polygon_to_unrotated_mpt(polygon, coordinate_authority)
        if not (
            0 <= canonical_box[0] < canonical_box[2] <= unrotated[0]
            and 0 <= canonical_box[1] < canonical_box[3] <= unrotated[1]
            and all(
                canonical_box[0] <= point[0] <= canonical_box[2]
                and canonical_box[1] <= point[1] <= canonical_box[3]
                for point in canonical_polygon
            )
        ):
            raise _error("terminal canonical line geometry lies outside its page or bbox")
        source_geometry = {"rec_box": box, "rec_polygon": polygon}
        emitted.append(
            {
                "canonical_bbox_mpt": canonical_box,
                "line_index": index,
                "raw_pixel_bbox": list(box),
                "source_geometry_sha256": canonical_json_sha256_v1(source_geometry),
            }
        )
    return emitted, line_text_hash, word_count, word_hash


@dataclass(frozen=True)
class _AuthenticatedInputs:
    control: dict[str, Any]
    plan_payload: bytes
    plan_document: dict[str, Any]
    plan_page: dict[str, Any]
    page_record: dict[str, Any]
    page_result: dict[str, Any]
    page_result_payload: bytes
    backend: dict[str, Any]
    backend_payload: bytes
    source_payload: bytes
    upstream_render_payload: bytes | None


def _validate_native_upstream(inputs: _AuthenticatedInputs) -> None:
    contract = inputs.control.get("native_reader_contract")
    if type(contract) is not dict:
        raise _error("finalized V3 native reader contract is absent")
    try:
        validate_causal_native_text_evidence_v2_envelopes(
            request=inputs.page_record["request"],
            request_sha256=inputs.page_record["request_sha256"],
            document_id=inputs.page_record["document_id"],
            source_sha256=inputs.page_record["source_sha256"],
            source_size_bytes=inputs.page_record["source_size_bytes"],
            physical_page=inputs.page_record["physical_page"],
            provider_runtime_ledger=contract["provider_runtime_ledger"],
            native_ordering_policy_identity=contract["native_ordering_policy_identity"],
            full_control_identity_sha256=inputs.control["control_identity_sha256"],
            backend=inputs.backend,
            result=inputs.page_result,
        )
    except (CausalNativeTextEvidenceError, KeyError, TypeError) as exc:
        raise _error("finalized native backend/result authority drifted") from exc


def _validate_terminal_upstream(
    inputs: _AuthenticatedInputs,
    *,
    render_payload: bytes,
    coordinate_authority: dict[str, Any],
    pixel_width: int,
    pixel_height: int,
) -> dict[str, Any]:
    record = inputs.page_record
    result = inputs.page_result
    backend = _exact_dict(inputs.backend, _TERMINAL_BACKEND_FIELDS, "terminal backend")
    failure = _exact_dict(
        backend.get("normalization_failure"),
        _NORMALIZATION_FAILURE_FIELDS,
        "terminal normalization failure",
    )
    adoption = record.get("upstream_v2_adoption")
    failed_v2 = inputs.control.get("failed_v2_authority")
    raw = backend.get("raw_provider_payload")
    if type(adoption) is not dict or type(failed_v2) is not dict or type(raw) is not dict:
        raise _error("terminal upstream adoption or raw provider payload is absent")
    raw = cast(dict[str, Any], raw)
    render_ref = _object_ref(record["render_ref"], "terminal render reference", ".png")
    if (
        backend.get("format_version") != "BANK_CORPUS_WAVE_1_PPOCRV6_BACKEND_PAYLOAD_V3"
        or backend.get("claim_boundary")
        != "RAW_PINNED_PROVIDER_PAYLOAD_WITH_TERMINAL_BOUNDED_WORD_BOX_GEOMETRY_FAILURE"
        or backend.get("request_sha256") != record["request_sha256"]
        or not same_typed_json_v1(backend.get("request"), record["request"])
        or backend.get("provider_identity_sha256") != record["request"]["provider_identity_sha256"]
        or not same_typed_json_v1(backend.get("render_ref"), render_ref)
        or not same_typed_json_v1(result.get("input_render_ref"), render_ref)
        or not same_typed_json_v1(result.get("backend_payload_ref"), record["backend_payload_ref"])
        or not same_typed_json_v1(
            adoption.get("source_refs"),
            {
                "backend_payload_ref": record["backend_payload_ref"],
                "render_ref": record["render_ref"],
                "result_ref": record["result_ref"],
            },
        )
        or backend.get("word_box_normalization_ledger") is not None
        or not same_typed_json_v1(failure, result.get("normalization_failure"))
        or not same_typed_json_v1(result.get("coordinate_authority"), coordinate_authority)
        or render_payload != inputs.upstream_render_payload
        or len(render_payload) != render_ref["size_bytes"]
        or hashlib.sha256(render_payload).hexdigest() != render_ref["sha256"]
        or failure.get("format_version") != "BANK_CORPUS_WAVE_1_PPOCRV6_NORMALIZATION_FAILURE_V1"
        or failure.get("status") != _OCR_TERMINAL_STATUS
        or failure.get("reason") != _NORMALIZATION_FAILURE_REASON
        or failure.get("policy_sha256")
        != normalization_policy_sha256(WORD_BOX_NORMALIZATION_POLICY)
        or failure.get("control_identity_sha256") != adoption.get("source_control_identity_sha256")
        or failure.get("control_identity_sha256") != failed_v2.get("control_identity_sha256")
        or failure.get("normalization_producer_implementation_ledger_sha256")
        != failed_v2.get("producer_implementation_ledger_sha256")
        or not same_typed_json_v1(failure.get("pixel_dimensions"), [pixel_width, pixel_height])
        or failure.get("raw_payload_sha256") != canonical_payload_sha256(raw)
    ):
        raise _error("terminal upstream backend/result/render/failure binding drifted")
    authority = {
        "policy": canonical_clone_v1(WORD_BOX_NORMALIZATION_POLICY),
        "policy_sha256": failure["policy_sha256"],
        "control_identity_sha256": failure["control_identity_sha256"],
        "normalization_producer_implementation_ledger_sha256": failure[
            "normalization_producer_implementation_ledger_sha256"
        ],
    }
    try:
        normalize_ppocrv6_word_boxes(
            raw,
            pixel_width=pixel_width,
            pixel_height=pixel_height,
            authority=authority,
        )
    except WaveOneRoleBWordBoxNormalizationError:
        pass
    else:
        raise _error("terminal raw payload is unexpectedly word-box normalizable")
    return raw


def _validate_input_object_bytes(inputs: _AuthenticatedInputs) -> None:
    record = inputs.page_record
    for payload, value, reference, label in (
        (
            inputs.page_result_payload,
            inputs.page_result,
            record["result_ref"],
            "finalized page result",
        ),
        (
            inputs.backend_payload,
            inputs.backend,
            record["backend_payload_ref"],
            "finalized backend",
        ),
    ):
        if (
            _canonical_bytes(value) != payload
            or len(payload) != reference["size_bytes"]
            or hashlib.sha256(payload).hexdigest() != reference["sha256"]
        ):
            raise _error(f"{label} canonical bytes or CAS identity drifted")


def _build_authenticated_line_pixel_hydration_v1(
    inputs: _AuthenticatedInputs,
) -> tuple[dict[str, Any], bytes]:
    try:
        projection = project_authenticated_page_v2(
            page_record=inputs.page_record,
            page_result=inputs.page_result,
        )
    except SourceEvidenceProjectionV2Error as exc:
        raise _error("finalized page record/result projection drifted") from exc
    del projection
    _validate_input_object_bytes(inputs)
    state = _source_state(inputs.page_record, inputs.page_result, inputs.backend)
    adapter_id = _adapter_for_source_state(state)
    request = inputs.page_record["request"]
    dpi = (
        200
        if adapter_id == _NATIVE_ADAPTER_ID
        else request.get("render_specification", {}).get("dpi")
    )
    if type(dpi) is not int or dpi not in {200, 300}:
        raise _error("hydration render profile DPI is not admitted")
    render_payload, pixel_width, pixel_height, private_authority = _validate_source_page(
        inputs.source_payload,
        plan_document=inputs.plan_document,
        plan_page=inputs.plan_page,
        page_record=inputs.page_record,
        dpi=dpi,
    )
    public_authority = public_coordinate_authority(private_authority)

    if adapter_id == _NATIVE_ADAPTER_ID:
        if inputs.upstream_render_payload is not None:
            raise _error("native no-render source unexpectedly acquired an upstream render")
        _validate_native_upstream(inputs)
        lines, line_text_hash, word_count, word_hash = _native_geometry_lines(
            inputs.page_result,
            coordinate_authority=private_authority,
            pixel_width=pixel_width,
            pixel_height=pixel_height,
        )
        upstream_public_count = inputs.page_record["line_axis_count"]
        raw_provider_hash = None
        terminal_failure_preserved = False
        render_origin = "DETERMINISTIC_SOURCE_REPLAY_FOR_NATIVE_GEOMETRY"
        upstream_render_ref = None
    else:
        raw = _validate_terminal_upstream(
            inputs,
            render_payload=render_payload,
            coordinate_authority=public_authority,
            pixel_width=pixel_width,
            pixel_height=pixel_height,
        )
        lines, line_text_hash, word_count, word_hash = _terminal_geometry_lines(
            raw,
            coordinate_authority=private_authority,
            pixel_width=pixel_width,
            pixel_height=pixel_height,
        )
        upstream_public_count = 0
        raw_provider_hash = canonical_payload_sha256(raw)
        terminal_failure_preserved = True
        render_origin = "EXACT_UPSTREAM_RENDER_REPRODUCED_FROM_SOURCE"
        upstream_render_ref = canonical_clone_v1(inputs.page_record["render_ref"])

    if len(lines) <= 0 or len(lines) != (
        inputs.page_record["line_axis_count"]
        if adapter_id == _NATIVE_ADAPTER_ID
        else len(inputs.backend["raw_provider_payload"]["rec_texts"])
    ):
        raise _error("authenticated source-line denominator was not preserved in full")
    pins = survey_v3.FINALIZED_V3_SURVEY_AUTHORITY_V1
    envelope = {
        "format_version": ENVELOPE_FORMAT_VERSION,
        "claim_boundary": _CLAIM_BOUNDARY,
        "envelope_id": _ENVELOPE_ID_PREFIX + "0" * 64,
        "adapter_id": adapter_id,
        "source_state": _source_state_payload(state),
        "finalized_v3_authority": {
            "aggregate_artifact_ref": {
                "sha256": pins.aggregate_artifact_sha256,
                "size_bytes": pins.aggregate_size_bytes,
            },
            "aggregate_identity_sha256": pins.aggregate_identity_sha256,
            "control_artifact_ref": {
                "sha256": pins.control_artifact_sha256,
                "size_bytes": pins.control_size_bytes,
            },
            "control_identity_sha256": pins.control_identity_sha256,
            "document_count": pins.document_count,
            "request_count": pins.request_count,
            "sealed_plan_ref": {
                "sha256": pins.sealed_plan_sha256,
                "size_bytes": sentinel.SEALED_PLAN_SIZE_BYTES,
            },
        },
        "source_binding": {
            "document_id": inputs.page_record["document_id"],
            "physical_page": inputs.page_record["physical_page"],
            "plan_document_binding_sha256": canonical_json_sha256_v1(
                _plan_document_binding(inputs.plan_document)
            ),
            "plan_page_binding_sha256": canonical_json_sha256_v1(inputs.plan_page),
            "request_sha256": inputs.page_record["request_sha256"],
            "source_pdf_sha256": inputs.page_record["source_sha256"],
            "source_size_bytes": inputs.page_record["source_size_bytes"],
        },
        "upstream_binding": {
            "backend_payload_ref": canonical_clone_v1(inputs.page_record["backend_payload_ref"]),
            "line_text_axis_sha256": line_text_hash,
            "page_record_format_version": inputs.page_record["format_version"],
            "page_record_sha256": canonical_json_sha256_v1(inputs.page_record),
            "raw_provider_payload_sha256": raw_provider_hash,
            "render_ref": upstream_render_ref,
            "request_ordinal": inputs.page_record["request_ordinal"],
            "result_format_version": inputs.page_result["format_version"],
            "result_ref": canonical_clone_v1(inputs.page_record["result_ref"]),
            "route": inputs.page_record["route"],
            "status": inputs.page_record["status"],
            "status_preserved": True,
            "unresolved": inputs.page_record["unresolved"],
        },
        "render_binding": {
            "dpi": dpi,
            "origin": render_origin,
            "pixel_height": pixel_height,
            "pixel_width": pixel_width,
            "render_profile": {
                "alpha": False,
                "annotations": "INCLUDED",
                "colorspace": "RGB",
                "source": "FULL_COMPOSITED_DISPLAYED_PDF_PAGE",
            },
            "sha256": hashlib.sha256(render_payload).hexdigest(),
            "size_bytes": len(render_payload),
            "upstream_render_ref": upstream_render_ref,
        },
        "coordinate_authority": public_authority,
        "lines": lines,
        "metrics": {
            "authenticated_source_line_axis_count": len(lines),
            "emitted_line_count": len(lines),
            "excluded_line_count": 0,
            "upstream_public_line_axis_count": upstream_public_count,
        },
        "quarantine": {
            "source_word_axis_count": word_count,
            "terminal_word_geometry_failure_preserved": terminal_failure_preserved,
            "word_axis_sha256": word_hash,
            "word_geometry_exposed": False,
            "word_text_exposed": False,
        },
        "authority": canonical_clone_v1(_AUTHORITY),
    }
    envelope["envelope_id"] = _ENVELOPE_ID_PREFIX + canonical_json_sha256_v1(
        {key: value for key, value in envelope.items() if key != "envelope_id"}
    )
    return validate_line_pixel_hydration_envelope_v1(envelope), render_payload


def _validate_source_state_payload(value: Any, adapter_id: str) -> dict[str, Any]:
    state = _exact_dict(value, _SOURCE_STATE_FIELDS, "hydration source state")
    if type(state["unresolved"]) is not bool:
        raise _error("hydration source unresolved state must be one exact boolean")
    tuple_state = (
        state["result_format_version"],
        state["backend_format_version"],
        state["route"],
        state["status"],
        state["render_binding_state"],
        state["public_line_denominator_state"],
        state["unresolved"],
    )
    if _adapter_for_source_state(tuple_state) != adapter_id:
        raise _error("hydration adapter/source-state binding drifted")
    return state


def _validate_finalized_authority(value: Any) -> dict[str, Any]:
    authority = _exact_dict(value, _FINALIZED_AUTHORITY_FIELDS, "finalized V3 hydration authority")
    pins = survey_v3.FINALIZED_V3_SURVEY_AUTHORITY_V1
    expected = {
        "aggregate_artifact_ref": {
            "sha256": pins.aggregate_artifact_sha256,
            "size_bytes": pins.aggregate_size_bytes,
        },
        "aggregate_identity_sha256": pins.aggregate_identity_sha256,
        "control_artifact_ref": {
            "sha256": pins.control_artifact_sha256,
            "size_bytes": pins.control_size_bytes,
        },
        "control_identity_sha256": pins.control_identity_sha256,
        "document_count": pins.document_count,
        "request_count": pins.request_count,
        "sealed_plan_ref": {
            "sha256": pins.sealed_plan_sha256,
            "size_bytes": sentinel.SEALED_PLAN_SIZE_BYTES,
        },
    }
    if not same_typed_json_v1(authority, expected):
        raise _error("finalized V3 hydration authority pins drifted")
    return authority


def _validate_source_binding(value: Any) -> dict[str, Any]:
    binding = _exact_dict(value, _SOURCE_BINDING_FIELDS, "hydration source binding")
    digest = _sha256(binding["source_pdf_sha256"], "hydration source identity")
    if binding["document_id"] != f"sha256:{digest}":
        raise _error("hydration document identity is not source-content-bound")
    _positive_int(binding["source_size_bytes"], "hydration source size")
    _positive_int(binding["physical_page"], "hydration physical page")
    for field in (
        "plan_document_binding_sha256",
        "plan_page_binding_sha256",
        "request_sha256",
    ):
        _sha256(binding[field], f"hydration {field}")
    return binding


def _validate_upstream_binding(value: Any, source_state: dict[str, Any]) -> dict[str, Any]:
    binding = _exact_dict(value, _UPSTREAM_BINDING_FIELDS, "hydration upstream binding")
    _object_ref(binding["backend_payload_ref"], "hydration backend reference")
    _object_ref(binding["result_ref"], "hydration result reference")
    for field in ("line_text_axis_sha256", "page_record_sha256"):
        _sha256(binding[field], f"hydration upstream {field}")
    if binding["raw_provider_payload_sha256"] is not None:
        _sha256(binding["raw_provider_payload_sha256"], "hydration raw provider identity")
    _positive_int(binding["request_ordinal"], "hydration request ordinal")
    if type(binding["unresolved"]) is not bool or binding["status_preserved"] is not True:
        raise _error("hydration upstream status preservation booleans drifted")
    if (
        binding["page_record_format_version"] != "BANK_CORPUS_WAVE_1_ROLE_B_FULL_PAGE_RECORD_V2"
        or binding["result_format_version"] != source_state["result_format_version"]
        or binding["route"] != source_state["route"]
        or binding["status"] != source_state["status"]
        or binding["unresolved"] is not source_state["unresolved"]
        or binding["status_preserved"] is not True
    ):
        raise _error("hydration upstream source-state binding drifted")
    if source_state["render_binding_state"] == "RENDER_PRESENT":
        _object_ref(binding["render_ref"], "hydration upstream render reference", ".png")
        if binding["raw_provider_payload_sha256"] is None:
            raise _error("terminal hydration lacks its raw provider identity")
    elif binding["render_ref"] is not None or binding["raw_provider_payload_sha256"] is not None:
        raise _error("native hydration unexpectedly acquired OCR/render authority")
    return binding


def _validate_coordinate_authority(value: Any, width: int, height: int) -> dict[str, Any]:
    if type(value) is not dict or value.get("pixel_dimensions") != [width, height]:
        raise _error("hydration coordinate authority dimensions drifted")
    required = {
        "canonical_coordinate_system",
        "canonical_origin",
        "displayed_coordinate_system",
        "displayed_dimensions_mpt",
        "displayed_mpt_to_unrotated_mpt",
        "matrix_convention",
        "pdf_rotation_degrees",
        "pixel_coordinate_system",
        "pixel_dimensions",
        "pixel_to_displayed_mpt",
        "pixel_to_unrotated_mpt",
        "unrotated_dimensions_mpt",
        "unrotated_mpt_to_pixel",
    }
    if set(value) != required:
        raise _error("hydration coordinate authority fields drifted")
    if (
        value["matrix_convention"] != "COLUMN_VECTOR_3X3_RATIONAL"
        or value["pixel_coordinate_system"] != "DISPLAYED_PAGE_RASTER_PIXELS_TOP_LEFT"
        or value["canonical_coordinate_system"] != "UNROTATED_PDF_MILLI_POINTS_TOP_LEFT"
        or value["canonical_origin"] != "UNROTATED_CROP_BOX_TOP_LEFT_RELATIVE"
        or type(value["pdf_rotation_degrees"]) is not int
        or value["pdf_rotation_degrees"] not in {0, 90, 180, 270}
    ):
        raise _error("hydration coordinate authority identity drifted")
    for matrix_name in (
        "displayed_mpt_to_unrotated_mpt",
        "pixel_to_displayed_mpt",
        "pixel_to_unrotated_mpt",
        "unrotated_mpt_to_pixel",
    ):
        matrix = value[matrix_name]
        if (
            type(matrix) is not list
            or len(matrix) != 3
            or any(type(row) is not list or len(row) != 3 for row in matrix)
        ):
            raise _error("hydration coordinate matrix shape drifted")
        for row in matrix:
            for coefficient in row:
                record = _exact_dict(
                    coefficient, {"denominator", "numerator"}, "coordinate coefficient"
                )
                if (
                    type(record["numerator"]) is not int
                    or type(record["denominator"]) is not int
                    or record["denominator"] <= 0
                ):
                    raise _error("hydration coordinate coefficient drifted")
    for dimension_name in ("displayed_dimensions_mpt", "unrotated_dimensions_mpt"):
        dimensions = value[dimension_name]
        if (
            type(dimensions) is not list
            or len(dimensions) != 2
            or any(type(item) is not int or item <= 0 for item in dimensions)
        ):
            raise _error("hydration canonical dimensions drifted")
    return cast(dict[str, Any], value)


def validate_line_pixel_hydration_envelope_v1(value: Any) -> dict[str, Any]:
    """Validate the closed geometry envelope shape, without granting authority."""

    envelope = _exact_dict(value, _ENVELOPE_FIELDS, "line-pixel hydration envelope")
    if (
        envelope["format_version"] != ENVELOPE_FORMAT_VERSION
        or envelope["claim_boundary"] != _CLAIM_BOUNDARY
        or envelope["adapter_id"] not in {_NATIVE_ADAPTER_ID, _TERMINAL_ADAPTER_ID}
    ):
        raise _error("line-pixel hydration envelope identity drifted")
    identifier = envelope["envelope_id"]
    if (
        type(identifier) is not str
        or not identifier.startswith(_ENVELOPE_ID_PREFIX)
        or _SHA256_RE.fullmatch(identifier.removeprefix(_ENVELOPE_ID_PREFIX)) is None
        or identifier
        != _ENVELOPE_ID_PREFIX
        + canonical_json_sha256_v1(
            {key: item for key, item in envelope.items() if key != "envelope_id"}
        )
    ):
        raise _error("line-pixel hydration envelope content identity drifted")
    source_state = _validate_source_state_payload(envelope["source_state"], envelope["adapter_id"])
    _validate_finalized_authority(envelope["finalized_v3_authority"])
    _validate_source_binding(envelope["source_binding"])
    upstream = _validate_upstream_binding(envelope["upstream_binding"], source_state)
    render = _exact_dict(envelope["render_binding"], _RENDER_BINDING_FIELDS, "render binding")
    _sha256(render["sha256"], "hydration render identity")
    _positive_int(render["size_bytes"], "hydration render size")
    width = _positive_int(render["pixel_width"], "hydration render width")
    height = _positive_int(render["pixel_height"], "hydration render height")
    if type(render["dpi"]) is not int or render["dpi"] not in {200, 300}:
        raise _error("hydration render DPI drifted")
    expected_profile = {
        "alpha": False,
        "annotations": "INCLUDED",
        "colorspace": "RGB",
        "source": "FULL_COMPOSITED_DISPLAYED_PDF_PAGE",
    }
    if not same_typed_json_v1(render["render_profile"], expected_profile):
        raise _error("hydration render profile drifted")
    if not same_typed_json_v1(render["upstream_render_ref"], upstream["render_ref"]):
        raise _error("hydration render/upstream reference binding drifted")
    if source_state["render_binding_state"] == "RENDER_PRESENT":
        if render["origin"] != "EXACT_UPSTREAM_RENDER_REPRODUCED_FROM_SOURCE":
            raise _error("terminal hydration render origin drifted")
    elif (
        render["origin"] != "DETERMINISTIC_SOURCE_REPLAY_FOR_NATIVE_GEOMETRY"
        or render["dpi"] != 200
    ):
        raise _error("native hydration render origin/profile drifted")
    authority = _validate_coordinate_authority(envelope["coordinate_authority"], width, height)
    unrotated_width, unrotated_height = authority["unrotated_dimensions_mpt"]
    lines = envelope["lines"]
    if type(lines) is not list or not lines:
        raise _error("hydration line denominator must be positive")
    for index, line_value in enumerate(lines):
        line = _exact_dict(line_value, _LINE_FIELDS, f"hydration line {index}")
        if line["line_index"] != index:
            raise _error("hydration line order drifted")
        _sha256(line["source_geometry_sha256"], f"hydration line {index} geometry identity")
        pixel_box = line["raw_pixel_bbox"]
        if (
            type(pixel_box) is not list
            or len(pixel_box) != 4
            or any(type(item) is not int for item in pixel_box)
            or not (
                0 <= pixel_box[0] < pixel_box[2] <= width
                and 0 <= pixel_box[1] < pixel_box[3] <= height
            )
        ):
            raise _error("hydration line pixel bbox drifted")
        _validate_canonical_bbox(
            line["canonical_bbox_mpt"],
            unrotated_width,
            unrotated_height,
            f"hydration line {index} canonical bbox",
        )
    metrics = _exact_dict(envelope["metrics"], _METRIC_FIELDS, "hydration metrics")
    for field in _METRIC_FIELDS:
        _nonnegative_int(metrics[field], f"hydration metric {field}")
    if (
        metrics["emitted_line_count"] != len(lines)
        or metrics["authenticated_source_line_axis_count"] != len(lines)
        or metrics["excluded_line_count"] != 0
        or (
            envelope["adapter_id"] == _NATIVE_ADAPTER_ID
            and metrics["upstream_public_line_axis_count"] != len(lines)
        )
        or (
            envelope["adapter_id"] == _TERMINAL_ADAPTER_ID
            and metrics["upstream_public_line_axis_count"] != 0
        )
    ):
        raise _error("hydration line denominator accounting drifted")
    quarantine = _exact_dict(envelope["quarantine"], _QUARANTINE_FIELDS, "hydration quarantine")
    _nonnegative_int(quarantine["source_word_axis_count"], "hydration source word count")
    _sha256(quarantine["word_axis_sha256"], "hydration hidden word-axis identity")
    if (
        quarantine["word_geometry_exposed"] is not False
        or quarantine["word_text_exposed"] is not False
        or quarantine["terminal_word_geometry_failure_preserved"]
        is not (envelope["adapter_id"] == _TERMINAL_ADAPTER_ID)
    ):
        raise _error("hydration word quarantine boundary drifted")
    authority_claims = _exact_dict(envelope["authority"], _AUTHORITY_FIELDS, "hydration authority")
    if not same_typed_json_v1(authority_claims, _AUTHORITY):
        raise _error("hydration claim authority drifted")
    return canonical_clone_v1(envelope)


def _receipt_from_envelope(envelope: dict[str, Any], render_payload: bytes) -> dict[str, Any]:
    envelope_payload = _canonical_bytes(envelope)
    receipt = {
        "format_version": RECEIPT_FORMAT_VERSION,
        "claim_boundary": _CLAIM_BOUNDARY,
        "receipt_id": _RECEIPT_ID_PREFIX + "0" * 64,
        "adapter_id": envelope["adapter_id"],
        "source_locator": {
            "physical_page": envelope["source_binding"]["physical_page"],
            "source_pdf_sha256": envelope["source_binding"]["source_pdf_sha256"],
            "source_size_bytes": envelope["source_binding"]["source_size_bytes"],
        },
        "envelope_ref": {
            "sha256": hashlib.sha256(envelope_payload).hexdigest(),
            "size_bytes": len(envelope_payload),
        },
        "render_ref": {
            "sha256": hashlib.sha256(render_payload).hexdigest(),
            "size_bytes": len(render_payload),
        },
        "upstream_backend_ref": canonical_clone_v1(
            envelope["upstream_binding"]["backend_payload_ref"]
        ),
        "upstream_result_ref": canonical_clone_v1(envelope["upstream_binding"]["result_ref"]),
        "upstream_status": envelope["upstream_binding"]["status"],
        "emitted_line_count": envelope["metrics"]["emitted_line_count"],
        "line_axis_sha256": canonical_json_sha256_v1(envelope["lines"]),
        "authority": canonical_clone_v1(_RECEIPT_AUTHORITY),
    }
    receipt["receipt_id"] = _RECEIPT_ID_PREFIX + canonical_json_sha256_v1(
        {key: value for key, value in receipt.items() if key != "receipt_id"}
    )
    return _validate_receipt(receipt)


def _validate_receipt(value: Any) -> dict[str, Any]:
    receipt = _exact_dict(value, _RECEIPT_FIELDS, "hydration receipt")
    if (
        receipt["format_version"] != RECEIPT_FORMAT_VERSION
        or receipt["claim_boundary"] != _CLAIM_BOUNDARY
        or receipt["adapter_id"] not in {_NATIVE_ADAPTER_ID, _TERMINAL_ADAPTER_ID}
    ):
        raise _error("hydration receipt identity drifted")
    identifier = receipt["receipt_id"]
    if (
        type(identifier) is not str
        or not identifier.startswith(_RECEIPT_ID_PREFIX)
        or _SHA256_RE.fullmatch(identifier.removeprefix(_RECEIPT_ID_PREFIX)) is None
        or identifier
        != _RECEIPT_ID_PREFIX
        + canonical_json_sha256_v1(
            {key: item for key, item in receipt.items() if key != "receipt_id"}
        )
    ):
        raise _error("hydration receipt content identity drifted")
    locator = _exact_dict(receipt["source_locator"], _SOURCE_LOCATOR_FIELDS, "source locator")
    _sha256(locator["source_pdf_sha256"], "receipt source identity")
    _positive_int(locator["source_size_bytes"], "receipt source size")
    _positive_int(locator["physical_page"], "receipt physical page")
    _content_ref(receipt["envelope_ref"], "receipt envelope reference")
    _content_ref(receipt["render_ref"], "receipt render reference")
    _object_ref(receipt["upstream_backend_ref"], "receipt upstream backend reference")
    _object_ref(receipt["upstream_result_ref"], "receipt upstream result reference")
    _positive_int(receipt["emitted_line_count"], "receipt emitted line count")
    _sha256(receipt["line_axis_sha256"], "receipt line-axis identity")
    authority = _exact_dict(
        receipt["authority"], _RECEIPT_AUTHORITY_FIELDS, "hydration receipt authority"
    )
    if not same_typed_json_v1(authority, _RECEIPT_AUTHORITY):
        raise _error("hydration receipt authority drifted")
    return canonical_clone_v1(receipt)


_MINT_TOKEN = object()


class AuthenticatedLinePixelHydrationReceiptV1:
    """Opaque live authority over one exact envelope, receipt, and render."""

    __slots__ = ("__weakref__",)

    def __init__(self, token: object) -> None:
        if token is not _MINT_TOKEN:
            raise _error("authenticated hydration receipt cannot be caller-constructed")

    def __copy__(self) -> None:
        raise _error("authenticated hydration receipt cannot be copied")

    def __deepcopy__(self, _memo: object) -> None:
        raise _error("authenticated hydration receipt cannot be deep-copied")

    def __reduce__(self) -> None:
        raise _error("authenticated hydration receipt cannot be serialized")

    def __reduce_ex__(self, _protocol: int) -> None:
        raise _error("authenticated hydration receipt cannot be serialized")


_AUTHENTICATED_HYDRATIONS: weakref.WeakKeyDictionary[
    AuthenticatedLinePixelHydrationReceiptV1,
    tuple[bytes, str, bytes, str, bytes, str],
] = weakref.WeakKeyDictionary()


def _mint(
    envelope: dict[str, Any], render_payload: bytes
) -> AuthenticatedLinePixelHydrationReceiptV1:
    validated = validate_line_pixel_hydration_envelope_v1(envelope)
    if type(render_payload) is not bytes or (
        len(render_payload) != validated["render_binding"]["size_bytes"]
        or hashlib.sha256(render_payload).hexdigest() != validated["render_binding"]["sha256"]
    ):
        raise _error("hydration render bytes differ from the envelope render binding")
    receipt = _receipt_from_envelope(validated, render_payload)
    envelope_payload = _canonical_bytes(validated)
    receipt_payload = _canonical_bytes(receipt)
    capability = AuthenticatedLinePixelHydrationReceiptV1(_MINT_TOKEN)
    _AUTHENTICATED_HYDRATIONS[capability] = (
        envelope_payload,
        hashlib.sha256(envelope_payload).hexdigest(),
        receipt_payload,
        hashlib.sha256(receipt_payload).hexdigest(),
        bytes(render_payload),
        hashlib.sha256(render_payload).hexdigest(),
    )
    return capability


def _authenticated_payloads(
    capability: AuthenticatedLinePixelHydrationReceiptV1,
) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    if type(capability) is not AuthenticatedLinePixelHydrationReceiptV1:
        raise _error("hydration authority requires one exact opaque capability type")
    stored = _AUTHENTICATED_HYDRATIONS.get(capability)
    if stored is None:
        raise _error("authenticated hydration capability is unknown or expired")
    envelope_payload, envelope_digest, receipt_payload, receipt_digest, render, render_digest = (
        stored
    )
    if (
        hashlib.sha256(envelope_payload).hexdigest() != envelope_digest
        or hashlib.sha256(receipt_payload).hexdigest() != receipt_digest
        or hashlib.sha256(render).hexdigest() != render_digest
    ):
        raise _error("authenticated hydration capability bytes drifted")
    envelope = validate_line_pixel_hydration_envelope_v1(
        _strict_canonical_json(envelope_payload, "authenticated hydration envelope")
    )
    receipt = _validate_receipt(
        _strict_canonical_json(receipt_payload, "authenticated hydration receipt")
    )
    expected = _receipt_from_envelope(envelope, render)
    if not same_typed_json_v1(receipt, expected):
        raise _error("authenticated hydration envelope/receipt/render binding drifted")
    return envelope, receipt, bytes(render)


def read_authenticated_line_pixel_hydration_envelope_v1(
    capability: AuthenticatedLinePixelHydrationReceiptV1,
) -> dict[str, Any]:
    """Read the exact envelope bound to a live opaque capability."""

    envelope, _receipt, _render = _authenticated_payloads(capability)
    return envelope


def project_authenticated_line_pixel_hydration_receipt_v1(
    capability: AuthenticatedLinePixelHydrationReceiptV1,
) -> dict[str, Any]:
    """Project a closed receipt; the projection alone grants no authority."""

    _envelope, receipt, _render = _authenticated_payloads(capability)
    return receipt


def read_authenticated_line_pixel_hydration_render_v1(
    capability: AuthenticatedLinePixelHydrationReceiptV1,
) -> bytes:
    """Read the exact deterministic PNG bytes bound to a live capability."""

    _envelope, _receipt, render = _authenticated_payloads(capability)
    return render


def validate_authenticated_line_pixel_hydration_envelope_v1(
    value: Any,
    capability: AuthenticatedLinePixelHydrationReceiptV1,
) -> dict[str, Any]:
    """Require byte equality with the envelope held by a live capability."""

    candidate = validate_line_pixel_hydration_envelope_v1(value)
    expected, _receipt, _render = _authenticated_payloads(capability)
    if _canonical_bytes(candidate) != _canonical_bytes(expected):
        raise _error("line-pixel hydration envelope differs from live replay authority")
    return candidate


def _load_authenticated_inputs_v1(
    project_root: Path,
    *,
    source_pdf_sha256: str,
    physical_page: int,
) -> _AuthenticatedInputs:
    plan_payload = _stable_nofollow_bytes(
        project_root, sentinel.SEALED_PLAN_RELATIVE_PATH, "sealed page-read plan"
    )
    if (
        len(plan_payload) != sentinel.SEALED_PLAN_SIZE_BYTES
        or hashlib.sha256(plan_payload).hexdigest() != sentinel.SEALED_PLAN_SHA256
    ):
        raise _error("sealed page-read plan byte identity drifted")
    plan = _strict_canonical_json(plan_payload, "sealed page-read plan")
    plan_document, plan_page, source_relative = _validate_plan_and_select_source(
        plan,
        source_pdf_sha256=source_pdf_sha256,
        physical_page=physical_page,
    )
    source_payload = _stable_nofollow_bytes(project_root, source_relative, "source PDF")
    if (
        len(source_payload) != plan_document["size_bytes"]
        or hashlib.sha256(source_payload).hexdigest() != source_pdf_sha256
    ):
        raise _error("source PDF byte identity drifted")

    pins = survey_v3.FINALIZED_V3_SURVEY_AUTHORITY_V1
    try:
        with full_v3._v3_read_only_output_snapshot(  # noqa: SLF001
            project_root, list(pins.document_ids)
        ):
            manifest_before = full_v3._v3_output_live_manifest(project_root)  # noqa: SLF001
            with full_v3._v3_bind_output_reads(project_root, manifest_before):  # noqa: SLF001
                authority = survey_v3._authenticate_finalized_authority(  # noqa: SLF001
                    project_root, pins
                )
                matches = [
                    record
                    for record in authority.page_records
                    if record.get("source_sha256") == source_pdf_sha256
                    and record.get("physical_page") == physical_page
                ]
                if len(matches) != 1:
                    raise _error("source/page is not unique in finalized V3 authority")
                page_record = canonical_clone_v1(matches[0])
                authenticated_page = survey_v3._load_authenticated_page(  # noqa: SLF001
                    project_root, authority.control, page_record
                )
                result_payload, _result_identity = full_v3._v3_read_object(  # noqa: SLF001
                    project_root,
                    page_record["result_ref"],
                    ".json",
                    "hydration finalized result",
                )
                page_result = full_v3._json_object(  # noqa: SLF001
                    result_payload, "hydration finalized result"
                )
                backend_payload, _backend_identity = full_v3._v3_read_object(  # noqa: SLF001
                    project_root,
                    page_record["backend_payload_ref"],
                    ".json",
                    "hydration finalized backend",
                )
                backend = full_v3._json_object(  # noqa: SLF001
                    backend_payload, "hydration finalized backend"
                )
                if page_record["render_ref"] is None:
                    upstream_render_payload = None
                else:
                    upstream_render_payload, _render_identity = full_v3._v3_read_object(  # noqa: SLF001
                        project_root,
                        page_record["render_ref"],
                        ".png",
                        "hydration finalized render",
                    )
                if not same_typed_json_v1(authenticated_page.page_record, page_record) or not (
                    same_typed_json_v1(authenticated_page.page_result, page_result)
                ):
                    raise _error("finalized V3 target page changed across authenticated reads")
                control = canonical_clone_v1(authority.control)
            manifest_after = full_v3._v3_output_live_manifest(project_root)  # noqa: SLF001
            if not same_typed_json_v1(manifest_after, manifest_before):
                raise _error("finalized V3 output changed during hydration replay")
    except (
        full_v3.WaveOneRoleBFullReaderError,
        survey_v3.FinalizedV3SurveyStreamError,
    ) as exc:
        raise _error("finalized V3 authority could not be replayed") from exc

    if (
        _stable_nofollow_bytes(project_root, sentinel.SEALED_PLAN_RELATIVE_PATH, "final plan")
        != plan_payload
        or _stable_nofollow_bytes(project_root, source_relative, "final source PDF")
        != source_payload
    ):
        raise _error("plan or source PDF changed during hydration replay")
    return _AuthenticatedInputs(
        control=control,
        plan_payload=plan_payload,
        plan_document=plan_document,
        plan_page=plan_page,
        page_record=page_record,
        page_result=page_result,
        page_result_payload=result_payload,
        backend=backend,
        backend_payload=backend_payload,
        source_payload=source_payload,
        upstream_render_payload=upstream_render_payload,
    )


def replay_authenticated_line_pixel_hydration_v1(
    project_root: Path,
    *,
    source_pdf_sha256: str,
    physical_page: int,
) -> tuple[dict[str, Any], AuthenticatedLinePixelHydrationReceiptV1]:
    """Replay one neutral source locator and mint geometry-only live authority."""

    if not isinstance(project_root, Path):
        raise _error("project root must be one pathlib Path")
    if type(source_pdf_sha256) is not str:
        raise _error("source selector must be one exact SHA-256 string")
    _sha256(source_pdf_sha256, "source selector")
    _positive_int(physical_page, "physical-page selector")
    try:
        root = project_root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise _error("project root cannot be resolved") from exc
    if not root.is_dir():
        raise _error("project root is not a directory")
    inputs = _load_authenticated_inputs_v1(
        root,
        source_pdf_sha256=source_pdf_sha256,
        physical_page=physical_page,
    )
    envelope, render_payload = _build_authenticated_line_pixel_hydration_v1(inputs)
    capability = _mint(envelope, render_payload)
    return envelope, capability
