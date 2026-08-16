"""Bank-blind graph for the customer-loan currency-analysis family.

The family is defined by the live TM interval 756--758: customer loans,
optionally an explicit currency-analysis branch, and the two currency children
``VND`` and ``foreign currency / gold``.  The matcher scans a complete PDF,
requires the loan owner to precede the descendant region, finds the first and
last family items, and stops at the next numbered note.  Child order is not a
matching rule.  A branch title may be absent, and horizontal, vertical and
hybrid row/column layouts are retained.

Fresh VietOCR Transformer text is only an anchor proposal.  Accentless and
bounded one-character matching may locate a region, but no number, schema row
or mapping is accepted here.  Currency pairs belonging to cash, deposits,
interbank balances or risk tables are retained as negative controls when they
have no preceding customer-loan owner.
"""

from __future__ import annotations

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
    "LoanCurrencyVariantGraphV1Error",
    "build_loan_currency_variant_graph_document_v1",
    "validate_loan_currency_variant_graph_replay_v1",
]


FORMAT_VERSION = "LOAN_CURRENCY_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "LOAN_CURRENCY_CLASSIFICATION"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_LOAN_OWNER_OPTIONAL_CURRENCY_BRANCH_"
    "UNORDERED_REQUIRED_CURRENCY_CHILDREN_FIRST_LAST_BOUNDARY_HORIZONTAL_VERTICAL_"
    "HYBRID_PERIOD_UNIT_NUMERIC_LANE_STRUCTURE_PROPOSAL_ONLY_NO_NUMERIC_SCHEMA_"
    "MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_or_page_used_for_inference": False,
    "child_order_fixed": False,
    "complete_pdf_region_enumeration_required": True,
    "fresh_vietocr_transformer_text_required": True,
    "mapping_authority": False,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "optional_branch_title_supported": True,
    "owner_must_precede_descendant_region": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "text_similarity_alone_can_accept": False,
    "whole_pdf_negative_controls_retained": True,
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
_NUMBER = re.compile(r"^\(?[+-]?[0-9]+(?:[., ][0-9]+)*%?\)?$")
_DASH = re.compile(r"^[\-–—]+$")
_MAJOR_NOTE = re.compile(r"^\s*[0-9]{1,2}[.)]\s+(?![0-9])")
_ISOLATED_MAJOR_NOTE = re.compile(r"^\s*[0-9]{1,2}[.)]\s*$")
_DATE = re.compile(
    r"(?:[0-3]?[0-9](?:[./-]|\s+)[01]?[0-9](?:[./-]|\s+)(?:20)?[0-9]{2})|"
    r"(?:ngay\s+[0-3]?[0-9]\s+thang\s+[01]?[0-9]\s+nam\s+20[0-9]{2})"
)
_OWNER_ALIASES = [
    "Cho vay khách hàng",
    "Các khoản cho vay khách hàng",
    "Dư nợ cho vay khách hàng",
]
_BRANCH_ALIASES = [
    "Theo loại tiền tệ",
    "Theo loại hình tiền tệ",
    "Phân tích theo loại hình tiền tệ",
    "Phân tích theo loại tiền tệ",
    "Phân tích dư nợ theo loại hình tiền tệ",
    "Phân tích dư nợ theo loại tiền tệ",
    "Phân tích dư nợ cho vay theo loại tiền tệ",
    "Phân tích dư nợ theo loại tiền",
    "Phân loại dư nợ theo loại tiền tệ",
    "Phân tích cho vay theo loại tiền tệ",
]
_CHILD_ALIASES = {
    "VND_LOANS": [
        "Bằng VND",
        "Bằng đồng Việt Nam",
        "Cho vay bằng VND",
        "Cho vay bằng đồng Việt Nam",
        "Dư nợ bằng VND",
        "Dư nợ bằng đồng Việt Nam",
    ],
    "FOREIGN_CURRENCY_AND_GOLD_LOANS": [
        "Bằng ngoại tệ",
        "Bằng ngoại tệ và vàng",
        "Bằng vàng và ngoại tệ",
        "Cho vay bằng ngoại tệ",
        "Cho vay bằng ngoại tệ và vàng",
        "Cho vay bằng vàng và ngoại tệ",
        "Dư nợ bằng ngoại tệ",
        "Dư nợ bằng ngoại tệ và vàng",
    ],
}
_UNIT_ALIASES = ["triệu đồng", "triệu VND"]
_MAX_OWNER_PAGE_SPAN = 4
_MAX_CHILD_PAIR_LINE_GAP = 24
_MAX_NUMERIC_FOLLOWER_GAP = 6


