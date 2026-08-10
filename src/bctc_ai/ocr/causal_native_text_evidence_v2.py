"""Authenticated causal-native evidence with source-order line projection.

V1 remains sealed.  This add-only adapter keeps the exact V1 causal-visibility
provider and its runtime ledger, but replaces the unsafe lexicographic line
projection at the evidence boundary.  PyMuPDF ``sort=True`` words stay in their
global visual order and lines are contiguous first-occurrence runs.  A line
identity that reappears after another line is terminally quarantined instead of
being silently reordered.

The raw V1 wrapper payload is backend-only.  The public result contains either
the exact accepted source-order projection or no source text for a contiguity
terminal.  Every result is bound to authenticated source, provider, policies,
page cropbox geometry, request, and full-reader control identities.
"""

from __future__ import annotations

import re
import socket
import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from pathlib import Path
from typing import Any

import fitz
import yaml

from bctc_ai.ocr.causal_native_text import (
    load_causal_native_text_policy,
    read_causal_native_text_page,
    round_points_to_millipoints,
)
from bctc_ai.ocr.causal_native_text_evidence_v1 import (
    CausalNativeTextEvidenceError,
    _authenticated_policy_copies,
    _canonical_clone,
    _canonical_json_bytes,
    _canonical_json_sha256,
    _require_nonnegative_integer,
    _require_positive_integer,
    _require_sha256,
    _same_typed_json,
    _stable_regular_bytes,
    _validate_json_tree,
    _validate_provider_runtime_ledger,
    _validate_request,
)

__all__ = [
    "BACKEND_FIELDS",
    "BACKEND_FORMAT_VERSION",
    "COORDINATE_AUTHORITY_FIELDS",
    "CausalNativeTextEvidenceError",
    "LINE_CONTIGUITY_FAILURE_TYPE",
    "LINE_CONTIGUITY_STATUS",
    "ORDERING_POLICY_IDENTITY_FIELDS",
    "ORDERING_POLICY_RECORD_PATH",
    "ORDERING_RECEIPT_FIELDS",
    "ORDERING_RECEIPT_FORMAT_VERSION",
    "RESULT_FIELDS",
    "RESULT_FORMAT_VERSION",
    "RESULT_METRIC_FIELDS",
    "TERMINAL_STATUSES",
    "build_causal_native_text_evidence_v2",
    "validate_causal_native_text_evidence_v2_envelopes",
    "validate_causal_native_text_evidence_v2_replay",
]


BACKEND_FORMAT_VERSION = "BANK_CORPUS_WAVE_1_CAUSAL_NATIVE_BACKEND_PAYLOAD_V2"
RESULT_FORMAT_VERSION = "BANK_CORPUS_WAVE_1_ROLE_B_CAUSAL_NATIVE_PAGE_READ_RESULT_V2"
ORDERING_RECEIPT_FORMAT_VERSION = "BANK_CORPUS_WAVE_1_ROLE_B_CAUSAL_NATIVE_VISUAL_ORDER_RECEIPT_V1"
ORDERING_POLICY_RECORD_PATH = "config/ocr/causal-native-text-evidence-v2.yaml"
TERMINAL_STATUSES = frozenset(
    {
        "CAUSAL_NATIVE_TEXT_READ_COMPLETE",
        "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY",
        "UNRESOLVED_NATIVE_TEXT_QUALITY",
        "UNRESOLVED_CAUSAL_NATIVE_LINE_CONTIGUITY",
    }
)

_ROUTE = "CAUSAL_NATIVE_TEXT"
_BACKEND_CLAIM_BOUNDARY = (
    "AUTHENTICATED_CAUSAL_NATIVE_WRAPPER_AND_VISUAL_ORDER_EVIDENCE_FOR_ONE_EXACT_PAGE_REQUEST_ONLY"
)
_RESULT_CLAIM_BOUNDARY = "SOURCE_VISIBLE_NATIVE_PAGE_TEXT_GEOMETRY_AND_VISUAL_ORDER_EVIDENCE_ONLY"
_ORDERING_POLICY = "CAUSAL_NATIVE_TEXT_VISUAL_ORDER_EVIDENCE_V2"
_SOURCE_WORD_ORDER = "PYMUPDF_GET_TEXT_WORDS_SORT_TRUE"
_LINE_PROJECTION = "CONTIGUOUS_FIRST_OCCURRENCE_LINE_RUNS"
_CONTIGUITY_STATUS = "UNRESOLVED_CAUSAL_NATIVE_LINE_CONTIGUITY"
_CONTIGUITY_FAILURE = "NoncontiguousNativeLineIdentity"
_ORDER_ACCEPTED = "CONTIGUOUS_SOURCE_ORDER_ACCEPTED"
_ORDER_SOURCE_TERMINAL = "SOURCE_ORDER_NOT_APPLICABLE_TO_UPSTREAM_TERMINAL"
_ORDER_QUARANTINED = "NONCONTIGUOUS_LINE_ORDER_QUARANTINED"
_SCORE_KIND = "NATIVE_TEXT_NO_RECOGNITION_SCORE"
_SAFE_TYPE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")
_GIT_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_PROVIDER = "PYMUPDF_CAUSAL_NATIVE_TEXT_VISIBILITY_V1"
_CAUSAL_POLICY_RECORD_PATH = "config/ocr/causal-native-text-v1.yaml"
_QUALITY_POLICY_RECORD_PATH = "config/ocr/native-text-quality-v2.yaml"

_REQUEST_FIELDS = {
    "bank_identity_used",
    "filename_used",
    "format_version",
    "git_commit",
    "historical_values_used",
    "implementation_ledger_sha256",
    "input_ledger_sha256",
    "physical_page",
    "pre_ocr_feature_fingerprint_sha256",
    "provider_identity_sha256",
    "render_runtime_identity_sha256",
    "render_specification",
    "role_a_used",
    "route",
    "route_plan_sha256",
    "schema_used",
    "selection_receipt_sha256",
    "sentinel_sha256",
    "source_sha256",
    "source_size_bytes",
}
_PROVIDER_LEDGER_FIELDS = {
    "config_records",
    "ocr_fallback_allowed",
    "provider",
    "pymupdf_binding_version",
    "pymupdf_distribution_version",
    "pymupdf_runtime_versions",
    "sha256",
}
_CONFIG_RECORD_FIELDS = {"path", "sha256", "size_bytes"}

_ORDERING_POLICY_IDENTITY_FIELDS = {"path", "sha256", "size_bytes"}
_WORD_FIELDS = {
    "raw_text",
    "score",
    "score_kind",
    "canonical_bbox_mpt",
    "block_number",
    "line_number",
    "word_number",
}
_LINE_FIELDS = {
    "raw_text",
    "score",
    "score_kind",
    "canonical_bbox_mpt",
    "block_number",
    "line_number",
    "words",
}
_QUARANTINED_FIELDS = {
    "page",
    "text_sha256",
    "nonwhitespace_character_count",
    "bbox_mpt",
    "block_number",
    "line_number",
    "span_number",
    "color",
    "alpha",
    "render_sequence",
    "occluding_sequence",
    "occluding_object_type",
    "reason",
}
_COORDINATE_FIELDS = {
    "canonical_coordinate_system",
    "coordinate_unit",
    "geometry_source",
    "pdf_rotation_applied_to_coordinates",
    "pdf_rotation_degrees",
    "canonical_cropbox_bounds_mpt",
    "source_cropbox_mpt",
    "source_mediabox_mpt",
}
_ORDERING_RECEIPT_FIELDS = {
    "format_version",
    "policy",
    "ordering_policy_identity",
    "source_word_order",
    "line_projection",
    "status",
    "source_word_count",
    "line_run_count",
    "distinct_line_identity_count",
    "noncontiguous_line_identity_count",
    "source_words_sha256",
    "line_runs_sha256",
    "noncontiguous_line_identities_sha256",
}
_PUBLIC_PAYLOAD_FIELDS = {
    "status",
    "failure_type",
    "native_text_quality",
    "corruption_markers",
    "lines",
    "words",
    "quarantined_spans",
    "ordering_receipt",
    "ocr_fallback_used",
    "source_blank_claimed",
}
_BACKEND_FIELDS = {
    "format_version",
    "status",
    "claim_boundary",
    "document_id",
    "source_sha256",
    "source_size_bytes",
    "physical_page",
    "route",
    "request_sha256",
    "request",
    "full_control_identity_sha256",
    "provider_identity_sha256",
    "provider_runtime_ledger",
    "causal_native_policy_identity",
    "native_text_quality_policy_identity",
    "ordering_policy_identity",
    "coordinate_authority",
    "raw_causal_native_wrapper_payload",
    "ordering_receipt",
    "ocr_fallback_used",
    "source_blank_claimed",
    "safety",
}
_RESULT_FIELDS = {
    "format_version",
    "status",
    "claim_boundary",
    "document_id",
    "source_sha256",
    "source_size_bytes",
    "physical_page",
    "route",
    "request_sha256",
    "request",
    "full_control_identity_sha256",
    "provider_identity_sha256",
    "backend_payload_sha256",
    "ordering_policy_identity",
    "coordinate_authority",
    "failure_type",
    "native_text_quality",
    "corruption_markers",
    "lines",
    "words",
    "quarantined_spans",
    "ordering_receipt",
    "metrics",
    "ocr_fallback_used",
    "source_blank_claimed",
    "safety",
}
_RESULT_METRIC_FIELDS = {
    "line_count",
    "word_token_count",
    "ghost_quarantined_span_count",
    "ordering_quarantined_raw_line_run_count",
    "ordering_quarantined_raw_word_count",
    "noncontiguous_line_identity_count",
}

