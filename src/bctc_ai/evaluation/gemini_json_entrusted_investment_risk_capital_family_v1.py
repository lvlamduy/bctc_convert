"""Family 24 adapter over the multi-table hierarchical evaluator.

The shared evaluator remains authoritative for note-table owner fencing,
period lanes, accounting closure, and schema bindings.  This adapter adds two
source presentations that are deliberately too narrow for the shared engine:

* an exact Family-24 result row on a primary balance statement; and
* an otherwise unitless note whose observed total lanes uniquely match that
  exact primary Family-24 result's explicit unit and period axis; and
* source-authenticated PDF-visible label or dash repairs bound to immutable
  source, page-render, selected-page JSON, table, row, and cell identities.

No bank name, filename, reporting date, page number, or numeric value selects
a mapping.  Duplicate primary presentations are admitted only when their
scaled values agree exactly, after which the highest-precision source unit is
selected once.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.evaluation.gemini_json_customer_deposit_family_v1 import _money
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    compile_gemini_json_flat_family_specs_v1,
)
from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import (
    _normalized,
    _without_leading_ordinal,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    CLAIM_BOUNDARY as GENERIC_CLAIM_BOUNDARY,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    _classification_roles,
    build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    classify_gemini_json_multitable_hierarchical_table_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
    validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    validate_gemini_json_multitable_hierarchical_sweep_query_bindings_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FAMILY_ID = "ENTRUSTED_INVESTMENT_RISK_CAPITAL"
ADAPTER_FORMAT_VERSION = (
    "GEMINI_JSON_ENTRUSTED_INVESTMENT_RISK_CAPITAL_FAMILY_ADAPTER_V1"
)
SOURCE_REPAIR_FORMAT_VERSION = (
    "ENTRUSTED_INVESTMENT_RISK_CAPITAL_AUTHENTICATED_SOURCE_REPAIR_SPEC_V1"
)
ADAPTER_CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_FAMILY24_GENERIC_NOTE_CLOSURE_AND_"
    "EXACT_PRIMARY_BALANCE_SOURCE_RESULT_WITH_AUTHENTICATED_PDF_VISIBLE_"
    "SOURCE_REPAIR_BINDING_AND_EXACT_DUPLICATE_SCALE_CORROBORATION_HIGHEST_"
    "PRECISION_SOURCE_UNIT_SINGLE_POPULATION_AND_EXACT_OBSERVED_LANE_PRIMARY_"
    "RESULT_UNIT_CORROBORATION_SCHEMA_MAPPING_PROPOSAL_ONLY_"
    "NO_BANK_FILE_YEAR_PAGE_VALUE_ROUTING_BACKSOLVE_CANONICAL_OR_EXPORT_"
    "AUTHORITY"
)

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_PAGE_VERSION = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_SECTION_ID = re.compile(r"s[1-9][0-9]*\Z")
_TABLE_ID = re.compile(r"t[1-9][0-9]*\Z")
_OWNER_FENCED_SHORT_CURRENCY_ALIASES = {
    "FOREIGN_CURRENCY_RECEIVED_SOURCE": ["Bằng ngoại tệ", "Bằng ngoại tệ (i)"],
    "VND_RECEIVED_SOURCE": ["Bằng VND"],
}


class GeminiJsonEntrustedInvestmentRiskCapitalFamilyV1Error(ValueError):
    """Family-24 specs, evidence, candidate, or replay drifted."""


def _error(message: str) -> GeminiJsonEntrustedInvestmentRiskCapitalFamilyV1Error:
    return GeminiJsonEntrustedInvestmentRiskCapitalFamilyV1Error(message)


def _validate_source_repairs(value: Any) -> list[dict[str, Any]]:
    if (
        type(value) is not dict
        or set(value) != {"family_id", "format_version", "render_contract", "repairs"}
        or value.get("family_id") != FAMILY_ID
        or value.get("format_version") != SOURCE_REPAIR_FORMAT_VERSION
        or value.get("render_contract")
        != {
            "alpha": False,
            "colorspace": "RGB",
            "format": "PNG",
            "matrix": [2, 2],
            "renderer": "PyMuPDF",
        }
        or type(value.get("repairs")) is not list
    ):
        raise _error("Family-24 authenticated source-repair spec is invalid")
    checked = []
    identities = set()
    for repair in value["repairs"]:
        kind = repair.get("repair_kind") if type(repair) is dict else None
        fields = {
            "after_exact",
            "before_exact",
            "locator",
            "pdf_page_render_sha256",
            "repair_id",
            "repair_kind",
            "source_sha256",
        }
        if kind == "MONEY_CELL_VISIBLE_DASH":
            fields.add("column_ordinal")
        locator = repair.get("locator") if type(repair) is dict else None
        if (
            type(repair) is not dict
            or set(repair) != fields
            or kind not in {"LABEL_EXACT", "MONEY_CELL_VISIBLE_DASH"}
            or type(locator) is not dict
            or set(locator)
            != {
                "page_json_version_id",
                "physical_page",
                "row_ordinal",
                "section_id",
                "table_id",
            }
            or _PAGE_VERSION.fullmatch(locator.get("page_json_version_id", "")) is None
            or type(locator.get("physical_page")) is not int
            or locator["physical_page"] <= 0
            or type(locator.get("row_ordinal")) is not int
            or locator["row_ordinal"] <= 0
            or _SECTION_ID.fullmatch(locator.get("section_id", "")) is None
            or _TABLE_ID.fullmatch(locator.get("table_id", "")) is None
            or _SHA256.fullmatch(repair.get("source_sha256", "")) is None
            or _SHA256.fullmatch(repair.get("pdf_page_render_sha256", "")) is None
            or (
                kind == "LABEL_EXACT"
                and (
                    type(repair.get("before_exact")) is not str
                    or not repair["before_exact"]
                    or type(repair.get("after_exact")) is not str
                    or not repair["after_exact"]
                )
            )
            or (
                kind == "MONEY_CELL_VISIBLE_DASH"
                and (
                    repair.get("before_exact") is not None
                    or repair.get("after_exact") != "-"
                    or type(repair.get("column_ordinal")) is not int
                    or repair["column_ordinal"] <= 0
                )
            )
        ):
            raise _error("Family-24 authenticated source repair is invalid")
        material = {key: canonical_clone_v1(item) for key, item in repair.items() if key != "repair_id"}
        if repair.get("repair_id") != (
            "geircfav1:repair:" + canonical_json_sha256_v1(material)
        ):
            raise _error("Family-24 authenticated source-repair identity drifted")
        identity = (
            repair["source_sha256"],
            *[locator[key] for key in ("page_json_version_id", "section_id", "table_id")],
            locator["row_ordinal"],
            repair.get("column_ordinal"),
            kind,
        )
        if identity in identities:
            raise _error("Family-24 authenticated source-repair axis is duplicate")
        identities.add(identity)
        checked.append(canonical_clone_v1(repair))
    return checked


def compile_gemini_json_entrusted_investment_risk_capital_family_specs_v1(
    topology_spec: Any,
    evaluation_spec: Any,
    schema_binding_spec: Any,
    source_repair_spec: Any,
) -> dict[str, Any]:
    """Compile one Family-24 triplet plus its authenticated source repairs."""

    base_compiled = compile_gemini_json_flat_family_specs_v1(
        topology_spec, evaluation_spec, schema_binding_spec
    )
    if base_compiled.get("topology", {}).get("family_id") != FAMILY_ID:
        raise _error("Family-24 declarative frontier is invalid")
    adapted_topology = canonical_clone_v1(topology_spec)
    children = adapted_topology.get("children")
    if type(children) is not list:
        raise _error("Family-24 declarative child frontier is invalid")
    for role, aliases in _OWNER_FENCED_SHORT_CURRENCY_ALIASES.items():
        matches = [
            child
            for child in children
            if type(child) is dict and child.get("role") == role
        ]
        if len(matches) != 1 or type(matches[0].get("matchers")) is not list:
            raise _error("Family-24 owner-fenced short currency role is absent")
        matches[0]["matchers"].append(
            {"aliases": canonical_clone_v1(aliases), "within_role": None}
        )
    compiled = compile_gemini_json_flat_family_specs_v1(
        adapted_topology, evaluation_spec, schema_binding_spec
    )
    if (
        compiled.get("topology", {}).get("family_id") != FAMILY_ID
        or compiled.get("evaluation", {}).get("family_id") != FAMILY_ID
        or compiled.get("schema", {}).get("family_id") != FAMILY_ID
        or set(compiled.get("bindings", {}))
        != {
            "DIRECT_INTERNATIONAL_ORGANIZATION",
            "DIRECT_INTERNATIONAL_ORGANIZATION_FOREIGN_CURRENCY",
            "DIRECT_INTERNATIONAL_ORGANIZATION_VND",
            "FOREIGN_CURRENCY_RECEIVED_SOURCE",
            "ORGANIZATION_OR_INDIVIDUAL",
            "OTHER_RECEIVED_SOURCE",
            "VND_RECEIVED_SOURCE",
        }
        or {
            item["canonical_unit"]
            for item in compiled.get("unit_bindings", [])
            if item.get("accepted") is True
        }
        != {"MILLION_VND", "VND"}
    ):
        raise _error("Family-24 declarative frontier is invalid")
    compiled["entrusted_investment_risk_capital_source_repairs"] = (
        _validate_source_repairs(source_repair_spec)
    )
    compiled["entrusted_investment_risk_capital_source_repair_spec_sha256"] = (
        canonical_json_sha256_v1(source_repair_spec)
    )
    compiled["entrusted_investment_risk_capital_adapter_format_version"] = (
        ADAPTER_FORMAT_VERSION
    )
    compiled["entrusted_investment_risk_capital_owner_fenced_short_currency_aliases"] = (
        canonical_clone_v1(_OWNER_FENCED_SHORT_CURRENCY_ALIASES)
    )
    return compiled


def _source_table(
    page_json: Mapping[str, Any], *, section_id: str, table_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        section = page_json["sections"][int(section_id[1:]) - 1]
        table = section["tables"][int(table_id[1:]) - 1]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise _error("Family-24 source locator does not resolve one table") from exc
    if type(section) is not dict or type(table) is not dict:
        raise _error("Family-24 source table is invalid")
    return section, table


def _document_repairs(
    *,
    source_sha256: str,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    pages = {
        page_json_version_id: canonical_clone_v1(page_json)
        for page_json_version_id, page_json in page_json_by_version.items()
    }
    applicable = [
        repair
        for repair in compiled_specs.get(
            "entrusted_investment_risk_capital_source_repairs", []
        )
        if repair["source_sha256"] == source_sha256
    ]
    for repair in applicable:
        locator = repair["locator"]
        page = pages.get(locator["page_json_version_id"])
        if page is None:
            raise _error("Family-24 repair page is outside the selected document")
        _, table = _source_table(
            page,
            section_id=locator["section_id"],
            table_id=locator["table_id"],
        )
        rows = table.get("rows")
        if type(rows) is not list or locator["row_ordinal"] > len(rows):
            raise _error("Family-24 repair row is outside its bound source table")
        row = rows[locator["row_ordinal"] - 1]
        if type(row) is not dict:
            raise _error("Family-24 repair row is invalid")
        if repair["repair_kind"] == "LABEL_EXACT":
            if row.get("label_exact") != repair["before_exact"]:
                raise _error("Family-24 label repair before-image drifted")
            row["label_exact"] = repair["after_exact"]
        else:
            values = row.get("values_exact")
            column_ordinal = repair["column_ordinal"]
            if (
                type(values) is not list
                or column_ordinal > len(values)
                or values[column_ordinal - 1] is not repair["before_exact"]
            ):
                raise _error("Family-24 dash repair before-image drifted")
            values[column_ordinal - 1] = repair["after_exact"]
    return pages, canonical_clone_v1(applicable)


def _parent_aliases(compiled_specs: Mapping[str, Any]) -> set[str]:
    return {
        _normalized(alias)
        for alias in compiled_specs["topology"]["parent"]["aliases"]
    }


def _is_parent_label(label: Any, *, compiled_specs: Mapping[str, Any]) -> bool:
    if type(label) is not str:
        return False
    return _without_leading_ordinal(_normalized(label)) in _parent_aliases(compiled_specs)


def _money_ordinals(table: Mapping[str, Any]) -> list[int]:
    columns = table.get("columns")
    if type(columns) is not list:
        return []
    return [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]


def _accepted_explicit_unit(
    source_exact: Any, *, compiled_specs: Mapping[str, Any]
) -> tuple[str, int] | None:
    source = _normalized(source_exact)
    matches = []
    for binding in compiled_specs.get("unit_bindings", []):
        if binding.get("accepted") is not True:
            continue
        for alias in binding["aliases"]:
            if alias == source or alias in source:
                matches.append(
                    (
                        len(alias),
                        binding["canonical_unit"],
                        binding["magnitude_power10"],
                    )
                )
    if not matches:
        return None
    longest = max(item[0] for item in matches)
    unique = sorted({item[1:] for item in matches if item[0] == longest})
    return unique[0] if len(unique) == 1 else None


def _preceding_primary_unit(
    *,
    region: Mapping[str, Any],
    page_json_by_version: Mapping[str, dict[str, Any]],
    selected_page_axis: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    pages = [
        item
        for item in selected_page_axis
        if item.get("document_ordinal") == region["document_ordinal"]
    ]
    current = next(
        (
            (ordinal, item)
            for ordinal, item in enumerate(pages)
            if item.get("page_json_version_id") == region["page_json_version_id"]
        ),
        None,
    )
    if current is None or current[0] == 0:
        return None
    prior = pages[current[0] - 1]
    if (
        prior.get("selected_page_ordinal") + 1 != region["selected_page_ordinal"]
        or prior.get("physical_page") + 1 != region["physical_page"]
    ):
        return None
    page = page_json_by_version.get(prior["page_json_version_id"])
    units = []
    for section in page.get("sections", []) if type(page) is dict else []:
        if (
            type(section) is not dict
            or section.get("statement_type") != "BALANCE_SHEET"
            or section.get("content_kind") != "PRIMARY_STATEMENT"
        ):
            continue
        for table in section.get("tables", []):
            if type(table) is not dict:
                continue
            unit = _accepted_explicit_unit(table.get("unit_exact"), compiled_specs=compiled_specs)
            if unit is not None:
                units.append(unit)
    if len(set(units)) != 1:
        return None
    canonical_unit, magnitude_power10 = units[0]
    return {
        "canonical_unit": canonical_unit,
        "magnitude_power10": magnitude_power10,
        "page_json_version_id": prior["page_json_version_id"],
        "physical_page": prior["physical_page"],
        "rule": (
            "IMMEDIATELY_PRECEDING_CONTIGUOUS_PRIMARY_BALANCE_PAGE_EXPLICIT_UNIT"
        ),
    }


def _root_regions(
    *,
    document: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    pages, repairs = _document_repairs(
        source_sha256=document["source_sha256"],
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
    )
    regions = []
    for page_axis in selected_page_axis:
        if page_axis.get("document_ordinal") != document["document_ordinal"]:
            continue
        page = pages.get(page_axis["page_json_version_id"])
        if type(page) is not dict:
            raise _error("Family-24 selected page JSON is absent")
        for section_ordinal, section in enumerate(page.get("sections", []), start=1):
            if (
                type(section) is not dict
                or section.get("statement_type") != "BALANCE_SHEET"
                or section.get("content_kind") != "PRIMARY_STATEMENT"
            ):
                continue
            for table_ordinal, table in enumerate(section.get("tables", []), start=1):
                if type(table) is not dict or len(_money_ordinals(table)) != 2:
                    continue
                root_rows = [
                    ordinal
                    for ordinal, row in enumerate(table.get("rows", []), start=1)
                    if type(row) is dict
                    and _is_parent_label(row.get("label_exact"), compiled_specs=compiled_specs)
                ]
                if len(root_rows) != 1:
                    continue
                regions.append(
                    {
                        "component_roles": [],
                        "document_id": document["document_id"],
                        "document_ordinal": document["document_ordinal"],
                        "fragment_ordinal": 0,
                        "page_json_version_id": page_axis["page_json_version_id"],
                        "physical_page": page_axis["physical_page"],
                        "section_id": f"s{section_ordinal}",
                        "selected_page_ordinal": page_axis["selected_page_ordinal"],
                        "source_logical_name": document["source_logical_name"],
                        "source_sha256": document["source_sha256"],
                        "table_id": f"t{table_ordinal}",
                    }
                )
    for ordinal, region in enumerate(regions, start=1):
        region["fragment_ordinal"] = ordinal
    return regions, pages, repairs


def _region_repairs(
    region: Mapping[str, Any], repairs: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    return [
        canonical_clone_v1(repair)
        for repair in repairs
        if repair["locator"]["page_json_version_id"] == region["page_json_version_id"]
        and repair["locator"]["section_id"] == region["section_id"]
        and repair["locator"]["table_id"] == region["table_id"]
    ]


def _root_observation(
    *,
    region: Mapping[str, Any],
    page_json_by_version: Mapping[str, dict[str, Any]],
    selected_page_axis: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    repairs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    page = page_json_by_version[region["page_json_version_id"]]
    section, table = _source_table(
        page, section_id=region["section_id"], table_id=region["table_id"]
    )
    root_rows = [
        (ordinal, row)
        for ordinal, row in enumerate(table.get("rows", []), start=1)
        if type(row) is dict
        and _is_parent_label(row.get("label_exact"), compiled_specs=compiled_specs)
    ]
    money_ordinals = _money_ordinals(table)
    reasons = []
    row_ordinal = None
    row = None
    if len(root_rows) != 1:
        reasons.append("EXACTLY_ONE_PRIMARY_SOURCE_RESULT_ROW_NOT_PROVEN")
    else:
        row_ordinal, row = root_rows[0]
    values = []
    if row is not None:
        source_values = row.get("values_exact")
        if type(source_values) is not list or any(
            ordinal > len(source_values) for ordinal in money_ordinals
        ):
            reasons.append("PRIMARY_SOURCE_RESULT_CELL_AXIS_INCOMPLETE")
        else:
            for ordinal in money_ordinals:
                source = source_values[ordinal - 1]
                if source is None:
                    values.append(
                        {
                            "coefficient": None,
                            "source_text": None,
                            "state": "BLANK_SOURCE_CELL",
                        }
                    )
                    continue
                try:
                    values.append(_money(source))
                except (TypeError, ValueError):
                    reasons.append("PRIMARY_SOURCE_RESULT_MONEY_CELL_INVALID")
    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        page, section, table, compiled_specs=compiled_specs
    )
    inspection_region = {
        **region,
        "component_roles": sorted(_classification_roles(classification)),
        "fragment_ordinal": 1,
    }
    query_receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        [inspection_region]
    )
    inspected = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=[inspection_region],
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    table_receipts = inspected.get("closure_receipt", {}).get("table_receipts", [])
    table_receipt = table_receipts[0] if len(table_receipts) == 1 else None
    lane_axis = table_receipt.get("lane_axis") if type(table_receipt) is dict else None
    if (
        type(lane_axis) is not dict
        or lane_axis.get("complete") is not True
        or len(lane_axis.get("lane_keys", [])) != 2
        or len(money_ordinals) != 2
    ):
        reasons.append("PRIMARY_SOURCE_RESULT_PERIOD_AXIS_INCOMPLETE")
    unit_axis = table_receipt.get("unit_axis") if type(table_receipt) is dict else None
    unit_receipt = None
    if type(unit_axis) is dict and unit_axis.get("complete") is True:
        binding = next(
            (
                item
                for item in compiled_specs["unit_bindings"]
                if item["canonical_unit"] == unit_axis.get("canonical_unit")
                and item["accepted"] is True
            ),
            None,
        )
        if binding is not None:
            unit_receipt = {
                "canonical_unit": binding["canonical_unit"],
                "magnitude_power10": binding["magnitude_power10"],
                "rule": "GENERIC_TABLE_OR_DOCUMENT_UNIT_AXIS_EXACT",
            }
    if unit_receipt is None:
        unit_receipt = _preceding_primary_unit(
            region=region,
            page_json_by_version=page_json_by_version,
            selected_page_axis=selected_page_axis,
            compiled_specs=compiled_specs,
        )
    if unit_receipt is None:
        reasons.append("PRIMARY_SOURCE_RESULT_UNIT_AXIS_INCOMPLETE")
    if values and all(value.get("coefficient") is None for value in values):
        reasons.append("PRIMARY_SOURCE_RESULT_ALL_LANES_BLANK")
    reasons = sorted(set(reasons))
    source_ref = None
    if row is not None and row_ordinal is not None:
        source_ref = {
            "hierarchy_path_exact": canonical_clone_v1(row.get("hierarchy_path_exact", [])),
            "label_exact": row.get("label_exact"),
            "locator": canonical_clone_v1({**region, "fragment_ordinal": 1}),
            "money_column_ordinals": money_ordinals,
            "row_id": row.get("row_id", f"r{row_ordinal}"),
            "row_kind": row.get("row_kind"),
            "row_ordinal": row_ordinal,
        }
    return {
        "magnitude_power10": (
            unit_receipt["magnitude_power10"] if unit_receipt is not None else None
        ),
        "reasons": reasons,
        "repair_receipts": _region_repairs(region, repairs),
        "source_ref": source_ref,
        "status": READY if not reasons else UNRESOLVED,
        "table_receipt": canonical_clone_v1(table_receipt),
        "unit": unit_receipt["canonical_unit"] if unit_receipt is not None else None,
        "unit_receipt": canonical_clone_v1(unit_receipt),
        "values": values if not reasons else [],
    }


def _select_root_regions(
    *,
    regions: Sequence[dict[str, Any]],
    pages: Mapping[str, dict[str, Any]],
    selected_page_axis: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    repairs: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    observations = [
        _root_observation(
            region=region,
            page_json_by_version=pages,
            selected_page_axis=selected_page_axis,
            compiled_specs=compiled_specs,
            repairs=repairs,
        )
        for region in regions
    ]
    ready = [
        (region, observation)
        for region, observation in zip(regions, observations, strict=True)
        if observation["status"] == READY
    ]
    rule = "ALL_SOURCE_VISIBLE_ROOT_POPULATIONS_RETAINED_UNRESOLVED"
    selected = list(regions)
    if len(ready) == 1:
        selected = [ready[0][0]]
        rule = "UNIQUE_COMPLETE_SOURCE_VISIBLE_ROOT_POPULATION"
    elif len(ready) > 1:
        scaled = [
            tuple(
                (
                    None
                    if value["coefficient"] is None
                    else value["coefficient"]
                    * (10 ** observation["magnitude_power10"])
                )
                for value in observation["values"]
            )
            for _, observation in ready
        ]
        if len(set(scaled)) == 1:
            chosen = min(
                ready,
                key=lambda item: (
                    item[1]["magnitude_power10"],
                    item[0]["selected_page_ordinal"],
                    item[0]["section_id"],
                    item[0]["table_id"],
                ),
            )
            selected = [chosen[0]]
            rule = (
                "EXACT_SCALED_DUPLICATE_CORROBORATION_HIGHEST_PRECISION_SOURCE_UNIT"
            )
    for ordinal, region in enumerate(selected, start=1):
        region["fragment_ordinal"] = ordinal
    projection = []
    for region, observation in zip(regions, observations, strict=True):
        projection.append(
            {
                "locator": {
                    key: region[key]
                    for key in (
                        "page_json_version_id",
                        "physical_page",
                        "section_id",
                        "table_id",
                    )
                },
                "magnitude_power10": observation["magnitude_power10"],
                "reasons": observation["reasons"],
                "repair_ids": [
                    item["repair_id"] for item in observation["repair_receipts"]
                ],
                "status": observation["status"],
                "unit": observation["unit"],
                "values": canonical_clone_v1(observation["values"]),
            }
        )
    material = {
        "population_projection": projection,
        "rule": rule,
        "selected_region_axis_sha256": canonical_json_sha256_v1(selected),
        "source_repair_spec_sha256": compiled_specs[
            "entrusted_investment_risk_capital_source_repair_spec_sha256"
        ],
    }
    return selected, {
        **material,
        "adapter_query_receipt_id": (
            "geircfav1:query:" + canonical_json_sha256_v1(material)
        ),
    }


def build_gemini_json_entrusted_investment_risk_capital_indexed_query_evidence_v1(
    *,
    base_indexed_query_evidence: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Add exact primary-source-result candidates to exhaustive base evidence."""

    base = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        base_indexed_query_evidence, compiled_specs=compiled_specs
    )
    pages_by_document: dict[int, list[dict[str, Any]]] = {}
    for page in base["selected_page_axis"]:
        pages_by_document.setdefault(page["document_ordinal"], []).append(page)
    clusters = []
    for disposition, document in zip(
        base["candidate_dispositions"], base["selected_document_axis"], strict=True
    ):
        cluster = canonical_clone_v1(disposition["cluster"])
        if disposition["disposition"] != NOT_OBSERVED:
            clusters.append(cluster)
            continue
        document_pages = page_json_by_document.get(document["document_ordinal"])
        if type(document_pages) is not dict:
            raise _error("Family-24 selected document page JSON is absent")
        regions, repaired_pages, repairs = _root_regions(
            document=document,
            selected_page_axis=pages_by_document[document["document_ordinal"]],
            page_json_by_version=document_pages,
            compiled_specs=compiled_specs,
        )
        if not regions:
            clusters.append(cluster)
            continue
        selected, receipt = _select_root_regions(
            regions=regions,
            pages=repaired_pages,
            selected_page_axis=pages_by_document[document["document_ordinal"]],
            compiled_specs=compiled_specs,
            repairs=repairs,
        )
        material = {
            **{key: value for key, value in cluster.items() if key != "cluster_id"},
            "component_regions": selected,
            "entrusted_investment_risk_capital_query_adapter_receipt": receipt,
            "reasons": [],
            "status": READY,
        }
        clusters.append(
            {
                **material,
                "cluster_id": "gjmthfcv1:cluster:" + canonical_json_sha256_v1(material),
            }
        )
    evidence = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=base["selected_document_axis"],
        selected_page_axis=base["selected_page_axis"],
        document_clusters=clusters,
        query_policy_sha256=canonical_json_sha256_v1(compiled_specs["query_policy"]),
    )
    return validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        evidence, compiled_specs=compiled_specs
    )


