"""Family 23 adapter over the multi-table hierarchical evaluator.

The shared evaluator remains the authority for owner/reset fencing, role
classification, period lanes, arithmetic closure, and schema bindings.  This
adapter owns only two Family-23 source presentations which the shared engine
deliberately does not generalize:

* source-authenticated exact-VND notes retain ``VND`` rather than being
  mislabeled as ``MILLION_VND``; and
* a bounded set of visible-dash transcription artefacts, including exact
  null cells backed by registered full-page/crop render receipts, and a
  headerless adjacent continuation fragment proved by an exact primary-
  statement owner-row total can be replayed.  The immutable selected Gemini
  JSON is never changed.

Registered repairs are exact source/page/table/row/column observations rather
than inference routes.  Literal token cleanup and continuation recovery remain
generic over source identities.  No null cell is interpreted as zero from an
equation or owner total.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.evaluation.gemini_json_customer_deposit_family_v1 import (
    _document_unit_context_axis,
    _money,
    _two_period_axis,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    compile_gemini_json_flat_family_specs_v1,
)
from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import (
    _matches,
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
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
    validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FAMILY_ID = "GOVERNMENT_SBV_LIABILITIES"
ADAPTER_FORMAT_VERSION = "GEMINI_JSON_GOVERNMENT_SBV_LIABILITIES_FAMILY_ADAPTER_V1"
ADJACENT_QUERY_RECEIPT_FORMAT_VERSION = (
    "GEMINI_JSON_GOVERNMENT_SBV_LIABILITIES_ADJACENT_QUERY_RECEIPT_V1"
)
PRIMARY_ROOT_QUERY_RECEIPT_FORMAT_VERSION = (
    "GEMINI_JSON_GOVERNMENT_SBV_LIABILITIES_PRIMARY_ROOT_QUERY_RECEIPT_V1"
)
DIRECT_ROOT_CHILD_PROJECTION_RECEIPT_FORMAT_VERSION = (
    "GEMINI_JSON_GOVERNMENT_SBV_LIABILITIES_DIRECT_ROOT_CHILD_PROJECTION_RECEIPT_V1"
)
SOURCE_REPAIR_FORMAT_VERSION = (
    "GEMINI_JSON_GOVERNMENT_SBV_LIABILITIES_AUTHENTICATED_SOURCE_REPAIR_SPEC_V1"
)
ADAPTER_CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_FAMILY23_GENERIC_OWNER_ROLE_PERIOD_UNIT_"
    "AND_ACCOUNTING_CLOSURE_WITH_EXACT_SOURCE_UNIT_RETENTION_AND_BOUNDED_DASH_"
    "OVERLAY_PROVED_BY_AUTHENTICATED_FULL_PAGE_AND_CELL_CROP_OR_SAME_DOCUMENT_"
    "UNIT_BEARING_PRIMARY_OWNER_TOTAL_SCHEMA_MAPPING_PROPOSAL_ONLY_NO_SOURCE_"
    "MUTATION_OCR_PROVIDER_BANK_VALUE_ROUTING_NULL_ZERO_BACKSOLVE_CANONICAL_OR_"
    "EXPORT_AUTHORITY"
)

# These are literal non-numeric suffixes already present in the immutable
# selected JSON where the corresponding source PDF shows one accounting dash.
# They are extraction-token classes, not document identities or value routes.
_VISIBLE_DASH_TRANSCRIPTION_ARTEFACTS = frozenset(
    {
        "-ktCap",
        "-ktCap-",
        "-单",
        "-单-",
    }
)
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_PAGE_VERSION = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_SECTION_ID = re.compile(r"s[1-9][0-9]*\Z")
_TABLE_ID = re.compile(r"t[1-9][0-9]*\Z")


class GeminiJsonGovernmentSbvLiabilitiesFamilyV1Error(ValueError):
    """Family-23 specs, overlay proof, candidate, or replay drifted."""


def _error(message: str) -> GeminiJsonGovernmentSbvLiabilitiesFamilyV1Error:
    return GeminiJsonGovernmentSbvLiabilitiesFamilyV1Error(message)


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
        raise _error("Government/SBV authenticated source-repair spec is invalid")
    checked = []
    identities = set()
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
            != {
                "bbox_pixels_xyxy",
                "pixel_height",
                "pixel_width",
                "rgb_sha256",
            }
            or type(bbox) is not list
            or len(bbox) != 4
            or any(type(value) is not int for value in bbox)
            or not (0 <= bbox[0] < bbox[2] <= render["pixel_width"])
            or not (0 <= bbox[1] < bbox[3] <= render["pixel_height"])
            or crop.get("pixel_width") != bbox[2] - bbox[0]
            or crop.get("pixel_height") != bbox[3] - bbox[1]
            or _SHA256.fullmatch(crop.get("rgb_sha256", "")) is None
        ):
            raise _error("Government/SBV authenticated source repair is invalid")
        material = {
            key: canonical_clone_v1(item)
            for key, item in repair.items()
            if key != "repair_id"
        }
        if repair.get("repair_id") != (
            "gjslfav1:source-repair:" + canonical_json_sha256_v1(material)
        ):
            raise _error("Government/SBV source-repair identity drifted")
        identity = (
            source["source_sha256"],
            locator["page_json_version_id"],
            locator["section_id"],
            locator["table_id"],
            locator["row_ordinal"],
            locator["column_ordinal"],
        )
        if identity in identities:
            raise _error("Government/SBV source-repair cell axis is duplicate")
        identities.add(identity)
        checked.append(canonical_clone_v1(repair))
    if value.get("repair_axis_sha256") != canonical_json_sha256_v1(checked):
        raise _error("Government/SBV source-repair axis seal drifted")
    return checked


def compile_gemini_json_government_sbv_liabilities_family_specs_v1(
    topology_spec: Any,
    evaluation_spec: Any,
    schema_binding_spec: Any,
    source_repair_spec: Any,
) -> dict[str, Any]:
    """Compile and bind one declarative Family-23 triplet."""

    compiled = compile_gemini_json_flat_family_specs_v1(
        topology_spec, evaluation_spec, schema_binding_spec
    )
    return bind_gemini_json_government_sbv_liabilities_source_repairs_v1(
        compiled, source_repair_spec
    )


def bind_gemini_json_government_sbv_liabilities_source_repairs_v1(
    compiled_specs: Any,
    source_repair_spec: Any,
) -> dict[str, Any]:
    """Bind exact PDF observations to an already compiled generic family."""

    if type(compiled_specs) is not dict:
        raise _error("Government/SBV compiled family frontier is invalid")
    compiled = canonical_clone_v1(compiled_specs)
    if (
        compiled.get("topology", {}).get("family_id") != FAMILY_ID
        or compiled.get("schema", {}).get("family_id") != FAMILY_ID
        or compiled.get("evaluation", {}).get("family_id") != FAMILY_ID
        or set(compiled.get("bindings", {}))
        != {
            "CENTRAL_BANK_LOAN",
            "CREDIT_FILE_LOAN",
            "DISCOUNT_LOAN",
            "PLEDGED_SECURITIES_LOAN",
            "CLEARING_LOAN",
            "SPECIAL_SUPPORT_LOAN",
            "LONG_TERM_INTERNATIONAL_LOAN",
            "STATE_ENTERPRISE_SUPPORT_LOAN",
            "REFINANCE_LOAN",
            "OTHER_LOAN",
            "OVERDUE_LOAN",
            "TREASURY_PAYMENT_DEPOSIT",
            "TREASURY_PAYMENT_VND",
            "TREASURY_PAYMENT_FOREIGN",
            "TREASURY_TERM_DEPOSIT",
            "CENTRAL_BANK_DEPOSIT",
            "MINISTRY_FINANCE_DEPOSIT",
            "OTHER_LIABILITY",
        }
        or {
            item["canonical_unit"]
            for item in compiled.get("unit_bindings", [])
            if item.get("accepted") is True
        }
        != {"MILLION_VND", "VND"}
    ):
        raise _error("Government/SBV declarative family frontier is invalid")
    compiled["government_sbv_liabilities_source_repairs"] = _validate_source_repairs(
        source_repair_spec
    )
    compiled["government_sbv_liabilities_source_repair_spec_sha256"] = (
        canonical_json_sha256_v1(source_repair_spec)
    )
    compiled["government_sbv_liabilities_adapter_format_version"] = ADAPTER_FORMAT_VERSION
    return compiled


def build_gemini_json_government_sbv_liabilities_region_query_receipt_v1(
    regions: Any,
) -> dict[str, Any]:
    """Seal the unchanged generic query-region axis."""

    return build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)


def _blank_surface(value: Any) -> bool:
    return value is None or type(value) is str and not value.strip()


def _exact_owner_alias(
    value: Any, *, compiled_specs: Mapping[str, Any]
) -> str | None:
    folded = _without_leading_ordinal(_normalized(value))
    matches = [
        alias
        for alias in compiled_specs["query_policy"]["owner_aliases"]
        if folded == alias
    ]
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


def _page_table_positions(page: Mapping[str, Any]) -> list[tuple[int, int]]:
    result = []
    for section_ordinal, section in enumerate(page.get("sections") or [], start=1):
        if type(section) is not dict:
            continue
        for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
            if type(table) is dict:
                result.append((section_ordinal, table_ordinal))
    return result


def _adjacent_owner_continuation_receipt_v1(
    *,
    cluster: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    document_unit_context: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Prove one exact page-final owner / next-page leading continuation.

    This is intentionally stricter than ordinary owner fencing.  It recovers
    only the extraction shape where an exact owner heading is the final table
    on one page and the immediately following selected/physical page begins
    with one titleless ``CONTINUES_FROM_PREVIOUS_PAGE`` family table.  A
    primary-statement owner row must independently prove the target total,
    period pair, and unit.
    """

    if cluster.get("reasons") != ["COMPLETE_OWNER_CLUSTER_NOT_RESOLVED"]:
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
    if len(page_axis) != len(page_json_by_version):
        return None

    owner_candidates = []
    target_candidates = []
    for item in inventory:
        if type(item) is not dict or type(item.get("classification")) is not dict:
            continue
        classification = item["classification"]
        resolved = _table_from_inventory(
            inventory_item=item, page_json_by_version=page_json_by_version
        )
        if resolved is None:
            continue
        section, table = resolved
        axis_item = page_axis.get(item.get("page_json_version_id"))
        page = page_json_by_version.get(item.get("page_json_version_id"))
        if type(axis_item) is not dict or type(page) is not dict:
            continue
        columns = table.get("columns")
        rows = table.get("rows")
        money_ordinals = _money_ordinals(table)
        if type(columns) is not list or type(rows) is not list or money_ordinals != [1, 2]:
            continue

        owner_alias = _exact_owner_alias(
            table.get("title_exact"), compiled_specs=compiled_specs
        )
        owner_position = (
            int(item["section_id"][1:]),
            int(item["table_id"][1:]),
        )
        if (
            owner_alias is not None
            and classification.get("owner_visible") is True
            and not classification.get("role_hits")
            and not classification.get("total_rows")
            and not classification.get("unbound_money_row_ordinals")
            and table.get("continuation") == "CONTINUES_ON_NEXT_PAGE"
            and (table.get("unit_exact") is None or table.get("unit_exact") == "")
            and _blank_surface(section.get("title_exact"))
            and _blank_surface(section.get("narrative_exact"))
            and _page_table_positions(page)
            and owner_position == _page_table_positions(page)[-1]
            and int(item["section_id"][1:]) == len(page.get("sections") or [])
            and all(
                type(row) is dict
                and row.get("row_kind") == "UNKNOWN"
                and _blank_surface(row.get("label_exact"))
                and type(row.get("values_exact")) is list
                and len(row["values_exact"]) == 2
                and all(value is None for value in row["values_exact"])
                for row in rows
            )
        ):
            owner_period_axis = _two_period_axis(table)
            if owner_period_axis.get("complete") is True:
                owner_candidates.append(
                    (item, section, table, axis_item, owner_alias, owner_period_axis)
                )

        role_hits = classification.get("role_hits")
        roles = sorted(
            {
                *(hit.get("role") for hit in role_hits if type(hit) is dict),
                *(classification.get("context_roles") or []),
            }
            - {None}
        ) if type(role_hits) is list else []
        root_roles = set(roles).intersection(compiled_specs["root_component_roles"])
        target_position = item.get("position")
        terminal_totals = classification.get("total_rows")
        header_paths = [column.get("header_path_exact") for column in columns]
        if (
            classification.get("owner_visible") is False
            and classification.get("ambiguous_rows") == []
            and classification.get("typed_control_disposition") is None
            and classification.get("family_presence_anchor_visible") is True
            and len(root_roles) >= 2
            and len(roles) >= compiled_specs["minimum_declared_detail_role_count"]
            and type(target_position) is list
            and target_position == [item.get("physical_page"), 1, 1]
            and _page_table_positions(page)
            and _page_table_positions(page)[0] == (1, 1)
            and item.get("section_id") == "s1"
            and item.get("table_id") == "t1"
            and _blank_surface(section.get("title_exact"))
            and _blank_surface(section.get("narrative_exact"))
            and _blank_surface(table.get("title_exact"))
            and table.get("continuation") == "CONTINUES_FROM_PREVIOUS_PAGE"
            and (table.get("unit_exact") is None or table.get("unit_exact") == "")
            and all(
                type(path) is list and path and all(_blank_surface(value) for value in path)
                for path in header_paths
            )
            and type(terminal_totals) is list
            and terminal_totals
            and terminal_totals == [
                {
                    "row_kind": "TOTAL",
                    "row_ordinal": len(rows),
                    "source_order": len(rows),
                }
            ]
            and classification.get("unbound_money_row_ordinals") == [len(rows)]
            and type(rows[-1]) is dict
            and rows[-1].get("row_kind") == "TOTAL"
            and type(rows[-1].get("values_exact")) is list
            and len(rows[-1]["values_exact"]) == 2
        ):
            target_coefficients = [
                _coefficient(source) for source in rows[-1]["values_exact"]
            ]
            if all(type(value) is int for value in target_coefficients):
                target_candidates.append(
                    (item, section, table, axis_item, roles, target_coefficients)
                )

    compatible = []
    for owner in owner_candidates:
        owner_item, _owner_section, _owner_table, owner_axis, _, owner_period_axis = owner
        for target in target_candidates:
            target_item, _target_section, _target_table, target_axis, _, target_total = target
            if (
                target_axis.get("selected_page_ordinal")
                != owner_axis.get("selected_page_ordinal") + 1
                or target_axis.get("physical_page") != owner_axis.get("physical_page") + 1
                or any(
                    target_axis.get(field) != owner_axis.get(field)
                    for field in (
                        "document_id",
                        "document_ordinal",
                        "source_logical_name",
                        "source_sha256",
                    )
                )
            ):
                continue
            # Page-final plus next-page-leading leaves no ordered source surface
            # between the two tables.  Retain the explicit empty axis in the
            # receipt so reset-fence absence is independently auditable.
            intervening_surfaces: list[dict[str, Any]] = []
            owner_evidence = [
                canonical_clone_v1(item)
                for item in document_unit_context.get("owner_row_evidence", [])
                if type(item) is dict
                and item.get("coefficients") == target_total
                and item.get("period_axis_complete") is True
                and item.get("period_signatures") == owner_period_axis.get("signatures")
                and item.get("canonical_unit") in {"MILLION_VND", "VND"}
            ]
            unit_identities = {
                (item["canonical_unit"], item.get("magnitude_power10"))
                for item in owner_evidence
            }
            if intervening_surfaces or len(unit_identities) != 1 or not owner_evidence:
                continue
            compatible.append((owner, target, owner_evidence, intervening_surfaces))
    if len(compatible) != 1:
        return None

    owner, target, owner_evidence, intervening_surfaces = compatible[0]
    owner_item, _owner_section, owner_table, owner_axis, owner_alias, owner_period_axis = owner
    target_item, _target_section, _target_table, target_axis, roles, target_total = target
    locator_fields = (
        "page_json_version_id",
        "physical_page",
        "section_id",
        "selected_page_ordinal",
        "table_id",
    )
    owner_locator = {
        **{field: owner_item[field] for field in locator_fields if field in owner_item},
        "selected_page_ordinal": owner_axis["selected_page_ordinal"],
    }
    target_locator = {
        **{field: target_item[field] for field in locator_fields if field in target_item},
        "selected_page_ordinal": target_axis["selected_page_ordinal"],
    }
    material = {
        "document_id": cluster["document_id"],
        "document_ordinal": cluster["document_ordinal"],
        "format_version": ADJACENT_QUERY_RECEIPT_FORMAT_VERSION,
        "intervening_reset_surface_axis": intervening_surfaces,
        "owner_alias": owner_alias,
        "owner_locator": owner_locator,
        "owner_period_axis": canonical_clone_v1(owner_period_axis),
        "owner_source_exact": owner_table["title_exact"],
        "rule": (
            "EXACT_PAGE_FINAL_OWNER_NEXT_SELECTED_AND_PHYSICAL_PAGE_LEADING_TITLELESS_"
            "CONTINUATION_NO_INTERVENING_RESET_COMPATIBLE_PERIOD_AND_PRIMARY_OWNER_UNIT_TOTAL"
        ),
        "source_logical_name": cluster["source_logical_name"],
        "source_sha256": cluster["source_sha256"],
        "target_component_roles": roles,
        "target_locator": target_locator,
        "target_total_coefficients": target_total,
        "unit_owner_evidence": owner_evidence,
        "unit_owner_evidence_axis_sha256": canonical_json_sha256_v1(owner_evidence),
    }
    receipt = {
        **material,
        "adjacent_query_receipt_id": (
            "gjslfaqrv1:receipt:" + canonical_json_sha256_v1(material)
        ),
    }
    region = {
        "component_roles": roles,
        "document_id": cluster["document_id"],
        "document_ordinal": cluster["document_ordinal"],
        "fragment_ordinal": 1,
        "page_json_version_id": target_item["page_json_version_id"],
        "physical_page": target_item["physical_page"],
        "section_id": target_item["section_id"],
        "selected_page_ordinal": target_axis["selected_page_ordinal"],
        "source_logical_name": cluster["source_logical_name"],
        "source_sha256": cluster["source_sha256"],
        "table_id": target_item["table_id"],
    }
    return region, receipt


