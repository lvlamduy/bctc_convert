"""Recursive accounting closure over manifest-selected Gemini page JSON.

This module deliberately has no PDF/OCR/geometry dependency.  Gemini's exact
row labels, hierarchy paths, columns and raw cell strings are the source axis;
the declarative topology/equation/schema specs are the only semantic axis.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from typing import Any

from bctc_ai.evaluation.accounting_family_topology_v1 import (
    compile_accounting_family_topology_spec_v1,
)
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    match_vietnamese_anchor_alias_v1,
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.evaluation.gemini_json_structural_context_v1 import (
    resolve_candidate_structural_context_v1,
)
from bctc_ai.evaluation.source_observation_lane_math_v1 import (
    additive_source_lane_receipts_v1,
    observed_source_coefficient_v1,
    partial_source_mapping_values_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_clone_v1, canonical_json_sha256_v1

FORMAT_VERSION = "GEMINI_JSON_HIERARCHICAL_ACCOUNTING_FAMILY_SWEEP_V3"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_DECLARATIVE_TWO_THEN_THREE_ANCHOR_"
    "EXACT_HIERARCHY_PATH_PERIOD_UNIT_ALL_LANE_RECURSIVE_DIRECT_FRONTIER_"
    "ACCOUNTING_CLOSURE_SCHEMA_MAPPING_PROPOSAL_ONLY_NO_GEOMETRY_PPOCR_"
    "VIETOCR_BANK_FILE_PAGE_NOTE_ROUTING_BACKSOLVE_CANONICAL_OR_EXPORT_AUTHORITY"
)
_EVALUATION_FORMATS = {
    "ACCOUNTING_FAMILY_EVALUATION_SPEC_V3",
    "ACCOUNTING_FAMILY_EVALUATION_SPEC_V4",
    "ACCOUNTING_FAMILY_EVALUATION_SPEC_V5",
    "ACCOUNTING_FAMILY_EVALUATION_SPEC_V6",
    "ACCOUNTING_FAMILY_EVALUATION_SPEC_V7",
    "ACCOUNTING_FAMILY_EVALUATION_SPEC_V8",
}
_SCHEMA_FORMATS = {
    "ACCOUNTING_FAMILY_SCHEMA_BINDING_SPEC_V4",
    "ACCOUNTING_FAMILY_SCHEMA_BINDING_SPEC_V5",
    "ACCOUNTING_FAMILY_SCHEMA_BINDING_SPEC_V6",
    "ACCOUNTING_FAMILY_SCHEMA_BINDING_SPEC_V7",
    "ACCOUNTING_FAMILY_SCHEMA_BINDING_SPEC_V8",
}
_DASHES = {"-", "–", "—", "_"}
_DATE_DMY = re.compile(r"(?<!\d)([0-3]?\d)[./-]([01]?\d)[./-]((?:19|20)\d{2})(?!\d)")
_DATE_MDY = re.compile(r"(?<!\d)([01]?\d)[./-]([0-3]?\d)[./-]((?:19|20)\d{2})(?!\d)")
_DATE_WORDS = re.compile(
    r"ng[aà]y\s+([0-3]?\d)\s+th[aá]ng\s+([01]?\d)\s+n[aă]m\s+((?:19|20)\d{2})",
    re.IGNORECASE,
)
_EXCLUDED_TWO_LANE_NARRATIVE = re.compile(
    r"(?P<current>[0-9]+(?:[.,][0-9]{3})*)\s+"
    r"(?P<current_unit>tri[eệ]u\s+(?:[đd][oồ]ng|vnd))\s*"
    r"\(\s*(?P<day>[0-3]?\d)[./-](?P<month>[01]?\d)[./-](?P<year>(?:19|20)\d{2})\s*:\s*"
    r"(?P<comparative>[0-9]+(?:[.,][0-9]{3})*)\s+"
    r"(?P<comparative_unit>tri[eệ]u\s+(?:[đd][oồ]ng|vnd))\s*\)",
    re.IGNORECASE,
)
_CURRENT_PERIOD_ALIASES = {
    "cuoi ky",
    "cuoi nam",
    "ky nay",
    "nam nay",
    "so cuoi quy",
    "so cuoi ky",
    "so cuoi nam",
    "tai ngay cuoi ky",
    "tai ngay cuoi nam",
}
_COMPARATIVE_PERIOD_ALIASES = {
    "dau ky",
    "dau nam",
    "ky truoc",
    "nam truoc",
    "so dau ky",
    "so dau nam",
    "tai ngay dau ky",
    "tai ngay dau nam",
}
_GENERIC_TOTAL_LABELS = {"", "cong", "tong", "tong cong"}


def _error(message: str) -> ValueError:
    from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
        GeminiJsonFlatAccountingFamilyV1Error,
    )

    return GeminiJsonFlatAccountingFamilyV1Error(message)


@lru_cache(maxsize=16384)
def _normalized(value: Any) -> str:
    # A small number of otherwise valid provider rows contain the two literal
    # JSON-escape characters ``\\n`` in a label rather than an actual line
    # break.  They carry the same visible layout meaning and must not create a
    # synthetic ``n`` token in the semantic anchor.
    if type(value) is str:
        value = value.replace("\\n", " ")
    folded = normalize_vietnamese_anchor_v1(value) if type(value) is str else ""
    folded = " ".join(re.sub(r"[^a-z0-9%]+", " ", folded).split())
    for expanded, acronym in (
        ("to chuc kinh te", "tckt"),
        ("to chuc tin dung", "tctd"),
        ("ngan hang thuong mai", "nhtm"),
    ):
        folded = folded.replace(f"{expanded} {acronym}", expanded)
    return folded


def _without_leading_ordinal(folded: str) -> str:
    tokens = folded.split()
    ordinal_tokens = {
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
        "xi",
        "xii",
        "xiii",
        "xiv",
        "xv",
    }
    while len(tokens) > 1 and (tokens[0].isdigit() or tokens[0] in ordinal_tokens):
        tokens.pop(0)
    return " ".join(tokens)


def _is_generic_total_label(value: Any) -> bool:
    return _without_leading_ordinal(_normalized(value)) in _GENERIC_TOTAL_LABELS


def _matches(value: Any, alias: str) -> bool:
    folded = _normalized(value)
    alias = _normalized(alias)
    forms = {folded, _without_leading_ordinal(folded)}
    # Some provider payloads contain a literal ``\\n`` immediately before a
    # Vietnamese word whose leading ``n`` was consumed by the escape marker
    # (for example ``trong\\nước`` for the visible wrap ``trong / nước``).
    # Admit both exact interpretations of that representation.  The ordinary
    # whitespace interpretation remains primary, and no fuzzy/substring label
    # matching is introduced.
    if type(value) is str and "\\n" in value:
        preserved_n = _normalized(value.replace("\\n", " n"))
        forms |= {preserved_n, _without_leading_ordinal(preserved_n)}
    forms |= {
        form.removeprefix(prefix).strip()
        for form in tuple(forms)
        for prefix in ("trong do ", "bao gom ")
        if form.startswith(prefix)
    }
    if alias in forms:
        return True
    suffixes = {form.removeprefix(alias).strip() for form in forms if form.startswith(alias + " ")}
    allowed_suffix_tokens = {
        "1",
        "2",
        "3",
        "4",
        "5",
        "i",
        "ii",
        "iii",
        "iv",
        "v",
    }

    def is_note_reference_suffix(suffix: str) -> bool:
        tokens = suffix.split()
        if tokens[:1] == ["xem"]:
            tokens = tokens[1:]
        if tokens[:2] != ["thuyet", "minh"]:
            return False
        reference = tokens[2:]
        if reference[:1] == ["so"]:
            reference = reference[1:]
        if not reference:
            return False
        groups = []
        current = []
        for token in reference:
            if token == "va":
                if not current:
                    return False
                groups.append(current)
                current = []
            else:
                current.append(token)
        if not current:
            return False
        groups.append(current)
        return bool(
            1 <= len(groups) <= 3
            and all(
                1 <= len(group) <= 3
                and group[0].isdigit()
                and all(
                    token.isdigit()
                    or re.fullmatch(r"[a-z]", token)
                    or re.fullmatch(r"[ivxlcdm]+", token)
                    for token in group[1:]
                )
                for group in groups
            )
        )

    return bool(suffixes) and all(
        suffix
        and (
            all(token in allowed_suffix_tokens for token in suffix.split())
            or is_note_reference_suffix(suffix)
        )
        for suffix in suffixes
    )


def _without_decorative_parentheticals(value: str) -> str:
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

    return re.sub(r"\(([^()]*)\)", replacement, value)


def _matcher_match_kind(
    value: Any,
    matcher: dict[str, Any],
    *,
    enable_declared_equivalences: bool = False,
) -> str | None:
    mode = matcher.get("match_mode", "EXACT_NORMALIZED")

    def normalize_member(value_to_normalize: Any) -> str:
        folded = _normalized(value_to_normalize)
        return re.sub(
            r"\b(?:1\s*tv|mtv|mot\s+tv|1\s+thanh\s+vien)\b",
            "mot thanh vien",
            folded,
        )

    # Preserve the declared alias axis for the primary exact gate.  Configured
    # equivalences are deliberately secondary evidence: an exact declared
    # ``MTV`` spelling must not be reported as if it were an inferred
    # ``1TV``/``một thành viên`` equivalence.
    aliases = [_normalized(alias) for alias in matcher["aliases"]]
    if mode == "EXACT_NORMALIZED":
        if any(_matches(value, alias) for alias in aliases):
            return "EXACT_NORMALIZED"
        if enable_declared_equivalences and matcher.get(
            "normalize_single_member_abbreviations", False
        ):
            transformed_aliases = [normalize_member(alias) for alias in matcher["aliases"]]
            folded = normalize_member(value)
            forms = {folded, _without_leading_ordinal(folded)}
            if any(alias in forms for alias in transformed_aliases):
                return "EXACT_NORMALIZED_SINGLE_MEMBER_ABBREVIATION_EQUIVALENCE"
        if (
            enable_declared_equivalences
            and matcher.get("allow_decorative_parenthetical_removal", False)
            and type(value) is str
        ):
            stripped = _without_decorative_parentheticals(value)
            if stripped != value and any(_matches(stripped, alias) for alias in aliases):
                return "EXACT_NORMALIZED_AFTER_DECORATIVE_PARENTHETICAL_REMOVAL"
        if enable_declared_equivalences and matcher.get(
            "allow_trailing_organization_qualifier", False
        ):
            folded = _normalized(value)
            forms = {folded, _without_leading_ordinal(folded)}
            forbidden = {"bao", "gom", "khong", "loai", "ngoai", "sau", "tru", "truoc"}
            for form in forms:
                for alias in aliases:
                    prefix = alias + " tai "
                    if not form.startswith(prefix):
                        continue
                    qualifier_tokens = form[len(prefix) :].split()
                    if (
                        1 <= len(qualifier_tokens) <= 6
                        and not forbidden.intersection(qualifier_tokens)
                        and all(re.fullmatch(r"[0-9a-z]+", token) for token in qualifier_tokens)
                    ):
                        return "EXACT_NORMALIZED_WITH_TRAILING_ORGANIZATION_QUALIFIER"
        return None
    folded = _normalized(value)
    forms = {folded, _without_leading_ordinal(folded)}
    forms |= {
        form.removeprefix(prefix).strip()
        for form in tuple(forms)
        for prefix in ("trong do ", "bao gom ")
        if form.startswith(prefix)
    }

    def contains(form: str, phrase: str, *, start: int = 0) -> int:
        padded = f" {form} "
        token = f" {phrase} "
        position = padded.find(token, start)
        return position + len(token) if position >= 0 else -1

    if mode == "CONTAINS_NORMALIZED_PHRASE":
        return (
            "CONTAINS_NORMALIZED_PHRASE"
            if any(contains(form, alias) >= 0 for form in forms for alias in aliases)
            else None
        )
    if mode == "CONTAINS_ORDERED_NORMALIZED_PHRASES":
        for form in forms:
            cursor = 0
            for alias in aliases:
                cursor = contains(form, alias, start=cursor)
                if cursor < 0:
                    break
            else:
                return "CONTAINS_ORDERED_NORMALIZED_PHRASES"
        return None
    raise _error("Gemini JSON hierarchy matcher mode is invalid")


def _matcher_matches(
    value: Any,
    matcher: dict[str, Any],
    *,
    enable_declared_equivalences: bool = False,
) -> bool:
    return (
        _matcher_match_kind(
            value,
            matcher,
            enable_declared_equivalences=enable_declared_equivalences,
        )
        is not None
    )


def _bounded_one_character_parent_title_match(
    title: str,
    aliases: list[str],
) -> dict[str, str] | None:
    """Return one unique one-edit parent phrase proposal inside a full title.

    This is deliberately only a proposal.  The caller still requires the
    complete local hierarchy and one exact all-lane accounting solution before
    it can produce a READY candidate.
    """

    title_tokens = _normalized(title).split()
    proposals: list[dict[str, str]] = []
    for raw_alias in aliases:
        alias = _normalized(raw_alias)
        alias_tokens = alias.split()
        if len(alias_tokens) < 3 or len(alias.replace(" ", "")) < 12:
            continue
        for start in range(len(title_tokens) - len(alias_tokens) + 1):
            surface = " ".join(title_tokens[start : start + len(alias_tokens)])
            match_kind = match_vietnamese_anchor_alias_v1(surface, [alias])
            if match_kind != "ONE_EDIT_ALIAS_IN_COMPLETE_ORDERED_TOPOLOGY":
                continue
            proposal = {
                "alias": raw_alias,
                "match_mode": "ONE_EDIT_PARENT_PHRASE_IN_EXACT_ACCOUNTING_GRAPH",
                "normalized_surface": surface,
                "source_title_exact": title,
            }
            if proposal not in proposals:
                proposals.append(proposal)
    return proposals[0] if len(proposals) == 1 else None


def _path_value_matches_alias(folded: str, alias: str, label: str) -> bool:
    alias = _normalized(alias)
    stripped = _without_leading_ordinal(folded)
    if _matches(stripped, alias):
        return True
    # Gemini can concatenate the last ancestor and the current row label in
    # one path string (for example "Chứng khoán NợTổng").  Accept only exact
    # whitespace-free ancestor+label identity, never a loose substring.
    if label and stripped.replace(" ", "") == (alias + label).replace(" ", ""):
        return True
    if not label or not stripped.endswith(" " + label):
        return False
    ancestor_prefix = stripped[: -len(label)].strip()
    return (
        ancestor_prefix == alias
        or ancestor_prefix.startswith(alias + " ")
        or ancestor_prefix.endswith(alias)
        or ancestor_prefix.endswith(" " + alias)
        or f" {alias} " in f" {ancestor_prefix} "
    )


def _path_has_role(
    path: Any,
    *,
    aliases: list[str],
    label_exact: Any,
) -> bool:
    if type(path) is not list:
        return False
    label = _normalized(label_exact)
    for value in path:
        folded = _normalized(value)
        if not folded or folded == label:
            continue
        if any(_path_value_matches_alias(folded, alias, label) for alias in aliases):
            return True
    return False


def _path_role_position(path: Any, *, aliases: list[str], label_exact: Any) -> int:
    if type(path) is not list:
        return -1
    label = _normalized(label_exact)
    positions = []
    for position, value in enumerate(path):
        folded = _normalized(value)
        if (
            folded
            and folded != label
            and any(_path_value_matches_alias(folded, alias, label) for alias in aliases)
        ):
            positions.append(position)
    return max(positions, default=-1)


def _money(value: Any) -> dict[str, Any]:
    if value is None:
        return {
            "coefficient": None,
            "source_text": None,
            "state": "BLANK_SOURCE_CELL",
        }
    if type(value) is not str or not value.strip():
        raise _error("Gemini JSON hierarchy money cell is invalid")
    body = value.strip()
    if body and all(character in _DASHES for character in body):
        return {"coefficient": 0, "source_text": value, "state": "DASH_ZERO"}
    if (
        body[0] in _DASHES
        and body[-1] in _DASHES
        and _normalized(body.strip("".join(_DASHES)).strip()) == "tiep theo"
    ):
        return {
            "coefficient": 0,
            "source_text": value,
            "state": "LAYOUT_CONTINUATION_MARKER_ZERO",
        }
    negative = body.startswith("(") and body.endswith(")")
    body = body[1:-1].strip() if negative else body
    if body.startswith("-"):
        if negative:
            raise _error("Gemini JSON hierarchy money sign is contradictory")
        negative = True
        body = body[1:].strip()
    digits = body.replace(".", "").replace(",", "").replace(" ", "")
    if not digits.isdigit():
        raise _error("Gemini JSON hierarchy money cell is not an exact integer")
    coefficient = int(digits)
    return {
        "coefficient": -coefficient if negative else coefficient,
        "source_text": value,
        "state": "RAW_SIGNED_INTEGER",
    }


def _header_text(column: Any) -> str:
    path = column.get("header_path_exact") if type(column) is dict else None
    if (
        type(path) is not list
        or not path
        or any(value is not None and type(value) is not str for value in path)
    ):
        return ""
    return " ".join(value for value in path if value).strip()


def _date_parse_text(value: str) -> str:
    """Make a literal JSON line-break escape whitespace without moving spans."""

    return value.replace("\\n", "  ")


def _header_date(value: str) -> date | None:
    parse_text = _date_parse_text(value)
    for pattern in (_DATE_DMY, _DATE_WORDS):
        for match in pattern.finditer(parse_text):
            try:
                return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
            except ValueError:
                continue
    # A slash date is interpreted as MDY only when it cannot be DMY: the
    # second field is a valid day above 12.  Ambiguous 01/02-style dates retain
    # the project's DMY authority and never reach this fallback.
    for match in _DATE_MDY.finditer(parse_text):
        month = int(match.group(1))
        day = int(match.group(2))
        if day <= 12:
            continue
        try:
            return date(int(match.group(3)), month, day)
        except ValueError:
            continue
    return None


def _header_dates(value: str) -> set[date]:
    parse_text = _date_parse_text(value)
    parsed: set[date] = set()
    for pattern in (_DATE_DMY, _DATE_WORDS):
        for match in pattern.finditer(parse_text):
            try:
                parsed.add(date(int(match.group(3)), int(match.group(2)), int(match.group(1))))
            except ValueError:
                continue
    for match in _DATE_MDY.finditer(parse_text):
        month = int(match.group(1))
        day = int(match.group(2))
        if day <= 12:
            continue
        try:
            parsed.add(date(int(match.group(3)), month, day))
        except ValueError:
            continue
    return parsed


def _ordered_exact_date_surfaces(value: str) -> list[dict[str, Any]]:
    """Return exact, non-fabricated dates in source order.

    DMY remains authoritative for an ambiguous slash date.  MDY is admitted
    only through the same unambiguous ``day > 12`` fallback as
    :func:`_header_date`.
    """

    parse_text = _date_parse_text(value)
    parsed: dict[tuple[int, int], dict[str, Any]] = {}
    for pattern in (_DATE_DMY, _DATE_WORDS):
        for match in pattern.finditer(parse_text):
            try:
                parsed_date = date(
                    int(match.group(3)), int(match.group(2)), int(match.group(1))
                )
            except ValueError:
                continue
            parsed[(match.start(), match.end())] = {
                "date": parsed_date,
                "source_text": value[match.start() : match.end()],
                "source_span": [match.start(), match.end()],
            }
    for match in _DATE_MDY.finditer(parse_text):
        span = (match.start(), match.end())
        if span in parsed:
            continue
        month = int(match.group(1))
        day = int(match.group(2))
        if day <= 12:
            continue
        try:
            parsed_date = date(int(match.group(3)), month, day)
        except ValueError:
            continue
        parsed[span] = {
            "date": parsed_date,
            "source_text": value[match.start() : match.end()],
            "source_span": [match.start(), match.end()],
        }
    return [parsed[span] for span in sorted(parsed)]


def _unique_section_narrative_period_pair(
    narratives: Any,
) -> dict[str, Any] | None:
    """Bind one explicit current/comparative narrative without inventing dates."""

    if type(narratives) is not list or any(type(value) is not str for value in narratives):
        return None
    candidates = []
    for ordinal, narrative in enumerate(narratives, start=1):
        normalized = _normalized(narrative)
        comparative_marker = re.search(r"\(\s*tại\s+ngày\b", narrative, re.IGNORECASE)
        records = _ordered_exact_date_surfaces(narrative)
        if (
            not normalized.startswith("tai ngay ")
            or len(re.findall(r"\btai ngay\b", normalized)) != 2
            or comparative_marker is None
            or len(records) != 2
            or records[0]["date"] <= records[1]["date"]
            or records[0]["source_span"][0] >= comparative_marker.start()
            or records[1]["source_span"][0] <= comparative_marker.start()
        ):
            continue
        candidates.append(
            {
                "dates": [record["date"] for record in records],
                "date_source_texts": [record["source_text"] for record in records],
                "narrative_exact": narrative,
                "narrative_ordinal": ordinal,
            }
        )
    if len(candidates) != 1:
        return None
    selected_ordinal = candidates[0]["narrative_ordinal"]
    if any(
        _header_dates(narrative)
        for ordinal, narrative in enumerate(narratives, start=1)
        if ordinal != selected_ordinal
    ):
        return None
    return candidates[0]


def _narrative_period_tables_are_exact_parallel_populations(
    source_tables: list[dict[str, Any]],
) -> bool:
    """Require two closed, header-identical money tables before order projection."""

    if len(source_tables) != 2 or any(
        table.get("continuation") != "NONE" for table in source_tables
    ):
        return False
    column_axes = []
    for table in source_tables:
        columns = table.get("columns")
        rows = table.get("rows")
        if (
            type(columns) is not list
            or not columns
            or any(
                type(column) is not dict
                or column.get("value_kind") != "MONEY"
                or not _normalized(_header_text(column))
                for column in columns
            )
            or type(rows) is not list
            or len(rows) < 2
        ):
            return False
        column_axes.append(
            [(_normalized(_header_text(column)), column["value_kind"]) for column in columns]
        )
        total_ordinals = [
            ordinal
            for ordinal, row in enumerate(rows, start=1)
            if type(row) is dict and row.get("row_kind") == "TOTAL"
        ]
        if total_ordinals != [len(rows)] or not _is_generic_total_label(
            rows[-1].get("label_exact")
        ):
            return False
        try:
            for column_index in range(len(columns)):
                if any(
                    type(row) is not dict
                    or type(row.get("values_exact")) is not list
                    or len(row["values_exact"]) != len(columns)
                    for row in rows[:-1]
                ):
                    return False
                component_records = [
                    {"cells": [_money(row["values_exact"][column_index])]}
                    for row in rows[:-1]
                ]
                total_record = {
                    "cells": [_money(rows[-1]["values_exact"][column_index])]
                }
                if not _source_equation_matches_on_observed_lanes(
                    total_record, component_records
                ):
                    return False
        except (KeyError, IndexError, TypeError, ValueError):
            return False
    return column_axes[0] == column_axes[1]


def _period_alias_role(value: str) -> str | None:
    folded = _normalized(value)
    current = any(
        alias == folded or f" {alias} " in f" {folded} " for alias in _CURRENT_PERIOD_ALIASES
    )
    comparative = any(
        alias == folded or f" {alias} " in f" {folded} " for alias in _COMPARATIVE_PERIOD_ALIASES
    )
    if current == comparative:
        return None
    return "CURRENT_PERIOD" if current else "COMPARATIVE_PERIOD"


def _period_signature(value: str) -> tuple[str, str] | None:
    parsed = _header_date(value)
    if parsed is not None:
        return "DATE", parsed.isoformat()
    role = _period_alias_role(value)
    return ("SEMANTIC_ALIAS", role) if role is not None else None


def _percent(value: Any) -> dict[str, Any]:
    if value is None:
        return {"source_text": None, "state": "BLANK_PRESENTATION"}
    if type(value) is not str or not value.strip():
        raise _error("Gemini JSON hierarchy percentage cell is invalid")
    body = value.strip()
    if body in _DASHES:
        return {
            "coefficient": 0,
            "scale": 0,
            "source_text": value,
            "state": "DASH_ZERO",
        }
    body = body.removesuffix("%").strip().replace(" ", "")
    if "," in body and "." in body:
        raise _error("Gemini JSON hierarchy percentage separator is ambiguous")
    normalized = body.replace(",", ".")
    try:
        parsed = Decimal(normalized)
    except InvalidOperation as exc:
        raise _error("Gemini JSON hierarchy percentage cell is not an exact decimal") from exc
    if not parsed.is_finite() or parsed < 0 or parsed > 100:
        raise _error("Gemini JSON hierarchy percentage cell is outside zero to one hundred")
    exponent = parsed.as_tuple().exponent
    scale = max(0, -exponent)
    coefficient = int(parsed.scaleb(scale))
    return {
        "coefficient": coefficient,
        "scale": scale,
        "source_text": value,
        "state": "RAW_UNSIGNED_DECIMAL_PERCENT",
    }


def _footnote_narrative_mapping_evidence(
    *,
    table_title: Any,
    narratives: Any,
    period_value_axis_receipt: dict[str, Any] | None,
    policies: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Parse exact two-lane source adjustments declared by a table footnote."""

    title = table_title if type(table_title) is str else ""
    active = [policy for policy in policies if policy["footnote_marker"] in title]
    if not active:
        return [], []
    if len(active) != 1 or type(narratives) is not list or period_value_axis_receipt is None:
        return [], ["TITLE_FOOTNOTE_NARRATIVE_SOURCE_NOT_EXACT"]
    policy = active[0]
    matches = []
    for narrative_ordinal, narrative in enumerate(narratives, start=1):
        if type(narrative) is not str:
            continue
        folded = _normalized(narrative)
        cursor = 0
        for phrase in policy["required_ordered_phrases"]:
            position = folded.find(_normalized(phrase), cursor)
            if position < 0:
                break
            cursor = position + len(_normalized(phrase))
        else:
            source_match = _EXCLUDED_TWO_LANE_NARRATIVE.search(narrative)
            if source_match is None or not all(
                _normalized(unit) in {_normalized(alias) for alias in policy["unit_aliases"]}
                for unit in (
                    source_match.group("current_unit"),
                    source_match.group("comparative_unit"),
                )
            ):
                continue
            try:
                comparative_date = date(
                    int(source_match.group("year")),
                    int(source_match.group("month")),
                    int(source_match.group("day")),
                )
                cells = [
                    _money(source_match.group("current")),
                    _money(source_match.group("comparative")),
                ]
            except (ValueError, TypeError):
                continue
            signatures = period_value_axis_receipt["period_signatures"]
            if signatures[1] != ["DATE", comparative_date.isoformat()]:
                continue
            matches.append(
                {
                    "cells": cells,
                    "emitted_mapping_role": policy["emitted_mapping_role"],
                    "footnote_marker": policy["footnote_marker"],
                    "narrative_exact": narrative,
                    "narrative_ordinal": narrative_ordinal,
                    "operation": policy["operation"],
                    "source_comparative_date": comparative_date.isoformat(),
                }
            )
    if len(matches) != 1:
        return [], ["TITLE_FOOTNOTE_NARRATIVE_SOURCE_NOT_EXACT"]
    return matches, []


