"""Bank-blind graph for interest-expense disclosures.

The minimum searchable combination is the disclosure owner plus deposit- and
borrowing-interest children.  Issued-paper interest, finance-lease interest
and other credit expense are optional structural reinforcements.  Child order
may vary; a printed parent total may precede or follow the children.  When a
page omits its unit, the nearest preceding monetary unit in the same complete
PDF is retained as explicit document-level inheritance evidence.

Fresh VietOCR text is used only for anchors.  Geometry, source-number replay,
period scope, signs and accounting equations remain mandatory in the bounded
mapping review.
"""

from __future__ import annotations

import importlib.util
import itertools
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    match_vietnamese_anchor_alias_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "InterestExpenseVariantGraphV1Error",
    "build_interest_expense_variant_graph_document_v1",
    "validate_interest_expense_variant_graph_replay_v1",
]

FORMAT_VERSION = "INTEREST_EXPENSE_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "INTEREST_EXPENSE"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_INTEREST_EXPENSE_OWNER_DEPOSIT_"
    "BORROWING_OPTIONAL_CHILD_PERIOD_UNIT_FLEXIBLE_TOTAL_POSITION_STRUCTURE_"
    "ONLY_NO_NUMERIC_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_or_routing": False,
    "complete_pdf_region_enumeration_required": True,
    "document_unit_inheritance_is_explicit_not_silent": True,
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
_OWNER_ALIASES = (
    "Chi phí lãi và các chi phí tương tự",
    "Chi phí lãi và các khoản chi phí tương tự",
    "Chi phí lãi và các khoản tương tự chi phí lãi",
    "Chi phí lãi và các khoản chi phí lãi tương tự",
)
_MAX_REGION_LINES = 48
_DOCUMENT_UNIT_LOOKBACK_LINES = 250


class InterestExpenseVariantGraphV1Error(ValueError):
    """The complete-PDF input or interest-expense graph drifted."""


def _error(message: str) -> InterestExpenseVariantGraphV1Error:
    return InterestExpenseVariantGraphV1Error(message)