def _mapping_units(candidate: Mapping[str, Any]) -> dict[tuple[str, str, str], str]:
    result = {}
    receipts = candidate.get("closure_receipt", {}).get("table_receipts", [])
    for receipt in receipts if type(receipts) is list else []:
        region = receipt.get("region") if type(receipt) is dict else None
        unit_axis = receipt.get("unit_axis") if type(receipt) is dict else None
        if type(region) is not dict or type(unit_axis) is not dict:
            continue
        unit = unit_axis.get("canonical_unit")
        key = tuple(region.get(field) for field in ("page_json_version_id", "section_id", "table_id"))
        if unit not in {"MILLION_VND", "VND"} or any(type(item) is not str for item in key):
            continue
        prior = result.setdefault(key, unit)
        if prior != unit:
            raise _error("Family-24 one source table has conflicting units")
    return result


def _reseal_note_candidate(
    candidate: dict[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
    primary_source_unit_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if candidate.get("status") != READY:
        return candidate
    blank_source_corrections = []
    derived_state_corrections = []
    omitted_roles = []
    blank_source_ref_lanes: dict[str, set[int]] = {}
    retained = []
    for mapping in candidate.get("mappings", []):
        values = mapping.get("values", [])
        blank_lanes = [
            ordinal
            for ordinal, value in enumerate(values, start=1)
            if value.get("source_text") is None
            and (
                "BLANK_ZERO" in value.get("state", "")
                or (
                    "BLANK" in value.get("state", "")
                    and "INFERRED" in value.get("state", "")
                )
            )
        ]
        if mapping.get("state", "").startswith("DECLARED_FAMILY_ROOT_DERIVED"):
            for ordinal, value in enumerate(values, start=1):
                if (
                    value.get("source_text") is None
                    and value.get("coefficient") is not None
                    and value.get("state") == "EXACT_COMPLETE_TOP_LEVEL_COMPONENT_SUM"
                ):
                    value["state"] = "DERIVED_EXACT_COMPLETE_TOP_LEVEL_COMPONENT_SUM"
                    derived_state_corrections.append(
                        {
                            "lane_ordinal": ordinal,
                            "role": mapping.get("role"),
                            "rule": "EXPLICITLY_TYPE_SOURCELESS_COMPLETE_SUM_AS_DERIVED",
                        }
                    )
        if not blank_lanes:
            retained.append(mapping)
            continue
        for source_ref in mapping.get("source_refs", []):
            blank_source_ref_lanes.setdefault(
                canonical_json_sha256_v1(source_ref), set()
            ).update(blank_lanes)
        for ordinal in blank_lanes:
            values[ordinal - 1] = {
                "coefficient": None,
                "source_text": None,
                "state": "BLANK_SOURCE_CELL",
            }
        blank_source_corrections.append(
            {
                "lane_ordinals": blank_lanes,
                "role": mapping.get("role"),
                "rule": "SOURCE_NULL_PRESERVED_AS_TYPED_BLANK_NEVER_ZERO",
            }
        )
        if all(value.get("coefficient") is None for value in values):
            omitted_roles.append(mapping.get("role"))
        else:
            retained.append(mapping)
    still_retained = []
    for mapping in retained:
        if not mapping.get("state", "").startswith("DECLARED_FAMILY_ROOT_DERIVED"):
            still_retained.append(mapping)
            continue
        affected_lanes = set()
        for source_ref in mapping.get("source_refs", []):
            affected_lanes.update(
                blank_source_ref_lanes.get(canonical_json_sha256_v1(source_ref), set())
            )
        for ordinal in sorted(affected_lanes):
            mapping["values"][ordinal - 1] = {
                "coefficient": None,
                "source_text": None,
                "state": "DERIVED_INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL",
            }
        if affected_lanes:
            blank_source_corrections.append(
                {
                    "lane_ordinals": sorted(affected_lanes),
                    "role": mapping.get("role"),
                    "rule": "DERIVATION_LANE_INVALIDATED_BY_SOURCE_BLANK",
                }
            )
        if all(value.get("coefficient") is None for value in mapping.get("values", [])):
            omitted_roles.append(mapping.get("role"))
        else:
            still_retained.append(mapping)
    retained = still_retained
    candidate["mappings"] = retained
    if not retained:
        candidate["reasons"] = ["ALL_MAPPABLE_SOURCE_ROLES_ARE_BLANK"]
        candidate["status"] = UNRESOLVED
    units = _mapping_units(candidate)
    corrections = []
    for mapping in candidate.get("mappings", []):
        source_units = set()
        for source_ref in mapping.get("source_refs", []):
            locator = source_ref.get("locator") if type(source_ref) is dict else None
            if type(locator) is not dict:
                continue
            key = tuple(locator.get(field) for field in ("page_json_version_id", "section_id", "table_id"))
            if key in units:
                source_units.add(units[key])
        if len(source_units) != 1:
            raise _error("Family-24 mapping source unit is absent or ambiguous")
        source_unit = next(iter(source_units))
        before = mapping.get("unit")
        if before != source_unit:
            corrections.append(
                {
                    "after_unit": source_unit,
                    "before_unit": before,
                    "report_norm_id": mapping.get("report_norm_id"),
                    "role": mapping.get("role"),
                }
            )
            mapping["unit"] = source_unit
        material = {key: item for key, item in mapping.items() if key != "item_mapping_id"}
        mapping["item_mapping_id"] = "gjmthfmv1:item:" + canonical_json_sha256_v1(material)
    if (
        not corrections
        and not blank_source_corrections
        and not derived_state_corrections
        and not omitted_roles
        and primary_source_unit_receipt is None
    ):
        return candidate
    adapter_material = {
        "adapter_format_version": ADAPTER_FORMAT_VERSION,
        "blank_source_lane_corrections": blank_source_corrections,
        "derived_state_corrections": derived_state_corrections,
        "mapping_unit_corrections": corrections,
        "omitted_all_blank_roles": sorted(omitted_roles),
        "primary_source_unit_receipt": canonical_clone_v1(
            primary_source_unit_receipt
        ),
        "shared_engine_claim_boundary": GENERIC_CLAIM_BOUNDARY,
        "source_repair_spec_sha256": compiled_specs[
            "entrusted_investment_risk_capital_source_repair_spec_sha256"
        ],
    }
    candidate["claim_boundary"] = ADAPTER_CLAIM_BOUNDARY
    candidate["closure_receipt"]["entrusted_investment_risk_capital_adapter_receipt"] = {
        **adapter_material,
        "adapter_receipt_id": (
            "geircfav1:receipt:" + canonical_json_sha256_v1(adapter_material)
        ),
    }
    material = {key: item for key, item in candidate.items() if key != "candidate_id"}
    candidate["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(material)
    return candidate


def _unitless_note_total_observation(
    *,
    candidate: Mapping[str, Any],
    regions: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
) -> dict[str, Any] | None:
    """Return one source-observed unitless note total on a complete period axis."""

    if (
        candidate.get("status") != UNRESOLVED
        or candidate.get("reasons")
        != ["FRAGMENT_PERIOD_OR_UNIT_AXIS_NOT_LOCALLY_USABLE"]
        or len(regions) != 1
    ):
        return None
    receipts = candidate.get("closure_receipt", {}).get("table_receipts", [])
    if type(receipts) is not list or len(receipts) != 1:
        return None
    receipt = receipts[0]
    classification = receipt.get("classification") if type(receipt) is dict else None
    lane_axis = receipt.get("lane_axis") if type(receipt) is dict else None
    unit_axis = receipt.get("unit_axis") if type(receipt) is dict else None
    total_rows = (
        classification.get("total_rows") if type(classification) is dict else None
    )
    if (
        type(classification) is not dict
        or classification.get("owner_visible") is not True
        or classification.get("family_presence_anchor_visible") is not True
        or type(total_rows) is not list
        or len(total_rows) != 1
        or type(lane_axis) is not dict
        or lane_axis.get("complete") is not True
        or len(lane_axis.get("lane_keys", [])) != 2
        or type(unit_axis) is not dict
        or unit_axis.get("complete") is not False
        or unit_axis.get("reasons") != ["MONEY_UNIT_NOT_EXACTLY_RESOLVED"]
    ):
        return None
    region = regions[0]
    page = page_json_by_version.get(region["page_json_version_id"])
    if type(page) is not dict:
        return None
    _, table = _source_table(
        page, section_id=region["section_id"], table_id=region["table_id"]
    )
    if table.get("unit_exact") is not None:
        return None
    rows = table.get("rows")
    money_ordinals = lane_axis.get("money_column_ordinals")
    total_ordinal = total_rows[0].get("row_ordinal")
    if (
        type(rows) is not list
        or type(money_ordinals) is not list
        or len(money_ordinals) != 2
        or any(type(ordinal) is not int for ordinal in money_ordinals)
        or type(total_ordinal) is not int
        or total_ordinal <= 0
        or total_ordinal > len(rows)
    ):
        return None
    row = rows[total_ordinal - 1]
    source_values = row.get("values_exact") if type(row) is dict else None
    if type(source_values) is not list or any(
        ordinal <= 0 or ordinal > len(source_values) for ordinal in money_ordinals
    ):
        return None
    values = []
    for ordinal in money_ordinals:
        source = source_values[ordinal - 1]
        if source is None:
            values.append(
                {
                    "coefficient": None,
                    "source_text": None,
                    "state": "BLANK_SOURCE_CELL",
                }
            )
            continue
        try:
            values.append(_money(source))
        except (TypeError, ValueError):
            return None
    observed_lanes = [
        ordinal
        for ordinal, value in enumerate(values, start=1)
        if value["coefficient"] is not None
    ]
    if not observed_lanes:
        return None
    source_ref = {
        "hierarchy_path_exact": canonical_clone_v1(row.get("hierarchy_path_exact", [])),
        "label_exact": row.get("label_exact"),
        "locator": canonical_clone_v1(region),
        "money_column_ordinals": canonical_clone_v1(money_ordinals),
        "row_id": row.get("row_id", f"r{total_ordinal}"),
        "row_kind": row.get("row_kind"),
        "row_ordinal": total_ordinal,
    }
    return {
        "lane_keys": canonical_clone_v1(lane_axis["lane_keys"]),
        "observed_lane_ordinals": observed_lanes,
        "source_ref": source_ref,
        "values": values,
    }


def _recover_unitless_note_candidate_from_primary_source_result(
    *,
    candidate: dict[str, Any],
    regions: Sequence[dict[str, Any]],
    source_page_json_by_version: Mapping[str, dict[str, Any]],
    repaired_page_json_by_version: Mapping[str, dict[str, Any]],
    selected_page_axis: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Seal only a uniquely matching explicit-unit primary Family-24 result."""

    note = _unitless_note_total_observation(
        candidate=candidate,
        regions=regions,
        page_json_by_version=repaired_page_json_by_version,
    )
    if note is None:
        return candidate, None
    first = regions[0]
    document = {
        key: first[key]
        for key in (
            "document_id",
            "document_ordinal",
            "source_logical_name",
            "source_sha256",
        )
    }
    root_regions, root_pages, repairs = _root_regions(
        document=document,
        selected_page_axis=selected_page_axis,
        page_json_by_version=source_page_json_by_version,
        compiled_specs=compiled_specs,
    )
    matches = []
    for region in root_regions:
        observation = _root_observation(
            region=region,
            page_json_by_version=root_pages,
            selected_page_axis=selected_page_axis,
            compiled_specs=compiled_specs,
            repairs=repairs,
        )
        root_lane_axis = observation.get("table_receipt", {}).get("lane_axis", {})
        if (
            observation.get("status") != READY
            or not same_typed_json_v1(root_lane_axis.get("lane_keys"), note["lane_keys"])
            or any(
                observation["values"][ordinal - 1]["coefficient"]
                != note["values"][ordinal - 1]["coefficient"]
                for ordinal in note["observed_lane_ordinals"]
            )
        ):
            continue
        matches.append((region, observation))
    if len(matches) != 1:
        return candidate, None
    root_region, root_observation = matches[0]
    canonical_unit = root_observation["unit"]
    injected_unit = {"MILLION_VND": "million vnd", "VND": "vnd"}.get(
        canonical_unit
    )
    if injected_unit is None:
        return candidate, None
    private_pages = canonical_clone_v1(repaired_page_json_by_version)
    for region in regions:
        _, table = _source_table(
            private_pages[region["page_json_version_id"]],
            section_id=region["section_id"],
            table_id=region["table_id"],
        )
        if table.get("unit_exact") is not None:
            return candidate, None
        table["unit_exact"] = injected_unit
    recovered = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=regions,
        page_json_by_version=private_pages,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if recovered.get("status") != READY:
        return candidate, None
    receipt_material = {
        "canonical_unit": canonical_unit,
        "magnitude_power10": root_observation["magnitude_power10"],
        "matched_observed_lane_ordinals": canonical_clone_v1(
            note["observed_lane_ordinals"]
        ),
        "note_total_source_ref": canonical_clone_v1(note["source_ref"]),
        "note_total_values": canonical_clone_v1(note["values"]),
        "primary_source_ref": canonical_clone_v1(root_observation["source_ref"]),
        "primary_unit_receipt": canonical_clone_v1(root_observation["unit_receipt"]),
        "primary_values": canonical_clone_v1(root_observation["values"]),
        "rule": (
            "UNIQUE_EXPLICIT_UNIT_PRIMARY_FAMILY24_RESULT_EQUALS_EVERY_"
            "OBSERVED_UNITLESS_NOTE_TOTAL_LANE_ON_EXACT_PERIOD_AXIS"
        ),
    }
    primary_receipt = {
        **receipt_material,
        "receipt_id": "geircfav1:primary-unit:"
        + canonical_json_sha256_v1(receipt_material),
    }
    recovered["closure_receipt"]["document_unit_context"] = canonical_clone_v1(
        candidate.get("closure_receipt", {}).get("document_unit_context")
    )
    root_key = tuple(
        root_region[key]
        for key in ("page_json_version_id", "section_id", "table_id")
    )
    for table_receipt in recovered["closure_receipt"].get("table_receipts", []):
        table_receipt["unit_axis"] = {
            "canonical_unit": canonical_unit,
            "complete": True,
            "document_unit_context_evidence": None,
            "evidence": [],
            "family24_primary_source_result_locator": {
                "page_json_version_id": root_key[0],
                "section_id": root_key[1],
                "table_id": root_key[2],
            },
            "primary_source_unit_receipt_id": primary_receipt["receipt_id"],
            "reasons": [],
            "source": "FAMILY24_PRIMARY_SOURCE_RESULT_OBSERVED_LANE_EXACT_UNIT_CORROBORATION",
            "undeclared_evidence": [],
        }
    return recovered, primary_receipt


def _root_candidate(
    *,
    regions: Sequence[dict[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    selected_page_axis: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    first = regions[0]
    pages, repairs = _document_repairs(
        source_sha256=first["source_sha256"],
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
    )
    observations = [
        _root_observation(
            region=region,
            page_json_by_version=pages,
            selected_page_axis=selected_page_axis,
            compiled_specs=compiled_specs,
            repairs=repairs,
        )
        for region in regions
    ]
    reasons = sorted(
        {
            reason
            for observation in observations
            for reason in observation["reasons"]
        }
    )
    if len(regions) != 1:
        reasons.append("MULTIPLE_SOURCE_VISIBLE_ROOT_POPULATIONS_CONFLICT")
        reasons = sorted(set(reasons))
    mappings = []
    if not reasons:
        observation = observations[0]
        mapping_material = {
            "report_norm_id": compiled_specs["schema"]["family_root_report_norm_id"],
            "role": "FAMILY_ROOT_TOTAL",
            "row_id": observation["source_ref"]["row_id"],
            "source_refs": [observation["source_ref"]],
            "state": "SOURCE_VISIBLE_EXACT_PRIMARY_BALANCE_RESULT",
            "unit": observation["unit"],
            "values": observation["values"],
        }
        mappings = [
            {
                **mapping_material,
                "item_mapping_id": (
                    "gjmthfmv1:item:" + canonical_json_sha256_v1(mapping_material)
                ),
            }
        ]
    adapter_material = {
        "adapter_format_version": ADAPTER_FORMAT_VERSION,
        "observations": [
            {
                "reasons": observation["reasons"],
                "repair_receipts": observation["repair_receipts"],
                "source_ref": observation["source_ref"],
                "table_receipt": observation["table_receipt"],
                "unit_receipt": observation["unit_receipt"],
                "values": observation["values"],
            }
            for observation in observations
        ],
        "shared_engine_claim_boundary": GENERIC_CLAIM_BOUNDARY,
        "source_repair_spec_sha256": compiled_specs[
            "entrusted_investment_risk_capital_source_repair_spec_sha256"
        ],
    }
    closure_receipt = {
        "entrusted_investment_risk_capital_adapter_receipt": {
            **adapter_material,
            "adapter_receipt_id": (
                "geircfav1:receipt:" + canonical_json_sha256_v1(adapter_material)
            ),
        },
        "query_receipt": build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            regions
        ),
        "rule": "EXACT_SOURCE_VISIBLE_PRIMARY_BALANCE_RESULT_ONLY",
    }
    material = {
        "claim_boundary": ADAPTER_CLAIM_BOUNDARY,
        "closure_receipt": closure_receipt,
        "component_regions": canonical_clone_v1(regions),
        "document_id": first["document_id"],
        "family_id": FAMILY_ID,
        "mappings": mappings,
        "page_json_version_id": first["page_json_version_id"],
        "physical_page": first["physical_page"],
        "reasons": reasons,
        "section_id": first["section_id"],
        "source_logical_name": first["source_logical_name"],
        "source_sha256": first["source_sha256"],
        "status": READY if mappings and not reasons else UNRESOLVED,
        "table_id": first["table_id"],
    }
    return {
        **material,
        "candidate_id": "gjmthfcv1:candidate:" + canonical_json_sha256_v1(material),
    }


def evaluate_gemini_json_entrusted_investment_risk_capital_family_cluster_v1(
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    selected_page_axis: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate a note cluster or one exact primary source-result population."""

    if compiled_specs.get("topology", {}).get("family_id") != FAMILY_ID:
        raise _error("Family-24 adapter received another family")
    if type(regions) not in {list, tuple} or not regions:
        raise _error("Family-24 region axis is invalid")
    pages, _ = _document_repairs(
        source_sha256=regions[0]["source_sha256"],
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
    )
    root_flags = []
    for region in regions:
        section, table = _source_table(
            pages[region["page_json_version_id"]],
            section_id=region["section_id"],
            table_id=region["table_id"],
        )
        root_flags.append(
            section.get("statement_type") == "BALANCE_SHEET"
            and section.get("content_kind") == "PRIMARY_STATEMENT"
            and any(
                type(row) is dict
                and _is_parent_label(row.get("label_exact"), compiled_specs=compiled_specs)
                for row in table.get("rows", [])
            )
        )
    expected_receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        regions
    )
    if not same_typed_json_v1(query_receipt, expected_receipt):
        raise _error("Family-24 query receipt does not bind regions")
    if all(root_flags):
        return _root_candidate(
            regions=regions,
            page_json_by_version=page_json_by_version,
            selected_page_axis=selected_page_axis,
            compiled_specs=compiled_specs,
        )
    if any(root_flags):
        raise _error("Family-24 primary and note populations cannot be mixed")
    raw = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=regions,
        page_json_by_version=pages,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    raw, primary_source_unit_receipt = (
        _recover_unitless_note_candidate_from_primary_source_result(
            candidate=canonical_clone_v1(raw),
            regions=regions,
            source_page_json_by_version=page_json_by_version,
            repaired_page_json_by_version=pages,
            selected_page_axis=selected_page_axis,
            compiled_specs=compiled_specs,
            query_receipt=query_receipt,
        )
    )
    return _reseal_note_candidate(
        canonical_clone_v1(raw),
        compiled_specs=compiled_specs,
        primary_source_unit_receipt=primary_source_unit_receipt,
    )


def build_gemini_json_entrusted_investment_risk_capital_trials_v1(
    *,
    indexed_query_evidence: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Evaluate every accepted cluster and preserve the exhaustive disposition axis."""

    evidence = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
    pages_by_document: dict[int, list[dict[str, Any]]] = {}
    for page in evidence["selected_page_axis"]:
        pages_by_document.setdefault(page["document_ordinal"], []).append(page)
    trials = []
    for disposition in evidence["candidate_dispositions"]:
        cluster = disposition["cluster"]
        document_ordinal = disposition["document_ordinal"]
        candidates = []
        mappings = []
        reasons = []
        selected_candidate_id = None
        status = disposition["disposition"]
        if status == READY:
            regions = cluster["component_regions"]
            candidate = evaluate_gemini_json_entrusted_investment_risk_capital_family_cluster_v1(
                regions=regions,
                page_json_by_version=page_json_by_document[document_ordinal],
                selected_page_axis=pages_by_document[document_ordinal],
                compiled_specs=compiled_specs,
                query_receipt=(
                    build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
                        regions
                    )
                ),
            )
            candidates = [candidate]
            status = candidate["status"]
            if status == READY:
                mappings = candidate["mappings"]
                selected_candidate_id = candidate["candidate_id"]
            else:
                reasons = candidate["reasons"]
        elif status == UNRESOLVED:
            reasons = cluster["reasons"]
        trials.append(
            {
                "candidate_count": len(candidates),
                "candidates": candidates,
                "document_ordinal": document_ordinal,
                "mappings": mappings,
                "reasons": reasons,
                "selected_candidate_id": selected_candidate_id,
                "source_logical_name": disposition["source_logical_name"],
                "source_sha256": disposition["source_sha256"],
                "status": status,
            }
        )
    return validate_gemini_json_multitable_hierarchical_sweep_query_bindings_v1(
        trials=trials,
        indexed_query_evidence=evidence,
        compiled_specs=compiled_specs,
    )


def validate_gemini_json_entrusted_investment_risk_capital_candidate_replay_v1(
    value: Any,
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    selected_page_axis: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    expected = evaluate_gemini_json_entrusted_investment_risk_capital_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        selected_page_axis=selected_page_axis,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if type(value) is not dict or not same_typed_json_v1(value, expected):
        raise _error("Family-24 candidate replay drifted")
    return expected


def validate_gemini_json_entrusted_investment_risk_capital_replay_v1(
    *,
    base_indexed_query_evidence: Any,
    indexed_query_evidence: Any,
    trials: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    replayed = build_gemini_json_entrusted_investment_risk_capital_indexed_query_evidence_v1(
        base_indexed_query_evidence=base_indexed_query_evidence,
        page_json_by_document=page_json_by_document,
        compiled_specs=compiled_specs,
    )
    if not same_typed_json_v1(indexed_query_evidence, replayed):
        raise _error("Family-24 indexed query evidence replay drifted")
    expected = build_gemini_json_entrusted_investment_risk_capital_trials_v1(
        indexed_query_evidence=replayed,
        page_json_by_document=page_json_by_document,
        compiled_specs=compiled_specs,
    )
    if type(trials) is not list or not same_typed_json_v1(trials, expected):
        raise _error("Family-24 sweep replay drifted")
    return expected
