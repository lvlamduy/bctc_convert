"""Recursive accounting closure over manifest-selected Gemini page JSON.

This module deliberately has no PDF/OCR/geometry dependency.  Gemini's exact
row labels, hierarchy paths, columns and raw cell strings are the source axis;
the declarative topology/equation/schema specs are the only semantic axis.
"""

from __future__ import annotations

import re
from collections import defaultdict
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
}
_SCHEMA_FORMATS = {
    "ACCOUNTING_FAMILY_SCHEMA_BINDING_SPEC_V4",
    "ACCOUNTING_FAMILY_SCHEMA_BINDING_SPEC_V5",
    "ACCOUNTING_FAMILY_SCHEMA_BINDING_SPEC_V6",
    "ACCOUNTING_FAMILY_SCHEMA_BINDING_SPEC_V7",
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


def _error(message: str) -> ValueError:
    from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
        GeminiJsonFlatAccountingFamilyV1Error,
    )

    return GeminiJsonFlatAccountingFamilyV1Error(message)


@lru_cache(maxsize=16384)
def _normalized(value: Any) -> str:
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


def _matches(value: Any, alias: str) -> bool:
    folded = _normalized(value)
    alias = _normalized(alias)
    forms = {folded, _without_leading_ordinal(folded)}
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
    return bool(suffixes) and all(
        suffix
        and (
            all(token in allowed_suffix_tokens for token in suffix.split())
            or (
                suffix.split()[:2] == ["thuyet", "minh"]
                and len(suffix.split()) > 2
                and all(token.isdigit() for token in suffix.split()[2:])
            )
        )
        for suffix in suffixes
    )


def _matcher_matches(value: Any, matcher: dict[str, Any]) -> bool:
    mode = matcher.get("match_mode", "EXACT_NORMALIZED")
    aliases = [_normalized(alias) for alias in matcher["aliases"]]
    if mode == "EXACT_NORMALIZED":
        return any(_matches(value, alias) for alias in aliases)
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
        return any(contains(form, alias) >= 0 for form in forms for alias in aliases)
    if mode == "CONTAINS_ORDERED_NORMALIZED_PHRASES":
        for form in forms:
            cursor = 0
            for alias in aliases:
                cursor = contains(form, alias, start=cursor)
                if cursor < 0:
                    break
            else:
                return True
        return False
    raise _error("Gemini JSON hierarchy matcher mode is invalid")


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
            "coefficient": 0,
            "source_text": None,
            "state": "BLANK_ZERO_IF_EQUATION_EXACT",
        }
    if type(value) is not str or not value.strip():
        raise _error("Gemini JSON hierarchy money cell is invalid")
    body = value.strip()
    if body in _DASHES:
        return {"coefficient": 0, "source_text": value, "state": "DASH_ZERO"}
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


