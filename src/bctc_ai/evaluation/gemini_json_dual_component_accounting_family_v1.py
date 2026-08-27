"""Exact two-fragment accounting closure over selected Gemini page JSON.

The primitive is intentionally family-generic.  A declarative policy names two
components, their seed/required/optional row roles, and the visible totals that
close each component independently.  Indexed discovery may join exactly one
seed-bearing fragment from each component, but it never supplies numeric,
period, unit, or schema authority to this evaluator.
"""

from __future__ import annotations

import re
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
    _header_text,
    _matches,
    _money,
    _period_signature,
)
from bctc_ai.evaluation.gemini_json_structural_context_v1 import (
    declared_surface_alias_match_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

ENGINE_FORMAT_VERSION = "GEMINI_JSON_DUAL_COMPONENT_ACCOUNTING_FAMILY_V1"
EVALUATION_FORMAT_VERSION = "ACCOUNTING_DUAL_COMPONENT_FAMILY_EVALUATION_SPEC_V1"
SCHEMA_FORMAT_VERSION = "ACCOUNTING_DUAL_COMPONENT_SCHEMA_BINDING_SPEC_V1"
INDEXED_QUERY_EVIDENCE_FORMAT_VERSION = "GEMINI_JSON_INDEXED_DUAL_COMPONENT_QUERY_EVIDENCE_V1"
READY = "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
NOT_OBSERVED = "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
UNRESOLVED = "UNRESOLVED_GEMINI_JSON_FAMILY"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_INDEXED_EXACT_TWO_SEED_SAME_PAGE_"
    "OWNER_RESET_FENCE_DUAL_INDEPENDENT_VISIBLE_TOTAL_OR_STRUCTURAL_GROSS_"
    "FALLBACK_EXACT_PERIOD_UNIT_SIBLING_INHERITANCE_CONDITIONAL_BLANK_ZERO_"
    "EXHAUSTIVE_SOURCE_INVENTORY_STRUCTURAL_ROOT_SCHEMA_MAPPING_PROPOSAL_"
    "ONLY_NO_GEOMETRY_PPOCR_VIETOCR_BANK_FILE_PAGE_NOTE_ROUTING_BACKSOLVE_"
    "CANONICAL_OR_EXPORT_AUTHORITY"
)