def _period_value_column_axis(
    *, columns: Any, table_unit: Any, evaluation: dict[str, Any]
) -> tuple[list[int], list[dict[str, Any]], list[int], dict[str, Any] | None, list[str]]:
    """Bind one or two accounting periods with optional paired percentages."""

    reasons: list[str] = []
    if type(columns) is not list or not columns:
        return [], [], [], None, ["PERIOD_VALUE_COLUMN_AXIS_IS_ABSENT"]
    kinds = [column.get("value_kind") if type(column) is dict else None for column in columns]
    allowed = evaluation.get("expected_lane_unit_kind_alternatives")
    if allowed is None:
        allowed = [evaluation.get("expected_lane_unit_kinds")]
    if kinds not in allowed:
        reasons.append("PERIOD_VALUE_COLUMN_KIND_SEQUENCE_IS_NOT_DECLARED")
    money_indices = [index for index, kind in enumerate(kinds) if kind == "MONEY"]
    percent_indices = [index for index, kind in enumerate(kinds) if kind == "PERCENT"]
    money_columns = [columns[index] for index in money_indices]
    supported_money_lane_counts = (
        {1, 2}
        if evaluation.get("format_version") == "ACCOUNTING_FAMILY_EVALUATION_SPEC_V7"
        else {2}
    )
    if len(money_indices) not in supported_money_lane_counts or any(
        not _header_text(column) for column in columns
    ):
        reasons.append("PERIOD_VALUE_COLUMN_HEADER_OR_MONEY_LANE_COUNT_IS_NOT_EXACT")
        return money_indices, money_columns, percent_indices, None, reasons
    if percent_indices and (
        len(percent_indices) != 2
        or len(columns) != 4
        or money_indices != [0, 2]
        or percent_indices != [1, 3]
    ):
        reasons.append("PERCENTAGE_COMPANION_COLUMN_ORDER_IS_NOT_PERIOD_PAIRED")
    unit_declared = type(table_unit) is str and bool(table_unit.strip())
    if not unit_declared:
        unit_declared = all(
            any(
                token in _normalized(_header_text(column))
                for token in ("trieu dong", "trieu vnd", "nghin dong", "vnd")
            )
            for column in money_columns
        )
    unit_disposition = (
        "EXPLICIT_TABLE_OR_COLUMN_MONEY_UNIT"
        if unit_declared
        else "SOURCE_TABLE_UNIT_NOT_EXPLICIT_RAW_COEFFICIENTS_PRESERVED"
    )
    signatures = [_period_signature(_header_text(column)) for column in money_columns]
    if any(signature is None for signature in signatures):
        reasons.append("CURRENT_AND_COMPARATIVE_PERIOD_HEADERS_ARE_NOT_EXACT")
    elif len(signatures) == 2 and signatures[0][0] != signatures[1][0]:
        reasons.append("CURRENT_AND_COMPARATIVE_PERIOD_HEADER_KINDS_DIFFER")
    elif (
        len(signatures) == 2
        and signatures[0][0] == "DATE"
        and not signatures[0][1] > signatures[1][1]
    ):
        reasons.append("CURRENT_PERIOD_DATE_IS_NOT_AFTER_COMPARATIVE_PERIOD_DATE")
    elif (
        len(signatures) == 2
        and signatures
        != [
            ("SEMANTIC_ALIAS", "CURRENT_PERIOD"),
            ("SEMANTIC_ALIAS", "COMPARATIVE_PERIOD"),
        ]
        and signatures[0][0] == "SEMANTIC_ALIAS"
    ):
        reasons.append("ORDERED_CURRENT_COMPARATIVE_PERIOD_ALIASES_DO_NOT_REPLAY")
    if percent_indices and len(percent_indices) == 2:
        companion_signatures = []
        for period_ordinal, index in enumerate(percent_indices):
            header = _header_text(columns[index])
            signature = _period_signature(header)
            if signature is None and (
                header.strip() == "%" or _normalized(header) in {"ty le", "phan tram"}
            ):
                signature = signatures[period_ordinal]
            companion_signatures.append(signature)
        if companion_signatures != signatures:
            reasons.append("PERCENTAGE_COMPANION_PERIODS_DO_NOT_MATCH_MONEY_PERIODS")
    receipt = (
        {
            "money_column_indices": money_indices,
            "percent_column_indices": percent_indices,
            "period_signatures": [list(signature) for signature in signatures],
            "source_value_kind_sequence": kinds,
            "unit_disposition": unit_disposition,
        }
        if not reasons
        else None
    )
    return money_indices, money_columns, percent_indices, receipt, reasons


