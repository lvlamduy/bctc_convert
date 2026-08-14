"""Bank-blind variable graph for customer-deposit note clusters.

The graph locates a customer-deposit owner and the smallest complete cluster of
deposit-type parents.  It admits either row-oriented parent/child presentation
with period columns or period-stacked blocks with VND/foreign/total columns.
Savings rows may be standalone additive parents or nested non-additive detail.
Bank code, filename, note number and page number are never matcher inputs.

Fresh VietOCR text is semantic-anchor evidence only.  Values and geometry are
retained as proposals for a later independent pixel/accounting verifier.
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
    "CustomerDepositVariantGraphV1Error",
    "build_customer_deposit_variant_graph_document_v1",
    "validate_customer_deposit_variant_graph_replay_v1",
]


FORMAT_VERSION = "CUSTOMER_DEPOSIT_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "CUSTOMER_DEPOSIT_CLASSIFICATION"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_CUSTOMER_DEPOSIT_OWNER_PARENT_CHILD_"
    "BOUNDARY_PERIOD_CURRENCY_AND_TOTAL_STRUCTURE_PROPOSAL_ONLY_NO_NUMERIC_SCHEMA_"
    "MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)

_REQUIRED_PARENT_ROLES = frozenset({"NO_TERM", "TERM", "DEDICATED", "ESCROW"})
_PARENT_ROLES = (
    "NO_TERM",
    "TERM",
    "SAVINGS_NO_TERM",
    "SAVINGS_TERM",
    "DEDICATED",
    "ESCROW",
)
_PARENT_ANCHOR = "PARENT:CUSTOMER_DEPOSIT"
_NUMBER = re.compile(r"^\(?-?[0-9]+(?:[.,][0-9]+)*\)?$")
_DASH = re.compile(r"^[\-–—]+$")

_SAFETY = {
    "bank_filename_note_or_page_used_for_inference": False,
    "complete_pdf_region_enumeration_required": True,
    "currency_child_requires_preceding_or_explicit_parent": True,
    "fresh_vietocr_transformer_text_required": True,
    "mapping_authority": False,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "pair_combinations_exhausted_before_triples": True,
    "parent_order_fixed": False,
    "parent_precedes_child_required": True,
    "persisted_result_self_authenticating": False,
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


class CustomerDepositVariantGraphV1Error(ValueError):
    """The customer-deposit graph input or deterministic replay drifted."""


def _error(message: str) -> CustomerDepositVariantGraphV1Error:
    return CustomerDepositVariantGraphV1Error(message)


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
        raise _error("customer-deposit matcher requires one complete nonempty PDF")
    pages: list[dict[str, Any]] = []
    prior_page = 0
    for raw_page in value:
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_sequence",
            "primary_numeric_authority",
        }:
            raise _error("customer-deposit matcher page fields drifted")
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
                raise _error("customer-deposit line fields drifted")
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
    if "tien gui cua khach hang" not in text:
        return False
    forbidden = (
        "tang tien gui",
        "giam tien gui",
        "chi nop phi",
        "bao hiem",
        "xac dinh",
        "rui ro thanh khoan",
        "lai suat",
        "bao gom so du",
    )
    return len(text.split()) <= 13 and not any(term in text for term in forbidden)


def _continuation(text: str) -> bool:
    return _owner(text) and "tiep theo" in text


def _parent_role(text: str) -> str | None:
    if "bang " in text:
        return None
    if "tien gui tiet kiem khong ky han" in text:
        return "SAVINGS_NO_TERM"
    if "tien gui tiet kiem co ky han" in text:
        return "SAVINGS_TERM"
    if (
        "tien gui khong ky han" in text or "tien vang gui khong ky han" in text
    ) and "tiet kiem" not in text:
        return "NO_TERM"
    if (
        "tien gui co ky han" in text or "tien vang gui co ky han" in text
    ) and "tiet kiem" not in text:
        return "TERM"
    if "tien gui von chuyen dung" in text:
        return "DEDICATED"
    if "tien gui ky quy" in text or "tien ky quy" in text:
        return "ESCROW"
    return None


def _explicit_child_parent(text: str) -> str | None:
    if "tiet kiem khong ky han" in text:
        return "SAVINGS_NO_TERM"
    if "tiet kiem co ky han" in text:
        return "SAVINGS_TERM"
    if "khong ky han" in text:
        return "NO_TERM"
    if "co ky han" in text:
        return "TERM"
    if "von chuyen dung" in text:
        return "DEDICATED"
    if "ky quy" in text:
        return "ESCROW"
    return None


def _currency_role(text: str) -> str | None:
    if "bang" not in text:
        return None
    if "ngoai te" in text or "vang ngoai te" in text:
        return "FOREIGN"
    if "vnd" in text or "tien dong" in text:
        return "VND"
    return None


def _value_proposals(
    lines: Sequence[Mapping[str, Any]], line: Mapping[str, Any]
) -> list[dict[str, Any]]:
    top, bottom = line["bbox"][1], line["bbox"][3]
    width = max((item["bbox"][2] for item in lines), default=1)
    result = []
    for item in lines:
        token = item["vietocr_text"].strip().replace(" ", "")
        center_y = (item["bbox"][1] + item["bbox"][3]) / 2
        if (
            item["bbox"][0] > width * 0.45
            and top - 15 <= center_y <= bottom + 18
            and (_NUMBER.fullmatch(token) or _DASH.fullmatch(token))
        ):
            result.append(
                {
                    "bbox": list(item["bbox"]),
                    "raw_text": item["vietocr_text"],
                    "source_line_index": item["source_line_index"],
                }
            )
    return sorted(result, key=lambda item: (item["bbox"][0], item["source_line_index"]))


def _events(
    lines: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    parent_events: list[dict[str, Any]] = []
    child_events: list[dict[str, Any]] = []
    active_parent: str | None = None
    for line in lines:
        text = line["normalized_text"]
        role = _parent_role(text)
        if role is not None:
            active_parent = role
            parent_events.append(
                {
                    "bbox": list(line["bbox"]),
                    "normalized_label": text,
                    "parent_role": role,
                    "source_line_index": line["source_line_index"],
                    "value_proposals": _value_proposals(lines, line),
                    "vietocr_label": line["vietocr_text"],
                }
            )
            continue
        currency = _currency_role(text)
        if currency is None:
            continue
        explicit_parent = _explicit_child_parent(text)
        parent = explicit_parent or active_parent
        if parent is None:
            continue
        child_events.append(
            {
                "bbox": list(line["bbox"]),
                "currency_role": currency,
                "normalized_label": text,
                "parent_role": parent,
                "source_line_index": line["source_line_index"],
                "value_proposals": _value_proposals(lines, line),
                "vietocr_label": line["vietocr_text"],
            }
        )
    return parent_events, child_events


def _period_headers(lines: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for line in lines:
        text = line["normalized_text"]
        if (
            re.search(r"(?:30|31)[ /.-](?:0?[136]|12)[ /.-]20(?:25|26)", text)
            or re.search(r"(?:30|31) thang (?:0?[136]|12) nam 20(?:25|26)", text)
            or "so cuoi ky" in text
            or "so dau ky" in text
            or ("ngay 31 thang" in text and "nam 202" in text)
        ):
            result.append(
                {
                    "bbox": list(line["bbox"]),
                    "normalized_text": text,
                    "source_line_index": line["source_line_index"],
                    "vietocr_text": line["vietocr_text"],
                }
            )
    return result


def _currency_headers(lines: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for line in lines:
        text = line["normalized_text"]
        role = None
        if "bang tien dong" in text or "bang vnd" in text:
            role = "VND"
        elif "bang ngoai te" in text:
            role = "FOREIGN"
        elif "tong cong" in text:
            role = "TOTAL"
        if role is not None:
            result.append(
                {
                    "axis_role": role,
                    "bbox": list(line["bbox"]),
                    "source_line_index": line["source_line_index"],
                    "vietocr_text": line["vietocr_text"],
                }
            )
    return result


def _panels(parent_events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    panels: list[list[Mapping[str, Any]]] = []
    current: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    for event in parent_events:
        role = event["parent_role"]
        if role in seen and _REQUIRED_PARENT_ROLES.issubset(seen):
            panels.append(current)
            current = []
            seen = set()
        current.append(event)
        seen.add(role)
    if current:
        panels.append(current)
    result = []
    for ordinal, panel in enumerate(panels, 1):
        roles = {event["parent_role"] for event in panel}
        result.append(
            {
                "boundary": {
                    "first_parent_role": panel[0]["parent_role"],
                    "first_source_line_index": panel[0]["source_line_index"],
                    "last_parent_role": panel[-1]["parent_role"],
                    "last_source_line_index": panel[-1]["source_line_index"],
                },
                "complete": _REQUIRED_PARENT_ROLES.issubset(roles),
                "panel_ordinal": ordinal,
                "parent_roles_in_pdf_order": [event["parent_role"] for event in panel],
                "parents": canonical_clone_v1(panel),
            }
        )
    return result


def _candidate_pages(pages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for page in pages:
        for position, line in enumerate(page["lines"]):
            if not _owner(line["normalized_text"]):
                continue
            region_lines = page["lines"][position:]
            parents, children = _events(region_lines)
            result.append(
                {
                    "children": children,
                    "continuation": _continuation(line["normalized_text"]),
                    "currency_headers": _currency_headers(region_lines),
                    "owner": {
                        "bbox": list(line["bbox"]),
                        "normalized_text": line["normalized_text"],
                        "source_line_index": line["source_line_index"],
                        "vietocr_text": line["vietocr_text"],
                    },
                    "page_sequence": page["page_sequence"],
                    "panels": _panels(parents),
                    "parent_events": parents,
                    "period_headers": _period_headers(region_lines),
                    "primary_numeric_authority": page["primary_numeric_authority"],
                }
            )
    return result


def _group_candidates(candidates: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for candidate in candidates:
        if (
            candidate["continuation"]
            and groups
            and candidate["page_sequence"] == groups[-1]["page_sequences"][-1] + 1
        ):
            groups[-1]["page_records"].append(canonical_clone_v1(candidate))
            groups[-1]["page_sequences"].append(candidate["page_sequence"])
        else:
            groups.append(
                {
                    "page_records": [canonical_clone_v1(candidate)],
                    "page_sequences": [candidate["page_sequence"]],
                }
            )
    for group in groups:
        complete_panels = [
            panel for page in group["page_records"] for panel in page["panels"] if panel["complete"]
        ]
        roles = {
            event["parent_role"]
            for page in group["page_records"]
            for event in page["parent_events"]
        }
        group["complete_panels"] = complete_panels
        group["complete"] = bool(complete_panels)
        group["parent_roles"] = sorted(roles, key=_PARENT_ROLES.index)
    return groups


def _anchor_set(group: Mapping[str, Any]) -> set[str]:
    return {_PARENT_ANCHOR, *(f"ROLE:{role}" for role in group["parent_roles"])}


def _presentation_layout(group: Mapping[str, Any]) -> dict[str, Any]:
    pages = group["page_records"]
    header_roles: list[str] = []
    value_column_x_starts: set[int] = set()
    child_count = 0
    for page in pages:
        for header in page["currency_headers"]:
            role = header["axis_role"]
            if role not in header_roles:
                header_roles.append(role)
        child_count += len(page["children"])
        for event in [*page["parent_events"], *page["children"]]:
            value_column_x_starts.update(
                proposal["bbox"][0] for proposal in event["value_proposals"]
            )
    period_header_count = sum(len(page["period_headers"]) for page in pages)
    complete_panel_count = len(group["complete_panels"])
    if complete_panel_count > 1 and {"VND", "FOREIGN", "TOTAL"}.issubset(header_roles):
        primary_mode = "PERIOD_STACKED_ROWS_X_CURRENCY_COLUMNS"
    elif child_count:
        primary_mode = "PARENT_CHILD_ROWS_X_PERIOD_COLUMNS"
    else:
        primary_mode = "PARENT_ROWS_X_PERIOD_COLUMNS"
    modes = [primary_mode]
    if len(group["page_sequences"]) > 1:
        modes.append("CROSS_PAGE_CONTINUATION")
    return {
        "axis_evidence": {
            "currency_child_count": child_count,
            "currency_header_roles_in_pdf_order": header_roles,
            "period_header_count": period_header_count,
            "value_column_x_starts": sorted(value_column_x_starts),
        },
        "modes": modes,
        "primary_mode": primary_mode,
        "row_order_preserved_from_pdf": True,
    }


def _minimal_anchor(
    selected: Mapping[str, Any], groups: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    selected_anchors = sorted(_anchor_set(selected))
    for size in (2, 3):
        for combination in itertools.combinations(selected_anchors, size):
            match_count = sum(set(combination).issubset(_anchor_set(group)) for group in groups)
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
            set(selected_anchors).issubset(_anchor_set(group)) for group in groups
        ),
        "status": "UNRESOLVED_NO_UNIQUE_PAIR_OR_TRIPLE",
    }


def _build(pages: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    groups = _group_candidates(_candidate_pages(pages))
    complete = [group for group in groups if group["complete"]]
    regions = []
    for ordinal, group in enumerate(complete, 1):
        pages_payload = canonical_clone_v1(group["page_records"])
        first_panel = group["complete_panels"][0]
        last_panel = group["complete_panels"][-1]
        material = {
            "cluster_boundary": {
                "first_page_sequence": group["page_sequences"][0],
                "first_parent_role": first_panel["boundary"]["first_parent_role"],
                "first_source_line_index": first_panel["boundary"]["first_source_line_index"],
                "last_page_sequence": group["page_sequences"][-1],
                "last_parent_role": last_panel["boundary"]["last_parent_role"],
                "last_source_line_index": last_panel["boundary"]["last_source_line_index"],
            },
            "complete_panel_count": len(group["complete_panels"]),
            "layout": _presentation_layout(group),
            "minimal_anchor": _minimal_anchor(group, groups),
            "page_records": pages_payload,
            "page_sequences": list(group["page_sequences"]),
            "parent_roles": list(group["parent_roles"]),
            "region_ordinal": ordinal,
        }
        regions.append(
            {
                **material,
                "region_id": "cdvgv1:region:" + canonical_json_sha256_v1(material),
            }
        )
    near_regions = []
    for ordinal, group in enumerate((item for item in groups if not item["complete"]), 1):
        material = {
            "page_sequences": list(group["page_sequences"]),
            "parent_roles": list(group["parent_roles"]),
            "region_ordinal": ordinal,
            "status": "NEAR_REGION_INCOMPLETE_REQUIRED_PARENT_SET",
        }
        near_regions.append(
            {
                **material,
                "near_region_id": "cdvgv1:near:" + canonical_json_sha256_v1(material),
            }
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
        "complete_customer_deposit_region_count": len(regions),
        "complete_panel_count": sum(region["complete_panel_count"] for region in regions),
        "continuation_region_count": sum(len(region["page_sequences"]) > 1 for region in regions),
        "near_region_count": len(near_regions),
        "page_count": len(pages),
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
    return {**material, "result_id": "cdvgv1:result:" + canonical_json_sha256_v1(material)}


def _validate_shape(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("customer-deposit result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["regions"]) is not list
        or type(value["near_regions"]) is not list
    ):
        raise _error("customer-deposit result identity or authority drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "cdvgv1:result:" + canonical_json_sha256_v1(material):
        raise _error("customer-deposit result identity drifted")
    return canonical_clone_v1(value)


def build_customer_deposit_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
    """Scan one complete PDF with the generic customer-deposit graph."""

    return _validate_shape(_build(_pages(pages)))


def validate_customer_deposit_variant_graph_replay_v1(value: Any, pages: Any) -> dict[str, Any]:
    """Exact-rebuild a customer-deposit graph from the complete PDF lines."""

    persisted = _validate_shape(value)
    rebuilt = build_customer_deposit_variant_graph_document_v1(pages)
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("customer-deposit graph does not replay exactly")
    return rebuilt
