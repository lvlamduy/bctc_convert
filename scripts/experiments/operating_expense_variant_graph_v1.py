"""Bank-blind variant graph for the operating-expense disclosure.

The core is deliberately small: an Arabic-numbered detailed-note owner, two
period lanes, a monetary unit, at least two top-level expense parents, and a
printed two-lane total after the observed rows.  Employee, asset and
administrative children are contextual: their parent must precede them, but
their presence and sibling order may vary.  Direct tax, deposit-insurance,
provision, IT, non-deductible VAT and other-operating rows are optional.

Fresh VietOCR Transformer text is anchor evidence only.  Numbers, schema,
mapping, canonicalization and export authority remain outside this graph.
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
    "OperatingExpenseVariantGraphV1Error",
    "build_operating_expense_variant_graph_document_v1",
    "validate_operating_expense_variant_graph_replay_v1",
]

FORMAT_VERSION = "OPERATING_EXPENSE_VARIANT_GRAPH_DOCUMENT_V1"
_MAX_REGION_LINES = 96
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
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_ARABIC_NUMBERED_OPERATING_"
    "EXPENSE_NOTE_TWO_PERIOD_UNIT_MULTIPLE_TOP_LEVEL_EXPENSE_PARENTS_"
    "OPTIONAL_CONTEXT_BOUND_CHILDREN_AND_TRAILING_TOTAL_STRUCTURE_ONLY_"
    "NO_NUMERIC_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_or_routing": False,
    "child_order_may_vary_without_bank_rules": True,
    "complete_pdf_region_enumeration_required": True,
    "fresh_vietocr_transformer_text_required": True,
    "mapping_authority": False,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "optional_children_supported": True,
    "pair_search_exhausted_before_larger_combinations": True,
    "parent_must_precede_contextual_children": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "statement_aggregate_without_arabic_detailed_note_can_accept": False,
    "text_similarity_alone_can_accept": False,
}
_TOP_LEVEL_ROLES = {
    "ADMINISTRATION",
    "ASSET",
    "DEPOSIT_INSURANCE",
    "EMPLOYEE",
    "IT",
    "NONDEDUCTIBLE_VAT",
    "OTHER_OPERATING",
    "PROVISION",
    "TAX_AND_FEES",
}


class OperatingExpenseVariantGraphV1Error(ValueError):
    """The complete-PDF input or operating-expense graph drifted."""


def _error(message: str) -> OperatingExpenseVariantGraphV1Error:
    return OperatingExpenseVariantGraphV1Error(message)


def _support() -> ModuleType:
    name = "interest_income_graph_support_for_operating_expense"
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
    return value in {
        "chi phi hoat dong",
        "chi phi quan ly chung",
        "chi phi quan ly",
    } or value.startswith("chi phi quan ly chung chi phi hoat dong")


def _has_inline_arabic_enumerator(text: str) -> bool:
    return re.match(r"^\d{1,3}\s+chi phi (?:hoat dong|quan ly)", text) is not None


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


def _owner_number(lines: Sequence[Mapping[str, Any]], start: int) -> int | None:
    match = re.match(r"^(\d{1,3})\s+", lines[start]["normalized_text"])
    if match is not None:
        return int(match.group(1))
    if start > 0 and re.fullmatch(r"\d{1,3}", lines[start - 1]["normalized_text"]):
        return int(lines[start - 1]["normalized_text"])
    return None


def _is_next_section(
    line: Mapping[str, Any], owner: Mapping[str, Any], owner_number: int | None
) -> bool:
    if line["bbox"][0] > owner["bbox"][0] + 200 or owner_number is None:
        return False
    match = re.match(r"^(\d{1,3})(?:\s+[a-z]|$)", line["normalized_text"])
    return match is not None and int(match.group(1)) > owner_number


def _window(lines: Sequence[Mapping[str, Any]], start: int) -> list[Mapping[str, Any]]:
    owner = lines[start]
    owner_number = _owner_number(lines, start)
    result: list[Mapping[str, Any]] = []
    for line in lines[start + 1 : start + 1 + _MAX_REGION_LINES]:
        if line["page_sequence"] != owner["page_sequence"] or _is_next_section(
            line, owner, owner_number
        ):
            break
        result.append(line)
    return result


def _top_level_role(text: str) -> str | None:
    value = _strip_enumerator(text)
    if len(value.split()) > 22:
        return None
    if ("nop thue" in value or "chi phi thue" in value) and ("phi" in value or "le phi" in value):
        return "TAX_AND_FEES"
    if value in {"chi phi cho nhan vien", "chi cho nhan vien"}:
        return "EMPLOYEE"
    if value in {"chi ve tai san", "chi phi ve tai san"}:
        return "ASSET"
    if "hoat dong quan ly cong vu" in value:
        return "ADMINISTRATION"
    if "bao hiem" in value and "tien gui" in value:
        return "DEPOSIT_INSURANCE"
    if "du phong" in value and not any(
        token in value for token in ("rui ro tin dung", "chung khoan kinh doanh")
    ):
        return "PROVISION"
    if "cong nghe thong tin" in value:
        return "IT"
    if "thue gtgt" in value and "khong duoc khau tru" in value:
        return "NONDEDUCTIBLE_VAT"
    if value in {"chi phi hoat dong khac", "chi phi quan ly hoat dong khac"}:
        return "OTHER_OPERATING"
    return None


def _contextual_child_role(text: str, context: str | None) -> str | None:
    value = _strip_enumerator(text)
    if len(value.split()) > 24:
        return None
    if context == "EMPLOYEE":
        if "luong" in value and "phu cap" in value:
            return "SALARY_AND_ALLOWANCE"
        if "dong gop theo luong" in value:
            return "PAYROLL_CONTRIBUTIONS"
        if "tro cap" in value:
            return "EMPLOYEE_BENEFIT"
        if value in {"khac", "chi khac", "cac khoan chi khac", "chi khac cho nhan vien"}:
            return "OTHER_EMPLOYEE"
    if context == "ASSET":
        if "khau hao" in value or "khau tru" in value:
            return "DEPRECIATION"
        if "thue tai san" in value:
            return "ASSET_RENT"
        if "khac ve tscd" in value or "chi khac ve tai san" in value:
            return "OTHER_ASSET"
    if context == "ADMINISTRATION":
        if "cong tac phi" in value:
            return "TRAVEL"
        if "hoat dong doan the" in value:
            return "UNION_ACTIVITY"
        if value in {"khac", "chi khac", "cac khoan chi khac"}:
            return "OTHER_ADMINISTRATION"
    return None


def _region(lines: Sequence[Mapping[str, Any]], start: int) -> dict[str, Any]:
    support = _support()
    owner = lines[start]
    window = _window(lines, start)
    events = [support._line_ref(owner, "OWNER")]
    roles: list[str] = []
    top_level_roles: list[str] = []
    period_count = 0
    unit_count = 0
    context: str | None = None
    numeric_lines: list[Mapping[str, Any]] = []
    last_role_ordinal = -1
    header_fragments: list[str] = []
    first_top_level_seen = False
    for line in window:
        text = line["normalized_text"]
        if not first_top_level_seen:
            header_fragments.append(text)
        axis = support._axis_role(text)
        if axis is not None:
            events.append(support._line_ref(line, axis))
            period_count += axis == "PERIOD_AXIS"
            unit_count += axis == "UNIT_AXIS"
            continue
        role = _top_level_role(text)
        if role is not None:
            first_top_level_seen = True
            context = role if role in {"ADMINISTRATION", "ASSET", "EMPLOYEE"} else None
            top_level_roles.append(role)
        else:
            role = _contextual_child_role(text, context)
        if role is not None:
            roles.append(role)
            last_role_ordinal = line["global_ordinal"]
            events.append(support._line_ref(line, role))
        if support._NUMBER.fullmatch(text) and line["bbox"][0] > owner["bbox"][0] + 500:
            numeric_lines.append(line)

    trailing_numeric_count = sum(
        line["global_ordinal"] > last_role_ordinal for line in numeric_lines
    )
    unique_top = list(dict.fromkeys(top_level_roles))
    unique_roles = list(dict.fromkeys(roles))
    complete = (
        len(unique_top) >= 2
        and len(numeric_lines) >= 6
        and period_count >= 2
        and unit_count >= 1
        and trailing_numeric_count >= 2
    )
    anchor_roles = ["OWNER", *unique_top, "PERIOD_AXIS", "UNIT_AXIS"]
    end = window[-1] if window else owner
    return {
        "anchor_roles": anchor_roles,
        "complete": complete,
        "end_global_ordinal": end["global_ordinal"],
        "events": events,
        "layout": {
            "all_observed_roles": unique_roles,
            "contextual_child_roles": [r for r in unique_roles if r not in _TOP_LEVEL_ROLES],
            "parent_precedes_contextual_children": True,
            "period_axis_line_count": period_count,
            "presentation": "OPTIONAL_TOP_LEVEL_ROWS_WITH_CONTEXT_BOUND_CHILDREN_THEN_TOTAL",
            "q1_period_context": "3 thang" in " ".join(header_fragments)
            and "31 thang 3" in " ".join(header_fragments),
            "top_level_roles": unique_top,
            "trailing_numeric_count_after_last_observed_role": trailing_numeric_count,
            "unit_axis_line_count": unit_count,
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
        "contextual_child_region_count": sum(
            bool(item["layout"]["contextual_child_roles"]) for item in regions
        ),
        "near_region_count": len(near),
        "numeric_line_count_in_complete_regions": sum(
            item["numeric_line_count"] for item in regions
        ),
        "page_count_with_complete_region": len(
            {item["owner"]["page_sequence"] for item in regions}
        ),
        "q1_axis_region_count": sum(item["layout"]["q1_period_context"] for item in regions),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("operating-expense graph fields drifted")
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
        raise _error("operating-expense graph identity or metrics drifted")
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
        raise _error("operating-expense graph uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "oevgv1:graph:" + canonical_json_sha256_v1(material):
        raise _error("operating-expense graph identity drifted")
    return canonical_clone_v1(value)


def build_operating_expense_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
    """Enumerate every complete operating-expense note in one PDF."""

    try:
        parsed = _support()._pages(pages)
    except Exception as exc:
        raise _error(str(exc)) from exc
    lines = _support()._flatten(parsed)
    candidates = [_region(lines, i) for i in range(len(lines)) if _is_owner(lines, i)]
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
        {**material, "result_id": "oevgv1:graph:" + canonical_json_sha256_v1(material)}
    )


def validate_operating_expense_variant_graph_replay_v1(value: Any, pages: Any) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_operating_expense_variant_graph_document_v1(pages)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("operating-expense graph does not replay exactly")
    return supplied