def _compile_specs(topology_spec: Any, evaluation_spec: Any, schema_spec: Any) -> dict[str, Any]:
    try:
        topology = compile_accounting_family_topology_spec_v1(topology_spec)
    except ValueError as exc:
        raise _error("Gemini JSON hierarchy topology spec is invalid") from exc
    evaluation_format = (
        evaluation_spec.get("format_version") if type(evaluation_spec) is dict else None
    )
    evaluation_keys = {
        "closure_policy",
        "expected_lane_unit_kinds",
        "family_id",
        "format_version",
        "hierarchical_closure_spec",
        "period_semantics",
    }
    if evaluation_format == "ACCOUNTING_FAMILY_EVALUATION_SPEC_V4":
        evaluation_keys |= {
            "candidate_selection_policy",
            "occurrence_row_axis_policy",
        }
    if evaluation_format in {
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V5",
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V6",
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V7",
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V8",
    }:
        evaluation_keys = {
            "candidate_selection_policy",
            "closure_policy",
            "expected_lane_unit_kind_alternatives",
            "family_id",
            "format_version",
            "hierarchical_closure_spec",
            "occurrence_row_axis_policy",
            "period_semantics",
        }
        if evaluation_format == "ACCOUNTING_FAMILY_EVALUATION_SPEC_V6":
            evaluation_keys.add("period_table_projection_policy")
        elif evaluation_format == "ACCOUNTING_FAMILY_EVALUATION_SPEC_V7":
            evaluation_keys.add("dual_axis_projection_policy")
        elif evaluation_format == "ACCOUNTING_FAMILY_EVALUATION_SPEC_V8":
            evaluation_keys.add("title_axis_projection_policy")
    lane_alternatives = (
        evaluation_spec.get("expected_lane_unit_kind_alternatives")
        if type(evaluation_spec) is dict
        and evaluation_format
        in {
            "ACCOUNTING_FAMILY_EVALUATION_SPEC_V5",
            "ACCOUNTING_FAMILY_EVALUATION_SPEC_V6",
            "ACCOUNTING_FAMILY_EVALUATION_SPEC_V7",
            "ACCOUNTING_FAMILY_EVALUATION_SPEC_V8",
        }
        else [evaluation_spec.get("expected_lane_unit_kinds")]
        if type(evaluation_spec) is dict
        else None
    )
    if (
        type(evaluation_spec) is not dict
        or set(evaluation_spec) != evaluation_keys
        or evaluation_format not in _EVALUATION_FORMATS
        or evaluation_spec.get("family_id") != topology["family_id"]
        or type(lane_alternatives) is not list
        or not lane_alternatives
        or any(
            alternative not in (["MONEY", "MONEY"], ["MONEY", "PERCENT", "MONEY", "PERCENT"])
            and not (
                evaluation_format == "ACCOUNTING_FAMILY_EVALUATION_SPEC_V7"
                and alternative == ["MONEY"]
            )
            for alternative in lane_alternatives
        )
        or len({tuple(alternative) for alternative in lane_alternatives}) != len(lane_alternatives)
    ):
        raise _error("Gemini JSON hierarchy evaluation spec is invalid or unsupported")
    period_table_projection_policy = None
    dual_axis_projection_policy = None
    title_axis_projection_policy = None
    if evaluation_format == "ACCOUNTING_FAMILY_EVALUATION_SPEC_V6":
        raw_projection = evaluation_spec["period_table_projection_policy"]
        if (
            type(raw_projection) is not dict
            or set(raw_projection)
            != {
                "format_version",
                "period_table_count",
                "population_policy",
                "target_column_aliases",
            }
            or raw_projection["format_version"] != "GEMINI_JSON_PERIOD_TABLE_PROJECTION_POLICY_V1"
            or raw_projection["period_table_count"] != 2
            or raw_projection["population_policy"]
            != "IDENTICAL_DECLARED_ROLE_POPULATION_AND_SOURCE_ORDER"
            or type(raw_projection["target_column_aliases"]) is not list
            or not raw_projection["target_column_aliases"]
            or any(
                type(alias) is not str or not _normalized(alias)
                for alias in raw_projection["target_column_aliases"]
            )
            or len({_normalized(alias) for alias in raw_projection["target_column_aliases"]})
            != len(raw_projection["target_column_aliases"])
        ):
            raise _error("Gemini JSON period-table projection policy is invalid")
        period_table_projection_policy = {
            **canonical_clone_v1(raw_projection),
            "target_column_aliases": sorted(
                {_normalized(alias) for alias in raw_projection["target_column_aliases"]}
            ),
        }
    elif evaluation_format == "ACCOUNTING_FAMILY_EVALUATION_SPEC_V7":
        raw_projection = evaluation_spec["dual_axis_projection_policy"]
        expected_fields = {
            "blank_role_cell_policy",
            "blank_zero_derivable_roles",
            "format_version",
            "metric_aliases",
            "orientations",
            "period_cluster_policy",
            "period_table_count_alternatives",
            "population_policy",
            "projected_role_order",
            "total_aliases",
            "unit_aliases",
        }
        optional_fields = {
            "external_population_control",
            "source_blank_mapping_policy",
            "visible_total_rounding_policy",
        }
        if (
            type(raw_projection) is not dict
            or not expected_fields <= set(raw_projection)
            or not set(raw_projection) <= expected_fields | optional_fields
        ):
            raise _error("Gemini JSON dual-axis projection policy fields are invalid")
        normalized_alias_lists: dict[str, list[str]] = {}
        for field in ("metric_aliases", "total_aliases", "unit_aliases"):
            values = raw_projection[field]
            if (
                type(values) is not list
                or not values
                or any(type(value) is not str or not _normalized(value) for value in values)
            ):
                raise _error("Gemini JSON dual-axis projection aliases are invalid")
            normalized = [_normalized(value) for value in values]
            if len(normalized) != len(set(normalized)):
                raise _error("Gemini JSON dual-axis projection aliases are ambiguous")
            normalized_alias_lists[field] = normalized
        projected_roles = raw_projection["projected_role_order"]
        blank_zero_derivable_roles = raw_projection["blank_zero_derivable_roles"]
        source_blank_mapping_policy = raw_projection.get(
            "source_blank_mapping_policy",
            "REQUIRE_ALL_ROLES_OR_EXACT_ZERO_DERIVATION",
        )
        external_population_control = raw_projection.get("external_population_control")
        compiled_external_population_control = None
        if external_population_control is not None:
            external_fields = {
                "candidate_context",
                "control_report_norm_id",
                "control_source",
                "controlled_metric_aliases",
                "format_version",
                "match_rule",
                "query_gate_metric_aliases",
                "unit_decimal_magnitude_by_alias",
            }
            control_source_fields = {
                "content_kind",
                "hierarchy_match_rule",
                "label_aliases",
                "label_match_rule",
                "row_kind",
                "statement_type",
            }
            candidate_context_fields = {
                "hard_negative_aliases",
                "partial_axis_owner_aliases",
            }

            def normalized_unique_alias_axis(value: Any) -> list[str] | None:
                if (
                    type(value) is not list
                    or not value
                    or any(type(alias) is not str or not _normalized(alias) for alias in value)
                ):
                    return None
                normalized = [_normalized(alias) for alias in value]
                return normalized if len(normalized) == len(set(normalized)) else None

            control_source = (
                external_population_control.get("control_source")
                if type(external_population_control) is dict
                else None
            )
            candidate_context = (
                external_population_control.get("candidate_context")
                if type(external_population_control) is dict
                else None
            )
            controlled_aliases = (
                normalized_unique_alias_axis(
                    external_population_control.get("controlled_metric_aliases")
                )
                if type(external_population_control) is dict
                else None
            )
            query_gate_aliases = (
                normalized_unique_alias_axis(
                    external_population_control.get("query_gate_metric_aliases")
                )
                if type(external_population_control) is dict
                else None
            )
            control_label_aliases = (
                normalized_unique_alias_axis(control_source.get("label_aliases"))
                if type(control_source) is dict
                else None
            )
            hard_negative_aliases = (
                normalized_unique_alias_axis(candidate_context.get("hard_negative_aliases"))
                if type(candidate_context) is dict
                else None
            )
            partial_owner_aliases = (
                normalized_unique_alias_axis(
                    candidate_context.get("partial_axis_owner_aliases")
                )
                if type(candidate_context) is dict
                else None
            )
            magnitude_axis = (
                external_population_control.get("unit_decimal_magnitude_by_alias")
                if type(external_population_control) is dict
                else None
            )
            normalized_magnitude_axis = (
                {
                    _normalized(alias): magnitude
                    for alias, magnitude in magnitude_axis.items()
                }
                if type(magnitude_axis) is dict
                and all(
                    type(alias) is str
                    and _normalized(alias)
                    and type(magnitude) is int
                    and 0 <= magnitude <= 18
                    for alias, magnitude in magnitude_axis.items()
                )
                else None
            )
            if (
                type(external_population_control) is not dict
                or set(external_population_control) != external_fields
                or external_population_control.get("format_version")
                != "GEMINI_JSON_DUAL_AXIS_EXTERNAL_POPULATION_CONTROL_V1"
                or type(external_population_control.get("control_report_norm_id")) is not int
                or external_population_control["control_report_norm_id"] <= 0
                or external_population_control.get("match_rule")
                != "EXACT_PERIOD_UNIT_MAGNITUDE_AND_INTEGER_EQUALITY"
                or type(control_source) is not dict
                or set(control_source) != control_source_fields
                or control_source.get("content_kind") != "PRIMARY_STATEMENT"
                or control_source.get("statement_type") != "BALANCE_SHEET"
                or control_source.get("row_kind") != "ITEM"
                or control_source.get("label_match_rule")
                != "EXACT_WITH_OPTIONAL_LEADING_ONE"
                or control_source.get("hierarchy_match_rule")
                != "NUMBERED_LABEL_OR_REPEATED_UNNUMBERED_EXACT_LABEL"
                or control_label_aliases is None
                or type(candidate_context) is not dict
                or set(candidate_context) != candidate_context_fields
                or hard_negative_aliases is None
                or partial_owner_aliases is None
                or controlled_aliases is None
                or not set(controlled_aliases) <= set(normalized_alias_lists["metric_aliases"])
                or query_gate_aliases is None
                or not set(query_gate_aliases) <= set(controlled_aliases)
                or normalized_magnitude_axis is None
                or len(normalized_magnitude_axis) != len(magnitude_axis)
                or set(normalized_magnitude_axis)
                != set(normalized_alias_lists["unit_aliases"])
            ):
                raise _error("Gemini JSON dual-axis external population control is invalid")
            compiled_external_population_control = {
                **canonical_clone_v1(external_population_control),
                "candidate_context": {
                    "hard_negative_aliases": hard_negative_aliases,
                    "partial_axis_owner_aliases": partial_owner_aliases,
                },
                "control_source": {
                    **canonical_clone_v1(control_source),
                    "label_aliases": control_label_aliases,
                },
                "controlled_metric_aliases": controlled_aliases,
                "query_gate_metric_aliases": query_gate_aliases,
                "unit_decimal_magnitude_by_alias": dict(
                    sorted(normalized_magnitude_axis.items())
                ),
            }

        visible_total_rounding_policy = raw_projection.get(
            "visible_total_rounding_policy"
        )
        compiled_visible_total_rounding_policy = None
        if visible_total_rounding_policy is not None:
            rounding_fields = {
                "format_version",
                "maximum_absolute_display_residual",
                "minimum_unit_decimal_magnitude",
                "unit_decimal_magnitude_by_alias",
            }
            rounding_magnitudes = (
                visible_total_rounding_policy.get("unit_decimal_magnitude_by_alias")
                if type(visible_total_rounding_policy) is dict
                else None
            )
            normalized_rounding_magnitudes = (
                {
                    _normalized(alias): magnitude
                    for alias, magnitude in rounding_magnitudes.items()
                }
                if type(rounding_magnitudes) is dict
                and all(
                    type(alias) is str
                    and _normalized(alias)
                    and type(magnitude) is int
                    and 0 <= magnitude <= 18
                    for alias, magnitude in rounding_magnitudes.items()
                )
                else None
            )
            if (
                type(visible_total_rounding_policy) is not dict
                or set(visible_total_rounding_policy) != rounding_fields
                or visible_total_rounding_policy.get("format_version")
                != "GEMINI_JSON_DUAL_AXIS_VISIBLE_TOTAL_ROUNDING_POLICY_V1"
                or type(
                    visible_total_rounding_policy.get("maximum_absolute_display_residual")
                )
                is not int
                or not 0
                < visible_total_rounding_policy["maximum_absolute_display_residual"]
                <= 2
                or type(
                    visible_total_rounding_policy.get("minimum_unit_decimal_magnitude")
                )
                is not int
                or not 3
                <= visible_total_rounding_policy["minimum_unit_decimal_magnitude"]
                <= 18
                or normalized_rounding_magnitudes is None
                or len(normalized_rounding_magnitudes) != len(rounding_magnitudes)
                or set(normalized_rounding_magnitudes)
                != set(normalized_alias_lists["unit_aliases"])
            ):
                raise _error("Gemini JSON dual-axis visible-total rounding policy is invalid")
            compiled_visible_total_rounding_policy = {
                **canonical_clone_v1(visible_total_rounding_policy),
                "unit_decimal_magnitude_by_alias": dict(
                    sorted(normalized_rounding_magnitudes.items())
                ),
            }
        topology_child_roles = {child["role"] for child in topology["children"]}
        preserves_source_blanks = (
            source_blank_mapping_policy == "PRESERVE_BLANK_OMIT_MAPPING"
        )
        if (
            raw_projection["format_version"] != "GEMINI_JSON_DUAL_AXIS_PROJECTION_POLICY_V1"
            or raw_projection["orientations"]
            != ["ROW_ROLES_METRIC_COLUMN", "METRIC_ROW_ROLE_COLUMNS"]
            or raw_projection["period_cluster_policy"]
            != "SAME_OR_ADJACENT_PAGE_EXACT_PERIOD_COMPLEMENT"
            or raw_projection["period_table_count_alternatives"] != [1, 2]
            or raw_projection["population_policy"]
            != "EXACT_OPPOSITE_AXIS_QUALIFIER_AND_EXHAUSTIVE_ROLE_PAIR"
            or raw_projection["blank_role_cell_policy"]
            != (
                "PRESERVE_SOURCE_BLANK_OMIT_MAPPING"
                if preserves_source_blanks
                else "ALLOW_ZERO_ONLY_WHEN_EXACT_TOTAL_EQUALS_OTHER_ROLE"
            )
            or source_blank_mapping_policy
            not in {
                "REQUIRE_ALL_ROLES_OR_EXACT_ZERO_DERIVATION",
                "OMIT_ROLE_WHEN_SOURCE_BLANK_AND_NO_EXACT_ZERO_EQUATION",
                "PRESERVE_BLANK_OMIT_MAPPING",
            }
            or type(projected_roles) is not list
            or len(projected_roles) != 2
            or len(set(projected_roles)) != 2
            or any(role not in topology_child_roles for role in projected_roles)
            or type(blank_zero_derivable_roles) is not list
            or len(blank_zero_derivable_roles) != len(set(blank_zero_derivable_roles))
            or any(role not in projected_roles for role in blank_zero_derivable_roles)
            or preserves_source_blanks
            and bool(blank_zero_derivable_roles)
            or not preserves_source_blanks
            and not blank_zero_derivable_roles
        ):
            raise _error("Gemini JSON dual-axis projection policy is invalid")
        dual_axis_projection_policy = {
            **canonical_clone_v1(raw_projection),
            **normalized_alias_lists,
            "source_blank_mapping_policy": source_blank_mapping_policy,
        }
        if compiled_external_population_control is not None:
            dual_axis_projection_policy["external_population_control"] = (
                compiled_external_population_control
            )
        if compiled_visible_total_rounding_policy is not None:
            dual_axis_projection_policy["visible_total_rounding_policy"] = (
                compiled_visible_total_rounding_policy
            )
    elif evaluation_format == "ACCOUNTING_FAMILY_EVALUATION_SPEC_V8":
        raw_projection = evaluation_spec["title_axis_projection_policy"]
        expected_fields = {
            "contextual_role_variants",
            "detached_root_component_policy",
            "format_version",
            "leading_parent_population_policy",
            "trailing_subtotal_population_policy",
            "minimum_distinct_child_roles",
            "owner_binding_policy",
            "owner_page_radius",
            "owner_reset_aliases",
            "required_child_roles",
            "structural_branch_role",
            "structural_surface_kinds",
        }
        optional_fields = {
            "structural_branch_fallback_group_roles",
            "unresolved_near_source_policy",
        }
        children_by_role_for_projection = {child["role"]: child for child in topology["children"]}
        contextual_variants = raw_projection.get("contextual_role_variants")
        branch_fallback_group_roles = raw_projection.get(
            "structural_branch_fallback_group_roles", []
        )
        unresolved_near_source_policy = raw_projection.get(
            "unresolved_near_source_policy", "ANY_UNVETOED_STRUCTURAL_AXIS"
        )
        if (
            type(raw_projection) is not dict
            or not expected_fields <= set(raw_projection)
            or not set(raw_projection) <= expected_fields | optional_fields
            or raw_projection.get("format_version")
            != "GEMINI_JSON_HIERARCHICAL_TITLE_AXIS_PROJECTION_POLICY_V1"
            or raw_projection.get("owner_binding_policy")
            != "LOCAL_THEN_PRECEDING_SELECTED_PAGE_OWNER_WITH_POPULATION_RESET"
            or raw_projection.get("owner_page_radius") != 2
            or raw_projection.get("leading_parent_population_policy")
            != "EXACT_CONTIGUOUS_DIRECT_CHILDREN_WITH_OPTIONAL_DECLARED_PEER_FENCE"
            or raw_projection.get("trailing_subtotal_population_policy")
            != "EXACT_CONTIGUOUS_DIRECT_CHILDREN_TRAILING_SUBTOTAL_WITH_DECLARED_PEER_FENCE"
            or raw_projection.get("detached_root_component_policy")
            != "DECLARED_DIRECT_ROOT_COMPONENTS_AND_UNIQUE_EXACT_TOTAL"
            or raw_projection.get("structural_surface_kinds")
            not in (
                ["TITLE", "SECTION_NARRATIVE"],
                ["TITLE", "SECTION_NARRATIVE", "GROUP_ROW"],
            )
            or raw_projection.get("structural_branch_role") not in children_by_role_for_projection
            or children_by_role_for_projection[raw_projection["structural_branch_role"]][
                "role_kind"
            ]
            != "STRUCTURAL_GROUP"
            or type(branch_fallback_group_roles) is not list
            or len(branch_fallback_group_roles) != len(set(branch_fallback_group_roles))
            or any(
                role == raw_projection["structural_branch_role"]
                or role not in children_by_role_for_projection
                or children_by_role_for_projection[role]["role_kind"] != "STRUCTURAL_GROUP"
                for role in branch_fallback_group_roles
            )
            or unresolved_near_source_policy
            not in {
                "ANY_UNVETOED_STRUCTURAL_AXIS",
                "REQUIRE_UNVETOED_BRANCH_OWNER_AND_MINIMUM_CHILD_ROLES",
            }
            or type(raw_projection.get("required_child_roles")) is not list
            or not raw_projection["required_child_roles"]
            or len(raw_projection["required_child_roles"])
            != len(set(raw_projection["required_child_roles"]))
            or any(
                role not in children_by_role_for_projection
                for role in raw_projection["required_child_roles"]
            )
            or type(raw_projection.get("minimum_distinct_child_roles")) is not int
            or not 2
            <= raw_projection["minimum_distinct_child_roles"]
            <= len(raw_projection["required_child_roles"])
            or not any(
                pool["roles"] == raw_projection["required_child_roles"]
                and pool["minimum_count"] == raw_projection["minimum_distinct_child_roles"]
                for pool in topology["required_role_pools"]
            )
            or type(raw_projection.get("owner_reset_aliases")) is not list
            or not raw_projection["owner_reset_aliases"]
            or any(
                type(alias) is not str or not _normalized(alias)
                for alias in raw_projection["owner_reset_aliases"]
            )
            or not {_normalized(alias) for alias in raw_projection["owner_reset_aliases"]}
            <= {_normalized(alias) for alias in topology["hard_negative_aliases"]}
            or type(contextual_variants) is not list
            or len(contextual_variants) > 8
            or any(
                type(variant) is not dict
                or set(variant)
                != {
                    "flat_terminal_role",
                    "nested_descendant_roles",
                    "operation",
                    "source_role",
                }
                or variant.get("operation")
                != "UNQUALIFIED_FLAT_ITEM_TO_TERMINAL_OR_EXACT_NESTED_SUBTOTAL"
                or variant.get("source_role") not in children_by_role_for_projection
                or variant.get("flat_terminal_role") not in children_by_role_for_projection
                or children_by_role_for_projection[variant["flat_terminal_role"]]["role_kind"]
                != "ADDITIVE_CHILD"
                or variant["flat_terminal_role"] == variant["source_role"]
                or type(variant.get("nested_descendant_roles")) is not list
                or not variant["nested_descendant_roles"]
                or len(variant["nested_descendant_roles"])
                != len(set(variant["nested_descendant_roles"]))
                or variant["flat_terminal_role"] not in variant["nested_descendant_roles"]
                or any(
                    role not in children_by_role_for_projection
                    or children_by_role_for_projection[role]["role_kind"] != "ADDITIVE_CHILD"
                    for role in variant["nested_descendant_roles"]
                )
                for variant in contextual_variants
            )
            or len({variant["source_role"] for variant in contextual_variants})
            != len(contextual_variants)
        ):
            raise _error("Gemini JSON hierarchical title-axis projection policy is invalid")
        title_axis_projection_policy = canonical_clone_v1(raw_projection)
    hierarchy = evaluation_spec["hierarchical_closure_spec"]
    if (
        type(hierarchy) is not dict
        or hierarchy.get("family_id") != topology["family_id"]
        or type(hierarchy.get("equations")) is not list
        or not hierarchy["equations"]
    ):
        raise _error("Gemini JSON hierarchy equation spec is invalid")
    children_by_role = {child["role"]: child for child in topology["children"]}
    known_roles = set(children_by_role) | {topology["parent"]["role"]}
    equations: list[dict[str, Any]] = []
    result_roles: set[str] = set()
    for equation in hierarchy["equations"]:
        result = equation.get("result_role") if type(equation) is dict else None
        alternatives = (
            equation.get("component_role_alternatives") if type(equation) is dict else None
        )
        maximum_rounding_residual = (
            equation.get("maximum_source_rounding_residual_coefficients", 0)
            if type(equation) is dict
            else None
        )
        if (
            result not in known_roles
            or result in result_roles
            or type(alternatives) is not list
            or not alternatives
            or type(maximum_rounding_residual) is not int
            or not 0 <= maximum_rounding_residual <= 1
        ):
            raise _error("Gemini JSON hierarchy equation result is invalid")
        checked_alternatives = []
        for alternative in alternatives:
            roles = alternative.get("component_roles") if type(alternative) is dict else None
            coverage = alternative.get("coverage_policy") if type(alternative) is dict else None
            lane_specific_only = (
                alternative.get("lane_specific_only", False) if type(alternative) is dict else None
            )
            if evaluation_format in {
                "ACCOUNTING_FAMILY_EVALUATION_SPEC_V4",
                "ACCOUNTING_FAMILY_EVALUATION_SPEC_V5",
                "ACCOUNTING_FAMILY_EVALUATION_SPEC_V6",
                "ACCOUNTING_FAMILY_EVALUATION_SPEC_V7",
                "ACCOUNTING_FAMILY_EVALUATION_SPEC_V8",
            }:
                selection_policy = equation.get("component_selection_policy")
                variable_subset = (
                    evaluation_format
                    in {
                        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V5",
                        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V6",
                        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V7",
                        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V8",
                    }
                    and selection_policy == "EXHAUSTIVE_VISIBLE_SUBSET_OF_DECLARED_POOL"
                )
                if evaluation_format in {
                    "ACCOUNTING_FAMILY_EVALUATION_SPEC_V5",
                    "ACCOUNTING_FAMILY_EVALUATION_SPEC_V6",
                    "ACCOUNTING_FAMILY_EVALUATION_SPEC_V7",
                    "ACCOUNTING_FAMILY_EVALUATION_SPEC_V8",
                } and selection_policy not in {
                    "DECLARED_EXACT_ALTERNATIVE",
                    "EXHAUSTIVE_VISIBLE_SUBSET_OF_DECLARED_POOL",
                }:
                    raise _error("Gemini JSON hierarchy component selection policy is invalid")
                minimum = 1 if variable_subset else len(roles) if type(roles) is list else None
                minimum_additive = 0
                derivation = alternative.get("derivation_policy")
                valid_policy = coverage == "EXHAUSTIVE_COMPONENT_SET" and derivation in {
                    "ALLOW_DERIVATION_FROM_EXHAUSTIVE_VISIBLE_COMPONENTS",
                    "VISIBLE_RESULT_CORROBORATION_ONLY",
                }
            else:
                minimum = alternative.get("minimum_component_count")
                minimum_additive = alternative.get("minimum_additive_child_count", 0)
                derivation = (
                    "ALLOW_DERIVATION_FROM_EXHAUSTIVE_VISIBLE_COMPONENTS"
                    if coverage == "EXHAUSTIVE_COMPONENT_SET"
                    else "VISIBLE_RESULT_CORROBORATION_ONLY"
                )
                valid_policy = (
                    coverage
                    in {
                        "EXHAUSTIVE_COMPONENT_SET",
                        "VISIBLE_RESULT_CORROBORATION_ONLY",
                    }
                    and type(minimum) is int
                    and type(minimum_additive) is int
                    and type(roles) is list
                    and 1 <= minimum <= len(roles)
                    and 0 <= minimum_additive <= len(roles)
                )
            if (
                type(roles) is not list
                or not roles
                or len(roles) != len(set(roles))
                or result in roles
                or any(role not in known_roles for role in roles)
                or type(lane_specific_only) is not bool
                or (
                    lane_specific_only
                    and evaluation_format != "ACCOUNTING_FAMILY_EVALUATION_SPEC_V3"
                )
                or not valid_policy
            ):
                raise _error("Gemini JSON hierarchy equation alternative is invalid")
            checked_alternatives.append(
                {
                    **canonical_clone_v1(alternative),
                    "derivation_policy": derivation,
                    "minimum_additive_child_count": minimum_additive,
                    "minimum_component_count": minimum,
                    "lane_specific_only": lane_specific_only,
                    "variable_component_subset": (
                        evaluation_format == "ACCOUNTING_FAMILY_EVALUATION_SPEC_V3"
                        or (
                            evaluation_format
                            in {
                                "ACCOUNTING_FAMILY_EVALUATION_SPEC_V5",
                                "ACCOUNTING_FAMILY_EVALUATION_SPEC_V6",
                                "ACCOUNTING_FAMILY_EVALUATION_SPEC_V7",
                                "ACCOUNTING_FAMILY_EVALUATION_SPEC_V8",
                            }
                            and equation.get("component_selection_policy")
                            == "EXHAUSTIVE_VISIBLE_SUBSET_OF_DECLARED_POOL"
                        )
                    ),
                }
            )
        visible_roles = equation.get("visible_result_roles")
        if (
            type(visible_roles) is not list
            or not visible_roles
            or any(role not in known_roles for role in visible_roles)
        ):
            raise _error("Gemini JSON hierarchy visible result roles are invalid")
        equations.append(
            {
                **canonical_clone_v1(equation),
                "component_role_alternatives": checked_alternatives,
                "maximum_source_rounding_residual_coefficients": maximum_rounding_residual,
            }
        )
        result_roles.add(result)
    available_results: set[str] = set()
    pending = list(equations)
    ordered: list[dict[str, Any]] = []
    while pending:
        progressed = False
        for equation in list(pending):
            dependencies = {
                role
                for alternative in equation["component_role_alternatives"]
                for role in alternative["component_roles"]
                if role in result_roles
            }
            if dependencies <= available_results:
                ordered.append(equation)
                available_results.add(equation["result_role"])
                pending.remove(equation)
                progressed = True
        if not progressed:
            raise _error("Gemini JSON hierarchy equation graph is cyclic")
    component_result_roles = {
        role
        for equation in equations
        for alternative in equation["component_role_alternatives"]
        for role in alternative["component_roles"]
        if role in result_roles
    }
    family_result_roles = result_roles - component_result_roles
    family_result_role = topology["parent"]["role"]
    if family_result_role not in result_roles:
        if len(family_result_roles) != 1:
            raise _error("Gemini JSON hierarchy has no unique family-root equation")
        family_result_role = next(iter(family_result_roles))
    if title_axis_projection_policy is not None:
        equation_by_result = {equation["result_role"]: equation for equation in equations}
        for variant in title_axis_projection_policy["contextual_role_variants"]:
            equation = equation_by_result.get(variant["source_role"])
            if (
                equation is None
                or len(equation["component_role_alternatives"]) != 1
                or set(equation["component_role_alternatives"][0]["component_roles"])
                != set(variant["nested_descendant_roles"])
                or not equation["component_role_alternatives"][0]["variable_component_subset"]
            ):
                raise _error("Gemini JSON contextual role variant equation is invalid")

    schema_fields = {
        "family_id",
        "family_report_norm_id",
        "family_root_mapping_policy",
        "format_version",
        "ignored_roles",
        "role_bindings",
    }
    if type(schema_spec) is dict and schema_spec.get("format_version") in {
        "ACCOUNTING_FAMILY_SCHEMA_BINDING_SPEC_V6",
        "ACCOUNTING_FAMILY_SCHEMA_BINDING_SPEC_V7",
    }:
        schema_fields.add("family_owner_report_norm_id")
    if type(schema_spec) is dict and schema_spec.get("format_version") == (
        "ACCOUNTING_FAMILY_SCHEMA_BINDING_SPEC_V7"
    ):
        schema_fields |= {
            "footnote_narrative_mapping_transforms",
            "source_role_mapping_transforms",
        }
    if type(schema_spec) is dict and schema_spec.get("format_version") == (
        "ACCOUNTING_FAMILY_SCHEMA_BINDING_SPEC_V8"
    ):
        schema_fields.add("presentation_context_bindings")
    if (
        type(schema_spec) is not dict
        or set(schema_spec) != schema_fields
        or schema_spec.get("format_version") not in _SCHEMA_FORMATS
        or schema_spec.get("family_id") != topology["family_id"]
        or type(schema_spec.get("family_report_norm_id")) is not int
        or schema_spec.get("family_root_mapping_policy")
        not in {
            "MAP_WHEN_HIERARCHICALLY_RESOLVED",
            "REQUIRE_HIERARCHICALLY_RESOLVED",
            "REQUIRE_HIERARCHICALLY_RESOLVED_CONTEXT_ONLY",
        }
        or type(schema_spec.get("ignored_roles")) is not list
        or type(schema_spec.get("role_bindings")) is not list
    ):
        raise _error("Gemini JSON hierarchy schema binding spec is invalid")
    bindings: dict[str, int] = {}
    for binding in schema_spec["role_bindings"]:
        if (
            type(binding) is not dict
            or (
                schema_spec["format_version"]
                in {
                    "ACCOUNTING_FAMILY_SCHEMA_BINDING_SPEC_V6",
                    "ACCOUNTING_FAMILY_SCHEMA_BINDING_SPEC_V7",
                }
                and set(binding) != {"parent_report_norm_id", "report_norm_id", "role"}
            )
            or type(binding.get("role")) is not str
            or binding["role"] not in children_by_role
            or binding["role"] in bindings
            or type(binding.get("report_norm_id")) is not int
            or binding["report_norm_id"] <= 0
        ):
            raise _error("Gemini JSON hierarchy role binding is invalid")
        if "parent_report_norm_id" in binding and (
            type(binding["parent_report_norm_id"]) is not int
            or binding["parent_report_norm_id"] <= 0
        ):
            raise _error("Gemini JSON hierarchy binding parent is invalid")
        bindings[binding["role"]] = binding["report_norm_id"]
    ignored = set(schema_spec["ignored_roles"])
    if set(bindings) | ignored != set(children_by_role) or set(bindings) & ignored:
        raise _error("Gemini JSON hierarchy schema frontier is incomplete")

    presentation_context_bindings: list[dict[str, Any]] = []
    if schema_spec["format_version"] == "ACCOUNTING_FAMILY_SCHEMA_BINDING_SPEC_V8":
        raw_contexts = schema_spec["presentation_context_bindings"]
        if type(raw_contexts) is not list or not raw_contexts or len(raw_contexts) > 8:
            raise _error("Gemini JSON presentation-context schema binding axis is invalid")
        contexts = []
        emitted_roles: set[str] = set()
        emitted_ids = set(bindings.values()) | {schema_spec["family_report_norm_id"]}
        context_names: set[str] = set()
        for context in raw_contexts:
            if (
                type(context) is not dict
                or set(context) != {"context", "evidence_roles", "excluded_roles", "role_bindings"}
                or type(context["context"]) is not str
                or not context["context"]
                or context["context"] in context_names
                or type(context["evidence_roles"]) is not list
                or not context["evidence_roles"]
                or len(context["evidence_roles"]) != len(set(context["evidence_roles"]))
                or any(role not in children_by_role for role in context["evidence_roles"])
                or type(context["excluded_roles"]) is not list
                or not context["excluded_roles"]
                or len(context["excluded_roles"]) != len(set(context["excluded_roles"]))
                or any(role not in children_by_role for role in context["excluded_roles"])
                or set(context["evidence_roles"]) & set(context["excluded_roles"])
                or type(context["role_bindings"]) is not list
                or not context["role_bindings"]
                or len(context["role_bindings"]) > 32
            ):
                raise _error("Gemini JSON presentation-context schema binding is invalid")
            parsed_bindings = []
            source_roles: set[str] = set()
            for binding in context["role_bindings"]:
                if (
                    type(binding) is not dict
                    or set(binding) != {"emitted_role", "report_norm_id", "source_role"}
                    or type(binding["emitted_role"]) is not str
                    or not binding["emitted_role"]
                    or binding["emitted_role"] in emitted_roles
                    or type(binding["report_norm_id"]) is not int
                    or binding["report_norm_id"] <= 0
                    or binding["report_norm_id"] in emitted_ids
                    or binding["source_role"] not in children_by_role
                    or binding["source_role"] not in ignored
                    or binding["source_role"] in source_roles
                ):
                    raise _error("Gemini JSON contextual schema role binding is invalid")
                emitted_roles.add(binding["emitted_role"])
                emitted_ids.add(binding["report_norm_id"])
                source_roles.add(binding["source_role"])
                parsed_bindings.append(canonical_clone_v1(binding))
            context_names.add(context["context"])
            contexts.append(
                {
                    "context": context["context"],
                    "evidence_roles": canonical_clone_v1(context["evidence_roles"]),
                    "excluded_roles": canonical_clone_v1(context["excluded_roles"]),
                    "role_bindings": parsed_bindings,
                }
            )
        if any(
            not set(left["evidence_roles"]) <= set(right["excluded_roles"])
            for ordinal, left in enumerate(contexts)
            for right in contexts[ordinal + 1 :]
        ) or any(
            not set(right["evidence_roles"]) <= set(left["excluded_roles"])
            for ordinal, left in enumerate(contexts)
            for right in contexts[ordinal + 1 :]
        ):
            raise _error("Gemini JSON presentation contexts are not mutually exclusive")
        presentation_context_bindings = contexts

    source_role_mapping_transforms: list[dict[str, Any]] = []
    footnote_narrative_mapping_transforms: list[dict[str, Any]] = []
    if schema_spec["format_version"] == "ACCOUNTING_FAMILY_SCHEMA_BINDING_SPEC_V7":
        raw_source_transforms = schema_spec["source_role_mapping_transforms"]
        raw_narrative_transforms = schema_spec["footnote_narrative_mapping_transforms"]
        if (
            type(raw_source_transforms) is not list
            or type(raw_narrative_transforms) is not list
            or len(raw_source_transforms) > 8
            or len(raw_narrative_transforms) > 8
        ):
            raise _error("Gemini JSON hierarchy mapping transform axis is invalid")
        for transform in raw_source_transforms:
            if (
                type(transform) is not dict
                or set(transform)
                != {
                    "emitted_mapping_role",
                    "inclusive_mapping_role",
                    "operation",
                    "source_owner_role",
                    "source_role",
                }
                or transform["operation"]
                != "SUBTRACT_EXACT_NONADDITIVE_SOURCE_FROM_INCLUSIVE_ROLE_AND_EMIT_SOURCE"
                or transform["source_role"] not in children_by_role
                or children_by_role[transform["source_role"]]["role_kind"] != "NONADDITIVE_CHILD"
                or transform["source_owner_role"] not in children_by_role
                or transform["inclusive_mapping_role"] not in bindings
                or transform["emitted_mapping_role"] not in bindings
                or transform["source_role"] == transform["emitted_mapping_role"]
            ):
                raise _error("Gemini JSON hierarchy source-role mapping transform is invalid")
            source_role_mapping_transforms.append(canonical_clone_v1(transform))
        for transform in raw_narrative_transforms:
            if (
                type(transform) is not dict
                or set(transform)
                != {
                    "emitted_mapping_role",
                    "footnote_marker",
                    "operation",
                    "required_ordered_phrases",
                    "unit_aliases",
                }
                or transform["operation"]
                != "ADD_EXACT_TWO_LANE_NARRATIVE_SOURCE_TO_VISIBLE_ROOT_AND_EMIT_SOURCE"
                or transform["emitted_mapping_role"] not in bindings
                or type(transform["footnote_marker"]) is not str
                or not transform["footnote_marker"].strip()
                or type(transform["required_ordered_phrases"]) is not list
                or len(transform["required_ordered_phrases"]) < 2
                or any(
                    type(phrase) is not str or len(_normalized(phrase).split()) < 2
                    for phrase in transform["required_ordered_phrases"]
                )
                or type(transform["unit_aliases"]) is not list
                or not transform["unit_aliases"]
                or any(
                    type(alias) is not str or not _normalized(alias)
                    for alias in transform["unit_aliases"]
                )
            ):
                raise _error("Gemini JSON hierarchy narrative mapping transform is invalid")
            footnote_narrative_mapping_transforms.append(canonical_clone_v1(transform))
        source_emitted_roles = [
            transform["emitted_mapping_role"] for transform in source_role_mapping_transforms
        ]
        narrative_emitted_roles = [
            transform["emitted_mapping_role"] for transform in footnote_narrative_mapping_transforms
        ]
        if len(source_emitted_roles) != len(set(source_emitted_roles)) or len(
            narrative_emitted_roles
        ) != len(set(narrative_emitted_roles)):
            raise _error("Gemini JSON hierarchy mapping transforms emit one role ambiguously")

    aliases_by_role = {
        child["role"]: sorted(
            {alias for matcher in child["matchers"] for alias in matcher["aliases"]}
        )
        for child in topology["children"]
    }
    raw_aliases_by_role = {
        child["role"]: sorted(
            {alias for matcher in child["matchers"] for alias in matcher["aliases"]}
        )
        for child in topology_spec["children"]
    }
    raw_presence_aliases_by_role = {
        child["role"]: sorted(
            {
                alias
                for matcher in child["matchers"]
                if matcher.get("presence_anchor", True)
                for alias in matcher["aliases"]
            }
        )
        for child in topology_spec["children"]
    }
    if set(raw_aliases_by_role) != set(aliases_by_role):
        raise _error("Gemini JSON hierarchy raw query role axis drifted")
    if evaluation_format == "ACCOUNTING_FAMILY_EVALUATION_SPEC_V8" and any(
        not raw_presence_aliases_by_role[role]
        for role in [
            title_axis_projection_policy["structural_branch_role"],
            *title_axis_projection_policy["required_child_roles"],
        ]
    ):
        raise _error("Gemini JSON title-axis query role has no presence aliases")
    anchor_groups = []
    query_anchor_groups = []
    query_anchor_group_role_axes: list[list[str]] = []
    for combination in topology["required_role_combinations"]:
        if len(combination) == 1:
            role = combination[0]
            owners = {
                matcher["within_role"]
                for matcher in children_by_role[role]["matchers"]
                if matcher["within_role"] is not None
            }
            if len(owners) != 1:
                raise _error("Gemini JSON hierarchy single-role anchor has no unique owner")
            owner = next(iter(owners))
            anchor_groups.append([aliases_by_role[owner], aliases_by_role[role]])
            anchor_groups.append([topology["parent"]["aliases"], aliases_by_role[role]])
            query_anchor_groups.append([raw_aliases_by_role[owner], raw_aliases_by_role[role]])
            query_anchor_group_role_axes.append([owner, role])
            query_anchor_groups.append(
                [topology_spec["parent"]["aliases"], raw_aliases_by_role[role]]
            )
            query_anchor_group_role_axes.append([topology["parent"]["role"], role])
            continue
        if len(combination) not in {2, 3}:
            raise _error("Gemini JSON hierarchy anchor combination is invalid")
        anchor_groups.append([aliases_by_role[role] for role in combination])
        raw_children_by_role = {child["role"]: child for child in topology_spec["children"]}
        raw_unscoped_aliases = {
            role: sorted(
                {
                    alias
                    for matcher in raw_children_by_role[role]["matchers"]
                    if matcher["within_role"] is None and matcher.get("presence_anchor", True)
                    for alias in matcher["aliases"]
                }
            )
            for role in combination
        }
        raw_scoped_aliases: dict[str, dict[str, list[str]]] = {}
        for role in combination:
            by_owner: dict[str, set[str]] = defaultdict(set)
            for matcher in raw_children_by_role[role]["matchers"]:
                owner = matcher["within_role"]
                if owner is None or not matcher.get("presence_anchor", True):
                    continue
                by_owner[owner].update(matcher["aliases"])
            raw_scoped_aliases[role] = {
                owner: sorted(aliases) for owner, aliases in by_owner.items()
            }
        common_scoped_owners = set.intersection(
            *(set(raw_scoped_aliases[role]) for role in combination)
        )
        safe_query_groups: list[tuple[list[list[str]], list[str]]] = []
        if all(raw_unscoped_aliases[role] for role in combination):
            safe_query_groups.append(
                ([raw_unscoped_aliases[role] for role in combination], list(combination))
            )
        if len(combination) == 2:
            for owner in sorted(common_scoped_owners):
                owner_aliases = sorted(
                    {
                        alias
                        for matcher in raw_children_by_role[owner]["matchers"]
                        if matcher["within_role"] is None and matcher.get("presence_anchor", True)
                        for alias in matcher["aliases"]
                    }
                )
                if not owner_aliases:
                    continue
                group = [
                    owner_aliases,
                    *(raw_scoped_aliases[role][owner] for role in combination),
                ]
                entry = (group, [owner, *combination])
                if entry not in safe_query_groups:
                    safe_query_groups.append(entry)
        for owner in combination:
            scoped_roles = [role for role in combination if role != owner]
            if not raw_unscoped_aliases[owner] or not all(
                owner in raw_scoped_aliases[role] for role in scoped_roles
            ):
                continue
            group = [
                raw_unscoped_aliases[owner],
                *(raw_scoped_aliases[role][owner] for role in scoped_roles),
            ]
            entry = (group, [owner, *scoped_roles])
            if entry not in safe_query_groups:
                safe_query_groups.append(entry)
        if safe_query_groups:
            # Keep qualified anchors separate from short contextual labels.
            # Contextual query modes include their declared owner as a distinct
            # anchor, so unrelated tables containing the same short pair do not
            # become unresolved family candidates.
            for group, role_axis in safe_query_groups:
                query_anchor_groups.append(group)
                query_anchor_group_role_axes.append(role_axis)
        else:
            query_anchor_groups.append([raw_aliases_by_role[role] for role in combination])
            query_anchor_group_role_axes.append(list(combination))
    raw_query_anchor_groups = canonical_clone_v1(query_anchor_groups)
    raw_query_anchor_group_role_axes = canonical_clone_v1(query_anchor_group_role_axes)
    query_group_compilation_receipt = None
    if evaluation_format == "ACCOUNTING_FAMILY_EVALUATION_SPEC_V8":
        retained_ordinals = []
        subsumed_groups = []

        def strict_subset(left: list[list[str]], right: list[list[str]]) -> bool:
            left_sets = [set(aliases) for aliases in left]
            right_sets = [set(aliases) for aliases in right]
            return all(
                left_set <= right_set
                for left_set, right_set in zip(left_sets, right_sets, strict=True)
            ) and any(
                left_set < right_set
                for left_set, right_set in zip(left_sets, right_sets, strict=True)
            )

        for ordinal, (group, role_axis) in enumerate(
            zip(raw_query_anchor_groups, raw_query_anchor_group_role_axes, strict=True), start=1
        ):
            supersets = [
                other_ordinal
                for other_ordinal, (other, other_role_axis) in enumerate(
                    zip(
                        raw_query_anchor_groups,
                        raw_query_anchor_group_role_axes,
                        strict=True,
                    ),
                    start=1,
                )
                if ordinal != other_ordinal
                and role_axis == other_role_axis
                and len(group) == len(other)
                and strict_subset(group, other)
            ]
            terminal_supersets = [
                candidate
                for candidate in supersets
                if not any(
                    candidate != other
                    and strict_subset(
                        raw_query_anchor_groups[candidate - 1],
                        raw_query_anchor_groups[other - 1],
                    )
                    for other in supersets
                )
            ]
            if terminal_supersets:
                retained = min(terminal_supersets)
                subsumed_groups.append(
                    {
                        "raw_group_ordinal": ordinal,
                        "retained_raw_group_ordinal": retained,
                        "role_axis": role_axis,
                        "rule": "SAME_ROLE_ARITY_LOCATION_STRICT_ALIAS_SUBSET",
                    }
                )
            else:
                retained_ordinals.append(ordinal)
        query_anchor_groups = [
            raw_query_anchor_groups[ordinal - 1] for ordinal in retained_ordinals
        ]
        query_anchor_group_role_axes = [
            raw_query_anchor_group_role_axes[ordinal - 1] for ordinal in retained_ordinals
        ]
        query_group_compilation_receipt = {
            "effective_group_count": len(query_anchor_groups),
            "effective_group_sha256": canonical_json_sha256_v1(
                [
                    {"alias_groups": group, "role_axis": role_axis}
                    for group, role_axis in zip(
                        query_anchor_groups, query_anchor_group_role_axes, strict=True
                    )
                ]
            ),
            "raw_group_count": len(raw_query_anchor_groups),
            "raw_group_sha256": canonical_json_sha256_v1(
                [
                    {"alias_groups": group, "role_axis": role_axis}
                    for group, role_axis in zip(
                        raw_query_anchor_groups,
                        raw_query_anchor_group_role_axes,
                        strict=True,
                    )
                ]
            ),
            "subsumed_groups": subsumed_groups,
        }
    compiled = {
        "aliases_by_role": aliases_by_role,
        "anchor_alias_groups": anchor_groups,
        "bindings": bindings,
        "claim_boundary": CLAIM_BOUNDARY,
        "engine_format_version": FORMAT_VERSION,
        "equations": ordered,
        "evaluation": canonical_clone_v1(evaluation_spec),
        "family_result_role": family_result_role,
        "ignored_roles": sorted(ignored),
        "footnote_narrative_mapping_transforms": footnote_narrative_mapping_transforms,
        "period_table_projection_policy": period_table_projection_policy,
        "presentation_context_bindings": presentation_context_bindings,
        "query_aliases_by_role": canonical_clone_v1(raw_aliases_by_role),
        "query_anchor_alias_groups": canonical_clone_v1(query_anchor_groups),
        "query_parent_aliases": canonical_clone_v1(topology_spec["parent"]["aliases"]),
        "schema": canonical_clone_v1(schema_spec),
        "source_role_mapping_transforms": source_role_mapping_transforms,
        "topology": topology,
    }
    if evaluation_format == "ACCOUNTING_FAMILY_EVALUATION_SPEC_V7":
        compiled["dual_axis_projection_policy"] = dual_axis_projection_policy
    elif evaluation_format == "ACCOUNTING_FAMILY_EVALUATION_SPEC_V8":
        compiled["title_axis_projection_policy"] = title_axis_projection_policy
        compiled["query_anchor_group_role_axes"] = canonical_clone_v1(query_anchor_group_role_axes)
        compiled["query_group_compilation_receipt"] = query_group_compilation_receipt
        compiled["query_presence_aliases_by_role"] = canonical_clone_v1(
            raw_presence_aliases_by_role
        )
        compiled["raw_query_anchor_alias_groups"] = raw_query_anchor_groups
        compiled["raw_query_anchor_group_role_axes"] = raw_query_anchor_group_role_axes
    return compiled


