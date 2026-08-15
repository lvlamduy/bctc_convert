"""Bank-blind full-PDF graph for tangible fixed-asset movements.

The common accounting core is an owner (tangible fixed assets), followed by
the cost, accumulated-depreciation and carrying-value branches.  Movement
rows, asset-class columns, comparison-page continuations and page rotation are
layout variants.  Text is an anchor only; numeric, period, unit, hierarchy and
accounting authority belong to the independent review layer.

No bank, filename, note number or physical page participates in matching.
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
    "LEASED_FORMAT_VERSION",
    "TangibleFixedAssetsVariantGraphV1Error",
    "build_leased_fixed_assets_variant_graph_document_v1",
    "build_tangible_fixed_assets_variant_graph_document_v1",
    "validate_leased_fixed_assets_variant_graph_replay_v1",
    "validate_tangible_fixed_assets_variant_graph_replay_v1",
]

FORMAT_VERSION = "TANGIBLE_FIXED_ASSETS_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "TANGIBLE_FIXED_ASSET_MOVEMENT"
LEASED_FORMAT_VERSION = "LEASED_FIXED_ASSETS_VARIANT_GRAPH_DOCUMENT_V1"
LEASED_FAMILY_ID = "LEASED_FIXED_ASSET_MOVEMENT"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_TANGIBLE_FIXED_ASSET_OWNER_COST_"
    "ACCUMULATED_DEPRECIATION_CARRYING_VALUE_OPTIONAL_MOVEMENTS_ASSET_CLASS_"
    "COLUMNS_COMPARATIVE_CONTINUATION_AND_ROTATED_SOURCE_AXIS_STRUCTURE_ONLY_"
    "NO_NUMERIC_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_or_routing": False,
    "complete_pdf_region_enumeration_required": True,
    "fresh_vietocr_transformer_text_required": True,
    "mapping_authority": False,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "optional_movements_and_asset_class_columns_may_vary": True,
    "pair_search_exhausted_before_larger_combinations": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "rotated_same_transformer_rescue_may_supply_semantic_text": True,
    "text_similarity_alone_can_accept": False,
}
_LEASED_CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_LEASED_FIXED_ASSET_OWNER_COST_"
    "ACCUMULATED_DEPRECIATION_OPTIONAL_MOVEMENTS_ASSET_CLASS_COLUMNS_"
    "COMPARATIVE_CONTINUATION_AND_ROTATED_SOURCE_AXIS_STRUCTURE_ONLY_NO_"
    "NUMERIC_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_LEASED_SAFETY = canonical_clone_v1(_SAFETY)
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
_SEMANTIC_SOURCES = {
    "FULL_DOCUMENT_FRESH_VIETOCR_TRANSFORMER",
    "ROTATED_FRESH_VIETOCR_TRANSFORMER_RESCUE",
}
_NUMBER = re.compile(r"^\(?[+-]?[0-9]+(?:[., ][0-9]+)*%?\)?$")
_DATE = re.compile(
    r"(?:[0-3]?[0-9](?:[./-]|\s+)[01]?[0-9](?:[./-]|\s+)(?:20)?[0-9]{2})|"
    r"(?:ngay\s+[0-3]?[0-9]\s+thang\s+[01]?[0-9])|"
    r"(?:so\s+du\s+(?:dau|cuoi)\s+ky)|(?:tai\s+ngay\s+(?:dau|cuoi)\s+ky)"
)
_MAX_REGION_PAGES = 2

_TANGIBLE_SPEC = {
    "claim_boundary": CLAIM_BOUNDARY,
    "core_roles": ("COST", "ACCUMULATED_DEPRECIATION", "CARRYING_VALUE"),
    "family_id": FAMILY_ID,
    "format_version": FORMAT_VERSION,
    "id_prefix": "tfavgv1:result:",
    "minimum_numeric_lines": 6,
    "owner_phrases": ("tai san co dinh huu hinh",),
    "owner_reject_phrases": ("thong tin khac", "nguyen gia", "bien dong"),
    "safety": _SAFETY,
    "trailing_family_phrases": (
        "tai san co dinh thue tai chinh",
        "tai san co dinh vo hinh",
        "bat dong san dau tu",
    ),
}
_LEASED_SPEC = {
    "claim_boundary": _LEASED_CLAIM_BOUNDARY,
    "core_roles": ("COST", "ACCUMULATED_DEPRECIATION"),
    "family_id": LEASED_FAMILY_ID,
    "format_version": LEASED_FORMAT_VERSION,
    "id_prefix": "lfavgv1:result:",
    "minimum_numeric_lines": 4,
    "owner_phrases": ("tai san co dinh thue tai chinh", "tscd thue tai chinh"),
    "owner_reject_phrases": ("thong tin khac", "nguyen tac", "chinh sach"),
    "safety": _LEASED_SAFETY,
    "trailing_family_phrases": ("tai san co dinh vo hinh", "bat dong san dau tu"),
}


class TangibleFixedAssetsVariantGraphV1Error(ValueError):
    """The complete-PDF input or replayed tangible-asset graph drifted."""


def _error(message: str) -> TangibleFixedAssetsVariantGraphV1Error:
    return TangibleFixedAssetsVariantGraphV1Error(message)


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
        raise _error("line bbox must contain four exact positive-bound integers")
    return list(value)


def _pages(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence) or not value:
        raise _error("tangible-fixed-assets matcher requires one complete nonempty PDF")
    pages: list[dict[str, Any]] = []
    global_ordinal = 0
    previous_page = 0
    for raw_page in value:
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_sequence",
            "primary_numeric_authority",
        }:
            raise _error("tangible-fixed-assets matcher page fields drifted")
        page_sequence = raw_page["page_sequence"]
        if type(page_sequence) is not int or page_sequence != previous_page + 1:
            raise _error("complete PDF page sequence must be exact and gap-free")
        if type(raw_page["primary_numeric_authority"]) is not bool:
            raise _error("primary numeric authority flag must be exact bool")
        if type(raw_page["lines"]) is not list:
            raise _error("page lines must be one list")
        lines: list[dict[str, Any]] = []
        for line_index, raw_line in enumerate(raw_page["lines"]):
            if type(raw_line) is not dict or set(raw_line) != {
                "bbox",
                "semantic_text",
                "semantic_text_source",
                "source_line_index",
                "source_text",
                "vietocr_text",
            }:
                raise _error("tangible-fixed-assets line fields drifted")
            if raw_line["source_line_index"] != line_index:
                raise _error("source line indices must be exact and gap-free")
            if raw_line["source_text"] is not None and type(raw_line["source_text"]) is not str:
                raise _error("source text must be null or one exact string")
            if (
                type(raw_line["vietocr_text"]) is not str
                or type(raw_line["semantic_text"]) is not str
            ):
                raise _error("VietOCR and semantic text must be exact strings")
            if raw_line["semantic_text_source"] not in _SEMANTIC_SOURCES:
                raise _error("semantic text source is unsupported")
            lines.append(
                {
                    "bbox": _bbox(raw_line["bbox"]),
                    "global_ordinal": global_ordinal,
                    "normalized_text": normalize_vietnamese_anchor_v1(raw_line["semantic_text"]),
                    "page_sequence": page_sequence,
                    "semantic_text": raw_line["semantic_text"],
                    "semantic_text_source": raw_line["semantic_text_source"],
                    "source_line_index": line_index,
                    "source_text": raw_line["source_text"],
                    "vietocr_text": raw_line["vietocr_text"],
                }
            )
            global_ordinal += 1
        pages.append(
            {
                "lines": lines,
                "page_sequence": page_sequence,
                "primary_numeric_authority": raw_page["primary_numeric_authority"],
            }
        )
        previous_page = page_sequence
    return pages


def _edit_distance(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for row, left_char in enumerate(left, 1):
        current = [row]
        for column, right_char in enumerate(right, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (left_char != right_char),
                )
            )
        previous = current
    return previous[-1]


def _near_phrase(value: str, expected: str, *, allowance: int = 2) -> bool:
    if expected in value:
        return True
    value_tokens = value.split()
    expected_tokens = expected.split()
    for width in range(
        max(1, len(expected_tokens) - 1),
        min(len(value_tokens), len(expected_tokens) + 1) + 1,
    ):
        for start in range(len(value_tokens) - width + 1):
            if _edit_distance(" ".join(value_tokens[start : start + width]), expected) <= allowance:
                return True
    return False


def _strip_enumerator(text: str) -> str:
    return re.sub(r"^(?:[0-9]+(?:[.]?[0-9]+)?\s+)+", "", text).strip()


def _is_owner(text: str, spec: Mapping[str, Any] = _TANGIBLE_SPEC) -> bool:
    value = _strip_enumerator(text)
    if any(prefix in value for prefix in spec["owner_reject_phrases"]):
        return False
    return len(value.split()) <= 11 and any(
        _near_phrase(value, phrase, allowance=2) for phrase in spec["owner_phrases"]
    )


def _is_next_family(text: str, spec: Mapping[str, Any] = _TANGIBLE_SPEC) -> bool:
    value = _strip_enumerator(text)
    return len(value.split()) <= 12 and any(
        _near_phrase(value, phrase, allowance=2) for phrase in spec["trailing_family_phrases"]
    )


def _branch_role(text: str) -> str | None:
    value = _strip_enumerator(text)
    if len(value.split()) > 10:
        return None
    if _near_phrase(value, "nguyen gia", allowance=1):
        return "COST"
    if any(
        _near_phrase(value, phrase, allowance=2)
        for phrase in ("hao mon luy ke", "khau hao luy ke", "gia tri hao mon luy ke")
    ):
        return "ACCUMULATED_DEPRECIATION"
    if _near_phrase(value, "gia tri con lai", allowance=2):
        return "CARRYING_VALUE"
    return None


def _movement_role(text: str) -> str | None:
    value = _strip_enumerator(text)
    if len(value.split()) > 14:
        return None
    rules = (
        ("OPENING", ("so du dau ky", "tai ngay dau ky", "tai ngay 1 1")),
        ("ENDING", ("so du cuoi ky", "tai ngay cuoi ky", "tai ngay 30 06")),
        ("PURCHASE", ("mua trong ky",)),
        ("DEPRECIATION", ("khau hao trong ky",)),
        ("INCREASE", ("tang trong ky",)),
        ("DECREASE", ("giam trong ky",)),
        ("OTHER_NET", ("tang giam khac",)),
        ("FOREIGN_EXCHANGE", ("chenh lech ty gia",)),
        ("DISPOSAL", ("thanh ly", "nhuong ban")),
        ("RECLASSIFICATION", ("phan loai lai",)),
    )
    for role, phrases in rules:
        if any(_near_phrase(value, phrase, allowance=2) for phrase in phrases):
            return role
    return None


def _line_ref(line: Mapping[str, Any], role: str) -> dict[str, Any]:
    return {
        "bbox": list(line["bbox"]),
        "global_ordinal": line["global_ordinal"],
        "page_sequence": line["page_sequence"],
        "role": role,
        "semantic_text": line["semantic_text"],
        "semantic_text_source": line["semantic_text_source"],
        "source_line_index": line["source_line_index"],
        "vietocr_text": line["vietocr_text"],
    }


def _is_rotated(lines: Sequence[Mapping[str, Any]]) -> bool:
    if not lines:
        return False
    tall = sum(
        line["bbox"][3] - line["bbox"][1] > line["bbox"][2] - line["bbox"][0] for line in lines
    )
    rescued = sum(
        line["semantic_text_source"] == "ROTATED_FRESH_VIETOCR_TRANSFORMER_RESCUE" for line in lines
    )
    return tall * 2 > len(lines) and rescued > 0


def _logical_position(line: Mapping[str, Any], *, rotated: bool) -> tuple[int, int]:
    if rotated:
        return line["bbox"][0], line["bbox"][1]
    return line["global_ordinal"], 0


def _candidate_window(
    owner: Mapping[str, Any],
    pages: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any] = _TANGIBLE_SPEC,
) -> tuple[list[Mapping[str, Any]], bool]:
    owner_page = pages[owner["page_sequence"] - 1]
    rotated = _is_rotated(owner_page["lines"])
    selected: list[Mapping[str, Any]] = []
    for page in pages[owner["page_sequence"] - 1 : owner["page_sequence"] - 1 + _MAX_REGION_PAGES]:
        if page["page_sequence"] != owner["page_sequence"] and any(
            _is_next_family(line["normalized_text"], spec) for line in page["lines"]
        ):
            break
        for line in page["lines"]:
            if page["page_sequence"] == owner["page_sequence"] and not rotated:
                if line["global_ordinal"] < owner["global_ordinal"]:
                    continue
            if line is not owner and _is_owner(line["normalized_text"], spec):
                break
            if _is_next_family(line["normalized_text"], spec):
                break
            selected.append(line)
    return selected, rotated


def _region(
    owner: Mapping[str, Any],
    pages: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any] = _TANGIBLE_SPEC,
) -> dict[str, Any]:
    window, rotated = _candidate_window(owner, pages, spec)
    branches: dict[str, list[Mapping[str, Any]]] = {}
    movements: dict[str, list[Mapping[str, Any]]] = {}
    periods: list[Mapping[str, Any]] = []
    units: list[Mapping[str, Any]] = []
    numeric_lines: list[Mapping[str, Any]] = []
    for line in window:
        text = line["normalized_text"]
        branch = _branch_role(text)
        movement = _movement_role(text)
        if branch is not None:
            branches.setdefault(branch, []).append(line)
        if movement is not None:
            movements.setdefault(movement, []).append(line)
        if _DATE.search(text):
            periods.append(line)
        if "trieu dong" in text or "trieu vnd" in text:
            units.append(line)
        if _NUMBER.fullmatch(text.replace(" ", "")):
            numeric_lines.append(line)
    core_roles = spec["core_roles"]
    current_branches = {
        role: [
            line
            for line in branches.get(role, [])
            if line["page_sequence"] == owner["page_sequence"]
        ]
        for role in core_roles
    }
    unique_branches = all(len(current_branches[role]) == 1 for role in core_roles)
    ordered = False
    if unique_branches:
        positions = [
            _logical_position(current_branches[role][0], rotated=rotated) for role in core_roles
        ]
        owner_position = _logical_position(owner, rotated=rotated)
        ordered = owner_position < positions[0] and all(
            left < right for left, right in itertools.pairwise(positions)
        )
    complete = (
        unique_branches
        and ordered
        and len(periods) >= 2
        and len(units) >= 1
        and len(numeric_lines) >= spec["minimum_numeric_lines"]
        and "OPENING" in movements
        and "ENDING" in movements
    )
    anchor_roles = ["OWNER", *[role for role in core_roles if role in branches]]
    events = [_line_ref(owner, "OWNER")]
    for role in core_roles:
        events.extend(_line_ref(line, role) for line in branches.get(role, []))
    for role in sorted(movements):
        events.extend(_line_ref(line, role) for line in movements[role])
    events.extend(_line_ref(line, "PERIOD_AXIS") for line in periods[:8])
    events.extend(_line_ref(line, "UNIT_AXIS") for line in units[:6])
    page_span = sorted({line["page_sequence"] for line in window}) or [owner["page_sequence"]]
    return {
        "anchor_roles": anchor_roles,
        "complete": complete,
        "end_global_ordinal": max(
            (line["global_ordinal"] for line in window), default=owner["global_ordinal"]
        ),
        "events": events,
        "layout": {
            "branch_order_verified": ordered,
            "branch_roles": sorted(branches),
            "explicit_unit_line_count": len(units),
            "movement_roles": sorted(movements),
            "period_axis_line_count": len(periods),
            "presentation": (
                "ROTATED_VERTICAL_SOURCE_AXIS_MOVEMENT_GRID"
                if rotated
                else (
                    "CURRENT_TABLE_WITH_COMPARATIVE_CONTINUATION"
                    if len(page_span) == 2
                    else "CURRENT_PERIOD_MOVEMENT_GRID"
                )
            ),
            "rotated_source_axis": rotated,
        },
        "numeric_line_count": len(numeric_lines),
        "owner": _line_ref(owner, "OWNER"),
        "pair_anchor_combinations": [
            list(pair) for pair in itertools.combinations(anchor_roles, 2)
        ],
        "page_span": [page_span[0], page_span[-1]],
        "start_global_ordinal": min(
            (line["global_ordinal"] for line in window), default=owner["global_ordinal"]
        ),
    }


def _validate_result(value: Any, spec: Mapping[str, Any] = _TANGIBLE_SPEC) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("tangible-fixed-assets graph result fields drifted")
    if (
        value["format_version"] != spec["format_version"]
        or value["family_id"] != spec["family_id"]
        or value["claim_boundary"] != spec["claim_boundary"]
        or not same_typed_json_v1(value["safety"], spec["safety"])
        or type(value["regions"]) is not list
        or type(value["near_regions"]) is not list
        or type(value["metrics"]) is not dict
        or type(value["uniqueness"]) is not dict
    ):
        raise _error("tangible-fixed-assets graph identity or authority drifted")
    complete_count = len(value["regions"])
    expected_status = (
        "ACCEPTED_UNIQUE_VARIANT_GRAPH"
        if complete_count == 1
        else (
            "UNRESOLVED_NO_COMPLETE_REGION"
            if complete_count == 0
            else "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
        )
    )
    expected_uniqueness = {
        "complete_region_count": complete_count,
        "status": "UNIQUE_FULL_MATCH" if complete_count == 1 else "NOT_UNIQUE_FULL_MATCH",
    }
    expected_metrics = {
        "complete_region_count": complete_count,
        "near_region_count": len(value["near_regions"]),
        "owner_candidate_count": complete_count + len(value["near_regions"]),
    }
    if (
        value["status"] != expected_status
        or not same_typed_json_v1(value["uniqueness"], expected_uniqueness)
        or not same_typed_json_v1(value["metrics"], expected_metrics)
    ):
        raise _error("tangible-fixed-assets graph metrics or uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != spec["id_prefix"] + canonical_json_sha256_v1(material):
        raise _error("tangible-fixed-assets graph identity drifted")
    return canonical_clone_v1(value)


def _build_variant_graph_document_v1(pages: Any, spec: Mapping[str, Any]) -> dict[str, Any]:
    normalized_pages = _pages(pages)
    owners = [
        line
        for page in normalized_pages
        for line in page["lines"]
        if _is_owner(line["normalized_text"], spec)
    ]
    candidates = [_region(owner, normalized_pages, spec) for owner in owners]
    regions = [candidate for candidate in candidates if candidate["complete"]]
    near_regions = [candidate for candidate in candidates if not candidate["complete"]]
    material = {
        "claim_boundary": spec["claim_boundary"],
        "family_id": spec["family_id"],
        "format_version": spec["format_version"],
        "metrics": {
            "complete_region_count": len(regions),
            "near_region_count": len(near_regions),
            "owner_candidate_count": len(candidates),
        },
        "near_regions": near_regions,
        "regions": regions,
        "safety": canonical_clone_v1(spec["safety"]),
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
            "status": "UNIQUE_FULL_MATCH" if len(regions) == 1 else "NOT_UNIQUE_FULL_MATCH",
        },
    }
    return _validate_result(
        {**material, "result_id": spec["id_prefix"] + canonical_json_sha256_v1(material)},
        spec,
    )


def build_tangible_fixed_assets_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
    """Enumerate every complete and near-complete tangible-asset region."""

    return _build_variant_graph_document_v1(pages, _TANGIBLE_SPEC)


def build_leased_fixed_assets_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
    """Enumerate every complete and near-complete leased-asset region."""

    return _build_variant_graph_document_v1(pages, _LEASED_SPEC)


def validate_tangible_fixed_assets_variant_graph_replay_v1(
    value: Any, pages: Any
) -> dict[str, Any]:
    """Rebuild the graph from the complete PDF and require typed equality."""

    supplied = _validate_result(value)
    rebuilt = build_tangible_fixed_assets_variant_graph_document_v1(pages)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("tangible-fixed-assets graph does not replay exactly")
    return supplied


def validate_leased_fixed_assets_variant_graph_replay_v1(value: Any, pages: Any) -> dict[str, Any]:
    """Rebuild the leased-asset graph from the complete PDF."""

    supplied = _validate_result(value, _LEASED_SPEC)
    rebuilt = build_leased_fixed_assets_variant_graph_document_v1(pages)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("leased-fixed-assets graph does not replay exactly")
    return supplied
