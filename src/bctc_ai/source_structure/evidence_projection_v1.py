"""Project authenticated full-reader results into a neutral source envelope.

The caller is responsible for authenticating the supplied full-reader objects.
This module performs a closed, deterministic projection and cross-binds the
objects it consumes.  It never discovers files, traverses a run directory, or
requires a final corpus aggregate.
"""

from __future__ import annotations

import re
from fractions import Fraction
from hashlib import sha256
from math import gcd, isfinite
from statistics import fmean
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    NEUTRAL_PAGE_CLAIM_BOUNDARY,
    NEUTRAL_PAGE_FORMAT_VERSION,
    PROJECTION_RECEIPT_FORMAT_VERSION,
    SOURCE_STRUCTURE_SAFETY_V1,
    AtomAuthority,
    AtomKind,
    SourceStructureContractError,
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    make_source_object_id_v1,
    same_typed_json_v1,
    validate_neutral_page_envelope_v1,
)

__all__ = [
    "LINE_SUPPLEMENT_CLAIM_BOUNDARY",
    "LINE_SUPPLEMENT_FORMAT_VERSION",
    "SourceEvidenceProjectionError",
    "project_authenticated_page_v1",
    "validate_line_only_supplement_v1",
]


class SourceEvidenceProjectionError(SourceStructureContractError):
    """Authenticated inputs cannot be projected without weakening evidence."""


LINE_SUPPLEMENT_FORMAT_VERSION = "BANK_CORPUS_WAVE_1_ROLE_B_LINE_ONLY_PAGE_EVIDENCE_V1"
LINE_SUPPLEMENT_CLAIM_BOUNDARY = (
    "AUTHENTICATED_PPOCRV6_LINE_TEXT_SCORE_AND_LINE_GEOMETRY_ONLY_FROM_"
    "TERMINAL_WORD_BOX_GEOMETRY_PAGE"
)

_OCR_ROUTE = "DOMINANT_RASTER_OCR"
_NATIVE_ROUTE = "CAUSAL_NATIVE_TEXT"
_OCR_COMPLETE = "OCR_WORD_BOX_READ_COMPLETE"
_OCR_TERMINAL = "UNRESOLVED_OCR_WORD_BOX_GEOMETRY"
_NATIVE_COMPLETE = "CAUSAL_NATIVE_TEXT_READ_COMPLETE"
_NATIVE_TERMINAL = frozenset(
    {"UNRESOLVED_CAUSAL_NATIVE_VISIBILITY", "UNRESOLVED_NATIVE_TEXT_QUALITY"}
)
# This adapter is deliberately frozen to the current native RESULT_V1 object.
# A future full-reader V3/V2 native result is unsupported until its own exact
# format, fields, page bounds, ordering receipt, and producer identities freeze.
_ALL_TERMINAL = frozenset({_OCR_TERMINAL, *_NATIVE_TERMINAL})

_REQUEST_FIELDS = {
    "format_version",
    "git_commit",
    "implementation_ledger_sha256",
    "input_ledger_sha256",
    "selection_receipt_sha256",
    "sentinel_sha256",
    "route_plan_sha256",
    "pre_ocr_feature_fingerprint_sha256",
    "source_sha256",
    "source_size_bytes",
    "physical_page",
    "route",
    "provider_identity_sha256",
    "render_runtime_identity_sha256",
    "render_specification",
    "bank_identity_used",
    "filename_used",
    "role_a_used",
    "schema_used",
    "historical_values_used",
}
_RENDER_SPECIFICATION_FIELDS = {
    "dpi",
    "colorspace",
    "alpha",
    "annotations",
    "source",
}

_PAGE_RECORD_FIELDS = {
    "format_version",
    "request_ordinal",
    "document_id",
    "source_sha256",
    "source_size_bytes",
    "physical_page",
    "route",
    "request_sha256",
    "request",
    "status",
    "origin",
    "render_ref",
    "backend_payload_ref",
    "result_ref",
    "line_count",
    "word_token_count",
    "unresolved",
    "quarantined_span_count",
    "word_box_correction_count",
    "word_box_corrected_edge_count",
    "statement_classification_count",
    "table_classification_count",
    "row_reconstruction_count",
    "cell_interpretation_count",
    "absence_declaration_count",
}
_ZERO_INTERPRETATION_FIELDS = {
    "statement_classification_count",
    "table_classification_count",
    "row_reconstruction_count",
    "cell_interpretation_count",
    "absence_declaration_count",
}
_OBJECT_REF_FIELDS = {"path", "sha256", "size_bytes"}
_OCR_RESULT_V2_FIELDS = {
    "format_version",
    "status",
    "claim_boundary",
    "request_sha256",
    "request",
    "source_sha256",
    "source_size_bytes",
    "physical_page",
    "route",
    "provider_identity_sha256",
    "render_runtime_identity_sha256",
    "input_render_ref",
    "backend_payload_ref",
    "word_box_normalization_ledger",
    "coordinate_authority",
    "lines",
    "words",
    "metrics",
    "source_blank_claimed",
    "safety",
}
_OCR_RESULT_V3_FIELDS = {
    "format_version",
    "status",
    "claim_boundary",
    "request_sha256",
    "request",
    "source_sha256",
    "source_size_bytes",
    "physical_page",
    "route",
    "provider_identity_sha256",
    "render_runtime_identity_sha256",
    "input_render_ref",
    "backend_payload_ref",
    "normalization_failure",
    "coordinate_authority",
    "lines",
    "words",
    "metrics",
    "ocr_fallback_used",
    "source_blank_claimed",
    "safety",
}
_NATIVE_RESULT_FIELDS = {
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
    "coordinate_authority",
    "failure_type",
    "native_text_quality",
    "corruption_markers",
    "lines",
    "words",
    "quarantined_spans",
    "metrics",
    "ocr_fallback_used",
    "source_blank_claimed",
    "safety",
}
_OCR_LINE_FIELDS = {
    "raw_text",
    "score",
    "score_kind",
    "raw_pixel_bbox",
    "raw_pixel_polygon",
    "canonical_bbox_mpt",
    "canonical_polygon_mpt",
    "words",
}
_OCR_WORD_FIELDS = {
    "raw_text",
    "score",
    "score_kind",
    "normalized_pixel_bbox",
    "canonical_bbox_mpt",
    "canonical_polygon_mpt",
}
_NATIVE_LINE_FIELDS = {
    "raw_text",
    "score",
    "score_kind",
    "canonical_bbox_mpt",
    "block_number",
    "line_number",
    "words",
}
_NATIVE_WORD_FIELDS = {
    "raw_text",
    "score",
    "score_kind",
    "canonical_bbox_mpt",
    "block_number",
    "line_number",
    "word_number",
}
_QUARANTINE_FIELDS = {
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
_OCR_AUTHORITY_FIELDS = {
    "matrix_convention",
    "pixel_coordinate_system",
    "displayed_coordinate_system",
    "canonical_coordinate_system",
    "canonical_origin",
    "pixel_dimensions",
    "displayed_dimensions_mpt",
    "unrotated_dimensions_mpt",
    "pdf_rotation_degrees",
    "pixel_to_displayed_mpt",
    "displayed_mpt_to_unrotated_mpt",
    "pixel_to_unrotated_mpt",
    "unrotated_mpt_to_pixel",
}
_NATIVE_AUTHORITY = {
    "canonical_coordinate_system": "UNROTATED_PDF_MILLI_POINTS_TOP_LEFT",
    "coordinate_unit": "MILLI_POINT",
    "geometry_source": "PYMUPDF_NATIVE_TEXT_WORD_GEOMETRY",
    "pdf_rotation_applied_to_coordinates": False,
}
_SUPPLEMENT_FIELDS = {
    "format_version",
    "supplemental_disposition",
    "claim_boundary",
    "control_identity_sha256",
    "upstream",
    "coordinate_authority",
    "lines",
    "words",
    "quarantine",
    "metrics",
    "safety",
}
_SUPPLEMENT_LINE_FIELDS = {
    "format_version",
    "line_index",
    "text",
    "score",
    "pixel_rec_box",
    "pixel_rec_polygon",
    "canonical_rec_box_mpt",
    "canonical_rec_polygon_mpt",
}
_SUPPLEMENT_UPSTREAM_FIELDS = {
    "aggregate_identity_sha256",
    "status",
    "status_preserved",
    "normalization_failure_reason",
    "request_sha256",
    "request_ordinal",
    "document_id",
    "physical_page",
    "source_sha256",
    "backend_payload_ref",
    "result_ref",
    "normalization_failure",
}
_SUPPLEMENT_QUARANTINE_FIELDS = {
    "format_version",
    "status",
    "reason",
    "ordered_subdivision_counts_by_line",
    "total_subdivision_count",
    "word_axes_sha256",
    "raw_provider_payload_sha256",
    "raw_backend_payload_ref",
    "word_text_exposed",
    "word_geometry_exposed",
    "accepted_word_count",
}
_SUPPLEMENT_SAFETY = {
    "page_read_complete_claimed": False,
    "ocr_complete_claimed": False,
    "word_geometry_accepted": False,
    "word_tokens_exposed": False,
    "blank_claimed": False,
    "absence_claimed": False,
    "statement_classification_attempted": False,
    "table_classification_attempted": False,
    "row_reconstruction_attempted": False,
    "cell_interpretation_attempted": False,
    "axis_interpretation_attempted": False,
    "schema_used": False,
    "mapping_used": False,
    "role_a_used": False,
    "historical_values_used": False,
    "bank_registry_metadata_used": False,
    "filename_metadata_used": False,
    "source_path_metadata_used": False,
    "new_ocr_inference_used": False,
    "network_used": False,
    "native_ocr_fallback_used": False,
}
_SUPPLEMENT_ACCEPTED = "LINE_ONLY_EVIDENCE_AVAILABLE_FROM_TERMINAL_WORD_BOX_GEOMETRY"
_SUPPLEMENT_REJECTED = "NO_LINE_ONLY_EVIDENCE_AVAILABLE_NO_NONEMPTY_VALID_LINE_TEXT"
_UPSTREAM_FALSE_FLAGS = {
    "bank_identity_used",
    "filename_used",
    "role_a_used",
    "schema_used",
    "historical_values_used",
}
_UPSTREAM_SAFETY = {
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
}
_OCR_NORMALIZATION_FAILURE_FIELDS = {
    "format_version",
    "status",
    "reason",
    "policy_sha256",
    "control_identity_sha256",
    "normalization_producer_implementation_ledger_sha256",
    "pixel_dimensions",
    "raw_payload_sha256",
}
_OCR_NORMALIZATION_LEDGER_FIELDS = {
    "format_version",
    "status",
    "rule_id",
    "maximum_per_edge_overshoot_pixels",
    "policy_sha256",
    "control_identity_sha256",
    "normalization_producer_implementation_ledger_sha256",
    "pixel_dimensions",
    "raw_payload_sha256",
    "normalized_payload_sha256",
    "correction_count",
    "corrected_edge_count",
    "corrections",
}
_OCR_CORRECTION_FIELDS = {
    "json_path",
    "line_index",
    "word_index",
    "raw_box",
    "normalized_box",
    "per_edge_clip_pixels",
    "validated_line_rec_box",
}
_OCR_CLIP_FIELDS = {"left", "top", "right", "bottom"}
_NATIVE_VISIBILITY_FAILURE_TYPES = frozenset(
    {"CausalNativeTextError", "RuntimeError", "ValueError"}
)


def _error(message: str) -> SourceEvidenceProjectionError:
    return SourceEvidenceProjectionError(message)


def _exact_dict(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise _error(f"{label} fields drifted")
    return value


def _sha(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise _error(f"{label} is not a lowercase SHA-256")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise _error(f"{label} must be a nonnegative integer")
    return value


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} must be a positive integer")
    return value


def _finite_number(value: Any, label: str) -> int | float:
    if type(value) not in {int, float} or not isfinite(value):
        raise _error(f"{label} must be a finite non-boolean number")
    return value


def _bbox(
    value: Any,
    label: str,
    *,
    integer: bool,
    positive_area: bool = True,
) -> list[int] | list[int | float]:
    allowed = {int} if integer else {int, float}
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) not in allowed or not isfinite(item) for item in value)
    ):
        raise _error(f"{label} must contain four finite coordinates")
    if (positive_area and (value[0] >= value[2] or value[1] >= value[3])) or (
        not positive_area and (value[0] > value[2] or value[1] > value[3])
    ):
        raise _error(f"{label} must have positive area")
    return value


