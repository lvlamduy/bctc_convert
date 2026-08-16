"""Bank-blind variable graph for cash and precious-metals note clusters.

The matcher scans one complete PDF.  It requires a short cash/gold owner,
followed by VND cash and foreign-currency cash rows.  Monetary gold and the
other live-schema children are optional.  The cluster ends at the first
geometry-bound total before the next note family.  Period and unit columns are
part of the structural decision; a balance-sheet total, cash-flow disclosure,
accounting-policy paragraph, or financial-risk table is only a near region.

Fresh VietOCR text is used only to locate semantic anchors.  Geometry, source
order, period/unit axes and visible numeric cells are retained for independent
pixel and accounting verification.  Bank, file, note and page identities are
never matcher inputs.
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

try:
    from scripts.experiments.adaptive_accounting_table_geometry_v1 import (
        cluster_numeric_rows_v1,
        median_text_height_v1,
    )
except ModuleNotFoundError:  # Direct execution puts scripts/experiments on sys.path.
    from adaptive_accounting_table_geometry_v1 import (  # type: ignore[no-redef]
        cluster_numeric_rows_v1,
        median_text_height_v1,
    )

__all__ = [
    "FORMAT_VERSION",
    "CashPreciousMetalsVariantGraphV1Error",
    "build_cash_precious_metals_variant_graph_document_v1",
    "validate_cash_precious_metals_variant_graph_replay_v1",
]


FORMAT_VERSION = "CASH_PRECIOUS_METALS_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "CASH_PRECIOUS_METALS"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_CASH_PRECIOUS_METALS_OWNER_CHILD_"
    "FIRST_LAST_CLUSTER_BOUNDARY_LAYOUT_PERIOD_UNIT_TOTAL_STRUCTURE_PROPOSAL_"
    "ONLY_NO_NUMERIC_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)

_REQUIRED_CHILD_ROLES = frozenset({"CASH_VND", "CASH_FOREIGN"})
_CHILD_ROLE_ORDER = (
    "CASH_VND",
    "CASH_FOREIGN",
    "FOREIGN_CURRENCY_VALUABLE_DOCUMENT",
    "MONETARY_GOLD",
    "NONMONETARY_GOLD",
    "OTHER_PRECIOUS_METALS_GEMS",
    "OTHER",
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


class CashPreciousMetalsVariantGraphV1Error(ValueError):
    """The cash/precious-metals graph input or replay drifted."""


def _error(message: str) -> CashPreciousMetalsVariantGraphV1Error:
    return CashPreciousMetalsVariantGraphV1Error(message)


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
        raise _error("cash/precious-metals matcher requires one complete nonempty PDF")
    pages: list[dict[str, Any]] = []
    prior_page = 0
    for raw_page in value:
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_sequence",
            "primary_numeric_authority",
        }:
            raise _error("cash/precious-metals matcher page fields drifted")
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
                raise _error("cash/precious-metals line fields drifted")
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
    words = text.split()
    if "tien mat" not in text or not any(
        term in text for term in ("vang", "kim loai quy", "da quy")
    ):
        return False
    forbidden = (
        "tuong duong tien",
        "bao gom",
        "rui ro",
        "gia tri ghi so",
        "phan loai tai san",
        "luu chuyen tien",
        "tai quy",
        "co tuc",
    )
    return len(words) <= 11 and not any(term in text for term in forbidden)


def _negative_family(text: str) -> str | None:
    if "tien va cac khoan tuong duong tien" in text:
        return "DISTINCT_CASH_EQUIVALENTS_OR_CASH_FLOW_FAMILY"
    if "phan loai tai san tai chinh" in text or "gia tri ghi so" in text:
        return "DISTINCT_FINANCIAL_INSTRUMENT_CLASSIFICATION_FAMILY"
    if "rui ro" in text and any(term in text for term in ("ngoai te", "thanh khoan")):
        return "DISTINCT_FINANCIAL_RISK_FAMILY"
    return None


def _section_break(text: str) -> bool:
    return any(
        term in text
        for term in (
            "tien gui tai nhnn",
            "tien gui tai ngan hang nha nuoc",
            "tien gui va cho vay cac tctd",
            "chung khoan kinh doanh",
        )
    )


def _child_role(text: str) -> str | None:
    if "tien mat bang" in text and (
        "vnd" in text or "tien dong" in text or "dong viet nam" in text
    ):
        return "CASH_VND"
    if "tien mat bang" in text and "ngoai te" in text:
        return "CASH_FOREIGN"
    if "chung tu co gia" in text and "ngoai te" in text:
        return "FOREIGN_CURRENCY_VALUABLE_DOCUMENT"
    if "vang phi tien te" in text:
        return "NONMONETARY_GOLD"
    if "vang tien te" in text or text == "vang":
        return "MONETARY_GOLD"
    if "kim loai quy" in text or "da quy khac" in text:
        return "OTHER_PRECIOUS_METALS_GEMS"
    if text == "khac":
        return "OTHER"
    return None


def _token(line: Mapping[str, Any]) -> str:
    return line["vietocr_text"].strip().replace(" ", "")


def _is_money(line: Mapping[str, Any]) -> bool:
    token = _token(line)
    return _NUMBER.fullmatch(token) is not None or _DASH.fullmatch(token) is not None


def _value_proposals(
    lines: Sequence[Mapping[str, Any]], label: Mapping[str, Any]
) -> list[dict[str, Any]]:
    top, bottom = label["bbox"][1], label["bbox"][3]
    width = max((item["bbox"][2] for item in lines), default=1)
    values: list[dict[str, Any]] = []
    for item in lines:
        center_y = (item["bbox"][1] + item["bbox"][3]) / 2
        if (
            item["bbox"][0] > width * 0.47
            and top - 15 <= center_y <= bottom + 18
            and _is_money(item)
        ):
            values.append(
                {
                    "bbox": list(item["bbox"]),
                    "source_line_index": item["source_line_index"],
                    "source_text": item["source_text"],
                    "vietocr_text": item["vietocr_text"],
                }
            )
    return sorted(values, key=lambda item: (item["bbox"][0], item["source_line_index"]))


def _axis_groups(
    lines: Sequence[Mapping[str, Any]], start: int, stop: int, *, kind: str
) -> list[dict[str, Any]]:
    width = max((item["bbox"][2] for item in lines), default=1)
    candidates: list[Mapping[str, Any]] = []
    for item in lines:
        index = item["source_line_index"]
        text = item["normalized_text"]
        if not start < index < stop or item["bbox"][0] <= width * 0.45:
            continue
        if kind == "PERIOD":
            matched = (
                re.search(r"(?:30|31)[ /.-](?:03|3|06|6|12)[ /.-]20[0-9]{2}", text) is not None
                or "ngay 31 thang" in text
                or re.fullmatch(r"nam 20[0-9]{2}", text) is not None
                or text in {"so cuoi nam", "so dau nam"}
            )
        else:
            matched = "trieu dong" in text or "trieu vnd" in text
        if matched:
            candidates.append(item)
    groups: list[list[Mapping[str, Any]]] = []
    for item in sorted(candidates, key=lambda value: value["bbox"][0]):
        center = (item["bbox"][0] + item["bbox"][2]) / 2
        for group in groups:
            prior = sum((x["bbox"][0] + x["bbox"][2]) / 2 for x in group) / len(group)
            if abs(center - prior) <= max(55, width * 0.055):
                group.append(item)
                break
        else:
            groups.append([item])
    return [
        {
            "bbox_union": [
                min(item["bbox"][0] for item in group),
                min(item["bbox"][1] for item in group),
                max(item["bbox"][2] for item in group),
                max(item["bbox"][3] for item in group),
            ],
            "source_line_indices": [item["source_line_index"] for item in group],
            "vietocr_text": [item["vietocr_text"] for item in group],
        }
        for group in groups
    ]


def _total_after(
    lines: Sequence[Mapping[str, Any]], child: Mapping[str, Any]
) -> dict[str, Any] | None:
    width = max((item["bbox"][2] for item in lines), default=1)
    scale = median_text_height_v1(lines)
    child_center = (child["bbox"][1] + child["bbox"][3]) / 2
    rows = cluster_numeric_rows_v1(
        lines,
        is_numeric=_is_money,
        start_index=child["source_line_index"],
        stop_index=min(
            child["source_line_index"] + 9,
            max(item["source_line_index"] for item in lines) + 1,
        ),
        page_width=width,
    )
    for row in rows:
        center = sum((item["bbox"][1] + item["bbox"][3]) / 2 for item in row) / len(row)
        if center <= child_center + scale * 0.45:
            continue
        if len(row) >= 2:
            return {
                "role": "TOTAL",
                "role_kind": "TOTAL",
                "source_line_index": min(item["source_line_index"] for item in row),
                "value_proposals": [
                    {
                        "bbox": list(item["bbox"]),
                        "source_line_index": item["source_line_index"],
                        "source_text": item["source_text"],
                        "vietocr_text": item["vietocr_text"],
                    }
                    for item in row
                ],
            }
    return None


def _minimal_anchor(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    roles = ["PARENT:CASH_PRECIOUS_METALS"] + [
        f"CHILD:{event['role']}" for event in events if event["role_kind"] == "CHILD"
    ]
    parent_pairs = [
        pair for pair in itertools.combinations(roles, 2) if pair[0].startswith("PARENT:")
    ]
    child_pairs = [
        pair
        for pair in itertools.combinations(roles, 2)
        if pair[0].startswith("CHILD:") and pair[1].startswith("CHILD:")
    ]
    tested = parent_pairs + child_pairs
    if not tested:
        raise _error("complete cash/precious-metals graph has no anchor pair")
    return {
        "combination_size": 2,
        "pair_search_order": "ALL_PARENT_CHILD_PAIRS_THEN_ALL_CHILD_CHILD_PAIRS",
        "selected_roles": list(tested[0]),
        "tested_pair_count": len(tested),
    }


def _candidate(
    page: Mapping[str, Any], owner: Mapping[str, Any]
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    lines = page["lines"]
    owner_index = owner["source_line_index"]
    window: list[Mapping[str, Any]] = []
    break_reason = "END_OF_PAGE"
    for item in lines:
        if item["source_line_index"] <= owner_index:
            continue
        if item["source_line_index"] > owner_index + 32:
            break_reason = "MAXIMUM_CLUSTER_SPAN"
            break
        if _section_break(item["normalized_text"]):
            break_reason = "DISTINCT_NEXT_NOTE_FAMILY"
            break
        window.append(item)
    child_events: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in window:
        role = _child_role(item["normalized_text"])
        if role is None or role in seen:
            continue
        values = _value_proposals(lines, item)
        child_events.append(
            {
                "bbox": list(item["bbox"]),
                "role": role,
                "role_kind": "CHILD",
                "source_line_index": item["source_line_index"],
                "value_proposals": values,
                "vietocr_text": item["vietocr_text"],
            }
        )
        seen.add(role)
    present = {event["role"] for event in child_events}
    missing = sorted(_REQUIRED_CHILD_ROLES - present)
    last_child = max(child_events, key=lambda item: item["source_line_index"], default=None)
    total = _total_after(lines, last_child) if last_child is not None else None
    first_child_index = min(
        (event["source_line_index"] for event in child_events), default=owner_index + 1
    )
    periods = _axis_groups(lines, owner_index, first_child_index, kind="PERIOD")
    units = _axis_groups(lines, owner_index, first_child_index, kind="UNIT")
    reasons = []
    if missing:
        reasons.append("MISSING_REQUIRED_CHILDREN:" + ",".join(missing))
    if any(
        len(event["value_proposals"]) < 2
        for event in child_events
        if event["role"] in _REQUIRED_CHILD_ROLES
    ):
        reasons.append("REQUIRED_CHILD_HAS_FEWER_THAN_TWO_MONETARY_VALUES")
    if len(periods) < 2:
        reasons.append("FEWER_THAN_TWO_PERIOD_AXES")
    if len(units) < 1:
        reasons.append("NO_MONETARY_UNIT_AXIS")
    if total is None or len(total["value_proposals"]) < 2:
        reasons.append("NO_TWO_AXIS_TRAILING_TOTAL")
    near = {
        "break_reason": break_reason,
        "child_roles": [event["role"] for event in child_events],
        "owner_source_line_index": owner_index,
        "owner_vietocr_text": owner["vietocr_text"],
        "page_sequence": page["page_sequence"],
        "reasons": reasons,
    }
    if reasons:
        return None, near
    events = sorted(child_events, key=lambda item: item["source_line_index"])
    assert last_child is not None and total is not None
    end_index = max(value["source_line_index"] for value in total["value_proposals"])
    variant = (
        "VND_FOREIGN_AND_MONETARY_GOLD"
        if "MONETARY_GOLD" in present
        else "VND_FOREIGN_WITH_OPTIONAL_OTHER_CHILDREN"
    )
    material = {
        "cluster_boundary": {
            "first_item_role": "CASH_PRECIOUS_METALS_OWNER",
            "first_page_sequence": page["page_sequence"],
            "first_source_line_index": owner_index,
            "last_item_role": "TOTAL",
            "last_page_sequence": page["page_sequence"],
            "last_source_line_index": end_index,
            "selection_rule": (
                "SHORT_OWNER_THEN_REQUIRED_VND_AND_FOREIGN_CHILDREN_THROUGH_FIRST_"
                "TWO_AXIS_TOTAL_BEFORE_DISTINCT_NEXT_NOTE_FAMILY"
            ),
        },
        "events": events + [total],
        "layout": {
            "meaningful_axes": {
                "period_axes": periods,
                "period_header_count": len(periods),
                "unit_axes": units,
                "unit_header_count": len(units),
            },
            "orientation": "ROW_LABELS_BY_PERIOD_COLUMNS",
            "variant": variant,
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
        "region_id": "cpmvgv1:region:" + canonical_json_sha256_v1(material),
    }, near


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("cash/precious-metals result fields drifted")
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
        raise _error("cash/precious-metals result identity or shape drifted")
    count = len(value["regions"])
    expected_status = (
        "ACCEPTED_UNIQUE_VARIANT_GRAPH"
        if count == 1
        else "UNRESOLVED_NO_COMPLETE_REGION"
        if count == 0
        else "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
    )
    expected_uniqueness = {
        "complete_region_count": count,
        "status": "UNIQUE_FULL_MATCH"
        if count == 1
        else "NO_FULL_MATCH"
        if count == 0
        else "MULTIPLE_FULL_MATCHES",
    }
    expected_metrics = {
        "complete_cash_precious_metals_region_count": count,
        "near_region_count": len(value["near_regions"]),
    }
    if (
        value["status"] != expected_status
        or not same_typed_json_v1(value["uniqueness"], expected_uniqueness)
        or not same_typed_json_v1(value["metrics"], expected_metrics)
    ):
        raise _error("cash/precious-metals result status or metrics drifted")
    for region in value["regions"]:
        if type(region) is not dict or type(region.get("region_id")) is not str:
            raise _error("cash/precious-metals region shape drifted")
        material = canonical_clone_v1(region)
        identity = material.pop("region_id")
        if identity != "cpmvgv1:region:" + canonical_json_sha256_v1(material):
            raise _error("cash/precious-metals region identity drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "cpmvgv1:result:" + canonical_json_sha256_v1(material):
        raise _error("cash/precious-metals result identity drifted")
    return canonical_clone_v1(value)


def build_cash_precious_metals_variant_graph_document_v1(
    document_pages: Any,
) -> dict[str, Any]:
    """Enumerate every complete/near cash and precious-metals region in one PDF."""

    pages = _pages(document_pages)
    regions: list[dict[str, Any]] = []
    near: list[dict[str, Any]] = []
    for page in pages:
        for line in page["lines"]:
            negative = _negative_family(line["normalized_text"])
            if negative is not None:
                near.append(
                    {
                        "break_reason": negative,
                        "child_roles": [],
                        "owner_source_line_index": line["source_line_index"],
                        "owner_vietocr_text": line["vietocr_text"],
                        "page_sequence": page["page_sequence"],
                        "reasons": [negative],
                    }
                )
            if not _owner(line["normalized_text"]):
                continue
            region, near_region = _candidate(page, line)
            near.append(near_region)
            if region is not None:
                regions.append(region)
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "metrics": {
            "complete_cash_precious_metals_region_count": len(regions),
            "near_region_count": len(near),
        },
        "near_regions": near,
        "regions": regions,
        "safety": canonical_clone_v1(_SAFETY),
        "status": (
            "ACCEPTED_UNIQUE_VARIANT_GRAPH"
            if len(regions) == 1
            else "UNRESOLVED_NO_COMPLETE_REGION"
            if not regions
            else "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
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
    return _validate_result(
        {**material, "result_id": "cpmvgv1:result:" + canonical_json_sha256_v1(material)}
    )


def validate_cash_precious_metals_variant_graph_replay_v1(
    value: Any, document_pages: Any
) -> dict[str, Any]:
    """Exact-rebuild the matcher result from the complete PDF line axis."""

    persisted = _validate_result(value)
    expected = build_cash_precious_metals_variant_graph_document_v1(document_pages)
    if not same_typed_json_v1(persisted, expected):
        raise _error("cash/precious-metals graph does not replay exactly")
    return persisted
