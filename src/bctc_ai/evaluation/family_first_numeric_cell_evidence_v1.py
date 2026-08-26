"""Typed PP-OCRv6 recognition evidence for one financial numeric crop.

This module deliberately starts *after* geometry/table logic has selected a
candidate numeric cell.  It binds the immutable crop bytes to the raw
recognizer output, classifies only conservative financial-number grammars, and
keeps blank, malformed, and ambiguous tokens unresolved.  In particular, an
explicit visible dash is zero while a blank crop is not.  Accounting closure
is not an input and therefore cannot repair a missing or substituted digit.

The record is evidence, not a standalone proof that the pinned recognizer ran;
the batch runner/receipt must separately attest that the provider consumed the
same immutable crop bytes with the pinned PP-OCRv6 recognizer.
"""

from __future__ import annotations

import hashlib
import io
import math
import re
import unicodedata
from typing import Any

from PIL import Image

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "FamilyFirstNumericCellEvidenceV1Error",
    "build_family_first_ppocrv6_numeric_cell_evidence_v1",
    "parse_visible_financial_numeric_token_v1",
    "validate_family_first_ppocrv6_numeric_cell_evidence_replay_v1",
]


FORMAT_VERSION = "FAMILY_FIRST_PPOCRV6_NUMERIC_CELL_EVIDENCE_V1"
CLAIM_BOUNDARY = (
    "IMMUTABLE_CROP_BOUND_RAW_PPOCRV6_NUMERIC_RECOGNITION_AND_CONSERVATIVE_"
    "TOKEN_PARSE_EVIDENCE_ONLY_NO_TABLE_PERIOD_UNIT_ACCOUNTING_FAMILY_SCHEMA_"
    "MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "accounting_closure_used_to_change_digits": False,
    "blank_token_means_zero": False,
    "dash_only_token_means_zero": True,
    "family_authority": False,
    "gemma_used": False,
    "mapping_authority": False,
    "numeric_evidence_only": True,
    "period_or_unit_authority": False,
    "provider_input_path_used_as_identity": False,
    "provider_model_execution_attested_by_this_record": False,
    "raw_record_self_authenticates": False,
    "schema_authority": False,
}
_PROVIDER_FIELDS = {"input_path", "page_index", "rec_score", "rec_text"}
_RECORD_FIELDS = {
    "authority",
    "claim_boundary",
    "crop_ref",
    "evidence_id",
    "format_version",
    "parsed_token",
    "provider_recognition",
}
_PARSED_FIELDS = {
    "classification",
    "coefficient",
    "negative_parentheses",
    "normalized_token",
    "percentage_mark_present",
    "scale",
    "separator_interpretation",
    "sign",
}
_DASHES = {"-", "\u2013", "\u2014", "\u2212"}
_SPACES = {" ", "\u00a0", "\u2007", "\u202f"}
_DIGITS = re.compile(r"^[0-9]+$")
_GROUPED_INTEGER_WITH_NOISE_SUFFIX = re.compile(
    r"^([0-9]{1,3}([.,])[0-9]{3}(?:\2[0-9]{3})*)[\s]+(\S.*)$"
)
_MALFORMED_DUPLICATE_DECIMAL_MARK = re.compile(r"^([0-9]+)([.,])([.,])([0-9]{2})$")


class FamilyFirstNumericCellEvidenceV1Error(ValueError):
    """A crop, recognizer response, numeric parse, or replay drifted."""


def _error(message: str) -> FamilyFirstNumericCellEvidenceV1Error:
    return FamilyFirstNumericCellEvidenceV1Error(message)


def _unresolved(token: str, *, percentage: bool, parentheses: bool) -> dict[str, Any]:
    return {
        "classification": "UNRESOLVED_TOKEN",
        "coefficient": None,
        "negative_parentheses": parentheses,
        "normalized_token": token,
        "percentage_mark_present": percentage,
        "scale": None,
        "separator_interpretation": None,
        "sign": None,
    }


