"""Customer-deposit multi-view accounting closure over selected Gemini JSON.

The engine is bank/file/page blind.  It accepts the two source presentations
observed in the corpus (one row-oriented two-period table, or two stacked
period tables with VND/foreign/total columns), optionally joins a customer-type
view inside the same owner/reset fence, and derives all schema mappings from
source rows plus exact accounting closure.  Gemini is not asked to construct
roles, equations, or a graph.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from bctc_ai.evaluation.accounting_family_topology_v1 import (
    compile_accounting_family_topology_spec_v1,
)
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import (
    _COMPARATIVE_PERIOD_ALIASES,
    _CURRENT_PERIOD_ALIASES,
    _header_dates,
    _header_text,
    _money,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

ENGINE_FORMAT_VERSION = "GEMINI_JSON_CUSTOMER_DEPOSIT_ACCOUNTING_FAMILY_V1"
INDEXED_QUERY_EVIDENCE_FORMAT_VERSION = "GEMINI_JSON_INDEXED_CUSTOMER_DEPOSIT_QUERY_EVIDENCE_V1"
EVALUATION_FORMAT_VERSION = "ACCOUNTING_CUSTOMER_DEPOSIT_FAMILY_EVALUATION_SPEC_V1"
SCHEMA_FORMAT_VERSION = "ACCOUNTING_CUSTOMER_DEPOSIT_SCHEMA_BINDING_SPEC_V1"
READY = "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
NOT_OBSERVED = "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
UNRESOLVED = "UNRESOLVED_GEMINI_JSON_FAMILY"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_DECLARATIVE_CUSTOMER_DEPOSIT_OWNER_RESET_"
    "FENCE_ROW_PERIOD_OR_STACKED_PERIOD_CURRENCY_LAYOUT_OPTIONAL_CUSTOMER_VIEW_"
    "EXACT_PERIOD_UNIT_HIERARCHY_TOTAL_AND_CHILD_CLOSURE_CONDITIONAL_BLANK_ZERO_"
    "STRUCTURAL_ROOT_SCHEMA_MAPPING_PROPOSAL_ONLY_NO_GEOMETRY_OCR_BANK_FILE_PAGE_"
    "NOTE_ROUTING_BACKSOLVE_CANONICAL_OR_EXPORT_AUTHORITY"
)

_PAGE_VERSION = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_DOCUMENT_ID = re.compile(r"gfpstorev1:document:[0-9a-f]{64}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SECTION_ID = re.compile(r"s[1-9][0-9]*\Z")
_TABLE_ID = re.compile(r"t[1-9][0-9]*\Z")

_TYPE_SOURCE_ROLES = (
    "NO_TERM",
    "TERM",
    "SAVINGS_NO_TERM",
    "SAVINGS_TERM",
    "ESCROW",
    "DEDICATED",
)
_BASE_TYPE_ROLES = ("NO_TERM", "TERM", "ESCROW", "DEDICATED")
_DISTINCTIVE_TYPE_ROLES = {"SAVINGS_NO_TERM", "SAVINGS_TERM", "ESCROW", "DEDICATED"}
_CUSTOMER_SOURCE_ROLES = (
    "CUSTOMER_TCKT",
    "STATE_COMPANY",
    "TNHH",
    "STATE_100_TNHH",
    "STATE_OVER_50_ONE_MEMBER_TNHH",
    "STATE_OVER_50_MULTI_MEMBER_TNHH",
    "OTHER_TNHH",
    "STATE_OVER_50_JSC",
    "OTHER_JSC",
    "PRIVATE_ENTERPRISE",
    "COMBINED_COMPANY",
    "COOPERATIVE",
    "PARTNERSHIP",
    "FOREIGN_INVESTED",
    "HOUSEHOLD_INDIVIDUAL",
    "ADMIN_ASSOCIATION",
    "OTHER_CUSTOMER",
)
_TYPE_OUTPUT_ROLES = (
    "NO_TERM",
    "NO_TERM_VND",
    "NO_TERM_FOREIGN",
    "TERM",
    "TERM_VND",
    "TERM_FOREIGN",
    "SAVINGS",
    "SAVINGS_VND",
    "SAVINGS_FOREIGN",
    "ESCROW",
    "ESCROW_VND",
    "ESCROW_FOREIGN",
    "DEDICATED",
    "DEDICATED_VND",
    "DEDICATED_FOREIGN",
)
_OUTPUT_ROLES = {*_TYPE_OUTPUT_ROLES, *_CUSTOMER_SOURCE_ROLES}


class GeminiJsonCustomerDepositFamilyV1Error(ValueError):
    """The selected source, declarative triplet, or closure drifted."""


def _error(message: str) -> GeminiJsonCustomerDepositFamilyV1Error:
    return GeminiJsonCustomerDepositFamilyV1Error(message)


def _normalized(value: Any) -> str:
    return normalize_vietnamese_anchor_v1(value) if type(value) is str else ""


def _compile_units(value: Any) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if type(value) is not list or not value:
        raise _error("customer-deposit money-unit bindings are absent")
    checked: list[dict[str, Any]] = []
    by_alias: dict[str, dict[str, Any]] = {}
    canonical_units: set[str] = set()
    for raw in value:
        if (
            type(raw) is not dict
            or set(raw) != {"accepted", "aliases", "canonical_unit", "magnitude_power10"}
            or type(raw.get("accepted")) is not bool
            or type(raw.get("aliases")) is not list
            or not raw["aliases"]
            or any(type(alias) is not str or not alias.strip() for alias in raw["aliases"])
            or type(raw.get("canonical_unit")) is not str
            or not raw["canonical_unit"]
            or raw["canonical_unit"] in canonical_units
            or type(raw.get("magnitude_power10")) is not int
            or raw["magnitude_power10"] < 0
        ):
            raise _error("customer-deposit money-unit binding is invalid")
        aliases = [_normalized(alias) for alias in raw["aliases"]]
        if any(not alias or alias in by_alias for alias in aliases):
            raise _error("customer-deposit money-unit aliases collide")
        canonical_units.add(raw["canonical_unit"])
        binding = {**canonical_clone_v1(raw), "aliases": aliases}
        for alias in aliases:
            by_alias[alias] = binding
        checked.append(binding)
    if sum(item["accepted"] for item in checked) != 1:
        raise _error("customer-deposit policy needs exactly one accepted money unit")
    return checked, by_alias


def compile_gemini_json_customer_deposit_family_specs_v1(
    topology_spec: Any, evaluation_spec: Any, schema_binding_spec: Any
) -> dict[str, Any]:
    """Compile a data-only customer-deposit topology/evaluation/schema triplet."""

    try:
        topology = compile_accounting_family_topology_spec_v1(topology_spec)
    except ValueError as exc:
        raise _error("customer-deposit topology spec is invalid") from exc
    evaluation_fields = {
        "blank_zero_policy",
        "closure_policy",
        "customer_view_policy",
        "family_id",
        "format_version",
        "layout_policy",
        "money_unit_bindings",
        "period_semantics",
        "stacked_currency_aliases",
        "type_direct_roles",
        "type_parent_shorthand_aliases",
        "type_savings_source_roles",
    }
    if (
        type(evaluation_spec) is not dict
        or set(evaluation_spec) != evaluation_fields
        or evaluation_spec.get("format_version") != EVALUATION_FORMAT_VERSION
        or evaluation_spec.get("family_id") != topology["family_id"]
        or evaluation_spec.get("blank_zero_policy") != "ZERO_ONLY_AFTER_COMPLETE_EQUATION_EXACT"
        or evaluation_spec.get("closure_policy")
        != "EXACT_TYPE_CURRENCY_AND_OPTIONAL_CUSTOMER_VIEW_ALL_LANES"
        or evaluation_spec.get("customer_view_policy")
        != "OPTIONAL_ONLY_WITHIN_SAME_OWNER_OR_EXPLICIT_CONTINUATION_FENCE"
        or evaluation_spec.get("layout_policy")
        != "ONE_TWO_PERIOD_TABLE_OR_TWO_STACKED_PERIOD_CURRENCY_TABLES"
        or evaluation_spec.get("period_semantics") != "CURRENT_AND_COMPARATIVE_SNAPSHOT"
        or evaluation_spec.get("type_direct_roles") != list(_BASE_TYPE_ROLES)
        or evaluation_spec.get("type_savings_source_roles") != ["SAVINGS_NO_TERM", "SAVINGS_TERM"]
    ):
        raise _error("customer-deposit evaluation spec is invalid")
    aliases_by_source_role: dict[str, list[str]] = {}
    for child in topology["children"]:
        aliases = sorted(
            {
                alias
                for matcher in child["matchers"]
                if matcher["within_role"] is None
                for alias in matcher["aliases"]
            }
        )
        if not aliases:
            raise _error("customer-deposit source role has no root alias")
        aliases_by_source_role[child["role"]] = aliases
    expected_source_roles = {*_TYPE_SOURCE_ROLES, *_CUSTOMER_SOURCE_ROLES}
    if set(aliases_by_source_role) != expected_source_roles:
        raise _error("customer-deposit source-role frontier is incomplete")
    currency_aliases = evaluation_spec["stacked_currency_aliases"]
    if type(currency_aliases) is not dict or set(currency_aliases) != {"VND", "FOREIGN", "TOTAL"}:
        raise _error("customer-deposit stacked currency axis is invalid")
    compiled_currency_aliases = {}
    for role, aliases in currency_aliases.items():
        if (
            type(aliases) is not list
            or not aliases
            or any(type(alias) is not str or not alias.strip() for alias in aliases)
        ):
            raise _error("customer-deposit stacked currency aliases are invalid")
        folded = [_normalized(alias) for alias in aliases]
        if len(folded) != len(set(folded)):
            raise _error("customer-deposit stacked currency aliases collide")
        compiled_currency_aliases[role] = folded
    shorthand = evaluation_spec["type_parent_shorthand_aliases"]
    if type(shorthand) is not dict or set(shorthand) != {"NO_TERM", "TERM"}:
        raise _error("customer-deposit parent shorthand declarations are invalid")
    compiled_shorthand = {}
    for role, aliases in shorthand.items():
        if type(aliases) is not list or not aliases:
            raise _error("customer-deposit parent shorthand declarations are invalid")
        compiled_shorthand[role] = [_normalized(alias) for alias in aliases]
    units, units_by_alias = _compile_units(evaluation_spec["money_unit_bindings"])
    schema_fields = {
        "family_id",
        "family_root_report_norm_id",
        "format_version",
        "role_bindings",
        "root_mapping_policy",
        "schema_period_type",
    }
    if (
        type(schema_binding_spec) is not dict
        or set(schema_binding_spec) != schema_fields
        or schema_binding_spec.get("format_version") != SCHEMA_FORMAT_VERSION
        or schema_binding_spec.get("family_id") != topology["family_id"]
        or type(schema_binding_spec.get("family_root_report_norm_id")) is not int
        or schema_binding_spec["family_root_report_norm_id"] <= 0
        or schema_binding_spec.get("root_mapping_policy") != "STRUCTURAL_CONTEXT_ONLY"
        or schema_binding_spec.get("schema_period_type") != "SNAPSHOT"
        or type(schema_binding_spec.get("role_bindings")) is not list
    ):
        raise _error("customer-deposit schema binding spec is invalid")
    bindings: dict[str, int] = {}
    identities = {schema_binding_spec["family_root_report_norm_id"]}
    for raw in schema_binding_spec["role_bindings"]:
        if (
            type(raw) is not dict
            or set(raw) != {"report_norm_id", "role"}
            or raw.get("role") not in _OUTPUT_ROLES
            or raw["role"] in bindings
            or type(raw.get("report_norm_id")) is not int
            or raw["report_norm_id"] <= 0
            or raw["report_norm_id"] in identities
        ):
            raise _error("customer-deposit schema role binding is invalid")
        bindings[raw["role"]] = raw["report_norm_id"]
        identities.add(raw["report_norm_id"])
    if set(bindings) != _OUTPUT_ROLES:
        raise _error("customer-deposit schema binding frontier is incomplete")
    return {
        "aliases_by_source_role": aliases_by_source_role,
        "anchor_alias_groups": [
            [aliases_by_source_role[role] for role in ("NO_TERM", "TERM", "DEDICATED")],
            [aliases_by_source_role[role] for role in ("NO_TERM", "TERM", "ESCROW")],
        ],
        "bindings": bindings,
        "claim_boundary": CLAIM_BOUNDARY,
        "currency_aliases": compiled_currency_aliases,
        "engine_format_version": ENGINE_FORMAT_VERSION,
        "evaluation": canonical_clone_v1(evaluation_spec),
        "parent_shorthand_aliases": compiled_shorthand,
        "query_policy": {
            "hard_negative_aliases": canonical_clone_v1(topology["hard_negative_aliases"]),
            "owner_aliases": canonical_clone_v1(topology["parent"]["aliases"]),
            "reset_aliases": canonical_clone_v1(topology["structural_reset_aliases"]),
        },
        "schema": canonical_clone_v1(schema_binding_spec),
        "topology": topology,
        "unit_binding_by_alias": units_by_alias,
        "unit_bindings": units,
    }


def _match_alias(text: str, alias: str) -> bool:
    if text == alias or text.startswith(alias + " "):
        return True
    return len(alias.split()) >= 3 and f" {alias} " in f" {text} "


def _source_roles_for_text(
    value: Any, *, roles: Sequence[str], compiled_specs: Mapping[str, Any]
) -> list[str]:
    folded = _normalized(value)
    matches = [
        (alias, role)
        for role in roles
        for alias in compiled_specs["aliases_by_source_role"][role]
        if _match_alias(folded, alias)
    ]
    if not matches:
        return []
    maximal = [
        (alias, role)
        for alias, role in matches
        if not any(
            alias != other_alias and f" {alias} " in f" {other_alias} "
            for other_alias, _other_role in matches
        )
    ]
    return sorted({role for _alias, role in maximal})


def _currency_role_for_text(value: Any) -> str | None:
    folded = _normalized(value)
    if "ngoai te" in folded or "vang ngoai te" in folded:
        return "FOREIGN"
    if any(
        phrase in folded
        for phrase in ("bang vnd", "bang dong viet nam", "bang tien dong", "bang dong")
    ):
        return "VND"
    return None


def _parent_role_for_currency_row(
    row: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> tuple[str | None, bool]:
    path = row.get("hierarchy_path_exact")
    label = row.get("label_exact")
    label_folded = _normalized(label)
    candidates: set[str] = set()
    if type(path) is list:
        for item in path:
            folded = _normalized(item)
            if not folded or folded == label_folded:
                continue
            candidates.update(
                _source_roles_for_text(
                    folded, roles=_TYPE_SOURCE_ROLES, compiled_specs=compiled_specs
                )
            )
    if len(candidates) == 1:
        return next(iter(candidates)), False
    if len(candidates) > 1:
        return None, True
    candidates.update(
        _source_roles_for_text(label, roles=_TYPE_SOURCE_ROLES, compiled_specs=compiled_specs)
    )
    for role, aliases in compiled_specs["parent_shorthand_aliases"].items():
        if any(
            re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", label_folded)
            for alias in aliases
        ):
            candidates.add(role)
    return (next(iter(candidates)), False) if len(candidates) == 1 else (None, len(candidates) > 1)


def classify_gemini_json_customer_deposit_table_v1(
    table: Any, *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Classify one table from declared role population and typed columns."""

    if type(table) is not dict:
        raise _error("customer-deposit table is invalid")
    rows = table.get("rows")
    columns = table.get("columns")
    if type(rows) is not list or type(columns) is not list:
        raise _error("customer-deposit table axes are invalid")
    money_columns = [
        index
        for index, column in enumerate(columns)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    percent_columns = [
        index
        for index, column in enumerate(columns)
        if type(column) is dict and column.get("value_kind") == "PERCENT"
    ]
    type_hits: list[dict[str, Any]] = []
    customer_hits: list[dict[str, Any]] = []
    ambiguous_rows: list[int] = []
    root_total_ordinals: list[int] = []
    for ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict:
            continue
        label = row.get("label_exact")
        type_roles = _source_roles_for_text(
            label, roles=_TYPE_SOURCE_ROLES, compiled_specs=compiled_specs
        )
        customer_roles = _source_roles_for_text(
            label, roles=_CUSTOMER_SOURCE_ROLES, compiled_specs=compiled_specs
        )
        if row.get("row_kind") == "TOTAL" and not type_roles and not customer_roles:
            root_total_ordinals.append(ordinal)
        if len(type_roles) > 1 or len(customer_roles) > 1:
            ambiguous_rows.append(ordinal)
        for role in type_roles:
            type_hits.append({"role": role, "row_ordinal": ordinal})
        for role in customer_roles:
            customer_hits.append({"role": role, "row_ordinal": ordinal})
    type_roles = {item["role"] for item in type_hits}
    customer_roles = {item["role"] for item in customer_hits}
    reasons = []
    component_role = None
    if ambiguous_rows:
        reasons.append("SOURCE_ROW_ROLE_MATCH_IS_AMBIGUOUS")
    if (
        {"NO_TERM", "TERM"} <= type_roles
        and type_roles & _DISTINCTIVE_TYPE_ROLES
        and len(money_columns) in {2, 3}
        and len(root_total_ordinals) == 1
    ):
        component_role = "TYPE_CURRENCY"
    elif (
        {"NO_TERM", "TERM"} <= type_roles
        and type_roles & _DISTINCTIVE_TYPE_ROLES
        and not money_columns
        and percent_columns
    ):
        component_role = "INTEREST_RATE_CONTROL"
    if (
        len(customer_roles) >= 2
        and len(money_columns) == 2
        and len(percent_columns) in {0, 2}
        and len(root_total_ordinals) == 1
    ):
        if component_role is not None:
            reasons.append("TABLE_MATCHES_MULTIPLE_CUSTOMER_DEPOSIT_COMPONENTS")
        else:
            component_role = "CUSTOMER_TYPE"
    return {
        "ambiguous_row_ordinals": ambiguous_rows,
        "component_role": component_role,
        "customer_role_hits": customer_hits,
        "money_column_ordinals": [index + 1 for index in money_columns],
        "percent_column_ordinals": [index + 1 for index in percent_columns],
        "reasons": sorted(set(reasons)),
        "root_total_ordinals": root_total_ordinals,
        "type_role_hits": type_hits,
    }


def _has_explicit_percentage_evidence(table: Mapping[str, Any]) -> bool:
    surfaces = [table.get("unit_exact")]
    columns = table.get("columns")
    if type(columns) is list:
        for column in columns:
            if type(column) is not dict:
                continue
            path = column.get("header_path_exact")
            if type(path) is list:
                surfaces.extend(path)
    return any(
        type(surface) is str and ("%" in surface or "phan tram" in _normalized(surface))
        for surface in surfaces
    )


def _surface_matches(value: Any, aliases: Sequence[str]) -> str | None:
    folded = _normalized(value)
    matches = [alias for alias in aliases if _match_alias(folded, alias)]
    if not matches:
        return None
    longest = max(map(len, matches))
    selected = sorted(alias for alias in matches if len(alias) == longest)
    return selected[0] if len(selected) == 1 else None


def _page_record_axis(page_records: Any) -> list[dict[str, Any]]:
    required = {
        "document_id",
        "document_ordinal",
        "page_json",
        "page_json_version_id",
        "physical_page",
        "selected_page_ordinal",
        "source_logical_name",
        "source_sha256",
    }
    if type(page_records) not in {list, tuple} or not page_records:
        raise _error("customer-deposit selected page records are absent")
    checked = []
    identity = None
    prior = None
    for raw in page_records:
        if (
            type(raw) is not dict
            or set(raw) != required
            or _DOCUMENT_ID.fullmatch(raw.get("document_id", "")) is None
            or type(raw.get("document_ordinal")) is not int
            or raw["document_ordinal"] <= 0
            or _PAGE_VERSION.fullmatch(raw.get("page_json_version_id", "")) is None
            or type(raw.get("physical_page")) is not int
            or raw["physical_page"] <= 0
            or type(raw.get("selected_page_ordinal")) is not int
            or raw["selected_page_ordinal"] <= 0
            or type(raw.get("source_logical_name")) is not str
            or not raw["source_logical_name"]
            or _SHA256.fullmatch(raw.get("source_sha256", "")) is None
            or type(raw.get("page_json")) is not dict
            or type(raw["page_json"].get("sections")) is not list
        ):
            raise _error("customer-deposit selected page record is invalid")
        current_identity = tuple(
            raw[key]
            for key in ("document_id", "document_ordinal", "source_logical_name", "source_sha256")
        )
        position = (raw["selected_page_ordinal"], raw["physical_page"])
        if identity is None:
            identity = current_identity
        elif identity != current_identity:
            raise _error("customer-deposit selected pages cross document identity")
        if prior is not None and position <= prior:
            raise _error("customer-deposit selected pages are not in source order")
        prior = position
        checked.append(canonical_clone_v1(raw))
    return checked


def _region(
    record: Mapping[str, Any],
    section_id: str,
    table_id: str,
    component_role: str,
    fragment_ordinal: int,
) -> dict[str, Any]:
    return {
        "component_role": component_role,
        "document_id": record["document_id"],
        "document_ordinal": record["document_ordinal"],
        "fragment_ordinal": fragment_ordinal,
        "page_json_version_id": record["page_json_version_id"],
        "physical_page": record["physical_page"],
        "section_id": section_id,
        "selected_page_ordinal": record["selected_page_ordinal"],
        "source_logical_name": record["source_logical_name"],
        "source_sha256": record["source_sha256"],
        "table_id": table_id,
    }


def coalesce_gemini_json_customer_deposit_document_v1(
    *, page_records: Any, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Select one exhaustive type cluster and optional owner-bound customer view."""

    pages = _page_record_axis(page_records)
    tables: list[dict[str, Any]] = []
    declared_role_tables: list[dict[str, Any]] = []
    markers: list[dict[str, Any]] = []
    for record in pages:
        for section_ordinal, section in enumerate(record["page_json"]["sections"], start=1):
            if type(section) is not dict:
                continue
            section_id = f"s{section_ordinal}"
            section_surfaces = [("SECTION_TITLE", section.get("title_exact"))]
            narratives = section.get("narratives_exact")
            if type(narratives) is list:
                section_surfaces.extend(
                    (f"SECTION_NARRATIVE:{ordinal}", value)
                    for ordinal, value in enumerate(narratives, start=1)
                )
            for source_kind, value in section_surfaces:
                for marker_kind, aliases in (
                    ("OWNER", compiled_specs["query_policy"]["owner_aliases"]),
                    ("RESET", compiled_specs["query_policy"]["reset_aliases"]),
                    ("HARD_NEGATIVE", compiled_specs["query_policy"]["hard_negative_aliases"]),
                ):
                    alias = _surface_matches(value, aliases)
                    if alias is not None:
                        markers.append(
                            {
                                "alias": alias,
                                "kind": marker_kind,
                                "position": [record["selected_page_ordinal"], section_ordinal, 0],
                                "section_id": section_id,
                                "source_exact": value,
                                "source_kind": source_kind,
                                "table_id": None,
                            }
                        )
            section_tables = section.get("tables")
            if type(section_tables) is not list:
                continue
            for table_ordinal, table in enumerate(section_tables, start=1):
                if type(table) is not dict:
                    continue
                table_id = f"t{table_ordinal}"
                classification = classify_gemini_json_customer_deposit_table_v1(
                    table, compiled_specs=compiled_specs
                )
                position = [record["selected_page_ordinal"], section_ordinal, table_ordinal]
                title = table.get("title_exact")
                for marker_kind, aliases in (
                    ("OWNER", compiled_specs["query_policy"]["owner_aliases"]),
                    ("RESET", compiled_specs["query_policy"]["reset_aliases"]),
                    ("HARD_NEGATIVE", compiled_specs["query_policy"]["hard_negative_aliases"]),
                ):
                    alias = _surface_matches(title, aliases)
                    if alias is not None:
                        markers.append(
                            {
                                "alias": alias,
                                "kind": marker_kind,
                                "position": position,
                                "section_id": section_id,
                                "source_exact": title,
                                "source_kind": "TABLE_TITLE",
                                "table_id": table_id,
                            }
                        )
                if classification["component_role"] is not None:
                    tables.append(
                        {
                            "classification": classification,
                            "position": position,
                            "record": record,
                            "section_id": section_id,
                            "table": table,
                            "table_id": table_id,
                        }
                    )
                if classification["type_role_hits"] or classification["customer_role_hits"]:
                    declared_role_tables.append(
                        {
                            "classification": classification,
                            "position": position,
                            "record": record,
                            "section_id": section_id,
                            "table": table,
                            "table_id": table_id,
                        }
                    )
    type_tables = [
        item for item in tables if item["classification"]["component_role"] == "TYPE_CURRENCY"
    ]
    reasons: list[str] = []
    selected_type: list[dict[str, Any]] = []
    if len(type_tables) == 1:
        selected_type = type_tables
    elif len(type_tables) == 2:
        first_type, second_type = type_tables
        same_page_section = (
            first_type["record"]["page_json_version_id"]
            == second_type["record"]["page_json_version_id"]
            and first_type["section_id"] == second_type["section_id"]
        )
        second_local_owner = any(
            marker["kind"] == "OWNER"
            and marker["position"][:2] == second_type["position"][:2]
            and marker["position"] <= second_type["position"]
            for marker in markers
        )
        explicit_continuation = second_type["table"].get(
            "continuation"
        ) == "CONTINUES_FROM_PREVIOUS_PAGE" or any(
            marker["kind"] == "OWNER"
            and marker["position"][:2] == second_type["position"][:2]
            and "tiep theo" in _normalized(marker["alias"])
            for marker in markers
        )
        adjacent_continuation = (
            second_type["record"]["selected_page_ordinal"]
            == first_type["record"]["selected_page_ordinal"] + 1
            and second_type["record"]["physical_page"] == first_type["record"]["physical_page"] + 1
            and second_local_owner
            and explicit_continuation
            and not any(
                marker["kind"] in {"RESET", "HARD_NEGATIVE"}
                and first_type["position"] < marker["position"] < second_type["position"]
                for marker in markers
            )
        )
        same_role_population = {
            hit["role"] for hit in first_type["classification"]["type_role_hits"]
        } == {hit["role"] for hit in second_type["classification"]["type_role_hits"]}
        if (
            (same_page_section or adjacent_continuation)
            and all(
                len(item["classification"]["money_column_ordinals"]) == 3 for item in type_tables
            )
            and same_role_population
        ):
            selected_type = type_tables
        else:
            reasons.append("TYPE_CURRENCY_COMPONENT_NOT_EXACTLY_ONE_LAYOUT_CLUSTER")
    elif not type_tables:
        reasons.append("NO_DISTINCTIVE_TYPE_CURRENCY_COMPONENT")
    else:
        reasons.append("TYPE_CURRENCY_COMPONENT_NOT_EXACTLY_ONE_LAYOUT_CLUSTER")
    owner = None
    if selected_type:
        first_position = selected_type[0]["position"]
        prior_markers = [
            marker
            for marker in markers
            if marker["position"] <= first_position
            and marker["kind"] in {"OWNER", "RESET", "HARD_NEGATIVE"}
        ]
        if prior_markers and prior_markers[-1]["kind"] == "OWNER":
            owner = prior_markers[-1]
        elif prior_markers:
            reasons.append("IMPLIED_OWNER_BLOCKED_BY_RESET_OR_HARD_NEGATIVE")
        else:
            owner = {
                "alias": None,
                "kind": "IMPLIED_OWNER",
                "position": first_position,
                "section_id": selected_type[0]["section_id"],
                "source_exact": None,
                "source_kind": "UNIQUE_DISTINCTIVE_TYPE_ROLE_POPULATION",
                "table_id": selected_type[0]["table_id"],
            }
    selected_customer = None
    customer_tables = [
        item for item in tables if item["classification"]["component_role"] == "CUSTOMER_TYPE"
    ]
    if selected_type:
        last_type = selected_type[-1]
        attachable = []
        for item in customer_tables:
            same_section_after = (
                item["record"]["page_json_version_id"]
                == last_type["record"]["page_json_version_id"]
                and item["section_id"] == last_type["section_id"]
                and item["position"] > last_type["position"]
            )
            next_page = item["record"]["physical_page"] == last_type["record"]["physical_page"] + 1
            local_owner = any(
                marker["kind"] == "OWNER"
                and marker["position"][:2] == item["position"][:2]
                and marker["position"] <= item["position"]
                for marker in markers
            )
            if same_section_after or (next_page and local_owner):
                intervening = [
                    marker
                    for marker in markers
                    if last_type["position"] < marker["position"] < item["position"]
                    and marker["kind"] in {"RESET", "HARD_NEGATIVE"}
                ]
                if not intervening:
                    attachable.append(item)
        if len(attachable) == 1:
            selected_customer = attachable[0]
        elif len(attachable) > 1:
            reasons.append("CUSTOMER_TYPE_VIEW_NOT_UNIQUE_WITHIN_OWNER_FENCE")
    regions = []
    for ordinal, item in enumerate(selected_type, start=1):
        regions.append(
            _region(
                item["record"],
                item["section_id"],
                item["table_id"],
                "TYPE_CURRENCY",
                ordinal,
            )
        )
    if selected_customer is not None:
        regions.append(
            _region(
                selected_customer["record"],
                selected_customer["section_id"],
                selected_customer["table_id"],
                "CUSTOMER_TYPE",
                1,
            )
        )
    selected_table_keys = {
        (
            item["record"]["page_json_version_id"],
            item["section_id"],
            item["table_id"],
        )
        for item in [*selected_type, *([] if selected_customer is None else [selected_customer])]
    }
    fence_start = (
        owner["position"]
        if owner is not None
        else selected_type[0]["position"]
        if selected_type
        else None
    )
    fence_end = None
    if selected_type:
        boundary_markers = [
            marker
            for marker in markers
            if marker["position"] > selected_type[-1]["position"]
            and marker["kind"] in {"OWNER", "RESET", "HARD_NEGATIVE"}
        ]
        if boundary_markers:
            fence_end = min(marker["position"] for marker in boundary_markers)
    declared_role_inventory = []
    for item in declared_role_tables:
        key = (
            item["record"]["page_json_version_id"],
            item["section_id"],
            item["table_id"],
        )
        inside_fence = (
            fence_start is not None
            and item["position"] >= fence_start
            and (fence_end is None or item["position"] < fence_end)
        )
        if key in selected_table_keys:
            disposition = "SELECTED_FAMILY_COMPONENT"
        elif item["classification"]["component_role"] == "INTEREST_RATE_CONTROL" or (
            not item["classification"]["money_column_ordinals"]
            and (
                item["classification"]["percent_column_ordinals"]
                or _has_explicit_percentage_evidence(item["table"])
            )
        ):
            disposition = "EXCLUDED_TYPED_NON_MONEY_CONTROL"
        elif inside_fence:
            disposition = "UNCONSUMED_DECLARED_ROLE_TABLE_WITHIN_OWNER_FENCE"
            reasons.append(disposition)
        else:
            disposition = "OUTSIDE_SELECTED_OWNER_FENCE"
        declared_role_inventory.append(
            {
                "classification": item["classification"],
                "disposition": disposition,
                "page_json_version_id": item["record"]["page_json_version_id"],
                "physical_page": item["record"]["physical_page"],
                "position": item["position"],
                "section_id": item["section_id"],
                "table_id": item["table_id"],
            }
        )
    material = {
        "component_regions": regions if not reasons else [],
        "declared_role_table_inventory": declared_role_inventory,
        "document_id": pages[0]["document_id"],
        "document_ordinal": pages[0]["document_ordinal"],
        "owner_receipt": owner,
        "reasons": sorted(set(reasons)),
        "source_logical_name": pages[0]["source_logical_name"],
        "source_sha256": pages[0]["source_sha256"],
        "status": READY
        if regions and not reasons
        else (NOT_OBSERVED if not type_tables else UNRESOLVED),
    }
    return {
        **material,
        "cluster_id": "gjfcdfcv1:cluster:" + canonical_json_sha256_v1(material),
    }


def _source_table(
    page_json: Mapping[str, Any], *, section_id: str, table_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    sections = page_json.get("sections")
    if type(sections) is not list:
        raise _error("customer-deposit page has no section axis")
    if _SECTION_ID.fullmatch(section_id) is None:
        raise _error("customer-deposit section identity is invalid")
    section_index = int(section_id[1:]) - 1
    if not 0 <= section_index < len(sections) or type(sections[section_index]) is not dict:
        raise _error("customer-deposit section identity is out of range")
    section = sections[section_index]
    tables = section.get("tables")
    if type(tables) is not list or _TABLE_ID.fullmatch(table_id) is None:
        raise _error("customer-deposit table axis is invalid")
    table_index = int(table_id[1:]) - 1
    if not 0 <= table_index < len(tables) or type(tables[table_index]) is not dict:
        raise _error("customer-deposit table identity is out of range")
    return section, tables[table_index]


def _region_axis(regions: Any) -> list[dict[str, Any]]:
    fields = {
        "component_role",
        "document_id",
        "document_ordinal",
        "fragment_ordinal",
        "page_json_version_id",
        "physical_page",
        "section_id",
        "selected_page_ordinal",
        "source_logical_name",
        "source_sha256",
        "table_id",
    }
    if type(regions) not in {list, tuple} or not 1 <= len(regions) <= 3:
        raise _error("customer-deposit region axis cardinality is invalid")
    checked = []
    identity = None
    prior = None
    type_fragments = 0
    customer_fragments = 0
    for raw in regions:
        if (
            type(raw) is not dict
            or set(raw) != fields
            or raw.get("component_role") not in {"TYPE_CURRENCY", "CUSTOMER_TYPE"}
            or _DOCUMENT_ID.fullmatch(raw.get("document_id", "")) is None
            or type(raw.get("document_ordinal")) is not int
            or raw["document_ordinal"] <= 0
            or type(raw.get("fragment_ordinal")) is not int
            or raw["fragment_ordinal"] <= 0
            or _PAGE_VERSION.fullmatch(raw.get("page_json_version_id", "")) is None
            or type(raw.get("physical_page")) is not int
            or raw["physical_page"] <= 0
            or type(raw.get("selected_page_ordinal")) is not int
            or raw["selected_page_ordinal"] <= 0
            or _SECTION_ID.fullmatch(raw.get("section_id", "")) is None
            or _TABLE_ID.fullmatch(raw.get("table_id", "")) is None
            or type(raw.get("source_logical_name")) is not str
            or not raw["source_logical_name"]
            or _SHA256.fullmatch(raw.get("source_sha256", "")) is None
        ):
            raise _error("customer-deposit region is invalid")
        current_identity = tuple(
            raw[key]
            for key in ("document_id", "document_ordinal", "source_logical_name", "source_sha256")
        )
        position = (
            raw["selected_page_ordinal"],
            int(raw["section_id"][1:]),
            int(raw["table_id"][1:]),
        )
        if identity is None:
            identity = current_identity
        elif identity != current_identity:
            raise _error("customer-deposit regions cross document identity")
        if prior is not None and position <= prior:
            raise _error("customer-deposit regions are not in source order")
        prior = position
        if raw["component_role"] == "TYPE_CURRENCY":
            type_fragments += 1
            if raw["fragment_ordinal"] != type_fragments or customer_fragments:
                raise _error("customer-deposit type fragment axis is invalid")
        else:
            customer_fragments += 1
            if raw["fragment_ordinal"] != 1 or customer_fragments > 1:
                raise _error("customer-deposit customer-view axis is invalid")
        checked.append(canonical_clone_v1(raw))
    if type_fragments not in {1, 2}:
        raise _error("customer-deposit type layout needs one or two fragments")
    return checked


def build_gemini_json_customer_deposit_region_query_receipt_v1(
    regions: Any,
) -> dict[str, Any]:
    checked = _region_axis(regions)
    first = checked[0]
    material = {
        "document_id": first["document_id"],
        "exact_fragment_count": len(checked),
        "format_version": "GEMINI_JSON_CUSTOMER_DEPOSIT_REGION_QUERY_RECEIPT_V1",
        "ordered_fragment_axis_sha256": canonical_json_sha256_v1(checked),
        "source_logical_name": first["source_logical_name"],
        "source_sha256": first["source_sha256"],
    }
    return {
        **material,
        "query_receipt_id": "gjfcdrqrv1:receipt:" + canonical_json_sha256_v1(material),
    }


def _semantic_period_roles(value: str) -> list[str]:
    folded = _normalized(value)
    roles = []
    if any(alias == folded or f" {alias} " in f" {folded} " for alias in _CURRENT_PERIOD_ALIASES):
        roles.append("CURRENT_PERIOD")
    if any(
        alias == folded or f" {alias} " in f" {folded} " for alias in _COMPARATIVE_PERIOD_ALIASES
    ):
        roles.append("COMPARATIVE_PERIOD")
    return roles


def _two_period_axis(table: Mapping[str, Any]) -> dict[str, Any]:
    columns = table.get("columns")
    if type(columns) is not list:
        return {"complete": False, "reasons": ["COLUMN_AXIS_INVALID"]}
    money_ordinals = [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    if len(money_ordinals) != 2:
        return {
            "complete": False,
            "money_column_ordinals": money_ordinals,
            "reasons": ["EXACTLY_TWO_MONEY_COLUMNS_REQUIRED"],
        }
    headers = [_header_text(columns[ordinal - 1]) for ordinal in money_ordinals]
    dates = [sorted(item.isoformat() for item in _header_dates(header)) for header in headers]
    semantics = [_semantic_period_roles(header) for header in headers]
    signatures: list[list[str] | None] = []
    reasons = []
    expected = ("CURRENT_PERIOD", "COMPARATIVE_PERIOD")
    for lane, (date_axis, semantic_axis) in enumerate(zip(dates, semantics, strict=True), start=1):
        if len(date_axis) > 1:
            reasons.append(
                f"MULTIPLE_DISTINCT_DATES_IN_ONE_PERIOD_HEADER:c{money_ordinals[lane - 1]}"
            )
        if len(semantic_axis) > 1:
            reasons.append(
                f"MULTIPLE_SEMANTIC_PERIOD_ROLES_IN_ONE_HEADER:c{money_ordinals[lane - 1]}"
            )
        if (
            len(date_axis) == 1
            and len(semantic_axis) == 1
            and semantic_axis[0] != expected[lane - 1]
        ):
            reasons.append(
                f"DATE_AND_SEMANTIC_PERIOD_EVIDENCE_CONFLICT:c{money_ordinals[lane - 1]}"
            )
        if len(date_axis) == 1 and len(semantic_axis) <= 1:
            signatures.append(["DATE", date_axis[0]])
        elif not date_axis and len(semantic_axis) == 1:
            signatures.append(["SEMANTIC_ALIAS", semantic_axis[0]])
        else:
            signatures.append(None)
    if all(signature is not None for signature in signatures):
        first, second = signatures
        assert first is not None and second is not None
        if first[0] != second[0]:
            reasons.append("PERIOD_SIGNATURE_KINDS_DIFFER")
        elif first[0] == "DATE" and not date.fromisoformat(first[1]) > date.fromisoformat(
            second[1]
        ):
            reasons.append("DATE_PERIOD_AXIS_IS_NOT_STRICT_CURRENT_THEN_COMPARATIVE")
        elif first != ["SEMANTIC_ALIAS", "CURRENT_PERIOD"] and first[0] == "SEMANTIC_ALIAS":
            reasons.append("SEMANTIC_PERIOD_AXIS_IS_NOT_CURRENT_COMPARATIVE")
    else:
        reasons.append("TWO_PERIOD_AXIS_INCOMPLETE")
    return {
        "complete": not reasons,
        "date_evidence_by_lane": dates,
        "headers_exact": headers,
        "money_column_ordinals": money_ordinals,
        "reasons": sorted(set(reasons)),
        "semantic_roles_by_lane": semantics,
        "signatures": signatures,
        "source": "LOCAL_MONEY_COLUMN_HEADERS",
    }


def _alias_occurrences(text: str, aliases: Sequence[str]) -> list[str]:
    occurrences = [
        (match.start(), match.end(), alias)
        for alias in aliases
        for match in re.finditer(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", text)
    ]
    return sorted(
        {
            alias
            for start, end, alias in occurrences
            if not any(
                other_start <= start and end <= other_end and other_end - other_start > end - start
                for other_start, other_end, _other_alias in occurrences
            )
        }
    )


def _column_unit_surfaces(
    column: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> list[str]:
    """Return unit-bearing header segments after removing currency-role prefixes."""

    path = column.get("header_path_exact")
    values = [item for item in path if type(item) is str] if type(path) is list else []
    currency_aliases = sorted(
        {alias for aliases in compiled_specs["currency_aliases"].values() for alias in aliases},
        key=len,
        reverse=True,
    )
    surfaces = []
    for value in values:
        for line in value.splitlines() or [value]:
            folded = _normalized(line)
            if not folded:
                continue
            for alias in currency_aliases:
                if folded == alias:
                    folded = ""
                    break
                if folded.startswith(alias + " "):
                    folded = folded[len(alias) :].strip()
                    break
            if folded:
                surfaces.append(folded)
    return surfaces


def _document_unit_context_axis(
    page_json_by_version: Mapping[str, dict[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Build a document unit consensus from explicit scaled table-unit carriers."""

    scaled_aliases = [
        alias
        for alias, binding in compiled_specs["unit_binding_by_alias"].items()
        if binding["magnitude_power10"] > 0
    ]
    evidence = []
    conflicts = []
    for page_json_version_id, page_json in sorted(page_json_by_version.items()):
        if _PAGE_VERSION.fullmatch(page_json_version_id) is None or type(page_json) is not dict:
            raise _error("customer-deposit document unit context page is invalid")
        sections = page_json.get("sections")
        if type(sections) is not list:
            raise _error("customer-deposit document unit context section axis is invalid")
        for section_ordinal, section in enumerate(sections, start=1):
            if type(section) is not dict or type(section.get("tables")) is not list:
                continue
            for table_ordinal, table in enumerate(section["tables"], start=1):
                if type(table) is not dict:
                    continue
                unit_exact = table.get("unit_exact")
                if type(unit_exact) is not str or not unit_exact.strip():
                    continue
                matches = _alias_occurrences(_normalized(unit_exact), scaled_aliases)
                if not matches:
                    continue
                bindings = [compiled_specs["unit_binding_by_alias"][alias] for alias in matches]
                identities = {
                    (binding["canonical_unit"], binding["magnitude_power10"])
                    for binding in bindings
                }
                locator = {
                    "page_json_version_id": page_json_version_id,
                    "section_id": f"s{section_ordinal}",
                    "table_id": f"t{table_ordinal}",
                }
                if len(identities) != 1:
                    conflicts.append({**locator, "source_exact": unit_exact})
                    continue
                binding = bindings[0]
                evidence.append(
                    {
                        **locator,
                        "accepted": binding["accepted"],
                        "canonical_unit": binding["canonical_unit"],
                        "magnitude_power10": binding["magnitude_power10"],
                        "matched_aliases": matches,
                        "source_exact": unit_exact,
                        "source_kind": "TABLE_UNIT",
                    }
                )
    identities = {
        (item["canonical_unit"], item["magnitude_power10"], item["accepted"]) for item in evidence
    }
    distinct_pages = {item["page_json_version_id"] for item in evidence}
    unique = (
        not conflicts
        and len(identities) == 1
        and len(distinct_pages) >= 2
        and next(iter(identities))[2]
    )
    canonical_unit = next(iter(identities))[0] if unique else None
    return {
        "canonical_unit": canonical_unit,
        "conflicts": conflicts,
        "distinct_page_version_count": len(distinct_pages),
        "evidence": evidence,
        "evidence_axis_sha256": canonical_json_sha256_v1(evidence),
        "rule": "EXPLICIT_SCALED_TABLE_UNIT_UNIQUE_ACROSS_AT_LEAST_TWO_SELECTED_PAGES",
        "status": "UNIQUE" if unique else "NOT_UNIQUE",
    }


def _unit_axis(
    table: Mapping[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
    document_unit_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    columns = table.get("columns")
    if type(columns) is not list:
        return {
            "canonical_unit": None,
            "complete": False,
            "evidence": [],
            "reasons": ["COLUMN_AXIS_INVALID"],
        }
    money_columns = [
        column for column in columns if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    aliases = list(compiled_specs["unit_binding_by_alias"])
    evidence = []
    conflicts = []
    undeclared = []

    def classify(source_kind: str, source_exact: Any, explicit: bool) -> dict[str, Any] | None:
        folded = _normalized(source_exact)
        matches = _alias_occurrences(folded, aliases)
        if matches:
            records = []
            for alias in matches:
                binding = compiled_specs["unit_binding_by_alias"][alias]
                records.append(
                    {
                        "accepted": binding["accepted"],
                        "canonical_unit": binding["canonical_unit"],
                        "matched_alias": alias,
                        "magnitude_power10": binding["magnitude_power10"],
                        "source_exact": source_exact,
                        "source_kind": source_kind,
                    }
                )
            evidence.extend(records)
            identities = {(item["canonical_unit"], item["magnitude_power10"]) for item in records}
            if len(identities) != 1:
                conflicts.append({"source_exact": source_exact, "source_kind": source_kind})
                return None
            return records[0]
        if explicit or re.search(r"\b(?:dong|vnd|usd|trieu|nghin|ty)\b", folded):
            undeclared.append({"source_exact": source_exact, "source_kind": source_kind})
        return None

    table_record = None
    if type(table.get("unit_exact")) is str and table["unit_exact"].strip():
        table_record = classify("TABLE_UNIT", table["unit_exact"], True)
    column_records = []
    for ordinal, column in enumerate(money_columns, start=1):
        surface_records = [
            classify(f"MONEY_COLUMN_HEADER:{ordinal}:{surface_ordinal}", surface, False)
            for surface_ordinal, surface in enumerate(
                _column_unit_surfaces(column, compiled_specs=compiled_specs), start=1
            )
        ]
        present = [record for record in surface_records if record is not None]
        identities = {(record["canonical_unit"], record["magnitude_power10"]) for record in present}
        if len(identities) > 1:
            conflicts.append(
                {"source_exact": _header_text(column), "source_kind": f"MONEY_COLUMN:{ordinal}"}
            )
            column_records.append(None)
        elif present:
            column_records.append(present[0])
        else:
            column_records.append(None)
    reasons = []
    if conflicts:
        reasons.append("MULTIPLE_CONFLICTING_DECLARED_MONEY_UNITS_ON_ONE_SURFACE")
    if undeclared:
        reasons.append("UNDECLARED_EXPLICIT_MONEY_UNIT")
    if any(item is not None and not item["accepted"] for item in [table_record, *column_records]):
        reasons.append("EXPLICIT_MONEY_UNIT_IS_NOT_ACCEPTED")
    canonical_unit = None
    source = None
    if table_record is not None and table_record["accepted"]:
        canonical_unit = table_record["canonical_unit"]
        source = "LOCAL_TABLE_UNIT"
        if any(
            item is not None and item["canonical_unit"] != canonical_unit for item in column_records
        ):
            reasons.append("CONFLICTING_EXPLICIT_MONEY_UNITS")
    elif column_records and all(item is not None and item["accepted"] for item in column_records):
        units = {item["canonical_unit"] for item in column_records if item is not None}
        if len(units) == 1:
            canonical_unit = next(iter(units))
            source = "LOCAL_UNIFORM_ALL_MONEY_COLUMN_UNITS"
        else:
            reasons.append("CONFLICTING_EXPLICIT_MONEY_UNITS")
    else:
        reasons.append("MONEY_UNIT_NOT_EXACTLY_RESOLVED")
    inherited_context = None
    if (
        canonical_unit is None
        and reasons == ["MONEY_UNIT_NOT_EXACTLY_RESOLVED"]
        and not evidence
        and not undeclared
        and not conflicts
        and type(document_unit_context) is dict
        and document_unit_context.get("status") == "UNIQUE"
        and type(document_unit_context.get("canonical_unit")) is str
    ):
        canonical_unit = document_unit_context["canonical_unit"]
        source = "DOCUMENT_EXPLICIT_TABLE_UNIT_CONSENSUS"
        inherited_context = canonical_clone_v1(document_unit_context)
        reasons = []
    return {
        "canonical_unit": canonical_unit,
        "complete": canonical_unit is not None and not reasons,
        "document_unit_context_evidence": inherited_context,
        "evidence": evidence,
        "reasons": sorted(set(reasons)),
        "source": source,
        "undeclared_evidence": undeclared,
    }


def _stacked_currency_axis(
    table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    columns = table.get("columns")
    if (
        type(columns) is not list
        or len(columns) != 3
        or any(
            type(column) is not dict or column.get("value_kind") != "MONEY" for column in columns
        )
    ):
        return {
            "complete": False,
            "reasons": ["STACKED_LAYOUT_REQUIRES_EXACTLY_THREE_MONEY_COLUMNS"],
        }
    by_role: dict[str, int] = {}
    reasons = []
    headers = [_header_text(column) for column in columns]
    for ordinal, (column, _header) in enumerate(zip(columns, headers, strict=True), start=1):
        path = column.get("header_path_exact")
        path_values = [value for value in path if type(value) is str] if type(path) is list else []
        matched_roles = []
        for role, aliases in compiled_specs["currency_aliases"].items():
            if any(
                (
                    len(alias.split()) == 1
                    and any(_normalized(value) == alias for value in path_values)
                )
                or (
                    len(alias.split()) > 1
                    and any(_match_alias(_normalized(value), alias) for value in path_values)
                )
                for alias in aliases
            ):
                matched_roles.append(role)
        if len(matched_roles) != 1:
            reasons.append(f"STACKED_CURRENCY_COLUMN_ROLE_NOT_UNIQUE:c{ordinal}")
        elif matched_roles[0] in by_role:
            reasons.append(f"STACKED_CURRENCY_ROLE_DUPLICATED:{matched_roles[0]}")
        else:
            by_role[matched_roles[0]] = ordinal
    if set(by_role) != {"VND", "FOREIGN", "TOTAL"}:
        reasons.append("STACKED_CURRENCY_AXIS_INCOMPLETE")
    return {
        "column_ordinal_by_role": by_role,
        "complete": not reasons,
        "headers_exact": headers,
        "reasons": sorted(set(reasons)),
    }


def _stacked_period_signature(table: Mapping[str, Any]) -> dict[str, Any]:
    surfaces = [table.get("title_exact")]
    columns = table.get("columns")
    if type(columns) is list:
        surfaces.extend(_header_text(column) for column in columns if type(column) is dict)
    dates = sorted(
        {
            item.isoformat()
            for surface in surfaces
            if type(surface) is str
            for item in _header_dates(surface)
        }
    )
    semantics = sorted(
        {
            role
            for surface in surfaces
            if type(surface) is str
            for role in _semantic_period_roles(surface)
        }
    )
    reasons = []
    if len(dates) > 1:
        reasons.append("STACKED_FRAGMENT_MULTIPLE_DISTINCT_DATES")
    if len(semantics) > 1:
        reasons.append("STACKED_FRAGMENT_MULTIPLE_SEMANTIC_PERIOD_ROLES")
    if len(dates) == 1 and len(semantics) == 1:
        # A dated fragment may also say current/comparative, but this is only
        # accepted after the two-fragment ordering check below.
        signature = ["DATE", dates[0]]
    elif len(dates) == 1:
        signature = ["DATE", dates[0]]
    elif len(semantics) == 1:
        signature = ["SEMANTIC_ALIAS", semantics[0]]
    else:
        signature = None
        reasons.append("STACKED_FRAGMENT_PERIOD_SIGNATURE_ABSENT")
    return {
        "complete": signature is not None and not reasons,
        "dates": dates,
        "reasons": sorted(set(reasons)),
        "semantic_roles": semantics,
        "signature": signature,
        "surfaces_exact": surfaces,
    }


def _parse_cells(row: Mapping[str, Any], column_ordinals: Sequence[int]) -> list[dict[str, Any]]:
    values = row.get("values_exact")
    if type(values) is not list or any(
        not 1 <= ordinal <= len(values) for ordinal in column_ordinals
    ):
        raise _error("customer-deposit row value vector does not bind the selected columns")
    try:
        return [_money(values[ordinal - 1]) for ordinal in column_ordinals]
    except ValueError as exc:
        raise _error("customer-deposit money cell is invalid") from exc


def _derived_cells(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if not records:
        raise _error("customer-deposit derived cell axis is empty")
    width = len(records[0]["cells"])
    if width != 2 or any(len(record["cells"]) != width for record in records):
        raise _error("customer-deposit derived cell vectors do not align")
    return [
        {
            "coefficient": sum(record["cells"][lane]["coefficient"] for record in records),
            "source_text": None,
            "state": "DERIVED_EXACT_SUM_OF_SOURCE_ROWS",
        }
        for lane in range(width)
    ]


def _coefficients(record: Mapping[str, Any]) -> list[int]:
    return [cell["coefficient"] for cell in record["cells"]]


def _equation(
    *,
    equation_kind: str,
    component_records: Sequence[Mapping[str, Any]],
    result_record: Mapping[str, Any],
    result_role: str,
) -> dict[str, Any]:
    component_sums = [
        sum(record["cells"][lane]["coefficient"] for record in component_records)
        for lane in range(2)
    ]
    result = _coefficients(result_record)
    material = {
        "component_roles": [record["role"] for record in component_records],
        "component_source_refs": [
            canonical_clone_v1(record["source_refs"]) for record in component_records
        ],
        "component_sums": component_sums,
        "equation_kind": equation_kind,
        "result_coefficients": result,
        "result_role": result_role,
        "result_source_refs": canonical_clone_v1(result_record["source_refs"]),
        "status": "EXACT" if component_sums == result else "MISMATCH",
    }
    return {
        **material,
        "equation_id": "gjfcdev1:equation:" + canonical_json_sha256_v1(material),
    }


def _source_ref(
    region: Mapping[str, Any], row_ordinal: int, row: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "hierarchy_path_exact": canonical_clone_v1(row.get("hierarchy_path_exact")),
        "label_exact": row.get("label_exact"),
        "locator": canonical_clone_v1(region),
        "row_id": f"r{row_ordinal}",
        "row_kind": row.get("row_kind"),
        "row_ordinal": row_ordinal,
    }


def _record(
    *, role: str, cells: list[dict[str, Any]], source_refs: list[dict[str, Any]], state: str
) -> dict[str, Any]:
    return {
        "cells": canonical_clone_v1(cells),
        "role": role,
        "source_refs": canonical_clone_v1(source_refs),
        "state": state,
    }


def _aggregate_records(role: str, records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return _record(
        role=role,
        cells=_derived_cells(records),
        source_refs=[ref for record in records for ref in record["source_refs"]],
        state="DERIVED_EXACT_SUM_OF_SOURCE_ROWS",
    )


def _ordinary_type_view(
    *,
    table: Mapping[str, Any],
    region: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
    document_unit_context: Mapping[str, Any] | None,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], dict[str, Any], list[str]]:
    period_axis = _two_period_axis(table)
    unit_axis = _unit_axis(
        table,
        compiled_specs=compiled_specs,
        document_unit_context=document_unit_context,
    )
    reasons = [*period_axis["reasons"], *unit_axis["reasons"]]
    money_columns = period_axis.get("money_column_ordinals", [])
    rows = table.get("rows")
    if type(rows) is not list:
        raise _error("customer-deposit ordinary type row axis is invalid")
    direct: dict[str, list[dict[str, Any]]] = defaultdict(list)
    children: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    savings_children: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    totals: list[dict[str, Any]] = []
    inventory = []
    for ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict:
            reasons.append("SOURCE_ROW_AXIS_INVALID")
            continue
        ref = _source_ref(region, ordinal, row)
        label = row.get("label_exact")
        currency_role = _currency_role_for_text(label)
        matched_roles = _source_roles_for_text(
            label, roles=_TYPE_SOURCE_ROLES, compiled_specs=compiled_specs
        )
        if row.get("row_kind") == "TOTAL" and not matched_roles:
            try:
                cells = _parse_cells(row, money_columns)
            except GeminiJsonCustomerDepositFamilyV1Error:
                reasons.append("TYPE_VISIBLE_TOTAL_MONEY_VECTOR_INVALID")
                cells = []
            totals.append(
                _record(
                    role="TYPE_VISIBLE_TOTAL",
                    cells=cells,
                    source_refs=[ref],
                    state="SOURCE_VISIBLE",
                )
            )
            inventory.append({**ref, "disposition": "TYPE_VISIBLE_TOTAL", "matched_roles": []})
            continue
        disposition = "UNCLASSIFIED_TYPE_ROW"
        if currency_role is None and len(matched_roles) == 1:
            role = matched_roles[0]
            try:
                cells = _parse_cells(row, money_columns)
            except GeminiJsonCustomerDepositFamilyV1Error:
                reasons.append(f"TYPE_DIRECT_ROLE_MONEY_VECTOR_INVALID:{role}")
                cells = []
            direct[role].append(
                _record(role=role, cells=cells, source_refs=[ref], state="SOURCE_VISIBLE")
            )
            disposition = "TYPE_DIRECT_ROLE"
        elif currency_role is not None:
            parent_role, parent_ambiguous = _parent_role_for_currency_row(
                row, compiled_specs=compiled_specs
            )
            if parent_ambiguous:
                reasons.append(f"TYPE_CURRENCY_PARENT_AMBIGUOUS:r{ordinal}")
            elif parent_role is None:
                reasons.append(f"TYPE_CURRENCY_PARENT_ABSENT:r{ordinal}")
            else:
                try:
                    cells = _parse_cells(row, money_columns)
                except GeminiJsonCustomerDepositFamilyV1Error:
                    reasons.append(f"TYPE_CURRENCY_ROLE_MONEY_VECTOR_INVALID:r{ordinal}")
                    cells = []
                child = _record(
                    role=f"{parent_role}_{currency_role}",
                    cells=cells,
                    source_refs=[ref],
                    state="SOURCE_VISIBLE",
                )
                children[(parent_role, currency_role)].append(child)
                savings_role_hits = [
                    role for role in matched_roles if role in {"SAVINGS_NO_TERM", "SAVINGS_TERM"}
                ]
                if len(savings_role_hits) == 1:
                    savings_children[(savings_role_hits[0], currency_role)].append(child)
                disposition = "TYPE_CURRENCY_CHILD"
        if disposition == "UNCLASSIFIED_TYPE_ROW":
            reasons.append(f"UNCONSUMED_TYPE_SOURCE_ROW:r{ordinal}")
        inventory.append(
            {
                **ref,
                "currency_role": currency_role,
                "disposition": disposition,
                "matched_roles": matched_roles,
            }
        )
    if len(totals) != 1 or not totals[0]["cells"]:
        reasons.append("TYPE_VISIBLE_TOTAL_COUNT_NOT_ONE")
    for role, records in direct.items():
        if len(records) > 1:
            reasons.append(f"DUPLICATE_TYPE_DIRECT_ROLE:{role}")
    source_parent_records: dict[str, dict[str, Any]] = {}
    equations: list[dict[str, Any]] = []
    output: dict[str, dict[str, Any]] = {}
    for role in _TYPE_SOURCE_ROLES:
        direct_record = direct.get(role, [None])[0] if len(direct.get(role, [])) == 1 else None
        child_records = [
            child
            for currency_role in ("VND", "FOREIGN")
            for child in children.get((role, currency_role), [])
        ]
        if direct_record is None and not child_records:
            continue
        child_sum = _aggregate_records(role, child_records) if child_records else None
        direct_visible = direct_record is not None and any(
            cell["source_text"] is not None for cell in direct_record["cells"]
        )
        if direct_visible:
            parent_record = direct_record
            if child_sum is not None:
                equation = _equation(
                    equation_kind="TYPE_PARENT_EQUALS_CURRENCY_CHILDREN",
                    component_records=child_records,
                    result_record=direct_record,
                    result_role=role,
                )
                equations.append(equation)
                if equation["status"] != "EXACT":
                    reasons.append(f"TYPE_PARENT_CURRENCY_EQUATION_MISMATCH:{role}")
        elif child_sum is not None:
            parent_record = child_sum
        else:
            reasons.append(f"TYPE_PARENT_BLANK_WITHOUT_CHILD_FRONTIER:{role}")
            continue
        source_parent_records[role] = parent_record
        if role in _BASE_TYPE_ROLES:
            output[role] = _record(
                role=role,
                cells=parent_record["cells"],
                source_refs=parent_record["source_refs"],
                state=parent_record["state"],
            )
            for currency_role in ("VND", "FOREIGN"):
                records = children.get((role, currency_role), [])
                if records:
                    output_role = f"{role}_{currency_role}"
                    output[output_role] = _aggregate_records(output_role, records)
    savings_source_records = [
        source_parent_records[role]
        for role in ("SAVINGS_NO_TERM", "SAVINGS_TERM")
        if role in source_parent_records
    ]
    if savings_source_records:
        output["SAVINGS"] = _aggregate_records("SAVINGS", savings_source_records)
    for currency_role in ("VND", "FOREIGN"):
        records = [
            child
            for source_role in ("SAVINGS_NO_TERM", "SAVINGS_TERM")
            for child in savings_children.get((source_role, currency_role), [])
        ]
        if not records:
            records = [
                child
                for source_role in ("SAVINGS_NO_TERM", "SAVINGS_TERM")
                for child in children.get((source_role, currency_role), [])
            ]
        if records:
            output_role = f"SAVINGS_{currency_role}"
            output[output_role] = _aggregate_records(output_role, records)
    if "SAVINGS" not in output:
        savings_currency_records = [
            output[role] for role in ("SAVINGS_VND", "SAVINGS_FOREIGN") if role in output
        ]
        if savings_currency_records:
            output["SAVINGS"] = _aggregate_records("SAVINGS", savings_currency_records)
    present_base_roles = [role for role in _BASE_TYPE_ROLES if role in source_parent_records]
    additive_roles = list(present_base_roles)
    for role in ("SAVINGS_NO_TERM", "SAVINGS_TERM"):
        record = source_parent_records.get(role)
        if record is None:
            continue
        if all(
            type(ref.get("hierarchy_path_exact")) is list
            and bool(ref["hierarchy_path_exact"])
            and _source_roles_for_text(
                ref["hierarchy_path_exact"][0],
                roles=_TYPE_SOURCE_ROLES,
                compiled_specs=compiled_specs,
            )
            == [role]
            for ref in record["source_refs"]
        ):
            additive_roles.append(role)
    if not any(
        set(required_roles) <= set(present_base_roles)
        for required_roles in compiled_specs["topology"]["required_role_combinations"]
    ):
        reasons.append("TYPE_ROOT_DIRECT_FRONTIER_INCOMPLETE")
    elif len(totals) == 1 and totals[0]["cells"]:
        equation = _equation(
            equation_kind="TYPE_ROOT_EQUALS_DIRECT_PARENT_FRONTIER",
            component_records=[source_parent_records[role] for role in additive_roles],
            result_record=totals[0],
            result_role="TYPE_VISIBLE_TOTAL",
        )
        equations.append(equation)
        if equation["status"] != "EXACT":
            reasons.append("TYPE_ROOT_TOTAL_EQUATION_MISMATCH")
    return (
        output,
        equations,
        {
            "layout": "ROW_ROLES_X_TWO_PERIOD_COLUMNS",
            "period_axis": period_axis,
            "source_inventory": inventory,
            "unit_axis": unit_axis,
        },
        sorted(set(reasons)),
    )


def _stacked_type_view(
    *,
    tables: Sequence[Mapping[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    document_unit_context: Mapping[str, Any] | None,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], dict[str, Any], list[str]]:
    if len(tables) != 2 or len(regions) != 2:
        raise _error("customer-deposit stacked type layout needs two fragments")
    period_receipts = [_stacked_period_signature(table) for table in tables]
    currency_receipts = [
        _stacked_currency_axis(table, compiled_specs=compiled_specs) for table in tables
    ]
    unit_receipts = [
        _unit_axis(
            table,
            compiled_specs=compiled_specs,
            document_unit_context=document_unit_context,
        )
        for table in tables
    ]
    reasons = [
        *(
            f"STACKED_FRAGMENT_{ordinal}:{reason}"
            for ordinal, receipt in enumerate(period_receipts, 1)
            for reason in receipt["reasons"]
        ),
        *(
            f"STACKED_FRAGMENT_{ordinal}:{reason}"
            for ordinal, receipt in enumerate(currency_receipts, 1)
            for reason in receipt["reasons"]
        ),
        *(
            f"STACKED_FRAGMENT_{ordinal}:{reason}"
            for ordinal, receipt in enumerate(unit_receipts, 1)
            for reason in receipt["reasons"]
        ),
    ]
    signatures = [receipt.get("signature") for receipt in period_receipts]
    for ordinal, (receipt, expected_role) in enumerate(
        zip(period_receipts, ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"), strict=True),
        start=1,
    ):
        semantic_roles = receipt.get("semantic_roles", [])
        if len(semantic_roles) == 1 and semantic_roles[0] != expected_role:
            reasons.append(f"STACKED_DATE_AND_SEMANTIC_PERIOD_EVIDENCE_CONFLICT:fragment_{ordinal}")
    if all(signature is not None for signature in signatures):
        first, second = signatures
        assert first is not None and second is not None
        if first[0] != second[0]:
            reasons.append("STACKED_PERIOD_SIGNATURE_KINDS_DIFFER")
        elif first[0] == "DATE" and not date.fromisoformat(first[1]) > date.fromisoformat(
            second[1]
        ):
            reasons.append("STACKED_PERIOD_AXIS_IS_NOT_STRICT_CURRENT_THEN_COMPARATIVE")
        elif first[0] == "SEMANTIC_ALIAS" and [first[1], second[1]] != [
            "CURRENT_PERIOD",
            "COMPARATIVE_PERIOD",
        ]:
            reasons.append("STACKED_SEMANTIC_PERIOD_AXIS_IS_NOT_CURRENT_COMPARATIVE")
    if any(
        receipt.get("canonical_unit") != unit_receipts[0].get("canonical_unit")
        for receipt in unit_receipts[1:]
    ):
        reasons.append("STACKED_FRAGMENT_UNITS_DIFFER")
    fragment_rows: list[dict[str, dict[str, dict[str, Any]]]] = []
    fragment_totals: list[dict[str, dict[str, Any]]] = []
    inventory = []
    for table, region, currency_axis in zip(tables, regions, currency_receipts, strict=True):
        rows = table.get("rows")
        if type(rows) is not list:
            raise _error("customer-deposit stacked row axis is invalid")
        by_role: dict[str, dict[str, dict[str, Any]]] = {}
        total_by_currency: dict[str, dict[str, Any]] = {}
        for ordinal, row in enumerate(rows, start=1):
            if type(row) is not dict:
                reasons.append("STACKED_SOURCE_ROW_INVALID")
                continue
            ref = _source_ref(region, ordinal, row)
            role = None
            disposition = "UNCLASSIFIED_STACKED_TYPE_ROW"
            matched = _source_roles_for_text(
                row.get("label_exact"), roles=_TYPE_SOURCE_ROLES, compiled_specs=compiled_specs
            )
            if row.get("row_kind") == "TOTAL" and not matched:
                disposition = "TYPE_VISIBLE_TOTAL"
                for currency_role, column_ordinal in currency_axis.get(
                    "column_ordinal_by_role", {}
                ).items():
                    total_by_currency[currency_role] = _record(
                        role=f"TYPE_VISIBLE_TOTAL_{currency_role}",
                        cells=[_parse_cells(row, [column_ordinal])[0]],
                        source_refs=[ref],
                        state="SOURCE_VISIBLE",
                    )
            else:
                if len(matched) == 1:
                    role = matched[0]
                    disposition = "STACKED_TYPE_ROLE"
                    if role in by_role:
                        reasons.append(f"STACKED_DUPLICATE_TYPE_ROLE:{role}")
                    records = {}
                    for currency_role, column_ordinal in currency_axis.get(
                        "column_ordinal_by_role", {}
                    ).items():
                        records[currency_role] = _record(
                            role=f"{role}_{currency_role}",
                            cells=[_parse_cells(row, [column_ordinal])[0]],
                            source_refs=[ref],
                            state="SOURCE_VISIBLE",
                        )
                    by_role[role] = records
                else:
                    reasons.append(f"STACKED_UNCONSUMED_OR_AMBIGUOUS_TYPE_ROW:r{ordinal}")
            inventory.append(
                {
                    **ref,
                    "disposition": disposition,
                    "matched_role": role,
                }
            )
        if set(total_by_currency) != {"VND", "FOREIGN", "TOTAL"}:
            reasons.append("STACKED_VISIBLE_TOTAL_CURRENCY_AXIS_INCOMPLETE")
        fragment_rows.append(by_role)
        fragment_totals.append(total_by_currency)
    role_sets = [set(item) for item in fragment_rows]
    if role_sets[0] != role_sets[1]:
        reasons.append("STACKED_PERIOD_ROLE_POPULATIONS_DIFFER")
    source_period_records: dict[str, dict[str, dict[str, Any]]] = {}
    equations: list[dict[str, Any]] = []
    output: dict[str, dict[str, Any]] = {}
    for role in sorted(role_sets[0] & role_sets[1], key=_TYPE_SOURCE_ROLES.index):
        records_by_currency = {}
        for currency_role in ("VND", "FOREIGN", "TOTAL"):
            lane_records = [fragment_rows[lane][role][currency_role] for lane in range(2)]
            records_by_currency[currency_role] = _record(
                role=f"{role}_{currency_role}",
                cells=[record["cells"][0] for record in lane_records],
                source_refs=[ref for record in lane_records for ref in record["source_refs"]],
                state="SOURCE_VISIBLE_STACKED_PERIOD_AXIS",
            )
        source_period_records[role] = records_by_currency
        equation = _equation(
            equation_kind="STACKED_ROLE_TOTAL_EQUALS_CURRENCY_COMPONENTS",
            component_records=[records_by_currency["VND"], records_by_currency["FOREIGN"]],
            result_record=records_by_currency["TOTAL"],
            result_role=role,
        )
        equations.append(equation)
        if equation["status"] != "EXACT":
            reasons.append(f"STACKED_ROLE_CURRENCY_EQUATION_MISMATCH:{role}")
        if role in _BASE_TYPE_ROLES:
            output[role] = _record(
                role=role,
                cells=records_by_currency["TOTAL"]["cells"],
                source_refs=records_by_currency["TOTAL"]["source_refs"],
                state=records_by_currency["TOTAL"]["state"],
            )
            for currency_role in ("VND", "FOREIGN"):
                output_role = f"{role}_{currency_role}"
                output[output_role] = _record(
                    role=output_role,
                    cells=records_by_currency[currency_role]["cells"],
                    source_refs=records_by_currency[currency_role]["source_refs"],
                    state=records_by_currency[currency_role]["state"],
                )
    savings_roles = [
        role for role in ("SAVINGS_NO_TERM", "SAVINGS_TERM") if role in source_period_records
    ]
    if savings_roles:
        for output_role, currency_role in (
            ("SAVINGS", "TOTAL"),
            ("SAVINGS_VND", "VND"),
            ("SAVINGS_FOREIGN", "FOREIGN"),
        ):
            output[output_role] = _aggregate_records(
                output_role, [source_period_records[role][currency_role] for role in savings_roles]
            )
    present_base_roles = [role for role in _BASE_TYPE_ROLES if role in source_period_records]
    additive_roles = list(present_base_roles)
    for role in ("SAVINGS_NO_TERM", "SAVINGS_TERM"):
        if role not in source_period_records:
            continue
        refs = source_period_records[role]["TOTAL"]["source_refs"]
        if all(
            type(ref.get("hierarchy_path_exact")) is list
            and bool(ref["hierarchy_path_exact"])
            and _source_roles_for_text(
                ref["hierarchy_path_exact"][0],
                roles=_TYPE_SOURCE_ROLES,
                compiled_specs=compiled_specs,
            )
            == [role]
            for ref in refs
        ):
            additive_roles.append(role)
    if not any(
        set(required_roles) <= set(present_base_roles)
        for required_roles in compiled_specs["topology"]["required_role_combinations"]
    ):
        reasons.append("STACKED_TYPE_ROOT_DIRECT_FRONTIER_INCOMPLETE")
    else:
        total_records = {}
        for currency_role in ("VND", "FOREIGN", "TOTAL"):
            lane_records = [fragment_totals[lane].get(currency_role) for lane in range(2)]
            if any(record is None for record in lane_records):
                continue
            records = [record for record in lane_records if record is not None]
            total_records[currency_role] = _record(
                role=f"TYPE_VISIBLE_TOTAL_{currency_role}",
                cells=[record["cells"][0] for record in records],
                source_refs=[ref for record in records for ref in record["source_refs"]],
                state="SOURCE_VISIBLE_STACKED_PERIOD_AXIS",
            )
        for currency_role in ("VND", "FOREIGN", "TOTAL"):
            if currency_role not in total_records:
                continue
            equation = _equation(
                equation_kind=f"STACKED_TYPE_ROOT_{currency_role}_FRONTIER",
                component_records=[
                    source_period_records[role][currency_role] for role in additive_roles
                ],
                result_record=total_records[currency_role],
                result_role=f"TYPE_VISIBLE_TOTAL_{currency_role}",
            )
            equations.append(equation)
            if equation["status"] != "EXACT":
                reasons.append(f"STACKED_TYPE_ROOT_EQUATION_MISMATCH:{currency_role}")
    return (
        output,
        equations,
        {
            "currency_axes": currency_receipts,
            "layout": "TWO_STACKED_PERIOD_TABLES_X_CURRENCY_COLUMNS",
            "period_axes": period_receipts,
            "source_inventory": inventory,
            "unit_axes": unit_receipts,
        },
        sorted(set(reasons)),
    )


def _customer_view(
    *,
    table: Mapping[str, Any],
    region: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
    document_unit_context: Mapping[str, Any] | None,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], dict[str, Any], list[str]]:
    period_axis = _two_period_axis(table)
    unit_axis = _unit_axis(
        table,
        compiled_specs=compiled_specs,
        document_unit_context=document_unit_context,
    )
    reasons = [*period_axis["reasons"], *unit_axis["reasons"]]
    money_columns = period_axis.get("money_column_ordinals", [])
    rows = table.get("rows")
    if type(rows) is not list:
        raise _error("customer-deposit customer-view row axis is invalid")
    by_role: dict[str, list[dict[str, Any]]] = defaultdict(list)
    parent_role_by_row: dict[int, str | None] = {}
    totals = []
    inventory = []
    for ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict:
            reasons.append("CUSTOMER_SOURCE_ROW_INVALID")
            continue
        ref = _source_ref(region, ordinal, row)
        if row.get("row_kind") == "TOTAL":
            try:
                cells = _parse_cells(row, money_columns)
            except GeminiJsonCustomerDepositFamilyV1Error:
                reasons.append("CUSTOMER_VISIBLE_TOTAL_MONEY_VECTOR_INVALID")
                cells = []
            totals.append(
                _record(
                    role="CUSTOMER_VISIBLE_TOTAL",
                    cells=cells,
                    source_refs=[ref],
                    state="SOURCE_VISIBLE",
                )
            )
            inventory.append({**ref, "disposition": "CUSTOMER_VISIBLE_TOTAL", "matched_roles": []})
            continue
        matched = _source_roles_for_text(
            row.get("label_exact"), roles=_CUSTOMER_SOURCE_ROLES, compiled_specs=compiled_specs
        )
        if len(matched) != 1:
            reasons.append(f"CUSTOMER_SOURCE_ROW_UNCONSUMED_OR_AMBIGUOUS:r{ordinal}")
            inventory.append(
                {**ref, "disposition": "UNCONSUMED_OR_AMBIGUOUS", "matched_roles": matched}
            )
            continue
        role = matched[0]
        try:
            cells = _parse_cells(row, money_columns)
        except GeminiJsonCustomerDepositFamilyV1Error:
            reasons.append(f"CUSTOMER_ROLE_MONEY_VECTOR_INVALID:{role}:r{ordinal}")
            cells = []
        record = _record(role=role, cells=cells, source_refs=[ref], state="SOURCE_VISIBLE")
        by_role[role].append(record)
        ancestors = []
        path = row.get("hierarchy_path_exact")
        label_folded = _normalized(row.get("label_exact"))
        if type(path) is list:
            for value in path:
                if _normalized(value) == label_folded:
                    continue
                ancestors.extend(
                    _source_roles_for_text(
                        value, roles=_CUSTOMER_SOURCE_ROLES, compiled_specs=compiled_specs
                    )
                )
        parent_role_by_row[ordinal] = ancestors[0] if len(set(ancestors)) == 1 else None
        if len(set(ancestors)) > 1:
            reasons.append(f"CUSTOMER_HIERARCHY_PARENT_AMBIGUOUS:r{ordinal}")
        inventory.append(
            {
                **ref,
                "disposition": "MAPPED_CUSTOMER_ROLE",
                "matched_roles": matched,
                "parent_role": parent_role_by_row[ordinal],
            }
        )
    if len(totals) != 1 or not totals[0]["cells"]:
        reasons.append("CUSTOMER_VISIBLE_TOTAL_COUNT_NOT_ONE")
    output = {role: _aggregate_records(role, records) for role, records in by_role.items()}
    equations = []
    for parent_role in by_role:
        child_records = [
            record
            for role, records in by_role.items()
            for record in records
            if any(
                ref["row_ordinal"] in parent_role_by_row
                and parent_role_by_row[ref["row_ordinal"]] == parent_role
                for ref in record["source_refs"]
            )
        ]
        if not child_records:
            continue
        equation = _equation(
            equation_kind="CUSTOMER_GROUP_EQUALS_HIERARCHY_CHILDREN",
            component_records=child_records,
            result_record=output[parent_role],
            result_role=parent_role,
        )
        equations.append(equation)
        if equation["status"] != "EXACT":
            reasons.append(f"CUSTOMER_HIERARCHY_EQUATION_MISMATCH:{parent_role}")
    root_records = []
    for role, records in by_role.items():
        top_level_records = [
            record
            for record in records
            if all(
                parent_role_by_row.get(ref["row_ordinal"]) is None for ref in record["source_refs"]
            )
        ]
        if top_level_records:
            root_records.append(_aggregate_records(role, top_level_records))
    if len(totals) == 1 and totals[0]["cells"] and root_records:
        equation = _equation(
            equation_kind="CUSTOMER_VISIBLE_TOTAL_EQUALS_TOP_LEVEL_FRONTIER",
            component_records=root_records,
            result_record=totals[0],
            result_role="CUSTOMER_VISIBLE_TOTAL",
        )
        equations.append(equation)
        if equation["status"] != "EXACT":
            reasons.append("CUSTOMER_ROOT_TOTAL_EQUATION_MISMATCH")
    else:
        reasons.append("CUSTOMER_ROOT_FRONTIER_INCOMPLETE")
    return (
        output,
        equations,
        {
            "layout": "CUSTOMER_ROWS_X_MONEY_AND_OPTIONAL_PERCENT_COLUMNS",
            "period_axis": period_axis,
            "source_inventory": inventory,
            "unit_axis": unit_axis,
        },
        sorted(set(reasons)),
    )


def _upgrade_blank_states(records: Sequence[Mapping[str, Any]]) -> None:
    for record in records:
        for cell in record["cells"]:
            if cell["state"] == "BLANK_ZERO_IF_EQUATION_EXACT":
                cell["state"] = "INFERRED_BLANK_ZERO_EQUATION_EXACT"


def evaluate_gemini_json_customer_deposit_family_cluster_v1(
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate one exact type/currency cluster and optional customer view."""

    region_axis = _region_axis(regions)
    expected_receipt = build_gemini_json_customer_deposit_region_query_receipt_v1(region_axis)
    if type(query_receipt) is not dict or not same_typed_json_v1(query_receipt, expected_receipt):
        raise _error("customer-deposit query receipt does not bind the exact fragments")
    document_unit_context = _document_unit_context_axis(
        page_json_by_version, compiled_specs=compiled_specs
    )
    type_regions = [item for item in region_axis if item["component_role"] == "TYPE_CURRENCY"]
    customer_regions = [item for item in region_axis if item["component_role"] == "CUSTOMER_TYPE"]
    tables = []
    for region in region_axis:
        page_json = page_json_by_version.get(region["page_json_version_id"])
        if type(page_json) is not dict:
            raise _error("customer-deposit selected page JSON is absent")
        _section, table = _source_table(
            page_json, section_id=region["section_id"], table_id=region["table_id"]
        )
        classification = classify_gemini_json_customer_deposit_table_v1(
            table, compiled_specs=compiled_specs
        )
        if (
            classification["component_role"] != region["component_role"]
            or classification["reasons"]
        ):
            raise _error("customer-deposit source fragment classification drifted")
        tables.append(table)
    table_by_region = dict(
        zip((canonical_json_sha256_v1(item) for item in region_axis), tables, strict=True)
    )
    type_tables = [table_by_region[canonical_json_sha256_v1(item)] for item in type_regions]
    if len(type_regions) == 1:
        type_output, type_equations, type_receipt, reasons = _ordinary_type_view(
            table=type_tables[0],
            region=type_regions[0],
            compiled_specs=compiled_specs,
            document_unit_context=document_unit_context,
        )
    else:
        type_output, type_equations, type_receipt, reasons = _stacked_type_view(
            tables=type_tables,
            regions=type_regions,
            compiled_specs=compiled_specs,
            document_unit_context=document_unit_context,
        )
    customer_output: dict[str, dict[str, Any]] = {}
    customer_equations: list[dict[str, Any]] = []
    customer_receipt = None
    if customer_regions:
        customer_table = table_by_region[canonical_json_sha256_v1(customer_regions[0])]
        (
            proposed_customer_output,
            proposed_customer_equations,
            proposed_customer_receipt,
            customer_reasons,
        ) = _customer_view(
            table=customer_table,
            region=customer_regions[0],
            compiled_specs=compiled_specs,
            document_unit_context=document_unit_context,
        )
        type_period = (
            type_receipt["period_axis"]["signatures"]
            if type_receipt["layout"] == "ROW_ROLES_X_TWO_PERIOD_COLUMNS"
            else [receipt["signature"] for receipt in type_receipt["period_axes"]]
        )
        if proposed_customer_receipt["period_axis"].get("signatures") != type_period:
            customer_reasons.append("CUSTOMER_AND_TYPE_PERIOD_AXES_DIFFER")
        type_units = (
            [type_receipt["unit_axis"].get("canonical_unit")]
            if "unit_axis" in type_receipt
            else [receipt.get("canonical_unit") for receipt in type_receipt["unit_axes"]]
        )
        if any(
            unit != proposed_customer_receipt["unit_axis"].get("canonical_unit")
            for unit in type_units
        ):
            customer_reasons.append("CUSTOMER_AND_TYPE_UNITS_DIFFER")
        customer_reasons = sorted(set(customer_reasons))
        if not customer_reasons and all(
            equation["status"] == "EXACT" for equation in proposed_customer_equations
        ):
            customer_output = proposed_customer_output
            customer_equations = proposed_customer_equations
            customer_receipt = {
                **proposed_customer_receipt,
                "disposition": "INCLUDED_EXACT_OPTIONAL_CUSTOMER_VIEW",
                "rejection_reasons": [],
            }
        else:
            customer_receipt = {
                **proposed_customer_receipt,
                "disposition": "EXCLUDED_NONEXACT_OPTIONAL_CUSTOMER_VIEW",
                "rejection_reasons": customer_reasons,
            }
    all_output = {**type_output, **customer_output}
    duplicate_roles = set(type_output) & set(customer_output)
    if duplicate_roles:
        reasons.append("TYPE_AND_CUSTOMER_OUTPUT_ROLE_AXES_OVERLAP")
    reasons = sorted(set(reasons))
    equations = [*type_equations, *customer_equations]
    exact = (
        bool(all_output)
        and not reasons
        and all(equation["status"] == "EXACT" for equation in equations)
    )
    if exact:
        _upgrade_blank_states(list(all_output.values()))
    mappings = []
    if exact:
        role_order = [item["role"] for item in compiled_specs["schema"]["role_bindings"]]
        for role in role_order:
            record = all_output.get(role)
            if record is None:
                continue
            material = {
                "report_norm_id": compiled_specs["bindings"][role],
                "role": role,
                "row_id": (
                    record["source_refs"][0]["row_id"]
                    if len(record["source_refs"]) == 1
                    else "aggregate:" + role
                ),
                "source_refs": canonical_clone_v1(record["source_refs"]),
                "state": record["state"],
                "unit": "MILLION_VND",
                "values": canonical_clone_v1(record["cells"]),
            }
            mappings.append(
                {
                    **material,
                    "item_mapping_id": "gjfcdmv1:item:" + canonical_json_sha256_v1(material),
                }
            )
    first = region_axis[0]
    structural_root_receipt = {
        "emitted_mapping": False,
        "mapping_policy": "STRUCTURAL_CONTEXT_ONLY",
        "report_norm_id": compiled_specs["schema"]["family_root_report_norm_id"],
        "role": compiled_specs["topology"]["parent"]["role"],
    }
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "closure_receipt": {
            "customer_view": customer_receipt,
            "equations": equations,
            "query_receipt": canonical_clone_v1(expected_receipt),
            "rule": "EXACT_TYPE_CURRENCY_AND_OPTIONAL_CUSTOMER_VIEW_ALL_LANES",
            "structural_root_receipt": structural_root_receipt,
            "type_currency_view": type_receipt,
        },
        "component_regions": region_axis,
        "document_id": first["document_id"],
        "family_id": compiled_specs["topology"]["family_id"],
        "mappings": mappings,
        "page_json_version_id": first["page_json_version_id"],
        "physical_page": first["physical_page"],
        "reasons": reasons,
        "section_id": first["section_id"],
        "source_logical_name": first["source_logical_name"],
        "source_sha256": first["source_sha256"],
        "status": READY if exact else UNRESOLVED,
        "table_id": first["table_id"],
    }
    return {
        "candidate_id": "gjfcdcv1:candidate:" + canonical_json_sha256_v1(material),
        **material,
    }


def validate_gemini_json_customer_deposit_family_candidate_replay_v1(
    value: Any,
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Exact-rebuild a customer-deposit candidate from selected source JSON."""

    rebuilt = evaluate_gemini_json_customer_deposit_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if type(value) is not dict or not same_typed_json_v1(value, rebuilt):
        raise _error("customer-deposit candidate does not replay exactly")
    return rebuilt


def build_gemini_json_indexed_customer_deposit_query_evidence_v1(
    *,
    selected_document_axis: Sequence[dict[str, Any]],
    selected_page_axis: Sequence[dict[str, Any]],
    document_clusters: Sequence[dict[str, Any]],
    query_policy_sha256: str,
) -> dict[str, Any]:
    """Seal the complete selected document/page axis and one disposition per document."""

    documents = canonical_clone_v1(list(selected_document_axis))
    pages = canonical_clone_v1(list(selected_page_axis))
    clusters = canonical_clone_v1(list(document_clusters))
    dispositions = [
        {
            "cluster": canonical_clone_v1(cluster),
            "disposition": cluster.get("status"),
            "document_id": cluster.get("document_id"),
            "document_ordinal": cluster.get("document_ordinal"),
            "source_logical_name": cluster.get("source_logical_name"),
            "source_sha256": cluster.get("source_sha256"),
        }
        for cluster in clusters
    ]
    accepted = [
        canonical_clone_v1(cluster) for cluster in clusters if cluster.get("status") == READY
    ]
    receipt = {
        "accepted_cluster_axis_sha256": canonical_json_sha256_v1(accepted),
        "accepted_cluster_count": len(accepted),
        "accepted_fragment_count": sum(len(item.get("component_regions", [])) for item in accepted),
        "candidate_disposition_axis_sha256": canonical_json_sha256_v1(dispositions),
        "candidate_disposition_count": len(dispositions),
        "disposition_counts": {
            status: sum(item.get("disposition") == status for item in dispositions)
            for status in (READY, NOT_OBSERVED, UNRESOLVED)
        },
        "query_policy_sha256": query_policy_sha256,
        "selected_document_axis_sha256": canonical_json_sha256_v1(documents),
        "selected_document_count": len(documents),
        "selected_page_axis_sha256": canonical_json_sha256_v1(pages),
        "selected_page_count": len(pages),
        "selected_page_json_frontier_sha256": canonical_json_sha256_v1(
            [item.get("page_json_version_id") for item in pages]
        ),
    }
    material = {
        "accepted_clusters": accepted,
        "candidate_dispositions": dispositions,
        "format_version": INDEXED_QUERY_EVIDENCE_FORMAT_VERSION,
        "query_receipt": receipt,
        "selected_document_axis": documents,
        "selected_page_axis": pages,
    }
    return {
        **material,
        "query_evidence_id": "gjficdqev1:evidence:" + canonical_json_sha256_v1(material),
    }


def validate_gemini_json_indexed_customer_deposit_query_evidence_v1(
    value: Any, *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate every internal axis/hash in customer-deposit indexed evidence."""

    fields = {
        "accepted_clusters",
        "candidate_dispositions",
        "format_version",
        "query_evidence_id",
        "query_receipt",
        "selected_document_axis",
        "selected_page_axis",
    }
    if (
        compiled_specs.get("engine_format_version") != ENGINE_FORMAT_VERSION
        or type(value) is not dict
        or set(value) != fields
        or value.get("format_version") != INDEXED_QUERY_EVIDENCE_FORMAT_VERSION
        or any(
            type(value.get(field)) is not list
            for field in (
                "accepted_clusters",
                "candidate_dispositions",
                "selected_document_axis",
                "selected_page_axis",
            )
        )
        or type(value.get("query_receipt")) is not dict
    ):
        raise _error("indexed customer-deposit query evidence is invalid")
    documents = value["selected_document_axis"]
    dispositions = value["candidate_dispositions"]
    pages = value["selected_page_axis"]
    document_fields = {
        "document_id",
        "document_ordinal",
        "source_logical_name",
        "source_sha256",
    }
    if not documents or len(documents) != len(dispositions):
        raise _error("indexed customer-deposit document disposition axis is incomplete")
    document_by_ordinal = {}
    for ordinal, document in enumerate(documents, start=1):
        if (
            type(document) is not dict
            or set(document) != document_fields
            or document.get("document_ordinal") != ordinal
            or _DOCUMENT_ID.fullmatch(document.get("document_id", "")) is None
            or type(document.get("source_logical_name")) is not str
            or not document["source_logical_name"]
            or _SHA256.fullmatch(document.get("source_sha256", "")) is None
        ):
            raise _error("indexed customer-deposit selected document axis is invalid")
        document_by_ordinal[ordinal] = document
    page_fields = document_fields | {
        "page_json_version_id",
        "physical_page",
        "selected_page_ordinal",
    }
    prior_document_ordinal = 0
    per_document_page_ordinal: dict[int, int] = defaultdict(int)
    page_versions = []
    for page in pages:
        document = (
            document_by_ordinal.get(page.get("document_ordinal")) if type(page) is dict else None
        )
        if (
            type(page) is not dict
            or set(page) != page_fields
            or document is None
            or any(page.get(field) != document[field] for field in document_fields)
            or _PAGE_VERSION.fullmatch(page.get("page_json_version_id", "")) is None
            or type(page.get("physical_page")) is not int
            or page["physical_page"] <= 0
            or type(page.get("selected_page_ordinal")) is not int
            or page["selected_page_ordinal"] <= 0
            or page["document_ordinal"] < prior_document_ordinal
        ):
            raise _error("indexed customer-deposit selected page axis is invalid")
        prior_document_ordinal = page["document_ordinal"]
        per_document_page_ordinal[page["document_ordinal"]] += 1
        if page["selected_page_ordinal"] != per_document_page_ordinal[page["document_ordinal"]]:
            raise _error("indexed customer-deposit selected page order is incomplete")
        page_versions.append(page["page_json_version_id"])
    if len(page_versions) != len(set(page_versions)) or set(per_document_page_ordinal) != set(
        document_by_ordinal
    ):
        raise _error("indexed customer-deposit selected page frontier is duplicate or incomplete")
    accepted_projection = []
    for ordinal, (document, disposition) in enumerate(zip(documents, dispositions, strict=True), 1):
        cluster = disposition.get("cluster") if type(disposition) is dict else None
        if (
            type(disposition) is not dict
            or set(disposition) != document_fields | {"cluster", "disposition"}
            or any(disposition.get(field) != document[field] for field in document_fields)
            or disposition.get("disposition") not in {READY, NOT_OBSERVED, UNRESOLVED}
            or type(cluster) is not dict
            or cluster.get("document_ordinal") != ordinal
            or any(cluster.get(field) != document[field] for field in document_fields)
            or cluster.get("status") != disposition["disposition"]
            or cluster.get("cluster_id")
            != "gjfcdfcv1:cluster:"
            + canonical_json_sha256_v1(
                {
                    key: canonical_clone_v1(item)
                    for key, item in cluster.items()
                    if key != "cluster_id"
                }
            )
        ):
            raise _error("indexed customer-deposit disposition cluster binding drifted")
        regions = cluster.get("component_regions")
        reasons = cluster.get("reasons")
        if (
            type(reasons) is not list
            or reasons != sorted(set(reasons))
            or any(type(reason) is not str or not reason for reason in reasons)
            or (cluster["status"] == READY and (not regions or reasons))
            or (cluster["status"] == NOT_OBSERVED and regions)
            or (cluster["status"] == UNRESOLVED and (not reasons or regions))
        ):
            raise _error("indexed customer-deposit disposition semantics drifted")
        if cluster["status"] == READY:
            checked_regions = _region_axis(regions)
            if any(
                region["document_ordinal"] != ordinal
                or region["document_id"] != document["document_id"]
                or region["source_logical_name"] != document["source_logical_name"]
                or region["source_sha256"] != document["source_sha256"]
                for region in checked_regions
            ):
                raise _error("indexed customer-deposit accepted region identity drifted")
            accepted_projection.append(cluster)
    if not same_typed_json_v1(value["accepted_clusters"], accepted_projection):
        raise _error("indexed customer-deposit accepted cluster projection drifted")
    receipt = value["query_receipt"]
    expected_receipt = {
        "accepted_cluster_axis_sha256": canonical_json_sha256_v1(accepted_projection),
        "accepted_cluster_count": len(accepted_projection),
        "accepted_fragment_count": sum(
            len(item["component_regions"]) for item in accepted_projection
        ),
        "candidate_disposition_axis_sha256": canonical_json_sha256_v1(dispositions),
        "candidate_disposition_count": len(dispositions),
        "disposition_counts": {
            status: sum(item["disposition"] == status for item in dispositions)
            for status in (READY, NOT_OBSERVED, UNRESOLVED)
        },
        "query_policy_sha256": canonical_json_sha256_v1(compiled_specs["query_policy"]),
        "selected_document_axis_sha256": canonical_json_sha256_v1(documents),
        "selected_document_count": len(documents),
        "selected_page_axis_sha256": canonical_json_sha256_v1(pages),
        "selected_page_count": len(pages),
        "selected_page_json_frontier_sha256": canonical_json_sha256_v1(page_versions),
    }
    if not same_typed_json_v1(receipt, expected_receipt):
        raise _error("indexed customer-deposit query receipt drifted")
    material = {key: canonical_clone_v1(value[key]) for key in fields - {"query_evidence_id"}}
    if value["query_evidence_id"] != "gjficdqev1:evidence:" + canonical_json_sha256_v1(material):
        raise _error("indexed customer-deposit query evidence identity drifted")
    return canonical_clone_v1(value)


def validate_gemini_json_customer_deposit_sweep_query_bindings_v1(
    *, trials: Any, indexed_query_evidence: Any, compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Bind every trial and candidate to its exhaustive selected-document disposition."""

    evidence = validate_gemini_json_indexed_customer_deposit_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
    documents = evidence["selected_document_axis"]
    if type(trials) is not list or len(trials) != len(documents):
        raise _error("customer-deposit sweep trial axis is incomplete")
    accepted_by_ordinal = {item["document_ordinal"]: item for item in evidence["accepted_clusters"]}
    for ordinal, (trial, document, disposition) in enumerate(
        zip(trials, documents, evidence["candidate_dispositions"], strict=True), start=1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("source_logical_name") != document["source_logical_name"]
            or trial.get("source_sha256") != document["source_sha256"]
            or type(trial.get("candidates")) is not list
            or trial.get("candidate_count") != len(trial["candidates"])
        ):
            raise _error("customer-deposit sweep trial identity drifted")
        if disposition["disposition"] == READY:
            cluster = accepted_by_ordinal[ordinal]
            if len(trial["candidates"]) != 1:
                raise _error("customer-deposit accepted document needs exactly one candidate")
            candidate = trial["candidates"][0]
            if not same_typed_json_v1(
                candidate.get("component_regions"), cluster["component_regions"]
            ):
                raise _error("customer-deposit candidate region binding drifted")
            if candidate.get("status") == READY:
                if (
                    trial.get("status") != READY
                    or trial.get("selected_candidate_id") != candidate.get("candidate_id")
                    or not same_typed_json_v1(trial.get("mappings"), candidate.get("mappings"))
                    or trial.get("reasons")
                ):
                    raise _error("customer-deposit READY trial binding drifted")
            elif (
                trial.get("status") != UNRESOLVED
                or trial.get("selected_candidate_id") is not None
                or trial.get("mappings")
                or trial.get("reasons") != candidate.get("reasons")
            ):
                raise _error("customer-deposit unresolved candidate binding drifted")
        elif disposition["disposition"] == NOT_OBSERVED:
            if (
                trial.get("status") != NOT_OBSERVED
                or trial["candidates"]
                or trial.get("mappings")
                or trial.get("reasons")
                or trial.get("selected_candidate_id") is not None
            ):
                raise _error("customer-deposit not-observed trial binding drifted")
        elif (
            trial.get("status") != UNRESOLVED
            or trial["candidates"]
            or trial.get("mappings")
            or trial.get("selected_candidate_id") is not None
            or trial.get("reasons") != disposition["cluster"]["reasons"]
        ):
            raise _error("customer-deposit unresolved query disposition binding drifted")
    return canonical_clone_v1(trials)
