"""Bank-blind declarative parent/child topology discovery for TM families.

This module is deliberately narrower than a family mapper.  It enumerates
semantic clusters from a complete document using fresh VietOCR labels and
source-bound line geometry, while leaving period, unit, numeric, accounting,
schema, and mapping decisions to independent shared primitives and the family
evaluation layer.

The same engine supports explicit or structurally implied parents, required
and optional siblings, reordered rows, wrapped labels, hard-negative families,
and structural resets.  It also proves the smallest role combination that is
unique in the supplied document by exhausting pairs before triples.  No bank,
filename, note number, page selector, reporting year, or schema ID is accepted
by the specification.
"""

from __future__ import annotations

import itertools
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
    "SPEC_FORMAT_VERSION",
    "AccountingFamilyTopologyV1Error",
    "build_accounting_family_topology_scan_v1",
    "validate_accounting_family_topology_scan_replay_v1",
]


FORMAT_VERSION = "ACCOUNTING_FAMILY_TOPOLOGY_SCAN_V1"
SPEC_FORMAT_VERSION = "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V1"
CLAIM_BOUNDARY = (
    "COMPLETE_DOCUMENT_BANK_BLIND_FRESH_VIETOCR_PARENT_REQUIRED_OPTIONAL_SIBLING_"
    "WRAPPED_LABEL_FLEXIBLE_ORDER_HARD_NEGATIVE_STRUCTURAL_RESET_AND_PAIR_BEFORE_"
    "TRIPLE_UNIQUENESS_PROPOSAL_ONLY_NO_PERIOD_UNIT_NUMERIC_ACCOUNTING_SCHEMA_"
    "MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_page_year_used_for_matching": False,
    "continuation_authority": False,
    "family_layout_logic_is_declarative": True,
    "mapping_authority": False,
    "numeric_authority": False,
    "pair_combinations_exhausted_before_triples": True,
    "period_or_unit_authority": False,
    "persisted_result_self_authenticating": False,
    "reordered_siblings_permitted": True,
    "schema_authority": False,
    "text_similarity_alone_can_accept": False,
    "vietocr_transformer_text_required": True,
    "whole_document_enumeration_required": True,
}
_SPEC_FIELDS = {
    "children",
    "family_id",
    "format_version",
    "hard_negative_aliases",
    "limits",
    "parent",
    "structural_reset_aliases",
}
_RESULT_FIELDS = {
    "claim_boundary",
    "family_id",
    "format_version",
    "metrics",
    "near_regions",
    "regions",
    "safety",
    "scan_id",
    "status",
    "uniqueness",
}
_ROLE_KINDS = {
    "ADDITIVE_CHILD",
    "NONADDITIVE_CHILD",
    "SOURCE_ONLY_GROUP_PARENT",
    "SUBTOTAL",
    "TOTAL",
}
_PRESENCE = {"OPTIONAL", "REQUIRED"}
_PARENT_RESOLUTION = {"EXPLICIT_ONLY", "EXPLICIT_OR_UNIQUE_REQUIRED_CHILD_CLUSTER"}


class AccountingFamilyTopologyV1Error(ValueError):
    """The semantic document, declarative family spec, or replay drifted."""


def _error(message: str) -> AccountingFamilyTopologyV1Error:
    return AccountingFamilyTopologyV1Error(message)


def _nonempty_string(value: Any, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise _error(f"{label} must be one non-empty exact string")
    return value


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} must be one positive exact integer")
    return value


