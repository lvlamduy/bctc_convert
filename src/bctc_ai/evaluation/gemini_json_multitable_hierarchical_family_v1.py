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
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from itertools import product
from typing import Any

from bctc_ai.evaluation.accounting_family_topology_v1 import (
    compile_accounting_family_topology_spec_v1,
)
from bctc_ai.evaluation.gemini_json_customer_deposit_family_v1 import (
    _alias_occurrences,
    _column_unit_surfaces,
    _compile_units,
    _document_unit_context_axis,
    _source_table,
)
from bctc_ai.evaluation.gemini_json_customer_deposit_family_v1 import (
    _unit_axis as _customer_deposit_unit_axis,
)
from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import (
    _header_text,
    _matches,
    _normalized,
    _path_has_role,
    _row_role_match_modes,
    _without_leading_ordinal,
)
from bctc_ai.evaluation.gemini_json_other_long_term_investments_family_v1 import (
    _global_records,
    _heading_marker_matches,
    _local_record,
    _marker_matches,
    _page_record_axis,
    _row_local_record,
    _semantic_period_roles,
    _source_money,
    _surface_dates,
    _table_lane_axis,
)
from bctc_ai.evaluation.gemini_json_other_long_term_investments_family_v1 import (
    _local_equation as _other_long_term_local_equation,
)
from bctc_ai.evaluation.source_observation_lane_math_v1 import (
    observed_source_coefficient_v1,
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


def _unit_axis(
    table: Mapping[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
    document_unit_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve units after discarding only surface-dominated short aliases.

    Gemini can retain both a clean unit header (``Triệu VND``) and a noisy
    full header surface such as ``31/12/2025 nTriệu VND``.  The shared unit
    resolver correctly prefers the longest alias *within* one surface, but the
    noisy surface can expose only the shorter ``VND`` suffix and falsely turn
    the two representations of one column into a unit conflict.  Narrow the
    alias map only when every occurrence of the short alias is textually
    covered by a longer declared alias on that same source surface.  A
    standalone short-unit surface therefore remains authoritative and a real
    mixed-unit table still fails closed.
    """

    # Some Gemini pages preserve a rendered line break as the two literal
    # characters ``\\n`` inside one header-path item.  Treat that serialization
    # artifact as a surface separator for unit resolution only.  The source
    # table and its provenance remain byte-for-byte unchanged.
    normalized_table = canonical_clone_v1(table)
    normalized_columns = normalized_table.get("columns")
    for column in normalized_columns if type(normalized_columns) is list else []:
        if type(column) is not dict:
            continue
        path = column.get("header_path_exact")
        if type(path) is not list:
            continue
        column["header_path_exact"] = [
            (
                item.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\r", "\n")
                if type(item) is str
                else item
            )
            for item in path
        ]

    aliases = list(compiled_specs["unit_binding_by_alias"])
    surfaces = []
    unit_exact = normalized_table.get("unit_exact")
    if type(unit_exact) is str and (folded := _normalized(unit_exact)):
        surfaces.append(folded)
    columns = normalized_table.get("columns")
    for column in columns if type(columns) is list else []:
        if type(column) is dict and column.get("value_kind") == "MONEY":
            surfaces.extend(
                _column_unit_surfaces(column, compiled_specs=compiled_specs)
            )
    dominated = set()
    for alias in aliases:
        matched_surfaces = [
            surface
            for surface in surfaces
            if alias in _alias_occurrences(surface, aliases)
        ]
        if matched_surfaces and all(
            any(
                len(other) > len(alias)
                and alias in other
                and other in surface
                for other in aliases
            )
            for surface in matched_surfaces
        ):
            dominated.add(alias)
    if not dominated:
        return _customer_deposit_unit_axis(
            normalized_table,
            compiled_specs=compiled_specs,
            document_unit_context=document_unit_context,
        )
    narrowed = dict(compiled_specs)
    narrowed["unit_binding_by_alias"] = {
        alias: binding
        for alias, binding in compiled_specs["unit_binding_by_alias"].items()
        if alias not in dominated
    }
    narrowed_table = normalized_table
    narrowed_columns = narrowed_table.get("columns")
    for column in narrowed_columns if type(narrowed_columns) is list else []:
        if type(column) is not dict or column.get("value_kind") != "MONEY":
            continue
        path = column.get("header_path_exact")
        if type(path) is not list:
            continue
        filtered_path = []
        for item in path:
            if type(item) is not str:
                filtered_path.append(item)
                continue
            retained_lines = []
            for line in item.splitlines() or [item]:
                folded = _normalized(line)
                occurrences = set(_alias_occurrences(folded, aliases))
                if occurrences and occurrences <= dominated:
                    continue
                retained_lines.append(line)
            if retained_lines:
                filtered_path.append("\n".join(retained_lines))
        column["header_path_exact"] = filtered_path
    return _customer_deposit_unit_axis(
        narrowed_table,
        compiled_specs=narrowed,
        document_unit_context=document_unit_context,
    )


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
        "declared_result_role_policy",
        "document_source_result_signal_policy",
        "document_cluster_policy",
        "context_residual_bindings",
        "duplicate_role_aggregation_policy",
        "duplicate_complete_table_population_policy",
        "equation_consumed_unmatched_residual_anchor_policy",
        "equation_consumed_unmatched_residual_role",
        "family_root_population_policy",
        "family_root_requirement",
        "family_root_terminal_scope_policy",
        "hierarchy_role_scope_policy",
        "label_only_structural_group_policy",
        "money_metric_policy",
        "non_money_metric_roles",
        "ordered_role_scopes",
        "ordered_role_scope_projections",
        "mapped_source_subtotal_policy",
        "minimum_declared_detail_role_count",
        "minimum_source_visible_root_component_count",
        "multi_metric_lane_equation",
        "owner_complete_population_policy",
        "owner_match_policy",
        "owner_surface_kinds",
        "period_lane_policy",
        "primary_statement_family_root_subtree_policy",
        "query_owner_aliases",
        "required_role_combination_mapping_policy",
        "role_anchored_owner_fallback_policy",
        "role_anchored_supplemental_roles",
        "root_component_role_combinations",
        "root_component_equation_policy",
        "root_only_source_result_policy",
        "row_population_context_policy",
        "row_population_context_roles_requiring_explicit_heading",
        "row_alias_prefix_roles",
        "source_only_detail_context_roles",
        "structural_marker_policy",
        "supplemental_owner_aliases",
        "supplemental_detail_residuals",
        "source_result_query_policy",
        "source_reference_identity_policy",
        "source_presentation_rounding_policy",
        "source_total_blank_lane_control_policy",
        "signed_context_frontier_equations",
        "source_hierarchy_overlap_total_policy",
        "structural_parent_derivation_policy",
        "unmapped_direct_family_row_policy",
        "validation_role_leaf_projections",
        "validation_only_roles",
        "accepted_value_column_kinds",
        "duration_month_resolution_policy",
        "ratio_metric_equations",
        "continuation_period_axis_policy",
        "continuation_leading_child_scope_policy",
        "adjacent_continuation_family_root_policy",
        "cross_fragment_same_role_parent_equation_policy",
        "duration_header_path_scope_policy",
        "numbered_subsection_unit_axis_policy",
        "owner_outline_continuation_policy",
        "owner_summary_structural_role_policy",
        "sole_table_detail_narrative_context_policy",
        "ordered_titleless_money_table_narrative_context_policy",
        "primary_statement_source_result_fallback_policy",
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
        or evaluation_spec.get("period_semantics")
        not in {
            "CURRENT_AND_COMPARATIVE_SNAPSHOT",
            "CURRENT_AND_COMPARATIVE_DURATION",
        }
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
    owner_match_policy = evaluation_spec.get("owner_match_policy", "CONTAINS_ALIAS")
    if owner_match_policy not in {
        "CONTAINS_ALIAS",
        "EXACT_NORMALIZED_WITH_BOUNDED_SOURCE_SUFFIX",
    }:
        raise _error("multi-table hierarchical owner match policy is invalid")
    owner_complete_population_policy = evaluation_spec.get(
        "owner_complete_population_policy", "DECLARED_COMPONENTS_ONLY"
    )
    if owner_complete_population_policy not in {
        "DECLARED_COMPONENTS_ONLY",
        "EXACT_OWNER_WHOLE_MONEY_TABLE",
    }:
        raise _error("multi-table hierarchical owner-complete population policy is invalid")
    source_hierarchy_overlap_total_policy = evaluation_spec.get(
        "source_hierarchy_overlap_total_policy",
        "UNRESOLVED_ON_OVERLAPPING_SOURCE_HIERARCHY_TOTAL",
    )
    if source_hierarchy_overlap_total_policy not in {
        "UNRESOLVED_ON_OVERLAPPING_SOURCE_HIERARCHY_TOTAL",
        "MAP_EXACT_PRINTED_TOTAL_WITH_OVERLAPPING_SOURCE_HIERARCHY_RECEIPT",
    }:
        raise _error("multi-table hierarchical source hierarchy overlap policy is invalid")
    direct_frontier_policy = evaluation_spec.get(
        "direct_frontier_policy", "ALL_EXACT_SOURCE_FRONTIERS_UNIQUE"
    )
    if direct_frontier_policy not in {
        "ALL_EXACT_SOURCE_FRONTIERS_UNIQUE",
        "CANONICAL_PROVEN_TOP_LEVEL_DIRECT_FRONTIER",
        "CANONICAL_PROVEN_OR_CONTIGUOUS_NUMBERED_TOP_LEVEL_DIRECT_FRONTIER",
    }:
        raise _error("multi-table hierarchical direct frontier policy is invalid")
    declared_result_role_policy = evaluation_spec.get(
        "declared_result_role_policy", "SOURCE_ROW_KIND_ONLY"
    )
    if declared_result_role_policy not in {
        "SOURCE_ROW_KIND_ONLY",
        "SOURCE_ROW_KIND_OR_DECLARED_SUBTOTAL_TOTAL_ROLE",
    }:
        raise _error("multi-table hierarchical declared result role policy is invalid")
    mapped_source_subtotal_policy = evaluation_spec.get(
        "mapped_source_subtotal_policy", "REQUIRE_EXACT_DIRECT_FRONTIER"
    )
    if mapped_source_subtotal_policy not in {
        "REQUIRE_EXACT_DIRECT_FRONTIER",
        "ALLOW_SOURCE_VISIBLE_ROOT_COMPONENT_CONSUMED_BY_EXACT_ROOT_EQUATION",
        "ALLOW_SOURCE_VISIBLE_DECLARED_ROLE_WITH_NONADDITIVE_CHILDREN_OR_ROOT_COMPONENT_EQUATION",
    }:
        raise _error("multi-table hierarchical mapped subtotal policy is invalid")
    hierarchy_role_scope_policy = evaluation_spec.get(
        "hierarchy_role_scope_policy", "UNSCOPED_CONTEXT_FALLBACK"
    )
    if hierarchy_role_scope_policy not in {
        "UNSCOPED_CONTEXT_FALLBACK",
        "PATH_DECLARED_ROLES_FIRST",
    }:
        raise _error("multi-table hierarchical hierarchy role scope policy is invalid")
    family_root_population_policy = evaluation_spec.get(
        "family_root_population_policy", "WHOLE_TABLE"
    )
    if family_root_population_policy not in {
        "WHOLE_TABLE",
        "EXPLICIT_SOURCE_ROOT_SUBTREE_ONLY",
        "EXPLICIT_PRIMARY_STATEMENT_SOURCE_ROOT_SUBTREE_OTHERWISE_WHOLE_TABLE",
    }:
        raise _error("multi-table hierarchical family root population policy is invalid")
    family_root_requirement = evaluation_spec.get("family_root_requirement", "OPTIONAL")
    if family_root_requirement not in {
        "OPTIONAL",
        "REQUIRED_SOURCE_VISIBLE_EXACT_ROOT",
    }:
        raise _error("multi-table hierarchical family root requirement is invalid")
    source_total_blank_lane_control_policy = evaluation_spec.get(
        "source_total_blank_lane_control_policy", "EXACT_ALL_SOURCE_LANES"
    )
    if source_total_blank_lane_control_policy not in {
        "EXACT_ALL_SOURCE_LANES",
        "OBSERVED_LANES_EXACT_REMAINDER_BLANK",
    }:
        raise _error("multi-table hierarchical source-total blank-lane policy is invalid")
    family_root_terminal_scope_policy = evaluation_spec.get(
        "family_root_terminal_scope_policy", "LAST_VALUE_BEARING_ROW_IN_SELECTED_REGION"
    )
    if family_root_terminal_scope_policy not in {
        "LAST_VALUE_BEARING_ROW_IN_SELECTED_REGION",
        "LAST_SOURCE_TOTAL_WITHIN_EXPLICIT_FAMILY_ROOT_SUBTREE",
    }:
        raise _error("multi-table hierarchical family-root terminal scope policy is invalid")
    source_presentation_rounding_policy = evaluation_spec.get(
        "source_presentation_rounding_policy", "EXACT_SOURCE_ARITHMETIC_ONLY"
    )
    if source_presentation_rounding_policy not in {
        "EXACT_SOURCE_ARITHMETIC_ONLY",
        "INDEPENDENT_DISPLAY_UNIT_ROUNDING_INTERVAL_ALL_EQUATIONS",
    }:
        raise _error("multi-table hierarchical source-presentation rounding policy is invalid")
    primary_statement_family_root_subtree_policy = evaluation_spec.get(
        "primary_statement_family_root_subtree_policy", "DISABLED"
    )
    if primary_statement_family_root_subtree_policy not in {
        "DISABLED",
        "EXACT_PARENT_GROUP_UNDER_VISIBLE_TOTAL_WITH_COMPLETE_DECLARED_CHILD_FRONTIER",
    }:
        raise _error("multi-table hierarchical primary-statement subtree policy is invalid")
    primary_statement_source_result_fallback_policy = evaluation_spec.get(
        "primary_statement_source_result_fallback_policy", "DISABLED"
    )
    if primary_statement_source_result_fallback_policy not in {
        "DISABLED",
        "UNIQUE_SHALLOWEST_STRUCTURAL_EXACT_VISIBLE_ROOT_WHEN_NOTE_NOT_OBSERVED",
    }:
        raise _error("multi-table hierarchical primary source-result fallback is invalid")
    label_only_structural_group_policy = evaluation_spec.get(
        "label_only_structural_group_policy", "DISABLED"
    )
    if label_only_structural_group_policy not in {
        "DISABLED",
        "DIRECT_CHILD_FRONTIER_ONLY_AFTER_SOURCE_TOTAL_CLOSURE",
        "SINGLE_DIRECT_CHILD_ONLY_AFTER_SOURCE_TOTAL_CLOSURE",
    }:
        raise _error("multi-table hierarchical label-only structural group policy is invalid")
    structural_parent_derivation_policy = evaluation_spec.get(
        "structural_parent_derivation_policy", "TRANSPOSED_METRIC_ONLY"
    )
    if structural_parent_derivation_policy not in {
        "TRANSPOSED_METRIC_ONLY",
        "DECLARED_CONTEXT_CHILD_FRONTIER",
    }:
        raise _error("multi-table hierarchical structural parent derivation policy is invalid")
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
    document_cluster_policy = evaluation_spec.get(
        "document_cluster_policy", "ONE_EXPLICIT_OWNER_RESET_FENCE"
    )
    if document_cluster_policy not in {
        "ONE_EXPLICIT_OWNER_RESET_FENCE",
        "DOCUMENT_EXACT_DECLARED_ROOT_COMPONENTS_PLUS_SOURCE_RESULT",
    }:
        raise _error("multi-table hierarchical document cluster policy is invalid")
    document_source_result_signal_policy = evaluation_spec.get(
        "document_source_result_signal_policy", "ANY_FAMILY_ROOT_ROW"
    )
    if document_source_result_signal_policy not in {
        "ANY_FAMILY_ROOT_ROW",
        "AUTHENTICATED_ROOT_OWNER_OR_PRIMARY",
    }:
        raise _error("multi-table hierarchical source-result signal policy is invalid")
    source_result_query_policy = evaluation_spec.get(
        "source_result_query_policy", "OWNER_OR_DECLARED_ROLE"
    )
    if source_result_query_policy not in {
        "OWNER_OR_DECLARED_ROLE",
        "OWNER_OR_EXACT_SOURCE_RESULT_ROW",
        "REQUIRED_EXACT_SOURCE_RESULT_ROW",
    }:
        raise _error("multi-table hierarchical source-result query policy is invalid")
    source_reference_identity_policy = evaluation_spec.get(
        "source_reference_identity_policy", "PRESERVE_SOURCE_PRESENTATIONS"
    )
    if source_reference_identity_policy not in {
        "PRESERVE_SOURCE_PRESENTATIONS",
        "EXACT_UNIQUE_SOURCE_IDENTITIES",
    }:
        raise _error("multi-table hierarchical source-reference policy is invalid")
    minimum_declared_detail_role_count = evaluation_spec.get(
        "minimum_declared_detail_role_count", 2
    )
    if (
        type(minimum_declared_detail_role_count) is not int
        or not 1 <= minimum_declared_detail_role_count <= 8
    ):
        raise _error("multi-table hierarchical minimum detail role count is invalid")
    minimum_source_visible_root_component_count = evaluation_spec.get(
        "minimum_source_visible_root_component_count", 2
    )
    if (
        type(minimum_source_visible_root_component_count) is not int
        or not 1 <= minimum_source_visible_root_component_count <= 8
    ):
        raise _error(
            "multi-table hierarchical minimum source-visible root component count is invalid"
        )
    required_role_combination_mapping_policy = evaluation_spec.get(
        "required_role_combination_mapping_policy", "QUERY_EVIDENCE_ONLY"
    )
    if required_role_combination_mapping_policy not in {
        "QUERY_EVIDENCE_ONLY",
        "REQUIRE_COMPLETE_COMBINATION_BEFORE_MAPPING",
    }:
        raise _error("multi-table hierarchical required-role mapping policy is invalid")
    root_only_source_result_policy = evaluation_spec.get(
        "root_only_source_result_policy", "ALLOW_EXACT_SOURCE_RESULT"
    )
    if root_only_source_result_policy not in {
        "ALLOW_EXACT_SOURCE_RESULT",
        "REQUIRE_MINIMUM_DECLARED_COMPONENTS",
    }:
        raise _error("multi-table hierarchical root-only source-result policy is invalid")
    row_population_context_policy = evaluation_spec.get(
        "row_population_context_policy", "ONE_ANCHORED_OR_TWO_DECLARED_CHILD_ROLES"
    )
    if row_population_context_policy not in {
        "ONE_ANCHORED_OR_TWO_DECLARED_CHILD_ROLES",
        "AT_LEAST_TWO_DECLARED_CHILD_ROLES",
    }:
        raise _error("multi-table hierarchical row population context policy is invalid")
    root_component_equation_policy = evaluation_spec.get(
        "root_component_equation_policy", "DECLARED_DIRECT_SUM"
    )
    if root_component_equation_policy not in {
        "DECLARED_DIRECT_SUM",
        "UNIQUE_DECLARED_SIGN_ORIENTATION_FIRST_COMPONENT_POSITIVE",
    }:
        raise _error("multi-table hierarchical root component equation policy is invalid")
    duplicate_role_aggregation_policy = evaluation_spec.get(
        "duplicate_role_aggregation_policy", "DECLARED_SAME_ROLE_SOURCE_ROW_SUM"
    )
    if duplicate_role_aggregation_policy not in {
        "DECLARED_SAME_ROLE_SOURCE_ROW_SUM",
        "ALL_SOURCE_ROWS_CONSUMED_BY_EXACT_TABLE_FRONTIER",
    }:
        raise _error("multi-table hierarchical duplicate role aggregation policy is invalid")
    duplicate_complete_table_population_policy = evaluation_spec.get(
        "duplicate_complete_table_population_policy", "ALLOW_CORROBORATING_PRESENTATIONS"
    )
    if duplicate_complete_table_population_policy not in {
        "ALLOW_CORROBORATING_PRESENTATIONS",
        "UNRESOLVED_EXACT_REPEATED_POPULATION",
        "UNRESOLVED_EXACT_REPEATED_ACTIVE_FAMILY_POPULATION",
        "UNRESOLVED_EXACT_REPEATED_OWNER_FENCED_WHOLE_TABLE_POPULATION",
    }:
        raise _error(
            "multi-table hierarchical duplicate complete table population policy is invalid"
        )
    unmapped_direct_family_row_policy = evaluation_spec.get(
        "unmapped_direct_family_row_policy", "IGNORE"
    )
    if unmapped_direct_family_row_policy not in {
        "IGNORE",
        "UNRESOLVED_WHEN_ACTIVE_FAMILY_POPULATION_HAS_ANY_UNMAPPED_MONEY_ROW",
        "UNRESOLVED_WHEN_ACTIVE_FAMILY_POPULATION_HAS_UNMAPPED_DIRECT_MONEY_ROW",
        "UNRESOLVED_WHEN_EXPLICIT_FAMILY_ROOT_HAS_UNMAPPED_DIRECT_MONEY_CHILD",
        "UNRESOLVED_WHEN_OWNER_FENCED_WHOLE_TABLE_HAS_UNMAPPED_DIRECT_MONEY_ROW",
    }:
        raise _error("multi-table hierarchical unmapped direct family row policy is invalid")
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

    # A parent-owned flat disclosure has no intermediate structural context
    # role.  Keep the arrays explicit in the spec, but allow them to be empty
    # so the same engine can cover both hierarchical balance disclosures and
    # duration-note tables without inventing a synthetic schema node.
    table_context_roles = role_axis("table_context_roles", allow_empty=True)
    detail_context_roles = role_axis("detail_context_roles", allow_empty=True)
    context_total_mapping_roles = role_axis("context_total_mapping_roles", allow_empty=True)
    source_only_detail_context_roles = (
        role_axis("source_only_detail_context_roles", allow_empty=True)
        if "source_only_detail_context_roles" in evaluation_spec
        else []
    )
    if not set(source_only_detail_context_roles) <= set(detail_context_roles) or any(
        child_by_role[role]["role_kind"] == "STRUCTURAL_GROUP"
        for role in source_only_detail_context_roles
    ):
        raise _error("multi-table hierarchical source-only detail contexts are invalid")
    row_population_context_roles_requiring_explicit_heading = (
        role_axis(
            "row_population_context_roles_requiring_explicit_heading", allow_empty=True
        )
        if "row_population_context_roles_requiring_explicit_heading" in evaluation_spec
        else []
    )
    if not set(row_population_context_roles_requiring_explicit_heading) <= set(
        table_context_roles
    ):
        raise _error(
            "multi-table hierarchical explicit-heading context roles are invalid"
        )
    continuation_period_axis_policy = evaluation_spec.get(
        "continuation_period_axis_policy", "LOCAL_PERIOD_AXIS_ONLY"
    )
    if continuation_period_axis_policy not in {
        "LOCAL_PERIOD_AXIS_ONLY",
        "ADJACENT_PAGE_EXPLICIT_CONTINUATION_INHERITS_COMPLETE_BLANK_HEADER_AXIS",
    }:
        raise _error("multi-table hierarchical continuation period policy is invalid")
    continuation_leading_child_scope_policy = evaluation_spec.get(
        "continuation_leading_child_scope_policy", "DISABLED"
    )
    if continuation_leading_child_scope_policy not in {
        "DISABLED",
        "EXACT_PRIOR_ROOT_CARRIER_SCOPES_CONSECUTIVE_RECEIVER_PREFIX",
    }:
        raise _error(
            "multi-table hierarchical continuation leading-child scope policy is invalid"
        )
    adjacent_continuation_family_root_policy = evaluation_spec.get(
        "adjacent_continuation_family_root_policy", "DISABLED"
    )
    if adjacent_continuation_family_root_policy not in {
        "DISABLED",
        "EXACT_UNION_OF_DECLARED_ROOT_COMPONENTS_EQUALS_RECEIVER_TERMINAL_TOTAL",
    }:
        raise _error(
            "multi-table hierarchical adjacent continuation family-root policy is invalid"
        )
    cross_fragment_same_role_parent_equation_policy = evaluation_spec.get(
        "cross_fragment_same_role_parent_equation_policy", "DISABLED"
    )
    if cross_fragment_same_role_parent_equation_policy not in {
        "DISABLED",
        (
            "EXACT_ADJACENT_PRIOR_TERMINAL_COLON_SAME_ROLE_PARENT_EQUALS_"
            "RECEIVER_LEADING_DETAIL_SUM_ALL_LANES"
        ),
    }:
        raise _error(
            "multi-table hierarchical cross-fragment same-role equation policy is invalid"
        )
    duration_header_path_scope_policy = evaluation_spec.get(
        "duration_header_path_scope_policy", "WHOLE_HEADER_PATH"
    )
    if duration_header_path_scope_policy not in {
        "WHOLE_HEADER_PATH",
        "DISTINCT_SUFFIX_AFTER_EXACT_COMMON_PREFIX",
    }:
        raise _error("multi-table hierarchical duration header-path scope is invalid")
    numbered_subsection_unit_axis_policy = evaluation_spec.get(
        "numbered_subsection_unit_axis_policy", "LOCAL_UNIT_AXIS_ONLY"
    )
    if numbered_subsection_unit_axis_policy not in {
        "LOCAL_UNIT_AXIS_ONLY",
        "SAME_PAGE_ADJACENT_EXPLICIT_OWNER_SUBSECTION_INHERITS_UNIT",
    }:
        raise _error("multi-table hierarchical numbered-subsection unit policy is invalid")
    owner_outline_continuation_policy = evaluation_spec.get(
        "owner_outline_continuation_policy", "SOURCE_POSITION_ONLY"
    )
    if owner_outline_continuation_policy not in {
        "SOURCE_POSITION_ONLY",
        "SAME_SECTION_NUMBERED_TABLE_PRECEDES_HIGHER_NUMBERED_NARRATIVE_RESET",
    }:
        raise _error("multi-table hierarchical owner outline continuation is invalid")
    owner_summary_structural_role_policy = evaluation_spec.get(
        "owner_summary_structural_role_policy", "DISABLED"
    )
    if owner_summary_structural_role_policy not in {
        "DISABLED",
        "OWNER_TABLE_ROOT_SIBLING_FRONTIER_PREFERS_STRUCTURAL_ROLE",
    }:
        raise _error("multi-table hierarchical owner summary structural role is invalid")
    sole_table_detail_narrative_context_policy = evaluation_spec.get(
        "sole_table_detail_narrative_context_policy", "DISABLED"
    )
    if sole_table_detail_narrative_context_policy not in {
        "DISABLED",
        "TITLELESS_SOLE_MONEY_TABLE_EXACT_LONGEST_DECLARED_CONTEXT",
    }:
        raise _error("multi-table hierarchical sole-table narrative context is invalid")
    ordered_titleless_money_table_narrative_context_policy = evaluation_spec.get(
        "ordered_titleless_money_table_narrative_context_policy", "DISABLED"
    )
    if ordered_titleless_money_table_narrative_context_policy not in {
        "DISABLED",
        "ONE_TO_ONE_ORDERED_EXACT_DECLARED_CONTEXTS",
    }:
        raise _error("multi-table hierarchical ordered narrative context is invalid")
    root_component_roles = role_axis("root_component_roles")
    root_component_role_combinations = []
    raw_root_component_role_combinations = evaluation_spec.get(
        "root_component_role_combinations"
    )
    if raw_root_component_role_combinations is not None:
        equation_policies = {
            "DECLARED_DIRECT_SUM",
            "UNIQUE_DECLARED_SIGN_ORIENTATION_FIRST_COMPONENT_POSITIVE",
        }
        if (
            type(raw_root_component_role_combinations) is not list
            or not raw_root_component_role_combinations
        ):
            raise _error(
                "multi-table hierarchical root component role combinations are invalid"
            )
        component_policy_by_role: dict[str, str] = {}
        combination_role_axes = []
        for raw in raw_root_component_role_combinations:
            if (
                type(raw) is not dict
                or set(raw)
                != {
                    "component_frontier_equation_policy",
                    "equation_policy",
                    "roles",
                }
                or type(raw.get("roles")) is not list
                or not raw["roles"]
                or any(type(role) is not str or role not in roles for role in raw["roles"])
                or len(raw["roles"]) != len(set(raw["roles"]))
                or raw.get("equation_policy") not in equation_policies
                or raw.get("component_frontier_equation_policy") not in equation_policies
            ):
                raise _error(
                    "multi-table hierarchical root component role combination is invalid"
                )
            role_axis_key = tuple(raw["roles"])
            if role_axis_key in combination_role_axes:
                raise _error(
                    "multi-table hierarchical root component role combination is repeated"
                )
            combination_role_axes.append(role_axis_key)
            for role in raw["roles"]:
                prior_policy = component_policy_by_role.setdefault(
                    role, raw["component_frontier_equation_policy"]
                )
                if prior_policy != raw["component_frontier_equation_policy"]:
                    raise _error(
                        "multi-table hierarchical component frontier equation policy conflicts"
                    )
            root_component_role_combinations.append(canonical_clone_v1(raw))
        first = root_component_role_combinations[0]
        if (
            first["roles"] != root_component_roles
            or first["equation_policy"] != root_component_equation_policy
            or first["component_frontier_equation_policy"] != "DECLARED_DIRECT_SUM"
        ):
            raise _error(
                "multi-table hierarchical first root component combination differs from legacy policy"
            )
    role_anchored_owner_fallback_policy = evaluation_spec.get(
        "role_anchored_owner_fallback_policy", "DISABLED"
    )
    if role_anchored_owner_fallback_policy not in {
        "DISABLED",
        "UNIQUE_REQUIRED_ROLE_TABLE_PLUS_SAME_PAGE_DECLARED_SUPPLEMENTAL_TABLES",
    }:
        raise _error("multi-table hierarchical role-anchored owner fallback is invalid")
    role_anchored_supplemental_roles = (
        role_axis("role_anchored_supplemental_roles", allow_empty=True)
        if "role_anchored_supplemental_roles" in evaluation_spec
        else []
    )
    if role_anchored_owner_fallback_policy == "DISABLED" and role_anchored_supplemental_roles:
        raise _error("multi-table hierarchical disabled role fallback has supplemental roles")
    validation_only_roles = (
        role_axis("validation_only_roles", allow_empty=True)
        if "validation_only_roles" in evaluation_spec
        else []
    )
    if (
        source_hierarchy_overlap_total_policy
        == "MAP_EXACT_PRINTED_TOTAL_WITH_OVERLAPPING_SOURCE_HIERARCHY_RECEIPT"
        and not validation_only_roles
    ):
        raise _error(
            "multi-table hierarchical hierarchy-overlap mapping needs validation-only roles"
        )
    non_money_metric_roles = (
        role_axis("non_money_metric_roles", allow_empty=True)
        if "non_money_metric_roles" in evaluation_spec
        else []
    )
    if not set(non_money_metric_roles) <= set(validation_only_roles):
        raise _error("multi-table hierarchical non-money roles are not validation-only")
    accepted_value_column_kinds = evaluation_spec.get("accepted_value_column_kinds", ["MONEY"])
    if (
        type(accepted_value_column_kinds) is not list
        or "MONEY" not in accepted_value_column_kinds
        or len(accepted_value_column_kinds) != len(set(accepted_value_column_kinds))
        or any(kind not in {"MONEY", "UNKNOWN"} for kind in accepted_value_column_kinds)
    ):
        raise _error("multi-table hierarchical accepted value-column kinds are invalid")
    duration_month_resolution_policy = evaluation_spec.get(
        "duration_month_resolution_policy", "DISABLED"
    )
    if duration_month_resolution_policy not in {
        "DISABLED",
        "SOURCE_VISIBLE_HEADER_OR_TYPED_DOCUMENT_DURATION_CONTEXT",
    }:
        raise _error("multi-table hierarchical duration-month policy is invalid")
    ratio_metric_equations = []
    ratio_result_roles = set()
    for equation in evaluation_spec.get("ratio_metric_equations", []):
        if (
            type(equation) is not dict
            or set(equation)
            != {
                "decimal_scale",
                "denominator_role",
                "numerator_roles",
                "result_role",
            }
            or equation.get("result_role") not in roles
            or equation["result_role"] in ratio_result_roles
            or equation.get("denominator_role") not in roles
            or equation["denominator_role"] == equation["result_role"]
            or type(equation.get("numerator_roles")) is not list
            or not equation["numerator_roles"]
            or len(equation["numerator_roles"]) != len(set(equation["numerator_roles"]))
            or any(
                role not in roles or role in {equation["result_role"], equation["denominator_role"]}
                for role in equation["numerator_roles"]
            )
            or type(equation.get("decimal_scale")) is not int
            or not 0 <= equation["decimal_scale"] <= 6
        ):
            raise _error("multi-table hierarchical ratio metric equation is invalid")
        ratio_result_roles.add(equation["result_role"])
        ratio_metric_equations.append(canonical_clone_v1(equation))
    if bool(ratio_metric_equations) != (
        duration_month_resolution_policy
        == "SOURCE_VISIBLE_HEADER_OR_TYPED_DOCUMENT_DURATION_CONTEXT"
    ):
        raise _error("multi-table hierarchical ratio and duration policies disagree")
    if ratio_result_roles.intersection(validation_only_roles):
        raise _error("multi-table hierarchical ratio result role is validation-only")
    multi_metric_lane_equation = None
    if "multi_metric_lane_equation" in evaluation_spec:
        raw_metric_equation = evaluation_spec["multi_metric_lane_equation"]
        if (
            type(raw_metric_equation) is not dict
            or set(raw_metric_equation)
            != {
                "component_terms",
                "coverage_policy",
                "metric_aliases",
                "result_metric",
            }
            or raw_metric_equation.get("coverage_policy") != "EVERY_VISIBLE_SOURCE_ROW_EXACT"
            or type(raw_metric_equation.get("metric_aliases")) is not dict
            or not 2 <= len(raw_metric_equation["metric_aliases"]) <= 8
            or type(raw_metric_equation.get("result_metric")) is not str
            or raw_metric_equation["result_metric"] not in raw_metric_equation["metric_aliases"]
            or type(raw_metric_equation.get("component_terms")) is not list
            or not raw_metric_equation["component_terms"]
        ):
            raise _error("multi-table hierarchical multi-metric lane equation is invalid")
        metric_aliases = {}
        normalized_metric_aliases = set()
        for metric, aliases in raw_metric_equation["metric_aliases"].items():
            if (
                type(metric) is not str
                or re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", metric) is None
                or type(aliases) is not list
                or not aliases
                or any(type(alias) is not str or not _normalized(alias) for alias in aliases)
            ):
                raise _error("multi-table hierarchical metric aliases are invalid")
            normalized = sorted({_normalized(alias) for alias in aliases})
            if len(normalized) != len(aliases) or normalized_metric_aliases.intersection(
                normalized
            ):
                raise _error("multi-table hierarchical metric aliases overlap")
            normalized_metric_aliases.update(normalized)
            metric_aliases[metric] = normalized
        component_terms = []
        component_metrics = set()
        for term in raw_metric_equation["component_terms"]:
            if (
                type(term) is not dict
                or set(term) != {"metric", "sign"}
                or term.get("metric") not in metric_aliases
                or term["metric"] == raw_metric_equation["result_metric"]
                or term["metric"] in component_metrics
                or type(term.get("sign")) is not int
                or term.get("sign") not in {-1, 1}
            ):
                raise _error("multi-table hierarchical metric component term is invalid")
            component_metrics.add(term["metric"])
            component_terms.append(canonical_clone_v1(term))
        if component_metrics | {raw_metric_equation["result_metric"]} != set(metric_aliases):
            raise _error("multi-table hierarchical metric equation frontier is incomplete")
        multi_metric_lane_equation = {
            "component_terms": component_terms,
            "coverage_policy": "EVERY_VISIBLE_SOURCE_ROW_EXACT",
            "metric_aliases": metric_aliases,
            "result_metric": raw_metric_equation["result_metric"],
        }
    signed_context_frontier_equations = []
    signed_frontier_carrier_roles = set()
    for declaration in evaluation_spec.get("signed_context_frontier_equations", []):
        if (
            type(declaration) is not dict
            or set(declaration)
            != {
                "allowed_component_roles",
                "carrier_role",
                "policy",
                "resolved_adjustment_role",
                "source_adjustment_roles",
            }
            or declaration.get("policy")
            != ("FIRST_CARRIER_THEN_CONTIGUOUS_DECLARED_COMPONENTS_ENDING_IN_SIGNED_ADJUSTMENT")
            or declaration.get("carrier_role") not in roles
            or declaration["carrier_role"] in validation_only_roles
            or declaration["carrier_role"] in signed_frontier_carrier_roles
            or type(declaration.get("allowed_component_roles")) is not list
            or not declaration["allowed_component_roles"]
            or len(declaration["allowed_component_roles"])
            != len(set(declaration["allowed_component_roles"]))
            or declaration["carrier_role"] not in declaration["allowed_component_roles"]
            or any(role not in roles for role in declaration["allowed_component_roles"])
            or type(declaration.get("source_adjustment_roles")) is not list
            or not declaration["source_adjustment_roles"]
            or len(declaration["source_adjustment_roles"])
            != len(set(declaration["source_adjustment_roles"]))
            or any(
                role not in validation_only_roles for role in declaration["source_adjustment_roles"]
            )
            or declaration.get("resolved_adjustment_role")
            not in declaration["source_adjustment_roles"]
            or declaration["resolved_adjustment_role"] not in declaration["allowed_component_roles"]
            or not set(declaration["source_adjustment_roles"])
            <= set(declaration["allowed_component_roles"])
        ):
            raise _error("multi-table hierarchical signed context frontier is invalid")
        signed_frontier_carrier_roles.add(declaration["carrier_role"])
        signed_context_frontier_equations.append(canonical_clone_v1(declaration))
    ordered_role_scopes = []
    ordered_role_scope_ids = set()
    supplied_ordered_role_scopes = evaluation_spec.get("ordered_role_scopes", [])
    if type(supplied_ordered_role_scopes) is not list:
        raise _error("multi-table hierarchical ordered role scopes are invalid")
    for scope in supplied_ordered_role_scopes:
        if (
            type(scope) is not dict
            or set(scope) != {"scope_id", "scoped_roles", "start_after_roles", "terminal_roles"}
            or type(scope.get("scope_id")) is not str
            or not scope["scope_id"]
            or scope["scope_id"] in ordered_role_scope_ids
        ):
            raise _error("multi-table hierarchical ordered role scope is invalid")
        axes = {}
        for field in ("scoped_roles", "start_after_roles", "terminal_roles"):
            axis = scope.get(field)
            if (
                type(axis) is not list
                or (field != "start_after_roles" and not axis)
                or any(type(role) is not str or role not in roles for role in axis)
                or len(axis) != len(set(axis))
            ):
                raise _error("multi-table hierarchical ordered role scope axis is invalid")
            axes[field] = list(axis)
        if not set(axes["terminal_roles"]) <= set(axes["scoped_roles"]):
            raise _error("multi-table hierarchical ordered terminal is outside its scope")
        ordered_role_scope_ids.add(scope["scope_id"])
        ordered_role_scopes.append({"scope_id": scope["scope_id"], **axes})
    aggregate_duplicate_roles = role_axis("aggregate_duplicate_roles", allow_empty=True)
    ordered_role_scope_projections = []
    supplied_scope_projections = evaluation_spec.get("ordered_role_scope_projections", [])
    if type(supplied_scope_projections) is not list:
        raise _error("multi-table hierarchical ordered role projections are invalid")
    scope_by_id = {scope["scope_id"]: scope for scope in ordered_role_scopes}
    projection_keys = set()
    for projection in supplied_scope_projections:
        if (
            type(projection) is not dict
            or set(projection) != {"scope_id", "source_role", "target_role"}
            or projection.get("scope_id") not in scope_by_id
            or projection.get("source_role") not in validation_only_roles
            or projection["source_role"] not in scope_by_id[projection["scope_id"]]["scoped_roles"]
            or projection.get("target_role") not in roles
            or projection["target_role"] in validation_only_roles
            or projection["target_role"] not in aggregate_duplicate_roles
            or projection["source_role"] == projection["target_role"]
            or (
                projection["scope_id"],
                projection["source_role"],
                projection["target_role"],
            )
            in projection_keys
        ):
            raise _error("multi-table hierarchical ordered role projection is invalid")
        projection_keys.add(
            (
                projection["scope_id"],
                projection["source_role"],
                projection["target_role"],
            )
        )
        ordered_role_scope_projections.append(canonical_clone_v1(projection))
    context_residual_bindings = []
    context_residual_context_roles = set()
    context_residual_roles = set()
    supplied_context_residual_bindings = evaluation_spec.get("context_residual_bindings", [])
    if type(supplied_context_residual_bindings) is not list:
        raise _error("multi-table hierarchical context residual bindings are invalid")
    for binding in supplied_context_residual_bindings:
        if (
            type(binding) is not dict
            or set(binding) != {"context_role", "residual_role"}
            or binding.get("context_role") not in roles
            or binding["context_role"] in context_residual_context_roles
            or binding.get("residual_role") not in roles
            or binding["residual_role"] in context_residual_roles
            or binding["context_role"] == binding["residual_role"]
            or binding["context_role"]
            not in set(table_context_roles) | set(context_total_mapping_roles)
            or child_by_role[binding["context_role"]]["role_kind"] != "STRUCTURAL_GROUP"
            or child_by_role[binding["residual_role"]]["role_kind"] != "ADDITIVE_CHILD"
            or binding["residual_role"] not in aggregate_duplicate_roles
        ):
            raise _error("multi-table hierarchical context residual binding is invalid")
        context_residual_context_roles.add(binding["context_role"])
        context_residual_roles.add(binding["residual_role"])
        context_residual_bindings.append(canonical_clone_v1(binding))
    equation_consumed_unmatched_residual_role = evaluation_spec.get(
        "equation_consumed_unmatched_residual_role"
    )
    if equation_consumed_unmatched_residual_role is not None and (
        type(equation_consumed_unmatched_residual_role) is not str
        or equation_consumed_unmatched_residual_role not in roles
        or equation_consumed_unmatched_residual_role not in aggregate_duplicate_roles
    ):
        raise _error("multi-table hierarchical unmatched residual role is invalid")
    equation_consumed_unmatched_residual_anchor_policy = evaluation_spec.get(
        "equation_consumed_unmatched_residual_anchor_policy",
        "DIRECT_RESIDUAL_ROLE_REQUIRED",
    )
    if equation_consumed_unmatched_residual_anchor_policy not in {
        "DIRECT_RESIDUAL_ROLE_REQUIRED",
        "EXACT_SOURCE_EQUATION_FRONTIER_SUFFICIENT",
    } or (
        equation_consumed_unmatched_residual_role is None
        and equation_consumed_unmatched_residual_anchor_policy != "DIRECT_RESIDUAL_ROLE_REQUIRED"
    ):
        raise _error("multi-table hierarchical unmatched residual anchor policy is invalid")
    validation_role_leaf_projections = []
    leaf_projection_sources = set()
    for projection in evaluation_spec.get("validation_role_leaf_projections", []):
        if (
            type(projection) is not dict
            or set(projection) != {"source_role", "target_role"}
            or projection.get("source_role") not in validation_only_roles
            or projection["source_role"] in leaf_projection_sources
            or projection.get("target_role") not in roles
            or projection["target_role"] in validation_only_roles
            or projection["source_role"] == projection["target_role"]
            or projection["target_role"] not in aggregate_duplicate_roles
        ):
            raise _error("multi-table hierarchical validation leaf projection is invalid")
        leaf_projection_sources.add(projection["source_role"])
        validation_role_leaf_projections.append(canonical_clone_v1(projection))
    row_alias_prefix_roles = (
        role_axis("row_alias_prefix_roles", allow_empty=True)
        if "row_alias_prefix_roles" in evaluation_spec
        else []
    )
    supplemental_owner_aliases = evaluation_spec.get("supplemental_owner_aliases", [])
    if type(supplemental_owner_aliases) is not list or any(
        type(alias) is not str or not _normalized(alias) for alias in supplemental_owner_aliases
    ):
        raise _error("multi-table hierarchical supplemental owner aliases are invalid")
    supplemental_owner_aliases = sorted(
        {_normalized(alias) for alias in supplemental_owner_aliases}
    )
    query_owner_aliases = evaluation_spec.get("query_owner_aliases")
    if query_owner_aliases is not None and (
        type(query_owner_aliases) is not list
        or not query_owner_aliases
        or any(type(alias) is not str or not _normalized(alias) for alias in query_owner_aliases)
    ):
        raise _error("multi-table hierarchical query owner aliases are invalid")
    if query_owner_aliases is not None:
        query_owner_aliases = sorted({_normalized(alias) for alias in query_owner_aliases})
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
    supplemental_detail_residuals = []
    supplemental_residual_roles = set()
    for declaration in evaluation_spec.get("supplemental_detail_residuals", []):
        if (
            type(declaration) is not dict
            or set(declaration) != {"markers", "residual_role"}
            or declaration.get("residual_role") not in roles
            or declaration["residual_role"] in supplemental_residual_roles
            or declaration["residual_role"] not in aggregate_duplicate_roles
            or type(declaration.get("markers")) is not list
            or not declaration["markers"]
            or any(
                type(marker) is not str or not _normalized(marker)
                for marker in declaration["markers"]
            )
        ):
            raise _error("multi-table hierarchical supplemental detail residual is invalid")
        supplemental_residual_roles.add(declaration["residual_role"])
        supplemental_detail_residuals.append(
            {
                "markers": sorted({_normalized(marker) for marker in declaration["markers"]}),
                "residual_role": declaration["residual_role"],
            }
        )
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
        unless_declared_roles = item.get("unless_declared_roles", [])
        required_row_label_alias_groups = item.get(
            "required_row_label_alias_groups", []
        )
        match_mode = item.get("match_mode", "CONTAINS_NORMALIZED")
        if (
            type(item) is not dict
            or not {"aliases", "disposition"} <= set(item)
            or set(item)
            - {
                "aliases",
                "disposition",
                "match_mode",
                "surface_kinds",
                "unless_declared_roles",
                "required_row_label_alias_groups",
            }
            or type(item.get("disposition")) is not str
            or not item["disposition"]
            or type(item.get("aliases")) is not list
            or not item["aliases"]
            or any(type(alias) is not str or not _normalized(alias) for alias in item["aliases"])
            or type(surface_kinds) is not list
            or not surface_kinds
            or len(surface_kinds) != len(set(surface_kinds))
            or any(
                kind
                not in {
                    "SECTION_TITLE",
                    "SECTION_NARRATIVE",
                    "TABLE_TITLE",
                    "COLUMN_HEADER",
                    "ROW_LABEL_POPULATION",
                }
                for kind in surface_kinds
            )
            or type(unless_declared_roles) is not list
            or len(unless_declared_roles) != len(set(unless_declared_roles))
            or any(type(role) is not str or role not in roles for role in unless_declared_roles)
            or type(required_row_label_alias_groups) is not list
            or any(
                type(group) is not list
                or not group
                or len(group) != len(set(group))
                or any(type(alias) is not str or not _normalized(alias) for alias in group)
                for group in required_row_label_alias_groups
            )
            or match_mode not in {"CONTAINS_NORMALIZED", "EXACT_NORMALIZED"}
        ):
            raise _error("multi-table hierarchical typed control exclusion is invalid")
        exclusion = {
            "aliases": sorted({_normalized(alias) for alias in item["aliases"]}),
            "disposition": item["disposition"],
        }
        if "surface_kinds" in item:
            exclusion["surface_kinds"] = sorted(surface_kinds)
        if "unless_declared_roles" in item:
            exclusion["unless_declared_roles"] = sorted(unless_declared_roles)
        if "required_row_label_alias_groups" in item:
            exclusion["required_row_label_alias_groups"] = [
                sorted({_normalized(alias) for alias in group})
                for group in required_row_label_alias_groups
            ]
        if "match_mode" in item:
            exclusion["match_mode"] = match_mode
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
            "STRUCTURAL_CONTEXT_ONLY",
            "SOURCE_VISIBLE_EXACT_RESULT_WITH_OPTIONAL_COMPLETE_COMPONENT_EQUATION_VETO",
            "SOURCE_VISIBLE_PRIMARY_RESULT_OR_EXACT_NOTE_EQUATION",
            "SOURCE_VISIBLE_TOTAL_PROVEN_BY_EXACT_EQUATION_ONLY",
            "SOURCE_VISIBLE_TOTAL_OR_COMPLETE_TOP_LEVEL_COMPONENT_SUM",
        }
        or schema_binding_spec.get("schema_period_type") not in {"SNAPSHOT", "DURATION"}
        or (
            evaluation_spec["period_semantics"] == "CURRENT_AND_COMPARATIVE_SNAPSHOT"
            and schema_binding_spec.get("schema_period_type") != "SNAPSHOT"
        )
        or (
            evaluation_spec["period_semantics"] == "CURRENT_AND_COMPARATIVE_DURATION"
            and schema_binding_spec.get("schema_period_type") != "DURATION"
        )
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
    if not bindings or not (set(root_component_roles) - set(validation_only_roles)) <= set(
        bindings
    ):
        raise _error("multi-table hierarchical schema frontier is incomplete")
    if any(
        projection["target_role"] not in bindings for projection in ordered_role_scope_projections
    ):
        raise _error("multi-table hierarchical ordered projection target is not mapped")
    if any(
        projection["target_role"] not in bindings for projection in validation_role_leaf_projections
    ):
        raise _error("multi-table hierarchical validation leaf projection target is not mapped")
    aliases_by_role = {role: _aliases(child) for role, child in child_by_role.items()}
    presence_anchor_roles = sorted(
        role
        for role, child in child_by_role.items()
        if any(matcher["presence_anchor"] for matcher in child["matchers"])
    )
    query_policy = {
        "hard_negative_aliases": canonical_clone_v1(topology["hard_negative_aliases"]),
        "leading_component_policy": evaluation_spec["component_policy"],
        "owner_aliases": sorted(
            query_owner_aliases
            if query_owner_aliases is not None
            else {
                *topology["parent"]["aliases"],
                *supplemental_owner_aliases,
            }
        ),
        "reset_aliases": canonical_clone_v1(topology["structural_reset_aliases"]),
    }
    if "owner_surface_kinds" in evaluation_spec:
        # Preserve the exact compiled policy/hash of existing released families
        # while binding every family that opts into a narrower source surface.
        query_policy["owner_surface_kinds"] = list(owner_surface_kinds)
    if "owner_match_policy" in evaluation_spec:
        query_policy["owner_match_policy"] = owner_match_policy
    if "hierarchy_role_scope_policy" in evaluation_spec:
        query_policy["hierarchy_role_scope_policy"] = hierarchy_role_scope_policy
    if "structural_marker_policy" in evaluation_spec:
        query_policy["structural_marker_policy"] = structural_marker_policy
    if "row_alias_prefix_roles" in evaluation_spec:
        query_policy["row_alias_prefix_roles"] = row_alias_prefix_roles
    if "declared_result_role_policy" in evaluation_spec:
        query_policy["declared_result_role_policy"] = declared_result_role_policy
    if "role_anchored_owner_fallback_policy" in evaluation_spec:
        query_policy["role_anchored_owner_fallback_policy"] = role_anchored_owner_fallback_policy
    if "role_anchored_supplemental_roles" in evaluation_spec:
        query_policy["role_anchored_supplemental_roles"] = role_anchored_supplemental_roles
    if "non_money_metric_roles" in evaluation_spec:
        query_policy["non_money_metric_roles"] = non_money_metric_roles
    if "accepted_value_column_kinds" in evaluation_spec:
        query_policy["accepted_value_column_kinds"] = accepted_value_column_kinds
    if "ratio_metric_equations" in evaluation_spec:
        query_policy["ratio_metric_roles"] = sorted(ratio_result_roles)
    if "ordered_role_scopes" in evaluation_spec:
        query_policy["ordered_role_scopes"] = canonical_clone_v1(ordered_role_scopes)
    if "supplemental_owner_aliases" in evaluation_spec:
        query_policy["supplemental_owner_aliases"] = supplemental_owner_aliases
    if "query_owner_aliases" in evaluation_spec:
        query_policy["query_owner_aliases"] = query_owner_aliases
    if "document_cluster_policy" in evaluation_spec:
        query_policy["document_cluster_policy"] = document_cluster_policy
    if "document_source_result_signal_policy" in evaluation_spec:
        query_policy["document_source_result_signal_policy"] = document_source_result_signal_policy
    if "source_result_query_policy" in evaluation_spec:
        query_policy["source_result_query_policy"] = source_result_query_policy
    if "minimum_declared_detail_role_count" in evaluation_spec:
        query_policy["minimum_declared_detail_role_count"] = minimum_declared_detail_role_count
    if "owner_complete_population_policy" in evaluation_spec:
        query_policy["owner_complete_population_policy"] = owner_complete_population_policy
    if "row_population_context_policy" in evaluation_spec:
        query_policy["row_population_context_policy"] = row_population_context_policy
    return {
        "aggregate_duplicate_roles": aggregate_duplicate_roles,
        **(
            {"accepted_value_column_kinds": accepted_value_column_kinds}
            if "accepted_value_column_kinds" in evaluation_spec
            else {}
        ),
        "aliases_by_role": aliases_by_role,
        "bindings": bindings,
        "claim_boundary": CLAIM_BOUNDARY,
        "child_by_role": child_by_role,
        "currency_aliases": {},
        "corroboration_pairs": corroboration_pairs,
        "context_total_mapping_roles": context_total_mapping_roles,
        **(
            {"context_residual_bindings": context_residual_bindings}
            if context_residual_bindings
            else {}
        ),
        "derived_role_equations": derived_role_equations,
        "declared_result_role_policy": declared_result_role_policy,
        "detail_context_roles": detail_context_roles,
        **(
            {"source_only_detail_context_roles": source_only_detail_context_roles}
            if "source_only_detail_context_roles" in evaluation_spec
            else {}
        ),
        "direct_frontier_policy": direct_frontier_policy,
        "document_cluster_policy": document_cluster_policy,
        "document_source_result_signal_policy": document_source_result_signal_policy,
        "duplicate_role_aggregation_policy": duplicate_role_aggregation_policy,
        "engine_format_version": ENGINE_FORMAT_VERSION,
        "equation_consumed_unmatched_residual_role": (equation_consumed_unmatched_residual_role),
        **(
            {
                "equation_consumed_unmatched_residual_anchor_policy": (
                    equation_consumed_unmatched_residual_anchor_policy
                )
            }
            if "equation_consumed_unmatched_residual_anchor_policy" in evaluation_spec
            else {}
        ),
        "evaluation": canonical_clone_v1(evaluation_spec),
        "family_root_population_policy": family_root_population_policy,
        "family_root_requirement": family_root_requirement,
        "family_root_terminal_scope_policy": family_root_terminal_scope_policy,
        "source_total_blank_lane_control_policy": source_total_blank_lane_control_policy,
        "matchers_by_role": {
            role: canonical_clone_v1(child["matchers"]) for role, child in child_by_role.items()
        },
        "output_role_order": [item["role"] for item in schema_binding_spec["role_bindings"]],
        "label_only_structural_group_policy": label_only_structural_group_policy,
        "money_metric_policy": money_metric_policy,
        **(
            {"multi_metric_lane_equation": multi_metric_lane_equation}
            if multi_metric_lane_equation is not None
            else {}
        ),
        "non_money_metric_roles": non_money_metric_roles,
        **(
            {"duration_month_resolution_policy": duration_month_resolution_policy}
            if "duration_month_resolution_policy" in evaluation_spec
            else {}
        ),
        "ordered_role_scopes": ordered_role_scopes,
        "ordered_role_scope_projections": ordered_role_scope_projections,
        "mapped_source_subtotal_policy": mapped_source_subtotal_policy,
        "minimum_declared_detail_role_count": minimum_declared_detail_role_count,
        **(
            {"owner_complete_population_policy": owner_complete_population_policy}
            if "owner_complete_population_policy" in evaluation_spec
            else {}
        ),
        "period_lane_policy": period_lane_policy,
        **(
            {"continuation_period_axis_policy": continuation_period_axis_policy}
            if "continuation_period_axis_policy" in evaluation_spec
            else {}
        ),
        **(
            {
                "continuation_leading_child_scope_policy": (
                    continuation_leading_child_scope_policy
                )
            }
            if "continuation_leading_child_scope_policy" in evaluation_spec
            else {}
        ),
        **(
            {
                "adjacent_continuation_family_root_policy": (
                    adjacent_continuation_family_root_policy
                )
            }
            if "adjacent_continuation_family_root_policy" in evaluation_spec
            else {}
        ),
        **(
            {
                "cross_fragment_same_role_parent_equation_policy": (
                    cross_fragment_same_role_parent_equation_policy
                )
            }
            if "cross_fragment_same_role_parent_equation_policy" in evaluation_spec
            else {}
        ),
        **(
            {"duration_header_path_scope_policy": duration_header_path_scope_policy}
            if "duration_header_path_scope_policy" in evaluation_spec
            else {}
        ),
        **(
            {"numbered_subsection_unit_axis_policy": numbered_subsection_unit_axis_policy}
            if "numbered_subsection_unit_axis_policy" in evaluation_spec
            else {}
        ),
        **(
            {"owner_outline_continuation_policy": owner_outline_continuation_policy}
            if "owner_outline_continuation_policy" in evaluation_spec
            else {}
        ),
        **(
            {"owner_summary_structural_role_policy": owner_summary_structural_role_policy}
            if "owner_summary_structural_role_policy" in evaluation_spec
            else {}
        ),
        **(
            {
                "sole_table_detail_narrative_context_policy": (
                    sole_table_detail_narrative_context_policy
                )
            }
            if "sole_table_detail_narrative_context_policy" in evaluation_spec
            else {}
        ),
        **(
            {
                "ordered_titleless_money_table_narrative_context_policy": (
                    ordered_titleless_money_table_narrative_context_policy
                )
            }
            if "ordered_titleless_money_table_narrative_context_policy" in evaluation_spec
            else {}
        ),
        "primary_statement_family_root_subtree_policy": (
            primary_statement_family_root_subtree_policy
        ),
        **(
            {
                "primary_statement_source_result_fallback_policy": (
                    primary_statement_source_result_fallback_policy
                )
            }
            if "primary_statement_source_result_fallback_policy" in evaluation_spec
            else {}
        ),
        "presence_anchor_roles": presence_anchor_roles,
        "query_policy": query_policy,
        "required_role_combination_mapping_policy": (required_role_combination_mapping_policy),
        "root_component_roles": root_component_roles,
        **(
            {"root_component_role_combinations": root_component_role_combinations}
            if raw_root_component_role_combinations is not None
            else {}
        ),
        "root_component_equation_policy": root_component_equation_policy,
        "role_anchored_owner_fallback_policy": role_anchored_owner_fallback_policy,
        "role_anchored_supplemental_roles": role_anchored_supplemental_roles,
        "row_population_context_policy": row_population_context_policy,
        **(
            {
                "row_population_context_roles_requiring_explicit_heading": (
                    row_population_context_roles_requiring_explicit_heading
                )
            }
            if "row_population_context_roles_requiring_explicit_heading" in evaluation_spec
            else {}
        ),
        "role_unit_overrides": role_unit_overrides,
        **(
            {
                "ratio_metric_equations": ratio_metric_equations,
                "ratio_metric_roles": sorted(ratio_result_roles),
            }
            if "ratio_metric_equations" in evaluation_spec
            else {}
        ),
        "row_alias_prefix_roles": row_alias_prefix_roles,
        "schema": canonical_clone_v1(schema_binding_spec),
        "source_result_query_policy": source_result_query_policy,
        "source_reference_identity_policy": source_reference_identity_policy,
        "source_presentation_rounding_policy": source_presentation_rounding_policy,
        **(
            {"signed_context_frontier_equations": signed_context_frontier_equations}
            if signed_context_frontier_equations
            else {}
        ),
        **(
            {"source_hierarchy_overlap_total_policy": source_hierarchy_overlap_total_policy}
            if "source_hierarchy_overlap_total_policy" in evaluation_spec
            else {}
        ),
        "structural_parent_derivation_policy": structural_parent_derivation_policy,
        "supplemental_detail_residuals": supplemental_detail_residuals,
        "table_context_roles": table_context_roles,
        "topology": topology,
        "typed_control_exclusions": exclusions,
        "unit_binding_by_alias": unit_binding_by_alias,
        "unit_bindings": unit_bindings,
        "unmapped_direct_family_row_policy": unmapped_direct_family_row_policy,
        **(
            {"validation_role_leaf_projections": validation_role_leaf_projections}
            if validation_role_leaf_projections
            else {}
        ),
        "validation_only_roles": validation_only_roles,
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


def _outline_top_level_number(value: Any, *, governing_alias: str | None = None) -> int | None:
    """Return a source-visible note number without inventing outline scope.

    Financial-note pages often expose one owner as ``21. ...`` and the next
    note as ``22. ...`` without repeating a family-specific reset alias.  The
    top-level outline is authoritative structure, while dates and narrative
    numbers are not.  For an owner surface, only the line governed by the
    matched owner alias is eligible.  For a later heading, only a line-leading
    note number is eligible; obvious date lines fail closed.
    """

    if type(value) is not str:
        return None
    normalized_alias = _normalized(governing_alias)
    candidates = set()
    for raw_line in value.splitlines():
        line = raw_line.strip()
        normalized_line = _normalized(line)
        if not normalized_line:
            continue
        if normalized_alias and not (
            normalized_line == normalized_alias or f" {normalized_alias} " in f" {normalized_line} "
        ):
            continue
        match = re.match(
            r"^(?P<top>[1-9][0-9]{0,2})(?:\.[0-9]+)*(?:[.)])?\s+(?P<tail>.+)$",
            line,
        )
        if match is None:
            continue
        tail = _normalized(match.group("tail"))
        if tail.startswith(("thang ", "month ", "nam ", "year ")):
            continue
        candidates.add(int(match.group("top")))
    return next(iter(candidates)) if len(candidates) == 1 else None


def _outline_number_path(value: Any) -> tuple[int, ...] | None:
    """Return one source-visible dotted note path from a heading surface."""

    if type(value) is not str:
        return None
    candidates = set()
    for raw_line in value.splitlines():
        line = raw_line.strip()
        match = re.match(
            r"^(?P<path>[1-9][0-9]{0,2}(?:\.[0-9]+)+)(?:[.)])?\s+(?P<tail>.+)$",
            line,
        )
        if match is None:
            continue
        tail = _normalized(match.group("tail"))
        if tail.startswith(("thang ", "month ", "nam ", "year ")):
            continue
        candidates.add(tuple(int(part) for part in match.group("path").split(".")))
    return next(iter(candidates)) if len(candidates) == 1 else None


def _contains_alias(value: Any, alias: str) -> bool:
    folded = _normalized(value)
    alias = _normalized(alias)
    return bool(folded and alias and (folded == alias or f" {alias} " in f" {folded} "))


def _owner_visible(
    section: Mapping[str, Any], table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> bool:
    matcher = (
        _matches
        if compiled_specs["query_policy"].get("owner_match_policy")
        == "EXACT_NORMALIZED_WITH_BOUNDED_SOURCE_SUFFIX"
        else _contains_alias
    )
    return any(
        matcher(value, alias)
        for value in _owner_surface_axis(section, table, compiled_specs=compiled_specs)
        for alias in compiled_specs["query_policy"]["owner_aliases"]
    )


def _owner_marker_matches(
    value: Any, aliases: Sequence[str], *, compiled_specs: Mapping[str, Any]
) -> list[str]:
    if (
        compiled_specs["query_policy"].get("owner_match_policy")
        != "EXACT_NORMALIZED_WITH_BOUNDED_SOURCE_SUFFIX"
    ):
        return _heading_surface_matches(value, aliases, compiled_specs=compiled_specs)
    surfaces = [value]
    if (
        compiled_specs["query_policy"].get("structural_marker_policy")
        == "WHOLE_SURFACE_AND_INDIVIDUAL_LINES"
        and type(value) is str
    ):
        surfaces.extend(line for line in value.splitlines() if line.strip())
    return sorted({alias for surface in surfaces for alias in aliases if _matches(surface, alias)})


def _value_column_ordinals(
    columns: Sequence[Any], *, compiled_specs: Mapping[str, Any]
) -> list[int]:
    """Return declared numeric columns without trusting Gemini's soft kind alone.

    ``UNKNOWN`` is opt-in for families whose tables contain a heterogeneous
    metric axis (people, money, and per-person ratios).  Ownership, row roles,
    period evidence, and unit evidence still have to close independently; this
    helper never promotes an arbitrary unknown table by itself.
    """

    accepted = set(compiled_specs.get("accepted_value_column_kinds", ["MONEY"]))
    return [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") in accepted
    ]


def _typed_control_disposition(
    page_json: Mapping[str, Any],
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
    declared_roles: Sequence[str] = (),
) -> tuple[str | None, list[dict[str, Any]]]:
    if page_json.get("status") == "PRIMARY_FINANCIAL_STATEMENT" or (
        section.get("content_kind") == "PRIMARY_STATEMENT"
        and section.get("statement_type") == "BALANCE_SHEET"
    ):
        return "PRIMARY_FINANCIAL_STATEMENT_SUMMARY", []
    override_receipts = []
    for exclusion in compiled_specs["typed_control_exclusions"]:
        if _typed_control_surface_matches(exclusion, section=section, table=table):
            overrides = sorted(
                set(declared_roles).intersection(exclusion.get("unless_declared_roles", []))
            )
            if overrides:
                override_receipts.append(
                    {
                        "control_disposition": exclusion["disposition"],
                        "declared_roles": overrides,
                        "rule": "DECLARED_ROLE_EXPLICITLY_OVERRIDES_BROAD_CONTROL_SURFACE",
                    }
                )
                continue
            return exclusion["disposition"], override_receipts
    columns = table.get("columns")
    if type(columns) is list and not _value_column_ordinals(columns, compiled_specs=compiled_specs):
        return "NO_MONEY_VALUE_AXIS", override_receipts
    return None, override_receipts


def _typed_control_surface_matches(
    exclusion: Mapping[str, Any], *, section: Mapping[str, Any], table: Mapping[str, Any]
) -> bool:
    """Match one declared control only on its exact opted-in source axis."""

    kinds = exclusion.get("surface_kinds", ["SECTION_TITLE", "SECTION_NARRATIVE", "TABLE_TITLE"])
    surfaces = []
    if "SECTION_TITLE" in kinds:
        surfaces.append(_normalized(section.get("title_exact")))
    if "SECTION_NARRATIVE" in kinds:
        narratives = section.get("narratives_exact")
        if type(narratives) is list:
            surfaces.extend(_normalized(value) for value in narratives)
    if "TABLE_TITLE" in kinds:
        surfaces.append(_normalized(table.get("title_exact")))
    columns = table.get("columns")
    if "COLUMN_HEADER" in kinds and type(columns) is list:
        # Untitled control tables can be distinguishable only by declared
        # metric headers.  This scope is opt-in so a shared section narrative
        # cannot accidentally exclude its accounting sibling.
        surfaces.extend(
            _normalized(_header_text(column)) for column in columns if type(column) is dict
        )
    exact = exclusion.get("match_mode", "CONTAINS_NORMALIZED") == "EXACT_NORMALIZED"

    def matches(surface: str, alias: str) -> bool:
        return surface == alias if exact else alias in surface

    surface_match = any(
        surface and any(matches(surface, alias) for alias in exclusion["aliases"])
        for surface in surfaces
    )
    required_groups = exclusion.get("required_row_label_alias_groups", [])
    if surface_match and required_groups:
        rows = table.get("rows")
        labels = (
            [
                _normalized(row.get("label_exact"))
                for row in rows
                if type(row) is dict and _normalized(row.get("label_exact"))
            ]
            if type(rows) is list
            else []
        )
        return bool(
            labels
            and all(
                any(matches(label, alias) for label in labels for alias in group)
                for group in required_groups
            )
        )
    if surface_match:
        return True
    if "ROW_LABEL_POPULATION" not in kinds:
        return False
    rows = table.get("rows")
    if type(rows) is not list:
        return False
    labels = [
        _normalized(row.get("label_exact"))
        for row in rows
        if type(row) is dict
        and row.get("row_kind") != "TOTAL"
        and type(row.get("values_exact")) is list
        and _normalized(row.get("label_exact"))
    ]
    return bool(
        labels
        and all(any(matches(label, alias) for alias in exclusion["aliases"]) for label in labels)
    )


def _sole_titleless_money_table_narratives(
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
) -> list[str]:
    """Return only narratives structurally local to one titleless MONEY table."""

    if (
        compiled_specs.get("sole_table_detail_narrative_context_policy", "DISABLED")
        != "TITLELESS_SOLE_MONEY_TABLE_EXACT_LONGEST_DECLARED_CONTEXT"
        or _normalized(table.get("title_exact"))
    ):
        return []
    tables = section.get("tables")
    if type(tables) is not list:
        return []
    money_tables = [
        candidate
        for candidate in tables
        if type(candidate) is dict
        and type(candidate.get("columns")) is list
        and _value_column_ordinals(candidate["columns"], compiled_specs=compiled_specs)
    ]
    if len(money_tables) != 1 or money_tables[0] is not table:
        return []
    narratives = section.get("narratives_exact")
    if type(narratives) is not list:
        return []
    return [
        value
        for value in narratives
        if type(value) is str
        if _normalized(value)
    ]


def _ordered_titleless_money_table_narrative_context(
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Bind one titleless MONEY table to one exact ordered narrative.

    A multi-table section heading is only an umbrella.  Some sources instead
    print one numbered narrative immediately for each following titleless
    table.  This opt-in recognizes that source grammar only when the complete
    section has a one-to-one, source-ordered axis: every titleless MONEY table
    has one exact declared context narrative and every resolved role is
    unique.  Unrelated prose is ignored, while a duplicate/ambiguous declared
    narrative makes the whole axis unusable.
    """

    if (
        compiled_specs.get(
            "ordered_titleless_money_table_narrative_context_policy", "DISABLED"
        )
        != "ONE_TO_ONE_ORDERED_EXACT_DECLARED_CONTEXTS"
        or _normalized(table.get("title_exact"))
    ):
        return None
    tables = section.get("tables")
    if type(tables) is not list:
        return None
    all_money_tables = [
        candidate
        for candidate in tables
        if type(candidate) is dict
        and type(candidate.get("columns")) is list
        and _value_column_ordinals(candidate["columns"], compiled_specs=compiled_specs)
    ]
    money_tables = [
        candidate
        for candidate in all_money_tables
        if not _normalized(candidate.get("title_exact"))
    ]
    if len(money_tables) != len(all_money_tables):
        return None
    table_indexes = [index for index, candidate in enumerate(money_tables) if candidate is table]
    if len(table_indexes) != 1:
        return None
    narratives = section.get("narratives_exact")
    if type(narratives) is not list:
        return None
    declared_context_roles = sorted(
        {
            *compiled_specs["table_context_roles"],
            *compiled_specs["detail_context_roles"],
        }
    )
    contexts = []
    for narrative_ordinal, value in enumerate(narratives, start=1):
        if type(value) is not str:
            continue
        exact = _without_leading_ordinal(_normalized(value))
        if not exact:
            continue
        roles = sorted(
            role
            for role in declared_context_roles
            if any(exact == _normalized(alias) for alias in compiled_specs["aliases_by_role"][role])
        )
        if len(roles) > 1:
            return None
        if len(roles) == 1:
            contexts.append(
                {
                    "narrative_ordinal": narrative_ordinal,
                    "role": roles[0],
                    "source_exact": value,
                }
            )
    if (
        len(contexts) != len(money_tables)
        or len({context["role"] for context in contexts}) != len(contexts)
    ):
        return None
    table_index = table_indexes[0]
    context = contexts[table_index]
    return {
        **context,
        "money_table_ordinal": table_index + 1,
        "ordered_context_roles": [item["role"] for item in contexts],
        "rule": "ONE_TO_ONE_SOURCE_ORDERED_TITLELESS_MONEY_TABLE_EXACT_DECLARED_NARRATIVES",
    }


def _context_roles(
    section: Mapping[str, Any], table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> list[str]:
    # A section heading scopes its sole table.  In a multi-table section it is
    # only an umbrella: sibling populations must establish context from their
    # own table title or from a coherent row-role population.  This prevents a
    # summary heading from being copied onto every later detail/roll-forward.
    tables = section.get("tables")
    context_surfaces = [table.get("title_exact")]
    section_title_scopes_table = bool(type(tables) is list and len(tables) == 1)
    if type(tables) is list and len(tables) > 1:
        noncontrol_tables = []
        for sibling in tables:
            if type(sibling) is not dict:
                continue
            columns = sibling.get("columns")
            if type(columns) is not list or not _value_column_ordinals(
                columns, compiled_specs=compiled_specs
            ):
                # A percentage/rate/text sibling cannot own an accounting
                # MONEY population and therefore must not prevent the section
                # heading from scoping the sole accounting table.
                continue
            title_control = any(
                not exclusion.get("unless_declared_roles")
                and _typed_control_surface_matches(exclusion, section=section, table=sibling)
                for exclusion in compiled_specs["typed_control_exclusions"]
            )
            if not title_control:
                noncontrol_tables.append(sibling)
        section_title_scopes_table = bool(
            len(noncontrol_tables) == 1 and noncontrol_tables[0] is table
        )
    if section_title_scopes_table:
        context_surfaces.append(section.get("title_exact"))
    context_surfaces.extend(
        _sole_titleless_money_table_narratives(
            section, table, compiled_specs=compiled_specs
        )
    )
    ordered_narrative_context = _ordered_titleless_money_table_narrative_context(
        section, table, compiled_specs=compiled_specs
    )
    if ordered_narrative_context is not None:
        context_surfaces.append(ordered_narrative_context["source_exact"])
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


def _project_exact_compound_source_rows(
    table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> tuple[list[Any], list[dict[str, Any]]]:
    """Split an exact line-aligned source row into declared logical rows.

    Gemini occasionally preserves a printed two-line disclosure as one row:
    two labels separated by a newline and, in every value cell, two values in
    the same order. This is source structure rather than arithmetic. Split
    only when all axes have the same bounded cardinality and every projected
    label resolves to one distinct declared non-structural role. Wrapped
    prose, partial cells, duplicate roles, or ambiguity stays raw and reaches
    the ordinary fail-closed path.
    """

    raw_rows = table.get("rows")
    if type(raw_rows) is not list:
        return [], []
    output: list[Any] = []
    receipts: list[dict[str, Any]] = []
    for source_row_ordinal, raw_row in enumerate(raw_rows, start=1):
        if (
            type(raw_row) is not dict
            or raw_row.get("row_kind") != "ITEM"
            or type(raw_row.get("label_exact")) is not str
            or type(raw_row.get("values_exact")) is not list
        ):
            output.append(raw_row)
            continue
        label_lines = [line.strip() for line in raw_row["label_exact"].splitlines() if line.strip()]
        if not 2 <= len(label_lines) <= 4:
            output.append(raw_row)
            continue
        value_lines: list[list[str]] = []
        for value in raw_row["values_exact"]:
            if type(value) is not str:
                value_lines = []
                break
            lines = [line.strip() for line in value.splitlines() if line.strip()]
            if len(lines) != len(label_lines):
                value_lines = []
                break
            value_lines.append(lines)
        if not value_lines:
            output.append(raw_row)
            continue
        path = raw_row.get("hierarchy_path_exact")
        parent_path = list(path) if type(path) is list else []
        if parent_path and type(parent_path[-1]) is str:
            label_line_axis = {_normalized(line) for line in label_lines}
            trailing_path_lines = [
                line.strip() for line in parent_path[-1].splitlines() if line.strip()
            ]
            retained_trailing_lines = [
                line for line in trailing_path_lines if _normalized(line) not in label_line_axis
            ]
            if len(retained_trailing_lines) != len(trailing_path_lines):
                parent_path = parent_path[:-1]
                if retained_trailing_lines:
                    parent_path.append("\n".join(retained_trailing_lines))
            elif _normalized(parent_path[-1]) == _normalized(raw_row["label_exact"]):
                parent_path = parent_path[:-1]
        projected_rows = []
        projected_roles = []
        for subrow_ordinal, label in enumerate(label_lines, start=1):
            projected = canonical_clone_v1(raw_row)
            projected["label_exact"] = label
            projected["hierarchy_path_exact"] = [*parent_path, label]
            projected["values_exact"] = [lines[subrow_ordinal - 1] for lines in value_lines]
            try:
                modes = _row_role_match_modes(
                    projected,
                    topology=compiled_specs["topology"],
                    aliases_by_role=compiled_specs["aliases_by_role"],
                    fallback_within_role=None,
                    enable_declared_equivalences=True,
                )
            except ValueError:
                modes = {}
            roles = [role for role in modes if role in compiled_specs["child_by_role"]]
            if (
                len(roles) != 1
                or compiled_specs["child_by_role"][roles[0]]["role_kind"] == "STRUCTURAL_GROUP"
            ):
                projected_rows = []
                break
            projected_rows.append(projected)
            projected_roles.append(roles[0])
        if not projected_rows or len(projected_roles) != len(set(projected_roles)):
            output.append(raw_row)
            continue
        first_projected_ordinal = len(output) + 1
        material = {
            "projected_roles": projected_roles,
            "projected_row_ordinals": list(
                range(first_projected_ordinal, first_projected_ordinal + len(projected_rows))
            ),
            "rule": (
                "EXACT_LINE_ALIGNED_LABEL_AND_EVERY_VALUE_CELL_PROJECT_TO_DISTINCT_"
                "DECLARED_NONSTRUCTURAL_ROLES"
            ),
            "source_hierarchy_path_exact": canonical_clone_v1(raw_row.get("hierarchy_path_exact")),
            "source_label_exact": raw_row["label_exact"],
            "source_row_ordinal": source_row_ordinal,
            "source_values_exact": canonical_clone_v1(raw_row["values_exact"]),
        }
        projection_id = "gjmthfcv1:compound-row:" + canonical_json_sha256_v1(material)
        receipts.append({**material, "projection_id": projection_id})
        for subrow_ordinal, projected in enumerate(projected_rows, start=1):
            projected["_compound_row_projection"] = {
                "projection_id": projection_id,
                "projected_role": projected_roles[subrow_ordinal - 1],
                "source_row_ordinal": source_row_ordinal,
                "subrow_ordinal": subrow_ordinal,
            }
            output.append(projected)
    return output, receipts


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
    rows, compound_row_projection_receipts = _project_exact_compound_source_rows(
        table, compiled_specs=compiled_specs
    )
    if type(columns) is not list or type(rows) is not list:
        raise _error("multi-table hierarchical source axes are invalid")
    money_ordinals = _value_column_ordinals(columns, compiled_specs=compiled_specs)
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
    hierarchy_path_scope_resolutions = []
    ordered_root_scope_resolutions = []
    owner_summary_structural_role_resolutions = []
    row_population_context_suppressions = []
    unscoped_shared_child_rows = []
    unbound_money_rows = []
    total_rows = []
    family_root_row_ordinals = []
    primary_statement_source_result_candidates = []
    primary_statement_family_root_group_ordinals = []
    heading_context_roles = _context_roles(section, table, compiled_specs=compiled_specs)
    # Re-evaluate with an artificial sibling so only the table title can
    # contribute.  This preserves whether a role came from an explicit local
    # title or was inferred from the row population/sole-table section title.
    table_title_context_roles = _context_roles(
        {"tables": [table, {}]}, table, compiled_specs=compiled_specs
    )
    fallback_within_role = heading_context_roles[0] if len(heading_context_roles) == 1 else None

    def unique_declared_parent_chain(role: str) -> set[str]:
        chain = {role}
        current = role
        while True:
            parents = {
                matcher["within_role"]
                for matcher in compiled_specs["matchers_by_role"].get(current, [])
                if matcher["within_role"] is not None
            }
            if len(parents) != 1:
                return chain
            current = next(iter(parents))
            if current in chain:
                return chain
            chain.add(current)

    def declared_under(role: str, ancestor: str) -> bool:
        pending = [role]
        seen = set()
        while pending:
            current = pending.pop()
            if current == ancestor:
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

    for row_ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict or type(row.get("values_exact")) is not list:
            continue
        values = row["values_exact"]
        visible = any(
            ordinal <= len(values) and values[ordinal - 1] is not None for ordinal in money_ordinals
        )
        root_label = _without_leading_ordinal(_normalized(row.get("label_exact")))
        primary_balance_sheet = bool(
            page_json.get("status") == "PRIMARY_FINANCIAL_STATEMENT"
            and section.get("content_kind") == "PRIMARY_STATEMENT"
            and section.get("statement_type") == "BALANCE_SHEET"
        )
        if (
            (
                "owner_surface_kinds" in compiled_specs["query_policy"]
                or (
                    primary_balance_sheet
                    and compiled_specs.get(
                        "primary_statement_source_result_fallback_policy", "DISABLED"
                    )
                    != "DISABLED"
                )
            )
            and root_label in set(compiled_specs["topology"]["parent"]["aliases"])
        ):
            if (
                primary_balance_sheet
                and compiled_specs.get(
                    "primary_statement_source_result_fallback_policy", "DISABLED"
                )
                == "UNIQUE_SHALLOWEST_STRUCTURAL_EXACT_VISIBLE_ROOT_WHEN_NOTE_NOT_OBSERVED"
                and visible
            ):
                path = row.get("hierarchy_path_exact")
                primary_statement_source_result_candidates.append(
                    {
                        "hierarchy_depth": (
                            len([value for value in path if _normalized(value)])
                            if type(path) is list
                            else 0
                        ),
                        "row_kind": row.get("row_kind"),
                        "row_ordinal": row_ordinal,
                    }
                )
            elif section.get("statement_type") != "CASH_FLOW":
                family_root_row_ordinals.append(row_ordinal)
            elif (
                compiled_specs["primary_statement_family_root_subtree_policy"]
                == ("EXACT_PARENT_GROUP_UNDER_VISIBLE_TOTAL_WITH_COMPLETE_DECLARED_CHILD_FRONTIER")
                and page_json.get("status") == "PRIMARY_FINANCIAL_STATEMENT"
                and section.get("content_kind") == "PRIMARY_STATEMENT"
                and row.get("row_kind") in {"GROUP", "ITEM", "SUBTOTAL"}
                and all(value is None for value in values)
            ):
                primary_statement_family_root_group_ordinals.append(row_ordinal)
        match_cache: dict[str | None, dict[str, str]] = {}
        direct_disclosure_scope_role: str | None = None

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
                    label = _without_leading_ordinal(_normalized(source_row.get("label_exact")))
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
        source_only_detail_context = bool(
            not explicit_path_roles
            and fallback_within_role
            in compiled_specs.get("source_only_detail_context_roles", [])
        )
        try:
            # A source-visible hierarchy path is stronger than a broad table
            # title.  Starting with the title fallback can make one generic
            # child label (for example ``Bằng VND``) simultaneously claim the
            # title branch and its exact path branch, which then degrades to
            # an unbound row.  Resolve the row from its own path first; use
            # table context only when no path scope exists.
            modes = match_with_fallback(row, None if explicit_path_roles else fallback_within_role)
            if (
                not modes
                and not explicit_path_roles
                and fallback_within_role is not None
                and not source_only_detail_context
            ):
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
            if not source_only_detail_context and modes and all(
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
                nearest_structural = None
                label_has_disclosure_prefix = False
                candidate_scopes = set(
                    explicit_path_roles
                    or (
                        {fallback_within_role}
                        if source_only_detail_context
                        else {
                            *compiled_specs["table_context_roles"],
                            *compiled_specs["detail_context_roles"],
                        }
                    )
                )
                if explicit_path_roles:
                    candidate_scopes.update(
                        ancestor
                        for path_role in explicit_path_roles
                        for ancestor in unique_declared_parent_chain(path_role)
                    )
                if (
                    compiled_specs["query_policy"].get("hierarchy_role_scope_policy")
                    == "PATH_DECLARED_ROLES_FIRST"
                ):
                    preceding_structural = [
                        hit
                        for hit in role_hits
                        if hit["row_ordinal"] < row_ordinal
                        and compiled_specs["child_by_role"][hit["role"]]["role_kind"]
                        == "STRUCTURAL_GROUP"
                    ]
                    nearest_structural = (
                        max(preceding_structural, key=lambda hit: hit["row_ordinal"])
                        if preceding_structural
                        else None
                    )
                    wrapper_tokens = {"trong do", "bao gom", "of which", "including"}
                    normalized_label = _normalized(row.get("label_exact"))
                    label_has_disclosure_prefix = any(
                        normalized_label == token or normalized_label.startswith(token + " ")
                        for token in wrapper_tokens
                    )
                    path_has_wrapper = any(
                        _normalized(value) in wrapper_tokens
                        for value in (row.get("hierarchy_path_exact") or [])[:-1]
                    )
                    intervening_wrappers = [
                        ordinal
                        for ordinal in range(
                            (
                                1
                                if nearest_structural is None
                                else nearest_structural["row_ordinal"] + 1
                            ),
                            row_ordinal,
                        )
                        if type(rows[ordinal - 1]) is dict
                        and rows[ordinal - 1].get("row_kind") == "GROUP"
                        and _normalized(rows[ordinal - 1].get("label_exact")) in wrapper_tokens
                        and type(rows[ordinal - 1].get("values_exact")) is list
                        and all(value is None for value in rows[ordinal - 1]["values_exact"])
                    ]
                    if nearest_structural is not None and (
                        label_has_disclosure_prefix
                        or path_has_wrapper
                        or len(intervening_wrappers) == 1
                    ):
                        candidate_scopes.add(nearest_structural["role"])
                        if label_has_disclosure_prefix:
                            direct_disclosure_scope_role = nearest_structural["role"]
                scoped_modes_by_scope = {
                    scope: match_with_fallback(row, scope) for scope in candidate_scopes
                }
                scoped_modes = list(scoped_modes_by_scope.values())
                modes = {
                    role: mode for candidate in scoped_modes for role, mode in candidate.items()
                }
                if (
                    not modes
                    and nearest_structural is not None
                    and label_has_disclosure_prefix
                    and (
                        not explicit_path_roles
                        or all(
                            declared_under(nearest_structural["role"], path_role)
                            for path_role in explicit_path_roles
                        )
                    )
                ):
                    # The generic hierarchical matcher correctly refuses to
                    # apply a fallback scope when any explicit path is
                    # present. A direct ``Trong do / Of which`` row is the
                    # narrow exception: the nearest preceding structural
                    # carrier may refine a broader explicit path, provided
                    # the exact post-prefix label resolves to one of its
                    # declared direct children. This never relaxes matching
                    # for unrelated or value-selected scopes.
                    direct_modes = {
                        role: "EXACT_NEAREST_STRUCTURAL_DISCLOSURE_CHILD"
                        for role, matchers in compiled_specs["matchers_by_role"].items()
                        if any(
                            matcher["within_role"] == nearest_structural["role"]
                            and any(
                                _matches(row.get("label_exact"), alias)
                                for alias in matcher["aliases"]
                            )
                            for matcher in matchers
                        )
                    }
                    if len(direct_modes) == 1:
                        modes = direct_modes
                        direct_disclosure_scope_role = nearest_structural["role"]
                resolved_parent_scopes = sorted(
                    scope
                    for scope, candidate in scoped_modes_by_scope.items()
                    if scope not in explicit_path_roles and set(candidate) == set(modes)
                )
                if explicit_path_roles and len(modes) == 1 and resolved_parent_scopes:
                    hierarchy_path_scope_resolutions.append(
                        {
                            "candidate_roles": sorted(modes),
                            "path_declared_scope_roles": sorted(explicit_path_roles),
                            "resolved_parent_scope_roles": resolved_parent_scopes,
                            "resolved_role": next(iter(modes)),
                            "row_ordinal": row_ordinal,
                            "rule": (
                                "EXACT_HIERARCHY_PATH_DECLARED_PARENT_CHAIN_SCOPES_CHILD"
                            ),
                        }
                    )
        except ValueError:
            modes = {"AMBIGUOUS": "AMBIGUOUS"}
        matched = sorted(role for role in modes if role in compiled_specs["child_by_role"])
        if (
            direct_disclosure_scope_role is not None
            and len(matched) == 1
            and any(
                matcher["within_role"] == direct_disclosure_scope_role
                for matcher in compiled_specs["matchers_by_role"][matched[0]]
            )
        ):
            hierarchy_path_scope_resolutions.append(
                {
                    "resolved_role": matched[0],
                    "row_ordinal": row_ordinal,
                    "structural_ancestor_role": direct_disclosure_scope_role,
                    "rule": (
                        "NEAREST_PRECEDING_DECLARED_STRUCTURAL_ROLE_PLUS_EXACT_"
                        "DISCLOSURE_PREFIX_SCOPES_CHILD"
                    ),
                }
            )
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
        if (
            len(matched) > 1
            and compiled_specs["query_policy"].get("hierarchy_role_scope_policy")
            == "PATH_DECLARED_ROLES_FIRST"
        ):
            path_declared_scopes = {
                ancestor
                for path_role in explicit_path_roles
                for ancestor in unique_declared_parent_chain(path_role)
            }
            scoped = [
                role
                for role in matched
                if any(declared_under(role, ancestor) for ancestor in path_declared_scopes)
            ]
            if len(scoped) == 1:
                hierarchy_path_scope_resolutions.append(
                    {
                        "candidate_roles": sorted(matched),
                        "path_declared_scope_roles": sorted(path_declared_scopes),
                        "resolved_role": scoped[0],
                        "row_ordinal": row_ordinal,
                        "rule": "EXACT_HIERARCHY_PATH_DECLARED_PARENT_CHAIN_SCOPES_CHILD",
                    }
                )
                matched = scoped
        if (
            len(matched) > 1
            and compiled_specs["query_policy"].get("hierarchy_role_scope_policy")
            == "PATH_DECLARED_ROLES_FIRST"
        ):
            preceding_structural_roles = [
                hit
                for hit in role_hits
                if compiled_specs["child_by_role"][hit["role"]]["role_kind"] == "STRUCTURAL_GROUP"
                and hit["row_ordinal"] < row_ordinal
            ]
            nearest_structural_role = (
                max(preceding_structural_roles, key=lambda hit: hit["row_ordinal"])
                if preceding_structural_roles
                else None
            )
            path = {
                _normalized(value)
                for value in (row.get("hierarchy_path_exact") or [])[:-1]
                if _normalized(value)
            }
            transparent_wrappers = [
                ordinal
                for ordinal in range(
                    (
                        1
                        if nearest_structural_role is None
                        else nearest_structural_role["row_ordinal"] + 1
                    ),
                    row_ordinal,
                )
                if type(rows[ordinal - 1]) is dict
                and rows[ordinal - 1].get("row_kind") == "GROUP"
                and _normalized(rows[ordinal - 1].get("label_exact"))
                in {"trong do", "bao gom", "of which", "including"}
                and _normalized(rows[ordinal - 1].get("label_exact")) in path
                and type(rows[ordinal - 1].get("values_exact")) is list
                and all(value is None for value in rows[ordinal - 1]["values_exact"])
            ]
            if nearest_structural_role is not None and len(transparent_wrappers) == 1:
                scoped = [
                    role
                    for role in matched
                    if declared_under(role, nearest_structural_role["role"])
                ]
                if len(scoped) == 1:
                    hierarchy_path_scope_resolutions.append(
                        {
                            "candidate_roles": sorted(matched),
                            "resolved_role": scoped[0],
                            "row_ordinal": row_ordinal,
                            "structural_ancestor_role": nearest_structural_role["role"],
                            "transparent_wrapper_row_ordinal": transparent_wrappers[0],
                            "rule": (
                                "NEAREST_PRECEDING_DECLARED_STRUCTURAL_ROLE_PLUS_EXACT_BLANK_"
                                "DISCLOSURE_WRAPPER_SCOPES_CHILD"
                            ),
                        }
                    )
                    matched = scoped
        if (
            len(matched) > 1
            and compiled_specs["row_population_context_policy"]
            == "AT_LEAST_TWO_DECLARED_CHILD_ROLES"
        ):
            preceding_root_hits = [
                hit
                for hit in role_hits
                if hit["role"] in compiled_specs["root_component_roles"]
                and hit["row_ordinal"] < row_ordinal
                # Gemini row_kind is useful corroboration but is not the
                # authority for accounting structure. A source-visible row
                # that matched one declared STRUCTURAL_GROUP remains a valid
                # ordered carrier even when Gemini called it ITEM. The next
                # declared structural carrier closes the interval, so this
                # never scopes a child by value or document identity.
                and compiled_specs["child_by_role"][hit["role"]]["role_kind"] == "STRUCTURAL_GROUP"
            ]
            if preceding_root_hits:
                nearest = max(preceding_root_hits, key=lambda hit: hit["row_ordinal"])
                scoped = [
                    role
                    for role in matched
                    if any(
                        matcher["within_role"] == nearest["role"]
                        for matcher in compiled_specs["matchers_by_role"][role]
                    )
                ]
                if len(scoped) == 1:
                    ordered_root_scope_resolutions.append(
                        {
                            "candidate_roles": sorted(matched),
                            "preceding_root_role": nearest["role"],
                            "preceding_root_row_ordinal": nearest["row_ordinal"],
                            "resolved_role": scoped[0],
                            "row_ordinal": row_ordinal,
                            "rule": "NEAREST_PRECEDING_VISIBLE_STRUCTURAL_ROOT_SCOPES_CHILD",
                        }
                    )
                    matched = scoped
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
    ordered_role_scope_receipts = []
    outside_ordered_role_scope_rows = []
    resolved_scope_intervals: list[dict[str, Any]] = []
    resolved_terminal_hits_by_role: dict[str, dict[str, Any]] = {}
    for scope in compiled_specs["ordered_role_scopes"]:
        start_hits = [
            resolved_terminal_hits_by_role[role]
            for role in scope["start_after_roles"]
            if role in resolved_terminal_hits_by_role
        ]
        if scope["start_after_roles"] and not start_hits:
            start_hits = [hit for hit in role_hits if hit["role"] in scope["start_after_roles"]]
        if scope["start_after_roles"] and len(start_hits) != 1:
            ordered_role_scope_receipts.append(
                {
                    "scope_id": scope["scope_id"],
                    "start_row_ordinal": None,
                    "status": "START_ROLE_NOT_UNIQUE_SCOPE_NOT_APPLIED",
                    "terminal_row_ordinal": None,
                }
            )
            continue
        start_ordinal = start_hits[0]["row_ordinal"] if start_hits else 0
        terminal_hits = [
            hit
            for hit in role_hits
            if hit["role"] in scope["terminal_roles"] and hit["row_ordinal"] > start_ordinal
        ]
        if not terminal_hits:
            ordered_role_scope_receipts.append(
                {
                    "scope_id": scope["scope_id"],
                    "start_row_ordinal": start_ordinal,
                    "status": "TERMINAL_ROLE_NOT_VISIBLE_SCOPE_NOT_APPLIED",
                    "terminal_row_ordinal": None,
                }
            )
            continue
        terminal_hit = min(terminal_hits, key=lambda hit: hit["row_ordinal"])
        terminal_ordinal = terminal_hit["row_ordinal"]
        out_of_interval_hits = [
            hit
            for hit in role_hits
            if hit["role"] in scope["scoped_roles"]
            and not start_ordinal < hit["row_ordinal"] <= terminal_ordinal
        ]
        resolved_scope_intervals.append(
            {
                "scope_id": scope["scope_id"],
                "scoped_roles": set(scope["scoped_roles"]),
                "start_row_ordinal": start_ordinal,
                "terminal_row_ordinal": terminal_ordinal,
            }
        )
        resolved_terminal_hits_by_role[terminal_hit["role"]] = terminal_hit
        ordered_role_scope_receipts.append(
            {
                "out_of_interval_role_hits": canonical_clone_v1(out_of_interval_hits),
                "scope_id": scope["scope_id"],
                "start_row_ordinal": start_ordinal,
                "status": "UNIQUE_ORDERED_ROLE_SCOPE_APPLIED",
                "terminal_row_ordinal": terminal_ordinal,
            }
        )
    retained_role_hits = []
    for hit in role_hits:
        memberships = [
            interval
            for interval in resolved_scope_intervals
            if hit["role"] in interval["scoped_roles"]
        ]
        if not memberships or any(
            interval["start_row_ordinal"] < hit["row_ordinal"] <= interval["terminal_row_ordinal"]
            for interval in memberships
        ):
            retained_role_hits.append(hit)
            continue
        outside_ordered_role_scope_rows.append(
            {
                "original_role": hit["role"],
                "row_ordinal": hit["row_ordinal"],
                "scope_ids": sorted(interval["scope_id"] for interval in memberships),
                "rule": "DECLARED_ROLE_OUTSIDE_ALL_ORDERED_SOURCE_STAGES_RETAINED_SOURCE_ONLY",
            }
        )
        if hit["row_ordinal"] not in unbound_money_rows:
            unbound_money_rows.append(hit["row_ordinal"])
    role_hits = retained_role_hits
    if (
        compiled_specs.get("owner_summary_structural_role_policy", "DISABLED")
        == "OWNER_TABLE_ROOT_SIBLING_FRONTIER_PREFERS_STRUCTURAL_ROLE"
        and _owner_visible(section, table, compiled_specs=compiled_specs)
        and total_rows
    ):
        visible_ordinals = {
            ordinal
            for ordinal, source_row in enumerate(rows, start=1)
            if type(source_row) is dict
            and type(source_row.get("values_exact")) is list
            and any(
                column_ordinal <= len(source_row["values_exact"])
                and source_row["values_exact"][column_ordinal - 1] is not None
                for column_ordinal in money_ordinals
            )
        }
        terminal_total = max(
            (item["row_ordinal"] for item in total_rows), default=None
        )
        if visible_ordinals and terminal_total == max(visible_ordinals):
            rewritten_hits = []
            for hit in role_hits:
                row = rows[hit["row_ordinal"] - 1]
                structural_candidates = [
                    role
                    for role in compiled_specs["root_component_roles"]
                    if compiled_specs["child_by_role"][role]["role_kind"]
                    == "STRUCTURAL_GROUP"
                    and any(
                        _without_leading_ordinal(_normalized(row.get("label_exact")))
                        == _normalized(alias)
                        for alias in compiled_specs["aliases_by_role"][role]
                    )
                    and any(
                        matcher["within_role"] == role
                        for matcher in compiled_specs["matchers_by_role"][hit["role"]]
                    )
                ]
                if len(structural_candidates) != 1:
                    rewritten_hits.append(hit)
                    continue
                structural_role = structural_candidates[0]
                outside_branch_hits = [
                    candidate
                    for candidate in role_hits
                    if candidate["row_ordinal"] != hit["row_ordinal"]
                    and candidate["row_ordinal"] in visible_ordinals
                    and not declared_under(candidate["role"], structural_role)
                ]
                outside_branch_frontier = [
                    candidate
                    for candidate in outside_branch_hits
                    if not any(
                        other["row_ordinal"] != candidate["row_ordinal"]
                        and _row_is_strict_descendant(
                            rows,
                            candidate["row_ordinal"],
                            other["row_ordinal"],
                        )
                        for other in outside_branch_hits
                    )
                ]
                if len(
                    {candidate["row_ordinal"] for candidate in outside_branch_frontier}
                ) < 2:
                    rewritten_hits.append(hit)
                    continue
                rewritten = {**hit, "role": structural_role}
                rewritten_hits.append(rewritten)
                matched_scopes_by_hit[(hit["row_ordinal"], structural_role)] = set()
                owner_summary_structural_role_resolutions.append(
                    {
                        "original_role": hit["role"],
                        "outside_branch_frontier": [
                            {
                                "role": candidate["role"],
                                "row_ordinal": candidate["row_ordinal"],
                            }
                            for candidate in outside_branch_frontier
                        ],
                        "resolved_role": structural_role,
                        "row_ordinal": hit["row_ordinal"],
                        "terminal_total_row_ordinal": terminal_total,
                        "rule": (
                            "EXACT_OWNER_SUMMARY_ROOT_LABEL_PLUS_MULTIPLE_VISIBLE_OUTSIDE_"
                            "BRANCH_FRONTIER_ROWS_PREFERS_STRUCTURAL_ROLE"
                        ),
                    }
                )
            role_hits = rewritten_hits
    primary_statement_source_result_receipt = None
    if primary_statement_source_result_candidates:
        minimum_depth = min(
            item["hierarchy_depth"] for item in primary_statement_source_result_candidates
        )
        shallowest = [
            item
            for item in primary_statement_source_result_candidates
            if item["hierarchy_depth"] == minimum_depth
        ]
        selected_primary_candidates = shallowest
        selection_rule = "UNIQUE_SHALLOWEST_EXACT_VISIBLE_FAMILY_ROOT"
        if len(shallowest) > 1:
            structural = [
                item
                for item in shallowest
                if item["row_kind"] in {"GROUP", "SUBTOTAL", "TOTAL"}
            ]
            if len(structural) == 1:
                selected_primary_candidates = structural
                selection_rule = (
                    "UNIQUE_STRUCTURAL_ROOT_AMONG_SHALLOWEST_EXACT_VISIBLE_FAMILY_ROOTS"
                )
        if len(selected_primary_candidates) == 1:
            selected_primary = selected_primary_candidates[0]
            selected_ordinal = selected_primary["row_ordinal"]
            family_root_row_ordinals.append(selected_ordinal)
            candidate_ordinals = {
                item["row_ordinal"]
                for item in primary_statement_source_result_candidates
            }
            role_hits = [
                hit for hit in role_hits if hit["row_ordinal"] not in candidate_ordinals
            ]
            ambiguous_rows = [
                item
                for item in ambiguous_rows
                if item["row_ordinal"] not in candidate_ordinals
            ]
            unbound_money_rows = [
                ordinal
                for ordinal in unbound_money_rows
                if ordinal not in candidate_ordinals
            ]
            primary_statement_source_result_receipt = {
                "candidate_row_ordinals": sorted(
                    item["row_ordinal"]
                    for item in primary_statement_source_result_candidates
                ),
                "hierarchy_depth": selected_primary["hierarchy_depth"],
                "row_kind": selected_primary["row_kind"],
                "source_result_row_ordinal": selected_ordinal,
                "rule": selection_rule,
            }

    primary_statement_family_root_subtree_receipts = []
    for group_ordinal in primary_statement_family_root_group_ordinals:
        descendant_hits = [
            hit
            for hit in role_hits
            if _row_is_strict_descendant(rows, hit["row_ordinal"], group_ordinal)
        ]
        descendant_roles = {hit["role"] for hit in descendant_hits}
        if len(
            descendant_roles.intersection(compiled_specs["root_component_roles"])
        ) < compiled_specs["evaluation"].get(
            "minimum_source_visible_root_component_count", 2
        ) or not any(
            set(combination) <= descendant_roles
            for combination in compiled_specs["topology"]["required_role_combinations"]
        ):
            continue
        ancestor_totals = []
        for candidate_ordinal in range(1, group_ordinal):
            candidate = rows[candidate_ordinal - 1]
            if (
                type(candidate) is not dict
                or candidate.get("row_kind") not in {"GROUP", "ITEM", "SUBTOTAL", "TOTAL"}
                or not _row_is_strict_descendant(rows, group_ordinal, candidate_ordinal)
            ):
                continue
            if any(
                candidate_ordinal < intermediate_ordinal < group_ordinal
                and type(rows[intermediate_ordinal - 1]) is dict
                and _row_is_strict_descendant(rows, group_ordinal, intermediate_ordinal)
                and _row_is_strict_descendant(rows, intermediate_ordinal, candidate_ordinal)
                for intermediate_ordinal in range(candidate_ordinal + 1, group_ordinal)
            ):
                continue
            candidate_values = candidate.get("values_exact")
            if type(candidate_values) is not list or not any(
                ordinal <= len(candidate_values) and candidate_values[ordinal - 1] is not None
                for ordinal in money_ordinals
            ):
                continue
            ancestor_totals.append(candidate_ordinal)
        if len(ancestor_totals) != 1:
            continue
        result_ordinal = ancestor_totals[0]
        family_root_row_ordinals.append(result_ordinal)
        primary_statement_family_root_subtree_receipts.append(
            {
                "declared_child_roles": sorted(descendant_roles),
                "declared_child_row_ordinals": sorted(
                    hit["row_ordinal"] for hit in descendant_hits
                ),
                "family_group_row_ordinal": group_ordinal,
                "source_result_row_ordinal": result_ordinal,
                "rule": (
                    "EXACT_PARENT_GROUP_DIRECTLY_UNDER_VISIBLE_SOURCE_TOTAL_WITH_"
                    "COMPLETE_DECLARED_CHILD_FRONTIER"
                ),
            }
        )
    family_root_row_ordinals = sorted(set(family_root_row_ordinals))
    declared_within_roles = {
        scope
        for hit in role_hits
        for scope in matched_scopes_by_hit[(hit["row_ordinal"], hit["role"])]
    }
    explicit_anchored_within_roles = {
        scope
        for hit in role_hits
        if hit["role"] in compiled_specs["presence_anchor_roles"]
        for scope in matched_scopes_by_hit[(hit["row_ordinal"], hit["role"])]
        if any(
            matcher["within_role"] == scope and matcher["presence_anchor"]
            for matcher in compiled_specs["matchers_by_role"][hit["role"]]
        )
    }
    anchored_within_roles = (
        explicit_anchored_within_roles
        if compiled_specs["row_population_context_policy"]
        == "ONE_ANCHORED_OR_TWO_DECLARED_CHILD_ROLES"
        else set()
    )
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
        and len(explicit_anchored_within_roles) == 1
        and set(heading_context_roles) != explicit_anchored_within_roles
    ):
        # A continuation section heading can repeat the outer note while the
        # sole table is an explicitly anchored inner analysis.  The row
        # population is the stronger table-local context in that case.
        context_roles = sorted(explicit_anchored_within_roles)
    elif len(heading_context_roles) == 1:
        context_roles = heading_context_roles
    elif len(anchored_within_roles) == 1:
        context_roles = sorted(anchored_within_roles)
    elif len(declared_within_roles) == 1 and len({hit["role"] for hit in role_hits}) >= 2:
        context_roles = sorted(declared_within_roles)
    else:
        context_roles = heading_context_roles
    sole_narrative_context_surfaces = _sole_titleless_money_table_narratives(
        section, table, compiled_specs=compiled_specs
    )
    ordered_narrative_context = _ordered_titleless_money_table_narrative_context(
        section, table, compiled_specs=compiled_specs
    )
    narrative_context_surfaces = [
        *sole_narrative_context_surfaces,
        *(
            [ordered_narrative_context["source_exact"]]
            if ordered_narrative_context is not None
            else []
        ),
    ]
    narrative_context_roles = {
        role
        for role in context_roles
        if any(
            _contains_alias(surface, alias)
            for surface in narrative_context_surfaces
            for alias in compiled_specs["aliases_by_role"][role]
        )
    }
    if context_roles and context_roles == table_title_context_roles:
        context_resolution_kind = "EXPLICIT_TABLE_TITLE"
    elif (
        context_roles
        and ordered_narrative_context is not None
        and context_roles == [ordered_narrative_context["role"]]
    ):
        context_resolution_kind = "EXPLICIT_TITLELESS_ORDERED_TABLE_SECTION_NARRATIVE"
    elif context_roles and set(context_roles) == narrative_context_roles:
        context_resolution_kind = "EXPLICIT_TITLELESS_SOLE_TABLE_SECTION_NARRATIVE"
    elif context_roles and context_roles == heading_context_roles:
        context_resolution_kind = "EXPLICIT_SOLE_TABLE_SECTION_TITLE"
    elif context_roles:
        context_resolution_kind = "DECLARED_ROW_POPULATION_SCOPE"
    else:
        context_resolution_kind = "NO_CONTEXT_ROLE"
    suppressed_context_roles = set(context_roles).intersection(
        compiled_specs.get("row_population_context_roles_requiring_explicit_heading", [])
    )
    explicit_path_context_roles = {
        role
        for role in suppressed_context_roles
        if any(
            _path_has_role(
                row.get("hierarchy_path_exact"),
                aliases=compiled_specs["aliases_by_role"][role],
                label_exact=row.get("label_exact"),
            )
            for row in rows
            if type(row) is dict
        )
    }
    if (
        suppressed_context_roles
        and context_resolution_kind == "DECLARED_ROW_POPULATION_SCOPE"
        and not explicit_path_context_roles
    ):
        suppressed_row_ordinals = []
        retained_role_hits = []
        for hit in role_hits:
            if hit["role"] in suppressed_context_roles or any(
                matcher["within_role"] in suppressed_context_roles
                for matcher in compiled_specs["matchers_by_role"][hit["role"]]
            ):
                suppressed_row_ordinals.append(hit["row_ordinal"])
                if hit["row_ordinal"] not in unbound_money_rows:
                    unbound_money_rows.append(hit["row_ordinal"])
            else:
                retained_role_hits.append(hit)
        role_hits = retained_role_hits
        context_roles = [
            role for role in context_roles if role not in suppressed_context_roles
        ]
        context_resolution_kind = "NO_CONTEXT_ROLE"
        row_population_context_suppressions.append(
            {
                "context_roles": sorted(suppressed_context_roles),
                "row_ordinals": sorted(set(suppressed_row_ordinals)),
                "rule": (
                    "ROW_POPULATION_CONTEXT_REQUIRES_EXPLICIT_HEADING_OR_HIERARCHY_PATH"
                ),
            }
        )
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
    typed_control_disposition, typed_control_override_receipts = _typed_control_disposition(
        page_json,
        section,
        table,
        compiled_specs=compiled_specs,
        declared_roles=sorted(
            {
                *context_roles,
                *(hit["role"] for hit in role_hits),
                *(hit["role"] for hit in transposed_row_role_hits),
            }
        ),
    )
    if (
        typed_control_disposition == "PRIMARY_FINANCIAL_STATEMENT_SUMMARY"
        and primary_statement_family_root_subtree_receipts
    ):
        typed_control_override_receipts.append(
            {
                "control_disposition": typed_control_disposition,
                "family_root_subtree_receipts": canonical_clone_v1(
                    primary_statement_family_root_subtree_receipts
                ),
                "rule": (
                    "PRIMARY_STATEMENT_CONTROL_OVERRIDDEN_ONLY_BY_EXACT_VISIBLE_RESULT_"
                    "AND_COMPLETE_DECLARED_FAMILY_SUBTREE"
                ),
            }
        )
        typed_control_disposition = None
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
    if typed_control_override_receipts:
        material["typed_control_override_receipts"] = typed_control_override_receipts
    if compound_row_projection_receipts:
        material["compound_row_projection_receipts"] = compound_row_projection_receipts
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
    if (
        "owner_surface_kinds" in compiled_specs["query_policy"]
        or compiled_specs.get(
            "primary_statement_source_result_fallback_policy", "DISABLED"
        )
        != "DISABLED"
    ):
        material["family_root_row_ordinals"] = family_root_row_ordinals
    if primary_statement_family_root_subtree_receipts:
        material["primary_statement_family_root_subtree_receipts"] = (
            primary_statement_family_root_subtree_receipts
        )
    if primary_statement_source_result_candidates:
        material["primary_statement_source_result_candidates"] = (
            primary_statement_source_result_candidates
        )
    if primary_statement_source_result_receipt is not None:
        material["primary_statement_source_result_receipt"] = (
            primary_statement_source_result_receipt
        )
    if ordered_narrative_context is not None:
        material["ordered_titleless_narrative_context_receipt"] = (
            ordered_narrative_context
        )
    if compiled_specs["row_population_context_policy"] == "AT_LEAST_TWO_DECLARED_CHILD_ROLES":
        material["ordered_root_scope_resolutions"] = ordered_root_scope_resolutions
    if hierarchy_path_scope_resolutions:
        material["hierarchy_path_scope_resolutions"] = hierarchy_path_scope_resolutions
    if owner_summary_structural_role_resolutions:
        material["owner_summary_structural_role_resolutions"] = (
            owner_summary_structural_role_resolutions
        )
    if row_population_context_suppressions:
        material["row_population_context_suppressions"] = (
            row_population_context_suppressions
        )
    if compiled_specs["ordered_role_scopes"]:
        material["ordered_role_scope_receipts"] = ordered_role_scope_receipts
        material["outside_ordered_role_scope_rows"] = outside_ordered_role_scope_rows
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


def _explicit_continuation_leading_scope_classification_v1(
    *,
    prior_classification: Mapping[str, Any],
    current_classification: Mapping[str, Any],
    current_table: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Resolve only a receiver's leading child suffix under one prior carrier.

    The exact continuation markers and adjacency are checked by both callers.
    Here, source order supplies the remaining boundary: one prior declared root
    carrier may govern only the consecutive leading receiver rows before the
    next declared root carrier/result.  An ambiguous leading alias is resolved
    only when exactly one of its declared roles descends from that carrier.
    """

    output = canonical_clone_v1(current_classification)
    rows = current_table.get("rows")
    if (
        compiled_specs.get("continuation_leading_child_scope_policy", "DISABLED")
        != "EXACT_PRIOR_ROOT_CARRIER_SCOPES_CONSECUTIVE_RECEIVER_PREFIX"
        or type(rows) is not list
    ):
        return output, None
    configured_root_roles = {
        role
        for declaration in compiled_specs.get("root_component_role_combinations", [])
        for role in declaration["roles"]
    } or set(compiled_specs["root_component_roles"])
    prior_root_roles = configured_root_roles.intersection(
        _classification_roles(prior_classification)
    )
    if len(prior_root_roles) != 1:
        return output, None
    carrier_role = next(iter(prior_root_roles))

    def declared_under(role: str, ancestor: str) -> bool:
        pending = [role]
        seen = set()
        while pending:
            current = pending.pop()
            if current == ancestor:
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

    hit_by_ordinal = {
        hit["row_ordinal"]: hit for hit in output.get("role_hits", [])
    }
    ambiguous_by_ordinal = {
        item["row_ordinal"]: item for item in output.get("ambiguous_rows", [])
    }
    boundary_ordinals = [
        ordinal
        for ordinal, hit in hit_by_ordinal.items()
        if hit["role"] in configured_root_roles and hit["role"] != carrier_role
    ]
    boundary_ordinals.extend(output.get("family_root_row_ordinals", []))
    boundary_ordinal = min(boundary_ordinals, default=len(rows) + 1)
    leading_ordinals = sorted(
        ordinal
        for ordinal in {*hit_by_ordinal, *ambiguous_by_ordinal}
        if ordinal < boundary_ordinal
    )
    if not leading_ordinals or leading_ordinals[0] != 1:
        return output, None
    if set(range(1, leading_ordinals[-1] + 1)) != set(leading_ordinals):
        return output, None
    resolved = []
    for ordinal in leading_ordinals:
        if ordinal in hit_by_ordinal:
            role = hit_by_ordinal[ordinal]["role"]
            if role == carrier_role or not declared_under(role, carrier_role):
                return canonical_clone_v1(current_classification), None
            continue
        ambiguous = ambiguous_by_ordinal[ordinal]
        compatible_roles = [
            role
            for role in ambiguous["matched_roles"]
            if role != carrier_role and declared_under(role, carrier_role)
        ]
        if len(compatible_roles) != 1:
            return canonical_clone_v1(current_classification), None
        role = compatible_roles[0]
        resolved.append(
            {
                "role": role,
                "row_kind": rows[ordinal - 1].get("row_kind"),
                "row_ordinal": ordinal,
                "source_order": ordinal,
            }
        )
    if not resolved:
        return output, None
    resolved_ordinals = {hit["row_ordinal"] for hit in resolved}
    output["role_hits"] = sorted(
        [*output["role_hits"], *resolved], key=lambda hit: hit["row_ordinal"]
    )
    output["ambiguous_rows"] = [
        item
        for item in output["ambiguous_rows"]
        if item["row_ordinal"] not in resolved_ordinals
    ]
    scope_receipt = {
        "carrier_role": carrier_role,
        "leading_row_ordinals": leading_ordinals,
        "resolved_rows": canonical_clone_v1(resolved),
        "root_boundary_row_ordinal": (
            boundary_ordinal if boundary_ordinal <= len(rows) else None
        ),
        "rule": (
            "EXACT_ADJACENT_CONTINUATION_PRIOR_ROOT_CARRIER_SCOPES_ONLY_"
            "CONSECUTIVE_LEADING_RECEIVER_CHILD_SUFFIX"
        ),
    }
    output["continuation_leading_scope_receipt"] = scope_receipt
    material = {key: value for key, value in output.items() if key != "classification_id"}
    output["classification_id"] = (
        "gjmthfcv1:classification:" + canonical_json_sha256_v1(material)
    )
    return output, scope_receipt


def _coalesce_document_declared_root_components_v1(
    *,
    pages: Sequence[Mapping[str, Any]],
    table_axis: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Compose one document graph from declared component roots and result.

    Some disclosures print two independently totalled sibling populations and
    their source-visible result in separate sections.  An owner interval cannot
    represent that graph without either dropping one sibling or swallowing the
    remainder of the document.  This policy therefore inventories every MONEY
    table, selects only tables carrying a declared family role/result signal,
    and requires the complete configured root-component set plus the visible
    result.  Values never select a table; the evaluator still proves every
    local subtotal and the final equation afterwards.
    """

    root_component_role_combinations = compiled_specs.get(
        "root_component_role_combinations"
    )
    root_role_axes = (
        [set(declaration["roles"]) for declaration in root_component_role_combinations]
        if root_component_role_combinations
        else [set(compiled_specs["root_component_roles"])]
    )
    root_roles = set().union(*root_role_axes)

    def terminal_source_total_visible(item: Mapping[str, Any]) -> bool:
        classification = item["classification"]
        total_ordinals = {
            row["row_ordinal"]
            for row in classification.get("total_rows", [])
            if row.get("row_kind") == "TOTAL"
        }
        observed_ordinals = {
            hit["row_ordinal"] for hit in classification.get("role_hits", [])
        } | set(classification.get("unbound_money_row_ordinals", []))
        return bool(
            root_component_role_combinations
            and len(total_ordinals) == 1
            and observed_ordinals
            and max(observed_ordinals | total_ordinals) in total_ordinals
        )

    def declared_root_ancestors(role: str) -> set[str]:
        pending = [role]
        seen = set()
        roots = set()
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            if current in root_roles:
                roots.add(current)
            pending.extend(
                matcher["within_role"]
                for matcher in compiled_specs["matchers_by_role"].get(current, [])
                if matcher["within_role"] is not None
            )
        return roots

    def authenticated_table_roots(item: Mapping[str, Any]) -> set[str]:
        classification = item["classification"]
        return root_roles.intersection(_classification_roles(classification))

    def detailed_table_roots(item: Mapping[str, Any]) -> set[str]:
        classification = item["classification"]
        roles = _classification_roles(classification)
        table_roots = authenticated_table_roots(item)
        return {
            root
            for root in table_roots
            if len({role for role in roles - root_roles if root in declared_root_ancestors(role)})
            >= compiled_specs["minimum_declared_detail_role_count"]
        }

    def declared_signal(item: Mapping[str, Any]) -> bool:
        classification = item["classification"]
        roles = _classification_roles(classification)
        table_roots = authenticated_table_roots(item)
        # A generic child alias outside an authenticated family population is
        # not document-level family evidence.  For example, an unrelated
        # operating-expense note may contain a row labelled ``Chi khac``.  The
        # child becomes evidence only when the same table has an explicit root
        # carrier or a context resolved from at least two declared siblings.
        scoped_children = {
            role
            for role in roles - root_roles
            if declared_root_ancestors(role).intersection(table_roots)
        }
        if (
            compiled_specs["document_source_result_signal_policy"]
            == "AUTHENTICATED_ROOT_OWNER_OR_PRIMARY"
        ):
            source_result_signal = bool(
                (
                    classification.get("family_root_row_ordinals")
                    or terminal_source_total_visible(item)
                )
                and (
                    table_roots
                    or classification.get("owner_visible")
                    or classification.get("typed_control_disposition")
                    == "PRIMARY_FINANCIAL_STATEMENT_SUMMARY"
                )
            )
        else:
            source_result_signal = bool(classification.get("family_root_row_ordinals"))
        return bool(
            table_roots
            or scoped_children
            or source_result_signal
            or classification.get("ambiguous_rows")
            and table_roots
            or classification.get("typed_control_conflict_disposition")
            and table_roots
        )

    signalled_items = [item for item in table_axis if declared_signal(item)]

    def eligible_family_component(item: Mapping[str, Any]) -> bool:
        classification = item["classification"]
        disposition = classification.get("typed_control_disposition")
        return bool(
            disposition is None
            or (
                disposition == "PRIMARY_FINANCIAL_STATEMENT_SUMMARY"
                and classification.get("family_root_row_ordinals")
            )
        )

    def source_result_carrier(item: Mapping[str, Any]) -> bool:
        classification = item["classification"]
        return bool(
            (
                classification.get("typed_control_disposition")
                == "PRIMARY_FINANCIAL_STATEMENT_SUMMARY"
                and classification.get("family_root_row_ordinals")
            )
            or terminal_source_total_visible(item)
        )

    family_items = [
        item
        for item in signalled_items
        if eligible_family_component(item)
        and (detailed_table_roots(item) or source_result_carrier(item))
    ]
    roles = {
        role for item in family_items for role in _classification_roles(item["classification"])
    }
    result_visible = any(source_result_carrier(item) for item in family_items)

    detailed_roots = {root for item in family_items for root in detailed_table_roots(item)}
    complete_role_axes = [axis for axis in root_role_axes if axis <= roles]
    complete_detailed_role_axes = [axis for axis in root_role_axes if axis <= detailed_roots]
    selected_root_roles = (
        complete_role_axes[0]
        if len(complete_role_axes) == 1
        else set(compiled_specs["root_component_roles"])
    )
    missing_roots = sorted(selected_root_roles - roles)
    summary_only = bool(
        signalled_items
        and result_visible
        and not detailed_roots
        and (not missing_roots or all(source_result_carrier(item) for item in signalled_items))
    )
    reasons = []
    if signalled_items and missing_roots and not summary_only:
        reasons.append("DOCUMENT_DECLARED_ROOT_COMPONENTS_INCOMPLETE:" + ",".join(missing_roots))
    if signalled_items and not result_visible:
        reasons.append("DOCUMENT_SOURCE_VISIBLE_RESULT_NOT_OBSERVED")
    missing_detailed_roots = sorted(selected_root_roles - detailed_roots)
    if root_component_role_combinations and len(complete_role_axes) != 1:
        reasons.append(
            "DOCUMENT_DECLARED_ROOT_COMPONENT_ALTERNATIVE_"
            + ("AMBIGUOUS" if complete_role_axes else "INCOMPLETE")
        )
    if root_component_role_combinations and len(complete_detailed_role_axes) != 1:
        reasons.append(
            "DOCUMENT_DECLARED_ROOT_DETAIL_ALTERNATIVE_"
            + ("AMBIGUOUS" if complete_detailed_role_axes else "INCOMPLETE")
        )
    if signalled_items and detailed_roots and missing_detailed_roots:
        reasons.append(
            "DOCUMENT_DECLARED_ROOT_DETAIL_POPULATIONS_INCOMPLETE:"
            + ",".join(missing_detailed_roots)
        )
    for item in signalled_items:
        conflict = item["classification"].get("typed_control_conflict_disposition")
        if conflict is not None and not eligible_family_component(item):
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

    selected_keys = {
        (item["record"]["page_json_version_id"], item["section_id"], item["table_id"])
        for item in family_items
    }
    inventory = []
    for item in table_axis:
        key = (item["record"]["page_json_version_id"], item["section_id"], item["table_id"])
        classification = item["classification"]
        if key in selected_keys:
            disposition = "SELECTED_DOCUMENT_DECLARED_FAMILY_COMPONENT"
        elif classification.get("typed_control_disposition") is not None:
            disposition = "EXCLUDED_TYPED_CONTROL"
        elif key in {
            (
                candidate["record"]["page_json_version_id"],
                candidate["section_id"],
                candidate["table_id"],
            )
            for candidate in signalled_items
        }:
            disposition = "EXCLUDED_NONDETAILED_DECLARED_ROOT_POPULATION"
        else:
            disposition = "OUTSIDE_DOCUMENT_DECLARED_FAMILY_GRAPH"
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

    complete = bool(
        family_items
        and not missing_roots
        and not missing_detailed_roots
        and (not root_component_role_combinations or len(complete_role_axes) == 1)
        and (not root_component_role_combinations or len(complete_detailed_role_axes) == 1)
        and result_visible
        and not reasons
    )
    regions = (
        [_region(item, ordinal) for ordinal, item in enumerate(family_items, start=1)]
        if complete
        else []
    )
    status = (
        READY if regions else NOT_OBSERVED if summary_only or not signalled_items else UNRESOLVED
    )
    material = {
        "component_regions": regions,
        "declared_money_table_inventory": inventory,
        "document_id": pages[0]["document_id"],
        "document_ordinal": pages[0]["document_ordinal"],
        "owner_receipt": (
            None
            if not signalled_items
            else {
                "component_roles": sorted(roles),
                "detailed_root_roles": sorted(detailed_roots),
                "policy": "DOCUMENT_EXACT_DECLARED_ROOT_COMPONENTS_PLUS_SOURCE_RESULT",
                "result_role": compiled_specs["topology"]["parent"]["role"],
                "root_component_roles": sorted(selected_root_roles),
                "selected_component_positions": [item["position"] for item in family_items],
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


def coalesce_gemini_json_multitable_hierarchical_document_v1(
    *, page_records: Any, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Select exactly one exhaustive explicit owner/reset-fenced cluster."""

    pages = _page_record_axis(page_records)
    owner_markers = []
    reset_markers = []
    outline_markers = []
    table_axis = []
    boundary_aliases = sorted(
        {
            *compiled_specs["query_policy"]["hard_negative_aliases"],
            *compiled_specs["query_policy"]["reset_aliases"],
        }
    )
    typed_control_boundary_aliases = {
        alias
        for exclusion in compiled_specs["typed_control_exclusions"]
        for alias in exclusion["aliases"]
    }
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
                section_owner_surfaces.append(("SECTION_TITLE", section.get("title_exact")))
            narratives = section.get("narratives_exact")
            if "SECTION_NARRATIVE" in owner_surface_kinds and type(narratives) is list:
                section_owner_surfaces.extend(("SECTION_NARRATIVE", value) for value in narratives)
            for surface_kind, value in section_owner_surfaces:
                for alias in (
                    []
                    if primary
                    else _owner_marker_matches(
                        value,
                        compiled_specs["query_policy"]["owner_aliases"],
                        compiled_specs=compiled_specs,
                    )
                ):
                    owner_markers.append(
                        {
                            "alias": alias,
                            "outline_top_level_number": _outline_top_level_number(
                                value, governing_alias=alias
                            ),
                            "position": section_position,
                            "source_exact": value,
                            "_surface_kind": surface_kind,
                        }
                    )
            section_outline = _outline_top_level_number(section.get("title_exact"))
            if section_outline is not None:
                outline_markers.append(
                    {
                        "alias": f"SOURCE_OUTLINE_TOP_LEVEL:{section_outline}",
                        "outline_top_level_number": section_outline,
                        "position": section_position,
                        "source_exact": section.get("title_exact"),
                    }
                )
            if type(narratives) is list:
                for value in narratives:
                    narrative_outline = _outline_top_level_number(value)
                    if narrative_outline is not None:
                        outline_markers.append(
                            {
                                "alias": f"SOURCE_OUTLINE_TOP_LEVEL:{narrative_outline}",
                                "outline_top_level_number": narrative_outline,
                                "position": section_position,
                                "source_exact": value,
                            }
                        )
            section_boundary_surfaces = [("SECTION_TITLE", section.get("title_exact"))]
            if type(narratives) is list:
                section_boundary_surfaces.extend(
                    ("SECTION_NARRATIVE", value) for value in narratives
                )
            for surface_kind, value in section_boundary_surfaces:
                for alias in _heading_surface_matches(
                    value, boundary_aliases, compiled_specs=compiled_specs
                ):
                    reset_markers.append(
                        {
                            "alias": alias,
                            "container_section_outline": section_outline,
                            "outline_top_level_number": _outline_top_level_number(value),
                            "position": section_position,
                            "source_exact": value,
                            "_surface_kind": surface_kind,
                            "typed_control_only": alias in typed_control_boundary_aliases,
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
                if classification.get("primary_statement_family_root_subtree_receipts"):
                    for receipt in classification["primary_statement_family_root_subtree_receipts"]:
                        result_ordinal = receipt["source_result_row_ordinal"]
                        rows = table.get("rows")
                        assert type(rows) is list
                        owner_markers.append(
                            {
                                "alias": "EXACT_PRIMARY_STATEMENT_FAMILY_ROOT_SUBTREE",
                                "outline_top_level_number": None,
                                "position": position,
                                "source_exact": rows[result_ordinal - 1].get("label_exact"),
                                "_surface_kind": "TABLE_EXACT_RESULT",
                            }
                        )
                if compiled_specs["source_result_query_policy"] in {
                    "OWNER_OR_EXACT_SOURCE_RESULT_ROW",
                    "REQUIRED_EXACT_SOURCE_RESULT_ROW",
                } and classification.get("family_root_row_ordinals"):
                    rows = table.get("rows")
                    assert type(rows) is list
                    for row_ordinal in classification["family_root_row_ordinals"]:
                        row = rows[row_ordinal - 1]
                        owner_markers.append(
                            {
                                "alias": "EXACT_SOURCE_RESULT_ROW",
                                "outline_top_level_number": None,
                                "position": position,
                                "source_exact": row.get("label_exact"),
                                "_surface_kind": "TABLE_EXACT_RESULT",
                            }
                        )
                for value in [table.get("title_exact")]:
                    if not primary and "TABLE_TITLE" in owner_surface_kinds:
                        for alias in _owner_marker_matches(
                            value,
                            compiled_specs["query_policy"]["owner_aliases"],
                            compiled_specs=compiled_specs,
                        ):
                            owner_markers.append(
                                {
                                    "alias": alias,
                                    "outline_top_level_number": _outline_top_level_number(
                                        value, governing_alias=alias
                                    ),
                                    "position": position,
                                    "source_exact": value,
                                    "_surface_kind": "TABLE_TITLE",
                                }
                            )
                    table_outline = _outline_top_level_number(value)
                    if table_outline is not None:
                        outline_markers.append(
                            {
                                "alias": f"SOURCE_OUTLINE_TOP_LEVEL:{table_outline}",
                                "outline_top_level_number": table_outline,
                                "position": position,
                                "source_exact": value,
                            }
                        )
                    if (alias := _marker_matches(value, boundary_aliases)) is not None:
                        reset_markers.append(
                            {
                                "alias": alias,
                                "outline_top_level_number": table_outline,
                                "position": position,
                                "source_exact": value,
                                "_surface_kind": "TABLE_TITLE",
                                "typed_control_only": alias in typed_control_boundary_aliases,
                            }
                        )
                if classification["money_column_ordinals"]:
                    table_axis.append(
                        {
                            "classification": classification,
                            "outline_top_level_number": _outline_top_level_number(
                                table.get("title_exact")
                            ),
                            "position": position,
                            "record": record,
                            "section_id": f"s{section_ordinal}",
                            "table_id": f"t{table_ordinal}",
                        }
                    )

    def item_source_table(item: Mapping[str, Any]) -> Mapping[str, Any] | None:
        sections = item["record"]["page_json"].get("sections")
        section_ordinal = int(item["section_id"][1:])
        table_ordinal = int(item["table_id"][1:])
        if (
            type(sections) is not list
            or section_ordinal > len(sections)
            or type(sections[section_ordinal - 1]) is not dict
        ):
            return None
        source_tables = sections[section_ordinal - 1].get("tables")
        if (
            type(source_tables) is not list
            or table_ordinal > len(source_tables)
            or type(source_tables[table_ordinal - 1]) is not dict
        ):
            return None
        return source_tables[table_ordinal - 1]

    explicit_continuation_marker_visible = any(
        (source_table := item_source_table(item)) is not None
        and source_table.get("continuation")
        in {"CONTINUES_ON_NEXT_PAGE", "CONTINUES_FROM_PREVIOUS_PAGE"}
        for item in table_axis
    )
    if (
        compiled_specs["document_cluster_policy"]
        == "DOCUMENT_EXACT_DECLARED_ROOT_COMPONENTS_PLUS_SOURCE_RESULT"
        and not (
            compiled_specs.get("continuation_period_axis_policy", "LOCAL_PERIOD_AXIS_ONLY")
            == "ADJACENT_PAGE_EXPLICIT_CONTINUATION_INHERITS_COMPLETE_BLANK_HEADER_AXIS"
            and explicit_continuation_marker_visible
        )
    ):
        return _coalesce_document_declared_root_components_v1(
            pages=pages,
            table_axis=table_axis,
            compiled_specs=compiled_specs,
        )

    def narrative_reset_is_logically_after_numbered_table(
        reset: Mapping[str, Any], item: Mapping[str, Any]
    ) -> bool:
        """Correct one bounded Gemini section-order inversion from source outline evidence."""

        item_outline = item.get("outline_top_level_number")
        if (
            item_outline is None
            and item.get("_surface_kind") == "SECTION_TITLE"
            and reset.get("position") == item.get("position")
        ):
            same_section_table_outlines = {
                candidate["outline_top_level_number"]
                for candidate in table_axis
                if candidate["position"][:2] == item["position"][:2]
                and type(candidate.get("outline_top_level_number")) is int
            }
            if len(same_section_table_outlines) == 1:
                item_outline = next(iter(same_section_table_outlines))
        return bool(
            compiled_specs.get("owner_outline_continuation_policy", "SOURCE_POSITION_ONLY")
            == "SAME_SECTION_NUMBERED_TABLE_PRECEDES_HIGHER_NUMBERED_NARRATIVE_RESET"
            and reset.get("_surface_kind") == "SECTION_NARRATIVE"
            and reset["position"][2] == 0
            and (
                item["position"][2] > 0
                or item.get("_surface_kind") == "SECTION_TITLE"
            )
            and reset["position"][:2] == item["position"][:2]
            and type(reset.get("outline_top_level_number")) is int
            and type(item_outline) is int
            and reset["outline_top_level_number"] > item_outline
        )

    def item_inside_owner_interval(
        item: Mapping[str, Any], owner: Mapping[str, Any], reset: Mapping[str, Any] | None
    ) -> bool:
        reset_after_item_by_outline = bool(
            reset is not None
            and narrative_reset_is_logically_after_numbered_table(reset, item)
            and item.get("outline_top_level_number")
            == owner.get("outline_top_level_number")
        )
        if owner.get("_surface_kind") == "TABLE_EXACT_RESULT":
            # With no explicit heading/reset fence, the exact result row owns
            # only its source table.
            return item["position"] == owner["position"]
        if owner.get("_surface_kind") == "TABLE_TITLE":
            if item["position"] == owner["position"]:
                return True
            # A compound table title may carry both the governing numbered
            # note and its first subsection (``19 ... / 19.1 ...``).  Admit
            # only contiguous following tables in the same source section
            # whose independently parsed outline retains that exact top-level
            # number.  This is a bounded source-order fence; an unnumbered or
            # differently numbered sibling remains outside the owner.
            owner_outline = owner.get("outline_top_level_number")
            return bool(
                type(owner_outline) is int
                and item["position"][:2] == owner["position"][:2]
                and item["position"] > owner["position"]
                and item.get("outline_top_level_number") == owner_outline
                and (
                    reset is None
                    or item["position"] < reset["position"]
                    or reset_after_item_by_outline
                )
            )
        return bool(
            owner["position"] <= item["position"]
            and (
                reset is None
                or item["position"] < reset["position"]
                or reset_after_item_by_outline
            )
        )

    def source_section_table(
        item: Mapping[str, Any],
    ) -> tuple[Mapping[str, Any], Mapping[str, Any]] | None:
        sections = item["record"]["page_json"].get("sections")
        section_ordinal = int(item["section_id"][1:])
        table_ordinal = int(item["table_id"][1:])
        if (
            type(sections) is not list
            or section_ordinal > len(sections)
            or type(sections[section_ordinal - 1]) is not dict
        ):
            return None
        source_section = sections[section_ordinal - 1]
        source_tables = source_section.get("tables")
        if (
            type(source_tables) is not list
            or table_ordinal > len(source_tables)
            or type(source_tables[table_ordinal - 1]) is not dict
        ):
            return None
        return source_section, source_tables[table_ordinal - 1]

    def role_lineage(role: str) -> set[str]:
        pending = [role]
        output = set()
        while pending:
            current = pending.pop()
            if current in output:
                continue
            output.add(current)
            pending.extend(
                matcher["within_role"]
                for matcher in compiled_specs["matchers_by_role"].get(current, [])
                if matcher["within_role"] is not None
            )
        return output

    def explicit_adjacent_continuation_receipt(
        prior_item: Mapping[str, Any], current_item: Mapping[str, Any]
    ) -> dict[str, Any] | None:
        if (
            compiled_specs.get("continuation_period_axis_policy", "LOCAL_PERIOD_AXIS_ONLY")
            != "ADJACENT_PAGE_EXPLICIT_CONTINUATION_INHERITS_COMPLETE_BLANK_HEADER_AXIS"
            or current_item["position"][0] != prior_item["position"][0] + 1
            or current_item["record"]["physical_page"]
            != prior_item["record"]["physical_page"] + 1
            or current_item["record"]["document_id"]
            != prior_item["record"]["document_id"]
            or current_item["record"]["source_sha256"]
            != prior_item["record"]["source_sha256"]
        ):
            return None
        prior_source = source_section_table(prior_item)
        current_source = source_section_table(current_item)
        if prior_source is None or current_source is None:
            return None
        prior_section, prior_table = prior_source
        current_section, current_table = current_source
        if (
            prior_table.get("continuation") != "CONTINUES_ON_NEXT_PAGE"
            or current_table.get("continuation") != "CONTINUES_FROM_PREVIOUS_PAGE"
        ):
            return None
        prior_lane_axis = _multitable_lane_axis(
            prior_section, prior_table, compiled_specs=compiled_specs
        )
        current_lane_axis = _multitable_lane_axis(
            current_section, current_table, compiled_specs=compiled_specs
        )
        receiver_lane_axis = None
        receiver_lane_axis_rule = None
        if (
            prior_lane_axis.get("complete") is True
            and current_lane_axis.get("complete") is True
            and current_lane_axis.get("lane_keys") == prior_lane_axis.get("lane_keys")
            and current_lane_axis.get("selected_metric_kinds")
            == prior_lane_axis.get("selected_metric_kinds")
            and current_lane_axis.get("money_column_ordinals")
            == prior_lane_axis.get("money_column_ordinals")
            and current_lane_axis.get("source_lane_keys")
            == prior_lane_axis.get("source_lane_keys")
        ):
            # Some explicit continuations repeat their period headings on the
            # receiver.  Preserve that local source axis byte-for-byte; the
            # continuation marker supplies only the cross-page graph edge.
            # Conflicting or incomplete headings remain unusable.
            receiver_lane_axis = current_lane_axis
            receiver_lane_axis_rule = "EXACT_EQUIVALENT_EXPLICIT_PERIOD_AXIS_NO_MUTATION"
        else:
            inherited_lane_axis = _adjacent_continuation_lane_axis(
                current_section,
                current_table,
                {
                    "document_id": current_item["record"]["document_id"],
                    "physical_page": current_item["record"]["physical_page"],
                    "selected_page_ordinal": current_item["position"][0],
                },
                compiled_specs=compiled_specs,
                prior_fragment={
                    "lane_axis": prior_lane_axis,
                    "region": {
                        "document_id": prior_item["record"]["document_id"],
                        "physical_page": prior_item["record"]["physical_page"],
                        "selected_page_ordinal": prior_item["position"][0],
                    },
                    "table": prior_table,
                },
            )
            if inherited_lane_axis is not None:
                receiver_lane_axis = inherited_lane_axis
                receiver_lane_axis_rule = "COMPLETE_PRIOR_AXIS_INHERITED_BY_BLANK_RECEIVER"
        current_classification, leading_scope_receipt = (
            _explicit_continuation_leading_scope_classification_v1(
                prior_classification=prior_item["classification"],
                current_classification=current_item["classification"],
                current_table=current_table,
                compiled_specs=compiled_specs,
            )
        )
        if (
            receiver_lane_axis is None
            or current_classification.get("typed_control_disposition") is not None
            or current_classification.get("ambiguous_rows")
        ):
            return None
        allowed_unbound_ordinals = {
            row["row_ordinal"] for row in current_classification.get("total_rows", [])
        }
        if (
            set(current_classification.get("unbound_money_row_ordinals", []))
            - allowed_unbound_ordinals
        ):
            return None
        prior_roles = _classification_roles(prior_item["classification"])
        current_roles = _classification_roles(current_classification)
        shared_lineage_roles = {
            ancestor
            for prior_role in prior_roles
            for current_role in current_roles
            for ancestor in role_lineage(prior_role).intersection(
                role_lineage(current_role)
            )
        }
        prior_root_component_roles = prior_roles.intersection(
            compiled_specs["root_component_roles"]
        )
        current_root_component_roles = current_roles.intersection(
            compiled_specs["root_component_roles"]
        )
        if (
            not prior_roles
            or not current_roles
            or not (
                shared_lineage_roles
                or (prior_root_component_roles and current_root_component_roles)
            )
        ):
            return None
        return {
            "_resolved_classification": current_classification,
            "compatible_declared_root_component_roles": sorted(
                prior_root_component_roles | current_root_component_roles
            ),
            "current_position": canonical_clone_v1(current_item["position"]),
            "header_axis_rule": receiver_lane_axis_rule,
            "inherited_lane_axis": canonical_clone_v1(receiver_lane_axis),
            "prior_position": canonical_clone_v1(prior_item["position"]),
            **(
                {"leading_scope_receipt": leading_scope_receipt}
                if leading_scope_receipt is not None
                else {}
            ),
            "shared_declared_lineage_roles": sorted(shared_lineage_roles),
            "rule": (
                "UNIQUE_EXPLICIT_PHYSICALLY_AND_SELECTED_ADJACENT_CONTINUATION_"
                "WITH_EXACT_EQUIVALENT_OR_BLANK_INHERITED_RECEIVER_AXIS_AND_COMPATIBLE_"
                "DECLARED_LINEAGE_OR_ROOT_COMPONENTS"
            ),
        }

    def explicit_receiver_is_locally_usable(item: Mapping[str, Any]) -> bool:
        """Reject a continuation receiver unless one exact predecessor owns it."""

        source = source_section_table(item)
        if source is None or source[1].get("continuation") != "CONTINUES_FROM_PREVIOUS_PAGE":
            return True
        predecessors = [
            candidate
            for candidate in table_axis
            if candidate["position"][0] == item["position"][0] - 1
            and candidate["record"]["physical_page"]
            == item["record"]["physical_page"] - 1
            and candidate["record"]["document_id"] == item["record"]["document_id"]
            and candidate["record"]["source_sha256"] == item["record"]["source_sha256"]
            and (candidate_source := source_section_table(candidate)) is not None
            and candidate_source[1].get("continuation") == "CONTINUES_ON_NEXT_PAGE"
        ]
        usable = [
            (predecessor, receipt)
            for predecessor in predecessors
            if (receipt := explicit_adjacent_continuation_receipt(predecessor, item))
            is not None
        ]
        if len(usable) != 1:
            return False
        # The receipt builder is pure while comparing predecessor candidates.
        # Commit its derived classification only after source adjacency and
        # axis/role compatibility identify exactly one predecessor.
        item["classification"] = usable[0][1]["_resolved_classification"]
        return True

    def public_explicit_continuation_receipt(
        receipt: Mapping[str, Any],
    ) -> dict[str, Any]:
        return {
            key: canonical_clone_v1(value)
            for key, value in receipt.items()
            if not key.startswith("_")
        }

    def cross_page_blank_axis_is_explicitly_continued(
        item: Mapping[str, Any], owner: Mapping[str, Any]
    ) -> bool:
        """Do not carry an all-blank header axis across pages without a marker."""

        if item["position"][0] <= owner["position"][0]:
            return True
        source = source_section_table(item)
        if source is None:
            return False
        _source_section, source_table = source
        columns = source_table.get("columns")
        money_ordinals = item["classification"].get("money_column_ordinals", [])
        if type(columns) is not list or not money_ordinals:
            return True
        if any(
            ordinal <= len(columns)
            and _normalized(_header_text(columns[ordinal - 1]))
            for ordinal in money_ordinals
        ):
            return True
        return source_table.get("continuation") == "CONTINUES_FROM_PREVIOUS_PAGE"

    intervals = []
    for owner in sorted(owner_markers, key=lambda item: item["position"]):
        preceding_resets = [
            marker
            for marker in reset_markers
            if marker["position"] <= owner["position"]
            and not narrative_reset_is_logically_after_numbered_table(marker, owner)
        ]
        prior_reset = max(preceding_resets, key=lambda item: item["position"], default=None)
        overlapping_intervals = [
            interval
            for interval in intervals
            if interval["owner"]["position"] >= (prior_reset or {"position": [-1]})["position"]
        ]
        exact_row_owner_aliases = {
            "EXACT_SOURCE_RESULT_ROW",
            "EXACT_PRIMARY_STATEMENT_FAMILY_ROOT_SUBTREE",
        }
        if overlapping_intervals and (
            owner.get("alias") not in exact_row_owner_aliases
            or any(
                interval["owner"].get("alias") not in exact_row_owner_aliases
                for interval in overlapping_intervals
            )
        ):
            # Running/repeated family headings inside the same reset-free note
            # are continuation evidence, not a second population.
            continue
        owner_outline = owner.get("outline_top_level_number")
        following_resets = [
            marker
            for marker in reset_markers
            if marker["position"] > owner["position"]
            and not (
                type(owner_outline) is int
                and marker.get("typed_control_only") is True
                and (
                    marker.get("outline_top_level_number") == owner_outline
                    or (
                        marker.get("_surface_kind") == "SECTION_NARRATIVE"
                        and marker.get("outline_top_level_number") is None
                        and marker.get("container_section_outline") == owner_outline
                    )
                )
            )
        ]
        if type(owner_outline) is int:
            following_resets.extend(
                marker
                for marker in outline_markers
                if marker["position"] > owner["position"]
                and marker["outline_top_level_number"] != owner_outline
            )
        reset = min(following_resets, key=lambda item: item["position"], default=None)
        items = [
            item
            for item in table_axis
            if item_inside_owner_interval(item, owner, reset)
            and explicit_receiver_is_locally_usable(item)
            and cross_page_blank_axis_is_explicitly_continued(item, owner)
        ]
        leading_items = []
        same_page_preceding = (
            []
            if owner.get("_surface_kind") in {"TABLE_EXACT_RESULT", "TABLE_TITLE"}
            else [
                item
                for item in table_axis
                if item["position"][0] == owner["position"][0]
                and (
                    prior_reset is None
                    or (
                        prior_reset["position"] < item["position"]
                        and not (
                            prior_reset["position"][2] == 0
                            and prior_reset["position"][:2] == item["position"][:2]
                        )
                    )
                )
                and item["position"] < owner["position"]
            ]
        )
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
        items.sort(key=lambda item: item["position"])
        continuation_receipts = []
        for prior_item, current_item in zip(items, items[1:], strict=False):
            current_source = source_section_table(current_item)
            if (
                current_source is not None
                and current_source[1].get("continuation")
                == "CONTINUES_FROM_PREVIOUS_PAGE"
                and (
                    continuation_receipt := explicit_adjacent_continuation_receipt(
                        prior_item, current_item
                    )
                )
                is not None
            ):
                continuation_receipts.append(
                    public_explicit_continuation_receipt(continuation_receipt)
                )
        while items:
            prior_item = max(items, key=lambda item: item["position"])
            possible_receivers = [
                item
                for item in table_axis
                if item not in items
                and item["position"][0] == prior_item["position"][0] + 1
                and item["record"]["physical_page"]
                == prior_item["record"]["physical_page"] + 1
                and (source := source_section_table(item)) is not None
                and source[1].get("continuation") == "CONTINUES_FROM_PREVIOUS_PAGE"
            ]
            if len(possible_receivers) != 1:
                break
            receiver = possible_receivers[0]
            if not explicit_receiver_is_locally_usable(receiver):
                break
            continuation_receipt = explicit_adjacent_continuation_receipt(
                prior_item, receiver
            )
            if continuation_receipt is None:
                break
            items.append(receiver)
            items.sort(key=lambda item: item["position"])
            receiver["classification"] = continuation_receipt[
                "_resolved_classification"
            ]
            continuation_receipts.append(
                public_explicit_continuation_receipt(continuation_receipt)
            )
        if items:
            intervals.append(
                {
                    "continuation_receipts": continuation_receipts,
                    "items": items,
                    "leading_items": leading_items,
                    "owner": owner,
                    "reset": reset,
                    "skipped_same_section_items": skipped_same_section_items,
                }
            )

    complete = []
    require_exact_source_result = (
        compiled_specs["source_result_query_policy"] == "REQUIRED_EXACT_SOURCE_RESULT_ROW"
    )
    select_exact_source_result_population = (
        compiled_specs["source_result_query_policy"] == "OWNER_OR_EXACT_SOURCE_RESULT_ROW"
    )

    def exact_owner_whole_money_table_carrier(item: Mapping[str, Any]) -> bool:
        """Recognize one complete table only from source structure.

        This opt-in is intentionally independent of values and of document
        identity.  It covers two source-authenticated shapes which cannot be
        discovered from declared row aliases alone: a locally owned table with
        one terminal source total, and a locally owned single declared root
        component whose printed table has no total.  Every visible MONEY row
        must belong to that same table population; arithmetic remains an
        evaluator veto, never a query selector.
        """

        if compiled_specs.get("owner_complete_population_policy") != (
            "EXACT_OWNER_WHOLE_MONEY_TABLE"
        ):
            return False
        classification = item["classification"]
        if not classification.get("owner_visible"):
            return False
        role_hits = classification.get("role_hits", [])
        total_rows = classification.get("total_rows", [])
        unbound_ordinals = set(classification.get("unbound_money_row_ordinals", []))
        role_ordinals = {hit["row_ordinal"] for hit in role_hits}
        total_ordinals = {row["row_ordinal"] for row in total_rows}
        observed_ordinals = role_ordinals | total_ordinals | unbound_ordinals
        if not observed_ordinals:
            return False
        terminal_total_frontier = bool(
            len(total_ordinals) == 1
            and max(observed_ordinals) in total_ordinals
            and any(ordinal < max(observed_ordinals) for ordinal in observed_ordinals)
        )
        declared_roles = {hit["role"] for hit in role_hits}
        declared_root_roles = declared_roles.intersection(compiled_specs["root_component_roles"])
        sole_declared_root_component = bool(
            not total_ordinals
            and not unbound_ordinals
            and len(role_hits) == 1
            and len(role_ordinals) == 1
            and declared_roles <= set(compiled_specs["root_component_roles"])
        )
        complete_declared_root_frontier = bool(
            not total_ordinals
            and not unbound_ordinals
            and role_ordinals == observed_ordinals
            and len(declared_root_roles)
            >= compiled_specs["evaluation"].get("minimum_source_visible_root_component_count", 2)
            and any(
                set(combination) <= declared_root_roles
                for combination in compiled_specs["topology"]["required_role_combinations"]
            )
        )
        return bool(
            terminal_total_frontier
            or sole_declared_root_component
            or complete_declared_root_frontier
        )

    def source_result_population_carrier(item: Mapping[str, Any]) -> bool:
        classification = item["classification"]
        declared_root_roles = set(compiled_specs["root_component_roles"]).intersection(
            _classification_roles(classification)
        )
        return bool(
            classification.get("family_root_row_ordinals")
            or (
                classification.get("total_rows")
                and len(declared_root_roles)
                >= compiled_specs["evaluation"].get(
                    "minimum_source_visible_root_component_count", 2
                )
            )
            or exact_owner_whole_money_table_carrier(item)
        )

    source_result_population_conflicts = []
    for interval in intervals:
        eligible_family_items = [
            item
            for item in interval["items"]
            if item["classification"]["typed_control_disposition"] is None
        ]
        source_result_items = [
            item for item in eligible_family_items if source_result_population_carrier(item)
        ]
        if select_exact_source_result_population and len(source_result_items) > 1:
            source_result_population_conflicts.append(interval)
        family_items = (
            source_result_items if select_exact_source_result_population else eligible_family_items
        )
        roles = {
            role for item in family_items for role in _classification_roles(item["classification"])
        }
        span = (
            family_items[-1]["position"][0] - family_items[0]["position"][0] if family_items else 0
        )
        family_root_row_visible = any(
            item["classification"].get("family_root_row_ordinals") for item in family_items
        )
        owner_complete_population_visible = any(
            exact_owner_whole_money_table_carrier(item) for item in family_items
        )
        if (
            family_items
            and (roles or family_root_row_visible or owner_complete_population_visible)
            and (family_root_row_visible or not require_exact_source_result)
            and span <= compiled_specs["topology"]["limits"]["max_continuation_pages"]
        ):
            complete.append({**interval, "family_items": family_items, "roles": sorted(roles)})

    exact_source_result_observed = any(
        item["classification"].get("family_root_row_ordinals")
        for interval in intervals
        for item in interval["items"]
    )
    rootless_source_result_control = bool(
        require_exact_source_result and intervals and not exact_source_result_observed
    )
    reasons = []
    if source_result_population_conflicts:
        reasons.append("MULTIPLE_SOURCE_RESULT_POPULATIONS_INSIDE_OWNER_FENCE")
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
    source_result_population_not_observed = bool(
        select_exact_source_result_population
        and intervals
        and not any(
            source_result_population_carrier(item)
            for interval in intervals
            for item in interval["items"]
        )
    )
    if (
        intervals
        and selected is None
        and not reasons
        and not rootless_source_result_control
        and not source_result_population_not_observed
    ):
        reasons.append("COMPLETE_OWNER_CLUSTER_NOT_RESOLVED")

    role_fallback_policy = compiled_specs["role_anchored_owner_fallback_policy"]
    role_anchored_population_not_observed = False
    if (
        selected is None
        and role_fallback_policy
        == "UNIQUE_REQUIRED_ROLE_TABLE_PLUS_SAME_PAGE_DECLARED_SUPPLEMENTAL_TABLES"
        and set(reasons) <= {"COMPLETE_OWNER_CLUSTER_NOT_RESOLVED"}
    ):
        required_role_combinations = [
            set(combination)
            for combination in compiled_specs["topology"]["required_role_combinations"]
        ]

        def item_roles(item: Mapping[str, Any]) -> set[str]:
            return set(_classification_roles(item["classification"]))

        role_anchors = [
            item
            for item in table_axis
            if item["classification"]["typed_control_disposition"] is None
            and any(required <= item_roles(item) for required in required_role_combinations)
        ]
        if len(role_anchors) == 1:
            anchor = role_anchors[0]
            supplemental_roles = set(compiled_specs["role_anchored_supplemental_roles"])
            supplemental_items = [
                item
                for item in table_axis
                if item is not anchor
                and item["record"]["page_json_version_id"]
                == anchor["record"]["page_json_version_id"]
                and item["classification"]["typed_control_disposition"] is None
                and item_roles(item).intersection(supplemental_roles)
                and not any(required <= item_roles(item) for required in required_role_combinations)
            ]
            fallback_items = sorted(
                [anchor, *supplemental_items], key=lambda item: item["position"]
            )
            selected = {
                "family_items": fallback_items,
                "items": fallback_items,
                "leading_items": [],
                "owner": {
                    "alias": "DECLARED_REQUIRED_ROLE_TABLE",
                    "outline_top_level_number": None,
                    "position": anchor["position"],
                    "source_exact": None,
                },
                "reset": None,
                "role_anchored_fallback": True,
                "roles": sorted({role for item in fallback_items for role in item_roles(item)}),
                "skipped_same_section_items": [],
            }
            reasons = []
        elif len(role_anchors) > 1:
            reasons = ["MULTIPLE_REQUIRED_ROLE_TABLE_POPULATIONS"]
        else:
            # A source may expose only a primary-statement tax line or a tax
            # payable control table under an otherwise matching heading.  The
            # family is not observed unless one table carries the complete
            # declarative role combination; an incomplete heading is neither
            # a candidate nor an unresolved accounting graph.
            reasons = []
            role_anchored_population_not_observed = True
    if (
        selected is None
        and not reasons
        and compiled_specs.get(
            "primary_statement_source_result_fallback_policy", "DISABLED"
        )
        == "UNIQUE_SHALLOWEST_STRUCTURAL_EXACT_VISIBLE_ROOT_WHEN_NOTE_NOT_OBSERVED"
    ):
        primary_source_result_items = [
            item
            for item in table_axis
            if item["classification"].get(
                "primary_statement_source_result_receipt"
            )
            is not None
            and item["classification"].get("typed_control_disposition")
            == "PRIMARY_FINANCIAL_STATEMENT_SUMMARY"
        ]
        if len(primary_source_result_items) == 1:
            primary_item = primary_source_result_items[0]
            selected = {
                "family_items": [primary_item],
                "items": [primary_item],
                "leading_items": [],
                "owner": {
                    "alias": "EXACT_PRIMARY_STATEMENT_SOURCE_RESULT_FALLBACK",
                    "outline_top_level_number": None,
                    "position": primary_item["position"],
                    "source_exact": None,
                    "_surface_kind": "TABLE_EXACT_RESULT",
                },
                "primary_statement_source_result_fallback": True,
                "reset": None,
                "roles": sorted(
                    _classification_roles(primary_item["classification"])
                ),
                "skipped_same_section_items": [],
            }
            role_anchored_population_not_observed = False
        elif len(primary_source_result_items) > 1:
            reasons = ["MULTIPLE_PRIMARY_STATEMENT_SOURCE_RESULT_FALLBACK_POPULATIONS"]
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
        elif (
            select_exact_source_result_population
            and selected is not None
            and not source_result_population_carrier(item)
            and item_inside_owner_interval(item, selected["owner"], selected["reset"])
        ):
            disposition = "EXCLUDED_NON_SOURCE_RESULT_MONEY_TABLE_INSIDE_OWNER_FENCE"
        elif (
            selected is None
            and rootless_source_result_control
            and any(
                item_inside_owner_interval(item, interval["owner"], interval["reset"])
                for interval in intervals
            )
        ):
            disposition = "SOURCE_RESULT_OWNER_WITHOUT_EXACT_RESULT_ROW"
        elif selected is not None and (
            (selected.get("role_anchored_fallback") is True and key in selected_keys)
            or (
                selected.get("role_anchored_fallback") is not True
                and item_inside_owner_interval(item, selected["owner"], selected["reset"])
            )
        ):
            if rootless_source_result_control:
                disposition = "SOURCE_RESULT_OWNER_WITHOUT_EXACT_RESULT_ROW"
            else:
                disposition = "UNCONSUMED_MONEY_TABLE_INSIDE_OWNER_FENCE"
                # Only the uniquely selected owner interval is authoritative.
                # A different heading that happens to contain the owner words
                # may form a non-family interval (for example service expense
                # before operating expense); its tables must not contaminate
                # the selected exhaustive inventory.  Multiple complete owner
                # intervals are already vetoed above.
                reasons.append(
                    "UNCONSUMED_MONEY_TABLE_INSIDE_OWNER_FENCE:" + ":".join(map(str, key))
                )
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
    status = (
        READY
        if regions and not reasons
        else NOT_OBSERVED
        if rootless_source_result_control
        or source_result_population_not_observed
        or role_anchored_population_not_observed
        or (not intervals and not reasons)
        else UNRESOLVED
    )
    material = {
        "component_regions": regions if status == READY else [],
        "declared_money_table_inventory": inventory,
        "document_id": pages[0]["document_id"],
        "document_ordinal": pages[0]["document_ordinal"],
        "owner_receipt": (
            None
            if selected is None
            else {
                **{
                    key: value
                    for key, value in selected["owner"].items()
                    if not key.startswith("_")
                },
                "leading_component_positions": [
                    item["position"] for item in selected["leading_items"]
                ],
                **(
                    {
                        "explicit_adjacent_continuation_receipts": canonical_clone_v1(
                            selected["continuation_receipts"]
                        )
                    }
                    if selected.get("continuation_receipts")
                    else {}
                ),
                "leading_component_rule": (
                    "UNIQUE_REQUIRED_ROLE_TABLE_PLUS_SAME_PAGE_DECLARED_SUPPLEMENTAL_TABLES"
                    if selected.get("role_anchored_fallback") is True
                    else (
                        "UNIQUE_PRIMARY_STATEMENT_EXACT_VISIBLE_ROOT_TABLE"
                        if selected.get("primary_statement_source_result_fallback") is True
                        else "CONTIGUOUS_SAME_PAGE_DECLARED_ROOT_COMPONENT_SUFFIX_BEFORE_OWNER"
                    )
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


def _coefficients(record: Mapping[str, Any]) -> list[int | None]:
    return [observed_source_coefficient_v1(cell) for cell in record["cells"]]


def _record_has_observed_lane(record: Mapping[str, Any]) -> bool:
    """Return whether a record contributes at least one observed coefficient.

    A wholly blank source row remains part of the typed source inventory, but
    it is not an additive zero and therefore cannot enter any equation
    frontier. Exact structural proxies are retained because their derived
    coefficients are observed from a complete source-child frontier.
    """

    return any(
        observed_source_coefficient_v1(cell) is not None for cell in record["cells"]
    )


def _sum_records(records: Sequence[Mapping[str, Any]]) -> list[int | None]:
    if not records:
        return []
    output = []
    for lane in range(len(records[0]["cells"])):
        coefficients = [
            observed_source_coefficient_v1(record["cells"][lane]) for record in records
        ]
        output.append(
            None
            if any(coefficient is None for coefficient in coefficients)
            else sum(coefficient for coefficient in coefficients if coefficient is not None)
        )
    return output


def _sum_record_cells(
    records: Sequence[Mapping[str, Any]], *, exact_state: str
) -> list[dict[str, Any]]:
    return [
        {
            "coefficient": coefficient,
            "source_text": None,
            "state": (
                exact_state
                if coefficient is not None
                else "DERIVED_INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL"
            ),
        }
        for coefficient in _sum_records(records)
    ]


def _equation_record(record: Mapping[str, Any]) -> dict[str, Any]:
    cells = []
    for cell in record["cells"]:
        coefficient = observed_source_coefficient_v1(cell)
        cells.append(
            canonical_clone_v1(cell)
            if coefficient is not None
            else {
                "coefficient": None,
                "source_text": None,
                "state": "BLANK_SOURCE_CELL",
            }
        )
    return {**record, "cells": cells}


def _local_equation(
    *,
    equation_kind: str,
    components: Sequence[Mapping[str, Any]],
    result: Mapping[str, Any],
    multipliers: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Replay local arithmetic after masking every unobserved source lane."""

    return _other_long_term_local_equation(
        equation_kind=equation_kind,
        components=[_equation_record(record) for record in components],
        result=_equation_record(result),
        multipliers=multipliers,
    )


def _same_lane_axis(records: Sequence[Mapping[str, Any]]) -> bool:
    return bool(records) and all(records[0]["lane_keys"] == item["lane_keys"] for item in records)


def _duration_interval_surface(value: Any) -> bool:
    normalized = _normalized(value)
    return bool(
        normalized
        and (
            re.search(r"(?:^|\s)tu(?:\s|$).+(?:^|\s)den(?:\s|$)", normalized)
            or re.search(r"(?:^|\s)from(?:\s|$).+(?:^|\s)to(?:\s|$)", normalized)
        )
    )


_ORDERED_DURATION_DATE = re.compile(
    r"(?<!\d)(?P<day>[0-3]?\d)(?:[./-]|\s)+(?P<month>[01]?\d)(?:[./-]|\s)+"
    r"(?P<year>(?:19|20)\d{2})(?!\d)|"
    r"(?<!\d)(?:ngay\s*)?(?P<word_day>[0-3]?\d)\s+thang\s+"
    r"(?P<word_month>[01]?\d)\s+nam\s+(?P<word_year>(?:19|20)\d{2})(?!\d)"
)


def _ordered_duration_dates(value: Any) -> list[date]:
    """Parse distinct source dates in encounter order using project DMY rules."""

    if type(value) is not str:
        return []
    parsed = []
    for match in _ORDERED_DURATION_DATE.finditer(_normalized(value)):
        if match.group("year") is not None:
            first = int(match.group("day"))
            second = int(match.group("month"))
            year = int(match.group("year"))
            try:
                item = date(year, second, first)
            except ValueError:
                # Match the shared parser's unambiguous MDY fallback only when
                # the second field cannot be a month.
                if second <= 12:
                    continue
                try:
                    item = date(year, first, second)
                except ValueError:
                    continue
        else:
            try:
                item = date(
                    int(match.group("word_year")),
                    int(match.group("word_month")),
                    int(match.group("word_day")),
                )
            except ValueError:
                continue
        if item not in parsed:
            parsed.append(item)
    return parsed


def _duration_semantic_period_roles(value: str) -> list[str]:
    """Return explicit lane roles after excluding duration-only wording.

    ``sáu/chín tháng đầu năm`` describes an elapsed reporting duration, not an
    opening-balance/comparative lane.  The shared snapshot parser correctly
    treats a standalone ``đầu năm`` as comparative; this duration adapter
    removes only the governed ``tháng đầu năm`` occurrence and leaves every
    other explicit current/comparative marker fail-closed.
    """

    # Remove only the governed duration phrase before applying the shared
    # semantic-role inventory.  Looking at the already-collapsed role list is
    # unsafe: ``6 tháng đầu năm 2025; năm trước`` contains both a duration
    # phrase and a genuine comparative marker.  The latter must survive and
    # conflict with the current-year date/year evidence below.
    folded = re.sub(r"\bthang\s+dau\s+nam\b", " ", _normalized(value))
    folded = re.sub(r"\bluy\s+ke\s+tu\s+dau\s+ky\s+den\b", " ", folded)
    folded = re.sub(
        r"\b(?:luy\s+ke\s+)?(?:tu\s+)?dau\s+nam(?:\s+den\s+cuoi\s+quy(?:\s+nay)?)?\b",
        " ",
        folded,
    )
    return _semantic_period_roles(folded)


def _duration_multitable_lane_axis(
    table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Resolve source-visible duration columns without fabricating intervals.

    A duration header may expose a full start/end range, one visible ending
    date, a bare year, or an explicit current/comparative semantic marker.
    Multiple dates are accepted only under source-visible interval grammar;
    arbitrary multi-date surfaces remain ambiguous and fail closed.
    """

    columns = table.get("columns")
    assert type(columns) is list
    all_money_ordinals = _value_column_ordinals(columns, compiled_specs=compiled_specs)
    money_ordinals = list(all_money_ordinals)
    excluded_parallel_money_ordinals = []
    if len(money_ordinals) > 2:
        cumulative_ordinals = [
            ordinal
            for ordinal in money_ordinals
            if any(
                marker in _normalized(_header_text(columns[ordinal - 1]))
                for marker in ("luy ke", "tu dau nam", "den cuoi quy")
            )
        ]
        if len(money_ordinals) == 4 and len(cumulative_ordinals) == 2:
            excluded_parallel_money_ordinals = [
                ordinal for ordinal in money_ordinals if ordinal not in cumulative_ordinals
            ]
            money_ordinals = cumulative_ordinals
    if not 1 <= len(money_ordinals) <= 2:
        return {
            "complete": False,
            "lane_keys": [],
            "layout_kind": None,
            "money_column_ordinals": all_money_ordinals,
            "reasons": ["DURATION_MONEY_COLUMN_CARDINALITY_NOT_ONE_OR_TWO"],
            "source_period_axis": {
                "complete": False,
                "money_column_ordinals": all_money_ordinals,
                "reasons": ["DURATION_MONEY_COLUMN_CARDINALITY_NOT_ONE_OR_TWO"],
            },
        }
    scoped_semantic_headers: dict[int, str] = {}
    duration_header_path_scope_receipt = None
    if (
        compiled_specs.get(
            "duration_header_path_scope_policy", "WHOLE_HEADER_PATH"
        )
        == "DISTINCT_SUFFIX_AFTER_EXACT_COMMON_PREFIX"
        and len(money_ordinals) == 2
    ):
        normalized_paths: dict[int, list[str]] = {}
        source_paths: dict[int, list[str]] = {}
        for ordinal in money_ordinals:
            column = columns[ordinal - 1]
            path = column.get("header_path_exact") if type(column) is dict else None
            if type(path) is not list:
                normalized_paths = {}
                break
            source_path = [
                item
                for item in path
                if type(item) is str and _normalized(item)
            ]
            normalized_path = [_normalized(item) for item in source_path]
            if not normalized_path:
                normalized_paths = {}
                break
            source_paths[ordinal] = source_path
            normalized_paths[ordinal] = normalized_path
        common_length = 0
        if len(normalized_paths) == len(money_ordinals):
            while common_length < min(map(len, normalized_paths.values())) and len(
                {
                    normalized_paths[ordinal][common_length]
                    for ordinal in money_ordinals
                }
            ) == 1:
                common_length += 1
        suffixes = {
            ordinal: source_paths[ordinal][common_length:]
            for ordinal in money_ordinals
            if ordinal in source_paths
        }
        suffix_roles = {
            ordinal: _duration_semantic_period_roles(" ".join(suffix))
            for ordinal, suffix in suffixes.items()
        }
        if (
            common_length > 0
            and len(suffixes) == len(money_ordinals)
            and all(suffixes.values())
            and all(len(roles) == 1 for roles in suffix_roles.values())
            and {roles[0] for roles in suffix_roles.values()}
            == {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"}
        ):
            scoped_semantic_headers = {
                ordinal: " ".join(suffixes[ordinal]) for ordinal in money_ordinals
            }
            duration_header_path_scope_receipt = {
                "common_prefix_exact": source_paths[money_ordinals[0]][:common_length],
                "money_column_suffixes_exact": {
                    f"c{ordinal}": suffixes[ordinal] for ordinal in money_ordinals
                },
                "rule": "DISTINCT_SUFFIX_AFTER_EXACT_COMMON_PREFIX",
                "semantic_roles_by_money_column": {
                    f"c{ordinal}": suffix_roles[ordinal] for ordinal in money_ordinals
                },
            }
    evidence = {}
    reasons = []
    for ordinal in money_ordinals:
        header = _header_text(columns[ordinal - 1])
        # Preserve the source order of an explicit range. Sorting the dates
        # would turn a reversed ``from end to start`` header into a plausible
        # interval. Duplicate textual occurrences of the same date are benign.
        dates = _ordered_duration_dates(header)
        semantic_roles = _duration_semantic_period_roles(
            scoped_semantic_headers.get(ordinal, header)
        )
        bare_years = sorted(
            {int(value) for value in re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", header)}
        )
        unbound_bare_years = sorted(set(bare_years) - {item.year for item in dates})
        if len(semantic_roles) > 1:
            reasons.append(f"MULTIPLE_SEMANTIC_PERIOD_ROLES_IN_MONEY_COLUMN:c{ordinal}")
        if dates and unbound_bare_years:
            reasons.append(f"DATE_AND_UNBOUND_BARE_YEAR_CONFLICT:c{ordinal}")
        if len(dates) > 2:
            reasons.append(f"TOO_MANY_DURATION_DATES_IN_MONEY_COLUMN:c{ordinal}")
            continue
        if len(dates) == 2:
            start, end = dates
            if not _duration_interval_surface(header):
                reasons.append(f"MULTIPLE_UNGOVERNED_DATES_IN_MONEY_COLUMN:c{ordinal}")
                continue
            day_count = (end - start).days
            if not 1 <= day_count <= 370:
                reasons.append(f"INVALID_DURATION_DATE_RANGE_IN_MONEY_COLUMN:c{ordinal}")
                continue
            evidence[ordinal] = {
                "end": end.isoformat(),
                "kind": "SOURCE_VISIBLE_DATE_RANGE",
                "semantic_roles": semantic_roles,
                "start": start.isoformat(),
            }
        elif len(dates) == 1:
            evidence[ordinal] = {
                "end": dates[0].isoformat(),
                "kind": "SOURCE_VISIBLE_END_DATE",
                "semantic_roles": semantic_roles,
            }
        elif len(bare_years) == 1:
            evidence[ordinal] = {
                "kind": "SOURCE_VISIBLE_BARE_YEAR",
                "semantic_roles": semantic_roles,
                "year": bare_years[0],
            }
        elif len(bare_years) > 1:
            reasons.append(f"MULTIPLE_BARE_YEARS_IN_MONEY_COLUMN:c{ordinal}")
        elif len(semantic_roles) == 1:
            evidence[ordinal] = {
                "kind": "SOURCE_VISIBLE_SEMANTIC_ROLE",
                "semantic_roles": semantic_roles,
            }
        else:
            reasons.append(f"DURATION_PERIOD_EVIDENCE_ABSENT:c{ordinal}")
    if reasons or len(evidence) != len(money_ordinals):
        reasons = sorted(set(reasons))
        return {
            "complete": False,
            "lane_keys": [],
            "layout_kind": None,
            "money_column_ordinals": money_ordinals,
            "reasons": reasons,
            "source_period_axis": {
                "complete": False,
                "evidence_by_money_column": {
                    f"c{ordinal}": evidence[ordinal] for ordinal in sorted(evidence)
                },
                "reasons": reasons,
            },
        }

    kinds = {item["kind"] for item in evidence.values()}
    if len(kinds) != 1:
        reasons.append("DURATION_PERIOD_PRECISION_DIFFERS_ACROSS_MONEY_COLUMNS")
    kind = next(iter(kinds)) if len(kinds) == 1 else None
    ordered = list(money_ordinals)
    if len(money_ordinals) == 2 and kind in {
        "SOURCE_VISIBLE_DATE_RANGE",
        "SOURCE_VISIBLE_END_DATE",
    }:
        ordered = sorted(money_ordinals, key=lambda item: evidence[item]["end"], reverse=True)
        if evidence[ordered[0]]["end"] == evidence[ordered[1]]["end"]:
            reasons.append("DURATION_END_DATES_ARE_NOT_DISTINCT")
        if kind == "SOURCE_VISIBLE_DATE_RANGE":
            if evidence[ordered[0]]["start"] <= evidence[ordered[1]]["start"]:
                reasons.append("DURATION_RANGE_START_AND_END_ORDER_CONFLICT")
            lengths = []
            for ordinal in ordered:
                start = next(
                    item
                    for item in _surface_dates(_header_text(columns[ordinal - 1]))
                    if item.isoformat() == evidence[ordinal]["start"]
                )
                end = next(
                    item
                    for item in _surface_dates(_header_text(columns[ordinal - 1]))
                    if item.isoformat() == evidence[ordinal]["end"]
                )
                lengths.append((end - start).days)
            if abs(lengths[0] - lengths[1]) > 3:
                reasons.append("DURATION_RANGE_LENGTHS_ARE_NOT_COMPARABLE")
    elif len(money_ordinals) == 2 and kind == "SOURCE_VISIBLE_BARE_YEAR":
        ordered = sorted(money_ordinals, key=lambda item: evidence[item]["year"], reverse=True)
        if evidence[ordered[0]]["year"] == evidence[ordered[1]]["year"]:
            reasons.append("DURATION_BARE_YEARS_ARE_NOT_DISTINCT")
    elif len(money_ordinals) == 2 and kind == "SOURCE_VISIBLE_SEMANTIC_ROLE":
        by_role = {evidence[ordinal]["semantic_roles"][0]: ordinal for ordinal in money_ordinals}
        if set(by_role) != {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"}:
            reasons.append("DURATION_SEMANTIC_PERIOD_AXIS_IS_NOT_CURRENT_COMPARATIVE")
        else:
            ordered = [by_role["CURRENT_PERIOD"], by_role["COMPARATIVE_PERIOD"]]
    expected_roles = {
        ordinal: role
        for ordinal, role in zip(
            ordered,
            ["CURRENT_PERIOD", "COMPARATIVE_PERIOD"][: len(ordered)],
            strict=True,
        )
    }
    for ordinal, item in evidence.items():
        if item["semantic_roles"] and item["semantic_roles"] != [expected_roles[ordinal]]:
            reasons.append(f"DATE_SEMANTIC_PERIOD_CONFLICT:c{ordinal}")
    if reasons:
        reasons = sorted(set(reasons))
        return {
            "complete": False,
            "lane_keys": [],
            "layout_kind": None,
            "money_column_ordinals": money_ordinals,
            "reasons": reasons,
            "source_period_axis": {
                "complete": False,
                "evidence_by_money_column": {
                    f"c{ordinal}": evidence[ordinal] for ordinal in sorted(evidence)
                },
                "reasons": reasons,
            },
        }
    source_lane_keys = []
    for ordinal in ordered:
        item = evidence[ordinal]
        if item["kind"] == "SOURCE_VISIBLE_DATE_RANGE":
            source_lane_keys.append(["DURATION_DATE_RANGE", item["start"], item["end"]])
        elif item["kind"] == "SOURCE_VISIBLE_END_DATE":
            source_lane_keys.append(["DURATION_END_DATE", item["end"]])
        elif item["kind"] == "SOURCE_VISIBLE_BARE_YEAR":
            source_lane_keys.append(["DURATION_BARE_YEAR", str(item["year"])])
        else:
            source_lane_keys.append(["SEMANTIC_ALIAS", item["semantic_roles"][0]])
    result = {
        "complete": True,
        "lane_keys": [
            ["SEMANTIC_ALIAS", role]
            for role in ["CURRENT_PERIOD", "COMPARATIVE_PERIOD"][: len(ordered)]
        ],
        "layout_kind": "DURATION_PERIOD_MONEY_COLUMNS",
        "money_column_ordinals": ordered,
        "reasons": [],
        "selected_metric_kinds": ["GENERIC_AMOUNT"] * len(ordered),
        "source_lane_keys": source_lane_keys,
        "source_period_axis": {
            "complete": True,
            "evidence_by_money_column": {
                f"c{ordinal}": evidence[ordinal] for ordinal in sorted(evidence)
            },
            "rule": "SOURCE_VISIBLE_DURATION_RANGE_END_DATE_BARE_YEAR_OR_SEMANTIC_ROLE",
        },
    }
    if excluded_parallel_money_ordinals:
        result["excluded_parallel_duration_money_column_ordinals"] = (
            excluded_parallel_money_ordinals
        )
        result["source_period_axis"]["selection_rule"] = (
            "EXACT_TWO_CUMULATIVE_DURATION_COLUMNS_FROM_PARALLEL_QUARTER_AND_YTD_AXIS"
        )
    if duration_header_path_scope_receipt is not None:
        result["source_period_axis"]["header_path_scope_receipt"] = (
            duration_header_path_scope_receipt
        )
    return result


_DURATION_MONTH_TOKEN = re.compile(
    r"(?<![a-z0-9])(?P<count>3|6|9|12|ba|sau|chin|muoi\s+hai|three|six|nine|twelve)"
    r"\s+(?:thang|months?)(?![a-z0-9])"
)
_DURATION_MONTH_VALUES = {
    "3": 3,
    "ba": 3,
    "three": 3,
    "6": 6,
    "sau": 6,
    "six": 6,
    "9": 9,
    "chin": 9,
    "nine": 9,
    "12": 12,
    "muoi hai": 12,
    "twelve": 12,
}


def _explicit_duration_month_counts(value: Any) -> list[int]:
    folded = _normalized(value)
    return sorted(
        {
            _DURATION_MONTH_VALUES[re.sub(r"\s+", " ", match.group("count"))]
            for match in _DURATION_MONTH_TOKEN.finditer(folded)
        }
    )


def _document_duration_month_context_axis(
    page_json_by_version: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Inventory governed reporting-duration phrases across immutable JSON.

    Only titles of typed primary income/cash-flow statements can provide
    document context, and the visible phrase must bind ``N months`` to an
    ended reporting period.  Maturity buckets, legal dates, loan tenors, and
    arbitrary note narratives therefore cannot establish this axis.  A local
    note may use symbolic ``Kỳ này/Kỳ trước`` while the primary statement
    supplies the exact duration independently.
    """

    evidence = []
    conflicts = []

    def observe(
        value: Any,
        *,
        page_json_version_id: str,
        section_id: str,
        source_kind: str,
        table_id: str | None = None,
    ) -> None:
        folded = _normalized(value)
        annual_reporting_period = bool(
            re.search(r"\bnam(?:\s+tai\s+chinh)?\s+ket\s+thuc\b", folded)
            or re.search(r"\b(?:financial\s+)?year\s+ended\b", folded)
        )
        explicit_reporting_period = bool(
            re.search(
                r"\b(?:cho|trong)\s+(?:ky|giai\s+doan)\b.*"
                r"\b(?:thang|months?)\b.*\b(?:ket\s+thuc|ended)\b",
                folded,
            )
            or re.search(r"\b(?:three|six|nine|twelve)\s+months?\s+ended\b", folded)
        )
        if not (annual_reporting_period or explicit_reporting_period):
            return
        counts = sorted(
            {
                *_explicit_duration_month_counts(value),
                *([12] if annual_reporting_period else []),
            }
        )
        if not counts:
            return
        item = {
            "month_counts": counts,
            "page_json_version_id": page_json_version_id,
            "section_id": section_id,
            "source_exact": value,
            "source_kind": source_kind,
        }
        if table_id is not None:
            item["table_id"] = table_id
        if len(counts) != 1:
            conflicts.append(item)
        else:
            evidence.append(item)

    for page_json_version_id, page_json in sorted(page_json_by_version.items()):
        if _PAGE_VERSION.fullmatch(page_json_version_id) is None or type(page_json) is not dict:
            raise _error("multi-table duration context page is invalid")
        if page_json.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
            continue
        for section_ordinal, section in enumerate(page_json.get("sections") or [], start=1):
            if type(section) is not dict:
                continue
            if section.get("content_kind") != "PRIMARY_STATEMENT" or section.get(
                "statement_type"
            ) not in {"INCOME_STATEMENT", "CASH_FLOW"}:
                continue
            section_id = f"s{section_ordinal}"
            observe(
                section.get("title_exact"),
                page_json_version_id=page_json_version_id,
                section_id=section_id,
                source_kind="SECTION_TITLE",
            )
    identities = {item["month_counts"][0] for item in evidence}
    unique = not conflicts and len(identities) == 1
    return {
        "conflicts": conflicts,
        "evidence": evidence,
        "evidence_axis_sha256": canonical_json_sha256_v1(evidence),
        "months": next(iter(identities)) if unique else None,
        "rule": (
            "UNIQUE_GOVERNED_EXPLICIT_N_MONTH_DURATION_ACROSS_TYPED_PRIMARY_"
            "INCOME_AND_CASH_FLOW_STATEMENT_TITLES"
        ),
        "status": "UNIQUE"
        if unique
        else ("ABSENT" if not evidence and not conflicts else "NOT_UNIQUE"),
    }


def _table_duration_month_axis(
    table: Mapping[str, Any],
    lane_axis: Mapping[str, Any],
    *,
    document_context: Mapping[str, Any],
) -> dict[str, Any]:
    columns = table.get("columns")
    if type(columns) is not list or not lane_axis.get("complete"):
        return {"complete": False, "months": [], "reasons": ["DURATION_LANE_AXIS_INVALID"]}
    months = []
    evidence = []
    reasons = []
    inherited = (
        document_context.get("months") if document_context.get("status") == "UNIQUE" else None
    )
    for ordinal in lane_axis["money_column_ordinals"]:
        header = _header_text(columns[ordinal - 1])
        explicit = _explicit_duration_month_counts(header)
        bare_years = re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", header)
        folded = _normalized(header)
        local_months = None
        source_kind = None
        if len(explicit) > 1:
            reasons.append(f"MULTIPLE_DURATION_MONTH_COUNTS_IN_VALUE_COLUMN:c{ordinal}")
        elif len(explicit) == 1:
            local_months = explicit[0]
            source_kind = "SOURCE_VISIBLE_EXPLICIT_MONTH_COUNT"
        elif (
            bool(
                re.search(r"\b(?:nam|year)\s+(?:19|20)\d{2}\b", folded)
                or re.search(r"\bnam\s+tai\s+chinh\b", folded)
            )
            and not re.search(r"\b(?:quy|quarter|q[1-4])\b", folded)
            and not _ordered_duration_dates(header)
            and not re.search(r"\b(?:thang|month)\b", folded)
        ):
            local_months = 12
            source_kind = "SOURCE_VISIBLE_ANNUAL_YEAR_HEADER"
        elif inherited is not None:
            local_months = inherited
            source_kind = "TYPED_DOCUMENT_DURATION_CONTEXT"
        elif any(
            marker in f" {folded} "
            for marker in (" nam nay ", " nam truoc ", " current year ", " prior year ")
        ):
            local_months = 12
            source_kind = "SOURCE_VISIBLE_ANNUAL_YEAR_HEADER"
        elif (
            len(set(bare_years)) == 1
            and not _ordered_duration_dates(header)
            and not re.search(r"\b(?:thang|month|quy|quarter|q[1-4])\b", folded)
        ):
            # A lone year is conventionally a full-year duration only when no
            # authenticated non-annual document duration exists.  The typed
            # document branch above therefore wins for interim reports whose
            # local table prints only ``2025 / 2024``.
            local_months = 12
            source_kind = "SOURCE_VISIBLE_BARE_YEAR_WITHOUT_TYPED_NONANNUAL_CONTEXT"
        else:
            dates = _ordered_duration_dates(header)
            if (
                len(dates) == 1
                and dates[0].month in {3, 6, 9, 12}
                and any(marker in f" {folded} " for marker in (" den ", " ended ", " ket thuc "))
            ):
                local_months = dates[0].month
                source_kind = "SOURCE_VISIBLE_CUMULATIVE_QUARTER_END_HEADER"
            else:
                reasons.append(f"DURATION_MONTH_COUNT_NOT_RESOLVED:c{ordinal}")
        if local_months is not None:
            if inherited is not None and local_months != inherited:
                reasons.append(f"LOCAL_AND_DOCUMENT_DURATION_MONTH_CONFLICT:c{ordinal}")
            months.append(local_months)
            evidence.append(
                {
                    "column_ordinal": ordinal,
                    "months": local_months,
                    "source_exact": header,
                    "source_kind": source_kind,
                }
            )
    if len(months) != len(lane_axis["money_column_ordinals"]):
        reasons.append("DURATION_MONTH_AXIS_INCOMPLETE")
    if len(set(months)) > 1:
        reasons.append("CURRENT_AND_COMPARATIVE_DURATION_MONTH_COUNTS_DIFFER")
    return {
        "complete": not reasons,
        "document_duration_context": (
            canonical_clone_v1(document_context)
            if any(item["source_kind"] == "TYPED_DOCUMENT_DURATION_CONTEXT" for item in evidence)
            else None
        ),
        "evidence": evidence,
        "months": months if not reasons else [],
        "reasons": sorted(set(reasons)),
    }


def _source_ratio_decimal(value: Any) -> dict[str, Any]:
    if type(value) is int:
        return {"decimal": Decimal(value), "decimal_scale": 0, "source_text": str(value)}
    if type(value) is not str or not value.strip():
        raise _error("ratio metric source value is not visible text")
    source_text = value
    body = value.strip().replace(" ", "")
    negative = body.startswith("(") and body.endswith(")")
    if negative:
        body = body[1:-1]
    if body.startswith("-"):
        negative = True
        body = body[1:]
    if re.fullmatch(r"[0-9]+", body):
        scale = 0
        normalized = body
    elif re.fullmatch(r"[0-9]{1,3}[.,][0-9]{1,2}", body):
        separator = "," if "," in body else "."
        whole, fraction = body.split(separator)
        scale = len(fraction)
        normalized = whole + "." + fraction
    else:
        raise _error("ratio metric source value is not an exact decimal")
    try:
        parsed = Decimal(normalized)
    except InvalidOperation as exc:
        raise _error("ratio metric source decimal is invalid") from exc
    if negative:
        parsed = -parsed
    return {"decimal": parsed, "decimal_scale": scale, "source_text": source_text}


def _derive_table_ratio_metric_records(
    *,
    rows: Sequence[Mapping[str, Any]],
    row_records: Mapping[int, Mapping[str, Any]],
    hit_by_row: Mapping[int, str],
    lane_axis: Mapping[str, Any],
    region: Mapping[str, Any],
    table: Mapping[str, Any],
    document_duration_context: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    ratio_metric_equations = compiled_specs.get("ratio_metric_equations", [])
    if not ratio_metric_equations:
        return [], [], [], []
    duration_axis = _table_duration_month_axis(
        table, lane_axis, document_context=document_duration_context
    )
    if not duration_axis["complete"]:
        return [], [], [{"duration_month_axis": duration_axis}], duration_axis["reasons"]
    ordinals_by_role: dict[str, list[int]] = defaultdict(list)
    for row_ordinal, role in hit_by_row.items():
        ordinals_by_role[role].append(row_ordinal)
    output = []
    equations = []
    receipts = []
    reasons = []

    def visible_record(record: Mapping[str, Any] | None) -> bool:
        return bool(
            record is not None and any(cell["source_text"] is not None for cell in record["cells"])
        )

    for declaration in ratio_metric_equations:
        result_role = declaration["result_role"]
        result_ordinals = ordinals_by_role.get(result_role, [])
        denominator_ordinals = ordinals_by_role.get(declaration["denominator_role"], [])
        if not result_ordinals:
            # Ratio rows are optional source evidence.  Their absence cannot
            # make an otherwise complete direct mapping population unusable.
            continue
        if len(result_ordinals) != 1:
            reasons.append(f"RATIO_RESULT_ROLE_NOT_UNIQUE:{result_role}")
            continue
        if len(denominator_ordinals) != 1:
            reasons.append(f"RATIO_DENOMINATOR_ROLE_NOT_UNIQUE:{result_role}")
            continue
        result_ordinal = result_ordinals[0]
        denominator_ordinal = denominator_ordinals[0]
        denominator = row_records.get(denominator_ordinal)
        if not visible_record(denominator):
            reasons.append(f"RATIO_DENOMINATOR_SOURCE_NOT_VISIBLE:{result_role}")
            continue
        numerator_candidates = []
        for numerator_role in declaration["numerator_roles"]:
            numerator_ordinals = ordinals_by_role.get(numerator_role, [])
            direct = (
                row_records.get(numerator_ordinals[0]) if len(numerator_ordinals) == 1 else None
            )
            if visible_record(direct):
                numerator_candidates.append((numerator_role, direct))
                continue
            derivations = [
                item
                for item in compiled_specs["derived_role_equations"]
                if item["result_role"] == numerator_role
            ]
            if len(derivations) != 1:
                continue
            components = []
            for component_role in derivations[0]["component_roles"]:
                component_ordinals = ordinals_by_role.get(component_role, [])
                component = (
                    row_records.get(component_ordinals[0]) if len(component_ordinals) == 1 else None
                )
                if not visible_record(component):
                    components = []
                    break
                components.append(component)
            if not components or not _same_lane_axis(components):
                continue
            numerator_candidates.append(
                (
                    numerator_role,
                    _local_record(
                        numerator_role,
                        _sum_record_cells(
                            components,
                            exact_state="EXACT_DECLARED_RATIO_NUMERATOR_COMPONENT_SUM",
                        ),
                        components[0]["lane_keys"],
                        [
                            source_ref
                            for component in components
                            for source_ref in component["source_refs"]
                        ],
                        "DECLARED_RATIO_NUMERATOR_DERIVED_FROM_VISIBLE_COMPONENT_SUM",
                        components[0]["valuation_basis"],
                    ),
                )
            )
        if len(numerator_candidates) != 1:
            reasons.append(f"RATIO_NUMERATOR_ALTERNATIVE_NOT_UNIQUE:{result_role}")
            continue
        numerator_role, numerator = numerator_candidates[0]
        assert denominator is not None
        if not _same_lane_axis([numerator, denominator]):
            reasons.append(f"RATIO_COMPONENT_LANE_AXIS_NOT_EXACT:{result_role}")
            continue
        if any(value is None for value in _coefficients(numerator)) or any(
            value is None for value in _coefficients(denominator)
        ):
            reasons.append(f"RATIO_COMPONENT_SOURCE_LANE_IS_UNOBSERVED:{result_role}")
            continue
        source_row = rows[result_ordinal - 1]
        source_values = source_row.get("values_exact")
        value_ordinals = lane_axis["money_column_ordinals"]
        if type(source_values) is not list or any(
            ordinal > len(source_values) for ordinal in value_ordinals
        ):
            reasons.append(f"RATIO_VISIBLE_VALUE_AXIS_INCOMPLETE:{result_role}")
            continue
        try:
            visible = [
                _source_ratio_decimal(source_values[ordinal - 1]) for ordinal in value_ordinals
            ]
        except GeminiJsonMultitableHierarchicalFamilyV1Error:
            reasons.append(f"RATIO_VISIBLE_VALUE_NOT_EXACT_DECIMAL:{result_role}")
            continue
        label = _normalized(source_row.get("label_exact"))
        source_is_monthly = bool(re.search(r"\b(?:thang|month|monthly)\b", label))
        target_quantum = Decimal(1).scaleb(-declaration["decimal_scale"])
        mapped_cells = []
        visible_computed = []
        visible_rounding_intervals = []
        comparison_rules = []
        mapped_decimals = []
        mismatch = False
        for lane, months in enumerate(duration_axis["months"]):
            numerator_value = Decimal(numerator["cells"][lane]["coefficient"])
            denominator_value = Decimal(denominator["cells"][lane]["coefficient"])
            # The source displays the denominator as a whole unit, so its
            # authenticated interval is [value - 0.5, value + 0.5).  Require
            # that entire interval to stay strictly positive before division.
            if denominator_value <= Decimal("0.5"):
                mismatch = True
                break
            nominal_monthly = numerator_value / denominator_value / Decimal(months)
            visible_quantum = Decimal(1).scaleb(-visible[lane]["decimal_scale"])
            source_divisor = Decimal(months) if source_is_monthly else Decimal(1)
            nominal_visible = numerator_value / denominator_value / source_divisor
            expected_visible = nominal_visible.quantize(visible_quantum, rounding=ROUND_HALF_UP)
            # Both amount and average-headcount rows are printed as whole
            # source units.  Propagate their declared half-unit display
            # precision through the ratio instead of introducing an arbitrary
            # epsilon.  A printed ratio is corroborated iff its own rounding
            # bin intersects that exact possible interval.
            half_source_unit = Decimal("0.5")
            interval_low = (
                max(Decimal(0), numerator_value - half_source_unit)
                / (denominator_value + half_source_unit)
                / source_divisor
            )
            interval_high = (
                (numerator_value + half_source_unit)
                / (denominator_value - half_source_unit)
                / source_divisor
            )
            visible_half_quantum = visible_quantum / Decimal(2)
            visible_bin_low = visible[lane]["decimal"] - visible_half_quantum
            visible_bin_high = visible[lane]["decimal"] + visible_half_quantum
            interval_exact = bool(
                interval_high >= visible_bin_low and interval_low < visible_bin_high
            )
            if expected_visible == visible[lane]["decimal"]:
                comparison_rule = "EXACT_DECLARED_VISIBLE_SCALE_ROUND_HALF_UP"
            elif interval_exact:
                comparison_rule = "EXACT_PROPAGATED_HALF_UNIT_SOURCE_DISPLAY_ROUNDING_INTERVAL"
            else:
                comparison_rule = "MISMATCH_OUTSIDE_SOURCE_DISPLAY_ROUNDING_INTERVAL"
            visible_computed.append(format(expected_visible, "f"))
            visible_rounding_intervals.append(
                {
                    "source_ratio_lower_bound_decimal": format(interval_low, "f"),
                    "source_ratio_upper_bound_decimal": format(interval_high, "f"),
                    "source_ratio_interval_rule": (
                        "WHOLE_UNIT_NUMERATOR_AND_DENOMINATOR_HALF_OPEN_BOUNDS"
                    ),
                    "visible_rounding_bin_lower_decimal": format(visible_bin_low, "f"),
                    "visible_rounding_bin_upper_decimal": format(visible_bin_high, "f"),
                }
            )
            comparison_rules.append(comparison_rule)
            mapped = (visible[lane]["decimal"] if source_is_monthly else nominal_monthly).quantize(
                target_quantum, rounding=ROUND_HALF_UP
            )
            mapped_decimals.append(format(mapped, "f"))
            if not interval_exact:
                mismatch = True
            scaled = mapped * (Decimal(10) ** declaration["decimal_scale"])
            mapped_cells.append(
                {
                    "coefficient": int(scaled),
                    "decimal_scale": declaration["decimal_scale"],
                    "normalized_decimal": format(mapped, "f"),
                    "source_text": (visible[lane]["source_text"] if source_is_monthly else None),
                    "state": (
                        "SOURCE_VISIBLE_MONTHLY_RATIO_CORROBORATED_BY_EXACT_"
                        "DISPLAY_PRECISION_INTERVAL"
                        if source_is_monthly
                        else "DERIVED_MONTHLY_RATIO_AFTER_SOURCE_VISIBLE_CORROBORATION"
                    ),
                }
            )
        result_source_ref = _transposed_source_ref(
            region,
            result_ordinal,
            source_row,
            money_column_ordinals=value_ordinals,
        )
        equation_material = {
            "component_roles": [numerator_role, declaration["denominator_role"]],
            "component_source_refs": [
                canonical_clone_v1(numerator["source_refs"]),
                canonical_clone_v1(denominator["source_refs"]),
            ],
            "comparison_rules": comparison_rules,
            "equation_kind": "EXACT_SOURCE_VISIBLE_RATIO_CORROBORATES_DERIVED_MONTHLY_VALUE",
            "lane_keys": canonical_clone_v1(numerator["lane_keys"]),
            "mapped_monthly_decimals": mapped_decimals,
            "months": canonical_clone_v1(duration_axis["months"]),
            "result_role": result_role,
            "result_source_refs": [canonical_clone_v1(result_source_ref)],
            "source_average_basis": "MONTHLY" if source_is_monthly else "PERIOD_TOTAL",
            "status": "MISMATCH" if mismatch else "EXACT",
            "visible_computed_decimals": visible_computed,
            "visible_rounding_intervals": visible_rounding_intervals,
            "visible_source_decimals": [format(item["decimal"], "f") for item in visible],
        }
        equation = {
            **equation_material,
            "equation_id": "gjmthfev1:equation:" + canonical_json_sha256_v1(equation_material),
        }
        equations.append(equation)
        receipts.append(
            {
                "declaration": canonical_clone_v1(declaration),
                "duration_month_axis": duration_axis,
                "equation_id": equation["equation_id"],
                "result_source_ref": canonical_clone_v1(result_source_ref),
            }
        )
        if mismatch:
            reasons.append(f"SOURCE_VISIBLE_RATIO_EQUATION_MISMATCH:{result_role}")
            continue
        output.append(
            _local_record(
                result_role,
                mapped_cells,
                numerator["lane_keys"],
                [
                    *canonical_clone_v1(numerator["source_refs"]),
                    *canonical_clone_v1(denominator["source_refs"]),
                    result_source_ref,
                ],
                "DERIVED_MONTHLY_RATIO_PROVEN_BY_SOURCE_VISIBLE_AVERAGE",
                f"MONTHLY_RATIO_DECIMAL_SCALE_{declaration['decimal_scale']}",
            )
        )
    return output, equations, receipts, sorted(set(reasons))


def _declared_multi_metric_lane_axis(
    table: Mapping[str, Any],
    *,
    declaration: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Resolve a repeated period × metric column layout from source headers.

    The declaration is data-only.  It selects no row or value and is active
    only when at least one configured metric alias is source-visible.  Once
    active, every value column and every visible row must belong to one exact
    period/metric equation frontier; a partial, duplicate, or mismatching
    frontier is unresolved rather than silently falling back to an ordinary
    two-column layout.
    """

    columns = table.get("columns")
    rows = table.get("rows")
    if type(columns) is not list or type(rows) is not list:
        return None
    value_ordinals = _value_column_ordinals(columns, compiled_specs=compiled_specs)
    column_axis = []
    any_metric_visible = False
    reasons = []
    for ordinal in value_ordinals:
        header = _header_text(columns[ordinal - 1])
        matched_metrics = sorted(
            metric
            for metric, aliases in declaration["metric_aliases"].items()
            if any(_contains_alias(header, alias) for alias in aliases)
        )
        any_metric_visible = any_metric_visible or bool(matched_metrics)
        dates = sorted({item.isoformat() for item in _surface_dates(header)}, reverse=True)
        semantic_roles = _semantic_period_roles(header)
        bare_years = sorted(
            {int(value) for value in re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", header)},
            reverse=True,
        )
        if len(matched_metrics) != 1:
            reasons.append(
                f"MULTI_METRIC_VALUE_COLUMN_ROLE_NOT_UNIQUE:c{ordinal}:"
                + ("NONE" if not matched_metrics else "+".join(matched_metrics))
            )
        if len(dates) > 1:
            reasons.append(f"MULTIPLE_PERIOD_DATES_IN_MULTI_METRIC_COLUMN:c{ordinal}")
        if len(semantic_roles) > 1:
            reasons.append(f"MULTIPLE_SEMANTIC_PERIOD_ROLES_IN_MULTI_METRIC_COLUMN:c{ordinal}")
        if not dates and not semantic_roles and len(bare_years) != 1:
            reasons.append(f"MULTI_METRIC_COLUMN_PERIOD_NOT_UNIQUE:c{ordinal}")
        column_axis.append(
            {
                "bare_years": bare_years,
                "column_ordinal": ordinal,
                "dates": dates,
                "header_exact": header,
                "metric": matched_metrics[0] if len(matched_metrics) == 1 else None,
                "semantic_roles": semantic_roles,
            }
        )
    if not any_metric_visible:
        return None
    if not value_ordinals:
        reasons.append("MULTI_METRIC_VALUE_COLUMN_AXIS_EMPTY")

    period_kind_axis = {
        "DATE" if item["dates"] else "SEMANTIC_ALIAS" if item["semantic_roles"] else "BARE_YEAR"
        for item in column_axis
    }
    if len(period_kind_axis) != 1:
        reasons.append("MULTI_METRIC_PERIOD_EVIDENCE_KINDS_MIXED")
    period_kind = next(iter(period_kind_axis)) if len(period_kind_axis) == 1 else None
    raw_period_keys = []
    for item in column_axis:
        if item["dates"]:
            raw_period_keys.append(("DATE", item["dates"][0]))
        elif item["semantic_roles"]:
            raw_period_keys.append(("SEMANTIC_ALIAS", item["semantic_roles"][0]))
        elif len(item["bare_years"]) == 1:
            raw_period_keys.append(("BARE_YEAR", str(item["bare_years"][0])))
        else:
            raw_period_keys.append(("UNRESOLVED", f"c{item['column_ordinal']}"))
    distinct_period_keys = sorted(set(raw_period_keys), reverse=True)
    if len(distinct_period_keys) != 2:
        reasons.append("MULTI_METRIC_EXACT_TWO_PERIOD_POPULATIONS_REQUIRED")

    ordered_period_keys: list[tuple[str, str]] = []
    lane_role_by_key: dict[tuple[str, str], str] = {}
    if period_kind == "DATE" and len(distinct_period_keys) == 2:
        ordered_period_keys = sorted(distinct_period_keys, key=lambda item: item[1], reverse=True)
        lane_role_by_key = {
            ordered_period_keys[0]: "CURRENT_PERIOD",
            ordered_period_keys[1]: "COMPARATIVE_PERIOD",
        }
    elif period_kind == "BARE_YEAR" and len(distinct_period_keys) == 2:
        ordered_period_keys = sorted(
            distinct_period_keys, key=lambda item: int(item[1]), reverse=True
        )
        lane_role_by_key = {
            ordered_period_keys[0]: "CURRENT_PERIOD",
            ordered_period_keys[1]: "COMPARATIVE_PERIOD",
        }
    elif period_kind == "SEMANTIC_ALIAS" and set(distinct_period_keys) == {
        ("SEMANTIC_ALIAS", "CURRENT_PERIOD"),
        ("SEMANTIC_ALIAS", "COMPARATIVE_PERIOD"),
    }:
        ordered_period_keys = [
            ("SEMANTIC_ALIAS", "CURRENT_PERIOD"),
            ("SEMANTIC_ALIAS", "COMPARATIVE_PERIOD"),
        ]
        lane_role_by_key = {key: key[1] for key in ordered_period_keys}

    metric_by_period: dict[tuple[str, str], dict[str, int]] = defaultdict(dict)
    expected_metrics = set(declaration["metric_aliases"])
    for item, period_key in zip(column_axis, raw_period_keys, strict=True):
        metric = item["metric"]
        if metric is None:
            continue
        if metric in metric_by_period[period_key]:
            reasons.append(
                f"DUPLICATE_MULTI_METRIC_PERIOD_COLUMN:{period_key[0]}:{period_key[1]}:{metric}"
            )
        metric_by_period[period_key][metric] = item["column_ordinal"]
        if period_key in lane_role_by_key and item["semantic_roles"]:
            if item["semantic_roles"] != [lane_role_by_key[period_key]]:
                reasons.append(
                    f"DATE_SEMANTIC_MULTI_METRIC_PERIOD_CONFLICT:c{item['column_ordinal']}"
                )
    for period_key in distinct_period_keys:
        if set(metric_by_period[period_key]) != expected_metrics:
            reasons.append(
                f"MULTI_METRIC_PERIOD_FRONTIER_INCOMPLETE:{period_key[0]}:{period_key[1]}"
            )

    raw_equations = []
    visible_row_count = 0
    if not reasons and ordered_period_keys:
        for row_ordinal, row in enumerate(rows, start=1):
            if type(row) is not dict or type(row.get("values_exact")) is not list:
                continue
            values = row["values_exact"]
            if len(values) != len(columns):
                reasons.append(f"MULTI_METRIC_ROW_WIDTH_MISMATCH:r{row_ordinal}")
                continue
            row_has_visible_value = any(
                values[ordinal - 1] is not None for ordinal in value_ordinals
            )
            if not row_has_visible_value:
                continue
            visible_row_count += 1
            for period_key in ordered_period_keys:
                metric_values = {
                    metric: values[ordinal - 1]
                    for metric, ordinal in metric_by_period[period_key].items()
                }
                if all(value is None for value in metric_values.values()):
                    reasons.append(
                        f"VISIBLE_MULTI_METRIC_ROW_PERIOD_POPULATION_EMPTY:r{row_ordinal}:"
                        f"{period_key[1]}"
                    )
                    continue
                if sum(value is None for value in metric_values.values()) > 1:
                    reasons.append(
                        f"MULTI_METRIC_ROW_PERIOD_HAS_MULTIPLE_UNKNOWNS:r{row_ordinal}:"
                        f"{period_key[1]}"
                    )
                    continue
                parsed = {}
                try:
                    for metric, value in metric_values.items():
                        parsed[metric] = _source_money(value)
                except ValueError:
                    reasons.append(
                        f"MULTI_METRIC_SOURCE_CELL_NOT_EXACT_INTEGER:r{row_ordinal}:{period_key[1]}"
                    )
                    continue
                if any(
                    observed_source_coefficient_v1(cell) is None
                    for cell in parsed.values()
                ):
                    reasons.append(
                        f"MULTI_METRIC_SOURCE_EQUATION_HAS_UNOBSERVED_CELL:"
                        f"r{row_ordinal}:{period_key[1]}"
                    )
                    continue
                component_sum = sum(
                    term["sign"]
                    * observed_source_coefficient_v1(parsed[term["metric"]])
                    for term in declaration["component_terms"]
                )
                result = parsed[declaration["result_metric"]]
                status = (
                    "EXACT"
                    if component_sum == observed_source_coefficient_v1(result)
                    else "MISMATCH"
                )
                if status != "EXACT":
                    reasons.append(
                        f"MULTI_METRIC_SOURCE_EQUATION_MISMATCH:r{row_ordinal}:{period_key[1]}"
                    )
                raw_equations.append(
                    {
                        "component_cells": [
                            {
                                **canonical_clone_v1(parsed[term["metric"]]),
                                "column_ordinal": metric_by_period[period_key][term["metric"]],
                                "metric": term["metric"],
                                "sign": term["sign"],
                            }
                            for term in declaration["component_terms"]
                        ],
                        "component_sum": component_sum,
                        "lane_role": lane_role_by_key[period_key],
                        "result_cell": {
                            **canonical_clone_v1(result),
                            "column_ordinal": metric_by_period[period_key][
                                declaration["result_metric"]
                            ],
                            "metric": declaration["result_metric"],
                        },
                        "row_id": f"r{row_ordinal}",
                        "row_ordinal": row_ordinal,
                        "source_label_exact": row.get("label_exact"),
                        "source_period_key": list(period_key),
                        "status": status,
                    }
                )
    if visible_row_count == 0:
        reasons.append("MULTI_METRIC_VISIBLE_SOURCE_ROW_AXIS_EMPTY")

    result_metric = declaration["result_metric"]
    selected_ordinals = [
        metric_by_period[key][result_metric]
        for key in ordered_period_keys
        if result_metric in metric_by_period[key]
    ]
    return {
        "complete": not reasons and len(selected_ordinals) == 2,
        "lane_keys": (
            [
                ["SEMANTIC_ALIAS", "CURRENT_PERIOD"],
                ["SEMANTIC_ALIAS", "COMPARATIVE_PERIOD"],
            ]
            if not reasons and len(selected_ordinals) == 2
            else []
        ),
        "layout_kind": (
            "TWO_PERIOD_REPEATED_DECLARED_METRIC_COLUMNS_EXACT_EQUATION"
            if not reasons and len(selected_ordinals) == 2
            else None
        ),
        "money_column_ordinals": selected_ordinals,
        "multi_metric_column_axis": column_axis,
        "multi_metric_equation_axis": raw_equations,
        "reasons": sorted(set(reasons)),
        "selected_metric_kinds": (
            [result_metric, result_metric] if not reasons and len(selected_ordinals) == 2 else []
        ),
        "source_lane_keys": (
            [list(key) for key in ordered_period_keys]
            if not reasons and len(selected_ordinals) == 2
            else []
        ),
        "source_period_axis": {
            "column_axis": column_axis,
            "metric_equation": canonical_clone_v1(declaration),
            "rule": (
                "EXACT_TWO_PERIODS_EACH_WITH_COMPLETE_DECLARED_METRIC_FRONTIER_"
                "EVERY_VISIBLE_SOURCE_ROW_EQUATION_EXACT"
            ),
        },
    }


def _multitable_lane_axis(
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    columns = table.get("columns")
    if type(columns) is not list:
        return _table_lane_axis(section, table)
    if "multi_metric_lane_equation" in compiled_specs:
        multi_metric = _declared_multi_metric_lane_axis(
            table,
            declaration=compiled_specs["multi_metric_lane_equation"],
            compiled_specs=compiled_specs,
        )
        if multi_metric is not None:
            return multi_metric
    if compiled_specs["evaluation"]["period_semantics"] == "CURRENT_AND_COMPARATIVE_DURATION":
        return _duration_multitable_lane_axis(table, compiled_specs=compiled_specs)
    money_ordinals = _value_column_ordinals(columns, compiled_specs=compiled_specs)
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


def _adjacent_continuation_lane_axis(
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    region: Mapping[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
    prior_fragment: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Inherit only an explicit, physically adjacent continuation's blank axis.

    The local source columns remain the value locators.  Only their semantic
    period identities come from the immediately preceding fragment, and the
    receipt binds that exact source locator; no header text is fabricated.
    """

    if (
        compiled_specs.get("continuation_period_axis_policy", "LOCAL_PERIOD_AXIS_ONLY")
        != "ADJACENT_PAGE_EXPLICIT_CONTINUATION_INHERITS_COMPLETE_BLANK_HEADER_AXIS"
        or type(prior_fragment) is not dict
        or table.get("continuation") != "CONTINUES_FROM_PREVIOUS_PAGE"
    ):
        return None
    prior_table = prior_fragment.get("table")
    prior_region = prior_fragment.get("region")
    prior_axis = prior_fragment.get("lane_axis")
    if (
        type(prior_table) is not dict
        or prior_table.get("continuation") != "CONTINUES_ON_NEXT_PAGE"
        or type(prior_region) is not dict
        or type(prior_axis) is not dict
        or prior_axis.get("complete") is not True
        or region.get("document_id") != prior_region.get("document_id")
        or region.get("selected_page_ordinal")
        != prior_region.get("selected_page_ordinal", -2) + 1
        or region.get("physical_page") != prior_region.get("physical_page", -2) + 1
    ):
        return None
    columns = table.get("columns")
    if type(columns) is not list:
        return None
    money_ordinals = _value_column_ordinals(columns, compiled_specs=compiled_specs)
    prior_money_ordinals = prior_axis.get("money_column_ordinals")
    lane_keys = prior_axis.get("lane_keys")
    source_lane_keys = prior_axis.get("source_lane_keys", lane_keys)
    if (
        type(prior_money_ordinals) is not list
        or type(lane_keys) is not list
        or type(source_lane_keys) is not list
        or len(money_ordinals) != len(prior_money_ordinals)
        or len(money_ordinals) != len(lane_keys)
        or len(money_ordinals) != len(source_lane_keys)
        or not money_ordinals
    ):
        return None
    local_surfaces = [section.get("title_exact"), table.get("title_exact")]
    local_surfaces.extend(_header_text(columns[ordinal - 1]) for ordinal in money_ordinals)
    if any(
        _normalized(surface)
        and (
            _surface_dates(str(surface))
            or _semantic_period_roles(str(surface))
            or re.search(r"(?<!\d)(?:19|20)\d{2}(?!\d)", str(surface))
        )
        for surface in local_surfaces
    ):
        return None
    if any(_normalized(_header_text(columns[ordinal - 1])) for ordinal in money_ordinals):
        return None
    return {
        "complete": True,
        "lane_keys": canonical_clone_v1(lane_keys),
        "layout_kind": "ADJACENT_PAGE_EXPLICIT_CONTINUATION_BLANK_HEADER_AXIS",
        "money_column_ordinals": money_ordinals,
        "reasons": [],
        "selected_metric_kinds": canonical_clone_v1(
            prior_axis.get("selected_metric_kinds", ["GENERIC_AMOUNT"] * len(money_ordinals))
        ),
        "source_lane_keys": canonical_clone_v1(source_lane_keys),
        "source_period_axis": {
            "inherited_from_locator": canonical_clone_v1(prior_region),
            "local_money_column_ordinals": money_ordinals,
            "prior_source_lane_keys": canonical_clone_v1(source_lane_keys),
            "rule": (
                "EXPLICIT_CONTINUES_FROM_PREVIOUS_PAGE_PLUS_ADJACENT_PRIOR_"
                "CONTINUES_ON_NEXT_PAGE_WITH_COMPLETE_AXIS_AND_ALL_LOCAL_HEADERS_BLANK"
            ),
        },
    }


def _adjacent_numbered_subsection_unit_axis(
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    region: Mapping[str, Any],
    lane_axis: Mapping[str, Any],
    local_unit_axis: Mapping[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
    prior_fragment: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Bind a unitless numbered child to its adjacent explicit owner carrier."""

    if (
        compiled_specs.get("numbered_subsection_unit_axis_policy", "LOCAL_UNIT_AXIS_ONLY")
        != "SAME_PAGE_ADJACENT_EXPLICIT_OWNER_SUBSECTION_INHERITS_UNIT"
        or type(prior_fragment) is not dict
        or local_unit_axis.get("complete") is True
        or local_unit_axis.get("reasons") != ["MONEY_UNIT_NOT_EXACTLY_RESOLVED"]
        or local_unit_axis.get("evidence")
        or local_unit_axis.get("undeclared_evidence")
        or _normalized(table.get("unit_exact"))
    ):
        return None
    prior_region = prior_fragment.get("region")
    prior_table = prior_fragment.get("table")
    prior_section = prior_fragment.get("section")
    prior_lane_axis = prior_fragment.get("lane_axis")
    prior_unit_axis = prior_fragment.get("unit_axis")
    prior_classification = prior_fragment.get("classification")
    if (
        type(prior_region) is not dict
        or type(prior_table) is not dict
        or type(prior_section) is not dict
        or type(prior_lane_axis) is not dict
        or type(prior_unit_axis) is not dict
        or prior_unit_axis.get("complete") is not True
        or type(prior_unit_axis.get("canonical_unit")) is not str
        or type(prior_classification) is not dict
        or prior_classification.get("owner_visible") is not True
        or region.get("document_id") != prior_region.get("document_id")
        or region.get("selected_page_ordinal")
        != prior_region.get("selected_page_ordinal")
        or region.get("physical_page") != prior_region.get("physical_page")
        or lane_axis.get("complete") is not True
        or prior_lane_axis.get("complete") is not True
        or lane_axis.get("lane_keys") != prior_lane_axis.get("lane_keys")
    ):
        return None
    columns = table.get("columns")
    prior_columns = prior_table.get("columns")
    if type(columns) is not list or type(prior_columns) is not list:
        return None
    money_ordinals = _value_column_ordinals(columns, compiled_specs=compiled_specs)
    prior_money_ordinals = _value_column_ordinals(
        prior_columns, compiled_specs=compiled_specs
    )
    if not money_ordinals or len(money_ordinals) != len(prior_money_ordinals):
        return None
    aliases = list(compiled_specs["unit_binding_by_alias"])
    if any(
        _alias_occurrences(_normalized(_header_text(columns[ordinal - 1])), aliases)
        for ordinal in money_ordinals
    ):
        return None

    def fragment_path(
        source_section: Mapping[str, Any], source_table: Mapping[str, Any]
    ) -> tuple[int, ...] | None:
        return _outline_number_path(source_table.get("title_exact")) or _outline_number_path(
            source_section.get("title_exact")
        )

    prior_path = fragment_path(prior_section, prior_table)
    current_path = fragment_path(section, table)
    if (
        prior_path is None
        or current_path is None
        or len(current_path) <= len(prior_path)
        or current_path[: len(prior_path)] != prior_path
    ):
        return None
    inherited_receipt = {
        "current_outline_path": list(current_path),
        "inherited_from_locator": canonical_clone_v1(prior_region),
        "prior_outline_path": list(prior_path),
        "prior_unit_axis_evidence": canonical_clone_v1(
            prior_unit_axis.get("evidence", [])
        ),
        "rule": (
            "IMMEDIATELY_PRECEDING_SAME_PAGE_EXPLICIT_OWNER_NUMBERED_PARENT_"
            "WITH_COMPLETE_UNIT_AND_PERIOD_AXIS_SCOPES_STRICT_NUMBERED_SUBSECTION"
        ),
    }
    return {
        "canonical_unit": prior_unit_axis["canonical_unit"],
        "complete": True,
        "document_unit_context_evidence": inherited_receipt,
        "evidence": canonical_clone_v1(prior_unit_axis.get("evidence", [])),
        "reasons": [],
        "source": "ADJACENT_EXPLICIT_OWNER_NUMBERED_PARENT_UNIT",
        "undeclared_evidence": [],
    }


def _adjacent_continuation_unit_axis(
    table: Mapping[str, Any],
    region: Mapping[str, Any],
    lane_axis: Mapping[str, Any],
    local_unit_axis: Mapping[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
    prior_fragment: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Carry the unit of the same explicit adjacent continued table."""

    if (
        compiled_specs.get("continuation_period_axis_policy", "LOCAL_PERIOD_AXIS_ONLY")
        != "ADJACENT_PAGE_EXPLICIT_CONTINUATION_INHERITS_COMPLETE_BLANK_HEADER_AXIS"
        or lane_axis.get("layout_kind")
        != "ADJACENT_PAGE_EXPLICIT_CONTINUATION_BLANK_HEADER_AXIS"
        or type(prior_fragment) is not dict
        or table.get("continuation") != "CONTINUES_FROM_PREVIOUS_PAGE"
        or local_unit_axis.get("complete") is True
        or local_unit_axis.get("reasons") != ["MONEY_UNIT_NOT_EXACTLY_RESOLVED"]
        or local_unit_axis.get("evidence")
        or local_unit_axis.get("undeclared_evidence")
        or _normalized(table.get("unit_exact"))
    ):
        return None
    prior_table = prior_fragment.get("table")
    prior_region = prior_fragment.get("region")
    prior_unit_axis = prior_fragment.get("unit_axis")
    if (
        type(prior_table) is not dict
        or prior_table.get("continuation") != "CONTINUES_ON_NEXT_PAGE"
        or type(prior_region) is not dict
        or type(prior_unit_axis) is not dict
        or prior_unit_axis.get("complete") is not True
        or region.get("document_id") != prior_region.get("document_id")
        or region.get("selected_page_ordinal")
        != prior_region.get("selected_page_ordinal", -2) + 1
        or region.get("physical_page") != prior_region.get("physical_page", -2) + 1
    ):
        return None
    return {
        "canonical_unit": prior_unit_axis["canonical_unit"],
        "complete": True,
        "document_unit_context_evidence": {
            "inherited_from_locator": canonical_clone_v1(prior_region),
            "rule": (
                "SAME_EXPLICIT_PHYSICALLY_AND_SELECTED_ADJACENT_CONTINUATION_"
                "INHERITS_COMPLETE_PRIOR_UNIT_WITH_BLANK_LOCAL_UNIT_SURFACES"
            ),
        },
        "evidence": canonical_clone_v1(prior_unit_axis.get("evidence", [])),
        "reasons": [],
        "source": "ADJACENT_EXPLICIT_CONTINUATION_UNIT",
        "undeclared_evidence": [],
    }


def _materialize_multi_metric_source_equations(
    lane_axis: Mapping[str, Any],
    *,
    region: Mapping[str, Any],
    rows: Sequence[Any],
) -> list[dict[str, Any]]:
    equations = []
    for raw in lane_axis.get("multi_metric_equation_axis", []):
        row_ordinal = raw["row_ordinal"]
        row = rows[row_ordinal - 1]

        def source_ref(
            column_ordinal: int,
            row: Mapping[str, Any] = row,
            raw: Mapping[str, Any] = raw,
            row_ordinal: int = row_ordinal,
        ) -> dict[str, Any]:
            return {
                "column_ordinal": column_ordinal,
                "hierarchy_path_exact": canonical_clone_v1(row.get("hierarchy_path_exact")),
                "label_exact": row.get("label_exact"),
                "locator": canonical_clone_v1(region),
                "money_column_ordinals": [column_ordinal],
                "row_id": raw["row_id"],
                "row_kind": row.get("row_kind"),
                "row_ordinal": row_ordinal,
            }

        component_refs = [[source_ref(cell["column_ordinal"])] for cell in raw["component_cells"]]
        result_ref = source_ref(raw["result_cell"]["column_ordinal"])
        material = {
            "component_roles": [
                "SOURCE_METRIC_" + cell["metric"] for cell in raw["component_cells"]
            ],
            "component_source_refs": component_refs,
            "component_sums": [raw["component_sum"]],
            "equation_kind": (
                "EXACT_DECLARED_SOURCE_MULTI_METRIC_ROW_EQUATION_SELECTS_RESULT_LANE"
            ),
            "lane_keys": [["SEMANTIC_ALIAS", raw["lane_role"]]],
            "multipliers": [cell["sign"] for cell in raw["component_cells"]],
            "result_coefficients": [raw["result_cell"]["coefficient"]],
            "result_role": "SOURCE_METRIC_" + raw["result_cell"]["metric"],
            "result_source_refs": [result_ref],
            "source_metric_receipt": canonical_clone_v1(raw),
            "status": raw["status"],
        }
        equations.append(
            {
                **material,
                "equation_id": "gjmthfev1:equation:" + canonical_json_sha256_v1(material),
            }
        )
    return equations


def _path_contains_label(row: Mapping[str, Any], label: str) -> bool:
    return bool(
        label
        and any(
            _normalized(value) == label
            or any(_normalized(line) == label for line in value.splitlines())
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


def _observed_lane_control_equation(
    *, kind: str, components: Sequence[Mapping[str, Any]], result: Mapping[str, Any]
) -> dict[str, Any] | None:
    """Validate a source control independently on each observed lane.

    A printed subtotal or total remains useful structural evidence when every
    fully observed lane closes and another lane has a genuine source blank.
    The blank lane stays explicitly incomplete: it cannot prove, infer, round,
    or veto anything. A mismatch on any observed lane, an all-incomplete
    equation, or incompatible lane axes remains unusable.
    """

    if not components or not _same_lane_axis([*components, result]):
        return None
    equation = _local_equation(
        equation_kind=kind,
        components=components,
        result=result,
    )
    return equation if _is_observed_lane_control_equation(equation) else None


def _is_observed_lane_control_equation(equation: Mapping[str, Any]) -> bool:
    if _is_complete_source_control_equation(equation):
        return True
    lane_statuses = equation.get("lane_statuses", [])
    return bool(
        equation.get("status") == "INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL"
        and "EXACT" in lane_statuses
        and set(lane_statuses) <= {"EXACT", "INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL"}
    )


def _is_complete_source_control_equation(equation: Mapping[str, Any]) -> bool:
    return equation.get("status") in {
        "EXACT",
        "SOURCE_PRESENTATION_ROUNDING_INTERVAL_EXACT",
    }


def _source_presentation_rounding_equation(
    *,
    kind: str,
    components: Sequence[Mapping[str, Any]],
    result: Mapping[str, Any],
    canonical_unit: str | None,
    magnitude_power10: int | None,
    multipliers: Sequence[int] | None = None,
) -> dict[str, Any] | None:
    """Accept one display-unit residual only on a complete scaled source axis.

    Independent values printed in a scaled presentation can each be rounded,
    so a directly selected source frontier may differ from its printed result
    by one display unit. This primitive never repairs a cell: all operands and
    results must be observed, VND is excluded, and the receipt preserves the
    exact expected/observed residual for every lane.
    """

    if (
        not components
        or not _same_lane_axis([*components, result])
        or type(magnitude_power10) is not int
        or magnitude_power10 < 3
        or canonical_unit == "VND"
        or any(
            observed_source_coefficient_v1(cell) is None
            for record in [*components, result]
            for cell in record["cells"]
        )
    ):
        return None
    equation = _local_equation(
        equation_kind=kind,
        components=components,
        result=result,
        multipliers=multipliers,
    )
    if equation["status"] == "EXACT":
        return equation
    if equation["status"] != "MISMATCH":
        return None
    lane_receipts = []
    for lane_key, expected, observed in zip(
        equation["lane_keys"],
        equation["component_sums"],
        equation["result_coefficients"],
        strict=True,
    ):
        if type(expected) is not int or type(observed) is not int:
            return None
        residual = observed - expected
        if abs(residual) > 1:
            return None
        lane_receipts.append(
            {
                "expected_component_sum": expected,
                "lane_key": canonical_clone_v1(lane_key),
                "observed_result": observed,
                "residual": residual,
            }
        )
    if not any(item["residual"] for item in lane_receipts):
        return None
    material = {
        key: canonical_clone_v1(value)
        for key, value in equation.items()
        if key != "equation_id"
    }
    material["status"] = "SOURCE_PRESENTATION_ROUNDING_INTERVAL_EXACT"
    material["source_presentation_rounding_receipt"] = {
        "canonical_unit": canonical_unit,
        "lane_receipts": lane_receipts,
        "magnitude_power10": magnitude_power10,
        "maximum_absolute_display_unit_residual": 1,
        "rule": "INDEPENDENT_DISPLAY_UNIT_ROUNDING_INTERVAL_ALL_EQUATIONS",
    }
    return {
        **material,
        "equation_id": "gjmthfev1:equation:" + canonical_json_sha256_v1(material),
    }


def _supplemental_detail_population_key(
    source_refs: Sequence[Mapping[str, Any]],
    *,
    role: str,
    compiled_specs: Mapping[str, Any],
) -> tuple[str, tuple[str, str, str]] | None:
    """Bind rows to one explicit, non-exhaustive source detail population.

    A source marker such as ``Trong đó``/``Of which`` is disclosure scope, not
    an additive equation.  A configured residual leaf may collect distinct
    rows from that scope, but only when every source ref is a direct child of
    the same marker in the same table.  This never promotes an unscoped or
    top-level unknown row.
    """

    declarations = [
        item
        for item in compiled_specs["supplemental_detail_residuals"]
        if item["residual_role"] == role
    ]
    if len(declarations) != 1 or not source_refs:
        return None
    markers = set(declarations[0]["markers"])
    keys = set()
    for source_ref in source_refs:
        path = [
            _normalized(value)
            for value in source_ref.get("hierarchy_path_exact", [])
            if _normalized(value)
        ]
        label = _normalized(source_ref.get("label_exact"))
        locator = source_ref.get("locator")
        if (
            len(path) != 2
            or path[0] not in markers
            or not label
            or path[1] != label
            or type(locator) is not dict
        ):
            return None
        keys.add(
            (
                path[0],
                (
                    locator["page_json_version_id"],
                    locator["section_id"],
                    locator["table_id"],
                ),
            )
        )
    return next(iter(keys)) if len(keys) == 1 else None


def _supplemental_residual_population_receipt(
    occurrences: Sequence[Mapping[str, Any]],
    *,
    role: str,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    source_refs = [
        source_ref for occurrence in occurrences for source_ref in occurrence["source_refs"]
    ]
    key = _supplemental_detail_population_key(source_refs, role=role, compiled_specs=compiled_specs)
    if key is None or len({ref["row_id"] for ref in source_refs}) != len(source_refs):
        return None
    marker, table_key = key
    return {
        "marker": marker,
        "role": role,
        "rule": (
            "ONE_EXPLICIT_NONEXHAUSTIVE_DETAIL_POPULATION_DIRECT_CHILD_ROWS_"
            "TO_DECLARED_RESIDUAL_NO_PARENT_OR_ROOT_ADDITION"
        ),
        "source_refs": canonical_clone_v1(source_refs),
        "source_table_key": list(table_key),
    }


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
        observed_occurrences = [
            occurrence
            for occurrence in occurrences
            if _record_has_observed_lane(occurrence)
        ]
        all_blank_occurrences = [
            occurrence
            for occurrence in occurrences
            if not _record_has_observed_lane(occurrence)
        ]
        if not observed_occurrences:
            output.extend(canonical_clone_v1(occurrences))
            continue
        supplemental_receipt = _supplemental_residual_population_receipt(
            observed_occurrences, role=role, compiled_specs=compiled_specs
        )
        if (
            compiled_specs["duplicate_role_aggregation_policy"]
            == ("ALL_SOURCE_ROWS_CONSUMED_BY_EXACT_TABLE_FRONTIER")
            and any(
                source_ref.get("row_ordinal") not in consumed_ordinals
                for occurrence in observed_occurrences
                for source_ref in occurrence["source_refs"]
            )
            and supplemental_receipt is None
        ):
            output.extend(canonical_clone_v1(occurrences))
            continue
        if len(observed_occurrences) == 1:
            output.append(canonical_clone_v1(observed_occurrences[0]))
            receipts.append(
                {
                    "coefficients": _coefficients(observed_occurrences[0]),
                    "omitted_all_blank_source_refs": [
                        canonical_clone_v1(source_ref)
                        for occurrence in all_blank_occurrences
                        for source_ref in occurrence["source_refs"]
                    ],
                    "role": role,
                    "rule": (
                        "ALL_BLANK_DUPLICATE_OCCURRENCES_OMITTED_WHILE_"
                        "OBSERVED_SOURCE_OCCURRENCE_IS_PRESERVED"
                    ),
                    "source_refs": canonical_clone_v1(
                        observed_occurrences[0]["source_refs"]
                    ),
                }
            )
            continue
        lane_keys = canonical_clone_v1(observed_occurrences[0]["lane_keys"])
        coefficients = _sum_records(observed_occurrences)
        cells = _sum_record_cells(
            observed_occurrences,
            exact_state="EXACT_SAME_ROLE_SOURCE_ROW_SUM",
        )
        source_refs = [
            source_ref
            for occurrence in observed_occurrences
            for source_ref in occurrence["source_refs"]
        ]
        output.append(
            _local_record(
                role,
                cells,
                lane_keys,
                source_refs,
                (
                    "SOURCE_SUPPLEMENTAL_DETAIL_RESIDUAL_ROWS_AGGREGATED"
                    if supplemental_receipt is not None
                    else "SOURCE_SAME_ROLE_ROWS_AGGREGATED_AFTER_TABLE_CLOSURE"
                ),
                observed_occurrences[0]["valuation_basis"],
            )
        )
        receipt = {
            "coefficients": coefficients,
            "role": role,
            "rule": (
                supplemental_receipt["rule"]
                if supplemental_receipt is not None
                else "SAME_ROLE_ROWS_SUM_ONLY_AFTER_SHARED_TABLE_FRONTIER_EXACT"
            ),
            "source_refs": canonical_clone_v1(source_refs),
        }
        if supplemental_receipt is not None:
            receipt["supplemental_detail_population"] = supplemental_receipt
        if all_blank_occurrences:
            receipt["omitted_all_blank_source_refs"] = [
                canonical_clone_v1(source_ref)
                for occurrence in all_blank_occurrences
                for source_ref in occurrence["source_refs"]
            ]
        receipts.append(receipt)
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

    receipts = []
    residual_roles = {
        declaration["residual_role"]
        for declaration in compiled_specs["supplemental_detail_residuals"]
    }
    if compiled_specs["equation_consumed_unmatched_residual_role"] is not None:
        residual_roles.add(compiled_specs["equation_consumed_unmatched_residual_role"])

    # A table-context total is structural, not another additive residual leaf.
    # Remove it before grouping duplicate roles so that genuine residual leaves
    # disclosed in two or more other tables can still be combined.  Performing
    # this after aggregation makes the structural record poison the whole role
    # group and leaves the remaining explicit populations unresolved.
    suppressed_record_ids = set()
    for role in residual_roles:
        role_records = [record for record in records if record["role"] == role]
        explicit_records = [
            record for record in role_records if "CONTEXT_ROLE" not in record["state"]
        ]
        for context in role_records:
            if "CONTEXT_ROLE" not in context["state"] or not any(
                explicit["lane_keys"] == context["lane_keys"]
                and explicit["valuation_basis"] == context["valuation_basis"]
                for explicit in explicit_records
            ):
                continue
            suppressed_record_ids.add(id(context))
            receipts.append(
                {
                    "context_role": role,
                    "detail_source_refs": canonical_clone_v1(context["source_refs"]),
                    "explicit_residual_source_refs": [
                        canonical_clone_v1(explicit["source_refs"]) for explicit in explicit_records
                    ],
                    "rule": (
                        "STRUCTURAL_CONTEXT_TOTAL_IS_NOT_A_RESIDUAL_LEAF_WHEN_"
                        "EXPLICIT_RESIDUAL_SOURCE_ROWS_EXIST_ON_THE_SAME_LANE_AXIS"
                    ),
                }
            )

    by_role: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        if id(record) not in suppressed_record_ids:
            by_role[record["role"]].append(record)
    output = []
    aggregatable_states = {
        "SOURCE_EQUATION_CONSUMED_UNMATCHED_ROW_PROJECTED_TO_RESIDUAL",
        "SOURCE_OBSERVED_ROLE_ROW",
        "SOURCE_SAME_ROLE_ROWS_AGGREGATED_AFTER_TABLE_CLOSURE",
        "SOURCE_SUPPLEMENTAL_DETAIL_RESIDUAL_ROWS_AGGREGATED",
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
            cells = _sum_record_cells(
                occurrences,
                exact_state="EXACT_DISTINCT_TABLE_ROLE_SUM",
            )
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
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[str],
]:
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
    reasons = []
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
            if any(
                len(component_populations[role].get(key, [])) != 1
                for role in declaration["component_roles"]
            ):
                continue
            components = [
                component_populations[role][key][0] for role in declaration["component_roles"]
            ]
            source_results = result_populations.get(key, [])
            if source_results:
                if len(source_results) != 1:
                    # Duplicate-source handling is sealed independently by the
                    # exhaustive role aggregation gate below.
                    continue
                source_result = source_results[0]
                equation = _exact_equation(
                    kind="EXACT_DECLARED_SOURCE_RESULT_EQUALS_VISIBLE_COMPONENT_SUM",
                    components=components,
                    result=source_result,
                )
                if equation is None:
                    reasons.append(
                        f"DECLARED_SOURCE_RESULT_COMPONENT_EQUATION_MISMATCH:{result_role}"
                    )
                    continue
                equations.append(equation)
                receipts.append(
                    {
                        "coefficients": _coefficients(source_result),
                        "component_roles": canonical_clone_v1(declaration["component_roles"]),
                        "result_role": result_role,
                        "result_source_refs": canonical_clone_v1(source_result["source_refs"]),
                        "rule": "SOURCE_VISIBLE_DECLARED_RESULT_EQUALS_DIRECT_COMPONENT_SUM",
                        "source_refs": [
                            source_ref
                            for component in components
                            for source_ref in canonical_clone_v1(component["source_refs"])
                        ],
                    }
                )
                continue
            coefficients = _sum_records(components)
            cells = _sum_record_cells(
                components,
                exact_state="EXACT_DECLARED_SOURCE_COMPONENT_SUM",
            )
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
    return output, equations, receipts, sorted(set(reasons))


def _derive_complete_top_level_family_root(
    records: Sequence[Mapping[str, Any]],
    *,
    proven_roles: set[str],
    source_only_axis: Sequence[Mapping[str, Any]],
    source_equations: Sequence[Mapping[str, Any]],
    source_result_component_evidence_roles: set[str],
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
    root_mapping_policy = compiled_specs["schema"]["root_mapping_policy"]
    if root_mapping_policy == (
        "SOURCE_VISIBLE_EXACT_RESULT_WITH_OPTIONAL_COMPLETE_COMPONENT_EQUATION_VETO"
    ):
        existing_roots = [record for record in output if record["role"] == "FAMILY_ROOT_TOTAL"]
        if len(existing_roots) != 1:
            return (
                output,
                [],
                [],
                ["EXACT_SOURCE_RESULT_ROW_" + ("ABSENT" if not existing_roots else "NOT_UNIQUE")],
            )
        root = existing_roots[0]
        component_records = [record for record in output if record["role"] != "FAMILY_ROOT_TOTAL"]
        if not source_result_component_evidence_roles:
            if any(
                cell["source_text"] is None or cell["state"].endswith("_IF_EQUATION_EXACT")
                for cell in root["cells"]
            ):
                return output, [], [], ["EXACT_SOURCE_RESULT_ROW_HAS_UNPROVEN_BLANK"]
            root["state"] = "SOURCE_VISIBLE_EXACT_RESULT_ROW_WITHOUT_COMPONENT_EVIDENCE"
            # Context-only or unrelated records may coexist in the same source
            # table, but without a declared component hit they are not part of
            # this result's authenticated graph and must not leak into mapping.
            output = [root]
            return (
                output,
                [],
                [
                    {
                        "coefficients": _coefficients(root),
                        "component_roles": [],
                        "result_role": "FAMILY_ROOT_TOTAL",
                        "rule": (
                            "SOURCE_VISIBLE_EXACT_RESULT_ROW_MAPS_DIRECTLY_WHEN_NO_"
                            "DECLARED_COMPONENT_EVIDENCE_IS_PRESENT"
                        ),
                        "source_refs": canonical_clone_v1(root["source_refs"]),
                    }
                ],
                [],
            )

        by_role: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for record in component_records:
            by_role[record["role"]].append(record)
        components = []
        for role in compiled_specs["root_component_roles"]:
            matches = by_role.get(role, [])
            if len(matches) != 1 or role not in proven_roles:
                return (
                    output,
                    [],
                    [],
                    ["SOURCE_RESULT_DECLARED_COMPONENT_POPULATION_NOT_EXACT:" + role],
                )
            components.append(matches[0])
        equation = _exact_equation(
            kind="EXACT_SOURCE_RESULT_EQUALS_COMPLETE_DECLARED_ROOT_COMPONENTS",
            components=components,
            result=root,
        )
        if equation is None:
            return output, [], [], ["SOURCE_RESULT_DECLARED_COMPONENT_EQUATION_MISMATCH"]
        root["state"] = "SOURCE_VISIBLE_EXACT_RESULT_VALIDATED_BY_COMPLETE_COMPONENT_EQUATION"
        return (
            output,
            [equation],
            [
                {
                    "coefficients": _coefficients(root),
                    "component_roles": canonical_clone_v1(compiled_specs["root_component_roles"]),
                    "result_role": "FAMILY_ROOT_TOTAL",
                    "rule": (
                        "SOURCE_VISIBLE_EXACT_RESULT_ROW_IS_VETOED_BY_COMPLETE_DECLARED_"
                        "COMPONENT_EQUATION_WHEN_COMPONENT_EVIDENCE_IS_PRESENT"
                    ),
                    "source_equation_id": equation["equation_id"],
                    "source_refs": canonical_clone_v1(root["source_refs"]),
                }
            ],
            [],
        )
    if root_mapping_policy != "SOURCE_VISIBLE_TOTAL_OR_COMPLETE_TOP_LEVEL_COMPONENT_SUM":
        return output, [], [], []

    root_roles = set(compiled_specs["root_component_roles"])
    declared_equation_parent_by_component: dict[str, set[str]] = defaultdict(set)
    for declaration in compiled_specs["derived_role_equations"]:
        for component_role in declaration["component_roles"]:
            declared_equation_parent_by_component[component_role].add(declaration["result_role"])

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
            # Some sources print two independent structural populations whose
            # declared sum forms a wider parent (for example demand + term =
            # total deposits).  That additive edge is part of the compiled
            # graph even when row aliases have no ``within_role`` relation.
            pending.extend(declared_equation_parent_by_component.get(current, set()))
        return False

    validation_only_source_roles = set(compiled_specs["child_by_role"]) - set(
        compiled_specs["bindings"]
    )

    def is_declared_source_row(source_only: Mapping[str, Any]) -> bool:
        source_ref = source_only["source_ref"]
        if source_only.get("declared_role") in compiled_specs["child_by_role"]:
            return True
        if source_only.get("declared_validation_role") in validation_only_source_roles:
            return True
        # Reuse the exact source-row classifier instead of comparing folded
        # strings a second, narrower way.  The shared classifier safely
        # handles source-visible outline ordinals, ``Trong đó`` wrappers and
        # bounded note-reference suffixes.  Otherwise a row can be correctly
        # classified as a declared validation-only role during extraction but
        # later be falsely reported as an unmapped top-level row merely due to
        # presentation syntax.
        surfaces = {
            _normalized(source_ref.get("label_exact")),
            *{
                _normalized(value)
                for value in source_ref.get("hierarchy_path_exact", [])
                if _normalized(value)
            },
        }
        fallback_scopes = [
            None,
            *[
                role
                for role in source_ref.get("locator", {}).get("component_roles", [])
                if role in compiled_specs["child_by_role"]
            ],
        ]
        matched_roles = {
            role
            for role in compiled_specs["child_by_role"]
            if any(
                surface in set(compiled_specs["aliases_by_role"][role])
                for surface in surfaces
                if surface
            )
        }
        for scope in fallback_scopes:
            try:
                matched_roles.update(
                    _row_role_match_modes(
                        source_ref,
                        topology=compiled_specs["topology"],
                        aliases_by_role=compiled_specs["aliases_by_role"],
                        fallback_within_role=scope,
                        enable_declared_equivalences=True,
                    )
                )
            except ValueError:
                # One incompatible fallback scope cannot invalidate an exact
                # source alias or another uniquely scoped classification.
                continue
        label = _normalized(source_ref.get("label_exact"))
        label_without_outline = re.sub(r"^(?:[ivxlcdm]+|[0-9]+)\s+", "", label)
        parent_visible = any(
            label_without_outline == alias or alias in surfaces
            for alias in compiled_specs["topology"]["parent"]["aliases"]
        )
        return bool(
            parent_visible
            or len(matched_roles & validation_only_source_roles) == 1
            or (source_ref.get("label_exact") is None and len(matched_roles) == 1)
        )

    unresolved_top_level_source_only = [
        source_only
        for source_only in source_only_axis
        if compiled_specs["equation_consumed_unmatched_residual_role"] is None
        if source_only["source_ref"].get("row_kind") != "GROUP"
        and not (
            source_only.get("consumed_by_exact_equation")
            and source_only["source_ref"].get("row_kind") in {"SUBTOTAL", "TOTAL"}
        )
        if len(
            [
                value
                for value in source_only["source_ref"].get("hierarchy_path_exact", [])
                if _normalized(value)
            ]
        )
        <= 1
        and not (
            source_only.get("declared_validation_role") in compiled_specs["child_by_role"]
            and compiled_specs["child_by_role"][source_only["declared_validation_role"]][
                "role_kind"
            ]
            == "NONADDITIVE_CHILD"
        )
        and not (
            source_only.get("consumed_by_exact_equation") and is_declared_source_row(source_only)
        )
    ]
    if unresolved_top_level_source_only:
        return (
            output,
            [],
            [],
            ["UNMAPPED_TOP_LEVEL_SOURCE_ONLY_ROW_NOT_DECLARED_VALIDATION_ROLE"],
        )

    existing_roots = [record for record in output if record["role"] == "FAMILY_ROOT_TOTAL"]
    if existing_roots:
        if (
            len(existing_roots) == 1
            and len(output) == 1
            and existing_roots[0]["state"] == "SOURCE_VISIBLE_EXACT_FAMILY_ROOT_ONLY_ROW"
            and not source_result_component_evidence_roles
            and not source_only_axis
        ):
            # One owner-fenced table containing exactly one source-visible
            # family-root row is already the complete source population.  A
            # self-equation would be tautological and supplies no additional
            # accounting evidence, so preserve the source row directly.
            root = existing_roots[0]
            return (
                output,
                [],
                [
                    {
                        "coefficients": _coefficients(root),
                        "component_roles": [],
                        "result_role": "FAMILY_ROOT_TOTAL",
                        "rule": "SOLE_SOURCE_VISIBLE_FAMILY_ROOT_ROW_NO_SELF_EQUATION",
                        "source_refs": canonical_clone_v1(root["source_refs"]),
                    }
                ],
                [],
            )

        def source_identity_axis(source_refs: Sequence[Mapping[str, Any]]) -> set[tuple[str, ...]]:
            return {
                (
                    source_ref["locator"]["page_json_version_id"],
                    source_ref["locator"]["section_id"],
                    source_ref["locator"]["table_id"],
                    source_ref["row_id"],
                    canonical_json_sha256_v1(source_ref.get("money_column_ordinals", [])),
                )
                for source_ref in source_refs
            }

        root_population_keys = [
            (canonical_json_sha256_v1(root["lane_keys"]), root["valuation_basis"])
            for root in existing_roots
        ]
        signed_policy = (
            compiled_specs["root_component_equation_policy"]
            == "UNIQUE_DECLARED_SIGN_ORIENTATION_FIRST_COMPONENT_POSITIVE"
        )
        if not signed_policy and len(set(root_population_keys)) != len(root_population_keys):
            return output, [], [], ["FAMILY_ROOT_SOURCE_POPULATION_IS_AMBIGUOUS"]

        equation_by_root_population = []
        for root in existing_roots:
            root_result_axis = source_identity_axis(root["source_refs"])
            root_equations = [
                equation
                for equation in source_equations
                if _is_observed_lane_control_equation(equation)
                and source_identity_axis(equation.get("result_source_refs", [])) == root_result_axis
                and equation.get("result_coefficients") == _coefficients(root)
            ]
            deferred_document_result = bool(
                signed_policy
                and root.get("state")
                == "SOURCE_VISIBLE_FAMILY_ROOT_DEFERRED_TO_DOCUMENT_COMPONENT_CLOSURE"
            )
            if not root_equations and deferred_document_result:
                equation_by_root_population.append((root, None))
                continue
            if len(root_equations) != 1:
                return output, [], [], ["FAMILY_ROOT_SOURCE_EQUATION_IS_NOT_UNIQUE"]
            equation_by_root_population.append((root, root_equations[0]))
        reconciled_roots = []
        for key in dict.fromkeys(root_population_keys):
            population = [
                root
                for root, root_key in zip(existing_roots, root_population_keys, strict=True)
                if root_key == key
            ]
            if len({tuple(_coefficients(root)) for root in population}) != 1:
                return output, [], [], ["FAMILY_ROOT_CORROBORATING_SOURCE_VALUES_CONFLICT"]
            selected = canonical_clone_v1(population[0])
            if len(population) > 1:
                selected["source_refs"] = [
                    source_ref for root in population for source_ref in root["source_refs"]
                ]
                selected["state"] = "CORROBORATED_SOURCE_VISIBLE_FAMILY_ROOT_PRESENTATIONS"
            reconciled_roots.append(selected)
        if signed_policy:
            output = [record for record in output if record["role"] != "FAMILY_ROOT_TOTAL"]
            output.extend(reconciled_roots)

        equation_result_axes = [
            source_identity_axis(equation.get("result_source_refs", []))
            for equation in source_equations
            if _is_observed_lane_control_equation(equation)
        ]
        equation_component_axes = [
            source_identity_axis(component_source_refs)
            for equation in source_equations
            if _is_complete_source_control_equation(equation)
            for component_source_refs in equation.get("component_source_refs", [])
        ]
        allow_root_component_equation = compiled_specs["mapped_source_subtotal_policy"] in {
            "ALLOW_SOURCE_VISIBLE_ROOT_COMPONENT_CONSUMED_BY_EXACT_ROOT_EQUATION",
            (
                "ALLOW_SOURCE_VISIBLE_DECLARED_ROLE_WITH_NONADDITIVE_CHILDREN_OR_"
                "ROOT_COMPONENT_EQUATION"
            ),
        }
        allow_nonadditive_child_disclosure = compiled_specs["mapped_source_subtotal_policy"] == (
            "ALLOW_SOURCE_VISIBLE_DECLARED_ROLE_WITH_NONADDITIVE_CHILDREN_OR_"
            "ROOT_COMPONENT_EQUATION"
        )

        def declared_children(role: str) -> set[str]:
            return {
                child_role
                for child_role, matchers in compiled_specs["matchers_by_role"].items()
                if any(matcher["within_role"] == role for matcher in matchers)
            }

        def only_nonadditive_children(role: str) -> bool:
            children = declared_children(role)
            return bool(children) and all(
                compiled_specs["child_by_role"][child]["role_kind"] == "NONADDITIVE_CHILD"
                for child in children
            )

        independently_proven_subtotal_records = [
            record
            for record in output
            if record["state"] == "SOURCE_OBSERVED_ROLE_ROW"
            and any(
                source_ref.get("row_kind") in {"GROUP", "SUBTOTAL", "TOTAL"}
                for source_ref in record["source_refs"]
            )
            and (
                (
                    allow_root_component_equation
                    and record["role"] in set(compiled_specs["root_component_roles"])
                    and any(
                        source_identity_axis(record["source_refs"]) == component_axis
                        for component_axis in equation_component_axes
                    )
                )
                or (
                    allow_nonadditive_child_disclosure and only_nonadditive_children(record["role"])
                )
            )
        ]
        independently_proven_subtotal_axes = {
            frozenset(source_identity_axis(record["source_refs"]))
            for record in independently_proven_subtotal_records
        }
        unproven_subtotal_roles = sorted(
            {
                record["role"]
                for record in output
                if record["role"] != "FAMILY_ROOT_TOTAL"
                and record["state"] == "SOURCE_OBSERVED_ROLE_ROW"
                and any(
                    source_ref.get("row_kind") in {"GROUP", "SUBTOTAL", "TOTAL"}
                    for source_ref in record["source_refs"]
                )
                and not any(
                    source_identity_axis(record["source_refs"]) == result_axis
                    for result_axis in equation_result_axes
                )
                and frozenset(source_identity_axis(record["source_refs"]))
                not in independently_proven_subtotal_axes
            }
        )
        if unproven_subtotal_roles:
            return (
                output,
                [],
                [],
                [
                    "MAPPED_SOURCE_SUBTOTAL_NOT_PROVEN_BY_EXACT_DIRECT_FRONTIER:" + role
                    for role in unproven_subtotal_roles
                ],
            )
        receipts = [
            {
                "coefficients": canonical_clone_v1(source_equation["result_coefficients"]),
                "component_source_refs": canonical_clone_v1(
                    source_equation["component_source_refs"]
                ),
                "result_state": (
                    "SOURCE_VISIBLE_FAMILY_ROOT_BOUND_TO_UNIQUE_EXACT_TABLE_FRONTIER"
                    if source_equation["status"] == "EXACT"
                    else (
                        "SOURCE_VISIBLE_FAMILY_ROOT_BOUND_TO_DISPLAY_UNIT_"
                        "ROUNDING_INTERVAL_TABLE_FRONTIER"
                        if source_equation["status"]
                        == "SOURCE_PRESENTATION_ROUNDING_INTERVAL_EXACT"
                        else "SOURCE_VISIBLE_FAMILY_ROOT_BOUND_TO_OBSERVED_LANES_"
                        "EXACT_REMAINDER_BLANK_TABLE_FRONTIER"
                    )
                ),
                "rule": (
                    "SOURCE_VISIBLE_FAMILY_ROOT_USES_UNIQUE_TABLE_LOCAL_DIRECT_"
                    "FRONTIER_EACH_BLANK_LANE_REMAINS_INCOMPLETE_DISCLOSURE_"
                    "MAPPINGS_ARE_NOT_ASSUMED_ADDITIVE"
                ),
                "source_equation_id": source_equation["equation_id"],
                "source_refs": canonical_clone_v1(root["source_refs"]),
            }
            for root, source_equation in equation_by_root_population
            if source_equation is not None
        ]
        receipts.extend(
            {
                "coefficients": _coefficients(record),
                "component_roles": [record["role"]],
                "result_role": record["role"],
                "rule": (
                    "SOURCE_VISIBLE_ROLE_WITH_ONLY_DECLARED_NONADDITIVE_CHILDREN_"
                    "IS_INDEPENDENTLY_MAPPABLE_DISCLOSED_SUBSETS_ARE_NOT_EXHAUSTIVE"
                    if only_nonadditive_children(record["role"])
                    else (
                        "SOURCE_VISIBLE_STRUCTURAL_ROOT_COMPONENT_IS_INDEPENDENTLY_"
                        "MAPPABLE_AFTER_EXACT_FAMILY_ROOT_EQUATION_CONSUMPTION_"
                        "DISCLOSED_DESCENDANTS_ARE_NOT_ASSUMED_EXHAUSTIVE"
                    )
                ),
                "source_refs": canonical_clone_v1(record["source_refs"]),
            }
            for record in independently_proven_subtotal_records
        )
        if compiled_specs.get("root_component_role_combinations"):
            if len(reconciled_roots) != 1:
                return (
                    output,
                    [],
                    receipts,
                    ["FAMILY_ROOT_ALTERNATIVE_SOURCE_POPULATION_IS_NOT_UNIQUE"],
                )
            root = reconciled_roots[0]
            complete_alternatives = []
            for declaration in compiled_specs["root_component_role_combinations"]:
                components = []
                for role in declaration["roles"]:
                    matches = [
                        record
                        for record in output
                        if record["role"] == role
                        and record["lane_keys"] == root["lane_keys"]
                        and record["valuation_basis"] == root["valuation_basis"]
                        and all(
                            cell["source_text"] is not None
                            and cell["coefficient"] is not None
                            for cell in record["cells"]
                        )
                    ]
                    if len(matches) != 1 or role not in proven_roles:
                        components = []
                        break
                    components.append(matches[0])
                if components:
                    complete_alternatives.append((declaration, components))
            if len(complete_alternatives) != 1:
                return (
                    output,
                    [],
                    receipts,
                    [
                        "FAMILY_ROOT_DECLARED_COMPONENT_ALTERNATIVE_"
                        + ("NOT_UNIQUE" if complete_alternatives else "INCOMPLETE")
                    ],
                )
            declaration, components = complete_alternatives[0]
            if declaration["equation_policy"] == "DECLARED_DIRECT_SUM":
                multipliers = [1] * len(components)
                root_equation = _local_equation(
                    equation_kind="EXACT_DECLARED_DIRECT_ROOT_COMPONENT_SUM",
                    components=components,
                    result=root,
                    multipliers=multipliers,
                )
                if root_equation["status"] != "EXACT":
                    return (
                        output,
                        [],
                        receipts,
                        ["FAMILY_ROOT_DECLARED_DIRECT_COMPONENT_EQUATION_MISMATCH"],
                    )
                equation_rule = "DECLARED_DIRECT_ROOT_COMPONENT_SUM_ALL_LANES_EXACT"
            else:
                multiplier_candidates = [
                    [1, *suffix]
                    for suffix in product((-1, 1), repeat=max(0, len(components) - 1))
                    if _local_equation(
                        equation_kind=(
                            "EXACT_UNIQUE_DECLARED_ROOT_COMPONENT_SIGN_ORIENTATION"
                        ),
                        components=components,
                        result=root,
                        multipliers=[1, *suffix],
                    )["status"]
                    == "EXACT"
                ]
                if len(multiplier_candidates) != 1:
                    return (
                        output,
                        [],
                        receipts,
                        [
                            "FAMILY_ROOT_DECLARED_COMPONENT_SIGN_ORIENTATION_"
                            + ("NOT_UNIQUE" if multiplier_candidates else "MISMATCH")
                        ],
                    )
                multipliers = multiplier_candidates[0]
                root_equation = _local_equation(
                    equation_kind="EXACT_UNIQUE_DECLARED_ROOT_COMPONENT_SIGN_ORIENTATION",
                    components=components,
                    result=root,
                    multipliers=multipliers,
                )
                equation_rule = (
                    "UNIQUE_PLUS_MINUS_ONE_ORIENTATION_FIRST_DECLARED_COMPONENT_POSITIVE"
                )
            receipts.append(
                {
                    "component_roles": canonical_clone_v1(declaration["roles"]),
                    "multipliers": multipliers,
                    "result_role": "FAMILY_ROOT_TOTAL",
                    "rule": equation_rule,
                    "source_equation_id": root_equation["equation_id"],
                }
            )
            return output, [root_equation], receipts, []
        if not signed_policy:
            return output, [], receipts, []
        if len(reconciled_roots) != 1:
            return output, [], receipts, ["FAMILY_ROOT_SIGNED_POPULATION_IS_NOT_UNIQUE"]
        root = reconciled_roots[0]
        components = []
        for role in compiled_specs["root_component_roles"]:
            matches = [
                record
                for record in output
                if record["role"] == role
                and record["lane_keys"] == root["lane_keys"]
                and record["valuation_basis"] == root["valuation_basis"]
            ]
            if len(matches) != 1 or role not in proven_roles:
                return (
                    output,
                    [],
                    receipts,
                    ["FAMILY_ROOT_DECLARED_COMPONENT_POPULATION_NOT_EXACT:" + role],
                )
            components.append(matches[0])
        multiplier_candidates = [
            [1, *suffix]
            for suffix in product((-1, 1), repeat=max(0, len(components) - 1))
            if _local_equation(
                equation_kind="EXACT_UNIQUE_DECLARED_ROOT_COMPONENT_SIGN_ORIENTATION",
                components=components,
                result=root,
                multipliers=[1, *suffix],
            )["status"]
            == "EXACT"
        ]
        if len(multiplier_candidates) != 1:
            return (
                output,
                [],
                receipts,
                [
                    "FAMILY_ROOT_DECLARED_COMPONENT_SIGN_ORIENTATION_"
                    + ("NOT_UNIQUE" if multiplier_candidates else "MISMATCH")
                ],
            )
        multipliers = multiplier_candidates[0]
        signed_equation = _local_equation(
            equation_kind="EXACT_UNIQUE_DECLARED_ROOT_COMPONENT_SIGN_ORIENTATION",
            components=components,
            result=root,
            multipliers=multipliers,
        )
        receipts.append(
            {
                "component_roles": canonical_clone_v1(compiled_specs["root_component_roles"]),
                "multipliers": multipliers,
                "result_role": "FAMILY_ROOT_TOTAL",
                "rule": "UNIQUE_PLUS_MINUS_ONE_ORIENTATION_FIRST_DECLARED_COMPONENT_POSITIVE",
                "source_equation_id": signed_equation["equation_id"],
            }
        )
        return output, [signed_equation], receipts, []

    if compiled_specs.get("root_component_role_combinations"):
        return output, [], [], ["SOURCE_VISIBLE_FAMILY_ROOT_ALTERNATIVE_NOT_PROVEN"]

    if any(
        record["role"] != "FAMILY_ROOT_TOTAL"
        and record["role"] not in validation_only_source_roles
        and not reaches_root(record["role"])
        for record in output
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
    minimum_synthesized_root_components = (
        compiled_specs["evaluation"].get("minimum_source_visible_root_component_count", 1)
        if compiled_specs["evaluation"].get(
            "root_only_source_result_policy", "ALLOW_EXACT_SOURCE_RESULT"
        )
        == "REQUIRE_MINIMUM_DECLARED_COMPONENTS"
        else 1
    )
    if len(candidate_component_roles) < minimum_synthesized_root_components or any(
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
    cells = _sum_record_cells(
        components,
        exact_state="EXACT_COMPLETE_TOP_LEVEL_COMPONENT_SUM",
    )
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
        if any(coefficient is None for coefficient in coefficients):
            return output, [], [], []
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
    prior_fragment: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        page_json, section, table, compiled_specs=compiled_specs
    )
    if type(prior_fragment) is dict:
        prior_region = prior_fragment.get("region")
        prior_table = prior_fragment.get("table")
        prior_classification = prior_fragment.get("classification")
        if (
            type(prior_region) is dict
            and type(prior_table) is dict
            and type(prior_classification) is dict
            and prior_table.get("continuation") == "CONTINUES_ON_NEXT_PAGE"
            and table.get("continuation") == "CONTINUES_FROM_PREVIOUS_PAGE"
            and prior_region.get("document_id") == region.get("document_id")
            and prior_region.get("source_sha256") == region.get("source_sha256")
            and prior_region.get("selected_page_ordinal")
            == region.get("selected_page_ordinal", -2) - 1
            and prior_region.get("physical_page") == region.get("physical_page", -2) - 1
        ):
            classification, _leading_scope_receipt = (
                _explicit_continuation_leading_scope_classification_v1(
                    prior_classification=prior_classification,
                    current_classification=classification,
                    current_table=table,
                    compiled_specs=compiled_specs,
                )
            )
    context_total_state = {
        "EXPLICIT_TABLE_TITLE": "SOURCE_PRINTED_TOTAL_PROVEN_AS_EXPLICIT_TABLE_CONTEXT_ROLE",
        "EXPLICIT_TITLELESS_ORDERED_TABLE_SECTION_NARRATIVE": (
            "SOURCE_PRINTED_TOTAL_PROVEN_AS_EXPLICIT_ORDERED_TABLE_NARRATIVE_CONTEXT_ROLE"
        ),
        "EXPLICIT_TITLELESS_SOLE_TABLE_SECTION_NARRATIVE": (
            "SOURCE_PRINTED_TOTAL_PROVEN_AS_EXPLICIT_SOLE_TABLE_SECTION_NARRATIVE_CONTEXT_ROLE"
        ),
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
    lane_axis = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
    if not lane_axis["complete"]:
        inherited_lane_axis = _adjacent_continuation_lane_axis(
            section,
            table,
            region,
            compiled_specs=compiled_specs,
            prior_fragment=prior_fragment,
        )
        if inherited_lane_axis is not None:
            lane_axis = inherited_lane_axis
    unit_table = canonical_clone_v1(table)
    if lane_axis["complete"]:
        columns = table.get("columns")
        assert type(columns) is list
        unit_table["columns"] = []
        for ordinal in lane_axis["money_column_ordinals"]:
            column = canonical_clone_v1(columns[ordinal - 1])
            if "multi_metric_lane_equation" in compiled_specs:
                # Metric labels are a declared non-unit dimension.  Validate
                # units on a private projection with those exact header
                # segments removed; e.g. Vietnamese ``hợp đồng`` must not be
                # mistaken for the standalone currency word ``đồng``.
                aliases = {
                    alias
                    for metric_aliases in compiled_specs["multi_metric_lane_equation"][
                        "metric_aliases"
                    ].values()
                    for alias in metric_aliases
                }
                path = column.get("header_path_exact")
                if type(path) is list:
                    column["header_path_exact"] = [
                        segment
                        for segment in path
                        if not any(_contains_alias(segment, alias) for alias in aliases)
                    ]
            # The shared unit primitive intentionally inventories MONEY
            # columns.  An opt-in UNKNOWN numeric column is promoted only in
            # this private validation copy after the family owner/role/period
            # policy selected it; immutable Gemini JSON is never changed.
            if column.get("value_kind") in compiled_specs.get(
                "accepted_value_column_kinds", ["MONEY"]
            ):
                column["value_kind"] = "MONEY"
            unit_table["columns"].append(column)
    unit_axis = _unit_axis(
        unit_table,
        compiled_specs=compiled_specs,
        document_unit_context=document_unit_context,
    )
    if not unit_axis["complete"]:
        inherited_continuation_unit_axis = _adjacent_continuation_unit_axis(
            table,
            region,
            lane_axis,
            unit_axis,
            compiled_specs=compiled_specs,
            prior_fragment=prior_fragment,
        )
        if inherited_continuation_unit_axis is not None:
            unit_axis = inherited_continuation_unit_axis
    if not unit_axis["complete"]:
        inherited_unit_axis = _adjacent_numbered_subsection_unit_axis(
            section,
            table,
            region,
            lane_axis,
            unit_axis,
            compiled_specs=compiled_specs,
            prior_fragment=prior_fragment,
        )
        if inherited_unit_axis is not None:
            unit_axis = inherited_unit_axis
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
    selected_unit_bindings = [
        binding
        for binding in compiled_specs["unit_bindings"]
        if binding["accepted"] is True
        and binding["canonical_unit"] == unit_axis["canonical_unit"]
    ]
    selected_unit_magnitude_power10 = (
        selected_unit_bindings[0]["magnitude_power10"]
        if len(selected_unit_bindings) == 1
        else None
    )

    def configured_complete_source_equation(
        *,
        kind: str,
        components: Sequence[Mapping[str, Any]],
        result: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        equation = _exact_equation(kind=kind, components=components, result=result)
        if equation is not None or compiled_specs[
            "source_presentation_rounding_policy"
        ] != "INDEPENDENT_DISPLAY_UNIT_ROUNDING_INTERVAL_ALL_EQUATIONS":
            return equation
        return _source_presentation_rounding_equation(
            kind=kind,
            components=components,
            result=result,
            canonical_unit=unit_axis["canonical_unit"],
            magnitude_power10=selected_unit_magnitude_power10,
        )

    def configured_observed_lane_source_equation(
        *,
        kind: str,
        components: Sequence[Mapping[str, Any]],
        result: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        equation = _observed_lane_control_equation(
            kind=kind, components=components, result=result
        )
        if equation is not None or compiled_specs[
            "source_presentation_rounding_policy"
        ] != "INDEPENDENT_DISPLAY_UNIT_ROUNDING_INTERVAL_ALL_EQUATIONS":
            return equation
        return _source_presentation_rounding_equation(
            kind=kind,
            components=components,
            result=result,
            canonical_unit=unit_axis["canonical_unit"],
            magnitude_power10=selected_unit_magnitude_power10,
        )

    def configured_component_frontier_source_equation(
        *,
        carrier_role: str | None,
        kind: str,
        components: Sequence[Mapping[str, Any]],
        result: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        """Apply one opt-in carrier equation without changing legacy families.

        The configured role-combination graph may declare that one structural
        carrier is itself a net result whose visible children use a unique
        +/- orientation.  The role graph and source order select the children;
        arithmetic only proves or vetoes that already-selected frontier.  A
        blank lane therefore supplies no candidate and can never become zero.
        """

        declarations = compiled_specs.get("root_component_role_combinations")
        if not declarations or carrier_role is None:
            return configured_observed_lane_source_equation(
                kind=kind, components=components, result=result
            )
        policies = {
            declaration["component_frontier_equation_policy"]
            for declaration in declarations
            if carrier_role in declaration["roles"]
        }
        if not policies or policies == {"DECLARED_DIRECT_SUM"}:
            return configured_observed_lane_source_equation(
                kind=kind, components=components, result=result
            )
        if policies != {"UNIQUE_DECLARED_SIGN_ORIENTATION_FIRST_COMPONENT_POSITIVE"}:
            return None
        multiplier_candidates = [
            [1, *suffix]
            for suffix in product((-1, 1), repeat=max(0, len(components) - 1))
            if _local_equation(
                equation_kind=(
                    "EXACT_UNIQUE_DECLARED_COMPONENT_FRONTIER_SIGN_ORIENTATION_"
                    "EQUAL_VISIBLE_CARRIER"
                ),
                components=components,
                result=result,
                multipliers=[1, *suffix],
            )["status"]
            == "EXACT"
        ]
        if len(multiplier_candidates) != 1:
            return None
        equation = _local_equation(
            equation_kind=(
                "EXACT_UNIQUE_DECLARED_COMPONENT_FRONTIER_SIGN_ORIENTATION_"
                "EQUAL_VISIBLE_CARRIER"
            ),
            components=components,
            result=result,
            multipliers=multiplier_candidates[0],
        )
        material = {
            key: canonical_clone_v1(value)
            for key, value in equation.items()
            if key != "equation_id"
        }
        material["component_frontier_role"] = carrier_role
        return {
            **material,
            "equation_id": "gjfoltiev1:equation:" + canonical_json_sha256_v1(material),
        }
    rows, compound_row_projection_receipts = _project_exact_compound_source_rows(
        table, compiled_specs=compiled_specs
    )
    if compound_row_projection_receipts != classification.get(
        "compound_row_projection_receipts", []
    ):
        raise _error("multi-table compound row projection drifted")
    family_root_ordinals = set(classification.get("family_root_row_ordinals", []))
    declared_role_ordinals = {hit["row_ordinal"] for hit in classification["role_hits"]}
    document_source_result_carrier = bool(
        compiled_specs["document_cluster_policy"]
        == "DOCUMENT_EXACT_DECLARED_ROOT_COMPONENTS_PLUS_SOURCE_RESULT"
        and classification.get("typed_control_disposition") == "PRIMARY_FINANCIAL_STATEMENT_SUMMARY"
        and family_root_ordinals
    )
    source_result_population_ordinals = family_root_ordinals | {
        hit["row_ordinal"]
        for hit in classification["role_hits"]
        if hit["role"] in compiled_specs["root_component_roles"]
    }
    scope_to_explicit_family_root = bool(
        family_root_ordinals
        and (
            compiled_specs["family_root_population_policy"] == "EXPLICIT_SOURCE_ROOT_SUBTREE_ONLY"
            or (
                compiled_specs["family_root_population_policy"]
                == "EXPLICIT_PRIMARY_STATEMENT_SOURCE_ROOT_SUBTREE_OTHERWISE_WHOLE_TABLE"
                and (
                    classification.get("primary_statement_family_root_subtree_receipts")
                    or classification.get("primary_statement_source_result_receipt")
                )
            )
        )
    )
    needs_flat_family_population = bool(
        scope_to_explicit_family_root
        or compiled_specs["unmapped_direct_family_row_policy"]
        == "UNRESOLVED_WHEN_EXPLICIT_FAMILY_ROOT_HAS_UNMAPPED_DIRECT_MONEY_CHILD"
    )
    flat_family_row_ordinals: set[int] = set()
    for root_ordinal in family_root_ordinals if needs_flat_family_population else []:
        root_row = rows[root_ordinal - 1]
        # A flat ordered population needs a source-visible structural carrier.
        # An ITEM whose label happens to equal the family root cannot acquire
        # unrelated neighbouring ITEM rows merely from adjacency.
        if type(root_row) is not dict or root_row.get("row_kind") not in {
            "GROUP",
            "SUBTOTAL",
            "TOTAL",
        }:
            continue
        # A GROUP is a leading structural owner: adjacent flat children may
        # follow it, never precede it.  Visible TOTAL/SUBTOTAL carriers can be
        # printed before or after their components.  Keep the two bounded
        # populations separate until source hierarchy or one declared child
        # role uniquely selects a side; otherwise retain both and let the
        # exhaustive unmapped/duplicate gates fail closed.  This prevents a
        # combined income/expense table from assigning the preceding income
        # population to a following expense subtotal merely by adjacency.
        steps = (1,) if root_row.get("row_kind") == "GROUP" else (-1, 1)
        populations: dict[int, list[int]] = {}
        for step in steps:
            population = []
            ordinal = root_ordinal + step
            while 1 <= ordinal <= len(rows):
                row = rows[ordinal - 1]
                if type(row) is not dict or row.get("row_kind") in {
                    "GROUP",
                    "SUBTOTAL",
                    "TOTAL",
                }:
                    break
                population.append(ordinal)
                ordinal += step
            populations[step] = population
        selected_populations = list(populations.values())
        if len(selected_populations) > 1:
            hierarchy_descendants_visible = any(
                other_ordinal != root_ordinal
                and type(rows[other_ordinal - 1]) is dict
                and _row_is_strict_descendant(rows, other_ordinal, root_ordinal)
                for other_ordinal in range(1, len(rows) + 1)
            )
            hierarchy_scoped = [
                population
                for population in selected_populations
                if any(
                    _row_is_strict_descendant(rows, ordinal, root_ordinal) for ordinal in population
                )
            ]
            declared_child_scoped = [
                population
                for population in selected_populations
                if any(
                    ordinal in declared_role_ordinals and ordinal not in family_root_ordinals
                    for ordinal in population
                )
            ]
            hierarchy_selected = hierarchy_scoped[0] if len(hierarchy_scoped) == 1 else None
            if classification.get("primary_statement_family_root_subtree_receipts"):
                declared_outside_hierarchy = bool(
                    hierarchy_descendants_visible
                    and any(
                        ordinal in declared_role_ordinals and ordinal not in family_root_ordinals
                        for population in selected_populations
                        for ordinal in population
                        if not _row_is_strict_descendant(rows, ordinal, root_ordinal)
                    )
                )
                if hierarchy_descendants_visible and not declared_outside_hierarchy:
                    selected_populations = hierarchy_scoped
            else:
                declared_outside_hierarchy = any(
                    hierarchy_selected is not None
                    and ordinal in declared_role_ordinals
                    and ordinal not in family_root_ordinals
                    for population in selected_populations
                    if population is not hierarchy_selected
                    for ordinal in population
                )
                if hierarchy_selected is not None and not declared_outside_hierarchy:
                    selected_populations = hierarchy_scoped
                elif len(declared_child_scoped) == 1:
                    selected_populations = declared_child_scoped
        flat_family_row_ordinals.update(
            ordinal for population in selected_populations for ordinal in population
        )

    def row_inside_explicit_family_root(row_ordinal: int) -> bool:
        return bool(
            not family_root_ordinals
            or row_ordinal in family_root_ordinals
            or row_ordinal in flat_family_row_ordinals
            or any(
                _row_is_strict_descendant(rows, row_ordinal, root_ordinal)
                for root_ordinal in family_root_ordinals
            )
        )

    outside_family_root_rows = [
        {
            "row": canonical_clone_v1(row),
            "row_ordinal": row_ordinal,
        }
        for row_ordinal, row in enumerate(rows, start=1)
        if type(row) is dict
        and scope_to_explicit_family_root
        and not row_inside_explicit_family_root(row_ordinal)
    ]
    non_money_metric_hits = [
        hit
        for hit in classification["role_hits"]
        if hit["role"] in compiled_specs["non_money_metric_roles"]
    ]
    non_money_metric_row_ordinals = {hit["row_ordinal"] for hit in non_money_metric_hits}
    ratio_metric_hits = [
        hit
        for hit in classification["role_hits"]
        if hit["role"] in compiled_specs.get("ratio_metric_roles", [])
    ]
    ratio_metric_row_ordinals = {hit["row_ordinal"] for hit in ratio_metric_hits}
    if non_money_metric_hits:
        receipt["non_money_metric_source_rows"] = [
            {
                "role": hit["role"],
                "row": canonical_clone_v1(rows[hit["row_ordinal"] - 1]),
                "row_ordinal": hit["row_ordinal"],
                "rule": "DECLARED_VALIDATION_ONLY_NON_MONEY_METRIC_ROW",
            }
            for hit in non_money_metric_hits
        ]
    if ratio_metric_hits:
        receipt["ratio_metric_source_rows"] = [
            {
                "role": hit["role"],
                "row": canonical_clone_v1(rows[hit["row_ordinal"] - 1]),
                "row_ordinal": hit["row_ordinal"],
                "rule": "DECLARED_SOURCE_RATIO_ROW_PARSED_BY_TYPED_DECIMAL_RATIO_GATE",
            }
            for hit in ratio_metric_hits
        ]
    row_records: dict[int, dict[str, Any]] = {}
    parse_reasons = []
    for row_ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict:
            continue
        if document_source_result_carrier and row_ordinal not in source_result_population_ordinals:
            continue
        if scope_to_explicit_family_root and not row_inside_explicit_family_root(row_ordinal):
            continue
        if row_ordinal in non_money_metric_row_ordinals | ratio_metric_row_ordinals:
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
            or row.get("row_kind") in {"GROUP", "SUBTOTAL", "TOTAL"}
        ):
            row_records[row_ordinal] = record
    if parse_reasons:
        receipt["parse_reasons"] = sorted(set(parse_reasons))
    if scope_to_explicit_family_root:
        receipt["family_root_population_receipt"] = {
            "explicit_family_root_row_ordinals": sorted(family_root_ordinals),
            "flat_item_row_ordinals": sorted(flat_family_row_ordinals),
            "rule": (
                "EXPLICIT_SOURCE_ROOT_HIERARCHY_PLUS_CONTIGUOUS_FLAT_ITEMS_"
                "BOUNDED_BY_STRUCTURAL_ROW"
            ),
        }

    hit_by_row: dict[int, str] = {}
    for hit in classification["role_hits"]:
        if hit["role"] in compiled_specs["non_money_metric_roles"]:
            continue
        ordinal = hit["row_ordinal"]
        if ordinal in hit_by_row and hit_by_row[ordinal] != hit["role"]:
            raise _error("multi-table hierarchical source row role repeated")
        hit_by_row[ordinal] = hit["role"]
    supplemental_inferred_ordinals: set[int] = set()
    supplemental_residual_projection_receipts = []
    for declaration in compiled_specs["supplemental_detail_residuals"]:
        residual_role = declaration["residual_role"]
        for marker in declaration["markers"]:
            carriers = [
                ordinal
                for ordinal, row in enumerate(rows, start=1)
                if type(row) is dict
                and _normalized(row.get("label_exact")) == marker
                and row.get("row_kind") != "TOTAL"
                and type(row.get("values_exact")) is list
                and all(value is None for value in row["values_exact"])
            ]
            if len(carriers) != 1:
                continue
            carrier_ordinal = carriers[0]
            projected = []
            for ordinal, record in sorted(row_records.items()):
                if ordinal in hit_by_row or ordinal == carrier_ordinal:
                    continue
                row = rows[ordinal - 1]
                path = [
                    _normalized(value)
                    for value in row.get("hierarchy_path_exact", [])
                    if _normalized(value)
                ]
                label = _normalized(row.get("label_exact"))
                if (
                    ordinal > carrier_ordinal
                    and row.get("row_kind") == "ITEM"
                    and len(path) == 2
                    and path[0] == marker
                    and label
                    and path[1] == label
                ):
                    hit_by_row[ordinal] = residual_role
                    supplemental_inferred_ordinals.add(ordinal)
                    projected.append(canonical_clone_v1(record["source_refs"][0]))
            if projected:
                supplemental_residual_projection_receipts.append(
                    {
                        "carrier_row_ordinal": carrier_ordinal,
                        "marker": marker,
                        "projected_source_refs": projected,
                        "residual_role": residual_role,
                        "rule": (
                            "UNMATCHED_DIRECT_CHILD_ROWS_OF_ONE_EXPLICIT_"
                            "NONEXHAUSTIVE_DETAIL_MARKER_PROJECT_TO_DECLARED_RESIDUAL"
                        ),
                    }
                )
    label_only_group_proxies: dict[int, tuple[list[int], dict[str, Any]]] = {}
    if compiled_specs["label_only_structural_group_policy"] in {
        "DIRECT_CHILD_FRONTIER_ONLY_AFTER_SOURCE_TOTAL_CLOSURE",
        "SINGLE_DIRECT_CHILD_ONLY_AFTER_SOURCE_TOTAL_CLOSURE",
    }:

        def structural_depth(row_ordinal: int) -> int:
            return len(
                [
                    value
                    for value in rows[row_ordinal - 1].get("hierarchy_path_exact") or []
                    if _normalized(value)
                ]
            )

        def is_carrier_result_row(carrier_ordinal: int, row_ordinal: int) -> bool:
            carrier_row = rows[carrier_ordinal - 1]
            candidate_row = rows[row_ordinal - 1]
            carrier_label = _normalized(carrier_row.get("label_exact"))
            candidate_label = _normalized(candidate_row.get("label_exact"))
            carrier_path = [
                normalized
                for value in carrier_row.get("hierarchy_path_exact") or []
                if (normalized := _normalized(value))
            ]
            candidate_path = [
                normalized
                for value in candidate_row.get("hierarchy_path_exact") or []
                if (normalized := _normalized(value))
            ]
            return bool(
                (
                    candidate_row.get("row_kind") in {"SUBTOTAL", "TOTAL"}
                    and not candidate_label
                    and candidate_path == carrier_path
                )
                or (
                    candidate_row.get("row_kind") == "TOTAL"
                    and carrier_label
                    and candidate_label == "tong " + carrier_label
                    and candidate_path[: len(carrier_path)] == carrier_path
                )
            )

        # Build the deepest blank carrier first.  A wider carrier can then use
        # the already-authenticated child proxy rather than summing an all-blank
        # GROUP row or (worse) its terminal printed total.  SUBTOTAL/TOTAL rows
        # are equation results and therefore never belong to the proxy's
        # component frontier.
        for carrier_ordinal, role in sorted(
            hit_by_row.items(), key=lambda item: (-structural_depth(item[0]), item[0])
        ):
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
                and not is_carrier_result_row(carrier_ordinal, ordinal)
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
            if not direct:
                # Gemini sometimes flattens ``Parent - Child`` into one path
                # string instead of preserving path segments.  The compiled
                # role graph plus contiguous source order still identifies a
                # direct-child frontier without inspecting values.  Stop at
                # the first row not declared directly within this carrier so
                # no sibling or later population can leak into the proxy.
                for ordinal in range(carrier_ordinal + 1, len(rows) + 1):
                    child_role = hit_by_row.get(ordinal)
                    if child_role is None or ordinal not in row_records:
                        break
                    if not any(
                        matcher["within_role"] == role
                        for matcher in compiled_specs["matchers_by_role"].get(child_role, [])
                    ):
                        break
                    direct.append(ordinal)
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
            # ``Trong đó / Of which`` is a transparent disclosure wrapper: its
            # descendants are subsets of another direct component, not an
            # additional additive branch.  A blank wrapper is retained in the
            # source inventory but excluded from this structural sum.
            direct = [
                ordinal
                for ordinal in direct
                if not (
                    rows[ordinal - 1].get("row_kind") == "GROUP"
                    and all(cell["source_text"] is None for cell in row_records[ordinal]["cells"])
                    and _normalized(rows[ordinal - 1].get("label_exact"))
                    in {"trong do", "bao gom", "of which", "including"}
                )
            ]
            if not direct or (single_only and len(direct) != 1):
                continue
            direct_records = [
                label_only_group_proxies.get(ordinal, ([], row_records[ordinal]))[1]
                for ordinal in direct
            ]
            if len(direct_records) == 1:
                proxy = direct_records[0]
            else:
                proxy = _local_record(
                    "SOURCE_ROW",
                    _sum_record_cells(
                        direct_records,
                        exact_state="EXACT_LABEL_ONLY_GROUP_DIRECT_CHILD_FRONTIER_SUM",
                    ),
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
                (
                    "SOURCE_UNMATCHED_SUPPLEMENTAL_DETAIL_ROW_PROJECTED_TO_RESIDUAL"
                    if ordinal in supplemental_inferred_ordinals
                    else "SOURCE_OBSERVED_ROLE_ROW"
                ),
                record["valuation_basis"],
            )
        )

    optional_component_veto_source_result = bool(
        compiled_specs["schema"]["root_mapping_policy"]
        == "SOURCE_VISIBLE_EXACT_RESULT_WITH_OPTIONAL_COMPLETE_COMPONENT_EQUATION_VETO"
    )
    direct_primary_source_result = bool(
        compiled_specs["schema"]["root_mapping_policy"]
        == "SOURCE_VISIBLE_PRIMARY_RESULT_OR_EXACT_NOTE_EQUATION"
        and classification.get("primary_statement_source_result_receipt")
    )
    primary_source_result_candidate_ordinals = {
        item["row_ordinal"]
        for item in classification.get(
            "primary_statement_source_result_candidates", []
        )
    }
    source_result_row_receipt = None
    if optional_component_veto_source_result:
        source_result_row_receipt = {
            "declared_component_evidence_roles": sorted(set(hit_by_row.values())),
            "family_root_row_ordinals": sorted(family_root_ordinals),
            "rule": (
                "EXACT_SOURCE_RESULT_ROW_MAPS_DIRECTLY_WITHOUT_COMPONENT_EVIDENCE_"
                "OTHERWISE_COMPLETE_COMPONENT_EQUATION_IS_A_VETO"
            ),
        }

    equations = _materialize_multi_metric_source_equations(
        lane_axis,
        region=region,
        rows=rows,
    )
    proven_roles: set[str] = set()
    consumed_ordinals: set[int] = set()
    proven_carrier_children: dict[int, set[int]] = defaultdict(set)
    source_visible_family_root_ordinals: set[int] = set()
    deferred_hierarchy_family_roots: list[tuple[int, dict[str, Any]]] = []
    label_only_structural_group_receipts = []
    projected_label_only_groups: set[int] = set()
    source_hierarchy_overlap_total_receipts = []

    def transparent_disclosure_wrapper(row_ordinal: int) -> bool:
        """Return whether a blank GROUP only carries disclosure hierarchy.

        Gemini commonly preserves ``Trong đó / Bao gồm / Of which`` as an
        intermediate row.  It is neither a numeric component nor a subtotal;
        treating it as the carrier's sole direct child hides the actual
        children one level below and prevents an otherwise exact source
        equation from closing.  Ordinarily this requires a typed GROUP.  An
        authenticated primary-statement family group may carry a generic ITEM
        row kind from Gemini, so its exact label/hierarchy/frontier receipt is
        the stronger local structure authority.
        """

        row = rows[row_ordinal - 1]
        record = row_records.get(row_ordinal)
        authenticated_family_group_ordinals = {
            item["family_group_row_ordinal"]
            for item in classification.get("primary_statement_family_root_subtree_receipts", [])
        }
        return bool(
            type(row) is dict
            and record is not None
            and (
                row.get("row_kind") == "GROUP" or row_ordinal in authenticated_family_group_ordinals
            )
            and all(cell["source_text"] is None for cell in record["cells"])
            and (
                _normalized(row.get("label_exact"))
                in {"trong do", "bao gom", "of which", "including"}
                or row_ordinal in authenticated_family_group_ordinals
            )
        )

    def effective_direct_descendants(
        carrier_ordinal: int,
    ) -> list[tuple[int, dict[str, Any]]]:
        descendants = [
            (ordinal, record)
            for ordinal, record in row_records.items()
            if ordinal != carrier_ordinal
            and _row_is_strict_descendant(rows, ordinal, carrier_ordinal)
        ]
        direct = [
            (ordinal, record)
            for ordinal, record in descendants
            if not any(
                other_ordinal != ordinal and _row_is_strict_descendant(rows, ordinal, other_ordinal)
                for other_ordinal, _other in descendants
            )
        ]
        expanded = []
        for ordinal, record in direct:
            if transparent_disclosure_wrapper(ordinal):
                expanded.extend(effective_direct_descendants(ordinal))
            else:
                expanded.append((ordinal, record))
        return expanded

    def following_disclosure_wrapper_children(
        carrier_ordinal: int,
    ) -> list[tuple[int, dict[str, Any]]]:
        """Recover children of an immediately following disclosure wrapper.

        Some structured page responses preserve ``Trong đó / Of which`` in a
        blank GROUP row but flatten its relationship to the preceding visible
        carrier.  The child rows still carry a hierarchy path whose first
        segment extends that wrapper label.  This source order + hierarchy
        grammar identifies one bounded frontier before arithmetic is used as
        a veto.  It never scans for a value-equal subset.
        """

        wrapper_ordinal = carrier_ordinal + 1
        if wrapper_ordinal not in row_records or not transparent_disclosure_wrapper(
            wrapper_ordinal
        ):
            return []
        wrapper_label = _normalized(rows[wrapper_ordinal - 1].get("label_exact"))
        if not wrapper_label:
            return []
        children = []
        for ordinal in range(wrapper_ordinal + 1, len(rows) + 1):
            record = row_records.get(ordinal)
            if record is None:
                continue
            row = rows[ordinal - 1]
            if row.get("row_kind") in {"SUBTOTAL", "TOTAL"}:
                break
            path = [
                _normalized(value)
                for value in (row.get("hierarchy_path_exact") or [])
                if _normalized(value)
            ]
            if not path or not (
                path[0] == wrapper_label or path[0].startswith(wrapper_label + " ")
            ):
                break
            children.append((ordinal, record))
        return children

    if optional_component_veto_source_result and len(family_root_ordinals) == 1:
        root_ordinal = next(iter(family_root_ordinals))
        root = row_records.get(root_ordinal)
        if root is not None:
            local_records.append(
                _local_record(
                    "FAMILY_ROOT_TOTAL",
                    root["cells"],
                    root["lane_keys"],
                    root["source_refs"],
                    "SOURCE_VISIBLE_EXACT_RESULT_PENDING_OPTIONAL_COMPONENT_VETO",
                    root["valuation_basis"],
                )
            )
            # The cluster-level policy below is the sole authority that proves
            # this visible result. Marking the ordinal here only prevents the
            # ordinary subtotal scanner from emitting a second root record.
            source_visible_family_root_ordinals.add(root_ordinal)
    if direct_primary_source_result and len(family_root_ordinals) == 1:
        root_ordinal = next(iter(family_root_ordinals))
        root = row_records.get(root_ordinal)
        if root is not None and any(
            cell["source_text"] is not None for cell in root["cells"]
        ):
            local_records.append(
                _local_record(
                    "FAMILY_ROOT_TOTAL",
                    root["cells"],
                    root["lane_keys"],
                    root["source_refs"],
                    "SOURCE_VISIBLE_PRIMARY_STATEMENT_EXACT_RESULT",
                    root["valuation_basis"],
                )
            )
            source_visible_family_root_ordinals.add(root_ordinal)
            consumed_ordinals.add(root_ordinal)
            proven_roles.add("FAMILY_ROOT_TOTAL")
            source_result_row_receipt = {
                **canonical_clone_v1(
                    classification["primary_statement_source_result_receipt"]
                ),
                "rule": (
                    "SOURCE_VISIBLE_PRIMARY_RESULT_MAPS_DIRECTLY_WITHOUT_"
                    "BLANK_BACKSOLVE_OR_COMPONENT_EQUATION"
                ),
            }
    total_ordinals = {
        ordinal
        for ordinal, row in enumerate(rows, start=1)
        if type(row) is dict
        and ordinal in row_records
        and not (
            direct_primary_source_result
            and ordinal in primary_source_result_candidate_ordinals
        )
        and (
            (
                row.get("row_kind") in {"SUBTOTAL", "TOTAL"}
                and (
                    hit_by_row.get(ordinal) is None
                    or compiled_specs["child_by_role"][hit_by_row[ordinal]]["role_kind"]
                    in {"STRUCTURAL_GROUP", "SUBTOTAL", "TOTAL"}
                )
            )
            or (
                compiled_specs["declared_result_role_policy"]
                == "SOURCE_ROW_KIND_OR_DECLARED_SUBTOTAL_TOTAL_ROLE"
                and hit_by_row.get(ordinal) is not None
                and compiled_specs["child_by_role"][hit_by_row[ordinal]]["role_kind"]
                in {"SUBTOTAL", "TOTAL"}
            )
        )
    }
    declared_result_row_kind_overrides = [
        {
            "declared_role": hit_by_row[ordinal],
            "declared_role_kind": compiled_specs["child_by_role"][hit_by_row[ordinal]]["role_kind"],
            "row_ordinal": ordinal,
            "source_row_kind": rows[ordinal - 1].get("row_kind"),
            "rule": "DECLARED_SUBTOTAL_OR_TOTAL_ROLE_SUPPLEMENTS_GEMINI_ROW_KIND",
        }
        for ordinal in sorted(total_ordinals)
        if rows[ordinal - 1].get("row_kind") not in {"SUBTOTAL", "TOTAL"} and ordinal in hit_by_row
    ]
    if declared_result_row_kind_overrides:
        receipt["declared_result_row_kind_overrides"] = declared_result_row_kind_overrides
    unlabeled_subtotals_by_path: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for ordinal in sorted(total_ordinals):
        row = rows[ordinal - 1]
        path = tuple(
            normalized
            for value in row.get("hierarchy_path_exact") or []
            if (normalized := _normalized(value))
        )
        if (
            row.get("row_kind") == "SUBTOTAL"
            and not _normalized(row.get("label_exact"))
            and len(path) == 1
        ):
            unlabeled_subtotals_by_path[path].append(ordinal)
    ambiguous_unlabeled_structural_subtotals = [
        {"hierarchy_path_normalized": list(path), "row_ordinals": ordinals}
        for path, ordinals in sorted(unlabeled_subtotals_by_path.items())
        if len(ordinals) != 1
    ]
    if ambiguous_unlabeled_structural_subtotals:
        receipt["ambiguous_unlabeled_structural_subtotals"] = (
            ambiguous_unlabeled_structural_subtotals
        )
    # First prove visible hierarchy carriers from their exact direct children.
    for carrier_ordinal, carrier in sorted(row_records.items()):
        label = _normalized(rows[carrier_ordinal - 1].get("label_exact"))
        if not label:
            continue
        direct = effective_direct_descendants(carrier_ordinal)
        equation_kind = "EXACT_VISIBLE_HIERARCHY_DIRECT_CHILDREN_EQUAL_CARRIER"
        if not direct:
            direct = following_disclosure_wrapper_children(carrier_ordinal)
            equation_kind = "EXACT_VISIBLE_CARRIER_FOLLOWED_BY_DISCLOSURE_WRAPPER_CHILDREN"
        if not direct:
            continue
        equation = configured_component_frontier_source_equation(
            carrier_role=hit_by_row.get(carrier_ordinal),
            kind=equation_kind,
            components=[record for _ordinal, record in direct],
            result=carrier,
        )
        if equation is not None:
            equations.append(equation)
            proven_carrier_children[carrier_ordinal].update(ordinal for ordinal, _record in direct)
            consumed_ordinals.update(ordinal for ordinal, _record in direct)
            consumed_ordinals.add(carrier_ordinal)
            if _is_complete_source_control_equation(equation):
                proven_roles.update(
                    hit_by_row[ordinal]
                    for ordinal, _record in direct
                    if ordinal in hit_by_row
                )
                if carrier_ordinal in hit_by_row:
                    proven_roles.add(hit_by_row[carrier_ordinal])
            if carrier_ordinal in family_root_ordinals and any(
                cell["source_text"] is not None for cell in carrier["cells"]
            ):
                # Do not choose a nested explicit-root carrier before the
                # table's wider top-level frontier has been evaluated.  A
                # later printed total may include this exact carrier plus
                # other direct family roles.  Keep the independently proven
                # carrier as a fallback and materialize it only when no wider
                # source total closes.  This is graph order, never value-based
                # root selection.
                deferred_hierarchy_family_roots.append((carrier_ordinal, carrier))

    # Gemini can flatten a compact hierarchy into one path string while still
    # preserving exact source order and declared row roles.  Recover only the
    # contiguous *direct* role frontier of a visible structural carrier; stop
    # at the first non-child row and let arithmetic merely prove or veto the
    # already selected graph.  This is the role-graph analogue of the visible
    # hierarchy rule above, not a search for a value-equal subset.
    for carrier_ordinal, carrier_role in sorted(hit_by_row.items()):
        if carrier_ordinal in proven_carrier_children:
            continue
        carrier = row_records.get(carrier_ordinal)
        if (
            carrier is None
            or compiled_specs["child_by_role"][carrier_role]["role_kind"] != "STRUCTURAL_GROUP"
            or not any(cell["source_text"] is not None for cell in carrier["cells"])
        ):
            continue
        direct = []
        for ordinal in range(carrier_ordinal + 1, len(rows) + 1):
            record = row_records.get(ordinal)
            role = hit_by_row.get(ordinal)
            if record is None or role is None:
                break
            if not any(
                matcher["within_role"] == carrier_role
                for matcher in compiled_specs["matchers_by_role"].get(role, [])
            ):
                break
            direct.append((ordinal, record))
        if not direct:
            continue
        equation = configured_component_frontier_source_equation(
            carrier_role=carrier_role,
            kind="EXACT_CONTIGUOUS_DECLARED_DIRECT_ROLE_FRONTIER_EQUALS_VISIBLE_CARRIER",
            components=[record for _ordinal, record in direct],
            result=carrier,
        )
        if equation is None:
            continue
        equations.append(equation)
        proven_carrier_children[carrier_ordinal].update(ordinal for ordinal, _record in direct)
        consumed_ordinals.update({carrier_ordinal, *(ordinal for ordinal, _record in direct)})
        if _is_complete_source_control_equation(equation):
            proven_roles.add(carrier_role)
            proven_roles.update(hit_by_row[ordinal] for ordinal, _record in direct)

    # A label-only structural group may terminate in either an unlabeled
    # subtotal on the same hierarchy path or a labelled ``Total <carrier>``
    # row.  Select that result only from this source grammar, then use exact
    # arithmetic as a veto.  This handles nested group/subtotal presentations
    # recursively without asking Gemini to emit synthetic parent values.
    def normalized_row_path(row_ordinal: int) -> list[str]:
        return [
            normalized
            for value in rows[row_ordinal - 1].get("hierarchy_path_exact") or []
            if (normalized := _normalized(value))
        ]

    for carrier_ordinal, (child_ordinals, proxy_record) in sorted(
        label_only_group_proxies.items(),
        key=lambda item: (-len(normalized_row_path(item[0])), item[0]),
    ):
        if carrier_ordinal in projected_label_only_groups:
            continue
        carrier_label = _normalized(rows[carrier_ordinal - 1].get("label_exact"))
        carrier_path = normalized_row_path(carrier_ordinal)
        if not carrier_label or not carrier_path:
            continue
        structural_results = []
        for total_ordinal in sorted(total_ordinals):
            if total_ordinal <= carrier_ordinal:
                continue
            total_row = rows[total_ordinal - 1]
            total_label = _normalized(total_row.get("label_exact"))
            total_path = normalized_row_path(total_ordinal)
            same_path_unlabelled_subtotal = bool(
                total_row.get("row_kind") in {"SUBTOTAL", "TOTAL"}
                and not total_label
                and total_path == carrier_path
            )
            labelled_carrier_total = bool(
                total_label
                and total_label == "tong " + carrier_label
                and len(total_path) >= len(carrier_path)
                and total_path[: len(carrier_path)] == carrier_path
            )
            if same_path_unlabelled_subtotal or labelled_carrier_total:
                structural_results.append(total_ordinal)
        if len(structural_results) != 1:
            continue
        result_ordinal = structural_results[0]
        result_record = row_records[result_ordinal]
        equation = configured_complete_source_equation(
            kind="EXACT_LABEL_ONLY_STRUCTURAL_GROUP_PROXY_EQUALS_PRINTED_RESULT",
            components=[proxy_record],
            result=result_record,
        )
        if equation is None:
            continue
        equations.append(equation)
        role = hit_by_row[carrier_ordinal]
        local_records.append(
            _local_record(
                role,
                result_record["cells"],
                result_record["lane_keys"],
                [*row_records[carrier_ordinal]["source_refs"], *result_record["source_refs"]],
                "DECLARED_LABEL_ONLY_STRUCTURAL_GROUP_BOUND_TO_EXACT_PRINTED_RESULT",
                result_record["valuation_basis"],
            )
        )
        source_child_ordinals = {
            source_ref["row_ordinal"] for source_ref in proxy_record["source_refs"]
        }
        consumed_ordinals.update(
            {carrier_ordinal, result_ordinal, *child_ordinals, *source_child_ordinals}
        )
        proven_carrier_children[carrier_ordinal].update(child_ordinals)
        proven_carrier_children[result_ordinal].update(source_child_ordinals)
        proven_roles.add(role)
        proven_roles.update(
            hit_by_row[ordinal] for ordinal in source_child_ordinals if ordinal in hit_by_row
        )
        projected_label_only_groups.add(carrier_ordinal)
        label_only_structural_group_receipts.append(
            {
                "carrier_role": role,
                "carrier_row_ordinal": carrier_ordinal,
                "child_row_ordinals": child_ordinals,
                "child_source_refs": canonical_clone_v1(proxy_record["source_refs"]),
                "result_row_ordinal": result_ordinal,
                "rule": (
                    "STRUCTURAL_PATH_OR_TOTAL_LABEL_BINDS_LABEL_ONLY_GROUP_TO_"
                    "PRINTED_RESULT_AFTER_COMPLETE_DIRECT_CHILD_FRONTIER_CLOSURE"
                ),
                "source_equation_id": equation["equation_id"],
            }
        )

    # Validation-only structural carriers also need their local equations even
    # though they are intentionally not mapping roles and therefore have no
    # label-only mapping proxy above.  Bind an unlabeled subtotal to the one
    # preceding blank GROUP with the exact same normalized hierarchy path.
    for subtotal_ordinal in sorted(total_ordinals - consumed_ordinals):
        subtotal_row = rows[subtotal_ordinal - 1]
        if subtotal_row.get("row_kind") != "SUBTOTAL" or _normalized(
            subtotal_row.get("label_exact")
        ):
            continue
        subtotal_path = normalized_row_path(subtotal_ordinal)
        if not subtotal_path:
            continue
        carriers = [
            ordinal
            for ordinal in row_records
            if ordinal < subtotal_ordinal
            and normalized_row_path(ordinal) == subtotal_path
            and rows[ordinal - 1].get("row_kind") == "GROUP"
            and all(cell["source_text"] is None for cell in row_records[ordinal]["cells"])
        ]
        if len(carriers) != 1:
            continue
        carrier_ordinal = carriers[0]
        descendants_before_subtotal = [
            (ordinal, record)
            for ordinal, record in row_records.items()
            if carrier_ordinal < ordinal < subtotal_ordinal
            and _row_is_strict_descendant(rows, ordinal, carrier_ordinal)
        ]
        direct = [
            (ordinal, record)
            for ordinal, record in descendants_before_subtotal
            if not any(
                other_ordinal != ordinal and _row_is_strict_descendant(rows, ordinal, other_ordinal)
                for other_ordinal, _other in descendants_before_subtotal
            )
        ]
        equation = configured_complete_source_equation(
            kind="EXACT_LABEL_ONLY_GROUP_DIRECT_CHILDREN_EQUAL_UNLABELED_SUBTOTAL",
            components=[record for _ordinal, record in direct],
            result=row_records[subtotal_ordinal],
        )
        if equation is None:
            continue
        equations.append(equation)
        consumed_ordinals.update(
            {carrier_ordinal, subtotal_ordinal, *(ordinal for ordinal, _record in direct)}
        )
        proven_roles.update(
            hit_by_row[ordinal] for ordinal, _record in direct if ordinal in hit_by_row
        )
        if carrier_ordinal in hit_by_row:
            proven_roles.add(hit_by_row[carrier_ordinal])

    # When several independently closed structural groups are printed as
    # unlabeled subtotals followed by one terminal unlabeled total, those
    # subtotal rows are the exact top-level frontier.  Require them to cover
    # every populated source row through disjoint local equations before the
    # final arithmetic check.
    for total_ordinal in sorted(total_ordinals - consumed_ordinals):
        total_row = rows[total_ordinal - 1]
        if (
            total_row.get("row_kind") != "TOTAL"
            or _normalized(total_row.get("label_exact"))
            or total_ordinal != max(row_records)
        ):
            continue
        subtotal_ordinals = [
            ordinal
            for ordinal in sorted(total_ordinals)
            if ordinal < total_ordinal
            and rows[ordinal - 1].get("row_kind") == "SUBTOTAL"
            and not _normalized(rows[ordinal - 1].get("label_exact"))
            and ordinal in consumed_ordinals
        ]
        if len(subtotal_ordinals) < 2:
            continue
        subtotal_equations = []
        for subtotal_ordinal in subtotal_ordinals:
            matches = [
                equation
                for equation in equations
                if _is_complete_source_control_equation(equation)
                and {ref.get("row_ordinal") for ref in equation.get("result_source_refs", [])}
                == {subtotal_ordinal}
            ]
            if len(matches) != 1:
                subtotal_equations = []
                break
            subtotal_equations.append(matches[0])
        if not subtotal_equations:
            continue
        component_axes = [
            {ref.get("row_ordinal") for refs in equation["component_source_refs"] for ref in refs}
            for equation in subtotal_equations
        ]
        if any(
            axis.intersection(other)
            for index, axis in enumerate(component_axes)
            for other in component_axes[index + 1 :]
        ):
            continue
        covered = set(subtotal_ordinals).union(*component_axes)
        uncovered = set(row_records) - covered - {total_ordinal}
        if any(
            rows[ordinal - 1].get("row_kind") != "GROUP"
            or any(cell["source_text"] is not None for cell in row_records[ordinal]["cells"])
            for ordinal in uncovered
        ):
            continue
        equation = configured_complete_source_equation(
            kind="EXACT_CLOSED_STRUCTURAL_GROUP_SUBTOTALS_EQUAL_TERMINAL_TOTAL",
            components=[row_records[ordinal] for ordinal in subtotal_ordinals],
            result=row_records[total_ordinal],
        )
        if equation is None:
            continue
        equations.append(equation)
        consumed_ordinals.update({total_ordinal, *subtotal_ordinals, *uncovered})
        proven_carrier_children[total_ordinal].update(subtotal_ordinals)

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
        equation = configured_complete_source_equation(
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

    # A source may print one net carrier, repeat the same label for its gross
    # amount, and terminate the contiguous child frontier with one signed
    # adjustment (for example a deposit/margin deduction).  Gemini is not
    # required to reconstruct that graph: the declarative role sequence and
    # source order select the bounded frontier, while arithmetic only proves
    # or vetoes it.  This also repairs a generic hierarchy-loss variant where
    # punctuation was flattened out of ``hierarchy_path_exact``.
    signed_context_frontier_receipts = []
    for declaration in compiled_specs.get("signed_context_frontier_equations", []):
        carrier_role = declaration["carrier_role"]
        carrier_ordinals = sorted(
            ordinal for ordinal, role in hit_by_row.items() if role == carrier_role
        )
        if len(carrier_ordinals) != 2:
            continue
        carrier_ordinal, repeated_ordinal = carrier_ordinals
        allowed_roles = set(declaration["allowed_component_roles"])
        source_adjustment_roles = set(declaration["source_adjustment_roles"])
        component_axis = []
        for ordinal in range(carrier_ordinal + 1, len(rows) + 1):
            record = row_records.get(ordinal)
            role = hit_by_row.get(ordinal)
            if record is None or role not in allowed_roles:
                break
            component_axis.append((ordinal, record))
            if role in source_adjustment_roles:
                break
        if (
            not component_axis
            or component_axis[-1][0] <= repeated_ordinal
            or component_axis[-1][0] != carrier_ordinal + len(component_axis)
            or repeated_ordinal not in {ordinal for ordinal, _record in component_axis}
            or sum(hit_by_row[ordinal] == carrier_role for ordinal, _record in component_axis) != 1
            or sum(
                hit_by_row[ordinal] in source_adjustment_roles
                for ordinal, _record in component_axis
            )
            != 1
            or hit_by_row[component_axis[-1][0]] not in source_adjustment_roles
        ):
            continue
        adjustment_ordinal = component_axis[-1][0]
        adjustment_record = row_records[adjustment_ordinal]
        if any(
            cell["coefficient"] is not None and cell["coefficient"] > 0
            for cell in adjustment_record["cells"]
        ):
            continue
        component_ordinals = [ordinal for ordinal, _record in component_axis]
        existing_equations = [
            equation
            for equation in equations
            if _is_complete_source_control_equation(equation)
            and {ref.get("row_ordinal") for ref in equation["result_source_refs"]}
            == {carrier_ordinal}
            and {
                ref.get("row_ordinal") for refs in equation["component_source_refs"] for ref in refs
            }
            == set(component_ordinals)
        ]
        if len(existing_equations) > 1:
            continue
        if existing_equations:
            equation = existing_equations[0]
        else:
            equation = configured_complete_source_equation(
                kind="EXACT_SIGNED_CONTEXT_CONTIGUOUS_FRONTIER_EQUALS_NET_CARRIER",
                components=[record for _ordinal, record in component_axis],
                result=row_records[carrier_ordinal],
            )
            if equation is None:
                continue
            equations.append(equation)
        resolved_adjustment_role = declaration["resolved_adjustment_role"]
        previous_adjustment_role = hit_by_row[adjustment_ordinal]
        hit_by_row[adjustment_ordinal] = resolved_adjustment_role
        for record in local_records:
            source_ordinals = {ref.get("row_ordinal") for ref in record.get("source_refs", [])}
            if source_ordinals == {adjustment_ordinal} and record["role"] in (
                source_adjustment_roles
            ):
                record["role"] = resolved_adjustment_role
        consumed_ordinals.update({carrier_ordinal, *component_ordinals})
        proven_carrier_children[carrier_ordinal].update(component_ordinals)
        proven_roles.update(hit_by_row[ordinal] for ordinal in component_ordinals)
        proven_roles.add(carrier_role)
        if repeated_ordinal not in shadowed_role_ordinals:
            shadowed_role_ordinals.add(repeated_ordinal)
            local_records = [
                record
                for record in local_records
                if {ref.get("row_ordinal") for ref in record.get("source_refs", [])}
                != {repeated_ordinal}
            ]
        signed_context_frontier_receipts.append(
            {
                "adjustment_row_ordinal": adjustment_ordinal,
                "carrier_role": carrier_role,
                "carrier_row_ordinal": carrier_ordinal,
                "component_row_ordinals": component_ordinals,
                "previous_adjustment_role": previous_adjustment_role,
                "repeated_carrier_row_ordinal": repeated_ordinal,
                "resolved_adjustment_role": resolved_adjustment_role,
                "rule": declaration["policy"],
                "source_equation_id": equation["equation_id"],
            }
        )

    # When Gemini flattens a compact hierarchy path into one string, the
    # shallower-path duplicate check above may not recognize a repeated
    # carrier/detail label.  An already-authenticated exact source equation
    # supplies a stronger structural receipt: exactly one same-role row is
    # its result and every other same-role occurrence is a component.  Keep
    # only that result row; never sum the carrier and its disclosed detail.
    equation_shadow_receipts = []
    for role, role_ordinals in ordinals_by_role.items():
        active_ordinals = [
            ordinal for ordinal in role_ordinals if ordinal not in shadowed_role_ordinals
        ]
        if len(active_ordinals) < 2:
            continue
        matches = []
        for equation in equations:
            if not _is_complete_source_control_equation(equation):
                continue
            result_ordinals = {
                ref.get("row_ordinal") for ref in equation.get("result_source_refs", [])
            }
            component_ordinals = {
                ref.get("row_ordinal")
                for refs in equation.get("component_source_refs", [])
                for ref in refs
            }
            if (
                len(result_ordinals) == 1
                and result_ordinals <= set(active_ordinals)
                and set(active_ordinals) - result_ordinals <= component_ordinals
            ):
                matches.append((next(iter(result_ordinals)), equation))
        if len(matches) != 1:
            continue
        carrier_ordinal, equation = matches[0]
        detail_ordinals = sorted(set(active_ordinals) - {carrier_ordinal})
        shadowed_role_ordinals.update(detail_ordinals)
        local_records = [
            record
            for record in local_records
            if not (
                record["role"] == role
                and {ref.get("row_ordinal") for ref in record.get("source_refs", [])}
                <= set(detail_ordinals)
            )
        ]
        equation_shadow_receipts.append(
            {
                "carrier_row_ordinal": carrier_ordinal,
                "detail_row_ordinals": detail_ordinals,
                "role": role,
                "rule": "UNIQUE_EXACT_SOURCE_EQUATION_RESULT_SHADOWS_SAME_ROLE_COMPONENTS",
                "source_equation_id": equation["equation_id"],
            }
        )
    hierarchical_duplicate_receipts.extend(equation_shadow_receipts)

    # A labelled SUBTOTAL can precede its direct children even when Gemini did
    # not repeat the hierarchy path.  Accept exactly one ordered prefix whose
    # source values close the subtotal; multiple closing prefixes are
    # ambiguous and remain unresolved.
    for carrier_ordinal in sorted(total_ordinals):
        if (
            carrier_ordinal in proven_carrier_children
            or (
                rows[carrier_ordinal - 1].get("row_kind") != "SUBTOTAL"
                and not (
                    carrier_ordinal in family_root_ordinals
                    and rows[carrier_ordinal - 1].get("row_kind") == "TOTAL"
                )
                and not (
                    compiled_specs["document_cluster_policy"]
                    == "DOCUMENT_EXACT_DECLARED_ROOT_COMPONENTS_PLUS_SOURCE_RESULT"
                    and hit_by_row.get(carrier_ordinal) in compiled_specs["root_component_roles"]
                    and rows[carrier_ordinal - 1].get("row_kind") == "TOTAL"
                )
            )
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
            equation = configured_complete_source_equation(
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
        if (
            carrier_ordinal in family_root_ordinals
            and carrier_ordinal not in source_visible_family_root_ordinals
            and any(
                cell["source_text"] is not None for cell in row_records[carrier_ordinal]["cells"]
            )
        ):
            carrier = row_records[carrier_ordinal]
            local_records.append(
                _local_record(
                    "FAMILY_ROOT_TOTAL",
                    carrier["cells"],
                    carrier["lane_keys"],
                    carrier["source_refs"],
                    "SOURCE_VISIBLE_FAMILY_ROOT_PROVEN_BY_ORDERED_CHILD_FRONTIER",
                    carrier["valuation_basis"],
                )
            )
            source_visible_family_root_ordinals.add(carrier_ordinal)
            proven_roles.add("FAMILY_ROOT_TOTAL")

    # Then prove each printed subtotal/total against exactly one source frontier.
    for total_ordinal in sorted(total_ordinals):
        total = row_records[total_ordinal]
        ordered_stage_starts = {
            item["start_row_ordinal"]
            for item in classification.get("ordered_role_scope_receipts", [])
            if item["status"] == "UNIQUE_ORDERED_ROLE_SCOPE_APPLIED"
            and item["terminal_row_ordinal"] == total_ordinal
        }
        ordered_stage_start = (
            next(iter(ordered_stage_starts)) if len(ordered_stage_starts) == 1 else 0
        )
        candidates: list[tuple[str, list[tuple[int, dict[str, Any]]]]] = []
        preceding = [
            (
                ordinal,
                label_only_group_proxies.get(ordinal, ([], record))[1],
            )
            for ordinal, record in row_records.items()
            if ordered_stage_start < ordinal < total_ordinal and ordinal not in total_ordinals
            if _record_has_observed_lane(
                label_only_group_proxies.get(ordinal, ([], record))[1]
            )
        ]
        if preceding:
            candidates.append(("ALL_PRECEDING_NON_TOTAL_ROWS", preceding))
        prior_total = max(
            (
                ordinal
                for ordinal in total_ordinals
                if ordered_stage_start < ordinal < total_ordinal
            ),
            default=ordered_stage_start,
        )
        interval_source = [
            (ordinal, record)
            for ordinal, record in row_records.items()
            if prior_total < ordinal < total_ordinal and ordinal not in total_ordinals
        ]
        interval = [
            (ordinal, record)
            for ordinal, record in interval_source
            if _record_has_observed_lane(record)
        ]
        if interval and interval != preceding:
            candidates.append(("SINCE_PRIOR_TOTAL", interval))
        # Suppress descendants of a visible-valued ancestor from the table's
        # top-level direct frontier; their own hierarchy equation above is the
        # sole consumer of those descendants.
        frontier_lower_bound = (
            prior_total
            if compiled_specs["document_cluster_policy"]
            == "DOCUMENT_EXACT_DECLARED_ROOT_COMPONENTS_PLUS_SOURCE_RESULT"
            else ordered_stage_start
        )
        labelled_hierarchy_carriers = [
            (ordinal, row_records[ordinal])
            for ordinal in total_ordinals
            if frontier_lower_bound < ordinal < total_ordinal
            and (
                proven_carrier_children.get(ordinal)
                or (
                    compiled_specs["mapped_source_subtotal_policy"]
                    in {
                        "ALLOW_SOURCE_VISIBLE_ROOT_COMPONENT_CONSUMED_BY_EXACT_ROOT_EQUATION",
                        (
                            "ALLOW_SOURCE_VISIBLE_DECLARED_ROLE_WITH_NONADDITIVE_CHILDREN_OR_"
                            "ROOT_COMPONENT_EQUATION"
                        ),
                    }
                    and _normalized(rows[ordinal - 1].get("label_exact"))
                    and any(
                        cell["source_text"] is not None for cell in row_records[ordinal]["cells"]
                    )
                )
            )
        ]
        # ``interval`` deliberately retains the raw source rows for the
        # ordinary SINCE_PRIOR_TOTAL candidate above.  The canonical
        # top-level frontier, however, must use the already authenticated
        # direct-child proxy for a label-only structural GROUP.  Otherwise a
        # second sibling population after a printed subtotal contributes an
        # all-blank carrier instead of its exact child sum, while the first
        # population (which happens to use ``preceding``) succeeds.  Apply the
        # same projection symmetrically on both sides of a prior total.
        top_level_preceding = [
            (
                ordinal,
                label_only_group_proxies.get(ordinal, ([], record))[1],
            )
            for ordinal, record in (
                interval_source
                if frontier_lower_bound and interval_source
                else [item for item in preceding if item[0] > frontier_lower_bound]
            )
            if _record_has_observed_lane(
                label_only_group_proxies.get(ordinal, ([], record))[1]
            )
        ]
        top_level_source = sorted(
            [*top_level_preceding, *labelled_hierarchy_carriers], key=lambda item: item[0]
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
            if re.match(r"^(?:trong do|of which)\b", normalized_label) is not None or (
                len(hierarchy_path) > 1
                and re.match(r"^(?:trong do|of which)\b", hierarchy_path[0]) is not None
            ):
                # A source-visible "Trong đó / Of which" row is a disclosed
                # subset, never an additional component of an encompassing
                # total. It remains independently mappable when declared.
                continue
            declared_role = hit_by_row.get(ordinal)
            if (
                declared_role is not None
                and compiled_specs["child_by_role"][declared_role]["role_kind"]
                == "NONADDITIVE_CHILD"
            ):
                # A declared disclosure subset is not an additive peer even
                # when Gemini flattens or corrupts its wrapper hierarchy.  The
                # declarative role kind is the authoritative graph edge;
                # values never decide exclusion from the parent frontier.
                continue
            if any(
                other_ordinal != ordinal
                and (
                    ordinal in proven_descendants(other_ordinal)
                    or (
                        compiled_specs["mapped_source_subtotal_policy"]
                        in {
                            "ALLOW_SOURCE_VISIBLE_ROOT_COMPONENT_CONSUMED_BY_EXACT_ROOT_EQUATION",
                            (
                                "ALLOW_SOURCE_VISIBLE_DECLARED_ROLE_WITH_NONADDITIVE_CHILDREN_OR_"
                                "ROOT_COMPONENT_EQUATION"
                            ),
                        }
                        and any(
                            cell["source_text"] is not None
                            for cell in row_records[other_ordinal]["cells"]
                        )
                        and _row_is_strict_descendant(rows, ordinal, other_ordinal)
                    )
                )
                for other_ordinal, _other in top_level_source
            ):
                continue
            top_level.append((ordinal, record))
        if top_level and top_level != preceding:
            top_level_candidate = ("VISIBLE_TOP_LEVEL_DIRECT_FRONTIER", top_level)
            if compiled_specs["direct_frontier_policy"] in {
                "CANONICAL_PROVEN_TOP_LEVEL_DIRECT_FRONTIER",
                "CANONICAL_PROVEN_OR_CONTIGUOUS_NUMBERED_TOP_LEVEL_DIRECT_FRONTIER",
            }:
                candidates = [top_level_candidate]
            else:
                candidates.append(top_level_candidate)

        # Some notes expose the exhaustive top level through a visible
        # ``1. ...`` through ``N. ...`` sequence while subordinate disclosure
        # rows are unnumbered or dash-prefixed and Gemini does not preserve a
        # usable hierarchy path for them.  The contiguous source ordinals are
        # structural evidence independent of values.  Use that frontier only
        # when it starts at one, has no gaps/duplicates, and its already chosen
        # rows later close the printed total on every lane.
        numbered_top_level = []
        numbered_values = []
        for ordinal, record in preceding:
            raw_label = rows[ordinal - 1].get("label_exact")
            match = (
                re.match(r"^\s*(?P<ordinal>[1-9][0-9]?)\s*[.)]\s+\S", raw_label)
                if type(raw_label) is str
                else None
            )
            if match is None:
                continue
            numbered_top_level.append((ordinal, record))
            numbered_values.append(int(match.group("ordinal")))
        if (
            compiled_specs["direct_frontier_policy"]
            == "CANONICAL_PROVEN_OR_CONTIGUOUS_NUMBERED_TOP_LEVEL_DIRECT_FRONTIER"
            and len(numbered_top_level) >= 2
            and numbered_values == list(range(1, len(numbered_values) + 1))
        ):
            numbered_candidate = (
                "SOURCE_VISIBLE_CONTIGUOUS_NUMBERED_TOP_LEVEL_FRONTIER",
                numbered_top_level,
            )
            candidates = [numbered_candidate]
        if (
            compiled_specs["direct_frontier_policy"]
            in {
                "CANONICAL_PROVEN_TOP_LEVEL_DIRECT_FRONTIER",
                "CANONICAL_PROVEN_OR_CONTIGUOUS_NUMBERED_TOP_LEVEL_DIRECT_FRONTIER",
            }
            and prior_total in set(classification.get("family_root_row_ordinals", []))
            and prior_total < total_ordinal
        ):
            candidates = [
                (
                    "EXPLICIT_FAMILY_ROOT_ROW_EQUALS_PRINTED_TOTAL",
                    [(prior_total, row_records[prior_total])],
                )
            ]
        preexisting_result_equations = [
            equation
            for equation in equations
            if _is_complete_source_control_equation(equation)
            and {ref.get("row_ordinal") for ref in equation.get("result_source_refs", [])}
            == {total_ordinal}
        ]
        if len(preexisting_result_equations) == 1:
            preexisting_component_ordinals = [
                ref.get("row_ordinal")
                for refs in preexisting_result_equations[0]["component_source_refs"]
                for ref in refs
            ]
            if (
                preexisting_component_ordinals
                and None not in preexisting_component_ordinals
                and len(preexisting_component_ordinals) == len(set(preexisting_component_ordinals))
                and set(preexisting_component_ordinals) <= set(row_records)
            ):
                candidates = [
                    (
                        "PREEXISTING_EXACT_STRUCTURAL_FRONTIER",
                        [
                            (ordinal, row_records[ordinal])
                            for ordinal in preexisting_component_ordinals
                        ],
                    )
                ]
        if (
            compiled_specs.get("root_component_role_combinations")
            and total_ordinal == max(row_records)
        ):
            configured_frontiers = []
            for declaration in compiled_specs["root_component_role_combinations"]:
                axis = []
                for role in declaration["roles"]:
                    role_rows = [
                        (ordinal, row_records[ordinal])
                        for ordinal, row_role in sorted(hit_by_row.items())
                        if row_role == role
                        and ordinal < total_ordinal
                        and ordinal in proven_carrier_children
                    ]
                    if len(role_rows) != 1:
                        axis = []
                        break
                    axis.extend(role_rows)
                if axis:
                    configured_frontiers.append(axis)
            if len(configured_frontiers) == 1:
                candidates = [
                    ("CONFIGURED_COMPLETE_ROOT_COMPONENT_ALTERNATIVE", configured_frontiers[0])
                ]
            elif configured_frontiers:
                candidates = []
        matches = []
        for kind, component_axis in candidates:
            selected_root_component_declaration = None
            if compiled_specs.get("root_component_role_combinations"):
                roles_by_ordinal = [hit_by_row.get(ordinal) for ordinal, _record in component_axis]
                complete_declarations = [
                    declaration
                    for declaration in compiled_specs["root_component_role_combinations"]
                    if len(roles_by_ordinal) == len(declaration["roles"])
                    and set(roles_by_ordinal) == set(declaration["roles"])
                    and all(roles_by_ordinal.count(role) == 1 for role in declaration["roles"])
                ]
                if len(complete_declarations) != 1:
                    continue
                selected_root_component_declaration = complete_declarations[0]
                by_declared_role = {
                    hit_by_row[ordinal]: (ordinal, record)
                    for ordinal, record in component_axis
                }
                component_axis = [
                    by_declared_role[role]
                    for role in selected_root_component_declaration["roles"]
                ]
            signed_source_root = bool(
                document_source_result_carrier
                and total_ordinal in family_root_ordinals
                and (
                    selected_root_component_declaration or {}
                ).get(
                    "equation_policy", compiled_specs["root_component_equation_policy"]
                )
                == "UNIQUE_DECLARED_SIGN_ORIENTATION_FIRST_COMPONENT_POSITIVE"
            )
            if signed_source_root:
                # An income statement may print service expense either as a
                # negative coefficient or as a positive magnitude.  The
                # source-visible net row selects neither convention by label
                # or value.  Require the already-selected direct frontier to
                # contain each declared root component exactly once, order it
                # by the declarative graph, and accept only one +/-1
                # orientation with the first component positive.  This is a
                # source equation veto/proof, not a backsolve.
                selected_root_roles = (
                    selected_root_component_declaration["roles"]
                    if selected_root_component_declaration is not None
                    else compiled_specs["root_component_roles"]
                )
                by_root_role: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
                for ordinal, record in component_axis:
                    role = hit_by_row.get(ordinal)
                    if role in selected_root_roles:
                        by_root_role[role].append((ordinal, record))
                if any(
                    len(by_root_role.get(role, [])) != 1
                    for role in selected_root_roles
                ) or len(component_axis) != len(selected_root_roles):
                    continue
                ordered_component_axis = [
                    by_root_role[role][0] for role in selected_root_roles
                ]
                multiplier_candidates = [
                    [1, *suffix]
                    for suffix in product(
                        (-1, 1),
                        repeat=max(0, len(ordered_component_axis) - 1),
                    )
                    if _local_equation(
                        equation_kind=(
                            "EXACT_UNIQUE_DECLARED_ROOT_COMPONENT_SIGN_ORIENTATION_"
                            "EQUAL_PRINTED_TOTAL"
                        ),
                        components=[record for _ordinal, record in ordered_component_axis],
                        result=total,
                        multipliers=[1, *suffix],
                    )["status"]
                    == "EXACT"
                ]
                if len(multiplier_candidates) != 1:
                    continue
                component_axis = ordered_component_axis
                equation = _local_equation(
                    equation_kind=(
                        "EXACT_UNIQUE_DECLARED_ROOT_COMPONENT_SIGN_ORIENTATION_EQUAL_PRINTED_TOTAL"
                    ),
                    components=[record for _ordinal, record in component_axis],
                    result=total,
                    multipliers=multiplier_candidates[0],
                )
            else:
                equation = _exact_equation(
                    kind="EXACT_" + kind + "_EQUAL_PRINTED_TOTAL",
                    components=[record for _ordinal, record in component_axis],
                    result=total,
                )
                if equation is None and compiled_specs[
                    "source_presentation_rounding_policy"
                ] == "INDEPENDENT_DISPLAY_UNIT_ROUNDING_INTERVAL_ALL_EQUATIONS":
                    equation = _source_presentation_rounding_equation(
                        kind="EXACT_" + kind + "_EQUAL_PRINTED_TOTAL",
                        components=[record for _ordinal, record in component_axis],
                        result=total,
                        canonical_unit=unit_axis["canonical_unit"],
                        magnitude_power10=selected_unit_magnitude_power10,
                    )
                if equation is None and (
                    compiled_specs["source_total_blank_lane_control_policy"]
                    == "OBSERVED_LANES_EXACT_REMAINDER_BLANK"
                    or any(
                        ordinal in label_only_group_proxies
                        for ordinal, _record in component_axis
                    )
                ):
                    # A source-visible label-only structural group can be
                    # projected from its child frontier independently by lane.
                    # This admits the printed total only as an observed-lane
                    # control; ordinary leaf-only totals remain exact-only.
                    equation = _observed_lane_control_equation(
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
        if (
            not unique
            and compiled_specs.get("source_hierarchy_overlap_total_policy")
            == "MAP_EXACT_PRINTED_TOTAL_WITH_OVERLAPPING_SOURCE_HIERARCHY_RECEIPT"
        ):
            visible_component_axis = [
                (ordinal, record)
                for ordinal, record in sorted(row_records.items())
                if frontier_lower_bound < ordinal < total_ordinal
                and ordinal not in total_ordinals
                and any(cell["source_text"] is not None for cell in record["cells"])
            ]
            visible_ordinals = {ordinal for ordinal, _record in visible_component_axis}
            overlap_edges = sorted(
                {
                    (carrier_ordinal, child_ordinal)
                    for carrier_ordinal in visible_ordinals
                    for child_ordinal in proven_descendants(carrier_ordinal)
                    if child_ordinal in visible_ordinals
                }
            )
            overlap_carriers_are_validation_only = bool(overlap_edges) and all(
                hit_by_row.get(carrier_ordinal) in set(compiled_specs["validation_only_roles"])
                for carrier_ordinal, _child_ordinal in overlap_edges
            )
            overlap_equation = (
                configured_complete_source_equation(
                    kind=(
                        "EXACT_PRINTED_TOTAL_EQUALS_SOURCE_VISIBLE_HIERARCHY_OVERLAPPING_FRONTIER"
                    ),
                    components=[record for _ordinal, record in visible_component_axis],
                    result=total,
                )
                if overlap_carriers_are_validation_only
                else None
            )
            if overlap_equation is not None:
                unique = {
                    tuple(ordinal for ordinal, _record in visible_component_axis): (
                        "SOURCE_VISIBLE_HIERARCHY_OVERLAPPING_FRONTIER",
                        visible_component_axis,
                        overlap_equation,
                    )
                }
                source_hierarchy_overlap_total_receipts.append(
                    {
                        "component_row_ordinals": sorted(visible_ordinals),
                        "overlap_edges": [
                            {
                                "carrier_row_ordinal": carrier_ordinal,
                                "child_row_ordinal": child_ordinal,
                            }
                            for carrier_ordinal, child_ordinal in overlap_edges
                        ],
                        "result_row_ordinal": total_ordinal,
                        "rule": (
                            "PRINTED_TOTAL_PRESERVED_ONLY_WHEN_EXACT_RAW_VISIBLE_ROW_"
                            "SUM_EXPLICITLY_DOUBLE_COUNTS_A_PROVEN_SOURCE_HIERARCHY"
                        ),
                        "source_equation_id": overlap_equation["equation_id"],
                    }
                )
        if len(unique) != 1:
            continue
        _kind, component_axis, equation = next(iter(unique.values()))
        component_ordinals = {ordinal for ordinal, _record in component_axis}
        existing_same_frontier = [
            existing
            for existing in equations
            if _is_complete_source_control_equation(existing)
            and {ref.get("row_ordinal") for ref in existing.get("result_source_refs", [])}
            == {total_ordinal}
            and {
                ref.get("row_ordinal")
                for refs in existing.get("component_source_refs", [])
                for ref in refs
            }
            == component_ordinals
        ]
        if len(existing_same_frontier) == 1:
            equation = existing_same_frontier[0]
        else:
            equations.append(equation)
        proven_carrier_children[total_ordinal].update(
            ordinal for ordinal, _record in component_axis
        )
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
            if _is_complete_source_control_equation(equation):
                proven_roles.add(role)
            # A complete source-total equation proves each declared direct
            # child role. A lane-local equation still permits the structural
            # projection above, but deliberately supplies no role-wide proof:
            # every blank source lane remains null and unusable in arithmetic.
            if _is_complete_source_control_equation(equation) and compiled_specs[
                "duplicate_role_aggregation_policy"
            ] == (
                "ALL_SOURCE_ROWS_CONSUMED_BY_EXACT_TABLE_FRONTIER"
            ):
                proven_roles.update(
                    hit_by_row[child_ordinal]
                    for child_ordinal in child_ordinals
                    if child_ordinal in hit_by_row
                )
        if _is_complete_source_control_equation(equation):
            proven_roles.update(
                hit_by_row[ordinal]
                for ordinal, _record in component_axis
                if ordinal in hit_by_row
            )
            if total_ordinal in hit_by_row:
                proven_roles.add(hit_by_row[total_ordinal])
        component_hit_roles = {
            hit_by_row[ordinal] for ordinal, _record in component_axis if ordinal in hit_by_row
        }
        validation_projection_targets_by_source: dict[str, set[str]] = defaultdict(set)
        for projection in [
            *compiled_specs.get("validation_role_leaf_projections", []),
            *compiled_specs["ordered_role_scope_projections"],
        ]:
            validation_projection_targets_by_source[projection["source_role"]].add(
                projection["target_role"]
            )
        root_eligible_component_hit_roles = {
            target_role
            for role in component_hit_roles
            for target_role in (validation_projection_targets_by_source.get(role, {role}))
        }
        root_component_role_axes = (
            [
                set(declaration["roles"])
                for declaration in compiled_specs["root_component_role_combinations"]
            ]
            if compiled_specs.get("root_component_role_combinations")
            else [set(compiled_specs["root_component_roles"])]
        )
        matching_root_component_role_axes = [
            axis for axis in root_component_role_axes if root_eligible_component_hit_roles == axis
        ]
        selected_root_component_roles = (
            matching_root_component_role_axes[0]
            if len(matching_root_component_role_axes) == 1
            else set(compiled_specs["root_component_roles"])
        )
        root_component_role_axis_is_unique = bool(
            not compiled_specs.get("root_component_role_combinations")
            or len(matching_root_component_role_axes) == 1
        )
        explicit_root_row_equals_total = bool(
            len(component_axis) == 1 and component_axis[0][0] in family_root_ordinals
        )
        # A combined statement can contain the requested family followed by a
        # different sibling population and a final net total.  Once the source
        # exposes one explicit family-root row, only that row or a printed
        # subtotal inside its authenticated hierarchy subtree may represent
        # the family root.  Arithmetic closure of a later sibling/net total is
        # corroboration for that other population, never permission to reuse
        # it as this family's root.
        total_inside_explicit_family_root = bool(
            not scope_to_explicit_family_root
            or total_ordinal in family_root_ordinals
            or any(
                _row_is_strict_descendant(rows, total_ordinal, root_ordinal)
                for root_ordinal in family_root_ordinals
            )
        )
        source_visible_family_root_already_emitted = bool(source_visible_family_root_ordinals)
        context_roles = classification["context_roles"]
        context_role = context_roles[0] if len(context_roles) == 1 else None
        other_context_carriers = component_hit_roles.intersection(
            compiled_specs["table_context_roles"]
        ) - ({context_role} if context_role is not None else set())

        def role_is_declared_within(role: str, context: str) -> bool:
            pending = [role]
            seen = set()
            while pending:
                current = pending.pop()
                if current == context:
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

        context_total_preferred = bool(
            context_role in compiled_specs["context_total_mapping_roles"]
            and not other_context_carriers
            and (
                classification["context_resolution_kind"]
                in {
                    "EXPLICIT_TABLE_TITLE",
                    "EXPLICIT_TITLELESS_ORDERED_TABLE_SECTION_NARRATIVE",
                    "EXPLICIT_TITLELESS_SOLE_TABLE_SECTION_NARRATIVE",
                    "EXPLICIT_SOLE_TABLE_SECTION_TITLE",
                }
                or (
                    context_role not in component_hit_roles
                    and component_hit_roles
                    and any(
                        role_is_declared_within(role, context_role) for role in component_hit_roles
                    )
                    and all(
                        role_is_declared_within(role, context_role)
                        or role
                        in {
                            declaration["residual_role"]
                            for declaration in compiled_specs["supplemental_detail_residuals"]
                        }
                        for role in component_hit_roles
                    )
                )
            )
        )
        if compiled_specs["schema"]["root_mapping_policy"] == "STRUCTURAL_CONTEXT_ONLY":
            # Some TM families use the family root solely as an authenticated
            # owner for several non-additive numeric disclosures.  A source
            # row that Gemini happens to classify as TOTAL must not turn one
            # of those child measures into a synthetic family-root value.
            root_total_emitted = False
        elif (
            compiled_specs["schema"]["root_mapping_policy"]
            == "SOURCE_VISIBLE_TOTAL_OR_COMPLETE_TOP_LEVEL_COMPONENT_SUM"
        ):
            terminal_total = not any(ordinal > total_ordinal for ordinal in row_records)
            owner_complete_total_frontier = False
            if compiled_specs.get("owner_complete_population_policy") == (
                "EXACT_OWNER_WHOLE_MONEY_TABLE"
            ) and classification.get("owner_visible"):
                source_total_ordinals = {
                    item["row_ordinal"] for item in classification.get("total_rows", [])
                }
                source_population_ordinals = (
                    {hit["row_ordinal"] for hit in classification.get("role_hits", [])}
                    | set(classification.get("unbound_money_row_ordinals", []))
                    | source_total_ordinals
                )
                direct_component_ordinals = {ordinal for ordinal, _record in component_axis}
                owner_complete_total_frontier = bool(
                    terminal_total
                    and source_total_ordinals == {total_ordinal}
                    and direct_component_ordinals
                    and direct_component_ordinals == source_population_ordinals - {total_ordinal}
                )
            root_total_emitted = bool(
                explicit_root_row_equals_total
                or (
                    not context_total_preferred
                    and terminal_total
                    and component_hit_roles
                    and root_component_role_axis_is_unique
                    and root_eligible_component_hit_roles
                    <= selected_root_component_roles
                )
                or (
                    not context_total_preferred
                    and terminal_total
                    and bool(classification.get("inverted_hierarchy_scope_rows"))
                    and classification["family_presence_anchor_visible"]
                )
                or (not context_total_preferred and owner_complete_total_frontier)
            )
        elif compiled_specs["schema"]["root_mapping_policy"] in {
            "SOURCE_VISIBLE_PRIMARY_RESULT_OR_EXACT_NOTE_EQUATION",
            "SOURCE_VISIBLE_TOTAL_PROVEN_BY_EXACT_EQUATION_ONLY",
        }:
            # This policy deliberately forbids synthesizing a schema-root
            # mapping for an owner-complete table that does not print one.
            # When the source contains several independently closed
            # subtotals, only the terminal exact total is the family result;
            # an earlier subtotal remains a structural component even though
            # its own local equation is exact.
            later_value_rows = [
                ordinal for ordinal in row_records if ordinal > total_ordinal
            ]
            if compiled_specs["family_root_terminal_scope_policy"] == (
                "LAST_SOURCE_TOTAL_WITHIN_EXPLICIT_FAMILY_ROOT_SUBTREE"
            ):
                # A combined statement can print a completed family subtotal
                # and then a separately declared net-result control. The
                # latter is outside this family's source subtree when its
                # exact label is a compiled hard-negative boundary; an
                # unknown or merely similar later row still blocks terminal
                # status and keeps the family unresolved.
                family_subtree_boundary_aliases = {
                    *compiled_specs["query_policy"]["hard_negative_aliases"],
                    *compiled_specs["query_policy"].get("supplemental_owner_aliases", []),
                }
                later_value_rows = [
                    ordinal
                    for ordinal in later_value_rows
                    if not any(
                        _matches(rows[ordinal - 1].get("label_exact"), alias)
                        for alias in family_subtree_boundary_aliases
                    )
                ]
            terminal_total = not later_value_rows
            terminal_closed_structural_group_total = bool(
                terminal_total
                and equation.get("equation_kind")
                == "EXACT_CLOSED_STRUCTURAL_GROUP_SUBTOTALS_EQUAL_TERMINAL_TOTAL"
            )
            source_total_equation_usable = bool(
                equation["status"] == "EXACT"
                or (
                    compiled_specs["source_presentation_rounding_policy"]
                    == "INDEPENDENT_DISPLAY_UNIT_ROUNDING_INTERVAL_ALL_EQUATIONS"
                    and equation["status"]
                    == "SOURCE_PRESENTATION_ROUNDING_INTERVAL_EXACT"
                )
                or (
                    compiled_specs["source_total_blank_lane_control_policy"]
                    == "OBSERVED_LANES_EXACT_REMAINDER_BLANK"
                    and _is_observed_lane_control_equation(equation)
                )
            )
            root_total_emitted = bool(
                source_total_equation_usable
                and (
                    explicit_root_row_equals_total
                    or terminal_closed_structural_group_total
                    or (
                        not context_total_preferred
                        and terminal_total
                        and component_hit_roles
                        and root_component_role_axis_is_unique
                        and root_eligible_component_hit_roles
                        <= selected_root_component_roles
                        and len(component_hit_roles)
                        >= compiled_specs["evaluation"].get(
                            "minimum_source_visible_root_component_count", 2
                        )
                    )
                )
            )
        else:
            root_total_emitted = bool(
                explicit_root_row_equals_total
                or (
                    not context_total_preferred
                    and component_hit_roles
                    and root_component_role_axis_is_unique
                    and root_eligible_component_hit_roles
                    <= selected_root_component_roles
                    and len(component_hit_roles)
                    >= compiled_specs["evaluation"].get(
                        "minimum_source_visible_root_component_count", 2
                    )
                )
            )
        root_total_emitted = bool(
            root_total_emitted
            and total_inside_explicit_family_root
            and not source_visible_family_root_already_emitted
        )
        if root_total_emitted:
            local_records.append(
                _local_record(
                    "FAMILY_ROOT_TOTAL",
                    total["cells"],
                    total["lane_keys"],
                    total["source_refs"],
                    (
                        "SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_BY_DIRECT_FRONTIER"
                        if equation["status"] == "EXACT"
                        else (
                            "SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_WITHIN_"
                            "DISPLAY_UNIT_ROUNDING_INTERVAL"
                            if equation["status"]
                            == "SOURCE_PRESENTATION_ROUNDING_INTERVAL_EXACT"
                            else "SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_WITH_"
                            "INCOMPLETE_BLANK_LANE_CONTROL"
                        )
                    ),
                    total["valuation_basis"],
                )
            )
            source_visible_family_root_ordinals.add(total_ordinal)
            if _is_complete_source_control_equation(equation):
                proven_roles.add("FAMILY_ROOT_TOTAL")
        existing_context_role_records = (
            []
            if len(context_roles) != 1
            else [record for record in local_records if record["role"] == context_roles[0]]
        )
        component_axis_ordinals = {ordinal for ordinal, _record in component_axis}
        replaceable_nested_context_records = bool(
            context_total_preferred
            and existing_context_role_records
            and all(
                {source_ref.get("row_ordinal") for source_ref in record.get("source_refs", [])}
                <= component_axis_ordinals
                for record in existing_context_role_records
            )
        )
        if replaceable_nested_context_records:
            # A table title can declare the structural role while a same-label
            # row inside the table is only one additive branch.  When the
            # terminal total has already closed over that row and every other
            # direct branch, the title-scoped total is the role observation;
            # retaining the nested row would silently under-map the source.
            local_records = [
                record for record in local_records if record not in existing_context_role_records
            ]
        if (
            len(context_roles) == 1
            and not root_total_emitted
            and context_roles[0] in compiled_specs["context_total_mapping_roles"]
            and not any(
                role == context_roles[0]
                and ordinal in row_records
                and not _record_has_observed_lane(row_records[ordinal])
                for ordinal, role in hit_by_row.items()
            )
            and (
                replaceable_nested_context_records
                or not any(record["role"] == context_roles[0] for record in local_records)
            )
            and (
                not component_hit_roles
                or all(
                    role_is_declared_within(role, context_roles[0]) for role in component_hit_roles
                )
            )
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

    cross_fragment_same_role_parent_equation_receipts = []
    cross_fragment_same_role_detail_ordinals: set[int] = set()
    if (
        compiled_specs.get(
            "cross_fragment_same_role_parent_equation_policy", "DISABLED"
        )
        == (
            "EXACT_ADJACENT_PRIOR_TERMINAL_COLON_SAME_ROLE_PARENT_EQUALS_"
            "RECEIVER_LEADING_DETAIL_SUM_ALL_LANES"
        )
        and type(prior_fragment) is dict
        and table.get("continuation") == "CONTINUES_FROM_PREVIOUS_PAGE"
    ):
        prior_table = prior_fragment.get("table")
        prior_region = prior_fragment.get("region")
        prior_lane_axis = prior_fragment.get("lane_axis")
        prior_unit_axis = prior_fragment.get("unit_axis")
        prior_classification = prior_fragment.get("classification")
        prior_rows = prior_table.get("rows") if type(prior_table) is dict else None
        exact_fragment_pair = bool(
            type(prior_region) is dict
            and type(prior_lane_axis) is dict
            and type(prior_unit_axis) is dict
            and type(prior_classification) is dict
            and type(prior_rows) is list
            and prior_region.get("document_id") == region["document_id"]
            and prior_region.get("source_sha256") == region["source_sha256"]
            and prior_region.get("selected_page_ordinal")
            == region["selected_page_ordinal"] - 1
            and prior_region.get("physical_page") == region["physical_page"] - 1
            and prior_lane_axis.get("complete") is True
            and prior_lane_axis.get("lane_keys") == lane_axis["lane_keys"]
            and prior_unit_axis.get("complete") is True
            and prior_unit_axis.get("canonical_unit") == unit_axis["canonical_unit"]
        )
        prior_value_records: dict[int, dict[str, Any]] = {}
        if exact_fragment_pair:
            for prior_ordinal, prior_row in enumerate(prior_rows, start=1):
                if type(prior_row) is not dict:
                    continue
                try:
                    prior_record = _row_local_record(
                        "SOURCE_ROW",
                        prior_ordinal,
                        prior_row,
                        region=prior_region,
                        lane_axis=prior_lane_axis,
                        state="SOURCE_OBSERVED_ROW",
                    )
                except (IndexError, TypeError, ValueError):
                    prior_record = None
                if prior_record is not None and any(
                    cell["source_text"] is not None for cell in prior_record["cells"]
                ):
                    prior_value_records[prior_ordinal] = prior_record
        terminal_prior_ordinal = (
            max(prior_value_records) if prior_value_records else None
        )
        parent_candidates = []
        if terminal_prior_ordinal is not None:
            for hit in prior_classification.get("role_hits", []):
                parent_ordinal = hit["row_ordinal"]
                parent_role = hit["role"]
                parent_row = prior_rows[parent_ordinal - 1]
                if (
                    parent_ordinal != terminal_prior_ordinal
                    or parent_role not in compiled_specs["bindings"]
                    or parent_row.get("row_kind") != "ITEM"
                    or not (
                        type(parent_row.get("label_exact")) is str
                        and parent_row["label_exact"].rstrip().endswith(":")
                    )
                ):
                    continue
                ordered_receiver_ordinals = sorted(row_records)
                leading_detail_ordinals = []
                for receiver_ordinal in ordered_receiver_ordinals:
                    if hit_by_row.get(receiver_ordinal) != parent_role:
                        break
                    leading_detail_ordinals.append(receiver_ordinal)
                if len(leading_detail_ordinals) < 2:
                    continue
                parent = prior_value_records[parent_ordinal]
                details = [row_records[ordinal] for ordinal in leading_detail_ordinals]
                if any(
                    cell["source_text"] is None
                    for record in [parent, *details]
                    for cell in record["cells"]
                ):
                    continue
                equation = _exact_equation(
                    kind=(
                        "EXACT_ADJACENT_PRIOR_TERMINAL_COLON_SAME_ROLE_PARENT_"
                        "EQUALS_RECEIVER_LEADING_DETAIL_SUM_ALL_LANES"
                    ),
                    components=details,
                    result=parent,
                )
                if equation is not None:
                    parent_candidates.append(
                        (
                            parent_ordinal,
                            parent_role,
                            leading_detail_ordinals,
                            equation,
                        )
                    )
        if len(parent_candidates) == 1:
            parent_ordinal, parent_role, detail_ordinals, equation = parent_candidates[0]
            detail_ordinal_set = set(detail_ordinals)
            local_records = [
                record
                for record in local_records
                if not (
                    record["role"] == parent_role
                    and {
                        source_ref.get("row_ordinal")
                        for source_ref in record.get("source_refs", [])
                    }
                    <= detail_ordinal_set
                )
            ]
            equations.append(equation)
            consumed_ordinals.update(detail_ordinal_set)
            cross_fragment_same_role_detail_ordinals.update(detail_ordinal_set)
            proven_roles.add(parent_role)
            cross_fragment_same_role_parent_equation_receipts.append(
                {
                    "detail_row_ordinals": detail_ordinals,
                    "equation_id": equation["equation_id"],
                    "lane_axis": canonical_clone_v1(lane_axis),
                    "parent_row_ordinal": parent_ordinal,
                    "prior_region": canonical_clone_v1(prior_region),
                    "receiver_region": canonical_clone_v1(region),
                    "role": parent_role,
                    "rule": (
                        "EXACT_ADJACENT_PRIOR_TERMINAL_COLON_SAME_ROLE_PARENT_"
                        "EQUALS_RECEIVER_LEADING_DETAIL_SUM_ALL_LANES"
                    ),
                    "unit_axis": canonical_clone_v1(unit_axis),
                }
            )

    adjacent_continuation_family_root_receipt = None
    adjacent_continuation_family_root_incomplete_receipt = None
    if (
        compiled_specs.get("adjacent_continuation_family_root_policy", "DISABLED")
        == "EXACT_UNION_OF_DECLARED_ROOT_COMPONENTS_EQUALS_RECEIVER_TERMINAL_TOTAL"
        and compiled_specs["root_component_equation_policy"] == "DECLARED_DIRECT_SUM"
        and compiled_specs["schema"]["root_mapping_policy"]
        in {
            "SOURCE_VISIBLE_PRIMARY_RESULT_OR_EXACT_NOTE_EQUATION",
            "SOURCE_VISIBLE_TOTAL_PROVEN_BY_EXACT_EQUATION_ONLY",
        }
        and type(prior_fragment) is dict
        and not source_visible_family_root_ordinals
    ):
        prior_table = prior_fragment.get("table")
        prior_region = prior_fragment.get("region")
        prior_lane_axis = prior_fragment.get("lane_axis")
        prior_unit_axis = prior_fragment.get("unit_axis")
        prior_classification = prior_fragment.get("classification")
        prior_rows = prior_table.get("rows") if type(prior_table) is dict else None
        receiver_total_ordinals = [
            ordinal
            for ordinal in sorted(total_ordinals)
            if rows[ordinal - 1].get("row_kind") == "TOTAL"
        ]
        receiver_total_ordinal = (
            receiver_total_ordinals[0] if len(receiver_total_ordinals) == 1 else None
        )
        exact_fragment_pair = bool(
            type(prior_table) is dict
            and type(prior_region) is dict
            and type(prior_lane_axis) is dict
            and type(prior_unit_axis) is dict
            and type(prior_classification) is dict
            and type(prior_rows) is list
            and prior_table.get("continuation") == "CONTINUES_ON_NEXT_PAGE"
            and table.get("continuation") == "CONTINUES_FROM_PREVIOUS_PAGE"
            and prior_region.get("document_id") == region["document_id"]
            and prior_region.get("source_sha256") == region["source_sha256"]
            and prior_region.get("selected_page_ordinal")
            == region["selected_page_ordinal"] - 1
            and prior_region.get("physical_page") == region["physical_page"] - 1
            and prior_lane_axis.get("complete") is True
            and prior_lane_axis.get("lane_keys") == lane_axis["lane_keys"]
            and prior_unit_axis.get("complete") is True
            and prior_unit_axis.get("canonical_unit") == unit_axis["canonical_unit"]
            and not prior_classification.get("ambiguous_rows")
            and not classification.get("ambiguous_rows")
            and receiver_total_ordinal is not None
            and receiver_total_ordinal == max(row_records)
            and not _normalized(rows[receiver_total_ordinal - 1].get("label_exact"))
        )
        prior_records_by_ordinal: dict[int, dict[str, Any]] = {}
        if exact_fragment_pair:
            for prior_ordinal, prior_row in enumerate(prior_rows, start=1):
                if type(prior_row) is not dict:
                    continue
                try:
                    prior_record = _row_local_record(
                        "SOURCE_ROW",
                        prior_ordinal,
                        prior_row,
                        region=prior_region,
                        lane_axis=prior_lane_axis,
                        state="SOURCE_OBSERVED_ROW",
                    )
                except (IndexError, TypeError, ValueError):
                    prior_record = None
                if prior_record is not None and _record_has_observed_lane(prior_record):
                    prior_records_by_ordinal[prior_ordinal] = prior_record
        prior_hits = [
            hit
            for hit in (prior_classification or {}).get("role_hits", [])
            if hit["role"] in compiled_specs["root_component_roles"]
            and hit["row_ordinal"] in prior_records_by_ordinal
        ]
        current_hits = [
            hit
            for hit in classification.get("role_hits", [])
            if hit["role"] in compiled_specs["root_component_roles"]
            and hit["row_ordinal"] in row_records
        ]
        prior_observed_ordinals = set(prior_records_by_ordinal)
        current_observed_ordinals = {
            ordinal
            for ordinal, record in row_records.items()
            if _record_has_observed_lane(record)
        }
        component_hits = [*prior_hits, *current_hits]
        component_roles = [hit["role"] for hit in component_hits]
        complete_exact_population = bool(
            exact_fragment_pair
            and receiver_total_ordinal is not None
            and prior_hits
            and current_hits
            and prior_observed_ordinals
            == {hit["row_ordinal"] for hit in prior_hits}
            and current_observed_ordinals
            == {
                receiver_total_ordinal,
                *(hit["row_ordinal"] for hit in current_hits),
            }
            and set(component_roles) == set(compiled_specs["root_component_roles"])
            and len(component_roles) == len(compiled_specs["root_component_roles"])
            and all(component_roles.count(role) == 1 for role in component_roles)
        )
        if complete_exact_population:
            record_by_role = {
                hit["role"]: (
                    prior_records_by_ordinal[hit["row_ordinal"]]
                    if hit in prior_hits
                    else row_records[hit["row_ordinal"]]
                )
                for hit in component_hits
            }
            components = [
                record_by_role[role] for role in compiled_specs["root_component_roles"]
            ]
            root = row_records[receiver_total_ordinal]
            blank_source_cells = [
                {
                    "cell": canonical_clone_v1(cell),
                    "lane_key": canonical_clone_v1(lane_key),
                    "role": role,
                }
                for role, record in zip(
                    [*compiled_specs["root_component_roles"], "FAMILY_ROOT_TOTAL"],
                    [*components, root],
                    strict=True,
                )
                for lane_key, cell in zip(record["lane_keys"], record["cells"], strict=True)
                if cell["source_text"] is None
            ]
            if blank_source_cells:
                adjacent_continuation_family_root_incomplete_receipt = {
                    "blank_source_cells": blank_source_cells,
                    "prior_region": canonical_clone_v1(prior_region),
                    "receiver_region": canonical_clone_v1(region),
                    "rule": (
                        "ADJACENT_CONTINUATION_ROOT_EQUATION_UNAVAILABLE_WHEN_"
                        "ANY_SOURCE_LANE_IS_BLANK"
                    ),
                }
            else:
                root_equation = _exact_equation(
                    kind=(
                        "EXACT_ADJACENT_CONTINUATION_DECLARED_ROOT_COMPONENTS_"
                        "EQUAL_RECEIVER_TERMINAL_TOTAL"
                    ),
                    components=components,
                    result=root,
                )
                if root_equation is not None:
                    equations.append(root_equation)
                    local_records.append(
                        _local_record(
                            "FAMILY_ROOT_TOTAL",
                            root["cells"],
                            root["lane_keys"],
                            root["source_refs"],
                            (
                                "SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_BY_EXACT_"
                                "ADJACENT_CONTINUATION_GROUP"
                            ),
                            root["valuation_basis"],
                        )
                    )
                    source_visible_family_root_ordinals.add(receiver_total_ordinal)
                    consumed_ordinals.update(
                        {
                            receiver_total_ordinal,
                            *(hit["row_ordinal"] for hit in current_hits),
                        }
                    )
                    proven_roles.update(
                        {"FAMILY_ROOT_TOTAL", *compiled_specs["root_component_roles"]}
                    )
                    adjacent_continuation_family_root_receipt = {
                        "component_roles": canonical_clone_v1(
                            compiled_specs["root_component_roles"]
                        ),
                        "source_equation_id": root_equation["equation_id"],
                        "prior_region": canonical_clone_v1(prior_region),
                        "receiver_region": canonical_clone_v1(region),
                        "receiver_total_row_ordinal": receiver_total_ordinal,
                        "rule": (
                            "EXACT_ADJACENT_CONTINUATION_UNION_OF_DECLARED_ROOT_"
                            "COMPONENTS_EQUALS_SOURCE_VISIBLE_RECEIVER_TOTAL"
                        ),
                    }

    adjacent_continuation_frontier_receipt = None
    if (
        lane_axis.get("layout_kind")
        == "ADJACENT_PAGE_EXPLICIT_CONTINUATION_BLANK_HEADER_AXIS"
        and compiled_specs["root_component_equation_policy"]
        == "UNIQUE_DECLARED_SIGN_ORIENTATION_FIRST_COMPONENT_POSITIVE"
        and type(prior_fragment) is dict
        and len(family_root_ordinals) == 1
    ):
        prior_table = prior_fragment.get("table")
        prior_region = prior_fragment.get("region")
        prior_lane_axis = prior_fragment.get("lane_axis")
        prior_unit_axis = prior_fragment.get("unit_axis")
        prior_classification = prior_fragment.get("classification")
        prior_rows = prior_table.get("rows") if type(prior_table) is dict else None
        current_root_ordinal = next(iter(family_root_ordinals))
        current_component_axis = [
            (ordinal, role, row_records[ordinal])
            for ordinal, role in sorted(hit_by_row.items())
            if ordinal in row_records and ordinal not in family_root_ordinals
        ]
        exact_fragment_pair = bool(
            type(prior_region) is dict
            and type(prior_lane_axis) is dict
            and type(prior_unit_axis) is dict
            and type(prior_classification) is dict
            and type(prior_rows) is list
            and prior_table.get("continuation") == "CONTINUES_ON_NEXT_PAGE"
            and table.get("continuation") == "CONTINUES_FROM_PREVIOUS_PAGE"
            and prior_region.get("document_id") == region["document_id"]
            and prior_region.get("source_sha256") == region["source_sha256"]
            and prior_region.get("selected_page_ordinal")
            == region["selected_page_ordinal"] - 1
            and prior_region.get("physical_page") == region["physical_page"] - 1
            and prior_lane_axis.get("complete") is True
            and prior_lane_axis.get("lane_keys") == lane_axis["lane_keys"]
            and prior_unit_axis.get("complete") is True
            and prior_unit_axis.get("canonical_unit") == unit_axis["canonical_unit"]
            and current_root_ordinal in row_records
            and current_root_ordinal == max(row_records)
            and set(row_records)
            == {current_root_ordinal, *(ordinal for ordinal, _role, _record in current_component_axis)}
            and current_component_axis
        )
        carrier_candidates = []
        if exact_fragment_pair:
            for hit in prior_classification.get("role_hits", []):
                carrier_role = hit["role"]
                if carrier_role not in compiled_specs["root_component_roles"] or not all(
                    any(
                        matcher["within_role"] == carrier_role
                        for matcher in compiled_specs["matchers_by_role"].get(role, [])
                    )
                    for _ordinal, role, _record in current_component_axis
                ):
                    continue
                prior_ordinal = hit["row_ordinal"]
                try:
                    carrier = _row_local_record(
                        "SOURCE_ROW",
                        prior_ordinal,
                        prior_rows[prior_ordinal - 1],
                        region=prior_region,
                        lane_axis=prior_lane_axis,
                        state="SOURCE_OBSERVED_ROW",
                    )
                except (IndexError, TypeError, ValueError):
                    carrier = None
                if carrier is not None and all(
                    cell["source_text"] is not None for cell in carrier["cells"]
                ):
                    carrier_candidates.append((prior_ordinal, carrier_role, carrier))
        if len(carrier_candidates) == 1:
            prior_ordinal, carrier_role, carrier = carrier_candidates[0]
            continuation_equation = configured_complete_source_equation(
                kind=(
                    "EXACT_ADJACENT_CONTINUATION_DIRECT_CHILDREN_EQUAL_"
                    "PRIOR_FRAGMENT_CARRIER"
                ),
                components=[record for _ordinal, _role, record in current_component_axis],
                result=carrier,
            )
            root = row_records[current_root_ordinal]
            if continuation_equation is not None and all(
                cell["source_text"] is not None for cell in root["cells"]
            ):
                equations.append(continuation_equation)
                consumed_ordinals.update(
                    {current_root_ordinal, *(ordinal for ordinal, _role, _record in current_component_axis)}
                )
                proven_roles.add(carrier_role)
                proven_roles.update(role for _ordinal, role, _record in current_component_axis)
                if not source_visible_family_root_ordinals:
                    local_records.append(
                        _local_record(
                            "FAMILY_ROOT_TOTAL",
                            root["cells"],
                            root["lane_keys"],
                            root["source_refs"],
                            "SOURCE_VISIBLE_FAMILY_ROOT_DEFERRED_TO_DOCUMENT_COMPONENT_CLOSURE",
                            root["valuation_basis"],
                        )
                    )
                    source_visible_family_root_ordinals.add(current_root_ordinal)
                    proven_roles.add("FAMILY_ROOT_TOTAL")
                adjacent_continuation_frontier_receipt = {
                    "carrier_role": carrier_role,
                    "component_roles": [
                        role for _ordinal, role, _record in current_component_axis
                    ],
                    "current_fragment_root_row_ordinal": current_root_ordinal,
                    "prior_fragment_carrier_row_ordinal": prior_ordinal,
                    "rule": (
                        "EXPLICIT_PHYSICALLY_AND_SELECTED_ADJACENT_CONTINUATION_"
                        "DIRECT_CHILDREN_PROVE_PRIOR_CARRIER_BEFORE_DOCUMENT_ROOT_CLOSURE"
                    ),
                    "source_equation_id": continuation_equation["equation_id"],
                }

    if adjacent_continuation_frontier_receipt is not None:
        receipt["adjacent_continuation_frontier_receipt"] = (
            adjacent_continuation_frontier_receipt
        )
    if adjacent_continuation_family_root_receipt is not None:
        receipt["adjacent_continuation_family_root_receipt"] = (
            adjacent_continuation_family_root_receipt
        )
    if adjacent_continuation_family_root_incomplete_receipt is not None:
        receipt["adjacent_continuation_family_root_incomplete_receipt"] = (
            adjacent_continuation_family_root_incomplete_receipt
        )
    if cross_fragment_same_role_parent_equation_receipts:
        receipt["cross_fragment_same_role_parent_equation_receipts"] = (
            cross_fragment_same_role_parent_equation_receipts
        )

    if (
        compiled_specs["schema"]["root_mapping_policy"] != "STRUCTURAL_CONTEXT_ONLY"
        and not source_visible_family_root_ordinals
        and len(deferred_hierarchy_family_roots) == 1
    ):
        root_ordinal, root = deferred_hierarchy_family_roots[0]
        local_records.append(
            _local_record(
                "FAMILY_ROOT_TOTAL",
                root["cells"],
                root["lane_keys"],
                root["source_refs"],
                "SOURCE_VISIBLE_FAMILY_ROOT_PROVEN_BY_DIRECT_CHILD_FRONTIER",
                root["valuation_basis"],
            )
        )
        source_visible_family_root_ordinals.add(root_ordinal)
        proven_roles.add("FAMILY_ROOT_TOTAL")

    if (
        document_source_result_carrier
        and not source_visible_family_root_ordinals
        and set(row_records) == family_root_ordinals
        and len(family_root_ordinals) == 1
    ):
        # Some primary income statements print only the family result while
        # the independently totalled component populations live in the note.
        # Preserve that result without granting local proof: the document graph
        # must still find every configured root and one unique signed equation.
        # A primary table that also exposes components cannot use this path to
        # bypass a local mismatch.
        root_ordinal = next(iter(family_root_ordinals))
        root = row_records[root_ordinal]
        local_records.append(
            _local_record(
                "FAMILY_ROOT_TOTAL",
                root["cells"],
                root["lane_keys"],
                root["source_refs"],
                "SOURCE_VISIBLE_FAMILY_ROOT_DEFERRED_TO_DOCUMENT_COMPONENT_CLOSURE",
                root["valuation_basis"],
            )
        )
        source_visible_family_root_ordinals.add(root_ordinal)
        proven_roles.add("FAMILY_ROOT_TOTAL")

    if (
        not source_visible_family_root_ordinals
        and len(row_records) == 1
        and set(row_records) == family_root_ordinals
        and len(rows) == 1
    ):
        # A bounded note may disclose the family as one exact source-visible
        # result row and no component rows.  The row itself is authoritative;
        # requiring a fabricated self-equation would add no evidence.  This
        # path is deliberately narrower than statement-row discovery: the
        # query has already authenticated one exact owner/reset fence and the
        # exhaustive table inventory contains no second row to ignore.
        root_ordinal, root = next(iter(row_records.items()))
        local_records.append(
            _local_record(
                "FAMILY_ROOT_TOTAL",
                root["cells"],
                root["lane_keys"],
                root["source_refs"],
                "SOURCE_VISIBLE_EXACT_FAMILY_ROOT_ONLY_ROW",
                root["valuation_basis"],
            )
        )
        source_visible_family_root_ordinals.add(root_ordinal)
        consumed_ordinals.add(root_ordinal)
        proven_roles.add("FAMILY_ROOT_TOTAL")

    exact_component_ordinals = {
        source_ref["row_ordinal"]
        for equation in equations
        if _is_complete_source_control_equation(equation)
        for source_refs in equation["component_source_refs"]
        for source_ref in source_refs
    }
    exact_result_ordinals = {
        source_ref["row_ordinal"]
        for equation in equations
        if _is_complete_source_control_equation(equation)
        for source_ref in equation["result_source_refs"]
    }
    applied_ordered_scope_by_id = {
        item["scope_id"]: item
        for item in classification.get("ordered_role_scope_receipts", [])
        if item["status"] == "UNIQUE_ORDERED_ROLE_SCOPE_APPLIED"
    }

    def has_more_specific_ordered_projection(source_role: str, row_ordinal: int) -> bool:
        """Return whether an ordered projection supersedes a leaf fallback.

        A generic source role may be a catch-all leaf in a flat presentation,
        yet acquire a narrower accounting meaning inside one authenticated
        ordered stage.  The ordered stage is structural evidence selected by
        declared role boundaries, so it takes precedence over the otherwise
        valid leaf-to-residual fallback.  No value participates in choosing
        between the two projections.
        """

        return any(
            projection["source_role"] == source_role
            and (scope := applied_ordered_scope_by_id.get(projection["scope_id"])) is not None
            and scope["start_row_ordinal"] < row_ordinal <= scope["terminal_row_ordinal"]
            for projection in compiled_specs["ordered_role_scope_projections"]
        )

    validation_role_leaf_projection_receipts = []
    for projection in compiled_specs.get("validation_role_leaf_projections", []):
        source_role = projection["source_role"]
        target_role = projection["target_role"]
        projected_source_refs = []
        for ordinal in sorted(
            ordinal for ordinal, role in hit_by_row.items() if role == source_role
        ):
            # The same source label can be a leaf in one presentation and an
            # accounting parent in another.  Only a leaf that participates in
            # an exact printed source-total equation may flow to the declared
            # catch-all.  A carrier with any visible descendant, or one that
            # is itself an equation result, remains validation-only so parent
            # and children can never be double-counted.
            if (
                ordinal not in row_records
                or ordinal not in exact_component_ordinals
                or ordinal in exact_result_ordinals
                or has_more_specific_ordered_projection(source_role, ordinal)
                or any(
                    other_ordinal != ordinal
                    and _row_is_strict_descendant(rows, other_ordinal, ordinal)
                    and any(
                        cell["source_text"] is not None
                        for cell in row_records[other_ordinal]["cells"]
                    )
                    for other_ordinal in row_records
                )
            ):
                continue
            record = row_records[ordinal]
            local_records.append(
                _local_record(
                    target_role,
                    record["cells"],
                    record["lane_keys"],
                    record["source_refs"],
                    (
                        "SOURCE_VALIDATION_ROLE_LEAF_PROJECTED_TO_DECLARED_RESIDUAL_"
                        "AFTER_EXACT_SOURCE_TOTAL"
                    ),
                    record["valuation_basis"],
                )
            )
            proven_roles.add(target_role)
            projected_source_refs.append(canonical_clone_v1(record["source_refs"][0]))
        if projected_source_refs:
            validation_role_leaf_projection_receipts.append(
                {
                    "projected_source_refs": projected_source_refs,
                    "source_role": source_role,
                    "target_role": target_role,
                    "rule": (
                        "VALIDATION_ONLY_STRUCTURAL_ROLE_PROJECTS_TO_DECLARED_RESIDUAL_"
                        "IFF_LEAF_EXACT_SOURCE_TOTAL_COMPONENT_NOT_EQUATION_RESULT"
                    ),
                }
            )

    derived_structural_parent_receipts = []
    equation_consumed_residual_projection_receipts = []
    residual_role = compiled_specs["equation_consumed_unmatched_residual_role"]
    direct_residual_anchor_visible = bool(
        residual_role is not None
        and any(hit["role"] == residual_role for hit in classification["role_hits"])
    )
    anchorless_residual_projection = bool(
        residual_role is not None
        and compiled_specs.get(
            "equation_consumed_unmatched_residual_anchor_policy",
            "DIRECT_RESIDUAL_ROLE_REQUIRED",
        )
        == "EXACT_SOURCE_EQUATION_FRONTIER_SUFFICIENT"
    )
    if residual_role is not None and (
        direct_residual_anchor_visible or anchorless_residual_projection
    ):
        source_total_component_ordinals = {
            source_ref["row_ordinal"]
            for equation in equations
            if _is_complete_source_control_equation(equation)
            and any(
                source_ref.get("row_kind") in {"SUBTOTAL", "TOTAL"}
                or source_ref["row_ordinal"] in family_root_ordinals
                for source_ref in equation["result_source_refs"]
            )
            for source_refs in equation["component_source_refs"]
            for source_ref in source_refs
        }
        component_ordinals = (
            exact_component_ordinals
            if direct_residual_anchor_visible
            else source_total_component_ordinals
        )
        result_ordinals = {
            source_ref["row_ordinal"]
            for equation in equations
            if _is_complete_source_control_equation(equation)
            for source_ref in equation["result_source_refs"]
        }
        sole_child_corroboration_ordinals = {
            equation["component_source_refs"][0][0]["row_ordinal"]
            for equation in equations
            if _is_complete_source_control_equation(equation)
            and len(equation["component_source_refs"]) == 1
            and len(equation["component_source_refs"][0]) == 1
            and any(
                source_ref["row_ordinal"] in hit_by_row
                for source_ref in equation["result_source_refs"]
            )
        }
        projected_source_refs = []
        for ordinal, record in sorted(row_records.items()):
            if (
                ordinal in hit_by_row
                or ordinal not in component_ordinals
                or ordinal in result_ordinals
                or ordinal in sole_child_corroboration_ordinals
                or rows[ordinal - 1].get("row_kind") != "ITEM"
            ):
                continue
            local_records.append(
                _local_record(
                    residual_role,
                    record["cells"],
                    record["lane_keys"],
                    record["source_refs"],
                    "SOURCE_EQUATION_CONSUMED_UNMATCHED_ROW_PROJECTED_TO_RESIDUAL",
                    record["valuation_basis"],
                )
            )
            hit_by_row[ordinal] = residual_role
            proven_roles.add(residual_role)
            projected_source_refs.append(canonical_clone_v1(record["source_refs"][0]))
        if projected_source_refs:
            equation_consumed_residual_projection_receipts.append(
                {
                    "projected_source_refs": projected_source_refs,
                    "residual_role": residual_role,
                    "rule": (
                        "UNMATCHED_ITEM_ROWS_USED_AS_EXACT_EQUATION_COMPONENTS_PROJECT_"
                        "TO_DECLARED_RESIDUAL_EXCLUDING_RESULTS_AND_SOLE_CHILD_CORROBORATIONS"
                    ),
                }
            )
    context_residual_projection_receipts = []
    unresolved_context_residual_rows = []
    if compiled_specs.get("context_residual_bindings"):
        exact_component_ordinals = {
            source_ref["row_ordinal"]
            for equation in equations
            if _is_complete_source_control_equation(equation)
            for source_refs in equation["component_source_refs"]
            for source_ref in source_refs
        }
        exact_result_ordinals = {
            source_ref["row_ordinal"]
            for equation in equations
            if _is_complete_source_control_equation(equation)
            for source_ref in equation["result_source_refs"]
        }
        for binding in compiled_specs["context_residual_bindings"]:
            context_role = binding["context_role"]
            residual_role = binding["residual_role"]
            carrier_ordinals = [
                ordinal for ordinal, role in hit_by_row.items() if role == context_role
            ]
            if len(carrier_ordinals) != 1:
                continue
            carrier_ordinal = carrier_ordinals[0]
            projected_source_refs = []
            for ordinal, record in sorted(row_records.items()):
                if (
                    ordinal in hit_by_row
                    or rows[ordinal - 1].get("row_kind") != "ITEM"
                    or not _row_is_strict_descendant(rows, ordinal, carrier_ordinal)
                    or any(
                        other_ordinal not in {ordinal, carrier_ordinal}
                        and _normalized(rows[other_ordinal - 1].get("label_exact"))
                        and _row_is_strict_descendant(rows, other_ordinal, carrier_ordinal)
                        and _row_is_strict_descendant(rows, ordinal, other_ordinal)
                        for other_ordinal in row_records
                    )
                ):
                    continue
                if ordinal not in exact_component_ordinals or ordinal in exact_result_ordinals:
                    unresolved_context_residual_rows.append(
                        {
                            "context_carrier_row_ordinal": carrier_ordinal,
                            "context_role": context_role,
                            "residual_role": residual_role,
                            "source_ref": canonical_clone_v1(record["source_refs"][0]),
                        }
                    )
                    continue
                local_records.append(
                    _local_record(
                        residual_role,
                        record["cells"],
                        record["lane_keys"],
                        record["source_refs"],
                        "SOURCE_CONTEXT_DIRECT_CHILD_PROJECTED_TO_DECLARED_RESIDUAL_AFTER_"
                        "EXACT_CONTEXT_TOTAL_CLOSURE",
                        record["valuation_basis"],
                    )
                )
                hit_by_row[ordinal] = residual_role
                proven_roles.add(residual_role)
                projected_source_refs.append(canonical_clone_v1(record["source_refs"][0]))
            if projected_source_refs:
                context_residual_projection_receipts.append(
                    {
                        "context_carrier_row_ordinal": carrier_ordinal,
                        "context_role": context_role,
                        "projected_source_refs": projected_source_refs,
                        "residual_role": residual_role,
                        "rule": (
                            "UNMATCHED_DIRECT_CHILDREN_OF_ONE_DECLARED_STRUCTURAL_CONTEXT_"
                            "PROJECT_TO_ITS_DECLARED_RESIDUAL_ONLY_AFTER_EXACT_CONTEXT_TOTAL_"
                            "CLOSURE"
                        ),
                    }
                )
    if compiled_specs["table_context_roles"] and (
        compiled_specs["structural_parent_derivation_policy"] == "DECLARED_CONTEXT_CHILD_FRONTIER"
        or compiled_specs["money_metric_policy"]
        == "CARRYING_VALUE_PREFERRED_WITH_EXACT_PERIOD_AND_INSTRUMENT_AXES"
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
                _sum_record_cells(
                    components,
                    exact_state="EXACT_COMPLETE_VISIBLE_SCOPED_CHILD_FRONTIER_SUM",
                ),
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

    if not source_visible_family_root_ordinals and derived_structural_parent_receipts:
        # The source may omit one structural subtotal while still printing a
        # terminal family total.  Derive the subtotal only from its complete
        # declared child frontier above, then accept the printed root only
        # when those derived/visible top-level roles reproduce it and the raw
        # table already supplies exactly one exact source equation for that
        # same result row.  The equation frontier, not values, selects scope.
        root_components = [
            record
            for record in local_records
            if record["role"] in compiled_specs["root_component_roles"]
        ]
        root_matches = []
        if root_components and _same_lane_axis(root_components):
            for total_ordinal in sorted(total_ordinals):
                if any(ordinal > total_ordinal for ordinal in row_records):
                    continue
                if any(
                    source_ref.get("row_ordinal") not in consumed_ordinals
                    or source_ref.get("row_ordinal", total_ordinal) >= total_ordinal
                    for component in root_components
                    for source_ref in component["source_refs"]
                ):
                    continue
                source_root_equations = [
                    equation
                    for equation in equations
                    if _is_complete_source_control_equation(equation)
                    and {
                        source_ref.get("row_ordinal")
                        for source_ref in equation["result_source_refs"]
                    }
                    == {total_ordinal}
                ]
                if len(source_root_equations) != 1:
                    continue
                derived_equation = configured_complete_source_equation(
                    kind=(
                        "EXACT_DERIVED_STRUCTURAL_PARENT_AND_VISIBLE_ROOT_"
                        "COMPONENTS_EQUAL_PRINTED_TOTAL"
                    ),
                    components=root_components,
                    result=row_records[total_ordinal],
                )
                if derived_equation is not None:
                    root_matches.append(total_ordinal)
        if len(root_matches) == 1:
            total_ordinal = root_matches[0]
            total = row_records[total_ordinal]
            local_records.append(
                _local_record(
                    "FAMILY_ROOT_TOTAL",
                    total["cells"],
                    total["lane_keys"],
                    total["source_refs"],
                    (
                        "SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_AFTER_"
                        "DERIVED_STRUCTURAL_PARENT_CLOSURE"
                    ),
                    total["valuation_basis"],
                )
            )
            source_visible_family_root_ordinals.add(total_ordinal)
            consumed_ordinals.add(total_ordinal)
            proven_roles.add("FAMILY_ROOT_TOTAL")
            proven_roles.update(component["role"] for component in root_components)

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

    ordered_role_scope_projection_receipts = []
    applied_scope_by_id = {
        item["scope_id"]: item
        for item in classification.get("ordered_role_scope_receipts", [])
        if item["status"] == "UNIQUE_ORDERED_ROLE_SCOPE_APPLIED"
    }
    for projection in compiled_specs["ordered_role_scope_projections"]:
        scope = applied_scope_by_id.get(projection["scope_id"])
        if scope is None:
            continue
        projected_records = []
        retained_records = []
        for record in local_records:
            row_ordinals = {source_ref.get("row_ordinal") for source_ref in record["source_refs"]}
            if (
                record["role"] != projection["source_role"]
                or None in row_ordinals
                or not row_ordinals
                or not all(
                    scope["start_row_ordinal"] < row_ordinal <= scope["terminal_row_ordinal"]
                    for row_ordinal in row_ordinals
                )
                or not row_ordinals <= consumed_ordinals
            ):
                retained_records.append(record)
                continue
            projected = canonical_clone_v1(record)
            projected["role"] = projection["target_role"]
            projected["state"] = (
                "SOURCE_VALIDATION_ROLE_PROJECTED_TO_MAPPED_ROLE_AFTER_ORDERED_STAGE_"
                "EXACT_EQUATION_CLOSURE"
            )
            projected_records.append(projected)
            proven_roles.add(projection["target_role"])
        local_records = [*retained_records, *projected_records]
        if projected_records:
            ordered_role_scope_projection_receipts.append(
                {
                    "projected_source_refs": [
                        source_ref
                        for record in projected_records
                        for source_ref in canonical_clone_v1(record["source_refs"])
                    ],
                    "rule": (
                        "VALIDATION_ROLE_PROJECTS_TO_DECLARED_MAPPED_AGGREGATE_ONLY_"
                        "INSIDE_ONE_ORDERED_STAGE_AFTER_EXACT_EQUATION_CONSUMPTION"
                    ),
                    **canonical_clone_v1(projection),
                }
            )

    ratio_records, ratio_equations, ratio_receipts, ratio_reasons = (
        _derive_table_ratio_metric_records(
            rows=rows,
            row_records=row_records,
            hit_by_row=hit_by_row,
            lane_axis=lane_axis,
            region=region,
            table=table,
            document_duration_context=document_period_context,
            compiled_specs=compiled_specs,
        )
    )
    local_records.extend(ratio_records)
    equations.extend(ratio_equations)
    proven_roles.update(record["role"] for record in ratio_records)
    if ratio_receipts:
        receipt["ratio_metric_receipts"] = ratio_receipts
    receipt["ratio_metric_reasons"] = ratio_reasons

    source_only_rows = []
    validation_only_roles = set(compiled_specs["validation_only_roles"])
    for ordinal, record in sorted(row_records.items()):
        if not (
            (
                ordinal not in hit_by_row
                or hit_by_row[ordinal] not in compiled_specs["bindings"]
                or ordinal in shadowed_role_ordinals
                or ordinal in cross_fragment_same_role_detail_ordinals
            )
            and ordinal not in total_ordinals
        ):
            continue
        source_only = {
            "consumed_by_exact_equation": ordinal in consumed_ordinals,
            "declared_role": hit_by_row.get(ordinal),
            "row_ordinal": ordinal,
            "source_ref": canonical_clone_v1(record["source_refs"][0]),
        }
        declared_role = hit_by_row.get(ordinal)
        if declared_role in validation_only_roles:
            # Preserve the role resolved by the complete table classifier.
            # Re-running a row-local matcher later loses ordered/hierarchy
            # context and can make one generic child label appear to belong
            # to two structural branches.
            source_only["declared_validation_role"] = declared_role
        source_only_rows.append(source_only)
    standalone_exact_source_result = bool(
        optional_component_veto_source_result and len(family_root_ordinals) == 1 and not hit_by_row
    )
    unmapped_direct_family_rows = []
    authenticated_primary_family_group_ordinals = {
        item["family_group_row_ordinal"]
        for item in classification.get("primary_statement_family_root_subtree_receipts", [])
    }
    if (
        compiled_specs["unmapped_direct_family_row_policy"]
        == "UNRESOLVED_WHEN_ACTIVE_FAMILY_POPULATION_HAS_ANY_UNMAPPED_MONEY_ROW"
        and scope_to_explicit_family_root
    ):
        for ordinal, record in sorted(row_records.items()):
            if ordinal in hit_by_row or ordinal in family_root_ordinals:
                continue
            row = rows[ordinal - 1]
            if _normalized(row.get("label_exact")) and any(
                cell["source_text"] is not None for cell in record["cells"]
            ):
                unmapped_direct_family_rows.append(canonical_clone_v1(record["source_refs"][0]))
    elif (
        (
            compiled_specs["unmapped_direct_family_row_policy"]
            == "UNRESOLVED_WHEN_EXPLICIT_FAMILY_ROOT_HAS_UNMAPPED_DIRECT_MONEY_CHILD"
            and family_root_ordinals
        )
        or (
            compiled_specs["unmapped_direct_family_row_policy"]
            == "UNRESOLVED_WHEN_ACTIVE_FAMILY_POPULATION_HAS_UNMAPPED_DIRECT_MONEY_ROW"
            and scope_to_explicit_family_root
        )
    ) and not standalone_exact_source_result:
        for ordinal, record in sorted(row_records.items()):
            if ordinal in hit_by_row or ordinal in family_root_ordinals:
                continue
            row = rows[ordinal - 1]
            if (
                row.get("row_kind") != "ITEM"
                or not _normalized(row.get("label_exact"))
                or not any(cell["source_text"] is not None for cell in record["cells"])
            ):
                continue
            owning_roots = [
                root_ordinal
                for root_ordinal in family_root_ordinals
                if ordinal in flat_family_row_ordinals
                or _row_is_strict_descendant(rows, ordinal, root_ordinal)
            ]
            if not owning_roots:
                continue
            is_direct = any(
                ordinal in flat_family_row_ordinals
                or not any(
                    other_ordinal not in {ordinal, root_ordinal}
                    and other_ordinal not in authenticated_primary_family_group_ordinals
                    and _normalized(rows[other_ordinal - 1].get("label_exact"))
                    and _row_is_strict_descendant(rows, other_ordinal, root_ordinal)
                    and _row_is_strict_descendant(rows, ordinal, other_ordinal)
                    for other_ordinal in row_records
                )
                for root_ordinal in owning_roots
            )
            if is_direct:
                unmapped_direct_family_rows.append(canonical_clone_v1(record["source_refs"][0]))
    elif (
        compiled_specs["unmapped_direct_family_row_policy"]
        in {
            "UNRESOLVED_WHEN_ACTIVE_FAMILY_POPULATION_HAS_ANY_UNMAPPED_MONEY_ROW",
            "UNRESOLVED_WHEN_ACTIVE_FAMILY_POPULATION_HAS_UNMAPPED_DIRECT_MONEY_ROW",
            "UNRESOLVED_WHEN_OWNER_FENCED_WHOLE_TABLE_HAS_UNMAPPED_DIRECT_MONEY_ROW",
        }
        and not scope_to_explicit_family_root
    ):
        for ordinal, record in sorted(row_records.items()):
            if ordinal in hit_by_row or ordinal in family_root_ordinals:
                continue
            row = rows[ordinal - 1]
            if (
                (
                    compiled_specs["unmapped_direct_family_row_policy"]
                    == "UNRESOLVED_WHEN_ACTIVE_FAMILY_POPULATION_HAS_ANY_UNMAPPED_MONEY_ROW"
                    or row.get("row_kind") == "ITEM"
                )
                and _normalized(row.get("label_exact"))
                and any(cell["source_text"] is not None for cell in record["cells"])
            ):
                unmapped_direct_family_rows.append(canonical_clone_v1(record["source_refs"][0]))
    unproven_conditional_zero_rows = sorted(
        {
            source_ref["row_ordinal"]
            for record in local_records
            if not (
                record["role"] in validation_only_roles
                and compiled_specs["child_by_role"][record["role"]]["role_kind"]
                == "NONADDITIVE_CHILD"
            )
            if any(cell["state"].endswith("_IF_EQUATION_EXACT") for cell in record["cells"])
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
            and _supplemental_residual_population_receipt(
                occurrences, role=role, compiled_specs=compiled_specs
            )
            is None
        )
    local_records, aggregation_receipts = _aggregate_duplicate_roles(
        local_records,
        compiled_specs=compiled_specs,
        consumed_ordinals=consumed_ordinals,
    )
    if document_source_result_carrier:
        # The primary statement authenticates the requested result and its
        # exact local equation.  Detailed note populations remain the sole
        # source of schema component mappings, preventing a repeated summary,
        # segment table, or related-party carrier from replacing detail rows.
        local_records = [
            record for record in local_records if record["role"] == "FAMILY_ROOT_TOTAL"
        ]
        receipt["document_source_result_carrier_receipt"] = {
            "family_root_row_ordinals": sorted(family_root_ordinals),
            "root_component_row_ordinals": sorted(
                source_result_population_ordinals - family_root_ordinals
            ),
            "rule": (
                "PRIMARY_STATEMENT_EXACT_ROOT_COMPONENT_EQUATION_SUPPLIES_RESULT_ONLY_"
                "DETAIL_COMPONENT_MAPPINGS_REMAIN_NOTE_LOCAL"
            ),
        }
    receipt["aggregation_receipts"] = aggregation_receipts
    receipt["hierarchical_duplicate_receipts"] = hierarchical_duplicate_receipts
    if signed_context_frontier_receipts:
        receipt["signed_context_frontier_receipts"] = signed_context_frontier_receipts
    if supplemental_residual_projection_receipts:
        receipt["supplemental_residual_projection_receipts"] = (
            supplemental_residual_projection_receipts
        )
    if equation_consumed_residual_projection_receipts:
        receipt["equation_consumed_residual_projection_receipts"] = (
            equation_consumed_residual_projection_receipts
        )
    if ordered_role_scope_projection_receipts:
        receipt["ordered_role_scope_projection_receipts"] = ordered_role_scope_projection_receipts
    if context_residual_projection_receipts:
        receipt["context_residual_projection_receipts"] = context_residual_projection_receipts
    if compiled_specs.get("context_residual_bindings"):
        receipt["unresolved_context_residual_rows"] = unresolved_context_residual_rows
    if compiled_specs["label_only_structural_group_policy"] != "DISABLED":
        receipt["label_only_structural_group_receipts"] = label_only_structural_group_receipts
    if derived_structural_parent_receipts:
        receipt["derived_structural_parent_receipts"] = derived_structural_parent_receipts
    if validation_role_leaf_projection_receipts:
        receipt["validation_role_leaf_projection_receipts"] = (
            validation_role_leaf_projection_receipts
        )
    if source_hierarchy_overlap_total_receipts:
        receipt["source_hierarchy_overlap_total_receipts"] = source_hierarchy_overlap_total_receipts
    receipt["source_only_rows"] = source_only_rows
    if source_result_row_receipt is not None:
        receipt["source_result_row_receipt"] = source_result_row_receipt
    if scope_to_explicit_family_root:
        receipt["outside_family_root_rows"] = outside_family_root_rows
    if compiled_specs["unmapped_direct_family_row_policy"] != "IGNORE":
        receipt["unmapped_direct_family_rows"] = unmapped_direct_family_rows
    receipt["unproven_conditional_zero_rows"] = unproven_conditional_zero_rows
    if compiled_specs["duplicate_role_aggregation_policy"] == (
        "ALL_SOURCE_ROWS_CONSUMED_BY_EXACT_TABLE_FRONTIER"
    ):
        receipt["unsealed_duplicate_roles"] = unsealed_duplicate_roles
    unconsumed_source_result_total_rows = (
        sorted(
            item["row_ordinal"]
            for item in classification["total_rows"]
            if not scope_to_explicit_family_root
            or row_inside_explicit_family_root(item["row_ordinal"])
            if item["row_ordinal"] not in consumed_ordinals
        )
        if compiled_specs["source_result_query_policy"] == "OWNER_OR_EXACT_SOURCE_RESULT_ROW"
        else []
    )
    if compiled_specs["source_result_query_policy"] == "OWNER_OR_EXACT_SOURCE_RESULT_ROW":
        receipt["unconsumed_source_result_total_rows"] = unconsumed_source_result_total_rows
    if optional_component_veto_source_result and len(family_root_ordinals) > 1:
        unconsumed_reason = "EXACT_SOURCE_RESULT_ROW_NOT_UNIQUE"
    elif ambiguous_unlabeled_structural_subtotals:
        unconsumed_reason = "UNLABELED_STRUCTURAL_SUBTOTAL_NOT_UNIQUE"
    elif classification["ambiguous_rows"]:
        unconsumed_reason = "AMBIGUOUS_DECLARED_SOURCE_ROW_ROLE"
    elif len(classification["context_roles"]) > 1:
        unconsumed_reason = "AMBIGUOUS_DECLARED_TABLE_CONTEXT_ROLE"
    elif parse_reasons and not standalone_exact_source_result:
        unconsumed_reason = "INVALID_VISIBLE_SOURCE_MONEY_CELL"
    elif ratio_reasons:
        unconsumed_reason = "SOURCE_RATIO_METRIC_NOT_EXACTLY_RESOLVED"
    elif document_source_result_carrier and not source_visible_family_root_ordinals:
        unconsumed_reason = "PRIMARY_SOURCE_RESULT_EQUATION_NOT_EXACT"
    elif unproven_conditional_zero_rows:
        unconsumed_reason = "UNPROVEN_CONDITIONAL_BLANK_ZERO_SOURCE_ROW"
    elif unsealed_duplicate_roles:
        unconsumed_reason = "DUPLICATE_ROLE_SOURCE_ROWS_NOT_ALL_EQUATION_CONSUMED"
    elif unconsumed_source_result_total_rows:
        unconsumed_reason = "SOURCE_RESULT_TOTAL_NOT_PROVEN_BY_EXACT_EQUATION"
    elif unresolved_context_residual_rows:
        unconsumed_reason = "CONTEXT_RESIDUAL_SOURCE_ROW_NOT_PROVEN_BY_EXACT_CONTEXT_TOTAL"
    elif unmapped_direct_family_rows:
        unconsumed_reason = "UNMAPPED_DIRECT_FAMILY_SOURCE_MONEY_ROW"
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
) -> tuple[
    dict[str, dict[str, Any]],
    list[dict[str, Any]],
    list[str],
    list[dict[str, Any]],
]:
    # Validation-only roles are equation inputs, not mapping observations.
    # Independent signed adjustments may legitimately differ on the same
    # lane, so global role reconciliation must not turn them into a false
    # mapping conflict after their local frontiers have already closed.
    mapping_records = [
        record
        for record in local_records
        if record["role"] not in set(compiled_specs["validation_only_roles"])
    ]
    records, partial, reasons, optional_conditional_omissions = _global_records(
        mapping_records, proven_roles=proven_roles, allow_bare_year=True
    )
    if (
        compiled_specs.get("adjacent_continuation_family_root_policy", "DISABLED")
        == "EXACT_UNION_OF_DECLARED_ROOT_COMPONENTS_EQUALS_RECEIVER_TERMINAL_TOTAL"
        and "FAMILY_ROOT_TOTAL" in records
    ):
        # The imported lane reconciler repeats one record-level provenance ref
        # once per observed lane.  This opt-in root is a single source TOTAL,
        # so retain its exact source-row identity once without touching any
        # value, cell state, or legacy-family provenance shape.
        root = records["FAMILY_ROOT_TOTAL"]
        unique_source_refs = {}
        for source_ref in root["source_refs"]:
            unique_source_refs.setdefault(
                canonical_json_sha256_v1(source_ref), canonical_clone_v1(source_ref)
            )
        root["source_refs"] = list(unique_source_refs.values())
    if compiled_specs["period_lane_policy"] == "CURRENT_AND_COMPARATIVE_REQUIRED" or reasons:
        return records, partial, reasons, optional_conditional_omissions

    partial_current_roles = {
        item["role"] for item in partial if item.get("missing_lanes") == ["COMPARATIVE_PERIOD"]
    }
    if not partial_current_roles:
        return records, partial, reasons, optional_conditional_omissions
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
        if cell["state"].endswith("_IF_EQUATION_EXACT"):
            if role not in proven_roles:
                single_reasons.append(f"UNPROVEN_CONDITIONAL_SOURCE_CELL_IN_MAPPING_ROLE:{role}")
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
    return (
        output,
        remaining_partial,
        sorted(set(single_reasons)),
        optional_conditional_omissions,
    )


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
    ratio_duration_policy = bool(compiled_specs.get("ratio_metric_equations", []))
    if ratio_duration_policy:
        document_period_context = _document_duration_month_context_axis(page_json_by_version)
    elif transposed_policy:
        document_period_context = _document_reporting_period_context_axis(page_json_by_version)
    else:
        document_period_context = {}
    local_records = []
    equations = []
    mapping_units = set()
    proven_roles: set[str] = set()
    table_receipts = []
    source_only_axis = []
    reasons = []
    prior_fragment: dict[str, Any] | None = None
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
            prior_fragment=prior_fragment,
        )
        local_records.extend(extracted["local_records"])
        if extracted["local_records"] and extracted["receipt"]["unit_axis"].get(
            "complete"
        ):
            mapping_units.add(extracted["receipt"]["unit_axis"]["canonical_unit"])
        equations.extend(extracted["equations"])
        proven_roles.update(extracted["proven_roles"])
        table_receipts.append(extracted["receipt"])
        classification = extracted["receipt"]["classification"]
        prior_fragment = {
            "classification": canonical_clone_v1(classification),
            "lane_axis": canonical_clone_v1(extracted["receipt"]["lane_axis"]),
            "region": canonical_clone_v1(region),
            "section": canonical_clone_v1(section),
            "table": canonical_clone_v1(table),
            "unit_axis": canonical_clone_v1(extracted["receipt"]["unit_axis"]),
        }
        active_family_population = bool(
            classification["family_presence_anchor_visible"]
            # An exact source label that resolves to multiple declared family
            # roles is family evidence even though no single anchor can be
            # selected.  It must remain fail-closed; only a table with no
            # declared/ambiguous family evidence is an inactive MONEY sibling.
            or classification["ambiguous_rows"]
            or len(classification["context_roles"]) > 1
        )
        owner_complete_population = bool(
            compiled_specs.get("owner_complete_population_policy")
            == "EXACT_OWNER_WHOLE_MONEY_TABLE"
            and classification["owner_visible"]
        )
        # Keep every table receipt in the exhaustive owner-fenced inventory,
        # but an unrelated MONEY table under the same note owner is not an
        # active family population merely because it is physically nearby.
        # Only a declared family anchor (or the explicit whole-table opt-in)
        # may promote its unbound rows into mapping vetoes.  This distinction
        # is structural and value-independent; genuine extra rows in an
        # active table still fail closed below.
        if active_family_population or owner_complete_population:
            source_only_axis.extend(extracted["source_only_rows"])
        if extracted["unconsumed_reason"] is not None and (
            active_family_population or owner_complete_population
        ):
            reasons.append(extracted["unconsumed_reason"])
    if local_records and len(mapping_units) != 1:
        reasons.append("DOCUMENT_MAPPING_UNIT_AXIS_NOT_UNIQUE")
    candidate_unit = next(iter(mapping_units)) if len(mapping_units) == 1 else None
    duplicate_population_policy = compiled_specs["evaluation"].get(
        "duplicate_complete_table_population_policy",
        "ALLOW_CORROBORATING_PRESENTATIONS",
    )
    if duplicate_population_policy in {
        "UNRESOLVED_EXACT_REPEATED_POPULATION",
        "UNRESOLVED_EXACT_REPEATED_ACTIVE_FAMILY_POPULATION",
        "UNRESOLVED_EXACT_REPEATED_OWNER_FENCED_WHOLE_TABLE_POPULATION",
    }:
        complete_population_receipts: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for receipt in table_receipts:
            classification = receipt["classification"]
            lane_axis = receipt["lane_axis"]
            roles = {
                hit["role"]
                for hit in classification["role_hits"]
                if hit["role"] in compiled_specs["root_component_roles"]
            }
            if not lane_axis.get("complete") or len(lane_axis.get("lane_keys", [])) != 2:
                continue
            if duplicate_population_policy == "UNRESOLVED_EXACT_REPEATED_POPULATION":
                complete = bool(classification.get("family_root_row_ordinals") and roles)
            elif duplicate_population_policy == (
                "UNRESOLVED_EXACT_REPEATED_ACTIVE_FAMILY_POPULATION"
            ):
                complete = bool(
                    (
                        classification.get("family_root_row_ordinals")
                        or classification.get("owner_visible")
                    )
                    and classification.get("total_rows")
                    and any(
                        set(combination) <= roles
                        for combination in compiled_specs["topology"]["required_role_combinations"]
                    )
                )
            else:
                complete = bool(
                    classification.get("owner_visible")
                    and classification.get("total_rows")
                    and any(
                        set(combination) <= roles
                        for combination in compiled_specs["topology"]["required_role_combinations"]
                    )
                )
            if not complete:
                continue
            signature = canonical_json_sha256_v1(
                {
                    "lane_keys": lane_axis["lane_keys"],
                    "valuation_basis": lane_axis.get("selected_metric_kinds"),
                }
            )
            complete_population_receipts[signature].append(receipt)
        if any(len(receipts) > 1 for receipts in complete_population_receipts.values()):
            reasons.append("DUPLICATE_COMPLETE_SOURCE_TABLE_POPULATION")
    local_records, context_total_corroboration_receipts = _reconcile_nested_context_totals(
        local_records, compiled_specs=compiled_specs
    )
    local_records, cluster_aggregation_receipts = _aggregate_cluster_duplicate_roles(
        local_records, compiled_specs=compiled_specs
    )
    (
        local_records,
        derived_equations,
        derived_role_receipts,
        derived_role_reasons,
    ) = _derive_declared_role_equations(local_records, compiled_specs=compiled_specs)
    equations.extend(derived_equations)
    proven_roles.update(receipt["result_role"] for receipt in derived_role_receipts)
    reasons.extend(derived_role_reasons)
    (
        local_records,
        root_component_equations,
        root_component_sum_receipts,
        root_component_reasons,
    ) = _derive_complete_top_level_family_root(
        local_records,
        proven_roles=proven_roles,
        source_only_axis=source_only_axis,
        source_equations=equations,
        source_result_component_evidence_roles={
            hit["role"]
            for receipt in table_receipts
            for hit in receipt["classification"]["role_hits"]
        },
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
    (
        records,
        partial_roles,
        global_reasons,
        optional_conditional_omissions,
    ) = _multitable_global_records(
        local_records,
        proven_roles=proven_roles,
        compiled_specs=compiled_specs,
    )
    if compiled_specs["source_reference_identity_policy"] == "EXACT_UNIQUE_SOURCE_IDENTITIES":
        for record in records.values():
            unique_source_refs = {}
            for source_ref in record["source_refs"]:
                unique_source_refs.setdefault(
                    canonical_json_sha256_v1(source_ref), canonical_clone_v1(source_ref)
                )
            record["source_refs"] = list(unique_source_refs.values())
    reasons.extend(global_reasons)
    if (
        compiled_specs["family_root_requirement"] == "REQUIRED_SOURCE_VISIBLE_EXACT_ROOT"
        and "FAMILY_ROOT_TOTAL" not in records
    ):
        reasons.append("REQUIRED_SOURCE_VISIBLE_EXACT_FAMILY_ROOT_NOT_PROVEN")
    observed_declared_roles = set(records).intersection(compiled_specs["child_by_role"])
    if compiled_specs[
        "required_role_combination_mapping_policy"
    ] == "REQUIRE_COMPLETE_COMBINATION_BEFORE_MAPPING" and not any(
        set(combination) <= observed_declared_roles
        for combination in compiled_specs["topology"]["required_role_combinations"]
    ):
        # The owner fence may intentionally retain a partial near-control so
        # its source evidence is audited.  It is never mapping authority until
        # one complete declarative role combination survives extraction; no
        # equation or value may backsolve the missing role.
        reasons.append("REQUIRED_DECLARED_ROLE_COMBINATION_NOT_COMPLETE")
    minimum_root_components = compiled_specs["evaluation"].get(
        "minimum_source_visible_root_component_count"
    )
    if (
        compiled_specs["evaluation"].get(
            "root_only_source_result_policy", "ALLOW_EXACT_SOURCE_RESULT"
        )
        == "REQUIRE_MINIMUM_DECLARED_COMPONENTS"
        and type(minimum_root_components) is int
        and "FAMILY_ROOT_TOTAL" in records
        and len(set(compiled_specs["root_component_roles"]).intersection(records))
        < minimum_root_components
    ):
        reasons.append("MINIMUM_SOURCE_VISIBLE_ROOT_COMPONENTS_NOT_PROVEN")
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
            if (
                record is None
                or role in compiled_specs["validation_only_roles"]
                or (
                    role == "FAMILY_ROOT_TOTAL"
                    and compiled_specs["schema"]["root_mapping_policy"] == "STRUCTURAL_CONTEXT_ONLY"
                )
            ):
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
                "unit": compiled_specs["role_unit_overrides"].get(role, candidate_unit),
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
        **(
            {"optional_conditional_omissions": optional_conditional_omissions}
            if optional_conditional_omissions
            else {}
        ),
        "partial_role_observations": partial_roles,
        "query_receipt": canonical_clone_v1(expected_receipt),
        "rule": (
            "EXHAUSTIVE_OWNER_FENCED_SOURCE_DIRECT_FRONTIER_SUBTOTAL_TOTAL_"
            "SOURCE_ONLY_UNMAPPED_ALL_LANES"
        ),
        "source_only_unmapped_rows": source_only_axis,
        "structural_root_receipt": {
            "emitted_mapping": (
                "FAMILY_ROOT_TOTAL" in records
                and not reasons
                and compiled_specs["schema"]["root_mapping_policy"] != "STRUCTURAL_CONTEXT_ONLY"
            ),
            "mapping_policy": compiled_specs["schema"]["root_mapping_policy"],
            "report_norm_id": compiled_specs["schema"]["family_root_report_norm_id"],
            "role": compiled_specs["topology"]["parent"]["role"],
        },
        "table_receipts": table_receipts,
    }
    cross_fragment_same_role_parent_equation_receipts = [
        canonical_clone_v1(item)
        for receipt in table_receipts
        for item in receipt.get(
            "cross_fragment_same_role_parent_equation_receipts", []
        )
    ]
    if cross_fragment_same_role_parent_equation_receipts:
        closure_receipt["cross_fragment_same_role_parent_equation_receipts"] = (
            cross_fragment_same_role_parent_equation_receipts
        )
    if transposed_policy or ratio_duration_policy:
        closure_receipt["document_period_context"] = document_period_context
    if compiled_specs["validation_only_roles"]:
        closure_receipt["validation_only_roles"] = canonical_clone_v1(
            compiled_specs["validation_only_roles"]
        )
    if compiled_specs["source_reference_identity_policy"] != "PRESERVE_SOURCE_PRESENTATIONS":
        closure_receipt["source_reference_identity_policy"] = compiled_specs[
            "source_reference_identity_policy"
        ]
    if compiled_specs["schema"]["root_mapping_policy"] in {
        "SOURCE_VISIBLE_EXACT_RESULT_WITH_OPTIONAL_COMPLETE_COMPONENT_EQUATION_VETO",
        "SOURCE_VISIBLE_TOTAL_OR_COMPLETE_TOP_LEVEL_COMPONENT_SUM",
    }:
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