def _primary_statement_exact_root_projection_v1(
    *,
    region: Mapping[str, Any],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]] | None:
    """Project one exact balance-sheet family-root row for generic evaluation.

    The shared engine correctly excludes primary statements as controls when
    searching for note detail.  Family 23 nevertheless has a schema mapping
    for the visible statement result itself.  This projection is allowed only
    for one exact declared parent row in one balance-sheet table; it never
    selects a value, fills a blank, or imports a neighbouring liability row.
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
        alias = _exact_parent_alias(row.get("label_exact"), compiled_specs=compiled_specs)
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
            "TABLE_PROJECTED_WITHOUT_VALUE_SELECTION_OR_BLANK_COMPLETION"
        ),
        "source_logical_name": region["source_logical_name"],
        "source_sha256": region["source_sha256"],
        "table_unit_exact": table.get("unit_exact"),
    }
    receipt = {
        **material,
        "primary_root_query_receipt_id": (
            "gjslfprqrv1:receipt:" + canonical_json_sha256_v1(material)
        ),
    }
    pages = {
        page_json_version_id: canonical_clone_v1(page_json)
        for page_json_version_id, page_json in page_json_by_version.items()
    }
    projected_page = pages[region["page_json_version_id"]]
    projected_page["status"] = "FINANCIAL_NOTE_CONTENT"
    projected_section = projected_page["sections"][int(region["section_id"][1:]) - 1]
    projected_section["content_kind"] = "FINANCIAL_NOTE"
    projected_section["statement_type"] = "NOT_APPLICABLE"
    projected_table = projected_section["tables"][int(region["table_id"][1:]) - 1]
    projected_row = canonical_clone_v1(projected_table["rows"][row_ordinal - 1])
    projected_row["row_kind"] = "TOTAL"
    projected_table["rows"] = [projected_row]
    projected_table["continuation"] = "NONE"
    return pages, receipt


def _primary_statement_exact_root_query_recovery_v1(
    *,
    cluster: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Recover exactly one classifier-proved primary-statement root table."""

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
    """Apply only the structural projection sealed by an exact root receipt."""

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
        raise _error("Government/SBV primary-root projection locator drifted") from exc
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
    ):
        raise _error("Government/SBV primary-root projection source shape drifted")
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
    """Restore projected r1 references to their immutable source row identity."""

    original = receipt["root_row"]
    locator = receipt["locator"]
    for mapping in candidate.get("mappings", []):
        refs = mapping.get("source_refs") if type(mapping) is dict else None
        if type(refs) is not list or not refs:
            raise _error("Government/SBV projected root mapping source is absent")
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
                raise _error("Government/SBV projected root mapping source drifted")
            source_ref["row_id"] = f"r{original['row_ordinal']}"
            source_ref["row_kind"] = original["row_kind"]
            source_ref["row_ordinal"] = original["row_ordinal"]
        if mapping.get("row_id") == "r1":
            mapping["row_id"] = f"r{original['row_ordinal']}"


