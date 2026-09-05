"""Family-25 adapter for exact structural and source-observation receipts.

The shared multi-table hierarchical evaluator remains authoritative for owner
fencing, role classification, period and unit axes, arithmetic closure, and
schema bindings.  This adapter may recover an exact local owner surface or one
unique blank owner printed as the first row inside its table, make a printed
face-value hierarchy wrapper transparent, restore an exact printed tenor
carrier omitted from child paths, or project one unshadowed primary-statement
root.  It may also restore a PDF-visible accounting dash that the immutable
selected Gemini JSON recorded as ``null``; each such repair is bound to the
PDF, page JSON, table cell, deterministic full-page render, and RGB crop.  No
structural receipt chooses a value, and blank cells are never zeroed.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.evaluation.gemini_json_customer_deposit_family_v1 import (
    _document_unit_context_axis,
    _two_period_axis,
)
from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import (
    _normalized,
    _without_leading_ordinal,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    CLAIM_BOUNDARY as GENERIC_CLAIM_BOUNDARY,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    classify_gemini_json_multitable_hierarchical_table_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
    validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
)
from bctc_ai.evaluation.gemini_json_other_long_term_investments_family_v1 import (
    _semantic_period_roles,
    _source_money,
    _surface_dates,
)
from bctc_ai.evaluation.source_observation_lane_math_v1 import (
    observed_source_coefficient_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FAMILY_ID = "ISSUED_VALUABLE_PAPERS"
ADAPTER_FORMAT_VERSION = "GEMINI_JSON_ISSUED_VALUABLE_PAPERS_FAMILY_ADAPTER_V1"
LOCAL_OWNER_QUERY_RECEIPT_FORMAT_VERSION = (
    "GEMINI_JSON_ISSUED_VALUABLE_PAPERS_LOCAL_OWNER_QUERY_RECEIPT_V1"
)
INTERNAL_ROOT_ROW_QUERY_RECEIPT_FORMAT_VERSION = (
    "GEMINI_JSON_ISSUED_VALUABLE_PAPERS_INTERNAL_ROOT_ROW_QUERY_RECEIPT_V1"
)
FACE_VALUE_WRAPPER_RECEIPT_FORMAT_VERSION = (
    "GEMINI_JSON_ISSUED_VALUABLE_PAPERS_FACE_VALUE_WRAPPER_RECEIPT_V1"
)
TENOR_INSTRUMENT_PROJECTION_RECEIPT_FORMAT_VERSION = (
    "GEMINI_JSON_ISSUED_VALUABLE_PAPERS_TENOR_INSTRUMENT_PROJECTION_RECEIPT_V1"
)
VALIDATION_ROW_PROJECTION_RECEIPT_FORMAT_VERSION = (
    "GEMINI_JSON_ISSUED_VALUABLE_PAPERS_VALIDATION_ROW_PROJECTION_RECEIPT_V1"
)
TRANSPOSED_AXIS_PROJECTION_RECEIPT_FORMAT_VERSION = (
    "GEMINI_JSON_ISSUED_VALUABLE_PAPERS_TRANSPOSED_AXIS_PROJECTION_RECEIPT_V1"
)
MATURITY_AND_VALIDATION_PROJECTION_RECEIPT_FORMAT_VERSION = (
    "GEMINI_JSON_ISSUED_VALUABLE_PAPERS_MATURITY_AND_VALIDATION_PROJECTION_RECEIPT_V1"
)
ALTERNATE_PRESENTATION_PRUNE_RECEIPT_FORMAT_VERSION = (
    "GEMINI_JSON_ISSUED_VALUABLE_PAPERS_ALTERNATE_PRESENTATION_PRUNE_RECEIPT_V1"
)
PRIMARY_ROOT_QUERY_RECEIPT_FORMAT_VERSION = (
    "GEMINI_JSON_ISSUED_VALUABLE_PAPERS_PRIMARY_ROOT_QUERY_RECEIPT_V1"
)
VALIDATION_ONLY_LEADING_PRUNE_RECEIPT_FORMAT_VERSION = (
    "GEMINI_JSON_ISSUED_VALUABLE_PAPERS_VALIDATION_ONLY_LEADING_PRUNE_RECEIPT_V1"
)
ADJACENT_RECEIVER_QUERY_RECEIPT_FORMAT_VERSION = (
    "GEMINI_JSON_ISSUED_VALUABLE_PAPERS_ADJACENT_RECEIVER_QUERY_RECEIPT_V1"
)
EMPTY_OWNER_CONTINUATION_QUERY_RECEIPT_FORMAT_VERSION = (
    "GEMINI_JSON_ISSUED_VALUABLE_PAPERS_EMPTY_OWNER_CONTINUATION_QUERY_RECEIPT_V1"
)
ADJACENT_SOURCE_SYNTAX_PROJECTION_RECEIPT_FORMAT_VERSION = (
    "GEMINI_JSON_ISSUED_VALUABLE_PAPERS_ADJACENT_SOURCE_SYNTAX_PROJECTION_RECEIPT_V1"
)
SOURCE_REPAIR_FORMAT_VERSION = (
    "GEMINI_JSON_ISSUED_VALUABLE_PAPERS_AUTHENTICATED_SOURCE_REPAIR_SPEC_V1"
)
ADAPTER_CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_FAMILY25_EXACT_LOCAL_OR_INTERNAL_ROOT_"
    "ROW_OWNER_FACE_VALUE_WRAPPER_TENOR_CARRIER_AND_UNSHADOWED_PRIMARY_ROOT_"
    "STRUCTURAL_RECEIPTS_GENERIC_ROLE_PERIOD_UNIT_AND_ACCOUNTING_CLOSURE_WITH_"
    "PDF_VISIBLE_DASH_OVERLAY_PROVED_BY_AUTHENTICATED_FULL_PAGE_AND_CELL_CROP_"
    "SCHEMA_MAPPING_PROPOSAL_ONLY_NO_SOURCE_MUTATION_OCR_PROVIDER_BANK_FILE_"
    "YEAR_PAGE_VALUE_ROUTING_NULL_ZERO_BACKSOLVE_CANONICAL_OR_EXPORT_AUTHORITY"
)

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_PAGE_VERSION = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_SECTION_ID = re.compile(r"s[1-9][0-9]*\Z")
_TABLE_ID = re.compile(r"t[1-9][0-9]*\Z")
_EXPECTED_BINDINGS = {
    "BOND",
    "BOND_LONG",
    "BOND_MEDIUM",
    "BOND_PRINTED_BELOW_FIVE_YEARS",
    "BOND_SHORT",
    "CD_LONG",
    "CD_MEDIUM",
    "CD_PRINTED_OVER_TWELVE_MONTHS",
    "CD_SHORT",
    "CERTIFICATE_OF_DEPOSIT",
    "OTHER_ISSUED_PAPER",
    "PROMISSORY_AND_BOND_LONG",
    "PROMISSORY_AND_BOND_MEDIUM",
    "PROMISSORY_AND_BOND_SHORT",
    "PROMISSORY_AND_BOND_TOTAL",
    "PROMISSORY_LONG",
    "PROMISSORY_MEDIUM",
    "PROMISSORY_NOTE",
    "PROMISSORY_SHORT",
}
_INSTRUMENT_ROLES = frozenset(
    {
        "BOND",
        "CERTIFICATE_OF_DEPOSIT",
        "PROMISSORY_AND_BOND_TOTAL",
        "PROMISSORY_NOTE",
    }
)
_VISIBLE_DASH_TRANSCRIPTION_ARTEFACTS = frozenset({"- 特別", "_"})


class GeminiJsonIssuedValuablePapersFamilyV1Error(ValueError):
    """Family-25 specs, source-repair evidence, or candidate replay drifted."""


def _error(message: str) -> GeminiJsonIssuedValuablePapersFamilyV1Error:
    return GeminiJsonIssuedValuablePapersFamilyV1Error(message)


def _validate_source_repairs(value: Any) -> list[dict[str, Any]]:
    render_contract = {
        "alpha": False,
        "colorspace": "RGB",
        "format": "PNG",
        "render_dpi": 300,
        "renderer": "BCTC_AI_FULL_PDF_PAGE_RENDER_V1_PYMUPDF",
    }
    if (
        type(value) is not dict
        or set(value)
        != {
            "family_id",
            "format_version",
            "policy",
            "render_contract",
            "repair_axis_sha256",
            "repairs",
        }
        or value.get("family_id") != FAMILY_ID
        or value.get("format_version") != SOURCE_REPAIR_FORMAT_VERSION
        or value.get("policy")
        != "ONLY_PDF_VISIBLE_ACCOUNTING_DASH_MISSING_AS_NULL_NO_BLANK_ZERO_INFERENCE"
        or value.get("render_contract") != render_contract
        or type(value.get("repairs")) is not list
    ):
        raise _error("issued-paper authenticated source-repair spec is invalid")
    checked: list[dict[str, Any]] = []
    identities: set[tuple[Any, ...]] = set()
    for repair in value["repairs"]:
        locator = repair.get("locator") if type(repair) is dict else None
        source = repair.get("source") if type(repair) is dict else None
        render = repair.get("render") if type(repair) is dict else None
        crop = repair.get("crop_evidence") if type(repair) is dict else None
        bbox = crop.get("bbox_pixels_xyxy") if type(crop) is dict else None
        if (
            type(repair) is not dict
            or set(repair)
            != {
                "after_exact",
                "before_exact",
                "crop_evidence",
                "locator",
                "observed_pdf_glyph",
                "repair_id",
                "repair_kind",
                "render",
                "source",
            }
            or repair.get("repair_kind") != "MONEY_CELL_VISIBLE_DASH"
            or repair.get("before_exact") is not None
            or repair.get("after_exact") != "-"
            or repair.get("observed_pdf_glyph") != "-"
            or type(locator) is not dict
            or set(locator)
            != {
                "column_ordinal",
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
            or type(locator.get("column_ordinal")) is not int
            or locator["column_ordinal"] <= 0
            or _SECTION_ID.fullmatch(locator.get("section_id", "")) is None
            or _TABLE_ID.fullmatch(locator.get("table_id", "")) is None
            or type(source) is not dict
            or set(source)
            != {"source_logical_name", "source_sha256", "source_size_bytes"}
            or type(source.get("source_logical_name")) is not str
            or not source["source_logical_name"]
            or source["source_logical_name"].startswith("/")
            or ".." in source["source_logical_name"].split("/")
            or _SHA256.fullmatch(source.get("source_sha256", "")) is None
            or type(source.get("source_size_bytes")) is not int
            or source["source_size_bytes"] <= 0
            or type(render) is not dict
            or set(render)
            != {
                "image_sha256",
                "image_size_bytes",
                "media_type",
                "physical_page",
                "pixel_height",
                "pixel_width",
                "render_dpi",
                "render_receipt_sha256",
            }
            or render.get("physical_page") != locator["physical_page"]
            or render.get("render_dpi") != 300
            or render.get("media_type") != "image/png"
            or _SHA256.fullmatch(render.get("image_sha256", "")) is None
            or _SHA256.fullmatch(render.get("render_receipt_sha256", "")) is None
            or any(
                type(render.get(field)) is not int or render[field] <= 0
                for field in ("image_size_bytes", "pixel_height", "pixel_width")
            )
            or type(crop) is not dict
            or set(crop)
            != {"bbox_pixels_xyxy", "pixel_height", "pixel_width", "rgb_sha256"}
            or type(bbox) is not list
            or len(bbox) != 4
            or any(type(coordinate) is not int for coordinate in bbox)
            or not (0 <= bbox[0] < bbox[2] <= render["pixel_width"])
            or not (0 <= bbox[1] < bbox[3] <= render["pixel_height"])
            or crop.get("pixel_width") != bbox[2] - bbox[0]
            or crop.get("pixel_height") != bbox[3] - bbox[1]
            or _SHA256.fullmatch(crop.get("rgb_sha256", "")) is None
        ):
            raise _error("issued-paper authenticated source repair is invalid")
        material = {
            key: canonical_clone_v1(item)
            for key, item in repair.items()
            if key != "repair_id"
        }
        if repair.get("repair_id") != (
            "gjivpfav1:source-repair:" + canonical_json_sha256_v1(material)
        ):
            raise _error("issued-paper source-repair identity drifted")
        identity = (
            source["source_sha256"],
            locator["page_json_version_id"],
            locator["section_id"],
            locator["table_id"],
            locator["row_ordinal"],
            locator["column_ordinal"],
        )
        if identity in identities:
            raise _error("issued-paper source-repair cell axis is duplicate")
        identities.add(identity)
        checked.append(canonical_clone_v1(repair))
    if value.get("repair_axis_sha256") != canonical_json_sha256_v1(checked):
        raise _error("issued-paper source-repair axis seal drifted")
    return checked


def bind_gemini_json_issued_valuable_papers_source_repairs_v1(
    compiled_specs: Any, source_repair_spec: Any
) -> dict[str, Any]:
    """Bind exact PDF observations to a compiled generic Family-25 spec."""

    if type(compiled_specs) is not dict:
        raise _error("issued-paper compiled family frontier is invalid")
    compiled = canonical_clone_v1(compiled_specs)
    if (
        compiled.get("topology", {}).get("family_id") != FAMILY_ID
        or compiled.get("evaluation", {}).get("family_id") != FAMILY_ID
        or compiled.get("schema", {}).get("family_id") != FAMILY_ID
        or set(compiled.get("bindings", {})) != _EXPECTED_BINDINGS
        or {
            item["canonical_unit"]
            for item in compiled.get("unit_bindings", [])
            if item.get("accepted") is True
        }
        != {"MILLION_VND", "VND"}
    ):
        raise _error("issued-paper declarative family frontier is invalid")
    compiled["issued_valuable_papers_source_repairs"] = _validate_source_repairs(
        source_repair_spec
    )
    compiled["issued_valuable_papers_source_repair_spec_sha256"] = (
        canonical_json_sha256_v1(source_repair_spec)
    )
    compiled["issued_valuable_papers_adapter_format_version"] = ADAPTER_FORMAT_VERSION
    return compiled


def compile_gemini_json_issued_valuable_papers_family_specs_v1(
    topology_spec: Any,
    evaluation_spec: Any,
    schema_binding_spec: Any,
    source_repair_spec: Any,
) -> dict[str, Any]:
    """Compile the declarative Family-25 specs and bind source repairs."""

    compiled = compile_gemini_json_multitable_hierarchical_family_specs_v1(
        topology_spec, evaluation_spec, schema_binding_spec
    )
    return bind_gemini_json_issued_valuable_papers_source_repairs_v1(
        compiled, source_repair_spec
    )


def build_gemini_json_issued_valuable_papers_region_query_receipt_v1(
    regions: Any,
) -> dict[str, Any]:
    """Seal the unchanged shared query-region axis."""

    return build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)


def _exact_owner_alias(
    value: Any, *, compiled_specs: Mapping[str, Any]
) -> str | None:
    folded = _without_leading_ordinal(_normalized(value))
    matches = [
        alias
        for alias in compiled_specs["query_policy"]["owner_aliases"]
        if folded == _normalized(alias)
    ]
    return matches[0] if len(matches) == 1 else None


def _exact_boundary_alias(
    value: Any, *, compiled_specs: Mapping[str, Any]
) -> str | None:
    folded = _without_leading_ordinal(_normalized(value))
    aliases = {
        *compiled_specs["query_policy"]["hard_negative_aliases"],
        *compiled_specs["query_policy"]["reset_aliases"],
    }
    matches = [alias for alias in aliases if folded == _normalized(alias)]
    return matches[0] if len(matches) == 1 else None


def _exact_parent_alias(
    value: Any, *, compiled_specs: Mapping[str, Any]
) -> str | None:
    folded = _without_leading_ordinal(_normalized(value))
    matches = [
        _normalized(alias)
        for alias in compiled_specs["topology"]["parent"]["aliases"]
        if folded == _normalized(alias)
    ]
    return matches[0] if len(matches) == 1 else None


def _money_ordinals(table: Mapping[str, Any]) -> list[int]:
    columns = table.get("columns")
    if type(columns) is not list:
        return []
    return [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]


def _table_from_inventory(
    *,
    inventory_item: Mapping[str, Any],
    page_json_by_version: Mapping[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    page = page_json_by_version.get(inventory_item.get("page_json_version_id"))
    if type(page) is not dict:
        return None
    try:
        section = page["sections"][int(inventory_item["section_id"][1:]) - 1]
        table = section["tables"][int(inventory_item["table_id"][1:]) - 1]
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    if type(section) is not dict or type(table) is not dict:
        return None
    return section, table


def _primary_statement_exact_root_projection_v1(
    *,
    region: Mapping[str, Any],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]] | None:
    """Project one exact balance-sheet family-root row for generic evaluation.

    The generic query correctly treats primary statements as controls while it
    searches for note detail.  Family 25 also has a schema binding for the
    directly printed statement result.  This projection is restricted to one
    exact declared parent row in one balance-sheet table and never selects a
    value, completes a blank, or imports a neighbouring liability row.
    """

    try:
        build_gemini_json_multitable_hierarchical_region_query_receipt_v1([region])
    except ValueError:
        return None
    page = page_json_by_version.get(region.get("page_json_version_id"))
    if type(page) is not dict or page.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
        return None
    try:
        section = page["sections"][int(region["section_id"][1:]) - 1]
        table = section["tables"][int(region["table_id"][1:]) - 1]
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    if (
        type(section) is not dict
        or type(table) is not dict
        or section.get("content_kind") != "PRIMARY_STATEMENT"
        or section.get("statement_type") != "BALANCE_SHEET"
    ):
        return None
    money_ordinals = _money_ordinals(table)
    period_axis = _two_period_axis(table)
    rows = table.get("rows")
    if (
        len(money_ordinals) != 2
        or period_axis.get("complete") is not True
        or period_axis.get("money_column_ordinals") != money_ordinals
        or type(rows) is not list
    ):
        return None
    matches = []
    for row_ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict:
            continue
        alias = _exact_parent_alias(
            row.get("label_exact"), compiled_specs=compiled_specs
        )
        values = row.get("values_exact")
        hierarchy = row.get("hierarchy_path_exact")
        if alias is None:
            continue
        if (
            row.get("row_kind") not in {"ITEM", "GROUP", "SUBTOTAL", "TOTAL"}
            or type(values) is not list
            or any(column_ordinal > len(values) for column_ordinal in money_ordinals)
            or type(hierarchy) is not list
            or not hierarchy
            or _without_leading_ordinal(_normalized(hierarchy[-1])) != alias
        ):
            return None
        matches.append((row_ordinal, row, alias))
    if len(matches) != 1:
        return None
    row_ordinal, source_row, alias = matches[0]
    locator = {
        key: region[key]
        for key in (
            "page_json_version_id",
            "physical_page",
            "section_id",
            "table_id",
        )
    }
    material = {
        "document_id": region["document_id"],
        "document_ordinal": region["document_ordinal"],
        "format_version": PRIMARY_ROOT_QUERY_RECEIPT_FORMAT_VERSION,
        "locator": locator,
        "money_column_ordinals": money_ordinals,
        "non_primary_direct_family_candidate_axis": [],
        "period_axis": canonical_clone_v1(period_axis),
        "projection": {
            "after_page_status": "FINANCIAL_NOTE_CONTENT",
            "after_row_kind": "TOTAL",
            "after_section_content_kind": "FINANCIAL_NOTE",
            "after_section_statement_type": "NOT_APPLICABLE",
            "after_table_continuation": "NONE",
            "before_page_status": page["status"],
            "before_row_kind": source_row["row_kind"],
            "before_section_content_kind": section["content_kind"],
            "before_section_statement_type": section["statement_type"],
            "before_table_continuation": table.get("continuation"),
        },
        "root_alias_normalized": alias,
        "root_row": {
            "hierarchy_path_exact": canonical_clone_v1(
                source_row["hierarchy_path_exact"]
            ),
            "label_exact": source_row["label_exact"],
            "row_kind": source_row["row_kind"],
            "row_ordinal": row_ordinal,
            "values_exact": canonical_clone_v1(source_row["values_exact"]),
        },
        "rule": (
            "ONE_EXACT_DECLARED_FAMILY_ROOT_ROW_IN_ONE_PRIMARY_BALANCE_SHEET_"
            "TABLE_ONLY_WHEN_NO_UNTYPED_NON_PRIMARY_DIRECT_FAMILY_CANDIDATE_"
            "PROJECTED_WITHOUT_VALUE_SELECTION_OR_BLANK_COMPLETION"
        ),
        "source_logical_name": region["source_logical_name"],
        "source_sha256": region["source_sha256"],
        "table_unit_exact": table.get("unit_exact"),
    }
    receipt = {
        **material,
        "primary_root_query_receipt_id": (
            "gjivpprqrv1:receipt:" + canonical_json_sha256_v1(material)
        ),
    }
    pages = {
        page_json_version_id: canonical_clone_v1(page_json)
        for page_json_version_id, page_json in page_json_by_version.items()
    }
    projected_page = pages[region["page_json_version_id"]]
    projected_page["status"] = "FINANCIAL_NOTE_CONTENT"
    projected_section = projected_page["sections"][
        int(region["section_id"][1:]) - 1
    ]
    projected_section["content_kind"] = "FINANCIAL_NOTE"
    projected_section["statement_type"] = "NOT_APPLICABLE"
    projected_table = projected_section["tables"][int(region["table_id"][1:]) - 1]
    projected_row = canonical_clone_v1(projected_table["rows"][row_ordinal - 1])
    projected_row["row_kind"] = "TOTAL"
    projected_table["rows"] = [projected_row]
    projected_table["continuation"] = "NONE"
    return pages, receipt


def _non_primary_direct_family_candidates_v1(
    *,
    inventory: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """List untyped note tables that could contain schema-bound Family-25 detail.

    Validation-only roles deliberately have broad labels such as ``Bằng VND``
    and tenor buckets.  They close an already selected Family-25 table, but do
    not by themselves identify a competing direct schema source.  Treating one
    of those labels in an unrelated note as a veto would suppress an exact
    primary-statement Family-25 root.
    """

    candidates = []
    direct_roles = set(compiled_specs["root_component_roles"]) - set(
        compiled_specs["validation_only_roles"]
    )
    for item in inventory:
        classification = item.get("classification")
        if type(classification) is not dict:
            continue
        resolved = _table_from_inventory(
            inventory_item=item, page_json_by_version=page_json_by_version
        )
        page = page_json_by_version.get(item.get("page_json_version_id"))
        if resolved is None or type(page) is not dict:
            continue
        section, _table = resolved
        if (
            page.get("status") == "PRIMARY_FINANCIAL_STATEMENT"
            or section.get("content_kind") != "FINANCIAL_NOTE"
            or classification.get("typed_control_disposition") is not None
        ):
            continue
        role_hits = classification.get("role_hits")
        observed_roles = {
            *(hit.get("role") for hit in role_hits if type(hit) is dict),
            *(classification.get("context_roles") or []),
        } - {None} if type(role_hits) is list else set()
        if not classification.get("family_root_row_ordinals") and not (
            observed_roles & direct_roles
        ):
            continue
        candidates.append(
            {
                "classification_id": classification.get("classification_id"),
                "family_root_row_ordinals": canonical_clone_v1(
                    classification.get("family_root_row_ordinals")
                ),
                "locator": {
                    key: item[key]
                    for key in (
                        "page_json_version_id",
                        "physical_page",
                        "section_id",
                        "table_id",
                    )
                },
                "observed_root_component_roles": sorted(observed_roles & direct_roles),
            }
        )
    return candidates


def _primary_statement_exact_root_query_recovery_v1(
    *,
    cluster: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Recover one primary root only when no direct note candidate exists."""

    if cluster.get("status") != "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY":
        return None
    inventory = cluster.get("declared_money_table_inventory")
    if type(inventory) is not list:
        return None
    root_items = [
        item
        for item in inventory
        if type(item) is dict
        and type(item.get("classification")) is dict
        and item["classification"].get("typed_control_disposition")
        == "PRIMARY_FINANCIAL_STATEMENT_SUMMARY"
        and len(item["classification"].get("family_root_row_ordinals", [])) == 1
    ]
    if len(root_items) != 1:
        return None
    if _non_primary_direct_family_candidates_v1(
        inventory=inventory,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
    ):
        return None
    item = root_items[0]
    selected = [
        page
        for page in selected_page_axis
        if all(
            page.get(field) == cluster.get(field)
            for field in (
                "document_id",
                "document_ordinal",
                "source_logical_name",
                "source_sha256",
            )
        )
        and page.get("page_json_version_id") == item.get("page_json_version_id")
        and page.get("physical_page") == item.get("physical_page")
    ]
    if len(selected) != 1:
        return None
    classification = item["classification"]
    region = {
        "component_roles": [],
        "document_id": cluster["document_id"],
        "document_ordinal": cluster["document_ordinal"],
        "fragment_ordinal": 1,
        "page_json_version_id": item["page_json_version_id"],
        "physical_page": item["physical_page"],
        "section_id": item["section_id"],
        "selected_page_ordinal": selected[0]["selected_page_ordinal"],
        "source_logical_name": cluster["source_logical_name"],
        "source_sha256": cluster["source_sha256"],
        "table_id": item["table_id"],
    }
    projected = _primary_statement_exact_root_projection_v1(
        region=region,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
    )
    if projected is None:
        return None
    _pages, receipt = projected
    if (
        classification.get("family_root_row_ordinals")
        != [receipt["root_row"]["row_ordinal"]]
        or classification.get("money_column_ordinals")
        != receipt["money_column_ordinals"]
        or classification.get("ambiguous_rows") != []
    ):
        return None
    return region, receipt


