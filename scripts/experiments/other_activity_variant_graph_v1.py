"""Bank-blind variant graph for detailed other-activity income/expense notes."""

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

FORMAT_VERSION = "OTHER_ACTIVITY_VARIANT_GRAPH_DOCUMENT_V1"
_MAX_LINES = 56
_FIELDS = {
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
_CLAIM = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_ARABIC_NUMBERED_DETAILED_OTHER_"
    "ACTIVITY_NOTE_OPTIONAL_NET_ONLY_OR_GROSS_INCOME_EXPENSE_CHILDREN_TWO_"
    "PERIOD_UNIT_AND_TRAILING_NET_STRUCTURE_ONLY_NO_NUMERIC_SCHEMA_MAPPING_"
    "OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_or_routing": False,
    "complete_pdf_region_enumeration_required": True,
    "fresh_vietocr_transformer_text_required": True,
    "gross_income_expense_and_net_only_variants_supported": True,
    "mapping_authority": False,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "optional_rows_supported": True,
    "pair_search_exhausted_before_larger_combinations": True,
    "parent_must_precede_contextual_children": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "segment_statement_or_policy_text_can_accept": False,
    "text_similarity_alone_can_accept": False,
}


class OtherActivityVariantGraphV1Error(ValueError):
    """The semantic input or other-activity graph drifted."""


def _error(message: str) -> OtherActivityVariantGraphV1Error:
    return OtherActivityVariantGraphV1Error(message)


def _support() -> ModuleType:
    name = "interest_income_graph_support_for_other_activity"
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


def _strip(text: str) -> str:
    value = _support()._strip_enumerator(text)
    return re.sub(r"^(?:[ivx]+)\s+", "", value).strip()


def _owner_text(text: str) -> bool:
    value = _strip(text)
    return value.startswith("lai thuan tu hoat dong khac") or value.startswith(
        "lai thuan tu hoat dong kinh doanh khac"
    )


def _owner(lines: Sequence[Mapping[str, Any]], index: int) -> bool:
    line = lines[index]
    if not _owner_text(line["normalized_text"]):
        return False
    if re.match(r"^\d{1,3}\s+", line["normalized_text"]):
        return True
    if index == 0:
        return False
    previous = lines[index - 1]
    overlap = min(previous["bbox"][3], line["bbox"][3]) - max(previous["bbox"][1], line["bbox"][1])
    return (
        previous["page_sequence"] == line["page_sequence"]
        and re.fullmatch(r"\d{1,3}", previous["normalized_text"]) is not None
        and previous["bbox"][0] < line["bbox"][0]
        and overlap > 0
    )


def _owner_number(lines: Sequence[Mapping[str, Any]], start: int) -> int | None:
    match = re.match(r"^(\d{1,3})\s+", lines[start]["normalized_text"])
    if match:
        return int(match.group(1))
    if start and re.fullmatch(r"\d{1,3}", lines[start - 1]["normalized_text"]):
        return int(lines[start - 1]["normalized_text"])
    return None


def _window(lines: Sequence[Mapping[str, Any]], start: int) -> list[Mapping[str, Any]]:
    owner = lines[start]
    number = _owner_number(lines, start)
    result = []
    for line in lines[start + 1 : start + 1 + _MAX_LINES]:
        if line["page_sequence"] != owner["page_sequence"]:
            break
        match = re.match(r"^(\d{1,3})(?:\s+[a-z]|$)", line["normalized_text"])
        if (
            match
            and number is not None
            and int(match.group(1)) > number
            and line["bbox"][0] <= owner["bbox"][0] + 200
        ):
            break
        result.append(line)
    return result


def _role(text: str) -> str | None:
    value = _strip(text)
    if len(value.split()) > 24:
        return None
    if _owner_text(value):
        return "NET_TOTAL"
    if "thu nhap chi phi khac" in value:
        return "NET_OTHER"
    expense = value.startswith("chi ") or value.startswith("chi phi")
    if value.startswith("thu nhap tu hoat dong khac"):
        return "INCOME_PARENT"
    if value.startswith("chi phi cho hoat dong khac") or value.startswith("chi phi hoat dong khac"):
        return "EXPENSE_PARENT"
    if "cong cu tai chinh phai sinh khac" in value:
        if expense:
            return "EXPENSE_DERIVATIVE"
        if value.startswith("lai "):
            return "NET_DERIVATIVE"
        return "INCOME_DERIVATIVE"
    if "no da xu ly" in value or "no da xoa" in value:
        return "DEBT_RECOVERY"
    if "thanh ly tai san" in value:
        return "EXPENSE_ASSET_DISPOSAL" if expense else "INCOME_ASSET_DISPOSAL"
    if "hoat dong ban no" in value or "nghiep vu mua ban no" in value:
        return "EXPENSE_DEBT_SALE" if expense else "INCOME_DEBT_SALE"
    if "phat vi pham hop dong" in value:
        return "INCOME_CONTRACT_PENALTY"
    if value in {"thu nhap khac", "thu khac"}:
        return "INCOME_OTHER"
    if value in {"chi khac", "chi phi khac"}:
        return "EXPENSE_OTHER"
    return None


