"""Exact second-channel authority for selected one-edit topology anchors.

The topology reader may use one edit to *retrieve* a plausible family region.
That tolerance is deliberately not accounting or mapping authority.  This
module closes that gap for V4 callers: after downstream evidence has selected
one candidate, every selected parent/expanded-occurrence one-edit match must be
re-observed as an exact declared alias on the identical bound source-text
lines, in the identical family/role/recursive structural-owner context.
Expanded children are bound by occurrence ID so one exact occurrence can
never corroborate a fuzzy repetition of the same role.

Only accent removal/case/punctuation normalization, an enumeration prefix,
and the topology engine's bounded decorative parenthetical removal are exact
transforms here.  Edit distance is never consulted by the authority channel.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.evaluation import accounting_family_occurrence_row_axis_v2 as occurrence_row_v2
from bctc_ai.evaluation import accounting_family_topology_candidates_v2 as candidates_v2
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
    "BOUND_SOURCE_TEXT_ALIAS_ON_IDENTICAL_OCCURRENCE_FAMILY_ROLE_RECURSIVE_PARENT_CHAIN_"
    "PAGE_AND_LINE_SPAN_NO_NUMERIC_SCHEMA_MAPPING_OR_DISCARDED_CANDIDATE_VETO_AUTHORITY"
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
    "exact_alias_requires_same_recursive_nearest_structural_owner_chain": True,
    "exact_source_occurrence_axis": "PPOCR_EXACT_DECLARED_ALIASES_ONLY",
    "one_edit_channel": "VIETOCR_TRANSFORMER_RETRIEVAL_ONLY",
    "selected_candidate_only": True,
}
_SAFETY = {
    "bank_file_page_period_scope_used_for_routing": False,
    "discarded_or_near_one_edit_match_can_veto_selected_candidate": False,
    "mapping_authority": False,
    "one_edit_similarity_can_grant_exact_authority": False,
    "schema_authority": False,
    "same_role_span_with_different_parent_context_can_authorize": False,
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


def _pages_with_occurrence_geometry_v1(document_pages: Any) -> list[dict[str, Any]]:
    """Parse topology fields while retaining production occurrence evidence.

    The public authority input may carry the canonical numeric-recognizer
    record used by occurrence geometry.  It is excluded from topology text
    retrieval, but retained byte-for-byte for the coextensive/wrapped-row
    replay so a fabricated score or stripped page cannot change that replay.
    """

    if type(document_pages) is not list:
        raise _error("one-edit exact-authority document pages drifted")
    topology_pages = []
    widths = []
    numeric_axes = []
    for raw_page in document_pages:
        if type(raw_page) is not dict or set(raw_page) not in (
            {"lines", "page_sequence"},
            {"lines", "page_sequence", "page_width"},
        ):
            raise _error("one-edit exact-authority document page drifted")
        width = raw_page.get("page_width")
        if width is not None and (type(width) is not int or width <= 0):
            raise _error("one-edit exact-authority page width drifted")
        if type(raw_page.get("lines")) is not list:
            raise _error("one-edit exact-authority document line axis drifted")
        topology_lines = []
        numeric_axis = []
        for raw_line in raw_page["lines"]:
            if type(raw_line) is not dict or set(raw_line) not in (
                {"bbox", "source_line_index", "source_text", "vietocr_text"},
                {
                    "bbox",
                    "numeric_recognition",
                    "source_line_index",
                    "source_text",
                    "vietocr_text",
                },
            ):
                raise _error("one-edit exact-authority document line drifted")
            numeric_recognition = raw_line.get("numeric_recognition")
            if numeric_recognition is not None and (
                type(numeric_recognition) is not dict
                or type(numeric_recognition.get("raw_prediction")) is not str
            ):
                raise _error("one-edit exact-authority numeric recognition drifted")
            topology_lines.append(
                {
                    "bbox": canonical_clone_v1(raw_line["bbox"]),
                    "source_line_index": raw_line["source_line_index"],
                    "source_text": raw_line["source_text"],
                    "vietocr_text": raw_line["vietocr_text"],
                }
            )
            numeric_axis.append(canonical_clone_v1(numeric_recognition))
        topology_pages.append(
            {
                "lines": topology_lines,
                "page_sequence": raw_page.get("page_sequence"),
            }
        )
        widths.append(width)
        numeric_axes.append(numeric_axis)
    pages = topology_v1._pages(topology_pages)  # noqa: SLF001
    for page, width, numeric_axis in zip(pages, widths, numeric_axes, strict=True):
        page["page_width"] = width
        for line, numeric_recognition in zip(page["lines"], numeric_axis, strict=True):
            if numeric_recognition is not None:
                line["numeric_recognition"] = numeric_recognition
    return pages


def _retrieval_only_pages_v1(
    pages: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Rebuild the exact page contract used by V2 topology retrieval."""

    return [
        {
            "lines": [
                {
                    "bbox": canonical_clone_v1(line["bbox"]),
                    "source_line_index": line["source_line_index"],
                    # PP-OCR is the independent exact-authority channel.  It
                    # must never participate in the retrieval replay.
                    "source_text": None,
                    "vietocr_text": line["vietocr_text"],
                }
                for line in page["lines"]
            ],
            "page_sequence": page["page_sequence"],
        }
        for page in pages
    ]


