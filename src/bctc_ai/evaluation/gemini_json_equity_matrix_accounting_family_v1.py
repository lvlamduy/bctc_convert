"""Bidirectional equity-matrix accounting closure over selected Gemini JSON.

Gemini supplies only table structure and source text.  This primitive detects
whether equity components live on rows or columns, normalizes the opposite
movement axis, consumes source-only components and nested visible subtotals,
and maps schema roles only after the complete horizontal and vertical graph
closes.  It has no OCR, geometry, bank, filename, page, note-number, or value
routing behavior.
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
    _header_dates,
    _matches,
    _money,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

ENGINE_FORMAT_VERSION = "GEMINI_JSON_EQUITY_MATRIX_ACCOUNTING_FAMILY_V1"
EVALUATION_FORMAT_VERSION = "ACCOUNTING_EQUITY_MATRIX_FAMILY_EVALUATION_SPEC_V1"
SCHEMA_FORMAT_VERSION = "ACCOUNTING_EQUITY_MATRIX_SCHEMA_BINDING_SPEC_V1"
INDEXED_QUERY_EVIDENCE_FORMAT_VERSION = "GEMINI_JSON_INDEXED_EQUITY_MATRIX_QUERY_EVIDENCE_V1"
READY = "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
NOT_OBSERVED = "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
UNRESOLVED = "UNRESOLVED_GEMINI_JSON_FAMILY"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_BIDIRECTIONAL_COMPONENT_MOVEMENT_MATRIX_"
    "EXPLICIT_OWNER_RESET_FENCE_ONE_PAGE_CONTINUATION_EXACT_COMPONENT_INVENTORY_"
    "VISIBLE_HIERARCHICAL_TOTALS_VERTICAL_ROLLFORWARD_CONDITIONAL_BLANK_ZERO_"
    "DOCUMENT_UNIT_CONSENSUS_STRUCTURAL_ROOT_SCHEMA_MAPPING_PROPOSAL_ONLY_NO_"
    "OCR_GEOMETRY_BANK_FILE_PAGE_NOTE_VALUE_ROUTING_BACKSOLVE_CANONICAL_OR_"
    "EXPORT_AUTHORITY"
)

_PAGE_VERSION = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_DOCUMENT_ID = re.compile(r"gfpstorev1:document:[0-9a-f]{64}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SECTION_ID = re.compile(r"s[1-9][0-9]*\Z")
_TABLE_ID = re.compile(r"t[1-9][0-9]*\Z")
_ROW_ID = re.compile(r"r[1-9][0-9]*\Z")
_COLUMN_ID = re.compile(r"c[1-9][0-9]*\Z")
_MAPPED_MOVEMENT_ROLES = ("OPENING", "INCREASE", "DECREASE", "CLOSING")
_MAPPED_TOTAL_ROLES = {
    "OPENING": "OPENING_TOTAL",
    "INCREASE": "INCREASE_TOTAL",
    "DECREASE": "DECREASE_TOTAL",
    "CLOSING": "CLOSING_TOTAL",
}


class GeminiJsonEquityMatrixAccountingFamilyV1Error(ValueError):
    """The matrix policy, selected source graph, or replay drifted."""


def _error(message: str) -> GeminiJsonEquityMatrixAccountingFamilyV1Error:
    return GeminiJsonEquityMatrixAccountingFamilyV1Error(message)


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
            raise _error("equity-matrix child role has no root-level aliases")
        result[child["role"]] = aliases
    return result


def _compile_alias_map(value: Any, *, label: str) -> dict[str, list[str]]:
    if type(value) is not dict or not value:
        raise _error(f"equity-matrix {label} alias map is absent")
    result = {}
    seen: set[str] = set()
    for role, aliases in value.items():
        if (
            type(role) is not str
            or not role
            or type(aliases) is not list
            or not aliases
            or any(type(alias) is not str or not alias.strip() for alias in aliases)
        ):
            raise _error(f"equity-matrix {label} alias map is invalid")
        normalized = [_normalized(alias) for alias in aliases]
        if any(not alias or alias in seen for alias in normalized):
            raise _error(f"equity-matrix {label} aliases collide")
        seen.update(normalized)
        result[role] = canonical_clone_v1(aliases)
    return result


def _compile_units(value: Any) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if type(value) is not list or not value:
        raise _error("equity-matrix unit bindings are absent")
    result = []
    by_alias: dict[str, dict[str, Any]] = {}
    canonical_units: set[str] = set()
    fields = {
        "accepted",
        "aliases",
        "canonical_unit",
        "document_consensus_eligible",
        "magnitude_power10",
    }
    for raw in value:
        if (
            type(raw) is not dict
            or set(raw) != fields
            or type(raw.get("accepted")) is not bool
            or type(raw.get("document_consensus_eligible")) is not bool
            or type(raw.get("aliases")) is not list
            or not raw["aliases"]
            or any(type(alias) is not str or not alias.strip() for alias in raw["aliases"])
            or type(raw.get("canonical_unit")) is not str
            or not raw["canonical_unit"]
            or raw["canonical_unit"] in canonical_units
            or type(raw.get("magnitude_power10")) is not int
            or raw["magnitude_power10"] < 0
        ):
            raise _error("equity-matrix unit binding is invalid")
        canonical_units.add(raw["canonical_unit"])
        normalized_aliases = [_normalized(alias) for alias in raw["aliases"]]
        if any(not alias or alias in by_alias for alias in normalized_aliases):
            raise _error("equity-matrix unit aliases collide")
        binding = {**canonical_clone_v1(raw), "aliases": normalized_aliases}
        for alias in normalized_aliases:
            by_alias[alias] = binding
        result.append(binding)
    if sum(item["accepted"] for item in result) != 1:
        raise _error("equity-matrix requires exactly one accepted money unit")
    return result, by_alias


def compile_gemini_json_equity_matrix_family_specs_v1(
    topology_spec: Any, evaluation_spec: Any, schema_binding_spec: Any
) -> dict[str, Any]:
    """Compile one strict declarative matrix family triplet."""

    try:
        topology = compile_accounting_family_topology_spec_v1(topology_spec)
    except ValueError as exc:
        raise _error("equity-matrix topology spec is invalid") from exc
    if (
        type(evaluation_spec) is not dict
        or set(evaluation_spec)
        != {
            "blank_zero_policy",
            "closure_policy",
            "family_id",
            "format_version",
            "matrix_policy",
        }
        or evaluation_spec.get("format_version") != EVALUATION_FORMAT_VERSION
        or evaluation_spec.get("family_id") != topology["family_id"]
        or evaluation_spec.get("blank_zero_policy") != "ZERO_ONLY_AFTER_COMPLETE_MATRIX_GRAPH_EXACT"
        or evaluation_spec.get("closure_policy")
        != "EXACT_HORIZONTAL_TOTALS_AND_VERTICAL_ROLLFORWARD_ALL_SELECTED_CELLS"
    ):
        raise _error("equity-matrix evaluation spec is invalid")
    policy = evaluation_spec["matrix_policy"]
    policy_fields = {
        "accepted_orientations",
        "max_continuation_pages",
        "minimum_mapped_component_roles",
        "movement_role_aliases",
        "source_only_component_aliases",
        "total_aliases",
        "unit_bindings",
    }
    if (
        type(policy) is not dict
        or set(policy) != policy_fields
        or policy.get("accepted_orientations") != ["COMPONENT_COLUMNS", "COMPONENT_ROWS"]
        or policy.get("max_continuation_pages") != 1
        or type(policy.get("minimum_mapped_component_roles")) is not int
        or policy["minimum_mapped_component_roles"] < 2
        or type(policy.get("total_aliases")) is not list
        or not policy["total_aliases"]
        or any(type(alias) is not str or not alias.strip() for alias in policy["total_aliases"])
    ):
        raise _error("equity-matrix policy is invalid")
    movement_aliases = _compile_alias_map(policy["movement_role_aliases"], label="movement")
    if set(movement_aliases) != set(_MAPPED_MOVEMENT_ROLES):
        raise _error("equity-matrix movement roles are incomplete")
    source_only_aliases = _compile_alias_map(
        policy["source_only_component_aliases"], label="source-only component"
    )
    mapped_aliases = _aliases_by_role(topology)
    mapped_normalized = {
        _normalized(alias) for aliases in mapped_aliases.values() for alias in aliases
    }
    source_only_normalized = {
        _normalized(alias) for aliases in source_only_aliases.values() for alias in aliases
    }
    if mapped_normalized & source_only_normalized:
        raise _error("mapped and source-only component aliases collide")
    units, unit_by_alias = _compile_units(policy["unit_bindings"])
    schema_fields = {
        "component_role_bindings",
        "family_id",
        "family_root_report_norm_id",
        "format_version",
        "movement_total_bindings",
        "root_mapping_policy",
    }
    if (
        type(schema_binding_spec) is not dict
        or set(schema_binding_spec) != schema_fields
        or schema_binding_spec.get("format_version") != SCHEMA_FORMAT_VERSION
        or schema_binding_spec.get("family_id") != topology["family_id"]
        or type(schema_binding_spec.get("family_root_report_norm_id")) is not int
        or schema_binding_spec["family_root_report_norm_id"] <= 0
        or schema_binding_spec.get("root_mapping_policy")
        != "SOURCE_VISIBLE_MATRIX_GRAND_TOTAL_CELLS_ONLY"
    ):
        raise _error("equity-matrix schema binding spec is invalid")

    def bindings(value: Any, *, roles: set[str], label: str) -> dict[str, int]:
        if type(value) is not list or len(value) != len(roles):
            raise _error(f"equity-matrix {label} binding axis is incomplete")
        result: dict[str, int] = {}
        ids: set[int] = set()
        for raw in value:
            if (
                type(raw) is not dict
                or set(raw) != {"report_norm_id", "role"}
                or raw.get("role") not in roles
                or raw["role"] in result
                or type(raw.get("report_norm_id")) is not int
                or raw["report_norm_id"] <= 0
                or raw["report_norm_id"] in ids
            ):
                raise _error(f"equity-matrix {label} binding is invalid")
            result[raw["role"]] = raw["report_norm_id"]
            ids.add(raw["report_norm_id"])
        if set(result) != roles:
            raise _error(f"equity-matrix {label} binding roles are incomplete")
        return result

    component_bindings = bindings(
        schema_binding_spec["component_role_bindings"],
        roles=set(mapped_aliases),
        label="component",
    )
    movement_bindings = bindings(
        schema_binding_spec["movement_total_bindings"],
        roles=set(_MAPPED_TOTAL_ROLES.values()),
        label="movement total",
    )
    all_ids = {
        schema_binding_spec["family_root_report_norm_id"],
        *component_bindings.values(),
        *movement_bindings.values(),
    }
    if len(all_ids) != 1 + len(component_bindings) + len(movement_bindings):
        raise _error("equity-matrix schema report norm IDs collide")
    query_policy = {
        "hard_negative_aliases": canonical_clone_v1(topology["hard_negative_aliases"]),
        "max_continuation_pages": policy["max_continuation_pages"],
        "minimum_mapped_component_roles": policy["minimum_mapped_component_roles"],
        "owner_aliases": canonical_clone_v1(topology["parent"]["aliases"]),
        "reset_aliases": canonical_clone_v1(topology["structural_reset_aliases"]),
    }
    return {
        "aliases_by_role": mapped_aliases,
        "claim_boundary": CLAIM_BOUNDARY,
        "component_report_norm_id_by_role": component_bindings,
        "engine_format_version": ENGINE_FORMAT_VERSION,
        "evaluation": canonical_clone_v1(evaluation_spec),
        "family_id": topology["family_id"],
        "family_root_report_norm_id": schema_binding_spec["family_root_report_norm_id"],
        "movement_aliases_by_role": movement_aliases,
        "movement_total_report_norm_id_by_role": movement_bindings,
        "query_policy": query_policy,
        "schema": canonical_clone_v1(schema_binding_spec),
        "source_only_aliases_by_role": source_only_aliases,
        "topology": topology,
        "total_aliases": canonical_clone_v1(policy["total_aliases"]),
        "unit_binding_by_alias": unit_by_alias,
        "unit_bindings": units,
    }


def _node_index(identifier: Any, prefix: str, limit: int) -> int:
    pattern = _SECTION_ID if prefix == "s" else _TABLE_ID
    if type(identifier) is not str or pattern.fullmatch(identifier) is None:
        raise _error("equity-matrix source node identity is invalid")
    index = int(identifier[1:]) - 1
    if not 0 <= index < limit:
        raise _error("equity-matrix source node identity is out of range")
    return index


def _source_table(
    page_json: Mapping[str, Any], *, section_id: str, table_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    sections = page_json.get("sections")
    if type(sections) is not list:
        raise _error("equity-matrix page has no section axis")
    section = sections[_node_index(section_id, "s", len(sections))]
    tables = section.get("tables") if type(section) is dict else None
    if type(tables) is not list:
        raise _error("equity-matrix section has no table axis")
    table = tables[_node_index(table_id, "t", len(tables))]
    if type(table) is not dict:
        raise _error("equity-matrix source table is invalid")
    return section, table


def _header_members(column: Any) -> list[str]:
    members = column.get("header_path_exact") if type(column) is dict else None
    return (
        [item for item in members if type(item) is str and item.strip()]
        if type(members) is list
        else []
    )


def _role_matches(members: Sequence[Any], aliases_by_role: Mapping[str, list[str]]) -> list[str]:
    return sorted(
        role
        for role, aliases in aliases_by_role.items()
        if any(_matches(member, alias) for member in members for alias in aliases)
    )


def _unit_occurrences(surface: Any, *, compiled_specs: Mapping[str, Any]) -> list[dict[str, Any]]:
    folded = _normalized(surface)
    occurrences = [
        (match.start(), match.end(), alias)
        for alias in compiled_specs["unit_binding_by_alias"]
        for match in re.finditer(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", folded)
    ]
    maximal = sorted(
        [
            item
            for item in occurrences
            if not any(
                other[0] <= item[0]
                and item[1] <= other[1]
                and other[1] - other[0] > item[1] - item[0]
                for other in occurrences
            )
        ],
        key=lambda item: (item[0], item[1], item[2]),
    )
    return [
        {
            "accepted": compiled_specs["unit_binding_by_alias"][alias]["accepted"],
            "canonical_unit": compiled_specs["unit_binding_by_alias"][alias]["canonical_unit"],
            "matched_alias": alias,
            "magnitude_power10": compiled_specs["unit_binding_by_alias"][alias][
                "magnitude_power10"
            ],
        }
        for _start, _end, alias in maximal
    ]


def _semantic_component_members(
    members: Sequence[str], *, compiled_specs: Mapping[str, Any]
) -> list[str]:
    result = []
    aliases = sorted(compiled_specs["unit_binding_by_alias"], key=len, reverse=True)
    for member in members:
        folded = _normalized(member)
        for alias in aliases:
            folded = re.sub(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", " ", folded)
        folded = " ".join(folded.split())
        if folded:
            result.append(folded)
    return result


def _component_record(
    *,
    members: Sequence[str],
    row_kind: Any,
    axis_id: str,
    axis_ordinal: int,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    semantic_members = _semantic_component_members(members, compiled_specs=compiled_specs)
    mapped = _role_matches(semantic_members, compiled_specs["aliases_by_role"])
    source_only = _role_matches(semantic_members, compiled_specs["source_only_aliases_by_role"])
    total_members = [
        member
        for member in semantic_members
        if any(_matches(member, alias) for alias in compiled_specs["total_aliases"])
    ]
    reasons = []
    group_prefix: list[str] = []
    if len(mapped) + len(source_only) > 1:
        reasons.append("COMPONENT_AXIS_MEMBER_MATCHES_MULTIPLE_DECLARED_ROLES")
    if total_members and (mapped or source_only):
        reasons.append("COMPONENT_AXIS_TOTAL_AND_LEAF_ROLES_CONFLICT")
    kind = "UNCLASSIFIED_COMPONENT_AXIS"
    role = None
    if len(mapped) == 1 and not source_only and not total_members:
        kind, role = "MAPPED_COMPONENT", mapped[0]
    elif len(source_only) == 1 and not mapped and not total_members:
        kind, role = "SOURCE_ONLY_COMPONENT", source_only[0]
    elif row_kind == "TOTAL" or len(total_members) == 1:
        prefix = (
            semantic_members[:-1] if total_members and semantic_members[-1] in total_members else []
        )
        group_prefix = [_normalized(member) for member in prefix]
        kind = "GROUP_TOTAL" if prefix else "GRAND_TOTAL"
    return {
        "axis_id": axis_id,
        "axis_ordinal": axis_ordinal,
        "kind": kind,
        "group_prefix": group_prefix,
        "members_exact": canonical_clone_v1(list(members)),
        "reasons": reasons,
        "role": role,
        "semantic_path": [_normalized(member) for member in semantic_members],
    }


def classify_gemini_json_equity_matrix_table_v1(
    table: Any, *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Classify one matrix fragment from its two declared axes only."""

    rows = table.get("rows") if type(table) is dict else None
    columns = table.get("columns") if type(table) is dict else None
    if type(rows) is not list or type(columns) is not list or not rows or not columns:
        raise _error("equity-matrix table axes are invalid")
    if any(
        type(row) is not dict
        or type(row.get("values_exact")) is not list
        or len(row["values_exact"]) != len(columns)
        or type(row.get("hierarchy_path_exact")) is not list
        for row in rows
    ):
        raise _error("equity-matrix row cell vectors are invalid")
    if any(type(column) is not dict for column in columns):
        raise _error("equity-matrix column axis is invalid")
    row_components = [
        _component_record(
            members=[row.get("label_exact")] if type(row.get("label_exact")) is str else [],
            row_kind=row.get("row_kind"),
            axis_id=f"r{ordinal}",
            axis_ordinal=ordinal,
            compiled_specs=compiled_specs,
        )
        for ordinal, row in enumerate(rows, start=1)
    ]
    column_components = [
        _component_record(
            members=_header_members(column),
            row_kind=None,
            axis_id=f"c{ordinal}",
            axis_ordinal=ordinal,
            compiled_specs=compiled_specs,
        )
        for ordinal, column in enumerate(columns, start=1)
    ]
    row_mapped = {item["role"] for item in row_components if item["kind"] == "MAPPED_COMPONENT"}
    column_mapped = {
        item["role"] for item in column_components if item["kind"] == "MAPPED_COMPONENT"
    }
    minimum = compiled_specs["query_policy"]["minimum_mapped_component_roles"]
    orientations = []
    if len(row_mapped) >= minimum and len(columns) >= 4:
        orientations.append("COMPONENT_ROWS")
    if (
        len(column_mapped) >= minimum
        and sum(column.get("value_kind") == "MONEY" for column in columns) >= 4
    ):
        orientations.append("COMPONENT_COLUMNS")
    reasons = sorted(
        {reason for item in [*row_components, *column_components] for reason in item["reasons"]}
    )
    if len(orientations) > 1:
        # Movement labels can legitimately reuse component vocabulary (for
        # example ``Lợi nhuận sau thuế`` or ``Chênh lệch tỷ giá``).  They are
        # not the component axis when the opposite axis carries a strictly
        # more complete declared component population.  Keep a tie
        # fail-closed: it is genuine orientation ambiguity rather than a
        # reason to prefer rows or columns by layout convention.
        row_score = len(row_mapped)
        column_score = len(column_mapped)
        if row_score > column_score:
            orientations = ["COMPONENT_ROWS"]
        elif column_score > row_score:
            orientations = ["COMPONENT_COLUMNS"]
        else:
            reasons.append("BOTH_MATRIX_ORIENTATIONS_MATCH")
    orientation = orientations[0] if len(orientations) == 1 else None
    component_axis = (
        row_components
        if orientation == "COMPONENT_ROWS"
        else column_components
        if orientation == "COMPONENT_COLUMNS"
        else []
    )
    roles = [item["role"] for item in component_axis if item["kind"] == "MAPPED_COMPONENT"]
    if len(roles) != len(set(roles)):
        reasons.append("DUPLICATE_MAPPED_COMPONENT_ROLE")
    if (
        orientation is not None
        and sum(item["kind"] == "GRAND_TOTAL" for item in component_axis) != 1
    ):
        reasons.append("EXACTLY_ONE_COMPONENT_GRAND_TOTAL_REQUIRED")
    if orientation is not None and any(
        item["kind"] == "UNCLASSIFIED_COMPONENT_AXIS" for item in component_axis
    ):
        reasons.append("UNCLASSIFIED_COMPONENT_AXIS_PRESENT")
    return {
        "column_declared_component_roles": sorted(column_mapped),
        "component_axis": component_axis,
        "component_axis_sha256": canonical_json_sha256_v1(component_axis),
        "mapped_component_roles": sorted(set(roles)),
        "orientation": orientation,
        "reasons": sorted(set(reasons)),
        "row_declared_component_roles": sorted(row_mapped),
        "status": "MATRIX_FRAGMENT" if orientation is not None and not reasons else "NOT_MATRIX",
    }