BACKEND_FIELDS = frozenset(_BACKEND_FIELDS)
RESULT_FIELDS = frozenset(_RESULT_FIELDS)
ORDERING_RECEIPT_FIELDS = frozenset(_ORDERING_RECEIPT_FIELDS)
RESULT_METRIC_FIELDS = frozenset(_RESULT_METRIC_FIELDS)
COORDINATE_AUTHORITY_FIELDS = frozenset(_COORDINATE_FIELDS)
ORDERING_POLICY_IDENTITY_FIELDS = frozenset(_ORDERING_POLICY_IDENTITY_FIELDS)
LINE_CONTIGUITY_STATUS = _CONTIGUITY_STATUS
LINE_CONTIGUITY_FAILURE_TYPE = _CONTIGUITY_FAILURE


class _NetworkAccessDenied(RuntimeError):
    """A provider attempted network access inside the native evidence boundary."""


@dataclass
class _NetworkDenialState:
    attempted: bool = False


_NETWORK_GUARD_LOCK = threading.RLock()


@contextmanager
def _deny_network_connections() -> Iterator[_NetworkDenialState]:
    """Deny connection attempts during one provider call and restore exactly."""

    with _NETWORK_GUARD_LOCK:
        original_create_connection = socket.create_connection
        original_connect = socket.socket.connect
        original_connect_ex = socket.socket.connect_ex
        state = _NetworkDenialState()

        def deny(*_args: Any, **_kwargs: Any) -> Any:
            state.attempted = True
            raise _NetworkAccessDenied("native evidence network access is prohibited")

        socket.create_connection = deny
        socket.socket.connect = deny
        socket.socket.connect_ex = deny
        try:
            yield state
        finally:
            socket.create_connection = original_create_connection
            socket.socket.connect = original_connect
            socket.socket.connect_ex = original_connect_ex


def _safety_boundary() -> dict[str, bool]:
    return {
        "statement_classified": False,
        "table_classified": False,
        "rows_reconstructed": False,
        "cells_interpreted": False,
        "absence_claimed": False,
        "bank_registry_metadata_used": False,
        "filename_metadata_used": False,
        "role_a_used": False,
        "schema_used": False,
        "mapping_used": False,
        "historical_values_used": False,
        "ocr_fallback_used": False,
        "network_used": False,
    }


def _ordering_policy_path(causal_policy_path: Path) -> Path:
    if not isinstance(causal_policy_path, Path):
        raise CausalNativeTextEvidenceError("causal policy locator must be a Path")
    return causal_policy_path.parent / Path(ORDERING_POLICY_RECORD_PATH).name


def _validate_ordering_policy_identity(
    expected: Mapping[str, Any],
    *,
    ordering_policy_path: Path,
) -> tuple[dict[str, Any], bytes]:
    if not isinstance(expected, Mapping):
        raise CausalNativeTextEvidenceError("native ordering policy identity must be an object")
    identity = _canonical_clone(dict(expected))
    if set(identity) != _ORDERING_POLICY_IDENTITY_FIELDS:
        raise CausalNativeTextEvidenceError("native ordering policy identity fields drifted")
    if identity["path"] != ORDERING_POLICY_RECORD_PATH:
        raise CausalNativeTextEvidenceError("native ordering policy path drifted")
    _require_sha256(identity["sha256"], "native ordering policy identity")
    _require_positive_integer(identity["size_bytes"], "native ordering policy size")
    policy_bytes = _stable_regular_bytes(ordering_policy_path)
    if (
        identity["size_bytes"] != len(policy_bytes)
        or identity["sha256"] != sha256(policy_bytes).hexdigest()
    ):
        raise CausalNativeTextEvidenceError("native ordering policy bytes drifted")
    return identity, policy_bytes


