"""Declarative flat accounting-family closure over selected Gemini page JSON.

The primitive consumes only Gemini's structured page objects plus declarative
family/evaluation/schema specifications.  It has no PDF geometry, PP-OCR,
VietOCR, bank, filename, page-number, or note-number matching path.
"""

from __future__ import annotations

import re
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
            "format_version",
            "query_receipt",
            "selected_document_axis",
        }
        or value.get("format_version") != ROLLFORWARD_INDEXED_QUERY_EVIDENCE_FORMAT_VERSION
        or type(value.get("accepted_regions")) is not list
        or type(value.get("candidate_dispositions")) is not list
        or type(value.get("query_receipt")) is not dict
        or type(value.get("selected_document_axis")) is not list
        or not value["selected_document_axis"]
    ):
        raise _error("Gemini JSON indexed roll-forward query evidence is invalid")
    regions = value["accepted_regions"]
    dispositions = value["candidate_dispositions"]
    receipt = value["query_receipt"]
    selected_documents = value["selected_document_axis"]
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
        "local_owner_visible",
        "movement_roles_in_source_order",
        "orientation",
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
                    or type(classification.get("local_owner_visible")) is not bool
                    or type(classification.get("movement_roles_in_source_order")) is not list
                    or any(
                        role not in movement_roles
                        for role in classification["movement_roles_in_source_order"]
                    )
                    or classification.get("orientation")
                    not in {None, "LANE_COLUMNS", "PERIOD_COLUMNS"}
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
            or disposition["disposition"] != "ACCEPTED_COMPONENT"
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

    accepted_disposition_evidence = {
        item["candidate_evidence_sha256"]
        for item in dispositions
        if item["disposition"] == "ACCEPTED_COMPONENT"
    }
    region_evidence = {item["candidate_evidence_sha256"] for item in regions}
    if len(region_evidence) != len(regions) or region_evidence != accepted_disposition_evidence:
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
    accepted_by_source: dict[str, list[dict[str, Any]]] = {}
    for accepted in evidence["accepted_regions"]:
        accepted_by_source.setdefault(accepted["source_logical_name"], []).append(
            {field: accepted[field] for field in locator_fields}
        )
    near_sources = {
        disposition["source_logical_name"]
        for disposition in evidence["candidate_dispositions"]
        if type(disposition["classification"]) is dict
        and disposition["classification"]["local_owner_visible"] is True
        and disposition["classification"]["structural_hard_negative_visible"] is False
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
        candidate_material = {
            key: value for key, value in candidate.items() if key != "candidate_id"
        }
        if candidate.get("candidate_id") != (
            "gjfafcv1:candidate:" + canonical_json_sha256_v1(candidate_material)
        ):
            raise _error("Gemini JSON roll-forward candidate identity drifted")
        accepted_locator_hashes = {canonical_json_sha256_v1(region) for region in accepted_regions}
        for mapping in candidate["mappings"]:
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
            ):
                raise _error("Gemini JSON roll-forward mapping is not component bound")
            mapping_material = {
                key: value for key, value in mapping.items() if key != "item_mapping_id"
            }
            if mapping["item_mapping_id"] != (
                "gjfrfmv1:item:" + canonical_json_sha256_v1(mapping_material)
            ):
                raise _error("Gemini JSON roll-forward mapping identity drifted")
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
