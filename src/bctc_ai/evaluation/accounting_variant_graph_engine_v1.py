"""Generic, bank-blind anchor/topology engine for accounting note families.

Family modules provide declarative Vietnamese aliases and structural limits;
the engine supplies accentless normalization, bounded one-character OCR error
tolerance, ordered parent/branch/children matching, optional intermediate
anchors, previous-page owner context, full-document enumeration, and explicit
near-region falsifiers.  It never sees a bank, filename, note number, schema
ID, or mapped value and therefore cannot grant accounting or mapping authority.

Text is only an anchor proposal.  A family wrapper must still validate pixel
geometry, period and unit axes, report scope, totals, signs, and accounting
equations before accepting a graph or mapping any row.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "AccountingVariantGraphEngineV1Error",
    "build_accounting_variant_region_scan_v1",
    "match_vietnamese_anchor_alias_v1",
    "normalize_vietnamese_anchor_v1",
    "validate_accounting_variant_region_scan_replay_v1",
]


FORMAT_VERSION = "ACCOUNTING_VARIANT_GRAPH_ENGINE_REGION_SCAN_V1"
SPEC_FORMAT_VERSION = "ACCOUNTING_VARIANT_FAMILY_SPEC_V1"
CLAIM_BOUNDARY = (
    "BANK_BLIND_VIETOCR_TEXT_ANCHOR_AND_ORDERED_TOPOLOGY_REGION_ENUMERATION_ONLY_"
    "FAMILY_WRAPPER_MUST_VALIDATE_GEOMETRY_AXES_SCOPE_TOTALS_AND_ACCOUNTING_"
    "NO_NUMERIC_SCHEMA_MAPPING_CANONICALIZATION_EXPORT_OR_PRODUCTION_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_or_page_used_for_matching": False,
    "bounded_one_base_character_error_only": True,
    "exact_input_replay_required": True,
    "family_aliases_are_declarative_not_bank_routed": True,
    "mapping_authority": False,
    "near_regions_preserved": True,
    "numeric_authority": False,
    "persisted_result_self_authenticating": False,
    "text_similarity_alone_can_accept": False,
    "vietocr_transformer_text_required": True,
}
_NUMBER = re.compile(r"^[()]*[+-]?[0-9][0-9., ]*%?[()]*$")
_ROLE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_VARIANT = re.compile(r"^[A-Z][A-Z0-9_]*$")
_MAX_BRANCH_ANCHOR_LINE_SPAN = 3
_MAX_LABEL_ANCHOR_LINE_SPAN = 3


class AccountingVariantGraphEngineV1Error(ValueError):
    """The declarative family spec, line axis, or replay drifted."""


def _error(message: str) -> AccountingVariantGraphEngineV1Error:
    return AccountingVariantGraphEngineV1Error(message)


def normalize_vietnamese_anchor_v1(value: str) -> str:
    """Return lowercase Vietnamese text with combining marks/punctuation removed."""

    if type(value) is not str:
        raise _error("Vietnamese anchor text must be one exact string")
    text = unicodedata.normalize("NFD", value.casefold().replace("đ", "d"))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9%]+", " ", text).split())


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


def _find_phrase(
    tokens: Sequence[str], phrase: Sequence[str], start: int
) -> tuple[int, int] | None:
    stop = len(tokens) - len(phrase) + 1
    for offset in range(start, max(start, stop)):
        actual = tokens[offset : offset + len(phrase)]
        if len(actual) != len(phrase):
            continue
        edits = 0
        for observed, expected in zip(actual, phrase, strict=True):
            if observed == expected:
                continue
            if not _edit_distance_at_most_one(observed, expected):
                break
            edits += 1
            if edits > 1:
                break
        else:
            return offset + len(phrase), edits
    return None


def _nonempty_string(value: Any, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise _error(f"{label} must be one non-empty string")
    return value


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} must be one positive integer")
    return value


def _normalized_aliases(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    if type(value) is not list or (not allow_empty and not value):
        requirement = "list" if allow_empty else "non-empty list"
        raise _error(f"{label} must be one {requirement}")
    aliases = [
        normalize_vietnamese_anchor_v1(_nonempty_string(item, f"{label} item")) for item in value
    ]
    if any(not alias for alias in aliases) or len(set(aliases)) != len(aliases):
        raise _error(f"{label} normalized aliases must be unique and non-empty")
    return aliases


def _family_spec(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "branch_core_phrases",
        "branch_variants",
        "family_id",
        "format_version",
        "limits",
        "optional_intermediate_aliases",
        "ordered_children",
        "owner_aliases",
    }:
        raise _error("accounting variant family spec fields drifted")
    family_id = _nonempty_string(value["family_id"], "family ID")
    if value["format_version"] != SPEC_FORMAT_VERSION or _ROLE.fullmatch(family_id) is None:
        raise _error("accounting variant family spec identity drifted")
    core = value["branch_core_phrases"]
    if type(core) is not list or not core:
        raise _error("branch core phrases must be one non-empty list")
    normalized_core = [
        normalize_vietnamese_anchor_v1(_nonempty_string(phrase, "branch core phrase")).split()
        for phrase in core
    ]
    if any(not phrase for phrase in normalized_core):
        raise _error("branch core phrase normalized empty")

    raw_variants = value["branch_variants"]
    if type(raw_variants) is not list or not raw_variants:
        raise _error("branch variants must be one non-empty list")
    variants: list[dict[str, Any]] = []
    variant_bindings: set[tuple[str, tuple[str, ...]]] = set()
    for raw in raw_variants:
        if type(raw) is not dict or set(raw) not in (
            {"anchor_phrase", "variant_id"},
            {"allow_inline_prefix", "anchor_phrase", "variant_id"},
        ):
            raise _error("branch variant fields drifted")
        allow_inline_prefix = raw.get("allow_inline_prefix", False)
        if type(allow_inline_prefix) is not bool:
            raise _error("branch variant inline-prefix policy must be one exact bool")
        variant_id = _nonempty_string(raw["variant_id"], "branch variant ID")
        phrase = normalize_vietnamese_anchor_v1(
            _nonempty_string(raw["anchor_phrase"], "branch variant phrase")
        ).split()
        binding = (variant_id, tuple(phrase))
        if _VARIANT.fullmatch(variant_id) is None or binding in variant_bindings or not phrase:
            raise _error("branch variant identity/phrase drifted")
        variant_bindings.add(binding)
        variants.append(
            {
                "allow_inline_prefix": allow_inline_prefix,
                "anchor_tokens": phrase,
                "variant_id": variant_id,
            }
        )

    raw_children = value["ordered_children"]
    if type(raw_children) is not list or len(raw_children) < 2:
        raise _error("ordered children must contain at least two roles")
    children: list[dict[str, Any]] = []
    roles: set[str] = set()
    for raw in raw_children:
        if type(raw) is not dict or set(raw) != {"aliases", "role"}:
            raise _error("ordered child fields drifted")
        role = _nonempty_string(raw["role"], "ordered child role")
        if _ROLE.fullmatch(role) is None or role in roles:
            raise _error("ordered child role drifted or repeats")
        roles.add(role)
        children.append(
            {
                "aliases": _normalized_aliases(raw["aliases"], f"{role} aliases"),
                "role": role,
            }
        )

    limits = value["limits"]
    if type(limits) is not dict or set(limits) != {
        "max_branch_to_last_child_line_span",
        "max_child_gap",
        "min_numeric_followers_per_child",
    }:
        raise _error("accounting variant family structural limits drifted")
    return {
        "branch_core_tokens": normalized_core,
        "branch_variants": variants,
        "family_id": family_id,
        "limits": {
            key: _positive_int(limits[key], f"family structural limit {key}") for key in limits
        },
        "optional_intermediate_aliases": _normalized_aliases(
            value["optional_intermediate_aliases"],
            "optional intermediate aliases",
            allow_empty=True,
        ),
        "ordered_children": children,
        "owner_aliases": _normalized_aliases(value["owner_aliases"], "owner aliases"),
    }


def _document_pages(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence) or not value:
        raise _error("document pages must be one non-empty sequence")
    pages: list[dict[str, Any]] = []
    for page_offset, raw_page in enumerate(value):
        if type(raw_page) is not dict or set(raw_page) != {"lines", "page_sequence"}:
            raise _error(f"document page {page_offset} fields drifted")
        page_sequence = _positive_int(raw_page["page_sequence"], "page sequence")
        if type(raw_page["lines"]) is not list:
            raise _error("document lines must be one list")
        lines: list[dict[str, Any]] = []
        for line_index, raw_line in enumerate(raw_page["lines"]):
            if type(raw_line) is not dict or set(raw_line) != {
                "source_line_index",
                "vietocr_text",
            }:
                raise _error("document semantic line fields drifted")
            if (
                raw_line["source_line_index"] != line_index
                or type(raw_line["vietocr_text"]) is not str
            ):
                raise _error("document semantic line identity/text drifted")
            lines.append(
                {
                    "source_line_index": line_index,
                    "vietocr_text": raw_line["vietocr_text"],
                }
            )
        pages.append({"lines": lines, "page_sequence": page_sequence})
    sequences = [page["page_sequence"] for page in pages]
    if sequences != sorted(sequences) or len(set(sequences)) != len(sequences):
        raise _error("document page sequences must be unique and ordered")
    return pages


def _number_like(text: str) -> bool:
    compact = text.strip().replace("\u00a0", " ").replace("\u202f", " ")
    return bool(compact and _NUMBER.fullmatch(compact) and any(char.isdigit() for char in compact))


def _alias_match(text: str, aliases: Sequence[str]) -> str | None:
    normalized = normalize_vietnamese_anchor_v1(text)
    if normalized in aliases:
        return "EXACT_ACCENTLESS_ALIAS"
    # A row role is frequently followed by a parenthesized definition such as
    # ``Nợ ngắn hạn (Dưới 1 năm)``.  The qualifier is presentation metadata,
    # not a different accounting role.  Admit it only when the base alias is
    # an exact token prefix and the visible surface ends in parentheses; the
    # complete ordered topology and numeric followers remain mandatory.
    if text.rstrip().endswith(")") and any(normalized.startswith(alias + " ") for alias in aliases):
        return "QUALIFIED_PREFIX_ALIAS_IN_COMPLETE_ORDERED_TOPOLOGY"
    if any(_edit_distance_at_most_one(normalized, alias) for alias in aliases):
        return "ONE_EDIT_ALIAS_IN_COMPLETE_ORDERED_TOPOLOGY"
    return None


def match_vietnamese_anchor_alias_v1(value: str, aliases: Sequence[str]) -> str | None:
    """Match one fresh OCR surface against declarative family aliases.

    The public helper exposes the engine's exact accentless/one-base-character
    policy so family wrappers do not reimplement fuzzy text logic.  It grants
    anchor evidence only; callers must still require complete topology and
    accounting checks.
    """

    if isinstance(aliases, (str, bytes, bytearray)) or not isinstance(aliases, Sequence):
        raise _error("anchor aliases must be one non-string sequence")
    normalized = _normalized_aliases(list(aliases), "anchor aliases")
    return _alias_match(value, normalized)


def _owner_alias_match(text: str, aliases: Sequence[str]) -> str | None:
    normalized = normalize_vietnamese_anchor_v1(text)
    normalized = re.sub(r"^(?:[0-9]+\s+)+", "", normalized)
    normalized = re.sub(r"\s+tiep theo$", "", normalized)
    if normalized in aliases:
        return "EXACT_ACCENTLESS_ALIAS"
    if any(_edit_distance_at_most_one(normalized, alias) for alias in aliases):
        return "ONE_EDIT_ALIAS_IN_COMPLETE_ORDERED_TOPOLOGY"
    return None


def _branch_core_cursor(tokens: Sequence[str], spec: Mapping[str, Any]) -> tuple[int, int] | None:
    cursor = 0
    edits = 0
    for phrase in spec["branch_core_tokens"]:
        matched = _find_phrase(tokens, phrase, cursor)
        if matched is None or edits + matched[1] > 1:
            return None
        cursor, phrase_edits = matched
        edits += phrase_edits
    return cursor, edits


def _branch_match(text: str, spec: Mapping[str, Any]) -> tuple[dict[str, Any] | None, bool, bool]:
    normalized_surface = normalize_vietnamese_anchor_v1(text)
    tokens = normalized_surface.split()
    core = _branch_core_cursor(tokens, spec)
    if core is None:
        return None, False, False
    cursor, core_edits = core
    for variant in spec["branch_variants"]:
        matched = _find_phrase(tokens, variant["anchor_tokens"], cursor)
        if matched is None or core_edits + matched[1] > 1:
            continue
        total_edits = core_edits + matched[1]
        return (
            {
                "match_kind": (
                    "EXACT_ACCENTLESS_STRUCTURAL_ANCHORS"
                    if total_edits == 0
                    else "ONE_EDIT_STRUCTURAL_ANCHORS_IN_COMPLETE_TOPOLOGY"
                ),
                "normalized_surface": normalized_surface,
                "surface": text,
                "variant": variant["variant_id"],
            },
            True,
            variant["allow_inline_prefix"],
        )
    return None, True, False


def _joined_surface(lines: Sequence[Mapping[str, Any]], start: int, stop: int) -> str:
    return " ".join(line["vietocr_text"].strip() for line in lines[start:stop]).strip()


def _starts_with_branch_core(text: str, spec: Mapping[str, Any]) -> bool:
    """Require a branch window to begin at the branch, not one line before it.

    Branch matching deliberately finds ordered phrases inside a complete title,
    because harmless words can occur between structural anchors.  When several
    OCR lines are joined, however, that permissiveness must not let an owner or
    unrelated preceding line absorb the real title and create a duplicate
    candidate.  The first non-number token therefore has to be the beginning of
    the first core phrase (with the same one-character OCR tolerance).
    """

    tokens = normalize_vietnamese_anchor_v1(text).split()
    while tokens and tokens[0].isdigit():
        tokens.pop(0)
    if not tokens:
        return False
    first_core = spec["branch_core_tokens"][0]
    prefix_length = min(len(tokens), len(first_core))
    if prefix_length == 0:
        return False
    edits = 0
    for observed, expected in zip(tokens[:prefix_length], first_core[:prefix_length], strict=True):
        if observed == expected:
            continue
        if not _edit_distance_at_most_one(observed, expected):
            return False
        edits += 1
        if edits > 1:
            return False
    return True


def _branch_window(
    lines: Sequence[Mapping[str, Any]], start: int, spec: Mapping[str, Any]
) -> tuple[dict[str, Any] | None, bool, str]:
    starts_with_core = _starts_with_branch_core(lines[start]["vietocr_text"], spec)
    if not starts_with_core:
        first_line_tokens = normalize_vietnamese_anchor_v1(lines[start]["vietocr_text"]).split()
        if _branch_core_cursor(first_line_tokens, spec) is None or not any(
            variant["allow_inline_prefix"] for variant in spec["branch_variants"]
        ):
            return None, False, lines[start]["vietocr_text"]
    core_matched = False
    near_surface = lines[start]["vietocr_text"]
    for width in range(1, min(_MAX_BRANCH_ANCHOR_LINE_SPAN, len(lines) - start) + 1):
        # A later line which can itself start a family branch is a hard title
        # boundary.  Without this guard, a near-family sentence such as
        # ``Phân tích chất lượng dư nợ ...`` can absorb the following numbered
        # ``Phân tích dư nợ theo thời gian ...`` heading.  The joined surface
        # would then borrow the maturity variant from its sibling and create a
        # duplicate complete graph.  Wrapped headings still work because their
        # continuation line does not restart the branch core.
        if width > 1 and _starts_with_branch_core(lines[start + width - 1]["vietocr_text"], spec):
            break
        surface = _joined_surface(lines, start, start + width)
        branch, core, allow_inline_prefix = _branch_match(surface, spec)
        if core and starts_with_core:
            core_matched = True
            near_surface = surface
        if branch is not None and (starts_with_core or allow_inline_prefix):
            return branch, True, surface
    return None, core_matched, near_surface


def _alias_windows(
    lines: Sequence[Mapping[str, Any]],
    start: int,
    stop: int,
    aliases: Sequence[str],
) -> list[tuple[int, int, str, str]]:
    matches: list[tuple[int, int, str, str]] = []
    for line_index in range(start, stop):
        for width in range(
            1,
            min(_MAX_LABEL_ANCHOR_LINE_SPAN, stop - line_index) + 1,
        ):
            surface = _joined_surface(lines, line_index, line_index + width)
            kind = _alias_match(surface, aliases)
            if kind is not None:
                matches.append((line_index, line_index + width - 1, kind, surface))
                break
    return matches


def _owner_context(
    pages: Sequence[Mapping[str, Any]], page_offset: int, branch_index: int, aliases: Sequence[str]
) -> dict[str, Any] | None:
    page = pages[page_offset]
    local: list[tuple[int, int, str, str]] = []
    for line_index in range(branch_index):
        for width in range(
            1,
            min(_MAX_LABEL_ANCHOR_LINE_SPAN, branch_index - line_index) + 1,
        ):
            surface = _joined_surface(page["lines"], line_index, line_index + width)
            kind = _owner_alias_match(surface, aliases)
            if kind is not None:
                local.append((line_index, line_index + width - 1, kind, surface))
                break
    if local:
        line_index, _end_index, kind, surface = max(local, key=lambda item: (item[1], item[0]))
        return {
            "match_kind": kind,
            "mode": "SAME_PAGE_NEAREST_PRECEDING",
            "normalized_surface": normalize_vietnamese_anchor_v1(surface),
            "page_sequence": page["page_sequence"],
            "source_line_index": line_index,
            "surface": surface,
        }
    if page_offset == 0 or pages[page_offset - 1]["page_sequence"] != page["page_sequence"] - 1:
        return None
    previous = pages[page_offset - 1]
    matches: list[tuple[int, int, str, str]] = []
    for line_index in range(len(previous["lines"])):
        for width in range(
            1,
            min(_MAX_LABEL_ANCHOR_LINE_SPAN, len(previous["lines"]) - line_index) + 1,
        ):
            surface = _joined_surface(previous["lines"], line_index, line_index + width)
            kind = _owner_alias_match(surface, aliases)
            if kind is not None:
                matches.append((line_index, line_index + width - 1, kind, surface))
                break
    if not matches:
        return None
    line_index, _end_index, kind, surface = max(matches, key=lambda item: (item[1], item[0]))
    return {
        "match_kind": kind,
        "mode": "IMMEDIATE_PREVIOUS_PAGE",
        "normalized_surface": normalize_vietnamese_anchor_v1(surface),
        "page_sequence": previous["page_sequence"],
        "source_line_index": line_index,
        "surface": surface,
    }


def _ordered_children(
    lines: Sequence[Mapping[str, Any]], branch_index: int, spec: Mapping[str, Any]
) -> tuple[list[int], list[dict[str, Any]], list[str]]:
    positions: list[int] = []
    records: list[dict[str, Any]] = []
    reasons: list[str] = []
    cursor = branch_index
    limits = spec["limits"]
    for child in spec["ordered_children"]:
        search_stop = min(
            len(lines),
            branch_index + limits["max_branch_to_last_child_line_span"] + 1,
            cursor + limits["max_child_gap"] + 1,
        )
        matches = _alias_windows(lines, cursor + 1, search_stop, child["aliases"])
        if not matches:
            reasons.append(f"MISSING_ORDERED_CHILD_{child['role']}")
            break
        position, end_position, kind, surface = matches[0]
        positions.append(position)
        records.append(
            {
                "match_kind": kind,
                "normalized_surface": normalize_vietnamese_anchor_v1(surface),
                "role": child["role"],
                "surface": surface,
            }
        )
        cursor = end_position
    if len(positions) != len(spec["ordered_children"]):
        return positions, records, reasons
    if (
        sum(
            record["match_kind"] == "ONE_EDIT_ALIAS_IN_COMPLETE_ORDERED_TOPOLOGY"
            for record in records
        )
        > 1
    ):
        reasons.append("MULTIPLE_APPROXIMATE_CHILD_ROLES")
    for child_offset, position in enumerate(positions):
        stop = (
            positions[child_offset + 1]
            if child_offset + 1 < len(positions)
            else min(len(lines), position + limits["max_child_gap"] + 1)
        )
        numeric_count = sum(
            _number_like(line["vietocr_text"]) for line in lines[position + 1 : stop]
        )
        if numeric_count < limits["min_numeric_followers_per_child"]:
            reasons.append(f"INSUFFICIENT_NUMERIC_FOLLOWERS_{records[child_offset]['role']}")
    return positions, records, sorted(set(reasons))


def _scan(pages: Sequence[Mapping[str, Any]], spec: Mapping[str, Any]) -> dict[str, Any]:
    regions: list[dict[str, Any]] = []
    near_regions: list[dict[str, Any]] = []
    for page_offset, page in enumerate(pages):
        lines = page["lines"]
        for branch_index in range(len(lines)):
            branch, core_matched, branch_surface = _branch_window(lines, branch_index, spec)
            if not core_matched:
                continue
            if branch is None:
                near_regions.append(
                    {
                        "branch_source_line_index": branch_index,
                        "branch_surface": branch_surface,
                        "normalized_branch_surface": normalize_vietnamese_anchor_v1(branch_surface),
                        "page_sequence": page["page_sequence"],
                        "unresolved_reasons": ["BRANCH_VARIANT_NOT_RESOLVED"],
                    }
                )
                continue
            positions, child_records, reasons = _ordered_children(lines, branch_index, spec)
            owner = _owner_context(pages, page_offset, branch_index, spec["owner_aliases"])
            if owner is None:
                reasons.append("OWNER_CONTEXT_NOT_RESOLVED")
            if reasons:
                near_regions.append(
                    {
                        "branch_source_line_index": branch_index,
                        "branch_surface": branch_surface,
                        "normalized_branch_surface": normalize_vietnamese_anchor_v1(branch_surface),
                        "page_sequence": page["page_sequence"],
                        "unresolved_reasons": sorted(set(reasons)),
                    }
                )
                # Owner is part of the required core, but retain the anchor
                # region separately so a family wrapper can diagnose inherited
                # context rather than losing the candidate altogether.
            if len(positions) != len(spec["ordered_children"]):
                continue
            first_child = positions[0]
            intermediate = [
                {
                    "match_kind": kind,
                    "normalized_surface": normalize_vietnamese_anchor_v1(surface),
                    "source_line_index": start,
                    "surface": surface,
                }
                for start, _end, kind, surface in _alias_windows(
                    lines,
                    branch_index + 1,
                    first_child,
                    spec["optional_intermediate_aliases"],
                )
            ]
            regions.append(
                {
                    "branch_match": branch,
                    "branch_source_line_index": branch_index,
                    "child_match_records": child_records,
                    "child_source_line_indices": positions,
                    "context_complete": not reasons,
                    "optional_intermediate_matches": intermediate,
                    "owner_context": owner,
                    "page_sequence": page["page_sequence"],
                    "unresolved_reasons": sorted(set(reasons)),
                }
            )
    return {"near_regions": near_regions, "regions": regions}


_ALIAS_MATCH_KINDS = {
    "EXACT_ACCENTLESS_ALIAS",
    "ONE_EDIT_ALIAS_IN_COMPLETE_ORDERED_TOPOLOGY",
    "QUALIFIED_PREFIX_ALIAS_IN_COMPLETE_ORDERED_TOPOLOGY",
}
_BRANCH_MATCH_KINDS = {
    "EXACT_ACCENTLESS_STRUCTURAL_ANCHORS",
    "ONE_EDIT_STRUCTURAL_ANCHORS_IN_COMPLETE_TOPOLOGY",
}


def _nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise _error(f"{label} must be one non-negative integer")
    return value


def _reasons(value: Any, label: str, *, required: bool) -> list[str]:
    if (
        type(value) is not list
        or (required and not value)
        or any(type(item) is not str or not item for item in value)
        or value != sorted(set(value))
    ):
        raise _error(f"{label} unresolved reasons drifted")
    return list(value)


def _validate_branch_record(value: Any) -> None:
    if (
        type(value) is not dict
        or set(value) != {"match_kind", "normalized_surface", "surface", "variant"}
        or value["match_kind"] not in _BRANCH_MATCH_KINDS
        or type(value["surface"]) is not str
        or not value["surface"].strip()
        or value["normalized_surface"] != normalize_vietnamese_anchor_v1(value["surface"])
        or type(value["variant"]) is not str
        or _VARIANT.fullmatch(value["variant"]) is None
    ):
        raise _error("accounting variant branch match record drifted")


def _validate_owner_record(value: Any) -> None:
    if (
        type(value) is not dict
        or set(value)
        != {
            "match_kind",
            "mode",
            "normalized_surface",
            "page_sequence",
            "source_line_index",
            "surface",
        }
        or value["match_kind"] not in _ALIAS_MATCH_KINDS
        or value["mode"] not in {"SAME_PAGE_NEAREST_PRECEDING", "IMMEDIATE_PREVIOUS_PAGE"}
        or type(value["surface"]) is not str
        or not value["surface"].strip()
        or value["normalized_surface"] != normalize_vietnamese_anchor_v1(value["surface"])
    ):
        raise _error("accounting variant owner context record drifted")
    _positive_int(value["page_sequence"], "owner page sequence")
    _nonnegative_int(value["source_line_index"], "owner source line index")


def _validate_region(value: Any) -> None:
    if type(value) is not dict or set(value) != {
        "branch_match",
        "branch_source_line_index",
        "child_match_records",
        "child_source_line_indices",
        "context_complete",
        "optional_intermediate_matches",
        "owner_context",
        "page_sequence",
        "unresolved_reasons",
    }:
        raise _error("accounting variant ordered region fields drifted")
    _validate_branch_record(value["branch_match"])
    branch_index = _nonnegative_int(
        value["branch_source_line_index"], "region branch source line index"
    )
    _positive_int(value["page_sequence"], "region page sequence")
    if type(value["context_complete"]) is not bool:
        raise _error("accounting variant region completion flag drifted")
    reasons = _reasons(value["unresolved_reasons"], "region", required=False)
    if value["context_complete"] is not (not reasons):
        raise _error("accounting variant region completion/reasons disagree")

    records = value["child_match_records"]
    positions = value["child_source_line_indices"]
    if (
        type(records) is not list
        or len(records) < 2
        or type(positions) is not list
        or len(records) != len(positions)
        or any(type(position) is not int or position <= branch_index for position in positions)
        or positions != sorted(set(positions))
    ):
        raise _error("accounting variant ordered child axis drifted")
    roles: list[str] = []
    for record in records:
        if (
            type(record) is not dict
            or set(record) != {"match_kind", "normalized_surface", "role", "surface"}
            or record["match_kind"] not in _ALIAS_MATCH_KINDS
            or type(record["role"]) is not str
            or _ROLE.fullmatch(record["role"]) is None
            or type(record["surface"]) is not str
            or not record["surface"].strip()
            or record["normalized_surface"] != normalize_vietnamese_anchor_v1(record["surface"])
        ):
            raise _error("accounting variant ordered child record drifted")
        roles.append(record["role"])
    if len(set(roles)) != len(roles):
        raise _error("accounting variant ordered child roles repeat")

    optional = value["optional_intermediate_matches"]
    if type(optional) is not list:
        raise _error("accounting variant optional intermediate axis drifted")
    optional_indices: list[int] = []
    for record in optional:
        if (
            type(record) is not dict
            or set(record) != {"match_kind", "normalized_surface", "source_line_index", "surface"}
            or record["match_kind"] not in _ALIAS_MATCH_KINDS
            or type(record["surface"]) is not str
            or not record["surface"].strip()
            or record["normalized_surface"] != normalize_vietnamese_anchor_v1(record["surface"])
        ):
            raise _error("accounting variant optional intermediate record drifted")
        optional_indices.append(
            _nonnegative_int(record["source_line_index"], "optional intermediate source line index")
        )
    if optional_indices != sorted(set(optional_indices)) or any(
        not branch_index < index < positions[0] for index in optional_indices
    ):
        raise _error("accounting variant optional intermediate position drifted")

    owner = value["owner_context"]
    if owner is None:
        if "OWNER_CONTEXT_NOT_RESOLVED" not in reasons:
            raise _error("missing accounting owner was not retained as unresolved")
    else:
        _validate_owner_record(owner)
        if "OWNER_CONTEXT_NOT_RESOLVED" in reasons:
            raise _error("resolved accounting owner still marked unresolved")


def _validate_near_region(value: Any) -> None:
    if type(value) is not dict or set(value) != {
        "branch_source_line_index",
        "branch_surface",
        "normalized_branch_surface",
        "page_sequence",
        "unresolved_reasons",
    }:
        raise _error("accounting variant near-region fields drifted")
    _nonnegative_int(value["branch_source_line_index"], "near-region branch line index")
    _positive_int(value["page_sequence"], "near-region page sequence")
    if type(value["branch_surface"]) is not str or not value["branch_surface"].strip():
        raise _error("accounting variant near-region surface drifted")
    if value["normalized_branch_surface"] != normalize_vietnamese_anchor_v1(
        value["branch_surface"]
    ):
        raise _error("accounting variant near-region normalization drifted")
    _reasons(value["unresolved_reasons"], "near-region", required=True)


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "claim_boundary",
        "family_id",
        "format_version",
        "metrics",
        "near_regions",
        "regions",
        "safety",
        "scan_id",
    }:
        raise _error("accounting variant engine result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or type(value["family_id"]) is not str
        or _ROLE.fullmatch(value["family_id"]) is None
        or type(value["regions"]) is not list
        or type(value["near_regions"]) is not list
        or not same_typed_json_v1(value["safety"], _SAFETY)
    ):
        raise _error("accounting variant engine identity/safety drifted")
    for region in value["regions"]:
        _validate_region(region)
    for region in value["near_regions"]:
        _validate_near_region(region)
    expected_metrics = {
        "complete_context_region_count": sum(
            region["context_complete"] for region in value["regions"]
        ),
        "near_region_count": len(value["near_regions"]),
        "ordered_anchor_region_count": len(value["regions"]),
    }
    if not same_typed_json_v1(value["metrics"], expected_metrics):
        raise _error("accounting variant engine metrics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("scan_id")
    if identity != "avgev1:scan:" + canonical_json_sha256_v1(material):
        raise _error("accounting variant engine scan identity drifted")
    return canonical_clone_v1(value)


def build_accounting_variant_region_scan_v1(
    document_pages: Sequence[Mapping[str, Any]], family_spec: Mapping[str, Any]
) -> dict[str, Any]:
    """Enumerate every complete and near family region in one full PDF."""

    pages = _document_pages(document_pages)
    spec = _family_spec(family_spec)
    scanned = _scan(pages, spec)
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": spec["family_id"],
        "format_version": FORMAT_VERSION,
        "metrics": {
            "complete_context_region_count": sum(
                region["context_complete"] for region in scanned["regions"]
            ),
            "near_region_count": len(scanned["near_regions"]),
            "ordered_anchor_region_count": len(scanned["regions"]),
        },
        "near_regions": scanned["near_regions"],
        "regions": scanned["regions"],
        "safety": canonical_clone_v1(_SAFETY),
    }
    return _validate_result(
        {**material, "scan_id": "avgev1:scan:" + canonical_json_sha256_v1(material)}
    )


def validate_accounting_variant_region_scan_replay_v1(
    value: Any,
    document_pages: Sequence[Mapping[str, Any]],
    family_spec: Mapping[str, Any],
) -> dict[str, Any]:
    """Exact-rebuild the generic region scan from its document/spec inputs."""

    persisted = _validate_result(value)
    rebuilt = build_accounting_variant_region_scan_v1(document_pages, family_spec)
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("accounting variant engine scan does not replay exactly")
    return rebuilt
