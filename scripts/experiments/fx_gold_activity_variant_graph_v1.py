"""Bank-blind graph for net foreign-exchange and gold activity notes.

The graph is intentionally family-wide rather than bank-specific.  It starts
from the net FX/gold disclosure owner, requires income and expense parents,
and admits optional children for spot FX, gold, currency derivatives, FX
differences and other items.  A filing may combine spot FX and gold into one
child, omit gold, reorder optional children, and print parent totals before or
after their children.  Full-document enumeration keeps income-statement
totals, accounting-policy prose, currency-risk tables and exchange-rate notes
as hard negative controls.

Fresh VietOCR Transformer text is anchor evidence only.  Numeric authority,
period/unit scope, accounting closure and schema mapping are deliberately
outside this structural matcher.
"""

from __future__ import annotations

import importlib.util
import itertools
import re
import sys
from collections.abc import Callable, Mapping, Sequence
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
    "FORMAT_VERSION_V2",
    "FxGoldActivityVariantGraphV1Error",
    "build_fx_gold_activity_variant_graph_document_v1",
    "build_fx_gold_activity_variant_graph_document_v2",
    "validate_fx_gold_activity_variant_graph_replay_v1",
    "validate_fx_gold_activity_variant_graph_replay_v2",
]

FORMAT_VERSION = "FX_GOLD_ACTIVITY_VARIANT_GRAPH_DOCUMENT_V1"
FORMAT_VERSION_V2 = "FX_GOLD_ACTIVITY_VARIANT_GRAPH_DOCUMENT_V2"
FAMILY_ID = "NET_FOREIGN_EXCHANGE_AND_GOLD_ACTIVITY"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_NET_FX_GOLD_OWNER_INCOME_EXPENSE_"
    "PARENTS_OPTIONAL_UNORDERED_CHILDREN_COMBINED_OR_SPLIT_SPOT_GOLD_"
    "FLEXIBLE_PARENT_TOTAL_POSITION_STRUCTURE_ONLY_NO_NUMERIC_SCHEMA_MAPPING_"
    "OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_or_routing": False,
    "combined_or_split_spot_fx_and_gold_children_supported": True,
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
    "public_exact_replay_required": True,
    "text_similarity_alone_can_accept": False,
}
_CLAIM_BOUNDARY_V2 = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_NET_FX_GOLD_OWNER_INCOME_"
    "EXPENSE_PARENTS_OPTIONAL_UNORDERED_CHILDREN_COMBINED_OR_SPLIT_SPOT_"
    "GOLD_REVALUATION_DERIVATIVE_AND_FX_DIFFERENCE_FLEXIBLE_PARENT_TOTAL_"
    "POSITION_STRUCTURE_ONLY_NO_NUMERIC_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
_SAFETY_V2 = {
    **_SAFETY,
    "generic_preposition_variants_supported": True,
    "gold_sale_and_revaluation_rows_supported": True,
    "currency_derivative_word_may_be_implicit_under_fx_parent": True,
    "spot_fx_and_gold_combination_requires_giao_ngay_token": False,
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
    "Lãi thuần từ hoạt động kinh doanh vàng và ngoại hối",
    "Lãi thuần từ hoạt động kinh doanh ngoại hối",
    "Lãi/lỗ thuần từ hoạt động kinh doanh vàng và ngoại hối",
    "Lãi/lỗ thuần từ hoạt động kinh doanh ngoại hối",
    "Lỗ/lãi thuần từ hoạt động kinh doanh vàng và ngoại hối",
    "Lỗ/lãi thuần từ hoạt động kinh doanh ngoại hối",
)
_MAX_REGION_LINES = 52


class FxGoldActivityVariantGraphV1Error(ValueError):
    """The complete-PDF input or FX/gold graph drifted."""


def _error(message: str) -> FxGoldActivityVariantGraphV1Error:
    return FxGoldActivityVariantGraphV1Error(message)


def _support() -> ModuleType:
    name = "interest_income_graph_support_for_fx_gold_activity"
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
    return len(value.split()) <= 17 and (
        match_vietnamese_anchor_alias_v1(value, _OWNER_ALIASES) is not None
    )


def _is_next_family(text: str) -> bool:
    value = _strip_enumerator(text)
    if len(value.split()) > 23:
        return False
    return any(
        phrase in value
        for phrase in (
            "lai thuan tu chung khoan kinh doanh",
            "lai lo thuan tu mua ban chung khoan",
            "lai thuan tu mua ban chung khoan",
            "lai thuan tu hoat dong kinh doanh khac",
            "lai thuan tu hoat dong khac",
        )
    )


