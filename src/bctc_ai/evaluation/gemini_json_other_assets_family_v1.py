"""Replayable Family-22 query and evaluation adapter.

The shared multi-table engine remains the authority for role classification,
period/unit parsing, arithmetic closure, and schema mappings.  This adapter
handles two source structures that are specific to the other-assets notes:

* a page-leading table explicitly marked ``CONTINUES_FROM_PREVIOUS_PAGE``
  when the immediately preceding source table omitted its matching marker;
* provision-control presentations whose MONEY axis is not a Family-22 schema
  axis (provision-only, or repeated asset-balance/provision metrics).

Neither rule inspects numeric values to select a table.  Source cells and
source coordinates are never rewritten.  Every accepted normalization is
content-addressed and replayed before storage.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    _classification_roles,
    _multitable_lane_axis,
    _unit_axis,
    build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    classify_gemini_json_multitable_hierarchical_table_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
    validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FAMILY_ID = "OTHER_ASSETS"
ADAPTER_FORMAT_VERSION = "GEMINI_JSON_OTHER_ASSETS_FAMILY_ADAPTER_V1"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_DECLARATIVE_MULTITABLE_HIERARCHICAL_"
    "FAMILY22_QUERY_ADAPTER_EXACT_PROVISION_CONTROL_AND_ONE_SIDED_EXPLICIT_"
    "CONTINUATION_RECEIPTS_SHARED_ENGINE_CLOSURE_SCHEMA_MAPPING_PROPOSAL_ONLY_"
    "NO_GEOMETRY_OCR_VALUE_SELECTION_BACKSOLVE_CANONICAL_OR_EXPORT_AUTHORITY"
)

_PROVISION_HEADING_MARKERS = (
    "du phong cho tai san co khac",
    "du phong rui ro cac tai san co noi bang khac",
    "du phong rui ro cho cac tai san co khac",
    "du phong rui ro cho cac tai san co noi bang khac",
)


class GeminiJsonOtherAssetsFamilyV1Error(ValueError):
    """Family-22 adapter input, receipt, or replay drifted."""


def _error(message: str) -> GeminiJsonOtherAssetsFamilyV1Error:
    return GeminiJsonOtherAssetsFamilyV1Error(message)


def _source_table(
    page_json: Mapping[str, Any], *, section_id: str, table_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        section = page_json["sections"][int(section_id[1:]) - 1]
        table = section["tables"][int(table_id[1:]) - 1]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise _error("Family-22 source locator does not resolve one table") from exc
    if type(section) is not dict or type(table) is not dict:
        raise _error("Family-22 source table is invalid")
    return section, table


def _normalized(value: Any) -> str:
    return normalize_vietnamese_anchor_v1(value if type(value) is str else "")


def _header_text(column: Mapping[str, Any]) -> str:
    path = column.get("header_path_exact")
    if type(path) is not list:
        return ""
    return " ".join(item for item in path if type(item) is str and item.strip())


def _money_column_ordinals(table: Mapping[str, Any]) -> list[int]:
    columns = table.get("columns")
    if type(columns) is not list:
        return []
    return [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]


def _locator(region: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: region[key]
        for key in (
            "page_json_version_id",
            "physical_page",
            "section_id",
            "selected_page_ordinal",
            "table_id",
        )
    }


def _first_money_table_locator(page_json: Mapping[str, Any]) -> tuple[str, str] | None:
    for section_ordinal, section in enumerate(page_json.get("sections") or [], start=1):
        if type(section) is not dict:
            continue
        for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
            if type(table) is dict and _money_column_ordinals(table):
                return f"s{section_ordinal}", f"t{table_ordinal}"
    return None


def _last_money_table_locator(page_json: Mapping[str, Any]) -> tuple[str, str] | None:
    result = None
    for section_ordinal, section in enumerate(page_json.get("sections") or [], start=1):
        if type(section) is not dict:
            continue
        for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
            if type(table) is dict and _money_column_ordinals(table):
                result = f"s{section_ordinal}", f"t{table_ordinal}"
    return result


def _exact_provision_control_receipt_v1(
    *,
    region: Mapping[str, Any],
    page_json_by_version: Mapping[str, dict[str, Any]],
    classification: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Classify a provision metric population that has no Family-22 output axis."""

    try:
        page_json = page_json_by_version[region["page_json_version_id"]]
        section, table = _source_table(
            page_json,
            section_id=region["section_id"],
            table_id=region["table_id"],
        )
    except (KeyError, GeminiJsonOtherAssetsFamilyV1Error):
        return None
    heading = _normalized(
        " ".join(
            value
            for value in (section.get("title_exact"), table.get("title_exact"))
            if type(value) is str and value.strip()
        )
    )
    if not any(marker in heading for marker in _PROVISION_HEADING_MARKERS):
        return None
    columns = table.get("columns")
    rows = table.get("rows")
    money_ordinals = _money_column_ordinals(table)
    if type(columns) is not list or type(rows) is not list or not rows:
        return None
    headers = [_normalized(_header_text(columns[ordinal - 1])) for ordinal in money_ordinals]
    header_paths = [
        canonical_clone_v1(columns[ordinal - 1].get("header_path_exact"))
        for ordinal in money_ordinals
    ]
    metric_axis = [
        "ASSET_BALANCE"
        if "so du tai san co" in header
        else "PROVISION"
        if "du phong" in header
        else None
        for header in headers
    ]
    total_rows = classification.get("total_rows")
    if type(total_rows) is not list:
        return None
    role_hits = classification.get("role_hits")
    if type(role_hits) is not list:
        return None

    if (
        len(money_ordinals) == 2
        and not role_hits
        and not classification.get("ambiguous_rows")
        and not classification.get("family_root_row_ordinals")
    ):
        control_kind = "TWO_PERIOD_PROVISION_ONLY_WITH_NO_SCHEMA_ROLE_HIT"
        selected_money_column_ordinals: list[int] = []
        source_only_money_column_ordinals = money_ordinals
    elif (
        money_ordinals == [1, 2, 3, 4]
        and bool(total_rows)
        and metric_axis
        == ["ASSET_BALANCE", "PROVISION", "ASSET_BALANCE", "PROVISION"]
        and bool(role_hits)
        and not classification.get("ambiguous_rows")
        and not classification.get("family_root_row_ordinals")
        and all(type(path) is list and len(path) >= 2 for path in header_paths)
        and same_typed_json_v1(header_paths[0][:-1], header_paths[1][:-1])
        and same_typed_json_v1(header_paths[2][:-1], header_paths[3][:-1])
        and not same_typed_json_v1(header_paths[0][:-1], header_paths[2][:-1])
    ):
        control_kind = "TWO_PERIOD_ASSET_BALANCE_AND_PROVISION_METRIC_CONTROL"
        selected_money_column_ordinals = [1, 3]
        source_only_money_column_ordinals = [2, 4]
    else:
        return None

    table_row_axis = []
    for row_ordinal, row in enumerate(rows, start=1):
        values = row.get("values_exact") if type(row) is dict else None
        if type(row) is not dict or type(values) is not list or len(values) != len(columns):
            return None
        table_row_axis.append(
            {
                "hierarchy_path_exact": canonical_clone_v1(
                    row.get("hierarchy_path_exact")
                ),
                "label_exact": row.get("label_exact"),
                "row_kind": row.get("row_kind"),
                "row_ordinal": row_ordinal,
                "values_exact": canonical_clone_v1(values),
            }
        )
    role_observation_axis = []
    for item in role_hits:
        row_ordinal = item["row_ordinal"]
        row = rows[row_ordinal - 1]
        role_observation_axis.append(
            {
                "gross_source_cells": [
                    {
                        "column_ordinal": ordinal,
                        "source_text": row["values_exact"][ordinal - 1],
                    }
                    for ordinal in selected_money_column_ordinals
                ],
                "hierarchy_path_exact": canonical_clone_v1(
                    row.get("hierarchy_path_exact")
                ),
                "label_exact": row.get("label_exact"),
                "provision_source_cells": [
                    {
                        "column_ordinal": ordinal,
                        "source_text": row["values_exact"][ordinal - 1],
                    }
                    for ordinal in source_only_money_column_ordinals
                    if ordinal not in selected_money_column_ordinals
                ],
                "role": item["role"],
                "row_kind": item["row_kind"],
                "row_ordinal": row_ordinal,
                "source_ref": {
                    "hierarchy_path_exact": canonical_clone_v1(
                        row.get("hierarchy_path_exact")
                    ),
                    "label_exact": row.get("label_exact"),
                    "locator": _locator(region),
                    "money_column_ordinals": money_ordinals,
                    "row_id": f"r{row_ordinal}",
                    "row_ordinal": row_ordinal,
                },
            }
        )

    material = {
        "column_headers_exact": [
            canonical_clone_v1(columns[ordinal - 1].get("header_path_exact"))
            for ordinal in money_ordinals
        ],
        "control_kind": control_kind,
        "disposition": (
            "SECONDARY_PROVISION_RISK_SUBSET_CONTROL_SOURCE_ONLY"
            if control_kind
            == "TWO_PERIOD_ASSET_BALANCE_AND_PROVISION_METRIC_CONTROL"
            else "PROVISION_ONLY_POPULATION_OUTSIDE_FAMILY22_SCHEMA_SOURCE_ONLY"
        ),
        "format_version": ADAPTER_FORMAT_VERSION,
        "gross_money_column_ordinals": selected_money_column_ordinals,
        "locator": _locator(region),
        "money_column_ordinals": money_ordinals,
        "period_identity_axis": (
            [header_paths[0][:-1], header_paths[2][:-1]]
            if control_kind
            == "TWO_PERIOD_ASSET_BALANCE_AND_PROVISION_METRIC_CONTROL"
            else header_paths
        ),
        "provision_money_column_ordinals": source_only_money_column_ordinals,
        "role_observation_axis": role_observation_axis,
        "rule": (
            "EXACT_PROVISION_HEADING_PLUS_TYPED_PROVISION_METRIC_AXIS_IS_"
            "AUTHENTICATED_SECONDARY_RISK_SUBSET_OR_PROVISION_ONLY_SOURCE_"
            "CONTROL_OUTSIDE_FAMILY22_SCHEMA_MAPPING_AXIS"
        ),
        "section_title_exact": section.get("title_exact"),
        "selected_mapping_money_column_ordinals": [],
        "source_only_money_column_ordinals": money_ordinals,
        "table_row_axis": table_row_axis,
        "table_title_exact": table.get("title_exact"),
        "total_row_ordinals": [item["row_ordinal"] for item in total_rows],
    }
    return {
        **material,
        "receipt_id": "gjoafav1:provision:" + canonical_json_sha256_v1(material),
    }


