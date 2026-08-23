"""Resolve a table unit locally, then by exact repeated document inheritance.

The primitive is independent of bank, filing period, page number and family.
It first searches the selected topology region for explicit unit observations.
Only when the region has none may it inherit one unit that repeats on at least
two distinct pages of the same authenticated document.  The word ``tỷ`` in
``tỷ giá`` is deliberately not a billion-unit observation.
"""

from __future__ import annotations

import re
from typing import Any

from bctc_ai.evaluation import accounting_family_row_axis_v1 as row_axis_v1
from bctc_ai.evaluation.accounting_table_axes_v1 import accounting_unit_surface_v1
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "AccountingDocumentUnitContextV1Error",
    "build_accounting_document_unit_context_v1",
    "validate_accounting_document_unit_context_replay_v1",
]


FORMAT_VERSION = "ACCOUNTING_DOCUMENT_UNIT_CONTEXT_V1"
CLAIM_BOUNDARY = (
    "EXACT_VISIBLE_LOCAL_UNIT_OR_REPEATED_SAME_DOCUMENT_UNIT_INHERITANCE_"
    "NO_BANK_FILE_PAGE_YEAR_FAMILY_OR_NUMERIC_MAPPING_AUTHORITY"
)
_SAFETY = {
    "bank_file_page_year_or_family_used_for_unit_routing": False,
    "document_inheritance_requires_two_distinct_pages": True,
    "geometry_authority": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "raw_record_self_authenticating": False,
    "schema_authority": False,
    "ty_gia_interpreted_as_billion_unit": False,
}
_FIELDS = {
    "claim_boundary",
    "context_id",
    "evidence_axis_sha256",
    "evidence_count",
    "evidence_mode",
    "evidence_page_count",
    "format_version",
    "resolved_unit",
    "safety",
    "status",
}


class AccountingDocumentUnitContextV1Error(ValueError):
    """The visible unit axis, region binding, or inheritance rule drifted."""


def _error(message: str) -> AccountingDocumentUnitContextV1Error:
    return AccountingDocumentUnitContextV1Error(message)


def _explicit_unit_surface(
    surface: str,
    *,
    expected_unit_kind: str,
    expected_currency: str,
    expected_magnitude_power10: int,
) -> dict[str, Any] | None:
    parsed = accounting_unit_surface_v1(surface)
    if parsed is None:
        return None
    normalized = normalize_vietnamese_anchor_v1(surface)
    required_word = {3: "nghin", 6: "trieu", 9: "ty"}.get(expected_magnitude_power10)
    if required_word is None:
        raise _error("unit magnitude is outside the supported explicit word axis")
    # ``tỷ giá`` describes an exchange rate, not a VND billion scale.  Require
    # the magnitude word and reject the bare exchange-rate phrase.
    words = normalized.split()
    if required_word not in words:
        return None
    if (
        expected_magnitude_power10 == 9
        and re.search(r"(?:^|\s)ty\s+(?:dong|vnd)(?:\s|$)", normalized) is None
    ):
        return None
    if (
        parsed["unit_kind"] != expected_unit_kind
        or parsed["currency"] != expected_currency
        or parsed["magnitude_power10"] != expected_magnitude_power10
    ):
        return None
    return canonical_clone_v1(parsed)