def _checked_region_axis(regions: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
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
    if type(regions) not in {list, tuple} or not 1 <= len(regions) <= 2:
        raise _error("equity-matrix region axis must contain one or two fragments")
    result = []
    identity = None
    prior_key = None
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
            or _TABLE_ID.fullmatch(region.get("table_id", "")) is None
            or type(region.get("source_logical_name")) is not str
            or not region["source_logical_name"]
            or _SHA256.fullmatch(region.get("source_sha256", "")) is None
        ):
            raise _error("equity-matrix source region is invalid")
        current_identity = tuple(
            region[key]
            for key in (
                "document_id",
                "document_ordinal",
                "source_logical_name",
                "source_sha256",
            )
        )
        key = (
            region["selected_page_ordinal"],
            int(region["section_id"][1:]),
            int(region["table_id"][1:]),
        )
        if identity is None:
            identity = current_identity
        elif current_identity != identity:
            raise _error("equity-matrix fragments belong to different documents")
        if prior_key is not None and key <= prior_key:
            raise _error("equity-matrix fragments are not in source order")
        prior_key = key
        result.append(canonical_clone_v1(region))
    if len(result) == 2 and (
        result[1]["physical_page"] - result[0]["physical_page"] != 1
        or result[1]["selected_page_ordinal"] - result[0]["selected_page_ordinal"] != 1
    ):
        raise _error("equity-matrix continuation fragments are not adjacent pages")
    return result


