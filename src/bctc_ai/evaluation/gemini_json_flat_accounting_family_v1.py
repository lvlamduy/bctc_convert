"""Declarative flat accounting-family closure over selected Gemini page JSON.

The primitive consumes only Gemini's structured page objects plus declarative
family/evaluation/schema specifications.  It has no PDF geometry, PP-OCR,
VietOCR, bank, filename, page-number, or note-number matching path.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import date
from typing import Any

from bctc_ai.evaluation.accounting_family_topology_v1 import (
    compile_accounting_family_topology_spec_v1,
)
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FORMAT_VERSION = "GEMINI_JSON_FLAT_ACCOUNTING_FAMILY_SWEEP_V1"
HIERARCHICAL_FORMAT_VERSION = "GEMINI_JSON_HIERARCHICAL_ACCOUNTING_FAMILY_SWEEP_V2"
INDEXED_QUERY_EVIDENCE_FORMAT_VERSION = "GEMINI_JSON_INDEXED_TITLE_AXIS_QUERY_EVIDENCE_V1"
ROLLFORWARD_INDEXED_QUERY_EVIDENCE_FORMAT_VERSION = (
    "GEMINI_JSON_INDEXED_ROLLFORWARD_QUERY_EVIDENCE_V1"
)
READY = "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
NOT_OBSERVED = "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
UNRESOLVED = "UNRESOLVED_GEMINI_JSON_FAMILY"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_DECLARATIVE_TWO_THEN_THREE_ANCHOR_"
    "PARENT_TITLE_EXACT_ROLE_POPULATION_ALL_LANE_EXACT_DIRECT_FRONTIER_"
    "ACCOUNTING_CLOSURE_SCHEMA_MAPPING_PROPOSAL_ONLY_NO_GEOMETRY_PPOCR_"
    "VIETOCR_BANK_FILE_PAGE_NOTE_ROUTING_BACKSOLVE_CANONICAL_OR_EXPORT_AUTHORITY"
)
HIERARCHICAL_CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_DECLARATIVE_TWO_THEN_THREE_ANCHOR_"
    "PARENT_TITLE_EXACT_ROLE_POPULATION_ALL_LANE_EXACT_RECURSIVE_DIRECT_"
    "FRONTIER_SOURCE_GROUP_EQUIVALENCE_AGGREGATE_SCHEMA_MAPPING_PROPOSAL_"
    "ONLY_NO_GEOMETRY_PPOCR_VIETOCR_BANK_FILE_PAGE_NOTE_ROUTING_BACKSOLVE_"
    "CANONICAL_OR_EXPORT_AUTHORITY"
)
_DIGITS = re.compile(r"^\d+$")
_GROUPED = re.compile(r"^\d{1,3}(?:[., ]\d{3})+$")
_SECTION_KINDS = {"FINANCIAL_NOTE", "PRIMARY_FINANCIAL_STATEMENT"}


class GeminiJsonFlatAccountingFamilyV1Error(ValueError):
    """The JSON page, declarative spec, or persisted result drifted."""


def _error(message: str) -> GeminiJsonFlatAccountingFamilyV1Error:
    return GeminiJsonFlatAccountingFamilyV1Error(message)


def _compile_specs(
    topology_spec: Any,
    evaluation_spec: Any,
    schema_binding_spec: Any,
) -> dict[str, Any]:
    if (
        type(evaluation_spec) is dict
        and evaluation_spec.get("format_version")
        == "ACCOUNTING_ROLLFORWARD_FAMILY_EVALUATION_SPEC_V1"
    ):
        from bctc_ai.evaluation.gemini_json_rollforward_accounting_family_v1 import (
            compile_gemini_json_rollforward_family_specs_v1,
        )

        return compile_gemini_json_rollforward_family_specs_v1(
            topology_spec, evaluation_spec, schema_binding_spec
        )
    if (
        type(evaluation_spec) is dict
        and evaluation_spec.get("format_version")
        == "ACCOUNTING_STACKED_PERIOD_FAMILY_EVALUATION_SPEC_V1"
    ):
        from bctc_ai.evaluation.gemini_json_stacked_period_accounting_family_v1 import (
            compile_gemini_json_stacked_period_family_specs_v1,
        )

        return compile_gemini_json_stacked_period_family_specs_v1(
            topology_spec, evaluation_spec, schema_binding_spec
        )
    if type(evaluation_spec) is dict and evaluation_spec.get("format_version") in {
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V3",
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V4",
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V5",
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V6",
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V7",
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V8",
    }:
        from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import (
            compile_gemini_json_hierarchical_family_specs_v1,
        )

        return compile_gemini_json_hierarchical_family_specs_v1(
            topology_spec, evaluation_spec, schema_binding_spec
        )
    try:
        topology = compile_accounting_family_topology_spec_v1(topology_spec)
    except ValueError as exc:
        raise _error("Gemini JSON family topology spec is invalid") from exc
    evaluation_format = (
        evaluation_spec.get("format_version") if type(evaluation_spec) is dict else None
    )
    evaluation_keys = {
        "closure_policy",
        "expected_lane_unit_kinds",
        "family_id",
        "format_version",
        "period_semantics",
    }
    if evaluation_format == "ACCOUNTING_FAMILY_EVALUATION_SPEC_V2":
        evaluation_keys.add("source_group_equivalences")
    if (
        type(evaluation_spec) is not dict
        or set(evaluation_spec) != evaluation_keys
        or evaluation_format
        not in {
            "ACCOUNTING_FAMILY_EVALUATION_SPEC_V1",
            "ACCOUNTING_FAMILY_EVALUATION_SPEC_V2",
        }
        or evaluation_spec["family_id"] != topology["family_id"]
        or evaluation_spec["closure_policy"] != "REQUIRE_EXACT_UNIQUE_VISIBLE_TRAILING_TOTAL"
        or type(evaluation_spec["expected_lane_unit_kinds"]) is not list
        or not evaluation_spec["expected_lane_unit_kinds"]
        or any(kind != "MONEY" for kind in evaluation_spec["expected_lane_unit_kinds"])
        or type(evaluation_spec["period_semantics"]) is not str
        or not evaluation_spec["period_semantics"]
    ):
        raise _error("Gemini JSON family evaluation spec is invalid or unsupported")
    children = topology["children"]
    children_by_role = {child["role"]: child for child in children}
    source_group_equivalences: list[dict[str, Any]] = []
    component_group_by_role: dict[str, str] = {}
    if evaluation_format == "ACCOUNTING_FAMILY_EVALUATION_SPEC_V2":
        for equivalence in evaluation_spec["source_group_equivalences"]:
            if (
                type(equivalence) is not dict
                or set(equivalence) != {"component_roles", "group_role"}
                or type(equivalence["group_role"]) is not str
                or equivalence["group_role"] not in children_by_role
                or children_by_role[equivalence["group_role"]]["role_kind"]
                != "SOURCE_ONLY_GROUP_PARENT"
                or type(equivalence["component_roles"]) is not list
                or len(equivalence["component_roles"]) < 2
                or len(set(equivalence["component_roles"])) != len(equivalence["component_roles"])
                or any(
                    role not in children_by_role
                    or children_by_role[role]["role_kind"] != "ADDITIVE_CHILD"
                    or role in component_group_by_role
                    for role in equivalence["component_roles"]
                )
            ):
                raise _error("Gemini JSON family source-group equivalence is invalid")
            for role in equivalence["component_roles"]:
                component_group_by_role[role] = equivalence["group_role"]
            source_group_equivalences.append(canonical_clone_v1(equivalence))
    schema_format = (
        schema_binding_spec.get("format_version") if type(schema_binding_spec) is dict else None
    )
    schema_keys = {
        "family_id",
        "family_report_norm_id",
        "format_version",
        "role_bindings",
    }
    if schema_format == "ACCOUNTING_FAMILY_SCHEMA_BINDING_SPEC_V2":
        schema_keys.add("aggregate_role_bindings")
    if (
        type(schema_binding_spec) is not dict
        or set(schema_binding_spec) != schema_keys
        or schema_format
        not in {
            "ACCOUNTING_FAMILY_SCHEMA_BINDING_SPEC_V1",
            "ACCOUNTING_FAMILY_SCHEMA_BINDING_SPEC_V2",
        }
        or schema_binding_spec["family_id"] != topology["family_id"]
        or type(schema_binding_spec["family_report_norm_id"]) is not int
        or schema_binding_spec["family_report_norm_id"] <= 0
        or type(schema_binding_spec["role_bindings"]) is not list
    ):
        raise _error("Gemini JSON family schema binding spec is invalid")
    bindings: dict[str, int] = {}
    for binding in schema_binding_spec["role_bindings"]:
        if (
            type(binding) is not dict
            or set(binding) != {"report_norm_id", "role"}
            or type(binding["role"]) is not str
            or not binding["role"]
            or binding["role"] in bindings
            or type(binding["report_norm_id"]) is not int
            or binding["report_norm_id"] <= 0
        ):
            raise _error("Gemini JSON family role binding is invalid")
        bindings[binding["role"]] = binding["report_norm_id"]
    child_roles = [child["role"] for child in children]
    aggregate_bindings: list[dict[str, Any]] = []
    aggregate_sources: set[str] = set()
    if schema_format == "ACCOUNTING_FAMILY_SCHEMA_BINDING_SPEC_V2":
        aggregate_roles: set[str] = set()
        report_norm_ids = set(bindings.values()) | {schema_binding_spec["family_report_norm_id"]}
        for aggregate in schema_binding_spec["aggregate_role_bindings"]:
            if (
                type(aggregate) is not dict
                or set(aggregate) != {"operation", "report_norm_id", "role", "source_roles"}
                or aggregate["operation"] != "SUM_OBSERVED_SOURCE_ROLES"
                or type(aggregate["role"]) is not str
                or not aggregate["role"]
                or aggregate["role"] in aggregate_roles
                or aggregate["role"] in child_roles
                or type(aggregate["report_norm_id"]) is not int
                or aggregate["report_norm_id"] <= 0
                or aggregate["report_norm_id"] in report_norm_ids
                or type(aggregate["source_roles"]) is not list
                or not aggregate["source_roles"]
                or len(set(aggregate["source_roles"])) != len(aggregate["source_roles"])
                or any(
                    role not in children_by_role or role in bindings or role in aggregate_sources
                    for role in aggregate["source_roles"]
                )
            ):
                raise _error("Gemini JSON family aggregate role binding is invalid")
            aggregate_roles.add(aggregate["role"])
            report_norm_ids.add(aggregate["report_norm_id"])
            aggregate_sources.update(aggregate["source_roles"])
            aggregate_bindings.append(canonical_clone_v1(aggregate))
    if set(bindings) | aggregate_sources != set(child_roles):
        raise _error("Gemini JSON family schema binding role frontier is incomplete")
    aliases_by_role: dict[str, list[str]] = {}
    for child in children:
        aliases = sorted(
            {
                alias
                for matcher in child["matchers"]
                if matcher["within_role"] is None
                for alias in matcher["aliases"]
            }
        )
        if not aliases:
            raise _error("Gemini JSON flat family child has no root-level aliases")
        aliases_by_role[child["role"]] = aliases
    combinations = []
    for combination in topology["required_role_combinations"]:
        if len(combination) not in {2, 3} or any(
            role not in aliases_by_role for role in combination
        ):
            raise _error("Gemini JSON family anchor combination is invalid")
        combinations.append([aliases_by_role[role] for role in combination])
    if not combinations:
        raise _error("Gemini JSON family needs at least one two-or-three anchor combination")
    return {
        "aggregate_bindings": aggregate_bindings,
        "aliases_by_role": aliases_by_role,
        "anchor_alias_groups": combinations,
        "bindings": bindings,
        "claim_boundary": (
            CLAIM_BOUNDARY
            if evaluation_format == "ACCOUNTING_FAMILY_EVALUATION_SPEC_V1"
            else HIERARCHICAL_CLAIM_BOUNDARY
        ),
        "component_group_by_role": component_group_by_role,
        "engine_format_version": (
            FORMAT_VERSION
            if evaluation_format == "ACCOUNTING_FAMILY_EVALUATION_SPEC_V1"
            else HIERARCHICAL_FORMAT_VERSION
        ),
        "evaluation": canonical_clone_v1(evaluation_spec),
        "schema": canonical_clone_v1(schema_binding_spec),
        "source_group_equivalences": source_group_equivalences,
        "topology": topology,
    }


def compile_gemini_json_flat_family_specs_v1(
    topology_spec: Any,
    evaluation_spec: Any,
    schema_binding_spec: Any,
) -> dict[str, Any]:
    """Compile three existing family specs for JSON-first matching."""

    return _compile_specs(topology_spec, evaluation_spec, schema_binding_spec)


def _money(value: Any) -> dict[str, Any]:
    if value is None:
        return {"coefficient": 0, "source_text": None, "state": "BLANK_ZERO_IF_EQUATION_EXACT"}
    if type(value) is not str or value != value.strip() or not value:
        raise _error("Gemini JSON money cell is not one exact raw string or null")
    if value in {"-", "–", "—", "_"}:
        return {"coefficient": 0, "source_text": value, "state": "DASH_ZERO"}
    negative = value.startswith("(") and value.endswith(")")
    body = value[1:-1] if negative else value
    if body.startswith("-"):
        if negative:
            raise _error("Gemini JSON money sign is contradictory")
        negative = True
        body = body[1:]
    if not (_DIGITS.fullmatch(body) or _GROUPED.fullmatch(body)):
        raise _error("Gemini JSON money grouping is invalid or decimal-ambiguous")
    digits = body.replace(".", "").replace(",", "").replace(" ", "")
    coefficient = int(digits)
    return {
        "coefficient": -coefficient if negative else coefficient,
        "source_text": value,
        "state": "RAW_SIGNED_INTEGER",
    }


def _index(identifier: Any, prefix: str, limit: int, field: str) -> int:
    if type(identifier) is not str or not identifier.startswith(prefix):
        raise _error(f"Gemini JSON family {field} is invalid")
    suffix = identifier[len(prefix) :]
    if not suffix.isdigit() or suffix.startswith("0"):
        raise _error(f"Gemini JSON family {field} is invalid")
    index = int(suffix) - 1
    if not 0 <= index < limit:
        raise _error(f"Gemini JSON family {field} is out of range")
    return index


def _candidate_result(
    *,
    topology: dict[str, Any],
    page_json_version_id: str,
    physical_page: int,
    section_id: str,
    table_id: str,
    reasons: list[str],
) -> dict[str, Any]:
    candidate_material = {
        "family_id": topology["family_id"],
        "page_json_version_id": page_json_version_id,
        "physical_page": physical_page,
        "section_id": section_id,
        "table_id": table_id,
    }
    return {
        **candidate_material,
        "candidate_id": "gjfafcv1:candidate:" + canonical_json_sha256_v1(candidate_material),
        "mappings": [],
        "reasons": sorted(set(reasons)),
        "status": UNRESOLVED if reasons else READY,
    }


def _hierarchy_parent_role(
    *,
    row: dict[str, Any],
    row_ordinal: int,
    aliases_by_role: dict[str, list[str]],
    preliminary_rows_by_role: dict[str, list[int]],
) -> tuple[str | None, bool]:
    """Return the unique declared role named by the row's ancestor path."""

    path = row.get("hierarchy_path_exact")
    if type(path) is not list:
        return None, True
    label = row.get("label_exact")
    label_folded = normalize_vietnamese_anchor_v1(label) if type(label) is str else ""
    matches: list[tuple[int, str]] = []
    for path_value in path:
        if type(path_value) is not str or not path_value:
            continue
        folded = normalize_vietnamese_anchor_v1(path_value)
        if folded == label_folded:
            continue
        for role, aliases in aliases_by_role.items():
            if not any(ordinal != row_ordinal for ordinal in preliminary_rows_by_role[role]):
                continue
            for alias in aliases:
                if folded == alias or folded.startswith(alias + " "):
                    matches.append((len(alias), role))
    if not matches:
        return None, False
    longest = max(length for length, _role in matches)
    roles = {role for length, role in matches if length == longest}
    return (next(iter(roles)), False) if len(roles) == 1 else (None, True)


