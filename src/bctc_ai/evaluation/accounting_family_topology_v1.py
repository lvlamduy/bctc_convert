"""Bank-blind declarative parent/child topology discovery for TM families.

This module is deliberately narrower than a family mapper.  It enumerates
semantic clusters from a complete document using fresh VietOCR labels and
source-bound line geometry, while leaving period, unit, numeric, accounting,
schema, and mapping decisions to independent shared primitives and the family
evaluation layer.

The same engine supports explicit or structurally implied parents, required
and optional siblings, declarative alternative core-role combinations,
reordered rows, wrapped labels, hard-negative families, and structural resets.
It also proves the smallest role combination that is
unique in the supplied document by exhausting pairs before triples.  No bank,
filename, note number, page selector, reporting year, or schema ID is accepted
by the specification.
"""

from __future__ import annotations

import itertools
import re
from bisect import bisect_left, bisect_right
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
    "SPEC_FORMAT_VERSION_V2",
    "SPEC_FORMAT_VERSION_V3",
    "SPEC_FORMAT_VERSION_V4",
    "AccountingFamilyTopologyV1Error",
    "build_accounting_family_topology_scan_v1",
    "compile_accounting_family_topology_spec_v1",
    "enumerate_accounting_family_role_occurrences_v1",
    "validate_accounting_family_topology_scan_replay_v1",
]


FORMAT_VERSION = "ACCOUNTING_FAMILY_TOPOLOGY_SCAN_V1"
SPEC_FORMAT_VERSION = "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V1"
SPEC_FORMAT_VERSION_V2 = "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V2"
SPEC_FORMAT_VERSION_V3 = "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V3"
SPEC_FORMAT_VERSION_V4 = "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V4"
CLAIM_BOUNDARY = (
    "COMPLETE_DOCUMENT_BANK_BLIND_FRESH_VIETOCR_PRIMARY_EXACT_BOUND_SOURCE_TEXT_"
    "CHALLENGER_PARENT_REQUIRED_OPTIONAL_SIBLING_"
    "WRAPPED_LABEL_FLEXIBLE_ORDER_HARD_NEGATIVE_STRUCTURAL_RESET_AND_PAIR_BEFORE_"
    "TRIPLE_UNIQUENESS_PROPOSAL_ONLY_NO_PERIOD_UNIT_NUMERIC_ACCOUNTING_SCHEMA_"
    "MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_page_year_used_for_matching": False,
    "continuation_authority": False,
    "contextual_roles_use_page_geometry_when_provider_order_drifts": True,
    "family_layout_logic_is_declarative": True,
    "mapping_authority": False,
    "numeric_authority": False,
    "pair_combinations_exhausted_before_triples": True,
    "period_or_unit_authority": False,
    "persisted_result_self_authenticating": False,
    "reordered_siblings_permitted": True,
    "schema_authority": False,
    "source_bound_text_challenger_requires_exact_alias_and_complete_topology": True,
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
_SPEC_V2_FIELDS = {
    *_SPEC_FIELDS,
    "presence_evidence_mode",
    "required_role_combinations",
}
_SPEC_V3_FIELDS = _SPEC_V2_FIELDS
_SPEC_V4_FIELDS = {*_SPEC_V3_FIELDS, "required_role_pools"}
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
    "STRUCTURAL_GROUP",
    "SUBTOTAL",
    "TOTAL",
}
_PRESENCE = {"OPTIONAL", "REQUIRED"}
_MATCH_MODES = {
    "EXACT_NORMALIZED",
    "CONTAINS_NORMALIZED_PHRASE",
    "CONTAINS_ORDERED_NORMALIZED_PHRASES",
}
_PARENT_RESOLUTION = {"EXPLICIT_ONLY", "EXPLICIT_OR_UNIQUE_REQUIRED_CHILD_CLUSTER"}
_PRESENCE_EVIDENCE_MODES = {
    "GLOBAL_CORE_HITS",
    "WITHIN_EXPLICIT_PARENT_CLUSTER",
}
_ENUMERATION_PREFIX = re.compile(
    r"^\s*(?:(?:\d{1,3}(?:\.\d{1,3})*)\s*[.),\-:]|"
    r"(?:\(\d{1,3}(?:\.\d{1,3})*\))|(?:[ivxlcdm]{1,8}|[a-z])[.)\-:])\s+",
    flags=re.IGNORECASE,
)
_BARE_NUMERIC_HEADING_PREFIX = re.compile(r"^\s*\d{1,3}(?:\.\d{1,3})*\s+(?=[A-ZÀ-ỴĐ]{2})")


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


