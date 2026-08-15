"""Bank-blind graph for interest-income disclosures.

The common core is an interest-income owner followed by deposit-interest and
customer-loan-interest rows, two period lanes, a monetary unit and a printed
parent total.  Securities, finance-lease, guarantee, purchased-debt and other
credit-income rows are optional and may be reordered.  The printed total may
precede the children (as in a compact parent-first table) or follow them.

The matcher scans one complete PDF and never uses bank, filename, note or page
identity as a routing condition.  Fresh VietOCR text is semantic anchor
evidence only; numeric and schema authority belongs to the bounded review
layer.
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
    "InterestIncomeVariantGraphV1Error",
    "build_interest_income_variant_graph_document_v1",
    "validate_interest_income_variant_graph_replay_v1",
]

FORMAT_VERSION = "INTEREST_INCOME_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "INTEREST_INCOME"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_INTEREST_INCOME_OWNER_DEPOSIT_"
    "LOAN_OPTIONAL_CHILD_PERIOD_UNIT_FLEXIBLE_TOTAL_POSITION_STRUCTURE_ONLY_"
    "NO_NUMERIC_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_or_routing": False,
    "complete_pdf_region_enumeration_required": True,
    "fresh_vietocr_transformer_text_required": True,
    "mapping_authority": False,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "optional_children_and_row_order_may_vary_without_bank_rules": True,
    "pair_search_exhausted_before_larger_combinations": True,
    "persisted_result_self_authenticating": False,
    "printed_parent_total_may_precede_or_follow_children": True,
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
_DATE_OR_PERIOD = re.compile(
    r"(?:20(?:2[0-9]))|(?:[0-3]?[0-9][./-][01]?[0-9][./-](?:20)?[0-9]{2})|"
    r"(?:sau thang|6 thang|quy [ivx]+|nam nay|nam truoc|ky nay|ky truoc)"
)
_OWNER_ALIASES = ("Thu nhập lãi và các khoản thu nhập tương tự",)
_MAX_REGION_LINES = 62


class InterestIncomeVariantGraphV1Error(ValueError):
    """The complete-PDF input or interest-income graph drifted."""


def _error(message: str) -> InterestIncomeVariantGraphV1Error:
    return InterestIncomeVariantGraphV1Error(message)


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
        raise _error("interest-income matcher requires one complete nonempty PDF")
    pages: list[dict[str, Any]] = []
    global_ordinal = 0
    previous_page = 0
    for raw_page in value:
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_sequence",
            "primary_numeric_authority",
        }:
            raise _error("interest-income matcher page fields drifted")
        page_sequence = raw_page["page_sequence"]
        if type(page_sequence) is not int or page_sequence != previous_page + 1:
            raise _error("complete PDF page sequence must be exact and gap-free")
        if type(raw_page["primary_numeric_authority"]) is not bool:
            raise _error("primary numeric authority flag must be exact bool")
        if type(raw_page["lines"]) is not list:
            raise _error("page lines must be one list")
        lines = []
        seen: set[int] = set()
        for raw_line in raw_page["lines"]:
            if type(raw_line) is not dict or set(raw_line) != {
                "bbox",
                "semantic_text",
                "semantic_text_source",
                "source_line_index",
                "source_text",
                "vietocr_text",
            }:
                raise _error("interest-income line fields drifted")
            line_index = raw_line["source_line_index"]
            if type(line_index) is not int or line_index < 0 or line_index in seen:
                raise _error("source line indices must be exact unique integers")
            seen.add(line_index)
            if raw_line["source_text"] is not None and type(raw_line["source_text"]) is not str:
                raise _error("source text must be null or one exact string")
            if (
                type(raw_line["vietocr_text"]) is not str
                or type(raw_line["semantic_text"]) is not str
                or raw_line["semantic_text_source"]
                not in {
                    "FULL_DOCUMENT_FRESH_VIETOCR_TRANSFORMER",
                    "ROTATED_FRESH_VIETOCR_TRANSFORMER_RESCUE",
                }
            ):
                raise _error("fresh VietOCR semantic text must be one exact string")
            lines.append(
                {
                    "bbox": _bbox(raw_line["bbox"]),
                    "global_ordinal": global_ordinal,
                    "normalized_text": normalize_vietnamese_anchor_v1(raw_line["semantic_text"]),
                    "page_sequence": page_sequence,
                    "semantic_text_source": raw_line["semantic_text_source"],
                    "source_line_index": line_index,
                    "source_text": raw_line["source_text"],
                    "vietocr_text": raw_line["vietocr_text"],
                }
            )
            global_ordinal += 1
        if seen != set(range(len(raw_page["lines"]))):
            raise _error("source line indices must preserve a complete gap-free page")
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
    value = re.sub(r"^(?:[ivx]+[.]\s*)?", "", text).strip()
    # A note enumerator is followed by whitespace.  Requiring it prevents a
    # period such as ``30.6.2026`` from being stripped as an enumerator.
    value = re.sub(r"^(?:[0-9]+(?:[.][0-9]+)*[.)]?\s+)+", "", value).strip()
    return re.sub(r"\s+(?:tiep theo|hop nhat)$", "", value).strip(" :;.-")


def _is_owner(text: str) -> bool:
    value = _strip_enumerator(text)
    return len(value.split()) <= 14 and (
        match_vietnamese_anchor_alias_v1(value, _OWNER_ALIASES) is not None
    )


def _is_next_family(text: str) -> bool:
    value = _strip_enumerator(text)
    if len(value.split()) > 18:
        return False
    return any(
        phrase in value
        for phrase in (
            "chi phi lai va cac chi phi tuong tu",
            "chi phi lai va cac khoan chi phi tuong tu",
            "chi phi lai va cac khoan tuong tu chi phi lai",
            "chi phi lai va cac khoan chi phi lai tuong tu",
        )
    )


def _child_role(text: str) -> str | None:
    value = _strip_enumerator(text)
    if len(value.split()) > 18 or _is_owner(value):
        return None
    if "tien gui" in value and any(token in value for token in ("lai", "thu nhap")):
        return "DEPOSIT_INTEREST"
    if "cho thue tai chinh" in value:
        return "FINANCE_LEASE_INTEREST"
    if "cho vay" in value and any(token in value for token in ("lai", "thu nhap")):
        return "CUSTOMER_LOAN_INTEREST"
    if "chung khoan kinh doanh" in value:
        return "TRADING_SECURITIES_DETAIL"
    if "chung khoan dau tu" in value:
        return "INVESTMENT_SECURITIES_DETAIL"
    if "chung khoan" in value and any(token in value for token in ("lai", "thu nhap")):
        return "SECURITIES_INTEREST"
    if "bao lanh" in value and any(token in value for token in ("thu", "phi")):
        return "GUARANTEE_FEE_INTEREST"
    if any(phrase in value for phrase in ("mua ban no", "mua no")):
        return "PURCHASED_DEBT_INTEREST"
    if "tin dung" in value and "khac" in value:
        return "OTHER_CREDIT_INCOME"
    return None


def _axis_role(text: str) -> str | None:
    value = _strip_enumerator(text)
    if "trieu dong" in value or "trieu vnd" in value:
        return "UNIT_AXIS"
    if _DATE_OR_PERIOD.search(value):
        return "PERIOD_AXIS"
    return None


def _line_ref(line: Mapping[str, Any], role: str) -> dict[str, Any]:
    return {
        "bbox": list(line["bbox"]),
        "global_ordinal": line["global_ordinal"],
        "page_sequence": line["page_sequence"],
        "role": role,
        "semantic_text_source": line["semantic_text_source"],
        "source_line_index": line["source_line_index"],
        "vietocr_text": line["vietocr_text"],
    }


def _flatten(pages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [line for page in pages for line in page["lines"]]


def _window(lines: Sequence[Mapping[str, Any]], start: int) -> list[Mapping[str, Any]]:
    owner = lines[start]
    window = []
    for line in lines[start + 1 : start + 1 + _MAX_REGION_LINES]:
        if line["page_sequence"] != owner["page_sequence"]:
            break
        if _is_next_family(line["normalized_text"]):
            break
        if _is_owner(line["normalized_text"]):
            break
        window.append(line)
    return window


def _region(lines: Sequence[Mapping[str, Any]], start: int) -> dict[str, Any]:
    owner = lines[start]
    window = _window(lines, start)
    prefix = [
        line
        for line in lines[max(0, start - 10) : start]
        if line["page_sequence"] == owner["page_sequence"]
    ]
    events = [_line_ref(owner, "OWNER")]
    children: list[tuple[str, Mapping[str, Any]]] = []
    period_count = 0
    unit_count = 0
    numeric_lines = []
    for line in [*prefix, *window]:
        text = line["normalized_text"]
        child = _child_role(text)
        axis = _axis_role(text)
        if child is not None:
            children.append((child, line))
            events.append(_line_ref(line, child))
        elif axis is not None:
            events.append(_line_ref(line, axis))
            period_count += axis == "PERIOD_AXIS"
            unit_count += axis == "UNIT_AXIS"
        if line in window and axis is None and _NUMBER.fullmatch(text):
            numeric_lines.append(line)
    child_roles = {role for role, _ in children}
    if children:
        first_child = min(line["global_ordinal"] for _, line in children)
        last_child = max(line["global_ordinal"] for _, line in children)
        leading_values = sum(line["global_ordinal"] < first_child for line in numeric_lines)
        trailing_values = sum(line["global_ordinal"] > last_child for line in numeric_lines)
    else:
        leading_values = trailing_values = 0
    if leading_values >= 2:
        total_position = "LEADING_PARENT_TOTAL_BEFORE_CHILDREN"
    elif trailing_values >= 2:
        total_position = "TRAILING_UNLABELED_TOTAL_AFTER_CHILDREN"
    else:
        total_position = "NO_PRINTED_PARENT_TOTAL_POSITION"
    core = {"DEPOSIT_INTEREST", "CUSTOMER_LOAN_INTEREST"}
    complete = (
        core.issubset(child_roles)
        and len(numeric_lines) >= 10
        and period_count >= 2
        and unit_count >= 1
        and total_position != "NO_PRINTED_PARENT_TOTAL_POSITION"
    )
    anchor_roles = ["OWNER", *sorted(child_roles), "PERIOD_AXIS", "UNIT_AXIS"]
    end = window[-1] if window else owner
    return {
        "anchor_roles": anchor_roles,
        "complete": complete,
        "end_global_ordinal": end["global_ordinal"],
        "events": events,
        "layout": {
            "child_roles": sorted(child_roles),
            "optional_child_count": len(child_roles - core),
            "period_axis_line_count": period_count,
            "presentation": "OWNER_FLEXIBLE_CHILD_ORDER_TWO_PERIOD_VALUE_LANES",
            "printed_parent_total_position": total_position,
            "unit_axis_line_count": unit_count,
        },
        "numeric_line_count": len(numeric_lines),
        "owner": _line_ref(owner, "OWNER"),
        "page_span": [owner["page_sequence"], end["page_sequence"]],
        "pair_anchor_combinations": [
            list(pair) for pair in itertools.combinations(dict.fromkeys(anchor_roles), 2)
        ],
        "start_global_ordinal": owner["global_ordinal"],
    }


def _metrics(
    regions: Sequence[Mapping[str, Any]], near: Sequence[Mapping[str, Any]]
) -> dict[str, int]:
    return {
        "complete_region_count": len(regions),
        "leading_total_region_count": sum(
            item["layout"]["printed_parent_total_position"]
            == "LEADING_PARENT_TOTAL_BEFORE_CHILDREN"
            for item in regions
        ),
        "near_region_count": len(near),
        "numeric_line_count_in_complete_regions": sum(
            item["numeric_line_count"] for item in regions
        ),
        "page_count_with_complete_region": len(
            {item["owner"]["page_sequence"] for item in regions}
        ),
        "trailing_total_region_count": sum(
            item["layout"]["printed_parent_total_position"]
            == "TRAILING_UNLABELED_TOTAL_AFTER_CHILDREN"
            for item in regions
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("interest-income result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["regions"]) is not list
        or type(value["near_regions"]) is not list
        or not same_typed_json_v1(
            value["metrics"], _metrics(value["regions"], value["near_regions"])
        )
    ):
        raise _error("interest-income result identity or metrics drifted")
    complete_count = len(value["regions"])
    expected_status = (
        "ACCEPTED_UNIQUE_VARIANT_GRAPH" if complete_count == 1 else "UNRESOLVED_NO_UNIQUE_REGION"
    )
    expected_uniqueness = {
        "complete_region_count": complete_count,
        "status": "UNIQUE_FULL_MATCH" if complete_count == 1 else "NOT_UNIQUE_FULL_MATCH",
    }
    if value["status"] != expected_status or not same_typed_json_v1(
        value["uniqueness"], expected_uniqueness
    ):
        raise _error("interest-income uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "iivgv1:graph:" + canonical_json_sha256_v1(material):
        raise _error("interest-income graph identity drifted")
    return canonical_clone_v1(value)


def build_interest_income_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
    """Enumerate every interest-income-like region in one complete PDF."""

    parsed = _pages(pages)
    lines = _flatten(parsed)
    candidates = [
        _region(lines, index)
        for index, line in enumerate(lines)
        if _is_owner(line["normalized_text"])
    ]
    regions = [item for item in candidates if item["complete"]]
    near = [item for item in candidates if not item["complete"]]
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "metrics": _metrics(regions, near),
        "near_regions": near,
        "regions": regions,
        "safety": canonical_clone_v1(_SAFETY),
        "status": "ACCEPTED_UNIQUE_VARIANT_GRAPH"
        if len(regions) == 1
        else "UNRESOLVED_NO_UNIQUE_REGION",
        "uniqueness": {
            "complete_region_count": len(regions),
            "status": "UNIQUE_FULL_MATCH" if len(regions) == 1 else "NOT_UNIQUE_FULL_MATCH",
        },
    }
    return _validate_result(
        {**material, "result_id": "iivgv1:graph:" + canonical_json_sha256_v1(material)}
    )


def validate_interest_income_variant_graph_replay_v1(value: Any, pages: Any) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_interest_income_variant_graph_document_v1(pages)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("interest-income graph does not replay exactly")
    return supplied
