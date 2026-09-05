"""Fail-closed Family 40 adapter for cash and cash equivalents.

The shared multi-table evaluator remains authoritative for row classification,
period and unit resolution, exact source arithmetic, and schema bindings.  This
module owns three narrowly bounded Family-40 source presentations:

* one exact local owner table can be recovered when unrelated family-like
  populations elsewhere in the document make the generic owner fence
  conservative;
* the exact Vietnamese header pair ``Số cuối kỳ này`` / ``Số cuối kỳ trước``
  is projected to an unambiguous current/comparative pair and then restored in
  the receipt; and
* selected-JSON nulls may become an accounting dash only when an authenticated
  full-page/crop source-repair artifact binds the exact source and cell.

No value, equation, bank identity, or expected output participates in query
selection.  Unregistered blank cells remain blank and therefore unresolved.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

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
    READY,
    UNRESOLVED,
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

FAMILY_ID = "CASH_EQUIVALENTS"
ADAPTER_FORMAT_VERSION = "GEMINI_JSON_CASH_EQUIVALENTS_FAMILY_ADAPTER_V1"
LOCAL_OWNER_QUERY_RECEIPT_FORMAT_VERSION = (
    "GEMINI_JSON_CASH_EQUIVALENTS_LOCAL_OWNER_QUERY_RECEIPT_V1"
)
HEADER_PROJECTION_RECEIPT_FORMAT_VERSION = (
    "GEMINI_JSON_CASH_EQUIVALENTS_HEADER_PROJECTION_RECEIPT_V1"
)
PARTIAL_ROOT_OMISSION_RECEIPT_FORMAT_VERSION = (
    "GEMINI_JSON_CASH_EQUIVALENTS_PARTIAL_ROOT_OMISSION_RECEIPT_V1"
)
PRIMARY_SUPPLEMENTAL_QUERY_RECEIPT_FORMAT_VERSION = (
    "GEMINI_JSON_CASH_EQUIVALENTS_PRIMARY_SUPPLEMENTAL_QUERY_RECEIPT_V1"
)
PRIMARY_SUPPLEMENTAL_PROJECTION_RECEIPT_FORMAT_VERSION = (
    "GEMINI_JSON_CASH_EQUIVALENTS_PRIMARY_SUPPLEMENTAL_PROJECTION_RECEIPT_V1"
)
SOURCE_REPAIR_FORMAT_VERSION = (
    "GEMINI_JSON_CASH_EQUIVALENTS_AUTHENTICATED_SOURCE_REPAIR_SPEC_V1"
)
ADAPTER_CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_FAMILY40_GENERIC_OWNER_ROLE_PERIOD_UNIT_"
    "AND_ACCOUNTING_CLOSURE_WITH_VALUE_INDEPENDENT_EXACT_LOCAL_OWNER_RECOVERY_"
    "EXACT_AMBIGUOUS_VIETNAMESE_PERIOD_HEADER_PROJECTION_AND_AUTHENTICATED_PDF_"
    "VISIBLE_DASH_CELL_OVERLAY_PLUS_TYPED_PARTIAL_SOURCE_LANES_WITHOUT_ROOT_"
    "EQUATION_SCHEMA_MAPPING_PROPOSAL_ONLY_NO_SOURCE_MUTATION_OCR_PROVIDER_"
    "BANK_VALUE_ROUTING_BLANK_ZERO_BACKSOLVE_CANONICAL_OR_EXPORT_AUTHORITY"
)

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_PAGE_VERSION = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_SECTION_ID = re.compile(r"s[1-9][0-9]*\Z")
_TABLE_ID = re.compile(r"t[1-9][0-9]*\Z")
_RECOVERABLE_RAW_REASON_AXES = frozenset(
    {
        (),
        ("COMPLETE_OWNER_CLUSTER_NOT_RESOLVED",),
        ("MULTIPLE_COMPLETE_OWNER_CLUSTERS",),
        ("MULTIPLE_SOURCE_RESULT_POPULATIONS_INSIDE_OWNER_FENCE",),
    }
)
_AMBIGUOUS_PERIOD_HEADER_PAIR = (
    ("Số cuối kỳ này",),
    ("Số cuối kỳ trước",),
)
_PROJECTED_PERIOD_HEADER_PAIR = (("Kỳ này",), ("Kỳ trước",))
_PRIMARY_SUPPLEMENTAL_OWNER = _normalized(
    "Các khoản tiền tương đương tiền cuối kỳ bao gồm"
)


class GeminiJsonCashEquivalentsFamilyV1Error(ValueError):
    """Family-40 spec, source observation, candidate, or replay drifted."""


def _error(message: str) -> GeminiJsonCashEquivalentsFamilyV1Error:
    return GeminiJsonCashEquivalentsFamilyV1Error(message)


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
        raise _error("cash-equivalents authenticated source-repair spec is invalid")
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
            or _PAGE_VERSION.fullmatch(locator.get("page_json_version_id", ""))
            is None
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
            raise _error("cash-equivalents authenticated source repair is invalid")
        material = {
            key: canonical_clone_v1(item)
            for key, item in repair.items()
            if key != "repair_id"
        }
        expected_id = "gjcefav1:source-repair:" + canonical_json_sha256_v1(material)
        if repair.get("repair_id") != expected_id:
            raise _error("cash-equivalents source-repair identity drifted")
        identity = (
            source["source_sha256"],
            locator["page_json_version_id"],
            locator["section_id"],
            locator["table_id"],
            locator["row_ordinal"],
            locator["column_ordinal"],
        )
        if identity in identities:
            raise _error("cash-equivalents source-repair cell axis is duplicate")
        identities.add(identity)
        checked.append(canonical_clone_v1(repair))
    if value.get("repair_axis_sha256") != canonical_json_sha256_v1(checked):
        raise _error("cash-equivalents source-repair axis seal drifted")
    return checked


def bind_gemini_json_cash_equivalents_source_repairs_v1(
    compiled_specs: Any, source_repair_spec: Any
) -> dict[str, Any]:
    """Bind exact PDF cell observations to a generic Family-40 frontier."""

    if type(compiled_specs) is not dict:
        raise _error("cash-equivalents compiled family frontier is invalid")
    compiled = canonical_clone_v1(compiled_specs)
    if (
        compiled.get("topology", {}).get("family_id") != FAMILY_ID
        or compiled.get("evaluation", {}).get("family_id") != FAMILY_ID
        or compiled.get("schema", {}).get("family_id") != FAMILY_ID
        or set(compiled.get("bindings", {}))
        != {
            "CASH",
            "CENTRAL_BANK",
            "INTERBANK_GENERAL",
            "INTERBANK_DEMAND",
            "INTERBANK_TERM",
            "SECURITIES",
        }
        or {
            item["canonical_unit"]
            for item in compiled.get("unit_bindings", [])
            if item.get("accepted") is True
        }
        != {"MILLION_VND"}
    ):
        raise _error("cash-equivalents declarative family frontier is invalid")
    compiled["cash_equivalents_source_repairs"] = _validate_source_repairs(
        source_repair_spec
    )
    compiled["cash_equivalents_source_repair_spec_sha256"] = (
        canonical_json_sha256_v1(source_repair_spec)
    )
    compiled["cash_equivalents_adapter_format_version"] = ADAPTER_FORMAT_VERSION
    return compiled


def compile_gemini_json_cash_equivalents_family_specs_v1(
    topology_spec: Any,
    evaluation_spec: Any,
    schema_binding_spec: Any,
    source_repair_spec: Any,
) -> dict[str, Any]:
    """Compile the declarative family and exact source-repair artifact."""

    compiled = compile_gemini_json_flat_family_specs_v1(
        topology_spec, evaluation_spec, schema_binding_spec
    )
    return bind_gemini_json_cash_equivalents_source_repairs_v1(
        compiled, source_repair_spec
    )


def build_gemini_json_cash_equivalents_region_query_receipt_v1(
    regions: Any,
) -> dict[str, Any]:
    """Seal the unchanged generic query-region axis."""

    return build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)


def _table_from_inventory(
    *,
    inventory_item: Mapping[str, Any],
    page_json_by_version: Mapping[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None:
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
    return page, section, table


def _exact_alias(value: Any, aliases: Sequence[str]) -> str | None:
    folded = _without_leading_ordinal(_normalized(value))
    matches = [alias for alias in aliases if folded == alias]
    return matches[0] if len(matches) == 1 else None


def _surface_match(
    value: Any,
    *,
    aliases: Sequence[str],
) -> tuple[str, str] | None:
    """Match the whole surface, otherwise exactly one individual source line."""

    alias = _exact_alias(value, aliases)
    if alias is not None:
        return alias, value
    if type(value) is not str:
        return None
    line_matches = []
    for line in value.splitlines():
        if (line_alias := _exact_alias(line, aliases)) is not None:
            line_matches.append((line_alias, line))
    return line_matches[0] if len(line_matches) == 1 else None


def _local_owner_recovery_v1(
    *,
    cluster: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Recover one structurally complete exact-owner table without using values."""

    if (
        cluster.get("status") == READY
        or tuple(cluster.get("reasons") or []) not in _RECOVERABLE_RAW_REASON_AXES
    ):
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
    owner_aliases = compiled_specs.get("query_policy", {}).get("owner_aliases")
    reset_aliases = sorted(
        {
            *compiled_specs.get("query_policy", {}).get("reset_aliases", []),
            *compiled_specs.get("query_policy", {}).get("hard_negative_aliases", []),
        }
    )
    root_roles = set(compiled_specs.get("root_component_roles", []))
    required_combinations = [
        set(combination)
        for combination in compiled_specs.get("topology", {}).get(
            "required_role_combinations", []
        )
        if type(combination) is list
    ]
    minimum_roles = compiled_specs.get("minimum_declared_detail_role_count")
    if (
        type(owner_aliases) is not list
        or any(type(alias) is not str for alias in owner_aliases)
        or any(type(alias) is not str for alias in reset_aliases)
        or type(minimum_roles) is not int
    ):
        raise _error("cash-equivalents compiled query frontier is invalid")
    candidates = []
    for item in inventory:
        if type(item) is not dict or type(item.get("classification")) is not dict:
            continue
        axis_item = page_axis.get(item.get("page_json_version_id"))
        resolved = _table_from_inventory(
            inventory_item=item, page_json_by_version=page_json_by_version
        )
        if type(axis_item) is not dict or resolved is None:
            continue
        page, section, table = resolved
        classification = item["classification"]
        rows = table.get("rows")
        role_hits = classification.get("role_hits")
        total_rows = classification.get("total_rows")
        if type(rows) is not list or type(role_hits) is not list or not rows:
            continue
        roles_by_row: dict[int, list[str]] = {}
        for hit in role_hits:
            if type(hit) is not dict or type(hit.get("row_ordinal")) is not int:
                continue
            roles_by_row.setdefault(hit["row_ordinal"], []).append(hit.get("role"))
        direct_rows = set(range(1, len(rows)))
        roles = sorted(
            {
                *(hit.get("role") for hit in role_hits if type(hit) is dict),
                *(classification.get("context_roles") or []),
            }
            - {None}
        )
        role_set = set(roles)
        same_section_money_tables = [
            candidate
            for candidate in inventory
            if type(candidate) is dict
            and candidate.get("page_json_version_id")
            == item.get("page_json_version_id")
            and candidate.get("section_id") == item.get("section_id")
            and type(candidate.get("classification")) is dict
            and candidate["classification"].get("money_column_ordinals")
        ]
        owner_surfaces = [
            {
                "source_exact": section.get("title_exact"),
                "source_kind": "SECTION_TITLE",
                "surface_ordinal": 1,
            },
            {
                "source_exact": table.get("title_exact"),
                "source_kind": "TABLE_TITLE",
                "surface_ordinal": int(item["table_id"][1:]),
            },
            *(
                {
                    "source_exact": narrative,
                    "source_kind": "SECTION_NARRATIVE",
                    "surface_ordinal": ordinal,
                }
                for ordinal, narrative in enumerate(
                    section.get("narratives_exact") or [], start=1
                )
            ),
        ]
        owner_matches = []
        for surface in owner_surfaces:
            matched = _surface_match(
                surface["source_exact"], aliases=owner_aliases
            )
            if matched is not None:
                owner_matches.append(
                    {
                        **surface,
                        "alias": matched[0],
                        "matched_source_exact": matched[1],
                    }
                )
        deduped_owner_matches = {
            (
                match["alias"],
                _without_leading_ordinal(_normalized(match["matched_source_exact"])),
            ): match
            for match in owner_matches
        }
        narrative_owner = (
            len(deduped_owner_matches) == 1
            and next(iter(deduped_owner_matches.values()))["source_kind"]
            == "SECTION_NARRATIVE"
        )
        all_surfaces = [
            *owner_surfaces,
            *(
                {
                    "source_exact": narrative,
                    "source_kind": "SECTION_NARRATIVE",
                    "surface_ordinal": ordinal,
                }
                for ordinal, narrative in enumerate(
                    section.get("narratives_exact") or [], start=1
                )
            ),
            *(
                {
                    "source_exact": candidate.get("title_exact"),
                    "source_kind": "SECTION_TABLE_TITLE",
                    "surface_ordinal": ordinal,
                }
                for ordinal, candidate in enumerate(
                    section.get("tables") or [], start=1
                )
                if type(candidate) is dict
            ),
            *(
                {
                    "source_exact": row.get("label_exact"),
                    "source_kind": "SELECTED_TABLE_ROW_LABEL",
                    "surface_ordinal": ordinal,
                }
                for ordinal, row in enumerate(rows, start=1)
                if type(row) is dict
            ),
        ]
        reset_matches = [
            {**surface, "alias": matched[0], "matched_source_exact": matched[1]}
            for surface in all_surfaces
            if (
                matched := _surface_match(
                    surface["source_exact"], aliases=reset_aliases
                )
            )
            is not None
        ]
        terminal_total = [
            {
                "row_kind": "TOTAL",
                "row_ordinal": len(rows),
                "source_order": len(rows),
            }
        ]
        if (
            page.get("status") != "FINANCIAL_NOTE_CONTENT"
            or section.get("content_kind") != "FINANCIAL_NOTE"
            or section.get("statement_type") not in {"NOT_APPLICABLE", "CASH_FLOW"}
            or table.get("continuation") != "NONE"
            or classification.get("owner_visible") is not True
            and not narrative_owner
            or classification.get("family_presence_anchor_visible") is not True
            or classification.get("money_column_ordinals") != [1, 2]
            or classification.get("typed_control_disposition") is not None
            or classification.get("ambiguous_rows") != []
            or classification.get("family_root_row_ordinals") != []
            or not narrative_owner
            and (
                len(same_section_money_tables) != 1
                or same_section_money_tables[0] is not item
            )
            or len(deduped_owner_matches) != 1
            or reset_matches
            or total_rows != terminal_total
            or classification.get("unbound_money_row_ordinals") != [len(rows)]
            or set(roles_by_row) != direct_rows
            or any(len(roles_by_row[row]) != 1 for row in direct_rows)
            or len(role_set) < minimum_roles
            or not role_set
            or not role_set.issubset(root_roles)
            or required_combinations
            and not any(combination.issubset(role_set) for combination in required_combinations)
        ):
            continue
        owner = next(iter(deduped_owner_matches.values()))
        candidates.append((item, axis_item, owner, roles, all_surfaces))
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
        "owner_matched_source_exact": owner["matched_source_exact"],
        "owner_source_exact": owner["source_exact"],
        "owner_source_kind": owner["source_kind"],
        "owner_surface_ordinal": owner["surface_ordinal"],
        "raw_cluster_id": cluster["cluster_id"],
        "raw_cluster_reasons": canonical_clone_v1(cluster["reasons"]),
        "raw_cluster_status": cluster["status"],
        "rule": (
            "UNIQUE_EXACT_LOCAL_OWNER_"
            + (
                "UNIQUE_DECLARED_FAMILY_SHAPE_IN_SECTION_"
                if owner["source_kind"] == "SECTION_NARRATIVE"
                else "SOLE_SECTION_MONEY_TABLE_"
            )
            + "COMPLETE_DECLARED_NON_TOTAL_ROWS_ONE_TERMINAL_TOTAL_NO_RESET_"
            "VALUE_INDEPENDENT"
        ),
        "section_surface_axis": canonical_clone_v1(surfaces),
        "source_logical_name": cluster["source_logical_name"],
        "source_sha256": cluster["source_sha256"],
    }
    receipt = {
        **material,
        "local_owner_query_receipt_id": (
            "gjceloqrv1:receipt:" + canonical_json_sha256_v1(material)
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


def _primary_cash_flow_anchor_v1(
    *,
    page: Mapping[str, Any],
    candidate_section_ordinal: int,
    candidate_table_ordinal: int,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Return one earlier primary cash-flow closing-balance anchor."""

    reset_aliases = compiled_specs.get("query_policy", {}).get("hard_negative_aliases")
    sections = page.get("sections")
    if type(reset_aliases) is not list or type(sections) is not list:
        raise _error("cash-equivalents primary supplemental frontier is invalid")
    anchors = []
    for section_ordinal, section in enumerate(sections, start=1):
        if type(section) is not dict:
            continue
        for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
            if (section_ordinal, table_ordinal) >= (
                candidate_section_ordinal,
                candidate_table_ordinal,
            ):
                continue
            if (
                type(table) is not dict
                or section.get("content_kind") != "PRIMARY_STATEMENT"
                or section.get("statement_type") != "CASH_FLOW"
            ):
                continue
            matches = []
            for row_ordinal, row in enumerate(table.get("rows") or [], start=1):
                if type(row) is not dict:
                    continue
                matched = _exact_alias(row.get("label_exact"), reset_aliases)
                if matched is not None and matched.endswith("cuoi ky"):
                    matches.append(
                        {
                            "alias": matched,
                            "row_ordinal": row_ordinal,
                            "source_exact": row.get("label_exact"),
                        }
                    )
            if len(matches) == 1:
                anchors.append(
                    {
                        **matches[0],
                        "section_id": f"s{section_ordinal}",
                        "table_id": f"t{table_ordinal}",
                    }
                )
    return anchors[0] if len(anchors) == 1 else None


def _primary_supplemental_shape_v1(
    *,
    page: Mapping[str, Any],
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    section_ordinal: int,
    table_ordinal: int,
    classification: Mapping[str, Any] | None,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Recognize one exact two-period detail table after a cash-flow close."""

    columns = table.get("columns")
    rows = table.get("rows")
    owner_surfaces = [
        ("SECTION_TITLE", section.get("title_exact")),
        ("TABLE_TITLE", table.get("title_exact")),
    ]
    owner_matches = [
        {
            "source_exact": source_exact,
            "source_kind": source_kind,
        }
        for source_kind, source_exact in owner_surfaces
        if _without_leading_ordinal(_normalized(source_exact))
        == _PRIMARY_SUPPLEMENTAL_OWNER
    ]
    if (
        page.get("status") != "PRIMARY_FINANCIAL_STATEMENT"
        or type(columns) is not list
        or len(columns) != 2
        or any(
            type(column) is not dict or column.get("value_kind") != "MONEY"
            for column in columns
        )
        or type(rows) is not list
        or len(rows) != 4
        or any(type(row) is not dict for row in rows)
        or any(row.get("row_kind") != "ITEM" for row in rows[:3])
        or rows[3].get("row_kind") != "TOTAL"
        or table.get("continuation") != "NONE"
        or not owner_matches
        or len(
            {
                _without_leading_ordinal(_normalized(item["source_exact"]))
                for item in owner_matches
            }
        )
        != 1
    ):
        return None
    anchor = _primary_cash_flow_anchor_v1(
        page=page,
        candidate_section_ordinal=section_ordinal,
        candidate_table_ordinal=table_ordinal,
        compiled_specs=compiled_specs,
    )
    if anchor is None:
        return None
    if classification is None:
        roles = []
        for row in rows[:3]:
            label = _without_leading_ordinal(_normalized(row.get("label_exact")))
            matching_roles = sorted(
                role
                for role in compiled_specs.get("root_component_roles", [])
                if label in compiled_specs.get("aliases_by_role", {}).get(role, [])
            )
            if len(matching_roles) != 1:
                return None
            roles.append(matching_roles[0])
    else:
        role_hits = classification.get("role_hits")
        if type(role_hits) is not list:
            return None
        hits_by_row: dict[int, list[str]] = {}
        for hit in role_hits:
            if (
                type(hit) is dict
                and type(hit.get("row_ordinal")) is int
                and type(hit.get("role")) is str
            ):
                hits_by_row.setdefault(hit["row_ordinal"], []).append(hit["role"])
        if set(hits_by_row) != {1, 2, 3} or any(
            len(hits_by_row[row]) != 1 for row in hits_by_row
        ):
            return None
        roles = [hits_by_row[row][0] for row in (1, 2, 3)]
        if (
            classification.get("typed_control_disposition")
            != "PRIMARY_FINANCIAL_STATEMENT_SUMMARY"
            or classification.get("ambiguous_rows") != []
            or classification.get("family_root_row_ordinals") != []
            or classification.get("money_column_ordinals") != [1, 2]
            or classification.get("total_rows")
            != [{"row_kind": "TOTAL", "row_ordinal": 4, "source_order": 4}]
            or classification.get("unbound_money_row_ordinals") != [4]
        ):
            return None
    role_set = set(roles)
    if (
        len(role_set) != 3
        or not {"CASH", "CENTRAL_BANK"}.issubset(role_set)
        or not role_set.issubset(set(compiled_specs.get("root_component_roles", [])))
        or any(
            type(row.get("values_exact")) is not list
            or len(row["values_exact"]) != 2
            or not any(value is not None for value in row["values_exact"])
            for row in rows[:3]
        )
        or type(rows[3].get("values_exact")) is not list
        or len(rows[3]["values_exact"]) != 2
        or any(value is None for value in rows[3]["values_exact"])
    ):
        return None
    owner = owner_matches[-1]
    return {
        "anchor": anchor,
        "component_roles": sorted(role_set),
        "owner_alias": _PRIMARY_SUPPLEMENTAL_OWNER,
        "owner_source_exact": owner["source_exact"],
        "owner_source_kind": owner["source_kind"],
    }


def _primary_supplemental_recovery_v1(
    *,
    cluster: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Recover one exact primary cash-flow supplemental detail table."""

    if cluster.get("status") == READY or tuple(cluster.get("reasons") or []) not in {
        (),
        ("COMPLETE_OWNER_CLUSTER_NOT_RESOLVED",),
    }:
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
        axis_item = page_axis.get(item.get("page_json_version_id"))
        resolved = _table_from_inventory(
            inventory_item=item, page_json_by_version=page_json_by_version
        )
        if type(axis_item) is not dict or resolved is None:
            continue
        page, section, table = resolved
        shape = _primary_supplemental_shape_v1(
            page=page,
            section=section,
            table=table,
            section_ordinal=int(item["section_id"][1:]),
            table_ordinal=int(item["table_id"][1:]),
            classification=item["classification"],
            compiled_specs=compiled_specs,
        )
        if shape is not None:
            candidates.append((item, axis_item, shape))
    if len(candidates) != 1:
        return None
    item, axis_item, shape = candidates[0]
    locator = {
        "page_json_version_id": item["page_json_version_id"],
        "physical_page": item["physical_page"],
        "section_id": item["section_id"],
        "selected_page_ordinal": axis_item["selected_page_ordinal"],
        "table_id": item["table_id"],
    }
    material = {
        "classification_id": item["classification"]["classification_id"],
        "component_roles": shape["component_roles"],
        "document_id": cluster["document_id"],
        "document_ordinal": cluster["document_ordinal"],
        "format_version": PRIMARY_SUPPLEMENTAL_QUERY_RECEIPT_FORMAT_VERSION,
        "locator": locator,
        "owner_alias": shape["owner_alias"],
        "owner_source_exact": shape["owner_source_exact"],
        "owner_source_kind": shape["owner_source_kind"],
        "primary_cash_flow_anchor": canonical_clone_v1(shape["anchor"]),
        "raw_cluster_id": cluster["cluster_id"],
        "raw_cluster_reasons": canonical_clone_v1(cluster["reasons"]),
        "raw_cluster_status": cluster["status"],
        "rule": (
            "UNIQUE_EXACT_PRIMARY_CASH_FLOW_SUPPLEMENTAL_DETAIL_AFTER_VISIBLE_"
            "CLOSING_BALANCE_THREE_DECLARED_ROLES_TERMINAL_TOTAL_VALUE_INDEPENDENT"
        ),
        "source_logical_name": cluster["source_logical_name"],
        "source_sha256": cluster["source_sha256"],
    }
    receipt = {
        **material,
        "primary_supplemental_query_receipt_id": (
            "gjcepsqrv1:receipt:" + canonical_json_sha256_v1(material)
        ),
    }
    region = {
        "component_roles": shape["component_roles"],
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


def adapt_gemini_json_cash_equivalents_indexed_query_evidence_v1(
    value: Any,
    *,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Recover only a unique, structurally complete exact local owner table."""

    evidence = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        value, compiled_specs=compiled_specs
    )
    clusters = []
    receipts = []
    for disposition in evidence["candidate_dispositions"]:
        cluster = canonical_clone_v1(disposition["cluster"])
        pages = page_json_by_document.get(cluster["document_ordinal"])
        recovered = None
        if type(pages) is dict:
            recovered = _local_owner_recovery_v1(
                cluster=cluster,
                selected_page_axis=evidence["selected_page_axis"],
                page_json_by_version=pages,
                compiled_specs=compiled_specs,
            )
            if recovered is None:
                recovered = _primary_supplemental_recovery_v1(
                    cluster=cluster,
                    selected_page_axis=evidence["selected_page_axis"],
                    page_json_by_version=pages,
                    compiled_specs=compiled_specs,
                )
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
                    item["disposition"] = (
                        "SELECTED_FAMILY_COMPONENT_AFTER_EXACT_LOCAL_OWNER_RECEIPT"
                    )
            cluster["component_regions"] = [region]
            owner_receipt = {
                "alias": receipt["owner_alias"],
                "leading_component_positions": [],
                "leading_component_rule": (
                    "EXACT_LOCAL_SOLE_TABLE_OWNER"
                    if "local_owner_query_receipt_id" in receipt
                    else "EXACT_PRIMARY_CASH_FLOW_SUPPLEMENTAL_DETAIL"
                ),
                "position": [
                    receipt["locator"]["selected_page_ordinal"],
                    int(receipt["locator"]["section_id"][1:]),
                    0
                    if receipt["owner_source_kind"] != "TABLE_TITLE"
                    else int(receipt["locator"]["table_id"][1:]),
                ],
                "source_exact": receipt["owner_source_exact"],
            }
            if "local_owner_query_receipt_id" in receipt:
                owner_receipt["local_owner_query_receipt_id"] = receipt[
                    "local_owner_query_receipt_id"
                ]
            else:
                owner_receipt["primary_supplemental_query_receipt_id"] = receipt[
                    "primary_supplemental_query_receipt_id"
                ]
            cluster["owner_receipt"] = owner_receipt
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
) -> tuple[dict[str, Any], dict[str, Any]]:
    page = pages.get(region.get("page_json_version_id"))
    try:
        section = page["sections"][int(region["section_id"][1:]) - 1]  # type: ignore[index]
        table = section["tables"][int(region["table_id"][1:]) - 1]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise _error(
            "cash-equivalents region does not resolve one selected source table"
        ) from exc
    if type(section) is not dict or type(table) is not dict:
        raise _error("cash-equivalents selected source table is invalid")
    return section, table


def _project_primary_supplemental_pages_v1(
    *,
    regions: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Project only an authenticated primary supplemental table for evaluation."""

    pages = {
        version_id: canonical_clone_v1(page)
        for version_id, page in page_json_by_version.items()
    }
    receipts = []

    def period_leaf(column: Any) -> str | None:
        path = column.get("header_path_exact") if type(column) is dict else None
        if type(path) is not list:
            return None
        for value in reversed(path):
            normalized = _normalized(value)
            if normalized and re.fullmatch(r"\(?[1-9][0-9]*\)?", normalized) is None:
                return normalized
        return None

    def adjacent_unit_projection(
        region: Mapping[str, Any], table: dict[str, Any]
    ) -> dict[str, Any] | None:
        if table.get("unit_exact") is not None:
            return None
        page_ids = list(pages)
        try:
            target_index = page_ids.index(region["page_json_version_id"])
        except (KeyError, ValueError) as exc:
            raise _error("cash-equivalents primary supplemental page axis drifted") from exc
        if target_index <= 0 or target_index != region["physical_page"] - 1:
            return None
        prior_id = page_ids[target_index - 1]
        prior_page = pages[prior_id]
        source_tables = []
        for section_ordinal, candidate_section in enumerate(
            prior_page.get("sections") or [], start=1
        ):
            if (
                type(candidate_section) is not dict
                or candidate_section.get("content_kind") != "PRIMARY_STATEMENT"
                or candidate_section.get("statement_type") != "CASH_FLOW"
            ):
                continue
            for table_ordinal, candidate_table in enumerate(
                candidate_section.get("tables") or [], start=1
            ):
                if (
                    type(candidate_table) is dict
                    and candidate_table.get("continuation")
                    == "CONTINUES_ON_NEXT_PAGE"
                    and type(candidate_table.get("unit_exact")) is str
                ):
                    source_tables.append(
                        (section_ordinal, table_ordinal, candidate_table)
                    )
        if len(source_tables) != 1:
            return None
        source_section, source_table_ordinal, source_table = source_tables[0]
        source_unit = source_table["unit_exact"]
        normalized_unit = _normalized(source_unit)
        matching_units = [
            binding
            for binding in compiled_specs.get("unit_bindings", [])
            if binding.get("accepted") is True
            and any(
                normalized_unit == alias or normalized_unit.startswith(alias + " ")
                for alias in binding.get("aliases", [])
            )
        ]
        source_columns = source_table.get("columns")
        target_columns = table.get("columns")
        source_periods = [
            period_leaf(column)
            for column in source_columns or []
            if type(column) is dict and column.get("value_kind") == "MONEY"
        ]
        target_periods = [period_leaf(column) for column in target_columns or []]
        if (
            len(matching_units) != 1
            or matching_units[0].get("canonical_unit") != "MILLION_VND"
            or len(source_periods) != 2
            or source_periods != target_periods
        ):
            return None
        table["unit_exact"] = source_unit
        return {
            "after_unit_exact": source_unit,
            "before_unit_exact": None,
            "rule": (
                "EXACT_IMMEDIATELY_PRECEDING_PRIMARY_CASH_FLOW_CONTINUATION_"
                "TABLE_COMPATIBLE_PERIOD_AXIS_VISIBLE_ACCEPTED_UNIT"
            ),
            "source_locator": {
                "page_json_version_id": prior_id,
                "physical_page": region["physical_page"] - 1,
                "section_id": f"s{source_section}",
                "table_id": f"t{source_table_ordinal}",
            },
            "source_unit_exact": source_unit,
        }

    for region in regions:
        page = pages.get(region.get("page_json_version_id"))
        if type(page) is not dict:
            raise _error("cash-equivalents primary supplemental page is absent")
        section, table = _region_table(pages, region)
        try:
            section_ordinal = int(region["section_id"][1:])
            table_ordinal = int(region["table_id"][1:])
        except (KeyError, TypeError, ValueError) as exc:
            raise _error("cash-equivalents primary supplemental locator is invalid") from exc
        shape = _primary_supplemental_shape_v1(
            page=page,
            section=section,
            table=table,
            section_ordinal=section_ordinal,
            table_ordinal=table_ordinal,
            classification=None,
            compiled_specs=compiled_specs,
        )
        if shape is None:
            continue
        if sorted(region.get("component_roles") or []) != shape["component_roles"]:
            raise _error("cash-equivalents primary supplemental role axis drifted")
        columns = table["columns"]
        before_paths = [
            canonical_clone_v1(column["header_path_exact"]) for column in columns
        ]
        expected_leaves = ["nam nay", "nam truoc"]
        period_projection = None
        if (
            all(len(path) == 2 for path in before_paths)
            and len({_normalized(path[0]) for path in before_paths}) == 1
            and _normalized(before_paths[0][0])
            == "luy ke tu dau nam den cuoi quy nay"
            and [_normalized(path[1]) for path in before_paths] == expected_leaves
        ):
            after_paths = [[path[1]] for path in before_paths]
            for column, after in zip(columns, after_paths, strict=True):
                column["header_path_exact"] = after
            period_projection = {
                "after_header_paths_exact": canonical_clone_v1(after_paths),
                "before_header_paths_exact": before_paths,
                "rule": (
                    "EXACT_CLOSING_BALANCE_SUPPLEMENTAL_TABLE_STRIP_INHERITED_"
                    "CASH_FLOW_DURATION_PREFIX_KEEP_VISIBLE_YEAR_ROLES"
                ),
            }
        unit_projection = adjacent_unit_projection(region, table)
        material = {
            "after_page_status": "FINANCIAL_NOTE_CONTENT",
            "before_page_status": "PRIMARY_FINANCIAL_STATEMENT",
            "component_roles": shape["component_roles"],
            "format_version": (
                PRIMARY_SUPPLEMENTAL_PROJECTION_RECEIPT_FORMAT_VERSION
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
            "owner_alias": shape["owner_alias"],
            "owner_source_exact": shape["owner_source_exact"],
            "owner_source_kind": shape["owner_source_kind"],
            "primary_cash_flow_anchor": canonical_clone_v1(shape["anchor"]),
            "period_projection": canonical_clone_v1(period_projection),
            "query_receipt_id": query_receipt.get("query_receipt_id"),
            "rule": (
                "PROJECT_EXACT_PRIMARY_CASH_FLOW_SUPPLEMENTAL_DETAIL_ONLY_"
                "PRESERVE_RAW_TABLE_ROWS_HEADERS_VALUES_AND_SOURCE_REFS"
            ),
            "source_logical_name": region["source_logical_name"],
            "source_sha256": region["source_sha256"],
            "table_rows_sha256": canonical_json_sha256_v1(table["rows"]),
            "unit_projection": canonical_clone_v1(unit_projection),
        }
        receipts.append(
            {
                **material,
                "primary_supplemental_projection_receipt_id": (
                    "gjcepsprv1:receipt:" + canonical_json_sha256_v1(material)
                ),
            }
        )
        page["status"] = "FINANCIAL_NOTE_CONTENT"
    return pages, receipts


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
        raise _error("cash-equivalents repair candidate source identity is ambiguous")
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
        for repair in compiled_specs.get("cash_equivalents_source_repairs", [])
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
            raise _error("cash-equivalents repair logical source identity drifted")
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
            raise _error("cash-equivalents repair is outside its selected table")
        if locator["page_json_version_id"] not in pages:
            raise _error("cash-equivalents repair page is outside selected document")
        _section, table = _region_table(pages, matching_regions[0])
        rows = table.get("rows")
        if type(rows) is not list or locator["row_ordinal"] > len(rows):
            raise _error("cash-equivalents repair row is outside selected table")
        row = rows[locator["row_ordinal"] - 1]
        values = row.get("values_exact") if type(row) is dict else None
        if (
            type(values) is not list
            or locator["column_ordinal"] > len(values)
            or values[locator["column_ordinal"] - 1] is not repair["before_exact"]
        ):
            raise _error("cash-equivalents repair cell before-image drifted")
        values[locator["column_ordinal"] - 1] = repair["after_exact"]
    return pages, applicable


def _project_ambiguous_period_headers_v1(
    *,
    regions: Sequence[Mapping[str, Any]],
    pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    projected = {
        version_id: canonical_clone_v1(page) for version_id, page in pages.items()
    }
    receipts = []
    owner_aliases = compiled_specs.get("query_policy", {}).get("owner_aliases")
    reset_aliases = sorted(
        {
            *compiled_specs.get("query_policy", {}).get("reset_aliases", []),
            *compiled_specs.get("query_policy", {}).get("hard_negative_aliases", []),
        }
    )
    if type(owner_aliases) is not list:
        raise _error("cash-equivalents compiled owner alias axis is invalid")
    for region in regions:
        section, table = _region_table(projected, region)
        columns = table.get("columns")
        if type(columns) is not list or len(columns) != 2:
            continue
        before = tuple(
            tuple(column.get("header_path_exact") or [])
            if type(column) is dict
            else ()
            for column in columns
        )
        if before != _AMBIGUOUS_PERIOD_HEADER_PAIR:
            continue
        if any(
            type(column) is not dict or column.get("value_kind") != "MONEY"
            for column in columns
        ):
            continue
        owner_surfaces = [section.get("title_exact"), table.get("title_exact")]
        owner_matches = [
            matched
            for surface in owner_surfaces
            if (matched := _surface_match(surface, aliases=owner_aliases)) is not None
        ]
        reset_surfaces = [
            *owner_surfaces,
            *(section.get("narratives_exact") or []),
            *(
                row.get("label_exact")
                for row in table.get("rows") or []
                if type(row) is dict
            ),
        ]
        if (
            not owner_matches
            or len({match[0] for match in owner_matches}) != 1
            or any(
                _surface_match(surface, aliases=reset_aliases) is not None
                for surface in reset_surfaces
            )
        ):
            continue
        material = {
            "after_header_paths_exact": [list(item) for item in _PROJECTED_PERIOD_HEADER_PAIR],
            "before_header_paths_exact": [list(item) for item in before],
            "format_version": HEADER_PROJECTION_RECEIPT_FORMAT_VERSION,
            "locator": {
                field: region[field]
                for field in (
                    "page_json_version_id",
                    "physical_page",
                    "section_id",
                    "table_id",
                )
            },
            "owner_alias": owner_matches[0][0],
            "query_receipt_id": query_receipt.get("query_receipt_id"),
            "rule": (
                "EXACT_TWO_MONEY_COLUMN_OWNER_TABLE_CURRENT_PERIOD_THIS_END_"
                "VERSUS_COMPARATIVE_PRIOR_END_HEADER_DISAMBIGUATION"
            ),
            "source_logical_name": region["source_logical_name"],
            "source_sha256": region["source_sha256"],
        }
        receipt = {
            **material,
            "header_projection_receipt_id": (
                "gjcehprv1:receipt:" + canonical_json_sha256_v1(material)
            ),
        }
        for column, after in zip(columns, _PROJECTED_PERIOD_HEADER_PAIR, strict=True):
            column["header_path_exact"] = list(after)
        receipts.append(receipt)
    return projected, receipts


def _restore_header_projection_receipts_v1(
    candidate: dict[str, Any], *, receipts: Sequence[Mapping[str, Any]]
) -> None:
    table_receipts = candidate.get("closure_receipt", {}).get("table_receipts")
    if type(table_receipts) is not list:
        raise _error("cash-equivalents projected table receipt axis is absent")
    for receipt in receipts:
        locator = receipt["locator"]
        matching = [
            table_receipt
            for table_receipt in table_receipts
            if type(table_receipt) is dict
            and all(
                table_receipt.get("region", {}).get(field) == locator[field]
                for field in (
                    "page_json_version_id",
                    "physical_page",
                    "section_id",
                    "table_id",
                )
            )
        ]
        if len(matching) != 1:
            raise _error("cash-equivalents projected table receipt is ambiguous")
        period_axis = matching[0].get("lane_axis", {}).get("source_period_axis")
        if (
            type(period_axis) is not dict
            or period_axis.get("headers_exact")
            != [item[0] for item in _PROJECTED_PERIOD_HEADER_PAIR]
        ):
            raise _error("cash-equivalents projected header receipt drifted")
        period_axis["headers_exact"] = [
            item[0] for item in _AMBIGUOUS_PERIOD_HEADER_PAIR
        ]


def _typed_partial_root_omission_v1(
    *,
    required_candidate: Mapping[str, Any],
    regions: Sequence[Mapping[str, Any]],
    pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Keep visible sibling lanes when one source cell is genuinely blank.

    The shared evaluator is replayed with only the root requirement relaxed.
    This fallback is accepted solely when that replay exposes at least one
    typed partial source observation, emits no family root, and uses no root
    equation.  A total mismatch with fully observed rows therefore cannot use
    this route.
    """

    if (
        required_candidate.get("status") != UNRESOLVED
        or required_candidate.get("reasons")
        != ["REQUIRED_SOURCE_VISIBLE_EXACT_FAMILY_ROOT_NOT_PROVEN"]
        or compiled_specs.get("family_root_requirement")
        != "REQUIRED_SOURCE_VISIBLE_EXACT_ROOT"
    ):
        return None
    optional_specs = canonical_clone_v1(compiled_specs)
    optional_specs["family_root_requirement"] = "OPTIONAL"
    optional_specs["evaluation"]["family_root_requirement"] = "OPTIONAL"
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=regions,
        page_json_by_version=pages,
        compiled_specs=optional_specs,
        query_receipt=query_receipt,
    )
    if candidate.get("status") != READY or candidate.get("reasons") != []:
        return None
    mappings = candidate.get("mappings")
    equations = candidate.get("closure_receipt", {}).get("equations")
    if type(mappings) is not list or not mappings or type(equations) is not list:
        return None
    if any(mapping.get("role") == "FAMILY_ROOT_TOTAL" for mapping in mappings):
        return None
    if any(
        equation.get("result_role") == "FAMILY_ROOT_TOTAL"
        for equation in equations
        if type(equation) is dict
    ):
        return None
    partial_axis = []
    for mapping in mappings:
        if (
            type(mapping) is not dict
            or mapping.get("role") not in compiled_specs.get("bindings", {})
            or type(mapping.get("values")) is not list
            or not mapping["values"]
        ):
            return None
        blank_lanes = []
        observed_lanes = []
        for lane_ordinal, cell in enumerate(mapping["values"], start=1):
            if type(cell) is not dict:
                return None
            coefficient = cell.get("coefficient")
            if coefficient is None:
                if (
                    cell.get("source_text") is not None
                    or cell.get("state") != "BLANK_SOURCE_CELL"
                ):
                    return None
                blank_lanes.append(lane_ordinal)
            elif type(coefficient) is int and type(cell.get("source_text")) is str:
                observed_lanes.append(lane_ordinal)
            else:
                return None
        if blank_lanes:
            if not observed_lanes:
                return None
            partial_axis.append(
                {
                    "blank_lane_ordinals": blank_lanes,
                    "observed_lane_ordinals": observed_lanes,
                    "report_norm_id": mapping["report_norm_id"],
                    "role": mapping["role"],
                    "row_id": mapping["row_id"],
                    "source_refs": canonical_clone_v1(mapping["source_refs"]),
                }
            )
    if not partial_axis:
        return None
    material = {
        "after_family_root_requirement": "OPTIONAL_FOR_THIS_CANDIDATE_ONLY",
        "before_family_root_requirement": "REQUIRED_SOURCE_VISIBLE_EXACT_ROOT",
        "format_version": PARTIAL_ROOT_OMISSION_RECEIPT_FORMAT_VERSION,
        "partial_mapping_axis": partial_axis,
        "partial_mapping_axis_sha256": canonical_json_sha256_v1(partial_axis),
        "query_receipt_id": query_receipt.get("query_receipt_id"),
        "raw_candidate_id": required_candidate.get("candidate_id"),
        "raw_candidate_reasons": canonical_clone_v1(required_candidate["reasons"]),
        "region_axis_sha256": canonical_json_sha256_v1(list(regions)),
        "rule": (
            "ONLY_REQUIRED_ROOT_NOT_PROVEN_TYPED_PARTIAL_SOURCE_LANES_REPLAY_"
            "WITHOUT_ROOT_MAPPING_OR_ROOT_EQUATION_BLANKS_REMAIN_NULL"
        ),
    }
    receipt = {
        **material,
        "partial_root_omission_receipt_id": (
            "gjceprorv1:receipt:" + canonical_json_sha256_v1(material)
        ),
    }
    return candidate, receipt


def _reseal_candidate(
    candidate: dict[str, Any],
    *,
    authenticated_source_repairs: Sequence[Mapping[str, Any]],
    header_projection_receipts: Sequence[Mapping[str, Any]],
    partial_root_omission_receipt: Mapping[str, Any] | None,
    primary_supplemental_projection_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if (
        not authenticated_source_repairs
        and not header_projection_receipts
        and partial_root_omission_receipt is None
        and not primary_supplemental_projection_receipts
    ):
        return candidate
    closure = candidate.get("closure_receipt")
    if type(closure) is not dict:
        raise _error("cash-equivalents generic candidate closure receipt is absent")
    material = {
        "adapter_format_version": ADAPTER_FORMAT_VERSION,
        "authenticated_source_repairs": canonical_clone_v1(
            list(authenticated_source_repairs)
        ),
        "header_projection_receipts": canonical_clone_v1(
            list(header_projection_receipts)
        ),
        "partial_root_omission_receipt": canonical_clone_v1(
            partial_root_omission_receipt
        ),
        "primary_supplemental_projection_receipts": canonical_clone_v1(
            list(primary_supplemental_projection_receipts)
        ),
        "shared_engine_claim_boundary": GENERIC_CLAIM_BOUNDARY,
    }
    candidate["claim_boundary"] = ADAPTER_CLAIM_BOUNDARY
    closure["cash_equivalents_adapter_receipt"] = {
        **material,
        "adapter_receipt_id": "gjcefav1:receipt:"
        + canonical_json_sha256_v1(material),
    }
    candidate_material = {
        key: candidate[key] for key in candidate if key != "candidate_id"
    }
    candidate["candidate_id"] = (
        "gjmthfcv1:candidate:" + canonical_json_sha256_v1(candidate_material)
    )
    return candidate


def evaluate_gemini_json_cash_equivalents_family_cluster_v1(
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate Family 40 with only exact structural/source observations."""

    if compiled_specs.get("topology", {}).get("family_id") != FAMILY_ID:
        raise _error("cash-equivalents adapter received another family")
    if type(regions) not in {list, tuple} or not regions:
        return evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
            regions=regions,
            page_json_by_version=page_json_by_version,
            compiled_specs=compiled_specs,
            query_receipt=query_receipt,
        )
    pages, primary_supplemental_receipts = _project_primary_supplemental_pages_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    pages, repairs = _apply_authenticated_source_repairs(
        regions=regions,
        page_json_by_version=pages,
        compiled_specs=compiled_specs,
    )
    pages, header_receipts = _project_ambiguous_period_headers_v1(
        regions=regions,
        pages=pages,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=regions,
        page_json_by_version=pages,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    partial_root_omission_receipt = None
    partial = _typed_partial_root_omission_v1(
        required_candidate=candidate,
        regions=regions,
        pages=pages,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if partial is not None:
        candidate, partial_root_omission_receipt = partial
    if header_receipts:
        _restore_header_projection_receipts_v1(candidate, receipts=header_receipts)
    return _reseal_candidate(
        candidate,
        authenticated_source_repairs=repairs,
        header_projection_receipts=header_receipts,
        partial_root_omission_receipt=partial_root_omission_receipt,
        primary_supplemental_projection_receipts=primary_supplemental_receipts,
    )


def validate_gemini_json_cash_equivalents_family_candidate_replay_v1(
    value: Any,
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay the complete adapter from immutable selected JSON."""

    expected = evaluate_gemini_json_cash_equivalents_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if type(value) is not dict or not same_typed_json_v1(value, expected):
        raise _error("cash-equivalents family adapter candidate replay drifted")
    return expected
