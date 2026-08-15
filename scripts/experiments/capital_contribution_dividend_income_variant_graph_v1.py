"""Bank-blind graph for capital-contribution, share and dividend income.

The detailed note begins at an Arabic-numbered note boundary, carries two
period lanes and a local or document-level monetary unit, then contains one or
more income children and a printed two-lane total.  Children may be collapsed
into one parent row, split by trading/investment/long-term capital source,
include an equity-method share or another income row, and may wrap or reorder.

Fresh VietOCR is anchor evidence only.  Numeric, schema, mapping and export
authority remain outside this graph.
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
    "CapitalContributionDividendIncomeVariantGraphV1Error",
    "build_capital_contribution_dividend_income_variant_graph_document_v1",
    "validate_capital_contribution_dividend_income_variant_graph_replay_v1",
]

FORMAT_VERSION = "CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_VARIANT_GRAPH_DOCUMENT_V1"
_MAX_REGION_LINES = 48
_RESULT_FIELDS = {
    "claim_boundary",
    "format_version",
    "metrics",
    "near_regions",
    "regions",
    "result_id",
    "safety",
    "status",
    "uniqueness",
}
_CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_ARABIC_NUMBERED_CAPITAL_"
    "CONTRIBUTION_SHARE_AND_DIVIDEND_INCOME_NOTE_TWO_PERIOD_UNIT_OPTIONAL_"
    "GENERAL_OR_SOURCE_SPLIT_DIVIDEND_EQUITY_METHOD_OR_OTHER_CHILD_AND_"
    "TRAILING_TOTAL_STRUCTURE_ONLY_NO_NUMERIC_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_or_routing": False,
    "child_order_may_vary_without_bank_rules": True,
    "collapsed_parent_only_variant_supported": True,
    "complete_pdf_region_enumeration_required": True,
    "document_section_unit_inheritance_supported": True,
    "fresh_vietocr_transformer_text_required": True,
    "mapping_authority": False,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "optional_children_supported": True,
    "pair_search_exhausted_before_larger_combinations": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "statement_aggregate_without_detailed_note_axes_can_accept": False,
    "text_similarity_alone_can_accept": False,
}


class CapitalContributionDividendIncomeVariantGraphV1Error(ValueError):
    """The complete-PDF input or contribution/dividend graph drifted."""


def _error(message: str) -> CapitalContributionDividendIncomeVariantGraphV1Error:
    return CapitalContributionDividendIncomeVariantGraphV1Error(message)


def _support() -> ModuleType:
    name = "interest_income_graph_support_for_capital_contribution_dividend"
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


def _is_owner_text(text: str) -> bool:
    value = _strip_enumerator(text)
    return (
        len(value.split()) <= 14
        and value.startswith("thu nhap tu gop von mua co phan")
        and "giam" not in value
        and "thoi gian" not in value
    )


def _has_inline_arabic_enumerator(text: str) -> bool:
    return re.match(r"^\d{1,3}\s+thu nhap tu gop von mua co phan", text) is not None


def _is_owner(lines: Sequence[Mapping[str, Any]], index: int) -> bool:
    line = lines[index]
    if not _is_owner_text(line["normalized_text"]):
        return False
    if _has_inline_arabic_enumerator(line["normalized_text"]):
        return True
    if index == 0:
        return False
    previous = lines[index - 1]
    return (
        previous["page_sequence"] == line["page_sequence"]
        and re.fullmatch(r"\d{1,3}", previous["normalized_text"]) is not None
        and previous["bbox"][0] < line["bbox"][0]
        and min(previous["bbox"][3], line["bbox"][3]) - max(previous["bbox"][1], line["bbox"][1])
        > 0
    )


def _is_next_section(line: Mapping[str, Any], owner: Mapping[str, Any]) -> bool:
    text = line["normalized_text"]
    if line["bbox"][0] >= owner["bbox"][0]:
        return False
    if re.fullmatch(r"\d{1,3}", text) is not None:
        return True
    return re.match(r"^\d{1,3}\s+[a-z]", text) is not None


def _window(lines: Sequence[Mapping[str, Any]], start: int) -> list[Mapping[str, Any]]:
    owner = lines[start]
    window: list[Mapping[str, Any]] = []
    for line in lines[start + 1 : start + 1 + _MAX_REGION_LINES]:
        if line["page_sequence"] != owner["page_sequence"] or _is_next_section(line, owner):
            break
        window.append(line)
    return window


def _child_role(text: str) -> str | None:
    value = _strip_enumerator(text)
    if len(value.split()) > 22:
        return None
    if _is_owner_text(value):
        return "COLLAPSED_PARENT"
    if "phan chia lai" in value and "phuong phap von" in value:
        return "EQUITY_METHOD"
    if "hop nhat kinh doanh" in value and "thu nhap" in value:
        return "OTHER_INCOME"
    if "chung khoan von kinh doanh" in value:
        return "TRADING_EQUITY_DIVIDEND"
    if "chung khoan von dau tu" in value:
        return "INVESTMENT_EQUITY_DIVIDEND"
    if "gop von dau tu dai han" in value:
        return "LONG_TERM_CAPITAL_DIVIDEND"
    if "co tuc" in value and "gop von" in value:
        return "DIRECT_DIVIDEND"
    if value.startswith("thu tu chung khoan von"):
        return "COMBINED_EQUITY_SECURITIES_DIVIDEND"
    return None


def _region(lines: Sequence[Mapping[str, Any]], start: int) -> dict[str, Any]:
    support = _support()
    owner = lines[start]
    window = _window(lines, start)
    events = [support._line_ref(owner, "OWNER")]
    children: list[tuple[str, Mapping[str, Any]]] = []
    numerics: list[Mapping[str, Any]] = []
    period_count = 0
    unit_count = 0
    for offset, line in enumerate(window):
        text = line["normalized_text"]
        axis = support._axis_role(text)
        if axis is not None:
            events.append(support._line_ref(line, axis))
            period_count += axis == "PERIOD_AXIS"
            unit_count += axis == "UNIT_AXIS"
        child = _child_role(text)
        if child is None and offset + 1 < len(window) and axis is None:
            following = window[offset + 1]
            if (
                support._NUMBER.fullmatch(text) is None
                and support._axis_role(following["normalized_text"]) is None
                and support._NUMBER.fullmatch(following["normalized_text"]) is None
            ):
                child = _child_role(f"{text} {following['normalized_text']}")
        if child is not None:
            children.append((child, line))
            events.append(support._line_ref(line, child))
        if axis is None and support._NUMBER.fullmatch(text):
            numerics.append(line)

    inherited_document_unit = False
    if unit_count == 0:
        for line in reversed(lines[max(0, start - 180) : start]):
            if line["page_sequence"] < owner["page_sequence"] - 1:
                break
            text = line["normalized_text"]
            if text.startswith("don vi") and support._axis_role(text) == "UNIT_AXIS":
                events.append(support._line_ref(line, "INHERITED_UNIT_AXIS"))
                unit_count = 1
                inherited_document_unit = True
                break

    roles = {role for role, _ in children}
    last_child = max((line["global_ordinal"] for _, line in children), default=-1)
    trailing_numeric_count = sum(line["global_ordinal"] > last_child for line in numerics)
    total_position = (
        "TRAILING_TWO_PERIOD_TOTAL_AFTER_CHILDREN"
        if trailing_numeric_count >= 2
        else "NO_PRINTED_TWO_PERIOD_TOTAL_POSITION"
    )
    complete = (
        bool(roles)
        and len(numerics) >= 4
        and period_count >= 2
        and unit_count >= 1
        and total_position == "TRAILING_TWO_PERIOD_TOTAL_AFTER_CHILDREN"
    )
    anchor_roles = ["OWNER", *sorted(roles), "PERIOD_AXIS", "UNIT_AXIS"]
    end = window[-1] if window else owner
    return {
        "anchor_roles": anchor_roles,
        "complete": complete,
        "end_global_ordinal": end["global_ordinal"],
        "events": events,
        "layout": {
            "child_roles": sorted(roles),
            "inherited_document_unit_used": inherited_document_unit,
            "period_axis_line_count": period_count,
            "presentation": "OPTIONAL_DIVIDEND_SOURCE_EQUITY_METHOD_OR_OTHER_CHILDREN_THEN_TOTAL",
            "trailing_numeric_count_after_last_child": trailing_numeric_count,
            "total_position": total_position,
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
        "collapsed_parent_region_count": sum(
            "COLLAPSED_PARENT" in item["layout"]["child_roles"] for item in regions
        ),
        "complete_region_count": len(regions),
        "equity_method_region_count": sum(
            "EQUITY_METHOD" in item["layout"]["child_roles"] for item in regions
        ),
        "inherited_document_unit_region_count": sum(
            item["layout"]["inherited_document_unit_used"] for item in regions
        ),
        "near_region_count": len(near),
        "numeric_line_count_in_complete_regions": sum(
            item["numeric_line_count"] for item in regions
        ),
        "page_count_with_complete_region": len(
            {item["owner"]["page_sequence"] for item in regions}
        ),
        "q1_axis_region_count": sum(
            any(
                event["role"] == "PERIOD_AXIS"
                and "31 thang 3" in normalize_vietnamese_anchor_v1(event["vietocr_text"])
                for event in item["events"]
            )
            for item in regions
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("contribution/dividend graph fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != _CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["regions"]) is not list
        or type(value["near_regions"]) is not list
        or not same_typed_json_v1(
            value["metrics"], _metrics(value["regions"], value["near_regions"])
        )
    ):
        raise _error("contribution/dividend graph identity or metrics drifted")
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
        raise _error("contribution/dividend graph uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "ccdvgv1:graph:" + canonical_json_sha256_v1(material):
        raise _error("contribution/dividend graph identity drifted")
    return canonical_clone_v1(value)


def build_capital_contribution_dividend_income_variant_graph_document_v1(
    pages: Any,
) -> dict[str, Any]:
    """Enumerate every detailed contribution/dividend-income note in one PDF."""

    try:
        parsed = _support()._pages(pages)
    except Exception as exc:
        raise _error(str(exc)) from exc
    lines = _support()._flatten(parsed)
    candidates = [_region(lines, index) for index in range(len(lines)) if _is_owner(lines, index)]
    regions = [item for item in candidates if item["complete"]]
    near = [item for item in candidates if not item["complete"]]
    material = {
        "claim_boundary": _CLAIM_BOUNDARY,
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
        {**material, "result_id": "ccdvgv1:graph:" + canonical_json_sha256_v1(material)}
    )


def validate_capital_contribution_dividend_income_variant_graph_replay_v1(
    value: Any, pages: Any
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_capital_contribution_dividend_income_variant_graph_document_v1(pages)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("contribution/dividend graph does not replay exactly")
    return supplied
