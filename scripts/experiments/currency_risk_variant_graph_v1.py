"""Bank-blind complete-PDF variant graph for currency-risk tables."""

from __future__ import annotations

import importlib.util
import itertools
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

FORMAT_VERSION = "CURRENCY_RISK_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "CURRENCY_RISK"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_PAIR_FIRST_CURRENCY_RISK_OWNER_"
    "OPTIONAL_CURRENCY_AXES_ASSET_LIABILITY_STATE_TOPOLOGY_UNIT_AND_NUMERIC_"
    "STRUCTURE_ONLY_NO_NUMERIC_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_or_routing": False,
    "child_row_order_required_for_matching": False,
    "complete_pdf_region_enumeration_required": True,
    "currency_axis_order_required_for_matching": False,
    "fresh_vietocr_transformer_text_required": True,
    "interest_liquidity_or_fair_value_table_can_accept": False,
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
_ASSET_ROLES = {
    "ASSET_CASH",
    "ASSET_CENTRAL_BANK",
    "ASSET_CUSTOMER_LOANS",
    "ASSET_DERIVATIVE",
    "ASSET_FIXED_PROPERTY",
    "ASSET_INTERBANK",
    "ASSET_INVESTMENT_SECURITIES",
    "ASSET_LONG_TERM_INVESTMENT",
    "ASSET_OTHER",
    "ASSET_PURCHASED_DEBT",
    "ASSET_TRADING_SECURITIES",
}
_LIABILITY_ROLES = {
    "LIABILITY_CAPITAL",
    "LIABILITY_CUSTOMER_DEPOSITS",
    "LIABILITY_DERIVATIVE",
    "LIABILITY_ENTRUSTED_CAPITAL",
    "LIABILITY_GOVERNMENT_INTERBANK",
    "LIABILITY_ISSUED_PAPERS",
    "LIABILITY_OTHER",
}
_STATE_ROLES = {"STATE_COMBINED", "STATE_EXTERNAL", "STATE_INTERNAL"}


class CurrencyRiskVariantGraphV1Error(ValueError):
    """The complete-PDF input or currency-risk graph drifted."""


def _error(message: str) -> CurrencyRiskVariantGraphV1Error:
    return CurrencyRiskVariantGraphV1Error(message)


def _support() -> ModuleType:
    name = "interest_income_graph_support_for_currency_risk"
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
    return len(value.split()) <= 16 and ("rui ro tien te" in value or "rui ro ty gia" in value)


def _negative_family(text: str) -> str | None:
    value = _strip(text)
    if "rui ro lai suat" in value or "dinh gia lai lai suat" in value:
        return "INTEREST_RATE_RISK"
    if "rui ro thanh khoan" in value or "thoi han thanh toan" in value:
        return "LIQUIDITY_RISK"
    if "gia tri hop ly" in value:
        return "FINANCIAL_INSTRUMENTS"
    return None


def _unit(text: str) -> bool:
    value = _strip(text)
    return "trieu dong" in value or "trieu vnd" in value


def _currency_axes(text: str) -> set[str]:
    value = _strip(text)
    roles: set[str] = set()
    if "usd" in value or "do la my" in value or "do ia my" in value:
        roles.add("USD")
    if "eur" in value:
        roles.add("EUR")
    if value == "vnd" or (value.startswith("vnd ") and len(value.split()) <= 3):
        roles.add("VND")
    if "vang" in value and "tien mat" not in value:
        roles.add("GOLD")
    if any(
        phrase in value
        for phrase in (
            "cac loai ngoai te khac",
            "cac ngoai te khac",
            "ngoai te khac",
            "tien te khac",
        )
    ):
        roles.add("OTHER")
    if value in {"tong", "tong cong"}:
        roles.add("TOTAL")
    return roles