def _apply_primary_root_projection_receipt_v1(
    *,
    page_json_by_version: Mapping[str, dict[str, Any]],
    receipt: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Apply only the structural projection sealed by an exact-root receipt."""

    pages = {
        page_json_version_id: canonical_clone_v1(page_json)
        for page_json_version_id, page_json in page_json_by_version.items()
    }
    locator = receipt["locator"]
    page = pages.get(locator["page_json_version_id"])
    try:
        section = page["sections"][int(locator["section_id"][1:]) - 1]  # type: ignore[index]
        table = section["tables"][int(locator["table_id"][1:]) - 1]
        row_ordinal = receipt["root_row"]["row_ordinal"]
        row = table["rows"][row_ordinal - 1]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise _error("issued-paper primary-root projection locator drifted") from exc
    if (
        page.get("status") != receipt["projection"]["before_page_status"]
        or section.get("content_kind")
        != receipt["projection"]["before_section_content_kind"]
        or section.get("statement_type")
        != receipt["projection"]["before_section_statement_type"]
        or table.get("continuation")
        != receipt["projection"]["before_table_continuation"]
        or row.get("row_kind") != receipt["root_row"]["row_kind"]
        or row.get("label_exact") != receipt["root_row"]["label_exact"]
        or row.get("hierarchy_path_exact")
        != receipt["root_row"]["hierarchy_path_exact"]
        or row.get("values_exact") != receipt["root_row"]["values_exact"]
    ):
        raise _error("issued-paper primary-root projection source shape drifted")
    page["status"] = receipt["projection"]["after_page_status"]
    section["content_kind"] = receipt["projection"]["after_section_content_kind"]
    section["statement_type"] = receipt["projection"]["after_section_statement_type"]
    projected_row = canonical_clone_v1(row)
    projected_row["row_kind"] = receipt["projection"]["after_row_kind"]
    table["rows"] = [projected_row]
    table["continuation"] = receipt["projection"]["after_table_continuation"]
    return pages


def _restore_primary_root_mapping_source_refs_v1(
    candidate: dict[str, Any], *, receipt: Mapping[str, Any]
) -> None:
    """Restore projected r1 references to the immutable source row identity."""

    original = receipt["root_row"]
    locator = receipt["locator"]
    for mapping in candidate.get("mappings", []):
        refs = mapping.get("source_refs") if type(mapping) is dict else None
        if type(refs) is not list or not refs:
            raise _error("issued-paper projected root mapping source is absent")
        for source_ref in refs:
            ref_locator = source_ref.get("locator") if type(source_ref) is dict else None
            if (
                type(ref_locator) is not dict
                or any(
                    ref_locator.get(field) != locator[field]
                    for field in (
                        "page_json_version_id",
                        "physical_page",
                        "section_id",
                        "table_id",
                    )
                )
                or source_ref.get("row_ordinal") != 1
            ):
                raise _error("issued-paper projected root mapping source drifted")
            source_ref["row_id"] = f"r{original['row_ordinal']}"
            source_ref["row_kind"] = original["row_kind"]
            source_ref["row_ordinal"] = original["row_ordinal"]
        if mapping.get("row_id") == "r1":
            mapping["row_id"] = f"r{original['row_ordinal']}"
        mapping_material = {
            key: mapping[key] for key in mapping if key != "item_mapping_id"
        }
        mapping["item_mapping_id"] = (
            "gjmthfmv1:item:" + canonical_json_sha256_v1(mapping_material)
        )


def _local_owner_query_recovery_v1(
    *,
    cluster: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Recover one exact local owner whose sole money table is the family note.

    The source store deliberately omits narrative owner surfaces for this
    family.  A recovery is therefore restricted to one financial-note section
    containing exactly one MONEY table, one exact owner string, a declared
    root component, and one terminal printed total.  No value participates in
    choosing the table, and an intervening hard/reset surface vetoes recovery.
    """

    if cluster.get("reasons") not in ([], ["COMPLETE_OWNER_CLUSTER_NOT_RESOLVED"]):
        return None
    inventory = cluster.get("declared_money_table_inventory")
    if type(inventory) is not list:
        return None
    page_axis = {
        item.get("page_json_version_id"): item
        for item in selected_page_axis
        if type(item) is dict
        and item.get("document_ordinal") == cluster.get("document_ordinal")
    }
    candidates = []
    for item in inventory:
        if type(item) is not dict or type(item.get("classification")) is not dict:
            continue
        resolved = _table_from_inventory(
            inventory_item=item, page_json_by_version=page_json_by_version
        )
        axis_item = page_axis.get(item.get("page_json_version_id"))
        page = page_json_by_version.get(item.get("page_json_version_id"))
        if resolved is None or type(axis_item) is not dict or type(page) is not dict:
            continue
        section, table = resolved
        classification = item["classification"]
        rows = table.get("rows")
        total_rows = classification.get("total_rows")
        role_hits = classification.get("role_hits")
        roles = sorted(
            {
                *(hit.get("role") for hit in role_hits if type(hit) is dict),
                *(classification.get("context_roles") or []),
            }
            - {None}
        ) if type(role_hits) is list else []
        root_roles = set(roles).intersection(compiled_specs["root_component_roles"])

        owner_surfaces: list[dict[str, Any]] = [
            {
                "source_kind": "SECTION_TITLE",
                "source_exact": section.get("title_exact"),
                "surface_ordinal": 1,
            }
        ]
        narratives = section.get("narratives_exact")
        if type(narratives) is list:
            owner_surfaces.extend(
                {
                    "source_kind": "SECTION_NARRATIVE",
                    "source_exact": source,
                    "surface_ordinal": ordinal,
                }
                for ordinal, source in enumerate(narratives, start=1)
            )
        owner_surfaces.append(
            {
                "source_kind": "TABLE_TITLE",
                "source_exact": table.get("title_exact"),
                "surface_ordinal": int(item["table_id"][1:]),
            }
        )
        surfaces = canonical_clone_v1(owner_surfaces[:-1])
        surfaces.extend(
            {
                "source_kind": "TABLE_TITLE",
                "source_exact": candidate.get("title_exact"),
                "surface_ordinal": ordinal,
            }
            for ordinal, candidate in enumerate(section.get("tables") or [], start=1)
            if type(candidate) is dict
        )
        owner_matches = [
            {**surface, "alias": alias}
            for surface in owner_surfaces
            if (
                alias := _exact_owner_alias(
                    surface["source_exact"], compiled_specs=compiled_specs
                )
            )
            is not None
        ]
        reset_matches = [
            {**surface, "alias": alias}
            for surface in surfaces
            if (
                alias := _exact_boundary_alias(
                    surface["source_exact"], compiled_specs=compiled_specs
                )
            )
            is not None
        ]
        same_section_money_tables = [
            candidate
            for candidate in inventory
            if type(candidate) is dict
            and candidate.get("page_json_version_id") == item.get("page_json_version_id")
            and candidate.get("section_id") == item.get("section_id")
            and type(candidate.get("classification")) is dict
            and candidate["classification"].get("money_column_ordinals")
        ]
        terminal_total = (
            [
                {
                    "row_kind": "TOTAL",
                    "row_ordinal": len(rows),
                    "source_order": len(rows),
                }
            ]
            if type(rows) is list and rows
            else None
        )
        if (
            page.get("status") != "FINANCIAL_NOTE_CONTENT"
            or section.get("content_kind") != "FINANCIAL_NOTE"
            or section.get("statement_type") != "NOT_APPLICABLE"
            or len(owner_matches) != 1
            or reset_matches
            or len(same_section_money_tables) != 1
            or same_section_money_tables[0] is not item
            or classification.get("layout_orientation")
            != "ROW_ROLES_PERIOD_COLUMNS"
            or classification.get("money_column_ordinals") != [1, 2]
            or classification.get("typed_control_disposition") is not None
            or classification.get("family_presence_anchor_visible") is not True
            or classification.get("ambiguous_rows") != []
            or not roles
            or not root_roles
            or total_rows != terminal_total
        ):
            continue
        candidates.append((item, axis_item, owner_matches[0], roles, surfaces))
    if len(candidates) != 1:
        return None

    item, axis_item, owner, roles, surfaces = candidates[0]
    locator = {
        "page_json_version_id": item["page_json_version_id"],
        "physical_page": item["physical_page"],
        "section_id": item["section_id"],
        "selected_page_ordinal": axis_item["selected_page_ordinal"],
        "table_id": item["table_id"],
    }
    material = {
        "classification_id": item["classification"]["classification_id"],
        "component_roles": roles,
        "document_id": cluster["document_id"],
        "document_ordinal": cluster["document_ordinal"],
        "format_version": LOCAL_OWNER_QUERY_RECEIPT_FORMAT_VERSION,
        "locator": locator,
        "owner_alias": owner["alias"],
        "owner_source_exact": owner["source_exact"],
        "owner_source_kind": owner["source_kind"],
        "owner_surface_ordinal": owner["surface_ordinal"],
        "raw_cluster_id": cluster["cluster_id"],
        "raw_cluster_reasons": canonical_clone_v1(cluster["reasons"]),
        "raw_cluster_status": cluster["status"],
        "rule": (
            "UNIQUE_EXACT_LOCAL_OWNER_SURFACE_SOLE_SECTION_MONEY_TABLE_DECLARED_"
            "ROOT_COMPONENT_TERMINAL_TOTAL_NO_LOCAL_RESET"
        ),
        "section_surface_axis": canonical_clone_v1(surfaces),
        "source_logical_name": cluster["source_logical_name"],
        "source_sha256": cluster["source_sha256"],
    }
    receipt = {
        **material,
        "local_owner_query_receipt_id": (
            "gjivploqrv1:receipt:" + canonical_json_sha256_v1(material)
        ),
    }
    region = {
        "component_roles": roles,
        "document_id": cluster["document_id"],
        "document_ordinal": cluster["document_ordinal"],
        "fragment_ordinal": 1,
        "page_json_version_id": item["page_json_version_id"],
        "physical_page": item["physical_page"],
        "section_id": item["section_id"],
        "selected_page_ordinal": axis_item["selected_page_ordinal"],
        "source_logical_name": cluster["source_logical_name"],
        "source_sha256": cluster["source_sha256"],
        "table_id": item["table_id"],
    }
    return region, receipt


def _internal_root_row_query_recovery_v1(
    *,
    cluster: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Recover one titleless note table whose first row is the exact owner.

    A small source population prints the note number and Family-25 owner as a
    blank structural row inside the table, rather than as a section or table
    heading.  Recovery is deliberately table-local and structural: there must
    be exactly one table in the document with that exact row-1 owner shape, at
    least one declared schema child below it, and exactly one visible TOTAL as
    the final raw row.  The owner cells stay null and never participate in an
    equation or mapping.
    """

    if (
        cluster.get("status")
        != "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
        or cluster.get("reasons") != []
    ):
        return None
    inventory = cluster.get("declared_money_table_inventory")
    if type(inventory) is not list:
        return None

    root_items = []
    for item in inventory:
        if type(item) is not dict or type(item.get("classification")) is not dict:
            continue
        resolved = _table_from_inventory(
            inventory_item=item,
            page_json_by_version=page_json_by_version,
        )
        if resolved is None:
            continue
        section, table = resolved
        rows = table.get("rows")
        if type(rows) is not list or not rows or type(rows[0]) is not dict:
            continue
        root_alias = _exact_parent_alias(
            rows[0].get("label_exact"), compiled_specs=compiled_specs
        )
        if root_alias is not None:
            root_items.append((item, section, table, root_alias))
    if len(root_items) != 1:
        return None

    item, section, table, root_alias = root_items[0]
    classification = item["classification"]
    rows = table["rows"]
    root_row = rows[0]
    terminal_row = rows[-1]
    if type(terminal_row) is not dict:
        return None
    money_ordinals = classification.get("money_column_ordinals")
    root_values = root_row.get("values_exact")
    root_path = root_row.get("hierarchy_path_exact")
    terminal_values = terminal_row.get("values_exact")
    terminal_path = terminal_row.get("hierarchy_path_exact")
    role_hits = classification.get("role_hits")
    total_rows = classification.get("total_rows")
    period_axis = _two_period_axis(table)
    if (
        type(role_hits) is not list
        or type(total_rows) is not list
        or type(root_values) is not list
        or type(root_path) is not list
        or type(terminal_values) is not list
        or type(terminal_path) is not list
    ):
        return None

    output_roles = set(compiled_specs["output_role_order"])
    declared_child_hits = [
        canonical_clone_v1(hit)
        for hit in role_hits
        if type(hit) is dict
        and hit.get("role") in output_roles
        and type(hit.get("row_ordinal")) is int
        and 1 < hit["row_ordinal"] < len(rows)
        and type(rows[hit["row_ordinal"] - 1]) is dict
        and type(rows[hit["row_ordinal"] - 1].get("hierarchy_path_exact")) is list
        and rows[hit["row_ordinal"] - 1]["hierarchy_path_exact"]
        and _without_leading_ordinal(
            _normalized(
                rows[hit["row_ordinal"] - 1]["hierarchy_path_exact"][0]
            )
        )
        == root_alias
    ]
    component_roles = sorted(
        {
            *(hit.get("role") for hit in role_hits if type(hit) is dict),
            *(classification.get("context_roles") or []),
        }
        - {None}
    )
    direct_root_roles = set(compiled_specs["root_component_roles"]) - set(
        compiled_specs["validation_only_roles"]
    )
    terminal_totals = [
        candidate
        for candidate in total_rows
        if type(candidate) is dict and candidate.get("row_kind") == "TOTAL"
    ]
    terminal_path_folded = [
        _without_leading_ordinal(_normalized(value))
        for value in terminal_path
        if _normalized(value)
    ]
    reset_surface_axis: list[dict[str, Any]] = [
        {
            "source_exact": section.get("title_exact"),
            "source_kind": "SECTION_TITLE",
            "surface_ordinal": 1,
        }
    ]
    narratives = section.get("narratives_exact")
    if type(narratives) is list:
        reset_surface_axis.extend(
            {
                "source_exact": source,
                "source_kind": "SECTION_NARRATIVE",
                "surface_ordinal": ordinal,
            }
            for ordinal, source in enumerate(narratives, start=1)
        )
    reset_surface_axis.append(
        {
            "source_exact": table.get("title_exact"),
            "source_kind": "TABLE_TITLE",
            "surface_ordinal": int(item["table_id"][1:]),
        }
    )
    reset_surface_axis.extend(
        {
            "source_exact": row.get("label_exact"),
            "source_kind": "TABLE_ROW",
            "surface_ordinal": row_ordinal,
        }
        for row_ordinal, row in enumerate(rows[1:], start=2)
        if type(row) is dict
    )
    reset_matches = [
        {**surface, "alias": alias}
        for surface in reset_surface_axis
        if (
            alias := _exact_boundary_alias(
                surface["source_exact"], compiled_specs=compiled_specs
            )
        )
        is not None
    ]
    selected = [
        axis_item
        for axis_item in selected_page_axis
        if type(axis_item) is dict
        and all(
            axis_item.get(field) == cluster.get(field)
            for field in (
                "document_id",
                "document_ordinal",
                "source_logical_name",
                "source_sha256",
            )
        )
        and axis_item.get("page_json_version_id")
        == item.get("page_json_version_id")
        and axis_item.get("physical_page") == item.get("physical_page")
    ]
    page = page_json_by_version.get(item.get("page_json_version_id"))
    if (
        type(page) is not dict
        or page.get("status") != "FINANCIAL_NOTE_CONTENT"
        or section.get("content_kind") != "FINANCIAL_NOTE"
        or section.get("statement_type") != "NOT_APPLICABLE"
        or table.get("continuation") != "NONE"
        or classification.get("layout_orientation")
        != "ROW_ROLES_PERIOD_COLUMNS"
        or money_ordinals != [1, 2]
        or period_axis.get("complete") is not True
        or period_axis.get("money_column_ordinals") != money_ordinals
        or classification.get("owner_visible") is not False
        or classification.get("family_presence_anchor_visible") is not True
        or classification.get("family_root_row_ordinals") != [1]
        or classification.get("typed_control_disposition") is not None
        or classification.get("typed_control_conflict_disposition") is not None
        or classification.get("ambiguous_rows") != []
        or reset_matches
        or root_row.get("row_kind") != "GROUP"
        or any(value is not None for value in root_values)
        or len([value for value in root_path if _normalized(value)]) != 1
        or _without_leading_ordinal(_normalized(root_path[-1])) != root_alias
        or not declared_child_hits
        or not (set(component_roles) & direct_root_roles)
        or terminal_row.get("row_kind") != "TOTAL"
        or terminal_totals
        != [
            {
                "row_kind": "TOTAL",
                "row_ordinal": len(rows),
                "source_order": len(rows),
            }
        ]
        or any(
            ordinal > len(terminal_values)
            or type(terminal_values[ordinal - 1]) is not str
            or not terminal_values[ordinal - 1].strip()
            for ordinal in money_ordinals
        )
        or terminal_path_folded
        != [
            root_alias,
            _without_leading_ordinal(_normalized(terminal_row.get("label_exact"))),
        ]
        or terminal_path_folded[-1] not in {"cong", "tong", "tong cong"}
        or len(selected) != 1
    ):
        return None

    locator = {
        "page_json_version_id": item["page_json_version_id"],
        "physical_page": item["physical_page"],
        "section_id": item["section_id"],
        "selected_page_ordinal": selected[0]["selected_page_ordinal"],
        "table_id": item["table_id"],
    }
    root_row_exact = {"row_ordinal": 1, **canonical_clone_v1(root_row)}
    terminal_root_row_exact = {
        "row_ordinal": len(rows),
        **canonical_clone_v1(terminal_row),
    }
    raw_source_row_axis = canonical_clone_v1(rows)
    material = {
        "classification_id": classification["classification_id"],
        "component_roles": component_roles,
        "declared_child_role_hits": declared_child_hits,
        "document_id": cluster["document_id"],
        "document_ordinal": cluster["document_ordinal"],
        "format_version": INTERNAL_ROOT_ROW_QUERY_RECEIPT_FORMAT_VERSION,
        "locator": locator,
        "money_column_ordinals": canonical_clone_v1(money_ordinals),
        "period_axis": canonical_clone_v1(period_axis),
        "raw_cluster_id": cluster["cluster_id"],
        "raw_cluster_reasons": canonical_clone_v1(cluster["reasons"]),
        "raw_cluster_status": cluster["status"],
        "raw_inventory_disposition": item.get("disposition"),
        "raw_source_row_axis": raw_source_row_axis,
        "raw_source_row_axis_sha256": canonical_json_sha256_v1(
            raw_source_row_axis
        ),
        "reset_surface_axis": canonical_clone_v1(reset_surface_axis),
        "root_alias_normalized": root_alias,
        "root_row_exact": root_row_exact,
        "rule": (
            "UNIQUE_TABLE_WITH_EXACT_BLANK_INTERNAL_ROOT_AT_RAW_ROW_ONE_"
            "DECLARED_SCHEMA_CHILD_AND_UNIQUE_TERMINAL_VISIBLE_TOTAL_NO_"
            "AMBIGUITY_RESET_OR_TYPED_CONTROL_NO_OWNER_BLANK_MAPPING"
        ),
        "source_logical_name": cluster["source_logical_name"],
        "source_sha256": cluster["source_sha256"],
        "table_unit_exact": table.get("unit_exact"),
        "terminal_root_row_exact": terminal_root_row_exact,
    }
    receipt = {
        **material,
        "internal_root_row_query_receipt_id": (
            "gjivpirrqrv1:receipt:" + canonical_json_sha256_v1(material)
        ),
    }
    region = {
        "component_roles": component_roles,
        "document_id": cluster["document_id"],
        "document_ordinal": cluster["document_ordinal"],
        "fragment_ordinal": 1,
        "page_json_version_id": item["page_json_version_id"],
        "physical_page": item["physical_page"],
        "section_id": item["section_id"],
        "selected_page_ordinal": selected[0]["selected_page_ordinal"],
        "source_logical_name": cluster["source_logical_name"],
        "source_sha256": cluster["source_sha256"],
        "table_id": item["table_id"],
    }
    return region, receipt


def _prune_numbered_prior_note_validation_only_leading_regions_v1(
    *,
    cluster: Mapping[str, Any],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Remove only validation-only rows captured from the prior numbered note.

    The shared leading-component rule is useful when a printed component table
    precedes its owner heading.  Family 25 also has deliberately broad
    validation labels (currency and tenor labels), which can make the final
    table of numbered note N look like a leading component of owner N+1.  This
    receipt is restricted to the immediately prior numbered note, requires
    every advertised leading region to contain validation-only roles, and
    requires the owner region that remains to expose a schema-bound role.
    """

    if cluster.get("status") != READY:
        return None
    owner = cluster.get("owner_receipt")
    regions = cluster.get("component_regions")
    inventory = cluster.get("declared_money_table_inventory")
    if (
        type(owner) is not dict
        or owner.get("leading_component_rule")
        != "CONTIGUOUS_SAME_PAGE_DECLARED_ROOT_COMPONENT_SUFFIX_BEFORE_OWNER"
        or type(owner.get("leading_component_positions")) is not list
        or not owner["leading_component_positions"]
        or type(owner.get("outline_top_level_number")) is not int
        or type(owner.get("position")) is not list
        or len(owner["position"]) != 3
        or _exact_owner_alias(
            owner.get("source_exact"), compiled_specs=compiled_specs
        )
        is None
        or type(regions) is not list
        or type(inventory) is not list
    ):
        return None
    leading_positions = owner["leading_component_positions"]
    validation_roles = set(compiled_specs["validation_only_roles"])
    direct_roles = set(compiled_specs["root_component_roles"]) - validation_roles
    by_position = {
        (
            region.get("selected_page_ordinal"),
            int(region.get("section_id", "s0")[1:]),
            int(region.get("table_id", "t0")[1:]),
        ): region
        for region in regions
        if type(region) is dict
        and _SECTION_ID.fullmatch(region.get("section_id", "")) is not None
        and _TABLE_ID.fullmatch(region.get("table_id", "")) is not None
    }
    try:
        leading_keys = [tuple(position) for position in leading_positions]
    except TypeError:
        return None
    dropped = [by_position.get(position) for position in leading_keys]
    if any(type(region) is not dict for region in dropped):
        return None
    dropped_regions = [region for region in dropped if type(region) is dict]
    if any(
        not region.get("component_roles")
        or not set(region["component_roles"]).issubset(validation_roles)
        for region in dropped_regions
    ):
        return None
    dropped_region_ids = {id(region) for region in dropped_regions}
    remaining = [region for region in regions if id(region) not in dropped_region_ids]
    if not remaining or not any(
        set(region.get("component_roles", [])) & direct_roles for region in remaining
    ):
        return None

    owner_page, owner_section, _owner_surface = owner["position"]
    prior_number = owner["outline_top_level_number"] - 1
    dropped_axis = []
    dropped_inventory_keys = set()
    for region in dropped_regions:
        if (
            region.get("selected_page_ordinal") != owner_page
            or int(region["section_id"][1:]) >= owner_section
        ):
            return None
        resolved_page = page_json_by_version.get(region["page_json_version_id"])
        try:
            section = resolved_page["sections"][int(region["section_id"][1:]) - 1]  # type: ignore[index]
            table = section["tables"][int(region["table_id"][1:]) - 1]
        except (KeyError, IndexError, TypeError, ValueError):
            return None
        title = section.get("title_exact")
        number_match = (
            re.match(r"\s*([0-9]+)(?:\s*[.)]|\s+)", title)
            if type(title) is str
            else None
        )
        if (
            number_match is None
            or int(number_match.group(1)) != prior_number
            or _exact_owner_alias(title, compiled_specs=compiled_specs) is not None
            or _exact_boundary_alias(title, compiled_specs=compiled_specs) is not None
            or type(table) is not dict
        ):
            return None
        key = (
            region["page_json_version_id"],
            region["section_id"],
            region["table_id"],
        )
        matching_inventory = [
            item
            for item in inventory
            if type(item) is dict
            and (
                item.get("page_json_version_id"),
                item.get("section_id"),
                item.get("table_id"),
            )
            == key
            and item.get("disposition") == "SELECTED_FAMILY_COMPONENT"
            and item.get("classification", {}).get("typed_control_disposition")
            is None
        ]
        if len(matching_inventory) != 1:
            return None
        dropped_inventory_keys.add(key)
        dropped_axis.append(
            {
                "classification_id": matching_inventory[0]["classification"][
                    "classification_id"
                ],
                "component_roles": canonical_clone_v1(region["component_roles"]),
                "locator": {
                    key: region[key]
                    for key in (
                        "page_json_version_id",
                        "physical_page",
                        "section_id",
                        "table_id",
                    )
                },
                "prior_note_title_exact": title,
            }
        )

    material = {
        "document_id": cluster["document_id"],
        "document_ordinal": cluster["document_ordinal"],
        "dropped_validation_only_region_axis": dropped_axis,
        "format_version": VALIDATION_ONLY_LEADING_PRUNE_RECEIPT_FORMAT_VERSION,
        "owner_receipt_before": canonical_clone_v1(owner),
        "raw_cluster_id": cluster["cluster_id"],
        "rule": (
            "ALL_LEADING_REGIONS_VALIDATION_ONLY_FROM_IMMEDIATELY_PRIOR_"
            "NUMBERED_NOTE_AND_REMAINING_OWNER_HAS_SCHEMA_BOUND_ROLE"
        ),
        "source_logical_name": cluster["source_logical_name"],
        "source_sha256": cluster["source_sha256"],
    }
    receipt = {
        **material,
        "validation_only_leading_prune_receipt_id": (
            "gjivpvolprv1:receipt:" + canonical_json_sha256_v1(material)
        ),
    }
    pruned = canonical_clone_v1(cluster)
    pruned["component_regions"] = canonical_clone_v1(remaining)
    for fragment_ordinal, region in enumerate(
        pruned["component_regions"], start=1
    ):
        region["fragment_ordinal"] = fragment_ordinal
    pruned["owner_receipt"]["leading_component_positions"] = []
    for item in pruned["declared_money_table_inventory"]:
        key = (
            item.get("page_json_version_id"),
            item.get("section_id"),
            item.get("table_id"),
        )
        if key in dropped_inventory_keys:
            item["disposition"] = (
                "EXCLUDED_IMMEDIATELY_PRIOR_NUMBERED_NOTE_VALIDATION_ONLY_"
                "BY_FAMILY25_RECEIPT"
            )
    cluster_material = {
        key: item for key, item in pruned.items() if key != "cluster_id"
    }
    pruned["cluster_id"] = (
        "gjmthfcv1:cluster:" + canonical_json_sha256_v1(cluster_material)
    )
    return pruned, receipt


def _observed_money_coefficients_v1(
    row: Mapping[str, Any], *, money_ordinals: Sequence[int]
) -> list[int] | None:
    values = row.get("values_exact")
    if type(values) is not list or any(ordinal > len(values) for ordinal in money_ordinals):
        return None
    coefficients = []
    for ordinal in money_ordinals:
        try:
            coefficient = observed_source_coefficient_v1(
                _source_money(values[ordinal - 1])
            )
        except ValueError:
            return None
        if coefficient is None:
            return None
        coefficients.append(coefficient)
    return coefficients


def _prune_exact_alternate_instrument_presentation_v1(
    *,
    cluster: Mapping[str, Any],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Keep maturity detail when a second table is an exact type presentation.

    The TCB notes print the same liability population twice: first by original
    maturity (the schema-detail frontier), then by customer type.  The latter
    contains only the already represented certificate and bond parent roles.
    Source order and headings choose the maturity table; values only veto the
    receipt by requiring exact all-lane parent and root corroboration.
    """

    if cluster.get("status") != READY:
        return None
    regions = cluster.get("component_regions")
    inventory = cluster.get("declared_money_table_inventory")
    if type(regions) is not list or len(regions) != 2 or type(inventory) is not list:
        return None
    first_region, second_region = regions
    if any(type(region) is not dict for region in regions):
        return None
    if any(
        first_region.get(field) != second_region.get(field)
        for field in ("page_json_version_id", "physical_page", "section_id")
    ):
        return None
    first_table = _region_table(page_json_by_version, first_region)
    second_table = _region_table(page_json_by_version, second_region)
    page = page_json_by_version.get(first_region["page_json_version_id"])
    try:
        section = page["sections"][int(first_region["section_id"][1:]) - 1]  # type: ignore[index]
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    if type(section) is not dict:
        return None
    narratives = section.get("narratives_exact")
    title_axis = [first_table.get("title_exact"), second_table.get("title_exact")]
    if all(_normalized(title) for title in title_axis):
        semantic_axis = title_axis
        semantic_source_kind = "TABLE_TITLE"
    elif (
        not any(_normalized(title) for title in title_axis)
        and type(narratives) is list
        and len(narratives) >= 2
    ):
        semantic_axis = narratives[:2]
        semantic_source_kind = "SECTION_NARRATIVE_ORDER"
    else:
        return None
    if (
        "theo ky han" not in _normalized(semantic_axis[0])
        or "theo loai hinh" not in _normalized(semantic_axis[1])
    ):
        return None
    first_classification = classify_gemini_json_multitable_hierarchical_table_v1(
        page, section, first_table, compiled_specs=compiled_specs
    )
    second_classification = classify_gemini_json_multitable_hierarchical_table_v1(
        page, section, second_table, compiled_specs=compiled_specs
    )
    first_rows = first_table.get("rows")
    second_rows = second_table.get("rows")
    first_money = first_classification.get("money_column_ordinals")
    second_money = second_classification.get("money_column_ordinals")
    first_roles = {
        hit.get("role")
        for hit in first_classification.get("role_hits", [])
        if type(hit) is dict
    } - {None}
    second_roles = {
        hit.get("role")
        for hit in second_classification.get("role_hits", [])
        if type(hit) is dict
    } - {None}
    detail_roles = {
        "BOND_SHORT",
        "BOND_MEDIUM",
        "BOND_LONG",
        "CD_SHORT",
        "CD_MEDIUM",
        "CD_LONG",
    }
    if (
        type(first_rows) is not list
        or not first_rows
        or type(second_rows) is not list
        or not second_rows
        or first_money != [1, 2]
        or second_money != [1, 2]
        or not (first_roles & detail_roles)
        or second_roles != {"BOND", "CERTIFICATE_OF_DEPOSIT"}
        or any(
            classification.get("ambiguous_rows") != []
            or classification.get("typed_control_disposition") is not None
            for classification in (first_classification, second_classification)
        )
        or type(first_rows[-1]) is not dict
        or type(second_rows[-1]) is not dict
        or first_rows[-1].get("row_kind") != "TOTAL"
        or second_rows[-1].get("row_kind") != "TOTAL"
    ):
        return None
    first_total = _observed_money_coefficients_v1(
        first_rows[-1], money_ordinals=first_money
    )
    second_total = _observed_money_coefficients_v1(
        second_rows[-1], money_ordinals=second_money
    )
    if first_total is None or first_total != second_total:
        return None

    def direct_role_sum(
        rows: Sequence[Any], classification: Mapping[str, Any], role: str
    ) -> list[int] | None:
        vectors = []
        for hit in classification.get("role_hits", []):
            if type(hit) is not dict or hit.get("role") != role:
                continue
            ordinal = hit.get("row_ordinal")
            if type(ordinal) is not int or not 1 <= ordinal <= len(rows):
                return None
            vector = _observed_money_coefficients_v1(
                rows[ordinal - 1], money_ordinals=[1, 2]
            )
            if vector is None:
                return None
            vectors.append(vector)
        if not vectors:
            return None
        return [sum(vector[lane] for vector in vectors) for lane in range(2)]

    primary_parent_axis = {}
    alternate_parent_axis = {}
    for role, child_roles in {
        "BOND": {"BOND_SHORT", "BOND_MEDIUM", "BOND_LONG"},
        "CERTIFICATE_OF_DEPOSIT": {"CD_SHORT", "CD_MEDIUM", "CD_LONG"},
    }.items():
        primary_vectors = [
            direct_role_sum(first_rows, first_classification, child_role)
            for child_role in sorted(child_roles & first_roles)
        ]
        if not primary_vectors or any(vector is None for vector in primary_vectors):
            return None
        primary = [
            sum(vector[lane] for vector in primary_vectors if vector is not None)
            for lane in range(2)
        ]
        alternate = direct_role_sum(second_rows, second_classification, role)
        if alternate is None or primary != alternate:
            return None
        primary_parent_axis[role] = primary
        alternate_parent_axis[role] = alternate
    if [
        primary_parent_axis["BOND"][lane]
        + primary_parent_axis["CERTIFICATE_OF_DEPOSIT"][lane]
        for lane in range(2)
    ] != first_total:
        return None

    locator = {
        key: second_region[key]
        for key in ("page_json_version_id", "physical_page", "section_id", "table_id")
    }
    material = {
        "alternate_parent_axis": alternate_parent_axis,
        "alternate_source_rows": canonical_clone_v1(second_rows),
        "document_id": cluster["document_id"],
        "document_ordinal": cluster["document_ordinal"],
        "format_version": ALTERNATE_PRESENTATION_PRUNE_RECEIPT_FORMAT_VERSION,
        "locator": locator,
        "primary_parent_axis": primary_parent_axis,
        "primary_total_axis": first_total,
        "raw_component_regions": canonical_clone_v1(regions),
        "raw_cluster_id": cluster["cluster_id"],
        "rule": (
            "SOURCE_ORDERED_MATURITY_DETAIL_PREFERRED_OVER_EXACT_CORROBORATING_"
            "TYPE_PRESENTATION_ALL_PARENT_AND_ROOT_LANES_EXACT"
        ),
        "semantic_source_axis": canonical_clone_v1(semantic_axis),
        "semantic_source_kind": semantic_source_kind,
        "source_logical_name": cluster["source_logical_name"],
        "source_sha256": cluster["source_sha256"],
    }
    receipt = {
        **material,
        "alternate_presentation_prune_receipt_id": (
            "gjivpapprv1:receipt:" + canonical_json_sha256_v1(material)
        ),
    }
    pruned = canonical_clone_v1(cluster)
    pruned["component_regions"] = [canonical_clone_v1(first_region)]
    pruned["component_regions"][0]["fragment_ordinal"] = 1
    for item in pruned["declared_money_table_inventory"]:
        if all(item.get(field) == locator[field] for field in locator):
            item["disposition"] = (
                "EXCLUDED_EXACT_CORROBORATING_ALTERNATE_TYPE_PRESENTATION_"
                "BY_FAMILY25_RECEIPT"
            )
    return pruned, receipt


def _inventory_component_roles_v1(item: Mapping[str, Any]) -> list[str]:
    classification = item.get("classification")
    if type(classification) is not dict:
        return []
    role_hits = classification.get("role_hits")
    roles = set(classification.get("context_roles") or [])
    if type(role_hits) is list:
        roles.update(
            hit.get("role") for hit in role_hits if type(hit) is dict
        )
    return sorted(role for role in roles if type(role) is str and role)


def _region_from_inventory_item_v1(
    *,
    cluster: Mapping[str, Any],
    item: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    fragment_ordinal: int,
) -> dict[str, Any] | None:
    selected = [
        page
        for page in selected_page_axis
        if type(page) is dict
        and all(
            page.get(field) == cluster.get(field)
            for field in (
                "document_id",
                "document_ordinal",
                "source_logical_name",
                "source_sha256",
            )
        )
        and page.get("page_json_version_id") == item.get("page_json_version_id")
        and page.get("physical_page") == item.get("physical_page")
    ]
    if len(selected) != 1:
        return None
    return {
        "component_roles": _inventory_component_roles_v1(item),
        "document_id": cluster["document_id"],
        "document_ordinal": cluster["document_ordinal"],
        "fragment_ordinal": fragment_ordinal,
        "page_json_version_id": item["page_json_version_id"],
        "physical_page": item["physical_page"],
        "section_id": item["section_id"],
        "selected_page_ordinal": selected[0]["selected_page_ordinal"],
        "source_logical_name": cluster["source_logical_name"],
        "source_sha256": cluster["source_sha256"],
        "table_id": item["table_id"],
    }


def _table_is_page_edge_v1(
    *,
    page: Mapping[str, Any],
    section_id: str,
    table_id: str,
    edge: str,
) -> bool:
    positions = [
        (section_ordinal, table_ordinal)
        for section_ordinal, section in enumerate(page.get("sections", []), start=1)
        if type(section) is dict and type(section.get("tables")) is list
        for table_ordinal, table in enumerate(section["tables"], start=1)
        if type(table) is dict
    ]
    if not positions:
        return False
    position = (int(section_id[1:]), int(table_id[1:]))
    return position == (positions[0] if edge == "FIRST" else positions[-1])


def _exact_adjacent_receiver_query_recovery_v1(
    *,
    cluster: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Accept one explicit leading receiver omitted from an owner cluster.

    The shared query correctly fails closed when an owner interval contains an
    unconsumed MONEY table.  Some Family-25 notes end at the physical bottom of
    page N and expose exactly one page-N+1 leading table explicitly marked
    ``CONTINUES_FROM_PREVIOUS_PAGE``.  This recovery only reassembles that raw
    page edge; it does not decide whether the receiver is detail or a duplicate
    presentation, and it never changes a source value.
    """

    reasons = cluster.get("reasons")
    inventory = cluster.get("declared_money_table_inventory")
    owner = cluster.get("owner_receipt")
    if (
        cluster.get("status") != "UNRESOLVED_GEMINI_JSON_FAMILY"
        or type(reasons) is not list
        or len(reasons) != 1
        or type(reasons[0]) is not str
        or not reasons[0].startswith("UNCONSUMED_MONEY_TABLE_INSIDE_OWNER_FENCE:")
        or type(inventory) is not list
        or type(owner) is not dict
        or _exact_owner_alias(owner.get("source_exact"), compiled_specs=compiled_specs)
        is None
        or type(owner.get("position")) is not list
        or len(owner["position"]) != 3
    ):
        return None

    receivers = [
        item
        for item in inventory
        if type(item) is dict
        and item.get("disposition") == "UNCONSUMED_MONEY_TABLE_INSIDE_OWNER_FENCE"
        and reasons[0]
        == "UNCONSUMED_MONEY_TABLE_INSIDE_OWNER_FENCE:"
        + ":".join(
            str(item.get(field))
            for field in ("page_json_version_id", "section_id", "table_id")
        )
    ]
    selected_items = [
        item
        for item in inventory
        if type(item) is dict and item.get("disposition") == "SELECTED_FAMILY_COMPONENT"
    ]
    if len(receivers) != 1 or not selected_items:
        return None
    receiver = receivers[0]
    receiver_resolved = _table_from_inventory(
        inventory_item=receiver,
        page_json_by_version=page_json_by_version,
    )
    receiver_page = page_json_by_version.get(receiver.get("page_json_version_id"))
    if receiver_resolved is None or type(receiver_page) is not dict:
        return None
    receiver_section, receiver_table = receiver_resolved
    receiver_classification = receiver.get("classification")
    receiver_rows = receiver_table.get("rows")
    receiver_money = _money_ordinals(receiver_table)
    if (
        type(receiver_classification) is not dict
        or type(receiver_rows) is not list
        or not receiver_rows
        or not receiver_money
        or receiver_table.get("continuation") != "CONTINUES_FROM_PREVIOUS_PAGE"
        or receiver.get("section_id") != "s1"
        or receiver.get("table_id") != "t1"
        or not _table_is_page_edge_v1(
            page=receiver_page,
            section_id=receiver["section_id"],
            table_id=receiver["table_id"],
            edge="FIRST",
        )
        or receiver_classification.get("layout_orientation")
        != "ROW_ROLES_PERIOD_COLUMNS"
        or receiver_classification.get("typed_control_disposition") is not None
        or receiver_classification.get("typed_control_conflict_disposition") is not None
        or receiver_classification.get("ambiguous_rows") != []
        or not any(
            type(row) is dict
            and type(row.get("values_exact")) is list
            and all(
                ordinal <= len(row["values_exact"])
                and type(row["values_exact"][ordinal - 1]) is str
                and row["values_exact"][ordinal - 1].strip()
                for ordinal in receiver_money
            )
            for row in receiver_rows
        )
    ):
        return None

    receiver_axis = _region_from_inventory_item_v1(
        cluster=cluster,
        item=receiver,
        selected_page_axis=selected_page_axis,
        fragment_ordinal=1,
    )
    if receiver_axis is None:
        return None
    prior_items = [
        item
        for item in selected_items
        if item.get("physical_page") == receiver["physical_page"] - 1
    ]
    if not prior_items:
        return None
    prior = max(prior_items, key=lambda item: tuple(item["position"]))
    prior_resolved = _table_from_inventory(
        inventory_item=prior,
        page_json_by_version=page_json_by_version,
    )
    prior_page = page_json_by_version.get(prior.get("page_json_version_id"))
    if prior_resolved is None or type(prior_page) is not dict:
        return None
    prior_section, prior_table = prior_resolved
    prior_classification = prior.get("classification")
    prior_axis = _region_from_inventory_item_v1(
        cluster=cluster,
        item=prior,
        selected_page_axis=selected_page_axis,
        fragment_ordinal=1,
    )
    if (
        type(prior_classification) is not dict
        or prior_axis is None
        or prior_axis["selected_page_ordinal"] + 1
        != receiver_axis["selected_page_ordinal"]
        or prior_axis["physical_page"] + 1 != receiver_axis["physical_page"]
        or owner["position"][0] != prior_axis["selected_page_ordinal"]
        or tuple(owner["position"]) > tuple(prior["position"])
        or prior_table.get("continuation") not in {"NONE", "CONTINUES_ON_NEXT_PAGE"}
        or not _table_is_page_edge_v1(
            page=prior_page,
            section_id=prior["section_id"],
            table_id=prior["table_id"],
            edge="LAST",
        )
        or prior_classification.get("typed_control_disposition") is not None
        or prior_classification.get("typed_control_conflict_disposition") is not None
        or prior_classification.get("ambiguous_rows") != []
    ):
        return None

    receiver_surfaces = [
        receiver_section.get("title_exact"),
        *(receiver_section.get("narratives_exact") or []),
        receiver_table.get("title_exact"),
    ]
    if any(
        _exact_boundary_alias(surface, compiled_specs=compiled_specs) is not None
        for surface in receiver_surfaces
    ):
        return None
    explicit_units = {
        _normalized(table.get("unit_exact"))
        for table in (prior_table, receiver_table)
        if _normalized(table.get("unit_exact"))
    }
    if len(explicit_units) > 1:
        return None

    selected_with_receiver = sorted(
        [*selected_items, receiver], key=lambda item: tuple(item["position"])
    )
    regions = []
    for fragment_ordinal, item in enumerate(selected_with_receiver, start=1):
        region = _region_from_inventory_item_v1(
            cluster=cluster,
            item=item,
            selected_page_axis=selected_page_axis,
            fragment_ordinal=fragment_ordinal,
        )
        if region is None:
            return None
        regions.append(region)
    receiver_locator = {
        key: receiver_axis[key]
        for key in (
            "page_json_version_id",
            "physical_page",
            "section_id",
            "selected_page_ordinal",
            "table_id",
        )
    }
    prior_locator = {
        key: prior_axis[key]
        for key in (
            "page_json_version_id",
            "physical_page",
            "section_id",
            "selected_page_ordinal",
            "table_id",
        )
    }
    material = {
        "document_id": cluster["document_id"],
        "document_ordinal": cluster["document_ordinal"],
        "explicit_unit_axis": sorted(explicit_units),
        "format_version": ADJACENT_RECEIVER_QUERY_RECEIPT_FORMAT_VERSION,
        "owner_receipt": canonical_clone_v1(owner),
        "prior_classification_id": prior_classification["classification_id"],
        "prior_locator": prior_locator,
        "prior_table_continuation": prior_table.get("continuation"),
        "raw_cluster_id": cluster["cluster_id"],
        "raw_cluster_reasons": canonical_clone_v1(reasons),
        "raw_component_inventory_axis": canonical_clone_v1(selected_items),
        "receiver_classification_id": receiver_classification["classification_id"],
        "receiver_columns": canonical_clone_v1(receiver_table.get("columns")),
        "receiver_locator": receiver_locator,
        "receiver_rows": canonical_clone_v1(receiver_rows),
        "receiver_table_continuation": receiver_table.get("continuation"),
        "receiver_unit_exact": receiver_table.get("unit_exact"),
        "rule": (
            "ONE_UNCONSUMED_FIRST_TABLE_EXPLICIT_FROM_PREVIOUS_RECEIVER_ON_"
            "IMMEDIATELY_ADJACENT_PAGE_AFTER_PAGE_FINAL_OWNER_COMPONENT_NO_"
            "RESET_AMBIGUITY_CONTROL_OR_UNIT_CONFLICT_VALUES_UNCHANGED"
        ),
        "source_logical_name": cluster["source_logical_name"],
        "source_sha256": cluster["source_sha256"],
    }
    receipt = {
        **material,
        "adjacent_receiver_query_receipt_id": (
            "gjivparqrv1:receipt:" + canonical_json_sha256_v1(material)
        ),
    }
    recovered = canonical_clone_v1(cluster)
    for item in recovered["declared_money_table_inventory"]:
        if all(
            item.get(field) == receiver.get(field)
            for field in ("page_json_version_id", "section_id", "table_id")
        ):
            item["disposition"] = (
                "SELECTED_EXACT_ADJACENT_CONTINUATION_RECEIVER_BY_FAMILY25_RECEIPT"
            )
    recovered["component_regions"] = regions
    recovered["owner_receipt"] = {
        **canonical_clone_v1(owner),
        "adjacent_receiver_query_receipt_id": receipt[
            "adjacent_receiver_query_receipt_id"
        ],
    }
    recovered["reasons"] = []
    recovered["status"] = READY
    return recovered, receipt


def _empty_owner_continuation_query_recovery_v1(
    *,
    cluster: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Recover a page-final empty owner carrier plus its leading receiver."""

    inventory = cluster.get("declared_money_table_inventory")
    if (
        cluster.get("status") != "UNRESOLVED_GEMINI_JSON_FAMILY"
        or cluster.get("reasons") != ["COMPLETE_OWNER_CLUSTER_NOT_RESOLVED"]
        or cluster.get("owner_receipt") is not None
        or type(inventory) is not list
    ):
        return None
    owner_candidates = []
    for item in inventory:
        if type(item) is not dict or type(item.get("classification")) is not dict:
            continue
        resolved = _table_from_inventory(
            inventory_item=item, page_json_by_version=page_json_by_version
        )
        page = page_json_by_version.get(item.get("page_json_version_id"))
        if resolved is None or type(page) is not dict:
            continue
        section, table = resolved
        rows = table.get("rows")
        surfaces = [
            section.get("title_exact"),
            *(section.get("narratives_exact") or []),
            table.get("title_exact"),
        ]
        owner_aliases = {
            alias
            for surface in surfaces
            if (
                alias := _exact_owner_alias(
                    surface, compiled_specs=compiled_specs
                )
            )
            is not None
        }
        classification = item["classification"]
        if (
            len(owner_aliases) == 1
            and table.get("continuation") == "CONTINUES_ON_NEXT_PAGE"
            and type(rows) is list
            and len(rows) == 1
            and type(rows[0]) is dict
            and rows[0].get("row_kind") == "UNKNOWN"
            and not _normalized(rows[0].get("label_exact"))
            and not any(
                _normalized(value) for value in rows[0].get("hierarchy_path_exact", [])
            )
            and type(rows[0].get("values_exact")) is list
            and all(value is None for value in rows[0]["values_exact"])
            and classification.get("owner_visible") is True
            and classification.get("family_presence_anchor_visible") is False
            and classification.get("role_hits") == []
            and classification.get("context_roles") == []
            and classification.get("ambiguous_rows") == []
            and classification.get("typed_control_disposition") is None
            and classification.get("typed_control_conflict_disposition") is None
            and _two_period_axis(table).get("complete") is True
            and _table_is_page_edge_v1(
                page=page,
                section_id=item["section_id"],
                table_id=item["table_id"],
                edge="LAST",
            )
        ):
            owner_candidates.append((item, section, table, next(iter(owner_aliases))))
    if len(owner_candidates) != 1:
        return None
    owner_item, owner_section, owner_table, owner_alias = owner_candidates[0]
    receiver_candidates = []
    direct_roles = set(compiled_specs["output_role_order"]) - set(
        compiled_specs["validation_only_roles"]
    )
    for item in inventory:
        if (
            type(item) is not dict
            or item.get("physical_page") != owner_item["physical_page"] + 1
            or item.get("section_id") != "s1"
            or item.get("table_id") != "t1"
            or type(item.get("classification")) is not dict
        ):
            continue
        resolved = _table_from_inventory(
            inventory_item=item, page_json_by_version=page_json_by_version
        )
        page = page_json_by_version.get(item.get("page_json_version_id"))
        if resolved is None or type(page) is not dict:
            continue
        section, table = resolved
        rows = table.get("rows")
        classification = item["classification"]
        roles = set(_inventory_component_roles_v1(item))
        money = _money_ordinals(table)
        if (
            table.get("continuation") == "CONTINUES_FROM_PREVIOUS_PAGE"
            and _table_is_page_edge_v1(
                page=page,
                section_id=item["section_id"],
                table_id=item["table_id"],
                edge="FIRST",
            )
            and type(rows) is list
            and len(rows) >= 2
            and type(rows[-1]) is dict
            and rows[-1].get("row_kind") == "TOTAL"
            and type(rows[-1].get("values_exact")) is list
            and all(
                ordinal <= len(rows[-1]["values_exact"])
                and type(rows[-1]["values_exact"][ordinal - 1]) is str
                and rows[-1]["values_exact"][ordinal - 1].strip()
                for ordinal in money
            )
            and roles & direct_roles
            and classification.get("owner_visible") is False
            and classification.get("ambiguous_rows") == []
            and classification.get("typed_control_disposition") is None
            and classification.get("typed_control_conflict_disposition") is None
            and all(
                not any(
                    _normalized(value)
                    for value in column.get("header_path_exact", [])
                )
                for column in table.get("columns", [])
                if type(column) is dict and column.get("value_kind") == "MONEY"
            )
            and not _normalized(table.get("unit_exact"))
            and not any(
                _exact_boundary_alias(surface, compiled_specs=compiled_specs)
                is not None
                for surface in [
                    section.get("title_exact"),
                    *(section.get("narratives_exact") or []),
                    table.get("title_exact"),
                ]
            )
        ):
            receiver_candidates.append((item, section, table))
    if len(receiver_candidates) != 1:
        return None
    receiver_item, receiver_section, receiver_table = receiver_candidates[0]
    owner_region = _region_from_inventory_item_v1(
        cluster=cluster,
        item=owner_item,
        selected_page_axis=selected_page_axis,
        fragment_ordinal=1,
    )
    receiver_region = _region_from_inventory_item_v1(
        cluster=cluster,
        item=receiver_item,
        selected_page_axis=selected_page_axis,
        fragment_ordinal=2,
    )
    if (
        owner_region is None
        or receiver_region is None
        or receiver_region["physical_page"] != owner_region["physical_page"] + 1
        or receiver_region["selected_page_ordinal"]
        != owner_region["selected_page_ordinal"] + 1
    ):
        return None
    material = {
        "document_id": cluster["document_id"],
        "document_ordinal": cluster["document_ordinal"],
        "format_version": EMPTY_OWNER_CONTINUATION_QUERY_RECEIPT_FORMAT_VERSION,
        "owner_alias": owner_alias,
        "owner_classification_id": owner_item["classification"]["classification_id"],
        "owner_locator": {
            key: owner_region[key]
            for key in (
                "page_json_version_id",
                "physical_page",
                "section_id",
                "selected_page_ordinal",
                "table_id",
            )
        },
        "owner_source_rows": canonical_clone_v1(owner_table["rows"]),
        "owner_surface_axis": canonical_clone_v1(
            [
                owner_section.get("title_exact"),
                *(owner_section.get("narratives_exact") or []),
                owner_table.get("title_exact"),
            ]
        ),
        "owner_unit_exact": owner_table.get("unit_exact"),
        "raw_cluster_id": cluster["cluster_id"],
        "raw_cluster_reasons": canonical_clone_v1(cluster["reasons"]),
        "receiver_classification_id": receiver_item["classification"][
            "classification_id"
        ],
        "receiver_locator": {
            key: receiver_region[key]
            for key in (
                "page_json_version_id",
                "physical_page",
                "section_id",
                "selected_page_ordinal",
                "table_id",
            )
        },
        "receiver_source_rows": canonical_clone_v1(receiver_table["rows"]),
        "rule": (
            "UNIQUE_PAGE_FINAL_EXACT_OWNER_EMPTY_CARRIER_EXPLICIT_ON_NEXT_AND_"
            "IMMEDIATELY_ADJACENT_FIRST_TABLE_EXPLICIT_FROM_PREVIOUS_WITH_"
            "DECLARED_CHILDREN_TERMINAL_VISIBLE_TOTAL_NO_RESET_OR_AMBIGUITY"
        ),
        "source_logical_name": cluster["source_logical_name"],
        "source_sha256": cluster["source_sha256"],
    }
    receipt = {
        **material,
        "empty_owner_continuation_query_receipt_id": (
            "gjivpeocqrv1:receipt:" + canonical_json_sha256_v1(material)
        ),
    }
    recovered = canonical_clone_v1(cluster)
    selected_keys = {
        (
            owner_item["page_json_version_id"],
            owner_item["section_id"],
            owner_item["table_id"],
        ),
        (
            receiver_item["page_json_version_id"],
            receiver_item["section_id"],
            receiver_item["table_id"],
        ),
    }
    for item in recovered["declared_money_table_inventory"]:
        key = (item["page_json_version_id"], item["section_id"], item["table_id"])
        if key in selected_keys:
            item["disposition"] = (
                "SELECTED_EXACT_EMPTY_OWNER_ADJACENT_CONTINUATION_BY_FAMILY25_RECEIPT"
            )
    recovered["component_regions"] = [owner_region, receiver_region]
    recovered["owner_receipt"] = {
        "alias": owner_alias,
        "empty_owner_continuation_query_receipt_id": receipt[
            "empty_owner_continuation_query_receipt_id"
        ],
        "leading_component_positions": [],
        "leading_component_rule": "EXACT_EMPTY_OWNER_ADJACENT_CONTINUATION",
        "position": [
            owner_region["selected_page_ordinal"],
            int(owner_region["section_id"][1:]),
            int(owner_region["table_id"][1:]),
        ],
        "source_exact": next(
            surface
            for surface in material["owner_surface_axis"]
            if _exact_owner_alias(surface, compiled_specs=compiled_specs) is not None
        ),
    }
    recovered["reasons"] = []
    recovered["status"] = READY
    return recovered, receipt


def adapt_gemini_json_issued_valuable_papers_indexed_query_evidence_v1(
    value: Any,
    *,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Recover exact local/internal note owners or an unshadowed primary root."""

    evidence = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        value, compiled_specs=compiled_specs
    )
    clusters = []
    receipts = []
    for disposition in evidence["candidate_dispositions"]:
        cluster = canonical_clone_v1(disposition["cluster"])
        pages = page_json_by_document.get(cluster["document_ordinal"])
        if type(pages) is dict:
            alternate = _prune_exact_alternate_instrument_presentation_v1(
                cluster=cluster,
                page_json_by_version=pages,
                compiled_specs=compiled_specs,
            )
            if alternate is not None:
                cluster, receipt = alternate
                receipts.append(receipt)
            pruned = _prune_numbered_prior_note_validation_only_leading_regions_v1(
                cluster=cluster,
                page_json_by_version=pages,
                compiled_specs=compiled_specs,
            )
            if pruned is not None:
                cluster, receipt = pruned
                receipts.append(receipt)
            adjacent = _exact_adjacent_receiver_query_recovery_v1(
                cluster=cluster,
                selected_page_axis=evidence["selected_page_axis"],
                page_json_by_version=pages,
                compiled_specs=compiled_specs,
            )
            if adjacent is not None:
                cluster, receipt = adjacent
                receipts.append(receipt)
            empty_owner = _empty_owner_continuation_query_recovery_v1(
                cluster=cluster,
                selected_page_axis=evidence["selected_page_axis"],
                page_json_by_version=pages,
                compiled_specs=compiled_specs,
            )
            if empty_owner is not None:
                cluster, receipt = empty_owner
                receipts.append(receipt)
        recovered = None
        recovery_kind = None
        if type(pages) is dict and cluster.get("status") != READY:
            recovered = _local_owner_query_recovery_v1(
                cluster=cluster,
                selected_page_axis=evidence["selected_page_axis"],
                page_json_by_version=pages,
                compiled_specs=compiled_specs,
            )
            recovery_kind = "LOCAL_OWNER" if recovered is not None else None
        if type(pages) is dict and recovered is None:
            recovered = _internal_root_row_query_recovery_v1(
                cluster=cluster,
                selected_page_axis=evidence["selected_page_axis"],
                page_json_by_version=pages,
                compiled_specs=compiled_specs,
            )
            recovery_kind = "INTERNAL_ROOT_ROW" if recovered is not None else None
        if (
            type(pages) is dict
            and recovered is None
            and cluster.get("reasons") == []
        ):
            recovered = _primary_statement_exact_root_query_recovery_v1(
                cluster=cluster,
                selected_page_axis=evidence["selected_page_axis"],
                page_json_by_version=pages,
                compiled_specs=compiled_specs,
            )
            recovery_kind = "PRIMARY_ROOT" if recovered is not None else None
        if recovered is not None:
            region, receipt = recovered
            for item in cluster["declared_money_table_inventory"]:
                if (
                    item.get("page_json_version_id"),
                    item.get("section_id"),
                    item.get("table_id"),
                ) == (
                    region["page_json_version_id"],
                    region["section_id"],
                    region["table_id"],
                ):
                    if recovery_kind == "LOCAL_OWNER":
                        item["disposition"] = (
                            "SELECTED_FAMILY_COMPONENT_AFTER_EXACT_LOCAL_OWNER_RECEIPT"
                        )
                    elif recovery_kind == "INTERNAL_ROOT_ROW":
                        item["disposition"] = (
                            "SELECTED_FAMILY_COMPONENT_AFTER_EXACT_INTERNAL_ROOT_ROW_RECEIPT"
                        )
                    else:
                        item["disposition"] = (
                            "SELECTED_PRIMARY_STATEMENT_EXACT_FAMILY_ROOT_"
                            "AFTER_ADAPTER_RECEIPT"
                        )
            cluster["component_regions"] = [region]
            if recovery_kind == "LOCAL_OWNER":
                cluster["owner_receipt"] = {
                    "alias": receipt["owner_alias"],
                    "leading_component_positions": [],
                    "leading_component_rule": "EXACT_LOCAL_SOLE_TABLE_OWNER",
                    "local_owner_query_receipt_id": receipt[
                        "local_owner_query_receipt_id"
                    ],
                    "position": [
                        receipt["locator"]["selected_page_ordinal"],
                        int(receipt["locator"]["section_id"][1:]),
                        0
                        if receipt["owner_source_kind"] != "TABLE_TITLE"
                        else int(receipt["locator"]["table_id"][1:]),
                    ],
                    "source_exact": receipt["owner_source_exact"],
                }
            elif recovery_kind == "INTERNAL_ROOT_ROW":
                cluster["owner_receipt"] = {
                    "alias": receipt["root_alias_normalized"],
                    "internal_root_row_query_receipt_id": receipt[
                        "internal_root_row_query_receipt_id"
                    ],
                    "leading_component_positions": [],
                    "leading_component_rule": "EXACT_INTERNAL_ROOT_ROW_SOLE_CANDIDATE",
                    "position": [
                        receipt["locator"]["selected_page_ordinal"],
                        int(receipt["locator"]["section_id"][1:]),
                        int(receipt["locator"]["table_id"][1:]),
                    ],
                    "source_exact": receipt["root_row_exact"]["label_exact"],
                }
            else:
                cluster["owner_receipt"] = canonical_clone_v1(receipt)
            cluster["reasons"] = []
            cluster["status"] = READY
            receipts.append(receipt)
        material = {key: item for key, item in cluster.items() if key != "cluster_id"}
        cluster["cluster_id"] = (
            "gjmthfcv1:cluster:" + canonical_json_sha256_v1(material)
        )
        clusters.append(cluster)
    adapted = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=evidence["selected_document_axis"],
        selected_page_axis=evidence["selected_page_axis"],
        document_clusters=clusters,
        query_policy_sha256=canonical_json_sha256_v1(compiled_specs["query_policy"]),
    )
    validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        adapted, compiled_specs=compiled_specs
    )
    return adapted, receipts


def _region_table(
    pages: Mapping[str, dict[str, Any]], region: Mapping[str, Any]
) -> dict[str, Any]:
    page = pages.get(region.get("page_json_version_id"))
    try:
        section = page["sections"][int(region["section_id"][1:]) - 1]  # type: ignore[index]
        table = section["tables"][int(region["table_id"][1:]) - 1]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise _error("issued-paper region does not resolve one selected source table") from exc
    if type(table) is not dict:
        raise _error("issued-paper selected source table is invalid")
    return table


def _exact_declared_role(
    value: Any,
    *,
    compiled_specs: Mapping[str, Any],
    roles: set[str] | frozenset[str],
    within_role: str | None,
) -> str | None:
    folded = _without_leading_ordinal(_normalized(value))
    child_by_role = compiled_specs.get("child_by_role")
    if type(child_by_role) is not dict:
        raise _error("issued-paper compiled child role axis is absent")
    matches = []
    for role in sorted(roles):
        child = child_by_role.get(role)
        if type(child) is not dict:
            continue
        if any(
            type(matcher) is dict
            and matcher.get("within_role") == within_role
            and folded
            in {
                _without_leading_ordinal(_normalized(alias))
                for alias in matcher.get("aliases", [])
            }
            for matcher in child.get("matchers", [])
        ):
            matches.append(role)
    return matches[0] if len(matches) == 1 else None


def _project_face_value_wrappers(
    *,
    pages: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[
    dict[str, dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    """Make one printed ``Mệnh giá`` hierarchy wrapper transparent.

    Some selected JSON paths place tenor children underneath a valuation-basis
    subtotal, or fuse the same printed indentation into one path string.  The
    source rows still give an exact instrument GROUP, immediately followed by
    an exact ``Mệnh giá`` SUBTOTAL and exact tenor ITEM labels.  This projection
    changes hierarchy paths only; labels, values, ordering, and source locators
    remain untouched and are restored in emitted mapping evidence.
    """

    projected_pages = {
        version_id: canonical_clone_v1(page) for version_id, page in pages.items()
    }
    projected_regions = canonical_clone_v1(list(regions))
    receipts = []
    for region_index, region in enumerate(regions):
        table = _region_table(projected_pages, region)
        rows = table.get("rows")
        if type(rows) is not list:
            continue
        raw_rows = canonical_clone_v1(rows)
        current_role = None
        current_group = None
        wrapper = None
        projections = []
        table_projections = []
        projected_child_roles: set[str] = set()
        for row_ordinal, row in enumerate(rows, start=1):
            if type(row) is not dict:
                current_role = current_group = wrapper = None
                continue
            instrument_role = _exact_declared_role(
                row.get("label_exact"),
                compiled_specs=compiled_specs,
                roles=_INSTRUMENT_ROLES,
                within_role=None,
            )
            if row.get("row_kind") == "GROUP" and instrument_role is not None:
                current_role = instrument_role
                current_group = {
                    "hierarchy_path_exact": canonical_clone_v1(
                        row.get("hierarchy_path_exact")
                    ),
                    "label_exact": row.get("label_exact"),
                    "row_ordinal": row_ordinal,
                }
                wrapper = None
                continue
            if current_role is None or current_group is None:
                continue
            if wrapper is None:
                if (
                    row.get("row_kind") == "SUBTOTAL"
                    and _normalized(row.get("label_exact")) == "menh gia"
                    and row_ordinal == current_group["row_ordinal"] + 1
                ):
                    wrapper = {
                        "hierarchy_path_exact": canonical_clone_v1(
                            row.get("hierarchy_path_exact")
                        ),
                        "label_exact": row.get("label_exact"),
                        "row_ordinal": row_ordinal,
                    }
                    continue
                current_role = current_group = wrapper = None
                continue
            if row.get("row_kind") in {"GROUP", "TOTAL"}:
                current_role = current_group = wrapper = None
                continue
            child_roles = {
                role
                for role, child in compiled_specs["child_by_role"].items()
                if type(child) is dict
                and child.get("role_kind") == "ADDITIVE_CHILD"
                and any(
                    type(matcher) is dict
                    and matcher.get("within_role") == current_role
                    for matcher in child.get("matchers", [])
                )
            }
            child_role = _exact_declared_role(
                row.get("label_exact"),
                compiled_specs=compiled_specs,
                roles=child_roles,
                within_role=current_role,
            )
            if row.get("row_kind") != "ITEM" or child_role is None:
                current_role = current_group = wrapper = None
                continue
            before_path = row.get("hierarchy_path_exact")
            after_path = [current_group["label_exact"], row.get("label_exact")]
            if type(before_path) is not list or before_path == after_path:
                continue
            projection = {
                "after_hierarchy_path_exact": canonical_clone_v1(after_path),
                "before_hierarchy_path_exact": canonical_clone_v1(before_path),
                "child_role": child_role,
                "group": canonical_clone_v1(current_group),
                "label_exact": row.get("label_exact"),
                "row_ordinal": row_ordinal,
                "wrapper": canonical_clone_v1(wrapper),
            }
            projections.append(projection)
            projected_child_roles.add(child_role)
            row["hierarchy_path_exact"] = canonical_clone_v1(after_path)

        # ABB's complete instrument presentation uses a blank GROUP row,
        # followed immediately by a visible ``Mệnh giá`` SUBTOTAL and three
        # tenor rows, for each of bond/promissory-note/CD.  The GROUP is the
        # structural owner and the SUBTOTAL is the source-visible instrument
        # observation.  Make that relationship explicit only for the exact
        # three-block/terminal-total shape and only when every fully observed
        # lane closes.  A blank lane is never included in an equation and is
        # preserved as a blank mapping cell.
        expected_parent_axis = [
            (1, 2, (3, 4, 5), "BOND"),
            (6, 7, (8, 9, 10), "PROMISSORY_NOTE"),
            (11, 12, (13, 14, 15), "CERTIFICATE_OF_DEPOSIT"),
        ]
        expected_kind_axis = [
            "GROUP",
            "SUBTOTAL",
            "ITEM",
            "ITEM",
            "ITEM",
            "GROUP",
            "SUBTOTAL",
            "ITEM",
            "ITEM",
            "ITEM",
            "GROUP",
            "SUBTOTAL",
            "ITEM",
            "ITEM",
            "ITEM",
            "TOTAL",
        ]
        money_ordinals = _money_ordinals(table)
        parent_vectors: list[list[int | None]] = []
        root_vector: list[int | None] | None = None

        def observed_or_blank_vector(
            source_row: Mapping[str, Any],
            *,
            ordinals: Sequence[int] = money_ordinals,
        ) -> list[int | None] | None:
            values = source_row.get("values_exact")
            if type(values) is not list or any(
                ordinal > len(values) for ordinal in ordinals
            ):
                return None
            vector = []
            for ordinal in ordinals:
                source = values[ordinal - 1]
                if source in _VISIBLE_DASH_TRANSCRIPTION_ARTEFACTS:
                    source = "-"
                try:
                    vector.append(
                        observed_source_coefficient_v1(_source_money(source))
                    )
                except ValueError:
                    return None
            return vector

        abb_shape = (
            len(raw_rows) == len(expected_kind_axis)
            and all(type(row) is dict for row in raw_rows)
            and [row.get("row_kind") for row in raw_rows] == expected_kind_axis
            and money_ordinals == [1, 2]
            and _normalized(raw_rows[-1].get("label_exact")) == "tong"
        )
        if abb_shape:
            for group_ordinal, wrapper_ordinal, child_ordinals, parent_role in (
                expected_parent_axis
            ):
                group = raw_rows[group_ordinal - 1]
                wrapper = raw_rows[wrapper_ordinal - 1]
                group_role = _exact_declared_role(
                    group.get("label_exact"),
                    compiled_specs=compiled_specs,
                    roles=_INSTRUMENT_ROLES,
                    within_role=None,
                )
                child_roles = {
                    _exact_declared_role(
                        raw_rows[ordinal - 1].get("label_exact"),
                        compiled_specs=compiled_specs,
                        roles={
                            role
                            for role, child in compiled_specs[
                                "child_by_role"
                            ].items()
                            if type(child) is dict
                            and child.get("role_kind") == "ADDITIVE_CHILD"
                        },
                        within_role=parent_role,
                    )
                    for ordinal in child_ordinals
                }
                group_values = group.get("values_exact")
                wrapper_path = wrapper.get("hierarchy_path_exact")
                if (
                    group_role != parent_role
                    or type(group_values) is not list
                    or any(value is not None for value in group_values)
                    or _normalized(wrapper.get("label_exact")) != "menh gia"
                    or type(wrapper_path) is not list
                    or _normalized(group.get("label_exact"))
                    not in _normalized(" ".join(str(value) for value in wrapper_path))
                    or len(child_roles) != 3
                    or None in child_roles
                    or any(
                        rows[ordinal - 1].get("hierarchy_path_exact")
                        != [group.get("label_exact"), rows[ordinal - 1].get("label_exact")]
                        for ordinal in child_ordinals
                    )
                ):
                    abb_shape = False
                    break
                parent_vector = observed_or_blank_vector(wrapper)
                if parent_vector is None or all(
                    coefficient is None for coefficient in parent_vector
                ):
                    abb_shape = False
                    break
                parent_vectors.append(parent_vector)
            root_vector = observed_or_blank_vector(raw_rows[-1])
            if root_vector is None or any(
                coefficient is None for coefficient in root_vector
            ):
                abb_shape = False
        complete_lane_equations = []
        if abb_shape and root_vector is not None:
            for lane in range(len(money_ordinals)):
                lane_components = [vector[lane] for vector in parent_vectors]
                if any(component is None for component in lane_components):
                    continue
                component_sum = sum(
                    component
                    for component in lane_components
                    if component is not None
                )
                if component_sum != root_vector[lane]:
                    abb_shape = False
                    break
                complete_lane_equations.append(
                    {
                        "component_coefficients": lane_components,
                        "component_sum": component_sum,
                        "lane_ordinal": lane + 1,
                        "root_coefficient": root_vector[lane],
                        "status": "EXACT",
                    }
                )
        if abb_shape and complete_lane_equations:
            for group_ordinal, wrapper_ordinal, _child_ordinals, parent_role in (
                expected_parent_axis
            ):
                group = rows[group_ordinal - 1]
                wrapper = rows[wrapper_ordinal - 1]
                group_label = raw_rows[group_ordinal - 1]["label_exact"]
                projections.extend(
                    [
                        {
                            "after_hierarchy_path_exact": [None],
                            "after_label_exact": None,
                            "after_row_kind": "GROUP",
                            "before_hierarchy_path_exact": canonical_clone_v1(
                                group.get("hierarchy_path_exact")
                            ),
                            "before_label_exact": group.get("label_exact"),
                            "before_row_kind": group.get("row_kind"),
                            "projection_kind": (
                                "ALL_NULL_INSTRUMENT_GROUP_MADE_STRUCTURAL_"
                                "AFTER_VISIBLE_FACE_VALUE_SUBTOTAL_BINDING"
                            ),
                            "row_ordinal": group_ordinal,
                        },
                        {
                            "after_hierarchy_path_exact": [group_label],
                            "after_label_exact": group_label,
                            "after_row_kind": wrapper.get("row_kind"),
                            "before_hierarchy_path_exact": canonical_clone_v1(
                                wrapper.get("hierarchy_path_exact")
                            ),
                            "before_label_exact": wrapper.get("label_exact"),
                            "before_row_kind": wrapper.get("row_kind"),
                            "parent_role": parent_role,
                            "projection_kind": (
                                "VISIBLE_FACE_VALUE_SUBTOTAL_BOUND_TO_EXACT_"
                                "IMMEDIATELY_PRECEDING_INSTRUMENT_GROUP"
                            ),
                            "row_ordinal": wrapper_ordinal,
                        },
                    ]
                )
                group["hierarchy_path_exact"] = [None]
                group["label_exact"] = None
                wrapper["hierarchy_path_exact"] = [group_label]
                wrapper["label_exact"] = group_label
            table_projections.append(
                {
                    "complete_lane_equations": complete_lane_equations,
                    "parent_role_axis": [
                        item[3] for item in expected_parent_axis
                    ],
                    "parent_vectors_with_blanks_preserved": parent_vectors,
                    "projection_kind": (
                        "EXACT_THREE_INSTRUMENT_FACE_VALUE_BLOCKS_AND_"
                        "TERMINAL_FAMILY_TOTAL"
                    ),
                    "raw_source_rows": raw_rows,
                    "root_vector": root_vector,
                }
            )
        if not projections:
            continue
        projected_region = projected_regions[region_index]
        before_roles = canonical_clone_v1(projected_region["component_roles"])
        page = projected_pages[region["page_json_version_id"]]
        section = page["sections"][int(region["section_id"][1:]) - 1]
        classification = classify_gemini_json_multitable_hierarchical_table_v1(
            page, section, table, compiled_specs=compiled_specs
        )
        after_roles = _classification_component_roles_v1(classification)
        if not projected_child_roles <= set(after_roles):
            raise _error("issued-paper face-value projection classification drifted")
        projected_region["component_roles"] = after_roles
        locator = {
            key: region[key]
            for key in (
                "page_json_version_id",
                "physical_page",
                "section_id",
                "table_id",
            )
        }
        material = {
            "format_version": FACE_VALUE_WRAPPER_RECEIPT_FORMAT_VERSION,
            "locator": locator,
            "projections": projections,
            "region_component_roles": {
                "after": after_roles,
                "before": before_roles,
            },
            "rule": (
                "EXACT_INSTRUMENT_GROUP_IMMEDIATELY_FOLLOWED_BY_FACE_VALUE_"
                "SUBTOTAL_THEN_EXACT_TENOR_ITEMS_STRUCTURAL_SOURCE_SYNTAX_ONLY"
            ),
            "table_projections": table_projections,
        }
        receipts.append(
            {
                **material,
                "face_value_wrapper_receipt_id": (
                    "gjivpfafwv1:receipt:" + canonical_json_sha256_v1(material)
                ),
            }
        )
    return projected_pages, projected_regions, receipts


def _project_tenor_carrier_instrument_rows(
    *,
    pages: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[
    dict[str, dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    """Restore a printed tenor carrier omitted from child hierarchy paths.

    Some source tables print one tenor total followed immediately by its
    instrument-specific rows, while selected JSON flattens every hierarchy
    path to the row label.  Exact configured tenor aliases and exact configured
    instrument labels establish the source tree without consulting values.
    Only hierarchy paths and the corresponding region role frontier change.
    """

    projected_pages = {
        version_id: canonical_clone_v1(page) for version_id, page in pages.items()
    }
    projected_regions = canonical_clone_v1(list(regions))
    receipts = []
    for region_index, region in enumerate(regions):
        table = _region_table(projected_pages, region)
        rows = table.get("rows")
        if type(rows) is not list:
            continue
        projections = []
        projected_child_roles: set[str] = set()
        for carrier_index, carrier in enumerate(rows):
            if type(carrier) is not dict or carrier.get("row_kind") not in {
                "GROUP",
                "ITEM",
                "SUBTOTAL",
            }:
                continue
            if carrier.get("hierarchy_path_exact") != [carrier.get("label_exact")]:
                continue
            child_role_by_instrument = {
                instrument_role: child_role
                for instrument_role in sorted(_INSTRUMENT_ROLES)
                if (
                    child_role := _exact_declared_role(
                        carrier.get("label_exact"),
                        compiled_specs=compiled_specs,
                        roles={
                            role
                            for role, child in compiled_specs["child_by_role"].items()
                            if type(child) is dict
                            and child.get("role_kind") == "ADDITIVE_CHILD"
                        },
                        within_role=instrument_role,
                    )
                )
                is not None
            }
            if not child_role_by_instrument:
                continue
            for child_index in range(carrier_index + 1, len(rows)):
                child = rows[child_index]
                if type(child) is not dict or child.get("row_kind") != "ITEM":
                    break
                instrument_role = _exact_declared_role(
                    child.get("label_exact"),
                    compiled_specs=compiled_specs,
                    roles=_INSTRUMENT_ROLES,
                    within_role=None,
                )
                child_role = child_role_by_instrument.get(instrument_role)
                if instrument_role is None or child_role is None:
                    break
                before_path = child.get("hierarchy_path_exact")
                if before_path != [child.get("label_exact")]:
                    break
                after_path = [carrier.get("label_exact"), child.get("label_exact")]
                projections.append(
                    {
                        "after_hierarchy_path_exact": canonical_clone_v1(after_path),
                        "before_hierarchy_path_exact": canonical_clone_v1(before_path),
                        "child_role": child_role,
                        "instrument_role": instrument_role,
                        "label_exact": child.get("label_exact"),
                        "row_ordinal": child_index + 1,
                        "tenor_carrier": {
                            "hierarchy_path_exact": canonical_clone_v1(
                                carrier.get("hierarchy_path_exact")
                            ),
                            "label_exact": carrier.get("label_exact"),
                            "row_kind": carrier.get("row_kind"),
                            "row_ordinal": carrier_index + 1,
                        },
                    }
                )
                projected_child_roles.add(child_role)
                child["hierarchy_path_exact"] = canonical_clone_v1(after_path)
        if not projections:
            continue
        projected_region = projected_regions[region_index]
        before_roles = canonical_clone_v1(projected_region["component_roles"])
        page = projected_pages[region["page_json_version_id"]]
        section = page["sections"][int(region["section_id"][1:]) - 1]
        classification = classify_gemini_json_multitable_hierarchical_table_v1(
            page,
            section,
            table,
            compiled_specs=compiled_specs,
        )
        after_roles = sorted(
            {
                *(hit["role"] for hit in classification["role_hits"]),
                *classification["context_roles"],
                *(
                    hit["role"]
                    for hit in classification.get("transposed_column_role_hits", [])
                    if hit.get("status", "").startswith("EXACT_")
                ),
                *(
                    hit["role"]
                    for hit in classification.get("transposed_row_role_hits", [])
                ),
            }
        )
        if not projected_child_roles <= set(after_roles):
            raise _error("issued-paper tenor projection classification drifted")
        projected_region["component_roles"] = after_roles
        locator = {
            key: region[key]
            for key in (
                "page_json_version_id",
                "physical_page",
                "section_id",
                "table_id",
            )
        }
        material = {
            "format_version": TENOR_INSTRUMENT_PROJECTION_RECEIPT_FORMAT_VERSION,
            "locator": locator,
            "projections": projections,
            "region_component_roles": {"after": after_roles, "before": before_roles},
            "rule": (
                "EXACT_TENOR_CARRIER_FOLLOWED_IMMEDIATELY_BY_EXACT_INSTRUMENT_"
                "ROWS_HIERARCHY_ONLY_NO_VALUE_SELECTION"
            ),
        }
        receipts.append(
            {
                **material,
                "tenor_instrument_projection_receipt_id": (
                    "gjivptiprv1:receipt:" + canonical_json_sha256_v1(material)
                ),
            }
        )
    return projected_pages, projected_regions, receipts


def _classification_component_roles_v1(
    classification: Mapping[str, Any],
) -> list[str]:
    return sorted(
        {
            *(
                hit["role"]
                for hit in classification.get("role_hits", [])
                if type(hit) is dict and type(hit.get("role")) is str
            ),
            *(classification.get("context_roles") or []),
            *(
                hit["role"]
                for hit in classification.get("transposed_column_role_hits", [])
                if type(hit) is dict
                and type(hit.get("role")) is str
                and hit.get("status", "").startswith("EXACT_")
            ),
            *(
                hit["role"]
                for hit in classification.get("transposed_row_role_hits", [])
                if type(hit) is dict and type(hit.get("role")) is str
            ),
        }
    )


def _project_exact_validation_rows_v1(
    *,
    pages: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Project two narrow validation shapes without manufacturing a value."""

    projected_pages = {
        version_id: canonical_clone_v1(page) for version_id, page in pages.items()
    }
    projected_regions = canonical_clone_v1(list(regions))
    receipts = []
    validation_roles = set(compiled_specs["validation_only_roles"])
    for region_index, region in enumerate(regions):
        table = _region_table(projected_pages, region)
        rows = table.get("rows")
        money_ordinals = _money_ordinals(table)
        if (
            type(rows) is not list
            or len(rows) != 3
            or money_ordinals != [1, 2]
            or any(type(row) is not dict for row in rows)
            or rows[-1].get("row_kind") != "TOTAL"
        ):
            continue
        first = _observed_money_coefficients_v1(rows[0], money_ordinals=money_ordinals)
        second = _observed_money_coefficients_v1(rows[1], money_ordinals=money_ordinals)
        total = _observed_money_coefficients_v1(rows[2], money_ordinals=money_ordinals)
        first_role = _exact_declared_role(
            rows[0].get("label_exact"),
            compiled_specs=compiled_specs,
            roles=validation_roles,
            within_role=None,
        )
        second_role = _exact_declared_role(
            rows[1].get("label_exact"),
            compiled_specs=compiled_specs,
            roles=validation_roles,
            within_role=None,
        )
        row_projections = []
        rule = None
        if (
            rows[0].get("row_kind") == "ITEM"
            and rows[1].get("row_kind") == "ITEM"
            and first is not None
            and total == first
            and second is None
            and type(rows[1].get("values_exact")) is list
            and all(value is None for value in rows[1]["values_exact"])
            and first_role is not None
            and second_role is not None
        ):
            row_projections.append(
                {
                    "after_row_kind": "GROUP",
                    "before_hierarchy_path_exact": canonical_clone_v1(
                        rows[1].get("hierarchy_path_exact")
                    ),
                    "before_label_exact": rows[1].get("label_exact"),
                    "before_row_kind": "ITEM",
                    "row_ordinal": 2,
                }
            )
            rows[1]["row_kind"] = "GROUP"
            rule = (
                "EXACT_ALL_NULL_VALIDATION_SIBLING_BETWEEN_VISIBLE_VALIDATION_"
                "ROW_AND_EQUAL_TERMINAL_TOTAL_STRUCTURAL_ONLY"
            )
        elif (
            rows[0].get("row_kind") == "ITEM"
            and rows[1].get("row_kind") == "ITEM"
            and _normalized(rows[0].get("label_exact"))
            == "giay to co gia bang vnd"
            and _normalized(rows[1].get("label_exact")) == "menh gia"
            and first is not None
            and second == first
            and total == first
            and first_role is not None
            and second_role is not None
            and rows[0].get("hierarchy_path_exact") == [rows[0].get("label_exact")]
            and rows[1].get("hierarchy_path_exact") == [rows[1].get("label_exact")]
        ):
            after_path = [rows[0].get("label_exact"), rows[1].get("label_exact")]
            row_projections.append(
                {
                    "after_hierarchy_path_exact": canonical_clone_v1(after_path),
                    "before_hierarchy_path_exact": canonical_clone_v1(
                        rows[1].get("hierarchy_path_exact")
                    ),
                    "before_label_exact": rows[1].get("label_exact"),
                    "before_row_kind": rows[1].get("row_kind"),
                    "row_ordinal": 2,
                }
            )
            rows[1]["hierarchy_path_exact"] = after_path
            rule = (
                "EXACT_FACE_VALUE_VALIDATION_ROW_WRAPPED_BY_EQUAL_VISIBLE_"
                "CURRENCY_ROW_AND_EQUAL_TERMINAL_TOTAL_HIERARCHY_ONLY"
            )
        if not row_projections or rule is None:
            continue
        page = projected_pages[region["page_json_version_id"]]
        section = page["sections"][int(region["section_id"][1:]) - 1]
        classification = classify_gemini_json_multitable_hierarchical_table_v1(
            page, section, table, compiled_specs=compiled_specs
        )
        before_roles = canonical_clone_v1(projected_regions[region_index]["component_roles"])
        after_roles = _classification_component_roles_v1(classification)
        projected_regions[region_index]["component_roles"] = after_roles
        locator = {
            key: region[key]
            for key in ("page_json_version_id", "physical_page", "section_id", "table_id")
        }
        material = {
            "format_version": VALIDATION_ROW_PROJECTION_RECEIPT_FORMAT_VERSION,
            "locator": locator,
            "observed_axis": {"first": first, "second": second, "total": total},
            "region_component_roles": {"after": after_roles, "before": before_roles},
            "row_projections": row_projections,
            "rule": rule,
        }
        receipts.append(
            {
                **material,
                "validation_row_projection_receipt_id": (
                    "gjivpvrprv1:receipt:" + canonical_json_sha256_v1(material)
                ),
            }
        )
    return projected_pages, projected_regions, receipts


def _project_adjacent_source_syntax_v1(
    *,
    pages: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Restore only the missing sender edge and blank receiver axes.

    A receiver's explicit ``CONTINUES_FROM_PREVIOUS_PAGE`` marker, physical
    adjacency, and the two page-edge table positions authenticate the graph
    edge.  When Gemini omitted the reciprocal sender marker, it is projected
    solely for generic continuation evaluation.  Fully blank receiver period
    headers and units may copy the exact preceding carrier surfaces; values are
    never inspected or changed here.
    """

    projected_pages = {
        version_id: canonical_clone_v1(page) for version_id, page in pages.items()
    }
    projected_regions = canonical_clone_v1(list(regions))
    receipts_by_locator: dict[tuple[str, str, str], dict[str, Any]] = {}

    def receipt_for(
        *, region: Mapping[str, Any], before_roles: Sequence[str]
    ) -> dict[str, Any]:
        key = (
            region["page_json_version_id"],
            region["section_id"],
            region["table_id"],
        )
        if key not in receipts_by_locator:
            receipts_by_locator[key] = {
                "column_projections": [],
                "format_version": (
                    ADJACENT_SOURCE_SYNTAX_PROJECTION_RECEIPT_FORMAT_VERSION
                ),
                "locator": {
                    field: region[field]
                    for field in (
                        "page_json_version_id",
                        "physical_page",
                        "section_id",
                        "table_id",
                    )
                },
                "region_component_roles": {
                    "after": canonical_clone_v1(list(before_roles)),
                    "before": canonical_clone_v1(list(before_roles)),
                },
                "row_projections": [],
                "rule": (
                    "EXACT_PHYSICAL_AND_SELECTED_ADJACENT_PAGE_EDGE_"
                    "CONTINUATION_RECIPROCAL_MARKER_AND_BLANK_AXIS_ONLY"
                ),
                "table_projections": [],
            }
        return receipts_by_locator[key]

    for receiver_index, receiver_region in enumerate(projected_regions):
        if receiver_index == 0:
            continue
        receiver_table = _region_table(projected_pages, receiver_region)
        if receiver_table.get("continuation") != "CONTINUES_FROM_PREVIOUS_PAGE":
            continue
        prior_index = receiver_index - 1
        prior_region = projected_regions[prior_index]
        if (
            prior_region.get("document_id") != receiver_region.get("document_id")
            or prior_region.get("source_sha256")
            != receiver_region.get("source_sha256")
            or prior_region.get("physical_page", -2) + 1
            != receiver_region.get("physical_page")
            or prior_region.get("selected_page_ordinal", -2) + 1
            != receiver_region.get("selected_page_ordinal")
        ):
            continue
        prior_page = projected_pages.get(prior_region["page_json_version_id"])
        receiver_page = projected_pages.get(receiver_region["page_json_version_id"])
        if (
            type(prior_page) is not dict
            or type(receiver_page) is not dict
            or not _table_is_page_edge_v1(
                page=prior_page,
                section_id=prior_region["section_id"],
                table_id=prior_region["table_id"],
                edge="LAST",
            )
            or not _table_is_page_edge_v1(
                page=receiver_page,
                section_id=receiver_region["section_id"],
                table_id=receiver_region["table_id"],
                edge="FIRST",
            )
        ):
            continue
        prior_table = _region_table(projected_pages, prior_region)
        if prior_table.get("continuation") not in {
            "NONE",
            "CONTINUES_ON_NEXT_PAGE",
        }:
            continue

        prior_receipt = receipt_for(
            region=prior_region,
            before_roles=regions[prior_index]["component_roles"],
        )
        if prior_table.get("continuation") == "NONE":
            prior_receipt["table_projections"].append(
                {
                    "after_continuation": "CONTINUES_ON_NEXT_PAGE",
                    "before_continuation": "NONE",
                    "projection_kind": (
                        "RECIPROCAL_SENDER_MARKER_FROM_EXACT_ADJACENT_RECEIVER"
                    ),
                }
            )
            prior_table["continuation"] = "CONTINUES_ON_NEXT_PAGE"

        receiver_receipt = receipt_for(
            region=receiver_region,
            before_roles=regions[receiver_index]["component_roles"],
        )
        receiver_columns = receiver_table.get("columns")
        prior_columns = prior_table.get("columns")
        receiver_money = _money_ordinals(receiver_table)
        prior_axis = _two_period_axis(prior_table)
        receiver_headers_blank = bool(receiver_money) and all(
            not any(
                _normalized(value)
                for value in receiver_columns[ordinal - 1].get(
                    "header_path_exact", []
                )
            )
            for ordinal in receiver_money
        ) if type(receiver_columns) is list else False
        if (
            type(receiver_columns) is list
            and type(prior_columns) is list
            and receiver_headers_blank
            and prior_axis.get("complete") is True
            and prior_axis.get("money_column_ordinals")
            and len(prior_axis["money_column_ordinals"]) == len(receiver_money)
        ):
            for receiver_ordinal, prior_ordinal in zip(
                receiver_money,
                prior_axis["money_column_ordinals"],
                strict=True,
            ):
                before_path = canonical_clone_v1(
                    receiver_columns[receiver_ordinal - 1].get("header_path_exact")
                )
                after_path = canonical_clone_v1(
                    prior_columns[prior_ordinal - 1].get("header_path_exact")
                )
                receiver_columns[receiver_ordinal - 1][
                    "header_path_exact"
                ] = after_path
                receiver_receipt["column_projections"].append(
                    {
                        "after_header_path_exact": after_path,
                        "before_header_path_exact": before_path,
                        "column_ordinal": receiver_ordinal,
                        "inherited_from_column_ordinal": prior_ordinal,
                        "inherited_from_locator": {
                            field: prior_region[field]
                            for field in (
                                "page_json_version_id",
                                "physical_page",
                                "section_id",
                                "table_id",
                            )
                        },
                        "projection_kind": (
                            "BLANK_RECEIVER_PERIOD_HEADER_FROM_EXACT_SENDER_AXIS"
                        ),
                    }
                )
        if (
            not _normalized(receiver_table.get("unit_exact"))
            and _normalized(prior_table.get("unit_exact"))
        ):
            receiver_receipt["table_projections"].append(
                {
                    "after_unit_exact": prior_table.get("unit_exact"),
                    "before_unit_exact": receiver_table.get("unit_exact"),
                    "inherited_from_locator": {
                        field: prior_region[field]
                        for field in (
                            "page_json_version_id",
                            "physical_page",
                            "section_id",
                            "table_id",
                        )
                    },
                    "projection_kind": (
                        "BLANK_RECEIVER_UNIT_FROM_EXACT_ADJACENT_SENDER"
                    ),
                }
            )
            receiver_table["unit_exact"] = prior_table.get("unit_exact")

    dropped_region_indices: set[int] = set()
    output_roles = set(compiled_specs["output_role_order"])
    root_component_roles = set(compiled_specs["root_component_roles"]) - set(
        compiled_specs["validation_only_roles"]
    )
    for receiver_index in range(1, len(projected_regions)):
        prior_index = receiver_index - 1
        prior_region = projected_regions[prior_index]
        receiver_region = projected_regions[receiver_index]
        prior_table = _region_table(projected_pages, prior_region)
        receiver_table = _region_table(projected_pages, receiver_region)
        if (
            prior_table.get("continuation") != "CONTINUES_ON_NEXT_PAGE"
            or receiver_table.get("continuation")
            != "CONTINUES_FROM_PREVIOUS_PAGE"
            or prior_region.get("physical_page", -2) + 1
            != receiver_region.get("physical_page")
            or prior_region.get("selected_page_ordinal", -2) + 1
            != receiver_region.get("selected_page_ordinal")
            or prior_region.get("source_sha256")
            != receiver_region.get("source_sha256")
        ):
            continue
        prior_page = projected_pages[prior_region["page_json_version_id"]]
        receiver_page = projected_pages[receiver_region["page_json_version_id"]]
        prior_section = prior_page["sections"][int(prior_region["section_id"][1:]) - 1]
        receiver_section = receiver_page["sections"][
            int(receiver_region["section_id"][1:]) - 1
        ]
        prior_classification = classify_gemini_json_multitable_hierarchical_table_v1(
            prior_page,
            prior_section,
            prior_table,
            compiled_specs=compiled_specs,
        )
        receiver_classification = (
            classify_gemini_json_multitable_hierarchical_table_v1(
                receiver_page,
                receiver_section,
                receiver_table,
                compiled_specs=compiled_specs,
            )
        )

        # One leading generic tenor is the visibly continued final child of a
        # unique prior instrument carrier.  Scope only that first row and only
        # when the configured child matcher becomes unique under the carrier.
        prior_root_hits = [
            hit
            for hit in prior_classification.get("role_hits", [])
            if type(hit) is dict and hit.get("role") in root_component_roles
        ]
        receiver_rows = receiver_table.get("rows")
        receiver_hits = receiver_classification.get("role_hits")
        if (
            len(prior_root_hits) == 1
            and type(receiver_rows) is list
            and receiver_rows
            and type(receiver_rows[0]) is dict
            and type(receiver_hits) is list
            and [
                hit
                for hit in receiver_hits
                if type(hit) is dict and hit.get("row_ordinal") == 1
            ]
            == [
                {
                    "role": "GENERIC_ISSUED_PAPER_SOURCE",
                    "row_kind": receiver_rows[0].get("row_kind"),
                    "row_ordinal": 1,
                    "source_order": 1,
                }
            ]
            and type(receiver_rows[0].get("hierarchy_path_exact")) is list
            and len(receiver_rows[0]["hierarchy_path_exact"]) == 1
        ):
            carrier = prior_root_hits[0]
            child_role = _exact_declared_role(
                receiver_rows[0].get("label_exact"),
                compiled_specs=compiled_specs,
                roles=output_roles,
                within_role=carrier["role"],
            )
            prior_rows = prior_table.get("rows")
            carrier_row = (
                prior_rows[carrier["row_ordinal"] - 1]
                if type(prior_rows) is list
                and carrier["row_ordinal"] <= len(prior_rows)
                else None
            )
            if (
                child_role is not None
                and type(carrier_row) is dict
                and _normalized(carrier_row.get("label_exact"))
            ):
                before_path = canonical_clone_v1(
                    receiver_rows[0]["hierarchy_path_exact"]
                )
                after_path = [
                    carrier_row["label_exact"],
                    *canonical_clone_v1(before_path),
                ]
                receipt = receipt_for(
                    region=receiver_region,
                    before_roles=regions[receiver_index]["component_roles"],
                )
                receipt["row_projections"].append(
                    {
                        "after_hierarchy_path_exact": after_path,
                        "before_hierarchy_path_exact": before_path,
                        "before_label_exact": receiver_rows[0].get("label_exact"),
                        "before_row_kind": receiver_rows[0].get("row_kind"),
                        "child_role": child_role,
                        "continued_from_role": carrier["role"],
                        "continued_from_row_ordinal": carrier["row_ordinal"],
                        "row_ordinal": 1,
                    }
                )
                receiver_rows[0]["hierarchy_path_exact"] = after_path

        # A blank row carrying the exact owner label is structural, not a
        # zero-valued result.  It may be made transparent only when every
        # remaining sender row is a visible declared child and their exact
        # all-lane sum equals the receiver's sole terminal total.
        prior_rows = prior_table.get("rows")
        receiver_rows = receiver_table.get("rows")
        prior_money = _money_ordinals(prior_table)
        receiver_money = _money_ordinals(receiver_table)
        if (
            type(prior_rows) is list
            and len(prior_rows) >= 2
            and type(prior_rows[0]) is dict
            and prior_classification.get("family_root_row_ordinals") == [1]
            and _exact_parent_alias(
                prior_rows[0].get("label_exact"), compiled_specs=compiled_specs
            )
            is not None
            and type(prior_rows[0].get("values_exact")) is list
            and all(value is None for value in prior_rows[0]["values_exact"])
            and all(
                type(row) is dict and row.get("row_kind") == "ITEM"
                for row in prior_rows[1:]
            )
            and type(receiver_rows) is list
            and len(receiver_rows) == 1
            and type(receiver_rows[0]) is dict
            and receiver_rows[0].get("row_kind") == "TOTAL"
            and len(prior_money) == len(receiver_money) > 0
        ):
            child_vectors = [
                _observed_money_coefficients_v1(
                    row, money_ordinals=prior_money
                )
                for row in prior_rows[1:]
            ]
            receiver_total = _observed_money_coefficients_v1(
                receiver_rows[0], money_ordinals=receiver_money
            )
            child_hit_ordinals = {
                hit["row_ordinal"]
                for hit in prior_classification.get("role_hits", [])
                if type(hit) is dict
                and hit.get("role") in output_roles
                and type(hit.get("row_ordinal")) is int
                and hit["row_ordinal"] > 1
            }
            expected_total = (
                [
                    sum(vector[lane] for vector in child_vectors if vector is not None)
                    for lane in range(len(prior_money))
                ]
                if child_vectors and all(vector is not None for vector in child_vectors)
                else None
            )
            if (
                child_hit_ordinals == set(range(2, len(prior_rows) + 1))
                and expected_total == receiver_total
            ):
                receipt = receipt_for(
                    region=prior_region,
                    before_roles=regions[prior_index]["component_roles"],
                )
                receipt["table_projections"].append(
                    {
                        "dropped_blank_owner_wrapper": canonical_clone_v1(
                            prior_rows[0]
                        ),
                        "child_row_ordinals": sorted(child_hit_ordinals),
                        "exact_child_sum_axis": expected_total,
                        "projection_kind": (
                            "BLANK_OWNER_WRAPPER_SENDER_ROWS_COALESCED_INTO_"
                            "EXACT_ADJACENT_RECEIVER"
                        ),
                        "receiver_total_axis": receiver_total,
                    }
                )
                receiver_receipt = receipt_for(
                    region=receiver_region,
                    before_roles=regions[receiver_index]["component_roles"],
                )
                original_receiver_total = canonical_clone_v1(receiver_rows[0])
                combined_rows = [
                    *canonical_clone_v1(prior_rows[1:]),
                    original_receiver_total,
                ]
                receiver_receipt["table_projections"].append(
                    {
                        "after_continuation": "NONE",
                        "before_continuation": (
                            "CONTINUES_FROM_PREVIOUS_PAGE"
                        ),
                        "exact_child_sum_axis": expected_total,
                        "projected_row_count": len(combined_rows),
                        "projection_kind": (
                            "EXACT_ADJACENT_BLANK_OWNER_WRAPPER_SENDER_CHILD_"
                            "ROWS_AND_RECEIVER_TOTAL_COALESCED_WITH_SOURCE_"
                            "LOCATORS_PRESERVED"
                        ),
                        "receiver_total_axis": receiver_total,
                    }
                )
                for projected_ordinal, source_row in enumerate(
                    prior_rows[1:], start=1
                ):
                    receiver_receipt["row_projections"].append(
                        {
                            "after_hierarchy_path_exact": canonical_clone_v1(
                                source_row.get("hierarchy_path_exact")
                            ),
                            "after_label_exact": source_row.get("label_exact"),
                            "after_row_kind": source_row.get("row_kind"),
                            "before_hierarchy_path_exact": canonical_clone_v1(
                                source_row.get("hierarchy_path_exact")
                            ),
                            "before_label_exact": source_row.get("label_exact"),
                            "before_locator": {
                                field: prior_region[field]
                                for field in (
                                    "page_json_version_id",
                                    "physical_page",
                                    "section_id",
                                    "table_id",
                                )
                            },
                            "before_row_kind": source_row.get("row_kind"),
                            "before_row_ordinal": projected_ordinal + 1,
                            "row_ordinal": projected_ordinal,
                        }
                    )
                receiver_receipt["row_projections"].append(
                    {
                        "after_hierarchy_path_exact": canonical_clone_v1(
                            original_receiver_total.get("hierarchy_path_exact")
                        ),
                        "after_label_exact": original_receiver_total.get(
                            "label_exact"
                        ),
                        "after_row_kind": original_receiver_total.get("row_kind"),
                        "before_hierarchy_path_exact": canonical_clone_v1(
                            original_receiver_total.get("hierarchy_path_exact")
                        ),
                        "before_label_exact": original_receiver_total.get(
                            "label_exact"
                        ),
                        "before_locator": {
                            field: receiver_region[field]
                            for field in (
                                "page_json_version_id",
                                "physical_page",
                                "section_id",
                                "table_id",
                            )
                        },
                        "before_row_kind": original_receiver_total.get("row_kind"),
                        "before_row_ordinal": 1,
                        "row_ordinal": len(combined_rows),
                    }
                )
                receiver_table["continuation"] = "NONE"
                receiver_table["rows"] = combined_rows
                dropped_region_indices.add(prior_index)

        # Some VAB notes print only generic maturity buckets beneath the
        # exact owner on the page-final sender, followed by one titleless
        # terminal total on the explicitly continued receiver.  The bucket
        # population does not identify an instrument, so it remains a
        # validation-only population.  Coalesce the two physical fragments
        # only when every source row is observed, the all-lane equation is
        # exact, and the receiver has no competing semantic surface.  This
        # exposes the printed family total without guessing any child role.
        if prior_index not in dropped_region_indices:
            prior_rows = prior_table.get("rows")
            receiver_rows = receiver_table.get("rows")
            prior_money = _money_ordinals(prior_table)
            receiver_money = _money_ordinals(receiver_table)
            owner_surfaces = [
                {
                    "source_exact": prior_section.get("title_exact"),
                    "source_kind": "SECTION_TITLE",
                },
                {
                    "source_exact": prior_table.get("title_exact"),
                    "source_kind": "TABLE_TITLE",
                },
            ]
            owner_matches = [
                {**surface, "alias": alias}
                for surface in owner_surfaces
                if (
                    alias := _exact_owner_alias(
                        surface["source_exact"], compiled_specs=compiled_specs
                    )
                )
                is not None
            ]
            receiver_surfaces = [
                receiver_section.get("title_exact"),
                *(receiver_section.get("narratives_exact") or []),
                receiver_table.get("title_exact"),
            ]
            prior_vectors = (
                [
                    _observed_money_coefficients_v1(
                        row, money_ordinals=prior_money
                    )
                    for row in prior_rows
                ]
                if type(prior_rows) is list
                else []
            )
            receiver_item_vectors = (
                [
                    _observed_money_coefficients_v1(
                        row, money_ordinals=receiver_money
                    )
                    for row in receiver_rows[:-1]
                ]
                if type(receiver_rows) is list
                else []
            )
            receiver_total = (
                _observed_money_coefficients_v1(
                    receiver_rows[-1], money_ordinals=receiver_money
                )
                if type(receiver_rows) is list
                and receiver_rows
                and type(receiver_rows[-1]) is dict
                else None
            )
            component_vectors = [*prior_vectors, *receiver_item_vectors]
            expected_total = (
                [
                    sum(
                        vector[lane]
                        for vector in component_vectors
                        if vector is not None
                    )
                    for lane in range(len(prior_money))
                ]
                if component_vectors
                and all(vector is not None for vector in component_vectors)
                else None
            )
            prior_role_hits = prior_classification.get("role_hits")
            receiver_role_hits = receiver_classification.get("role_hits")
            validation_roles = set(compiled_specs["validation_only_roles"])
            explicit_units = {
                _normalized(table.get("unit_exact"))
                for table in (prior_table, receiver_table)
                if _normalized(table.get("unit_exact"))
            }
            if (
                type(prior_rows) is list
                and prior_rows
                and all(
                    type(row) is dict and row.get("row_kind") == "ITEM"
                    for row in prior_rows
                )
                and type(prior_role_hits) is list
                and len(prior_role_hits) == len(prior_rows)
                and {
                    hit.get("row_ordinal")
                    for hit in prior_role_hits
                    if type(hit) is dict
                }
                == set(range(1, len(prior_rows) + 1))
                and {
                    hit.get("role")
                    for hit in prior_role_hits
                    if type(hit) is dict
                }
                <= validation_roles
                and prior_classification.get("context_roles") == []
                and prior_classification.get("family_root_row_ordinals") == []
                and prior_classification.get("total_rows") == []
                and prior_classification.get("ambiguous_rows") == []
                and prior_classification.get("unbound_money_row_ordinals") == []
                and type(receiver_rows) is list
                and receiver_rows
                and all(
                    type(row) is dict and row.get("row_kind") == "ITEM"
                    for row in receiver_rows[:-1]
                )
                and type(receiver_rows[-1]) is dict
                and receiver_rows[-1].get("row_kind") == "TOTAL"
                and not _normalized(receiver_rows[-1].get("label_exact"))
                and not any(
                    _normalized(value)
                    for value in receiver_rows[-1].get(
                        "hierarchy_path_exact", []
                    )
                )
                and type(receiver_role_hits) is list
                and len(receiver_role_hits) == len(receiver_rows) - 1
                and {
                    hit.get("row_ordinal")
                    for hit in receiver_role_hits
                    if type(hit) is dict
                }
                == set(range(1, len(receiver_rows)))
                and {
                    hit.get("role")
                    for hit in receiver_role_hits
                    if type(hit) is dict
                }
                <= validation_roles
                and receiver_classification.get("context_roles") == []
                and receiver_classification.get("family_root_row_ordinals") == []
                and receiver_classification.get("ambiguous_rows") == []
                and receiver_classification.get("total_rows")
                == [
                    {
                        "row_kind": "TOTAL",
                        "row_ordinal": len(receiver_rows),
                        "source_order": len(receiver_rows),
                    }
                ]
                and receiver_classification.get("unbound_money_row_ordinals")
                == [len(receiver_rows)]
                and len(owner_matches) == 1
                and not any(_normalized(surface) for surface in receiver_surfaces)
                and len(explicit_units) <= 1
                and _two_period_axis(prior_table).get("complete") is True
                and _two_period_axis(receiver_table).get("complete") is True
                and _two_period_axis(prior_table).get("signatures")
                == _two_period_axis(receiver_table).get("signatures")
                and len(prior_money) == len(receiver_money) > 0
                and expected_total is not None
                and expected_total == receiver_total
            ):
                owner = owner_matches[0]
                prior_receipt = receipt_for(
                    region=prior_region,
                    before_roles=regions[prior_index]["component_roles"],
                )
                prior_receipt["table_projections"].append(
                    {
                        "exact_generic_bucket_sum_axis": expected_total,
                        "owner_alias": owner["alias"],
                        "owner_source_exact": owner["source_exact"],
                        "owner_source_kind": owner["source_kind"],
                        "projection_kind": (
                            "PAGE_FINAL_EXACT_OWNER_GENERIC_BUCKET_SENDER_"
                            "COALESCED_INTO_TITLELESS_ADJACENT_TOTAL_RECEIVER"
                        ),
                        "raw_sender_rows": canonical_clone_v1(prior_rows),
                    }
                )
                receiver_receipt = receipt_for(
                    region=receiver_region,
                    before_roles=regions[receiver_index]["component_roles"],
                )
                original_receiver_rows = canonical_clone_v1(receiver_rows)
                combined_rows = [
                    *canonical_clone_v1(prior_rows),
                    *canonical_clone_v1(original_receiver_rows),
                ]
                combined_rows[-1]["label_exact"] = owner["source_exact"]
                combined_rows[-1]["hierarchy_path_exact"] = [
                    owner["source_exact"]
                ]
                receiver_receipt["table_projections"].append(
                    {
                        "after_continuation": "NONE",
                        "before_continuation": (
                            "CONTINUES_FROM_PREVIOUS_PAGE"
                        ),
                        "exact_generic_bucket_sum_axis": expected_total,
                        "owner_alias": owner["alias"],
                        "owner_source_exact": owner["source_exact"],
                        "owner_source_kind": owner["source_kind"],
                        "projection_kind": (
                            "TITLELESS_RECEIVER_TOTAL_SCOPED_BY_EXACT_ADJACENT_"
                            "OWNER_AND_ALL_LANE_GENERIC_BUCKET_EQUATION"
                        ),
                        "raw_receiver_rows": original_receiver_rows,
                        "receiver_total_axis": receiver_total,
                    }
                )
                for projected_ordinal, source_row in enumerate(prior_rows, start=1):
                    receiver_receipt["row_projections"].append(
                        {
                            "after_hierarchy_path_exact": canonical_clone_v1(
                                source_row.get("hierarchy_path_exact")
                            ),
                            "after_label_exact": source_row.get("label_exact"),
                            "after_row_kind": source_row.get("row_kind"),
                            "before_hierarchy_path_exact": canonical_clone_v1(
                                source_row.get("hierarchy_path_exact")
                            ),
                            "before_label_exact": source_row.get("label_exact"),
                            "before_locator": {
                                field: prior_region[field]
                                for field in (
                                    "page_json_version_id",
                                    "physical_page",
                                    "section_id",
                                    "table_id",
                                )
                            },
                            "before_row_kind": source_row.get("row_kind"),
                            "before_row_ordinal": projected_ordinal,
                            "row_ordinal": projected_ordinal,
                        }
                    )
                for receiver_row_ordinal, source_row in enumerate(
                    original_receiver_rows, start=1
                ):
                    projected_ordinal = len(prior_rows) + receiver_row_ordinal
                    is_total = receiver_row_ordinal == len(original_receiver_rows)
                    receiver_receipt["row_projections"].append(
                        {
                            "after_hierarchy_path_exact": (
                                [owner["source_exact"]]
                                if is_total
                                else canonical_clone_v1(
                                    source_row.get("hierarchy_path_exact")
                                )
                            ),
                            "after_label_exact": (
                                owner["source_exact"]
                                if is_total
                                else source_row.get("label_exact")
                            ),
                            "after_row_kind": source_row.get("row_kind"),
                            "before_hierarchy_path_exact": canonical_clone_v1(
                                source_row.get("hierarchy_path_exact")
                            ),
                            "before_label_exact": source_row.get("label_exact"),
                            "before_locator": {
                                field: receiver_region[field]
                                for field in (
                                    "page_json_version_id",
                                    "physical_page",
                                    "section_id",
                                    "table_id",
                                )
                            },
                            "before_row_kind": source_row.get("row_kind"),
                            "before_row_ordinal": receiver_row_ordinal,
                            "row_ordinal": projected_ordinal,
                        }
                    )
                receiver_table["continuation"] = "NONE"
                receiver_table["rows"] = combined_rows
                dropped_region_indices.add(prior_index)

        # A one-row receiver that exactly repeats its sender's terminal total
        # is corroboration, not a second source population.  Drop it only when
        # it has no declared family role of its own.
        prior_rows = prior_table.get("rows")
        receiver_rows = receiver_table.get("rows")
        if (
            type(prior_rows) is list
            and prior_rows
            and type(prior_rows[-1]) is dict
            and prior_rows[-1].get("row_kind") == "TOTAL"
            and type(receiver_rows) is list
            and len(receiver_rows) == 1
            and type(receiver_rows[0]) is dict
            and receiver_rows[0].get("row_kind") == "TOTAL"
            and receiver_classification.get("role_hits") == []
            and receiver_classification.get("context_roles") == []
            and receiver_classification.get("family_root_row_ordinals") == []
            and _observed_money_coefficients_v1(
                prior_rows[-1], money_ordinals=_money_ordinals(prior_table)
            )
            == _observed_money_coefficients_v1(
                receiver_rows[0], money_ordinals=_money_ordinals(receiver_table)
            )
            is not None
        ):
            receipt = receipt_for(
                region=receiver_region,
                before_roles=regions[receiver_index]["component_roles"],
            )
            receipt["table_projections"].append(
                {
                    "dropped_exact_duplicate_receiver_region": canonical_clone_v1(
                        receiver_region
                    ),
                    "exact_sender_total_axis": _observed_money_coefficients_v1(
                        prior_rows[-1], money_ordinals=_money_ordinals(prior_table)
                    ),
                    "receiver_source_rows": canonical_clone_v1(receiver_rows),
                    "projection_kind": (
                        "ONE_ROW_RECEIVER_EXACTLY_DUPLICATES_SENDER_TERMINAL_TOTAL"
                    ),
                }
            )
            dropped_region_indices.add(receiver_index)

    # One adjacent detail presentation can expose four source metrics for the
    # current reporting date while the preceding summary supplies the two
    # reporting periods.  Validate every visible face/discount/premium/net
    # equation and both parent totals before exposing only the printed net
    # column as the schema valuation metric.
    metric_alias_by_role = {
        "CARRYING_VALUE": "gia tri thuan",
        "DISCOUNT": "chiet khau",
        "FACE_VALUE": "menh gia",
        "PREMIUM": "phu troi",
    }
    for receiver_index in range(1, len(projected_regions)):
        if receiver_index in dropped_region_indices:
            continue
        prior_index = receiver_index - 1
        if prior_index in dropped_region_indices:
            continue
        prior_region = projected_regions[prior_index]
        receiver_region = projected_regions[receiver_index]
        prior_table = _region_table(projected_pages, prior_region)
        receiver_table = _region_table(projected_pages, receiver_region)
        if (
            prior_table.get("continuation") != "CONTINUES_ON_NEXT_PAGE"
            or receiver_table.get("continuation")
            != "CONTINUES_FROM_PREVIOUS_PAGE"
            or prior_region.get("physical_page", -2) + 1
            != receiver_region.get("physical_page")
            or prior_region.get("selected_page_ordinal", -2) + 1
            != receiver_region.get("selected_page_ordinal")
        ):
            continue
        columns = receiver_table.get("columns")
        rows = receiver_table.get("rows")
        prior_rows = prior_table.get("rows")
        if (
            type(columns) is not list
            or type(rows) is not list
            or type(prior_rows) is not list
            or len(columns) != 4
            or len(rows) != 6
            or any(
                type(column) is not dict or column.get("value_kind") != "MONEY"
                for column in columns
            )
            or any(type(row) is not dict for row in rows)
        ):
            continue
        metric_ordinals: dict[str, int] = {}
        metric_axis_valid = True
        for ordinal, column in enumerate(columns, start=1):
            header = " ".join(
                value
                for value in column.get("header_path_exact", [])
                if type(value) is str
            )
            matches = [
                role
                for role, alias in metric_alias_by_role.items()
                if _normalized(header) == alias
            ]
            if len(matches) != 1 or matches[0] in metric_ordinals:
                metric_axis_valid = False
                break
            metric_ordinals[matches[0]] = ordinal
        if not metric_axis_valid or set(metric_ordinals) != set(metric_alias_by_role):
            continue
        receiver_page = projected_pages[receiver_region["page_json_version_id"]]
        receiver_section = receiver_page["sections"][
            int(receiver_region["section_id"][1:]) - 1
        ]
        date_surfaces = [receiver_table.get("title_exact")]
        visible_dates = sorted(
            {
                value.isoformat()
                for surface in date_surfaces
                if type(surface) is str
                for value in _surface_dates(surface)
            }
        )
        if len(visible_dates) != 1:
            continue
        row_equations = []
        equations_valid = True
        for row_ordinal, row in enumerate(rows, start=1):
            values = row.get("values_exact")
            if type(values) is not list or len(values) != len(columns):
                equations_valid = False
                break
            metric_cells = {
                role: _source_money(values[ordinal - 1])
                for role, ordinal in metric_ordinals.items()
            }
            coefficients = {
                role: observed_source_coefficient_v1(cell)
                for role, cell in metric_cells.items()
            }
            if all(coefficient is None for coefficient in coefficients.values()):
                continue
            if any(coefficient is None for coefficient in coefficients.values()):
                equations_valid = False
                break
            computed = (
                coefficients["FACE_VALUE"]
                - coefficients["DISCOUNT"]
                + coefficients["PREMIUM"]
            )
            if computed != coefficients["CARRYING_VALUE"]:
                equations_valid = False
                break
            row_equations.append(
                {
                    "computed_carrying_value": computed,
                    "metric_cells": canonical_clone_v1(metric_cells),
                    "row_ordinal": row_ordinal,
                    "status": "EXACT",
                }
            )
        if not equations_valid or not row_equations:
            continue
        prior_page = projected_pages[prior_region["page_json_version_id"]]
        prior_section = prior_page["sections"][int(prior_region["section_id"][1:]) - 1]
        prior_classification = classify_gemini_json_multitable_hierarchical_table_v1(
            prior_page,
            prior_section,
            prior_table,
            compiled_specs=compiled_specs,
        )
        receiver_classification = (
            classify_gemini_json_multitable_hierarchical_table_v1(
                receiver_page,
                receiver_section,
                receiver_table,
                compiled_specs=compiled_specs,
            )
        )
        parent_hits = {
            hit["role"]: hit["row_ordinal"]
            for hit in prior_classification.get("role_hits", [])
            if type(hit) is dict and hit.get("role") in {"BOND", "CERTIFICATE_OF_DEPOSIT"}
        }
        receiver_parent_hits = {
            hit["role"]: hit["row_ordinal"]
            for hit in receiver_classification.get("role_hits", [])
            if type(hit) is dict and hit.get("role") in {"BOND", "CERTIFICATE_OF_DEPOSIT"}
        }
        prior_axis = _two_period_axis(prior_table)
        prior_money = prior_axis.get("money_column_ordinals")
        result_ordinal = metric_ordinals["CARRYING_VALUE"]
        if (
            set(parent_hits) != {"BOND", "CERTIFICATE_OF_DEPOSIT"}
            or receiver_parent_hits
            != {"BOND": 1, "CERTIFICATE_OF_DEPOSIT": 4}
            or prior_axis.get("complete") is not True
            or type(prior_money) is not list
            or len(prior_money) != 2
            or rows[2].get("row_kind") != "SUBTOTAL"
            or _normalized(rows[2].get("label_exact"))
            or rows[5].get("row_kind") != "SUBTOTAL"
            or _normalized(rows[5].get("label_exact"))
            or _exact_declared_role(
                rows[1].get("label_exact"),
                compiled_specs=compiled_specs,
                roles=output_roles,
                within_role="BOND",
            )
            is None
            or _exact_declared_role(
                rows[4].get("label_exact"),
                compiled_specs=compiled_specs,
                roles=output_roles,
                within_role="CERTIFICATE_OF_DEPOSIT",
            )
            is None
        ):
            continue
        try:
            prior_parent_current = {
                role: observed_source_coefficient_v1(
                    _source_money(
                        prior_rows[row_ordinal - 1]["values_exact"][prior_money[0] - 1]
                    )
                )
                for role, row_ordinal in parent_hits.items()
            }
            detail_parent_current = {
                "BOND": observed_source_coefficient_v1(
                    _source_money(rows[2]["values_exact"][result_ordinal - 1])
                ),
                "CERTIFICATE_OF_DEPOSIT": observed_source_coefficient_v1(
                    _source_money(rows[5]["values_exact"][result_ordinal - 1])
                ),
            }
            prior_root = observed_source_coefficient_v1(
                _source_money(
                    prior_rows[-1]["values_exact"][prior_money[0] - 1]
                )
            )
        except (IndexError, TypeError, ValueError):
            continue
        if (
            prior_parent_current != detail_parent_current
            or any(value is None for value in detail_parent_current.values())
            or prior_root != sum(detail_parent_current.values())
        ):
            continue
        receipt = receipt_for(
            region=receiver_region,
            before_roles=regions[receiver_index]["component_roles"],
        )
        for role, ordinal in sorted(metric_ordinals.items(), key=lambda item: item[1]):
            column = columns[ordinal - 1]
            before_path = canonical_clone_v1(column.get("header_path_exact"))
            before_kind = column.get("value_kind")
            after_path = (
                [receiver_table["title_exact"], *before_path]
                if role == "CARRYING_VALUE"
                else before_path
            )
            after_kind = "MONEY" if role == "CARRYING_VALUE" else "TEXT"
            column["header_path_exact"] = after_path
            column["value_kind"] = after_kind
            receipt["column_projections"].append(
                {
                    "after_header_path_exact": after_path,
                    "after_value_kind": after_kind,
                    "before_header_path_exact": before_path,
                    "before_value_kind": before_kind,
                    "column_ordinal": ordinal,
                    "metric_role": role,
                    "projection_kind": (
                        "EXACT_SINGLE_PERIOD_DETAIL_CARRYING_VALUE_AFTER_"
                        "FOUR_METRIC_SOURCE_EQUATION"
                    ),
                }
            )
        receipt["table_projections"].append(
            {
                "detail_parent_current_axis": detail_parent_current,
                "metric_row_equations": row_equations,
                "prior_parent_current_axis": prior_parent_current,
                "prior_root_current": prior_root,
                "projection_kind": (
                    "EXACT_CURRENT_DATE_FOUR_METRIC_DETAIL_CORROBORATES_"
                    "ADJACENT_TWO_PERIOD_PARENT_SUMMARY"
                ),
                "visible_date": visible_dates[0],
            }
        )

    # Extend the shared exact owner-row unit rule across an explicitly joined
    # fragment cluster.  Equality only authenticates that the primary owner
    # row and the note terminal total are the same presentation; it never
    # supplies or changes a monetary coefficient.
    document_unit_context = _document_unit_context_axis(
        projected_pages, compiled_specs=compiled_specs
    )
    owner_unit_evidence = document_unit_context.get("owner_row_evidence")
    active_region_indices = [
        index
        for index in range(len(projected_regions))
        if index not in dropped_region_indices
    ]
    root_observation_axis = []
    for region_index in active_region_indices:
        region = projected_regions[region_index]
        table = _region_table(projected_pages, region)
        rows = table.get("rows")
        period_axis = _two_period_axis(table)
        money = period_axis.get("money_column_ordinals")
        if (
            type(rows) is not list
            or not rows
            or type(rows[-1]) is not dict
            or rows[-1].get("row_kind") != "TOTAL"
            or period_axis.get("complete") is not True
            or type(money) is not list
        ):
            continue
        coefficients = _observed_money_coefficients_v1(
            rows[-1], money_ordinals=money
        )
        if coefficients is not None:
            root_observation_axis.append(
                {
                    "coefficients": coefficients,
                    "locator": {
                        field: region[field]
                        for field in (
                            "page_json_version_id",
                            "physical_page",
                            "section_id",
                            "table_id",
                        )
                    },
                    "period_signatures": canonical_clone_v1(
                        period_axis["signatures"]
                    ),
                    "row_ordinal": len(rows),
                }
            )
    matched_owner_units = []
    if type(owner_unit_evidence) is list:
        for evidence in owner_unit_evidence:
            if type(evidence) is not dict:
                continue
            corroborating_roots = [
                root
                for root in root_observation_axis
                if root["coefficients"] == evidence.get("coefficients")
                and root["period_signatures"] == evidence.get("period_signatures")
            ]
            if corroborating_roots:
                matched_owner_units.append(
                    {
                        "corroborating_roots": corroborating_roots,
                        "owner_row_evidence": canonical_clone_v1(evidence),
                    }
                )
    owner_unit_identities = {
        (
            item["owner_row_evidence"].get("canonical_unit"),
            item["owner_row_evidence"].get("magnitude_power10"),
        )
        for item in matched_owner_units
    }
    if len(owner_unit_identities) == 1 and matched_owner_units:
        canonical_unit, magnitude_power10 = next(iter(owner_unit_identities))
        source_unit_strings = []
        for item in matched_owner_units:
            source_exact = item["owner_row_evidence"].get("source_exact")
            if type(source_exact) is str and source_exact.strip():
                source_unit_strings.append(source_exact)
            elif type(source_exact) is list:
                source_unit_strings.extend(
                    evidence.get("source_exact")
                    for evidence in source_exact
                    if type(evidence) is dict
                    and type(evidence.get("source_exact")) is str
                    and evidence["source_exact"].strip()
                )
        source_unit_by_normalized = {
            _normalized(source): source for source in source_unit_strings
        }
        if len(source_unit_by_normalized) == 1:
            source_unit_exact = next(iter(source_unit_by_normalized.values()))
            matched_signatures = {
                canonical_json_sha256_v1(
                    item["owner_row_evidence"]["period_signatures"]
                )
                for item in matched_owner_units
            }
            for region_index in active_region_indices:
                region = projected_regions[region_index]
                table = _region_table(projected_pages, region)
                period_axis = _two_period_axis(table)
                if (
                    _normalized(table.get("unit_exact"))
                    or period_axis.get("complete") is not True
                    or canonical_json_sha256_v1(period_axis.get("signatures"))
                    not in matched_signatures
                ):
                    continue
                receipt = receipt_for(
                    region=region,
                    before_roles=regions[region_index]["component_roles"],
                )
                receipt["table_projections"].append(
                    {
                        "after_unit_exact": source_unit_exact,
                        "before_unit_exact": table.get("unit_exact"),
                        "canonical_unit": canonical_unit,
                        "magnitude_power10": magnitude_power10,
                        "matched_owner_unit_axis": canonical_clone_v1(
                            matched_owner_units
                        ),
                        "projection_kind": (
                            "EXACT_PRIMARY_OWNER_ROW_AND_NOTE_TERMINAL_TOTAL_"
                            "ALL_LANE_PERIOD_MATCH_SCOPES_BLANK_FRAGMENT_UNIT"
                        ),
                    }
                )
                table["unit_exact"] = source_unit_exact

    receipts = []
    for key in sorted(receipts_by_locator):
        receipt = receipts_by_locator[key]
        if (
            not receipt["column_projections"]
            and not receipt["row_projections"]
            and not receipt["table_projections"]
        ):
            continue
        region = next(
            region
            for region in projected_regions
            if (
                region["page_json_version_id"],
                region["section_id"],
                region["table_id"],
            )
            == key
        )
        page = projected_pages[region["page_json_version_id"]]
        section = page["sections"][int(region["section_id"][1:]) - 1]
        table = section["tables"][int(region["table_id"][1:]) - 1]
        classification = classify_gemini_json_multitable_hierarchical_table_v1(
            page, section, table, compiled_specs=compiled_specs
        )
        after_roles = _classification_component_roles_v1(classification)
        receipt["region_component_roles"]["after"] = after_roles
        region["component_roles"] = after_roles
        material = canonical_clone_v1(receipt)
        receipt["adjacent_source_syntax_projection_receipt_id"] = (
            "gjivpassprv1:receipt:" + canonical_json_sha256_v1(material)
        )
        receipts.append(receipt)
    projected_regions = [
        region
        for index, region in enumerate(projected_regions)
        if index not in dropped_region_indices
    ]
    for fragment_ordinal, region in enumerate(projected_regions, start=1):
        region["fragment_ordinal"] = fragment_ordinal
    return projected_pages, projected_regions, receipts


def _project_maturity_context_and_prune_validations_v1(
    *,
    pages: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Recover STB's explicit bond/CD maturity split and validation tables."""

    projected_pages = {
        version_id: canonical_clone_v1(page) for version_id, page in pages.items()
    }
    projected_regions = canonical_clone_v1(list(regions))
    receipts = []
    projected_by_index: dict[int, list[dict[str, Any]]] = {}
    column_projected_by_index: dict[int, list[dict[str, Any]]] = {}
    table_projected_by_index: dict[int, list[dict[str, Any]]] = {}

    for region_index, region in enumerate(projected_regions):
        table = _region_table(projected_pages, region)
        rows = table.get("rows")
        if type(rows) is not list:
            continue

        # STB prints two explicitly named maturity populations in one table,
        # each followed by ``Cộng``, and one final ``Tổng``.  The first group
        # names bonds directly; the second uses the wider GTCG abbreviation.
        # Recover the printed parent/root row syntax only when all three
        # source equations and both complete tenor partitions are exact.
        # Values are never changed and the GTCG subtree is scoped to CD only
        # because the same table independently prints the sibling bond group.
        special_layouts = (
            {
                "leading_owner": False,
                "row_kinds": [
                    "GROUP",
                    "ITEM",
                    "ITEM",
                    "ITEM",
                    "TOTAL",
                    "GROUP",
                    "ITEM",
                    "ITEM",
                    "ITEM",
                    "TOTAL",
                    "TOTAL",
                ],
            },
            {
                "leading_owner": True,
                "row_kinds": [
                    "GROUP",
                    "GROUP",
                    "ITEM",
                    "ITEM",
                    "ITEM",
                    "SUBTOTAL",
                    "GROUP",
                    "ITEM",
                    "ITEM",
                    "ITEM",
                    "SUBTOTAL",
                    "TOTAL",
                ],
            },
        )
        special_layout = next(
            (
                layout
                for layout in special_layouts
                if len(rows) == len(layout["row_kinds"])
                and all(type(row) is dict for row in rows)
                and [row.get("row_kind") for row in rows]
                == layout["row_kinds"]
            ),
            None,
        )
        special_offset = (
            1
            if type(special_layout) is dict
            and special_layout["leading_owner"] is True
            else 0
        )
        bond_group_index = special_offset
        bond_child_indices = tuple(range(special_offset + 1, special_offset + 4))
        bond_total_index = special_offset + 4
        cd_group_index = special_offset + 5
        cd_child_indices = tuple(range(special_offset + 6, special_offset + 9))
        cd_total_index = special_offset + 9
        family_total_index = special_offset + 10
        labels = [
            _normalized(row.get("label_exact")) if type(row) is dict else ""
            for row in rows
        ]
        money_ordinals = _money_ordinals(table)
        before_classification = None
        if len(projected_regions) == 1 and special_layout is not None:
            page = projected_pages[region["page_json_version_id"]]
            section = page["sections"][int(region["section_id"][1:]) - 1]
            before_classification = (
                classify_gemini_json_multitable_hierarchical_table_v1(
                    page, section, table, compiled_specs=compiled_specs
                )
            )
        bond_child_roles = [
            _exact_declared_role(
                rows[index].get("label_exact"),
                compiled_specs=compiled_specs,
                roles={"BOND_SHORT", "BOND_MEDIUM", "BOND_LONG"},
                within_role="BOND",
            )
            for index in bond_child_indices
        ] if special_layout is not None else []
        cd_child_roles = [
            _exact_declared_role(
                rows[index].get("label_exact"),
                compiled_specs=compiled_specs,
                roles={"CD_SHORT", "CD_MEDIUM", "CD_LONG"},
                within_role="CERTIFICATE_OF_DEPOSIT",
            )
            for index in cd_child_indices
        ] if special_layout is not None else []
        row_vectors = [
            _observed_money_coefficients_v1(row, money_ordinals=money_ordinals)
            for row in rows
        ] if special_layout is not None else []

        def exact_axis_sum(
            indices: Sequence[int],
            *,
            source_vectors: Sequence[list[int] | None] = row_vectors,
            lane_count: int = len(money_ordinals),
        ) -> list[int] | None:
            vectors = [source_vectors[index] for index in indices]
            if not vectors or any(vector is None for vector in vectors):
                return None
            return [
                sum(vector[lane] for vector in vectors if vector is not None)
                for lane in range(lane_count)
            ]

        bond_sum = exact_axis_sum(bond_child_indices) if row_vectors else None
        cd_sum = exact_axis_sum(cd_child_indices) if row_vectors else None
        root_sum = (
            exact_axis_sum((bond_total_index, cd_total_index))
            if row_vectors
            else None
        )
        leading_owner = special_offset == 1
        owner_prefix = [rows[0].get("label_exact")] if leading_owner else []
        special_hierarchy = (
            special_layout is not None
            and (
                not leading_owner
                or rows[0].get("hierarchy_path_exact")
                == [rows[0].get("label_exact")]
            )
            and rows[bond_group_index].get("hierarchy_path_exact")
            == [*owner_prefix, rows[bond_group_index].get("label_exact")]
            and all(
                rows[index].get("hierarchy_path_exact")
                == [
                    *owner_prefix,
                    rows[bond_group_index].get("label_exact"),
                    rows[index].get("label_exact"),
                ]
                for index in (*bond_child_indices, bond_total_index)
            )
            and rows[cd_group_index].get("hierarchy_path_exact")
            == [*owner_prefix, rows[cd_group_index].get("label_exact")]
            and all(
                rows[index].get("hierarchy_path_exact")
                == [
                    *owner_prefix,
                    rows[cd_group_index].get("label_exact"),
                    rows[index].get("label_exact"),
                ]
                for index in (*cd_child_indices, cd_total_index)
            )
            and rows[family_total_index].get("hierarchy_path_exact")
            == [*owner_prefix, rows[family_total_index].get("label_exact")]
        )
        source_owner_exact = (
            rows[0].get("label_exact") if leading_owner else table.get("title_exact")
        )
        source_owner_alias = _exact_owner_alias(
            source_owner_exact, compiled_specs=compiled_specs
        )
        owner_shape_exact = (
            not _normalized(table.get("title_exact"))
            and row_vectors[0] is None
            and before_classification.get("family_root_row_ordinals") == [1]
            if leading_owner and type(before_classification) is dict
            else (
                not leading_owner
                and before_classification.get("family_root_row_ordinals") == []
                if type(before_classification) is dict
                else False
            )
        )
        if (
            special_layout is not None
            and money_ordinals == [1, 2]
            and source_owner_alias is not None
            and owner_shape_exact
            and labels[bond_group_index] == "phat hanh trai phieu theo thoi gian"
            and labels[bond_total_index] == "cong"
            and labels[cd_group_index] == "phat hanh gtcg theo thoi gian"
            and labels[cd_total_index] == "cong"
            and labels[family_total_index] == "tong"
            and set(bond_child_roles)
            == {"BOND_SHORT", "BOND_MEDIUM", "BOND_LONG"}
            and set(cd_child_roles) == {"CD_SHORT", "CD_MEDIUM", "CD_LONG"}
            and len(set(bond_child_roles)) == 3
            and len(set(cd_child_roles)) == 3
            and special_hierarchy
            and type(before_classification) is dict
            and before_classification.get("ambiguous_rows") == []
            and before_classification.get("typed_control_disposition") is None
            and bond_sum is not None
            and bond_sum == row_vectors[bond_total_index]
            and cd_sum is not None
            and cd_sum == row_vectors[cd_total_index]
            and root_sum is not None
            and root_sum == row_vectors[family_total_index]
        ):
            raw_rows = canonical_clone_v1(rows)
            row_changes = {
                bond_group_index + 1: {
                    "hierarchy_path_exact": [None],
                    "label_exact": None,
                    "row_kind": "GROUP",
                },
                bond_total_index + 1: {
                    "hierarchy_path_exact": ["Trái phiếu"],
                    "label_exact": "Trái phiếu",
                    "row_kind": "SUBTOTAL",
                },
                cd_total_index + 1: {
                    "hierarchy_path_exact": ["Chứng chỉ tiền gửi"],
                    "label_exact": "Chứng chỉ tiền gửi",
                    "row_kind": "SUBTOTAL",
                },
                family_total_index + 1: {
                    "hierarchy_path_exact": ["Phát hành giấy tờ có giá"],
                    "label_exact": "Phát hành giấy tờ có giá",
                    "row_kind": "TOTAL",
                },
            }
            if leading_owner:
                row_changes[1] = {
                    "hierarchy_path_exact": [None],
                    "label_exact": None,
                    "row_kind": "GROUP",
                }
            for index in cd_child_indices:
                row_ordinal = index + 1
                row_changes[row_ordinal] = {
                    "hierarchy_path_exact": [
                        "Chứng chỉ tiền gửi",
                        *canonical_clone_v1(
                            rows[index].get("hierarchy_path_exact")
                        ),
                    ],
                    "label_exact": rows[index].get("label_exact"),
                    "row_kind": rows[index].get("row_kind"),
                }
            row_projections = []
            for row_ordinal, after in sorted(row_changes.items()):
                row = rows[row_ordinal - 1]
                row_projections.append(
                    {
                        "after_hierarchy_path_exact": canonical_clone_v1(
                            after["hierarchy_path_exact"]
                        ),
                        "after_label_exact": after["label_exact"],
                        "after_row_kind": after["row_kind"],
                        "before_hierarchy_path_exact": canonical_clone_v1(
                            row.get("hierarchy_path_exact")
                        ),
                        "before_label_exact": row.get("label_exact"),
                        "before_row_kind": row.get("row_kind"),
                        "row_ordinal": row_ordinal,
                    }
                )
                row.update(canonical_clone_v1(after))
            projected_by_index[region_index] = row_projections
            table_projected_by_index[region_index] = [
                {
                    "bond_child_roles": bond_child_roles,
                    "bond_sum_axis": bond_sum,
                    "bond_total_axis": row_vectors[bond_total_index],
                    "cd_child_roles": cd_child_roles,
                    "cd_sum_axis": cd_sum,
                    "cd_total_axis": row_vectors[cd_total_index],
                    "leading_owner_row_ordinal": 1 if leading_owner else None,
                    "projection_kind": (
                        "EXACT_SIBLING_BOND_AND_GTCG_MATURITY_PARTITIONS_WITH_"
                        "PRINTED_PARENT_TOTALS_AND_FINAL_FAMILY_TOTAL"
                    ),
                    "raw_source_rows": raw_rows,
                    "root_component_sum_axis": root_sum,
                    "root_total_axis": row_vectors[family_total_index],
                    "source_owner_exact": source_owner_exact,
                    "source_owner_alias": source_owner_alias,
                    "source_row_ordinals": {
                        "bond_children": [index + 1 for index in bond_child_indices],
                        "bond_group": bond_group_index + 1,
                        "bond_total": bond_total_index + 1,
                        "cd_children": [index + 1 for index in cd_child_indices],
                        "cd_group": cd_group_index + 1,
                        "cd_total": cd_total_index + 1,
                        "family_total": family_total_index + 1,
                    },
                }
            ]
            continue
        title = _normalized(table.get("title_exact"))
        indices = []
        if "phat hanh gtcg theo thoi gian" in title:
            indices = list(range(0, max(0, len(rows) - 1)))
            blank_headers = (
                _money_ordinals(table) == [1, 2]
                and all(
                    not any(_normalized(value) for value in column.get("header_path_exact", []))
                    for column in table.get("columns", [])
                    if type(column) is dict and column.get("value_kind") == "MONEY"
                )
            )
            prior_axes = []
            if blank_headers:
                for prior_index, prior_region in enumerate(projected_regions[:region_index]):
                    if any(
                        prior_region.get(field) != region.get(field)
                        for field in ("page_json_version_id", "physical_page", "section_id")
                    ):
                        continue
                    prior_table = _region_table(projected_pages, prior_region)
                    if (
                        "phat hanh trai phieu theo thoi gian"
                        in _normalized(prior_table.get("title_exact"))
                        and _two_period_axis(prior_table).get("complete") is True
                        and _money_ordinals(prior_table) == [1, 2]
                    ):
                        prior_axes.append((prior_index, prior_table["columns"]))
            if len(prior_axes) == 1:
                prior_index, prior_columns = prior_axes[0]
                column_projections = []
                for column_ordinal in (1, 2):
                    before_path = canonical_clone_v1(
                        table["columns"][column_ordinal - 1].get("header_path_exact")
                    )
                    after_path = canonical_clone_v1(
                        prior_columns[column_ordinal - 1].get("header_path_exact")
                    )
                    table["columns"][column_ordinal - 1]["header_path_exact"] = after_path
                    column_projections.append(
                        {
                            "after_header_path_exact": after_path,
                            "before_header_path_exact": before_path,
                            "column_ordinal": column_ordinal,
                            "prior_region_index": prior_index,
                            "projection_kind": (
                                "SAME_PAGE_ADJACENT_BOND_AND_GTCG_MATURITY_PERIOD_AXIS"
                            ),
                        }
                    )
                column_projected_by_index[region_index] = column_projections
        else:
            starts = [
                index
                for index, row in enumerate(rows)
                if type(row) is dict
                and (
                    _normalized(row.get("label_exact"))
                    == "phat hanh gtcg theo thoi gian"
                    or "phat hanh gtcg theo thoi gian"
                    in {
                        _normalized(value)
                        for value in row.get("hierarchy_path_exact", [])
                    }
                )
            ]
            if starts and starts == list(range(starts[0], starts[-1] + 1)):
                start = starts[0]
                indices = [
                    index
                    for index in range(start, len(rows))
                    if type(rows[index]) is dict
                    and _normalized(rows[index].get("label_exact")) != "tong"
                ]
        if not indices:
            continue
        # A sibling/existing bond presentation is mandatory.  This prevents a
        # generic GTCG heading from being guessed as CD in isolation.
        bond_visible = any(
            "phat hanh trai phieu theo thoi gian"
            in _normalized(_region_table(projected_pages, other).get("title_exact"))
            or any(
                type(row) is dict
                and (
                    "phat hanh trai phieu theo thoi gian"
                    in _normalized(row.get("label_exact"))
                    or any(
                        "phat hanh trai phieu theo thoi gian"
                        in _normalized(value)
                        for value in row.get("hierarchy_path_exact", [])
                    )
                )
                for row in (_region_table(projected_pages, other).get("rows") or [])
            )
            for other in projected_regions
        )
        if not bond_visible:
            continue
        row_projections = []
        for index in indices:
            row = rows[index]
            path = row.get("hierarchy_path_exact")
            if type(path) is not list or not path or "chung chi tien gui" in {
                _normalized(item) for item in path
            }:
                continue
            after_path = ["Chứng chỉ tiền gửi", *path]
            row_projections.append(
                {
                    "after_hierarchy_path_exact": canonical_clone_v1(after_path),
                    "before_hierarchy_path_exact": canonical_clone_v1(path),
                    "before_label_exact": row.get("label_exact"),
                    "before_row_kind": row.get("row_kind"),
                    "row_ordinal": index + 1,
                }
            )
            row["hierarchy_path_exact"] = after_path
        if row_projections:
            projected_by_index[region_index] = row_projections

    # A two-table SHB presentation first repeats the same family face-value
    # total three times, then prints the complete transposed bond/CD maturity
    # population.  The first table contributes no distinct observation.  It
    # may be removed only when its three vectors are identical, the adjacent
    # detail table has the exact two instrument columns and two period blocks,
    # and both detail terminal equations reproduce that same two-period axis.
    if len(projected_regions) == 2:
        summary_region, detail_region = projected_regions
        summary_table = _region_table(projected_pages, summary_region)
        detail_table = _region_table(projected_pages, detail_region)
        same_container = all(
            summary_region.get(field) == detail_region.get(field)
            for field in (
                "document_id",
                "source_sha256",
                "page_json_version_id",
                "physical_page",
                "selected_page_ordinal",
                "section_id",
            )
        )
        summary_rows = summary_table.get("rows")
        detail_rows = detail_table.get("rows")
        page = projected_pages.get(summary_region.get("page_json_version_id"))
        section = (
            page["sections"][int(summary_region["section_id"][1:]) - 1]
            if type(page) is dict
            else None
        )
        summary_classification = (
            classify_gemini_json_multitable_hierarchical_table_v1(
                page,
                section,
                summary_table,
                compiled_specs=compiled_specs,
            )
            if type(page) is dict and type(section) is dict
            else None
        )
        detail_classification = (
            classify_gemini_json_multitable_hierarchical_table_v1(
                page,
                section,
                detail_table,
                compiled_specs=compiled_specs,
            )
            if type(page) is dict and type(section) is dict
            else None
        )
        summary_vectors = (
            [
                _observed_money_coefficients_v1(
                    row, money_ordinals=[1, 2]
                )
                for row in summary_rows
            ]
            if type(summary_rows) is list
            and len(summary_rows) == 3
            and all(type(row) is dict for row in summary_rows)
            else []
        )
        detail_terminal_vectors = (
            [
                _observed_money_coefficients_v1(
                    detail_rows[index], money_ordinals=[1, 2, 3]
                )
                for index in (7, 15)
            ]
            if type(detail_rows) is list
            and len(detail_rows) == 16
            and all(type(row) is dict for row in detail_rows)
            else []
        )
        detail_period_root_axis = (
            [vector[2] for vector in detail_terminal_vectors if vector is not None]
            if detail_terminal_vectors
            and all(vector is not None for vector in detail_terminal_vectors)
            else []
        )
        detail_terminal_equations = (
            [
                {
                    "component_coefficients": vector[:2],
                    "component_sum": sum(vector[:2]),
                    "period_block_ordinal": ordinal,
                    "root_coefficient": vector[2],
                    "status": "EXACT",
                }
                for ordinal, vector in enumerate(detail_terminal_vectors, start=1)
                if vector is not None and sum(vector[:2]) == vector[2]
            ]
            if detail_terminal_vectors
            else []
        )
        transposed_column_roles = (
            {
                hit.get("role")
                for hit in detail_classification.get(
                    "transposed_column_role_hits", []
                )
                if type(hit) is dict
                and hit.get("status", "").startswith("EXACT_")
            }
            if type(detail_classification) is dict
            else set()
        )
        if (
            same_container
            and summary_region.get("table_id") == "t1"
            and detail_region.get("table_id") == "t2"
            and summary_table.get("continuation") == "NONE"
            and detail_table.get("continuation") == "NONE"
            and not _normalized(summary_table.get("title_exact"))
            and "chi tiet ky han cua cac giay to co gia phat hanh"
            in _normalized(detail_table.get("title_exact"))
            and _money_ordinals(summary_table) == [1, 2]
            and _money_ordinals(detail_table) == [1, 2, 3]
            and type(summary_rows) is list
            and all(type(row) is dict for row in summary_rows)
            and [row.get("row_kind") for row in summary_rows]
            == ["ITEM", "TOTAL", "TOTAL"]
            and _normalized(summary_rows[0].get("label_exact"))
            == "giay to co gia bang vnd"
            and _normalized(summary_rows[1].get("label_exact")) == "menh gia"
            and not _normalized(summary_rows[2].get("label_exact"))
            and len(summary_vectors) == 3
            and summary_vectors[0] is not None
            and summary_vectors[0] == summary_vectors[1] == summary_vectors[2]
            and type(summary_classification) is dict
            and summary_classification.get("ambiguous_rows") == []
            and summary_classification.get("typed_control_disposition") is None
            and [
                hit.get("role")
                for hit in summary_classification.get("role_hits", [])
                if type(hit) is dict
            ]
            == [
                "GENERIC_ISSUED_PAPER_SOURCE",
                "GENERIC_ISSUED_PAPER_SOURCE",
            ]
            and transposed_column_roles
            == {"BOND", "CERTIFICATE_OF_DEPOSIT"}
            and type(detail_rows) is list
            and all(type(row) is dict for row in detail_rows)
            and detail_rows[0].get("row_kind") == "GROUP"
            and _normalized(detail_rows[0].get("label_exact"))
            == "so du cuoi nam"
            and detail_rows[7].get("row_kind") == "TOTAL"
            and detail_rows[8].get("row_kind") == "GROUP"
            and _normalized(detail_rows[8].get("label_exact")) == "so du dau nam"
            and detail_rows[15].get("row_kind") == "TOTAL"
            and len(detail_terminal_equations) == 2
            and detail_period_root_axis == summary_vectors[0]
        ):
            material = {
                "detail_locator": {
                    field: detail_region[field]
                    for field in (
                        "page_json_version_id",
                        "physical_page",
                        "section_id",
                        "table_id",
                    )
                },
                "detail_period_root_axis": detail_period_root_axis,
                "detail_terminal_equations": detail_terminal_equations,
                "dropped_region": canonical_clone_v1(summary_region),
                "format_version": (
                    MATURITY_AND_VALIDATION_PROJECTION_RECEIPT_FORMAT_VERSION
                ),
                "locator": {
                    field: summary_region[field]
                    for field in (
                        "page_json_version_id",
                        "physical_page",
                        "section_id",
                        "table_id",
                    )
                },
                "raw_source_rows": canonical_clone_v1(summary_rows),
                "region_component_roles": {
                    "after": canonical_clone_v1(summary_region["component_roles"]),
                    "before": canonical_clone_v1(summary_region["component_roles"]),
                },
                "row_projections": [],
                "rule": (
                    "EXACT_REPEATED_FACE_VALUE_SUMMARY_PRUNED_BEFORE_ADJACENT_"
                    "COMPLETE_TRANSPOSED_BOND_CD_MATURITY_PRESENTATION"
                ),
                "summary_repeated_axis": summary_vectors,
                "table_projections": [],
            }
            receipts.append(
                {
                    **material,
                    "maturity_validation_projection_receipt_id": (
                        "gjivpmvprv1:receipt:"
                        + canonical_json_sha256_v1(material)
                    ),
                }
            )
            projected_regions = [canonical_clone_v1(detail_region)]
            projected_regions[0]["fragment_ordinal"] = 1
            projected_by_index = (
                {0: projected_by_index[1]} if 1 in projected_by_index else {}
            )
            column_projected_by_index = (
                {0: column_projected_by_index[1]}
                if 1 in column_projected_by_index
                else {}
            )
            table_projected_by_index = (
                {0: table_projected_by_index[1]}
                if 1 in table_projected_by_index
                else {}
            )

    # Reclassify after the hierarchy-only CD projection before deciding which
    # presentations are validation-only.
    for region_index, region in enumerate(projected_regions):
        table = _region_table(projected_pages, region)
        page = projected_pages[region["page_json_version_id"]]
        section = page["sections"][int(region["section_id"][1:]) - 1]
        classification = classify_gemini_json_multitable_hierarchical_table_v1(
            page, section, table, compiled_specs=compiled_specs
        )
        if region_index in projected_by_index:
            region["component_roles"] = _classification_component_roles_v1(classification)

    direct_roles = set(compiled_specs["root_component_roles"]) - set(
        compiled_specs["validation_only_roles"]
    )
    validation_indices = []
    core_indices = []
    for index, region in enumerate(projected_regions):
        table = _region_table(projected_pages, region)
        page = projected_pages[region["page_json_version_id"]]
        section = page["sections"][int(region["section_id"][1:]) - 1]
        surface = _normalized(table.get("title_exact") or section.get("title_exact"))
        classification = classify_gemini_json_multitable_hierarchical_table_v1(
            page, section, table, compiled_specs=compiled_specs
        )
        roles = set(_classification_component_roles_v1(classification))
        if (
            ("theo loai giay to co gia" in surface or "theo loai tien" in surface)
            and not (roles & direct_roles)
        ):
            validation_indices.append(index)
        else:
            core_indices.append(index)
    if validation_indices and core_indices:
        core_totals = []
        for index in core_indices:
            table = _region_table(projected_pages, projected_regions[index])
            rows = table.get("rows")
            money = _money_ordinals(table)
            if type(rows) is list and rows and type(rows[-1]) is dict and rows[-1].get("row_kind") == "TOTAL":
                vector = _observed_money_coefficients_v1(rows[-1], money_ordinals=money)
                if vector is not None:
                    core_totals.append((index, vector))
        validation_totals = []
        for index in validation_indices:
            table = _region_table(projected_pages, projected_regions[index])
            rows = table.get("rows")
            money = _money_ordinals(table)
            if type(rows) is not list or not rows or type(rows[-1]) is not dict or rows[-1].get("row_kind") != "TOTAL":
                validation_totals = []
                break
            vector = _observed_money_coefficients_v1(rows[-1], money_ordinals=money)
            if vector is None:
                validation_totals = []
                break
            validation_totals.append((index, vector))
        matching_roots = [
            item
            for item in core_totals
            if validation_totals
            and all(vector == item[1] for _index, vector in validation_totals)
        ]
        if len(matching_roots) == 1:
            root_index, root_axis = matching_roots[0]
            for index, vector in validation_totals:
                region = projected_regions[index]
                table = _region_table(projected_pages, region)
                locator = {
                    key: region[key]
                    for key in (
                        "page_json_version_id",
                        "physical_page",
                        "section_id",
                        "table_id",
                    )
                }
                material = {
                    "dropped_region": canonical_clone_v1(region),
                    "format_version": MATURITY_AND_VALIDATION_PROJECTION_RECEIPT_FORMAT_VERSION,
                    "locator": locator,
                    "raw_source_rows": canonical_clone_v1(table.get("rows")),
                    "region_component_roles": {
                        "after": canonical_clone_v1(region["component_roles"]),
                        "before": canonical_clone_v1(region["component_roles"]),
                    },
                    "root_region": canonical_clone_v1(projected_regions[root_index]),
                    "root_total_axis": root_axis,
                    "row_projections": [],
                    "rule": (
                        "EXACT_FACE_OR_CURRENCY_VALIDATION_PRESENTATION_TERMINAL_"
                        "TOTAL_EQUALS_UNIQUE_MATURITY_ROOT_ALL_VISIBLE_LANES"
                    ),
                    "validation_total_axis": vector,
                }
                receipts.append(
                    {
                        **material,
                        "maturity_validation_projection_receipt_id": (
                            "gjivpmvprv1:receipt:" + canonical_json_sha256_v1(material)
                        ),
                    }
                )
            projected_regions = [
                region
                for index, region in enumerate(projected_regions)
                if index not in set(validation_indices)
            ]
            remap = {
                old: new
                for new, old in enumerate(
                    index for index in range(len(regions)) if index not in set(validation_indices)
                )
            }
            projected_by_index = {
                remap[index]: value
                for index, value in projected_by_index.items()
                if index in remap
            }
            column_projected_by_index = {
                remap[index]: value
                for index, value in column_projected_by_index.items()
                if index in remap
            }
            table_projected_by_index = {
                remap[index]: value
                for index, value in table_projected_by_index.items()
                if index in remap
            }

    for index in sorted(
        {
            *projected_by_index,
            *column_projected_by_index,
            *table_projected_by_index,
        }
    ):
        row_projections = projected_by_index.get(index, [])
        column_projections = column_projected_by_index.get(index, [])
        table_projections = table_projected_by_index.get(index, [])
        region = projected_regions[index]
        table = _region_table(projected_pages, region)
        page = projected_pages[region["page_json_version_id"]]
        section = page["sections"][int(region["section_id"][1:]) - 1]
        classification = classify_gemini_json_multitable_hierarchical_table_v1(
            page, section, table, compiled_specs=compiled_specs
        )
        after_roles = _classification_component_roles_v1(classification)
        before_region = next(
            raw
            for raw in regions
            if all(
                raw.get(field) == region.get(field)
                for field in ("page_json_version_id", "section_id", "table_id")
            )
        )
        material = {
            "format_version": MATURITY_AND_VALIDATION_PROJECTION_RECEIPT_FORMAT_VERSION,
            "column_projections": column_projections,
            "locator": {
                key: region[key]
                for key in ("page_json_version_id", "physical_page", "section_id", "table_id")
            },
            "region_component_roles": {
                "after": after_roles,
                "before": canonical_clone_v1(before_region["component_roles"]),
            },
            "row_projections": row_projections,
            "rule": (
                "EXACT_SIBLING_BOND_AND_GTCG_MATURITY_PARTITIONS_PARENT_AND_"
                "ROOT_SOURCE_TOTALS_ALL_LANES_STRUCTURAL_SYNTAX_ONLY"
                if table_projections
                else (
                    "EXACT_GTCG_MATURITY_SUBTREE_SCOPED_TO_CERTIFICATE_ONLY_"
                    "WITH_VISIBLE_SIBLING_BOND_MATURITY_PRESENTATION_"
                    "HIERARCHY_ONLY"
                )
            ),
            "table_projections": table_projections,
        }
        receipts.append(
            {
                **material,
                "maturity_validation_projection_receipt_id": (
                    "gjivpmvprv1:receipt:" + canonical_json_sha256_v1(material)
                ),
            }
        )
    for fragment_ordinal, region in enumerate(projected_regions, start=1):
        region["fragment_ordinal"] = fragment_ordinal
    return projected_pages, projected_regions, receipts


def _project_transposed_source_axes_v1(
    *,
    pages: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Expose exact transposed total/period syntax hidden by JSON shape."""

    projected_pages = {
        version_id: canonical_clone_v1(page) for version_id, page in pages.items()
    }
    projected_regions = canonical_clone_v1(list(regions))
    receipts_by_index: dict[int, dict[str, Any]] = {}

    def receipt_for(index: int) -> dict[str, Any]:
        if index not in receipts_by_index:
            region = regions[index]
            receipts_by_index[index] = {
                "column_projections": [],
                "locator": {
                    key: region[key]
                    for key in (
                        "page_json_version_id",
                        "physical_page",
                        "section_id",
                        "table_id",
                    )
                },
                "row_projections": [],
            }
        return receipts_by_index[index]

    # ``Tổng`` and ``Tổng cộng`` are the same printed total concept.  Shared
    # transposed detection intentionally uses the latter as a narrow marker;
    # bind the exact synonym only when both instrument columns and tenor rows
    # are already independently declared.
    for region_index, region in enumerate(projected_regions):
        table = _region_table(projected_pages, region)
        columns = table.get("columns")
        rows = table.get("rows")
        if (
            type(columns) is not list
            or len(columns) != 3
            or type(rows) is not list
            or not rows
            or type(rows[-1]) is not dict
            or rows[-1].get("row_kind") != "TOTAL"
        ):
            continue
        page = projected_pages[region["page_json_version_id"]]
        section = page["sections"][int(region["section_id"][1:]) - 1]
        classification = classify_gemini_json_multitable_hierarchical_table_v1(
            page, section, table, compiled_specs=compiled_specs
        )
        column_roles = {
            hit.get("role")
            for hit in classification.get("transposed_column_role_hits", [])
            if type(hit) is dict and hit.get("status", "").startswith("EXACT_")
        }
        row_roles = {
            hit.get("role")
            for hit in classification.get("transposed_row_role_hits", [])
            if type(hit) is dict
        }
        header_path = columns[-1].get("header_path_exact")
        if (
            column_roles == {"BOND", "CERTIFICATE_OF_DEPOSIT"}
            and row_roles
            & {"BOND_SHORT", "BOND_MEDIUM", "BOND_LONG", "CD_SHORT", "CD_MEDIUM", "CD_LONG"}
            and type(header_path) is list
            and sum(_normalized(part) == "tong" for part in header_path) == 1
            and not any(_normalized(part) == "tong cong" for part in header_path)
        ):
            after_path = [
                "Tổng cộng" if _normalized(part) == "tong" else part
                for part in header_path
            ]
            receipt_for(region_index)["column_projections"].append(
                {
                    "after_header_path_exact": canonical_clone_v1(after_path),
                    "before_header_path_exact": canonical_clone_v1(header_path),
                    "column_ordinal": 3,
                    "projection_kind": "EXACT_TOTAL_HEADER_SYNONYM",
                }
            )
            columns[-1]["header_path_exact"] = after_path

    # An MSB transposed terminal row is labelled ``Số dư cuối kỳ/năm``.  The
    # same source page also prints a two-period instrument summary.  Only when
    # its current instrument and root values match exactly may that period-like
    # label be made neutral for the shared transposed parser.
    for region_index, region in enumerate(projected_regions):
        table = _region_table(projected_pages, region)
        rows = table.get("rows")
        if type(rows) is not list or not rows or type(rows[-1]) is not dict:
            continue
        terminal = rows[-1]
        if terminal.get("row_kind") != "TOTAL" or len(_semantic_period_roles(terminal.get("label_exact"))) != 1:
            continue
        page = projected_pages[region["page_json_version_id"]]
        section = page["sections"][int(region["section_id"][1:]) - 1]
        classification = classify_gemini_json_multitable_hierarchical_table_v1(
            page, section, table, compiled_specs=compiled_specs
        )
        if classification.get("layout_orientation") != "INSTRUMENT_COLUMNS_TENOR_ROWS":
            continue
        column_hits = {
            hit["role"]: hit["column_ordinal"]
            for hit in classification.get("transposed_column_role_hits", [])
            if type(hit) is dict and hit.get("status", "").startswith("EXACT_")
        }
        money_ordinals = classification.get("money_column_ordinals")
        transposed_values = _observed_money_coefficients_v1(
            terminal, money_ordinals=money_ordinals or []
        )
        if (
            set(column_hits) != {"BOND", "CERTIFICATE_OF_DEPOSIT"}
            or type(money_ordinals) is not list
            or transposed_values is None
        ):
            continue
        corroborations = []
        for other_index, other_region in enumerate(projected_regions):
            if other_index == region_index:
                continue
            other_table = _region_table(projected_pages, other_region)
            other_page = projected_pages[other_region["page_json_version_id"]]
            other_section = other_page["sections"][int(other_region["section_id"][1:]) - 1]
            other_classification = classify_gemini_json_multitable_hierarchical_table_v1(
                other_page, other_section, other_table, compiled_specs=compiled_specs
            )
            if other_classification.get("money_column_ordinals") != [1, 2]:
                continue
            role_values = {}
            for role in ("BOND", "CERTIFICATE_OF_DEPOSIT"):
                hits = [
                    hit
                    for hit in other_classification.get("role_hits", [])
                    if type(hit) is dict and hit.get("role") == role
                ]
                if len(hits) != 1:
                    break
                row = other_table["rows"][hits[0]["row_ordinal"] - 1]
                vector = _observed_money_coefficients_v1(row, money_ordinals=[1, 2])
                if vector is None:
                    break
                role_values[role] = vector[0]
            else:
                totals = [
                    row
                    for row in other_table.get("rows", [])
                    if type(row) is dict and row.get("row_kind") == "TOTAL"
                ]
                if len(totals) == 1:
                    total = _observed_money_coefficients_v1(
                        totals[0], money_ordinals=[1, 2]
                    )
                    if total is not None:
                        corroborations.append((other_index, role_values, total[0]))
        expected = {
            role: transposed_values[money_ordinals.index(ordinal)]
            for role, ordinal in column_hits.items()
        }
        total_ordinal = next(
            ordinal for ordinal in money_ordinals if ordinal not in column_hits.values()
        )
        expected_total = transposed_values[money_ordinals.index(total_ordinal)]
        exact = [
            item
            for item in corroborations
            if item[1] == expected and item[2] == expected_total
        ]
        if len(exact) != 1:
            continue
        receipt_for(region_index)["row_projections"].append(
            {
                "after_hierarchy_path_exact": [None],
                "after_label_exact": None,
                "before_hierarchy_path_exact": canonical_clone_v1(
                    terminal.get("hierarchy_path_exact")
                ),
                "before_label_exact": terminal.get("label_exact"),
                "before_row_kind": terminal.get("row_kind"),
                "corroborating_region_index": exact[0][0],
                "observed_instrument_axis": expected,
                "observed_root_total": expected_total,
                "projection_kind": "PERIOD_LIKE_TRANSPOSED_TERMINAL_TOTAL_LABEL",
                "row_ordinal": len(rows),
            }
        )
        terminal["label_exact"] = None
        terminal["hierarchy_path_exact"] = [None]

    # Two TPB transposed detail tables are the current/comparative populations
    # of a two-period face-value summary.  Bind each header to its explicit
    # table-title date, or (only for exactly two titleless tables) to source
    # order.  Totals must equal the corresponding printed summary lane.
    transposed_indices = []
    summary_indices = []
    for index, region in enumerate(projected_regions):
        table = _region_table(projected_pages, region)
        page = projected_pages[region["page_json_version_id"]]
        section = page["sections"][int(region["section_id"][1:]) - 1]
        classification = classify_gemini_json_multitable_hierarchical_table_v1(
            page, section, table, compiled_specs=compiled_specs
        )
        if classification.get("layout_orientation") == "INSTRUMENT_COLUMNS_TENOR_ROWS":
            transposed_indices.append(index)
        elif _two_period_axis(table).get("complete") is True:
            summary_indices.append(index)
    dropped_summary_indices: set[int] = set()
    if len(transposed_indices) == 2 and len(summary_indices) == 1:
        summary_index = summary_indices[0]
        summary_table = _region_table(projected_pages, projected_regions[summary_index])
        summary_rows = summary_table.get("rows")
        summary_totals = [
            row
            for row in summary_rows or []
            if type(row) is dict and row.get("row_kind") == "TOTAL"
        ]
        if not summary_totals and type(summary_rows) is list and len(summary_rows) == 1:
            summary_totals = [summary_rows[0]]
        summary_values = (
            _observed_money_coefficients_v1(summary_totals[0], money_ordinals=[1, 2])
            if len(summary_totals) == 1
            else None
        )
        period_surfaces = [
            summary_table["columns"][ordinal - 1].get("header_path_exact", [None])[0]
            for ordinal in [1, 2]
        ]
        title_dates = []
        detail_totals = []
        for index in transposed_indices:
            table = _region_table(projected_pages, projected_regions[index])
            title_dates.append(sorted(item.isoformat() for item in _surface_dates(table.get("title_exact"))))
            classification_page = projected_pages[projected_regions[index]["page_json_version_id"]]
            classification_section = classification_page["sections"][
                int(projected_regions[index]["section_id"][1:]) - 1
            ]
            classification = classify_gemini_json_multitable_hierarchical_table_v1(
                classification_page,
                classification_section,
                table,
                compiled_specs=compiled_specs,
            )
            totals = [
                row
                for row in table.get("rows", [])
                if type(row) is dict and row.get("row_kind") == "TOTAL"
            ]
            total_columns = [
                ordinal
                for ordinal in classification.get("money_column_ordinals", [])
                if ordinal
                not in {
                    hit["column_ordinal"]
                    for hit in classification.get("transposed_column_role_hits", [])
                    if hit.get("status", "").startswith("EXACT_")
                }
            ]
            vector = (
                _observed_money_coefficients_v1(totals[0], money_ordinals=total_columns)
                if len(totals) == 1 and len(total_columns) == 1
                else None
            )
            detail_totals.append(vector[0] if vector is not None else None)
        source_order_mode = all(not dates for dates in title_dates)
        explicit_mode = all(len(dates) == 1 for dates in title_dates)
        summary_dates = [
            sorted(item.isoformat() for item in _surface_dates(surface))
            for surface in period_surfaces
        ]
        axis_valid = (
            summary_values is not None
            and detail_totals == summary_values
            and all(len(dates) == 1 for dates in summary_dates)
            and (
                source_order_mode
                or (
                    explicit_mode
                    and [dates[0] for dates in title_dates]
                    == [dates[0] for dates in summary_dates]
                )
            )
        )
        if axis_valid:
            for lane, index in enumerate(transposed_indices):
                table = _region_table(projected_pages, projected_regions[index])
                period_surface = (
                    table.get("title_exact") if explicit_mode else period_surfaces[lane]
                )
                for column_ordinal, column in enumerate(table["columns"], start=1):
                    before_path = canonical_clone_v1(column.get("header_path_exact"))
                    after_path = [period_surface, *before_path]
                    receipt_for(index)["column_projections"].append(
                        {
                            "after_header_path_exact": canonical_clone_v1(after_path),
                            "before_header_path_exact": before_path,
                            "column_ordinal": column_ordinal,
                            "projection_kind": (
                                "EXPLICIT_TABLE_TITLE_PERIOD"
                                if explicit_mode
                                else "EXACT_TWO_TABLE_SOURCE_ORDER_PERIOD"
                            ),
                        }
                    )
                    column["header_path_exact"] = after_path
                receipt_for(index)["summary_corroboration"] = {
                    "detail_total": detail_totals[lane],
                    "period_surface_exact": period_surface,
                    "summary_lane": lane,
                    "summary_total": summary_values[lane],
                }
            dropped_summary_indices.add(summary_index)

    receipts = []
    for index, item in sorted(receipts_by_index.items()):
        region = projected_regions[index]
        table = _region_table(projected_pages, region)
        page = projected_pages[region["page_json_version_id"]]
        section = page["sections"][int(region["section_id"][1:]) - 1]
        classification = classify_gemini_json_multitable_hierarchical_table_v1(
            page, section, table, compiled_specs=compiled_specs
        )
        before_roles = canonical_clone_v1(region["component_roles"])
        after_roles = _classification_component_roles_v1(classification)
        region["component_roles"] = after_roles
        material = {
            **item,
            "format_version": TRANSPOSED_AXIS_PROJECTION_RECEIPT_FORMAT_VERSION,
            "region_component_roles": {"after": after_roles, "before": before_roles},
            "rule": (
                "EXACT_TRANSPOSED_SOURCE_SYNTAX_ONLY_TOTAL_SYNONYM_PERIOD_HEADER_"
                "OR_CORROBORATED_PERIOD_LIKE_TERMINAL_NO_VALUE_MUTATION"
            ),
        }
        receipts.append(
            {
                **material,
                "transposed_axis_projection_receipt_id": (
                    "gjivptaprv1:receipt:" + canonical_json_sha256_v1(material)
                ),
            }
        )
    if dropped_summary_indices:
        kept = [
            region
            for index, region in enumerate(projected_regions)
            if index not in dropped_summary_indices
        ]
        for fragment_ordinal, region in enumerate(kept, start=1):
            region["fragment_ordinal"] = fragment_ordinal
        for receipt in receipts:
            receipt["dropped_summary_regions"] = canonical_clone_v1(
                [regions[index] for index in sorted(dropped_summary_indices)]
            )
            receipt_material = {
                key: canonical_clone_v1(value)
                for key, value in receipt.items()
                if key != "transposed_axis_projection_receipt_id"
            }
            receipt["transposed_axis_projection_receipt_id"] = (
                "gjivptaprv1:receipt:"
                + canonical_json_sha256_v1(receipt_material)
            )
        projected_regions = kept
    return projected_pages, projected_regions, receipts


def _apply_visible_dash_transcription_cleanup(
    *,
    pages: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    projected_pages = {
        version_id: canonical_clone_v1(page) for version_id, page in pages.items()
    }
    repairs = []
    for region in regions:
        table = _region_table(projected_pages, region)
        columns = table.get("columns")
        rows = table.get("rows")
        money_ordinals = [
            ordinal
            for ordinal, column in enumerate(columns or [], start=1)
            if type(column) is dict and column.get("value_kind") == "MONEY"
        ]
        if type(rows) is not list:
            continue
        for row_ordinal, row in enumerate(rows, start=1):
            values = row.get("values_exact") if type(row) is dict else None
            if type(values) is not list:
                continue
            for column_ordinal in money_ordinals:
                if (
                    column_ordinal <= len(values)
                    and values[column_ordinal - 1]
                    in _VISIBLE_DASH_TRANSCRIPTION_ARTEFACTS
                ):
                    before = values[column_ordinal - 1]
                    repairs.append(
                        {
                            "after_source_text": "-",
                            "before_source_text": before,
                            "column_ordinal": column_ordinal,
                            "locator": {
                                key: region[key]
                                for key in (
                                    "page_json_version_id",
                                    "physical_page",
                                    "section_id",
                                    "table_id",
                                )
                            },
                            "row_ordinal": row_ordinal,
                            "rule": "EXACT_PDF_VISIBLE_DASH_TRANSCRIPTION_TOKEN",
                        }
                    )
                    values[column_ordinal - 1] = "-"
    return projected_pages, repairs


def _restore_face_value_projection_source_refs(
    candidate: dict[str, Any],
    *,
    receipts: Sequence[Mapping[str, Any]],
    original_regions: Sequence[Mapping[str, Any]],
    original_query_receipt: Mapping[str, Any],
) -> None:
    by_locator = {
        tuple(receipt["locator"][key] for key in ("page_json_version_id", "section_id", "table_id")):
        receipt
        for receipt in receipts
    }
    projection_by_row = {
        (*locator, projection["row_ordinal"]): projection
        for locator, receipt in by_locator.items()
        for projection in receipt["projections"]
    }
    for mapping in candidate.get("mappings", []):
        for source_ref in mapping.get("source_refs", []):
            locator = source_ref.get("locator") if type(source_ref) is dict else None
            if type(locator) is not dict:
                continue
            key = tuple(
                locator.get(field)
                for field in ("page_json_version_id", "section_id", "table_id")
            )
            receipt = by_locator.get(key)
            if receipt is None:
                continue
            locator["component_roles"] = canonical_clone_v1(
                receipt["region_component_roles"]["before"]
            )
            projection = projection_by_row.get((*key, source_ref.get("row_ordinal")))
            if projection is not None:
                if "after_hierarchy_path_exact" in projection:
                    if source_ref.get("hierarchy_path_exact") != projection[
                        "after_hierarchy_path_exact"
                    ]:
                        raise _error(
                            "issued-paper face-value projection source drifted"
                        )
                    source_ref["hierarchy_path_exact"] = canonical_clone_v1(
                        projection["before_hierarchy_path_exact"]
                    )
                if "after_label_exact" in projection:
                    if source_ref.get("label_exact") != projection[
                        "after_label_exact"
                    ]:
                        raise _error(
                            "issued-paper face-value projection label drifted"
                        )
                    source_ref["label_exact"] = projection["before_label_exact"]
                if "after_row_kind" in projection:
                    if source_ref.get("row_kind") != projection["after_row_kind"]:
                        raise _error(
                            "issued-paper face-value projection row-kind drifted"
                        )
                    source_ref["row_kind"] = projection["before_row_kind"]
        material = {
            key: mapping[key] for key in mapping if key != "item_mapping_id"
        }
        mapping["item_mapping_id"] = (
            "gjmthfmv1:item:" + canonical_json_sha256_v1(material)
        )
    table_receipts = candidate.get("closure_receipt", {}).get("table_receipts", [])
    for table_receipt in table_receipts if type(table_receipts) is list else []:
        region = table_receipt.get("region") if type(table_receipt) is dict else None
        if type(region) is not dict:
            continue
        key = tuple(
            region.get(field)
            for field in ("page_json_version_id", "section_id", "table_id")
        )
        receipt = by_locator.get(key)
        if receipt is not None:
            region["component_roles"] = canonical_clone_v1(
                receipt["region_component_roles"]["before"]
            )
    candidate["component_regions"] = canonical_clone_v1(list(original_regions))
    candidate["closure_receipt"]["query_receipt"] = canonical_clone_v1(
        original_query_receipt
    )


def _restore_tenor_instrument_projection_source_refs(
    candidate: dict[str, Any],
    *,
    receipts: Sequence[Mapping[str, Any]],
    original_regions: Sequence[Mapping[str, Any]],
    original_query_receipt: Mapping[str, Any],
) -> None:
    by_locator = {
        tuple(
            receipt["locator"][key]
            for key in ("page_json_version_id", "section_id", "table_id")
        ): receipt
        for receipt in receipts
    }
    projection_by_row = {
        (*locator, projection["row_ordinal"]): projection
        for locator, receipt in by_locator.items()
        for projection in receipt["projections"]
    }
    for mapping in candidate.get("mappings", []):
        for source_ref in mapping.get("source_refs", []):
            locator = source_ref.get("locator") if type(source_ref) is dict else None
            if type(locator) is not dict:
                continue
            key = tuple(
                locator.get(field)
                for field in ("page_json_version_id", "section_id", "table_id")
            )
            receipt = by_locator.get(key)
            if receipt is None:
                continue
            locator["component_roles"] = canonical_clone_v1(
                receipt["region_component_roles"]["before"]
            )
            projection = projection_by_row.get((*key, source_ref.get("row_ordinal")))
            if projection is not None:
                if source_ref.get("hierarchy_path_exact") != projection[
                    "after_hierarchy_path_exact"
                ]:
                    raise _error("issued-paper tenor projection source drifted")
                source_ref["hierarchy_path_exact"] = canonical_clone_v1(
                    projection["before_hierarchy_path_exact"]
                )
        material = {
            key: mapping[key] for key in mapping if key != "item_mapping_id"
        }
        mapping["item_mapping_id"] = (
            "gjmthfmv1:item:" + canonical_json_sha256_v1(material)
        )
    table_receipts = candidate.get("closure_receipt", {}).get("table_receipts", [])
    for table_receipt in table_receipts if type(table_receipts) is list else []:
        region = table_receipt.get("region") if type(table_receipt) is dict else None
        if type(region) is not dict:
            continue
        key = tuple(
            region.get(field)
            for field in ("page_json_version_id", "section_id", "table_id")
        )
        receipt = by_locator.get(key)
        if receipt is not None:
            region["component_roles"] = canonical_clone_v1(
                receipt["region_component_roles"]["before"]
            )
    candidate["component_regions"] = canonical_clone_v1(list(original_regions))
    candidate["closure_receipt"]["query_receipt"] = canonical_clone_v1(
        original_query_receipt
    )


def _restore_source_syntax_projection_refs_v1(
    candidate: dict[str, Any],
    *,
    receipts: Sequence[Mapping[str, Any]],
    original_regions: Sequence[Mapping[str, Any]],
    original_query_receipt: Mapping[str, Any],
) -> None:
    by_locator = {
        tuple(
            receipt["locator"][key]
            for key in ("page_json_version_id", "section_id", "table_id")
        ): receipt
        for receipt in receipts
    }
    row_projection_by_axis = {
        (*locator, projection["row_ordinal"]): projection
        for locator, receipt in by_locator.items()
        for projection in receipt.get("row_projections", [])
    }
    for mapping in candidate.get("mappings", []):
        for source_ref in mapping.get("source_refs", []):
            locator = source_ref.get("locator") if type(source_ref) is dict else None
            if type(locator) is not dict:
                continue
            key = tuple(
                locator.get(field)
                for field in ("page_json_version_id", "section_id", "table_id")
            )
            receipt = by_locator.get(key)
            if receipt is None:
                continue
            locator["component_roles"] = canonical_clone_v1(
                receipt["region_component_roles"]["before"]
            )
            projection = row_projection_by_axis.get((*key, source_ref.get("row_ordinal")))
            if projection is None:
                continue
            if "after_label_exact" in projection:
                if source_ref.get("label_exact") != projection["after_label_exact"]:
                    raise _error("issued-paper projected row label source drifted")
                source_ref["label_exact"] = projection["before_label_exact"]
            if "after_hierarchy_path_exact" in projection:
                if source_ref.get("hierarchy_path_exact") != projection[
                    "after_hierarchy_path_exact"
                ]:
                    raise _error("issued-paper projected row hierarchy source drifted")
                source_ref["hierarchy_path_exact"] = canonical_clone_v1(
                    projection["before_hierarchy_path_exact"]
                )
            if "after_row_kind" in projection:
                if source_ref.get("row_kind") != projection["after_row_kind"]:
                    raise _error("issued-paper projected row kind source drifted")
                source_ref["row_kind"] = projection["before_row_kind"]
            before_locator = projection.get("before_locator")
            before_row_ordinal = projection.get("before_row_ordinal")
            if type(before_locator) is dict or before_row_ordinal is not None:
                if type(before_locator) is not dict or type(before_row_ordinal) is not int:
                    raise _error("issued-paper projected source locator is incomplete")
                original_matches = [
                    original_region
                    for original_region in original_regions
                    if all(
                        original_region.get(field) == before_locator.get(field)
                        for field in (
                            "page_json_version_id",
                            "physical_page",
                            "section_id",
                            "table_id",
                        )
                    )
                ]
                if len(original_matches) != 1:
                    raise _error("issued-paper projected source locator drifted")
                projected_row_ordinal = projection["row_ordinal"]
                source_ref["locator"] = canonical_clone_v1(original_matches[0])
                source_ref["row_id"] = f"r{before_row_ordinal}"
                source_ref["row_ordinal"] = before_row_ordinal
                if mapping.get("row_id") == f"r{projected_row_ordinal}":
                    mapping["row_id"] = f"r{before_row_ordinal}"
        material = {
            key: mapping[key] for key in mapping if key != "item_mapping_id"
        }
        mapping["item_mapping_id"] = (
            "gjmthfmv1:item:" + canonical_json_sha256_v1(material)
        )
    table_receipts = candidate.get("closure_receipt", {}).get("table_receipts", [])
    for table_receipt in table_receipts if type(table_receipts) is list else []:
        region = table_receipt.get("region") if type(table_receipt) is dict else None
        if type(region) is not dict:
            continue
        key = tuple(
            region.get(field)
            for field in ("page_json_version_id", "section_id", "table_id")
        )
        receipt = by_locator.get(key)
        if receipt is not None:
            region["component_roles"] = canonical_clone_v1(
                receipt["region_component_roles"]["before"]
            )
    candidate["component_regions"] = canonical_clone_v1(list(original_regions))
    candidate["closure_receipt"]["query_receipt"] = canonical_clone_v1(
        original_query_receipt
    )


def _apply_authenticated_source_repairs(
    *,
    regions: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    pages = {
        version_id: canonical_clone_v1(page)
        for version_id, page in page_json_by_version.items()
    }
    if not regions:
        return pages, []
    identities = {
        (region.get("source_logical_name"), region.get("source_sha256"))
        for region in regions
    }
    if len(identities) != 1:
        raise _error("issued-paper repair candidate source identity is ambiguous")
    source_logical_name, source_sha256 = next(iter(identities))
    region_locators = {
        tuple(
            region.get(field)
            for field in (
                "page_json_version_id",
                "physical_page",
                "section_id",
                "table_id",
            )
        )
        for region in regions
    }
    applicable = [
        canonical_clone_v1(repair)
        for repair in compiled_specs.get("issued_valuable_papers_source_repairs", [])
        if repair["source"]["source_sha256"] == source_sha256
        and tuple(
            repair["locator"][field]
            for field in (
                "page_json_version_id",
                "physical_page",
                "section_id",
                "table_id",
            )
        )
        in region_locators
    ]
    for repair in applicable:
        source = repair["source"]
        locator = repair["locator"]
        if source["source_logical_name"] != source_logical_name:
            raise _error("issued-paper repair logical source identity drifted")
        matching_regions = [
            region
            for region in regions
            if all(
                region.get(field) == locator[field]
                for field in (
                    "page_json_version_id",
                    "physical_page",
                    "section_id",
                    "table_id",
                )
            )
        ]
        if len(matching_regions) != 1:
            raise _error("issued-paper repair is outside its selected component table")
        page = pages.get(locator["page_json_version_id"])
        if page is None:
            raise _error("issued-paper repair page is outside the selected document")
        table = _region_table(pages, matching_regions[0])
        rows = table.get("rows")
        if type(rows) is not list or locator["row_ordinal"] > len(rows):
            raise _error("issued-paper repair row is outside its selected table")
        row = rows[locator["row_ordinal"] - 1]
        values = row.get("values_exact") if type(row) is dict else None
        if (
            type(values) is not list
            or locator["column_ordinal"] > len(values)
            or values[locator["column_ordinal"] - 1] is not repair["before_exact"]
        ):
            raise _error("issued-paper repair cell before-image drifted")
        values[locator["column_ordinal"] - 1] = repair["after_exact"]
    return pages, applicable


def _reseal_candidate(
    candidate: dict[str, Any],
    *,
    adjacent_source_syntax_projection_receipts: Sequence[Mapping[str, Any]],
    authenticated_source_repairs: Sequence[Mapping[str, Any]],
    face_value_wrapper_receipts: Sequence[Mapping[str, Any]],
    maturity_validation_projection_receipts: Sequence[Mapping[str, Any]],
    primary_root_projection_receipt: Mapping[str, Any] | None,
    tenor_instrument_projection_receipts: Sequence[Mapping[str, Any]],
    transposed_axis_projection_receipts: Sequence[Mapping[str, Any]],
    validation_row_projection_receipts: Sequence[Mapping[str, Any]],
    visible_dash_transcription_repairs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if (
        not adjacent_source_syntax_projection_receipts
        and not authenticated_source_repairs
        and not face_value_wrapper_receipts
        and not maturity_validation_projection_receipts
        and primary_root_projection_receipt is None
        and not tenor_instrument_projection_receipts
        and not transposed_axis_projection_receipts
        and not validation_row_projection_receipts
        and not visible_dash_transcription_repairs
    ):
        return candidate
    material = {
        "adapter_format_version": ADAPTER_FORMAT_VERSION,
        "adjacent_source_syntax_projection_receipts": canonical_clone_v1(
            list(adjacent_source_syntax_projection_receipts)
        ),
        "authenticated_source_repairs": canonical_clone_v1(
            list(authenticated_source_repairs)
        ),
        "face_value_wrapper_receipts": canonical_clone_v1(
            list(face_value_wrapper_receipts)
        ),
        "maturity_validation_projection_receipts": canonical_clone_v1(
            list(maturity_validation_projection_receipts)
        ),
        "primary_root_projection_receipt": canonical_clone_v1(
            primary_root_projection_receipt
        ),
        "shared_engine_claim_boundary": GENERIC_CLAIM_BOUNDARY,
        "tenor_instrument_projection_receipts": canonical_clone_v1(
            list(tenor_instrument_projection_receipts)
        ),
        "transposed_axis_projection_receipts": canonical_clone_v1(
            list(transposed_axis_projection_receipts)
        ),
        "validation_row_projection_receipts": canonical_clone_v1(
            list(validation_row_projection_receipts)
        ),
        "visible_dash_transcription_repairs": canonical_clone_v1(
            list(visible_dash_transcription_repairs)
        ),
    }
    candidate["claim_boundary"] = ADAPTER_CLAIM_BOUNDARY
    candidate["closure_receipt"]["issued_valuable_papers_adapter_receipt"] = {
        **material,
        "adapter_receipt_id": "gjivpfav1:receipt:" + canonical_json_sha256_v1(material),
    }
    candidate_material = {
        key: candidate[key] for key in candidate if key != "candidate_id"
    }
    candidate["candidate_id"] = (
        "gjmthfcv1:candidate:" + canonical_json_sha256_v1(candidate_material)
    )
    return candidate


def evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate Family 25 after applying only authenticated dash observations."""

    if compiled_specs.get("topology", {}).get("family_id") != FAMILY_ID:
        raise _error("issued-paper adapter received another family")
    if type(regions) not in {list, tuple} or not regions:
        return evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
            regions=regions,
            page_json_by_version=page_json_by_version,
            compiled_specs=compiled_specs,
            query_receipt=query_receipt,
        )
    pages, repairs = _apply_authenticated_source_repairs(
        regions=regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
    )
    primary_projection = None
    if len(regions) == 1:
        identified_projection = _primary_statement_exact_root_projection_v1(
            region=regions[0],
            page_json_by_version=pages,
            compiled_specs=compiled_specs,
        )
        if identified_projection is not None:
            _unused_pages, primary_projection = identified_projection
    if primary_projection is not None:
        projected_pages = _apply_primary_root_projection_receipt_v1(
            page_json_by_version=pages,
            receipt=primary_projection,
        )
        candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
            regions=regions,
            page_json_by_version=projected_pages,
            compiled_specs=compiled_specs,
            query_receipt=query_receipt,
        )
        if candidate.get("status") == READY:
            _restore_primary_root_mapping_source_refs_v1(
                candidate, receipt=primary_projection
            )
        return _reseal_candidate(
            candidate,
            adjacent_source_syntax_projection_receipts=[],
            authenticated_source_repairs=repairs,
            face_value_wrapper_receipts=[],
            maturity_validation_projection_receipts=[],
            primary_root_projection_receipt=primary_projection,
            tenor_instrument_projection_receipts=[],
            transposed_axis_projection_receipts=[],
            validation_row_projection_receipts=[],
            visible_dash_transcription_repairs=[],
        )
    adjacent_projected_pages, adjacent_projected_regions, adjacent_receipts = (
        _project_adjacent_source_syntax_v1(
            pages=pages,
            regions=regions,
            compiled_specs=compiled_specs,
        )
    )
    adjacent_projected_query_receipt = (
        build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            adjacent_projected_regions
        )
        if adjacent_receipts
        else query_receipt
    )
    validation_projected_pages, validation_projected_regions, validation_receipts = (
        _project_exact_validation_rows_v1(
            pages=adjacent_projected_pages,
            regions=adjacent_projected_regions,
            compiled_specs=compiled_specs,
        )
    )
    validation_projected_query_receipt = (
        build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            validation_projected_regions
        )
        if validation_receipts
        else adjacent_projected_query_receipt
    )
    maturity_projected_pages, maturity_projected_regions, maturity_receipts = (
        _project_maturity_context_and_prune_validations_v1(
            pages=validation_projected_pages,
            regions=validation_projected_regions,
            compiled_specs=compiled_specs,
        )
    )
    maturity_projected_query_receipt = (
        build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            maturity_projected_regions
        )
        if maturity_receipts
        else validation_projected_query_receipt
    )
    face_projected_pages, face_projected_regions, wrapper_receipts = (
        _project_face_value_wrappers(
            pages=maturity_projected_pages,
            regions=maturity_projected_regions,
            compiled_specs=compiled_specs,
        )
    )
    projected_pages, projected_regions, tenor_projection_receipts = (
        _project_tenor_carrier_instrument_rows(
            pages=face_projected_pages,
            regions=face_projected_regions,
            compiled_specs=compiled_specs,
        )
    )
    projected_pages, dash_repairs = _apply_visible_dash_transcription_cleanup(
        pages=projected_pages,
        regions=projected_regions,
    )
    face_projected_query_receipt = (
        build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            face_projected_regions
        )
        if wrapper_receipts
        else maturity_projected_query_receipt
    )
    projected_query_receipt = (
        build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            projected_regions
        )
        if tenor_projection_receipts
        else face_projected_query_receipt
    )
    transposed_input_regions = canonical_clone_v1(projected_regions)
    transposed_input_query_receipt = projected_query_receipt
    projected_pages, projected_regions, transposed_receipts = (
        _project_transposed_source_axes_v1(
            pages=projected_pages,
            regions=projected_regions,
            compiled_specs=compiled_specs,
        )
    )
    projected_query_receipt = (
        build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            projected_regions
        )
        if transposed_receipts
        else projected_query_receipt
    )
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=projected_regions,
        page_json_by_version=projected_pages,
        compiled_specs=compiled_specs,
        query_receipt=projected_query_receipt,
    )
    if transposed_receipts:
        _restore_source_syntax_projection_refs_v1(
            candidate,
            receipts=transposed_receipts,
            original_regions=transposed_input_regions,
            original_query_receipt=transposed_input_query_receipt,
        )
    if tenor_projection_receipts:
        _restore_tenor_instrument_projection_source_refs(
            candidate,
            receipts=tenor_projection_receipts,
            original_regions=face_projected_regions,
            original_query_receipt=face_projected_query_receipt,
        )
    if wrapper_receipts:
        _restore_face_value_projection_source_refs(
            candidate,
            receipts=wrapper_receipts,
            original_regions=regions,
            original_query_receipt=query_receipt,
        )
    if maturity_receipts:
        _restore_source_syntax_projection_refs_v1(
            candidate,
            receipts=maturity_receipts,
            original_regions=validation_projected_regions,
            original_query_receipt=validation_projected_query_receipt,
        )
    if validation_receipts:
        _restore_source_syntax_projection_refs_v1(
            candidate,
            receipts=validation_receipts,
            original_regions=adjacent_projected_regions,
            original_query_receipt=adjacent_projected_query_receipt,
        )
    if adjacent_receipts:
        _restore_source_syntax_projection_refs_v1(
            candidate,
            receipts=adjacent_receipts,
            original_regions=regions,
            original_query_receipt=query_receipt,
        )
    return _reseal_candidate(
        candidate,
        adjacent_source_syntax_projection_receipts=adjacent_receipts,
        authenticated_source_repairs=repairs,
        face_value_wrapper_receipts=wrapper_receipts,
        maturity_validation_projection_receipts=maturity_receipts,
        primary_root_projection_receipt=None,
        tenor_instrument_projection_receipts=tenor_projection_receipts,
        transposed_axis_projection_receipts=transposed_receipts,
        validation_row_projection_receipts=validation_receipts,
        visible_dash_transcription_repairs=dash_repairs,
    )


def validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(
    value: Any,
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay the complete adapter path from immutable selected JSON."""

    expected = evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if type(value) is not dict or not same_typed_json_v1(value, expected):
        raise _error("issued-paper family adapter candidate replay drifted")
    return expected