def _header_date(value: str) -> date | None:
    for pattern in (_DATE_DMY, _DATE_WORDS):
        for match in pattern.finditer(value):
            try:
                return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
            except ValueError:
                continue
    # A slash date is interpreted as MDY only when it cannot be DMY: the
    # second field is a valid day above 12.  Ambiguous 01/02-style dates retain
    # the project's DMY authority and never reach this fallback.
    for match in _DATE_MDY.finditer(value):
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
    parsed: set[date] = set()
    for pattern in (_DATE_DMY, _DATE_WORDS):
        for match in pattern.finditer(value):
            try:
                parsed.add(date(int(match.group(3)), int(match.group(2)), int(match.group(1))))
            except ValueError:
                continue
    for match in _DATE_MDY.finditer(value):
        month = int(match.group(1))
        day = int(match.group(2))
        if day <= 12:
            continue
        try:
            parsed.add(date(int(match.group(3)), month, day))
        except ValueError:
            continue
    return parsed


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
    lane_alternatives = (
        evaluation_spec.get("expected_lane_unit_kind_alternatives")
        if type(evaluation_spec) is dict
        and evaluation_format
        in {
            "ACCOUNTING_FAMILY_EVALUATION_SPEC_V5",
            "ACCOUNTING_FAMILY_EVALUATION_SPEC_V6",
            "ACCOUNTING_FAMILY_EVALUATION_SPEC_V7",
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
        if type(raw_projection) is not dict or set(raw_projection) != expected_fields:
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
        topology_child_roles = {child["role"] for child in topology["children"]}
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
            != "ALLOW_ZERO_ONLY_WHEN_EXACT_TOTAL_EQUALS_OTHER_ROLE"
            or type(projected_roles) is not list
            or len(projected_roles) != 2
            or len(set(projected_roles)) != 2
            or any(role not in topology_child_roles for role in projected_roles)
            or type(blank_zero_derivable_roles) is not list
            or not blank_zero_derivable_roles
            or len(blank_zero_derivable_roles) != len(set(blank_zero_derivable_roles))
            or any(role not in projected_roles for role in blank_zero_derivable_roles)
        ):
            raise _error("Gemini JSON dual-axis projection policy is invalid")
        dual_axis_projection_policy = {
            **canonical_clone_v1(raw_projection),
            **normalized_alias_lists,
        }
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
            }:
                selection_policy = equation.get("component_selection_policy")
                variable_subset = (
                    evaluation_format
                    in {
                        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V5",
                        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V6",
                        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V7",
                    }
                    and selection_policy == "EXHAUSTIVE_VISIBLE_SUBSET_OF_DECLARED_POOL"
                )
                if evaluation_format in {
                    "ACCOUNTING_FAMILY_EVALUATION_SPEC_V5",
                    "ACCOUNTING_FAMILY_EVALUATION_SPEC_V6",
                    "ACCOUNTING_FAMILY_EVALUATION_SPEC_V7",
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
    if set(raw_aliases_by_role) != set(aliases_by_role):
        raise _error("Gemini JSON hierarchy raw query role axis drifted")
    anchor_groups = []
    query_anchor_groups = []
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
            query_anchor_groups.append(
                [topology_spec["parent"]["aliases"], raw_aliases_by_role[role]]
            )
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
        safe_query_groups: list[list[list[str]]] = []
        if all(raw_unscoped_aliases[role] for role in combination):
            safe_query_groups.append([raw_unscoped_aliases[role] for role in combination])
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
                if group not in safe_query_groups:
                    safe_query_groups.append(group)
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
            if group not in safe_query_groups:
                safe_query_groups.append(group)
        if safe_query_groups:
            # Keep qualified anchors separate from short contextual labels.
            # Contextual query modes include their declared owner as a distinct
            # anchor, so unrelated tables containing the same short pair do not
            # become unresolved family candidates.
            query_anchor_groups.extend(safe_query_groups)
        else:
            query_anchor_groups.append([raw_aliases_by_role[role] for role in combination])
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
        "query_aliases_by_role": canonical_clone_v1(raw_aliases_by_role),
        "query_anchor_alias_groups": canonical_clone_v1(query_anchor_groups),
        "query_parent_aliases": canonical_clone_v1(topology_spec["parent"]["aliases"]),
        "schema": canonical_clone_v1(schema_spec),
        "source_role_mapping_transforms": source_role_mapping_transforms,
        "topology": topology,
    }
    if evaluation_format == "ACCOUNTING_FAMILY_EVALUATION_SPEC_V7":
        compiled["dual_axis_projection_policy"] = dual_axis_projection_policy
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
) -> dict[str, str]:
    scoped: dict[str, list[str]] = defaultdict(list)
    unscoped: dict[str, list[str]] = defaultdict(list)
    for child in topology["children"]:
        role = child["role"]
        for matcher in child["matchers"]:
            if not _matcher_matches(row.get("label_exact"), matcher):
                continue
            within = matcher["within_role"]
            if within is None:
                unscoped[role].append(matcher.get("match_mode", "EXACT_NORMALIZED"))
            elif within == fallback_within_role or _path_has_role(
                row.get("hierarchy_path_exact"),
                aliases=aliases_by_role[within],
                label_exact=row.get("label_exact"),
            ):
                scoped[role].append(matcher.get("match_mode", "EXACT_NORMALIZED"))
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
    }
    return {role: max(selected[role], key=lambda mode: rank[mode]) for role in matches}