def _raw_role(text: str) -> str | None:
    value = _strip(text)
    if "trang thai tien te noi ngoai bang" in value:
        return "STATE_COMBINED"
    if "trang thai tien te ngoai bang" in value:
        return "STATE_EXTERNAL"
    if "trang thai tien te noi bang" in value:
        return "STATE_INTERNAL"
    if "tong no phai tra" in value:
        return "LIABILITY_TOTAL"
    if "tong tai san" in value:
        return "ASSET_TOTAL"
    if value in {"tai san", "tai san co"}:
        return "ASSET_SECTION"
    if value in {"no phai tra", "no phai tra va von chu so huu"}:
        return "LIABILITY_SECTION"
    if "tien mat" in value and any(token in value for token in ("vang", "da quy")):
        return "ASSET_CASH"
    if "tien gui tai nhnn" in value or "tien gui tai ngan hang nha nuoc" in value:
        return "ASSET_CENTRAL_BANK"
    if "cho vay khach hang" in value:
        return "ASSET_CUSTOMER_LOANS"
    if "mua no" in value:
        return "ASSET_PURCHASED_DEBT"
    if "chung khoan kinh doanh" in value:
        return "ASSET_TRADING_SECURITIES"
    if "chung khoan dau tu" in value:
        return "ASSET_INVESTMENT_SECURITIES"
    if "gop von" in value or "dau tu dai han" in value:
        return "ASSET_LONG_TERM_INVESTMENT"
    if "tai san co dinh" in value or "bat dong san dau tu" in value:
        return "ASSET_FIXED_PROPERTY"
    if "tai san co khac" in value:
        return "ASSET_OTHER"
    if "cong cu tai chinh phai sinh" in value:
        return "DERIVATIVE_ROW"
    if "tien gui cua khach hang" in value:
        return "LIABILITY_CUSTOMER_DEPOSITS"
    if "von tai tro" in value and "uy thac" in value:
        return "LIABILITY_ENTRUSTED_CAPITAL"
    if "phat hanh giay to co gia" in value:
        return "LIABILITY_ISSUED_PAPERS"
    if "cac khoan no khac" in value:
        return "LIABILITY_OTHER"
    if "von va cac quy" in value:
        return "LIABILITY_CAPITAL"
    if (
        "tien gui" in value and ("vay" in value or "cap tin dung" in value)
    ) or "cac khoan no chinh phu" in value:
        return "INTERBANK_ROW"
    return None


