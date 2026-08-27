"""Pure structural-context projection over selected Gemini page JSON.

The immutable SQLite query and the public evaluator both call this primitive.
It has no database, OCR, geometry, bank, filename, or page-routing behavior.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.evaluation.gemini_financial_page_json_v1 import normalize_search_text_v1
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

FORMAT_VERSION = "GEMINI_JSON_STRUCTURAL_CONTEXT_RESOLUTION_V1"
_SECTION_ID = re.compile(r"s[1-9][0-9]*\Z")
_TABLE_ID = re.compile(r"t[1-9][0-9]*\Z")
_PAGE_JSON_VERSION_ID = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")


class GeminiJsonStructuralContextV1Error(ValueError):
    """The selected context page axis or declared policy is invalid."""


def _error(message: str) -> GeminiJsonStructuralContextV1Error:
    return GeminiJsonStructuralContextV1Error(message)


def family_anchor_lookup_forms_v1(aliases: Sequence[str]) -> list[str]:
    """Bind semantic aliases to exact row labels with harmless list markers."""

    folded = {normalize_search_text_v1(alias)["text_ascii_folded"] for alias in aliases}
    comma_forms = {
        " ".join(tokens[:ordinal]) + ", " + " ".join(tokens[ordinal:])
        for alias in folded
        for tokens in [alias.split()]
        for ordinal in range(1, len(tokens))
    }
    internal_separator_forms = {
        " ".join(tokens[:ordinal]) + f" {separator} " + " ".join(tokens[ordinal:])
        for alias in folded
        for tokens in [alias.split()]
        for ordinal in range(1, len(tokens))
        for separator in ("-", "–", "—", "•")
    }
    punctuation_forms = (
        set(folded)
        | {alias + ":" for alias in folded}
        | {alias + " (*)" for alias in folded}
        | comma_forms
        | internal_separator_forms
    )
    combined_comma_footnote_forms = {
        alias + separator + marker
        for alias in comma_forms
        for separator in ("", " ")
        for marker in ("(*)", "(**)", "(***)")
    }
    punctuation_forms |= {
        alias + separator + marker
        for alias in folded
        for separator in ("", " ")
        for marker in ("(*)", "(**)", "(***)")
    }
    punctuation_forms |= {
        alias.replace("tien vang ", "tien, vang ", 1)
        for alias in punctuation_forms
        if alias.startswith("tien vang ")
    }
    punctuation_forms |= {
        alias.replace(" tctd ", marker, 1)
        for alias in punctuation_forms
        if " tctd " in alias
        for marker in (' ("tctd") ', " (“tctd”) ", " (tctd) ")
    }
    for alias in folded:
        stem, separator, suffix = alias.rpartition(" ")
        if separator and (suffix.isdigit() or suffix in {"i", "ii", "iii", "iv", "v"}):
            punctuation_forms.add(f"{stem} ({suffix})")
        if " bang " in alias:
            prefix, value_kind = alias.rsplit(" bang ", maxsplit=1)
            punctuation_forms.update(
                f"{prefix} {marker} bang {value_kind}" for marker in ("-", "–", "—", "•")
            )
    ordinal_prefixes = {
        *(str(value) for value in range(1, 21)),
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
    return sorted(
        punctuation_forms
        | combined_comma_footnote_forms
        | {marker + alias for alias in punctuation_forms for marker in ("- ", "– ", "— ", "• ")}
        | {prefix + " " + alias for alias in punctuation_forms for prefix in ordinal_prefixes}
        | {prefix + ". " + alias for alias in punctuation_forms for prefix in ordinal_prefixes}
    )


def declared_surface_alias_match_v1(value: Any, aliases: Sequence[str]) -> str | None:
    """Return the unique longest declared phrase on one authenticated surface."""

    if type(value) is not str or not value.strip():
        return None
    folded = normalize_search_text_v1(value)["text_ascii_folded"]
    padded = f" {folded} "
    matches = []
    for alias in aliases:
        normalized = normalize_search_text_v1(alias)["text_ascii_folded"]
        if normalized and f" {normalized} " in padded:
            matches.append((len(normalized.split()), len(normalized), normalized, alias))
    if not matches:
        return None
    best_rank = max(match[:2] for match in matches)
    best = {
        (normalized, alias)
        for tokens, length, normalized, alias in matches
        if (tokens, length) == best_rank
    }
    return next(iter(best))[1] if len(best) == 1 else None


def _table_surfaces_v1(
    page_json: Mapping[str, Any],
    *,
    section_id: str,
    table_id: str,
    include_narratives: bool,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    try:
        section_ordinal = int(section_id[1:])
        table_ordinal = int(table_id[1:])
        sections = page_json["sections"]
        section = sections[section_ordinal - 1]
        tables = section["tables"]
        table = tables[table_ordinal - 1]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise _error("selected title-axis table identity is invalid") from exc
    if (
        type(sections) is not list
        or type(section) is not dict
        or type(tables) is not list
        or type(table) is not dict
        or not 1 <= section_ordinal <= len(sections)
        or not 1 <= table_ordinal <= len(tables)
    ):
        raise _error("selected title-axis table identity is invalid")
    surfaces: list[dict[str, Any]] = []
    if type(section.get("title_exact")) is str and section["title_exact"]:
        surfaces.append({"source_kind": "SECTION_TITLE", "source_exact": section["title_exact"]})
    if type(table.get("title_exact")) is str and table["title_exact"]:
        surfaces.append({"source_kind": "TABLE_TITLE", "source_exact": table["title_exact"]})
    narratives = section.get("narratives_exact", [])
    if type(narratives) is not list or any(type(value) is not str for value in narratives):
        raise _error("selected title-axis narratives are invalid")
    if include_narratives:
        surfaces.extend(
            {
                "source_kind": "SECTION_NARRATIVE",
                "source_exact": value,
                "narrative_ordinal": ordinal,
            }
            for ordinal, value in enumerate(narratives, start=1)
            if value
        )
    return section, table, surfaces


def resolve_candidate_structural_context_v1(
    *,
    candidate_document_id: str,
    candidate_source_logical_name: str,
    candidate_source_sha256: str,
    candidate_page_json_version_id: str,
    candidate_page_json: Mapping[str, Any],
    candidate_physical_page: int,
    candidate_section_id: str,
    candidate_table_id: str,
    context_page_records: Sequence[Mapping[str, Any]],
    structural_branch_role: str,
    structural_branch_aliases: Sequence[str],
    structural_surface_kinds: Sequence[str],
    explicit_parent_role: str,
    explicit_parent_aliases: Sequence[str],
    hard_negative_aliases: Sequence[str],
    owner_reset_aliases: Sequence[str],
    adjacent_page_radius: int,
) -> dict[str, Any]:
    """Resolve one row-qualified table's local branch and bounded owner."""

    if (
        type(candidate_document_id) is not str
        or not candidate_document_id
        or type(candidate_source_logical_name) is not str
        or not candidate_source_logical_name
        or type(candidate_source_sha256) is not str
        or len(candidate_source_sha256) != 64
        or any(character not in "0123456789abcdef" for character in candidate_source_sha256)
        or type(candidate_page_json_version_id) is not str
        or _PAGE_JSON_VERSION_ID.fullmatch(candidate_page_json_version_id) is None
        or type(candidate_page_json) is not dict
        or type(candidate_physical_page) is not int
        or candidate_physical_page < 1
        or type(candidate_section_id) is not str
        or _SECTION_ID.fullmatch(candidate_section_id) is None
        or type(candidate_table_id) is not str
        or _TABLE_ID.fullmatch(candidate_table_id) is None
        or type(context_page_records) not in {list, tuple}
        or not context_page_records
        or type(structural_branch_role) is not str
        or not structural_branch_role
        or type(explicit_parent_role) is not str
        or not explicit_parent_role
        or tuple(structural_surface_kinds) not in {("TITLE",), ("TITLE", "SECTION_NARRATIVE")}
        or type(adjacent_page_radius) is not int
        or not 0 <= adjacent_page_radius <= 2
        or any(
            type(values) not in {list, tuple}
            or not values
            or any(type(value) is not str or not value.strip() for value in values)
            for values in (
                structural_branch_aliases,
                explicit_parent_aliases,
                hard_negative_aliases,
                owner_reset_aliases,
            )
        )
    ):
        raise _error("selected title-axis context request is invalid")
    records: list[dict[str, Any]] = []
    versions: set[str] = set()
    pages: set[int] = set()
    for source in context_page_records:
        if (
            type(source) is not dict
            or source.get("document_id") != candidate_document_id
            or source.get("source_logical_name") != candidate_source_logical_name
            or source.get("source_sha256") != candidate_source_sha256
            or type(source.get("page_json_version_id")) is not str
            or _PAGE_JSON_VERSION_ID.fullmatch(source["page_json_version_id"]) is None
            or type(source.get("physical_page")) is not int
            or not 0 <= candidate_physical_page - source["physical_page"] <= adjacent_page_radius
            or type(source.get("page_json")) is not dict
            or source["page_json_version_id"] in versions
            or source["physical_page"] in pages
        ):
            raise _error("selected title-axis context page axis is invalid")
        versions.add(source["page_json_version_id"])
        pages.add(source["physical_page"])
        records.append(dict(source))
    if records != sorted(records, key=lambda record: record["physical_page"]):
        raise _error("selected title-axis context page order or source is invalid")
    candidate = [
        record
        for record in records
        if record["page_json_version_id"] == candidate_page_json_version_id
        and record["physical_page"] == candidate_physical_page
    ]
    if len(candidate) != 1 or candidate[0]["page_json"] != candidate_page_json:
        raise _error("selected title-axis candidate page is absent")
    page_json = candidate_page_json
    include_narratives = "SECTION_NARRATIVE" in structural_surface_kinds
    _section, table, local_surfaces = _table_surfaces_v1(
        page_json,
        section_id=candidate_section_id,
        table_id=candidate_table_id,
        include_narratives=include_narratives,
    )

    def first_evidence(
        surfaces: Sequence[Mapping[str, Any]], aliases: Sequence[str]
    ) -> dict[str, Any] | None:
        for surface in surfaces:
            alias = declared_surface_alias_match_v1(surface["source_exact"], aliases)
            if alias is not None:
                return {**surface, "alias": alias}
        return None

    def all_evidence(
        surfaces: Sequence[Mapping[str, Any]], aliases: Sequence[str]
    ) -> list[dict[str, Any]]:
        return [
            {**surface, "alias": alias}
            for surface in surfaces
            if (alias := declared_surface_alias_match_v1(surface["source_exact"], aliases))
            is not None
        ]

    def located(evidence: dict[str, Any] | None) -> dict[str, Any] | None:
        if evidence is None:
            return None
        return {
            **evidence,
            "page_json_version_id": candidate_page_json_version_id,
            "physical_page": candidate_physical_page,
            "section_id": candidate_section_id,
            "table_id": candidate_table_id,
        }

    local_negative = located(first_evidence(local_surfaces, hard_negative_aliases))
    branch = located(first_evidence(local_surfaces, structural_branch_aliases))
    base = {
        "branch_evidence": branch,
        "format_version": FORMAT_VERSION,
        "hard_negative_evidence": local_negative,
        "owner_evidence": None,
        "owner_failure_reason": None,
        "owner_mode": None,
        "reset_evidence": None,
        "rule": "CANDIDATE_LOCAL_BRANCH_THEN_LOCAL_OR_BOUNDED_PRECEDING_OWNER",
    }
    if local_negative is not None:
        return {**base, "disposition": "HARD_NEGATIVE_VETO"}

    local_surface_owners = all_evidence(local_surfaces, explicit_parent_aliases)
    branch_owner_surfaces = [
        owner
        for owner in local_surface_owners
        if branch is not None
        and all(
            owner.get(key) == branch.get(key)
            for key in ("source_kind", "source_exact", "narrative_ordinal")
        )
    ]
    # A branch phrase may itself include the family owner phrase.  That one
    # candidate-local surface is the most specific owner and a repeated note
    # heading is corroborative, not a second population.  Multiple independent
    # title/narrative owners remain ambiguous and never fall through to carry.
    if len(branch_owner_surfaces) == 1:
        local_surface_owners = branch_owner_surfaces
    elif len(local_surface_owners) > 1:

        def owner_surface_rank(evidence: Mapping[str, Any]) -> int:
            source = normalize_search_text_v1(evidence["source_exact"])["text_ascii_folded"]
            alias = normalize_search_text_v1(evidence["alias"])["text_ascii_folded"]
            tokens = source.split()
            if len(tokens) > 1 and (
                tokens[0].rstrip(".:)").isdigit()
                or tokens[0].rstrip(".:)")
                in {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"}
            ):
                source = " ".join(tokens[1:])
            return int(source == alias)

        best_rank = max(owner_surface_rank(evidence) for evidence in local_surface_owners)
        local_surface_owners = [
            evidence
            for evidence in local_surface_owners
            if owner_surface_rank(evidence) == best_rank
        ]
    if len(local_surface_owners) > 1:
        return {
            **base,
            "disposition": ("OWNER_ABSENT_OR_AMBIGUOUS" if branch is not None else "BRANCH_ABSENT"),
            "owner_failure_reason": "MULTIPLE_LOCAL_EXPLICIT_OWNER_SURFACES",
        }
    owner = located(local_surface_owners[0] if local_surface_owners else None)
    if owner is None:
        row_forms = set(family_anchor_lookup_forms_v1(explicit_parent_aliases))
        rows = table.get("rows")
        if type(rows) is not list:
            raise _error("selected title-axis owner row axis is invalid")
        owner_rows = [
            (ordinal, row)
            for ordinal, row in enumerate(rows, start=1)
            if type(row) is dict
            and type(row.get("label_exact")) is str
            and normalize_search_text_v1(row["label_exact"])["text_ascii_folded"] in row_forms
        ]
        if len(owner_rows) > 1:
            return {
                **base,
                "disposition": (
                    "OWNER_ABSENT_OR_AMBIGUOUS" if branch is not None else "BRANCH_ABSENT"
                ),
                "owner_failure_reason": "MULTIPLE_LOCAL_EXPLICIT_OWNER_ROWS",
            }
        if len(owner_rows) == 1:
            ordinal, row = owner_rows[0]
            owner = located(
                {
                    "alias": row["label_exact"],
                    "row_id": f"r{ordinal}",
                    "source_exact": row["label_exact"],
                    "source_kind": "ROW_LABEL",
                }
            )
    owner_mode = "LOCAL_EXPLICIT_OWNER" if owner is not None else None
    reset_evidence = None
    if owner is None:
        candidate_section_ordinal = int(candidate_section_id[1:])
        candidate_table_ordinal = int(candidate_table_id[1:])
        prior_tables = []
        for record in records:
            page_distance = candidate_physical_page - record["physical_page"]
            if not 0 <= page_distance <= adjacent_page_radius:
                raise _error("selected title-axis context page is outside the bounded axis")
            sections = record["page_json"].get("sections")
            if type(sections) is not list:
                raise _error("selected title-axis context section axis is invalid")
            for section_ordinal, context_section in enumerate(sections, start=1):
                tables = context_section.get("tables") if type(context_section) is dict else None
                if type(tables) is not list:
                    raise _error("selected title-axis context table axis is invalid")
                for table_ordinal, _table in enumerate(tables, start=1):
                    if page_distance == 0 and (
                        section_ordinal > candidate_section_ordinal
                        or (
                            section_ordinal == candidate_section_ordinal
                            and table_ordinal >= candidate_table_ordinal
                        )
                    ):
                        continue
                    prior_tables.append(
                        (
                            (
                                page_distance,
                                0
                                if page_distance == 0
                                and section_ordinal == candidate_section_ordinal
                                else 1,
                                -section_ordinal,
                                -table_ordinal,
                            ),
                            record,
                            f"s{section_ordinal}",
                            f"t{table_ordinal}",
                        )
                    )
        for _priority, record, prior_section_id, prior_table_id in sorted(
            prior_tables, key=lambda item: item[0]
        ):
            _prior_section, _prior_table, prior_surfaces = _table_surfaces_v1(
                record["page_json"],
                section_id=prior_section_id,
                table_id=prior_table_id,
                include_narratives=False,
            )
            reset = first_evidence(prior_surfaces, owner_reset_aliases)
            if reset is not None:
                reset_evidence = {
                    **reset,
                    "page_json_version_id": record["page_json_version_id"],
                    "physical_page": record["physical_page"],
                    "section_id": prior_section_id,
                    "table_id": prior_table_id,
                }
                break
            prior_owner = first_evidence(prior_surfaces, explicit_parent_aliases)
            if prior_owner is not None:
                owner = {
                    **prior_owner,
                    "page_json_version_id": record["page_json_version_id"],
                    "physical_page": record["physical_page"],
                    "section_id": prior_section_id,
                    "table_id": prior_table_id,
                }
                owner_mode = "BOUNDED_PRECEDING_SELECTED_PAGE_OWNER_CARRY"
                break
    if owner is None:
        owner_failure_reason = (
            "POPULATION_RESET_BEFORE_OWNER"
            if reset_evidence is not None
            else "NO_BOUNDED_PRECEDING_OWNER"
        )
        return {
            **base,
            "disposition": ("OWNER_ABSENT_OR_AMBIGUOUS" if branch is not None else "BRANCH_ABSENT"),
            "owner_failure_reason": owner_failure_reason,
            "reset_evidence": reset_evidence,
        }
    if branch is None:
        return {
            **base,
            "disposition": "BRANCH_ABSENT",
            "owner_evidence": owner,
            "owner_mode": owner_mode,
            "reset_evidence": reset_evidence,
        }
    context_axis = [
        {
            "document_id": candidate_document_id,
            "page_json_sha256": canonical_json_sha256_v1(record["page_json"]),
            "page_json_version_id": record["page_json_version_id"],
            "physical_page": record["physical_page"],
            "source_logical_name": candidate_source_logical_name,
            "source_sha256": candidate_source_sha256,
        }
        for record in records
    ]
    receipt = {
        "branch_evidence": branch,
        "branch_role": structural_branch_role,
        "candidate_page_json_version_id": candidate_page_json_version_id,
        "candidate_section_id": candidate_section_id,
        "candidate_table_id": candidate_table_id,
        "context_page_axis_sha256": canonical_json_sha256_v1(context_axis),
        "owner_evidence": owner,
        "owner_mode": owner_mode,
        "owner_role": explicit_parent_role,
        "rule": "ROW_QUALIFIED_CANDIDATE_LOCAL_BRANCH_AND_BOUNDED_PRECEDING_OWNER",
    }
    return {
        **base,
        "disposition": "ACCEPTED",
        "owner_evidence": owner,
        "owner_mode": owner_mode,
        "structural_context_receipt": receipt,
    }
