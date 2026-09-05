"""Family-31 adapter for an exact primary-statement FX/gold result.

The shared multi-table evaluator remains authoritative for classification,
period and unit axes, source arithmetic, mappings, and accounting closure.
This adapter only recovers one source-visible family-root row from a primary
income statement when the document has no note candidate.  The projection is
structural: it never chooses, completes, scales, or infers a numeric value.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import (
    _money,
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
    _local_equation,
    _multitable_lane_axis,
    _unit_axis,
    build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    classify_gemini_json_multitable_hierarchical_table_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
    validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    validate_gemini_json_multitable_hierarchical_sweep_query_bindings_v1,
)
from bctc_ai.evaluation.gemini_json_other_long_term_investments_family_v1 import (
    _row_local_record,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FAMILY_ID = "FX_GOLD_ACTIVITY"
ADAPTER_FORMAT_VERSION = "GEMINI_JSON_FX_GOLD_ACTIVITY_FAMILY_ADAPTER_V1"
PRIMARY_ROOT_QUERY_RECEIPT_FORMAT_VERSION = (
    "GEMINI_JSON_FX_GOLD_ACTIVITY_PRIMARY_ROOT_QUERY_RECEIPT_V1"
)
SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION = (
    "GEMINI_JSON_FX_GOLD_ACTIVITY_AUTHENTICATED_SOURCE_REPAIR_ARTIFACT_V1"
)
SOURCE_REPAIR_POLICY = (
    "TRANSCRIBE_ONLY_AUTHENTICATED_PDF_VISIBLE_DASH_NO_EQUATION_BACKSOLVE_"
    "NO_BLANK_TO_ZERO_NO_PROVIDER"
)
DEFAULT_SOURCE_REPAIR_PATH = "data/registered/gemini_json_fx_gold_activity_source_repairs_v1.json"
ADAPTER_CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_FAMILY31_EXACT_UNSHADOWED_PRIMARY_"
    "INCOME_STATEMENT_SOURCE_ROOT_STRUCTURAL_PROJECTION_GENERIC_ROLE_PERIOD_"
    "UNIT_OR_UNIQUE_DOCUMENT_PRIMARY_STATEMENT_EXPLICIT_UNIT_CONTEXT_AND_"
    "ACCOUNTING_CLOSURE_SCHEMA_MAPPING_PROPOSAL_ONLY_NO_SOURCE_"
    "MUTATION_OCR_PROVIDER_BANK_FILE_YEAR_PAGE_VALUE_ROUTING_NULL_ZERO_"
    "BACKSOLVE_CANONICAL_OR_EXPORT_AUTHORITY"
)


class GeminiJsonFxGoldActivityFamilyV1Error(ValueError):
    """Family-31 adapter input, receipt, or replay drifted."""


def _error(message: str) -> GeminiJsonFxGoldActivityFamilyV1Error:
    return GeminiJsonFxGoldActivityFamilyV1Error(message)


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_DOCUMENT_ID = re.compile(r"gfpstorev1:document:[0-9a-f]{64}\Z")
_PAGE_ID = re.compile(r"gfpstorev1:page:[0-9a-f]{64}\Z")
_PAGE_VERSION_ID = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_RUN_ID = re.compile(r"gfpstorev1:run:[0-9a-f]{64}\Z")
_REPAIR_ID = re.compile(r"gjfgaasrv1:repair:[0-9a-f]{64}\Z")
_OVERLAY_ID = re.compile(r"gjfgaasrv1:overlay:[0-9a-f]{64}\Z")


def _load_default_source_repair_artifact_v1() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[3] / DEFAULT_SOURCE_REPAIR_PATH
    try:
        return json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("FX/gold source-repair artifact is absent or invalid") from exc


def _repair_bbox_v1(value: Any, *, width: int, height: int, label: str) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or not (0 <= value[0] < value[2] <= width)
        or not (0 <= value[1] < value[3] <= height)
    ):
        raise _error(f"FX/gold source-repair {label} is invalid")
    return list(value)


def _compile_authenticated_source_repair_artifact_v1(value: Any) -> dict[str, Any]:
    """Validate the byte- and image-bound PDF dash transcription registry."""

    if (
        type(value) is not dict
        or set(value) != {"family_id", "format_version", "overlay_id", "repairs", "review_policy"}
        or value.get("family_id") != FAMILY_ID
        or value.get("format_version") != SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION
        or value.get("review_policy") != SOURCE_REPAIR_POLICY
        or type(value.get("repairs")) is not list
        or not value["repairs"]
    ):
        raise _error("FX/gold source-repair artifact is invalid")
    repair_fields = {
        "base_page_json_sha256",
        "base_page_json_version_id",
        "cell_repairs",
        "effective_page_json_sha256",
        "extraction_run_id",
        "repair_id",
        "repair_reason",
        "source_binding",
        "stored_canonical_json_sha256",
        "table_ref",
        "visual_evidence",
    }
    source_fields = {
        "document_id",
        "image_sha256",
        "image_size_bytes",
        "media_type",
        "page_id",
        "physical_page",
        "pixel_height",
        "pixel_width",
        "render_dpi",
        "source_logical_name",
        "source_sha256",
        "source_size_bytes",
    }
    table_fields = {
        "base_table_sha256",
        "effective_table_sha256",
        "section_id",
        "table_id",
    }
    visual_fields = {
        "evidence_kind",
        "render_mode",
        "reviewed_utc_date",
        "table_crop_bbox_pixels_xyxy",
        "table_crop_rgb_sha256",
    }
    cell_fields = {
        "after_exact",
        "before_exact",
        "cell_id",
        "column_header_path_exact",
        "crop_bbox_pixels_xyxy",
        "crop_rgb_sha256",
        "row_hierarchy_path_exact",
        "row_label_exact",
        "visual_state",
    }
    checked = []
    seen_versions: set[str] = set()
    seen_ids: set[str] = set()
    for raw in value["repairs"]:
        if type(raw) is not dict or set(raw) != repair_fields:
            raise _error("FX/gold source-repair fields drifted")
        repair = canonical_clone_v1(raw)
        source = repair.get("source_binding")
        if type(source) is not dict or set(source) != source_fields:
            raise _error("FX/gold source-repair source fields drifted")
        if (
            type(source.get("source_logical_name")) is not str
            or not source["source_logical_name"].strip()
            or _SHA256.fullmatch(source.get("source_sha256", "")) is None
            or type(source.get("source_size_bytes")) is not int
            or source["source_size_bytes"] <= 0
            or _DOCUMENT_ID.fullmatch(source.get("document_id", "")) is None
            or _PAGE_ID.fullmatch(source.get("page_id", "")) is None
            or type(source.get("physical_page")) is not int
            or source["physical_page"] <= 0
            or _SHA256.fullmatch(source.get("image_sha256", "")) is None
            or type(source.get("image_size_bytes")) is not int
            or source["image_size_bytes"] <= 0
            or type(source.get("pixel_width")) is not int
            or source["pixel_width"] <= 0
            or type(source.get("pixel_height")) is not int
            or source["pixel_height"] <= 0
            or source.get("render_dpi") != 300
            or source.get("media_type") != "image/png"
        ):
            raise _error("FX/gold source-repair source binding is invalid")
        expected_document_id = "gfpstorev1:document:" + canonical_json_sha256_v1(
            {
                "source_logical_name": source["source_logical_name"],
                "source_sha256": source["source_sha256"],
                "source_size_bytes": source["source_size_bytes"],
            }
        )
        expected_page_id = "gfpstorev1:page:" + canonical_json_sha256_v1(
            {
                "document_id": expected_document_id,
                "image_sha256": source["image_sha256"],
                "image_size_bytes": source["image_size_bytes"],
                "media_type": source["media_type"],
                "physical_page": source["physical_page"],
                "pixel_height": source["pixel_height"],
                "pixel_width": source["pixel_width"],
                "render_dpi": source["render_dpi"],
            }
        )
        if source["document_id"] != expected_document_id or source["page_id"] != expected_page_id:
            raise _error("FX/gold source-repair source identity does not replay")
        if (
            _SHA256.fullmatch(repair.get("base_page_json_sha256", "")) is None
            or _SHA256.fullmatch(repair.get("effective_page_json_sha256", "")) is None
            or _SHA256.fullmatch(repair.get("stored_canonical_json_sha256", "")) is None
            or _PAGE_VERSION_ID.fullmatch(repair.get("base_page_json_version_id", "")) is None
            or _RUN_ID.fullmatch(repair.get("extraction_run_id", "")) is None
            or repair["base_page_json_version_id"] in seen_versions
        ):
            raise _error("FX/gold source-repair page binding is invalid")
        expected_version_id = "gfpstorev1:json:" + canonical_json_sha256_v1(
            {
                "canonical_json_sha256": repair["stored_canonical_json_sha256"],
                "extraction_run_id": repair["extraction_run_id"],
                "page_id": source["page_id"],
            }
        )
        if repair["base_page_json_version_id"] != expected_version_id:
            raise _error("FX/gold source-repair page identity does not replay")
        seen_versions.add(repair["base_page_json_version_id"])
        table = repair.get("table_ref")
        if (
            type(table) is not dict
            or set(table) != table_fields
            or re.fullmatch(r"s[1-9][0-9]*", table.get("section_id", "")) is None
            or re.fullmatch(r"t[1-9][0-9]*", table.get("table_id", "")) is None
            or _SHA256.fullmatch(table.get("base_table_sha256", "")) is None
            or _SHA256.fullmatch(table.get("effective_table_sha256", "")) is None
        ):
            raise _error("FX/gold source-repair table binding is invalid")
        visual = repair.get("visual_evidence")
        if (
            type(visual) is not dict
            or set(visual) != visual_fields
            or visual.get("evidence_kind") != "AUTHENTICATED_MANUAL_VISUAL_TRANSCRIPTION"
            or visual.get("render_mode") != "PDF_PAGE_GET_PIXMAP_DPI_EXACT_RGB"
            or re.fullmatch(r"20\d{2}-[01]\d-[0-3]\d", visual.get("reviewed_utc_date", "")) is None
            or _SHA256.fullmatch(visual.get("table_crop_rgb_sha256", "")) is None
        ):
            raise _error("FX/gold source-repair visual evidence is invalid")
        table_bbox = _repair_bbox_v1(
            visual.get("table_crop_bbox_pixels_xyxy"),
            width=source["pixel_width"],
            height=source["pixel_height"],
            label="table crop",
        )
        cells = repair.get("cell_repairs")
        if type(cells) is not list or not cells:
            raise _error("FX/gold source-repair cell axis is invalid")
        seen_cells: set[str] = set()
        checked_cells = []
        for raw_cell in cells:
            if type(raw_cell) is not dict or set(raw_cell) != cell_fields:
                raise _error("FX/gold source-repair cell fields drifted")
            cell = canonical_clone_v1(raw_cell)
            cell_match = re.fullmatch(r"r([1-9][0-9]*):c([1-9][0-9]*)", cell.get("cell_id", ""))
            bbox = _repair_bbox_v1(
                cell.get("crop_bbox_pixels_xyxy"),
                width=source["pixel_width"],
                height=source["pixel_height"],
                label="cell crop",
            )
            if (
                cell_match is None
                or cell["cell_id"] in seen_cells
                or cell.get("before_exact") is not None
                or cell.get("after_exact") != "-"
                or cell.get("visual_state") != "DASH"
                or type(cell.get("row_label_exact")) is not str
                or not cell["row_label_exact"].strip()
                or type(cell.get("row_hierarchy_path_exact")) is not list
                or not cell["row_hierarchy_path_exact"]
                or any(
                    type(item) is not str or not item for item in cell["row_hierarchy_path_exact"]
                )
                or type(cell.get("column_header_path_exact")) is not list
                or not cell["column_header_path_exact"]
                or any(
                    type(item) is not str or not item for item in cell["column_header_path_exact"]
                )
                or _SHA256.fullmatch(cell.get("crop_rgb_sha256", "")) is None
                or not (
                    table_bbox[0] <= bbox[0] < bbox[2] <= table_bbox[2]
                    and table_bbox[1] <= bbox[1] < bbox[3] <= table_bbox[3]
                )
            ):
                raise _error("FX/gold source-repair cell is invalid")
            seen_cells.add(cell["cell_id"])
            checked_cells.append(cell)
        checked_cells.sort(
            key=lambda item: tuple(int(part[1:]) for part in item["cell_id"].split(":"))
        )
        if cells != checked_cells or repair.get("repair_reason") != (
            "VISIBLE_PDF_TRANSCRIPTION_MISMATCH"
        ):
            raise _error("FX/gold source-repair cell axis is unordered")
        expected_repair_id = "gjfgaasrv1:repair:" + canonical_json_sha256_v1(
            {key: repair[key] for key in repair if key != "repair_id"}
        )
        if (
            _REPAIR_ID.fullmatch(repair.get("repair_id", "")) is None
            or repair["repair_id"] != expected_repair_id
            or repair["repair_id"] in seen_ids
        ):
            raise _error("FX/gold source-repair identity does not replay")
        seen_ids.add(repair["repair_id"])
        checked.append(repair)
    checked.sort(
        key=lambda item: (
            item["source_binding"]["source_logical_name"],
            item["source_binding"]["physical_page"],
            int(item["table_ref"]["section_id"][1:]),
            int(item["table_ref"]["table_id"][1:]),
        )
    )
    if value["repairs"] != checked:
        raise _error("FX/gold source-repair axis is unordered")
    material = {
        "family_id": FAMILY_ID,
        "format_version": SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION,
        "repairs": checked,
        "review_policy": SOURCE_REPAIR_POLICY,
    }
    expected_overlay_id = "gjfgaasrv1:overlay:" + canonical_json_sha256_v1(material)
    if (
        _OVERLAY_ID.fullmatch(value.get("overlay_id", "")) is None
        or value["overlay_id"] != expected_overlay_id
    ):
        raise _error("FX/gold source-repair overlay identity does not replay")
    return {**material, "overlay_id": expected_overlay_id}


def compile_gemini_json_fx_gold_activity_family_specs_v1(
    topology_spec: Any,
    evaluation_spec: Any,
    schema_binding_spec: Any,
    source_repair_spec: Any | None = None,
) -> dict[str, Any]:
    """Compile Family 31 and mark the family-local adapter boundary."""

    compiled = compile_gemini_json_multitable_hierarchical_family_specs_v1(
        topology_spec, evaluation_spec, schema_binding_spec
    )
    if (
        compiled.get("topology", {}).get("family_id") != FAMILY_ID
        or compiled.get("schema", {}).get("family_id") != FAMILY_ID
        or compiled.get("family_root_population_policy") != "WHOLE_TABLE"
        or compiled.get("primary_statement_source_result_fallback_policy", "DISABLED") != "DISABLED"
        or {
            item.get("canonical_unit")
            for item in compiled.get("unit_bindings", [])
            if item.get("accepted") is True
        }
        != {"MILLION_VND", "VND"}
    ):
        raise _error("FX/gold declarative adapter boundary is invalid")
    raw_source_repairs = (
        _load_default_source_repair_artifact_v1()
        if source_repair_spec is None
        else source_repair_spec
    )
    compiled["fx_gold_activity_adapter_format_version"] = ADAPTER_FORMAT_VERSION
    compiled["fx_gold_activity_source_repair_overlay"] = (
        _compile_authenticated_source_repair_artifact_v1(raw_source_repairs)
    )
    compiled["fx_gold_activity_source_repair_spec_sha256"] = canonical_json_sha256_v1(
        raw_source_repairs
    )
    return compiled


def _apply_authenticated_source_repairs_v1(
    *,
    pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Apply only registered PDF-visible dash tokens to private page clones."""

    overlay = compiled_specs.get("fx_gold_activity_source_repair_overlay")
    if (
        type(overlay) is not dict
        or overlay.get("family_id") != FAMILY_ID
        or overlay.get("format_version") != SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION
        or type(overlay.get("repairs")) is not list
    ):
        raise _error("FX/gold source-repair overlay is not compiled")
    effective = {version_id: canonical_clone_v1(page) for version_id, page in pages.items()}
    receipts = []
    for repair in overlay["repairs"]:
        version_id = repair["base_page_json_version_id"]
        if version_id not in effective:
            continue
        page = effective[version_id]
        if canonical_json_sha256_v1(page) != repair["base_page_json_sha256"]:
            raise _error("FX/gold source-repair base page drifted")
        table_ref = repair["table_ref"]
        try:
            section = page["sections"][int(table_ref["section_id"][1:]) - 1]
            table = section["tables"][int(table_ref["table_id"][1:]) - 1]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise _error("FX/gold source-repair table does not resolve") from exc
        if (
            type(table) is not dict
            or canonical_json_sha256_v1(table) != table_ref["base_table_sha256"]
        ):
            raise _error("FX/gold source-repair base table drifted")
        for cell in repair["cell_repairs"]:
            match = re.fullmatch(r"r([1-9][0-9]*):c([1-9][0-9]*)", cell["cell_id"])
            if match is None:
                raise _error("FX/gold source-repair cell locator drifted")
            row_ordinal, column_ordinal = (int(value) for value in match.groups())
            try:
                row = table["rows"][row_ordinal - 1]
                column = table["columns"][column_ordinal - 1]
                before = row["values_exact"][column_ordinal - 1]
            except (KeyError, IndexError, TypeError) as exc:
                raise _error("FX/gold source-repair cell does not resolve") from exc
            if (
                type(row) is not dict
                or type(column) is not dict
                or not same_typed_json_v1(row.get("label_exact"), cell["row_label_exact"])
                or not same_typed_json_v1(
                    row.get("hierarchy_path_exact"),
                    cell["row_hierarchy_path_exact"],
                )
                or not same_typed_json_v1(
                    column.get("header_path_exact"),
                    cell["column_header_path_exact"],
                )
                or not same_typed_json_v1(before, cell["before_exact"])
            ):
                raise _error("FX/gold source-repair cell source drifted")
            row["values_exact"][column_ordinal - 1] = cell["after_exact"]
        if (
            canonical_json_sha256_v1(table) != table_ref["effective_table_sha256"]
            or canonical_json_sha256_v1(page) != repair["effective_page_json_sha256"]
        ):
            raise _error("FX/gold source-repair effective source drifted")
        receipts.append(canonical_clone_v1(repair))
    return effective, receipts