def _joined_roles(page: Mapping[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    support = _support()
    roles: list[str] = []
    events: list[dict[str, Any]] = []
    after_asset_total = False
    lines = page["lines"]
    label_zone_limit = max(line["bbox"][2] for line in lines) * 0.48
    for index, line in enumerate(lines):
        candidates = [line["normalized_text"]]
        current_is_label = (
            line["bbox"][0] <= label_zone_limit
            and support._NUMBER.fullmatch(line["normalized_text"]) is None
        )
        if (
            current_is_label
            and index + 1 < len(lines)
            and lines[index + 1]["bbox"][0] <= label_zone_limit
            and support._NUMBER.fullmatch(lines[index + 1]["normalized_text"]) is None
        ):
            candidates.append(f"{candidates[-1]} {lines[index + 1]['normalized_text']}")
        if (
            len(candidates) == 2
            and index + 2 < len(lines)
            and lines[index + 2]["bbox"][0] <= label_zone_limit
            and support._NUMBER.fullmatch(lines[index + 2]["normalized_text"]) is None
        ):
            candidates.append(f"{candidates[-1]} {lines[index + 2]['normalized_text']}")
        role = next((found for value in candidates if (found := _raw_role(value))), None)
        if role is None:
            continue
        if role == "ASSET_TOTAL":
            after_asset_total = True
        elif role == "DERIVATIVE_ROW":
            role = "LIABILITY_DERIVATIVE" if after_asset_total else "ASSET_DERIVATIVE"
        elif role == "INTERBANK_ROW":
            role = "LIABILITY_GOVERNMENT_INTERBANK" if after_asset_total else "ASSET_INTERBANK"
        if role not in roles:
            roles.append(role)
            events.append(support._line_ref(line, role))
    return roles, events


def _header_features(page: Mapping[str, Any]) -> tuple[list[str], list[dict[str, Any]], int]:
    support = _support()
    cutoff = len(page["lines"])
    for index, line in enumerate(page["lines"]):
        role = _raw_role(line["normalized_text"])
        if role in _ASSET_ROLES | {"ASSET_SECTION", "ASSET_TOTAL"} or role in {
            "DERIVATIVE_ROW",
            "INTERBANK_ROW",
        }:
            cutoff = index
            break
    latest_axis_line: dict[str, Mapping[str, Any]] = {}
    unit_lines: list[Mapping[str, Any]] = []
    unit_count = 0
    for line in page["lines"][:cutoff]:
        for axis in _currency_axes(line["normalized_text"]):
            latest_axis_line[axis] = line
        if _unit(line["normalized_text"]):
            unit_count += 1
            unit_lines.append(line)
    needles = {
        "EUR": "eur",
        "GOLD": "vang",
        "OTHER": "te khac",
        "TOTAL": "tong",
        "USD": "usd",
        "VND": "vnd",
    }
    axes = sorted(
        latest_axis_line,
        key=lambda axis: (
            latest_axis_line[axis]["bbox"][0],
            latest_axis_line[axis]["normalized_text"].find(needles[axis]),
        ),
    )
    events = [support._line_ref(latest_axis_line[axis], f"CURRENCY_AXIS_{axis}") for axis in axes]
    events.extend(support._line_ref(line, "UNIT_AXIS") for line in unit_lines)
    return axes, events, unit_count


def _table_features(page: Mapping[str, Any]) -> dict[str, Any]:
    support = _support()
    roles, role_events = _joined_roles(page)
    axes, header_events, unit_count = _header_features(page)
    observed = set(roles)
    numeric_count = sum(
        support._NUMBER.fullmatch(line["normalized_text"]) is not None for line in page["lines"]
    )
    asset_count = len(observed & _ASSET_ROLES)
    liability_count = len(observed & _LIABILITY_ROLES)
    negative_families = list(
        dict.fromkeys(
            family
            for line in page["lines"]
            if (family := _negative_family(line["normalized_text"])) is not None
        )
    )
    complete = (
        "USD" in axes
        and "TOTAL" in axes
        and len(axes) >= 4
        and unit_count >= 1
        and asset_count >= 5
        and "ASSET_TOTAL" in observed
        and liability_count >= 3
        and "LIABILITY_TOTAL" in observed
        and "STATE_INTERNAL" in observed
        and numeric_count >= 20
        and not negative_families
    )
    return {
        "asset_role_count": asset_count,
        "complete": complete,
        "currency_axes": axes,
        "events": [*header_events, *role_events],
        "liability_role_count": liability_count,
        "negative_families": negative_families,
        "numeric_token_count": numeric_count,
        "observed_source_roles": roles,
        "state_roles": [role for role in roles if role in _STATE_ROLES],
        "unit_axis_count": unit_count,
    }


def _owner_for_table(
    pages: Sequence[Mapping[str, Any]], index: int
) -> tuple[Mapping[str, Any], Mapping[str, Any]] | None:
    possible = [pages[index]]
    if index:
        possible.append(pages[index - 1])
    candidates = [
        (page, line)
        for page in possible
        for line in page["lines"]
        if _owner(line["normalized_text"])
    ]
    return max(candidates, key=lambda item: item[1]["global_ordinal"], default=None)


def _region(
    members: Sequence[
        tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], dict[str, Any]]
    ],
) -> dict[str, Any]:
    support = _support()
    first_page, first_owner_page, first_owner, _ = members[0]
    last_page = members[-1][0]
    axes = list(
        dict.fromkeys(axis for *_, features in members for axis in features["currency_axes"])
    )
    roles = list(
        dict.fromkeys(
            role for *_, features in members for role in features["observed_source_roles"]
        )
    )
    state_roles = list(dict.fromkeys(role for role in roles if role in _STATE_ROLES))
    anchors = [
        "FAMILY_OWNER",
        *[f"CURRENCY_AXIS_{axis}" for axis in axes],
        *roles,
    ]
    events = [support._line_ref(first_owner, "FAMILY_OWNER")]
    events.extend(event for *_, features in members for event in features["events"])
    return {
        "anchor_roles": anchors,
        "complete": True,
        "end_global_ordinal": last_page["lines"][-1]["global_ordinal"],
        "events": events,
        "layout": {
            "asset_role_count": len(set(roles) & _ASSET_ROLES),
            "currency_axes_observed": axes,
            "liability_role_count": len(set(roles) & _LIABILITY_ROLES),
            "observed_source_roles": roles,
            "optional_currency_axes_allowed": True,
            "period_table_count": len(members),
            "row_and_axis_order_is_semantic": False,
            "state_roles_observed": state_roles,
            "table_continues_from_previous_page": first_owner_page is not first_page,
        },
        "numeric_token_count": sum(member[3]["numeric_token_count"] for member in members),
        "owner": support._line_ref(first_owner, "FAMILY_OWNER"),
        "page_span": [first_owner_page["page_sequence"], last_page["page_sequence"]],
        "pair_anchor_combinations": [list(pair) for pair in itertools.combinations(anchors, 2)],
        "start_global_ordinal": first_owner_page["lines"][0]["global_ordinal"],
        "table_page_sequences": [member[0]["page_sequence"] for member in members],
    }