def _polygon(
    value: Any,
    label: str,
    *,
    integer: bool,
) -> list[list[int]] | list[list[int | float]]:
    allowed = {int} if integer else {int, float}
    if type(value) is not list or len(value) < 4:
        raise _error(f"{label} must contain at least four points")
    for point in value:
        if (
            type(point) is not list
            or len(point) != 2
            or any(type(item) not in allowed or not isfinite(item) for item in point)
        ):
            raise _error(f"{label} points drifted")
    area_twice = abs(
        sum(
            value[index][0] * value[(index + 1) % len(value)][1]
            - value[(index + 1) % len(value)][0] * value[index][1]
            for index in range(len(value))
        )
    )
    if area_twice == 0:
        raise _error(f"{label} is degenerate")
    return value


def _canonical_bbox(points: list[list[int]]) -> list[int]:
    return [
        min(point[0] for point in points),
        min(point[1] for point in points),
        max(point[0] for point in points),
        max(point[1] for point in points),
    ]


def _validate_object_ref(value: Any, *, suffix: str, label: str) -> dict[str, Any]:
    reference = _exact_dict(value, _OBJECT_REF_FIELDS, label)
    digest = _sha(reference["sha256"], f"{label} identity")
    _positive_int(reference["size_bytes"], f"{label} size")
    expected = f"objects/sha256/{digest[:2]}/{digest}{suffix}"
    if reference["path"] != expected:
        raise _error(f"{label} content-addressed locator drifted")
    return reference


def _neutral_ref(value: dict[str, Any], *, kind: str, media_type: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "sha256": value["sha256"],
        "size_bytes": value["size_bytes"],
        "media_type": media_type,
        "upstream_reference_sha256": canonical_json_sha256_v1(value),
    }


def _validate_request(record: dict[str, Any], result: dict[str, Any]) -> None:
    request = _exact_dict(record["request"], _REQUEST_FIELDS, "authenticated request")
    if not same_typed_json_v1(request, result["request"]):
        raise _error("authenticated request binding drifted")
    if request["format_version"] != "BANK_CORPUS_WAVE_1_PAGE_READ_REQUEST_V1":
        raise _error("authenticated request format drifted")
    if canonical_json_sha256_v1(request) != record["request_sha256"]:
        raise _error("authenticated request digest drifted")
    if any(request[field] is not False for field in _UPSTREAM_FALSE_FLAGS):
        raise _error("authenticated request used forbidden identity/reference metadata")
    if (
        type(request["git_commit"]) is not str
        or re.fullmatch(r"[0-9a-f]{40}", request["git_commit"]) is None
    ):
        raise _error("authenticated request Git commit drifted")
    for field in (
        "implementation_ledger_sha256",
        "input_ledger_sha256",
        "selection_receipt_sha256",
        "sentinel_sha256",
        "route_plan_sha256",
        "pre_ocr_feature_fingerprint_sha256",
        "source_sha256",
        "provider_identity_sha256",
    ):
        _sha(request[field], f"authenticated request {field}")
    _positive_int(request["source_size_bytes"], "authenticated request source size")
    _positive_int(request["physical_page"], "authenticated request physical page")
    for field in ("source_sha256", "source_size_bytes", "physical_page", "route"):
        if not same_typed_json_v1(request[field], record[field]):
            raise _error(f"authenticated request {field} drifted")
    if request["route"] == _OCR_ROUTE:
        _sha(
            request["render_runtime_identity_sha256"],
            "authenticated request render runtime identity",
        )
        render = _exact_dict(
            request["render_specification"],
            _RENDER_SPECIFICATION_FIELDS,
            "authenticated request render specification",
        )
        if (
            type(render["dpi"]) is not int
            or render["dpi"] not in {200, 300}
            or render["colorspace"] != "RGB"
            or render["alpha"] is not False
            or render["annotations"] != "INCLUDED"
            or render["source"] != "FULL_COMPOSITED_DISPLAYED_PDF_PAGE"
        ):
            raise _error("authenticated request OCR render specification drifted")
    elif request["route"] == _NATIVE_ROUTE:
        if (
            request["render_runtime_identity_sha256"] is not None
            or request["render_specification"] is not None
        ):
            raise _error("authenticated native request unexpectedly selected a render")
    else:
        raise _error("authenticated request route drifted")


def _validate_page_record(value: Any) -> dict[str, Any]:
    record = _exact_dict(value, _PAGE_RECORD_FIELDS, "authenticated page record")
    if record["format_version"] != "BANK_CORPUS_WAVE_1_ROLE_B_FULL_PAGE_RECORD_V1":
        raise _error("authenticated page record format drifted")
    _positive_int(record["request_ordinal"], "request ordinal")
    source_sha = _sha(record["source_sha256"], "source identity")
    if record["document_id"] != f"sha256:{source_sha}":
        raise _error("authenticated document identity is not source-content-bound")
    _positive_int(record["source_size_bytes"], "source size")
    _positive_int(record["physical_page"], "physical page")
    _sha(record["request_sha256"], "request identity")
    for field in (
        "line_count",
        "word_token_count",
        "quarantined_span_count",
        "word_box_correction_count",
        "word_box_corrected_edge_count",
        *_ZERO_INTERPRETATION_FIELDS,
    ):
        _nonnegative_int(record[field], f"page record {field}")
    if any(record[field] != 0 for field in _ZERO_INTERPRETATION_FIELDS):
        raise _error("authenticated reader record crossed its semantic claim boundary")
    if type(record["unresolved"]) is not bool:
        raise _error("authenticated page unresolved flag drifted")
    _validate_object_ref(record["backend_payload_ref"], suffix=".json", label="backend ref")
    _validate_object_ref(record["result_ref"], suffix=".json", label="result ref")
    if record["route"] == _OCR_ROUTE:
        _validate_object_ref(record["render_ref"], suffix=".png", label="render ref")
        if record["status"] not in {_OCR_COMPLETE, _OCR_TERMINAL}:
            raise _error("OCR page record status drifted")
        if (
            record["origin"]
            not in {
                "AUTHENTICATED_SUCCESSFUL_SENTINEL_BYTE_COPY",
                "PINNED_PPOCRV6_FULL_READER",
            }
            or record["quarantined_span_count"] != 0
        ):
            raise _error("OCR page record origin/quarantine accounting drifted")
        if record["status"] == _OCR_TERMINAL and record["origin"] != "PINNED_PPOCRV6_FULL_READER":
            raise _error("terminal OCR page record origin drifted")
        if record["status"] == _OCR_TERMINAL and any(
            record[field] != 0
            for field in (
                "line_count",
                "word_token_count",
                "word_box_correction_count",
                "word_box_corrected_edge_count",
            )
        ):
            raise _error("terminal OCR page record exposed normalized geometry")
    elif record["route"] == _NATIVE_ROUTE:
        if record["render_ref"] is not None:
            raise _error("native page record unexpectedly has a render")
        if record["status"] not in {_NATIVE_COMPLETE, *_NATIVE_TERMINAL}:
            raise _error("native page record status drifted")
        if (
            record["origin"] != "SEALED_CAUSAL_NATIVE_TEXT_GATE"
            or record["word_box_correction_count"] != 0
            or record["word_box_corrected_edge_count"] != 0
        ):
            raise _error("native page record origin/correction accounting drifted")
    else:
        raise _error("authenticated page route drifted")
    if record["unresolved"] != (record["status"] in _ALL_TERMINAL):
        raise _error("authenticated page terminal accounting drifted")
    return record