def _direct_root_central_child_projection_v1(
    *,
    region: Mapping[str, Any],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]] | None:
    """Scope exact direct loan-detail rows beneath their omitted loan carrier."""

    page = page_json_by_version.get(region.get("page_json_version_id"))
    if type(page) is not dict or page.get("status") == "PRIMARY_FINANCIAL_STATEMENT":
        return None
    try:
        section = page["sections"][int(region["section_id"][1:]) - 1]
        table = section["tables"][int(region["table_id"][1:]) - 1]
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    owner_surfaces = [section.get("title_exact"), table.get("title_exact")]
    owner_aliases = [
        _exact_owner_alias(surface, compiled_specs=compiled_specs)
        for surface in owner_surfaces
    ]
    owner_aliases = sorted({alias for alias in owner_aliases if alias is not None})
    rows = table.get("rows")
    if len(owner_aliases) != 1 or type(rows) is not list:
        return None
    owner_alias = owner_aliases[0]
    central_aliases = compiled_specs["aliases_by_role"]["CENTRAL_BANK_LOAN"]
    if any(
        type(row) is dict
        and any(_matches(row.get("label_exact"), alias) for alias in central_aliases)
        for row in rows
    ):
        return None
    child_roles = [
        role
        for role, matchers in compiled_specs["matchers_by_role"].items()
        if any(matcher.get("within_role") == "CENTRAL_BANK_LOAN" for matcher in matchers)
    ]
    repairs = []
    for row_ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict or row.get("row_kind") == "TOTAL":
            continue
        values = row.get("values_exact")
        hierarchy = row.get("hierarchy_path_exact")
        if type(values) is not list or not any(value is not None for value in values):
            continue
        if (
            type(hierarchy) is not list
            or len(hierarchy) != 2
            or _exact_owner_alias(hierarchy[0], compiled_specs=compiled_specs) != owner_alias
            or hierarchy[1] != row.get("label_exact")
        ):
            return None
        matching_roles = [
            role
            for role in child_roles
            if any(
                _matches(row.get("label_exact"), alias)
                for matcher in compiled_specs["matchers_by_role"][role]
                for alias in matcher["aliases"]
            )
        ]
        if len(matching_roles) != 1:
            return None
        repairs.append(
            {
                "after_hierarchy_path_exact": [
                    hierarchy[0],
                    "Vay NHNN",
                    hierarchy[1],
                ],
                "before_hierarchy_path_exact": canonical_clone_v1(hierarchy),
                "label_exact": row["label_exact"],
                "role": matching_roles[0],
                "row_ordinal": row_ordinal,
            }
        )
    if len(repairs) < 2:
        return None
    material = {
        "format_version": DIRECT_ROOT_CHILD_PROJECTION_RECEIPT_FORMAT_VERSION,
        "locator": {
            key: region[key]
            for key in (
                "page_json_version_id",
                "physical_page",
                "section_id",
                "table_id",
            )
        },
        "owner_alias_normalized": owner_alias,
        "region_component_roles": {
            "after": sorted(
                {
                    *region["component_roles"],
                    *(repair["role"] for repair in repairs),
                }
            ),
            "before": canonical_clone_v1(region["component_roles"]),
        },
        "repairs": repairs,
        "rule": (
            "EXACT_OWNER_TABLE_DIRECT_CENTRAL_BANK_LOAN_CHILD_ROWS_WITH_OMITTED_"
            "STRUCTURAL_CARRIER_PATH_ONLY_NO_VALUE_CHANGE"
        ),
        "source_logical_name": region["source_logical_name"],
        "source_sha256": region["source_sha256"],
    }
    receipt = {
        **material,
        "direct_root_child_projection_receipt_id": (
            "gjslfdrcprv1:receipt:" + canonical_json_sha256_v1(material)
        ),
    }
    pages = {
        page_json_version_id: canonical_clone_v1(page_json)
        for page_json_version_id, page_json in page_json_by_version.items()
    }
    projected_table = _region_table(pages, region)
    for repair in repairs:
        projected_table["rows"][repair["row_ordinal"] - 1]["hierarchy_path_exact"] = (
            canonical_clone_v1(repair["after_hierarchy_path_exact"])
        )
    return pages, receipt


