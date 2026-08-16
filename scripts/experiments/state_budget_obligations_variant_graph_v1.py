"""Bank-blind graph for State-budget-obligation disclosure variants."""

from __future__ import annotations

import importlib.util
import itertools
import re
import sys
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FORMAT_VERSION = "STATE_BUDGET_OBLIGATIONS_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "STATE_BUDGET_OBLIGATIONS"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_STATE_BUDGET_OWNER_REQUIRED_"
    "TAX_CHILDREN_OPENING_PAYABLE_PAID_CLOSING_AXES_OPTIONAL_EXTRA_LANE_"
    "STRUCTURE_ONLY_NO_NUMERIC_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_or_routing": False,
    "complete_pdf_region_enumeration_required": True,
    "fresh_vietocr_transformer_text_required": True,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "optional_tax_rows_and_extra_movement_lanes_supported": True,
    "pair_search_exhausted_before_larger_combinations": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "tax_policy_or_income_tax_reconciliation_alone_can_accept": False,
    "text_similarity_alone_can_accept": False,
}
_FIELDS = {
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
_DATE_AXIS = re.compile(
    r"(?<![0-9])([0-3]?[0-9])(?:[./-]|\s+)([01]?[0-9])(?:[./-]|\s+)(20[0-9]{2})(?![0-9])"
)


class StateBudgetObligationsVariantGraphV1Error(ValueError):
    """The complete-PDF input or State-budget graph drifted."""


def _error(message: str) -> StateBudgetObligationsVariantGraphV1Error:
    return StateBudgetObligationsVariantGraphV1Error(message)


def _support() -> ModuleType:
    name = "interest_income_graph_support_for_state_budget_obligations"
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
    return _support()._strip_enumerator(text).lstrip("-+ ").strip()


def _owner(text: str) -> bool:
    value = _strip(text)
    return (
        "tinh hinh thuc hien nghia vu voi ngan sach nha nuoc" in value
        or "tinh hinh thuc hien nghia vu voi nsnn" in value
    )


def _role(text: str) -> str | None:
    value = _strip(text)
    if _owner(value):
        return "OWNER"
    if value in {"thue gtgt", "thue gia tri gia tang"}:
        return "VAT"
    if value in {"thue tndn", "thue tndn hien hanh", "thue thu nhap doanh nghiep"}:
        return "CORPORATE_INCOME_TAX"
    if value == "thue thu nhap ca nhan":
        return "PERSONAL_INCOME_TAX"
    if value == "thue nha dat":
        return "HOUSE_LAND_TAX"
    if value in {"cac loai thue khac", "thue khac"}:
        return "OTHER_TAX"
    if "cac khoan phi le phi" in value or "cac khoan phai nop khac" in value:
        return "OTHER_PAYABLE"
    if value == "thue nha thau":
        return "CONTRACTOR_TAX_DETAIL"
    if value == "tien thue dat":
        return "LAND_RENT_SOURCE_ONLY"
    if value in {"tong cong", "cong"}:
        return "TOTAL"
    return None


def _axis_role(text: str) -> str | None:
    value = text.strip()
    if "so du dau" in value or "so dau ky" in value or value == "dau ky":
        return "OPENING_AXIS"
    if "so phai nop" in value:
        return "PAYABLE_AXIS"
    if "so da nop" in value:
        return "PAID_AXIS"
    if "so du cuoi" in value or "so cuoi" in value:
        return "CLOSING_AXIS"
    if "tang do hop nhat kinh doanh" in value:
        return "BUSINESS_COMBINATION_INCREASE_AXIS"
    if value in {"phai tra", "phai thu", "tong cong"}:
        return "CLOSING_SUBAXIS"
    if "trieu dong" in value or "trieu vnd" in value:
        return "UNIT_AXIS"
    return None


def _date_axis(text: str) -> date | None:
    matched = _DATE_AXIS.search(text)
    if matched is None:
        return None
    day, month, year = map(int, matched.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _region(page: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
    support = _support()
    roles: list[str] = []
    axes: list[str] = []
    events = [support._line_ref(owner, "OWNER")]
    numeric_count = 0
    dated_lines: dict[date, Mapping[str, Any]] = {}
    lines = page["lines"]
    for index, line in enumerate(lines):
        text = line["normalized_text"]
        role = _role(text)
        if role is None and index + 1 < len(lines):
            role = _role(f"{text} {lines[index + 1]['normalized_text']}")
        if role is not None and role != "OWNER":
            roles.append(role)
            events.append(support._line_ref(line, role))
        axis = _axis_role(text)
        if axis is not None:
            axes.append(axis)
            events.append(support._line_ref(line, axis))
        if (observed_date := _date_axis(text)) is not None:
            dated_lines.setdefault(observed_date, line)
        if "so phai nop" in text and axis != "PAYABLE_AXIS":
            axes.append("PAYABLE_AXIS")
            events.append(support._line_ref(line, "PAYABLE_AXIS"))
        numeric_count += support._NUMBER.fullmatch(text) is not None
    if len(dated_lines) == 2:
        opening_date, closing_date = sorted(dated_lines)
        for role, observed_date in (
            ("OPENING_AXIS", opening_date),
            ("CLOSING_AXIS", closing_date),
        ):
            if role not in axes:
                axes.append(role)
                events.append(support._line_ref(dated_lines[observed_date], role))
    observed_roles = list(dict.fromkeys(roles))
    observed_axes = list(dict.fromkeys(axes))
    required_roles = {"VAT", "CORPORATE_INCOME_TAX", "OTHER_TAX"}
    required_axes = {"OPENING_AXIS", "PAYABLE_AXIS", "PAID_AXIS", "CLOSING_AXIS"}
    complete = (
        required_roles.issubset(observed_roles)
        and required_axes.issubset(observed_axes)
        and numeric_count >= 12
    )
    anchors = ["OWNER", *sorted(required_roles), *sorted(required_axes)]
    return {
        "anchor_roles": anchors,
        "complete": complete,
        "end_global_ordinal": lines[-1]["global_ordinal"],
        "events": events,
        "layout": {
            "document_unit_inheritance_required": "UNIT_AXIS" not in observed_axes,
            "observed_axis_roles": observed_axes,
            "observed_tax_roles": observed_roles,
        },
        "numeric_token_count": numeric_count,
        "owner": support._line_ref(owner, "OWNER"),
        "page_span": [page["page_sequence"], page["page_sequence"]],
        "pair_anchor_combinations": [list(pair) for pair in itertools.combinations(anchors, 2)],
        "start_global_ordinal": lines[0]["global_ordinal"],
    }


def _metrics(regions: list[dict[str, Any]], near: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "complete_region_count": len(regions),
        "document_unit_inheritance_region_count": sum(
            item["layout"]["document_unit_inheritance_required"] for item in regions
        ),
        "near_region_count": len(near),
        "page_count_with_complete_region": len(
            {item["owner"]["page_sequence"] for item in regions}
        ),
    }


def _validate(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("State-budget graph fields drifted")
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
        raise _error("State-budget graph identity drifted")
    expected_status = (
        "ACCEPTED_UNIQUE_VARIANT_GRAPH"
        if len(value["regions"]) == 1
        else "UNRESOLVED_NO_UNIQUE_REGION"
    )
    uniqueness = (
        "UNIQUE_FULL_MATCH"
        if len(value["regions"]) == 1
        else "NO_FULL_MATCH"
        if not value["regions"]
        else "MULTIPLE_FULL_MATCHES"
    )
    if value["status"] != expected_status or value["uniqueness"] != {
        "complete_region_count": len(value["regions"]),
        "status": uniqueness,
    }:
        raise _error("State-budget disposition drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "sbovgv1:graph:" + canonical_json_sha256_v1(material):
        raise _error("State-budget graph ID drifted")
    return canonical_clone_v1(value)


def build_state_budget_obligations_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
    parsed = _support()._pages(pages)
    candidates = []
    for page in parsed:
        owners = [line for line in page["lines"] if _owner(line["normalized_text"])]
        if owners:
            candidates.append(_region(page, owners[0]))
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
            "status": (
                "UNIQUE_FULL_MATCH"
                if len(regions) == 1
                else "NO_FULL_MATCH"
                if not regions
                else "MULTIPLE_FULL_MATCHES"
            ),
        },
    }
    return _validate(
        {**material, "result_id": "sbovgv1:graph:" + canonical_json_sha256_v1(material)}
    )
