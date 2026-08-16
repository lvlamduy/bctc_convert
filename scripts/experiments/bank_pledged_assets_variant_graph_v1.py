"""Bank-blind graph for assets pledged or discounted by the bank."""

from __future__ import annotations

import importlib.util
import itertools
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FORMAT_VERSION = "BANK_PLEDGED_ASSETS_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "BANK_PLEDGED_OR_DISCOUNTED_ASSETS"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_BANK_OWN_ASSET_PLEDGE_OWNER_"
    "PAIR_FIRST_OPTIONAL_USE_AND_ACCOUNTING_CLASS_ROWS_PERIOD_UNIT_TOTAL_"
    "STRUCTURE_ONLY_NO_NUMERIC_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_or_routing": False,
    "bank_own_asset_scope_required": True,
    "complete_pdf_region_enumeration_required": True,
    "customer_or_other_tctd_collateral_branch_can_accept": False,
    "fresh_vietocr_transformer_text_required": True,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
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


class BankPledgedAssetsVariantGraphV1Error(ValueError):
    """The complete-PDF input or bank-pledged-assets graph drifted."""


def _error(message: str) -> BankPledgedAssetsVariantGraphV1Error:
    return BankPledgedAssetsVariantGraphV1Error(message)


def _support() -> ModuleType:
    name = "interest_income_graph_support_for_bank_pledged_assets"
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
        "tai san" in value
        and ("gtcg" in value or "giay to co gia" in value)
        and "dua di" in value
        and ("the chap" in value or "cam co" in value or "chiet khau" in value)
    )


def _role(text: str) -> str | None:
    value = _strip(text)
    if "giay to co gia dua di the chap" in value or "giay to co gia dua di cam co" in value:
        return "PLEDGED_VALUABLE_PAPERS"
    if "giay to co gia dua di chiet khau" in value:
        return "DISCOUNTED_VALUABLE_PAPERS"
    if "giay to co gia thuoc chung khoan kinh doanh" in value:
        return "TRADING_SECURITIES"
    if "giay to co gia thuoc chung khoan dau tu" in value:
        return "INVESTMENT_SECURITIES"
    if "giay to co gia ban va cam ket mua lai" in value:
        return "REPURCHASED_VALUABLE_PAPERS"
    if "tai san khac dua di the chap" in value or "tai san khac dua di cam co" in value:
        return "OTHER_PLEDGED_ASSETS"
    return None


def _axis_role(text: str) -> str | None:
    value = text.strip()
    if "31 12 2025" in value or "31 thang 12" in value or "nam 2025" in value:
        return "COMPARATIVE_AXIS"
    if (
        "30 6 2026" in value
        or "30 06 2026" in value
        or "31 3 2026" in value
        or "31 thang 3" in value
        or "30 thang 6" in value
        or "nam 2026" in value
    ):
        return "CURRENT_AXIS"
    if "trieu dong" in value or "trieu vnd" in value:
        return "UNIT_AXIS"
    return None


def _region(page: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
    support = _support()
    roles: list[str] = []
    axes: list[str] = []
    events = [support._line_ref(owner, "BANK_OWN_ASSET_OWNER")]
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
    observed_roles = list(dict.fromkeys(roles))
    observed_axes = list(dict.fromkeys(axes))
    required_axes = {"CURRENT_AXIS", "COMPARATIVE_AXIS", "UNIT_AXIS"}
    complete = (
        len(observed_roles) >= 2 and required_axes.issubset(observed_axes) and numeric_count >= 6
    )
    anchors = ["BANK_OWN_ASSET_OWNER", *sorted(observed_roles), *sorted(required_axes)]
    return {
        "anchor_roles": anchors,
        "complete": complete,
        "end_global_ordinal": page["lines"][-1]["global_ordinal"],
        "events": events,
        "layout": {
            "observed_axis_roles": observed_axes,
            "observed_source_roles": observed_roles,
            "source_order_is_semantic": False,
        },
        "numeric_token_count": numeric_count,
        "owner": support._line_ref(owner, "BANK_OWN_ASSET_OWNER"),
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
        raise _error("bank-pledged-assets graph fields drifted")
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
        raise _error("bank-pledged-assets graph identity drifted")
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
        raise _error("bank-pledged-assets disposition drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "bpavgv1:graph:" + canonical_json_sha256_v1(material):
        raise _error("bank-pledged-assets graph ID drifted")
    return canonical_clone_v1(value)


def build_bank_pledged_assets_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
    parsed = _support()._pages(pages)
    candidates = []
    for page in parsed:
        owner = next((line for line in page["lines"] if _owner(line["normalized_text"])), None)
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
        {**material, "result_id": "bpavgv1:graph:" + canonical_json_sha256_v1(material)}
    )