def _support() -> ModuleType:
    name = "interest_income_graph_support_for_interest_expense"
    if name in sys.modules:
        return sys.modules[name]
    path = Path(__file__).with_name("interest_income_variant_graph_v1.py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error("cannot load common interest-flow graph support")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _strip_enumerator(text: str) -> str:
    return _support()._strip_enumerator(text)


def _is_owner(text: str) -> bool:
    value = _strip_enumerator(text)
    return len(value.split()) <= 15 and (
        match_vietnamese_anchor_alias_v1(value, _OWNER_ALIASES) is not None
    )


def _is_next_family(text: str) -> bool:
    value = _strip_enumerator(text)
    if len(value.split()) > 20:
        return False
    return any(
        phrase in value
        for phrase in (
            "thu nhap lai thuan",
            "thu nhap tu lai thuan",
            "lai thuan tu hoat dong dich vu",
            "lai lo thuan tu mua ban chung khoan",
            "lai thuan tu mua ban chung khoan",
            "lo lai thuan tu hoat dong mua ban chung khoan",
        )
    )


def _child_role(text: str) -> str | None:
    value = _strip_enumerator(text)
    tokens = set(value.split())
    expense_action = "tra" in tokens or "chi" in tokens or "chi phi" in value
    if len(value.split()) > 20 or _is_owner(value):
        return None
    if "phat hanh giay to co gia" in value:
        return "ISSUED_PAPER_INTEREST"
    if "thue tai chinh" in value and expense_action:
        return "FINANCE_LEASE_INTEREST"
    # A combined source row such as ``tiền gửi và vay các TCTD khác`` is
    # economically a borrowing-cost row.  Borrowing therefore has precedence
    # over the incidental deposit token; this is phrase semantics, not a
    # document-specific route.
    if "vay" in value and expense_action:
        return "BORROWING_INTEREST"
    if "tien gui" in value and expense_action:
        return "DEPOSIT_INTEREST"
    if any(
        phrase in value
        for phrase in (
            "chi phi hoat dong tin dung khac",
            "chi phi khac cho hoat dong tin dung",
            "chi cac hoat dong tin dung khac",
        )
    ):
        return "OTHER_CREDIT_EXPENSE"
    return None


def _window(lines: list[dict[str, Any]], start: int) -> list[dict[str, Any]]:
    owner = lines[start]
    window = []
    for line in lines[start + 1 : start + 1 + _MAX_REGION_LINES]:
        if line["page_sequence"] != owner["page_sequence"]:
            break
        if _is_next_family(line["normalized_text"]) or _is_owner(line["normalized_text"]):
            break
        window.append(line)
    return window


def _document_unit(
    lines: list[dict[str, Any]], start: int, owner: Mapping[str, Any]
) -> dict[str, Any] | None:
    support = _support()
    preceding = lines[max(0, start - _DOCUMENT_UNIT_LOOKBACK_LINES) : start]
    candidates = [
        line for line in preceding if support._axis_role(line["normalized_text"]) == "UNIT_AXIS"
    ]
    if not candidates:
        return None
    nearest = candidates[-1]
    if owner["page_sequence"] - nearest["page_sequence"] > 2:
        return None
    return nearest


def _document_period_axes(
    lines: list[dict[str, Any]], start: int, owner: Mapping[str, Any]
) -> list[dict[str, Any]]:
    support = _support()
    preceding = lines[max(0, start - _DOCUMENT_UNIT_LOOKBACK_LINES) : start]
    candidates = [
        line
        for line in preceding
        if support._axis_role(line["normalized_text"]) == "PERIOD_AXIS"
        and owner["page_sequence"] - line["page_sequence"] <= 2
    ]
    return candidates[-4:]


def _region(lines: list[dict[str, Any]], start: int) -> dict[str, Any]:
    support = _support()
    owner = lines[start]
    window = _window(lines, start)
    prefix = [
        line
        for line in lines[max(0, start - 10) : start]
        if line["page_sequence"] == owner["page_sequence"]
    ]
    events = [support._line_ref(owner, "OWNER")]
    children: list[tuple[str, Mapping[str, Any]]] = []
    period_count = 0
    unit_count = 0
    numeric_lines = []
    for line in [*prefix, *window]:
        text = line["normalized_text"]
        child = _child_role(text)
        axis = support._axis_role(text)
        if child is not None:
            children.append((child, line))
            events.append(support._line_ref(line, child))
        elif axis is not None:
            events.append(support._line_ref(line, axis))
            period_count += axis == "PERIOD_AXIS"
            unit_count += axis == "UNIT_AXIS"
        if line in window and axis is None and support._NUMBER.fullmatch(text):
            numeric_lines.append(line)

    unit_scope = "LOCAL_PAGE_UNIT_AXIS"
    if unit_count == 0:
        inherited = _document_unit(lines, start, owner)
        if inherited is not None:
            events.append(support._line_ref(inherited, "DOCUMENT_UNIT_AXIS"))
            unit_count = 1
            unit_scope = "NEAREST_PRECEDING_DOCUMENT_UNIT_AXIS"
        else:
            unit_scope = "NO_UNIT_AXIS"

    period_scope = "LOCAL_PAGE_PERIOD_AXIS"
    if period_count < 2:
        inherited_periods = _document_period_axes(lines, start, owner)
        if len(inherited_periods) >= 2:
            events.extend(
                support._line_ref(line, "DOCUMENT_PERIOD_AXIS") for line in inherited_periods
            )
            period_count = len(inherited_periods)
            period_scope = "NEAREST_PRECEDING_DOCUMENT_PERIOD_AXIS"
        else:
            period_scope = "NO_COMPLETE_PERIOD_AXIS"

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

    core = {"DEPOSIT_INTEREST", "BORROWING_INTEREST"}
    complete = (
        core.issubset(child_roles)
        and len(numeric_lines) >= 8
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
            "period_axis_scope": period_scope,
            "presentation": "OWNER_FLEXIBLE_CHILD_ORDER_TWO_PERIOD_VALUE_LANES",
            "printed_parent_total_position": total_position,
            "unit_axis_line_count": unit_count,
            "unit_axis_scope": unit_scope,
        },
        "numeric_line_count": len(numeric_lines),
        "owner": support._line_ref(owner, "OWNER"),
        "page_span": [owner["page_sequence"], end["page_sequence"]],
        "pair_anchor_combinations": [
            list(pair) for pair in itertools.combinations(dict.fromkeys(anchor_roles), 2)
        ],
        "start_global_ordinal": owner["global_ordinal"],
    }


def _metrics(regions: list[dict[str, Any]], near: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "complete_region_count": len(regions),
        "document_unit_inheritance_region_count": sum(
            item["layout"]["unit_axis_scope"] == "NEAREST_PRECEDING_DOCUMENT_UNIT_AXIS"
            for item in regions
        ),
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
        raise _error("interest-expense result fields drifted")
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
        raise _error("interest-expense result identity or metrics drifted")
    count = len(value["regions"])
    status = "ACCEPTED_UNIQUE_VARIANT_GRAPH" if count == 1 else "UNRESOLVED_NO_UNIQUE_REGION"
    uniqueness = {
        "complete_region_count": count,
        "status": "UNIQUE_FULL_MATCH" if count == 1 else "NOT_UNIQUE_FULL_MATCH",
    }
    if value["status"] != status or not same_typed_json_v1(value["uniqueness"], uniqueness):
        raise _error("interest-expense uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "ievgv1:graph:" + canonical_json_sha256_v1(material):
        raise _error("interest-expense graph identity drifted")
    return canonical_clone_v1(value)


def build_interest_expense_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
    """Enumerate every interest-expense-like region in one complete PDF."""

    try:
        parsed = _support()._pages(pages)
    except Exception as exc:
        raise _error(str(exc)) from exc
    lines = _support()._flatten(parsed)
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
        {**material, "result_id": "ievgv1:graph:" + canonical_json_sha256_v1(material)}
    )


def validate_interest_expense_variant_graph_replay_v1(value: Any, pages: Any) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_interest_expense_variant_graph_document_v1(pages)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("interest-expense graph does not replay exactly")
    return supplied