def _parsed_number(
    token: str,
    *,
    classification: str = "SIGNED_NUMBER",
    digits: str,
    scale: int,
    negative: bool,
    parentheses: bool,
    percentage: bool,
    separator: str,
) -> dict[str, Any]:
    coefficient = int(digits)
    if negative and coefficient:
        coefficient = -coefficient
    return {
        "classification": classification,
        "coefficient": coefficient,
        "negative_parentheses": parentheses,
        "normalized_token": token,
        "percentage_mark_present": percentage,
        "scale": scale,
        "separator_interpretation": separator,
        "sign": -1 if negative and coefficient else (1 if coefficient else 0),
    }


def _grouped_integer(value: str, separator: str) -> str | None:
    parts = value.split(separator)
    if (
        len(parts) < 2
        or not 1 <= len(parts[0]) <= 3
        or not all(_DIGITS.fullmatch(part) for part in parts)
        or not all(len(part) == 3 for part in parts[1:])
    ):
        return None
    return "".join(parts)


def _decimal_parts(value: str, decimal_separator: str) -> tuple[str, str] | None:
    if value.count(decimal_separator) != 1:
        return None
    integer_part, fraction = value.split(decimal_separator)
    if not 1 <= len(fraction) <= 2 or _DIGITS.fullmatch(fraction) is None:
        return None
    thousands_separator = "," if decimal_separator == "." else "."
    if thousands_separator in integer_part:
        integer_digits = _grouped_integer(integer_part, thousands_separator)
    else:
        integer_digits = integer_part if _DIGITS.fullmatch(integer_part) else None
    if integer_digits is None:
        return None
    return integer_digits, fraction


def _mixed_grouped_integer(value: str) -> str | None:
    """Return digits for an OCR token whose thousands marks disagree.

    ``1.460,873`` and ``1,460.854`` are not accepted as final numbers here.
    They are retained as typed candidates because every group after the first
    contains exactly three digits, while both punctuation kinds occur.  A
    downstream table gate must still corroborate the candidate with an
    independent same-crop reader, an integer-money column, peer formatting,
    and an exact visible accounting equation.
    """

    if "." not in value or "," not in value:
        return None
    parts = re.split(r"[.,]", value)
    if (
        len(parts) < 3
        or not 1 <= len(parts[0]) <= 3
        or not all(_DIGITS.fullmatch(part) for part in parts)
        or not all(len(part) == 3 for part in parts[1:])
    ):
        return None
    return "".join(parts)


