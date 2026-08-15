"""Bank-blind graph for service-income, service-expense and net-service notes.

The graph starts from the net-service disclosure owner and requires both the
income and expense parents plus at least one service child under each parent.
Children are optional and unordered because banks disclose different service
populations.  Printed parent totals may precede or follow their children, and
the final net may be labelled or unlabelled.  Complete PDFs are enumerated so
statement totals, accounting-policy prose and segment reports remain explicit
negative controls rather than being routed by bank, page or note number.

Fresh VietOCR Transformer text is anchor evidence only.  Pixel labels, the
independent source numeric axis, periods, units, signs and exact accounting
equations are required by the bounded mapping stage.
"""

from __future__ import annotations

import importlib.util
import itertools
import re
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
    "ServiceActivityVariantGraphV1Error",
    "build_service_activity_variant_graph_document_v1",
    "validate_service_activity_variant_graph_replay_v1",
]

FORMAT_VERSION = "SERVICE_ACTIVITY_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "SERVICE_ACTIVITY_INCOME_EXPENSE_NET"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_NET_SERVICE_OWNER_INCOME_EXPENSE_"
    "PARENTS_OPTIONAL_UNORDERED_CHILDREN_FLEXIBLE_PARENT_TOTAL_AND_NET_"
    "POSITION_STRUCTURE_ONLY_NO_NUMERIC_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_or_routing": False,
    "complete_pdf_region_enumeration_required": True,
    "fresh_vietocr_transformer_text_required": True,
    "mapping_authority": False,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "optional_children_and_child_order_may_vary_without_bank_rules": True,
    "pair_search_exhausted_before_larger_combinations": True,
    "persisted_result_self_authenticating": False,
    "printed_income_and_expense_totals_may_precede_or_follow_children": True,
    "printed_net_total_may_be_labelled_or_unlabelled": True,
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
    "Lãi thuần từ hoạt động dịch vụ",
    "Lãi/lỗ thuần từ hoạt động dịch vụ",
    "Lỗ/lãi thuần từ hoạt động dịch vụ",
)
_MAX_REGION_LINES = 80


class ServiceActivityVariantGraphV1Error(ValueError):
    """The complete-PDF input or service-activity graph drifted."""


def _error(message: str) -> ServiceActivityVariantGraphV1Error:
    return ServiceActivityVariantGraphV1Error(message)


