"""Bank-blind complete-PDF variant graph for interest-rate-risk tables."""

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

FORMAT_VERSION = "INTEREST_RATE_RISK_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "INTEREST_RATE_RISK"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_OR_GEOMETRY_SELECTED_ROTATED_VIETOCR_"
    "PAIR_FIRST_INTEREST_RATE_RISK_OWNER_OPTIONAL_REPRICING_AXES_ASSET_"
    "LIABILITY_GAP_TOPOLOGY_UNIT_AND_NUMERIC_STRUCTURE_ONLY_NO_NUMERIC_"
    "SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_or_routing": False,
    "child_row_order_required_for_matching": False,
    "complete_pdf_region_enumeration_required": True,
    "fresh_vietocr_transformer_text_required": True,
    "interest_rate_axis_order_required_for_matching": False,
    "liquidity_currency_or_fair_value_table_can_accept": False,
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


class InterestRateRiskVariantGraphV1Error(ValueError):
    """The complete-PDF input or interest-rate-risk graph drifted."""


def _error(message: str) -> InterestRateRiskVariantGraphV1Error:
    return InterestRateRiskVariantGraphV1Error(message)


def _support() -> ModuleType:
    name = "interest_income_graph_support_for_interest_rate_risk"
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
    return len(value.split()) <= 18 and (
        "rui ro lai suat" in value or "bang rui ro lai suat" in value
    )


def _negative_family(text: str) -> str | None:
    value = _strip(text)
    if "rui ro tien te" in value or "rui ro ty gia" in value:
        return "CURRENCY_RISK"
    if "rui ro thanh khoan" in value or "thoi gian dao han" in value:
        return "LIQUIDITY_RISK"
    if "gia tri hop ly" in value:
        return "FINANCIAL_INSTRUMENTS"
    return None


def _unit(text: str) -> bool:
    value = _strip(text)
    return "trieu dong" in value or "trieu vnd" in value


def _raw_role(text: str) -> str | None:
    value = _strip(text)
    if "chenh" in value and "nhay cam" in value and "noi ngoai bang" in value:
        return "STATE_COMBINED"
    if "chenh" in value and "nhay cam" in value and "ngoai bang" in value:
        return "STATE_EXTERNAL"
    if "chenh" in value and "nhay cam" in value and "noi bang" in value:
        return "STATE_INTERNAL"
    if "muc chenh lech rong" in value:
        return "STATE_INTERNAL"
    if "cam ket ngoai bang" in value and "nhay cam" in value:
        return "STATE_EXTERNAL"
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
    if "gui tai nhnn" in value or "gui tai ngan hang nha nuoc" in value:
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
    if "gui cua khach hang" in value:
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
        "gui" in value and ("vay" in value or "cho vay" in value or "cap tin dung" in value)
    ) or "cac khoan no chinh phu" in value:
        return "INTERBANK_ROW"
    return None