def build_gemini_json_equity_matrix_region_query_receipt_v1(
    regions: Sequence[Mapping[str, Any]], *, owner_receipt: Mapping[str, Any]
) -> dict[str, Any]:
    """Seal exact component regions and their externally indexed owner fence."""

    checked = _checked_region_axis(regions)
    if type(owner_receipt) is not dict:
        raise _error("equity-matrix owner receipt is invalid")
    payload = {
        "component_region_axis_sha256": canonical_json_sha256_v1(checked),
        "component_regions": checked,
        "owner_receipt": canonical_clone_v1(owner_receipt),
        "rule": "EXACT_SELECTED_MATRIX_FRAGMENTS_UNDER_ONE_RESET_FENCED_OWNER",
    }
    return {**payload, "query_receipt_sha256": canonical_json_sha256_v1(payload)}


def _movement_matches(members: Sequence[str], *, compiled_specs: Mapping[str, Any]) -> list[str]:
    return sorted(
        role
        for role, aliases in compiled_specs["movement_aliases_by_role"].items()
        if any(_matches(member, alias) for member in members for alias in aliases)
    )


def _movement_surface_record(
    *,
    members: Sequence[str],
    axis_id: str,
    axis_ordinal: int,
    source_ref: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    semantic_members = _semantic_component_members(members, compiled_specs=compiled_specs)
    # Alias matching intentionally uses normalized members, but dates must be
    # parsed from the literal surface.  Normalization removes date separators
    # (``1.1.2025`` -> ``1 1 2025``), which would otherwise turn source-visible
    # balance dates into undated rows/columns.
    source_exact = " ".join(member for member in members if type(member) is str)
    explicit_roles = _movement_matches(semantic_members, compiled_specs=compiled_specs)
    dates = sorted(item.isoformat() for item in _header_dates(source_exact))
    folded = _normalized(source_exact)
    balance_marker = bool(re.search(r"\b(?:so du|du dau|du cuoi|tai ngay)\b", folded))
    reasons = []
    if len(explicit_roles) > 1:
        reasons.append("MOVEMENT_AXIS_SURFACE_MATCHES_MULTIPLE_ROLES")
    if len(dates) > 1:
        reasons.append("MOVEMENT_AXIS_SURFACE_HAS_MULTIPLE_DATES")
    if dates and not balance_marker:
        reasons.append("MOVEMENT_AXIS_DATE_HAS_NO_BALANCE_MARKER")
    return {
        "axis_id": axis_id,
        "axis_ordinal": axis_ordinal,
        "balance_marker": balance_marker,
        "dates": dates,
        "explicit_roles": explicit_roles,
        "members_exact": canonical_clone_v1(list(members)),
        "reasons": reasons,
        "source_ref": canonical_clone_v1(source_ref),
    }


def _component_projection(axis: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "axis_ordinal": item["axis_ordinal"],
            "group_prefix": canonical_clone_v1(item["group_prefix"]),
            "kind": item["kind"],
            "role": item["role"],
            "semantic_path": canonical_clone_v1(item["semantic_path"]),
        }
        for item in axis
    ]