def _one_sided_continuation_receipt_v1(
    *,
    prior_region: Mapping[str, Any],
    receiver_region: Mapping[str, Any],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Authenticate one explicit receiver whose adjacent sender omitted ON_NEXT."""

    if (
        prior_region.get("document_id") != receiver_region.get("document_id")
        or prior_region.get("source_sha256") != receiver_region.get("source_sha256")
        or receiver_region.get("selected_page_ordinal")
        != prior_region.get("selected_page_ordinal", -2) + 1
        or receiver_region.get("physical_page")
        != prior_region.get("physical_page", -2) + 1
    ):
        return None
    try:
        prior_page = page_json_by_version[prior_region["page_json_version_id"]]
        receiver_page = page_json_by_version[receiver_region["page_json_version_id"]]
        prior_section, prior_table = _source_table(
            prior_page,
            section_id=prior_region["section_id"],
            table_id=prior_region["table_id"],
        )
        receiver_section, receiver_table = _source_table(
            receiver_page,
            section_id=receiver_region["section_id"],
            table_id=receiver_region["table_id"],
        )
    except (KeyError, GeminiJsonOtherAssetsFamilyV1Error):
        return None
    if (
        _last_money_table_locator(prior_page)
        != (prior_region.get("section_id"), prior_region.get("table_id"))
        or _first_money_table_locator(receiver_page)
        != (receiver_region.get("section_id"), receiver_region.get("table_id"))
        or prior_table.get("continuation")
        not in {"NONE", "CONTINUES_ON_NEXT_PAGE"}
        or receiver_table.get("continuation") != "CONTINUES_FROM_PREVIOUS_PAGE"
    ):
        return None

    prior_classification = classify_gemini_json_multitable_hierarchical_table_v1(
        prior_page,
        prior_section,
        prior_table,
        compiled_specs=compiled_specs,
    )
    receiver_classification = classify_gemini_json_multitable_hierarchical_table_v1(
        receiver_page,
        receiver_section,
        receiver_table,
        compiled_specs=compiled_specs,
    )
    receiver_roles = sorted(_classification_roles(receiver_classification))
    rows = receiver_table.get("rows")
    total_rows = receiver_classification.get("total_rows")
    if (
        prior_classification.get("typed_control_disposition") is not None
        or receiver_classification.get("typed_control_disposition") is not None
        or receiver_classification.get("ambiguous_rows")
        or not receiver_roles
        or type(rows) is not list
        or not rows
        or type(total_rows) is not list
        or len(total_rows) != 1
        or total_rows[0].get("row_ordinal") != len(rows)
        or rows[-1].get("row_kind") != "TOTAL"
    ):
        return None

    prior_lane = _multitable_lane_axis(
        prior_section, prior_table, compiled_specs=compiled_specs
    )
    receiver_lane = _multitable_lane_axis(
        receiver_section, receiver_table, compiled_specs=compiled_specs
    )
    prior_unit = _unit_axis(
        prior_table,
        compiled_specs=compiled_specs,
        document_unit_context=None,
    )
    receiver_unit = _unit_axis(
        receiver_table,
        compiled_specs=compiled_specs,
        document_unit_context=None,
    )
    receiver_ordinals = _money_column_ordinals(receiver_table)
    columns = receiver_table.get("columns")
    if prior_lane.get("complete") is not True or prior_unit.get("complete") is not True:
        return None
    explicit_equivalent = bool(
        receiver_lane.get("complete") is True
        and receiver_unit.get("complete") is True
        and receiver_lane.get("lane_keys") == prior_lane.get("lane_keys")
        and receiver_lane.get("selected_metric_kinds")
        == prior_lane.get("selected_metric_kinds")
        and receiver_unit.get("canonical_unit") == prior_unit.get("canonical_unit")
    )
    blank_receiver = bool(
        type(columns) is list
        and receiver_ordinals == prior_lane.get("money_column_ordinals")
        and receiver_ordinals
        and all(
            columns[ordinal - 1].get("header_path_exact") == [None]
            for ordinal in receiver_ordinals
        )
        and receiver_unit.get("complete") is not True
        and not receiver_unit.get("evidence")
        and not receiver_unit.get("undeclared_evidence")
    )
    if not explicit_equivalent and not blank_receiver:
        return None
    axis_rule = (
        "EXACT_EQUIVALENT_EXPLICIT_PERIOD_AND_UNIT_AXIS_NO_MUTATION"
        if explicit_equivalent
        else "COMPLETE_PRIOR_PERIOD_AND_UNIT_AXIS_INHERITED_BY_BLANK_RECEIVER"
    )
    sender_marker_rule = (
        "EXACT_TWO_SIDED_EXPLICIT_CONTINUATION"
        if prior_table.get("continuation") == "CONTINUES_ON_NEXT_PAGE"
        else "ADJACENT_SENDER_OMITTED_ON_NEXT_MARKER"
    )
    material = {
        "axis_rule": axis_rule,
        "format_version": ADAPTER_FORMAT_VERSION,
        "prior_lane_axis": canonical_clone_v1(prior_lane),
        "prior_locator": _locator(prior_region),
        "prior_unit_axis": canonical_clone_v1(prior_unit),
        "receiver_component_roles": receiver_roles,
        "receiver_lane_axis": canonical_clone_v1(receiver_lane),
        "receiver_locator": _locator(receiver_region),
        "receiver_total_row_ordinal": len(rows),
        "receiver_unit_axis": canonical_clone_v1(receiver_unit),
        "sender_marker_rule": sender_marker_rule,
        "rule": (
            "EXPLICIT_PAGE_LEADING_FROM_PREVIOUS_RECEIVER_PLUS_ADJACENT_FINAL_"
            "MONEY_TABLE_SENDER_WITH_EXACT_OR_OMITTED_ON_NEXT_MARKER_NO_VALUE_"
            "SELECTION"
        ),
    }
    return {
        **material,
        "receipt_id": "gjoafav1:continuation:" + canonical_json_sha256_v1(material),
    }


def _region_from_inventory(
    *,
    cluster: Mapping[str, Any],
    item: Mapping[str, Any],
    page_axis: Mapping[tuple[int, str], Mapping[str, Any]],
) -> dict[str, Any]:
    key = (cluster["document_ordinal"], item["page_json_version_id"])
    axis = page_axis.get(key)
    if type(axis) is not dict:
        raise _error("Family-22 selected page axis is incomplete")
    return {
        "component_roles": sorted(_classification_roles(item["classification"])),
        "document_id": cluster["document_id"],
        "document_ordinal": cluster["document_ordinal"],
        "fragment_ordinal": 0,
        "page_json_version_id": item["page_json_version_id"],
        "physical_page": item["physical_page"],
        "section_id": item["section_id"],
        "selected_page_ordinal": axis["selected_page_ordinal"],
        "source_logical_name": cluster["source_logical_name"],
        "source_sha256": cluster["source_sha256"],
        "table_id": item["table_id"],
    }


def adapt_gemini_json_other_assets_indexed_query_evidence_v1(
    value: Any,
    *,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Apply the two exact Family-22 source-structure dispositions."""

    if compiled_specs.get("topology", {}).get("family_id") != FAMILY_ID:
        raise _error("Family-22 adapter received another family")
    base = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        value, compiled_specs=compiled_specs
    )
    page_axis = {
        (item["document_ordinal"], item["page_json_version_id"]): item
        for item in base["selected_page_axis"]
    }
    clusters = []
    all_receipts = []
    for disposition in base["candidate_dispositions"]:
        cluster = canonical_clone_v1(disposition["cluster"])
        pages = page_json_by_document.get(cluster["document_ordinal"])
        if type(pages) is not dict:
            raise _error("Family-22 selected document page JSON is absent")
        inventory = cluster.get("declared_money_table_inventory")
        if type(inventory) is not list:
            raise _error("Family-22 declared MONEY inventory is absent")

        selected_items = []
        unresolved_items = []
        provision_receipts = []
        for item in inventory:
            if item.get("disposition") not in {
                "SELECTED_FAMILY_COMPONENT",
                "UNCONSUMED_MONEY_TABLE_INSIDE_OWNER_FENCE",
            }:
                continue
            provisional = _region_from_inventory(
                cluster=cluster,
                item=item,
                page_axis=page_axis,
            )
            receipt = _exact_provision_control_receipt_v1(
                region=provisional,
                page_json_by_version=pages,
                classification=item["classification"],
            )
            if receipt is not None:
                provision_receipts.append(receipt)
                item["disposition"] = "EXCLUDED_EXACT_FAMILY22_PROVISION_CONTROL"
            elif item.get("disposition") == "SELECTED_FAMILY_COMPONENT":
                selected_items.append(item)
            else:
                unresolved_items.append(item)

        continuation_receipts = []
        for item in sorted(unresolved_items, key=lambda entry: entry["position"]):
            provisional_items = sorted([*selected_items, item], key=lambda entry: entry["position"])
            item_index = provisional_items.index(item)
            receipt = None
            if item_index > 0:
                prior_region = _region_from_inventory(
                    cluster=cluster,
                    item=provisional_items[item_index - 1],
                    page_axis=page_axis,
                )
                receiver_region = _region_from_inventory(
                    cluster=cluster,
                    item=item,
                    page_axis=page_axis,
                )
                receipt = _one_sided_continuation_receipt_v1(
                    prior_region=prior_region,
                    receiver_region=receiver_region,
                    page_json_by_version=pages,
                    compiled_specs=compiled_specs,
                )
            if receipt is not None:
                item["disposition"] = "SELECTED_EXACT_FAMILY22_ONE_SIDED_CONTINUATION"
                selected_items.append(item)
                continuation_receipts.append(receipt)

        handled_unconsumed = len(continuation_receipts) + sum(
            1
            for receipt in provision_receipts
            if any(
                item.get("disposition")
                == "UNCONSUMED_MONEY_TABLE_INSIDE_OWNER_FENCE"
                and (
                    item.get("page_json_version_id"),
                    item.get("section_id"),
                    item.get("table_id"),
                )
                == (
                    receipt["locator"]["page_json_version_id"],
                    receipt["locator"]["section_id"],
                    receipt["locator"]["table_id"],
                )
                for item in disposition["cluster"]["declared_money_table_inventory"]
            )
        )
        original_unconsumed = [
            item
            for item in disposition["cluster"]["declared_money_table_inventory"]
            if item.get("disposition") == "UNCONSUMED_MONEY_TABLE_INSIDE_OWNER_FENCE"
        ]
        can_resolve = bool(
            selected_items
            and (continuation_receipts or provision_receipts)
            and (
                disposition["disposition"] == READY
                or (
                    original_unconsumed
                    and handled_unconsumed == len(original_unconsumed)
                    and len(cluster.get("reasons", [])) == len(original_unconsumed)
                    and all(
                        reason.startswith("UNCONSUMED_MONEY_TABLE_INSIDE_OWNER_FENCE:")
                        for reason in cluster.get("reasons", [])
                    )
                )
            )
        )
        if can_resolve:
            regions = [
                _region_from_inventory(cluster=cluster, item=item, page_axis=page_axis)
                for item in sorted(selected_items, key=lambda entry: entry["position"])
            ]
            for fragment_ordinal, region in enumerate(regions, start=1):
                region["fragment_ordinal"] = fragment_ordinal
            adapter_material = {
                "continuation_receipts": continuation_receipts,
                "format_version": ADAPTER_FORMAT_VERSION,
                "provision_control_receipts": provision_receipts,
            }
            adapter_receipt = {
                **adapter_material,
                "receipt_id": "gjoafav1:query:" + canonical_json_sha256_v1(adapter_material),
            }
            material = {
                **{key: item for key, item in cluster.items() if key != "cluster_id"},
                "component_regions": regions,
                "other_assets_query_adapter_receipt": adapter_receipt,
                "reasons": [],
                "status": READY,
            }
            cluster = {
                **material,
                "cluster_id": "gjmthfcv1:cluster:" + canonical_json_sha256_v1(material),
            }
            all_receipts.append(adapter_receipt)
        else:
            # Inventory dispositions are explored on a clone.  A partial match
            # must not leak into the fail-closed source cluster or invalidate
            # its content-addressed identity.
            cluster = canonical_clone_v1(disposition["cluster"])
        clusters.append(cluster)

    adapted = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=base["selected_document_axis"],
        selected_page_axis=base["selected_page_axis"],
        document_clusters=clusters,
        query_policy_sha256=canonical_json_sha256_v1(compiled_specs["query_policy"]),
    )
    validated = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        adapted, compiled_specs=compiled_specs
    )
    all_receipts.sort(key=lambda item: item["receipt_id"])
    return validated, all_receipts