def _evaluate_hierarchical_table_v2(
    *,
    page_json_version_id: str,
    physical_page: int,
    section_id: str,
    table_id: str,
    table: dict[str, Any],
    compiled_specs: dict[str, Any],
    reasons: list[str],
) -> dict[str, Any]:
    """Evaluate one source-bound recursive direct frontier without geometry."""

    topology = compiled_specs["topology"]
    expected_kinds = compiled_specs["evaluation"]["expected_lane_unit_kinds"]
    columns = table.get("columns")
    rows = table.get("rows")
    assert type(rows) is list and rows
    aliases_by_role = compiled_specs["aliases_by_role"]
    alias_to_roles: dict[str, set[str]] = {}
    for role, aliases in aliases_by_role.items():
        for alias in aliases:
            alias_to_roles.setdefault(alias, set()).add(role)
    preliminary_rows_by_role = {role: [] for role in aliases_by_role}
    label_roles_by_ordinal: dict[int, str] = {}
    totals: list[tuple[int, dict[str, Any]]] = []
    for row_ordinal, row in enumerate(rows, start=1):
        values = row.get("values_exact")
        if type(values) is not list or len(values) != len(expected_kinds):
            reasons.append("ROW_VALUE_VECTOR_DOES_NOT_MATCH_COLUMN_AXIS")
            continue
        if row.get("row_kind") == "TOTAL":
            totals.append((row_ordinal, row))
            continue
        label = row.get("label_exact")
        folded = normalize_vietnamese_anchor_v1(label) if type(label) is str else ""
        matched = alias_to_roles.get(folded, set())
        if len(matched) > 1:
            reasons.append(f"ROW_LABEL_MATCHES_MULTIPLE_ROLES:{row_ordinal}")
        elif len(matched) == 1:
            role = next(iter(matched))
            label_roles_by_ordinal[row_ordinal] = role
            preliminary_rows_by_role[role].append(row_ordinal)

    bound_by_role: dict[str, list[tuple[int, dict[str, Any]]]] = {
        role: [] for role in aliases_by_role
    }
    subordinate_by_parent: dict[str, list[tuple[int, dict[str, Any], str | None]]] = {
        role: [] for role in aliases_by_role
    }
    parent_role_by_ordinal: dict[int, str] = {}
    presentation_rows: list[int] = []
    unbound_rows: list[int] = []
    component_group = compiled_specs["component_group_by_role"]
    for row_ordinal, row in enumerate(rows, start=1):
        values = row.get("values_exact")
        if type(values) is not list or len(values) != len(expected_kinds):
            continue
        if row.get("row_kind") == "TOTAL":
            continue
        role = label_roles_by_ordinal.get(row_ordinal)
        parent_role, parent_ambiguous = _hierarchy_parent_role(
            row=row,
            row_ordinal=row_ordinal,
            aliases_by_role=aliases_by_role,
            preliminary_rows_by_role=preliminary_rows_by_role,
        )
        if parent_ambiguous:
            reasons.append(f"ROW_HIERARCHY_PARENT_IS_AMBIGUOUS:{row_ordinal}")
        if parent_role is not None:
            parent_role_by_ordinal[row_ordinal] = parent_role
            scoped_role = role if component_group.get(role) == parent_role else None
            subordinate_by_parent[parent_role].append((row_ordinal, row, scoped_role))
        if role is not None and (parent_role is None or component_group.get(role) == parent_role):
            bound_by_role[role].append((row_ordinal, row))
        elif parent_role is not None:
            # A typed child under another declared role is source evidence for
            # that parent's local subtotal, never a second root component.
            continue
        elif row.get("row_kind") == "GROUP" and all(value is None for value in values):
            presentation_rows.append(row_ordinal)
        else:
            unbound_rows.append(row_ordinal)

    children_by_role = {child["role"]: child for child in topology["children"]}
    for role, child in children_by_role.items():
        count = len(bound_by_role[role])
        if child["presence"] == "REQUIRED" and count != 1:
            reasons.append(f"REQUIRED_ROLE_USE_COUNT_NOT_ONE:{role}:{count}")
        elif child["presence"] == "OPTIONAL" and count > 1:
            reasons.append(f"OPTIONAL_ROLE_USE_COUNT_ABOVE_ONE:{role}:{count}")
    if unbound_rows:
        reasons.append("UNBOUND_VISIBLE_NUMERIC_OR_SEMANTIC_ROWS")
    if len(totals) != 1:
        reasons.append(f"VISIBLE_TRAILING_TOTAL_COUNT_NOT_ONE:{len(totals)}")

    parsed_by_role: dict[str, dict[str, Any]] = {}
    for role, bindings in bound_by_role.items():
        if len(bindings) != 1:
            continue
        ordinal, row = bindings[0]
        try:
            cells = [_money(value) for value in row["values_exact"]]
        except GeminiJsonFlatAccountingFamilyV1Error:
            reasons.append(f"ROLE_MONEY_CELL_IS_NOT_EXACT_INTEGER:{role}")
            continue
        parsed_by_role[role] = {"cells": cells, "ordinal": ordinal, "row": row}
    parsed_total = None
    if len(totals) == 1:
        try:
            parsed_total = {
                "cells": [_money(value) for value in totals[0][1]["values_exact"]],
                "ordinal": totals[0][0],
                "row": totals[0][1],
            }
        except GeminiJsonFlatAccountingFamilyV1Error:
            reasons.append("VISIBLE_TOTAL_MONEY_CELL_IS_NOT_EXACT_INTEGER")

    nested_equations: list[dict[str, Any]] = []
    for parent_role, child_rows in subordinate_by_parent.items():
        if not child_rows:
            continue
        parent = parsed_by_role.get(parent_role)
        if parent is None:
            reasons.append(f"NESTED_COMPONENT_PARENT_IS_NOT_UNIQUE:{parent_role}")
            continue
        parsed_children = []
        for ordinal, row, role in child_rows:
            try:
                cells = [_money(value) for value in row["values_exact"]]
            except GeminiJsonFlatAccountingFamilyV1Error:
                reasons.append(f"NESTED_COMPONENT_MONEY_CELL_IS_NOT_EXACT_INTEGER:{ordinal}")
                continue
            parsed_children.append(
                {
                    "cells": cells,
                    "label_exact": row.get("label_exact"),
                    "ordinal": ordinal,
                    "role": role,
                }
            )
        if len(parsed_children) != len(child_rows):
            continue
        lane_sums = [
            sum(child["cells"][lane]["coefficient"] for child in parsed_children)
            for lane in range(len(expected_kinds))
        ]
        if lane_sums != [cell["coefficient"] for cell in parent["cells"]]:
            reasons.append(f"NESTED_PARENT_NOT_EXACT_CHILD_SUM:{parent_role}")
        nested_equations.append(
            {
                "component_row_ids": [f"r{child['ordinal']}" for child in parsed_children],
                "component_roles": [child["role"] for child in parsed_children],
                "component_labels_exact": [child["label_exact"] for child in parsed_children],
                "lane_component_sums": lane_sums,
                "result_coefficients": [cell["coefficient"] for cell in parent["cells"]],
                "result_role": parent_role,
                "result_row_id": f"r{parent['ordinal']}",
            }
        )

    for equivalence in compiled_specs["source_group_equivalences"]:
        group_role = equivalence["group_role"]
        component_roles = equivalence["component_roles"]
        group_present = group_role in parsed_by_role
        present_components = [role for role in component_roles if role in parsed_by_role]
        if group_present and present_components:
            if len(present_components) != len(component_roles):
                reasons.append(f"SOURCE_GROUP_COMPONENT_FRONTIER_IS_PARTIAL:{group_role}")
            elif any(
                parent_role_by_ordinal.get(parsed_by_role[role]["ordinal"]) != group_role
                for role in component_roles
            ):
                reasons.append(f"SOURCE_GROUP_COMPONENT_PARENT_DOES_NOT_REPLAY:{group_role}")

    if not any(
        all(role in parsed_by_role for role in combination)
        for combination in topology["required_role_combinations"]
    ):
        reasons.append("NO_REQUIRED_TWO_OR_THREE_ROLE_COMBINATION_IS_COMPLETE")

    root_roles: list[str] = []
    grouped_components = set(compiled_specs["component_group_by_role"])
    grouped_parents = {
        equivalence["group_role"] for equivalence in compiled_specs["source_group_equivalences"]
    }
    for equivalence in compiled_specs["source_group_equivalences"]:
        group_role = equivalence["group_role"]
        if group_role in parsed_by_role:
            root_roles.append(group_role)
        else:
            root_roles.extend(
                role for role in equivalence["component_roles"] if role in parsed_by_role
            )
    for child in topology["children"]:
        role = child["role"]
        if role not in parsed_by_role or role in grouped_components or role in grouped_parents:
            continue
        if child["role_kind"] != "ADDITIVE_CHILD":
            reasons.append(f"UNSUPPORTED_ROOT_ROLE_KIND:{role}")
        else:
            root_roles.append(role)
    if len(root_roles) != len(set(root_roles)):
        reasons.append("ROOT_DIRECT_FRONTIER_REUSES_ONE_ROLE")
    root_roles = sorted(set(root_roles), key=lambda role: parsed_by_role[role]["ordinal"])
    root_sums = [
        sum(parsed_by_role[role]["cells"][lane]["coefficient"] for role in root_roles)
        for lane in range(len(expected_kinds))
    ]
    if parsed_total is not None:
        for lane, component_sum in enumerate(root_sums):
            if component_sum != parsed_total["cells"][lane]["coefficient"]:
                reasons.append(f"VISIBLE_TOTAL_NOT_EXACT_RECURSIVE_COMPONENT_SUM:{lane}")

    result = _candidate_result(
        topology=topology,
        page_json_version_id=page_json_version_id,
        physical_page=physical_page,
        section_id=section_id,
        table_id=table_id,
        reasons=reasons,
    )
    if reasons:
        return result
    assert parsed_total is not None
    mapping_rows: list[dict[str, Any]] = [
        {
            "parsed": parsed_total,
            "report_norm_id": compiled_specs["schema"]["family_report_norm_id"],
            "role": topology["parent"]["role"],
        }
    ]
    for child in topology["children"]:
        role = child["role"]
        if role in parsed_by_role and role in compiled_specs["bindings"]:
            mapping_rows.append(
                {
                    "parsed": parsed_by_role[role],
                    "report_norm_id": compiled_specs["bindings"][role],
                    "role": role,
                }
            )
    for aggregate in compiled_specs["aggregate_bindings"]:
        source_roles = [role for role in aggregate["source_roles"] if role in parsed_by_role]
        if not source_roles:
            continue
        source_roles.sort(key=lambda role: parsed_by_role[role]["ordinal"])
        cells = [
            {
                "coefficient": sum(
                    parsed_by_role[role]["cells"][lane]["coefficient"] for role in source_roles
                ),
                "source_text": None,
                "state": "DERIVED_EXACT_SUM_OF_OBSERVED_SOURCE_ROLES",
            }
            for lane in range(len(expected_kinds))
        ]
        mapping_rows.append(
            {
                "derived_from_row_ids": [
                    f"r{parsed_by_role[role]['ordinal']}" for role in source_roles
                ],
                "derived_from_roles": source_roles,
                "parsed": {
                    "cells": cells,
                    "ordinal": min(parsed_by_role[role]["ordinal"] for role in source_roles),
                    "row": {
                        "hierarchy_path_exact": [
                            parsed_by_role[role]["row"]["label_exact"] for role in source_roles
                        ],
                        "label_exact": " + ".join(
                            parsed_by_role[role]["row"]["label_exact"] for role in source_roles
                        ),
                    },
                },
                "report_norm_id": aggregate["report_norm_id"],
                "role": aggregate["role"],
            }
        )
    result["mappings"] = []
    for mapping in mapping_rows:
        parsed = mapping["parsed"]
        record = {
            "columns": canonical_clone_v1(columns),
            "hierarchy_path_exact": canonical_clone_v1(parsed["row"]["hierarchy_path_exact"]),
            "label_exact": parsed["row"]["label_exact"],
            "report_norm_id": mapping["report_norm_id"],
            "role": mapping["role"],
            "row_id": f"r{parsed['ordinal']}",
            "values": canonical_clone_v1(parsed["cells"]),
        }
        if "derived_from_roles" in mapping:
            record["derived_from_row_ids"] = canonical_clone_v1(mapping["derived_from_row_ids"])
            record["derived_from_roles"] = canonical_clone_v1(mapping["derived_from_roles"])
            record["row_id"] = "aggregate:" + mapping["role"]
        result["mappings"].append(record)
    result["closure_receipt"] = {
        "aggregate_roles": [
            aggregate["role"] for aggregate in compiled_specs["aggregate_bindings"]
        ],
        "component_roles_in_source_order": root_roles,
        "component_row_ids_in_source_order": [
            f"r{parsed_by_role[role]['ordinal']}" for role in root_roles
        ],
        "lane_component_sums": root_sums,
        "nested_equations": nested_equations,
        "presentation_row_ordinals": presentation_rows,
        "result_coefficients": [cell["coefficient"] for cell in parsed_total["cells"]],
        "result_row_id": f"r{parsed_total['ordinal']}",
        "rule": "EXACT_EXHAUSTIVE_VISIBLE_RECURSIVE_DIRECT_FRONTIER_ALL_LANES",
    }
    return result


