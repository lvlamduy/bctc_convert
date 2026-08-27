"""Authenticated composition of disjoint Gemini JSON accounting fragments.

The primitive is deliberately family-configured rather than bank/page routed.
It projects exact, manifest-selected JSON table cells into one bounded document
region, composes only reset-fenced source fragments, and delegates all
accounting closure to the existing hierarchical evaluator.  It never reads a
PDF, invokes OCR, or treats a synthetic table as source evidence.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    READY,
    UNRESOLVED,
)
from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import (
    _money,
    _normalized,
    _period_signature,
    _row_role_match_modes,
    evaluate_gemini_json_hierarchical_family_table_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
)

POLICY_FORMAT_VERSION = "DOCUMENT_REGION_FRAGMENT_COMPOSER_POLICY_V1"
FRAGMENT_FORMAT_VERSION = "DOCUMENT_REGION_FRAGMENT_CANDIDATE_V1"
COMPOSITION_FORMAT_VERSION = "DOCUMENT_REGION_FRAGMENT_COMPOSITION_V1"
RECEIPT_FORMAT_VERSION = "DOCUMENT_REGION_FRAGMENT_COMPOSITION_RECEIPT_V1"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_EXACT_PAGE_TABLE_ROW_CELL_PROJECTION_ONLY_"
    "BOUNDED_RESET_FENCED_DOCUMENT_REGION_FRAGMENT_COMPOSITION_EXACT_PERIOD_"
    "UNIT_DUPLICATE_CORROBORATION_AND_EXISTING_ACCOUNTING_CLOSURE_REPLAY_NO_"
    "PDF_GEOMETRY_OCR_BANK_FILE_PAGE_ROUTING_BACKSOLVE_OR_EXPORT_AUTHORITY"
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_VERSION_ID = re.compile(r"^gfpstorev1:json:[0-9a-f]{64}$")
_CONTINUES_FROM_PREVIOUS = {"BOTH", "CONTINUES_FROM_PREVIOUS_PAGE"}
_CONTINUES_ON_NEXT = {"BOTH", "CONTINUES_ON_NEXT_PAGE"}


class DocumentRegionFragmentComposerV1Error(ValueError):
    """The policy, selected source frontier, or replay evidence drifted."""


def _error(message: str) -> DocumentRegionFragmentComposerV1Error:
    return DocumentRegionFragmentComposerV1Error(message)


def _node_index(identifier: Any, prefix: str, limit: int) -> int:
    if type(identifier) is not str or re.fullmatch(rf"{prefix}[1-9][0-9]*", identifier) is None:
        raise _error("document-region fragment node identity is invalid")
    index = int(identifier[len(prefix) :]) - 1
    if not 0 <= index < limit:
        raise _error("document-region fragment node identity is out of range")
    return index


def _source_nodes(
    page_json: Mapping[str, Any], *, section_id: str, table_id: str
) -> tuple[dict[str, Any], dict[str, Any], int, int]:
    sections = page_json.get("sections")
    if type(sections) is not list:
        raise _error("document-region page has no section axis")
    section_index = _node_index(section_id, "s", len(sections))
    section = sections[section_index]
    tables = section.get("tables") if type(section) is dict else None
    if type(tables) is not list:
        raise _error("document-region section has no table axis")
    table_index = _node_index(table_id, "t", len(tables))
    table = tables[table_index]
    if type(table) is not dict:
        raise _error("document-region table is invalid")
    return section, table, section_index + 1, table_index + 1


def _contains_alias(value: Any, aliases: Sequence[str]) -> list[str]:
    folded = _normalized(value)
    if not folded:
        return []
    padded = f" {folded} "
    return [alias for alias in aliases if alias == folded or f" {alias} " in padded]


def _compile_aliases(values: Any, *, field: str, allow_empty: bool = False) -> list[str]:
    if type(values) is not list or (not values and not allow_empty):
        raise _error(f"document-region {field} aliases are invalid")
    normalized = [_normalized(value) for value in values]
    if any(
        type(value) is not str or not value or not folded
        for value, folded in zip(values, normalized, strict=True)
    ):
        raise _error(f"document-region {field} aliases are invalid")
    if len(set(normalized)) != len(normalized):
        raise _error(f"document-region {field} aliases normalize ambiguously")
    return normalized


def compile_document_region_fragment_composer_policy_v1(
    policy: Any, *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Compile one data-only region composer policy against family specs."""

    fields = {
        "allow_distinctive_child_cluster_cross_page",
        "branch_aliases",
        "control_surface_aliases",
        "cross_page_policy",
        "distinctive_child_roles",
        "duplicate_policy",
        "exhaustiveness_policy",
        "family_id",
        "format_version",
        "hard_negative_aliases",
        "maximum_components",
        "maximum_page_span",
        "minimum_distinctive_child_roles",
        "owner_aliases",
        "period_axis_cardinality",
        "period_axis_semantics",
        "reset_aliases",
        "unit_aliases",
    }
    topology = compiled_specs.get("topology") if type(compiled_specs) is dict else None
    if (
        type(policy) is not dict
        or set(policy) != fields
        or type(topology) is not dict
        or policy.get("format_version") != POLICY_FORMAT_VERSION
        or policy.get("family_id") != topology.get("family_id")
        or type(policy.get("maximum_components")) is not int
        or not 1 <= policy["maximum_components"] <= 32
        or type(policy.get("maximum_page_span")) is not int
        or not 1 <= policy["maximum_page_span"] <= 4
        or type(policy.get("allow_distinctive_child_cluster_cross_page")) is not bool
        or policy.get("cross_page_policy") != "LOCAL_OWNER_OR_BRANCH_OR_EXPLICIT_CONTINUATION"
        or policy.get("duplicate_policy")
        != "EXACT_ROLE_PERIOD_UNIT_VALUE_CORROBORATE_OTHERWISE_UNRESOLVED"
        or policy.get("exhaustiveness_policy")
        != "ALL_ROLE_BEARING_MONEY_TABLES_IN_FENCED_SELECTED_PAGE_INTERVAL"
        or type(policy.get("period_axis_cardinality")) is not int
        or policy["period_axis_cardinality"] not in {1, 2}
        or policy.get("period_axis_semantics") != "EXACT_DOCUMENT_ACCOUNTING_PERIOD_AXIS"
    ):
        raise _error("document-region fragment composer policy is invalid")
    known_roles = {topology["parent"]["role"]} | {child["role"] for child in topology["children"]}
    distinctive_roles = policy["distinctive_child_roles"]
    minimum = policy["minimum_distinctive_child_roles"]
    if (
        type(distinctive_roles) is not list
        or not distinctive_roles
        or len(set(distinctive_roles)) != len(distinctive_roles)
        or any(
            role not in known_roles or role == topology["parent"]["role"]
            for role in distinctive_roles
        )
        or type(minimum) is not int
        or not 2 <= minimum <= len(distinctive_roles)
    ):
        raise _error("document-region distinctive child cluster policy is invalid")
    owner_aliases = _compile_aliases(policy["owner_aliases"], field="owner")
    topology_owner_aliases = {_normalized(value) for value in topology["parent"]["aliases"]}
    if not set(owner_aliases) <= topology_owner_aliases:
        raise _error("document-region owner aliases are outside the family topology")
    compiled = canonical_clone_v1(policy)
    compiled["owner_aliases"] = owner_aliases
    compiled["branch_aliases"] = _compile_aliases(
        policy["branch_aliases"], field="branch", allow_empty=True
    )
    compiled["reset_aliases"] = _compile_aliases(
        policy["reset_aliases"], field="reset", allow_empty=True
    )
    compiled["hard_negative_aliases"] = _compile_aliases(
        policy["hard_negative_aliases"], field="hard-negative", allow_empty=True
    )
    compiled["control_surface_aliases"] = _compile_aliases(
        policy["control_surface_aliases"], field="control-surface", allow_empty=True
    )
    compiled["unit_aliases"] = _compile_aliases(policy["unit_aliases"], field="unit")
    compiled["policy_sha256"] = canonical_json_sha256_v1(policy)
    return compiled