def compile_gemini_json_hierarchical_family_specs_v1(
    topology_spec: Any, evaluation_spec: Any, schema_binding_spec: Any
) -> dict[str, Any]:
    """Compile one V4/V5/V6 accounting family for JSON-only evaluation."""

    return _compile_specs(topology_spec, evaluation_spec, schema_binding_spec)


def _row_role_match_modes(
    row: dict[str, Any],
    *,
    topology: dict[str, Any],
    aliases_by_role: dict[str, list[str]],
    fallback_within_role: str | None = None,
    enable_declared_equivalences: bool = False,
) -> dict[str, str]:
    def self_contained_scope_visible(within_role: str, match_kind: str) -> bool:
        """Admit an exact child label that embeds its structural parent.

        Some source tables flatten a structural carrier and its child into one
        self-contained row instead of emitting a separate hierarchy ancestor.
        This is safe only for an exact child match whose label starts with one
        complete, nontrivial declared parent alias.  Generic child fragments
        such as ``Bằng VND`` therefore cannot claim an unrelated population.
        """

        if not match_kind.startswith("EXACT_NORMALIZED"):
            return False
        label = _normalized(row.get("label_exact"))
        return any(
            len(alias.split()) >= 3 and (label == alias or label.startswith(alias + " "))
            for raw_alias in aliases_by_role[within_role]
            if (alias := _normalized(raw_alias))
        )

    # ``fallback_within_role`` is only a source-order aid for genuinely flat
    # tables.  Once Gemini supplies an explicit parent/structural ancestor in
    # the hierarchy path, that source evidence outranks the last active row.
    # Otherwise a statement-level sibling can be pulled into the preceding
    # branch merely because its label also has a branch-scoped alias.
    explicit_scope_visible = _path_has_role(
        row.get("hierarchy_path_exact"),
        aliases=topology["parent"]["aliases"],
        label_exact=row.get("label_exact"),
    ) or any(
        child["role_kind"] == "STRUCTURAL_GROUP"
        and _path_has_role(
            row.get("hierarchy_path_exact"),
            aliases=aliases_by_role[child["role"]],
            label_exact=row.get("label_exact"),
        )
        for child in topology["children"]
    )

    scoped: dict[str, list[str]] = defaultdict(list)
    unscoped: dict[str, list[str]] = defaultdict(list)
    for child in topology["children"]:
        role = child["role"]
        for matcher in child["matchers"]:
            match_kind = _matcher_match_kind(
                row.get("label_exact"),
                matcher,
                enable_declared_equivalences=enable_declared_equivalences,
            )
            if match_kind is None:
                continue
            within = matcher["within_role"]
            if within is None:
                unscoped[role].append(match_kind)
            elif (
                (within == fallback_within_role and not explicit_scope_visible)
                or _path_has_role(
                    row.get("hierarchy_path_exact"),
                    aliases=aliases_by_role[within],
                    label_exact=row.get("label_exact"),
                )
                or self_contained_scope_visible(within, match_kind)
            ):
                scoped[role].append(match_kind)
    selected = scoped or unscoped
    matches = sorted(selected)
    kinds = {
        role: next(c["role_kind"] for c in topology["children"] if c["role"] == role)
        for role in matches
    }
    # One printed compound row may be both a structural subtotal and its sole
    # typed child.  It is safe only because the equation must corroborate the
    # same values and the root frontier consumes the structural role, not both.
    if len(matches) > 1 and set(kinds.values()) != {"STRUCTURAL_GROUP", "ADDITIVE_CHILD"}:
        raise _error("Gemini JSON hierarchy row matches multiple incompatible roles")
    rank = {
        "CONTAINS_NORMALIZED_PHRASE": 1,
        "CONTAINS_ORDERED_NORMALIZED_PHRASES": 2,
        "EXACT_NORMALIZED": 3,
        "EXACT_NORMALIZED_AFTER_DECORATIVE_PARENTHETICAL_REMOVAL": 2,
        "EXACT_NORMALIZED_SINGLE_MEMBER_ABBREVIATION_EQUIVALENCE": 2,
        "EXACT_NORMALIZED_WITH_TRAILING_ORGANIZATION_QUALIFIER": 2,
    }
    return {role: max(selected[role], key=lambda mode: rank[mode]) for role in matches}


def _row_roles(
    row: dict[str, Any],
    *,
    topology: dict[str, Any],
    aliases_by_role: dict[str, list[str]],
    fallback_within_role: str | None = None,
    enable_declared_equivalences: bool = False,
) -> list[str]:
    return list(
        _row_role_match_modes(
            row,
            topology=topology,
            aliases_by_role=aliases_by_role,
            fallback_within_role=fallback_within_role,
            enable_declared_equivalences=enable_declared_equivalences,
        )
    )


def _nearest_owner(
    row: dict[str, Any],
    *,
    structural_roles: set[str],
    aliases_by_role: dict[str, list[str]],
    own_roles: set[str],
) -> str | None:
    matches: list[tuple[int, int, str]] = []
    for role in structural_roles - own_roles:
        position = _path_role_position(
            row.get("hierarchy_path_exact"),
            aliases=aliases_by_role[role],
            label_exact=row.get("label_exact"),
        )
        if position >= 0:
            matches.append((position, max(map(len, aliases_by_role[role])), role))
    if not matches:
        return None
    nearest = max(position for position, _length, _role in matches)
    longest = max(length for position, length, _role in matches if position == nearest)
    roles = {
        role for position, length, role in matches if position == nearest and length == longest
    }
    if len(roles) != 1:
        raise _error("Gemini JSON hierarchy row owner is ambiguous")
    return next(iter(roles))


def _coefficients(record: Mapping[str, Any]) -> list[int | None]:
    return [observed_source_coefficient_v1(cell) for cell in record["cells"]]


def _sum(records: Sequence[Mapping[str, Any]], lane_count: int) -> list[int | None]:
    output: list[int | None] = []
    for lane in range(lane_count):
        coefficients = [_coefficients(record)[lane] for record in records]
        output.append(
            None
            if any(coefficient is None for coefficient in coefficients)
            else sum(coefficient for coefficient in coefficients if coefficient is not None)
        )
    return output


def _source_lane_receipts(
    record: Mapping[str, Any],
    components: Sequence[Mapping[str, Any]],
    *,
    maximum_rounding_residual: int,
) -> list[dict[str, Any]]:
    return additive_source_lane_receipts_v1(
        result_cells=record["cells"],
        component_cell_vectors=[component["cells"] for component in components],
        maximum_absolute_residual=maximum_rounding_residual,
    )


def _source_rounding_residuals(
    record: Mapping[str, Any],
    components: Sequence[Mapping[str, Any]],
    *,
    maximum_rounding_residual: int,
) -> list[int | None]:
    return [
        receipt["residual"]
        for receipt in _source_lane_receipts(
            record,
            components,
            maximum_rounding_residual=maximum_rounding_residual,
        )
    ]


def _source_equation_matches_on_observed_lanes(
    record: Mapping[str, Any],
    components: Sequence[Mapping[str, Any]],
    *,
    maximum_rounding_residual: int = 0,
) -> bool:
    """Accept proved lanes, ignore incomplete lanes, and veto numeric conflicts."""

    receipts = _source_lane_receipts(
        record,
        components,
        maximum_rounding_residual=maximum_rounding_residual,
    )
    proved = {
        "EXACT_OBSERVED_SOURCE_LANE",
        "BOUNDED_DISPLAY_ROUNDING_SOURCE_LANE",
    }
    return any(receipt["status"] in proved for receipt in receipts) and all(
        receipt["status"] != "SOURCE_LANE_EQUATION_CONFLICT" for receipt in receipts
    )


def _source_equation_is_complete_and_exact(
    record: Mapping[str, Any], components: Sequence[Mapping[str, Any]]
) -> bool:
    """Require every lane to be observed before collapsing a source frontier."""

    receipts = _source_lane_receipts(record, components, maximum_rounding_residual=0)
    return all(receipt["status"] == "EXACT_OBSERVED_SOURCE_LANE" for receipt in receipts)


def _records_match_on_observed_lanes(
    left: Mapping[str, Any], right: Mapping[str, Any]
) -> bool:
    return _source_equation_matches_on_observed_lanes(left, [right])


def _record_has_observed_lane(record: Mapping[str, Any]) -> bool:
    return any(coefficient is not None for coefficient in _coefficients(record))


def _carrier_matches_source_sum(
    record: Mapping[str, Any],
    components: Sequence[Mapping[str, Any]],
    *,
    maximum_rounding_residual: int,
) -> bool:
    return _source_equation_matches_on_observed_lanes(
        record,
        components,
        maximum_rounding_residual=maximum_rounding_residual,
    )


def _solve(
    *,
    base_by_role: dict[str, dict[str, Any]],
    anonymous: list[dict[str, Any]],
    compiled: dict[str, Any],
    ambiguous_provision_target: str | None,
    lane_count: int,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], list[str], set[str]]:
    topology = compiled["topology"]
    family_result_role = compiled["family_result_role"]
    resolved = dict(base_by_role)
    used_anonymous: set[str] = set()
    equations_receipt: list[dict[str, Any]] = []
    reasons: list[str] = []
    # Exact lineage is recorded from the selected equation frontier, never
    # inferred from the union of declarative alternatives.  This lets a later
    # equation replace a proved subtotal's descendants without suppressing a
    # role that belonged only to an unused alternative.
    closed_descendants_by_result_by_lane: dict[str, list[set[str]]] = {}
    deferred_visible_only_frontiers: list[tuple[str, set[str]]] = []
    component_parents: dict[str, set[str]] = defaultdict(set)
    for equation in compiled["equations"]:
        for alternative in equation["component_role_alternatives"]:
            for role in alternative["component_roles"]:
                component_parents[role].add(equation["result_role"])
    component_ancestors: dict[str, set[str]] = {
        role: set(parents) for role, parents in component_parents.items()
    }
    changed = True
    while changed:
        changed = False
        for _role, ancestors in component_ancestors.items():
            transitive = set().union(
                *(component_ancestors.get(ancestor, set()) for ancestor in ancestors)
            )
            if not transitive <= ancestors:
                ancestors.update(transitive)
                changed = True
    if "INTERBANK_PROVISION_AMBIGUOUS" in resolved:
        ambiguous = resolved.pop("INTERBANK_PROVISION_AMBIGUOUS")
        if ambiguous_provision_target is None or ambiguous_provision_target in resolved:
            reasons.append("AMBIGUOUS_PROVISION_HAS_NO_UNIQUE_EQUATION_ROLE")
        else:
            target_parents = component_parents[ambiguous_provision_target]
            source_owner = ambiguous.get("owner_role")
            inferred_owner = (
                source_owner
                if source_owner in target_parents
                else next(iter(target_parents))
                if len(target_parents) == 1
                else None
            )
            resolved[ambiguous_provision_target] = {
                **ambiguous,
                "inferred_from_role": "INTERBANK_PROVISION_AMBIGUOUS",
                "owner_role": inferred_owner,
                "role": ambiguous_provision_target,
            }

    for equation in compiled["equations"]:
        result_role = equation["result_role"]
        maximum_rounding_residual = equation["maximum_source_rounding_residual_coefficients"]

        component_universe = {
            role
            for alternative in equation["component_role_alternatives"]
            for role in alternative["component_roles"]
        }
        regular_component_universe = {
            role
            for alternative in equation["component_role_alternatives"]
            if not alternative["lane_specific_only"]
            for role in alternative["component_roles"]
        }
        lane_direct_visible = set()
        for role in component_universe & set(resolved):
            record = resolved[role]
            if not _record_has_observed_lane(record):
                continue
            owner = record.get("owner_role")
            allowed_parents = component_parents[role]
            if (
                owner is not None
                and owner in resolved
                and owner in allowed_parents
                and owner != result_role
            ):
                continue
            lane_direct_visible.add(role)
        direct_visible = lane_direct_visible & regular_component_universe
        # Consume a proved ancestor only on the lanes where its own equation
        # consumed the descendant.  A source blank neither licenses the
        # collapse nor prevents a visible sister lane from using it.
        collapsed_descendants_by_lane = [
            {
                role: sorted(
                    ancestor
                    for ancestor in direct_visible - {role, result_role}
                    if ancestor in closed_descendants_by_result_by_lane
                    and role in closed_descendants_by_result_by_lane[ancestor][lane]
                )
                for role in direct_visible
            }
            for lane in range(lane_count)
        ]
        collapsed_descendants = {
            role: sorted(
                set().union(
                    *(
                        set(collapsed_descendants_by_lane[lane][role])
                        for lane in range(lane_count)
                        if observed_source_coefficient_v1(resolved[role]["cells"][lane])
                        is not None
                    )
                )
            )
            for role in direct_visible
            if any(
                observed_source_coefficient_v1(resolved[role]["cells"][lane]) is not None
                and bool(collapsed_descendants_by_lane[lane][role])
                for lane in range(lane_count)
            )
        }
        collapsed_descendants = {
            role: ancestors for role, ancestors in collapsed_descendants.items() if ancestors
        }
        direct_visible -= set(collapsed_descendants)
        role_kinds = {child["role"]: child["role_kind"] for child in topology["children"]}
        for total_role in sorted(
            role for role in direct_visible if role_kinds.get(role) == "TOTAL"
        ):
            cooccurring = {
                role
                for alternative in equation["component_role_alternatives"]
                if total_role in alternative["component_roles"]
                for role in alternative["component_roles"]
            }
            subtotal_components = sorted(
                (
                    resolved[role]
                    for role in direct_visible - cooccurring - {total_role}
                    if role_kinds.get(role) in {"ADDITIVE_CHILD", "STRUCTURAL_GROUP"}
                ),
                key=lambda record: (record["ordinal"], record["role"], record["row_id"]),
            )
            if subtotal_components and _source_equation_is_complete_and_exact(
                resolved[total_role], subtotal_components
            ):
                equations_receipt.append(
                    {
                        "component_roles": [record["role"] for record in subtotal_components],
                        "component_row_ids": [record["row_id"] for record in subtotal_components],
                        "lane_component_sums": _coefficients(resolved[total_role]),
                        "mode": "VISIBLE_TOTAL_EXACTLY_CORROBORATED_BY_DIRECT_COMPONENTS",
                        "result_coefficients": _coefficients(resolved[total_role]),
                        "result_role": total_role,
                        "result_row_id": resolved[total_role]["row_id"],
                    }
                )
                direct_visible -= {record["role"] for record in subtotal_components}
        existing = resolved.get(result_role)
        declared_result_carriers: dict[str, dict[str, Any]] = {}
        if existing is not None:
            declared_result_carriers[existing["row_id"]] = existing
        for visible_role in set(equation["visible_result_roles"]) - {result_role}:
            visible = resolved.get(visible_role)
            if visible is not None:
                declared_result_carriers[visible["row_id"]] = visible
        for record in anonymous:
            if record.get("owner_role") == result_role or result_role in record.get(
                "allowed_result_roles", set()
            ):
                declared_result_carriers[record["row_id"]] = record
        if not direct_visible:
            if existing is not None:
                equations_receipt.append(
                    {
                        "component_roles": [],
                        "mode": "VISIBLE_SOURCE_ONLY_NO_DECLARED_COMPONENT_VISIBLE",
                        "result_coefficients": _coefficients(existing),
                        "result_role": result_role,
                        "result_row_id": existing["row_id"],
                    }
                )
            continue
        eligible = []
        for alternative in equation["component_role_alternatives"]:
            if alternative["lane_specific_only"]:
                continue
            declared = set(alternative["component_roles"])
            if alternative["variable_component_subset"]:
                selected_declared = direct_visible & declared
                matches = (
                    len(selected_declared) >= alternative["minimum_component_count"]
                    and sum(role_kinds.get(role) == "ADDITIVE_CHILD" for role in selected_declared)
                    >= alternative["minimum_additive_child_count"]
                )
            elif alternative["coverage_policy"] == "EXHAUSTIVE_COMPONENT_SET":
                matches = declared == direct_visible
            else:
                matches = (
                    direct_visible <= declared
                    and len(direct_visible) >= alternative["minimum_component_count"]
                )
            if matches:
                eligible.append(alternative)
        if not eligible and not declared_result_carriers:
            reasons.append(f"NO_EXHAUSTIVE_DIRECT_FRONTIER:{result_role}")
            continue
        alternatives = []
        for alternative in eligible:
            selected_roles = [
                role for role in alternative["component_roles"] if role in direct_visible
            ]
            components = [resolved[role] for role in selected_roles]
            sums = _sum(components, lane_count)
            carriers: list[dict[str, Any]] = []
            authoritative_visible = False
            if existing is not None and _carrier_matches_source_sum(
                existing,
                components,
                maximum_rounding_residual=maximum_rounding_residual,
            ):
                carriers.append(existing)
            if existing is not None:
                authoritative_visible = True
            visible_roles = set(equation["visible_result_roles"])
            for role in visible_roles - {result_role}:
                record = resolved.get(role)
                if record is not None and _carrier_matches_source_sum(
                    record,
                    components,
                    maximum_rounding_residual=maximum_rounding_residual,
                ):
                    carriers.append(record)
                if record is not None:
                    authoritative_visible = True
            maximum_component_ordinal = max(component["ordinal"] for component in components)
            for record in anonymous:
                if (
                    record.get("owner_role") == result_role and "allowed_result_roles" not in record
                ) or result_role in record.get("authoritative_result_roles", set()):
                    authoritative_visible = True
                if (
                    (
                        record["row_id"] not in used_anonymous
                        or result_role in record.get("trailing_population_carrier_for_roles", set())
                    )
                    and not (
                        compiled["evaluation"]["format_version"]
                        in {
                            "ACCOUNTING_FAMILY_EVALUATION_SPEC_V5",
                            "ACCOUNTING_FAMILY_EVALUATION_SPEC_V6",
                            "ACCOUNTING_FAMILY_EVALUATION_SPEC_V7",
                            "ACCOUNTING_FAMILY_EVALUATION_SPEC_V8",
                        }
                        and record.get("owner_role") == topology["parent"]["role"]
                        and result_role != family_result_role
                        and "allowed_result_roles" not in record
                    )
                    and (
                        record["ordinal"] > maximum_component_ordinal
                        or record.get("presentation_shadow_for_role") == result_role
                        or record.get("leading_parent_carrier_for_role") == result_role
                        or result_role in record.get("trailing_population_carrier_for_roles", set())
                    )
                    and _carrier_matches_source_sum(
                        record,
                        components,
                        maximum_rounding_residual=maximum_rounding_residual,
                    )
                    and result_role in record.get("allowed_result_roles", {result_role})
                    and record.get("owner_role") in {None, result_role, topology["parent"]["role"]}
                ):
                    carriers.append(record)
            unique_carriers = {carrier["row_id"]: carrier for carrier in carriers}
            if existing is not None and existing["row_id"] in unique_carriers:
                corroborating = [
                    record
                    for row_id, record in unique_carriers.items()
                    if row_id != existing["row_id"]
                    and record.get("owner_role") == result_role
                    and _records_match_on_observed_lanes(record, existing)
                ]
                if len(corroborating) == len(unique_carriers) - 1 == 1:
                    unique_carriers = {
                        existing["row_id"]: {
                            **existing,
                            "corroborating_result_row_ids": [corroborating[0]["row_id"]],
                        }
                    }
            if len(unique_carriers) == 1:
                alternatives.append(
                    (alternative, components, sums, next(iter(unique_carriers.values())))
                )
            elif (
                not unique_carriers
                and not authoritative_visible
                and any(coefficient is not None for coefficient in sums)
                and alternative["derivation_policy"]
                == "ALLOW_DERIVATION_FROM_EXHAUSTIVE_VISIBLE_COMPONENTS"
            ):
                alternatives.append((alternative, components, sums, None))
        alternatives_by_frontier = {}
        for alternative, components, sums, carrier in alternatives:
            key = (
                tuple(record["role"] for record in components),
                tuple(record["row_id"] for record in components),
                carrier["row_id"] if carrier is not None else None,
                tuple(sums),
            )
            alternatives_by_frontier[key] = (alternative, components, sums, carrier)
        alternatives = list(alternatives_by_frontier.values())
        equivalent_presentation_frontiers: list[list[str]] = []
        if len(alternatives) > 1:
            signatures = {
                (
                    tuple(sums),
                    carrier["row_id"] if carrier is not None else None,
                )
                for _alternative, _components, sums, carrier in alternatives
            }
            role_sets = [
                {record["role"] for record in components}
                for _alternative, components, _sums, _carrier in alternatives
            ]

            def structurally_covers(left: set[str], right: set[str]) -> bool:
                return all(
                    role in left or bool(left & component_ancestors.get(role, set()))
                    for role in right
                )

            maximum_frontiers = [
                index
                for index, roles in enumerate(role_sets)
                if all(
                    index == other or structurally_covers(roles, other_roles)
                    for other, other_roles in enumerate(role_sets)
                )
                and any(
                    not structurally_covers(other_roles, roles)
                    for other, other_roles in enumerate(role_sets)
                    if index != other
                )
            ]
            if len(maximum_frontiers) == 1:
                alternatives = [alternatives[maximum_frontiers[0]]]
                role_sets = [role_sets[maximum_frontiers[0]]]
            if (
                len(alternatives) > 1
                and len(signatures) == 1
                and all(
                    not roles & other_roles
                    for index, roles in enumerate(role_sets)
                    for other_roles in role_sets[index + 1 :]
                )
            ):
                equivalent_presentation_frontiers = [
                    [record["role"] for record in components]
                    for _alternative, components, _sums, _carrier in alternatives
                ]
                alternatives = alternatives[:1]
        lane_specific_frontiers: list[
            tuple[list[str], list[dict[str, Any]]] | None
        ] = [None for _lane in range(lane_count)]
        lane_specific_conflict = False
        lane_carrier = (
            next(iter(declared_result_carriers.values()))
            if len(declared_result_carriers) == 1
            else None
        )
        if len(alternatives) != 1 and lane_carrier is not None:
            for lane in range(lane_count):
                carrier_coefficient = observed_source_coefficient_v1(
                    lane_carrier["cells"][lane]
                )
                if carrier_coefficient is None:
                    continue
                candidate_axes = []
                for collapse_proved_descendants in (True, False):
                    lane_candidates = {}
                    lane_has_complete_frontier = False
                    for alternative in equation["component_role_alternatives"]:
                        declared = set(alternative["component_roles"])
                        lane_roles = [
                            role
                            for role in alternative["component_roles"]
                            if role in lane_direct_visible
                            and (
                                not collapse_proved_descendants
                                or not collapsed_descendants_by_lane[lane].get(role)
                            )
                        ]
                        if (
                            len(lane_roles) < alternative["minimum_component_count"]
                            or sum(
                                role_kinds.get(role) == "ADDITIVE_CHILD"
                                for role in lane_roles
                            )
                            < alternative["minimum_additive_child_count"]
                            or not set(lane_roles) <= declared
                        ):
                            continue
                        lane_components = [resolved[role] for role in lane_roles]
                        if any(
                            observed_source_coefficient_v1(component["cells"][lane]) is None
                            for component in lane_components
                        ):
                            continue
                        if (
                            lane_carrier not in base_by_role.values()
                            and lane_components
                            and lane_carrier["ordinal"]
                            <= max(component["ordinal"] for component in lane_components)
                        ):
                            continue
                        lane_has_complete_frontier = True
                        component_sum = sum(
                            observed_source_coefficient_v1(component["cells"][lane])
                            for component in lane_components
                        )
                        if component_sum != carrier_coefficient:
                            continue
                        key = (
                            tuple(lane_roles),
                            tuple(component["row_id"] for component in lane_components),
                        )
                        lane_candidates[key] = (lane_roles, lane_components)
                    candidate_axes.append(
                        (lane_candidates, lane_has_complete_frontier)
                    )
                preferred_candidates, preferred_complete = candidate_axes[0]
                fallback_candidates, fallback_complete = candidate_axes[1]
                if len(preferred_candidates) == 1:
                    lane_specific_frontiers[lane] = next(
                        iter(preferred_candidates.values())
                    )
                    continue
                if not preferred_candidates and len(fallback_candidates) == 1:
                    # Retain an arithmetically exact but lineage-reusing
                    # frontier so the lane-use audit emits the explicit
                    # double-consumption veto instead of hiding it as a
                    # generic solution-count failure.
                    lane_specific_frontiers[lane] = next(
                        iter(fallback_candidates.values())
                    )
                    continue
                if not (preferred_complete or fallback_complete):
                    continue
                if len(preferred_candidates) != 1:
                    lane_specific_conflict = True
                    break
        if not lane_specific_conflict and any(
            frontier is not None for frontier in lane_specific_frontiers
        ):
            selected_roles_by_lane = [
                roles if frontier is not None else []
                for frontier in lane_specific_frontiers
                for roles in ([frontier[0]] if frontier is not None else [[]])
            ]
            components_by_lane = [
                components if frontier is not None else []
                for frontier in lane_specific_frontiers
                for components in ([frontier[1]] if frontier is not None else [[]])
            ]
            resolved[result_role] = {**lane_carrier, "owner_role": None, "role": result_role}
            if lane_carrier["row_id"].startswith("r") and lane_carrier not in base_by_role.values():
                used_anonymous.add(lane_carrier["row_id"])
            equations_receipt.append(
                {
                    "component_roles": sorted(
                        set().union(*(set(roles) for roles in selected_roles_by_lane))
                    ),
                    "component_roles_by_lane": selected_roles_by_lane,
                    "component_row_ids_by_lane": [
                        [component["row_id"] for component in components]
                        for components in components_by_lane
                    ],
                    "lane_component_sums": [
                        (
                            sum(
                                observed_source_coefficient_v1(
                                    component["cells"][lane]
                                )
                                for component in components
                            )
                            if components
                            else None
                        )
                        for lane, components in enumerate(components_by_lane)
                    ],
                    "mode": (
                        "VISIBLE_RESULT_EXACTLY_CORROBORATED_BY_LANE_SPECIFIC_FRONTIERS"
                        if all(frontier is not None for frontier in lane_specific_frontiers)
                        else "VISIBLE_RESULT_CORROBORATED_BY_PARTIAL_LANE_SPECIFIC_FRONTIERS"
                    ),
                    "result_coefficients": _coefficients(lane_carrier),
                    "result_role": result_role,
                    "result_row_id": lane_carrier["row_id"],
                }
            )
            lineage_by_lane = []
            for lane, selected_roles in enumerate(selected_roles_by_lane):
                descendants = set(selected_roles)
                for role in selected_roles:
                    prior = closed_descendants_by_result_by_lane.get(role)
                    if prior is not None:
                        descendants.update(prior[lane])
                lineage_by_lane.append(descendants)
            closed_descendants_by_result_by_lane[result_role] = lineage_by_lane
            continue
        if len(alternatives) != 1:
            result_is_visibly_declared = existing is not None or any(
                record.get("owner_role") == result_role for record in anonymous
            )
            if not eligible:
                reasons.append(f"NO_EXHAUSTIVE_DIRECT_FRONTIER:{result_role}")
            elif (
                not alternatives
                and not result_is_visibly_declared
                and eligible
                and all(
                    alternative["derivation_policy"] == "VISIBLE_RESULT_CORROBORATION_ONLY"
                    for alternative in eligible
                )
            ):
                deferred_visible_only_frontiers.append((result_role, direct_visible))
            else:
                reasons.append(
                    f"EXACT_DIRECT_FRONTIER_SOLUTION_COUNT_NOT_ONE:{result_role}:{len(alternatives)}"
                )
            continue
        alternative, components, sums, carrier = alternatives[0]
        selected_roles = [component["role"] for component in components]
        if carrier is None:
            source_rounding_residuals: list[int | None] = []
            lane_statuses = [
                (
                    "DERIVED_EXACT_OBSERVED_COMPONENT_LANE"
                    if coefficient is not None
                    else "COMPONENT_SOURCE_LANE_UNOBSERVED"
                )
                for coefficient in sums
            ]
            result = {
                "cells": [
                    {
                        "coefficient": coefficient,
                        "source_text": None,
                        "state": (
                            "DERIVED_EXACT_RECURSIVE_DIRECT_FRONTIER"
                            if coefficient is not None
                            else "DERIVED_INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL"
                        ),
                    }
                    for coefficient in sums
                ],
                "derived_from_roles": selected_roles,
                "derived_from_row_ids": [component["row_id"] for component in components],
                "label_exact": result_role,
                "ordinal": max(component["ordinal"] for component in components),
                "owner_role": None,
                "path": [],
                "role": result_role,
                "row_id": "derived:" + result_role,
            }
            mode = (
                "DERIVED_FROM_EXHAUSTIVE_VISIBLE_COMPONENTS"
                if all(coefficient is not None for coefficient in sums)
                else "DERIVED_FROM_EXHAUSTIVE_VISIBLE_COMPONENTS_ON_COMPLETE_SOURCE_LANES"
            )
        else:
            result = {**carrier, "owner_role": None, "role": result_role}
            lane_receipts = _source_lane_receipts(
                carrier,
                components,
                maximum_rounding_residual=maximum_rounding_residual,
            )
            lane_statuses = [receipt["status"] for receipt in lane_receipts]
            source_rounding_residuals = [receipt["residual"] for receipt in lane_receipts]
            if carrier["row_id"].startswith("r") and carrier not in base_by_role.values():
                used_anonymous.add(carrier["row_id"])
            used_anonymous.update(result.get("corroborating_result_row_ids", []))
            mode = (
                "VISIBLE_RESULT_CORROBORATED_ON_OBSERVED_LANES_WITH_INCOMPLETE_SOURCE_LANE"
                if any("UNOBSERVED" in status for status in lane_statuses)
                else "VISIBLE_RESULT_EXACTLY_CORROBORATED"
                if not any(source_rounding_residuals)
                else "VISIBLE_RESULT_CORROBORATED_WITH_BOUNDED_SOURCE_ROUNDING_RESIDUAL"
            )
        proved_lanes = {
            lane
            for lane, status in enumerate(lane_statuses)
            if status
            in {
                "DERIVED_EXACT_OBSERVED_COMPONENT_LANE",
                "EXACT_OBSERVED_SOURCE_LANE",
                "BOUNDED_DISPLAY_ROUNDING_SOURCE_LANE",
            }
        }
        incomplete_lanes = set(range(lane_count)) - proved_lanes
        resolved[result_role] = result
        equations_receipt.append(
            {
                "component_roles": selected_roles,
                "component_row_ids": [component["row_id"] for component in components],
                **(
                    {
                        "component_roles_by_lane": [
                            selected_roles if lane in proved_lanes else []
                            for lane in range(lane_count)
                        ],
                        "source_lane_equation_statuses": lane_statuses,
                    }
                    if incomplete_lanes
                    else {}
                ),
                "lane_component_sums": sums,
                "mode": mode,
                "result_coefficients": _coefficients(result),
                "result_role": result_role,
                "result_row_id": result["row_id"],
                **(
                    {"source_rounding_residual_coefficients": source_rounding_residuals}
                    if any(
                        residual is not None and residual != 0
                        for residual in source_rounding_residuals
                    )
                    else {}
                ),
                **(
                    {"equivalent_presentation_frontiers": equivalent_presentation_frontiers}
                    if equivalent_presentation_frontiers
                    else {}
                ),
                **(
                    {"corroborating_result_row_ids": result["corroborating_result_row_ids"]}
                    if "corroborating_result_row_ids" in result
                    else {}
                ),
                **(
                    {
                        "collapsed_descendant_roles": sorted(collapsed_descendants),
                        "collapsed_descendant_row_ids": [
                            resolved[role]["row_id"] for role in sorted(collapsed_descendants)
                        ],
                        "collapsed_to_verified_ancestor_roles": {
                            role: collapsed_descendants[role]
                            for role in sorted(collapsed_descendants)
                        },
                    }
                    if collapsed_descendants
                    else {}
                ),
            }
        )
        lineage_by_lane = []
        for lane in range(lane_count):
            descendants = set(selected_roles) if lane in proved_lanes else set()
            if lane in proved_lanes:
                for role in selected_roles:
                    prior = closed_descendants_by_result_by_lane.get(role)
                    if prior is not None:
                        descendants.update(prior[lane])
            lineage_by_lane.append(descendants)
        closed_descendants_by_result_by_lane[result_role] = lineage_by_lane
    if ambiguous_provision_target is not None:
        use_count = sum(
            ambiguous_provision_target in receipt.get("component_roles", [])
            for receipt in equations_receipt
        )
        if use_count != 1:
            reasons.append(f"INFERRED_AMBIGUOUS_PROVISION_USE_COUNT_NOT_ONE:{use_count}")
    component_use_counts = {
        role: sum(role in receipt.get("component_roles", []) for receipt in equations_receipt)
        for _result_role, roles in deferred_visible_only_frontiers
        for role in roles
    }
    for result_role, roles in deferred_visible_only_frontiers:
        if any(component_use_counts[role] != 1 for role in roles):
            reasons.append(f"UNRESOLVED_VISIBLE_ONLY_FRONTIER:{result_role}")
    lane_use_counts: dict[tuple[str, int], int] = defaultdict(int)
    for receipt in equations_receipt:
        roles_by_lane = receipt.get("component_roles_by_lane")
        if roles_by_lane is None:
            roles_by_lane = [receipt.get("component_roles", []) for _lane in range(lane_count)]
        for lane, roles in enumerate(roles_by_lane):
            for role in roles:
                lane_use_counts[(role, lane)] += 1
    for (role, lane), use_count in sorted(lane_use_counts.items()):
        if use_count > 1:
            reasons.append(f"COMPONENT_ROLE_LANE_USE_COUNT_ABOVE_ONE:{role}:{lane}:{use_count}")
    if family_result_role not in resolved:
        reasons.append("FAMILY_ROOT_IS_NOT_HIERARCHICALLY_RESOLVED")
    return resolved, equations_receipt, reasons, used_anonymous