def _joined_roles(page: Mapping[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    support = _support()
    roles: list[str] = []
    events: list[dict[str, Any]] = []
    after_asset_total = False
    lines = page["lines"]
    label_zone_limit = max(line["bbox"][2] for line in lines) * 0.46
    label_lines = [
        line
        for line in lines
        if line["bbox"][0] <= label_zone_limit
        and support._NUMBER.fullmatch(line["normalized_text"]) is None
    ]
    for index, line in enumerate(label_lines):
        candidates = [line["normalized_text"]]
        for following in label_lines[index + 1 : index + 3]:
            if following["bbox"][1] - line["bbox"][3] > 100:
                break
            candidates.append(f"{candidates[-1]} {following['normalized_text']}")
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


def _axis_role(value: str) -> str | None:
    value = _strip(value)
    if "khong chiu l" in value or "khong bi dinh gia lai" in value:
        return "NO_INTEREST"
    if re.search(r"\btren\s+0?3\s+thang\b", value):
        return "OVERDUE_GT3M"
    if re.search(r"\bden\s+0?3\s+thang\b", value) and not value.startswith("tu"):
        return "OVERDUE_LE3M"
    if "qua han" in value:
        return "OVERDUE"
    if re.search(r"\b(?:den|duoi)\s+0?1(?:\s+thang)?\b", value) or re.search(
        r"\btrong vong\s+0?1\s+thang\b", value
    ):
        return "WITHIN_LE1M"
    if re.search(r"\btu\s+0?1\s*(?:den\s*)?0?5\s+nam\b", value):
        return "WITHIN_1_5Y"
    if re.search(r"\btu\s+t?den\s+0?3(?:\s+thang)?\b", value):
        # A recurrent Transformer character merge can turn ``1 đến`` into
        # ``Tđến``.  This only produces an anchor candidate; the enclosing
        # column topology, unit, parent rows, totals and equations still gate
        # any mapping authority.
        return "WITHIN_1_3M"
    if re.search(r"\btu\s+0?1\s*(?:den\s*)?0?3(?:\s+thang)?\b", value):
        return "WITHIN_1_3M"
    if re.search(r"\btu\s+0?3\s*(?:-|den|\?)?\s*0?6", value):
        return "WITHIN_3_6M"
    if re.search(r"\btu\s+0?6\s*(?:-|den)?\s*12", value):
        return "WITHIN_6_12M"
    if re.search(r"\btren\s+0?5\s+nam\b", value):
        return "WITHIN_GT5Y"
    if re.search(r"\btren\s+0?1\s+nam\b", value):
        return "WITHIN_GT1Y"
    if value in {"tong", "tong cong"}:
        return "TOTAL"
    return None


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
    header = page["lines"][:cutoff]
    candidates: list[tuple[str, Mapping[str, Any]]] = []
    for index, line in enumerate(header):
        phrases = [line["normalized_text"]]
        center = (line["bbox"][0] + line["bbox"][2]) / 2
        for following in header[index + 1 :]:
            following_center = (following["bbox"][0] + following["bbox"][2]) / 2
            if following["bbox"][1] - line["bbox"][3] > 105:
                break
            overlap = min(line["bbox"][2], following["bbox"][2]) - max(
                line["bbox"][0], following["bbox"][0]
            )
            minimum_width = min(
                line["bbox"][2] - line["bbox"][0],
                following["bbox"][2] - following["bbox"][0],
            )
            if abs(center - following_center) <= 55 or overlap >= minimum_width * 0.25:
                phrases.append(f"{phrases[-1]} {following['normalized_text']}")
        role = _axis_role(phrases[0])
        if role is None:
            role = next(
                (found for phrase in reversed(phrases[1:]) if (found := _axis_role(phrase))),
                None,
            )
        if role is not None:
            candidates.append((role, line))
    observed = {role for role, _line in candidates}
    if {"OVERDUE_GT3M", "OVERDUE_LE3M"} & observed:
        candidates = [(role, line) for role, line in candidates if role != "OVERDUE"]
    latest: dict[str, Mapping[str, Any]] = {}
    for role, line in candidates:
        latest[role] = line
    axes = sorted(
        latest,
        key=lambda role: (latest[role]["bbox"][0] + latest[role]["bbox"][2]) / 2,
    )
    unit_lines = [line for line in header if _unit(line["normalized_text"])]
    events = [support._line_ref(latest[role], f"REPRICING_AXIS_{role}") for role in axes]
    events.extend(support._line_ref(line, "UNIT_AXIS") for line in unit_lines)
    return axes, events, len(unit_lines)


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
    term_axes = {
        "WITHIN_1_3M",
        "WITHIN_1_5Y",
        "WITHIN_3_6M",
        "WITHIN_6_12M",
        "WITHIN_GT1Y",
        "WITHIN_GT5Y",
        "WITHIN_LE1M",
    }
    complete = (
        "NO_INTEREST" in axes
        and "TOTAL" in axes
        and len(set(axes) & term_axes) >= 3
        and len(axes) >= 7
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
        "events": [*header_events, *role_events],
        "liability_role_count": liability_count,
        "negative_families": negative_families,
        "numeric_token_count": numeric_count,
        "observed_source_roles": roles,
        "repricing_axes": axes,
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
        dict.fromkeys(axis for *_, features in members for axis in features["repricing_axes"])
    )
    roles = list(
        dict.fromkeys(
            role for *_, features in members for role in features["observed_source_roles"]
        )
    )
    anchors = ["FAMILY_OWNER", *[f"REPRICING_AXIS_{axis}" for axis in axes], *roles]
    events = [support._line_ref(first_owner, "FAMILY_OWNER")]
    events.extend(event for *_, features in members for event in features["events"])
    return {
        "anchor_roles": anchors,
        "complete": True,
        "end_global_ordinal": last_page["lines"][-1]["global_ordinal"],
        "events": events,
        "layout": {
            "asset_role_count": len(set(roles) & _ASSET_ROLES),
            "liability_role_count": len(set(roles) & _LIABILITY_ROLES),
            "observed_source_roles": roles,
            "optional_repricing_axes_allowed": True,
            "period_table_count": len(members),
            "repricing_axes_observed": axes,
            "row_and_axis_order_is_semantic": False,
            "state_roles_observed": [role for role in roles if role in _STATE_ROLES],
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
    tables: list[
        tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], dict[str, Any]]
    ] = []
    near: list[dict[str, Any]] = []
    for index, page in enumerate(pages):
        features = _table_features(page)
        owner = _owner_for_table(pages, index)
        if not features["complete"]:
            if owner is not None or len(features["repricing_axes"]) >= 3:
                near.append(
                    {
                        "negative_families": features["negative_families"],
                        "page_span": [page["page_sequence"], page["page_sequence"]],
                        "reason": (
                            "INTEREST_RATE_RISK_OWNER_WITHOUT_COMPLETE_TABLE"
                            if owner is not None
                            else "REPRICING_LIKE_AXES_WITHOUT_BOUND_FAMILY_OWNER_OR_CORE"
                        ),
                        "repricing_axes_observed": features["repricing_axes"],
                    }
                )
            continue
        if owner is None:
            near.append(
                {
                    "negative_families": features["negative_families"],
                    "page_span": [page["page_sequence"], page["page_sequence"]],
                    "reason": "COMPLETE_REPRICING_LIKE_TABLE_WITHOUT_BOUND_FAMILY_OWNER",
                    "repricing_axes_observed": features["repricing_axes"],
                }
            )
            continue
        tables.append((page, owner[0], owner[1], features))
    regions: list[dict[str, Any]] = []
    cursor = 0
    while cursor < len(tables):
        members = [tables[cursor]]
        cursor += 1
        while (
            cursor < len(tables)
            and tables[cursor][0]["page_sequence"] == members[-1][0]["page_sequence"] + 1
        ):
            members.append(tables[cursor])
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
        raise _error("interest-rate-risk graph fields drifted")
    regions = value["regions"]
    near = value["near_regions"]
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["status"] != "INTEREST_RATE_RISK_GRAPH_ENUMERATION_COMPLETE"
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(regions) is not list
        or type(near) is not list
        or not same_typed_json_v1(value["metrics"], _metrics(regions, near))
    ):
        raise _error("interest-rate-risk graph identity drifted")
    expected_uniqueness = {
        "complete_region_count": len(regions),
        "status": "UNIQUE_FULL_MATCH" if len(regions) == 1 else "NOT_UNIQUE_FULL_MATCH",
    }
    if not same_typed_json_v1(value["uniqueness"], expected_uniqueness):
        raise _error("interest-rate-risk uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "irrvgv1:graph:" + canonical_json_sha256_v1(material):
        raise _error("interest-rate-risk graph ID drifted")
    return canonical_clone_v1(value)


def build_interest_rate_risk_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
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
        "status": "INTEREST_RATE_RISK_GRAPH_ENUMERATION_COMPLETE",
        "uniqueness": {
            "complete_region_count": len(regions),
            "status": "UNIQUE_FULL_MATCH" if len(regions) == 1 else "NOT_UNIQUE_FULL_MATCH",
        },
    }
    return _validate(
        {**material, "result_id": "irrvgv1:graph:" + canonical_json_sha256_v1(material)}
    )


def validate_interest_rate_risk_variant_graph_document_v1(value: Any) -> dict[str, Any]:
    return _validate(value)