def _section_parent(text: str) -> str | None:
    value = _strip_enumerator(text)
    if len(value.split()) > 15 or _is_owner(value):
        return None
    if any(
        phrase in value
        for phrase in (
            "thu nhap tu hoat dong kinh doanh vang va ngoai hoi",
            "thu nhap tu hoat dong kinh doanh ngoai hoi",
            "thu nhap hoat dong kinh doanh ngoai hoi",
        )
    ):
        return "INCOME_PARENT"
    if any(
        phrase in value
        for phrase in (
            "chi phi tu hoat dong kinh doanh vang va ngoai hoi",
            "chi phi tu hoat dong kinh doanh ngoai hoi",
            "chi phi hoat dong kinh doanh ngoai hoi",
        )
    ):
        return "EXPENSE_PARENT"
    return None


def _section_parent_v2(text: str) -> str | None:
    """Recognize family-equivalent parent wording without report-specific rules."""

    parent = _section_parent(text)
    if parent is not None:
        return parent
    value = _strip_enumerator(text)
    if len(value.split()) > 15 or _is_owner(value):
        return None
    if "thu nhap" in value and "hoat dong kinh doanh" in value and "ngoai hoi" in value:
        return "INCOME_PARENT"
    if "chi phi" in value and "hoat dong kinh doanh" in value and "ngoai hoi" in value:
        return "EXPENSE_PARENT"
    return None


def _child_role(text: str, section: str | None) -> str | None:
    if section not in {"INCOME", "EXPENSE"}:
        return None
    value = _strip_enumerator(text)
    if len(value.split()) > 18 or _section_parent(value) is not None or _is_owner(value):
        return None
    prefix = "INCOME" if section == "INCOME" else "EXPENSE"
    if "ngoai te giao ngay" in value and "vang" in value:
        return f"{prefix}_SPOT_FX_AND_GOLD"
    if "ngoai te giao ngay" in value:
        return f"{prefix}_SPOT_FX"
    if "kinh doanh vang" in value:
        return f"{prefix}_GOLD"
    if "phai sinh" in value and any(token in value for token in ("tien te", "ngoai hoi")):
        return f"{prefix}_CURRENCY_DERIVATIVES"
    if "chenh lech ty gia" in value:
        return f"{prefix}_FX_DIFFERENCE"
    if "khac" in value:
        return f"{prefix}_OTHER"
    return None


def _child_role_v2(text: str, section: str | None) -> str | None:
    """Classify optional FX/gold rows by accounting meaning inside a section.

    Currency/gold context comes from the already-established section parent.
    This deliberately avoids bank, page, note-number and filename routing.
    """

    role = _child_role(text, section)
    if role is not None:
        return role
    if section not in {"INCOME", "EXPENSE"}:
        return None
    value = _strip_enumerator(text)
    if len(value.split()) > 20 or _section_parent_v2(value) is not None or _is_owner(value):
        return None
    prefix = "INCOME" if section == "INCOME" else "EXPENSE"
    if "ngoai te" in value and "vang" in value:
        return f"{prefix}_SPOT_FX_AND_GOLD"
    if "phai sinh" in value:
        return f"{prefix}_CURRENCY_DERIVATIVES"
    if "chenh lech ty gia" in value:
        return f"{prefix}_FX_DIFFERENCE"
    if "vang" in value:
        return f"{prefix}_GOLD"
    if "ngoai te" in value and any(
        phrase in value for phrase in ("giao ngay", "mua ban", "kinh doanh")
    ):
        return f"{prefix}_SPOT_FX"
    if "khac" in value:
        return f"{prefix}_OTHER"
    return None


def _window(lines: Sequence[Mapping[str, Any]], start: int) -> list[Mapping[str, Any]]:
    owner = lines[start]
    window: list[Mapping[str, Any]] = []
    for line in lines[start + 1 : start + 1 + _MAX_REGION_LINES]:
        if line["page_sequence"] != owner["page_sequence"] or _is_next_family(
            line["normalized_text"]
        ):
            break
        window.append(line)
    return window


def _position(
    parent: Mapping[str, Any] | None,
    children: Sequence[tuple[str, Mapping[str, Any]]],
    numerics: Sequence[Mapping[str, Any]],
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


def _region(
    lines: Sequence[Mapping[str, Any]],
    start: int,
    *,
    parent_resolver: Callable[[str], str | None] = _section_parent,
    child_resolver: Callable[[str, str | None], str | None] = _child_role,
) -> dict[str, Any]:
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
        parent = parent_resolver(text)
        axis = support._axis_role(text)
        if parent is not None:
            section = "INCOME" if parent == "INCOME_PARENT" else "EXPENSE"
            parents[parent] = line
            events.append(support._line_ref(line, parent))
            continue
        child = child_resolver(text, section)
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
                "NET_FX_GOLD_OWNER_INCOME_PARENT_OPTIONAL_CHILDREN_EXPENSE_PARENT_"
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
        "leading_expense_total_region_count": sum(
            item["layout"]["expense_parent_total_position"]
            == "LEADING_PARENT_TOTAL_BEFORE_CHILDREN"
            for item in regions
        ),
        "leading_income_total_region_count": sum(
            item["layout"]["income_parent_total_position"] == "LEADING_PARENT_TOTAL_BEFORE_CHILDREN"
            for item in regions
        ),
        "near_region_count": len(near),
        "numeric_line_count_in_complete_regions": sum(
            item["numeric_line_count"] for item in regions
        ),
        "page_count_with_complete_region": len(
            {item["owner"]["page_sequence"] for item in regions}
        ),
        "trailing_expense_total_region_count": sum(
            item["layout"]["expense_parent_total_position"]
            == "TRAILING_UNLABELED_TOTAL_AFTER_CHILDREN"
            for item in regions
        ),
        "trailing_income_total_region_count": sum(
            item["layout"]["income_parent_total_position"]
            == "TRAILING_UNLABELED_TOTAL_AFTER_CHILDREN"
            for item in regions
        ),
    }