def _validate_result(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or value["status"] != "RESOLVED_EXACT_MONEY_UNIT_CONTEXT"
        or value["evidence_mode"]
        not in {
            "LOCAL_SELECTED_REGION_EXPLICIT_UNIT",
            "REPEATED_DOCUMENT_EXPLICIT_UNIT_INHERITANCE",
        }
        or type(value["evidence_count"]) is not int
        or value["evidence_count"] <= 0
        or type(value["evidence_page_count"]) is not int
        or value["evidence_page_count"] <= 0
        or type(value["evidence_axis_sha256"]) is not str
        or len(value["evidence_axis_sha256"]) != 64
        or type(value["resolved_unit"]) is not dict
    ):
        raise _error("accounting document unit-context result drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("context_id")
    if identity != "aducv1:context:" + canonical_json_sha256_v1(material):
        raise _error("accounting document unit-context identity drifted")
    return canonical_clone_v1(value)


def build_accounting_document_unit_context_v1(
    pages: Any,
    topology_region: Any,
    *,
    expected_unit_kind: str = "MONEY",
    expected_currency: str = "VND",
    expected_magnitude_power10: int = 6,
) -> dict[str, Any]:
    """Resolve an explicit local unit or one repeated document-wide unit."""

    parsed_pages = row_axis_v1._pages(pages)
    if type(topology_region) is not dict:
        raise _error("unit context requires one exact topology region")
    required_region_fields = {
        "page_sequence",
        "cluster_end_page_sequence_inclusive",
        "cluster_start_source_line_index",
        "cluster_end_source_line_index_exclusive",
    }
    if not required_region_fields.issubset(topology_region):
        raise _error("unit-context topology boundary drifted")
    start_page = topology_region["page_sequence"]
    stop_page = topology_region["cluster_end_page_sequence_inclusive"]
    start_line = topology_region["cluster_start_source_line_index"]
    stop_line = topology_region["cluster_end_source_line_index_exclusive"]
    if (
        type(start_page) is not int
        or type(stop_page) is not int
        or not 1 <= start_page <= stop_page <= len(parsed_pages)
        or type(start_line) is not int
        or (stop_line is not None and type(stop_line) is not int)
        or start_line < 0
        or (start_page == stop_page and stop_line is not None and stop_line <= start_line)
    ):
        raise _error("unit-context topology range drifted")

    evidence = []
    for page in parsed_pages:
        for line in page["lines"]:
            parsed = _explicit_unit_surface(
                line["vietocr_text"],
                expected_unit_kind=expected_unit_kind,
                expected_currency=expected_currency,
                expected_magnitude_power10=expected_magnitude_power10,
            )
            if parsed is not None:
                evidence.append(
                    {
                        "page_sequence": page["page_sequence"],
                        "source_line_index": line["line_ordinal"],
                        "surface": line["vietocr_text"],
                        "unit": parsed,
                    }
                )
    local = [
        item
        for item in evidence
        if start_page <= item["page_sequence"] <= stop_page
        and (item["page_sequence"] != start_page or item["source_line_index"] >= start_line)
        and (
            item["page_sequence"] != stop_page
            or stop_line is None
            or item["source_line_index"] < stop_line
        )
    ]
    selected = local if local else evidence
    mode = (
        "LOCAL_SELECTED_REGION_EXPLICIT_UNIT"
        if local
        else "REPEATED_DOCUMENT_EXPLICIT_UNIT_INHERITANCE"
    )
    page_count = len({item["page_sequence"] for item in selected})
    if not selected or (not local and page_count < 2):
        raise _error("money unit is neither local nor repeated across the document")
    units = {
        (
            item["unit"]["unit_kind"],
            item["unit"]["currency"],
            item["unit"]["magnitude_power10"],
        )
        for item in selected
    }
    if len(units) != 1:
        raise _error("visible money-unit observations conflict")
    unit_kind, currency, magnitude = next(iter(units))
    resolved = {
        "currency": currency,
        "magnitude_power10": magnitude,
        "unit_kind": unit_kind,
    }
    axis = canonical_clone_v1(selected)
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "evidence_axis_sha256": canonical_json_sha256_v1(axis),
        "evidence_count": len(axis),
        "evidence_mode": mode,
        "evidence_page_count": page_count,
        "format_version": FORMAT_VERSION,
        "resolved_unit": resolved,
        "safety": canonical_clone_v1(_SAFETY),
        "status": "RESOLVED_EXACT_MONEY_UNIT_CONTEXT",
    }
    return _validate_result(
        {**material, "context_id": "aducv1:context:" + canonical_json_sha256_v1(material)}
    )


def validate_accounting_document_unit_context_replay_v1(
    value: Any,
    pages: Any,
    topology_region: Any,
    *,
    expected_unit_kind: str = "MONEY",
    expected_currency: str = "VND",
    expected_magnitude_power10: int = 6,
) -> dict[str, Any]:
    persisted = _validate_result(value)
    expected = build_accounting_document_unit_context_v1(
        pages,
        topology_region,
        expected_unit_kind=expected_unit_kind,
        expected_currency=expected_currency,
        expected_magnitude_power10=expected_magnitude_power10,
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("accounting document unit context does not replay exactly")
    return persisted