def _restore_direct_root_child_source_refs_v1(
    candidate: dict[str, Any],
    *,
    receipt: Mapping[str, Any],
    original_region: Mapping[str, Any],
    original_query_receipt: Mapping[str, Any],
) -> None:
    by_row = {repair["row_ordinal"]: repair for repair in receipt["repairs"]}
    for mapping in candidate.get("mappings", []):
        for source_ref in mapping.get("source_refs", []):
            repair = by_row.get(source_ref.get("row_ordinal"))
            if repair is None:
                continue
            if source_ref.get("hierarchy_path_exact") != repair[
                "after_hierarchy_path_exact"
            ]:
                raise _error("Government/SBV direct-root projection source drifted")
            source_ref["hierarchy_path_exact"] = canonical_clone_v1(
                repair["before_hierarchy_path_exact"]
            )
            source_ref["locator"]["component_roles"] = canonical_clone_v1(
                original_region["component_roles"]
            )
    candidate["component_regions"] = [canonical_clone_v1(original_region)]
    candidate["closure_receipt"]["query_receipt"] = canonical_clone_v1(
        original_query_receipt
    )


def adapt_gemini_json_government_sbv_liabilities_indexed_query_evidence_v1(
    value: Any,
    *,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Add exact adjacent fragments or exact primary root-only recoveries."""

    evidence = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        value, compiled_specs=compiled_specs
    )
    clusters = []
    receipts = []
    for disposition in evidence["candidate_dispositions"]:
        cluster = canonical_clone_v1(disposition["cluster"])
        ordinal = cluster["document_ordinal"]
        pages = page_json_by_document.get(ordinal)
        recovered = None
        recovery_kind = None
        if (
            type(pages) is dict
            and cluster.get("reasons") == ["COMPLETE_OWNER_CLUSTER_NOT_RESOLVED"]
        ):
            recovered = _adjacent_owner_continuation_receipt_v1(
                cluster=cluster,
                selected_page_axis=evidence["selected_page_axis"],
                page_json_by_version=pages,
                compiled_specs=compiled_specs,
                document_unit_context=_document_unit_context_axis(
                    pages, compiled_specs=compiled_specs
                ),
            )
            recovery_kind = "ADJACENT" if recovered is not None else None
        elif type(pages) is dict and not cluster.get("reasons"):
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
                locator = (
                    item.get("page_json_version_id"),
                    item.get("section_id"),
                    item.get("table_id"),
                )
                if locator == (
                    region["page_json_version_id"],
                    region["section_id"],
                    region["table_id"],
                ):
                    item["disposition"] = (
                        "SELECTED_FAMILY_COMPONENT_AFTER_EXACT_ADJACENT_OWNER_RECEIPT"
                        if recovery_kind == "ADJACENT"
                        else "SELECTED_PRIMARY_STATEMENT_EXACT_FAMILY_ROOT_AFTER_ADAPTER_RECEIPT"
                    )
            cluster["component_regions"] = [region]
            if recovery_kind == "ADJACENT":
                cluster["owner_receipt"] = {
                    "adjacent_query_receipt_id": receipt["adjacent_query_receipt_id"],
                    "alias": receipt["owner_alias"],
                    "leading_component_positions": [],
                    "leading_component_rule": (
                        "EXACT_PAGE_FINAL_OWNER_NEXT_PAGE_LEADING_CONTINUATION"
                    ),
                    "position": [
                        receipt["owner_locator"]["physical_page"],
                        int(receipt["owner_locator"]["section_id"][1:]),
                        int(receipt["owner_locator"]["table_id"][1:]),
                    ],
                    "source_exact": receipt["owner_source_exact"],
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
    page_json_by_version: Mapping[str, dict[str, Any]], region: Mapping[str, Any]
) -> dict[str, Any]:
    page = page_json_by_version.get(region.get("page_json_version_id"))
    try:
        section_index = int(region["section_id"][1:]) - 1
        table_index = int(region["table_id"][1:]) - 1
        section = page["sections"][section_index]  # type: ignore[index]
        table = section["tables"][table_index]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise _error("Government/SBV region does not resolve one selected source table") from exc
    if type(table) is not dict:
        raise _error("Government/SBV selected source table is invalid")
    return table


def _apply_authenticated_source_repairs(
    *,
    regions: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    pages = {
        page_json_version_id: canonical_clone_v1(page_json)
        for page_json_version_id, page_json in page_json_by_version.items()
    }
    if not regions:
        return pages, []
    identity = {
        (region.get("source_logical_name"), region.get("source_sha256"))
        for region in regions
    }
    if len(identity) != 1:
        raise _error("Government/SBV repair candidate source identity is ambiguous")
    source_logical_name, source_sha256 = next(iter(identity))
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
        for repair in compiled_specs.get("government_sbv_liabilities_source_repairs", [])
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
            raise _error("Government/SBV repair logical source identity drifted")
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
            raise _error("Government/SBV repair is outside its selected component table")
        page = pages.get(locator["page_json_version_id"])
        if page is None:
            raise _error("Government/SBV repair page is outside the selected document")
        table = _region_table(pages, matching_regions[0])
        rows = table.get("rows")
        if type(rows) is not list or locator["row_ordinal"] > len(rows):
            raise _error("Government/SBV repair row is outside its selected table")
        row = rows[locator["row_ordinal"] - 1]
        values = row.get("values_exact") if type(row) is dict else None
        if (
            type(values) is not list
            or locator["column_ordinal"] > len(values)
            or values[locator["column_ordinal"] - 1] is not repair["before_exact"]
        ):
            raise _error("Government/SBV repair cell before-image drifted")
        values[locator["column_ordinal"] - 1] = repair["after_exact"]
    return pages, applicable


def _money_ordinals(table: Mapping[str, Any]) -> list[int]:
    columns = table.get("columns")
    if type(columns) is not list:
        return []
    return [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]


def _coefficient(source_text: Any) -> int | None:
    if source_text is None:
        return None
    try:
        return _money(source_text)["coefficient"]
    except (TypeError, ValueError):
        return None


def _owner_total_axis(candidate: Mapping[str, Any]) -> dict[tuple[int, ...], list[dict[str, Any]]]:
    context = candidate.get("closure_receipt", {}).get("document_unit_context", {})
    evidence = context.get("owner_row_evidence") if type(context) is dict else None
    result: dict[tuple[int, ...], list[dict[str, Any]]] = {}
    for item in evidence if type(evidence) is list else []:
        coefficients = item.get("coefficients") if type(item) is dict else None
        if (
            type(coefficients) is list
            and coefficients
            and all(type(value) is int for value in coefficients)
            and item.get("period_axis_complete") is True
            and item.get("canonical_unit") in {"MILLION_VND", "VND"}
        ):
            result.setdefault(tuple(coefficients), []).append(canonical_clone_v1(item))
    return result


def _prepare_dash_overlay(
    *,
    raw_candidate: Mapping[str, Any],
    regions: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any] | None]:
    """Build one private overlay; return none unless its total has one owner proof."""

    # Retain the authenticated selected-page insertion order.  The shared
    # document context uses physical adjacency for a unit carried from the
    # immediately preceding primary-statement page.
    pages = {
        page_json_version_id: canonical_clone_v1(page_json)
        for page_json_version_id, page_json in page_json_by_version.items()
    }
    artefact_repairs: list[dict[str, Any]] = []
    continuation_header_repairs: list[dict[str, Any]] = []
    owner_unit_repairs: list[dict[str, Any]] = []
    total_cells: list[list[Any]] = []
    region_keys = set()
    for region in regions:
        key = (
            region.get("page_json_version_id"),
            region.get("section_id"),
            region.get("table_id"),
        )
        if key in region_keys:
            raise _error("Government/SBV overlay region axis is duplicate")
        region_keys.add(key)
        table = _region_table(pages, region)
        money_ordinals = _money_ordinals(table)
        if len(money_ordinals) != 2:
            continue
        rows = table.get("rows")
        if type(rows) is not list:
            continue
        for row_ordinal, row in enumerate(rows, start=1):
            if type(row) is not dict or type(row.get("values_exact")) is not list:
                continue
            values = row["values_exact"]
            if any(ordinal > len(values) for ordinal in money_ordinals):
                continue
            for column_ordinal in money_ordinals:
                source = values[column_ordinal - 1]
                if source in _VISIBLE_DASH_TRANSCRIPTION_ARTEFACTS:
                    artefact_repairs.append(
                        {
                            "after_source_text": "-",
                            "before_source_text": source,
                            "column_ordinal": column_ordinal,
                            "locator": {
                                "page_json_version_id": region["page_json_version_id"],
                                "physical_page": region["physical_page"],
                                "section_id": region["section_id"],
                                "table_id": region["table_id"],
                            },
                            "row_ordinal": row_ordinal,
                        }
                    )
                    values[column_ordinal - 1] = "-"
            if row.get("row_kind") == "TOTAL":
                total_cells.append([values[ordinal - 1] for ordinal in money_ordinals])

    if len(total_cells) != 1:
        return pages, None
    repaired_total = [_coefficient(source) for source in total_cells[0]]
    if any(value is None for value in repaired_total):
        return pages, None
    owner_axis = _owner_total_axis(raw_candidate)
    owner_evidence = owner_axis.get(tuple(repaired_total))
    if not owner_evidence:
        return pages, None
    owner_units = {item.get("canonical_unit") for item in owner_evidence}
    if len(owner_units) != 1:
        return pages, None
    owner_unit = next(iter(owner_units))
    owner_unit_source = next(
        (
            item.get("source_exact")
            for item in owner_evidence
            if type(item.get("source_exact")) is str
            and item["source_exact"].strip()
        ),
        None,
    )

    # A continuation page can omit its repeated column headings in the PDF.
    # Carry them only from the immediately preceding authenticated component
    # when the shared classifier proved that predecessor's two-period lane and
    # both fragments have the same resolved unit.  Query coalescing already
    # proves that both tables are inside one owner/reset fence.
    table_receipts = raw_candidate.get("closure_receipt", {}).get("table_receipts", [])
    receipt_by_locator = {
        (
            receipt["region"]["page_json_version_id"],
            receipt["region"]["section_id"],
            receipt["region"]["table_id"],
        ): receipt
        for receipt in table_receipts
        if type(receipt) is dict
        and type(receipt.get("region")) is dict
        and type(receipt.get("lane_axis")) is dict
        and type(receipt.get("unit_axis")) is dict
    }
    # The detail note may omit its unit while the exact matching owner row on
    # a primary statement carries it.  This is intentionally narrower than a
    # document-wide majority: the two owner coefficients must equal the one
    # visible detail total above, and the unit text copied here is itself an
    # immutable source string.
    resolved_unit_by_locator: dict[tuple[Any, Any, Any], Any] = {}
    for region in regions:
        key = (
            region.get("page_json_version_id"),
            region.get("section_id"),
            region.get("table_id"),
        )
        receipt = receipt_by_locator.get(key)
        if receipt is None:
            continue
        table = _region_table(pages, region)
        unit_axis = receipt["unit_axis"]
        if unit_axis.get("complete") is True:
            resolved_unit_by_locator[key] = unit_axis.get("canonical_unit")
        elif (
            owner_unit_source is not None
            and owner_unit in {"MILLION_VND", "VND"}
            and (table.get("unit_exact") is None or table.get("unit_exact") == "")
        ):
            table["unit_exact"] = owner_unit_source
            resolved_unit_by_locator[key] = owner_unit
            owner_unit_repairs.append(
                {
                    "after_unit_exact": owner_unit_source,
                    "before_unit_exact": None,
                    "canonical_unit": owner_unit,
                    "locator": {
                        "page_json_version_id": region["page_json_version_id"],
                        "physical_page": region["physical_page"],
                        "section_id": region["section_id"],
                        "table_id": region["table_id"],
                    },
                    "source_owner_locator": {
                        "page_json_version_id": owner_evidence[0]["page_json_version_id"],
                        "row_ordinal": owner_evidence[0]["row_ordinal"],
                        "section_id": owner_evidence[0]["section_id"],
                        "table_id": owner_evidence[0]["table_id"],
                    },
                }
            )

    carrier: tuple[Mapping[str, Any], dict[str, Any], dict[str, Any]] | None = None
    first_region = regions[0]
    first_key = (
        first_region.get("page_json_version_id"),
        first_region.get("section_id"),
        first_region.get("table_id"),
    )
    first_receipt = receipt_by_locator.get(first_key)
    page_ids = list(pages)
    try:
        first_page_index = page_ids.index(first_region.get("page_json_version_id"))
    except ValueError:
        first_page_index = -1
    if (
        first_receipt is not None
        and first_receipt["lane_axis"].get("complete") is not True
        and first_page_index > 0
    ):
        prior_page_id = page_ids[first_page_index - 1]
        prior_page = pages[prior_page_id]
        external_carriers = []
        for section_ordinal, section in enumerate(prior_page.get("sections", []), start=1):
            if type(section) is not dict or type(section.get("tables")) is not list:
                continue
            for table_ordinal, table in enumerate(section["tables"], start=1):
                if type(table) is not dict:
                    continue
                folded_surfaces = [
                    _without_leading_ordinal(_normalized(surface))
                    for surface in (section.get("title_exact"), table.get("title_exact"))
                ]
                if not any(
                    _matches(folded, alias)
                    for folded in folded_surfaces
                    for alias in compiled_specs["query_policy"]["owner_aliases"]
                ):
                    continue
                carrier_table = canonical_clone_v1(table)
                carrier_columns = carrier_table.get("columns")
                if type(carrier_columns) is not list or len(carrier_columns) != 2:
                    continue
                for column in carrier_columns:
                    if type(column) is not dict:
                        break
                    column["value_kind"] = "MONEY"
                else:
                    period_axis = _two_period_axis(carrier_table)
                    if period_axis.get("complete") is True:
                        carrier_region = {
                            "page_json_version_id": prior_page_id,
                            "physical_page": first_region["physical_page"] - 1,
                            "section_id": f"s{section_ordinal}",
                            "table_id": f"t{table_ordinal}",
                        }
                        external_carriers.append(
                            (
                                carrier_region,
                                carrier_table,
                                {
                                    "lane_axis": period_axis,
                                    "unit_axis": {"canonical_unit": owner_unit},
                                },
                            )
                        )
                continue
        if len(external_carriers) == 1:
            carrier = external_carriers[0]
            resolved_unit_by_locator[
                (
                    carrier[0]["page_json_version_id"],
                    carrier[0]["section_id"],
                    carrier[0]["table_id"],
                )
            ] = owner_unit
    for region in regions:
        key = (
            region.get("page_json_version_id"),
            region.get("section_id"),
            region.get("table_id"),
        )
        receipt = receipt_by_locator.get(key)
        table = _region_table(pages, region)
        money_ordinals = _money_ordinals(table)
        if receipt is None or len(money_ordinals) != 2:
            carrier = None
            continue
        lane_axis = receipt["lane_axis"]
        unit_axis = receipt["unit_axis"]
        if lane_axis.get("complete") is True:
            carrier = (region, table, receipt)
            continue
        columns = table.get("columns")
        header_paths = (
            [columns[ordinal - 1].get("header_path_exact") for ordinal in money_ordinals]
            if type(columns) is list
            and all(type(columns[ordinal - 1]) is dict for ordinal in money_ordinals)
            else []
        )
        if (
            carrier is None
            or region.get("physical_page") != carrier[0].get("physical_page") + 1
            or key not in resolved_unit_by_locator
            or resolved_unit_by_locator[key]
            != resolved_unit_by_locator.get(
                (
                    carrier[0].get("page_json_version_id"),
                    carrier[0].get("section_id"),
                    carrier[0].get("table_id"),
                )
            )
            or len(header_paths) != 2
            or any(
                type(path) is not list
                or any(value not in {None, ""} for value in path)
                for path in header_paths
            )
        ):
            carrier = None
            continue
        carrier_columns = carrier[1].get("columns")
        carrier_ordinals = _money_ordinals(carrier[1])
        if type(carrier_columns) is not list or len(carrier_ordinals) != 2:
            carrier = None
            continue
        after_paths = [
            canonical_clone_v1(carrier_columns[ordinal - 1].get("header_path_exact"))
            for ordinal in carrier_ordinals
        ]
        if any(
            type(path) is not list
            or not any(type(value) is str and value.strip() for value in path)
            for path in after_paths
        ):
            carrier = None
            continue
        for column_ordinal, before, after in zip(
            money_ordinals, header_paths, after_paths, strict=True
        ):
            columns[column_ordinal - 1]["header_path_exact"] = canonical_clone_v1(after)
            continuation_header_repairs.append(
                {
                    "after_header_path_exact": after,
                    "before_header_path_exact": canonical_clone_v1(before),
                    "column_ordinal": column_ordinal,
                    "locator": {
                        "page_json_version_id": region["page_json_version_id"],
                        "physical_page": region["physical_page"],
                        "section_id": region["section_id"],
                        "table_id": region["table_id"],
                    },
                    "source_locator": {
                        "page_json_version_id": carrier[0]["page_json_version_id"],
                        "physical_page": carrier[0]["physical_page"],
                        "section_id": carrier[0]["section_id"],
                        "table_id": carrier[0]["table_id"],
                    },
                }
            )
        carrier = (region, table, receipt)

    repairs = [
        *artefact_repairs,
        *continuation_header_repairs,
        *owner_unit_repairs,
    ]
    if not repairs:
        return pages, None
    material = {
        "adapter_format_version": ADAPTER_FORMAT_VERSION,
        "immutable_selected_json_changed": False,
        "owner_total_evidence": owner_evidence,
        "owner_total_evidence_axis_sha256": canonical_json_sha256_v1(owner_evidence),
        "repaired_total_coefficients": repaired_total,
        "repairs": repairs,
        "rule": (
            "EXACT_VISIBLE_DASH_TRANSCRIPTION_ARTEFACT_OR_ADJACENT_"
            "CONTINUATION_HEADER_ONLY_AFTER_SAME_DOCUMENT_UNIT_BEARING_"
            "PRIMARY_OWNER_TOTAL_EXACT"
        ),
    }
    return pages, {
        **material,
        "overlay_receipt_id": "gjslfav1:overlay:" + canonical_json_sha256_v1(material),
    }


def _mapping_units(candidate: Mapping[str, Any]) -> dict[tuple[str, str, str], str]:
    result: dict[tuple[str, str, str], str] = {}
    receipts = candidate.get("closure_receipt", {}).get("table_receipts", [])
    for receipt in receipts if type(receipts) is list else []:
        region = receipt.get("region") if type(receipt) is dict else None
        unit_axis = receipt.get("unit_axis") if type(receipt) is dict else None
        if type(region) is not dict or type(unit_axis) is not dict:
            continue
        unit = unit_axis.get("canonical_unit")
        key = (
            region.get("page_json_version_id"),
            region.get("section_id"),
            region.get("table_id"),
        )
        if unit not in {"MILLION_VND", "VND"} or any(type(item) is not str for item in key):
            continue
        prior = result.setdefault(key, unit)
        if prior != unit:
            raise _error("Government/SBV one source table has conflicting adapter units")
    return result


def _drop_unauthenticated_null_derived_mappings(
    candidate: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Never expose a schema value produced by interpreting null as zero."""

    if candidate.get("status") != READY:
        return candidate, []
    mappings = candidate.get("mappings")
    if type(mappings) is not list:
        raise _error("Government/SBV candidate mapping axis is invalid")
    retained = []
    omissions = []
    for mapping in mappings:
        values = mapping.get("values") if type(mapping) is dict else None
        null_derived_lanes = [
            lane
            for lane, value in enumerate(values if type(values) is list else [], start=1)
            if type(value) is dict
            and value.get("source_text") is None
            and (
                "BLANK_ZERO" in str(value.get("state", ""))
                or str(value.get("state", "")).startswith("INFERRED_BLANK")
            )
        ]
        if not null_derived_lanes:
            retained.append(mapping)
            continue
        omissions.append(
            {
                "null_derived_lanes": null_derived_lanes,
                "report_norm_id": mapping.get("report_norm_id"),
                "role": mapping.get("role"),
                "rule": "NULL_SOURCE_CELL_IS_NOT_ZERO_WITHOUT_AUTHENTICATED_PDF_GLYPH",
                "source_refs": canonical_clone_v1(mapping.get("source_refs", [])),
                "states": [value.get("state") for value in values],
            }
        )
    candidate["mappings"] = retained
    if not retained:
        candidate["status"] = "UNRESOLVED_GEMINI_JSON_FAMILY"
        candidate["reasons"] = sorted(
            {
                *candidate.get("reasons", []),
                "NULL_DERIVED_MAPPING_FRONTIER_NOT_AUTHENTICATED",
            }
        )
    return candidate, omissions


def _overlay_mapping_value_corrections(
    candidate: dict[str, Any],
    *,
    overlay_receipt: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Repair zeroed structural carriers, then prove the visible root total."""

    mappings = candidate.get("mappings")
    if type(mappings) is not list:
        raise _error("Government/SBV adapter mapping axis is invalid")
    mapping_by_role: dict[str, dict[str, Any]] = {}
    for mapping in mappings:
        role = mapping.get("role") if type(mapping) is dict else None
        if type(role) is not str or role in mapping_by_role:
            raise _error("Government/SBV adapter mapping role axis is not unique")
        mapping_by_role[role] = mapping

    def coefficients(mapping: Mapping[str, Any]) -> list[int]:
        values = mapping.get("values")
        result = [item.get("coefficient") for item in values] if type(values) is list else []
        if len(result) != 2 or any(type(value) is not int for value in result):
            raise _error("Government/SBV adapter mapping coefficient axis is invalid")
        return result

    def source_refs(roles: Sequence[str]) -> list[dict[str, Any]]:
        return [
            canonical_clone_v1(source_ref)
            for role in roles
            for source_ref in mapping_by_role[role].get("source_refs", [])
        ]

    corrections: list[dict[str, Any]] = []
    child_by_role = compiled_specs.get("child_by_role")
    if type(child_by_role) is not dict:
        raise _error("Government/SBV compiled child axis is absent")
    for parent_role, parent in child_by_role.items():
        if parent.get("role_kind") != "STRUCTURAL_GROUP":
            continue
        component_roles = [
            role
            for role in compiled_specs.get("output_role_order", [])
            if role in mapping_by_role
            and any(
                matcher.get("within_role") == parent_role
                for matcher in child_by_role[role].get("matchers", [])
            )
        ]
        if not component_roles:
            continue
        after = [
            sum(coefficients(mapping_by_role[role])[lane] for role in component_roles)
            for lane in range(2)
        ]
        if parent_role not in mapping_by_role:
            component_units = {mapping_by_role[role].get("unit") for role in component_roles}
            if len(component_units) != 1:
                raise _error("Government/SBV structural child units disagree")
            parent_mapping = {
                "item_mapping_id": "",
                "report_norm_id": compiled_specs["bindings"][parent_role],
                "role": parent_role,
                "row_id": f"adapter-derived:{parent_role}",
                "source_refs": source_refs(component_roles),
                "state": "ADAPTER_DERIVED_EXACT_SUM_OF_COMPONENT_ROLES",
                "unit": next(iter(component_units)),
                "values": [
                    {
                        "coefficient": value,
                        "source_text": None,
                        "state": "DERIVED_EXACT_SUM_OF_ADAPTER_COMPONENT_ROLES",
                    }
                    for value in after
                ],
            }
            mappings.append(parent_mapping)
            mapping_by_role[parent_role] = parent_mapping
            corrections.append(
                {
                    "after_coefficients": after,
                    "before_coefficients": None,
                    "component_roles": component_roles,
                    "role": parent_role,
                    "rule": "ABSENT_STRUCTURAL_CARRIER_DERIVED_FROM_EXACT_CHILD_SUM",
                }
            )
            continue
        parent_mapping = mapping_by_role[parent_role]
        before = coefficients(parent_mapping)
        if before == after:
            continue
        if any(before):
            raise _error("Government/SBV visible structural carrier conflicts with its children")
        corrections.append(
            {
                "after_coefficients": after,
                "before_coefficients": before,
                "component_roles": component_roles,
                "role": parent_role,
                "rule": "ZERO_STRUCTURAL_CARRIER_REPLACED_BY_EXACT_CHILD_SUM",
            }
        )
        parent_mapping["row_id"] = f"adapter-derived:{parent_role}"
        parent_mapping["source_refs"] = source_refs(component_roles)
        parent_mapping["state"] = "ADAPTER_DERIVED_EXACT_SUM_OF_COMPONENT_ROLES"
        parent_mapping["values"] = [
            {
                "coefficient": value,
                "source_text": None,
                "state": "DERIVED_EXACT_SUM_OF_ADAPTER_COMPONENT_ROLES",
            }
            for value in after
        ]

    root_roles = [
        role
        for role in compiled_specs.get("root_component_roles", [])
        if role in mapping_by_role
    ]
    if not root_roles:
        raise _error("Government/SBV overlay cannot prove one family-root mapping")
    root_after = [
        sum(coefficients(mapping_by_role[role])[lane] for role in root_roles)
        for lane in range(2)
    ]
    visible_total = overlay_receipt.get("repaired_total_coefficients")
    if root_after != visible_total:
        raise _error("Government/SBV repaired root does not equal the visible terminal total")
    root = mapping_by_role.get("FAMILY_ROOT_TOTAL")
    if root is None:
        root_units = {mapping_by_role[role].get("unit") for role in root_roles}
        if len(root_units) != 1:
            raise _error("Government/SBV root-component units disagree")
        root = {
            "item_mapping_id": "",
            "report_norm_id": compiled_specs["schema"]["family_root_report_norm_id"],
            "role": "FAMILY_ROOT_TOTAL",
            "row_id": "adapter-derived:FAMILY_ROOT_TOTAL",
            "source_refs": source_refs(root_roles),
            "state": "ADAPTER_DERIVED_ROOT_EXACT_VISIBLE_TERMINAL_AND_OWNER_TOTAL",
            "unit": next(iter(root_units)),
            "values": [
                {
                    "coefficient": value,
                    "source_text": None,
                    "state": "DERIVED_EXACT_ROOT_COMPONENT_SUM",
                }
                for value in root_after
            ],
        }
        mappings.append(root)
        mapping_by_role["FAMILY_ROOT_TOTAL"] = root
        corrections.append(
            {
                "after_coefficients": root_after,
                "before_coefficients": None,
                "component_roles": root_roles,
                "role": "FAMILY_ROOT_TOTAL",
                "rule": "ABSENT_ROOT_DERIVED_FROM_EXACT_COMPONENT_SUM_EQUALS_VISIBLE_TERMINAL_AND_OWNER_TOTAL",
            }
        )
    else:
        root_before = coefficients(root)
        if root_before == root_after:
            pass
        elif any(root_before):
            raise _error("Government/SBV generic root conflicts with the repaired root")
        else:
            corrections.append(
                {
                    "after_coefficients": root_after,
                    "before_coefficients": root_before,
                    "component_roles": root_roles,
                    "role": "FAMILY_ROOT_TOTAL",
                    "rule": "EXACT_ROOT_COMPONENT_SUM_EQUALS_VISIBLE_TERMINAL_AND_OWNER_TOTAL",
                }
            )
            root["row_id"] = "adapter-derived:FAMILY_ROOT_TOTAL"
            root["source_refs"] = source_refs(root_roles)
            root["state"] = "ADAPTER_DERIVED_ROOT_EXACT_VISIBLE_TERMINAL_AND_OWNER_TOTAL"
            root["values"] = [
                {
                    "coefficient": value,
                    "source_text": None,
                    "state": "DERIVED_EXACT_ROOT_COMPONENT_SUM",
                }
                for value in root_after
            ]
    role_order = [*compiled_specs.get("output_role_order", []), "FAMILY_ROOT_TOTAL"]
    mappings.sort(key=lambda mapping: role_order.index(mapping["role"]))
    return corrections


def _reseal_candidate(
    candidate: dict[str, Any],
    *,
    overlay_receipt: dict[str, Any] | None,
    authenticated_source_repairs: Sequence[Mapping[str, Any]],
    null_derived_mapping_omissions: Sequence[Mapping[str, Any]],
    primary_root_projection_receipt: Mapping[str, Any] | None,
    direct_root_child_projection_receipt: Mapping[str, Any] | None,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    mapping_value_corrections = (
        _overlay_mapping_value_corrections(
            candidate,
            overlay_receipt=overlay_receipt,
            compiled_specs=compiled_specs,
        )
        if overlay_receipt is not None and candidate.get("status") == READY
        else []
    )
    unit_by_locator = (
        _mapping_units(candidate) if candidate.get("status") == READY else {}
    )
    unit_corrections = []
    state_corrections = []
    for mapping in candidate.get("mappings", []):
        units = set()
        for source_ref in mapping.get("source_refs", []):
            locator = source_ref.get("locator") if type(source_ref) is dict else None
            if type(locator) is not dict:
                continue
            key = (
                locator.get("page_json_version_id"),
                locator.get("section_id"),
                locator.get("table_id"),
            )
            if key in unit_by_locator:
                units.add(unit_by_locator[key])
        if len(units) != 1:
            raise _error("Government/SBV mapping source unit is absent or ambiguous")
        source_unit = next(iter(units))
        before = mapping.get("unit")
        if before != source_unit:
            unit_corrections.append(
                {
                    "after_unit": source_unit,
                    "before_unit": before,
                    "report_norm_id": mapping.get("report_norm_id"),
                    "role": mapping.get("role"),
                }
            )
            mapping["unit"] = source_unit
        for lane, value in enumerate(mapping.get("values", []), start=1):
            state = value.get("state") if type(value) is dict else None
            if (
                type(value) is dict
                and type(value.get("coefficient")) is int
                and value.get("source_text") is None
                and type(state) is str
                and state.startswith("EXACT_")
                and "BLANK" not in state
            ):
                after_state = "DERIVED_" + state
                state_corrections.append(
                    {
                        "after_state": after_state,
                        "before_state": state,
                        "lane": lane,
                        "report_norm_id": mapping.get("report_norm_id"),
                        "role": mapping.get("role"),
                    }
                )
                value["state"] = after_state
        mapping_material = {key: mapping[key] for key in mapping if key != "item_mapping_id"}
        mapping["item_mapping_id"] = (
            "gjmthfmv1:item:" + canonical_json_sha256_v1(mapping_material)
        )
    if (
        overlay_receipt is None
        and primary_root_projection_receipt is None
        and direct_root_child_projection_receipt is None
        and not authenticated_source_repairs
        and not null_derived_mapping_omissions
        and not state_corrections
        and not unit_corrections
    ):
        return candidate
    adapter_material = {
        "adapter_format_version": ADAPTER_FORMAT_VERSION,
        "authenticated_source_repairs": canonical_clone_v1(
            list(authenticated_source_repairs)
        ),
        "mapping_value_corrections": mapping_value_corrections,
        "mapping_unit_corrections": unit_corrections,
        "mapping_state_corrections": state_corrections,
        "null_derived_mapping_omissions": canonical_clone_v1(
            list(null_derived_mapping_omissions)
        ),
        "overlay_receipt": canonical_clone_v1(overlay_receipt),
        "primary_root_projection_receipt": canonical_clone_v1(
            primary_root_projection_receipt
        ),
        "direct_root_child_projection_receipt": canonical_clone_v1(
            direct_root_child_projection_receipt
        ),
        "shared_engine_claim_boundary": GENERIC_CLAIM_BOUNDARY,
    }
    candidate["claim_boundary"] = ADAPTER_CLAIM_BOUNDARY
    candidate["closure_receipt"]["government_sbv_liabilities_adapter_receipt"] = {
        **adapter_material,
        "adapter_receipt_id": (
            "gjslfav1:receipt:" + canonical_json_sha256_v1(adapter_material)
        ),
    }
    candidate_material = {key: candidate[key] for key in candidate if key != "candidate_id"}
    candidate["candidate_id"] = (
        "gjmthfcv1:candidate:" + canonical_json_sha256_v1(candidate_material)
    )
    return candidate


def evaluate_gemini_json_government_sbv_liabilities_family_cluster_v1(
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate Family 23 and apply only independently proved source overlays."""

    if compiled_specs.get("topology", {}).get("family_id") != FAMILY_ID:
        raise _error("Government/SBV adapter received another family")
    if type(regions) not in {list, tuple} or not regions:
        return evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
            regions=regions,
            page_json_by_version=page_json_by_version,
            compiled_specs=compiled_specs,
            query_receipt=query_receipt,
        )
    source_pages, authenticated_source_repairs = _apply_authenticated_source_repairs(
        regions=regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
    )
    primary_projection = None
    if len(regions) == 1:
        identified_projection = _primary_statement_exact_root_projection_v1(
            region=regions[0],
            page_json_by_version=page_json_by_version,
            compiled_specs=compiled_specs,
        )
        if identified_projection is not None:
            _unused_pages, primary_projection = identified_projection
    if primary_projection is not None:
        projected_pages = _apply_primary_root_projection_receipt_v1(
            page_json_by_version=source_pages,
            receipt=primary_projection,
        )
        projected = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
            regions=regions,
            page_json_by_version=projected_pages,
            compiled_specs=compiled_specs,
            query_receipt=query_receipt,
        )
        if projected.get("status") == READY:
            _restore_primary_root_mapping_source_refs_v1(
                projected, receipt=primary_projection
            )
            projected, omissions = _drop_unauthenticated_null_derived_mappings(
                projected
            )
        else:
            omissions = []
        return _reseal_candidate(
            projected,
            overlay_receipt=None,
            authenticated_source_repairs=authenticated_source_repairs,
            null_derived_mapping_omissions=omissions,
            primary_root_projection_receipt=primary_projection,
            direct_root_child_projection_receipt=None,
            compiled_specs=compiled_specs,
        )
    direct_root_projection = None
    if len(regions) == 1:
        direct_root_projection = _direct_root_central_child_projection_v1(
            region=regions[0],
            page_json_by_version=source_pages,
            compiled_specs=compiled_specs,
        )
    if direct_root_projection is not None:
        projected_pages, projection_receipt = direct_root_projection
        projected_region = canonical_clone_v1(regions[0])
        projected_region["component_roles"] = canonical_clone_v1(
            projection_receipt["region_component_roles"]["after"]
        )
        projected_regions = [projected_region]
        projected = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
            regions=projected_regions,
            page_json_by_version=projected_pages,
            compiled_specs=compiled_specs,
            query_receipt=(
                build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
                    projected_regions
                )
            ),
        )
        if projected.get("status") == READY:
            _restore_direct_root_child_source_refs_v1(
                projected,
                receipt=projection_receipt,
                original_region=regions[0],
                original_query_receipt=query_receipt,
            )
            projected, omissions = _drop_unauthenticated_null_derived_mappings(
                projected
            )
        else:
            omissions = []
        return _reseal_candidate(
            projected,
            overlay_receipt=None,
            authenticated_source_repairs=authenticated_source_repairs,
            null_derived_mapping_omissions=omissions,
            primary_root_projection_receipt=None,
            direct_root_child_projection_receipt=projection_receipt,
            compiled_specs=compiled_specs,
        )
    raw = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=regions,
        page_json_by_version=source_pages,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if raw.get("status") == READY:
        filtered, omissions = _drop_unauthenticated_null_derived_mappings(
            canonical_clone_v1(raw)
        )
        return _reseal_candidate(
            filtered,
            overlay_receipt=None,
            authenticated_source_repairs=authenticated_source_repairs,
            null_derived_mapping_omissions=omissions,
            primary_root_projection_receipt=None,
            direct_root_child_projection_receipt=None,
            compiled_specs=compiled_specs,
        )
    pages, overlay_receipt = _prepare_dash_overlay(
        raw_candidate=raw,
        regions=regions,
        page_json_by_version=source_pages,
        compiled_specs=compiled_specs,
    )
    if overlay_receipt is None:
        return _reseal_candidate(
            canonical_clone_v1(raw),
            overlay_receipt=None,
            authenticated_source_repairs=authenticated_source_repairs,
            null_derived_mapping_omissions=[],
            primary_root_projection_receipt=None,
            direct_root_child_projection_receipt=None,
            compiled_specs=compiled_specs,
        )
    repaired = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=regions,
        page_json_by_version=pages,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if repaired.get("status") != READY:
        return _reseal_candidate(
            canonical_clone_v1(raw),
            overlay_receipt=None,
            authenticated_source_repairs=authenticated_source_repairs,
            null_derived_mapping_omissions=[],
            primary_root_projection_receipt=None,
            direct_root_child_projection_receipt=None,
            compiled_specs=compiled_specs,
        )
    filtered, omissions = _drop_unauthenticated_null_derived_mappings(repaired)
    try:
        return _reseal_candidate(
            filtered,
            overlay_receipt=overlay_receipt,
            authenticated_source_repairs=authenticated_source_repairs,
            null_derived_mapping_omissions=omissions,
            primary_root_projection_receipt=None,
            direct_root_child_projection_receipt=None,
            compiled_specs=compiled_specs,
        )
    except GeminiJsonGovernmentSbvLiabilitiesFamilyV1Error:
        return raw


def validate_gemini_json_government_sbv_liabilities_family_candidate_replay_v1(
    value: Any,
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay the complete adapter path from immutable selected JSON."""

    expected = evaluate_gemini_json_government_sbv_liabilities_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if type(value) is not dict or not same_typed_json_v1(value, expected):
        raise _error("Government/SBV family adapter candidate replay drifted")
    return expected