def _fraction(value: Any, label: str) -> Fraction:
    item = _exact_dict(value, {"numerator", "denominator"}, label)
    numerator = item["numerator"]
    denominator = item["denominator"]
    if type(numerator) is not int or type(denominator) is not int or denominator <= 0:
        raise _error(f"{label} rational coefficient drifted")
    if gcd(abs(numerator), denominator) != 1:
        raise _error(f"{label} rational coefficient is not reduced")
    return Fraction(numerator, denominator)


def _matrix(value: Any, label: str) -> tuple[tuple[Fraction, ...], ...]:
    if (
        type(value) is not list
        or len(value) != 3
        or any(type(row) is not list or len(row) != 3 for row in value)
    ):
        raise _error(f"{label} matrix shape drifted")
    return tuple(
        tuple(
            _fraction(item, f"{label}[{row_index}][{column_index}]")
            for column_index, item in enumerate(row)
        )
        for row_index, row in enumerate(value)
    )


def _multiply(
    left: tuple[tuple[Fraction, ...], ...],
    right: tuple[tuple[Fraction, ...], ...],
) -> tuple[tuple[Fraction, ...], ...]:
    return tuple(
        tuple(
            sum((left[row][k] * right[k][column] for k in range(3)), Fraction())
            for column in range(3)
        )
        for row in range(3)
    )


def _inverse_affine(
    matrix: tuple[tuple[Fraction, ...], ...],
) -> tuple[tuple[Fraction, ...], ...]:
    a, c, e = matrix[0]
    b, d, f = matrix[1]
    if matrix[2] != (Fraction(0), Fraction(0), Fraction(1)):
        raise _error("coordinate matrix is not affine")
    determinant = a * d - b * c
    if determinant == 0:
        raise _error("coordinate matrix is singular")
    return (
        (d / determinant, -c / determinant, (c * f - d * e) / determinant),
        (-b / determinant, a / determinant, (b * e - a * f) / determinant),
        (Fraction(0), Fraction(0), Fraction(1)),
    )


def _validate_ocr_coordinate_authority(value: Any) -> dict[str, Any]:
    authority = _exact_dict(value, _OCR_AUTHORITY_FIELDS, "OCR coordinate authority")
    expected_strings = {
        "matrix_convention": "COLUMN_VECTOR_3X3_RATIONAL",
        "pixel_coordinate_system": "DISPLAYED_PAGE_RASTER_PIXELS_TOP_LEFT",
        "displayed_coordinate_system": "DISPLAYED_PDF_MILLI_POINTS_TOP_LEFT",
        "canonical_coordinate_system": "UNROTATED_PDF_MILLI_POINTS_TOP_LEFT",
        "canonical_origin": "UNROTATED_CROP_BOX_TOP_LEFT_RELATIVE",
    }
    if any(authority[key] != expected for key, expected in expected_strings.items()):
        raise _error("OCR coordinate system semantics drifted")
    dimensions: dict[str, tuple[int, int]] = {}
    for field in (
        "pixel_dimensions",
        "displayed_dimensions_mpt",
        "unrotated_dimensions_mpt",
    ):
        item = authority[field]
        if type(item) is not list or len(item) != 2:
            raise _error(f"OCR {field} drifted")
        dimensions[field] = (
            _positive_int(item[0], f"OCR {field} width"),
            _positive_int(item[1], f"OCR {field} height"),
        )
    rotation = authority["pdf_rotation_degrees"]
    if type(rotation) is not int or rotation not in {0, 90, 180, 270}:
        raise _error("OCR PDF rotation drifted")
    pixel_width, pixel_height = dimensions["pixel_dimensions"]
    displayed_width, displayed_height = dimensions["displayed_dimensions_mpt"]
    unrotated_width, unrotated_height = dimensions["unrotated_dimensions_mpt"]
    if rotation in {0, 180}:
        expected_displayed = (unrotated_width, unrotated_height)
    else:
        expected_displayed = (unrotated_height, unrotated_width)
    if (displayed_width, displayed_height) != expected_displayed:
        raise _error("OCR displayed/unrotated dimensions disagree with rotation")
    pixel_to_displayed = (
        (Fraction(displayed_width, pixel_width), Fraction(0), Fraction(0)),
        (Fraction(0), Fraction(displayed_height, pixel_height), Fraction(0)),
        (Fraction(0), Fraction(0), Fraction(1)),
    )
    if rotation == 0:
        displayed_to_unrotated = (
            (Fraction(1), Fraction(0), Fraction(0)),
            (Fraction(0), Fraction(1), Fraction(0)),
            (Fraction(0), Fraction(0), Fraction(1)),
        )
    elif rotation == 90:
        displayed_to_unrotated = (
            (Fraction(0), Fraction(1), Fraction(0)),
            (Fraction(-1), Fraction(0), Fraction(unrotated_height)),
            (Fraction(0), Fraction(0), Fraction(1)),
        )
    elif rotation == 180:
        displayed_to_unrotated = (
            (Fraction(-1), Fraction(0), Fraction(unrotated_width)),
            (Fraction(0), Fraction(-1), Fraction(unrotated_height)),
            (Fraction(0), Fraction(0), Fraction(1)),
        )
    else:
        displayed_to_unrotated = (
            (Fraction(0), Fraction(-1), Fraction(unrotated_width)),
            (Fraction(1), Fraction(0), Fraction(0)),
            (Fraction(0), Fraction(0), Fraction(1)),
        )
    observed_pixel_to_displayed = _matrix(authority["pixel_to_displayed_mpt"], "pixel-to-displayed")
    observed_displayed_to_unrotated = _matrix(
        authority["displayed_mpt_to_unrotated_mpt"], "displayed-to-unrotated"
    )
    observed_pixel_to_unrotated = _matrix(authority["pixel_to_unrotated_mpt"], "pixel-to-unrotated")
    observed_unrotated_to_pixel = _matrix(authority["unrotated_mpt_to_pixel"], "unrotated-to-pixel")
    expected_pixel_to_unrotated = _multiply(displayed_to_unrotated, pixel_to_displayed)
    if (
        observed_pixel_to_displayed != pixel_to_displayed
        or observed_displayed_to_unrotated != displayed_to_unrotated
        or observed_pixel_to_unrotated != expected_pixel_to_unrotated
        or observed_unrotated_to_pixel != _inverse_affine(expected_pixel_to_unrotated)
    ):
        raise _error("OCR exact coordinate transform drifted")
    return authority


def _round_fraction_half_away(value: Fraction) -> int:
    sign = -1 if value < 0 else 1
    absolute = abs(value)
    quotient, remainder = divmod(absolute.numerator, absolute.denominator)
    return sign * (quotient + (2 * remainder >= absolute.denominator))


def _transform_pixel_polygon(
    polygon: list[list[int | float]], authority: dict[str, Any]
) -> list[list[int]]:
    matrix = _matrix(authority["pixel_to_unrotated_mpt"], "pixel-to-unrotated")
    transformed = []
    for x, y in polygon:
        point_x = Fraction(str(x))
        point_y = Fraction(str(y))
        transformed.append(
            [
                _round_fraction_half_away(
                    matrix[0][0] * point_x + matrix[0][1] * point_y + matrix[0][2]
                ),
                _round_fraction_half_away(
                    matrix[1][0] * point_x + matrix[1][1] * point_y + matrix[1][2]
                ),
            ]
        )
    return transformed


def _validate_ocr_geometry(
    item: dict[str, Any], *, authority: dict[str, Any], label: str, word: bool
) -> None:
    pixel_bbox_field = "normalized_pixel_bbox" if word else "raw_pixel_bbox"
    raw_bbox = _bbox(item[pixel_bbox_field], f"{label} pixel bbox", integer=False)
    canonical_bbox = _bbox(item["canonical_bbox_mpt"], f"{label} canonical bbox", integer=True)
    canonical_polygon = _polygon(
        item["canonical_polygon_mpt"], f"{label} canonical polygon", integer=True
    )
    if word:
        raw_polygon: list[list[int | float]] = [
            [raw_bbox[0], raw_bbox[1]],
            [raw_bbox[2], raw_bbox[1]],
            [raw_bbox[2], raw_bbox[3]],
            [raw_bbox[0], raw_bbox[3]],
        ]
    else:
        raw_polygon = _polygon(item["raw_pixel_polygon"], f"{label} raw polygon", integer=False)
    pixel_width, pixel_height = authority["pixel_dimensions"]
    if not (
        0 <= raw_bbox[0] < raw_bbox[2] <= pixel_width
        and 0 <= raw_bbox[1] < raw_bbox[3] <= pixel_height
    ) or any(
        not 0 <= point[0] <= pixel_width or not 0 <= point[1] <= pixel_height
        for point in raw_polygon
    ):
        raise _error(f"{label} pixel geometry lies outside the rendered page")
    expected_polygon = _transform_pixel_polygon(raw_polygon, authority)
    if not same_typed_json_v1(canonical_polygon, expected_polygon):
        raise _error(f"{label} canonical transform drifted")
    if canonical_bbox != _canonical_bbox(canonical_polygon):
        raise _error(f"{label} canonical bbox drifted")
    unrotated_width, unrotated_height = authority["unrotated_dimensions_mpt"]
    if not (
        0 <= canonical_bbox[0] < canonical_bbox[2] <= unrotated_width
        and 0 <= canonical_bbox[1] < canonical_bbox[3] <= unrotated_height
    ) or any(
        not 0 <= point[0] <= unrotated_width or not 0 <= point[1] <= unrotated_height
        for point in canonical_polygon
    ):
        raise _error(f"{label} canonical geometry lies outside the unrotated page")


def _validate_text(value: Any, label: str, *, nonempty: bool) -> str:
    if type(value) is not str or (nonempty and not value):
        raise _error(f"{label} must be source text with the required emptiness semantics")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise _error(f"{label} contains invalid Unicode") from error
    return value


