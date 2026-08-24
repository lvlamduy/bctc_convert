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

import base64
import binascii
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
    "QUARANTINED_GENERATED_AUTHORITY",
    "AuthenticatedUnresolvedPageV1",
    "ContentRefKindV1",
    "ExactContentRefV1",
    "GoogleOcrProfileV1",
    "GoogleOcrProfileDerivationV1",
    "GoogleOcrReleaseChannelV1",
    "GoogleOcrResidencyAssuranceV1",
    "GoogleOcrExecutionReceiptV1",
    "GoogleOcrExecutionStatusV1",
    "GoogleOcrInputBindingKindV1",
    "GoogleOcrInlineInputV1",
    "GoogleOcrImmutableGcsInputV1",
    "GoogleOcrRescueContractV1Error",
    "GoogleOcrRescuePlanV1",
    "GoogleOcrRouteV1",
    "PageAuthenticationStateV1",
    "PageResolutionStateV1",
    "TransportAuthenticationStateV1",
    "build_google_ocr_execution_receipt_v1",
    "build_google_ocr_rescue_plan_v1",
    "derive_google_ocr_profile_v1",
    "normalize_google_ocr_response_v1",
    "validate_google_ocr_execution_receipt_v1",
    "validate_google_ocr_rescue_plan_v1",
]