def _occurrence_row_pages_v1(
    pages: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Project the complete fields consumed by occurrence expansion.

    Occurrence expansion is semantic, but it also uses exact same-row numeric
    evidence to reject a heading-only coextensive total and to distinguish an
    independently complete row from a wrapped label.  Stripping the PP-OCR
    source text here made the independent replay crash on those legitimate V4
    shapes.  The source channel remains retrieval-inert: it is exposed only as
    ``numeric_recognition`` to the occurrence geometry predicates, never as
    topology match input.
    """

    return [
        {
            "lines": [
                {
                    "bbox": canonical_clone_v1(line["bbox"]),
                    "line_ordinal": line["source_line_index"],
                    "numeric_recognition": canonical_clone_v1(
                        line.get("numeric_recognition")
                        or {
                            "raw_prediction": (
                                line["source_text"] if type(line["source_text"]) is str else ""
                            ),
                            "reader_score": 1.0,
                        }
                    ),
                    "vietocr_text": line["vietocr_text"],
                }
                for line in page["lines"]
            ],
            "page_sequence": page["page_sequence"],
            "page_width": page.get("page_width"),
        }
        for page in pages
    ]


def _expected_occurrence_id_v1(match: Mapping[str, Any]) -> str:
    return "aforav2:occurrence:" + canonical_json_sha256_v1(
        {
            "document_line_ordinal": match["document_line_ordinal"],
            "end_document_line_ordinal": match["end_document_line_ordinal"],
            "page_sequence": match["page_sequence"],
            "role": match["role"],
            "role_occurrence_ordinal": match["role_occurrence_ordinal"],
        }
    )


def _root_scope_id_v1(selected_region: Mapping[str, Any]) -> str:
    return "aforav2:root:" + canonical_json_sha256_v1(
        {
            "end": selected_region["cluster_end_document_line_ordinal_exclusive"],
            "parent_match": selected_region.get("parent_match"),
            "start": selected_region["cluster_start_document_line_ordinal"],
        }
    )


def _physical_occurrence_signature_v1(match: Mapping[str, Any]) -> str:
    """Typed physical identity; distinct coextensive semantic roles remain valid."""

    return canonical_json_sha256_v1(
        {
            "document_line_ordinal": match["document_line_ordinal"],
            "end_document_line_ordinal": match["end_document_line_ordinal"],
            "end_source_line_index": match["end_source_line_index"],
            "page_sequence": match["page_sequence"],
            "role": match["role"],
            "source_line_index": match["source_line_index"],
        }
    )


def _validate_canonical_expanded_occurrence_axis_v1(
    expanded_region: Mapping[str, Any],
    selected_region: Mapping[str, Any],
) -> None:
    """Verify identities and nearest structural owners on the replayed axis."""

    matches = expanded_region.get("child_matches")
    if type(matches) is not list or any(type(match) is not dict for match in matches):
        raise _error("canonical expanded occurrence child axis drifted")
    occurrence_ids = [match.get("occurrence_id") for match in matches]
    physical_signatures = [_physical_occurrence_signature_v1(match) for match in matches]
    if (
        any(
            type(occurrence_id) is not str or occurrence_id != _expected_occurrence_id_v1(match)
            for occurrence_id, match in zip(occurrence_ids, matches, strict=True)
        )
        or len(occurrence_ids) != len(set(occurrence_ids))
        or len(physical_signatures) != len(set(physical_signatures))
    ):
        raise _error("canonical expanded occurrence identity axis drifted")
    undecorated = []
    for match in matches:
        raw = canonical_clone_v1(match)
        raw.pop("occurrence_id", None)
        raw.pop("scope_owner_occurrence_id", None)
        raw.pop("scope_owner_role", None)
        undecorated.append(raw)
    try:
        expected = occurrence_row_v2._decorate_scopes(  # noqa: SLF001
            undecorated,
            selected_region,
        )
    except occurrence_row_v2.AccountingFamilyOccurrenceRowAxisV2Error as exc:
        raise _error("canonical occurrence lost its nearest structural owner") from exc
    if not same_typed_json_v1(matches, expected):
        raise _error("canonical occurrence nearest structural owner drifted")


def _canonical_expanded_occurrence_region_v1(
    pages: Sequence[Mapping[str, Any]],
    family_spec: Mapping[str, Any],
    selected_topology_region: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay the complete selected V2 occurrence authority from source inputs."""

    retrieval_pages = _retrieval_only_pages_v1(pages)
    try:
        prepared = candidates_v2._prepare_accounting_family_topology_candidates_v2(  # noqa: SLF001
            retrieval_pages,
            family_spec,
        )
        topology_scan, topology_candidates, bindings = (
            candidates_v2._prepared_accounting_family_topology_authority_v2(  # noqa: SLF001
                prepared
            )
        )
    except candidates_v2.AccountingFamilyTopologyCandidatesV2Error as exc:
        raise _error("canonical V2 topology candidate replay failed") from exc
    selected_ordinals = [
        ordinal
        for ordinal, region in enumerate(topology_candidates["regions"])
        if same_typed_json_v1(region, selected_topology_region)
    ]
    if len(selected_ordinals) != 1:
        raise _error("selected topology region is not one exact canonical V2 candidate")
    selected_ordinal = selected_ordinals[0]
    canonical_selected = topology_candidates["regions"][selected_ordinal]
    try:
        matches, replayed_selected, effective_region, _topology_candidates_id = (
            occurrence_row_v2._expanded_matches(  # noqa: SLF001
                _occurrence_row_pages_v1(pages),
                family_spec,
                topology_scan,
                canonical_selected,
                None,
                topology_candidates,
                bindings[selected_ordinal],
            )
        )
        if not same_typed_json_v1(replayed_selected, canonical_selected):
            raise _error("selected candidate changed during occurrence replay")
        matches = occurrence_row_v2._attach_schema_scope_source_label_bboxes(  # noqa: SLF001
            _occurrence_row_pages_v1(pages),
            topology_v1._spec(family_spec),  # noqa: SLF001
            matches,
        )
        decorated = occurrence_row_v2._decorate_scopes(  # noqa: SLF001
            matches,
            replayed_selected,
        )
        expanded_region = occurrence_row_v2._expanded_region(  # noqa: SLF001
            effective_region,
            decorated,
        )
    except occurrence_row_v2.AccountingFamilyOccurrenceRowAxisV2Error as exc:
        raise _error("canonical V2 occurrence-axis replay failed") from exc
    _validate_canonical_expanded_occurrence_axis_v1(expanded_region, canonical_selected)
    return canonical_clone_v1(expanded_region)


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


def _source_occurrence_id_v1(match: Mapping[str, Any]) -> str:
    return "afeoeav1:source-occurrence:" + canonical_json_sha256_v1(
        {
            "document_line_ordinal": match["document_line_ordinal"],
            "end_document_line_ordinal": match["end_document_line_ordinal"],
            "matched_within_role": match.get("matched_within_role"),
            "page_sequence": match["page_sequence"],
            "role": match["role"],
            "role_occurrence_ordinal": match["role_occurrence_ordinal"],
            "source_line_index": match["source_line_index"],
            "end_source_line_index": match["end_source_line_index"],
        }
    )


def _decorate_exact_source_occurrences_v1(
    source_records: Sequence[Mapping[str, Any]],
    pages: Sequence[Mapping[str, Any]],
    selected_region: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Give exact PP-OCR records an independent deterministic owner axis."""

    root_scope_id = "afeoeav1:source-root:" + canonical_json_sha256_v1(
        {
            "family_parent": selected_region.get("parent_match"),
            "region_end": selected_region["cluster_end_document_line_ordinal_exclusive"],
            "region_start": selected_region["cluster_start_document_line_ordinal"],
        }
    )
    decorated = []
    for source_record in source_records:
        match = canonical_clone_v1(source_record)
        page = next(item for item in pages if item["page_sequence"] == match["page_sequence"])
        source_line = next(
            line
            for line in page["lines"]
            if line["source_line_index"] == match["source_line_index"]
        )
        match["source_label_bbox"] = canonical_clone_v1(source_line["bbox"])
        match["source_occurrence_id"] = _source_occurrence_id_v1(match)
        decorated.append(match)
    if len({item["source_occurrence_id"] for item in decorated}) != len(decorated):
        raise _error("exact-source occurrence identity repeats")
    for match in decorated:
        within_role = match.get("matched_within_role")
        owners = []
        for candidate in decorated:
            if (
                candidate["role"] != within_role
                or candidate["source_occurrence_id"] == match["source_occurrence_id"]
            ):
                continue
            source_precedes = candidate["document_line_ordinal"] <= match["document_line_ordinal"]
            parent_bbox = candidate["source_label_bbox"]
            child_bbox = match["source_label_bbox"]
            text_height = max(
                parent_bbox[3] - parent_bbox[1],
                child_bbox[3] - child_bbox[1],
            )
            visual_precedes = (
                candidate["page_sequence"] == match["page_sequence"]
                and parent_bbox[1] <= child_bbox[1]
                and parent_bbox[3] <= child_bbox[3]
                and 2 * (child_bbox[1] - parent_bbox[3]) >= -text_height
            )
            if source_precedes or visual_precedes:
                owners.append(candidate)
        owner = max(
            owners,
            key=lambda item: (
                item["page_sequence"],
                item["source_label_bbox"][1],
                item["source_label_bbox"][3],
                item["document_line_ordinal"],
            ),
            default=None,
        )
        match["source_scope_owner_occurrence_id"] = (
            owner["source_occurrence_id"]
            if owner is not None
            else root_scope_id
            if within_role is None
            else None
        )
        match["source_scope_owner_role"] = owner["role"] if owner is not None else None
    return decorated


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


def _nearest_source_owner(
    match: Mapping[str, Any], source_occurrences: Sequence[Mapping[str, Any]]
) -> Mapping[str, Any] | None:
    owner_id = match.get("source_scope_owner_occurrence_id")
    selected = [item for item in source_occurrences if item.get("source_occurrence_id") == owner_id]
    if len(selected) == 1:
        return selected[0]
    return None


def _exact_source_occurrence_matches_retrieval_v1(
    retrieval: Mapping[str, Any],
    source: Mapping[str, Any],
    *,
    compiled: Mapping[str, Any],
    pages: Sequence[Mapping[str, Any]],
) -> bool:
    if (
        source.get("role") != retrieval.get("role")
        or source.get("matched_within_role") != retrieval.get("matched_within_role")
        or not _same_match_span(source, retrieval, pages)
    ):
        return False
    surface = _source_surface(source, pages)
    if surface is None:
        return False
    aliases = _alias_entries(
        compiled,
        role=retrieval["role"],
        within_role=retrieval.get("matched_within_role"),
    )
    return len(_exact_alias_bindings(surface, aliases)) == 1


def _exact_source_owner_chain_matches_retrieval_v1(
    retrieval: Mapping[str, Any],
    source: Mapping[str, Any],
    *,
    compiled: Mapping[str, Any],
    effective_matches: Sequence[Mapping[str, Any]],
    pages: Sequence[Mapping[str, Any]],
    source_occurrences: Sequence[Mapping[str, Any]],
    visited: set[tuple[str, str]] | None = None,
) -> bool:
    """Recursively bind one exact occurrence and every nearest owner."""

    if not _exact_source_occurrence_matches_retrieval_v1(
        retrieval,
        source,
        compiled=compiled,
        pages=pages,
    ):
        return False
    retrieval_id = retrieval.get("occurrence_id")
    source_id = source.get("source_occurrence_id")
    if type(retrieval_id) is not str:
        return False
    pair = (retrieval_id, source_id if type(source_id) is str else "EXACT_RAW_SAME_SPAN")
    seen = set() if visited is None else visited
    if pair in seen:
        return False
    seen.add(pair)
    retrieval_owner = _nearest_selected_owner(retrieval, effective_matches)
    within_role = retrieval.get("matched_within_role")
    if within_role is None:
        return retrieval_owner is None
    if retrieval_owner is None or retrieval_owner.get("role") != within_role:
        return False
    source_owner = _nearest_source_owner(source, source_occurrences)
    # An exact retrieval owner already seals the selected role/parent context
    # and nearest-owner geometry.  Independent PP-OCR exactness is required
    # only for retrieval nodes that themselves used one-edit search.  But an
    # independently exact *contradictory* owner may not be ignored.
    if not _is_one_edit(retrieval_owner):
        return source_owner is None or _exact_source_occurrence_matches_retrieval_v1(
            retrieval_owner,
            source_owner,
            compiled=compiled,
            pages=pages,
        )
    if source_owner is None:
        return False
    return _exact_source_owner_chain_matches_retrieval_v1(
        retrieval_owner,
        source_owner,
        compiled=compiled,
        effective_matches=effective_matches,
        pages=pages,
        source_occurrences=source_occurrences,
        visited=seen,
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
    source_occurrences: Sequence[Mapping[str, Any]],
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
    else:
        raw_source_role_axis = [
            {
                **canonical_clone_v1(item),
                "matched_within_role": item.get("_within_role"),
                "role": role,
            }
            for item in exact_hits["children"].get(role, [])
        ]
        source_role_axis = [item for item in source_occurrences if item["role"] == role]
        if coextensive_parent_child:
            source_role_axis = raw_source_role_axis
        else:
            decorated_same_physical_span = [
                item for item in source_role_axis if _same_match_span(item, match, pages)
            ]
            decorated_signatures = {
                (
                    item.get("page_sequence"),
                    item.get("source_line_index"),
                    item.get("end_source_line_index"),
                    item.get("matched_within_role"),
                )
                for item in source_role_axis
            }
            if not decorated_same_physical_span:
                source_role_axis.extend(
                    item
                    for item in raw_source_role_axis
                    if (
                        item.get("page_sequence"),
                        item.get("source_line_index"),
                        item.get("end_source_line_index"),
                        item.get("matched_within_role"),
                    )
                    not in decorated_signatures
                )
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
    source_occurrence = same_role_context_span[0] if len(same_role_context_span) == 1 else None
    source_owner_chain_bound = (
        match_scope == "FAMILY_PARENT"
        or source_occurrence is not None
        and _exact_source_owner_chain_matches_retrieval_v1(
            match,
            source_occurrence,
            compiled=compiled,
            effective_matches=effective_matches,
            pages=pages,
            source_occurrences=source_occurrences,
        )
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
        elif selected_parent is not None and _is_one_edit(selected_parent) and exact_parent is None:
            status = "EXACT_FAMILY_PARENT_CONTEXT_MISMATCH"
        elif match_scope == "EXPANDED_OCCURRENCE" and not source_owner_chain_bound:
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


def _build_from_canonical_expanded_occurrences_v1(
    pages: Sequence[Mapping[str, Any]],
    compiled: Mapping[str, Any],
    *,
    document_pages: Any,
    family_spec: Any,
    selected_topology_region: Mapping[str, Any],
    expanded_occurrence_region: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the receipt from one already canonical retrieval occurrence axis.

    Occurrence V2 uses this low-level primitive before its schema projector.
    It deliberately performs no occurrence replay of its own, avoiding a
    private replay cycle; the caller supplies an axis it has just derived from
    the same canonical pages/spec/selected region.  The public builder below
    still independently replays that axis before entering this primitive.
    """

    _validate_canonical_expanded_occurrence_axis_v1(
        expanded_occurrence_region,
        selected_topology_region,
    )
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
    source_occurrences = _decorate_exact_source_occurrences_v1(
        _context_bound_source_records(
            exact_hits,
            compiled,
            selected_topology_region,
        ),
        pages,
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
                source_occurrences=source_occurrences,
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


def build_accounting_family_one_edit_exact_authority_v1(
    document_pages: Any,
    family_spec: Any,
    selected_topology_region: Any,
    expanded_occurrence_region: Any,
) -> dict[str, Any]:
    """Gate one selected V4 candidate and every expanded role occurrence."""

    try:
        pages = _pages_with_occurrence_geometry_v1(document_pages)
        compiled = topology_v1._spec(family_spec)  # noqa: SLF001
    except (ValueError, RuntimeError) as exc:
        raise _error("one-edit exact-authority document or family spec drifted") from exc
    if type(selected_topology_region) is not dict or type(expanded_occurrence_region) is not dict:
        raise _error("one-edit exact-authority selected/expanded region binding drifted")
    canonical_expanded_occurrence_region = _canonical_expanded_occurrence_region_v1(
        pages,
        family_spec,
        selected_topology_region,
    )
    if not same_typed_json_v1(
        expanded_occurrence_region,
        canonical_expanded_occurrence_region,
    ):
        raise _error("expanded occurrence region does not replay exactly")
    # Never derive authority from the caller-owned object, even after the
    # typed comparison.  All later checks and hashes consume the replayed axis.
    return _build_from_canonical_expanded_occurrences_v1(
        pages,
        compiled,
        document_pages=document_pages,
        family_spec=family_spec,
        selected_topology_region=selected_topology_region,
        expanded_occurrence_region=canonical_expanded_occurrence_region,
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