def build_gemini_json_fx_gold_activity_region_query_receipt_v1(
    regions: Any,
) -> dict[str, Any]:
    """Seal the unchanged shared region axis."""

    return build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)


def _money_ordinals(table: Mapping[str, Any]) -> list[int]:
    columns = table.get("columns")
    if type(columns) is not list:
        return []
    return [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]


def _root_alias(value: Any, *, compiled_specs: Mapping[str, Any]) -> str | None:
    folded = _without_leading_ordinal(_normalized(value))
    matches = [
        _normalized(alias)
        for alias in compiled_specs["topology"]["parent"]["aliases"]
        if folded == _normalized(alias)
    ]
    return matches[0] if len(matches) == 1 else None


def _query_owner_alias(value: Any, *, compiled_specs: Mapping[str, Any]) -> str | None:
    folded = _without_leading_ordinal(_normalized(value))
    matches = [
        alias for alias in compiled_specs["query_policy"]["owner_aliases"] if folded == alias
    ]
    return matches[0] if len(matches) == 1 else None


def _table_from_inventory(
    *,
    item: Mapping[str, Any],
    page_json_by_version: Mapping[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    page = page_json_by_version.get(item.get("page_json_version_id"))
    if type(page) is not dict:
        return None
    try:
        section = page["sections"][int(item["section_id"][1:]) - 1]
        table = section["tables"][int(item["table_id"][1:]) - 1]
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    if type(section) is not dict or type(table) is not dict:
        return None
    return section, table


def _direct_note_candidate_axis(
    *,
    inventory: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Fail closed when any untyped note exposes a family role or root."""

    candidates = []
    for item in inventory:
        classification = item.get("classification") if type(item) is dict else None
        resolved = (
            _table_from_inventory(item=item, page_json_by_version=page_json_by_version)
            if type(classification) is dict
            else None
        )
        page = page_json_by_version.get(item.get("page_json_version_id"))
        if resolved is None or type(page) is not dict:
            continue
        section, _table = resolved
        role_hits = classification.get("role_hits")
        observed_roles = (
            sorted(
                {
                    hit.get("role")
                    for hit in role_hits
                    if type(hit) is dict and type(hit.get("role")) is str
                }
            )
            if type(role_hits) is list
            else []
        )
        substantive_roles = set(observed_roles) - {"INCOME_OTHER", "EXPENSE_OTHER"}
        if (
            page.get("status") == "PRIMARY_FINANCIAL_STATEMENT"
            or section.get("content_kind") != "FINANCIAL_NOTE"
            or classification.get("typed_control_disposition") is not None
            or not (substantive_roles or classification.get("family_root_row_ordinals"))
        ):
            continue
        candidates.append(
            {
                "classification_id": classification.get("classification_id"),
                "family_root_row_ordinals": canonical_clone_v1(
                    classification.get("family_root_row_ordinals", [])
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
                "observed_roles": observed_roles,
            }
        )
    return candidates


def _unique_primary_statement_unit_context_v1(
    *,
    page_json_by_version: Mapping[str, dict[str, Any]],
    target_locator: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Bind one explicit unit shared by every unit-bearing primary table.

    Tables with no visible unit evidence do not vote.  Any conflicting,
    undeclared, or internally incomplete unit evidence vetoes the context.
    This is document/source provenance only: values, magnitude, and distance
    never participate.
    """

    evidence_axis = []
    for page_json_version_id, page in sorted(page_json_by_version.items()):
        if type(page) is not dict or page.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
            continue
        sections = page.get("sections")
        for section_ordinal, section in enumerate(
            sections if type(sections) is list else [], start=1
        ):
            if (
                type(section) is not dict
                or section.get("content_kind") != "PRIMARY_STATEMENT"
                or type(section.get("tables")) is not list
            ):
                continue
            for table_ordinal, table in enumerate(section["tables"], start=1):
                if type(table) is not dict or not _money_ordinals(table):
                    continue
                locator = {
                    "page_json_version_id": page_json_version_id,
                    "section_id": f"s{section_ordinal}",
                    "table_id": f"t{table_ordinal}",
                }
                if all(
                    locator.get(key) == target_locator.get(key)
                    for key in ("page_json_version_id", "section_id", "table_id")
                ):
                    continue
                unit_axis = _unit_axis(table, compiled_specs=compiled_specs)
                visible_evidence = [
                    *unit_axis.get("evidence", []),
                    *unit_axis.get("undeclared_evidence", []),
                ]
                if not visible_evidence:
                    continue
                if (
                    unit_axis.get("complete") is not True
                    or unit_axis.get("canonical_unit") not in {"MILLION_VND", "VND"}
                    or unit_axis.get("undeclared_evidence")
                ):
                    return None
                evidence_axis.append(
                    {
                        "canonical_unit": unit_axis["canonical_unit"],
                        "locator": locator,
                        "statement_type": section.get("statement_type"),
                        "unit_axis": canonical_clone_v1(unit_axis),
                    }
                )
    units = {item["canonical_unit"] for item in evidence_axis}
    if len(units) != 1:
        return None
    canonical_unit = next(iter(units))
    exact_sources = sorted(
        {
            evidence["source_exact"]
            for item in evidence_axis
            for evidence in item["unit_axis"]["evidence"]
            if evidence.get("canonical_unit") == canonical_unit
            and type(evidence.get("source_exact")) is str
            and evidence["source_exact"].strip()
        }
    )
    if not exact_sources:
        return None
    material = {
        "canonical_unit": canonical_unit,
        "evidence_axis": evidence_axis,
        "rule": (
            "EVERY_UNIT_BEARING_PRIMARY_STATEMENT_TABLE_IN_THE_SAME_DOCUMENT_"
            "HAS_ONE_COMPLETE_ACCEPTED_CANONICAL_UNIT_WHILE_UNIT_ABSENT_TABLES_"
            "DO_NOT_VOTE_NO_VALUE_MAGNITUDE_DISTANCE_OR_ROUNDING"
        ),
        "source_unit_exact": exact_sources[0],
        "target_locator": canonical_clone_v1(dict(target_locator)),
    }
    return {
        **material,
        "primary_statement_unit_context_receipt_id": (
            "gjfgapsucrv1:receipt:" + canonical_json_sha256_v1(material)
        ),
    }


def _primary_statement_exact_root_projection_v1(
    *,
    region: Mapping[str, Any],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]] | None:
    """Project one exact two-period income-statement family-root row."""

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
        or section.get("statement_type") != "INCOME_STATEMENT"
    ):
        return None
    source_money_ordinals = _money_ordinals(table)
    period_axis = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
    money_ordinals = period_axis.get("money_column_ordinals")
    rows = table.get("rows")
    if (
        type(money_ordinals) is not list
        or len(money_ordinals) != 2
        or not set(money_ordinals).issubset(source_money_ordinals)
        or period_axis.get("complete") is not True
        or type(rows) is not list
    ):
        return None
    matches = []
    for row_ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict:
            continue
        alias = _root_alias(row.get("label_exact"), compiled_specs=compiled_specs)
        if alias is None:
            continue
        values = row.get("values_exact")
        hierarchy = row.get("hierarchy_path_exact")
        if (
            row.get("row_kind") not in {"ITEM", "GROUP", "SUBTOTAL", "TOTAL"}
            or type(values) is not list
            or any(ordinal > len(values) for ordinal in money_ordinals)
            or all(values[ordinal - 1] is None for ordinal in money_ordinals)
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
    target_unit_axis = _unit_axis(table, compiled_specs=compiled_specs)
    unit_context_receipt = None
    after_table_unit_exact = table.get("unit_exact")
    if target_unit_axis.get("complete") is not True:
        if target_unit_axis.get("evidence") or target_unit_axis.get("undeclared_evidence"):
            return None
        unit_context_receipt = _unique_primary_statement_unit_context_v1(
            page_json_by_version=page_json_by_version,
            target_locator=locator,
            compiled_specs=compiled_specs,
        )
        if unit_context_receipt is None:
            return None
        after_table_unit_exact = unit_context_receipt["source_unit_exact"]
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
            "after_table_unit_exact": after_table_unit_exact,
            "before_page_status": page["status"],
            "before_row_kind": source_row["row_kind"],
            "before_section_content_kind": section["content_kind"],
            "before_section_statement_type": section["statement_type"],
            "before_table_continuation": table.get("continuation"),
            "before_table_unit_exact": table.get("unit_exact"),
        },
        "root_alias_normalized": alias,
        "root_row": {
            "hierarchy_path_exact": canonical_clone_v1(source_row["hierarchy_path_exact"]),
            "label_exact": source_row["label_exact"],
            "row_kind": source_row["row_kind"],
            "row_ordinal": row_ordinal,
            "values_exact": canonical_clone_v1(source_row["values_exact"]),
        },
        "rule": (
            "ONE_EXACT_DECLARED_FAMILY_ROOT_ROW_IN_ONE_PRIMARY_INCOME_STATEMENT_"
            "TABLE_ONLY_WHEN_NO_UNTYPED_NON_PRIMARY_DIRECT_FAMILY_CANDIDATE_"
            "PROJECTED_WITHOUT_VALUE_SELECTION_OR_BLANK_COMPLETION"
        ),
        "source_logical_name": region["source_logical_name"],
        "source_money_column_ordinals": source_money_ordinals,
        "source_sha256": region["source_sha256"],
        "table_unit_exact": table.get("unit_exact"),
        "target_unit_axis": canonical_clone_v1(target_unit_axis),
        "unit_context_receipt": canonical_clone_v1(unit_context_receipt),
    }
    receipt = {
        **material,
        "primary_root_query_receipt_id": (
            "gjfgaprqrv1:receipt:" + canonical_json_sha256_v1(material)
        ),
    }
    pages = {
        version_id: canonical_clone_v1(source_page)
        for version_id, source_page in page_json_by_version.items()
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
    projected_table["unit_exact"] = after_table_unit_exact
    return pages, receipt


def _primary_statement_exact_root_query_recovery_v1(
    *,
    cluster: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    if cluster.get("status") != NOT_OBSERVED or cluster.get("reasons") != []:
        return None
    inventory = cluster.get("declared_money_table_inventory")
    if type(inventory) is not list:
        return None
    note_axis = _direct_note_candidate_axis(
        inventory=inventory,
        page_json_by_version=page_json_by_version,
    )
    if note_axis:
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
        if page.get("document_ordinal") == cluster.get("document_ordinal")
        and page.get("document_id") == cluster.get("document_id")
        and page.get("source_sha256") == cluster.get("source_sha256")
        and page.get("page_json_version_id") == item.get("page_json_version_id")
        and page.get("physical_page") == item.get("physical_page")
    ]
    if len(selected) != 1:
        return None
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
    classification = item["classification"]
    if (
        classification.get("family_root_row_ordinals") != [receipt["root_row"]["row_ordinal"]]
        or classification.get("money_column_ordinals") != receipt["source_money_column_ordinals"]
        or classification.get("ambiguous_rows") != []
    ):
        return None
    return region, receipt


def adapt_gemini_json_fx_gold_activity_indexed_query_evidence_v1(
    value: Any,
    *,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Recover only exact unshadowed primary income-statement roots."""

    evidence = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        value, compiled_specs=compiled_specs
    )
    clusters = []
    receipts = []
    for disposition in evidence["candidate_dispositions"]:
        cluster = canonical_clone_v1(disposition["cluster"])
        pages = page_json_by_document.get(cluster["document_ordinal"])
        recovered = (
            _primary_statement_exact_root_query_recovery_v1(
                cluster=cluster,
                selected_page_axis=evidence["selected_page_axis"],
                page_json_by_version=pages,
                compiled_specs=compiled_specs,
            )
            if type(pages) is dict
            else None
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
                        "SELECTED_PRIMARY_STATEMENT_EXACT_FAMILY_ROOT_AFTER_FAMILY31_RECEIPT"
                    )
            cluster["component_regions"] = [region]
            cluster["owner_receipt"] = canonical_clone_v1(receipt)
            cluster["reasons"] = []
            cluster["status"] = READY
            receipts.append(receipt)
        continuation_recovery = (
            _terminal_cong_query_recovery_v1(
                cluster=cluster,
                selected_page_axis=evidence["selected_page_axis"],
                pages=pages,
                compiled_specs=compiled_specs,
            )
            if type(pages) is dict
            else None
        )
        if continuation_recovery is not None:
            recovered_regions, receipt = continuation_recovery
            receiver = recovered_regions[-1]
            for item in cluster["declared_money_table_inventory"]:
                if (
                    item.get("page_json_version_id"),
                    item.get("section_id"),
                    item.get("table_id"),
                ) == (
                    receiver["page_json_version_id"],
                    receiver["section_id"],
                    receiver["table_id"],
                ):
                    item["disposition"] = (
                        "SELECTED_RECIPROCAL_TERMINAL_CONG_RECEIVER_AFTER_FAMILY31_RECEIPT"
                    )
            cluster["component_regions"] = recovered_regions
            cluster["owner_receipt"] = canonical_clone_v1(receipt)
            cluster["reasons"] = []
            cluster["status"] = READY
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
    return adapted, receipts


def _apply_primary_root_projection_receipt_v1(
    *,
    page_json_by_version: Mapping[str, dict[str, Any]],
    receipt: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    pages = {
        version_id: canonical_clone_v1(page) for version_id, page in page_json_by_version.items()
    }
    locator = receipt["locator"]
    page = pages.get(locator["page_json_version_id"])
    try:
        section = page["sections"][int(locator["section_id"][1:]) - 1]  # type: ignore[index]
        table = section["tables"][int(locator["table_id"][1:]) - 1]
        row_ordinal = receipt["root_row"]["row_ordinal"]
        row = table["rows"][row_ordinal - 1]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise _error("FX/gold primary-root projection locator drifted") from exc
    projection = receipt["projection"]
    root_row = receipt["root_row"]
    if (
        page.get("status") != projection["before_page_status"]
        or section.get("content_kind") != projection["before_section_content_kind"]
        or section.get("statement_type") != projection["before_section_statement_type"]
        or table.get("continuation") != projection["before_table_continuation"]
        or table.get("unit_exact") != projection["before_table_unit_exact"]
        or row.get("row_kind") != root_row["row_kind"]
        or row.get("label_exact") != root_row["label_exact"]
        or row.get("hierarchy_path_exact") != root_row["hierarchy_path_exact"]
        or row.get("values_exact") != root_row["values_exact"]
    ):
        raise _error("FX/gold primary-root projection source shape drifted")
    page["status"] = projection["after_page_status"]
    section["content_kind"] = projection["after_section_content_kind"]
    section["statement_type"] = projection["after_section_statement_type"]
    projected_row = canonical_clone_v1(row)
    projected_row["row_kind"] = projection["after_row_kind"]
    table["rows"] = [projected_row]
    table["continuation"] = projection["after_table_continuation"]
    table["unit_exact"] = projection["after_table_unit_exact"]
    return pages


def _restore_primary_root_mapping_source_refs_v1(
    candidate: dict[str, Any], *, receipt: Mapping[str, Any]
) -> None:
    original = receipt["root_row"]
    locator = receipt["locator"]
    for mapping in candidate.get("mappings", []):
        refs = mapping.get("source_refs") if type(mapping) is dict else None
        if type(refs) is not list or not refs:
            raise _error("FX/gold projected root mapping source is absent")
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
                raise _error("FX/gold projected root mapping source drifted")
            source_ref["row_id"] = f"r{original['row_ordinal']}"
            source_ref["row_kind"] = original["row_kind"]
            source_ref["row_ordinal"] = original["row_ordinal"]
        if mapping.get("row_id") == "r1":
            mapping["row_id"] = f"r{original['row_ordinal']}"
        material = {key: mapping[key] for key in mapping if key != "item_mapping_id"}
        mapping["item_mapping_id"] = "gjmthfmv1:item:" + canonical_json_sha256_v1(material)


def _restore_terminal_cong_projection_source_refs_v1(
    candidate: dict[str, Any], *, receipt: Mapping[str, Any]
) -> None:
    """Restore every projected row to its exact sender/receiver source row."""

    projections = receipt.get("row_projections")
    original_regions = receipt.get("original_regions")
    if type(projections) is not list or type(original_regions) is not list:
        raise _error("FX/gold terminal-Cộng projection receipt is invalid")
    by_projected_ordinal = {
        projection.get("projected_row_ordinal"): projection
        for projection in projections
        if type(projection) is dict
    }
    if len(by_projected_ordinal) != len(projections):
        raise _error("FX/gold terminal-Cộng projection row axis is duplicate")

    def original_region(projection: Mapping[str, Any]) -> dict[str, Any]:
        locator = projection.get("before_locator")
        matches = [
            region
            for region in original_regions
            if type(region) is dict
            and type(locator) is dict
            and all(
                region.get(field) == locator.get(field)
                for field in (
                    "page_json_version_id",
                    "physical_page",
                    "section_id",
                    "selected_page_ordinal",
                    "table_id",
                )
            )
        ]
        if len(matches) != 1:
            raise _error("FX/gold terminal-Cộng source locator drifted")
        return canonical_clone_v1(matches[0])

    for mapping in candidate.get("mappings", []):
        if type(mapping) is not dict:
            raise _error("FX/gold terminal-Cộng mapping is invalid")
        row_id = mapping.get("row_id")
        if type(row_id) is str and row_id.startswith("r") and row_id[1:].isdigit():
            projection = by_projected_ordinal.get(int(row_id[1:]))
            if projection is not None:
                mapping["row_id"] = f"r{projection['before_row_ordinal']}"
        for source_ref in mapping.get("source_refs", []):
            locator = source_ref.get("locator") if type(source_ref) is dict else None
            row_ordinal = source_ref.get("row_ordinal") if type(source_ref) is dict else None
            projection = by_projected_ordinal.get(row_ordinal)
            if (
                type(locator) is not dict
                or projection is None
                or any(
                    locator.get(field) != receipt["projected_region"].get(field)
                    for field in (
                        "page_json_version_id",
                        "physical_page",
                        "section_id",
                        "table_id",
                    )
                )
            ):
                raise _error("FX/gold terminal-Cộng projected source ref drifted")
            before_row = projection["before_row"]
            after_row = projection["after_row"]
            if (
                source_ref.get("label_exact") != after_row.get("label_exact")
                or source_ref.get("hierarchy_path_exact") != after_row.get("hierarchy_path_exact")
                or source_ref.get("row_kind") != after_row.get("row_kind")
            ):
                raise _error("FX/gold terminal-Cộng projected source row drifted")
            source_ref["locator"] = original_region(projection)
            source_ref["row_id"] = f"r{projection['before_row_ordinal']}"
            source_ref["row_ordinal"] = projection["before_row_ordinal"]
            source_ref["label_exact"] = before_row.get("label_exact")
            source_ref["hierarchy_path_exact"] = canonical_clone_v1(
                before_row.get("hierarchy_path_exact")
            )
            source_ref["row_kind"] = before_row.get("row_kind")
        material = {key: mapping[key] for key in mapping if key != "item_mapping_id"}
        mapping["item_mapping_id"] = "gjmthfmv1:item:" + canonical_json_sha256_v1(material)
    candidate["component_regions"] = canonical_clone_v1(original_regions)
    candidate["closure_receipt"]["query_receipt"] = canonical_clone_v1(
        receipt["original_query_receipt"]
    )


def _region_table(
    *, pages: Mapping[str, dict[str, Any]], region: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    page = pages.get(region.get("page_json_version_id"))
    try:
        section = page["sections"][int(region["section_id"][1:]) - 1]  # type: ignore[index]
        table = section["tables"][int(region["table_id"][1:]) - 1]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise _error("FX/gold region does not resolve one source table") from exc
    if type(section) is not dict or type(table) is not dict:
        raise _error("FX/gold region source table is invalid")
    return section, table


def _exact_root_vector(
    *,
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    lane_axis = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
    return _exact_root_vector_for_lane_axis(
        table=table,
        lane_axis=lane_axis,
        compiled_specs=compiled_specs,
    )


def _exact_root_vector_for_lane_axis(
    *,
    table: Mapping[str, Any],
    lane_axis: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Read one exact source root on an already authenticated lane axis."""

    money_ordinals = lane_axis.get("money_column_ordinals")
    rows = table.get("rows")
    if (
        lane_axis.get("complete") is not True
        or type(money_ordinals) is not list
        or len(money_ordinals) != 2
        or type(rows) is not list
    ):
        return None
    matches = []
    for row_ordinal, row in enumerate(rows, start=1):
        if (
            type(row) is not dict
            or _root_alias(row.get("label_exact"), compiled_specs=compiled_specs) is None
        ):
            continue
        values = row.get("values_exact")
        if type(values) is not list or any(ordinal > len(values) for ordinal in money_ordinals):
            return None
        cells = [_money(values[ordinal - 1]) for ordinal in money_ordinals]
        if any(type(cell.get("coefficient")) is not int for cell in cells):
            return None
        matches.append(
            {
                "lane_axis": canonical_clone_v1(lane_axis),
                "root_row": {
                    "hierarchy_path_exact": canonical_clone_v1(row.get("hierarchy_path_exact")),
                    "label_exact": row.get("label_exact"),
                    "row_kind": row.get("row_kind"),
                    "row_ordinal": row_ordinal,
                    "values_exact": canonical_clone_v1(values),
                },
                "vector": [cell["coefficient"] for cell in cells],
            }
        )
    return matches[0] if len(matches) == 1 else None


def _region_locator(region: Mapping[str, Any]) -> dict[str, Any]:
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


def _source_row_vector(
    row: Mapping[str, Any], *, money_ordinals: Sequence[int]
) -> list[int] | None:
    values = row.get("values_exact")
    if type(values) is not list or any(
        type(ordinal) is not int or ordinal < 1 or ordinal > len(values)
        for ordinal in money_ordinals
    ):
        return None
    cells = [_money(values[ordinal - 1]) for ordinal in money_ordinals]
    if any(type(cell.get("coefficient")) is not int for cell in cells):
        return None
    return [cell["coefficient"] for cell in cells]


def _leading_cong_total_ordinal_v1(
    table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> int | None:
    """Return a terminal leading ``Cộng`` only at a table/reset boundary."""

    rows = table.get("rows")
    if type(rows) is not list:
        return None
    matches = [
        ordinal
        for ordinal, row in enumerate(rows, start=1)
        if type(row) is dict
        and row.get("row_kind") == "TOTAL"
        and _normalized(row.get("label_exact")) == "cong"
    ]
    if not matches:
        return None
    total_ordinal = matches[0]
    if total_ordinal < len(rows):
        following = rows[total_ordinal]
        if type(following) is not dict:
            return None
        folded = _without_leading_ordinal(_normalized(following.get("label_exact")))
        reset_aliases = {
            _normalized(alias)
            for alias in compiled_specs["topology"].get("structural_reset_aliases", [])
        }
        if folded not in reset_aliases:
            return None
    return total_ordinal


def _terminal_cong_continuation_projection_v1(
    *,
    pages: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], dict[str, Any]] | None:
    """Join one exact KLB-style income/expense continuation on a clone."""

    if len(regions) != 2:
        return None
    ordered = sorted(
        regions,
        key=lambda item: (
            item.get("selected_page_ordinal", -1),
            item.get("physical_page", -1),
            item.get("section_id", ""),
            item.get("table_id", ""),
        ),
    )
    prior_region, receiver_region = ordered
    if (
        prior_region.get("document_id") != receiver_region.get("document_id")
        or prior_region.get("source_sha256") != receiver_region.get("source_sha256")
        or receiver_region.get("selected_page_ordinal")
        != prior_region.get("selected_page_ordinal", -2) + 1
        or receiver_region.get("physical_page") != prior_region.get("physical_page", -2) + 1
    ):
        return None
    try:
        prior_section, prior_table = _region_table(pages=pages, region=prior_region)
        receiver_section, receiver_table = _region_table(pages=pages, region=receiver_region)
    except GeminiJsonFxGoldActivityFamilyV1Error:
        return None
    if (
        prior_table.get("continuation") != "CONTINUES_ON_NEXT_PAGE"
        or receiver_table.get("continuation") not in {"CONTINUES_FROM_PREVIOUS_PAGE", "BOTH"}
        or _root_alias(prior_table.get("title_exact"), compiled_specs=compiled_specs) is None
    ):
        return None
    prior_axis = _multitable_lane_axis(prior_section, prior_table, compiled_specs=compiled_specs)
    receiver_axis = _multitable_lane_axis(
        receiver_section, receiver_table, compiled_specs=compiled_specs
    )
    prior_unit = _unit_axis(prior_table, compiled_specs=compiled_specs)
    receiver_unit = _unit_axis(receiver_table, compiled_specs=compiled_specs)
    if (
        prior_axis.get("complete") is not True
        or receiver_axis.get("complete") is not True
        or prior_axis.get("money_column_ordinals") != receiver_axis.get("money_column_ordinals")
        or prior_axis.get("lane_keys") != receiver_axis.get("lane_keys")
        or prior_axis.get("source_lane_keys") != receiver_axis.get("source_lane_keys")
        or prior_unit.get("complete") is not True
        or receiver_unit.get("complete") is not True
        or prior_unit.get("canonical_unit") != receiver_unit.get("canonical_unit")
        or prior_unit.get("canonical_unit") not in {"MILLION_VND", "VND"}
    ):
        return None
    total_ordinal = _leading_cong_total_ordinal_v1(receiver_table, compiled_specs=compiled_specs)
    receiver_rows = receiver_table.get("rows")
    prior_rows = prior_table.get("rows")
    if (
        total_ordinal is None
        or type(receiver_rows) is not list
        or type(prior_rows) is not list
        or not prior_rows
    ):
        return None
    receiver_prefix = canonical_clone_v1(receiver_table)
    receiver_prefix["rows"] = canonical_clone_v1(receiver_rows[:total_ordinal])
    try:
        prior_classification = classify_gemini_json_multitable_hierarchical_table_v1(
            pages[prior_region["page_json_version_id"]],
            prior_section,
            prior_table,
            compiled_specs=compiled_specs,
        )
        receiver_classification = classify_gemini_json_multitable_hierarchical_table_v1(
            pages[receiver_region["page_json_version_id"]],
            receiver_section,
            receiver_prefix,
            compiled_specs=compiled_specs,
        )
    except ValueError:
        return None
    prior_hits = prior_classification.get("role_hits")
    receiver_hits = receiver_classification.get("role_hits")
    if type(prior_hits) is not list or type(receiver_hits) is not list:
        return None
    prior_roles = {hit.get("role") for hit in prior_hits if type(hit) is dict}
    receiver_roles = {hit.get("role") for hit in receiver_hits if type(hit) is dict}
    if (
        "INCOME_PARENT" not in prior_roles
        or "EXPENSE_PARENT" not in receiver_roles
        or len(prior_roles) < 2
        or len(receiver_roles) < 2
        or any(type(role) is not str or not role.startswith("INCOME_") for role in prior_roles)
        or any(type(role) is not str or not role.startswith("EXPENSE_") for role in receiver_roles)
        or prior_classification.get("family_root_row_ordinals") not in (None, [])
        or receiver_classification.get("family_root_row_ordinals") not in (None, [])
        or prior_classification.get("unbound_money_row_ordinals") != []
        or receiver_classification.get("unbound_money_row_ordinals") != [total_ordinal]
    ):
        return None
    money_ordinals = prior_axis["money_column_ordinals"]

    def branch_vector(
        *,
        rows: Sequence[Mapping[str, Any]],
        hits: Sequence[Mapping[str, Any]],
        parent_role: str,
    ) -> tuple[list[int], list[dict[str, Any]]] | None:
        parent_hits = [hit for hit in hits if hit.get("role") == parent_role]
        child_hits = [hit for hit in hits if hit.get("role") != parent_role]
        if len(parent_hits) != 1 or not child_hits:
            return None
        parent_row = rows[parent_hits[0]["row_ordinal"] - 1]
        parent_values = parent_row.get("values_exact")
        if type(parent_values) is not list:
            return None
        child_axis = []
        vectors = []
        for hit in child_hits:
            row = rows[hit["row_ordinal"] - 1]
            vector = _source_row_vector(row, money_ordinals=money_ordinals)
            if vector is None:
                return None
            vectors.append(vector)
            child_axis.append(
                {
                    "role": hit["role"],
                    "row": canonical_clone_v1(row),
                    "row_ordinal": hit["row_ordinal"],
                    "vector": vector,
                }
            )
        vector = [sum(values) for values in zip(*vectors, strict=True)]
        parent_cells = [_money(parent_values[ordinal - 1]) for ordinal in money_ordinals]
        if not (
            all(cell.get("coefficient") is None for cell in parent_cells)
            or [cell.get("coefficient") for cell in parent_cells] == vector
        ):
            return None
        return vector, child_axis

    prior_branch = branch_vector(
        rows=prior_rows,
        hits=prior_hits,
        parent_role="INCOME_PARENT",
    )
    receiver_branch = branch_vector(
        rows=receiver_rows[:total_ordinal],
        hits=receiver_hits,
        parent_role="EXPENSE_PARENT",
    )
    total_row = receiver_rows[total_ordinal - 1]
    total_vector = _source_row_vector(total_row, money_ordinals=money_ordinals)
    if prior_branch is None or receiver_branch is None or total_vector is None:
        return None
    expected_total = [
        income + expense
        for income, expense in zip(prior_branch[0], receiver_branch[0], strict=True)
    ]
    if expected_total != total_vector:
        return None
    governors = [
        governor
        for governor in _primary_root_unit_governors(pages=pages, compiled_specs=compiled_specs)
        if governor["canonical_unit"] == prior_unit["canonical_unit"]
        and governor["vector"] == total_vector
    ]
    if len(governors) != 1:
        return None

    owner_label_exact = prior_table["title_exact"]
    projected_root = canonical_clone_v1(total_row)
    projected_root["label_exact"] = owner_label_exact
    projected_root["hierarchy_path_exact"] = [owner_label_exact]
    row_projections = []
    projected_rows = []
    for row_ordinal, row in enumerate(prior_rows, start=1):
        cloned = canonical_clone_v1(row)
        projected_rows.append(cloned)
        row_projections.append(
            {
                "after_row": canonical_clone_v1(cloned),
                "before_locator": _region_locator(prior_region),
                "before_row": canonical_clone_v1(row),
                "before_row_ordinal": row_ordinal,
                "projected_row_ordinal": len(projected_rows),
            }
        )
    for row_ordinal, row in enumerate(receiver_rows[:total_ordinal], start=1):
        cloned = projected_root if row_ordinal == total_ordinal else canonical_clone_v1(row)
        projected_rows.append(cloned)
        row_projections.append(
            {
                "after_row": canonical_clone_v1(cloned),
                "before_locator": _region_locator(receiver_region),
                "before_row": canonical_clone_v1(row),
                "before_row_ordinal": row_ordinal,
                "projected_row_ordinal": len(projected_rows),
            }
        )
    projected_region = canonical_clone_v1(prior_region)
    projected_region["component_roles"] = sorted(prior_roles | receiver_roles)
    projected_region["fragment_ordinal"] = 1
    projected_regions = [projected_region]
    original_query_receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        ordered
    )
    projected_query_receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        projected_regions
    )
    material = {
        "branch_equation": {
            "expense_children": receiver_branch[1],
            "expense_vector": receiver_branch[0],
            "income_children": prior_branch[1],
            "income_vector": prior_branch[0],
            "multipliers": [1, 1],
            "result_vector": total_vector,
        },
        "canonical_unit": prior_unit["canonical_unit"],
        "governor": canonical_clone_v1(governors[0]),
        "original_query_receipt": original_query_receipt,
        "original_regions": canonical_clone_v1(ordered),
        "prior_lane_axis": canonical_clone_v1(prior_axis),
        "prior_table": {
            "columns": canonical_clone_v1(prior_table.get("columns")),
            "continuation": prior_table.get("continuation"),
            "locator": _region_locator(prior_region),
            "rows": canonical_clone_v1(prior_rows),
            "title_exact": prior_table.get("title_exact"),
            "unit_axis": canonical_clone_v1(prior_unit),
            "unit_exact": prior_table.get("unit_exact"),
        },
        "projected_query_receipt": projected_query_receipt,
        "projected_region": projected_region,
        "receiver_lane_axis": canonical_clone_v1(receiver_axis),
        "receiver_table": {
            "columns": canonical_clone_v1(receiver_table.get("columns")),
            "continuation": receiver_table.get("continuation"),
            "first_following_row": (
                canonical_clone_v1(receiver_rows[total_ordinal])
                if total_ordinal < len(receiver_rows)
                else None
            ),
            "leading_total_ordinal": total_ordinal,
            "locator": _region_locator(receiver_region),
            "rows": canonical_clone_v1(receiver_rows),
            "title_exact": receiver_table.get("title_exact"),
            "unit_axis": canonical_clone_v1(receiver_unit),
            "unit_exact": receiver_table.get("unit_exact"),
        },
        "row_projections": row_projections,
        "rule": (
            "RECIPROCAL_PHYSICALLY_AND_SELECTED_ADJACENT_FX_NOTE_SPLIT_"
            "INCOME_SENDER_PLUS_EXPENSE_RECEIVER_WITH_EQUAL_EXPLICIT_LANE_"
            "AND_UNIT_AXES_UNIQUE_TERMINAL_LEADING_CONG_EXACTLY_EQUALS_"
            "SOURCE_CHILD_SUM_AND_UNIQUE_PRIMARY_RESULT"
        ),
    }
    receipt = {
        **material,
        "terminal_cong_continuation_projection_receipt_id": (
            "gjfgatccprv1:receipt:" + canonical_json_sha256_v1(material)
        ),
    }
    projected_pages = {version_id: canonical_clone_v1(page) for version_id, page in pages.items()}
    _projected_section, projected_table = _region_table(
        pages=projected_pages, region=projected_region
    )
    projected_table["rows"] = projected_rows
    projected_table["continuation"] = "NONE"
    return projected_pages, projected_regions, receipt