def _region(lines: Sequence[Mapping[str, Any]], start: int) -> dict[str, Any]:
    support = _support()
    owner = lines[start]
    window = _window(lines, start)
    events = [support._line_ref(owner, "OWNER")]
    roles: list[str] = []
    role_ordinals: dict[str, int] = {}
    period_count = 0
    unit_count = 0
    numeric = []
    last_role = -1
    q1_fragments = []
    first_role = False
    for index, line in enumerate(window):
        text = line["normalized_text"]
        if not first_role:
            q1_fragments.append(text)
        axis = support._axis_role(text)
        if axis:
            events.append(support._line_ref(line, axis))
            period_count += axis == "PERIOD_AXIS"
            unit_count += axis == "UNIT_AXIS"
            continue
        role = _role(text)
        if role is None and index + 1 < len(window):
            following = window[index + 1]["normalized_text"]
            if not support._NUMBER.fullmatch(following):
                role = _role(f"{text} {following}")
        if role:
            first_role = True
            roles.append(role)
            role_ordinals.setdefault(role, line["global_ordinal"])
            last_role = line["global_ordinal"]
            events.append(support._line_ref(line, role))
        if support._NUMBER.fullmatch(text) and line["bbox"][0] > owner["bbox"][0] + 500:
            numeric.append(line)
    observed = list(dict.fromkeys(roles))
    gross = "INCOME_PARENT" in observed and "EXPENSE_PARENT" in observed
    income_children = [
        role
        for role in observed
        if (role.startswith("INCOME_") and role != "INCOME_PARENT") or role == "DEBT_RECOVERY"
    ]
    expense_children = [
        role for role in observed if role.startswith("EXPENSE_") and role != "EXPENSE_PARENT"
    ]
    net_components = [
        role for role in observed if role in {"DEBT_RECOVERY", "NET_DERIVATIVE", "NET_OTHER"}
    ]
    parent_order = not gross or (
        all(role_ordinals["INCOME_PARENT"] < role_ordinals[role] for role in income_children)
        and all(role_ordinals["EXPENSE_PARENT"] < role_ordinals[role] for role in expense_children)
    )
    trailing = sum(line["global_ordinal"] > last_role for line in numeric)
    complete = (
        period_count >= 2
        and unit_count >= 1
        and len(numeric) >= 8
        and trailing >= 2
        and parent_order
        and (
            (gross and len(income_children) >= 2 and len(expense_children) >= 1)
            or len(net_components) >= 2
        )
    )
    anchors = ["OWNER", *[r for r in observed if r != "NET_TOTAL"], "PERIOD_AXIS", "UNIT_AXIS"]
    end = window[-1] if window else owner
    return {
        "anchor_roles": anchors,
        "complete": complete,
        "end_global_ordinal": end["global_ordinal"],
        "events": events,
        "layout": {
            "observed_roles": observed,
            "parent_precedes_contextual_children": parent_order,
            "period_axis_line_count": period_count,
            "presentation": (
                "GROSS_INCOME_AND_EXPENSE_WITH_OPTIONAL_CHILDREN_THEN_NET_TOTAL"
                if gross
                else "NET_ONLY_OPTIONAL_COMPONENTS_THEN_TOTAL"
            ),
            "q1_period_context": "3 thang" in " ".join(q1_fragments)
            and "31 thang 3" in " ".join(q1_fragments),
            "trailing_numeric_count_after_last_role": trailing,
            "unit_axis_line_count": unit_count,
        },
        "numeric_line_count": len(numeric),
        "owner": support._line_ref(owner, "OWNER"),
        "page_span": [owner["page_sequence"], end["page_sequence"]],
        "pair_anchor_combinations": [
            list(pair) for pair in itertools.combinations(dict.fromkeys(anchors), 2)
        ],
        "start_global_ordinal": owner["global_ordinal"],
    }


def _metrics(regions: list[dict[str, Any]], near: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "complete_region_count": len(regions),
        "gross_variant_region_count": sum(
            item["layout"]["presentation"].startswith("GROSS_") for item in regions
        ),
        "near_region_count": len(near),
        "net_only_variant_region_count": sum(
            item["layout"]["presentation"].startswith("NET_ONLY_") for item in regions
        ),
        "page_count_with_complete_region": len(
            {item["owner"]["page_sequence"] for item in regions}
        ),
        "q1_axis_region_count": sum(item["layout"]["q1_period_context"] for item in regions),
    }


def _validate(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("other-activity graph fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != _CLAIM
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["regions"]) is not list
        or type(value["near_regions"]) is not list
        or not same_typed_json_v1(
            value["metrics"], _metrics(value["regions"], value["near_regions"])
        )
    ):
        raise _error("other-activity graph identity drifted")
    count = len(value["regions"])
    expected_status = (
        "ACCEPTED_UNIQUE_VARIANT_GRAPH" if count == 1 else "UNRESOLVED_NO_UNIQUE_REGION"
    )
    expected_unique = {
        "complete_region_count": count,
        "status": "UNIQUE_FULL_MATCH" if count == 1 else "NOT_UNIQUE_FULL_MATCH",
    }
    if value["status"] != expected_status or not same_typed_json_v1(
        value["uniqueness"], expected_unique
    ):
        raise _error("other-activity uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "oavgv1:graph:" + canonical_json_sha256_v1(material):
        raise _error("other-activity graph ID drifted")
    return canonical_clone_v1(value)


def build_other_activity_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
    try:
        parsed = _support()._pages(pages)
    except Exception as exc:
        raise _error(str(exc)) from exc
    lines = _support()._flatten(parsed)
    candidates = [_region(lines, i) for i in range(len(lines)) if _owner(lines, i)]
    regions = [item for item in candidates if item["complete"]]
    near = [item for item in candidates if not item["complete"]]
    material = {
        "claim_boundary": _CLAIM,
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
    return _validate(
        {**material, "result_id": "oavgv1:graph:" + canonical_json_sha256_v1(material)}
    )


def validate_other_activity_variant_graph_replay_v1(value: Any, pages: Any) -> dict[str, Any]:
    supplied = _validate(value)
    rebuilt = build_other_activity_variant_graph_document_v1(pages)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("other-activity graph does not replay exactly")
    return supplied
