"""Closed contracts for source-first page structure evidence.

This module intentionally depends only on the Python standard library.  It is
an add-only boundary after the authenticated full-page reader: it can describe
source-visible evidence and geometric proposals, but it cannot claim a
statement, table, logical row, financial cell, period axis, value, mapping, or
absence.
"""

from __future__ import annotations

import json
import re
import struct
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from fractions import Fraction
from hashlib import sha256
from math import gcd, isfinite
from typing import Any

__all__ = [
    "ATOM_DISPOSITION_FORMAT_VERSION",
    "NEUTRAL_PAGE_CLAIM_BOUNDARY",
    "NEUTRAL_PAGE_FORMAT_VERSION",
    "PAGE_PROPOSAL_CLAIM_BOUNDARY",
    "PAGE_PROPOSAL_FORMAT_VERSION",
    "PROJECTION_RECEIPT_FORMAT_VERSION",
    "SOURCE_STRUCTURE_SAFETY_V1",
    "TOPOLOGY_FEATURE_FORMAT_VERSION",
    "VALUE_SEMANTICS_FORMAT_VERSION",
    "AtomAuthority",
    "AtomKind",
    "PrimaryDisposition",
    "ProposalKind",
    "SourceStructureContractError",
    "ValueSemanticStatus",
    "canonical_clone_v1",
    "canonical_json_bytes_v1",
    "canonical_json_sha256_v1",
    "decode_canonical_json_bytes_v1",
    "make_empty_page_proposal_set_v1",
    "make_page_proposal_set_v1",
    "make_source_object_id_v1",
    "make_topology_fingerprint_v1",
    "same_typed_json_v1",
    "validate_neutral_page_envelope_v1",
    "validate_page_proposal_set_v1",
    "validate_value_semantics_v1",
]


class SourceStructureContractError(ValueError):
    """A source-structure artifact crossed its closed evidence boundary."""


class AtomKind(StrEnum):
    LINE = "LINE"
    WORD = "WORD"
    EXCLUDED_EMPTY_LINE = "EXCLUDED_EMPTY_LINE"
    EXCLUDED_EMPTY_WORD = "EXCLUDED_EMPTY_WORD"
    QUARANTINED_SPAN = "QUARANTINED_SPAN"
    QUARANTINED_SUMMARY = "QUARANTINED_SUMMARY"


class AtomAuthority(StrEnum):
    AUTHENTICATED_PRIMARY = "AUTHENTICATED_PRIMARY"
    SUPPLEMENTAL_COARSE_LINE = "SUPPLEMENTAL_COARSE_LINE"
    UPSTREAM_QUARANTINE = "UPSTREAM_QUARANTINE"


class ProposalKind(StrEnum):
    SOURCE_BLOCK_CANDIDATE = "SOURCE_BLOCK_CANDIDATE"
    TABULAR_GEOMETRY_CANDIDATE = "TABULAR_GEOMETRY_CANDIDATE"
    CONTINUATION_GEOMETRY_CANDIDATE = "CONTINUATION_GEOMETRY_CANDIDATE"


class PrimaryDisposition(StrEnum):
    OWNED_BY_SOURCE_OBJECT = "OWNED_BY_SOURCE_OBJECT"
    RETAINED_UNOWNED = "RETAINED_UNOWNED"
    UPSTREAM_TERMINAL_UNRESOLVED = "UPSTREAM_TERMINAL_UNRESOLVED"
    UPSTREAM_QUARANTINED = "UPSTREAM_QUARANTINED"


class ValueSemanticStatus(StrEnum):
    OBSERVED_VALUE = "OBSERVED_VALUE"
    OBSERVED_ZERO = "OBSERVED_ZERO"
    DASH = "DASH"
    BLANK = "BLANK"
    UNRESOLVED = "UNRESOLVED"


NEUTRAL_PAGE_FORMAT_VERSION = "BANK_CORPUS_WAVE_1_ROLE_B_NEUTRAL_PAGE_EVIDENCE_V1"
NEUTRAL_PAGE_CLAIM_BOUNDARY = (
    "AUTHENTICATED_SOURCE_VISIBLE_TEXT_AND_GEOMETRY_ONLY_NO_SEMANTIC_PROMOTION"
)
PAGE_PROPOSAL_FORMAT_VERSION = "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_SOURCE_PROPOSALS_V1"
PAGE_PROPOSAL_CLAIM_BOUNDARY = (
    "SOURCE_LOCAL_GEOMETRY_PROPOSALS_ONLY_NO_STATEMENT_TABLE_ROW_CELL_OR_AXIS_CLAIM"
)
ATOM_DISPOSITION_FORMAT_VERSION = "BANK_CORPUS_WAVE_1_ROLE_B_ATOM_DISPOSITION_V1"
VALUE_SEMANTICS_FORMAT_VERSION = "BANK_CORPUS_VALUE_SEMANTICS_EVIDENCE_V1"
TOPOLOGY_FEATURE_FORMAT_VERSION = "BANK_CORPUS_SOURCE_TOPOLOGY_FEATURES_V1"
PROJECTION_RECEIPT_FORMAT_VERSION = "BANK_CORPUS_SOURCE_PROJECTION_RECEIPT_V1"

SOURCE_STRUCTURE_SAFETY_V1: dict[str, bool] = {
    "source_text_and_geometry_only": True,
    "statement_claimed": False,
    "table_claimed": False,
    "logical_rows_claimed": False,
    "financial_cells_claimed": False,
    "period_axis_claimed": False,
    "unit_axis_claimed": False,
    "scope_claimed": False,
    "value_claimed": False,
    "blank_claimed": False,
    "absence_claimed": False,
    "external_identity_metadata_used": False,
    "reference_answers_used": False,
    "template_metadata_used": False,
    "prior_period_values_used": False,
}

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_ID_RE = re.compile(r"^ssv1:[a-z][a-z0-9_]{0,39}:[0-9a-f]{64}$")
_TOPOLOGY_ID_RE = re.compile(r"^sstfv1:[0-9a-f]{64}$")
_ALLOWED_ROUTES = frozenset({"DOMINANT_RASTER_OCR", "CAUSAL_NATIVE_TEXT"})
_COMPLETE_STATUSES = frozenset({"OCR_WORD_BOX_READ_COMPLETE", "CAUSAL_NATIVE_TEXT_READ_COMPLETE"})
_TERMINAL_STATUSES = frozenset(
    {
        "UNRESOLVED_OCR_WORD_BOX_GEOMETRY",
        "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY",
        "UNRESOLVED_NATIVE_TEXT_QUALITY",
    }
)
_NATIVE_VISIBILITY_FAILURE_TYPES = frozenset(
    {"CausalNativeTextError", "RuntimeError", "ValueError"}
)
_FORBIDDEN_OUTPUT_KEY_FRAGMENTS = (
    "bank",
    "filename",
    "path",
    "role_a",
    "rolea",
    "schema",
    "reportnormid",
    "report_norm_id",
    "history",
    "historical",
    "human_review",
)
_FORBIDDEN_IDENTITY_VALUE_FRAGMENTS = (
    "bank",
    "filename",
    "path",
    "role_a",
    "rolea",
    "schema",
    "reportnormid",
    "report_norm_id",
    "history",
    "historical",
    "human_review",
    "document_id",
    "request_sha256",
    "source_sha256",
)

_TOPOLOGY_FEATURE_FIELDS = {
    "format_version",
    "evidence_mode",
    "page_orientation",
    "primary_line_count_bucket",
    "primary_word_count_bucket",
    "supplemental_line_count_bucket",
    "quarantine_count_bucket",
    "source_object_kind_sequence",
    "relation_code_sequence",
}
_TOPOLOGY_EVIDENCE_MODES = frozenset(
    {
        "OCR_PRIMARY",
        "NATIVE_PRIMARY",
        "OCR_TERMINAL_WITH_LINE_SUPPLEMENT",
        "UPSTREAM_TERMINAL_NO_TEXT",
    }
)
_TOPOLOGY_ORIENTATIONS = frozenset({"PORTRAIT", "LANDSCAPE", "SQUARE"})
_TOPOLOGY_COUNT_BUCKETS = frozenset(
    {
        "ZERO",
        "ONE",
        "TWO_TO_FOUR",
        "FIVE_TO_NINE",
        "TEN_TO_NINETEEN",
        "TWENTY_TO_FORTY_NINE",
        "FIFTY_PLUS",
    }
)
_TOPOLOGY_RELATION_CODES = frozenset(
    {
        "BBOX_CONTAINMENT",
        "DENSE_COLUMN_ALIGNMENT",
        "HORIZONTAL_GAP",
        "SAME_HORIZONTAL_BAND",
        "VERTICAL_GAP",
        "VERTICAL_SUCCESSOR",
    }
)
_PROPOSAL_EVIDENCE_CODES = frozenset(
    {
        "ADJACENT_ATOM_GEOMETRY",
        "BBOX_CONTAINS_PRIMARY_ATOMS",
        "DENSE_TABULAR_ALIGNMENT",
        "HORIZONTAL_ALIGNMENT",
        "LOCAL_GEOMETRY",
        "NEIGHBORING_PAGE_CONTINUITY_GEOMETRY",
        "VERTICAL_GAP_COHERENCE",
    }
)
_DISPOSITION_REASON_BY_KIND = {
    PrimaryDisposition.OWNED_BY_SOURCE_OBJECT: "PRIMARY_LOCAL_GEOMETRY_OWNERSHIP",
    PrimaryDisposition.RETAINED_UNOWNED: "NO_SOURCE_OBJECT_OWNERSHIP_PROPOSED",
    PrimaryDisposition.UPSTREAM_TERMINAL_UNRESOLVED: "UPSTREAM_TERMINAL_RETAINED",
    PrimaryDisposition.UPSTREAM_QUARANTINED: "UPSTREAM_QUARANTINE_RETAINED",
}
_UNRESOLVED_REASON_CODES = frozenset(
    {
        "AMBIGUOUS_VISIBLE_TOKEN",
        "CONFLICTING_NUMERIC_READER_EVIDENCE",
        "OCR_TOKEN_MISSING_IN_BOUNDED_REGION",
        "TOKEN_NOT_OBSERVED",
        "UNREADABLE_SOURCE_PIXELS",
    }
)