FORMAT_VERSION = "GOOGLE_OCR_RESCUE_CHALLENGER_V1"
PLAN_FORMAT_VERSION = "GOOGLE_OCR_RESCUE_REQUEST_PLAN_V1"
EXECUTION_RECEIPT_FORMAT_VERSION = "GOOGLE_OCR_EXECUTION_RECEIPT_V1"
PLAN_CLAIM_BOUNDARY = (
    "OFFLINE_PLAN_ONLY_CALLER_MUST_SUPPLY_CURRENT_AUTHENTICATED_REFS_"
    "NO_UPLOAD_AUTHORIZATION_NO_PROVIDER_EXECUTION"
)
EXECUTION_RECEIPT_CLAIM_BOUNDARY = (
    "CALLER_AUTHENTICATED_TRANSPORT_CAPTURE_REQUIRED_SELF_HASH_IS_CONTENT_"
    "BOOKKEEPING_ONLY_NOT_AUTHORITY_NO_UPLOAD_AUTHORIZATION"
)
_TASK = (
    "Extract source-visible Vietnamese text, hierarchy, geometry, and table structure "
    "from this one unresolved page. Do not infer, map, correct, or invent values."
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_POSITIVE_INDEX = re.compile(r"^(0|[1-9][0-9]*)$")
_DOC_PROCESSOR_RESOURCE = re.compile(
    r"^projects/([^/]+)/locations/([a-z0-9-]+)/processors/([^/]+)/"
    r"processorVersions/([^/]+)$"
)
_VISION_REGIONAL_RESOURCE = re.compile(r"^projects/([^/]+)/locations/(eu|us)/images:annotate$")
_GCS_BUCKET = re.compile(r"^[a-z0-9][a-z0-9._-]{1,221}[a-z0-9]$")
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
_LAYOUT_STABLE_VERSION = "pretrained-layout-parser-v1.0-2024-06-03"
_LAYOUT_PREVIEW_VERSIONS = {
    "pretrained-layout-parser-v1.5-2025-08-25",
    "pretrained-layout-parser-v1.5-pro-2025-08-25",
    "pretrained-layout-parser-v1.6-pro-2025-12-01",
    "pretrained-layout-parser-v1.6-2026-01-13",
}
_LAYOUT_NON_RESIDENT_VERSIONS = {
    "pretrained-layout-parser-v1.6-pro-2025-12-01",
    "pretrained-layout-parser-v1.6-2026-01-13",
}
_OCR_STABLE_VERSIONS = {
    "pretrained-ocr-v1.2-2022-11-10",
    "pretrained-ocr-v2.0-2023-06-02",
    "pretrained-ocr-v2.1-2024-08-07",
}
_OCR_PREVIEW_VERSIONS = {"pretrained-ocr-v2.1.1-2025-01-31"}
_VISION_KNOWN_VERSIONS = {"builtin-document-text-detection", "vision-rest-v1"}
_DOCUMENT_AI_LOCATIONS = {
    "global",
    "us",
    "eu",
    "asia-south1",
    "asia-southeast1",
    "northamerica-northeast1",
    "australia-southeast1",
    "europe-west2",
    "europe-west3",
}
_OCR_STABLE_LOCATIONS = _DOCUMENT_AI_LOCATIONS - {"global"}
_OCR_V211_PREVIEW_LOCATIONS = {
    "asia-south1",
    "northamerica-northeast1",
    "australia-southeast1",
    "europe-west2",
    "europe-west3",
}
_LAYOUT_VERSION_LOCATIONS = {"eu", "us"}
_HUMAN_REVIEW_STATES = {
    "STATE_UNSPECIFIED",
    "SKIPPED",
    "VALIDATION_PASSED",
    "IN_PROGRESS",
    "ERROR",
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
QUARANTINED_GENERATED_AUTHORITY: Mapping[str, bool] = MappingProxyType(
    {
        "generated_or_image_annotation": True,
        "source_visible_text_authority": False,
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
    UNKNOWN = "UNKNOWN"


class GoogleOcrResidencyAssuranceV1(StrEnum):
    COMPLIANT = "COMPLIANT"
    NONCOMPLIANT = "NONCOMPLIANT"
    UNVERIFIED = "UNVERIFIED"


class GoogleOcrExecutionStatusV1(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class GoogleOcrInputBindingKindV1(StrEnum):
    INLINE = "INLINE"
    IMMUTABLE_GCS = "IMMUTABLE_GCS"


class ContentRefKindV1(StrEnum):
    SOURCE_PAGE = "SOURCE_PAGE"
    PAGE_IMAGE = "PAGE_IMAGE"
    AUTHENTICATION_RECEIPT = "AUTHENTICATION_RECEIPT"
    UNRESOLVED_GRAPH = "UNRESOLVED_GRAPH"
    PROVIDER = "PROVIDER"
    API_VERSION = "API_VERSION"
    ENDPOINT = "ENDPOINT"
    PROCESSOR = "PROCESSOR"
    PROCESSOR_VERSION = "PROCESSOR_VERSION"
    REGION = "REGION"
    PROMPT = "PROMPT"
    CONFIG = "CONFIG"
    TRANSPORT_CAPTURE = "TRANSPORT_CAPTURE"


class PageAuthenticationStateV1(StrEnum):
    CALLER_AUTHENTICATED_CURRENT_REFS = "CALLER_AUTHENTICATED_CURRENT_REFS"


class PageResolutionStateV1(StrEnum):
    UNRESOLVED_AFTER_DETERMINISTIC_GRAPH = "UNRESOLVED_AFTER_DETERMINISTIC_GRAPH"


class TransportAuthenticationStateV1(StrEnum):
    CALLER_AUTHENTICATED_TRANSPORT_CAPTURE = "CALLER_AUTHENTICATED_TRANSPORT_CAPTURE"


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
    api_version: str
    endpoint_hostname: str
    processor_name: str
    processor_resource: str
    processor_version: str
    provider_ref: ExactContentRefV1
    api_version_ref: ExactContentRefV1
    endpoint_ref: ExactContentRefV1
    processor_ref: ExactContentRefV1
    processor_version_ref: ExactContentRefV1
    region_ref: ExactContentRefV1
    prompt_ref: ExactContentRefV1
    config_ref: ExactContentRefV1


@dataclass(frozen=True, slots=True)
class GoogleOcrProfileDerivationV1:
    location: str
    release_channel: GoogleOcrReleaseChannelV1
    residency_assurance: GoogleOcrResidencyAssuranceV1
    source_visible_geometry_supported: bool
    http_method: str
    request_resource: str


@dataclass(frozen=True, slots=True)
class GoogleOcrInlineInputV1:
    kind: GoogleOcrInputBindingKindV1
    sha256: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class GoogleOcrImmutableGcsInputV1:
    kind: GoogleOcrInputBindingKindV1
    bucket: str
    object_name: str
    generation: str
    caller_verified_content_sha256: str
    caller_verified_content_size_bytes: int


GoogleOcrInputBindingV1 = GoogleOcrInlineInputV1 | GoogleOcrImmutableGcsInputV1


@dataclass(frozen=True, slots=True)
class GoogleOcrRescuePlanV1:
    format_version: str
    claim_boundary: str
    task: str
    page: AuthenticatedUnresolvedPageV1
    profile: GoogleOcrProfileV1
    derived_location: str
    release_channel: GoogleOcrReleaseChannelV1
    residency_assurance: GoogleOcrResidencyAssuranceV1
    external_upload_requires_explicit_authorization: bool
    external_upload_authorized_by_plan: bool
    network_call_performed: bool
    credentials_accessed: bool
    image_bytes_embedded: bool
    execution_state: str
    data_residency_warning: str
    plan_id: str


@dataclass(frozen=True, slots=True)
class GoogleOcrExecutionReceiptV1:
    format_version: str
    claim_boundary: str
    plan_id: str
    endpoint_hostname: str
    http_method: str
    api_version: str
    processor_resource: str
    request_body_sha256: str
    request_body_size_bytes: int
    input_binding: GoogleOcrInputBindingV1
    request_id: str | None
    operation_id: str | None
    status: GoogleOcrExecutionStatusV1
    http_status_code: int
    response_sha256: str
    response_size_bytes: int
    transport_capture_ref: ExactContentRefV1
    transport_authentication_state: TransportAuthenticationStateV1
    self_hash_is_authority: bool
    external_upload_authorized_by_receipt: bool
    receipt_id: str


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


def _document_endpoint_location(hostname: str) -> str:
    if hostname == "documentai.googleapis.com":
        return "global"
    suffix = "-documentai.googleapis.com"
    if hostname.endswith(suffix):
        location = hostname[: -len(suffix)]
        if location in _DOCUMENT_AI_LOCATIONS:
            return location
    raise _error("Document AI endpoint hostname is not a documented exact hostname")


def _vision_endpoint_location(hostname: str) -> str:
    if hostname == "vision.googleapis.com":
        return "global"
    if hostname in {"eu-vision.googleapis.com", "us-vision.googleapis.com"}:
        return hostname.split("-", 1)[0]
    raise _error("Cloud Vision endpoint hostname is not a documented exact hostname")


def derive_google_ocr_profile_v1(profile: GoogleOcrProfileV1) -> GoogleOcrProfileDerivationV1:
    """Derive location, release, residency, method, and resource from exact pins.

    No caller-provided boolean can upgrade residency.  Unknown processor
    versions deliberately remain ``UNVERIFIED``.
    """

    if type(profile) is not GoogleOcrProfileV1:
        raise _error("profile must be GoogleOcrProfileV1")
    if type(profile.route) is not GoogleOcrRouteV1:
        raise _error("profile.route drifted")
    if profile.provider_name != "GOOGLE_CLOUD_REST":
        raise _error("profile.provider_name must be exact GOOGLE_CLOUD_REST")
    if profile.api_version != "v1":
        raise _error("profile.api_version must pin the supported REST v1 contract")
    _require_string(profile.endpoint_hostname, "profile.endpoint_hostname")
    _require_string(profile.processor_name, "profile.processor_name")
    _require_string(profile.processor_resource, "profile.processor_resource")
    _require_string(profile.processor_version, "profile.processor_version")
    for ref, kind, label in (
        (profile.provider_ref, ContentRefKindV1.PROVIDER, "provider_ref"),
        (profile.api_version_ref, ContentRefKindV1.API_VERSION, "api_version_ref"),
        (profile.endpoint_ref, ContentRefKindV1.ENDPOINT, "endpoint_ref"),
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
    if profile.provider_ref.logical_id != "provider/google-cloud-rest":
        raise _error("provider_ref logical ID must bind exact GOOGLE_CLOUD_REST")
    if profile.api_version_ref.logical_id != f"google-api-version/{profile.api_version}":
        raise _error("api_version_ref logical ID does not bind profile.api_version")
    if profile.endpoint_ref.logical_id != f"google-endpoint/{profile.endpoint_hostname}":
        raise _error("endpoint_ref logical ID does not bind profile.endpoint_hostname")
    if (
        profile.processor_ref.logical_id
        != f"google-processor-resource/{profile.processor_resource}"
    ):
        raise _error("processor_ref logical ID does not bind profile.processor_resource")
    if (
        profile.processor_version_ref.logical_id
        != f"google-processor-version/{profile.processor_version}"
    ):
        raise _error("processor_version_ref logical ID does not bind profile.processor_version")

    if profile.route is GoogleOcrRouteV1.CLOUD_VISION_DOCUMENT_TEXT_DETECTION:
        if profile.processor_name != "DOCUMENT_TEXT_DETECTION":
            raise _error("Cloud Vision route must pin DOCUMENT_TEXT_DETECTION")
        endpoint_location = _vision_endpoint_location(profile.endpoint_hostname)
        if endpoint_location == "global":
            if profile.processor_resource != "images:annotate":
                raise _error("global Cloud Vision route must pin images:annotate")
            resource_location = "global"
        else:
            match = _VISION_REGIONAL_RESOURCE.fullmatch(profile.processor_resource)
            if match is None:
                raise _error(
                    "regional Cloud Vision route must pin its exact project/location resource"
                )
            resource_location = match.group(2)
        release = (
            GoogleOcrReleaseChannelV1.STABLE
            if profile.processor_version in _VISION_KNOWN_VERSIONS
            else GoogleOcrReleaseChannelV1.UNKNOWN
        )
        geometry_supported = profile.processor_version in _VISION_KNOWN_VERSIONS
    else:
        endpoint_location = _document_endpoint_location(profile.endpoint_hostname)
        match = _DOC_PROCESSOR_RESOURCE.fullmatch(profile.processor_resource)
        if match is None:
            raise _error("Document AI route must pin an exact ProcessorVersion resource")
        resource_location = match.group(2)
        resource_version = match.group(4)
        if resource_version != profile.processor_version:
            raise _error("processor resource and exact processor_version disagree")
        expected_name = (
            "OCR_PROCESSOR"
            if profile.route is GoogleOcrRouteV1.DOCUMENT_AI_OCR_PROCESSOR
            else "LAYOUT_PARSER_PROCESSOR"
        )
        if profile.processor_name != expected_name:
            raise _error(f"{profile.route.value} must pin {expected_name}")
        if profile.route is GoogleOcrRouteV1.DOCUMENT_AI_LAYOUT_PARSER:
            if profile.processor_version == _LAYOUT_STABLE_VERSION:
                release = GoogleOcrReleaseChannelV1.STABLE
            elif profile.processor_version in _LAYOUT_PREVIEW_VERSIONS:
                release = GoogleOcrReleaseChannelV1.PREVIEW
            else:
                release = GoogleOcrReleaseChannelV1.UNKNOWN
            geometry_supported = profile.processor_version == _LAYOUT_STABLE_VERSION
            if (
                profile.processor_version in {*_LAYOUT_PREVIEW_VERSIONS, _LAYOUT_STABLE_VERSION}
                and resource_location not in _LAYOUT_VERSION_LOCATIONS
            ):
                raise _error("Layout Parser version is not documented for the resource location")
        else:
            if profile.processor_version in _OCR_STABLE_VERSIONS:
                release = GoogleOcrReleaseChannelV1.STABLE
            elif profile.processor_version in _OCR_PREVIEW_VERSIONS:
                release = GoogleOcrReleaseChannelV1.PREVIEW
            else:
                release = GoogleOcrReleaseChannelV1.UNKNOWN
            geometry_supported = True
            if (
                profile.processor_version in _OCR_STABLE_VERSIONS
                and resource_location not in _OCR_STABLE_LOCATIONS
            ):
                raise _error("stable OCR version is not documented for the resource location")
            if (
                profile.processor_version in _OCR_PREVIEW_VERSIONS
                and resource_location not in _OCR_V211_PREVIEW_LOCATIONS
            ):
                raise _error("preview OCR version is not documented for the resource location")

    if endpoint_location != resource_location:
        raise _error(
            "endpoint hostname location and processor resource location disagree "
            f"({endpoint_location!r} != {resource_location!r})"
        )
    if profile.region_ref.logical_id != f"google-location/{resource_location}":
        raise _error("region_ref logical ID does not bind the derived resource location")

    known_version = release is not GoogleOcrReleaseChannelV1.UNKNOWN
    if (
        profile.route is GoogleOcrRouteV1.DOCUMENT_AI_LAYOUT_PARSER
        and profile.processor_version in _LAYOUT_NON_RESIDENT_VERSIONS
    ):
        residency = GoogleOcrResidencyAssuranceV1.NONCOMPLIANT
    elif not known_version or resource_location == "global":
        residency = GoogleOcrResidencyAssuranceV1.UNVERIFIED
    else:
        residency = GoogleOcrResidencyAssuranceV1.COMPLIANT
    return GoogleOcrProfileDerivationV1(
        location=resource_location,
        release_channel=release,
        residency_assurance=residency,
        source_visible_geometry_supported=geometry_supported,
        http_method="POST",
        request_resource=profile.processor_resource,
    )


def _validate_profile(profile: GoogleOcrProfileV1) -> GoogleOcrProfileDerivationV1:
    return derive_google_ocr_profile_v1(profile)


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
        "api_version": profile.api_version,
        "endpoint_hostname": profile.endpoint_hostname,
        "processor_name": profile.processor_name,
        "processor_resource": profile.processor_resource,
        "processor_version": profile.processor_version,
        "provider_ref": _ref_projection(profile.provider_ref),
        "api_version_ref": _ref_projection(profile.api_version_ref),
        "endpoint_ref": _ref_projection(profile.endpoint_ref),
        "processor_ref": _ref_projection(profile.processor_ref),
        "processor_version_ref": _ref_projection(profile.processor_version_ref),
        "region_ref": _ref_projection(profile.region_ref),
        "prompt_ref": _ref_projection(profile.prompt_ref),
        "config_ref": _ref_projection(profile.config_ref),
    }


def _residency_warning(derivation: GoogleOcrProfileDerivationV1) -> str:
    if derivation.residency_assurance is GoogleOcrResidencyAssuranceV1.NONCOMPLIANT:
        return "DATA_RESIDENCY_NONCOMPLIANT_EXPLICIT_UPLOAD_AUTHORIZATION_REQUIRED"
    if derivation.residency_assurance is GoogleOcrResidencyAssuranceV1.UNVERIFIED:
        return "DATA_RESIDENCY_UNVERIFIED_EXPLICIT_UPLOAD_AUTHORIZATION_REQUIRED"
    return "REGIONAL_DATA_RESIDENCY_PROFILE_STILL_REQUIRES_EXPLICIT_UPLOAD_AUTHORIZATION"


def _validate_plan_route_compatibility(
    page: AuthenticatedUnresolvedPageV1,
    profile: GoogleOcrProfileV1,
    derivation: GoogleOcrProfileDerivationV1,
) -> None:
    if profile.route is GoogleOcrRouteV1.CLOUD_VISION_DOCUMENT_TEXT_DETECTION:
        if page.mime_type not in {"image/png", "image/jpeg"}:
            raise _error(
                "Cloud Vision images:annotate rescue supports only one-page image/png or image/jpeg; "
                "PDF/TIFF require a separately contracted files route"
            )
        if not derivation.source_visible_geometry_supported:
            raise _error("unknown Cloud Vision processor version has no frozen geometry contract")
    if (
        profile.route is GoogleOcrRouteV1.DOCUMENT_AI_LAYOUT_PARSER
        and not derivation.source_visible_geometry_supported
    ):
        raise _error(
            "source-visible geometry rescue supports only stable Layout Parser "
            f"{_LAYOUT_STABLE_VERSION}; preview/unknown versions fail at plan time"
        )


def _plan_payload(plan: GoogleOcrRescuePlanV1) -> dict[str, Any]:
    return {
        "format_version": plan.format_version,
        "claim_boundary": plan.claim_boundary,
        "task": plan.task,
        "page": _page_projection(plan.page),
        "profile": _profile_projection(plan.profile),
        "derived_profile": {
            "location": plan.derived_location,
            "release_channel": plan.release_channel.value,
            "residency_assurance": plan.residency_assurance.value,
        },
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
    derivation = _validate_profile(plan.profile)
    _validate_plan_route_compatibility(plan.page, plan.profile, derivation)
    if (
        plan.derived_location != derivation.location
        or plan.release_channel is not derivation.release_channel
        or plan.residency_assurance is not derivation.residency_assurance
        or plan.external_upload_requires_explicit_authorization is not True
        or plan.external_upload_authorized_by_plan is not False
        or plan.network_call_performed is not False
        or plan.credentials_accessed is not False
        or plan.image_bytes_embedded is not False
        or plan.execution_state != "PLANNED_NOT_EXECUTED"
        or plan.data_residency_warning != _residency_warning(derivation)
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
    derivation = _validate_profile(profile)
    _validate_plan_route_compatibility(page, profile, derivation)
    shell = GoogleOcrRescuePlanV1(
        format_version=PLAN_FORMAT_VERSION,
        claim_boundary=PLAN_CLAIM_BOUNDARY,
        task=_TASK,
        page=page,
        profile=profile,
        derived_location=derivation.location,
        release_channel=derivation.release_channel,
        residency_assurance=derivation.residency_assurance,
        external_upload_requires_explicit_authorization=True,
        external_upload_authorized_by_plan=False,
        network_call_performed=False,
        credentials_accessed=False,
        image_bytes_embedded=False,
        execution_state="PLANNED_NOT_EXECUTED",
        data_residency_warning=_residency_warning(derivation),
        plan_id="",
    )
    plan = replace(
        shell,
        plan_id=f"gocrpv1:plan:{canonical_json_sha256_v1(_plan_payload(shell))}",
    )
    validate_google_ocr_rescue_plan_v1(plan)
    return plan


def _input_binding_projection(binding: GoogleOcrInputBindingV1) -> dict[str, Any]:
    if type(binding) is GoogleOcrInlineInputV1:
        return {
            "kind": binding.kind.value,
            "sha256": binding.sha256,
            "size_bytes": binding.size_bytes,
        }
    if type(binding) is GoogleOcrImmutableGcsInputV1:
        return {
            "kind": binding.kind.value,
            "bucket": binding.bucket,
            "object_name": binding.object_name,
            "generation": binding.generation,
            "caller_verified_content_sha256": binding.caller_verified_content_sha256,
            "caller_verified_content_size_bytes": binding.caller_verified_content_size_bytes,
        }
    raise _error("execution receipt input_binding has an unsupported union member")


def _receipt_payload(receipt: GoogleOcrExecutionReceiptV1) -> dict[str, Any]:
    return {
        "format_version": receipt.format_version,
        "claim_boundary": receipt.claim_boundary,
        "plan_id": receipt.plan_id,
        "endpoint_hostname": receipt.endpoint_hostname,
        "http_method": receipt.http_method,
        "api_version": receipt.api_version,
        "processor_resource": receipt.processor_resource,
        "request_body_sha256": receipt.request_body_sha256,
        "request_body_size_bytes": receipt.request_body_size_bytes,
        "input_binding": _input_binding_projection(receipt.input_binding),
        "request_id": receipt.request_id,
        "operation_id": receipt.operation_id,
        "status": receipt.status.value,
        "http_status_code": receipt.http_status_code,
        "response_sha256": receipt.response_sha256,
        "response_size_bytes": receipt.response_size_bytes,
        "transport_capture_ref": _ref_projection(receipt.transport_capture_ref),
        "transport_authentication_state": receipt.transport_authentication_state.value,
        "self_hash_is_authority": receipt.self_hash_is_authority,
        "external_upload_authorized_by_receipt": receipt.external_upload_authorized_by_receipt,
    }


def _validate_optional_transport_id(value: Any, label: str) -> None:
    if value is not None and (type(value) is not str or not value or len(value) > 512):
        raise _error(f"{label} must be null or one nonempty bounded string")


def _validate_input_binding(
    binding: GoogleOcrInputBindingV1, page: AuthenticatedUnresolvedPageV1
) -> None:
    if type(binding) is GoogleOcrInlineInputV1:
        if binding.kind is not GoogleOcrInputBindingKindV1.INLINE:
            raise _error("inline input binding kind drifted")
        if binding.sha256 != page.page_image_ref.sha256:
            raise _error("inline input SHA does not equal the authenticated page_image_ref SHA")
        if binding.size_bytes != page.page_image_ref.size_bytes:
            raise _error("inline input size does not equal the authenticated page_image_ref size")
        return
    if type(binding) is GoogleOcrImmutableGcsInputV1:
        if binding.kind is not GoogleOcrInputBindingKindV1.IMMUTABLE_GCS:
            raise _error("GCS input binding kind drifted")
        if _GCS_BUCKET.fullmatch(binding.bucket) is None:
            raise _error("GCS bucket name drifted")
        if (
            type(binding.object_name) is not str
            or not binding.object_name
            or "\r" in binding.object_name
            or "\n" in binding.object_name
        ):
            raise _error("GCS object name must be one nonempty line")
        if (
            type(binding.generation) is not str
            or not binding.generation.isdigit()
            or int(binding.generation) <= 0
        ):
            raise _error("GCS generation must be one immutable positive decimal string")
        if binding.caller_verified_content_sha256 != page.page_image_ref.sha256:
            raise _error("caller-verified GCS content SHA does not equal page_image_ref SHA")
        if binding.caller_verified_content_size_bytes != page.page_image_ref.size_bytes:
            raise _error("caller-verified GCS content size does not equal page_image_ref size")
        return
    raise _error("execution receipt input_binding has an unsupported union member")


def validate_google_ocr_execution_receipt_v1(
    receipt: GoogleOcrExecutionReceiptV1,
    *,
    plan: GoogleOcrRescuePlanV1,
) -> None:
    """Validate caller-authenticated transport facts against the current plan."""

    validate_google_ocr_rescue_plan_v1(plan)
    if type(receipt) is not GoogleOcrExecutionReceiptV1:
        raise _error("receipt must be GoogleOcrExecutionReceiptV1")
    if (
        receipt.format_version != EXECUTION_RECEIPT_FORMAT_VERSION
        or receipt.claim_boundary != EXECUTION_RECEIPT_CLAIM_BOUNDARY
    ):
        raise _error("execution receipt format or claim boundary drifted")
    derivation = derive_google_ocr_profile_v1(plan.profile)
    if receipt.plan_id != plan.plan_id:
        raise _error("execution receipt belongs to a different request plan")
    if (
        receipt.endpoint_hostname != plan.profile.endpoint_hostname
        or receipt.http_method != derivation.http_method
        or receipt.api_version != plan.profile.api_version
        or receipt.processor_resource != plan.profile.processor_resource
    ):
        raise _error("transport endpoint/method/API/resource does not match the exact request plan")
    if (
        type(receipt.request_body_sha256) is not str
        or _SHA256.fullmatch(receipt.request_body_sha256) is None
    ):
        raise _error("request_body_sha256 must be lowercase SHA-256")
    _positive_int(receipt.request_body_size_bytes, "request_body_size_bytes")
    _validate_input_binding(receipt.input_binding, plan.page)
    _validate_optional_transport_id(receipt.request_id, "request_id")
    _validate_optional_transport_id(receipt.operation_id, "operation_id")
    if type(receipt.status) is not GoogleOcrExecutionStatusV1:
        raise _error("execution status drifted")
    if type(receipt.http_status_code) is not int or not 100 <= receipt.http_status_code <= 599:
        raise _error("http_status_code must be one exact HTTP status integer")
    if receipt.status is GoogleOcrExecutionStatusV1.SUCCEEDED:
        if not 200 <= receipt.http_status_code <= 299:
            raise _error("SUCCEEDED receipt requires a 2xx HTTP status")
    elif receipt.http_status_code < 400:
        raise _error("FAILED receipt requires a 4xx/5xx HTTP status")
    if (
        type(receipt.response_sha256) is not str
        or _SHA256.fullmatch(receipt.response_sha256) is None
    ):
        raise _error("response_sha256 must be lowercase SHA-256")
    _positive_int(receipt.response_size_bytes, "response_size_bytes")
    _content_ref(
        receipt.transport_capture_ref,
        ContentRefKindV1.TRANSPORT_CAPTURE,
        "transport_capture_ref",
    )
    if receipt.transport_capture_ref.size_bytes <= 0:
        raise _error("transport_capture_ref must bind nonempty authenticated capture bytes")
    if (
        receipt.transport_authentication_state
        is not TransportAuthenticationStateV1.CALLER_AUTHENTICATED_TRANSPORT_CAPTURE
        or receipt.self_hash_is_authority is not False
        or receipt.external_upload_authorized_by_receipt is not False
    ):
        raise _error(
            "receipt caller-authentication, self-hash, or upload-authority boundary drifted"
        )
    expected = f"gocrpv1:execution:{canonical_json_sha256_v1(_receipt_payload(receipt))}"
    if receipt.receipt_id != expected:
        raise _error("receipt_id does not bind the exact caller-authenticated transport facts")


def build_google_ocr_execution_receipt_v1(
    *,
    plan: GoogleOcrRescuePlanV1,
    endpoint_hostname: str,
    http_method: str,
    api_version: str,
    processor_resource: str,
    request_body_sha256: str,
    request_body_size_bytes: int,
    input_binding: GoogleOcrInputBindingV1,
    status: GoogleOcrExecutionStatusV1,
    http_status_code: int,
    response_sha256: str,
    response_size_bytes: int,
    transport_capture_ref: ExactContentRefV1,
    request_id: str | None = None,
    operation_id: str | None = None,
) -> GoogleOcrExecutionReceiptV1:
    """Bind caller-captured transport metadata; never execute or authorize it."""

    shell = GoogleOcrExecutionReceiptV1(
        format_version=EXECUTION_RECEIPT_FORMAT_VERSION,
        claim_boundary=EXECUTION_RECEIPT_CLAIM_BOUNDARY,
        plan_id=plan.plan_id,
        endpoint_hostname=endpoint_hostname,
        http_method=http_method,
        api_version=api_version,
        processor_resource=processor_resource,
        request_body_sha256=request_body_sha256,
        request_body_size_bytes=request_body_size_bytes,
        input_binding=input_binding,
        request_id=request_id,
        operation_id=operation_id,
        status=status,
        http_status_code=http_status_code,
        response_sha256=response_sha256,
        response_size_bytes=response_size_bytes,
        transport_capture_ref=transport_capture_ref,
        transport_authentication_state=(
            TransportAuthenticationStateV1.CALLER_AUTHENTICATED_TRANSPORT_CAPTURE
        ),
        self_hash_is_authority=False,
        external_upload_authorized_by_receipt=False,
        receipt_id="",
    )
    receipt = replace(
        shell,
        receipt_id=f"gocrpv1:execution:{canonical_json_sha256_v1(_receipt_payload(shell))}",
    )
    validate_google_ocr_execution_receipt_v1(receipt, plan=plan)
    return receipt


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


def _human_review_status(value: Any) -> dict[str, Any]:
    status = _require_exact_dict(
        value,
        allowed={"state", "stateMessage", "humanReviewOperation"},
        required={"state"},
        label="Document AI humanReviewStatus",
    )
    state = _require_string(status["state"], "Document AI humanReviewStatus.state")
    if state not in _HUMAN_REVIEW_STATES:
        raise _error("Document AI humanReviewStatus.state drifted")
    state_message = (
        _require_string(
            status["stateMessage"],
            "Document AI humanReviewStatus.stateMessage",
            allow_empty=True,
        )
        if "stateMessage" in status
        else ""
    )
    operation = (
        _require_string(
            status["humanReviewOperation"],
            "Document AI humanReviewStatus.humanReviewOperation",
        )
        if "humanReviewOperation" in status
        else None
    )
    if (state == "IN_PROGRESS") != (operation is not None):
        raise _error("humanReviewOperation must be present exactly for IN_PROGRESS")
    return {
        "state": state,
        "state_message": state_message,
        "human_review_operation": operation,
    }


def _document_ai_root(root: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    wrapper = _require_exact_dict(
        root,
        allowed={"document", "humanReviewStatus"},
        required={"document"},
        label="Document AI response",
    )
    metadata: dict[str, Any] = {
        "human_review_status": (
            _human_review_status(wrapper["humanReviewStatus"])
            if "humanReviewStatus" in wrapper
            else None
        )
    }
    document = _require_exact_dict(
        wrapper["document"],
        allowed={
            "text",
            "mimeType",
            "pages",
            "documentLayout",
            "chunkedDocument",
            "blobAssets",
        },
        required={"text"},
        label="Document AI document",
    )
    return document, metadata


def _normalize_document_ai_ocr(
    root: dict[str, Any], plan: GoogleOcrRescuePlanV1
) -> tuple[str, dict]:
    document, metadata = _document_ai_root(root)
    if any(field in document for field in ("documentLayout", "chunkedDocument", "blobAssets")):
        raise _error("Document AI OCR route cannot accept Layout Parser document unions")
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


def _annotations(value: Any, label: str) -> dict[str, Any] | None:
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
        ),
        "authority": dict(QUARANTINED_GENERATED_AUTHORITY),
    }


def _image_source(
    value: dict[str, Any], *, allowed_blob_asset_ids: set[str], label: str
) -> dict[str, Any]:
    source_keys = [key for key in ("blobAssetId", "gcsUri", "dataUri") if key in value]
    if len(source_keys) != 1:
        raise _error(f"{label} must contain exactly one documented image source union member")
    key = source_keys[0]
    raw = _require_string(value[key], f"{label}.{key}")
    if key == "blobAssetId":
        if raw not in allowed_blob_asset_ids:
            raise _error(f"{label}.blobAssetId is not present in document.blobAssets")
        source = {"kind": "BLOB_ASSET", "blob_asset_id": raw}
    elif key == "gcsUri":
        if not raw.startswith("gs://") or raw.count("/") < 3:
            raise _error(f"{label}.gcsUri must be one exact gs:// object URI")
        source = {
            "kind": "GCS_URI_QUARANTINED",
            "reference_sha256": sha256(raw.encode()).hexdigest(),
            "reference_size_bytes": len(raw.encode()),
        }
    else:
        if not raw.startswith("data:"):
            raise _error(f"{label}.dataUri must be one exact data URI")
        source = {
            "kind": "DATA_URI_QUARANTINED",
            "reference_sha256": sha256(raw.encode()).hexdigest(),
            "reference_size_bytes": len(raw.encode()),
        }
    source["authority"] = dict(QUARANTINED_GENERATED_AUTHORITY)
    return source


def _blob_assets(value: Any, label: str) -> tuple[list[dict[str, Any]], set[str]]:
    output = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(_require_list(value, label)):
        item_label = f"{label}[{index}]"
        item = _require_exact_dict(
            raw,
            allowed={"assetId", "content", "mimeType"},
            required={"assetId", "content", "mimeType"},
            label=item_label,
        )
        asset_id = _require_string(item["assetId"], f"{item_label}.assetId")
        if asset_id in seen_ids:
            raise _error(f"{item_label}.assetId is duplicated")
        seen_ids.add(asset_id)
        encoded = _require_string(item["content"], f"{item_label}.content", allow_empty=True)
        try:
            decoded = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise _error(f"{item_label}.content is not strict base64") from exc
        output.append(
            {
                "asset_id": asset_id,
                "mime_type": _require_string(item["mimeType"], f"{item_label}.mimeType"),
                "content_sha256": sha256(decoded).hexdigest(),
                "content_size_bytes": len(decoded),
                "authority": dict(QUARANTINED_GENERATED_AUTHORITY),
            }
        )
    return output, seen_ids


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
    blob_asset_ids: set[str],
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
                            blob_asset_ids=blob_asset_ids,
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
    blob_asset_ids: set[str],
) -> dict[str, Any]:
    if depth > 32:
        raise _error("Layout Parser block nesting exceeds the bounded depth")
    item = _require_exact_dict(
        value,
        allowed={
            "blockId",
            "pageSpan",
            "boundingBox",
            "textBlock",
            "tableBlock",
            "listBlock",
            "imageBlock",
        },
        required={"blockId", "pageSpan", "boundingBox"},
        label=label,
    )
    union = [key for key in ("textBlock", "tableBlock", "listBlock", "imageBlock") if key in item]
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
                        blob_asset_ids=blob_asset_ids,
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
                    blob_asset_ids=blob_asset_ids,
                ),
                "body_rows": _layout_parser_rows(
                    table["bodyRows"],
                    width=width,
                    height=height,
                    label=f"{label}.tableBlock.bodyRows",
                    depth=depth,
                    seen_ids=seen_ids,
                    blob_asset_ids=blob_asset_ids,
                ),
            }
        )
    elif kind == "listBlock":
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
                            blob_asset_ids=blob_asset_ids,
                        )
                        for index, child in enumerate(
                            _require_list(entry["blocks"], f"{entry_label}.blocks")
                        )
                    ]
                }
            )
        base.update({"kind": "LIST", "list_type": list_type, "list_entries": entries})
    else:
        image = _require_exact_dict(
            item[kind],
            allowed={
                "mimeType",
                "imageText",
                "annotations",
                "blobAssetId",
                "gcsUri",
                "dataUri",
            },
            required={"mimeType"},
            label=f"{label}.imageBlock",
        )
        base.update(
            {
                "kind": "IMAGE_QUARANTINED",
                "mime_type": _require_string(image["mimeType"], f"{label}.imageBlock.mimeType"),
                "image_text": (
                    _require_string(
                        image["imageText"],
                        f"{label}.imageBlock.imageText",
                        allow_empty=True,
                    )
                    if "imageText" in image
                    else ""
                ),
                "annotations": _annotations(
                    image.get("annotations"), f"{label}.imageBlock.annotations"
                ),
                "image_source": _image_source(
                    image,
                    allowed_blob_asset_ids=blob_asset_ids,
                    label=f"{label}.imageBlock",
                ),
                "authority": dict(QUARANTINED_GENERATED_AUTHORITY),
            }
        )
    return base


