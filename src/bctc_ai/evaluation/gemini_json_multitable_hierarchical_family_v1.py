"""Generic multi-table hierarchical note closure over selected Gemini JSON.

Gemini is only the source reader.  This engine inventories every MONEY table
inside one explicit owner/reset fence, resolves period and unit axes, preserves
unmapped source rows, and proves table-local hierarchy/total equations before
emitting schema mappings.  Family semantics are data-only topology,
evaluation, and schema-binding specs; there is no bank, filename, page, note,
value, or prompt routing.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from itertools import product
from typing import Any

from bctc_ai.evaluation.accounting_family_topology_v1 import (
    compile_accounting_family_topology_spec_v1,
)
from bctc_ai.evaluation.gemini_json_customer_deposit_family_v1 import (
    _compile_units,
    _document_unit_context_axis,
    _source_table,
    _unit_axis,
)
from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import (
    _header_text,
    _normalized,
    _path_has_role,
    _row_role_match_modes,
)
from bctc_ai.evaluation.gemini_json_other_long_term_investments_family_v1 import (
    _global_records,
    _heading_marker_matches,
    _local_equation,
    _local_record,
    _marker_matches,
    _page_record_axis,
    _row_local_record,
    _semantic_period_roles,
    _source_money,
    _surface_dates,
    _table_lane_axis,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

ENGINE_FORMAT_VERSION = "GEMINI_JSON_MULTITABLE_HIERARCHICAL_ACCOUNTING_FAMILY_V1"
INDEXED_QUERY_EVIDENCE_FORMAT_VERSION = (
    "GEMINI_JSON_INDEXED_MULTITABLE_HIERARCHICAL_QUERY_EVIDENCE_V1"
)
EVALUATION_FORMAT_VERSION = "ACCOUNTING_MULTITABLE_HIERARCHICAL_FAMILY_EVALUATION_SPEC_V1"
SCHEMA_FORMAT_VERSION = "ACCOUNTING_MULTITABLE_HIERARCHICAL_SCHEMA_BINDING_SPEC_V1"
READY = "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
NOT_OBSERVED = "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
UNRESOLVED = "UNRESOLVED_GEMINI_JSON_FAMILY"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_DECLARATIVE_MULTITABLE_HIERARCHICAL_"
    "OWNER_RESET_FENCE_EXHAUSTIVE_MONEY_TABLE_SOURCE_ONLY_UNMAPPED_DIRECT_"
    "FRONTIER_PERIOD_UNIT_SUBTOTAL_TOTAL_ROLLFORWARD_ALL_LANE_CLOSURE_SCHEMA_"
    "MAPPING_PROPOSAL_ONLY_NO_GEOMETRY_OCR_BANK_FILE_PAGE_NOTE_VALUE_PROMPT_"
    "ROUTING_BACKSOLVE_CANONICAL_OR_EXPORT_AUTHORITY"
)

_PAGE_VERSION = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_DOCUMENT_ID = re.compile(r"gfpstorev1:document:[0-9a-f]{64}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SECTION_ID = re.compile(r"s[1-9][0-9]*\Z")
_TABLE_ID = re.compile(r"t[1-9][0-9]*\Z")


class GeminiJsonMultitableHierarchicalFamilyV1Error(ValueError):
    """Selected JSON, declarative specs, or accounting closure drifted."""


def _error(message: str) -> GeminiJsonMultitableHierarchicalFamilyV1Error:
    return GeminiJsonMultitableHierarchicalFamilyV1Error(message)


def _aliases(child: Mapping[str, Any]) -> list[str]:
    return sorted({alias for matcher in child["matchers"] for alias in matcher["aliases"]})


def compile_gemini_json_multitable_hierarchical_family_specs_v1(
    topology_spec: Any, evaluation_spec: Any, schema_binding_spec: Any
) -> dict[str, Any]:
    """Compile a data-only multi-table hierarchical family triplet."""

    try:
        topology = compile_accounting_family_topology_spec_v1(topology_spec)
    except ValueError as exc:
        raise _error("multi-table hierarchical topology spec is invalid") from exc
    evaluation_fields = {
        "aggregate_duplicate_roles",
        "blank_zero_policy",
        "closure_policy",
        "component_policy",
        "corroboration_pairs",
        "context_total_mapping_roles",
        "derived_role_equations",
        "detail_context_roles",
        "family_id",
        "format_version",
        "layout_policy",
        "money_unit_bindings",
        "period_semantics",
        "root_component_roles",
        "role_unit_overrides",
        "table_context_roles",
        "typed_control_exclusions",
    }
    optional_evaluation_fields = {
        "direct_frontier_policy",
        "duplicate_role_aggregation_policy",
        "hierarchy_role_scope_policy",
        "label_only_structural_group_policy",
        "money_metric_policy",
        "owner_surface_kinds",
        "period_lane_policy",
        "row_alias_prefix_roles",
        "structural_marker_policy",
    }
    if (
        type(evaluation_spec) is not dict
        or not evaluation_fields <= set(evaluation_spec)
        or set(evaluation_spec) - evaluation_fields - optional_evaluation_fields
        or evaluation_spec.get("format_version") != EVALUATION_FORMAT_VERSION
        or evaluation_spec.get("family_id") != topology["family_id"]
        or evaluation_spec.get("blank_zero_policy") != "ZERO_ONLY_AFTER_COMPLETE_EQUATION_EXACT"
        or evaluation_spec.get("closure_policy")
        != "EXACT_SOURCE_DIRECT_FRONTIER_SUBTOTAL_TOTAL_AND_CONFIGURED_ROOT_ALL_LANES"
        or evaluation_spec.get("component_policy")
        != (
            "ONE_EXPLICIT_OWNER_RESET_FENCE_WITH_CONTIGUOUS_DECLARED_LEADING_"
            "ROOT_COMPONENTS_EXHAUSTIVE_MONEY_TABLE_INVENTORY"
        )
        or evaluation_spec.get("layout_policy")
        != "TWO_PERIOD_COLUMNS_OR_ORDERED_PERIOD_TABLES_WITH_LOCAL_SOURCE_PROVENANCE"
        or evaluation_spec.get("period_semantics") != "CURRENT_AND_COMPARATIVE_SNAPSHOT"
        or type(evaluation_spec.get("typed_control_exclusions")) is not list
        or type(evaluation_spec.get("role_unit_overrides")) is not list
    ):
        raise _error("multi-table hierarchical evaluation spec is invalid")
    owner_surface_kinds = evaluation_spec.get(
        "owner_surface_kinds",
        ["SECTION_TITLE", "SECTION_NARRATIVE", "TABLE_TITLE"],
    )
    if (
        type(owner_surface_kinds) is not list
        or not owner_surface_kinds
        or len(owner_surface_kinds) != len(set(owner_surface_kinds))
        or any(
            kind not in {"SECTION_TITLE", "SECTION_NARRATIVE", "TABLE_TITLE"}
            for kind in owner_surface_kinds
        )
    ):
        raise _error("multi-table hierarchical owner surface kinds are invalid")
    direct_frontier_policy = evaluation_spec.get(
        "direct_frontier_policy", "ALL_EXACT_SOURCE_FRONTIERS_UNIQUE"
    )
    if direct_frontier_policy not in {
        "ALL_EXACT_SOURCE_FRONTIERS_UNIQUE",
        "CANONICAL_PROVEN_TOP_LEVEL_DIRECT_FRONTIER",
    }:
        raise _error("multi-table hierarchical direct frontier policy is invalid")
    hierarchy_role_scope_policy = evaluation_spec.get(
        "hierarchy_role_scope_policy", "UNSCOPED_CONTEXT_FALLBACK"
    )
    if hierarchy_role_scope_policy not in {
        "UNSCOPED_CONTEXT_FALLBACK",
        "PATH_DECLARED_ROLES_FIRST",
    }:
        raise _error("multi-table hierarchical hierarchy role scope policy is invalid")
    label_only_structural_group_policy = evaluation_spec.get(
        "label_only_structural_group_policy", "DISABLED"
    )
    if label_only_structural_group_policy not in {
        "DISABLED",
        "DIRECT_CHILD_FRONTIER_ONLY_AFTER_SOURCE_TOTAL_CLOSURE",
        "SINGLE_DIRECT_CHILD_ONLY_AFTER_SOURCE_TOTAL_CLOSURE",
    }:
        raise _error("multi-table hierarchical label-only structural group policy is invalid")
    structural_marker_policy = evaluation_spec.get("structural_marker_policy", "WHOLE_SURFACE_ONLY")
    if structural_marker_policy not in {
        "WHOLE_SURFACE_ONLY",
        "WHOLE_SURFACE_AND_INDIVIDUAL_LINES",
    }:
        raise _error("multi-table hierarchical structural marker policy is invalid")
    money_metric_policy = evaluation_spec.get("money_metric_policy", "GENERIC_AMOUNT_ONLY")
    if money_metric_policy not in {
        "CARRYING_VALUE_PREFERRED_WITH_EXACT_PERIOD_AND_INSTRUMENT_AXES",
        "GENERIC_AMOUNT_ONLY",
    }:
        raise _error("multi-table hierarchical money metric policy is invalid")
    period_lane_policy = evaluation_spec.get(
        "period_lane_policy", "CURRENT_AND_COMPARATIVE_REQUIRED"
    )
    if period_lane_policy not in {
        "CURRENT_AND_COMPARATIVE_REQUIRED",
        "CURRENT_REQUIRED_COMPARATIVE_IF_SOURCE_VISIBLE",
    }:
        raise _error("multi-table hierarchical period lane policy is invalid")
    duplicate_role_aggregation_policy = evaluation_spec.get(
        "duplicate_role_aggregation_policy", "DECLARED_SAME_ROLE_SOURCE_ROW_SUM"
    )
    if duplicate_role_aggregation_policy not in {
        "DECLARED_SAME_ROLE_SOURCE_ROW_SUM",
        "ALL_SOURCE_ROWS_CONSUMED_BY_EXACT_TABLE_FRONTIER",
    }:
        raise _error("multi-table hierarchical duplicate role aggregation policy is invalid")
    child_by_role = {child["role"]: child for child in topology["children"]}
    roles = set(child_by_role)

    def role_axis(field: str, *, allow_empty: bool = False) -> list[str]:
        value = evaluation_spec.get(field)
        if (
            type(value) is not list
            or (not value and not allow_empty)
            or any(type(role) is not str or role not in roles for role in value)
            or len(value) != len(set(value))
        ):
            raise _error(f"multi-table hierarchical {field} is invalid")
        return list(value)

    table_context_roles = role_axis("table_context_roles")
    detail_context_roles = role_axis("detail_context_roles")
    context_total_mapping_roles = role_axis("context_total_mapping_roles")
    root_component_roles = role_axis("root_component_roles")
    aggregate_duplicate_roles = role_axis("aggregate_duplicate_roles", allow_empty=True)
    row_alias_prefix_roles = (
        role_axis("row_alias_prefix_roles", allow_empty=True)
        if "row_alias_prefix_roles" in evaluation_spec
        else []
    )
    role_unit_overrides = {}
    for item in evaluation_spec.get("role_unit_overrides", []):
        if (
            type(item) is not dict
            or set(item) != {"role", "unit"}
            or item.get("role") not in roles
            or item["role"] in role_unit_overrides
            or type(item.get("unit")) is not str
            or not item["unit"]
        ):
            raise _error("multi-table hierarchical role unit override is invalid")
        role_unit_overrides[item["role"]] = item["unit"]
    corroboration_pairs = []
    for pair in evaluation_spec.get("corroboration_pairs", []):
        if (
            type(pair) is not dict
            or set(pair) != {"carrier_role", "detail_role"}
            or pair["carrier_role"] not in roles
            or pair["detail_role"] not in roles
            or pair["carrier_role"] == pair["detail_role"]
            or pair in corroboration_pairs
        ):
            raise _error("multi-table hierarchical corroboration pair is invalid")
        corroboration_pairs.append(canonical_clone_v1(pair))
    derived_role_equations = []
    derived_result_roles = set()
    for equation in evaluation_spec.get("derived_role_equations", []):
        if (
            type(equation) is not dict
            or set(equation) != {"component_roles", "result_role"}
            or equation.get("result_role") not in roles
            or equation["result_role"] in derived_result_roles
            or type(equation.get("component_roles")) is not list
            or len(equation["component_roles"]) < 2
            or len(equation["component_roles"]) != len(set(equation["component_roles"]))
            or any(role not in roles for role in equation["component_roles"])
            or equation["result_role"] in equation["component_roles"]
        ):
            raise _error("multi-table hierarchical derived role equation is invalid")
        derived_result_roles.add(equation["result_role"])
        derived_role_equations.append(canonical_clone_v1(equation))
    if any(
        child_by_role[role]["role_kind"] not in {"STRUCTURAL_GROUP", "SUBTOTAL", "TOTAL"}
        for role in table_context_roles
    ):
        raise _error("multi-table hierarchical context role is not structural")
    if set(table_context_roles) & set(detail_context_roles):
        raise _error("multi-table hierarchical detail context role overlaps structural context")
    exclusions = []
    for item in evaluation_spec["typed_control_exclusions"]:
        surface_kinds = item.get(
            "surface_kinds", ["SECTION_TITLE", "SECTION_NARRATIVE", "TABLE_TITLE"]
        )
        if (
            type(item) is not dict
            or set(item)
            not in (
                {"aliases", "disposition"},
                {"aliases", "disposition", "surface_kinds"},
            )
            or type(item.get("disposition")) is not str
            or not item["disposition"]
            or type(item.get("aliases")) is not list
            or not item["aliases"]
            or any(type(alias) is not str or not _normalized(alias) for alias in item["aliases"])
            or type(surface_kinds) is not list
            or not surface_kinds
            or len(surface_kinds) != len(set(surface_kinds))
            or any(
                kind not in {"SECTION_TITLE", "SECTION_NARRATIVE", "TABLE_TITLE", "COLUMN_HEADER"}
                for kind in surface_kinds
            )
        ):
            raise _error("multi-table hierarchical typed control exclusion is invalid")
        exclusion = {
            "aliases": sorted({_normalized(alias) for alias in item["aliases"]}),
            "disposition": item["disposition"],
        }
        if "surface_kinds" in item:
            exclusion["surface_kinds"] = sorted(surface_kinds)
        exclusions.append(exclusion)
    try:
        unit_bindings, unit_binding_by_alias = _compile_units(
            evaluation_spec["money_unit_bindings"]
        )
    except ValueError as exc:
        raise _error("multi-table hierarchical unit bindings are invalid") from exc

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
        or schema_binding_spec.get("root_mapping_policy")
        not in {
            "SOURCE_VISIBLE_TOTAL_PROVEN_BY_EXACT_EQUATION_ONLY",
            "SOURCE_VISIBLE_TOTAL_OR_COMPLETE_TOP_LEVEL_COMPONENT_SUM",
        }
        or schema_binding_spec.get("schema_period_type") != "SNAPSHOT"
        or type(schema_binding_spec.get("role_bindings")) is not list
    ):
        raise _error("multi-table hierarchical schema binding spec is invalid")
    bindings: dict[str, int] = {}
    identities = {schema_binding_spec["family_root_report_norm_id"]}
    for raw in schema_binding_spec["role_bindings"]:
        if (
            type(raw) is not dict
            or set(raw) != {"report_norm_id", "role"}
            or raw.get("role") not in roles
            or raw["role"] in bindings
            or type(raw.get("report_norm_id")) is not int
            or raw["report_norm_id"] <= 0
            or raw["report_norm_id"] in identities
        ):
            raise _error("multi-table hierarchical schema role binding is invalid")
        bindings[raw["role"]] = raw["report_norm_id"]
        identities.add(raw["report_norm_id"])
    if not bindings or not set(root_component_roles) <= set(bindings):
        raise _error("multi-table hierarchical schema frontier is incomplete")
    aliases_by_role = {role: _aliases(child) for role, child in child_by_role.items()}
    presence_anchor_roles = sorted(
        role
        for role, child in child_by_role.items()
        if any(matcher["presence_anchor"] for matcher in child["matchers"])
    )
    query_policy = {
        "hard_negative_aliases": canonical_clone_v1(topology["hard_negative_aliases"]),
        "leading_component_policy": evaluation_spec["component_policy"],
        "owner_aliases": canonical_clone_v1(topology["parent"]["aliases"]),
        "reset_aliases": canonical_clone_v1(topology["structural_reset_aliases"]),
    }
    if "owner_surface_kinds" in evaluation_spec:
        # Preserve the exact compiled policy/hash of existing released families
        # while binding every family that opts into a narrower source surface.
        query_policy["owner_surface_kinds"] = list(owner_surface_kinds)
    if "hierarchy_role_scope_policy" in evaluation_spec:
        query_policy["hierarchy_role_scope_policy"] = hierarchy_role_scope_policy
    if "structural_marker_policy" in evaluation_spec:
        query_policy["structural_marker_policy"] = structural_marker_policy
    if "row_alias_prefix_roles" in evaluation_spec:
        query_policy["row_alias_prefix_roles"] = row_alias_prefix_roles
    return {
        "aggregate_duplicate_roles": aggregate_duplicate_roles,
        "aliases_by_role": aliases_by_role,
        "bindings": bindings,
        "claim_boundary": CLAIM_BOUNDARY,
        "child_by_role": child_by_role,
        "currency_aliases": {},
        "corroboration_pairs": corroboration_pairs,
        "context_total_mapping_roles": context_total_mapping_roles,
        "derived_role_equations": derived_role_equations,
        "detail_context_roles": detail_context_roles,
        "direct_frontier_policy": direct_frontier_policy,
        "duplicate_role_aggregation_policy": duplicate_role_aggregation_policy,
        "engine_format_version": ENGINE_FORMAT_VERSION,
        "evaluation": canonical_clone_v1(evaluation_spec),
        "matchers_by_role": {
            role: canonical_clone_v1(child["matchers"]) for role, child in child_by_role.items()
        },
        "output_role_order": [item["role"] for item in schema_binding_spec["role_bindings"]],
        "label_only_structural_group_policy": label_only_structural_group_policy,
        "money_metric_policy": money_metric_policy,
        "period_lane_policy": period_lane_policy,
        "presence_anchor_roles": presence_anchor_roles,
        "query_policy": query_policy,
        "root_component_roles": root_component_roles,
        "role_unit_overrides": role_unit_overrides,
        "row_alias_prefix_roles": row_alias_prefix_roles,
        "schema": canonical_clone_v1(schema_binding_spec),
        "table_context_roles": table_context_roles,
        "topology": topology,
        "typed_control_exclusions": exclusions,
        "unit_binding_by_alias": unit_binding_by_alias,
        "unit_bindings": unit_bindings,
    }


def _surface_axis(section: Mapping[str, Any], table: Mapping[str, Any]) -> list[Any]:
    values: list[Any] = [section.get("title_exact"), table.get("title_exact")]
    narratives = section.get("narratives_exact")
    if type(narratives) is list:
        values.extend(narratives)
    return values


def _owner_surface_axis(
    section: Mapping[str, Any], table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> list[Any]:
    kinds = compiled_specs["query_policy"].get(
        "owner_surface_kinds",
        ["SECTION_TITLE", "SECTION_NARRATIVE", "TABLE_TITLE"],
    )
    values = []
    if "SECTION_TITLE" in kinds:
        values.append(section.get("title_exact"))
    if "SECTION_NARRATIVE" in kinds:
        narratives = section.get("narratives_exact")
        if type(narratives) is list:
            values.extend(narratives)
    if "TABLE_TITLE" in kinds:
        values.append(table.get("title_exact"))
    return values


def _heading_surface_matches(
    value: Any, aliases: Sequence[str], *, compiled_specs: Mapping[str, Any]
) -> list[str]:
    surfaces = [value]
    if (
        compiled_specs["query_policy"].get("structural_marker_policy")
        == "WHOLE_SURFACE_AND_INDIVIDUAL_LINES"
        and type(value) is str
    ):
        surfaces.extend(line for line in value.splitlines() if line.strip())
    return sorted(
        {
            alias
            for surface in surfaces
            if (alias := _heading_marker_matches(surface, aliases)) is not None
        }
    )


def _contains_alias(value: Any, alias: str) -> bool:
    folded = _normalized(value)
    alias = _normalized(alias)
    return bool(folded and alias and (folded == alias or f" {alias} " in f" {folded} "))


def _owner_visible(
    section: Mapping[str, Any], table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> bool:
    return any(
        _contains_alias(value, alias)
        for value in _owner_surface_axis(section, table, compiled_specs=compiled_specs)
        for alias in compiled_specs["query_policy"]["owner_aliases"]
    )


def _typed_control_disposition(
    page_json: Mapping[str, Any],
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
) -> str | None:
    if page_json.get("status") == "PRIMARY_FINANCIAL_STATEMENT" or (
        section.get("content_kind") == "PRIMARY_STATEMENT"
        and section.get("statement_type") == "BALANCE_SHEET"
    ):
        return "PRIMARY_FINANCIAL_STATEMENT_SUMMARY"
    columns = table.get("columns")
    for exclusion in compiled_specs["typed_control_exclusions"]:
        kinds = exclusion.get(
            "surface_kinds", ["SECTION_TITLE", "SECTION_NARRATIVE", "TABLE_TITLE"]
        )
        surfaces = []
        if "SECTION_TITLE" in kinds:
            surfaces.append(_normalized(section.get("title_exact")))
        if "SECTION_NARRATIVE" in kinds:
            narratives = section.get("narratives_exact")
            if type(narratives) is list:
                surfaces.extend(_normalized(value) for value in narratives)
        if "TABLE_TITLE" in kinds:
            surfaces.append(_normalized(table.get("title_exact")))
        if "COLUMN_HEADER" in kinds and type(columns) is list:
            # Untitled control tables can be distinguishable only by declared
            # metric headers.  This scope is opt-in so a shared section
            # narrative cannot accidentally exclude its accounting sibling.
            surfaces.extend(
                _normalized(_header_text(column)) for column in columns if type(column) is dict
            )
        if any(
            surface and any(alias in surface for alias in exclusion["aliases"])
            for surface in surfaces
        ):
            return exclusion["disposition"]
    if type(columns) is list and not any(
        type(column) is dict and column.get("value_kind") == "MONEY" for column in columns
    ):
        return "NO_MONEY_VALUE_AXIS"
    return None


def _context_roles(
    section: Mapping[str, Any], table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> list[str]:
    # A section heading scopes its sole table.  In a multi-table section it is
    # only an umbrella: sibling populations must establish context from their
    # own table title or from a coherent row-role population.  This prevents a
    # summary heading from being copied onto every later detail/roll-forward.
    tables = section.get("tables")
    context_surfaces = [table.get("title_exact")]
    if type(tables) is list and len(tables) == 1:
        context_surfaces.append(section.get("title_exact"))
    matches = []
    for role in [
        *compiled_specs["table_context_roles"],
        *compiled_specs["detail_context_roles"],
    ]:
        aliases = compiled_specs["aliases_by_role"][role]
        score = max(
            (
                len(_normalized(alias))
                for value in context_surfaces
                for alias in aliases
                if _contains_alias(value, alias)
            ),
            default=None,
        )
        if score is not None:
            matches.append((score, role))
    if not matches:
        return []
    maximum = max(score for score, _role in matches)
    return sorted(role for score, role in matches if score == maximum)


def _transposed_column_role_hits(
    columns: Sequence[Any], *, compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Bind instrument columns from declared structural aliases only.

    This orientation is opt-in.  A column is accepted only when one unique
    longest declared structural role matches its full header surface.  Values
    never choose the role, and the ordinary row-oriented path is unchanged.
    """

    if (
        compiled_specs["money_metric_policy"]
        != "CARRYING_VALUE_PREFERRED_WITH_EXACT_PERIOD_AND_INSTRUMENT_AXES"
    ):
        return []
    hits = []
    for column_ordinal, column in enumerate(columns, start=1):
        if type(column) is not dict or column.get("value_kind") != "MONEY":
            continue
        header = _header_text(column)
        matches = []
        for role in compiled_specs["table_context_roles"]:
            for alias in compiled_specs["aliases_by_role"][role]:
                if _contains_alias(header, alias):
                    matches.append((len(_normalized(alias)), role, alias))
        if not matches:
            continue
        maximum = max(score for score, _role, _alias in matches)
        roles = sorted({role for score, role, _alias in matches if score == maximum})
        if len(roles) != 1:
            hits.append(
                {
                    "column_ordinal": column_ordinal,
                    "matched_roles": roles,
                    "source_header_exact": header,
                    "status": "AMBIGUOUS_LONGEST_DECLARED_INSTRUMENT_ROLE",
                }
            )
            continue
        role = roles[0]
        hits.append(
            {
                "column_ordinal": column_ordinal,
                "role": role,
                "source_header_exact": header,
                "status": "EXACT_UNIQUE_LONGEST_DECLARED_INSTRUMENT_ROLE",
            }
        )
    return hits