def _terminal_cong_query_recovery_v1(
    *,
    cluster: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]] | None:
    """Recover the one receiver table omitted by an owner fence."""

    regions = cluster.get("component_regions")
    inventory = cluster.get("declared_money_table_inventory")
    if (
        cluster.get("status") != READY
        or type(regions) is not list
        or len(regions) != 1
        or type(inventory) is not list
    ):
        return None
    prior = regions[0]
    candidates = []
    for item in inventory:
        if (
            type(item) is not dict
            or item.get("physical_page") != prior.get("physical_page", -2) + 1
            or item.get("disposition") == "SELECTED_FAMILY_COMPONENT"
            or type(item.get("classification")) is not dict
        ):
            continue
        resolved = _table_from_inventory(item=item, page_json_by_version=pages)
        if resolved is None:
            continue
        _section, table = resolved
        total_ordinal = _leading_cong_total_ordinal_v1(table, compiled_specs=compiled_specs)
        if total_ordinal is None:
            continue
        roles = sorted(
            {
                hit["role"]
                for hit in item["classification"].get("role_hits", [])
                if type(hit) is dict
                and type(hit.get("role")) is str
                and hit.get("row_ordinal", total_ordinal + 1) < total_ordinal
                and hit["role"].startswith("EXPENSE_")
            }
        )
        selected = [
            page
            for page in selected_page_axis
            if page.get("document_id") == cluster.get("document_id")
            and page.get("source_sha256") == cluster.get("source_sha256")
            and page.get("page_json_version_id") == item.get("page_json_version_id")
            and page.get("physical_page") == item.get("physical_page")
        ]
        if not roles or len(selected) != 1:
            continue
        receiver = {
            "component_roles": roles,
            "document_id": cluster["document_id"],
            "document_ordinal": cluster["document_ordinal"],
            "fragment_ordinal": 2,
            "page_json_version_id": item["page_json_version_id"],
            "physical_page": item["physical_page"],
            "section_id": item["section_id"],
            "selected_page_ordinal": selected[0]["selected_page_ordinal"],
            "source_logical_name": cluster["source_logical_name"],
            "source_sha256": cluster["source_sha256"],
            "table_id": item["table_id"],
        }
        pair = [canonical_clone_v1(prior), receiver]
        projected = _terminal_cong_continuation_projection_v1(
            pages=pages, regions=pair, compiled_specs=compiled_specs
        )
        if projected is not None:
            candidates.append((pair, projected[2]))
    return candidates[0] if len(candidates) == 1 else None