def _validate_result_config(
    value: Any,
    *,
    format_version: str,
    claim_boundary: str,
    safety: Mapping[str, Any],
    result_prefix: str,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("FX/gold result fields drifted")
    if (
        value["format_version"] != format_version
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != claim_boundary
        or not same_typed_json_v1(value["safety"], safety)
        or type(value["regions"]) is not list
        or type(value["near_regions"]) is not list
        or not same_typed_json_v1(
            value["metrics"], _metrics(value["regions"], value["near_regions"])
        )
    ):
        raise _error("FX/gold result identity or metrics drifted")
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
        raise _error("FX/gold uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != result_prefix + canonical_json_sha256_v1(material):
        raise _error("FX/gold graph identity drifted")
    return canonical_clone_v1(value)


def _validate_result(value: Any) -> dict[str, Any]:
    return _validate_result_config(
        value,
        format_version=FORMAT_VERSION,
        claim_boundary=CLAIM_BOUNDARY,
        safety=_SAFETY,
        result_prefix="fxgav1:graph:",
    )


def _build(
    pages: Any,
    *,
    format_version: str,
    claim_boundary: str,
    safety: Mapping[str, Any],
    result_prefix: str,
    parent_resolver: Callable[[str], str | None],
    child_resolver: Callable[[str, str | None], str | None],
) -> dict[str, Any]:
    try:
        parsed = _support()._pages(pages)
    except Exception as exc:
        raise _error(str(exc)) from exc
    lines = _support()._flatten(parsed)
    candidates = [
        _region(
            lines,
            index,
            parent_resolver=parent_resolver,
            child_resolver=child_resolver,
        )
        for index, line in enumerate(lines)
        if _is_owner(line["normalized_text"])
    ]
    regions = [item for item in candidates if item["complete"]]
    near = [item for item in candidates if not item["complete"]]
    material = {
        "claim_boundary": claim_boundary,
        "family_id": FAMILY_ID,
        "format_version": format_version,
        "metrics": _metrics(regions, near),
        "near_regions": near,
        "regions": regions,
        "safety": canonical_clone_v1(safety),
        "status": (
            "ACCEPTED_UNIQUE_VARIANT_GRAPH" if len(regions) == 1 else "UNRESOLVED_NO_UNIQUE_REGION"
        ),
        "uniqueness": {
            "complete_region_count": len(regions),
            "status": "UNIQUE_FULL_MATCH" if len(regions) == 1 else "NOT_UNIQUE_FULL_MATCH",
        },
    }
    return _validate_result_config(
        {**material, "result_id": result_prefix + canonical_json_sha256_v1(material)},
        format_version=format_version,
        claim_boundary=claim_boundary,
        safety=safety,
        result_prefix=result_prefix,
    )


def build_fx_gold_activity_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
    """Enumerate every detailed FX/gold-activity-like region in one complete PDF."""

    return _build(
        pages,
        format_version=FORMAT_VERSION,
        claim_boundary=CLAIM_BOUNDARY,
        safety=_SAFETY,
        result_prefix="fxgav1:graph:",
        parent_resolver=_section_parent,
        child_resolver=_child_role,
    )


def build_fx_gold_activity_variant_graph_document_v2(pages: Any) -> dict[str, Any]:
    """Enumerate the generic annual-compatible FX/gold graph variants."""

    return _build(
        pages,
        format_version=FORMAT_VERSION_V2,
        claim_boundary=_CLAIM_BOUNDARY_V2,
        safety=_SAFETY_V2,
        result_prefix="fxgav2:graph:",
        parent_resolver=_section_parent_v2,
        child_resolver=_child_role_v2,
    )


def validate_fx_gold_activity_variant_graph_replay_v1(value: Any, pages: Any) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_fx_gold_activity_variant_graph_document_v1(pages)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("FX/gold graph does not replay exactly")
    return supplied


def validate_fx_gold_activity_variant_graph_replay_v2(value: Any, pages: Any) -> dict[str, Any]:
    supplied = _validate_result_config(
        value,
        format_version=FORMAT_VERSION_V2,
        claim_boundary=_CLAIM_BOUNDARY_V2,
        safety=_SAFETY_V2,
        result_prefix="fxgav2:graph:",
    )
    rebuilt = build_fx_gold_activity_variant_graph_document_v2(pages)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("FX/gold V2 graph does not replay exactly")
    return supplied
