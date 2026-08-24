"""Exact second-channel authority for selected one-edit topology anchors.

The topology reader may use one edit to *retrieve* a plausible family region.
That tolerance is deliberately not accounting or mapping authority.  This
module closes that gap for V4 callers: after downstream evidence has selected
one candidate, every selected parent/expanded-occurrence one-edit match must be
re-observed as an exact declared alias on the identical bound source-text
lines, in the identical family/role/structural-parent context.  Expanded
children are bound by occurrence ID so one exact occurrence can never
corroborate a fuzzy repetition of the same role.

Only accent removal/case/punctuation normalization, an enumeration prefix,
and the topology engine's bounded decorative parenthetical removal are exact
transforms here.  Edit distance is never consulted by the authority channel.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
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
    "AccountingFamilyOneEditExactAuthorityV1Error",
    "build_accounting_family_one_edit_exact_authority_v1",
    "validate_accounting_family_one_edit_exact_authority_receipt_shape_v1",
    "validate_accounting_family_one_edit_exact_authority_replay_v1",
]


FORMAT_VERSION = "ACCOUNTING_FAMILY_ONE_EDIT_EXACT_AUTHORITY_V1"
CLAIM_BOUNDARY = (
    "SELECTED_V4_TOPOLOGY_ONE_EDIT_RETRIEVAL_MATCHES_REQUIRE_INDEPENDENT_EXACT_"
    "BOUND_SOURCE_TEXT_ALIAS_ON_IDENTICAL_OCCURRENCE_FAMILY_ROLE_PARENT_PAGE_AND_LINE_SPAN_"
    "NO_NUMERIC_SCHEMA_MAPPING_OR_DISCARDED_CANDIDATE_VETO_AUTHORITY"
)
_AUTHORITY_SPEC = {
    "allowed_exact_transforms": [
        "ACCENTLESS",
        "ACCENTLESS_AFTER_ENUMERATION_PREFIX",
        "ACCENTLESS_AFTER_DECORATIVE_PARENTHETICAL_REMOVAL",
        "ACCENTLESS_AFTER_ENUMERATION_PREFIX_AND_DECORATIVE_PARENTHETICAL_REMOVAL",
    ],
    "bound_source_channel": "PPOCR_BOUND_SOURCE_TEXT",
    "exact_alias_requires_same_family_parent_context": True,
    "exact_alias_requires_same_expanded_occurrence_id": True,
    "exact_alias_requires_same_page_and_source_line_indices": True,
    "one_edit_channel": "VIETOCR_TRANSFORMER_RETRIEVAL_ONLY",
    "selected_candidate_only": True,
}
_SAFETY = {
    "bank_file_page_period_scope_used_for_routing": False,
    "discarded_or_near_one_edit_match_can_veto_selected_candidate": False,
    "mapping_authority": False,
    "one_edit_similarity_can_grant_exact_authority": False,
    "schema_authority": False,
    "source_text_exact_alias_and_context_required": True,
    "expanded_occurrence_identity_required": True,
}
_RESULT_FIELDS = {
    "authority_spec",
    "checks",
    "claim_boundary",
    "family_id",
    "format_version",
    "input_binding",
    "metrics",
    "receipt_id",
    "safety",
    "status",
    "unresolved_reasons",
}
_INPUT_BINDING_FIELDS = {
    "document_pages_sha256",
    "expanded_occurrence_region_sha256",
    "family_spec_sha256",
    "selected_topology_region_sha256",
}
_METRIC_FIELDS = {
    "exact_bound_count",
    "selected_one_edit_match_count",
    "unresolved_match_count",
}
_CHECK_FIELDS = {
    "exact_channel",
    "match_scope",
    "occurrence_id",
    "page_sequence",
    "retrieval_channel",
    "role",
    "role_kind",
    "source_line_indices",
    "status",
    "within_role",
}
_RETRIEVAL_FIELDS = {
    "alias_candidates",
    "alias_candidates_sha256",
    "channel",
    "match_kind",
    "normalized_surface",
    "surface",
}
_EXACT_FIELDS = {
    "alias_normalized",
    "alias_pointer",
    "alias_sha256",
    "channel",
    "context_binding",
    "context_binding_sha256",
    "normalized_surface",
    "source_surface",
    "source_surface_sha256",
    "transform",
}
_CONTEXT_FIELDS = {
    "family_id",
    "family_parent",
    "occurrence_id",
    "parent_resolution",
    "scope_owner_occurrence_id",
    "selected_region_sha256",
    "structural_parent",
    "within_role",
}
_STATUSES = {
    "EXACT_SOURCE_AUTHORITY_BOUND",
    "NOT_REQUIRED_NO_SELECTED_ONE_EDIT_RETRIEVAL",
    "UNRESOLVED_SELECTED_ONE_EDIT_WITHOUT_EXACT_SOURCE_AUTHORITY",
}
_CHECK_STATUSES = {
    "BOUND_SOURCE_TEXT_REMAINS_ONE_EDIT_NOT_EXACT",
    "EXACT_ALIAS_DIFFERENT_SOURCE_SPAN",
    "EXACT_FAMILY_PARENT_CONTEXT_MISMATCH",
    "EXACT_SOURCE_ROLE_CONTEXT_SPAN_BOUND",
    "EXACT_STRUCTURAL_PARENT_CONTEXT_MISMATCH",
    "MISSING_BOUND_SOURCE_TEXT",
    "NO_EXACT_DECLARED_ALIAS_ON_RETRIEVAL_SOURCE_SPAN",
    "RETRIEVAL_ONE_EDIT_ALIAS_SPEC_BINDING_DRIFTED",
}


class AccountingFamilyOneEditExactAuthorityV1Error(ValueError):
    """The selected match, exact source channel, spec, or receipt drifted."""


def _error(message: str) -> AccountingFamilyOneEditExactAuthorityV1Error:
    return AccountingFamilyOneEditExactAuthorityV1Error(message)


def _is_one_edit(match: Mapping[str, Any]) -> bool:
    return str(match.get("match_kind", "")).startswith("ONE_EDIT_ALIAS")


def _match_line_indices(
    match: Mapping[str, Any], pages: Sequence[Mapping[str, Any]]
) -> tuple[int, ...]:
    page_sequence = match.get("page_sequence")
    page = next((item for item in pages if item["page_sequence"] == page_sequence), None)
    if page is None:
        raise _error("selected one-edit match page is absent from the complete source axis")
    start = match.get("source_line_index")
    stop = match.get("end_source_line_index")
    if type(start) is not int or type(stop) is not int or stop < start:
        raise _error("selected one-edit match source span drifted")
    positions = {line["source_line_index"]: position for position, line in enumerate(page["lines"])}
    if start not in positions or stop not in positions or positions[stop] < positions[start]:
        raise _error("selected one-edit match source span is absent from its bound page")
    explicit = match.get("source_line_indices")
    if explicit is None:
        result = tuple(
            line["source_line_index"]
            for line in page["lines"][positions[start] : positions[stop] + 1]
        )
    else:
        if (
            type(explicit) is not list
            or not explicit
            or any(type(index) is not int for index in explicit)
            or len(explicit) != len(set(explicit))
            or explicit[0] != start
            or explicit[-1] != stop
            or any(index not in positions for index in explicit)
            or explicit != sorted(explicit, key=positions.__getitem__)
        ):
            raise _error("selected one-edit noncontiguous source-line identity drifted")
        result = tuple(explicit)
    if not result:
        raise _error("selected one-edit match retained an empty source-line span")
    return result


def _match_identity(match: Mapping[str, Any], pages: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "document_line_span": [
            match.get("document_line_ordinal"),
            match.get("end_document_line_ordinal"),
        ],
        "occurrence_id": match.get("occurrence_id"),
        "page_sequence": match.get("page_sequence"),
        "role": match.get("role"),
        "source_line_indices": list(_match_line_indices(match, pages)),
        "scope_owner_occurrence_id": match.get("scope_owner_occurrence_id"),
        "within_role": match.get("matched_within_role"),
    }


def _same_match_span(
    left: Mapping[str, Any], right: Mapping[str, Any], pages: Sequence[Mapping[str, Any]]
) -> bool:
    return (
        left.get("page_sequence") == right.get("page_sequence")
        and left.get("document_line_ordinal") == right.get("document_line_ordinal")
        and left.get("end_document_line_ordinal") == right.get("end_document_line_ordinal")
        and _match_line_indices(left, pages) == _match_line_indices(right, pages)
    )


def _source_surface(match: Mapping[str, Any], pages: Sequence[Mapping[str, Any]]) -> str | None:
    page = next(item for item in pages if item["page_sequence"] == match["page_sequence"])
    by_index = {line["source_line_index"]: line for line in page["lines"]}
    values = [by_index[index]["source_text"] for index in _match_line_indices(match, pages)]
    if any(type(value) is not str or not value.strip() for value in values):
        return None
    return " ".join(value.strip() for value in values).strip()


def _exact_axes(surface: str) -> list[tuple[str, str]]:
    axes = [("ACCENTLESS", normalize_vietnamese_anchor_v1(surface))]
    stripped = topology_v1._ENUMERATION_PREFIX.sub("", surface, count=1)  # noqa: SLF001
    if stripped != surface:
        axes.append(
            (
                "ACCENTLESS_AFTER_ENUMERATION_PREFIX",
                normalize_vietnamese_anchor_v1(stripped),
            )
        )
    decorative = topology_v1._without_decorative_parentheticals(surface)  # noqa: SLF001
    if decorative != surface:
        axes.append(
            (
                "ACCENTLESS_AFTER_DECORATIVE_PARENTHETICAL_REMOVAL",
                normalize_vietnamese_anchor_v1(decorative),
            )
        )
    decorative_stripped = topology_v1._ENUMERATION_PREFIX.sub(  # noqa: SLF001
        "", decorative, count=1
    )
    if decorative_stripped != decorative:
        axes.append(
            (
                "ACCENTLESS_AFTER_ENUMERATION_PREFIX_AND_DECORATIVE_PARENTHETICAL_REMOVAL",
                normalize_vietnamese_anchor_v1(decorative_stripped),
            )
        )
    deduplicated: list[tuple[str, str]] = []
    seen = set()
    for transform, normalized in axes:
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduplicated.append((transform, normalized))
    return deduplicated


def _alias_entries(
    compiled: Mapping[str, Any], *, role: str, within_role: str | None
) -> list[dict[str, str]]:
    if role == compiled["parent"]["role"]:
        return [
            {
                "alias": alias,
                "pointer": f"/parent/aliases/{alias_ordinal}",
            }
            for alias_ordinal, alias in enumerate(compiled["parent"]["aliases"])
        ]
    children = [
        (child_ordinal, child)
        for child_ordinal, child in enumerate(compiled["children"])
        if child["role"] == role
    ]
    if len(children) != 1:
        return []
    child_ordinal, child = children[0]
    if compiled["spec_format_version"] != topology_v1.SPEC_FORMAT_VERSION_V3:
        matcher = child["matchers"][0]
        if matcher["within_role"] != within_role:
            return []
        return [
            {
                "alias": alias,
                "pointer": f"/children/{child_ordinal}/aliases/{alias_ordinal}",
            }
            for alias_ordinal, alias in enumerate(matcher["aliases"])
        ]
    return [
        {
            "alias": alias,
            "pointer": (
                f"/children/{child_ordinal}/matchers/{matcher_ordinal}/aliases/{alias_ordinal}"
            ),
        }
        for matcher_ordinal, matcher in enumerate(child["matchers"])
        if matcher["within_role"] == within_role
        for alias_ordinal, alias in enumerate(matcher["aliases"])
    ]


def _retrieval_alias_candidates(
    match: Mapping[str, Any], aliases: Sequence[Mapping[str, str]]
) -> list[dict[str, str]]:
    transform_by_kind = {
        "ONE_EDIT_ALIAS_REQUIRES_COMPLETE_TOPOLOGY": "ACCENTLESS",
        "ONE_EDIT_ALIAS_AFTER_ENUMERATION_PREFIX_REQUIRES_COMPLETE_TOPOLOGY": (
            "ACCENTLESS_AFTER_ENUMERATION_PREFIX"
        ),
        "ONE_EDIT_ALIAS_AFTER_DECORATIVE_PARENTHETICAL_REMOVAL_REQUIRES_COMPLETE_TOPOLOGY": (
            "ACCENTLESS_AFTER_DECORATIVE_PARENTHETICAL_REMOVAL"
        ),
        "ONE_EDIT_ALIAS_AFTER_ENUMERATION_PREFIX_AND_DECORATIVE_PARENTHETICAL_REMOVAL_REQUIRES_COMPLETE_TOPOLOGY": (
            "ACCENTLESS_AFTER_ENUMERATION_PREFIX_AND_DECORATIVE_PARENTHETICAL_REMOVAL"
        ),
    }
    selected_transform = transform_by_kind.get(match.get("match_kind"))
    candidates = []
    for transform, normalized in _exact_axes(str(match.get("surface", ""))):
        if transform != selected_transform:
            continue
        for alias in aliases:
            if normalized != alias["alias"] and topology_v1._one_edit_alias_is_safe(  # noqa: SLF001
                normalized, alias["alias"]
            ):
                candidates.append(dict(alias))
    return sorted(
        {item["pointer"]: item for item in candidates}.values(),
        key=lambda item: item["pointer"],
    )


def _exact_alias_bindings(
    surface: str, aliases: Sequence[Mapping[str, str]]
) -> list[dict[str, str]]:
    bindings = []
    for transform, normalized in _exact_axes(surface):
        for alias in aliases:
            if normalized == alias["alias"]:
                bindings.append({**dict(alias), "transform": transform})
    return sorted(
        {item["pointer"]: item for item in bindings}.values(),
        key=lambda item: item["pointer"],
    )


def _source_exact_axes(
    pages: Sequence[Mapping[str, Any]], compiled: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source_pages = [
        {
            "lines": [
                {
                    "bbox": canonical_clone_v1(line["bbox"]),
                    "normalized_text": normalize_vietnamese_anchor_v1(
                        line["source_text"] if type(line["source_text"]) is str else ""
                    ),
                    "source_line_index": line["source_line_index"],
                    "source_text": None,
                    "vietocr_text": (
                        line["source_text"] if type(line["source_text"]) is str else ""
                    ),
                }
                for line in page["lines"]
            ],
            "page_sequence": page["page_sequence"],
        }
        for page in pages
    ]
    hits, _line_axis, _page_axis = topology_v1._document_hits(  # noqa: SLF001
        source_pages, compiled
    )
    exact_hits = {
        "children": {
            role: [
                hit
                for hit in records
                if str(hit.get("match_kind", "")).startswith("EXACT_ACCENTLESS_ALIAS")
            ]
            for role, records in hits["children"].items()
        },
        "parents": [
            hit
            for hit in hits["parents"]
            if str(hit.get("match_kind", "")).startswith("EXACT_ACCENTLESS_ALIAS")
        ],
    }
    return exact_hits, source_pages


def _context_bound_source_records(
    exact_hits: Mapping[str, Any],
    compiled: Mapping[str, Any],
    selected_region: Mapping[str, Any],
) -> list[dict[str, Any]]:
    return topology_v1._child_records_in_range(  # noqa: SLF001
        exact_hits["children"],
        compiled,
        retain_all_occurrences=True,
        start=selected_region["cluster_start_document_line_ordinal"],
        stop=selected_region["cluster_end_document_line_ordinal_exclusive"],
    )


def _nearest_selected_owner(
    match: Mapping[str, Any], effective_matches: Sequence[Mapping[str, Any]]
) -> Mapping[str, Any] | None:
    owner_id = match.get("scope_owner_occurrence_id")
    if owner_id is not None:
        selected = [item for item in effective_matches if item.get("occurrence_id") == owner_id]
        if len(selected) == 1:
            return selected[0]
    within_role = match.get("matched_within_role")
    if within_role is None:
        return None
    preceding = [
        item
        for item in effective_matches
        if item.get("role") == within_role
        and item.get("document_line_ordinal", -1) <= match.get("document_line_ordinal", -1)
        and item is not match
    ]
    return max(
        preceding,
        key=lambda item: (
            item.get("document_line_ordinal", -1),
            item.get("end_document_line_ordinal", -1),
        ),
        default=None,
    )


def _empty_exact_channel(
    *, source_surface: str | None, context_binding: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "alias_normalized": None,
        "alias_pointer": None,
        "alias_sha256": None,
        "channel": "PPOCR_BOUND_SOURCE_TEXT_EXACT",
        "context_binding": canonical_clone_v1(context_binding),
        "context_binding_sha256": canonical_json_sha256_v1(context_binding),
        "normalized_surface": (
            normalize_vietnamese_anchor_v1(source_surface) if source_surface is not None else None
        ),
        "source_surface": source_surface,
        "source_surface_sha256": (
            canonical_json_sha256_v1(source_surface) if source_surface is not None else None
        ),
        "transform": None,
    }


def _check(
    match: Mapping[str, Any],
    *,
    aliases: Sequence[Mapping[str, str]],
    compiled: Mapping[str, Any],
    effective_matches: Sequence[Mapping[str, Any]],
    exact_hits: Mapping[str, Any],
    pages: Sequence[Mapping[str, Any]],
    selected_region: Mapping[str, Any],
    source_records: Sequence[Mapping[str, Any]],
    match_scope: str,
) -> dict[str, Any]:
    indices = _match_line_indices(match, pages)
    role = compiled["parent"]["role"] if match_scope == "FAMILY_PARENT" else match["role"]
    within_role = None if match_scope == "FAMILY_PARENT" else match.get("matched_within_role")
    occurrence_id = None if match_scope == "FAMILY_PARENT" else match.get("occurrence_id")
    retrieval_candidates = _retrieval_alias_candidates(match, aliases)
    retrieval_alias_axis = [
        {
            "alias_normalized": item["alias"],
            "alias_pointer": item["pointer"],
            "alias_sha256": canonical_json_sha256_v1(item["alias"]),
        }
        for item in retrieval_candidates
    ]
    retrieval = {
        "alias_candidates": retrieval_alias_axis,
        "alias_candidates_sha256": canonical_json_sha256_v1(retrieval_alias_axis),
        "channel": "VIETOCR_TRANSFORMER_RETRIEVAL_ONLY",
        "match_kind": match["match_kind"],
        "normalized_surface": normalize_vietnamese_anchor_v1(match["surface"]),
        "surface": match["surface"],
    }
    selected_parent = selected_region.get("parent_match")
    owner = _nearest_selected_owner(match, effective_matches)
    context_binding = {
        "family_id": compiled["family_id"],
        "family_parent": (
            _match_identity(selected_parent, pages) if selected_parent is not None else None
        ),
        "occurrence_id": occurrence_id,
        "parent_resolution": selected_region["parent_resolution"],
        "scope_owner_occurrence_id": (
            None if match_scope == "FAMILY_PARENT" else match.get("scope_owner_occurrence_id")
        ),
        "selected_region_sha256": canonical_json_sha256_v1(selected_region),
        "structural_parent": _match_identity(owner, pages) if owner is not None else None,
        "within_role": within_role,
    }
    surface = _source_surface(match, pages)
    exact_channel = _empty_exact_channel(
        source_surface=surface,
        context_binding=context_binding,
    )
    status = "RETRIEVAL_ONE_EDIT_ALIAS_SPEC_BINDING_DRIFTED"
    if retrieval_candidates and surface is None:
        status = "MISSING_BOUND_SOURCE_TEXT"
    exact_bindings = _exact_alias_bindings(surface, aliases) if surface is not None else []
    coextensive_parent_child = (
        match_scope == "EXPANDED_OCCURRENCE"
        and selected_parent is not None
        and _same_match_span(match, selected_parent, pages)
    )
    if match_scope == "FAMILY_PARENT":
        source_role_axis = exact_hits["parents"]
    elif coextensive_parent_child:
        source_role_axis = [
            {
                **canonical_clone_v1(item),
                "matched_within_role": item.get("_within_role"),
                "role": role,
            }
            for item in exact_hits["children"].get(role, [])
        ]
    else:
        source_role_axis = [item for item in source_records if item["role"] == role]
    same_role_context_span = [
        item
        for item in source_role_axis
        if (
            (match_scope == "FAMILY_PARENT" or item.get("matched_within_role") == within_role)
            and _same_match_span(item, match, pages)
        )
    ]
    exact_parent = (
        None
        if selected_parent is None
        else next(
            (
                item
                for item in exact_hits["parents"]
                if _same_match_span(item, selected_parent, pages)
                and _exact_alias_bindings(
                    _source_surface(selected_parent, pages) or "",
                    _alias_entries(
                        compiled,
                        role=compiled["parent"]["role"],
                        within_role=None,
                    ),
                )
            ),
            None,
        )
    )
    exact_owner = None
    if owner is not None:
        exact_owner = next(
            (
                item
                for item in source_records
                if item["role"] == owner["role"] and _same_match_span(item, owner, pages)
            ),
            None,
        )
    if retrieval_candidates and surface is not None:
        if not exact_bindings:
            if any(
                topology_v1._one_edit_alias_is_safe(  # noqa: SLF001
                    normalized, alias["alias"]
                )
                and normalized != alias["alias"]
                for _transform, normalized in _exact_axes(surface)
                for alias in aliases
            ):
                status = "BOUND_SOURCE_TEXT_REMAINS_ONE_EDIT_NOT_EXACT"
            elif any(
                item
                for item in source_role_axis
                if (
                    match_scope == "FAMILY_PARENT" or item.get("matched_within_role") == within_role
                )
            ):
                status = "EXACT_ALIAS_DIFFERENT_SOURCE_SPAN"
            else:
                status = "NO_EXACT_DECLARED_ALIAS_ON_RETRIEVAL_SOURCE_SPAN"
        elif selected_parent is not None and exact_parent is None:
            status = "EXACT_FAMILY_PARENT_CONTEXT_MISMATCH"
        elif owner is not None and exact_owner is None:
            status = "EXACT_STRUCTURAL_PARENT_CONTEXT_MISMATCH"
        elif len(exact_bindings) != 1 or len(same_role_context_span) != 1:
            # An exact surface under another role/parent or on another span is
            # not independent corroboration of this selected retrieval match.
            status = (
                "EXACT_ALIAS_DIFFERENT_SOURCE_SPAN"
                if any(
                    item
                    for item in source_role_axis
                    if (
                        match_scope == "FAMILY_PARENT"
                        or item.get("matched_within_role") == within_role
                    )
                )
                else "NO_EXACT_DECLARED_ALIAS_ON_RETRIEVAL_SOURCE_SPAN"
            )
        else:
            binding = exact_bindings[0]
            status = "EXACT_SOURCE_ROLE_CONTEXT_SPAN_BOUND"
            exact_channel.update(
                {
                    "alias_normalized": binding["alias"],
                    "alias_pointer": binding["pointer"],
                    "alias_sha256": canonical_json_sha256_v1(binding["alias"]),
                    "normalized_surface": binding["alias"],
                    "transform": binding["transform"],
                }
            )
    role_kind = (
        "FAMILY_PARENT" if match_scope == "FAMILY_PARENT" else str(match.get("role_kind", ""))
    )
    return {
        "exact_channel": exact_channel,
        "match_scope": match_scope,
        "occurrence_id": occurrence_id,
        "page_sequence": match["page_sequence"],
        "retrieval_channel": retrieval,
        "role": role,
        "role_kind": role_kind,
        "source_line_indices": list(indices),
        "status": status,
        "within_role": within_role,
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _RESULT_FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["authority_spec"]) is not dict
        or set(value["authority_spec"]) != {"sha256", "value"}
        or not same_typed_json_v1(value["authority_spec"]["value"], _AUTHORITY_SPEC)
        or value["authority_spec"]["sha256"] != canonical_json_sha256_v1(_AUTHORITY_SPEC)
        or type(value["family_id"]) is not str
        or not value["family_id"]
        or type(value["input_binding"]) is not dict
        or set(value["input_binding"]) != _INPUT_BINDING_FIELDS
        or any(
            type(item) is not str
            or len(item) != 64
            or any(character not in "0123456789abcdef" for character in item)
            for item in value["input_binding"].values()
        )
        or type(value["metrics"]) is not dict
        or set(value["metrics"]) != _METRIC_FIELDS
        or any(type(item) is not int or item < 0 for item in value["metrics"].values())
        or type(value["checks"]) is not list
        or value["status"] not in _STATUSES
        or type(value["unresolved_reasons"]) is not list
        or any(type(reason) is not str or not reason for reason in value["unresolved_reasons"])
    ):
        raise _error("one-edit exact-authority receipt shape drifted")
    for check in value["checks"]:
        exact = check.get("exact_channel") if type(check) is dict else None
        retrieval = check.get("retrieval_channel") if type(check) is dict else None
        if (
            type(check) is not dict
            or set(check) != _CHECK_FIELDS
            or check["match_scope"] not in {"EXPANDED_OCCURRENCE", "FAMILY_PARENT"}
            or (check["match_scope"] == "FAMILY_PARENT" and check["occurrence_id"] is not None)
            or (
                check["match_scope"] == "EXPANDED_OCCURRENCE"
                and (type(check["occurrence_id"]) is not str or not check["occurrence_id"])
            )
            or type(check["role"]) is not str
            or not check["role"]
            or type(check["role_kind"]) is not str
            or not check["role_kind"]
            or (
                check["within_role"] is not None
                and (type(check["within_role"]) is not str or not check["within_role"])
            )
            or type(check["page_sequence"]) is not int
            or check["page_sequence"] <= 0
            or type(check["source_line_indices"]) is not list
            or not check["source_line_indices"]
            or any(type(index) is not int or index < 0 for index in check["source_line_indices"])
            or check["status"] not in _CHECK_STATUSES
            or type(retrieval) is not dict
            or set(retrieval) != _RETRIEVAL_FIELDS
            or retrieval["channel"] != "VIETOCR_TRANSFORMER_RETRIEVAL_ONLY"
            or not str(retrieval["match_kind"]).startswith("ONE_EDIT_ALIAS")
            or type(retrieval["alias_candidates"]) is not list
            or any(
                type(alias) is not dict
                or set(alias) != {"alias_normalized", "alias_pointer", "alias_sha256"}
                or type(alias["alias_normalized"]) is not str
                or not alias["alias_normalized"]
                or type(alias["alias_pointer"]) is not str
                or not alias["alias_pointer"]
                or alias["alias_sha256"] != canonical_json_sha256_v1(alias["alias_normalized"])
                for alias in retrieval["alias_candidates"]
            )
            or retrieval["alias_candidates_sha256"]
            != canonical_json_sha256_v1(retrieval["alias_candidates"])
            or type(exact) is not dict
            or set(exact) != _EXACT_FIELDS
            or exact["channel"] != "PPOCR_BOUND_SOURCE_TEXT_EXACT"
            or type(exact["context_binding"]) is not dict
            or set(exact["context_binding"]) != _CONTEXT_FIELDS
            or exact["context_binding"]["family_id"] != value["family_id"]
            or exact["context_binding"].get("occurrence_id") != check["occurrence_id"]
            or exact["context_binding"].get("within_role") != check["within_role"]
            or exact["context_binding"]["selected_region_sha256"]
            != value["input_binding"]["selected_topology_region_sha256"]
            or (
                check["match_scope"] == "FAMILY_PARENT"
                and exact["context_binding"]["scope_owner_occurrence_id"] is not None
            )
            or (
                exact["context_binding"]["structural_parent"] is not None
                and exact["context_binding"]["structural_parent"].get("occurrence_id")
                != exact["context_binding"]["scope_owner_occurrence_id"]
            )
            or exact["context_binding_sha256"] != canonical_json_sha256_v1(exact["context_binding"])
            or (exact["source_surface"] is None and exact["source_surface_sha256"] is not None)
            or (
                exact["source_surface"] is not None
                and exact["source_surface_sha256"]
                != canonical_json_sha256_v1(exact["source_surface"])
            )
            or (
                check["status"] == "EXACT_SOURCE_ROLE_CONTEXT_SPAN_BOUND"
                and (
                    exact["alias_pointer"] is None
                    or exact["alias_normalized"] is None
                    or exact["alias_sha256"] != canonical_json_sha256_v1(exact["alias_normalized"])
                    or exact["transform"] not in _AUTHORITY_SPEC["allowed_exact_transforms"]
                )
            )
        ):
            raise _error("one-edit exact-authority check axis drifted")
    bound = sum(
        check["status"] == "EXACT_SOURCE_ROLE_CONTEXT_SPAN_BOUND" for check in value["checks"]
    )
    occurrence_ids = [
        check["occurrence_id"]
        for check in value["checks"]
        if check["match_scope"] == "EXPANDED_OCCURRENCE"
    ]
    if len(occurrence_ids) != len(set(occurrence_ids)):
        raise _error("one-edit exact-authority occurrence identity repeats")
    metrics = {
        "exact_bound_count": bound,
        "selected_one_edit_match_count": len(value["checks"]),
        "unresolved_match_count": len(value["checks"]) - bound,
    }
    expected_status = (
        "NOT_REQUIRED_NO_SELECTED_ONE_EDIT_RETRIEVAL"
        if not value["checks"]
        else "EXACT_SOURCE_AUTHORITY_BOUND"
        if bound == len(value["checks"])
        else "UNRESOLVED_SELECTED_ONE_EDIT_WITHOUT_EXACT_SOURCE_AUTHORITY"
    )
    expected_reasons = [
        (
            f"ONE_EDIT_EXACT_AUTHORITY:{check['status']}:{check['role']}:"
            f"OCCURRENCE_{check['occurrence_id'] or 'FAMILY_PARENT'}:"
            f"PAGE_{check['page_sequence']}:LINES_"
            + ",".join(str(index) for index in check["source_line_indices"])
        )
        for check in value["checks"]
        if check["status"] != "EXACT_SOURCE_ROLE_CONTEXT_SPAN_BOUND"
    ]
    if (
        not same_typed_json_v1(value["metrics"], metrics)
        or value["status"] != expected_status
        or value["unresolved_reasons"] != expected_reasons
    ):
        raise _error("one-edit exact-authority status or metrics drifted")
    material = canonical_clone_v1(value)
    receipt_id = material.pop("receipt_id")
    if receipt_id != "afeoeav1:receipt:" + canonical_json_sha256_v1(material):
        raise _error("one-edit exact-authority receipt identity drifted")
    return canonical_clone_v1(value)


def build_accounting_family_one_edit_exact_authority_v1(
    document_pages: Any,
    family_spec: Any,
    selected_topology_region: Any,
    expanded_occurrence_region: Any,
) -> dict[str, Any]:
    """Gate one selected V4 candidate and every expanded role occurrence."""

    try:
        pages = topology_v1._pages(document_pages)  # noqa: SLF001
        compiled = topology_v1._spec(family_spec)  # noqa: SLF001
    except (ValueError, RuntimeError) as exc:
        raise _error("one-edit exact-authority document or family spec drifted") from exc
    if (
        type(selected_topology_region) is not dict
        or type(expanded_occurrence_region) is not dict
        or not same_typed_json_v1(
            selected_topology_region.get("parent_match"),
            expanded_occurrence_region.get("parent_match"),
        )
        or any(
            selected_topology_region.get(field) != expanded_occurrence_region.get(field)
            for field in (
                "cluster_end_document_line_ordinal_exclusive",
                "cluster_start_document_line_ordinal",
                "parent_resolution",
            )
        )
        or type(expanded_occurrence_region.get("child_matches")) is not list
    ):
        raise _error("one-edit exact-authority selected/expanded region binding drifted")
    selected_parent = selected_topology_region.get("parent_match")
    effective_matches = expanded_occurrence_region["child_matches"]
    occurrence_ids = [
        match.get("occurrence_id") if type(match) is dict else None for match in effective_matches
    ]
    if (
        any(type(occurrence_id) is not str or not occurrence_id for occurrence_id in occurrence_ids)
        or len(occurrence_ids) != len(set(occurrence_ids))
        or any(
            type(match.get("scope_owner_occurrence_id")) is not str
            or not match["scope_owner_occurrence_id"]
            or match.get("matched_within_role") != match.get("scope_owner_role")
            or (
                match.get("scope_owner_role") is not None
                and (type(match["scope_owner_role"]) is not str or not match["scope_owner_role"])
            )
            for match in effective_matches
        )
    ):
        raise _error("one-edit exact-authority expanded occurrence identity axis drifted")
    occurrence_by_id = {match["occurrence_id"]: match for match in effective_matches}
    if any(
        match["scope_owner_role"] is not None
        and (
            match["scope_owner_occurrence_id"] not in occurrence_by_id
            or occurrence_by_id[match["scope_owner_occurrence_id"]].get("role")
            != match["scope_owner_role"]
        )
        for match in effective_matches
    ):
        raise _error("one-edit exact-authority expanded structural-owner axis drifted")
    selected_matches: list[tuple[str, Mapping[str, Any]]] = []
    if selected_parent is not None and _is_one_edit(selected_parent):
        selected_matches.append(("FAMILY_PARENT", selected_parent))
    selected_matches.extend(
        ("EXPANDED_OCCURRENCE", match) for match in effective_matches if _is_one_edit(match)
    )
    exact_hits, _source_pages = _source_exact_axes(pages, compiled)
    source_records = _context_bound_source_records(
        exact_hits,
        compiled,
        selected_topology_region,
    )
    checks = []
    for match_scope, match in selected_matches:
        role = compiled["parent"]["role"] if match_scope == "FAMILY_PARENT" else match.get("role")
        within_role = None if match_scope == "FAMILY_PARENT" else match.get("matched_within_role")
        checks.append(
            _check(
                match,
                aliases=_alias_entries(compiled, role=role, within_role=within_role),
                compiled=compiled,
                effective_matches=effective_matches,
                exact_hits=exact_hits,
                pages=pages,
                selected_region=selected_topology_region,
                source_records=source_records,
                match_scope=match_scope,
            )
        )
    bound = sum(check["status"] == "EXACT_SOURCE_ROLE_CONTEXT_SPAN_BOUND" for check in checks)
    metrics = {
        "exact_bound_count": bound,
        "selected_one_edit_match_count": len(checks),
        "unresolved_match_count": len(checks) - bound,
    }
    reasons = [
        (
            f"ONE_EDIT_EXACT_AUTHORITY:{check['status']}:{check['role']}:"
            f"OCCURRENCE_{check['occurrence_id'] or 'FAMILY_PARENT'}:"
            f"PAGE_{check['page_sequence']}:LINES_"
            + ",".join(str(index) for index in check["source_line_indices"])
        )
        for check in checks
        if check["status"] != "EXACT_SOURCE_ROLE_CONTEXT_SPAN_BOUND"
    ]
    material = {
        "authority_spec": {
            "sha256": canonical_json_sha256_v1(_AUTHORITY_SPEC),
            "value": canonical_clone_v1(_AUTHORITY_SPEC),
        },
        "checks": checks,
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": compiled["family_id"],
        "format_version": FORMAT_VERSION,
        "input_binding": {
            "document_pages_sha256": canonical_json_sha256_v1(document_pages),
            "expanded_occurrence_region_sha256": canonical_json_sha256_v1(
                expanded_occurrence_region
            ),
            "family_spec_sha256": canonical_json_sha256_v1(family_spec),
            "selected_topology_region_sha256": canonical_json_sha256_v1(selected_topology_region),
        },
        "metrics": metrics,
        "safety": canonical_clone_v1(_SAFETY),
        "status": (
            "NOT_REQUIRED_NO_SELECTED_ONE_EDIT_RETRIEVAL"
            if not checks
            else "EXACT_SOURCE_AUTHORITY_BOUND"
            if not reasons
            else "UNRESOLVED_SELECTED_ONE_EDIT_WITHOUT_EXACT_SOURCE_AUTHORITY"
        ),
        "unresolved_reasons": reasons,
    }
    return _validate_result(
        {
            **material,
            "receipt_id": "afeoeav1:receipt:" + canonical_json_sha256_v1(material),
        }
    )


def validate_accounting_family_one_edit_exact_authority_receipt_shape_v1(
    value: Any,
) -> dict[str, Any]:
    """Validate a closed receipt and all of its internal content hashes."""

    return _validate_result(value)


def validate_accounting_family_one_edit_exact_authority_replay_v1(
    value: Any,
    document_pages: Any,
    family_spec: Any,
    selected_topology_region: Any,
    expanded_occurrence_region: Any,
) -> dict[str, Any]:
    """Exact-rebuild a receipt from bound source text and the selected region."""

    persisted = _validate_result(value)
    expected = build_accounting_family_one_edit_exact_authority_v1(
        document_pages,
        family_spec,
        selected_topology_region,
        expanded_occurrence_region,
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("one-edit exact-authority receipt does not replay exactly")
    return persisted