_ENVELOPE_FIELDS = {
    "format_version",
    "claim_boundary",
    "source_locator",
    "source_local_page_id",
    "route",
    "upstream_status",
    "terminal",
    "terminal_reason",
    "coordinate_authority",
    "evidence_refs",
    "atoms",
    "projection_receipt",
    "metrics",
    "safety",
}
_SOURCE_LOCATOR_FIELDS = {
    "source_sha256",
    "source_size_bytes",
    "physical_page",
    "request_sha256",
}
_EVIDENCE_REF_FIELDS = {
    "kind",
    "sha256",
    "size_bytes",
    "media_type",
    "upstream_reference_sha256",
}
_OCR_COORDINATE_AUTHORITY_FIELDS = {
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
_NATIVE_COORDINATE_AUTHORITY = {
    "canonical_coordinate_system": "UNROTATED_PDF_MILLI_POINTS_TOP_LEFT",
    "coordinate_unit": "MILLI_POINT",
    "geometry_source": "PYMUPDF_NATIVE_TEXT_WORD_GEOMETRY",
    "pdf_rotation_applied_to_coordinates": False,
}
_ATOM_FIELDS = {
    "source_local_id",
    "kind",
    "authority",
    "raw_text",
    "raw_text_sha256",
    "quarantine_summary",
    "quarantine_payload_sha256",
    "score",
    "score_kind",
    "canonical_bbox_mpt",
    "canonical_polygon_mpt",
    "pixel_bbox",
    "pixel_polygon",
    "pixel_geometry_kind",
    "upstream_locator",
}
_NATIVE_QUARANTINE_SUMMARY_FIELDS = {
    "kind",
    "excluded_text_sha256",
    "nonwhitespace_character_count",
    "color",
    "alpha",
    "render_sequence",
    "occluding_sequence",
    "occluding_object_type",
    "reason",
}
_WORD_AXIS_QUARANTINE_SUMMARY_FIELDS = {
    "kind",
    "reason",
    "ordered_subdivision_counts_by_line",
    "total_subdivision_count",
    "word_axes_sha256",
    "raw_provider_payload_sha256",
}
_EMPTY_AXIS_QUARANTINE_SUMMARY_FIELDS = {
    "kind",
    "axis_kind",
    "excluded_text_sha256",
    "reason",
}
_METRIC_FIELDS = {
    "atom_count",
    "upstream_line_axis_count",
    "upstream_word_axis_count",
    "upstream_quarantined_span_axis_count",
    "primary_line_count",
    "primary_word_count",
    "excluded_empty_line_axis_count",
    "excluded_empty_word_axis_count",
    "supplemental_line_count",
    "supplement_validated_line_axis_count",
    "supplement_excluded_empty_line_axis_count",
    "supplement_quarantined_subdivision_count",
    "quarantined_atom_count",
}
_PROJECTION_RECEIPT_FIELDS = {
    "format_version",
    "result_ref_sha256",
    "result_projection_sha256",
    "coordinate_authority_sha256",
    "upstream_line_axis_sha256",
    "upstream_word_axis_sha256",
    "upstream_quarantine_axis_sha256",
    "atom_sequence_sha256",
    "atom_id_sequence_sha256",
    "supplement_ref_sha256",
    "supplement_projection_sha256",
    "supplement_evidence_projection_sha256",
    "upstream_line_axis_count",
    "upstream_word_axis_count",
    "upstream_quarantined_span_axis_count",
    "excluded_empty_line_axis_count",
    "excluded_empty_word_axis_count",
    "supplement_validated_line_axis_count",
    "supplement_accepted_line_count",
    "supplement_excluded_empty_line_axis_count",
    "supplement_quarantined_subdivision_count",
}
_PROPOSAL_SET_FIELDS = {
    "format_version",
    "claim_boundary",
    "source_local_page_id",
    "neutral_page_sha256",
    "proposals",
    "dispositions",
    "safety",
}
_PROPOSAL_FIELDS = {
    "source_local_id",
    "kind",
    "canonical_bbox_mpt",
    "primary_atom_ids",
    "supporting_atom_ids",
    "evidence_codes",
}
_DISPOSITION_FIELDS = {
    "format_version",
    "source_atom_id",
    "primary_disposition",
    "source_object_id",
    "reason_code",
}
_VALUE_FIELDS = {
    "format_version",
    "status",
    "raw_token",
    "normalized_value",
    "source_region_id",
    "bounded_region_bbox_mpt",
    "visible_numeric_zero_verified",
    "visible_dash_verified",
    "pixel_blank_verified",
    "pixel_evidence_ref",
    "unresolved_reason",
}


def _validate_json_tree(value: Any, *, label: str = "value") -> None:
    value_type = type(value)
    if value is None or value_type in {bool, int, str}:
        if value_type is str:
            try:
                value.encode("utf-8")
            except UnicodeEncodeError as error:
                raise SourceStructureContractError(f"{label} contains invalid Unicode") from error
        return
    if value_type is float:
        if not isfinite(value):
            raise SourceStructureContractError(f"{label} contains a non-finite number")
        return
    if value_type is list:
        for index, item in enumerate(value):
            _validate_json_tree(item, label=f"{label}[{index}]")
        return
    if value_type is dict:
        if any(type(key) is not str for key in value):
            raise SourceStructureContractError(f"{label} has a non-string object key")
        for key, item in value.items():
            _validate_json_tree(item, label=f"{label}.{key}")
        return
    raise SourceStructureContractError(f"{label} contains unsupported type {value_type.__name__}")


def canonical_json_bytes_v1(value: Any) -> bytes:
    """Serialize exact JSON types deterministically, including a final newline."""

    _validate_json_tree(value)
    try:
        rendered = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        return (rendered + "\n").encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as error:
        raise SourceStructureContractError("value is not canonical JSON") from error


def canonical_json_sha256_v1(value: Any) -> str:
    return sha256(canonical_json_bytes_v1(value)).hexdigest()


def same_typed_json_v1(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(
            same_typed_json_v1(left[key], right[key]) for key in left
        )
    if type(left) is list:
        return len(left) == len(right) and all(
            same_typed_json_v1(a, b) for a, b in zip(left, right, strict=True)
        )
    if type(left) is float:
        # JSON spelling preserves negative zero (``-0.0``), so typed equality
        # must preserve its IEEE-754 sign bit as well.  Ordinary ``==`` does
        # not: ``-0.0 == 0.0`` is true.
        return struct.pack(">d", left) == struct.pack(">d", right)
    return bool(left == right)


def canonical_clone_v1(value: Any) -> Any:
    return decode_canonical_json_bytes_v1(canonical_json_bytes_v1(value))


def decode_canonical_json_bytes_v1(payload: bytes) -> Any:
    if type(payload) is not bytes:
        raise SourceStructureContractError("canonical JSON payload must be bytes")

    def reject_constant(value: str) -> None:
        raise SourceStructureContractError(f"canonical JSON contains {value}")

    def closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise SourceStructureContractError("canonical JSON contains a duplicate key")
            result[key] = value
        return result

    try:
        decoded = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=closed_object,
            parse_constant=reject_constant,
        )
    except SourceStructureContractError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SourceStructureContractError("canonical JSON payload cannot be decoded") from error
    if canonical_json_bytes_v1(decoded) != payload:
        raise SourceStructureContractError("JSON bytes are not in canonical V1 form")
    return decoded


def _require_exact_dict(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise SourceStructureContractError(f"{label} fields drifted")
    return value


def _require_sha256(value: Any, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise SourceStructureContractError(f"{label} must be a lowercase SHA-256")
    return value


def _require_nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise SourceStructureContractError(f"{label} must be a nonnegative integer")
    return value


def _require_positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise SourceStructureContractError(f"{label} must be a positive integer")
    return value


def _require_source_id(value: Any, label: str) -> str:
    if type(value) is not str or _SOURCE_ID_RE.fullmatch(value) is None:
        raise SourceStructureContractError(f"{label} is not a V1 source-local identity")
    return value


def _validate_bbox(value: Any, label: str, *, positive_area: bool = True) -> list[int]:
    if type(value) is not list or len(value) != 4 or any(type(item) is not int for item in value):
        raise SourceStructureContractError(f"{label} must contain four integer millipoints")
    x0, y0, x1, y1 = value
    if (positive_area and (x0 >= x1 or y0 >= y1)) or (not positive_area and (x0 > x1 or y0 > y1)):
        raise SourceStructureContractError(f"{label} has invalid geometry")
    return value


def _validate_polygon(value: Any, label: str) -> list[list[int]]:
    if type(value) is not list or len(value) < 4:
        raise SourceStructureContractError(f"{label} must contain at least four points")
    for point in value:
        if (
            type(point) is not list
            or len(point) != 2
            or any(type(item) is not int for item in point)
        ):
            raise SourceStructureContractError(f"{label} points must be integer pairs")
    area_twice = abs(
        sum(
            value[index][0] * value[(index + 1) % len(value)][1]
            - value[(index + 1) % len(value)][0] * value[index][1]
            for index in range(len(value))
        )
    )
    if area_twice == 0:
        raise SourceStructureContractError(f"{label} is degenerate")
    return value


def _require_finite_number(value: Any, label: str) -> int | float:
    if type(value) not in {int, float} or not isfinite(value):
        raise SourceStructureContractError(f"{label} must be a finite non-boolean number")
    return value


def _validate_numeric_bbox(
    value: Any,
    label: str,
    *,
    width: int | None = None,
    height: int | None = None,
) -> list[int | float]:
    if type(value) is not list or len(value) != 4:
        raise SourceStructureContractError(f"{label} must contain four finite coordinates")
    coordinates = [_require_finite_number(item, label) for item in value]
    if not coordinates[0] < coordinates[2] or not coordinates[1] < coordinates[3]:
        raise SourceStructureContractError(f"{label} must have positive area")
    if (
        width is not None
        and height is not None
        and not (
            0 <= coordinates[0] < coordinates[2] <= width
            and 0 <= coordinates[1] < coordinates[3] <= height
        )
    ):
        raise SourceStructureContractError(f"{label} lies outside the rendered page")
    return coordinates


def _validate_numeric_polygon(
    value: Any,
    label: str,
    *,
    width: int | None = None,
    height: int | None = None,
) -> list[list[int | float]]:
    if type(value) is not list or len(value) != 4:
        raise SourceStructureContractError(f"{label} must be an ordered quadrilateral")
    polygon: list[list[int | float]] = []
    for point in value:
        if type(point) is not list or len(point) != 2:
            raise SourceStructureContractError(f"{label} point shape drifted")
        x = _require_finite_number(point[0], f"{label} x")
        y = _require_finite_number(point[1], f"{label} y")
        if width is not None and height is not None and not (0 <= x <= width and 0 <= y <= height):
            raise SourceStructureContractError(f"{label} lies outside the rendered page")
        polygon.append([x, y])
    area_twice = abs(
        sum(
            polygon[index][0] * polygon[(index + 1) % 4][1]
            - polygon[(index + 1) % 4][0] * polygon[index][1]
            for index in range(4)
        )
    )
    if area_twice == 0:
        raise SourceStructureContractError(f"{label} is degenerate")
    return polygon


def _rational(value: Any, label: str) -> Fraction:
    item = _require_exact_dict(value, {"numerator", "denominator"}, label)
    numerator = item["numerator"]
    denominator = item["denominator"]
    if type(numerator) is not int or type(denominator) is not int or denominator <= 0:
        raise SourceStructureContractError(f"{label} rational coefficient drifted")
    if gcd(abs(numerator), denominator) != 1:
        raise SourceStructureContractError(f"{label} rational coefficient is not reduced")
    return Fraction(numerator, denominator)


def _rational_matrix(value: Any, label: str) -> tuple[tuple[Fraction, ...], ...]:
    if (
        type(value) is not list
        or len(value) != 3
        or any(type(row) is not list or len(row) != 3 for row in value)
    ):
        raise SourceStructureContractError(f"{label} matrix shape drifted")
    return tuple(
        tuple(
            _rational(item, f"{label}[{row_index}][{column_index}]")
            for column_index, item in enumerate(row)
        )
        for row_index, row in enumerate(value)
    )


def _matrix_multiply(
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


def _inverse_affine_matrix(
    matrix: tuple[tuple[Fraction, ...], ...],
) -> tuple[tuple[Fraction, ...], ...]:
    a, c, e = matrix[0]
    b, d, f = matrix[1]
    if matrix[2] != (Fraction(0), Fraction(0), Fraction(1)):
        raise SourceStructureContractError("coordinate matrix is not affine")
    determinant = a * d - b * c
    if determinant == 0:
        raise SourceStructureContractError("coordinate matrix is singular")
    return (
        (d / determinant, -c / determinant, (c * f - d * e) / determinant),
        (-b / determinant, a / determinant, (b * e - a * f) / determinant),
        (Fraction(0), Fraction(0), Fraction(1)),
    )


def _validate_coordinate_authority(value: Any, *, route: str) -> dict[str, Any]:
    if route == "CAUSAL_NATIVE_TEXT":
        if not same_typed_json_v1(value, _NATIVE_COORDINATE_AUTHORITY):
            raise SourceStructureContractError("native coordinate authority drifted")
        return value
    authority = _require_exact_dict(
        value,
        _OCR_COORDINATE_AUTHORITY_FIELDS,
        "OCR coordinate authority",
    )
    expected_strings = {
        "matrix_convention": "COLUMN_VECTOR_3X3_RATIONAL",
        "pixel_coordinate_system": "DISPLAYED_PAGE_RASTER_PIXELS_TOP_LEFT",
        "displayed_coordinate_system": "DISPLAYED_PDF_MILLI_POINTS_TOP_LEFT",
        "canonical_coordinate_system": "UNROTATED_PDF_MILLI_POINTS_TOP_LEFT",
        "canonical_origin": "UNROTATED_CROP_BOX_TOP_LEFT_RELATIVE",
    }
    if any(authority[key] != expected for key, expected in expected_strings.items()):
        raise SourceStructureContractError("OCR coordinate-system semantics drifted")
    dimensions: dict[str, tuple[int, int]] = {}
    for field in (
        "pixel_dimensions",
        "displayed_dimensions_mpt",
        "unrotated_dimensions_mpt",
    ):
        item = authority[field]
        if type(item) is not list or len(item) != 2:
            raise SourceStructureContractError(f"OCR {field} drifted")
        dimensions[field] = (
            _require_positive_int(item[0], f"OCR {field} width"),
            _require_positive_int(item[1], f"OCR {field} height"),
        )
    rotation = authority["pdf_rotation_degrees"]
    if type(rotation) is not int or rotation not in {0, 90, 180, 270}:
        raise SourceStructureContractError("OCR PDF rotation drifted")
    pixel_width, pixel_height = dimensions["pixel_dimensions"]
    displayed_width, displayed_height = dimensions["displayed_dimensions_mpt"]
    unrotated_width, unrotated_height = dimensions["unrotated_dimensions_mpt"]
    expected_displayed = (
        (unrotated_width, unrotated_height)
        if rotation in {0, 180}
        else (unrotated_height, unrotated_width)
    )
    if (displayed_width, displayed_height) != expected_displayed:
        raise SourceStructureContractError(
            "OCR displayed/unrotated dimensions disagree with rotation"
        )
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
    observed_pixel_to_displayed = _rational_matrix(
        authority["pixel_to_displayed_mpt"], "pixel-to-displayed"
    )
    observed_displayed_to_unrotated = _rational_matrix(
        authority["displayed_mpt_to_unrotated_mpt"], "displayed-to-unrotated"
    )
    observed_pixel_to_unrotated = _rational_matrix(
        authority["pixel_to_unrotated_mpt"], "pixel-to-unrotated"
    )
    observed_unrotated_to_pixel = _rational_matrix(
        authority["unrotated_mpt_to_pixel"], "unrotated-to-pixel"
    )
    expected_pixel_to_unrotated = _matrix_multiply(
        displayed_to_unrotated,
        pixel_to_displayed,
    )
    if (
        observed_pixel_to_displayed != pixel_to_displayed
        or observed_displayed_to_unrotated != displayed_to_unrotated
        or observed_pixel_to_unrotated != expected_pixel_to_unrotated
        or observed_unrotated_to_pixel != _inverse_affine_matrix(expected_pixel_to_unrotated)
    ):
        raise SourceStructureContractError("OCR exact coordinate transform drifted")
    return authority


def _round_fraction_half_away(value: Fraction) -> int:
    sign = -1 if value < 0 else 1
    absolute = abs(value)
    quotient, remainder = divmod(absolute.numerator, absolute.denominator)
    return sign * (quotient + (2 * remainder >= absolute.denominator))


def _transform_pixel_polygon(
    polygon: list[list[int | float]],
    authority: dict[str, Any],
) -> list[list[int]]:
    matrix = _rational_matrix(authority["pixel_to_unrotated_mpt"], "pixel-to-unrotated")
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


def _polygon_bbox(polygon: Sequence[Sequence[int]]) -> list[int]:
    return [
        min(point[0] for point in polygon),
        min(point[1] for point in polygon),
        max(point[0] for point in polygon),
        max(point[1] for point in polygon),
    ]


def _reject_forbidden_output_keys(value: Any, *, label: str) -> None:
    if type(value) is list:
        for index, item in enumerate(value):
            _reject_forbidden_output_keys(item, label=f"{label}[{index}]")
        return
    if type(value) is not dict:
        return
    for key, item in value.items():
        folded = key.casefold()
        if any(fragment in folded for fragment in _FORBIDDEN_OUTPUT_KEY_FRAGMENTS):
            raise SourceStructureContractError(f"{label} contains forbidden field {key!r}")
        _reject_forbidden_output_keys(item, label=f"{label}.{key}")


def make_source_object_id_v1(namespace: str, identity_payload: Mapping[str, Any]) -> str:
    """Bind an ID to its page/request provenance and exact source-local payload."""

    if type(namespace) is not str or re.fullmatch(r"[a-z][a-z0-9_]{0,39}", namespace) is None:
        raise SourceStructureContractError("source identity namespace is invalid")
    if type(identity_payload) is not dict:
        raise SourceStructureContractError("source identity payload must be a plain object")
    required_binding = {"source_local_page_id", "request_sha256"}
    if not required_binding <= set(identity_payload):
        raise SourceStructureContractError("source identity payload lacks page/request binding")
    _require_source_id(identity_payload["source_local_page_id"], "source page binding")
    _require_sha256(identity_payload["request_sha256"], "request binding")
    _validate_json_tree(identity_payload, label="source identity payload")
    return f"ssv1:{namespace}:{canonical_json_sha256_v1(identity_payload)}"


def make_topology_fingerprint_v1(feature_payload: Mapping[str, Any]) -> str:
    """Hash one closed, identity-free topology feature vocabulary.

    V1 deliberately accepts categorical topology only.  Absolute boxes, page
    numbers, hashes, labels, paths, bank identities, schema identities, and
    arbitrary caller-defined feature names cannot enter a clustering key.
    """

    if type(feature_payload) is not dict:
        raise SourceStructureContractError("topology fingerprint payload must be a plain object")

    def reject_identity_content(value: Any, *, label: str) -> None:
        if type(value) is list:
            for index, item in enumerate(value):
                reject_identity_content(item, label=f"{label}[{index}]")
            return
        if type(value) is dict:
            for key, item in value.items():
                if label == "topology fingerprint" and key == "format_version":
                    continue
                folded_key = key.casefold()
                if any(fragment in folded_key for fragment in _FORBIDDEN_IDENTITY_VALUE_FRAGMENTS):
                    raise SourceStructureContractError(
                        f"topology fingerprint contains forbidden identity/reference key {key!r}"
                    )
                reject_identity_content(item, label=f"{label}.{key}")
            return
        if type(value) is str:
            folded_value = value.casefold()
            if (
                any(fragment in folded_value for fragment in _FORBIDDEN_IDENTITY_VALUE_FRAGMENTS)
                or re.search(r"(?:^|[^0-9a-f])[0-9a-f]{64}(?:$|[^0-9a-f])", folded_value)
                or "sha256:" in folded_value
                or folded_value.startswith(("/", "./", "../", "file:", "s3:", "http:"))
            ):
                raise SourceStructureContractError(
                    f"{label} contains forbidden identity/reference content"
                )

    reject_identity_content(feature_payload, label="topology fingerprint")
    features = _require_exact_dict(
        feature_payload,
        _TOPOLOGY_FEATURE_FIELDS,
        "topology fingerprint feature schema",
    )
    if features["format_version"] != TOPOLOGY_FEATURE_FORMAT_VERSION:
        raise SourceStructureContractError("topology fingerprint format drifted")
    if features["evidence_mode"] not in _TOPOLOGY_EVIDENCE_MODES:
        raise SourceStructureContractError("topology evidence mode drifted")
    if features["page_orientation"] not in _TOPOLOGY_ORIENTATIONS:
        raise SourceStructureContractError("topology page orientation drifted")
    for field in (
        "primary_line_count_bucket",
        "primary_word_count_bucket",
        "supplemental_line_count_bucket",
        "quarantine_count_bucket",
    ):
        if features[field] not in _TOPOLOGY_COUNT_BUCKETS:
            raise SourceStructureContractError(f"topology {field} drifted")
    kinds = features["source_object_kind_sequence"]
    relations = features["relation_code_sequence"]
    if type(kinds) is not list or any(
        type(kind) is not str or kind not in {item.value for item in ProposalKind} for kind in kinds
    ):
        raise SourceStructureContractError("topology source-object kind sequence drifted")
    if type(relations) is not list or any(
        type(code) is not str or code not in _TOPOLOGY_RELATION_CODES for code in relations
    ):
        raise SourceStructureContractError("topology relation-code sequence drifted")
    _validate_json_tree(features, label="topology fingerprint")
    return f"sstfv1:{canonical_json_sha256_v1(features)}"


def _validate_source_locator(value: Any) -> dict[str, Any]:
    locator = _require_exact_dict(value, _SOURCE_LOCATOR_FIELDS, "source locator")
    _require_sha256(locator["source_sha256"], "source identity")
    _require_positive_int(locator["source_size_bytes"], "source size")
    _require_positive_int(locator["physical_page"], "physical page")
    _require_sha256(locator["request_sha256"], "request identity")
    return locator


def _validate_evidence_ref(value: Any) -> dict[str, Any]:
    reference = _require_exact_dict(value, _EVIDENCE_REF_FIELDS, "evidence reference")
    if reference["kind"] not in {"RENDER", "BACKEND_PAYLOAD", "RESULT", "LINE_SUPPLEMENT"}:
        raise SourceStructureContractError("evidence reference kind drifted")
    _require_sha256(reference["sha256"], "evidence object identity")
    _require_positive_int(reference["size_bytes"], "evidence object size")
    if reference["media_type"] not in {"image/png", "application/json"}:
        raise SourceStructureContractError("evidence reference media type drifted")
    _require_sha256(reference["upstream_reference_sha256"], "upstream reference identity")
    return reference


def _validate_atom(
    value: Any,
    *,
    page_id: str,
    request_sha256: str,
    route: str,
    coordinate_authority: dict[str, Any],
) -> dict[str, Any]:
    atom = _require_exact_dict(value, _ATOM_FIELDS, "evidence atom")
    atom_id = _require_source_id(atom["source_local_id"], "evidence atom identity")
    try:
        kind = AtomKind(atom["kind"])
        authority = AtomAuthority(atom["authority"])
    except (TypeError, ValueError) as error:
        raise SourceStructureContractError("evidence atom kind/authority drifted") from error

    locator_fields = {
        "OCR_LINE_INDEX": {"kind", "line_index"},
        "OCR_WORD_INDEX": {"kind", "line_index", "word_index"},
        "NATIVE_LINE_INDEX": {"kind", "block_number", "line_number"},
        "NATIVE_WORD_INDEX": {"kind", "block_number", "line_number", "word_number"},
        "NATIVE_QUARANTINED_SPAN_INDEX": {
            "kind",
            "block_number",
            "line_number",
            "span_number",
        },
        "SUPPLEMENT_LINE_INDEX": {"kind", "line_index"},
        "SUPPLEMENT_WORD_AXIS_QUARANTINE": {"kind"},
    }
    locator = atom["upstream_locator"]
    if type(locator) is not dict or locator.get("kind") not in locator_fields:
        raise SourceStructureContractError("evidence atom upstream locator drifted")
    locator_kind = locator["kind"]
    _require_exact_dict(locator, locator_fields[locator_kind], "evidence atom locator")
    for key, item in locator.items():
        if key != "kind":
            _require_nonnegative_int(item, f"evidence atom locator {key}")

    expected_kind_by_locator = {
        "OCR_LINE_INDEX": {AtomKind.LINE, AtomKind.EXCLUDED_EMPTY_LINE},
        "OCR_WORD_INDEX": {AtomKind.WORD, AtomKind.EXCLUDED_EMPTY_WORD},
        "NATIVE_LINE_INDEX": {AtomKind.LINE},
        "NATIVE_WORD_INDEX": {AtomKind.WORD},
        "NATIVE_QUARANTINED_SPAN_INDEX": {AtomKind.QUARANTINED_SPAN},
        "SUPPLEMENT_LINE_INDEX": {AtomKind.LINE},
        "SUPPLEMENT_WORD_AXIS_QUARANTINE": {AtomKind.QUARANTINED_SUMMARY},
    }
    if kind not in expected_kind_by_locator[locator_kind]:
        raise SourceStructureContractError("evidence atom kind/locator drifted")
    if locator_kind.startswith("OCR_") and route != "DOMINANT_RASTER_OCR":
        raise SourceStructureContractError("OCR atom appeared on a native route")
    if locator_kind.startswith("NATIVE_") and route != "CAUSAL_NATIVE_TEXT":
        raise SourceStructureContractError("native atom appeared on an OCR route")
    if locator_kind.startswith("SUPPLEMENT_") and route != "DOMINANT_RASTER_OCR":
        raise SourceStructureContractError("supplement atom appeared on a native route")

    quarantine_kind = kind in {
        AtomKind.EXCLUDED_EMPTY_LINE,
        AtomKind.EXCLUDED_EMPTY_WORD,
        AtomKind.QUARANTINED_SPAN,
        AtomKind.QUARANTINED_SUMMARY,
    }
    expected_authority = (
        AtomAuthority.UPSTREAM_QUARANTINE
        if quarantine_kind
        else AtomAuthority.SUPPLEMENTAL_COARSE_LINE
        if locator_kind == "SUPPLEMENT_LINE_INDEX"
        else AtomAuthority.AUTHENTICATED_PRIMARY
    )
    if authority is not expected_authority:
        raise SourceStructureContractError("evidence atom authority drifted")

    raw_text = atom["raw_text"]
    text_sha = atom["raw_text_sha256"]
    quarantine_summary = atom["quarantine_summary"]
    quarantine_payload_sha = atom["quarantine_payload_sha256"]
    if not quarantine_kind:
        if type(raw_text) is not str or raw_text == "":
            raise SourceStructureContractError(
                "visible evidence atom text must satisfy exact nonempty NO_TRIM eligibility"
            )
        try:
            raw_text.encode("utf-8")
        except UnicodeEncodeError as error:
            raise SourceStructureContractError(
                "evidence atom text contains invalid Unicode"
            ) from error
        _require_sha256(text_sha, "evidence atom text identity")
        if sha256(raw_text.encode("utf-8")).hexdigest() != text_sha:
            raise SourceStructureContractError("evidence atom text identity drifted")
        if quarantine_summary is not None or quarantine_payload_sha is not None:
            raise SourceStructureContractError("visible evidence atom carried quarantine data")
    else:
        if raw_text is not None or text_sha is not None:
            raise SourceStructureContractError("quarantined atom exposed or promoted text")
        if kind in {AtomKind.EXCLUDED_EMPTY_LINE, AtomKind.EXCLUDED_EMPTY_WORD}:
            summary = _require_exact_dict(
                quarantine_summary,
                _EMPTY_AXIS_QUARANTINE_SUMMARY_FIELDS,
                "empty-axis quarantine summary",
            )
            expected_axis = "LINE" if kind is AtomKind.EXCLUDED_EMPTY_LINE else "WORD"
            if (
                summary["kind"] != "EMPTY_TEXT_AXIS_EXCLUSION"
                or summary["axis_kind"] != expected_axis
                or summary["excluded_text_sha256"] != sha256(b"").hexdigest()
                or summary["reason"] != "EXACT_EMPTY_STRING_NOT_PROMOTED"
            ):
                raise SourceStructureContractError("empty-axis quarantine summary drifted")
        elif kind is AtomKind.QUARANTINED_SPAN:
            summary = _require_exact_dict(
                quarantine_summary,
                _NATIVE_QUARANTINE_SUMMARY_FIELDS,
                "native quarantine summary",
            )
            if summary["kind"] != "NATIVE_EXCLUDED_SPAN":
                raise SourceStructureContractError("native quarantine summary kind drifted")
            _require_sha256(summary["excluded_text_sha256"], "excluded text identity")
            _require_nonnegative_int(
                summary["nonwhitespace_character_count"],
                "quarantine character count",
            )
            _require_nonnegative_int(summary["render_sequence"], "quarantine render sequence")
            if type(summary["color"]) is not int or not 0 <= summary["color"] <= 0xFFFFFF:
                raise SourceStructureContractError("quarantine summary color drifted")
            if type(summary["alpha"]) is not int or not 0 <= summary["alpha"] <= 255:
                raise SourceStructureContractError("quarantine summary alpha drifted")
            if summary["occluding_sequence"] is not None:
                _require_nonnegative_int(
                    summary["occluding_sequence"], "quarantine occluding sequence"
                )
            if (
                summary["occluding_object_type"] is not None
                and type(summary["occluding_object_type"]) is not str
            ):
                raise SourceStructureContractError("quarantine object type drifted")
            if type(summary["reason"]) is not str or not summary["reason"]:
                raise SourceStructureContractError("native quarantine reason drifted")
        else:
            summary = _require_exact_dict(
                quarantine_summary,
                _WORD_AXIS_QUARANTINE_SUMMARY_FIELDS,
                "word-axis quarantine summary",
            )
            if (
                summary["kind"] != "TERMINAL_WORD_AXIS_QUARANTINE"
                or summary["reason"] != "BOUNDED_WORD_BOX_NORMALIZATION_INVARIANT_FAILED"
            ):
                raise SourceStructureContractError("word-axis quarantine summary kind drifted")
            counts = summary["ordered_subdivision_counts_by_line"]
            if type(counts) is not list:
                raise SourceStructureContractError("word-axis quarantine counts drifted")
            for count in counts:
                _require_nonnegative_int(count, "word-axis subdivision count")
            if summary["total_subdivision_count"] != sum(counts):
                raise SourceStructureContractError("word-axis quarantine total drifted")
            _require_sha256(summary["word_axes_sha256"], "word-axis quarantine identity")
            _require_sha256(summary["raw_provider_payload_sha256"], "raw provider payload identity")

    score = atom["score"]
    if score is not None:
        _require_finite_number(score, "evidence atom score")
        if not 0 <= score <= 1:
            raise SourceStructureContractError("evidence atom score lies outside [0, 1]")
    score_kind = atom["score_kind"]
    expected_score = {
        "OCR_LINE_INDEX": ("PP_OCRV6_LINE_RECOGNITION_SCORE", True),
        "OCR_WORD_INDEX": ("PP_OCRV6_LINE_SCORE_ONLY", False),
        "NATIVE_LINE_INDEX": ("NATIVE_TEXT_NO_RECOGNITION_SCORE", False),
        "NATIVE_WORD_INDEX": ("NATIVE_TEXT_NO_RECOGNITION_SCORE", False),
        "NATIVE_QUARANTINED_SPAN_INDEX": ("UPSTREAM_QUARANTINE_HASH_ONLY", False),
        "SUPPLEMENT_LINE_INDEX": ("PP_OCRV6_LINE_RECOGNITION_SCORE", True),
        "SUPPLEMENT_WORD_AXIS_QUARANTINE": ("UPSTREAM_QUARANTINE_HASH_ONLY", False),
    }[locator_kind]
    if (
        score_kind != expected_score[0]
        or (score is not None) is not expected_score[1]
        or (expected_score[1] and type(score) is not float)
    ):
        raise SourceStructureContractError("evidence atom score semantics drifted")

    bbox = atom["canonical_bbox_mpt"]
    polygon = atom["canonical_polygon_mpt"]
    pixel_bbox = atom["pixel_bbox"]
    pixel_polygon = atom["pixel_polygon"]
    pixel_geometry_kind = atom["pixel_geometry_kind"]
    expected_pixel_kind = {
        "OCR_LINE_INDEX": "RAW_PROVIDER_LINE_REC_BOX_AND_POLYGON",
        "OCR_WORD_INDEX": "BOUNDED_NORMALIZED_WORD_BOX",
        "NATIVE_LINE_INDEX": "NOT_APPLICABLE",
        "NATIVE_WORD_INDEX": "NOT_APPLICABLE",
        "NATIVE_QUARANTINED_SPAN_INDEX": "NOT_APPLICABLE",
        "SUPPLEMENT_LINE_INDEX": "RAW_PROVIDER_LINE_REC_BOX_AND_POLYGON",
        "SUPPLEMENT_WORD_AXIS_QUARANTINE": "NOT_APPLICABLE",
    }[locator_kind]
    if pixel_geometry_kind != expected_pixel_kind:
        raise SourceStructureContractError("evidence atom pixel geometry authority drifted")

    if locator_kind == "SUPPLEMENT_WORD_AXIS_QUARANTINE":
        if any(item is not None for item in (bbox, polygon, pixel_bbox, pixel_polygon)):
            raise SourceStructureContractError("word-axis quarantine exposed hidden geometry")
    elif locator_kind.startswith("NATIVE_"):
        native_bbox = _validate_bbox(bbox, "native evidence atom bbox", positive_area=False)
        if any(coordinate < 0 for coordinate in native_bbox):
            raise SourceStructureContractError(
                "native evidence atom lies outside the nonnegative canonical page domain"
            )
        if polygon is not None or pixel_bbox is not None or pixel_polygon is not None:
            raise SourceStructureContractError("native evidence atom exposed non-native geometry")
    else:
        pixel_width, pixel_height = coordinate_authority["pixel_dimensions"]
        unrotated_width, unrotated_height = coordinate_authority["unrotated_dimensions_mpt"]
        raw_box = _validate_numeric_bbox(
            pixel_bbox,
            "evidence atom pixel bbox",
            width=pixel_width,
            height=pixel_height,
        )
        if locator_kind == "OCR_WORD_INDEX":
            if pixel_polygon is not None:
                raise SourceStructureContractError("normalized OCR word exposed a raw polygon")
            raw_polygon = [
                [raw_box[0], raw_box[1]],
                [raw_box[2], raw_box[1]],
                [raw_box[2], raw_box[3]],
                [raw_box[0], raw_box[3]],
            ]
        else:
            raw_polygon = _validate_numeric_polygon(
                pixel_polygon,
                "evidence atom pixel polygon",
                width=pixel_width,
                height=pixel_height,
            )
        canonical_polygon = _validate_polygon(polygon, "evidence atom canonical polygon")
        canonical_bbox = _validate_bbox(bbox, "evidence atom canonical bbox")
        if not same_typed_json_v1(
            canonical_polygon,
            _transform_pixel_polygon(raw_polygon, coordinate_authority),
        ):
            raise SourceStructureContractError("evidence atom canonical polygon transform drifted")
        if locator_kind == "SUPPLEMENT_LINE_INDEX":
            box_polygon = [
                [raw_box[0], raw_box[1]],
                [raw_box[2], raw_box[1]],
                [raw_box[2], raw_box[3]],
                [raw_box[0], raw_box[3]],
            ]
            expected_bbox = _polygon_bbox(
                _transform_pixel_polygon(box_polygon, coordinate_authority)
            )
            if canonical_bbox != expected_bbox or any(
                not canonical_bbox[0] <= point[0] <= canonical_bbox[2]
                or not canonical_bbox[1] <= point[1] <= canonical_bbox[3]
                for point in canonical_polygon
            ):
                raise SourceStructureContractError(
                    "supplement polygon is not contained within canonical rec-box authority"
                )
        elif canonical_bbox != _polygon_bbox(canonical_polygon):
            raise SourceStructureContractError("evidence atom polygon/bbox drifted")
        if not (
            0 <= canonical_bbox[0] < canonical_bbox[2] <= unrotated_width
            and 0 <= canonical_bbox[1] < canonical_bbox[3] <= unrotated_height
        ) or any(
            not 0 <= point[0] <= unrotated_width or not 0 <= point[1] <= unrotated_height
            for point in canonical_polygon
        ):
            raise SourceStructureContractError("evidence atom canonical geometry lies outside page")

    payload_without_identity = {
        key: atom[key]
        for key in sorted(_ATOM_FIELDS - {"source_local_id", "quarantine_payload_sha256"})
    }
    if quarantine_kind:
        expected_quarantine_sha = canonical_json_sha256_v1(payload_without_identity)
        if (
            _require_sha256(quarantine_payload_sha, "quarantine payload identity")
            != expected_quarantine_sha
        ):
            raise SourceStructureContractError("quarantine payload identity drifted")
    elif quarantine_payload_sha is not None:
        raise SourceStructureContractError("visible evidence atom carried quarantine identity")
    identity_atom_payload = {key: atom[key] for key in sorted(_ATOM_FIELDS - {"source_local_id"})}
    expected_id = make_source_object_id_v1(
        "atom",
        {
            "source_local_page_id": page_id,
            "request_sha256": request_sha256,
            "atom_payload": identity_atom_payload,
        },
    )
    if atom_id != expected_id:
        raise SourceStructureContractError("evidence atom identity is not content/provenance-bound")
    return atom


def validate_neutral_page_envelope_v1(value: Any) -> dict[str, Any]:
    envelope = _require_exact_dict(value, _ENVELOPE_FIELDS, "neutral page envelope")
    _reject_forbidden_output_keys(envelope, label="neutral page envelope")
    if envelope["format_version"] != NEUTRAL_PAGE_FORMAT_VERSION:
        raise SourceStructureContractError("neutral page format drifted")
    if envelope["claim_boundary"] != NEUTRAL_PAGE_CLAIM_BOUNDARY:
        raise SourceStructureContractError("neutral page claim boundary drifted")
    locator = _validate_source_locator(envelope["source_locator"])
    page_id = _require_source_id(envelope["source_local_page_id"], "neutral page identity")
    route = envelope["route"]
    status = envelope["upstream_status"]
    if route not in _ALLOWED_ROUTES:
        raise SourceStructureContractError("neutral page route drifted")
    if status not in _COMPLETE_STATUSES | _TERMINAL_STATUSES:
        raise SourceStructureContractError("neutral page status drifted")
    terminal = envelope["terminal"]
    if type(terminal) is not bool or terminal != (status in _TERMINAL_STATUSES):
        raise SourceStructureContractError("neutral page terminal state drifted")
    if terminal:
        reason = envelope["terminal_reason"]
        if status == "UNRESOLVED_OCR_WORD_BOX_GEOMETRY":
            allowed = reason == "BOUNDED_WORD_BOX_NORMALIZATION_INVARIANT_FAILED"
        elif status == "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY":
            allowed = reason in _NATIVE_VISIBILITY_FAILURE_TYPES
        else:
            allowed = reason in {"NO_TEXT_LAYER", "CORRUPT_TEXT_LAYER"}
        if not allowed:
            raise SourceStructureContractError("terminal reason does not match upstream failure")
    elif envelope["terminal_reason"] is not None:
        raise SourceStructureContractError("complete page cannot carry a terminal reason")
    references = envelope["evidence_refs"]
    if type(references) is not list:
        raise SourceStructureContractError("neutral evidence references must be an array")
    for reference in references:
        _validate_evidence_ref(reference)
    ref_kinds = [reference["kind"] for reference in references]
    if len(ref_kinds) != len(set(ref_kinds)):
        raise SourceStructureContractError("neutral evidence reference accounting drifted")
    if route == "DOMINANT_RASTER_OCR":
        expected_ref_kinds = {"RENDER", "BACKEND_PAYLOAD", "RESULT"}
        if status == "UNRESOLVED_OCR_WORD_BOX_GEOMETRY" and "LINE_SUPPLEMENT" in ref_kinds:
            expected_ref_kinds.add("LINE_SUPPLEMENT")
    else:
        expected_ref_kinds = {"BACKEND_PAYLOAD", "RESULT"}
    if set(ref_kinds) != expected_ref_kinds:
        raise SourceStructureContractError(
            "neutral evidence reference set does not match route/status"
        )
    coordinate_authority = _validate_coordinate_authority(
        envelope["coordinate_authority"],
        route=route,
    )
    receipt = _require_exact_dict(
        envelope["projection_receipt"],
        _PROJECTION_RECEIPT_FIELDS,
        "upstream projection receipt",
    )
    if receipt["format_version"] != PROJECTION_RECEIPT_FORMAT_VERSION:
        raise SourceStructureContractError("upstream projection receipt format drifted")
    for field in (
        "result_ref_sha256",
        "result_projection_sha256",
        "coordinate_authority_sha256",
        "upstream_line_axis_sha256",
        "upstream_word_axis_sha256",
        "upstream_quarantine_axis_sha256",
        "atom_sequence_sha256",
        "atom_id_sequence_sha256",
        "supplement_evidence_projection_sha256",
    ):
        _require_sha256(receipt[field], f"projection receipt {field}")
    for field in (
        "upstream_line_axis_count",
        "upstream_word_axis_count",
        "upstream_quarantined_span_axis_count",
        "excluded_empty_line_axis_count",
        "excluded_empty_word_axis_count",
        "supplement_validated_line_axis_count",
        "supplement_accepted_line_count",
        "supplement_excluded_empty_line_axis_count",
        "supplement_quarantined_subdivision_count",
    ):
        _require_nonnegative_int(receipt[field], f"projection receipt {field}")
    result_reference = next(reference for reference in references if reference["kind"] == "RESULT")
    supplement_references = [
        reference for reference in references if reference["kind"] == "LINE_SUPPLEMENT"
    ]
    if (
        receipt["result_ref_sha256"] != result_reference["sha256"]
        or receipt["result_projection_sha256"] != result_reference["sha256"]
        or receipt["coordinate_authority_sha256"] != canonical_json_sha256_v1(coordinate_authority)
    ):
        raise SourceStructureContractError("upstream projection receipt binding drifted")
    if supplement_references:
        supplement_sha = supplement_references[0]["sha256"]
        if (
            receipt["supplement_ref_sha256"] != supplement_sha
            or receipt["supplement_projection_sha256"] != supplement_sha
        ):
            raise SourceStructureContractError("line-supplement projection receipt drifted")
    elif (
        receipt["supplement_ref_sha256"] is not None
        or receipt["supplement_projection_sha256"] is not None
        or any(
            receipt[field] != 0
            for field in (
                "supplement_validated_line_axis_count",
                "supplement_accepted_line_count",
                "supplement_excluded_empty_line_axis_count",
                "supplement_quarantined_subdivision_count",
            )
        )
    ):
        raise SourceStructureContractError("absent supplement carried a projection receipt")
    page_identity_payload = {
        "source_sha256": locator["source_sha256"],
        "source_size_bytes": locator["source_size_bytes"],
        "physical_page": locator["physical_page"],
        "request_sha256": locator["request_sha256"],
        "route": route,
        "upstream_status": status,
        "terminal_reason": envelope["terminal_reason"],
        "evidence_refs": references,
        "coordinate_authority_sha256": receipt["coordinate_authority_sha256"],
        "projection_source_receipt": {
            key: receipt[key]
            for key in sorted(
                _PROJECTION_RECEIPT_FIELDS - {"atom_sequence_sha256", "atom_id_sequence_sha256"}
            )
        },
    }
    expected_page_id = f"ssv1:page:{canonical_json_sha256_v1(page_identity_payload)}"
    if page_id != expected_page_id:
        raise SourceStructureContractError("neutral page identity is not provenance-bound")
    atoms = envelope["atoms"]
    if type(atoms) is not list:
        raise SourceStructureContractError("neutral page atoms must be an array")
    seen: set[str] = set()
    for atom in atoms:
        validated = _validate_atom(
            atom,
            page_id=page_id,
            request_sha256=locator["request_sha256"],
            route=route,
            coordinate_authority=coordinate_authority,
        )
        if validated["source_local_id"] in seen:
            raise SourceStructureContractError("neutral page contains a duplicate atom")
        seen.add(validated["source_local_id"])
        if terminal and validated["authority"] == AtomAuthority.AUTHENTICATED_PRIMARY:
            raise SourceStructureContractError("terminal page cannot expose accepted primary atoms")
        if not terminal and validated["authority"] == AtomAuthority.SUPPLEMENTAL_COARSE_LINE:
            raise SourceStructureContractError("complete page cannot consume a terminal supplement")

    if receipt["atom_sequence_sha256"] != canonical_json_sha256_v1(atoms) or receipt[
        "atom_id_sequence_sha256"
    ] != canonical_json_sha256_v1([atom["source_local_id"] for atom in atoms]):
        raise SourceStructureContractError("neutral atom sequence/content receipt drifted")

    base_lines = [
        atom
        for atom in atoms
        if atom["upstream_locator"]["kind"] in {"OCR_LINE_INDEX", "NATIVE_LINE_INDEX"}
    ]
    base_words = [
        atom
        for atom in atoms
        if atom["upstream_locator"]["kind"] in {"OCR_WORD_INDEX", "NATIVE_WORD_INDEX"}
    ]
    native_quarantine = [
        atom
        for atom in atoms
        if atom["upstream_locator"]["kind"] == "NATIVE_QUARANTINED_SPAN_INDEX"
    ]
    supplement_lines = [
        atom for atom in atoms if atom["upstream_locator"]["kind"] == "SUPPLEMENT_LINE_INDEX"
    ]
    supplement_summaries = [
        atom
        for atom in atoms
        if atom["upstream_locator"]["kind"] == "SUPPLEMENT_WORD_AXIS_QUARANTINE"
    ]
    reconstructed_lines: list[dict[str, Any]] = []
    reconstructed_words: list[dict[str, Any]] = []
    reconstructed_quarantine: list[dict[str, Any]] = []
    reconstructed_supplement_projection: dict[str, Any] | None = None

    if route == "DOMINANT_RASTER_OCR" and not terminal:
        expected_sequence: list[dict[str, Any]] = []
        lines_by_index: dict[int, dict[str, Any]] = {}
        words_by_line: dict[int, list[dict[str, Any]]] = {}
        for atom in atoms:
            locator_kind = atom["upstream_locator"]["kind"]
            if locator_kind == "OCR_LINE_INDEX":
                line_index = atom["upstream_locator"]["line_index"]
                if line_index in lines_by_index:
                    raise SourceStructureContractError("OCR line axis is duplicated")
                lines_by_index[line_index] = atom
            elif locator_kind == "OCR_WORD_INDEX":
                words_by_line.setdefault(atom["upstream_locator"]["line_index"], []).append(atom)
            else:
                raise SourceStructureContractError(
                    "complete OCR atom sequence contains foreign axes"
                )
        if sorted(lines_by_index) != list(range(receipt["upstream_line_axis_count"])):
            raise SourceStructureContractError("OCR line axis was dropped or reordered")
        for line_index in range(receipt["upstream_line_axis_count"]):
            line = lines_by_index[line_index]
            expected_sequence.append(line)
            words = words_by_line.get(line_index, [])
            word_indexes = [word["upstream_locator"]["word_index"] for word in words]
            if word_indexes != list(range(len(words))):
                raise SourceStructureContractError("OCR word axis was dropped or reordered")
            expected_sequence.extend(words)
            upstream_words = [
                {
                    "raw_text": (
                        "" if word["kind"] == AtomKind.EXCLUDED_EMPTY_WORD else word["raw_text"]
                    ),
                    "score": None,
                    "score_kind": word["score_kind"],
                    "normalized_pixel_bbox": word["pixel_bbox"],
                    "canonical_bbox_mpt": word["canonical_bbox_mpt"],
                    "canonical_polygon_mpt": word["canonical_polygon_mpt"],
                }
                for word in words
            ]
            reconstructed_words.extend(upstream_words)
            reconstructed_lines.append(
                {
                    "raw_text": (
                        "" if line["kind"] == AtomKind.EXCLUDED_EMPTY_LINE else line["raw_text"]
                    ),
                    "score": line["score"],
                    "score_kind": line["score_kind"],
                    "raw_pixel_bbox": line["pixel_bbox"],
                    "raw_pixel_polygon": line["pixel_polygon"],
                    "canonical_bbox_mpt": line["canonical_bbox_mpt"],
                    "canonical_polygon_mpt": line["canonical_polygon_mpt"],
                    "words": upstream_words,
                }
            )
            line_text = "" if line["kind"] == AtomKind.EXCLUDED_EMPTY_LINE else line["raw_text"]
            word_text = "".join(
                "" if word["kind"] == AtomKind.EXCLUDED_EMPTY_WORD else word["raw_text"]
                for word in words
            )
            if line_text != word_text:
                raise SourceStructureContractError("OCR line/word exact text projection drifted")
        if not same_typed_json_v1(expected_sequence, atoms):
            raise SourceStructureContractError("OCR atom sequence drifted")
    elif route == "CAUSAL_NATIVE_TEXT":
        expected_sequence = []
        seen_line_identities: set[tuple[int, int]] = set()
        cursor = 0
        while (
            cursor < len(atoms) and atoms[cursor]["upstream_locator"]["kind"] == "NATIVE_LINE_INDEX"
        ):
            line = atoms[cursor]
            locator_item = line["upstream_locator"]
            identity = (locator_item["block_number"], locator_item["line_number"])
            if identity in seen_line_identities:
                raise SourceStructureContractError(
                    "native visual-order line run is repeated or noncontiguous"
                )
            seen_line_identities.add(identity)
            expected_sequence.append(line)
            cursor += 1
            words = []
            while (
                cursor < len(atoms)
                and atoms[cursor]["upstream_locator"]["kind"] == "NATIVE_WORD_INDEX"
                and (
                    atoms[cursor]["upstream_locator"]["block_number"],
                    atoms[cursor]["upstream_locator"]["line_number"],
                )
                == identity
            ):
                words.append(atoms[cursor])
                expected_sequence.append(atoms[cursor])
                cursor += 1
            if not words or [word["upstream_locator"]["word_number"] for word in words] != sorted(
                {word["upstream_locator"]["word_number"] for word in words}
            ):
                raise SourceStructureContractError("native word axis was dropped or reordered")
            if line["raw_text"] != " ".join(word["raw_text"] for word in words):
                raise SourceStructureContractError("native line/word text projection drifted")
            expected_line_bbox = [
                min(word["canonical_bbox_mpt"][0] for word in words),
                min(word["canonical_bbox_mpt"][1] for word in words),
                max(word["canonical_bbox_mpt"][2] for word in words),
                max(word["canonical_bbox_mpt"][3] for word in words),
            ]
            if line["canonical_bbox_mpt"] != expected_line_bbox:
                raise SourceStructureContractError("native line/word geometry projection drifted")
            upstream_words = [
                {
                    "raw_text": word["raw_text"],
                    "score": None,
                    "score_kind": word["score_kind"],
                    "canonical_bbox_mpt": word["canonical_bbox_mpt"],
                    "block_number": word["upstream_locator"]["block_number"],
                    "line_number": word["upstream_locator"]["line_number"],
                    "word_number": word["upstream_locator"]["word_number"],
                }
                for word in words
            ]
            reconstructed_words.extend(upstream_words)
            reconstructed_lines.append(
                {
                    "raw_text": line["raw_text"],
                    "score": None,
                    "score_kind": line["score_kind"],
                    "canonical_bbox_mpt": line["canonical_bbox_mpt"],
                    "block_number": locator_item["block_number"],
                    "line_number": locator_item["line_number"],
                    "words": upstream_words,
                }
            )
        while cursor < len(atoms):
            atom = atoms[cursor]
            if atom["upstream_locator"]["kind"] != "NATIVE_QUARANTINED_SPAN_INDEX":
                raise SourceStructureContractError("native atom sequence contains foreign axes")
            locator_item = atom["upstream_locator"]
            expected_sequence.append(atom)
            summary = atom["quarantine_summary"]
            reconstructed_quarantine.append(
                {
                    "page": locator["physical_page"],
                    "text_sha256": summary["excluded_text_sha256"],
                    "nonwhitespace_character_count": summary["nonwhitespace_character_count"],
                    "bbox_mpt": atom["canonical_bbox_mpt"],
                    "block_number": locator_item["block_number"],
                    "line_number": locator_item["line_number"],
                    "span_number": locator_item["span_number"],
                    "color": summary["color"],
                    "alpha": summary["alpha"],
                    "render_sequence": summary["render_sequence"],
                    "occluding_sequence": summary["occluding_sequence"],
                    "occluding_object_type": summary["occluding_object_type"],
                    "reason": summary["reason"],
                }
            )
            cursor += 1
        if not same_typed_json_v1(expected_sequence, atoms):
            raise SourceStructureContractError("native atom sequence drifted")
    else:
        if any(
            atom["upstream_locator"]["kind"]
            not in {"SUPPLEMENT_LINE_INDEX", "SUPPLEMENT_WORD_AXIS_QUARANTINE"}
            for atom in atoms
        ):
            raise SourceStructureContractError("terminal OCR page promoted base reader axes")
        indexes = [atom["upstream_locator"]["line_index"] for atom in supplement_lines]
        if indexes != sorted(set(indexes)) or any(
            index >= receipt["supplement_validated_line_axis_count"] for index in indexes
        ):
            raise SourceStructureContractError("supplement line axis was reordered")
        expected_sequence = supplement_lines + supplement_summaries
        if len(supplement_summaries) != (
            1 if supplement_references else 0
        ) or not same_typed_json_v1(
            expected_sequence,
            atoms,
        ):
            raise SourceStructureContractError("supplement atom sequence/accounting drifted")
        if supplement_references:
            summary = supplement_summaries[0]["quarantine_summary"]
            backend_reference = next(
                reference for reference in references if reference["kind"] == "BACKEND_PAYLOAD"
            )
            reconstructed_supplement_projection = {
                "supplemental_disposition": (
                    "LINE_ONLY_EVIDENCE_AVAILABLE_FROM_TERMINAL_WORD_BOX_GEOMETRY"
                    if supplement_lines
                    else "NO_LINE_ONLY_EVIDENCE_AVAILABLE_NO_NONEMPTY_VALID_LINE_TEXT"
                ),
                "lines": [
                    {
                        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_LINE_OBSERVATION_V1",
                        "line_index": atom["upstream_locator"]["line_index"],
                        "text": atom["raw_text"],
                        "score": atom["score"],
                        "pixel_rec_box": atom["pixel_bbox"],
                        "pixel_rec_polygon": atom["pixel_polygon"],
                        "canonical_rec_box_mpt": atom["canonical_bbox_mpt"],
                        "canonical_rec_polygon_mpt": atom["canonical_polygon_mpt"],
                    }
                    for atom in supplement_lines
                ],
                "words": [],
                "quarantine": {
                    "format_version": ("BANK_CORPUS_WAVE_1_ROLE_B_WORD_SUBDIVISION_QUARANTINE_V1"),
                    "status": "QUARANTINED_UNRESOLVED_WORD_BOX_GEOMETRY",
                    "reason": summary["reason"],
                    "ordered_subdivision_counts_by_line": summary[
                        "ordered_subdivision_counts_by_line"
                    ],
                    "total_subdivision_count": summary["total_subdivision_count"],
                    "word_axes_sha256": summary["word_axes_sha256"],
                    "raw_provider_payload_sha256": summary["raw_provider_payload_sha256"],
                    "raw_backend_payload_ref": {
                        "path": (
                            f"objects/sha256/{backend_reference['sha256'][:2]}/"
                            f"{backend_reference['sha256']}.json"
                        ),
                        "sha256": backend_reference["sha256"],
                        "size_bytes": backend_reference["size_bytes"],
                    },
                    "word_text_exposed": False,
                    "word_geometry_exposed": False,
                    "accepted_word_count": 0,
                },
                "metrics": {
                    "validated_line_axis_count": receipt["supplement_validated_line_axis_count"],
                    "excluded_empty_line_axis_count": receipt[
                        "supplement_excluded_empty_line_axis_count"
                    ],
                    "accepted_line_count": receipt["supplement_accepted_line_count"],
                    "accepted_word_count": 0,
                    "quarantined_subdivision_count": receipt[
                        "supplement_quarantined_subdivision_count"
                    ],
                },
            }

    if (
        receipt["upstream_line_axis_sha256"] != canonical_json_sha256_v1(reconstructed_lines)
        or receipt["upstream_word_axis_sha256"] != canonical_json_sha256_v1(reconstructed_words)
        or receipt["upstream_quarantine_axis_sha256"]
        != canonical_json_sha256_v1(reconstructed_quarantine)
        or receipt["supplement_evidence_projection_sha256"]
        != canonical_json_sha256_v1(reconstructed_supplement_projection)
    ):
        raise SourceStructureContractError(
            "neutral atoms do not reproduce the exact upstream projection receipt"
        )

    metrics = _require_exact_dict(envelope["metrics"], _METRIC_FIELDS, "neutral metrics")
    for key in _METRIC_FIELDS:
        _require_nonnegative_int(metrics[key], f"neutral metric {key}")
    expected_metrics = {
        "atom_count": len(atoms),
        "upstream_line_axis_count": len(base_lines),
        "upstream_word_axis_count": len(base_words),
        "upstream_quarantined_span_axis_count": len(native_quarantine),
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
        "supplement_validated_line_axis_count": receipt["supplement_validated_line_axis_count"],
        "supplement_excluded_empty_line_axis_count": receipt[
            "supplement_excluded_empty_line_axis_count"
        ],
        "supplement_quarantined_subdivision_count": receipt[
            "supplement_quarantined_subdivision_count"
        ],
        "quarantined_atom_count": sum(
            atom["authority"] == AtomAuthority.UPSTREAM_QUARANTINE for atom in atoms
        ),
    }
    if not same_typed_json_v1(metrics, expected_metrics):
        raise SourceStructureContractError("neutral page metrics drifted")
    receipt_count_bindings = {
        "upstream_line_axis_count": metrics["upstream_line_axis_count"],
        "upstream_word_axis_count": metrics["upstream_word_axis_count"],
        "upstream_quarantined_span_axis_count": metrics["upstream_quarantined_span_axis_count"],
        "excluded_empty_line_axis_count": metrics["excluded_empty_line_axis_count"],
        "excluded_empty_word_axis_count": metrics["excluded_empty_word_axis_count"],
        "supplement_validated_line_axis_count": metrics["supplement_validated_line_axis_count"],
        "supplement_accepted_line_count": metrics["supplemental_line_count"],
        "supplement_excluded_empty_line_axis_count": metrics[
            "supplement_excluded_empty_line_axis_count"
        ],
        "supplement_quarantined_subdivision_count": metrics[
            "supplement_quarantined_subdivision_count"
        ],
    }
    if any(receipt[field] != count for field, count in receipt_count_bindings.items()):
        raise SourceStructureContractError("upstream projection receipt counts drifted")
    if (
        metrics["upstream_line_axis_count"]
        != metrics["primary_line_count"] + metrics["excluded_empty_line_axis_count"]
        or metrics["upstream_word_axis_count"]
        != metrics["primary_word_count"] + metrics["excluded_empty_word_axis_count"]
        or metrics["supplement_validated_line_axis_count"]
        != metrics["supplemental_line_count"] + metrics["supplement_excluded_empty_line_axis_count"]
    ):
        raise SourceStructureContractError("neutral source-axis no-drop accounting drifted")
    if not same_typed_json_v1(envelope["safety"], SOURCE_STRUCTURE_SAFETY_V1):
        raise SourceStructureContractError("neutral page safety boundary drifted")
    canonical_json_bytes_v1(envelope)
    return canonical_clone_v1(envelope)


def _default_disposition(atom: Mapping[str, Any], *, terminal: bool) -> str:
    if atom["authority"] == AtomAuthority.UPSTREAM_QUARANTINE:
        return PrimaryDisposition.UPSTREAM_QUARANTINED.value
    if terminal or atom["authority"] == AtomAuthority.SUPPLEMENTAL_COARSE_LINE:
        return PrimaryDisposition.UPSTREAM_TERMINAL_UNRESOLVED.value
    return PrimaryDisposition.RETAINED_UNOWNED.value


def make_empty_page_proposal_set_v1(envelope: Mapping[str, Any]) -> dict[str, Any]:
    page = validate_neutral_page_envelope_v1(envelope)
    dispositions = [
        {
            "format_version": ATOM_DISPOSITION_FORMAT_VERSION,
            "source_atom_id": atom["source_local_id"],
            "primary_disposition": _default_disposition(atom, terminal=page["terminal"]),
            "source_object_id": None,
            "reason_code": (
                "UPSTREAM_QUARANTINE_RETAINED"
                if atom["authority"] == AtomAuthority.UPSTREAM_QUARANTINE
                else "UPSTREAM_TERMINAL_RETAINED"
                if page["terminal"]
                else "NO_SOURCE_OBJECT_OWNERSHIP_PROPOSED"
            ),
        }
        for atom in page["atoms"]
    ]
    return make_page_proposal_set_v1(page, proposals=[], dispositions=dispositions)


def make_page_proposal_set_v1(
    envelope: Mapping[str, Any],
    *,
    proposals: Sequence[Mapping[str, Any]],
    dispositions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    page = validate_neutral_page_envelope_v1(envelope)
    if type(proposals) is not list or type(dispositions) is not list:
        raise SourceStructureContractError("proposal/disposition inputs must be plain arrays")
    value = {
        "format_version": PAGE_PROPOSAL_FORMAT_VERSION,
        "claim_boundary": PAGE_PROPOSAL_CLAIM_BOUNDARY,
        "source_local_page_id": page["source_local_page_id"],
        "neutral_page_sha256": canonical_json_sha256_v1(page),
        "proposals": canonical_clone_v1(proposals),
        "dispositions": canonical_clone_v1(dispositions),
        "safety": canonical_clone_v1(SOURCE_STRUCTURE_SAFETY_V1),
    }
    return validate_page_proposal_set_v1(value, envelope=page)


def validate_page_proposal_set_v1(
    value: Any,
    *,
    envelope: Mapping[str, Any],
) -> dict[str, Any]:
    page = validate_neutral_page_envelope_v1(envelope)
    proposal_set = _require_exact_dict(value, _PROPOSAL_SET_FIELDS, "page proposal set")
    _reject_forbidden_output_keys(proposal_set, label="page proposal set")
    if proposal_set["format_version"] != PAGE_PROPOSAL_FORMAT_VERSION:
        raise SourceStructureContractError("page proposal format drifted")
    if proposal_set["claim_boundary"] != PAGE_PROPOSAL_CLAIM_BOUNDARY:
        raise SourceStructureContractError("page proposal claim boundary drifted")
    if proposal_set["source_local_page_id"] != page["source_local_page_id"]:
        raise SourceStructureContractError("page proposal parent identity drifted")
    if proposal_set["neutral_page_sha256"] != canonical_json_sha256_v1(page):
        raise SourceStructureContractError("page proposal evidence digest drifted")
    if not same_typed_json_v1(proposal_set["safety"], SOURCE_STRUCTURE_SAFETY_V1):
        raise SourceStructureContractError("page proposal safety boundary drifted")
    proposals = proposal_set["proposals"]
    if type(proposals) is not list:
        raise SourceStructureContractError("page proposals must be an array")
    atom_by_id = {atom["source_local_id"]: atom for atom in page["atoms"]}
    proposal_by_id: dict[str, dict[str, Any]] = {}
    primary_owner_by_atom: dict[str, str] = {}
    for proposal in proposals:
        item = _require_exact_dict(proposal, _PROPOSAL_FIELDS, "source proposal")
        try:
            kind = ProposalKind(item["kind"])
        except (TypeError, ValueError) as error:
            raise SourceStructureContractError("source proposal kind drifted") from error
        bbox = _validate_bbox(item["canonical_bbox_mpt"], "source proposal bbox")
        primary = item["primary_atom_ids"]
        supporting = item["supporting_atom_ids"]
        codes = item["evidence_codes"]
        if (
            type(primary) is not list
            or not primary
            or type(supporting) is not list
            or type(codes) is not list
            or not codes
        ):
            raise SourceStructureContractError("source proposal evidence arrays drifted")
        if any(
            type(atom_id) is not str or atom_id not in atom_by_id
            for atom_id in primary + supporting
        ):
            raise SourceStructureContractError("source proposal cites an unknown atom")
        if len(set(primary)) != len(primary) or len(set(supporting)) != len(supporting):
            raise SourceStructureContractError("source proposal repeats an atom")
        if set(primary) & set(supporting):
            raise SourceStructureContractError("source proposal primary/supporting atoms overlap")
        if codes != sorted(set(codes)) or any(
            type(code) is not str or code not in _PROPOSAL_EVIDENCE_CODES for code in codes
        ):
            raise SourceStructureContractError(
                "source proposal evidence codes are outside the closed V1 vocabulary"
            )
        for atom_id in primary + supporting:
            authority = atom_by_id[atom_id]["authority"]
            if authority != AtomAuthority.AUTHENTICATED_PRIMARY:
                raise SourceStructureContractError(
                    "terminal, supplemental, or quarantined atom was promoted into a source object"
                )
        primary_boxes = [atom_by_id[atom_id]["canonical_bbox_mpt"] for atom_id in primary]
        if any(
            type(atom_bbox) is not list
            or not (
                bbox[0] <= atom_bbox[0]
                and bbox[1] <= atom_bbox[1]
                and atom_bbox[2] <= bbox[2]
                and atom_bbox[3] <= bbox[3]
            )
            for atom_bbox in primary_boxes
        ):
            raise SourceStructureContractError(
                "source proposal bbox does not contain every primary atom bbox"
            )
        if page["route"] == "DOMINANT_RASTER_OCR":
            page_width, page_height = page["coordinate_authority"]["unrotated_dimensions_mpt"]
            if not (0 <= bbox[0] < bbox[2] <= page_width and 0 <= bbox[1] < bbox[3] <= page_height):
                raise SourceStructureContractError(
                    "OCR source proposal bbox lies outside authenticated page bounds"
                )
        else:
            # Current native RESULT_V1 authenticates a nonnegative canonical
            # coordinate system but carries no upper page dimensions.  V1
            # therefore binds proposal geometry to the exact primary-evidence
            # union instead of inventing an unauthenticated native page bound.
            expected_native_union = [
                min(atom_bbox[0] for atom_bbox in primary_boxes),
                min(atom_bbox[1] for atom_bbox in primary_boxes),
                max(atom_bbox[2] for atom_bbox in primary_boxes),
                max(atom_bbox[3] for atom_bbox in primary_boxes),
            ]
            if any(coordinate < 0 for coordinate in bbox) or bbox != expected_native_union:
                raise SourceStructureContractError(
                    "native source proposal bbox must equal the nonnegative primary-atom union"
                )
        expected_id = make_source_object_id_v1(
            "source_object",
            {
                "source_local_page_id": page["source_local_page_id"],
                "request_sha256": page["source_locator"]["request_sha256"],
                "kind": kind.value,
                "canonical_bbox_mpt": bbox,
                "primary_atom_ids": primary,
                "supporting_atom_ids": supporting,
                "evidence_codes": codes,
            },
        )
        proposal_id = _require_source_id(item["source_local_id"], "source object identity")
        if proposal_id != expected_id or proposal_id in proposal_by_id:
            raise SourceStructureContractError("source object identity drifted or repeated")
        proposal_by_id[proposal_id] = item
        for atom_id in primary:
            if atom_id in primary_owner_by_atom:
                raise SourceStructureContractError(
                    "one atom cannot be primary in multiple source objects"
                )
            primary_owner_by_atom[atom_id] = proposal_id
    if page["terminal"] and proposals:
        raise SourceStructureContractError("upstream terminal page cannot promote source objects")
    dispositions = proposal_set["dispositions"]
    if type(dispositions) is not list:
        raise SourceStructureContractError("atom dispositions must be an array")
    disposition_by_atom: dict[str, dict[str, Any]] = {}
    for disposition in dispositions:
        item = _require_exact_dict(disposition, _DISPOSITION_FIELDS, "atom disposition")
        if item["format_version"] != ATOM_DISPOSITION_FORMAT_VERSION:
            raise SourceStructureContractError("atom disposition format drifted")
        atom_id = item["source_atom_id"]
        if atom_id not in atom_by_id or atom_id in disposition_by_atom:
            raise SourceStructureContractError("atom disposition is unknown or duplicated")
        try:
            primary_disposition = PrimaryDisposition(item["primary_disposition"])
        except (TypeError, ValueError) as error:
            raise SourceStructureContractError("atom primary disposition drifted") from error
        source_object_id = item["source_object_id"]
        reason = item["reason_code"]
        if reason != _DISPOSITION_REASON_BY_KIND[primary_disposition]:
            raise SourceStructureContractError(
                "atom disposition reason is outside the closed V1 vocabulary"
            )
        atom = atom_by_id[atom_id]
        if primary_disposition is PrimaryDisposition.OWNED_BY_SOURCE_OBJECT:
            if source_object_id not in proposal_by_id:
                raise SourceStructureContractError("owned atom cites an unknown source object")
            if atom_id not in proposal_by_id[source_object_id]["primary_atom_ids"]:
                raise SourceStructureContractError("owned atom is not primary in its source object")
            if atom["authority"] != AtomAuthority.AUTHENTICATED_PRIMARY or page["terminal"]:
                raise SourceStructureContractError(
                    "ineligible atom received source-object ownership"
                )
        else:
            if source_object_id is not None:
                raise SourceStructureContractError("unowned atom carries a source object")
            expected = _default_disposition(atom, terminal=page["terminal"])
            if primary_disposition != expected:
                raise SourceStructureContractError("atom disposition violates upstream authority")
        disposition_by_atom[atom_id] = item
    if set(disposition_by_atom) != set(atom_by_id):
        missing = set(atom_by_id) - set(disposition_by_atom)
        raise SourceStructureContractError(
            f"every atom needs one primary disposition; missing={len(missing)}"
        )
    owned_in_dispositions = {
        atom_id
        for atom_id, disposition in disposition_by_atom.items()
        if disposition["primary_disposition"] == PrimaryDisposition.OWNED_BY_SOURCE_OBJECT
    }
    owned_in_proposals = {
        atom_id for proposal in proposals for atom_id in proposal["primary_atom_ids"]
    }
    if owned_in_dispositions != owned_in_proposals:
        raise SourceStructureContractError("source-object primary ownership accounting drifted")
    canonical_json_bytes_v1(proposal_set)
    return canonical_clone_v1(proposal_set)


def _normalized_financial_token_v1(raw_token: str) -> str:
    """Parse the closed Vietnamese-statement numeric token grammar.

    Dots/commas in repeated three-digit groups are thousands separators.  If
    both occur, the last separator is decimal and the other must be valid
    grouping.  This is deliberately conservative: ambiguous typography must
    stay UNRESOLVED rather than being normalized speculatively.
    """

    token = raw_token.strip()
    negative = False
    if token.startswith("(") or token.endswith(")"):
        if not (token.startswith("(") and token.endswith(")")):
            raise SourceStructureContractError("visible numeric token has unbalanced parentheses")
        negative = True
        token = token[1:-1].strip()
    if token.startswith(("+", "-")):
        if negative:
            raise SourceStructureContractError("visible numeric token has conflicting signs")
        negative = token[0] == "-"
        token = token[1:]
    if not token or re.fullmatch(r"[0-9., \u00a0\u202f]+", token) is None:
        raise SourceStructureContractError("visible raw token is not in the numeric grammar")

    if re.search(r"[ \u00a0\u202f]", token):
        if "." in token or "," in token:
            raise SourceStructureContractError(
                "mixed space/punctuation numeric grouping is ambiguous"
            )
        groups = re.split(r"[ \u00a0\u202f]", token)
        if (
            any(not group for group in groups)
            or re.fullmatch(r"[0-9]{1,3}", groups[0]) is None
            or any(re.fullmatch(r"[0-9]{3}", group) is None for group in groups[1:])
        ):
            raise SourceStructureContractError("visible numeric space grouping drifted")
        numeric = "".join(groups)
    elif "." in token and "," in token:
        decimal_separator = "." if token.rfind(".") > token.rfind(",") else ","
        grouping_separator = "," if decimal_separator == "." else "."
        integer_part, fractional_part = token.rsplit(decimal_separator, 1)
        if re.fullmatch(r"[0-9]+", fractional_part) is None:
            raise SourceStructureContractError("visible numeric decimal part drifted")
        groups = integer_part.split(grouping_separator)
        if (
            re.fullmatch(r"[0-9]{1,3}", groups[0]) is None
            or len(groups) < 2
            or any(re.fullmatch(r"[0-9]{3}", group) is None for group in groups[1:])
        ):
            raise SourceStructureContractError("visible numeric grouping drifted")
        numeric = "".join(groups) + "." + fractional_part
    elif "." in token or "," in token:
        separator = "." if "." in token else ","
        groups = token.split(separator)
        if any(re.fullmatch(r"[0-9]+", group) is None for group in groups):
            raise SourceStructureContractError("visible numeric separator grammar drifted")
        if len(groups) == 2 and len(groups[1]) == 3:
            raise SourceStructureContractError(
                "single-separator three-digit token is locale-ambiguous"
            )
        grouping = (
            len(groups) >= 2
            and re.fullmatch(r"[0-9]{1,3}", groups[0]) is not None
            and all(len(group) == 3 for group in groups[1:])
        )
        if grouping:
            numeric = "".join(groups)
        elif len(groups) == 2:
            numeric = groups[0] + "." + groups[1]
        else:
            raise SourceStructureContractError("visible numeric token is separator-ambiguous")
    else:
        numeric = token
    try:
        parsed = Decimal(("-" if negative else "") + numeric)
    except InvalidOperation as error:  # pragma: no cover - guarded grammar
        raise SourceStructureContractError("visible numeric token cannot be parsed") from error
    if not parsed.is_finite():  # pragma: no cover - Decimal grammar guard
        raise SourceStructureContractError("visible numeric token is non-finite")
    if parsed == 0:
        return "0"
    rendered = format(parsed, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def validate_value_semantics_v1(
    value: Any,
    *,
    envelope: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate explicit evidence; never infer zero or blank from a missing token."""

    page = validate_neutral_page_envelope_v1(envelope)
    record = _require_exact_dict(value, _VALUE_FIELDS, "value semantics evidence")
    _reject_forbidden_output_keys(record, label="value semantics evidence")
    if record["format_version"] != VALUE_SEMANTICS_FORMAT_VERSION:
        raise SourceStructureContractError("value semantics format drifted")
    try:
        status = ValueSemanticStatus(record["status"])
    except (TypeError, ValueError) as error:
        raise SourceStructureContractError("value semantics status drifted") from error
    raw = record["raw_token"]
    normalized = record["normalized_value"]
    region_id = record["source_region_id"]
    bbox = record["bounded_region_bbox_mpt"]
    flags = (
        record["visible_numeric_zero_verified"],
        record["visible_dash_verified"],
        record["pixel_blank_verified"],
    )
    atom_by_id = {atom["source_local_id"]: atom for atom in page["atoms"]}
    if any(type(flag) is not bool for flag in flags):
        raise SourceStructureContractError("value semantics proof flags must be boolean")
    if region_id is not None:
        _require_source_id(region_id, "value source region")
        if region_id not in atom_by_id:
            raise SourceStructureContractError(
                "value source region is not an atom in the authenticated neutral envelope"
            )
    if bbox is not None:
        _validate_bbox(bbox, "value bounded region")
    if region_id is not None and bbox is not None:
        region_bbox = atom_by_id[region_id]["canonical_bbox_mpt"]
        if type(region_bbox) is not list or not (
            region_bbox[0] <= bbox[0]
            and region_bbox[1] <= bbox[1]
            and bbox[2] <= region_bbox[2]
            and bbox[3] <= region_bbox[3]
        ):
            raise SourceStructureContractError(
                "value bounded region lies outside its authenticated source atom"
            )
    if raw is not None and (type(raw) is not str or not raw.strip()):
        raise SourceStructureContractError("visible raw token cannot be empty")
    if raw is not None and (region_id is None or bbox is None):
        raise SourceStructureContractError(
            "visible raw token requires authenticated source-region authority"
        )
    pixel_reference = record["pixel_evidence_ref"]
    reason = record["unresolved_reason"]
    if status is ValueSemanticStatus.BLANK:
        raise SourceStructureContractError(
            "BLANK is unsupported in V1 without authenticated grid-cell pixel replay"
        )
    if pixel_reference is not None:
        raise SourceStructureContractError(
            "pixel evidence references are unsupported in value semantics V1"
        )
    if status is ValueSemanticStatus.UNRESOLVED:
        if normalized is not None or any(flags) or reason not in _UNRESOLVED_REASON_CODES:
            raise SourceStructureContractError("unresolved value evidence drifted")
        if (region_id is None) != (bbox is None):
            raise SourceStructureContractError(
                "unresolved bounded evidence requires both region identity and geometry"
            )
        if raw is not None:
            atom = atom_by_id[region_id]
            if (
                type(atom["canonical_bbox_mpt"]) is not list
                or atom["raw_text"] != raw
                or not same_typed_json_v1(atom["canonical_bbox_mpt"], bbox)
            ):
                raise SourceStructureContractError(
                    "unresolved visible token is not exactly bound to one authenticated atom"
                )
    else:
        if reason is not None or region_id is None or bbox is None:
            raise SourceStructureContractError(
                "observed value evidence requires a bounded source region"
            )
        atom = atom_by_id[region_id]
        if (
            page["terminal"]
            or atom["authority"] != AtomAuthority.AUTHENTICATED_PRIMARY.value
            or atom["kind"] not in {AtomKind.LINE.value, AtomKind.WORD.value}
            or type(atom["canonical_bbox_mpt"]) is not list
            or raw != atom["raw_text"]
            or not same_typed_json_v1(bbox, atom["canonical_bbox_mpt"])
        ):
            raise SourceStructureContractError(
                "observed value evidence is not exactly bound to one nonterminal primary text atom"
            )
        if status is ValueSemanticStatus.DASH:
            if (
                raw is None
                or raw.strip() not in {"-", "–", "—"}
                or normalized is not None
                or flags != (False, True, False)
            ):
                raise SourceStructureContractError("DASH requires an explicit visible dash token")
        elif status is ValueSemanticStatus.OBSERVED_ZERO:
            try:
                parsed_zero = None if raw is None else _normalized_financial_token_v1(raw)
            except SourceStructureContractError as error:
                raise SourceStructureContractError(
                    "OBSERVED_ZERO raw token is not exact numeric evidence"
                ) from error
            if parsed_zero != "0" or normalized != "0" or flags != (True, False, False):
                raise SourceStructureContractError(
                    "OBSERVED_ZERO requires explicit visible-zero proof"
                )
        else:
            if raw is None or type(normalized) is not str or flags != (False, False, False):
                raise SourceStructureContractError(
                    "OBSERVED_VALUE requires visible raw/numeric evidence"
                )
            parsed = _normalized_financial_token_v1(raw)
            if parsed == "0" or normalized != parsed:
                raise SourceStructureContractError(
                    "OBSERVED_VALUE normalized value is not the exact parsed raw token"
                )
    canonical_json_bytes_v1(record)
    return canonical_clone_v1(record)


def _assert_contract_constants() -> None:
    if set(SOURCE_STRUCTURE_SAFETY_V1) != {
        "source_text_and_geometry_only",
        "statement_claimed",
        "table_claimed",
        "logical_rows_claimed",
        "financial_cells_claimed",
        "period_axis_claimed",
        "unit_axis_claimed",
        "scope_claimed",
        "value_claimed",
        "blank_claimed",
        "absence_claimed",
        "external_identity_metadata_used",
        "reference_answers_used",
        "template_metadata_used",
        "prior_period_values_used",
    }:
        raise AssertionError("source-structure safety contract is not closed")
    if _TOPOLOGY_ID_RE.fullmatch("sstfv1:" + "0" * 64) is None:
        raise AssertionError("topology identity pattern drifted")


_assert_contract_constants()
