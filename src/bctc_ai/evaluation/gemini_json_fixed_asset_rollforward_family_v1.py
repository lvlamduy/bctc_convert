"""Generic fixed-asset roll-forward over selected Gemini page JSON.

Gemini is only the source reader.  Deterministic code inventories every
family-bearing table, selects the unique current presentation, normalizes the
row hierarchy, proves each horizontal total, seals a bounded right-edge total
shift only through all affected equations, collapses visible subtotal blocks,
and closes every declared signed branch plus any declared carrying-value
control equation.  The primitive
contains no bank, filename, note, page, value, or prompt route.

The engine is intentionally family-parameterized.  Tangible, leased and
intangible fixed-asset families can provide different aliases and schema IDs
without changing the algorithm or the provider prompt boundary.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from bctc_ai.evaluation.accounting_family_topology_v1 import (
    compile_accounting_family_topology_spec_v1,
)
from bctc_ai.evaluation.accounting_row_width_total_column_seal_v1 import (
    build_accounting_equation_inventory_manifest_v1,
    build_accounting_row_width_total_column_seal_v1,
)
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.evaluation.gemini_json_customer_deposit_family_v1 import _source_table
from bctc_ai.evaluation.ordered_visible_subtotal_block_collapse_v1 import (
    build_ordered_visible_subtotal_block_collapse_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

ENGINE_FORMAT_VERSION = "GEMINI_JSON_FIXED_ASSET_ROLLFORWARD_ACCOUNTING_FAMILY_V1"
INDEXED_QUERY_EVIDENCE_FORMAT_VERSION = (
    "GEMINI_JSON_INDEXED_FIXED_ASSET_ROLLFORWARD_QUERY_EVIDENCE_V1"
)
EVALUATION_FORMAT_VERSION = "ACCOUNTING_FIXED_ASSET_ROLLFORWARD_FAMILY_EVALUATION_SPEC_V1"
SCHEMA_FORMAT_VERSION = "ACCOUNTING_FIXED_ASSET_ROLLFORWARD_SCHEMA_BINDING_SPEC_V1"
READY = "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
NOT_OBSERVED = "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
UNRESOLVED = "UNRESOLVED_GEMINI_JSON_FAMILY"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_DECLARATIVE_FIXED_ASSET_OWNER_HEADER_"
    "CONFIGURED_BRANCH_CURRENT_PERIOD_TOTAL_COLUMN_ALL_ROW_HORIZONTAL_SIGNED_"
    "BRANCH_OPTIONAL_CARRYING_CONTROL_VISIBLE_SUBTOTAL_AND_UNIQUE_ALL_EQUATION_"
    "WIDTH_SEAL_SCHEMA_"
    "MAPPING_PROPOSAL_ONLY_NO_GEOMETRY_OCR_BANK_FILE_PAGE_NOTE_VALUE_OR_PROMPT_"
    "ROUTING_CANONICAL_SQLITE_QUERY_AND_CANDIDATE_REPLAY_REQUIRED_FOR_PERSISTENCE"
)

_PAGE_VERSION = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_DOCUMENT_ID = re.compile(r"gfpstorev1:document:[0-9a-f]{64}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SECTION_ID = re.compile(r"s[1-9][0-9]*\Z")
_TABLE_ID = re.compile(r"t[1-9][0-9]*\Z")
_DATE_DMY = re.compile(
    r"(?<!\d)([0-3]?\d)(?:[./-]|\s+(?:thang\s+)?)"
    r"([01]?\d)(?:[./-]|\s+(?:nam\s+)?)((?:19|20)\d{2})(?!\d)"
)
_DASHES = {"-", "_", "–", "—", "−"}
_BRANCH_KINDS = {"SIGNED_ADDITIVE", "COST_AND_DEPRECIATION_CONTROL"}
_CLOSURE_POLICIES = {
    "ALL_SOURCE_ROWS_HORIZONTAL_PLUS_SIGNED_BRANCH_AND_CARRYING_EQUATIONS_EXACT",
    "ALL_SOURCE_ROWS_HORIZONTAL_PLUS_SIGNED_BRANCH_EQUATIONS_EXACT_WITH_OPTIONAL_CARRYING_CONTROL",
}


class GeminiJsonFixedAssetRollforwardFamilyV1Error(ValueError):
    """The selected JSON, declarative triplet, or exact closure drifted."""


def _error(message: str) -> GeminiJsonFixedAssetRollforwardFamilyV1Error:
    return GeminiJsonFixedAssetRollforwardFamilyV1Error(message)


def _normalized(value: Any) -> str:
    if type(value) is not str:
        return ""
    return normalize_vietnamese_anchor_v1(value)


def _normalized_aliases(value: Any, *, label: str) -> list[str]:
    if (
        type(value) is not list
        or not value
        or any(type(item) is not str or not item.strip() for item in value)
    ):
        raise _error(f"fixed-asset {label} aliases are invalid")
    aliases = [_normalized(item) for item in value]
    if any(not item for item in aliases) or len(aliases) != len(set(aliases)):
        raise _error(f"fixed-asset {label} aliases collide")
    return aliases


def _aliases(child: Mapping[str, Any]) -> list[str]:
    return sorted(
        {_normalized(alias) for matcher in child["matchers"] for alias in matcher["aliases"]}
    )


def _compile_units(value: Any) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if type(value) is not list or not value:
        raise _error("fixed-asset unit bindings are absent")
    bindings = []
    by_alias: dict[str, dict[str, Any]] = {}
    canonical_units: set[str] = set()
    for raw in value:
        if (
            type(raw) is not dict
            or set(raw) != {"accepted", "aliases", "canonical_unit", "magnitude_power10"}
            or type(raw["accepted"]) is not bool
            or type(raw["canonical_unit"]) is not str
            or not raw["canonical_unit"]
            or raw["canonical_unit"] in canonical_units
            or type(raw["magnitude_power10"]) is not int
            or raw["magnitude_power10"] < 0
        ):
            raise _error("fixed-asset unit binding drifted")
        canonical_units.add(raw["canonical_unit"])
        aliases = _normalized_aliases(raw["aliases"], label=raw["canonical_unit"])
        binding = {**canonical_clone_v1(raw), "aliases": aliases}
        bindings.append(binding)
        for alias in aliases:
            if alias in by_alias:
                raise _error("fixed-asset unit aliases collide")
            by_alias[alias] = binding
    if not any(item["accepted"] for item in bindings):
        raise _error("fixed-asset needs one accepted money unit")
    return bindings, by_alias


def compile_gemini_json_fixed_asset_rollforward_family_specs_v1(
    topology_spec: Any, evaluation_spec: Any, schema_binding_spec: Any
) -> dict[str, Any]:
    """Compile one data-only fixed-asset family triplet."""

    try:
        topology = compile_accounting_family_topology_spec_v1(topology_spec)
    except ValueError as exc:
        raise _error("fixed-asset topology spec is invalid") from exc
    evaluation_fields = {
        "asset_header_aliases",
        "branch_layouts",
        "closure_policy",
        "family_id",
        "format_version",
        "header_hard_negative_aliases",
        "layout_policy",
        "minimum_distinct_asset_header_aliases",
        "money_unit_bindings",
        "period_policy",
        "row_width_policy",
        "subtotal_policy",
        "total_column_aliases",
    }
    if (
        type(evaluation_spec) is not dict
        or set(evaluation_spec) != evaluation_fields
        or evaluation_spec.get("format_version") != EVALUATION_FORMAT_VERSION
        or evaluation_spec.get("family_id") != topology["family_id"]
        or evaluation_spec.get("closure_policy") not in _CLOSURE_POLICIES
        or evaluation_spec.get("layout_policy")
        != "ONE_CURRENT_TOTAL_COLUMN_TABLE_WITH_OPTIONAL_TYPED_COMPARATIVE_CONTROL_TABLES"
        or evaluation_spec.get("period_policy")
        != "UNIQUE_SOURCE_VISIBLE_OR_TYPED_DOCUMENT_REPORTING_DATE_WITH_COMPARATIVE_ENDPOINT_CONTINUITY"
        or evaluation_spec.get("row_width_policy")
        != "UNIQUE_RIGHT_EDGE_TOTAL_WITH_ALL_EQUATION_SEALED_RELOCATION_ONLY"
        or evaluation_spec.get("subtotal_policy")
        != "VISIBLE_SUBTOTAL_AND_DIRECT_CHILDREN_COEXIST_BUT_VERTICAL_CONSUMES_EXACTLY_ONE_FRONTIER"
        or type(evaluation_spec.get("minimum_distinct_asset_header_aliases")) is not int
        or evaluation_spec["minimum_distinct_asset_header_aliases"] < 1
    ):
        raise _error("fixed-asset evaluation spec is invalid")
    asset_aliases = _normalized_aliases(
        evaluation_spec["asset_header_aliases"], label="asset header"
    )
    hard_negative_aliases = _normalized_aliases(
        evaluation_spec["header_hard_negative_aliases"], label="header hard-negative"
    )
    total_aliases = _normalized_aliases(
        evaluation_spec["total_column_aliases"], label="total column"
    )
    units, unit_by_alias = _compile_units(evaluation_spec["money_unit_bindings"])
    child_by_role = {child["role"]: child for child in topology["children"]}
    branch_layouts = []
    branch_roles: set[str] = set()
    endpoint_roles: set[str] = set()
    subtotal_roles: set[str] = set()
    for raw in evaluation_spec["branch_layouts"]:
        if (
            type(raw) is not dict
            or set(raw)
            != {
                "branch_role",
                "ending_role",
                "hierarchy_aliases",
                "opening_role",
                "rollforward_kind",
                "subtotal_roles",
            }
            or raw["branch_role"] not in child_by_role
            or raw["branch_role"] in branch_roles
            or raw["opening_role"] not in child_by_role
            or raw["ending_role"] not in child_by_role
            or raw["opening_role"] in endpoint_roles
            or raw["ending_role"] in endpoint_roles
            or raw["rollforward_kind"] not in _BRANCH_KINDS
            or type(raw["subtotal_roles"]) is not list
            or any(role not in child_by_role for role in raw["subtotal_roles"])
        ):
            raise _error("fixed-asset branch layout drifted")
        branch_roles.add(raw["branch_role"])
        endpoint_roles.update((raw["opening_role"], raw["ending_role"]))
        subtotal_roles.update(raw["subtotal_roles"])
        branch_layouts.append(
            {
                **canonical_clone_v1(raw),
                "hierarchy_aliases": _normalized_aliases(
                    raw["hierarchy_aliases"], label=raw["branch_role"]
                ),
            }
        )
    if (
        len(branch_layouts) not in {2, 3}
        or sum(item["rollforward_kind"] == "SIGNED_ADDITIVE" for item in branch_layouts) != 2
        or sum(
            item["rollforward_kind"] == "COST_AND_DEPRECIATION_CONTROL" for item in branch_layouts
        )
        not in {0, 1}
    ):
        raise _error("fixed-asset needs two signed branches and at most one carrying control")
    carrying_count = sum(
        item["rollforward_kind"] == "COST_AND_DEPRECIATION_CONTROL" for item in branch_layouts
    )
    signed_branch_layouts = [
        item for item in branch_layouts if item["rollforward_kind"] == "SIGNED_ADDITIVE"
    ]
    if (
        sum(layout["opening_role"].startswith("COST_") for layout in signed_branch_layouts) != 1
        or sum(layout["opening_role"].startswith("DEP_") for layout in signed_branch_layouts) != 1
    ):
        raise _error("fixed-asset signed branches need one cost and one depreciation role")
    if (
        evaluation_spec["closure_policy"]
        == "ALL_SOURCE_ROWS_HORIZONTAL_PLUS_SIGNED_BRANCH_AND_CARRYING_EQUATIONS_EXACT"
        and carrying_count != 1
    ):
        raise _error("fixed-asset carrying closure policy needs one carrying control")
    schema_fields = {
        "context_only_roles",
        "family_id",
        "family_root_report_norm_id",
        "format_version",
        "role_bindings",
        "schema_period_role",
        "structural_root_mapping_policy",
    }
    if (
        type(schema_binding_spec) is not dict
        or set(schema_binding_spec) != schema_fields
        or schema_binding_spec.get("format_version") != SCHEMA_FORMAT_VERSION
        or schema_binding_spec.get("family_id") != topology["family_id"]
        or type(schema_binding_spec.get("family_root_report_norm_id")) is not int
        or schema_binding_spec["family_root_report_norm_id"] <= 0
        or schema_binding_spec.get("schema_period_role") != "CURRENT_PERIOD"
        or schema_binding_spec.get("structural_root_mapping_policy")
        != "CONTEXT_ONLY_NO_NUMERIC_MAPPING"
        or type(schema_binding_spec.get("context_only_roles")) is not dict
        or type(schema_binding_spec.get("role_bindings")) is not list
    ):
        raise _error("fixed-asset schema binding spec is invalid")
    context_roles = schema_binding_spec["context_only_roles"]
    if (
        set(context_roles) != {topology["parent"]["role"], *branch_roles}
        or context_roles[topology["parent"]["role"]]
        != schema_binding_spec["family_root_report_norm_id"]
        or any(type(value) is not int or value <= 0 for value in context_roles.values())
    ):
        raise _error("fixed-asset context-only role bindings drifted")
    bindings: dict[str, int] = {}
    output_role_order = []
    seen_ids = set(context_roles.values())
    for raw in schema_binding_spec["role_bindings"]:
        if (
            type(raw) is not dict
            or set(raw) != {"report_norm_id", "role"}
            or raw["role"] not in child_by_role
            or raw["role"] in branch_roles
            or raw["role"] in bindings
            or type(raw["report_norm_id"]) is not int
            or raw["report_norm_id"] <= 0
            or raw["report_norm_id"] in seen_ids
        ):
            raise _error("fixed-asset output role binding drifted")
        bindings[raw["role"]] = raw["report_norm_id"]
        output_role_order.append(raw["role"])
        seen_ids.add(raw["report_norm_id"])
    if endpoint_roles - set(bindings) or subtotal_roles - set(bindings):
        raise _error("fixed-asset endpoint/subtotal schema frontier is incomplete")
    role_aliases = {role: _aliases(child) for role, child in child_by_role.items()}
    output_roles_by_branch = {}
    for layout in branch_layouts:
        prefix = (
            "CARRY_"
            if layout["rollforward_kind"] == "COST_AND_DEPRECIATION_CONTROL"
            else ("COST_" if layout["branch_role"].startswith("COST") else "DEP_")
        )
        roles = [role for role in output_role_order if role.startswith(prefix)]
        if set((layout["opening_role"], layout["ending_role"])) - set(roles):
            raise _error("fixed-asset branch output role frontier drifted")
        output_roles_by_branch[layout["branch_role"]] = roles
    evaluation = {
        **canonical_clone_v1(evaluation_spec),
        "asset_header_aliases": asset_aliases,
        "branch_layouts": branch_layouts,
        "header_hard_negative_aliases": hard_negative_aliases,
        "money_unit_bindings": units,
        "total_column_aliases": total_aliases,
    }
    schema = canonical_clone_v1(schema_binding_spec)
    query_policy = {
        "asset_header_aliases": asset_aliases,
        "branch_layouts": branch_layouts,
        "header_hard_negative_aliases": hard_negative_aliases,
        "minimum_distinct_asset_header_aliases": evaluation[
            "minimum_distinct_asset_header_aliases"
        ],
        "owner_aliases": canonical_clone_v1(topology["parent"]["aliases"]),
        "structural_reset_aliases": canonical_clone_v1(topology["structural_reset_aliases"]),
        "total_column_aliases": total_aliases,
    }
    return {
        "bindings": bindings,
        "claim_boundary": CLAIM_BOUNDARY,
        "engine_format_version": ENGINE_FORMAT_VERSION,
        "evaluation": evaluation,
        "output_role_order": output_role_order,
        "output_roles_by_branch": output_roles_by_branch,
        "query_policy": query_policy,
        "role_aliases": role_aliases,
        "schema": schema,
        "topology": topology,
        "unit_binding_by_alias": unit_by_alias,
    }


def _contains_alias(value: Any, alias: str) -> bool:
    folded = _normalized(value)
    return bool(folded and re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", folded))


def _surface_dates(value: Any) -> set[date]:
    folded = _normalized(value)
    dates = set()
    for day_text, month_text, year_text in _DATE_DMY.findall(folded):
        try:
            dates.add(date(int(year_text), int(month_text), int(day_text)))
        except ValueError:
            continue
    return dates


def _header_text(column: Mapping[str, Any]) -> str:
    path = column.get("header_path_exact")
    return " ".join(item for item in path if type(item) is str) if type(path) is list else ""


def _period_header_evidence(value: Any) -> bool:
    folded = _normalized(value)
    return bool(
        _surface_dates(value)
        or any(
            token in folded
            for token in (
                "so dau ky",
                "so dau nam",
                "so cuoi ky",
                "so cuoi nam",
                "current period",
                "comparative period",
            )
        )
    )


def _governed_period_end_from_surface(value: Any) -> date | None:
    folded = _normalized(value)
    governed_full = re.search(
        r"(?:ky|nam|giai doan)?\s*(?:tai chinh\s*)?(?:ket thuc|ended)\s*"
        r"(?:vao\s*)?(?:ngay\s*)?([0-3]?\d)\s+(?:thang\s+)?([01]?\d)\s+"
        r"(?:nam\s+)?((?:19|20)\d{2})",
        folded,
    )
    if governed_full is not None:
        try:
            return date(
                int(governed_full.group(3)),
                int(governed_full.group(2)),
                int(governed_full.group(1)),
            )
        except ValueError:
            return None
    # A bare reporting year is not proof of a calendar-year end.  Exact
    # day/month comes from source-visible endpoints or the typed document
    # reporting-date receipt; this also supports non-calendar fiscal years.
    return None


def _surface_axis(section: Mapping[str, Any], table: Mapping[str, Any]) -> list[str]:
    axis = []
    for value in (section.get("title_exact"), table.get("title_exact")):
        if type(value) is str and value.strip():
            axis.append(value)
    narratives = section.get("narratives_exact")
    if type(narratives) is list:
        axis.extend(value for value in narratives if type(value) is str and value.strip())
    return axis


def _owner_visible(
    section: Mapping[str, Any], table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> bool:
    aliases = [_normalized(alias) for alias in compiled_specs["topology"]["parent"]["aliases"]]
    return any(
        _contains_alias(surface, alias)
        for surface in _surface_axis(section, table)
        for alias in aliases
    )


def _branch_layout_for_row(
    row: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any] | None:
    path = row.get("hierarchy_path_exact")
    surfaces = []
    if type(path) is list:
        surfaces.extend(item for item in path[:1] if type(item) is str)
    if not surfaces and type(row.get("label_exact")) is str:
        surfaces.append(row["label_exact"])
    matches = [
        layout
        for layout in compiled_specs["evaluation"]["branch_layouts"]
        if any(
            _contains_alias(surface, alias)
            for surface in surfaces
            for alias in layout["hierarchy_aliases"]
        )
    ]
    return matches[0] if len(matches) == 1 else None


def _endpoint_role(
    label: Any, layout: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> str | None:
    folded = _normalized(label)
    dates = _surface_dates(label)
    opening = any(item.month == 1 and item.day == 1 for item in dates) or any(
        token in folded for token in ("so du dau", "so dau", "tai ngay dau ky", "tai ngay dau nam")
    )
    ending = any(item.month != 1 or item.day != 1 for item in dates) or any(
        token in folded
        for token in ("so du cuoi", "so cuoi", "tai ngay cuoi ky", "tai ngay cuoi nam")
    )
    if opening and not ending:
        return layout["opening_role"]
    if ending and not opening:
        return layout["ending_role"]
    for role in (layout["opening_role"], layout["ending_role"]):
        if any(_contains_alias(label, alias) for alias in compiled_specs["role_aliases"][role]):
            return role
    return None


def _role_for_row(
    row: Mapping[str, Any], layout: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> str | None:
    endpoint = _endpoint_role(row.get("label_exact"), layout, compiled_specs=compiled_specs)
    if endpoint is not None:
        return endpoint
    candidates = []
    for role in compiled_specs["output_roles_by_branch"][layout["branch_role"]]:
        if role in {layout["opening_role"], layout["ending_role"]}:
            continue
        matching_aliases = [
            alias
            for alias in compiled_specs["role_aliases"][role]
            if _contains_alias(row.get("label_exact"), alias)
        ]
        if matching_aliases:
            candidates.append((max(map(len, matching_aliases)), role))
    if not candidates:
        return None
    longest = max(item[0] for item in candidates)
    roles = {role for length, role in candidates if length == longest}
    return next(iter(roles)) if len(roles) == 1 else None


def _table_period_receipt(
    section: Mapping[str, Any], table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    ending_dates = set()
    rows = table.get("rows")
    if type(rows) is list:
        for row in rows:
            if type(row) is not dict:
                continue
            layout = _branch_layout_for_row(row, compiled_specs=compiled_specs)
            if layout is None:
                continue
            if (
                _endpoint_role(row.get("label_exact"), layout, compiled_specs=compiled_specs)
                == layout["ending_role"]
            ):
                ending_dates.update(_surface_dates(row.get("label_exact")))
    local_governed_dates = {
        item
        for surface in [
            table.get("title_exact"),
            *(section.get("narratives_exact") or []),
        ]
        if (item := _governed_period_end_from_surface(surface)) is not None
    }
    section_context_dates = {
        item
        for surface in [section.get("title_exact")]
        if (item := _governed_period_end_from_surface(surface)) is not None
    }
    # Table-local narratives and endpoint rows outrank a page/section report
    # heading.  This lets a comparative table retain its prior-year date when
    # it appears under a current-period report header, while still rejecting
    # contradictions inside the table's own source boundary.
    distinct_dates = ending_dates | local_governed_dates
    if not distinct_dates:
        distinct_dates = section_context_dates
    if len(distinct_dates) > 1:
        status = "CONFLICTING_SOURCE_VISIBLE_PERIOD_END_DATES"
        period_end_date = None
    elif len(distinct_dates) == 1:
        status = "UNIQUE_SOURCE_VISIBLE_PERIOD_END_DATE"
        period_end_date = next(iter(distinct_dates)).isoformat()
    else:
        status = "NO_EXACT_PERIOD_END_DATE"
        period_end_date = None
    return {
        "endpoint_dates": sorted(item.isoformat() for item in ending_dates),
        "local_governed_surface_dates": sorted(item.isoformat() for item in local_governed_dates),
        "period_end_date": period_end_date,
        "section_context_dates": sorted(item.isoformat() for item in section_context_dates),
        "status": status,
    }


def classify_gemini_json_fixed_asset_rollforward_table_v1(
    section: Any, table: Any, *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Classify one table from owner, typed headers and complete branch seeds."""

    if type(section) is not dict or type(table) is not dict:
        raise _error("fixed-asset section/table is invalid")
    rows = table.get("rows")
    columns = table.get("columns")
    if type(rows) is not list or type(columns) is not list:
        raise _error("fixed-asset table axes are invalid")
    money_ordinals = [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    family_header_ordinals = []
    negative_header_hits = []
    total_ordinals = []
    for ordinal in money_ordinals:
        header = _header_text(columns[ordinal - 1])
        if any(
            _contains_alias(header, alias)
            for alias in compiled_specs["evaluation"]["asset_header_aliases"]
        ):
            family_header_ordinals.append(ordinal)
        for alias in compiled_specs["evaluation"]["header_hard_negative_aliases"]:
            if _contains_alias(header, alias):
                negative_header_hits.append({"alias": alias, "column_ordinal": ordinal})
        if any(
            _contains_alias(header, alias)
            for alias in compiled_specs["evaluation"]["total_column_aliases"]
        ):
            total_ordinals.append(ordinal)
    branch_hits = set()
    recognized_row_count = 0
    unclassified_numeric_rows = []
    for ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict:
            continue
        values = row.get("values_exact")
        has_money = type(values) is list and any(
            index - 1 < len(values) and values[index - 1] not in {None, ""}
            for index in money_ordinals
        )
        layout = _branch_layout_for_row(row, compiled_specs=compiled_specs)
        if layout is None:
            if row.get("row_kind") != "GROUP" and has_money:
                unclassified_numeric_rows.append(ordinal)
            continue
        branch_hits.add(layout["branch_role"])
        if row.get("row_kind") == "GROUP":
            continue
        role = _role_for_row(row, layout, compiled_specs=compiled_specs)
        if role is None and has_money:
            unclassified_numeric_rows.append(ordinal)
        elif role is not None:
            recognized_row_count += 1
    required_branches = {
        item["branch_role"] for item in compiled_specs["evaluation"]["branch_layouts"]
    }
    owner = _owner_visible(section, table, compiled_specs=compiled_specs)
    variant_hard_negative_visible = any(
        _contains_alias(surface, alias)
        for surface in _surface_axis(section, table)
        for alias in compiled_specs["evaluation"]["header_hard_negative_aliases"]
    )
    two_period_non_rollforward_control = bool(
        owner
        and branch_hits != required_branches
        and not family_header_ordinals
        and len(money_ordinals) == 2
        and all(
            _period_header_evidence(_header_text(columns[ordinal - 1]))
            for ordinal in money_ordinals
        )
    )
    # A section owner can legitimately govern a two-period informational
    # control table (for example fully-depreciated assets).  Such a table is
    # not a roll-forward fragment.
    min_headers = compiled_specs["evaluation"]["minimum_distinct_asset_header_aliases"]
    has_family_signal = bool(
        not two_period_non_rollforward_control
        and (
            (owner and (family_header_ordinals or branch_hits))
            or (
                branch_hits == required_branches
                and len(family_header_ordinals) >= min_headers
                and not negative_header_hits
                and not variant_hard_negative_visible
            )
        )
    )
    period_receipt = _table_period_receipt(section, table, compiled_specs=compiled_specs)
    reasons = []
    if negative_header_hits and has_family_signal:
        reasons.append("HARD_NEGATIVE_ASSET_HEADER_VISIBLE")
    if variant_hard_negative_visible and owner:
        reasons.append("HARD_NEGATIVE_FIXED_ASSET_VARIANT_SURFACE_VISIBLE")
    if branch_hits and branch_hits != required_branches:
        reasons.append("CONFIGURED_BRANCH_SEED_FRONTIER_INCOMPLETE")
    if branch_hits == required_branches and not owner:
        reasons.append("EXPLICIT_FIXED_ASSET_OWNER_NOT_VISIBLE")
    if (
        branch_hits == required_branches
        and len(family_header_ordinals)
        < compiled_specs["evaluation"]["minimum_distinct_asset_header_aliases"]
    ):
        reasons.append("DISTINCT_ASSET_HEADER_FRONTIER_INCOMPLETE")
    if branch_hits == required_branches and (
        len(total_ordinals) != 1 or not money_ordinals or total_ordinals[0] != money_ordinals[-1]
    ):
        reasons.append("UNIQUE_RIGHT_EDGE_TOTAL_COLUMN_NOT_VISIBLE")
    if unclassified_numeric_rows:
        reasons.append("UNCLASSIFIED_NUMERIC_ROW_INSIDE_FIXED_ASSET_BRANCH")
    if period_receipt["status"] == "CONFLICTING_SOURCE_VISIBLE_PERIOD_END_DATES":
        reasons.append("FIXED_ASSET_TABLE_PERIOD_EVIDENCE_CONFLICT")
    complete = (
        branch_hits == required_branches
        and owner
        and len(family_header_ordinals)
        >= compiled_specs["evaluation"]["minimum_distinct_asset_header_aliases"]
        and len(total_ordinals) == 1
        and total_ordinals[0] == money_ordinals[-1]
        and not reasons
    )
    return {
        "branch_roles": sorted(branch_hits),
        "complete": complete,
        "family_header_column_ordinals": family_header_ordinals,
        "family_signal": has_family_signal,
        "hard_negative_header_hits": negative_header_hits,
        "money_column_ordinals": money_ordinals,
        "owner_visible": owner,
        "period_end_date": period_receipt["period_end_date"],
        "period_receipt": period_receipt,
        "reasons": sorted(set(reasons)),
        "recognized_row_count": recognized_row_count,
        "total_column_ordinals": total_ordinals,
        "unclassified_numeric_row_ordinals": unclassified_numeric_rows,
    }


def _endpoint_total_signature(
    section: Mapping[str, Any], table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> dict[str, int] | None:
    classification = classify_gemini_json_fixed_asset_rollforward_table_v1(
        section, table, compiled_specs=compiled_specs
    )
    if not classification["complete"]:
        return None
    total_ordinal = classification["total_column_ordinals"][0]
    signature = {}
    for row in table.get("rows", []):
        if type(row) is not dict or row.get("row_kind") == "GROUP":
            continue
        layout = _branch_layout_for_row(row, compiled_specs=compiled_specs)
        if layout is None:
            continue
        role = _endpoint_role(row.get("label_exact"), layout, compiled_specs=compiled_specs)
        if role not in {layout["opening_role"], layout["ending_role"]}:
            continue
        values = row.get("values_exact")
        if type(values) is not list or total_ordinal > len(values):
            return None
        try:
            cell = _money(
                values[total_ordinal - 1],
                source_locator={"period_selection_endpoint": role},
            )
        except GeminiJsonFixedAssetRollforwardFamilyV1Error:
            return None
        if cell["state"] == "BLANK" or role in signature:
            return None
        signature[role] = cell["coefficient"]
    expected = {
        role
        for layout in compiled_specs["evaluation"]["branch_layouts"]
        for role in (layout["opening_role"], layout["ending_role"])
    }
    return signature if set(signature) == expected else None


def _continuity_selects_current(
    candidate: Mapping[str, Any],
    controls: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
) -> bool:
    current_signature = _endpoint_total_signature(
        candidate["section"], candidate["table"], compiled_specs=compiled_specs
    )
    if current_signature is None:
        return False
    for control in controls:
        comparative_signature = _endpoint_total_signature(
            control["section"], control["table"], compiled_specs=compiled_specs
        )
        if comparative_signature is None:
            return False
        for layout in compiled_specs["evaluation"]["branch_layouts"]:
            if (
                current_signature[layout["opening_role"]]
                != comparative_signature[layout["ending_role"]]
            ):
                return False
    return True


def _document_reporting_date_receipt(page_records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    evidence = []
    for record in page_records:
        for section_ordinal, section in enumerate(record["page_json"].get("sections", []), start=1):
            if type(section) is not dict:
                continue
            if section.get("content_kind") == "PRIMARY_STATEMENT" and section.get(
                "statement_type"
            ) in {"INCOME_STATEMENT", "CASH_FLOW"}:
                governed_dates = {
                    item
                    for surface in [
                        section.get("title_exact"),
                        *(section.get("narratives_exact") or []),
                    ]
                    if (item := _governed_period_end_from_surface(surface)) is not None
                }
                if len(governed_dates) == 1:
                    current = next(iter(governed_dates))
                    evidence.append(
                        {
                            "comparative_date": None,
                            "current_date": current.isoformat(),
                            "page_json_version_id": record["page_json_version_id"],
                            "physical_page": record["physical_page"],
                            "section_id": f"s{section_ordinal}",
                            "source_kind": "TYPED_PRIMARY_STATEMENT_PERIOD_HEADING",
                            "table_id": None,
                        }
                    )
            if not (
                section.get("content_kind") == "PRIMARY_STATEMENT"
                and section.get("statement_type") == "BALANCE_SHEET"
            ):
                continue
            for table_ordinal, table in enumerate(section.get("tables", []), start=1):
                if type(table) is not dict:
                    continue
                column_dates = []
                for column_ordinal, column in enumerate(table.get("columns", []), start=1):
                    if type(column) is not dict or column.get("value_kind") != "MONEY":
                        continue
                    dates = sorted(_surface_dates(_header_text(column)))
                    if len(dates) == 1:
                        column_dates.append((column_ordinal, dates[0]))
                distinct = sorted({item[1] for item in column_dates})
                if (
                    len(distinct) != 2
                    or not distinct[1] > distinct[0]
                    or (distinct[1] - distinct[0]).days > 366
                ):
                    continue
                evidence.append(
                    {
                        "comparative_date": distinct[0].isoformat(),
                        "current_date": distinct[1].isoformat(),
                        "page_json_version_id": record["page_json_version_id"],
                        "physical_page": record["physical_page"],
                        "section_id": f"s{section_ordinal}",
                        "source_kind": "TYPED_BALANCE_SHEET_DATE_COLUMNS",
                        "table_id": f"t{table_ordinal}",
                    }
                )
    current_dates = sorted({item["current_date"] for item in evidence})
    comparative_dates = sorted(
        {item["comparative_date"] for item in evidence if item["comparative_date"] is not None}
    )
    current_date = current_dates[0] if len(current_dates) == 1 else None
    comparative_date = comparative_dates[0] if len(comparative_dates) == 1 else None
    return {
        "comparative_date": comparative_date,
        "current_date": current_date,
        "evidence": evidence,
        "status": "UNIQUE_TYPED_DOCUMENT_REPORTING_DATE" if current_date else "NOT_UNIQUE",
    }


def _page_record_axis(page_records: Any) -> list[dict[str, Any]]:
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
        raise _error("fixed-asset selected page records are absent")
    checked = []
    identity = None
    prior_position = None
    for raw in page_records:
        if (
            type(raw) is not dict
            or set(raw) != fields
            or _DOCUMENT_ID.fullmatch(raw.get("document_id", "")) is None
            or type(raw.get("document_ordinal")) is not int
            or raw["document_ordinal"] <= 0
            or _PAGE_VERSION.fullmatch(raw.get("page_json_version_id", "")) is None
            or type(raw.get("physical_page")) is not int
            or raw["physical_page"] <= 0
            or type(raw.get("selected_page_ordinal")) is not int
            or raw["selected_page_ordinal"] <= 0
            or type(raw.get("source_logical_name")) is not str
            or not raw["source_logical_name"]
            or _SHA256.fullmatch(raw.get("source_sha256", "")) is None
            or type(raw.get("page_json")) is not dict
            or type(raw["page_json"].get("sections")) is not list
        ):
            raise _error("fixed-asset selected page record is invalid")
        current_identity = tuple(
            raw[key]
            for key in ("document_id", "document_ordinal", "source_logical_name", "source_sha256")
        )
        position = (raw["selected_page_ordinal"], raw["physical_page"])
        if identity is None:
            identity = current_identity
        elif current_identity != identity:
            raise _error("fixed-asset page records cross document identity")
        if prior_position is not None and position <= prior_position:
            raise _error("fixed-asset page records are not ordered")
        prior_position = position
        checked.append(canonical_clone_v1(raw))
    if [item["selected_page_ordinal"] for item in checked] != list(range(1, len(checked) + 1)):
        raise _error("fixed-asset selected page ordinals are incomplete")
    return checked


def _region(
    item: Mapping[str, Any],
    *,
    component_role: str,
    fragment_ordinal: int,
    period_end_date: str | None,
    period_selection_kind: str,
) -> dict[str, Any]:
    return {
        "component_role": component_role,
        "document_id": item["record"]["document_id"],
        "document_ordinal": item["record"]["document_ordinal"],
        "fragment_ordinal": fragment_ordinal,
        "page_json_version_id": item["record"]["page_json_version_id"],
        "period_end_date": period_end_date,
        "period_selection_kind": period_selection_kind,
        "physical_page": item["record"]["physical_page"],
        "section_id": item["section_id"],
        "selected_page_ordinal": item["record"]["selected_page_ordinal"],
        "source_logical_name": item["record"]["source_logical_name"],
        "source_sha256": item["record"]["source_sha256"],
        "table_id": item["table_id"],
    }


def coalesce_gemini_json_fixed_asset_rollforward_document_v1(
    *, page_records: Any, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Inventory all family signals and select one current table by source period."""

    pages = _page_record_axis(page_records)
    reporting_date_receipt = _document_reporting_date_receipt(pages)
    inventory = []
    family_tables = []
    for record in pages:
        sections = record["page_json"]["sections"]
        for section_ordinal, section in enumerate(sections, start=1):
            if type(section) is not dict:
                continue
            tables = section.get("tables")
            if type(tables) is not list:
                continue
            for table_ordinal, table in enumerate(tables, start=1):
                if type(table) is not dict:
                    continue
                classification = classify_gemini_json_fixed_asset_rollforward_table_v1(
                    section, table, compiled_specs=compiled_specs
                )
                if not classification["family_signal"]:
                    continue
                item = {
                    "classification": classification,
                    "position": [record["selected_page_ordinal"], section_ordinal, table_ordinal],
                    "record": record,
                    "section": section,
                    "section_id": f"s{section_ordinal}",
                    "table": table,
                    "table_id": f"t{table_ordinal}",
                }
                family_tables.append(item)
    complete = [item for item in family_tables if item["classification"]["complete"]]
    reasons = []
    current = None
    controls = []
    if family_tables and len(complete) != len(family_tables):
        reasons.extend(
            reason
            for item in family_tables
            if not item["classification"]["complete"]
            for reason in item["classification"]["reasons"]
        )
        reasons.append("FAMILY_SIGNAL_TABLE_IS_NOT_A_COMPLETE_FIXED_ASSET_PRESENTATION")
    elif len(complete) == 1:
        current = complete[0]
    elif len(complete) > 1:
        period_dates = [item["classification"]["period_end_date"] for item in complete]
        if not any(value is None for value in period_dates):
            latest = max(period_dates)
            selected = [
                item for item in complete if item["classification"]["period_end_date"] == latest
            ]
            if len(selected) != 1:
                reasons.append("CURRENT_FIXED_ASSET_TABLE_IS_NOT_UNIQUE")
            else:
                current = selected[0]
                controls = [item for item in complete if item is not current]
        else:
            document_date = reporting_date_receipt["current_date"]
            missing = [
                item for item in complete if item["classification"]["period_end_date"] is None
            ]
            known = [
                item for item in complete if item["classification"]["period_end_date"] is not None
            ]
            if (
                document_date is not None
                and len(missing) == 1
                and known
                and all(item["classification"]["period_end_date"] < document_date for item in known)
            ):
                selected = missing
            else:
                selected = [
                    item
                    for item in complete
                    if _continuity_selects_current(
                        item,
                        [other for other in complete if other is not item],
                        compiled_specs=compiled_specs,
                    )
                ]
            if len(selected) != 1:
                reasons.append(
                    "MULTIPLE_FAMILY_TABLES_REQUIRE_UNIQUE_PERIOD_OR_ENDPOINT_CONTINUITY"
                )
            else:
                current = selected[0]
                controls = [item for item in complete if item is not current]
    control_period_bindings = []
    if current is not None and not reasons:
        local_period = current["classification"]["period_end_date"]
        effective_period = local_period or reporting_date_receipt["current_date"]
        if effective_period is None:
            reasons.append("CURRENT_FIXED_ASSET_PERIOD_END_DATE_NOT_AUTHENTICATED")
        for item in controls:
            control_period = item["classification"]["period_end_date"]
            if control_period is not None:
                control_period_bindings.append(
                    (control_period, "LOCAL_EXPLICIT_COMPARATIVE_CONTROL_DATE")
                )
            elif reporting_date_receipt["comparative_date"] is not None and (
                _continuity_selects_current(current, [item], compiled_specs=compiled_specs)
            ):
                control_period_bindings.append(
                    (
                        reporting_date_receipt["comparative_date"],
                        "TYPED_DOCUMENT_COMPARATIVE_DATE_WITH_ENDPOINT_CONTINUITY",
                    )
                )
            else:
                reasons.append("COMPARATIVE_CONTROL_PERIOD_END_DATE_NOT_AUTHENTICATED")
    if current is not None and not reasons:
        local_period = current["classification"]["period_end_date"]
        effective_period = local_period or reporting_date_receipt["current_date"]
        current_region = _region(
            current,
            component_role="CURRENT_TABLE",
            fragment_ordinal=1,
            period_end_date=effective_period,
            period_selection_kind=(
                "LOCAL_EXPLICIT_END_DATE"
                if local_period is not None
                else "UNIQUE_TYPED_DOCUMENT_REPORTING_DATE"
            ),
        )
        control_regions = [
            _region(
                item,
                component_role="COMPARATIVE_CONTROL_TABLE",
                fragment_ordinal=index,
                period_end_date=control_period_bindings[index - 1][0],
                period_selection_kind=control_period_bindings[index - 1][1],
            )
            for index, item in enumerate(controls, start=1)
        ]
    else:
        current_region = None
        control_regions = []
    for item in family_tables:
        if item is current:
            disposition = "SELECTED_UNIQUE_CURRENT_TABLE"
        elif item in controls:
            disposition = "TYPED_COMPARATIVE_CONTROL_TABLE"
        elif item["classification"]["complete"]:
            disposition = "UNSELECTED_COMPLETE_FAMILY_TABLE"
        else:
            disposition = "UNRESOLVED_FAMILY_SIGNAL_TABLE"
        inventory.append(
            {
                "classification": canonical_clone_v1(item["classification"]),
                "disposition": disposition,
                "page_json_version_id": item["record"]["page_json_version_id"],
                "physical_page": item["record"]["physical_page"],
                "position": item["position"],
                "section_id": item["section_id"],
                "table_id": item["table_id"],
            }
        )
    material = {
        "component_regions": [current_region] if current_region is not None else [],
        "control_regions": control_regions,
        "document_id": pages[0]["document_id"],
        "document_ordinal": pages[0]["document_ordinal"],
        "family_table_inventory": inventory,
        "document_reporting_date_receipt": reporting_date_receipt,
        "reasons": sorted(set(reasons)),
        "source_logical_name": pages[0]["source_logical_name"],
        "source_sha256": pages[0]["source_sha256"],
        "status": (
            READY
            if current_region is not None and not reasons
            else (NOT_OBSERVED if not family_tables else UNRESOLVED)
        ),
    }
    return {
        **material,
        "cluster_id": "gjffarfcv1:cluster:" + canonical_json_sha256_v1(material),
    }


def _region_axis(regions: Any, *, component_role: str, maximum: int) -> list[dict[str, Any]]:
    fields = {
        "component_role",
        "document_id",
        "document_ordinal",
        "fragment_ordinal",
        "page_json_version_id",
        "period_end_date",
        "period_selection_kind",
        "physical_page",
        "section_id",
        "selected_page_ordinal",
        "source_logical_name",
        "source_sha256",
        "table_id",
    }
    if type(regions) not in {list, tuple} or not 0 <= len(regions) <= maximum:
        raise _error("fixed-asset region axis cardinality is invalid")
    checked = []
    identity = None
    prior = None
    for ordinal, raw in enumerate(regions, start=1):
        period_end_date = raw.get("period_end_date") if type(raw) is dict else None
        period_selection_kind = raw.get("period_selection_kind") if type(raw) is dict else None
        try:
            parsed_period_end = (
                date.fromisoformat(period_end_date) if type(period_end_date) is str else None
            )
        except ValueError:
            parsed_period_end = None
        expected_period_kinds = (
            {"LOCAL_EXPLICIT_END_DATE", "UNIQUE_TYPED_DOCUMENT_REPORTING_DATE"}
            if component_role == "CURRENT_TABLE"
            else {
                "LOCAL_EXPLICIT_COMPARATIVE_CONTROL_DATE",
                "TYPED_DOCUMENT_COMPARATIVE_DATE_WITH_ENDPOINT_CONTINUITY",
            }
        )
        if (
            type(raw) is not dict
            or set(raw) != fields
            or raw.get("component_role") != component_role
            or raw.get("fragment_ordinal") != ordinal
            or _DOCUMENT_ID.fullmatch(raw.get("document_id", "")) is None
            or type(raw.get("document_ordinal")) is not int
            or raw["document_ordinal"] <= 0
            or _PAGE_VERSION.fullmatch(raw.get("page_json_version_id", "")) is None
            or parsed_period_end is None
            or period_end_date != parsed_period_end.isoformat()
            or period_selection_kind not in expected_period_kinds
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
            raise _error("fixed-asset region is invalid")
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
            raise _error("fixed-asset regions cross document identity")
        if prior is not None and position <= prior:
            raise _error("fixed-asset regions are not in source order")
        prior = position
        checked.append(canonical_clone_v1(raw))
    return checked


def build_gemini_json_fixed_asset_rollforward_region_query_receipt_v1(
    regions: Any, *, control_regions: Any
) -> dict[str, Any]:
    current = _region_axis(regions, component_role="CURRENT_TABLE", maximum=1)
    controls = _region_axis(control_regions, component_role="COMPARATIVE_CONTROL_TABLE", maximum=8)
    if len(current) != 1:
        raise _error("fixed-asset query receipt needs one current table")
    if controls and any(
        item["document_id"] != current[0]["document_id"]
        or item["source_sha256"] != current[0]["source_sha256"]
        for item in controls
    ):
        raise _error("fixed-asset control regions cross current document")
    material = {
        "control_region_axis_sha256": canonical_json_sha256_v1(controls),
        "current_region": current[0],
        "document_id": current[0]["document_id"],
        "exact_control_region_count": len(controls),
        "format_version": "GEMINI_JSON_FIXED_ASSET_ROLLFORWARD_REGION_QUERY_RECEIPT_V1",
        "source_logical_name": current[0]["source_logical_name"],
        "source_sha256": current[0]["source_sha256"],
    }
    return {
        **material,
        "query_receipt_id": "gjffarrqrv1:receipt:" + canonical_json_sha256_v1(material),
    }


def _money(value: Any, *, source_locator: Mapping[str, Any]) -> dict[str, Any]:
    if value is None:
        return {
            "coefficient": None,
            "source_locator": canonical_clone_v1(source_locator),
            "source_text": "",
            "state": "BLANK",
        }
    if type(value) is not str:
        raise _error("fixed-asset money source must be exact text or null")
    source_text = value
    text = value.strip()
    if not text:
        return {
            "coefficient": None,
            "source_locator": canonical_clone_v1(source_locator),
            "source_text": source_text,
            "state": "BLANK",
        }
    if text in _DASHES:
        return {
            "coefficient": 0,
            "source_locator": canonical_clone_v1(source_locator),
            "source_text": source_text,
            "state": "DASH_ZERO",
        }
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1].strip()
    explicit_negative = text.startswith("-")
    if explicit_negative:
        text = text[1:].strip()
    digits = re.sub(r"[.,\s]", "", text)
    if not digits.isdigit():
        raise _error("fixed-asset money text is not one exact signed integer")
    coefficient = int(digits)
    if negative or explicit_negative:
        coefficient = -coefficient
    return {
        "coefficient": coefficient,
        "source_locator": canonical_clone_v1(source_locator),
        "source_text": source_text,
        "state": "PRINTED_ZERO" if coefficient == 0 else "NUMBER",
    }


def _unit_axis(table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]) -> dict[str, Any]:
    recognized = list(compiled_specs["unit_binding_by_alias"])
    evidence = []
    conflicting_surfaces = []
    undeclared = []

    def classify(surface: dict[str, Any], *, explicit_slot: bool) -> dict[str, Any] | None:
        folded = _normalized(surface["text_exact"])
        occurrences = [
            (match.start(), match.end(), alias)
            for alias in recognized
            for match in re.finditer(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", folded)
        ]
        maximal = sorted(
            [
                occurrence
                for occurrence in occurrences
                if not any(
                    other[0] <= occurrence[0]
                    and occurrence[1] <= other[1]
                    and other[1] - other[0] > occurrence[1] - occurrence[0]
                    for other in occurrences
                )
            ],
            key=lambda item: (item[0], item[1], item[2]),
        )
        if maximal:
            records = []
            for match_ordinal, (_start, _end, alias) in enumerate(maximal, start=1):
                binding = compiled_specs["unit_binding_by_alias"][alias]
                record = {
                    **surface,
                    "accepted": binding["accepted"],
                    "canonical_unit": binding["canonical_unit"],
                    "match_ordinal": match_ordinal,
                    "matched_alias": alias,
                    "magnitude_power10": binding["magnitude_power10"],
                }
                records.append(record)
                evidence.append(record)
            identities = {
                (record["canonical_unit"], record["magnitude_power10"]) for record in records
            }
            if len(identities) != 1:
                conflicting_surfaces.append(
                    {**surface, "matched_aliases": [record["matched_alias"] for record in records]}
                )
                return None
            return records[0]
        if explicit_slot or re.search(r"\b(?:dong|vnd|trieu|nghin|ty)\b", folded):
            undeclared.append(surface)
        return None

    table_record = None
    unit_exact = table.get("unit_exact")
    if type(unit_exact) is str and unit_exact.strip():
        table_record = classify(
            {"source_kind": "TABLE_UNIT", "text_exact": unit_exact}, explicit_slot=True
        )
    columns = table.get("columns")
    money_records = []
    if type(columns) is list:
        for ordinal, column in enumerate(columns, start=1):
            if type(column) is not dict or column.get("value_kind") != "MONEY":
                continue
            header = _header_text(column)
            money_records.append(
                classify(
                    {"source_kind": f"MONEY_COLUMN_HEADER:c{ordinal}", "text_exact": header},
                    explicit_slot=False,
                )
                if header
                else None
            )
    reasons = []
    if conflicting_surfaces:
        reasons.append("MULTIPLE_CONFLICTING_DECLARED_MONEY_UNITS_ON_ONE_SURFACE")
    if undeclared:
        reasons.append("UNDECLARED_EXPLICIT_MONEY_UNIT")
    if any(item is not None and not item["accepted"] for item in [table_record, *money_records]):
        reasons.append("EXPLICIT_MONEY_UNIT_IS_NOT_ACCEPTED")
    canonical_unit = None
    source = None
    if table_record is not None and table_record["accepted"]:
        canonical_unit = table_record["canonical_unit"]
        source = "LOCAL_TABLE_UNIT"
        if any(
            item is not None and item["canonical_unit"] != canonical_unit for item in money_records
        ):
            reasons.append("CONFLICTING_EXPLICIT_MONEY_UNITS")
    elif money_records:
        if any(item is None or not item["accepted"] for item in money_records):
            reasons.append("MONEY_COLUMN_UNITS_ARE_NOT_UNIFORMLY_EXPLICIT")
        else:
            units = {item["canonical_unit"] for item in money_records if item is not None}
            if len(units) != 1:
                reasons.append("CONFLICTING_EXPLICIT_MONEY_UNITS")
            else:
                canonical_unit = next(iter(units))
                source = "LOCAL_UNIFORM_ALL_MONEY_COLUMN_UNITS"
    return {
        "canonical_unit": canonical_unit,
        "complete": canonical_unit is not None and not reasons,
        "conflicting_surfaces": conflicting_surfaces,
        "evidence": evidence,
        "reasons": sorted(set(reasons)),
        "source": source,
        "undeclared_evidence": undeclared,
    }


def _effective_blank(cell: Any, *, fallback: Mapping[str, Any]) -> dict[str, Any]:
    if cell is not None:
        return canonical_clone_v1(cell)
    return {
        "coefficient": None,
        "source_locator": canonical_clone_v1(fallback["source_locator"]),
        "source_text": "",
        "state": "BLANK",
    }


def _flattened_child(row: Mapping[str, Any]) -> bool:
    path = row.get("hierarchy_path_exact")
    return bool(
        type(path) is list
        and len(path) == 2
        and type(path[-1]) is str
        and "\n" in path[-1]
        and _normalized(row.get("label_exact")) != _normalized(path[-1])
    )


def _extract_table_records(
    *,
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    region: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    classification = classify_gemini_json_fixed_asset_rollforward_table_v1(
        section, table, compiled_specs=compiled_specs
    )
    reasons = list(classification["reasons"])
    if not classification["complete"]:
        reasons.append("CURRENT_TABLE_CLASSIFICATION_IS_NOT_COMPLETE")
    unit_axis = _unit_axis(table, compiled_specs=compiled_specs)
    reasons.extend(unit_axis["reasons"])
    if not unit_axis["complete"]:
        reasons.append("CURRENT_TABLE_MONEY_UNIT_IS_NOT_COMPLETE")
    columns = table.get("columns")
    rows = table.get("rows")
    if type(columns) is not list or type(rows) is not list:
        raise _error("fixed-asset current table axes are invalid")
    money_ordinals = classification["money_column_ordinals"]
    total_ordinal = (
        classification["total_column_ordinals"][0]
        if classification["total_column_ordinals"]
        else None
    )
    if total_ordinal is None:
        return {
            "classification": classification,
            "mappings": [],
            "reasons": sorted(set(reasons)),
            "subtotal_collapse": None,
            "table_receipt": None,
            "unit_axis": unit_axis,
            "width_seal": None,
        }
    money_ids = [f"c{ordinal}" for ordinal in money_ordinals]
    total_id = f"c{total_ordinal}"
    records = []
    branch_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    row_by_id = {}
    for source_ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict:
            reasons.append("SOURCE_ROW_IS_NOT_AN_OBJECT")
            continue
        layout = _branch_layout_for_row(row, compiled_specs=compiled_specs)
        if layout is None or row.get("row_kind") == "GROUP":
            continue
        role = _role_for_row(row, layout, compiled_specs=compiled_specs)
        if role is None:
            reasons.append(f"UNCLASSIFIED_NUMERIC_ROW:r{source_ordinal}")
            continue
        values = row.get("values_exact")
        if type(values) is not list or len(values) != len(columns):
            reasons.append(f"SOURCE_ROW_CELL_AXIS_INVALID:r{source_ordinal}")
            continue
        row_id = f"r{source_ordinal}"
        cells = {}
        try:
            for ordinal in money_ordinals:
                column_id = f"c{ordinal}"
                cells[column_id] = _money(
                    values[ordinal - 1],
                    source_locator={
                        "column_id": column_id,
                        "page_json_version_id": region["page_json_version_id"],
                        "row_id": row_id,
                        "section_id": region["section_id"],
                        "table_id": region["table_id"],
                    },
                )
        except GeminiJsonFixedAssetRollforwardFamilyV1Error:
            reasons.append(f"MONEY_CELL_INVALID:{row_id}")
            continue
        if all(cell["state"] == "BLANK" for cell in cells.values()):
            continue
        record = {
            "branch_role": layout["branch_role"],
            "cells": cells,
            "flattened_child": _flattened_child(row),
            "hierarchy_path_exact": canonical_clone_v1(row.get("hierarchy_path_exact")),
            "label_exact": row.get("label_exact"),
            "role": role,
            "row_id": row_id,
            "row_kind": row.get("row_kind"),
            "source_ordinal": source_ordinal,
        }
        records.append(record)
        branch_records[layout["branch_role"]].append(record)
        row_by_id[row_id] = record
    block_by_subtotal: dict[str, list[str]] = {}
    parent_by_child: dict[str, str] = {}
    direct_by_branch: dict[str, list[str]] = defaultdict(list)
    branch_layout_by_role = {
        item["branch_role"]: item for item in compiled_specs["evaluation"]["branch_layouts"]
    }
    for branch_role, branch_axis in branch_records.items():
        layout = branch_layout_by_role[branch_role]
        current_subtotal = None
        for record in branch_axis:
            path = record["hierarchy_path_exact"]
            is_child = bool(type(path) is list and (len(path) >= 3 or record["flattened_child"]))
            if record["role"] in layout["subtotal_roles"] and not is_child:
                current_subtotal = record
                block_by_subtotal.setdefault(record["row_id"], [])
                direct_by_branch[branch_role].append(record["row_id"])
                continue
            if is_child:
                if current_subtotal is None:
                    reasons.append(
                        f"VISIBLE_SUBTOTAL_CHILD_HAS_NO_PRECEDING_SUBTOTAL:{record['row_id']}"
                    )
                    continue
                parent_by_child[record["row_id"]] = current_subtotal["row_id"]
                block_by_subtotal[current_subtotal["row_id"]].append(record["row_id"])
                continue
            current_subtotal = None
            if record["role"] not in {layout["opening_role"], layout["ending_role"]}:
                direct_by_branch[branch_role].append(record["row_id"])
    # One-child subtotals are neither a complete visible block nor an
    # independent direct movement frontier.
    if any(len(children) == 1 for children in block_by_subtotal.values()):
        reasons.append("VISIBLE_SUBTOTAL_REQUIRES_AT_LEAST_TWO_DIRECT_CHILDREN")
    equations = []
    for record in records:
        detail_numeric = [
            column_id
            for column_id in money_ids[:-1]
            if record["cells"][column_id]["state"] != "BLANK"
        ]
        omitted_candidate = None
        if detail_numeric:
            rightmost = detail_numeric[-1]
            preceding = [
                column_id for column_id in detail_numeric if int(column_id[1:]) < int(rightmost[1:])
            ]
            rightmost_coefficient = record["cells"][rightmost]["coefficient"]
            if (
                preceding
                and rightmost_coefficient
                == sum(record["cells"][column_id]["coefficient"] for column_id in preceding)
                and all(
                    record["cells"][f"c{ordinal}"]["state"] == "BLANK"
                    for ordinal in money_ordinals
                    if int(rightmost[1:]) < ordinal < total_ordinal
                )
                and (
                    record["cells"][total_id]["state"] == "BLANK"
                    or (
                        record["cells"][total_id]["coefficient"] == rightmost_coefficient
                        and record["cells"][total_id]["state"]
                        == record["cells"][rightmost]["state"]
                        and record["cells"][total_id]["source_text"]
                        == record["cells"][rightmost]["source_text"]
                    )
                )
            ):
                omitted_candidate = rightmost
        term_ids = [column_id for column_id in detail_numeric if column_id != omitted_candidate]
        if not term_ids:
            reasons.append(f"HORIZONTAL_EQUATION_HAS_NO_VISIBLE_DETAIL_TERM:{record['row_id']}")
            continue
        equations.append(
            {
                "axis": "HORIZONTAL_ROW",
                "equation_id": f"horizontal:{record['row_id']}",
                "result": {"column_id": total_id, "row_id": record["row_id"]},
                "terms": [
                    {"column_id": column_id, "multiplier": 1, "row_id": record["row_id"]}
                    for column_id in term_ids
                ],
            }
        )
    for subtotal_id, child_ids in block_by_subtotal.items():
        if len(child_ids) < 2:
            continue
        for column_id in money_ids:
            involved = [row_by_id[subtotal_id], *(row_by_id[child_id] for child_id in child_ids)]
            if any(item["cells"][column_id]["state"] == "BLANK" for item in involved):
                continue
            equations.append(
                {
                    "axis": "VERTICAL_ROLLFORWARD",
                    "equation_id": f"subtotal:{subtotal_id}:{column_id}",
                    "result": {"column_id": column_id, "row_id": subtotal_id},
                    "terms": [
                        {"column_id": column_id, "multiplier": 1, "row_id": child_id}
                        for child_id in child_ids
                    ],
                }
            )
    signed_layouts = [
        item
        for item in compiled_specs["evaluation"]["branch_layouts"]
        if item["rollforward_kind"] == "SIGNED_ADDITIVE"
    ]
    carrying_layout = next(
        (
            item
            for item in compiled_specs["evaluation"]["branch_layouts"]
            if item["rollforward_kind"] == "COST_AND_DEPRECIATION_CONTROL"
        ),
        None,
    )
    endpoint_by_role: dict[str, list[str]] = defaultdict(list)
    for record in records:
        endpoint_by_role[record["role"]].append(record["row_id"])
    for layout in compiled_specs["evaluation"]["branch_layouts"]:
        for role in (layout["opening_role"], layout["ending_role"]):
            if len(endpoint_by_role[role]) != 1:
                reasons.append(f"EXACT_ONE_BRANCH_ENDPOINT_REQUIRED:{role}")
        opening_ids = endpoint_by_role[layout["opening_role"]]
        ending_ids = endpoint_by_role[layout["ending_role"]]
        if len(opening_ids) == len(ending_ids) == 1:
            opening_ordinal = row_by_id[opening_ids[0]]["source_ordinal"]
            ending_ordinal = row_by_id[ending_ids[0]]["source_ordinal"]
            movement_ordinals = [
                record["source_ordinal"]
                for record in branch_records[layout["branch_role"]]
                if record["role"] not in {layout["opening_role"], layout["ending_role"]}
            ]
            if not (
                opening_ordinal < ending_ordinal
                and all(opening_ordinal < ordinal < ending_ordinal for ordinal in movement_ordinals)
            ):
                reasons.append(
                    f"BRANCH_SOURCE_ORDER_OPENING_MOVEMENTS_ENDING_INVALID:{layout['branch_role']}"
                )
    for layout in signed_layouts:
        opening_ids = endpoint_by_role[layout["opening_role"]]
        ending_ids = endpoint_by_role[layout["ending_role"]]
        if len(opening_ids) == len(ending_ids) == 1:
            equations.append(
                {
                    "axis": "VERTICAL_ROLLFORWARD",
                    "equation_id": f"branch:{layout['branch_role']}",
                    "result": {"column_id": total_id, "row_id": ending_ids[0]},
                    "terms": [
                        {"column_id": total_id, "multiplier": 1, "row_id": opening_ids[0]},
                        *[
                            {"column_id": total_id, "multiplier": 1, "row_id": row_id}
                            for row_id in direct_by_branch[layout["branch_role"]]
                        ],
                    ],
                }
            )
    if carrying_layout is not None and all(
        len(endpoint_by_role[layout[endpoint]]) == 1
        for layout in [*signed_layouts, carrying_layout]
        for endpoint in ("opening_role", "ending_role")
    ):
        cost_layout = next(
            layout for layout in signed_layouts if layout["opening_role"].startswith("COST_")
        )
        depreciation_layout = next(
            layout for layout in signed_layouts if layout["opening_role"].startswith("DEP_")
        )
        dep_values = [
            row_by_id[endpoint_by_role[depreciation_layout[key]][0]]["cells"][total_id][
                "coefficient"
            ]
            for key in ("opening_role", "ending_role")
        ]
        if all(type(value) is int and value <= 0 for value in dep_values):
            depreciation_multiplier = 1
        elif all(type(value) is int and value >= 0 for value in dep_values):
            depreciation_multiplier = -1
        else:
            depreciation_multiplier = None
            reasons.append("DEPRECIATION_ENDPOINT_SIGN_CONVENTION_IS_MIXED_OR_BLANK")
        if depreciation_multiplier is not None:
            for endpoint in ("opening_role", "ending_role"):
                carry_role = carrying_layout[endpoint]
                cost_role = cost_layout[endpoint]
                depreciation_role = depreciation_layout[endpoint]
                equations.append(
                    {
                        "axis": "VERTICAL_ROLLFORWARD",
                        "equation_id": f"carrying:{carry_role}",
                        "result": {
                            "column_id": total_id,
                            "row_id": endpoint_by_role[carry_role][0],
                        },
                        "terms": [
                            {
                                "column_id": total_id,
                                "multiplier": 1,
                                "row_id": endpoint_by_role[cost_role][0],
                            },
                            {
                                "column_id": total_id,
                                "multiplier": depreciation_multiplier,
                                "row_id": endpoint_by_role[depreciation_role][0],
                            },
                        ],
                    }
                )
    width_input = None
    width_seal = None
    if not reasons:
        authority_sha256 = canonical_json_sha256_v1(compiled_specs["evaluation"])
        width_input = {
            "columns": [
                {
                    "column_id": column_id,
                    "column_kind": "TOTAL" if column_id == total_id else "DETAIL",
                    "column_ordinal": ordinal,
                }
                for ordinal, column_id in enumerate(money_ids)
            ],
            "equation_inventory": build_accounting_equation_inventory_manifest_v1(
                equations,
                authority_kind="PINNED_CONFIG",
                authority_ref=(
                    compiled_specs["topology"]["family_id"] + ":" + EVALUATION_FORMAT_VERSION
                ),
                authority_sha256=authority_sha256,
            ),
            "equations": equations,
            "period_id": region["period_end_date"] or "CURRENT_PERIOD",
            "rows": [
                {
                    "cells": canonical_clone_v1(record["cells"]),
                    "row_id": record["row_id"],
                    "row_kind": "DATA",
                    "row_ordinal": ordinal,
                }
                for ordinal, record in enumerate(records)
            ],
            "table_id": region["table_id"],
            "unit_id": unit_axis["canonical_unit"],
        }
        width_seal = build_accounting_row_width_total_column_seal_v1(width_input)
        if width_seal["status"] == "UNRESOLVED":
            reasons.extend(width_seal["unresolved_reasons"])
    effective_by_row = {}
    if width_seal is not None:
        effective_by_row = {
            row["row_id"]: row["cells"] for row in width_seal["effective_projection"]["rows"]
        }
    collapse_input_rows = []
    collapse_mappings = []
    collapse_frontiers = []
    prior_branch = None
    for record in records:
        branch_role = record["branch_role"]
        if prior_branch is not None and prior_branch != branch_role:
            collapse_input_rows.append(
                {
                    "cells": {
                        total_id: {
                            "coefficient": None,
                            "source_locator": {"synthetic_reset": branch_role},
                            "source_text": "",
                            "state": "BLANK",
                        }
                    },
                    "hierarchy_level": 0,
                    "money_lane_ids": [total_id],
                    "period_id": region["period_end_date"] or "CURRENT_PERIOD",
                    "root_id": branch_role,
                    "row_id": f"reset:{branch_role}",
                    "row_kind": "RESET",
                    "row_ordinal": len(collapse_input_rows),
                    "source_parent_row_id": None,
                    "table_id": region["table_id"],
                    "unit_id": unit_axis["canonical_unit"] or "UNRESOLVED_UNIT",
                }
            )
        prior_branch = branch_role
        children = block_by_subtotal.get(record["row_id"], [])
        parent_id = parent_by_child.get(record["row_id"])
        if children:
            block_records = [record, *(row_by_id[row_id] for row_id in children)]
            lane_ids = [
                column_id
                for column_id in money_ids
                if all(
                    _effective_blank(
                        effective_by_row[item["row_id"]].get(column_id),
                        fallback=item["cells"][column_id],
                    )["state"]
                    != "BLANK"
                    for item in block_records
                )
            ]
        elif parent_id is not None:
            subtotal = row_by_id[parent_id]
            siblings = block_by_subtotal[parent_id]
            block_records = [subtotal, *(row_by_id[row_id] for row_id in siblings)]
            lane_ids = [
                column_id
                for column_id in money_ids
                if all(
                    _effective_blank(
                        effective_by_row[item["row_id"]].get(column_id),
                        fallback=item["cells"][column_id],
                    )["state"]
                    != "BLANK"
                    for item in block_records
                )
            ]
        else:
            lane_ids = [total_id]
        lane_ids = lane_ids or [total_id]
        source_parent = (
            (f"root:{branch_role}" if record["flattened_child"] else parent_id)
            if parent_id is not None
            else f"root:{branch_role}"
        )
        collapse_input_rows.append(
            {
                "cells": {
                    column_id: _effective_blank(
                        effective_by_row.get(record["row_id"], record["cells"]).get(column_id),
                        fallback=record["cells"][column_id],
                    )
                    for column_id in lane_ids
                },
                "hierarchy_level": 2 if parent_id is not None else 1,
                "money_lane_ids": lane_ids,
                "period_id": region["period_end_date"] or "CURRENT_PERIOD",
                "root_id": branch_role,
                "row_id": record["row_id"],
                "row_kind": (
                    "DETAIL"
                    if parent_id is not None
                    else ("SUBTOTAL" if len(children) >= 2 else "PEER")
                ),
                "row_ordinal": len(collapse_input_rows),
                "source_parent_row_id": source_parent,
                "table_id": region["table_id"],
                "unit_id": unit_axis["canonical_unit"] or "UNRESOLVED_UNIT",
            }
        )
        mapping_id = f"mapping:{record['row_id']}:{record['role']}"
        collapse_mappings.append(
            {"mapping_id": mapping_id, "role_id": record["role"], "row_id": record["row_id"]}
        )
        if len(children) >= 2:
            collapse_frontiers.append(
                {
                    "equation_id": f"branch:{branch_role}",
                    "mapping_ids": [mapping_id],
                    "subtotal_row_id": record["row_id"],
                }
            )
    collapse_source = {
        "equation_frontiers": collapse_frontiers,
        "mappings": collapse_mappings,
        "rows": collapse_input_rows,
    }
    subtotal_collapse = None
    if effective_by_row and collapse_input_rows:
        subtotal_collapse = build_ordered_visible_subtotal_block_collapse_v1(collapse_source)
        if subtotal_collapse["status"] == "UNRESOLVED":
            reasons.extend(subtotal_collapse["unresolved_reasons"])
    records_by_role: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if effective_by_row:
        for record in records:
            cell = _effective_blank(
                effective_by_row[record["row_id"]].get(total_id),
                fallback=record["cells"][total_id],
            )
            if cell["state"] != "BLANK":
                records_by_role[record["role"]].append({"cell": cell, "record": record})
    mappings = []
    if not reasons:
        for role in compiled_specs["output_role_order"]:
            observations = records_by_role.get(role, [])
            if not observations:
                continue
            coefficient = sum(item["cell"]["coefficient"] for item in observations)
            source_refs = [
                {
                    "cell": canonical_clone_v1(item["cell"]),
                    "hierarchy_path_exact": canonical_clone_v1(
                        item["record"]["hierarchy_path_exact"]
                    ),
                    "label_exact": item["record"]["label_exact"],
                    "row_id": item["record"]["row_id"],
                    "source_ordinal": item["record"]["source_ordinal"],
                }
                for item in observations
            ]
            row_id = (
                observations[0]["record"]["row_id"]
                if len(observations) == 1
                else "aggregate:" + role
            )
            material = {
                "bound_unit": unit_axis["canonical_unit"],
                "cell": {
                    "coefficient": coefficient,
                    "state": (
                        observations[0]["cell"]["state"]
                        if len(observations) == 1
                        else "AGGREGATED_EXACT_SAME_ROLE_SOURCE_ROWS"
                    ),
                },
                "period_date": region["period_end_date"],
                "report_norm_id": compiled_specs["bindings"][role],
                "role": role,
                "row_id": row_id,
                "source_refs": source_refs,
            }
            mappings.append(
                {
                    **material,
                    "item_mapping_id": "gjffarimv1:item:" + canonical_json_sha256_v1(material),
                }
            )
    table_receipt = {
        "classification": classification,
        "equations": equations,
        "raw_row_inventory": [
            {
                "branch_role": record["branch_role"],
                "hierarchy_path_exact": canonical_clone_v1(record["hierarchy_path_exact"]),
                "label_exact": record["label_exact"],
                "role": record["role"],
                "row_id": record["row_id"],
                "source_ordinal": record["source_ordinal"],
            }
            for record in records
        ],
        "unit_axis": unit_axis,
    }
    return {
        "classification": classification,
        "mappings": mappings,
        "reasons": sorted(set(reasons)),
        "subtotal_collapse": subtotal_collapse,
        "table_receipt": table_receipt,
        "unit_axis": unit_axis,
        "width_seal": width_seal,
    }


def evaluate_gemini_json_fixed_asset_rollforward_family_cluster_v1(
    *,
    regions: Any,
    control_regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate one current fixed-asset table and retain typed controls."""

    current = _region_axis(regions, component_role="CURRENT_TABLE", maximum=1)
    controls = _region_axis(control_regions, component_role="COMPARATIVE_CONTROL_TABLE", maximum=8)
    expected_receipt = build_gemini_json_fixed_asset_rollforward_region_query_receipt_v1(
        current, control_regions=controls
    )
    if type(query_receipt) is not dict or not same_typed_json_v1(query_receipt, expected_receipt):
        raise _error("fixed-asset query receipt does not bind current/control regions")
    if len(current) != 1:
        raise _error("fixed-asset evaluator needs exactly one current table")
    region = current[0]
    page_json = page_json_by_version.get(region["page_json_version_id"])
    if type(page_json) is not dict:
        raise _error("fixed-asset current page JSON is absent")
    section, table = _source_table(
        page_json, section_id=region["section_id"], table_id=region["table_id"]
    )
    extracted = _extract_table_records(
        section=section,
        table=table,
        region=region,
        compiled_specs=compiled_specs,
    )
    reasons = extracted["reasons"]
    mappings = extracted["mappings"] if not reasons else []
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "closure_receipt": {
            "control_regions": controls,
            "query_receipt": expected_receipt,
            "structural_root_receipt": {
                "emitted_mapping": False,
                "mapping_policy": compiled_specs["schema"]["structural_root_mapping_policy"],
                "report_norm_id": compiled_specs["schema"]["family_root_report_norm_id"],
                "role": compiled_specs["topology"]["parent"]["role"],
            },
            "subtotal_collapse": extracted["subtotal_collapse"],
            "table_receipt": extracted["table_receipt"],
            "width_seal": extracted["width_seal"],
        },
        "component_regions": current,
        "control_regions": controls,
        "document_id": region["document_id"],
        "family_id": compiled_specs["topology"]["family_id"],
        "mappings": mappings,
        "page_json_version_id": region["page_json_version_id"],
        "physical_page": region["physical_page"],
        "reasons": reasons,
        "section_id": region["section_id"],
        "source_logical_name": region["source_logical_name"],
        "source_sha256": region["source_sha256"],
        "status": READY if mappings and not reasons else UNRESOLVED,
        "table_id": region["table_id"],
    }
    return {
        "candidate_id": "gjffarcv1:candidate:" + canonical_json_sha256_v1(material),
        **material,
    }


def validate_gemini_json_fixed_asset_rollforward_family_candidate_replay_v1(
    value: Any,
    *,
    regions: Any,
    control_regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    rebuilt = evaluate_gemini_json_fixed_asset_rollforward_family_cluster_v1(
        regions=regions,
        control_regions=control_regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if type(value) is not dict or not same_typed_json_v1(value, rebuilt):
        raise _error("fixed-asset candidate does not replay exactly")
    return rebuilt


def build_gemini_json_indexed_fixed_asset_rollforward_query_evidence_v1(
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
            "cluster": cluster,
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
        "accepted_control_region_count": sum(
            len(item.get("control_regions", [])) for item in accepted
        ),
        "accepted_current_region_count": sum(
            len(item.get("component_regions", [])) for item in accepted
        ),
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
        "query_evidence_id": "gjffareqv1:evidence:" + canonical_json_sha256_v1(material),
    }


def validate_gemini_json_indexed_fixed_asset_rollforward_query_evidence_v1(
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
        raise _error("indexed fixed-asset query evidence is invalid")
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
        raise _error("indexed fixed-asset document axis is incomplete")
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
            raise _error("indexed fixed-asset document axis is invalid")
        by_ordinal[ordinal] = document
    page_fields = document_fields | {
        "page_json_version_id",
        "physical_page",
        "selected_page_ordinal",
    }
    page_versions = []
    per_document: dict[int, int] = defaultdict(int)
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
            raise _error("indexed fixed-asset page axis is invalid")
        prior_document = page["document_ordinal"]
        per_document[page["document_ordinal"]] += 1
        if page.get("selected_page_ordinal") != per_document[page["document_ordinal"]]:
            raise _error("indexed fixed-asset page order is incomplete")
        page_versions.append(page["page_json_version_id"])
    if len(page_versions) != len(set(page_versions)) or set(per_document) != set(by_ordinal):
        raise _error("indexed fixed-asset page frontier is incomplete")
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
            != "gjffarfcv1:cluster:"
            + canonical_json_sha256_v1(
                {key: item for key, item in cluster.items() if key != "cluster_id"}
            )
        ):
            raise _error("indexed fixed-asset cluster binding drifted")
        regions = cluster.get("component_regions")
        controls = cluster.get("control_regions")
        reasons = cluster.get("reasons")
        if (
            type(reasons) is not list
            or reasons != sorted(set(reasons))
            or type(controls) is not list
            or (cluster["status"] == READY and (len(regions) != 1 or reasons))
            or (cluster["status"] == NOT_OBSERVED and (regions or controls or reasons))
            or (cluster["status"] == UNRESOLVED and (not reasons or regions or controls))
        ):
            raise _error("indexed fixed-asset disposition drifted")
        if cluster["status"] == READY:
            _region_axis(regions, component_role="CURRENT_TABLE", maximum=1)
            _region_axis(controls, component_role="COMPARATIVE_CONTROL_TABLE", maximum=8)
            accepted.append(cluster)
    if not same_typed_json_v1(value["accepted_clusters"], accepted):
        raise _error("indexed fixed-asset accepted cluster axis drifted")
    expected_receipt = {
        "accepted_cluster_axis_sha256": canonical_json_sha256_v1(accepted),
        "accepted_cluster_count": len(accepted),
        "accepted_control_region_count": sum(len(item["control_regions"]) for item in accepted),
        "accepted_current_region_count": sum(len(item["component_regions"]) for item in accepted),
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
        raise _error("indexed fixed-asset query receipt drifted")
    material = {key: canonical_clone_v1(value[key]) for key in fields - {"query_evidence_id"}}
    if value["query_evidence_id"] != "gjffareqv1:evidence:" + canonical_json_sha256_v1(material):
        raise _error("indexed fixed-asset evidence identity drifted")
    return canonical_clone_v1(value)


def validate_gemini_json_fixed_asset_rollforward_sweep_query_bindings_v1(
    *, trials: Any, indexed_query_evidence: Any, compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    evidence = validate_gemini_json_indexed_fixed_asset_rollforward_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
    documents = evidence["selected_document_axis"]
    if type(trials) is not list or len(trials) != len(documents):
        raise _error("fixed-asset sweep trial axis is incomplete")
    accepted = {item["document_ordinal"]: item for item in evidence["accepted_clusters"]}
    checked = []
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
            raise _error("fixed-asset sweep trial identity drifted")
        if disposition["disposition"] == READY:
            if len(trial["candidates"]) != 1:
                raise _error("accepted fixed-asset source needs exactly one candidate")
            candidate = trial["candidates"][0]
            cluster = accepted[ordinal]
            if not same_typed_json_v1(
                candidate.get("component_regions"), cluster["component_regions"]
            ) or not same_typed_json_v1(
                candidate.get("control_regions"), cluster["control_regions"]
            ):
                raise _error("fixed-asset candidate region binding drifted")
            if candidate.get("status") == READY:
                if (
                    trial.get("status") != READY
                    or trial.get("selected_candidate_id") != candidate.get("candidate_id")
                    or not same_typed_json_v1(trial.get("mappings"), candidate.get("mappings"))
                    or trial.get("reasons")
                ):
                    raise _error("fixed-asset READY trial drifted")
            elif (
                trial.get("status") != UNRESOLVED
                or trial.get("selected_candidate_id") is not None
                or trial.get("mappings")
                or trial.get("reasons") != candidate.get("reasons")
            ):
                raise _error("fixed-asset unresolved candidate drifted")
        elif disposition["disposition"] == NOT_OBSERVED:
            if (
                trial.get("status") != NOT_OBSERVED
                or trial["candidates"]
                or trial.get("mappings")
                or trial.get("reasons")
                or trial.get("selected_candidate_id") is not None
            ):
                raise _error("fixed-asset not-observed trial drifted")
        elif (
            trial.get("status") != UNRESOLVED
            or trial["candidates"]
            or trial.get("mappings")
            or trial.get("selected_candidate_id") is not None
            or trial.get("reasons") != disposition["cluster"]["reasons"]
        ):
            raise _error("fixed-asset unresolved source disposition drifted")
        checked.append(canonical_clone_v1(trial))
    return checked