def _validate_ocr_lines_words(
    lines: Any,
    words: Any,
    *,
    authority: dict[str, Any],
) -> None:
    if type(lines) is not list or type(words) is not list:
        raise _error("OCR line/word axes drifted")
    flattened: list[dict[str, Any]] = []
    for line_index, line in enumerate(lines):
        item = _exact_dict(line, _OCR_LINE_FIELDS, f"OCR line {line_index}")
        _validate_text(item["raw_text"], f"OCR line {line_index} text", nonempty=False)
        if (
            type(item["score"]) is not float
            or not isfinite(item["score"])
            or not 0.0 <= item["score"] <= 1.0
            or item["score_kind"] != "PP_OCRV6_LINE_RECOGNITION_SCORE"
        ):
            raise _error(f"OCR line {line_index} score semantics drifted")
        _validate_ocr_geometry(
            item, authority=authority, label=f"OCR line {line_index}", word=False
        )
        line_words = item["words"]
        if type(line_words) is not list:
            raise _error(f"OCR line {line_index} word axis drifted")
        for word_index, word in enumerate(line_words):
            word_item = _exact_dict(
                word, _OCR_WORD_FIELDS, f"OCR line {line_index} word {word_index}"
            )
            _validate_text(word_item["raw_text"], "OCR word text", nonempty=False)
            if word_item["score"] is not None or word_item["score_kind"] != (
                "PP_OCRV6_LINE_SCORE_ONLY"
            ):
                raise _error("OCR word score semantics drifted")
            _validate_ocr_geometry(
                word_item,
                authority=authority,
                label=f"OCR line {line_index} word {word_index}",
                word=True,
            )
            flattened.append(word_item)
        if item["raw_text"] != "".join(word["raw_text"] for word in line_words):
            raise _error(f"OCR line {line_index} exact word-text projection drifted")
    if not same_typed_json_v1(flattened, words):
        raise _error("OCR flattened word projection drifted")


def _validate_native_lines_words(lines: Any, words: Any) -> None:
    if type(lines) is not list or type(words) is not list:
        raise _error("native line/word axes drifted")
    flattened: list[dict[str, Any]] = []
    seen_line_identities: set[tuple[int, int]] = set()
    for line in lines:
        item = _exact_dict(line, _NATIVE_LINE_FIELDS, "native line")
        _validate_text(item["raw_text"], "native line text", nonempty=True)
        if not any(not character.isspace() for character in item["raw_text"]):
            raise _error("native line text cannot be whitespace-only")
        if item["score"] is not None or item["score_kind"] != "NATIVE_TEXT_NO_RECOGNITION_SCORE":
            raise _error("native line score semantics drifted")
        line_bbox = _bbox(
            item["canonical_bbox_mpt"],
            "native line bbox",
            integer=True,
            positive_area=False,
        )
        if any(coordinate < 0 for coordinate in line_bbox):
            raise _error("native line bbox lies outside the nonnegative canonical page domain")
        identity = (
            _nonnegative_int(item["block_number"], "native line block"),
            _nonnegative_int(item["line_number"], "native line number"),
        )
        if identity in seen_line_identities:
            raise _error("native visual-order line run is repeated or noncontiguous")
        seen_line_identities.add(identity)
        line_words = item["words"]
        if type(line_words) is not list or not line_words:
            raise _error("native line lacks words")
        prior_word: int | None = None
        for word in line_words:
            word_item = _exact_dict(word, _NATIVE_WORD_FIELDS, "native word")
            _validate_text(word_item["raw_text"], "native word text", nonempty=True)
            if not any(not character.isspace() for character in word_item["raw_text"]):
                raise _error("native word text cannot be whitespace-only")
            if word_item["score"] is not None or word_item["score_kind"] != (
                "NATIVE_TEXT_NO_RECOGNITION_SCORE"
            ):
                raise _error("native word score semantics drifted")
            word_bbox = _bbox(
                word_item["canonical_bbox_mpt"],
                "native word bbox",
                integer=True,
                positive_area=False,
            )
            if any(coordinate < 0 for coordinate in word_bbox):
                raise _error("native word bbox lies outside the nonnegative canonical page domain")
            if (word_item["block_number"], word_item["line_number"]) != identity:
                raise _error("native word/line identity drifted")
            word_number = _nonnegative_int(word_item["word_number"], "native word number")
            if prior_word is not None and word_number <= prior_word:
                raise _error("native word order drifted")
            prior_word = word_number
            flattened.append(word_item)
        if item["raw_text"] != " ".join(word["raw_text"] for word in line_words):
            raise _error("native line text projection drifted")
        expected_bbox = [
            min(word["canonical_bbox_mpt"][0] for word in line_words),
            min(word["canonical_bbox_mpt"][1] for word in line_words),
            max(word["canonical_bbox_mpt"][2] for word in line_words),
            max(word["canonical_bbox_mpt"][3] for word in line_words),
        ]
        if item["canonical_bbox_mpt"] != expected_bbox:
            raise _error("native line bbox projection drifted")
    if not same_typed_json_v1(flattened, words):
        raise _error("native flattened word projection drifted")


def _validate_quarantine(value: Any, *, physical_page: int) -> list[dict[str, Any]]:
    if type(value) is not list:
        raise _error("native quarantine axis drifted")
    for item in value:
        span = _exact_dict(item, _QUARANTINE_FIELDS, "native quarantined span")
        if span["page"] != physical_page:
            raise _error("native quarantine page drifted")
        _sha(span["text_sha256"], "native quarantine text identity")
        _nonnegative_int(span["nonwhitespace_character_count"], "quarantine character count")
        span_bbox = _bbox(
            span["bbox_mpt"],
            "native quarantine bbox",
            integer=True,
            positive_area=False,
        )
        if any(coordinate < 0 for coordinate in span_bbox):
            raise _error(
                "native quarantine bbox lies outside the nonnegative canonical page domain"
            )
        for field in ("block_number", "line_number", "span_number", "render_sequence"):
            _nonnegative_int(span[field], f"quarantine {field}")
        if type(span["color"]) is not int or not 0 <= span["color"] <= 0xFFFFFF:
            raise _error("native quarantine color drifted")
        if type(span["alpha"]) is not int or not 0 <= span["alpha"] <= 255:
            raise _error("native quarantine alpha drifted")
        if span["occluding_sequence"] is not None:
            _nonnegative_int(span["occluding_sequence"], "quarantine occluding sequence")
        if (
            span["occluding_object_type"] is not None
            and type(span["occluding_object_type"]) is not str
        ):
            raise _error("native quarantine object type drifted")
        if type(span["reason"]) is not str or not span["reason"]:
            raise _error("native quarantine reason drifted")
    return value


def _validate_ocr_normalization_ledger(
    value: Any,
    *,
    record: dict[str, Any],
    result: dict[str, Any],
    authority: dict[str, Any],
) -> None:
    ledger = _exact_dict(value, _OCR_NORMALIZATION_LEDGER_FIELDS, "OCR normalization ledger")
    if (
        ledger["format_version"]
        != "BANK_CORPUS_WAVE_1_ROLE_B_PPOCRV6_WORD_BOX_NORMALIZATION_LEDGER_V1"
        or ledger["rule_id"] != "PP_OCRV6_TEXT_WORD_BOX_PAGE_BOUNDARY_CLIP_MAX_1PX_V1"
        or ledger["maximum_per_edge_overshoot_pixels"] != 1
    ):
        raise _error("OCR normalization ledger policy drifted")
    for field in (
        "policy_sha256",
        "control_identity_sha256",
        "normalization_producer_implementation_ledger_sha256",
        "raw_payload_sha256",
        "normalized_payload_sha256",
    ):
        _sha(ledger[field], f"OCR normalization ledger {field}")
    if not same_typed_json_v1(ledger["pixel_dimensions"], authority["pixel_dimensions"]):
        raise _error("OCR normalization ledger pixel authority drifted")
    correction_count = _nonnegative_int(
        ledger["correction_count"], "OCR normalization correction count"
    )
    corrected_edge_count = _nonnegative_int(
        ledger["corrected_edge_count"], "OCR normalization corrected-edge count"
    )
    corrections = ledger["corrections"]
    if type(corrections) is not list or correction_count != len(corrections):
        raise _error("OCR normalization correction axis drifted")
    width, height = authority["pixel_dimensions"]
    prior_identity: tuple[int, int] | None = None
    observed_corrected_edges = 0
    for correction in corrections:
        item = _exact_dict(correction, _OCR_CORRECTION_FIELDS, "OCR normalization correction")
        line_index = _nonnegative_int(item["line_index"], "OCR correction line index")
        word_index = _nonnegative_int(item["word_index"], "OCR correction word index")
        identity = (line_index, word_index)
        if prior_identity is not None and identity <= prior_identity:
            raise _error("OCR normalization correction order drifted")
        prior_identity = identity
        if (
            line_index >= len(result["lines"])
            or word_index >= len(result["lines"][line_index]["words"])
            or item["json_path"] != f"$.text_word_boxes[{line_index}][{word_index}]"
        ):
            raise _error("OCR normalization correction locator drifted")
        raw_box = _bbox(item["raw_box"], "OCR correction raw box", integer=False)
        normalized_box = _bbox(
            item["normalized_box"], "OCR correction normalized box", integer=False
        )
        line_box = _bbox(
            item["validated_line_rec_box"],
            "OCR correction validated line box",
            integer=False,
        )
        per_edge = _exact_dict(
            item["per_edge_clip_pixels"],
            _OCR_CLIP_FIELDS,
            "OCR correction per-edge clip",
        )
        expected_per_edge = {
            "left": max(0, -raw_box[0]),
            "top": max(0, -raw_box[1]),
            "right": max(0, raw_box[2] - width),
            "bottom": max(0, raw_box[3] - height),
        }
        for edge in _OCR_CLIP_FIELDS:
            observed = _finite_number(per_edge[edge], f"OCR correction {edge} clip")
            if observed < 0 or observed > 1:
                raise _error("OCR normalization per-edge allowance drifted")
        expected_normalized = [
            min(width, max(0, raw_box[0])),
            min(height, max(0, raw_box[1])),
            min(width, max(0, raw_box[2])),
            min(height, max(0, raw_box[3])),
        ]
        result_line = result["lines"][line_index]
        result_word = result_line["words"][word_index]
        if (
            not same_typed_json_v1(per_edge, expected_per_edge)
            or not same_typed_json_v1(normalized_box, expected_normalized)
            or not same_typed_json_v1(line_box, result_line["raw_pixel_bbox"])
            or not same_typed_json_v1(normalized_box, result_word["normalized_pixel_bbox"])
            or not (
                0 <= normalized_box[0] < normalized_box[2] <= width
                and 0 <= normalized_box[1] < normalized_box[3] <= height
            )
            or not (
                line_box[0] <= normalized_box[0]
                and line_box[1] <= normalized_box[1]
                and normalized_box[2] <= line_box[2]
                and normalized_box[3] <= line_box[3]
            )
        ):
            raise _error("OCR normalization correction evidence drifted")
        observed_corrected_edges += sum(amount > 0 for amount in per_edge.values())
    if corrected_edge_count != observed_corrected_edges:
        raise _error("OCR normalization corrected-edge accounting drifted")
    expected_status = "NO_CHANGE" if not corrections else "PAGE_BOUNDARY_CLIPPED"
    if (
        ledger["status"] != expected_status
        or record["word_box_correction_count"] != correction_count
        or record["word_box_corrected_edge_count"] != corrected_edge_count
        or (not corrections and ledger["raw_payload_sha256"] != ledger["normalized_payload_sha256"])
        or (corrections and ledger["raw_payload_sha256"] == ledger["normalized_payload_sha256"])
    ):
        raise _error("OCR normalization ledger accounting drifted")