def _unlabeled_subtotals_and_root_projection_v1(
    *,
    pages: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], dict[str, Any]] | None:
    """Promote source-visible unlabeled SSB subtotals/result structurally."""

    if len(regions) != 1:
        return None
    region = regions[0]
    try:
        section, table = _region_table(pages=pages, region=region)
    except GeminiJsonFxGoldActivityFamilyV1Error:
        return None
    owner_surfaces = [
        value
        for value in (table.get("title_exact"), section.get("title_exact"))
        if _root_alias(value, compiled_specs=compiled_specs) is not None
    ]
    owner_aliases = {_root_alias(value, compiled_specs=compiled_specs) for value in owner_surfaces}
    rows = table.get("rows")
    if len(owner_aliases) != 1 or not owner_surfaces or type(rows) is not list:
        return None
    try:
        classification = classify_gemini_json_multitable_hierarchical_table_v1(
            pages[region["page_json_version_id"]],
            section,
            table,
            compiled_specs=compiled_specs,
        )
    except ValueError:
        return None
    hits = classification.get("role_hits")
    totals = classification.get("total_rows")
    if (
        type(hits) is not list
        or type(totals) is not list
        or len(totals) != 3
        or classification.get("family_root_row_ordinals") not in (None, [])
        or classification.get("ambiguous_rows") != []
    ):
        return None
    by_role: dict[str, list[dict[str, Any]]] = {}
    for hit in hits:
        if type(hit) is not dict or type(hit.get("role")) is not str:
            return None
        by_role.setdefault(hit["role"], []).append(hit)
    if len(by_role.get("INCOME_PARENT", [])) != 1 or len(by_role.get("EXPENSE_PARENT", [])) != 1:
        return None
    income_hits = [hit for hit in hits if hit["role"].startswith("INCOME_")]
    expense_hits = [hit for hit in hits if hit["role"].startswith("EXPENSE_")]
    if (
        len(income_hits) + len(expense_hits) != len(hits)
        or len(income_hits) < 2
        or len(expense_hits) < 2
    ):
        return None
    income_subtotal_ordinal = max(hit["row_ordinal"] for hit in income_hits) + 1
    expense_subtotal_ordinal = max(hit["row_ordinal"] for hit in expense_hits) + 1
    root_ordinal = expense_subtotal_ordinal + 1
    total_axis = [(item.get("row_ordinal"), item.get("row_kind")) for item in totals]
    if (
        total_axis
        != [
            (income_subtotal_ordinal, "SUBTOTAL"),
            (expense_subtotal_ordinal, "SUBTOTAL"),
            (root_ordinal, "TOTAL"),
        ]
        or classification.get("unbound_money_row_ordinals")
        != [income_subtotal_ordinal, expense_subtotal_ordinal, root_ordinal]
        or root_ordinal != len(rows)
        or set(range(1, len(rows) + 1))
        != {
            *(hit["row_ordinal"] for hit in hits),
            income_subtotal_ordinal,
            expense_subtotal_ordinal,
            root_ordinal,
        }
    ):
        return None
    lane_axis = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
    unit_axis = _unit_axis(table, compiled_specs=compiled_specs)
    money_ordinals = lane_axis.get("money_column_ordinals")
    if (
        lane_axis.get("complete") is not True
        or type(money_ordinals) is not list
        or len(money_ordinals) != 2
        or unit_axis.get("complete") is not True
        or unit_axis.get("canonical_unit") not in {"MILLION_VND", "VND"}
    ):
        return None

    def branch_receipt(
        *, branch_hits: Sequence[Mapping[str, Any]], parent_role: str, subtotal_ordinal: int
    ) -> dict[str, Any] | None:
        parent_hit = next((hit for hit in branch_hits if hit["role"] == parent_role), None)
        child_hits = [hit for hit in branch_hits if hit["role"] != parent_role]
        if parent_hit is None or not child_hits:
            return None
        parent_row = rows[parent_hit["row_ordinal"] - 1]
        subtotal_row = rows[subtotal_ordinal - 1]
        if (
            type(parent_row) is not dict
            or type(subtotal_row) is not dict
            or parent_row.get("row_kind") != "GROUP"
            or subtotal_row.get("label_exact") is not None
            or any(
                _money(parent_row["values_exact"][ordinal - 1]).get("coefficient") is not None
                for ordinal in money_ordinals
            )
        ):
            return None
        subtotal_vector = _source_row_vector(subtotal_row, money_ordinals=money_ordinals)
        if subtotal_vector is None:
            return None
        child_axis = []
        observed_sums = [0 for _ in money_ordinals]
        observed_counts = [0 for _ in money_ordinals]
        for hit in child_hits:
            row = rows[hit["row_ordinal"] - 1]
            values = row.get("values_exact") if type(row) is dict else None
            if type(values) is not list:
                return None
            cells = [_money(values[ordinal - 1]) for ordinal in money_ordinals]
            if all(cell.get("coefficient") is None for cell in cells):
                return None
            for lane, cell in enumerate(cells):
                if type(cell.get("coefficient")) is int:
                    observed_sums[lane] += cell["coefficient"]
                    observed_counts[lane] += 1
            child_axis.append(
                {
                    "cells": cells,
                    "role": hit["role"],
                    "row": canonical_clone_v1(row),
                    "row_ordinal": hit["row_ordinal"],
                }
            )
        if any(count == 0 for count in observed_counts) or observed_sums != subtotal_vector:
            return None
        return {
            "child_axis": child_axis,
            "observed_child_sum_vector": observed_sums,
            "parent_role": parent_role,
            "parent_structural_row": canonical_clone_v1(parent_row),
            "parent_structural_row_ordinal": parent_hit["row_ordinal"],
            "subtotal_row": canonical_clone_v1(subtotal_row),
            "subtotal_row_ordinal": subtotal_ordinal,
            "subtotal_vector": subtotal_vector,
        }

    income = branch_receipt(
        branch_hits=income_hits,
        parent_role="INCOME_PARENT",
        subtotal_ordinal=income_subtotal_ordinal,
    )
    expense = branch_receipt(
        branch_hits=expense_hits,
        parent_role="EXPENSE_PARENT",
        subtotal_ordinal=expense_subtotal_ordinal,
    )
    root_row = rows[root_ordinal - 1]
    root_vector = (
        _source_row_vector(root_row, money_ordinals=money_ordinals)
        if type(root_row) is dict
        and root_row.get("label_exact") is None
        and root_row.get("row_kind") == "TOTAL"
        else None
    )
    if income is None or expense is None or root_vector is None:
        return None
    if [
        left + right
        for left, right in zip(income["subtotal_vector"], expense["subtotal_vector"], strict=True)
    ] != root_vector:
        return None
    governors = [
        governor
        for governor in _primary_root_unit_governors(pages=pages, compiled_specs=compiled_specs)
        if governor["canonical_unit"] == unit_axis["canonical_unit"]
        and governor["vector"] == root_vector
    ]
    if len(governors) != 1:
        return None

    owner_label_exact = owner_surfaces[0]
    projected_rows = []
    row_projections = []

    def append_projection(*, before_ordinal: int, after_row: Mapping[str, Any]) -> None:
        projected_rows.append(canonical_clone_v1(after_row))
        row_projections.append(
            {
                "after_row": canonical_clone_v1(after_row),
                "before_locator": _region_locator(region),
                "before_row": canonical_clone_v1(rows[before_ordinal - 1]),
                "before_row_ordinal": before_ordinal,
                "projected_row_ordinal": len(projected_rows),
            }
        )

    income_parent = canonical_clone_v1(rows[income["parent_structural_row_ordinal"] - 1])
    income_parent["values_exact"] = canonical_clone_v1(income["subtotal_row"]["values_exact"])
    append_projection(before_ordinal=income_subtotal_ordinal, after_row=income_parent)
    for hit in income_hits:
        if hit["role"] != "INCOME_PARENT":
            append_projection(
                before_ordinal=hit["row_ordinal"],
                after_row=rows[hit["row_ordinal"] - 1],
            )
    expense_parent = canonical_clone_v1(rows[expense["parent_structural_row_ordinal"] - 1])
    expense_parent["values_exact"] = canonical_clone_v1(expense["subtotal_row"]["values_exact"])
    append_projection(before_ordinal=expense_subtotal_ordinal, after_row=expense_parent)
    for hit in expense_hits:
        if hit["role"] != "EXPENSE_PARENT":
            append_projection(
                before_ordinal=hit["row_ordinal"],
                after_row=rows[hit["row_ordinal"] - 1],
            )
    projected_root = canonical_clone_v1(root_row)
    projected_root["label_exact"] = owner_label_exact
    projected_root["hierarchy_path_exact"] = [owner_label_exact]
    append_projection(before_ordinal=root_ordinal, after_row=projected_root)

    projected_region = canonical_clone_v1(region)
    original_query_receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        regions
    )
    projected_query_receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        [projected_region]
    )
    material = {
        "branch_receipts": [income, expense],
        "canonical_unit": unit_axis["canonical_unit"],
        "governor": canonical_clone_v1(governors[0]),
        "lane_axis": canonical_clone_v1(lane_axis),
        "original_query_receipt": original_query_receipt,
        "original_regions": canonical_clone_v1(list(regions)),
        "projected_query_receipt": projected_query_receipt,
        "projected_region": projected_region,
        "root_equation": {
            "component_roles": ["INCOME_PARENT", "EXPENSE_PARENT"],
            "component_vectors": [
                income["subtotal_vector"],
                expense["subtotal_vector"],
            ],
            "multipliers": [1, 1],
            "result_vector": root_vector,
        },
        "row_projections": row_projections,
        "rule": (
            "ONE_EXPLICIT_FX_OWNER_TABLE_WITH_TWO_LABEL_ONLY_STRUCTURAL_"
            "PARENTS_EXACT_UNLABELED_SOURCE_SUBTOTALS_AND_ONE_FINAL_UNLABELED_"
            "SOURCE_RESULT_EACH_OBSERVED_LANE_CLOSES_WITHOUT_COMPLETING_BLANKS_"
            "AND_RESULT_EXACTLY_MATCHES_ONE_PRIMARY_STATEMENT_ROOT"
        ),
        "source_table": {
            "columns": canonical_clone_v1(table.get("columns")),
            "continuation": table.get("continuation"),
            "locator": _region_locator(region),
            "rows": canonical_clone_v1(rows),
            "title_exact": table.get("title_exact"),
            "unit_axis": canonical_clone_v1(unit_axis),
            "unit_exact": table.get("unit_exact"),
        },
        "structural_blank_rows": [
            {
                "row": canonical_clone_v1(rows[income["parent_structural_row_ordinal"] - 1]),
                "row_ordinal": income["parent_structural_row_ordinal"],
            },
            {
                "row": canonical_clone_v1(rows[expense["parent_structural_row_ordinal"] - 1]),
                "row_ordinal": expense["parent_structural_row_ordinal"],
            },
        ],
    }
    receipt = {
        **material,
        "unlabeled_subtotals_and_root_projection_receipt_id": (
            "gjfgausarrprv1:receipt:" + canonical_json_sha256_v1(material)
        ),
    }
    projected_pages = {version_id: canonical_clone_v1(page) for version_id, page in pages.items()}
    _projected_section, projected_table = _region_table(
        pages=projected_pages, region=projected_region
    )
    projected_table["rows"] = projected_rows
    return projected_pages, [projected_region], receipt