_PAGE_VERSION = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_DOCUMENT_ID = re.compile(r"gfpstorev1:document:[0-9a-f]{64}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SECTION_ID = re.compile(r"s[1-9][0-9]*\Z")
_TABLE_ID = re.compile(r"t[1-9][0-9]*\Z")
_ROW_ID = re.compile(r"r[1-9][0-9]*\Z")
_COMPONENT_ROLES = ("BALANCE", "DETAIL")


class GeminiJsonDualComponentAccountingFamilyV1Error(ValueError):
    """The dual-component policy, source cluster, or replay drifted."""


def _error(message: str) -> GeminiJsonDualComponentAccountingFamilyV1Error:
    return GeminiJsonDualComponentAccountingFamilyV1Error(message)


def _normalized(value: Any) -> str:
    return normalize_vietnamese_anchor_v1(value) if type(value) is str else ""


def _aliases_by_role(topology: Mapping[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
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
            raise _error("dual-component child role has no root-level aliases")
        result[child["role"]] = aliases
    return result


def _compile_components(
    value: Any, *, aliases_by_role: Mapping[str, list[str]]
) -> dict[str, dict[str, Any]]:
    if type(value) is not list or len(value) != 2:
        raise _error("dual-component evaluation needs exactly two component declarations")
    result: dict[str, dict[str, Any]] = {}
    assigned_roles: set[str] = set()
    fields = {
        "component_role",
        "optional_roles",
        "required_roles",
        "seed_role",
        "total_policy",
    }
    for raw in value:
        if (
            type(raw) is not dict
            or set(raw) != fields
            or raw.get("component_role") not in _COMPONENT_ROLES
            or raw["component_role"] in result
            or type(raw.get("required_roles")) is not list
            or not raw["required_roles"]
            or type(raw.get("optional_roles")) is not list
            or len(set(raw["required_roles"] + raw["optional_roles"]))
            != len(raw["required_roles"] + raw["optional_roles"])
            or any(
                role not in aliases_by_role
                for role in raw["required_roles"] + raw["optional_roles"]
            )
            or raw.get("seed_role") not in raw["required_roles"]
            or raw.get("total_policy")
            not in {
                "REQUIRE_EXACTLY_ONE_VISIBLE_TOTAL",
                "VISIBLE_TOTAL_OR_UNIQUE_BALANCE_GROSS_WHEN_ABSENT",
            }
            or (
                raw["component_role"] == "BALANCE"
                and raw["total_policy"] != "REQUIRE_EXACTLY_ONE_VISIBLE_TOTAL"
            )
            or (
                raw["component_role"] == "DETAIL"
                and raw["total_policy"] != "VISIBLE_TOTAL_OR_UNIQUE_BALANCE_GROSS_WHEN_ABSENT"
            )
        ):
            raise _error("dual-component component declaration is invalid")
        roles = set(raw["required_roles"] + raw["optional_roles"])
        if roles & assigned_roles:
            raise _error("dual-component row roles must belong to exactly one component")
        assigned_roles |= roles
        result[raw["component_role"]] = canonical_clone_v1(raw)
    if set(result) != set(_COMPONENT_ROLES) or assigned_roles != set(aliases_by_role):
        raise _error("dual-component declarations do not exhaust topology child roles")
    return result


def _compile_units(value: Any) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if type(value) is not list or not value:
        raise _error("dual-component unit bindings are absent")
    checked = []
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
            raise _error("dual-component unit binding is invalid")
        canonical_units.add(raw["canonical_unit"])
        normalized_aliases = [_normalized(alias) for alias in raw["aliases"]]
        if any(not alias or alias in by_alias for alias in normalized_aliases):
            raise _error("dual-component unit aliases collide")
        binding = {**canonical_clone_v1(raw), "aliases": normalized_aliases}
        for alias in normalized_aliases:
            by_alias[alias] = binding
        checked.append(binding)
    if sum(item["accepted"] for item in checked) != 1:
        raise _error("dual-component policy requires exactly one accepted money unit")
    return checked, by_alias


def compile_gemini_json_dual_component_family_specs_v1(
    topology_spec: Any, evaluation_spec: Any, schema_binding_spec: Any
) -> dict[str, Any]:
    """Compile a strict topology/evaluation/schema triplet."""

    try:
        topology = compile_accounting_family_topology_spec_v1(topology_spec)
    except ValueError as exc:
        raise _error("dual-component topology spec is invalid") from exc
    evaluation_fields = {
        "blank_zero_policy",
        "closure_policy",
        "coalescing_policy",
        "component_specs",
        "family_id",
        "format_version",
        "period_semantics",
        "unit_bindings",
    }
    if (
        type(evaluation_spec) is not dict
        or set(evaluation_spec) != evaluation_fields
        or evaluation_spec.get("format_version") != EVALUATION_FORMAT_VERSION
        or evaluation_spec.get("family_id") != topology["family_id"]
        or evaluation_spec.get("closure_policy") != "EXACT_INDEPENDENT_DUAL_COMPONENT_ALL_LANES"
        or evaluation_spec.get("period_semantics") != "CURRENT_AND_COMPARATIVE_SNAPSHOT"
        or evaluation_spec.get("blank_zero_policy") != "ZERO_ONLY_AFTER_COMPLETE_EQUATION_EXACT"
    ):
        raise _error("dual-component evaluation spec is invalid")
    coalescing = evaluation_spec["coalescing_policy"]
    if (
        type(coalescing) is not dict
        or set(coalescing)
        != {
            "component_order",
            "hard_negative_aliases",
            "max_page_span",
            "owner_aliases",
            "reset_aliases",
        }
        or coalescing.get("component_order") != ["BALANCE", "DETAIL"]
        or coalescing.get("max_page_span") != 0
        or any(
            type(coalescing.get(field)) is not list
            or not coalescing[field]
            or any(type(alias) is not str or not alias.strip() for alias in coalescing[field])
            for field in ("hard_negative_aliases", "owner_aliases", "reset_aliases")
        )
    ):
        raise _error("dual-component coalescing policy is invalid")
    aliases = _aliases_by_role(topology)
    components = _compile_components(evaluation_spec["component_specs"], aliases_by_role=aliases)
    units, units_by_alias = _compile_units(evaluation_spec["unit_bindings"])
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
        raise _error("dual-component schema binding spec is invalid")
    bindings: dict[str, int] = {}
    identities = {schema_binding_spec["family_root_report_norm_id"]}
    for raw in schema_binding_spec["role_bindings"]:
        if (
            type(raw) is not dict
            or set(raw) != {"report_norm_id", "role"}
            or raw.get("role") not in aliases
            or raw["role"] in bindings
            or type(raw.get("report_norm_id")) is not int
            or raw["report_norm_id"] <= 0
            or raw["report_norm_id"] in identities
        ):
            raise _error("dual-component schema role binding is invalid")
        bindings[raw["role"]] = raw["report_norm_id"]
        identities.add(raw["report_norm_id"])
    if set(bindings) != set(aliases):
        raise _error("dual-component schema bindings do not exhaust child roles")
    query_policy = {
        "component_seed_roles": {role: components[role]["seed_role"] for role in _COMPONENT_ROLES},
        "hard_negative_aliases": canonical_clone_v1(coalescing["hard_negative_aliases"]),
        "owner_aliases": canonical_clone_v1(coalescing["owner_aliases"]),
        "reset_aliases": canonical_clone_v1(coalescing["reset_aliases"]),
    }
    return {
        "aliases_by_role": aliases,
        "anchor_alias_groups": [
            [aliases[components[role]["seed_role"]] for role in _COMPONENT_ROLES]
        ],
        "bindings": bindings,
        "claim_boundary": CLAIM_BOUNDARY,
        "components": components,
        "dual_component_projection_policy": query_policy,
        "engine_format_version": ENGINE_FORMAT_VERSION,
        "evaluation": canonical_clone_v1(evaluation_spec),
        "query_anchor_alias_groups": [
            [aliases[components[role]["seed_role"]] for role in _COMPONENT_ROLES]
        ],
        "query_policy": query_policy,
        "schema": canonical_clone_v1(schema_binding_spec),
        "topology": topology,
        "unit_bindings": units,
        "unit_binding_by_alias": units_by_alias,
    }


def _node_index(identifier: Any, prefix: str, limit: int) -> int:
    pattern = _SECTION_ID if prefix == "s" else _TABLE_ID
    if type(identifier) is not str or pattern.fullmatch(identifier) is None:
        raise _error("dual-component source node identity is invalid")
    index = int(identifier[1:]) - 1
    if not 0 <= index < limit:
        raise _error("dual-component source node identity is out of range")
    return index


def _source_table(
    page_json: Mapping[str, Any], *, section_id: str, table_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    sections = page_json.get("sections")
    if type(sections) is not list:
        raise _error("dual-component page has no section axis")
    section = sections[_node_index(section_id, "s", len(sections))]
    tables = section.get("tables") if type(section) is dict else None
    if type(tables) is not list:
        raise _error("dual-component section has no table axis")
    table = tables[_node_index(table_id, "t", len(tables))]
    if type(table) is not dict:
        raise _error("dual-component source table is invalid")
    return section, table


def _roles_for_row(row: Any, *, compiled_specs: Mapping[str, Any]) -> list[str]:
    if type(row) is not dict:
        return []
    label = row.get("label_exact")
    return sorted(
        role
        for role, aliases in compiled_specs["aliases_by_role"].items()
        if any(_matches(label, alias) for alias in aliases)
    )


def classify_gemini_json_dual_component_table_v1(
    table: Any, *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Classify a fragment only from revalidated seed rows in canonical JSON."""

    rows = table.get("rows") if type(table) is dict else None
    if type(rows) is not list:
        raise _error("dual-component table row axis is invalid")
    seed_hits: dict[str, list[str]] = {role: [] for role in _COMPONENT_ROLES}
    seed_roles = {
        role: compiled_specs["components"][role]["seed_role"] for role in _COMPONENT_ROLES
    }
    for ordinal, row in enumerate(rows, start=1):
        roles = _roles_for_row(row, compiled_specs=compiled_specs)
        for component_role, seed_role in seed_roles.items():
            if seed_role in roles:
                seed_hits[component_role].append(f"r{ordinal}")
    present = [role for role in _COMPONENT_ROLES if seed_hits[role]]
    component_role = present[0] if len(present) == 1 and len(seed_hits[present[0]]) == 1 else None
    reasons = []
    if len(present) > 1:
        reasons.append("MIXED_COMPONENT_SEEDS_IN_ONE_FRAGMENT")
    for role in present:
        if len(seed_hits[role]) != 1:
            reasons.append(f"DUPLICATE_{role}_SEED_ROWS")
    return {
        "component_role": component_role,
        "reasons": sorted(reasons),
        "seed_hits": seed_hits,
    }


def _declared_role_population(
    table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    rows = table.get("rows")
    if type(rows) is not list:
        raise _error("dual-component table row axis is invalid")
    role_hits = [
        {"roles": roles, "row_id": f"r{ordinal}"}
        for ordinal, row in enumerate(rows, start=1)
        for roles in [_roles_for_row(row, compiled_specs=compiled_specs)]
        if roles
    ]
    role_row_ids = {item["row_id"] for item in role_hits}
    non_total_row_ids = {
        f"r{ordinal}"
        for ordinal, row in enumerate(rows, start=1)
        if type(row) is dict and row.get("row_kind") != "TOTAL"
    }
    return {
        "population_disposition": (
            "DECLARED_ROLE_ONLY_POPULATION"
            if role_hits and non_total_row_ids <= role_row_ids
            else "INCIDENTAL_ROLE_IN_FOREIGN_POPULATION"
            if role_hits
            else "NO_DECLARED_ROLE"
        ),
        "role_hits": role_hits,
    }


def _surface_marker(
    text: Any, *, compiled_specs: Mapping[str, Any]
) -> tuple[str | None, str | None]:
    policy = compiled_specs["query_policy"]
    owner = declared_surface_alias_match_v1(text, policy["owner_aliases"])
    reset = declared_surface_alias_match_v1(
        text, [*policy["reset_aliases"], *policy["hard_negative_aliases"]]
    )
    if owner is None and reset is None:
        return None, None
    owner_rank = len(_normalized(owner).split()) if owner is not None else -1
    reset_rank = len(_normalized(reset).split()) if reset is not None else -1
    if owner_rank > reset_rank:
        return "OWNER", owner
    return "RESET", reset


def coalesce_gemini_json_dual_component_page_v1(
    *, page_json: Mapping[str, Any], locator: Mapping[str, Any], compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Join exactly one balance and one detail seed below one ordered owner fence."""

    sections = page_json.get("sections")
    if type(sections) is not list:
        raise _error("dual-component candidate page has no section axis")
    current_owner: dict[str, Any] | None = None
    owner_ordinal = 0
    structural_axis = []
    fragments = []
    role_bearing_fragments = []
    nonordering_reset_receipts = []

    def marker(text: Any, source_kind: str, section_id: str, table_id: str | None) -> None:
        nonlocal current_owner, owner_ordinal
        kind, alias = _surface_marker(text, compiled_specs=compiled_specs)
        if kind is None:
            return
        record = {
            "alias": alias,
            "section_id": section_id,
            "source_exact": text,
            "source_kind": source_kind,
            "table_id": table_id,
        }
        structural_axis.append(record)
        if kind == "RESET":
            current_owner = None
        else:
            owner_ordinal += 1
            current_owner = {**record, "owner_ordinal": owner_ordinal}

    for section_ordinal, section in enumerate(sections, start=1):
        if type(section) is not dict:
            raise _error("dual-component page section is invalid")
        section_id = f"s{section_ordinal}"
        marker(section.get("title_exact"), "SECTION_TITLE", section_id, None)
        # Section narratives have no authenticated interleave position relative
        # to tables.  They are retained as evidence but cannot move a fence.
        narratives = section.get("narratives_exact", [])
        if type(narratives) is not list or any(type(item) is not str for item in narratives):
            raise _error("dual-component section narrative axis is invalid")
        narrative_owner_receipts = []
        for narrative_ordinal, narrative in enumerate(narratives, start=1):
            kind, alias = _surface_marker(narrative, compiled_specs=compiled_specs)
            if kind is not None:
                record = {
                    "alias": alias,
                    "narrative_ordinal": narrative_ordinal,
                    "section_id": section_id,
                    "source_exact": narrative,
                    "source_kind": "SECTION_NARRATIVE_NON_ORDERING_EVIDENCE",
                    "table_id": None,
                }
                structural_axis.append(record)
                if kind == "RESET":
                    nonordering_reset_receipts.append(record)
                elif any(
                    _matches(narrative, owner_alias)
                    for owner_alias in compiled_specs["query_policy"]["owner_aliases"]
                ):
                    narrative_owner_receipts.append(record)
        if current_owner is None and len(narrative_owner_receipts) == 1:
            owner_ordinal += 1
            current_owner = {
                **narrative_owner_receipts[0],
                "owner_ordinal": owner_ordinal,
                "source_kind": "SECTION_NARRATIVE_CONTEXT_OWNER",
            }
        tables = section.get("tables", [])
        if type(tables) is not list:
            raise _error("dual-component page table axis is invalid")
        for table_ordinal, table in enumerate(tables, start=1):
            table_id = f"t{table_ordinal}"
            marker(table.get("title_exact"), "TABLE_TITLE", section_id, table_id)
            classification = classify_gemini_json_dual_component_table_v1(
                table, compiled_specs=compiled_specs
            )
            role_population = _declared_role_population(table, compiled_specs=compiled_specs)
            if role_population["role_hits"]:
                role_bearing_fragments.append(
                    {
                        "locator": {
                            **canonical_clone_v1(locator),
                            "section_id": section_id,
                            "table_id": table_id,
                        },
                        "owner": canonical_clone_v1(current_owner),
                        **role_population,
                    }
                )
            if not any(classification["seed_hits"].values()):
                continue
            fragments.append(
                {
                    "classification": classification,
                    "component_role": classification["component_role"],
                    "locator": {
                        **canonical_clone_v1(locator),
                        "section_id": section_id,
                        "table_id": table_id,
                    },
                    "owner": canonical_clone_v1(current_owner),
                }
            )
    reasons = [reason for item in fragments for reason in item["classification"]["reasons"]]
    if len(fragments) != 2:
        reasons.append("EXACTLY_TWO_SEED_BEARING_FRAGMENTS_REQUIRED")
    by_component = {
        role: [item for item in fragments if item["component_role"] == role]
        for role in _COMPONENT_ROLES
    }
    for role in _COMPONENT_ROLES:
        if len(by_component[role]) != 1:
            reasons.append(f"EXACTLY_ONE_{role}_FRAGMENT_REQUIRED")
    component_regions = []
    owner = None
    if not reasons:
        balance = by_component["BALANCE"][0]
        detail = by_component["DETAIL"][0]
        balance_owner = balance["owner"]
        detail_owner = detail["owner"]
        if balance_owner is None and detail_owner is None:
            reasons.append("EXPLICIT_OWNER_FENCE_REQUIRED")
        elif balance_owner is None or detail_owner is None or balance_owner != detail_owner:
            reasons.append("COMPONENT_FRAGMENTS_CROSS_OWNER_OR_RESET_FENCE")
        elif (
            int(balance["locator"]["section_id"][1:]),
            int(balance["locator"]["table_id"][1:]),
        ) >= (
            int(detail["locator"]["section_id"][1:]),
            int(detail["locator"]["table_id"][1:]),
        ):
            reasons.append("BALANCE_FRAGMENT_MUST_PRECEDE_DETAIL_FRAGMENT")
        else:
            owner = balance_owner
            component_regions = [balance["locator"], detail["locator"]]
            consumed_locations = {
                (item["section_id"], item["table_id"]) for item in component_regions
            }
            if any(
                item["owner"] == owner
                and item["population_disposition"] == "DECLARED_ROLE_ONLY_POPULATION"
                and (item["locator"]["section_id"], item["locator"]["table_id"])
                not in consumed_locations
                for item in role_bearing_fragments
            ):
                reasons.append("UNCONSUMED_ROLE_BEARING_FRAGMENT_UNDER_OWNER_FENCE")
            first_section = int(component_regions[0]["section_id"][1:])
            last_section = int(component_regions[1]["section_id"][1:])
            if any(
                first_section <= int(receipt["section_id"][1:]) <= last_section
                for receipt in nonordering_reset_receipts
            ):
                reasons.append("NONORDERABLE_NARRATIVE_RESET_OR_HARD_NEGATIVE_IN_INTERVAL")
    return {
        "component_regions": component_regions if not reasons else [],
        "fragments": fragments,
        "owner": owner if not reasons else None,
        "role_bearing_fragments": role_bearing_fragments,
        "reasons": sorted(set(reasons)),
        "status": "ACCEPTED" if not reasons else "UNRESOLVED",
        "structural_axis": structural_axis,
    }


def build_gemini_json_dual_component_region_query_receipt_v1(
    regions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Bind one candidate to its exact ordered source fragments."""

    checked = _region_axis(regions)
    first = checked[0]
    material = {
        "document_id": first["document_id"],
        "exact_fragment_count": len(checked),
        "format_version": "GEMINI_JSON_DUAL_COMPONENT_REGION_QUERY_RECEIPT_V1",
        "ordered_fragment_axis_sha256": canonical_json_sha256_v1(checked),
        "source_logical_name": first["source_logical_name"],
        "source_sha256": first["source_sha256"],
    }
    return {
        **material,
        "query_receipt_id": "gjfdcrqrv1:receipt:" + canonical_json_sha256_v1(material),
    }


def _region_axis(regions: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    fields = {
        "document_id",
        "document_ordinal",
        "page_json_version_id",
        "physical_page",
        "selected_page_ordinal",
        "section_id",
        "source_logical_name",
        "source_sha256",
        "table_id",
    }
    if type(regions) not in {list, tuple} or len(regions) != 2:
        raise _error("dual-component region axis must contain exactly two fragments")
    result = []
    first_identity = None
    for region in regions:
        if (
            type(region) is not dict
            or set(region) != fields
            or _DOCUMENT_ID.fullmatch(region.get("document_id", "")) is None
            or type(region.get("document_ordinal")) is not int
            or region["document_ordinal"] <= 0
            or _PAGE_VERSION.fullmatch(region.get("page_json_version_id", "")) is None
            or type(region.get("physical_page")) is not int
            or region["physical_page"] <= 0
            or type(region.get("selected_page_ordinal")) is not int
            or region["selected_page_ordinal"] <= 0
            or _SECTION_ID.fullmatch(region.get("section_id", "")) is None
            or type(region.get("source_logical_name")) is not str
            or not region["source_logical_name"]
            or _SHA256.fullmatch(region.get("source_sha256", "")) is None
            or _TABLE_ID.fullmatch(region.get("table_id", "")) is None
        ):
            raise _error("dual-component source region is invalid")
        identity = tuple(
            region[key]
            for key in (
                "document_id",
                "document_ordinal",
                "page_json_version_id",
                "physical_page",
                "selected_page_ordinal",
                "source_logical_name",
                "source_sha256",
            )
        )
        if first_identity is None:
            first_identity = identity
        elif identity != first_identity:
            raise _error("dual-component fragments are not exact same-page siblings")
        result.append(canonical_clone_v1(region))
    if (
        int(result[0]["section_id"][1:]),
        int(result[0]["table_id"][1:]),
    ) >= (
        int(result[1]["section_id"][1:]),
        int(result[1]["table_id"][1:]),
    ):
        raise _error("dual-component region axis is not in structural source order")
    return result


def _period_axis(table: Mapping[str, Any]) -> dict[str, Any]:
    columns = table.get("columns")
    if (
        type(columns) is not list
        or len(columns) != 2
        or any(
            type(column) is not dict or column.get("value_kind") != "MONEY" for column in columns
        )
    ):
        return {
            "complete": False,
            "partial": False,
            "reasons": ["EXACTLY_TWO_MONEY_COLUMNS_REQUIRED"],
        }
    headers = [_header_text(column) for column in columns]
    signatures = [_period_signature(header) for header in headers]
    present = sum(signature is not None for signature in signatures)
    reasons = []
    if present == 1:
        reasons.append("PARTIAL_PERIOD_AXIS_CANNOT_INHERIT")
    if present == 2:
        first, second = signatures
        assert first is not None and second is not None
        if first[0] != second[0]:
            reasons.append("PERIOD_SIGNATURE_KINDS_DIFFER")
        elif first == ("SEMANTIC_ALIAS", "CURRENT_PERIOD") and second == (
            "SEMANTIC_ALIAS",
            "COMPARATIVE_PERIOD",
        ):
            pass
        elif first[0] == "SEMANTIC_ALIAS":
            reasons.append("SEMANTIC_PERIOD_AXIS_ORDER_IS_NOT_CURRENT_COMPARATIVE")
        else:
            current = date.fromisoformat(first[1])
            comparative = date.fromisoformat(second[1])
            if not current > comparative:
                reasons.append("DATE_PERIOD_AXIS_IS_NOT_STRICT_CURRENT_THEN_COMPARATIVE")
    return {
        "complete": present == 2 and not reasons,
        "headers_exact": headers,
        "partial": present == 1,
        "reasons": reasons,
        "signatures": [
            list(signature) if signature is not None else None for signature in signatures
        ],
        "source": "LOCAL_COLUMN_HEADERS" if present else None,
    }


def _unit_axis(table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]) -> dict[str, Any]:
    recognized_aliases = list(compiled_specs["unit_binding_by_alias"])
    evidence: list[dict[str, Any]] = []
    undeclared: list[dict[str, Any]] = []

    def classify(surface: dict[str, Any], *, explicit_unit_slot: bool) -> dict[str, Any] | None:
        matched = declared_surface_alias_match_v1(surface["text_exact"], recognized_aliases)
        if matched is not None:
            binding = compiled_specs["unit_binding_by_alias"][_normalized(matched)]
            record = {
                **surface,
                "accepted": binding["accepted"],
                "canonical_unit": binding["canonical_unit"],
                "matched_alias": matched,
                "magnitude_power10": binding["magnitude_power10"],
            }
            evidence.append(record)
            return record
        if explicit_unit_slot or re.search(
            r"\b(?:dong|vnd|usd|trieu|nghin|ty)\b", _normalized(surface["text_exact"])
        ):
            undeclared.append(surface)
        return None

    table_record = None
    unit_exact = table.get("unit_exact")
    if type(unit_exact) is str and unit_exact.strip():
        table_record = classify(
            {"source_kind": "TABLE_UNIT", "text_exact": unit_exact},
            explicit_unit_slot=True,
        )
    columns = table.get("columns")
    column_records = []
    if type(columns) is list:
        for ordinal, column in enumerate(columns, start=1):
            header = _header_text(column)
            record = (
                classify(
                    {"source_kind": f"COLUMN_HEADER:c{ordinal}", "text_exact": header},
                    explicit_unit_slot=False,
                )
                if header
                else None
            )
            column_records.append(record)
    reasons = []
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
    elif any(item is not None for item in column_records):
        if (
            len(column_records) != 2
            or any(item is None for item in column_records)
            or any(not item["accepted"] for item in column_records if item is not None)
        ):
            reasons.append("MONEY_COLUMN_UNITS_ARE_NOT_UNIFORMLY_EXPLICIT")
        else:
            column_units = {item["canonical_unit"] for item in column_records if item is not None}
            if len(column_units) != 1:
                reasons.append("CONFLICTING_EXPLICIT_MONEY_UNITS")
            else:
                canonical_unit = next(iter(column_units))
                source = "LOCAL_UNIFORM_ALL_MONEY_COLUMN_UNITS"
    return {
        "canonical_unit": canonical_unit,
        "complete": canonical_unit is not None and not reasons,
        "evidence": evidence,
        "reasons": reasons,
        "source": source,
        "undeclared_evidence": undeclared,
    }


def _resolve_sibling_axes(
    tables: Mapping[str, Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    axes = {
        role: {
            "period": _period_axis(tables[role]),
            "unit": _unit_axis(tables[role], compiled_specs=compiled_specs),
        }
        for role in _COMPONENT_ROLES
    }
    reasons = []
    for role in _COMPONENT_ROLES:
        reasons.extend(f"{role}:{reason}" for reason in axes[role]["period"]["reasons"])
        reasons.extend(f"{role}:{reason}" for reason in axes[role]["unit"]["reasons"])
    for axis_name in ("period", "unit"):
        first = axes["BALANCE"][axis_name]
        second = axes["DETAIL"][axis_name]
        if first["complete"] and second["complete"]:
            key = "signatures" if axis_name == "period" else "canonical_unit"
            if first[key] != second[key]:
                reasons.append(f"EXPLICIT_SIBLING_{axis_name.upper()}_AXES_DIFFER")
            continue
        if first["complete"] == second["complete"]:
            reasons.append(f"EXACT_SIBLING_{axis_name.upper()}_INHERITANCE_UNAVAILABLE")
            continue
        source_role, target_role = (
            ("BALANCE", "DETAIL") if first["complete"] else ("DETAIL", "BALANCE")
        )
        target = axes[target_role][axis_name]
        if axis_name == "period" and target.get("partial"):
            reasons.append("PARTIAL_PERIOD_AXIS_CANNOT_INHERIT")
            continue
        if axis_name == "unit" and (target["evidence"] or target["undeclared_evidence"]):
            reasons.append("EXPLICIT_UNIT_EVIDENCE_CANNOT_BE_REPLACED_BY_INHERITANCE")
            continue
        inherited = canonical_clone_v1(axes[source_role][axis_name])
        inherited["source"] = f"EXACT_SAME_PAGE_{source_role}_SIBLING_INHERITANCE"
        inherited["inherited_from_component_role"] = source_role
        axes[target_role][axis_name] = inherited
    return axes, sorted(set(reasons))


def _component_rows(
    *, component_role: str, table: Mapping[str, Any], compiled_specs: Mapping[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[str, Any] | None, list[dict[str, Any]], list[str]]:
    spec = compiled_specs["components"][component_role]
    allowed = set(spec["required_roles"] + spec["optional_roles"])
    rows = table.get("rows")
    columns = table.get("columns")
    if type(rows) is not list or type(columns) is not list or len(columns) != 2:
        raise _error("dual-component table axes are invalid")
    by_role: dict[str, dict[str, Any]] = {}
    totals = []
    inventory = []
    reasons = []
    for ordinal, row in enumerate(rows, start=1):
        if (
            type(row) is not dict
            or type(row.get("values_exact")) is not list
            or len(row["values_exact"]) != 2
            or type(row.get("hierarchy_path_exact")) is not list
        ):
            reasons.append("SOURCE_ROW_AXIS_OR_TWO_CELL_VECTOR_INVALID")
            continue
        roles = _roles_for_row(row, compiled_specs=compiled_specs)
        matched = [role for role in roles if role in allowed]
        foreign = [role for role in roles if role not in allowed]
        row_id = f"r{ordinal}"
        disposition = "UNCLASSIFIED_NUMERIC_ROW"
        if row.get("row_kind") == "TOTAL":
            totals.append({"ordinal": ordinal, "row": row, "row_id": row_id})
            disposition = "COMPONENT_RESULT_TOTAL"
        elif len(matched) == 1 and not foreign:
            role = matched[0]
            disposition = "MAPPED_COMPONENT_ROLE"
            if totals:
                reasons.append(f"COMPONENT_ROLE_AFTER_VISIBLE_TOTAL:{role}")
            if role in by_role:
                reasons.append(f"DUPLICATE_COMPONENT_ROLE:{role}")
            else:
                try:
                    cells = [_money(value) for value in row["values_exact"]]
                except ValueError:
                    reasons.append(f"MONEY_CELL_INVALID:{role}")
                    cells = []
                by_role[role] = {
                    "cells": cells,
                    "ordinal": ordinal,
                    "row": row,
                    "row_id": row_id,
                }
        elif roles:
            reasons.append("ROLE_BEARING_ROW_BELONGS_TO_OTHER_OR_MULTIPLE_COMPONENTS")
        # Every source row in a seed-bearing fragment is numeric by contract.
        if disposition == "UNCLASSIFIED_NUMERIC_ROW":
            reasons.append(f"UNMAPPED_NUMERIC_SOURCE_ROW:{row_id}")
        inventory.append(
            {
                "disposition": disposition,
                "hierarchy_path_exact": canonical_clone_v1(row["hierarchy_path_exact"]),
                "label_exact": row.get("label_exact"),
                "matched_roles": roles,
                "row_ordinal": ordinal,
                "row_id": row_id,
                "row_kind": row.get("row_kind"),
                "values_exact": canonical_clone_v1(row["values_exact"]),
            }
        )
    for role in spec["required_roles"]:
        if role not in by_role:
            reasons.append(f"REQUIRED_COMPONENT_ROLE_ABSENT:{role}")
    if len(totals) > 1:
        reasons.append("DUPLICATE_VISIBLE_COMPONENT_TOTAL")
    total = totals[0] if len(totals) == 1 else None
    if total is not None and any(
        record["ordinal"] > total["ordinal"] for record in by_role.values()
    ):
        reasons.append("VISIBLE_TOTAL_DOES_NOT_TRAIL_ALL_COMPONENT_ROLES")
    if total is not None:
        try:
            total["cells"] = [_money(value) for value in total["row"]["values_exact"]]
        except ValueError:
            reasons.append("VISIBLE_COMPONENT_TOTAL_MONEY_CELL_INVALID")
    if component_role == "BALANCE" and total is None:
        reasons.append("BALANCE_VISIBLE_TOTAL_REQUIRED")
    return by_role, total, inventory, sorted(set(reasons))


def _upgrade_blank_cells(records: Sequence[dict[str, Any]]) -> None:
    for record in records:
        for cell in record.get("cells", []):
            if cell.get("state") == "BLANK_ZERO_IF_EQUATION_EXACT":
                cell["state"] = "INFERRED_BLANK_ZERO_EQUATION_EXACT"


def evaluate_gemini_json_dual_component_family_cluster_v1(
    *,
    regions: Sequence[dict[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate independent balance/detail closures and emit child mappings only."""

    region_axis = _region_axis(regions)
    expected_receipt = build_gemini_json_dual_component_region_query_receipt_v1(region_axis)
    if type(query_receipt) is not dict or not same_typed_json_v1(query_receipt, expected_receipt):
        raise _error("dual-component query receipt does not bind the exact fragments")
    first = region_axis[0]
    page_json = page_json_by_version.get(first["page_json_version_id"])
    if type(page_json) is not dict:
        raise _error("dual-component selected page JSON is absent")
    sections_and_tables = [
        _source_table(page_json, section_id=item["section_id"], table_id=item["table_id"])
        for item in region_axis
    ]
    tables = dict(zip(_COMPONENT_ROLES, (pair[1] for pair in sections_and_tables), strict=True))
    reasons = []
    for role in _COMPONENT_ROLES:
        classification = classify_gemini_json_dual_component_table_v1(
            tables[role], compiled_specs=compiled_specs
        )
        if classification["component_role"] != role or classification["reasons"]:
            reasons.append(f"{role}_FRAGMENT_SEED_CLASSIFICATION_DRIFTED")
    axes, axis_reasons = _resolve_sibling_axes(tables, compiled_specs=compiled_specs)
    reasons.extend(axis_reasons)
    rows_by_component = {}
    total_by_component = {}
    source_inventory = []
    for component_role, region in zip(_COMPONENT_ROLES, region_axis, strict=True):
        by_role, total, inventory, component_reasons = _component_rows(
            component_role=component_role,
            table=tables[component_role],
            compiled_specs=compiled_specs,
        )
        rows_by_component[component_role] = by_role
        total_by_component[component_role] = total
        reasons.extend(f"{component_role}:{reason}" for reason in component_reasons)
        source_inventory.append(
            {
                "column_axis": [
                    {
                        "column_id": f"c{ordinal}",
                        "header_path_exact": canonical_clone_v1(column.get("header_path_exact")),
                        "value_kind": column.get("value_kind"),
                    }
                    for ordinal, column in enumerate(tables[component_role].get("columns", []), 1)
                ],
                "component_role": component_role,
                "locator": canonical_clone_v1(region),
                "row_axis": inventory,
            }
        )
    equations = []
    exact = not reasons
    fallback_used = False
    all_cell_records = [
        record for by_role in rows_by_component.values() for record in by_role.values()
    ] + [record for record in total_by_component.values() if record is not None]
    for component_role in _COMPONENT_ROLES:
        spec = compiled_specs["components"][component_role]
        by_role = rows_by_component[component_role]
        result = total_by_component[component_role]
        result_kind = "VISIBLE_COMPONENT_TOTAL"
        if component_role == "DETAIL" and result is None:
            # Structural gross fallback is deliberately narrow: the detail has
            # its principal seed, no visible total, and the unique balance VND
            # seed supplies the gross result.  A visible detail total always
            # wins and is never compared to the balance gross amount.
            balance_seed = compiled_specs["components"]["BALANCE"]["seed_role"]
            detail_optional_present = set(spec["optional_roles"]) & set(by_role)
            balance_optional_present = set(
                compiled_specs["components"]["BALANCE"]["optional_roles"]
            ) & set(rows_by_component["BALANCE"])
            if (
                spec["seed_role"] in by_role
                and not detail_optional_present
                and not balance_optional_present
                and balance_seed in rows_by_component["BALANCE"]
            ):
                result = rows_by_component["BALANCE"][balance_seed]
                result_kind = "UNIQUE_BALANCE_GROSS_STRUCTURAL_FALLBACK"
                fallback_used = True
            else:
                reasons.append("DETAIL_VISIBLE_TOTAL_ABSENT_AND_GROSS_FALLBACK_NOT_STRUCTURAL")
                exact = False
        if result is None or any(not record.get("cells") for record in by_role.values()):
            exact = False
            continue
        component_roles = [
            role for role in spec["required_roles"] + spec["optional_roles"] if role in by_role
        ]
        for lane_index, period_role in enumerate(("CURRENT_PERIOD", "COMPARATIVE_PERIOD")):
            component_sum = sum(
                by_role[role]["cells"][lane_index]["coefficient"] for role in component_roles
            )
            result_coefficient = result["cells"][lane_index]["coefficient"]
            status = "EXACT" if component_sum == result_coefficient else "MISMATCH"
            if status != "EXACT":
                reasons.append(f"{component_role}_LANE_EQUATION_MISMATCH:{period_role}")
                exact = False
            material = {
                "component_role": component_role,
                "component_role_coefficients": [
                    {
                        "coefficient": by_role[role]["cells"][lane_index]["coefficient"],
                        "role": role,
                        "row_id": by_role[role]["row_id"],
                        "row_ordinal": by_role[role]["ordinal"],
                        "source_text": by_role[role]["cells"][lane_index]["source_text"],
                        "state": by_role[role]["cells"][lane_index]["state"],
                    }
                    for role in component_roles
                ],
                "component_sum": component_sum,
                "period_role": period_role,
                "result_coefficient": result_coefficient,
                "result_kind": result_kind,
                "result_row_ordinal": result["ordinal"],
                "result_row_id": result["row_id"],
                "result_source_text": result["cells"][lane_index]["source_text"],
                "status": status,
            }
            equations.append(
                {
                    **material,
                    "equation_id": "gjfdcev1:equation:" + canonical_json_sha256_v1(material),
                }
            )
    reasons = sorted(set(reasons))
    if exact and not reasons and len(equations) == 4:
        _upgrade_blank_cells(all_cell_records)
        # Equation states are rebuilt after blank-zero promotion so persisted
        # receipts cannot claim provisional blanks once closure is exact.
        for equation in equations:
            component_role = equation["component_role"]
            lane_index = 0 if equation["period_role"] == "CURRENT_PERIOD" else 1
            for item in equation["component_role_coefficients"]:
                item["state"] = rows_by_component[component_role][item["role"]]["cells"][
                    lane_index
                ]["state"]
            material = {key: value for key, value in equation.items() if key != "equation_id"}
            equation["equation_id"] = "gjfdcev1:equation:" + canonical_json_sha256_v1(material)
    else:
        exact = False
    mappings = []
    if exact:
        role_order = [raw["role"] for raw in compiled_specs["schema"]["role_bindings"]]
        component_by_role = {
            role: component_role
            for component_role in _COMPONENT_ROLES
            for role in compiled_specs["components"][component_role]["required_roles"]
            + compiled_specs["components"][component_role]["optional_roles"]
        }
        locator_by_component = dict(zip(_COMPONENT_ROLES, region_axis, strict=True))
        for role in role_order:
            component_role = component_by_role[role]
            record = rows_by_component[component_role].get(role)
            if record is None:
                continue
            row = record["row"]
            material = {
                "component_role": component_role,
                "hierarchy_path_exact": canonical_clone_v1(row["hierarchy_path_exact"]),
                "label_exact": row.get("label_exact"),
                "locator": canonical_clone_v1(locator_by_component[component_role]),
                "period_provenance": canonical_clone_v1(axes[component_role]["period"]),
                "report_norm_id": compiled_specs["bindings"][role],
                "role": role,
                "row_id": record["row_id"],
                "row_ordinal": record["ordinal"],
                "unit_provenance": canonical_clone_v1(axes[component_role]["unit"]),
                "values": canonical_clone_v1(record["cells"]),
            }
            mappings.append(
                {
                    **material,
                    "item_mapping_id": "gjfdcmv1:item:" + canonical_json_sha256_v1(material),
                }
            )
    structural_root_receipt = {
        "emitted_mapping": False,
        "mapping_policy": "STRUCTURAL_CONTEXT_ONLY",
        "report_norm_id": compiled_specs["schema"]["family_root_report_norm_id"],
        "role": compiled_specs["topology"]["parent"]["role"],
    }
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "closure_receipt": {
            "axes_by_component": axes,
            "equations": equations,
            "fallback_used": fallback_used,
            "query_receipt": canonical_clone_v1(expected_receipt),
            "rule": "EXACT_INDEPENDENT_DUAL_COMPONENT_ALL_LANES",
            "source_inventory": source_inventory,
            "structural_root_receipt": structural_root_receipt,
        },
        "component_regions": region_axis,
        "component_table_refs": [
            {"section_id": item["section_id"], "table_id": item["table_id"]} for item in region_axis
        ],
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
        "candidate_id": "gjfafcv1:candidate:" + canonical_json_sha256_v1(material),
        **material,
    }


def validate_gemini_json_dual_component_family_candidate_replay_v1(
    value: Any,
    *,
    regions: Sequence[dict[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild and exact-compare a candidate, including all source receipts."""

    rebuilt = evaluate_gemini_json_dual_component_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if type(value) is not dict or not same_typed_json_v1(value, rebuilt):
        raise _error("dual-component family candidate does not replay exactly")
    return rebuilt


def build_gemini_json_indexed_dual_component_query_evidence_v1(
    *,
    selected_document_axis: Sequence[dict[str, Any]],
    indexed_role_hits: Sequence[dict[str, Any]],
    indexed_seed_hits: Sequence[dict[str, Any]],
    accepted_clusters: Sequence[dict[str, Any]],
    candidate_dispositions: Sequence[dict[str, Any]],
    selected_page_json_version_ids: Sequence[str],
    query_policy_sha256: str,
) -> dict[str, Any]:
    """Seal the exhaustive indexed document disposition and accepted clusters."""

    selected_documents = canonical_clone_v1(list(selected_document_axis))
    role_hits = canonical_clone_v1(list(indexed_role_hits))
    seed_hits = canonical_clone_v1(list(indexed_seed_hits))
    clusters = canonical_clone_v1(list(accepted_clusters))
    dispositions = canonical_clone_v1(list(candidate_dispositions))
    counts = {
        kind: sum(item.get("disposition") == kind for item in dispositions)
        for kind in ("ACCEPTED_CLUSTER", "NOT_OBSERVED", "UNRESOLVED_CLUSTER")
    }
    receipt = {
        "accepted_cluster_count": len(clusters),
        "accepted_fragment_count": sum(len(item.get("component_regions", [])) for item in clusters),
        "candidate_disposition_count": len(dispositions),
        "decoded_candidate_page_count": len(
            {item.get("page_json_version_id") for item in role_hits}
        ),
        "disposition_counts": counts,
        "indexed_seed_hit_count": len(seed_hits),
        "indexed_role_hit_count": len(role_hits),
        "query_policy_sha256": query_policy_sha256,
        "selected_document_count": len(selected_documents),
        "selected_document_axis_sha256": canonical_json_sha256_v1(selected_documents),
        "selected_page_count": len(selected_page_json_version_ids),
        "selected_page_json_frontier_sha256": canonical_json_sha256_v1(
            list(selected_page_json_version_ids)
        ),
        "accepted_cluster_axis_sha256": canonical_json_sha256_v1(clusters),
        "indexed_seed_hit_axis_sha256": canonical_json_sha256_v1(seed_hits),
        "indexed_role_hit_axis_sha256": canonical_json_sha256_v1(role_hits),
        "candidate_disposition_axis_sha256": canonical_json_sha256_v1(dispositions),
    }
    material = {
        "accepted_clusters": clusters,
        "candidate_dispositions": dispositions,
        "format_version": INDEXED_QUERY_EVIDENCE_FORMAT_VERSION,
        "indexed_role_hits": role_hits,
        "indexed_seed_hits": seed_hits,
        "query_receipt": receipt,
        "selected_document_axis": selected_documents,
    }
    return {
        **material,
        "query_evidence_id": "gjfidcqev1:evidence:" + canonical_json_sha256_v1(material),
    }


def validate_gemini_json_indexed_dual_component_query_evidence_v1(
    value: Any, *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Replay every content hash and exhaustive document disposition."""

    fields = {
        "accepted_clusters",
        "candidate_dispositions",
        "format_version",
        "indexed_role_hits",
        "indexed_seed_hits",
        "query_evidence_id",
        "query_receipt",
        "selected_document_axis",
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
                "indexed_role_hits",
                "indexed_seed_hits",
                "selected_document_axis",
            )
        )
        or type(value.get("query_receipt")) is not dict
    ):
        raise _error("indexed dual-component query evidence is invalid")
    documents = value["selected_document_axis"]
    dispositions = value["candidate_dispositions"]
    if len(documents) != len(dispositions) or not documents:
        raise _error("indexed dual-component document disposition axis is incomplete")
    document_fields = {
        "document_id",
        "document_ordinal",
        "source_logical_name",
        "source_sha256",
    }
    disposition_fields = document_fields | {
        "disposition",
        "indexed_role_hit_count",
        "indexed_role_hit_receipts",
        "reason_codes",
    }
    for ordinal, (document, disposition) in enumerate(zip(documents, dispositions, strict=True), 1):
        if (
            type(document) is not dict
            or set(document) != document_fields
            or document.get("document_ordinal") != ordinal
            or _DOCUMENT_ID.fullmatch(document.get("document_id", "")) is None
            or type(document.get("source_logical_name")) is not str
            or not document["source_logical_name"]
            or _SHA256.fullmatch(document.get("source_sha256", "")) is None
            or type(disposition) is not dict
            or set(disposition) != disposition_fields
            or disposition.get("document_ordinal") != ordinal
            or disposition.get("document_id") != document["document_id"]
            or disposition.get("source_logical_name") != document["source_logical_name"]
            or disposition.get("source_sha256") != document["source_sha256"]
            or disposition.get("disposition")
            not in {"ACCEPTED_CLUSTER", "NOT_OBSERVED", "UNRESOLVED_CLUSTER"}
        ):
            raise _error("indexed dual-component document axis is invalid")
    document_by_ordinal = {item["document_ordinal"]: item for item in documents}
    role_hit_fields = {
        "component_role",
        "document_id",
        "document_ordinal",
        "is_seed",
        "label_exact",
        "page_json_version_id",
        "physical_page",
        "query_disposition",
        "role",
        "row_id",
        "section_id",
        "selected_page_ordinal",
        "source_logical_name",
        "source_order",
        "source_sha256",
        "table_id",
    }
    component_by_role = {
        role: component_role
        for component_role in _COMPONENT_ROLES
        for role in compiled_specs["components"][component_role]["required_roles"]
        + compiled_specs["components"][component_role]["optional_roles"]
    }
    seed_roles = {
        compiled_specs["components"][component_role]["seed_role"]
        for component_role in _COMPONENT_ROLES
    }
    hit_order = []
    for hit in value["indexed_role_hits"]:
        document = (
            document_by_ordinal.get(hit.get("document_ordinal")) if type(hit) is dict else None
        )
        if (
            type(hit) is not dict
            or set(hit) != role_hit_fields
            or document is None
            or hit.get("document_id") != document["document_id"]
            or hit.get("source_logical_name") != document["source_logical_name"]
            or hit.get("source_sha256") != document["source_sha256"]
            or hit.get("component_role") not in _COMPONENT_ROLES
            or hit.get("role") not in component_by_role
            or component_by_role[hit["role"]] != hit["component_role"]
            or type(hit.get("is_seed")) is not bool
            or hit["is_seed"] != (hit["role"] in seed_roles)
            or type(hit.get("label_exact")) is not str
            or not hit["label_exact"]
            or _PAGE_VERSION.fullmatch(hit.get("page_json_version_id", "")) is None
            or type(hit.get("physical_page")) is not int
            or hit["physical_page"] <= 0
            or _ROW_ID.fullmatch(hit.get("row_id", "")) is None
            or _SECTION_ID.fullmatch(hit.get("section_id", "")) is None
            or _TABLE_ID.fullmatch(hit.get("table_id", "")) is None
            or type(hit.get("selected_page_ordinal")) is not int
            or hit["selected_page_ordinal"] <= 0
            or type(hit.get("source_order")) is not int
            or hit["source_order"] < 0
            or hit.get("query_disposition")
            not in {
                "CONSUMED_ACCEPTED_COMPONENT_FRAGMENT",
                "INCIDENTAL_ROLE_IN_FOREIGN_POPULATION",
                "OUTSIDE_DECLARED_OWNER_FENCE",
                "UNCONSUMED_FAMILY_INTERVAL_ROLE_HIT",
            }
        ):
            raise _error("indexed dual-component role-hit inventory is invalid")
        hit_order.append(
            (
                hit["selected_page_ordinal"],
                int(hit["section_id"][1:]),
                int(hit["table_id"][1:]),
                hit["source_order"],
                hit["row_id"],
                hit["component_role"],
                hit["role"],
            )
        )
    if hit_order != sorted(hit_order) or len(hit_order) != len(set(hit_order)):
        raise _error("indexed dual-component role-hit inventory is repeated or unordered")
    expected_seed_hits = [
        canonical_clone_v1(hit) for hit in value["indexed_role_hits"] if hit["is_seed"]
    ]
    if not same_typed_json_v1(value["indexed_seed_hits"], expected_seed_hits):
        raise _error("indexed dual-component seed-hit projection drifted")
    hit_receipt_fields = {
        "component_role",
        "is_seed",
        "page_json_version_id",
        "query_disposition",
        "role",
        "row_id",
        "section_id",
        "table_id",
    }
    active_dispositions = {
        "CONSUMED_ACCEPTED_COMPONENT_FRAGMENT",
        "UNCONSUMED_FAMILY_INTERVAL_ROLE_HIT",
    }
    for disposition in dispositions:
        active_hits = [
            hit
            for hit in value["indexed_role_hits"]
            if hit["document_ordinal"] == disposition["document_ordinal"]
            and hit["query_disposition"] in active_dispositions
        ]
        expected_hit_receipts = [
            {key: canonical_clone_v1(hit[key]) for key in hit_receipt_fields} for hit in active_hits
        ]
        reasons = disposition["reason_codes"]
        if (
            type(disposition["indexed_role_hit_count"]) is not int
            or disposition["indexed_role_hit_count"] != len(active_hits)
            or not same_typed_json_v1(
                disposition["indexed_role_hit_receipts"], expected_hit_receipts
            )
            or type(reasons) is not list
            or reasons != sorted(set(reasons))
            or any(type(reason) is not str or not reason for reason in reasons)
        ):
            raise _error("indexed dual-component disposition hit receipt drifted")
        kind = disposition["disposition"]
        if (
            (
                kind == "ACCEPTED_CLUSTER"
                and (
                    not active_hits
                    or reasons
                    or any(
                        hit["query_disposition"] != "CONSUMED_ACCEPTED_COMPONENT_FRAGMENT"
                        for hit in active_hits
                    )
                )
            )
            or (kind == "NOT_OBSERVED" and (active_hits or reasons))
            or (kind == "UNRESOLVED_CLUSTER" and (not active_hits or not reasons))
        ):
            raise _error("indexed dual-component disposition semantics drifted")
    clusters = value["accepted_clusters"]
    accepted_ordinals = {
        item["document_ordinal"]
        for item in dispositions
        if item["disposition"] == "ACCEPTED_CLUSTER"
    }
    if len(clusters) != len(accepted_ordinals) or [
        item.get("document_ordinal") for item in clusters
    ] != sorted(accepted_ordinals):
        raise _error("indexed dual-component accepted cluster axis is incomplete")
    owner_fields = {
        "alias",
        "owner_ordinal",
        "section_id",
        "source_exact",
        "source_kind",
        "table_id",
    }
    narrative_owner_fields = owner_fields | {"narrative_ordinal"}
    for cluster in clusters:
        document = (
            document_by_ordinal.get(cluster.get("document_ordinal"))
            if type(cluster) is dict
            else None
        )
        owner = cluster.get("owner") if type(cluster) is dict else None
        if (
            type(cluster) is not dict
            or set(cluster) != {"component_regions", "document_ordinal", "owner"}
            or cluster.get("document_ordinal") not in accepted_ordinals
            or document is None
            or type(owner) is not dict
            or set(owner) not in (owner_fields, narrative_owner_fields)
            or owner.get("alias") not in compiled_specs["query_policy"]["owner_aliases"]
            or type(owner.get("owner_ordinal")) is not int
            or owner["owner_ordinal"] <= 0
            or _SECTION_ID.fullmatch(owner.get("section_id", "")) is None
            or type(owner.get("source_exact")) is not str
            or not owner["source_exact"]
            or owner.get("source_kind")
            not in {"SECTION_TITLE", "TABLE_TITLE", "SECTION_NARRATIVE_CONTEXT_OWNER"}
            or (
                owner["source_kind"] == "SECTION_NARRATIVE_CONTEXT_OWNER"
                and (
                    set(owner) != narrative_owner_fields
                    or type(owner.get("narrative_ordinal")) is not int
                    or owner["narrative_ordinal"] <= 0
                    or owner.get("table_id") is not None
                )
            )
            or (
                owner["source_kind"] != "SECTION_NARRATIVE_CONTEXT_OWNER"
                and set(owner) != owner_fields
            )
            or (
                owner.get("table_id") is not None and _TABLE_ID.fullmatch(owner["table_id"]) is None
            )
        ):
            raise _error("indexed dual-component accepted cluster is invalid")
        regions = _region_axis(cluster["component_regions"])
        if any(
            region["document_ordinal"] != cluster["document_ordinal"]
            or region["document_id"] != document["document_id"]
            or region["source_logical_name"] != document["source_logical_name"]
            or region["source_sha256"] != document["source_sha256"]
            for region in regions
        ):
            raise _error("indexed dual-component accepted cluster source binding drifted")
        consumed_locations = {
            (region["page_json_version_id"], region["section_id"], region["table_id"])
            for region in regions
        }
        consumed_hits = [
            hit
            for hit in value["indexed_role_hits"]
            if hit["query_disposition"] == "CONSUMED_ACCEPTED_COMPONENT_FRAGMENT"
            and hit["document_ordinal"] == cluster["document_ordinal"]
        ]
        location_component_roles = {
            (region["page_json_version_id"], region["section_id"], region["table_id"]): role
            for role, region in zip(_COMPONENT_ROLES, regions, strict=True)
        }
        if (
            {
                (
                    hit["page_json_version_id"],
                    hit["section_id"],
                    hit["table_id"],
                )
                for hit in consumed_hits
            }
            != consumed_locations
            or {hit["component_role"] for hit in consumed_hits if hit["is_seed"]}
            != set(_COMPONENT_ROLES)
            or any(
                location_component_roles[
                    (
                        hit["page_json_version_id"],
                        hit["section_id"],
                        hit["table_id"],
                    )
                ]
                != hit["component_role"]
                for hit in consumed_hits
            )
            or any(
                hit["query_disposition"] != "CONSUMED_ACCEPTED_COMPONENT_FRAGMENT"
                for hit in value["indexed_role_hits"]
                if hit["document_ordinal"] == cluster["document_ordinal"]
                and (
                    hit["page_json_version_id"],
                    hit["section_id"],
                    hit["table_id"],
                )
                in consumed_locations
            )
        ):
            raise _error("indexed dual-component accepted region/role-hit binding drifted")
    all_consumed_ordinals = {
        hit["document_ordinal"]
        for hit in value["indexed_role_hits"]
        if hit["query_disposition"] == "CONSUMED_ACCEPTED_COMPONENT_FRAGMENT"
    }
    if all_consumed_ordinals != accepted_ordinals:
        raise _error("indexed dual-component consumed role-hit document axis drifted")
    receipt = value["query_receipt"]
    query_policy_sha256 = canonical_json_sha256_v1(compiled_specs["query_policy"])
    counts = {
        kind: sum(item["disposition"] == kind for item in dispositions)
        for kind in ("ACCEPTED_CLUSTER", "NOT_OBSERVED", "UNRESOLVED_CLUSTER")
    }
    expected_receipt_fields = {
        "accepted_cluster_axis_sha256": canonical_json_sha256_v1(clusters),
        "accepted_cluster_count": len(clusters),
        "accepted_fragment_count": sum(len(item["component_regions"]) for item in clusters),
        "candidate_disposition_axis_sha256": canonical_json_sha256_v1(dispositions),
        "candidate_disposition_count": len(dispositions),
        "decoded_candidate_page_count": len(
            {item.get("page_json_version_id") for item in value["indexed_role_hits"]}
        ),
        "disposition_counts": counts,
        "indexed_seed_hit_axis_sha256": canonical_json_sha256_v1(value["indexed_seed_hits"]),
        "indexed_seed_hit_count": len(value["indexed_seed_hits"]),
        "indexed_role_hit_axis_sha256": canonical_json_sha256_v1(value["indexed_role_hits"]),
        "indexed_role_hit_count": len(value["indexed_role_hits"]),
        "query_policy_sha256": query_policy_sha256,
        "selected_document_axis_sha256": canonical_json_sha256_v1(documents),
        "selected_document_count": len(documents),
    }
    if any(receipt.get(key) != expected for key, expected in expected_receipt_fields.items()):
        raise _error("indexed dual-component query receipt hashes or counts drifted")
    if (
        type(receipt.get("selected_page_count")) is not int
        or receipt["selected_page_count"] <= 0
        or _SHA256.fullmatch(receipt.get("selected_page_json_frontier_sha256", "")) is None
    ):
        raise _error("indexed dual-component selected page frontier receipt is invalid")
    material = {key: canonical_clone_v1(value[key]) for key in fields - {"query_evidence_id"}}
    if value["query_evidence_id"] != "gjfidcqev1:evidence:" + canonical_json_sha256_v1(material):
        raise _error("indexed dual-component query evidence content ID drifted")
    return canonical_clone_v1(value)


def validate_gemini_json_dual_component_sweep_query_bindings_v1(
    *, trials: Any, indexed_query_evidence: Any, compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Bind every trial/candidate to the exhaustive indexed disposition axis."""

    evidence = validate_gemini_json_indexed_dual_component_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
    if type(trials) is not list or len(trials) != len(evidence["selected_document_axis"]):
        raise _error("dual-component sweep trial axis is incomplete")
    clusters_by_ordinal = {item["document_ordinal"]: item for item in evidence["accepted_clusters"]}
    for ordinal, (trial, document, disposition) in enumerate(
        zip(
            trials,
            evidence["selected_document_axis"],
            evidence["candidate_dispositions"],
            strict=True,
        ),
        1,
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("source_logical_name") != document["source_logical_name"]
            or trial.get("source_sha256") != document["source_sha256"]
            or type(trial.get("candidates")) is not list
            or trial.get("candidate_count") != len(trial["candidates"])
        ):
            raise _error("dual-component sweep trial identity drifted")
        kind = disposition["disposition"]
        if kind == "ACCEPTED_CLUSTER":
            cluster = clusters_by_ordinal[ordinal]
            if len(trial["candidates"]) != 1:
                raise _error("dual-component accepted document needs exactly one candidate")
            candidate = trial["candidates"][0]
            if candidate.get("component_regions") != cluster["component_regions"]:
                raise _error("dual-component candidate region binding drifted")
            if candidate.get("status") == READY:
                if (
                    trial.get("status") != READY
                    or trial.get("selected_candidate_id") != candidate.get("candidate_id")
                    or trial.get("mappings") != candidate.get("mappings")
                    or trial.get("reasons")
                ):
                    raise _error("dual-component READY trial binding drifted")
            elif (
                trial.get("status") != UNRESOLVED
                or trial.get("selected_candidate_id") is not None
                or trial.get("mappings")
                or trial.get("reasons") != candidate.get("reasons")
            ):
                raise _error("dual-component unresolved candidate binding drifted")
        elif kind == "NOT_OBSERVED":
            if (
                trial.get("status") != NOT_OBSERVED
                or trial["candidates"]
                or trial.get("mappings")
                or trial.get("reasons")
                or trial.get("selected_candidate_id") is not None
            ):
                raise _error("dual-component not-observed trial binding drifted")
        elif (
            trial.get("status") != UNRESOLVED
            or trial["candidates"]
            or trial.get("mappings")
            or trial.get("selected_candidate_id") is not None
            or trial.get("reasons") != disposition.get("reason_codes")
        ):
            raise _error("dual-component unresolved query disposition binding drifted")
    return canonical_clone_v1(trials)