def _row_roles(
    row: dict[str, Any],
    *,
    topology: dict[str, Any],
    aliases_by_role: dict[str, list[str]],
    fallback_within_role: str | None = None,
) -> list[str]:
    return list(
        _row_role_match_modes(
            row,
            topology=topology,
            aliases_by_role=aliases_by_role,
            fallback_within_role=fallback_within_role,
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


def _coefficients(record: dict[str, Any]) -> list[int]:
    return [cell["coefficient"] for cell in record["cells"]]


def _sum(records: list[dict[str, Any]], lane_count: int) -> list[int]:
    return [sum(_coefficients(record)[lane] for record in records) for lane in range(lane_count)]


def _source_rounding_residuals(record: dict[str, Any], component_sums: list[int]) -> list[int]:
    return [
        observed - computed
        for observed, computed in zip(_coefficients(record), component_sums, strict=True)
    ]


def _carrier_matches_source_sum(
    record: dict[str, Any],
    component_sums: list[int],
    *,
    maximum_rounding_residual: int,
) -> bool:
    return all(
        abs(residual) <= maximum_rounding_residual
        for residual in _source_rounding_residuals(record, component_sums)
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
            if subtotal_components and _sum(subtotal_components, lane_count) == _coefficients(
                resolved[total_role]
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
                sums,
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
                    sums,
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
                    record["row_id"] not in used_anonymous
                    and not (
                        compiled["evaluation"]["format_version"]
                        in {
                            "ACCOUNTING_FAMILY_EVALUATION_SPEC_V5",
                            "ACCOUNTING_FAMILY_EVALUATION_SPEC_V6",
                            "ACCOUNTING_FAMILY_EVALUATION_SPEC_V7",
                        }
                        and record.get("owner_role") == topology["parent"]["role"]
                        and result_role != family_result_role
                        and "allowed_result_roles" not in record
                    )
                    and (
                        record["ordinal"] > maximum_component_ordinal
                        or record.get("presentation_shadow_for_role") == result_role
                    )
                    and _carrier_matches_source_sum(
                        record,
                        sums,
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
                    and _coefficients(record) == _coefficients(existing)
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
        lane_specific_frontiers = []
        lane_carrier = (
            next(iter(declared_result_carriers.values()))
            if len(declared_result_carriers) == 1
            else None
        )
        if len(alternatives) != 1 and lane_carrier is not None:
            for lane in range(lane_count):
                lane_candidates = {}
                for alternative in equation["component_role_alternatives"]:
                    declared = set(alternative["component_roles"])
                    lane_roles = [
                        role
                        for role in alternative["component_roles"]
                        if role in lane_direct_visible
                    ]
                    if (
                        len(lane_roles) < alternative["minimum_component_count"]
                        or sum(role_kinds.get(role) == "ADDITIVE_CHILD" for role in lane_roles)
                        < alternative["minimum_additive_child_count"]
                        or not set(lane_roles) <= declared
                    ):
                        continue
                    lane_components = [resolved[role] for role in lane_roles]
                    if (
                        lane_carrier not in base_by_role.values()
                        and lane_components
                        and lane_carrier["ordinal"]
                        <= max(component["ordinal"] for component in lane_components)
                    ):
                        continue
                    if (
                        sum(
                            component["cells"][lane]["coefficient"] for component in lane_components
                        )
                        != lane_carrier["cells"][lane]["coefficient"]
                    ):
                        continue
                    key = (
                        tuple(lane_roles),
                        tuple(component["row_id"] for component in lane_components),
                    )
                    lane_candidates[key] = (lane_roles, lane_components)
                if len(lane_candidates) != 1:
                    lane_specific_frontiers = []
                    break
                lane_specific_frontiers.append(next(iter(lane_candidates.values())))
        if len(lane_specific_frontiers) == lane_count:
            selected_roles_by_lane = [roles for roles, _components in lane_specific_frontiers]
            components_by_lane = [components for _roles, components in lane_specific_frontiers]
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
                    "lane_component_sums": _coefficients(lane_carrier),
                    "mode": "VISIBLE_RESULT_EXACTLY_CORROBORATED_BY_LANE_SPECIFIC_FRONTIERS",
                    "result_coefficients": _coefficients(lane_carrier),
                    "result_role": result_role,
                    "result_row_id": lane_carrier["row_id"],
                }
            )
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
            source_rounding_residuals: list[int] = []
            result = {
                "cells": [
                    {
                        "coefficient": coefficient,
                        "source_text": None,
                        "state": "DERIVED_EXACT_RECURSIVE_DIRECT_FRONTIER",
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
            mode = "DERIVED_FROM_EXHAUSTIVE_VISIBLE_COMPONENTS"
        else:
            result = {**carrier, "owner_role": None, "role": result_role}
            source_rounding_residuals = _source_rounding_residuals(carrier, sums)
            if carrier["row_id"].startswith("r") and carrier not in base_by_role.values():
                used_anonymous.add(carrier["row_id"])
            used_anonymous.update(result.get("corroborating_result_row_ids", []))
            mode = (
                "VISIBLE_RESULT_EXACTLY_CORROBORATED"
                if not any(source_rounding_residuals)
                else "VISIBLE_RESULT_CORROBORATED_WITH_BOUNDED_SOURCE_ROUNDING_RESIDUAL"
            )
        resolved[result_role] = result
        equations_receipt.append(
            {
                "component_roles": selected_roles,
                "component_row_ids": [component["row_id"] for component in components],
                "lane_component_sums": sums,
                "mode": mode,
                "result_coefficients": _coefficients(result),
                "result_role": result_role,
                "result_row_id": result["row_id"],
                **(
                    {"source_rounding_residual_coefficients": source_rounding_residuals}
                    if any(source_rounding_residuals)
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
            }
        )
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


def _intermediate_parent_subtotal_receipts(
    *,
    candidates: list[dict[str, Any]],
    records_by_role: dict[str, list[dict[str, Any]]],
    anonymous: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
    topology: dict[str, Any],
    unmatched_numeric_ordinals: set[int],
    lane_count: int,
) -> list[dict[str, Any]]:
    """Corroborate one visible parent subtotal without promoting it to the root.

    Some source tables print the family label twice at different accounting
    levels: first as the subtotal of one contiguous direct-child block, then
    as an unlabeled grand total after a second structural group.  The first
    row is presentation evidence, not another component and not the family
    root.  This primitive consumes it only when the local source interval is
    exhaustive and every money lane sums exactly.
    """

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
                and not _normalized(source_rows[record["ordinal"] - 1].get("label_exact"))
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
        or _sum(components, lane_count) != _coefficients(candidate)
    ):
        return []
    return [
        {
            "component_roles": component_roles,
            "component_row_ids": [record["row_id"] for record in components],
            "lane_component_sums": _coefficients(candidate),
            "mode": "VISIBLE_INTERMEDIATE_PARENT_SUBTOTAL_EXACTLY_CORROBORATED_BY_CONTIGUOUS_DIRECT_CHILDREN",
            "result_coefficients": _coefficients(candidate),
            "result_role": parent_role,
            "result_row_id": candidate["row_id"],
            "source_interval_ordinals": [candidate["ordinal"], boundary - 1],
        }
    ]


def _mapping_from_source_record(
    *,
    record: dict[str, Any],
    role: str,
    report_norm_id: int,
    money_columns: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "columns": canonical_clone_v1(money_columns),
        "hierarchy_path_exact": canonical_clone_v1(record.get("path", [])),
        "label_exact": record.get("label_exact"),
        "report_norm_id": report_norm_id,
        "role": role,
        "row_id": record["row_id"],
        "values": canonical_clone_v1(record["cells"]),
    }


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
        observed_inclusive = [cell["coefficient"] for cell in inclusive["values"]]
        source_values = _coefficients(source)
        normalized_values = [
            observed - source_value
            for observed, source_value in zip(observed_inclusive, source_values, strict=True)
        ]
        inclusive["values"] = [
            {
                "coefficient": coefficient,
                "source_text": None,
                "state": "DERIVED_EXACT_SOURCE_MAPPING_NORMALIZATION",
            }
            for coefficient in normalized_values
        ]
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
        observed_root = [cell["coefficient"] for cell in root["values"]]
        source_values = _coefficients(evidence)
        normalized_root = [
            observed + source_value
            for observed, source_value in zip(observed_root, source_values, strict=True)
        ]
        root["values"] = [
            {
                "coefficient": coefficient,
                "source_text": None,
                "state": "DERIVED_EXACT_SOURCE_MAPPING_NORMALIZATION",
            }
            for coefficient in normalized_root
        ]
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
    missing_date_indices = [index for index, value in enumerate(table_dates) if value is None]
    if len(missing_date_indices) == 1:
        section_dates = _header_dates(str(section.get("title_exact") or ""))
        missing_candidates = section_dates - {value for value in table_dates if value is not None}
        if len(missing_candidates) == 1:
            missing_index = missing_date_indices[0]
            table_dates[missing_index] = next(iter(missing_candidates))
            table_date_sources[missing_index] = "SECTION_TITLE_UNIQUE_MISSING_PERIOD"
    if any(value is None for value in table_dates) or len(set(table_dates)) != 2:
        return None
    ordered = sorted(
        zip(table_dates, table_date_sources, table_ids, source_tables, strict=True),
        key=lambda item: item[0],
        reverse=True,
    )
    projected_by_period: list[dict[str, Any]] = []
    for period_date, date_source, source_table_id, table in ordered:
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
            component_sum = sum(_money(record["source_value"])["coefficient"] for record in records)
            if total_rows and _money(total_rows[0][2])["coefficient"] != component_sum:
                return None
        except ValueError:
            return None
        projected_by_period.append(
            {
                "column": columns[target_index],
                "date": period_date,
                "date_source": date_source,
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
) -> dict[str, Any]:
    """Evaluate one local Gemini table with an exact recursive equation DAG."""

    from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import _candidate_result

    topology = compiled_specs["topology"]
    reasons: list[str] = []
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
    if any(_normalized(alias) in title_folded for alias in topology["hard_negative_aliases"]):
        reasons.append("HARD_NEGATIVE_FAMILY_TITLE_PRESENT")
    parent_in_title = any(
        _normalized(alias) in title_folded for alias in topology["parent"]["aliases"]
    )
    parent_title_match = (
        None
        if parent_in_title
        else _bounded_one_character_parent_title_match(title, topology["parent"]["aliases"])
    )
    columns = table.get("columns")
    period_value_axis_receipt = None
    percent_indices: list[int] = []
    if compiled_specs["evaluation"]["format_version"] in {
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V5",
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V6",
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V7",
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
    parent_row_ordinals = [
        ordinal
        for ordinal, row in enumerate(source_rows, start=1)
        if any(_matches(row.get("label_exact"), alias) for alias in topology["parent"]["aliases"])
    ]
    explicit_parent_visible = (
        parent_in_title or parent_title_match is not None or len(parent_row_ordinals) == 1
    )
    if not parent_in_title and len(parent_row_ordinals) == 1:
        parent_ordinal = parent_row_ordinals[0]
        rows = [
            (ordinal, row)
            for ordinal, row in enumerate(source_rows, start=1)
            if ordinal == parent_ordinal
            or _path_has_role(
                row.get("hierarchy_path_exact"),
                aliases=topology["parent"]["aliases"],
                label_exact=row.get("label_exact"),
            )
        ]
    else:
        rows = list(enumerate(source_rows, start=1))
    structural_roles = {
        child["role"] for child in topology["children"] if child["role_kind"] == "STRUCTURAL_GROUP"
    }
    records_by_role: dict[str, list[dict[str, Any]]] = defaultdict(list)
    anonymous: list[dict[str, Any]] = []
    intermediate_parent_subtotal_candidates: list[dict[str, Any]] = []
    unmatched_numeric: list[int] = []
    unrelated_group_labels: set[str] = set()
    active_structural_role: str | None = None
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
        role_match_modes = _row_role_match_modes(
            row,
            topology=topology,
            aliases_by_role=compiled_specs["aliases_by_role"],
            fallback_within_role=active_structural_role,
        )
        roles = list(role_match_modes)
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
            or (row.get("row_kind") == "TOTAL" and not _normalized(row.get("label_exact")))
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
                owner is None
                and row.get("row_kind") == "SUBTOTAL"
                and compiled_specs["evaluation"]["format_version"]
                in {
                    "ACCOUNTING_FAMILY_EVALUATION_SPEC_V5",
                    "ACCOUNTING_FAMILY_EVALUATION_SPEC_V6",
                    "ACCOUNTING_FAMILY_EVALUATION_SPEC_V7",
                }
            ):
                record["allowed_result_roles"] = {
                    equation["result_role"]
                    for equation in compiled_specs["equations"]
                    if equation["result_role"] != compiled_specs["family_result_role"]
                }
            anonymous.append(record)
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
            _coefficients(primary[0]) != _coefficients(shadow)
            or not descendants
            or _sum(descendants, lane_count) != _coefficients(shadow)
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
    for role, records in records_by_role.items():
        if len(records) > 1:
            reasons.append(f"ROLE_OCCURRENCE_COUNT_ABOVE_ONE:{role}:{len(records)}")
    base = {role: records[0] for role, records in records_by_role.items() if len(records) == 1}
    intermediate_parent_receipts = _intermediate_parent_subtotal_receipts(
        candidates=intermediate_parent_subtotal_candidates,
        records_by_role=records_by_role,
        anonymous=anonymous,
        source_rows=source_rows,
        topology=topology,
        unmatched_numeric_ordinals=set(unmatched_numeric),
        lane_count=lane_count,
    )
    if intermediate_parent_subtotal_candidates and not intermediate_parent_receipts:
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
    solutions = []
    solution_failures: list[str] = []
    for target in targets:
        resolved, receipts, local_reasons, used = _solve(
            base_by_role=base,
            anonymous=anonymous,
            compiled=compiled_specs,
            ambiguous_provision_target=target,
            lane_count=lane_count,
        )
        if not local_reasons:
            solutions.append((resolved, receipts, used, target))
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
        "EXPLICIT_SECTION_OR_TABLE_TITLE"
        if parent_in_title
        else "ONE_EDIT_SECTION_OR_TABLE_PARENT_TITLE_WITH_EXACT_GRAPH"
        if parent_title_match is not None
        else "EXPLICIT_PARENT_ROW"
        if len(parent_row_ordinals) == 1
        else "UNIQUE_REQUIRED_CHILD_CLUSTER"
    )
    if reasons:
        return result
    resolved, receipts, used_anonymous, inferred_target = solutions[0]
    receipts = [*intermediate_parent_receipts, *receipts]
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
            "values": canonical_clone_v1(record["cells"]),
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
    if mapping_normalization_reasons:
        failed = _candidate_result(
            topology=topology,
            page_json_version_id=page_json_version_id,
            physical_page=physical_page,
            section_id=section_id,
            table_id=table_id,
            reasons=mapping_normalization_reasons,
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
    closure_receipt = {
        "equations": receipts,
        "family_root_mapping_policy": compiled_specs["schema"]["family_root_mapping_policy"],
        "inferred_ambiguous_provision_role": inferred_target,
        **(
            {"period_value_column_axis": period_value_axis_receipt}
            if period_value_axis_receipt is not None
            else {}
        ),
        "rule": "EXACT_EXHAUSTIVE_GEMINI_JSON_RECURSIVE_DIRECT_FRONTIER_ALL_LANES",
        "used_anonymous_result_row_ids": sorted(used_anonymous),
    }
    if parent_title_match is not None:
        closure_receipt["parent_label_match"] = parent_title_match
    if mapping_normalization_receipts:
        closure_receipt["mapping_normalizations"] = mapping_normalization_receipts
    if source_role_label_matches:
        closure_receipt["source_role_label_matches"] = source_role_label_matches
    result["closure_receipt"] = closure_receipt
    return result