def _chunk_page_text(value: Any, *, label: str) -> dict[str, Any]:
    item = _require_exact_dict(
        value,
        allowed={"text", "pageSpan"},
        required={"text", "pageSpan"},
        label=label,
    )
    return {
        "text": _require_string(item["text"], f"{label}.text", allow_empty=True),
        "page_span": _layout_page_span(item["pageSpan"], f"{label}.pageSpan"),
        "authority": dict(QUARANTINED_GENERATED_AUTHORITY),
    }


def _chunk_field(value: Any, *, blob_asset_ids: set[str], label: str) -> dict[str, Any]:
    item = _require_exact_dict(
        value,
        allowed={"imageChunkField", "tableChunkField"},
        required=set(),
        label=label,
    )
    if len(item) != 1:
        raise _error(f"{label} must contain exactly one chunk field union member")
    if "imageChunkField" in item:
        image = _require_exact_dict(
            item["imageChunkField"],
            allowed={"annotations", "blobAssetId", "gcsUri", "dataUri"},
            required=set(),
            label=f"{label}.imageChunkField",
        )
        return {
            "kind": "IMAGE_CHUNK_QUARANTINED",
            "annotations": _annotations(
                image.get("annotations"), f"{label}.imageChunkField.annotations"
            ),
            "image_source": _image_source(
                image,
                allowed_blob_asset_ids=blob_asset_ids,
                label=f"{label}.imageChunkField",
            ),
            "authority": dict(QUARANTINED_GENERATED_AUTHORITY),
        }
    table = _require_exact_dict(
        item["tableChunkField"],
        allowed={"annotations"},
        required=set(),
        label=f"{label}.tableChunkField",
    )
    return {
        "kind": "TABLE_CHUNK_ANNOTATION_QUARANTINED",
        "annotations": _annotations(
            table.get("annotations"), f"{label}.tableChunkField.annotations"
        ),
        "authority": dict(QUARANTINED_GENERATED_AUTHORITY),
    }