def _blank_header_continuation_root_v1(
    *,
    pages: Mapping[str, dict[str, Any]],
    prior_region: Mapping[str, Any],
    receiver_region: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Bind one reciprocal adjacent receiver to the sender's complete lane axis."""

    if (
        compiled_specs.get("continuation_period_axis_policy")
        != "ADJACENT_PAGE_EXPLICIT_CONTINUATION_INHERITS_COMPLETE_BLANK_HEADER_AXIS"
        or prior_region.get("document_id") != receiver_region.get("document_id")
        or prior_region.get("source_sha256") != receiver_region.get("source_sha256")
        or receiver_region.get("selected_page_ordinal")
        != prior_region.get("selected_page_ordinal", -2) + 1
        or receiver_region.get("physical_page") != prior_region.get("physical_page", -2) + 1
    ):
        return None
    try:
        prior_section, prior_table = _region_table(
            pages=pages,
            region=prior_region,
        )
        receiver_section, receiver_table = _region_table(
            pages=pages,
            region=receiver_region,
        )
    except GeminiJsonFxGoldActivityFamilyV1Error:
        return None
    if (
        prior_table.get("continuation") != "CONTINUES_ON_NEXT_PAGE"
        or receiver_table.get("continuation") != "CONTINUES_FROM_PREVIOUS_PAGE"
    ):
        return None
    prior_axis = _multitable_lane_axis(
        prior_section,
        prior_table,
        compiled_specs=compiled_specs,
    )
    receiver_local_axis = _multitable_lane_axis(
        receiver_section,
        receiver_table,
        compiled_specs=compiled_specs,
    )
    receiver_columns = receiver_table.get("columns")
    receiver_ordinals = _money_ordinals(receiver_table)
    prior_ordinals = prior_axis.get("money_column_ordinals")
    if (
        prior_axis.get("complete") is not True
        or receiver_local_axis.get("complete") is True
        or type(prior_ordinals) is not list
        or type(receiver_columns) is not list
        or not receiver_ordinals
        or len(receiver_ordinals) != len(prior_ordinals)
        or any(
            ordinal > len(receiver_columns)
            or any(
                _normalized(segment)
                for segment in (receiver_columns[ordinal - 1].get("header_path_exact") or [])
            )
            for ordinal in receiver_ordinals
        )
    ):
        return None
    prior_roles = {role for role in prior_region.get("component_roles", []) if type(role) is str}
    receiver_roles = {
        role for role in receiver_region.get("component_roles", []) if type(role) is str
    }
    root_components = set(compiled_specs.get("root_component_roles", []))
    if not receiver_roles or not root_components.issubset(prior_roles | receiver_roles):
        return None
    inherited_axis = canonical_clone_v1(prior_axis)
    inherited_axis["layout_kind"] = "ADJACENT_PAGE_EXPLICIT_CONTINUATION_BLANK_HEADER_AXIS"
    inherited_axis["money_column_ordinals"] = receiver_ordinals
    inherited_axis["source_period_axis"] = {
        "inherited_from_locator": _region_locator(prior_region),
        "local_money_column_ordinals": receiver_ordinals,
        "prior_source_lane_keys": canonical_clone_v1(
            prior_axis.get("source_lane_keys", prior_axis.get("lane_keys"))
        ),
        "rule": (
            "EXPLICIT_CONTINUES_FROM_PREVIOUS_PAGE_PLUS_ADJACENT_PRIOR_"
            "CONTINUES_ON_NEXT_PAGE_WITH_COMPLETE_AXIS_AND_ALL_LOCAL_HEADERS_BLANK"
        ),
    }
    root = _exact_root_vector_for_lane_axis(
        table=receiver_table,
        lane_axis=inherited_axis,
        compiled_specs=compiled_specs,
    )
    if (
        root is None
        or _exact_root_vector(
            section=prior_section,
            table=prior_table,
            compiled_specs=compiled_specs,
        )
        is not None
    ):
        return None
    return {
        "inherited_lane_axis": inherited_axis,
        "prior_locator": _region_locator(prior_region),
        "receiver_local_lane_axis": canonical_clone_v1(receiver_local_axis),
        "receiver_locator": _region_locator(receiver_region),
        "root": root,
        "rule": (
            "UNIQUE_RECIPROCAL_PHYSICALLY_AND_SELECTED_ADJACENT_RECEIVER_"
            "ROOT_USES_ONLY_THE_COMPLETE_PRIOR_LANE_IDENTITIES_AND_LOCAL_"
            "RECEIVER_SOURCE_CELLS"
        ),
    }


def _primary_root_unit_governors(
    *,
    pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    governors = []
    for page_json_version_id, page in pages.items():
        if type(page) is not dict or page.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
            continue
        sections = page.get("sections")
        for section_ordinal, section in enumerate(
            sections if type(sections) is list else [], start=1
        ):
            if (
                type(section) is not dict
                or section.get("content_kind") != "PRIMARY_STATEMENT"
                or section.get("statement_type") != "INCOME_STATEMENT"
                or type(section.get("tables")) is not list
            ):
                continue
            for table_ordinal, table in enumerate(section["tables"], start=1):
                if type(table) is not dict:
                    continue
                unit_axis = _unit_axis(table, compiled_specs=compiled_specs)
                root = _exact_root_vector(
                    section=section, table=table, compiled_specs=compiled_specs
                )
                if unit_axis.get("complete") is not True or root is None:
                    continue
                governors.append(
                    {
                        "canonical_unit": unit_axis["canonical_unit"],
                        "lane_axis": root["lane_axis"],
                        "locator": {
                            "page_json_version_id": page_json_version_id,
                            "section_id": f"s{section_ordinal}",
                            "table_id": f"t{table_ordinal}",
                        },
                        "root_row": root["root_row"],
                        "unit_axis": canonical_clone_v1(unit_axis),
                        "vector": root["vector"],
                    }
                )
    return governors


def _apply_exact_primary_root_unit_corroboration_v1(
    *,
    pages: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Inject a unit only after one exact statement/detail root-vector match."""

    projected = {version_id: canonical_clone_v1(page) for version_id, page in pages.items()}
    governors = _primary_root_unit_governors(pages=pages, compiled_specs=compiled_specs)
    receipts = []
    ordered_regions = sorted(
        regions,
        key=lambda item: (
            item.get("selected_page_ordinal", -1),
            item.get("physical_page", -1),
            item.get("section_id", ""),
            item.get("table_id", ""),
        ),
    )
    for prior_region, receiver_region in zip(
        ordered_regions,
        ordered_regions[1:],
        strict=False,
    ):
        continuation = _blank_header_continuation_root_v1(
            pages=projected,
            prior_region=prior_region,
            receiver_region=receiver_region,
            compiled_specs=compiled_specs,
        )
        if continuation is None:
            continue
        _prior_section, prior_table = _region_table(
            pages=projected,
            region=prior_region,
        )
        _receiver_section, receiver_table = _region_table(
            pages=projected,
            region=receiver_region,
        )
        local_units = [
            _unit_axis(table, compiled_specs=compiled_specs)
            for table in (prior_table, receiver_table)
        ]
        if any(
            item.get("complete") is True or item.get("evidence") or item.get("undeclared_evidence")
            for item in local_units
        ):
            continue
        target = continuation["root"]
        matches = [item for item in governors if item["vector"] == target["vector"]]
        if len(matches) != 1:
            continue
        governor = matches[0]
        if governor["canonical_unit"] not in {"MILLION_VND", "VND"}:
            continue
        after_unit = governor["unit_axis"]["evidence"][0]["source_exact"]
        if type(after_unit) is not str or not after_unit.strip():
            continue
        material = {
            "after_table_unit_exact": after_unit,
            "before_table_unit_exact_axis": [
                prior_table.get("unit_exact"),
                receiver_table.get("unit_exact"),
            ],
            "canonical_unit": governor["canonical_unit"],
            "continuation": continuation,
            "governor": canonical_clone_v1(governor),
            "rule": (
                "UNIQUE_PRIMARY_INCOME_STATEMENT_ROOT_DURATION_VECTOR_EXACTLY_"
                "EQUALS_RECIPROCAL_ADJACENT_UNITLESS_DETAIL_ROOT_VECTOR_"
                "NO_SCALE_OR_ROUNDING"
            ),
            "target": {
                "lane_axis": target["lane_axis"],
                "locator": continuation["receiver_locator"],
                "root_row": target["root_row"],
                "vector": target["vector"],
            },
        }
        prior_table["unit_exact"] = after_unit
        receiver_table["unit_exact"] = after_unit
        receipts.append(
            {
                **material,
                "unit_corroboration_receipt_id": (
                    "gjfgaucrv1:receipt:" + canonical_json_sha256_v1(material)
                ),
            }
        )
    for region in regions:
        section, table = _region_table(pages=projected, region=region)
        local_unit = _unit_axis(table, compiled_specs=compiled_specs)
        if (
            local_unit.get("complete") is True
            or local_unit.get("evidence")
            or local_unit.get("undeclared_evidence")
        ):
            continue
        target = _exact_root_vector(section=section, table=table, compiled_specs=compiled_specs)
        if target is None:
            continue
        matches = [item for item in governors if item["vector"] == target["vector"]]
        if len(matches) != 1:
            continue
        governor = matches[0]
        if governor["canonical_unit"] not in {"MILLION_VND", "VND"}:
            continue
        after_unit = governor["unit_axis"]["evidence"][0]["source_exact"]
        if type(after_unit) is not str or not after_unit.strip():
            continue
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
            "after_table_unit_exact": after_unit,
            "before_table_unit_exact": table.get("unit_exact"),
            "canonical_unit": governor["canonical_unit"],
            "governor": canonical_clone_v1(governor),
            "rule": (
                "UNIQUE_PRIMARY_INCOME_STATEMENT_ROOT_DURATION_VECTOR_EXACTLY_"
                "EQUALS_UNITLESS_DETAIL_ROOT_VECTOR_NO_SCALE_OR_ROUNDING"
            ),
            "target": {
                "lane_axis": target["lane_axis"],
                "locator": locator,
                "root_row": target["root_row"],
                "vector": target["vector"],
            },
        }
        table["unit_exact"] = after_unit
        receipts.append(
            {
                **material,
                "unit_corroboration_receipt_id": (
                    "gjfgaucrv1:receipt:" + canonical_json_sha256_v1(material)
                ),
            }
        )
    return projected, receipts


def _detail_regions_with_primary_result_context_v1(
    *,
    pages: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    original_query_receipt: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Remove primary result-only regions after an exact typed reconciliation."""

    primary_regions = []
    detail_regions = []
    for region in regions:
        page = pages.get(region.get("page_json_version_id"))
        if type(page) is not dict:
            return [canonical_clone_v1(item) for item in regions], None
        if page.get("status") == "PRIMARY_FINANCIAL_STATEMENT":
            primary_regions.append(region)
        else:
            detail_regions.append(region)
    if not primary_regions or not detail_regions:
        return [canonical_clone_v1(item) for item in regions], None

    detail_roots = []
    for region in detail_regions:
        section, table = _region_table(pages=pages, region=region)
        root = _exact_root_vector(
            section=section,
            table=table,
            compiled_specs=compiled_specs,
        )
        if root is None:
            continue
        unit_axis = _unit_axis(table, compiled_specs=compiled_specs)
        if unit_axis.get("complete") is not True:
            return [canonical_clone_v1(item) for item in regions], None
        detail_roots.append(
            {
                "continuation": None,
                "region": region,
                "root": root,
                "unit_axis": unit_axis,
            }
        )
    ordered_detail_regions = sorted(
        detail_regions,
        key=lambda item: (
            item.get("selected_page_ordinal", -1),
            item.get("physical_page", -1),
            item.get("section_id", ""),
            item.get("table_id", ""),
        ),
    )
    for prior_region, receiver_region in zip(
        ordered_detail_regions,
        ordered_detail_regions[1:],
        strict=False,
    ):
        continuation = _blank_header_continuation_root_v1(
            pages=pages,
            prior_region=prior_region,
            receiver_region=receiver_region,
            compiled_specs=compiled_specs,
        )
        if continuation is None:
            continue
        _receiver_section, receiver_table = _region_table(
            pages=pages,
            region=receiver_region,
        )
        unit_axis = _unit_axis(receiver_table, compiled_specs=compiled_specs)
        if unit_axis.get("complete") is not True:
            return [canonical_clone_v1(item) for item in regions], None
        detail_roots.append(
            {
                "continuation": continuation,
                "region": receiver_region,
                "root": continuation["root"],
                "unit_axis": unit_axis,
            }
        )
    if len(detail_roots) != 1:
        return [canonical_clone_v1(item) for item in regions], None
    target_detail = detail_roots[0]
    target_region = target_detail["region"]
    target_root = target_detail["root"]
    target_unit_axis = target_detail["unit_axis"]

    primary_results = []
    for region in primary_regions:
        section, table = _region_table(pages=pages, region=region)
        root = _exact_root_vector(
            section=section,
            table=table,
            compiled_specs=compiled_specs,
        )
        unit_axis = _unit_axis(table, compiled_specs=compiled_specs)
        if root is None or unit_axis.get("complete") is not True:
            return [canonical_clone_v1(item) for item in regions], None
        primary_results.append(
            {
                "canonical_unit": unit_axis["canonical_unit"],
                "lane_axis": root["lane_axis"],
                "locator": {
                    key: region[key]
                    for key in (
                        "page_json_version_id",
                        "physical_page",
                        "section_id",
                        "table_id",
                    )
                },
                "root_row": root["root_row"],
                "unit_axis": canonical_clone_v1(unit_axis),
                "vector": root["vector"],
            }
        )
    by_unit: dict[str, list[dict[str, Any]]] = {}
    for item in primary_results:
        by_unit.setdefault(item["canonical_unit"], []).append(item)
    target_unit = target_unit_axis["canonical_unit"]
    for canonical_unit, items in by_unit.items():
        vectors = {tuple(item["vector"]) for item in items}
        if len(vectors) != 1:
            return [canonical_clone_v1(item) for item in regions], None
        if canonical_unit == target_unit and next(iter(vectors)) != tuple(target_root["vector"]):
            return [canonical_clone_v1(item) for item in regions], None

    selected = []
    for fragment_ordinal, region in enumerate(detail_regions, start=1):
        cloned = canonical_clone_v1(region)
        cloned["fragment_ordinal"] = fragment_ordinal
        selected.append(cloned)
    selected_query_receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        selected
    )
    source_results = []
    for item in primary_results:
        source_results.append(
            {
                **canonical_clone_v1(item),
                "disposition": (
                    "EXACT_SAME_UNIT_ROOT_VECTOR_CORROBORATION"
                    if item["canonical_unit"] == target_unit
                    else "EXPLICIT_ALTERNATE_UNIT_PRIMARY_RESULT_CONTEXT_ONLY"
                ),
            }
        )
    target_locator = {
        key: target_region[key]
        for key in (
            "page_json_version_id",
            "physical_page",
            "section_id",
            "table_id",
        )
    }
    material = {
        "original_query_receipt": canonical_clone_v1(original_query_receipt),
        "primary_source_results": source_results,
        "rule": (
            "PRIMARY_INCOME_STATEMENT_SOURCE_RESULTS_ARE_CONTEXT_ONLY_WHEN_ONE_"
            "DETAIL_ROOT_HAS_A_COMPLETE_UNIT_EVERY_SAME_UNIT_PRIMARY_VECTOR_"
            "EXACTLY_MATCHES_AND_EVERY_ALTERNATE_UNIT_AXIS_IS_INTERNALLY_UNIQUE_"
            "NO_SCALE_OR_ROUNDING"
        ),
        "selected_detail_query_receipt": selected_query_receipt,
        "target_detail_root": {
            "canonical_unit": target_unit,
            "continuation": canonical_clone_v1(target_detail["continuation"]),
            "lane_axis": target_root["lane_axis"],
            "locator": target_locator,
            "root_row": target_root["root_row"],
            "unit_axis": canonical_clone_v1(target_unit_axis),
            "vector": target_root["vector"],
        },
    }
    receipt = {
        **material,
        "primary_result_context_receipt_id": (
            "gjfgaprcrv1:receipt:" + canonical_json_sha256_v1(material)
        ),
    }
    return selected, receipt


def _reseal_candidate(
    candidate: dict[str, Any],
    *,
    primary_root_receipt: Mapping[str, Any] | None,
    primary_result_context_receipt: Mapping[str, Any] | None,
    terminal_cong_projection_receipt: Mapping[str, Any] | None,
    unlabeled_subtotals_and_root_projection_receipt: Mapping[str, Any] | None,
    source_repair_overlay_id: str,
    source_repair_receipts: Sequence[Mapping[str, Any]],
    source_repair_spec_sha256: str,
    source_visible_signed_root_receipt: Mapping[str, Any] | None,
    unit_corroboration_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if (
        primary_root_receipt is None
        and primary_result_context_receipt is None
        and terminal_cong_projection_receipt is None
        and unlabeled_subtotals_and_root_projection_receipt is None
        and not source_repair_receipts
        and source_visible_signed_root_receipt is None
        and not unit_corroboration_receipts
    ):
        return candidate
    material = {
        "adapter_format_version": ADAPTER_FORMAT_VERSION,
        "primary_result_context_receipt": canonical_clone_v1(primary_result_context_receipt),
        "primary_root_projection_receipt": canonical_clone_v1(primary_root_receipt),
        "shared_engine_claim_boundary": GENERIC_CLAIM_BOUNDARY,
        "source_repair_overlay_id": source_repair_overlay_id,
        "source_repair_receipts": canonical_clone_v1(list(source_repair_receipts)),
        "source_repair_spec_sha256": source_repair_spec_sha256,
        "source_visible_signed_root_receipt": canonical_clone_v1(
            source_visible_signed_root_receipt
        ),
        "terminal_cong_continuation_projection_receipt": canonical_clone_v1(
            terminal_cong_projection_receipt
        ),
        "unlabeled_subtotals_and_root_projection_receipt": canonical_clone_v1(
            unlabeled_subtotals_and_root_projection_receipt
        ),
        "unit_corroboration_receipts": canonical_clone_v1(list(unit_corroboration_receipts)),
    }
    candidate["claim_boundary"] = ADAPTER_CLAIM_BOUNDARY
    candidate["closure_receipt"]["fx_gold_activity_adapter_receipt"] = {
        **material,
        "adapter_receipt_id": ("gjfgafav1:receipt:" + canonical_json_sha256_v1(material)),
    }
    candidate_material = {key: candidate[key] for key in candidate if key != "candidate_id"}
    candidate["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        candidate_material
    )
    return candidate


def _replace_derived_root_with_source_visible_signed_root_v1(
    candidate: dict[str, Any],
    *,
    pages: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Retain one printed terminal root after a unique signed component proof.

    The shared evaluator deliberately proves table-local totals by direct sums.
    A compact FX note can instead print positive income and expense magnitudes,
    followed by their net result.  In that layout the local direct-sum stage
    omits the printed result and the later document stage would otherwise emit
    a synthetic income-plus-expense root.  This family-local correction is
    structural and fail-closed: the terminal source row and the two declared
    parent roles select the graph, while arithmetic may only prove the unique
    signed orientation.  A compact or detailed presentation may leave that
    terminal result unlabeled; it is admitted only when the exact owner
    surface, one ordered pair of parent rows, an exhaustive declared row
    frontier, and one unbound terminal TOTAL uniquely identify it.  No source
    value is changed or backsolved.
    """

    if (
        candidate.get("status") != READY
        or compiled_specs.get("root_component_equation_policy")
        != "UNIQUE_DECLARED_SIGN_ORIENTATION_FIRST_COMPONENT_POSITIVE"
    ):
        return None
    root_mappings = [
        mapping
        for mapping in candidate.get("mappings", [])
        if mapping.get("role") == "FAMILY_ROOT_TOTAL"
    ]
    if (
        len(root_mappings) != 1
        or root_mappings[0].get("state")
        != "DECLARED_FAMILY_ROOT_DERIVED_FROM_COMPLETE_TOP_LEVEL_COMPONENT_SUM"
    ):
        return None
    root_mapping = root_mappings[0]

    component_roles = list(compiled_specs.get("root_component_roles", []))
    if component_roles != ["INCOME_PARENT", "EXPENSE_PARENT"]:
        return None

    ordered_regions = sorted(
        regions,
        key=lambda item: (
            item.get("selected_page_ordinal", -1),
            item.get("physical_page", -1),
            item.get("section_id", ""),
            item.get("table_id", ""),
        ),
    )
    inherited_lane_axes: dict[tuple[Any, ...], dict[str, Any]] = {}
    for prior_region, receiver_region in zip(
        ordered_regions,
        ordered_regions[1:],
        strict=False,
    ):
        continuation = _blank_header_continuation_root_v1(
            pages=pages,
            prior_region=prior_region,
            receiver_region=receiver_region,
            compiled_specs=compiled_specs,
        )
        if continuation is not None:
            inherited_lane_axes[
                (
                    receiver_region.get("page_json_version_id"),
                    receiver_region.get("section_id"),
                    receiver_region.get("table_id"),
                )
            ] = continuation["inherited_lane_axis"]

    source_root_records = []
    saw_source_root = False
    for region in regions:
        try:
            section, table = _region_table(pages=pages, region=region)
        except GeminiJsonFxGoldActivityFamilyV1Error:
            continue
        rows = table.get("rows")
        if type(rows) is not list or not rows:
            continue
        classification = classify_gemini_json_multitable_hierarchical_table_v1(
            pages[region["page_json_version_id"]],
            section,
            table,
            compiled_specs=compiled_specs,
        )
        root_ordinals = classification.get("family_root_row_ordinals", [])
        root_source_state = "SOURCE_VISIBLE_FAMILY_ROOT_PENDING_UNIQUE_SIGNED_COMPONENT_PROOF"
        if root_ordinals == []:
            owner_aliases = {
                alias
                for value in (table.get("title_exact"), section.get("title_exact"))
                if (alias := _query_owner_alias(value, compiled_specs=compiled_specs)) is not None
            }
            role_hits = classification.get("role_hits")
            total_rows = classification.get("total_rows")
            terminal_ordinal = len(rows)
            terminal_row = rows[-1]
            declared_role_axis = (
                [(hit.get("role"), hit.get("row_ordinal")) for hit in role_hits]
                if type(role_hits) is list and all(type(hit) is dict for hit in role_hits)
                else None
            )
            declared_row_ordinals = (
                {row_ordinal for _role, row_ordinal in declared_role_axis}
                if declared_role_axis is not None
                and all(type(row_ordinal) is int for _role, row_ordinal in declared_role_axis)
                else set()
            )
            root_parent_axis = (
                [
                    (role, row_ordinal)
                    for role, row_ordinal in declared_role_axis
                    if role in {"INCOME_PARENT", "EXPENSE_PARENT"}
                ]
                if declared_role_axis is not None
                else []
            )
            has_unlabeled_terminal_source_total = bool(
                len(owner_aliases) == 1
                and classification.get("typed_control_disposition") is None
                and classification.get("owner_visible") is True
                and type(terminal_row) is dict
                and terminal_row.get("label_exact") is None
                and terminal_row.get("hierarchy_path_exact") == [None]
                and terminal_row.get("row_kind") == "TOTAL"
                and type(total_rows) is list
                and sum(
                    row.get("row_ordinal") == terminal_ordinal
                    and row.get("source_order") == terminal_ordinal
                    and row.get("row_kind") == "TOTAL"
                    for row in total_rows
                    if type(row) is dict
                )
                == 1
            )
            saw_source_root = saw_source_root or has_unlabeled_terminal_source_total
            if (
                has_unlabeled_terminal_source_total
                and [role for role, _row_ordinal in root_parent_axis]
                == ["INCOME_PARENT", "EXPENSE_PARENT"]
                and root_parent_axis[0][1] == 1
                and 1 < root_parent_axis[1][1] < terminal_ordinal
                and declared_row_ordinals == set(range(1, terminal_ordinal))
                and terminal_ordinal >= 3
                and classification.get("unbound_money_row_ordinals") == [terminal_ordinal]
                and classification.get("ambiguous_rows") == []
            ):
                root_ordinals = [terminal_ordinal]
                root_source_state = (
                    "SOURCE_VISIBLE_UNLABELED_TERMINAL_ROOT_PENDING_UNIQUE_SIGNED_COMPONENT_PROOF"
                )
        saw_source_root = saw_source_root or bool(root_ordinals)
        if len(root_ordinals) != 1 or root_ordinals[0] != len(rows):
            continue
        lane_axis = _multitable_lane_axis(
            section,
            table,
            compiled_specs=compiled_specs,
        )
        if lane_axis.get("complete") is not True:
            lane_axis = inherited_lane_axes.get(
                (
                    region.get("page_json_version_id"),
                    region.get("section_id"),
                    region.get("table_id"),
                ),
                lane_axis,
            )
        unit_axis = _unit_axis(table, compiled_specs=compiled_specs)
        if (
            lane_axis.get("complete") is not True
            or unit_axis.get("complete") is not True
            or unit_axis.get("canonical_unit") != root_mapping.get("unit")
        ):
            continue
        root_ordinal = root_ordinals[0]
        root_record = _row_local_record(
            "FAMILY_ROOT_TOTAL",
            root_ordinal,
            rows[root_ordinal - 1],
            region=region,
            lane_axis=lane_axis,
            state=root_source_state,
        )
        if (
            root_record is not None
            and len(root_record["cells"]) == len(root_mapping.get("values", []))
            and all(cell.get("source_text") is not None for cell in root_record["cells"])
        ):
            source_root_records.append(root_record)
    if not source_root_records:
        if saw_source_root:
            raise _error("FX/gold source-visible family root is not one complete terminal row")
        return None
    if len(source_root_records) != 1:
        raise _error("FX/gold terminal source-visible family root is not unique")
    source_root = source_root_records[0]

    # Once a complete terminal source root is present, silently retaining the
    # generic derived root is unsafe.  Both declared parents must be uniquely
    # source-observed.  A parent can be carried either by its own value row or
    # by a blank structural label bound to its exact printed subtotal; both
    # states retain source cells and are therefore valid equation inputs.
    source_component_states = {
        "SOURCE_OBSERVED_ROLE_ROW",
        "DECLARED_LABEL_ONLY_STRUCTURAL_GROUP_BOUND_TO_EXACT_PRINTED_RESULT",
    }
    component_mappings = []
    for role in component_roles:
        matches = [
            mapping
            for mapping in candidate["mappings"]
            if mapping.get("role") == role
            and mapping.get("state") in source_component_states
            and type(mapping.get("values")) is list
            and len(mapping["values"]) == len(source_root["cells"])
            and all(
                type(cell) is dict and cell.get("source_text") is not None
                for cell in mapping["values"]
            )
            and bool(mapping.get("source_refs"))
        ]
        if len(matches) != 1:
            raise _error(
                "FX/gold terminal source-visible family root does not have "
                f"one complete source-observed {role} mapping"
            )
        component_mappings.append(matches[0])

    def unique_source_refs(mapping: Mapping[str, Any]) -> list[dict[str, Any]]:
        output = []
        seen = set()
        for source_ref in mapping.get("source_refs", []):
            key = canonical_json_sha256_v1(source_ref)
            if key not in seen:
                output.append(canonical_clone_v1(source_ref))
                seen.add(key)
        return output

    component_records = [
        {
            "cells": canonical_clone_v1(mapping["values"]),
            "lane_keys": canonical_clone_v1(source_root["lane_keys"]),
            "role": mapping["role"],
            "source_refs": unique_source_refs(mapping),
            "state": mapping["state"],
            "valuation_basis": source_root["valuation_basis"],
        }
        for mapping in component_mappings
    ]
    equations = [
        _local_equation(
            equation_kind=("EXACT_FX_GOLD_SOURCE_VISIBLE_ROOT_UNIQUE_DECLARED_SIGN_ORIENTATION"),
            components=component_records,
            result=source_root,
            multipliers=multipliers,
        )
        for multipliers in ([1, -1], [1, 1])
    ]
    exact_equations = [equation for equation in equations if equation["status"] == "EXACT"]
    if len(exact_equations) != 1:
        raise _error("FX/gold source-visible family root sign orientation is not unique")
    signed_equation = exact_equations[0]

    closure = candidate.get("closure_receipt")
    if type(closure) is not dict:
        raise _error("FX/gold candidate closure receipt is invalid")
    obsolete_equations = [
        equation
        for equation in closure.get("equations", [])
        if equation.get("equation_kind")
        == "EXACT_COMPLETE_TOP_LEVEL_COMPONENT_SUM_DERIVES_FAMILY_ROOT"
        and equation.get("component_roles") == component_roles
        and equation.get("result_role") == "FAMILY_ROOT_TOTAL"
    ]
    obsolete_receipts = [
        receipt
        for receipt in closure.get("root_component_sum_receipts", [])
        if receipt.get("rule")
        == "COMPLETE_DECLARED_TOP_LEVEL_ROLE_FRONTIER_DIRECT_SUM_NO_BACKSOLVE"
        and receipt.get("component_roles") == component_roles
        and receipt.get("result_state")
        == "DECLARED_FAMILY_ROOT_DERIVED_FROM_COMPLETE_TOP_LEVEL_COMPONENT_SUM"
    ]
    if len(obsolete_equations) != 1 or len(obsolete_receipts) != 1:
        raise _error("FX/gold obsolete derived root proof is not unique")

    root_material = {
        "report_norm_id": compiled_specs["schema"]["family_root_report_norm_id"],
        "role": "FAMILY_ROOT_TOTAL",
        "row_id": source_root["source_refs"][0]["row_id"],
        "source_refs": canonical_clone_v1(source_root["source_refs"]),
        "state": "SOURCE_VISIBLE_FAMILY_ROOT_VALIDATED_BY_UNIQUE_SIGNED_COMPONENT_EQUATION",
        "unit": root_mapping["unit"],
        "values": canonical_clone_v1(source_root["cells"]),
    }
    replacement_mapping = {
        **root_material,
        "item_mapping_id": "gjmthfmv1:item:" + canonical_json_sha256_v1(root_material),
    }
    candidate["mappings"] = [
        replacement_mapping if mapping is root_mapping else mapping
        for mapping in candidate["mappings"]
    ]
    obsolete_equation_id = obsolete_equations[0]["equation_id"]
    closure["equations"] = [
        equation
        for equation in closure["equations"]
        if equation["equation_id"] != obsolete_equation_id
    ]
    closure["equations"].append(signed_equation)
    closure["root_component_sum_receipts"] = [
        receipt
        for receipt in closure["root_component_sum_receipts"]
        if receipt is not obsolete_receipts[0]
    ]
    signed_root_receipt = {
        "component_roles": component_roles,
        "multipliers": canonical_clone_v1(signed_equation["multipliers"]),
        "result_role": "FAMILY_ROOT_TOTAL",
        "rule": (
            "TERMINAL_SOURCE_VISIBLE_FAMILY_ROOT_REPLACES_GENERIC_DIRECT_SUM_ONLY_"
            "AFTER_UNIQUE_DECLARED_SIGN_ORIENTATION_ALL_LANES_EXACT"
        ),
        "source_equation_id": signed_equation["equation_id"],
        "source_root_detection_state": source_root["state"],
        "source_refs": canonical_clone_v1(source_root["source_refs"]),
    }
    closure["root_component_sum_receipts"].append(signed_root_receipt)
    material = {
        "new_mapping_id": replacement_mapping["item_mapping_id"],
        "obsolete_equation_id": obsolete_equation_id,
        "obsolete_mapping_id": root_mapping["item_mapping_id"],
        "rule": (
            "ONE_TERMINAL_SOURCE_VISIBLE_ROOT_AND_ONE_EACH_DECLARED_PARENT_"
            "UNIQUE_SIGN_ORIENTATION_NO_VALUE_MUTATION_NO_BACKSOLVE"
        ),
        "signed_root_receipt": signed_root_receipt,
    }
    return {
        **material,
        "signed_source_root_receipt_id": (
            "gjfgasrrv1:receipt:" + canonical_json_sha256_v1(material)
        ),
    }


def evaluate_gemini_json_fx_gold_activity_family_cluster_v1(
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate with an exact primary-root projection when applicable."""

    if compiled_specs.get("topology", {}).get("family_id") != FAMILY_ID:
        raise _error("FX/gold adapter received another family")
    try:
        expected_query_receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            regions
        )
    except ValueError as exc:
        raise _error("FX/gold region query receipt input is invalid") from exc
    if not same_typed_json_v1(query_receipt, expected_query_receipt):
        raise _error("FX/gold region query receipt drifted")
    effective_pages, source_repair_receipts = _apply_authenticated_source_repairs_v1(
        pages=page_json_by_version,
        compiled_specs=compiled_specs,
    )
    source_overlay = compiled_specs["fx_gold_activity_source_repair_overlay"]
    source_repair_overlay_id = source_overlay["overlay_id"]
    source_repair_spec_sha256 = compiled_specs["fx_gold_activity_source_repair_spec_sha256"]
    projection = None
    if type(regions) in {list, tuple} and len(regions) == 1:
        identified = _primary_statement_exact_root_projection_v1(
            region=regions[0],
            page_json_by_version=effective_pages,
            compiled_specs=compiled_specs,
        )
        if identified is not None:
            _unused_pages, projection = identified
    if projection is None:
        unlabeled_projection = (
            _unlabeled_subtotals_and_root_projection_v1(
                pages=effective_pages,
                regions=regions,
                compiled_specs=compiled_specs,
            )
            if type(regions) in {list, tuple}
            else None
        )
        if unlabeled_projection is not None:
            projected_pages, projected_regions, unlabeled_receipt = unlabeled_projection
            candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
                regions=projected_regions,
                page_json_by_version=projected_pages,
                compiled_specs=compiled_specs,
                query_receipt=unlabeled_receipt["projected_query_receipt"],
            )
            _restore_terminal_cong_projection_source_refs_v1(candidate, receipt=unlabeled_receipt)
            return _reseal_candidate(
                candidate,
                primary_root_receipt=None,
                primary_result_context_receipt=None,
                terminal_cong_projection_receipt=None,
                unlabeled_subtotals_and_root_projection_receipt=unlabeled_receipt,
                source_repair_overlay_id=source_repair_overlay_id,
                source_repair_receipts=source_repair_receipts,
                source_repair_spec_sha256=source_repair_spec_sha256,
                source_visible_signed_root_receipt=None,
                unit_corroboration_receipts=[],
            )
        terminal_cong_projection = (
            _terminal_cong_continuation_projection_v1(
                pages=effective_pages,
                regions=regions,
                compiled_specs=compiled_specs,
            )
            if type(regions) in {list, tuple}
            else None
        )
        if terminal_cong_projection is not None:
            projected_pages, projected_regions, continuation_receipt = terminal_cong_projection
            candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
                regions=projected_regions,
                page_json_by_version=projected_pages,
                compiled_specs=compiled_specs,
                query_receipt=continuation_receipt["projected_query_receipt"],
            )
            _restore_terminal_cong_projection_source_refs_v1(
                candidate, receipt=continuation_receipt
            )
            return _reseal_candidate(
                candidate,
                primary_root_receipt=None,
                primary_result_context_receipt=None,
                terminal_cong_projection_receipt=continuation_receipt,
                unlabeled_subtotals_and_root_projection_receipt=None,
                source_repair_overlay_id=source_repair_overlay_id,
                source_repair_receipts=source_repair_receipts,
                source_repair_spec_sha256=source_repair_spec_sha256,
                source_visible_signed_root_receipt=None,
                unit_corroboration_receipts=[],
            )
        projected_pages, unit_receipts = (
            _apply_exact_primary_root_unit_corroboration_v1(
                pages=effective_pages,
                regions=regions,
                compiled_specs=compiled_specs,
            )
            if type(regions) in {list, tuple}
            else (
                {
                    version_id: canonical_clone_v1(page)
                    for version_id, page in page_json_by_version.items()
                },
                [],
            )
        )
        selected_regions, primary_context_receipt = (
            _detail_regions_with_primary_result_context_v1(
                pages=projected_pages,
                regions=regions,
                compiled_specs=compiled_specs,
                original_query_receipt=query_receipt,
            )
            if type(regions) in {list, tuple}
            else (canonical_clone_v1(regions), None)
        )
        selected_query_receipt = (
            primary_context_receipt["selected_detail_query_receipt"]
            if primary_context_receipt is not None
            else query_receipt
        )
        candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
            regions=selected_regions,
            page_json_by_version=projected_pages,
            compiled_specs=compiled_specs,
            query_receipt=selected_query_receipt,
        )
        if primary_context_receipt is not None:
            candidate["component_regions"] = canonical_clone_v1(list(regions))
        signed_root_receipt = (
            _replace_derived_root_with_source_visible_signed_root_v1(
                candidate,
                pages=projected_pages,
                regions=selected_regions,
                compiled_specs=compiled_specs,
            )
            if type(selected_regions) in {list, tuple}
            else None
        )
        return _reseal_candidate(
            candidate,
            primary_root_receipt=None,
            primary_result_context_receipt=primary_context_receipt,
            terminal_cong_projection_receipt=None,
            unlabeled_subtotals_and_root_projection_receipt=None,
            source_repair_overlay_id=source_repair_overlay_id,
            source_repair_receipts=source_repair_receipts,
            source_repair_spec_sha256=source_repair_spec_sha256,
            source_visible_signed_root_receipt=signed_root_receipt,
            unit_corroboration_receipts=unit_receipts,
        )
    projected_pages = _apply_primary_root_projection_receipt_v1(
        page_json_by_version=effective_pages, receipt=projection
    )
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=regions,
        page_json_by_version=projected_pages,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if candidate.get("status") == READY:
        _restore_primary_root_mapping_source_refs_v1(candidate, receipt=projection)
    return _reseal_candidate(
        candidate,
        primary_root_receipt=projection,
        primary_result_context_receipt=None,
        terminal_cong_projection_receipt=None,
        unlabeled_subtotals_and_root_projection_receipt=None,
        source_repair_overlay_id=source_repair_overlay_id,
        source_repair_receipts=source_repair_receipts,
        source_repair_spec_sha256=source_repair_spec_sha256,
        source_visible_signed_root_receipt=None,
        unit_corroboration_receipts=[],
    )