def _aliases(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    if type(value) is not list or (not value and not allow_empty):
        raise _error(f"{label} must be one {'list' if allow_empty else 'non-empty list'}")
    normalized = [
        normalize_vietnamese_anchor_v1(_nonempty_string(item, f"{label} item")) for item in value
    ]
    if any(not item for item in normalized) or len(normalized) != len(set(normalized)):
        raise _error(f"{label} aliases must normalize to unique non-empty strings")
    return normalized


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
        raise _error("semantic line bbox must be four exact positive-area integers")
    return list(value)


def _spec(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _SPEC_FIELDS:
        raise _error("accounting family topology spec fields drifted")
    family_id = _nonempty_string(value["family_id"], "family ID")
    if value["format_version"] != SPEC_FORMAT_VERSION:
        raise _error("accounting family topology spec version drifted")
    parent = value["parent"]
    if type(parent) is not dict or set(parent) != {"aliases", "resolution_mode", "role"}:
        raise _error("accounting family parent spec fields drifted")
    parent_role = _nonempty_string(parent["role"], "parent role")
    resolution_mode = parent["resolution_mode"]
    if type(resolution_mode) is not str or resolution_mode not in _PARENT_RESOLUTION:
        raise _error("accounting family parent resolution mode drifted")

    raw_children = value["children"]
    if type(raw_children) is not list or len(raw_children) < 2:
        raise _error("accounting family needs at least two child roles")
    children: list[dict[str, Any]] = []
    roles = {parent_role}
    for raw in raw_children:
        if type(raw) is not dict or set(raw) != {"aliases", "presence", "role", "role_kind"}:
            raise _error("accounting family child spec fields drifted")
        role = _nonempty_string(raw["role"], "child role")
        presence = raw["presence"]
        role_kind = raw["role_kind"]
        if role in roles:
            raise _error("accounting family roles must be unique")
        if type(presence) is not str or presence not in _PRESENCE:
            raise _error("accounting family child presence drifted")
        if type(role_kind) is not str or role_kind not in _ROLE_KINDS:
            raise _error("accounting family child semantic kind drifted")
        roles.add(role)
        children.append(
            {
                "aliases": _aliases(raw["aliases"], f"{role} aliases"),
                "preferred_ordinal": len(children),
                "presence": presence,
                "role": role,
                "role_kind": role_kind,
            }
        )
    if sum(child["presence"] == "REQUIRED" for child in children) < 2:
        raise _error("accounting family needs at least two required child roles")

    limits = value["limits"]
    if type(limits) is not dict or set(limits) != {
        "max_cluster_span_lines",
        "max_label_line_span",
    }:
        raise _error("accounting family topology limits drifted")
    max_label_span = _positive_int(limits["max_label_line_span"], "maximum label line span")
    if max_label_span > 4:
        raise _error("maximum label line span exceeds the bounded generic policy")
    return {
        "children": children,
        "family_id": family_id,
        "hard_negative_aliases": _aliases(
            value["hard_negative_aliases"], "hard-negative", allow_empty=True
        ),
        "limits": {
            "max_cluster_span_lines": _positive_int(
                limits["max_cluster_span_lines"], "maximum cluster span"
            ),
            "max_label_line_span": max_label_span,
        },
        "parent": {
            "aliases": _aliases(parent["aliases"], "parent"),
            "resolution_mode": resolution_mode,
            "role": parent_role,
        },
        "structural_reset_aliases": _aliases(
            value["structural_reset_aliases"], "structural reset", allow_empty=True
        ),
    }


def _pages(value: Any) -> list[dict[str, Any]]:
    if type(value) is not list or not value:
        raise _error("topology scan requires one complete non-empty document")
    pages: list[dict[str, Any]] = []
    for expected_page, raw_page in enumerate(value, 1):
        if type(raw_page) is not dict or set(raw_page) != {"lines", "page_sequence"}:
            raise _error("topology page fields drifted")
        if raw_page["page_sequence"] != expected_page or type(raw_page["lines"]) is not list:
            raise _error("topology page sequence or line axis drifted")
        lines: list[dict[str, Any]] = []
        prior_index = -1
        for raw_line in raw_page["lines"]:
            if type(raw_line) is not dict or set(raw_line) != {
                "bbox",
                "source_line_index",
                "source_text",
                "vietocr_text",
            }:
                raise _error("topology semantic line fields drifted")
            index = raw_line["source_line_index"]
            if type(index) is not int or index <= prior_index:
                raise _error("topology source line indices must be exact and increasing")
            source_text = raw_line["source_text"]
            vietocr_text = raw_line["vietocr_text"]
            if source_text is not None and type(source_text) is not str:
                raise _error("topology source text must be null or one exact string")
            if type(vietocr_text) is not str:
                raise _error("topology VietOCR text must be one exact string")
            lines.append(
                {
                    "bbox": _bbox(raw_line["bbox"]),
                    "normalized_text": normalize_vietnamese_anchor_v1(vietocr_text),
                    "source_line_index": index,
                    "source_text": source_text,
                    "vietocr_text": vietocr_text,
                }
            )
            prior_index = index
        pages.append({"lines": lines, "page_sequence": expected_page})
    return pages


def _edit_distance_at_most_one(left: str, right: str) -> bool:
    if left == right:
        return True
    if abs(len(left) - len(right)) > 1:
        return False
    if len(left) > len(right):
        left, right = right, left
    if len(left) == len(right):
        return sum(a != b for a, b in zip(left, right, strict=True)) <= 1
    left_index = 0
    right_index = 0
    differences = 0
    while left_index < len(left) and right_index < len(right):
        if left[left_index] == right[right_index]:
            left_index += 1
            right_index += 1
        else:
            differences += 1
            right_index += 1
            if differences > 1:
                return False
    return True


def _alias_kind(surface: str, aliases: Sequence[str]) -> str | None:
    normalized = normalize_vietnamese_anchor_v1(surface)
    if normalized in aliases:
        return "EXACT_ACCENTLESS_ALIAS"
    if any(_edit_distance_at_most_one(normalized, alias) for alias in aliases):
        return "ONE_EDIT_ALIAS_REQUIRES_COMPLETE_TOPOLOGY"
    return None


def _joined(lines: Sequence[Mapping[str, Any]], start: int, stop: int) -> str:
    return " ".join(line["vietocr_text"].strip() for line in lines[start:stop]).strip()


def _role_hits(
    lines: Sequence[Mapping[str, Any]],
    *,
    aliases: Sequence[str],
    max_label_span: int,
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for start in range(len(lines)):
        for width in range(1, min(max_label_span, len(lines) - start) + 1):
            surface = _joined(lines, start, start + width)
            kind = _alias_kind(surface, aliases)
            if kind is None:
                continue
            hits.append(
                {
                    "end_source_line_index": lines[start + width - 1]["source_line_index"],
                    "match_kind": kind,
                    "normalized_surface": normalize_vietnamese_anchor_v1(surface),
                    "source_line_index": lines[start]["source_line_index"],
                    "surface": surface,
                }
            )
            break
    # A wrapped match may also expose an exact shorter match beginning on its
    # continuation line.  Retain the shortest match at each ending position so
    # one visual label cannot become two semantic rows.
    by_end: dict[int, dict[str, Any]] = {}
    for hit in hits:
        existing = by_end.get(hit["end_source_line_index"])
        if existing is None or hit["source_line_index"] < existing["source_line_index"]:
            by_end[hit["end_source_line_index"]] = hit
    return sorted(by_end.values(), key=lambda item: item["source_line_index"])


def _page_hits(page: Mapping[str, Any], spec: Mapping[str, Any]) -> dict[str, Any]:
    lines = page["lines"]
    max_span = spec["limits"]["max_label_line_span"]
    children = {
        child["role"]: _role_hits(lines, aliases=child["aliases"], max_label_span=max_span)
        for child in spec["children"]
    }
    return {
        "children": children,
        "hard_negatives": _role_hits(
            lines,
            aliases=spec["hard_negative_aliases"],
            max_label_span=max_span,
        ),
        "parents": _role_hits(
            lines,
            aliases=spec["parent"]["aliases"],
            max_label_span=max_span,
        ),
        "resets": _role_hits(
            lines,
            aliases=spec["structural_reset_aliases"],
            max_label_span=max_span,
        ),
    }


def _first_after(hits: Sequence[Mapping[str, Any]], index: int) -> int | None:
    positions = [hit["source_line_index"] for hit in hits if hit["source_line_index"] > index]
    return min(positions) if positions else None


def _child_records_in_range(
    hits: Mapping[str, Sequence[Mapping[str, Any]]],
    spec: Mapping[str, Any],
    *,
    start: int,
    stop: int,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for child in spec["children"]:
        candidates = [hit for hit in hits[child["role"]] if start < hit["source_line_index"] < stop]
        if not candidates:
            continue
        hit = min(candidates, key=lambda item: item["source_line_index"])
        records.append(
            {
                **canonical_clone_v1(hit),
                "preferred_ordinal": child["preferred_ordinal"],
                "presence": child["presence"],
                "role": child["role"],
                "role_kind": child["role_kind"],
            }
        )
    return sorted(records, key=lambda item: item["source_line_index"])


def _candidate(
    *,
    page: Mapping[str, Any],
    parent: Mapping[str, Any] | None,
    records: Sequence[Mapping[str, Any]],
    start: int,
    stop: int,
    spec: Mapping[str, Any],
    hard_negative_hits: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    observed_roles = [record["role"] for record in records]
    required_roles = [
        child["role"] for child in spec["children"] if child["presence"] == "REQUIRED"
    ]
    missing = [role for role in required_roles if role not in observed_roles]
    hard_negatives = [
        canonical_clone_v1(hit)
        for hit in hard_negative_hits
        if start <= hit["source_line_index"] < stop
    ]
    reasons = [f"MISSING_REQUIRED_CHILD:{role}" for role in missing]
    if hard_negatives:
        reasons.append("HARD_NEGATIVE_FAMILY_IN_CLUSTER")
    preferred = sorted(records, key=lambda item: item["preferred_ordinal"])
    return {
        "child_matches": canonical_clone_v1(list(records)),
        "cluster_end_source_line_index_exclusive": stop,
        "cluster_start_source_line_index": start,
        "hard_negative_matches": hard_negatives,
        "observed_roles": observed_roles,
        "page_sequence": page["page_sequence"],
        "parent_match": canonical_clone_v1(parent) if parent is not None else None,
        "parent_resolution": (
            "EXPLICIT_PARENT" if parent is not None else "IMPLIED_BY_REQUIRED_CHILD_CLUSTER"
        ),
        "preferred_sibling_order_preserved": observed_roles
        == [record["role"] for record in preferred],
        "unresolved_reasons": sorted(reasons),
    }


def _explicit_candidates(
    page: Mapping[str, Any], hits: Mapping[str, Any], spec: Mapping[str, Any]
) -> list[dict[str, Any]]:
    candidates = []
    maximum_span = spec["limits"]["max_cluster_span_lines"]
    for parent_offset, parent in enumerate(hits["parents"]):
        start = parent["source_line_index"]
        stops = [start + maximum_span + 1]
        if parent_offset + 1 < len(hits["parents"]):
            stops.append(hits["parents"][parent_offset + 1]["source_line_index"])
        reset = _first_after(hits["resets"], start)
        if reset is not None:
            stops.append(reset)
        stop = min(stops)
        records = _child_records_in_range(hits["children"], spec, start=start, stop=stop)
        candidates.append(
            _candidate(
                page=page,
                parent=parent,
                records=records,
                start=start,
                stop=stop,
                spec=spec,
                hard_negative_hits=hits["hard_negatives"],
            )
        )
    return candidates


def _implied_candidates(
    page: Mapping[str, Any],
    hits: Mapping[str, Any],
    spec: Mapping[str, Any],
    explicit: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if spec["parent"]["resolution_mode"] != "EXPLICIT_OR_UNIQUE_REQUIRED_CHILD_CLUSTER":
        return []
    required = [child for child in spec["children"] if child["presence"] == "REQUIRED"]
    axes = [hits["children"][child["role"]] for child in required]
    if any(not axis for axis in axes):
        return []
    maximum_span = spec["limits"]["max_cluster_span_lines"]
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[int, ...]] = set()
    for combination in itertools.product(*axes):
        positions = [hit["source_line_index"] for hit in combination]
        if len(set(positions)) != len(positions) or max(positions) - min(positions) > maximum_span:
            continue
        signature = tuple(sorted(positions))
        if signature in seen:
            continue
        seen.add(signature)
        start = min(positions) - 1
        stop = max(positions) + maximum_span + 1
        resets = [
            hit["source_line_index"]
            for hit in hits["resets"]
            if start < hit["source_line_index"] < stop
        ]
        if resets and min(resets) <= max(positions):
            continue
        if resets:
            stop = min(stop, min(resets))
        if any(
            item["cluster_start_source_line_index"]
            <= min(positions)
            < item["cluster_end_source_line_index_exclusive"]
            for item in explicit
        ):
            continue
        records = _child_records_in_range(hits["children"], spec, start=start, stop=stop)
        candidates.append(
            _candidate(
                page=page,
                parent=None,
                records=records,
                start=max(0, start),
                stop=stop,
                spec=spec,
                hard_negative_hits=hits["hard_negatives"],
            )
        )
    return candidates


def _anchor_roles(candidate: Mapping[str, Any], parent_role: str) -> list[str]:
    anchors = []
    if candidate["parent_match"] is not None:
        anchors.append("PARENT:" + parent_role)
    anchors.extend("CHILD:" + role for role in candidate["observed_roles"])
    return anchors


def _minimal_unique_anchors(
    candidate: Mapping[str, Any], all_candidates: Sequence[Mapping[str, Any]], parent_role: str
) -> dict[str, Any] | None:
    anchors = _anchor_roles(candidate, parent_role)
    other_sets = [
        set(_anchor_roles(item, parent_role)) for item in all_candidates if item is not candidate
    ]
    for size in (2, 3):
        if len(anchors) < size:
            continue
        combinations = list(itertools.combinations(anchors, size))
        parent_first = [item for item in combinations if item[0].startswith("PARENT:")]
        child_only = [item for item in combinations if item not in parent_first]
        for combination in [*parent_first, *child_only]:
            if not any(set(combination).issubset(other) for other in other_sets):
                return {
                    "combination_size": size,
                    "pair_before_triple_search": True,
                    "selected_roles": list(combination),
                }
    return None


def _build(pages: Sequence[Mapping[str, Any]], spec: Mapping[str, Any]) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for page in pages:
        hits = _page_hits(page, spec)
        explicit = _explicit_candidates(page, hits, spec)
        candidates.extend(explicit)
        candidates.extend(_implied_candidates(page, hits, spec, explicit))

    complete = [candidate for candidate in candidates if not candidate["unresolved_reasons"]]
    for candidate in complete:
        candidate["minimal_unique_anchor"] = _minimal_unique_anchors(
            candidate, candidates, spec["parent"]["role"]
        )
    near = [candidate for candidate in candidates if candidate["unresolved_reasons"]]
    unique = len(complete) == 1 and complete[0]["minimal_unique_anchor"] is not None
    return {
        "metrics": {
            "complete_region_count": len(complete),
            "explicit_parent_region_count": sum(
                item["parent_resolution"] == "EXPLICIT_PARENT" for item in complete
            ),
            "implied_parent_region_count": sum(
                item["parent_resolution"] == "IMPLIED_BY_REQUIRED_CHILD_CLUSTER"
                for item in complete
            ),
            "near_region_count": len(near),
            "reordered_complete_region_count": sum(
                not item["preferred_sibling_order_preserved"] for item in complete
            ),
        },
        "near_regions": near,
        "regions": complete,
        "status": (
            "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
            if unique
            else "UNRESOLVED_NO_COMPLETE_REGION"
            if not complete
            else "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS"
        ),
        "uniqueness": {
            "complete_region_count": len(complete),
            "minimal_role_combination_proved": unique,
        },
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("accounting family topology result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["family_id"]) is not str
        or not value["family_id"]
    ):
        raise _error("accounting family topology result identity drifted")
    material = canonical_clone_v1(value)
    scan_id = material.pop("scan_id")
    if scan_id != "aftv1:scan:" + canonical_json_sha256_v1(material):
        raise _error("accounting family topology scan identity drifted")
    if type(value["regions"]) is not list or type(value["near_regions"]) is not list:
        raise _error("accounting family topology region axes drifted")
    return canonical_clone_v1(value)


def build_accounting_family_topology_scan_v1(
    document_pages: Any, family_spec: Any
) -> dict[str, Any]:
    """Enumerate all complete and near semantic family clusters in one PDF."""

    pages = _pages(document_pages)
    spec = _spec(family_spec)
    built = _build(pages, spec)
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": spec["family_id"],
        "format_version": FORMAT_VERSION,
        **built,
        "safety": canonical_clone_v1(_SAFETY),
    }
    return _validate_result(
        {**material, "scan_id": "aftv1:scan:" + canonical_json_sha256_v1(material)}
    )


def validate_accounting_family_topology_scan_replay_v1(
    value: Any, document_pages: Any, family_spec: Any
) -> dict[str, Any]:
    """Exact-rebuild one topology scan from the full document and family spec."""

    persisted = _validate_result(value)
    expected = build_accounting_family_topology_scan_v1(document_pages, family_spec)
    if not same_typed_json_v1(persisted, expected):
        raise _error("accounting family topology scan does not replay exactly")
    return persisted