def _apply_one_sided_continuation_normalizations_v1(
    *,
    regions: Sequence[Mapping[str, Any]],
    pages: dict[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    receipts = []
    ordered = sorted(
        regions,
        key=lambda item: (
            item["selected_page_ordinal"],
            int(item["section_id"][1:]),
            int(item["table_id"][1:]),
        ),
    )
    for prior_region, receiver_region in zip(ordered, ordered[1:], strict=False):
        receipt = _one_sided_continuation_receipt_v1(
            prior_region=prior_region,
            receiver_region=receiver_region,
            page_json_by_version=pages,
            compiled_specs=compiled_specs,
        )
        if receipt is None:
            continue
        _prior_section, prior_table = _source_table(
            pages[prior_region["page_json_version_id"]],
            section_id=prior_region["section_id"],
            table_id=prior_region["table_id"],
        )
        prior_table["continuation"] = "CONTINUES_ON_NEXT_PAGE"
        receipts.append(receipt)
    return receipts


def evaluate_gemini_json_other_assets_family_cluster_v1(
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate Family 22 after replaying exact continuation normalization."""

    if compiled_specs.get("topology", {}).get("family_id") != FAMILY_ID:
        raise _error("Family-22 adapter received another family")
    expected = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
    if type(query_receipt) is not dict or not same_typed_json_v1(query_receipt, expected):
        raise _error("Family-22 query receipt does not bind exact fragments")
    pages = canonical_clone_v1(page_json_by_version)
    continuation_receipts = _apply_one_sided_continuation_normalizations_v1(
        regions=expected["region_axis"],
        pages=pages,
        compiled_specs=compiled_specs,
    )
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=expected["region_axis"],
        page_json_by_version=pages,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if not continuation_receipts:
        return candidate
    material = {
        "continuation_receipts": continuation_receipts,
        "format_version": ADAPTER_FORMAT_VERSION,
        "shared_engine_claim_boundary": candidate["claim_boundary"],
    }
    candidate["claim_boundary"] = CLAIM_BOUNDARY
    candidate["closure_receipt"]["other_assets_adapter_receipt"] = {
        **material,
        "receipt_id": "gjoafav1:evaluation:" + canonical_json_sha256_v1(material),
    }
    candidate_material = {key: item for key, item in candidate.items() if key != "candidate_id"}
    candidate["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        candidate_material
    )
    return candidate


def validate_gemini_json_other_assets_family_candidate_replay_v1(
    value: Any,
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    expected = evaluate_gemini_json_other_assets_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if type(value) is not dict or not same_typed_json_v1(value, expected):
        raise _error("Family-22 candidate replay drifted")
    return expected