def _legacy_intermediate_parent_subtotal_receipts(
    *,
    candidates: list[dict[str, Any]],
    records_by_role: dict[str, list[dict[str, Any]]],
    anonymous: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
    topology: dict[str, Any],
    unmatched_numeric_ordinals: set[int],
    lane_count: int,
) -> list[dict[str, Any]]:
    """Preserve the V1--V7 intermediate-parent receipt byte contract."""

    if len(candidates) != 1:
        return []
    candidate = candidates[0]
    parent_role = topology["parent"]["role"]
    role_kinds = {child["role"]: child["role_kind"] for child in topology["children"]}
    records_by_ordinal: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for role_records in records_by_role.values():
        for record in role_records:
            records_by_ordinal[record["ordinal"]].append(record)
    boundary = None
    for ordinal in range(candidate["ordinal"] + 1, len(source_rows) + 1):
        row = source_rows[ordinal - 1]
        ordinal_records = records_by_ordinal.get(ordinal, [])
        if row.get("row_kind") == "GROUP" and any(
            role_kinds.get(record["role"]) == "STRUCTURAL_GROUP" for record in ordinal_records
        ):
            boundary = ordinal
            break
    if boundary is None or not any(
        record["ordinal"] > boundary
        and (
            parent_role in record.get("authoritative_result_roles", set())
            or (
                record.get("owner_role") == parent_role
                and source_rows[record["ordinal"] - 1].get("row_kind") == "TOTAL"
                and _is_generic_total_label(source_rows[record["ordinal"] - 1].get("label_exact"))
            )
        )
        for record in anonymous
    ):
        return []
    components: list[dict[str, Any]] = []
    nested_nonadditive: list[dict[str, Any]] = []
    for ordinal in range(candidate["ordinal"] + 1, boundary):
        if ordinal in unmatched_numeric_ordinals:
            return []
        source_row = source_rows[ordinal - 1]
        ordinal_records = records_by_ordinal.get(ordinal, [])
        direct = [
            record
            for record in ordinal_records
            if role_kinds.get(record["role"]) in {"ADDITIVE_CHILD", "STRUCTURAL_GROUP"}
            and record.get("owner_role") == parent_role
        ]
        nonadditive = [
            record
            for record in ordinal_records
            if role_kinds.get(record["role"]) == "NONADDITIVE_CHILD"
        ]
        if len(direct) > 1 or (ordinal_records and not direct and not nonadditive):
            return []
        if not ordinal_records and (
            source_row.get("row_kind") == "GROUP" or _normalized(source_row.get("label_exact"))
        ):
            return []
        if direct:
            components.append(direct[0])
        nested_nonadditive.extend(nonadditive)
    component_roles = [record["role"] for record in components]
    if (
        len(components) < 2
        or len(component_roles) != len(set(component_roles))
        or any(record.get("owner_role") not in component_roles for record in nested_nonadditive)
        or not _source_equation_matches_on_observed_lanes(candidate, components)
    ):
        return []
    return [
        {
            "component_roles": component_roles,
            "component_row_ids": [record["row_id"] for record in components],
            "lane_component_sums": _sum(components, lane_count),
            "mode": "VISIBLE_INTERMEDIATE_PARENT_SUBTOTAL_EXACTLY_CORROBORATED_BY_CONTIGUOUS_DIRECT_CHILDREN",
            "result_coefficients": _coefficients(candidate),
            "result_role": parent_role,
            "result_row_id": candidate["row_id"],
            "source_interval_ordinals": [candidate["ordinal"], boundary - 1],
        }
    ]


def _exact_peer_population_fence_receipt(
    *,
    boundary_ordinal: int,
    boundary_role: str,
    carrier: dict[str, Any],
    records_by_role: Mapping[str, list[dict[str, Any]]],
    anonymous: Sequence[dict[str, Any]],
    source_rows: Sequence[Mapping[str, Any]],
    compiled: Mapping[str, Any],
    unmatched_numeric_ordinals: set[int],
    lane_count: int,
) -> dict[str, Any] | None:
    """Prove an excluded peer subtotal and later total, rather than decorate a fence."""

    peer_records = [
        record
        for record in records_by_role.get(boundary_role, [])
        if record["ordinal"] == boundary_ordinal
    ]
    peer_equations = [
        equation for equation in compiled["equations"] if equation["result_role"] == boundary_role
    ]
    later_total_ordinals = [
        ordinal
        for ordinal in range(boundary_ordinal + 1, len(source_rows) + 1)
        if source_rows[ordinal - 1].get("row_kind") == "TOTAL"
    ]
    if len(peer_records) != 1 or len(peer_equations) != 1 or len(later_total_ordinals) != 1:
        return None
    peer = peer_records[0]
    total_ordinal = later_total_ordinals[0]
    total_records = [
        record
        for record in anonymous
        if record["ordinal"] == total_ordinal and record["row_id"] == f"r{total_ordinal}"
    ]
    if len(total_records) != 1:
        return None
    total = total_records[0]
    post_total_numeric_ordinals = [
        ordinal
        for ordinal in range(total_ordinal + 1, len(source_rows) + 1)
        if type(source_rows[ordinal - 1].get("values_exact")) is list
        and any(value is not None for value in source_rows[ordinal - 1]["values_exact"])
    ]
    if post_total_numeric_ordinals or not _source_equation_matches_on_observed_lanes(
        total, [carrier, peer]
    ):
        return None

    equation = peer_equations[0]
    solutions: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    for alternative in equation["component_role_alternatives"]:
        components = []
        valid = True
        for role in alternative["component_roles"]:
            occurrences = [
                record
                for record in records_by_role.get(role, [])
                if boundary_ordinal < record["ordinal"] < total_ordinal
                and record.get("owner_role") == boundary_role
            ]
            if len(occurrences) != 1:
                valid = False
                break
            components.append(occurrences[0])
        if not valid:
            continue
        selected_roles = {record["role"] for record in components}
        declared_roles = set(alternative["component_roles"])
        if (
            len(selected_roles) < alternative["minimum_component_count"]
            or sum(
                next(
                    child["role_kind"]
                    for child in compiled["topology"]["children"]
                    if child["role"] == role
                )
                == "ADDITIVE_CHILD"
                for role in selected_roles
            )
            < alternative["minimum_additive_child_count"]
            or (not alternative["variable_component_subset"] and selected_roles != declared_roles)
            or not _source_equation_matches_on_observed_lanes(peer, components)
        ):
            continue
        component_ordinals = {record["ordinal"] for record in components}
        interval_numeric_ordinals = {
            ordinal
            for ordinal in range(boundary_ordinal + 1, total_ordinal)
            if type(source_rows[ordinal - 1].get("values_exact")) is list
            and any(value is not None for value in source_rows[ordinal - 1]["values_exact"])
        }
        if (
            interval_numeric_ordinals != component_ordinals
            or interval_numeric_ordinals & unmatched_numeric_ordinals
        ):
            continue
        solutions.append((alternative, components))
    if len(solutions) != 1:
        return None
    alternative, components = solutions[0]
    return {
        "component_roles": [record["role"] for record in components],
        "component_row_ids": [record["row_id"] for record in components],
        "later_total_coefficients": _coefficients(total),
        "later_total_row_id": total["row_id"],
        "peer_coefficients": _coefficients(peer),
        "peer_result_role": boundary_role,
        "peer_result_row_id": peer["row_id"],
        "peer_source_interval_ordinals": [boundary_ordinal, total_ordinal - 1],
        "post_total_numeric_ordinals": post_total_numeric_ordinals,
        "rule": "EXACT_DECLARED_PEER_EQUATION_AND_LATER_TOTAL_EQUALS_CARRIER_PLUS_PEER",
        "selected_alternative_component_roles": alternative["component_roles"],
    }


def _leading_parent_population_boundary_receipts(
    *,
    candidates: list[dict[str, Any]],
    records_by_role: dict[str, list[dict[str, Any]]],
    anonymous: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
    compiled: dict[str, Any],
    unmatched_numeric_ordinals: set[int],
    lane_count: int,
) -> tuple[list[dict[str, Any]], set[int]]:
    """Prove one leading parent carrier and fence any peer population.

    This is carrier eligibility and accounting-population evidence, not an
    equation.  The recursive solver remains the sole consumer of the direct
    children (children -> intermediate subtotal -> family root), so no source
    row can be consumed twice outside its lane-use audit.
    """

    if len(candidates) != 1:
        return [], set()
    candidate = candidates[0]
    topology = compiled["topology"]
    parent_role = topology["parent"]["role"]
    role_kinds = {child["role"]: child["role_kind"] for child in topology["children"]}
    family_result_role = compiled["family_result_role"]
    components_by_result = {
        equation["result_role"]: {
            role
            for alternative in equation["component_role_alternatives"]
            for role in alternative["component_roles"]
        }
        for equation in compiled["equations"]
    }
    family_population_roles = {family_result_role}
    frontier = [family_result_role]
    while frontier:
        result_role = frontier.pop()
        for component_role in components_by_result.get(result_role, set()):
            if component_role not in family_population_roles:
                family_population_roles.add(component_role)
                frontier.append(component_role)
    records_by_ordinal: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for role_records in records_by_role.values():
        for record in role_records:
            records_by_ordinal[record["ordinal"]].append(record)

    boundary = None
    boundary_record = None
    for ordinal in range(candidate["ordinal"] + 1, len(source_rows) + 1):
        row = source_rows[ordinal - 1]
        ordinal_records = records_by_ordinal.get(ordinal, [])
        raw_role_modes = _row_role_match_modes(
            row,
            topology=topology,
            aliases_by_role=compiled["aliases_by_role"],
            fallback_within_role=None,
            enable_declared_equivalences=True,
        )
        raw_peer_roles = sorted(
            role
            for role in raw_role_modes
            if role_kinds.get(role) == "STRUCTURAL_GROUP" and role not in family_population_roles
        )
        peer_records = [
            record
            for record in ordinal_records
            if role_kinds.get(record["role"]) == "STRUCTURAL_GROUP"
            and record["role"] not in family_population_roles
        ]
        if (
            row.get("row_kind") in {"GROUP", "SUBTOTAL", "ITEM"}
            and len(raw_peer_roles) == 1
            and len(peer_records) <= 1
        ):
            boundary = ordinal
            boundary_record = (
                peer_records[0]
                if peer_records
                else {
                    "label_exact": row.get("label_exact"),
                    "ordinal": ordinal,
                    "role": raw_peer_roles[0],
                    "row_id": f"r{ordinal}",
                }
            )
            break
    population_end = boundary - 1 if boundary is not None else len(source_rows)

    components: list[dict[str, Any]] = []
    nested_nonadditive: list[dict[str, Any]] = []
    for ordinal in range(candidate["ordinal"] + 1, population_end + 1):
        if ordinal in unmatched_numeric_ordinals:
            return [], set()
        source_row = source_rows[ordinal - 1]
        ordinal_records = records_by_ordinal.get(ordinal, [])
        direct = [
            record
            for record in ordinal_records
            if role_kinds.get(record["role"]) in {"ADDITIVE_CHILD", "STRUCTURAL_GROUP"}
            and record.get("owner_role") == parent_role
        ]
        nonadditive = [
            record
            for record in ordinal_records
            if role_kinds.get(record["role"]) == "NONADDITIVE_CHILD"
        ]
        if len(direct) > 1 or (ordinal_records and not direct and not nonadditive):
            return [], set()
        if not ordinal_records and (
            source_row.get("row_kind") == "GROUP" or _normalized(source_row.get("label_exact"))
        ):
            return [], set()
        if direct:
            components.append(direct[0])
        nested_nonadditive.extend(nonadditive)
    component_roles = [record["role"] for record in components]
    if (
        len(components) < 2
        or len(component_roles) != len(set(component_roles))
        or any(record.get("owner_role") not in component_roles for record in nested_nonadditive)
        or not _source_equation_matches_on_observed_lanes(candidate, components)
    ):
        return [], set()
    excluded_ordinals = (
        set(range(boundary, len(source_rows) + 1)) if boundary is not None else set()
    )
    boundary_descendant_ordinals: list[int] = []
    later_total_ordinals: list[int] = []
    peer_fence_receipt = None
    if boundary is not None:
        boundary_label = _normalized(source_rows[boundary - 1].get("label_exact"))
        boundary_descendant_ordinals = [
            ordinal
            for ordinal in range(boundary + 1, len(source_rows) + 1)
            if boundary_label
            in {
                _normalized(value)
                for value in source_rows[ordinal - 1].get("hierarchy_path_exact", [])
                if _normalized(value)
            }
        ]
        later_total_ordinals = [
            ordinal
            for ordinal in range(boundary + 1, len(source_rows) + 1)
            if source_rows[ordinal - 1].get("row_kind") == "TOTAL"
        ]
        if (
            not boundary_label
            or not boundary_descendant_ordinals
            or len(later_total_ordinals) != 1
            or any(ordinal in unmatched_numeric_ordinals for ordinal in excluded_ordinals)
        ):
            return [], set()
        peer_fence_receipt = _exact_peer_population_fence_receipt(
            boundary_ordinal=boundary,
            boundary_role=boundary_record["role"],
            carrier=candidate,
            records_by_role=records_by_role,
            anonymous=anonymous,
            source_rows=source_rows,
            compiled=compiled,
            unmatched_numeric_ordinals=unmatched_numeric_ordinals,
            lane_count=lane_count,
        )
        if peer_fence_receipt is None:
            return [], set()
    receipt = {
        "boundary_kind": "STRUCTURAL_PEER" if boundary is not None else "TABLE_END",
        "carrier_coefficients": _coefficients(candidate),
        "carrier_role": parent_role,
        "carrier_row_id": candidate["row_id"],
        "component_roles": component_roles,
        "component_row_ids": [record["row_id"] for record in components],
        "excluded_interval_ordinals": (
            [boundary, len(source_rows)] if boundary is not None else None
        ),
        "excluded_row_ids": [f"r{ordinal}" for ordinal in sorted(excluded_ordinals)],
        "peer_boundary_descendant_row_ids": [
            f"r{ordinal}" for ordinal in boundary_descendant_ordinals
        ],
        "post_boundary_total_row_ids": [f"r{ordinal}" for ordinal in later_total_ordinals],
        "peer_boundary_role": boundary_record["role"] if boundary_record is not None else None,
        "peer_boundary_row_id": (
            boundary_record["row_id"] if boundary_record is not None else None
        ),
        "population_interval_ordinals": [candidate["ordinal"], population_end],
        "peer_fence_equation": peer_fence_receipt,
        "rule": "LEADING_PARENT_CARRIER_EXACT_CONTIGUOUS_POPULATION_WITH_PEER_FENCE",
    }
    candidate["allowed_result_roles"] = {parent_role}
    candidate["authoritative_result_roles"] = {parent_role}
    candidate["leading_parent_carrier_for_role"] = parent_role
    if all(record["row_id"] != candidate["row_id"] for record in anonymous):
        anonymous.append(candidate)
    if excluded_ordinals:
        for role in list(records_by_role):
            records_by_role[role] = [
                record
                for record in records_by_role[role]
                if record["ordinal"] not in excluded_ordinals
            ]
            if not records_by_role[role]:
                del records_by_role[role]
        anonymous[:] = [
            record for record in anonymous if record["ordinal"] not in excluded_ordinals
        ]
        if all(record["row_id"] != candidate["row_id"] for record in anonymous):
            anonymous.append(candidate)
    return [receipt], excluded_ordinals


