"""Bank-blind variant graph for deposits at central banks.

The family is discovered with the shared accounting-variant engine.  The
outer note owner must precede a central-bank sub-parent and the VND/foreign
currency children.  Both child orders are allowed.  A family wrapper then
requires visible period/unit axes, row/column geometry and the first two-axis
total after the final family row.  Optional central-bank geography rows are
retained between the currency children and that total.  A reserve-ratio table
or the next note family is outside the cluster.

Fresh VietOCR text only proposes anchors.  Bank, filename, note number and
page identity are never matcher inputs and no numeric/schema/mapping authority
is granted here.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    build_accounting_variant_region_scan_v1,
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "CentralBankDepositsVariantGraphV1Error",
    "build_central_bank_deposits_variant_graph_document_v1",
    "validate_central_bank_deposits_variant_graph_replay_v1",
]


FORMAT_VERSION = "CENTRAL_BANK_DEPOSITS_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "CENTRAL_BANK_DEPOSITS"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_SHARED_VARIANT_ENGINE_FRESH_VIETOCR_CENTRAL_BANK_"
    "DEPOSIT_OWNER_PARENT_CHILD_FIRST_LAST_CLUSTER_BOUNDARY_LAYOUT_PERIOD_UNIT_"
    "TOTAL_STRUCTURE_PROPOSAL_ONLY_NO_NUMERIC_SCHEMA_MAPPING_EXPORT_AUTHORITY"
)
_NUMBER = re.compile(r"^\(?-?[0-9]+(?:[.,][0-9]+)*\)?$")
_DASH = re.compile(r"^[\-–—]+$")
_SAFETY = {
    "bank_filename_note_or_page_used_for_inference": False,
    "child_order_variants_are_family_level_not_bank_routed": True,
    "complete_pdf_region_enumeration_required": True,
    "fresh_vietocr_transformer_text_required": True,
    "mapping_authority": False,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "pair_combinations_exhausted_before_triples": True,
    "parent_precedes_children_required": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "reserve_ratio_auxiliary_table_inside_family_balance_cluster": False,
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


class CentralBankDepositsVariantGraphV1Error(ValueError):
    """The central-bank deposit graph input or replay drifted."""


def _error(message: str) -> CentralBankDepositsVariantGraphV1Error:
    return CentralBankDepositsVariantGraphV1Error(message)


def _family_spec(order: tuple[str, str]) -> dict[str, Any]:
    aliases = {
        "DEPOSIT_VND": ["Bằng VND", "Bằng tiền đồng"],
        "DEPOSIT_FOREIGN_CURRENCY": ["Bằng ngoại tệ"],
    }
    return {
        "branch_core_phrases": ["tiền gửi"],
        "branch_variants": [
            {"anchor_phrase": "tại NHNN", "variant_id": "AT_NHNN"},
            {
                "anchor_phrase": "tại Ngân hàng Nhà nước Việt Nam",
                "variant_id": "AT_STATE_BANK_VIETNAM",
            },
            {
                "anchor_phrase": "tại Ngân hàng Trung ương",
                "variant_id": "AT_CENTRAL_BANK",
            },
        ],
        "family_id": FAMILY_ID,
        "format_version": "ACCOUNTING_VARIANT_FAMILY_SPEC_V1",
        "limits": {
            "max_branch_to_last_child_line_span": 14,
            "max_child_gap": 9,
            "min_numeric_followers_per_child": 2,
        },
        "optional_intermediate_aliases": [],
        "ordered_children": [{"aliases": aliases[role], "role": role} for role in order],
        "owner_aliases": [
            "Tiền gửi tại NHNN",
            "Tiền gửi tại Ngân hàng Nhà nước Việt Nam",
            "Tiền gửi tại Ngân hàng Trung ương",
        ],
    }


_ORDER_SPECS = (
    (
        "VND_THEN_FOREIGN_CURRENCY",
        _family_spec(("DEPOSIT_VND", "DEPOSIT_FOREIGN_CURRENCY")),
    ),
    (
        "FOREIGN_CURRENCY_THEN_VND",
        _family_spec(("DEPOSIT_FOREIGN_CURRENCY", "DEPOSIT_VND")),
    ),
)


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
        raise _error("central-bank matcher requires one complete nonempty PDF")
    pages: list[dict[str, Any]] = []
    prior_page = 0
    for raw_page in value:
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_sequence",
            "primary_numeric_authority",
        }:
            raise _error("central-bank matcher page fields drifted")
        sequence = raw_page["page_sequence"]
        if type(sequence) is not int or sequence != prior_page + 1:
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
                raise _error("central-bank matcher line fields drifted")
            index = raw_line["source_line_index"]
            if type(index) is not int or index != prior_index + 1:
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
            prior_index = index
        pages.append(
            {
                "lines": lines,
                "page_sequence": sequence,
                "primary_numeric_authority": raw_page["primary_numeric_authority"],
            }
        )
        prior_page = sequence
    return pages


def _engine_pages(pages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "lines": [
                {
                    "source_line_index": line["source_line_index"],
                    "vietocr_text": line["vietocr_text"],
                }
                for line in page["lines"]
            ],
            "page_sequence": page["page_sequence"],
        }
        for page in pages
    ]


def _token(line: Mapping[str, Any]) -> str:
    return line["vietocr_text"].strip().replace(" ", "")


def _is_money(line: Mapping[str, Any]) -> bool:
    token = _token(line)
    return _NUMBER.fullmatch(token) is not None or _DASH.fullmatch(token) is not None


def _value_proposals(
    lines: Sequence[Mapping[str, Any]], label: Mapping[str, Any]
) -> list[dict[str, Any]]:
    top, bottom = label["bbox"][1], label["bbox"][3]
    label_center_y = (top + bottom) / 2
    row_tolerance = max(14.0, (bottom - top) * 0.65)
    width = max((item["bbox"][2] for item in lines), default=1)
    values = []
    for item in lines:
        center_y = (item["bbox"][1] + item["bbox"][3]) / 2
        if (
            item["bbox"][0] > width * 0.47
            and abs(center_y - label_center_y) <= row_tolerance
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


def _optional_role(text: str) -> str | None:
    if "ngan hang nha nuoc lao" in text or "ngan hang trung uong lao" in text:
        return "CENTRAL_BANK_LAOS"
    if "ngan hang quoc gia campuchia" in text or "ngan hang trung uong campuchia" in text:
        return "CENTRAL_BANK_CAMBODIA"
    if "tien gui phong toa" in text:
        return "BLOCKED_DEPOSIT"
    if text == "tien gui khac":
        return "OTHER_DEPOSIT"
    return None


def _total_after(
    lines: Sequence[Mapping[str, Any]], last_event: Mapping[str, Any]
) -> dict[str, Any] | None:
    width = max((item["bbox"][2] for item in lines), default=1)
    bottom = last_event["bbox"][3]
    numeric = [
        item
        for item in lines
        if last_event["source_line_index"]
        < item["source_line_index"]
        <= last_event["source_line_index"] + 8
        and item["bbox"][0] > width * 0.47
        and item["bbox"][1] >= bottom + 3
        and _is_money(item)
    ]
    for seed in numeric:
        center = (seed["bbox"][1] + seed["bbox"][3]) / 2
        row = sorted(
            [
                item
                for item in numeric
                if abs((item["bbox"][1] + item["bbox"][3]) / 2 - center) <= 14
            ],
            key=lambda item: item["bbox"][0],
        )
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
    roles = ["PARENT:CENTRAL_BANK_DEPOSITS"] + [
        f"CHILD:{event['role']}"
        for event in events
        if event["role"] in {"DEPOSIT_VND", "DEPOSIT_FOREIGN_CURRENCY"}
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
        raise _error("complete central-bank graph has no anchor pair")
    return {
        "combination_size": 2,
        "pair_search_order": "ALL_PARENT_CHILD_PAIRS_THEN_ALL_CHILD_CHILD_PAIRS",
        "selected_roles": list(tested[0]),
        "tested_pair_count": len(tested),
        "unique_within_complete_context_regions": True,
    }


def _candidate(
    page: Mapping[str, Any], engine_region: Mapping[str, Any], order_variant: str
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    lines = page["lines"]
    by_index = {line["source_line_index"]: line for line in lines}
    owner_record = engine_region.get("owner_context")
    child_indices = engine_region.get("child_source_line_indices")
    child_records = engine_region.get("child_match_records")
    branch_index = engine_region.get("branch_source_line_index")
    if (
        type(owner_record) is not dict
        or owner_record.get("page_sequence") != page["page_sequence"]
        or type(branch_index) is not int
        or type(child_indices) is not list
        or type(child_records) is not list
        or len(child_indices) != 2
        or len(child_records) != 2
    ):
        return None, {
            "order_variant": order_variant,
            "page_sequence": page["page_sequence"],
            "reasons": ["GENERIC_ENGINE_REGION_SHAPE_OR_OWNER_MODE_UNSUPPORTED"],
        }
    owner_index = owner_record.get("source_line_index")
    if type(owner_index) is not int or any(
        index not in by_index for index in (owner_index, branch_index, *child_indices)
    ):
        raise _error("generic engine/source line cross-binding drifted")
    branch_line = by_index[branch_index]
    events: list[dict[str, Any]] = [
        {
            "bbox": list(branch_line["bbox"]),
            "role": "CENTRAL_BANK_VIETNAM_PARENT",
            "role_kind": "INTERMEDIATE_PARENT",
            "source_line_index": branch_index,
            "value_proposals": _value_proposals(lines, branch_line),
            "vietocr_text": branch_line["vietocr_text"],
        }
    ]
    for index, record in zip(child_indices, child_records, strict=True):
        line = by_index[index]
        role = record.get("role")
        if role not in {"DEPOSIT_VND", "DEPOSIT_FOREIGN_CURRENCY"}:
            raise _error("generic engine child role drifted")
        events.append(
            {
                "bbox": list(line["bbox"]),
                "role": role,
                "role_kind": "REQUIRED_CHILD",
                "source_line_index": index,
                "value_proposals": _value_proposals(lines, line),
                "vietocr_text": line["vietocr_text"],
            }
        )
    last_child_index = max(child_indices)
    for item in lines:
        if not last_child_index < item["source_line_index"] <= last_child_index + 10:
            continue
        role = _optional_role(item["normalized_text"])
        if role is not None:
            events.append(
                {
                    "bbox": list(item["bbox"]),
                    "role": role,
                    "role_kind": "OPTIONAL_CHILD",
                    "source_line_index": item["source_line_index"],
                    "value_proposals": _value_proposals(lines, item),
                    "vietocr_text": item["vietocr_text"],
                }
            )
    events.sort(key=lambda item: item["source_line_index"])
    last_event = events[-1]
    total = _total_after(lines, last_event)
    first_child_index = min(child_indices)
    periods = _axis_groups(lines, owner_index, first_child_index, kind="PERIOD")
    units = _axis_groups(lines, owner_index, first_child_index, kind="UNIT")
    reasons = []
    required = [
        event for event in events if event["role"] in {"DEPOSIT_VND", "DEPOSIT_FOREIGN_CURRENCY"}
    ]
    if any(len(event["value_proposals"]) < 2 for event in required):
        reasons.append("REQUIRED_CHILD_HAS_FEWER_THAN_TWO_MONETARY_VALUES")
    if len(periods) < 2:
        reasons.append("FEWER_THAN_TWO_PERIOD_AXES")
    if len(units) < 1:
        reasons.append("NO_MONETARY_UNIT_AXIS")
    if total is None or len(total["value_proposals"]) < 2:
        reasons.append("NO_TWO_AXIS_TRAILING_TOTAL")
    near = {
        "branch_source_line_index": branch_index,
        "child_roles": [event["role"] for event in events],
        "order_variant": order_variant,
        "owner_source_line_index": owner_index,
        "page_sequence": page["page_sequence"],
        "reasons": reasons,
    }
    if reasons:
        return None, near
    assert total is not None
    total_end = max(item["source_line_index"] for item in total["value_proposals"])
    optional_roles = [event["role"] for event in events if event["role_kind"] == "OPTIONAL_CHILD"]
    material = {
        "cluster_boundary": {
            "first_item_role": "CENTRAL_BANK_DEPOSITS_OWNER",
            "first_page_sequence": page["page_sequence"],
            "first_source_line_index": owner_index,
            "last_item_role": "TOTAL",
            "last_page_sequence": page["page_sequence"],
            "last_source_line_index": total_end,
            "selection_rule": (
                "OUTER_OWNER_THEN_CENTRAL_BANK_PARENT_AND_REQUIRED_CURRENCY_CHILDREN_"
                "THROUGH_FIRST_TWO_AXIS_TOTAL_BEFORE_RESERVE_RATIO_OR_NEXT_NOTE_FAMILY"
            ),
        },
        "events": events + [total],
        "generic_engine_binding": {
            "branch_match": canonical_clone_v1(engine_region["branch_match"]),
            "context_complete": engine_region["context_complete"],
            "order_variant": order_variant,
            "owner_context": canonical_clone_v1(owner_record),
        },
        "layout": {
            "meaningful_axes": {
                "period_axes": periods,
                "period_header_count": len(periods),
                "unit_axes": units,
                "unit_header_count": len(units),
            },
            "orientation": "ROW_LABELS_BY_PERIOD_COLUMNS",
            "variant": (
                "MULTI_CENTRAL_BANK_WITH_VIETNAM_CURRENCY_BREAKDOWN"
                if optional_roles
                else "VIETNAM_VND_FOREIGN_ONLY"
            ),
        },
        "minimal_anchor": _minimal_anchor(events),
        "optional_child_roles": optional_roles,
        "owner": {
            "bbox": list(by_index[owner_index]["bbox"]),
            "source_line_index": owner_index,
            "vietocr_text": by_index[owner_index]["vietocr_text"],
        },
        "page_sequence": page["page_sequence"],
        "primary_numeric_authority": page["primary_numeric_authority"],
    }
    return {
        **material,
        "region_id": "cbdvgv1:region:" + canonical_json_sha256_v1(material),
    }, near


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("central-bank deposit result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["regions"]) is not list
        or type(value["near_regions"]) is not list
    ):
        raise _error("central-bank deposit result identity or authority drifted")
    region_count = len(value["regions"])
    expected_status = (
        "ACCEPTED_UNIQUE_VARIANT_GRAPH"
        if region_count == 1
        else (
            "UNRESOLVED_NO_COMPLETE_REGION"
            if region_count == 0
            else "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
        )
    )
    expected_uniqueness = {
        "complete_region_count": region_count,
        "status": (
            "UNIQUE_FULL_MATCH"
            if region_count == 1
            else ("NO_FULL_MATCH" if region_count == 0 else "MULTIPLE_FULL_MATCHES")
        ),
    }
    expected_metrics = {
        "complete_central_bank_deposit_region_count": region_count,
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
        raise _error("central-bank deposit result status or metrics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "cbdvgv1:result:" + canonical_json_sha256_v1(material):
        raise _error("central-bank deposit result identity drifted")
    return canonical_clone_v1(value)


def build_central_bank_deposits_variant_graph_document_v1(
    document_pages: Any,
) -> dict[str, Any]:
    """Enumerate every complete central-bank deposit cluster in one PDF."""

    pages = _pages(document_pages)
    by_page = {page["page_sequence"]: page for page in pages}
    engine_pages = _engine_pages(pages)
    regions_by_key: dict[tuple[int, int, int, tuple[int, ...]], dict[str, Any]] = {}
    near_regions: list[dict[str, Any]] = []
    for order_variant, spec in _ORDER_SPECS:
        engine_scan = build_accounting_variant_region_scan_v1(engine_pages, spec)
        for near in engine_scan["near_regions"]:
            near_regions.append(
                {
                    "branch_source_line_index": near["branch_source_line_index"],
                    "order_variant": order_variant,
                    "page_sequence": near["page_sequence"],
                    "reasons": canonical_clone_v1(near["unresolved_reasons"]),
                }
            )
        for region in engine_scan["regions"]:
            if region["context_complete"] is not True:
                continue
            wrapped, near = _candidate(by_page[region["page_sequence"]], region, order_variant)
            if wrapped is None:
                near_regions.append(near)
                continue
            key = (
                wrapped["page_sequence"],
                wrapped["owner"]["source_line_index"],
                region["branch_source_line_index"],
                tuple(sorted(region["child_source_line_indices"])),
            )
            regions_by_key[key] = wrapped
    regions = sorted(
        regions_by_key.values(),
        key=lambda item: (item["page_sequence"], item["owner"]["source_line_index"]),
    )
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "metrics": {
            "complete_central_bank_deposit_region_count": len(regions),
            "near_region_count": len(near_regions),
            "page_count": len(pages),
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
        {**material, "result_id": "cbdvgv1:result:" + canonical_json_sha256_v1(material)}
    )


def validate_central_bank_deposits_variant_graph_replay_v1(
    value: Any, document_pages: Any
) -> dict[str, Any]:
    """Exact-rebuild one complete-PDF family graph."""

    persisted = _validate_result(value)
    rebuilt = build_central_bank_deposits_variant_graph_document_v1(document_pages)
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("central-bank deposit graph does not replay exactly")
    return persisted