class LoanCurrencyVariantGraphV1Error(ValueError):
    """The complete-PDF input or replayed loan-currency graph drifted."""


def _error(message: str) -> LoanCurrencyVariantGraphV1Error:
    return LoanCurrencyVariantGraphV1Error(message)


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
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence) or not value:
        raise _error("loan-currency matcher requires one complete nonempty PDF")
    pages: list[dict[str, Any]] = []
    previous_page = 0
    global_ordinal = 0
    for raw_page in value:
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_sequence",
            "primary_numeric_authority",
        }:
            raise _error("loan-currency matcher page fields drifted")
        sequence = raw_page["page_sequence"]
        if type(sequence) is not int or sequence != previous_page + 1:
            raise _error("complete PDF page sequence must be gap-free")
        if type(raw_page["primary_numeric_authority"]) is not bool:
            raise _error("primary numeric authority flag must be exact bool")
        if type(raw_page["lines"]) is not list:
            raise _error("page lines must be one list")
        lines: list[dict[str, Any]] = []
        for expected_index, raw_line in enumerate(raw_page["lines"]):
            if type(raw_line) is not dict or set(raw_line) != {
                "bbox",
                "source_line_index",
                "source_text",
                "vietocr_text",
            }:
                raise _error("loan-currency matcher line fields drifted")
            if raw_line["source_line_index"] != expected_index:
                raise _error("source line indices must be exact and gap-free")
            if raw_line["source_text"] is not None and type(raw_line["source_text"]) is not str:
                raise _error("source text must be null or one exact string")
            if type(raw_line["vietocr_text"]) is not str:
                raise _error("fresh VietOCR text must be one exact string")
            lines.append(
                {
                    "bbox": _bbox(raw_line["bbox"]),
                    "global_ordinal": global_ordinal,
                    "normalized_text": normalize_vietnamese_anchor_v1(raw_line["vietocr_text"]),
                    "page_sequence": sequence,
                    "source_line_index": expected_index,
                    "source_text": raw_line["source_text"],
                    "vietocr_text": raw_line["vietocr_text"],
                }
            )
            global_ordinal += 1
        pages.append(
            {
                "lines": lines,
                "page_sequence": sequence,
                "primary_numeric_authority": raw_page["primary_numeric_authority"],
            }
        )
        previous_page = sequence
    return pages


def _clean_heading(value: str) -> str:
    value = re.sub(r"^\s*[0-9]{1,2}(?:\.[0-9]{1,2})?\s*[.)\-–—:]?\s*", "", value)
    value = re.sub(r"\s*\(\s*tiếp\s+theo\s*\)\s*$", "", value, flags=re.IGNORECASE)
    return value.strip().rstrip(":;.-–—").strip()


def _match(value: str, aliases: Sequence[str], *, heading: bool = False) -> str | None:
    surface = _clean_heading(value) if heading else value.strip().lstrip("+-• ").strip()
    return match_vietnamese_anchor_alias_v1(surface, aliases)


def _is_money(value: str) -> bool:
    token = value.strip().replace("\u00a0", " ").replace("\u202f", " ")
    compact = token.replace(" ", "")
    if _DASH.fullmatch(compact) is not None:
        return True
    if _NUMBER.fullmatch(compact) is not None and any(char.isdigit() for char in compact):
        return True
    body = compact.strip("()")
    digits = sum(char.isdigit() for char in body)
    letters = [char.lower() for char in body if char.isalpha()]
    return (
        digits >= 4
        and 1 <= len(letters) <= 2
        and all(char in {"b", "i", "l", "o", "s", "z"} for char in letters)
        and all(char.isdigit() or char in ".,-" or char.isalpha() for char in body)
        and digits / (digits + len(letters)) >= 0.70
    )


def _join(lines: Sequence[Mapping[str, Any]], start: int, width: int) -> str:
    return " ".join(line["vietocr_text"].strip() for line in lines[start : start + width]).strip()


