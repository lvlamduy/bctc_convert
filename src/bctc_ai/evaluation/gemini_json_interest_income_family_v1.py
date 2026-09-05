"""Family-28 adapter for interest-income disclosures.

The shared multi-table engine remains the accounting authority.  This module
adds only three independently replayable source-normalisation steps before the
shared evaluator runs:

* exact, PDF-authenticated transcription repairs whose replacement is a dash;
* one governed cumulative-duration header normalisation; and
* an exact source-unit corroboration against the same document's primary
  interest-income row.

None of the steps derives a numeric value or turns an unobserved cell into
zero.  All transformations are applied to private page clones.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import (
    _normalized,
    _without_leading_ordinal,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    CLAIM_BOUNDARY as SHARED_CLAIM_BOUNDARY,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    _multitable_lane_axis,
    _source_money,
    _source_table,
    _unit_axis,
    build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    classify_gemini_json_multitable_hierarchical_table_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
    validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FAMILY_ID = "INTEREST_INCOME"
ADAPTER_FORMAT_VERSION = "GEMINI_JSON_INTEREST_INCOME_FAMILY_ADAPTER_V1"
SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION = (
    "GEMINI_JSON_INTEREST_INCOME_AUTHENTICATED_SOURCE_REPAIR_ARTIFACT_V1"
)
SOURCE_REPAIR_POLICY = (
    "ONLY_EXACT_PDF_RENDER_VISIBLE_DASH_TRANSCRIPTION_REPAIR_NO_EQUATION_DERIVATION"
)
ONE_SIDED_CONTINUATION_RECEIPT_FORMAT_VERSION = (
    "GEMINI_JSON_INTEREST_INCOME_ONE_SIDED_EXPLICIT_CONTINUATION_RECEIPT_V1"
)
DEFAULT_SOURCE_REPAIR_PATH = "data/registered/gemini_json_interest_income_source_repairs_v1.json"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_DECLARATIVE_INTEREST_INCOME_"
    "MULTITABLE_HIERARCHICAL_EXACT_PDF_DASH_TRANSCRIPTION_GOVERNED_DURATION_"
    "HEADER_AND_PRIMARY_STATEMENT_VALUE_PERIOD_UNIT_CORROBORATION_PRIVATE_CLONE_"
    "ONLY_NO_BLANK_ZERO_NO_NUMERIC_BACKSOLVE_NO_MAGNITUDE_UNIT_INFERENCE_"
    "PROPOSAL_ONLY_" + SHARED_CLAIM_BOUNDARY
)

_PAGE_VERSION = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SECTION_ID = re.compile(r"s[1-9][0-9]*\Z")
_TABLE_ID = re.compile(r"t[1-9][0-9]*\Z")
_ROW_ID = re.compile(r"r[1-9][0-9]*\Z")
_REPAIR_ID = re.compile(r"gjiifav1:repair:[0-9a-f]{64}\Z")
_OVERLAY_ID = re.compile(r"gjiifav1:overlay:[0-9a-f]{64}\Z")


class GeminiJsonInterestIncomeFamilyV1Error(ValueError):
    """The Family-28 source adapter or its replay evidence drifted."""


def _error(message: str) -> GeminiJsonInterestIncomeFamilyV1Error:
    return GeminiJsonInterestIncomeFamilyV1Error(message)


def _load_default_source_repair_artifact_v1() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[3] / DEFAULT_SOURCE_REPAIR_PATH
    try:
        return json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("interest-income source-repair artifact is absent or invalid") from exc


def _compile_authenticated_source_repair_artifact_v1(value: Any) -> dict[str, Any]:
    artifact_fields = {
        "format_version",
        "overlay_id",
        "policy",
        "repair_axis_sha256",
        "repair_count",
        "repairs",
    }
    if (
        type(value) is not dict
        or set(value) != artifact_fields
        or value.get("format_version") != SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION
        or value.get("policy") != SOURCE_REPAIR_POLICY
        or type(value.get("repairs")) is not list
        or not value["repairs"]
        or value.get("repair_count") != len(value["repairs"])
        or value.get("repair_axis_sha256") != canonical_json_sha256_v1(value["repairs"])
    ):
        raise _error("interest-income source-repair artifact is invalid")

    repair_fields = {
        "base_page_json_sha256",
        "base_table_sha256",
        "cell_repairs",
        "page_image",
        "page_json_version_id",
        "physical_page",
        "reason",
        "repair_id",
        "section_id",
        "source_logical_name",
        "source_sha256",
        "table_id",
    }
    image_fields = {
        "height",
        "media_type",
        "render_dpi",
        "sha256",
        "size_bytes",
        "width",
    }
    cell_fields = {
        "column_ordinal",
        "original_value_exact",
        "replacement_value_exact",
        "row_hierarchy_path_exact",
        "row_id",
        "row_kind",
        "row_label_exact",
        "visual_observation",
    }
    repairs = []
    seen_versions: set[str] = set()
    seen_ids: set[str] = set()
    for raw_repair in value["repairs"]:
        if type(raw_repair) is not dict or set(raw_repair) != repair_fields:
            raise _error("interest-income source-repair fields drifted")
        repair = canonical_clone_v1(raw_repair)
        image = repair.get("page_image")
        if (
            type(image) is not dict
            or set(image) != image_fields
            or _SHA256.fullmatch(image.get("sha256", "")) is None
            or type(image.get("size_bytes")) is not int
            or image["size_bytes"] <= 0
            or type(image.get("width")) is not int
            or image["width"] <= 0
            or type(image.get("height")) is not int
            or image["height"] <= 0
            or image.get("render_dpi") != 300
            or image.get("media_type") != "image/png"
        ):
            raise _error("interest-income source-repair page image is invalid")
        if (
            _SHA256.fullmatch(repair.get("base_page_json_sha256", "")) is None
            or _SHA256.fullmatch(repair.get("base_table_sha256", "")) is None
            or _PAGE_VERSION.fullmatch(repair.get("page_json_version_id", "")) is None
            or repair["page_json_version_id"] in seen_versions
            or type(repair.get("physical_page")) is not int
            or repair["physical_page"] <= 0
            or _SECTION_ID.fullmatch(repair.get("section_id", "")) is None
            or _TABLE_ID.fullmatch(repair.get("table_id", "")) is None
            or type(repair.get("source_logical_name")) is not str
            or not repair["source_logical_name"].strip()
            or _SHA256.fullmatch(repair.get("source_sha256", "")) is None
            or repair.get("reason")
            != "PDF_RENDER_VISIBLE_DASH_SELECTED_JSON_TRANSCRIPTION_MISMATCH"
            or type(repair.get("cell_repairs")) is not list
            or not repair["cell_repairs"]
        ):
            raise _error("interest-income source-repair source binding is invalid")
        seen_versions.add(repair["page_json_version_id"])
        cells = []
        seen_cells: set[tuple[str, int]] = set()
        for raw_cell in repair["cell_repairs"]:
            if type(raw_cell) is not dict or set(raw_cell) != cell_fields:
                raise _error("interest-income source-repair cell fields drifted")
            cell = canonical_clone_v1(raw_cell)
            identity = (cell.get("row_id"), cell.get("column_ordinal"))
            if (
                _ROW_ID.fullmatch(cell.get("row_id", "")) is None
                or type(cell.get("column_ordinal")) is not int
                or cell["column_ordinal"] <= 0
                or identity in seen_cells
                or cell.get("original_value_exact") is not None
                and type(cell.get("original_value_exact")) is not str
                or cell.get("replacement_value_exact") != "-"
                or cell.get("visual_observation") != "PDF_RENDER_VISIBLE_DASH"
                or type(cell.get("row_kind")) is not str
                or not cell["row_kind"]
                or type(cell.get("row_label_exact")) is not str
                or not cell["row_label_exact"].strip()
                or type(cell.get("row_hierarchy_path_exact")) is not list
                or not cell["row_hierarchy_path_exact"]
                or any(
                    item is not None and type(item) is not str
                    for item in cell["row_hierarchy_path_exact"]
                )
            ):
                raise _error("interest-income source-repair cell is invalid")
            seen_cells.add(identity)
            cells.append(cell)
        ordered_cells = sorted(
            cells,
            key=lambda item: (int(item["row_id"][1:]), item["column_ordinal"]),
        )
        if repair["cell_repairs"] != ordered_cells:
            raise _error("interest-income source-repair cell axis is unordered")
        expected_id = "gjiifav1:repair:" + canonical_json_sha256_v1(
            {key: repair[key] for key in repair if key != "repair_id"}
        )
        if (
            _REPAIR_ID.fullmatch(repair.get("repair_id", "")) is None
            or repair["repair_id"] != expected_id
            or repair["repair_id"] in seen_ids
        ):
            raise _error("interest-income source-repair identity does not replay")
        seen_ids.add(repair["repair_id"])
        repairs.append(repair)
    ordered_repairs = sorted(
        repairs,
        key=lambda item: (
            item["source_logical_name"],
            item["physical_page"],
            int(item["section_id"][1:]),
            int(item["table_id"][1:]),
        ),
    )
    if value["repairs"] != ordered_repairs:
        raise _error("interest-income source-repair axis is unordered")
    material = {
        key: canonical_clone_v1(value[key]) for key in artifact_fields if key != "overlay_id"
    }
    expected_overlay_id = "gjiifav1:overlay:" + canonical_json_sha256_v1(material)
    if (
        _OVERLAY_ID.fullmatch(value.get("overlay_id", "")) is None
        or value["overlay_id"] != expected_overlay_id
    ):
        raise _error("interest-income source-repair overlay identity does not replay")
    return canonical_clone_v1(value)


def compile_gemini_json_interest_income_family_specs_v1(
    topology_spec: Any,
    evaluation_spec: Any,
    schema_binding_spec: Any,
    source_repair_spec: Any | None = None,
) -> dict[str, Any]:
    """Compile Family 28 plus its independently authenticated source overlay."""

    try:
        compiled = compile_gemini_json_multitable_hierarchical_family_specs_v1(
            topology_spec, evaluation_spec, schema_binding_spec
        )
    except ValueError as exc:
        raise _error("interest-income declarative family specs are invalid") from exc
    return bind_gemini_json_interest_income_source_repair_artifact_v1(
        compiled,
        source_repair_spec,
    )


def bind_gemini_json_interest_income_source_repair_artifact_v1(
    compiled_specs: Any,
    source_repair_spec: Any | None = None,
) -> dict[str, Any]:
    """Bind the exact dash overlay to an already compiled generic family."""

    if type(compiled_specs) is not dict:
        raise _error("interest-income compiled family frontier is invalid")
    compiled = canonical_clone_v1(compiled_specs)
    if (
        compiled.get("topology", {}).get("family_id") != FAMILY_ID
        or compiled.get("schema", {}).get("family_id") != FAMILY_ID
        or compiled.get("evaluation", {}).get("family_id") != FAMILY_ID
        or {
            binding["canonical_unit"]
            for binding in compiled.get("unit_bindings", [])
            if binding.get("accepted") is True
        }
        != {"MILLION_VND", "VND"}
    ):
        raise _error("interest-income compiled family frontier is invalid")
    raw_overlay = (
        _load_default_source_repair_artifact_v1()
        if source_repair_spec is None
        else source_repair_spec
    )
    compiled["interest_income_adapter_format_version"] = ADAPTER_FORMAT_VERSION
    compiled["interest_income_source_repair_overlay"] = (
        _compile_authenticated_source_repair_artifact_v1(raw_overlay)
    )
    compiled["interest_income_source_repair_spec_sha256"] = canonical_json_sha256_v1(raw_overlay)
    return compiled


def build_gemini_json_interest_income_region_query_receipt_v1(
    regions: Any,
) -> dict[str, Any]:
    return build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)


def coalesce_gemini_json_interest_income_document_v1(
    *, page_records: Any, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    if compiled_specs.get("topology", {}).get("family_id") != FAMILY_ID:
        raise _error("interest-income adapter received another family")
    return coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=page_records,
        compiled_specs=compiled_specs,
    )


def _region_table(
    pages: Mapping[str, dict[str, Any]], region: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    page = pages.get(region.get("page_json_version_id"))
    if type(page) is not dict:
        raise _error("interest-income selected page JSON is absent")
    try:
        return _source_table(
            page,
            section_id=region["section_id"],
            table_id=region["table_id"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise _error("interest-income selected source table is invalid") from exc


def _classification_role_axis(classification: Mapping[str, Any]) -> list[str]:
    return sorted(
        {
            hit["role"]
            for hit in classification.get("role_hits", [])
            if type(hit) is dict and type(hit.get("role")) is str
        }
    )


def _one_sided_explicit_continuation_receipt_v1(
    *,
    prior_region: Mapping[str, Any],
    receiver_region: Mapping[str, Any],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Authenticate a page-leading explicit receiver whose sender omitted ON_NEXT.

    This is intentionally narrower than the shared two-sided continuation rule.
    The receiver itself must explicitly say ``CONTINUES_FROM_PREVIOUS_PAGE``;
    both selected and physical pages must be adjacent; the sender must be the
    final table on its page with a complete local period/unit axis; and the
    receiver must be the titleless first table with blank headers, only declared
    family roles, and one terminal printed total.  No value participates in
    admitting the fragment.
    """

    if (
        prior_region.get("document_id") != receiver_region.get("document_id")
        or prior_region.get("source_sha256") != receiver_region.get("source_sha256")
        or receiver_region.get("selected_page_ordinal")
        != prior_region.get("selected_page_ordinal", -2) + 1
        or receiver_region.get("physical_page") != prior_region.get("physical_page", -2) + 1
        or receiver_region.get("section_id") != "s1"
        or receiver_region.get("table_id") != "t1"
    ):
        return None
    try:
        prior_page = page_json_by_version[prior_region["page_json_version_id"]]
        receiver_page = page_json_by_version[receiver_region["page_json_version_id"]]
        prior_section, prior_table = _region_table(page_json_by_version, prior_region)
        receiver_section, receiver_table = _region_table(page_json_by_version, receiver_region)
    except (KeyError, TypeError, ValueError, GeminiJsonInterestIncomeFamilyV1Error):
        return None
    prior_sections = prior_page.get("sections")
    receiver_sections = receiver_page.get("sections")
    prior_tables = prior_section.get("tables")
    receiver_tables = receiver_section.get("tables")
    if (
        type(prior_sections) is not list
        or not prior_sections
        or prior_section is not prior_sections[-1]
        or type(prior_tables) is not list
        or not prior_tables
        or prior_table is not prior_tables[-1]
        or type(receiver_sections) is not list
        or not receiver_sections
        or receiver_section is not receiver_sections[0]
        or type(receiver_tables) is not list
        or not receiver_tables
        or receiver_table is not receiver_tables[0]
        or prior_table.get("continuation") != "NONE"
        or receiver_table.get("continuation") != "CONTINUES_FROM_PREVIOUS_PAGE"
        or _normalized(receiver_section.get("title_exact"))
        or _normalized(receiver_table.get("title_exact"))
    ):
        return None

    prior_axis = _multitable_lane_axis(prior_section, prior_table, compiled_specs=compiled_specs)
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
    columns = receiver_table.get("columns")
    prior_money_ordinals = prior_axis.get("money_column_ordinals")
    if type(columns) is not list or type(prior_money_ordinals) is not list:
        return None
    receiver_money_ordinals = [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    if (
        prior_axis.get("complete") is not True
        or prior_unit.get("complete") is not True
        or receiver_unit.get("complete") is True
        or receiver_unit.get("evidence")
        or receiver_unit.get("undeclared_evidence")
        or receiver_money_ordinals != prior_money_ordinals
        or not receiver_money_ordinals
        or any(
            column.get("header_path_exact") != [None]
            for column in (columns[ordinal - 1] for ordinal in receiver_money_ordinals)
        )
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
    prior_roles = _classification_role_axis(prior_classification)
    receiver_roles = _classification_role_axis(receiver_classification)
    root_roles = set(compiled_specs.get("root_component_roles", []))
    rows = receiver_table.get("rows")
    total_rows = receiver_classification.get("total_rows")
    terminal_total = (
        [
            {
                "row_kind": rows[-1].get("row_kind"),
                "row_ordinal": len(rows),
                "source_order": len(rows),
            }
        ]
        if type(rows) is list and rows and type(rows[-1]) is dict
        else []
    )
    if (
        prior_classification.get("typed_control_disposition") is not None
        or receiver_classification.get("typed_control_disposition") is not None
        or prior_classification.get("ambiguous_rows")
        or receiver_classification.get("ambiguous_rows")
        or not prior_roles
        or not receiver_roles
        or not set(prior_roles).issubset(root_roles)
        or not set(receiver_roles).issubset(root_roles)
        or total_rows != terminal_total
        or set(receiver_classification.get("unbound_money_row_ordinals", [])) != {len(rows)}
    ):
        return None

    # Preserve the authenticated source rows verbatim.  A terminal source
    # parent and its next-page same-role detail rows are related only by the
    # shared, opt-in cross-fragment equation policy; query recovery must not
    # manufacture GROUP kinds or hierarchy paths to make that equation fit.
    structural_group_normalization = None
    receiver_hierarchy_normalizations = []

    material = {
        "format_version": ONE_SIDED_CONTINUATION_RECEIPT_FORMAT_VERSION,
        "prior_component_roles": prior_roles,
        "prior_lane_axis": canonical_clone_v1(prior_axis),
        "prior_locator": {
            key: prior_region[key]
            for key in (
                "page_json_version_id",
                "physical_page",
                "section_id",
                "selected_page_ordinal",
                "table_id",
            )
        },
        "prior_unit_axis": canonical_clone_v1(prior_unit),
        "receiver_component_roles": receiver_roles,
        "receiver_hierarchy_normalizations": receiver_hierarchy_normalizations,
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
        "rule": (
            "EXPLICIT_PAGE_LEADING_CONTINUES_FROM_PREVIOUS_PAGE_RECEIVER_PLUS_"
            "ADJACENT_PAGE_FINAL_COMPLETE_AXIS_UNIT_DECLARED_FAMILY_SENDER_"
            "WITH_MISSING_ON_NEXT_MARKER_NO_VALUE_SELECTION"
        ),
        "source_sha256": prior_region["source_sha256"],
        "structural_group_normalization": structural_group_normalization,
    }
    return {
        **material,
        "receipt_id": "gjiifav1:one-sided-continuation:" + canonical_json_sha256_v1(material),
    }


def adapt_gemini_json_interest_income_indexed_query_evidence_v1(
    value: Any,
    *,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Add only a uniquely authenticated one-sided continuation receiver."""

    evidence = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        value, compiled_specs=compiled_specs
    )
    page_axis_by_document: dict[int, list[dict[str, Any]]] = {}
    for item in evidence["selected_page_axis"]:
        page_axis_by_document.setdefault(item["document_ordinal"], []).append(item)
    clusters = []
    receipts = []
    for disposition in evidence["candidate_dispositions"]:
        cluster = canonical_clone_v1(disposition["cluster"])
        regions = cluster.get("component_regions")
        pages = page_json_by_document.get(cluster["document_ordinal"])
        if cluster.get("status") == READY and type(regions) is list and regions and pages:
            prior_region = max(
                regions,
                key=lambda item: (
                    item["selected_page_ordinal"],
                    item["physical_page"],
                    item["section_id"],
                    item["table_id"],
                ),
            )
            possible_axes = [
                item
                for item in page_axis_by_document.get(cluster["document_ordinal"], [])
                if item["selected_page_ordinal"] == prior_region["selected_page_ordinal"] + 1
                and item["physical_page"] == prior_region["physical_page"] + 1
                and item["document_id"] == prior_region["document_id"]
                and item["source_sha256"] == prior_region["source_sha256"]
            ]
            recovered = []
            for axis_item in possible_axes:
                receiver_region = {
                    "component_roles": [],
                    "document_id": cluster["document_id"],
                    "document_ordinal": cluster["document_ordinal"],
                    "fragment_ordinal": len(regions) + 1,
                    "page_json_version_id": axis_item["page_json_version_id"],
                    "physical_page": axis_item["physical_page"],
                    "section_id": "s1",
                    "selected_page_ordinal": axis_item["selected_page_ordinal"],
                    "source_logical_name": cluster["source_logical_name"],
                    "source_sha256": cluster["source_sha256"],
                    "table_id": "t1",
                }
                try:
                    receiver_page = pages[axis_item["page_json_version_id"]]
                    receiver_section, receiver_table = _region_table(pages, receiver_region)
                    receiver_classification = classify_gemini_json_multitable_hierarchical_table_v1(
                        receiver_page,
                        receiver_section,
                        receiver_table,
                        compiled_specs=compiled_specs,
                    )
                except (KeyError, GeminiJsonInterestIncomeFamilyV1Error):
                    continue
                receiver_region["component_roles"] = _classification_role_axis(
                    receiver_classification
                )
                receipt = _one_sided_explicit_continuation_receipt_v1(
                    prior_region=prior_region,
                    receiver_region=receiver_region,
                    page_json_by_version=pages,
                    compiled_specs=compiled_specs,
                )
                if receipt is not None:
                    recovered.append((receiver_region, receipt))
            if len(recovered) == 1:
                receiver_region, receipt = recovered[0]
                cluster["component_regions"].append(receiver_region)
                cluster["component_regions"].sort(
                    key=lambda item: (
                        item["selected_page_ordinal"],
                        item["section_id"],
                        item["table_id"],
                    )
                )
                for item in cluster["declared_money_table_inventory"]:
                    if (
                        item.get("page_json_version_id"),
                        item.get("section_id"),
                        item.get("table_id"),
                    ) == (
                        receiver_region["page_json_version_id"],
                        receiver_region["section_id"],
                        receiver_region["table_id"],
                    ):
                        item["disposition"] = (
                            "SELECTED_AFTER_ONE_SIDED_EXPLICIT_CONTINUATION_RECEIPT"
                        )
                cluster["owner_receipt"]["interest_income_one_sided_continuation_receipt_id"] = (
                    receipt["receipt_id"]
                )
                receipts.append(receipt)
        material = {key: item for key, item in cluster.items() if key != "cluster_id"}
        cluster["cluster_id"] = "gjmthfcv1:cluster:" + canonical_json_sha256_v1(material)
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
    receipts.sort(key=lambda item: item["receipt_id"])
    return adapted, receipts


def _apply_one_sided_continuation_normalization_v1(
    *,
    pages: dict[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    receipts = []
    ordered = sorted(
        regions,
        key=lambda item: (
            item["selected_page_ordinal"],
            item["section_id"],
            item["table_id"],
        ),
    )
    for prior_region, receiver_region in zip(ordered, ordered[1:], strict=False):
        receipt = _one_sided_explicit_continuation_receipt_v1(
            prior_region=prior_region,
            receiver_region=receiver_region,
            page_json_by_version=pages,
            compiled_specs=compiled_specs,
        )
        if receipt is None:
            continue
        _prior_section, prior_table = _region_table(pages, prior_region)
        prior_table["continuation"] = "CONTINUES_ON_NEXT_PAGE"
        normalization = receipt["structural_group_normalization"]
        if type(normalization) is dict:
            rows = prior_table["rows"]
            row = rows[normalization["row_ordinal"] - 1]
            if (
                row.get("row_kind") != normalization["before_row_kind"]
                or row.get("label_exact") != normalization["source_label_exact"]
            ):
                raise _error("interest-income continuation structural row binding drifted")
            row["row_kind"] = normalization["after_row_kind"]
        _receiver_section, receiver_table = _region_table(pages, receiver_region)
        for item in receipt["receiver_hierarchy_normalizations"]:
            receiver_rows = receiver_table["rows"]
            receiver_row = receiver_rows[item["row_ordinal"] - 1]
            if receiver_row.get("label_exact") != item[
                "source_label_exact"
            ] or not same_typed_json_v1(
                receiver_row.get("hierarchy_path_exact"),
                item["before_hierarchy_path_exact"],
            ):
                raise _error("interest-income continuation hierarchy binding drifted")
            receiver_row["hierarchy_path_exact"] = canonical_clone_v1(
                item["after_hierarchy_path_exact"]
            )
        receipts.append(receipt)
    return receipts


def _repair_receipt(
    *, repair: Mapping[str, Any], compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    material = {
        "base_page_json_sha256": repair["base_page_json_sha256"],
        "base_table_sha256": repair["base_table_sha256"],
        "cell_repairs": canonical_clone_v1(repair["cell_repairs"]),
        "overlay_id": compiled_specs["interest_income_source_repair_overlay"]["overlay_id"],
        "page_image": canonical_clone_v1(repair["page_image"]),
        "page_json_version_id": repair["page_json_version_id"],
        "physical_page": repair["physical_page"],
        "repair_id": repair["repair_id"],
        "rule": (
            "EXACT_SOURCE_PDF_RENDER_SELECTED_JSON_TABLE_ROW_COLUMN_BEFORE_TO_"
            "LITERAL_DASH_TRANSCRIPTION_ONLY_NO_EQUATION_DERIVATION"
        ),
        "section_id": repair["section_id"],
        "source_logical_name": repair["source_logical_name"],
        "source_sha256": repair["source_sha256"],
        "status": "AUTHENTICATED_PDF_VISIBLE_DASH_TRANSCRIBED",
        "table_id": repair["table_id"],
    }
    return {
        **material,
        "receipt_id": "gjiifav1:repair-receipt:" + canonical_json_sha256_v1(material),
    }


def _apply_authenticated_source_repairs_v1(
    *,
    regions: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    pages = {
        version_id: canonical_clone_v1(page) for version_id, page in page_json_by_version.items()
    }
    region_keys = {
        (
            region.get("page_json_version_id"),
            region.get("physical_page"),
            region.get("section_id"),
            region.get("table_id"),
        ): region
        for region in regions
    }
    receipts = []
    overlay = compiled_specs.get("interest_income_source_repair_overlay")
    if type(overlay) is not dict:
        raise _error("interest-income compiled source-repair overlay is invalid")
    for repair in overlay["repairs"]:
        key = (
            repair["page_json_version_id"],
            repair["physical_page"],
            repair["section_id"],
            repair["table_id"],
        )
        region = region_keys.get(key)
        if region is None:
            continue
        if (
            region.get("source_logical_name") != repair["source_logical_name"]
            or region.get("source_sha256") != repair["source_sha256"]
        ):
            raise _error("interest-income source-repair source identity drifted")
        base_page = page_json_by_version.get(repair["page_json_version_id"])
        if (
            type(base_page) is not dict
            or canonical_json_sha256_v1(base_page) != repair["base_page_json_sha256"]
        ):
            raise _error("interest-income source-repair base page drifted")
        _base_section, base_table = _region_table(page_json_by_version, region)
        if canonical_json_sha256_v1(base_table) != repair["base_table_sha256"]:
            raise _error("interest-income source-repair base table drifted")
        _section, table = _region_table(pages, region)
        rows = table.get("rows")
        columns = table.get("columns")
        if type(rows) is not list or type(columns) is not list:
            raise _error("interest-income source-repair table axes are invalid")
        for cell in repair["cell_repairs"]:
            row_index = int(cell["row_id"][1:]) - 1
            column_index = cell["column_ordinal"] - 1
            if not (0 <= row_index < len(rows) and 0 <= column_index < len(columns)):
                raise _error("interest-income source-repair cell is outside its table")
            row = rows[row_index]
            values = row.get("values_exact") if type(row) is dict else None
            if (
                type(row) is not dict
                or type(columns[column_index]) is not dict
                or columns[column_index].get("value_kind") != "MONEY"
                or type(values) is not list
                or len(values) != len(columns)
                or row.get("row_kind") != cell["row_kind"]
                or row.get("label_exact") != cell["row_label_exact"]
                or not same_typed_json_v1(
                    row.get("hierarchy_path_exact"),
                    cell["row_hierarchy_path_exact"],
                )
                or not same_typed_json_v1(values[column_index], cell["original_value_exact"])
            ):
                raise _error("interest-income source-repair cell binding drifted")
            values[column_index] = cell["replacement_value_exact"]
        receipts.append(_repair_receipt(repair=repair, compiled_specs=compiled_specs))
    receipts.sort(key=lambda item: item["repair_id"])
    return pages, receipts


def _normalize_governed_duration_headers_v1(
    *,
    pages: dict[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    receipts = []
    for region in regions:
        _section, table = _region_table(pages, region)
        columns = table.get("columns")
        money = [
            (ordinal, column)
            for ordinal, column in enumerate(columns if type(columns) is list else [], start=1)
            if type(column) is dict and column.get("value_kind") == "MONEY"
        ]
        if len(money) != 2:
            continue
        paths = [column.get("header_path_exact") for _ordinal, column in money]
        if not all(type(path) is list and len(path) == 2 for path in paths):
            continue
        parents = {_normalized(path[0]) for path in paths}
        leaves = [_normalized(path[1]) for path in paths]
        if parents != {"luy ke tu dau nam den cuoi ky nay"} or leaves != [
            "nam nay",
            "nam truoc",
        ]:
            continue
        before = canonical_clone_v1(paths)
        for (_ordinal, column), path in zip(money, paths, strict=True):
            column["header_path_exact"] = [path[1]]
        material = {
            "after_header_paths_exact": [[path[1]] for path in paths],
            "before_header_paths_exact": before,
            "locator": {
                key: region[key]
                for key in (
                    "page_json_version_id",
                    "physical_page",
                    "section_id",
                    "table_id",
                )
            },
            "rule": (
                "EXACT_SHARED_CUMULATIVE_DURATION_GOVERNOR_REMOVED_BEFORE_"
                "CURRENT_COMPARATIVE_LEAF_SEMANTICS"
            ),
        }
        receipts.append(
            {
                **material,
                "receipt_id": "gjiifav1:period:" + canonical_json_sha256_v1(material),
            }
        )
    return receipts


def _money_column_ordinals(table: Mapping[str, Any]) -> list[int]:
    columns = table.get("columns")
    return [
        ordinal
        for ordinal, column in enumerate(columns if type(columns) is list else [], start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]


def _observed_vector(row: Mapping[str, Any], money_ordinals: Sequence[int]) -> list[int] | None:
    values = row.get("values_exact")
    if type(values) is not list or any(ordinal > len(values) for ordinal in money_ordinals):
        return None
    cells = [_source_money(values[ordinal - 1]) for ordinal in money_ordinals]
    coefficients = [cell["coefficient"] for cell in cells]
    return (
        coefficients if coefficients and all(type(value) is int for value in coefficients) else None
    )


def _target_family_total_vector(
    *,
    page: Mapping[str, Any],
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> tuple[list[int], dict[str, Any]] | None:
    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        page, section, table, compiled_specs=compiled_specs
    )
    money_ordinals = classification.get("money_column_ordinals")
    rows = table.get("rows")
    if type(money_ordinals) is not list or len(money_ordinals) != 2 or type(rows) is not list:
        return None
    total_rows = classification.get("total_rows", [])
    if type(total_rows) is not list:
        return None
    total_vectors = []
    for total in total_rows:
        ordinal = total.get("row_ordinal")
        if type(ordinal) is int and 1 <= ordinal <= len(rows):
            vector = _observed_vector(rows[ordinal - 1], money_ordinals)
            if vector is not None:
                total_vectors.append((ordinal, vector))
    if len(total_rows) == 1 and len(total_vectors) == 1:
        ordinal, vector = total_vectors[0]
        return vector, {
            "money_column_ordinals": money_ordinals,
            "row_ordinals": [ordinal],
            "source_kind": "UNIQUE_SOURCE_VISIBLE_TOTAL",
        }
    if total_rows:
        return None
    if classification.get("ambiguous_rows") or classification.get("unbound_money_row_ordinals"):
        return None

    validation_only = set(compiled_specs.get("validation_only_roles", []))
    root_roles = set(compiled_specs.get("root_component_roles", [])) - validation_only
    hits_by_role: dict[str, list[dict[str, Any]]] = {}
    for hit in classification.get("role_hits", []):
        if hit.get("role") in root_roles:
            hits_by_role.setdefault(hit["role"], []).append(hit)
    selected = []
    omitted_all_blank_roles = []
    for role, hits in hits_by_role.items():
        ranked = []
        for hit in hits:
            ordinal = hit.get("row_ordinal")
            if type(ordinal) is not int or not (1 <= ordinal <= len(rows)):
                continue
            row = rows[ordinal - 1]
            path = row.get("hierarchy_path_exact") if type(row) is dict else None
            depth = len(path) if type(path) is list else 10**6
            ranked.append((depth, ordinal, row))
        if not ranked:
            continue
        minimum = min(item[0] for item in ranked)
        shallow = [item for item in ranked if item[0] == minimum]
        if len(shallow) != 1:
            return None
        _depth, ordinal, row = shallow[0]
        values = row.get("values_exact") if type(row) is dict else None
        if type(values) is not list or any(ordinal > len(values) for ordinal in money_ordinals):
            return None
        cells = [_source_money(values[ordinal - 1]) for ordinal in money_ordinals]
        coefficients = [cell["coefficient"] for cell in cells]
        if all(value is None for value in coefficients):
            omitted_all_blank_roles.append(role)
            continue
        if not all(type(value) is int for value in coefficients):
            return None
        vector = coefficients
        selected.append((role, ordinal, vector))
    if len(selected) < 2:
        return None
    vector = [sum(item[2][lane] for item in selected) for lane in range(2)]
    return vector, {
        "money_column_ordinals": money_ordinals,
        "omitted_all_blank_roles": sorted(omitted_all_blank_roles),
        "roles": sorted(item[0] for item in selected),
        "row_ordinals": sorted(item[1] for item in selected),
        "source_kind": "COMPLETE_SHALLOW_DECLARED_ROOT_COMPONENT_SUM",
    }


def _primary_statement_explicit_unit_axis(
    pages: Mapping[str, dict[str, Any]], compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    evidence = []
    for page_ordinal, (version_id, page) in enumerate(pages.items(), start=1):
        if page.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
            continue
        for section_ordinal, section in enumerate(page.get("sections") or [], start=1):
            if type(section) is not dict:
                continue
            for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
                if type(table) is not dict:
                    continue
                axis = _unit_axis(
                    table,
                    compiled_specs=compiled_specs,
                    document_unit_context=None,
                )
                if axis.get("complete"):
                    evidence.append(
                        {
                            "canonical_unit": axis["canonical_unit"],
                            "page_json_version_id": version_id,
                            "page_ordinal": page_ordinal,
                            "section_id": f"s{section_ordinal}",
                            "source": axis.get("source"),
                            "table_id": f"t{table_ordinal}",
                        }
                    )
    return evidence


def _primary_statement_interest_income_roots(
    pages: Mapping[str, dict[str, Any]], compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    owner_aliases = {
        _normalized(alias) for alias in compiled_specs["topology"]["parent"]["aliases"]
    }
    explicit_units = _primary_statement_explicit_unit_axis(pages, compiled_specs)
    result = []
    for page_ordinal, (version_id, page) in enumerate(pages.items(), start=1):
        if page.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
            continue
        for section_ordinal, section in enumerate(page.get("sections") or [], start=1):
            if type(section) is not dict:
                continue
            for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
                if type(table) is not dict:
                    continue
                money_ordinals = _money_column_ordinals(table)
                if len(money_ordinals) < 2:
                    continue
                local_axis = _unit_axis(
                    table,
                    compiled_specs=compiled_specs,
                    document_unit_context=None,
                )
                unit = local_axis.get("canonical_unit") if local_axis.get("complete") else None
                unit_evidence = None
                if unit is None:
                    distances = [
                        abs(item["page_ordinal"] - page_ordinal)
                        for item in explicit_units
                        if abs(item["page_ordinal"] - page_ordinal) <= 1
                    ]
                    if distances:
                        minimum = min(distances)
                        nearest = [
                            item
                            for item in explicit_units
                            if abs(item["page_ordinal"] - page_ordinal) == minimum
                        ]
                        units = {item["canonical_unit"] for item in nearest}
                        if len(units) == 1:
                            unit = next(iter(units))
                            unit_evidence = canonical_clone_v1(nearest)
                if unit is None:
                    continue
                rows = table.get("rows")
                for row_ordinal, row in enumerate(rows if type(rows) is list else [], start=1):
                    if type(row) is not dict:
                        continue
                    folded = _without_leading_ordinal(_normalized(row.get("label_exact")))
                    if folded not in owner_aliases:
                        continue
                    values = row.get("values_exact")
                    if type(values) is not list:
                        continue
                    coefficients = []
                    complete = True
                    for ordinal in money_ordinals:
                        if ordinal > len(values):
                            complete = False
                            break
                        cell = _source_money(values[ordinal - 1])
                        if type(cell["coefficient"]) is not int:
                            complete = False
                            break
                        coefficients.append(cell["coefficient"])
                    if not complete:
                        continue
                    result.append(
                        {
                            "canonical_unit": unit,
                            "coefficients": coefficients,
                            "local_unit_axis": canonical_clone_v1(local_axis),
                            "money_column_ordinals": money_ordinals,
                            "page_json_version_id": version_id,
                            "page_ordinal": page_ordinal,
                            "row_ordinal": row_ordinal,
                            "section_id": f"s{section_ordinal}",
                            "table_id": f"t{table_ordinal}",
                            "unit_adjacency_evidence": unit_evidence,
                        }
                    )
    return result


def _bind_exact_primary_statement_units_v1(
    *,
    pages: dict[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    roots = _primary_statement_interest_income_roots(pages, compiled_specs)
    receipts = []
    for region in regions:
        section, table = _region_table(pages, region)
        local_axis = _unit_axis(
            table,
            compiled_specs=compiled_specs,
            document_unit_context=None,
        )
        if local_axis.get("complete") or local_axis.get("evidence"):
            continue
        target = _target_family_total_vector(
            page=pages[region["page_json_version_id"]],
            section=section,
            table=table,
            compiled_specs=compiled_specs,
        )
        if target is None:
            continue
        target_vector, target_receipt = target
        matches = []
        for root in roots:
            coefficients = root["coefficients"]
            slices = [
                coefficients[start : start + len(target_vector)]
                for start in range(len(coefficients) - len(target_vector) + 1)
            ]
            if target_vector in slices:
                matches.append(root)
        units = {item["canonical_unit"] for item in matches}
        if len(units) != 1:
            continue
        canonical_unit = next(iter(units))
        table["unit_exact"] = "Triệu đồng" if canonical_unit == "MILLION_VND" else "VND"
        material = {
            "canonical_unit": canonical_unit,
            "matched_primary_roots": canonical_clone_v1(matches),
            "rule": (
                "UNITLESS_INTEREST_INCOME_NOTE_VISIBLE_TOTAL_OR_COMPLETE_SHALLOW_"
                "COMPONENT_SUM_EQUALS_ONE_CANONICAL_UNIT_PRIMARY_STATEMENT_ROOT_"
                "CONTIGUOUS_PERIOD_VECTOR_NO_MAGNITUDE_INFERENCE"
            ),
            "target_locator": {
                key: region[key]
                for key in (
                    "page_json_version_id",
                    "physical_page",
                    "section_id",
                    "table_id",
                )
            },
            "target_unit_before_exact": None,
            "target_unit_exact": table["unit_exact"],
            "target_vector": target_vector,
            "target_vector_receipt": target_receipt,
        }
        receipts.append(
            {
                **material,
                "receipt_id": "gjiifav1:unit:" + canonical_json_sha256_v1(material),
            }
        )
    return receipts


def _reseal_candidate(
    candidate: dict[str, Any],
    *,
    continuation_receipts: Sequence[Mapping[str, Any]],
    source_repair_receipts: Sequence[Mapping[str, Any]],
    period_receipts: Sequence[Mapping[str, Any]],
    unit_receipts: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        not continuation_receipts
        and not source_repair_receipts
        and not period_receipts
        and not unit_receipts
    ):
        return candidate
    material = {
        "adapter_format_version": ADAPTER_FORMAT_VERSION,
        "one_sided_continuation_receipts": canonical_clone_v1(list(continuation_receipts)),
        "period_normalization_receipts": canonical_clone_v1(list(period_receipts)),
        "shared_engine_claim_boundary": SHARED_CLAIM_BOUNDARY,
        "source_repair_overlay_id": compiled_specs["interest_income_source_repair_overlay"][
            "overlay_id"
        ],
        "source_repair_receipts": canonical_clone_v1(list(source_repair_receipts)),
        "source_repair_spec_sha256": compiled_specs["interest_income_source_repair_spec_sha256"],
        "unit_corroboration_receipts": canonical_clone_v1(list(unit_receipts)),
    }
    candidate["claim_boundary"] = CLAIM_BOUNDARY
    candidate["closure_receipt"]["interest_income_adapter_receipt"] = {
        **material,
        "adapter_receipt_id": "gjiifav1:receipt:" + canonical_json_sha256_v1(material),
    }
    candidate_material = {key: candidate[key] for key in candidate if key != "candidate_id"}
    candidate["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        candidate_material
    )
    return candidate


def evaluate_gemini_json_interest_income_family_cluster_v1(
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate Family 28 after only exact, replayable source normalisation."""

    if compiled_specs.get("topology", {}).get("family_id") != FAMILY_ID:
        raise _error("interest-income adapter received another family")
    expected_receipt = build_gemini_json_interest_income_region_query_receipt_v1(regions)
    if type(query_receipt) is not dict or not same_typed_json_v1(query_receipt, expected_receipt):
        raise _error("interest-income query receipt does not bind exact fragments")
    region_axis = expected_receipt["region_axis"]
    pages, source_repairs = _apply_authenticated_source_repairs_v1(
        regions=region_axis,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
    )
    continuation_receipts = _apply_one_sided_continuation_normalization_v1(
        pages=pages,
        regions=region_axis,
        compiled_specs=compiled_specs,
    )
    period_receipts = _normalize_governed_duration_headers_v1(
        pages=pages,
        regions=region_axis,
    )
    unit_receipts = _bind_exact_primary_statement_units_v1(
        pages=pages,
        regions=region_axis,
        compiled_specs=compiled_specs,
    )
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=region_axis,
        page_json_by_version=pages,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    return _reseal_candidate(
        candidate,
        continuation_receipts=continuation_receipts,
        source_repair_receipts=source_repairs,
        period_receipts=period_receipts,
        unit_receipts=unit_receipts,
        compiled_specs=compiled_specs,
    )


def validate_gemini_json_interest_income_family_candidate_replay_v1(
    value: Any,
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    expected = evaluate_gemini_json_interest_income_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if type(value) is not dict or not same_typed_json_v1(value, expected):
        raise _error("interest-income candidate replay drifted")
    return expected