def _nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise _error(f"{label} must be one nonnegative exact integer")
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
    if type(value) is not dict or (
        set(value) != _SPEC_FIELDS
        and set(value) != _SPEC_V2_FIELDS
        and set(value) != _SPEC_V3_FIELDS
        and set(value) != _SPEC_V4_FIELDS
    ):
        raise _error("accounting family topology spec fields drifted")
    family_id = _nonempty_string(value["family_id"], "family ID")
    spec_version = value["format_version"]
    if spec_version not in {
        SPEC_FORMAT_VERSION,
        SPEC_FORMAT_VERSION_V2,
        SPEC_FORMAT_VERSION_V3,
        SPEC_FORMAT_VERSION_V4,
    }:
        raise _error("accounting family topology spec version drifted")
    if (spec_version == SPEC_FORMAT_VERSION) is not (set(value) == _SPEC_FIELDS):
        raise _error("accounting family topology spec version/field set drifted")
    if (spec_version == SPEC_FORMAT_VERSION_V4) is not (set(value) == _SPEC_V4_FIELDS):
        raise _error("accounting family topology V4 spec version/field set drifted")
    parent = value["parent"]
    if type(parent) is not dict or set(parent) != {"aliases", "resolution_mode", "role"}:
        raise _error("accounting family parent spec fields drifted")
    parent_role = _nonempty_string(parent["role"], "parent role")
    resolution_mode = parent["resolution_mode"]
    if type(resolution_mode) is not str or resolution_mode not in _PARENT_RESOLUTION:
        raise _error("accounting family parent resolution mode drifted")

    raw_children = value["children"]
    if type(raw_children) is not list or not raw_children:
        raise _error("accounting family needs at least one child role")
    children: list[dict[str, Any]] = []
    roles = {parent_role}
    for raw in raw_children:
        expected_child_fields = (
            {"matchers", "presence", "role", "role_kind"}
            if spec_version in {SPEC_FORMAT_VERSION_V3, SPEC_FORMAT_VERSION_V4}
            else {"aliases", "presence", "role", "role_kind"}
        )
        if type(raw) is not dict or set(raw) != expected_child_fields:
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
        if spec_version in {SPEC_FORMAT_VERSION_V3, SPEC_FORMAT_VERSION_V4}:
            raw_matchers = raw["matchers"]
            if type(raw_matchers) is not list or not raw_matchers:
                raise _error("contextual accounting family role needs at least one matcher")
            matchers = []
            seen_matchers: set[tuple[tuple[str, ...], str | None, bool, bool, bool, bool, str]] = (
                set()
            )
            for raw_matcher in raw_matchers:
                matcher_fields = set(raw_matcher) if type(raw_matcher) is dict else set()
                match_mode = (
                    raw_matcher.get("match_mode", "EXACT_NORMALIZED")
                    if type(raw_matcher) is dict
                    else None
                )
                if (
                    type(raw_matcher) is not dict
                    or not {"aliases", "within_role"} <= matcher_fields
                    or not matcher_fields
                    <= {
                        "aliases",
                        "allow_decorative_parenthetical_removal",
                        "allow_trailing_organization_qualifier",
                        "match_mode",
                        "normalize_single_member_abbreviations",
                        "presence_anchor",
                        "within_role",
                    }
                    or (
                        raw_matcher["within_role"] is not None
                        and (
                            type(raw_matcher["within_role"]) is not str
                            or not raw_matcher["within_role"]
                        )
                    )
                    or type(raw_matcher.get("presence_anchor", True)) is not bool
                    or match_mode not in _MATCH_MODES
                    or type(raw_matcher.get("allow_trailing_organization_qualifier", False))
                    is not bool
                    or type(raw_matcher.get("allow_decorative_parenthetical_removal", False))
                    is not bool
                    or type(raw_matcher.get("normalize_single_member_abbreviations", False))
                    is not bool
                    or (
                        raw_matcher.get("allow_trailing_organization_qualifier", False)
                        and raw_matcher["within_role"] is None
                    )
                    or (
                        match_mode != "EXACT_NORMALIZED"
                        and (
                            raw_matcher.get("presence_anchor", True)
                            or role_kind == "STRUCTURAL_GROUP"
                        )
                    )
                ):
                    raise _error("contextual accounting family matcher fields drifted")
                matcher_aliases = _aliases(
                    raw_matcher["aliases"], f"{role} contextual matcher aliases"
                )
                presence_anchor = raw_matcher.get("presence_anchor", True)
                if match_mode != "EXACT_NORMALIZED" and (
                    any(
                        len(alias.split()) < 2 or len(alias.replace(" ", "")) < 8
                        for alias in matcher_aliases
                    )
                    or (
                        match_mode == "CONTAINS_ORDERED_NORMALIZED_PHRASES"
                        and len(matcher_aliases) < 2
                    )
                ):
                    raise _error("normalized phrase matcher is too weak")
                allow_trailing_organization_qualifier = raw_matcher.get(
                    "allow_trailing_organization_qualifier", False
                )
                allow_decorative_parenthetical_removal = raw_matcher.get(
                    "allow_decorative_parenthetical_removal", False
                )
                normalize_single_member_abbreviations = raw_matcher.get(
                    "normalize_single_member_abbreviations", False
                )
                signature = (
                    tuple(matcher_aliases),
                    raw_matcher["within_role"],
                    presence_anchor,
                    allow_decorative_parenthetical_removal,
                    allow_trailing_organization_qualifier,
                    normalize_single_member_abbreviations,
                    match_mode,
                )
                if signature in seen_matchers:
                    raise _error("contextual accounting family matchers must be unique")
                seen_matchers.add(signature)
                matcher = {
                    "aliases": matcher_aliases,
                    "presence_anchor": presence_anchor,
                    "within_role": raw_matcher["within_role"],
                }
                if allow_trailing_organization_qualifier:
                    matcher["allow_trailing_organization_qualifier"] = True
                if allow_decorative_parenthetical_removal:
                    matcher["allow_decorative_parenthetical_removal"] = True
                if normalize_single_member_abbreviations:
                    matcher["normalize_single_member_abbreviations"] = True
                if match_mode != "EXACT_NORMALIZED":
                    matcher["match_mode"] = match_mode
                matchers.append(matcher)
        else:
            matchers = [
                {
                    "aliases": _aliases(raw["aliases"], f"{role} aliases"),
                    "presence_anchor": True,
                    "within_role": None,
                }
            ]
        children.append(
            {
                "matchers": matchers,
                "preferred_ordinal": len(children),
                "presence": presence,
                "role": role,
                "role_kind": role_kind,
            }
        )
    if spec_version in {SPEC_FORMAT_VERSION_V3, SPEC_FORMAT_VERSION_V4}:
        child_roles = {child["role"] for child in children}
        role_kind_by_role = {child["role"]: child["role_kind"] for child in children}
        for child in children:
            for matcher in child["matchers"]:
                within_role = matcher["within_role"]
                if within_role is not None and (
                    within_role == child["role"]
                    or within_role not in child_roles
                    or role_kind_by_role[within_role] != "STRUCTURAL_GROUP"
                ):
                    raise _error(
                        "contextual accounting family matcher must reference another structural role"
                    )
        structural_parent: dict[str, str | None] = {}
        for child in children:
            parents = {
                matcher["within_role"]
                for matcher in child["matchers"]
                if matcher["within_role"] is not None
            }
            if child["role_kind"] == "STRUCTURAL_GROUP" and len(parents) > 1:
                raise _error("one structural group cannot have multiple contextual parents")
            structural_parent[child["role"]] = next(iter(parents), None)
        for role in structural_parent:
            seen = {role}
            cursor = structural_parent[role]
            while cursor is not None:
                if cursor in seen:
                    raise _error("contextual accounting family role hierarchy contains a cycle")
                seen.add(cursor)
                cursor = structural_parent[cursor]
    required_roles = [child["role"] for child in children if child["presence"] == "REQUIRED"]
    if spec_version == SPEC_FORMAT_VERSION:
        if not required_roles:
            raise _error("accounting family needs at least one required child role")
        required_role_combinations = [required_roles]
        presence_evidence_mode = "GLOBAL_CORE_HITS"
    else:
        if required_roles:
            raise _error("alternative-core topology roles must use OPTIONAL presence")
        raw_combinations = value["required_role_combinations"]
        if type(raw_combinations) is not list or not raw_combinations:
            raise _error("alternative-core topology needs required role combinations")
        child_roles = {child["role"] for child in children}
        required_role_combinations = []
        seen_combinations: set[tuple[str, ...]] = set()
        for raw_combination in raw_combinations:
            if (
                type(raw_combination) is not list
                or len(raw_combination) not in {1, 2, 3}
                or any(type(role) is not str or role not in child_roles for role in raw_combination)
                or len(raw_combination) != len(set(raw_combination))
            ):
                raise _error("alternative required role combination drifted")
            if len(raw_combination) == 1 and not (
                resolution_mode == "EXPLICIT_ONLY"
                and value["presence_evidence_mode"] == "WITHIN_EXPLICIT_PARENT_CLUSTER"
            ):
                raise _error("single-child core requires one explicit parent-scoped cluster")
            combination = tuple(raw_combination)
            if combination in seen_combinations:
                raise _error("alternative required role combinations must be unique")
            seen_combinations.add(combination)
            required_role_combinations.append(list(combination))
        presence_evidence_mode = value["presence_evidence_mode"]
        if (
            type(presence_evidence_mode) is not str
            or presence_evidence_mode not in _PRESENCE_EVIDENCE_MODES
            or (
                presence_evidence_mode == "WITHIN_EXPLICIT_PARENT_CLUSTER"
                and resolution_mode != "EXPLICIT_ONLY"
            )
        ):
            raise _error("alternative-core presence evidence mode drifted")
    required_role_pools = []
    if spec_version == SPEC_FORMAT_VERSION_V4:
        child_roles = {child["role"] for child in children}
        raw_pools = value["required_role_pools"]
        if type(raw_pools) is not list or not raw_pools:
            raise _error("flexible topology needs at least one required role pool")
        seen_pools: set[frozenset[str]] = set()
        for raw_pool in raw_pools:
            if (
                type(raw_pool) is not dict
                or set(raw_pool) != {"minimum_count", "roles"}
                or type(raw_pool["roles"]) is not list
                or len(raw_pool["roles"]) < 2
                or raw_pool["roles"] != list(dict.fromkeys(raw_pool["roles"]))
                or any(role not in child_roles for role in raw_pool["roles"])
                or type(raw_pool["minimum_count"]) is not int
                or not 2 <= raw_pool["minimum_count"] <= len(raw_pool["roles"])
                or frozenset(raw_pool["roles"]) in seen_pools
            ):
                raise _error("flexible topology required role pool drifted")
            seen_pools.add(frozenset(raw_pool["roles"]))
            required_role_pools.append(canonical_clone_v1(raw_pool))

    limits = value["limits"]
    if type(limits) is not dict or set(limits) != {
        "max_continuation_pages",
        "max_cluster_span_lines",
        "max_label_line_span",
    }:
        raise _error("accounting family topology limits drifted")
    max_label_span = _positive_int(limits["max_label_line_span"], "maximum label line span")
    if max_label_span > 6:
        raise _error("maximum label line span exceeds the bounded generic policy")
    return {
        "children": children,
        "family_id": family_id,
        "hard_negative_aliases": _aliases(
            value["hard_negative_aliases"], "hard-negative", allow_empty=True
        ),
        "limits": {
            "max_continuation_pages": _nonnegative_int(
                limits["max_continuation_pages"], "maximum continuation pages"
            ),
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
        "presence_evidence_mode": presence_evidence_mode,
        "required_role_combinations": required_role_combinations,
        "required_role_pools": required_role_pools,
        "spec_format_version": spec_version,
        "structural_parent_by_role": (
            structural_parent
            if spec_version in {SPEC_FORMAT_VERSION_V3, SPEC_FORMAT_VERSION_V4}
            else {}
        ),
        "structural_reset_aliases": _aliases(
            value["structural_reset_aliases"], "structural reset", allow_empty=True
        ),
    }


def compile_accounting_family_topology_spec_v1(value: Any) -> dict[str, Any]:
    """Compile one declarative family spec for shared non-geometry consumers."""

    return _spec(value)


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


def _one_edit_alias_is_safe(candidate: str, alias: str) -> bool:
    """Permit one-edit rescue only on a sufficiently informative surface.

    One edit on a short generic Vietnamese word is too permissive (`vàng`
    versus `hàng`, or `khác` versus unrelated text).  Multiword and long
    single-token anchors still retain the requested missing/extra-character
    rescue, and complete topology remains a separate acceptance gate.
    """

    alias_tokens = alias.split()
    compact_length = len(alias.replace(" ", ""))
    minimum_length = 8 if len(alias_tokens) == 1 else 6
    return compact_length >= minimum_length and _edit_distance_at_most_one(candidate, alias)


def _alias_kind(surface: str, aliases: Sequence[str]) -> str | None:
    normalized = normalize_vietnamese_anchor_v1(surface)
    candidates = [(normalized, False)]
    stripped = _ENUMERATION_PREFIX.sub("", surface, count=1)
    if stripped != surface:
        stripped_normalized = normalize_vietnamese_anchor_v1(stripped)
        if stripped_normalized and stripped_normalized != normalized:
            candidates.append((stripped_normalized, True))
    for candidate, enumeration_stripped in candidates:
        if candidate in aliases:
            return (
                "EXACT_ACCENTLESS_ALIAS_AFTER_ENUMERATION_PREFIX"
                if enumeration_stripped
                else "EXACT_ACCENTLESS_ALIAS"
            )
    for candidate, enumeration_stripped in candidates:
        if any(_one_edit_alias_is_safe(candidate, alias) for alias in aliases):
            return (
                "ONE_EDIT_ALIAS_AFTER_ENUMERATION_PREFIX_REQUIRES_COMPLETE_TOPOLOGY"
                if enumeration_stripped
                else "ONE_EDIT_ALIAS_REQUIRES_COMPLETE_TOPOLOGY"
            )
    return None


def _without_decorative_parentheticals(surface: str) -> str:
    """Remove only bounded footnote markers and uppercase acronyms.

    Accounting labels commonly carry a trailing ``(i)``/``(1)`` footnote or
    repeat an immediately preceding organization name as ``("TCTD")``.  Both
    are typographic annotations rather than semantic qualifiers.  Longer or
    ordinary mixed/lower-case parentheticals are retained because they can
    change population, period, sign, or accounting meaning.
    """

    def replacement(match: re.Match[str]) -> str:
        content = match.group(1).strip()
        compact = re.sub(r"[^0-9A-Za-zÀ-ỿĐđ*]+", "", content)
        if not compact or len(compact) > 8:
            return match.group(0)
        letters = [character for character in compact if character.isalpha()]
        is_footnote = compact.isdigit() or compact.lower() in {
            "i",
            "ii",
            "iii",
            "iv",
            "v",
            "vi",
            "vii",
            "viii",
            "ix",
            "x",
        }
        is_uppercase_acronym = bool(letters) and all(character.isupper() for character in letters)
        return " " if is_footnote or is_uppercase_acronym else match.group(0)

    return re.sub(r"\(([^()]*)\)", replacement, surface)


def _surface_candidates(
    lines: Sequence[Mapping[str, Any]], max_label_span: int
) -> list[list[dict[str, Any]]]:
    """Normalize every bounded joined label once per page, not once per role.

    A family can declare many semantic roles and contextual matchers. Repeating
    Unicode normalization and enumeration-prefix handling for every role made
    complete-corpus sweeps scale with ``lines × roles × aliases``. The joined
    surface axis is role-independent, so cache it once while preserving the
    exact shortest-width-first matching behavior of :func:`_role_hits`.
    """

    def candidate(positions: Sequence[int]) -> dict[str, Any]:
        selected = [lines[position] for position in positions]
        surface = " ".join(line["vietocr_text"].strip() for line in selected).strip()
        normalized = normalize_vietnamese_anchor_v1(surface)
        stripped = _ENUMERATION_PREFIX.sub("", surface, count=1)
        stripped_normalized = (
            normalize_vietnamese_anchor_v1(stripped) if stripped != surface else None
        )
        decorative_surface = _without_decorative_parentheticals(surface)
        decorative_normalized = (
            normalize_vietnamese_anchor_v1(decorative_surface)
            if decorative_surface != surface
            else None
        )
        decorative_stripped = _ENUMERATION_PREFIX.sub("", decorative_surface, count=1)
        decorative_stripped_normalized = (
            normalize_vietnamese_anchor_v1(decorative_stripped)
            if decorative_stripped != decorative_surface
            else None
        )
        source_surface = (
            " ".join(line["source_text"].strip() for line in selected).strip()
            if all(
                type(line["source_text"]) is str and line["source_text"].strip()
                for line in selected
            )
            else None
        )
        source_normalized = (
            normalize_vietnamese_anchor_v1(source_surface) if source_surface is not None else None
        )
        item = {
            "decorative_normalized": (
                decorative_normalized
                if decorative_normalized and decorative_normalized != normalized
                else None
            ),
            "decorative_stripped_normalized": (
                decorative_stripped_normalized
                if decorative_stripped_normalized
                and decorative_stripped_normalized
                not in {normalized, stripped_normalized, decorative_normalized}
                else None
            ),
            "line_positions": list(positions),
            "normalized": normalized,
            "source_normalized": source_normalized,
            "source_stripped_normalized": None,
            "source_surface": source_surface,
            "stripped_normalized": (
                stripped_normalized
                if stripped_normalized and stripped_normalized != normalized
                else None
            ),
            "surface": surface,
            "width": len(positions),
        }
        if source_surface is not None:
            source_stripped = _ENUMERATION_PREFIX.sub("", source_surface, count=1)
            if source_stripped != source_surface:
                source_stripped_normalized = normalize_vietnamese_anchor_v1(source_stripped)
                if source_stripped_normalized != source_normalized:
                    item["source_stripped_normalized"] = source_stripped_normalized
        return item

    # Provider order is usually row-major, but a wrapped label can be emitted
    # as ``label fragment, value lane 1, value lane 2, continuation``.  Build a
    # bounded visual-continuation graph once per page so exact aliases can join
    # those label fragments without swallowing the interleaved numeric cells.
    visual_axis = sorted(
        (
            ((line["bbox"][1] + line["bbox"][3]) / 2.0, position)
            for position, line in enumerate(lines)
        )
    )
    visual_centers = [item[0] for item in visual_axis]
    followers: dict[int, list[int]] = {}
    for position, line in enumerate(lines):
        box = line["bbox"]
        height = box[3] - box[1]
        center = (box[1] + box[3]) / 2.0
        lower = bisect_left(visual_centers, center + height * 0.35)
        upper = bisect_right(visual_centers, center + height * 2.5)
        candidates = []
        for _visual_center, other_position in visual_axis[lower:upper]:
            other_surface = lines[other_position]["vietocr_text"].strip()
            if not other_surface or not any(character.isalpha() for character in other_surface):
                continue
            other_box = lines[other_position]["bbox"]
            other_height = other_box[3] - other_box[1]
            horizontal_tolerance = max(height, other_height) * 6.0
            if abs(other_box[0] - box[0]) <= horizontal_tolerance or (
                other_box[0] <= box[2] + horizontal_tolerance
                and box[0] <= other_box[2] + horizontal_tolerance
            ):
                candidates.append(other_position)
        followers[position] = sorted(
            candidates,
            key=lambda other: (
                (lines[other]["bbox"][1] + lines[other]["bbox"][3]) / 2.0,
                lines[other]["bbox"][0],
                other,
            ),
        )

    result = []
    for start in range(len(lines)):
        axis = []
        for width in range(1, min(max_label_span, len(lines) - start) + 1):
            # Empty semantic observations cannot carry either edge of a
            # wrapped label.  Allowing them here widens an otherwise exact
            # hit over the adjacent numeric cell/empty detector token, which
            # then makes the row-axis reader skip that cell as if it were part
            # of the label.  Interior non-empty wrapped fragments remain
            # supported; this only removes geometry that contributes no text.
            if (
                not lines[start]["vietocr_text"].strip()
                or not lines[start + width - 1]["vietocr_text"].strip()
            ):
                continue
            axis.append(candidate(tuple(range(start, start + width))))

        seen_positions = {tuple(item["line_positions"]) for item in axis}
        positions = (start,) if lines[start]["vietocr_text"].strip() else ()
        while positions and len(positions) < max_label_span:
            next_axis = followers[positions[-1]]
            if not next_axis:
                break
            # A visual row has only one next wrapped text fragment at the
            # closest lower baseline.  Provider ordinals can disagree with
            # visual order, while same-baseline numeric cells can precede the
            # real continuation by a few pixels.  The follower graph therefore
            # advances strictly by visual centre and excludes numeric-only
            # observations.  Sequential source-order candidates above still
            # preserve legitimate numeric headings; exact full-alias matching
            # remains a separate gate.
            expanded = (*positions, next_axis[0])
            if expanded in seen_positions:
                positions = expanded
                continue
            seen_positions.add(expanded)
            if expanded != tuple(range(expanded[0], expanded[-1] + 1)):
                axis.append(candidate(expanded))
            positions = expanded
        axis.sort(key=lambda item: (item["width"], item["line_positions"][-1]))
        result.append(axis)
    return result


def _cached_alias_kind(
    candidate: Mapping[str, Any],
    aliases: Sequence[str],
    *,
    allow_decorative_parenthetical_removal: bool,
    allow_bare_numeric_heading_prefix: bool = False,
    allow_leading_alias: bool = False,
    allow_trailing_organization_qualifier: bool = False,
) -> str | None:
    axes = [(candidate["normalized"], "")]
    if candidate["stripped_normalized"] is not None:
        axes.append((candidate["stripped_normalized"], "_AFTER_ENUMERATION_PREFIX"))
    if allow_decorative_parenthetical_removal and candidate["decorative_normalized"] is not None:
        axes.append(
            (
                candidate["decorative_normalized"],
                "_AFTER_DECORATIVE_PARENTHETICAL_REMOVAL",
            )
        )
    if (
        allow_decorative_parenthetical_removal
        and candidate["decorative_stripped_normalized"] is not None
    ):
        axes.append(
            (
                candidate["decorative_stripped_normalized"],
                "_AFTER_ENUMERATION_PREFIX_AND_DECORATIVE_PARENTHETICAL_REMOVAL",
            )
        )
    if allow_bare_numeric_heading_prefix and candidate["width"] == 1:
        bare_stripped = _BARE_NUMERIC_HEADING_PREFIX.sub("", candidate["surface"], count=1)
        if bare_stripped != candidate["surface"]:
            bare_normalized = normalize_vietnamese_anchor_v1(bare_stripped)
            if bare_normalized and bare_normalized not in {item[0] for item in axes}:
                axes.append((bare_normalized, "_AFTER_BARE_NUMERIC_HEADING_PREFIX"))
    for normalized, suffix in axes:
        if normalized in aliases:
            return "EXACT_ACCENTLESS_ALIAS" + suffix
    if allow_trailing_organization_qualifier:
        forbidden = {"bao", "gom", "khong", "loai", "ngoai", "sau", "tru", "truoc"}
        for normalized, suffix in axes:
            for alias in aliases:
                prefix = alias + " tai "
                if not normalized.startswith(prefix):
                    continue
                qualifier_tokens = normalized[len(prefix) :].split()
                if (
                    1 <= len(qualifier_tokens) <= 6
                    and not forbidden.intersection(qualifier_tokens)
                    and all(re.fullmatch(r"[0-9a-z]+", token) for token in qualifier_tokens)
                ):
                    return "EXACT_ACCENTLESS_ALIAS_WITH_TRAILING_ORGANIZATION_QUALIFIER" + suffix
    if allow_leading_alias:
        for normalized, suffix in axes:
            if any(
                len(alias.split()) >= 3 and normalized.startswith(alias + " ") for alias in aliases
            ):
                return "LEADING_ACCENTLESS_ALIAS" + suffix
    for normalized, suffix in axes:
        if any(_one_edit_alias_is_safe(normalized, alias) for alias in aliases):
            return "ONE_EDIT_ALIAS" + suffix + "_REQUIRES_COMPLETE_TOPOLOGY"
    return None


def _joined(lines: Sequence[Mapping[str, Any]], start: int, stop: int) -> str:
    return " ".join(line["vietocr_text"].strip() for line in lines[start:stop]).strip()


def _role_hits(
    lines: Sequence[Mapping[str, Any]],
    *,
    aliases: Sequence[str],
    document_offset: int,
    max_label_span: int,
    page_sequence: int,
    surface_candidates: Sequence[Sequence[Mapping[str, Any]]] | None = None,
    within_role: str | None = None,
    presence_anchor: bool = True,
    allow_bare_numeric_heading_prefix: bool = False,
    allow_decorative_parenthetical_removal: bool = False,
    allow_leading_alias: bool = False,
    allow_trailing_organization_qualifier: bool = False,
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for start in range(len(lines)):
        candidates = (
            surface_candidates[start]
            if surface_candidates is not None
            else _surface_candidates(lines[start:], max_label_span)[0]
        )
        for candidate in candidates:
            positions = candidate["line_positions"]
            surface = candidate["surface"]
            kind = _cached_alias_kind(
                candidate,
                aliases,
                allow_bare_numeric_heading_prefix=allow_bare_numeric_heading_prefix,
                allow_decorative_parenthetical_removal=allow_decorative_parenthetical_removal,
                allow_leading_alias=allow_leading_alias,
                allow_trailing_organization_qualifier=(allow_trailing_organization_qualifier),
            )
            matched_surface = surface
            if kind is None and candidate["source_surface"] is not None:
                source_axes = [
                    (candidate["source_normalized"], ""),
                    (
                        candidate["source_stripped_normalized"],
                        "_AFTER_ENUMERATION_PREFIX",
                    ),
                ]
                source_match = next(
                    (
                        (normalized, suffix)
                        for normalized, suffix in source_axes
                        if normalized is not None and normalized in aliases
                    ),
                    None,
                )
                if source_match is not None:
                    _normalized, suffix = source_match
                    kind = "EXACT_ACCENTLESS_BOUND_SOURCE_TEXT_CHALLENGER_ALIAS" + suffix
                    matched_surface = candidate["source_surface"]
            if kind is None:
                continue
            selected_lines = [lines[position] for position in positions]
            source_positions = sorted(positions)
            start_position = source_positions[0]
            end_position = source_positions[-1]
            hit = {
                "_bbox": [
                    min(line["bbox"][0] for line in selected_lines),
                    min(line["bbox"][1] for line in selected_lines),
                    max(line["bbox"][2] for line in selected_lines),
                    max(line["bbox"][3] for line in selected_lines),
                ],
                "document_line_ordinal": document_offset + start_position,
                "end_document_line_ordinal": document_offset + end_position,
                "end_source_line_index": max(line["source_line_index"] for line in selected_lines),
                "match_kind": kind,
                "normalized_surface": normalize_vietnamese_anchor_v1(matched_surface),
                "page_sequence": page_sequence,
                "source_line_index": min(line["source_line_index"] for line in selected_lines),
                "surface": matched_surface,
            }
            selected_source_indices = sorted(line["source_line_index"] for line in selected_lines)
            contiguous = source_positions == list(range(start_position, end_position + 1))
            if not contiguous:
                hit["source_line_indices"] = selected_source_indices
            if within_role is not None:
                hit["_within_role"] = within_role
            if not presence_anchor:
                hit["_presence_anchor"] = False
            hits.append(hit)
            break
    # A wrapped match may also expose an exact shorter match beginning on its
    # continuation line.  Retain the shortest match at each ending position so
    # one visual label cannot become two semantic rows.
    by_end: dict[int, dict[str, Any]] = {}
    for hit in hits:
        existing = by_end.get(hit["end_source_line_index"])
        if existing is None or hit["source_line_index"] > existing["source_line_index"]:
            by_end[hit["end_source_line_index"]] = hit
    return sorted(by_end.values(), key=lambda item: item["source_line_index"])


def _page_hits(
    page: Mapping[str, Any], spec: Mapping[str, Any], *, document_offset: int
) -> dict[str, Any]:
    lines = page["lines"]
    max_span = spec["limits"]["max_label_line_span"]
    allow_decorative_parenthetical_removal = spec["spec_format_version"] in {
        SPEC_FORMAT_VERSION_V3,
        SPEC_FORMAT_VERSION_V4,
    }
    surfaces = _surface_candidates(lines, max_span)
    children = {}
    for child in spec["children"]:
        combined = []
        for matcher in child["matchers"]:
            combined.extend(
                _role_hits(
                    lines,
                    aliases=matcher["aliases"],
                    document_offset=document_offset,
                    max_label_span=max_span,
                    page_sequence=page["page_sequence"],
                    surface_candidates=surfaces,
                    within_role=matcher["within_role"],
                    presence_anchor=matcher["presence_anchor"],
                    allow_trailing_organization_qualifier=matcher.get(
                        "allow_trailing_organization_qualifier", False
                    ),
                    allow_decorative_parenthetical_removal=(allow_decorative_parenthetical_removal),
                )
            )
        by_signature = {}
        for hit in combined:
            signature = (
                hit["document_line_ordinal"],
                hit["end_document_line_ordinal"],
                hit.get("_within_role"),
            )
            prior = by_signature.get(signature)
            if prior is None or hit["match_kind"].startswith("EXACT_"):
                by_signature[signature] = hit
        children[child["role"]] = sorted(
            by_signature.values(),
            key=lambda item: (
                item["document_line_ordinal"],
                item["end_document_line_ordinal"],
                item.get("_within_role") or "",
            ),
        )
    return {
        "children": children,
        "hard_negatives": _role_hits(
            lines,
            aliases=spec["hard_negative_aliases"],
            document_offset=document_offset,
            max_label_span=max_span,
            page_sequence=page["page_sequence"],
            surface_candidates=surfaces,
            allow_decorative_parenthetical_removal=allow_decorative_parenthetical_removal,
        ),
        "parents": _role_hits(
            lines,
            aliases=spec["parent"]["aliases"],
            document_offset=document_offset,
            max_label_span=max_span,
            page_sequence=page["page_sequence"],
            surface_candidates=surfaces,
            allow_bare_numeric_heading_prefix=True,
            allow_decorative_parenthetical_removal=allow_decorative_parenthetical_removal,
        ),
        "resets": _role_hits(
            lines,
            aliases=spec["structural_reset_aliases"],
            document_offset=document_offset,
            max_label_span=max_span,
            page_sequence=page["page_sequence"],
            surface_candidates=surfaces,
            allow_bare_numeric_heading_prefix=True,
            allow_decorative_parenthetical_removal=allow_decorative_parenthetical_removal,
            allow_leading_alias=True,
        ),
    }


def _first_after(hits: Sequence[Mapping[str, Any]], index: int) -> int | None:
    positions = [
        hit["document_line_ordinal"] for hit in hits if hit["document_line_ordinal"] > index
    ]
    return min(positions) if positions else None


def _matched_required_role_evidence(
    spec: Mapping[str, Any], observed_roles: set[str]
) -> tuple[list[list[str]], list[dict[str, Any]]]:
    """Return exact combination and flexible-pool presence evidence.

    Pool minima count distinct semantic roles, never repeated occurrences of a
    single role.  This primitive only proves family presence; later shared
    stages still prove row lanes, exhaustive direct frontiers, and totals.
    """

    matched_combinations = [
        combination
        for combination in spec["required_role_combinations"]
        if set(combination).issubset(observed_roles)
    ]
    matched_pools = [
        pool
        for pool in spec["required_role_pools"]
        if len(observed_roles.intersection(pool["roles"])) >= pool["minimum_count"]
    ]
    return matched_combinations, matched_pools


def _required_role_deficits(spec: Mapping[str, Any], observed_roles: set[str]) -> set[str]:
    """Return roles that can still complete one unsatisfied presence path."""

    matched_combinations, matched_pools = _matched_required_role_evidence(spec, observed_roles)
    if matched_combinations or matched_pools:
        return set()
    deficits = {
        role
        for combination in spec["required_role_combinations"]
        for role in combination
        if role not in observed_roles
    }
    deficits.update(
        role
        for pool in spec["required_role_pools"]
        if len(observed_roles.intersection(pool["roles"])) < pool["minimum_count"]
        for role in pool["roles"]
        if role not in observed_roles
    )
    return deficits


def _child_records_in_range(
    hits: Mapping[str, Sequence[Mapping[str, Any]]],
    spec: Mapping[str, Any],
    *,
    retain_all_occurrences: bool = False,
    start: int,
    stop: int,
) -> list[dict[str, Any]]:
    role_kind = {child["role"]: child["role_kind"] for child in spec["children"]}
    structural_parent = spec["structural_parent_by_role"]

    def structural_depth(role: str) -> int:
        depth = 0
        cursor = structural_parent.get(role)
        while cursor is not None:
            depth += 1
            cursor = structural_parent.get(cursor)
        return depth

    structural_roles = {role for role, kind in role_kind.items() if kind == "STRUCTURAL_GROUP"}

    def visual_position(hit: Mapping[str, Any]) -> tuple[int, float]:
        bbox = hit["_bbox"]
        return hit["page_sequence"], (bbox[1] + bbox[3]) / 2

    def visually_precedes(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
        return visual_position(left) < visual_position(right)

    valid_contextual_hit_ids: set[int] = set()
    shadowed_context_free_spans: set[tuple[int, int]] = set()

    def span(hit: Mapping[str, Any]) -> tuple[int, int]:
        return hit["document_line_ordinal"], hit["end_document_line_ordinal"]

    def visible_context_hit(hit: Mapping[str, Any]) -> bool:
        within_role = hit.get("_within_role")
        return (
            id(hit) in valid_contextual_hit_ids
            if within_role is not None
            else span(hit) not in shadowed_context_free_spans
        )

    if spec["spec_format_version"] == SPEC_FORMAT_VERSION_V4:
        contextual_hits = sorted(
            (
                (role, hit)
                for role, role_hits in hits.items()
                for hit in role_hits
                if hit.get("_within_role") is not None
            ),
            key=lambda item: (*visual_position(item[1]), item[0]),
        )
        for _role, hit in contextual_hits:
            within_role = hit["_within_role"]
            contexts = [
                item
                for item in hits[within_role]
                if start < item["document_line_ordinal"] < stop
                and visually_precedes(item, hit)
                and visible_context_hit(item)
            ]
            if not contexts:
                continue
            context = max(contexts, key=visual_position)
            context_depth = structural_depth(within_role)
            intervening_boundaries = [
                item
                for role in structural_roles
                if structural_depth(role) <= context_depth
                for item in hits[role]
                if start < item["document_line_ordinal"] < stop
                and visually_precedes(context, item)
                and visually_precedes(item, hit)
                and visible_context_hit(item)
            ]
            if intervening_boundaries:
                continue
            valid_contextual_hit_ids.add(id(hit))
            shadowed_context_free_spans.add(span(hit))

    def context_bound(hit: Mapping[str, Any]) -> bool:
        within_role = hit.get("_within_role")
        if spec["spec_format_version"] == SPEC_FORMAT_VERSION_V4:
            return visible_context_hit(hit)
        if within_role is None:
            return True
        contexts = [
            item
            for item in hits[within_role]
            if start < item["document_line_ordinal"] < stop and visually_precedes(item, hit)
        ]
        if not contexts:
            return False
        context = max(contexts, key=visual_position)
        context_depth = structural_depth(within_role)
        intervening_boundaries = [
            item
            for role in structural_roles
            if structural_depth(role) <= context_depth
            for item in hits[role]
            if start < item["document_line_ordinal"] < stop
            and visually_precedes(context, item)
            and visually_precedes(item, hit)
        ]
        return not intervening_boundaries

    records: list[dict[str, Any]] = []
    for child in spec["children"]:
        candidates = [
            hit
            for hit in hits[child["role"]]
            if (
                start < hit["document_line_ordinal"] < stop
                or (
                    child["role_kind"] == "SOURCE_ONLY_GROUP_PARENT"
                    and hit["document_line_ordinal"] == start
                )
            )
            and context_bound(hit)
        ]
        if not candidates:
            continue
        # A role can expose both its contextual and context-free matcher at the
        # same visual span.  That is one occurrence even when the caller keeps
        # only the first hit.  Prefer the contextual record because it carries
        # the stronger parent binding already checked by ``context_bound``.
        # This is also important when a provider emits overlapping parent and
        # child lines in reverse source order: visual geometry still proves the
        # parent context, while a stable sort would otherwise retain the
        # context-free twin merely because it was inserted first.
        by_span: dict[tuple[int, int], Mapping[str, Any]] = {}
        for candidate in candidates:
            signature = (
                candidate["document_line_ordinal"],
                candidate["end_document_line_ordinal"],
            )
            prior = by_span.get(signature)
            if prior is None or (
                prior.get("_within_role") is None and candidate.get("_within_role") is not None
            ):
                by_span[signature] = candidate
        unique_candidates = list(by_span.values())
        if retain_all_occurrences:
            selected = sorted(
                unique_candidates,
                key=lambda item: (
                    item["document_line_ordinal"],
                    item["end_document_line_ordinal"],
                ),
            )
        else:
            selected = [min(unique_candidates, key=lambda item: item["document_line_ordinal"])]
        for occurrence_ordinal, hit in enumerate(selected):
            public_hit = {key: item for key, item in hit.items() if not key.startswith("_")}
            if spec["spec_format_version"] in {
                SPEC_FORMAT_VERSION_V3,
                SPEC_FORMAT_VERSION_V4,
            }:
                public_hit["matched_within_role"] = hit.get("_within_role")
            record = {
                **canonical_clone_v1(public_hit),
                "preferred_ordinal": child["preferred_ordinal"],
                "presence": child["presence"],
                "role": child["role"],
                "role_kind": child["role_kind"],
            }
            if retain_all_occurrences:
                record["role_occurrence_ordinal"] = occurrence_ordinal
            records.append(record)
    if spec["spec_format_version"] == SPEC_FORMAT_VERSION_V4:
        records_by_span: dict[tuple[int, int], list[dict[str, Any]]] = {}
        for record in records:
            records_by_span.setdefault(
                (
                    record["document_line_ordinal"],
                    record["end_document_line_ordinal"],
                ),
                [],
            ).append(record)
        retained_records = []
        for span_records in records_by_span.values():
            contextual = [
                record for record in span_records if record.get("matched_within_role") is not None
            ]
            # One exact nested matcher is stronger than context-free aliases at
            # the same source span.  Multiple contextual roles remain visible
            # and ambiguous rather than being assigned by declaration order.
            retained_records.extend(contextual if len(contextual) == 1 else span_records)
        records = retained_records
    return sorted(records, key=lambda item: item["document_line_ordinal"])


def _candidate(
    *,
    line_by_document_ordinal: Mapping[int, Mapping[str, Any]],
    parent: Mapping[str, Any] | None,
    records: Sequence[Mapping[str, Any]],
    start: int,
    stop: int,
    spec: Mapping[str, Any],
    hard_negative_hits: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    # When the broad family parent and a source-only group parent share one
    # visual label, do not duplicate that same source row as a child if another
    # declared core combination already proves the family.  The coextensive
    # group remains necessary (and is retained) when it is itself part of the
    # only satisfied alternative, such as ``Vietnam + Laos``.
    pruned_records = list(records)
    for record in records:
        if (
            record["role_kind"] != "SOURCE_ONLY_GROUP_PARENT"
            or record["document_line_ordinal"] != start
        ):
            continue
        roles_without = {item["role"] for item in records if item is not record}
        matched_without, matched_pools_without = _matched_required_role_evidence(
            spec, roles_without
        )
        if matched_without or matched_pools_without:
            pruned_records.remove(record)
    records = pruned_records
    observed_roles = [record["role"] for record in records]
    matched_combinations, matched_pools = _matched_required_role_evidence(spec, set(observed_roles))
    hard_negatives = [
        canonical_clone_v1(hit)
        for hit in hard_negative_hits
        if start <= hit["document_line_ordinal"] < stop
    ]
    if matched_combinations or matched_pools:
        reasons = []
    elif spec["spec_format_version"] == SPEC_FORMAT_VERSION:
        reasons = [
            f"MISSING_REQUIRED_CHILD:{role}"
            for role in spec["required_role_combinations"][0]
            if role not in observed_roles
        ]
    elif spec["spec_format_version"] != SPEC_FORMAT_VERSION_V4:
        encoded = "|".join(
            "+".join(combination) for combination in spec["required_role_combinations"]
        )
        reasons = [f"MISSING_REQUIRED_ROLE_COMBINATION:{encoded}"]
    else:
        encoded_combinations = "|".join(
            "+".join(combination) for combination in spec["required_role_combinations"]
        )
        encoded_pools = "|".join(
            f"MINIMUM_{pool['minimum_count']}:" + "+".join(pool["roles"])
            for pool in spec["required_role_pools"]
        )
        reasons = [
            f"MISSING_REQUIRED_ROLE_COMBINATION:{encoded_combinations}",
            f"MISSING_REQUIRED_ROLE_POOL:{encoded_pools}",
        ]
    if hard_negatives:
        reasons.append("HARD_NEGATIVE_FAMILY_IN_CLUSTER")
    preferred = sorted(records, key=lambda item: item["preferred_ordinal"])
    anchors = [record for record in records]
    if parent is not None:
        anchors.append(parent)
    if not anchors:
        raise _error("accounting family candidate retained no structural anchor")
    start_page = min(item["page_sequence"] for item in anchors)
    end_page = max(item["page_sequence"] for item in anchors)
    stop_line = line_by_document_ordinal.get(stop)
    return {
        "child_matches": canonical_clone_v1(list(records)),
        "cluster_end_document_line_ordinal_exclusive": stop,
        "cluster_end_page_sequence_inclusive": end_page,
        "cluster_end_source_line_index_exclusive": (
            stop_line["source_line_index"]
            if stop_line is not None and stop_line["page_sequence"] == start_page
            else None
        ),
        "cluster_start_document_line_ordinal": start,
        "cluster_start_source_line_index": line_by_document_ordinal[start]["source_line_index"],
        "continuation_page_count": end_page - start_page,
        "hard_negative_matches": hard_negatives,
        "observed_roles": observed_roles,
        "page_sequence": start_page,
        "parent_match": canonical_clone_v1(parent) if parent is not None else None,
        "parent_resolution": (
            "EXPLICIT_PARENT" if parent is not None else "IMPLIED_BY_REQUIRED_CHILD_CLUSTER"
        ),
        "preferred_sibling_order_preserved": observed_roles
        == [record["role"] for record in preferred],
        "unresolved_reasons": sorted(reasons),
    }


def _explicit_candidates(
    hits: Mapping[str, Any],
    spec: Mapping[str, Any],
    *,
    line_by_document_ordinal: Mapping[int, Mapping[str, Any]],
    page_end_exclusive: Mapping[int, int],
) -> list[dict[str, Any]]:
    candidates = []
    maximum_span = spec["limits"]["max_cluster_span_lines"]
    max_continuation = spec["limits"]["max_continuation_pages"]
    maximum_page = max(page_end_exclusive)
    source_group_parent_positions = {
        hit["document_line_ordinal"]
        for child in spec["children"]
        if child["role_kind"] == "SOURCE_ONLY_GROUP_PARENT"
        for hit in hits["children"][child["role"]]
    }

    def role_deficit_continuation_stop(
        *,
        parent: Mapping[str, Any],
        records: Sequence[Mapping[str, Any]],
        proposed_stop: int,
    ) -> int:
        """Retain only structurally useful physical-page continuations.

        ``max_continuation_pages`` is a search budget, not permission to absorb
        every familiar label on the next page.  Starting with the roles visible
        on the parent's page, a later page must either fill one still-viable
        core-role deficit, add a child bound to a structural group already in
        the table (or repeated on that page), or carry an explicit ``tiếp theo``
        parent.  This is deliberately role- and relationship-driven: bank,
        note, page number, schema ID, and fixed layout never enter the rule.

        The boundary closes at the prior physical page as soon as one candidate
        page contributes no such evidence.  This prevents a generic label such
        as ``Giá trị thuần`` in the following family from being borrowed merely
        because it falls within the numeric continuation budget.
        """

        start_page = parent["page_sequence"]
        observed = {record["role"] for record in records if record["page_sequence"] == start_page}
        maximum_candidate_page = max(
            (
                page
                for page in page_end_exclusive
                if page_end_exclusive.get(page - 1, 0) < proposed_stop
            ),
            default=start_page,
        )
        for page_sequence in range(start_page + 1, maximum_candidate_page + 1):
            page_records = [
                record for record in records if record["page_sequence"] == page_sequence
            ]
            new_records = [record for record in page_records if record["role"] not in observed]
            deficits = _required_role_deficits(spec, observed)
            page_structural_groups = {
                record["role"]
                for record in page_records
                if record["role_kind"] == "STRUCTURAL_GROUP"
            }
            structurally_connected = any(
                record.get("matched_within_role") in {*observed, *page_structural_groups}
                for record in new_records
                if record.get("matched_within_role") is not None
            ) or any(
                record["role_kind"] == "STRUCTURAL_GROUP"
                and any(
                    child.get("matched_within_role") == record["role"] for child in page_records
                )
                for record in new_records
            )
            fills_core_deficit = any(record["role"] in deficits for record in new_records)
            explicit_continuation_parent = any(
                hit["page_sequence"] == page_sequence and "tiep theo" in hit["normalized_surface"]
                for hit in hits["parents"]
            )
            if not page_records or not (
                fills_core_deficit or structurally_connected or explicit_continuation_parent
            ):
                return page_end_exclusive[page_sequence - 1]
            observed.update(record["role"] for record in page_records)
        return proposed_stop

    for parent_offset, parent in enumerate(hits["parents"]):
        start = parent["document_line_ordinal"]
        allowed_end_page = min(maximum_page, parent["page_sequence"] + max_continuation)
        stops = [start + maximum_span + 1]
        stops.append(page_end_exclusive[allowed_end_page])

        # A visible source grouping row may legitimately repeat a broad family
        # parent's wording (for example an outer central-bank note followed by
        # a valued Vietnam subgroup).  Such a row is a child boundary, not the
        # start of a second table.  Skip it when finding the next *independent*
        # family parent; the later containment pass removes the redundant
        # nested candidate only after the outer proposal proves complete.
        def is_continuation_parent(
            hit: Mapping[str, Any],
            *,
            current_page: int = parent["page_sequence"],
            current_allowed_end_page: int = allowed_end_page,
        ) -> bool:
            return (
                spec["spec_format_version"] in {SPEC_FORMAT_VERSION_V3, SPEC_FORMAT_VERSION_V4}
                and hit["page_sequence"] == current_page + 1
                and hit["page_sequence"] <= current_allowed_end_page
                and "tiep theo" in hit["normalized_surface"]
            )

        next_independent_parent = next(
            (
                hit["document_line_ordinal"]
                for hit in hits["parents"][parent_offset + 1 :]
                if hit["document_line_ordinal"] not in source_group_parent_positions
                and not is_continuation_parent(hit)
            ),
            None,
        )
        if next_independent_parent is not None:
            stops.append(next_independent_parent)
        reset = _first_after(hits["resets"], start)
        if reset is not None:
            stops.append(reset)
        stop = min(stops)
        records = _child_records_in_range(hits["children"], spec, start=start, stop=stop)
        stop = role_deficit_continuation_stop(
            parent=parent,
            records=records,
            proposed_stop=stop,
        )
        records = _child_records_in_range(hits["children"], spec, start=start, stop=stop)
        candidates.append(
            _candidate(
                line_by_document_ordinal=line_by_document_ordinal,
                parent=parent,
                records=records,
                start=start,
                stop=stop,
                spec=spec,
                hard_negative_hits=hits["hard_negatives"],
            )
        )
    retained = []
    for candidate in candidates:
        start = candidate["cluster_start_document_line_ordinal"]
        if start not in source_group_parent_positions:
            retained.append(candidate)
            continue
        containing_complete = any(
            other is not candidate
            and not other["unresolved_reasons"]
            and other["cluster_start_document_line_ordinal"]
            < start
            < other["cluster_end_document_line_ordinal_exclusive"]
            and any(
                record["role_kind"] == "SOURCE_ONLY_GROUP_PARENT"
                and record["document_line_ordinal"] == start
                for record in other["child_matches"]
            )
            for other in candidates
        )
        if not containing_complete:
            retained.append(candidate)
    return retained


def _implied_candidates(
    hits: Mapping[str, Any],
    spec: Mapping[str, Any],
    explicit: Sequence[Mapping[str, Any]],
    *,
    line_by_document_ordinal: Mapping[int, Mapping[str, Any]],
    page_end_exclusive: Mapping[int, int],
) -> list[dict[str, Any]]:
    if spec["parent"]["resolution_mode"] != "EXPLICIT_OR_UNIQUE_REQUIRED_CHILD_CLUSTER":
        return []
    maximum_span = spec["limits"]["max_cluster_span_lines"]
    max_continuation = spec["limits"]["max_continuation_pages"]
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[int, ...]] = set()
    # Every declared alternative is already a child-child pair or triple.
    # Parent-less inference evaluates each alternative independently, then
    # de-duplicates the resulting source-position signature.
    for required_roles in spec["required_role_combinations"]:
        if len(required_roles) < 2:
            continue
        axes = [hits["children"][role] for role in required_roles]
        if any(not axis for axis in axes):
            continue
        for combination in itertools.product(*axes):
            positions = [hit["document_line_ordinal"] for hit in combination]
            pages = [hit["page_sequence"] for hit in combination]
            if (
                len(set(positions)) != len(positions)
                or max(positions) - min(positions) > maximum_span
                or max(pages) - min(pages) > max_continuation
            ):
                continue
            signature = tuple(sorted(positions))
            if signature in seen:
                continue
            seen.add(signature)
            start = min(positions) - 1
            stop = min(
                max(positions) + maximum_span + 1,
                page_end_exclusive[min(max(page_end_exclusive), min(pages) + max_continuation)],
            )
            resets = [
                hit["document_line_ordinal"]
                for hit in hits["resets"]
                if start < hit["document_line_ordinal"] < stop
            ]
            if resets and min(resets) <= max(positions):
                continue
            if resets:
                stop = min(stop, min(resets))
            if any(
                item["cluster_start_document_line_ordinal"]
                <= min(positions)
                < item["cluster_end_document_line_ordinal_exclusive"]
                for item in explicit
            ):
                continue
            records = _child_records_in_range(hits["children"], spec, start=start, stop=stop)
            candidates.append(
                _candidate(
                    line_by_document_ordinal=line_by_document_ordinal,
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


def _document_hits(
    pages: Sequence[Mapping[str, Any]], spec: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[int, dict[str, Any]], dict[int, int]]:
    """Build the complete source-ordered hit axis once for later generic stages."""

    combined_hits: dict[str, Any] = {
        "children": {child["role"]: [] for child in spec["children"]},
        "hard_negatives": [],
        "parents": [],
        "resets": [],
    }
    line_by_document_ordinal: dict[int, dict[str, Any]] = {}
    page_end_exclusive: dict[int, int] = {}
    offset = 0
    for page in pages:
        for local_ordinal, line in enumerate(page["lines"]):
            line_by_document_ordinal[offset + local_ordinal] = {
                "page_sequence": page["page_sequence"],
                "source_line_index": line["source_line_index"],
            }
        hits = _page_hits(page, spec, document_offset=offset)
        for role in combined_hits["children"]:
            combined_hits["children"][role].extend(hits["children"][role])
        for axis in ("hard_negatives", "parents", "resets"):
            combined_hits[axis].extend(hits[axis])
        offset += len(page["lines"])
        page_end_exclusive[page["page_sequence"]] = offset
    return combined_hits, line_by_document_ordinal, page_end_exclusive


_DocumentHits = tuple[dict[str, Any], dict[int, dict[str, Any]], dict[int, int]]


def _build(
    pages: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any],
    *,
    prepared_hits: _DocumentHits | None = None,
) -> dict[str, Any]:
    if prepared_hits is None:
        prepared_hits = _document_hits(pages, spec)
    combined_hits, line_by_document_ordinal, page_end_exclusive = prepared_hits

    explicit = _explicit_candidates(
        combined_hits,
        spec,
        line_by_document_ordinal=line_by_document_ordinal,
        page_end_exclusive=page_end_exclusive,
    )
    candidates = [
        *explicit,
        *_implied_candidates(
            combined_hits,
            spec,
            explicit,
            line_by_document_ordinal=line_by_document_ordinal,
            page_end_exclusive=page_end_exclusive,
        ),
    ]

    complete = [candidate for candidate in candidates if not candidate["unresolved_reasons"]]
    if spec["spec_format_version"] in {SPEC_FORMAT_VERSION_V3, SPEC_FORMAT_VERSION_V4}:
        # A filing can repeat a broad parent + two aggregate rows in the
        # primary statements or accounting-policy prose before presenting the
        # full note later.  If one complete proposal exposes a strict superset
        # of another proposal's semantic roles, retain the richer topology.
        # Equal-role proposals remain non-unique and must be separated later
        # by period/unit/geometry/numeric evidence.
        complete = [
            candidate
            for candidate in complete
            if not any(
                other is not candidate
                and set(candidate["observed_roles"]) < set(other["observed_roles"])
                for other in complete
            )
        ]
    for candidate in complete:
        candidate["minimal_unique_anchor"] = _minimal_unique_anchors(
            candidate, candidates, spec["parent"]["role"]
        )
    near = [candidate for candidate in candidates if candidate["unresolved_reasons"]]
    unique = len(complete) == 1 and complete[0]["minimal_unique_anchor"] is not None
    semantic_anchor_hit_count = len(combined_hits["parents"]) + sum(
        sum(hit.get("_presence_anchor", True) is True for hit in hits)
        for hits in combined_hits["children"].values()
    )
    core_roles = {
        role for combination in spec["required_role_combinations"] for role in combination
    }
    core_roles.update(role for pool in spec["required_role_pools"] for role in pool["roles"])
    if spec["presence_evidence_mode"] == "WITHIN_EXPLICIT_PARENT_CLUSTER":

        def record_is_presence_anchor(record: Mapping[str, Any]) -> bool:
            return any(
                hit["document_line_ordinal"] == record["document_line_ordinal"]
                and hit["end_document_line_ordinal"] == record["end_document_line_ordinal"]
                and hit.get("_within_role") == record.get("matched_within_role")
                and hit.get("_presence_anchor", True) is True
                for hit in combined_hits["children"][record["role"]]
            )

        scoped_core_hits = {
            (record["role"], record["document_line_ordinal"])
            for candidate in explicit
            if any(
                record["role_kind"] != "SOURCE_ONLY_GROUP_PARENT"
                for record in candidate["child_matches"]
            )
            for record in candidate["child_matches"]
            if record["role"] in core_roles and record_is_presence_anchor(record)
        }
        core_semantic_anchor_hit_count = len(scoped_core_hits)
    else:
        core_semantic_anchor_hit_count = sum(
            sum(
                hit.get("_presence_anchor", True) is True for hit in combined_hits["children"][role]
            )
            for role in core_roles
        )
    return {
        "metrics": {
            "complete_region_count": len(complete),
            "core_semantic_anchor_hit_count": core_semantic_anchor_hit_count,
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
            "semantic_anchor_hit_count": semantic_anchor_hit_count,
        },
        "near_regions": near,
        "regions": complete,
        "status": (
            "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
            if unique
            else "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
            if core_semantic_anchor_hit_count == 0
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
    return _build_validated_scan(pages, spec)


def _build_validated_scan(
    pages: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any],
    *,
    prepared_hits: _DocumentHits | None = None,
) -> dict[str, Any]:
    """Build one validated scan, optionally reusing its exact live hit axis."""

    built = _build(pages, spec, prepared_hits=prepared_hits)
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


def enumerate_accounting_family_role_occurrences_v1(
    document_pages: Any,
    family_spec: Any,
    topology_region: Any,
) -> list[dict[str, Any]]:
    """Return every exact semantic role occurrence inside one live scan region.

    Topology discovery intentionally retains the first hit per role because a
    small parent/child set is sufficient for whole-document uniqueness.  Some
    tables then repeat the same roles in stacked current/comparative blocks.
    Later generic table-axis stages need those repeated rows, but they must not
    broaden or invent the selected family boundary.  This accessor therefore
    rebuilds the complete scan, requires one exact selected region, and only
    expands role hits already contained by that region and its structural
    parent contexts.
    """

    pages = _pages(document_pages)
    spec = _spec(family_spec)
    prepared_hits = _document_hits(pages, spec)
    built = _build_validated_scan(pages, spec, prepared_hits=prepared_hits)
    if type(topology_region) is not dict:
        raise _error("role-occurrence region must be one exact topology object")
    selected_by_payload = {
        canonical_json_sha256_v1(region): region
        for region in built["regions"]
        if same_typed_json_v1(region, topology_region)
    }
    selected = list(selected_by_payload.values())
    if len(selected) != 1:
        raise _error("role-occurrence region is not one exact complete scan candidate")
    region = selected[0]
    hits, _line_axis, _page_axis = prepared_hits
    return _child_records_in_range(
        hits["children"],
        spec,
        retain_all_occurrences=True,
        start=region["cluster_start_document_line_ordinal"],
        stop=region["cluster_end_document_line_ordinal_exclusive"],
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