def parse_visible_financial_numeric_token_v1(raw_text: Any) -> dict[str, Any]:
    """Classify a raw visible token without using expected values or equations."""

    if type(raw_text) is not str:
        raise _error("raw numeric recognition must be one exact string")
    token = unicodedata.normalize("NFKC", raw_text).strip()
    if not token:
        return {
            "classification": "BLANK_UNRESOLVED",
            "coefficient": None,
            "negative_parentheses": False,
            "normalized_token": "",
            "percentage_mark_present": False,
            "scale": None,
            "separator_interpretation": None,
            "sign": None,
        }

    percentage = token.endswith("%")
    core = token[:-1].rstrip() if percentage else token
    parentheses = core.startswith("(") and core.endswith(")")
    if core.startswith("(") != core.endswith(")"):
        return _unresolved(token, percentage=percentage, parentheses=False)
    if parentheses:
        core = core[1:-1].strip()
    if core in _DASHES and not percentage and not parentheses:
        return {
            "classification": "DASH_ZERO",
            "coefficient": 0,
            "negative_parentheses": False,
            "normalized_token": token,
            "percentage_mark_present": False,
            "scale": 0,
            "separator_interpretation": "DASH",
            "sign": 0,
        }

    explicit_negative = core.startswith("-") or core.startswith("\u2212")
    explicit_positive = core.startswith("+")
    if explicit_negative or explicit_positive:
        core = core[1:].strip()
    if not core or (parentheses and (explicit_negative or explicit_positive)):
        return _unresolved(token, percentage=percentage, parentheses=parentheses)
    negative = parentheses or explicit_negative

    # A detector crop can contain one intact black monetary token followed by
    # a spatially overlapping coloured stamp or annotation.  Preserve the
    # intact leading token as a *candidate* only; downstream code must still
    # require an independent same-crop reader, an integer-money lane, peers,
    # and exact accounting closure before it can be used.  Requiring a
    # whitespace boundary, one consistent grouping separator, and an
    # alphabetic suffix avoids interpreting two adjacent numeric cells as one
    # rescued value.
    noisy = _GROUPED_INTEGER_WITH_NOISE_SUFFIX.fullmatch(core)
    if noisy is not None and any(character.isalpha() for character in noisy.group(3)):
        grouped_surface = noisy.group(1)
        separator = noisy.group(2)
        digits = _grouped_integer(grouped_surface, separator)
        if digits is not None and not percentage:
            return _parsed_number(
                token,
                classification="NOISE_SUFFIXED_GROUPED_INTEGER_CANDIDATE",
                digits=digits,
                scale=0,
                negative=negative,
                parentheses=parentheses,
                percentage=False,
                separator="NOISE_SUFFIXED_GROUPED_INTEGER_CANDIDATE",
            )

    if _DIGITS.fullmatch(core):
        return _parsed_number(
            token,
            digits=core,
            scale=0,
            negative=negative,
            parentheses=parentheses,
            percentage=percentage,
            separator="NONE",
        )

    space_kinds = {character for character in core if character in _SPACES}
    if space_kinds:
        if len(space_kinds) != 1 or any(character in core for character in ".,"):
            return _unresolved(token, percentage=percentage, parentheses=parentheses)
        space = next(iter(space_kinds))
        digits = _grouped_integer(core, space)
        if digits is None:
            return _unresolved(token, percentage=percentage, parentheses=parentheses)
        return _parsed_number(
            token,
            digits=digits,
            scale=0,
            negative=negative,
            parentheses=parentheses,
            percentage=percentage,
            separator="GROUPED_INTEGER_SPACE",
        )

    present = {separator for separator in ".," if separator in core}
    if len(present) == 1:
        separator = next(iter(present))
        grouped = _grouped_integer(core, separator)
        if grouped is not None:
            return _parsed_number(
                token,
                digits=grouped,
                scale=0,
                negative=negative,
                parentheses=parentheses,
                percentage=percentage,
                separator="GROUPED_INTEGER_POINT" if separator == "." else "GROUPED_INTEGER_COMMA",
            )
        decimal = _decimal_parts(core, separator)
        if decimal is not None:
            integer_digits, fraction = decimal
            return _parsed_number(
                token,
                digits=integer_digits + fraction,
                scale=len(fraction),
                negative=negative,
                parentheses=parentheses,
                percentage=percentage,
                separator="DECIMAL_POINT" if separator == "." else "DECIMAL_COMMA",
            )
    elif len(present) == 2:
        # PP-OCR can duplicate a percentage decimal mark as two adjacent,
        # different punctuation glyphs (for example ``1,.43``).  Preserve the
        # visible digits as a typed candidate only.  A downstream source-bound
        # gate must still require an independent same-crop reader, an exact
        # percentage lane with scale-two peers, and exact visible accounting
        # closure; this parser never chooses the candidate from arithmetic.
        malformed_decimal = _MALFORMED_DUPLICATE_DECIMAL_MARK.fullmatch(core)
        if malformed_decimal is not None and malformed_decimal.group(2) != malformed_decimal.group(
            3
        ):
            return _parsed_number(
                token,
                classification="MALFORMED_DUPLICATE_DECIMAL_MARK_CANDIDATE",
                digits=malformed_decimal.group(1) + malformed_decimal.group(4),
                scale=2,
                negative=negative,
                parentheses=parentheses,
                percentage=percentage,
                separator="MALFORMED_DUPLICATE_DECIMAL_MARK_CANDIDATE",
            )
        mixed_grouped = _mixed_grouped_integer(core)
        if mixed_grouped is not None and not percentage:
            return _parsed_number(
                token,
                classification="MIXED_GROUPED_INTEGER_CANDIDATE",
                digits=mixed_grouped,
                scale=0,
                negative=negative,
                parentheses=parentheses,
                percentage=False,
                separator="MIXED_GROUPED_INTEGER_CANDIDATE",
            )
        decimal_separator = "." if core.rfind(".") > core.rfind(",") else ","
        decimal = _decimal_parts(core, decimal_separator)
        if decimal is not None:
            integer_digits, fraction = decimal
            return _parsed_number(
                token,
                digits=integer_digits + fraction,
                scale=len(fraction),
                negative=negative,
                parentheses=parentheses,
                percentage=percentage,
                separator=(
                    "GROUPED_COMMA_DECIMAL_POINT"
                    if decimal_separator == "."
                    else "GROUPED_POINT_DECIMAL_COMMA"
                ),
            )
    return _unresolved(token, percentage=percentage, parentheses=parentheses)


