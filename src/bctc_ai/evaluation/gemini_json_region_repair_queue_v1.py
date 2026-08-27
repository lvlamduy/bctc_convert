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
_INVALID_ROW = re.compile(r"^(?:ROW|NESTED_COMPONENT)_MONEY_CELL_IS_NOT_EXACT_INTEGER:(\d+)$")
_INVALID_ROLE = re.compile(r"^ROLE_MONEY_CELL_IS_NOT_EXACT_INTEGER:([^:]+)$")
_UNSATISFIED_RESULT = re.compile(
    r"^(?:EXACT_DIRECT_FRONTIER_SOLUTION_COUNT_NOT_ONE:([^:]+):0"
    r"|NESTED_PARENT_NOT_EXACT_CHILD_SUM:([^:]+))$"
)


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

            row_ordinals = set()
            trigger_kinds = set()
            equation_roles = set()
            invalid_roles = set()
            for reason in candidate["reasons"]:
                invalid = _INVALID_ROW.fullmatch(reason)
                if invalid is not None:
                    ordinal = int(invalid.group(1))
                    if not 1 <= ordinal <= len(rows):
                        raise _error("typed invalid-money row lies outside candidate table")
                    row_ordinals.add(ordinal)
                    trigger_kinds.add("INVALID_MONEY_CELL")
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
                for ordinal, row in enumerate(rows, start=1):
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
                        else _label_role(row.get("label_exact"), aliases_by_role=aliases_by_role)
                    )
                    if roles & (equation_roles | invalid_roles):
                        row_ordinals.add(ordinal)
            if not row_ordinals:
                continue
            target_ids = [
                f"{candidate['section_id']}:{candidate['table_id']}:r{ordinal}"
                for ordinal in sorted(row_ordinals)
            ]
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
                "section_id": candidate["section_id"],
                "source_logical_name": trial["source_logical_name"],
                "source_sha256": trial["source_sha256"],
                "sweep_id": checked["sweep_id"],
                "table_id": candidate["table_id"],
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