def validate_gemini_json_fx_gold_activity_family_candidate_replay_v1(
    value: Any,
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay the family-local structural projection from selected JSON."""

    expected = evaluate_gemini_json_fx_gold_activity_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if type(value) is not dict or not same_typed_json_v1(value, expected):
        raise _error("FX/gold family candidate replay drifted")
    return expected


def build_gemini_json_fx_gold_activity_trials_v1(
    *,
    indexed_query_evidence: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Evaluate and replay the complete indexed Family-31 disposition axis."""

    indexed = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        indexed_query_evidence,
        compiled_specs=compiled_specs,
    )
    candidates: dict[int, dict[str, Any]] = {}
    for cluster in indexed["accepted_clusters"]:
        document_ordinal = cluster["document_ordinal"]
        pages = page_json_by_document.get(document_ordinal)
        if type(pages) is not dict:
            raise _error("FX/gold accepted document page frontier is absent")
        regions = cluster["component_regions"]
        query_receipt = build_gemini_json_fx_gold_activity_region_query_receipt_v1(regions)
        candidate = evaluate_gemini_json_fx_gold_activity_family_cluster_v1(
            regions=regions,
            page_json_by_version=pages,
            compiled_specs=compiled_specs,
            query_receipt=query_receipt,
        )
        candidates[document_ordinal] = (
            validate_gemini_json_fx_gold_activity_family_candidate_replay_v1(
                candidate,
                regions=regions,
                page_json_by_version=pages,
                compiled_specs=compiled_specs,
                query_receipt=query_receipt,
            )
        )

    trials = []
    for document, disposition in zip(
        indexed["selected_document_axis"],
        indexed["candidate_dispositions"],
        strict=True,
    ):
        document_ordinal = document["document_ordinal"]
        candidate = candidates.get(document_ordinal)
        if candidate is not None and candidate["status"] == READY:
            status = READY
            reasons = []
            mappings = canonical_clone_v1(candidate["mappings"])
            selected_candidate_id = candidate["candidate_id"]
        elif candidate is not None:
            status = UNRESOLVED
            reasons = canonical_clone_v1(candidate["reasons"])
            mappings = []
            selected_candidate_id = None
        elif disposition["disposition"] == NOT_OBSERVED:
            status = NOT_OBSERVED
            reasons = []
            mappings = []
            selected_candidate_id = None
        else:
            status = UNRESOLVED
            reasons = canonical_clone_v1(disposition["cluster"]["reasons"])
            mappings = []
            selected_candidate_id = None
        trials.append(
            {
                "candidate_count": int(candidate is not None),
                "candidates": [] if candidate is None else [candidate],
                "document_ordinal": document_ordinal,
                "mappings": mappings,
                "reasons": reasons,
                "selected_candidate_id": selected_candidate_id,
                "source_logical_name": document["source_logical_name"],
                "source_sha256": document["source_sha256"],
                "status": status,
            }
        )
    validate_gemini_json_multitable_hierarchical_sweep_query_bindings_v1(
        trials=trials,
        indexed_query_evidence=indexed,
        compiled_specs=compiled_specs,
    )
    return trials