def _chunked_document(
    value: Any,
    *,
    known_block_ids: set[str],
    blob_asset_ids: set[str],
    label: str,
) -> dict[str, Any]:
    document = _require_exact_dict(
        value,
        allowed={"chunks"},
        required={"chunks"},
        label=label,
    )
    chunks = []
    seen_chunk_ids: set[str] = set()
    for index, raw in enumerate(_require_list(document["chunks"], f"{label}.chunks")):
        chunk_label = f"{label}.chunks[{index}]"
        chunk = _require_exact_dict(
            raw,
            allowed={
                "chunkId",
                "sourceBlockIds",
                "content",
                "pageSpan",
                "pageHeaders",
                "pageFooters",
                "chunkFields",
            },
            required={"chunkId", "content", "pageSpan"},
            label=chunk_label,
        )
        chunk_id = _require_string(chunk["chunkId"], f"{chunk_label}.chunkId")
        if chunk_id in seen_chunk_ids:
            raise _error(f"{chunk_label}.chunkId is duplicated")
        seen_chunk_ids.add(chunk_id)
        source_ids = [
            _require_string(item, f"{chunk_label}.sourceBlockIds[{source_index}]")
            for source_index, item in enumerate(
                _require_list(chunk.get("sourceBlockIds", []), f"{chunk_label}.sourceBlockIds")
            )
        ]
        if len(set(source_ids)) != len(source_ids) or any(
            item not in known_block_ids for item in source_ids
        ):
            raise _error(f"{chunk_label}.sourceBlockIds are duplicated or unknown")
        chunks.append(
            {
                "chunk_id": chunk_id,
                "source_block_ids": source_ids,
                "content": _require_string(
                    chunk["content"], f"{chunk_label}.content", allow_empty=True
                ),
                "page_span": _layout_page_span(chunk["pageSpan"], f"{chunk_label}.pageSpan"),
                "page_headers": [
                    _chunk_page_text(item, label=f"{chunk_label}.pageHeaders[{item_index}]")
                    for item_index, item in enumerate(
                        _require_list(chunk.get("pageHeaders", []), f"{chunk_label}.pageHeaders")
                    )
                ],
                "page_footers": [
                    _chunk_page_text(item, label=f"{chunk_label}.pageFooters[{item_index}]")
                    for item_index, item in enumerate(
                        _require_list(chunk.get("pageFooters", []), f"{chunk_label}.pageFooters")
                    )
                ],
                "chunk_fields": [
                    _chunk_field(
                        item,
                        blob_asset_ids=blob_asset_ids,
                        label=f"{chunk_label}.chunkFields[{item_index}]",
                    )
                    for item_index, item in enumerate(
                        _require_list(chunk.get("chunkFields", []), f"{chunk_label}.chunkFields")
                    )
                ],
                "authority": dict(QUARANTINED_GENERATED_AUTHORITY),
            }
        )
    return {"chunks": chunks, "authority": dict(QUARANTINED_GENERATED_AUTHORITY)}


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
    blob_assets, blob_asset_ids = _blob_assets(
        document.get("blobAssets", []), "Document AI document.blobAssets"
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
            blob_asset_ids=blob_asset_ids,
        )
        for index, block in enumerate(
            _require_list(layout["blocks"], "Document AI documentLayout.blocks")
        )
    ]
    tables = [block for block in blocks if block["kind"] == "TABLE"]
    chunked = (
        _chunked_document(
            document["chunkedDocument"],
            known_block_ids=seen_ids,
            blob_asset_ids=blob_asset_ids,
            label="Document AI document.chunkedDocument",
        )
        if "chunkedDocument" in document
        else None
    )
    return raw_text, {
        "kind": "DOCUMENT_AI_DOCUMENT_LAYOUT",
        "response_metadata": metadata,
        "source_physical_page": plan.page.physical_page,
        "pixel_width": plan.page.pixel_width,
        "pixel_height": plan.page.pixel_height,
        "blocks": blocks,
        "tables": tables,
        "chunked_document": chunked,
        "blob_assets": blob_assets,
        "generated_and_image_evidence_quarantined": True,
    }