def _candidates(
    pages: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    table_candidates: list[
        tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], dict[str, Any]]
    ] = []
    near: list[dict[str, Any]] = []
    for index, page in enumerate(pages):
        features = _table_features(page)
        owner = _owner_for_table(pages, index)
        if not features["complete"]:
            if owner is not None or len(features["currency_axes"]) >= 3:
                near.append(
                    {
                        "currency_axes_observed": features["currency_axes"],
                        "negative_families": features["negative_families"],
                        "page_span": [page["page_sequence"], page["page_sequence"]],
                        "reason": (
                            "CURRENCY_RISK_OWNER_WITHOUT_COMPLETE_TABLE"
                            if owner is not None
                            else "CURRENCY_LIKE_AXES_WITHOUT_BOUND_FAMILY_OWNER_OR_CORE"
                        ),
                    }
                )
            continue
        if owner is None:
            near.append(
                {
                    "currency_axes_observed": features["currency_axes"],
                    "negative_families": features["negative_families"],
                    "page_span": [page["page_sequence"], page["page_sequence"]],
                    "reason": "COMPLETE_CURRENCY_LIKE_TABLE_WITHOUT_BOUND_FAMILY_OWNER",
                }
            )
            continue
        table_candidates.append((page, owner[0], owner[1], features))

    regions: list[dict[str, Any]] = []
    cursor = 0
    while cursor < len(table_candidates):
        members = [table_candidates[cursor]]
        cursor += 1
        while (
            cursor < len(table_candidates)
            and table_candidates[cursor][0]["page_sequence"] == members[-1][0]["page_sequence"] + 1
        ):
            members.append(table_candidates[cursor])
            cursor += 1
        regions.append(_region(members))
    return regions, near


def _metrics(
    regions: Sequence[Mapping[str, Any]], near: Sequence[Mapping[str, Any]]
) -> dict[str, int]:
    return {
        "complete_region_count": len(regions),
        "complete_table_page_count": sum(len(region["table_page_sequences"]) for region in regions),
        "near_region_count": len(near),
        "page_count_with_complete_region": len(
            {page for region in regions for page in region["table_page_sequences"]}
        ),
    }


def _validate(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("currency-risk graph fields drifted")
    regions = value["regions"]
    near = value["near_regions"]
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["status"] != "CURRENCY_RISK_GRAPH_ENUMERATION_COMPLETE"
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(regions) is not list
        or type(near) is not list
        or not same_typed_json_v1(value["metrics"], _metrics(regions, near))
    ):
        raise _error("currency-risk graph identity drifted")
    expected_uniqueness = {
        "complete_region_count": len(regions),
        "status": "UNIQUE_FULL_MATCH" if len(regions) == 1 else "NOT_UNIQUE_FULL_MATCH",
    }
    if not same_typed_json_v1(value["uniqueness"], expected_uniqueness):
        raise _error("currency-risk uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "crvgv1:graph:" + canonical_json_sha256_v1(material):
        raise _error("currency-risk graph ID drifted")
    return canonical_clone_v1(value)


def build_currency_risk_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
    checked = _support()._pages(pages)
    regions, near = _candidates(checked)
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "metrics": _metrics(regions, near),
        "near_regions": near,
        "regions": regions,
        "safety": canonical_clone_v1(_SAFETY),
        "status": "CURRENCY_RISK_GRAPH_ENUMERATION_COMPLETE",
        "uniqueness": {
            "complete_region_count": len(regions),
            "status": "UNIQUE_FULL_MATCH" if len(regions) == 1 else "NOT_UNIQUE_FULL_MATCH",
        },
    }
    return _validate(
        {**material, "result_id": "crvgv1:graph:" + canonical_json_sha256_v1(material)}
    )


def validate_currency_risk_variant_graph_document_v1(value: Any) -> dict[str, Any]:
    return _validate(value)