def _crop_ref(crop_png_bytes: Any) -> dict[str, Any]:
    if type(crop_png_bytes) is not bytes or not crop_png_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        raise _error("numeric cell crop must be exact PNG bytes")
    try:
        with Image.open(io.BytesIO(crop_png_bytes)) as image:
            image.load()
            width, height = image.size
    except OSError as exc:
        raise _error("numeric cell crop PNG cannot be decoded") from exc
    if width <= 0 or height <= 0:
        raise _error("numeric cell crop dimensions are invalid")
    return {
        "pixel_height": height,
        "pixel_width": width,
        "sha256": hashlib.sha256(crop_png_bytes).hexdigest(),
        "size_bytes": len(crop_png_bytes),
    }


def _provider(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _PROVIDER_FIELDS:
        raise _error("PP-OCRv6 recognizer result fields drifted")
    if value["input_path"] is not None:
        raise _error("reference-blind PP-OCRv6 provider input path must be null")
    if value["page_index"] is not None:
        raise _error("standalone numeric crop provider page index must be null")
    if type(value["rec_text"]) is not str:
        raise _error("PP-OCRv6 numeric recognition must be one exact string")
    score = value["rec_score"]
    if type(score) not in {int, float} or not math.isfinite(float(score)) or not 0 <= score <= 1:
        raise _error("PP-OCRv6 numeric recognition score must be finite in [0, 1]")
    return {"raw_text": value["rec_text"], "score": float(score)}


def _validate_record(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RECORD_FIELDS:
        raise _error("numeric cell evidence fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["parsed_token"]) is not dict
        or set(value["parsed_token"]) != _PARSED_FIELDS
    ):
        raise _error("numeric cell evidence contract drifted")
    material = canonical_clone_v1(value)
    evidence_id = material.pop("evidence_id")
    if evidence_id != "ffncev1:evidence:" + canonical_json_sha256_v1(material):
        raise _error("numeric cell evidence hash identity drifted")
    return canonical_clone_v1(value)


def build_family_first_ppocrv6_numeric_cell_evidence_v1(
    *, crop_png_bytes: bytes, recognizer_payload: Any
) -> dict[str, Any]:
    """Bind one immutable crop to conservative raw PP-OCR numeric evidence."""

    recognition = _provider(recognizer_payload)
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "crop_ref": _crop_ref(crop_png_bytes),
        "format_version": FORMAT_VERSION,
        "parsed_token": parse_visible_financial_numeric_token_v1(recognition["raw_text"]),
        "provider_recognition": recognition,
    }
    return _validate_record(
        {
            **material,
            "evidence_id": "ffncev1:evidence:" + canonical_json_sha256_v1(material),
        }
    )


def validate_family_first_ppocrv6_numeric_cell_evidence_replay_v1(
    value: Any, *, crop_png_bytes: bytes, recognizer_payload: Any
) -> dict[str, Any]:
    """Rebuild one numeric evidence record from crop and provider snapshots."""

    persisted = _validate_record(value)
    expected = build_family_first_ppocrv6_numeric_cell_evidence_v1(
        crop_png_bytes=crop_png_bytes,
        recognizer_payload=recognizer_payload,
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("numeric cell evidence does not replay exactly")
    return persisted