def normalize_google_ocr_response_v1(
    *,
    plan: GoogleOcrRescuePlanV1,
    execution_receipt: GoogleOcrExecutionReceiptV1,
    raw_response_bytes: bytes,
) -> dict[str, Any]:
    """Normalize captured REST JSON without executing or trusting the provider.

    ``raw_response_bytes`` must be the exact captured response bytes.  Their SHA
    is computed here; callers cannot inject a self-reported response hash.
    """

    validate_google_ocr_rescue_plan_v1(plan)
    validate_google_ocr_execution_receipt_v1(execution_receipt, plan=plan)
    if execution_receipt.status is not GoogleOcrExecutionStatusV1.SUCCEEDED:
        raise _error("only a caller-authenticated successful transport receipt can be normalized")
    raw_sha256 = sha256(raw_response_bytes).hexdigest() if type(raw_response_bytes) is bytes else ""
    if execution_receipt.response_sha256 != raw_sha256 or execution_receipt.response_size_bytes != (
        len(raw_response_bytes) if type(raw_response_bytes) is bytes else -1
    ):
        raise _error("raw response bytes do not match the caller-authenticated execution receipt")
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
            "sha256": raw_sha256,
            "size_bytes": len(raw_response_bytes),
            "execution_receipt_id": execution_receipt.receipt_id,
            "transport_capture_ref": _ref_projection(execution_receipt.transport_capture_ref),
        },
        "raw_text": raw_text,
        "structure": structure,
        "authority": dict(OUTPUT_AUTHORITY),
    }
    payload["challenger_id"] = f"gocrpv1:challenger:{canonical_json_sha256_v1(payload)}"
    return payload