def _validate_document_period_axis(
    value: Any, *, policy: Mapping[str, Any], page_records: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    fields = {
        "document_id",
        "family_id",
        "format_version",
        "period_signatures",
        "source_metadata_receipt",
        "source_metadata_receipt_sha256",
        "source_sha256",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value.get("format_version") != "DOCUMENT_REGION_ACCOUNTING_PERIOD_AXIS_V1"
        or value.get("family_id") != policy["family_id"]
        or value.get("document_id") != page_records[0]["document_id"]
        or value.get("source_sha256") != page_records[0]["source_sha256"]
        or type(value.get("source_metadata_receipt")) is not dict
        or value.get("source_metadata_receipt_sha256")
        != canonical_json_sha256_v1(value.get("source_metadata_receipt"))
    ):
        raise _error("document-region accounting period axis is invalid")
    signatures = value["period_signatures"]
    if (
        type(signatures) is not list
        or len(signatures) != policy["period_axis_cardinality"]
        or any(
            type(signature) is not list
            or len(signature) != 2
            or signature[0] not in {"DATE", "SEMANTIC_ALIAS"}
            or type(signature[1]) is not str
            or not signature[1]
            for signature in signatures
        )
        or len({tuple(signature) for signature in signatures}) != len(signatures)
    ):
        raise _error("document-region accounting period signatures are invalid")
    return canonical_clone_v1(value)


def _validate_selected_page_records(
    page_records: Any,
    *,
    selected_page_json_version_ids: Sequence[str],
) -> list[dict[str, Any]]:
    required = {
        "document_id",
        "page_json",
        "page_json_version_id",
        "physical_page",
        "selected_frontier_ordinal",
        "source_logical_name",
        "source_sha256",
    }
    if (
        type(selected_page_json_version_ids) not in {list, tuple}
        or not selected_page_json_version_ids
        or len(set(selected_page_json_version_ids)) != len(selected_page_json_version_ids)
        or any(_VERSION_ID.fullmatch(value) is None for value in selected_page_json_version_ids)
        or type(page_records) not in {list, tuple}
        or not page_records
    ):
        raise _error("document-region selected page frontier is invalid")
    output = []
    for record in page_records:
        if (
            type(record) is not dict
            or set(record) != required
            or type(record["document_id"]) is not str
            or not record["document_id"]
            or type(record["source_logical_name"]) is not str
            or not record["source_logical_name"]
            or type(record["source_sha256"]) is not str
            or _SHA256.fullmatch(record["source_sha256"]) is None
            or type(record["selected_frontier_ordinal"]) is not int
            or not 1 <= record["selected_frontier_ordinal"] <= len(selected_page_json_version_ids)
            or selected_page_json_version_ids[record["selected_frontier_ordinal"] - 1]
            != record["page_json_version_id"]
            or _VERSION_ID.fullmatch(record["page_json_version_id"]) is None
            or type(record["physical_page"]) is not int
            or record["physical_page"] <= 0
            or type(record["page_json"]) is not dict
            or type(record["page_json"].get("sections")) is not list
        ):
            raise _error("document-region selected page record is invalid")
        output.append(canonical_clone_v1(record))
    identity = {
        (item["document_id"], item["source_logical_name"], item["source_sha256"]) for item in output
    }
    ordinals = [item["selected_frontier_ordinal"] for item in output]
    physical_pages = [item["physical_page"] for item in output]
    if (
        len(identity) != 1
        or ordinals != sorted(ordinals)
        or len(set(ordinals)) != len(ordinals)
        or ordinals != list(range(ordinals[0], ordinals[-1] + 1))
        or physical_pages != sorted(physical_pages)
        or len(set(physical_pages)) != len(physical_pages)
    ):
        raise _error("document-region selected pages are not one contiguous source interval")
    return output


def _table_surfaces(
    *, page_record: Mapping[str, Any], section_id: str, table_id: str
) -> list[dict[str, Any]]:
    section, table, section_ordinal, table_ordinal = _source_nodes(
        page_record["page_json"], section_id=section_id, table_id=table_id
    )
    common = {
        "page_json_version_id": page_record["page_json_version_id"],
        "physical_page": page_record["physical_page"],
        "section_id": section_id,
        "selected_frontier_ordinal": page_record["selected_frontier_ordinal"],
    }
    surfaces = []
    if type(section.get("title_exact")) is str and section["title_exact"]:
        surfaces.append(
            {
                **common,
                "position": [page_record["selected_frontier_ordinal"], section_ordinal, 0, 0, 0],
                "source_exact": section["title_exact"],
                "source_kind": "SECTION_TITLE",
                "table_id": None,
            }
        )
    narratives = section.get("narratives_exact")
    if type(narratives) is list:
        for narrative_ordinal, narrative in enumerate(narratives, start=1):
            if type(narrative) is str and narrative:
                surfaces.append(
                    {
                        **common,
                        "narrative_ordinal": narrative_ordinal,
                        "position": [
                            page_record["selected_frontier_ordinal"],
                            section_ordinal,
                            0,
                            1,
                            narrative_ordinal,
                        ],
                        "source_exact": narrative,
                        "source_kind": "SECTION_NARRATIVE",
                        "table_id": None,
                    }
                )
    if type(table.get("title_exact")) is str and table["title_exact"]:
        surfaces.append(
            {
                **common,
                "position": [
                    page_record["selected_frontier_ordinal"],
                    section_ordinal,
                    table_ordinal,
                    0,
                    0,
                ],
                "source_exact": table["title_exact"],
                "source_kind": "TABLE_TITLE",
                "table_id": table_id,
            }
        )
    rows = table.get("rows")
    if type(rows) is list:
        for row_ordinal, row in enumerate(rows, start=1):
            label = row.get("label_exact") if type(row) is dict else None
            if type(label) is str and label:
                surfaces.append(
                    {
                        **common,
                        "position": [
                            page_record["selected_frontier_ordinal"],
                            section_ordinal,
                            table_ordinal,
                            1,
                            row_ordinal,
                        ],
                        "row_id": f"r{row_ordinal}",
                        "source_exact": label,
                        "source_kind": "ROW_LABEL",
                        "table_id": table_id,
                    }
                )
    return surfaces


def _all_page_surfaces(page_record: Mapping[str, Any]) -> list[dict[str, Any]]:
    sections = page_record["page_json"]["sections"]
    output = []
    for section_ordinal, section in enumerate(sections, start=1):
        tables = section.get("tables") if type(section) is dict else None
        if type(tables) is not list:
            continue
        if not tables:
            # Bind title/narrative-only reset evidence to a synthetic t1 position.
            section_copy = canonical_clone_v1(section)
            section_copy["tables"] = [
                {
                    "columns": [],
                    "continuation": "NONE",
                    "rows": [],
                    "title_exact": None,
                    "unit_exact": None,
                }
            ]
            page_copy = canonical_clone_v1(page_record)
            page_copy["page_json"]["sections"][section_ordinal - 1] = section_copy
            output.extend(
                _table_surfaces(
                    page_record=page_copy, section_id=f"s{section_ordinal}", table_id="t1"
                )
            )
            continue
        # Section surfaces are emitted once; table/row surfaces once per table.
        first = _table_surfaces(
            page_record=page_record, section_id=f"s{section_ordinal}", table_id="t1"
        )
        output.extend(first)
        for table_ordinal in range(2, len(tables) + 1):
            output.extend(
                surface
                for surface in _table_surfaces(
                    page_record=page_record,
                    section_id=f"s{section_ordinal}",
                    table_id=f"t{table_ordinal}",
                )
                if surface["source_kind"] not in {"SECTION_TITLE", "SECTION_NARRATIVE"}
            )
    return sorted(output, key=lambda item: item["position"])


def _unit_signature(
    *, table: Mapping[str, Any], column: Mapping[str, Any], aliases: Sequence[str]
) -> tuple[str | None, dict[str, Any] | None]:
    sources = [
        ("TABLE_UNIT", table.get("unit_exact")),
        (
            "COLUMN_HEADER",
            " ".join(value for value in column.get("header_path_exact", []) if value),
        ),
    ]
    for source_kind, source_exact in sources:
        folded = _normalized(source_exact)
        matches = [alias for alias in aliases if folded == alias or folded.endswith(" " + alias)]
        if matches:
            longest = max(map(len, matches))
            selected = sorted(alias for alias in matches if len(alias) == longest)
            if len(selected) == 1:
                return selected[0], {
                    "declared_unit_alias": selected[0],
                    "source_exact": source_exact,
                    "source_kind": source_kind,
                }
    return None, None


def project_column_lane_document_region_fragment_v1(
    *,
    page_record: Mapping[str, Any],
    request: Mapping[str, Any],
    document_period_axis: Mapping[str, Any],
    policy: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Reference adapter for ordinary row-role/period-column tables.

    Production adapters for stacked, transposed, or multi-metric layouts emit
    the same normalized candidate contract.  The composer itself never assumes
    this column-lane layout.
    """

    request_fields = {
        "control_column_ids",
        "mapping_column_ids",
        "page_json_version_id",
        "projection_kind",
        "section_id",
        "table_id",
    }
    if (
        type(request) is not dict
        or set(request) != request_fields
        or request.get("page_json_version_id") != page_record["page_json_version_id"]
        or request.get("projection_kind") not in {"BALANCE_MAPPING", "DECLARED_CONTROL"}
        or type(request.get("mapping_column_ids")) is not list
        or type(request.get("control_column_ids")) is not list
        or len(set(request["mapping_column_ids"] + request["control_column_ids"]))
        != len(request["mapping_column_ids"] + request["control_column_ids"])
    ):
        raise _error("document-region fragment request is invalid")
    section, table, section_ordinal, table_ordinal = _source_nodes(
        page_record["page_json"],
        section_id=request["section_id"],
        table_id=request["table_id"],
    )
    columns = table.get("columns")
    rows = table.get("rows")
    if type(columns) is not list or type(rows) is not list:
        raise _error("document-region fragment table axes are invalid")
    mapping_indices = [
        _node_index(column_id, "c", len(columns)) for column_id in request["mapping_column_ids"]
    ]
    control_indices = [
        _node_index(column_id, "c", len(columns)) for column_id in request["control_column_ids"]
    ]
    money_indices = [
        index
        for index, column in enumerate(columns)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    reasons = []
    if set(mapping_indices) | set(control_indices) != set(money_indices):
        reasons.append("MONEY_COLUMN_PARTITION_IS_NOT_EXHAUSTIVE")
    if request["projection_kind"] == "DECLARED_CONTROL" and mapping_indices:
        reasons.append("DECLARED_CONTROL_EXPOSES_MAPPING_COLUMNS")
    if request["projection_kind"] == "BALANCE_MAPPING" and not mapping_indices:
        reasons.append("BALANCE_MAPPING_HAS_NO_MONEY_COLUMN")
    surfaces = _table_surfaces(
        page_record=page_record,
        section_id=request["section_id"],
        table_id=request["table_id"],
    )
    header_surfaces = [
        {
            "source_exact": " ".join(
                value for value in column.get("header_path_exact", []) if type(value) is str
            ),
            "source_kind": "COLUMN_HEADER",
        }
        for column in columns
        if type(column) is dict
    ]
    declared_control = any(
        _contains_alias(surface.get("source_exact"), policy["control_surface_aliases"])
        for surface in [*surfaces, *header_surfaces]
    )
    if control_indices and not declared_control:
        reasons.append("CONTROL_MONEY_COLUMN_HAS_NO_DECLARED_CONTROL_SURFACE")
    period_records = []
    for index in mapping_indices:
        column = columns[index]
        header = " ".join(
            value for value in column.get("header_path_exact", []) if type(value) is str
        )
        signature = _period_signature(header)
        unit_signature, unit_evidence = _unit_signature(
            table=table, column=column, aliases=policy["unit_aliases"]
        )
        if signature is None or list(signature) not in document_period_axis["period_signatures"]:
            reasons.append(f"MAPPING_COLUMN_PERIOD_IS_NOT_DECLARED:c{index + 1}")
        if unit_signature is None:
            reasons.append(f"MAPPING_COLUMN_UNIT_IS_NOT_DECLARED:c{index + 1}")
        period_records.append(
            {
                "column_id": f"c{index + 1}",
                "column": canonical_clone_v1(column),
                "period_signature": list(signature) if signature is not None else None,
                "unit_evidence": unit_evidence,
                "unit_signature": unit_signature,
            }
        )
    if len({tuple(record["period_signature"] or []) for record in period_records}) != len(
        period_records
    ):
        reasons.append("FRAGMENT_MAPPING_PERIOD_REPEATS")
    enable_equivalences = (
        compiled_specs["evaluation"].get("format_version") == "ACCOUNTING_FAMILY_EVALUATION_SPEC_V8"
    )
    role_rows = []
    anonymous_rows = []
    numeric_roles: set[str] = set()
    for row_ordinal, row in enumerate(rows, start=1):
        values = row.get("values_exact") if type(row) is dict else None
        if type(values) is not list or len(values) != len(columns):
            raise _error("document-region row value vector drifted")
        try:
            modes = _row_role_match_modes(
                row,
                topology=compiled_specs["topology"],
                aliases_by_role=compiled_specs["aliases_by_role"],
                enable_declared_equivalences=enable_equivalences,
            )
        except ValueError:
            reasons.append(f"ROW_ROLE_ASSIGNMENT_IS_AMBIGUOUS:r{row_ordinal}")
            modes = {}
        selected_cells = []
        for period_record, index in zip(period_records, mapping_indices, strict=True):
            if values[index] is None:
                money = None
            else:
                try:
                    money = _money(values[index])
                except ValueError:
                    reasons.append(f"MAPPING_MONEY_CELL_IS_INVALID:r{row_ordinal}:c{index + 1}")
                    money = None
            selected_cells.append(
                {
                    "column_id": f"c{index + 1}",
                    "metric_signature": "UNQUALIFIED_BALANCE_AMOUNT",
                    "money": money,
                    "period_signature": canonical_clone_v1(period_record["period_signature"]),
                    "source_text": values[index],
                    "unit_signature": period_record["unit_signature"],
                }
            )
        has_visible_mapping_value = any(cell["source_text"] is not None for cell in selected_cells)
        if modes and has_visible_mapping_value:
            numeric_roles.update(modes)
        role_kinds = {
            child["role"]: child["role_kind"] for child in compiled_specs["topology"]["children"]
        }
        if (
            modes
            and any(cell["source_text"] is None for cell in selected_cells)
            and any(role_kinds.get(role) != "STRUCTURAL_GROUP" for role in modes)
        ):
            reasons.append(f"MAPPED_ROLE_CELL_IS_BLANK_UNKNOWN:r{row_ordinal}")
        source_row = {
            "cells": selected_cells,
            "hierarchy_path_exact": canonical_clone_v1(row.get("hierarchy_path_exact")),
            "label_exact": row.get("label_exact"),
            "label_match_modes": modes,
            "row_id": f"r{row_ordinal}",
            "row_kind": row.get("row_kind"),
            "source_position": [
                page_record["selected_frontier_ordinal"],
                section_ordinal,
                table_ordinal,
                row_ordinal,
            ],
        }
        if modes:
            role_rows.append(source_row)
        elif has_visible_mapping_value or row.get("row_kind") in {"SUBTOTAL", "TOTAL"}:
            anonymous_rows.append(source_row)
    local_owner_evidence = []
    local_branch_evidence = []
    for surface in surfaces:
        owner_matches = _contains_alias(surface["source_exact"], policy["owner_aliases"])
        branch_matches = _contains_alias(surface["source_exact"], policy["branch_aliases"])
        if owner_matches:
            local_owner_evidence.append(
                {**canonical_clone_v1(surface), "matched_aliases": owner_matches}
            )
        if branch_matches:
            local_branch_evidence.append(
                {**canonical_clone_v1(surface), "matched_aliases": branch_matches}
            )
    closure_material = {
        "anonymous_rows": anonymous_rows,
        "control_column_ids": request["control_column_ids"],
        "filtered_non_money_column_ids": [
            f"c{index + 1}" for index in range(len(columns)) if index not in money_indices
        ],
        "mapping_column_axis": period_records,
        "projection_kind": request["projection_kind"],
        "reasons": sorted(set(reasons)),
        "role_rows": role_rows,
    }
    identity_material = {
        "family_id": policy["family_id"],
        "page_json_version_id": page_record["page_json_version_id"],
        "section_id": request["section_id"],
        "table_id": request["table_id"],
        "projection_closure_sha256": canonical_json_sha256_v1(closure_material),
    }
    return {
        "adapter_format_version": "DOCUMENT_REGION_COLUMN_LANE_ADAPTER_V1",
        "anonymous_rows": anonymous_rows,
        "candidate_id": "drfcv1:fragment:" + canonical_json_sha256_v1(identity_material),
        "continuation": table.get("continuation"),
        "document_id": page_record["document_id"],
        "format_version": FRAGMENT_FORMAT_VERSION,
        "local_branch_evidence": local_branch_evidence,
        "local_owner_evidence": local_owner_evidence,
        "mapping_column_axis": period_records,
        "numeric_roles": sorted(numeric_roles),
        "page_json_sha256": canonical_json_sha256_v1(page_record["page_json"]),
        "page_json_version_id": page_record["page_json_version_id"],
        "physical_page": page_record["physical_page"],
        "projection_closure": closure_material,
        "projection_closure_sha256": identity_material["projection_closure_sha256"],
        "projection_kind": request["projection_kind"],
        "reasons": sorted(set(reasons)),
        "role_rows": role_rows,
        "section_id": request["section_id"],
        "selected_frontier_ordinal": page_record["selected_frontier_ordinal"],
        "source_logical_name": page_record["source_logical_name"],
        "source_sha256": page_record["source_sha256"],
        "source_table_sha256": canonical_json_sha256_v1(table),
        "status": "ELIGIBLE" if not reasons else "UNRESOLVED",
        "table_id": request["table_id"],
    }


def inventory_column_lane_document_region_fragment_v1(
    *,
    page_record: Mapping[str, Any],
    section_id: str,
    table_id: str,
    document_period_axis: Mapping[str, Any],
    policy: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Reference exhaustive inventory for ordinary column-lane tables."""

    _section, table, _section_ordinal, _table_ordinal = _source_nodes(
        page_record["page_json"], section_id=section_id, table_id=table_id
    )
    columns = table.get("columns")
    rows = table.get("rows")
    if type(columns) is not list or type(rows) is not list:
        raise _error("document-region inventory source axes are invalid")
    money_indices = [
        index
        for index, column in enumerate(columns)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    enabled = (
        compiled_specs["evaluation"].get("format_version") == "ACCOUNTING_FAMILY_EVALUATION_SPEC_V8"
    )
    has_role_or_total_numeric = False
    for row in rows:
        values = row.get("values_exact") if type(row) is dict else None
        if type(values) is not list or len(values) != len(columns):
            raise _error("document-region inventory row vector drifted")
        if not any(values[index] is not None for index in money_indices):
            continue
        try:
            roles = _row_role_match_modes(
                row,
                topology=compiled_specs["topology"],
                aliases_by_role=compiled_specs["aliases_by_role"],
                enable_declared_equivalences=enabled,
            )
        except ValueError:
            roles = {"AMBIGUOUS": "AMBIGUOUS"}
        if roles or row.get("row_kind") in {"GROUP", "SUBTOTAL", "TOTAL"}:
            has_role_or_total_numeric = True
            break
    surfaces = _table_surfaces(page_record=page_record, section_id=section_id, table_id=table_id)
    control_surface = any(
        _contains_alias(surface["source_exact"], policy["control_surface_aliases"])
        for surface in surfaces
    )
    if not has_role_or_total_numeric and not control_surface:
        return None
    expected = {tuple(signature) for signature in document_period_axis["period_signatures"]}
    mapping_indices = []
    for index in money_indices:
        column = columns[index]
        header = " ".join(
            value for value in column.get("header_path_exact", []) if type(value) is str
        )
        signature = _period_signature(header)
        unit, _evidence = _unit_signature(
            table=table, column=column, aliases=policy["unit_aliases"]
        )
        if signature in expected and unit is not None:
            mapping_indices.append(index)
    if has_role_or_total_numeric and not mapping_indices:
        # Preserve invalid period/unit columns as mapping evidence so the
        # projection emits a typed unresolved result rather than disappearing.
        mapping_indices = list(money_indices)
    control_indices = [index for index in money_indices if index not in mapping_indices]
    return {
        "control_column_ids": [f"c{index + 1}" for index in control_indices],
        "mapping_column_ids": [f"c{index + 1}" for index in mapping_indices],
        "page_json_version_id": page_record["page_json_version_id"],
        "projection_kind": "BALANCE_MAPPING" if mapping_indices else "DECLARED_CONTROL",
        "section_id": section_id,
        "table_id": table_id,
    }


def _validate_normalized_fragment_candidate(
    candidate: Any,
    *,
    page_record: Mapping[str, Any],
    document_period_axis: Mapping[str, Any],
    policy: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    required = {
        "adapter_format_version",
        "anonymous_rows",
        "candidate_id",
        "continuation",
        "document_id",
        "format_version",
        "local_branch_evidence",
        "local_owner_evidence",
        "mapping_column_axis",
        "numeric_roles",
        "page_json_sha256",
        "page_json_version_id",
        "physical_page",
        "projection_closure",
        "projection_closure_sha256",
        "projection_kind",
        "reasons",
        "role_rows",
        "section_id",
        "selected_frontier_ordinal",
        "source_logical_name",
        "source_sha256",
        "source_table_sha256",
        "status",
        "table_id",
    }
    if type(candidate) is not dict or set(candidate) != required:
        raise _error("normalized document-region fragment contract drifted")
    section, table, _section_ordinal, _table_ordinal = _source_nodes(
        page_record["page_json"],
        section_id=candidate["section_id"],
        table_id=candidate["table_id"],
    )
    del section
    if (
        type(candidate["adapter_format_version"]) is not str
        or not candidate["adapter_format_version"]
        or candidate["format_version"] != FRAGMENT_FORMAT_VERSION
        or candidate["document_id"] != page_record["document_id"]
        or candidate["source_logical_name"] != page_record["source_logical_name"]
        or candidate["source_sha256"] != page_record["source_sha256"]
        or candidate["page_json_version_id"] != page_record["page_json_version_id"]
        or candidate["physical_page"] != page_record["physical_page"]
        or candidate["selected_frontier_ordinal"] != page_record["selected_frontier_ordinal"]
        or candidate["page_json_sha256"] != canonical_json_sha256_v1(page_record["page_json"])
        or candidate["source_table_sha256"] != canonical_json_sha256_v1(table)
        or candidate["projection_closure_sha256"]
        != canonical_json_sha256_v1(candidate["projection_closure"])
        or candidate["status"] not in {"ELIGIBLE", "UNRESOLVED"}
        or candidate["projection_kind"] not in {"BALANCE_MAPPING", "DECLARED_CONTROL"}
        or type(candidate["reasons"]) is not list
        or candidate["reasons"] != sorted(set(candidate["reasons"]))
        or (candidate["status"] == "ELIGIBLE") == bool(candidate["reasons"])
    ):
        raise _error("normalized document-region fragment source binding drifted")
    identity_material = {
        "family_id": policy["family_id"],
        "page_json_version_id": candidate["page_json_version_id"],
        "section_id": candidate["section_id"],
        "table_id": candidate["table_id"],
        "projection_closure_sha256": candidate["projection_closure_sha256"],
    }
    if candidate["candidate_id"] != "drfcv1:fragment:" + canonical_json_sha256_v1(
        identity_material
    ):
        raise _error("normalized document-region fragment identity drifted")
    closure = candidate["projection_closure"]
    closure_fields = {
        "anonymous_rows",
        "control_column_ids",
        "filtered_non_money_column_ids",
        "mapping_column_axis",
        "projection_kind",
        "reasons",
        "role_rows",
    }
    if (
        type(closure) is not dict
        or set(closure) != closure_fields
        or closure["anonymous_rows"] != candidate["anonymous_rows"]
        or closure["mapping_column_axis"] != candidate["mapping_column_axis"]
        or closure["projection_kind"] != candidate["projection_kind"]
        or closure["reasons"] != candidate["reasons"]
        or closure["role_rows"] != candidate["role_rows"]
    ):
        raise _error("normalized document-region projection closure drifted")
    surfaces = _table_surfaces(
        page_record=page_record,
        section_id=candidate["section_id"],
        table_id=candidate["table_id"],
    )
    expected_owner_evidence = []
    expected_branch_evidence = []
    for surface in surfaces:
        owner_matches = _contains_alias(surface["source_exact"], policy["owner_aliases"])
        branch_matches = _contains_alias(surface["source_exact"], policy["branch_aliases"])
        if owner_matches:
            expected_owner_evidence.append(
                {**canonical_clone_v1(surface), "matched_aliases": owner_matches}
            )
        if branch_matches:
            expected_branch_evidence.append(
                {**canonical_clone_v1(surface), "matched_aliases": branch_matches}
            )
    if (
        candidate["local_owner_evidence"] != expected_owner_evidence
        or candidate["local_branch_evidence"] != expected_branch_evidence
        or candidate["continuation"] != table.get("continuation")
    ):
        raise _error("normalized document-region structural evidence drifted")
    columns = table.get("columns")
    rows = table.get("rows")
    if type(columns) is not list or type(rows) is not list:
        raise _error("normalized document-region source axes are invalid")
    known_roles = {compiled_specs["topology"]["parent"]["role"]} | {
        child["role"] for child in compiled_specs["topology"]["children"]
    }
    expected_periods = {tuple(value) for value in document_period_axis["period_signatures"]}
    for row_record in [*candidate["role_rows"], *candidate["anonymous_rows"]]:
        if type(row_record) is not dict:
            raise _error("normalized document-region source row is invalid")
        row_index = _node_index(row_record.get("row_id"), "r", len(rows))
        source_row = rows[row_index]
        if (
            row_record.get("label_exact") != source_row.get("label_exact")
            or row_record.get("hierarchy_path_exact") != source_row.get("hierarchy_path_exact")
            or row_record.get("row_kind") != source_row.get("row_kind")
            or type(row_record.get("label_match_modes")) is not dict
            or any(role not in known_roles for role in row_record["label_match_modes"])
            or type(row_record.get("cells")) is not list
        ):
            raise _error("normalized document-region source row binding drifted")
        source_values = source_row.get("values_exact")
        if type(source_values) is not list or len(source_values) != len(columns):
            raise _error("normalized document-region source value vector drifted")
        for cell in row_record["cells"]:
            if (
                type(cell) is not dict
                or set(cell)
                != {
                    "column_id",
                    "metric_signature",
                    "money",
                    "period_signature",
                    "source_text",
                    "unit_signature",
                }
                or type(cell["metric_signature"]) is not str
                or not cell["metric_signature"]
                or type(cell["period_signature"]) is not list
                or len(cell["period_signature"]) != 2
                or type(cell["unit_signature"]) not in {str, type(None)}
                or (
                    candidate["status"] == "ELIGIBLE"
                    and (
                        tuple(cell["period_signature"]) not in expected_periods
                        or cell["unit_signature"] not in policy["unit_aliases"]
                    )
                )
            ):
                raise _error("normalized document-region source cell contract drifted")
            column_index = _node_index(cell["column_id"], "c", len(columns))
            if cell["source_text"] != source_values[column_index]:
                raise _error("normalized document-region source cell text drifted")
            if cell["source_text"] is None:
                if cell["money"] is not None:
                    raise _error("blank document-region source cell became zero")
            else:
                try:
                    expected_money = _money(cell["source_text"])
                except ValueError as exc:
                    raise _error("normalized document-region source money is invalid") from exc
                if cell["money"] != expected_money:
                    raise _error("normalized document-region source money drifted")
    expected_numeric_roles = sorted(
        {
            role
            for row in candidate["role_rows"]
            if any(cell["source_text"] is not None for cell in row["cells"])
            for role in row["label_match_modes"]
        }
    )
    if candidate["numeric_roles"] != expected_numeric_roles:
        raise _error("normalized document-region numeric role axis drifted")
    return canonical_clone_v1(candidate)


def _component_axis(fragments: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": fragment["candidate_id"],
            "page_json_sha256": fragment["page_json_sha256"],
            "page_json_version_id": fragment["page_json_version_id"],
            "physical_page": fragment["physical_page"],
            "projection_closure_sha256": fragment["projection_closure_sha256"],
            "section_id": fragment["section_id"],
            "selected_frontier_ordinal": fragment["selected_frontier_ordinal"],
            "source_logical_name": fragment["source_logical_name"],
            "source_sha256": fragment["source_sha256"],
            "source_table_sha256": fragment["source_table_sha256"],
            "table_id": fragment["table_id"],
        }
        for fragment in fragments
    ]


def _page_axis(page_records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "page_json_sha256": canonical_json_sha256_v1(record["page_json"]),
            "page_json_version_id": record["page_json_version_id"],
            "physical_page": record["physical_page"],
            "selected_frontier_ordinal": record["selected_frontier_ordinal"],
            "source_logical_name": record["source_logical_name"],
            "source_sha256": record["source_sha256"],
        }
        for record in page_records
    ]


def _failed_composition(
    *,
    policy: Mapping[str, Any],
    fragments: Sequence[Mapping[str, Any]],
    page_records: Sequence[Mapping[str, Any]],
    selected_page_json_version_ids: Sequence[str],
    reasons: Sequence[str],
    structural_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    component_axis = _component_axis(fragments)
    pages = _page_axis(page_records)
    identity = {
        "component_axis_sha256": canonical_json_sha256_v1(component_axis),
        "family_id": policy["family_id"],
        "policy_sha256": policy["policy_sha256"],
        "selected_page_json_frontier_sha256": canonical_json_sha256_v1(
            list(selected_page_json_version_ids)
        ),
    }
    return {
        "candidate_id": "drfcv1:composition:" + canonical_json_sha256_v1(identity),
        "claim_boundary": CLAIM_BOUNDARY,
        "component_fragments": canonical_clone_v1(fragments),
        "composition_receipt": {
            "component_axis": component_axis,
            "component_axis_sha256": identity["component_axis_sha256"],
            "format_version": RECEIPT_FORMAT_VERSION,
            "ordered_region_axis_sha256": canonical_json_sha256_v1(
                {"components": component_axis, "pages": pages}
            ),
            "page_axis": pages,
            "page_axis_sha256": canonical_json_sha256_v1(pages),
            "policy_sha256": policy["policy_sha256"],
            "selected_page_json_frontier_sha256": identity["selected_page_json_frontier_sha256"],
            **(
                {"structural_receipt": canonical_clone_v1(structural_receipt)}
                if structural_receipt is not None
                else {}
            ),
        },
        "format_version": COMPOSITION_FORMAT_VERSION,
        "mappings": [],
        "reasons": sorted(set(reasons)),
        "status": UNRESOLVED,
    }


def _structural_receipt(
    *,
    page_records: Sequence[Mapping[str, Any]],
    fragments: Sequence[Mapping[str, Any]],
    policy: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Authenticate the owner/cluster, reset fence, and cross-page chain."""

    reasons: list[str] = []
    all_surfaces = [surface for page in page_records for surface in _all_page_surfaces(page)]
    all_surfaces.sort(key=lambda item: item["position"])
    first = fragments[0]
    last = fragments[-1]
    first_table_position = [
        first["selected_frontier_ordinal"],
        int(first["section_id"][1:]),
        int(first["table_id"][1:]),
    ]
    last_table_position = [
        last["selected_frontier_ordinal"],
        int(last["section_id"][1:]),
        int(last["table_id"][1:]),
    ]
    relevant_surfaces = [
        surface for surface in all_surfaces if surface["position"][:3] <= last_table_position
    ]
    reset_evidence = [
        {
            **canonical_clone_v1(surface),
            "matched_aliases": _contains_alias(surface["source_exact"], policy["reset_aliases"]),
        }
        for surface in relevant_surfaces
        if _contains_alias(surface["source_exact"], policy["reset_aliases"])
    ]
    hard_negative_evidence = [
        {
            **canonical_clone_v1(surface),
            "matched_aliases": _contains_alias(
                surface["source_exact"], policy["hard_negative_aliases"]
            ),
        }
        for surface in relevant_surfaces
        if _contains_alias(surface["source_exact"], policy["hard_negative_aliases"])
    ]
    last_reset_before_first = max(
        (
            evidence["position"]
            for evidence in [*reset_evidence, *hard_negative_evidence]
            if evidence["position"][:3] <= first_table_position
        ),
        default=None,
    )
    owner_candidates = []
    for surface in relevant_surfaces:
        aliases = _contains_alias(surface["source_exact"], policy["owner_aliases"])
        if (
            aliases
            and surface["position"][:3] <= first_table_position
            and (last_reset_before_first is None or surface["position"] > last_reset_before_first)
        ):
            owner_candidates.append({**canonical_clone_v1(surface), "matched_aliases": aliases})
    anchor_mode: str | None = None
    anchor_evidence: dict[str, Any] | None = None
    if owner_candidates:
        anchor_mode = "EXPLICIT_OWNER"
        anchor_evidence = owner_candidates[-1]
    else:
        qualifying = []
        distinctive = set(policy["distinctive_child_roles"])
        for fragment in fragments:
            roles = distinctive & set(fragment["numeric_roles"])
            if len(roles) >= policy["minimum_distinctive_child_roles"]:
                qualifying.append((fragment, sorted(roles)))
        if len(qualifying) == 1 and qualifying[0][0]["candidate_id"] == first["candidate_id"]:
            fragment, roles = qualifying[0]
            anchor_mode = "UNIQUE_DISTINCTIVE_CHILD_CLUSTER"
            anchor_evidence = {
                "candidate_id": fragment["candidate_id"],
                "distinctive_roles": roles,
                "page_json_version_id": fragment["page_json_version_id"],
                "physical_page": fragment["physical_page"],
                "section_id": fragment["section_id"],
                "table_id": fragment["table_id"],
            }
        else:
            reasons.append("EXPLICIT_OWNER_OR_UNIQUE_DISTINCTIVE_CHILD_CLUSTER_IS_ABSENT")
    anchor_position = (
        anchor_evidence.get("position")
        if anchor_mode == "EXPLICIT_OWNER" and anchor_evidence is not None
        else [*first_table_position, 0, 0]
    )
    fenced_resets = [
        evidence
        for evidence in reset_evidence
        if anchor_position < evidence["position"]
        and evidence["position"][:3] <= last_table_position
    ]
    fenced_negatives = [
        evidence
        for evidence in hard_negative_evidence
        if anchor_position < evidence["position"]
        and evidence["position"][:3] <= last_table_position
    ]
    if fenced_resets:
        reasons.append("STRUCTURAL_RESET_INSIDE_COMPOSED_REGION")
    if fenced_negatives:
        reasons.append("HARD_NEGATIVE_INSIDE_COMPOSED_REGION")

    cross_page_receipts = []
    prior_fragment = fragments[0]
    seen_pages = {prior_fragment["selected_frontier_ordinal"]}
    distinctive = set(policy["distinctive_child_roles"])
    for fragment in fragments[1:]:
        page_ordinal = fragment["selected_frontier_ordinal"]
        if page_ordinal in seen_pages:
            prior_fragment = fragment
            continue
        seen_pages.add(page_ordinal)
        modes = []
        if fragment["local_owner_evidence"]:
            modes.append("LOCAL_OWNER")
        if fragment["local_branch_evidence"]:
            modes.append("LOCAL_BRANCH")
        if fragment["continuation"] in _CONTINUES_FROM_PREVIOUS:
            modes.append("CONTINUES_FROM_PREVIOUS_PAGE")
        if prior_fragment["continuation"] in _CONTINUES_ON_NEXT:
            modes.append("PRIOR_CONTINUES_ON_NEXT_PAGE")
        distinctive_roles = sorted(distinctive & set(fragment["numeric_roles"]))
        if (
            policy["allow_distinctive_child_cluster_cross_page"]
            and len(distinctive_roles) >= policy["minimum_distinctive_child_roles"]
        ):
            modes.append("LOCAL_DISTINCTIVE_CHILD_CLUSTER")
        if not modes:
            reasons.append(
                "CROSS_PAGE_FRAGMENT_HAS_NO_LOCAL_BRANCH_OR_EXPLICIT_CONTINUATION:"
                + fragment["page_json_version_id"]
            )
        cross_page_receipts.append(
            {
                "candidate_id": fragment["candidate_id"],
                "distinctive_roles": distinctive_roles,
                "modes": modes,
                "page_json_version_id": fragment["page_json_version_id"],
                "selected_frontier_ordinal": page_ordinal,
            }
        )
        prior_fragment = fragment
    return (
        {
            "anchor_evidence": anchor_evidence,
            "anchor_mode": anchor_mode,
            "cross_page_receipts": cross_page_receipts,
            "fenced_hard_negative_evidence": fenced_negatives,
            "fenced_reset_evidence": fenced_resets,
            "first_table_position": first_table_position,
            "last_table_position": last_table_position,
            "rule": (
                "EARLIEST_EXPLICIT_OWNER_OR_UNIQUE_DISTINCTIVE_CLUSTER_THEN_"
                "SOURCE_ORDERED_RESET_FENCE_AND_EXPLICIT_CROSS_PAGE_CHAIN"
            ),
        },
        reasons,
    )


def _row_population_context(row: Mapping[str, Any]) -> list[str]:
    path = row.get("hierarchy_path_exact")
    if type(path) is not list:
        return []
    normalized = [_normalized(value) for value in path if _normalized(value)]
    label = _normalized(row.get("label_exact"))
    if normalized and normalized[-1] == label:
        normalized.pop()
    return normalized


def _source_cell_evidence(
    *, fragment: Mapping[str, Any], row: Mapping[str, Any], cell: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "candidate_id": fragment["candidate_id"],
        "column_id": cell["column_id"],
        "metric_signature": cell["metric_signature"],
        "money": canonical_clone_v1(cell["money"]),
        "page_json_version_id": fragment["page_json_version_id"],
        "period_signature": canonical_clone_v1(cell["period_signature"]),
        "physical_page": fragment["physical_page"],
        "row_id": row["row_id"],
        "section_id": fragment["section_id"],
        "source_text": cell["source_text"],
        "table_id": fragment["table_id"],
        "unit_signature": cell["unit_signature"],
    }


def _merge_rows(
    *,
    fragments: Sequence[Mapping[str, Any]],
    document_period_axis: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], list[str]]:
    """Merge exact period cells while preserving population-context row groups."""

    expected = [tuple(value) for value in document_period_axis["period_signatures"]]
    reasons: list[str] = []
    groups: dict[tuple[Any, ...], dict[str, Any]] = {}
    duplicate_receipts = []
    unit_signatures = set()
    for fragment in fragments:
        if fragment["projection_kind"] != "BALANCE_MAPPING":
            continue
        for row in [*fragment["role_rows"], *fragment["anonymous_rows"]]:
            roles = tuple(sorted(row["label_match_modes"]))
            if all(cell["source_text"] is None for cell in row["cells"]):
                # A fully blank row is exact label/path context only.  Omitting
                # it from the numeric projection prevents the downstream
                # engine's conditional blank-zero representation from
                # authenticating a visible zero subtotal or root.  Child
                # hierarchy paths retain the source-exact context.  Non-group
                # role blanks have already made the fragment unresolved.
                continue
            context = tuple(_row_population_context(row))
            if roles:
                key: tuple[Any, ...] = ("ROLES", roles, context)
            else:
                key = (
                    "ANONYMOUS",
                    row.get("row_kind"),
                    _normalized(row.get("label_exact")),
                    tuple(_normalized(value) for value in row.get("hierarchy_path_exact", [])),
                )
            group = groups.setdefault(
                key,
                {
                    "cells": defaultdict(list),
                    "first_position": row["source_position"],
                    "hierarchy_path_exact": canonical_clone_v1(row["hierarchy_path_exact"]),
                    "label_exact": row["label_exact"],
                    "roles": list(roles),
                    "row_kind": row["row_kind"],
                    "row_sources": [],
                    "metric_signatures": set(),
                },
            )
            group["first_position"] = min(group["first_position"], row["source_position"])
            group["row_sources"].append(
                {
                    "candidate_id": fragment["candidate_id"],
                    "hierarchy_path_exact": canonical_clone_v1(row["hierarchy_path_exact"]),
                    "label_exact": row["label_exact"],
                    "page_json_version_id": fragment["page_json_version_id"],
                    "row_id": row["row_id"],
                    "section_id": fragment["section_id"],
                    "table_id": fragment["table_id"],
                }
            )
            for cell in row["cells"]:
                if cell["period_signature"] is None or cell["unit_signature"] is None:
                    continue
                period = tuple(cell["period_signature"])
                unit_signatures.add(cell["unit_signature"])
                group["metric_signatures"].add(cell["metric_signature"])
                group["cells"][(period, cell["unit_signature"])].append(
                    _source_cell_evidence(fragment=fragment, row=row, cell=cell)
                )
    if len(unit_signatures) != 1:
        reasons.append("COMPOSED_MAPPING_UNIT_SIGNATURE_COUNT_NOT_ONE")
    unit_signature = next(iter(unit_signatures), None)
    synthetic_rows = []
    provenance_by_synthetic_row_id = {}
    for group in sorted(groups.values(), key=lambda value: value["first_position"]):
        if unit_signature is None:
            break
        if len(group["metric_signatures"]) != 1:
            reasons.append(
                "ROLE_POPULATION_METRIC_SIGNATURE_COUNT_NOT_ONE:"
                + ":".join(group["roles"] or ["ANONYMOUS"])
            )
        by_period = {}
        numeric = False
        for period in expected:
            sources = group["cells"].get((period, unit_signature), [])
            if not sources:
                by_period[period] = []
                continue
            coefficients = {
                source["money"]["coefficient"] for source in sources if source["money"] is not None
            }
            if len(coefficients) != 1:
                reasons.append(
                    "DUPLICATE_ROLE_PERIOD_UNIT_VALUE_CONFLICT:"
                    + ":".join(group["roles"] or ["ANONYMOUS"])
                    + ":"
                    + "/".join(period)
                )
                by_period[period] = sources
                continue
            numeric |= any(source["source_text"] is not None for source in sources)
            by_period[period] = sources
            if len(sources) > 1:
                duplicate_receipts.append(
                    {
                        "coefficient": next(iter(coefficients)),
                        "period_signature": list(period),
                        "population_context": _row_population_context(group),
                        "roles": group["roles"],
                        "source_cells": canonical_clone_v1(sources),
                        "unit_signature": unit_signature,
                    }
                )
        if numeric and any(not by_period[period] for period in expected):
            reasons.append(
                "NUMERIC_ROW_EXPECTED_PERIOD_COVERAGE_IS_INCOMPLETE:"
                + ":".join(group["roles"] or ["ANONYMOUS"])
            )
        values = []
        for period in expected:
            sources = by_period[period]
            values.append(sources[0]["source_text"] if sources else None)
        synthetic_row_id = f"r{len(synthetic_rows) + 1}"
        synthetic_rows.append(
            {
                "hierarchy_path_exact": canonical_clone_v1(group["hierarchy_path_exact"]),
                "label_exact": group["label_exact"],
                "row_kind": group["row_kind"],
                "values_exact": values,
            }
        )
        provenance_by_synthetic_row_id[synthetic_row_id] = {
            "period_sources": [
                {
                    "period_signature": list(period),
                    "source_cells": canonical_clone_v1(by_period[period]),
                }
                for period in expected
            ],
            "roles": group["roles"],
            "source_rows": canonical_clone_v1(group["row_sources"]),
        }
    return synthetic_rows, provenance_by_synthetic_row_id, duplicate_receipts, reasons


def _mapping_provenance(
    *,
    mapping: Mapping[str, Any],
    provenance_by_row_id: Mapping[str, Any],
    closure_receipt: Mapping[str, Any],
    expected_periods: Sequence[Sequence[str]],
) -> dict[str, Any]:
    row_id = mapping.get("row_id")
    if row_id in provenance_by_row_id:
        return {
            "mode": "DIRECT_OR_CORROBORATED_SOURCE_ROW",
            **canonical_clone_v1(provenance_by_row_id[row_id]),
        }
    requested_roles = set(mapping.get("derived_from_roles", []))
    if not requested_roles:
        requested_roles = {mapping["role"]}
    equation_by_result = {
        equation.get("result_role"): equation
        for equation in closure_receipt.get("equations", [])
        if type(equation) is dict and type(equation.get("result_role")) is str
    }
    frontier = list(requested_roles)
    leaf_roles = set()
    while frontier:
        role = frontier.pop()
        equation = equation_by_result.get(role)
        components = equation.get("component_roles", []) if equation is not None else []
        if components:
            frontier.extend(components)
        else:
            leaf_roles.add(role)
    source_groups = [
        provenance
        for provenance in provenance_by_row_id.values()
        if leaf_roles.intersection(provenance["roles"])
    ]
    return {
        "mode": "DERIVED_EXACT_EQUATION_SOURCE_FRONTIER",
        "period_sources": [
            {
                "period_signature": list(period),
                "source_cells": [
                    cell
                    for provenance in source_groups
                    for period_record in provenance["period_sources"]
                    if period_record["period_signature"] == list(period)
                    for cell in period_record["source_cells"]
                ],
            }
            for period in expected_periods
        ],
        "roles": sorted(leaf_roles),
        "source_rows": [row for provenance in source_groups for row in provenance["source_rows"]],
    }


def compose_document_region_fragments_v1(
    *,
    selected_page_json_version_ids: Sequence[str],
    page_records: Sequence[Mapping[str, Any]],
    fragment_requests: Sequence[Mapping[str, Any]],
    document_period_axis: Mapping[str, Any],
    policy: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
    projection_adapter: Callable[..., dict[str, Any]],
    projection_inventory_adapter: Callable[..., dict[str, Any] | None],
) -> dict[str, Any]:
    """Compose one exhaustive, reset-fenced document region.

    ``projection_adapter`` is an explicit replayable adapter boundary.  It may
    interpret ordinary, stacked, transposed, or multi-metric tables, but it
    must return the normalized fragment contract whose source cells are then
    exact-checked here.  Thus this composer never becomes a second table-axis
    evaluator.
    """

    compiled_policy = compile_document_region_fragment_composer_policy_v1(
        policy, compiled_specs=compiled_specs
    )
    records = _validate_selected_page_records(
        page_records,
        selected_page_json_version_ids=selected_page_json_version_ids,
    )
    period_axis = _validate_document_period_axis(
        document_period_axis, policy=compiled_policy, page_records=records
    )
    if (
        type(fragment_requests) not in {list, tuple}
        or not fragment_requests
        or not callable(projection_adapter)
        or not callable(projection_inventory_adapter)
    ):
        raise _error("document-region fragment request axis is invalid")
    by_version = {record["page_json_version_id"]: record for record in records}
    inventoried_requests = []
    for record in records:
        for section_ordinal, section in enumerate(record["page_json"]["sections"], start=1):
            tables = section.get("tables") if type(section) is dict else None
            if type(tables) is not list:
                continue
            for table_ordinal in range(1, len(tables) + 1):
                inventoried = projection_inventory_adapter(
                    page_record=canonical_clone_v1(record),
                    section_id=f"s{section_ordinal}",
                    table_id=f"t{table_ordinal}",
                    document_period_axis=canonical_clone_v1(period_axis),
                    policy=canonical_clone_v1(compiled_policy),
                    compiled_specs=compiled_specs,
                )
                if inventoried is not None:
                    inventoried_requests.append(inventoried)
    inventory_reasons = []

    def locator(request: Mapping[str, Any]) -> tuple[Any, Any, Any]:
        return (
            request.get("page_json_version_id"),
            request.get("section_id"),
            request.get("table_id"),
        )

    inventoried_by_locator = {locator(request): request for request in inventoried_requests}
    requested_by_locator = {
        locator(request): request for request in fragment_requests if type(request) is dict
    }
    missing_inventory = sorted(set(inventoried_by_locator) - set(requested_by_locator))
    extra_requests = sorted(set(requested_by_locator) - set(inventoried_by_locator))
    changed_requests = sorted(
        key
        for key in set(inventoried_by_locator) & set(requested_by_locator)
        if inventoried_by_locator[key] != requested_by_locator[key]
    )
    if missing_inventory:
        inventory_reasons.append(
            "UNCONSUMED_ROLE_BEARING_FRAGMENT_IN_EXHAUSTIVE_ADAPTER_INVENTORY:"
            + ",".join(":".join(map(str, key)) for key in missing_inventory)
        )
    if extra_requests:
        inventory_reasons.append(
            "FRAGMENT_REQUEST_IS_OUTSIDE_EXHAUSTIVE_ADAPTER_INVENTORY:"
            + ",".join(":".join(map(str, key)) for key in extra_requests)
        )
    if changed_requests:
        inventory_reasons.append("FRAGMENT_REQUEST_PROJECTION_OR_ORDER_DRIFTED_FROM_INVENTORY")
    if not inventoried_requests:
        raise _error("document-region adapter inventory is empty")
    if len(inventoried_requests) > compiled_policy["maximum_components"]:
        raise _error("document-region inventoried fragments are above the cap")
    requested_keys = []
    internal_requests = []
    for request in fragment_requests:
        if (
            type(request) is not dict
            or type(request.get("page_json_version_id")) is not str
            or request["page_json_version_id"] not in by_version
            or type(request.get("section_id")) is not str
            or type(request.get("table_id")) is not str
        ):
            raise _error("document-region fragment locator is invalid")
        record = by_version[request["page_json_version_id"]]
        _source_nodes(
            record["page_json"],
            section_id=request["section_id"],
            table_id=request["table_id"],
        )
        key = (
            record["selected_frontier_ordinal"],
            int(request["section_id"][1:]),
            int(request["table_id"][1:]),
        )
        requested_keys.append(key)
        internal_requests.append((record, request))
    if (
        requested_keys != sorted(requested_keys)
        or len(set(requested_keys)) != len(requested_keys)
        or len(requested_keys) > compiled_policy["maximum_components"]
    ):
        raise _error("document-region fragments are unordered, repeated, or above the cap")
    inventory_ordinals = [
        by_version[request["page_json_version_id"]]["selected_frontier_ordinal"]
        for request in inventoried_requests
    ]
    first_ordinal = min(inventory_ordinals)
    last_ordinal = max(inventory_ordinals)
    if last_ordinal - first_ordinal + 1 > compiled_policy["maximum_page_span"] or [
        record["selected_frontier_ordinal"] for record in records
    ] != list(range(first_ordinal, last_ordinal + 1)):
        raise _error("document-region selected page span is not exact or exceeds the cap")
    fragments = []
    for page_record, request in internal_requests:
        candidate = projection_adapter(
            page_record=canonical_clone_v1(page_record),
            request=canonical_clone_v1(request),
            document_period_axis=canonical_clone_v1(period_axis),
            policy=canonical_clone_v1(compiled_policy),
            compiled_specs=compiled_specs,
        )
        fragments.append(
            _validate_normalized_fragment_candidate(
                candidate,
                page_record=page_record,
                document_period_axis=period_axis,
                policy=compiled_policy,
                compiled_specs=compiled_specs,
            )
        )
    structural, structural_reasons = _structural_receipt(
        page_records=records,
        fragments=fragments,
        policy=compiled_policy,
    )
    reasons = [*inventory_reasons]
    reasons.extend(reason for fragment in fragments for reason in fragment["reasons"])
    reasons.extend(structural_reasons)
    if reasons:
        return _failed_composition(
            policy=compiled_policy,
            fragments=fragments,
            page_records=records,
            selected_page_json_version_ids=selected_page_json_version_ids,
            reasons=reasons,
            structural_receipt=structural,
        )
    synthetic_rows, provenance_by_row_id, duplicate_receipts, merge_reasons = _merge_rows(
        fragments=fragments,
        document_period_axis=period_axis,
        compiled_specs=compiled_specs,
    )
    if merge_reasons:
        return _failed_composition(
            policy=compiled_policy,
            fragments=fragments,
            page_records=records,
            selected_page_json_version_ids=selected_page_json_version_ids,
            reasons=merge_reasons,
            structural_receipt=structural,
        )
    unit_signatures = {
        cell["unit_signature"]
        for fragment in fragments
        if fragment["projection_kind"] == "BALANCE_MAPPING"
        for row in [*fragment["role_rows"], *fragment["anonymous_rows"]]
        for cell in row["cells"]
        if cell["unit_signature"] is not None
    }
    if len(unit_signatures) != 1:
        return _failed_composition(
            policy=compiled_policy,
            fragments=fragments,
            page_records=records,
            selected_page_json_version_ids=selected_page_json_version_ids,
            reasons=["COMPOSED_MAPPING_UNIT_SIGNATURE_COUNT_NOT_ONE"],
            structural_receipt=structural,
        )
    unit_signature = next(iter(unit_signatures))

    def synthetic_period_header(signature: Sequence[str]) -> str:
        if signature[0] == "DATE":
            year, month, day = signature[1].split("-")
            return f"{day}/{month}/{year}"
        return (
            "Số cuối kỳ"
            if signature[1] == "CURRENT_PERIOD"
            else "Số đầu kỳ"
            if signature[1] == "COMPARATIVE_PERIOD"
            else signature[1]
        )

    synthetic_columns = [
        {
            "header_path_exact": [synthetic_period_header(signature), unit_signature],
            "value_kind": "MONEY",
        }
        for signature in period_axis["period_signatures"]
    ]
    synthetic_table = {
        "columns": synthetic_columns,
        "continuation": "NONE",
        "rows": synthetic_rows,
        "title_exact": compiled_specs["topology"]["parent"]["aliases"][0],
        "unit_exact": unit_signature,
    }
    synthetic_page = {
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [synthetic_table],
                "title_exact": compiled_specs["topology"]["parent"]["aliases"][0],
            }
        ]
    }
    synthetic_page_hash = canonical_json_sha256_v1(synthetic_page)
    internal = evaluate_gemini_json_hierarchical_family_table_v1(
        page_json=synthetic_page,
        page_json_version_id="gfpstorev1:json:" + synthetic_page_hash,
        physical_page=fragments[0]["physical_page"],
        section_id="s1",
        table_id="t1",
        compiled_specs=dict(compiled_specs),
    )
    if internal["status"] != READY:
        return _failed_composition(
            policy=compiled_policy,
            fragments=fragments,
            page_records=records,
            selected_page_json_version_ids=selected_page_json_version_ids,
            reasons=["COMPOSED_ACCOUNTING_CLOSURE_IS_NOT_READY", *internal["reasons"]],
            structural_receipt=structural,
        )
    mappings = canonical_clone_v1(internal["mappings"])
    for mapping in mappings:
        provenance = _mapping_provenance(
            mapping=mapping,
            provenance_by_row_id=provenance_by_row_id,
            closure_receipt=internal["closure_receipt"],
            expected_periods=period_axis["period_signatures"],
        )
        mapping["document_region_fragment_provenance"] = provenance
        for value, period_sources in zip(
            mapping["values"], provenance["period_sources"], strict=True
        ):
            value["document_region_fragment_source_cells"] = canonical_clone_v1(
                period_sources["source_cells"]
            )
    component_axis = _component_axis(fragments)
    pages = _page_axis(records)
    provenance_axis = [
        {
            "report_norm_id": mapping["report_norm_id"],
            "role": mapping["role"],
            "source": mapping["document_region_fragment_provenance"],
        }
        for mapping in mappings
    ]
    receipt = {
        "component_axis": component_axis,
        "component_axis_sha256": canonical_json_sha256_v1(component_axis),
        "control_candidate_ids": [
            fragment["candidate_id"]
            for fragment in fragments
            if fragment["projection_kind"] == "DECLARED_CONTROL"
        ],
        "document_period_axis": canonical_clone_v1(period_axis),
        "duplicate_corroborations": duplicate_receipts,
        "final_closure_sha256": canonical_json_sha256_v1(internal["closure_receipt"]),
        "format_version": RECEIPT_FORMAT_VERSION,
        "internal_evaluator_candidate_id": internal["candidate_id"],
        "ordered_region_axis_sha256": canonical_json_sha256_v1(
            {"components": component_axis, "pages": pages}
        ),
        "page_axis": pages,
        "page_axis_sha256": canonical_json_sha256_v1(pages),
        "policy_sha256": compiled_policy["policy_sha256"],
        "provenance_axis_sha256": canonical_json_sha256_v1(provenance_axis),
        "selected_page_json_frontier_sha256": canonical_json_sha256_v1(
            list(selected_page_json_version_ids)
        ),
        "structural_receipt": structural,
        "synthetic_projection_sha256": synthetic_page_hash,
    }
    identity = {
        "family_id": compiled_policy["family_id"],
        "final_closure_sha256": receipt["final_closure_sha256"],
        "ordered_region_axis_sha256": receipt["ordered_region_axis_sha256"],
        "policy_sha256": receipt["policy_sha256"],
    }
    return {
        "candidate_id": "drfcv1:composition:" + canonical_json_sha256_v1(identity),
        "claim_boundary": CLAIM_BOUNDARY,
        "closure_receipt": canonical_clone_v1(internal["closure_receipt"]),
        "component_fragments": canonical_clone_v1(fragments),
        "composition_receipt": receipt,
        "format_version": COMPOSITION_FORMAT_VERSION,
        "mappings": mappings,
        "reasons": [],
        "status": READY,
    }


def validate_document_region_fragment_composition_replay_v1(
    *,
    selected_page_json_version_ids: Sequence[str],
    page_records: Sequence[Mapping[str, Any]],
    fragment_requests: Sequence[Mapping[str, Any]],
    document_period_axis: Mapping[str, Any],
    policy: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
    projection_adapter: Callable[..., dict[str, Any]],
    projection_inventory_adapter: Callable[..., dict[str, Any] | None],
    composition: Any,
) -> dict[str, Any]:
    """Pure exact replay over caller-supplied source records.

    Persistence/official consumers must use the SQLite replay entry point
    below, which reloads the canonical page bytes from the selected store.
    """

    expected = compose_document_region_fragments_v1(
        selected_page_json_version_ids=selected_page_json_version_ids,
        page_records=page_records,
        fragment_requests=fragment_requests,
        document_period_axis=document_period_axis,
        policy=policy,
        compiled_specs=compiled_specs,
        projection_adapter=projection_adapter,
        projection_inventory_adapter=projection_inventory_adapter,
    )
    if composition != expected:
        raise _error("document-region fragment composition does not replay exactly")
    return expected


def validate_document_region_fragment_composition_store_replay_v1(
    database_path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    fragment_requests: Sequence[Mapping[str, Any]],
    document_period_axis: Mapping[str, Any],
    policy: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
    projection_adapter: Callable[..., dict[str, Any]],
    projection_inventory_adapter: Callable[..., dict[str, Any] | None],
    composition: Any,
) -> dict[str, Any]:
    """Reload selected canonical JSON from SQLite and exact-replay a composition."""

    from bctc_ai.storage.gemini_financial_page_store_v1 import (
        load_page_json_versions_v1,
        selected_page_extraction_receipts_v1,
    )

    receipts = selected_page_extraction_receipts_v1(
        database_path,
        page_json_version_ids=selected_page_json_version_ids,
    )
    request_versions = {
        request.get("page_json_version_id")
        for request in fragment_requests
        if type(request) is dict
    }
    selected_by_version = {
        receipt["page_json_version_id"]: (ordinal, receipt)
        for ordinal, receipt in enumerate(receipts, start=1)
    }
    if not request_versions or not request_versions <= set(selected_by_version):
        raise _error("document-region store replay locators are outside the selected frontier")
    ordinals = [selected_by_version[version][0] for version in request_versions]
    first, last = min(ordinals), max(ordinals)
    interval_ids = list(selected_page_json_version_ids[first - 1 : last])
    loaded = load_page_json_versions_v1(database_path, page_json_version_ids=interval_ids)
    source_identity = {
        (record["source_logical_name"], record["source_sha256"]) for record in loaded
    }
    if len(source_identity) != 1:
        raise _error("document-region store replay crosses source documents")
    document_id = "drfcv1:document:" + canonical_json_sha256_v1(
        {
            "source_logical_name": loaded[0]["source_logical_name"],
            "source_sha256": loaded[0]["source_sha256"],
        }
    )
    page_records = [
        {
            "document_id": document_id,
            "page_json": record["page_json"],
            "page_json_version_id": record["page_json_version_id"],
            "physical_page": record["physical_page"],
            "selected_frontier_ordinal": first + offset,
            "source_logical_name": record["source_logical_name"],
            "source_sha256": record["source_sha256"],
        }
        for offset, record in enumerate(loaded)
    ]
    if document_period_axis.get("document_id") != document_id:
        raise _error("document-region store period axis document identity drifted")
    return validate_document_region_fragment_composition_replay_v1(
        selected_page_json_version_ids=selected_page_json_version_ids,
        page_records=page_records,
        fragment_requests=fragment_requests,
        document_period_axis=document_period_axis,
        policy=policy,
        compiled_specs=compiled_specs,
        projection_adapter=projection_adapter,
        projection_inventory_adapter=projection_inventory_adapter,
        composition=composition,
    )