def _load_ordering_policy(policy_bytes: bytes) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(policy_bytes.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as error:
        raise CausalNativeTextEvidenceError("native ordering policy cannot be loaded") from error
    if type(payload) is not dict:
        raise CausalNativeTextEvidenceError("native ordering policy must be an object")
    expected_root = {
        "version": 2,
        "policy": _ORDERING_POLICY,
        "claim_boundary": "SOURCE_VISIBLE_NATIVE_TEXT_GEOMETRY_AND_SOURCE_ORDER_ONLY",
    }
    if set(payload) != {*expected_root, "ordering", "geometry", "safety"} or any(
        payload.get(key) != value for key, value in expected_root.items()
    ):
        raise CausalNativeTextEvidenceError("native ordering policy identity drifted")
    expected_ordering = {
        "source_word_order": _SOURCE_WORD_ORDER,
        "line_projection": _LINE_PROJECTION,
        "require_unique_word_identity": True,
        "require_strict_word_number_order_within_run": True,
        "require_flattened_lines_equal_source_words": True,
        "noncontiguous_line_status": _CONTIGUITY_STATUS,
        "noncontiguous_line_failure_type": _CONTIGUITY_FAILURE,
        "quarantine_projection": "HASH_AND_COUNT_ONLY",
    }
    expected_geometry = {
        "canonical_coordinate_system": "UNROTATED_PDF_MILLI_POINTS_TOP_LEFT",
        "canonical_page_bounds": "UNROTATED_CROPBOX_LOCAL_BOUNDS",
        "require_word_boxes_inside_cropbox": True,
        "require_line_boxes_inside_cropbox": True,
        "require_quarantined_span_boxes_inside_cropbox": True,
    }
    expected_safety = {
        "preserve_raw_wrapper_payload_in_backend_only": True,
        "excluded_text_hash_only": True,
        "ordering_quarantine_hash_and_count_only": True,
        "ocr_fallback_allowed": False,
        "network_allowed": False,
        "source_blank_claim_allowed": False,
        "absence_claim_allowed": False,
        "table_or_statement_semantics_allowed": False,
        "schema_inputs_allowed": False,
        "role_a_inputs_allowed": False,
        "historical_values_allowed": False,
        "bank_or_page_specific_rules_allowed": False,
    }
    for key, expected in (
        ("ordering", expected_ordering),
        ("geometry", expected_geometry),
        ("safety", expected_safety),
    ):
        if type(payload[key]) is not dict or not _same_typed_json(payload[key], expected):
            raise CausalNativeTextEvidenceError(f"native ordering policy {key} boundary drifted")
    return _canonical_clone(payload)


def _validate_expected_request(
    request: Mapping[str, Any],
    *,
    request_sha256: str,
    document_id: str,
    source_sha256: str,
    source_size_bytes: int,
    physical_page: int,
    provider_identity_sha256: str,
) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        raise CausalNativeTextEvidenceError("expected sealed request must be an object")
    expected = _canonical_clone(dict(request))
    if set(expected) != _REQUEST_FIELDS:
        raise CausalNativeTextEvidenceError("expected sealed request fields drifted")
    if expected["format_version"] != "BANK_CORPUS_WAVE_1_PAGE_READ_REQUEST_V1":
        raise CausalNativeTextEvidenceError("expected sealed request format drifted")
    if expected["route"] != _ROUTE:
        raise CausalNativeTextEvidenceError("expected sealed request route drifted")
    if expected["render_runtime_identity_sha256"] is not None:
        raise CausalNativeTextEvidenceError("expected native request has render runtime")
    if expected["render_specification"] is not None:
        raise CausalNativeTextEvidenceError("expected native request has render specification")
    for key in (
        "bank_identity_used",
        "filename_used",
        "historical_values_used",
        "role_a_used",
        "schema_used",
    ):
        if expected[key] is not False:
            raise CausalNativeTextEvidenceError("expected sealed request safety drifted")
    if (
        type(expected["git_commit"]) is not str
        or _GIT_SHA1_RE.fullmatch(expected["git_commit"]) is None
    ):
        raise CausalNativeTextEvidenceError("expected sealed request Git identity drifted")
    for key in (
        "implementation_ledger_sha256",
        "input_ledger_sha256",
        "pre_ocr_feature_fingerprint_sha256",
        "provider_identity_sha256",
        "route_plan_sha256",
        "selection_receipt_sha256",
        "sentinel_sha256",
        "source_sha256",
    ):
        _require_sha256(expected[key], f"expected sealed request {key}")
    _require_sha256(request_sha256, "expected sealed request identity")
    if _canonical_json_sha256(expected) != request_sha256:
        raise CausalNativeTextEvidenceError("expected sealed request canonical hash drifted")
    _require_sha256(source_sha256, "expected source identity")
    _require_positive_integer(source_size_bytes, "expected source size")
    _require_positive_integer(physical_page, "expected physical page")
    if document_id != f"sha256:{source_sha256}":
        raise CausalNativeTextEvidenceError("expected document identity drifted")
    if (
        expected["source_sha256"] != source_sha256
        or expected["source_size_bytes"] != source_size_bytes
        or expected["physical_page"] != physical_page
        or expected["provider_identity_sha256"] != provider_identity_sha256
    ):
        raise CausalNativeTextEvidenceError("expected sealed request boundary drifted")
    return expected


def _validate_expected_provider_runtime_ledger(
    value: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    if not isinstance(value, Mapping):
        raise CausalNativeTextEvidenceError("expected provider ledger must be an object")
    ledger = _canonical_clone(dict(value))
    if set(ledger) != _PROVIDER_LEDGER_FIELDS:
        raise CausalNativeTextEvidenceError("expected provider ledger fields drifted")
    if ledger["provider"] != _PROVIDER or ledger["ocr_fallback_allowed"] is not False:
        raise CausalNativeTextEvidenceError("expected provider ledger boundary drifted")
    provider_identity = _require_sha256(ledger["sha256"], "expected provider identity")
    projection = {key: item for key, item in ledger.items() if key != "sha256"}
    if _canonical_json_sha256(projection) != provider_identity:
        raise CausalNativeTextEvidenceError("expected provider ledger identity drifted")
    for key in ("pymupdf_binding_version", "pymupdf_distribution_version"):
        if type(ledger[key]) is not str or not ledger[key]:
            raise CausalNativeTextEvidenceError("expected provider version drifted")
    runtime_versions = ledger["pymupdf_runtime_versions"]
    if (
        type(runtime_versions) is not list
        or not runtime_versions
        or any(
            item is not None and (type(item) is not str or not item) for item in runtime_versions
        )
    ):
        raise CausalNativeTextEvidenceError("expected provider runtime versions drifted")
    config_records = ledger["config_records"]
    if type(config_records) is not list or len(config_records) != 2:
        raise CausalNativeTextEvidenceError("expected provider config ledger drifted")
    records: dict[str, dict[str, Any]] = {}
    for value_record in config_records:
        if type(value_record) is not dict or set(value_record) != _CONFIG_RECORD_FIELDS:
            raise CausalNativeTextEvidenceError("expected provider config fields drifted")
        record = _canonical_clone(value_record)
        path = record["path"]
        if type(path) is not str or path in records:
            raise CausalNativeTextEvidenceError("expected provider config path drifted")
        _require_sha256(record["sha256"], "expected provider config identity")
        _require_positive_integer(record["size_bytes"], "expected provider config size")
        records[path] = record
    if set(records) != {_CAUSAL_POLICY_RECORD_PATH, _QUALITY_POLICY_RECORD_PATH}:
        raise CausalNativeTextEvidenceError("expected provider config record set drifted")
    return ledger, records


def _rect_millipoints(rect: fitz.Rect, label: str) -> list[int]:
    values = [rect.x0, rect.y0, rect.x1, rect.y1]
    if any(type(value) not in {int, float} or not isfinite(float(value)) for value in values):
        raise CausalNativeTextEvidenceError(f"{label} contains non-finite geometry")
    try:
        result = [round_points_to_millipoints(value) for value in values]
    except Exception:
        raise CausalNativeTextEvidenceError(f"{label} cannot be canonicalized") from None
    if result[0] > result[2] or result[1] > result[3]:
        raise CausalNativeTextEvidenceError(f"{label} has inverted geometry")
    return result


def _coordinate_authority(page: fitz.Page) -> dict[str, Any]:
    cropbox = _rect_millipoints(page.cropbox, "page cropbox")
    mediabox = _rect_millipoints(page.mediabox, "page mediabox")
    width = cropbox[2] - cropbox[0]
    height = cropbox[3] - cropbox[1]
    if width <= 0 or height <= 0:
        raise CausalNativeTextEvidenceError("page cropbox has no positive area")
    rotation = page.rotation
    if type(rotation) is not int or rotation not in {0, 90, 180, 270}:
        raise CausalNativeTextEvidenceError("page rotation identity drifted")
    authority = {
        "canonical_coordinate_system": "UNROTATED_PDF_MILLI_POINTS_TOP_LEFT",
        "coordinate_unit": "MILLI_POINT",
        "geometry_source": "PYMUPDF_NATIVE_TEXT_WORD_GEOMETRY",
        "pdf_rotation_applied_to_coordinates": False,
        "pdf_rotation_degrees": rotation,
        "canonical_cropbox_bounds_mpt": [0, 0, width, height],
        "source_cropbox_mpt": cropbox,
        "source_mediabox_mpt": mediabox,
    }
    return _validate_coordinate_authority(authority)


def _validate_integer_bbox(value: Any, label: str) -> list[int]:
    if type(value) is not list or len(value) != 4 or any(type(item) is not int for item in value):
        raise CausalNativeTextEvidenceError(f"{label} must be four integer millipoints")
    if value[0] >= value[2] or value[1] >= value[3]:
        raise CausalNativeTextEvidenceError(f"{label} must have positive-area geometry")
    return value


def _validate_coordinate_authority(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _COORDINATE_FIELDS:
        raise CausalNativeTextEvidenceError("native coordinate authority fields drifted")
    authority = _canonical_clone(value)
    expected_strings = {
        "canonical_coordinate_system": "UNROTATED_PDF_MILLI_POINTS_TOP_LEFT",
        "coordinate_unit": "MILLI_POINT",
        "geometry_source": "PYMUPDF_NATIVE_TEXT_WORD_GEOMETRY",
        "pdf_rotation_applied_to_coordinates": False,
    }
    if any(authority[key] != expected for key, expected in expected_strings.items()):
        raise CausalNativeTextEvidenceError("native coordinate authority drifted")
    if type(authority["pdf_rotation_degrees"]) is not int or authority[
        "pdf_rotation_degrees"
    ] not in {0, 90, 180, 270}:
        raise CausalNativeTextEvidenceError("native page rotation drifted")
    local = _validate_integer_bbox(
        authority["canonical_cropbox_bounds_mpt"], "canonical cropbox bounds"
    )
    crop = _validate_integer_bbox(authority["source_cropbox_mpt"], "source cropbox")
    media = _validate_integer_bbox(authority["source_mediabox_mpt"], "source mediabox")
    if local[:2] != [0, 0] or local[2] <= 0 or local[3] <= 0:
        raise CausalNativeTextEvidenceError("canonical cropbox bounds drifted")
    if crop[2] - crop[0] != local[2] or crop[3] - crop[1] != local[3]:
        raise CausalNativeTextEvidenceError("source and canonical cropbox dimensions drifted")
    if crop[0] < media[0] or crop[1] < media[1] or crop[2] > media[2] or crop[3] > media[3]:
        raise CausalNativeTextEvidenceError("source cropbox falls outside the mediabox")
    return authority


def _validate_bbox_in_cropbox(
    value: Any,
    *,
    authority: Mapping[str, Any],
    label: str,
) -> list[int]:
    bbox = _validate_integer_bbox(value, label)
    bounds = authority["canonical_cropbox_bounds_mpt"]
    if bbox[0] < bounds[0] or bbox[1] < bounds[1] or bbox[2] > bounds[2] or bbox[3] > bounds[3]:
        raise CausalNativeTextEvidenceError(f"{label} falls outside the page cropbox")
    return bbox


def _validate_word(
    value: Any,
    *,
    authority: Mapping[str, Any],
    label: str,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _WORD_FIELDS:
        raise CausalNativeTextEvidenceError(f"{label} fields drifted")
    word = _canonical_clone(value)
    raw_text = word["raw_text"]
    if (
        type(raw_text) is not str
        or not raw_text
        or not any(not character.isspace() for character in raw_text)
    ):
        raise CausalNativeTextEvidenceError(f"{label} text is empty")
    if word["score"] is not None or word["score_kind"] != _SCORE_KIND:
        raise CausalNativeTextEvidenceError(f"{label} score semantics drifted")
    _validate_bbox_in_cropbox(
        word["canonical_bbox_mpt"], authority=authority, label=f"{label} bbox"
    )
    for key in ("block_number", "line_number", "word_number"):
        _require_nonnegative_integer(word[key], f"{label} {key}")
    return word


def _word_identity(word: Mapping[str, Any]) -> tuple[int, int, int]:
    return (word["block_number"], word["line_number"], word["word_number"])


def _line_identity(word_or_line: Mapping[str, Any]) -> tuple[int, int]:
    return (word_or_line["block_number"], word_or_line["line_number"])


def _line_bbox(words: list[dict[str, Any]]) -> list[int]:
    return [
        min(word["canonical_bbox_mpt"][0] for word in words),
        min(word["canonical_bbox_mpt"][1] for word in words),
        max(word["canonical_bbox_mpt"][2] for word in words),
        max(word["canonical_bbox_mpt"][3] for word in words),
    ]


def _validate_source_words(
    value: Any,
    *,
    authority: Mapping[str, Any],
) -> list[dict[str, Any]]:
    if type(value) is not list:
        raise CausalNativeTextEvidenceError("native source words must be an array")
    words = [
        _validate_word(word, authority=authority, label="native source word") for word in value
    ]
    identities: set[tuple[int, int, int]] = set()
    for word in words:
        identity = _word_identity(word)
        if identity in identities:
            raise CausalNativeTextEvidenceError("native source word identity is duplicated")
        identities.add(identity)
    return words


def _validate_raw_lines(
    value: Any,
    *,
    source_words: list[dict[str, Any]],
    authority: Mapping[str, Any],
) -> list[dict[str, Any]]:
    if type(value) is not list:
        raise CausalNativeTextEvidenceError("native wrapper lines must be an array")
    lines = _canonical_clone(value)
    raw_words_by_line: dict[tuple[int, int], list[dict[str, Any]]] = {}
    seen_lines: set[tuple[int, int]] = set()
    for line in lines:
        if type(line) is not dict or set(line) != _LINE_FIELDS:
            raise CausalNativeTextEvidenceError("native wrapper line fields drifted")
        if line["score"] is not None or line["score_kind"] != _SCORE_KIND:
            raise CausalNativeTextEvidenceError("native wrapper line score semantics drifted")
        block_number = _require_nonnegative_integer(
            line["block_number"], "native wrapper line block_number"
        )
        line_number = _require_nonnegative_integer(
            line["line_number"], "native wrapper line line_number"
        )
        identity = (block_number, line_number)
        if identity in seen_lines:
            raise CausalNativeTextEvidenceError("native wrapper line identity is duplicated")
        seen_lines.add(identity)
        if type(line["words"]) is not list or not line["words"]:
            raise CausalNativeTextEvidenceError("native wrapper line has no words")
        line_words = [
            _validate_word(
                word,
                authority=authority,
                label="native wrapper line word",
            )
            for word in line["words"]
        ]
        for word in line_words:
            if _line_identity(word) != identity:
                raise CausalNativeTextEvidenceError("native wrapper word line identity drifted")
        if line["raw_text"] != " ".join(word["raw_text"] for word in line_words):
            raise CausalNativeTextEvidenceError("native wrapper line text projection drifted")
        if not _same_typed_json(line["canonical_bbox_mpt"], _line_bbox(line_words)):
            raise CausalNativeTextEvidenceError("native wrapper line geometry projection drifted")
        _validate_bbox_in_cropbox(
            line["canonical_bbox_mpt"],
            authority=authority,
            label="native wrapper line bbox",
        )
        raw_words_by_line[identity] = line_words

    source_words_by_line: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for word in source_words:
        source_words_by_line.setdefault(_line_identity(word), []).append(word)
    if set(raw_words_by_line) != set(source_words_by_line):
        raise CausalNativeTextEvidenceError("native wrapper line identity set drifted")
    for identity, expected_words in source_words_by_line.items():
        if not _same_typed_json(raw_words_by_line[identity], expected_words):
            raise CausalNativeTextEvidenceError(
                "native wrapper line/source word membership drifted"
            )
    return lines


def _validate_quarantined_spans(
    value: Any,
    *,
    physical_page: int,
    authority: Mapping[str, Any],
) -> list[dict[str, Any]]:
    if type(value) is not list:
        raise CausalNativeTextEvidenceError("quarantined spans must be an array")
    spans = _canonical_clone(value)
    for span in spans:
        if type(span) is not dict or set(span) != _QUARANTINED_FIELDS:
            raise CausalNativeTextEvidenceError("quarantined span fields drifted")
        if span["page"] != physical_page:
            raise CausalNativeTextEvidenceError("quarantined span page drifted")
        _require_sha256(span["text_sha256"], "quarantined text identity")
        _require_positive_integer(
            span["nonwhitespace_character_count"],
            "quarantined nonwhitespace character count",
        )
        _validate_bbox_in_cropbox(
            span["bbox_mpt"],
            authority=authority,
            label="quarantined span bbox",
        )
        for key in ("block_number", "line_number", "span_number", "render_sequence"):
            _require_nonnegative_integer(span[key], f"quarantined span {key}")
        if type(span["color"]) is not int or not 0 <= span["color"] <= 0xFFFFFF:
            raise CausalNativeTextEvidenceError("quarantined span color drifted")
        if type(span["alpha"]) is not int or not 0 <= span["alpha"] <= 255:
            raise CausalNativeTextEvidenceError("quarantined span alpha drifted")
        if span["occluding_sequence"] is not None:
            _require_nonnegative_integer(
                span["occluding_sequence"], "quarantined occluding sequence"
            )
        if (
            span["occluding_object_type"] is not None
            and type(span["occluding_object_type"]) is not str
        ):
            raise CausalNativeTextEvidenceError("quarantined object type drifted")
        if type(span["reason"]) is not str or not span["reason"]:
            raise CausalNativeTextEvidenceError("quarantined span reason drifted")
    return spans


def _validate_corruption_markers(value: Any) -> list[str]:
    if type(value) is not list or any(type(marker) is not str or not marker for marker in value):
        raise CausalNativeTextEvidenceError("native corruption markers drifted")
    if value != sorted(set(value)):
        raise CausalNativeTextEvidenceError("native corruption marker ordering drifted")
    return _canonical_clone(value)


def _validate_safe_failure_type(value: Any, label: str) -> str:
    if type(value) is not str or _SAFE_TYPE_NAME_RE.fullmatch(value) is None:
        raise CausalNativeTextEvidenceError(f"{label} failure type drifted")
    return value


def _validate_raw_wrapper_payload(
    value: Any,
    *,
    physical_page: int,
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict:
        raise CausalNativeTextEvidenceError("causal native wrapper returned a non-object")
    payload = _canonical_clone(value)
    status = payload.get("status")
    if status not in TERMINAL_STATUSES - {_CONTIGUITY_STATUS}:
        raise CausalNativeTextEvidenceError("causal native wrapper status drifted")
    if payload.get("ocr_fallback_used") is not False:
        raise CausalNativeTextEvidenceError("causal native wrapper used an OCR fallback")
    if payload.get("source_blank_claimed") is not False:
        raise CausalNativeTextEvidenceError("causal native wrapper claimed a blank source")
    common = {
        "status",
        "lines",
        "words",
        "quarantined_spans",
        "ocr_fallback_used",
        "source_blank_claimed",
    }
    if status == "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY":
        expected_fields = common | {"failure_type"}
    else:
        expected_fields = common | {"native_text_quality", "corruption_markers"}
    if set(payload) != expected_fields:
        raise CausalNativeTextEvidenceError("causal native wrapper fields drifted")

    source_words = _validate_source_words(payload["words"], authority=authority)
    _validate_raw_lines(payload["lines"], source_words=source_words, authority=authority)
    quarantined = _validate_quarantined_spans(
        payload["quarantined_spans"],
        physical_page=physical_page,
        authority=authority,
    )
    if status == "CAUSAL_NATIVE_TEXT_READ_COMPLETE":
        if payload["native_text_quality"] != "USABLE_TEXT_LAYER" or not source_words:
            raise CausalNativeTextEvidenceError("complete native result quality drifted")
        _validate_corruption_markers(payload["corruption_markers"])
    elif status == "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY":
        _validate_safe_failure_type(payload["failure_type"], "native visibility")
        if source_words or payload["lines"] or quarantined:
            raise CausalNativeTextEvidenceError("unresolved native visibility exposed page text")
    else:
        if payload["native_text_quality"] not in {
            "NO_TEXT_LAYER",
            "CORRUPT_TEXT_LAYER",
        }:
            raise CausalNativeTextEvidenceError("unresolved native quality drifted")
        _validate_corruption_markers(payload["corruption_markers"])
        if source_words or payload["lines"]:
            raise CausalNativeTextEvidenceError("unresolved native quality exposed accepted text")
    return payload


def _make_projected_line(words: list[dict[str, Any]]) -> dict[str, Any]:
    if not words:
        raise CausalNativeTextEvidenceError("cannot project an empty native line run")
    identity = _line_identity(words[0])
    if any(_line_identity(word) != identity for word in words):
        raise CausalNativeTextEvidenceError("native line run identity drifted")
    return {
        "raw_text": " ".join(word["raw_text"] for word in words),
        "score": None,
        "score_kind": _SCORE_KIND,
        "canonical_bbox_mpt": _line_bbox(words),
        "block_number": identity[0],
        "line_number": identity[1],
        "words": _canonical_clone(words),
    }


def _ordering_receipt(
    *,
    source_words: list[dict[str, Any]],
    runs: list[list[dict[str, Any]]],
    noncontiguous_identities: set[tuple[int, int]],
    ordering_policy_identity: Mapping[str, Any],
    status: str,
) -> dict[str, Any]:
    run_projection = [
        {
            "line_identity_sha256": _canonical_json_sha256(list(_line_identity(run[0]))),
            "word_count": len(run),
            "words_sha256": _canonical_json_sha256(run),
        }
        for run in runs
    ]
    noncontiguous_projection = [
        _canonical_json_sha256(list(identity)) for identity in sorted(noncontiguous_identities)
    ]
    receipt = {
        "format_version": ORDERING_RECEIPT_FORMAT_VERSION,
        "policy": _ORDERING_POLICY,
        "ordering_policy_identity": _canonical_clone(ordering_policy_identity),
        "source_word_order": _SOURCE_WORD_ORDER,
        "line_projection": _LINE_PROJECTION,
        "status": status,
        "source_word_count": len(source_words),
        "line_run_count": len(runs),
        "distinct_line_identity_count": len({_line_identity(word) for word in source_words}),
        "noncontiguous_line_identity_count": len(noncontiguous_identities),
        "source_words_sha256": _canonical_json_sha256(source_words),
        "line_runs_sha256": _canonical_json_sha256(run_projection),
        "noncontiguous_line_identities_sha256": _canonical_json_sha256(noncontiguous_projection),
    }
    return _validate_ordering_receipt(receipt, ordering_policy_identity=ordering_policy_identity)


def _validate_ordering_receipt(
    value: Any,
    *,
    ordering_policy_identity: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _ORDERING_RECEIPT_FIELDS:
        raise CausalNativeTextEvidenceError("native ordering receipt fields drifted")
    receipt = _canonical_clone(value)
    constants = {
        "format_version": ORDERING_RECEIPT_FORMAT_VERSION,
        "policy": _ORDERING_POLICY,
        "source_word_order": _SOURCE_WORD_ORDER,
        "line_projection": _LINE_PROJECTION,
    }
    if any(receipt[key] != expected for key, expected in constants.items()):
        raise CausalNativeTextEvidenceError("native ordering receipt identity drifted")
    if not _same_typed_json(receipt["ordering_policy_identity"], ordering_policy_identity):
        raise CausalNativeTextEvidenceError("native ordering receipt policy binding drifted")
    if receipt["status"] not in {
        _ORDER_ACCEPTED,
        _ORDER_SOURCE_TERMINAL,
        _ORDER_QUARANTINED,
    }:
        raise CausalNativeTextEvidenceError("native ordering receipt status drifted")
    for key in (
        "source_word_count",
        "line_run_count",
        "distinct_line_identity_count",
        "noncontiguous_line_identity_count",
    ):
        _require_nonnegative_integer(receipt[key], f"native ordering receipt {key}")
    for key in (
        "source_words_sha256",
        "line_runs_sha256",
        "noncontiguous_line_identities_sha256",
    ):
        _require_sha256(receipt[key], f"native ordering receipt {key}")
    if receipt["distinct_line_identity_count"] > receipt["line_run_count"]:
        raise CausalNativeTextEvidenceError("native ordering receipt counts drifted")
    if receipt["line_run_count"] > receipt["source_word_count"]:
        raise CausalNativeTextEvidenceError("native ordering receipt run count drifted")
    if receipt["noncontiguous_line_identity_count"] > receipt["distinct_line_identity_count"]:
        raise CausalNativeTextEvidenceError("native ordering receipt quarantine count drifted")
    if receipt["status"] == _ORDER_ACCEPTED and receipt["noncontiguous_line_identity_count"] != 0:
        raise CausalNativeTextEvidenceError("accepted native order has quarantined lines")
    if (
        receipt["status"] == _ORDER_QUARANTINED
        and receipt["noncontiguous_line_identity_count"] == 0
    ):
        raise CausalNativeTextEvidenceError("native order quarantine has no affected line")
    if receipt["status"] == _ORDER_SOURCE_TERMINAL and any(
        receipt[key] != 0
        for key in (
            "source_word_count",
            "line_run_count",
            "distinct_line_identity_count",
            "noncontiguous_line_identity_count",
        )
    ):
        raise CausalNativeTextEvidenceError("upstream terminal ordering receipt is nonempty")
    return receipt


def _project_contiguous_runs(
    source_words: list[dict[str, Any]],
) -> tuple[list[list[dict[str, Any]]], set[tuple[int, int]]]:
    runs: list[list[dict[str, Any]]] = []
    seen: set[tuple[int, int]] = set()
    noncontiguous: set[tuple[int, int]] = set()
    current_identity: tuple[int, int] | None = None
    for source_word in source_words:
        identity = _line_identity(source_word)
        word = _canonical_clone(source_word)
        if identity != current_identity:
            if identity in seen:
                noncontiguous.add(identity)
            seen.add(identity)
            runs.append([word])
            current_identity = identity
        else:
            runs[-1].append(word)
    for run in runs:
        previous_word_number: int | None = None
        for word in run:
            word_number = word["word_number"]
            if previous_word_number is not None and word_number <= previous_word_number:
                raise CausalNativeTextEvidenceError(
                    "native source word order drifted within a contiguous line run"
                )
            previous_word_number = word_number
    return runs, noncontiguous


def _public_payload_from_raw(
    raw_payload: Mapping[str, Any],
    *,
    physical_page: int,
    authority: Mapping[str, Any],
    ordering_policy_identity: Mapping[str, Any],
) -> dict[str, Any]:
    raw = _validate_raw_wrapper_payload(
        raw_payload,
        physical_page=physical_page,
        authority=authority,
    )
    source_words = _canonical_clone(raw["words"])
    runs, noncontiguous = _project_contiguous_runs(source_words)
    if raw["status"] != "CAUSAL_NATIVE_TEXT_READ_COMPLETE":
        receipt_status = _ORDER_SOURCE_TERMINAL
    elif noncontiguous:
        receipt_status = _ORDER_QUARANTINED
    else:
        receipt_status = _ORDER_ACCEPTED
    receipt = _ordering_receipt(
        source_words=source_words,
        runs=runs,
        noncontiguous_identities=noncontiguous,
        ordering_policy_identity=ordering_policy_identity,
        status=receipt_status,
    )

    if raw["status"] == "CAUSAL_NATIVE_TEXT_READ_COMPLETE" and not noncontiguous:
        lines = [_make_projected_line(run) for run in runs]
        flattened = [word for line in lines for word in line["words"]]
        if not _same_typed_json(flattened, source_words):
            raise CausalNativeTextEvidenceError(
                "accepted native line projection drifted from source word order"
            )
        payload = {
            "status": "CAUSAL_NATIVE_TEXT_READ_COMPLETE",
            "failure_type": None,
            "native_text_quality": "USABLE_TEXT_LAYER",
            "corruption_markers": _canonical_clone(raw["corruption_markers"]),
            "lines": lines,
            "words": source_words,
            "quarantined_spans": _canonical_clone(raw["quarantined_spans"]),
            "ordering_receipt": receipt,
            "ocr_fallback_used": False,
            "source_blank_claimed": False,
        }
    elif raw["status"] == "CAUSAL_NATIVE_TEXT_READ_COMPLETE":
        payload = {
            "status": _CONTIGUITY_STATUS,
            "failure_type": _CONTIGUITY_FAILURE,
            "native_text_quality": "USABLE_TEXT_LAYER",
            "corruption_markers": [],
            "lines": [],
            "words": [],
            "quarantined_spans": _canonical_clone(raw["quarantined_spans"]),
            "ordering_receipt": receipt,
            "ocr_fallback_used": False,
            "source_blank_claimed": False,
        }
    elif raw["status"] == "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY":
        payload = {
            "status": raw["status"],
            "failure_type": raw["failure_type"],
            "native_text_quality": None,
            "corruption_markers": [],
            "lines": [],
            "words": [],
            "quarantined_spans": [],
            "ordering_receipt": receipt,
            "ocr_fallback_used": False,
            "source_blank_claimed": False,
        }
    else:
        payload = {
            "status": raw["status"],
            "failure_type": None,
            "native_text_quality": raw["native_text_quality"],
            "corruption_markers": _canonical_clone(raw["corruption_markers"]),
            "lines": [],
            "words": [],
            "quarantined_spans": _canonical_clone(raw["quarantined_spans"]),
            "ordering_receipt": receipt,
            "ocr_fallback_used": False,
            "source_blank_claimed": False,
        }
    return _validate_public_payload(
        payload,
        physical_page=physical_page,
        authority=authority,
        ordering_policy_identity=ordering_policy_identity,
    )


def _validate_public_payload(
    value: Any,
    *,
    physical_page: int,
    authority: Mapping[str, Any],
    ordering_policy_identity: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _PUBLIC_PAYLOAD_FIELDS:
        raise CausalNativeTextEvidenceError("public native payload fields drifted")
    payload = _canonical_clone(value)
    status = payload["status"]
    if status not in TERMINAL_STATUSES:
        raise CausalNativeTextEvidenceError("public native payload status drifted")
    if payload["ocr_fallback_used"] is not False or payload["source_blank_claimed"] is not False:
        raise CausalNativeTextEvidenceError("public native payload safety drifted")
    words = _validate_source_words(payload["words"], authority=authority)
    lines = _validate_projected_lines(payload["lines"], source_words=words, authority=authority)
    quarantined = _validate_quarantined_spans(
        payload["quarantined_spans"],
        physical_page=physical_page,
        authority=authority,
    )
    markers = _validate_corruption_markers(payload["corruption_markers"])
    receipt = _validate_ordering_receipt(
        payload["ordering_receipt"],
        ordering_policy_identity=ordering_policy_identity,
    )
    if status == "CAUSAL_NATIVE_TEXT_READ_COMPLETE":
        if (
            payload["failure_type"] is not None
            or payload["native_text_quality"] != "USABLE_TEXT_LAYER"
            or not words
            or not lines
            or receipt["status"] != _ORDER_ACCEPTED
            or receipt["source_word_count"] != len(words)
            or receipt["line_run_count"] != len(lines)
        ):
            raise CausalNativeTextEvidenceError("complete public native payload drifted")
    elif status == _CONTIGUITY_STATUS:
        if (
            payload["failure_type"] != _CONTIGUITY_FAILURE
            or payload["native_text_quality"] != "USABLE_TEXT_LAYER"
            or markers
            or words
            or lines
            or receipt["status"] != _ORDER_QUARANTINED
        ):
            raise CausalNativeTextEvidenceError("native line-contiguity terminal payload drifted")
    elif status == "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY":
        _validate_safe_failure_type(payload["failure_type"], "public native visibility")
        if (
            payload["native_text_quality"] is not None
            or markers
            or words
            or lines
            or quarantined
            or receipt["status"] != _ORDER_SOURCE_TERMINAL
        ):
            raise CausalNativeTextEvidenceError("unresolved visibility public payload drifted")
    elif (
        payload["failure_type"] is not None
        or payload["native_text_quality"] not in {"NO_TEXT_LAYER", "CORRUPT_TEXT_LAYER"}
        or words
        or lines
        or receipt["status"] != _ORDER_SOURCE_TERMINAL
    ):
        raise CausalNativeTextEvidenceError("unresolved quality public payload drifted")
    return payload


def _validate_projected_lines(
    value: Any,
    *,
    source_words: list[dict[str, Any]],
    authority: Mapping[str, Any],
) -> list[dict[str, Any]]:
    if type(value) is not list:
        raise CausalNativeTextEvidenceError("projected native lines must be an array")
    lines = _canonical_clone(value)
    seen_lines: set[tuple[int, int]] = set()
    flattened: list[dict[str, Any]] = []
    for line in lines:
        if type(line) is not dict or set(line) != _LINE_FIELDS:
            raise CausalNativeTextEvidenceError("projected native line fields drifted")
        if line["score"] is not None or line["score_kind"] != _SCORE_KIND:
            raise CausalNativeTextEvidenceError("projected native line score drifted")
        block_number = _require_nonnegative_integer(
            line["block_number"], "projected native line block_number"
        )
        line_number = _require_nonnegative_integer(
            line["line_number"], "projected native line line_number"
        )
        identity = (block_number, line_number)
        if identity in seen_lines:
            raise CausalNativeTextEvidenceError(
                "projected native line identity reappeared noncontiguously"
            )
        seen_lines.add(identity)
        if type(line["words"]) is not list or not line["words"]:
            raise CausalNativeTextEvidenceError("projected native line has no words")
        line_words = [
            _validate_word(word, authority=authority, label="projected native line word")
            for word in line["words"]
        ]
        if any(_line_identity(word) != identity for word in line_words):
            raise CausalNativeTextEvidenceError("projected native word line identity drifted")
        previous_word_number: int | None = None
        for word in line_words:
            word_number = word["word_number"]
            if previous_word_number is not None and word_number <= previous_word_number:
                raise CausalNativeTextEvidenceError(
                    "projected native word order drifted within a contiguous line run"
                )
            previous_word_number = word_number
        if line["raw_text"] != " ".join(word["raw_text"] for word in line_words):
            raise CausalNativeTextEvidenceError("projected native line text drifted")
        if not _same_typed_json(line["canonical_bbox_mpt"], _line_bbox(line_words)):
            raise CausalNativeTextEvidenceError("projected native line geometry drifted")
        _validate_bbox_in_cropbox(
            line["canonical_bbox_mpt"],
            authority=authority,
            label="projected native line bbox",
        )
        flattened.extend(line_words)
    if not _same_typed_json(flattened, source_words):
        raise CausalNativeTextEvidenceError(
            "projected native lines do not flatten to source word order"
        )
    return lines


def _build_envelopes(
    *,
    request: Mapping[str, Any],
    request_sha256: str,
    source_bytes: bytes,
    document_id: str,
    physical_page: int,
    provider_runtime_ledger: Mapping[str, Any],
    causal_policy_path: Path,
    quality_policy_path: Path,
    native_ordering_policy_identity: Mapping[str, Any],
    full_control_identity_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if type(source_bytes) is not bytes:
        raise CausalNativeTextEvidenceError("authenticated source must be immutable bytes")
    _require_sha256(full_control_identity_sha256, "full execution control identity")
    ordering_path = _ordering_policy_path(causal_policy_path)
    ordering_identity, ordering_bytes_before = _validate_ordering_policy_identity(
        native_ordering_policy_identity,
        ordering_policy_path=ordering_path,
    )
    _load_ordering_policy(ordering_bytes_before)
    (
        provider_ledger,
        causal_policy_bytes,
        quality_policy_bytes,
        causal_policy_identity,
        quality_policy_identity,
    ) = _validate_provider_runtime_ledger(
        provider_runtime_ledger,
        causal_policy_path=causal_policy_path,
        quality_policy_path=quality_policy_path,
    )
    provider_identity = provider_ledger["sha256"]
    request_copy = _validate_request(
        request,
        request_sha256=request_sha256,
        source_bytes=source_bytes,
        document_id=document_id,
        physical_page=physical_page,
        provider_identity_sha256=provider_identity,
    )

    with _authenticated_policy_copies(
        causal_policy_bytes,
        quality_policy_bytes,
    ) as (authenticated_causal_path, authenticated_quality_path):
        try:
            policy = load_causal_native_text_policy(authenticated_causal_path)
        except Exception:
            raise CausalNativeTextEvidenceError(
                "authenticated causal-native policy cannot be loaded"
            ) from None
        try:
            document = fitz.open(stream=source_bytes, filetype="pdf")
        except Exception:
            raise CausalNativeTextEvidenceError("authenticated PDF cannot be opened") from None
        try:
            try:
                if document.page_count < physical_page:
                    raise CausalNativeTextEvidenceError(
                        "authenticated PDF does not contain the requested page"
                    )
                page = document.load_page(physical_page - 1)
                coordinate_authority = _coordinate_authority(page)
                with _deny_network_connections() as network_state:
                    raw_payload = read_causal_native_text_page(
                        page,
                        policy=policy,
                        quality_policy_path=authenticated_quality_path,
                    )
                    if network_state.attempted:
                        raise _NetworkAccessDenied("native evidence network access was attempted")
            except CausalNativeTextEvidenceError:
                raise
            except Exception:
                raise CausalNativeTextEvidenceError(
                    "sealed causal-native wrapper failed operationally"
                ) from None
        finally:
            document.close()

    ordering_bytes_after = _stable_regular_bytes(ordering_path)
    if ordering_bytes_after != ordering_bytes_before:
        raise CausalNativeTextEvidenceError("native ordering policy changed during the page read")
    observed_ordering_identity = {
        "path": ORDERING_POLICY_RECORD_PATH,
        "sha256": sha256(ordering_bytes_after).hexdigest(),
        "size_bytes": len(ordering_bytes_after),
    }
    if not _same_typed_json(observed_ordering_identity, ordering_identity):
        raise CausalNativeTextEvidenceError(
            "native ordering policy identity changed during the page read"
        )
    public_payload = _public_payload_from_raw(
        raw_payload,
        physical_page=physical_page,
        authority=coordinate_authority,
        ordering_policy_identity=ordering_identity,
    )

    source_sha256 = request_copy["source_sha256"]
    source_size_bytes = request_copy["source_size_bytes"]
    safety = _safety_boundary()
    backend = {
        "format_version": BACKEND_FORMAT_VERSION,
        "status": public_payload["status"],
        "claim_boundary": _BACKEND_CLAIM_BOUNDARY,
        "document_id": document_id,
        "source_sha256": source_sha256,
        "source_size_bytes": source_size_bytes,
        "physical_page": physical_page,
        "route": _ROUTE,
        "request_sha256": request_sha256,
        "request": _canonical_clone(request_copy),
        "full_control_identity_sha256": full_control_identity_sha256,
        "provider_identity_sha256": provider_identity,
        "provider_runtime_ledger": _canonical_clone(provider_ledger),
        "causal_native_policy_identity": causal_policy_identity,
        "native_text_quality_policy_identity": quality_policy_identity,
        "ordering_policy_identity": _canonical_clone(ordering_identity),
        "coordinate_authority": _canonical_clone(coordinate_authority),
        "raw_causal_native_wrapper_payload": _canonical_clone(raw_payload),
        "ordering_receipt": _canonical_clone(public_payload["ordering_receipt"]),
        "ocr_fallback_used": False,
        "source_blank_claimed": False,
        "safety": _canonical_clone(safety),
    }
    if set(backend) != _BACKEND_FIELDS:
        raise AssertionError("causal native V2 backend fields are not closed")
    backend_sha256 = _canonical_json_sha256(backend)
    result = {
        "format_version": RESULT_FORMAT_VERSION,
        "status": public_payload["status"],
        "claim_boundary": _RESULT_CLAIM_BOUNDARY,
        "document_id": document_id,
        "source_sha256": source_sha256,
        "source_size_bytes": source_size_bytes,
        "physical_page": physical_page,
        "route": _ROUTE,
        "request_sha256": request_sha256,
        "request": _canonical_clone(request_copy),
        "full_control_identity_sha256": full_control_identity_sha256,
        "provider_identity_sha256": provider_identity,
        "backend_payload_sha256": backend_sha256,
        "ordering_policy_identity": _canonical_clone(ordering_identity),
        "coordinate_authority": _canonical_clone(coordinate_authority),
        "failure_type": public_payload["failure_type"],
        "native_text_quality": public_payload["native_text_quality"],
        "corruption_markers": _canonical_clone(public_payload["corruption_markers"]),
        "lines": _canonical_clone(public_payload["lines"]),
        "words": _canonical_clone(public_payload["words"]),
        "quarantined_spans": _canonical_clone(public_payload["quarantined_spans"]),
        "ordering_receipt": _canonical_clone(public_payload["ordering_receipt"]),
        "metrics": {
            "line_count": len(public_payload["lines"]),
            "word_token_count": len(public_payload["words"]),
            "ghost_quarantined_span_count": len(public_payload["quarantined_spans"]),
            "ordering_quarantined_raw_line_run_count": (
                public_payload["ordering_receipt"]["line_run_count"]
                if public_payload["status"] == _CONTIGUITY_STATUS
                else 0
            ),
            "ordering_quarantined_raw_word_count": (
                public_payload["ordering_receipt"]["source_word_count"]
                if public_payload["status"] == _CONTIGUITY_STATUS
                else 0
            ),
            "noncontiguous_line_identity_count": public_payload["ordering_receipt"][
                "noncontiguous_line_identity_count"
            ],
        },
        "ocr_fallback_used": False,
        "source_blank_claimed": False,
        "safety": _canonical_clone(safety),
    }
    if set(result) != _RESULT_FIELDS:
        raise AssertionError("causal native V2 result fields are not closed")
    if set(result["metrics"]) != _RESULT_METRIC_FIELDS:
        raise AssertionError("causal native V2 result metric fields are not closed")
    _canonical_json_bytes(backend)
    _canonical_json_bytes(result)
    validate_causal_native_text_evidence_v2_envelopes(
        request=request_copy,
        request_sha256=request_sha256,
        document_id=document_id,
        source_sha256=source_sha256,
        source_size_bytes=source_size_bytes,
        physical_page=physical_page,
        provider_runtime_ledger=provider_ledger,
        native_ordering_policy_identity=ordering_identity,
        full_control_identity_sha256=full_control_identity_sha256,
        backend=backend,
        result=result,
    )
    return backend, result


def build_causal_native_text_evidence_v2(
    *,
    request: Mapping[str, Any],
    request_sha256: str,
    source_bytes: bytes,
    document_id: str,
    physical_page: int,
    provider_runtime_ledger: Mapping[str, Any],
    causal_policy_path: Path,
    quality_policy_path: Path,
    native_ordering_policy_identity: Mapping[str, Any],
    full_control_identity_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build one V2 native backend/result pair from authenticated source bytes."""

    return _build_envelopes(
        request=request,
        request_sha256=request_sha256,
        source_bytes=source_bytes,
        document_id=document_id,
        physical_page=physical_page,
        provider_runtime_ledger=provider_runtime_ledger,
        causal_policy_path=causal_policy_path,
        quality_policy_path=quality_policy_path,
        native_ordering_policy_identity=native_ordering_policy_identity,
        full_control_identity_sha256=full_control_identity_sha256,
    )


def _validate_observed_envelopes(
    backend: Any,
    result: Any,
    *,
    physical_page: int,
    native_ordering_policy_identity: Mapping[str, Any],
) -> None:
    _validate_json_tree(backend)
    _validate_json_tree(result)
    if type(backend) is not dict or set(backend) != _BACKEND_FIELDS:
        raise CausalNativeTextEvidenceError("causal native V2 backend fields drifted")
    if type(result) is not dict or set(result) != _RESULT_FIELDS:
        raise CausalNativeTextEvidenceError("causal native V2 result fields drifted")
    if backend["format_version"] != BACKEND_FORMAT_VERSION:
        raise CausalNativeTextEvidenceError("causal native V2 backend format drifted")
    if result["format_version"] != RESULT_FORMAT_VERSION:
        raise CausalNativeTextEvidenceError("causal native V2 result format drifted")
    if (
        backend["claim_boundary"] != _BACKEND_CLAIM_BOUNDARY
        or result["claim_boundary"] != _RESULT_CLAIM_BOUNDARY
    ):
        raise CausalNativeTextEvidenceError("causal native V2 claim boundary drifted")
    if backend["status"] not in TERMINAL_STATUSES or result["status"] != backend["status"]:
        raise CausalNativeTextEvidenceError("causal native V2 status drifted")
    if backend["route"] != _ROUTE or result["route"] != _ROUTE:
        raise CausalNativeTextEvidenceError("causal native V2 route drifted")
    if (
        backend["ocr_fallback_used"] is not False
        or result["ocr_fallback_used"] is not False
        or backend["source_blank_claimed"] is not False
        or result["source_blank_claimed"] is not False
    ):
        raise CausalNativeTextEvidenceError("causal native V2 safety claims drifted")
    if not _same_typed_json(backend["safety"], _safety_boundary()) or not _same_typed_json(
        result["safety"], _safety_boundary()
    ):
        raise CausalNativeTextEvidenceError("causal native V2 semantic boundary drifted")
    expected_ordering_identity = _canonical_clone(dict(native_ordering_policy_identity))
    if set(expected_ordering_identity) != _ORDERING_POLICY_IDENTITY_FIELDS:
        raise CausalNativeTextEvidenceError("expected native ordering identity drifted")
    if not _same_typed_json(
        backend["ordering_policy_identity"], expected_ordering_identity
    ) or not _same_typed_json(result["ordering_policy_identity"], expected_ordering_identity):
        raise CausalNativeTextEvidenceError("causal native V2 ordering binding drifted")
    authority = _validate_coordinate_authority(backend["coordinate_authority"])
    if not _same_typed_json(result["coordinate_authority"], authority):
        raise CausalNativeTextEvidenceError("causal native V2 coordinate binding drifted")
    raw = _validate_raw_wrapper_payload(
        backend["raw_causal_native_wrapper_payload"],
        physical_page=physical_page,
        authority=authority,
    )
    public = _public_payload_from_raw(
        raw,
        physical_page=physical_page,
        authority=authority,
        ordering_policy_identity=expected_ordering_identity,
    )
    if not _same_typed_json(backend["ordering_receipt"], public["ordering_receipt"]):
        raise CausalNativeTextEvidenceError("causal native V2 backend receipt drifted")
    observed_public = _validate_public_payload(
        {key: result[key] for key in _PUBLIC_PAYLOAD_FIELDS},
        physical_page=physical_page,
        authority=authority,
        ordering_policy_identity=expected_ordering_identity,
    )
    if not _same_typed_json(observed_public, public):
        raise CausalNativeTextEvidenceError("causal native V2 result projection drifted")
    expected_metrics = {
        "line_count": len(public["lines"]),
        "word_token_count": len(public["words"]),
        "ghost_quarantined_span_count": len(public["quarantined_spans"]),
        "ordering_quarantined_raw_line_run_count": (
            public["ordering_receipt"]["line_run_count"]
            if public["status"] == _CONTIGUITY_STATUS
            else 0
        ),
        "ordering_quarantined_raw_word_count": (
            public["ordering_receipt"]["source_word_count"]
            if public["status"] == _CONTIGUITY_STATUS
            else 0
        ),
        "noncontiguous_line_identity_count": public["ordering_receipt"][
            "noncontiguous_line_identity_count"
        ],
    }
    if type(result["metrics"]) is not dict or set(result["metrics"]) != _RESULT_METRIC_FIELDS:
        raise CausalNativeTextEvidenceError("causal native V2 result metric fields drifted")
    if not _same_typed_json(result["metrics"], expected_metrics):
        raise CausalNativeTextEvidenceError("causal native V2 result metrics drifted")
    shared_fields = {
        "document_id",
        "source_sha256",
        "source_size_bytes",
        "physical_page",
        "route",
        "request_sha256",
        "request",
        "full_control_identity_sha256",
        "provider_identity_sha256",
        "ordering_policy_identity",
        "coordinate_authority",
        "ordering_receipt",
        "ocr_fallback_used",
        "source_blank_claimed",
        "safety",
    }
    for key in shared_fields:
        if not _same_typed_json(backend[key], result[key]):
            raise CausalNativeTextEvidenceError(f"causal native V2 shared {key} binding drifted")
    if result["backend_payload_sha256"] != _canonical_json_sha256(backend):
        raise CausalNativeTextEvidenceError("causal native V2 backend hash binding drifted")


def validate_causal_native_text_evidence_v2_envelopes(
    *,
    request: Mapping[str, Any],
    request_sha256: str,
    document_id: str,
    source_sha256: str,
    source_size_bytes: int,
    physical_page: int,
    provider_runtime_ledger: Mapping[str, Any],
    native_ordering_policy_identity: Mapping[str, Any],
    full_control_identity_sha256: str,
    backend: Mapping[str, Any],
    result: Mapping[str, Any],
) -> None:
    """Validate a V2 envelope pair without reading source or invoking a provider.

    The caller supplies the identities already authenticated by its enclosing
    control plane.  This boundary closes the entire backend/result projection
    and requires exact typed equality to those expected identities.  It does
    not claim a source replay; use :func:`validate_causal_native_text_evidence_v2_replay`
    when authenticated PDF and live policy bytes are available.
    """

    _require_sha256(full_control_identity_sha256, "expected full execution control identity")
    if not isinstance(native_ordering_policy_identity, Mapping):
        raise CausalNativeTextEvidenceError(
            "expected native ordering policy identity must be an object"
        )
    ordering_identity = _canonical_clone(dict(native_ordering_policy_identity))
    if set(ordering_identity) != _ORDERING_POLICY_IDENTITY_FIELDS:
        raise CausalNativeTextEvidenceError("expected native ordering identity fields drifted")
    if ordering_identity["path"] != ORDERING_POLICY_RECORD_PATH:
        raise CausalNativeTextEvidenceError("expected native ordering policy path drifted")
    _require_sha256(ordering_identity["sha256"], "expected native ordering policy identity")
    _require_positive_integer(
        ordering_identity["size_bytes"], "expected native ordering policy size"
    )
    provider_ledger, config_records = _validate_expected_provider_runtime_ledger(
        provider_runtime_ledger
    )
    expected_request = _validate_expected_request(
        request,
        request_sha256=request_sha256,
        document_id=document_id,
        source_sha256=source_sha256,
        source_size_bytes=source_size_bytes,
        physical_page=physical_page,
        provider_identity_sha256=provider_ledger["sha256"],
    )
    _validate_observed_envelopes(
        backend,
        result,
        physical_page=physical_page,
        native_ordering_policy_identity=ordering_identity,
    )
    expected_top_level = {
        "document_id": document_id,
        "source_sha256": source_sha256,
        "source_size_bytes": source_size_bytes,
        "physical_page": physical_page,
        "route": _ROUTE,
        "request_sha256": request_sha256,
        "request": expected_request,
        "full_control_identity_sha256": full_control_identity_sha256,
        "provider_identity_sha256": provider_ledger["sha256"],
        "ordering_policy_identity": ordering_identity,
    }
    for envelope_name, envelope in (("backend", backend), ("result", result)):
        for key, expected in expected_top_level.items():
            if not _same_typed_json(envelope[key], expected):
                raise CausalNativeTextEvidenceError(
                    f"causal native V2 {envelope_name} expected {key} drifted"
                )
    if not _same_typed_json(backend["provider_runtime_ledger"], provider_ledger):
        raise CausalNativeTextEvidenceError("causal native V2 expected provider ledger drifted")
    if not _same_typed_json(
        backend["causal_native_policy_identity"],
        config_records[_CAUSAL_POLICY_RECORD_PATH],
    ):
        raise CausalNativeTextEvidenceError("causal native V2 causal policy identity drifted")
    if not _same_typed_json(
        backend["native_text_quality_policy_identity"],
        config_records[_QUALITY_POLICY_RECORD_PATH],
    ):
        raise CausalNativeTextEvidenceError("causal native V2 quality policy identity drifted")


def validate_causal_native_text_evidence_v2_replay(
    *,
    request: Mapping[str, Any],
    request_sha256: str,
    source_bytes: bytes,
    document_id: str,
    physical_page: int,
    provider_runtime_ledger: Mapping[str, Any],
    causal_policy_path: Path,
    quality_policy_path: Path,
    native_ordering_policy_identity: Mapping[str, Any],
    full_control_identity_sha256: str,
    backend: Mapping[str, Any],
    result: Mapping[str, Any],
) -> None:
    """Rebuild and byte/type-compare one authenticated V2 evidence pair."""

    if type(source_bytes) is not bytes:
        raise CausalNativeTextEvidenceError("authenticated source must be immutable bytes")
    ordering_path = _ordering_policy_path(causal_policy_path)
    _, ordering_bytes_before = _validate_ordering_policy_identity(
        native_ordering_policy_identity,
        ordering_policy_path=ordering_path,
    )
    _load_ordering_policy(ordering_bytes_before)
    validate_causal_native_text_evidence_v2_envelopes(
        request=request,
        request_sha256=request_sha256,
        document_id=document_id,
        source_sha256=sha256(source_bytes).hexdigest(),
        source_size_bytes=len(source_bytes),
        physical_page=physical_page,
        provider_runtime_ledger=provider_runtime_ledger,
        native_ordering_policy_identity=native_ordering_policy_identity,
        full_control_identity_sha256=full_control_identity_sha256,
        backend=backend,
        result=result,
    )
    expected_backend, expected_result = _build_envelopes(
        request=request,
        request_sha256=request_sha256,
        source_bytes=source_bytes,
        document_id=document_id,
        physical_page=physical_page,
        provider_runtime_ledger=provider_runtime_ledger,
        causal_policy_path=causal_policy_path,
        quality_policy_path=quality_policy_path,
        native_ordering_policy_identity=native_ordering_policy_identity,
        full_control_identity_sha256=full_control_identity_sha256,
    )
    ordering_bytes_after = _stable_regular_bytes(ordering_path)
    if ordering_bytes_after != ordering_bytes_before:
        raise CausalNativeTextEvidenceError("native ordering policy changed during replay")
    if (
        not _same_typed_json(backend, expected_backend)
        or not _same_typed_json(result, expected_result)
        or _canonical_json_bytes(backend) != _canonical_json_bytes(expected_backend)
        or _canonical_json_bytes(result) != _canonical_json_bytes(expected_result)
    ):
        raise CausalNativeTextEvidenceError("causal native V2 evidence replay drifted")
