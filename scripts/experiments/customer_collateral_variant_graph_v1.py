"""Bank-blind graph for customer-collateral disclosure variants."""

from __future__ import annotations

import importlib.util
import itertools
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.accounting_table_axes_v1 import extract_reporting_year_axis_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FORMAT_VERSION = "CUSTOMER_COLLATERAL_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "CUSTOMER_COLLATERAL_HELD"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_CUSTOMER_COLLATERAL_OWNER_"
    "PAIR_FIRST_CHILD_PERIOD_UNIT_TOTAL_STRUCTURE_ONLY_NO_NUMERIC_SCHEMA_"
    "MAPPING_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_or_routing": False,
    "complete_pdf_region_enumeration_required": True,
    "customer_scope_required": True,
    "fresh_vietocr_transformer_text_required": True,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "optional_children_and_source_order_supported": True,
    "pair_search_exhausted_before_larger_combinations": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
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


class CustomerCollateralVariantGraphV1Error(ValueError):
    """The complete-PDF input or customer-collateral graph drifted."""


def _error(message: str) -> CustomerCollateralVariantGraphV1Error:
    return CustomerCollateralVariantGraphV1Error(message)


def _support() -> ModuleType:
    name = "interest_income_graph_support_for_customer_collateral"
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


def _direct_owner(text: str) -> bool:
    value = _strip(text)
    return "tai san the chap cua khach hang" in value or (
        "tai san dam bao" in value and "nam giu" in value and "tai san the chap" in value
    )


def _generic_owner(page: Mapping[str, Any]) -> Mapping[str, Any] | None:
    has_collateral_title = any(
        "tai san" in line["normalized_text"]
        and ("the chap" in line["normalized_text"] or "cam co" in line["normalized_text"])
        for line in page["lines"]
    )
    if not has_collateral_title:
        return None
    return next(
        (
            line
            for line in page["lines"]
            if _strip(line["normalized_text"]) in {"cua khach hang", "khach hang"}
        ),
        None,
    )


def _role(text: str) -> str | None:
    value = _strip(text)
    if value == "bat dong san":
        return "REAL_ESTATE"
    if value == "dong san":
        return "MOVABLE_PROPERTY"
    if value in {"may moc thiet bi", "may moc thiet bi khac"}:
        return "MACHINERY_EQUIPMENT"
    if value in {"phuong tien van tai", "phuong tien van tai thiet bi truyen dan"}:
        return "TRANSPORT_EQUIPMENT"
    if value in {"hang ton kho", "hang hoa luu kho"}:
        return "INVENTORY"
    if value == "giay to co gia":
        return "VALUABLE_PAPERS"
    if "tai san dam bao khac" in value or "tai san the chap khac" in value:
        return "OTHER_COLLATERAL"
    if value == "tien gui":
        return "DEPOSIT_SOURCE_ONLY"
    if value == "quyen khai thac tai san":
        return "EXPLOITATION_RIGHT_SOURCE_ONLY"
    if value == "bao lanh":
        return "GUARANTEE_SOURCE_ONLY"
    if value == "vang ngoai te giay to co gia":
        return "COMBINED_GOLD_FX_VALUABLE_PAPERS_SOURCE_ONLY"
    return None


def _axis_role(text: str) -> str | None:
    value = text.strip()
    if "trieu dong" in value or "trieu vnd" in value:
        return "UNIT_AXIS"
    return None