def _transposed_row_role_hits(
    rows: Sequence[Any],
    column_role_hits: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Resolve tenor rows inside each already authenticated instrument column."""

    parent_roles = sorted(
        {hit["role"] for hit in column_role_hits if hit.get("status", "").startswith("EXACT_")}
    )
    if not parent_roles:
        return []
    hits = []
    for row_ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict or type(row.get("values_exact")) is not list:
            continue
        for parent_role in parent_roles:
            try:
                modes = _row_role_match_modes(
                    row,
                    topology=compiled_specs["topology"],
                    aliases_by_role=compiled_specs["aliases_by_role"],
                    fallback_within_role=parent_role,
                    enable_declared_equivalences=True,
                )
            except ValueError:
                modes = {}
            roles = sorted(
                role
                for role in modes
                if role in compiled_specs["child_by_role"]
                and compiled_specs["child_by_role"][role]["role_kind"] != "STRUCTURAL_GROUP"
                and any(
                    matcher["within_role"] == parent_role
                    for matcher in compiled_specs["matchers_by_role"][role]
                )
            )
            if len(roles) == 1:
                hits.append(
                    {
                        "parent_role": parent_role,
                        "role": roles[0],
                        "row_ordinal": row_ordinal,
                        "source_order": row_ordinal,
                    }
                )
    return hits


def classify_gemini_json_multitable_hierarchical_table_v1(
    page_json: Any,
    section: Any,
    table: Any,
    *,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Inventory one table without assigning document-level ownership."""

    if type(page_json) is not dict or type(section) is not dict or type(table) is not dict:
        raise _error("multi-table hierarchical source table is invalid")
    columns = table.get("columns")
    rows = table.get("rows")
    if type(columns) is not list or type(rows) is not list:
        raise _error("multi-table hierarchical source axes are invalid")
    money_ordinals = [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    transposed_column_role_hits = _transposed_column_role_hits(
        columns, compiled_specs=compiled_specs
    )
    transposed_row_role_hits = _transposed_row_role_hits(
        rows, transposed_column_role_hits, compiled_specs=compiled_specs
    )
    role_hits = []
    matched_scopes_by_hit: dict[tuple[int, str], set[str]] = {}
    ambiguous_rows = []
    inverted_hierarchy_scope_rows = []
    unscoped_shared_child_rows = []
    unbound_money_rows = []
    total_rows = []
    family_root_row_ordinals = []
    heading_context_roles = _context_roles(section, table, compiled_specs=compiled_specs)
    # Re-evaluate with an artificial sibling so only the table title can
    # contribute.  This preserves whether a role came from an explicit local
    # title or was inferred from the row population/sole-table section title.
    table_title_context_roles = _context_roles(
        {"tables": [table, {}]}, table, compiled_specs=compiled_specs
    )
    fallback_within_role = heading_context_roles[0] if len(heading_context_roles) == 1 else None
    for row_ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict or type(row.get("values_exact")) is not list:
            continue
        values = row["values_exact"]
        if "owner_surface_kinds" in compiled_specs["query_policy"] and _normalized(
            row.get("label_exact")
        ) in set(compiled_specs["query_policy"]["owner_aliases"]):
            family_root_row_ordinals.append(row_ordinal)
        visible = any(
            ordinal <= len(values) and values[ordinal - 1] is not None for ordinal in money_ordinals
        )

        match_cache: dict[str | None, dict[str, str]] = {}

        def match_with_fallback(
            source_row: Mapping[str, Any],
            scope: str | None,
            _match_cache: dict[str | None, dict[str, str]] = match_cache,
        ) -> dict[str, str]:
            if scope not in _match_cache:
                exact_modes = _row_role_match_modes(
                    source_row,
                    topology=compiled_specs["topology"],
                    aliases_by_role=compiled_specs["aliases_by_role"],
                    fallback_within_role=scope,
                    enable_declared_equivalences=True,
                )
                if exact_modes:
                    _match_cache[scope] = exact_modes
                else:
                    # Source labels commonly append an issuer, currency, or
                    # other visible qualifier to a declared accounting
                    # concept.  Resolve that shape from the unique longest
                    # declared alias prefix, never from document identity or
                    # values.  Scoped child aliases remain eligible only in
                    # their authenticated structural parent.
                    label = _normalized(source_row.get("label_exact"))
                    prefix_matches = [
                        (len(_normalized(alias)), role)
                        for role, matchers in compiled_specs["matchers_by_role"].items()
                        if role in compiled_specs["row_alias_prefix_roles"]
                        for matcher in matchers
                        if matcher["within_role"] is None or matcher["within_role"] == scope
                        for alias in matcher["aliases"]
                        if _normalized(alias) and label.startswith(_normalized(alias) + " ")
                    ]
                    maximum = max((length for length, _role in prefix_matches), default=None)
                    roles = sorted(
                        {
                            role
                            for length, role in prefix_matches
                            if maximum is not None and length == maximum
                        }
                    )
                    _match_cache[scope] = (
                        {roles[0]: "UNIQUE_LONGEST_DECLARED_ALIAS_PREFIX"}
                        if len(roles) == 1
                        else {}
                    )
            return _match_cache[scope]

        try:
            modes = match_with_fallback(row, fallback_within_role)
            if not modes and fallback_within_role is not None:
                # A detail table can be scoped by an additive carrier (for
                # example EXTERNAL_RECEIVABLES) whose children are declared
                # under its structural parent. Walk only the unique declared
                # parent chain before considering unrelated family scopes.
                scope = fallback_within_role
                visited = {scope}
                while not modes:
                    parents = {
                        matcher["within_role"]
                        for matcher in compiled_specs["matchers_by_role"].get(scope, [])
                        if matcher["within_role"] is not None
                    }
                    if len(parents) != 1:
                        break
                    scope = next(iter(parents))
                    if scope in visited:
                        break
                    visited.add(scope)
                    modes = match_with_fallback(row, scope)
            # A broad unscoped structural prefix may hide one exact additive
            # role under a nested declared scope.  Look for that refinement
            # only when the first result is structural; scanning every scope
            # for every row would let unrelated branches claim one another.
            if modes and all(
                compiled_specs["child_by_role"][role]["role_kind"] == "STRUCTURAL_GROUP"
                for role in modes
                if role in compiled_specs["child_by_role"]
            ):
                refinements = {
                    role: mode
                    for scope in {
                        *compiled_specs["table_context_roles"],
                        *compiled_specs["detail_context_roles"],
                    }
                    for role, mode in match_with_fallback(row, scope).items()
                    if compiled_specs["child_by_role"][role]["role_kind"] != "STRUCTURAL_GROUP"
                }
                if len(refinements) == 1:
                    modes = {**modes, **refinements}
            if not modes:
                explicit_path_roles = (
                    {
                        role
                        for role, aliases in compiled_specs["aliases_by_role"].items()
                        if _path_has_role(
                            row.get("hierarchy_path_exact"),
                            aliases=aliases,
                            label_exact=row.get("label_exact"),
                        )
                    }
                    if compiled_specs["query_policy"].get("hierarchy_role_scope_policy")
                    == "PATH_DECLARED_ROLES_FIRST"
                    else set()
                )
                scoped_modes = [
                    match_with_fallback(row, role)
                    for role in (
                        explicit_path_roles
                        or {
                            *compiled_specs["table_context_roles"],
                            *compiled_specs["detail_context_roles"],
                        }
                    )
                ]
                modes = {
                    role: mode for candidate in scoped_modes for role, mode in candidate.items()
                }
        except ValueError:
            modes = {"AMBIGUOUS": "AMBIGUOUS"}
        matched = sorted(role for role in modes if role in compiled_specs["child_by_role"])
        raw_label = str(row.get("label_exact") or "")
        structural_suffix = bool(re.search(r"\([^)]*\)\s*\Z", raw_label))
        label_without_suffix = _normalized(re.sub(r"\s*\([^)]*\)\s*\Z", "", raw_label))
        hierarchy_parent_label = any(
            other_ordinal != row_ordinal
            and _row_is_strict_descendant(rows, other_ordinal, row_ordinal)
            for other_ordinal in range(1, len(rows) + 1)
            if type(rows[other_ordinal - 1]) is dict
        )
        if (
            row.get("row_kind") in {"GROUP", "SUBTOTAL", "TOTAL"}
            or structural_suffix
            or hierarchy_parent_label
        ):
            structural_label_roles = sorted(
                role
                for role in compiled_specs["table_context_roles"]
                if any(
                    _normalized(row.get("label_exact")) == _normalized(alias)
                    or (
                        structural_suffix
                        and not raw_label.lstrip().startswith("-")
                        and label_without_suffix == _normalized(alias)
                    )
                    for alias in compiled_specs["aliases_by_role"][role]
                )
            )
            if len(structural_label_roles) == 1:
                matched = structural_label_roles
        if (
            len(matched) == 1
            and compiled_specs["money_metric_policy"]
            == "CARRYING_VALUE_PREFERRED_WITH_EXACT_PERIOD_AND_INSTRUMENT_AXES"
            and compiled_specs["child_by_role"][matched[0]]["role_kind"] == "STRUCTURAL_GROUP"
        ):
            structural_role = matched[0]
            normalized_label = _normalized(row.get("label_exact"))
            ancestor_surfaces = {
                _normalized(value)
                for value in (row.get("hierarchy_path_exact") or [])
                if _normalized(value) and _normalized(value) != normalized_label
            }
            scoped_children = sorted(
                role
                for role in compiled_specs["child_by_role"]
                if compiled_specs["child_by_role"][role]["role_kind"] != "STRUCTURAL_GROUP"
                and any(
                    matcher["within_role"] == structural_role
                    for matcher in compiled_specs["matchers_by_role"][role]
                )
                and any(
                    _normalized(alias) in ancestor_surfaces
                    for alias in compiled_specs["aliases_by_role"][role]
                )
            )
            if scoped_children:
                matched = scoped_children
            if len(scoped_children) == 1:
                inverted_hierarchy_scope_rows.append(
                    {
                        "ancestor_surfaces": sorted(ancestor_surfaces),
                        "parent_role": structural_role,
                        "role": scoped_children[0],
                        "row_ordinal": row_ordinal,
                        "rule": (
                            "EXACT_STRUCTURAL_INSTRUMENT_ROW_SCOPED_BY_UNIQUE_DECLARED_"
                            "TENOR_ANCESTOR"
                        ),
                    }
                )
        if len(matched) == 2:
            kinds = {role: compiled_specs["child_by_role"][role]["role_kind"] for role in matched}
            additive = [role for role in matched if kinds[role] != "STRUCTURAL_GROUP"]
            structural = [role for role in matched if kinds[role] == "STRUCTURAL_GROUP"]
            if len(additive) == len(structural) == 1:
                if row.get("row_kind") in {"GROUP", "SUBTOTAL", "TOTAL"}:
                    matched = structural
                elif str(row.get("label_exact") or "").lstrip().startswith("-"):
                    matched = additive
                else:
                    matched = structural
        if len(matched) > 1:
            declared_scopes = {
                role: {
                    matcher["within_role"]
                    for matcher in compiled_specs["matchers_by_role"][role]
                    if matcher["within_role"] is not None
                }
                for role in matched
            }
            shared_unscoped_tenor = bool(
                compiled_specs["money_metric_policy"]
                == "CARRYING_VALUE_PREFERRED_WITH_EXACT_PERIOD_AND_INSTRUMENT_AXES"
                and all(
                    compiled_specs["child_by_role"][role]["role_kind"] != "STRUCTURAL_GROUP"
                    and len(declared_scopes[role]) == 1
                    for role in matched
                )
                and len({next(iter(declared_scopes[role])) for role in matched}) > 1
                and not any(
                    _path_has_role(
                        row.get("hierarchy_path_exact"),
                        aliases=compiled_specs["aliases_by_role"][scope],
                        label_exact=row.get("label_exact"),
                    )
                    for role in matched
                    for scope in declared_scopes[role]
                )
            )
            if shared_unscoped_tenor:
                unscoped_shared_child_rows.append(
                    {
                        "matched_roles": matched,
                        "row_ordinal": row_ordinal,
                        "rule": "UNSCOPED_MULTI_PARENT_TENOR_RETAINED_SOURCE_ONLY",
                    }
                )
            else:
                ambiguous_rows.append({"matched_roles": matched, "row_ordinal": row_ordinal})
        elif matched:
            role = matched[0]
            matched_scopes_by_hit[(row_ordinal, role)] = {
                matcher["within_role"]
                for matcher in compiled_specs["matchers_by_role"][role]
                if matcher["within_role"] is not None
                and role in match_with_fallback(row, matcher["within_role"])
            }
            role_hits.append(
                {
                    "role": role,
                    "row_kind": row.get("row_kind"),
                    "row_ordinal": row_ordinal,
                    "source_order": row_ordinal,
                }
            )
        elif visible:
            unbound_money_rows.append(row_ordinal)
        if visible and row.get("row_kind") in {"SUBTOTAL", "TOTAL"}:
            total_rows.append(
                {
                    "row_kind": row.get("row_kind"),
                    "row_ordinal": row_ordinal,
                    "source_order": row_ordinal,
                }
            )
    declared_within_roles = {
        scope
        for hit in role_hits
        for scope in matched_scopes_by_hit[(hit["row_ordinal"], hit["role"])]
    }
    anchored_within_roles = {
        scope
        for hit in role_hits
        if hit["role"] in compiled_specs["presence_anchor_roles"]
        for scope in matched_scopes_by_hit[(hit["row_ordinal"], hit["role"])]
        if any(
            matcher["within_role"] == scope and matcher["presence_anchor"]
            for matcher in compiled_specs["matchers_by_role"][hit["role"]]
        )
    }
    continuation_heading = any(
        re.search(r"\b(?:tiep theo|continued)\b", _normalized(value))
        for value in (table.get("title_exact"), section.get("title_exact"))
        if type(value) is str
    )
    table_title_has_context = any(
        _contains_alias(table.get("title_exact"), alias)
        for role in [
            *compiled_specs["table_context_roles"],
            *compiled_specs["detail_context_roles"],
        ]
        for alias in compiled_specs["aliases_by_role"][role]
    )
    if (
        continuation_heading
        and not table_title_has_context
        and len(anchored_within_roles) == 1
        and set(heading_context_roles) != anchored_within_roles
    ):
        # A continuation section heading can repeat the outer note while the
        # sole table is an explicitly anchored inner analysis.  The row
        # population is the stronger table-local context in that case.
        context_roles = sorted(anchored_within_roles)
    elif len(heading_context_roles) == 1:
        context_roles = heading_context_roles
    elif len(anchored_within_roles) == 1:
        context_roles = sorted(anchored_within_roles)
    elif len(declared_within_roles) == 1 and len({hit["role"] for hit in role_hits}) >= 2:
        context_roles = sorted(declared_within_roles)
    else:
        context_roles = heading_context_roles
    if context_roles and context_roles == table_title_context_roles:
        context_resolution_kind = "EXPLICIT_TABLE_TITLE"
    elif context_roles and context_roles == heading_context_roles:
        context_resolution_kind = "EXPLICIT_SOLE_TABLE_SECTION_TITLE"
    elif context_roles:
        context_resolution_kind = "DECLARED_ROW_POPULATION_SCOPE"
    else:
        context_resolution_kind = "NO_CONTEXT_ROLE"
    transposed_row_ordinals = {hit["row_ordinal"] for hit in transposed_row_role_hits}
    if transposed_row_role_hits:
        # In a transposed population the same tenor label intentionally maps
        # to one child under each instrument column.  It is ambiguous only in
        # the row-oriented interpretation, not in the authenticated 2-D axis.
        ambiguous_rows = [
            item for item in ambiguous_rows if item["row_ordinal"] not in transposed_row_ordinals
        ]
    exact_transposed_column_ordinals = {
        hit["column_ordinal"]
        for hit in transposed_column_role_hits
        if hit.get("status", "").startswith("EXACT_")
    }
    transposed_total_column_ordinals = {
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict
        and column.get("value_kind") == "MONEY"
        and ordinal not in exact_transposed_column_ordinals
        and any(
            marker in f" {_normalized(_header_text(column))} "
            for marker in (" tong cong ", " total ")
        )
    }
    transposed_layout_visible = bool(
        exact_transposed_column_ordinals
        and len(transposed_total_column_ordinals) == 1
        and total_rows
    )
    typed_control_disposition = _typed_control_disposition(
        page_json, section, table, compiled_specs=compiled_specs
    )
    column_header_control_dispositions = {
        exclusion["disposition"]
        for exclusion in compiled_specs["typed_control_exclusions"]
        if "COLUMN_HEADER" in exclusion.get("surface_kinds", [])
    }
    typed_control_conflict_disposition = (
        typed_control_disposition
        if typed_control_disposition is not None
        and typed_control_disposition in column_header_control_dispositions
        and bool(role_hits or transposed_row_role_hits or context_roles)
        else None
    )
    material = {
        "ambiguous_rows": ambiguous_rows,
        "context_resolution_kind": context_resolution_kind,
        "context_roles": context_roles,
        "family_presence_anchor_visible": bool(
            family_root_row_ordinals
            or heading_context_roles
            or transposed_layout_visible
            or any(hit["role"] in compiled_specs["presence_anchor_roles"] for hit in role_hits)
        ),
        "money_column_ordinals": money_ordinals,
        "owner_visible": _owner_visible(section, table, compiled_specs=compiled_specs),
        "role_hits": role_hits,
        "total_rows": total_rows,
        "typed_control_disposition": (
            None if typed_control_conflict_disposition is not None else typed_control_disposition
        ),
        "unbound_money_row_ordinals": unbound_money_rows,
    }
    if typed_control_conflict_disposition is not None:
        # A control surface may not erase a simultaneously declared family
        # role.  Preserve both signals and force the owner-fenced cluster to U
        # instead of silently excluding the table.
        material["typed_control_conflict_disposition"] = typed_control_conflict_disposition
    if (
        compiled_specs["money_metric_policy"]
        == "CARRYING_VALUE_PREFERRED_WITH_EXACT_PERIOD_AND_INSTRUMENT_AXES"
    ):
        material["transposed_column_role_hits"] = transposed_column_role_hits
        material["transposed_row_role_hits"] = transposed_row_role_hits
        material["inverted_hierarchy_scope_rows"] = inverted_hierarchy_scope_rows
        material["unscoped_shared_child_rows"] = unscoped_shared_child_rows
        material["layout_orientation"] = (
            "INSTRUMENT_COLUMNS_TENOR_ROWS"
            if transposed_layout_visible
            else "ROW_ROLES_PERIOD_COLUMNS"
        )
    if "owner_surface_kinds" in compiled_specs["query_policy"]:
        material["family_root_row_ordinals"] = family_root_row_ordinals
    return {
        **material,
        "classification_id": "gjmthfcv1:classification:" + canonical_json_sha256_v1(material),
    }


def _classification_roles(classification: Mapping[str, Any]) -> set[str]:
    return {
        *(hit["role"] for hit in classification["role_hits"]),
        *(classification["context_roles"]),
        *(
            hit["role"]
            for hit in classification.get("transposed_column_role_hits", [])
            if hit.get("status", "").startswith("EXACT_")
        ),
        *(hit["role"] for hit in classification.get("transposed_row_role_hits", [])),
    }


def _region(item: Mapping[str, Any], fragment_ordinal: int) -> dict[str, Any]:
    record = item["record"]
    classification = item["classification"]
    return {
        "component_roles": sorted(_classification_roles(classification)),
        "document_id": record["document_id"],
        "document_ordinal": record["document_ordinal"],
        "fragment_ordinal": fragment_ordinal,
        "page_json_version_id": record["page_json_version_id"],
        "physical_page": record["physical_page"],
        "section_id": item["section_id"],
        "selected_page_ordinal": record["selected_page_ordinal"],
        "source_logical_name": record["source_logical_name"],
        "source_sha256": record["source_sha256"],
        "table_id": item["table_id"],
    }


def coalesce_gemini_json_multitable_hierarchical_document_v1(
    *, page_records: Any, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Select exactly one exhaustive explicit owner/reset-fenced cluster."""

    pages = _page_record_axis(page_records)
    owner_markers = []
    reset_markers = []
    table_axis = []
    boundary_aliases = sorted(
        {
            *compiled_specs["query_policy"]["hard_negative_aliases"],
            *compiled_specs["query_policy"]["reset_aliases"],
        }
    )
    owner_surface_kinds = compiled_specs["query_policy"].get(
        "owner_surface_kinds",
        ["SECTION_TITLE", "SECTION_NARRATIVE", "TABLE_TITLE"],
    )
    for record in pages:
        page_json = record["page_json"]
        primary = page_json.get("status") == "PRIMARY_FINANCIAL_STATEMENT"
        for section_ordinal, section in enumerate(page_json.get("sections") or [], start=1):
            if type(section) is not dict:
                continue
            section_position = [record["selected_page_ordinal"], section_ordinal, 0]
            section_owner_surfaces = []
            if "SECTION_TITLE" in owner_surface_kinds:
                section_owner_surfaces.append(section.get("title_exact"))
            narratives = section.get("narratives_exact")
            if "SECTION_NARRATIVE" in owner_surface_kinds and type(narratives) is list:
                section_owner_surfaces.extend(narratives)
            for value in section_owner_surfaces:
                for alias in (
                    []
                    if primary
                    else _heading_surface_matches(
                        value,
                        compiled_specs["query_policy"]["owner_aliases"],
                        compiled_specs=compiled_specs,
                    )
                ):
                    owner_markers.append(
                        {
                            "alias": alias,
                            "position": section_position,
                            "source_exact": value,
                        }
                    )
            section_boundary_surfaces = [section.get("title_exact")]
            if type(narratives) is list:
                section_boundary_surfaces.extend(narratives)
            for value in section_boundary_surfaces:
                for alias in _heading_surface_matches(
                    value, boundary_aliases, compiled_specs=compiled_specs
                ):
                    reset_markers.append(
                        {
                            "alias": alias,
                            "position": section_position,
                            "source_exact": value,
                        }
                    )
            tables = section.get("tables")
            if type(tables) is not list:
                continue
            for table_ordinal, table in enumerate(tables, start=1):
                if type(table) is not dict:
                    continue
                position = [record["selected_page_ordinal"], section_ordinal, table_ordinal]
                classification = classify_gemini_json_multitable_hierarchical_table_v1(
                    page_json, section, table, compiled_specs=compiled_specs
                )
                for value in [table.get("title_exact")]:
                    if (
                        not primary
                        and "TABLE_TITLE" in owner_surface_kinds
                        and (
                            alias := _marker_matches(
                                value, compiled_specs["query_policy"]["owner_aliases"]
                            )
                        )
                        is not None
                    ):
                        owner_markers.append(
                            {"alias": alias, "position": position, "source_exact": value}
                        )
                    if (alias := _marker_matches(value, boundary_aliases)) is not None:
                        reset_markers.append(
                            {"alias": alias, "position": position, "source_exact": value}
                        )
                if classification["money_column_ordinals"]:
                    table_axis.append(
                        {
                            "classification": classification,
                            "position": position,
                            "record": record,
                            "section_id": f"s{section_ordinal}",
                            "table_id": f"t{table_ordinal}",
                        }
                    )

    intervals = []
    for owner in sorted(owner_markers, key=lambda item: item["position"]):
        preceding_resets = [
            marker for marker in reset_markers if marker["position"] <= owner["position"]
        ]
        prior_reset = max(preceding_resets, key=lambda item: item["position"], default=None)
        if any(
            interval["owner"]["position"] >= (prior_reset or {"position": [-1]})["position"]
            for interval in intervals
        ):
            # Running/repeated family headings inside the same reset-free note
            # are continuation evidence, not a second population.
            continue
        following_resets = [
            marker for marker in reset_markers if marker["position"] > owner["position"]
        ]
        reset = min(following_resets, key=lambda item: item["position"], default=None)
        items = [
            item
            for item in table_axis
            if owner["position"] <= item["position"]
            and (reset is None or item["position"] < reset["position"])
        ]
        leading_items = []
        same_page_preceding = [
            item
            for item in table_axis
            if item["position"][0] == owner["position"][0]
            and (prior_reset is None or prior_reset["position"] < item["position"])
            and item["position"] < owner["position"]
        ]
        for item in reversed(same_page_preceding):
            classification = item["classification"]
            roles = _classification_roles(classification)
            if (
                classification["typed_control_disposition"] is not None
                or not classification["family_presence_anchor_visible"]
                or not roles.intersection(compiled_specs["root_component_roles"])
            ):
                break
            leading_items.append(item)
        leading_items.reverse()
        items = [*leading_items, *items]
        skipped_same_section_items = []
        if any(marker["position"] == owner["position"] for marker in reset_markers):
            same_section_items = [
                item for item in items if item["position"][:2] == owner["position"][:2]
            ]
            first_anchor = next(
                (
                    item
                    for item in same_section_items
                    if item["classification"]["family_presence_anchor_visible"]
                ),
                None,
            )
            if first_anchor is not None:
                skipped_same_section_items = [
                    item
                    for item in same_section_items
                    if item["position"] < first_anchor["position"]
                ]
                skipped_keys = {
                    (
                        item["record"]["page_json_version_id"],
                        item["section_id"],
                        item["table_id"],
                    )
                    for item in skipped_same_section_items
                }
                items = [
                    item
                    for item in items
                    if (
                        item["record"]["page_json_version_id"],
                        item["section_id"],
                        item["table_id"],
                    )
                    not in skipped_keys
                ]
        if items:
            intervals.append(
                {
                    "items": items,
                    "leading_items": leading_items,
                    "owner": owner,
                    "reset": reset,
                    "skipped_same_section_items": skipped_same_section_items,
                }
            )

    complete = []
    for interval in intervals:
        family_items = [
            item
            for item in interval["items"]
            if item["classification"]["typed_control_disposition"] is None
        ]
        roles = {
            role for item in family_items for role in _classification_roles(item["classification"])
        }
        span = (
            family_items[-1]["position"][0] - family_items[0]["position"][0] if family_items else 0
        )
        family_root_row_visible = any(
            item["classification"].get("family_root_row_ordinals") for item in family_items
        )
        if (
            family_items
            and (roles or family_root_row_visible)
            and span <= compiled_specs["topology"]["limits"]["max_continuation_pages"]
        ):
            complete.append({**interval, "family_items": family_items, "roles": sorted(roles)})

    reasons = []
    if len(complete) > 1:
        reasons.append("MULTIPLE_COMPLETE_OWNER_CLUSTERS")
    selected = complete[0] if len(complete) == 1 else None
    if selected is not None:
        for item in selected["family_items"]:
            conflict = item["classification"].get("typed_control_conflict_disposition")
            if conflict is not None:
                reasons.append(
                    "TYPED_CONTROL_AND_DECLARED_FAMILY_ROLE_CONFLICT:"
                    + conflict
                    + ":"
                    + ":".join(
                        (
                            item["record"]["page_json_version_id"],
                            item["section_id"],
                            item["table_id"],
                        )
                    )
                )
    if intervals and selected is None and not reasons:
        reasons.append("COMPLETE_OWNER_CLUSTER_NOT_RESOLVED")
    selected_keys = (
        {
            (item["record"]["page_json_version_id"], item["section_id"], item["table_id"])
            for item in selected["family_items"]
        }
        if selected is not None
        else set()
    )
    pre_owner_same_section_keys = {
        (item["record"]["page_json_version_id"], item["section_id"], item["table_id"])
        for interval in intervals
        for item in interval["skipped_same_section_items"]
    }
    inventory = []
    for item in table_axis:
        key = (item["record"]["page_json_version_id"], item["section_id"], item["table_id"])
        classification = item["classification"]
        if key in selected_keys:
            disposition = "SELECTED_FAMILY_COMPONENT"
        elif key in pre_owner_same_section_keys:
            disposition = "EXCLUDED_PRE_OWNER_SAME_SECTION_TABLE"
        elif classification["typed_control_disposition"] is not None:
            disposition = "EXCLUDED_TYPED_CONTROL"
        elif any(
            interval["owner"]["position"] <= item["position"]
            and (interval["reset"] is None or item["position"] < interval["reset"]["position"])
            for interval in intervals
        ):
            disposition = "UNCONSUMED_MONEY_TABLE_INSIDE_OWNER_FENCE"
            # An owner-fenced MONEY table with no typed exclusion must never
            # disappear merely because none of its rows maps to the schema.
            reasons.append("UNCONSUMED_MONEY_TABLE_INSIDE_OWNER_FENCE:" + ":".join(map(str, key)))
        else:
            disposition = "OUTSIDE_SELECTED_OWNER_FENCE"
        inventory.append(
            {
                "classification": canonical_clone_v1(classification),
                "disposition": disposition,
                "page_json_version_id": item["record"]["page_json_version_id"],
                "physical_page": item["record"]["physical_page"],
                "position": item["position"],
                "section_id": item["section_id"],
                "table_id": item["table_id"],
            }
        )
    regions = (
        [_region(item, ordinal) for ordinal, item in enumerate(selected["family_items"], start=1)]
        if selected is not None and not reasons
        else []
    )
    status = READY if regions and not reasons else UNRESOLVED if intervals else NOT_OBSERVED
    material = {
        "component_regions": regions if status == READY else [],
        "declared_money_table_inventory": inventory,
        "document_id": pages[0]["document_id"],
        "document_ordinal": pages[0]["document_ordinal"],
        "owner_receipt": (
            None
            if selected is None
            else {
                **selected["owner"],
                "leading_component_positions": [
                    item["position"] for item in selected["leading_items"]
                ],
                "leading_component_rule": (
                    "CONTIGUOUS_SAME_PAGE_DECLARED_ROOT_COMPONENT_SUFFIX_BEFORE_OWNER"
                ),
            }
        ),
        "reasons": sorted(set(reasons)),
        "source_logical_name": pages[0]["source_logical_name"],
        "source_sha256": pages[0]["source_sha256"],
        "status": status,
    }
    return {
        **material,
        "cluster_id": "gjmthfcv1:cluster:" + canonical_json_sha256_v1(material),
    }


def build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
    regions: Any,
) -> dict[str, Any]:
    axis = _region_axis(regions)
    material = {
        "format_version": "GEMINI_JSON_MULTITABLE_HIERARCHICAL_REGION_QUERY_RECEIPT_V1",
        "region_axis": axis,
        "region_axis_sha256": canonical_json_sha256_v1(axis),
    }
    return {
        **material,
        "query_receipt_id": "gjmthfrrv1:receipt:" + canonical_json_sha256_v1(material),
    }


def _region_axis(regions: Any) -> list[dict[str, Any]]:
    fields = {
        "component_roles",
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
    if type(regions) not in {list, tuple} or not 1 <= len(regions) <= 64:
        raise _error("multi-table hierarchical region cardinality is invalid")
    checked = []
    identity = None
    prior = None
    for ordinal, raw in enumerate(regions, start=1):
        if (
            type(raw) is not dict
            or set(raw) != fields
            or type(raw.get("component_roles")) is not list
            or raw["component_roles"] != sorted(set(raw["component_roles"]))
            or _DOCUMENT_ID.fullmatch(raw.get("document_id", "")) is None
            or type(raw.get("document_ordinal")) is not int
            or raw["document_ordinal"] <= 0
            or raw.get("fragment_ordinal") != ordinal
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
            raise _error("multi-table hierarchical region is invalid")
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
            raise _error("multi-table hierarchical regions cross document identity")
        if prior is not None and position <= prior:
            raise _error("multi-table hierarchical regions are not source ordered")
        prior = position
        checked.append(canonical_clone_v1(raw))
    return checked


def _coefficients(record: Mapping[str, Any]) -> list[int]:
    return [cell["coefficient"] for cell in record["cells"]]


def _sum_records(records: Sequence[Mapping[str, Any]]) -> list[int]:
    if not records:
        return []
    return [
        sum(record["cells"][lane]["coefficient"] for record in records)
        for lane in range(len(records[0]["cells"]))
    ]


def _same_lane_axis(records: Sequence[Mapping[str, Any]]) -> bool:
    return bool(records) and all(records[0]["lane_keys"] == item["lane_keys"] for item in records)


def _multitable_lane_axis(section: Mapping[str, Any], table: Mapping[str, Any]) -> dict[str, Any]:
    columns = table.get("columns")
    if type(columns) is not list:
        return _table_lane_axis(section, table)
    money_ordinals = [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    period_evidence = {}
    period_reasons = []
    for ordinal in money_ordinals:
        header = _header_text(columns[ordinal - 1])
        dates = sorted({item.isoformat() for item in _surface_dates(header)}, reverse=True)
        semantic_roles = _semantic_period_roles(header)
        period_evidence[ordinal] = (dates, semantic_roles)
        if len(dates) > 1:
            period_reasons.append(f"MULTIPLE_PERIOD_DATES_IN_MONEY_COLUMN:c{ordinal}")
        if len(semantic_roles) > 1:
            period_reasons.append(f"MULTIPLE_SEMANTIC_PERIOD_ROLES_IN_MONEY_COLUMN:c{ordinal}")
    dated = sorted(
        {dates[0] for dates, _roles in period_evidence.values() if len(dates) == 1},
        reverse=True,
    )
    if len(dated) == 2:
        expected_role = {dated[0]: "CURRENT_PERIOD", dated[1]: "COMPARATIVE_PERIOD"}
        for ordinal, (dates, semantic_roles) in period_evidence.items():
            if (
                len(dates) == 1
                and len(semantic_roles) == 1
                and semantic_roles[0] != expected_role[dates[0]]
            ):
                period_reasons.append(f"DATE_SEMANTIC_PERIOD_CONFLICT:c{ordinal}")
    if period_reasons:
        return {
            "complete": False,
            "lane_keys": [],
            "layout_kind": None,
            "money_column_ordinals": money_ordinals,
            "reasons": sorted(set(period_reasons)),
            "source_period_axis": {
                "complete": False,
                "money_column_ordinals": money_ordinals,
                "reasons": sorted(set(period_reasons)),
            },
        }
    if len(money_ordinals) == 1:
        ordinal = money_ordinals[0]
        dates, semantic_roles = period_evidence[ordinal]
        bare_years = {
            value
            for value in re.findall(
                r"(?<!\d)(?:19|20)\d{2}(?!\d)", _header_text(columns[ordinal - 1])
            )
        }
        if not dates and not semantic_roles and len(bare_years) == 1:
            bare_year = next(iter(bare_years))
            return {
                "complete": True,
                "lane_keys": [["BARE_YEAR", bare_year]],
                "layout_kind": "ONE_BARE_YEAR_MONEY_COLUMN",
                "money_column_ordinals": [ordinal],
                "reasons": [],
                "selected_metric_kinds": ["GENERIC_AMOUNT"],
                "source_lane_keys": [["BARE_YEAR", bare_year]],
                "source_period_axis": {
                    "bare_year_by_money_column": {f"c{ordinal}": int(bare_year)},
                    "rule": "ONE_VISIBLE_BARE_YEAR_NO_FABRICATED_MONTH_OR_DAY",
                },
            }
        if not dates and not semantic_roles and len(bare_years) > 1:
            return {
                "complete": False,
                "lane_keys": [],
                "layout_kind": None,
                "money_column_ordinals": money_ordinals,
                "reasons": ["MULTIPLE_BARE_YEARS_IN_ONE_MONEY_COLUMN"],
                "source_period_axis": {
                    "bare_year_by_money_column": {
                        f"c{ordinal}": sorted(int(value) for value in bare_years)
                    },
                    "rule": "ONE_VISIBLE_BARE_YEAR_REQUIRED",
                },
            }
    base = _table_lane_axis(section, table)
    if base["complete"]:
        source_lane_keys = canonical_clone_v1(base["lane_keys"])
        if len(base["lane_keys"]) == 2:
            base["lane_keys"] = [
                ["SEMANTIC_ALIAS", "CURRENT_PERIOD"],
                ["SEMANTIC_ALIAS", "COMPARATIVE_PERIOD"],
            ]
        base["source_lane_keys"] = source_lane_keys
        return base
    if len(money_ordinals) != 2:
        return base
    years_by_ordinal = {}
    for ordinal in money_ordinals:
        years = {
            int(value)
            for value in re.findall(
                r"(?<!\d)(?:19|20)\d{2}(?!\d)", _header_text(columns[ordinal - 1])
            )
        }
        if len(years) != 1:
            return base
        years_by_ordinal[ordinal] = next(iter(years))
    if len(set(years_by_ordinal.values())) != 2:
        return base
    ordered = sorted(years_by_ordinal, key=lambda ordinal: years_by_ordinal[ordinal], reverse=True)
    return {
        "complete": True,
        "lane_keys": [
            ["SEMANTIC_ALIAS", "CURRENT_PERIOD"],
            ["SEMANTIC_ALIAS", "COMPARATIVE_PERIOD"],
        ],
        "layout_kind": "TWO_BARE_YEAR_MONEY_COLUMNS_CURRENT_COMPARATIVE_SEMANTICS",
        "money_column_ordinals": ordered,
        "reasons": [],
        "selected_metric_kinds": ["GENERIC_AMOUNT", "GENERIC_AMOUNT"],
        "source_lane_keys": [["BARE_YEAR", str(years_by_ordinal[ordinal])] for ordinal in ordered],
        "source_period_axis": {
            "bare_year_by_money_column": {
                f"c{ordinal}": years_by_ordinal[ordinal] for ordinal in money_ordinals
            },
            "rule": "TWO_DISTINCT_BARE_YEARS_ORDER_ONLY_NO_FABRICATED_MONTH_OR_DAY",
        },
    }


def _path_contains_label(row: Mapping[str, Any], label: str) -> bool:
    return bool(
        label
        and any(
            _normalized(value) == label
            for value in row.get("hierarchy_path_exact") or []
            if type(value) is str
        )
        and _normalized(row.get("label_exact")) != label
    )


def _row_is_strict_descendant(
    rows: Sequence[Mapping[str, Any]], child_ordinal: int, parent_ordinal: int
) -> bool:
    child = rows[child_ordinal - 1]
    parent = rows[parent_ordinal - 1]
    child_path = [
        _normalized(value)
        for value in (child.get("hierarchy_path_exact") or [])
        if _normalized(value)
    ]
    parent_path = [
        _normalized(value)
        for value in (parent.get("hierarchy_path_exact") or [])
        if _normalized(value)
    ]
    if (
        parent_path
        and len(child_path) > len(parent_path)
        and child_path[: len(parent_path)] == parent_path
    ):
        return True
    parent_label = _normalized(parent.get("label_exact"))
    if sum(_normalized(row.get("label_exact")) == parent_label for row in rows) != 1:
        return False
    return _path_contains_label(child, parent_label)


def _exact_equation(
    *, kind: str, components: Sequence[Mapping[str, Any]], result: Mapping[str, Any]
) -> dict[str, Any] | None:
    if not components or not _same_lane_axis([*components, result]):
        return None
    equation = _local_equation(
        equation_kind=kind,
        components=components,
        result=result,
    )
    return equation if equation["status"] == "EXACT" else None


def _aggregate_duplicate_roles(
    records: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
    consumed_ordinals: set[int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_role: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        by_role[record["role"]].append(record)
    output = []
    receipts = []
    for role, occurrences in by_role.items():
        if len(occurrences) == 1:
            output.append(canonical_clone_v1(occurrences[0]))
            continue
        if role not in compiled_specs["aggregate_duplicate_roles"] or not _same_lane_axis(
            occurrences
        ):
            output.extend(canonical_clone_v1(occurrences))
            continue
        if compiled_specs["duplicate_role_aggregation_policy"] == (
            "ALL_SOURCE_ROWS_CONSUMED_BY_EXACT_TABLE_FRONTIER"
        ) and any(
            source_ref.get("row_ordinal") not in consumed_ordinals
            for occurrence in occurrences
            for source_ref in occurrence["source_refs"]
        ):
            output.extend(canonical_clone_v1(occurrences))
            continue
        lane_keys = canonical_clone_v1(occurrences[0]["lane_keys"])
        coefficients = _sum_records(occurrences)
        cells = [
            {
                "coefficient": coefficient,
                "source_text": None,
                "state": "EXACT_SAME_ROLE_SOURCE_ROW_SUM",
            }
            for coefficient in coefficients
        ]
        source_refs = [
            source_ref for occurrence in occurrences for source_ref in occurrence["source_refs"]
        ]
        output.append(
            _local_record(
                role,
                cells,
                lane_keys,
                source_refs,
                "SOURCE_SAME_ROLE_ROWS_AGGREGATED_AFTER_TABLE_CLOSURE",
                occurrences[0]["valuation_basis"],
            )
        )
        receipts.append(
            {
                "coefficients": coefficients,
                "role": role,
                "rule": "SAME_ROLE_ROWS_SUM_ONLY_AFTER_SHARED_TABLE_FRONTIER_EXACT",
                "source_refs": canonical_clone_v1(source_refs),
            }
        )
    return output, receipts


def _aggregate_cluster_duplicate_roles(
    records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Sum distinct additive disclosures that live in separate source tables.

    Table-local duplicate roles are already reduced by the exact source-order
    frontier.  At document scope, a family may disclose one configured role in
    two different tables (for example two differently-labelled prepaid-cost
    populations).  Sum only explicit source observations with disjoint visible
    labels and distinct table identities.  Repeated carrier/detail presentations
    retain their context-total state and are therefore corroborated, never
    double-counted by this reducer.
    """

    by_role: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        by_role[record["role"]].append(record)
    output = []
    receipts = []
    aggregatable_states = {
        "SOURCE_OBSERVED_ROLE_ROW",
        "SOURCE_SAME_ROLE_ROWS_AGGREGATED_AFTER_TABLE_CLOSURE",
    }

    def source_table_axis(record: Mapping[str, Any]) -> set[tuple[str, str, str]]:
        return {
            (
                source_ref["locator"]["page_json_version_id"],
                source_ref["locator"]["section_id"],
                source_ref["locator"]["table_id"],
            )
            for source_ref in record["source_refs"]
        }

    def source_label_axis(record: Mapping[str, Any]) -> set[str]:
        return {
            label
            for source_ref in record["source_refs"]
            if (label := _normalized(source_ref.get("label_exact")))
        }

    for role, role_occurrences in by_role.items():
        if role not in compiled_specs["aggregate_duplicate_roles"]:
            output.extend(canonical_clone_v1(role_occurrences))
            continue
        by_lane_and_basis: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
        for occurrence in role_occurrences:
            by_lane_and_basis[
                (
                    canonical_json_sha256_v1(occurrence["lane_keys"]),
                    occurrence["valuation_basis"],
                )
            ].append(occurrence)
        for occurrences in by_lane_and_basis.values():
            table_axes = [source_table_axis(item) for item in occurrences]
            label_axes = [source_label_axis(item) for item in occurrences]
            distinct_tables = all(len(axis) == 1 for axis in table_axes) and len(
                {next(iter(axis)) for axis in table_axes}
            ) == len(occurrences)
            disjoint_labels = all(
                left.isdisjoint(right)
                for ordinal, left in enumerate(label_axes)
                for right in label_axes[ordinal + 1 :]
            )
            if (
                len(occurrences) < 2
                or not distinct_tables
                or not all(label_axes)
                or not disjoint_labels
                or any(item["state"] not in aggregatable_states for item in occurrences)
            ):
                output.extend(canonical_clone_v1(occurrences))
                continue
            coefficients = _sum_records(occurrences)
            source_refs = [
                source_ref for occurrence in occurrences for source_ref in occurrence["source_refs"]
            ]
            cells = [
                {
                    "coefficient": coefficient,
                    "source_text": None,
                    "state": "EXACT_DISTINCT_TABLE_ROLE_SUM",
                }
                for coefficient in coefficients
            ]
            output.append(
                _local_record(
                    role,
                    cells,
                    occurrences[0]["lane_keys"],
                    source_refs,
                    "SOURCE_DISTINCT_LABEL_TABLES_AGGREGATED_AFTER_CLUSTER_CLOSURE",
                    occurrences[0]["valuation_basis"],
                )
            )
            receipts.append(
                {
                    "coefficients": coefficients,
                    "lane_keys": canonical_clone_v1(occurrences[0]["lane_keys"]),
                    "role": role,
                    "rule": ("CONFIGURED_ROLE_DISTINCT_VISIBLE_LABELS_DISTINCT_TABLES_DIRECT_SUM"),
                    "source_label_axis": [sorted(axis) for axis in label_axes],
                    "source_refs": canonical_clone_v1(source_refs),
                    "source_table_axis": [list(next(iter(axis))) for axis in table_axes],
                    "valuation_basis": occurrences[0]["valuation_basis"],
                }
            )
    return output, receipts


def _reconcile_nested_context_totals(
    records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Corroborate a titleless detail total against its visible carrier row.

    Some notes print a summary table and an immediately following titleless
    detail table.  Both row populations initially inherit the outer context,
    but the detail total is exactly the visible structural child in the
    summary.  Relabel only that duplicate context observation, requiring an
    exact all-lane match in a different source table and exactly one declared
    child role.  Values never select a candidate table or scope; they only veto
    or corroborate already inventoried source roles.
    """

    output = canonical_clone_v1(list(records))
    receipts = []

    def table_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
        locator = record["source_refs"][0]["locator"]
        return (
            locator["page_json_version_id"],
            locator["section_id"],
            locator["table_id"],
        )

    by_role: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in output:
        by_role[record["role"]].append(record)
    for context_role in compiled_specs["table_context_roles"]:
        context_records = [
            record for record in by_role.get(context_role, []) if "CONTEXT_ROLE" in record["state"]
        ]
        if len(context_records) < 2:
            continue
        if len({tuple(_coefficients(item)) for item in context_records}) < 2:
            continue
        declared_children = {
            role
            for role, matchers in compiled_specs["matchers_by_role"].items()
            if any(matcher["within_role"] == context_role for matcher in matchers)
        }
        carriers = [
            record
            for role in declared_children
            for record in by_role.get(role, [])
            if record["state"] == "SOURCE_OBSERVED_ROLE_ROW"
        ]
        for context in context_records:
            matches = [
                carrier
                for carrier in carriers
                if table_key(carrier) != table_key(context)
                and carrier["lane_keys"] == context["lane_keys"]
                and _coefficients(carrier) == _coefficients(context)
            ]
            matched_roles = {item["role"] for item in matches}
            if len(matched_roles) != 1:
                continue
            role = next(iter(matched_roles))
            exact_matches = [item for item in matches if item["role"] == role]
            if len(exact_matches) != 1:
                continue
            prior_role = context["role"]
            context["role"] = role
            context["state"] = "SOURCE_CONTEXT_TOTAL_CORROBORATED_BY_VISIBLE_CHILD_CARRIER"
            receipts.append(
                {
                    "carrier_source_refs": canonical_clone_v1(exact_matches[0]["source_refs"]),
                    "coefficients": _coefficients(context),
                    "context_role": prior_role,
                    "detail_source_refs": canonical_clone_v1(context["source_refs"]),
                    "resolved_role": role,
                    "rule": ("DIFFERENT_TABLE_EXACT_ALL_LANE_VISIBLE_DECLARED_CHILD_CARRIER"),
                }
            )
    return output, receipts


def _derive_declared_role_equations(
    records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Project declared additive roles from complete visible component rows.

    This is a data-only graph projection, not a value search: every component
    role is named by the compiled family spec, must occur exactly once in each
    lane/valuation population, and must already share that authenticated axis.
    A source-observed result wins on the same axis; code only creates missing
    result populations by direct addition of the visible components.
    """

    output = canonical_clone_v1(list(records))
    equations = []
    receipts = []
    by_role: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in output:
        by_role[record["role"]].append(record)

    def population_key(record: Mapping[str, Any]) -> tuple[str, str]:
        return (
            canonical_json_sha256_v1(record["lane_keys"]),
            record["valuation_basis"],
        )

    for declaration in compiled_specs["derived_role_equations"]:
        result_role = declaration["result_role"]
        component_populations = {}
        for role in declaration["component_roles"]:
            populations: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
            for record in by_role.get(role, []):
                populations[population_key(record)].append(record)
            component_populations[role] = populations
        result_populations: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for record in by_role.get(result_role, []):
            result_populations[population_key(record)].append(record)
        first_role = declaration["component_roles"][0]
        ordered_keys = [population_key(record) for record in by_role.get(first_role, [])]
        for key in dict.fromkeys(ordered_keys):
            if result_populations.get(key) or any(
                len(component_populations[role].get(key, [])) != 1
                for role in declaration["component_roles"]
            ):
                continue
            components = [
                component_populations[role][key][0] for role in declaration["component_roles"]
            ]
            coefficients = _sum_records(components)
            cells = [
                {
                    "coefficient": coefficient,
                    "source_text": None,
                    "state": "EXACT_DECLARED_SOURCE_COMPONENT_SUM",
                }
                for coefficient in coefficients
            ]
            source_refs = [
                source_ref for component in components for source_ref in component["source_refs"]
            ]
            result = _local_record(
                result_role,
                cells,
                components[0]["lane_keys"],
                source_refs,
                "DECLARED_ROLE_DERIVED_FROM_EXACT_VISIBLE_COMPONENT_SUM",
                components[0]["valuation_basis"],
            )
            equation = _exact_equation(
                kind="EXACT_DECLARED_DERIVED_ROLE_COMPONENT_SUM",
                components=components,
                result=result,
            )
            if equation is None:
                continue
            output.append(result)
            by_role[result_role].append(result)
            result_populations[key].append(result)
            equations.append(equation)
            receipts.append(
                {
                    "coefficients": coefficients,
                    "component_roles": canonical_clone_v1(declaration["component_roles"]),
                    "result_role": result_role,
                    "rule": "DECLARED_COMPONENT_ROLES_DIRECT_SUM_NO_BACKSOLVE",
                    "source_refs": canonical_clone_v1(source_refs),
                }
            )
    return output, equations, receipts


def _derive_complete_top_level_family_root(
    records: Sequence[Mapping[str, Any]],
    *,
    source_only_axis: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Derive a family root from one exhaustive structural top-level frontier.

    The source graph, never a value search, selects the frontier: each emitted
    component must be a configured root role, every other mapped role must be
    a declared descendant of one of those roots, and no unmapped top-level row
    may remain.  Values only prove or veto the already selected direct sum.
    Existing source-visible roots are retained and must equal the same sum.
    """

    output = canonical_clone_v1(list(records))
    if (
        compiled_specs["schema"]["root_mapping_policy"]
        != "SOURCE_VISIBLE_TOTAL_OR_COMPLETE_TOP_LEVEL_COMPONENT_SUM"
    ):
        return output, [], [], []

    root_roles = set(compiled_specs["root_component_roles"])

    def reaches_root(role: str) -> bool:
        pending = [role]
        seen = set()
        while pending:
            current = pending.pop()
            if current in root_roles:
                return True
            if current in seen:
                continue
            seen.add(current)
            pending.extend(
                matcher["within_role"]
                for matcher in compiled_specs["matchers_by_role"].get(current, [])
                if matcher["within_role"] is not None
            )
        return False

    if any(
        record["role"] != "FAMILY_ROOT_TOTAL" and not reaches_root(record["role"])
        for record in output
    ):
        return output, [], [], []
    if any(
        len(
            [
                value
                for value in source_only["source_ref"].get("hierarchy_path_exact", [])
                if _normalized(value)
            ]
        )
        <= 1
        for source_only in source_only_axis
    ):
        return output, [], [], []

    by_role: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in output:
        by_role[record["role"]].append(record)
    candidate_component_roles = [
        role for role in compiled_specs["root_component_roles"] if by_role.get(role)
    ]
    for declaration in compiled_specs["derived_role_equations"]:
        if declaration["result_role"] not in candidate_component_roles or not all(
            role in candidate_component_roles for role in declaration["component_roles"]
        ):
            continue
        candidate_component_roles = [
            role for role in candidate_component_roles if role not in declaration["component_roles"]
        ]
    if not candidate_component_roles or any(
        len(by_role[role]) != 1 for role in candidate_component_roles
    ):
        return output, [], [], []

    def source_ref_is_strict_descendant(
        source_ref: Mapping[str, Any], carrier_ref: Mapping[str, Any]
    ) -> bool:
        locator = source_ref["locator"]
        carrier_locator = carrier_ref["locator"]
        if any(
            locator[key] != carrier_locator[key]
            for key in ("page_json_version_id", "section_id", "table_id")
        ):
            return False
        path = [
            _normalized(value)
            for value in source_ref.get("hierarchy_path_exact", [])
            if _normalized(value)
        ]
        carrier_path = [
            _normalized(value)
            for value in carrier_ref.get("hierarchy_path_exact", [])
            if _normalized(value)
        ]
        return bool(
            carrier_path
            and len(path) > len(carrier_path)
            and path[: len(carrier_path)] == carrier_path
        )

    def record_is_nested_under(record: Mapping[str, Any], carrier: Mapping[str, Any]) -> bool:
        return bool(record["source_refs"]) and all(
            any(
                source_ref_is_strict_descendant(source_ref, carrier_ref)
                for carrier_ref in carrier["source_refs"]
            )
            for source_ref in record["source_refs"]
        )

    component_roles = [
        role
        for role in candidate_component_roles
        if not any(
            other_role != role and record_is_nested_under(by_role[role][0], by_role[other_role][0])
            for other_role in candidate_component_roles
        )
    ]
    if not component_roles:
        return output, [], [], []
    components = [by_role[role][0] for role in component_roles]
    if any(
        component["lane_keys"] != components[0]["lane_keys"]
        or component["valuation_basis"] != components[0]["valuation_basis"]
        for component in components[1:]
    ):
        return output, [], [], []

    coefficients = _sum_records(components)
    source_refs = [
        source_ref for component in components for source_ref in component["source_refs"]
    ]
    existing = by_role.get("FAMILY_ROOT_TOTAL", [])
    if len(existing) > 1:
        return output, [], [], ["FAMILY_ROOT_SOURCE_POPULATION_IS_AMBIGUOUS"]
    if existing:
        result = existing[0]
        equation = _exact_equation(
            kind="EXACT_COMPLETE_TOP_LEVEL_COMPONENT_SUM_EQUALS_SOURCE_FAMILY_ROOT",
            components=components,
            result=result,
        )
        if equation is None:
            return (
                output,
                [],
                [],
                ["SOURCE_FAMILY_ROOT_DIFFERS_FROM_COMPLETE_TOP_LEVEL_COMPONENT_SUM"],
            )
        state = "SOURCE_VISIBLE_FAMILY_ROOT_CORROBORATED_BY_COMPLETE_TOP_LEVEL_COMPONENT_SUM"
    else:
        cells = [
            {
                "coefficient": coefficient,
                "source_text": None,
                "state": "EXACT_COMPLETE_TOP_LEVEL_COMPONENT_SUM",
            }
            for coefficient in coefficients
        ]
        result = _local_record(
            "FAMILY_ROOT_TOTAL",
            cells,
            components[0]["lane_keys"],
            source_refs,
            "DECLARED_FAMILY_ROOT_DERIVED_FROM_COMPLETE_TOP_LEVEL_COMPONENT_SUM",
            components[0]["valuation_basis"],
        )
        equation = _exact_equation(
            kind="EXACT_COMPLETE_TOP_LEVEL_COMPONENT_SUM_DERIVES_FAMILY_ROOT",
            components=components,
            result=result,
        )
        if equation is None:
            raise _error("complete top-level family root arithmetic did not close")
        output.append(result)
        state = result["state"]
    receipt = {
        "coefficients": coefficients,
        "component_roles": component_roles,
        "result_state": state,
        "rule": "COMPLETE_DECLARED_TOP_LEVEL_ROLE_FRONTIER_DIRECT_SUM_NO_BACKSOLVE",
        "source_refs": canonical_clone_v1(source_refs),
    }
    return output, [equation], [receipt], []


def _transposed_source_ref(
    region: Mapping[str, Any],
    row_ordinal: int,
    row: Mapping[str, Any],
    *,
    money_column_ordinals: Sequence[int],
) -> dict[str, Any]:
    return {
        "hierarchy_path_exact": canonical_clone_v1(row.get("hierarchy_path_exact")),
        "label_exact": row.get("label_exact"),
        "locator": canonical_clone_v1(region),
        "money_column_ordinals": list(money_column_ordinals),
        "row_id": f"r{row_ordinal}",
        "row_kind": row.get("row_kind"),
        "row_ordinal": row_ordinal,
    }


def _transposed_record_from_rows(
    role: str,
    row_ordinals: Sequence[int],
    column_ordinals: Sequence[int],
    *,
    rows: Sequence[Mapping[str, Any]],
    lane_key: Sequence[str],
    region: Mapping[str, Any],
    state: str,
) -> dict[str, Any]:
    source_cells = []
    source_refs = []
    for row_ordinal in row_ordinals:
        row = rows[row_ordinal - 1]
        values = row.get("values_exact")
        if type(values) is not list or any(ordinal > len(values) for ordinal in column_ordinals):
            raise _error("transposed source coordinate is absent")
        source_cells.extend(_source_money(values[ordinal - 1]) for ordinal in column_ordinals)
        source_refs.append(
            _transposed_source_ref(
                region,
                row_ordinal,
                row,
                money_column_ordinals=column_ordinals,
            )
        )
    if len(source_cells) == 1:
        cell = source_cells[0]
    else:
        cell = {
            "coefficient": sum(item["coefficient"] for item in source_cells),
            "source_text": None,
            "state": "EXACT_TRANSPOSED_SOURCE_COORDINATE_SUM",
        }
    return _local_record(
        role,
        [cell],
        [list(lane_key)],
        source_refs,
        state,
        "CARRYING_VALUE",
    )


def _page_reporting_date_axis(page_json: Mapping[str, Any]) -> list[str]:
    dates = set()
    for section in page_json.get("sections") or []:
        if type(section) is not dict:
            continue
        title = section.get("title_exact")
        folded = _normalized(title)
        if not folded or not any(
            marker in f" {folded} " for marker in (" tai ngay ", " as at ", " as of ")
        ):
            continue
        dates.update(item.isoformat() for item in _surface_dates(title))
    return sorted(dates, reverse=True)


def _document_reporting_period_context_axis(
    page_json_by_version: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Derive a typed snapshot pair from repeated two-date MONEY tables."""

    pair_evidence: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for page_json_version_id, page_json in page_json_by_version.items():
        for section_ordinal, section in enumerate(page_json.get("sections") or [], start=1):
            if type(section) is not dict:
                continue
            for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
                if type(table) is not dict:
                    continue
                dates = set()
                invalid = False
                for column in table.get("columns") or []:
                    if type(column) is not dict or column.get("value_kind") != "MONEY":
                        continue
                    column_dates = {
                        item.isoformat() for item in _surface_dates(_header_text(column))
                    }
                    if len(column_dates) > 1:
                        invalid = True
                        break
                    dates.update(column_dates)
                if invalid or len(dates) != 2:
                    continue
                pair = tuple(sorted(dates, reverse=True))
                pair_evidence[pair].append(
                    {
                        "page_json_version_id": page_json_version_id,
                        "section_id": f"s{section_ordinal}",
                        "table_id": f"t{table_ordinal}",
                    }
                )
    if not pair_evidence:
        return {
            "comparative_period_date": None,
            "current_period_date": None,
            "evidence": [],
            "resolution": "NO_EXACT_TWO_DATE_MONEY_TABLE_CONTEXT",
        }
    latest_current = max(pair[0] for pair in pair_evidence)
    candidates = [pair for pair in pair_evidence if pair[0] == latest_current]
    maximum_support = max(len(pair_evidence[pair]) for pair in candidates)
    candidates = [pair for pair in candidates if len(pair_evidence[pair]) == maximum_support]
    if maximum_support < 2:
        return {
            "comparative_period_date": None,
            "current_period_date": None,
            "evidence": [
                {"dates": list(pair), "source_refs": canonical_clone_v1(pair_evidence[pair])}
                for pair in sorted(candidates, reverse=True)
            ],
            "resolution": "EXACT_TWO_DATE_MONEY_TABLE_CONTEXT_NOT_REPEATED",
        }
    if len(candidates) != 1:
        return {
            "comparative_period_date": None,
            "current_period_date": None,
            "evidence": [
                {"dates": list(pair), "source_refs": canonical_clone_v1(pair_evidence[pair])}
                for pair in sorted(candidates, reverse=True)
            ],
            "resolution": "EXACT_TWO_DATE_MONEY_TABLE_CONTEXT_AMBIGUOUS",
        }
    current, comparative = candidates[0]
    return {
        "comparative_period_date": comparative,
        "current_period_date": current,
        "evidence": canonical_clone_v1(pair_evidence[candidates[0]]),
        "resolution": "UNIQUE_LATEST_REPEATED_TWO_DATE_MONEY_TABLE_CONTEXT",
    }


def _transposed_period_axis(
    page_json: Mapping[str, Any],
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    classification: Mapping[str, Any],
    *,
    document_period_context: Mapping[str, Any],
) -> dict[str, Any]:
    columns = table.get("columns")
    rows = table.get("rows")
    if type(columns) is not list or type(rows) is not list:
        raise _error("transposed period source axes are invalid")
    exact_column_hits = [
        hit
        for hit in classification.get("transposed_column_role_hits", [])
        if hit.get("status", "").startswith("EXACT_")
    ]
    ambiguous_columns = [
        hit
        for hit in classification.get("transposed_column_role_hits", [])
        if not hit.get("status", "").startswith("EXACT_")
    ]
    instrument_ordinals = sorted({hit["column_ordinal"] for hit in exact_column_hits})
    total_ordinals = [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict
        and column.get("value_kind") == "MONEY"
        and ordinal not in instrument_ordinals
        and any(
            marker in f" {_normalized(_header_text(column))} "
            for marker in (" tong cong ", " total ")
        )
    ]
    all_money_ordinals = [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    unclassified_money_ordinals = sorted(
        set(all_money_ordinals) - set(instrument_ordinals) - set(total_ordinals)
    )
    reasons = []
    if ambiguous_columns:
        reasons.append("AMBIGUOUS_TRANSPOSED_INSTRUMENT_COLUMN_ROLE")
    if not {hit["role"] for hit in exact_column_hits}:
        reasons.append("TRANSPOSED_INSTRUMENT_ROLE_AXIS_INCOMPLETE")
    if len(total_ordinals) != 1:
        reasons.append("TRANSPOSED_EXACT_TOTAL_COLUMN_NOT_UNIQUE")
    if unclassified_money_ordinals:
        reasons.append(
            "TRANSPOSED_UNCLASSIFIED_MONEY_COLUMNS:"
            + ":".join(f"c{ordinal}" for ordinal in unclassified_money_ordinals)
        )

    column_date_axis = set()
    column_semantic_roles = set()
    for ordinal in [*instrument_ordinals, *total_ordinals]:
        header = _header_text(columns[ordinal - 1])
        dates = {item.isoformat() for item in _surface_dates(header)}
        semantic_roles = _semantic_period_roles(header)
        if len(dates) > 1:
            reasons.append(f"TRANSPOSED_COLUMN_PERIOD_DATE_AMBIGUOUS:c{ordinal}")
        if len(semantic_roles) > 1:
            reasons.append(f"TRANSPOSED_COLUMN_PERIOD_ROLE_AMBIGUOUS:c{ordinal}")
        column_date_axis.update(dates)
        column_semantic_roles.update(semantic_roles)
    if len(column_semantic_roles) > 1:
        reasons.append("TRANSPOSED_COLUMN_PERIOD_ROLE_AXIS_CONFLICTS")

    markers = []
    for row_ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict:
            continue
        label = row.get("label_exact")
        roles = _semantic_period_roles(label)
        dates = sorted({item.isoformat() for item in _surface_dates(label)}, reverse=True)
        if len(dates) > 1:
            reasons.append(f"TRANSPOSED_ROW_PERIOD_DATE_AMBIGUOUS:r{row_ordinal}")
        if len(roles) > 1:
            reasons.append(f"TRANSPOSED_ROW_PERIOD_ROLE_AMBIGUOUS:r{row_ordinal}")
        elif len(roles) == 1:
            values = row.get("values_exact")
            if type(values) is not list or any(
                ordinal <= len(values) and values[ordinal - 1] is not None
                for ordinal in [*instrument_ordinals, *total_ordinals]
            ):
                reasons.append(f"TRANSPOSED_ROW_PERIOD_MARKER_HAS_MONEY_VALUES:r{row_ordinal}")
            else:
                markers.append(
                    {
                        "date": dates[0] if len(dates) == 1 else None,
                        "role": roles[0],
                        "row_ordinal": row_ordinal,
                    }
                )
    blocks = []
    if markers:
        if column_date_axis or column_semantic_roles:
            reasons.append("TRANSPOSED_ROW_BLOCKS_CONFLICT_WITH_COLUMN_PERIOD_EVIDENCE")
        if [marker["role"] for marker in markers] != [
            "CURRENT_PERIOD",
            "COMPARATIVE_PERIOD",
        ]:
            reasons.append("TRANSPOSED_ROW_PERIOD_BLOCK_AXIS_NOT_CURRENT_COMPARATIVE")
        else:
            marker_dates = [marker["date"] for marker in markers]
            if any(marker_dates) and not all(marker_dates):
                reasons.append("TRANSPOSED_ROW_PERIOD_DATE_AXIS_PARTIAL")
            elif all(marker_dates) and marker_dates[0] <= marker_dates[1]:
                reasons.append("TRANSPOSED_ROW_PERIOD_DATE_AXIS_NOT_CURRENT_COMPARATIVE")
            for marker_index, marker in enumerate(markers):
                marker_ordinal = marker["row_ordinal"]
                end = (
                    markers[marker_index + 1]["row_ordinal"] - 1
                    if marker_index + 1 < len(markers)
                    else len(rows)
                )
                blocks.append(
                    {
                        "end_row_ordinal": end,
                        "lane_key": (
                            ["DATE", marker["date"]]
                            if marker["date"] is not None
                            else ["SEMANTIC_ALIAS", marker["role"]]
                        ),
                        "marker_row_ordinal": marker_ordinal,
                        "start_row_ordinal": marker_ordinal + 1,
                    }
                )
    else:
        date_axis = set(column_date_axis)
        page_reporting_dates = set(_page_reporting_date_axis(page_json))
        if not date_axis:
            date_axis.update(page_reporting_dates)
        continuation = bool(
            re.search(
                r"\b(?:tiep theo|continued)\b",
                _normalized(section.get("title_exact")),
            )
        )
        if not date_axis and document_period_context.get("resolution") == (
            "UNIQUE_LATEST_REPEATED_TWO_DATE_MONEY_TABLE_CONTEXT"
        ):
            context_key = "comparative_period_date" if continuation else "current_period_date"
            context_date = document_period_context.get(context_key)
            if type(context_date) is str:
                date_axis.add(context_date)
        if len(date_axis) != 1:
            reasons.append("TRANSPOSED_SINGLE_PERIOD_DATE_NOT_UNIQUELY_RESOLVED")
        else:
            date = next(iter(date_axis))
            contextual_roles = set()
            if date in page_reporting_dates:
                contextual_roles.add("CURRENT_PERIOD")
            if document_period_context.get("resolution") == (
                "UNIQUE_LATEST_REPEATED_TWO_DATE_MONEY_TABLE_CONTEXT"
            ):
                if date == document_period_context.get("current_period_date"):
                    contextual_roles.add("CURRENT_PERIOD")
                if date == document_period_context.get("comparative_period_date"):
                    contextual_roles.add("COMPARATIVE_PERIOD")
            if len(contextual_roles) > 1:
                reasons.append("TRANSPOSED_DATE_PERIOD_CONTEXT_CONFLICTS")
            if (
                len(column_semantic_roles) == 1
                and contextual_roles
                and next(iter(column_semantic_roles)) not in contextual_roles
            ):
                reasons.append("TRANSPOSED_DATE_SEMANTIC_PERIOD_CONFLICT")
            lane_key = (
                ["SEMANTIC_ALIAS", next(iter(column_semantic_roles))]
                if len(column_semantic_roles) == 1
                else ["DATE", date]
            )
            blocks.append(
                {
                    "end_row_ordinal": len(rows),
                    "lane_key": lane_key,
                    "marker_row_ordinal": None,
                    "start_row_ordinal": 1,
                }
            )
    for block in blocks:
        totals = [
            ordinal
            for ordinal in range(block["start_row_ordinal"], block["end_row_ordinal"] + 1)
            if type(rows[ordinal - 1]) is dict and rows[ordinal - 1].get("row_kind") == "TOTAL"
        ]
        if len(totals) != 1:
            reasons.append(
                "TRANSPOSED_PERIOD_BLOCK_TERMINAL_TOTAL_NOT_UNIQUE:" + ":".join(block["lane_key"])
            )
        else:
            block["total_row_ordinal"] = totals[0]
    material = {
        "blocks": blocks if not reasons else [],
        "complete": not reasons,
        "instrument_column_ordinals": instrument_ordinals,
        "reasons": sorted(set(reasons)),
        "rule": (
            "EXACT_INSTRUMENT_COLUMNS_TENOR_ROWS_WITH_ONE_TOTAL_COLUMN_AND_"
            "SOURCE_VISIBLE_PERIOD_BLOCKS"
        ),
        "total_column_ordinal": total_ordinals[0] if len(total_ordinals) == 1 else None,
        "unclassified_money_column_ordinals": unclassified_money_ordinals,
    }
    return material


def _transposed_carrier_record(
    role: str,
    carrier_ordinal: int,
    column_ordinals: Sequence[int],
    *,
    rows: Sequence[Mapping[str, Any]],
    lane_key: Sequence[str],
    region: Mapping[str, Any],
    end_exclusive: int,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], set[int]]:
    carrier = rows[carrier_ordinal - 1]
    values = carrier.get("values_exact")
    if type(values) is not list or any(ordinal > len(values) for ordinal in column_ordinals):
        return None, [], set()
    carrier_visible = any(values[ordinal - 1] is not None for ordinal in column_ordinals)
    descendants = [
        ordinal
        for ordinal in range(carrier_ordinal + 1, end_exclusive)
        if type(rows[ordinal - 1]) is dict
        and type(rows[ordinal - 1].get("values_exact")) is list
        and any(
            ordinal_column <= len(rows[ordinal - 1]["values_exact"])
            and rows[ordinal - 1]["values_exact"][ordinal_column - 1] is not None
            for ordinal_column in column_ordinals
        )
    ]
    direct = [
        ordinal
        for ordinal in descendants
        if not any(
            other != ordinal and _row_is_strict_descendant(rows, ordinal, other)
            for other in descendants
        )
    ]
    equations = []
    consumed = set()
    if carrier_visible:
        result = _transposed_record_from_rows(
            role,
            [carrier_ordinal],
            column_ordinals,
            rows=rows,
            lane_key=lane_key,
            region=region,
            state="SOURCE_VISIBLE_TRANSPOSED_TENOR_CARRIER",
        )
        if direct:
            components = [
                _transposed_record_from_rows(
                    f"SOURCE_DIRECT_CHILD_r{ordinal}",
                    [ordinal],
                    column_ordinals,
                    rows=rows,
                    lane_key=lane_key,
                    region=region,
                    state="SOURCE_VISIBLE_TRANSPOSED_DIRECT_CHILD",
                )
                for ordinal in direct
            ]
            equation = _exact_equation(
                kind="EXACT_TRANSPOSED_DIRECT_CHILDREN_EQUAL_VISIBLE_TENOR_CARRIER",
                components=components,
                result=result,
            )
            if equation is not None:
                equations.append(equation)
                consumed.update(direct)
        return result, equations, consumed
    if not direct:
        # A visually blank instrument/tenor intersection is an explicit
        # conditional zero candidate.  It is emitted only so the independent
        # horizontal row total and vertical instrument total can prove or
        # veto it; the global mapper promotes it only after those equations.
        return (
            _transposed_record_from_rows(
                role,
                [carrier_ordinal],
                column_ordinals,
                rows=rows,
                lane_key=lane_key,
                region=region,
                state="SOURCE_BLANK_TRANSPOSED_TENOR_CARRIER_CONDITIONAL_ZERO",
            ),
            [],
            set(),
        )
    result = _transposed_record_from_rows(
        role,
        direct,
        column_ordinals,
        rows=rows,
        lane_key=lane_key,
        region=region,
        state="EXACT_TRANSPOSED_BLANK_CARRIER_DIRECT_CHILD_FRONTIER_SUM",
    )
    return result, [], set(direct)


def _extract_transposed_table_local_records_core(
    *,
    page_json: Mapping[str, Any],
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    region: Mapping[str, Any],
    classification: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
    document_unit_context: Mapping[str, Any],
    document_period_context: Mapping[str, Any],
) -> dict[str, Any]:
    rows = table.get("rows")
    columns = table.get("columns")
    if type(rows) is not list or type(columns) is not list:
        raise _error("transposed source axes are invalid")
    period_axis = _transposed_period_axis(
        page_json,
        section,
        table,
        classification,
        document_period_context=document_period_context,
    )
    unit_table = canonical_clone_v1(table)
    selected_columns = [
        *period_axis["instrument_column_ordinals"],
        *(
            []
            if period_axis["total_column_ordinal"] is None
            else [period_axis["total_column_ordinal"]]
        ),
    ]
    unit_table["columns"] = [
        canonical_clone_v1(columns[ordinal - 1]) for ordinal in selected_columns
    ]
    unit_axis = _unit_axis(
        unit_table,
        compiled_specs=compiled_specs,
        document_unit_context=document_unit_context,
    )
    receipt = {
        "classification": canonical_clone_v1(classification),
        "document_period_context": canonical_clone_v1(document_period_context),
        "lane_axis": period_axis,
        "region": canonical_clone_v1(region),
        "unit_axis": unit_axis,
    }
    if not period_axis["complete"] or not unit_axis["complete"]:
        return {
            "equations": [],
            "local_records": [],
            "proven_roles": [],
            "receipt": receipt,
            "source_only_rows": [],
            "unconsumed_reason": "TRANSPOSED_PERIOD_UNIT_OR_INSTRUMENT_AXIS_NOT_USABLE",
        }
    role_columns: dict[str, list[int]] = defaultdict(list)
    for hit in classification["transposed_column_role_hits"]:
        if hit.get("status", "").startswith("EXACT_"):
            role_columns[hit["role"]].append(hit["column_ordinal"])
    transposed_hits = classification["transposed_row_role_hits"]
    local_records = []
    equations = []
    proven_roles = set()
    consumed_rows = set()
    reasons = []
    for block in period_axis["blocks"]:
        lane_key = block["lane_key"]
        total_row = block["total_row_ordinal"]
        block_hits = [
            hit
            for hit in transposed_hits
            if block["start_row_ordinal"] <= hit["row_ordinal"] < total_row
        ]
        by_parent_role: dict[str, list[dict[str, Any]]] = defaultdict(list)
        by_row: dict[int, list[dict[str, Any]]] = defaultdict(list)
        carrier_ordinals = sorted({hit["row_ordinal"] for hit in block_hits})
        for hit in block_hits:
            by_parent_role[hit["parent_role"]].append(hit)
            by_row[hit["row_ordinal"]].append(hit)
        role_record_by_parent_and_child = {}
        for parent_role in sorted(role_columns):
            hits = by_parent_role.get(parent_role, [])
            seen_roles = [hit["role"] for hit in hits]
            if len(seen_roles) != len(set(seen_roles)):
                reasons.append(
                    f"TRANSPOSED_CHILD_ROLE_NOT_UNIQUE:{parent_role}:{':'.join(lane_key)}"
                )
                continue
            for hit in hits:
                later = [ordinal for ordinal in carrier_ordinals if ordinal > hit["row_ordinal"]]
                end_exclusive = min(later, default=total_row)
                try:
                    record, child_equations, consumed = _transposed_carrier_record(
                        hit["role"],
                        hit["row_ordinal"],
                        role_columns[parent_role],
                        rows=rows,
                        lane_key=lane_key,
                        region=region,
                        end_exclusive=end_exclusive,
                    )
                except ValueError:
                    record = None
                    child_equations = []
                    consumed = set()
                if record is None:
                    reasons.append(
                        f"TRANSPOSED_TENOR_CARRIER_VALUE_NOT_RESOLVED:{hit['role']}:r{hit['row_ordinal']}"
                    )
                    continue
                local_records.append(record)
                equations.extend(child_equations)
                consumed_rows.update(consumed)
                role_record_by_parent_and_child[(parent_role, hit["role"])] = record
            try:
                parent_record = _transposed_record_from_rows(
                    parent_role,
                    [total_row],
                    role_columns[parent_role],
                    rows=rows,
                    lane_key=lane_key,
                    region=region,
                    state="SOURCE_VISIBLE_TRANSPOSED_INSTRUMENT_TOTAL",
                )
            except ValueError:
                reasons.append(f"TRANSPOSED_INSTRUMENT_TOTAL_INVALID:{parent_role}")
                continue
            components = [
                role_record_by_parent_and_child[(parent_role, hit["role"])]
                for hit in hits
                if (parent_role, hit["role"]) in role_record_by_parent_and_child
            ]
            if components:
                equation = _exact_equation(
                    kind="EXACT_TRANSPOSED_TENOR_FRONTIER_EQUALS_INSTRUMENT_TOTAL",
                    components=components,
                    result=parent_record,
                )
                if equation is None:
                    reasons.append(
                        f"TRANSPOSED_INSTRUMENT_VERTICAL_EQUATION_MISMATCH:{parent_role}"
                    )
                else:
                    equations.append(equation)
                    proven_roles.update([parent_role, *(item["role"] for item in components)])
            local_records.append(parent_record)

        total_column = period_axis["total_column_ordinal"]
        if type(total_column) is not int:
            raise _error("transposed total column is absent after complete lane validation")
        for carrier_ordinal, hits in sorted(by_row.items()):
            later = [ordinal for ordinal in carrier_ordinals if ordinal > carrier_ordinal]
            end_exclusive = min(later, default=total_row)
            try:
                row_total, child_equations, consumed = _transposed_carrier_record(
                    f"SOURCE_TRANSPOSED_ROW_TOTAL_r{carrier_ordinal}",
                    carrier_ordinal,
                    [total_column],
                    rows=rows,
                    lane_key=lane_key,
                    region=region,
                    end_exclusive=end_exclusive,
                )
            except ValueError:
                row_total = None
                child_equations = []
                consumed = set()
            components = [
                role_record_by_parent_and_child[(hit["parent_role"], hit["role"])]
                for hit in hits
                if (hit["parent_role"], hit["role"]) in role_record_by_parent_and_child
            ]
            equation = (
                None
                if row_total is None
                else _exact_equation(
                    kind="EXACT_TRANSPOSED_INSTRUMENT_COLUMNS_EQUAL_VISIBLE_ROW_TOTAL",
                    components=components,
                    result=row_total,
                )
            )
            if equation is None:
                reasons.append(f"TRANSPOSED_ROW_HORIZONTAL_EQUATION_MISMATCH:r{carrier_ordinal}")
            else:
                equations.extend([*child_equations, equation])
                consumed_rows.update(consumed)
                proven_roles.update(item["role"] for item in components)

        parent_records = [
            record
            for record in local_records
            if record["lane_keys"] == [lane_key]
            and record["role"] in role_columns
            and record["state"] == "SOURCE_VISIBLE_TRANSPOSED_INSTRUMENT_TOTAL"
        ]
        root_record = _transposed_record_from_rows(
            "FAMILY_ROOT_TOTAL",
            [total_row],
            [total_column],
            rows=rows,
            lane_key=lane_key,
            region=region,
            state="SOURCE_VISIBLE_TRANSPOSED_FAMILY_ROOT_TOTAL",
        )
        root_equation = _exact_equation(
            kind="EXACT_TRANSPOSED_INSTRUMENT_TOTALS_EQUAL_VISIBLE_FAMILY_ROOT",
            components=parent_records,
            result=root_record,
        )
        if root_equation is None:
            reasons.append("TRANSPOSED_FAMILY_ROOT_HORIZONTAL_EQUATION_MISMATCH")
        else:
            equations.append(root_equation)
            proven_roles.update(["FAMILY_ROOT_TOTAL", *(item["role"] for item in parent_records)])
        local_records.append(root_record)
        consumed_rows.add(total_row)
    source_only_rows = [
        {
            "consumed_by_exact_equation": row_ordinal in consumed_rows,
            "row_ordinal": row_ordinal,
            "source_ref": _transposed_source_ref(
                region,
                row_ordinal,
                row,
                money_column_ordinals=selected_columns,
            ),
        }
        for row_ordinal, row in enumerate(rows, start=1)
        if type(row) is dict
        and type(row.get("values_exact")) is list
        and row_ordinal not in {hit["row_ordinal"] for hit in transposed_hits}
        and row_ordinal not in {block["marker_row_ordinal"] for block in period_axis["blocks"]}
    ]
    receipt["source_only_rows"] = source_only_rows
    receipt["transposed_equation_count"] = len(equations)
    receipt["transposed_reasons"] = sorted(set(reasons))
    return {
        "equations": equations,
        "local_records": local_records,
        "proven_roles": sorted(proven_roles),
        "receipt": receipt,
        "source_only_rows": source_only_rows,
        "unconsumed_reason": None if not reasons else sorted(set(reasons))[0],
    }


def _transposed_right_shift_variants(
    table: Mapping[str, Any], *, total_column_ordinal: int
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    rows = table.get("rows")
    columns = table.get("columns")
    if type(rows) is not list or type(columns) is not list:
        return []
    row_options = []
    for row_ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict or type(row.get("values_exact")) is not list:
            continue
        values = row["values_exact"]
        if len(values) != len(columns) or values[total_column_ordinal - 1] is not None:
            continue
        candidates = {}
        for start_ordinal in range(1, total_column_ordinal):
            suffix = values[start_ordinal - 1 : total_column_ordinal - 1]
            if (
                not suffix
                or suffix[-1] is None
                or not any(
                    value is not None and _source_money(value)["coefficient"] != 0
                    for value in suffix
                )
            ):
                continue
            aligned = [
                *values[: start_ordinal - 1],
                None,
                *suffix,
                *values[total_column_ordinal:],
            ]
            if aligned == values:
                continue
            candidates[canonical_json_sha256_v1(aligned)] = (
                aligned,
                {
                    "after_values_exact": aligned,
                    "before_values_exact": canonical_clone_v1(values),
                    "row_ordinal": row_ordinal,
                    "rule": (
                        "ONE_CONTIGUOUS_SUFFIX_SHIFTED_RIGHT_INTO_BLANK_TOTAL_"
                        "COLUMN_ONLY_IF_ALL_HORIZONTAL_AND_VERTICAL_EQUATIONS_EXACT"
                    ),
                },
            )
        if candidates:
            row_options.append([(None, None), *candidates.values()])
    if not row_options:
        return []
    combination_count = 1
    for options in row_options:
        combination_count *= len(options)
        if combination_count > 256:
            return []
    variants = {}
    for selections in product(*row_options):
        repairs = [receipt for _aligned, receipt in selections if receipt is not None]
        if not repairs:
            continue
        variant = canonical_clone_v1(table)
        for aligned, receipt in selections:
            if aligned is not None and receipt is not None:
                variant["rows"][receipt["row_ordinal"] - 1]["values_exact"] = aligned
        alignment_receipt = (
            repairs[0]
            if len(repairs) == 1
            else {
                "row_repairs": repairs,
                "rule": (
                    "UNIQUE_BOUNDED_SET_OF_CONTIGUOUS_ROW_SUFFIX_SHIFTS_ONLY_IF_"
                    "ALL_HORIZONTAL_AND_VERTICAL_EQUATIONS_EXACT"
                ),
            }
        )
        variants[canonical_json_sha256_v1(variant)] = (variant, alignment_receipt)
    return list(variants.values())


def _extract_transposed_table_local_records(
    *,
    page_json: Mapping[str, Any],
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    region: Mapping[str, Any],
    classification: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
    document_unit_context: Mapping[str, Any],
    document_period_context: Mapping[str, Any],
) -> dict[str, Any]:
    raw = _extract_transposed_table_local_records_core(
        page_json=page_json,
        section=section,
        table=table,
        region=region,
        classification=classification,
        compiled_specs=compiled_specs,
        document_unit_context=document_unit_context,
        document_period_context=document_period_context,
    )
    if raw["unconsumed_reason"] is None:
        return raw
    total_column = raw["receipt"]["lane_axis"].get("total_column_ordinal")
    if type(total_column) is not int:
        return raw
    resolved = []
    for variant, alignment_receipt in _transposed_right_shift_variants(
        table, total_column_ordinal=total_column
    ):
        candidate = _extract_transposed_table_local_records_core(
            page_json=page_json,
            section=section,
            table=variant,
            region=region,
            classification=classification,
            compiled_specs=compiled_specs,
            document_unit_context=document_unit_context,
            document_period_context=document_period_context,
        )
        if candidate["unconsumed_reason"] is None:
            resolved.append((candidate, alignment_receipt))
    if len(resolved) != 1:
        return raw
    candidate, alignment_receipt = resolved[0]
    candidate["receipt"]["value_alignment_receipt"] = alignment_receipt
    return candidate


def _extract_table_local_records(
    *,
    page_json: Mapping[str, Any],
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    region: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
    document_unit_context: Mapping[str, Any],
    document_period_context: Mapping[str, Any],
) -> dict[str, Any]:
    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        page_json, section, table, compiled_specs=compiled_specs
    )
    context_total_state = {
        "EXPLICIT_TABLE_TITLE": "SOURCE_PRINTED_TOTAL_PROVEN_AS_EXPLICIT_TABLE_CONTEXT_ROLE",
        "EXPLICIT_SOLE_TABLE_SECTION_TITLE": (
            "SOURCE_PRINTED_TOTAL_PROVEN_AS_EXPLICIT_SECTION_CONTEXT_ROLE"
        ),
        "DECLARED_ROW_POPULATION_SCOPE": (
            "SOURCE_PRINTED_TOTAL_PROVEN_AS_ROW_POPULATION_CONTEXT_ROLE"
        ),
    }.get(
        classification["context_resolution_kind"],
        "SOURCE_PRINTED_TOTAL_PROVEN_AS_TABLE_CONTEXT_ROLE",
    )
    expected_roles = sorted(_classification_roles(classification))
    if expected_roles != region["component_roles"]:
        raise _error("multi-table hierarchical fragment classification drifted")
    if classification.get("layout_orientation") == "INSTRUMENT_COLUMNS_TENOR_ROWS":
        return _extract_transposed_table_local_records(
            page_json=page_json,
            section=section,
            table=table,
            region=region,
            classification=classification,
            compiled_specs=compiled_specs,
            document_unit_context=document_unit_context,
            document_period_context=document_period_context,
        )
    lane_axis = _multitable_lane_axis(section, table)
    unit_table = canonical_clone_v1(table)
    if lane_axis["complete"]:
        columns = table.get("columns")
        assert type(columns) is list
        unit_table["columns"] = [
            canonical_clone_v1(columns[ordinal - 1])
            for ordinal in lane_axis["money_column_ordinals"]
        ]
    unit_axis = _unit_axis(
        unit_table,
        compiled_specs=compiled_specs,
        document_unit_context=document_unit_context,
    )
    receipt: dict[str, Any] = {
        "classification": classification,
        "lane_axis": lane_axis,
        "region": canonical_clone_v1(region),
        "unit_axis": unit_axis,
    }
    if not lane_axis["complete"] or not unit_axis["complete"]:
        return {
            "equations": [],
            "local_records": [],
            "proven_roles": [],
            "receipt": receipt,
            "source_only_rows": [],
            "unconsumed_reason": "FRAGMENT_PERIOD_OR_UNIT_AXIS_NOT_LOCALLY_USABLE",
        }
    rows = table.get("rows")
    assert type(rows) is list
    declared_role_ordinals = {hit["row_ordinal"] for hit in classification["role_hits"]}
    row_records: dict[int, dict[str, Any]] = {}
    parse_reasons = []
    for row_ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict:
            continue
        try:
            record = _row_local_record(
                "SOURCE_ROW",
                row_ordinal,
                row,
                region=region,
                lane_axis=lane_axis,
                state="SOURCE_OBSERVED_ROW",
            )
        except ValueError:
            parse_reasons.append(f"MONEY_CELL_NOT_EXACT_INTEGER:r{row_ordinal}")
            continue
        if record is not None and (
            any(cell["source_text"] is not None for cell in record["cells"])
            or row_ordinal in declared_role_ordinals
            or row.get("row_kind") in {"SUBTOTAL", "TOTAL"}
        ):
            row_records[row_ordinal] = record
    if parse_reasons:
        receipt["parse_reasons"] = sorted(set(parse_reasons))

    hit_by_row: dict[int, str] = {}
    for hit in classification["role_hits"]:
        ordinal = hit["row_ordinal"]
        if ordinal in hit_by_row and hit_by_row[ordinal] != hit["role"]:
            raise _error("multi-table hierarchical source row role repeated")
        hit_by_row[ordinal] = hit["role"]
    label_only_group_proxies: dict[int, tuple[list[int], dict[str, Any]]] = {}
    if compiled_specs["label_only_structural_group_policy"] in {
        "DIRECT_CHILD_FRONTIER_ONLY_AFTER_SOURCE_TOTAL_CLOSURE",
        "SINGLE_DIRECT_CHILD_ONLY_AFTER_SOURCE_TOTAL_CLOSURE",
    }:
        for carrier_ordinal, role in sorted(hit_by_row.items()):
            carrier = row_records.get(carrier_ordinal)
            if (
                carrier is None
                or rows[carrier_ordinal - 1].get("row_kind") not in {"GROUP", "SUBTOTAL"}
                or any(cell["source_text"] is not None for cell in carrier["cells"])
            ):
                continue
            descendants = [
                ordinal
                for ordinal in row_records
                if ordinal != carrier_ordinal
                and _row_is_strict_descendant(rows, ordinal, carrier_ordinal)
                and not (
                    rows[ordinal - 1].get("row_kind") in {"SUBTOTAL", "TOTAL"}
                    and not _normalized(rows[ordinal - 1].get("label_exact"))
                )
            ]
            direct = [
                ordinal
                for ordinal in descendants
                if not any(
                    other_ordinal != ordinal
                    and _row_is_strict_descendant(rows, ordinal, other_ordinal)
                    for other_ordinal in descendants
                )
            ]
            single_only = (
                compiled_specs["label_only_structural_group_policy"]
                == "SINGLE_DIRECT_CHILD_ONLY_AFTER_SOURCE_TOTAL_CLOSURE"
            )
            if not direct or (single_only and len(direct) != 1):
                continue
            if role not in compiled_specs["context_total_mapping_roles"] and not (
                len(direct) == 1 and hit_by_row.get(direct[0]) == role
            ):
                continue
            direct_records = [row_records[ordinal] for ordinal in direct]
            if len(direct_records) == 1:
                proxy = direct_records[0]
            else:
                coefficients = _sum_records(direct_records)
                proxy = _local_record(
                    "SOURCE_ROW",
                    [
                        {
                            "coefficient": coefficient,
                            "source_text": None,
                            "state": "EXACT_LABEL_ONLY_GROUP_DIRECT_CHILD_FRONTIER_SUM",
                        }
                        for coefficient in coefficients
                    ],
                    direct_records[0]["lane_keys"],
                    [
                        source_ref
                        for direct_record in direct_records
                        for source_ref in direct_record["source_refs"]
                    ],
                    "SOURCE_LABEL_ONLY_GROUP_DIRECT_CHILD_FRONTIER_SUM",
                    direct_records[0]["valuation_basis"],
                )
            label_only_group_proxies[carrier_ordinal] = (direct, proxy)
    shadowed_role_ordinals: set[int] = set()
    hierarchical_duplicate_receipts = []
    ordinals_by_role: dict[str, list[int]] = defaultdict(list)
    for ordinal, role in hit_by_row.items():
        ordinals_by_role[role].append(ordinal)
    for role, role_ordinals in ordinals_by_role.items():
        if len(role_ordinals) < 2:
            continue
        normalized_paths = {
            ordinal: [
                _normalized(value)
                for value in (rows[ordinal - 1].get("hierarchy_path_exact") or [])
                if _normalized(value)
            ]
            for ordinal in role_ordinals
        }
        shallowest_depth = min(len(normalized_paths[ordinal]) for ordinal in role_ordinals)
        shallowest = [
            ordinal
            for ordinal in role_ordinals
            if len(normalized_paths[ordinal]) == shallowest_depth
        ]
        if len(shallowest) != 1:
            continue
        carrier_ordinal = shallowest[0]
        carrier_path = normalized_paths[carrier_ordinal]
        detail_ordinals = [ordinal for ordinal in role_ordinals if ordinal != carrier_ordinal]
        if not carrier_path or not all(
            normalized_paths[ordinal][: len(carrier_path)] == carrier_path
            and len(normalized_paths[ordinal]) > len(carrier_path)
            for ordinal in detail_ordinals
        ):
            continue
        shadowed_role_ordinals.update(detail_ordinals)
        hierarchical_duplicate_receipts.append(
            {
                "carrier_row_ordinal": carrier_ordinal,
                "detail_row_ordinals": detail_ordinals,
                "role": role,
                "rule": "SHALLOWEST_SAME_ROLE_HIERARCHY_CARRIER_ONLY",
            }
        )
    local_records = []
    for ordinal, role in hit_by_row.items():
        if ordinal in shadowed_role_ordinals:
            continue
        record = row_records.get(ordinal)
        if record is None:
            continue
        if rows[ordinal - 1].get("row_kind") in {"GROUP", "SUBTOTAL", "TOTAL"} and all(
            cell["source_text"] is None for cell in record["cells"]
        ):
            # A label-only structural row is a hierarchy carrier, not a
            # source-observed printed zero. Its populated children or total
            # may still map the role through the ordinary closure rules.
            continue
        local_records.append(
            _local_record(
                role,
                record["cells"],
                record["lane_keys"],
                record["source_refs"],
                "SOURCE_OBSERVED_ROLE_ROW",
                record["valuation_basis"],
            )
        )

    equations = []
    proven_roles: set[str] = set()
    consumed_ordinals: set[int] = set()
    proven_carrier_children: dict[int, set[int]] = defaultdict(set)
    label_only_structural_group_receipts = []
    projected_label_only_groups: set[int] = set()
    total_ordinals = {
        ordinal
        for ordinal, row in enumerate(rows, start=1)
        if type(row) is dict
        and row.get("row_kind") in {"SUBTOTAL", "TOTAL"}
        and ordinal in row_records
    }
    # First prove visible hierarchy carriers from their exact direct children.
    for carrier_ordinal, carrier in sorted(row_records.items()):
        label = _normalized(rows[carrier_ordinal - 1].get("label_exact"))
        if not label:
            continue
        descendants = [
            (ordinal, record)
            for ordinal, record in row_records.items()
            if ordinal != carrier_ordinal
            and _row_is_strict_descendant(rows, ordinal, carrier_ordinal)
        ]
        if not descendants:
            continue
        direct = []
        for ordinal, record in descendants:
            intervening_ordinals = {
                other_ordinal
                for other_ordinal, _other in descendants
                if other_ordinal != ordinal
                and _row_is_strict_descendant(rows, ordinal, other_ordinal)
            }
            if not intervening_ordinals:
                direct.append((ordinal, record))
        equation = _exact_equation(
            kind="EXACT_VISIBLE_HIERARCHY_DIRECT_CHILDREN_EQUAL_CARRIER",
            components=[record for _ordinal, record in direct],
            result=carrier,
        )
        if equation is not None:
            equations.append(equation)
            proven_carrier_children[carrier_ordinal].update(ordinal for ordinal, _record in direct)
            consumed_ordinals.update(ordinal for ordinal, _record in direct)
            consumed_ordinals.add(carrier_ordinal)
            proven_roles.update(
                hit_by_row[ordinal] for ordinal, _record in direct if ordinal in hit_by_row
            )
            if carrier_ordinal in hit_by_row:
                proven_roles.add(hit_by_row[carrier_ordinal])

    # Some valid Gemini pages preserve visible indentation in row labels but
    # omit it from hierarchy_path_exact.  A contiguous run of dash-prefixed
    # rows can therefore be accepted as direct children only when their exact
    # all-lane sum equals the immediately preceding visible carrier.
    for carrier_ordinal, carrier in sorted(row_records.items()):
        if carrier_ordinal in proven_carrier_children:
            continue
        direct = []
        for ordinal in range(carrier_ordinal + 1, len(rows) + 1):
            if ordinal not in row_records:
                continue
            label = str(rows[ordinal - 1].get("label_exact") or "")
            if not label.lstrip().startswith(("-", "–", "—")):
                break
            direct.append((ordinal, row_records[ordinal]))
        equation = _exact_equation(
            kind="EXACT_CONTIGUOUS_DASH_CHILDREN_EQUAL_VISIBLE_CARRIER",
            components=[record for _ordinal, record in direct],
            result=carrier,
        )
        if equation is None:
            continue
        equations.append(equation)
        proven_carrier_children[carrier_ordinal].update(ordinal for ordinal, _record in direct)
        consumed_ordinals.update(ordinal for ordinal, _record in direct)
        consumed_ordinals.add(carrier_ordinal)
        proven_roles.update(
            hit_by_row[ordinal] for ordinal, _record in direct if ordinal in hit_by_row
        )
        if carrier_ordinal in hit_by_row:
            proven_roles.add(hit_by_row[carrier_ordinal])

    # A labelled SUBTOTAL can precede its direct children even when Gemini did
    # not repeat the hierarchy path.  Accept exactly one ordered prefix whose
    # source values close the subtotal; multiple closing prefixes are
    # ambiguous and remain unresolved.
    for carrier_ordinal in sorted(total_ordinals):
        if (
            carrier_ordinal in proven_carrier_children
            or rows[carrier_ordinal - 1].get("row_kind") != "SUBTOTAL"
            or not _normalized(rows[carrier_ordinal - 1].get("label_exact"))
        ):
            continue
        prefix = []
        matches = []
        for ordinal in range(carrier_ordinal + 1, len(rows) + 1):
            if ordinal in total_ordinals:
                break
            record = row_records.get(ordinal)
            if record is None:
                continue
            prefix.append((ordinal, record))
            equation = _exact_equation(
                kind="EXACT_ORDERED_PREFIX_CHILDREN_EQUAL_VISIBLE_SUBTOTAL",
                components=[item for _item_ordinal, item in prefix],
                result=row_records[carrier_ordinal],
            )
            if equation is not None:
                matches.append((list(prefix), equation))
        if len(matches) != 1:
            continue
        direct, equation = matches[0]
        equations.append(equation)
        proven_carrier_children[carrier_ordinal].update(ordinal for ordinal, _record in direct)
        consumed_ordinals.update(ordinal for ordinal, _record in direct)
        consumed_ordinals.add(carrier_ordinal)
        proven_roles.update(
            hit_by_row[ordinal] for ordinal, _record in direct if ordinal in hit_by_row
        )
        if carrier_ordinal in hit_by_row:
            proven_roles.add(hit_by_row[carrier_ordinal])

    # Then prove each printed subtotal/total against exactly one source frontier.
    for total_ordinal in sorted(total_ordinals):
        total = row_records[total_ordinal]
        candidates: list[tuple[str, list[tuple[int, dict[str, Any]]]]] = []
        preceding = [
            (
                ordinal,
                label_only_group_proxies.get(ordinal, ([], record))[1],
            )
            for ordinal, record in row_records.items()
            if ordinal < total_ordinal and ordinal not in total_ordinals
        ]
        if preceding:
            candidates.append(("ALL_PRECEDING_NON_TOTAL_ROWS", preceding))
        prior_total = max(
            (ordinal for ordinal in total_ordinals if ordinal < total_ordinal), default=0
        )
        interval = [
            (ordinal, record)
            for ordinal, record in row_records.items()
            if prior_total < ordinal < total_ordinal and ordinal not in total_ordinals
        ]
        if interval and interval != preceding:
            candidates.append(("SINCE_PRIOR_TOTAL", interval))
        # Suppress descendants of a visible-valued ancestor from the table's
        # top-level direct frontier; their own hierarchy equation above is the
        # sole consumer of those descendants.
        labelled_hierarchy_carriers = [
            (ordinal, row_records[ordinal])
            for ordinal in total_ordinals
            if ordinal < total_ordinal and proven_carrier_children.get(ordinal)
        ]
        top_level_source = sorted(
            [*preceding, *labelled_hierarchy_carriers], key=lambda item: item[0]
        )

        def proven_descendants(carrier_ordinal: int) -> set[int]:
            descendants = set(proven_carrier_children.get(carrier_ordinal, set()))
            proxy = label_only_group_proxies.get(carrier_ordinal)
            if proxy is not None:
                descendants.update(proxy[0])
            pending = list(descendants)
            while pending:
                child = pending.pop()
                for nested in proven_carrier_children.get(child, set()):
                    if nested not in descendants:
                        descendants.add(nested)
                        pending.append(nested)
            return descendants

        top_level = []
        for ordinal, record in top_level_source:
            normalized_label = _normalized(rows[ordinal - 1].get("label_exact"))
            hierarchy_path = [
                _normalized(value)
                for value in (rows[ordinal - 1].get("hierarchy_path_exact") or [])
                if _normalized(value)
            ]
            if (
                len(hierarchy_path) > 1
                and re.match(r"^(?:trong do|of which)\b", normalized_label) is not None
            ):
                # A source-visible "Trong đó / Of which" row is a disclosed
                # subset, never an additional component of an encompassing
                # total. It remains independently mappable when declared.
                continue
            if any(
                other_ordinal != ordinal and ordinal in proven_descendants(other_ordinal)
                for other_ordinal, _other in top_level_source
            ):
                continue
            top_level.append((ordinal, record))
        if top_level and top_level != preceding:
            top_level_candidate = ("VISIBLE_TOP_LEVEL_DIRECT_FRONTIER", top_level)
            if (
                compiled_specs["direct_frontier_policy"]
                == "CANONICAL_PROVEN_TOP_LEVEL_DIRECT_FRONTIER"
            ):
                candidates = [top_level_candidate]
            else:
                candidates.append(top_level_candidate)
        if (
            compiled_specs["direct_frontier_policy"] == "CANONICAL_PROVEN_TOP_LEVEL_DIRECT_FRONTIER"
            and prior_total in set(classification.get("family_root_row_ordinals", []))
            and prior_total < total_ordinal
        ):
            candidates = [
                (
                    "EXPLICIT_FAMILY_ROOT_ROW_EQUALS_PRINTED_TOTAL",
                    [(prior_total, row_records[prior_total])],
                )
            ]
        matches = []
        for kind, component_axis in candidates:
            equation = _exact_equation(
                kind="EXACT_" + kind + "_EQUAL_PRINTED_TOTAL",
                components=[record for _ordinal, record in component_axis],
                result=total,
            )
            if equation is not None:
                matches.append((kind, component_axis, equation))
        unique = {
            tuple(ordinal for ordinal, _record in component_axis): (kind, component_axis, equation)
            for kind, component_axis, equation in matches
        }
        if len(unique) != 1:
            continue
        _kind, component_axis, equation = next(iter(unique.values()))
        equations.append(equation)
        consumed_ordinals.update(ordinal for ordinal, _record in component_axis)
        consumed_ordinals.add(total_ordinal)
        for ordinal, proxy_record in component_axis:
            proxy = label_only_group_proxies.get(ordinal)
            if proxy is None or ordinal in projected_label_only_groups:
                continue
            child_ordinals, _child_record = proxy
            role = hit_by_row[ordinal]
            local_records.append(
                _local_record(
                    role,
                    proxy_record["cells"],
                    proxy_record["lane_keys"],
                    proxy_record["source_refs"],
                    (
                        "DECLARED_LABEL_ONLY_STRUCTURAL_GROUP_PROJECTED_FROM_"
                        "SOLE_DIRECT_CHILD_AFTER_SOURCE_TOTAL_CLOSURE"
                        if len(child_ordinals) == 1
                        else "DECLARED_LABEL_ONLY_STRUCTURAL_GROUP_PROJECTED_FROM_"
                        "DIRECT_CHILD_FRONTIER_AFTER_SOURCE_TOTAL_CLOSURE"
                    ),
                    proxy_record["valuation_basis"],
                )
            )
            projection_receipt = {
                "carrier_role": role,
                "carrier_row_ordinal": ordinal,
                "child_source_refs": canonical_clone_v1(proxy_record["source_refs"]),
                "rule": (
                    "DIRECT_CHILD_FRONTIER_PROJECTS_LABEL_ONLY_STRUCTURAL_GROUP_"
                    "ONLY_AFTER_SOURCE_TOTAL_CLOSURE"
                ),
            }
            if len(child_ordinals) == 1:
                projection_receipt["child_row_ordinal"] = child_ordinals[0]
                projection_receipt["rule"] = (
                    "SINGLE_DIRECT_CHILD_PROJECTS_LABEL_ONLY_STRUCTURAL_GROUP_"
                    "ONLY_AFTER_SOURCE_TOTAL_CLOSURE"
                )
            else:
                projection_receipt["child_row_ordinals"] = child_ordinals
            label_only_structural_group_receipts.append(projection_receipt)
            projected_label_only_groups.add(ordinal)
            consumed_ordinals.update(child_ordinals)
            proven_roles.add(role)
            # The carrier proxy is constructed from the complete direct-child
            # frontier, and is projected only after that proxy participates in
            # the unique exact source-total closure above.  Consequently every
            # declared direct child is equation-consumed too.  Preserve that
            # proof at role granularity so a source BLANK in one child lane can
            # be canonicalized to zero by the existing conditional-zero gate.
            # This is graph-derived evidence, not a label/value inference.
            if compiled_specs["duplicate_role_aggregation_policy"] == (
                "ALL_SOURCE_ROWS_CONSUMED_BY_EXACT_TABLE_FRONTIER"
            ):
                proven_roles.update(
                    hit_by_row[child_ordinal]
                    for child_ordinal in child_ordinals
                    if child_ordinal in hit_by_row
                )
        proven_roles.update(
            hit_by_row[ordinal] for ordinal, _record in component_axis if ordinal in hit_by_row
        )
        if total_ordinal in hit_by_row:
            proven_roles.add(hit_by_row[total_ordinal])
        component_hit_roles = {
            hit_by_row[ordinal] for ordinal, _record in component_axis if ordinal in hit_by_row
        }
        explicit_root_row_equals_total = bool(
            len(component_axis) == 1
            and component_axis[0][0] in set(classification.get("family_root_row_ordinals", []))
        )
        if (
            compiled_specs["schema"]["root_mapping_policy"]
            == "SOURCE_VISIBLE_TOTAL_OR_COMPLETE_TOP_LEVEL_COMPONENT_SUM"
        ):
            terminal_total = not any(ordinal > total_ordinal for ordinal in row_records)
            root_total_emitted = bool(
                explicit_root_row_equals_total
                or (
                    terminal_total
                    and component_hit_roles
                    and component_hit_roles <= set(compiled_specs["root_component_roles"])
                )
                or (
                    terminal_total
                    and bool(classification.get("inverted_hierarchy_scope_rows"))
                    and classification["family_presence_anchor_visible"]
                )
            )
        else:
            root_total_emitted = bool(
                explicit_root_row_equals_total
                or (
                    component_hit_roles
                    and component_hit_roles <= set(compiled_specs["root_component_roles"])
                    and len(component_hit_roles) >= 2
                )
            )
        if root_total_emitted:
            local_records.append(
                _local_record(
                    "FAMILY_ROOT_TOTAL",
                    total["cells"],
                    total["lane_keys"],
                    total["source_refs"],
                    "SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_BY_DIRECT_FRONTIER",
                    total["valuation_basis"],
                )
            )
            proven_roles.add("FAMILY_ROOT_TOTAL")
        context_roles = classification["context_roles"]
        if (
            len(context_roles) == 1
            and not root_total_emitted
            and context_roles[0] in compiled_specs["context_total_mapping_roles"]
            and not any(record["role"] == context_roles[0] for record in local_records)
        ):
            local_records.append(
                _local_record(
                    context_roles[0],
                    total["cells"],
                    total["lane_keys"],
                    total["source_refs"],
                    context_total_state,
                    total["valuation_basis"],
                )
            )
            proven_roles.add(context_roles[0])

    derived_structural_parent_receipts = []
    if compiled_specs["money_metric_policy"] == (
        "CARRYING_VALUE_PREFERRED_WITH_EXACT_PERIOD_AND_INSTRUMENT_AXES"
    ):
        existing_roles = {record["role"] for record in local_records}
        for parent_role in compiled_specs["table_context_roles"]:
            if parent_role in existing_roles:
                continue
            child_roles = {
                role
                for role in compiled_specs["child_by_role"]
                if compiled_specs["child_by_role"][role]["role_kind"] != "STRUCTURAL_GROUP"
                and any(
                    matcher["within_role"] == parent_role
                    for matcher in compiled_specs["matchers_by_role"][role]
                )
            }
            components = [record for record in local_records if record["role"] in child_roles]
            if (
                not components
                or not _same_lane_axis(components)
                or any(
                    component["valuation_basis"] != components[0]["valuation_basis"]
                    for component in components[1:]
                )
                or any(
                    source_ref.get("row_ordinal") not in consumed_ordinals
                    for component in components
                    for source_ref in component["source_refs"]
                )
            ):
                continue
            coefficients = _sum_records(components)
            source_refs = [
                source_ref for component in components for source_ref in component["source_refs"]
            ]
            parent_record = _local_record(
                parent_role,
                [
                    {
                        "coefficient": coefficient,
                        "source_text": None,
                        "state": "EXACT_COMPLETE_VISIBLE_SCOPED_CHILD_FRONTIER_SUM",
                    }
                    for coefficient in coefficients
                ],
                components[0]["lane_keys"],
                source_refs,
                "STRUCTURAL_PARENT_DERIVED_FROM_COMPLETE_VISIBLE_SCOPED_CHILD_FRONTIER",
                components[0]["valuation_basis"],
            )
            equation = _exact_equation(
                kind="EXACT_COMPLETE_VISIBLE_SCOPED_CHILD_FRONTIER_DERIVES_PARENT",
                components=components,
                result=parent_record,
            )
            if equation is None:
                continue
            local_records.append(parent_record)
            equations.append(equation)
            existing_roles.add(parent_role)
            proven_roles.add(parent_role)
            proven_roles.update(component["role"] for component in components)
            derived_structural_parent_receipts.append(
                {
                    "coefficients": coefficients,
                    "component_roles": [component["role"] for component in components],
                    "parent_role": parent_role,
                    "rule": "COMPLETE_VISIBLE_SCOPED_CHILD_FRONTIER_DIRECT_SUM_NO_BACKSOLVE",
                    "source_refs": canonical_clone_v1(source_refs),
                }
            )

    context_roles = classification["context_roles"]
    if (
        len(context_roles) == 1
        and context_roles[0] in compiled_specs["context_total_mapping_roles"]
        and not any(record["role"] == context_roles[0] for record in local_records)
        and len(row_records) == 1
    ):
        only_ordinal, only = next(iter(row_records.items()))
        local_records.append(
            _local_record(
                context_roles[0],
                only["cells"],
                only["lane_keys"],
                only["source_refs"],
                context_total_state,
                only["valuation_basis"],
            )
        )
        equations.append(
            _local_equation(
                equation_kind="EXACT_EXHAUSTIVE_SINGLE_CHILD_EQUALS_CONTEXT_ROLE",
                components=[only],
                result=only,
            )
        )
        consumed_ordinals.add(only_ordinal)
        proven_roles.add(context_roles[0])
        if only_ordinal in hit_by_row:
            proven_roles.add(hit_by_row[only_ordinal])

    source_only_rows = [
        {
            "consumed_by_exact_equation": ordinal in consumed_ordinals,
            "row_ordinal": ordinal,
            "source_ref": canonical_clone_v1(record["source_refs"][0]),
        }
        for ordinal, record in sorted(row_records.items())
        if (ordinal not in hit_by_row or ordinal in shadowed_role_ordinals)
        and ordinal not in total_ordinals
    ]
    unproven_conditional_zero_rows = sorted(
        {
            source_ref["row_ordinal"]
            for record in local_records
            if any(cell["state"].endswith("ZERO_IF_EQUATION_EXACT") for cell in record["cells"])
            for source_ref in record["source_refs"]
            if source_ref["row_ordinal"] not in consumed_ordinals
        }
    )
    unsealed_duplicate_roles = []
    if compiled_specs["duplicate_role_aggregation_policy"] == (
        "ALL_SOURCE_ROWS_CONSUMED_BY_EXACT_TABLE_FRONTIER"
    ):
        local_records_by_role: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for local_record in local_records:
            local_records_by_role[local_record["role"]].append(local_record)
        unsealed_duplicate_roles = sorted(
            role
            for role, occurrences in local_records_by_role.items()
            if role in compiled_specs["aggregate_duplicate_roles"]
            and len(occurrences) > 1
            and _same_lane_axis(occurrences)
            and any(
                source_ref.get("row_ordinal") not in consumed_ordinals
                for occurrence in occurrences
                for source_ref in occurrence["source_refs"]
            )
        )
    local_records, aggregation_receipts = _aggregate_duplicate_roles(
        local_records,
        compiled_specs=compiled_specs,
        consumed_ordinals=consumed_ordinals,
    )
    receipt["aggregation_receipts"] = aggregation_receipts
    receipt["hierarchical_duplicate_receipts"] = hierarchical_duplicate_receipts
    if compiled_specs["label_only_structural_group_policy"] != "DISABLED":
        receipt["label_only_structural_group_receipts"] = label_only_structural_group_receipts
    if compiled_specs["money_metric_policy"] == (
        "CARRYING_VALUE_PREFERRED_WITH_EXACT_PERIOD_AND_INSTRUMENT_AXES"
    ):
        receipt["derived_structural_parent_receipts"] = derived_structural_parent_receipts
    receipt["source_only_rows"] = source_only_rows
    receipt["unproven_conditional_zero_rows"] = unproven_conditional_zero_rows
    if compiled_specs["duplicate_role_aggregation_policy"] == (
        "ALL_SOURCE_ROWS_CONSUMED_BY_EXACT_TABLE_FRONTIER"
    ):
        receipt["unsealed_duplicate_roles"] = unsealed_duplicate_roles
    if classification["ambiguous_rows"]:
        unconsumed_reason = "AMBIGUOUS_DECLARED_SOURCE_ROW_ROLE"
    elif len(classification["context_roles"]) > 1:
        unconsumed_reason = "AMBIGUOUS_DECLARED_TABLE_CONTEXT_ROLE"
    elif parse_reasons:
        unconsumed_reason = "INVALID_VISIBLE_SOURCE_MONEY_CELL"
    elif unproven_conditional_zero_rows:
        unconsumed_reason = "UNPROVEN_CONDITIONAL_BLANK_ZERO_SOURCE_ROW"
    elif unsealed_duplicate_roles:
        unconsumed_reason = "DUPLICATE_ROLE_SOURCE_ROWS_NOT_ALL_EQUATION_CONSUMED"
    else:
        unconsumed_reason = None
    return {
        "equations": equations,
        "local_records": local_records,
        "proven_roles": sorted(proven_roles),
        "receipt": receipt,
        "source_only_rows": source_only_rows,
        "unconsumed_reason": unconsumed_reason,
    }


def _multitable_global_records(
    local_records: Sequence[Mapping[str, Any]],
    *,
    proven_roles: set[str],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], list[str]]:
    records, partial, reasons = _global_records(
        local_records, proven_roles=proven_roles, allow_bare_year=True
    )
    if compiled_specs["period_lane_policy"] == "CURRENT_AND_COMPARATIVE_REQUIRED" or reasons:
        return records, partial, reasons

    partial_current_roles = {
        item["role"] for item in partial if item.get("missing_lanes") == ["COMPARATIVE_PERIOD"]
    }
    if not partial_current_roles:
        return records, partial, reasons
    lane_keys = {
        tuple(lane_key)
        for record in local_records
        if len(record["lane_keys"]) == 1
        for lane_key in record["lane_keys"]
    }
    latest_date = max((key[1] for key in lane_keys if key[0] == "DATE"), default=None)
    latest_year = max((key[1] for key in lane_keys if key[0] == "BARE_YEAR"), default=None)

    def is_current_lane(key: tuple[str, ...]) -> bool:
        return bool(
            key == ("SEMANTIC_ALIAS", "CURRENT_PERIOD")
            or (key[0] == "DATE" and key[1] == latest_date)
            or (key[0] == "BARE_YEAR" and key[1] == latest_year)
        )

    by_role: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in local_records:
        if (
            record["role"] in partial_current_roles
            and len(record["cells"]) == len(record["lane_keys"]) == 1
            and is_current_lane(tuple(record["lane_keys"][0]))
        ):
            by_role[record["role"]].append(record)
    output = dict(records)
    single_reasons = []
    recovered_roles = set()
    for role in sorted(partial_current_roles):
        observations = by_role.get(role, [])
        if not observations:
            continue
        coefficients = {item["cells"][0]["coefficient"] for item in observations}
        if len(coefficients) != 1:
            single_reasons.append(f"CONFLICTING_SOURCE_VALUES_FOR_ROLE_LANE:{role}:CURRENT_PERIOD")
            continue
        selected = observations[0]
        cell = canonical_clone_v1(selected["cells"][0])
        if cell["state"].endswith("ZERO_IF_EQUATION_EXACT"):
            if role not in proven_roles:
                single_reasons.append(f"UNPROVEN_BLANK_ZERO_IN_MAPPING_ROLE:{role}")
                continue
            cell["state"] = "INFERRED_" + cell["state"]
        output[role] = {
            "cells": [cell],
            "role": role,
            "source_refs": [
                source_ref
                for observation in observations
                if observation["cells"][0]["coefficient"] == cell["coefficient"]
                for source_ref in canonical_clone_v1(observation["source_refs"])
            ],
            "state": (
                selected["state"]
                if len({item["state"] for item in observations}) == 1
                else "CORROBORATED_MULTI_SOURCE_PRESENTATIONS"
            ),
        }
        recovered_roles.add(role)
    remaining_partial = [item for item in partial if item["role"] not in recovered_roles]
    return output, remaining_partial, sorted(set(single_reasons))


def evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate one exhaustive owner-bound multi-table family cluster."""

    region_axis = _region_axis(regions)
    expected_receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        region_axis
    )
    if type(query_receipt) is not dict or not same_typed_json_v1(query_receipt, expected_receipt):
        raise _error("multi-table hierarchical query receipt does not bind fragments")
    document_unit_context = _document_unit_context_axis(
        page_json_by_version, compiled_specs=compiled_specs
    )
    transposed_policy = (
        compiled_specs["money_metric_policy"]
        == "CARRYING_VALUE_PREFERRED_WITH_EXACT_PERIOD_AND_INSTRUMENT_AXES"
    )
    document_period_context = (
        _document_reporting_period_context_axis(page_json_by_version) if transposed_policy else {}
    )
    local_records = []
    equations = []
    proven_roles: set[str] = set()
    table_receipts = []
    source_only_axis = []
    reasons = []
    for region in region_axis:
        page_json = page_json_by_version.get(region["page_json_version_id"])
        if type(page_json) is not dict:
            raise _error("multi-table hierarchical selected page JSON is absent")
        section, table = _source_table(
            page_json, section_id=region["section_id"], table_id=region["table_id"]
        )
        extracted = _extract_table_local_records(
            page_json=page_json,
            section=section,
            table=table,
            region=region,
            compiled_specs=compiled_specs,
            document_unit_context=document_unit_context,
            document_period_context=document_period_context,
        )
        local_records.extend(extracted["local_records"])
        equations.extend(extracted["equations"])
        proven_roles.update(extracted["proven_roles"])
        table_receipts.append(extracted["receipt"])
        source_only_axis.extend(extracted["source_only_rows"])
        if extracted["unconsumed_reason"] is not None:
            reasons.append(extracted["unconsumed_reason"])
    local_records, context_total_corroboration_receipts = _reconcile_nested_context_totals(
        local_records, compiled_specs=compiled_specs
    )
    local_records, cluster_aggregation_receipts = _aggregate_cluster_duplicate_roles(
        local_records, compiled_specs=compiled_specs
    )
    local_records, derived_equations, derived_role_receipts = _derive_declared_role_equations(
        local_records, compiled_specs=compiled_specs
    )
    equations.extend(derived_equations)
    proven_roles.update(receipt["result_role"] for receipt in derived_role_receipts)
    (
        local_records,
        root_component_equations,
        root_component_sum_receipts,
        root_component_reasons,
    ) = _derive_complete_top_level_family_root(
        local_records,
        source_only_axis=source_only_axis,
        compiled_specs=compiled_specs,
    )
    equations.extend(root_component_equations)
    if root_component_sum_receipts:
        proven_roles.add("FAMILY_ROOT_TOTAL")
    reasons.extend(root_component_reasons)
    records_by_role: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in local_records:
        records_by_role[record["role"]].append(record)
    for pair in compiled_specs["corroboration_pairs"]:
        carriers = records_by_role.get(pair["carrier_role"], [])
        details = records_by_role.get(pair["detail_role"], [])
        if len(carriers) != 1 or len(details) != 1:
            continue
        equation = _exact_equation(
            kind="EXACT_DECLARED_DETAIL_ROLE_EQUALS_SOURCE_CARRIER_ROLE",
            components=details,
            result=carriers[0],
        )
        if equation is not None:
            equations.append(equation)
            proven_roles.add(pair["detail_role"])
    records, partial_roles, global_reasons = _multitable_global_records(
        local_records,
        proven_roles=proven_roles,
        compiled_specs=compiled_specs,
    )
    reasons.extend(global_reasons)
    if (
        not reasons
        and "FAMILY_ROOT_TOTAL" not in records
        and not any(role in records for role in compiled_specs["bindings"])
    ):
        reasons.append("MAPPABLE_SCHEMA_ROLE_FRONTIER_IS_EMPTY")
    mappings = []
    if not reasons:
        for role in [*compiled_specs["output_role_order"], "FAMILY_ROOT_TOTAL"]:
            record = records.get(role)
            if record is None:
                continue
            report_norm_id = (
                compiled_specs["schema"]["family_root_report_norm_id"]
                if role == "FAMILY_ROOT_TOTAL"
                else compiled_specs["bindings"][role]
            )
            material = {
                "report_norm_id": report_norm_id,
                "role": role,
                "row_id": (
                    record["source_refs"][0]["row_id"]
                    if len(record["source_refs"]) == 1
                    else "corroborated:" + role
                ),
                "source_refs": canonical_clone_v1(record["source_refs"]),
                "state": record["state"],
                "unit": compiled_specs["role_unit_overrides"].get(role, "MILLION_VND"),
                "values": canonical_clone_v1(record["cells"]),
            }
            mappings.append(
                {
                    **material,
                    "item_mapping_id": "gjmthfmv1:item:" + canonical_json_sha256_v1(material),
                }
            )
    first = region_axis[0]
    closure_receipt = {
        "cluster_aggregation_receipts": cluster_aggregation_receipts,
        "context_total_corroboration_receipts": context_total_corroboration_receipts,
        "derived_role_receipts": derived_role_receipts,
        "document_unit_context": document_unit_context,
        "equations": equations,
        "partial_role_observations": partial_roles,
        "query_receipt": canonical_clone_v1(expected_receipt),
        "rule": (
            "EXHAUSTIVE_OWNER_FENCED_SOURCE_DIRECT_FRONTIER_SUBTOTAL_TOTAL_"
            "SOURCE_ONLY_UNMAPPED_ALL_LANES"
        ),
        "source_only_unmapped_rows": source_only_axis,
        "structural_root_receipt": {
            "emitted_mapping": "FAMILY_ROOT_TOTAL" in records and not reasons,
            "mapping_policy": compiled_specs["schema"]["root_mapping_policy"],
            "report_norm_id": compiled_specs["schema"]["family_root_report_norm_id"],
            "role": compiled_specs["topology"]["parent"]["role"],
        },
        "table_receipts": table_receipts,
    }
    if transposed_policy:
        closure_receipt["document_period_context"] = document_period_context
    if (
        compiled_specs["schema"]["root_mapping_policy"]
        == "SOURCE_VISIBLE_TOTAL_OR_COMPLETE_TOP_LEVEL_COMPONENT_SUM"
    ):
        closure_receipt["root_component_sum_receipts"] = root_component_sum_receipts
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "closure_receipt": closure_receipt,
        "component_regions": region_axis,
        "document_id": first["document_id"],
        "family_id": compiled_specs["topology"]["family_id"],
        "mappings": mappings,
        "page_json_version_id": first["page_json_version_id"],
        "physical_page": first["physical_page"],
        "reasons": sorted(set(reasons)),
        "section_id": first["section_id"],
        "source_logical_name": first["source_logical_name"],
        "source_sha256": first["source_sha256"],
        "status": READY if mappings and not reasons else UNRESOLVED,
        "table_id": first["table_id"],
    }
    return {
        "candidate_id": "gjmthfcv1:candidate:" + canonical_json_sha256_v1(material),
        **material,
    }


def validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
    value: Any,
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    expected = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if type(value) is not dict or not same_typed_json_v1(value, expected):
        raise _error("multi-table hierarchical candidate replay drifted")
    return expected


def build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
    *,
    selected_document_axis: Sequence[dict[str, Any]],
    selected_page_axis: Sequence[dict[str, Any]],
    document_clusters: Sequence[dict[str, Any]],
    query_policy_sha256: str,
) -> dict[str, Any]:
    """Seal the exhaustive selected-frontier document disposition axis."""

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
    accepted = [cluster for cluster in clusters if cluster.get("status") == READY]
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
        "query_evidence_id": "gjmthfieqv1:evidence:" + canonical_json_sha256_v1(material),
    }


def validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
    value: Any, *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate the complete document/page/disposition closure."""

    fields = {
        "accepted_clusters",
        "candidate_dispositions",
        "format_version",
        "query_evidence_id",
        "query_receipt",
        "selected_document_axis",
        "selected_page_axis",
    }
    list_fields = (
        "accepted_clusters",
        "candidate_dispositions",
        "selected_document_axis",
        "selected_page_axis",
    )
    if (
        compiled_specs.get("engine_format_version") != ENGINE_FORMAT_VERSION
        or type(value) is not dict
        or set(value) != fields
        or value.get("format_version") != INDEXED_QUERY_EVIDENCE_FORMAT_VERSION
        or any(type(value.get(field)) is not list for field in list_fields)
        or type(value.get("query_receipt")) is not dict
    ):
        raise _error("indexed multi-table hierarchical query evidence is invalid")
    documents = value["selected_document_axis"]
    pages = value["selected_page_axis"]
    dispositions = value["candidate_dispositions"]
    document_fields = {
        "document_id",
        "document_ordinal",
        "source_logical_name",
        "source_sha256",
    }
    if not documents or len(documents) != len(dispositions):
        raise _error("indexed multi-table hierarchical document axis is incomplete")
    by_ordinal = {}
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
            raise _error("indexed multi-table hierarchical document axis is invalid")
        by_ordinal[ordinal] = document
    page_fields = document_fields | {
        "page_json_version_id",
        "physical_page",
        "selected_page_ordinal",
    }
    per_document: dict[int, int] = defaultdict(int)
    page_versions = []
    prior_document = 0
    for page in pages:
        document = by_ordinal.get(page.get("document_ordinal")) if type(page) is dict else None
        if (
            type(page) is not dict
            or set(page) != page_fields
            or document is None
            or any(page.get(field) != document[field] for field in document_fields)
            or _PAGE_VERSION.fullmatch(page.get("page_json_version_id", "")) is None
            or type(page.get("physical_page")) is not int
            or page["physical_page"] <= 0
            or page["document_ordinal"] < prior_document
        ):
            raise _error("indexed multi-table hierarchical page axis is invalid")
        prior_document = page["document_ordinal"]
        per_document[page["document_ordinal"]] += 1
        if page.get("selected_page_ordinal") != per_document[page["document_ordinal"]]:
            raise _error("indexed multi-table hierarchical page order is incomplete")
        page_versions.append(page["page_json_version_id"])
    if len(page_versions) != len(set(page_versions)) or set(per_document) != set(by_ordinal):
        raise _error("indexed multi-table hierarchical page frontier is incomplete")
    accepted = []
    for ordinal, (document, disposition) in enumerate(
        zip(documents, dispositions, strict=True), start=1
    ):
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
            != "gjmthfcv1:cluster:"
            + canonical_json_sha256_v1(
                {key: item for key, item in cluster.items() if key != "cluster_id"}
            )
        ):
            raise _error("indexed multi-table hierarchical cluster binding drifted")
        regions = cluster.get("component_regions")
        reasons = cluster.get("reasons")
        if (
            type(reasons) is not list
            or reasons != sorted(set(reasons))
            or (cluster["status"] == READY and (not regions or reasons))
            or (cluster["status"] == NOT_OBSERVED and regions)
            or (cluster["status"] == UNRESOLVED and (not reasons or regions))
        ):
            raise _error("indexed multi-table hierarchical disposition drifted")
        if cluster["status"] == READY:
            _region_axis(regions)
            accepted.append(cluster)
    if not same_typed_json_v1(value["accepted_clusters"], accepted):
        raise _error("indexed multi-table hierarchical accepted projection drifted")
    expected_receipt = {
        "accepted_cluster_axis_sha256": canonical_json_sha256_v1(accepted),
        "accepted_cluster_count": len(accepted),
        "accepted_fragment_count": sum(len(item["component_regions"]) for item in accepted),
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
    if not same_typed_json_v1(value["query_receipt"], expected_receipt):
        raise _error("indexed multi-table hierarchical query receipt drifted")
    material = {key: canonical_clone_v1(value[key]) for key in fields - {"query_evidence_id"}}
    if value["query_evidence_id"] != "gjmthfieqv1:evidence:" + canonical_json_sha256_v1(material):
        raise _error("indexed multi-table hierarchical evidence identity drifted")
    return canonical_clone_v1(value)


def validate_gemini_json_multitable_hierarchical_sweep_query_bindings_v1(
    *, trials: Any, indexed_query_evidence: Any, compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Bind every sweep trial to its exhaustive indexed disposition."""

    evidence = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
    documents = evidence["selected_document_axis"]
    if type(trials) is not list or len(trials) != len(documents):
        raise _error("multi-table hierarchical sweep trial axis is incomplete")
    accepted = {item["document_ordinal"]: item for item in evidence["accepted_clusters"]}
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
            raise _error("multi-table hierarchical sweep trial identity drifted")
        if disposition["disposition"] == READY:
            if len(trial["candidates"]) != 1:
                raise _error("accepted multi-table hierarchical trial needs one candidate")
            candidate = trial["candidates"][0]
            if not same_typed_json_v1(
                candidate.get("component_regions"),
                accepted[ordinal]["component_regions"],
            ):
                raise _error("multi-table hierarchical candidate regions drifted")
            if candidate.get("status") == READY:
                if (
                    trial.get("status") != READY
                    or trial.get("selected_candidate_id") != candidate.get("candidate_id")
                    or not same_typed_json_v1(trial.get("mappings"), candidate.get("mappings"))
                    or trial.get("reasons")
                ):
                    raise _error("multi-table hierarchical READY trial drifted")
            elif (
                trial.get("status") != UNRESOLVED
                or trial.get("selected_candidate_id") is not None
                or trial.get("mappings")
                or trial.get("reasons") != candidate.get("reasons")
            ):
                raise _error("multi-table hierarchical unresolved candidate drifted")
        elif disposition["disposition"] == NOT_OBSERVED:
            if (
                trial.get("status") != NOT_OBSERVED
                or trial["candidates"]
                or trial.get("mappings")
                or trial.get("reasons")
                or trial.get("selected_candidate_id") is not None
            ):
                raise _error("multi-table hierarchical not-observed trial drifted")
        elif (
            trial.get("status") != UNRESOLVED
            or trial["candidates"]
            or trial.get("mappings")
            or trial.get("selected_candidate_id") is not None
            or trial.get("reasons") != disposition["cluster"]["reasons"]
        ):
            raise _error("multi-table hierarchical unresolved disposition drifted")
    return canonical_clone_v1(trials)