def _local_unit_axis(
    table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    evidence = []
    conflicts = []
    undeclared = []

    def classify(text: Any, source_kind: str, *, explicit_slot: bool) -> dict[str, Any] | None:
        if type(text) is not str or not text.strip():
            return None
        occurrences = _unit_occurrences(text, compiled_specs=compiled_specs)
        if occurrences:
            identities = {
                (item["canonical_unit"], item["magnitude_power10"]) for item in occurrences
            }
            records = [
                {**item, "source_kind": source_kind, "text_exact": text} for item in occurrences
            ]
            evidence.extend(records)
            if len(identities) > 1:
                conflicts.append(
                    {
                        "matched_aliases": [item["matched_alias"] for item in occurrences],
                        "source_kind": source_kind,
                        "text_exact": text,
                    }
                )
                return None
            return records[0]
        # A bare ``đồng`` inside a semantic label such as ``cổ đông`` is not a
        # unit declaration.  Outside the typed table-unit slot, only an
        # explicit magnitude+currency phrase or a currency token is unit-like
        # enough to make an undeclared-unit claim.
        if explicit_slot or re.search(
            r"\b(?:(?:trieu|nghin|ty)\s+(?:dong|vnd|usd)|vnd|usd)\b",
            _normalized(text),
        ):
            undeclared.append({"source_kind": source_kind, "text_exact": text})
        return None

    table_record = classify(table.get("unit_exact"), "TABLE_UNIT", explicit_slot=True)
    columns = table.get("columns")
    money_columns = (
        [
            (ordinal, column)
            for ordinal, column in enumerate(columns, start=1)
            if type(column) is dict and column.get("value_kind") == "MONEY"
        ]
        if type(columns) is list
        else []
    )
    column_records = [
        classify(
            " ".join(_header_members(column)),
            f"MONEY_COLUMN_HEADER:c{ordinal}",
            explicit_slot=False,
        )
        for ordinal, column in money_columns
    ]
    reasons = []
    if conflicts:
        reasons.append("CONFLICTING_DECLARED_UNIT_ALIASES_ON_ONE_SURFACE")
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
            reasons.append("TABLE_AND_COLUMN_MONEY_UNITS_CONFLICT")
    elif any(item is not None for item in column_records):
        if (
            len(column_records) != len(money_columns)
            or any(item is None for item in column_records)
            or any(not item["accepted"] for item in column_records if item is not None)
        ):
            reasons.append("MONEY_COLUMN_UNIT_EVIDENCE_IS_PARTIAL")
        else:
            units = {item["canonical_unit"] for item in column_records if item is not None}
            if len(units) != 1:
                reasons.append("MONEY_COLUMN_UNITS_CONFLICT")
            else:
                canonical_unit = next(iter(units))
                source = "LOCAL_UNIFORM_ALL_MONEY_COLUMN_UNITS"
    return {
        "canonical_unit": canonical_unit,
        "complete": canonical_unit is not None and not reasons,
        "conflicting_surfaces": conflicts,
        "evidence": evidence,
        "reasons": sorted(set(reasons)),
        "source": source,
        "undeclared_evidence": undeclared,
    }


def _resolve_cluster_unit(
    *,
    tables: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    document_unit_context_evidence: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    local = [_local_unit_axis(table, compiled_specs=compiled_specs) for table in tables]
    reasons = [
        f"FRAGMENT_{ordinal}:{reason}"
        for ordinal, axis in enumerate(local, start=1)
        for reason in axis["reasons"]
    ]
    units = {axis["canonical_unit"] for axis in local if axis["complete"]}
    explicit_incomplete = any(
        not axis["complete"] and (axis["evidence"] or axis["undeclared_evidence"]) for axis in local
    )
    source = None
    canonical_unit = None
    if len(units) > 1:
        reasons.append("MATRIX_FRAGMENT_UNITS_CONFLICT")
    elif len(units) == 1 and not explicit_incomplete:
        canonical_unit = next(iter(units))
        source = "LOCAL_MATRIX_FRAGMENT_UNIT"
    elif not units and not explicit_incomplete:
        context = document_unit_context_evidence
        if (
            type(context) is dict
            and context.get("status") == "UNIQUE_AUTHENTICATED_DOCUMENT_MONEY_UNIT_CONSENSUS"
            and type(context.get("canonical_unit")) is str
        ):
            canonical_unit = context["canonical_unit"]
            source = "INDEXED_DOCUMENT_MONEY_UNIT_CONSENSUS"
        else:
            reasons.append("AUTHENTICATED_DOCUMENT_MONEY_UNIT_CONSENSUS_UNAVAILABLE")
    return (
        {
            "canonical_unit": canonical_unit,
            "document_unit_context_evidence": canonical_clone_v1(document_unit_context_evidence),
            "fragment_unit_axes": local,
            "source": source,
        },
        sorted(set(reasons)),
    )


def _parsed_cell(
    *, value: Any, region: Mapping[str, Any], row_id: str, column_id: str
) -> tuple[dict[str, Any] | None, str | None]:
    source_value = value
    if type(value) is str:
        compact = "".join(value.split())
        if compact and (
            all(character in "-–—_" for character in compact)
            or (
                any(character in "-–—_" for character in compact)
                and not any(character.isdigit() for character in compact)
            )
        ):
            value = "-"
    try:
        parsed = _money(value)
    except ValueError:
        return None, f"MONEY_CELL_INVALID:{region['page_json_version_id']}:{row_id}:{column_id}"
    parsed["source_text"] = source_value
    return (
        {
            **parsed,
            "cell_ref": {
                "column_id": column_id,
                "locator": canonical_clone_v1(region),
                "row_id": row_id,
            },
        },
        None,
    )


def _dash_prefixed_numeric_coefficient(value: Any) -> int | None:
    if type(value) is not str:
        return None
    remainder = re.sub(r"^[\s\-–—_]+", "", value)
    if remainder == value or not remainder.strip():
        return None
    try:
        parsed = _money(remainder)
    except ValueError:
        return None
    return parsed["coefficient"] if parsed["state"] == "RAW_SIGNED_INTEGER" else None


def _build_matrix_graph(
    *,
    regions: Sequence[Mapping[str, Any]],
    tables: Sequence[Mapping[str, Any]],
    classifications: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    reasons = []
    orientations = {item["orientation"] for item in classifications}
    if len(orientations) != 1 or None in orientations:
        return {}, ["MATRIX_FRAGMENT_ORIENTATIONS_DIFFER"]
    orientation = next(iter(orientations))
    projections = [_component_projection(item["component_axis"]) for item in classifications]
    if any(not same_typed_json_v1(projections[0], item) for item in projections[1:]):
        return {}, ["CONTINUATION_COMPONENT_AXES_DIFFER"]
    component_axis = canonical_clone_v1(classifications[0]["component_axis"])
    movement_axis = []
    component_cells: dict[str, dict[str, dict[str, Any]]] = {
        item["axis_id"]: {} for item in component_axis
    }
    alignment_receipts = []
    period_block_receipt = None
    if orientation == "COMPONENT_ROWS":
        if len(tables) != 1:
            return {}, ["COMPONENT_ROW_ORIENTATION_CANNOT_SPAN_MULTIPLE_FRAGMENTS"]
        table = tables[0]
        columns = table["columns"]
        raw_movement = [
            _movement_surface_record(
                members=_header_members(column),
                axis_id=f"c{ordinal}",
                axis_ordinal=ordinal,
                source_ref={**canonical_clone_v1(regions[0]), "column_id": f"c{ordinal}"},
                compiled_specs=compiled_specs,
            )
            for ordinal, column in enumerate(columns, start=1)
        ]
        reasons.extend(reason for item in raw_movement for reason in item["reasons"])
        by_role: dict[str, list[dict[str, Any]]] = {role: [] for role in _MAPPED_MOVEMENT_ROLES}
        for item in raw_movement:
            if len(item["explicit_roles"]) == 1:
                by_role[item["explicit_roles"][0]].append(item)
        dated_balances = [
            item for item in raw_movement if item["balance_marker"] and len(item["dates"]) == 1
        ]
        if not by_role["OPENING"] and len(dated_balances) >= 2:
            by_role["OPENING"].append(dated_balances[0])
        if not by_role["CLOSING"] and len(dated_balances) >= 2:
            by_role["CLOSING"].append(dated_balances[-1])
        if any(len(by_role[role]) != 1 for role in _MAPPED_MOVEMENT_ROLES):
            reasons.append("EXACT_OPENING_INCREASE_DECREASE_CLOSING_COLUMN_AXIS_REQUIRED")
        else:
            movement_axis = [by_role[role][0] for role in _MAPPED_MOVEMENT_ROLES]
            if [item["axis_ordinal"] for item in movement_axis] != sorted(
                item["axis_ordinal"] for item in movement_axis
            ):
                reasons.append("MOVEMENT_COLUMN_AXIS_ORDER_DRIFTED")
            for item, role in zip(movement_axis, _MAPPED_MOVEMENT_ROLES, strict=True):
                item["axis_role"] = role
        for component, row in zip(component_axis, table["rows"], strict=True):
            for movement in movement_axis:
                column_index = movement["axis_ordinal"] - 1
                cell, reason = _parsed_cell(
                    value=row["values_exact"][column_index],
                    region=regions[0],
                    row_id=component["axis_id"],
                    column_id=movement["axis_id"],
                )
                if reason:
                    reasons.append(reason)
                elif cell is not None:
                    component_cells[component["axis_id"]][movement["axis_role"]] = cell
    else:
        raw_rows = []
        for fragment_ordinal, (region, table) in enumerate(
            zip(regions, tables, strict=True), start=1
        ):
            for row_ordinal, row in enumerate(table["rows"], start=1):
                axis_id = f"f{fragment_ordinal}:r{row_ordinal}"
                raw_rows.append(
                    {
                        **_movement_surface_record(
                            members=[row.get("label_exact")]
                            if type(row.get("label_exact")) is str
                            else [],
                            axis_id=axis_id,
                            axis_ordinal=len(raw_rows) + 1,
                            source_ref={
                                **canonical_clone_v1(region),
                                "row_id": f"r{row_ordinal}",
                            },
                            compiled_specs=compiled_specs,
                        ),
                        "fragment_ordinal": fragment_ordinal,
                        "row": row,
                        "row_id": f"r{row_ordinal}",
                    }
                )
        reasons.extend(reason for item in raw_rows for reason in item["reasons"])
        balances = [
            item
            for item in raw_rows
            if item["balance_marker"]
            and (item["dates"] or set(item["explicit_roles"]) & {"OPENING", "CLOSING"})
        ]
        if len(balances) < 2:
            reasons.append("AT_LEAST_TWO_ORDERED_BALANCE_ROWS_REQUIRED")
        else:
            blocks = []
            for opening, closing in zip(balances, balances[1:], strict=False):
                detail_count = closing["axis_ordinal"] - opening["axis_ordinal"] - 1
                explicit_pair = (
                    "OPENING" in opening["explicit_roles"]
                    and "CLOSING" in closing["explicit_roles"]
                )
                if detail_count < 0 or (detail_count == 0 and not explicit_pair):
                    continue
                start = date.fromisoformat(opening["dates"][0]) if opening["dates"] else None
                end = date.fromisoformat(closing["dates"][0]) if closing["dates"] else None
                if (start is None) != (end is None):
                    continue
                if start is not None and (not start < end or (end - start).days > 366):
                    continue
                blocks.append(
                    {
                        "closing": closing,
                        "closing_date": end.isoformat() if end is not None else None,
                        "detail_row_count": detail_count,
                        "opening": opening,
                        "opening_date": start.isoformat() if start is not None else None,
                    }
                )
            selected_block = None
            if len(blocks) == 1:
                selected_block = blocks[0]
                selection_rule = "ONLY_COMPLETE_ORDERED_BALANCE_BLOCK"
            elif len(blocks) > 1 and all(item["closing_date"] is not None for item in blocks):
                latest = max(item["closing_date"] for item in blocks)
                latest_blocks = [item for item in blocks if item["closing_date"] == latest]
                if len(latest_blocks) == 1:
                    selected_block = latest_blocks[0]
                    selection_rule = "UNIQUE_LATEST_SOURCE_DATED_COMPLETE_BALANCE_BLOCK"
            if selected_block is None:
                reasons.append("CURRENT_MOVEMENT_BLOCK_PERIOD_NOT_UNIQUE")
            else:
                opening = selected_block["opening"]
                closing = selected_block["closing"]
                selected = raw_rows[opening["axis_ordinal"] - 1 : closing["axis_ordinal"]]
                period_block_receipt = {
                    "candidate_blocks": [
                        {
                            "closing_axis_id": item["closing"]["axis_id"],
                            "closing_date": item["closing_date"],
                            "detail_row_count": item["detail_row_count"],
                            "opening_axis_id": item["opening"]["axis_id"],
                            "opening_date": item["opening_date"],
                        }
                        for item in blocks
                    ],
                    "rule": selection_rule,
                    "selected_closing_axis_id": closing["axis_id"],
                    "selected_opening_axis_id": opening["axis_id"],
                }
            if selected_block is None:
                selected = []
            explicit_middle_roles: set[str] = set()
            for ordinal, item in enumerate(selected):
                if ordinal == 0:
                    item["axis_role"] = "OPENING"
                elif ordinal == len(selected) - 1:
                    item["axis_role"] = "CLOSING"
                elif len(item["explicit_roles"]) == 1 and item["explicit_roles"][0] in {
                    "INCREASE",
                    "DECREASE",
                }:
                    explicit_role = item["explicit_roles"][0]
                    if explicit_role in explicit_middle_roles:
                        reasons.append("DUPLICATE_EXPLICIT_MOVEMENT_TOTAL_ROLE")
                    explicit_middle_roles.add(explicit_role)
                    item["axis_role"] = explicit_role
                else:
                    item["axis_role"] = f"MOVEMENT_{ordinal:04d}"
            movement_axis = selected
            for component in component_axis:
                column_index = component["axis_ordinal"] - 1
                for movement in movement_axis:
                    region = regions[movement["fragment_ordinal"] - 1]
                    value = movement["row"]["values_exact"][column_index]
                    mixed_coefficient = _dash_prefixed_numeric_coefficient(value)
                    if (
                        component["kind"] == "GROUP_TOTAL"
                        and mixed_coefficient is not None
                        and column_index + 1 < len(movement["row"]["values_exact"])
                    ):
                        try:
                            following = _money(movement["row"]["values_exact"][column_index + 1])
                        except ValueError:
                            following = None
                        if following is not None and following["coefficient"] == mixed_coefficient:
                            alignment_receipts.append(
                                {
                                    "axis_role": movement["axis_role"],
                                    "component_axis_id": component["axis_id"],
                                    "raw_source_text": value,
                                    "rule": (
                                        "GROUP_TOTAL_DASH_WITH_DUPLICATED_FOLLOWING_"
                                        "LEAF_VALUE_CANONICALIZED_TO_DASH"
                                    ),
                                }
                            )
                            value = "-"
                    cell, reason = _parsed_cell(
                        value=value,
                        region=region,
                        row_id=movement["row_id"],
                        column_id=component["axis_id"],
                    )
                    if reason:
                        reasons.append(reason)
                    elif cell is not None:
                        component_cells[component["axis_id"]][movement["axis_role"]] = cell
    return (
        {
            "component_axis": component_axis,
            "component_cells": component_cells,
            "alignment_receipts": alignment_receipts,
            "movement_axis": [
                {key: canonical_clone_v1(value) for key, value in item.items() if key != "row"}
                for item in movement_axis
            ],
            "orientation": orientation,
            "period_block_receipt": period_block_receipt,
        },
        sorted(set(reasons)),
    )


def _starts_with(value: Sequence[str], prefix: Sequence[str]) -> bool:
    return len(value) > len(prefix) and list(value[: len(prefix)]) == list(prefix)


def _equation_terms_for_total(
    *, total: Mapping[str, Any], component_axis: Sequence[Mapping[str, Any]]
) -> list[Mapping[str, Any]]:
    leaves = [
        item
        for item in component_axis
        if item["kind"] in {"MAPPED_COMPONENT", "SOURCE_ONLY_COMPONENT"}
    ]
    groups = [item for item in component_axis if item["kind"] == "GROUP_TOTAL"]
    if total["kind"] == "GROUP_TOTAL":
        return [
            item for item in leaves if _starts_with(item["semantic_path"], total["group_prefix"])
        ]
    grouped_prefixes = [item["group_prefix"] for item in groups]
    return [
        *groups,
        *[
            item
            for item in leaves
            if not any(_starts_with(item["semantic_path"], prefix) for prefix in grouped_prefixes)
        ],
    ]


def _cell_term(cell: Mapping[str, Any], *, multiplier: int = 1) -> dict[str, Any]:
    return {
        "cell_ref": canonical_clone_v1(cell["cell_ref"]),
        "coefficient": cell["coefficient"],
        "multiplier": multiplier,
        "state": cell["state"],
    }


def _build_equations(graph: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[str], int]:
    axis = graph["component_axis"]
    cells = graph["component_cells"]
    movement = graph["movement_axis"]
    totals = [item for item in axis if item["kind"] in {"GROUP_TOTAL", "GRAND_TOTAL"}]
    reasons = []
    equations = []
    for move in movement:
        move_role = move["axis_role"]
        for total in totals:
            terms = _equation_terms_for_total(total=total, component_axis=axis)
            result = cells[total["axis_id"]].get(move_role)
            term_cells = [cells[item["axis_id"]].get(move_role) for item in terms]
            if result is None or not terms or any(item is None for item in term_cells):
                reasons.append("HORIZONTAL_TOTAL_EQUATION_CELL_AXIS_INCOMPLETE")
                continue
            computed = sum(item["coefficient"] for item in term_cells if item is not None)
            status = "EXACT" if computed == result["coefficient"] else "MISMATCH"
            equation = {
                "axis_role": move_role,
                "computed_value": computed,
                "equation_kind": (
                    "VISIBLE_GROUP_HORIZONTAL_TOTAL"
                    if total["kind"] == "GROUP_TOTAL"
                    else "VISIBLE_GRAND_HORIZONTAL_TOTAL"
                ),
                "result": _cell_term(result),
                "status": status,
                "terms": [_cell_term(item) for item in term_cells if item is not None],
                "total_axis_id": total["axis_id"],
            }
            equations.append(equation)
            if status != "EXACT":
                reasons.append("HORIZONTAL_VISIBLE_TOTAL_MISMATCH")
    sign_multiplier = 1
    if graph["orientation"] == "COMPONENT_ROWS":
        exact_modes = []
        for candidate in (1, -1):
            if all(
                cells[item["axis_id"]]["OPENING"]["coefficient"]
                + cells[item["axis_id"]]["INCREASE"]["coefficient"]
                + candidate * cells[item["axis_id"]]["DECREASE"]["coefficient"]
                == cells[item["axis_id"]]["CLOSING"]["coefficient"]
                for item in axis
            ):
                exact_modes.append(candidate)
        if not exact_modes:
            reasons.append("VERTICAL_EXPLICIT_MOVEMENT_SIGN_MODE_UNRESOLVED")
        else:
            sign_multiplier = exact_modes[0] if len(exact_modes) == 1 else -1
        for item in axis:
            required = ["OPENING", "INCREASE", "DECREASE", "CLOSING"]
            if any(role not in cells[item["axis_id"]] for role in required):
                reasons.append("VERTICAL_EXPLICIT_MOVEMENT_CELL_AXIS_INCOMPLETE")
                continue
            opening = cells[item["axis_id"]]["OPENING"]
            increase = cells[item["axis_id"]]["INCREASE"]
            decrease = cells[item["axis_id"]]["DECREASE"]
            closing = cells[item["axis_id"]]["CLOSING"]
            computed = (
                opening["coefficient"]
                + increase["coefficient"]
                + sign_multiplier * decrease["coefficient"]
            )
            status = "EXACT" if computed == closing["coefficient"] else "MISMATCH"
            equations.append(
                {
                    "component_axis_id": item["axis_id"],
                    "computed_value": computed,
                    "decrease_multiplier": sign_multiplier,
                    "equation_kind": "VERTICAL_EXPLICIT_MOVEMENT_ROLLFORWARD",
                    "result": _cell_term(closing),
                    "status": status,
                    "terms": [
                        _cell_term(opening),
                        _cell_term(increase),
                        _cell_term(decrease, multiplier=sign_multiplier),
                    ],
                }
            )
            if status != "EXACT":
                reasons.append("VERTICAL_COMPONENT_ROLLFORWARD_MISMATCH")
    else:
        roles = [item["axis_role"] for item in movement]
        if len(roles) < 2 or roles[0] != "OPENING" or roles[-1] != "CLOSING":
            reasons.append("VERTICAL_DETAILED_MOVEMENT_AXIS_INVALID")
        else:
            for item in axis:
                component = cells[item["axis_id"]]
                if any(role not in component for role in roles):
                    reasons.append("VERTICAL_DETAILED_MOVEMENT_CELL_AXIS_INCOMPLETE")
                    continue
                opening = component["OPENING"]
                closing = component["CLOSING"]
                detail = [component[role] for role in roles[1:-1]]
                computed = opening["coefficient"] + sum(cell["coefficient"] for cell in detail)
                status = "EXACT" if computed == closing["coefficient"] else "MISMATCH"
                equations.append(
                    {
                        "component_axis_id": item["axis_id"],
                        "computed_value": computed,
                        "equation_kind": "VERTICAL_DETAILED_MOVEMENT_ROLLFORWARD",
                        "result": _cell_term(closing),
                        "status": status,
                        "terms": [_cell_term(opening), *[_cell_term(cell) for cell in detail]],
                    }
                )
                if status != "EXACT":
                    reasons.append("VERTICAL_COMPONENT_ROLLFORWARD_MISMATCH")
    return equations, sorted(set(reasons)), sign_multiplier


def _component_column_row_alignment_candidates(
    *,
    graph: Mapping[str, Any],
    axis_role: str,
) -> list[dict[str, Any]]:
    axis = graph["component_axis"]
    source_cells = [graph["component_cells"][item["axis_id"]][axis_role] for item in axis]
    tokens = [
        (ordinal, cell) for ordinal, cell in enumerate(source_cells) if cell["coefficient"] != 0
    ]
    totals = [item for item in axis if item["kind"] in {"GROUP_TOTAL", "GRAND_TOTAL"}]
    candidates: dict[tuple[int, ...], dict[str, Any]] = {}
    # The matrix widths in the sealed policy are small (the production maximum
    # is eleven).  Enumerating monotone placements preserves Gemini's token
    # order and never invents or changes a digit.
    from itertools import combinations

    for positions in combinations(range(len(axis)), len(tokens)):
        vector = [0] * len(axis)
        placed: dict[int, Mapping[str, Any]] = {}
        for (_source_ordinal, cell), target_ordinal in zip(tokens, positions, strict=True):
            vector[target_ordinal] = cell["coefficient"]
            placed[target_ordinal] = cell
        if any(
            sum(
                vector[item["axis_ordinal"] - 1]
                for item in _equation_terms_for_total(total=total, component_axis=axis)
            )
            != vector[total["axis_ordinal"] - 1]
            for total in totals
        ):
            continue
        score = sum(
            abs(source_ordinal - target_ordinal)
            for (source_ordinal, _cell), target_ordinal in zip(tokens, positions, strict=True)
        )
        key = tuple(vector)
        prior = candidates.get(key)
        if prior is not None and prior["displacement_score"] <= score:
            continue
        effective_cells = []
        assignments = []
        for target_ordinal, component in enumerate(axis):
            if target_ordinal in placed:
                cell = canonical_clone_v1(placed[target_ordinal])
                source_cell_ref = canonical_clone_v1(cell["cell_ref"])
                source_column_id = source_cell_ref["column_id"]
                effective_cell_ref = canonical_clone_v1(source_cell_ref)
                effective_cell_ref["column_id"] = component["axis_id"]
                cell["cell_ref"] = effective_cell_ref
                cell["source_cell_ref"] = source_cell_ref
                if source_column_id != component["axis_id"]:
                    cell["source_state"] = cell["state"]
                    cell["state"] = "ROW_ALIGNMENT_SOURCE_DIGIT_REASSIGNED_GRAPH_EXACT"
                assignments.append(
                    {
                        "coefficient": cell["coefficient"],
                        "effective_cell_ref": effective_cell_ref,
                        "effective_component_axis_id": component["axis_id"],
                        "source_cell_ref": source_cell_ref,
                        "source_column_id": source_column_id,
                        "source_text": cell["source_text"],
                    }
                )
            else:
                raw = source_cells[target_ordinal]
                cell = canonical_clone_v1(raw)
                if raw["coefficient"] != 0:
                    # The non-zero source slot is consumed by one assignment
                    # elsewhere.  Keep the effective zero explicitly derived
                    # instead of claiming the same raw cell as both a digit
                    # and a blank.
                    cell = {
                        "cell_ref": canonical_clone_v1(raw["cell_ref"]),
                        "coefficient": 0,
                        "source_cell_ref": None,
                        "source_text": None,
                        "state": "ROW_ALIGNMENT_ZERO_EQUATION_EXACT",
                    }
                else:
                    cell["source_cell_ref"] = canonical_clone_v1(raw["cell_ref"])
            effective_cells.append(cell)
        candidates[key] = {
            "assignments": assignments,
            "cells": effective_cells,
            "displacement_score": score,
            "vector": key,
        }
    return sorted(
        candidates.values(),
        key=lambda item: (item["displacement_score"], item["vector"]),
    )


def _resolve_component_column_row_alignment_v1(
    graph: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    if graph.get("orientation") != "COMPONENT_COLUMNS":
        return None, ["ROW_ALIGNMENT_ONLY_APPLIES_TO_COMPONENT_COLUMNS"]
    movement = graph["movement_axis"]
    if len(movement) < 3:
        return None, ["ROW_ALIGNMENT_REQUIRES_DETAILED_MOVEMENT_ROWS"]
    axis = graph["component_axis"]
    opening_role = movement[0]["axis_role"]
    closing_role = movement[-1]["axis_role"]
    detail_roles = [item["axis_role"] for item in movement[1:-1]]
    domains = [
        _component_column_row_alignment_candidates(graph=graph, axis_role=axis_role)
        for axis_role in detail_roles
    ]
    if any(not domain for domain in domains):
        return None, ["ROW_ALIGNMENT_HAS_NO_HORIZONTAL_EXACT_PLACEMENT"]
    target = tuple(
        graph["component_cells"][item["axis_id"]][closing_role]["coefficient"]
        - graph["component_cells"][item["axis_id"]][opening_role]["coefficient"]
        for item in axis
    )
    state_bound = 100_000

    def achievable_sums(excluded: int, component_ordinal: int) -> set[int] | None:
        sums = {0}
        for domain_ordinal, domain in enumerate(domains):
            if domain_ordinal == excluded:
                continue
            values = {item["vector"][component_ordinal] for item in domain}
            sums = {left + right for left in sums for right in values}
            if len(sums) > state_bound:
                return None
        return sums

    changed = True
    while changed:
        changed = False
        for component_ordinal in range(len(axis)):
            complementary = [
                achievable_sums(domain_ordinal, component_ordinal)
                for domain_ordinal in range(len(domains))
            ]
            if any(values is None for values in complementary):
                return None, ["ROW_ALIGNMENT_SOLVER_STATE_BOUND_EXCEEDED"]
            for domain_ordinal, domain in enumerate(domains):
                remaining = complementary[domain_ordinal]
                assert remaining is not None
                filtered = [
                    item
                    for item in domain
                    if target[component_ordinal] - item["vector"][component_ordinal] in remaining
                ]
                if not filtered:
                    return None, ["ROW_ALIGNMENT_HAS_NO_VERTICAL_EXACT_PLACEMENT"]
                if len(filtered) != len(domain):
                    domains[domain_ordinal] = filtered
                    changed = True
    if any(len(domain) != 1 for domain in domains):
        return None, ["ROW_ALIGNMENT_EXACT_PLACEMENT_IS_NOT_UNIQUE"]
    selected = [domain[0] for domain in domains]
    if any(
        sum(item["vector"][component_ordinal] for item in selected) != target[component_ordinal]
        for component_ordinal in range(len(axis))
    ):
        return None, ["ROW_ALIGNMENT_VERTICAL_EXACT_SUM_DRIFTED"]
    rebuilt = canonical_clone_v1(graph)
    receipts = canonical_clone_v1(rebuilt.get("alignment_receipts", []))
    changed_row_count = 0
    for axis_role, candidate in zip(detail_roles, selected, strict=True):
        raw_vector = tuple(
            graph["component_cells"][item["axis_id"]][axis_role]["coefficient"] for item in axis
        )
        if candidate["vector"] != raw_vector:
            changed_row_count += 1
            receipts.append(
                {
                    "assignments": candidate["assignments"],
                    "axis_role": axis_role,
                    "displacement_score": candidate["displacement_score"],
                    "effective_vector": list(candidate["vector"]),
                    "raw_vector": list(raw_vector),
                    "rule": (
                        "UNIQUE_MONOTONE_DIGIT_PRESERVING_ROW_ALIGNMENT_"
                        "HORIZONTAL_AND_VERTICAL_GRAPH_EXACT"
                    ),
                }
            )
        for component, cell in zip(axis, candidate["cells"], strict=True):
            rebuilt["component_cells"][component["axis_id"]][axis_role] = cell
    if changed_row_count == 0:
        return None, ["ROW_ALIGNMENT_DID_NOT_CHANGE_THE_SOURCE_MATRIX"]
    rebuilt["alignment_receipts"] = receipts
    return rebuilt, []


def _mapping_value(
    cell: Mapping[str, Any], *, axis_role: str, equation_multiplier: int = 1
) -> dict[str, Any]:
    state = (
        "INFERRED_BLANK_ZERO_EQUATION_EXACT"
        if cell["state"] == "BLANK_ZERO_IF_EQUATION_EXACT"
        else cell["state"]
    )
    return {
        "axis_role": axis_role,
        "cell_ref": canonical_clone_v1(cell["cell_ref"]),
        "coefficient": cell["coefficient"],
        "equation_multiplier": equation_multiplier,
        "source_text": cell["source_text"],
        "state": state,
    }


def _build_mappings(
    *, graph: Mapping[str, Any], compiled_specs: Mapping[str, Any], unit: str, sign_multiplier: int
) -> list[dict[str, Any]]:
    result = []
    movement_roles = [item["axis_role"] for item in graph["movement_axis"]]
    selected_child_roles = (
        list(_MAPPED_MOVEMENT_ROLES)
        if graph["orientation"] == "COMPONENT_ROWS"
        else [
            "OPENING",
            *[role for role in ("INCREASE", "DECREASE") if role in movement_roles],
            "CLOSING",
        ]
    )
    grand_total = next(item for item in graph["component_axis"] if item["kind"] == "GRAND_TOTAL")
    for axis_role in selected_child_roles:
        if axis_role not in movement_roles:
            continue
        total_role = _MAPPED_TOTAL_ROLES[axis_role]
        cell = graph["component_cells"][grand_total["axis_id"]][axis_role]
        payload = {
            "item_mapping_id": "gjeqmfv1:item:pending",
            "report_norm_id": compiled_specs["movement_total_report_norm_id_by_role"][total_role],
            "role": total_role,
            "row_id": f"movement:{axis_role}",
            "unit": unit,
            "values": [
                _mapping_value(
                    cell,
                    axis_role=axis_role,
                    equation_multiplier=sign_multiplier if axis_role == "DECREASE" else 1,
                )
            ],
        }
        payload["item_mapping_id"] = "gjeqmfv1:item:" + canonical_json_sha256_v1(
            {key: value for key, value in payload.items() if key != "item_mapping_id"}
        )
        result.append(payload)
    for item in graph["component_axis"]:
        if item["kind"] != "MAPPED_COMPONENT":
            continue
        role = item["role"]
        values = [
            _mapping_value(
                graph["component_cells"][item["axis_id"]][axis_role],
                axis_role=axis_role,
                equation_multiplier=sign_multiplier if axis_role == "DECREASE" else 1,
            )
            for axis_role in selected_child_roles
            if axis_role in graph["component_cells"][item["axis_id"]]
        ]
        payload = {
            "component_axis": canonical_clone_v1(item),
            "item_mapping_id": "gjeqmfv1:item:pending",
            "report_norm_id": compiled_specs["component_report_norm_id_by_role"][role],
            "role": role,
            "row_id": f"component:{role}",
            "unit": unit,
            "values": values,
        }
        payload["item_mapping_id"] = "gjeqmfv1:item:" + canonical_json_sha256_v1(
            {key: value for key, value in payload.items() if key != "item_mapping_id"}
        )
        result.append(payload)
    return result


def evaluate_gemini_json_equity_matrix_family_cluster_v1(
    *,
    regions: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
    document_unit_context_evidence: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Evaluate one exact matrix cluster and emit mappings only after closure."""

    checked_regions = _checked_region_axis(regions)
    expected_query = build_gemini_json_equity_matrix_region_query_receipt_v1(
        checked_regions, owner_receipt=query_receipt.get("owner_receipt", {})
    )
    if not same_typed_json_v1(expected_query, query_receipt):
        raise _error("equity-matrix query receipt drifted")
    if (
        type(compiled_specs) is not dict
        or compiled_specs.get("engine_format_version") != ENGINE_FORMAT_VERSION
    ):
        raise _error("equity-matrix compiled specs are invalid")
    tables = []
    classifications = []
    reasons = []
    for region in checked_regions:
        page = page_json_by_version.get(region["page_json_version_id"])
        if type(page) is not dict:
            raise _error("equity-matrix selected canonical page is absent")
        _section, table = _source_table(
            page, section_id=region["section_id"], table_id=region["table_id"]
        )
        classification = classify_gemini_json_equity_matrix_table_v1(
            table, compiled_specs=compiled_specs
        )
        tables.append(table)
        classifications.append(classification)
        reasons.extend(classification["reasons"])
        if classification["status"] != "MATRIX_FRAGMENT":
            reasons.append("SELECTED_FRAGMENT_IS_NOT_ONE_COMPLETE_MATRIX_AXIS")
    unit_receipt, unit_reasons = _resolve_cluster_unit(
        tables=tables,
        compiled_specs=compiled_specs,
        document_unit_context_evidence=document_unit_context_evidence,
    )
    reasons.extend(unit_reasons)
    graph, graph_reasons = _build_matrix_graph(
        regions=checked_regions,
        tables=tables,
        classifications=classifications,
        compiled_specs=compiled_specs,
    )
    reasons.extend(graph_reasons)
    equations = []
    sign_multiplier = 1
    if graph and not graph_reasons:
        equations, equation_reasons, sign_multiplier = _build_equations(graph)
        matrix_mismatch_reasons = {
            "HORIZONTAL_VISIBLE_TOTAL_MISMATCH",
            "VERTICAL_COMPONENT_ROLLFORWARD_MISMATCH",
        }
        if (
            graph["orientation"] == "COMPONENT_COLUMNS"
            and equation_reasons
            and set(equation_reasons) <= matrix_mismatch_reasons
        ):
            aligned_graph, alignment_reasons = _resolve_component_column_row_alignment_v1(graph)
            if aligned_graph is not None:
                aligned_equations, aligned_reasons, aligned_multiplier = _build_equations(
                    aligned_graph
                )
                if not aligned_reasons:
                    graph = aligned_graph
                    equations = aligned_equations
                    sign_multiplier = aligned_multiplier
                    equation_reasons = []
            else:
                equation_reasons = sorted(set(equation_reasons) | set(alignment_reasons))
        reasons.extend(equation_reasons)
    reasons = sorted(set(reasons))
    mappings = (
        _build_mappings(
            graph=graph,
            compiled_specs=compiled_specs,
            unit=unit_receipt["canonical_unit"],
            sign_multiplier=sign_multiplier,
        )
        if not reasons and graph and unit_receipt["canonical_unit"] is not None
        else []
    )
    first = checked_regions[0]
    status = READY if mappings and not reasons else UNRESOLVED
    closure_receipt = {
        "alignment_receipts": canonical_clone_v1(graph.get("alignment_receipts", [])),
        "component_axis": canonical_clone_v1(graph.get("component_axis", [])),
        "equations": equations,
        "movement_axis": canonical_clone_v1(graph.get("movement_axis", [])),
        "orientation": graph.get("orientation"),
        "period_block_receipt": canonical_clone_v1(graph.get("period_block_receipt")),
        "query_receipt": canonical_clone_v1(query_receipt),
        "rule": (
            "COMPLETE_BIDIRECTIONAL_MATRIX_HORIZONTAL_HIERARCHY_AND_VERTICAL_"
            "ROLLFORWARD_EXACT_BEFORE_SCHEMA_MAPPING"
        ),
        "source_only_component_axes": [
            canonical_clone_v1(item)
            for item in graph.get("component_axis", [])
            if item["kind"] == "SOURCE_ONLY_COMPONENT"
        ],
        "unit_receipt": unit_receipt,
    }
    candidate = {
        "candidate_id": "gjeqmfv1:candidate:pending",
        "claim_boundary": CLAIM_BOUNDARY,
        "closure_receipt": closure_receipt,
        "component_regions": checked_regions,
        "document_id": first["document_id"],
        "family_id": compiled_specs["family_id"],
        "mappings": mappings,
        "page_json_version_id": first["page_json_version_id"],
        "physical_page": first["physical_page"],
        "reasons": reasons,
        "section_id": first["section_id"],
        "source_logical_name": first["source_logical_name"],
        "source_sha256": first["source_sha256"],
        "status": status,
        "table_id": first["table_id"],
    }
    candidate["candidate_id"] = "gjeqmfv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in candidate.items() if key != "candidate_id"}
    )
    return candidate


def validate_gemini_json_equity_matrix_family_candidate_replay_v1(
    value: Any,
    *,
    regions: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
    document_unit_context_evidence: Mapping[str, Any] | None,
) -> dict[str, Any]:
    expected = evaluate_gemini_json_equity_matrix_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
        document_unit_context_evidence=document_unit_context_evidence,
    )
    if not same_typed_json_v1(value, expected):
        raise _error("equity-matrix candidate does not replay from selected canonical JSON")
    return expected


def _selected_page_record_axis(page_records: Any) -> list[dict[str, Any]]:
    fields = {
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
        raise _error("equity-matrix selected page records are absent")
    checked = []
    identity = None
    prior = None
    for record in page_records:
        if (
            type(record) is not dict
            or set(record) != fields
            or _DOCUMENT_ID.fullmatch(record.get("document_id", "")) is None
            or type(record.get("document_ordinal")) is not int
            or record["document_ordinal"] <= 0
            or _PAGE_VERSION.fullmatch(record.get("page_json_version_id", "")) is None
            or type(record.get("physical_page")) is not int
            or record["physical_page"] <= 0
            or type(record.get("selected_page_ordinal")) is not int
            or record["selected_page_ordinal"] <= 0
            or type(record.get("source_logical_name")) is not str
            or not record["source_logical_name"]
            or _SHA256.fullmatch(record.get("source_sha256", "")) is None
            or type(record.get("page_json")) is not dict
            or type(record["page_json"].get("sections")) is not list
        ):
            raise _error("equity-matrix selected page record is invalid")
        current_identity = tuple(
            record[key]
            for key in (
                "document_id",
                "document_ordinal",
                "source_logical_name",
                "source_sha256",
            )
        )
        position = (record["selected_page_ordinal"], record["physical_page"])
        if identity is None:
            identity = current_identity
        elif current_identity != identity:
            raise _error("equity-matrix selected pages cross document identity")
        if prior is not None and position <= prior:
            raise _error("equity-matrix selected pages are not in source order")
        prior = position
        checked.append(canonical_clone_v1(record))
    return checked


def _contained_declared_alias(value: Any, aliases: Sequence[str]) -> str | None:
    folded = _normalized(value)
    matches = [
        alias
        for alias in aliases
        if re.search(
            rf"(?<![a-z0-9]){re.escape(_normalized(alias))}(?![a-z0-9])",
            folded,
        )
    ]
    if not matches:
        return None
    maximum = max(len(_normalized(alias)) for alias in matches)
    winners = sorted(alias for alias in matches if len(_normalized(alias)) == maximum)
    # Every alias in one call denotes the same typed marker role.  Multiple
    # owner spellings on a heading (for example both ``Vốn và các quỹ`` and
    # ``vốn chủ sở hữu``) corroborate rather than conflict.  Seal the
    # deterministic longest/lexical representative.
    return winners[0]


def _document_unit_context_v1(
    pages: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    evidence = []
    for record in pages:
        for section_ordinal, section in enumerate(record["page_json"]["sections"], start=1):
            if type(section) is not dict or type(section.get("tables")) is not list:
                continue
            for table_ordinal, table in enumerate(section["tables"], start=1):
                if type(table) is not dict or type(table.get("unit_exact")) is not str:
                    continue
                occurrences = _unit_occurrences(table["unit_exact"], compiled_specs=compiled_specs)
                identities = {
                    (item["canonical_unit"], item["magnitude_power10"])
                    for item in occurrences
                    if compiled_specs["unit_binding_by_alias"][item["matched_alias"]][
                        "document_consensus_eligible"
                    ]
                }
                if len(identities) != 1:
                    continue
                canonical_unit, magnitude = next(iter(identities))
                evidence.append(
                    {
                        "canonical_unit": canonical_unit,
                        "magnitude_power10": magnitude,
                        "page_json_version_id": record["page_json_version_id"],
                        "physical_page": record["physical_page"],
                        "section_id": f"s{section_ordinal}",
                        "source_exact": table["unit_exact"],
                        "source_kind": "TABLE_UNIT",
                        "table_id": f"t{table_ordinal}",
                    }
                )
    identities = {(item["canonical_unit"], item["magnitude_power10"]) for item in evidence}
    distinct_pages = {(item["page_json_version_id"], item["physical_page"]) for item in evidence}
    canonical_unit = next(iter(identities))[0] if len(identities) == 1 else None
    status = (
        "UNIQUE_AUTHENTICATED_DOCUMENT_MONEY_UNIT_CONSENSUS"
        if len(identities) == 1 and len(distinct_pages) >= 2
        else "CONFLICTING_DOCUMENT_MONEY_UNIT_CONTEXT"
        if len(identities) > 1
        else "INSUFFICIENT_DOCUMENT_MONEY_UNIT_CONTEXT"
    )
    material = {
        "canonical_unit": canonical_unit,
        "distinct_page_count": len(distinct_pages),
        "evidence": evidence,
        "evidence_axis_sha256": canonical_json_sha256_v1(evidence),
        "status": status,
    }
    return {
        **material,
        "document_unit_context_sha256": canonical_json_sha256_v1(material),
    }


def _matrix_region(item: Mapping[str, Any], *, fragment_ordinal: int) -> dict[str, Any]:
    record = item["record"]
    return {
        "document_id": record["document_id"],
        "document_ordinal": record["document_ordinal"],
        "page_json_version_id": record["page_json_version_id"],
        "physical_page": record["physical_page"],
        "selected_page_ordinal": record["selected_page_ordinal"],
        "section_id": item["section_id"],
        "source_logical_name": record["source_logical_name"],
        "source_sha256": record["source_sha256"],
        "table_id": item["table_id"],
    }


def coalesce_gemini_json_equity_matrix_document_v1(
    *, page_records: Any, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Select one complete matrix under one bounded owner/reset fence."""

    pages = _selected_page_record_axis(page_records)
    inventory = []
    owner_markers = []
    reset_markers = []
    for record in pages:
        for section_ordinal, section in enumerate(record["page_json"]["sections"], start=1):
            if type(section) is not dict:
                continue
            section_id = f"s{section_ordinal}"
            section_values = [section.get("title_exact")]
            if type(section.get("narratives_exact")) is list:
                section_values.extend(section["narratives_exact"])
            for source_exact in section_values:
                position = [record["selected_page_ordinal"], section_ordinal, 0]
                owner = _contained_declared_alias(
                    source_exact, compiled_specs["query_policy"]["owner_aliases"]
                )
                reset = _contained_declared_alias(
                    source_exact,
                    [
                        *compiled_specs["query_policy"]["reset_aliases"],
                        *compiled_specs["query_policy"]["hard_negative_aliases"],
                    ],
                )
                if owner is not None:
                    owner_markers.append(
                        {"alias": owner, "position": position, "source_exact": source_exact}
                    )
                if reset is not None:
                    reset_markers.append(
                        {"alias": reset, "position": position, "source_exact": source_exact}
                    )
            tables = section.get("tables")
            if type(tables) is not list:
                continue
            for table_ordinal, table in enumerate(tables, start=1):
                if type(table) is not dict:
                    continue
                table_id = f"t{table_ordinal}"
                position = [
                    record["selected_page_ordinal"],
                    section_ordinal,
                    table_ordinal,
                ]
                for source_exact in [table.get("title_exact")]:
                    owner = _contained_declared_alias(
                        source_exact, compiled_specs["query_policy"]["owner_aliases"]
                    )
                    reset = _contained_declared_alias(
                        source_exact,
                        [
                            *compiled_specs["query_policy"]["reset_aliases"],
                            *compiled_specs["query_policy"]["hard_negative_aliases"],
                        ],
                    )
                    if owner is not None:
                        owner_markers.append(
                            {
                                "alias": owner,
                                "position": position,
                                "source_exact": source_exact,
                            }
                        )
                    if reset is not None:
                        reset_markers.append(
                            {
                                "alias": reset,
                                "position": position,
                                "source_exact": source_exact,
                            }
                        )
                classification = classify_gemini_json_equity_matrix_table_v1(
                    table, compiled_specs=compiled_specs
                )
                if (
                    classification["row_declared_component_roles"]
                    or classification["column_declared_component_roles"]
                ):
                    inventory.append(
                        {
                            "classification": classification,
                            "position": position,
                            "record": record,
                            "section_id": section_id,
                            "table_id": table_id,
                        }
                    )
    selected = [item for item in inventory if item["classification"]["status"] == "MATRIX_FRAGMENT"]
    reasons = []
    owner_receipt = None
    if selected:
        first_position = min(item["position"] for item in selected)
        last_position = max(item["position"] for item in selected)
        if len(selected) > 2:
            reasons.append("MORE_THAN_TWO_MATRIX_FRAGMENTS_UNDER_DOCUMENT_OWNER")
        if (
            last_position[0] - first_position[0]
            > compiled_specs["query_policy"]["max_continuation_pages"]
        ):
            reasons.append("MATRIX_FRAGMENT_SPAN_EXCEEDS_DECLARED_BOUND")
        prior_owners = [
            marker
            for marker in owner_markers
            if marker["position"] <= first_position
            and first_position[0] - marker["position"][0]
            <= compiled_specs["query_policy"]["max_continuation_pages"]
        ]
        if not prior_owners:
            reasons.append("EXPLICIT_BOUNDED_MATRIX_OWNER_NOT_VISIBLE")
        else:
            owner = max(prior_owners, key=lambda item: item["position"])
            fenced_resets = [
                marker
                for marker in reset_markers
                if owner["position"] < marker["position"] <= last_position
            ]
            if fenced_resets:
                reasons.append("OWNER_TO_MATRIX_INTERVAL_CONTAINS_RESET_OR_HARD_NEGATIVE")
            owner_receipt = {
                "owner_alias": owner["alias"],
                "owner_position": owner["position"],
                "owner_source_exact": owner["source_exact"],
                "reset_fence_axis": fenced_resets,
                "rule": "LATEST_EXPLICIT_OWNER_WITHIN_ONE_PAGE_RESET_FREE_INTERVAL",
            }
            selected_keys = {
                (
                    item["record"]["page_json_version_id"],
                    item["section_id"],
                    item["table_id"],
                )
                for item in selected
            }
            max_scope_page = (
                first_position[0] + compiled_specs["query_policy"]["max_continuation_pages"]
            )
            unconsumed = [
                item
                for item in inventory
                if owner["position"] <= item["position"]
                and item["position"][0] <= max_scope_page
                and not any(
                    owner["position"] < marker["position"] <= item["position"]
                    or (
                        marker["position"][:2] == item["position"][:2]
                        and marker["position"][2] == 0
                        and any(
                            selected_item["position"][:2] == item["position"][:2]
                            and 0 < selected_item["position"][2] < item["position"][2]
                            for selected_item in selected
                        )
                    )
                    for marker in reset_markers
                )
                and (
                    item["record"]["page_json_version_id"],
                    item["section_id"],
                    item["table_id"],
                )
                not in selected_keys
            ]
            if unconsumed:
                reasons.append("UNCONSUMED_DECLARED_COMPONENT_EVIDENCE_IN_OWNER_INTERVAL")
    regions = [
        _matrix_region(item, fragment_ordinal=ordinal)
        for ordinal, item in enumerate(selected, start=1)
    ]
    if regions:
        try:
            _checked_region_axis(regions)
        except GeminiJsonEquityMatrixAccountingFamilyV1Error:
            reasons.append("MATRIX_REGION_AXIS_IS_NOT_ONE_OR_TWO_ADJACENT_FRAGMENTS")
    inventory_receipt = [
        {
            "classification": canonical_clone_v1(item["classification"]),
            "disposition": (
                "SELECTED_MATRIX_FRAGMENT" if item in selected else "UNSELECTED_DECLARED_ROLE_TABLE"
            ),
            "page_json_version_id": item["record"]["page_json_version_id"],
            "physical_page": item["record"]["physical_page"],
            "position": item["position"],
            "section_id": item["section_id"],
            "table_id": item["table_id"],
        }
        for item in inventory
    ]
    unit_context = _document_unit_context_v1(pages, compiled_specs=compiled_specs)
    first = pages[0]
    status = (
        NOT_OBSERVED
        if not selected and not inventory
        else READY
        if selected and not reasons and owner_receipt is not None
        else UNRESOLVED
    )
    material = {
        "component_regions": regions if status == READY else [],
        "declared_table_inventory": inventory_receipt,
        "document_id": first["document_id"],
        "document_ordinal": first["document_ordinal"],
        "document_unit_context_evidence": unit_context,
        "owner_receipt": owner_receipt,
        "reasons": sorted(set(reasons)),
        "source_logical_name": first["source_logical_name"],
        "source_sha256": first["source_sha256"],
        "status": status,
    }
    return {
        "cluster_id": "gjeqmfv1:cluster:" + canonical_json_sha256_v1(material),
        **material,
    }


def build_gemini_json_indexed_equity_matrix_query_evidence_v1(
    *,
    selected_document_axis: Sequence[dict[str, Any]],
    selected_page_axis: Sequence[dict[str, Any]],
    document_clusters: Sequence[dict[str, Any]],
    query_policy_sha256: str,
) -> dict[str, Any]:
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
        "query_evidence_id": "gjeqmfv1:evidence:" + canonical_json_sha256_v1(material),
    }


def validate_gemini_json_indexed_equity_matrix_query_evidence_v1(
    value: Any, *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
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
        raise _error("indexed equity-matrix query evidence is invalid")
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
        raise _error("indexed equity-matrix document axis is incomplete")
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
            raise _error("indexed equity-matrix selected document axis is invalid")
        by_ordinal[ordinal] = document
    page_fields = document_fields | {
        "page_json_version_id",
        "physical_page",
        "selected_page_ordinal",
    }
    per_document: dict[int, int] = {}
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
            raise _error("indexed equity-matrix selected page axis is invalid")
        prior_document = page["document_ordinal"]
        per_document[page["document_ordinal"]] = per_document.get(page["document_ordinal"], 0) + 1
        if page.get("selected_page_ordinal") != per_document[page["document_ordinal"]]:
            raise _error("indexed equity-matrix selected page order is incomplete")
        page_versions.append(page["page_json_version_id"])
    if len(page_versions) != len(set(page_versions)) or set(per_document) != set(by_ordinal):
        raise _error("indexed equity-matrix page frontier is duplicate or incomplete")
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
            != "gjeqmfv1:cluster:"
            + canonical_json_sha256_v1(
                {key: item for key, item in cluster.items() if key != "cluster_id"}
            )
        ):
            raise _error("indexed equity-matrix cluster binding drifted")
        regions = cluster.get("component_regions")
        reasons = cluster.get("reasons")
        if (
            type(reasons) is not list
            or reasons != sorted(set(reasons))
            or type(cluster.get("document_unit_context_evidence")) is not dict
            or (cluster["status"] == READY and (not regions or reasons))
            or (cluster["status"] == NOT_OBSERVED and regions)
            or (cluster["status"] == UNRESOLVED and (not reasons or regions))
        ):
            raise _error("indexed equity-matrix disposition semantics drifted")
        if cluster["status"] == READY:
            _checked_region_axis(regions)
            accepted.append(cluster)
    if not same_typed_json_v1(value["accepted_clusters"], accepted):
        raise _error("indexed equity-matrix accepted projection drifted")
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
        raise _error("indexed equity-matrix query receipt drifted")
    material = {key: canonical_clone_v1(value[key]) for key in fields - {"query_evidence_id"}}
    if value["query_evidence_id"] != "gjeqmfv1:evidence:" + canonical_json_sha256_v1(material):
        raise _error("indexed equity-matrix query evidence identity drifted")
    return canonical_clone_v1(value)


def validate_gemini_json_equity_matrix_sweep_query_bindings_v1(
    *, trials: Any, indexed_query_evidence: Any, compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    evidence = validate_gemini_json_indexed_equity_matrix_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
    documents = evidence["selected_document_axis"]
    if type(trials) is not list or len(trials) != len(documents):
        raise _error("equity-matrix sweep trial axis is incomplete")
    accepted = {item["document_ordinal"]: item for item in evidence["accepted_clusters"]}
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
        "alignment_receipts",
        "component_axis",
        "equations",
        "movement_axis",
        "orientation",
        "period_block_receipt",
        "query_receipt",
        "rule",
        "source_only_component_axes",
        "unit_receipt",
    }
    mapping_fields = {
        "item_mapping_id",
        "report_norm_id",
        "role",
        "row_id",
        "unit",
        "values",
    }
    value_fields = {
        "axis_role",
        "cell_ref",
        "coefficient",
        "equation_multiplier",
        "source_text",
        "state",
    }

    def validate_candidate(
        candidate: Any, *, document: Mapping[str, Any], cluster: Mapping[str, Any]
    ) -> dict[str, Any]:
        regions = cluster["component_regions"]
        first = regions[0]
        closure = candidate.get("closure_receipt") if type(candidate) is dict else None
        if (
            type(candidate) is not dict
            or set(candidate) != candidate_fields
            or candidate.get("claim_boundary") != CLAIM_BOUNDARY
            or candidate.get("family_id") != compiled_specs["family_id"]
            or candidate.get("document_id") != first["document_id"]
            or candidate.get("page_json_version_id") != first["page_json_version_id"]
            or candidate.get("physical_page") != first["physical_page"]
            or candidate.get("section_id") != first["section_id"]
            or candidate.get("table_id") != first["table_id"]
            or candidate.get("source_logical_name") != document["source_logical_name"]
            or candidate.get("source_sha256") != document["source_sha256"]
            or not same_typed_json_v1(candidate.get("component_regions"), regions)
            or candidate.get("status") not in {READY, UNRESOLVED}
            or type(candidate.get("reasons")) is not list
            or candidate["reasons"] != sorted(set(candidate["reasons"]))
            or type(candidate.get("mappings")) is not list
            or type(closure) is not dict
            or set(closure) != closure_fields
            or closure.get("orientation") not in {"COMPONENT_COLUMNS", "COMPONENT_ROWS"}
            or type(closure.get("component_axis")) is not list
            or type(closure.get("movement_axis")) is not list
            or type(closure.get("equations")) is not list
            or type(closure.get("alignment_receipts")) is not list
            or type(closure.get("source_only_component_axes")) is not list
            or type(closure.get("unit_receipt")) is not dict
            or (
                closure["orientation"] == "COMPONENT_COLUMNS"
                and type(closure.get("period_block_receipt")) is not dict
            )
            or (
                closure["orientation"] == "COMPONENT_ROWS"
                and closure.get("period_block_receipt") is not None
            )
        ):
            raise _error("equity-matrix candidate structure drifted")
        expected_query = build_gemini_json_equity_matrix_region_query_receipt_v1(
            regions, owner_receipt=cluster["owner_receipt"]
        )
        if not same_typed_json_v1(closure["query_receipt"], expected_query):
            raise _error("equity-matrix candidate query receipt drifted")
        material = {key: value for key, value in candidate.items() if key != "candidate_id"}
        if candidate["candidate_id"] != "gjeqmfv1:candidate:" + canonical_json_sha256_v1(material):
            raise _error("equity-matrix candidate identity drifted")
        component_axis = closure["component_axis"]
        mapped_components = {
            item.get("role"): item
            for item in component_axis
            if type(item) is dict and item.get("kind") == "MAPPED_COMPONENT"
        }
        if (
            None in mapped_components
            or len(mapped_components)
            != sum(
                type(item) is dict and item.get("kind") == "MAPPED_COMPONENT"
                for item in component_axis
            )
            or sum(
                type(item) is dict and item.get("kind") == "GRAND_TOTAL" for item in component_axis
            )
            != 1
        ):
            raise _error("equity-matrix candidate component axis drifted")
        movement_roles = [
            item.get("axis_role") for item in closure["movement_axis"] if type(item) is dict
        ]
        expected_axis_roles = (
            list(_MAPPED_MOVEMENT_ROLES)
            if closure["orientation"] == "COMPONENT_ROWS"
            else [
                "OPENING",
                *[role for role in ("INCREASE", "DECREASE") if role in movement_roles],
                "CLOSING",
            ]
        )
        expected_total_roles = {_MAPPED_TOTAL_ROLES[role] for role in expected_axis_roles}
        expected_roles = set(mapped_components) | expected_total_roles
        canonical_unit = closure["unit_receipt"].get("canonical_unit")
        seen_roles = set()
        region_hashes = {canonical_json_sha256_v1(item) for item in regions}
        for mapping in candidate["mappings"]:
            role = mapping.get("role") if type(mapping) is dict else None
            fields = mapping_fields | ({"component_axis"} if role in mapped_components else set())
            values = mapping.get("values") if type(mapping) is dict else None
            expected_rnid = (
                compiled_specs["component_report_norm_id_by_role"].get(role)
                if role in mapped_components
                else compiled_specs["movement_total_report_norm_id_by_role"].get(role)
            )
            if (
                type(mapping) is not dict
                or set(mapping) != fields
                or role not in expected_roles
                or role in seen_roles
                or mapping.get("report_norm_id") != expected_rnid
                or mapping.get("unit") != canonical_unit
                or type(values) is not list
                or not values
                or (
                    role in mapped_components
                    and (
                        mapping.get("row_id") != f"component:{role}"
                        or not same_typed_json_v1(
                            mapping.get("component_axis"), mapped_components[role]
                        )
                    )
                )
                or (
                    role in expected_total_roles
                    and mapping.get("row_id")
                    != f"movement:{next(key for key, value in _MAPPED_TOTAL_ROLES.items() if value == role)}"
                )
            ):
                raise _error("equity-matrix mapping schema binding drifted")
            seen_roles.add(role)
            mapping_material = {
                key: value for key, value in mapping.items() if key != "item_mapping_id"
            }
            if mapping["item_mapping_id"] != "gjeqmfv1:item:" + canonical_json_sha256_v1(
                mapping_material
            ):
                raise _error("equity-matrix mapping identity drifted")
            for value in values:
                cell_ref = value.get("cell_ref") if type(value) is dict else None
                if (
                    type(value) is not dict
                    or set(value) != value_fields
                    or value.get("axis_role") not in _MAPPED_MOVEMENT_ROLES
                    or type(value.get("coefficient")) is not int
                    or type(value.get("equation_multiplier")) is not int
                    or type(value.get("state")) is not str
                    or not value["state"]
                    or value.get("source_text") is not None
                    and type(value["source_text"]) is not str
                    or type(cell_ref) is not dict
                    or set(cell_ref) != {"column_id", "locator", "row_id"}
                    or _COLUMN_ID.fullmatch(cell_ref.get("column_id", "")) is None
                    or _ROW_ID.fullmatch(cell_ref.get("row_id", "")) is None
                    or type(cell_ref.get("locator")) is not dict
                    or canonical_json_sha256_v1(cell_ref["locator"]) not in region_hashes
                ):
                    raise _error("equity-matrix mapping value provenance drifted")
            expected_mapping_axis = (
                [next(key for key, value in _MAPPED_TOTAL_ROLES.items() if value == role)]
                if role in expected_total_roles
                else expected_axis_roles
            )
            if [value["axis_role"] for value in values] != expected_mapping_axis:
                raise _error("equity-matrix mapping movement axis drifted")
        if candidate["status"] == READY:
            if candidate["reasons"] or seen_roles != expected_roles or canonical_unit is None:
                raise _error("equity-matrix READY candidate semantics drifted")
        elif candidate["mappings"] or not candidate["reasons"]:
            raise _error("equity-matrix unresolved candidate semantics drifted")
        return candidate

    for ordinal, (trial, document, disposition) in enumerate(
        zip(trials, documents, evidence["candidate_dispositions"], strict=True), start=1
    ):
        if (
            type(trial) is not dict
            or set(trial) != trial_fields
            or trial.get("document_ordinal") != ordinal
            or trial.get("source_logical_name") != document["source_logical_name"]
            or trial.get("source_sha256") != document["source_sha256"]
            or type(trial.get("candidates")) is not list
            or trial.get("candidate_count") != len(trial["candidates"])
            or type(trial.get("mappings")) is not list
            or type(trial.get("reasons")) is not list
            or trial["reasons"] != sorted(set(trial["reasons"]))
            or trial.get("status") not in {READY, NOT_OBSERVED, UNRESOLVED}
        ):
            raise _error("equity-matrix sweep trial identity drifted")
        if disposition["disposition"] == READY:
            if len(trial["candidates"]) != 1:
                raise _error("equity-matrix accepted document needs exactly one candidate")
            candidate = validate_candidate(
                trial["candidates"][0], document=document, cluster=accepted[ordinal]
            )
            if not same_typed_json_v1(
                candidate.get("component_regions"), accepted[ordinal]["component_regions"]
            ):
                raise _error("equity-matrix candidate region binding drifted")
            if candidate.get("status") == READY:
                if (
                    trial.get("status") != READY
                    or trial.get("selected_candidate_id") != candidate.get("candidate_id")
                    or not same_typed_json_v1(trial.get("mappings"), candidate.get("mappings"))
                    or trial.get("reasons")
                ):
                    raise _error("equity-matrix READY trial binding drifted")
            elif (
                trial.get("status") != UNRESOLVED
                or trial.get("selected_candidate_id") is not None
                or trial.get("mappings")
                or trial.get("reasons") != candidate.get("reasons")
            ):
                raise _error("equity-matrix unresolved candidate binding drifted")
        elif disposition["disposition"] == NOT_OBSERVED:
            if (
                trial.get("status") != NOT_OBSERVED
                or trial["candidates"]
                or trial.get("mappings")
                or trial.get("reasons")
                or trial.get("selected_candidate_id") is not None
            ):
                raise _error("equity-matrix not-observed trial binding drifted")
        elif (
            trial.get("status") != UNRESOLVED
            or trial["candidates"]
            or trial.get("mappings")
            or trial.get("selected_candidate_id") is not None
            or trial.get("reasons") != disposition["cluster"]["reasons"]
        ):
            raise _error("equity-matrix unresolved query disposition binding drifted")
    return canonical_clone_v1(trials)
