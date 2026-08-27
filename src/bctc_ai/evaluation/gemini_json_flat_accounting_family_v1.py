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
)

FORMAT_VERSION = "GEMINI_JSON_FLAT_ACCOUNTING_FAMILY_SWEEP_V1"
HIERARCHICAL_FORMAT_VERSION = "GEMINI_JSON_HIERARCHICAL_ACCOUNTING_FAMILY_SWEEP_V2"
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
    if type(evaluation_spec) is dict and evaluation_spec.get("format_version") in {
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V3",
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V4",
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


def build_gemini_json_flat_family_sweep_v1(
    *,
    corpus_manifest_index_id: str,
    topology_spec: Any,
    evaluation_spec: Any,
    schema_binding_spec: Any,
    trials: list[dict[str, Any]],
    effective_page_frontier: Any | None = None,
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
    )
    if rebuilt != value:
        raise _error("Gemini JSON family sweep does not replay exactly")
    return canonical_clone_v1(value)