def _validate_result(record: dict[str, Any], value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise _error("authenticated page result must be a plain object")
    version = value.get("format_version")
    if version == "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V2":
        result = _exact_dict(value, _OCR_RESULT_V2_FIELDS, "OCR V2 result")
        if record["route"] != _OCR_ROUTE or result["status"] != _OCR_COMPLETE:
            raise _error("OCR V2 route/status drifted")
        if result["claim_boundary"] != "SOURCE_VISIBLE_PAGE_TEXT_AND_GEOMETRY_EVIDENCE_ONLY":
            raise _error("OCR V2 claim boundary drifted")
    elif version == "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V3":
        result = _exact_dict(value, _OCR_RESULT_V3_FIELDS, "OCR V3 result")
        if record["route"] != _OCR_ROUTE or result["status"] != _OCR_TERMINAL:
            raise _error("OCR V3 route/status drifted")
        if (
            result["claim_boundary"]
            != "SOURCE_VISIBLE_PAGE_RAW_OCR_EVIDENCE_WITH_UNRESOLVED_GEOMETRY"
        ):
            raise _error("OCR V3 claim boundary drifted")
        failure = _exact_dict(
            result["normalization_failure"],
            _OCR_NORMALIZATION_FAILURE_FIELDS,
            "OCR normalization failure",
        )
        if (
            failure["format_version"] != "BANK_CORPUS_WAVE_1_PPOCRV6_NORMALIZATION_FAILURE_V1"
            or failure["status"] != _OCR_TERMINAL
            or failure["reason"] != "BOUNDED_WORD_BOX_NORMALIZATION_INVARIANT_FAILED"
        ):
            raise _error("OCR normalization failure reason drifted")
        for field in (
            "policy_sha256",
            "control_identity_sha256",
            "normalization_producer_implementation_ledger_sha256",
            "raw_payload_sha256",
        ):
            _sha(failure[field], f"OCR normalization failure {field}")
        dimensions = failure["pixel_dimensions"]
        if (
            type(dimensions) is not list
            or len(dimensions) != 2
            or any(type(item) is not int or item <= 0 for item in dimensions)
        ):
            raise _error("OCR normalization failure pixel dimensions drifted")
        if result["ocr_fallback_used"] is not False:
            raise _error("terminal OCR result used an OCR fallback")
    elif version == "BANK_CORPUS_WAVE_1_ROLE_B_CAUSAL_NATIVE_PAGE_READ_RESULT_V1":
        result = _exact_dict(value, _NATIVE_RESULT_FIELDS, "causal-native V1 result")
        if record["route"] != _NATIVE_ROUTE or result["status"] not in {
            _NATIVE_COMPLETE,
            *_NATIVE_TERMINAL,
        }:
            raise _error("causal-native route/status drifted")
        if result["claim_boundary"] != "SOURCE_VISIBLE_NATIVE_PAGE_TEXT_AND_GEOMETRY_EVIDENCE_ONLY":
            raise _error("causal-native claim boundary drifted")
        if result["document_id"] != record["document_id"]:
            raise _error("causal-native document binding drifted")
        if result["backend_payload_sha256"] != record["backend_payload_ref"]["sha256"]:
            raise _error("causal-native backend reference drifted")
    else:
        raise _error("authenticated page result format is unsupported")
    for field in ("source_sha256", "source_size_bytes", "physical_page", "route", "request_sha256"):
        if not same_typed_json_v1(result[field], record[field]):
            raise _error(f"authenticated page result {field} drifted")
    if result["status"] != record["status"]:
        raise _error("authenticated page result status drifted")
    _validate_request(record, result)
    _sha(result["provider_identity_sha256"], "authenticated result provider identity")
    if result["provider_identity_sha256"] != record["request"]["provider_identity_sha256"]:
        raise _error("authenticated result provider identity drifted")
    if result["source_blank_claimed"] is not False:
        raise _error("authenticated page result claimed blank source")
    if not same_typed_json_v1(result["safety"], _UPSTREAM_SAFETY):
        raise _error("authenticated page result safety boundary drifted")
    result_payload = canonical_json_bytes_v1(result)
    if (
        len(result_payload) != record["result_ref"]["size_bytes"]
        or sha256(result_payload).hexdigest() != record["result_ref"]["sha256"]
    ):
        raise _error("authenticated result object/reference identity drifted")
    if record["route"] == _OCR_ROUTE:
        _sha(
            result["render_runtime_identity_sha256"],
            "OCR result render runtime identity",
        )
        if (
            result["render_runtime_identity_sha256"]
            != record["request"]["render_runtime_identity_sha256"]
        ):
            raise _error("OCR result render runtime identity drifted")
        if not same_typed_json_v1(result["input_render_ref"], record["render_ref"]):
            raise _error("OCR render reference drifted")
        if not same_typed_json_v1(result["backend_payload_ref"], record["backend_payload_ref"]):
            raise _error("OCR backend reference drifted")
        authority = _validate_ocr_coordinate_authority(result["coordinate_authority"])
        if result["status"] == _OCR_TERMINAL and not same_typed_json_v1(
            result["normalization_failure"]["pixel_dimensions"],
            authority["pixel_dimensions"],
        ):
            raise _error("OCR normalization failure coordinate authority drifted")
        if result["status"] == _OCR_COMPLETE:
            _validate_ocr_lines_words(result["lines"], result["words"], authority=authority)
            _validate_ocr_normalization_ledger(
                result["word_box_normalization_ledger"],
                record=record,
                result=result,
                authority=authority,
            )
            metrics = result["metrics"]
            expected_metric_fields = {
                "line_count",
                "word_token_count",
                "minimum_line_score",
                "mean_line_score",
                "lines_below_0_8",
                "lines_below_0_9",
            }
            _exact_dict(metrics, expected_metric_fields, "OCR metrics")
            for field in ("line_count", "word_token_count", "lines_below_0_8", "lines_below_0_9"):
                _nonnegative_int(metrics[field], f"OCR metric {field}")
            if metrics["line_count"] != len(result["lines"]) or metrics["word_token_count"] != len(
                result["words"]
            ):
                raise _error("OCR result metrics accounting drifted")
            scores = [line["score"] for line in result["lines"]]
            expected_minimum = min(scores) if scores else None
            expected_mean = fmean(scores) if scores else None
            if (
                not same_typed_json_v1(metrics["minimum_line_score"], expected_minimum)
                or not same_typed_json_v1(metrics["mean_line_score"], expected_mean)
                or metrics["lines_below_0_8"] != sum(score < 0.8 for score in scores)
                or metrics["lines_below_0_9"] != sum(score < 0.9 for score in scores)
            ):
                raise _error("OCR result score metrics drifted")
        elif result["lines"] != [] or result["words"] != []:
            raise _error("terminal OCR result exposed normalized line/word geometry")
        elif not same_typed_json_v1(result["metrics"], {"line_count": 0, "word_token_count": 0}):
            raise _error("terminal OCR result metrics drifted")
    else:
        _sha(result["full_control_identity_sha256"], "native full-control identity")
        _sha(result["backend_payload_sha256"], "native backend payload identity")
        if not same_typed_json_v1(result["coordinate_authority"], _NATIVE_AUTHORITY):
            raise _error("causal-native coordinate authority drifted")
        _validate_native_lines_words(result["lines"], result["words"])
        _validate_quarantine(result["quarantined_spans"], physical_page=record["physical_page"])
        if result["status"] in _NATIVE_TERMINAL and (result["lines"] or result["words"]):
            raise _error("terminal native result exposed accepted line/word evidence")
        expected_native_metrics = {
            "line_count": len(result["lines"]),
            "word_token_count": len(result["words"]),
            "quarantined_span_count": len(result["quarantined_spans"]),
        }
        if not same_typed_json_v1(result["metrics"], expected_native_metrics):
            raise _error("causal-native result metrics drifted")
        if result["ocr_fallback_used"] is not False:
            raise _error("causal-native result used an OCR fallback")
        if result["status"] == _NATIVE_COMPLETE:
            if (
                result["failure_type"] is not None
                or result["native_text_quality"] != "USABLE_TEXT_LAYER"
                or result["corruption_markers"] != []
                or not result["words"]
            ):
                raise _error("complete causal-native result quality drifted")
        elif result["status"] == "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY":
            if (
                result["failure_type"] not in _NATIVE_VISIBILITY_FAILURE_TYPES
                or result["native_text_quality"] is not None
                or result["corruption_markers"] != []
                or result["quarantined_spans"] != []
            ):
                raise _error("unresolved causal-native visibility evidence drifted")
        elif (
            result["failure_type"] is not None
            or result["native_text_quality"] not in {"NO_TEXT_LAYER", "CORRUPT_TEXT_LAYER"}
            or type(result["corruption_markers"]) is not list
            or any(type(marker) is not str or not marker for marker in result["corruption_markers"])
            or result["corruption_markers"] != sorted(set(result["corruption_markers"]))
            or (
                result["native_text_quality"] == "NO_TEXT_LAYER"
                and result["corruption_markers"] != []
            )
            or (
                result["native_text_quality"] == "CORRUPT_TEXT_LAYER"
                and result["corruption_markers"] == []
            )
        ):
            raise _error("unresolved native text-quality evidence drifted")
    if (
        len(result["lines"]) != record["line_count"]
        or len(result["words"]) != record["word_token_count"]
    ):
        raise _error("authenticated page result line/word accounting drifted")
    if (
        record["route"] == _NATIVE_ROUTE
        and len(result["quarantined_spans"]) != record["quarantined_span_count"]
    ):
        raise _error("authenticated native quarantine accounting drifted")
    return result


def _terminal_reason(result: dict[str, Any]) -> str | None:
    status = result["status"]
    if status == _OCR_TERMINAL:
        return result["normalization_failure"]["reason"]
    if status == "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY":
        return result["failure_type"]
    if status == "UNRESOLVED_NATIVE_TEXT_QUALITY":
        return result["native_text_quality"]
    return None


def _supplement_geometry(item: dict[str, Any], authority: dict[str, Any], label: str) -> None:
    pixel_width, pixel_height = authority["pixel_dimensions"]
    raw_box = _bbox(item["raw_pixel_bbox"], f"{label} raw rec-box", integer=False)
    raw_polygon = _polygon(
        item["raw_pixel_polygon"],
        f"{label} raw rec-polygon",
        integer=False,
    )
    if not (
        0 <= raw_box[0] < raw_box[2] <= pixel_width and 0 <= raw_box[1] < raw_box[3] <= pixel_height
    ) or any(
        not 0 <= point[0] <= pixel_width or not 0 <= point[1] <= pixel_height
        for point in raw_polygon
    ):
        raise _error(f"{label} raw geometry lies outside the rendered page")
    observed_box = _bbox(item["canonical_bbox_mpt"], f"{label} canonical rec-box", integer=True)
    observed_polygon = _polygon(
        item["canonical_polygon_mpt"],
        f"{label} canonical rec-polygon",
        integer=True,
    )
    raw_box_polygon = [
        [raw_box[0], raw_box[1]],
        [raw_box[2], raw_box[1]],
        [raw_box[2], raw_box[3]],
        [raw_box[0], raw_box[3]],
    ]
    expected_box = _canonical_bbox(_transform_pixel_polygon(raw_box_polygon, authority))
    expected_polygon = _transform_pixel_polygon(raw_polygon, authority)
    unrotated_width, unrotated_height = authority["unrotated_dimensions_mpt"]
    if (
        not same_typed_json_v1(observed_box, expected_box)
        or not same_typed_json_v1(observed_polygon, expected_polygon)
        or any(
            not observed_box[0] <= point[0] <= observed_box[2]
            or not observed_box[1] <= point[1] <= observed_box[3]
            for point in observed_polygon
        )
        or not (
            0 <= observed_box[0] < observed_box[2] <= unrotated_width
            and 0 <= observed_box[1] < observed_box[3] <= unrotated_height
        )
    ):
        raise _error(f"{label} canonical rec-box/polygon authority drifted")


def validate_line_only_supplement_v1(
    value: Any,
    *,
    page_record: dict[str, Any],
    page_result: dict[str, Any],
    supplement_ref: dict[str, Any],
) -> dict[str, Any]:
    page_record = _validate_page_record(page_record)
    page_result = _validate_result(page_record, page_result)
    supplement = _exact_dict(value, _SUPPLEMENT_FIELDS, "line-only supplement")
    if supplement["format_version"] != LINE_SUPPLEMENT_FORMAT_VERSION:
        raise _error("line-only supplement format drifted")
    if supplement["claim_boundary"] != LINE_SUPPLEMENT_CLAIM_BOUNDARY:
        raise _error("line-only supplement claim boundary drifted")
    if page_record["route"] != _OCR_ROUTE or page_record["status"] != _OCR_TERMINAL:
        raise _error("line-only supplement is restricted to terminal OCR word geometry")
    _sha(supplement["control_identity_sha256"], "line-only control identity")
    disposition = supplement["supplemental_disposition"]
    if disposition not in {_SUPPLEMENT_ACCEPTED, _SUPPLEMENT_REJECTED}:
        raise _error("line-only supplemental disposition drifted")
    upstream = _exact_dict(
        supplement["upstream"], _SUPPLEMENT_UPSTREAM_FIELDS, "line-only upstream binding"
    )
    _sha(upstream["aggregate_identity_sha256"], "line-only aggregate identity")
    if (
        upstream["status"] != _OCR_TERMINAL
        or upstream["status_preserved"] is not True
        or upstream["normalization_failure_reason"]
        != "BOUNDED_WORD_BOX_NORMALIZATION_INVARIANT_FAILED"
        or upstream["request_sha256"] != page_record["request_sha256"]
        or upstream["request_ordinal"] != page_record["request_ordinal"]
        or upstream["document_id"] != page_record["document_id"]
        or upstream["physical_page"] != page_record["physical_page"]
        or upstream["source_sha256"] != page_record["source_sha256"]
        or not same_typed_json_v1(
            upstream["backend_payload_ref"], page_record["backend_payload_ref"]
        )
        or not same_typed_json_v1(upstream["result_ref"], page_record["result_ref"])
        or not same_typed_json_v1(
            upstream["normalization_failure"], page_result["normalization_failure"]
        )
    ):
        raise _error("line-only supplement changed upstream terminal evidence")
    authority = _validate_ocr_coordinate_authority(supplement["coordinate_authority"])
    if not same_typed_json_v1(authority, page_result["coordinate_authority"]):
        raise _error("line-only supplement coordinate authority drifted")
    if supplement["words"] != []:
        raise _error("line-only supplement exposed word evidence")
    lines = supplement["lines"]
    if type(lines) is not list:
        raise _error("line-only supplement line axis drifted")
    width, height = authority["pixel_dimensions"]
    line_indexes: list[int] = []
    for index, line in enumerate(lines):
        item = _exact_dict(line, _SUPPLEMENT_LINE_FIELDS, f"supplement line {index}")
        if (
            item["format_version"] != "BANK_CORPUS_WAVE_1_ROLE_B_LINE_OBSERVATION_V1"
            or type(item["text"]) is not str
            or item["text"] == ""
        ):
            raise _error("line-only supplement line identity/text drifted")
        line_index = _nonnegative_int(item["line_index"], "line-only source line index")
        if line_indexes and line_index <= line_indexes[-1]:
            raise _error("line-only supplement source line order drifted")
        line_indexes.append(line_index)
        try:
            item["text"].encode("utf-8")
        except UnicodeEncodeError as error:
            raise _error("line-only supplement line contains invalid Unicode") from error
        if (
            type(item["score"]) is not float
            or not isfinite(item["score"])
            or not 0.0 <= item["score"] <= 1.0
        ):
            raise _error("line-only supplement score semantics drifted")
        normalized_geometry = {
            "raw_pixel_bbox": item["pixel_rec_box"],
            "raw_pixel_polygon": item["pixel_rec_polygon"],
            "canonical_bbox_mpt": item["canonical_rec_box_mpt"],
            "canonical_polygon_mpt": item["canonical_rec_polygon_mpt"],
        }
        _supplement_geometry(normalized_geometry, authority, f"supplement line {index}")
        raw_box = item["pixel_rec_box"]
        raw_polygon = item["pixel_rec_polygon"]
        if any(
            not 0 <= point[0] <= width or not 0 <= point[1] <= height for point in raw_polygon
        ) or not (0 <= raw_box[0] < raw_box[2] <= width and 0 <= raw_box[1] < raw_box[3] <= height):
            raise _error("line-only supplement raw geometry lies outside the page")
    metrics = _exact_dict(
        supplement["metrics"],
        {
            "validated_line_axis_count",
            "excluded_empty_line_axis_count",
            "accepted_line_count",
            "accepted_word_count",
            "quarantined_subdivision_count",
        },
        "line-only supplement metrics",
    )
    for field in metrics:
        _nonnegative_int(metrics[field], f"line-only metric {field}")
    quarantine = _exact_dict(
        supplement["quarantine"],
        _SUPPLEMENT_QUARANTINE_FIELDS,
        "line-only word-axis quarantine",
    )
    counts = quarantine["ordered_subdivision_counts_by_line"]
    if type(counts) is not list:
        raise _error("line-only quarantine subdivision axis drifted")
    for count in counts:
        _nonnegative_int(count, "line-only quarantine subdivision count")
    if (
        quarantine["format_version"] != "BANK_CORPUS_WAVE_1_ROLE_B_WORD_SUBDIVISION_QUARANTINE_V1"
        or quarantine["status"] != "QUARANTINED_UNRESOLVED_WORD_BOX_GEOMETRY"
        or quarantine["reason"] != "BOUNDED_WORD_BOX_NORMALIZATION_INVARIANT_FAILED"
        or quarantine["total_subdivision_count"] != sum(counts)
        or quarantine["raw_provider_payload_sha256"]
        != page_result["normalization_failure"]["raw_payload_sha256"]
        or not same_typed_json_v1(
            quarantine["raw_backend_payload_ref"], page_record["backend_payload_ref"]
        )
        or quarantine["word_text_exposed"] is not False
        or quarantine["word_geometry_exposed"] is not False
        or quarantine["accepted_word_count"] != 0
    ):
        raise _error("line-only word-axis quarantine boundary drifted")
    _sha(quarantine["word_axes_sha256"], "line-only hidden word-axis identity")
    _sha(quarantine["raw_provider_payload_sha256"], "line-only raw provider identity")
    expected_accepted = len(lines) if disposition == _SUPPLEMENT_ACCEPTED else 0
    if (
        metrics["accepted_line_count"] != expected_accepted
        or metrics["accepted_line_count"] != len(lines)
        or metrics["accepted_line_count"] + metrics["excluded_empty_line_axis_count"]
        != metrics["validated_line_axis_count"]
        or metrics["accepted_word_count"] != 0
        or metrics["quarantined_subdivision_count"] != quarantine["total_subdivision_count"]
        or metrics["validated_line_axis_count"] != len(counts)
        or any(index >= metrics["validated_line_axis_count"] for index in line_indexes)
        or (disposition == _SUPPLEMENT_ACCEPTED and lines == [])
        or (disposition == _SUPPLEMENT_REJECTED and lines != [])
    ):
        raise _error("line-only supplement metrics drifted")
    if not same_typed_json_v1(supplement["safety"], _SUPPLEMENT_SAFETY):
        raise _error("line-only supplement safety drifted")
    reference = _validate_object_ref(supplement_ref, suffix=".json", label="line supplement ref")
    payload = canonical_json_bytes_v1(supplement)
    if (
        len(payload) != reference["size_bytes"]
        or sha256(payload).hexdigest() != reference["sha256"]
    ):
        raise _error("line-only supplement object/reference identity drifted")
    return canonical_clone_v1(supplement)


def _atom(
    *,
    page_id: str,
    request_sha256: str,
    kind: str,
    authority: str,
    raw_text: str | None,
    raw_text_sha256: str | None,
    quarantine_summary: dict[str, Any] | None,
    score: int | float | None,
    score_kind: str,
    canonical_bbox_mpt: list[int] | None,
    canonical_polygon_mpt: list[list[int]] | None,
    pixel_bbox: list[int | float] | None,
    pixel_polygon: list[list[int | float]] | None,
    pixel_geometry_kind: str,
    upstream_locator: dict[str, Any],
) -> dict[str, Any]:
    atom_payload = {
        "kind": kind,
        "authority": authority,
        "raw_text": raw_text,
        "raw_text_sha256": raw_text_sha256,
        "quarantine_summary": canonical_clone_v1(quarantine_summary),
        "quarantine_payload_sha256": None,
        "score": score,
        "score_kind": score_kind,
        "canonical_bbox_mpt": canonical_clone_v1(canonical_bbox_mpt),
        "canonical_polygon_mpt": canonical_clone_v1(canonical_polygon_mpt),
        "pixel_bbox": canonical_clone_v1(pixel_bbox),
        "pixel_polygon": canonical_clone_v1(pixel_polygon),
        "pixel_geometry_kind": pixel_geometry_kind,
        "upstream_locator": canonical_clone_v1(upstream_locator),
    }
    if quarantine_summary is not None:
        atom_payload["quarantine_payload_sha256"] = canonical_json_sha256_v1(
            {
                key: atom_payload[key]
                for key in sorted(atom_payload)
                if key != "quarantine_payload_sha256"
            }
        )
    identity_payload = {
        "source_local_page_id": page_id,
        "request_sha256": request_sha256,
        "atom_payload": atom_payload,
    }
    return {
        "source_local_id": make_source_object_id_v1("atom", identity_payload),
        **atom_payload,
    }


def _text_sha(raw_text: str) -> str:
    return sha256(raw_text.encode("utf-8")).hexdigest()


def _empty_axis_summary(axis_kind: str) -> dict[str, Any]:
    return {
        "kind": "EMPTY_TEXT_AXIS_EXCLUSION",
        "axis_kind": axis_kind,
        "excluded_text_sha256": _text_sha(""),
        "reason": "EXACT_EMPTY_STRING_NOT_PROMOTED",
    }


def _ocr_atoms(
    result: dict[str, Any], *, page_id: str, request_sha256: str
) -> list[dict[str, Any]]:
    atoms = []
    for line_index, line in enumerate(result["lines"]):
        line_empty = line["raw_text"] == ""
        atoms.append(
            _atom(
                page_id=page_id,
                request_sha256=request_sha256,
                kind=(AtomKind.EXCLUDED_EMPTY_LINE.value if line_empty else AtomKind.LINE.value),
                authority=(
                    AtomAuthority.UPSTREAM_QUARANTINE.value
                    if line_empty
                    else AtomAuthority.AUTHENTICATED_PRIMARY.value
                ),
                raw_text=None if line_empty else line["raw_text"],
                raw_text_sha256=None if line_empty else _text_sha(line["raw_text"]),
                quarantine_summary=_empty_axis_summary("LINE") if line_empty else None,
                score=line["score"],
                score_kind=line["score_kind"],
                canonical_bbox_mpt=line["canonical_bbox_mpt"],
                canonical_polygon_mpt=line["canonical_polygon_mpt"],
                pixel_bbox=line["raw_pixel_bbox"],
                pixel_polygon=line["raw_pixel_polygon"],
                pixel_geometry_kind="RAW_PROVIDER_LINE_REC_BOX_AND_POLYGON",
                upstream_locator={"kind": "OCR_LINE_INDEX", "line_index": line_index},
            )
        )
        for word_index, word in enumerate(line["words"]):
            word_empty = word["raw_text"] == ""
            atoms.append(
                _atom(
                    page_id=page_id,
                    request_sha256=request_sha256,
                    kind=(
                        AtomKind.EXCLUDED_EMPTY_WORD.value if word_empty else AtomKind.WORD.value
                    ),
                    authority=(
                        AtomAuthority.UPSTREAM_QUARANTINE.value
                        if word_empty
                        else AtomAuthority.AUTHENTICATED_PRIMARY.value
                    ),
                    raw_text=None if word_empty else word["raw_text"],
                    raw_text_sha256=None if word_empty else _text_sha(word["raw_text"]),
                    quarantine_summary=_empty_axis_summary("WORD") if word_empty else None,
                    score=None,
                    score_kind=word["score_kind"],
                    canonical_bbox_mpt=word["canonical_bbox_mpt"],
                    canonical_polygon_mpt=word["canonical_polygon_mpt"],
                    pixel_bbox=word["normalized_pixel_bbox"],
                    pixel_polygon=None,
                    pixel_geometry_kind="BOUNDED_NORMALIZED_WORD_BOX",
                    upstream_locator={
                        "kind": "OCR_WORD_INDEX",
                        "line_index": line_index,
                        "word_index": word_index,
                    },
                )
            )
    return atoms


def _native_atoms(
    result: dict[str, Any], *, page_id: str, request_sha256: str
) -> list[dict[str, Any]]:
    atoms = []
    for line in result["lines"]:
        atoms.append(
            _atom(
                page_id=page_id,
                request_sha256=request_sha256,
                kind=AtomKind.LINE.value,
                authority=AtomAuthority.AUTHENTICATED_PRIMARY.value,
                raw_text=line["raw_text"],
                raw_text_sha256=_text_sha(line["raw_text"]),
                quarantine_summary=None,
                score=None,
                score_kind=line["score_kind"],
                canonical_bbox_mpt=line["canonical_bbox_mpt"],
                canonical_polygon_mpt=None,
                pixel_bbox=None,
                pixel_polygon=None,
                pixel_geometry_kind="NOT_APPLICABLE",
                upstream_locator={
                    "kind": "NATIVE_LINE_INDEX",
                    "block_number": line["block_number"],
                    "line_number": line["line_number"],
                },
            )
        )
        for word in line["words"]:
            atoms.append(
                _atom(
                    page_id=page_id,
                    request_sha256=request_sha256,
                    kind=AtomKind.WORD.value,
                    authority=AtomAuthority.AUTHENTICATED_PRIMARY.value,
                    raw_text=word["raw_text"],
                    raw_text_sha256=_text_sha(word["raw_text"]),
                    quarantine_summary=None,
                    score=None,
                    score_kind=word["score_kind"],
                    canonical_bbox_mpt=word["canonical_bbox_mpt"],
                    canonical_polygon_mpt=None,
                    pixel_bbox=None,
                    pixel_polygon=None,
                    pixel_geometry_kind="NOT_APPLICABLE",
                    upstream_locator={
                        "kind": "NATIVE_WORD_INDEX",
                        "block_number": word["block_number"],
                        "line_number": word["line_number"],
                        "word_number": word["word_number"],
                    },
                )
            )
    for span in result["quarantined_spans"]:
        locator = {
            "kind": "NATIVE_QUARANTINED_SPAN_INDEX",
            "block_number": span["block_number"],
            "line_number": span["line_number"],
            "span_number": span["span_number"],
        }
        summary = {
            "kind": "NATIVE_EXCLUDED_SPAN",
            "excluded_text_sha256": span["text_sha256"],
            "nonwhitespace_character_count": span["nonwhitespace_character_count"],
            "color": span["color"],
            "alpha": span["alpha"],
            "render_sequence": span["render_sequence"],
            "occluding_sequence": span["occluding_sequence"],
            "occluding_object_type": span["occluding_object_type"],
            "reason": span["reason"],
        }
        atoms.append(
            _atom(
                page_id=page_id,
                request_sha256=request_sha256,
                kind=AtomKind.QUARANTINED_SPAN.value,
                authority=AtomAuthority.UPSTREAM_QUARANTINE.value,
                raw_text=None,
                raw_text_sha256=None,
                quarantine_summary=summary,
                score=None,
                score_kind="UPSTREAM_QUARANTINE_HASH_ONLY",
                canonical_bbox_mpt=span["bbox_mpt"],
                canonical_polygon_mpt=None,
                pixel_bbox=None,
                pixel_polygon=None,
                pixel_geometry_kind="NOT_APPLICABLE",
                upstream_locator=locator,
            )
        )
    return atoms


def _supplement_atoms(
    supplement: dict[str, Any], *, page_id: str, request_sha256: str
) -> list[dict[str, Any]]:
    line_atoms = [
        _atom(
            page_id=page_id,
            request_sha256=request_sha256,
            kind=AtomKind.LINE.value,
            authority=AtomAuthority.SUPPLEMENTAL_COARSE_LINE.value,
            raw_text=line["text"],
            raw_text_sha256=_text_sha(line["text"]),
            quarantine_summary=None,
            score=line["score"],
            score_kind="PP_OCRV6_LINE_RECOGNITION_SCORE",
            canonical_bbox_mpt=line["canonical_rec_box_mpt"],
            canonical_polygon_mpt=line["canonical_rec_polygon_mpt"],
            pixel_bbox=line["pixel_rec_box"],
            pixel_polygon=line["pixel_rec_polygon"],
            pixel_geometry_kind="RAW_PROVIDER_LINE_REC_BOX_AND_POLYGON",
            upstream_locator={"kind": "SUPPLEMENT_LINE_INDEX", "line_index": line["line_index"]},
        )
        for line in supplement["lines"]
    ]
    quarantine = supplement["quarantine"]
    locator = {"kind": "SUPPLEMENT_WORD_AXIS_QUARANTINE"}
    summary = {
        "kind": "TERMINAL_WORD_AXIS_QUARANTINE",
        "reason": quarantine["reason"],
        "ordered_subdivision_counts_by_line": quarantine["ordered_subdivision_counts_by_line"],
        "total_subdivision_count": quarantine["total_subdivision_count"],
        "word_axes_sha256": quarantine["word_axes_sha256"],
        "raw_provider_payload_sha256": quarantine["raw_provider_payload_sha256"],
    }
    line_atoms.append(
        _atom(
            page_id=page_id,
            request_sha256=request_sha256,
            kind=AtomKind.QUARANTINED_SUMMARY.value,
            authority=AtomAuthority.UPSTREAM_QUARANTINE.value,
            raw_text=None,
            raw_text_sha256=None,
            quarantine_summary=summary,
            score=None,
            score_kind="UPSTREAM_QUARANTINE_HASH_ONLY",
            canonical_bbox_mpt=None,
            canonical_polygon_mpt=None,
            pixel_bbox=None,
            pixel_polygon=None,
            pixel_geometry_kind="NOT_APPLICABLE",
            upstream_locator=locator,
        )
    )
    return line_atoms


def _supplement_evidence_projection(supplement: dict[str, Any] | None) -> Any:
    if supplement is None:
        return None
    return {
        "supplemental_disposition": supplement["supplemental_disposition"],
        "lines": supplement["lines"],
        "words": supplement["words"],
        "quarantine": supplement["quarantine"],
        "metrics": supplement["metrics"],
    }


def project_authenticated_page_v1(
    *,
    page_record: dict[str, Any],
    page_result: dict[str, Any],
    line_only_supplement: dict[str, Any] | None = None,
    line_only_supplement_ref: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return one neutral envelope from caller-supplied authenticated objects."""

    record = _validate_page_record(page_record)
    result = _validate_result(record, page_result)
    if (line_only_supplement is None) != (line_only_supplement_ref is None):
        raise _error("line-only supplement and its authenticated ref must be supplied together")
    supplement = None
    if line_only_supplement is not None and line_only_supplement_ref is not None:
        supplement = validate_line_only_supplement_v1(
            line_only_supplement,
            page_record=record,
            page_result=result,
            supplement_ref=line_only_supplement_ref,
        )
    references = []
    if record["render_ref"] is not None:
        references.append(_neutral_ref(record["render_ref"], kind="RENDER", media_type="image/png"))
    references.extend(
        [
            _neutral_ref(
                record["backend_payload_ref"],
                kind="BACKEND_PAYLOAD",
                media_type="application/json",
            ),
            _neutral_ref(record["result_ref"], kind="RESULT", media_type="application/json"),
        ]
    )
    if line_only_supplement_ref is not None:
        references.append(
            _neutral_ref(
                line_only_supplement_ref,
                kind="LINE_SUPPLEMENT",
                media_type="application/json",
            )
        )
    locator = {
        "source_sha256": record["source_sha256"],
        "source_size_bytes": record["source_size_bytes"],
        "physical_page": record["physical_page"],
        "request_sha256": record["request_sha256"],
    }
    terminal_reason = _terminal_reason(result)
    result_lines = result["lines"]
    result_words = result["words"]
    result_quarantine = result.get("quarantined_spans", [])
    supplement_metrics = (
        supplement["metrics"]
        if supplement is not None
        else {
            "validated_line_axis_count": 0,
            "excluded_empty_line_axis_count": 0,
            "accepted_line_count": 0,
            "accepted_word_count": 0,
            "quarantined_subdivision_count": 0,
        }
    )
    receipt = {
        "format_version": PROJECTION_RECEIPT_FORMAT_VERSION,
        "result_ref_sha256": record["result_ref"]["sha256"],
        "result_projection_sha256": canonical_json_sha256_v1(result),
        "coordinate_authority_sha256": canonical_json_sha256_v1(result["coordinate_authority"]),
        "upstream_line_axis_sha256": canonical_json_sha256_v1(result_lines),
        "upstream_word_axis_sha256": canonical_json_sha256_v1(result_words),
        "upstream_quarantine_axis_sha256": canonical_json_sha256_v1(result_quarantine),
        "atom_sequence_sha256": "0" * 64,
        "atom_id_sequence_sha256": "0" * 64,
        "supplement_ref_sha256": (
            line_only_supplement_ref["sha256"] if line_only_supplement_ref is not None else None
        ),
        "supplement_projection_sha256": (
            canonical_json_sha256_v1(supplement) if supplement is not None else None
        ),
        "supplement_evidence_projection_sha256": canonical_json_sha256_v1(
            _supplement_evidence_projection(supplement)
        ),
        "upstream_line_axis_count": len(result_lines),
        "upstream_word_axis_count": len(result_words),
        "upstream_quarantined_span_axis_count": len(result_quarantine),
        "excluded_empty_line_axis_count": sum(line["raw_text"] == "" for line in result_lines),
        "excluded_empty_word_axis_count": sum(word["raw_text"] == "" for word in result_words),
        "supplement_validated_line_axis_count": supplement_metrics["validated_line_axis_count"],
        "supplement_accepted_line_count": supplement_metrics["accepted_line_count"],
        "supplement_excluded_empty_line_axis_count": supplement_metrics[
            "excluded_empty_line_axis_count"
        ],
        "supplement_quarantined_subdivision_count": supplement_metrics[
            "quarantined_subdivision_count"
        ],
    }
    page_identity_payload = {
        **locator,
        "route": record["route"],
        "upstream_status": record["status"],
        "terminal_reason": terminal_reason,
        "evidence_refs": references,
        "coordinate_authority_sha256": receipt["coordinate_authority_sha256"],
        "projection_source_receipt": {
            key: receipt[key]
            for key in sorted(set(receipt) - {"atom_sequence_sha256", "atom_id_sequence_sha256"})
        },
    }
    page_id = f"ssv1:page:{canonical_json_sha256_v1(page_identity_payload)}"
    if record["route"] == _OCR_ROUTE and record["status"] == _OCR_COMPLETE:
        atoms = _ocr_atoms(result, page_id=page_id, request_sha256=record["request_sha256"])
    elif record["route"] == _NATIVE_ROUTE:
        atoms = _native_atoms(result, page_id=page_id, request_sha256=record["request_sha256"])
    else:
        atoms = []
    if supplement is not None:
        atoms.extend(
            _supplement_atoms(
                supplement,
                page_id=page_id,
                request_sha256=record["request_sha256"],
            )
        )
    receipt["atom_sequence_sha256"] = canonical_json_sha256_v1(atoms)
    receipt["atom_id_sequence_sha256"] = canonical_json_sha256_v1(
        [atom["source_local_id"] for atom in atoms]
    )
    envelope = {
        "format_version": NEUTRAL_PAGE_FORMAT_VERSION,
        "claim_boundary": NEUTRAL_PAGE_CLAIM_BOUNDARY,
        "source_locator": locator,
        "source_local_page_id": page_id,
        "route": record["route"],
        "upstream_status": record["status"],
        "terminal": record["unresolved"],
        "terminal_reason": terminal_reason,
        "coordinate_authority": canonical_clone_v1(result["coordinate_authority"]),
        "evidence_refs": references,
        "atoms": atoms,
        "projection_receipt": receipt,
        "metrics": {
            "atom_count": len(atoms),
            "upstream_line_axis_count": len(result_lines),
            "upstream_word_axis_count": len(result_words),
            "upstream_quarantined_span_axis_count": len(result_quarantine),
            "primary_line_count": sum(
                atom["kind"] == AtomKind.LINE
                and atom["authority"] == AtomAuthority.AUTHENTICATED_PRIMARY
                for atom in atoms
            ),
            "primary_word_count": sum(
                atom["kind"] == AtomKind.WORD
                and atom["authority"] == AtomAuthority.AUTHENTICATED_PRIMARY
                for atom in atoms
            ),
            "excluded_empty_line_axis_count": sum(
                atom["kind"] == AtomKind.EXCLUDED_EMPTY_LINE for atom in atoms
            ),
            "excluded_empty_word_axis_count": sum(
                atom["kind"] == AtomKind.EXCLUDED_EMPTY_WORD for atom in atoms
            ),
            "supplemental_line_count": sum(
                atom["authority"] == AtomAuthority.SUPPLEMENTAL_COARSE_LINE for atom in atoms
            ),
            "supplement_validated_line_axis_count": supplement_metrics["validated_line_axis_count"],
            "supplement_excluded_empty_line_axis_count": supplement_metrics[
                "excluded_empty_line_axis_count"
            ],
            "supplement_quarantined_subdivision_count": supplement_metrics[
                "quarantined_subdivision_count"
            ],
            "quarantined_atom_count": sum(
                atom["authority"] == AtomAuthority.UPSTREAM_QUARANTINE for atom in atoms
            ),
        },
        "safety": canonical_clone_v1(SOURCE_STRUCTURE_SAFETY_V1),
    }
    return validate_neutral_page_envelope_v1(envelope)