def _label_matches(
    lines: Sequence[Mapping[str, Any]], aliases: Sequence[str], *, heading: bool = False
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for index in range(len(lines)):
        for width in range(1, min(3, len(lines) - index) + 1):
            surface = _join(lines, index, width)
            kind = _match(surface, aliases, heading=heading)
            if kind is None:
                continue
            matches.append(
                {
                    "bbox": list(lines[index]["bbox"]),
                    "end_source_line_index": index + width - 1,
                    "global_ordinal": lines[index]["global_ordinal"],
                    "match_kind": kind,
                    "normalized_surface": normalize_vietnamese_anchor_v1(surface),
                    "page_sequence": lines[index]["page_sequence"],
                    "source_line_index": index,
                    "surface": surface,
                }
            )
            break
    return matches


def _document_lines(pages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [line for page in pages for line in page["lines"]]


def _dedupe_matches_ending_on_same_line(
    matches: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Prefer the shortest exact window when a standalone title also matches.

    A preceding isolated note number may join with an already-complete owner
    line, yielding the same logical owner twice.  Wrapped titles remain intact
    because no shorter suffix matches their final line.
    """

    selected: dict[tuple[int, int], Mapping[str, Any]] = {}
    for match in matches:
        key = (match["page_sequence"], match["end_source_line_index"])
        current = selected.get(key)
        if current is None or match["source_line_index"] > current["source_line_index"]:
            selected[key] = match
    return [dict(selected[key]) for key in sorted(selected)]


def _next_note_ordinal(
    lines: Sequence[Mapping[str, Any]],
    owner: Mapping[str, Any],
    *,
    enable_extended_annual_variants: bool,
) -> int:
    owner_page = owner["page_sequence"]
    for line in lines[owner["global_ordinal"] + 1 :]:
        if line["page_sequence"] > owner_page + _MAX_OWNER_PAGE_SPAN:
            return line["global_ordinal"]
        if (
            _MAJOR_NOTE.match(line["vietocr_text"])
            or (
                enable_extended_annual_variants and _ISOLATED_MAJOR_NOTE.match(line["vietocr_text"])
            )
        ) and line["page_sequence"] >= owner_page:
            return line["global_ordinal"]
    return len(lines)


def _numeric_followers(
    lines: Sequence[Mapping[str, Any]],
    match: Mapping[str, Any],
    stop_ordinal: int,
    *,
    enable_extended_annual_variants: bool,
) -> list[dict[str, Any]]:
    if enable_extended_annual_variants:
        same_row = [
            line
            for line in lines
            if line["page_sequence"] == match["page_sequence"]
            and line["global_ordinal"] < stop_ordinal
            and line["bbox"][0] >= match["bbox"][2]
            and min(match["bbox"][3], line["bbox"][3]) - max(match["bbox"][1], line["bbox"][1])
            >= 0.25
            * min(
                match["bbox"][3] - match["bbox"][1],
                line["bbox"][3] - line["bbox"][1],
            )
            and _is_money(line["vietocr_text"])
        ]
        if len(same_row) >= 2:
            return [
                {
                    "bbox": list(line["bbox"]),
                    "source_line_index": line["source_line_index"],
                    "source_text": line["source_text"],
                    "vietocr_text": line["vietocr_text"],
                }
                for line in sorted(same_row, key=lambda item: (item["bbox"][0], item["bbox"][1]))
            ]
    flattened_axis = (
        match["global_ordinal"] < len(lines)
        and lines[match["global_ordinal"]]["global_ordinal"] == match["global_ordinal"]
    )
    start = (
        (match["global_ordinal"] if flattened_axis else match["source_line_index"])
        + (match["end_source_line_index"] - match["source_line_index"])
        + 1
    )
    followers: list[dict[str, Any]] = []
    for line in lines[start : min(stop_ordinal, start + _MAX_NUMERIC_FOLLOWER_GAP)]:
        if line["page_sequence"] != match["page_sequence"]:
            break
        if any(_match(line["vietocr_text"], aliases) for aliases in _CHILD_ALIASES.values()):
            break
        if _is_money(line["vietocr_text"]):
            followers.append(
                {
                    "bbox": list(line["bbox"]),
                    "source_line_index": line["source_line_index"],
                    "source_text": line["source_text"],
                    "vietocr_text": line["vietocr_text"],
                }
            )
        elif enable_extended_annual_variants and followers:
            break
    return followers


def _periods_and_units(
    lines: Sequence[Mapping[str, Any]], start: int, stop: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    periods: list[dict[str, Any]] = []
    units: list[dict[str, Any]] = []
    for line in lines[start:stop]:
        normalized = line["normalized_text"]
        if _DATE.search(normalized):
            periods.append(
                {
                    "bbox": list(line["bbox"]),
                    "page_sequence": line["page_sequence"],
                    "source_line_index": line["source_line_index"],
                    "vietocr_text": line["vietocr_text"],
                }
            )
        if _match(line["vietocr_text"], _UNIT_ALIASES) is not None:
            units.append(
                {
                    "bbox": list(line["bbox"]),
                    "page_sequence": line["page_sequence"],
                    "source_line_index": line["source_line_index"],
                    "vietocr_text": line["vietocr_text"],
                }
            )
    return periods, units


def _orientation(events: Sequence[Mapping[str, Any]]) -> str:
    same_rows = 0
    below_rows = 0
    for event in events:
        label_center = (event["bbox"][1] + event["bbox"][3]) / 2
        for value in event["value_proposals"]:
            value_center = (value["bbox"][1] + value["bbox"][3]) / 2
            if abs(label_center - value_center) <= max(18, event["bbox"][3] - event["bbox"][1]):
                same_rows += 1
            elif value_center > label_center:
                below_rows += 1
    if same_rows and below_rows:
        return "HYBRID_HORIZONTAL_VERTICAL"
    if same_rows:
        return "HORIZONTAL_ROWS_WITH_PERIOD_COLUMNS"
    return "VERTICAL_BLOCKS_WITH_HORIZONTAL_VALUE_LANES"


def _region(
    lines: Sequence[Mapping[str, Any]],
    owner: Mapping[str, Any],
    stop: int,
    branches: Sequence[Mapping[str, Any]],
    child_matches: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    enable_extended_annual_variants: bool,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    role_candidates: dict[str, list[dict[str, Any]]] = {}
    reasons: list[str] = []
    for role, matches in child_matches.items():
        candidates = [
            dict(match)
            for match in matches
            if owner["global_ordinal"] < match["global_ordinal"] < stop
        ]
        for match in candidates:
            match["value_proposals"] = _numeric_followers(
                lines,
                match,
                stop,
                enable_extended_annual_variants=enable_extended_annual_variants,
            )
        candidates = [match for match in candidates if len(match["value_proposals"]) >= 2]
        role_candidates[role] = candidates
        if not candidates:
            reasons.append(f"MISSING_{role}_WITH_TWO_PERIOD_VALUES")
    near = {
        "owner_context": canonical_clone_v1(owner),
        "unresolved_reasons": sorted(reasons),
    }
    if reasons:
        return None, near
    selected = {
        role: min(matches, key=lambda item: item["global_ordinal"])
        for role, matches in role_candidates.items()
    }
    if len({item["page_sequence"] for item in selected.values()}) > 2:
        near["unresolved_reasons"] = ["CURRENCY_CHILDREN_EXCEED_TWO_PAGE_CONTINUATION"]
        return None, near
    events = []
    for role, match in sorted(selected.items(), key=lambda item: item[1]["global_ordinal"]):
        events.append(
            {
                "bbox": match["bbox"],
                "match_kind": match["match_kind"],
                "normalized_surface": match["normalized_surface"],
                "page_sequence": match["page_sequence"],
                "role": role,
                "source_line_index": match["source_line_index"],
                "surface": match["surface"],
                "value_proposals": match["value_proposals"],
            }
        )
    last_event = max(
        events,
        key=lambda item: (
            item["page_sequence"],
            max(value["source_line_index"] for value in item["value_proposals"]),
        ),
    )
    last_index = max(value["source_line_index"] for value in last_event["value_proposals"])
    first_child_ordinal = min(item["global_ordinal"] for item in selected.values())
    eligible_branches = [
        item
        for item in branches
        if owner["global_ordinal"] < item["global_ordinal"] < first_child_ordinal
    ]
    if enable_extended_annual_variants:
        eligible_branches.extend(
            item
            for item in branches
            if item["page_sequence"] == owner["page_sequence"]
            and item["global_ordinal"] < owner["global_ordinal"]
            and owner["source_line_index"] - item["end_source_line_index"] <= 8
        )
    branch = (
        max(eligible_branches, key=lambda item: item["global_ordinal"])
        if eligible_branches
        else None
    )
    period_records, unit_records = _periods_and_units(
        lines,
        owner["global_ordinal"] + 1,
        max(item["global_ordinal"] for item in selected.values()) + _MAX_NUMERIC_FOLLOWER_GAP + 1,
    )
    minimal_anchor_roles = ["LOAN_OWNER", events[0]["role"]]
    material = {
        "branch_match": canonical_clone_v1(branch),
        "cluster_boundary": {
            "first_item_role": (
                "OPTIONAL_CURRENCY_BRANCH"
                if branch is not None and branch["global_ordinal"] < owner["global_ordinal"]
                else "CUSTOMER_LOAN_OWNER"
            ),
            "first_page_sequence": (
                branch["page_sequence"]
                if branch is not None and branch["global_ordinal"] < owner["global_ordinal"]
                else owner["page_sequence"]
            ),
            "first_source_line_index": (
                branch["source_line_index"]
                if branch is not None and branch["global_ordinal"] < owner["global_ordinal"]
                else owner["source_line_index"]
            ),
            "last_item_role": last_event["role"],
            "last_page_sequence": last_event["page_sequence"],
            "last_source_line_index": last_index,
            "selection_rule": (
                "LOAN_OWNER_PRECEDES_OPTIONAL_BRANCH_AND_BOTH_CURRENCY_CHILDREN_"
                "THROUGH_LAST_TWO_PERIOD_VALUE_BEFORE_NEXT_NUMBERED_NOTE"
            ),
        },
        "events": events,
        "layout": {
            "orientation": _orientation(events),
            "period_headings": period_records,
            "unit_headings": unit_records,
        },
        "minimal_anchor": {
            "combination_size": 2,
            "pair_search_exhausted_before_larger_combinations": True,
            "roles": minimal_anchor_roles,
        },
        "owner_context": canonical_clone_v1(owner),
    }
    return {
        **material,
        "region_id": "lcvgv1:region:" + canonical_json_sha256_v1(material),
    }, near


def _orphan_pairs(
    pages: Sequence[Mapping[str, Any]],
    owner_regions: Sequence[Mapping[str, Any]],
    *,
    enable_extended_annual_variants: bool,
) -> list[dict[str, Any]]:
    covered = {
        (event["page_sequence"], event["source_line_index"])
        for region in owner_regions
        for event in region["events"]
    }
    near: list[dict[str, Any]] = []
    for page in pages:
        by_role = {
            role: _label_matches(page["lines"], aliases) for role, aliases in _CHILD_ALIASES.items()
        }
        for left in by_role["VND_LOANS"]:
            for right in by_role["FOREIGN_CURRENCY_AND_GOLD_LOANS"]:
                if (
                    abs(left["source_line_index"] - right["source_line_index"])
                    > _MAX_CHILD_PAIR_LINE_GAP
                ):
                    continue
                if (left["page_sequence"], left["source_line_index"]) in covered or (
                    right["page_sequence"],
                    right["source_line_index"],
                ) in covered:
                    continue
                if (
                    len(
                        _numeric_followers(
                            page["lines"],
                            left,
                            len(page["lines"]),
                            enable_extended_annual_variants=enable_extended_annual_variants,
                        )
                    )
                    < 2
                ):
                    continue
                if (
                    len(
                        _numeric_followers(
                            page["lines"],
                            right,
                            len(page["lines"]),
                            enable_extended_annual_variants=enable_extended_annual_variants,
                        )
                    )
                    < 2
                ):
                    continue
                near.append(
                    {
                        "anchor_pair": [
                            {
                                "role": "VND_LOANS",
                                "source_line_index": left["source_line_index"],
                                "surface": left["surface"],
                            },
                            {
                                "role": "FOREIGN_CURRENCY_AND_GOLD_LOANS",
                                "source_line_index": right["source_line_index"],
                                "surface": right["surface"],
                            },
                        ],
                        "page_sequence": page["page_sequence"],
                        "unresolved_reasons": ["CUSTOMER_LOAN_OWNER_NOT_PRECEDING_CURRENCY_PAIR"],
                    }
                )
                break
    return near


def _collapse_same_cluster_regions(
    regions: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Keep the nearest owner when repeated/continued owners reach one table."""

    selected: dict[tuple[tuple[str, int, int], ...], Mapping[str, Any]] = {}
    shadowed: list[dict[str, Any]] = []
    for region in regions:
        key = tuple(
            (event["role"], event["page_sequence"], event["source_line_index"])
            for event in region["events"]
        )
        current = selected.get(key)
        if current is None:
            selected[key] = region
            continue
        winner, loser = sorted(
            (current, region),
            key=lambda item: item["owner_context"]["global_ordinal"],
            reverse=True,
        )
        selected[key] = winner
        shadowed.append(
            {
                "owner_context": canonical_clone_v1(loser["owner_context"]),
                "unresolved_reasons": ["SHADOWED_EARLIER_OWNER_FOR_SAME_CURRENCY_CLUSTER"],
            }
        )
    ordered = sorted(
        selected.values(),
        key=lambda item: (
            item["events"][0]["page_sequence"],
            item["events"][0]["source_line_index"],
        ),
    )
    return [canonical_clone_v1(item) for item in ordered], shadowed


def _build(value: Any, *, enable_extended_annual_variants: bool) -> dict[str, Any]:
    pages = _pages(value)
    lines = _document_lines(pages)
    owners = _dedupe_matches_ending_on_same_line(
        [
            match
            for page in pages
            for match in _label_matches(page["lines"], _OWNER_ALIASES, heading=True)
        ]
    )
    branches = [
        match
        for page in pages
        for match in _label_matches(page["lines"], _BRANCH_ALIASES, heading=True)
    ]
    child_matches = {
        role: [match for page in pages for match in _label_matches(page["lines"], aliases)]
        for role, aliases in _CHILD_ALIASES.items()
    }
    regions: list[dict[str, Any]] = []
    near_regions: list[dict[str, Any]] = []
    for owner in owners:
        region, near = _region(
            lines,
            owner,
            _next_note_ordinal(
                lines,
                owner,
                enable_extended_annual_variants=enable_extended_annual_variants,
            ),
            branches,
            child_matches,
            enable_extended_annual_variants=enable_extended_annual_variants,
        )
        if region is None:
            near_regions.append(near)
        else:
            regions.append(region)
    if enable_extended_annual_variants:
        regions, shadowed = _collapse_same_cluster_regions(regions)
        near_regions.extend(shadowed)
    near_regions.extend(
        _orphan_pairs(
            pages,
            regions,
            enable_extended_annual_variants=enable_extended_annual_variants,
        )
    )
    uniqueness = {
        "complete_region_count": len(regions),
        "status": (
            "UNIQUE_FULL_MATCH"
            if len(regions) == 1
            else "NO_FULL_MATCH"
            if not regions
            else "MULTIPLE_FULL_MATCHES"
        ),
    }
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "metrics": {
            "complete_loan_currency_region_count": len(regions),
            "complete_pdf_page_count": len(pages),
            "loan_owner_candidate_count": len(owners),
            "near_region_count": len(near_regions),
            "orphan_currency_pair_negative_control_count": sum(
                "anchor_pair" in item for item in near_regions
            ),
        },
        "near_regions": near_regions,
        "regions": regions,
        "safety": canonical_clone_v1(_SAFETY),
        "status": (
            "ACCEPTED_UNIQUE_VARIANT_GRAPH"
            if len(regions) == 1
            else "UNRESOLVED_NO_COMPLETE_REGION"
            if not regions
            else "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
        ),
        "uniqueness": uniqueness,
    }
    return {**material, "result_id": "lcvgv1:result:" + canonical_json_sha256_v1(material)}


def _validate_shape(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("loan-currency graph fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["regions"]) is not list
        or type(value["near_regions"]) is not list
        or type(value["metrics"]) is not dict
        or type(value["uniqueness"]) is not dict
    ):
        raise _error("loan-currency graph identity, authority or axes drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "lcvgv1:result:" + canonical_json_sha256_v1(material):
        raise _error("loan-currency graph identity drifted")
    return canonical_clone_v1(value)


def build_loan_currency_variant_graph_document_v1(
    document_pages: Any,
    *,
    enable_extended_annual_variants: bool = False,
) -> dict[str, Any]:
    """Scan one complete PDF for the shared loan-currency family graph."""

    return _validate_shape(
        _build(
            document_pages,
            enable_extended_annual_variants=enable_extended_annual_variants,
        )
    )


def validate_loan_currency_variant_graph_replay_v1(
    value: Any,
    document_pages: Any,
    *,
    enable_extended_annual_variants: bool = False,
) -> dict[str, Any]:
    """Rebuild the complete-PDF graph and reject coordinated self-rehashes."""

    checked = _validate_shape(value)
    rebuilt = _build(
        document_pages,
        enable_extended_annual_variants=enable_extended_annual_variants,
    )
    if not same_typed_json_v1(checked, rebuilt):
        raise _error("loan-currency graph does not replay exactly")
    return checked
