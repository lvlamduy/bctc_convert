"""Derive bounded row-only Gemini repair jobs from failed family validation."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    UNRESOLVED,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import _row_roles
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
)

FORMAT_VERSION = "GEMINI_JSON_REGION_REPAIR_QUEUE_V1"
REPAIR_CONTRACT_VERSION = "CONTEXTUAL_ROW_VALUES_AND_TABLE_TITLE_PERIOD_AXIS_V4"
_INVALID_ROW = re.compile(r"^(?:ROW|NESTED_COMPONENT)_MONEY_CELL_IS_NOT_EXACT_INTEGER:(\d+)$")
_INVALID_ROLE = re.compile(r"^ROLE_MONEY_CELL_IS_NOT_EXACT_INTEGER:([^:]+)$")
_INVALID_PERCENT_ROW = re.compile(r"^ROW_PERCENT_CELL_IS_NOT_EXACT_DECIMAL:(\d+)$")
_UNBOUND_VISIBLE_ROWS = re.compile(r"^UNBOUND_VISIBLE_NUMERIC_ROWS:(\d+(?:,\d+)*)$")
_MISSING_FAMILY_PARENT = re.compile(
    r"^FAMILY_PARENT_NOT_VISIBLE_IN_SECTION(?:_OR_TABLE_TITLE|_TABLE_OR_UNIQUE_ROW)$"
)
_UNSATISFIED_RESULT = re.compile(
    r"^(?:EXACT_DIRECT_FRONTIER_SOLUTION_COUNT_NOT_ONE:([^:]+):0"
    r"|NESTED_PARENT_NOT_EXACT_CHILD_SUM:([^:]+))$"
)
_STACKED_ROW = re.compile(
    r"^(?:ROW_VALUE_AXIS_INCOMPLETE|ROW_CELL_ERROR|UNMATCHED_VISIBLE_NUMERIC_ROW):"
    r"(s\d+):(t\d+):(\d+)(?::.*)?$"
)
_STACKED_LANE_EQUATION = re.compile(
    r"^VISIBLE_LANE_EQUATION_NOT_EXACT:([^:]+):(s\d+):(t\d+):r(\d+)$"
)
_STACKED_STRUCTURAL_EQUATION = re.compile(r"^STRUCTURAL_SUBTOTAL_NOT_EXACT:([^:]+):([^:]+)$")
_STACKED_PRESENTATION_EQUATION = re.compile(
    r"^PRESENTATION_NET_ROW_NOT_ONE_EXACT_LANE_EQUATION:([^:]+):(s\d+):(t\d+):r(\d+)$"
)
_STACKED_ROOT_EQUATION = re.compile(
    r"^VISIBLE_FAMILY_TOTAL_NOT_EXACT_DIRECT_FRONTIER:([^:]+):(s\d+):(t\d+):r(\d+)$"
)
_STACKED_GLOBAL_EQUATION_PREFIXES = (
    "PRESENTATION_NET_ROW_NOT_ONE_EXACT_LANE_EQUATION:",
    "VISIBLE_FAMILY_TOTAL_NOT_EXACT_DIRECT_FRONTIER:",
)
_MISSING_TITLE_FOOTNOTE_NARRATIVE = "TITLE_FOOTNOTE_NARRATIVE_SOURCE_NOT_EXACT"


class GeminiJsonRegionRepairQueueV1Error(ValueError):
    """A repair job cannot be derived without a bounded source row frontier."""


def _error(message: str) -> GeminiJsonRegionRepairQueueV1Error:
    return GeminiJsonRegionRepairQueueV1Error(message)


def _node_index(identifier: Any, *, prefix: str, limit: int) -> int:
    if type(identifier) is not str or not identifier.startswith(prefix):
        raise _error("repair candidate node ID is invalid")
    suffix = identifier.removeprefix(prefix)
    if not suffix.isdigit() or suffix.startswith("0"):
        raise _error("repair candidate node ID is invalid")
    index = int(suffix) - 1
    if not 0 <= index < limit:
        raise _error("repair candidate node ID lies outside the page JSON")
    return index


def _label_role(label: Any, *, aliases_by_role: Mapping[str, list[str]]) -> set[str]:
    if type(label) is not str or not label.strip():
        return set()
    folded = normalize_vietnamese_anchor_v1(label)
    folded = re.sub(r"^(?:[-+•]\s*|\d+(?:[.)]|\s+-)\s*)+", "", folded).strip()
    return {
        role
        for role, aliases in aliases_by_role.items()
        if any(folded == alias or folded.endswith(" " + alias) for alias in aliases)
    }


def _equation_frontier_roles(compiled_specs: Mapping[str, Any], result_role: str) -> set[str]:
    roles = {result_role}
    for equation in compiled_specs.get("equations", []):
        if equation.get("result_role") != result_role:
            continue
        for alternative in equation.get("component_role_alternatives", []):
            roles.update(alternative.get("component_roles", []))
    return roles


def build_family_region_repair_plans_v1(
    *,
    sweep: Mapping[str, Any],
    page_json_by_version: Mapping[str, Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Turn typed OCR/arithmetic failures into exact page/table/row repair jobs."""

    checked = validate_gemini_json_flat_family_sweep_v1(dict(sweep))
    aliases_by_role = compiled_specs.get("aliases_by_role")
    if type(aliases_by_role) is not dict:
        raise _error("compiled family alias axis is invalid")
    plans = []
    for trial in checked["trials"]:
        if trial["status"] != UNRESOLVED:
            continue
        for candidate in trial["candidates"]:
            if candidate["status"] != UNRESOLVED:
                continue
            version_id = candidate["page_json_version_id"]
            page_json = page_json_by_version.get(version_id)
            if type(page_json) is not dict:
                continue
            sections = page_json.get("sections")
            if type(sections) is not list:
                raise _error("repair candidate page section axis is invalid")
            section_index = _node_index(candidate["section_id"], prefix="s", limit=len(sections))
            tables = sections[section_index].get("tables")
            if type(tables) is not list:
                raise _error("repair candidate table axis is invalid")
            table_index = _node_index(candidate["table_id"], prefix="t", limit=len(tables))
            rows = tables[table_index].get("rows")
            if type(rows) is not list or not rows:
                raise _error("repair candidate row axis is invalid")

            stacked = (
                compiled_specs.get("engine_format_version")
                == "GEMINI_JSON_STACKED_PERIOD_ACCOUNTING_FAMILY_V1"
            )
            component_refs = (
                candidate.get("component_table_refs")
                if stacked
                else [
                    {
                        "section_id": candidate["section_id"],
                        "table_id": candidate["table_id"],
                    }
                ]
            )
            if (
                type(component_refs) is not list
                or not component_refs
                or any(
                    type(ref) is not dict or set(ref) != {"section_id", "table_id"}
                    for ref in component_refs
                )
            ):
                raise _error("repair candidate component table frontier is invalid")
            rows_by_ref: dict[tuple[str, str], list[dict[str, Any]]] = {}
            for ref in component_refs:
                ref_section_index = _node_index(ref["section_id"], prefix="s", limit=len(sections))
                ref_tables = sections[ref_section_index].get("tables")
                if type(ref_tables) is not list:
                    raise _error("repair component table axis is invalid")
                ref_table_index = _node_index(ref["table_id"], prefix="t", limit=len(ref_tables))
                ref_rows = ref_tables[ref_table_index].get("rows")
                if type(ref_rows) is not list or not ref_rows:
                    raise _error("repair component row axis is invalid")
                rows_by_ref[(ref["section_id"], ref["table_id"])] = ref_rows

            target_ids = set()
            trigger_kinds = set()
            equation_roles = set()
            invalid_roles = set()
            period_axis_incomplete = stacked and any(
                reason == "Gemini JSON stacked-period region does not expose exactly two periods"
                or reason.startswith("PERIOD_HAS_NO_DECLARED_ROLE:")
                for reason in candidate["reasons"]
            )
            if period_axis_incomplete:
                trigger_kinds.add("TABLE_PERIOD_AXIS_INCOMPLETE")
                for (section_id, table_id), selected_rows in rows_by_ref.items():
                    target_ids.update(
                        f"{section_id}:{table_id}:r{ordinal}"
                        for ordinal in range(1, len(selected_rows) + 1)
                    )
            table_title_incomplete = any(
                _MISSING_FAMILY_PARENT.fullmatch(reason) for reason in candidate["reasons"]
            )
            if table_title_incomplete:
                trigger_kinds.add("TABLE_EXPLICIT_FAMILY_TITLE_MISSING")
                for (section_id, table_id), selected_rows in rows_by_ref.items():
                    target_ids.update(
                        f"{section_id}:{table_id}:r{ordinal}"
                        for ordinal in range(1, len(selected_rows) + 1)
                    )
            section_narratives_incomplete = (
                _MISSING_TITLE_FOOTNOTE_NARRATIVE in candidate["reasons"]
            )
            if section_narratives_incomplete:
                trigger_kinds.add("SECTION_NARRATIVE_SOURCE_INCOMPLETE")
                target_ids.update(
                    f"{candidate['section_id']}:{candidate['table_id']}:r{ordinal}"
                    for ordinal in range(1, len(rows) + 1)
                )
            stacked_specific_periods = {
                match.group(1)
                for reason in candidate["reasons"]
                if (
                    match := (
                        _STACKED_LANE_EQUATION.fullmatch(reason)
                        or _STACKED_STRUCTURAL_EQUATION.fullmatch(reason)
                        or _STACKED_PRESENTATION_EQUATION.fullmatch(reason)
                    )
                )
                is not None
            }
            for reason in candidate["reasons"]:
                stacked_row = _STACKED_ROW.fullmatch(reason) if stacked else None
                if stacked_row is not None:
                    if period_axis_incomplete and "no exact period carrier" in reason:
                        continue
                    section_id, table_id, raw_ordinal = stacked_row.groups()
                    selected_rows = rows_by_ref.get((section_id, table_id))
                    ordinal = int(raw_ordinal)
                    if selected_rows is None or not 1 <= ordinal <= len(selected_rows):
                        raise _error("typed stacked row lies outside candidate tables")
                    target_ids.add(f"{section_id}:{table_id}:r{ordinal}")
                    trigger_kinds.add("INVALID_MONEY_CELL")
                    continue
                stacked_lane = _STACKED_LANE_EQUATION.fullmatch(reason) if stacked else None
                if stacked_lane is not None:
                    _period_role, section_id, table_id, raw_ordinal = stacked_lane.groups()
                    selected_rows = rows_by_ref.get((section_id, table_id))
                    ordinal = int(raw_ordinal)
                    if selected_rows is None or not 1 <= ordinal <= len(selected_rows):
                        raise _error("typed lane equation row lies outside candidate tables")
                    target_ids.add(f"{section_id}:{table_id}:r{ordinal}")
                    trigger_kinds.add("UNSATISFIED_EXACT_EQUATION")
                    continue
                structural = _STACKED_STRUCTURAL_EQUATION.fullmatch(reason) if stacked else None
                if structural is not None:
                    result_role = structural.group(2)
                    equation_roles.add(result_role)
                    equation_roles.update(
                        child["role"]
                        for child in compiled_specs["topology"]["children"]
                        if any(
                            matcher["within_role"] == result_role for matcher in child["matchers"]
                        )
                    )
                    trigger_kinds.add("UNSATISFIED_EXACT_EQUATION")
                    continue
                presentation = _STACKED_PRESENTATION_EQUATION.fullmatch(reason) if stacked else None
                if presentation is not None:
                    _period_role, section_id, table_id, raw_ordinal = presentation.groups()
                    selected_rows = rows_by_ref.get((section_id, table_id))
                    ordinal = int(raw_ordinal)
                    if selected_rows is None or not 1 <= ordinal <= len(selected_rows):
                        raise _error("typed presentation row lies outside candidate tables")
                    target_ids.add(f"{section_id}:{table_id}:r{ordinal}")
                    trigger_kinds.add("UNSATISFIED_EXACT_EQUATION")
                    continue
                root_equation = _STACKED_ROOT_EQUATION.fullmatch(reason) if stacked else None
                if root_equation is not None:
                    _period_role, section_id, table_id, raw_ordinal = root_equation.groups()
                    if _period_role in stacked_specific_periods:
                        continue
                    selected_rows = rows_by_ref.get((section_id, table_id))
                    ordinal = int(raw_ordinal)
                    if selected_rows is None or not 1 <= ordinal <= len(selected_rows):
                        raise _error("typed family-total row lies outside candidate tables")
                    target_ids.update(
                        f"{section_id}:{table_id}:r{row_ordinal}"
                        for row_ordinal, row in enumerate(selected_rows, start=1)
                        if type(row.get("values_exact")) is list
                        and any(value is not None for value in row["values_exact"])
                    )
                    trigger_kinds.add("UNSATISFIED_EXACT_EQUATION")
                    continue
                if stacked and reason.startswith(_STACKED_GLOBAL_EQUATION_PREFIXES):
                    if reason.rsplit(":", 1)[-1] in stacked_specific_periods:
                        continue
                    for (section_id, table_id), selected_rows in rows_by_ref.items():
                        for ordinal, row in enumerate(selected_rows, start=1):
                            values = row.get("values_exact")
                            if type(values) is list and any(value is not None for value in values):
                                target_ids.add(f"{section_id}:{table_id}:r{ordinal}")
                    trigger_kinds.add("UNSATISFIED_EXACT_EQUATION")
                    continue
                invalid = _INVALID_ROW.fullmatch(reason)
                if invalid is not None:
                    ordinal = int(invalid.group(1))
                    if not 1 <= ordinal <= len(rows):
                        raise _error("typed invalid-money row lies outside candidate table")
                    target_ids.add(f"{candidate['section_id']}:{candidate['table_id']}:r{ordinal}")
                    trigger_kinds.add("INVALID_MONEY_CELL")
                    continue
                invalid_percent = _INVALID_PERCENT_ROW.fullmatch(reason)
                if invalid_percent is not None:
                    ordinal = int(invalid_percent.group(1))
                    if not 1 <= ordinal <= len(rows):
                        raise _error("typed invalid-percentage row lies outside candidate table")
                    target_ids.add(f"{candidate['section_id']}:{candidate['table_id']}:r{ordinal}")
                    trigger_kinds.add("INVALID_PERCENT_CELL")
                    continue
                unbound_rows = _UNBOUND_VISIBLE_ROWS.fullmatch(reason)
                if unbound_rows is not None:
                    ordinals = [int(value) for value in unbound_rows.group(1).split(",")]
                    if any(not 1 <= ordinal <= len(rows) for ordinal in ordinals):
                        raise _error("typed unbound row lies outside candidate table")
                    target_ids.update(
                        f"{candidate['section_id']}:{candidate['table_id']}:r{ordinal}"
                        for ordinal in ordinals
                    )
                    trigger_kinds.add("UNMATCHED_SOURCE_LABEL")
                    continue
                invalid_role = _INVALID_ROLE.fullmatch(reason)
                if invalid_role is not None:
                    invalid_roles.add(invalid_role.group(1))
                    trigger_kinds.add("INVALID_MONEY_CELL")
                    continue
                unsatisfied = _UNSATISFIED_RESULT.fullmatch(reason)
                if unsatisfied is not None:
                    result_role = next(value for value in unsatisfied.groups() if value)
                    equation_roles.update(_equation_frontier_roles(compiled_specs, result_role))
                    trigger_kinds.add("UNSATISFIED_EXACT_EQUATION")
            if equation_roles or invalid_roles:
                for (section_id, table_id), selected_rows in rows_by_ref.items():
                    for ordinal, row in enumerate(selected_rows, start=1):
                        roles = (
                            set(
                                _row_roles(
                                    row,
                                    topology=compiled_specs["topology"],
                                    aliases_by_role=aliases_by_role,
                                )
                            )
                            if compiled_specs.get("engine_format_version")
                            == "GEMINI_JSON_HIERARCHICAL_ACCOUNTING_FAMILY_SWEEP_V3"
                            else _label_role(
                                row.get("label_exact"), aliases_by_role=aliases_by_role
                            )
                        )
                        if roles & (equation_roles | invalid_roles):
                            target_ids.add(f"{section_id}:{table_id}:r{ordinal}")
            if table_title_incomplete:
                # Title/header evidence is the prerequisite source boundary.
                # Repair it first; a later family rerun may then emit a
                # separate row/equation job without conflating evidence axes.
                trigger_kinds = {"TABLE_EXPLICIT_FAMILY_TITLE_MISSING"}
                target_ids = {
                    f"{section_id}:{table_id}:r{ordinal}"
                    for (section_id, table_id), selected_rows in rows_by_ref.items()
                    for ordinal in range(1, len(selected_rows) + 1)
                }
            if not target_ids:
                continue
            target_ids = sorted(
                target_ids,
                key=lambda value: tuple(int(part[1:]) for part in value.split(":")),
            )
            material = {
                "acceptance_policy": {
                    "candidate_identity_must_replay": True,
                    "forbid_arithmetic_backsolve": True,
                    "forbid_new_unresolved_reasons": True,
                    "promote_when_targeted_ocr_reason_is_removed": True,
                    "require_candidate_status": ("READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"),
                },
                "base_page_json_version_id": version_id,
                "candidate_id": candidate["candidate_id"],
                "component_table_refs": canonical_clone_v1(component_refs),
                "document_ordinal": trial["document_ordinal"],
                "family_id": checked["family_id"],
                "format_version": FORMAT_VERSION,
                "physical_page": candidate["physical_page"],
                "repair_policy": {
                    "context_radius_by_thinking_level": {"high": 3, "low": 1, "medium": 2},
                    "initial_thinking_level": "low",
                    "max_attempts": 3,
                    "thinking_escalation": ["medium", "high"],
                },
                "repair_contract_version": REPAIR_CONTRACT_VERSION,
                "repair_scope": (
                    "TABLE_TITLE_AND_COLUMNS"
                    if table_title_incomplete
                    else "SECTION_NARRATIVES"
                    if section_narratives_incomplete
                    else "TABLE_PERIOD_AXIS"
                    if period_axis_incomplete
                    else "ROW_LABEL_AND_VALUES"
                    if "UNMATCHED_SOURCE_LABEL" in trigger_kinds
                    else "ROW_VALUES"
                ),
                "section_id": candidate["section_id"],
                "source_logical_name": trial["source_logical_name"],
                "source_sha256": trial["source_sha256"],
                "sweep_id": checked["sweep_id"],
                "table_id": candidate["table_id"],
                "target_table_refs": (
                    canonical_clone_v1(component_refs)
                    if (
                        period_axis_incomplete
                        or table_title_incomplete
                        or section_narratives_incomplete
                    )
                    else []
                ),
                "target_ids": target_ids,
                "trigger_kinds": sorted(trigger_kinds),
                "trigger_reasons": canonical_clone_v1(candidate["reasons"]),
            }
            plans.append(
                {
                    **material,
                    "repair_job_id": "gjfrrqv1:job:" + canonical_json_sha256_v1(material),
                }
            )
    return sorted(plans, key=lambda plan: (plan["document_ordinal"], plan["repair_job_id"]))