def _support() -> ModuleType:
    name = "interest_income_graph_support_for_service_activity"
    if name in sys.modules:
        return sys.modules[name]
    path = Path(__file__).with_name("interest_income_variant_graph_v1.py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error("cannot load common accounting graph support")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _strip_enumerator(text: str) -> str:
    value = _support()._strip_enumerator(text)
    return re.sub(r"^(?:[ivx]+)\s+", "", value).strip()


def _is_owner(text: str) -> bool:
    value = _strip_enumerator(text)
    return len(value.split()) <= 14 and (
        match_vietnamese_anchor_alias_v1(value, _OWNER_ALIASES) is not None
    )


def _is_next_family(text: str) -> bool:
    value = _strip_enumerator(text)
    if len(value.split()) > 22:
        return False
    return any(
        phrase in value
        for phrase in (
            "lai thuan tu hoat dong kinh doanh ngoai hoi",
            "lai lo thuan tu hoat dong kinh doanh ngoai hoi",
            "lai thuan tu mua ban chung khoan",
            "lai lo thuan tu mua ban chung khoan",
            "thu nhap hoat dong khac",
            "lai thuan tu hoat dong khac",
        )
    )


def _section_parent(text: str) -> str | None:
    value = _strip_enumerator(text)
    if len(value.split()) > 12 or _is_owner(value):
        return None
    if value in {
        "thu nhap tu hoat dong dich vu",
        "thu nhap hoat dong dich vu",
    }:
        return "INCOME_PARENT"
    if value in {
        "chi phi tu hoat dong dich vu",
        "chi phi hoat dong dich vu",
    }:
        return "EXPENSE_PARENT"
    return None


def _child_role(text: str, section: str | None) -> str | None:
    if section not in {"INCOME", "EXPENSE"}:
        return None
    value = _strip_enumerator(text)
    if len(value.split()) > 18 or _section_parent(value) is not None or _is_owner(value):
        return None
    prefix = "INCOME" if section == "INCOME" else "EXPENSE"
    if "thanh toan" in value or "ngan quy" in value:
        return f"{prefix}_PAYMENT_TREASURY"
    if "tu van" in value:
        return f"{prefix}_CONSULTING"
    if "bao hiem" in value:
        return f"{prefix}_INSURANCE"
    if "uy thac" in value or "dai ly" in value:
        return f"{prefix}_TRUST_AGENCY"
    if any(phrase in value for phrase in ("xu ly no", "tham dinh", "khai thac tai san")):
        return f"{prefix}_DEBT_VALUATION"
    if "moi gioi" in value or "chung khoan" in value:
        return f"{prefix}_BROKERAGE"
    if "the" in value:
        return f"{prefix}_CARD"
    if "buu dien" in value or "vien thong" in value:
        return f"{prefix}_TELECOM"
    if "khac" in value:
        return f"{prefix}_OTHER"
    return None


def _window(lines: list[dict[str, Any]], start: int) -> list[dict[str, Any]]:
    owner = lines[start]
    window = []
    for line in lines[start + 1 : start + 1 + _MAX_REGION_LINES]:
        if line["page_sequence"] != owner["page_sequence"] or _is_next_family(
            line["normalized_text"]
        ):
            break
        window.append(line)
    return window


def _position(
    parent: Mapping[str, Any] | None,
    children: list[tuple[str, Mapping[str, Any]]],
    numerics: list[Mapping[str, Any]],
    next_parent: Mapping[str, Any] | None,
) -> str:
    if parent is None or not children:
        return "NO_PRINTED_PARENT_TOTAL_POSITION"
    first_child = min(line["global_ordinal"] for _, line in children)
    last_child = max(line["global_ordinal"] for _, line in children)
    stop = next_parent["global_ordinal"] if next_parent is not None else 10**12
    leading = sum(
        parent["global_ordinal"] < line["global_ordinal"] < first_child for line in numerics
    )
    trailing = sum(last_child < line["global_ordinal"] < stop for line in numerics)
    if leading >= 2:
        return "LEADING_PARENT_TOTAL_BEFORE_CHILDREN"
    if trailing >= 2:
        return "TRAILING_UNLABELED_TOTAL_AFTER_CHILDREN"
    return "NO_PRINTED_PARENT_TOTAL_POSITION"


def _region(lines: list[dict[str, Any]], start: int) -> dict[str, Any]:
    support = _support()
    owner = lines[start]
    window = _window(lines, start)
    events = [support._line_ref(owner, "OWNER")]
    parents: dict[str, Mapping[str, Any]] = {}
    children: dict[str, list[tuple[str, Mapping[str, Any]]]] = {
        "INCOME": [],
        "EXPENSE": [],
    }
    numerics: list[Mapping[str, Any]] = []
    section: str | None = None
    period_count = 0
    unit_count = 0
    for line in window:
        text = line["normalized_text"]
        parent = _section_parent(text)
        axis = support._axis_role(text)
        if parent is not None:
            section = "INCOME" if parent == "INCOME_PARENT" else "EXPENSE"
            parents[parent] = line
            events.append(support._line_ref(line, parent))
            continue
        child = _child_role(text, section)
        if child is not None:
            children[section].append((child, line))
            events.append(support._line_ref(line, child))
        elif axis is not None:
            events.append(support._line_ref(line, axis))
            period_count += axis == "PERIOD_AXIS"
            unit_count += axis == "UNIT_AXIS"
        if axis is None and support._NUMBER.fullmatch(text):
            numerics.append(line)

    income_position = _position(
        parents.get("INCOME_PARENT"),
        children["INCOME"],
        numerics,
        parents.get("EXPENSE_PARENT"),
    )
    expense_position = _position(parents.get("EXPENSE_PARENT"), children["EXPENSE"], numerics, None)
    income_roles = {role for role, _ in children["INCOME"]}
    expense_roles = {role for role, _ in children["EXPENSE"]}
    complete = (
        set(parents) == {"INCOME_PARENT", "EXPENSE_PARENT"}
        and bool(income_roles)
        and bool(expense_roles)
        and len(numerics) >= 10
        and period_count >= 2
        and unit_count >= 1
        and income_position != "NO_PRINTED_PARENT_TOTAL_POSITION"
        and expense_position != "NO_PRINTED_PARENT_TOTAL_POSITION"
    )
    anchor_roles = [
        "OWNER",
        *sorted(parents),
        *sorted(income_roles | expense_roles),
        "PERIOD_AXIS",
        "UNIT_AXIS",
    ]
    end = window[-1] if window else owner
    return {
        "anchor_roles": anchor_roles,
        "complete": complete,
        "end_global_ordinal": end["global_ordinal"],
        "events": events,
        "layout": {
            "expense_child_roles": sorted(expense_roles),
            "expense_parent_total_position": expense_position,
            "income_child_roles": sorted(income_roles),
            "income_parent_total_position": income_position,
            "period_axis_line_count": period_count,
            "presentation": (
                "NET_OWNER_INCOME_PARENT_OPTIONAL_CHILDREN_EXPENSE_PARENT_"
                "OPTIONAL_CHILDREN_FLEXIBLE_TOTALS"
            ),
            "unit_axis_line_count": unit_count,
        },
        "numeric_line_count": len(numerics),
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
        "leading_income_total_region_count": sum(
            item["layout"]["income_parent_total_position"] == "LEADING_PARENT_TOTAL_BEFORE_CHILDREN"
            for item in regions
        ),
        "leading_expense_total_region_count": sum(
            item["layout"]["expense_parent_total_position"]
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
        "trailing_income_total_region_count": sum(
            item["layout"]["income_parent_total_position"]
            == "TRAILING_UNLABELED_TOTAL_AFTER_CHILDREN"
            for item in regions
        ),
        "trailing_expense_total_region_count": sum(
            item["layout"]["expense_parent_total_position"]
            == "TRAILING_UNLABELED_TOTAL_AFTER_CHILDREN"
            for item in regions
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("service-activity result fields drifted")
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
        raise _error("service-activity result identity or metrics drifted")
    count = len(value["regions"])
    expected_status = (
        "ACCEPTED_UNIQUE_VARIANT_GRAPH" if count == 1 else "UNRESOLVED_NO_UNIQUE_REGION"
    )
    expected_uniqueness = {
        "complete_region_count": count,
        "status": "UNIQUE_FULL_MATCH" if count == 1 else "NOT_UNIQUE_FULL_MATCH",
    }
    if value["status"] != expected_status or not same_typed_json_v1(
        value["uniqueness"], expected_uniqueness
    ):
        raise _error("service-activity uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "savgv1:graph:" + canonical_json_sha256_v1(material):
        raise _error("service-activity graph identity drifted")
    return canonical_clone_v1(value)


def build_service_activity_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
    """Enumerate every service-activity-like region in one complete PDF."""

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
        "status": (
            "ACCEPTED_UNIQUE_VARIANT_GRAPH" if len(regions) == 1 else "UNRESOLVED_NO_UNIQUE_REGION"
        ),
        "uniqueness": {
            "complete_region_count": len(regions),
            "status": "UNIQUE_FULL_MATCH" if len(regions) == 1 else "NOT_UNIQUE_FULL_MATCH",
        },
    }
    return _validate_result(
        {**material, "result_id": "savgv1:graph:" + canonical_json_sha256_v1(material)}
    )


def validate_service_activity_variant_graph_replay_v1(value: Any, pages: Any) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_service_activity_variant_graph_document_v1(pages)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("service-activity graph does not replay exactly")
    return supplied
