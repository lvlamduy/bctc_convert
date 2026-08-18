"""Bank-blind variant graph for trading or investment securities-sale activity.

One shared engine covers the two adjacent TM families.  A profile selects only
the semantic family owner; all structural rules remain identical: two period
axes, one unit, required income and expense children, an optional provision or
other child, and a printed net total.  Child order, wrapped labels and whether
the provision label says ``rủi ro`` or ``giảm giá`` may vary.  In particular,
text similarity cannot overrule the note owner, geometry, axes and accounting
closure later used by the mapping verifier.

Fresh VietOCR Transformer text is anchor evidence only.  The graph has no
numeric, schema, mapping, canonicalization or export authority.
"""

from __future__ import annotations

import importlib.util
import itertools
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "SecuritiesSaleActivityVariantGraphV1Error",
    "build_securities_sale_activity_variant_graph_document_v1",
    "validate_securities_sale_activity_variant_graph_replay_v1",
]

FORMAT_VERSION = "SECURITIES_SALE_ACTIVITY_VARIANT_GRAPH_DOCUMENT_V1"
_FAMILY_VARIANTS = {"INVESTMENT_SECURITIES", "TRADING_SECURITIES"}
_MAX_REGION_LINES = 42
_RESULT_FIELDS = {
    "claim_boundary",
    "family_variant",
    "format_version",
    "metrics",
    "near_regions",
    "regions",
    "result_id",
    "safety",
    "status",
    "uniqueness",
}
_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_or_routing": False,
    "child_order_may_vary_without_bank_rules": True,
    "complete_pdf_region_enumeration_required": True,
    "document_section_unit_inheritance_supported": True,
    "fresh_vietocr_transformer_text_required": True,
    "investment_and_trading_families_kept_distinct": True,
    "mapping_authority": False,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "optional_provision_or_other_child_supported": True,
    "pair_search_exhausted_before_larger_combinations": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "text_similarity_alone_can_accept": False,
}


class SecuritiesSaleActivityVariantGraphV1Error(ValueError):
    """The complete-PDF input or securities-sale graph drifted."""


def _error(message: str) -> SecuritiesSaleActivityVariantGraphV1Error:
    return SecuritiesSaleActivityVariantGraphV1Error(message)


def _support() -> ModuleType:
    name = "interest_income_graph_support_for_securities_sale_activity"
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


def _claim_boundary(family_variant: str) -> str:
    return (
        "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_"
        f"{family_variant}_SALE_NET_OWNER_REQUIRED_INCOME_EXPENSE_OPTIONAL_"
        "PROVISION_OR_OTHER_CHILD_FLEXIBLE_LABEL_WRAP_AND_ORDER_PERIOD_UNIT_"
        "TRAILING_NET_STRUCTURE_ONLY_NO_NUMERIC_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
    )


def _validate_family_variant(value: Any) -> str:
    if type(value) is not str or value not in _FAMILY_VARIANTS:
        raise _error("securities-sale family variant is not exact")
    return value


def _is_owner(text: str, family_variant: str) -> bool:
    value = _strip_enumerator(text)
    if len(value.split()) > 18:
        return False
    has_net = any(
        prefix in value
        for prefix in (
            "lai lo thuan tu",
            "lo lai thuan tu",
            "lai thuan tu",
            "lo thuan tu",
        )
    )
    if not has_net or "mua ban chung khoan" not in value:
        return False
    is_investment = "dau tu" in value
    if family_variant == "INVESTMENT_SECURITIES":
        return is_investment
    return not is_investment and (
        "kinh doanh" in value
        or value.endswith("mua ban chung khoan kinh")
        or value.endswith("mua ban chung khoan")
    )


def _is_next_family(text: str, family_variant: str) -> bool:
    value = _strip_enumerator(text)
    if len(value.split()) > 22:
        return False
    if family_variant == "TRADING_SECURITIES" and _is_owner(value, "INVESTMENT_SECURITIES"):
        return True
    if family_variant == "INVESTMENT_SECURITIES" and _is_owner(value, "TRADING_SECURITIES"):
        return True
    return any(
        phrase in value
        for phrase in (
            "thu nhap tu gop von mua co phan",
            "lai thuan tu hoat dong kinh doanh khac",
            "lai thuan tu hoat dong khac",
            "chi phi hoat dong",
        )
    )


def _child_role(text: str) -> str | None:
    value = _strip_enumerator(text)
    if len(value.split()) > 19:
        return None
    if "thu nhap" in value and "mua ban chung khoan" in value:
        return "INCOME"
    # Provision rows often begin with "Chi phi du phong ...".  Resolve the
    # more specific accounting role before the generic expense wording so the
    # same bank-blind rule works for CTG/BID as well as rows headed by
    # "Trich lap" or "Hoan nhap".
    if "du phong" in value:
        if "chung khoan" in value:
            return "PROVISION"
        if "gop von" in value or "dau tu dai han" in value:
            return "OTHER"
    if any(token in value for token in ("chi phi", "chi ve", "chi tu")) and (
        "mua ban chung khoan" in value or "chung khoan dau tu" in value
    ):
        return "EXPENSE"
    if value == "khac" or value.startswith("thu khac") or value.startswith("chi khac"):
        return "OTHER"
    return None


def _window(
    lines: Sequence[Mapping[str, Any]], start: int, family_variant: str
) -> list[Mapping[str, Any]]:
    owner = lines[start]
    window: list[Mapping[str, Any]] = []
    for line in lines[start + 1 : start + 1 + _MAX_REGION_LINES]:
        if line["page_sequence"] != owner["page_sequence"] or _is_next_family(
            line["normalized_text"], family_variant
        ):
            break
        window.append(line)
    return window


