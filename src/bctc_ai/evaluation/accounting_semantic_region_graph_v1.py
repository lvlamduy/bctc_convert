"""Declarative semantic-region proposals above shared accounting geometry.

The engine is family-neutral.  A caller declares owner/veto contexts, branch
aliases, semantic rows, source-only ambiguities, structural resets, and closed
limits.  The engine retains raw NFC evidence, performs exact accented then
exact accentless matching, and consults the shared bounded one-character
matcher only after every exact row candidate misses.

Accepted owner context opens a bounded page-local body.  Adaptive accounting
geometry v2 measures rows and lanes, while ``accounting_scoped_table_graph_v1``
replays same-page owner/scope/role topology.  Both are proposals: this module
knows no ReportNormId, bank, filename, note, year, value, or mapping policy.
Explicit zero-line pages remain in the page sequence and evidence hash; they do
not invent a reset or geometry atom.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from enum import StrEnum
from functools import lru_cache
from typing import Any

from bctc_ai.evaluation.accounting_scoped_table_graph_v1 import (
    SPEC_FORMAT_VERSION as SCOPED_SPEC_FORMAT_VERSION,
)
from bctc_ai.evaluation.accounting_scoped_table_graph_v1 import (
    AccountingScopedTableGraphV1Error,
    build_accounting_scoped_table_graph_v1,
)
from bctc_ai.evaluation.accounting_table_axes_v1 import is_accounting_value_surface_v1
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    match_vietnamese_anchor_alias_v1,
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.evaluation.adaptive_accounting_table_geometry_v2 import (
    resolve_accounting_table_geometry_v2,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "SPEC_FORMAT_VERSION",
    "AccountingSemanticRegionGraphV1Error",
    "ScopedTableEnforcementV1",
    "build_accounting_semantic_region_graph_v1",
    "validate_accounting_semantic_region_graph_replay_v1",
]


FORMAT_VERSION = "ACCOUNTING_SEMANTIC_REGION_GRAPH_V1"
SPEC_FORMAT_VERSION = "ACCOUNTING_SEMANTIC_REGION_FAMILY_SPEC_V1"
CLAIM_BOUNDARY = (
    "DECLARATIVE_OWNER_VETO_BRANCH_SEMANTIC_ROW_AND_SHARED_GEOMETRY_REGION_"
    "PROPOSAL_ONLY_NO_VALUE_PERIOD_UNIT_FAMILY_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
_ID = re.compile(r"^[A-Z][A-Z0-9_]*$")
_ENUMERATION_PREFIX = re.compile(
    r"^\s*(?:(?:\d+(?:\.\d+)*|[a-z]|[ivxlcdm]+)[.)])\s*", re.IGNORECASE
)
_TIER_ORDER = {
    "EXACT_ACCENTED_ALIAS": 0,
    "EXACT_ACCENTLESS_ALIAS": 1,
    "ONE_BASE_CHARACTER_EDIT_AFTER_ALL_EXACT_MISSES": 2,
}
_BRANCH_PRIORITY = {
    ("FULL_BRANCH_ALIAS", "EXACT_ACCENTED_ALIAS"): 0,
    ("FULL_BRANCH_ALIAS", "EXACT_ACCENTLESS_ALIAS"): 1,
    ("DECLARATIVE_BRANCH_COMPONENT", "EXACT_ACCENTED_ALIAS"): 2,
    ("DECLARATIVE_BRANCH_COMPONENT", "EXACT_ACCENTLESS_ALIAS"): 3,
    (
        "FULL_BRANCH_ALIAS",
        "ONE_BASE_CHARACTER_EDIT_AFTER_ALL_EXACT_MISSES",
    ): 4,
    (
        "DECLARATIVE_BRANCH_COMPONENT",
        "ONE_BASE_CHARACTER_EDIT_AFTER_ALL_EXACT_MISSES",
    ): 5,
}
_CONTEXT_DISPOSITIONS = {"HARD_VETO", "REQUIRED_OWNER"}
_SCOPED_LIMIT_FIELDS = {
    "axis_tolerance_ppm",
    "continuation_page_budget",
    "max_owner_distance_lines",
    "max_role_gap_lines",
    "max_wrap_lines",
    "minimum_cell_row_overlap_ppm",
    "unlabeled_total_gap_jitter_ppm",
    "unlabeled_total_max_gap_lines",
    "unlabeled_total_max_numeric_columns",
    "unlabeled_total_min_numeric_columns",
}


class ScopedTableEnforcementV1(StrEnum):
    """How a scoped-table challenge affects an otherwise valid region."""

    REQUIRED_PROMOTION_GATE = "REQUIRED_PROMOTION_GATE"
    ADVISORY_CHALLENGER = "ADVISORY_CHALLENGER"


class AccountingSemanticRegionGraphV1Error(ValueError):
    """A generic spec, page axis, result identity, or replay drifted."""


def _error(message: str) -> AccountingSemanticRegionGraphV1Error:
    return AccountingSemanticRegionGraphV1Error(message)


def _nfc(value: Any, label: str, *, nonempty: bool = True) -> str:
    if type(value) is not str or (nonempty and not value.strip()):
        raise _error(f"{label} must be one {'nonempty ' if nonempty else ''}exact string")
    if value != unicodedata.normalize("NFC", value):
        raise _error(f"{label} must already be NFC-normalized")
    return value


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} must be one positive exact integer")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise _error(f"{label} must be one nonnegative exact integer")
    return value


def _identifier(value: Any, label: str) -> str:
    parsed = _nfc(value, label)
    if _ID.fullmatch(parsed) is None:
        raise _error(f"{label} must be one uppercase semantic identifier")
    return parsed


def _aliases(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    if type(value) is not list or (not allow_empty and not value):
        raise _error(f"{label} must be one {'possibly empty' if allow_empty else 'nonempty'} list")
    aliases = [_nfc(item, f"{label} alias") for item in value]
    normalized = [normalize_vietnamese_anchor_v1(item) for item in aliases]
    if any(not item for item in normalized) or len(set(normalized)) != len(normalized):
        raise _error(f"{label} aliases must be unique after accentless normalization")
    return aliases


def _spec(value: Any) -> dict[str, Any]:
    required = {
        "branch_aliases",
        "context_classes",
        "family_id",
        "format_version",
        "limits",
        "required_owner_context_id",
        "row_axis",
        "scoped_table",
        "source_only_ambiguities",
        "structural_reset_aliases",
    }
    optional = {"branch_components", "structural_reset_component_aliases"}
    if (
        type(value) is not dict
        or not required <= set(value)
        or not set(value) <= required | optional
    ):
        raise _error("semantic-region family spec fields drifted")
    if value["format_version"] != SPEC_FORMAT_VERSION:
        raise _error("semantic-region family spec version drifted")
    family_id = _identifier(value["family_id"], "family ID")

    raw_components = value.get("branch_components", [])
    if type(raw_components) is not list:
        raise _error("semantic-region branch components must be one list")
    components = []
    component_ids: set[str] = set()
    component_aliases: set[str] = set()
    for raw in raw_components:
        if type(raw) is not dict or set(raw) != {
            "aliases",
            "bounded_edit_on_exact_miss",
            "component_id",
        }:
            raise _error("semantic-region branch component fields drifted")
        component_id = _identifier(raw["component_id"], "branch component ID")
        if component_id in component_ids or type(raw["bounded_edit_on_exact_miss"]) is not bool:
            raise _error("semantic-region branch component identity/edit policy drifted")
        aliases = _aliases(raw["aliases"], component_id)
        normalized_aliases = {normalize_vietnamese_anchor_v1(alias) for alias in aliases}
        if normalized_aliases & component_aliases:
            raise _error("semantic-region branch component aliases repeat across components")
        component_ids.add(component_id)
        component_aliases.update(normalized_aliases)
        components.append(
            {
                "aliases": aliases,
                "bounded_edit_on_exact_miss": raw["bounded_edit_on_exact_miss"],
                "component_id": component_id,
            }
        )

    raw_contexts = value["context_classes"]
    if type(raw_contexts) is not list or len(raw_contexts) < 2:
        raise _error("semantic-region spec needs owner and hard-veto contexts")
    contexts = []
    context_ids: set[str] = set()
    for raw in raw_contexts:
        context_required = {"aliases", "context_id", "disposition"}
        if type(raw) is not dict or set(raw) not in (
            context_required,
            context_required | {"allow_token_subsequence_fence"},
        ):
            raise _error("semantic-region context fields drifted")
        context_id = _identifier(raw["context_id"], "context ID")
        allow_containment = raw.get("allow_token_subsequence_fence", False)
        if (
            context_id in context_ids
            or raw["disposition"] not in _CONTEXT_DISPOSITIONS
            or type(allow_containment) is not bool
            or (allow_containment and raw["disposition"] != "HARD_VETO")
        ):
            raise _error("semantic-region context identity/disposition repeats or drifted")
        context_ids.add(context_id)
        contexts.append(
            {
                "aliases": _aliases(raw["aliases"], context_id),
                "allow_token_subsequence_fence": allow_containment,
                "context_id": context_id,
                "disposition": raw["disposition"],
            }
        )
    owner_id = _identifier(value["required_owner_context_id"], "required owner context ID")
    owners = [item for item in contexts if item["disposition"] == "REQUIRED_OWNER"]
    if len(owners) != 1 or owners[0]["context_id"] != owner_id:
        raise _error("semantic-region spec requires exactly one named owner context")

    raw_rows = value["row_axis"]
    if type(raw_rows) is not list or not raw_rows:
        raise _error("semantic-region row axis must be one nonempty list")
    rows = []
    semantic_ids: set[str] = set()
    for raw in raw_rows:
        if type(raw) is not dict or set(raw) != {
            "aliases",
            "bounded_edit_on_exact_miss",
            "semantic_id",
        }:
            raise _error("semantic-region row fields drifted")
        semantic_id = _identifier(raw["semantic_id"], "row semantic ID")
        if semantic_id in semantic_ids or type(raw["bounded_edit_on_exact_miss"]) is not bool:
            raise _error("semantic-region row identity repeats or edit policy drifted")
        semantic_ids.add(semantic_id)
        rows.append(
            {
                "aliases": _aliases(raw["aliases"], semantic_id),
                "bounded_edit_on_exact_miss": raw["bounded_edit_on_exact_miss"],
                "semantic_id": semantic_id,
            }
        )

    raw_ambiguities = value["source_only_ambiguities"]
    if type(raw_ambiguities) is not list:
        raise _error("semantic-region source-only ambiguities must be one list")
    ambiguities = []
    ambiguity_ids: set[str] = set()
    for raw in raw_ambiguities:
        if type(raw) is not dict or set(raw) != {
            "aliases",
            "ambiguity_id",
            "candidate_semantic_ids",
            "reason",
        }:
            raise _error("semantic-region source-only ambiguity fields drifted")
        ambiguity_id = _identifier(raw["ambiguity_id"], "ambiguity ID")
        candidates = raw["candidate_semantic_ids"]
        if (
            ambiguity_id in ambiguity_ids
            or type(candidates) is not list
            or not candidates
            or candidates != sorted(set(candidates))
            or any(item not in semantic_ids for item in candidates)
        ):
            raise _error("semantic-region ambiguity identity/candidates drifted")
        ambiguity_ids.add(ambiguity_id)
        ambiguities.append(
            {
                "aliases": _aliases(raw["aliases"], ambiguity_id),
                "ambiguity_id": ambiguity_id,
                "candidate_semantic_ids": list(candidates),
                "reason": _identifier(raw["reason"], "ambiguity reason"),
            }
        )

    limits = value["limits"]
    required_limit_fields = {
        "branch_line_span",
        "context_page_budget",
        "maximum_body_lines_per_page",
        "row_label_line_span",
    }
    if (
        type(limits) is not dict
        or not required_limit_fields <= set(limits)
        or not set(limits) <= required_limit_fields | {"context_line_span"}
    ):
        raise _error("semantic-region structural limit fields drifted")
    parsed_limits = {
        "branch_line_span": _positive_int(limits["branch_line_span"], "branch line span"),
        "context_line_span": _positive_int(limits.get("context_line_span", 1), "context line span"),
        "context_page_budget": _nonnegative_int(
            limits["context_page_budget"], "context page budget"
        ),
        "maximum_body_lines_per_page": _positive_int(
            limits["maximum_body_lines_per_page"], "maximum body lines"
        ),
        "row_label_line_span": _positive_int(limits["row_label_line_span"], "row label line span"),
    }
    if (
        parsed_limits["branch_line_span"] > 3
        or parsed_limits["context_line_span"] > 3
        or parsed_limits["context_page_budget"] > 8
        or parsed_limits["maximum_body_lines_per_page"] > 512
        or parsed_limits["row_label_line_span"] > 3
    ):
        raise _error("semantic-region structural limits exceed closed bounds")

    scoped = value["scoped_table"]
    scoped_required = {
        "continuation_aliases",
        "hard_veto_scope_aliases",
        "layout_modes",
        "limits",
        "require_trailing_total_for_roles_as_columns",
        "trailing_total_aliases",
    }
    if type(scoped) is not dict or set(scoped) not in (
        scoped_required,
        scoped_required | {"enforcement"},
    ):
        raise _error("semantic-region scoped-table configuration fields drifted")
    layouts = scoped["layout_modes"]
    if (
        type(layouts) is not list
        or not layouts
        or layouts != sorted(set(layouts))
        or any(item not in {"ROLES_AS_COLUMNS", "ROLES_AS_ROWS"} for item in layouts)
    ):
        raise _error("semantic-region scoped-table layouts drifted")
    scoped_limits = scoped["limits"]
    if type(scoped_limits) is not dict or set(scoped_limits) != _SCOPED_LIMIT_FIELDS:
        raise _error("semantic-region scoped-table limits drifted")
    if any(type(item) is not int or item < 0 for item in scoped_limits.values()):
        raise _error("semantic-region scoped-table limits require exact nonnegative integers")
    require_total = scoped["require_trailing_total_for_roles_as_columns"]
    if type(require_total) is not bool:
        raise _error("semantic-region scoped-table total policy drifted")
    enforcement = scoped.get("enforcement", ScopedTableEnforcementV1.REQUIRED_PROMOTION_GATE.value)
    if type(enforcement) is not str:
        raise _error("semantic-region scoped-table enforcement drifted")
    try:
        parsed_enforcement = ScopedTableEnforcementV1(enforcement).value
    except ValueError as error:
        raise _error("semantic-region scoped-table enforcement drifted") from error
    parsed_scoped = {
        "continuation_aliases": _aliases(
            scoped["continuation_aliases"], "scoped continuation", allow_empty=True
        ),
        "hard_veto_scope_aliases": _aliases(scoped["hard_veto_scope_aliases"], "scoped hard veto"),
        "enforcement": parsed_enforcement,
        "layout_modes": list(layouts),
        "limits": canonical_clone_v1(scoped_limits),
        "require_trailing_total_for_roles_as_columns": require_total,
        "trailing_total_aliases": _aliases(
            scoped["trailing_total_aliases"], "scoped trailing total", allow_empty=True
        ),
    }
    if require_total and not parsed_scoped["trailing_total_aliases"]:
        raise _error("semantic-region required scoped total needs aliases")
    structural_resets = _aliases(
        value["structural_reset_aliases"], "structural reset", allow_empty=True
    )
    reset_components = _aliases(
        value.get("structural_reset_component_aliases", []),
        "structural reset component",
        allow_empty=True,
    )
    normalized_resets = {normalize_vietnamese_anchor_v1(alias) for alias in structural_resets}
    if any(
        normalize_vietnamese_anchor_v1(alias) not in normalized_resets for alias in reset_components
    ):
        raise _error("structural reset component aliases must be declared reset aliases")
    return {
        "branch_aliases": _aliases(value["branch_aliases"], "branch"),
        "branch_components": components,
        "context_classes": contexts,
        "family_id": family_id,
        "format_version": SPEC_FORMAT_VERSION,
        "limits": parsed_limits,
        "required_owner_context_id": owner_id,
        "row_axis": rows,
        "scoped_table": parsed_scoped,
        "source_only_ambiguities": ambiguities,
        "structural_reset_aliases": structural_resets,
        "structural_reset_component_aliases": reset_components,
    }


def _bbox(value: Any, *, width: int, height: int) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or value[0] < 0
        or value[1] < 0
        or value[0] >= value[2]
        or value[1] >= value[3]
        or value[2] > width
        or value[3] > height
    ):
        raise _error("semantic-region line bbox drifted")
    return list(value)


def _visual(lines: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        (dict(line) for line in lines),
        key=lambda line: (
            line["bbox"][1],
            line["bbox"][0],
            line["bbox"][3],
            line["bbox"][2],
            line["source_line_index"],
        ),
    )


def _pages(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise _error("semantic-region graph requires one exact region-page sequence")
    pages = []
    seen_pages: set[int] = set()
    for raw_page in value:
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_height",
            "page_sequence",
            "page_width",
        }:
            raise _error("semantic-region page fields drifted")
        page_sequence = _positive_int(raw_page["page_sequence"], "page sequence")
        width = _positive_int(raw_page["page_width"], "page width")
        height = _positive_int(raw_page["page_height"], "page height")
        if page_sequence in seen_pages or type(raw_page["lines"]) is not list:
            raise _error("semantic-region page sequence repeats or line axis drifted")
        seen_pages.add(page_sequence)
        lines = []
        seen_indices: set[int] = set()
        for raw_line in raw_page["lines"]:
            if type(raw_line) is not dict or set(raw_line) != {
                "bbox",
                "source_line_index",
                "source_text",
                "vietocr_text",
            }:
                raise _error("semantic-region line fields drifted")
            source_index = _nonnegative_int(raw_line["source_line_index"], "source line index")
            if source_index in seen_indices:
                raise _error("semantic-region source line index repeats on one page")
            seen_indices.add(source_index)
            source_text = raw_line["source_text"]
            if source_text is not None:
                source_text = _nfc(source_text, "source text", nonempty=False)
            lines.append(
                {
                    "bbox": _bbox(raw_line["bbox"], width=width, height=height),
                    "source_line_index": source_index,
                    "source_text": source_text,
                    "vietocr_text": _nfc(raw_line["vietocr_text"], "VietOCR text", nonempty=False),
                }
            )
        pages.append(
            {
                "lines": _visual(lines),
                "page_height": height,
                "page_sequence": page_sequence,
                "page_width": width,
            }
        )
    if not pages:
        raise _error("semantic-region graph requires at least one explicit page")
    return sorted(pages, key=lambda page: page["page_sequence"])


@lru_cache(maxsize=4_096)
def _accented(value: str) -> str:
    value = _ENUMERATION_PREFIX.sub("", value)
    value = unicodedata.normalize("NFC", value.casefold())
    normalized = " ".join(re.sub(r"[^0-9a-zà-ỹđ%]+", " ", value).split())
    return re.sub(r"^(?:[0-9]+\s+)+", "", normalized)


@lru_cache(maxsize=4_096)
def _accentless(value: str) -> str:
    value = _ENUMERATION_PREFIX.sub("", value)
    normalized = normalize_vietnamese_anchor_v1(value)
    return re.sub(r"^(?:[0-9]+\s+)+", "", normalized)


def _joined(lines: Sequence[Mapping[str, Any]]) -> str:
    return " ".join(line["vietocr_text"].strip() for line in lines).strip()


def _line_evidence(line: Mapping[str, Any], *, page_sequence: int) -> dict[str, Any]:
    return {
        "bbox": canonical_clone_v1(line["bbox"]),
        "page_sequence": page_sequence,
        "source_line_index": line["source_line_index"],
        "source_text": line["source_text"],
        "vietocr_accentless_surface": _accentless(line["vietocr_text"]),
        "vietocr_raw_nfc_surface": line["vietocr_text"],
    }


def _is_value(line: Mapping[str, Any]) -> bool:
    return is_accounting_value_surface_v1(line["vietocr_text"]) or (
        type(line["source_text"]) is str and is_accounting_value_surface_v1(line["source_text"])
    )


def _can_join_wrapped_label(
    current: tuple[int, Mapping[str, Any]],
    following: tuple[int, Mapping[str, Any]],
    body: Sequence[Mapping[str, Any]],
) -> bool:
    current_index, current_line = current
    following_index, following_line = following
    if any(_is_value(line) for line in body[current_index + 1 : following_index]):
        return False
    current_height = current_line["bbox"][3] - current_line["bbox"][1]
    following_height = following_line["bbox"][3] - following_line["bbox"][1]
    gap = following_line["bbox"][1] - current_line["bbox"][3]
    maximum_gap = max(4, min(current_height, following_height) // 2)
    maximum_indent = max(current_height, following_height) * 3
    return (
        gap <= maximum_gap
        and abs(following_line["bbox"][0] - current_line["bbox"][0]) <= maximum_indent
    )


def _exact_matches(surface: str, aliases: Sequence[str]) -> tuple[str | None, list[str]]:
    accented = _accented(surface)
    matches = [alias for alias in aliases if accented == _accented(alias)]
    if matches:
        return "EXACT_ACCENTED_ALIAS", matches
    accentless = _accentless(surface)
    matches = [alias for alias in aliases if accentless == _accentless(alias)]
    if matches:
        return "EXACT_ACCENTLESS_ALIAS", matches
    return None, []


def _bounded_matches(surface: str, aliases: Sequence[str]) -> tuple[list[str], int]:
    normalized_surface = _accentless(surface)
    matches = []
    comparisons = 0
    for alias in aliases:
        if abs(len(normalized_surface) - len(_accentless(alias))) > 1:
            continue
        comparisons += 1
        if (
            match_vietnamese_anchor_alias_v1(surface, [alias])
            == "ONE_EDIT_ALIAS_IN_COMPLETE_ORDERED_TOPOLOGY"
        ):
            matches.append(alias)
    return matches, comparisons


def _best_alias_match(
    surfaces: Sequence[str], aliases: Sequence[str], *, allow_bounded: bool
) -> tuple[str | None, str | None, list[str], int]:
    exact = []
    for span, surface in enumerate(surfaces, start=1):
        tier, matches = _exact_matches(surface, aliases)
        if tier is not None:
            exact.append((tier, -span, surface, matches))
    if exact:
        tier, _, surface, matches = min(
            exact, key=lambda item: (_TIER_ORDER[item[0]], item[1], item[2])
        )
        return tier, surface, matches, 0
    if not allow_bounded:
        return None, None, [], 0
    bounded = []
    comparisons = 0
    for span, surface in enumerate(surfaces, start=1):
        matches, count = _bounded_matches(surface, aliases)
        comparisons += count
        if matches:
            bounded.append((-span, surface, matches))
    if not bounded:
        return None, None, [], comparisons
    _, surface, matches = min(bounded, key=lambda item: (item[0], item[1]))
    return (
        "ONE_BASE_CHARACTER_EDIT_AFTER_ALL_EXACT_MISSES",
        surface,
        matches,
        comparisons,
    )


def _contains_token_sequence(surface: str, alias: str, *, accentless: bool) -> bool:
    normalize = _accentless if accentless else _accented
    surface_tokens = normalize(surface).split()
    alias_tokens = normalize(alias).split()
    width = len(alias_tokens)
    return bool(width) and any(
        surface_tokens[start : start + width] == alias_tokens
        for start in range(len(surface_tokens) - width + 1)
    )


def _exact_component_matches(
    surface: str, components: Sequence[Mapping[str, Any]]
) -> tuple[str | None, list[str], list[str]]:
    for tier, accentless in (
        ("EXACT_ACCENTED_ALIAS", False),
        ("EXACT_ACCENTLESS_ALIAS", True),
    ):
        matched = [
            (component["component_id"], alias)
            for component in components
            for alias in component["aliases"]
            if _contains_token_sequence(surface, alias, accentless=accentless)
        ]
        if matched:
            return (
                tier,
                sorted({alias for _, alias in matched}),
                sorted({component_id for component_id, _ in matched}),
            )
    return None, [], []


def _bounded_component_alias_matches(surface: str, alias: str) -> tuple[bool, int]:
    surface_tokens = _accentless(surface).split()
    alias_tokens = _accentless(alias).split()
    comparisons = 0
    widths = sorted(
        {
            width
            for width in (len(alias_tokens) - 1, len(alias_tokens), len(alias_tokens) + 1)
            if width > 0
        }
    )
    for width in widths:
        for start in range(len(surface_tokens) - width + 1):
            candidate = " ".join(surface_tokens[start : start + width])
            if abs(len(candidate) - len(_accentless(alias))) > 1:
                continue
            comparisons += 1
            if (
                match_vietnamese_anchor_alias_v1(candidate, [alias])
                == "ONE_EDIT_ALIAS_IN_COMPLETE_ORDERED_TOPOLOGY"
            ):
                return True, comparisons
    return False, comparisons


def _best_component_match(
    surfaces: Sequence[str],
    components: Sequence[Mapping[str, Any]],
    *,
    allow_bounded: bool,
) -> tuple[str | None, str | None, list[str], list[str], int, int | None]:
    exact = []
    for span, surface in enumerate(surfaces, start=1):
        tier, aliases, component_ids = _exact_component_matches(surface, components)
        if tier is not None:
            exact.append((tier, span, surface, aliases, component_ids))
    if exact:
        tier, span, surface, aliases, component_ids = min(
            exact, key=lambda item: (_TIER_ORDER[item[0]], item[1], item[2])
        )
        return tier, surface, aliases, component_ids, 0, span
    if not allow_bounded:
        return None, None, [], [], 0, None
    bounded = []
    comparisons = 0
    for span, surface in enumerate(surfaces, start=1):
        matched = []
        for component in components:
            if not component["bounded_edit_on_exact_miss"]:
                continue
            for alias in component["aliases"]:
                is_match, count = _bounded_component_alias_matches(surface, alias)
                comparisons += count
                if is_match:
                    matched.append((component["component_id"], alias))
        if matched:
            bounded.append(
                (
                    span,
                    surface,
                    sorted({alias for _, alias in matched}),
                    sorted({component_id for component_id, _ in matched}),
                )
            )
    if not bounded:
        return None, None, [], [], comparisons, None
    span, surface, aliases, component_ids = min(
        bounded, key=lambda item: (item[0], item[1], item[2], item[3])
    )
    return (
        "ONE_BASE_CHARACTER_EDIT_AFTER_ALL_EXACT_MISSES",
        surface,
        aliases,
        component_ids,
        comparisons,
        span,
    )


def _cohesive_nonvalue_surfaces(
    lines: Sequence[Mapping[str, Any]],
    start: int,
    maximum_span: int,
    context_fence_indices: set[int],
) -> list[str]:
    if _is_value(lines[start]) or start in context_fence_indices:
        return []
    surfaces = []
    for span in range(1, maximum_span + 1):
        stop = start + span
        if stop > len(lines):
            break
        current = lines[stop - 1]
        if _is_value(current) or stop - 1 in context_fence_indices:
            break
        if span > 1 and not _can_join_wrapped_label(
            (stop - 2, lines[stop - 2]), (stop - 1, current), lines
        ):
            break
        surfaces.append(_joined(lines[start:stop]))
    return surfaces


def _context_event_specificity(event: Mapping[str, Any]) -> tuple[int, int]:
    return max(
        (len(_accentless(alias).split()), len(_accentless(alias)))
        for alias in event["matched_aliases"]
    )


def _select_context_event(candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    if not candidates:
        return None
    ranked = [
        (
            (
                candidate["disposition"] != "HARD_VETO",
                -_context_event_specificity(candidate)[0],
                -_context_event_specificity(candidate)[1],
                _TIER_ORDER[candidate["match_tier"]],
                candidate["context_id"] == "STRUCTURAL_RESET",
            ),
            candidate,
        )
        for candidate in candidates
    ]
    best_rank = min(item[0] for item in ranked)
    winners = [candidate for rank, candidate in ranked if rank == best_rank]
    context_ids = {candidate["context_id"] for candidate in winners}
    aliases = sorted({alias for candidate in winners for alias in candidate["matched_aliases"]})
    if len(context_ids) != 1 or "AMBIGUOUS_CONTEXT_EVENT" in context_ids:
        return {
            "context_id": "AMBIGUOUS_CONTEXT_EVENT",
            "disposition": "HARD_VETO",
            "match_tier": winners[0]["match_tier"],
            "matched_aliases": aliases,
        }
    selected = canonical_clone_v1(winners[0])
    selected["matched_aliases"] = aliases
    return selected


def _select_priority_intervals(
    candidates: Sequence[Mapping[str, Any]],
    *,
    priority_key: Callable[[Mapping[str, Any]], Any],
    same_priority_key: Callable[[Mapping[str, Any]], Any],
    is_fail_closed_blocker: Callable[[Mapping[str, Any]], bool],
) -> tuple[list[dict[str, Any]], set[int], int]:
    blockers = [dict(item) for item in candidates if is_fail_closed_blocker(item)]
    ordinary = [dict(item) for item in candidates if not is_fail_closed_blocker(item)]
    selected = sorted(blockers, key=same_priority_key)
    selected_coverage = {index for item in selected for index in range(item["start"], item["stop"])}
    # Every enumerated higher-priority interval reserves coverage for all lower
    # tiers, even when it loses same-tier arbitration.  This prevents chains
    # HIGH[0,2), HIGH[1,3), LOW[2,3) from leaking LOW through a greedy gap.
    higher_priority_coverage = set(selected_coverage)
    priorities = sorted({priority_key(item) for item in ordinary})
    for priority in priorities:
        tier = [item for item in ordinary if priority_key(item) == priority]
        tier_selected_coverage: set[int] = set()
        for candidate in sorted(tier, key=same_priority_key):
            covered = set(range(candidate["start"], candidate["stop"]))
            if covered & (higher_priority_coverage | tier_selected_coverage):
                continue
            selected.append(candidate)
            selected_coverage.update(covered)
            tier_selected_coverage.update(covered)
        higher_priority_coverage.update(
            index for item in tier for index in range(item["start"], item["stop"])
        )
    return selected, selected_coverage, len(candidates) - len(selected)


def _context_event_plan(
    pages: Sequence[Mapping[str, Any]], spec: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], int, dict[str, int]]:
    plans = []
    comparisons = 0
    enumerated_count = 0
    suppressed_count = 0
    maximum_span = spec["limits"]["context_line_span"]
    for page_ordinal, page in enumerate(pages):
        lines = page["lines"]
        candidates = []
        for start in range(len(lines)):
            surfaces = _cohesive_nonvalue_surfaces(lines, start, maximum_span, set())
            seen_start_event_keys = set()
            for span, surface in enumerate(surfaces, 1):
                event, count = _context_class(surface, spec, allow_bounded=True)
                comparisons += count
                if event is None:
                    continue
                event_key = (
                    event["context_id"],
                    event["disposition"],
                    event["match_tier"],
                    tuple(event["matched_aliases"]),
                )
                if event_key in seen_start_event_keys:
                    continue
                seen_start_event_keys.add(event_key)
                material = {
                    **event,
                    "evidence": [
                        _line_evidence(line, page_sequence=page["page_sequence"])
                        for line in lines[start : start + span]
                    ],
                    "line_ordinal": start,
                    "line_stop_exclusive": start + span,
                    "page_sequence": page["page_sequence"],
                    "surface": surface,
                }
                candidates.append(
                    {
                        **material,
                        "context_event_id": "asrgv1:context_event:"
                        + canonical_json_sha256_v1(material),
                        "page_ordinal": page_ordinal,
                        "start": start,
                        "stop": start + span,
                    }
                )
        enumerated_count += len(candidates)
        selected, _, suppressed = _select_priority_intervals(
            candidates,
            priority_key=lambda item: (
                -_context_event_specificity(item)[0],
                -_context_event_specificity(item)[1],
                _TIER_ORDER[item["match_tier"]],
            ),
            same_priority_key=lambda item: (
                item["stop"] - item["start"],
                item["start"],
                item["context_event_id"],
            ),
            is_fail_closed_blocker=lambda item: item["disposition"] == "HARD_VETO",
        )
        # Branch construction must not reinterpret the uncovered tail of a
        # recognized context candidate.  Reserve the union of every enumerated
        # context interval, including same-tier candidates that lose diagnostic
        # arbitration.  Redundant longer windows for the same semantic event
        # have already been removed above, so this does not let a containment
        # superset consume an otherwise independent following context event.
        context_coverage = {
            index for item in candidates for index in range(item["start"], item["stop"])
        }
        suppressed_count += suppressed
        plans.append(
            {
                "events": sorted(
                    selected,
                    key=lambda item: (item["start"], item["stop"], item["context_event_id"]),
                ),
                "fence_indices": context_coverage,
            }
        )
    return (
        plans,
        comparisons,
        {
            "enumerated_event_count": enumerated_count,
            "overlap_suppressed_event_count": suppressed_count,
            "selected_event_count": sum(len(plan["events"]) for plan in plans),
            "wrapped_event_count": sum(
                event["stop"] - event["start"] > 1 for plan in plans for event in plan["events"]
            ),
        },
    )


def _branch_match(
    surfaces: Sequence[str], spec: Mapping[str, Any]
) -> tuple[dict[str, Any] | None, int]:
    tier, surface, aliases, _ = _best_alias_match(
        surfaces, spec["branch_aliases"], allow_bounded=False
    )
    if tier is not None and surface is not None:
        span = max(index for index, item in enumerate(surfaces, 1) if item == surface)
        return {
            "match_basis": "FULL_BRANCH_ALIAS",
            "match_tier": tier,
            "matched_aliases": sorted(aliases),
            "matched_component_ids": [],
            "span": span,
            "surface": surface,
        }, 0

    tier, surface, aliases, component_ids, _, span = _best_component_match(
        surfaces, spec["branch_components"], allow_bounded=False
    )
    if tier is not None and surface is not None and span is not None:
        return {
            "match_basis": "DECLARATIVE_BRANCH_COMPONENT",
            "match_tier": tier,
            "matched_aliases": aliases,
            "matched_component_ids": component_ids,
            "span": span,
            "surface": surface,
        }, 0

    tier, surface, aliases, comparisons = _best_alias_match(
        surfaces, spec["branch_aliases"], allow_bounded=True
    )
    if tier is not None and surface is not None:
        span = max(index for index, item in enumerate(surfaces, 1) if item == surface)
        return {
            "match_basis": "FULL_BRANCH_ALIAS",
            "match_tier": tier,
            "matched_aliases": sorted(aliases),
            "matched_component_ids": [],
            "span": span,
            "surface": surface,
        }, comparisons

    component = _best_component_match(surfaces, spec["branch_components"], allow_bounded=True)
    tier, surface, aliases, component_ids, count, span = component
    comparisons += count
    if tier is None or surface is None or span is None:
        return None, comparisons
    return {
        "match_basis": "DECLARATIVE_BRANCH_COMPONENT",
        "match_tier": tier,
        "matched_aliases": aliases,
        "matched_component_ids": component_ids,
        "span": span,
        "surface": surface,
    }, comparisons


def _branch_candidates(
    pages: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any],
    context_event_plans: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], int, dict[str, int]]:
    candidates = []
    comparisons = 0
    maximum_span = spec["limits"]["branch_line_span"]
    for page_ordinal, page in enumerate(pages):
        lines = page["lines"]
        context_fences = context_event_plans[page_ordinal]["fence_indices"]
        for start in range(len(lines)):
            surfaces = _cohesive_nonvalue_surfaces(lines, start, maximum_span, context_fences)
            matched, count = _branch_match(surfaces, spec)
            comparisons += count
            if matched is None:
                continue
            span = matched.pop("span")
            material = {
                "evidence": [
                    _line_evidence(line, page_sequence=page["page_sequence"])
                    for line in lines[start : start + span]
                ],
                "page_sequence": page["page_sequence"],
                **matched,
            }
            candidates.append(
                {
                    **material,
                    "branch_id": "asrgv1:branch:" + canonical_json_sha256_v1(material),
                    "page_ordinal": page_ordinal,
                    "start": start,
                    "stop": start + span,
                }
            )
    enumerated_count = len(candidates)
    selected = []
    suppressed_count = 0
    for page_ordinal in range(len(pages)):
        page_selected, _, page_suppressed = _select_priority_intervals(
            [item for item in candidates if item["page_ordinal"] == page_ordinal],
            priority_key=lambda item: _BRANCH_PRIORITY[(item["match_basis"], item["match_tier"])],
            same_priority_key=lambda item: (
                item["start"],
                item["stop"] - item["start"],
                item["branch_id"],
            ),
            is_fail_closed_blocker=lambda _item: False,
        )
        selected.extend(page_selected)
        suppressed_count += page_suppressed
    return (
        selected,
        comparisons,
        {
            "enumerated_candidate_count": enumerated_count,
            "overlap_suppressed_candidate_count": suppressed_count,
        },
    )


def _hard_context_components(spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        *(
            {
                "aliases": context["aliases"],
                "bounded_edit_on_exact_miss": True,
                "component_id": context["context_id"],
            }
            for context in spec["context_classes"]
            if context["disposition"] == "HARD_VETO" and context["allow_token_subsequence_fence"]
        ),
        {
            "aliases": spec["structural_reset_component_aliases"],
            "bounded_edit_on_exact_miss": True,
            "component_id": "STRUCTURAL_RESET",
        },
    ]


def _hard_context_component_event(
    surface: str, spec: Mapping[str, Any], *, allow_bounded: bool
) -> tuple[dict[str, Any] | None, int]:
    components = [component for component in _hard_context_components(spec) if component["aliases"]]
    exact = []
    for tier, accentless in (
        ("EXACT_ACCENTED_ALIAS", False),
        ("EXACT_ACCENTLESS_ALIAS", True),
    ):
        matches = [
            (component["component_id"], alias)
            for component in components
            for alias in component["aliases"]
            if _contains_token_sequence(surface, alias, accentless=accentless)
        ]
        if matches:
            exact = [(tier, *item) for item in matches]
            break
    comparisons = 0
    matches = exact
    if not matches and allow_bounded:
        for component in components:
            for alias in component["aliases"]:
                matched, count = _bounded_component_alias_matches(surface, alias)
                comparisons += count
                if matched:
                    matches.append(
                        (
                            "ONE_BASE_CHARACTER_EDIT_AFTER_ALL_EXACT_MISSES",
                            component["component_id"],
                            alias,
                        )
                    )
    if not matches:
        return None, comparisons
    # Longer declared events are more specific than their nested short fences.
    # Equal-specificity events remain ambiguous and therefore fail closed.
    maximum_specificity = max(
        (len(_accentless(alias).split()), len(_accentless(alias))) for _, _, alias in matches
    )
    winners = [
        (tier, context_id, alias)
        for tier, context_id, alias in matches
        if (len(_accentless(alias).split()), len(_accentless(alias))) == maximum_specificity
    ]
    tier = winners[0][0]
    aliases = sorted({alias for _, _, alias in winners})
    context_ids = sorted({context_id for _, context_id, _ in winners})
    if "STRUCTURAL_RESET" in context_ids and len(context_ids) > 1:
        winners = [item for item in winners if item[1] != "STRUCTURAL_RESET"]
        aliases = sorted({alias for _, _, alias in winners})
        context_ids = sorted({context_id for _, context_id, _ in winners})
    if len(context_ids) != 1:
        return {
            "context_id": "AMBIGUOUS_CONTEXT_EVENT",
            "disposition": "HARD_VETO",
            "match_basis": "TOKEN_BOUNDED_HARD_CONTEXT_OR_RESET",
            "match_tier": tier,
            "matched_aliases": aliases,
        }, comparisons
    context_id = context_ids[0]
    record = next(
        (context for context in spec["context_classes"] if context["context_id"] == context_id),
        {"context_id": "STRUCTURAL_RESET", "disposition": "HARD_VETO"},
    )
    return {
        **canonical_clone_v1(record),
        "match_basis": "TOKEN_BOUNDED_HARD_CONTEXT_OR_RESET",
        "match_tier": tier,
        "matched_aliases": aliases,
    }, comparisons


def _context_class(
    surface: str, spec: Mapping[str, Any], *, allow_bounded: bool
) -> tuple[dict[str, Any] | None, int]:
    exact: list[dict[str, Any]] = []
    for record in spec["context_classes"]:
        tier, aliases = _exact_matches(surface, record["aliases"])
        if tier is not None:
            exact.append(
                {
                    **canonical_clone_v1(record),
                    "match_tier": tier,
                    "matched_aliases": aliases,
                }
            )
    reset_tier, reset_aliases = _exact_matches(surface, spec["structural_reset_aliases"])
    if reset_tier is not None:
        exact.append(
            {
                "context_id": "STRUCTURAL_RESET",
                "disposition": "HARD_VETO",
                "match_tier": reset_tier,
                "matched_aliases": reset_aliases,
            }
        )
    hard_component, comparisons = _hard_context_component_event(surface, spec, allow_bounded=False)
    if hard_component is not None:
        exact.append(hard_component)
    if not allow_bounded or any(item["disposition"] == "HARD_VETO" for item in exact):
        return _select_context_event(exact), comparisons
    bounded: list[dict[str, Any]] = []
    for record in spec["context_classes"]:
        aliases, count = _bounded_matches(surface, record["aliases"])
        comparisons += count
        if aliases:
            bounded.append(
                {
                    **canonical_clone_v1(record),
                    "match_tier": "ONE_BASE_CHARACTER_EDIT_AFTER_ALL_EXACT_MISSES",
                    "matched_aliases": aliases,
                }
            )
    reset_aliases, count = _bounded_matches(surface, spec["structural_reset_aliases"])
    comparisons += count
    if reset_aliases:
        bounded.append(
            {
                "context_id": "STRUCTURAL_RESET",
                "disposition": "HARD_VETO",
                "match_tier": "ONE_BASE_CHARACTER_EDIT_AFTER_ALL_EXACT_MISSES",
                "matched_aliases": reset_aliases,
            }
        )
    hard_component, count = _hard_context_component_event(surface, spec, allow_bounded=True)
    comparisons += count
    if hard_component is not None:
        bounded.append(hard_component)
    if exact:
        bounded = [item for item in bounded if item["disposition"] == "HARD_VETO"]
    return _select_context_event([*exact, *bounded]), comparisons


def _owner_context(
    branch: Mapping[str, Any],
    pages: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any],
    context_event_plans: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    branch_ordinal = branch["page_ordinal"]
    branch_sequence = branch["page_sequence"]
    budget = spec["limits"]["context_page_budget"]
    events = []
    for page_ordinal in range(max(0, branch_ordinal - budget), branch_ordinal + 1):
        page = pages[page_ordinal]
        distance = branch_sequence - page["page_sequence"]
        if not 0 <= distance <= budget:
            continue
        stop = branch["start"] if page_ordinal == branch_ordinal else len(page["lines"])
        events.extend(
            {
                **event,
                "page_distance": distance,
            }
            for event in context_event_plans[page_ordinal]["events"]
            if event["stop"] <= stop
        )
    if not events:
        return {
            "disposition": "OWNER_REQUIRED_FAIL_CLOSED",
            "reason": "EXPLICIT_OWNER_NOT_FOUND_INSIDE_CONTEXT_PAGE_BUDGET",
        }
    closest = max(
        events,
        key=lambda item: (item["page_ordinal"], item["line_stop_exclusive"], item["line_ordinal"]),
    )
    if (
        closest["disposition"] != "REQUIRED_OWNER"
        or closest["context_id"] != spec["required_owner_context_id"]
    ):
        return {
            "closest_context_event": closest,
            "disposition": "OWNER_REQUIRED_FAIL_CLOSED",
            "reason": "CLOSEST_CONTEXT_IS_HARD_VETO_OR_STRUCTURAL_RESET",
        }
    owner_sequence = closest["page_sequence"]
    observed_sequences = {page["page_sequence"] for page in pages}
    if any(
        sequence not in observed_sequences
        for sequence in range(owner_sequence + 1, branch_sequence)
    ):
        return {
            "closest_context_event": closest,
            "disposition": "OWNER_REQUIRED_FAIL_CLOSED",
            "reason": "OWNER_CARRY_HAS_UNOBSERVED_INTERVENING_PAGE",
        }
    distance = closest["page_distance"]
    return {
        "context_id": closest["context_id"],
        "disposition": "EXPLICIT_OWNER_CONTEXT_ACCEPTED_FOR_PROPOSAL",
        "event_evidence": canonical_clone_v1(closest["evidence"]),
        "evidence": canonical_clone_v1(closest["evidence"][0]),
        "match_tier": closest["match_tier"],
        "mode": "SAME_PAGE" if distance == 0 else f"CARRIED_FROM_PREVIOUS_PAGE_{distance}",
        "page_distance": distance,
        "surface": closest["surface"],
    }


def _row_match(
    surfaces: Sequence[str], spec: Mapping[str, Any]
) -> tuple[dict[str, Any] | None, int]:
    exact_rows = []
    for row in spec["row_axis"]:
        for surface in surfaces:
            tier, aliases = _exact_matches(surface, row["aliases"])
            if tier is not None:
                exact_rows.append((tier, surface, row, aliases))
    exact_ambiguities = []
    for ambiguity in spec["source_only_ambiguities"]:
        for surface in surfaces:
            tier, aliases = _exact_matches(surface, ambiguity["aliases"])
            if tier is not None:
                exact_ambiguities.append((tier, surface, ambiguity, aliases))
    exact = [*exact_rows, *exact_ambiguities]
    if exact:
        best = min(_TIER_ORDER[item[0]] for item in exact)
        rows = [item for item in exact_rows if _TIER_ORDER[item[0]] == best]
        ambiguities = [item for item in exact_ambiguities if _TIER_ORDER[item[0]] == best]
        semantic_ids = {item[2]["semantic_id"] for item in rows}
        if ambiguities or len(semantic_ids) != 1:
            candidates = set(semantic_ids)
            candidates.update(
                semantic_id
                for item in ambiguities
                for semantic_id in item[2]["candidate_semantic_ids"]
            )
            return {
                "candidate_semantic_ids": sorted(candidates),
                "matched_aliases": sorted(
                    {alias for item in [*rows, *ambiguities] for alias in item[3]}
                ),
                "match_tier": exact[0][0],
                "reason": (
                    ambiguities[0][2]["reason"]
                    if len(ambiguities) == 1
                    else "MULTIPLE_EXACT_SEMANTIC_ROW_CANDIDATES"
                ),
                "semantic_id": None,
                "surface": exact[0][1],
            }, 0
        tier, surface, row, aliases = rows[0]
        return {
            "candidate_semantic_ids": [row["semantic_id"]],
            "matched_aliases": aliases,
            "match_tier": tier,
            "reason": "UNIQUE_EXACT_SEMANTIC_ROW_CANDIDATE",
            "semantic_id": row["semantic_id"],
            "surface": surface,
        }, 0

    comparisons = 0
    bounded_rows = []
    for row in spec["row_axis"]:
        if not row["bounded_edit_on_exact_miss"]:
            continue
        for surface in surfaces:
            aliases, count = _bounded_matches(surface, row["aliases"])
            comparisons += count
            if aliases:
                bounded_rows.append((surface, row, aliases))
    bounded_ambiguities = []
    for ambiguity in spec["source_only_ambiguities"]:
        for surface in surfaces:
            aliases, count = _bounded_matches(surface, ambiguity["aliases"])
            comparisons += count
            if aliases:
                bounded_ambiguities.append((surface, ambiguity, aliases))
    candidates = {item[1]["semantic_id"] for item in bounded_rows}
    candidates.update(
        semantic_id
        for item in bounded_ambiguities
        for semantic_id in item[1]["candidate_semantic_ids"]
    )
    if not candidates:
        return None, comparisons
    if bounded_ambiguities or len(candidates) != 1:
        return {
            "candidate_semantic_ids": sorted(candidates),
            "matched_aliases": sorted(
                {
                    alias
                    for _, _, aliases in [*bounded_rows, *bounded_ambiguities]
                    for alias in aliases
                }
            ),
            "match_tier": "ONE_BASE_CHARACTER_EDIT_AFTER_ALL_EXACT_MISSES",
            "reason": "BOUNDED_EDIT_HAS_MULTIPLE_OR_SOURCE_ONLY_CANDIDATES",
            "semantic_id": None,
            "surface": [*bounded_rows, *bounded_ambiguities][0][0],
        }, comparisons
    surface, row, aliases = bounded_rows[0]
    return {
        "candidate_semantic_ids": [row["semantic_id"]],
        "matched_aliases": aliases,
        "match_tier": "ONE_BASE_CHARACTER_EDIT_AFTER_ALL_EXACT_MISSES",
        "reason": "UNIQUE_ONE_EDIT_SEMANTIC_ROW_CANDIDATE_AFTER_ALL_EXACT_MISSES",
        "semantic_id": row["semantic_id"],
        "surface": surface,
    }, comparisons


def _body_and_rows(
    branch: Mapping[str, Any],
    page: Mapping[str, Any],
    spec: Mapping[str, Any],
    context_fence_indices: set[int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, bool]:
    body = []
    comparisons = 0
    maximum = spec["limits"]["maximum_body_lines_per_page"]
    lines = page["lines"]
    tail_length = len(lines) - branch["stop"]
    boundary_seen = False
    for offset in range(min(tail_length, maximum)):
        line_index = branch["stop"] + offset
        boundary = line_index in context_fence_indices
        if not boundary:
            surfaces = _cohesive_nonvalue_surfaces(
                lines,
                line_index,
                spec["limits"]["branch_line_span"],
                context_fence_indices,
            )
            branch_boundary, count = _branch_match(surfaces, spec)
            comparisons += count
            boundary = branch_boundary is not None
        if boundary:
            boundary_seen = True
            break
        body.append(lines[line_index])
    limit_reached = tail_length > maximum and not boundary_seen
    semantic = [(index, line) for index, line in enumerate(body) if not _is_value(line)]
    candidates = []
    max_span = spec["limits"]["row_label_line_span"]
    for ordinal, (_, line) in enumerate(semantic):
        windows = [[line]]
        for span in range(2, max_span + 1):
            if ordinal + span > len(semantic):
                break
            if not _can_join_wrapped_label(
                semantic[ordinal + span - 2], semantic[ordinal + span - 1], body
            ):
                break
            windows.append([item for _, item in semantic[ordinal : ordinal + span]])
        surfaces = [_joined(window) for window in windows]
        matched, count = _row_match(surfaces, spec)
        comparisons += count
        if matched is None:
            continue
        span = next(
            value
            for value in range(len(surfaces), 0, -1)
            if surfaces[value - 1] == matched["surface"]
        )
        selected = semantic[ordinal : ordinal + span]
        material = {
            **matched,
            "evidence": [
                _line_evidence(item, page_sequence=page["page_sequence"]) for _, item in selected
            ],
            "page_sequence": page["page_sequence"],
        }
        candidates.append(
            {
                **material,
                "body_indices": [index for index, _ in selected],
                "proposal_id": "asrgv1:row:" + canonical_json_sha256_v1(material),
                "semantic_start": ordinal,
                "semantic_stop": ordinal + span,
            }
        )
    proposals = []
    occupied: set[int] = set()
    for candidate in sorted(
        candidates,
        key=lambda item: (
            item["semantic_start"],
            _TIER_ORDER[item["match_tier"]],
            item["semantic_start"] - item["semantic_stop"],
            item["proposal_id"],
        ),
    ):
        covered = set(range(candidate["semantic_start"], candidate["semantic_stop"]))
        if covered & occupied:
            continue
        occupied.update(covered)
        proposals.append(candidate)
    return body, proposals, comparisons, limit_reached


def _union(boxes: Sequence[Sequence[int]]) -> list[int]:
    return [
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    ]


def _geometry(
    branch: Mapping[str, Any],
    body: Sequence[Mapping[str, Any]],
    page: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    branch_lines = page["lines"][branch["start"] : branch["stop"]]
    candidate_lines = [*branch_lines, *body]
    label_indices = {index for row in rows for index in row["body_indices"]}
    atoms = []
    for ordinal, line in enumerate(candidate_lines):
        body_index = ordinal - len(branch_lines)
        kind = "LABEL" if body_index in label_indices else "VALUE" if _is_value(line) else "OTHER"
        atoms.append(
            {
                "atom_id": f"p{page['page_sequence']}:l{line['source_line_index']}",
                "bbox": canonical_clone_v1(line["bbox"]),
                "kind": kind,
            }
        )
    return resolve_accounting_table_geometry_v2(
        atoms,
        page_width=page["page_width"],
        page_height=page["page_height"],
        region_bbox=_union([line["bbox"] for line in candidate_lines]),
    )


def _geometry_support(rows: list[dict[str, Any]], geometry: Mapping[str, Any]) -> None:
    assigned_rows = {
        item["row_ordinal"]
        for item in geometry["assignments"]
        if item["status"] == "ASSIGNED_TO_UNIQUE_ROW_LANE"
    }
    row_by_atom = {
        atom_id: band["row_ordinal"]
        for band in geometry["row_bands"]
        for atom_id in band["atom_ids"]
    }
    for row in rows:
        atom_ids = {
            f"p{evidence['page_sequence']}:l{evidence['source_line_index']}"
            for evidence in row["evidence"]
        }
        label_ordinals = sorted({row_by_atom[item] for item in atom_ids if item in row_by_atom})
        supported = sorted(set(label_ordinals) & assigned_rows)
        row["geometry_support"] = {
            "assigned_value_row_ordinals": supported,
            "label_row_ordinals": label_ordinals,
            "visible_unique_value_lane_required": True,
        }
        if row["semantic_id"] is None:
            row["status"] = "SOURCE_ONLY_AMBIGUOUS"
        elif supported:
            row["status"] = "SEMANTIC_ROW_TEXT_AND_GEOMETRY_PROPOSAL_REQUIRES_REPLAY"
        else:
            row["status"] = "TEXT_ROLE_PROPOSAL_MISSING_ROW_VALUE_GEOMETRY"


def _scoped_receipt(
    *,
    branch: Mapping[str, Any],
    owner: Mapping[str, Any],
    page: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any],
) -> dict[str, Any]:
    enforcement = spec["scoped_table"]["enforcement"]
    if owner["mode"] != "SAME_PAGE":
        return {
            "enforcement": enforcement,
            "reason": "SCOPED_TABLE_V1_REQUIRES_SAME_PAGE_OWNER_EVIDENCE",
            "status": "NOT_APPLICABLE_TO_EXPLICIT_CROSS_PAGE_OWNER_CARRY_RECEIPT",
        }
    supported = [
        row
        for row in rows
        if row["semantic_id"] is not None
        and row["status"] == "SEMANTIC_ROW_TEXT_AND_GEOMETRY_PROPOSAL_REQUIRES_REPLAY"
    ]
    counts: dict[str, int] = {}
    for row in supported:
        counts[row["semantic_id"]] = counts.get(row["semantic_id"], 0) + 1
    unique = [row for row in supported if counts[row["semantic_id"]] == 1]
    if len(unique) < 2:
        return {
            "enforcement": enforcement,
            "reason": "AT_LEAST_TWO_UNIQUE_SEMANTIC_ROWS_REQUIRED",
            "status": "NOT_RUN_INSUFFICIENT_ROLE_TOPOLOGY",
        }
    scoped = spec["scoped_table"]
    scoped_spec = {
        "continuation_aliases": scoped["continuation_aliases"],
        "family_id": spec["family_id"],
        "format_version": SCOPED_SPEC_FORMAT_VERSION,
        "layout_modes": scoped["layout_modes"],
        "limits": scoped["limits"],
        "owner_aliases": [owner["surface"]],
        "require_trailing_total_for_roles_as_columns": scoped[
            "require_trailing_total_for_roles_as_columns"
        ],
        "role_axis": [{"aliases": [row["surface"]], "role": row["semantic_id"]} for row in unique],
        "scope_axis": [
            {
                "aliases": [branch["surface"]],
                "disposition": "TARGET",
                "scope_id": spec["family_id"],
            },
            {
                "aliases": scoped["hard_veto_scope_aliases"],
                "disposition": "HARD_VETO_MIXED",
                "scope_id": "NON_TARGET_SCOPE",
            },
        ],
        "structural_reset_aliases": spec["structural_reset_aliases"],
        "target_scope_id": spec["family_id"],
        "trailing_total_aliases": scoped["trailing_total_aliases"],
    }
    try:
        result = build_accounting_scoped_table_graph_v1([page], scoped_spec)
    except AccountingScopedTableGraphV1Error:
        return {
            "enforcement": enforcement,
            "reason": "SCOPED_TABLE_V1_REJECTED_DYNAMIC_EXACT_SPEC",
            "result": None,
            "status": "SHARED_SCOPED_TABLE_FAIL_CLOSED",
        }
    if not result["graphs"]:
        return {
            "enforcement": enforcement,
            "reason": "SCOPED_TABLE_V1_RETURNED_NO_COMPLETE_GRAPH",
            "result": result,
            "status": "SHARED_SCOPED_TABLE_FAIL_CLOSED",
        }
    return {
        "enforcement": enforcement,
        "result": result,
        "spec_id": "asrgv1:scoped_spec:" + canonical_json_sha256_v1(scoped_spec),
        "status": "SHARED_SCOPED_TABLE_PROPOSAL_RETAINED_NO_MAPPING_AUTHORITY",
    }


def _public_branch(branch: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: canonical_clone_v1(branch[key])
        for key in (
            "branch_id",
            "evidence",
            "match_basis",
            "matched_aliases",
            "matched_component_ids",
            "match_tier",
            "page_sequence",
            "surface",
        )
    }


def _public_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            key: canonical_clone_v1(value)
            for key, value in row.items()
            if key not in {"body_indices", "semantic_start", "semantic_stop"}
        }
        for row in rows
    ]


def _near_region(
    branch: Mapping[str, Any],
    owner: Mapping[str, Any],
    reason: str,
    *,
    body_limit_reached: bool | None = None,
    geometry: Mapping[str, Any] | None = None,
    rows: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    material = {
        "body_limit_reached": body_limit_reached,
        "branch": _public_branch(branch),
        "owner_context": canonical_clone_v1(owner),
        "reason": reason,
        "source_only_geometry_proposal": (
            canonical_clone_v1(geometry) if geometry is not None else None
        ),
        "source_only_row_proposals": _public_rows(rows),
        "status": "SOURCE_ONLY_NEAR_REGION_FAIL_CLOSED",
    }
    return {**material, "near_region_id": "asrgv1:near:" + canonical_json_sha256_v1(material)}


def _build(
    region_pages: Sequence[Mapping[str, Any]], family_spec: Mapping[str, Any]
) -> dict[str, Any]:
    pages = _pages(region_pages)
    spec = _spec(family_spec)
    context_event_plans, comparisons, context_plan_metrics = _context_event_plan(pages, spec)
    branches, count, branch_enumeration = _branch_candidates(pages, spec, context_event_plans)
    comparisons += count
    regions = []
    near_regions = []
    for branch in branches:
        owner = _owner_context(branch, pages, spec, context_event_plans)
        context_fences = context_event_plans[branch["page_ordinal"]]["fence_indices"]
        if owner["disposition"] != "EXPLICIT_OWNER_CONTEXT_ACCEPTED_FOR_PROPOSAL":
            page = pages[branch["page_ordinal"]]
            body, rows, count, limit_reached = _body_and_rows(branch, page, spec, context_fences)
            comparisons += count
            geometry = None
            if body:
                geometry = _geometry(branch, body, page, rows)
                _geometry_support(rows, geometry)
            near_regions.append(
                _near_region(
                    branch,
                    owner,
                    owner["reason"],
                    body_limit_reached=limit_reached,
                    geometry=geometry,
                    rows=rows,
                )
            )
            continue
        page = pages[branch["page_ordinal"]]
        body, rows, count, limit_reached = _body_and_rows(branch, page, spec, context_fences)
        comparisons += count
        if not body:
            near_regions.append(_near_region(branch, owner, "BRANCH_HAS_NO_BOUNDED_BODY"))
            continue
        geometry = _geometry(branch, body, page, rows)
        _geometry_support(rows, geometry)
        shared = _scoped_receipt(branch=branch, owner=owner, page=page, rows=rows, spec=spec)
        shared_failed = shared["status"] == "SHARED_SCOPED_TABLE_FAIL_CLOSED"
        scoped_gate_required = (
            spec["scoped_table"]["enforcement"]
            == ScopedTableEnforcementV1.REQUIRED_PROMOTION_GATE.value
        )
        promotion_eligible = not limit_reached and not (shared_failed and scoped_gate_required)
        material = {
            "adaptive_geometry_v2": geometry,
            "body_limit_reached": limit_reached,
            "branch": _public_branch(branch),
            "owner_context": owner,
            "promotion_eligible": promotion_eligible,
            "row_proposals": _public_rows(rows),
            "shared_scoped_table_v1": shared,
            "status": (
                "SEMANTIC_REGION_PROPOSAL_REQUIRES_FAMILY_POLICY_REPLAY"
                if promotion_eligible
                else "SEMANTIC_REGION_PROPOSAL_FAIL_CLOSED"
            ),
        }
        regions.append(
            {**material, "region_id": "asrgv1:region:" + canonical_json_sha256_v1(material)}
        )
    bounded_absences = []
    if not branches:
        bounded_absences.append(
            {
                "page_sequences": [page["page_sequence"] for page in pages],
                "reason": "NO_BRANCH_IN_CALLER_BOUNDED_PAGES",
                "status": "BOUNDED_ABSENCE_NO_GLOBAL_CORPUS_CLAIM",
            }
        )
    bounded_absences.extend(
        {
            "near_region_id": item["near_region_id"],
            "reason": item["reason"],
            "status": "BOUNDED_ABSENCE_FROM_ACCEPTED_SEMANTIC_REGION",
        }
        for item in near_regions
    )
    material = {
        "bounded_absences": bounded_absences,
        "claim_boundary": CLAIM_BOUNDARY,
        "evidence_binding": {
            "canonical_page_evidence_sha256": canonical_json_sha256_v1(pages),
            "family_spec_id": "asrgv1:spec:" + canonical_json_sha256_v1(spec),
        },
        "family_id": spec["family_id"],
        "format_version": FORMAT_VERSION,
        "matcher_metrics": {"approximate_alias_comparison_count": comparisons},
        "metrics": {
            "bounded_absence_count": len(bounded_absences),
            "branch_candidate_count": len(branches),
            "branch_enumerated_candidate_count": branch_enumeration["enumerated_candidate_count"],
            "branch_component_fallback_candidate_count": sum(
                branch["match_basis"] == "DECLARATIVE_BRANCH_COMPONENT" for branch in branches
            ),
            "branch_overlap_suppressed_candidate_count": branch_enumeration[
                "overlap_suppressed_candidate_count"
            ],
            "context_event_count": context_plan_metrics["selected_event_count"],
            "context_event_enumerated_count": context_plan_metrics["enumerated_event_count"],
            "context_event_overlap_suppressed_count": context_plan_metrics[
                "overlap_suppressed_event_count"
            ],
            "context_event_wrapped_count": context_plan_metrics["wrapped_event_count"],
            "explicit_zero_line_page_count": sum(not page["lines"] for page in pages),
            "near_region_count": len(near_regions),
            "region_count": len(regions),
            "scoped_table_advisory_failure_region_count": sum(
                region["shared_scoped_table_v1"]["status"] == "SHARED_SCOPED_TABLE_FAIL_CLOSED"
                and region["shared_scoped_table_v1"]["enforcement"]
                == ScopedTableEnforcementV1.ADVISORY_CHALLENGER.value
                for region in regions
            ),
            "scoped_table_required_failure_region_count": sum(
                region["shared_scoped_table_v1"]["status"] == "SHARED_SCOPED_TABLE_FAIL_CLOSED"
                and region["shared_scoped_table_v1"]["enforcement"]
                == ScopedTableEnforcementV1.REQUIRED_PROMOTION_GATE.value
                for region in regions
            ),
        },
        "near_regions": near_regions,
        "regions": sorted(
            regions,
            key=lambda item: (
                item["branch"]["page_sequence"],
                item["branch"]["evidence"][0]["bbox"][1],
                item["region_id"],
            ),
        ),
        "safety": {
            "accounting_or_mapping_authority": False,
            "all_hard_context_interval_coverage_blocks_owner_events": True,
            "bounded_edit_runs_when_any_exact_row_candidate_exists": False,
            "branch_lower_tier_can_override_overlapping_higher_tier_candidate": False,
            "context_event_plan_is_reused_for_branch_body_and_owner_scans": True,
            "empty_page_creates_structural_reset": False,
            "family_schema_or_report_norm_id_known": False,
            "lower_priority_interval_candidates_cannot_leak_through_suppressed_higher_coverage": True,
            "provider_line_or_page_serialization_controls_order": False,
            "scoped_table_advisory_failure_can_coexist_with_otherwise_eligible_region": True,
            "scoped_table_advisory_failure_bypasses_other_required_gates": False,
            "scoped_table_advisory_failure_is_promotion_authority": False,
            "scoped_table_required_failure_can_promote_region": False,
            "spatially_distinct_lower_tier_branch_candidates_are_retained": True,
            "text_or_geometry_alone_can_map": False,
            "zero_search_hit_is_global_absence": False,
        },
        "status": (
            "SEMANTIC_REGION_PROPOSAL_ENUMERATION_WITH_NEAR_REGIONS"
            if near_regions
            else "SEMANTIC_REGION_PROPOSAL_ENUMERATION"
        ),
    }
    return {**material, "result_id": "asrgv1:result:" + canonical_json_sha256_v1(material)}


def build_accounting_semantic_region_graph_v1(
    region_pages: Sequence[Mapping[str, Any]], family_spec: Mapping[str, Any]
) -> dict[str, Any]:
    """Build family-neutral semantic-region and shared-geometry proposals."""

    return _build(region_pages, family_spec)


def validate_accounting_semantic_region_graph_replay_v1(
    value: Any,
    region_pages: Sequence[Mapping[str, Any]],
    family_spec: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild generic matching, context, geometry, and every identity exactly."""

    if type(value) is not dict or value.get("format_version") != FORMAT_VERSION:
        raise _error("semantic-region graph result identity drifted")
    identity = value.get("result_id")
    if type(identity) is not str:
        raise _error("semantic-region graph result ID drifted")
    material = canonical_clone_v1(value)
    material.pop("result_id", None)
    if identity != "asrgv1:result:" + canonical_json_sha256_v1(material):
        raise _error("semantic-region graph content identity drifted")
    rebuilt = _build(region_pages, family_spec)
    if not same_typed_json_v1(value, rebuilt):
        raise _error("semantic-region graph does not replay exactly")
    return rebuilt
