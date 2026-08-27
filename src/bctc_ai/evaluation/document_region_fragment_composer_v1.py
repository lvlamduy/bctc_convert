"""Authenticated composition of disjoint Gemini JSON accounting fragments.

The primitive is deliberately family-configured rather than bank/page routed.
It projects exact, manifest-selected JSON table cells into one bounded document
region, composes only reset-fenced source fragments, and delegates all
accounting closure to the existing hierarchical evaluator.  It never reads a
PDF, invokes OCR, or treats a synthetic table as source evidence.
"""

from __future__ import annotations

import hashlib
import inspect
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
ADAPTER_IDENTITY_FORMAT_VERSION = "DOCUMENT_REGION_FRAGMENT_ADAPTER_IDENTITY_V1"
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


def document_region_fragment_adapter_identity_v1(
    adapter: Callable[..., Any], *, adapter_id: str, adapter_format_version: str
) -> dict[str, Any]:
    """Return the sealed implementation/dependency pin for a registered adapter."""

    registry = _trusted_adapter_registry_v1()
    registered = registry.get(adapter_id)
    if (
        not inspect.isfunction(adapter)
        or registered is None
        or registered["callable"] is not adapter
        or registered["adapter_format_version"] != adapter_format_version
        or type(adapter_id) is not str
        or re.fullmatch(r"[A-Z][A-Z0-9_]{2,127}", adapter_id) is None
        or type(adapter_format_version) is not str
        or re.fullmatch(r"[A-Z][A-Z0-9_]{2,127}", adapter_format_version) is None
        or adapter.__closure__ is not None
    ):
        raise _error("document-region adapter is not in the trusted registry")
    dependency_manifest = []
    for dependency in registered["dependencies"]:
        dependency = inspect.unwrap(dependency)
        source_file = inspect.getsourcefile(dependency)
        if source_file is None:
            raise _error("document-region adapter dependency source is unavailable")
        try:
            callable_source = inspect.getsource(dependency).encode("utf-8")
            module_source = Path(source_file).read_bytes()
        except (OSError, TypeError) as exc:
            raise _error("document-region adapter dependency source is unavailable") from exc
        dependency_manifest.append(
            {
                "callable_module": dependency.__module__,
                "callable_qualname": dependency.__qualname__,
                "callable_source_sha256": hashlib.sha256(callable_source).hexdigest(),
                "module_source_sha256": hashlib.sha256(module_source).hexdigest(),
            }
        )
    material = {
        "adapter_format_version": adapter_format_version,
        "adapter_id": adapter_id,
        "adapter_kind": registered["adapter_kind"],
        "dependency_manifest": dependency_manifest,
    }
    return {
        "adapter_format_version": adapter_format_version,
        "adapter_id": adapter_id,
        "adapter_kind": registered["adapter_kind"],
        "dependency_manifest": dependency_manifest,
        "dependency_manifest_sha256": canonical_json_sha256_v1(dependency_manifest),
        "format_version": ADAPTER_IDENTITY_FORMAT_VERSION,
        "implementation_ref_sha256": canonical_json_sha256_v1(material),
    }


def _validate_adapter_identity(value: Any, *, field: str) -> dict[str, Any]:
    required = {
        "adapter_format_version",
        "adapter_id",
        "adapter_kind",
        "dependency_manifest",
        "dependency_manifest_sha256",
        "format_version",
        "implementation_ref_sha256",
    }
    if (
        type(value) is not dict
        or set(value) != required
        or value.get("format_version") != ADAPTER_IDENTITY_FORMAT_VERSION
        or type(value.get("adapter_id")) is not str
        or re.fullmatch(r"[A-Z][A-Z0-9_]{2,127}", value["adapter_id"]) is None
        or type(value.get("adapter_format_version")) is not str
        or re.fullmatch(r"[A-Z][A-Z0-9_]{2,127}", value["adapter_format_version"]) is None
        or value.get("adapter_kind") not in {"INVENTORY", "PROJECTION"}
        or type(value.get("dependency_manifest")) is not list
        or not value["dependency_manifest"]
        or value.get("dependency_manifest_sha256")
        != canonical_json_sha256_v1(value.get("dependency_manifest"))
        or type(value.get("implementation_ref_sha256")) is not str
        or _SHA256.fullmatch(value["implementation_ref_sha256"]) is None
    ):
        raise _error(f"document-region {field} adapter identity is invalid")
    registry = _trusted_adapter_registry_v1()
    registered = registry.get(value["adapter_id"])
    if registered is None:
        raise _error(f"document-region {field} adapter is not registered")
    expected = document_region_fragment_adapter_identity_v1(
        registered["callable"],
        adapter_id=value["adapter_id"],
        adapter_format_version=value["adapter_format_version"],
    )
    if expected != value:
        raise _error(f"document-region {field} registered adapter pin drifted")
    expected_kind = "INVENTORY" if field == "projection-inventory" else "PROJECTION"
    if value["adapter_kind"] != expected_kind:
        raise _error(f"document-region {field} adapter kind drifted")
    return canonical_clone_v1(value)


def _assert_callable_matches_adapter_identity(
    adapter: Callable[..., Any], identity: Mapping[str, Any], *, field: str
) -> None:
    expected = document_region_fragment_adapter_identity_v1(
        adapter,
        adapter_id=identity["adapter_id"],
        adapter_format_version=identity["adapter_format_version"],
    )
    if expected != identity:
        raise _error(f"document-region {field} adapter implementation pin drifted")


def _trusted_adapter_registry_v1() -> dict[str, dict[str, Any]]:
    """Return the code-owned, non-policy-extensible adapter allowlist."""

    shared_dependencies = (
        _money,
        _normalized,
        _period_signature,
        _row_role_match_modes,
        canonical_json_sha256_v1,
    )
    return {
        "DOCUMENT_REGION_COLUMN_LANE_PROJECTION": {
            "adapter_format_version": "DOCUMENT_REGION_COLUMN_LANE_ADAPTER_V1",
            "adapter_kind": "PROJECTION",
            "callable": project_column_lane_document_region_fragment_v1,
            "dependencies": (
                project_column_lane_document_region_fragment_v1,
                *shared_dependencies,
            ),
        },
        "DOCUMENT_REGION_COLUMN_LANE_INVENTORY": {
            "adapter_format_version": "DOCUMENT_REGION_COLUMN_LANE_INVENTORY_V1",
            "adapter_kind": "INVENTORY",
            "callable": inventory_column_lane_document_region_fragment_v1,
            "dependencies": (
                inventory_column_lane_document_region_fragment_v1,
                *shared_dependencies,
            ),
        },
        "DOCUMENT_REGION_EXACT_AXIS_PROJECTION": {
            "adapter_format_version": "DOCUMENT_REGION_EXACT_AXIS_ADAPTER_V1",
            "adapter_kind": "PROJECTION",
            "callable": project_exact_axis_document_region_fragment_v1,
            "dependencies": (
                project_exact_axis_document_region_fragment_v1,
                build_normalized_document_region_fragment_candidate_v1,
                *shared_dependencies,
            ),
        },
        "DOCUMENT_REGION_EXACT_AXIS_INVENTORY": {
            "adapter_format_version": "DOCUMENT_REGION_EXACT_AXIS_INVENTORY_V1",
            "adapter_kind": "INVENTORY",
            "callable": inventory_exact_axis_document_region_fragment_v1,
            "dependencies": (
                inventory_exact_axis_document_region_fragment_v1,
                *shared_dependencies,
            ),
        },
    }


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
        "metric_projection_rules",
        "minimum_distinctive_child_roles",
        "owner_aliases",
        "period_axis_cardinality",
        "period_axis_semantics",
        "projection_adapter_identity",
        "projection_inventory_adapter_identity",
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
        or not 1 <= policy["maximum_components"] <= 8
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
    compiled["projection_adapter_identity"] = _validate_adapter_identity(
        policy["projection_adapter_identity"], field="projection"
    )
    compiled["projection_inventory_adapter_identity"] = _validate_adapter_identity(
        policy["projection_inventory_adapter_identity"], field="projection-inventory"
    )
    metric_rules = policy["metric_projection_rules"]
    allowed_metric_rules = {
        "CARRYING_AMOUNT": "EXACT_MONEY_COLUMN_HEADER_ALIAS",
        "COST_AMOUNT": "EXACT_MONEY_COLUMN_HEADER_ALIAS",
        "PERCENTAGE": "EXACT_PERCENT_COLUMN_HEADER_ALIAS",
        "UNQUALIFIED_BALANCE_AMOUNT": "EXACT_MONEY_COLUMN_UNQUALIFIED",
    }
    if type(metric_rules) is not list or not metric_rules:
        raise _error("document-region metric projection rules are invalid")
    compiled_metric_rules = {}
    for rule in metric_rules:
        if (
            type(rule) is not dict
            or set(rule) != {"header_aliases", "metric_signature", "rule", "source_value_kind"}
            or rule.get("metric_signature") not in allowed_metric_rules
            or rule.get("rule") != allowed_metric_rules[rule["metric_signature"]]
            or rule.get("source_value_kind")
            != ("PERCENT" if rule["metric_signature"] == "PERCENTAGE" else "MONEY")
            or rule["metric_signature"] in compiled_metric_rules
        ):
            raise _error("document-region metric projection rules are invalid")
        aliases = _compile_aliases(
            rule.get("header_aliases"),
            field="metric-header",
            allow_empty=rule["metric_signature"] == "UNQUALIFIED_BALANCE_AMOUNT",
        )
        if (rule["metric_signature"] == "UNQUALIFIED_BALANCE_AMOUNT") != (not aliases):
            raise _error("document-region metric header aliases are invalid")
        compiled_metric_rules[rule["metric_signature"]] = {
            **canonical_clone_v1(rule),
            "header_aliases": aliases,
        }
    compiled["metric_projection_rules"] = compiled_metric_rules
    compiled["compiled_specs_sha256"] = canonical_json_sha256_v1(
        {
            "evaluation": compiled_specs.get("evaluation"),
            "schema": compiled_specs.get("schema"),
            "topology": compiled_specs.get("topology"),
        }
    )
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
        "composer_policy_sha256",
        "control_column_ids",
        "mapping_column_ids",
        "page_json_version_id",
        "projection_adapter_format_version",
        "projection_adapter_id",
        "projection_adapter_implementation_ref_sha256",
        "projection_inventory_adapter_format_version",
        "projection_inventory_adapter_id",
        "projection_inventory_adapter_implementation_ref_sha256",
        "projection_kind",
        "section_id",
        "table_id",
    }
    if (
        type(request) is not dict
        or set(request) != request_fields
        or request.get("composer_policy_sha256") != policy["policy_sha256"]
        or request.get("page_json_version_id") != page_record["page_json_version_id"]
        or request.get("projection_adapter_id")
        != policy["projection_adapter_identity"]["adapter_id"]
        or request.get("projection_adapter_format_version")
        != policy["projection_adapter_identity"]["adapter_format_version"]
        or request.get("projection_adapter_implementation_ref_sha256")
        != policy["projection_adapter_identity"]["implementation_ref_sha256"]
        or request.get("projection_inventory_adapter_id")
        != policy["projection_inventory_adapter_identity"]["adapter_id"]
        or request.get("projection_inventory_adapter_format_version")
        != policy["projection_inventory_adapter_identity"]["adapter_format_version"]
        or request.get("projection_inventory_adapter_implementation_ref_sha256")
        != policy["projection_inventory_adapter_identity"]["implementation_ref_sha256"]
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
        "adapter_identity": canonical_clone_v1(policy["projection_adapter_identity"]),
        "inventory_adapter_identity": canonical_clone_v1(
            policy["projection_inventory_adapter_identity"]
        ),
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
        "adapter_identity": canonical_clone_v1(policy["projection_adapter_identity"]),
        "anonymous_rows": anonymous_rows,
        "binding_model": "ROW_COLUMN_LANE_REFERENCE",
        "candidate_id": "drfcv1:fragment:" + canonical_json_sha256_v1(identity_material),
        "continuation": table.get("continuation"),
        "document_id": page_record["document_id"],
        "format_version": FRAGMENT_FORMAT_VERSION,
        "inventory_adapter_identity": canonical_clone_v1(
            policy["projection_inventory_adapter_identity"]
        ),
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
        try:
            roles = _row_role_match_modes(
                row,
                topology=compiled_specs["topology"],
                aliases_by_role=compiled_specs["aliases_by_role"],
                enable_declared_equivalences=enabled,
            )
        except ValueError:
            roles = {"AMBIGUOUS": "AMBIGUOUS"}
        has_money = any(values[index] is not None for index in money_indices)
        if roles or (has_money and row.get("row_kind") in {"GROUP", "SUBTOTAL", "TOTAL"}):
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
        "composer_policy_sha256": policy["policy_sha256"],
        "control_column_ids": [f"c{index + 1}" for index in control_indices],
        "mapping_column_ids": [f"c{index + 1}" for index in mapping_indices],
        "page_json_version_id": page_record["page_json_version_id"],
        "projection_adapter_id": policy["projection_adapter_identity"]["adapter_id"],
        "projection_adapter_implementation_ref_sha256": policy["projection_adapter_identity"][
            "implementation_ref_sha256"
        ],
        "projection_adapter_format_version": policy["projection_adapter_identity"][
            "adapter_format_version"
        ],
        "projection_inventory_adapter_format_version": policy[
            "projection_inventory_adapter_identity"
        ]["adapter_format_version"],
        "projection_inventory_adapter_id": policy["projection_inventory_adapter_identity"][
            "adapter_id"
        ],
        "projection_inventory_adapter_implementation_ref_sha256": policy[
            "projection_inventory_adapter_identity"
        ]["implementation_ref_sha256"],
        "projection_kind": "BALANCE_MAPPING" if mapping_indices else "DECLARED_CONTROL",
        "section_id": section_id,
        "table_id": table_id,
    }