def _net_total_position(
    children: Sequence[tuple[str, Mapping[str, Any]]],
    numerics: Sequence[Mapping[str, Any]],
) -> str:
    if not children:
        return "NO_PRINTED_NET_TOTAL_POSITION"
    last_child = max(line["global_ordinal"] for _, line in children)
    if sum(line["global_ordinal"] > last_child for line in numerics) >= 2:
        return "TRAILING_NET_TOTAL_AFTER_CHILDREN"
    return "NO_PRINTED_NET_TOTAL_POSITION"


def _region(lines: Sequence[Mapping[str, Any]], start: int, family_variant: str) -> dict[str, Any]:
    support = _support()
    owner = lines[start]
    window = _window(lines, start, family_variant)
    prefix = [
        line
        for line in lines[max(0, start - 28) : start]
        if line["page_sequence"] == owner["page_sequence"]
    ]
    events = [support._line_ref(owner, "OWNER")]
    children: list[tuple[str, Mapping[str, Any]]] = []
    numerics: list[Mapping[str, Any]] = []
    period_count = 0
    unit_count = 0
    for line in [*prefix, *window]:
        axis = support._axis_role(line["normalized_text"])
        if axis is not None:
            events.append(support._line_ref(line, axis))
            period_count += axis == "PERIOD_AXIS"
            unit_count += axis == "UNIT_AXIS"

    inherited_document_unit = False
    if unit_count == 0:
        for line in reversed(lines[max(0, start - 150) : start]):
            text = line["normalized_text"]
            if line["page_sequence"] < owner["page_sequence"] - 1:
                break
            if text.startswith("don vi") and support._axis_role(text) == "UNIT_AXIS":
                events.append(support._line_ref(line, "INHERITED_UNIT_AXIS"))
                unit_count = 1
                inherited_document_unit = True
                break

    for offset, line in enumerate(window):
        text = line["normalized_text"]
        axis = support._axis_role(text)
        child = _child_role(text)
        if child is None and offset + 1 < len(window) and axis is None:
            following = window[offset + 1]
            following_text = following["normalized_text"]
            if (
                support._NUMBER.fullmatch(text) is None
                and support._axis_role(following_text) is None
                and support._NUMBER.fullmatch(following_text) is None
            ):
                child = _child_role(f"{text} {following_text}")
        if child is not None:
            children.append((child, line))
            events.append(support._line_ref(line, child))
        if axis is None and support._NUMBER.fullmatch(text):
            numerics.append(line)

    roles = {role for role, _ in children}
    total_position = _net_total_position(children, numerics)
    complete = (
        {"INCOME", "EXPENSE"}.issubset(roles)
        and len(numerics) >= 4
        and period_count >= 2
        and unit_count >= 1
        and total_position == "TRAILING_NET_TOTAL_AFTER_CHILDREN"
    )
    anchor_roles = [
        "OWNER",
        *sorted(roles),
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
            "child_roles": sorted(roles),
            "inherited_document_unit_used": inherited_document_unit,
            "net_total_position": total_position,
            "period_axis_line_count": period_count,
            "presentation": (
                "SECURITIES_SALE_NET_OWNER_REQUIRED_INCOME_EXPENSE_"
                "OPTIONAL_PROVISION_OR_OTHER_TRAILING_NET"
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
        "near_region_count": len(near),
        "numeric_line_count_in_complete_regions": sum(
            item["numeric_line_count"] for item in regions
        ),
        "page_count_with_complete_region": len(
            {item["owner"]["page_sequence"] for item in regions}
        ),
        "provision_child_region_count": sum(
            "PROVISION" in item["layout"]["child_roles"] for item in regions
        ),
        "trailing_net_total_region_count": sum(
            item["layout"]["net_total_position"] == "TRAILING_NET_TOTAL_AFTER_CHILDREN"
            for item in regions
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("securities-sale result fields drifted")
    family_variant = _validate_family_variant(value["family_variant"])
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != _claim_boundary(family_variant)
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["regions"]) is not list
        or type(value["near_regions"]) is not list
        or not same_typed_json_v1(
            value["metrics"], _metrics(value["regions"], value["near_regions"])
        )
    ):
        raise _error("securities-sale result identity or metrics drifted")
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
        raise _error("securities-sale uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "ssav1:graph:" + canonical_json_sha256_v1(material):
        raise _error("securities-sale graph identity drifted")
    return canonical_clone_v1(value)


def build_securities_sale_activity_variant_graph_document_v1(
    pages: Any, *, family_variant: str
) -> dict[str, Any]:
    """Enumerate every detailed trading- or investment-sale region in one PDF."""

    family_variant = _validate_family_variant(family_variant)
    try:
        parsed = _support()._pages(pages)
    except Exception as exc:
        raise _error(str(exc)) from exc
    lines = _support()._flatten(parsed)
    candidates = [
        _region(lines, index, family_variant)
        for index, line in enumerate(lines)
        if _is_owner(line["normalized_text"], family_variant)
    ]
    regions = [item for item in candidates if item["complete"]]
    near = [item for item in candidates if not item["complete"]]
    material = {
        "claim_boundary": _claim_boundary(family_variant),
        "family_variant": family_variant,
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
        {**material, "result_id": "ssav1:graph:" + canonical_json_sha256_v1(material)}
    )


def validate_securities_sale_activity_variant_graph_replay_v1(
    value: Any, pages: Any, *, family_variant: str
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_securities_sale_activity_variant_graph_document_v1(
        pages, family_variant=family_variant
    )
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("securities-sale graph does not replay exactly")
    return supplied
