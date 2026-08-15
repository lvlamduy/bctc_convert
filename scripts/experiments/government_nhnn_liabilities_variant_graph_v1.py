"""Bank-blind complete-PDF graph for Government/SBV liabilities.

The graph admits the presentation variants observed in the eight bound bank
reports: an aggregate-only table, a central-bank-loan plus Treasury-deposit
table, and richer decompositions with loan facilities, currency/tenor rows,
repo transactions or other Government liabilities.  It never routes on bank,
file, page or note number.  Fresh VietOCR text proposes anchors only; visible
pixels, the source numeric challenger, period/unit scope and accounting
equations remain mandatory in the verification layer.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Mapping, Sequence
from typing import Any

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
    "GovernmentNHNNLiabilitiesVariantGraphV1Error",
    "build_government_nhnn_liabilities_variant_graph_document_v1",
    "validate_government_nhnn_liabilities_variant_graph_replay_v1",
]

FORMAT_VERSION = "GOVERNMENT_NHNN_LIABILITIES_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "GOVERNMENT_NHNN_LIABILITIES"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_GOVERNMENT_NHNN_LIABILITY_"
    "AGGREGATE_LOAN_TREASURY_CURRENCY_TENOR_REPO_OR_OTHER_LIABILITY_"
    "STRUCTURE_ONLY_NO_NUMERIC_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_or_routing": False,
    "complete_pdf_region_enumeration_required": True,
    "fresh_vietocr_transformer_text_required": True,
    "mapping_authority": False,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "optional_children_may_vary_without_bank_rules": True,
    "pair_search_exhausted_before_larger_combinations": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "text_similarity_alone_can_accept": False,
    "topology_period_unit_total_and_accounting_replay_required_for_mapping": True,
}
_RESULT_FIELDS = {
    "claim_boundary",
    "family_id",
    "format_version",
    "metrics",
    "near_regions",
    "regions",
    "result_id",
    "safety",
    "status",
    "uniqueness",
}
_NUMBER = re.compile(r"^\(?[+-]?[0-9]+(?:[., ][0-9]+)*%?\)?$")
_DATE = re.compile(
    r"(?:[0-3]?[0-9](?:[./-]|\s+)[01]?[0-9](?:[./-]|\s+)(?:20)?[0-9]{2})|"
    r"(?:ngay\s+[0-3]?[0-9]\s+thang\s+[01]?[0-9])|"
    r"(?:so\s+(?:du\s+)?(?:cuoi|dau)\s+(?:ky|nam))"
)
_OWNER_ALIASES = {
    "cac khoan no chinh phu va nhnn",
    "cac khoan no chinh phu va ngan hang nha nuoc",
    "cac khoan no chinh phu va ngan hang nha nuoc viet nam",
    "cac khoan no chinh phu va ngan hang trung uong",
}
_MAX_REGION_LINES = 120
# Every observed eight-bank family instance closes on its owner page.  Keeping
# this bound at one prevents the next note's isolated ordinal/page header from
# being mistaken for a family value while still allowing arbitrary row order
# and optional branches inside the actual table.
_MAX_REGION_PAGES = 1


class GovernmentNHNNLiabilitiesVariantGraphV1Error(ValueError):
    """The complete-PDF input or replayed Government/SBV graph drifted."""


def _error(message: str) -> GovernmentNHNNLiabilitiesVariantGraphV1Error:
    return GovernmentNHNNLiabilitiesVariantGraphV1Error(message)


def _bbox(value: Any) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or value[0] < 0
        or value[1] < 0
        or value[2] <= value[0]
        or value[3] <= value[1]
    ):
        raise _error("line bbox must contain four exact positive-bound integers")
    return list(value)


def _pages(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence) or not value:
        raise _error("Government/SBV matcher requires one complete nonempty PDF")
    pages: list[dict[str, Any]] = []
    global_ordinal = 0
    previous_page = 0
    for raw_page in value:
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_sequence",
            "primary_numeric_authority",
        }:
            raise _error("Government/SBV matcher page fields drifted")
        page_sequence = raw_page["page_sequence"]
        if type(page_sequence) is not int or page_sequence != previous_page + 1:
            raise _error("complete PDF page sequence must be exact and gap-free")
        if type(raw_page["primary_numeric_authority"]) is not bool:
            raise _error("primary numeric authority flag must be exact bool")
        if type(raw_page["lines"]) is not list:
            raise _error("page lines must be one list")
        lines: list[dict[str, Any]] = []
        for line_index, raw_line in enumerate(raw_page["lines"]):
            if type(raw_line) is not dict or set(raw_line) != {
                "bbox",
                "semantic_text",
                "semantic_text_source",
                "source_line_index",
                "source_text",
                "vietocr_text",
            }:
                raise _error("Government/SBV line fields drifted")
            if raw_line["source_line_index"] != line_index:
                raise _error("source line indices must be exact and gap-free")
            if raw_line["source_text"] is not None and type(raw_line["source_text"]) is not str:
                raise _error("source text must be null or one exact string")
            if (
                type(raw_line["vietocr_text"]) is not str
                or type(raw_line["semantic_text"]) is not str
                or raw_line["semantic_text_source"] != "FULL_DOCUMENT_FRESH_VIETOCR_TRANSFORMER"
            ):
                raise _error("fresh VietOCR semantic text must be one exact string")
            lines.append(
                {
                    "bbox": _bbox(raw_line["bbox"]),
                    "global_ordinal": global_ordinal,
                    "normalized_text": normalize_vietnamese_anchor_v1(raw_line["semantic_text"]),
                    "page_sequence": page_sequence,
                    "source_line_index": line_index,
                    "source_text": raw_line["source_text"],
                    "vietocr_text": raw_line["vietocr_text"],
                }
            )
            global_ordinal += 1
        pages.append(
            {
                "lines": lines,
                "page_sequence": page_sequence,
                "primary_numeric_authority": raw_page["primary_numeric_authority"],
            }
        )
        previous_page = page_sequence
    return pages


def _strip_enumerator(text: str) -> str:
    value = re.sub(r"^(?:[0-9]+\s+)+", "", text).strip()
    return re.sub(r"\s+tiep theo$", "", value).strip()


def _is_owner(text: str) -> bool:
    value = _strip_enumerator(text)
    return len(value.split()) <= 13 and value in _OWNER_ALIASES


def _has_note_context(index: int, lines: Sequence[Mapping[str, Any]]) -> bool:
    target = lines[index]
    if re.match(r"^[0-9]+\s+", target["normalized_text"]):
        return True
    if index == 0:
        return False
    prior = lines[index - 1]
    return (
        prior["page_sequence"] == target["page_sequence"]
        and prior["bbox"][0] < target["bbox"][0]
        and min(prior["bbox"][3], target["bbox"][3]) > max(prior["bbox"][1], target["bbox"][1])
        and bool(re.fullmatch(r"[0-9]+", prior["normalized_text"]))
    )


def _is_next_family(text: str) -> bool:
    value = _strip_enumerator(text)
    return len(value.split()) <= 13 and any(
        phrase in value
        for phrase in (
            "tien gui va vay cac tctd khac",
            "tien gui va vay cac to chuc tin dung khac",
            "tien gui va vay cac tctd",
        )
    )


def _role(text: str) -> str | None:
    value = _strip_enumerator(text)
    if len(value.split()) > 22:
        return None
    if _is_owner(text):
        return "FAMILY_REPEAT"
    checks: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("CREDIT_FILE_LOAN", ("vay theo ho so tin dung",)),
        ("DISCOUNT_LOAN", ("vay chiet khau", "vay tai chiet khau")),
        ("COLLATERAL_LOAN", ("vay cam co giay to co gia", "vay cam co cac giay to co gia")),
        ("OTHER_LOAN", ("vay khac",)),
        ("TREASURY_NONTERM", ("tien gui khong ky han cua kbnn",)),
        ("TREASURY_TERM", ("tien gui co ky han cua kbnn",)),
        (
            "TREASURY_VND",
            (
                "tien gui bang dong viet nam",
                "tien gui khong ky han bang vnd",
                "tien gui co ky han bang vnd",
            ),
        ),
        (
            "TREASURY_FX",
            ("tien gui khong ky han bang ngoai te", "tien gui co ky han bang ngoai te"),
        ),
        (
            "TREASURY_DEPOSIT",
            ("tien gui cua kho bac", "tien gui thanh toan cua kho bac", "tien gui cua kbnn"),
        ),
        ("FINANCE_MINISTRY_DEPOSIT", ("tien gui cua bo tai chinh",)),
        ("REPO", ("giao dich ban va mua lai trai phieu chinh",)),
        ("OTHER_LIABILITY", ("cac khoan no khac",)),
        ("CENTRAL_BANK_LOAN", ("vay nhnn", "vay ngan hang nha nuoc", "vay ngan hang trung uong")),
    )
    for role, phrases in checks:
        if any(phrase in value for phrase in phrases):
            return role
    return None


def _line_ref(line: Mapping[str, Any], role: str) -> dict[str, Any]:
    return {
        "bbox": list(line["bbox"]),
        "global_ordinal": line["global_ordinal"],
        "page_sequence": line["page_sequence"],
        "role": role,
        "source_line_index": line["source_line_index"],
        "vietocr_text": line["vietocr_text"],
    }


def _flatten(pages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [line for page in pages for line in page["lines"]]


def _window(lines: Sequence[Mapping[str, Any]], start: int) -> list[Mapping[str, Any]]:
    owner = lines[start]
    window: list[Mapping[str, Any]] = []
    for line in lines[start + 1 : start + 1 + _MAX_REGION_LINES]:
        if line["page_sequence"] > owner["page_sequence"] + _MAX_REGION_PAGES - 1:
            break
        if _is_next_family(line["normalized_text"]):
            break
        window.append(line)
    return window


def _region(owner_index: int, lines: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    owner = lines[owner_index]
    window = _window(lines, owner_index)
    roles: dict[str, list[Mapping[str, Any]]] = {}
    periods: list[Mapping[str, Any]] = []
    units: list[Mapping[str, Any]] = []
    numeric: list[Mapping[str, Any]] = []
    for line in window:
        role = _role(line["normalized_text"])
        if role is not None:
            roles.setdefault(role, []).append(line)
        if _DATE.search(line["normalized_text"]):
            periods.append(line)
        if "trieu dong" in line["normalized_text"] or "trieu vnd" in line["normalized_text"]:
            units.append(line)
        compact = line["normalized_text"].replace(" ", "")
        if _NUMBER.fullmatch(compact) and any(char.isdigit() for char in compact):
            numeric.append(line)
    detail_roles = set(roles)
    note_context = _has_note_context(owner_index, lines)
    complete = note_context and bool(detail_roles) and len(periods) >= 2 and len(numeric) >= 4
    anchor_roles = ["OWNER", *sorted(detail_roles)]
    evidence = [owner, *periods, *units, *numeric]
    for items in roles.values():
        evidence.extend(items)
    last = max(evidence, key=lambda item: item["global_ordinal"])
    events = [_line_ref(owner, "OWNER")]
    for role in sorted(roles):
        events.extend(_line_ref(item, role) for item in roles[role])
    events.extend(_line_ref(item, "PERIOD_AXIS") for item in periods[:8])
    events.extend(_line_ref(item, "UNIT_AXIS") for item in units[:8])
    presentation = (
        "AGGREGATE_ONLY_WITH_REPEATED_FAMILY_ROW"
        if detail_roles == {"FAMILY_REPEAT"}
        else (
            "LOAN_AND_TREASURY_WITH_OPTIONAL_CURRENCY_TENOR_REPO_OR_OTHER_ROWS"
            if any(
                role.startswith("TREASURY")
                or role in {"REPO", "OTHER_LIABILITY", "FINANCE_MINISTRY_DEPOSIT"}
                for role in detail_roles
            )
            else "CENTRAL_BANK_LOAN_DECOMPOSITION"
        )
    )
    return {
        "anchor_roles": anchor_roles,
        "complete": complete,
        "end_global_ordinal": last["global_ordinal"],
        "events": events,
        "layout": {
            "detail_roles": sorted(detail_roles),
            "explicit_unit_line_count": len(units),
            "note_heading_context": note_context,
            "period_axis_line_count": len(periods),
            "presentation": presentation,
            "unit_scope_requires_document_inheritance": len(units) < 2,
        },
        "numeric_line_count": len(numeric),
        "owner": _line_ref(owner, "OWNER"),
        "pair_anchor_combinations": [
            list(pair) for pair in itertools.combinations(anchor_roles, 2)
        ],
        "page_span": [owner["page_sequence"], last["page_sequence"]],
        "start_global_ordinal": owner["global_ordinal"],
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("Government/SBV graph result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["regions"]) is not list
        or type(value["near_regions"]) is not list
        or type(value["metrics"]) is not dict
        or type(value["uniqueness"]) is not dict
    ):
        raise _error("Government/SBV graph identity or authority drifted")
    complete_count = len(value["regions"])
    expected_status = (
        "ACCEPTED_UNIQUE_VARIANT_GRAPH"
        if complete_count == 1
        else (
            "UNRESOLVED_NO_COMPLETE_REGION"
            if complete_count == 0
            else "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
        )
    )
    expected_uniqueness = {
        "complete_region_count": complete_count,
        "status": "UNIQUE_FULL_MATCH" if complete_count == 1 else "NOT_UNIQUE_FULL_MATCH",
    }
    expected_metrics = {
        "complete_region_count": complete_count,
        "near_region_count": len(value["near_regions"]),
        "owner_candidate_count": complete_count + len(value["near_regions"]),
    }
    if (
        value["status"] != expected_status
        or not same_typed_json_v1(value["uniqueness"], expected_uniqueness)
        or not same_typed_json_v1(value["metrics"], expected_metrics)
    ):
        raise _error("Government/SBV graph metrics or uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "gnlvv1:result:" + canonical_json_sha256_v1(material):
        raise _error("Government/SBV graph identity drifted")
    return canonical_clone_v1(value)


def build_government_nhnn_liabilities_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
    """Enumerate every Government/SBV-liability note candidate in one PDF."""

    lines = _flatten(_pages(pages))
    candidates = [
        _region(index, lines)
        for index, line in enumerate(lines)
        if _is_owner(line["normalized_text"])
    ]
    regions = [item for item in candidates if item["complete"]]
    near_regions = [item for item in candidates if not item["complete"]]
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "metrics": {
            "complete_region_count": len(regions),
            "near_region_count": len(near_regions),
            "owner_candidate_count": len(candidates),
        },
        "near_regions": near_regions,
        "regions": regions,
        "safety": canonical_clone_v1(_SAFETY),
        "status": (
            "ACCEPTED_UNIQUE_VARIANT_GRAPH"
            if len(regions) == 1
            else (
                "UNRESOLVED_NO_COMPLETE_REGION"
                if not regions
                else "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
            )
        ),
        "uniqueness": {
            "complete_region_count": len(regions),
            "status": "UNIQUE_FULL_MATCH" if len(regions) == 1 else "NOT_UNIQUE_FULL_MATCH",
        },
    }
    return _validate_result(
        {**material, "result_id": "gnlvv1:result:" + canonical_json_sha256_v1(material)}
    )


def validate_government_nhnn_liabilities_variant_graph_replay_v1(
    value: Any, pages: Any
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_government_nhnn_liabilities_variant_graph_document_v1(pages)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("Government/SBV graph does not replay exactly")
    return supplied
