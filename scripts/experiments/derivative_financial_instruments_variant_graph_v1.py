"""Bank-blind graph for derivative financial instruments.

The matcher scans every physical page, locates the first/last boundary of a
derivative-note cluster and only then interprets its row/column layout.  The
same core admits contract-value, asset/liability, inflow/outflow and net-value
axes, stacked current/comparative blocks, optional group parents and optional
forward/swap/future/interest-rate children.  Bank, filename, page and note
number never participate in matching.

Fresh VietOCR Transformer text proposes anchors.  Geometry, period headings,
units, row order and numeric-lane topology are retained for later independent
pixel/accounting/schema verification.  This module grants no such authority.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    match_vietnamese_anchor_alias_v1,
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "DerivativeFinancialInstrumentsVariantGraphV1Error",
    "build_derivative_financial_instruments_variant_graph_document_v1",
    "validate_derivative_financial_instruments_variant_graph_replay_v1",
]


FORMAT_VERSION = "DERIVATIVE_FINANCIAL_INSTRUMENTS_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "DERIVATIVE_FINANCIAL_INSTRUMENTS"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_DERIVATIVE_OWNER_FIRST_LAST_"
    "BOUNDARY_STACKED_PERIOD_HORIZONTAL_VERTICAL_HYBRID_MEANINGFUL_LANE_"
    "PARENT_CHILD_ORDER_GEOMETRY_STRUCTURE_PROPOSAL_ONLY_NO_NUMERIC_SCHEMA_"
    "MAPPING_OR_EXPORT_AUTHORITY"
)
_NUMBER = re.compile(r"^\(?-?[0-9]+(?:[.,][0-9]+)*\)?$")
_DASH = re.compile(r"^[\-–—]+$")
_SAFETY = {
    "bank_filename_note_or_page_used_for_inference": False,
    "complete_pdf_region_enumeration_required": True,
    "fresh_vietocr_transformer_text_required": True,
    "layout_variants_are_family_level_not_bank_routed": True,
    "mapping_authority": False,
    "meaningless_or_unsupported_columns_mapped": False,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "pair_combinations_exhausted_before_triples": True,
    "parent_precedes_descendant_region_required": True,
    "persisted_result_self_authenticating": False,
    "policy_fair_value_cashflow_or_risk_surface_can_match": False,
    "public_exact_replay_required": True,
    "schema_authority": False,
    "text_similarity_alone_can_accept": False,
    "whole_pdf_uniqueness_required": True,
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


class DerivativeFinancialInstrumentsVariantGraphV1Error(ValueError):
    """The derivative family input or exact replay drifted."""


def _error(message: str) -> DerivativeFinancialInstrumentsVariantGraphV1Error:
    return DerivativeFinancialInstrumentsVariantGraphV1Error(message)


_OWNER_ALIASES = [
    "Các công cụ tài chính phái sinh và các tài sản tài chính khác",
    "Các công cụ tài chính phái sinh và các tài sản công nợ tài chính khác",
    "Các công cụ tài chính phái sinh và các khoản tài sản công nợ tài chính khác",
    "Các công cụ tài chính phái sinh và công nợ tài chính khác",
    "Công cụ tài chính phái sinh và các khoản nợ phải trả tài chính khác",
    "Các công cụ tài chính phái sinh và các khoản nợ tài chính khác",
]
_ROLE_ALIASES = {
    "CURRENCY_DERIVATIVE_PARENT": [
        "Công cụ tài chính phái sinh tiền tệ",
        "Công cụ TC phái sinh tiền tệ",
    ],
    "FORWARD_CURRENCY": ["Giao dịch kỳ hạn tiền tệ"],
    "CURRENCY_SWAP": ["Giao dịch hoán đổi tiền tệ"],
    "CURRENCY_FUTURE": ["Giao dịch tương lai tiền tệ"],
    "OTHER_DERIVATIVE_PARENT": [
        "Công cụ tài chính phái sinh khác",
        "Công cụ tài chính phái sinh lãi suất",
    ],
    "INTEREST_RATE_SWAP": [
        "Giao dịch hoán đổi lãi suất",
        "Giao dịch hoán đổi lãi suất tiền tệ chéo",
    ],
}
_CHILD_ROLES = {
    "FORWARD_CURRENCY",
    "CURRENCY_SWAP",
    "CURRENCY_FUTURE",
    "INTEREST_RATE_SWAP",
}
_NEXT_FAMILY_ALIASES = [
    "Cho vay khách hàng",
    "Vốn tài trợ ủy thác đầu tư",
    "Tiền gửi của khách hàng",
    "Phát hành giấy tờ có giá",
    "Chứng khoán đầu tư",
]


def _bbox(value: Any) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or value[0] < 0
        or value[1] < 0
        or value[2] <= value[0]
        or value[3] <= value[1]
    ):
        raise _error("line bbox must be four exact positive-bound integers")
    return list(value)


def _pages(value: Any) -> list[dict[str, Any]]:
    if type(value) is not list or not value:
        raise _error("derivative matcher requires one complete nonempty PDF")
    pages: list[dict[str, Any]] = []
    previous_page = 0
    for raw_page in value:
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_sequence",
            "primary_numeric_authority",
        }:
            raise _error("derivative matcher page fields drifted")
        sequence = raw_page["page_sequence"]
        if type(sequence) is not int or sequence != previous_page + 1:
            raise _error("complete PDF page sequence must be gap-free")
        if type(raw_page["primary_numeric_authority"]) is not bool:
            raise _error("primary numeric authority flag must be exact bool")
        if type(raw_page["lines"]) is not list:
            raise _error("page lines must be one list")
        lines = []
        previous_index = -1
        for raw_line in raw_page["lines"]:
            if type(raw_line) is not dict or set(raw_line) != {
                "bbox",
                "source_line_index",
                "source_text",
                "vietocr_text",
            }:
                raise _error("derivative matcher line fields drifted")
            index = raw_line["source_line_index"]
            if type(index) is not int or index != previous_index + 1:
                raise _error("source line indices must be exact, gap-free and increasing")
            source_text = raw_line["source_text"]
            if source_text is not None and type(source_text) is not str:
                raise _error("source text must be null or one exact string")
            text = raw_line["vietocr_text"]
            if type(text) is not str:
                raise _error("fresh VietOCR text must be one exact string")
            lines.append(
                {
                    "bbox": _bbox(raw_line["bbox"]),
                    "normalized_text": normalize_vietnamese_anchor_v1(text),
                    "source_line_index": index,
                    "source_text": source_text,
                    "vietocr_text": text,
                }
            )
            previous_index = index
        pages.append(
            {
                "lines": lines,
                "page_sequence": sequence,
                "primary_numeric_authority": raw_page["primary_numeric_authority"],
            }
        )
        previous_page = sequence
    return pages


def _token(line: Mapping[str, Any]) -> str:
    return line["vietocr_text"].strip().replace(" ", "")


def _is_money(line: Mapping[str, Any]) -> bool:
    token = _token(line)
    if _NUMBER.fullmatch(token) is not None or _DASH.fullmatch(token) is not None:
        return True
    # VietOCR is only the semantic/geometry locator in this pass.  Keep a crop
    # that is overwhelmingly numeric even when one or two glyphs were decoded
    # as a common digit-looking Latin letter (for example ``6,270,0ss``).  The
    # token is never corrected here and cannot become numeric authority; the
    # later pixel/source-number verifier must read the bound crop independently.
    body = token.strip("()")
    digits = sum(char.isdigit() for char in body)
    letters = [char.lower() for char in body if char.isalpha()]
    return (
        digits >= 4
        and 1 <= len(letters) <= 2
        and all(char in {"b", "i", "l", "o", "s", "z"} for char in letters)
        and all(char.isdigit() or char in ".,-" or char.isalpha() for char in body)
        and digits / (digits + len(letters)) >= 0.70
    )


def _page_width(lines: Sequence[Mapping[str, Any]]) -> int:
    return max((line["bbox"][2] for line in lines), default=1)


def _row_values(
    lines: Sequence[Mapping[str, Any]], label: Mapping[str, Any]
) -> list[dict[str, Any]]:
    center = (label["bbox"][1] + label["bbox"][3]) / 2
    tolerance = max(14.0, (label["bbox"][3] - label["bbox"][1]) * 0.58)
    width = _page_width(lines)
    values = [
        line
        for line in lines
        if line["bbox"][0] > width * 0.40
        and line["bbox"][0] < width * 0.97
        and abs((line["bbox"][1] + line["bbox"][3]) / 2 - center) <= tolerance
        and _is_money(line)
    ]
    return [
        {
            "bbox": list(line["bbox"]),
            "source_line_index": line["source_line_index"],
            "source_text": line["source_text"],
            "vietocr_text": line["vietocr_text"],
        }
        for line in sorted(values, key=lambda item: (item["bbox"][0], item["source_line_index"]))
    ]


def _role(line: Mapping[str, Any]) -> str | None:
    # Numbering and bullet prefixes are presentation structure, not bank- or
    # note-specific aliases.  Removing only the leading marker lets the same
    # family vocabulary match ``2 - Công cụ ... lãi suất`` and ordinary rows.
    surface = re.sub(
        r"^\s*(?:(?:\(?\d{1,3}\)?\s*[-.)–—:]?\s*)|(?:[-–—•]+\s*))",
        "",
        line["vietocr_text"],
    )
    matches = [
        role
        for role, aliases in _ROLE_ALIASES.items()
        if match_vietnamese_anchor_alias_v1(surface, aliases)
    ]
    if not matches:
        return None
    # The more specific interest-rate child must outrank its parent surface.
    if "INTEREST_RATE_SWAP" in matches:
        return "INTEREST_RATE_SWAP"
    if len(matches) != 1:
        raise _error("one derivative label ambiguously matches multiple roles")
    return matches[0]


def _is_owner(line: Mapping[str, Any]) -> bool:
    if match_vietnamese_anchor_alias_v1(line["vietocr_text"], _OWNER_ALIASES):
        return True
    text = line["normalized_text"]
    return (
        "cong cu tai chinh phai sinh" in text
        and any(token in text for token in ("tai san", "cong no", "khoan no"))
        and len(text.split()) <= 22
    )


def _period_key(text: str) -> tuple[int, int, int] | None:
    matched = re.search(r"([0-3]?[0-9])[ /.-]([01]?[0-9])[ /.-](20[0-9]{2})", text)
    if matched is None:
        matched = re.search(
            r"([0-3]?[0-9]) thang ([01]?[0-9])(?: nam)? (20[0-9]{2})",
            text,
        )
    if matched is not None:
        day, month, year = (int(item) for item in matched.groups())
        if 1 <= day <= 31 and 1 <= month <= 12:
            return year, month, day
    if "tai ngay" in text and (year_match := re.search(r"20[0-9]{2}", text)) is not None:
        return int(year_match.group()), 0, 0
    return None


def _period_headings(
    lines: Sequence[Mapping[str, Any]], *, start: int, stop: int
) -> list[dict[str, Any]]:
    candidates: list[tuple[Mapping[str, Any], tuple[int, int, int]]] = []
    for line in lines:
        if not start < line["source_line_index"] < stop:
            continue
        normalized = line["normalized_text"]
        if "tai ngay" not in normalized and len(normalized.split()) > 4:
            continue
        key = _period_key(normalized)
        if key is not None:
            candidates.append((line, key))
    ordered_keys = sorted({key for _, key in candidates}, reverse=True)
    roles = {}
    if ordered_keys:
        roles[ordered_keys[0]] = "CURRENT_PERIOD"
    if len(ordered_keys) >= 2:
        roles[ordered_keys[1]] = "COMPARATIVE_PERIOD"
    headings = []
    seen: set[str] = set()
    for line, key in candidates:
        role = roles.get(key)
        if role is None or role in seen:
            continue
        seen.add(role)
        headings.append(
            {
                "bbox": list(line["bbox"]),
                "period_role": role,
                "source_line_index": line["source_line_index"],
                "vietocr_text": line["vietocr_text"],
            }
        )
    return sorted(headings, key=lambda item: item["source_line_index"])


def _unit_evidence(
    lines: Sequence[Mapping[str, Any]], *, start: int, stop: int
) -> list[dict[str, Any]]:
    return [
        {
            "bbox": list(line["bbox"]),
            "source_line_index": line["source_line_index"],
            "vietocr_text": line["vietocr_text"],
        }
        for line in lines
        if start < line["source_line_index"] < stop
        and ("trieu dong" in line["normalized_text"] or "trieu vnd" in line["normalized_text"])
    ]


def _lane_headers(
    lines: Sequence[Mapping[str, Any]], *, start: int, first_period_row: int
) -> dict[str, Any]:
    surfaces = [line for line in lines if start < line["source_line_index"] < first_period_row]
    normalized = " ".join(line["normalized_text"] for line in surfaces)
    has_contract = any("hop dong" in line["normalized_text"] for line in surfaces)
    has_asset = "tai san" in normalized
    has_liability = "cong no" in normalized
    has_inflow = "dong tien vao" in normalized
    has_outflow = "dong tien ra" in normalized
    has_book_value = "ghi so" in normalized or "so ke toan" in normalized
    has_net_column = any(
        ("gia tri thuan" in line["normalized_text"] or "gia tri rong" in line["normalized_text"])
        and len(line["normalized_text"].split()) <= 4
        for line in surfaces
    )
    roles: list[str]
    if has_inflow and has_outflow:
        roles = ["CONTRACT_VALUE", "INFLOW", "OUTFLOW", "NET_VALUE"]
        mode = "CONTRACT_INFLOW_OUTFLOW_NET"
    elif has_asset and has_liability:
        if has_net_column:
            roles = ["ASSET_CARRYING_VALUE", "LIABILITY_CARRYING_VALUE", "NET_VALUE"]
            mode = "ASSET_LIABILITY_NET"
        elif has_contract:
            roles = [
                "CONTRACT_VALUE",
                "ASSET_CARRYING_VALUE",
                "LIABILITY_CARRYING_VALUE",
            ]
            mode = "CONTRACT_ASSET_LIABILITY"
        else:
            roles = ["ASSET_CARRYING_VALUE", "LIABILITY_CARRYING_VALUE"]
            mode = "ASSET_LIABILITY"
    elif has_contract and (has_book_value or has_net_column):
        roles = ["CONTRACT_VALUE", "NET_VALUE"]
        mode = "CONTRACT_NET"
    else:
        roles = []
        mode = "UNRESOLVED"
    header_lines = [
        {
            "bbox": list(line["bbox"]),
            "source_line_index": line["source_line_index"],
            "vietocr_text": line["vietocr_text"],
        }
        for line in surfaces
        if any(
            token in line["normalized_text"]
            for token in (
                "hop dong",
                "tai san",
                "cong no",
                "dong tien vao",
                "dong tien ra",
                "gia tri thuan",
                "gia tri rong",
                "ghi so",
            )
        )
    ]
    centers: dict[str, float] = {}
    for line in surfaces:
        text = line["normalized_text"]
        center = (line["bbox"][0] + line["bbox"][2]) / 2
        if "dong tien vao" in text:
            centers["INFLOW"] = center
        elif "dong tien ra" in text:
            centers["OUTFLOW"] = center
        elif text in {"tai san", "tai san trieu dong"}:
            centers["ASSET_CARRYING_VALUE"] = center
        elif "cong no" in text and len(text.split()) <= 4:
            centers["LIABILITY_CARRYING_VALUE"] = center
        elif "gia tri thuan" in text or "gia tri rong" in text:
            centers["NET_VALUE"] = center
        elif "hop dong" in text:
            centers.setdefault("CONTRACT_VALUE", center)
        elif mode == "CONTRACT_NET" and ("ghi so" in text or "so ke toan" in text):
            centers.setdefault("NET_VALUE", center)
    return {
        "header_lane_centers": {role: centers[role] for role in roles if role in centers},
        "header_lines": header_lines,
        "lane_roles_left_to_right": roles,
        "presentation_mode": mode,
    }


def _lane_centers(events: Sequence[Mapping[str, Any]], *, expected_count: int) -> list[float]:
    centers = sorted(
        (item["bbox"][0] + item["bbox"][2]) / 2
        for event in events
        for item in event["value_proposals"]
    )
    if not centers:
        return []
    groups: list[list[float]] = []
    span = max(centers) - min(centers)
    tolerance = max(40.0, span / max(8, expected_count * 3))
    for center in centers:
        for group in groups:
            if abs(center - sum(group) / len(group)) <= tolerance:
                group.append(center)
                break
        else:
            groups.append([center])
    result = [sum(group) / len(group) for group in groups]
    if len(result) > expected_count:
        # Merge the closest pair until the layout header and numeric lanes agree.
        while len(result) > expected_count:
            gap_index = min(
                range(len(result) - 1), key=lambda index: result[index + 1] - result[index]
            )
            result[gap_index : gap_index + 2] = [(result[gap_index] + result[gap_index + 1]) / 2]
    return result


def _assign_lanes(
    events: list[dict[str, Any]],
    lane_roles: Sequence[str],
    header_centers: Mapping[str, float],
) -> list[float]:
    if all(role in header_centers for role in lane_roles):
        centers = [header_centers[role] for role in lane_roles]
    else:
        centers = _lane_centers(events, expected_count=len(lane_roles))
    if len(centers) != len(lane_roles) or centers != sorted(centers):
        return []
    for event in events:
        for item in event["value_proposals"]:
            center = (item["bbox"][0] + item["bbox"][2]) / 2
            ordinal = min(range(len(centers)), key=lambda index: abs(center - centers[index]))
            item["lane_role"] = lane_roles[ordinal]
    return centers


def _minimal_anchor(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    roles = [f"CHILD:{event['role']}" for event in events if event["role"] in _CHILD_ROLES]
    pairs = list(itertools.combinations(["PARENT:DERIVATIVE_OWNER", *roles], 2))
    if not pairs:
        raise _error("complete derivative graph has no anchor pair")
    return {
        "combination_size": 2,
        "pair_search_order": "ALL_PARENT_CHILD_PAIRS_THEN_ALL_CHILD_CHILD_PAIRS",
        "selected_roles": list(pairs[0]),
        "tested_pair_count": len(pairs),
        "unique_within_complete_context_regions": True,
    }


def _candidate(
    page: Mapping[str, Any], owner: Mapping[str, Any]
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    lines = page["lines"]
    owner_index = owner["source_line_index"]
    later_boundaries = [
        line["source_line_index"]
        for line in lines
        if line["source_line_index"] > owner_index
        and any(
            match_vietnamese_anchor_alias_v1(line["vietocr_text"], [alias])
            for alias in _NEXT_FAMILY_ALIASES
        )
    ]
    stop = min(later_boundaries, default=len(lines))
    role_lines = [
        (line, role)
        for line in lines
        if owner_index < line["source_line_index"] < stop and (role := _role(line)) is not None
    ]
    # A complete table needs at least two distinct transaction children.  This
    # excludes policy prose and balance-sheet/fair-value repetitions.
    child_roles = {role for _, role in role_lines if role in _CHILD_ROLES}
    period_headings = _period_headings(lines, start=owner_index, stop=stop)
    events = [
        {
            "bbox": list(line["bbox"]),
            "role": role,
            "role_kind": "TRANSACTION_CHILD" if role in _CHILD_ROLES else "GROUP_PARENT",
            "source_line_index": line["source_line_index"],
            "value_proposals": _row_values(lines, line),
            "vietocr_text": line["vietocr_text"],
        }
        for line, role in role_lines
    ]
    reasons = []
    if len(child_roles) < 2:
        reasons.append("FEWER_THAN_TWO_DISTINCT_DERIVATIVE_TRANSACTION_CHILDREN")
    if len(period_headings) < 2:
        reasons.append("CURRENT_AND_COMPARATIVE_PERIOD_BLOCKS_NOT_BOTH_VISIBLE")
    if sum(bool(event["value_proposals"]) for event in events) < 2:
        reasons.append("FEWER_THAN_TWO_DERIVATIVE_ROWS_WITH_NUMERIC_GEOMETRY")
    first_derivative_row = min((event["source_line_index"] for event in events), default=stop)
    layout = _lane_headers(lines, start=owner_index, first_period_row=first_derivative_row)
    lane_roles = layout["lane_roles_left_to_right"]
    if not lane_roles:
        reasons.append("MEANINGFUL_NUMERIC_LANE_LAYOUT_NOT_RESOLVED")
        lane_centers: list[float] = []
    else:
        lane_centers = _assign_lanes(events, lane_roles, layout["header_lane_centers"])
        if len(lane_centers) != len(lane_roles):
            reasons.append("NUMERIC_LANES_DO_NOT_MATCH_VISIBLE_HEADER_LAYOUT")
    # Bind each row to the nearest preceding period heading.
    for event in events:
        preceding = [
            heading
            for heading in period_headings
            if heading["source_line_index"] < event["source_line_index"]
        ]
        event["period_role"] = preceding[-1]["period_role"] if preceding else None
    if any(event["period_role"] is None for event in events if event["value_proposals"]):
        reasons.append("NUMERIC_DERIVATIVE_ROW_PRECEDES_PERIOD_BLOCK")
    near = {
        "owner_source_line_index": owner_index,
        "page_sequence": page["page_sequence"],
        "reasons": reasons,
        "retained_roles": [event["role"] for event in events],
    }
    if reasons:
        return None, near
    boundary_end = max(
        [item["source_line_index"] for event in events for item in event["value_proposals"]]
        + [event["source_line_index"] for event in events]
    )
    material = {
        "cluster_boundary": {
            "first_item_role": "DERIVATIVE_FINANCIAL_INSTRUMENTS_OWNER",
            "first_page_sequence": page["page_sequence"],
            "first_source_line_index": owner_index,
            "last_item_role": max(events, key=lambda event: event["source_line_index"])["role"],
            "last_page_sequence": page["page_sequence"],
            "last_source_line_index": boundary_end,
            "selection_rule": (
                "OWNER_THROUGH_CURRENT_AND_COMPARATIVE_DERIVATIVE_GROUPS_CHILDREN_"
                "AND_LAST_VISIBLE_NUMERIC_ROW_BEFORE_NEXT_NOTE_FAMILY"
            ),
        },
        "events": events,
        "layout": {
            **layout,
            "lane_centers_left_to_right": lane_centers,
            "orientation": "STACKED_PERIOD_BLOCKS_BY_ROW_LABEL_AND_MEANINGFUL_COLUMNS",
            "period_headings": period_headings,
            "unit_evidence": _unit_evidence(lines, start=owner_index, stop=stop),
        },
        "minimal_anchor": _minimal_anchor(events),
        "owner": {
            "bbox": list(owner["bbox"]),
            "source_line_index": owner_index,
            "vietocr_text": owner["vietocr_text"],
        },
        "page_sequence": page["page_sequence"],
        "primary_numeric_authority": page["primary_numeric_authority"],
    }
    return {
        **material,
        "region_id": "dfigv1:region:" + canonical_json_sha256_v1(material),
    }, near


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("derivative graph result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["regions"]) is not list
        or type(value["near_regions"]) is not list
        or type(value["metrics"]) is not dict
    ):
        raise _error("derivative graph result identity or authority drifted")
    count = len(value["regions"])
    expected_status = (
        "ACCEPTED_UNIQUE_VARIANT_GRAPH"
        if count == 1
        else (
            "UNRESOLVED_NO_COMPLETE_REGION"
            if count == 0
            else "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
        )
    )
    expected_uniqueness = {
        "complete_region_count": count,
        "status": (
            "UNIQUE_FULL_MATCH"
            if count == 1
            else ("NO_FULL_MATCH" if count == 0 else "MULTIPLE_FULL_MATCHES")
        ),
    }
    expected_metrics = {
        "complete_derivative_region_count": count,
        "near_region_count": len(value["near_regions"]),
        "page_count": value["metrics"].get("page_count"),
    }
    if (
        value["status"] != expected_status
        or not same_typed_json_v1(value["uniqueness"], expected_uniqueness)
        or not same_typed_json_v1(value["metrics"], expected_metrics)
        or type(value["metrics"].get("page_count")) is not int
        or value["metrics"]["page_count"] <= 0
    ):
        raise _error("derivative graph status or metrics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "dfigv1:result:" + canonical_json_sha256_v1(material):
        raise _error("derivative graph result identity drifted")
    return canonical_clone_v1(value)


def build_derivative_financial_instruments_variant_graph_document_v1(
    pages: Any,
) -> dict[str, Any]:
    """Build one deterministic derivative graph over a complete PDF."""

    normalized_pages = _pages(pages)
    regions: list[dict[str, Any]] = []
    near_regions: list[dict[str, Any]] = []
    seen_regions: set[str] = set()
    for page in normalized_pages:
        owners = [line for line in page["lines"] if _is_owner(line)]
        for owner in owners:
            candidate, near = _candidate(page, owner)
            near_regions.append(near)
            if candidate is not None and candidate["region_id"] not in seen_regions:
                seen_regions.add(candidate["region_id"])
                regions.append(candidate)
    regions.sort(key=lambda item: (item["page_sequence"], item["owner"]["source_line_index"]))
    near_regions.sort(key=lambda item: (item["page_sequence"], item["owner_source_line_index"]))
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "metrics": {
            "complete_derivative_region_count": len(regions),
            "near_region_count": len(near_regions),
            "page_count": len(normalized_pages),
        },
        "near_regions": near_regions,
        "regions": regions,
        "safety": canonical_clone_v1(_SAFETY),
        "status": (
            "ACCEPTED_UNIQUE_VARIANT_GRAPH"
            if len(regions) == 1
            else (
                "UNRESOLVED_NO_COMPLETE_REGION"
                if not regions
                else "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
            )
        ),
        "uniqueness": {
            "complete_region_count": len(regions),
            "status": (
                "UNIQUE_FULL_MATCH"
                if len(regions) == 1
                else ("NO_FULL_MATCH" if not regions else "MULTIPLE_FULL_MATCHES")
            ),
        },
    }
    return _validate_result(
        {**material, "result_id": "dfigv1:result:" + canonical_json_sha256_v1(material)}
    )


def validate_derivative_financial_instruments_variant_graph_replay_v1(
    value: Any, pages: Any
) -> dict[str, Any]:
    """Exact-rebuild one derivative graph from the complete PDF input."""

    persisted = _validate_result(value)
    expected = build_derivative_financial_instruments_variant_graph_document_v1(pages)
    if not same_typed_json_v1(persisted, expected):
        raise _error("derivative graph does not replay exactly")
    return persisted
