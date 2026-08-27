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
READY = "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
NOT_OBSERVED = "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
UNRESOLVED = "UNRESOLVED_GEMINI_JSON_FAMILY"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_DECLARATIVE_TWO_THEN_THREE_ANCHOR_"
    "PARENT_TITLE_EXACT_ROLE_POPULATION_ALL_LANE_EXACT_DIRECT_FRONTIER_"
    "ACCOUNTING_CLOSURE_SCHEMA_MAPPING_PROPOSAL_ONLY_NO_GEOMETRY_PPOCR_"
    "VIETOCR_BANK_FILE_PAGE_NOTE_ROUTING_BACKSOLVE_CANONICAL_OR_EXPORT_AUTHORITY"
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
    try:
        topology = compile_accounting_family_topology_spec_v1(topology_spec)
    except ValueError as exc:
        raise _error("Gemini JSON family topology spec is invalid") from exc
    if (
        type(evaluation_spec) is not dict
        or set(evaluation_spec)
        != {
            "closure_policy",
            "expected_lane_unit_kinds",
            "family_id",
            "format_version",
            "period_semantics",
        }
        or evaluation_spec["format_version"] != "ACCOUNTING_FAMILY_EVALUATION_SPEC_V1"
        or evaluation_spec["family_id"] != topology["family_id"]
        or evaluation_spec["closure_policy"] != "REQUIRE_EXACT_UNIQUE_VISIBLE_TRAILING_TOTAL"
        or type(evaluation_spec["expected_lane_unit_kinds"]) is not list
        or not evaluation_spec["expected_lane_unit_kinds"]
        or any(kind != "MONEY" for kind in evaluation_spec["expected_lane_unit_kinds"])
        or type(evaluation_spec["period_semantics"]) is not str
        or not evaluation_spec["period_semantics"]
    ):
        raise _error("Gemini JSON family evaluation spec is invalid or unsupported")
    if (
        type(schema_binding_spec) is not dict
        or set(schema_binding_spec)
        != {
            "family_id",
            "family_report_norm_id",
            "format_version",
            "role_bindings",
        }
        or schema_binding_spec["format_version"] != "ACCOUNTING_FAMILY_SCHEMA_BINDING_SPEC_V1"
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
    children = topology["children"]
    child_roles = [child["role"] for child in children]
    if set(bindings) != set(child_roles):
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
        "aliases_by_role": aliases_by_role,
        "anchor_alias_groups": combinations,
        "bindings": bindings,
        "evaluation": canonical_clone_v1(evaluation_spec),
        "schema": canonical_clone_v1(schema_binding_spec),
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
    candidate_material = {
        "family_id": topology["family_id"],
        "page_json_version_id": page_json_version_id,
        "physical_page": physical_page,
        "section_id": section_id,
        "table_id": table_id,
    }
    result = {
        **candidate_material,
        "candidate_id": "gjfafcv1:candidate:" + canonical_json_sha256_v1(candidate_material),
        "mappings": [],
        "reasons": reasons,
        "status": UNRESOLVED if reasons else READY,
    }
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
        "claim_boundary": CLAIM_BOUNDARY,
        "corpus_manifest_index_id": corpus_manifest_index_id,
        "family_id": compiled["topology"]["family_id"],
        "format_version": FORMAT_VERSION,
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
    }
    return {
        **material,
        "sweep_id": "gjfafsv1:sweep:" + canonical_json_sha256_v1(material),
    }