def _trailing_subtotal_population_boundary_receipts(
    *,
    records_by_role: dict[str, list[dict[str, Any]]],
    anonymous: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
    compiled: dict[str, Any],
    unmatched_numeric_ordinals: set[int],
    lane_count: int,
) -> tuple[list[dict[str, Any]], set[int]]:
    """Bind one exact trailing subtotal before a declared peer population."""

    topology = compiled["topology"]
    family_result_role = compiled["family_result_role"]
    role_kinds = {child["role"]: child["role_kind"] for child in topology["children"]}
    components_by_result = {
        equation["result_role"]: {
            role
            for alternative in equation["component_role_alternatives"]
            for role in alternative["component_roles"]
        }
        for equation in compiled["equations"]
    }
    family_population_roles = {family_result_role}
    frontier = [family_result_role]
    while frontier:
        result_role = frontier.pop()
        for role in components_by_result.get(result_role, set()):
            if role not in family_population_roles:
                family_population_roles.add(role)
                frontier.append(role)
    records_by_ordinal: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for role_records in records_by_role.values():
        for record in role_records:
            records_by_ordinal[record["ordinal"]].append(record)

    boundary = None
    boundary_role = None
    for ordinal, row in enumerate(source_rows, start=1):
        try:
            raw_roles = _row_role_match_modes(
                row,
                topology=topology,
                aliases_by_role=compiled["aliases_by_role"],
                fallback_within_role=None,
                enable_declared_equivalences=True,
            )
        except ValueError:
            return [], set()
        peer_roles = sorted(
            role
            for role in raw_roles
            if role_kinds.get(role) == "STRUCTURAL_GROUP" and role not in family_population_roles
        )
        if row.get("row_kind") in {"GROUP", "SUBTOTAL", "ITEM"} and len(peer_roles) == 1:
            boundary = ordinal
            boundary_role = peer_roles[0]
            break
    if boundary is None or boundary <= 2:
        return [], set()
    candidates = [
        record
        for record in anonymous
        if record["ordinal"] == boundary - 1
        and source_rows[record["ordinal"] - 1].get("row_kind") == "SUBTOTAL"
        and _is_generic_total_label(source_rows[record["ordinal"] - 1].get("label_exact"))
    ]
    if len(candidates) != 1:
        return [], set()
    candidate = candidates[0]
    components = []
    for ordinal in range(1, candidate["ordinal"]):
        if ordinal in unmatched_numeric_ordinals:
            return [], set()
        ordinal_records = [
            record
            for record in records_by_ordinal.get(ordinal, [])
            if record["role"] in family_population_roles
            and role_kinds.get(record["role"]) in {"ADDITIVE_CHILD", "STRUCTURAL_GROUP"}
        ]
        source_values = source_rows[ordinal - 1].get("values_exact")
        has_numeric_source = type(source_values) is list and any(
            value is not None for value in source_values
        )
        if len(ordinal_records) > 1 or (has_numeric_source and not ordinal_records):
            return [], set()
        if ordinal_records:
            components.append(ordinal_records[0])
    component_roles = [record["role"] for record in components]
    if (
        len(components) < 2
        or len(component_roles) != len(set(component_roles))
        or not _source_equation_matches_on_observed_lanes(candidate, components)
    ):
        return [], set()
    eligible_results = []
    direct_roles = set(component_roles)
    for equation in compiled["equations"]:
        if equation["result_role"] == family_result_role:
            continue
        for alternative in equation["component_role_alternatives"]:
            declared = set(alternative["component_roles"])
            if (
                alternative["variable_component_subset"]
                and direct_roles <= declared
                and len(direct_roles) >= alternative["minimum_component_count"]
                and sum(role_kinds.get(role) == "ADDITIVE_CHILD" for role in direct_roles)
                >= alternative["minimum_additive_child_count"]
            ) or (not alternative["variable_component_subset"] and direct_roles == declared):
                eligible_results.append(equation["result_role"])
                break
    if len(set(eligible_results)) != 1:
        return [], set()
    intermediate_result_role = eligible_results[0]
    boundary_label = _normalized(source_rows[boundary - 1].get("label_exact"))
    boundary_descendant_ordinals = [
        ordinal
        for ordinal in range(boundary + 1, len(source_rows) + 1)
        if boundary_label
        in {
            _normalized(value)
            for value in source_rows[ordinal - 1].get("hierarchy_path_exact", [])
            if _normalized(value)
        }
    ]
    later_total_ordinals = [
        ordinal
        for ordinal in range(boundary + 1, len(source_rows) + 1)
        if source_rows[ordinal - 1].get("row_kind") == "TOTAL"
    ]
    excluded_ordinals = set(range(boundary, len(source_rows) + 1))
    if (
        not boundary_label
        or not boundary_descendant_ordinals
        or len(later_total_ordinals) != 1
        or any(ordinal in unmatched_numeric_ordinals for ordinal in excluded_ordinals)
    ):
        return [], set()
    peer_fence_receipt = _exact_peer_population_fence_receipt(
        boundary_ordinal=boundary,
        boundary_role=boundary_role,
        carrier=candidate,
        records_by_role=records_by_role,
        anonymous=anonymous,
        source_rows=source_rows,
        compiled=compiled,
        unmatched_numeric_ordinals=unmatched_numeric_ordinals,
        lane_count=lane_count,
    )
    if peer_fence_receipt is None:
        return [], set()
    candidate.setdefault("allowed_result_roles", set()).update(
        {intermediate_result_role, family_result_role}
    )
    candidate.setdefault("authoritative_result_roles", set()).update(
        {intermediate_result_role, family_result_role}
    )
    candidate["trailing_population_carrier_for_roles"] = {
        intermediate_result_role,
        family_result_role,
    }
    for role in list(records_by_role):
        records_by_role[role] = [
            record for record in records_by_role[role] if record["ordinal"] not in excluded_ordinals
        ]
        if not records_by_role[role]:
            del records_by_role[role]
    anonymous[:] = [record for record in anonymous if record["ordinal"] not in excluded_ordinals]
    receipt = {
        "boundary_kind": "STRUCTURAL_PEER",
        "carrier_coefficients": _coefficients(candidate),
        "carrier_position": "TRAILING_SUBTOTAL",
        "carrier_result_roles": [intermediate_result_role, family_result_role],
        "carrier_row_id": candidate["row_id"],
        "component_roles": component_roles,
        "component_row_ids": [record["row_id"] for record in components],
        "excluded_interval_ordinals": [boundary, len(source_rows)],
        "excluded_row_ids": [f"r{ordinal}" for ordinal in sorted(excluded_ordinals)],
        "peer_boundary_descendant_row_ids": [
            f"r{ordinal}" for ordinal in boundary_descendant_ordinals
        ],
        "peer_boundary_role": boundary_role,
        "peer_boundary_row_id": f"r{boundary}",
        "population_interval_ordinals": [1, candidate["ordinal"]],
        "post_boundary_total_row_ids": [f"r{ordinal}" for ordinal in later_total_ordinals],
        "peer_fence_equation": peer_fence_receipt,
        "rule": "TRAILING_SUBTOTAL_EXACT_CONTIGUOUS_POPULATION_WITH_PEER_FENCE",
    }
    return [receipt], excluded_ordinals


def _mapping_from_source_record(
    *,
    record: dict[str, Any],
    role: str,
    report_norm_id: int,
    money_columns: list[dict[str, Any]],
) -> dict[str, Any] | None:
    values = partial_source_mapping_values_v1(record["cells"])
    if values is None:
        return None
    return {
        "columns": canonical_clone_v1(money_columns),
        "hierarchy_path_exact": canonical_clone_v1(record.get("path", [])),
        "label_exact": record.get("label_exact"),
        "report_norm_id": report_norm_id,
        "role": role,
        "row_id": record["row_id"],
        "values": values,
    }