def _region(page: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
    support = _support()
    roles: list[str] = []
    axes: list[str] = []
    events = [support._line_ref(owner, "CUSTOMER_OWNER")]
    numeric_count = 0
    for index, line in enumerate(page["lines"]):
        text = line["normalized_text"]
        role = _role(text)
        if role is not None:
            roles.append(role)
            events.append(support._line_ref(line, role))
        axis = _axis_role(text)
        if axis is None and index + 1 < len(page["lines"]):
            axis = _axis_role(f"{text} {page['lines'][index + 1]['normalized_text']}")
        if axis is not None:
            axes.append(axis)
            events.append(support._line_ref(line, axis))
        numeric_count += support._NUMBER.fullmatch(text) is not None
    line_by_index = {line["source_line_index"]: line for line in page["lines"]}
    year_axis, _year_axis_mode = extract_reporting_year_axis_v1(page["lines"])
    for item in year_axis:
        axis = "CURRENT_AXIS" if item["role"] == "CURRENT_PERIOD" else "COMPARATIVE_AXIS"
        if axis not in axes:
            axes.append(axis)
            line = line_by_index[item["evidence_source_line_indices"][0]]
            events.append(support._line_ref(line, axis))
    observed_roles = list(dict.fromkeys(roles))
    observed_axes = list(dict.fromkeys(axes))
    mapped_children = {
        "REAL_ESTATE",
        "MOVABLE_PROPERTY",
        "MACHINERY_EQUIPMENT",
        "TRANSPORT_EQUIPMENT",
        "INVENTORY",
        "VALUABLE_PAPERS",
        "OTHER_COLLATERAL",
    }.intersection(observed_roles)
    required_axes = {"CURRENT_AXIS", "COMPARATIVE_AXIS", "UNIT_AXIS"}
    complete = (
        "REAL_ESTATE" in observed_roles
        and len(mapped_children) >= 2
        and required_axes.issubset(observed_axes)
        and numeric_count >= 8
    )
    anchors = ["CUSTOMER_OWNER", "REAL_ESTATE", *sorted(mapped_children), *sorted(required_axes)]
    return {
        "anchor_roles": anchors,
        "complete": complete,
        "end_global_ordinal": page["lines"][-1]["global_ordinal"],
        "events": events,
        "layout": {
            "observed_axis_roles": observed_axes,
            "observed_child_roles": observed_roles,
            "source_order_is_semantic": False,
        },
        "numeric_token_count": numeric_count,
        "owner": support._line_ref(owner, "CUSTOMER_OWNER"),
        "page_span": [page["page_sequence"], page["page_sequence"]],
        "pair_anchor_combinations": [list(pair) for pair in itertools.combinations(anchors, 2)],
        "start_global_ordinal": page["lines"][0]["global_ordinal"],
    }


def _metrics(regions: list[dict[str, Any]], near: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "complete_region_count": len(regions),
        "near_region_count": len(near),
        "page_count_with_complete_region": len(
            {item["owner"]["page_sequence"] for item in regions}
        ),
    }


def _validate(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("customer-collateral graph fields drifted")
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
        raise _error("customer-collateral graph identity drifted")
    count = len(value["regions"])
    expected_status = (
        "ACCEPTED_UNIQUE_VARIANT_GRAPH" if count == 1 else "UNRESOLVED_NO_UNIQUE_REGION"
    )
    uniqueness = (
        "UNIQUE_FULL_MATCH"
        if count == 1
        else "NO_FULL_MATCH"
        if count == 0
        else "MULTIPLE_FULL_MATCHES"
    )
    if value["status"] != expected_status or value["uniqueness"] != {
        "complete_region_count": count,
        "status": uniqueness,
    }:
        raise _error("customer-collateral disposition drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "ccvgv1:graph:" + canonical_json_sha256_v1(material):
        raise _error("customer-collateral graph ID drifted")
    return canonical_clone_v1(value)


def build_customer_collateral_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
    parsed = _support()._pages(pages)
    candidates = []
    for page in parsed:
        owner = next(
            (line for line in page["lines"] if _direct_owner(line["normalized_text"])), None
        )
        if owner is None:
            owner = _generic_owner(page)
        if owner is not None:
            candidates.append(_region(page, owner))
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
            "status": "UNIQUE_FULL_MATCH"
            if len(regions) == 1
            else "NO_FULL_MATCH"
            if not regions
            else "MULTIPLE_FULL_MATCHES",
        },
    }
    return _validate(
        {**material, "result_id": "ccvgv1:graph:" + canonical_json_sha256_v1(material)}
    )