def validate_gemini_json_fx_gold_activity_replay_v1(
    *,
    base_indexed_query_evidence: Any,
    indexed_query_evidence: Any,
    trials: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild the family query adaptation and every candidate from source JSON."""

    expected_indexed, query_receipts = adapt_gemini_json_fx_gold_activity_indexed_query_evidence_v1(
        base_indexed_query_evidence,
        page_json_by_document=page_json_by_document,
        compiled_specs=compiled_specs,
    )
    if not same_typed_json_v1(indexed_query_evidence, expected_indexed):
        raise _error("FX/gold indexed query replay drifted")
    expected_trials = build_gemini_json_fx_gold_activity_trials_v1(
        indexed_query_evidence=expected_indexed,
        page_json_by_document=page_json_by_document,
        compiled_specs=compiled_specs,
    )
    if type(trials) is not list or not same_typed_json_v1(trials, expected_trials):
        raise _error("FX/gold trial replay drifted")
    material = {
        "indexed_query_evidence_id": expected_indexed["query_evidence_id"],
        "query_adapter_receipt_axis": canonical_clone_v1(query_receipts),
        "query_adapter_receipt_axis_sha256": canonical_json_sha256_v1(query_receipts),
        "trial_axis_sha256": canonical_json_sha256_v1(expected_trials),
    }
    return {
        **material,
        "replay_receipt_id": ("gjfgarv1:receipt:" + canonical_json_sha256_v1(material)),
    }