def _apply_presentation_context_bindings(
    *,
    mappings: list[dict[str, Any]],
    resolved: dict[str, dict[str, Any]],
    compiled_specs: dict[str, Any],
    money_columns: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Emit schema totals whose IDs depend on one exact presentation axis."""

    policies = compiled_specs["presentation_context_bindings"]
    if not policies:
        return mappings, [], []
    resolved_roles = set(resolved)
    matched = [
        policy
        for policy in policies
        if resolved_roles & set(policy["evidence_roles"])
        and not resolved_roles & set(policy["excluded_roles"])
    ]
    if len(matched) > 1:
        return mappings, [], ["PRESENTATION_CONTEXT_SCHEMA_BINDING_IS_NOT_UNIQUE"]
    if not matched:
        return mappings, [], []
    policy = matched[0]
    output = canonical_clone_v1(mappings)
    existing_ids = {mapping["report_norm_id"] for mapping in output}
    receipts = []
    for binding in policy["role_bindings"]:
        record = resolved.get(binding["source_role"])
        if record is None:
            continue
        if binding["report_norm_id"] in existing_ids:
            return mappings, [], ["PRESENTATION_CONTEXT_SCHEMA_BINDING_REPEATS_REPORT_NORM_ID"]
        emitted = _mapping_from_source_record(
            record=record,
            role=binding["emitted_role"],
            report_norm_id=binding["report_norm_id"],
            money_columns=money_columns,
        )
        if emitted is None:
            continue
        emitted["presentation_context"] = policy["context"]
        emitted["source_role"] = binding["source_role"]
        output.append(emitted)
        existing_ids.add(binding["report_norm_id"])
        receipts.append(
            {
                "context": policy["context"],
                "emitted_role": binding["emitted_role"],
                "report_norm_id": binding["report_norm_id"],
                "source_role": binding["source_role"],
                "source_row_id": record["row_id"],
            }
        )
    output.sort(key=lambda mapping: (mapping["report_norm_id"], mapping["role"]))
    return output, receipts, []


def _apply_mapping_normalizations(
    *,
    mappings: list[dict[str, Any]],
    resolved: dict[str, dict[str, Any]],
    narrative_evidence: list[dict[str, Any]],
    compiled_specs: dict[str, Any],
    money_columns: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Apply declared observed-source mapping transforms after accounting closure."""

    output = canonical_clone_v1(mappings)
    mapping_by_role = {mapping["role"]: mapping for mapping in output}
    receipts: list[dict[str, Any]] = []
    reasons: list[str] = []
    role_kinds = {
        child["role"]: child["role_kind"] for child in compiled_specs["topology"]["children"]
    }
    bindings = compiled_specs["bindings"]
    for policy in compiled_specs["source_role_mapping_transforms"]:
        source = resolved.get(policy["source_role"])
        if source is None:
            continue
        inclusive = mapping_by_role.get(policy["inclusive_mapping_role"])
        emitted_role = policy["emitted_mapping_role"]
        if (
            inclusive is None
            or emitted_role in mapping_by_role
            or role_kinds.get(policy["source_role"]) != "NONADDITIVE_CHILD"
            or source.get("owner_role") != policy["source_owner_role"]
        ):
            reasons.append("SOURCE_ROLE_MAPPING_NORMALIZATION_IS_NOT_UNIQUE")
            continue
        observed_inclusive = [
            observed_source_coefficient_v1(cell) for cell in inclusive["values"]
        ]
        source_values = _coefficients(source)
        normalized_cells = [
            {
                "coefficient": (
                    observed - source_value
                    if observed is not None and source_value is not None
                    else None
                ),
                "source_text": None,
                "state": (
                    "DERIVED_EXACT_SOURCE_MAPPING_NORMALIZATION"
                    if observed is not None and source_value is not None
                    else "DERIVED_INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL"
                ),
            }
            for observed, source_value in zip(
                observed_inclusive, source_values, strict=True
            )
        ]
        normalized_mapping_values = partial_source_mapping_values_v1(normalized_cells)
        if normalized_mapping_values is None:
            output.remove(inclusive)
            mapping_by_role.pop(policy["inclusive_mapping_role"], None)
            continue
        normalized_values = [
            observed_source_coefficient_v1(cell) for cell in normalized_cells
        ]
        inclusive["values"] = normalized_mapping_values
        inclusive["mapping_normalization"] = {
            "observed_inclusive_coefficients": observed_inclusive,
            "operation": policy["operation"],
            "source_role": policy["source_role"],
            "source_row_id": source["row_id"],
            "source_coefficients": source_values,
        }
        emitted = _mapping_from_source_record(
            record=source,
            role=emitted_role,
            report_norm_id=bindings[emitted_role],
            money_columns=money_columns,
        )
        if emitted is None:
            continue
        emitted["mapping_normalization"] = {
            "inclusive_mapping_role": policy["inclusive_mapping_role"],
            "operation": policy["operation"],
            "source_role": policy["source_role"],
        }
        output.append(emitted)
        mapping_by_role[emitted_role] = emitted
        receipts.append(
            {
                "emitted_mapping_role": emitted_role,
                "inclusive_mapping_role": policy["inclusive_mapping_role"],
                "normalized_inclusive_coefficients": normalized_values,
                "observed_inclusive_coefficients": observed_inclusive,
                "operation": policy["operation"],
                "source_coefficients": source_values,
                "source_role": policy["source_role"],
                "source_row_id": source["row_id"],
            }
        )

    root_role = compiled_specs["topology"]["parent"]["role"]
    for evidence in narrative_evidence:
        root = mapping_by_role.get(root_role)
        emitted_role = evidence["emitted_mapping_role"]
        if root is None or emitted_role in mapping_by_role:
            reasons.append("NARRATIVE_MAPPING_NORMALIZATION_IS_NOT_UNIQUE")
            continue
        observed_root = [observed_source_coefficient_v1(cell) for cell in root["values"]]
        source_values = _coefficients(evidence)
        normalized_cells = [
            {
                "coefficient": (
                    observed + source_value
                    if observed is not None and source_value is not None
                    else None
                ),
                "source_text": None,
                "state": (
                    "DERIVED_EXACT_SOURCE_MAPPING_NORMALIZATION"
                    if observed is not None and source_value is not None
                    else "DERIVED_INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL"
                ),
            }
            for observed, source_value in zip(observed_root, source_values, strict=True)
        ]
        normalized_mapping_values = partial_source_mapping_values_v1(normalized_cells)
        if normalized_mapping_values is None:
            output.remove(root)
            mapping_by_role.pop(root_role, None)
            continue
        normalized_root = [observed_source_coefficient_v1(cell) for cell in normalized_cells]
        root["values"] = normalized_mapping_values
        root["mapping_normalization"] = {
            "narrative_ordinal": evidence["narrative_ordinal"],
            "observed_root_coefficients": observed_root,
            "operation": evidence["operation"],
            "source_coefficients": source_values,
        }
        source_record = {
            "cells": evidence["cells"],
            "label_exact": evidence["narrative_exact"],
            "path": [],
            "row_id": f"narrative:{evidence['narrative_ordinal']}",
        }
        emitted = _mapping_from_source_record(
            record=source_record,
            role=emitted_role,
            report_norm_id=bindings[emitted_role],
            money_columns=money_columns,
        )
        if emitted is None:
            continue
        emitted["mapping_normalization"] = {
            "operation": evidence["operation"],
            "source_comparative_date": evidence["source_comparative_date"],
            "source_kind": "EXACT_FOOTNOTE_NARRATIVE",
        }
        output.append(emitted)
        mapping_by_role[emitted_role] = emitted
        receipts.append(
            {
                "emitted_mapping_role": emitted_role,
                "narrative_exact": evidence["narrative_exact"],
                "narrative_ordinal": evidence["narrative_ordinal"],
                "normalized_root_coefficients": normalized_root,
                "observed_root_coefficients": observed_root,
                "operation": evidence["operation"],
                "source_coefficients": source_values,
                "source_comparative_date": evidence["source_comparative_date"],
            }
        )
    return output, receipts, reasons


def _projected_target_column_index(
    table: dict[str, Any], *, target_column_aliases: list[str]
) -> int | None:
    columns = table.get("columns")
    if type(columns) is not list or not columns:
        return None
    matches = []
    for index, column in enumerate(columns):
        header = _normalized(_header_text(column))
        if column.get("value_kind") == "MONEY" and any(
            header == alias or header.startswith(alias + " ") or f" {alias} " in f" {header} "
            for alias in target_column_aliases
        ):
            matches.append(index)
    return matches[0] if len(matches) == 1 else None


def evaluate_gemini_json_hierarchical_period_table_pair_v1(
    *,
    page_json: Any,
    page_json_version_id: str,
    physical_page: int,
    section_id: str,
    table_ids: list[str],
    compiled_specs: dict[str, Any],
) -> dict[str, Any] | None:
    """Project two exact period tables onto one declared asset column.

    ``None`` means the tables do not satisfy the projection contract and must
    be evaluated independently.  No source cell, period, label, or hierarchy
    relation is inferred by this adapter.
    """

    policy = compiled_specs.get("period_table_projection_policy")
    if policy is None or len(table_ids) != policy["period_table_count"]:
        return None
    if type(page_json) is not dict or type(page_json.get("sections")) is not list:
        raise _error("Gemini JSON projected period page is invalid")
    try:
        section = page_json["sections"][int(section_id[1:]) - 1]
        source_tables = [section["tables"][int(table_id[1:]) - 1] for table_id in table_ids]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise _error("Gemini JSON projected period table identity is invalid") from exc
    table_dates = [_header_date(str(table.get("title_exact") or "")) for table in source_tables]
    table_date_sources = ["TABLE_TITLE" if value is not None else None for value in table_dates]
    table_date_source_texts: list[str | None] = [None for _value in table_dates]
    narrative_period_evidence = None
    missing_date_indices = [index for index, value in enumerate(table_dates) if value is None]
    if len(missing_date_indices) == 1:
        section_dates = _header_dates(str(section.get("title_exact") or ""))
        missing_candidates = section_dates - {value for value in table_dates if value is not None}
        if len(missing_candidates) == 1:
            missing_index = missing_date_indices[0]
            table_dates[missing_index] = next(iter(missing_candidates))
            table_date_sources[missing_index] = "SECTION_TITLE_UNIQUE_MISSING_PERIOD"
    elif (
        len(missing_date_indices) == 2
        and not _header_dates(str(section.get("title_exact") or ""))
        and type(section.get("tables")) is list
        and table_ids == [f"t{ordinal}" for ordinal in range(1, len(section["tables"]) + 1)]
        and _narrative_period_tables_are_exact_parallel_populations(source_tables)
    ):
        narrative_period_evidence = _unique_section_narrative_period_pair(
            section.get("narratives_exact")
        )
        if narrative_period_evidence is not None:
            table_dates = narrative_period_evidence["dates"]
            table_date_sources = [
                "SECTION_NARRATIVE_ORDERED_PERIOD_PAIR" for _value in table_dates
            ]
            table_date_source_texts = narrative_period_evidence["date_source_texts"]
    if any(value is None for value in table_dates) or len(set(table_dates)) != 2:
        return None
    ordered = sorted(
        zip(
            table_dates,
            table_date_sources,
            table_date_source_texts,
            table_ids,
            source_tables,
            strict=True,
        ),
        key=lambda item: item[0],
        reverse=True,
    )
    projected_by_period: list[dict[str, Any]] = []
    for period_date, date_source, date_source_text, source_table_id, table in ordered:
        target_index = _projected_target_column_index(
            table,
            target_column_aliases=policy["target_column_aliases"],
        )
        columns = table.get("columns")
        rows = table.get("rows")
        if target_index is None or type(columns) is not list or type(rows) is not list:
            return None
        records = []
        unmatched_valued = []
        total_rows = []
        for ordinal, row in enumerate(rows, start=1):
            values = row.get("values_exact")
            if type(values) is not list or len(values) != len(columns):
                return None
            roles = _row_roles(
                row,
                topology=compiled_specs["topology"],
                aliases_by_role=compiled_specs["aliases_by_role"],
            )
            visible_value = values[target_index]
            if roles and visible_value is not None:
                records.append(
                    {
                        "ordinal": ordinal,
                        "roles": roles,
                        "row": row,
                        "source_value": visible_value,
                    }
                )
            elif visible_value is not None and row.get("row_kind") in {"SUBTOTAL", "TOTAL"}:
                total_rows.append((ordinal, row, visible_value))
            elif visible_value is not None:
                unmatched_valued.append(ordinal)
        role_signatures = [tuple(record["roles"]) for record in records]
        flattened_roles = [role for signature in role_signatures for role in signature]
        if (
            unmatched_valued
            or not role_signatures
            or len(flattened_roles) != len(set(flattened_roles))
            or len(total_rows) > 1
        ):
            return None
        try:
            component_records = [
                {"cells": [_money(record["source_value"])]} for record in records
            ]
            if total_rows and not _source_equation_matches_on_observed_lanes(
                {"cells": [_money(total_rows[0][2])]}, component_records
            ):
                return None
        except ValueError:
            return None
        projected_by_period.append(
            {
                "column": columns[target_index],
                "date": period_date,
                "date_source": date_source,
                "date_source_text": date_source_text,
                "records": records,
                "roles": [
                    signature[0] if len(signature) == 1 else list(signature)
                    for signature in role_signatures
                ],
                "source_table_id": source_table_id,
                "target_column_index": target_index,
                "total_row": total_rows[0] if total_rows else None,
                "unit_exact": table.get("unit_exact"),
            }
        )
    if projected_by_period[0]["roles"] != projected_by_period[1]["roles"]:
        return None
    projected_rows = []
    for current, comparative in zip(
        projected_by_period[0]["records"],
        projected_by_period[1]["records"],
        strict=True,
    ):
        projected_rows.append(
            {
                "hierarchy_path_exact": canonical_clone_v1(current["row"]["hierarchy_path_exact"]),
                "label_exact": current["row"].get("label_exact"),
                "row_kind": current["row"].get("row_kind"),
                "values_exact": [current["source_value"], comparative["source_value"]],
            }
        )
    if all(period["total_row"] is not None for period in projected_by_period):
        current_total = projected_by_period[0]["total_row"]
        comparative_total = projected_by_period[1]["total_row"]
        projected_rows.append(
            {
                "hierarchy_path_exact": canonical_clone_v1(
                    current_total[1]["hierarchy_path_exact"]
                ),
                "label_exact": current_total[1].get("label_exact"),
                "row_kind": "TOTAL",
                "values_exact": [current_total[2], comparative_total[2]],
            }
        )
    projected_table = {
        "columns": [
            {
                "header_path_exact": [
                    (
                        source_tables[table_ids.index(period["source_table_id"])].get("title_exact")
                        or period["date_source_text"]
                        or period["date"].strftime("%d.%m.%Y")
                    ),
                    *canonical_clone_v1(period["column"]["header_path_exact"]),
                ],
                "value_kind": "MONEY",
            }
            for period in projected_by_period
        ],
        "continuation": "NONE",
        "rows": projected_rows,
        "title_exact": " | ".join(
            str(source_tables[table_ids.index(period["source_table_id"])].get("title_exact") or "")
            for period in projected_by_period
        ),
        "unit_exact": (
            projected_by_period[0]["unit_exact"]
            if projected_by_period[0]["unit_exact"] == projected_by_period[1]["unit_exact"]
            else None
        ),
    }
    projected_page = canonical_clone_v1(page_json)
    primary_table_id = projected_by_period[0]["source_table_id"]
    projected_page["sections"][int(section_id[1:]) - 1]["tables"][int(primary_table_id[1:]) - 1] = (
        projected_table
    )
    result = evaluate_gemini_json_hierarchical_family_table_v1(
        page_json=projected_page,
        page_json_version_id=page_json_version_id,
        physical_page=physical_page,
        section_id=section_id,
        table_id=primary_table_id,
        compiled_specs=compiled_specs,
    )
    receipt = {
        "period_signatures": [period["date"].isoformat() for period in projected_by_period],
        "period_date_sources": [period["date_source"] for period in projected_by_period],
        "population_roles": projected_by_period[0]["roles"],
        "rule": policy["population_policy"],
        "source_table_ids": [period["source_table_id"] for period in projected_by_period],
        "target_column_headers": [
            canonical_clone_v1(period["column"]["header_path_exact"])
            for period in projected_by_period
        ],
        "target_column_indices": [period["target_column_index"] for period in projected_by_period],
    }
    if narrative_period_evidence is not None:
        receipt["narrative_period_binding"] = {
            "date_source_texts_exact": canonical_clone_v1(
                narrative_period_evidence["date_source_texts"]
            ),
            "narrative_exact": narrative_period_evidence["narrative_exact"],
            "narrative_ordinal": narrative_period_evidence["narrative_ordinal"],
            "period_signatures_in_source_order": [
                value.isoformat() for value in narrative_period_evidence["dates"]
            ],
            "projection_relation": "FIRST_TABLE_CURRENT_SECOND_TABLE_COMPARATIVE_SOURCE_ORDER",
            "rule": "UNIQUE_EXACT_SECTION_NARRATIVE_CURRENT_THEN_PARENTHETICAL_COMPARATIVE",
        }
    result["candidate_id"] = "gjfafcv1:candidate:" + canonical_json_sha256_v1(
        {
            "family_id": compiled_specs["topology"]["family_id"],
            "page_json_version_id": page_json_version_id,
            "physical_page": physical_page,
            "section_id": section_id,
            "source_table_ids": receipt["source_table_ids"],
        }
    )
    result["period_table_projection_receipt"] = receipt
    result["parent_binding_kind"] = (
        "PERIOD_TABLE_TARGET_COLUMN_AND_" + result["parent_binding_kind"]
    )
    result["source_table_ids"] = receipt["source_table_ids"]
    if result.get("closure_receipt") is not None:
        result["closure_receipt"]["period_table_projection"] = canonical_clone_v1(receipt)
    return result


def evaluate_gemini_json_hierarchical_family_table_v1(
    *,
    page_json: Any,
    page_json_version_id: str,
    physical_page: int,
    section_id: str,
    table_id: str,
    compiled_specs: dict[str, Any],
    external_context_receipt: dict[str, Any] | None = None,
    external_context_pages: Sequence[Mapping[str, Any]] | None = None,
    external_document_id: str | None = None,
    external_source_logical_name: str | None = None,
    external_source_sha256: str | None = None,
    title_axis_query_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate one local Gemini table with an exact recursive equation DAG."""

    from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import _candidate_result

    topology = compiled_specs["topology"]
    reasons: list[str] = []
    if external_context_receipt is not None:
        policy = compiled_specs.get("title_axis_projection_policy")
        expected_fields = {
            "branch_evidence",
            "branch_role",
            "candidate_page_json_version_id",
            "candidate_section_id",
            "candidate_table_id",
            "context_page_axis_sha256",
            "owner_evidence",
            "owner_mode",
            "owner_role",
            "rule",
            "title_axis_query_receipt_sha256",
        }
        branch_evidence = external_context_receipt.get("branch_evidence")
        owner_evidence = external_context_receipt.get("owner_evidence")
        if (
            type(policy) is not dict
            or type(external_context_receipt) is not dict
            or type(external_context_pages) not in {list, tuple}
            or type(external_document_id) is not str
            or type(external_source_logical_name) is not str
            or type(external_source_sha256) is not str
            or type(title_axis_query_receipt) is not dict
            or set(external_context_receipt) != expected_fields
            or external_context_receipt["candidate_page_json_version_id"] != page_json_version_id
            or external_context_receipt["candidate_section_id"] != section_id
            or external_context_receipt["candidate_table_id"] != table_id
            or external_context_receipt["branch_role"] != policy["structural_branch_role"]
            or external_context_receipt["owner_role"] != topology["parent"]["role"]
            or external_context_receipt["owner_mode"]
            not in {"LOCAL_EXPLICIT_OWNER", "BOUNDED_PRECEDING_SELECTED_PAGE_OWNER_CARRY"}
            or external_context_receipt["rule"]
            != "ROW_QUALIFIED_CANDIDATE_LOCAL_BRANCH_AND_BOUNDED_PRECEDING_OWNER"
            or external_context_receipt["title_axis_query_receipt_sha256"]
            != canonical_json_sha256_v1(title_axis_query_receipt)
            or type(branch_evidence) is not dict
            or branch_evidence.get("page_json_version_id") != page_json_version_id
            or branch_evidence.get("physical_page") != physical_page
            or branch_evidence.get("section_id") != section_id
            or branch_evidence.get("table_id") != table_id
            or branch_evidence.get("source_kind")
            not in {
                "SECTION_TITLE",
                "TABLE_TITLE",
                "SECTION_NARRATIVE",
                "ROW_LABEL",
            }
            or type(owner_evidence) is not dict
            or type(owner_evidence.get("page_json_version_id")) is not str
            or type(owner_evidence.get("physical_page")) is not int
            or not 0
            <= physical_page - owner_evidence["physical_page"]
            <= policy["owner_page_radius"]
            or (
                external_context_receipt["owner_mode"] == "LOCAL_EXPLICIT_OWNER"
                and (
                    owner_evidence["page_json_version_id"] != page_json_version_id
                    or owner_evidence["physical_page"] != physical_page
                )
            )
        ):
            raise _error("Gemini JSON hierarchy external structural context is invalid")
        context_resolution = resolve_candidate_structural_context_v1(
            candidate_document_id=external_document_id,
            candidate_source_logical_name=external_source_logical_name,
            candidate_source_sha256=external_source_sha256,
            candidate_page_json_version_id=page_json_version_id,
            candidate_page_json=page_json,
            candidate_physical_page=physical_page,
            candidate_section_id=section_id,
            candidate_table_id=table_id,
            context_page_records=external_context_pages,
            structural_branch_role=policy["structural_branch_role"],
            structural_branch_aliases=compiled_specs["query_presence_aliases_by_role"][
                policy["structural_branch_role"]
            ],
            structural_branch_fallback_group_aliases=[
                alias
                for role in policy.get("structural_branch_fallback_group_roles", [])
                for alias in compiled_specs["query_presence_aliases_by_role"][role]
            ],
            structural_surface_kinds=policy["structural_surface_kinds"],
            explicit_parent_role=topology["parent"]["role"],
            explicit_parent_aliases=compiled_specs["query_parent_aliases"],
            hard_negative_aliases=topology["hard_negative_aliases"],
            owner_reset_aliases=policy["owner_reset_aliases"],
            adjacent_page_radius=policy["owner_page_radius"],
        )
        if context_resolution["disposition"] != "ACCEPTED":
            raise _error("Gemini JSON hierarchy external structural context does not resolve")
        rederived_context = context_resolution["structural_context_receipt"]
        supplied_context = {
            key: value
            for key, value in external_context_receipt.items()
            if key != "title_axis_query_receipt_sha256"
        }
        if supplied_context != rederived_context:
            raise _error("Gemini JSON hierarchy external structural context does not replay")
    elif any(
        value is not None
        for value in (
            external_context_pages,
            external_document_id,
            external_source_logical_name,
            external_source_sha256,
            title_axis_query_receipt,
        )
    ):
        raise _error("Gemini JSON hierarchy external structural context is incomplete")
    if type(page_json) is not dict or type(page_json.get("sections")) is not list:
        raise _error("Gemini JSON hierarchy page is invalid")
    try:
        section = page_json["sections"][int(section_id[1:]) - 1]
        table = section["tables"][int(table_id[1:]) - 1]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise _error("Gemini JSON hierarchy table identity is invalid") from exc
    title = " ".join(
        value
        for value in (section.get("title_exact"), table.get("title_exact"))
        if type(value) is str and value
    )
    title_folded = _normalized(title)
    narrative_surfaces = [
        value
        for value in section.get("narratives_exact", [])
        if type(value) is str and value
    ]
    narrative_folded = " ".join(_normalized(value) for value in narrative_surfaces)
    structural_owner_folded = " ".join(
        value for value in (title_folded, narrative_folded) if value
    )
    if any(
        _normalized(alias) in structural_owner_folded
        for alias in topology["hard_negative_aliases"]
    ):
        reasons.append("HARD_NEGATIVE_FAMILY_TITLE_PRESENT")
    normalized_parent_aliases = [
        normalized
        for alias in topology["parent"]["aliases"]
        if (normalized := _normalized(alias))
    ]
    parent_title_aliases = [
        alias for alias in normalized_parent_aliases if alias in title_folded
    ]
    parent_in_title = bool(parent_title_aliases)
    parent_narrative_matches = [
        {
            "alias": alias,
            "narrative_exact": narrative,
            "narrative_ordinal": narrative_ordinal,
        }
        for narrative_ordinal, narrative in enumerate(narrative_surfaces, start=1)
        for alias in normalized_parent_aliases
        if alias in _normalized(narrative)
    ]
    parent_narrative_match = (
        sorted(
            parent_narrative_matches,
            key=lambda item: (
                -len(item["alias"].split()),
                -len(item["alias"]),
                item["narrative_ordinal"],
                item["alias"],
            ),
        )[0]
        if parent_narrative_matches and not parent_in_title
        else None
    )
    parent_in_narrative = parent_narrative_match is not None
    parent_surface_aliases = [
        *parent_title_aliases,
        *(
            [parent_narrative_match["alias"]]
            if parent_narrative_match is not None
            else []
        ),
    ]
    parent_in_owner_surface = parent_in_title or parent_in_narrative
    parent_title_match = (
        None
        if parent_in_owner_surface
        else _bounded_one_character_parent_title_match(title, topology["parent"]["aliases"])
    )
    columns = table.get("columns")
    period_value_axis_receipt = None
    percent_indices: list[int] = []
    if compiled_specs["evaluation"]["format_version"] in {
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V5",
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V6",
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V7",
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V8",
    }:
        (
            money_indices,
            money_columns,
            percent_indices,
            period_value_axis_receipt,
            column_reasons,
        ) = _period_value_column_axis(
            columns=columns,
            table_unit=table.get("unit_exact"),
            evaluation=compiled_specs["evaluation"],
        )
        reasons.extend(column_reasons)
    else:
        money_indices = (
            [index for index, column in enumerate(columns) if column.get("value_kind") == "MONEY"]
            if type(columns) is list
            else []
        )
        money_columns = [columns[index] for index in money_indices] if type(columns) is list else []
        unit_is_declared = (
            type(table.get("unit_exact")) is str and bool(table["unit_exact"].strip())
        ) or (
            len(money_columns) == 2
            and all(
                "trieu" in _normalized(" ".join(map(str, column.get("header_path_exact", []))))
                for column in money_columns
            )
        )
        if (
            type(columns) is not list
            or len(money_columns) != 2
            or any(
                type(column.get("header_path_exact")) is not list or not column["header_path_exact"]
                for column in money_columns
            )
            or not unit_is_declared
        ):
            reasons.append("PERIOD_UNIT_OR_MONEY_COLUMN_AXIS_IS_NOT_EXACT")
    supported_lane_counts = (
        {1, 2}
        if compiled_specs["evaluation"]["format_version"] == "ACCOUNTING_FAMILY_EVALUATION_SPEC_V7"
        else {2}
    )
    if len(money_columns) not in supported_lane_counts:
        if "PERIOD_UNIT_OR_MONEY_COLUMN_AXIS_IS_NOT_EXACT" not in reasons:
            reasons.append("PERIOD_UNIT_OR_MONEY_COLUMN_AXIS_IS_NOT_EXACT")
        return _candidate_result(
            topology=topology,
            page_json_version_id=page_json_version_id,
            physical_page=physical_page,
            section_id=section_id,
            table_id=table_id,
            reasons=reasons,
        )
    lane_count = len(money_columns)
    narrative_mapping_evidence, narrative_reasons = _footnote_narrative_mapping_evidence(
        table_title=table.get("title_exact"),
        narratives=section.get("narratives_exact"),
        period_value_axis_receipt=period_value_axis_receipt,
        policies=compiled_specs["footnote_narrative_mapping_transforms"],
    )
    reasons.extend(narrative_reasons)
    source_rows = table.get("rows")
    if type(source_rows) is not list or not source_rows:
        raise _error("Gemini JSON hierarchy row axis is empty")
    explicit_group_branch_interval: tuple[int, int] | None = None
    if (
        external_context_receipt is not None
        and branch_evidence.get("source_kind") == "ROW_LABEL"
        and any(
            _matches(branch_evidence.get("alias"), alias)
            for alias in compiled_specs["query_presence_aliases_by_role"][
                compiled_specs["title_axis_projection_policy"]["structural_branch_role"]
            ]
        )
        and type(branch_evidence.get("row_id")) is str
        and re.fullmatch(r"r[1-9][0-9]*", branch_evidence["row_id"])
    ):
        branch_ordinal = int(branch_evidence["row_id"][1:])
        if 1 <= branch_ordinal <= len(source_rows):
            branch_row = source_rows[branch_ordinal - 1]
            branch_label = _normalized(branch_row.get("label_exact"))
            if (
                branch_row.get("row_kind") == "GROUP"
                and branch_label
                and branch_label == _normalized(branch_evidence.get("source_exact"))
            ):
                # A broad note table may serialize several sibling analyses on
                # one row axis.  When the authenticated branch surface is an
                # explicit GROUP row, its own generic TOTAL/SUBTOTAL is an
                # exact population fence.  Require the branch to be the
                # immediate hierarchy owner of that closing row; a nested
                # subtotal or a later sibling total cannot close this interval.
                closing_ordinals = []
                for ordinal, row in enumerate(source_rows, start=1):
                    if ordinal <= branch_ordinal or row.get("row_kind") not in {
                        "SUBTOTAL",
                        "TOTAL",
                    }:
                        continue
                    if not _is_generic_total_label(row.get("label_exact")):
                        continue
                    normalized_path = [
                        _normalized(value)
                        for value in row.get("hierarchy_path_exact", [])
                        if _normalized(value)
                    ]
                    closing_label = _normalized(row.get("label_exact"))
                    if normalized_path and normalized_path[-1] == closing_label:
                        normalized_path = normalized_path[:-1]
                    if normalized_path and normalized_path[-1] == branch_label:
                        closing_ordinals.append(ordinal)
                if closing_ordinals:
                    explicit_group_branch_interval = (
                        branch_ordinal,
                        closing_ordinals[0],
                    )
    matcher_equivalences_enabled = (
        compiled_specs["evaluation"].get("format_version") == "ACCOUNTING_FAMILY_EVALUATION_SPEC_V8"
    )
    parent_row_ordinals = [
        ordinal
        for ordinal, row in enumerate(source_rows, start=1)
        if any(_matches(row.get("label_exact"), alias) for alias in topology["parent"]["aliases"])
    ]
    explicit_parent_visible = (
        parent_in_owner_surface
        or parent_title_match is not None
        or len(parent_row_ordinals) == 1
        or external_context_receipt is not None
    )
    detached_root_component_enabled = (
        compiled_specs.get("title_axis_projection_policy", {}).get("detached_root_component_policy")
        == "DECLARED_DIRECT_ROOT_COMPONENTS_AND_UNIQUE_EXACT_TOTAL"
    )
    leading_population_enabled = (
        compiled_specs.get("title_axis_projection_policy", {}).get(
            "leading_parent_population_policy"
        )
        == "EXACT_CONTIGUOUS_DIRECT_CHILDREN_WITH_OPTIONAL_DECLARED_PEER_FENCE"
    )
    detached_root_frontier_receipt: dict[str, Any] | None = None
    parent_ordinal = parent_row_ordinals[0] if len(parent_row_ordinals) == 1 else None
    explicit_parent_subtree_visible = (
        parent_ordinal is not None
        and parent_ordinal < len(source_rows)
        and _path_has_role(
            source_rows[parent_ordinal].get("hierarchy_path_exact"),
            aliases=topology["parent"]["aliases"],
            label_exact=source_rows[parent_ordinal].get("label_exact"),
        )
    )
    # A broad statement table can contain one explicit, more-specific family
    # group among unrelated sibling analyses.  Slice only that demonstrably
    # narrower subtree.  Do not apply the same rule when the title already
    # names a specific family view and the row is merely its generic
    # ``Cho vay khach hang`` carrier: that shape can have valid detached
    # components (for example delayed-LC quality) before the grand total.
    # Compare the explicit row with the most-specific alias that actually
    # matched this title.  A shorter alias elsewhere in the same family spec
    # (for example ``Theo kỳ hạn``) says nothing about whether the visible
    # title ``Cho vay khách hàng`` is broader than the explicit row
    # ``Phân tích dư nợ theo thời gian``.
    matched_parent_title_alias_length = max(
        (len(alias.split()) for alias in parent_surface_aliases),
        default=0,
    )
    broad_parent_title_only = bool(parent_surface_aliases)
    parent_row_has_more_specific_alias = parent_ordinal is not None and any(
        len(alias.split()) > matched_parent_title_alias_length
        and _matches(source_rows[parent_ordinal - 1].get("label_exact"), alias)
        for alias in normalized_parent_aliases
    )
    if len(parent_row_ordinals) == 1 and (
        not parent_in_owner_surface
        or (
            broad_parent_title_only
            and explicit_parent_subtree_visible
            and parent_row_has_more_specific_alias
        )
    ):
        parent_ordinal = parent_row_ordinals[0]
        parent_source_values = source_rows[parent_ordinal - 1].get("values_exact")
        parent_has_numeric_values = (
            type(parent_source_values) is list
            and len(parent_source_values) == len(columns or [])
            and any(parent_source_values[index] is not None for index in money_indices)
        )
        rows = (
            list(enumerate(source_rows, start=1))
            if leading_population_enabled and parent_has_numeric_values
            else [
                (ordinal, row)
                for ordinal, row in enumerate(source_rows, start=1)
                if ordinal == parent_ordinal
                or _path_has_role(
                    row.get("hierarchy_path_exact"),
                    aliases=topology["parent"]["aliases"],
                    label_exact=row.get("label_exact"),
                )
            ]
        )
        if explicit_group_branch_interval is not None:
            interval_start, interval_end = explicit_group_branch_interval
            rows = [
                (ordinal, source_rows[ordinal - 1])
                for ordinal in range(interval_start, interval_end + 1)
            ]
        if not leading_population_enabled and rows:
            # A provider may flatten the closing total out of the explicit
            # parent hierarchy even though it is the immediate, contiguous
            # final row of that parent block.  Admit only that one exact
            # structural shape.  Arithmetic and the anonymous-carrier
            # one-use rule below still have to prove that the row closes the
            # selected family; an intervening/reset row leaves it excluded.
            selected_ordinals = {ordinal for ordinal, _row in rows}
            selected_end = max(selected_ordinals)
            selected_interval = set(range(parent_ordinal, selected_end + 1))
            if selected_ordinals == selected_interval and selected_end < len(source_rows):
                trailing_ordinal = selected_end + 1
                trailing_row = source_rows[trailing_ordinal - 1]
                trailing_values = trailing_row.get("values_exact")
                if (
                    trailing_row.get("row_kind") in {"SUBTOTAL", "TOTAL"}
                    and _is_generic_total_label(trailing_row.get("label_exact"))
                    and type(trailing_values) is list
                    and len(trailing_values) == len(columns or [])
                    and any(trailing_values[index] is not None for index in money_indices)
                ):
                    rows.append((trailing_ordinal, trailing_row))
        if (
            detached_root_component_enabled
            and not parent_has_numeric_values
            and explicit_group_branch_interval is None
        ):
            family_root_equation = next(
                equation
                for equation in compiled_specs["equations"]
                if equation["result_role"] == compiled_specs["family_result_role"]
            )
            declared_direct_root_roles = {
                role
                for alternative in family_root_equation["component_role_alternatives"]
                for role in alternative["component_roles"]
            }
            equation_by_result = {
                equation["result_role"]: equation for equation in compiled_specs["equations"]
            }
            family_population_roles = set(declared_direct_root_roles)
            population_frontier = list(declared_direct_root_roles)
            while population_frontier:
                result_role = population_frontier.pop()
                equation = equation_by_result.get(result_role)
                if equation is None:
                    continue
                for alternative in equation["component_role_alternatives"]:
                    for role in alternative["component_roles"]:
                        if role not in family_population_roles:
                            family_population_roles.add(role)
                            population_frontier.append(role)
            detached_subtree_root_roles = declared_direct_root_roles | (
                family_population_roles & set(equation_by_result)
            )
            selected_ordinals = {ordinal for ordinal, _row in rows}
            detached_components: list[dict[str, Any]] = []
            detached_subtotal_row_ids: list[str] = []
            detached_subtree_labels: dict[str, str] = {}
            detached_subtree_rows: list[dict[str, Any]] = []
            detached_total_row_ids: list[str] = []
            parent_owned_interval_end = max(selected_ordinals)

            def detached_is_top_level(row: Mapping[str, Any]) -> bool:
                normalized_path = [
                    _normalized(value)
                    for value in row.get("hierarchy_path_exact", [])
                    if _normalized(value)
                ]
                normalized_label = _normalized(row.get("label_exact"))
                return len(normalized_path) <= 1 and (
                    not normalized_path or normalized_path[-1] == normalized_label
                )

            post_parent_total_ordinals = [
                ordinal
                for ordinal, row in enumerate(source_rows, start=1)
                if ordinal > parent_owned_interval_end
                and detached_is_top_level(row)
                and row.get("row_kind") == "TOTAL"
            ]
            detached_interval_end = (
                post_parent_total_ordinals[0]
                if len(post_parent_total_ordinals) == 1
                else len(source_rows)
            )
            for ordinal, row in enumerate(source_rows, start=1):
                if (
                    ordinal in selected_ordinals
                    or ordinal <= parent_owned_interval_end
                    or ordinal > detached_interval_end
                ):
                    continue
                normalized_label = _normalized(row.get("label_exact"))
                if not detached_is_top_level(row):
                    continue
                try:
                    detached_role_modes = _row_role_match_modes(
                        row,
                        topology=topology,
                        aliases_by_role=compiled_specs["aliases_by_role"],
                        fallback_within_role=None,
                        enable_declared_equivalences=matcher_equivalences_enabled,
                    )
                except ValueError:
                    reasons.append(f"DETACHED_ROOT_COMPONENT_ROLE_MATCH_IS_AMBIGUOUS:{ordinal}")
                    continue
                detached_roles = sorted(set(detached_role_modes) & detached_subtree_root_roles)
                if len(detached_roles) == 1:
                    rows.append((ordinal, row))
                    selected_ordinals.add(ordinal)
                    detached_components.append({"role": detached_roles[0], "row_id": f"r{ordinal}"})
                    if detached_roles[0] in equation_by_result and normalized_label:
                        detached_subtree_labels[normalized_label] = detached_roles[0]
                elif len(detached_roles) > 1:
                    reasons.append(f"DETACHED_ROOT_COMPONENT_ROLE_MATCH_IS_AMBIGUOUS:{ordinal}")
                elif row.get("row_kind") == "SUBTOTAL" and not normalized_label:
                    rows.append((ordinal, row))
                    selected_ordinals.add(ordinal)
                    detached_subtotal_row_ids.append(f"r{ordinal}")
                elif row.get("row_kind") == "TOTAL":
                    rows.append((ordinal, row))
                    selected_ordinals.add(ordinal)
                    detached_total_row_ids.append(f"r{ordinal}")
                else:
                    source_values = row.get("values_exact")
                    if type(source_values) is list and any(
                        source_values[index] is not None for index in money_indices
                    ):
                        reasons.append(f"UNRECOGNIZED_DETACHED_TOP_LEVEL_NUMERIC_ROW:{ordinal}")
                    elif row.get("row_kind") == "GROUP" and normalized_label:
                        reasons.append(f"UNRECOGNIZED_DETACHED_TOP_LEVEL_RESET:{ordinal}")
            for ordinal, row in enumerate(source_rows, start=1):
                if (
                    ordinal in selected_ordinals
                    or ordinal <= parent_owned_interval_end
                    or ordinal > detached_interval_end
                    or not detached_subtree_labels
                ):
                    continue
                path_labels = {
                    _normalized(value)
                    for value in row.get("hierarchy_path_exact", [])
                    if _normalized(value)
                }
                owning_labels = sorted(path_labels & set(detached_subtree_labels))
                if not owning_labels:
                    continue
                try:
                    subtree_role_modes = _row_role_match_modes(
                        row,
                        topology=topology,
                        aliases_by_role=compiled_specs["aliases_by_role"],
                        fallback_within_role=detached_subtree_labels[owning_labels[-1]],
                        enable_declared_equivalences=matcher_equivalences_enabled,
                    )
                except ValueError:
                    reasons.append(f"DETACHED_ROOT_SUBTREE_ROLE_MATCH_IS_AMBIGUOUS:{ordinal}")
                    continue
                subtree_roles = sorted(set(subtree_role_modes) & family_population_roles)
                if len(subtree_roles) != 1:
                    source_values = row.get("values_exact")
                    if type(source_values) is list and any(
                        source_values[index] is not None for index in money_indices
                    ):
                        reasons.append(
                            f"DETACHED_ROOT_SUBTREE_NUMERIC_ROLE_COUNT_NOT_ONE:{ordinal}:"
                            f"{len(subtree_roles)}"
                        )
                    continue
                rows.append((ordinal, row))
                selected_ordinals.add(ordinal)
                detached_subtree_rows.append(
                    {
                        "owner_role": detached_subtree_labels[owning_labels[-1]],
                        "role": subtree_roles[0],
                        "row_id": f"r{ordinal}",
                    }
                )
            for ordinal in range(parent_owned_interval_end + 1, detached_interval_end + 1):
                if ordinal in selected_ordinals:
                    continue
                row = source_rows[ordinal - 1]
                source_values = row.get("values_exact")
                if type(source_values) is list and any(
                    source_values[index] is not None for index in money_indices
                ):
                    reasons.append(f"UNBOUND_DETACHED_ROOT_INTERVAL_NUMERIC_ROW:{ordinal}")
            rows.sort(key=lambda item: item[0])
            detached_evidence_present = bool(
                detached_components
                or detached_subtotal_row_ids
                or detached_subtree_rows
                or detached_total_row_ids
            )
            if detached_evidence_present and len(post_parent_total_ordinals) != 1:
                reasons.append(
                    f"DETACHED_ROOT_TOTAL_ROW_COUNT_NOT_ONE:{len(post_parent_total_ordinals)}"
                )
            if detached_evidence_present:
                interval_rows = []
                for ordinal in range(parent_owned_interval_end + 1, detached_interval_end + 1):
                    row = source_rows[ordinal - 1]
                    try:
                        coefficients = [
                            _money(row["values_exact"][index])["coefficient"]
                            for index in money_indices
                        ]
                    except (KeyError, IndexError, TypeError, ValueError):
                        coefficients = None
                    interval_rows.append(
                        {
                            "money_coefficients": coefficients,
                            "row_id": f"r{ordinal}",
                            "row_kind": row.get("row_kind"),
                        }
                    )
                detached_root_frontier_receipt = {
                    "component_rows": detached_components,
                    "intermediate_subtotal_row_ids": detached_subtotal_row_ids,
                    "component_subtree_rows": detached_subtree_rows,
                    "family_result_role": compiled_specs["family_result_role"],
                    "parent_row_id": f"r{parent_ordinal}",
                    "rule": "DECLARED_DIRECT_ROOT_COMPONENTS_AND_UNIQUE_EXACT_TOTAL",
                    "source_interval_ordinals": [
                        parent_owned_interval_end + 1,
                        detached_interval_end,
                    ],
                    "source_interval_rows": interval_rows,
                    "total_row_ids": detached_total_row_ids,
                }
    else:
        rows = list(enumerate(source_rows, start=1))
        if explicit_group_branch_interval is not None:
            interval_start, interval_end = explicit_group_branch_interval
            rows = [
                (ordinal, source_rows[ordinal - 1])
                for ordinal in range(interval_start, interval_end + 1)
            ]
    structural_roles = {
        child["role"] for child in topology["children"] if child["role_kind"] == "STRUCTURAL_GROUP"
    }
    records_by_role: dict[str, list[dict[str, Any]]] = defaultdict(list)
    anonymous: list[dict[str, Any]] = []
    source_cell_alignment_alternatives: dict[str, dict[str, Any]] = {}
    intermediate_parent_subtotal_candidates: list[dict[str, Any]] = []
    unmatched_numeric: list[int] = []
    unrelated_group_labels: set[str] = set()
    active_structural_role: str | None = (
        external_context_receipt["branch_role"] if external_context_receipt is not None else None
    )
    trailing_population_enabled = (
        compiled_specs.get("title_axis_projection_policy", {}).get(
            "trailing_subtotal_population_policy"
        )
        == "EXACT_CONTIGUOUS_DIRECT_CHILDREN_TRAILING_SUBTOTAL_WITH_DECLARED_PEER_FENCE"
    )
    contextual_variants_by_source = {
        variant["source_role"]: variant
        for variant in compiled_specs.get("title_axis_projection_policy", {}).get(
            "contextual_role_variants", []
        )
    }
    for ordinal, row in rows:
        source_values = row.get("values_exact")
        if type(source_values) is not list or len(source_values) != len(columns or []):
            reasons.append(f"ROW_VALUE_VECTOR_DOES_NOT_MATCH_COLUMN_AXIS:{ordinal}")
            continue
        values = [source_values[index] for index in money_indices]
        try:
            cells = [_money(value) for value in values]
        except ValueError:
            reasons.append(f"ROW_MONEY_CELL_IS_NOT_EXACT_INTEGER:{ordinal}")
            continue
        percentage_companions = []
        if percent_indices:
            try:
                percentage_companions = [
                    {
                        "column_index": index,
                        **_percent(source_values[index]),
                    }
                    for index in percent_indices
                ]
            except ValueError:
                reasons.append(f"ROW_PERCENT_CELL_IS_NOT_EXACT_DECIMAL:{ordinal}")
                continue
        if (
            money_indices == [0, 2]
            and percent_indices == [1, 3]
            and len(source_values) == 4
            and type(source_values[0]) is str
            and source_values[0].strip()
            and all(character in _DASHES for character in source_values[0].strip())
            and type(source_values[1]) is str
            and re.fullmatch(
                r"\s*[0-9]{1,3}(?:[., ][0-9]{3})+\s*",
                source_values[1],
            )
            is not None
            and type(source_values[2]) is str
            and re.fullmatch(r"\s*0(?:[.,]0+)?%?\s*", source_values[2]) is not None
            and source_values[3] is None
        ):
            shifted_money = _money(source_values[1])
            if shifted_money["coefficient"] != 0:
                source_cell_alignment_alternatives[f"r{ordinal}"] = {
                    "cells": [_money(source_values[0]), shifted_money],
                    "percentage_companions": [
                        {"column_index": 1, **_percent(None)},
                        {"column_index": 3, **_percent(source_values[2])},
                    ],
                    "receipt": {
                        "original_values_exact": canonical_clone_v1(source_values),
                        "repaired_source_column_indices": [0, None, 1, 2],
                        "row_id": f"r{ordinal}",
                        "rule": (
                            "UNIQUE_EXACT_CLOSURE_FOUR_LANE_LEFT_SHIFT_AFTER_"
                            "DASH_AND_MISSING_PERCENTAGE_CELL"
                        ),
                    },
                }
        try:
            role_match_modes = _row_role_match_modes(
                row,
                topology=topology,
                aliases_by_role=compiled_specs["aliases_by_role"],
                fallback_within_role=active_structural_role,
                enable_declared_equivalences=matcher_equivalences_enabled,
            )
        except ValueError:
            reasons.append(f"ROW_ROLE_MATCH_IS_AMBIGUOUS:{ordinal}")
            unmatched_numeric.append(ordinal)
            continue
        roles = list(role_match_modes)
        contextual_variant_failed = False
        for source_role in sorted(set(roles) & set(contextual_variants_by_source)):
            variant = contextual_variants_by_source[source_role]
            descendant_roles = set(variant["nested_descendant_roles"])
            label = _normalized(row.get("label_exact"))
            nested_roles: set[str] = set()
            peer_roles: set[str] = set()
            for other_ordinal, other_row in enumerate(source_rows, start=1):
                if other_ordinal == ordinal:
                    continue
                try:
                    other_roles = (
                        set(
                            _row_role_match_modes(
                                other_row,
                                topology=topology,
                                aliases_by_role=compiled_specs["aliases_by_role"],
                                fallback_within_role=compiled_specs["title_axis_projection_policy"][
                                    "structural_branch_role"
                                ],
                                enable_declared_equivalences=matcher_equivalences_enabled,
                            )
                        )
                        & descendant_roles
                    )
                except ValueError:
                    contextual_variant_failed = True
                    break
                if not other_roles:
                    continue
                peer_roles.update(other_roles)
                if label and label in {
                    _normalized(value)
                    for value in other_row.get("hierarchy_path_exact", [])
                    if _normalized(value)
                }:
                    nested_roles.update(other_roles)
            if contextual_variant_failed:
                break
            if nested_roles:
                if row.get("row_kind") not in {"GROUP", "SUBTOTAL"}:
                    contextual_variant_failed = True
                    break
            elif row.get("row_kind") != "ITEM":
                contextual_variant_failed = True
                break
            else:
                roles = [role for role in roles if role != source_role]
                roles.append(variant["flat_terminal_role"])
                role_match_modes = {
                    role: mode for role, mode in role_match_modes.items() if role != source_role
                }
                role_match_modes[variant["flat_terminal_role"]] = (
                    "DECLARED_CONTEXTUAL_FLAT_TERMINAL_REDIRECT"
                )
        if contextual_variant_failed:
            unmatched_numeric.append(ordinal)
            continue
        row_structural_roles = sorted(structural_roles & set(roles))
        if len(row_structural_roles) == 1:
            active_structural_role = row_structural_roles[0]
        path_labels = {
            _normalized(value)
            for value in row.get("hierarchy_path_exact", [])
            if _normalized(value)
        }
        if not roles and any(
            path_label == unrelated or path_label.startswith(unrelated)
            for path_label in path_labels
            for unrelated in unrelated_group_labels
        ):
            continue
        if (
            not roles
            and row.get("row_kind") == "GROUP"
            and all(value is None for value in values)
            and _normalized(row.get("label_exact"))
        ):
            active_structural_role = None
            # An explicit family-parent row is a scope carrier, not an
            # unrelated peer fence.  Marking it unrelated causes its own
            # unlabelled trailing total (whose hierarchy path correctly
            # retains the parent) to be discarded before arithmetic closure.
            if ordinal not in parent_row_ordinals:
                unrelated_group_labels.add(_normalized(row["label_exact"]))
            continue
        owner = _nearest_owner(
            row,
            structural_roles=structural_roles,
            aliases_by_role=compiled_specs["aliases_by_role"],
            own_roles=set(roles),
        )
        path_has_family_parent = _path_has_role(
            row.get("hierarchy_path_exact"),
            aliases=topology["parent"]["aliases"],
            label_exact=row.get("label_exact"),
        )
        if path_has_family_parent and (
            owner is None
            or (row.get("row_kind") == "TOTAL" and _is_generic_total_label(row.get("label_exact")))
        ):
            owner = topology["parent"]["role"]
        record = {
            "cells": cells,
            "label_exact": row.get("label_exact"),
            "ordinal": ordinal,
            "owner_role": owner,
            "path": canonical_clone_v1(row.get("hierarchy_path_exact")),
            "percentage_companions": percentage_companions,
            "row_id": f"r{ordinal}",
        }
        is_parent_carrier_candidate = (
            leading_population_enabled
            and ordinal in parent_row_ordinals
            and row.get("row_kind") in {"GROUP", "SUBTOTAL"}
            and any(value is not None for value in values)
        )
        if is_parent_carrier_candidate:
            intermediate_parent_subtotal_candidates.append(record)
        if roles and any(value is not None for value in values):
            structural_matches = [
                role
                for role in roles
                if next(
                    child["role_kind"] for child in topology["children"] if child["role"] == role
                )
                == "STRUCTURAL_GROUP"
            ]
            additive_matches = [role for role in roles if role not in structural_matches]
            if len(structural_matches) == 1 and additive_matches:
                record["owner_role"] = structural_matches[0]
            for role in additive_matches or structural_matches:
                records_by_role[role].append(
                    {
                        **record,
                        "label_match_mode": role_match_modes[role],
                        "role": role,
                    }
                )
            if structural_matches and additive_matches:
                anonymous.append(
                    {
                        **record,
                        "allowed_result_roles": set(structural_matches),
                    }
                )
        elif roles:
            # A null structural header authenticates hierarchy but is not a
            # zero-valued accounting result.  Its children/subtotal decide it.
            continue
        elif row.get("row_kind") in {"SUBTOTAL", "TOTAL"}:
            if owner is None and row.get("row_kind") == "TOTAL":
                record["allowed_result_roles"] = {compiled_specs["family_result_role"]}
                record["authoritative_result_roles"] = {compiled_specs["family_result_role"]}
            elif (
                owner in structural_roles
                and row.get("row_kind") == "TOTAL"
                and _is_generic_total_label(row.get("label_exact"))
            ):
                # Providers sometimes retain the preceding structural group
                # in the hierarchy path of the final unlabeled table total.
                # Keep both exact accounting interpretations available: the
                # row may close that structural group, or it may be the family
                # total after the group.  Arithmetic, source order and the
                # one-use anonymous-carrier rule still have to select exactly
                # one interpretation; otherwise evaluation remains unresolved.
                record["source_owner_role"] = owner
                record["owner_role"] = None
                record["allowed_result_roles"] = {
                    owner,
                    compiled_specs["family_result_role"],
                }
            elif (
                (owner is None or owner == topology["parent"]["role"])
                and row.get("row_kind") == "SUBTOTAL"
                and _is_generic_total_label(row.get("label_exact"))
                and compiled_specs["evaluation"]["format_version"]
                in {
                    "ACCOUNTING_FAMILY_EVALUATION_SPEC_V5",
                    "ACCOUNTING_FAMILY_EVALUATION_SPEC_V6",
                    "ACCOUNTING_FAMILY_EVALUATION_SPEC_V7",
                    "ACCOUNTING_FAMILY_EVALUATION_SPEC_V8",
                }
            ):
                record["allowed_result_roles"] = {
                    equation["result_role"]
                    for equation in compiled_specs["equations"]
                    if equation["result_role"] != compiled_specs["family_result_role"]
                }
            anonymous.append(record)
        elif is_parent_carrier_candidate:
            continue
        elif ordinal in parent_row_ordinals and row.get("row_kind") == "GROUP":
            intermediate_parent_subtotal_candidates.append(record)
        elif all(value is None for value in values):
            continue
        else:
            unmatched_numeric.append(ordinal)
    required_pools_satisfied = True
    for pool in topology.get("required_role_pools", []):
        observed_count = sum(role in records_by_role for role in pool["roles"])
        if observed_count < pool["minimum_count"]:
            required_pools_satisfied = False
            reasons.append(
                f"REQUIRED_ROLE_POOL_COUNT_BELOW_MINIMUM:{observed_count}:{pool['minimum_count']}"
            )
    required_combination_visible = any(
        all(role in records_by_role for role in combination)
        for combination in topology["required_role_combinations"]
    )
    if not explicit_parent_visible and not (
        topology["parent"]["resolution_mode"] == "EXPLICIT_OR_UNIQUE_REQUIRED_CHILD_CLUSTER"
        and required_pools_satisfied
        and required_combination_visible
    ):
        reasons.append("FAMILY_PARENT_NOT_VISIBLE_IN_SECTION_TABLE_OR_UNIQUE_ROW")
    # A later presentation view may repeat one structural subtotal beneath an
    # untyped, label-only group (for example a listed/unlisted disclosure).
    # Keep the primary occurrence and bind the repeated subtotal as a
    # corroborating result only when its own typed children exhaustively replay
    # the same two-lane value.  Any partial, mismatched, or peer duplicate stays
    # on the ordinary fail-closed occurrence-count path.
    for role in sorted(structural_roles & set(records_by_role)):
        occurrences = records_by_role[role]
        if len(occurrences) != 2:
            continue

        def has_untyped_group_ancestor(record: dict[str, Any]) -> bool:
            path_labels = {_normalized(value) for value in record["path"] if _normalized(value)}
            for ancestor_ordinal, ancestor in enumerate(source_rows, start=1):
                if ancestor_ordinal >= record["ordinal"] or ancestor.get("row_kind") != "GROUP":
                    continue
                ancestor_values = ancestor.get("values_exact")
                ancestor_label = _normalized(ancestor.get("label_exact"))
                if (
                    type(ancestor_values) is list
                    and len(ancestor_values) == len(columns or [])
                    and all(ancestor_values[index] is None for index in money_indices)
                    and ancestor_label in path_labels
                    and not _row_roles(
                        ancestor,
                        topology=topology,
                        aliases_by_role=compiled_specs["aliases_by_role"],
                    )
                ):
                    return True
            return False

        primary = [record for record in occurrences if not has_untyped_group_ancestor(record)]
        shadows = [record for record in occurrences if has_untyped_group_ancestor(record)]
        if len(primary) != 1 or len(shadows) != 1:
            continue
        shadow = shadows[0]
        shadow_label = _normalized(shadow["label_exact"])
        descendants = [
            record
            for records in records_by_role.values()
            for record in records
            if record["role"] != role
            and record.get("owner_role") == role
            and record["ordinal"] > shadow["ordinal"]
            and shadow_label
            in {_normalized(value) for value in record["path"] if _normalized(value)}
        ]
        if (
            not _records_match_on_observed_lanes(primary[0], shadow)
            or not descendants
            or not _source_equation_matches_on_observed_lanes(shadow, descendants)
        ):
            continue
        records_by_role[role] = primary
        anonymous.append(
            {
                **shadow,
                "allowed_result_roles": {role},
                "owner_role": role,
                "presentation_shadow_for_role": role,
            }
        )
    leading_parent_population_receipts, excluded_population_ordinals = (
        _leading_parent_population_boundary_receipts(
            candidates=intermediate_parent_subtotal_candidates,
            records_by_role=records_by_role,
            anonymous=anonymous,
            source_rows=source_rows,
            compiled=compiled_specs,
            unmatched_numeric_ordinals=set(unmatched_numeric),
            lane_count=lane_count,
        )
        if leading_population_enabled
        else ([], set())
    )
    trailing_subtotal_population_receipts: list[dict[str, Any]] = []
    if trailing_population_enabled and not leading_parent_population_receipts:
        (
            trailing_subtotal_population_receipts,
            trailing_excluded_population_ordinals,
        ) = _trailing_subtotal_population_boundary_receipts(
            records_by_role=records_by_role,
            anonymous=anonymous,
            source_rows=source_rows,
            compiled=compiled_specs,
            unmatched_numeric_ordinals=set(unmatched_numeric),
            lane_count=lane_count,
        )
        excluded_population_ordinals.update(trailing_excluded_population_ordinals)
    unmatched_numeric = [
        ordinal for ordinal in unmatched_numeric if ordinal not in excluded_population_ordinals
    ]
    if (
        leading_population_enabled
        and intermediate_parent_subtotal_candidates
        and not leading_parent_population_receipts
    ):
        unmatched_numeric.extend(
            record["ordinal"] for record in intermediate_parent_subtotal_candidates
        )
    for role, records in records_by_role.items():
        if len(records) > 1:
            reasons.append(f"ROLE_OCCURRENCE_COUNT_ABOVE_ONE:{role}:{len(records)}")
    base = {role: records[0] for role, records in records_by_role.items() if len(records) == 1}
    legacy_intermediate_parent_receipts = (
        []
        if leading_population_enabled
        else _legacy_intermediate_parent_subtotal_receipts(
            candidates=intermediate_parent_subtotal_candidates,
            records_by_role=records_by_role,
            anonymous=anonymous,
            source_rows=source_rows,
            topology=topology,
            unmatched_numeric_ordinals=set(unmatched_numeric),
            lane_count=lane_count,
        )
    )
    if (
        not leading_population_enabled
        and intermediate_parent_subtotal_candidates
        and not legacy_intermediate_parent_receipts
    ):
        unmatched_numeric.extend(
            record["ordinal"] for record in intermediate_parent_subtotal_candidates
        )
    ambiguous = "INTERBANK_PROVISION_AMBIGUOUS" in base
    targets = [None]
    if ambiguous:
        targets = [
            role
            for role in (
                "INTERBANK_DEPOSIT_PROVISION",
                "INTERBANK_LOAN_PROVISION",
                "TOTAL_INTERBANK_PROVISION",
            )
            if role in compiled_specs["aliases_by_role"] and role not in base
        ]
        source_owner = base["INTERBANK_PROVISION_AMBIGUOUS"].get("owner_role")
        if source_owner is not None:
            result_parent: dict[str, set[str]] = defaultdict(set)
            target_parents: dict[str, set[str]] = defaultdict(set)
            for equation in compiled_specs["equations"]:
                result_role = equation["result_role"]
                for alternative in equation["component_role_alternatives"]:
                    for component_role in alternative["component_roles"]:
                        result_parent[component_role].add(result_role)
                        if component_role in targets:
                            target_parents[component_role].add(result_role)

            def distance_to_parent(parent: str) -> int | None:
                frontier = {source_owner}
                seen = set()
                for distance in range(len(compiled_specs["equations"]) + 2):
                    if parent in frontier:
                        return distance
                    seen.update(frontier)
                    frontier = {
                        ancestor
                        for role in frontier
                        for ancestor in result_parent.get(role, set())
                        if ancestor not in seen
                    }
                return None

            distances = {
                role: min(
                    (
                        distance
                        for parent in target_parents[role]
                        if (distance := distance_to_parent(parent)) is not None
                    ),
                    default=None,
                )
                for role in targets
            }
            finite = [distance for distance in distances.values() if distance is not None]
            if finite:
                nearest = min(finite)
                targets = [role for role in targets if distances[role] == nearest]
                exact_scope_targets = [
                    role for role in targets if target_parents[role] == {source_owner}
                ]
                if len(exact_scope_targets) == 1:
                    targets = exact_scope_targets
    solution_bases: list[tuple[dict[str, dict[str, Any]], dict[str, Any] | None]] = [
        (base, None)
    ]
    for row_id, alternative in sorted(source_cell_alignment_alternatives.items()):
        matched_roles = [
            role for role, record in base.items() if record.get("row_id") == row_id
        ]
        if len(matched_roles) != 1:
            continue
        role = matched_roles[0]
        repaired_base = dict(base)
        repaired_base[role] = {
            **base[role],
            "cells": canonical_clone_v1(alternative["cells"]),
            "percentage_companions": canonical_clone_v1(
                alternative["percentage_companions"]
            ),
        }
        solution_bases.append((repaired_base, alternative["receipt"]))
    solutions = []
    solution_failures: list[str] = []
    for solution_base, alignment_receipt in solution_bases:
        for target in targets:
            resolved, receipts, local_reasons, used = _solve(
                base_by_role=solution_base,
                anonymous=anonymous,
                compiled=compiled_specs,
                ambiguous_provision_target=target,
                lane_count=lane_count,
            )
            if not local_reasons:
                solutions.append((resolved, receipts, used, target, alignment_receipt))
            else:
                solution_failures.extend(local_reasons)
    if len(solutions) != 1:
        reasons.append(f"HIERARCHICAL_SOLUTION_COUNT_NOT_ONE:{len(solutions)}")
        if not solutions:
            reasons.extend(solution_failures)
    if unmatched_numeric:
        reasons.append(
            "UNBOUND_VISIBLE_NUMERIC_ROWS:" + ",".join(map(str, sorted(set(unmatched_numeric))))
        )
    result = _candidate_result(
        topology=topology,
        page_json_version_id=page_json_version_id,
        physical_page=physical_page,
        section_id=section_id,
        table_id=table_id,
        reasons=reasons,
    )
    result["parent_binding_kind"] = (
        ("EXPLICIT_CANDIDATE_LOCAL_BRANCH_AND_" + external_context_receipt["owner_mode"])
        if external_context_receipt is not None
        else "EXPLICIT_SECTION_OR_TABLE_TITLE"
        if parent_in_title
        else "EXPLICIT_SECTION_NARRATIVE"
        if parent_in_narrative
        else "ONE_EDIT_SECTION_OR_TABLE_PARENT_TITLE_WITH_EXACT_GRAPH"
        if parent_title_match is not None
        else "EXPLICIT_PARENT_ROW"
        if len(parent_row_ordinals) == 1
        else "UNIQUE_REQUIRED_CHILD_CLUSTER"
    )
    if reasons:
        return result
    resolved, receipts, used_anonymous, inferred_target, source_cell_alignment = solutions[0]
    receipts = [*legacy_intermediate_parent_receipts, *receipts]
    root_role = topology["parent"]["role"]
    family_result_role = compiled_specs["family_result_role"]
    mapping_roles = (
        []
        if compiled_specs["schema"]["family_root_mapping_policy"]
        == "REQUIRE_HIERARCHICALLY_RESOLVED_CONTEXT_ONLY"
        else [root_role]
    ) + [
        child["role"]
        for child in topology["children"]
        if child["role"] in compiled_specs["bindings"]
    ]
    mappings = []
    for role in mapping_roles:
        record = resolved.get(family_result_role if role == root_role else role)
        if record is None:
            continue
        mapping_values = partial_source_mapping_values_v1(record["cells"])
        if mapping_values is None:
            continue
        mapping = {
            "columns": canonical_clone_v1(money_columns),
            "hierarchy_path_exact": canonical_clone_v1(record["path"]),
            "label_exact": record["label_exact"],
            "report_norm_id": (
                compiled_specs["schema"]["family_report_norm_id"]
                if role == root_role
                else compiled_specs["bindings"][role]
            ),
            "role": role,
            "row_id": record["row_id"],
            "values": mapping_values,
        }
        if "derived_from_roles" in record:
            mapping["derived_from_roles"] = canonical_clone_v1(record["derived_from_roles"])
            mapping["derived_from_row_ids"] = canonical_clone_v1(record["derived_from_row_ids"])
        if "inferred_from_role" in record:
            mapping["inferred_from_role"] = record["inferred_from_role"]
        if record.get("label_match_mode") != "EXACT_NORMALIZED" and "label_match_mode" in record:
            mapping["label_match_mode"] = record["label_match_mode"]
        if record.get("percentage_companions"):
            mapping["percentage_companion_columns"] = canonical_clone_v1(
                [columns[index] for index in percent_indices]
            )
            mapping["percentage_companion_values"] = canonical_clone_v1(
                record["percentage_companions"]
            )
        mappings.append(mapping)
    mappings, mapping_normalization_receipts, mapping_normalization_reasons = (
        _apply_mapping_normalizations(
            mappings=mappings,
            resolved=resolved,
            narrative_evidence=narrative_mapping_evidence,
            compiled_specs=compiled_specs,
            money_columns=money_columns,
        )
    )
    mappings, presentation_binding_receipts, presentation_binding_reasons = (
        _apply_presentation_context_bindings(
            mappings=mappings,
            resolved=resolved,
            compiled_specs=compiled_specs,
            money_columns=money_columns,
        )
    )
    if mapping_normalization_reasons or presentation_binding_reasons:
        failed = _candidate_result(
            topology=topology,
            page_json_version_id=page_json_version_id,
            physical_page=physical_page,
            section_id=section_id,
            table_id=table_id,
            reasons=[*mapping_normalization_reasons, *presentation_binding_reasons],
        )
        failed["parent_binding_kind"] = result["parent_binding_kind"]
        return failed
    result["mappings"] = mappings
    source_role_label_matches = {
        role: {
            "label_exact": record["label_exact"],
            "match_mode": record["label_match_mode"],
            "row_id": record["row_id"],
        }
        for role, record in sorted(resolved.items())
        if record.get("label_match_mode") not in {None, "EXACT_NORMALIZED"}
    }
    has_incomplete_source_lane_equation = any(
        any("UNOBSERVED" in status for status in receipt["source_lane_equation_statuses"])
        for receipt in receipts
        if "source_lane_equation_statuses" in receipt
    )
    closure_receipt = {
        "equations": receipts,
        "family_root_mapping_policy": compiled_specs["schema"]["family_root_mapping_policy"],
        "inferred_ambiguous_provision_role": inferred_target,
        **(
            {"period_value_column_axis": period_value_axis_receipt}
            if period_value_axis_receipt is not None
            else {}
        ),
        "rule": (
            "EXACT_EXHAUSTIVE_GEMINI_JSON_RECURSIVE_DIRECT_FRONTIER_OBSERVED_LANES"
            if has_incomplete_source_lane_equation
            else "EXACT_EXHAUSTIVE_GEMINI_JSON_RECURSIVE_DIRECT_FRONTIER_ALL_LANES"
        ),
        "used_anonymous_result_row_ids": sorted(used_anonymous),
    }
    if leading_parent_population_receipts:
        closure_receipt["leading_parent_population_boundaries"] = canonical_clone_v1(
            leading_parent_population_receipts
        )
    if trailing_subtotal_population_receipts:
        closure_receipt["trailing_subtotal_population_boundaries"] = canonical_clone_v1(
            trailing_subtotal_population_receipts
        )
    if detached_root_frontier_receipt is not None:
        closure_receipt["detached_root_frontier"] = canonical_clone_v1(
            detached_root_frontier_receipt
        )
    if parent_title_match is not None:
        closure_receipt["parent_label_match"] = parent_title_match
    if parent_narrative_match is not None:
        closure_receipt["parent_narrative_binding"] = canonical_clone_v1(
            parent_narrative_match
        )
    if mapping_normalization_receipts:
        closure_receipt["mapping_normalizations"] = mapping_normalization_receipts
    if presentation_binding_receipts:
        closure_receipt["presentation_context_schema_bindings"] = presentation_binding_receipts
    if source_role_label_matches:
        closure_receipt["source_role_label_matches"] = source_role_label_matches
    if source_cell_alignment is not None:
        closure_receipt["source_cell_alignment_repair"] = canonical_clone_v1(
            source_cell_alignment
        )
    if external_context_receipt is not None:
        closure_receipt["external_structural_context"] = canonical_clone_v1(
            external_context_receipt
        )
    result["closure_receipt"] = closure_receipt
    return result
