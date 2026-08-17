"""Bank-blind graph for entrusted/investment-risk funding disclosures.

The graph recognizes the common parent disclosure and a variable population of
received-capital children.  Observed detailed variants may expose an aggregate
organization/person row, a VND ODA row, an NHNN programme row, direct
international funding, currency children, or an explicit residual.  It scans a
complete PDF and never routes on bank, filename, page, or note number.  Fresh
VietOCR text proposes anchors only; pixels, periods, units, values, schema, and
accounting checks remain mandatory in the verification layer.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    match_vietnamese_anchor_alias_v1,
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "EntrustedInvestmentRiskCapitalVariantGraphV1Error",
    "build_entrusted_investment_risk_capital_variant_graph_document_v1",
    "validate_entrusted_investment_risk_capital_variant_graph_replay_v1",
]

FORMAT_VERSION = "ENTRUSTED_INVESTMENT_RISK_CAPITAL_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "ENTRUSTED_INVESTMENT_RISK_CAPITAL"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_ENTRUSTED_INVESTMENT_RISK_CAPITAL_"
    "OWNER_RECEIVED_SOURCE_OPTIONAL_CURRENCY_OR_RESIDUAL_STRUCTURE_ONLY_NO_"
    "NUMERIC_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
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
_OWNER_ALIASES = (
    "Vốn tài trợ, ủy thác đầu tư, cho vay TCTD chịu rủi ro",
    "Vốn tài trợ, ủy thác đầu tư, cho vay tổ chức tín dụng chịu rủi ro",
    "Vốn nhận tài trợ, ủy thác đầu tư, cho vay các tổ chức tín dụng chịu rủi ro",
    "Các khoản vốn tài trợ, ủy thác đầu tư, cho vay tổ chức tín dụng chịu rủi ro",
)
_MAX_REGION_LINES = 55
_MAX_REGION_PAGES = 1


class EntrustedInvestmentRiskCapitalVariantGraphV1Error(ValueError):
    """The complete-PDF input or entrusted-capital graph drifted."""


def _error(message: str) -> EntrustedInvestmentRiskCapitalVariantGraphV1Error:
    return EntrustedInvestmentRiskCapitalVariantGraphV1Error(message)


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
        raise _error("entrusted-capital matcher requires one complete nonempty PDF")
    pages: list[dict[str, Any]] = []
    global_ordinal = 0
    previous_page = 0
    for raw_page in value:
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_sequence",
            "primary_numeric_authority",
        }:
            raise _error("entrusted-capital matcher page fields drifted")
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
                raise _error("entrusted-capital line fields drifted")
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
    if len(value.split()) > 17:
        return False
    return match_vietnamese_anchor_alias_v1(value, _OWNER_ALIASES) is not None


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
    return len(value.split()) <= 14 and any(
        phrase in value
        for phrase in (
            "phat hanh giay to co gia",
            "cac khoan phai tra va cong no khac",
            "cac khoan no khac",
        )
    )


def _role(text: str) -> str | None:
    value = _strip_enumerator(text)
    if len(value.split()) > 30:
        return None
    if _is_owner(text):
        return None
    received_source_prefix = "von nhan" in value or (
        value.startswith("von tai tro") and ("uy thac" in value or "cho vay" in value)
    )
    if not received_source_prefix:
        if value in {"bang ngoai te", "bang tien vnd", "bang vnd"}:
            return "CURRENCY_ONLY_CHILD"
        if value == "khac":
            return "OTHER_CHILD"
        return None
    if "to chuc" in value and "ca nhan" in value:
        return "ORGANIZATION_OR_INDIVIDUAL"
    if "truc tiep" in value and "to chuc quoc te" in value:
        return "DIRECT_INTERNATIONAL_ORGANIZATION"
    if "tu nhnn" in value or "ngan hang nha nuoc" in value:
        return "NHNN_PROGRAMME"
    if "bang vnd" in value or "bang tien vnd" in value:
        return "VND_RECEIVED_SOURCE"
    if "bang ngoai te" in value:
        return "FOREIGN_CURRENCY_RECEIVED_SOURCE"
    if "uy thac" in value or "tai tro" in value:
        return "OTHER_RECEIVED_SOURCE"
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
    note_context = _has_note_context(owner_index, lines)
    # A visible note enumerator is useful corroboration, but it is not a core
    # family edge: some audited notes print the exact owner without a number or
    # place the number outside the detected line axis.  The generic acceptance
    # graph therefore requires the owner, at least one received-source child,
    # both period/unit axes, and numeric cells.  Downstream verification still
    # binds pixels and closes the accounting relation before mapping.
    complete = bool(roles) and len(periods) >= 2 and len(units) >= 2 and len(numeric) >= 2
    anchor_roles = ["OWNER", *sorted(roles)]
    evidence = [owner, *periods, *units, *numeric]
    for items in roles.values():
        evidence.extend(items)
    last = max(evidence, key=lambda item: item["global_ordinal"])
    events = [_line_ref(owner, "OWNER")]
    for role in sorted(roles):
        events.extend(_line_ref(item, role) for item in roles[role])
    events.extend(_line_ref(item, "PERIOD_AXIS") for item in periods[:6])
    events.extend(_line_ref(item, "UNIT_AXIS") for item in units[:6])
    presentation = (
        "ORGANIZATION_OR_INDIVIDUAL_AGGREGATE"
        if set(roles) == {"ORGANIZATION_OR_INDIVIDUAL"}
        else (
            "VND_ODA_OR_OTHER_RECEIVED_SOURCE"
            if "VND_RECEIVED_SOURCE" in roles
            else (
                "NHNN_PROGRAMME_RECEIVED_SOURCE"
                if "NHNN_PROGRAMME" in roles
                else "VARIABLE_RECEIVED_SOURCE_AND_OPTIONAL_CURRENCY_CHILDREN"
            )
        )
    )
    return {
        "anchor_roles": anchor_roles,
        "complete": complete,
        "end_global_ordinal": last["global_ordinal"],
        "events": events,
        "layout": {
            "detail_roles": sorted(roles),
            "explicit_unit_line_count": len(units),
            "note_heading_context": note_context,
            "period_axis_line_count": len(periods),
            "presentation": presentation,
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
        raise _error("entrusted-capital graph result fields drifted")
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
        raise _error("entrusted-capital graph identity or authority drifted")
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
        raise _error("entrusted-capital graph metrics or uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "eircvv1:result:" + canonical_json_sha256_v1(material):
        raise _error("entrusted-capital graph identity drifted")
    return canonical_clone_v1(value)


def build_entrusted_investment_risk_capital_variant_graph_document_v1(
    pages: Any,
) -> dict[str, Any]:
    """Enumerate every entrusted/investment-risk-capital candidate in one PDF."""

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
        {**material, "result_id": "eircvv1:result:" + canonical_json_sha256_v1(material)}
    )


def validate_entrusted_investment_risk_capital_variant_graph_replay_v1(
    value: Any, pages: Any
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_entrusted_investment_risk_capital_variant_graph_document_v1(pages)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("entrusted-capital graph does not replay exactly")
    return supplied
