"""Offline contract for a bounded Google OCR structure challenger.

This module never contacts Google, reads credentials, or authorizes/uploads a
page.  It has two deliberately narrow jobs:

* bind a prospective request to one caller-authenticated, still-unresolved
  page image and exact provider/processor/version/region/prompt/config refs;
* normalize an already-captured response into provider-neutral text,
  hierarchy, geometry, and table evidence.

The normalized result is only a challenger.  In particular it cannot establish
numeric values, mappings, or absence; the existing accounting graph must
validate every proposed structure before use.  JSON response parsing is closed
over the documented REST shapes used here.  Duplicate keys, alternate casing,
unknown wrappers, ambiguous unions, non-finite numbers, and inconsistent pixel
versus normalized coordinates fail closed.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import StrEnum
from hashlib import sha256
from types import MappingProxyType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

__all__ = [
    "FORMAT_VERSION",
    "OUTPUT_AUTHORITY",
    "PLAN_CLAIM_BOUNDARY",
    "AuthenticatedUnresolvedPageV1",
    "ContentRefKindV1",
    "ExactContentRefV1",
    "GoogleOcrProfileV1",
    "GoogleOcrReleaseChannelV1",
    "GoogleOcrRescueContractV1Error",
    "GoogleOcrRescuePlanV1",
    "GoogleOcrRouteV1",
    "PageAuthenticationStateV1",
    "PageResolutionStateV1",
    "build_google_ocr_rescue_plan_v1",
    "normalize_google_ocr_response_v1",
    "validate_google_ocr_rescue_plan_v1",
]


FORMAT_VERSION = "GOOGLE_OCR_RESCUE_CHALLENGER_V1"
PLAN_FORMAT_VERSION = "GOOGLE_OCR_RESCUE_REQUEST_PLAN_V1"
PLAN_CLAIM_BOUNDARY = (
    "OFFLINE_PLAN_ONLY_CALLER_MUST_SUPPLY_CURRENT_AUTHENTICATED_REFS_"
    "NO_UPLOAD_AUTHORIZATION_NO_PROVIDER_EXECUTION"
)
_TASK = (
    "Extract source-visible Vietnamese text, hierarchy, geometry, and table structure "
    "from this one unresolved page. Do not infer, map, correct, or invent values."
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_POSITIVE_INDEX = re.compile(r"^(0|[1-9][0-9]*)$")
_MAX_RESPONSE_BYTES = 64 * 1024 * 1024
_PPM = 1_000_000
_ORIENTATIONS = {
    "ORIENTATION_UNSPECIFIED",
    "PAGE_UP",
    "PAGE_RIGHT",
    "PAGE_DOWN",
    "PAGE_LEFT",
}
_BREAK_TYPES = {
    "UNKNOWN",
    "SPACE",
    "SURE_SPACE",
    "EOL_SURE_SPACE",
    "HYPHEN",
    "LINE_BREAK",
    "TYPE_UNSPECIFIED",
    "WIDE_SPACE",
}
_TEXT_BLOCK_TYPES = {
    "paragraph",
    "subtitle",
    "heading-1",
    "heading-2",
    "heading-3",
    "heading-4",
    "heading-5",
    "header",
    "footer",
}

OUTPUT_AUTHORITY: Mapping[str, bool] = MappingProxyType(
    {
        "source_text_structure_challenger": True,
        "numeric_authority": False,
        "mapping_authority": False,
        "absence_authority": False,
        "graph_validation_required": True,
    }
)


class GoogleOcrRescueContractV1Error(ValueError):
    """A request plan or provider response crossed the closed contract."""


class GoogleOcrRouteV1(StrEnum):
    CLOUD_VISION_DOCUMENT_TEXT_DETECTION = "CLOUD_VISION_DOCUMENT_TEXT_DETECTION"
    DOCUMENT_AI_OCR_PROCESSOR = "DOCUMENT_AI_OCR_PROCESSOR"
    DOCUMENT_AI_LAYOUT_PARSER = "DOCUMENT_AI_LAYOUT_PARSER"


class GoogleOcrReleaseChannelV1(StrEnum):
    STABLE = "STABLE"
    PREVIEW = "PREVIEW"


class ContentRefKindV1(StrEnum):
    SOURCE_PAGE = "SOURCE_PAGE"
    PAGE_IMAGE = "PAGE_IMAGE"
    AUTHENTICATION_RECEIPT = "AUTHENTICATION_RECEIPT"
    UNRESOLVED_GRAPH = "UNRESOLVED_GRAPH"
    PROVIDER = "PROVIDER"
    PROCESSOR = "PROCESSOR"
    PROCESSOR_VERSION = "PROCESSOR_VERSION"
    REGION = "REGION"
    PROMPT = "PROMPT"
    CONFIG = "CONFIG"


class PageAuthenticationStateV1(StrEnum):
    CALLER_AUTHENTICATED_CURRENT_REFS = "CALLER_AUTHENTICATED_CURRENT_REFS"


class PageResolutionStateV1(StrEnum):
    UNRESOLVED_AFTER_DETERMINISTIC_GRAPH = "UNRESOLVED_AFTER_DETERMINISTIC_GRAPH"


@dataclass(frozen=True, slots=True)
class ExactContentRefV1:
    kind: ContentRefKindV1
    logical_id: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class AuthenticatedUnresolvedPageV1:
    document_id: str
    page_id: str
    physical_page: int
    pixel_width: int
    pixel_height: int
    mime_type: str
    source_page_ref: ExactContentRefV1
    page_image_ref: ExactContentRefV1
    authentication_receipt_ref: ExactContentRefV1
    unresolved_graph_ref: ExactContentRefV1
    authentication_state: PageAuthenticationStateV1
    resolution_state: PageResolutionStateV1
    unresolved_reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GoogleOcrProfileV1:
    route: GoogleOcrRouteV1
    provider_name: str
    processor_name: str
    processor_version: str
    region: str
    release_channel: GoogleOcrReleaseChannelV1
    uses_global_endpoint: bool
    data_residency_compliant: bool | None
    provider_ref: ExactContentRefV1
    processor_ref: ExactContentRefV1
    processor_version_ref: ExactContentRefV1
    region_ref: ExactContentRefV1
    prompt_ref: ExactContentRefV1
    config_ref: ExactContentRefV1


@dataclass(frozen=True, slots=True)
class GoogleOcrRescuePlanV1:
    format_version: str
    claim_boundary: str
    task: str
    page: AuthenticatedUnresolvedPageV1
    profile: GoogleOcrProfileV1
    external_upload_requires_explicit_authorization: bool
    external_upload_authorized_by_plan: bool
    network_call_performed: bool
    credentials_accessed: bool
    image_bytes_embedded: bool
    execution_state: str
    data_residency_warning: str
    plan_id: str


def _error(message: str) -> GoogleOcrRescueContractV1Error:
    return GoogleOcrRescueContractV1Error(message)


def _require_exact_dict(value: Any, *, allowed: set[str], required: set[str], label: str) -> dict:
    if type(value) is not dict:
        raise _error(f"{label} must be one JSON object")
    keys = set(value)
    if not required <= keys or not keys <= allowed:
        missing = sorted(required - keys)
        unknown = sorted(keys - allowed)
        raise _error(f"{label} fields drifted; missing={missing}, unknown={unknown}")
    return value


def _require_list(value: Any, label: str) -> list:
    if type(value) is not list:
        raise _error(f"{label} must be one JSON array")
    return value


def _require_string(value: Any, label: str, *, allow_empty: bool = False) -> str:
    if type(value) is not str or (not allow_empty and not value):
        raise _error(f"{label} must be one {'possibly empty ' if allow_empty else ''}string")
    return value


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} must be one positive exact integer")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise _error(f"{label} must be one nonnegative exact integer")
    return value


def _content_ref(ref: ExactContentRefV1, expected: ContentRefKindV1, label: str) -> None:
    if type(ref) is not ExactContentRefV1 or ref.kind is not expected:
        raise _error(f"{label} must be an exact {expected.value} content ref")
    _require_string(ref.logical_id, f"{label}.logical_id")
    if type(ref.sha256) is not str or _SHA256.fullmatch(ref.sha256) is None:
        raise _error(f"{label}.sha256 must be lowercase SHA-256")
    if type(ref.size_bytes) is not int or ref.size_bytes < 0:
        raise _error(f"{label}.size_bytes must be one nonnegative exact integer")


def _ref_projection(ref: ExactContentRefV1) -> dict[str, Any]:
    return {
        "kind": ref.kind.value,
        "logical_id": ref.logical_id,
        "sha256": ref.sha256,
        "size_bytes": ref.size_bytes,
    }


def _validate_page(page: AuthenticatedUnresolvedPageV1) -> None:
    if type(page) is not AuthenticatedUnresolvedPageV1:
        raise _error("page must be AuthenticatedUnresolvedPageV1")
    _require_string(page.document_id, "page.document_id")
    _require_string(page.page_id, "page.page_id")
    _positive_int(page.physical_page, "page.physical_page")
    _positive_int(page.pixel_width, "page.pixel_width")
    _positive_int(page.pixel_height, "page.pixel_height")
    if page.mime_type not in {"image/png", "image/jpeg", "image/tiff", "application/pdf"}:
        raise _error("page.mime_type is not an allowed one-page image/PDF MIME type")
    _content_ref(page.source_page_ref, ContentRefKindV1.SOURCE_PAGE, "source_page_ref")
    _content_ref(page.page_image_ref, ContentRefKindV1.PAGE_IMAGE, "page_image_ref")
    _content_ref(
        page.authentication_receipt_ref,
        ContentRefKindV1.AUTHENTICATION_RECEIPT,
        "authentication_receipt_ref",
    )
    _content_ref(
        page.unresolved_graph_ref,
        ContentRefKindV1.UNRESOLVED_GRAPH,
        "unresolved_graph_ref",
    )
    if page.authentication_state is not PageAuthenticationStateV1.CALLER_AUTHENTICATED_CURRENT_REFS:
        raise _error("page is not bound to caller-current authenticated refs")
    if page.resolution_state is not PageResolutionStateV1.UNRESOLVED_AFTER_DETERMINISTIC_GRAPH:
        raise _error("OCR rescue is allowed only after the deterministic graph is unresolved")
    if (
        type(page.unresolved_reason_codes) is not tuple
        or not page.unresolved_reason_codes
        or any(type(item) is not str or not item for item in page.unresolved_reason_codes)
        or tuple(sorted(set(page.unresolved_reason_codes))) != page.unresolved_reason_codes
    ):
        raise _error("unresolved_reason_codes must be one nonempty sorted unique string tuple")


def _validate_profile(profile: GoogleOcrProfileV1) -> None:
    if type(profile) is not GoogleOcrProfileV1:
        raise _error("profile must be GoogleOcrProfileV1")
    if type(profile.route) is not GoogleOcrRouteV1:
        raise _error("profile.route drifted")
    _require_string(profile.provider_name, "profile.provider_name")
    _require_string(profile.processor_name, "profile.processor_name")
    _require_string(profile.processor_version, "profile.processor_version")
    _require_string(profile.region, "profile.region")
    if type(profile.release_channel) is not GoogleOcrReleaseChannelV1:
        raise _error("profile.release_channel drifted")
    if type(profile.uses_global_endpoint) is not bool:
        raise _error("profile.uses_global_endpoint must be exact boolean")
    if (
        profile.data_residency_compliant is not None
        and type(profile.data_residency_compliant) is not bool
    ):
        raise _error("profile.data_residency_compliant must be boolean or null")
    if profile.uses_global_endpoint != (profile.region.casefold() == "global"):
        raise _error("profile region and global-endpoint declaration disagree")
    if (
        profile.release_channel is GoogleOcrReleaseChannelV1.PREVIEW
        and profile.uses_global_endpoint
        and profile.data_residency_compliant is not False
    ):
        raise _error("preview global profile must explicitly declare non-compliant Data Residency")
    if (
        profile.route is GoogleOcrRouteV1.CLOUD_VISION_DOCUMENT_TEXT_DETECTION
        and profile.processor_name != "DOCUMENT_TEXT_DETECTION"
    ):
        raise _error("Cloud Vision route must pin DOCUMENT_TEXT_DETECTION")
    for ref, kind, label in (
        (profile.provider_ref, ContentRefKindV1.PROVIDER, "provider_ref"),
        (profile.processor_ref, ContentRefKindV1.PROCESSOR, "processor_ref"),
        (
            profile.processor_version_ref,
            ContentRefKindV1.PROCESSOR_VERSION,
            "processor_version_ref",
        ),
        (profile.region_ref, ContentRefKindV1.REGION, "region_ref"),
        (profile.prompt_ref, ContentRefKindV1.PROMPT, "prompt_ref"),
        (profile.config_ref, ContentRefKindV1.CONFIG, "config_ref"),
    ):
        _content_ref(ref, kind, label)


def _page_projection(page: AuthenticatedUnresolvedPageV1) -> dict[str, Any]:
    return {
        "document_id": page.document_id,
        "page_id": page.page_id,
        "physical_page": page.physical_page,
        "pixel_width": page.pixel_width,
        "pixel_height": page.pixel_height,
        "mime_type": page.mime_type,
        "source_page_ref": _ref_projection(page.source_page_ref),
        "page_image_ref": _ref_projection(page.page_image_ref),
        "authentication_receipt_ref": _ref_projection(page.authentication_receipt_ref),
        "unresolved_graph_ref": _ref_projection(page.unresolved_graph_ref),
        "authentication_state": page.authentication_state.value,
        "resolution_state": page.resolution_state.value,
        "unresolved_reason_codes": list(page.unresolved_reason_codes),
    }


def _profile_projection(profile: GoogleOcrProfileV1) -> dict[str, Any]:
    return {
        "route": profile.route.value,
        "provider_name": profile.provider_name,
        "processor_name": profile.processor_name,
        "processor_version": profile.processor_version,
        "region": profile.region,
        "release_channel": profile.release_channel.value,
        "uses_global_endpoint": profile.uses_global_endpoint,
        "data_residency_compliant": profile.data_residency_compliant,
        "provider_ref": _ref_projection(profile.provider_ref),
        "processor_ref": _ref_projection(profile.processor_ref),
        "processor_version_ref": _ref_projection(profile.processor_version_ref),
        "region_ref": _ref_projection(profile.region_ref),
        "prompt_ref": _ref_projection(profile.prompt_ref),
        "config_ref": _ref_projection(profile.config_ref),
    }


def _residency_warning(profile: GoogleOcrProfileV1) -> str:
    if (
        profile.release_channel is GoogleOcrReleaseChannelV1.PREVIEW
        and profile.uses_global_endpoint
    ):
        return (
            "PREVIEW_GLOBAL_ENDPOINT_NOT_DATA_RESIDENCY_COMPLIANT_"
            "EXPLICIT_UPLOAD_AUTHORIZATION_REQUIRED"
        )
    if profile.uses_global_endpoint:
        return "GLOBAL_ENDPOINT_DATA_RESIDENCY_NOT_ASSURED_EXPLICIT_UPLOAD_AUTHORIZATION_REQUIRED"
    if profile.data_residency_compliant is not True:
        return "DATA_RESIDENCY_UNVERIFIED_EXPLICIT_UPLOAD_AUTHORIZATION_REQUIRED"
    return "REGIONAL_DATA_RESIDENCY_PROFILE_STILL_REQUIRES_EXPLICIT_UPLOAD_AUTHORIZATION"


def _plan_payload(plan: GoogleOcrRescuePlanV1) -> dict[str, Any]:
    return {
        "format_version": plan.format_version,
        "claim_boundary": plan.claim_boundary,
        "task": plan.task,
        "page": _page_projection(plan.page),
        "profile": _profile_projection(plan.profile),
        "privacy": {
            "external_upload_requires_explicit_authorization": (
                plan.external_upload_requires_explicit_authorization
            ),
            "external_upload_authorized_by_plan": plan.external_upload_authorized_by_plan,
            "network_call_performed": plan.network_call_performed,
            "credentials_accessed": plan.credentials_accessed,
            "image_bytes_embedded": plan.image_bytes_embedded,
        },
        "execution_state": plan.execution_state,
        "data_residency_warning": plan.data_residency_warning,
    }


def validate_google_ocr_rescue_plan_v1(plan: GoogleOcrRescuePlanV1) -> None:
    """Validate a plan and independently rebuild its content-addressed ID."""

    if type(plan) is not GoogleOcrRescuePlanV1:
        raise _error("plan must be GoogleOcrRescuePlanV1")
    if plan.format_version != PLAN_FORMAT_VERSION or plan.claim_boundary != PLAN_CLAIM_BOUNDARY:
        raise _error("plan format or claim boundary drifted")
    if plan.task != _TASK or len(plan.task) > 240:
        raise _error("plan task drifted from the short extraction-only instruction")
    _validate_page(plan.page)
    _validate_profile(plan.profile)
    if (
        plan.external_upload_requires_explicit_authorization is not True
        or plan.external_upload_authorized_by_plan is not False
        or plan.network_call_performed is not False
        or plan.credentials_accessed is not False
        or plan.image_bytes_embedded is not False
        or plan.execution_state != "PLANNED_NOT_EXECUTED"
        or plan.data_residency_warning != _residency_warning(plan.profile)
    ):
        raise _error("plan privacy, execution, or Data Residency boundary drifted")
    expected = f"gocrpv1:plan:{canonical_json_sha256_v1(_plan_payload(plan))}"
    if plan.plan_id != expected:
        raise _error("plan_id does not bind the exact caller refs and profile refs")


def build_google_ocr_rescue_plan_v1(
    *, page: AuthenticatedUnresolvedPageV1, profile: GoogleOcrProfileV1
) -> GoogleOcrRescuePlanV1:
    """Build, but never execute or authorize, one single-page rescue request."""

    _validate_page(page)
    _validate_profile(profile)
    shell = GoogleOcrRescuePlanV1(
        format_version=PLAN_FORMAT_VERSION,
        claim_boundary=PLAN_CLAIM_BOUNDARY,
        task=_TASK,
        page=page,
        profile=profile,
        external_upload_requires_explicit_authorization=True,
        external_upload_authorized_by_plan=False,
        network_call_performed=False,
        credentials_accessed=False,
        image_bytes_embedded=False,
        execution_state="PLANNED_NOT_EXECUTED",
        data_residency_warning=_residency_warning(profile),
        plan_id="",
    )
    plan = replace(
        shell,
        plan_id=f"gocrpv1:plan:{canonical_json_sha256_v1(_plan_payload(shell))}",
    )
    validate_google_ocr_rescue_plan_v1(plan)
    return plan


def _no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _error(f"provider response contains duplicate JSON key {key!r}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise _error(f"provider response contains non-finite number {value}")


def _parse_response(raw: bytes) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > _MAX_RESPONSE_BYTES:
        raise _error("raw_response_bytes must be nonempty bounded exact bytes")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_no_duplicate_object,
            parse_float=Decimal,
            parse_int=int,
            parse_constant=_reject_constant,
        )
    except GoogleOcrRescueContractV1Error:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("provider response is not strict UTF-8 JSON") from exc
    if type(value) is not dict:
        raise _error("provider response root must be one JSON object")
    return value


def _decimal(value: Any, label: str) -> Decimal:
    if type(value) is int:
        result = Decimal(value)
    elif type(value) is Decimal:
        result = value
    else:
        raise _error(f"{label} must be one finite JSON number")
    if not result.is_finite():
        raise _error(f"{label} must be finite")
    return result


def _confidence(value: Any, label: str) -> float | None:
    if value is None:
        return None
    number = _decimal(value, label)
    if number < 0 or number > 1:
        raise _error(f"{label} must be in [0,1]")
    return float(number)


def _round_ratio(numerator: int, denominator: int) -> int:
    if numerator < 0 or denominator <= 0:
        raise _error("internal coordinate ratio is invalid")
    return (2 * numerator + denominator) // (2 * denominator)


def _vertex_list(value: Any, *, normalized: bool, label: str) -> list[tuple[int, int]]:
    vertices = _require_list(value, label)
    if len(vertices) != 4:
        raise _error(f"{label} must contain exactly four ordered vertices")
    output: list[tuple[int, int]] = []
    for index, raw_vertex in enumerate(vertices):
        vertex = _require_exact_dict(
            raw_vertex,
            allowed={"x", "y"},
            required=set(),
            label=f"{label}[{index}]",
        )
        if normalized:
            try:
                x_decimal = _decimal(vertex.get("x", 0), f"{label}[{index}].x")
                y_decimal = _decimal(vertex.get("y", 0), f"{label}[{index}].y")
                if x_decimal < 0 or x_decimal > 1 or y_decimal < 0 or y_decimal > 1:
                    raise _error(f"{label}[{index}] is outside normalized page bounds")
                x = int((x_decimal * _PPM).to_integral_value(rounding=ROUND_HALF_UP))
                y = int((y_decimal * _PPM).to_integral_value(rounding=ROUND_HALF_UP))
            except InvalidOperation as exc:
                raise _error(f"{label}[{index}] cannot be normalized") from exc
        else:
            x = _nonnegative_int(vertex.get("x", 0), f"{label}[{index}].x")
            y = _nonnegative_int(vertex.get("y", 0), f"{label}[{index}].y")
        output.append((x, y))
    return output


def _polygon_area2(vertices: list[tuple[int, int]]) -> int:
    return abs(
        sum(
            x1 * y2 - x2 * y1
            for (x1, y1), (x2, y2) in zip(vertices, vertices[1:] + vertices[:1], strict=True)
        )
    )


def _bounding_poly(value: Any, *, width: int, height: int, label: str) -> dict[str, Any]:
    poly = _require_exact_dict(
        value,
        allowed={"vertices", "normalizedVertices"},
        required=set(),
        label=label,
    )
    if not poly:
        raise _error(f"{label} must contain vertices or normalizedVertices")
    pixels = (
        _vertex_list(poly["vertices"], normalized=False, label=f"{label}.vertices")
        if "vertices" in poly
        else None
    )
    normalized = (
        _vertex_list(
            poly["normalizedVertices"],
            normalized=True,
            label=f"{label}.normalizedVertices",
        )
        if "normalizedVertices" in poly
        else None
    )
    if pixels is not None:
        if any(x > width or y > height for x, y in pixels):
            raise _error(f"{label}.vertices exceed the authenticated page dimensions")
    normalized_pixels = (
        [(_round_ratio(x * width, _PPM), _round_ratio(y * height, _PPM)) for x, y in normalized]
        if normalized is not None
        else None
    )
    if pixels is not None and normalized_pixels is not None:
        if any(
            abs(px - nx) > 1 or abs(py - ny) > 1
            for (px, py), (nx, ny) in zip(pixels, normalized_pixels, strict=True)
        ):
            raise _error(f"{label} pixel and normalized vertices disagree")
    canonical_pixels = pixels if pixels is not None else normalized_pixels
    assert canonical_pixels is not None
    canonical_ppm = [
        (_round_ratio(x * _PPM, width), _round_ratio(y * _PPM, height)) for x, y in canonical_pixels
    ]
    if _polygon_area2(canonical_pixels) <= 0 or _polygon_area2(canonical_ppm) <= 0:
        raise _error(f"{label} must have positive polygon area")
    return {
        "pixel_vertices": [{"x": x, "y": y} for x, y in canonical_pixels],
        "normalized_vertices_ppm": [{"x": x, "y": y} for x, y in canonical_ppm],
    }


def _detected_languages(value: Any, label: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    output = []
    for index, raw in enumerate(_require_list(value, label)):
        item = _require_exact_dict(
            raw,
            allowed={"languageCode", "confidence"},
            required={"languageCode"},
            label=f"{label}[{index}]",
        )
        output.append(
            {
                "language_code": _require_string(
                    item["languageCode"], f"{label}[{index}].languageCode"
                ),
                "confidence": _confidence(item.get("confidence"), f"{label}[{index}].confidence"),
            }
        )
    return output


def _detected_break(value: Any, label: str) -> dict[str, Any] | None:
    if value is None:
        return None
    item = _require_exact_dict(
        value,
        allowed={"type", "isPrefix"},
        required={"type"},
        label=label,
    )
    break_type = _require_string(item["type"], f"{label}.type")
    if break_type not in _BREAK_TYPES:
        raise _error(f"{label}.type is not a documented break type")
    is_prefix = item.get("isPrefix", False)
    if type(is_prefix) is not bool:
        raise _error(f"{label}.isPrefix must be exact boolean")
    return {"type": break_type, "is_prefix": is_prefix}


def _vision_property(value: Any, label: str) -> dict[str, Any] | None:
    if value is None:
        return None
    item = _require_exact_dict(
        value,
        allowed={"detectedLanguages", "detectedBreak"},
        required=set(),
        label=label,
    )
    return {
        "detected_languages": _detected_languages(item.get("detectedLanguages"), label),
        "detected_break": _detected_break(item.get("detectedBreak"), label),
    }


def _break_suffix(break_value: dict[str, Any] | None) -> str:
    if break_value is None or break_value["is_prefix"]:
        return ""
    if break_value["type"] in {"SPACE", "SURE_SPACE", "WIDE_SPACE"}:
        return " "
    if break_value["type"] in {"EOL_SURE_SPACE", "LINE_BREAK"}:
        return "\n"
    if break_value["type"] == "HYPHEN":
        return "-\n"
    return ""


def _vision_symbol(raw: Any, *, width: int, height: int, label: str) -> dict[str, Any]:
    item = _require_exact_dict(
        raw,
        allowed={"property", "boundingBox", "text", "confidence"},
        required={"boundingBox", "text"},
        label=label,
    )
    text = _require_string(item["text"], f"{label}.text", allow_empty=False)
    prop = _vision_property(item.get("property"), f"{label}.property")
    return {
        "text": text,
        "confidence": _confidence(item.get("confidence"), f"{label}.confidence"),
        "geometry": _bounding_poly(
            item["boundingBox"], width=width, height=height, label=f"{label}.boundingBox"
        ),
        "property": prop,
    }


def _vision_word(raw: Any, *, width: int, height: int, label: str) -> dict[str, Any]:
    item = _require_exact_dict(
        raw,
        allowed={"property", "boundingBox", "symbols", "confidence"},
        required={"boundingBox", "symbols"},
        label=label,
    )
    symbols = [
        _vision_symbol(symbol, width=width, height=height, label=f"{label}.symbols[{index}]")
        for index, symbol in enumerate(_require_list(item["symbols"], f"{label}.symbols"))
    ]
    text = "".join(
        symbol["text"]
        + _break_suffix(
            None if symbol["property"] is None else symbol["property"]["detected_break"]
        )
        for symbol in symbols
    )
    return {
        "text": text,
        "confidence": _confidence(item.get("confidence"), f"{label}.confidence"),
        "geometry": _bounding_poly(
            item["boundingBox"], width=width, height=height, label=f"{label}.boundingBox"
        ),
        "property": _vision_property(item.get("property"), f"{label}.property"),
        "symbols": symbols,
    }


def _vision_paragraph(raw: Any, *, width: int, height: int, label: str) -> dict[str, Any]:
    item = _require_exact_dict(
        raw,
        allowed={"property", "boundingBox", "words", "confidence"},
        required={"boundingBox", "words"},
        label=label,
    )
    words = [
        _vision_word(word, width=width, height=height, label=f"{label}.words[{index}]")
        for index, word in enumerate(_require_list(item["words"], f"{label}.words"))
    ]
    return {
        "text": "".join(word["text"] for word in words),
        "confidence": _confidence(item.get("confidence"), f"{label}.confidence"),
        "geometry": _bounding_poly(
            item["boundingBox"], width=width, height=height, label=f"{label}.boundingBox"
        ),
        "property": _vision_property(item.get("property"), f"{label}.property"),
        "words": words,
    }


def _vision_block(raw: Any, *, width: int, height: int, label: str) -> dict[str, Any]:
    item = _require_exact_dict(
        raw,
        allowed={"property", "boundingBox", "paragraphs", "blockType", "confidence"},
        required={"boundingBox", "paragraphs"},
        label=label,
    )
    paragraphs = [
        _vision_paragraph(
            paragraph,
            width=width,
            height=height,
            label=f"{label}.paragraphs[{index}]",
        )
        for index, paragraph in enumerate(_require_list(item["paragraphs"], f"{label}.paragraphs"))
    ]
    block_type = item.get("blockType", "UNKNOWN")
    _require_string(block_type, f"{label}.blockType")
    return {
        "text": "".join(paragraph["text"] for paragraph in paragraphs),
        "block_type": block_type,
        "confidence": _confidence(item.get("confidence"), f"{label}.confidence"),
        "geometry": _bounding_poly(
            item["boundingBox"], width=width, height=height, label=f"{label}.boundingBox"
        ),
        "property": _vision_property(item.get("property"), f"{label}.property"),
        "paragraphs": paragraphs,
    }


def _normalize_cloud_vision(root: dict[str, Any], plan: GoogleOcrRescuePlanV1) -> tuple[str, dict]:
    response = _require_exact_dict(
        root,
        allowed={"responses"},
        required={"responses"},
        label="Cloud Vision response",
    )
    responses = _require_list(response["responses"], "Cloud Vision responses")
    if len(responses) != 1:
        raise _error("Cloud Vision response must contain exactly one image result")
    image = _require_exact_dict(
        responses[0],
        allowed={"fullTextAnnotation"},
        required={"fullTextAnnotation"},
        label="Cloud Vision image result",
    )
    annotation = _require_exact_dict(
        image["fullTextAnnotation"],
        allowed={"pages", "text"},
        required={"pages", "text"},
        label="Cloud Vision fullTextAnnotation",
    )
    raw_text = _require_string(annotation["text"], "Cloud Vision text", allow_empty=True)
    raw_pages = _require_list(annotation["pages"], "Cloud Vision pages")
    if len(raw_pages) != 1:
        raise _error("single-page rescue requires exactly one Cloud Vision Page")
    raw_page = _require_exact_dict(
        raw_pages[0],
        allowed={"property", "width", "height", "blocks", "confidence"},
        required={"width", "height", "blocks"},
        label="Cloud Vision page",
    )
    width = _positive_int(raw_page["width"], "Cloud Vision page.width")
    height = _positive_int(raw_page["height"], "Cloud Vision page.height")
    if width != plan.page.pixel_width or height != plan.page.pixel_height:
        raise _error("Cloud Vision Page dimensions do not match authenticated image refs")
    blocks = [
        _vision_block(block, width=width, height=height, label=f"Cloud Vision blocks[{index}]")
        for index, block in enumerate(_require_list(raw_page["blocks"], "Cloud Vision blocks"))
    ]
    return raw_text, {
        "kind": "CLOUD_VISION_TEXT_ANNOTATION",
        "pages": [
            {
                "source_physical_page": plan.page.physical_page,
                "provider_page_index": 1,
                "pixel_width": width,
                "pixel_height": height,
                "confidence": _confidence(
                    raw_page.get("confidence"), "Cloud Vision page.confidence"
                ),
                "property": _vision_property(
                    raw_page.get("property"), "Cloud Vision page.property"
                ),
                "blocks": blocks,
            }
        ],
        "tables": [],
    }


def _text_index(value: Any, label: str, *, default: int | None = None) -> int:
    if value is None and default is not None:
        return default
    if type(value) is int:
        return _nonnegative_int(value, label)
    if type(value) is str and _POSITIVE_INDEX.fullmatch(value) is not None:
        return int(value)
    raise _error(f"{label} must be one nonnegative int64 JSON string/integer")


def _text_anchor(value: Any, *, document_text: str, label: str) -> dict[str, Any]:
    anchor = _require_exact_dict(
        value,
        allowed={"textSegments", "content"},
        required={"textSegments"},
        label=label,
    )
    segments = _require_list(anchor["textSegments"], f"{label}.textSegments")
    if not segments:
        raise _error(f"{label}.textSegments must not be empty")
    output_segments = []
    pieces = []
    previous_end = -1
    for index, raw in enumerate(segments):
        segment = _require_exact_dict(
            raw,
            allowed={"startIndex", "endIndex"},
            required={"endIndex"},
            label=f"{label}.textSegments[{index}]",
        )
        start = _text_index(
            segment.get("startIndex"),
            f"{label}.textSegments[{index}].startIndex",
            default=0,
        )
        end = _text_index(segment["endIndex"], f"{label}.textSegments[{index}].endIndex")
        if start < previous_end or end <= start or end > len(document_text):
            raise _error(f"{label}.textSegments[{index}] is overlapping or outside Document.text")
        output_segments.append({"start_index": start, "end_index": end})
        pieces.append(document_text[start:end])
        previous_end = end
    text = "".join(pieces)
    if "content" in anchor:
        content = _require_string(anchor["content"], f"{label}.content", allow_empty=True)
        if content != text:
            raise _error(f"{label}.content disagrees with its text segments")
    return {"text": text, "text_segments": output_segments}


def _doc_layout(
    value: Any,
    *,
    document_text: str,
    width: int,
    height: int,
    label: str,
) -> dict[str, Any]:
    layout = _require_exact_dict(
        value,
        allowed={"textAnchor", "confidence", "boundingPoly", "orientation"},
        required={"textAnchor", "boundingPoly"},
        label=label,
    )
    orientation = layout.get("orientation", "ORIENTATION_UNSPECIFIED")
    if orientation not in _ORIENTATIONS:
        raise _error(f"{label}.orientation drifted")
    anchor = _text_anchor(
        layout["textAnchor"], document_text=document_text, label=f"{label}.textAnchor"
    )
    return {
        "text": anchor["text"],
        "text_segments": anchor["text_segments"],
        "confidence": _confidence(layout.get("confidence"), f"{label}.confidence"),
        "orientation": orientation,
        "geometry": _bounding_poly(
            layout["boundingPoly"], width=width, height=height, label=f"{label}.boundingPoly"
        ),
    }


def _doc_element(
    value: Any,
    *,
    document_text: str,
    width: int,
    height: int,
    label: str,
    token: bool,
) -> dict[str, Any]:
    allowed = {"layout", "detectedLanguages"}
    if token:
        allowed.add("detectedBreak")
    item = _require_exact_dict(value, allowed=allowed, required={"layout"}, label=label)
    output = {
        "layout": _doc_layout(
            item["layout"],
            document_text=document_text,
            width=width,
            height=height,
            label=f"{label}.layout",
        ),
        "detected_languages": _detected_languages(
            item.get("detectedLanguages"), f"{label}.detectedLanguages"
        ),
    }
    if token:
        output["detected_break"] = _detected_break(
            item.get("detectedBreak"), f"{label}.detectedBreak"
        )
    return output


def _doc_table_rows(
    value: Any,
    *,
    document_text: str,
    width: int,
    height: int,
    label: str,
) -> list[dict[str, Any]]:
    rows = []
    for row_index, raw_row in enumerate(_require_list(value, label)):
        row = _require_exact_dict(
            raw_row,
            allowed={"cells"},
            required={"cells"},
            label=f"{label}[{row_index}]",
        )
        cells = []
        for cell_index, raw_cell in enumerate(
            _require_list(row["cells"], f"{label}[{row_index}].cells")
        ):
            cell_label = f"{label}[{row_index}].cells[{cell_index}]"
            cell = _require_exact_dict(
                raw_cell,
                allowed={"layout", "rowSpan", "colSpan", "detectedLanguages"},
                required={"layout"},
                label=cell_label,
            )
            cells.append(
                {
                    "layout": _doc_layout(
                        cell["layout"],
                        document_text=document_text,
                        width=width,
                        height=height,
                        label=f"{cell_label}.layout",
                    ),
                    "row_span": _positive_int(cell.get("rowSpan", 1), f"{cell_label}.rowSpan"),
                    "col_span": _positive_int(cell.get("colSpan", 1), f"{cell_label}.colSpan"),
                    "detected_languages": _detected_languages(
                        cell.get("detectedLanguages"), f"{cell_label}.detectedLanguages"
                    ),
                }
            )
        rows.append({"cells": cells})
    return rows


def _doc_table(
    value: Any,
    *,
    document_text: str,
    width: int,
    height: int,
    label: str,
) -> dict[str, Any]:
    table = _require_exact_dict(
        value,
        allowed={"layout", "headerRows", "bodyRows", "detectedLanguages"},
        required={"layout", "headerRows", "bodyRows"},
        label=label,
    )
    return {
        "layout": _doc_layout(
            table["layout"],
            document_text=document_text,
            width=width,
            height=height,
            label=f"{label}.layout",
        ),
        "header_rows": _doc_table_rows(
            table["headerRows"],
            document_text=document_text,
            width=width,
            height=height,
            label=f"{label}.headerRows",
        ),
        "body_rows": _doc_table_rows(
            table["bodyRows"],
            document_text=document_text,
            width=width,
            height=height,
            label=f"{label}.bodyRows",
        ),
        "detected_languages": _detected_languages(
            table.get("detectedLanguages"), f"{label}.detectedLanguages"
        ),
    }


def _document_ai_root(root: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    wrapper = _require_exact_dict(
        root,
        allowed={"document", "humanReviewStatus", "humanReviewOperation"},
        required={"document"},
        label="Document AI response",
    )
    metadata: dict[str, Any] = {}
    for field in ("humanReviewStatus", "humanReviewOperation"):
        if field in wrapper:
            metadata[field] = _require_string(wrapper[field], f"Document AI {field}")
    document = _require_exact_dict(
        wrapper["document"],
        allowed={"text", "mimeType", "pages", "documentLayout"},
        required={"text"},
        label="Document AI document",
    )
    return document, metadata


def _normalize_document_ai_ocr(
    root: dict[str, Any], plan: GoogleOcrRescuePlanV1
) -> tuple[str, dict]:
    document, metadata = _document_ai_root(root)
    if "documentLayout" in document:
        raise _error("Document AI OCR route cannot accept a Layout Parser document union")
    if "pages" not in document:
        raise _error("Document AI OCR document.pages is required")
    raw_text = _require_string(document["text"], "Document AI text", allow_empty=True)
    if "mimeType" in document and document["mimeType"] != plan.page.mime_type:
        raise _error("Document AI mimeType does not match the authenticated input")
    raw_pages = _require_list(document["pages"], "Document AI pages")
    if len(raw_pages) != 1:
        raise _error("single-page rescue requires exactly one Document AI Page")
    page = _require_exact_dict(
        raw_pages[0],
        allowed={
            "pageNumber",
            "dimension",
            "layout",
            "detectedLanguages",
            "blocks",
            "paragraphs",
            "lines",
            "tokens",
            "symbols",
            "tables",
        },
        required={"pageNumber", "dimension"},
        label="Document AI page",
    )
    if _positive_int(page["pageNumber"], "Document AI page.pageNumber") != 1:
        raise _error("single-page Document AI provider pageNumber must be 1")
    dimension = _require_exact_dict(
        page["dimension"],
        allowed={"width", "height", "unit"},
        required={"width", "height", "unit"},
        label="Document AI page.dimension",
    )
    if dimension["unit"] not in {"pixel", "pixels", "px"}:
        raise _error("Document AI page.dimension must use pixel units")
    width_number = _decimal(dimension["width"], "Document AI page.dimension.width")
    height_number = _decimal(dimension["height"], "Document AI page.dimension.height")
    if width_number != plan.page.pixel_width or height_number != plan.page.pixel_height:
        raise _error("Document AI Page dimensions do not match authenticated image refs")
    width = plan.page.pixel_width
    height = plan.page.pixel_height

    def elements(field: str, *, token: bool = False) -> list[dict[str, Any]]:
        return [
            _doc_element(
                item,
                document_text=raw_text,
                width=width,
                height=height,
                label=f"Document AI page.{field}[{index}]",
                token=token,
            )
            for index, item in enumerate(_require_list(page.get(field, []), f"Document AI {field}"))
        ]

    tables = [
        _doc_table(
            item,
            document_text=raw_text,
            width=width,
            height=height,
            label=f"Document AI page.tables[{index}]",
        )
        for index, item in enumerate(_require_list(page.get("tables", []), "Document AI tables"))
    ]
    normalized_page = {
        "source_physical_page": plan.page.physical_page,
        "provider_page_index": 1,
        "pixel_width": width,
        "pixel_height": height,
        "layout": (
            _doc_layout(
                page["layout"],
                document_text=raw_text,
                width=width,
                height=height,
                label="Document AI page.layout",
            )
            if "layout" in page
            else None
        ),
        "detected_languages": _detected_languages(
            page.get("detectedLanguages"), "Document AI page.detectedLanguages"
        ),
        "blocks": elements("blocks"),
        "paragraphs": elements("paragraphs"),
        "lines": elements("lines"),
        "tokens": elements("tokens", token=True),
        "symbols": elements("symbols"),
        "tables": tables,
    }
    return raw_text, {
        "kind": "DOCUMENT_AI_PAGE_LAYOUT",
        "response_metadata": metadata,
        "pages": [normalized_page],
        "tables": tables,
    }


def _annotations(value: Any, label: str) -> dict[str, str] | None:
    if value is None:
        return None
    item = _require_exact_dict(
        value,
        allowed={"description"},
        required={"description"},
        label=label,
    )
    return {
        "description": _require_string(
            item["description"], f"{label}.description", allow_empty=True
        )
    }


def _layout_page_span(value: Any, label: str) -> dict[str, int]:
    span = _require_exact_dict(
        value,
        allowed={"pageStart", "pageEnd"},
        required={"pageStart", "pageEnd"},
        label=label,
    )
    start = _positive_int(span["pageStart"], f"{label}.pageStart")
    end = _positive_int(span["pageEnd"], f"{label}.pageEnd")
    if start != 1 or end != 1:
        raise _error("single-page Layout Parser block pageSpan must be exactly [1,1]")
    return {"provider_page_start": start, "provider_page_end": end}


def _layout_parser_rows(
    value: Any,
    *,
    width: int,
    height: int,
    label: str,
    depth: int,
    seen_ids: set[str],
) -> list[dict[str, Any]]:
    rows = []
    for row_index, raw_row in enumerate(_require_list(value, label)):
        row = _require_exact_dict(
            raw_row,
            allowed={"cells"},
            required={"cells"},
            label=f"{label}[{row_index}]",
        )
        cells = []
        for cell_index, raw_cell in enumerate(
            _require_list(row["cells"], f"{label}[{row_index}].cells")
        ):
            cell_label = f"{label}[{row_index}].cells[{cell_index}]"
            cell = _require_exact_dict(
                raw_cell,
                allowed={"blocks", "rowSpan", "colSpan"},
                required={"blocks"},
                label=cell_label,
            )
            cells.append(
                {
                    "blocks": [
                        _layout_parser_block(
                            block,
                            width=width,
                            height=height,
                            label=f"{cell_label}.blocks[{index}]",
                            depth=depth + 1,
                            seen_ids=seen_ids,
                        )
                        for index, block in enumerate(
                            _require_list(cell["blocks"], f"{cell_label}.blocks")
                        )
                    ],
                    "row_span": _positive_int(cell.get("rowSpan", 1), f"{cell_label}.rowSpan"),
                    "col_span": _positive_int(cell.get("colSpan", 1), f"{cell_label}.colSpan"),
                }
            )
        rows.append({"cells": cells})
    return rows


def _layout_parser_block(
    value: Any,
    *,
    width: int,
    height: int,
    label: str,
    depth: int,
    seen_ids: set[str],
) -> dict[str, Any]:
    if depth > 32:
        raise _error("Layout Parser block nesting exceeds the bounded depth")
    item = _require_exact_dict(
        value,
        allowed={"blockId", "pageSpan", "boundingBox", "textBlock", "tableBlock", "listBlock"},
        required={"blockId", "pageSpan", "boundingBox"},
        label=label,
    )
    union = [key for key in ("textBlock", "tableBlock", "listBlock") if key in item]
    if len(union) != 1:
        raise _error(f"{label} must contain exactly one supported block union member")
    block_id = _require_string(item["blockId"], f"{label}.blockId")
    if block_id in seen_ids:
        raise _error(f"{label}.blockId is duplicated")
    seen_ids.add(block_id)
    base: dict[str, Any] = {
        "block_id": block_id,
        "page_span": _layout_page_span(item["pageSpan"], f"{label}.pageSpan"),
        "geometry": _bounding_poly(
            item["boundingBox"], width=width, height=height, label=f"{label}.boundingBox"
        ),
    }
    kind = union[0]
    if kind == "textBlock":
        text_block = _require_exact_dict(
            item[kind],
            allowed={"text", "type", "blocks", "annotations"},
            required={"text", "type"},
            label=f"{label}.textBlock",
        )
        block_type = _require_string(text_block["type"], f"{label}.textBlock.type")
        if block_type not in _TEXT_BLOCK_TYPES:
            raise _error(f"{label}.textBlock.type drifted")
        base.update(
            {
                "kind": "TEXT",
                "text": _require_string(
                    text_block["text"], f"{label}.textBlock.text", allow_empty=True
                ),
                "text_type": block_type,
                "annotations": _annotations(
                    text_block.get("annotations"), f"{label}.textBlock.annotations"
                ),
                "blocks": [
                    _layout_parser_block(
                        child,
                        width=width,
                        height=height,
                        label=f"{label}.textBlock.blocks[{index}]",
                        depth=depth + 1,
                        seen_ids=seen_ids,
                    )
                    for index, child in enumerate(
                        _require_list(text_block.get("blocks", []), f"{label}.textBlock.blocks")
                    )
                ],
            }
        )
    elif kind == "tableBlock":
        table = _require_exact_dict(
            item[kind],
            allowed={"headerRows", "bodyRows", "caption", "annotations"},
            required={"headerRows", "bodyRows"},
            label=f"{label}.tableBlock",
        )
        base.update(
            {
                "kind": "TABLE",
                "caption": _require_string(
                    table.get("caption", ""), f"{label}.tableBlock.caption", allow_empty=True
                ),
                "annotations": _annotations(
                    table.get("annotations"), f"{label}.tableBlock.annotations"
                ),
                "header_rows": _layout_parser_rows(
                    table["headerRows"],
                    width=width,
                    height=height,
                    label=f"{label}.tableBlock.headerRows",
                    depth=depth,
                    seen_ids=seen_ids,
                ),
                "body_rows": _layout_parser_rows(
                    table["bodyRows"],
                    width=width,
                    height=height,
                    label=f"{label}.tableBlock.bodyRows",
                    depth=depth,
                    seen_ids=seen_ids,
                ),
            }
        )
    else:
        list_block = _require_exact_dict(
            item[kind],
            allowed={"listEntries", "type"},
            required={"listEntries", "type"},
            label=f"{label}.listBlock",
        )
        list_type = _require_string(list_block["type"], f"{label}.listBlock.type")
        if list_type not in {"ordered", "unordered"}:
            raise _error(f"{label}.listBlock.type drifted")
        entries = []
        for entry_index, raw_entry in enumerate(
            _require_list(list_block["listEntries"], f"{label}.listBlock.listEntries")
        ):
            entry_label = f"{label}.listBlock.listEntries[{entry_index}]"
            entry = _require_exact_dict(
                raw_entry,
                allowed={"blocks"},
                required={"blocks"},
                label=entry_label,
            )
            entries.append(
                {
                    "blocks": [
                        _layout_parser_block(
                            child,
                            width=width,
                            height=height,
                            label=f"{entry_label}.blocks[{index}]",
                            depth=depth + 1,
                            seen_ids=seen_ids,
                        )
                        for index, child in enumerate(
                            _require_list(entry["blocks"], f"{entry_label}.blocks")
                        )
                    ]
                }
            )
        base.update({"kind": "LIST", "list_type": list_type, "list_entries": entries})
    return base


def _normalize_document_ai_layout_parser(
    root: dict[str, Any], plan: GoogleOcrRescuePlanV1
) -> tuple[str, dict]:
    document, metadata = _document_ai_root(root)
    if "pages" in document:
        raise _error("Layout Parser route cannot ambiguously mix pages and documentLayout")
    if "documentLayout" not in document:
        raise _error("Layout Parser response requires document.documentLayout")
    raw_text = _require_string(document["text"], "Document AI Layout Parser text", allow_empty=True)
    if "mimeType" in document and document["mimeType"] != plan.page.mime_type:
        raise _error("Layout Parser mimeType does not match the authenticated input")
    layout = _require_exact_dict(
        document["documentLayout"],
        allowed={"blocks"},
        required={"blocks"},
        label="Document AI documentLayout",
    )
    seen_ids: set[str] = set()
    blocks = [
        _layout_parser_block(
            block,
            width=plan.page.pixel_width,
            height=plan.page.pixel_height,
            label=f"Document AI documentLayout.blocks[{index}]",
            depth=0,
            seen_ids=seen_ids,
        )
        for index, block in enumerate(
            _require_list(layout["blocks"], "Document AI documentLayout.blocks")
        )
    ]
    tables = [block for block in blocks if block["kind"] == "TABLE"]
    return raw_text, {
        "kind": "DOCUMENT_AI_DOCUMENT_LAYOUT",
        "response_metadata": metadata,
        "source_physical_page": plan.page.physical_page,
        "pixel_width": plan.page.pixel_width,
        "pixel_height": plan.page.pixel_height,
        "blocks": blocks,
        "tables": tables,
    }


def normalize_google_ocr_response_v1(
    *, plan: GoogleOcrRescuePlanV1, raw_response_bytes: bytes
) -> dict[str, Any]:
    """Normalize captured REST JSON without executing or trusting the provider.

    ``raw_response_bytes`` must be the exact captured response bytes.  Their SHA
    is computed here; callers cannot inject a self-reported response hash.
    """

    validate_google_ocr_rescue_plan_v1(plan)
    root = _parse_response(raw_response_bytes)
    if plan.profile.route is GoogleOcrRouteV1.CLOUD_VISION_DOCUMENT_TEXT_DETECTION:
        raw_text, structure = _normalize_cloud_vision(root, plan)
    elif plan.profile.route is GoogleOcrRouteV1.DOCUMENT_AI_OCR_PROCESSOR:
        raw_text, structure = _normalize_document_ai_ocr(root, plan)
    elif plan.profile.route is GoogleOcrRouteV1.DOCUMENT_AI_LAYOUT_PARSER:
        raw_text, structure = _normalize_document_ai_layout_parser(root, plan)
    else:  # pragma: no cover - enum validation above makes this defensive only.
        raise _error("unsupported OCR route")
    payload: dict[str, Any] = {
        "format_version": FORMAT_VERSION,
        "plan_id": plan.plan_id,
        "page": {
            "document_id": plan.page.document_id,
            "page_id": plan.page.page_id,
            "physical_page": plan.page.physical_page,
            "page_image_sha256": plan.page.page_image_ref.sha256,
            "pixel_width": plan.page.pixel_width,
            "pixel_height": plan.page.pixel_height,
        },
        "provider": _profile_projection(plan.profile),
        "raw_response": {
            "sha256": sha256(raw_response_bytes).hexdigest(),
            "size_bytes": len(raw_response_bytes),
        },
        "raw_text": raw_text,
        "structure": structure,
        "authority": dict(OUTPUT_AUTHORITY),
    }
    payload["challenger_id"] = f"gocrpv1:challenger:{canonical_json_sha256_v1(payload)}"
    return payload