_DECLARED_TOTAL_HEADER_ALIASES = {"cong", "tong", "tong cong", "total"}


def _registered_request_trust_axis(policy: Mapping[str, Any]) -> dict[str, Any]:
    projection = policy["projection_adapter_identity"]
    inventory = policy["projection_inventory_adapter_identity"]
    return {
        "composer_policy_sha256": policy["policy_sha256"],
        "projection_adapter_format_version": projection["adapter_format_version"],
        "projection_adapter_id": projection["adapter_id"],
        "projection_adapter_implementation_ref_sha256": projection["implementation_ref_sha256"],
        "projection_inventory_adapter_format_version": inventory["adapter_format_version"],
        "projection_inventory_adapter_id": inventory["adapter_id"],
        "projection_inventory_adapter_implementation_ref_sha256": inventory[
            "implementation_ref_sha256"
        ],
    }


def _exact_axis_header_role_modes(
    column: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> tuple[str | None, dict[str, str]]:
    enabled = (
        compiled_specs["evaluation"].get("format_version") == "ACCOUNTING_FAMILY_EVALUATION_SPEC_V8"
    )
    candidates = [
        value for value in column.get("header_path_exact", []) if type(value) is str and value
    ]
    matched: dict[str, str] = {}
    matched_label = None
    for value in candidates:
        try:
            modes = _row_role_match_modes(
                {
                    "hierarchy_path_exact": [value],
                    "label_exact": value,
                    "row_kind": "ITEM",
                },
                topology=compiled_specs["topology"],
                aliases_by_role=compiled_specs["aliases_by_role"],
                enable_declared_equivalences=enabled,
            )
        except ValueError as exc:
            raise _error("exact-axis column role header is ambiguous") from exc
        if modes:
            if matched and modes != matched:
                raise _error("exact-axis column exposes multiple role headers")
            matched = modes
            matched_label = value
    return matched_label, matched


def _exact_axis_money(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    try:
        return _money(value)
    except ValueError as exc:
        raise _error("exact-axis source money is invalid") from exc


def _exact_axis_period_signature(value: Any) -> tuple[str, str] | None:
    if type(value) is not str or not value:
        return None
    return _period_signature(value)


def _exact_axis_declared_role_inventory_v1(
    *, table: Mapping[str, Any], compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Return exact row/header locators that make a table family-role-bearing."""

    enabled = (
        compiled_specs["evaluation"].get("format_version") == "ACCOUNTING_FAMILY_EVALUATION_SPEC_V8"
    )
    inventory = []
    rows = table.get("rows")
    if type(rows) is list:
        for row_ordinal, row in enumerate(rows, start=1):
            if type(row) is not dict:
                continue
            try:
                modes = _row_role_match_modes(
                    row,
                    topology=compiled_specs["topology"],
                    aliases_by_role=compiled_specs["aliases_by_role"],
                    enable_declared_equivalences=enabled,
                )
            except (TypeError, ValueError):
                inventory.append(
                    {
                        "evidence_kind": "AMBIGUOUS_ROLE_ROW",
                        "hierarchy_path_exact": canonical_clone_v1(row.get("hierarchy_path_exact")),
                        "label_exact": row.get("label_exact"),
                        "row_id": f"r{row_ordinal}",
                    }
                )
                continue
            if modes:
                inventory.append(
                    {
                        "evidence_kind": "DECLARED_ROLE_ROW",
                        "hierarchy_path_exact": canonical_clone_v1(row.get("hierarchy_path_exact")),
                        "label_exact": row.get("label_exact"),
                        "role_match_modes": canonical_clone_v1(modes),
                        "row_id": f"r{row_ordinal}",
                    }
                )
    columns = table.get("columns")
    if type(columns) is list:
        for column_ordinal, column in enumerate(columns, start=1):
            if type(column) is not dict:
                continue
            try:
                label, modes = _exact_axis_header_role_modes(column, compiled_specs=compiled_specs)
            except DocumentRegionFragmentComposerV1Error:
                inventory.append(
                    {
                        "column_id": f"c{column_ordinal}",
                        "evidence_kind": "AMBIGUOUS_ROLE_COLUMN_HEADER",
                        "header_path_exact": canonical_clone_v1(column.get("header_path_exact")),
                    }
                )
                continue
            if modes:
                inventory.append(
                    {
                        "column_id": f"c{column_ordinal}",
                        "evidence_kind": "DECLARED_ROLE_COLUMN_HEADER",
                        "header_path_exact": canonical_clone_v1(column.get("header_path_exact")),
                        "label_exact": label,
                        "role_match_modes": canonical_clone_v1(modes),
                    }
                )
    return inventory


def _unsupported_exact_axis_inventory_payload_v1(
    *,
    page_record: Mapping[str, Any],
    section_id: str,
    table_id: str,
    policy: Mapping[str, Any],
    role_inventory: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        **_registered_request_trust_axis(policy),
        "adapter_projection_receipt": {
            "layout_kind": "UNSUPPORTED_ROLE_BEARING_EXACT_AXIS_LAYOUT",
            "role_inventory": canonical_clone_v1(list(role_inventory)),
            "rule": "EXHAUSTIVE_ROLE_BEARING_TABLE_FAILS_CLOSED_V1",
        },
        "logical_rows": [],
        "page_json_version_id": page_record["page_json_version_id"],
        "projection_kind": "BALANCE_MAPPING",
        "projection_reasons": ["UNSUPPORTED_ROLE_BEARING_EXACT_AXIS_LAYOUT"],
        "section_id": section_id,
        "source_bindings": [],
        "table_id": table_id,
    }


def _build_supported_exact_axis_inventory_payload_v1(
    *,
    page_record: Mapping[str, Any],
    section_id: str,
    table_id: str,
    document_period_axis: Mapping[str, Any],
    policy: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    _section, table, section_ordinal, table_ordinal = _source_nodes(
        page_record["page_json"], section_id=section_id, table_id=table_id
    )
    columns = table.get("columns")
    rows = table.get("rows")
    if type(columns) is not list or type(rows) is not list:
        return None
    expected_periods = [tuple(value) for value in document_period_axis["period_signatures"]]
    expected_set = set(expected_periods)
    unit_signature = _normalized(table.get("unit_exact"))
    if unit_signature not in policy["unit_aliases"]:
        return None
    if "UNQUALIFIED_BALANCE_AMOUNT" not in policy["metric_projection_rules"]:
        return None
    bindings: list[dict[str, Any]] = []

    def add(kind: str, **fields: Any) -> str:
        binding_id = f"b{len(bindings) + 1}"
        bindings.append({"binding_id": binding_id, "binding_kind": kind, **fields})
        return binding_id

    unit_id = add("TABLE_UNIT", unit_exact=table.get("unit_exact"))
    enabled = (
        compiled_specs["evaluation"].get("format_version") == "ACCOUNTING_FAMILY_EVALUATION_SPEC_V8"
    )
    header_roles = []
    for column_ordinal, column in enumerate(columns, start=1):
        if type(column) is not dict or column.get("value_kind") != "MONEY":
            continue
        label, modes = _exact_axis_header_role_modes(column, compiled_specs=compiled_specs)
        header = [
            value for value in column.get("header_path_exact", []) if type(value) is str and value
        ]
        total_label = next(
            (value for value in header if _normalized(value) in _DECLARED_TOTAL_HEADER_ALIASES),
            None,
        )
        if modes or total_label is not None:
            header_roles.append((column_ordinal, column, label or total_label, modes))
    row_periods = []
    for row_ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict:
            continue
        signature = _exact_axis_period_signature(row.get("label_exact"))
        if signature in expected_set:
            row_periods.append((row_ordinal, row, signature))
    logical_rows = []
    layout_kind = None
    if len(header_roles) >= 2 and {period for _, _, period in row_periods} == expected_set:
        layout_kind = "TRANSPOSED_PERIOD_ROW_ROLE_COLUMN"
        column_binding_ids = {
            ordinal: add(
                "COLUMN",
                column_id=f"c{ordinal}",
                header_path_exact=column.get("header_path_exact"),
                value_kind=column.get("value_kind"),
            )
            for ordinal, column, _label, _modes in header_roles
        }
        period_binding_ids = {
            period: add(
                "ROW",
                row_id=f"r{ordinal}",
                label_exact=row.get("label_exact"),
                hierarchy_path_exact=row.get("hierarchy_path_exact"),
                row_kind=row.get("row_kind"),
            )
            for ordinal, row, period in row_periods
        }
        row_by_period = {period: (ordinal, row) for ordinal, row, period in row_periods}
        for logical_ordinal, (column_ordinal, column, label, modes) in enumerate(
            header_roles, start=1
        ):
            header = [
                value
                for value in column.get("header_path_exact", [])
                if type(value) is str and value
            ]
            label_index = header.index(label)
            population = header[:label_index]
            cells = []
            for cell_ordinal, period in enumerate(expected_periods, start=1):
                row_ordinal, row = row_by_period[period]
                values = row.get("values_exact")
                if type(values) is not list or len(values) != len(columns):
                    raise _error("exact-axis transposed value vector drifted")
                raw = values[column_ordinal - 1]
                value_id = add(
                    "VALUE_CELL",
                    row_id=f"r{row_ordinal}",
                    column_id=f"c{column_ordinal}",
                    source_text=raw,
                )
                cells.append(
                    {
                        "layout_relation": {
                            "metric_axis_binding_id": column_binding_ids[column_ordinal],
                            "period_axis_binding_id": period_binding_ids[period],
                            "relation_kind": "TRANSPOSED_PERIOD_ROW_ROLE_COLUMN",
                            "role_axis_binding_id": column_binding_ids[column_ordinal],
                            "unit_axis_binding_id": unit_id,
                        },
                        "logical_cell_id": f"lc{logical_ordinal}_{cell_ordinal}",
                        "metric_signature": "UNQUALIFIED_BALANCE_AMOUNT",
                        "metric_source_binding_ids": [column_binding_ids[column_ordinal]],
                        "money": _exact_axis_money(raw),
                        "period_signature": list(period),
                        "period_source_binding_ids": [period_binding_ids[period]],
                        "source_text": raw,
                        "unit_signature": unit_signature,
                        "unit_source_binding_ids": [unit_id],
                        "value_source_binding_ids": [value_id],
                    }
                )
            logical_rows.append(
                {
                    "cells": cells,
                    "hierarchy_path_exact": [*population, label],
                    "label_exact": label,
                    "label_match_modes": modes,
                    "logical_row_id": f"lr{logical_ordinal}",
                    "population_context_exact": population,
                    "population_source_binding_ids": (
                        [column_binding_ids[column_ordinal]] if population else []
                    ),
                    "role_source_binding_ids": (
                        [column_binding_ids[column_ordinal]] if modes else []
                    ),
                    "row_kind": "ITEM" if modes else "TOTAL",
                    "row_kind_derivation": (
                        "DECLARED_ROLE_HEADER_ITEM" if modes else "DECLARED_TOTAL_HEADER"
                    ),
                    "row_source_binding_ids": [column_binding_ids[column_ordinal]],
                    "source_position": [
                        page_record["selected_frontier_ordinal"],
                        section_ordinal,
                        table_ordinal,
                        min(ordinal for ordinal, _row, _period in row_periods),
                        column_ordinal,
                    ],
                }
            )
    else:
        money_columns = [
            (ordinal, column)
            for ordinal, column in enumerate(columns, start=1)
            if type(column) is dict and column.get("value_kind") == "MONEY"
        ]
        period_headers = [
            (ordinal, row, _exact_axis_period_signature(row.get("label_exact")))
            for ordinal, row in enumerate(rows, start=1)
            if type(row) is dict
            and _exact_axis_period_signature(row.get("label_exact")) in expected_set
        ]
        if len(money_columns) != 1 or {period for _, _, period in period_headers} != expected_set:
            return None
        layout_kind = "STACKED_PERIOD_ROW_BLOCK"
        column_ordinal, column = money_columns[0]
        metric_id = add(
            "COLUMN",
            column_id=f"c{column_ordinal}",
            header_path_exact=column.get("header_path_exact"),
            value_kind=column.get("value_kind"),
        )
        period_headers.sort()
        period_rows = {}
        role_rows_by_period: dict[tuple[str, str], dict[str, tuple[int, dict[str, Any]]]] = {}
        totals_by_period = {}
        period_binding_ids = {}
        block_binding_ids = {}
        row_binding_ids = {}
        for block_index, (period_row_ordinal, period_row, period) in enumerate(period_headers):
            boundary = (
                period_headers[block_index + 1][0]
                if block_index + 1 < len(period_headers)
                else len(rows) + 1
            )
            block_ordinals = list(range(period_row_ordinal, boundary))
            period_binding_ids[period] = add(
                "ROW",
                row_id=f"r{period_row_ordinal}",
                label_exact=period_row.get("label_exact"),
                hierarchy_path_exact=period_row.get("hierarchy_path_exact"),
                row_kind=period_row.get("row_kind"),
            )
            block_binding_ids[period] = add(
                "ROW_BLOCK", row_ids=[f"r{ordinal}" for ordinal in block_ordinals]
            )
            period_rows[period] = (period_row_ordinal, period_row)
            roles_for_period = {}
            total_for_period = None
            for row_ordinal in block_ordinals[1:]:
                row = rows[row_ordinal - 1]
                if type(row) is not dict:
                    continue
                try:
                    modes = _row_role_match_modes(
                        row,
                        topology=compiled_specs["topology"],
                        aliases_by_role=compiled_specs["aliases_by_role"],
                        enable_declared_equivalences=enabled,
                    )
                except ValueError as exc:
                    raise _error("exact-axis stacked role row is ambiguous") from exc
                is_total = (
                    row.get("row_kind") == "TOTAL"
                    or _normalized(row.get("label_exact")) in _DECLARED_TOTAL_HEADER_ALIASES
                )
                if not modes and not is_total:
                    continue
                row_id = add(
                    "ROW",
                    row_id=f"r{row_ordinal}",
                    label_exact=row.get("label_exact"),
                    hierarchy_path_exact=row.get("hierarchy_path_exact"),
                    row_kind=row.get("row_kind"),
                )
                row_binding_ids[(period, row_ordinal)] = row_id
                if modes:
                    for role in modes:
                        if role in roles_for_period:
                            raise _error("exact-axis stacked role repeats inside a period block")
                    roles_for_period.update(
                        {role: (row_ordinal, row, modes, row_id) for role in modes}
                    )
                elif is_total:
                    if total_for_period is not None:
                        raise _error("exact-axis stacked total repeats inside a period block")
                    total_for_period = (row_ordinal, row, row_id)
            role_rows_by_period[period] = roles_for_period
            totals_by_period[period] = total_for_period
        common_roles = set.intersection(
            *(set(role_rows_by_period[period]) for period in expected_periods)
        )
        first_period = expected_periods[0]
        ordered_entries = [
            (
                role_rows_by_period[first_period][role][0],
                role,
                role_rows_by_period[first_period][role][1].get("label_exact"),
                role_rows_by_period[first_period][role][2],
                role_rows_by_period[first_period][role][1].get("row_kind"),
            )
            for role in common_roles
        ]
        if all(totals_by_period.get(period) is not None for period in expected_periods):
            total = totals_by_period[first_period]
            ordered_entries.append((total[0], None, total[1].get("label_exact"), {}, "TOTAL"))
        ordered_entries.sort()
        if len(common_roles) < 2 or not ordered_entries:
            return None
        for logical_ordinal, (_position, role, label, modes, row_kind) in enumerate(
            ordered_entries, start=1
        ):
            source_rows_for_logical = []
            source_row_ordinals_for_logical = []
            cells = []
            contexts = []
            for cell_ordinal, period in enumerate(expected_periods, start=1):
                if role is None:
                    row_ordinal, row, row_id = totals_by_period[period]
                else:
                    row_ordinal, row, _modes, row_id = role_rows_by_period[period][role]
                source_rows_for_logical.append(row_id)
                source_row_ordinals_for_logical.append(row_ordinal)
                path = [
                    value
                    for value in row.get("hierarchy_path_exact", [])
                    if type(value) is str and value
                ]
                context = path[:-1] if path and _normalized(path[-1]) == _normalized(label) else []
                contexts.append(context)
                values = row.get("values_exact")
                if type(values) is not list or len(values) != len(columns):
                    raise _error("exact-axis stacked value vector drifted")
                raw = values[column_ordinal - 1]
                value_id = add(
                    "VALUE_CELL",
                    row_id=f"r{row_ordinal}",
                    column_id=f"c{column_ordinal}",
                    source_text=raw,
                )
                cells.append(
                    {
                        "layout_relation": {
                            "metric_axis_binding_id": metric_id,
                            "period_axis_binding_id": period_binding_ids[period],
                            "period_block_binding_id": block_binding_ids[period],
                            "relation_kind": "STACKED_PERIOD_ROW_BLOCK",
                            "role_axis_binding_id": row_id,
                            "unit_axis_binding_id": unit_id,
                        },
                        "logical_cell_id": f"lc{logical_ordinal}_{cell_ordinal}",
                        "metric_signature": "UNQUALIFIED_BALANCE_AMOUNT",
                        "metric_source_binding_ids": [metric_id],
                        "money": _exact_axis_money(raw),
                        "period_signature": list(period),
                        "period_source_binding_ids": [
                            period_binding_ids[period],
                            block_binding_ids[period],
                        ],
                        "source_text": raw,
                        "unit_signature": unit_signature,
                        "unit_source_binding_ids": [unit_id],
                        "value_source_binding_ids": [value_id],
                    }
                )
            if any(context != contexts[0] for context in contexts):
                raise _error("exact-axis stacked role population context drifted across periods")
            logical_rows.append(
                {
                    "cells": cells,
                    "hierarchy_path_exact": [*contexts[0], label],
                    "label_exact": label,
                    "label_match_modes": modes,
                    "logical_row_id": f"lr{logical_ordinal}",
                    "population_context_exact": contexts[0],
                    "population_source_binding_ids": (
                        source_rows_for_logical if contexts[0] else []
                    ),
                    "role_source_binding_ids": source_rows_for_logical if modes else [],
                    "row_kind": row_kind,
                    "row_kind_derivation": "EXACT_SOURCE_ROW_KIND",
                    "row_source_binding_ids": source_rows_for_logical,
                    "source_position": [
                        page_record["selected_frontier_ordinal"],
                        section_ordinal,
                        table_ordinal,
                        min(source_row_ordinals_for_logical),
                        column_ordinal,
                    ],
                }
            )
    return {
        **_registered_request_trust_axis(policy),
        "adapter_projection_receipt": {
            "layout_kind": layout_kind,
            "metric_signature": "UNQUALIFIED_BALANCE_AMOUNT",
            "period_signatures": [list(period) for period in expected_periods],
            "rule": "EXACT_SOURCE_AXIS_LAYOUT_RELATION_V1",
        },
        "logical_rows": logical_rows,
        "page_json_version_id": page_record["page_json_version_id"],
        "projection_kind": "BALANCE_MAPPING",
        "projection_reasons": [],
        "section_id": section_id,
        "source_bindings": bindings,
        "table_id": table_id,
    }


def _build_exact_axis_inventory_payload_v1(
    *,
    page_record: Mapping[str, Any],
    section_id: str,
    table_id: str,
    document_period_axis: Mapping[str, Any],
    policy: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    _section, table, _section_ordinal, _table_ordinal = _source_nodes(
        page_record["page_json"], section_id=section_id, table_id=table_id
    )
    role_inventory = _exact_axis_declared_role_inventory_v1(
        table=table, compiled_specs=compiled_specs
    )
    if not role_inventory:
        return None
    try:
        supported = _build_supported_exact_axis_inventory_payload_v1(
            page_record=page_record,
            section_id=section_id,
            table_id=table_id,
            document_period_axis=document_period_axis,
            policy=policy,
            compiled_specs=compiled_specs,
        )
    except DocumentRegionFragmentComposerV1Error:
        supported = None
    if supported is not None:
        return supported
    return _unsupported_exact_axis_inventory_payload_v1(
        page_record=page_record,
        section_id=section_id,
        table_id=table_id,
        policy=policy,
        role_inventory=role_inventory,
    )


def inventory_exact_axis_document_region_fragment_v1(
    *,
    page_record: Mapping[str, Any],
    section_id: str,
    table_id: str,
    document_period_axis: Mapping[str, Any],
    policy: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Inventory one trusted stacked/transposed exact-axis projection."""

    return _build_exact_axis_inventory_payload_v1(
        page_record=page_record,
        section_id=section_id,
        table_id=table_id,
        document_period_axis=document_period_axis,
        policy=policy,
        compiled_specs=compiled_specs,
    )


def project_exact_axis_document_region_fragment_v1(
    *,
    page_record: Mapping[str, Any],
    request: Mapping[str, Any],
    document_period_axis: Mapping[str, Any],
    policy: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a candidate from the trusted inventory's exact-axis payload."""

    del document_period_axis
    required = {
        *set(_registered_request_trust_axis(policy)),
        "adapter_projection_receipt",
        "logical_rows",
        "page_json_version_id",
        "projection_kind",
        "projection_reasons",
        "section_id",
        "source_bindings",
        "table_id",
    }
    if type(request) is not dict or set(request) != required:
        raise _error("exact-axis fragment request contract drifted")
    return build_normalized_document_region_fragment_candidate_v1(
        page_record=page_record,
        section_id=request["section_id"],
        table_id=request["table_id"],
        adapter_format_version=policy["projection_adapter_identity"]["adapter_format_version"],
        projection_kind=request["projection_kind"],
        source_bindings=request["source_bindings"],
        logical_rows=request["logical_rows"],
        adapter_projection_receipt=request["adapter_projection_receipt"],
        reasons=request["projection_reasons"],
        policy=policy,
        compiled_specs=compiled_specs,
    )


def build_normalized_document_region_fragment_candidate_v1(
    *,
    page_record: Mapping[str, Any],
    section_id: str,
    table_id: str,
    adapter_format_version: str,
    projection_kind: str,
    source_bindings: Sequence[Mapping[str, Any]],
    logical_rows: Sequence[Mapping[str, Any]],
    adapter_projection_receipt: Mapping[str, Any],
    reasons: Sequence[str],
    policy: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the layout-neutral normalized fragment envelope.

    Table adapters remain responsible for interpreting their axes.  Every
    normalized role and cell must reference one or more exact source bindings;
    the composer replays those bindings against canonical page JSON before it
    accepts the adapter projection.
    """

    if (
        type(adapter_format_version) is not str
        or not adapter_format_version
        or projection_kind not in {"BALANCE_MAPPING", "DECLARED_CONTROL"}
        or type(source_bindings) not in {list, tuple}
        or type(logical_rows) not in {list, tuple}
        or type(adapter_projection_receipt) is not dict
        or type(reasons) not in {list, tuple}
        or any(type(reason) is not str or not reason for reason in reasons)
    ):
        raise _error("normalized document-region adapter projection is invalid")
    _section, table, _section_ordinal, _table_ordinal = _source_nodes(
        page_record["page_json"], section_id=section_id, table_id=table_id
    )
    surfaces = _table_surfaces(page_record=page_record, section_id=section_id, table_id=table_id)
    owner_evidence = []
    branch_evidence = []
    for surface in surfaces:
        owner_matches = _contains_alias(surface["source_exact"], policy["owner_aliases"])
        branch_matches = _contains_alias(surface["source_exact"], policy["branch_aliases"])
        if owner_matches:
            owner_evidence.append({**canonical_clone_v1(surface), "matched_aliases": owner_matches})
        if branch_matches:
            branch_evidence.append(
                {**canonical_clone_v1(surface), "matched_aliases": branch_matches}
            )
    rows = canonical_clone_v1(list(logical_rows))
    bindings = canonical_clone_v1(list(source_bindings))
    role_kinds = {
        child["role"]: child["role_kind"] for child in compiled_specs["topology"]["children"]
    }
    derived_reasons = list(reasons)
    for row in rows:
        roles = row.get("label_match_modes", {}) if type(row) is dict else {}
        cells = row.get("cells", []) if type(row) is dict else []
        if (
            type(roles) is dict
            and type(cells) is list
            and any(type(cell) is dict and cell.get("money") is None for cell in cells)
            and any(role_kinds.get(role) != "STRUCTURAL_GROUP" for role in roles)
        ):
            derived_reasons.append(
                "MAPPED_ROLE_CELL_IS_BLANK_UNKNOWN:" + str(row.get("logical_row_id"))
            )
    sorted_reasons = sorted(set(derived_reasons))
    closure_material = {
        "adapter_identity": canonical_clone_v1(policy["projection_adapter_identity"]),
        "adapter_projection_receipt": canonical_clone_v1(adapter_projection_receipt),
        "inventory_adapter_identity": canonical_clone_v1(
            policy["projection_inventory_adapter_identity"]
        ),
        "logical_rows": rows,
        "projection_kind": projection_kind,
        "reasons": sorted_reasons,
        "source_bindings": bindings,
    }
    closure_sha256 = canonical_json_sha256_v1(closure_material)
    identity_material = {
        "family_id": policy["family_id"],
        "page_json_version_id": page_record["page_json_version_id"],
        "projection_closure_sha256": closure_sha256,
        "section_id": section_id,
        "table_id": table_id,
    }
    numeric_roles = sorted(
        {
            role
            for row in rows
            for role in row.get("label_match_modes", {})
            if any(cell.get("money") is not None for cell in row.get("cells", []))
        }
    )
    return {
        "adapter_format_version": adapter_format_version,
        "adapter_identity": canonical_clone_v1(policy["projection_adapter_identity"]),
        "adapter_projection_receipt": canonical_clone_v1(adapter_projection_receipt),
        "binding_model": "GENERAL_EXACT_SOURCE_BINDINGS",
        "candidate_id": "drfcv1:fragment:" + canonical_json_sha256_v1(identity_material),
        "continuation": table.get("continuation"),
        "document_id": page_record["document_id"],
        "format_version": FRAGMENT_FORMAT_VERSION,
        "inventory_adapter_identity": canonical_clone_v1(
            policy["projection_inventory_adapter_identity"]
        ),
        "local_branch_evidence": branch_evidence,
        "local_owner_evidence": owner_evidence,
        "logical_rows": rows,
        "numeric_roles": numeric_roles,
        "page_json_sha256": canonical_json_sha256_v1(page_record["page_json"]),
        "page_json_version_id": page_record["page_json_version_id"],
        "physical_page": page_record["physical_page"],
        "projection_closure": closure_material,
        "projection_closure_sha256": closure_sha256,
        "projection_kind": projection_kind,
        "reasons": sorted_reasons,
        "section_id": section_id,
        "selected_frontier_ordinal": page_record["selected_frontier_ordinal"],
        "source_bindings": bindings,
        "source_logical_name": page_record["source_logical_name"],
        "source_sha256": page_record["source_sha256"],
        "source_table_sha256": canonical_json_sha256_v1(table),
        "status": "ELIGIBLE" if not sorted_reasons else "UNRESOLVED",
        "table_id": table_id,
    }


def _validate_row_column_lane_fragment_candidate(
    candidate: Any,
    *,
    page_record: Mapping[str, Any],
    document_period_axis: Mapping[str, Any],
    policy: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    required = {
        "adapter_format_version",
        "adapter_identity",
        "anonymous_rows",
        "binding_model",
        "candidate_id",
        "continuation",
        "document_id",
        "format_version",
        "inventory_adapter_identity",
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
        or candidate["adapter_format_version"]
        != policy["projection_adapter_identity"]["adapter_format_version"]
        or candidate["adapter_identity"] != policy["projection_adapter_identity"]
        or candidate["inventory_adapter_identity"]
        != policy["projection_inventory_adapter_identity"]
        or candidate["binding_model"] != "ROW_COLUMN_LANE_REFERENCE"
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
        "adapter_identity",
        "anonymous_rows",
        "control_column_ids",
        "filtered_non_money_column_ids",
        "inventory_adapter_identity",
        "mapping_column_axis",
        "projection_kind",
        "reasons",
        "role_rows",
    }
    if (
        type(closure) is not dict
        or set(closure) != closure_fields
        or closure["adapter_identity"] != candidate["adapter_identity"]
        or closure["inventory_adapter_identity"] != candidate["inventory_adapter_identity"]
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
    expected_period_axis = [tuple(value) for value in document_period_axis["period_signatures"]]
    expected_periods = set(expected_period_axis)
    mapping_by_column_id = {
        record["column_id"]: record for record in candidate["mapping_column_axis"]
    }
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
            mapping_record = mapping_by_column_id.get(cell["column_id"])
            if (
                mapping_record is None
                or cell["period_signature"] != mapping_record["period_signature"]
                or cell["unit_signature"] != mapping_record["unit_signature"]
                or cell["metric_signature"] != "UNQUALIFIED_BALANCE_AMOUNT"
            ):
                raise _error("normalized document-region source axis binding drifted")
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


def _exact_source_binding_records(
    source_bindings: Any,
    *,
    section: Mapping[str, Any],
    table: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Dereference a layout-neutral binding axis against canonical JSON."""

    columns = table.get("columns")
    rows = table.get("rows")
    if type(source_bindings) is not list or type(columns) is not list or type(rows) is not list:
        raise _error("normalized document-region general source binding axis is invalid")
    records: dict[str, dict[str, Any]] = {}
    locators = set()
    for binding in source_bindings:
        if (
            type(binding) is not dict
            or type(binding.get("binding_id")) is not str
            or re.fullmatch(r"b[1-9][0-9]*", binding["binding_id"]) is None
            or binding["binding_id"] in records
        ):
            raise _error("normalized document-region source binding identity is invalid")
        kind = binding.get("binding_kind")
        locator: tuple[Any, ...]
        if kind == "ROW":
            expected_fields = {
                "binding_id",
                "binding_kind",
                "hierarchy_path_exact",
                "label_exact",
                "row_id",
                "row_kind",
            }
            row_index = _node_index(binding.get("row_id"), "r", len(rows))
            source_row = rows[row_index]
            if (
                set(binding) != expected_fields
                or binding.get("label_exact") != source_row.get("label_exact")
                or binding.get("hierarchy_path_exact") != source_row.get("hierarchy_path_exact")
                or binding.get("row_kind") != source_row.get("row_kind")
            ):
                raise _error("normalized document-region ROW binding drifted")
            locator = (kind, binding["row_id"])
        elif kind == "COLUMN":
            expected_fields = {
                "binding_id",
                "binding_kind",
                "column_id",
                "header_path_exact",
                "value_kind",
            }
            column_index = _node_index(binding.get("column_id"), "c", len(columns))
            source_column = columns[column_index]
            if (
                set(binding) != expected_fields
                or binding.get("header_path_exact") != source_column.get("header_path_exact")
                or binding.get("value_kind") != source_column.get("value_kind")
            ):
                raise _error("normalized document-region COLUMN binding drifted")
            locator = (kind, binding["column_id"])
        elif kind == "VALUE_CELL":
            expected_fields = {
                "binding_id",
                "binding_kind",
                "column_id",
                "row_id",
                "source_text",
            }
            row_index = _node_index(binding.get("row_id"), "r", len(rows))
            column_index = _node_index(binding.get("column_id"), "c", len(columns))
            source_values = rows[row_index].get("values_exact")
            if (
                set(binding) != expected_fields
                or type(source_values) is not list
                or len(source_values) != len(columns)
                or binding.get("source_text") != source_values[column_index]
            ):
                raise _error("normalized document-region VALUE_CELL binding drifted")
            locator = (kind, binding["row_id"], binding["column_id"])
        elif kind == "ROW_BLOCK":
            expected_fields = {"binding_id", "binding_kind", "row_ids"}
            row_ids = binding.get("row_ids")
            if type(row_ids) is not list or not row_ids or len(set(row_ids)) != len(row_ids):
                raise _error("normalized document-region ROW_BLOCK binding is invalid")
            indices = [_node_index(row_id, "r", len(rows)) for row_id in row_ids]
            if set(binding) != expected_fields or indices != list(
                range(indices[0], indices[0] + len(indices))
            ):
                raise _error("normalized document-region ROW_BLOCK binding drifted")
            locator = (kind, *row_ids)
        elif kind == "TABLE_UNIT":
            expected_fields = {"binding_id", "binding_kind", "unit_exact"}
            if set(binding) != expected_fields or binding.get("unit_exact") != table.get(
                "unit_exact"
            ):
                raise _error("normalized document-region TABLE_UNIT binding drifted")
            locator = (kind,)
        elif kind == "TABLE_TITLE":
            expected_fields = {"binding_id", "binding_kind", "title_exact"}
            if set(binding) != expected_fields or binding.get("title_exact") != table.get(
                "title_exact"
            ):
                raise _error("normalized document-region TABLE_TITLE binding drifted")
            locator = (kind,)
        elif kind == "SECTION_TITLE":
            expected_fields = {"binding_id", "binding_kind", "title_exact"}
            if set(binding) != expected_fields or binding.get("title_exact") != section.get(
                "title_exact"
            ):
                raise _error("normalized document-region SECTION_TITLE binding drifted")
            locator = (kind,)
        elif kind == "SECTION_NARRATIVE":
            expected_fields = {
                "binding_id",
                "binding_kind",
                "narrative_exact",
                "narrative_ordinal",
            }
            narratives = section.get("narratives_exact")
            ordinal = binding.get("narrative_ordinal")
            if (
                set(binding) != expected_fields
                or type(narratives) is not list
                or type(ordinal) is not int
                or not 1 <= ordinal <= len(narratives)
                or binding.get("narrative_exact") != narratives[ordinal - 1]
            ):
                raise _error("normalized document-region SECTION_NARRATIVE binding drifted")
            locator = (kind, ordinal)
        else:
            raise _error("normalized document-region source binding kind is invalid")
        if locator in locators:
            raise _error("normalized document-region source locator is bound more than once")
        locators.add(locator)
        records[binding["binding_id"]] = canonical_clone_v1(binding)
    if list(records) != [f"b{ordinal}" for ordinal in range(1, len(records) + 1)]:
        raise _error("normalized document-region source binding order is invalid")
    return records


def _binding_exact_strings(
    binding: Mapping[str, Any], *, rows: Sequence[Mapping[str, Any]]
) -> list[str]:
    kind = binding["binding_kind"]
    values: list[Any]
    if kind == "ROW":
        values = [binding.get("label_exact"), *binding.get("hierarchy_path_exact", [])]
    elif kind == "COLUMN":
        values = list(binding.get("header_path_exact", []))
    elif kind == "ROW_BLOCK":
        values = [
            value
            for row_id in binding["row_ids"]
            for value in [
                rows[_node_index(row_id, "r", len(rows))].get("label_exact"),
                *rows[_node_index(row_id, "r", len(rows))].get("hierarchy_path_exact", []),
            ]
        ]
    elif kind == "TABLE_UNIT":
        values = [binding.get("unit_exact")]
    elif kind in {"TABLE_TITLE", "SECTION_TITLE"}:
        values = [binding.get("title_exact")]
    elif kind == "SECTION_NARRATIVE":
        values = [binding.get("narrative_exact")]
    else:
        values = []
    return [value for value in values if type(value) is str and value]


def _general_role_matches(
    binding: Mapping[str, Any],
    *,
    rows: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, str]:
    enabled = (
        compiled_specs["evaluation"].get("format_version") == "ACCOUNTING_FAMILY_EVALUATION_SPEC_V8"
    )
    candidates = []
    if binding["binding_kind"] == "ROW":
        candidates.append(rows[_node_index(binding["row_id"], "r", len(rows))])
    else:
        for value in _binding_exact_strings(binding, rows=rows):
            candidates.append(
                {
                    "hierarchy_path_exact": [value],
                    "label_exact": value,
                    "row_kind": "ITEM",
                }
            )
    matches: dict[str, str] = {}
    for candidate in candidates:
        try:
            modes = _row_role_match_modes(
                candidate,
                topology=compiled_specs["topology"],
                aliases_by_role=compiled_specs["aliases_by_role"],
                enable_declared_equivalences=enabled,
            )
        except ValueError as exc:
            raise _error("normalized document-region role source is ambiguous") from exc
        for role, mode in modes.items():
            if role in matches and matches[role] != mode:
                raise _error("normalized document-region role source mode is ambiguous")
            matches[role] = mode
    return matches


def _binding_population_context(
    binding: Mapping[str, Any],
    *,
    rows: Sequence[Mapping[str, Any]],
    claimed_roles: set[str],
    logical_label: Any,
    compiled_specs: Mapping[str, Any],
) -> list[str] | None:
    if binding["binding_kind"] == "ROW":
        source_row = rows[_node_index(binding["row_id"], "r", len(rows))]
        path = source_row.get("hierarchy_path_exact")
        if type(path) is not list:
            return []
        context = [value for value in path if type(value) is str and value]
        if context and _normalized(context[-1]) == _normalized(source_row.get("label_exact")):
            context.pop()
        return context
    if binding["binding_kind"] != "COLUMN":
        return None
    header = binding.get("header_path_exact")
    if type(header) is not list:
        return []
    for index, value in enumerate(header):
        if type(value) is not str:
            continue
        matches = _general_role_matches(
            {
                "binding_id": binding["binding_id"],
                "binding_kind": "COLUMN",
                "column_id": binding["column_id"],
                "header_path_exact": [value],
                "value_kind": binding["value_kind"],
            },
            rows=rows,
            compiled_specs=compiled_specs,
        )
        if claimed_roles.intersection(matches) or (
            not claimed_roles and _normalized(value) == _normalized(logical_label)
        ):
            return [item for item in header[:index] if type(item) is str and item]
    return None


def _validate_binding_reference_ids(
    value: Any,
    *,
    bindings: Mapping[str, Mapping[str, Any]],
    field: str,
    allow_empty: bool,
) -> list[str]:
    if (
        type(value) is not list
        or (not value and not allow_empty)
        or len(set(value)) != len(value)
        or any(type(binding_id) is not str or binding_id not in bindings for binding_id in value)
    ):
        raise _error(f"normalized document-region {field} binding references are invalid")
    return value


def _validate_general_exact_source_binding_candidate(
    candidate: Any,
    *,
    page_record: Mapping[str, Any],
    document_period_axis: Mapping[str, Any],
    policy: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    required = {
        "adapter_format_version",
        "adapter_identity",
        "adapter_projection_receipt",
        "binding_model",
        "candidate_id",
        "continuation",
        "document_id",
        "format_version",
        "inventory_adapter_identity",
        "local_branch_evidence",
        "local_owner_evidence",
        "logical_rows",
        "numeric_roles",
        "page_json_sha256",
        "page_json_version_id",
        "physical_page",
        "projection_closure",
        "projection_closure_sha256",
        "projection_kind",
        "reasons",
        "section_id",
        "selected_frontier_ordinal",
        "source_bindings",
        "source_logical_name",
        "source_sha256",
        "source_table_sha256",
        "status",
        "table_id",
    }
    if type(candidate) is not dict or set(candidate) != required:
        raise _error("normalized document-region general fragment contract drifted")
    section, table, section_ordinal, table_ordinal = _source_nodes(
        page_record["page_json"],
        section_id=candidate["section_id"],
        table_id=candidate["table_id"],
    )
    if (
        candidate["binding_model"] != "GENERAL_EXACT_SOURCE_BINDINGS"
        or candidate["adapter_identity"] != policy["projection_adapter_identity"]
        or candidate["inventory_adapter_identity"]
        != policy["projection_inventory_adapter_identity"]
        or candidate["adapter_format_version"]
        != policy["projection_adapter_identity"]["adapter_format_version"]
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
        raise _error("normalized document-region general fragment source binding drifted")
    closure = candidate["projection_closure"]
    closure_fields = {
        "adapter_identity",
        "adapter_projection_receipt",
        "logical_rows",
        "inventory_adapter_identity",
        "projection_kind",
        "reasons",
        "source_bindings",
    }
    if (
        type(closure) is not dict
        or set(closure) != closure_fields
        or closure["adapter_identity"] != candidate["adapter_identity"]
        or closure["inventory_adapter_identity"] != candidate["inventory_adapter_identity"]
        or closure["adapter_projection_receipt"] != candidate["adapter_projection_receipt"]
        or closure["logical_rows"] != candidate["logical_rows"]
        or closure["projection_kind"] != candidate["projection_kind"]
        or closure["reasons"] != candidate["reasons"]
        or closure["source_bindings"] != candidate["source_bindings"]
    ):
        raise _error("normalized document-region general projection closure drifted")
    identity_material = {
        "family_id": policy["family_id"],
        "page_json_version_id": candidate["page_json_version_id"],
        "projection_closure_sha256": candidate["projection_closure_sha256"],
        "section_id": candidate["section_id"],
        "table_id": candidate["table_id"],
    }
    if candidate["candidate_id"] != "drfcv1:fragment:" + canonical_json_sha256_v1(
        identity_material
    ):
        raise _error("normalized document-region general fragment identity drifted")
    surfaces = _table_surfaces(
        page_record=page_record,
        section_id=candidate["section_id"],
        table_id=candidate["table_id"],
    )
    expected_owner = []
    expected_branch = []
    for surface in surfaces:
        owner_matches = _contains_alias(surface["source_exact"], policy["owner_aliases"])
        branch_matches = _contains_alias(surface["source_exact"], policy["branch_aliases"])
        if owner_matches:
            expected_owner.append({**canonical_clone_v1(surface), "matched_aliases": owner_matches})
        if branch_matches:
            expected_branch.append(
                {**canonical_clone_v1(surface), "matched_aliases": branch_matches}
            )
    if (
        candidate["local_owner_evidence"] != expected_owner
        or candidate["local_branch_evidence"] != expected_branch
        or candidate["continuation"] != table.get("continuation")
    ):
        raise _error("normalized document-region general structural evidence drifted")
    source_rows = table.get("rows")
    if type(source_rows) is not list:
        raise _error("normalized document-region general source row axis is invalid")
    bindings = _exact_source_binding_records(
        candidate["source_bindings"], section=section, table=table
    )
    expected_period_axis = [tuple(value) for value in document_period_axis["period_signatures"]]
    expected_periods = set(expected_period_axis)
    known_roles = {compiled_specs["topology"]["parent"]["role"]} | {
        child["role"] for child in compiled_specs["topology"]["children"]
    }
    role_kinds = {
        child["role"]: child["role_kind"] for child in compiled_specs["topology"]["children"]
    }
    referenced: set[str] = set()
    value_binding_use: dict[str, int] = defaultdict(int)
    logical_ids = set()
    logical_cell_ids = set()
    expected_numeric_roles = set()
    expected_blank_reasons = set()
    logical_rows = candidate["logical_rows"]
    prior_source_position: list[int] | None = None
    if type(logical_rows) is not list:
        raise _error("normalized document-region logical row axis is invalid")
    for row in logical_rows:
        row_fields = {
            "cells",
            "hierarchy_path_exact",
            "label_exact",
            "label_match_modes",
            "logical_row_id",
            "population_context_exact",
            "population_source_binding_ids",
            "role_source_binding_ids",
            "row_kind",
            "row_kind_derivation",
            "row_source_binding_ids",
            "source_position",
        }
        if (
            type(row) is not dict
            or set(row) != row_fields
            or type(row.get("logical_row_id")) is not str
            or re.fullmatch(r"lr[1-9][0-9]*", row["logical_row_id"]) is None
            or row["logical_row_id"] in logical_ids
            or type(row.get("label_match_modes")) is not dict
            or any(role not in known_roles for role in row["label_match_modes"])
            or type(row.get("hierarchy_path_exact")) is not list
            or type(row.get("population_context_exact")) is not list
            or any(type(value) is not str or not value for value in row["population_context_exact"])
            or type(row.get("source_position")) is not list
            or len(row["source_position"]) != 5
            or row["source_position"][:3]
            != [page_record["selected_frontier_ordinal"], section_ordinal, table_ordinal]
            or any(type(value) is not int or value < 1 for value in row["source_position"][3:])
            or type(row.get("cells")) is not list
            or not row["cells"]
        ):
            raise _error("normalized document-region logical row is invalid")
        logical_ids.add(row["logical_row_id"])
        if row["logical_row_id"] != f"lr{len(logical_ids)}":
            raise _error("normalized document-region logical row order is invalid")
        row_refs = _validate_binding_reference_ids(
            row["row_source_binding_ids"],
            bindings=bindings,
            field="row-source",
            allow_empty=False,
        )
        role_refs = _validate_binding_reference_ids(
            row["role_source_binding_ids"],
            bindings=bindings,
            field="role-source",
            allow_empty=not bool(row["label_match_modes"]),
        )
        population_refs = _validate_binding_reference_ids(
            row["population_source_binding_ids"],
            bindings=bindings,
            field="population-source",
            allow_empty=not bool(row["population_context_exact"]),
        )
        referenced.update([*row_refs, *role_refs, *population_refs])
        if any(
            bindings[binding_id]["binding_kind"] == "VALUE_CELL"
            for binding_id in [*row_refs, *role_refs, *population_refs]
        ):
            raise _error("VALUE_CELL binding is outside value_source_binding_ids")
        row_strings = [
            value
            for binding_id in row_refs
            for value in _binding_exact_strings(bindings[binding_id], rows=source_rows)
        ]
        if row["label_exact"] is not None and row["label_exact"] not in row_strings:
            raise _error("normalized document-region logical label is synthetic-only")
        if any(value not in row_strings for value in row["hierarchy_path_exact"] if value):
            raise _error("normalized document-region logical hierarchy is synthetic-only")
        population_strings = [
            value
            for binding_id in population_refs
            for value in _binding_exact_strings(bindings[binding_id], rows=source_rows)
        ]
        if any(value not in population_strings for value in row["population_context_exact"]):
            raise _error("normalized document-region population context is synthetic-only")
        derived_contexts = [
            context
            for binding_id in row_refs
            if (
                context := _binding_population_context(
                    bindings[binding_id],
                    rows=source_rows,
                    claimed_roles=set(row["label_match_modes"]),
                    logical_label=row["label_exact"],
                    compiled_specs=compiled_specs,
                )
            )
            is not None
        ]
        normalized_declared_context = [
            _normalized(value) for value in row["population_context_exact"]
        ]
        if any(
            [_normalized(value) for value in context] != normalized_declared_context
            for context in derived_contexts
        ):
            raise _error("normalized document-region population context drifted")
        expected_logical_path = [*row["population_context_exact"]]
        if row["label_exact"] is not None:
            expected_logical_path.append(row["label_exact"])
        if [_normalized(value) for value in row["hierarchy_path_exact"] if value] != [
            _normalized(value) for value in expected_logical_path
        ]:
            raise _error("normalized document-region logical hierarchy path drifted")
        matched_roles: dict[str, str] = {}
        for binding_id in role_refs:
            for role, mode in _general_role_matches(
                bindings[binding_id], rows=source_rows, compiled_specs=compiled_specs
            ).items():
                matched_roles.setdefault(role, mode)
        if any(matched_roles.get(role) != mode for role, mode in row["label_match_modes"].items()):
            raise _error("normalized document-region role projection is not source-authenticated")
        row_kind_derivation = row.get("row_kind_derivation")
        if row_kind_derivation == "EXACT_SOURCE_ROW_KIND":
            source_row_kinds = {
                bindings[binding_id]["row_kind"]
                for binding_id in row_refs
                if bindings[binding_id]["binding_kind"] == "ROW"
            }
            if (
                not source_row_kinds
                or source_row_kinds != {row.get("row_kind")}
                or any(bindings[binding_id]["binding_kind"] != "ROW" for binding_id in row_refs)
            ):
                raise _error("normalized document-region source row_kind drifted")
        elif row_kind_derivation == "DECLARED_ROLE_HEADER_ITEM":
            if (
                row.get("row_kind") != "ITEM"
                or not row["label_match_modes"]
                or any(bindings[binding_id]["binding_kind"] != "COLUMN" for binding_id in row_refs)
            ):
                raise _error("normalized document-region role-header row_kind drifted")
        elif row_kind_derivation == "DECLARED_TOTAL_HEADER":
            if (
                row.get("row_kind") != "TOTAL"
                or row["label_match_modes"]
                or _normalized(row.get("label_exact")) not in _DECLARED_TOTAL_HEADER_ALIASES
                or any(bindings[binding_id]["binding_kind"] != "COLUMN" for binding_id in row_refs)
            ):
                raise _error("normalized document-region total-header row_kind drifted")
        else:
            raise _error("normalized document-region row_kind derivation is invalid")
        row_has_blank = False
        row_value_refs: list[str] = []
        row_period_ordinals: list[int] = []
        for cell in row["cells"]:
            cell_fields = {
                "layout_relation",
                "logical_cell_id",
                "metric_signature",
                "metric_source_binding_ids",
                "money",
                "period_signature",
                "period_source_binding_ids",
                "source_text",
                "unit_signature",
                "unit_source_binding_ids",
                "value_source_binding_ids",
            }
            if (
                type(cell) is not dict
                or set(cell) != cell_fields
                or type(cell.get("logical_cell_id")) is not str
                or not cell["logical_cell_id"]
                or cell["logical_cell_id"] in logical_cell_ids
                or type(cell.get("metric_signature")) is not str
                or not cell["metric_signature"]
                or type(cell.get("period_signature")) is not list
                or len(cell["period_signature"]) != 2
                or tuple(cell["period_signature"]) not in expected_periods
                or cell.get("unit_signature") not in policy["unit_aliases"]
            ):
                raise _error("normalized document-region logical cell is invalid")
            row_period_ordinals.append(expected_period_axis.index(tuple(cell["period_signature"])))
            logical_cell_ids.add(cell["logical_cell_id"])
            value_refs = _validate_binding_reference_ids(
                cell["value_source_binding_ids"],
                bindings=bindings,
                field="value-source",
                allow_empty=False,
            )
            period_refs = _validate_binding_reference_ids(
                cell["period_source_binding_ids"],
                bindings=bindings,
                field="period-source",
                allow_empty=False,
            )
            unit_refs = _validate_binding_reference_ids(
                cell["unit_source_binding_ids"],
                bindings=bindings,
                field="unit-source",
                allow_empty=False,
            )
            metric_refs = _validate_binding_reference_ids(
                cell["metric_source_binding_ids"],
                bindings=bindings,
                field="metric-source",
                allow_empty=False,
            )
            if any(
                bindings[binding_id]["binding_kind"] != "VALUE_CELL" for binding_id in value_refs
            ):
                raise _error("normalized document-region value source is not a cell")
            if any(
                bindings[binding_id]["binding_kind"] == "VALUE_CELL"
                for binding_id in [*period_refs, *unit_refs, *metric_refs]
            ):
                raise _error("VALUE_CELL binding is outside value_source_binding_ids")
            for binding_id in value_refs:
                value_binding_use[binding_id] += 1
                row_value_refs.append(binding_id)
            referenced.update([*value_refs, *period_refs, *unit_refs, *metric_refs])
            period_strings = [
                value
                for binding_id in period_refs
                for value in _binding_exact_strings(bindings[binding_id], rows=source_rows)
            ]
            if tuple(cell["period_signature"]) not in {
                signature
                for value in period_strings
                if (signature := _period_signature(value)) is not None
            }:
                raise _error("normalized document-region period is not source-authenticated")
            unit_strings = [
                value
                for binding_id in unit_refs
                for value in _binding_exact_strings(bindings[binding_id], rows=source_rows)
            ]
            if not any(_contains_alias(value, [cell["unit_signature"]]) for value in unit_strings):
                raise _error("normalized document-region unit is not source-authenticated")
            metric_rule = policy["metric_projection_rules"].get(cell["metric_signature"])
            metric_columns = [
                bindings[binding_id]
                for binding_id in metric_refs
                if bindings[binding_id]["binding_kind"] == "COLUMN"
            ]
            if (
                metric_rule is None
                or not metric_columns
                or any(
                    column["value_kind"] != metric_rule["source_value_kind"]
                    for column in metric_columns
                )
            ):
                raise _error("normalized document-region metric is not source-authenticated")
            if metric_rule["rule"].endswith("HEADER_ALIAS") and not any(
                _contains_alias(value, metric_rule["header_aliases"])
                for column in metric_columns
                for value in column["header_path_exact"]
            ):
                raise _error("normalized document-region metric header rule failed")
            if metric_rule["rule"].endswith("UNQUALIFIED"):
                other_aliases = [
                    alias
                    for signature, rule in policy["metric_projection_rules"].items()
                    if signature != cell["metric_signature"]
                    for alias in rule["header_aliases"]
                ]
                if any(
                    _contains_alias(value, other_aliases)
                    for column in metric_columns
                    for value in column["header_path_exact"]
                ):
                    raise _error("normalized document-region unqualified metric is qualified")
            relation = cell["layout_relation"]
            if type(relation) is not dict:
                raise _error("normalized document-region layout relation is invalid")
            if relation.get("relation_kind") == "STACKED_PERIOD_ROW_BLOCK":
                relation_fields = {
                    "metric_axis_binding_id",
                    "period_axis_binding_id",
                    "period_block_binding_id",
                    "relation_kind",
                    "role_axis_binding_id",
                    "unit_axis_binding_id",
                }
                if set(relation) != relation_fields:
                    raise _error("normalized document-region stacked layout relation drifted")
                period_axis = bindings.get(relation["period_axis_binding_id"])
                period_block = bindings.get(relation["period_block_binding_id"])
                role_axis = bindings.get(relation["role_axis_binding_id"])
                metric_axis = bindings.get(relation["metric_axis_binding_id"])
                unit_axis = bindings.get(relation["unit_axis_binding_id"])
                if (
                    period_axis is None
                    or period_axis["binding_kind"] != "ROW"
                    or period_block is None
                    or period_block["binding_kind"] != "ROW_BLOCK"
                    or role_axis is None
                    or role_axis["binding_kind"] != "ROW"
                    or metric_axis is None
                    or metric_axis["binding_kind"] != "COLUMN"
                    or unit_axis is None
                    or unit_axis["binding_kind"] != "TABLE_UNIT"
                    or relation["period_axis_binding_id"] not in period_refs
                    or relation["period_block_binding_id"] not in period_refs
                    or relation["role_axis_binding_id"] not in row_refs
                    or relation["metric_axis_binding_id"] not in metric_refs
                    or relation["unit_axis_binding_id"] not in unit_refs
                    or period_axis["row_id"] not in period_block["row_ids"]
                    or role_axis["row_id"] not in period_block["row_ids"]
                    or any(
                        bindings[binding_id]["row_id"] != role_axis["row_id"]
                        or bindings[binding_id]["column_id"] != metric_axis["column_id"]
                        for binding_id in value_refs
                    )
                ):
                    raise _error("normalized document-region stacked coordinate relation failed")
            elif relation.get("relation_kind") == "TRANSPOSED_PERIOD_ROW_ROLE_COLUMN":
                relation_fields = {
                    "metric_axis_binding_id",
                    "period_axis_binding_id",
                    "relation_kind",
                    "role_axis_binding_id",
                    "unit_axis_binding_id",
                }
                if set(relation) != relation_fields:
                    raise _error("normalized document-region transposed layout relation drifted")
                period_axis = bindings.get(relation["period_axis_binding_id"])
                role_axis = bindings.get(relation["role_axis_binding_id"])
                metric_axis = bindings.get(relation["metric_axis_binding_id"])
                unit_axis = bindings.get(relation["unit_axis_binding_id"])
                if (
                    period_axis is None
                    or period_axis["binding_kind"] != "ROW"
                    or role_axis is None
                    or role_axis["binding_kind"] != "COLUMN"
                    or metric_axis is None
                    or metric_axis["binding_kind"] != "COLUMN"
                    or unit_axis is None
                    or unit_axis["binding_kind"] != "TABLE_UNIT"
                    or relation["period_axis_binding_id"] not in period_refs
                    or relation["role_axis_binding_id"] not in row_refs
                    or relation["metric_axis_binding_id"] not in metric_refs
                    or relation["unit_axis_binding_id"] not in unit_refs
                    or any(
                        bindings[binding_id]["row_id"] != period_axis["row_id"]
                        or bindings[binding_id]["column_id"] != role_axis["column_id"]
                        or bindings[binding_id]["column_id"] != metric_axis["column_id"]
                        for binding_id in value_refs
                    )
                ):
                    raise _error("normalized document-region transposed coordinate relation failed")
            else:
                raise _error("normalized document-region layout relation kind is invalid")
            raw_values = [bindings[binding_id]["source_text"] for binding_id in value_refs]
            if all(value is None for value in raw_values):
                row_has_blank = True
                if cell["money"] is not None or cell["source_text"] is not None:
                    raise _error("blank document-region source binding became zero")
            elif any(value is None for value in raw_values):
                raise _error("normalized document-region aggregate mixes blank and numeric cells")
            else:
                try:
                    money_values = [_money(value) for value in raw_values]
                except ValueError as exc:
                    raise _error("normalized document-region source money is invalid") from exc
                if len(money_values) == 1:
                    expected_money = money_values[0]
                    expected_text = raw_values[0]
                else:
                    expected_money = {
                        "coefficient": sum(value["coefficient"] for value in money_values),
                        "source_text": None,
                        "state": "SUM_EXACT_SOURCE_CELLS",
                    }
                    expected_text = None
                if cell["money"] != expected_money or cell["source_text"] != expected_text:
                    raise _error("normalized document-region logical money drifted")
        if row_period_ordinals != sorted(set(row_period_ordinals)):
            raise _error("normalized document-region logical period order drifted")
        positional_bindings = [bindings[binding_id] for binding_id in [*row_refs, *row_value_refs]]
        row_ordinals = []
        column_ordinals = []
        for binding in positional_bindings:
            if binding["binding_kind"] in {"ROW", "VALUE_CELL"}:
                row_ordinals.append(int(binding["row_id"][1:]))
            elif binding["binding_kind"] == "ROW_BLOCK":
                row_ordinals.extend(int(row_id[1:]) for row_id in binding["row_ids"])
            if binding["binding_kind"] in {"COLUMN", "VALUE_CELL"}:
                column_ordinals.append(int(binding["column_id"][1:]))
        expected_position = [
            page_record["selected_frontier_ordinal"],
            section_ordinal,
            table_ordinal,
            min(row_ordinals, default=1),
            min(column_ordinals, default=1),
        ]
        if row["source_position"] != expected_position:
            raise _error("normalized document-region logical source position drifted")
        if prior_source_position is not None and row["source_position"] <= prior_source_position:
            raise _error("normalized document-region logical source order drifted")
        prior_source_position = row["source_position"]
        if row["label_match_modes"] and any(
            role_kinds.get(role) != "STRUCTURAL_GROUP" for role in row["label_match_modes"]
        ):
            if row_has_blank:
                expected_blank_reasons.add(
                    "MAPPED_ROLE_CELL_IS_BLANK_UNKNOWN:" + row["logical_row_id"]
                )
            if any(cell["money"] is not None for cell in row["cells"]):
                expected_numeric_roles.update(row["label_match_modes"])
    all_value_binding_ids = {
        binding_id
        for binding_id, binding in bindings.items()
        if binding["binding_kind"] == "VALUE_CELL"
    }
    if set(value_binding_use) != all_value_binding_ids or any(
        count != 1 for count in value_binding_use.values()
    ):
        raise _error("normalized document-region source cell is projected more than once")
    if referenced != set(bindings):
        raise _error("normalized document-region source bindings are not exhaustive")
    if not expected_blank_reasons <= set(candidate["reasons"]):
        raise _error("normalized document-region blank-unknown disposition drifted")
    if candidate["numeric_roles"] != sorted(expected_numeric_roles):
        raise _error("normalized document-region general numeric role axis drifted")
    return canonical_clone_v1(candidate)


def _validate_normalized_fragment_candidate(
    candidate: Any,
    *,
    page_record: Mapping[str, Any],
    document_period_axis: Mapping[str, Any],
    policy: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    if type(candidate) is not dict:
        raise _error("normalized document-region fragment is invalid")
    if candidate.get("binding_model") == "ROW_COLUMN_LANE_REFERENCE":
        return _validate_row_column_lane_fragment_candidate(
            candidate,
            page_record=page_record,
            document_period_axis=document_period_axis,
            policy=policy,
            compiled_specs=compiled_specs,
        )
    if candidate.get("binding_model") == "GENERAL_EXACT_SOURCE_BINDINGS":
        return _validate_general_exact_source_binding_candidate(
            candidate,
            page_record=page_record,
            document_period_axis=document_period_axis,
            policy=policy,
            compiled_specs=compiled_specs,
        )
    raise _error("normalized document-region fragment binding model is invalid")


def _component_axis(fragments: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "adapter_format_version": fragment["adapter_format_version"],
            "adapter_identity": canonical_clone_v1(fragment["adapter_identity"]),
            "binding_model": fragment["binding_model"],
            "candidate_id": fragment["candidate_id"],
            "page_json_sha256": fragment["page_json_sha256"],
            "page_json_version_id": fragment["page_json_version_id"],
            "physical_page": fragment["physical_page"],
            "inventory_adapter_identity": canonical_clone_v1(
                fragment["inventory_adapter_identity"]
            ),
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
        "compiled_specs_sha256": policy["compiled_specs_sha256"],
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
            "compiled_specs_sha256": policy["compiled_specs_sha256"],
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
    declared = row.get("population_context_exact")
    if type(declared) is list:
        return [_normalized(value) for value in declared if _normalized(value)]
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
    evidence = {
        "candidate_id": fragment["candidate_id"],
        "column_id": cell.get("column_id"),
        "logical_cell_id": cell.get("logical_cell_id"),
        "logical_row_id": row.get("logical_row_id"),
        "metric_signature": cell["metric_signature"],
        "money": canonical_clone_v1(cell["money"]),
        "page_json_version_id": fragment["page_json_version_id"],
        "period_signature": canonical_clone_v1(cell["period_signature"]),
        "physical_page": fragment["physical_page"],
        "row_id": row.get("row_id"),
        "section_id": fragment["section_id"],
        "source_text": cell["source_text"],
        "table_id": fragment["table_id"],
        "unit_signature": cell["unit_signature"],
    }
    if fragment["binding_model"] == "GENERAL_EXACT_SOURCE_BINDINGS":
        binding_ids = sorted(
            {
                binding_id
                for field in (
                    "metric_source_binding_ids",
                    "period_source_binding_ids",
                    "unit_source_binding_ids",
                    "value_source_binding_ids",
                )
                for binding_id in cell[field]
            }
        )
        binding_by_id = {binding["binding_id"]: binding for binding in fragment["source_bindings"]}
        evidence["exact_source_bindings"] = [
            canonical_clone_v1(binding_by_id[binding_id]) for binding_id in binding_ids
        ]
    return evidence


def _fragment_logical_rows(fragment: Mapping[str, Any]) -> list[dict[str, Any]]:
    if fragment["binding_model"] == "GENERAL_EXACT_SOURCE_BINDINGS":
        return fragment["logical_rows"]
    return [*fragment["role_rows"], *fragment["anonymous_rows"]]


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
        for row in _fragment_logical_rows(fragment):
            roles = tuple(sorted(row["label_match_modes"]))
            if all(cell["money"] is None for cell in row["cells"]):
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
                    "row_id": row.get("row_id"),
                    "logical_row_id": row.get("logical_row_id"),
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
            numeric |= any(source["money"] is not None for source in sources)
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
            if not sources:
                values.append(None)
            elif sources[0]["source_text"] is not None:
                values.append(sources[0]["source_text"])
            elif sources[0]["money"] is not None:
                values.append(str(sources[0]["money"]["coefficient"]))
            else:
                values.append(None)
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
    _assert_callable_matches_adapter_identity(
        projection_adapter,
        compiled_policy["projection_adapter_identity"],
        field="projection",
    )
    _assert_callable_matches_adapter_identity(
        projection_inventory_adapter,
        compiled_policy["projection_inventory_adapter_identity"],
        field="projection-inventory",
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
            or request.get("composer_policy_sha256") != compiled_policy["policy_sha256"]
            or type(request.get("page_json_version_id")) is not str
            or request["page_json_version_id"] not in by_version
            or type(request.get("section_id")) is not str
            or type(request.get("table_id")) is not str
            or request.get("projection_adapter_id")
            != compiled_policy["projection_adapter_identity"]["adapter_id"]
            or request.get("projection_adapter_format_version")
            != compiled_policy["projection_adapter_identity"]["adapter_format_version"]
            or request.get("projection_adapter_implementation_ref_sha256")
            != compiled_policy["projection_adapter_identity"]["implementation_ref_sha256"]
            or request.get("projection_inventory_adapter_id")
            != compiled_policy["projection_inventory_adapter_identity"]["adapter_id"]
            or request.get("projection_inventory_adapter_format_version")
            != compiled_policy["projection_inventory_adapter_identity"]["adapter_format_version"]
            or request.get("projection_inventory_adapter_implementation_ref_sha256")
            != compiled_policy["projection_inventory_adapter_identity"]["implementation_ref_sha256"]
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
        for row in _fragment_logical_rows(fragment)
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
        "compiled_specs_sha256": compiled_policy["compiled_specs_sha256"],
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
        "compiled_specs_sha256": receipt["compiled_specs_sha256"],
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