def evaluate_gemini_json_flat_family_table_v1(
    *,
    page_json: Any,
    page_json_version_id: str,
    physical_page: int,
    section_id: str,
    table_id: str,
    compiled_specs: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate one two/three-anchor table against a flat direct frontier."""

    if (
        compiled_specs.get("engine_format_version")
        == "GEMINI_JSON_HIERARCHICAL_ACCOUNTING_FAMILY_SWEEP_V3"
    ):
        from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import (
            evaluate_gemini_json_hierarchical_family_table_v1,
        )

        return evaluate_gemini_json_hierarchical_family_table_v1(
            page_json=page_json,
            page_json_version_id=page_json_version_id,
            physical_page=physical_page,
            section_id=section_id,
            table_id=table_id,
            compiled_specs=compiled_specs,
        )

    reasons: list[str] = []
    if (
        type(page_json) is not dict
        or page_json.get("status")
        not in {"FINANCIAL_NOTE_CONTENT", "MIXED_FINANCIAL_CONTENT", "PRIMARY_FINANCIAL_STATEMENT"}
        or type(page_json.get("sections")) is not list
    ):
        raise _error("Gemini JSON family candidate page is invalid")
    sections = page_json["sections"]
    section_index = _index(section_id, "s", len(sections), "section ID")
    section = sections[section_index]
    tables = section.get("tables")
    if type(tables) is not list:
        raise _error("Gemini JSON family candidate section has no table axis")
    table_index = _index(table_id, "t", len(tables), "table ID")
    table = tables[table_index]
    topology = compiled_specs["topology"]
    evaluation = compiled_specs["evaluation"]
    if section.get("content_kind") not in _SECTION_KINDS:
        reasons.append("CANDIDATE_SECTION_IS_NOT_FINANCIAL_CONTENT")
    title_exact = " ".join(
        text
        for text in (section.get("title_exact"), table.get("title_exact"))
        if type(text) is str and text
    )
    title_folded = normalize_vietnamese_anchor_v1(title_exact)
    if not any(alias in title_folded for alias in topology["parent"]["aliases"]):
        reasons.append("FAMILY_PARENT_NOT_VISIBLE_IN_SECTION_OR_TABLE_TITLE")
    local_text = " ".join(
        [title_exact]
        + [
            row["label_exact"]
            for row in table.get("rows", [])
            if type(row.get("label_exact")) is str
        ]
    )
    local_folded = normalize_vietnamese_anchor_v1(local_text)
    if any(alias in local_folded for alias in topology["hard_negative_aliases"]):
        reasons.append("HARD_NEGATIVE_FAMILY_VISIBLE_IN_CANDIDATE")
    columns = table.get("columns")
    expected_kinds = evaluation["expected_lane_unit_kinds"]
    if (
        type(columns) is not list
        or len(columns) != len(expected_kinds)
        or [column.get("value_kind") for column in columns] != expected_kinds
        or any(
            type(column.get("header_path_exact")) is not list or not column["header_path_exact"]
            for column in columns
        )
        or len({tuple(column["header_path_exact"]) for column in columns}) != len(columns)
        or type(table.get("unit_exact")) is not str
        or not table["unit_exact"]
    ):
        reasons.append("PERIOD_UNIT_OR_MONEY_COLUMN_AXIS_IS_NOT_EXACT")
    rows = table.get("rows")
    if type(rows) is not list or not rows:
        raise _error("Gemini JSON family candidate table row axis is empty")
    if compiled_specs["engine_format_version"] == HIERARCHICAL_FORMAT_VERSION:
        return _evaluate_hierarchical_table_v2(
            page_json_version_id=page_json_version_id,
            physical_page=physical_page,
            section_id=section_id,
            table_id=table_id,
            table=table,
            compiled_specs=compiled_specs,
            reasons=reasons,
        )
    alias_to_roles: dict[str, set[str]] = {}
    for role, aliases in compiled_specs["aliases_by_role"].items():
        for alias in aliases:
            alias_to_roles.setdefault(alias, set()).add(role)
    bound_by_role: dict[str, list[tuple[int, dict[str, Any]]]] = {
        role: [] for role in compiled_specs["aliases_by_role"]
    }
    totals: list[tuple[int, dict[str, Any]]] = []
    unbound_rows = []
    presentation_rows = []
    for row_ordinal, row in enumerate(rows, start=1):
        values = row.get("values_exact")
        if type(values) is not list or len(values) != len(expected_kinds):
            reasons.append("ROW_VALUE_VECTOR_DOES_NOT_MATCH_COLUMN_AXIS")
            continue
        if row.get("row_kind") == "TOTAL":
            totals.append((row_ordinal, row))
            continue
        label = row.get("label_exact")
        normalized = normalize_vietnamese_anchor_v1(label) if type(label) is str else ""
        matched = alias_to_roles.get(normalized, set())
        if len(matched) == 1:
            bound_by_role[next(iter(matched))].append((row_ordinal, row))
        elif row.get("row_kind") == "GROUP" and all(value is None for value in values):
            presentation_rows.append(row_ordinal)
        else:
            unbound_rows.append(row_ordinal)
    children_by_role = {child["role"]: child for child in topology["children"]}
    for role, child in children_by_role.items():
        count = len(bound_by_role[role])
        if child["presence"] == "REQUIRED" and count != 1:
            reasons.append(f"REQUIRED_ROLE_USE_COUNT_NOT_ONE:{role}:{count}")
        elif child["presence"] == "OPTIONAL" and count > 1:
            reasons.append(f"OPTIONAL_ROLE_USE_COUNT_ABOVE_ONE:{role}:{count}")
    if unbound_rows:
        reasons.append("UNBOUND_VISIBLE_NUMERIC_OR_SEMANTIC_ROWS")
    if len(totals) != 1:
        reasons.append(f"VISIBLE_TRAILING_TOTAL_COUNT_NOT_ONE:{len(totals)}")
    parsed_by_role: dict[str, dict[str, Any]] = {}
    for role, bindings in bound_by_role.items():
        if len(bindings) != 1:
            continue
        ordinal, row = bindings[0]
        try:
            cells = [_money(value) for value in row["values_exact"]]
        except GeminiJsonFlatAccountingFamilyV1Error:
            reasons.append(f"ROLE_MONEY_CELL_IS_NOT_EXACT_INTEGER:{role}")
            continue
        parsed_by_role[role] = {"cells": cells, "ordinal": ordinal, "row": row}
    parsed_total = None
    if len(totals) == 1:
        try:
            parsed_total = {
                "cells": [_money(value) for value in totals[0][1]["values_exact"]],
                "ordinal": totals[0][0],
                "row": totals[0][1],
            }
        except GeminiJsonFlatAccountingFamilyV1Error:
            reasons.append("VISIBLE_TOTAL_MONEY_CELL_IS_NOT_EXACT_INTEGER")
    additive_roles = [
        role
        for role, parsed in parsed_by_role.items()
        if children_by_role[role]["role_kind"] == "ADDITIVE_CHILD" and parsed
    ]
    unsupported_roles = [
        role for role in parsed_by_role if children_by_role[role]["role_kind"] != "ADDITIVE_CHILD"
    ]
    if unsupported_roles:
        reasons.append("FLAT_JSON_FAMILY_HAS_UNSUPPORTED_NONADDITIVE_ROLE")
    if parsed_total is not None and not unsupported_roles:
        for lane in range(len(expected_kinds)):
            component_sum = sum(
                parsed_by_role[role]["cells"][lane]["coefficient"] for role in additive_roles
            )
            if component_sum != parsed_total["cells"][lane]["coefficient"]:
                reasons.append(f"VISIBLE_TOTAL_NOT_EXACT_DIRECT_COMPONENT_SUM:{lane}")
    reasons = sorted(set(reasons))
    result = _candidate_result(
        topology=topology,
        page_json_version_id=page_json_version_id,
        physical_page=physical_page,
        section_id=section_id,
        table_id=table_id,
        reasons=reasons,
    )
    if reasons:
        return result
    assert parsed_total is not None
    mapping_rows = [
        (
            topology["parent"]["role"],
            compiled_specs["schema"]["family_report_norm_id"],
            parsed_total,
        )
    ] + [
        (role, compiled_specs["bindings"][role], parsed_by_role[role])
        for role in [child["role"] for child in topology["children"]]
        if role in parsed_by_role
    ]
    result["mappings"] = [
        {
            "columns": canonical_clone_v1(columns),
            "hierarchy_path_exact": canonical_clone_v1(parsed["row"]["hierarchy_path_exact"]),
            "label_exact": parsed["row"]["label_exact"],
            "report_norm_id": report_norm_id,
            "role": role,
            "row_id": f"r{parsed['ordinal']}",
            "values": canonical_clone_v1(parsed["cells"]),
        }
        for role, report_norm_id, parsed in mapping_rows
    ]
    result["closure_receipt"] = {
        "component_roles_in_source_order": [
            role
            for role, parsed in sorted(parsed_by_role.items(), key=lambda item: item[1]["ordinal"])
        ],
        "lane_component_sums": [
            sum(parsed_by_role[role]["cells"][lane]["coefficient"] for role in additive_roles)
            for lane in range(len(expected_kinds))
        ],
        "presentation_row_ordinals": presentation_rows,
        "result_coefficients": [cell["coefficient"] for cell in parsed_total["cells"]],
        "rule": "EXACT_EXHAUSTIVE_VISIBLE_DIRECT_FRONTIER_ALL_LANES",
    }
    return result


def _validate_indexed_query_evidence_v1(
    value: Any, *, compiled_specs: dict[str, Any]
) -> dict[str, Any]:
    if (
        compiled_specs["evaluation"].get("format_version") != "ACCOUNTING_FAMILY_EVALUATION_SPEC_V8"
        or type(value) is not dict
        or set(value)
        != {
            "accepted_regions",
            "candidate_dispositions",
            "format_version",
            "query_receipt",
        }
        or value.get("format_version") != INDEXED_QUERY_EVIDENCE_FORMAT_VERSION
        or type(value.get("query_receipt")) is not dict
        or type(value.get("candidate_dispositions")) is not list
        or type(value.get("accepted_regions")) is not list
    ):
        raise _error("Gemini JSON indexed query evidence is invalid")
    receipt = value["query_receipt"]
    dispositions = value["candidate_dispositions"]
    regions = value["accepted_regions"]
    policy = compiled_specs["title_axis_projection_policy"]
    required_child_roles = set(policy["required_child_roles"])
    minimum_child_roles = policy["minimum_distinct_child_roles"]
    locator_base_keys = {
        "alias",
        "page_json_version_id",
        "physical_page",
        "section_id",
        "source_exact",
        "source_kind",
        "table_id",
    }

    def valid_locator(locator: Any) -> bool:
        if locator is None:
            return True
        if type(locator) is not dict:
            return False
        optional_keys = set(locator) - locator_base_keys
        if optional_keys not in (set(), {"narrative_ordinal"}, {"row_id"}):
            return False
        return (
            locator_base_keys <= set(locator)
            and type(locator["alias"]) is str
            and bool(locator["alias"].strip())
            and type(locator["source_exact"]) is str
            and bool(locator["source_exact"].strip())
            and locator["source_kind"]
            in {"ROW_LABEL", "SECTION_NARRATIVE", "SECTION_TITLE", "TABLE_TITLE"}
            and type(locator["physical_page"]) is int
            and locator["physical_page"] >= 1
            and type(locator["page_json_version_id"]) is str
            and re.fullmatch(r"gfpstorev1:json:[0-9a-f]{64}", locator["page_json_version_id"])
            is not None
            and type(locator["section_id"]) is str
            and re.fullmatch(r"s[1-9][0-9]*", locator["section_id"]) is not None
            and type(locator["table_id"]) is str
            and re.fullmatch(r"t[1-9][0-9]*", locator["table_id"]) is not None
            and (
                "narrative_ordinal" not in locator
                or (
                    locator["source_kind"] == "SECTION_NARRATIVE"
                    and type(locator["narrative_ordinal"]) is int
                    and locator["narrative_ordinal"] >= 1
                )
            )
            and (
                "row_id" not in locator
                or (
                    locator["source_kind"] == "ROW_LABEL"
                    and type(locator["row_id"]) is str
                    and re.fullmatch(r"r[1-9][0-9]*", locator["row_id"]) is not None
                )
            )
        )

    disposition_counts: dict[str, int] = {}
    disposition_keys = []
    disposition_order = []
    for disposition in dispositions:
        if (
            type(disposition) is not dict
            or set(disposition)
            != {
                "branch_evidence",
                "child_role_row_assignment",
                "context_pages",
                "disposition",
                "hard_negative_evidence",
                "owner_evidence",
                "owner_failure_reason",
                "owner_mode",
                "page_json_version_id",
                "physical_page",
                "reset_evidence",
                "section_id",
                "selected_page_ordinal",
                "source_logical_name",
                "source_sha256",
                "table_id",
            }
            or type(disposition.get("disposition")) is not str
            or disposition["disposition"]
            not in {
                "ACCEPTED",
                "BRANCH_ABSENT",
                "HARD_NEGATIVE_VETO",
                "INSUFFICIENT_DISTINCT_CHILD_ROLES",
                "OWNER_ABSENT_OR_AMBIGUOUS",
            }
            or type(disposition.get("selected_page_ordinal")) is not int
            or disposition["selected_page_ordinal"] <= 0
            or type(disposition.get("physical_page")) is not int
            or disposition["physical_page"] <= 0
            or type(disposition.get("source_logical_name")) is not str
            or not disposition["source_logical_name"]
            or type(disposition.get("source_sha256")) is not str
            or re.fullmatch(r"[0-9a-f]{64}", disposition["source_sha256"]) is None
            or type(disposition.get("page_json_version_id")) is not str
            or re.fullmatch(
                r"gfpstorev1:json:[0-9a-f]{64}",
                disposition["page_json_version_id"],
            )
            is None
            or type(disposition.get("section_id")) is not str
            or re.fullmatch(r"s[1-9][0-9]*", disposition["section_id"]) is None
            or type(disposition.get("table_id")) is not str
            or re.fullmatch(r"t[1-9][0-9]*", disposition["table_id"]) is None
            or type(disposition.get("child_role_row_assignment")) is not list
            or not disposition["child_role_row_assignment"]
            or any(
                type(item) is not dict
                or set(item) != {"role", "row_id"}
                or item["role"] not in required_child_roles
                or type(item["row_id"]) is not str
                or re.fullmatch(r"r[1-9][0-9]*", item["row_id"]) is None
                for item in disposition["child_role_row_assignment"]
            )
            or [item["role"] for item in disposition["child_role_row_assignment"]]
            != sorted(item["role"] for item in disposition["child_role_row_assignment"])
            or len({item["role"] for item in disposition["child_role_row_assignment"]})
            != len(disposition["child_role_row_assignment"])
            or type(disposition.get("context_pages")) is not list
            or not disposition["context_pages"]
            or disposition["context_pages"]
            != sorted(
                disposition["context_pages"],
                key=lambda item: item.get("physical_page", -1) if type(item) is dict else -1,
            )
            or any(
                type(context) is not dict
                or set(context) != {"page_json_version_id", "physical_page"}
                or type(context["physical_page"]) is not int
                or context["physical_page"] <= 0
                or type(context["page_json_version_id"]) is not str
                or re.fullmatch(
                    r"gfpstorev1:json:[0-9a-f]{64}",
                    context["page_json_version_id"],
                )
                is None
                for context in disposition["context_pages"]
            )
            or len({context["physical_page"] for context in disposition["context_pages"]})
            != len(disposition["context_pages"])
            or {
                "page_json_version_id": disposition["page_json_version_id"],
                "physical_page": disposition["physical_page"],
            }
            not in disposition["context_pages"]
            or len({item["row_id"] for item in disposition["child_role_row_assignment"]})
            != len(disposition["child_role_row_assignment"])
            or not all(
                valid_locator(disposition[key])
                for key in (
                    "branch_evidence",
                    "hard_negative_evidence",
                    "owner_evidence",
                    "reset_evidence",
                )
            )
            or disposition.get("owner_mode")
            not in {
                None,
                "BOUNDED_PRECEDING_SELECTED_PAGE_OWNER_CARRY",
                "LOCAL_EXPLICIT_OWNER",
            }
            or (
                disposition.get("owner_failure_reason") is not None
                and type(disposition["owner_failure_reason"]) is not str
            )
        ):
            raise _error("Gemini JSON indexed candidate disposition is invalid")
        assignment_count = len(disposition["child_role_row_assignment"])
        if (
            (
                disposition["disposition"] == "ACCEPTED"
                and (
                    assignment_count < minimum_child_roles
                    or disposition["branch_evidence"] is None
                    or disposition["owner_evidence"] is None
                    or disposition["hard_negative_evidence"] is not None
                    or disposition["owner_mode"] is None
                )
            )
            or (
                disposition["disposition"] == "INSUFFICIENT_DISTINCT_CHILD_ROLES"
                and (
                    assignment_count >= minimum_child_roles
                    or disposition["branch_evidence"] is None
                    or disposition["owner_evidence"] is None
                    or disposition["hard_negative_evidence"] is not None
                )
            )
            or (
                disposition["disposition"] == "HARD_NEGATIVE_VETO"
                and disposition["hard_negative_evidence"] is None
            )
            or (
                disposition["disposition"] == "BRANCH_ABSENT"
                and (
                    disposition["branch_evidence"] is not None
                    or disposition["hard_negative_evidence"] is not None
                )
            )
            or (
                disposition["disposition"] == "OWNER_ABSENT_OR_AMBIGUOUS"
                and (
                    disposition["branch_evidence"] is None
                    or disposition["owner_evidence"] is not None
                    or disposition["hard_negative_evidence"] is not None
                    or disposition["owner_failure_reason"] is None
                )
            )
        ):
            raise _error("Gemini JSON indexed candidate disposition is incoherent")
        disposition_counts[disposition["disposition"]] = (
            disposition_counts.get(disposition["disposition"], 0) + 1
        )
        disposition_keys.append(
            tuple(
                disposition.get(key)
                for key in (
                    "source_logical_name",
                    "source_sha256",
                    "physical_page",
                    "page_json_version_id",
                    "section_id",
                    "table_id",
                )
            )
        )
        disposition_order.append(
            (
                disposition["selected_page_ordinal"],
                int(disposition["section_id"][1:]),
                int(disposition["table_id"][1:]),
            )
        )
    if len(disposition_keys) != len(set(disposition_keys)):
        raise _error("Gemini JSON indexed candidate disposition axis repeats a table")
    if disposition_order != sorted(disposition_order) or len(disposition_order) != len(
        set(disposition_order)
    ):
        raise _error("Gemini JSON indexed candidate disposition axis is not ordered")
    path_axis = []
    ordinal_axis = []
    region_keys = []
    query_receipt_sha256 = canonical_json_sha256_v1(receipt)
    accepted_dispositions = [
        disposition for disposition in dispositions if disposition["disposition"] == "ACCEPTED"
    ]
    if len(regions) != len(accepted_dispositions):
        raise _error("Gemini JSON indexed accepted region count is invalid")
    for region, disposition in zip(regions, accepted_dispositions, strict=True):
        structural_receipt = region.get("structural_context_receipt")
        if (
            type(region) is not dict
            or set(region)
            != {
                "context_pages",
                "document_id",
                "document_ordinal",
                "matched_child_roles",
                "page_json_version_id",
                "physical_page",
                "section_id",
                "source_logical_name",
                "source_sha256",
                "structural_context_receipt",
                "table_id",
            }
            or type(region.get("document_ordinal")) is not int
            or region["document_ordinal"] <= 0
            or type(region.get("document_id")) is not str
            or not region["document_id"]
            or type(region.get("context_pages")) is not list
            or not region["context_pages"]
            or any(
                type(context) is not dict
                or set(context) != {"page_json_version_id", "physical_page"}
                or type(context["physical_page"]) is not int
                or context["physical_page"] <= 0
                or type(context["page_json_version_id"]) is not str
                or re.fullmatch(
                    r"gfpstorev1:json:[0-9a-f]{64}",
                    context["page_json_version_id"],
                )
                is None
                for context in region["context_pages"]
            )
            or region["context_pages"] != disposition["context_pages"]
            or region["context_pages"]
            != sorted(region["context_pages"], key=lambda item: item["physical_page"])
            or len({item["physical_page"] for item in region["context_pages"]})
            != len(region["context_pages"])
            or {
                "page_json_version_id": region["page_json_version_id"],
                "physical_page": region["physical_page"],
            }
            not in region["context_pages"]
            or type(region.get("matched_child_roles")) is not list
            or region["matched_child_roles"]
            != [item["role"] for item in disposition["child_role_row_assignment"]]
            or type(structural_receipt) is not dict
            or set(structural_receipt)
            != {
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
            or structural_receipt.get("branch_evidence") != disposition["branch_evidence"]
            or structural_receipt.get("owner_evidence") != disposition["owner_evidence"]
            or structural_receipt.get("owner_mode") != disposition["owner_mode"]
            or structural_receipt.get("candidate_page_json_version_id")
            != region["page_json_version_id"]
            or structural_receipt.get("candidate_section_id") != region["section_id"]
            or structural_receipt.get("candidate_table_id") != region["table_id"]
            or structural_receipt.get("title_axis_query_receipt_sha256") != query_receipt_sha256
            or any(
                region[key] != disposition[key]
                for key in (
                    "page_json_version_id",
                    "physical_page",
                    "section_id",
                    "source_logical_name",
                    "source_sha256",
                    "table_id",
                )
            )
        ):
            raise _error("Gemini JSON indexed accepted region is invalid")
        path_axis.append(
            {
                key: region[key]
                for key in (
                    "source_logical_name",
                    "physical_page",
                    "page_json_version_id",
                    "section_id",
                    "table_id",
                )
            }
        )
        ordinal_axis.append(
            {
                "document_ordinal": region["document_ordinal"],
                "source_sha256": region["source_sha256"],
                **{
                    key: region[key]
                    for key in (
                        "physical_page",
                        "page_json_version_id",
                        "section_id",
                        "table_id",
                    )
                },
            }
        )
        region_keys.append(
            tuple(
                region[key]
                for key in (
                    "source_logical_name",
                    "source_sha256",
                    "physical_page",
                    "page_json_version_id",
                    "section_id",
                    "table_id",
                )
            )
        )
    accepted_disposition_keys = [
        key
        for disposition, key in zip(dispositions, disposition_keys, strict=True)
        if disposition["disposition"] == "ACCEPTED"
    ]
    expected_disposition_counts = [
        {"count": disposition_counts[item], "disposition": item}
        for item in sorted(disposition_counts)
    ]
    group_receipt = compiled_specs.get("query_group_compilation_receipt")
    fixed_receipt_keys = {
        "candidate_disposition_axis_sha256",
        "candidate_disposition_count",
        "candidate_disposition_counts",
        "candidate_surface_decode_count",
        "candidate_table_count_before_structural_axis",
        "context_page_json_decode_count",
        "context_page_title_scan_count",
        "exact_region_count",
        "exact_region_ordinal_source_axis_sha256",
        "exact_region_path_axis_sha256",
        "indexed_row_hit_count",
        "indexed_row_hit_table_count",
        "minimum_distinct_child_roles",
        "near_structural_evidence_document_count",
        "owner_mode_counts",
        "selected_page_json_frontier_sha256",
        "selected_page_json_version_count",
        "structural_surface_kinds",
        "target_document_count",
    }
    expected_owner_mode_counts = []
    owner_mode_counts: dict[str, int] = {}
    for disposition in dispositions:
        if disposition["disposition"] == "ACCEPTED":
            mode = disposition["owner_mode"]
            owner_mode_counts[mode] = owner_mode_counts.get(mode, 0) + 1
    expected_owner_mode_counts = [
        {"count": owner_mode_counts[mode], "mode": mode} for mode in sorted(owner_mode_counts)
    ]
    expected_near_sources = {
        disposition["source_logical_name"]
        for disposition in dispositions
        if disposition["hard_negative_evidence"] is None
        and (
            disposition["branch_evidence"] is not None or disposition["owner_evidence"] is not None
        )
    }
    if (
        type(group_receipt) is not dict
        or set(receipt) != fixed_receipt_keys | set(group_receipt)
        or len(region_keys) != len(set(region_keys))
        or region_keys != accepted_disposition_keys
        or ordinal_axis
        != sorted(
            ordinal_axis,
            key=lambda item: (
                item["document_ordinal"],
                item["physical_page"],
                item["section_id"],
                item["table_id"],
                item["page_json_version_id"],
            ),
        )
        or receipt.get("candidate_disposition_axis_sha256")
        != canonical_json_sha256_v1(dispositions)
        or receipt.get("candidate_disposition_count") != len(dispositions)
        or receipt.get("candidate_disposition_counts") != expected_disposition_counts
        or receipt.get("candidate_surface_decode_count") != len(dispositions)
        or receipt.get("candidate_table_count_before_structural_axis") != len(dispositions)
        or receipt.get("indexed_row_hit_table_count") != len(dispositions)
        or type(receipt.get("indexed_row_hit_count")) is not int
        or receipt["indexed_row_hit_count"] < len(dispositions)
        or receipt.get("minimum_distinct_child_roles") != minimum_child_roles
        or receipt.get("near_structural_evidence_document_count") != len(expected_near_sources)
        or receipt.get("owner_mode_counts") != expected_owner_mode_counts
        or receipt.get("structural_surface_kinds") != policy["structural_surface_kinds"]
        or receipt.get("exact_region_count") != len(regions)
        or receipt.get("exact_region_path_axis_sha256") != canonical_json_sha256_v1(path_axis)
        or receipt.get("exact_region_ordinal_source_axis_sha256")
        != canonical_json_sha256_v1(ordinal_axis)
        or receipt.get("target_document_count")
        != len({region["source_logical_name"] for region in regions})
        or type(receipt.get("selected_page_json_version_count")) is not int
        or receipt["selected_page_json_version_count"] <= 0
        or any(
            disposition["selected_page_ordinal"] > receipt["selected_page_json_version_count"]
            for disposition in dispositions
        )
        or type(receipt.get("selected_page_json_frontier_sha256")) is not str
        or len(receipt["selected_page_json_frontier_sha256"]) != 64
        or type(receipt.get("context_page_json_decode_count")) is not int
        or receipt["context_page_json_decode_count"] < len(regions)
        or receipt.get("context_page_title_scan_count")
        != receipt.get("context_page_json_decode_count")
        or any(receipt.get(key) != item for key, item in group_receipt.items())
    ):
        raise _error("Gemini JSON indexed query evidence does not replay")
    return canonical_clone_v1(value)


def _validate_indexed_rollforward_query_evidence_v1(
    value: Any, *, compiled_specs: dict[str, Any]
) -> dict[str, Any]:
    """Validate the persisted projection envelope without reopening SQLite.

    The runner performs the stronger public database replay first.  This replay
    binds every accepted locator back to one typed disposition and recomputes
    all source-axis hashes and aggregate counts so persisted bytes cannot drift
    coherently after ingestion.
    """

    if (
        compiled_specs.get("engine_format_version")
        != "GEMINI_JSON_ROLLFORWARD_ACCOUNTING_FAMILY_V1"
        or type(value) is not dict
        or set(value)
        != {
            "accepted_regions",
            "candidate_dispositions",
            "document_fiscal_close_context_evidence",
            "document_unit_context_evidence",
            "format_version",
            "query_receipt",
            "selected_document_axis",
        }
        or value.get("format_version") != ROLLFORWARD_INDEXED_QUERY_EVIDENCE_FORMAT_VERSION
        or type(value.get("accepted_regions")) is not list
        or type(value.get("candidate_dispositions")) is not list
        or type(value.get("document_fiscal_close_context_evidence")) is not list
        or type(value.get("document_unit_context_evidence")) is not list
        or type(value.get("query_receipt")) is not dict
        or type(value.get("selected_document_axis")) is not list
        or not value["selected_document_axis"]
    ):
        raise _error("Gemini JSON indexed roll-forward query evidence is invalid")
    regions = value["accepted_regions"]
    dispositions = value["candidate_dispositions"]
    receipt = value["query_receipt"]
    selected_documents = value["selected_document_axis"]
    document_fiscal_close_context = value["document_fiscal_close_context_evidence"]
    document_unit_context = value["document_unit_context_evidence"]
    locator_fields = {
        "document_id",
        "page_json_version_id",
        "physical_page",
        "section_id",
        "source_logical_name",
        "source_sha256",
        "table_id",
    }
    disposition_fields = locator_fields | {
        "candidate_evidence_sha256",
        "classification",
        "column_axis_sha256",
        "continuation_cluster_admission",
        "context_axis_sha256",
        "disposition",
        "document_ordinal",
        "query_policy_sha256",
        "reason_codes",
        "row_axis_sha256",
        "selected_page_ordinal",
    }
    region_fields = locator_fields | {
        "candidate_evidence_sha256",
        "column_axis_sha256",
        "context_axis_sha256",
        "document_ordinal",
        "layout_kind",
        "orientation",
        "row_axis_sha256",
        "selected_page_ordinal",
    }
    disposition_kinds = {
        "ACCEPTED_COMPONENT",
        "CORE_MOVEMENT_TOPOLOGY_INCOMPLETE",
        "DOCUMENT_CLUSTER_AMBIGUOUS",
        "LANE_OR_PERIOD_AXIS_UNCLASSIFIED",
        "LOCAL_OWNER_NOT_VISIBLE",
        "LOCAL_TABLE_CLASSIFICATION_ERROR",
        "RESET_OR_HARD_NEGATIVE_VETO",
    }
    classification_fields = {
        "column_lane_roles",
        "continuation_evidence",
        "context_lane_assignment_source_kind",
        "context_lane_candidates_in_source_order",
        "context_lane_evidence",
        "context_lane_role",
        "context_reset_visible",
        "lane_population_assignment_receipt",
        "local_owner_visible",
        "movement_roles_in_source_order",
        "orientation",
        "period_context_owner_visible",
        "reasons",
        "structural_hard_negative_visible",
    }
    lane_roles = {item["role"] for item in compiled_specs["layout"]["lane_roles"]}
    movement_roles = {item["role"] for item in compiled_specs["layout"]["movement_roles"]}
    query_policy = {
        "aliases_by_role": compiled_specs["aliases_by_role"],
        "engine_format_version": compiled_specs["engine_format_version"],
        "family_id": compiled_specs["topology"]["family_id"],
        "layout": compiled_specs["layout"],
    }
    query_policy_sha256 = canonical_json_sha256_v1(query_policy)

    selected_document_fields = {
        "document_id",
        "document_ordinal",
        "source_logical_name",
        "source_sha256",
    }
    selected_document_by_source: dict[str, dict[str, Any]] = {}
    for ordinal, document in enumerate(selected_documents, start=1):
        if (
            type(document) is not dict
            or set(document) != selected_document_fields
            or document.get("document_ordinal") != ordinal
            or type(document.get("document_id")) is not str
            or re.fullmatch(r"gfpstorev1:document:[0-9a-f]{64}", document["document_id"]) is None
            or type(document.get("source_logical_name")) is not str
            or not document["source_logical_name"]
            or document["source_logical_name"] in selected_document_by_source
            or type(document.get("source_sha256")) is not str
            or re.fullmatch(r"[0-9a-f]{64}", document["source_sha256"]) is None
        ):
            raise _error("Gemini JSON indexed roll-forward selected document axis is invalid")
        selected_document_by_source[document["source_logical_name"]] = document

    from bctc_ai.evaluation.gemini_json_rollforward_accounting_family_v1 import (
        _canonical_money_units_from_surface_v1,
        _validated_document_fiscal_close_context_evidence_v1,
    )

    unit_binding_by_canonical = {
        item["canonical_unit"]: item for item in compiled_specs["layout"]["unit_bindings"]
    }
    unit_context_fields = {
        "canonical_unit",
        "canonical_units",
        "distinct_page_count",
        "document_id",
        "document_ordinal",
        "evidence",
        "evidence_axis_sha256",
        "minimum_distinct_page_count",
        "rule",
        "source_logical_name",
        "source_sha256",
        "status",
    }
    unit_evidence_fields = {
        "canonical_unit",
        "column_id",
        "currency",
        "magnitude_power10",
        "page_json_version_id",
        "physical_page",
        "section_id",
        "selected_page_ordinal",
        "source_kind",
        "table_id",
        "text_exact",
    }
    unit_statuses = {
        "CONFLICTING_AUTHENTICATED_DOCUMENT_MONEY_UNIT_EVIDENCE",
        "INSUFFICIENT_AUTHENTICATED_DOCUMENT_MONEY_UNIT_EVIDENCE",
        "UNIQUE_AUTHENTICATED_DOCUMENT_MONEY_UNIT_CONSENSUS",
    }
    if len(document_unit_context) != len(selected_documents):
        raise _error("Gemini JSON indexed roll-forward document-unit axis is incomplete")
    for document, context in zip(selected_documents, document_unit_context, strict=True):
        if (
            type(context) is not dict
            or set(context) != unit_context_fields
            or any(
                context.get(field) != document[field]
                for field in (
                    "document_id",
                    "document_ordinal",
                    "source_logical_name",
                    "source_sha256",
                )
            )
            or type(context.get("evidence")) is not list
            or type(context.get("canonical_units")) is not list
            or context.get("canonical_units") != sorted(set(context["canonical_units"]))
            or context.get("minimum_distinct_page_count") != 2
            or context.get("status") not in unit_statuses
            or context.get("rule")
            != (
                "SELECTED_PAGE_VERSION_ONLY_EXPLICIT_TABLE_UNIT_MAGNITUDE_AND_"
                "CURRENCY_TWO_PAGE_UNIQUE_CANONICAL_MONEY_UNIT_CONSENSUS"
            )
        ):
            raise _error("Gemini JSON indexed roll-forward document-unit context is invalid")
        evidence = context["evidence"]
        expected_order = sorted(
            evidence,
            key=lambda item: (
                item.get("selected_page_ordinal", 0),
                int(item.get("section_id", "s0")[1:]),
                int(item.get("table_id", "t0")[1:]),
                item.get("source_kind", ""),
                item.get("column_id") or "",
                item.get("text_exact", ""),
                item.get("canonical_unit", ""),
            ),
        )
        if expected_order != evidence or len(
            {canonical_json_sha256_v1(item) for item in evidence}
        ) != len(evidence):
            raise _error("Gemini JSON indexed roll-forward document-unit axis is unordered")
        for item in evidence:
            binding = unit_binding_by_canonical.get(item.get("canonical_unit"))
            if (
                type(item) is not dict
                or set(item) != unit_evidence_fields
                or binding is None
                or not binding["document_consensus_eligible"]
                or item.get("currency") != binding["currency"]
                or item.get("magnitude_power10") != binding["magnitude_power10"]
                or type(item.get("page_json_version_id")) is not str
                or re.fullmatch(r"gfpstorev1:json:[0-9a-f]{64}", item["page_json_version_id"])
                is None
                or type(item.get("physical_page")) is not int
                or item["physical_page"] <= 0
                or type(item.get("section_id")) is not str
                or re.fullmatch(r"s[1-9][0-9]*", item["section_id"]) is None
                or type(item.get("table_id")) is not str
                or re.fullmatch(r"t[1-9][0-9]*", item["table_id"]) is None
                or item.get("column_id") is not None
                or item.get("source_kind") != "TABLE_UNIT"
                or type(item.get("text_exact")) is not str
                or not item["text_exact"]
                or type(item.get("selected_page_ordinal")) is not int
                or item["selected_page_ordinal"] <= 0
                or item["canonical_unit"]
                not in _canonical_money_units_from_surface_v1(
                    item["text_exact"],
                    compiled_specs=compiled_specs,
                    document_consensus_only=True,
                )
            ):
                raise _error("Gemini JSON indexed roll-forward document-unit evidence is invalid")
        canonical_units = sorted({item["canonical_unit"] for item in evidence})
        distinct_page_count = len(
            {(item["physical_page"], item["page_json_version_id"]) for item in evidence}
        )
        expected_status = (
            "UNIQUE_AUTHENTICATED_DOCUMENT_MONEY_UNIT_CONSENSUS"
            if len(canonical_units) == 1 and distinct_page_count >= 2
            else "CONFLICTING_AUTHENTICATED_DOCUMENT_MONEY_UNIT_EVIDENCE"
            if len(canonical_units) > 1
            else "INSUFFICIENT_AUTHENTICATED_DOCUMENT_MONEY_UNIT_EVIDENCE"
        )
        if (
            context["canonical_units"] != canonical_units
            or context["canonical_unit"]
            != (canonical_units[0] if expected_status.startswith("UNIQUE_") else None)
            or context["distinct_page_count"] != distinct_page_count
            or context["status"] != expected_status
            or context["evidence_axis_sha256"] != canonical_json_sha256_v1(evidence)
        ):
            raise _error("Gemini JSON indexed roll-forward document-unit receipt drifted")

    if len(document_fiscal_close_context) != len(selected_documents):
        raise _error("Gemini JSON indexed roll-forward fiscal-close axis is incomplete")
    for document, context in zip(selected_documents, document_fiscal_close_context, strict=True):
        try:
            checked_context = _validated_document_fiscal_close_context_evidence_v1(
                context,
                document_id=document["document_id"],
                source_logical_name=document["source_logical_name"],
                source_sha256=document["source_sha256"],
            )
        except Exception as exc:
            raise _error(
                "Gemini JSON indexed roll-forward fiscal-close context is invalid"
            ) from exc
        if not same_typed_json_v1(checked_context, context):
            raise _error("Gemini JSON indexed roll-forward fiscal-close receipt drifted")

    def valid_locator(item: dict[str, Any]) -> bool:
        return (
            type(item.get("document_id")) is str
            and re.fullmatch(r"gfpstorev1:document:[0-9a-f]{64}", item["document_id"]) is not None
            and type(item.get("page_json_version_id")) is str
            and re.fullmatch(r"gfpstorev1:json:[0-9a-f]{64}", item["page_json_version_id"])
            is not None
            and type(item.get("physical_page")) is int
            and item["physical_page"] > 0
            and type(item.get("section_id")) is str
            and re.fullmatch(r"s[1-9][0-9]*", item["section_id"]) is not None
            and type(item.get("table_id")) is str
            and re.fullmatch(r"t[1-9][0-9]*", item["table_id"]) is not None
            and type(item.get("source_logical_name")) is str
            and bool(item["source_logical_name"])
            and type(item.get("source_sha256")) is str
            and re.fullmatch(r"[0-9a-f]{64}", item["source_sha256"]) is not None
        )

    disposition_by_evidence: dict[str, dict[str, Any]] = {}
    for disposition in dispositions:
        classification = disposition.get("classification")
        if (
            type(disposition) is not dict
            or set(disposition) != disposition_fields
            or not valid_locator(disposition)
            or disposition.get("disposition") not in disposition_kinds
            or type(disposition.get("document_ordinal")) is not int
            or disposition["document_ordinal"] <= 0
            or type(disposition.get("selected_page_ordinal")) is not int
            or disposition["selected_page_ordinal"] <= 0
            or type(disposition.get("reason_codes")) is not list
            or any(type(reason) is not str or not reason for reason in disposition["reason_codes"])
            or any(
                type(disposition.get(field)) is not str
                or re.fullmatch(r"[0-9a-f]{64}", disposition[field]) is None
                for field in (
                    "candidate_evidence_sha256",
                    "column_axis_sha256",
                    "context_axis_sha256",
                    "query_policy_sha256",
                    "row_axis_sha256",
                )
            )
            or disposition["query_policy_sha256"] != query_policy_sha256
            or disposition.get("continuation_cluster_admission") is not None
            and type(disposition["continuation_cluster_admission"]) is not dict
            or (
                classification is None
                and disposition["disposition"] != "LOCAL_TABLE_CLASSIFICATION_ERROR"
            )
            or (
                classification is not None
                and (
                    type(classification) is not dict
                    or set(classification) != classification_fields
                    or type(classification.get("column_lane_roles")) is not list
                    or any(
                        role is not None and role not in lane_roles
                        for role in classification["column_lane_roles"]
                    )
                    or type(classification.get("continuation_evidence")) is not list
                    or any(
                        type(item) is not dict for item in classification["continuation_evidence"]
                    )
                    or classification.get("context_lane_assignment_source_kind")
                    not in {None, "SECTION_TITLE", "SINGLE_NARRATIVE", "TABLE_TITLE"}
                    or type(classification.get("context_lane_candidates_in_source_order"))
                    is not list
                    or any(
                        role not in lane_roles
                        for role in classification["context_lane_candidates_in_source_order"]
                    )
                    or type(classification.get("context_lane_evidence")) is not list
                    or any(
                        type(item) is not dict for item in classification["context_lane_evidence"]
                    )
                    or classification.get("context_lane_role") not in {None, *lane_roles}
                    or type(classification.get("context_reset_visible")) is not bool
                    or type(classification.get("lane_population_assignment_receipt")) is not dict
                    or type(classification.get("local_owner_visible")) is not bool
                    or type(classification.get("movement_roles_in_source_order")) is not list
                    or any(
                        role not in movement_roles
                        for role in classification["movement_roles_in_source_order"]
                    )
                    or classification.get("orientation")
                    not in {None, "LANE_COLUMNS", "PERIOD_COLUMNS"}
                    or type(classification.get("period_context_owner_visible")) is not bool
                    or type(classification.get("reasons")) is not list
                    or any(type(reason) is not str for reason in classification["reasons"])
                    or type(classification.get("structural_hard_negative_visible")) is not bool
                )
            )
        ):
            raise _error("Gemini JSON indexed roll-forward disposition is invalid")
        selected_document = selected_document_by_source.get(disposition["source_logical_name"])
        if (
            selected_document is None
            or disposition["document_id"] != selected_document["document_id"]
            or disposition["document_ordinal"] != selected_document["document_ordinal"]
            or disposition["source_sha256"] != selected_document["source_sha256"]
        ):
            raise _error("Gemini JSON indexed roll-forward disposition source is unselected")
        if classification is None:
            expected_disposition = "LOCAL_TABLE_CLASSIFICATION_ERROR"
            expected_reasons = ["ROLLFORWARD_LOCAL_TABLE_CLASSIFICATION_ERROR"]
        else:
            expected_reasons = list(classification["reasons"])
            if (
                classification["context_reset_visible"]
                or classification["structural_hard_negative_visible"]
            ):
                expected_disposition = "RESET_OR_HARD_NEGATIVE_VETO"
            elif expected_reasons:
                expected_disposition = (
                    "CORE_MOVEMENT_TOPOLOGY_INCOMPLETE"
                    if "ROLLFORWARD_CORE_MOVEMENT_ROLES_INCOMPLETE" in expected_reasons
                    else "LANE_OR_PERIOD_AXIS_UNCLASSIFIED"
                )
            elif not classification["local_owner_visible"]:
                expected_disposition = "LOCAL_OWNER_NOT_VISIBLE"
            else:
                expected_disposition = "ACCEPTED_COMPONENT"
        cluster_ambiguous = disposition["disposition"] == "DOCUMENT_CLUSTER_AMBIGUOUS"
        if (
            cluster_ambiguous
            and (
                expected_disposition != "ACCEPTED_COMPONENT"
                or disposition["reason_codes"]
                != [*expected_reasons, "ROLLFORWARD_DOCUMENT_CLUSTER_AMBIGUOUS"]
            )
        ) or (
            not cluster_ambiguous
            and (
                disposition["disposition"] != expected_disposition
                or disposition["reason_codes"] != expected_reasons
            )
        ):
            raise _error("Gemini JSON indexed roll-forward disposition semantics drifted")
        locator = {field: disposition[field] for field in locator_fields}
        material = {
            "column_axis_sha256": disposition["column_axis_sha256"],
            "context_axis_sha256": disposition["context_axis_sha256"],
            "document_ordinal": disposition["document_ordinal"],
            "locator": locator,
            "query_policy_sha256": query_policy_sha256,
            "row_axis_sha256": disposition["row_axis_sha256"],
            "selected_page_ordinal": disposition["selected_page_ordinal"],
        }
        evidence_sha256 = canonical_json_sha256_v1(material)
        if (
            evidence_sha256 != disposition["candidate_evidence_sha256"]
            or evidence_sha256 in disposition_by_evidence
        ):
            raise _error("Gemini JSON indexed roll-forward disposition axis drifted")
        disposition_by_evidence[evidence_sha256] = disposition

    admitted_component_evidence = {
        item["candidate_evidence_sha256"]
        for item in dispositions
        if item["disposition"] == "ACCEPTED_COMPONENT"
    }
    dispositions_by_source: dict[str, list[dict[str, Any]]] = {}
    for item in dispositions:
        dispositions_by_source.setdefault(item["source_logical_name"], []).append(item)
    for source_dispositions in dispositions_by_source.values():
        source_dispositions.sort(
            key=lambda item: (
                item["selected_page_ordinal"],
                int(item["section_id"][1:]),
                int(item["table_id"][1:]),
            )
        )
        for ordinal, continuation in enumerate(source_dispositions):
            classification = continuation["classification"]
            admission = continuation["continuation_cluster_admission"]
            if admission is None:
                continue
            if (
                ordinal == 0
                or continuation["disposition"] != "LOCAL_OWNER_NOT_VISIBLE"
                or classification is None
                or not classification["continuation_evidence"]
                or set(admission)
                != {
                    "owner_candidate_evidence_sha256",
                    "reset_fence_receipt",
                    "rule",
                    "status",
                }
                or admission["rule"]
                != (
                    "IMMEDIATELY_PRECEDING_ACCEPTED_LOCAL_OWNER_SAME_EXACT_TOPOLOGY_"
                    "EXPLICIT_INCOMING_CONTINUATION_ONE_PAGE_RESET_FENCED"
                )
                or admission["status"] not in {"ADMITTED_RESET_FENCE_CLEAR", "RESET_FENCE_VETO"}
                or type(admission["reset_fence_receipt"]) is not dict
            ):
                raise _error("Gemini JSON indexed continuation admission is invalid")
            owner = source_dispositions[ordinal - 1]
            owner_classification = owner["classification"]
            reset_fence = admission["reset_fence_receipt"]
            checked_pages = reset_fence.get("checked_page_intervals")
            checked_page_fields = {
                "first_section_ordinal",
                "last_section_ordinal",
                "page_json_version_id",
                "physical_page",
                "section_table_intervals",
            }
            checked_table_fields = {
                "first_table_ordinal",
                "last_table_ordinal",
                "section_ordinal",
            }
            if (
                type(checked_pages) is not list
                or len(checked_pages) != 2
                or any(
                    type(page) is not dict
                    or set(page) != checked_page_fields
                    or type(page["first_section_ordinal"]) is not int
                    or type(page["last_section_ordinal"]) is not int
                    or not 1 <= page["first_section_ordinal"] <= page["last_section_ordinal"]
                    or type(page["section_table_intervals"]) is not list
                    or not page["section_table_intervals"]
                    or any(
                        type(interval) is not dict
                        or set(interval) != checked_table_fields
                        or type(interval["section_ordinal"]) is not int
                        or not page["first_section_ordinal"]
                        <= interval["section_ordinal"]
                        <= page["last_section_ordinal"]
                        or type(interval["first_table_ordinal"]) is not int
                        or type(interval["last_table_ordinal"]) is not int
                        or not 1
                        <= interval["first_table_ordinal"]
                        <= interval["last_table_ordinal"]
                        for interval in page["section_table_intervals"]
                    )
                    or [interval["section_ordinal"] for interval in page["section_table_intervals"]]
                    != sorted(
                        {
                            interval["section_ordinal"]
                            for interval in page["section_table_intervals"]
                        }
                    )
                    for page in checked_pages
                )
            ):
                raise _error("Gemini JSON indexed continuation reset interval is invalid")
            owner_section = int(owner["section_id"][1:])
            owner_table = int(owner["table_id"][1:])
            continuation_section = int(continuation["section_id"][1:])
            continuation_table = int(continuation["table_id"][1:])
            first_checked, last_checked = checked_pages
            first_interval = first_checked["section_table_intervals"][0]
            last_interval = last_checked["section_table_intervals"][-1]
            reset_interval_bound_to_components = (
                first_checked["page_json_version_id"] == owner["page_json_version_id"]
                and first_checked["physical_page"] == owner["physical_page"]
                and first_checked["first_section_ordinal"] == owner_section
                and first_interval["section_ordinal"] == owner_section
                and first_interval["first_table_ordinal"] == owner_table
                and last_checked["page_json_version_id"] == continuation["page_json_version_id"]
                and last_checked["physical_page"] == continuation["physical_page"]
                and last_checked["first_section_ordinal"] == 1
                and last_checked["last_section_ordinal"] == continuation_section
                and last_interval["section_ordinal"] == continuation_section
                and last_interval["first_table_ordinal"] == 1
                and last_interval["last_table_ordinal"] == continuation_table
            )
            if (
                owner["candidate_evidence_sha256"] not in admitted_component_evidence
                or admission["owner_candidate_evidence_sha256"]
                != owner["candidate_evidence_sha256"]
                or owner_classification is None
                or not owner_classification["local_owner_visible"]
                or owner_classification["orientation"] != classification["orientation"]
                or owner_classification["movement_roles_in_source_order"]
                != classification["movement_roles_in_source_order"]
                or owner_classification["column_lane_roles"] != classification["column_lane_roles"]
                or continuation["physical_page"] - owner["physical_page"] != 1
                or not reset_interval_bound_to_components
                or set(reset_fence)
                != {"checked_page_intervals", "reset_hits", "scope_kind", "status"}
                or type(reset_fence["reset_hits"]) is not list
                or reset_fence["scope_kind"]
                != "SELECTED_COMPONENTS_AND_STRICTLY_INTERVENING_SURFACES"
                or reset_fence["status"]
                != ("RESET_FENCE_VIOLATED" if reset_fence["reset_hits"] else "RESET_FENCE_CLEAR")
                or admission["status"]
                != (
                    "RESET_FENCE_VETO"
                    if reset_fence["reset_hits"]
                    else "ADMITTED_RESET_FENCE_CLEAR"
                )
            ):
                raise _error("Gemini JSON indexed continuation admission drifted")
            if admission["status"] == "ADMITTED_RESET_FENCE_CLEAR":
                admitted_component_evidence.add(continuation["candidate_evidence_sha256"])

    for region in regions:
        if (
            type(region) is not dict
            or set(region) != region_fields
            or not valid_locator(region)
            or region.get("layout_kind")
            not in {
                "LANE_TABLES_PERIOD_COLUMNS",
                "PERIOD_TABLES_LANE_COLUMNS",
                "STACKED_PERIOD_BLOCKS",
            }
            or region.get("orientation") not in {"LANE_COLUMNS", "PERIOD_COLUMNS"}
            or type(region.get("document_ordinal")) is not int
            or type(region.get("selected_page_ordinal")) is not int
            or any(
                type(region.get(field)) is not str
                or re.fullmatch(r"[0-9a-f]{64}", region[field]) is None
                for field in (
                    "candidate_evidence_sha256",
                    "column_axis_sha256",
                    "context_axis_sha256",
                    "row_axis_sha256",
                )
            )
        ):
            raise _error("Gemini JSON indexed roll-forward accepted region is invalid")
        disposition = disposition_by_evidence.get(region["candidate_evidence_sha256"])
        if (
            disposition is None
            or disposition["candidate_evidence_sha256"] not in admitted_component_evidence
            or any(region[field] != disposition[field] for field in locator_fields)
            or any(
                region[field] != disposition[field]
                for field in (
                    "column_axis_sha256",
                    "context_axis_sha256",
                    "document_ordinal",
                    "row_axis_sha256",
                    "selected_page_ordinal",
                )
            )
            or region["orientation"] != disposition["classification"].get("orientation")
        ):
            raise _error("Gemini JSON indexed roll-forward accepted region is unbound")

    region_evidence = {item["candidate_evidence_sha256"] for item in regions}
    if len(region_evidence) != len(regions) or region_evidence != admitted_component_evidence:
        raise _error("Gemini JSON indexed roll-forward accepted component frontier drifted")

    ordered_regions = sorted(
        regions,
        key=lambda item: (
            item["document_ordinal"],
            item["physical_page"],
            int(item["section_id"][1:]),
            int(item["table_id"][1:]),
            item["page_json_version_id"],
        ),
    )
    ordered_dispositions = sorted(
        dispositions,
        key=lambda item: (
            item["selected_page_ordinal"],
            int(item["section_id"][1:]),
            int(item["table_id"][1:]),
            item["page_json_version_id"],
        ),
    )
    disposition_counts = {
        kind: sum(item["disposition"] == kind for item in dispositions)
        for kind in sorted({item["disposition"] for item in dispositions})
    }
    layout_counts = {
        "LANE_TABLES_PERIOD_COLUMNS": 0,
        "PERIOD_TABLES_LANE_COLUMNS": 0,
        "STACKED_PERIOD_BLOCKS": 0,
    }
    same_counts = {"LANE_TABLES_PERIOD_COLUMNS": 0, "PERIOD_TABLES_LANE_COLUMNS": 0}
    adjacent_counts = {"LANE_TABLES_PERIOD_COLUMNS": 0, "PERIOD_TABLES_LANE_COLUMNS": 0}
    by_source: dict[str, list[dict[str, Any]]] = {}
    for region in regions:
        by_source.setdefault(region["source_logical_name"], []).append(region)
    for source_regions in by_source.values():
        kinds = {region["layout_kind"] for region in source_regions}
        orientations = {region["orientation"] for region in source_regions}
        source_identities = {
            (region["document_id"], region["source_sha256"], region["document_ordinal"])
            for region in source_regions
        }
        pages = {region["physical_page"] for region in source_regions}
        if len(kinds) != 1 or len(source_identities) != 1 or max(pages) - min(pages) > 1:
            raise _error("Gemini JSON indexed roll-forward document layout is ambiguous")
        kind = next(iter(kinds))
        if (
            (
                kind == "STACKED_PERIOD_BLOCKS"
                and (len(source_regions) != 1 or orientations != {"LANE_COLUMNS"})
            )
            or (
                kind == "PERIOD_TABLES_LANE_COLUMNS"
                and (len(source_regions) != 2 or orientations != {"LANE_COLUMNS"})
            )
            or (
                kind == "LANE_TABLES_PERIOD_COLUMNS"
                and (len(source_regions) != 2 or orientations != {"PERIOD_COLUMNS"})
            )
        ):
            raise _error("Gemini JSON indexed roll-forward layout semantics drifted")
        layout_counts[kind] += 1
        if len(source_regions) == 2:
            (same_counts if len(pages) == 1 else adjacent_counts)[kind] += 1

    receipt_fields = {
        "accepted_layout_adjacent_page_counts",
        "accepted_layout_counts",
        "accepted_layout_same_page_counts",
        "candidate_disposition_axis_sha256",
        "candidate_disposition_count",
        "candidate_disposition_counts",
        "candidate_table_count",
        "column_record_count",
        "context_record_count",
        "endpoint_prefixes",
        "endpoint_seed_row_count",
        "exact_region_axis_sha256",
        "exact_region_count",
        "document_fiscal_close_context_axis_sha256",
        "document_fiscal_close_context_count",
        "document_fiscal_close_qualifying_evidence_count",
        "document_unit_context_axis_sha256",
        "document_unit_context_count",
        "document_unit_qualifying_evidence_count",
        "family_id",
        "format_version",
        "query_policy_sha256",
        "row_record_count",
        "selected_page_json_frontier_sha256",
        "selected_page_json_version_count",
        "selected_document_axis_sha256",
        "selected_document_count",
        "selected_source_axis_sha256",
        "target_document_count",
        "target_page_count",
    }
    if (
        set(receipt) != receipt_fields
        or ordered_regions != regions
        or ordered_dispositions != dispositions
        or receipt.get("format_version") != "GEMINI_JSON_INDEXED_ROLLFORWARD_QUERY_RECEIPT_V1"
        or receipt.get("family_id") != compiled_specs["topology"]["family_id"]
        or receipt.get("query_policy_sha256") != query_policy_sha256
        or receipt.get("candidate_disposition_axis_sha256")
        != canonical_json_sha256_v1(dispositions)
        or receipt.get("candidate_disposition_count") != len(dispositions)
        or receipt.get("candidate_disposition_counts") != disposition_counts
        or receipt.get("candidate_table_count") != len(dispositions)
        or receipt.get("context_record_count") != len(dispositions)
        or receipt.get("exact_region_axis_sha256") != canonical_json_sha256_v1(regions)
        or receipt.get("exact_region_count") != len(regions)
        or receipt.get("document_fiscal_close_context_axis_sha256")
        != canonical_json_sha256_v1(document_fiscal_close_context)
        or receipt.get("document_fiscal_close_context_count") != len(document_fiscal_close_context)
        or receipt.get("document_fiscal_close_qualifying_evidence_count")
        != sum(
            len(year_context["evidence"])
            for item in document_fiscal_close_context
            for year_context in item["year_contexts"]
        )
        or receipt.get("document_unit_context_axis_sha256")
        != canonical_json_sha256_v1(document_unit_context)
        or receipt.get("document_unit_context_count") != len(document_unit_context)
        or receipt.get("document_unit_qualifying_evidence_count")
        != sum(len(item["evidence"]) for item in document_unit_context)
        or receipt.get("target_document_count") != len(by_source)
        or receipt.get("selected_document_count") != len(selected_documents)
        or receipt.get("selected_document_axis_sha256")
        != canonical_json_sha256_v1(selected_documents)
        or receipt.get("target_page_count")
        != len({region["page_json_version_id"] for region in regions})
        or receipt.get("accepted_layout_counts") != layout_counts
        or receipt.get("accepted_layout_same_page_counts") != same_counts
        or receipt.get("accepted_layout_adjacent_page_counts") != adjacent_counts
        or type(receipt.get("selected_page_json_version_count")) is not int
        or receipt["selected_page_json_version_count"] <= 0
        or any(
            item["selected_page_ordinal"] > receipt["selected_page_json_version_count"]
            for item in dispositions
        )
        or any(
            type(receipt.get(field)) is not str
            or re.fullmatch(r"[0-9a-f]{64}", receipt[field]) is None
            for field in (
                "selected_page_json_frontier_sha256",
                "selected_source_axis_sha256",
            )
        )
        or type(receipt.get("endpoint_prefixes")) is not list
        or receipt["endpoint_prefixes"] != sorted(set(receipt["endpoint_prefixes"]))
        or any(
            type(receipt.get(field)) is not int or receipt[field] < 0
            for field in (
                "column_record_count",
                "endpoint_seed_row_count",
                "row_record_count",
            )
        )
        or receipt["endpoint_seed_row_count"] < len(dispositions)
    ):
        raise _error("Gemini JSON indexed roll-forward query evidence does not replay")
    return canonical_clone_v1(value)


def validate_gemini_json_rollforward_sweep_query_bindings_v1(
    *,
    trials: Any,
    indexed_query_evidence: Any,
    compiled_specs: dict[str, Any],
) -> list[dict[str, Any]]:
    """Bind every roll-forward trial and candidate to exact selected query evidence."""

    evidence = _validate_indexed_rollforward_query_evidence_v1(
        indexed_query_evidence,
        compiled_specs=compiled_specs,
    )
    if type(trials) is not list:
        raise _error("Gemini JSON roll-forward trial axis is invalid")
    selected_documents = evidence["selected_document_axis"]
    if len(trials) != len(selected_documents):
        raise _error("Gemini JSON roll-forward trial axis does not cover selected documents")

    from bctc_ai.evaluation.gemini_json_rollforward_accounting_family_v1 import (
        _DATE_DMY,
        _DATE_WORDS,
        _assign_period_column_lane_roles,
        _date_tokens,
        _document_fiscal_close_year_binding_receipt_v1,
        _endpoint_source_receipt,
        _normalized,
        _rebuild_rollforward_equations_from_role_vectors_v1,
        _rebuild_rollforward_potential_mappings_from_role_vectors_v1,
        _two_period_endpoint_continuity_v1,
        build_gemini_json_rollforward_region_query_receipt_v1,
    )

    locator_fields = (
        "document_id",
        "page_json_version_id",
        "physical_page",
        "section_id",
        "source_logical_name",
        "source_sha256",
        "table_id",
    )
    trial_fields = {
        "candidate_count",
        "candidates",
        "document_ordinal",
        "mappings",
        "reasons",
        "selected_candidate_id",
        "source_logical_name",
        "source_sha256",
        "status",
    }
    candidate_fields = {
        "candidate_id",
        "claim_boundary",
        "closure_receipt",
        "component_regions",
        "component_table_refs",
        "document_id",
        "family_id",
        "mappings",
        "page_json_version_id",
        "physical_page",
        "reasons",
        "section_id",
        "source_logical_name",
        "source_sha256",
        "status",
        "table_id",
    }
    closure_fields = {
        "bound_unit",
        "component_classifications",
        "component_region_axis_sha256",
        "duplicate_source_ambiguities",
        "endpoint_continuity_receipts",
        "equations",
        "lane_assignment_receipts",
        "lane_population_assignment_receipts",
        "lane_population_continuity_receipt",
        "orientation",
        "period_assignment_receipt",
        "period_lane_populations",
        "population_receipt",
        "potential_mapping_count",
        "query_receipt",
        "role_vectors",
        "rule",
        "unresolved_frontiers",
        "unit_provenance_receipt",
    }
    accepted_by_source: dict[str, list[dict[str, Any]]] = {}
    accepted_indexed_by_source: dict[str, list[dict[str, Any]]] = {}
    for accepted in evidence["accepted_regions"]:
        accepted_by_source.setdefault(accepted["source_logical_name"], []).append(
            {field: accepted[field] for field in locator_fields}
        )
        accepted_indexed_by_source.setdefault(accepted["source_logical_name"], []).append(accepted)
    accepted_classification_by_locator = {
        canonical_json_sha256_v1(
            {field: disposition[field] for field in locator_fields}
        ): disposition["classification"]
        for disposition in evidence["candidate_dispositions"]
        if disposition["disposition"] == "ACCEPTED_COMPONENT"
        or (
            type(disposition.get("continuation_cluster_admission")) is dict
            and disposition["continuation_cluster_admission"].get("status")
            == "ADMITTED_RESET_FENCE_CLEAR"
        )
    }
    continuation_admission_by_locator = {
        canonical_json_sha256_v1(
            {field: disposition[field] for field in locator_fields}
        ): disposition["continuation_cluster_admission"]
        for disposition in evidence["candidate_dispositions"]
        if type(disposition.get("continuation_cluster_admission")) is dict
        and disposition["continuation_cluster_admission"].get("status")
        == "ADMITTED_RESET_FENCE_CLEAR"
    }
    near_sources = {
        disposition["source_logical_name"]
        for disposition in evidence["candidate_dispositions"]
        if type(disposition["classification"]) is dict
        and disposition["classification"]["local_owner_visible"] is True
        and disposition["classification"]["structural_hard_negative_visible"] is False
    }
    unit_context_by_source = {
        context["source_logical_name"]: context
        for context in evidence["document_unit_context_evidence"]
    }
    fiscal_context_by_source = {
        context["source_logical_name"]: context
        for context in evidence["document_fiscal_close_context_evidence"]
    }

    def validate_candidate(
        candidate: Any,
        *,
        document: dict[str, Any],
        accepted_regions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if (
            type(candidate) is not dict
            or set(candidate) != candidate_fields
            or candidate.get("family_id") != compiled_specs["topology"]["family_id"]
            or candidate.get("claim_boundary") != compiled_specs["claim_boundary"]
            or candidate.get("status") not in {READY, UNRESOLVED}
            or type(candidate.get("reasons")) is not list
            or candidate["reasons"] != sorted(set(candidate["reasons"]))
            or any(type(reason) is not str or not reason for reason in candidate["reasons"])
            or type(candidate.get("mappings")) is not list
            or type(candidate.get("closure_receipt")) is not dict
            or set(candidate["closure_receipt"]) != closure_fields
            or candidate["closure_receipt"].get("rule")
            != "EXACT_SIGNED_ROLLFORWARD_ONE_UNKNOWN_FULL_RANK"
            or type(candidate.get("component_regions")) is not list
            or not candidate["component_regions"]
            or candidate["source_logical_name"] != document["source_logical_name"]
            or candidate["source_sha256"] != document["source_sha256"]
            or candidate["document_id"] != document["document_id"]
            or not same_typed_json_v1(candidate["component_regions"], accepted_regions)
        ):
            raise _error("Gemini JSON roll-forward candidate is not query-evidence bound")
        first = accepted_regions[0]
        if any(
            candidate[field] != first[field]
            for field in (
                "page_json_version_id",
                "physical_page",
                "section_id",
                "table_id",
            )
        ):
            raise _error("Gemini JSON roll-forward candidate root locator drifted")
        expected_component_table_refs = [
            {"section_id": region["section_id"], "table_id": region["table_id"]}
            for region in accepted_regions
            if region["page_json_version_id"] == first["page_json_version_id"]
        ]
        if not same_typed_json_v1(candidate["component_table_refs"], expected_component_table_refs):
            raise _error("Gemini JSON roll-forward candidate component refs drifted")
        expected_query_receipt = build_gemini_json_rollforward_region_query_receipt_v1(
            accepted_regions
        )
        if not same_typed_json_v1(
            candidate["closure_receipt"].get("query_receipt"),
            expected_query_receipt,
        ) or candidate["closure_receipt"].get(
            "component_region_axis_sha256"
        ) != canonical_json_sha256_v1(accepted_regions):
            raise _error("Gemini JSON roll-forward candidate query receipt drifted")
        unit_receipt = candidate["closure_receipt"].get("unit_provenance_receipt")
        if type(unit_receipt) is not dict:
            raise _error("Gemini JSON roll-forward candidate unit provenance is absent")
        assignment_kind = unit_receipt.get("assignment_kind")
        expected_unit_context = unit_context_by_source[document["source_logical_name"]]
        embedded_unit_context = unit_receipt.get("document_unit_context_evidence")
        local_unit_axis = unit_receipt.get("local_unit_axis")
        if type(local_unit_axis) is not list or not local_unit_axis:
            raise _error("Gemini JSON roll-forward candidate local-unit axis is invalid")
        canonical_units = {
            binding["canonical_unit"] for binding in compiled_specs["layout"]["unit_bindings"]
        }
        accepted_locator_hashes = {canonical_json_sha256_v1(region) for region in accepted_regions}
        component_classifications = candidate["closure_receipt"].get("component_classifications")
        if type(component_classifications) is not list or not component_classifications:
            raise _error("Gemini JSON roll-forward component unit classification is absent")
        classified_unit_by_locator = {}
        expected_component_classifications = []
        for item in component_classifications:
            if (
                type(item) is not dict
                or type(item.get("locator")) is not dict
                or canonical_json_sha256_v1(item["locator"]) not in accepted_locator_hashes
                or item.get("bound_unit") not in {None, *canonical_units}
            ):
                raise _error("Gemini JSON roll-forward component unit classification is invalid")
            locator_hash = canonical_json_sha256_v1(item["locator"])
            if locator_hash in classified_unit_by_locator:
                raise _error("Gemini JSON roll-forward component unit classification is duplicated")
            classified_unit_by_locator[locator_hash] = item["bound_unit"]
            indexed_classification = accepted_classification_by_locator.get(locator_hash)
            if type(indexed_classification) is not dict:
                raise _error("Gemini JSON roll-forward component classification is unindexed")
            expected_component_classifications.append(
                {
                    "bound_unit": item["bound_unit"],
                    **canonical_clone_v1(indexed_classification),
                    "locator": canonical_clone_v1(item["locator"]),
                }
            )
        if set(classified_unit_by_locator) != accepted_locator_hashes:
            raise _error("Gemini JSON roll-forward component unit classification is incomplete")
        if not same_typed_json_v1(
            component_classifications,
            expected_component_classifications,
        ):
            raise _error(
                "Gemini JSON roll-forward component classification drifted from indexed evidence"
            )
        indexed_layout_kinds = {
            item["layout_kind"]
            for item in accepted_indexed_by_source[document["source_logical_name"]]
        }
        if len(indexed_layout_kinds) != 1 or candidate["closure_receipt"].get(
            "orientation"
        ) != next(iter(indexed_layout_kinds)):
            raise _error("Gemini JSON roll-forward orientation drifted from indexed evidence")
        period_column_records = [
            {
                "classification": accepted_classification_by_locator[
                    canonical_json_sha256_v1(region)
                ],
                "locator": region,
            }
            for region in accepted_regions
            if accepted_classification_by_locator[canonical_json_sha256_v1(region)]["orientation"]
            == "PERIOD_COLUMNS"
        ]
        _lane_roles, expected_lane_assignment_receipts, lane_assignment_reasons = (
            _assign_period_column_lane_roles(
                period_column_records,
                compiled_specs=compiled_specs,
            )
        )
        if lane_assignment_reasons or not same_typed_json_v1(
            candidate["closure_receipt"].get("lane_assignment_receipts"),
            expected_lane_assignment_receipts,
        ):
            raise _error("Gemini JSON roll-forward lane assignment receipt drifted")
        local_fragment_keys = []
        for item in local_unit_axis:
            if (
                type(item) is not dict
                or set(item) != {"block_ordinal", "bound_unit", "locator"}
                or type(item.get("block_ordinal")) is not int
                or item["block_ordinal"] <= 0
                or type(item.get("locator")) is not dict
                or canonical_json_sha256_v1(item["locator"]) not in accepted_locator_hashes
                or item.get("bound_unit") not in {None, *canonical_units}
            ):
                raise _error("Gemini JSON roll-forward candidate local-unit axis is invalid")
            local_fragment_keys.append(
                (canonical_json_sha256_v1(item["locator"]), item["block_ordinal"])
            )
            if (
                item["bound_unit"]
                != classified_unit_by_locator[canonical_json_sha256_v1(item["locator"])]
            ):
                raise _error("Gemini JSON roll-forward local unit classification drifted")
        if len(local_fragment_keys) != len(set(local_fragment_keys)):
            raise _error("Gemini JSON roll-forward candidate local-unit axis is duplicated")
        local_units = [item.get("bound_unit") for item in local_unit_axis]
        local_non_null_units = {unit for unit in local_units if unit is not None}
        if assignment_kind == "AUTHENTICATED_DOCUMENT_MONEY_UNIT_CONSENSUS_INHERITED":
            if (
                any(unit is not None for unit in local_units)
                or expected_unit_context["status"]
                != "UNIQUE_AUTHENTICATED_DOCUMENT_MONEY_UNIT_CONSENSUS"
                or not same_typed_json_v1(embedded_unit_context, expected_unit_context)
                or unit_receipt.get("resolved_canonical_unit")
                != expected_unit_context["canonical_unit"]
            ):
                raise _error("Gemini JSON roll-forward inherited unit provenance drifted")
        elif assignment_kind == "UNRESOLVED_NO_LOCAL_OR_DOCUMENT_UNIT_CONSENSUS":
            if (
                any(unit is not None for unit in local_units)
                or expected_unit_context["status"]
                == "UNIQUE_AUTHENTICATED_DOCUMENT_MONEY_UNIT_CONSENSUS"
                or not same_typed_json_v1(embedded_unit_context, expected_unit_context)
                or unit_receipt.get("resolved_canonical_unit") is not None
            ):
                raise _error("Gemini JSON roll-forward unresolved unit provenance drifted")
        elif assignment_kind == "ALL_COMPONENTS_EXPLICIT_LOCAL_CANONICAL_UNIT":
            expected_resolved_unit = (
                next(iter(local_non_null_units)) if len(local_non_null_units) == 1 else None
            )
            if (
                any(unit is None for unit in local_units)
                or embedded_unit_context is not None
                or unit_receipt.get("resolved_canonical_unit") != expected_resolved_unit
            ):
                raise _error("Gemini JSON roll-forward local unit provenance drifted")
        elif assignment_kind == "MIXED_LOCAL_VISIBLE_AND_MISSING_UNIT_NOT_INHERITED":
            expected_resolved_unit = (
                next(iter(local_non_null_units)) if len(local_non_null_units) == 1 else None
            )
            if (
                not any(unit is None for unit in local_units)
                or not local_non_null_units
                or embedded_unit_context is not None
                or unit_receipt.get("resolved_canonical_unit") != expected_resolved_unit
            ):
                raise _error("Gemini JSON roll-forward mixed unit provenance drifted")
        else:
            raise _error("Gemini JSON roll-forward unit assignment kind is invalid")
        resolved_unit = unit_receipt.get("resolved_canonical_unit")
        role_vectors = candidate["closure_receipt"].get("role_vectors")
        endpoint_receipts = candidate["closure_receipt"].get("endpoint_continuity_receipts")
        if (
            type(role_vectors) is not list
            or type(endpoint_receipts) is not list
            or any(type(receipt) is not dict for receipt in endpoint_receipts)
        ):
            raise _error("Gemini JSON roll-forward unit-bearing closure axes are invalid")
        expected_lane_population_assignments = []
        for local_unit_item in local_unit_axis:
            locator_hash = canonical_json_sha256_v1(local_unit_item["locator"])
            indexed_classification = accepted_classification_by_locator[locator_hash]
            if indexed_classification["orientation"] != "LANE_COLUMNS":
                continue
            expected_lane_population_assignments.append(
                {
                    "block_ordinal": local_unit_item["block_ordinal"],
                    "locator": canonical_clone_v1(local_unit_item["locator"]),
                    "receipt": canonical_clone_v1(
                        indexed_classification["lane_population_assignment_receipt"]
                    ),
                }
            )
        lane_population_assignments = candidate["closure_receipt"].get(
            "lane_population_assignment_receipts"
        )
        if not same_typed_json_v1(
            lane_population_assignments,
            expected_lane_population_assignments,
        ):
            raise _error("Gemini JSON roll-forward lane-population assignments drifted from index")
        aggregate_population_axis = []
        for wrapper in expected_lane_population_assignments:
            receipt = wrapper["receipt"]
            decision_by_lane = {item["lane_role"]: item for item in receipt["decisions"]}
            for lane_role in sorted(
                {role for role in receipt["raw_lane_roles_by_column"] if role is not None}
            ):
                if receipt["raw_lane_roles_by_column"].count(lane_role) < 2:
                    continue
                decision = decision_by_lane.get(lane_role)
                aggregate_population_axis.append(
                    {
                        "aggregate_identity_normalized": (
                            decision["aggregate_identity_normalized"] if decision else None
                        ),
                        "block_ordinal": wrapper["block_ordinal"],
                        "lane_role": lane_role,
                        "locator": canonical_clone_v1(wrapper["locator"]),
                        "status": (
                            "UNIQUE_EXACT_HORIZONTAL_AGGREGATE" if decision else "UNRESOLVED"
                        ),
                    }
                )
        expected_lane_population_continuity = {
            "aggregate_population_axis": aggregate_population_axis,
            "rule": "SAME_EXACT_DECLARED_AGGREGATE_IDENTITY_ACROSS_PERIOD_COMPONENTS",
        }
        if not same_typed_json_v1(
            candidate["closure_receipt"].get("lane_population_continuity_receipt"),
            expected_lane_population_continuity,
        ):
            raise _error("Gemini JSON roll-forward lane-population continuity drifted")
        expected_period_lane_populations = {
            period_role: sorted(
                {
                    vector["lane_role"]
                    for vector in role_vectors
                    if vector["period_role"] == period_role
                }
            )
            for period_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD")
        }
        if not same_typed_json_v1(
            candidate["closure_receipt"].get("period_lane_populations"),
            expected_period_lane_populations,
        ):
            raise _error("Gemini JSON roll-forward period-lane population axis drifted")

        owner_components = [
            item for item in component_classifications if item["local_owner_visible"]
        ]
        continuation_components = [
            item for item in component_classifications if not item["local_owner_visible"]
        ]

        def locator_order(item: Mapping[str, Any]) -> tuple[int, int, int]:
            locator = item["locator"]
            return (
                locator["physical_page"],
                int(locator["section_id"][1:]),
                int(locator["table_id"][1:]),
            )

        unbound_continuations = [
            item
            for item in continuation_components
            if not any(locator_order(owner) < locator_order(item) for owner in owner_components)
        ]
        population_receipt = candidate["closure_receipt"].get("population_receipt")
        if type(population_receipt) is not dict:
            raise _error("Gemini JSON roll-forward population receipt is invalid")
        reset_fence = population_receipt.get("reset_fence_receipt")
        if type(reset_fence) is not dict or type(reset_fence.get("reset_hits")) is not list:
            raise _error("Gemini JSON roll-forward reset-fence receipt is invalid")
        if not continuation_components:
            expected_checked_pages = []
            page_axis: list[tuple[int, str]] = []
            for region in accepted_regions:
                page_key = (region["physical_page"], region["page_json_version_id"])
                if page_key not in page_axis:
                    page_axis.append(page_key)
            for physical_page, version_id in page_axis:
                page_regions = [
                    item
                    for item in accepted_regions
                    if item["physical_page"] == physical_page
                    and item["page_json_version_id"] == version_id
                ]
                section_ordinals = sorted({int(item["section_id"][1:]) for item in page_regions})
                expected_checked_pages.append(
                    {
                        "first_section_ordinal": section_ordinals[0],
                        "last_section_ordinal": section_ordinals[-1],
                        "page_json_version_id": version_id,
                        "physical_page": physical_page,
                        "section_table_intervals": [
                            {
                                "first_table_ordinal": int(item["table_id"][1:]),
                                "last_table_ordinal": int(item["table_id"][1:]),
                                "section_ordinal": int(item["section_id"][1:]),
                            }
                            for item in page_regions
                        ],
                    }
                )
            expected_reset_fence = {
                "checked_page_intervals": expected_checked_pages,
                "reset_hits": canonical_clone_v1(reset_fence["reset_hits"]),
                "scope_kind": "INDEPENDENT_LOCAL_OWNER_SELECTED_COMPONENTS_ONLY",
                "status": (
                    "RESET_FENCE_VIOLATED" if reset_fence["reset_hits"] else "RESET_FENCE_CLEAR"
                ),
            }
        else:
            continuation_admissions = [
                continuation_admission_by_locator.get(canonical_json_sha256_v1(item["locator"]))
                for item in continuation_components
            ]
            if len(continuation_admissions) != 1 or type(continuation_admissions[0]) is not dict:
                raise _error("Gemini JSON roll-forward continuation admission is absent")
            expected_reset_fence = canonical_clone_v1(
                continuation_admissions[0]["reset_fence_receipt"]
            )
        expected_population_receipt = {
            "binding_kind": (
                "ALL_COMPONENTS_EXPLICIT_LOCAL_OWNER"
                if owner_components and not continuation_components
                else "BOUNDED_SELECTED_COMPONENT_OWNER_CONTINUATION"
                if owner_components
                else "UNRESOLVED_NO_LOCAL_OWNER"
            ),
            "continuation_component_locators": [
                canonical_clone_v1(item["locator"]) for item in continuation_components
            ],
            "continuation_evidence_receipts": [
                {
                    "evidence": canonical_clone_v1(item["continuation_evidence"]),
                    "locator": canonical_clone_v1(item["locator"]),
                }
                for item in continuation_components
            ],
            "max_physical_page_span": (
                accepted_regions[-1]["physical_page"] - accepted_regions[0]["physical_page"]
            ),
            "owner_component_locators": [
                canonical_clone_v1(item["locator"]) for item in owner_components
            ],
            "reset_fence_receipt": expected_reset_fence,
            "reset_or_hard_negative_visible": bool(reset_fence["reset_hits"])
            or any(
                item["context_reset_visible"] or item["structural_hard_negative_visible"]
                for item in component_classifications
            ),
            "rule": (
                "AT_LEAST_ONE_SELECTED_COMPONENT_LOCAL_OWNER_OTHER_COMPONENTS_ONLY_"
                "WITHIN_ORDERED_ONE_PAGE_RESET_FENCED_CLUSTER"
            ),
            "unbound_continuation_locators": [
                canonical_clone_v1(item["locator"]) for item in unbound_continuations
            ],
        }
        if not same_typed_json_v1(population_receipt, expected_population_receipt):
            raise _error("Gemini JSON roll-forward population receipt drifted")
        if unit_receipt.get("rule") != (
            "LOCAL_CANONICAL_UNIT_OR_SELECTED_VERSION_DOCUMENT_TWO_PAGE_"
            "UNIQUE_MAGNITUDE_CURRENCY_CONSENSUS_NO_SCALE_CONVERSION"
        ):
            raise _error("Gemini JSON roll-forward unit provenance rule drifted")
        expected_fiscal_context = fiscal_context_by_source[document["source_logical_name"]]

        def validate_period_fiscal_binding(period_evidence: Any) -> None:
            if type(period_evidence) is not dict:
                raise _error("Gemini JSON roll-forward period evidence is invalid")
            date_sources = period_evidence.get("date_source_exact_axis")
            if type(date_sources) is not list or not date_sources:
                raise _error("Gemini JSON roll-forward period source axis is invalid")
            embedded_binding = period_evidence.get("document_fiscal_close_year_binding_receipt")
            has_full_date = any(
                type(source) is str
                and (
                    _DATE_DMY.search(_normalized(source)) or _DATE_WORDS.search(_normalized(source))
                )
                for source in date_sources
            )
            try:
                period_year = date.fromisoformat(period_evidence["period_date"]).year
            except (KeyError, TypeError, ValueError) as exc:
                raise _error("Gemini JSON roll-forward period date is invalid") from exc
            expected_binding = _document_fiscal_close_year_binding_receipt_v1(
                expected_fiscal_context,
                year=period_year,
            )
            if has_full_date:
                if embedded_binding is not None:
                    raise _error("Gemini JSON roll-forward full-date fiscal binding drifted")
            elif not same_typed_json_v1(embedded_binding, expected_binding):
                raise _error("Gemini JSON roll-forward fiscal year binding drifted")

        for vector in role_vectors:
            period_evidence = vector.get("period_semantics_evidence")
            if period_evidence is None:
                if (
                    vector.get("resolved_period") == "COMPARATIVE_UNDATED"
                    and vector.get("period_date") is None
                ):
                    continue
                raise _error("Gemini JSON roll-forward period evidence is invalid")
            validate_period_fiscal_binding(period_evidence)
        nested_axis = [candidate["closure_receipt"]]
        while nested_axis:
            nested = nested_axis.pop()
            if type(nested) is dict:
                if {
                    "date_source_exact_axis",
                    "document_fiscal_close_year_binding_receipt",
                    "period_date",
                    "source_kind",
                } <= set(nested):
                    validate_period_fiscal_binding(nested)
                nested_axis.extend(nested.values())
            elif type(nested) is list:
                nested_axis.extend(nested)
        role_vector_by_key = {}
        for vector in role_vectors:
            key = (
                vector.get("period_role"),
                vector.get("lane_role"),
                vector.get("movement_role"),
            )
            if key in role_vector_by_key:
                raise _error("Gemini JSON roll-forward role-vector axis is duplicated")
            role_vector_by_key[key] = vector
        replayed_endpoint_receipts, replayed_endpoint_reasons = _two_period_endpoint_continuity_v1(
            role_vectors,
            compiled_specs=compiled_specs,
        )
        if not same_typed_json_v1(endpoint_receipts, replayed_endpoint_receipts) or any(
            reason not in candidate["reasons"] for reason in replayed_endpoint_reasons
        ):
            raise _error("Gemini JSON roll-forward endpoint continuity replay drifted")
        replayed_equations = _rebuild_rollforward_equations_from_role_vectors_v1(
            role_vectors,
            compiled_specs=compiled_specs,
        )
        if not same_typed_json_v1(
            candidate["closure_receipt"].get("equations"), replayed_equations
        ):
            raise _error("Gemini JSON roll-forward equation axis replay drifted")
        expected_unresolved_frontiers = []
        for equation in replayed_equations:
            if equation["status"] in {"EXACT", "EXACT_ONE_UNKNOWN_INFERRED"}:
                continue
            period_role = equation["period_role"]
            lane_role = equation["lane_role"]
            scope = lane_role if period_role == "CURRENT_PERIOD" else f"{period_role}:{lane_role}"
            reason = f"ROLLFORWARD_LANE_EQUATION_{equation['status']}:{scope}"
            expected_unresolved_frontiers.append(
                {
                    "lane_role": lane_role,
                    "period_role": period_role,
                    "reason": reason,
                    "unknown_roles": [
                        item["role"]
                        for item in equation["role_coefficients"]
                        if item["coefficient"] is None
                    ],
                    "source_records": [
                        {
                            "locator": canonical_clone_v1(vector["locator"]),
                            "movement_role": vector["movement_role"],
                            "row_id": vector["row_id"],
                        }
                        for vector in sorted(
                            role_vectors,
                            key=lambda item: (
                                item["period_role"],
                                item["lane_role"],
                                item["movement_role"],
                            ),
                        )
                        if vector["period_role"] == period_role and vector["lane_role"] == lane_role
                    ],
                }
            )
        if not same_typed_json_v1(
            candidate["closure_receipt"].get("unresolved_frontiers"),
            expected_unresolved_frontiers,
        ):
            raise _error("Gemini JSON roll-forward unresolved frontier replay drifted")
        expected_duplicate_ambiguities = []
        role_vector_by_fragment_key = {
            (
                canonical_json_sha256_v1(vector["locator"]),
                vector["block_ordinal"],
                vector["lane_role"],
                vector["movement_role"],
            ): vector
            for vector in role_vectors
        }
        for wrapper in expected_lane_population_assignments:
            locator_hash = canonical_json_sha256_v1(wrapper["locator"])
            block_ordinal = wrapper["block_ordinal"]
            for unresolved in wrapper["receipt"]["unresolved_duplicate_lanes"]:
                lane_role = unresolved["lane_role"]
                ordinals = unresolved["candidate_column_ordinals"]
                for source in unresolved["duplicate_source_cell_receipts"]:
                    if source["block_ordinal"] != block_ordinal:
                        continue
                    vector = role_vector_by_fragment_key.get(
                        (
                            locator_hash,
                            block_ordinal,
                            lane_role,
                            source["movement_role"],
                        )
                    )
                    if vector is None or vector["column_ordinal"] not in ordinals:
                        raise _error("Gemini JSON roll-forward duplicate-source vector is absent")
                    first_offset = ordinals.index(vector["column_ordinal"])
                    first_cell = source["candidate_cells"][first_offset]
                    for offset, column_ordinal in enumerate(ordinals):
                        if offset == first_offset:
                            continue
                        expected_duplicate_ambiguities.append(
                            {
                                "corroborated_key": [
                                    vector["period_role"],
                                    lane_role,
                                    source["movement_role"],
                                ],
                                "disposition": (
                                    "IDENTICAL_DUPLICATE_SOURCE_AMBIGUOUS"
                                    if first_cell == source["candidate_cells"][offset]
                                    else "CONFLICTING_DUPLICATE_SOURCE_AMBIGUOUS"
                                ),
                                "first_column_ordinal": vector["column_ordinal"],
                                "first_locator": canonical_clone_v1(wrapper["locator"]),
                                "second_column_ordinal": column_ordinal,
                                "second_locator": canonical_clone_v1(wrapper["locator"]),
                            }
                        )
        if not same_typed_json_v1(
            candidate["closure_receipt"].get("duplicate_source_ambiguities"),
            expected_duplicate_ambiguities,
        ):
            raise _error("Gemini JSON roll-forward duplicate-source receipt drifted")
        replayed_potential_mappings = _rebuild_rollforward_potential_mappings_from_role_vectors_v1(
            role_vectors,
            compiled_specs=compiled_specs,
        )
        expected_candidate_mappings = (
            replayed_potential_mappings if candidate["status"] == READY else []
        )
        if candidate["closure_receipt"].get("potential_mapping_count") != len(
            replayed_potential_mappings
        ) or not same_typed_json_v1(candidate["mappings"], expected_candidate_mappings):
            raise _error("Gemini JSON roll-forward mapping axis replay drifted")
        period_assignment_receipt = candidate["closure_receipt"].get("period_assignment_receipt")
        if (
            type(period_assignment_receipt) is not dict
            or set(period_assignment_receipt)
            != {"assignments", "movement_context_evidence", "rule", "status"}
            or type(period_assignment_receipt.get("assignments")) is not list
            or type(period_assignment_receipt.get("movement_context_evidence")) is not list
            or period_assignment_receipt.get("rule")
            != (
                "ORDERED_DISTINCT_MOVEMENT_DATES_TO_ADJACENT_COMPONENTS_OR_"
                "ONE_CURRENT_DATE_PLUS_SYMBOLIC_COMPARATIVE"
            )
        ):
            raise _error("Gemini JSON roll-forward period assignment receipt is invalid")
        assignments = period_assignment_receipt["assignments"]
        movement_axis = period_assignment_receipt["movement_context_evidence"]
        movement_fields = {
            "date",
            "date_token",
            "document_fiscal_close_year_binding_receipt",
            "narrative_ordinal",
            "source_exact",
            "source_kind",
            "status",
            "year",
        }
        source_kinds = {
            "IMMEDIATELY_PRECEDING_SECTION_TITLE",
            "SELECTED_SECTION_MOVEMENT_NARRATIVE",
            "SELECTED_SECTION_TITLE",
        }
        for movement_evidence in movement_axis:
            if (
                type(movement_evidence) is not dict
                or set(movement_evidence) != movement_fields
                or type(movement_evidence.get("source_exact")) is not str
                or not movement_evidence["source_exact"]
                or movement_evidence.get("source_kind") not in source_kinds
                or (
                    movement_evidence["source_kind"] == "SELECTED_SECTION_MOVEMENT_NARRATIVE"
                    and (
                        type(movement_evidence.get("narrative_ordinal")) is not int
                        or movement_evidence["narrative_ordinal"] <= 0
                    )
                )
                or (
                    movement_evidence["source_kind"] != "SELECTED_SECTION_MOVEMENT_NARRATIVE"
                    and movement_evidence.get("narrative_ordinal") is not None
                )
            ):
                raise _error("Gemini JSON roll-forward movement-period evidence is invalid")
            tokens = _date_tokens(movement_evidence["source_exact"])
            unique_dates = {token[0] for token in tokens}
            folded = _normalized(movement_evidence["source_exact"])
            full_date_visible = bool(
                folded and (_DATE_DMY.search(folded) or _DATE_WORDS.search(folded))
            )
            status = movement_evidence.get("status")
            embedded_binding = movement_evidence.get("document_fiscal_close_year_binding_receipt")
            if status == "EXACT_ONE_YEAR_BOUND_TO_DOCUMENT_FISCAL_CLOSE_CONTEXT":
                year = movement_evidence.get("year")
                selected_token = tokens[-1] if len(unique_dates) == 1 else None
                expected_binding = (
                    _document_fiscal_close_year_binding_receipt_v1(
                        expected_fiscal_context,
                        year=year,
                    )
                    if type(year) is int
                    else None
                )
                if (
                    full_date_visible
                    or selected_token is None
                    or expected_binding is None
                    or not same_typed_json_v1(embedded_binding, expected_binding)
                    or movement_evidence.get("date_token") != selected_token[1]
                    or movement_evidence.get("date")
                    != date(
                        year,
                        expected_binding["year_context"]["month"],
                        expected_binding["year_context"]["day"],
                    ).isoformat()
                ):
                    raise _error("Gemini JSON roll-forward bound movement year drifted")
            elif status == "EXACT_ONE_DATE":
                selected_token = tokens[-1] if len(unique_dates) == 1 else None
                if (
                    not full_date_visible
                    or selected_token is None
                    or embedded_binding is not None
                    or movement_evidence.get("date") != selected_token[0].isoformat()
                    or movement_evidence.get("date_token") != selected_token[1]
                    or movement_evidence.get("year") != selected_token[0].year
                ):
                    raise _error("Gemini JSON roll-forward full-date movement drifted")
            elif status == "EXACT_ONE_YEAR_UNBOUND":
                selected_token = tokens[-1] if len(unique_dates) == 1 else None
                if (
                    full_date_visible
                    or selected_token is None
                    or embedded_binding is not None
                    or movement_evidence.get("date") is not None
                    or movement_evidence.get("date_token") != selected_token[1]
                    or movement_evidence.get("year") != selected_token[0].year
                    or _document_fiscal_close_year_binding_receipt_v1(
                        expected_fiscal_context,
                        year=selected_token[0].year,
                    )
                    is not None
                ):
                    raise _error("Gemini JSON roll-forward unresolved movement date drifted")
            elif status == "AMBIGUOUS_MULTIPLE_DATES":
                if (
                    len(unique_dates) <= 1
                    or movement_evidence.get("date") is not None
                    or movement_evidence.get("date_token") is not None
                    or movement_evidence.get("year") is not None
                    or embedded_binding is not None
                ):
                    raise _error("Gemini JSON roll-forward ambiguous movement date drifted")
            else:
                raise _error("Gemini JSON roll-forward movement-period status is invalid")
        if len({canonical_json_sha256_v1(item) for item in movement_axis}) != len(movement_axis):
            raise _error("Gemini JSON roll-forward movement-period axis is duplicated")

        assignment_fields = {
            "assignment_kind",
            "date",
            "document_fiscal_close_year_binding_receipt",
            "locator",
            "narrative_ordinal",
            "period_role",
            "source_exact",
            "source_kind",
        }

        def assignment_from_evidence(
            evidence_item: dict[str, Any],
            *,
            locator: dict[str, Any],
            period_role: str,
            assignment_kind: str,
        ) -> dict[str, Any]:
            return {
                "assignment_kind": assignment_kind,
                "date": evidence_item["date"],
                "document_fiscal_close_year_binding_receipt": canonical_clone_v1(
                    evidence_item["document_fiscal_close_year_binding_receipt"]
                ),
                "locator": canonical_clone_v1(locator),
                "narrative_ordinal": evidence_item["narrative_ordinal"],
                "period_role": period_role,
                "source_exact": evidence_item["source_exact"],
                "source_kind": evidence_item["source_kind"],
            }

        receipt_status = period_assignment_receipt["status"]
        if receipt_status == "ORDERED_TWO_DATE_CONTEXT_BOUND":
            if len(movement_axis) != 2 or len(accepted_regions) != 2:
                raise _error("Gemini JSON roll-forward ordered period axis is incomplete")
            expected_assignments = [
                assignment_from_evidence(
                    movement_axis[ordinal],
                    locator=accepted_regions[ordinal],
                    period_role="CURRENT_PERIOD" if ordinal == 0 else "COMPARATIVE_PERIOD",
                    assignment_kind="ORDERED_MOVEMENT_NARRATIVE_TO_COMPONENT",
                )
                for ordinal in range(2)
            ]
            movement_dates = [item["date"] for item in movement_axis]
            if (
                any(
                    item["status"]
                    not in {
                        "EXACT_ONE_DATE",
                        "EXACT_ONE_YEAR_BOUND_TO_DOCUMENT_FISCAL_CLOSE_CONTEXT",
                    }
                    for item in movement_axis
                )
                or any(value is None for value in movement_dates)
                or movement_dates[0] <= movement_dates[1]
            ):
                raise _error("Gemini JSON roll-forward ordered period grammar drifted")
        elif receipt_status == "CURRENT_PLUS_SYMBOLIC_COMPARATIVE_BOUND":
            if len(movement_axis) != 1 or len(accepted_regions) != 2:
                raise _error("Gemini JSON roll-forward symbolic period axis is incomplete")
            expected_assignments = [
                assignment_from_evidence(
                    movement_axis[0],
                    locator=accepted_regions[0],
                    period_role="CURRENT_PERIOD",
                    assignment_kind="VISIBLE_CURRENT_CONTEXT_TO_FIRST_COMPONENT",
                ),
                {
                    "assignment_kind": "SYMBOLIC_UNDATED_COMPARATIVE_SECOND_COMPONENT",
                    "date": None,
                    "document_fiscal_close_year_binding_receipt": None,
                    "locator": canonical_clone_v1(accepted_regions[1]),
                    "narrative_ordinal": None,
                    "period_role": "COMPARATIVE_PERIOD",
                    "source_exact": None,
                    "source_kind": "ORDERED_ADJACENT_COMPONENT_TOPOLOGY",
                },
            ]
            if movement_axis[0]["status"] not in {
                "EXACT_ONE_DATE",
                "EXACT_ONE_YEAR_BOUND_TO_DOCUMENT_FISCAL_CLOSE_CONTEXT",
            }:
                raise _error("Gemini JSON roll-forward symbolic period grammar drifted")
        else:
            expected_assignments = []
            if receipt_status not in {
                "AMBIGUOUS_OR_REVERSED_CONTEXT_DATES",
                "CONFLICTING_TABLE_PERIOD_EVIDENCE",
                "CONTEXT_DATE_AXIS_NOT_UNIQUE",
                "LOCAL_OWNER_SCOPE_NOT_VISIBLE",
                "NOT_APPLICABLE",
                "SYMBOLIC_COMPARATIVE_PRECONDITIONS_FAILED",
                "UNEXPECTED_SECOND_TABLE_PERIOD_EVIDENCE",
            }:
                raise _error("Gemini JSON roll-forward period assignment status is invalid")
            if receipt_status in {"LOCAL_OWNER_SCOPE_NOT_VISIBLE", "NOT_APPLICABLE"} and (
                movement_axis
            ):
                raise _error("Gemini JSON roll-forward inapplicable period evidence drifted")
            adjacent_period_components = (
                candidate["closure_receipt"]["orientation"] == "PERIOD_TABLES_LANE_COLUMNS"
                and len(accepted_regions) == 2
                and accepted_regions[0]["page_json_version_id"]
                == accepted_regions[1]["page_json_version_id"]
                and accepted_regions[0]["section_id"] == accepted_regions[1]["section_id"]
                and int(accepted_regions[1]["table_id"][1:])
                == int(accepted_regions[0]["table_id"][1:]) + 1
            )
            first_period_context_owner_visible = accepted_classification_by_locator[
                canonical_json_sha256_v1(accepted_regions[0])
            ]["period_context_owner_visible"]
            if not movement_axis:
                expected_empty_status = (
                    "NOT_APPLICABLE"
                    if not adjacent_period_components
                    else "LOCAL_OWNER_SCOPE_NOT_VISIBLE"
                    if not first_period_context_owner_visible
                    else "CONTEXT_DATE_AXIS_NOT_UNIQUE"
                )
                if receipt_status != expected_empty_status:
                    raise _error("Gemini JSON roll-forward empty period-context status drifted")
            elif len(movement_axis) == 1 and movement_axis[0]["status"] in {
                "EXACT_ONE_DATE",
                "EXACT_ONE_YEAR_BOUND_TO_DOCUMENT_FISCAL_CLOSE_CONTEXT",
            }:
                movement_date = movement_axis[0]["date"]
                component_vectors = [
                    [
                        vector
                        for vector in role_vectors
                        if same_typed_json_v1(vector.get("locator"), locator)
                    ]
                    for locator in accepted_regions
                ]
                required_lanes = {
                    item["role"]
                    for item in compiled_specs["layout"]["lane_roles"]
                    if not item["optional"]
                }
                required_movements = {
                    item["role"]
                    for item in compiled_specs["layout"]["movement_roles"]
                    if item["required"]
                }
                component_fingerprints = []
                component_units = []
                full_rank_topology = len(component_vectors) == 2
                replayed_equation_by_key = {
                    (equation["period_role"], equation["lane_role"]): equation
                    for equation in replayed_equations
                }
                for vectors in component_vectors:
                    keys = [
                        (vector.get("lane_role"), vector.get("movement_role")) for vector in vectors
                    ]
                    lanes = {lane for lane, _movement in keys}
                    period_roles = {vector.get("period_role") for vector in vectors}
                    units = {vector.get("bound_unit") for vector in vectors}
                    component_fingerprints.append(sorted([list(key) for key in keys]))
                    component_units.append(units)
                    if (
                        len(keys) != len(set(keys))
                        or not required_lanes <= lanes
                        or len(period_roles) != 1
                        or len(units) != 1
                        or any(
                            not required_movements
                            <= {movement for lane, movement in keys if lane == lane_role}
                            or replayed_equation_by_key.get(
                                (next(iter(period_roles)), lane_role), {}
                            ).get("status")
                            not in {"EXACT", "EXACT_ONE_UNKNOWN_INFERRED"}
                            for lane_role in lanes
                        )
                    ):
                        full_rank_topology = False
                if (
                    len(component_fingerprints) != 2
                    or component_fingerprints[0] != component_fingerprints[1]
                    or len({next(iter(units)) for units in component_units if len(units) == 1}) != 1
                ):
                    full_rank_topology = False

                first_period_axis = (
                    {vector.get("period_date") for vector in component_vectors[0]}
                    if len(component_vectors) == 2
                    else set()
                )
                second_period_axis = (
                    {
                        (
                            vector.get("period_date"),
                            (
                                vector["period_semantics_evidence"].get("source_kind")
                                if type(vector.get("period_semantics_evidence")) is dict
                                else None
                            ),
                        )
                        for vector in component_vectors[1]
                    }
                    if len(component_vectors) == 2
                    else set()
                )
                expected_single_context_status = (
                    "SYMBOLIC_COMPARATIVE_PRECONDITIONS_FAILED"
                    if not adjacent_period_components or not full_rank_topology
                    else "CONFLICTING_TABLE_PERIOD_EVIDENCE"
                    if first_period_axis != {movement_date}
                    else "UNEXPECTED_SECOND_TABLE_PERIOD_EVIDENCE"
                    if second_period_axis
                    and second_period_axis != {(movement_date, "SELECTED_SECTION_CONTEXT")}
                    else None
                )
                if expected_single_context_status is None:
                    raise _error(
                        "Gemini JSON roll-forward unresolved period status contradicts "
                        "symbolic binding preconditions"
                    )
                if receipt_status != expected_single_context_status:
                    raise _error("Gemini JSON roll-forward one-date period status drifted")
        if any(type(item) is not dict or set(item) != assignment_fields for item in assignments):
            raise _error("Gemini JSON roll-forward period assignment is invalid")
        if not same_typed_json_v1(assignments, expected_assignments):
            raise _error("Gemini JSON roll-forward period assignment axis drifted")
        for assignment in assignments:
            matching_vectors = [
                vector
                for vector in role_vectors
                if vector.get("period_role") == assignment["period_role"]
                and same_typed_json_v1(vector.get("locator"), assignment["locator"])
            ]
            if not matching_vectors:
                raise _error("Gemini JSON roll-forward period assignment is unbound")
            period_dates = {vector.get("period_date") for vector in matching_vectors}
            period_evidence_axis = [
                vector.get("period_semantics_evidence") for vector in matching_vectors
            ]
            if len(period_dates) != 1 or assignment["date"] != next(iter(period_dates)):
                raise _error("Gemini JSON roll-forward period assignment date drifted")
            if assignment["date"] is None:
                if any(evidence is not None for evidence in period_evidence_axis):
                    raise _error("Gemini JSON roll-forward symbolic period assignment drifted")
                continue
            if any(type(evidence) is not dict for evidence in period_evidence_axis):
                raise _error("Gemini JSON roll-forward assigned period evidence is invalid")
            period_evidence = period_evidence_axis[0]
            if any(
                not same_typed_json_v1(evidence, period_evidence)
                for evidence in period_evidence_axis[1:]
            ):
                raise _error("Gemini JSON roll-forward assigned period evidence diverged")
            if (
                assignment["source_exact"] not in period_evidence["date_source_exact_axis"]
                or assignment["source_kind"] != period_evidence["source_kind"]
                or not same_typed_json_v1(
                    assignment["document_fiscal_close_year_binding_receipt"],
                    period_evidence.get("document_fiscal_close_year_binding_receipt"),
                )
            ):
                raise _error("Gemini JSON roll-forward period assignment provenance drifted")

        def require_endpoint_period_matches_role_vector(source: Any, *, lane_role: Any) -> None:
            if type(source) is not dict:
                raise _error("Gemini JSON roll-forward endpoint period receipt is invalid")
            key = (
                source.get("period_role"),
                lane_role,
                source.get("movement_role"),
            )
            role_vector = role_vector_by_key.get(key)
            if role_vector is None or not same_typed_json_v1(
                source,
                _endpoint_source_receipt(role_vector),
            ):
                raise _error("Gemini JSON roll-forward endpoint period evidence drifted")

        closure_unit_values = [
            candidate["closure_receipt"].get("bound_unit"),
            *(item.get("bound_unit") for item in component_classifications),
            *(item.get("bound_unit") for item in local_unit_axis),
            *(vector.get("bound_unit") for vector in role_vectors),
            *(mapping.get("bound_unit") for mapping in candidate["mappings"]),
        ]
        for receipt in endpoint_receipts:
            for endpoint in (
                "following_closing",
                "next_opening",
                "previous_closing",
                "previous_opening",
            ):
                source = receipt.get(endpoint)
                if type(source) is not dict:
                    raise _error("Gemini JSON roll-forward endpoint unit receipt is invalid")
                require_endpoint_period_matches_role_vector(
                    source, lane_role=receipt.get("lane_role")
                )
                closure_unit_values.append(source.get("bound_unit"))
            alignment = receipt.get("endpoint_date_alignment_receipt")
            if alignment is not None:
                if type(alignment) is not dict:
                    raise _error("Gemini JSON roll-forward endpoint alignment receipt is invalid")
                for endpoint in ("following_opening", "previous_opening"):
                    source = alignment.get(endpoint)
                    if type(source) is not dict:
                        raise _error("Gemini JSON roll-forward endpoint alignment unit is invalid")
                    require_endpoint_period_matches_role_vector(
                        source, lane_role=receipt.get("lane_role")
                    )
                    closure_unit_values.append(source.get("bound_unit"))
            boundary = receipt.get("boundary_semantics_receipt")
            if boundary is not None:
                if (
                    type(boundary) is not dict
                    or not same_typed_json_v1(
                        boundary.get("current_period_evidence"),
                        receipt["following_closing"].get("period_semantics_evidence"),
                    )
                    or type(boundary.get("previous_fiscal_year_end_semantics")) is not dict
                    or not same_typed_json_v1(
                        boundary["previous_fiscal_year_end_semantics"].get(
                            "period_semantics_evidence"
                        ),
                        receipt["previous_closing"].get("period_semantics_evidence"),
                    )
                ):
                    raise _error("Gemini JSON roll-forward boundary period evidence drifted")
        non_null_closure_units = {unit for unit in closure_unit_values if unit is not None}
        expected_non_null_closure_units = (
            {resolved_unit}
            if resolved_unit is not None
            else local_non_null_units
            if assignment_kind == "ALL_COMPONENTS_EXPLICIT_LOCAL_CANONICAL_UNIT"
            and len(local_non_null_units) > 1
            else set()
        )
        if (
            resolved_unit is not None and resolved_unit not in canonical_units
        ) or non_null_closure_units != expected_non_null_closure_units:
            raise _error("Gemini JSON roll-forward closure unit provenance drifted")
        candidate_material = {
            key: value for key, value in candidate.items() if key != "candidate_id"
        }
        if candidate.get("candidate_id") != (
            "gjfafcv1:candidate:" + canonical_json_sha256_v1(candidate_material)
        ):
            raise _error("Gemini JSON roll-forward candidate identity drifted")
        accepted_locator_hashes = {canonical_json_sha256_v1(region) for region in accepted_regions}
        for mapping in candidate["mappings"]:
            role_vector = role_vector_by_key.get(
                (
                    mapping.get("period_role"),
                    mapping.get("lane_role"),
                    mapping.get("movement_role"),
                )
            )
            if (
                type(mapping) is not dict
                or type(mapping.get("item_mapping_id")) is not str
                or type(mapping.get("locator")) is not dict
                or canonical_json_sha256_v1(mapping["locator"]) not in accepted_locator_hashes
                or type(mapping.get("movement_role")) is not str
                or type(mapping.get("lane_role")) is not str
                or type(mapping.get("report_norm_id")) is not int
                or mapping["report_norm_id"] <= 0
                or type(mapping.get("row_id")) is not str
                or type(mapping.get("bound_unit")) is not str
                or role_vector is None
                or any(
                    not same_typed_json_v1(mapping.get(field), role_vector[field])
                    for field in role_vector
                )
            ):
                raise _error("Gemini JSON roll-forward mapping is not component bound")
            mapping_material = {
                key: value for key, value in mapping.items() if key != "item_mapping_id"
            }
            if mapping["item_mapping_id"] != (
                "gjfrfmv1:item:" + canonical_json_sha256_v1(mapping_material)
            ):
                raise _error("Gemini JSON roll-forward mapping identity drifted")
        if candidate["status"] == READY:
            role_fragment_keys = (
                {
                    (
                        canonical_json_sha256_v1(vector.get("locator")),
                        vector.get("block_ordinal"),
                    )
                    for vector in role_vectors
                }
                if type(role_vectors) is list
                else set()
            )
            endpoint_units = (
                {
                    receipt.get(endpoint, {}).get("bound_unit")
                    for receipt in endpoint_receipts
                    for endpoint in (
                        "following_closing",
                        "next_opening",
                        "previous_closing",
                        "previous_opening",
                    )
                }
                if type(endpoint_receipts) is list
                else set()
            )
            if (
                type(resolved_unit) is not str
                or candidate["closure_receipt"].get("bound_unit") != resolved_unit
                or {mapping["bound_unit"] for mapping in candidate["mappings"]} != {resolved_unit}
                or type(role_vectors) is not list
                or not role_vectors
                or {vector.get("bound_unit") for vector in role_vectors} != {resolved_unit}
                or role_fragment_keys != set(local_fragment_keys)
                or not endpoint_receipts
                or endpoint_units != {resolved_unit}
            ):
                raise _error("Gemini JSON roll-forward mapped unit provenance drifted")
        if (
            candidate["status"] == READY and (candidate["reasons"] or not candidate["mappings"])
        ) or (
            candidate["status"] == UNRESOLVED
            and (not candidate["reasons"] or candidate["mappings"])
        ):
            raise _error("Gemini JSON roll-forward candidate status semantics drifted")
        return candidate

    checked_trials = []
    for ordinal, (trial, document) in enumerate(
        zip(trials, selected_documents, strict=True), start=1
    ):
        if (
            type(trial) is not dict
            or set(trial) != trial_fields
            or trial.get("document_ordinal") != ordinal
            or document["document_ordinal"] != ordinal
            or trial.get("source_logical_name") != document["source_logical_name"]
            or trial.get("source_sha256") != document["source_sha256"]
            or type(trial.get("candidates")) is not list
            or type(trial.get("candidate_count")) is not int
            or trial["candidate_count"] != len(trial["candidates"])
            or len(trial["candidates"]) > 1
            or type(trial.get("mappings")) is not list
            or type(trial.get("reasons")) is not list
            or trial["reasons"] != sorted(set(trial["reasons"]))
            or any(type(reason) is not str or not reason for reason in trial["reasons"])
            or trial.get("status") not in {READY, NOT_OBSERVED, UNRESOLVED}
            or trial.get("selected_candidate_id") is not None
            and type(trial["selected_candidate_id"]) is not str
        ):
            raise _error("Gemini JSON roll-forward trial source axis drifted")
        source = document["source_logical_name"]
        accepted_regions = accepted_by_source.get(source, [])
        near = source in near_sources
        candidates = [
            validate_candidate(
                candidate,
                document=document,
                accepted_regions=accepted_regions,
            )
            for candidate in trial["candidates"]
        ]
        if accepted_regions and len(candidates) != 1:
            raise _error("Gemini JSON roll-forward accepted source must have exactly one candidate")
        if candidates and not accepted_regions:
            raise _error("Gemini JSON roll-forward candidate has no accepted source regions")
        candidate = candidates[0] if candidates else None
        if candidate is not None and candidate["status"] == READY:
            if (
                trial["status"] != READY
                or trial["selected_candidate_id"] != candidate["candidate_id"]
                or not same_typed_json_v1(trial["mappings"], candidate["mappings"])
                or trial["reasons"]
            ):
                raise _error("Gemini JSON roll-forward READY trial binding drifted")
        elif candidate is not None:
            if (
                trial["status"] != UNRESOLVED
                or trial["selected_candidate_id"] is not None
                or trial["mappings"]
                or trial["reasons"] != candidate["reasons"]
            ):
                raise _error("Gemini JSON roll-forward unresolved candidate binding drifted")
        elif near:
            if (
                trial["status"] != UNRESOLVED
                or trial["selected_candidate_id"] is not None
                or trial["mappings"]
                or trial["reasons"] != ["PARTIAL_REQUIRED_ANCHOR_FRONTIER_ONLY"]
            ):
                raise _error("Gemini JSON roll-forward near-only trial binding drifted")
        elif (
            trial["status"] != NOT_OBSERVED
            or trial["selected_candidate_id"] is not None
            or trial["mappings"]
            or trial["reasons"]
        ):
            raise _error("Gemini JSON roll-forward not-observed trial binding drifted")
        checked_trials.append(canonical_clone_v1(trial))
    return checked_trials


def build_gemini_json_flat_family_sweep_v1(
    *,
    corpus_manifest_index_id: str,
    topology_spec: Any,
    evaluation_spec: Any,
    schema_binding_spec: Any,
    trials: list[dict[str, Any]],
    effective_page_frontier: Any | None = None,
    indexed_query_evidence: Any | None = None,
) -> dict[str, Any]:
    """Seal a complete ordered document disposition axis."""

    if (
        type(corpus_manifest_index_id) is not str
        or not corpus_manifest_index_id.startswith("gjfccmiv1:index:")
        or type(trials) is not list
        or not trials
    ):
        raise _error("Gemini JSON family sweep inputs are invalid")
    compiled = _compile_specs(topology_spec, evaluation_spec, schema_binding_spec)
    indexed_query_evidence_required = compiled["evaluation"].get("format_version") in {
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V8",
        "ACCOUNTING_ROLLFORWARD_FAMILY_EVALUATION_SPEC_V1",
    }
    if indexed_query_evidence_required != (indexed_query_evidence is not None):
        raise _error("Gemini JSON sweep and indexed query evidence presence do not agree")
    checked_indexed_query_evidence = None
    if indexed_query_evidence is not None:
        checked_indexed_query_evidence = (
            _validate_indexed_rollforward_query_evidence_v1(
                indexed_query_evidence,
                compiled_specs=compiled,
            )
            if compiled.get("engine_format_version")
            == "GEMINI_JSON_ROLLFORWARD_ACCOUNTING_FAMILY_V1"
            else _validate_indexed_query_evidence_v1(
                indexed_query_evidence,
                compiled_specs=compiled,
            )
        )
    if (
        checked_indexed_query_evidence is not None
        and compiled.get("engine_format_version") == "GEMINI_JSON_ROLLFORWARD_ACCOUNTING_FAMILY_V1"
    ):
        trials = validate_gemini_json_rollforward_sweep_query_bindings_v1(
            trials=trials,
            indexed_query_evidence=checked_indexed_query_evidence,
            compiled_specs=compiled,
        )
    checked_effective_frontier = None
    if effective_page_frontier is not None:
        from bctc_ai.storage.gemini_family_effective_page_frontier_v1 import (
            validate_gemini_family_effective_page_frontier_v1,
        )

        checked_effective_frontier = validate_gemini_family_effective_page_frontier_v1(
            effective_page_frontier
        )
        if (
            checked_effective_frontier["base_corpus_manifest_index_id"] != corpus_manifest_index_id
            or checked_effective_frontier["family_id"] != compiled["topology"]["family_id"]
        ):
            raise _error("effective page frontier does not bind the family sweep")
    statuses = {READY, NOT_OBSERVED, UNRESOLVED}
    mapping_count = 0
    for ordinal, trial in enumerate(trials, start=1):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("status") not in statuses
            or type(trial.get("mappings")) is not list
            or (trial["status"] != READY and trial["mappings"])
        ):
            raise _error("Gemini JSON family sweep trial axis is invalid")
        mapping_count += len(trial["mappings"])
    metrics = {
        "document_count": len(trials),
        "mapping_count": mapping_count,
        "not_observed_count": sum(trial["status"] == NOT_OBSERVED for trial in trials),
        "ready_count": sum(trial["status"] == READY for trial in trials),
        "unresolved_count": sum(trial["status"] == UNRESOLVED for trial in trials),
    }
    material = {
        "claim_boundary": compiled["claim_boundary"],
        "corpus_manifest_index_id": corpus_manifest_index_id,
        "family_id": compiled["topology"]["family_id"],
        "format_version": compiled["engine_format_version"],
        "metrics": metrics,
        "specs": {
            "evaluation": {
                "sha256": canonical_json_sha256_v1(evaluation_spec),
                "value": canonical_clone_v1(evaluation_spec),
            },
            "schema_binding": {
                "sha256": canonical_json_sha256_v1(schema_binding_spec),
                "value": canonical_clone_v1(schema_binding_spec),
            },
            "topology": {
                "sha256": canonical_json_sha256_v1(topology_spec),
                "value": canonical_clone_v1(topology_spec),
            },
        },
        "state": "COMPLETE_DOCUMENT_GEMINI_JSON_FAMILY_SWEEP_PROPOSAL_ONLY",
        "trials": canonical_clone_v1(trials),
        **(
            {"indexed_query_evidence": checked_indexed_query_evidence}
            if checked_indexed_query_evidence is not None
            else {}
        ),
        **(
            {"effective_page_frontier": checked_effective_frontier}
            if checked_effective_frontier is not None
            else {}
        ),
    }
    return {
        **material,
        "sweep_id": "gjfafsv1:sweep:" + canonical_json_sha256_v1(material),
    }


def validate_gemini_json_flat_family_sweep_v1(value: Any) -> dict[str, Any]:
    """Rebuild one persisted sweep envelope and reject coherent drift."""

    if (
        type(value) is not dict
        or set(value)
        not in (
            {
                "claim_boundary",
                "corpus_manifest_index_id",
                "family_id",
                "format_version",
                "metrics",
                "specs",
                "state",
                "sweep_id",
                "trials",
            },
            {
                "claim_boundary",
                "corpus_manifest_index_id",
                "family_id",
                "format_version",
                "indexed_query_evidence",
                "metrics",
                "specs",
                "state",
                "sweep_id",
                "trials",
            },
            {
                "claim_boundary",
                "corpus_manifest_index_id",
                "effective_page_frontier",
                "family_id",
                "format_version",
                "indexed_query_evidence",
                "metrics",
                "specs",
                "state",
                "sweep_id",
                "trials",
            },
            {
                "claim_boundary",
                "corpus_manifest_index_id",
                "effective_page_frontier",
                "family_id",
                "format_version",
                "metrics",
                "specs",
                "state",
                "sweep_id",
                "trials",
            },
        )
        or type(value.get("specs")) is not dict
        or set(value["specs"]) != {"evaluation", "schema_binding", "topology"}
        or any(
            type(reference) is not dict
            or set(reference) != {"sha256", "value"}
            or reference["sha256"] != canonical_json_sha256_v1(reference["value"])
            for reference in value["specs"].values()
        )
    ):
        raise _error("Gemini JSON family sweep envelope is invalid")
    rebuilt = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id=value["corpus_manifest_index_id"],
        topology_spec=value["specs"]["topology"]["value"],
        evaluation_spec=value["specs"]["evaluation"]["value"],
        schema_binding_spec=value["specs"]["schema_binding"]["value"],
        trials=value["trials"],
        effective_page_frontier=value.get("effective_page_frontier"),
        indexed_query_evidence=value.get("indexed_query_evidence"),
    )
    if rebuilt != value:
        raise _error("Gemini JSON family sweep does not replay exactly")
    return canonical_clone_v1(value)
