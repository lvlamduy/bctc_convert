"""Bank-blind variable graph for trading-securities note clusters.

The matcher scans one complete PDF.  It locates a trading-securities owner,
then requires debt, equity and provision parents in PDF order while allowing
issuer-classification and listed/unlisted child variants.  Parent subtotals may
appear before or after their children; gross and net rows may be unlabeled.

Fresh VietOCR text is used only as semantic anchor evidence.  Geometry, period
and unit axes, row order and accounting totals are retained for a later
independent pixel/accounting verifier.  Bank, filename, note and page identity
are never matcher inputs.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Mapping, Sequence
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
    "GENERALIZED_FORMAT_VERSION",
    "TradingSecuritiesVariantGraphV1Error",
    "build_generalized_trading_securities_variant_graph_document_v2",
    "build_trading_securities_variant_graph_document_v1",
    "validate_generalized_trading_securities_variant_graph_replay_v2",
    "validate_trading_securities_variant_graph_replay_v1",
]


FORMAT_VERSION = "TRADING_SECURITIES_VARIANT_GRAPH_DOCUMENT_V1"
GENERALIZED_FORMAT_VERSION = "TRADING_SECURITIES_VARIANT_GRAPH_DOCUMENT_V2"
FAMILY_ID = "TRADING_SECURITIES"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_TRADING_SECURITIES_OWNER_PARENT_CHILD_"
    "FIRST_LAST_CLUSTER_BOUNDARY_LAYOUT_PERIOD_UNIT_GROSS_PROVISION_NET_STRUCTURE_"
    "PROPOSAL_ONLY_NO_NUMERIC_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
GENERALIZED_CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_TRADING_SECURITIES_OWNER_OPTIONAL_"
    "ASSET_BRANCH_PARENT_CHILD_PERIOD_UNIT_VISIBLE_TOTAL_AND_NONADDITIVE_"
    "ALTERNATE_VIEW_STRUCTURE_PROPOSAL_ONLY_NO_NUMERIC_SCHEMA_MAPPING_"
    "CANONICALIZATION_OR_EXPORT_AUTHORITY"
)

_REQUIRED_PARENT_ROLES = frozenset({"DEBT", "EQUITY", "PROVISION"})
_PARENT_ORDER = ("DEBT", "EQUITY", "OTHER_TRADING", "PROVISION")
_CHILD_ORDER = (
    "GOVERNMENT",
    "TCTD",
    "DOMESTIC_TCKT",
    "FOREIGN_TCKT",
    "OTHER",
    "LISTED",
    "UNLISTED",
)
_NUMBER = re.compile(r"^\(?-?[0-9]+(?:[.,][0-9]+)*\)?$")
_DASH = re.compile(r"^[\-–—]+$")

_SAFETY = {
    "bank_filename_note_or_page_used_for_inference": False,
    "complete_pdf_region_enumeration_required": True,
    "fresh_vietocr_transformer_text_required": True,
    "mapping_authority": False,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "pair_combinations_exhausted_before_triples": True,
    "parent_order_fixed": False,
    "parent_precedes_child_required": True,
    "percentage_or_auxiliary_axis_used_as_money": False,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "schema_authority": False,
    "text_similarity_alone_can_accept": False,
    "whole_pdf_uniqueness_required": True,
}
_GENERALIZED_SAFETY = {
    **_SAFETY,
    "alternate_nonadditive_view_counted_as_second_family": False,
    "debt_equity_and_provision_all_required": False,
    "optional_asset_or_provision_branch_supported": True,
    "sparse_candidate_requires_period_unit_child_and_numeric_evidence": True,
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


class TradingSecuritiesVariantGraphV1Error(ValueError):
    """The trading-securities graph input or deterministic replay drifted."""


def _error(message: str) -> TradingSecuritiesVariantGraphV1Error:
    return TradingSecuritiesVariantGraphV1Error(message)


def _norm(value: Any, label: str = "text") -> str:
    if type(value) is not str:
        raise _error(f"{label} must be one exact string")
    return normalize_vietnamese_anchor_v1(value)


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
        raise _error("trading-securities matcher requires one complete nonempty PDF")
    pages: list[dict[str, Any]] = []
    prior_page = 0
    for raw_page in value:
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_sequence",
            "primary_numeric_authority",
        }:
            raise _error("trading-securities matcher page fields drifted")
        page_sequence = raw_page["page_sequence"]
        if type(page_sequence) is not int or page_sequence != prior_page + 1:
            raise _error("complete PDF page sequence must be gap-free")
        if type(raw_page["primary_numeric_authority"]) is not bool:
            raise _error("primary numeric authority flag must be exact bool")
        if type(raw_page["lines"]) is not list:
            raise _error("page lines must be one list")
        lines: list[dict[str, Any]] = []
        prior_index = -1
        for raw_line in raw_page["lines"]:
            if type(raw_line) is not dict or set(raw_line) != {
                "bbox",
                "source_line_index",
                "source_text",
                "vietocr_text",
            }:
                raise _error("trading-securities line fields drifted")
            index = raw_line["source_line_index"]
            if type(index) is not int or index <= prior_index:
                raise _error("source line indices must be exact and increasing")
            source_text = raw_line["source_text"]
            if source_text is not None and type(source_text) is not str:
                raise _error("source text must be null or one exact string")
            text = raw_line["vietocr_text"]
            if type(text) is not str:
                raise _error("fresh VietOCR text must be one exact string")
            lines.append(
                {
                    "bbox": _bbox(raw_line["bbox"]),
                    "normalized_text": _norm(text),
                    "source_line_index": index,
                    "source_text": source_text,
                    "vietocr_text": text,
                }
            )
            prior_index = index
        pages.append(
            {
                "lines": lines,
                "page_sequence": page_sequence,
                "primary_numeric_authority": raw_page["primary_numeric_authority"],
            }
        )
        prior_page = page_sequence
    return pages


def _owner(text: str) -> bool:
    if "chung khoan kinh doanh" not in text:
        return False
    forbidden = (
        "bao gom",
        "du phong",
        "khac",
        "lai lo",
        "lai tu",
        "thay doi",
        "mua ban",
        "thu nhap",
        "rui ro",
    )
    return (
        "chung khoan dau tu" not in text
        and len(text.split()) <= 9
        and not any(term in text for term in forbidden)
    )


def _negative_family(text: str) -> str | None:
    if "chung khoan dau tu" in text and len(text.split()) <= 14:
        return "DISTINCT_INVESTMENT_SECURITIES_SUBFAMILY"
    if (
        "du phong chung khoan kinh doanh" in text
        or "thay doi du phong chung khoan kinh doanh" in text
    ) and "rui ro" not in text:
        return "DISTINCT_TRADING_SECURITIES_PROVISION_MOVEMENT_SUBFAMILY"
    return None


def _section_break(text: str) -> bool:
    if _negative_family(text) is not None:
        return True
    return any(
        term in text
        for term in (
            "cho vay khach hang",
            "gop von dau tu dai han",
            "cac khoan dau tu dai han khac",
        )
    )


def _parent_role(text: str) -> str | None:
    words = text.split()
    narrative = any(
        term in text for term in ("bao gom", "duoc", "trich lap", "ghi nhan", "doi voi")
    )
    if text.startswith("chung khoan no") and len(words) <= 4 and not narrative:
        return "DEBT"
    if text.startswith("chung khoan von") and len(words) <= 4 and not narrative:
        return "EQUITY"
    if text.startswith("chung khoan kinh doanh khac") and len(words) <= 6 and not narrative:
        return "OTHER_TRADING"
    if (
        (
            "du phong rui ro chung khoan kinh doanh" in text
            or "du phong rui do chung khoan kinh doanh" in text
            or "du phong giam gia chung khoan kinh doanh" in text
            or "du phong rui ro chung khoan" in text
        )
        and len(words) <= 9
        and not narrative
    ):
        return "PROVISION"
    return None


def _provision_detail_role(text: str) -> str | None:
    if "du phong chung" in text:
        return "PROVISION_GENERAL"
    if "du phong cu the" in text or (
        "du phong giam gia" in text and "chung khoan kinh doanh" not in text
    ):
        return "PROVISION_SPECIFIC"
    return None


def _child_role(text: str) -> str | None:
    if "chua niem yet" in text:
        return "UNLISTED"
    if "niem yet" in text:
        return "LISTED"
    if "chinh phu" in text or "kho bac" in text or "nhnn" in text:
        return "GOVERNMENT"
    if "tctd" in text or "to chuc tin dung" in text:
        return "TCTD"
    if (
        "tckt trong nuoc" in text
        or "to chuc kinh te trong nuoc" in text
        or "doanh nghiep trong nuoc" in text
    ):
        return "DOMESTIC_TCKT"
    if (
        "tckt nuoc ngoai" in text
        or "to chuc kinh te nuoc ngoai" in text
        or "chung khoan nuoc ngoai" in text
    ):
        return "FOREIGN_TCKT"
    if text in {"khac", "chung khoan khac"}:
        return "OTHER"
    return None


def _is_number(line: Mapping[str, Any]) -> bool:
    token = line["vietocr_text"].strip().replace(" ", "")
    return bool(_NUMBER.fullmatch(token) or _DASH.fullmatch(token))


def _value_proposals(
    lines: Sequence[Mapping[str, Any]], line: Mapping[str, Any]
) -> list[dict[str, Any]]:
    top, bottom = line["bbox"][1], line["bbox"][3]
    width = max((item["bbox"][2] for item in lines), default=1)
    result = []
    for item in lines:
        center_y = (item["bbox"][1] + item["bbox"][3]) / 2
        if (
            item["bbox"][0] > width * 0.43
            and top - 14 <= center_y <= bottom + 14
            and _is_number(item)
        ):
            result.append(
                {
                    "bbox": list(item["bbox"]),
                    "raw_text": item["vietocr_text"],
                    "source_line_index": item["source_line_index"],
                }
            )
    return sorted(result, key=lambda item: (item["bbox"][0], item["source_line_index"]))


def _events(lines: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    active_parent: str | None = None
    for line in lines:
        text = line["normalized_text"]
        parent = _parent_role(text)
        detail = _provision_detail_role(text)
        child = _child_role(text)
        if parent is not None:
            active_parent = parent
            role_kind = "PARENT"
            role = parent
        elif detail is not None and active_parent == "PROVISION":
            role_kind = "PROVISION_DETAIL"
            role = detail
        elif child is not None and active_parent in {"DEBT", "EQUITY", "OTHER_TRADING"}:
            role_kind = "CHILD"
            role = child
        else:
            continue
        events.append(
            {
                "bbox": list(line["bbox"]),
                "normalized_label": text,
                "parent_role": active_parent,
                "role": role,
                "role_kind": role_kind,
                "source_line_index": line["source_line_index"],
                "value_proposals": _value_proposals(lines, line),
                "vietocr_label": line["vietocr_text"],
            }
        )
    return events


def _period_headers(
    lines: Sequence[Mapping[str, Any]], *, allow_year_end_words: bool = False
) -> list[dict[str, Any]]:
    result = []
    width = max((line["bbox"][2] for line in lines), default=1)
    for line in lines:
        text = line["normalized_text"]
        if line["bbox"][0] > width * 0.4 and (
            re.search(r"(?:30|31)[ /.-](?:0?[136]|12)[ /.-]20[0-9]{2}", text)
            or re.search(r"(?:30|31) thang (?:0?[136]|12) nam 20[0-9]{2}", text)
            or text.startswith("ngay 30 thang")
            or text.startswith("ngay 31 thang")
            or "so cuoi ky" in text
            or "so dau ky" in text
            or (allow_year_end_words and "so cuoi nam" in text)
            or (allow_year_end_words and "so dau nam" in text)
        ):
            result.append(
                {
                    "bbox": list(line["bbox"]),
                    "source_line_index": line["source_line_index"],
                    "vietocr_text": line["vietocr_text"],
                }
            )
    return result


def _unit_headers(lines: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "bbox": list(line["bbox"]),
            "source_line_index": line["source_line_index"],
            "vietocr_text": line["vietocr_text"],
        }
        for line in lines
        if any(
            term in line["normalized_text"]
            for term in ("trieu dong", "nghin dong", "vnd", "dong viet nam")
        )
    ]


def _percentage_headers(lines: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "bbox": list(line["bbox"]),
            "source_line_index": line["source_line_index"],
            "vietocr_text": line["vietocr_text"],
        }
        for line in lines
        if "%" in line["vietocr_text"] or "ty trong" in line["normalized_text"]
    ]


def _unlabeled_numeric_rows(
    lines: Sequence[Mapping[str, Any]], events: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    event_y = {(event["bbox"][1] + event["bbox"][3]) / 2 for event in events}
    numeric = [line for line in lines if _is_number(line)]
    rows: list[list[Mapping[str, Any]]] = []
    for line in sorted(
        numeric, key=lambda item: ((item["bbox"][1] + item["bbox"][3]) / 2, item["bbox"][0])
    ):
        center_y = (line["bbox"][1] + line["bbox"][3]) / 2
        if any(abs(center_y - value) <= 14 for value in event_y):
            continue
        if not rows:
            rows.append([line])
            continue
        prior_y = sum((item["bbox"][1] + item["bbox"][3]) / 2 for item in rows[-1]) / len(rows[-1])
        if abs(center_y - prior_y) <= 14:
            rows[-1].append(line)
        else:
            rows.append([line])
    return [
        {
            "source_line_indices": [item["source_line_index"] for item in row],
            "values": [
                item["vietocr_text"] for item in sorted(row, key=lambda item: item["bbox"][0])
            ],
            "y_center": round(
                sum((item["bbox"][1] + item["bbox"][3]) / 2 for item in row) / len(row), 3
            ),
        }
        for row in rows
        if len(row) >= 2
    ]


def _candidate_pages(
    pages: Sequence[Mapping[str, Any]],
    *,
    generalized: bool = False,
    stop_at_next_owner: bool = False,
) -> list[dict[str, Any]]:
    result = []
    for page in pages:
        lines = page["lines"]
        owner_positions = [
            position for position, line in enumerate(lines) if _owner(line["normalized_text"])
        ]
        for position in owner_positions:
            first_parent_position = next(
                (
                    offset
                    for offset in range(position + 1, len(lines))
                    if _parent_role(lines[offset]["normalized_text"]) is not None
                ),
                None,
            )
            if first_parent_position is None:
                continue
            if any(position < other < first_parent_position for other in owner_positions):
                continue
            stop = len(lines)
            for offset in range(first_parent_position + 1, len(lines)):
                if _section_break(lines[offset]["normalized_text"]) or (
                    stop_at_next_owner and _owner(lines[offset]["normalized_text"])
                ):
                    stop = offset
                    break
            region_lines = lines[position:stop]
            axis_context_lines = lines[max(0, position - 2) : stop]
            events = _events(region_lines)
            parents = [event for event in events if event["role_kind"] == "PARENT"]
            result.append(
                {
                    "events": events,
                    "owner": {
                        "bbox": list(lines[position]["bbox"]),
                        "normalized_text": lines[position]["normalized_text"],
                        "source_line_index": lines[position]["source_line_index"],
                        "vietocr_text": lines[position]["vietocr_text"],
                    },
                    "page_sequence": page["page_sequence"],
                    "parent_roles_in_pdf_order": [event["role"] for event in parents],
                    "percentage_headers": _percentage_headers(axis_context_lines),
                    "period_headers": _period_headers(
                        axis_context_lines, allow_year_end_words=generalized
                    ),
                    "primary_numeric_authority": page["primary_numeric_authority"],
                    "region_lines": canonical_clone_v1(region_lines),
                    "unit_headers": _unit_headers(axis_context_lines),
                    "unlabeled_numeric_rows": _unlabeled_numeric_rows(region_lines, events),
                }
            )
    return result


def _view_kind(candidate: Mapping[str, Any]) -> str:
    texts = [candidate["owner"]["normalized_text"]]
    texts.extend(line["normalized_text"] for line in candidate["region_lines"])
    child_roles = {event["role"] for event in candidate["events"] if event["role_kind"] == "CHILD"}
    if any("tinh trang niem yet" in text for text in texts) or child_roles & {
        "LISTED",
        "UNLISTED",
    }:
        return "ALTERNATE_LISTING_VIEW"
    if any("chi tiet chung khoan kinh doanh" in text for text in texts):
        return "PRIMARY_DETAIL_VIEW"
    return "GENERAL_DETAIL_VIEW"


def _generalized_complete(candidate: Mapping[str, Any]) -> bool:
    parents = set(candidate["parent_roles_in_pdf_order"])
    if _REQUIRED_PARENT_ROLES.issubset(parents):
        return True
    asset_parents = parents & {"DEBT", "EQUITY", "OTHER_TRADING"}
    child_count = sum(event["role_kind"] == "CHILD" for event in candidate["events"])
    numeric_evidence = bool(candidate["unlabeled_numeric_rows"]) or any(
        event["value_proposals"] for event in candidate["events"]
    )
    return (
        bool(asset_parents)
        and child_count >= 1
        and len(candidate["period_headers"]) >= 2
        and len(candidate["unit_headers"]) >= 1
        and numeric_evidence
    )


def _suppress_supplemental_views(
    candidates: Sequence[Mapping[str, Any]],
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    selected: list[Mapping[str, Any]] = []
    suppressed: list[Mapping[str, Any]] = []
    for candidate in candidates:
        if _view_kind(candidate) != "ALTERNATE_LISTING_VIEW":
            selected.append(candidate)
            continue
        has_nearby_primary = any(
            _view_kind(other) != "ALTERNATE_LISTING_VIEW"
            and 0 <= candidate["page_sequence"] - other["page_sequence"] <= 1
            for other in candidates
        )
        (suppressed if has_nearby_primary else selected).append(candidate)
    return selected, suppressed


def _negative_regions(pages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for page in pages:
        for line in page["lines"]:
            family = _negative_family(line["normalized_text"])
            if family is None:
                continue
            material = {
                "negative_family": family,
                "owner_source_line_index": line["source_line_index"],
                "owner_vietocr_text": line["vietocr_text"],
                "page_sequence": page["page_sequence"],
                "status": "EXCLUDED_DISTINCT_SECURITIES_SUBFAMILY",
            }
            result.append(
                {**material, "near_region_id": "tsvgv1:near:" + canonical_json_sha256_v1(material)}
            )
    return result


def _anchor_set(candidate: Mapping[str, Any]) -> set[str]:
    anchors = {"PARENT:TRADING_SECURITIES"}
    anchors.update(f"ROLE:{role}" for role in candidate["parent_roles_in_pdf_order"])
    anchors.update(
        f"CHILD:{event['role']}" for event in candidate["events"] if event["role_kind"] == "CHILD"
    )
    return anchors


def _generalized_anchor_set(candidate: Mapping[str, Any]) -> set[str]:
    return _anchor_set(candidate) | {f"VIEW:{_view_kind(candidate)}"}


def _minimal_anchor(
    selected: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    selected_anchors = sorted(_anchor_set(selected))
    for size in (2, 3):
        for combination in itertools.combinations(selected_anchors, size):
            match_count = sum(
                set(combination).issubset(_anchor_set(candidate)) for candidate in candidates
            )
            if match_count == 1:
                return {
                    "anchors": list(combination),
                    "combination_size": size,
                    "full_document_match_count": 1,
                    "status": "UNIQUE_MINIMAL_ANCHOR_COMBINATION",
                }
    return {
        "anchors": selected_anchors,
        "combination_size": len(selected_anchors),
        "full_document_match_count": sum(
            set(selected_anchors).issubset(_anchor_set(candidate)) for candidate in candidates
        ),
        "status": "UNRESOLVED_NO_UNIQUE_PAIR_OR_TRIPLE",
    }


def _generalized_minimal_anchor(
    selected: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    selected_anchors = sorted(_generalized_anchor_set(selected))
    for size in (2, 3):
        for combination in itertools.combinations(selected_anchors, size):
            match_count = sum(
                set(combination).issubset(_generalized_anchor_set(candidate))
                for candidate in candidates
            )
            if match_count == 1:
                return {
                    "anchors": list(combination),
                    "combination_size": size,
                    "full_document_match_count": 1,
                    "status": "UNIQUE_MINIMAL_ANCHOR_COMBINATION",
                }
    return {
        "anchors": selected_anchors,
        "combination_size": len(selected_anchors),
        "full_document_match_count": sum(
            set(selected_anchors).issubset(_generalized_anchor_set(candidate))
            for candidate in candidates
        ),
        "status": "UNRESOLVED_NO_UNIQUE_PAIR_OR_TRIPLE",
    }


def _layout(candidate: Mapping[str, Any]) -> dict[str, Any]:
    child_roles = [event["role"] for event in candidate["events"] if event["role_kind"] == "CHILD"]
    branch = (
        "LISTED_UNLISTED_CLASSIFICATION"
        if any(role in {"LISTED", "UNLISTED"} for role in child_roles)
        else "ISSUER_CLASSIFICATION"
    )
    value_x_starts = sorted(
        {
            proposal["bbox"][0]
            for event in candidate["events"]
            for proposal in event["value_proposals"]
        }
    )
    subtotal_placements = []
    for parent in (event for event in candidate["events"] if event["role_kind"] == "PARENT"):
        later_children = [
            event
            for event in candidate["events"]
            if event["role_kind"] == "CHILD"
            and event["parent_role"] == parent["role"]
            and event["source_line_index"] > parent["source_line_index"]
        ]
        if parent["value_proposals"]:
            placement = "INLINE_PARENT_TOTAL_BEFORE_CHILDREN"
        elif later_children:
            placement = "PARENT_TOTAL_MAY_FOLLOW_CHILDREN"
        else:
            placement = "NO_EXPLICIT_PARENT_TOTAL_OBSERVED"
        subtotal_placements.append({"parent_role": parent["role"], "placement": placement})
    modes = [f"{branch}_ROWS_X_PERIOD_COLUMNS"]
    if candidate["percentage_headers"]:
        modes.append("AUXILIARY_PERCENTAGE_COLUMNS_PRESENT_NOT_MONEY")
    return {
        "branch_variant": branch,
        "meaningful_axes": {
            "money_column_x_starts": value_x_starts,
            "percentage_header_count": len(candidate["percentage_headers"]),
            "percentage_values_are_non_money_auxiliary": True,
            "period_header_count": len(candidate["period_headers"]),
            "unit_header_count": len(candidate["unit_headers"]),
        },
        "modes": modes,
        "parent_subtotal_placements": subtotal_placements,
        "primary_mode": modes[0],
        "row_order_preserved_from_pdf": True,
    }


def _build(pages: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    candidates = _candidate_pages(pages)
    complete = [
        candidate
        for candidate in candidates
        if _REQUIRED_PARENT_ROLES.issubset(candidate["parent_roles_in_pdf_order"])
    ]
    regions = []
    for ordinal, candidate in enumerate(complete, 1):
        last_event = candidate["events"][-1]
        net_rows = [
            row
            for row in candidate["unlabeled_numeric_rows"]
            if row["y_center"] > (last_event["bbox"][1] + last_event["bbox"][3]) / 2
        ]
        end_role = "NET" if net_rows else last_event["role"]
        end_line_index = (
            max(net_rows[-1]["source_line_indices"])
            if net_rows
            else last_event["source_line_index"]
        )
        material = {
            "cluster_boundary": {
                "first_item_role": "TRADING_SECURITIES_OWNER",
                "first_page_sequence": candidate["page_sequence"],
                "first_source_line_index": candidate["owner"]["source_line_index"],
                "last_item_role": end_role,
                "last_page_sequence": candidate["page_sequence"],
                "last_source_line_index": end_line_index,
                "selection_rule": (
                    "OWNER_THEN_REQUIRED_DEBT_EQUITY_PROVISION_PARENTS_THROUGH_LAST_"
                    "NET_OR_PROVISION_ITEM_BEFORE_DISTINCT_NEXT_FAMILY"
                ),
            },
            "events": canonical_clone_v1(candidate["events"]),
            "layout": _layout(candidate),
            "minimal_anchor": _minimal_anchor(candidate, candidates),
            "owner": canonical_clone_v1(candidate["owner"]),
            "page_sequence": candidate["page_sequence"],
            "parent_roles_in_pdf_order": list(candidate["parent_roles_in_pdf_order"]),
            "period_headers": canonical_clone_v1(candidate["period_headers"]),
            "region_ordinal": ordinal,
            "unit_headers": canonical_clone_v1(candidate["unit_headers"]),
            "unlabeled_numeric_rows": canonical_clone_v1(candidate["unlabeled_numeric_rows"]),
        }
        regions.append(
            {**material, "region_id": "tsvgv1:region:" + canonical_json_sha256_v1(material)}
        )
    near_regions = _negative_regions(pages)
    for _ordinal, candidate in enumerate(
        (item for item in candidates if item not in complete), len(near_regions) + 1
    ):
        material = {
            "negative_family": "INCOMPLETE_TRADING_SECURITIES_PARENT_SET",
            "owner_source_line_index": candidate["owner"]["source_line_index"],
            "owner_vietocr_text": candidate["owner"]["vietocr_text"],
            "page_sequence": candidate["page_sequence"],
            "status": "NEAR_REGION_INCOMPLETE_REQUIRED_PARENT_SET",
        }
        near_regions.append(
            {**material, "near_region_id": "tsvgv1:near:" + canonical_json_sha256_v1(material)}
        )
    unique = len(regions) == 1
    status = (
        "ACCEPTED_UNIQUE_VARIANT_GRAPH"
        if unique
        else (
            "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
            if len(regions) > 1
            else "UNRESOLVED_NO_COMPLETE_REGION"
        )
    )
    metrics = {
        "complete_trading_securities_region_count": len(regions),
        "document_page_count": len(pages),
        "near_region_count": len(near_regions),
    }
    uniqueness = {
        "complete_region_count": len(regions),
        "status": "UNIQUE_FULL_MATCH" if unique else "UNRESOLVED_NOT_UNIQUE",
    }
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "metrics": metrics,
        "near_regions": near_regions,
        "regions": regions,
        "safety": canonical_clone_v1(_SAFETY),
        "status": status,
        "uniqueness": uniqueness,
    }
    return {**material, "result_id": "tsvgv1:result:" + canonical_json_sha256_v1(material)}


def _build_generalized(pages: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    candidates = _candidate_pages(pages, generalized=True, stop_at_next_owner=True)
    structurally_complete = [
        candidate for candidate in candidates if _generalized_complete(candidate)
    ]
    complete, suppressed = _suppress_supplemental_views(structurally_complete)
    regions = []
    for ordinal, candidate in enumerate(complete, 1):
        last_event = candidate["events"][-1]
        trailing_rows = [
            row
            for row in candidate["unlabeled_numeric_rows"]
            if row["y_center"] > (last_event["bbox"][1] + last_event["bbox"][3]) / 2
        ]
        has_provision = "PROVISION" in candidate["parent_roles_in_pdf_order"]
        end_role = (
            "NET"
            if trailing_rows and has_provision
            else "TRAILING_FAMILY_TOTAL"
            if trailing_rows
            else last_event["role"]
        )
        end_line_index = (
            max(trailing_rows[-1]["source_line_indices"])
            if trailing_rows
            else last_event["source_line_index"]
        )
        material = {
            "cluster_boundary": {
                "first_item_role": "TRADING_SECURITIES_OWNER",
                "first_page_sequence": candidate["page_sequence"],
                "first_source_line_index": candidate["owner"]["source_line_index"],
                "last_item_role": end_role,
                "last_page_sequence": candidate["page_sequence"],
                "last_source_line_index": end_line_index,
                "selection_rule": (
                    "OWNER_THEN_ONE_OR_MORE_ASSET_PARENTS_WITH_CHILD_PERIOD_UNIT_"
                    "AND_VISIBLE_TOTAL_THROUGH_LAST_FAMILY_ITEM_BEFORE_NEXT_OWNER_"
                    "OR_DISTINCT_FAMILY"
                ),
            },
            "events": canonical_clone_v1(candidate["events"]),
            "layout": _layout(candidate),
            "minimal_anchor": _generalized_minimal_anchor(candidate, candidates),
            "owner": canonical_clone_v1(candidate["owner"]),
            "page_sequence": candidate["page_sequence"],
            "parent_roles_in_pdf_order": list(candidate["parent_roles_in_pdf_order"]),
            "period_headers": canonical_clone_v1(candidate["period_headers"]),
            "region_ordinal": ordinal,
            "unit_headers": canonical_clone_v1(candidate["unit_headers"]),
            "unlabeled_numeric_rows": canonical_clone_v1(candidate["unlabeled_numeric_rows"]),
            "view_kind": _view_kind(candidate),
        }
        regions.append(
            {**material, "region_id": "tsvgv2:region:" + canonical_json_sha256_v1(material)}
        )
    near_regions = _negative_regions(pages)
    for candidate in suppressed:
        material = {
            "negative_family": "ALTERNATE_NONADDITIVE_TRADING_VIEW",
            "owner_source_line_index": candidate["owner"]["source_line_index"],
            "owner_vietocr_text": candidate["owner"]["vietocr_text"],
            "page_sequence": candidate["page_sequence"],
            "status": "EXCLUDED_SUPPLEMENTAL_TRADING_VIEW",
        }
        near_regions.append(
            {**material, "near_region_id": "tsvgv2:near:" + canonical_json_sha256_v1(material)}
        )
    rejected = [
        candidate
        for candidate in candidates
        if candidate not in complete and candidate not in suppressed
    ]
    for candidate in rejected:
        material = {
            "negative_family": "INCOMPLETE_TRADING_SECURITIES_CORE",
            "owner_source_line_index": candidate["owner"]["source_line_index"],
            "owner_vietocr_text": candidate["owner"]["vietocr_text"],
            "page_sequence": candidate["page_sequence"],
            "status": "NEAR_REGION_INCOMPLETE_REQUIRED_CORE",
        }
        near_regions.append(
            {**material, "near_region_id": "tsvgv2:near:" + canonical_json_sha256_v1(material)}
        )
    unique = len(regions) == 1
    status = (
        "ACCEPTED_UNIQUE_VARIANT_GRAPH"
        if unique
        else (
            "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
            if len(regions) > 1
            else "UNRESOLVED_NO_COMPLETE_REGION"
        )
    )
    material = {
        "claim_boundary": GENERALIZED_CLAIM_BOUNDARY,
        "family_id": FAMILY_ID,
        "format_version": GENERALIZED_FORMAT_VERSION,
        "metrics": {
            "complete_trading_securities_region_count": len(regions),
            "document_page_count": len(pages),
            "near_region_count": len(near_regions),
        },
        "near_regions": near_regions,
        "regions": regions,
        "safety": canonical_clone_v1(_GENERALIZED_SAFETY),
        "status": status,
        "uniqueness": {
            "complete_region_count": len(regions),
            "status": "UNIQUE_FULL_MATCH" if unique else "UNRESOLVED_NOT_UNIQUE",
        },
    }
    return {**material, "result_id": "tsvgv2:result:" + canonical_json_sha256_v1(material)}


def _validate_shape(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("trading-securities result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["regions"]) is not list
        or type(value["near_regions"]) is not list
    ):
        raise _error("trading-securities result identity or authority drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "tsvgv1:result:" + canonical_json_sha256_v1(material):
        raise _error("trading-securities result identity drifted")
    return canonical_clone_v1(value)


def _validate_generalized_shape(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("generalized trading-securities result fields drifted")
    if (
        value["format_version"] != GENERALIZED_FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != GENERALIZED_CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _GENERALIZED_SAFETY)
        or type(value["regions"]) is not list
        or type(value["near_regions"]) is not list
    ):
        raise _error("generalized trading-securities result identity or authority drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "tsvgv2:result:" + canonical_json_sha256_v1(material):
        raise _error("generalized trading-securities result identity drifted")
    return canonical_clone_v1(value)


def build_trading_securities_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
    """Scan one complete PDF with the generic trading-securities graph."""

    return _validate_shape(_build(_pages(pages)))


def build_generalized_trading_securities_variant_graph_document_v2(
    pages: Any,
) -> dict[str, Any]:
    """Scan one PDF while allowing sparse core branches and supplemental views."""

    return _validate_generalized_shape(_build_generalized(_pages(pages)))


def validate_trading_securities_variant_graph_replay_v1(value: Any, pages: Any) -> dict[str, Any]:
    """Exact-rebuild a trading-securities graph from complete-PDF lines."""

    persisted = _validate_shape(value)
    rebuilt = build_trading_securities_variant_graph_document_v1(pages)
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("trading-securities graph does not replay exactly")
    return rebuilt


def validate_generalized_trading_securities_variant_graph_replay_v2(
    value: Any, pages: Any
) -> dict[str, Any]:
    """Exact-rebuild the generalized graph from complete-PDF lines."""

    persisted = _validate_generalized_shape(value)
    rebuilt = build_generalized_trading_securities_variant_graph_document_v2(pages)
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("generalized trading-securities graph does not replay exactly")
    return rebuilt
