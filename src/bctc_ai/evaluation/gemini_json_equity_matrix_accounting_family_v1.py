"""Bidirectional equity-matrix accounting closure over selected Gemini JSON.

Gemini supplies only table structure and source text.  This primitive detects
whether equity components live on rows or columns, normalizes the opposite
movement axis, consumes source-only components and nested visible subtotals,
and maps schema roles only after the complete horizontal and vertical graph
closes.  It has no OCR, geometry, bank, filename, page, note-number, or value
routing behavior.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.accounting_family_topology_v1 import (
    compile_accounting_family_topology_spec_v1,
)
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import (
    _header_dates,
    _matches,
    _money,
)
from bctc_ai.evaluation.source_observation_lane_math_v1 import (
    observed_source_coefficient_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

ENGINE_FORMAT_VERSION = "GEMINI_JSON_EQUITY_MATRIX_ACCOUNTING_FAMILY_V1"
EVALUATION_FORMAT_VERSION = "ACCOUNTING_EQUITY_MATRIX_FAMILY_EVALUATION_SPEC_V1"
SCHEMA_FORMAT_VERSION = "ACCOUNTING_EQUITY_MATRIX_SCHEMA_BINDING_SPEC_V1"
INDEXED_QUERY_EVIDENCE_FORMAT_VERSION = "GEMINI_JSON_INDEXED_EQUITY_MATRIX_QUERY_EVIDENCE_V1"
SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION = (
    "GEMINI_JSON_EQUITY_MATRIX_AUTHENTICATED_SOURCE_REPAIR_ARTIFACT_V1"
)
READY = "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
NOT_OBSERVED = "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
UNRESOLVED = "UNRESOLVED_GEMINI_JSON_FAMILY"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_BIDIRECTIONAL_COMPONENT_MOVEMENT_MATRIX_"
    "EXPLICIT_OWNER_RESET_FENCE_ONE_PAGE_CONTINUATION_EXACT_COMPONENT_INVENTORY_"
    "VISIBLE_HIERARCHICAL_TOTALS_OBSERVED_LANE_ROLLFORWARD_BLANK_SOURCE_NULL_"
    "DOCUMENT_UNIT_CONSENSUS_CONTENT_ADDRESSED_PDF_VISIBLE_SOURCE_REPAIR_"
    "TABLE_ROW_CELL_UNIT_TRANSCRIPTION_ONLY_STRUCTURAL_ROOT_SCHEMA_MAPPING_"
    "PROPOSAL_ONLY_NO_"
    "OCR_GEOMETRY_BANK_FILE_PAGE_NOTE_VALUE_ROUTING_BACKSOLVE_CANONICAL_OR_"
    "EXPORT_AUTHORITY"
)
VALUATION_CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_FINANCIAL_INSTRUMENT_BOOK_AND_FAIR_VALUE_"
    "CLASSIFICATION_MATRIX_EXPLICIT_OWNER_RESET_FENCE_EXHAUSTIVE_DECLARED_ROWS_"
    "FIXED_OR_UNIQUE_PACKED_SPARSE_ALIGNMENT_HORIZONTAL_ROW_AND_VERTICAL_ASSET_"
    "LIABILITY_TOTAL_CLOSURE_TYPED_PERIOD_UNIT_UNAVAILABLE_FAIR_VALUE_PRESERVED_"
    "STRUCTURAL_ROOT_AND_BRANCH_SCHEMA_MAPPING_PROPOSAL_ONLY_NO_OCR_GEOMETRY_"
    "BANK_FILE_PAGE_NOTE_VALUE_ROUTING_OR_EXPORT_AUTHORITY"
)

_PAGE_VERSION = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_DOCUMENT_ID = re.compile(r"gfpstorev1:document:[0-9a-f]{64}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SECTION_ID = re.compile(r"s[1-9][0-9]*\Z")
_TABLE_ID = re.compile(r"t[1-9][0-9]*\Z")
_ROW_ID = re.compile(r"r[1-9][0-9]*\Z")
_COLUMN_ID = re.compile(r"c[1-9][0-9]*\Z")
_EXTRACTION_RUN_ID = re.compile(r"gfpstorev1:run:[0-9a-f]{64}\Z")
_PAGE_ID = re.compile(r"gfpstorev1:page:[0-9a-f]{64}\Z")
_SOURCE_REPAIR_ID = re.compile(r"gjeqmsrv1:repair:[0-9a-f]{64}\Z")
_SOURCE_REPAIR_OVERLAY_ID = re.compile(r"gjeqmsrv1:overlay:[0-9a-f]{64}\Z")
_VISIBLE_ACCOUNTING_MONEY = re.compile(
    r"(?:[-_–—−]|\d+(?:[., ]\d+)*|\(\d+(?:[., ]\d+)*\))\Z"
)
_MAPPED_MOVEMENT_ROLES = ("OPENING", "INCREASE", "DECREASE", "CLOSING")
_MAPPED_TOTAL_ROLES = {
    "OPENING": "OPENING_TOTAL",
    "INCREASE": "INCREASE_TOTAL",
    "DECREASE": "DECREASE_TOTAL",
    "CLOSING": "CLOSING_TOTAL",
}
_ROOT_MAPPING_POLICIES = {
    "SOURCE_VISIBLE_MATRIX_GRAND_TOTAL_CELLS_ONLY",
    "SOURCE_VISIBLE_MATRIX_GRAND_TOTAL_VECTOR_WITH_COMPONENT_VECTORS",
}


class GeminiJsonEquityMatrixAccountingFamilyV1Error(ValueError):
    """The matrix policy, selected source graph, or replay drifted."""


def _error(message: str) -> GeminiJsonEquityMatrixAccountingFamilyV1Error:
    return GeminiJsonEquityMatrixAccountingFamilyV1Error(message)


def _normalized(value: Any) -> str:
    return normalize_vietnamese_anchor_v1(value) if type(value) is str else ""


def _aliases_by_role(topology: Mapping[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for child in topology["children"]:
        aliases = sorted(
            {
                alias
                for matcher in child["matchers"]
                if matcher["within_role"] is None
                for alias in matcher["aliases"]
            }
        )
        if not aliases:
            raise _error("equity-matrix child role has no root-level aliases")
        result[child["role"]] = aliases
    return result


def _compile_alias_map(value: Any, *, label: str) -> dict[str, list[str]]:
    if type(value) is not dict or not value:
        raise _error(f"equity-matrix {label} alias map is absent")
    result = {}
    seen: set[str] = set()
    for role, aliases in value.items():
        if (
            type(role) is not str
            or not role
            or type(aliases) is not list
            or not aliases
            or any(type(alias) is not str or not alias.strip() for alias in aliases)
        ):
            raise _error(f"equity-matrix {label} alias map is invalid")
        normalized = [_normalized(alias) for alias in aliases]
        if any(not alias or alias in seen for alias in normalized):
            raise _error(f"equity-matrix {label} aliases collide")
        seen.update(normalized)
        result[role] = canonical_clone_v1(aliases)
    return result


def _compile_units(value: Any) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if type(value) is not list or not value:
        raise _error("equity-matrix unit bindings are absent")
    result = []
    by_alias: dict[str, dict[str, Any]] = {}
    canonical_units: set[str] = set()
    fields = {
        "accepted",
        "aliases",
        "canonical_unit",
        "document_consensus_eligible",
        "magnitude_power10",
    }
    for raw in value:
        if (
            type(raw) is not dict
            or set(raw) != fields
            or type(raw.get("accepted")) is not bool
            or type(raw.get("document_consensus_eligible")) is not bool
            or type(raw.get("aliases")) is not list
            or not raw["aliases"]
            or any(type(alias) is not str or not alias.strip() for alias in raw["aliases"])
            or type(raw.get("canonical_unit")) is not str
            or not raw["canonical_unit"]
            or raw["canonical_unit"] in canonical_units
            or type(raw.get("magnitude_power10")) is not int
            or raw["magnitude_power10"] < 0
        ):
            raise _error("equity-matrix unit binding is invalid")
        canonical_units.add(raw["canonical_unit"])
        normalized_aliases = [_normalized(alias) for alias in raw["aliases"]]
        if any(not alias or alias in by_alias for alias in normalized_aliases):
            raise _error("equity-matrix unit aliases collide")
        binding = {**canonical_clone_v1(raw), "aliases": normalized_aliases}
        for alias in normalized_aliases:
            by_alias[alias] = binding
        result.append(binding)
    if not any(item["accepted"] for item in result):
        raise _error("equity-matrix requires at least one accepted money unit")
    return result, by_alias


def _source_repair_bbox_v1(
    value: Any, *, pixel_width: int, pixel_height: int
) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or not (0 <= value[0] < value[2] <= pixel_width)
        or not (0 <= value[1] < value[3] <= pixel_height)
    ):
        raise _error("equity-matrix authenticated source-repair crop is invalid")
    return list(value)


def _validate_authenticated_source_repair_artifact_v1(
    value: Any, *, family_id: str
) -> dict[str, Any]:
    """Validate a closed axis of direct PDF table/row/cell transcriptions.

    The artifact is intentionally data-only and content addressed.  It may
    move or restore only row/cell literals and table-unit literals that a
    reviewer read from the authenticated rendered PDF page; arithmetic can
    reject a transcription later but never supplies a replacement value here.
    """

    artifact_fields = {
        "family_id",
        "format_version",
        "overlay_id",
        "policy",
        "repair_axis_sha256",
        "repair_count",
        "repairs",
    }
    policy = (
        "TRANSCRIBE_ONLY_DIRECTLY_PDF_VISIBLE_TABLE_ROW_CELL_UNIT_TOKENS_NO_"
        "EQUATION_BACKSOLVE_NO_BLANK_TO_ZERO_NO_PROVIDER"
    )
    if (
        type(value) is not dict
        or set(value) != artifact_fields
        or value.get("family_id") != family_id
        or value.get("format_version") != SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION
        or value.get("policy") != policy
        or type(value.get("repairs")) is not list
        or not value["repairs"]
        or type(value.get("repair_count")) is not int
        or value["repair_count"] != len(value["repairs"])
        or _SHA256.fullmatch(value.get("repair_axis_sha256", "")) is None
        or _SOURCE_REPAIR_OVERLAY_ID.fullmatch(value.get("overlay_id", "")) is None
    ):
        raise _error("equity-matrix authenticated source-repair artifact is invalid")
    repair_fields = {
        "base_page_json_sha256",
        "base_page_json_version_id",
        "column_axis_exact",
        "effective_page_json_sha256",
        "extraction_run_id",
        "repair_id",
        "repair_reason",
        "row_repairs",
        "source_binding",
        "stored_canonical_json_sha256",
        "table_unit_repair",
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
    row_fields = {
        "after_values_exact",
        "before_values_exact",
        "cell_repairs",
        "row_hierarchy_path_exact",
        "row_id",
        "row_kind",
        "row_label_exact",
    }
    cell_fields = {
        "after_exact",
        "before_exact",
        "cell_id",
        "column_header_path_exact",
        "column_ordinal",
        "visual_state",
    }
    table_unit_fields = {
        "after_exact",
        "before_exact",
        "source_surface_axis_exact",
        "visual_state",
    }
    checked_repairs = []
    seen_versions: set[str] = set()
    for raw_repair in value["repairs"]:
        if type(raw_repair) is not dict or set(raw_repair) != repair_fields:
            raise _error("equity-matrix authenticated source-repair fields drifted")
        repair = canonical_clone_v1(raw_repair)
        source = repair["source_binding"]
        if type(source) is not dict or set(source) != source_fields:
            raise _error("equity-matrix authenticated source-repair source fields drifted")
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
            or source.get("render_dpi") not in {200, 300}
            or source.get("media_type") != "image/png"
        ):
            raise _error("equity-matrix authenticated source-repair source is invalid")
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
            raise _error("equity-matrix authenticated source-repair source identity drifted")
        if (
            _PAGE_VERSION.fullmatch(repair.get("base_page_json_version_id", "")) is None
            or repair["base_page_json_version_id"] in seen_versions
            or _EXTRACTION_RUN_ID.fullmatch(repair.get("extraction_run_id", "")) is None
            or any(
                _SHA256.fullmatch(repair.get(field, "")) is None
                for field in (
                    "base_page_json_sha256",
                    "effective_page_json_sha256",
                    "stored_canonical_json_sha256",
                )
            )
        ):
            raise _error("equity-matrix authenticated source-repair page binding is invalid")
        seen_versions.add(repair["base_page_json_version_id"])
        expected_version_id = "gfpstorev1:json:" + canonical_json_sha256_v1(
            {
                "canonical_json_sha256": repair["stored_canonical_json_sha256"],
                "extraction_run_id": repair["extraction_run_id"],
                "page_id": source["page_id"],
            }
        )
        if repair["base_page_json_version_id"] != expected_version_id:
            raise _error("equity-matrix authenticated source-repair page identity drifted")
        table_ref = repair["table_ref"]
        if (
            type(table_ref) is not dict
            or set(table_ref) != table_fields
            or _SECTION_ID.fullmatch(table_ref.get("section_id", "")) is None
            or _TABLE_ID.fullmatch(table_ref.get("table_id", "")) is None
            or _SHA256.fullmatch(table_ref.get("base_table_sha256", "")) is None
            or _SHA256.fullmatch(table_ref.get("effective_table_sha256", "")) is None
        ):
            raise _error("equity-matrix authenticated source-repair table binding is invalid")
        columns = repair["column_axis_exact"]
        if (
            type(columns) is not list
            or not columns
            or any(
                type(column) is not dict
                or set(column) != {"header_path_exact", "value_kind"}
                or type(column.get("header_path_exact")) is not list
                or not column["header_path_exact"]
                or any(type(item) is not str or not item for item in column["header_path_exact"])
                or column.get("value_kind") not in {"MONEY", "TEXT"}
                for column in columns
            )
        ):
            raise _error("equity-matrix authenticated source-repair column axis is invalid")
        table_unit_repair = repair["table_unit_repair"]
        if table_unit_repair is not None:
            if (
                type(table_unit_repair) is not dict
                or set(table_unit_repair) != table_unit_fields
                or (
                    table_unit_repair.get("before_exact") is not None
                    and (
                        type(table_unit_repair["before_exact"]) is not str
                        or not table_unit_repair["before_exact"].strip()
                    )
                )
                or type(table_unit_repair.get("after_exact")) is not str
                or not table_unit_repair["after_exact"].strip()
                or same_typed_json_v1(
                    table_unit_repair.get("before_exact"),
                    table_unit_repair["after_exact"],
                )
                or table_unit_repair.get("visual_state") != "PRINTED_UNIT"
            ):
                raise _error("equity-matrix authenticated source-repair table unit is invalid")
            surface_axis = table_unit_repair.get("source_surface_axis_exact")
            expected_column_ids = [
                f"c{ordinal}"
                for ordinal, column in enumerate(columns, start=1)
                if column["value_kind"] == "MONEY"
            ]
            if (
                type(surface_axis) is not list
                or not surface_axis
                or any(
                    type(surface) is not dict
                    or set(surface) != {"column_id", "source_exact"}
                    or _COLUMN_ID.fullmatch(surface.get("column_id", "")) is None
                    or surface.get("source_exact") != table_unit_repair["after_exact"]
                    for surface in surface_axis
                )
                or [surface["column_id"] for surface in surface_axis]
                != expected_column_ids
            ):
                raise _error(
                    "equity-matrix authenticated source-repair table unit surface axis is invalid"
                )
        visual = repair["visual_evidence"]
        if (
            type(visual) is not dict
            or set(visual) != visual_fields
            or visual.get("evidence_kind")
            != "AUTHENTICATED_MANUAL_VISUAL_ROW_CELL_TRANSCRIPTION"
            or visual.get("render_mode") != "PDF_PAGE_GET_PIXMAP_DPI_EXACT"
            or re.fullmatch(r"20\d{2}-[01]\d-[0-3]\d", visual.get("reviewed_utc_date", ""))
            is None
            or _SHA256.fullmatch(visual.get("table_crop_rgb_sha256", "")) is None
        ):
            raise _error("equity-matrix authenticated source-repair visual evidence is invalid")
        _source_repair_bbox_v1(
            visual["table_crop_bbox_pixels_xyxy"],
            pixel_width=source["pixel_width"],
            pixel_height=source["pixel_height"],
        )
        rows = repair["row_repairs"]
        if type(rows) is not list or (not rows and table_unit_repair is None):
            raise _error("equity-matrix authenticated source-repair change axis is empty")
        checked_rows = []
        seen_rows: set[str] = set()
        seen_cells: set[str] = set()
        for raw_row in rows:
            if type(raw_row) is not dict or set(raw_row) != row_fields:
                raise _error("equity-matrix authenticated source-repair row fields drifted")
            row = canonical_clone_v1(raw_row)
            row_match = _ROW_ID.fullmatch(row.get("row_id", ""))
            before = row.get("before_values_exact")
            after = row.get("after_values_exact")
            if (
                row_match is None
                or row["row_id"] in seen_rows
                or type(row.get("row_label_exact")) is not str
                or not row["row_label_exact"].strip()
                or row.get("row_kind") not in {"ITEM", "SUBTOTAL", "TOTAL"}
                or type(row.get("row_hierarchy_path_exact")) is not list
                or not row["row_hierarchy_path_exact"]
                or any(
                    type(item) is not str or not item
                    for item in row["row_hierarchy_path_exact"]
                )
                or type(before) is not list
                or type(after) is not list
                or len(before) != len(columns)
                or len(after) != len(columns)
            ):
                raise _error("equity-matrix authenticated source-repair row is invalid")
            seen_rows.add(row["row_id"])
            cells = row["cell_repairs"]
            if type(cells) is not list or not cells:
                raise _error("equity-matrix authenticated source-repair cell axis is empty")
            changed_ordinals = [
                ordinal
                for ordinal, (old, new) in enumerate(zip(before, after, strict=True), start=1)
                if not same_typed_json_v1(old, new)
            ]
            checked_cells = []
            for raw_cell in cells:
                if type(raw_cell) is not dict or set(raw_cell) != cell_fields:
                    raise _error("equity-matrix authenticated source-repair cell fields drifted")
                cell = canonical_clone_v1(raw_cell)
                match = re.fullmatch(rf"{re.escape(row['row_id'])}:c([1-9][0-9]*)", cell.get("cell_id", ""))
                ordinal = cell.get("column_ordinal")
                if (
                    match is None
                    or cell["cell_id"] in seen_cells
                    or type(ordinal) is not int
                    or ordinal != int(match.group(1))
                    or not 1 <= ordinal <= len(columns)
                    or columns[ordinal - 1]["value_kind"] != "MONEY"
                    or not same_typed_json_v1(cell.get("column_header_path_exact"), columns[ordinal - 1]["header_path_exact"])
                    or not same_typed_json_v1(cell.get("before_exact"), before[ordinal - 1])
                    or not same_typed_json_v1(cell.get("after_exact"), after[ordinal - 1])
                    or type(cell.get("after_exact")) is not str
                    or _VISIBLE_ACCOUNTING_MONEY.fullmatch(cell["after_exact"].strip()) is None
                    or (
                        cell.get("before_exact") is None
                        and cell["after_exact"].strip()
                        not in {"-", "_", "–", "—", "−"}
                        and _money(cell["after_exact"])["coefficient"] == 0
                    )
                    or cell.get("visual_state")
                    != ("DASH" if cell["after_exact"].strip() in {"-", "_", "–", "—", "−"} else "PRINTED_MONEY")
                ):
                    raise _error("equity-matrix authenticated source-repair cell is invalid")
                seen_cells.add(cell["cell_id"])
                checked_cells.append(cell)
            checked_cells.sort(key=lambda item: item["column_ordinal"])
            if cells != checked_cells or [item["column_ordinal"] for item in cells] != changed_ordinals:
                raise _error("equity-matrix authenticated source-repair changed-cell axis drifted")
            checked_rows.append(row)
        checked_rows.sort(key=lambda item: int(item["row_id"][1:]))
        if rows != checked_rows:
            raise _error("equity-matrix authenticated source-repair row axis is unordered")
        if repair["repair_reason"] not in {
            "VISIBLE_PDF_TABLE_UNIT_MISSING_IN_SELECTED_JSON",
            "VISIBLE_PDF_MONEY_TOKEN_MISTRANSCRIBED_IN_SELECTED_JSON",
            "VISIBLE_PDF_ROW_CELL_AXIS_MISALIGNED_IN_SELECTED_JSON",
        }:
            raise _error("equity-matrix authenticated source-repair reason is invalid")
        if (
            repair["repair_reason"]
            == "VISIBLE_PDF_TABLE_UNIT_MISSING_IN_SELECTED_JSON"
        ) != (table_unit_repair is not None and not rows):
            raise _error("equity-matrix authenticated source-repair reason drifts change kind")
        expected_repair_id = "gjeqmsrv1:repair:" + canonical_json_sha256_v1(
            {key: repair[key] for key in repair if key != "repair_id"}
        )
        if repair.get("repair_id") != expected_repair_id:
            raise _error("equity-matrix authenticated source-repair identity drifted")
        checked_repairs.append(repair)
    checked_repairs.sort(
        key=lambda item: (
            item["source_binding"]["source_logical_name"],
            item["source_binding"]["physical_page"],
            int(item["table_ref"]["section_id"][1:]),
            int(item["table_ref"]["table_id"][1:]),
        )
    )
    if value["repairs"] != checked_repairs:
        raise _error("equity-matrix authenticated source-repair axis is unordered")
    if value["repair_axis_sha256"] != canonical_json_sha256_v1(checked_repairs):
        raise _error("equity-matrix authenticated source-repair axis identity drifted")
    material = {
        "family_id": family_id,
        "format_version": SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION,
        "policy": policy,
        "repair_axis_sha256": value["repair_axis_sha256"],
        "repair_count": len(checked_repairs),
        "repairs": checked_repairs,
    }
    expected_overlay_id = "gjeqmsrv1:overlay:" + canonical_json_sha256_v1(material)
    if value["overlay_id"] != expected_overlay_id:
        raise _error("equity-matrix authenticated source-repair overlay identity drifted")
    return {**material, "overlay_id": expected_overlay_id}


def _compile_authenticated_source_repair_artifact_v1(
    value: Any, *, family_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    fields = {"artifact_format_version", "overlay_id", "path", "sha256", "size_bytes"}
    if (
        type(value) is not dict
        or set(value) != fields
        or value.get("artifact_format_version") != SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION
        or type(value.get("path")) is not str
        or not value["path"]
        or value["path"].startswith("/")
        or ".." in value["path"].split("/")
        or _SHA256.fullmatch(value.get("sha256", "")) is None
        or type(value.get("size_bytes")) is not int
        or value["size_bytes"] <= 0
        or _SOURCE_REPAIR_OVERLAY_ID.fullmatch(value.get("overlay_id", "")) is None
    ):
        raise _error("equity-matrix authenticated source-repair artifact ref is invalid")
    path = Path(__file__).resolve().parents[3] / value["path"]
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise _error("equity-matrix authenticated source-repair artifact is absent") from exc
    if len(payload) != value["size_bytes"] or sha256(payload).hexdigest() != value["sha256"]:
        raise _error("equity-matrix authenticated source-repair artifact bytes drifted")
    try:
        raw = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("equity-matrix authenticated source-repair artifact JSON is invalid") from exc
    compiled = _validate_authenticated_source_repair_artifact_v1(raw, family_id=family_id)
    if compiled["overlay_id"] != value["overlay_id"]:
        raise _error("equity-matrix authenticated source-repair artifact ref drifted")
    return compiled, canonical_clone_v1(value)


def _compile_valuation_matrix_specs_v1(
    *, topology: Mapping[str, Any], evaluation_spec: Any, schema_binding_spec: Any
) -> dict[str, Any]:
    """Compile the declarative carrying/fair-value matrix variant."""

    if (
        type(evaluation_spec) is not dict
        or set(evaluation_spec)
        != {
            "blank_zero_policy",
            "closure_policy",
            "family_id",
            "format_version",
            "matrix_policy",
        }
        or evaluation_spec.get("format_version") != EVALUATION_FORMAT_VERSION
        or evaluation_spec.get("family_id") != topology["family_id"]
        or evaluation_spec.get("blank_zero_policy") != "ZERO_ONLY_AFTER_COMPLETE_MATRIX_GRAPH_EXACT"
        or evaluation_spec.get("closure_policy")
        != "EXACT_CLASSIFICATION_ROWS_AND_ASSET_LIABILITY_BRANCH_TOTALS"
    ):
        raise _error("valuation-matrix evaluation spec is invalid")
    policy = evaluation_spec.get("matrix_policy")
    policy_fields = {
        "accepted_orientations",
        "aggregate_duplicate_roles",
        "asset_role_aliases",
        "asset_total_aliases",
        "book_total_header_aliases",
        "book_value_header_aliases",
        "fair_value_header_aliases",
        "liability_role_aliases",
        "liability_total_aliases",
        "matrix_kind",
        "max_continuation_pages",
        "minimum_mapped_component_roles",
        "unavailable_value_aliases",
        "unit_bindings",
    }
    if (
        type(policy) is not dict
        or set(policy) != policy_fields
        or policy.get("matrix_kind") != "VALUATION_CLASSIFICATION"
        or policy.get("accepted_orientations") != ["COMPONENT_ROWS"]
        or policy.get("max_continuation_pages") != 1
        or type(policy.get("minimum_mapped_component_roles")) is not int
        or policy["minimum_mapped_component_roles"] < 4
    ):
        raise _error("valuation-matrix policy is invalid")
    asset_aliases = _compile_alias_map(policy["asset_role_aliases"], label="asset role")
    liability_aliases = _compile_alias_map(policy["liability_role_aliases"], label="liability role")
    if set(asset_aliases) & set(liability_aliases):
        raise _error("valuation-matrix asset and liability roles collide")
    role_aliases = {**asset_aliases, **liability_aliases}
    aggregate_roles = policy["aggregate_duplicate_roles"]
    if (
        type(aggregate_roles) is not list
        or len(aggregate_roles) != len(set(aggregate_roles))
        or not set(aggregate_roles) <= set(role_aliases)
    ):
        raise _error("valuation-matrix aggregate role policy is invalid")

    def aliases(field: str) -> list[str]:
        values = policy.get(field)
        normalized = (
            [item.strip() for item in values]
            if type(values) is list and field == "unavailable_value_aliases"
            else [_normalized(item) for item in values]
            if type(values) is list
            else []
        )
        if (
            type(values) is not list
            or not values
            or any(type(item) is not str or not item.strip() for item in values)
            or any(not item for item in normalized)
            or len(set(normalized)) != len(values)
        ):
            raise _error(f"valuation-matrix {field} is invalid")
        return canonical_clone_v1(values)

    marker_fields = (
        "asset_total_aliases",
        "book_total_header_aliases",
        "book_value_header_aliases",
        "fair_value_header_aliases",
        "liability_total_aliases",
        "unavailable_value_aliases",
    )
    marker_aliases = {field: aliases(field) for field in marker_fields}
    units, unit_by_alias = _compile_units(policy["unit_bindings"])
    schema_fields = {
        "book_branch_report_norm_id",
        "component_role_bindings",
        "fair_branch_report_norm_id",
        "family_id",
        "family_root_report_norm_id",
        "format_version",
        "total_role_bindings",
    }
    if (
        type(schema_binding_spec) is not dict
        or set(schema_binding_spec) != schema_fields
        or schema_binding_spec.get("format_version") != SCHEMA_FORMAT_VERSION
        or schema_binding_spec.get("family_id") != topology["family_id"]
        or any(
            type(schema_binding_spec.get(field)) is not int or schema_binding_spec[field] <= 0
            for field in (
                "book_branch_report_norm_id",
                "fair_branch_report_norm_id",
                "family_root_report_norm_id",
            )
        )
    ):
        raise _error("valuation-matrix schema binding spec is invalid")

    def paired_bindings(
        value: Any, *, expected_roles: set[str], label: str
    ) -> dict[str, dict[str, int]]:
        fields = {"book_report_norm_id", "fair_report_norm_id", "role"}
        if type(value) is not list or len(value) != len(expected_roles):
            raise _error(f"valuation-matrix {label} binding axis is incomplete")
        result: dict[str, dict[str, int]] = {}
        for raw in value:
            if (
                type(raw) is not dict
                or set(raw) != fields
                or raw.get("role") not in expected_roles
                or raw["role"] in result
                or type(raw.get("book_report_norm_id")) is not int
                or raw["book_report_norm_id"] <= 0
                or type(raw.get("fair_report_norm_id")) is not int
                or raw["fair_report_norm_id"] <= 0
            ):
                raise _error(f"valuation-matrix {label} binding is invalid")
            result[raw["role"]] = {
                "book_report_norm_id": raw["book_report_norm_id"],
                "fair_report_norm_id": raw["fair_report_norm_id"],
            }
        if set(result) != expected_roles:
            raise _error(f"valuation-matrix {label} binding roles are incomplete")
        return result

    component_bindings = paired_bindings(
        schema_binding_spec["component_role_bindings"],
        expected_roles=set(role_aliases),
        label="component",
    )
    total_bindings = paired_bindings(
        schema_binding_spec["total_role_bindings"],
        expected_roles={"BOOK_TOTAL_ASSETS", "BOOK_TOTAL_LIABILITIES"},
        label="total",
    )
    report_norm_ids = {
        schema_binding_spec["family_root_report_norm_id"],
        schema_binding_spec["book_branch_report_norm_id"],
        schema_binding_spec["fair_branch_report_norm_id"],
        *(
            report_norm_id
            for binding in [*component_bindings.values(), *total_bindings.values()]
            for report_norm_id in binding.values()
        ),
    }
    expected_id_count = 3 + 2 * (len(component_bindings) + len(total_bindings))
    if len(report_norm_ids) != expected_id_count:
        raise _error("valuation-matrix schema report norm IDs collide")
    query_policy = {
        "hard_negative_aliases": canonical_clone_v1(topology["hard_negative_aliases"]),
        "matrix_kind": "VALUATION_CLASSIFICATION",
        "max_continuation_pages": 1,
        "minimum_mapped_component_roles": policy["minimum_mapped_component_roles"],
        "owner_aliases": canonical_clone_v1(topology["parent"]["aliases"]),
        "reset_aliases": canonical_clone_v1(topology["structural_reset_aliases"]),
    }
    return {
        "aliases_by_role": role_aliases,
        "asset_role_aliases_by_role": asset_aliases,
        "book_branch_report_norm_id": schema_binding_spec["book_branch_report_norm_id"],
        "claim_boundary": VALUATION_CLAIM_BOUNDARY,
        "component_report_norm_id_by_role": {
            role: binding["book_report_norm_id"] for role, binding in component_bindings.items()
        },
        "engine_format_version": ENGINE_FORMAT_VERSION,
        "evaluation": canonical_clone_v1(evaluation_spec),
        "fair_branch_report_norm_id": schema_binding_spec["fair_branch_report_norm_id"],
        "family_id": topology["family_id"],
        "family_root_report_norm_id": schema_binding_spec["family_root_report_norm_id"],
        "liability_role_aliases_by_role": liability_aliases,
        "query_policy": query_policy,
        "schema": canonical_clone_v1(schema_binding_spec),
        "topology": canonical_clone_v1(topology),
        "unit_binding_by_alias": unit_by_alias,
        "unit_bindings": units,
        "valuation_component_bindings_by_role": component_bindings,
        "valuation_marker_aliases": marker_aliases,
        "valuation_mode": True,
        "valuation_total_bindings_by_role": total_bindings,
    }


def compile_gemini_json_equity_matrix_family_specs_v1(
    topology_spec: Any, evaluation_spec: Any, schema_binding_spec: Any
) -> dict[str, Any]:
    """Compile one strict declarative matrix family triplet."""

    try:
        topology = compile_accounting_family_topology_spec_v1(topology_spec)
    except ValueError as exc:
        raise _error("equity-matrix topology spec is invalid") from exc
    if (
        type(evaluation_spec) is dict
        and type(evaluation_spec.get("matrix_policy")) is dict
        and evaluation_spec["matrix_policy"].get("matrix_kind") == "CATEGORICAL_PERIOD_MATRIX"
    ):
        from bctc_ai.evaluation.gemini_json_categorical_period_matrix_v1 import (
            compile_gemini_json_categorical_period_matrix_specs_v1,
        )

        return compile_gemini_json_categorical_period_matrix_specs_v1(
            topology=topology,
            evaluation_spec=evaluation_spec,
            schema_binding_spec=schema_binding_spec,
        )
    if (
        topology.get("family_id") == "LIQUIDITY_RISK"
        and type(evaluation_spec) is dict
        and type(evaluation_spec.get("matrix_policy")) is dict
        and evaluation_spec["matrix_policy"].get("matrix_kind") == "CURRENCY_RISK_CLASSIFICATION"
    ):
        from bctc_ai.evaluation.gemini_json_liquidity_risk_matrix_v1 import (
            compile_gemini_json_liquidity_risk_matrix_specs_v1,
        )

        return compile_gemini_json_liquidity_risk_matrix_specs_v1(
            topology=topology,
            evaluation_spec=evaluation_spec,
            schema_binding_spec=schema_binding_spec,
        )
    if (
        topology.get("family_id") == "INTEREST_RATE_RISK"
        and type(evaluation_spec) is dict
        and type(evaluation_spec.get("matrix_policy")) is dict
        and evaluation_spec["matrix_policy"].get("matrix_kind") == "CURRENCY_RISK_CLASSIFICATION"
    ):
        from bctc_ai.evaluation.gemini_json_interest_rate_risk_matrix_v1 import (
            compile_gemini_json_interest_rate_risk_matrix_specs_v1,
        )

        return compile_gemini_json_interest_rate_risk_matrix_specs_v1(
            topology=topology,
            evaluation_spec=evaluation_spec,
            schema_binding_spec=schema_binding_spec,
        )
    if (
        type(evaluation_spec) is dict
        and type(evaluation_spec.get("matrix_policy")) is dict
        and evaluation_spec["matrix_policy"].get("matrix_kind") == "CURRENCY_RISK_CLASSIFICATION"
    ):
        from bctc_ai.evaluation.gemini_json_currency_risk_matrix_v1 import (
            compile_gemini_json_currency_risk_matrix_specs_v1,
        )

        return compile_gemini_json_currency_risk_matrix_specs_v1(
            topology=topology,
            evaluation_spec=evaluation_spec,
            schema_binding_spec=schema_binding_spec,
        )
    if (
        type(evaluation_spec) is dict
        and type(evaluation_spec.get("matrix_policy")) is dict
        and evaluation_spec["matrix_policy"].get("matrix_kind") == "VALUATION_CLASSIFICATION"
    ):
        return _compile_valuation_matrix_specs_v1(
            topology=topology,
            evaluation_spec=evaluation_spec,
            schema_binding_spec=schema_binding_spec,
        )
    evaluation_fields = {
        "blank_zero_policy",
        "closure_policy",
        "family_id",
        "format_version",
        "matrix_policy",
    }
    if (
        type(evaluation_spec) is not dict
        or not evaluation_fields <= set(evaluation_spec)
        or not set(evaluation_spec)
        <= evaluation_fields | {"authenticated_source_repair_artifact_ref"}
        or evaluation_spec.get("format_version") != EVALUATION_FORMAT_VERSION
        or evaluation_spec.get("family_id") != topology["family_id"]
        or (
            evaluation_spec.get("blank_zero_policy"),
            evaluation_spec.get("closure_policy"),
        )
        not in {
            (
                "PRESERVE_BLANK_SOURCE_LANES_AS_NULL_NEVER_INFER_ZERO",
                "EXACT_WHERE_FULLY_OBSERVED_INCOMPLETE_BLANK_LANES_NON_BLOCKING",
            ),
            # Legacy declarations remain loadable while all consumers migrate.
            # Runtime semantics are nevertheless source-safe: a blank is null.
            (
                "ZERO_ONLY_AFTER_COMPLETE_MATRIX_GRAPH_EXACT",
                "EXACT_HORIZONTAL_TOTALS_AND_VERTICAL_ROLLFORWARD_ALL_SELECTED_CELLS",
            ),
        }
    ):
        raise _error("equity-matrix evaluation spec is invalid")
    policy = evaluation_spec["matrix_policy"]
    policy_fields = {
        "accepted_orientations",
        "max_continuation_pages",
        "minimum_mapped_component_roles",
        "movement_role_aliases",
        "source_only_component_aliases",
        "total_aliases",
        "unit_bindings",
    }
    if (
        type(policy) is not dict
        or not policy_fields
        <= set(policy)
        <= policy_fields
        | {
            "component_row_continuation_policy",
            "directional_duplicate_control_policy",
            "hierarchy_policy",
            "implicit_owner_policy",
            "primary_statement_root_unit_policy",
            "signed_branch_policy",
            "supplemental_component_group_policy",
            "supplemental_movement_policy",
        }
        or type(policy.get("accepted_orientations")) is not list
        or not policy["accepted_orientations"]
        or any(
            orientation not in {"COMPONENT_COLUMNS", "COMPONENT_ROWS"}
            for orientation in policy["accepted_orientations"]
        )
        or len(policy["accepted_orientations"]) != len(set(policy["accepted_orientations"]))
        or policy.get("max_continuation_pages") != 1
        or type(policy.get("minimum_mapped_component_roles")) is not int
        or policy["minimum_mapped_component_roles"] < 2
        or type(policy.get("total_aliases")) is not list
        or not policy["total_aliases"]
        or any(type(alias) is not str or not alias.strip() for alias in policy["total_aliases"])
    ):
        raise _error("equity-matrix policy is invalid")
    movement_aliases = _compile_alias_map(policy["movement_role_aliases"], label="movement")
    if set(movement_aliases) != set(_MAPPED_MOVEMENT_ROLES):
        raise _error("equity-matrix movement roles are incomplete")
    component_row_continuation_policy = policy.get(
        "component_row_continuation_policy",
        {
            "allow_blank_leading_label_tail": False,
            "mode": "DISABLED",
        },
    )
    if (
        type(component_row_continuation_policy) is not dict
        or set(component_row_continuation_policy)
        != {"allow_blank_leading_label_tail", "mode"}
        or type(component_row_continuation_policy.get("allow_blank_leading_label_tail"))
        is not bool
        or component_row_continuation_policy.get("mode")
        not in {
            "DISABLED",
            "EXPLICIT_RECIPROCAL_ADJACENT_COMPLEMENTARY_COMPONENT_AXIS",
        }
        or (
            component_row_continuation_policy["mode"] == "DISABLED"
            and component_row_continuation_policy["allow_blank_leading_label_tail"]
        )
    ):
        raise _error("equity-matrix component-row continuation policy is invalid")
    directional_duplicate_control_policy = policy.get(
        "directional_duplicate_control_policy",
        {"mode": "DISABLED", "subordinate_aliases_by_role": {}},
    )
    if (
        type(directional_duplicate_control_policy) is not dict
        or set(directional_duplicate_control_policy)
        != {"mode", "subordinate_aliases_by_role"}
        or directional_duplicate_control_policy.get("mode")
        not in {"DISABLED", "EXACT_ADJACENT_DIRECTIONAL_CHILD_CONTROL"}
        or type(
            directional_duplicate_control_policy.get("subordinate_aliases_by_role")
        )
        is not dict
    ):
        raise _error("equity-matrix directional duplicate-control policy is invalid")
    directional_duplicate_aliases = (
        _compile_alias_map(
            directional_duplicate_control_policy["subordinate_aliases_by_role"],
            label="directional duplicate control",
        )
        if directional_duplicate_control_policy["subordinate_aliases_by_role"]
        else {}
    )
    if (
        not set(directional_duplicate_aliases) <= {"INCREASE", "DECREASE"}
        or (
            directional_duplicate_control_policy["mode"] == "DISABLED"
            and directional_duplicate_aliases
        )
        or (
            directional_duplicate_control_policy["mode"]
            == "EXACT_ADJACENT_DIRECTIONAL_CHILD_CONTROL"
            and not directional_duplicate_aliases
        )
    ):
        raise _error("equity-matrix directional duplicate-control aliases are invalid")
    implicit_owner_policy = policy.get(
        "implicit_owner_policy",
        {"minimum_mapped_component_roles": 0, "mode": "DISABLED"},
    )
    if (
        type(implicit_owner_policy) is not dict
        or set(implicit_owner_policy) != {"minimum_mapped_component_roles", "mode"}
        or implicit_owner_policy.get("mode")
        not in {
            "DISABLED",
            "UNIQUE_COMPLETE_MATRIX_PLUS_SUPPLEMENTAL_COMPONENT_GROUP",
        }
        or type(implicit_owner_policy.get("minimum_mapped_component_roles")) is not int
        or implicit_owner_policy["minimum_mapped_component_roles"] < 0
        or (
            implicit_owner_policy["mode"] == "DISABLED"
            and implicit_owner_policy["minimum_mapped_component_roles"] != 0
        )
        or (
            implicit_owner_policy["mode"]
            == "UNIQUE_COMPLETE_MATRIX_PLUS_SUPPLEMENTAL_COMPONENT_GROUP"
            and implicit_owner_policy["minimum_mapped_component_roles"] < 4
        )
    ):
        raise _error("equity-matrix implicit-owner policy is invalid")
    primary_statement_root_unit_policy = policy.get(
        "primary_statement_root_unit_policy", {"mode": "DISABLED"}
    )
    if (
        type(primary_statement_root_unit_policy) is not dict
        or set(primary_statement_root_unit_policy) != {"mode"}
        or primary_statement_root_unit_policy.get("mode")
        not in {"DISABLED", "EXACT_FAMILY_ROOT_BOUNDARY_VECTOR_CORROBORATION"}
    ):
        raise _error("equity-matrix primary-statement root-unit policy is invalid")
    supplemental_policy = policy.get(
        "supplemental_movement_policy",
        {
            "decomposition_equations": [],
            "mapped_roles": [],
            "primary_rollforward_additive_roles": [],
            "role_aliases": {},
        },
    )
    supplemental_fields = {
        "decomposition_equations",
        "mapped_roles",
        "primary_rollforward_additive_roles",
        "role_aliases",
    }
    if (
        type(supplemental_policy) is not dict
        or set(supplemental_policy) != supplemental_fields
        or type(supplemental_policy.get("role_aliases")) is not dict
    ):
        raise _error("equity-matrix supplemental movement policy is invalid")
    supplemental_aliases = (
        _compile_alias_map(supplemental_policy["role_aliases"], label="supplemental movement")
        if supplemental_policy["role_aliases"]
        else {}
    )
    signed_branch_policy = policy.get(
        "signed_branch_policy", {"branch_aliases": {}, "branch_multipliers": {}}
    )
    if (
        type(signed_branch_policy) is not dict
        or set(signed_branch_policy) != {"branch_aliases", "branch_multipliers"}
        or type(signed_branch_policy.get("branch_aliases")) is not dict
        or type(signed_branch_policy.get("branch_multipliers")) is not dict
    ):
        raise _error("equity-matrix signed branch policy is invalid")
    signed_branch_aliases = (
        _compile_alias_map(signed_branch_policy["branch_aliases"], label="signed branch")
        if signed_branch_policy["branch_aliases"]
        else {}
    )
    if (
        set(signed_branch_aliases) != set(signed_branch_policy["branch_multipliers"])
        or any(
            type(multiplier) is not int or multiplier not in {-1, 1}
            for multiplier in signed_branch_policy["branch_multipliers"].values()
        )
        or (
            signed_branch_aliases
            and set(signed_branch_policy["branch_multipliers"].values()) != {-1, 1}
        )
    ):
        raise _error("equity-matrix signed branch projection is invalid")
    supplemental_roles = set(supplemental_aliases)
    primary_alias_axis = {
        _normalized(alias) for aliases in movement_aliases.values() for alias in aliases
    }
    supplemental_alias_axis = {
        _normalized(alias) for aliases in supplemental_aliases.values() for alias in aliases
    }
    if supplemental_roles & set(_MAPPED_MOVEMENT_ROLES) or (
        primary_alias_axis & supplemental_alias_axis
    ):
        raise _error("primary and supplemental movement declarations collide")
    for field in ("mapped_roles", "primary_rollforward_additive_roles"):
        values = supplemental_policy.get(field)
        if (
            type(values) is not list
            or len(values) != len(set(values))
            or not set(values) <= supplemental_roles
        ):
            raise _error("supplemental movement role projection is invalid")
    equations = supplemental_policy.get("decomposition_equations")
    if type(equations) is not list:
        raise _error("supplemental movement equations are invalid")
    for equation in equations:
        if (
            type(equation) is not dict
            or set(equation) != {"result_role", "term_multipliers"}
            or equation.get("result_role")
            not in {
                *_MAPPED_MOVEMENT_ROLES,
                *supplemental_roles,
            }
            or type(equation.get("term_multipliers")) is not dict
            or not equation["term_multipliers"]
            or any(
                role not in {*_MAPPED_MOVEMENT_ROLES, *supplemental_roles}
                or type(multiplier) is not int
                or multiplier == 0
                for role, multiplier in equation["term_multipliers"].items()
            )
        ):
            raise _error("supplemental movement equation is invalid")
    source_only_aliases = _compile_alias_map(
        policy["source_only_component_aliases"], label="source-only component"
    )
    mapped_aliases = _aliases_by_role(topology)
    supplemental_component_group_policy = policy.get(
        "supplemental_component_group_policy",
        {
            "group_source_only_role": None,
            "mapped_child_roles": [],
            "mode": "DISABLED",
            "owner_aliases": [],
        },
    )
    if (
        type(supplemental_component_group_policy) is not dict
        or set(supplemental_component_group_policy)
        != {
            "group_source_only_role",
            "mapped_child_roles",
            "mode",
            "owner_aliases",
        }
        or supplemental_component_group_policy.get("mode")
        not in {"DISABLED", "EXACT_SUPPLEMENTAL_COMPONENT_GROUP_MATRIX"}
        or type(supplemental_component_group_policy.get("mapped_child_roles")) is not list
        or len(supplemental_component_group_policy["mapped_child_roles"])
        != len(set(supplemental_component_group_policy["mapped_child_roles"]))
        or not set(supplemental_component_group_policy["mapped_child_roles"])
        <= set(mapped_aliases)
        or type(supplemental_component_group_policy.get("owner_aliases")) is not list
        or any(
            type(alias) is not str or not alias.strip()
            for alias in supplemental_component_group_policy["owner_aliases"]
        )
        or len(
            {
                _normalized(alias)
                for alias in supplemental_component_group_policy["owner_aliases"]
            }
        )
        != len(supplemental_component_group_policy["owner_aliases"])
        or (
            supplemental_component_group_policy["mode"] == "DISABLED"
            and (
                supplemental_component_group_policy["group_source_only_role"] is not None
                or supplemental_component_group_policy["mapped_child_roles"]
                or supplemental_component_group_policy["owner_aliases"]
            )
        )
        or (
            supplemental_component_group_policy["mode"]
            == "EXACT_SUPPLEMENTAL_COMPONENT_GROUP_MATRIX"
            and (
                supplemental_component_group_policy["group_source_only_role"]
                not in source_only_aliases
                or len(supplemental_component_group_policy["mapped_child_roles"]) < 2
                or not supplemental_component_group_policy["owner_aliases"]
            )
        )
    ):
        raise _error("equity-matrix supplemental component-group policy is invalid")
    hierarchy_policy = policy.get(
        "hierarchy_policy",
        {
            "aggregate_duplicate_roles": [],
            "disclosure_group_aliases": [],
            "mapped_group_total_roles": [],
        },
    )
    if (
        type(hierarchy_policy) is not dict
        or set(hierarchy_policy)
        != {
            "aggregate_duplicate_roles",
            "disclosure_group_aliases",
            "mapped_group_total_roles",
        }
        or type(hierarchy_policy.get("aggregate_duplicate_roles")) is not list
        or len(hierarchy_policy["aggregate_duplicate_roles"])
        != len(set(hierarchy_policy["aggregate_duplicate_roles"]))
        or not set(hierarchy_policy["aggregate_duplicate_roles"]) <= set(mapped_aliases)
        or type(hierarchy_policy.get("disclosure_group_aliases")) is not list
        or any(
            type(alias) is not str or not alias.strip()
            for alias in hierarchy_policy["disclosure_group_aliases"]
        )
        or len({_normalized(alias) for alias in hierarchy_policy["disclosure_group_aliases"]})
        != len(hierarchy_policy["disclosure_group_aliases"])
        or type(hierarchy_policy.get("mapped_group_total_roles")) is not list
        or len(hierarchy_policy["mapped_group_total_roles"])
        != len(set(hierarchy_policy["mapped_group_total_roles"]))
        or not set(hierarchy_policy["mapped_group_total_roles"]) <= set(mapped_aliases)
    ):
        raise _error("equity-matrix hierarchy policy is invalid")
    mapped_normalized = {
        _normalized(alias) for aliases in mapped_aliases.values() for alias in aliases
    }
    source_only_normalized = {
        _normalized(alias) for aliases in source_only_aliases.values() for alias in aliases
    }
    if mapped_normalized & source_only_normalized:
        raise _error("mapped and source-only component aliases collide")
    units, unit_by_alias = _compile_units(policy["unit_bindings"])
    source_repair_overlay = None
    source_repair_artifact_ref = None
    if "authenticated_source_repair_artifact_ref" in evaluation_spec:
        source_repair_overlay, source_repair_artifact_ref = (
            _compile_authenticated_source_repair_artifact_v1(
                evaluation_spec["authenticated_source_repair_artifact_ref"],
                family_id=topology["family_id"],
            )
        )
    schema_fields = {
        "component_role_bindings",
        "family_id",
        "family_root_report_norm_id",
        "format_version",
        "movement_total_bindings",
        "root_mapping_policy",
    }
    if (
        type(schema_binding_spec) is not dict
        or set(schema_binding_spec) != schema_fields
        or schema_binding_spec.get("format_version") != SCHEMA_FORMAT_VERSION
        or schema_binding_spec.get("family_id") != topology["family_id"]
        or type(schema_binding_spec.get("family_root_report_norm_id")) is not int
        or schema_binding_spec["family_root_report_norm_id"] <= 0
        or schema_binding_spec.get("root_mapping_policy") not in _ROOT_MAPPING_POLICIES
    ):
        raise _error("equity-matrix schema binding spec is invalid")

    def bindings(value: Any, *, roles: set[str], label: str) -> dict[str, int]:
        if type(value) is not list or len(value) != len(roles):
            raise _error(f"equity-matrix {label} binding axis is incomplete")
        result: dict[str, int] = {}
        ids: set[int] = set()
        for raw in value:
            if (
                type(raw) is not dict
                or set(raw) != {"report_norm_id", "role"}
                or raw.get("role") not in roles
                or raw["role"] in result
                or type(raw.get("report_norm_id")) is not int
                or raw["report_norm_id"] <= 0
                or raw["report_norm_id"] in ids
            ):
                raise _error(f"equity-matrix {label} binding is invalid")
            result[raw["role"]] = raw["report_norm_id"]
            ids.add(raw["report_norm_id"])
        if set(result) != roles:
            raise _error(f"equity-matrix {label} binding roles are incomplete")
        return result

    component_bindings = bindings(
        schema_binding_spec["component_role_bindings"],
        roles=set(mapped_aliases),
        label="component",
    )
    root_mapping_policy = schema_binding_spec["root_mapping_policy"]
    if root_mapping_policy == "SOURCE_VISIBLE_MATRIX_GRAND_TOTAL_CELLS_ONLY":
        movement_bindings = bindings(
            schema_binding_spec["movement_total_bindings"],
            roles=set(_MAPPED_TOTAL_ROLES.values()),
            label="movement total",
        )
    elif schema_binding_spec["movement_total_bindings"] != []:
        raise _error("equity-matrix vector-root mode cannot bind movement totals")
    else:
        movement_bindings = {}
    all_ids = {
        schema_binding_spec["family_root_report_norm_id"],
        *component_bindings.values(),
        *movement_bindings.values(),
    }
    if len(all_ids) != 1 + len(component_bindings) + len(movement_bindings):
        raise _error("equity-matrix schema report norm IDs collide")
    query_policy = {
        "hard_negative_aliases": canonical_clone_v1(topology["hard_negative_aliases"]),
        "max_continuation_pages": policy["max_continuation_pages"],
        "minimum_mapped_component_roles": policy["minimum_mapped_component_roles"],
        "owner_aliases": canonical_clone_v1(topology["parent"]["aliases"]),
        "reset_aliases": canonical_clone_v1(topology["structural_reset_aliases"]),
    }
    if source_repair_artifact_ref is not None:
        query_policy["authenticated_source_repair_artifact_ref"] = canonical_clone_v1(
            source_repair_artifact_ref
        )
    return {
        "aliases_by_role": mapped_aliases,
        "claim_boundary": CLAIM_BOUNDARY,
        "component_row_continuation_policy": canonical_clone_v1(
            component_row_continuation_policy
        ),
        "directional_duplicate_control_aliases_by_role": canonical_clone_v1(
            directional_duplicate_aliases
        ),
        "directional_duplicate_control_mode": directional_duplicate_control_policy[
            "mode"
        ],
        "implicit_owner_policy": canonical_clone_v1(implicit_owner_policy),
        "component_report_norm_id_by_role": component_bindings,
        "engine_format_version": ENGINE_FORMAT_VERSION,
        "evaluation": canonical_clone_v1(evaluation_spec),
        "family_id": topology["family_id"],
        "family_root_report_norm_id": schema_binding_spec["family_root_report_norm_id"],
        "hierarchy_policy": canonical_clone_v1(hierarchy_policy),
        "mapped_supplemental_movement_roles": canonical_clone_v1(
            supplemental_policy["mapped_roles"]
        ),
        "movement_aliases_by_role": {**movement_aliases, **supplemental_aliases},
        "movement_decomposition_equations": canonical_clone_v1(equations),
        "movement_roles": [*_MAPPED_MOVEMENT_ROLES, *supplemental_aliases],
        "movement_total_report_norm_id_by_role": movement_bindings,
        "primary_statement_root_unit_policy": canonical_clone_v1(
            primary_statement_root_unit_policy
        ),
        "query_policy": query_policy,
        "root_mapping_policy": root_mapping_policy,
        "schema": canonical_clone_v1(schema_binding_spec),
        "signed_branch_aliases_by_role": signed_branch_aliases,
        "signed_branch_multipliers": canonical_clone_v1(signed_branch_policy["branch_multipliers"]),
        "source_only_aliases_by_role": source_only_aliases,
        "source_repair_artifact_ref": source_repair_artifact_ref,
        "source_repair_overlay": source_repair_overlay,
        "supplemental_component_group_policy": canonical_clone_v1(
            supplemental_component_group_policy
        ),
        "supplemental_rollforward_additive_roles": canonical_clone_v1(
            supplemental_policy["primary_rollforward_additive_roles"]
        ),
        "topology": topology,
        "total_aliases": canonical_clone_v1(policy["total_aliases"]),
        "unit_binding_by_alias": unit_by_alias,
        "unit_bindings": units,
    }


def _node_index(identifier: Any, prefix: str, limit: int) -> int:
    pattern = _SECTION_ID if prefix == "s" else _TABLE_ID
    if type(identifier) is not str or pattern.fullmatch(identifier) is None:
        raise _error("equity-matrix source node identity is invalid")
    index = int(identifier[1:]) - 1
    if not 0 <= index < limit:
        raise _error("equity-matrix source node identity is out of range")
    return index


def _source_table(
    page_json: Mapping[str, Any], *, section_id: str, table_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    sections = page_json.get("sections")
    if type(sections) is not list:
        raise _error("equity-matrix page has no section axis")
    section = sections[_node_index(section_id, "s", len(sections))]
    tables = section.get("tables") if type(section) is dict else None
    if type(tables) is not list:
        raise _error("equity-matrix section has no table axis")
    table = tables[_node_index(table_id, "t", len(tables))]
    if type(table) is not dict:
        raise _error("equity-matrix source table is invalid")
    return section, table


def _authenticated_source_repair_receipt_v1(
    *, compiled_specs: Mapping[str, Any], repair: Mapping[str, Any]
) -> dict[str, Any]:
    material = {
        "artifact_ref": canonical_clone_v1(compiled_specs["source_repair_artifact_ref"]),
        "base_page_json_sha256": repair["base_page_json_sha256"],
        "base_table_sha256": repair["table_ref"]["base_table_sha256"],
        "changed_cell_axis": [
            canonical_clone_v1(cell)
            for row in repair["row_repairs"]
            for cell in row["cell_repairs"]
        ],
        "effective_page_json_sha256": repair["effective_page_json_sha256"],
        "effective_table_sha256": repair["table_ref"]["effective_table_sha256"],
        "overlay_id": compiled_specs["source_repair_overlay"]["overlay_id"],
        "page_json_version_id": repair["base_page_json_version_id"],
        "repair_id": repair["repair_id"],
        "row_axis": [
            {
                "after_values_exact": canonical_clone_v1(row["after_values_exact"]),
                "before_values_exact": canonical_clone_v1(row["before_values_exact"]),
                "row_hierarchy_path_exact": canonical_clone_v1(
                    row["row_hierarchy_path_exact"]
                ),
                "row_id": row["row_id"],
                "row_kind": row["row_kind"],
                "row_label_exact": row["row_label_exact"],
            }
            for row in repair["row_repairs"]
        ],
        "rule": (
            "EXACT_AUTHENTICATED_PDF_RENDER_SELECTED_JSON_TABLE_ROW_CELL_UNIT_"
            "DIRECT_LITERAL_TRANSCRIPTION_ONLY_EQUATION_VETO_NO_BACKSOLVE"
        ),
        "source_binding": canonical_clone_v1(repair["source_binding"]),
        "status": "AUTHENTICATED_PDF_VISIBLE_TABLE_SOURCE_AXIS_TRANSCRIBED",
        "table_ref": {
            "section_id": repair["table_ref"]["section_id"],
            "table_id": repair["table_ref"]["table_id"],
        },
        "table_unit_repair": canonical_clone_v1(repair["table_unit_repair"]),
        "visual_evidence": canonical_clone_v1(repair["visual_evidence"]),
    }
    return {
        **material,
        "receipt_id": "gjeqmsrv1:receipt:" + canonical_json_sha256_v1(material),
    }


def _apply_authenticated_source_repair_artifact_v1(
    *,
    page_json_by_version: Mapping[str, Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    regions: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Apply a registered repair to page clones after every binding replays."""

    overlay = compiled_specs.get("source_repair_overlay")
    artifact_ref = compiled_specs.get("source_repair_artifact_ref")
    if overlay is None and artifact_ref is None:
        return (
            {key: canonical_clone_v1(value) for key, value in page_json_by_version.items()},
            [],
        )
    if type(overlay) is not dict or type(artifact_ref) is not dict:
        raise _error("equity-matrix compiled source-repair overlay is invalid")
    region_by_version: dict[str, list[Mapping[str, Any]]] = {}
    for region in regions:
        version_id = region.get("page_json_version_id")
        if type(version_id) is not str:
            raise _error("equity-matrix source-repair region identity is invalid")
        region_by_version.setdefault(version_id, []).append(region)
    effective_pages = {
        key: canonical_clone_v1(value) for key, value in page_json_by_version.items()
    }
    receipts = []
    for repair in overlay["repairs"]:
        version_id = repair["base_page_json_version_id"]
        matching_regions = region_by_version.get(version_id, [])
        if not matching_regions:
            continue
        source = repair["source_binding"]
        table_ref = repair["table_ref"]
        if any(
            region.get("document_id") != source["document_id"]
            or region.get("source_logical_name") != source["source_logical_name"]
            or region.get("source_sha256") != source["source_sha256"]
            or region.get("physical_page") != source["physical_page"]
            for region in matching_regions
        ):
            raise _error("equity-matrix source-repair source binding drifted")
        if not any(
            region.get("section_id") == table_ref["section_id"]
            and region.get("table_id") == table_ref["table_id"]
            for region in matching_regions
        ):
            raise _error("equity-matrix source-repair target table is outside selected regions")
        base_page = page_json_by_version.get(version_id)
        if (
            type(base_page) is not dict
            or canonical_json_sha256_v1(base_page) != repair["base_page_json_sha256"]
        ):
            raise _error("equity-matrix source-repair base page drifted")
        _section, base_table = _source_table(
            base_page,
            section_id=table_ref["section_id"],
            table_id=table_ref["table_id"],
        )
        if (
            canonical_json_sha256_v1(base_table) != table_ref["base_table_sha256"]
            or not same_typed_json_v1(base_table.get("columns"), repair["column_axis_exact"])
            or (
                repair["table_unit_repair"] is not None
                and not same_typed_json_v1(
                    base_table.get("unit_exact"),
                    repair["table_unit_repair"]["before_exact"],
                )
            )
        ):
            raise _error("equity-matrix source-repair base table drifted")
        effective_page = canonical_clone_v1(base_page)
        _effective_section, effective_table = _source_table(
            effective_page,
            section_id=table_ref["section_id"],
            table_id=table_ref["table_id"],
        )
        rows = effective_table.get("rows")
        if type(rows) is not list:
            raise _error("equity-matrix source-repair row axis is invalid")
        for repair_row in repair["row_repairs"]:
            row_index = int(repair_row["row_id"][1:]) - 1
            row = rows[row_index] if 0 <= row_index < len(rows) else None
            if (
                type(row) is not dict
                or row.get("label_exact") != repair_row["row_label_exact"]
                or row.get("row_kind") != repair_row["row_kind"]
                or not same_typed_json_v1(
                    row.get("hierarchy_path_exact"),
                    repair_row["row_hierarchy_path_exact"],
                )
                or not same_typed_json_v1(
                    row.get("values_exact"), repair_row["before_values_exact"]
                )
            ):
                raise _error("equity-matrix source-repair row before-image drifted")
            row["values_exact"] = canonical_clone_v1(repair_row["after_values_exact"])
        if repair["table_unit_repair"] is not None:
            effective_table["unit_exact"] = repair["table_unit_repair"]["after_exact"]
        if (
            canonical_json_sha256_v1(effective_table)
            != table_ref["effective_table_sha256"]
            or canonical_json_sha256_v1(effective_page)
            != repair["effective_page_json_sha256"]
        ):
            raise _error("equity-matrix source-repair effective image drifted")
        effective_pages[version_id] = effective_page
        receipts.append(
            _authenticated_source_repair_receipt_v1(
                compiled_specs=compiled_specs,
                repair=repair,
            )
        )
    receipts.sort(key=lambda item: item["repair_id"])
    return effective_pages, receipts


def _header_members(column: Any) -> list[str]:
    members = column.get("header_path_exact") if type(column) is dict else None
    return (
        [item for item in members if type(item) is str and item.strip()]
        if type(members) is list
        else []
    )


def _role_matches(members: Sequence[Any], aliases_by_role: Mapping[str, list[str]]) -> list[str]:
    # Hierarchy paths are broad-to-specific. Resolve the deepest declared
    # member first, then the longest alias within that member. This lets a
    # child retain its own role under a mapped subtotal without double-matching
    # the parent catch-all.
    for member in reversed(members):
        matches = [
            (role, alias)
            for role, aliases in aliases_by_role.items()
            for alias in aliases
            if _matches(member, alias)
        ]
        if matches:
            longest = max(len(_normalized(alias)) for _role, alias in matches)
            return sorted({role for role, alias in matches if len(_normalized(alias)) == longest})
    return []


def _unit_occurrences(surface: Any, *, compiled_specs: Mapping[str, Any]) -> list[dict[str, Any]]:
    folded = _normalized(surface)
    occurrences = [
        (match.start(), match.end(), alias)
        for alias in compiled_specs["unit_binding_by_alias"]
        for match in re.finditer(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", folded)
    ]
    # ``Triệu đồng Việt Nam`` is one compound magnitude/currency
    # declaration.  Its two registered aliases (``triệu đồng`` and
    # ``đồng Việt Nam``) overlap on the word ``đồng``; the latter
    # must not be interpreted as a second, unit-magnitude VND declaration.
    # Keep genuinely separate declarations such as ``Triệu đồng; VND``
    # conflicting by requiring the source spans to overlap.
    def shadowed_currency_tail(item: tuple[int, int, str]) -> bool:
        start, end, alias = item
        binding = compiled_specs["unit_binding_by_alias"][alias]
        if binding["magnitude_power10"] != 0:
            return False
        return any(
            other_start < end
            and start < other_end
            and compiled_specs["unit_binding_by_alias"][other_alias]["magnitude_power10"] > 0
            for other_start, other_end, other_alias in occurrences
        )

    maximal = sorted(
        [
            item
            for item in occurrences
            if not shadowed_currency_tail(item)
            if not any(
                other[0] <= item[0]
                and item[1] <= other[1]
                and other[1] - other[0] > item[1] - item[0]
                for other in occurrences
            )
        ],
        key=lambda item: (item[0], item[1], item[2]),
    )
    return [
        {
            "accepted": compiled_specs["unit_binding_by_alias"][alias]["accepted"],
            "canonical_unit": compiled_specs["unit_binding_by_alias"][alias]["canonical_unit"],
            "matched_alias": alias,
            "magnitude_power10": compiled_specs["unit_binding_by_alias"][alias][
                "magnitude_power10"
            ],
        }
        for _start, _end, alias in maximal
    ]


def _semantic_component_members(
    members: Sequence[str], *, compiled_specs: Mapping[str, Any]
) -> list[str]:
    result = []
    unit_aliases = sorted(compiled_specs["unit_binding_by_alias"], key=len, reverse=True)
    component_aliases = {
        _normalized(alias)
        for aliases_by_role in (
            compiled_specs["aliases_by_role"],
            compiled_specs["source_only_aliases_by_role"],
        )
        for aliases in aliases_by_role.values()
        for alias in aliases
    }
    semantic_axis_aliases = component_aliases | {
        _normalized(alias) for alias in compiled_specs["total_aliases"]
    }
    inferred_parent_aliases = {
        _normalized(alias)
        for role in compiled_specs["hierarchy_policy"]["mapped_group_total_roles"]
        for alias in compiled_specs["aliases_by_role"][role]
    } | {
        _normalized(alias)
        for alias in compiled_specs["hierarchy_policy"]["disclosure_group_aliases"]
    }
    for member in members:
        folded = _normalized(member)
        for alias in unit_aliases:
            folded = re.sub(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", " ", folded)
        folded = " ".join(folded.split())
        if folded:
            # Some statements print the balance-sheet disclosure reference as
            # a final integer on each equity-component header (for example
            # ``Financial reserve / 7`` and ``Total / 13``).  Remove only one
            # trailing integer when the remaining full surface is an exact
            # declared component or total alias; the literal header remains
            # preserved in the component-axis receipt.
            without_reference = re.sub(r"\s+[1-9][0-9]*$", "", folded).strip()
            if without_reference in semantic_axis_aliases:
                folded = without_reference
            # Some page transcriptions flatten ``parent - child`` into one
            # hierarchy member.  Recover only an explicitly declared group
            # parent followed by an exact declared child alias.  An exact
            # whole-surface alias always wins, so ordinary long labels such as
            # ``Các loại thuế khác, phí và lệ phí`` are never split merely
            # because they contain shorter aliases.
            inferred = None
            if folded not in component_aliases:
                candidates = []
                for parent in inferred_parent_aliases:
                    prefix = f"{parent} "
                    if folded.startswith(prefix):
                        child = folded[len(prefix) :].strip()
                        if child in component_aliases:
                            candidates.append((len(parent), parent, child))
                if candidates:
                    _length, parent, child = max(candidates)
                    inferred = [parent, child]
            result.extend(inferred or [folded])
    return result


def _promote_inferred_mapped_group_totals_v1(
    component_axis: list[dict[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> None:
    """Promote a source-visible group row when its following children prove hierarchy.

    Gemini's optional ``row_kind`` is not authority.  Promotion is restricted
    to roles declared by ``mapped_group_total_roles`` and requires a later,
    strictly deeper semantic path under the exact group prefix.
    """

    allowed = set(compiled_specs["hierarchy_policy"]["mapped_group_total_roles"])
    for index, item in enumerate(component_axis):
        if (
            item["kind"] not in {"MAPPED_COMPONENT", "MAPPED_COMPONENT_GROUP_TOTAL"}
            or item["role"] not in allowed
        ):
            continue
        prefix = item["semantic_path"]
        children = [
            child
            for child in component_axis[index + 1 :]
            if _starts_with(child["semantic_path"], prefix)
        ]
        if not children:
            continue
        same_role_children = [
            child
            for child in children
            if child["kind"] == "MAPPED_COMPONENT" and child["role"] == item["role"]
        ]
        # A source subtotal and one of its strict children can legitimately
        # share a broad declared alias (for example ``other taxes`` and a
        # concrete tax that maps to that residual schema leaf).  Mapping both
        # would double count the child.  The visible parent remains an exact
        # equation frontier while the more specific child carries the schema
        # role.  Without a same-role child the declared parent itself remains
        # the mapped role, preserving ordinary group-total disclosures.
        if same_role_children:
            item["kind"] = "GROUP_TOTAL"
            item["role"] = None
            rule = "DECLARED_MAPPED_GROUP_DEMOTED_BY_STRICT_SAME_ROLE_CHILD"
        else:
            item["kind"] = "MAPPED_COMPONENT_GROUP_TOTAL"
            rule = "DECLARED_MAPPED_GROUP_PROMOTED_BY_FOLLOWING_DEEPER_SEMANTIC_PATHS"
        item["group_prefix"] = canonical_clone_v1(prefix)
        item["hierarchy_resolution"] = {
            "child_axis_ids": [child["axis_id"] for child in children],
            "rule": rule,
        }


def _recover_flat_group_total_children_v1(component_axis: list[dict[str, Any]]) -> None:
    """Recover contiguous children of one declared flat group subtotal.

    A source can flatten ``Các quỹ / Tổng cộng các quỹ`` into a
    single column header while printing the fund columns immediately before
    it.  The group name itself remains the authority: recovery requires at
    least two contiguous preceding leaves that contain a substantive token
    from that exact declared group prefix.  It therefore cannot absorb an
    intervening non-group component or invent a group from arithmetic.
    """

    generic_group_tokens = {"cac", "nhom", "loai"}
    leaf_kinds = {"MAPPED_COMPONENT", "SOURCE_ONLY_COMPONENT"}
    for total_index, total in enumerate(component_axis):
        prefix = total["group_prefix"]
        if (
            total["kind"] != "GROUP_TOTAL"
            or not prefix
            or len(total["semantic_path"]) != 1
        ):
            continue
        keywords = {
            token
            for member in prefix
            for token in member.split()
            if token not in generic_group_tokens
        }
        if not keywords:
            continue
        children = []
        for child in reversed(component_axis[:total_index]):
            if child["kind"] not in leaf_kinds:
                break
            child_tokens = {
                token for member in child["semantic_path"] for token in member.split()
            }
            if not keywords & child_tokens:
                break
            children.append(child)
        children.reverse()
        if len(children) < 2:
            continue
        for child in children:
            child["semantic_path"] = [*canonical_clone_v1(prefix), *child["semantic_path"]]
            child["group_prefix"] = canonical_clone_v1(prefix)
            child["hierarchy_resolution"] = {
                "group_total_axis_id": total["axis_id"],
                "rule": "CONTIGUOUS_PRECEDING_DECLARED_GROUP_TOKEN_CHILD",
            }
        total["hierarchy_resolution"] = {
            "child_axis_ids": [child["axis_id"] for child in children],
            "rule": "FLAT_DECLARED_GROUP_TOTAL_OWNS_CONTIGUOUS_TOKEN_MATCHING_CHILDREN",
        }


def _promote_full_scope_group_total_v1(component_axis: list[dict[str, Any]]) -> None:
    """Recognize a last-row total whose hierarchy prefix owns the full matrix."""

    if not component_axis:
        return
    total = component_axis[-1]
    prefix = total["group_prefix"]
    prior = [
        item
        for item in component_axis[:-1]
        if item["kind"] not in {"DISCLOSURE_GROUP_HEADER", "UNCLASSIFIED_COMPONENT_AXIS"}
    ]
    if (
        total["kind"] != "GROUP_TOTAL"
        or not prefix
        or not prior
        or not all(_starts_with(item["semantic_path"], prefix) for item in prior)
    ):
        return
    total["kind"] = "GRAND_TOTAL"
    total["group_prefix"] = []
    total["hierarchy_resolution"] = {
        "owned_axis_ids": [item["axis_id"] for item in prior],
        "source_group_prefix": canonical_clone_v1(prefix),
        "rule": "LAST_GROUP_TOTAL_PREFIX_OWNS_COMPLETE_PRECEDING_COMPONENT_POPULATION",
    }


def _component_record(
    *,
    members: Sequence[str],
    row_kind: Any,
    axis_id: str,
    axis_ordinal: int,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    semantic_members = _semantic_component_members(members, compiled_specs=compiled_specs)
    combined_aliases = {
        **{
            f"MAPPED:{role}": aliases for role, aliases in compiled_specs["aliases_by_role"].items()
        },
        **{
            f"SOURCE_ONLY:{role}": aliases
            for role, aliases in compiled_specs["source_only_aliases_by_role"].items()
        },
    }
    combined_matches = _role_matches(semantic_members, combined_aliases)
    mapped = [
        role.removeprefix("MAPPED:") for role in combined_matches if role.startswith("MAPPED:")
    ]
    source_only = [
        role.removeprefix("SOURCE_ONLY:")
        for role in combined_matches
        if role.startswith("SOURCE_ONLY:")
    ]
    branch_matches = sorted(
        {
            role
            for member in semantic_members
            for role, aliases in compiled_specs["signed_branch_aliases_by_role"].items()
            if any(_matches(member, alias) for alias in aliases)
        }
    )
    branch_role = branch_matches[0] if len(branch_matches) == 1 else None
    disclosure_members = [
        member
        for member in semantic_members
        if any(
            _matches(member, alias)
            for alias in compiled_specs["hierarchy_policy"]["disclosure_group_aliases"]
        )
    ]
    total_members = [
        member
        for member in semantic_members
        if any(_matches(member, alias) for alias in compiled_specs["total_aliases"])
    ]
    # A hierarchical subtotal can repeat its exact group name after a generic
    # total prefix (``Quỹ của TCTD / Tổng cộng Quỹ của TCTD``).
    # Recognize that source grammar even though the whole leaf is not itself
    # an exact generic-total alias.  Only explicitly declared disclosure
    # groups are eligible, so an arbitrary ``Tổng ...`` label cannot create
    # hierarchy.
    declared_groups = {
        _normalized(alias)
        for alias in compiled_specs["hierarchy_policy"]["disclosure_group_aliases"]
    } | {
        _normalized(alias)
        for aliases in compiled_specs["source_only_aliases_by_role"].values()
        for alias in aliases
    }
    declared_group_total_prefix: list[str] = []
    for member in semantic_members:
        for total_prefix in ("tong cong ", "tong ", "cong "):
            suffix = member.removeprefix(total_prefix).strip()
            if member.startswith(total_prefix) and suffix in declared_groups:
                declared_group_total_prefix = [suffix]
                total_members = [member]
                break
        if declared_group_total_prefix:
            break
    reasons = []
    group_prefix: list[str] = []
    if declared_group_total_prefix:
        # The repeated group label describes the subtotal, not a second
        # additive source-only leaf with the same name.
        mapped = []
        source_only = []
    if len(mapped) + len(source_only) > 1:
        reasons.append("COMPONENT_AXIS_MEMBER_MATCHES_MULTIPLE_DECLARED_ROLES")
    if len(branch_matches) > 1:
        reasons.append("COMPONENT_AXIS_MEMBER_MATCHES_MULTIPLE_SIGNED_BRANCHES")
    if total_members and (mapped or source_only):
        reasons.append("COMPONENT_AXIS_TOTAL_AND_LEAF_ROLES_CONFLICT")
    kind = "UNCLASSIFIED_COMPONENT_AXIS"
    role = None
    if branch_role is not None and row_kind == "GROUP" and not mapped and not source_only:
        kind = "SIGNED_BRANCH_HEADER"
        group_prefix = [_normalized(member) for member in semantic_members]
    elif row_kind == "GROUP" and len(disclosure_members) == 1:
        kind = "DISCLOSURE_GROUP_HEADER"
        group_prefix = [_normalized(member) for member in semantic_members]
    elif len(mapped) == 1 and not source_only and not total_members:
        role = mapped[0]
        if (
            row_kind == "GROUP"
            and role in compiled_specs["hierarchy_policy"]["mapped_group_total_roles"]
        ):
            kind = "MAPPED_COMPONENT_GROUP_TOTAL"
            group_prefix = [_normalized(member) for member in semantic_members]
        else:
            kind = "MAPPED_COMPONENT"
    elif len(source_only) == 1 and not mapped and not total_members:
        role = source_only[0]
        kind = "DISCLOSURE_COMPONENT" if disclosure_members else "SOURCE_ONLY_COMPONENT"
    elif branch_role is not None and row_kind in {"SUBTOTAL", "TOTAL"}:
        kind = "SIGNED_BRANCH_TOTAL"
        group_prefix = [_normalized(member) for member in semantic_members]
    elif row_kind in {"SUBTOTAL", "TOTAL"} or len(total_members) == 1:
        prefix = (
            semantic_members[:-1] if total_members and semantic_members[-1] in total_members else []
        )
        if declared_group_total_prefix:
            prefix = declared_group_total_prefix
        if not prefix and total_members:
            # Some matrices print a group subtotal as one flat surface
            # (``Tổng cộng các quỹ``) rather than the equivalent hierarchy
            # path ``Các quỹ / Tổng cộng các quỹ``.  Recover only a declared
            # disclosure-group suffix after an exact generic-total prefix.
            # The original surface stays in ``members_exact`` and an
            # undeclared suffix can never create an inferred group.
            for member in total_members:
                folded_total = _normalized(member)
                for total_prefix in ("tong cong ", "tong ", "cong "):
                    if (
                        folded_total.startswith(total_prefix)
                        and folded_total.removeprefix(total_prefix).strip()
                        in declared_groups
                    ):
                        prefix = [folded_total.removeprefix(total_prefix).strip()]
                        break
                if prefix:
                    break
        if (
            row_kind in {"SUBTOTAL", "TOTAL"}
            and semantic_members
            and not total_members
            and not prefix
        ):
            prefix = semantic_members
        group_prefix = [_normalized(member) for member in prefix]
        kind = "GROUP_TOTAL" if prefix else "GRAND_TOTAL"
    result = {
        "axis_id": axis_id,
        "axis_ordinal": axis_ordinal,
        "kind": kind,
        "group_prefix": group_prefix,
        "members_exact": canonical_clone_v1(list(members)),
        "reasons": reasons,
        "role": role,
        "semantic_path": [_normalized(member) for member in semantic_members],
    }
    if branch_role is not None:
        result["signed_branch_role"] = branch_role
        result["signed_branch_multiplier"] = compiled_specs["signed_branch_multipliers"][
            branch_role
        ]
    return result


def _valuation_label_matches_v1(value: Any, aliases: Sequence[str]) -> list[str]:
    folded = _normalized(value)
    tokens = folded.split()
    ordinal_tokens = {
        "i",
        "ii",
        "iii",
        "iv",
        "v",
        "vi",
        "vii",
        "viii",
        "ix",
        "x",
    }
    while len(tokens) > 1 and (tokens[0].isdigit() or tokens[0] in ordinal_tokens):
        tokens.pop(0)
    folded = " ".join(tokens)
    for suffix in (" gop", " thuan"):
        if folded.endswith(suffix):
            folded = folded[: -len(suffix)].strip()
    return sorted(
        {
            alias
            for alias in aliases
            if (
                folded == _normalized(alias)
                or folded.startswith(_normalized(alias) + " xem thuyet minh ")
                or (
                    len(folded.split()) >= 6
                    and _normalized(alias).startswith(folded + " ")
                    and len(_normalized(alias).split()) == len(folded.split()) + 1
                )
            )
        }
    )


def _valuation_role_v1(
    value: Any, *, aliases_by_role: Mapping[str, Sequence[str]]
) -> tuple[str | None, list[str]]:
    matches = [
        (role, alias)
        for role, aliases in aliases_by_role.items()
        for alias in _valuation_label_matches_v1(value, aliases)
    ]
    if not matches:
        return None, []
    maximum = max(len(_normalized(alias)) for _role, alias in matches)
    roles = sorted({role for role, alias in matches if len(_normalized(alias)) == maximum})
    return (roles[0] if len(roles) == 1 else None), roles


def _valuation_header_has_v1(members: Sequence[str], aliases: Sequence[str]) -> bool:
    folded = " ".join(_normalized(member) for member in members if _normalized(member))
    return any(
        re.search(rf"(?<![a-z0-9]){re.escape(_normalized(alias))}(?![a-z0-9])", folded)
        for alias in aliases
    )


def _valuation_active_source_cell_v1(value: Any) -> bool:
    return value is not None and (type(value) is not str or bool(value.strip()))


def _classify_valuation_matrix_table_v1(
    table: Any, *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    rows = table.get("rows") if type(table) is dict else None
    columns = table.get("columns") if type(table) is dict else None
    if type(rows) is not list or type(columns) is not list or not rows or not columns:
        raise _error("valuation-matrix table axes are invalid")
    if any(
        type(row) is not dict
        or type(row.get("values_exact")) is not list
        or len(row["values_exact"]) != len(columns)
        or type(row.get("hierarchy_path_exact")) is not list
        for row in rows
    ) or any(type(column) is not dict for column in columns):
        raise _error("valuation-matrix row or column axis is invalid")
    markers = compiled_specs["valuation_marker_aliases"]
    column_axis = []
    for ordinal, column in enumerate(columns, start=1):
        members = _header_members(column)
        book = _valuation_header_has_v1(members, markers["book_value_header_aliases"])
        book_total = _valuation_header_has_v1(members, markers["book_total_header_aliases"])
        fair = _valuation_header_has_v1(members, markers["fair_value_header_aliases"])
        roles = [
            role
            for role, present in (
                ("BOOK_CLASSIFICATION", book and not book_total),
                ("BOOK_TOTAL", book_total),
                ("FAIR_VALUE", fair and not book and not book_total),
            )
            if present
        ]
        column_axis.append(
            {
                "column_id": f"c{ordinal}",
                "header_path_exact": canonical_clone_v1(members),
                "role_source": "EXPLICIT_HEADER_ALIAS" if roles else None,
                "roles": roles,
                "value_kind": column.get("value_kind"),
            }
        )
    explicit_book_totals = [item for item in column_axis if item["roles"] == ["BOOK_TOTAL"]]
    explicit_fair_values = [item for item in column_axis if item["roles"] == ["FAIR_VALUE"]]
    if len(explicit_book_totals) == len(explicit_fair_values) == 1:
        total_ordinal = int(explicit_book_totals[0]["column_id"][1:])
        fair_ordinal = int(explicit_fair_values[0]["column_id"][1:])
        if fair_ordinal == total_ordinal + 1 == len(column_axis):
            for item in column_axis[: total_ordinal - 1]:
                if not item["roles"] and item["header_path_exact"]:
                    item["roles"] = ["BOOK_CLASSIFICATION"]
                    item["role_source"] = "LEFT_SIBLING_OF_EXACT_BOOK_TOTAL_AND_FAIR_VALUE_COLUMNS"
    reasons = []
    book_total_columns = [item for item in column_axis if item["roles"] == ["BOOK_TOTAL"]]
    fair_columns = [item for item in column_axis if item["roles"] == ["FAIR_VALUE"]]
    classification_columns = [
        item for item in column_axis if item["roles"] == ["BOOK_CLASSIFICATION"]
    ]
    if len(book_total_columns) != 1:
        reasons.append("EXACTLY_ONE_BOOK_TOTAL_COLUMN_REQUIRED")
    if len(fair_columns) != 1:
        reasons.append("EXACTLY_ONE_FAIR_VALUE_COLUMN_REQUIRED")
    if len(classification_columns) < 2:
        reasons.append("BOOK_CLASSIFICATION_COLUMN_AXIS_INCOMPLETE")
    if any(not item["roles"] for item in column_axis):
        reasons.append("UNCLASSIFIED_VALUATION_COLUMN_PRESENT")
    if any(len(item["roles"]) != 1 for item in column_axis):
        reasons.append("VALUATION_COLUMN_ROLE_CONFLICT")

    total_rows = []
    for ordinal, row in enumerate(rows, start=1):
        label = row.get("label_exact")
        explicit_total = _valuation_label_matches_v1(
            label,
            [*markers["asset_total_aliases"], *markers["liability_total_aliases"]],
        )
        generic_unlabeled_total = row.get("row_kind") in {"SUBTOTAL", "TOTAL"} and _normalized(
            label
        ) in {"", "tong", "tong cong"}
        if explicit_total or generic_unlabeled_total:
            total_rows.append(ordinal)
    if len(total_rows) != 2:
        reasons.append("EXACTLY_TWO_ASSET_LIABILITY_TOTAL_ROWS_REQUIRED")
    first_total = total_rows[0] if len(total_rows) == 2 else None
    second_total = total_rows[1] if len(total_rows) == 2 else None
    row_axis = []
    mapped_roles = []
    for ordinal, row in enumerate(rows, start=1):
        label = row.get("label_exact")
        active = any(_valuation_active_source_cell_v1(value) for value in row["values_exact"])
        if ordinal in total_rows:
            branch = "ASSET" if ordinal == first_total else "LIABILITY"
            kind = "BRANCH_TOTAL"
            role = "BOOK_TOTAL_ASSETS" if branch == "ASSET" else "BOOK_TOTAL_LIABILITIES"
            role_matches = [role]
        elif first_total is not None and ordinal < first_total:
            branch = "ASSET"
            role, role_matches = _valuation_role_v1(
                label, aliases_by_role=compiled_specs["asset_role_aliases_by_role"]
            )
            kind = "MAPPED_COMPONENT" if role is not None else "STRUCTURAL_GROUP"
        elif (
            first_total is not None
            and second_total is not None
            and first_total < ordinal < second_total
        ):
            branch = "LIABILITY"
            role, role_matches = _valuation_role_v1(
                label, aliases_by_role=compiled_specs["liability_role_aliases_by_role"]
            )
            kind = "MAPPED_COMPONENT" if role is not None else "STRUCTURAL_GROUP"
        else:
            branch = None
            role = None
            role_matches = []
            kind = "UNCONSUMED_ROW"
        if kind == "STRUCTURAL_GROUP" and active:
            kind = "UNCLASSIFIED_ACTIVE_ROW"
            reasons.append("UNCLASSIFIED_ACTIVE_VALUATION_ROW_PRESENT")
        if len(role_matches) > 1:
            reasons.append("VALUATION_ROW_MATCHES_MULTIPLE_ROLES")
        if kind == "UNCONSUMED_ROW" and active:
            reasons.append("ACTIVE_ROW_OUTSIDE_ASSET_LIABILITY_BRANCHES")
        if kind == "MAPPED_COMPONENT":
            mapped_roles.append(role)
        row_axis.append(
            {
                "branch": branch,
                "kind": kind,
                "label_exact": label,
                "role": role,
                "role_matches": role_matches,
                "row_id": f"r{ordinal}",
                "row_kind": row.get("row_kind"),
                "source_order": ordinal,
            }
        )
    duplicate_roles = {role for role in mapped_roles if mapped_roles.count(role) > 1}
    if duplicate_roles - set(
        compiled_specs["evaluation"]["matrix_policy"]["aggregate_duplicate_roles"]
    ):
        reasons.append("DUPLICATE_VALUATION_COMPONENT_ROLE")
    if len(set(mapped_roles)) < compiled_specs["query_policy"]["minimum_mapped_component_roles"]:
        reasons.append("VALUATION_COMPONENT_ROLE_POPULATION_INCOMPLETE")
    status = "MATRIX_FRAGMENT" if not reasons else "NOT_MATRIX"
    return {
        "column_axis": column_axis,
        "column_declared_component_roles": sorted(
            {role for item in column_axis for role in item["roles"]}
        ),
        "component_axis": row_axis,
        "component_axis_sha256": canonical_json_sha256_v1(row_axis),
        "mapped_component_roles": sorted(set(mapped_roles)),
        "matrix_kind": "VALUATION_CLASSIFICATION",
        "orientation": "COMPONENT_ROWS" if status == "MATRIX_FRAGMENT" else None,
        "reasons": sorted(set(reasons)),
        "row_declared_component_roles": sorted(set(mapped_roles)),
        "status": status,
    }


def classify_gemini_json_equity_matrix_table_v1(
    table: Any, *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Classify one matrix fragment from its two declared axes only."""

    if compiled_specs.get("exchange_rate_mode") is True:
        from bctc_ai.evaluation.gemini_json_categorical_period_matrix_v1 import (
            classify_gemini_json_categorical_period_matrix_table_v1,
        )

        return classify_gemini_json_categorical_period_matrix_table_v1(
            table, compiled_specs=compiled_specs
        )
    if compiled_specs.get("currency_risk_mode") is True:
        from bctc_ai.evaluation.gemini_json_currency_risk_matrix_v1 import (
            classify_gemini_json_currency_risk_matrix_table_v1,
        )

        return classify_gemini_json_currency_risk_matrix_table_v1(
            table, compiled_specs=compiled_specs
        )
    if compiled_specs.get("valuation_mode") is True:
        return _classify_valuation_matrix_table_v1(table, compiled_specs=compiled_specs)

    rows = table.get("rows") if type(table) is dict else None
    columns = table.get("columns") if type(table) is dict else None
    if type(rows) is not list or type(columns) is not list or not rows or not columns:
        raise _error("equity-matrix table axes are invalid")
    if any(
        type(row) is not dict
        or type(row.get("values_exact")) is not list
        or len(row["values_exact"]) != len(columns)
        or type(row.get("hierarchy_path_exact")) is not list
        for row in rows
    ):
        raise _error("equity-matrix row cell vectors are invalid")
    if any(type(column) is not dict for column in columns):
        raise _error("equity-matrix column axis is invalid")
    row_components = [
        _component_record(
            members=[
                member
                for member in row.get("hierarchy_path_exact", [])
                if type(member) is str and member.strip()
            ],
            row_kind=row.get("row_kind"),
            axis_id=f"r{ordinal}",
            axis_ordinal=ordinal,
            compiled_specs=compiled_specs,
        )
        for ordinal, row in enumerate(rows, start=1)
    ]
    _promote_inferred_mapped_group_totals_v1(row_components, compiled_specs=compiled_specs)
    _recover_flat_group_total_children_v1(row_components)
    _promote_full_scope_group_total_v1(row_components)
    column_components = [
        _component_record(
            members=_header_members(column),
            row_kind=None,
            axis_id=f"c{ordinal}",
            axis_ordinal=ordinal,
            compiled_specs=compiled_specs,
        )
        for ordinal, column in enumerate(columns, start=1)
    ]
    _recover_flat_group_total_children_v1(column_components)
    mapped_kinds = {"MAPPED_COMPONENT", "MAPPED_COMPONENT_GROUP_TOTAL"}
    row_mapped = {item["role"] for item in row_components if item["kind"] in mapped_kinds}
    column_mapped = {item["role"] for item in column_components if item["kind"] in mapped_kinds}
    minimum = compiled_specs["query_policy"]["minimum_mapped_component_roles"]
    orientations = []
    accepted_orientations = compiled_specs["evaluation"]["matrix_policy"]["accepted_orientations"]
    if (
        "COMPONENT_ROWS" in accepted_orientations
        and len(row_mapped) >= minimum
        and len(columns) >= 4
    ):
        orientations.append("COMPONENT_ROWS")
    if (
        "COMPONENT_COLUMNS" in accepted_orientations
        and len(column_mapped) >= minimum
        and sum(column.get("value_kind") == "MONEY" for column in columns) >= 4
    ):
        orientations.append("COMPONENT_COLUMNS")
    reasons = sorted(
        {reason for item in [*row_components, *column_components] for reason in item["reasons"]}
    )
    if len(orientations) > 1:
        # Movement labels can legitimately reuse component vocabulary (for
        # example ``Lợi nhuận sau thuế`` or ``Chênh lệch tỷ giá``).  They are
        # not the component axis when the opposite axis carries a strictly
        # more complete declared component population.  Keep a tie
        # fail-closed: it is genuine orientation ambiguity rather than a
        # reason to prefer rows or columns by layout convention.
        row_score = len(row_mapped)
        column_score = len(column_mapped)
        if row_score > column_score:
            orientations = ["COMPONENT_ROWS"]
        elif column_score > row_score:
            orientations = ["COMPONENT_COLUMNS"]
        else:
            reasons.append("BOTH_MATRIX_ORIENTATIONS_MATCH")
    orientation = orientations[0] if len(orientations) == 1 else None
    component_axis = (
        row_components
        if orientation == "COMPONENT_ROWS"
        else column_components
        if orientation == "COMPONENT_COLUMNS"
        else []
    )
    roles = [item["role"] for item in component_axis if item["kind"] in mapped_kinds]
    duplicate_roles = {role for role in roles if roles.count(role) > 1}
    signed_branch_roles = {
        item.get("signed_branch_role")
        for item in component_axis
        if item.get("signed_branch_role") is not None
    }
    signed_branch_mode = bool(signed_branch_roles) and orientation == "COMPONENT_ROWS"
    signed_branch_complete = False
    if signed_branch_mode:
        signed_branch_complete = all(
            sum(
                item["kind"] == "SIGNED_BRANCH_HEADER"
                and item.get("signed_branch_role") == branch_role
                for item in component_axis
            )
            == 1
            and sum(
                item["kind"] == "SIGNED_BRANCH_TOTAL"
                and item.get("signed_branch_role") == branch_role
                for item in component_axis
            )
            == 1
            and len(
                {
                    item["role"]
                    for item in component_axis
                    if item["kind"] in mapped_kinds
                    and item.get("signed_branch_role") == branch_role
                }
            )
            >= minimum
            for branch_role in sorted(signed_branch_roles)
        )
        if not signed_branch_complete:
            reasons.append("SIGNED_BRANCH_COMPONENT_POPULATION_INCOMPLETE")
        for branch_role in sorted(signed_branch_roles):
            branch_mapped_roles = [
                item["role"]
                for item in component_axis
                if item["kind"] in mapped_kinds and item.get("signed_branch_role") == branch_role
            ]
            if len(branch_mapped_roles) != len(set(branch_mapped_roles)):
                reasons.append("DUPLICATE_MAPPED_COMPONENT_ROLE_WITHIN_SIGNED_BRANCH")
    if not signed_branch_mode and duplicate_roles - set(
        compiled_specs["hierarchy_policy"]["aggregate_duplicate_roles"]
    ):
        reasons.append("DUPLICATE_MAPPED_COMPONENT_ROLE")
    if (
        orientation is not None
        and not signed_branch_mode
        and sum(item["kind"] == "GRAND_TOTAL" for item in component_axis) != 1
    ):
        reasons.append("EXACTLY_ONE_COMPONENT_GRAND_TOTAL_REQUIRED")
    if orientation is not None and any(
        item["kind"] == "UNCLASSIFIED_COMPONENT_AXIS" for item in component_axis
    ):
        reasons.append("UNCLASSIFIED_COMPONENT_AXIS_PRESENT")
    result = {
        "column_declared_component_roles": sorted(column_mapped),
        "component_axis": component_axis,
        "component_axis_sha256": canonical_json_sha256_v1(component_axis),
        "mapped_component_roles": sorted(set(roles)),
        "orientation": orientation,
        "reasons": sorted(set(reasons)),
        "row_declared_component_roles": sorted(row_mapped),
        "status": "MATRIX_FRAGMENT" if orientation is not None and not reasons else "NOT_MATRIX",
    }
    if signed_branch_mode:
        result["matrix_mode"] = "SIGNED_BRANCH_FRAGMENT"
        result["signed_branch_roles"] = sorted(signed_branch_roles)
    return result


def _component_row_continuation_plan_v1(
    *,
    tables: Sequence[Mapping[str, Any]],
    classifications: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Recognize one reciprocal, complementary row-axis page continuation.

    The plan is deliberately narrower than ordinary multi-table coalescing.
    Both structured continuation directions, the MONEY-column layout, the
    declared component inventory and the single grand total must agree.  One
    label split at the page boundary is accepted only when the second label
    fragment has no source values and the concatenated literal uniquely maps
    to a declared component role.
    """

    policy = compiled_specs["component_row_continuation_policy"]
    if (
        policy["mode"]
        != "EXPLICIT_RECIPROCAL_ADJACENT_COMPLEMENTARY_COMPONENT_AXIS"
        or len(tables) != 2
        or len(classifications) != 2
        or tables[0].get("continuation") != "CONTINUES_ON_NEXT_PAGE"
        or tables[1].get("continuation") != "CONTINUES_FROM_PREVIOUS_PAGE"
        or any(item.get("orientation") != "COMPONENT_ROWS" for item in classifications)
        or any(item.get("matrix_mode") is not None for item in classifications)
    ):
        return None
    permitted_fragment_reasons = {
        "EXACTLY_ONE_COMPONENT_GRAND_TOTAL_REQUIRED",
        "UNCLASSIFIED_COMPONENT_AXIS_PRESENT",
    }
    if any(
        not set(item.get("reasons", [])) <= permitted_fragment_reasons
        for item in classifications
    ):
        return None
    columns = [table.get("columns") for table in tables]
    if (
        any(type(axis) is not list or not axis for axis in columns)
        or len(columns[0]) != len(columns[1])
        or [item.get("value_kind") for item in columns[0]]
        != [item.get("value_kind") for item in columns[1]]
    ):
        return None
    money_ordinals = [
        ordinal
        for ordinal, column in enumerate(columns[0], start=1)
        if column.get("value_kind") == "MONEY"
    ]
    if len(money_ordinals) < 4:
        return None
    first_headers = [
        _normalized(" ".join(_header_members(columns[0][ordinal - 1])))
        for ordinal in money_ordinals
    ]
    second_headers = [
        _normalized(" ".join(_header_members(columns[1][ordinal - 1])))
        for ordinal in money_ordinals
    ]
    if any(not header for header in first_headers):
        return None
    if all(not header for header in second_headers):
        header_rule = "SECOND_FRAGMENT_INHERITS_IDENTICAL_POSITIONAL_MONEY_AXIS"
    elif same_typed_json_v1(first_headers, second_headers):
        header_rule = "SECOND_FRAGMENT_REPEATS_EXACT_NORMALIZED_MONEY_AXIS"
    else:
        return None

    fragment_axes: list[list[dict[str, Any]]] = []
    for fragment_ordinal, (table, classification) in enumerate(
        zip(tables, classifications, strict=True), start=1
    ):
        axis = []
        if len(classification["component_axis"]) != len(table["rows"]):
            return None
        for row_ordinal, item in enumerate(classification["component_axis"], start=1):
            axis.append(
                {
                    **canonical_clone_v1(item),
                    "axis_id": f"f{fragment_ordinal}:r{row_ordinal}",
                    "source_axis_id": f"r{row_ordinal}",
                    "source_fragment_ordinal": fragment_ordinal,
                    "source_row_ordinal": row_ordinal,
                }
            )
        fragment_axes.append(axis)

    split_label_receipt = None
    unclassified = [
        (fragment_ordinal, row_ordinal, item)
        for fragment_ordinal, axis in enumerate(fragment_axes, start=1)
        for row_ordinal, item in enumerate(axis, start=1)
        if item["kind"] == "UNCLASSIFIED_COMPONENT_AXIS"
    ]
    skipped_second_row = None
    if unclassified:
        if (
            not policy["allow_blank_leading_label_tail"]
            or len(unclassified) != 2
            or unclassified[0][:2] != (1, len(fragment_axes[0]))
            or unclassified[1][:2] != (2, 1)
        ):
            return None
        first_row = tables[0]["rows"][-1]
        second_row = tables[1]["rows"][0]
        first_label = first_row.get("label_exact")
        second_label = second_row.get("label_exact")
        if (
            type(first_label) is not str
            or not first_label.strip()
            or type(second_label) is not str
            or not second_label.strip()
            or any(
                value is not None and (type(value) is not str or value.strip())
                for value in second_row["values_exact"]
            )
        ):
            return None
        combined_label = f"{first_label.strip()} {second_label.strip()}"
        recovered = _component_record(
            members=[combined_label],
            row_kind=first_row.get("row_kind"),
            axis_id=fragment_axes[0][-1]["axis_id"],
            axis_ordinal=fragment_axes[0][-1]["axis_ordinal"],
            compiled_specs=compiled_specs,
        )
        if recovered["kind"] == "UNCLASSIFIED_COMPONENT_AXIS" or recovered["reasons"]:
            return None
        recovered.update(
            {
                "source_axis_id": fragment_axes[0][-1]["source_axis_id"],
                "source_fragment_ordinal": 1,
                "source_label_fragments_exact": [first_label, second_label],
                "source_row_ordinal": len(fragment_axes[0]),
            }
        )
        fragment_axes[0][-1] = recovered
        skipped_second_row = fragment_axes[1].pop(0)
        split_label_receipt = {
            "combined_label_exact": combined_label,
            "first_source_axis_id": recovered["source_axis_id"],
            "first_source_label_exact": first_label,
            "recovered_role": recovered.get("role"),
            "rule": (
                "RECIPROCAL_PAGE_BOUNDARY_LABEL_FRAGMENTS_JOINED_ONLY_WHEN_"
                "LEADING_TAIL_ROW_ALL_SOURCE_CELLS_BLANK"
            ),
            "second_source_axis_id": skipped_second_row["source_axis_id"],
            "second_source_label_exact": second_label,
        }

    component_axis = [item for axis in fragment_axes for item in axis]
    for ordinal, item in enumerate(component_axis, start=1):
        item["axis_ordinal"] = ordinal
    mapped_kinds = {"MAPPED_COMPONENT", "MAPPED_COMPONENT_GROUP_TOTAL"}
    mapped_roles = [item["role"] for item in component_axis if item["kind"] in mapped_kinds]
    duplicate_roles = {role for role in mapped_roles if mapped_roles.count(role) > 1}
    if (
        any(item["kind"] == "UNCLASSIFIED_COMPONENT_AXIS" for item in component_axis)
        or sum(item["kind"] == "GRAND_TOTAL" for item in component_axis) != 1
        or duplicate_roles - set(compiled_specs["hierarchy_policy"]["aggregate_duplicate_roles"])
        or len(set(mapped_roles)) < compiled_specs["query_policy"]["minimum_mapped_component_roles"]
    ):
        return None
    receipt = {
        "combined_component_axis_sha256": canonical_json_sha256_v1(component_axis),
        "fragment_component_axis_sha256": [
            item["component_axis_sha256"] for item in classifications
        ],
        "money_column_ordinals": money_ordinals,
        "money_header_rule": header_rule,
        "rule": (
            "EXPLICIT_RECIPROCAL_ADJACENT_COMPONENT_ROW_FRAGMENTS_FORM_ONE_"
            "COMPLEMENTARY_COMPONENT_AXIS"
        ),
        "split_label_receipt": split_label_receipt,
    }
    return {
        "component_axis": component_axis,
        "movement_fragment_ordinal": 1,
        "receipt": receipt,
    }


def _supplemental_component_group_plan_v1(
    *,
    tables: Sequence[Mapping[str, Any]],
    classifications: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Recognize a primary equity matrix plus one exact subgroup matrix."""

    policy = compiled_specs["supplemental_component_group_policy"]
    if (
        policy["mode"] != "EXACT_SUPPLEMENTAL_COMPONENT_GROUP_MATRIX"
        or len(tables) != 2
        or len(classifications) != 2
        or any(item.get("orientation") != "COMPONENT_COLUMNS" for item in classifications)
        or any(item.get("matrix_mode") is not None for item in classifications)
        or classifications[0].get("status") != "MATRIX_FRAGMENT"
    ):
        return None
    supplemental_mode = "COMPLETE_ROLLFORWARD_MATRIX"
    supplemental_period_date = None
    if classifications[1].get("status") != "MATRIX_FRAGMENT":
        supplemental_axis = classifications[1].get("component_axis", [])
        supplemental_rows = tables[1].get("rows")
        total_axes = [item for item in supplemental_axis if item["kind"] == "GROUP_TOTAL"]
        movement = (
            _movement_surface_record(
                members=[supplemental_rows[0].get("label_exact")]
                if type(supplemental_rows) is list
                and len(supplemental_rows) == 1
                and type(supplemental_rows[0].get("label_exact")) is str
                else [],
                axis_id="r1",
                axis_ordinal=1,
                source_ref={},
                compiled_specs=compiled_specs,
            )
            if type(supplemental_rows) is list and len(supplemental_rows) == 1
            else None
        )
        combined_boundary_surface = (
            _normalized(supplemental_rows[0].get("label_exact"))
            if type(supplemental_rows) is list
            and len(supplemental_rows) == 1
            and type(supplemental_rows[0].get("label_exact")) is str
            else ""
        )
        explicitly_both_boundaries = bool(
            movement is not None
            and movement["balance_marker"]
            and re.search(r"\bso du dau (?:ky|nam)\b", combined_boundary_surface)
            and re.search(r"\b(?:va|&) cuoi (?:ky|nam)\b", combined_boundary_surface)
        )
        column_dates = [
            sorted(
                item.isoformat()
                for item in _header_dates(" ".join(_header_members(column)))
            )
            for column in tables[1].get("columns", [])
            if column.get("value_kind") == "MONEY"
        ]
        distinct_column_dates = {
            dates[0] for dates in column_dates if len(dates) == 1
        }
        if (
            classifications[1].get("reasons")
            != ["EXACTLY_ONE_COMPONENT_GRAND_TOTAL_REQUIRED"]
            or len(total_axes) != 1
            or movement is None
            or not (
                set(movement["explicit_roles"]) == {"OPENING", "CLOSING"}
                or explicitly_both_boundaries
            )
            or not column_dates
            or any(len(dates) != 1 for dates in column_dates)
            or len(distinct_column_dates) != 1
        ):
            return None
        supplemental_mode = "EXPLICIT_OPENING_AND_CLOSING_PERIOD_SNAPSHOT"
        supplemental_period_date = next(iter(distinct_column_dates))
    primary_axis, supplemental_axis = [item["component_axis"] for item in classifications]
    mapped_kinds = {"MAPPED_COMPONENT", "MAPPED_COMPONENT_GROUP_TOTAL"}
    primary_mapped = {
        item["role"] for item in primary_axis if item["kind"] in mapped_kinds
    }
    supplemental_mapped = {
        item["role"] for item in supplemental_axis if item["kind"] in mapped_kinds
    }
    allowed_children = set(policy["mapped_child_roles"])
    group_axes = [
        item
        for item in primary_axis
        if item["kind"] == "SOURCE_ONLY_COMPONENT"
        and item.get("role") == policy["group_source_only_role"]
    ]
    if (
        len(supplemental_mapped) < 2
        or not supplemental_mapped <= allowed_children
        or len(group_axes) > 1
        or (not group_axes and len(primary_mapped & supplemental_mapped) < 2)
        or (not group_axes and not (primary_mapped - allowed_children))
    ):
        return None
    return {
        "group_axis_id": group_axes[0]["axis_id"] if group_axes else None,
        "mapped_child_roles": sorted(supplemental_mapped),
        "mode": supplemental_mode,
        "overlapping_primary_roles": sorted(primary_mapped & supplemental_mapped),
        "supplemental_period_date": supplemental_period_date,
        "receipt": {
            "group_source_only_role": policy["group_source_only_role"],
            "mapped_child_roles": sorted(supplemental_mapped),
            "mode": supplemental_mode,
            "primary_component_axis_sha256": classifications[0]["component_axis_sha256"],
            "rule": (
                "PRIMARY_EQUITY_MATRIX_PLUS_EXPLICIT_SUPPLEMENTAL_COMPONENT_GROUP_"
                "MATRIX_RECONCILE_BEFORE_CHILD_PROJECTION"
            ),
            "supplemental_component_axis_sha256": classifications[1][
                "component_axis_sha256"
            ],
        },
    }


def _checked_region_axis(regions: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    fields = {
        "document_id",
        "document_ordinal",
        "page_json_version_id",
        "physical_page",
        "selected_page_ordinal",
        "section_id",
        "source_logical_name",
        "source_sha256",
        "table_id",
    }
    if type(regions) not in {list, tuple} or not 1 <= len(regions) <= 2:
        raise _error("equity-matrix region axis must contain one or two fragments")
    result = []
    identity = None
    prior_key = None
    for region in regions:
        if (
            type(region) is not dict
            or set(region) != fields
            or _DOCUMENT_ID.fullmatch(region.get("document_id", "")) is None
            or type(region.get("document_ordinal")) is not int
            or region["document_ordinal"] <= 0
            or _PAGE_VERSION.fullmatch(region.get("page_json_version_id", "")) is None
            or type(region.get("physical_page")) is not int
            or region["physical_page"] <= 0
            or type(region.get("selected_page_ordinal")) is not int
            or region["selected_page_ordinal"] <= 0
            or _SECTION_ID.fullmatch(region.get("section_id", "")) is None
            or _TABLE_ID.fullmatch(region.get("table_id", "")) is None
            or type(region.get("source_logical_name")) is not str
            or not region["source_logical_name"]
            or _SHA256.fullmatch(region.get("source_sha256", "")) is None
        ):
            raise _error("equity-matrix source region is invalid")
        current_identity = tuple(
            region[key]
            for key in (
                "document_id",
                "document_ordinal",
                "source_logical_name",
                "source_sha256",
            )
        )
        key = (
            region["selected_page_ordinal"],
            int(region["section_id"][1:]),
            int(region["table_id"][1:]),
        )
        if identity is None:
            identity = current_identity
        elif current_identity != identity:
            raise _error("equity-matrix fragments belong to different documents")
        if prior_key is not None and key <= prior_key:
            raise _error("equity-matrix fragments are not in source order")
        prior_key = key
        result.append(canonical_clone_v1(region))
    if len(result) == 2:
        # A source can place an unrelated control table between the primary
        # matrix and an explicitly titled supplemental subgroup matrix on the
        # same page.  Source order is already checked above; semantic pairing
        # remains gated later by the family-specific exact subgroup plan.
        same_page_ordered = (
            result[1]["page_json_version_id"] == result[0]["page_json_version_id"]
        )
        adjacent_pages = (
            result[1]["physical_page"] - result[0]["physical_page"] == 1
            and result[1]["selected_page_ordinal"] - result[0]["selected_page_ordinal"] == 1
        )
        if not (same_page_ordered or adjacent_pages):
            raise _error("equity-matrix fragments are not adjacent source siblings")
    return result


def _validate_context_projection_receipts_v1(owner_receipt: Mapping[str, Any]) -> None:
    receipts = owner_receipt.get("context_projection_receipts")
    if receipts is None:
        return
    receipt_fields = {
        "base_page_json_sha256",
        "format_version",
        "page_json_version_id",
        "projected_page_json_sha256",
        "projection_receipt_sha256",
        "raw_response_sha256",
        "rule",
        "title_projection_axis",
    }
    title_fields = {
        "base_title_exact",
        "projected_title_exact",
        "section_id",
        "table_id",
    }
    if type(receipts) is not list or not receipts:
        raise _error("equity-matrix context projection receipt axis is invalid")
    versions = []
    for receipt in receipts:
        titles = receipt.get("title_projection_axis") if type(receipt) is dict else None
        if (
            type(receipt) is not dict
            or set(receipt) != receipt_fields
            or receipt.get("format_version") != "GEMINI_JSON_SEALED_RAW_TABLE_CONTEXT_PROJECTION_V1"
            or _PAGE_VERSION.fullmatch(receipt.get("page_json_version_id", "")) is None
            or any(
                _SHA256.fullmatch(receipt.get(field, "")) is None
                for field in (
                    "base_page_json_sha256",
                    "projected_page_json_sha256",
                    "raw_response_sha256",
                    "projection_receipt_sha256",
                )
            )
            or receipt.get("rule")
            != "ONLY_NULL_TABLE_TITLES_PROMOTED_FROM_AUTHENTICATED_OMITTED_TEXT_HEADERS"
            or type(titles) is not list
            or not titles
            or any(
                type(item) is not dict
                or set(item) != title_fields
                or item.get("base_title_exact") is not None
                or type(item.get("projected_title_exact")) is not str
                or not item["projected_title_exact"].strip()
                or _SECTION_ID.fullmatch(item.get("section_id", "")) is None
                or _TABLE_ID.fullmatch(item.get("table_id", "")) is None
                for item in titles
            )
        ):
            raise _error("equity-matrix context projection receipt drifted")
        material = {
            key: canonical_clone_v1(value)
            for key, value in receipt.items()
            if key != "projection_receipt_sha256"
        }
        if receipt["projection_receipt_sha256"] != canonical_json_sha256_v1(material):
            raise _error("equity-matrix context projection receipt identity drifted")
        versions.append(receipt["page_json_version_id"])
    if len(versions) != len(set(versions)):
        raise _error("equity-matrix context projection repeats one page version")


def build_gemini_json_equity_matrix_region_query_receipt_v1(
    regions: Sequence[Mapping[str, Any]], *, owner_receipt: Mapping[str, Any]
) -> dict[str, Any]:
    """Seal exact component regions and their externally indexed owner fence."""

    checked = _checked_region_axis(regions)
    if type(owner_receipt) is not dict:
        raise _error("equity-matrix owner receipt is invalid")
    _validate_context_projection_receipts_v1(owner_receipt)
    payload = {
        "component_region_axis_sha256": canonical_json_sha256_v1(checked),
        "component_regions": checked,
        "owner_receipt": canonical_clone_v1(owner_receipt),
        "rule": "EXACT_SELECTED_MATRIX_FRAGMENTS_UNDER_ONE_RESET_FENCED_OWNER",
    }
    return {**payload, "query_receipt_sha256": canonical_json_sha256_v1(payload)}


def _movement_matches(members: Sequence[str], *, compiled_specs: Mapping[str, Any]) -> list[str]:
    # Header paths are ordered broad-to-specific. Resolve primary and
    # supplemental semantics independently: a nested balance-side label such
    # as ``Số đầu năm / Phải trả`` must remain OPENING, while ``Số cuối năm /
    # Phải trả`` is a declared CLOSING decomposition term. Likewise a source
    # visible business-combination increase refines the broad ``Phát sinh``
    # parent. Compatibility comes only from the declarative supplemental
    # policy; no column index or bank-specific phrase is used.
    primary_roles = set(_MAPPED_MOVEMENT_ROLES)
    primary: list[str] = []
    supplemental: list[str] = []
    duration_roles = {
        "INCREASE" if match.group(1) == "tang" else "DECREASE"
        for surface in [*members, " ".join(members)]
        if (
            match := re.fullmatch(
                r"(tang|giam) trong (?:0?[1-9]|1[0-2]) thang",
                surface,
            )
        )
        is not None
    }
    english_balance_roles = {
        "OPENING"
        if match.group(1) in {"1", "01"}
        else "CLOSING"
        for surface in [*members, " ".join(members)]
        if (
            match := re.fullmatch(
                r"balance (?:as )?at (1|01|31) (january|december) \d{4}",
                surface,
            )
        )
        is not None
        and (
            (match.group(1) in {"1", "01"} and match.group(2) == "january")
            or (match.group(1) == "31" and match.group(2) == "december")
        )
    }
    for member in members:
        match_surfaces = {
            member,
            re.sub(
                r"\s+(?:trinh bay lai|da duoc trinh bay lai|da dieu chinh)$",
                "",
                member,
            ).strip(),
            # Column formulas commonly append a single parenthesized source
            # marker after the visible unit, for example ``Số đã nộp (c)``.
            # Normalization removes the parentheses.  Ignore only that final
            # one-letter marker for movement matching; retain the literal
            # member in the receipt and never strip words or digits.
            re.sub(r"\s+[a-z]$", "", member).strip(),
        }
        matches = [
            (role, alias)
            for role, aliases in compiled_specs["movement_aliases_by_role"].items()
            for alias in aliases
            if any(_matches(surface, alias) for surface in match_surfaces if surface)
        ]
        primary_matches = [(role, alias) for role, alias in matches if role in primary_roles]
        supplemental_matches = [
            (role, alias) for role, alias in matches if role not in primary_roles
        ]
        # Interim and quarterly disclosures sometimes spell the same declared
        # movement columns as ``Tăng/Giảm trong 03/06/09 tháng``.  The number
        # is a duration, not a reporting endpoint, so recognize only the
        # complete normalized surface and preserve the literal header in the
        # movement receipt.  A longer narrative or a bare year deliberately
        # does not match this grammar.
        if primary_matches:
            longest = max(len(_normalized(alias)) for _role, alias in primary_matches)
            primary = sorted(
                {role for role, alias in primary_matches if len(_normalized(alias)) == longest}
            )
        if supplemental_matches:
            longest = max(len(_normalized(alias)) for _role, alias in supplemental_matches)
            supplemental = sorted(
                {role for role, alias in supplemental_matches if len(_normalized(alias)) == longest}
            )
    if duration_roles:
        primary = sorted(duration_roles)
    if english_balance_roles:
        primary = sorted(english_balance_roles)
    if not primary:
        return supplemental
    if not supplemental:
        return primary
    additive_compatible = set()
    decomposition_compatible = set()
    if len(primary) == 1:
        primary_role = primary[0]
        if primary_role == "INCREASE":
            additive_compatible.update(
                set(supplemental) & set(compiled_specs["supplemental_rollforward_additive_roles"])
            )
        for declaration in compiled_specs["movement_decomposition_equations"]:
            if declaration["result_role"] == primary_role:
                decomposition_compatible.update(
                    set(supplemental) & set(declaration["term_multipliers"])
                )
    if additive_compatible:
        return sorted(additive_compatible)
    if decomposition_compatible:
        # Keep both candidates until the complete column frontier is visible.
        # The graph resolver below selects decomposition terms only when every
        # declared term plus an independent result column is present.
        return sorted({*primary, *decomposition_compatible})
    return primary


def _movement_surface_record(
    *,
    members: Sequence[str],
    axis_id: str,
    axis_ordinal: int,
    source_ref: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    semantic_members = _semantic_component_members(members, compiled_specs=compiled_specs)
    # Alias matching intentionally uses normalized members, but dates must be
    # parsed from the literal surface.  Normalization removes date separators
    # (``1.1.2025`` -> ``1 1 2025``), which would otherwise turn source-visible
    # balance dates into undated rows/columns.
    source_exact = " ".join(member for member in members if type(member) is str)
    explicit_roles = _movement_matches(semantic_members, compiled_specs=compiled_specs)
    dates = sorted(item.isoformat() for item in _header_dates(source_exact))
    folded = _normalized(source_exact)
    standalone_date_marker = bool(
        len(dates) == 1
        and (
            re.fullmatch(r"(?:ngay )?\d{1,2} \d{1,2} \d{4}", folded)
            or re.fullmatch(
                r"(?:ngay )?\d{1,2} thang \d{1,2} nam \d{4}",
                folded,
            )
        )
    )
    balance_marker = bool(
        re.search(r"\b(?:so du|so dau|so cuoi|du dau|du cuoi|tai ngay)\b", folded)
        or standalone_date_marker
        or set(explicit_roles) & {"OPENING", "CLOSING"}
    )
    reasons = []
    # A movement description may legitimately state the covered interval,
    # for example ``lợi nhuận từ ngày ... đến ngày ...``.  Multiple dates are
    # conflicting period evidence only on a declared balance boundary; they
    # do not make an otherwise ordinary movement row ambiguous.
    if len(dates) > 1 and (
        balance_marker or set(explicit_roles) & {"OPENING", "CLOSING"}
    ):
        reasons.append("MOVEMENT_AXIS_SURFACE_HAS_MULTIPLE_DATES")
    return {
        "axis_id": axis_id,
        "axis_ordinal": axis_ordinal,
        "balance_marker": balance_marker,
        "dates": dates,
        "explicit_roles": explicit_roles,
        "members_exact": canonical_clone_v1(list(members)),
        "reasons": reasons,
        "source_ref": canonical_clone_v1(source_ref),
    }


def _collapse_exact_parent_movement_rows_v1(
    rows: Sequence[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Retain an exact visible movement parent and demote its detail rows.

    Some equity statements print both an additive ``Tăng/Giảm`` subtotal and
    its immediately following hierarchy children.  Both are source evidence,
    but adding both would double-count the movement.  A parent replaces its
    children in the arithmetic frontier only when every source cell is
    observed and the parent vector equals the exact sum of those children.
    """

    collapsed_indexes: set[int] = set()
    receipts = []

    def normalized_path(item: Mapping[str, Any]) -> list[str]:
        path = item["row"].get("hierarchy_path_exact")
        return [
            folded
            for member in path
            if (folded := _normalized(member))
        ] if type(path) is list else []

    def is_descendant(parent: Mapping[str, Any], child: Mapping[str, Any]) -> bool:
        parent_label = _normalized(parent["row"].get("label_exact"))
        child_label = _normalized(child["row"].get("label_exact"))
        child_path = normalized_path(child)
        if not parent_label or child_label == parent_label or not child_path:
            return False
        return child_path[0] == parent_label or child_path[0].startswith(parent_label + " ")

    def observed_vector(item: Mapping[str, Any]) -> list[int] | None:
        values = item["row"].get("values_exact")
        if type(values) is not list:
            return None
        result = []
        for value in values:
            try:
                cell = _money(value)
            except ValueError:
                return None
            coefficient = observed_source_coefficient_v1(cell)
            if coefficient is None:
                return None
            result.append(coefficient)
        return result

    for index, parent in enumerate(rows):
        if index in collapsed_indexes or parent.get("explicit_roles") not in (
            ["INCREASE"],
            ["DECREASE"],
        ):
            continue
        children = []
        for child_index in range(index + 1, len(rows)):
            child = rows[child_index]
            if not is_descendant(parent, child):
                break
            children.append((child_index, child))
        if not children:
            continue
        parent_vector = observed_vector(parent)
        child_vectors = [observed_vector(child) for _child_index, child in children]
        if (
            parent_vector is None
            or any(vector is None for vector in child_vectors)
            or any(len(vector) != len(parent_vector) for vector in child_vectors if vector)
        ):
            continue
        computed = [
            sum(vector[column_index] for vector in child_vectors if vector is not None)
            for column_index in range(len(parent_vector))
        ]
        if computed != parent_vector:
            continue
        collapsed_indexes.update(child_index for child_index, _child in children)
        receipts.append(
            {
                "axis_role": parent["explicit_roles"][0],
                "child_source_refs": [
                    canonical_clone_v1(child["source_ref"]) for _child_index, child in children
                ],
                "computed_vector": computed,
                "parent_source_ref": canonical_clone_v1(parent["source_ref"]),
                "parent_vector": parent_vector,
                "rule": (
                    "EXACT_FULLY_OBSERVED_PARENT_MOVEMENT_VECTOR_EQUALS_"
                    "CONTIGUOUS_DECLARED_HIERARCHY_CHILD_SUM"
                ),
            }
        )
    return (
        [item for index, item in enumerate(rows) if index not in collapsed_indexes],
        receipts,
    )


def _component_projection(axis: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "axis_ordinal": item["axis_ordinal"],
            "group_prefix": canonical_clone_v1(item["group_prefix"]),
            "kind": item["kind"],
            "role": item["role"],
            "semantic_path": canonical_clone_v1(item["semantic_path"]),
        }
        for item in axis
    ]


def _local_unit_axis(
    table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    evidence = []
    conflicts = []
    undeclared = []

    def classify(text: Any, source_kind: str, *, explicit_slot: bool) -> dict[str, Any] | None:
        if type(text) is not str or not text.strip():
            return None
        occurrences = _unit_occurrences(text, compiled_specs=compiled_specs)
        if occurrences:
            identities = {
                (item["canonical_unit"], item["magnitude_power10"]) for item in occurrences
            }
            records = [
                {**item, "source_kind": source_kind, "text_exact": text} for item in occurrences
            ]
            evidence.extend(records)
            if len(identities) > 1:
                conflicts.append(
                    {
                        "matched_aliases": [item["matched_alias"] for item in occurrences],
                        "source_kind": source_kind,
                        "text_exact": text,
                    }
                )
                return None
            return records[0]
        # A bare ``đồng`` inside a semantic label such as ``cổ đông`` is not a
        # unit declaration.  Outside the typed table-unit slot, only an
        # explicit magnitude+currency phrase or a currency token is unit-like
        # enough to make an undeclared-unit claim.
        folded = _normalized(text)
        unit_like = re.search(
            r"\b(?:(?:trieu|nghin|ty)\s+(?:dong|vnd|usd)|vnd|usd)\b",
            folded,
        )
        currency_axis_without_magnitude = (
            compiled_specs.get("currency_risk_mode") is True
            and not explicit_slot
            and re.search(r"\b(?:trieu|nghin|ty)\b", folded) is None
        )
        if explicit_slot or unit_like and not currency_axis_without_magnitude:
            undeclared.append({"source_kind": source_kind, "text_exact": text})
        return None

    table_record = classify(table.get("unit_exact"), "TABLE_UNIT", explicit_slot=True)
    columns = table.get("columns")
    money_columns = (
        [
            (ordinal, column)
            for ordinal, column in enumerate(columns, start=1)
            if type(column) is dict
            and (
                column.get("value_kind") == "MONEY" or compiled_specs.get("valuation_mode") is True
            )
        ]
        if type(columns) is list
        else []
    )
    column_records = [
        classify(
            " ".join(_header_members(column)),
            f"MONEY_COLUMN_HEADER:c{ordinal}",
            explicit_slot=False,
        )
        for ordinal, column in money_columns
    ]
    reasons = []
    if conflicts:
        reasons.append("CONFLICTING_DECLARED_UNIT_ALIASES_ON_ONE_SURFACE")
    if undeclared:
        reasons.append("UNDECLARED_EXPLICIT_MONEY_UNIT")
    if any(item is not None and not item["accepted"] for item in [table_record, *column_records]):
        reasons.append("EXPLICIT_MONEY_UNIT_IS_NOT_ACCEPTED")
    canonical_unit = None
    source = None
    if table_record is not None and table_record["accepted"]:
        canonical_unit = table_record["canonical_unit"]
        source = "LOCAL_TABLE_UNIT"
        if any(
            item is not None and item["canonical_unit"] != canonical_unit for item in column_records
        ):
            reasons.append("TABLE_AND_COLUMN_MONEY_UNITS_CONFLICT")
    elif any(item is not None for item in column_records):
        valuation_nonfair_records = []
        if compiled_specs.get("valuation_mode") is True:
            fair_aliases = compiled_specs["valuation_marker_aliases"]["fair_value_header_aliases"]
            valuation_nonfair_records = [
                record
                for record, (_ordinal, column) in zip(column_records, money_columns, strict=True)
                if not _valuation_header_has_v1(_header_members(column), fair_aliases)
            ]
        if (
            valuation_nonfair_records
            and all(item is not None and item["accepted"] for item in valuation_nonfair_records)
            and len({item["canonical_unit"] for item in valuation_nonfair_records}) == 1
            and all(
                record is not None
                or _valuation_header_has_v1(
                    _header_members(column),
                    compiled_specs["valuation_marker_aliases"]["fair_value_header_aliases"],
                )
                for record, (_ordinal, column) in zip(column_records, money_columns, strict=True)
            )
        ):
            canonical_unit = valuation_nonfair_records[0]["canonical_unit"]
            source = "LOCAL_UNIFORM_BOOK_COLUMNS_WITH_UNITLESS_FAIR_COLUMN"
        elif (
            len(column_records) != len(money_columns)
            or any(item is None for item in column_records)
            or any(not item["accepted"] for item in column_records if item is not None)
        ):
            reasons.append("MONEY_COLUMN_UNIT_EVIDENCE_IS_PARTIAL")
        else:
            units = {item["canonical_unit"] for item in column_records if item is not None}
            if len(units) != 1:
                reasons.append("MONEY_COLUMN_UNITS_CONFLICT")
            else:
                canonical_unit = next(iter(units))
                source = "LOCAL_UNIFORM_ALL_MONEY_COLUMN_UNITS"
    return {
        "canonical_unit": canonical_unit,
        "complete": canonical_unit is not None and not reasons,
        "conflicting_surfaces": conflicts,
        "evidence": evidence,
        "reasons": sorted(set(reasons)),
        "source": source,
        "undeclared_evidence": undeclared,
    }


def _resolve_cluster_unit(
    *,
    tables: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    document_unit_context_evidence: Mapping[str, Any] | None,
    family_root_boundary_vector: Mapping[str, int] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    local = [_local_unit_axis(table, compiled_specs=compiled_specs) for table in tables]
    reasons = [
        f"FRAGMENT_{ordinal}:{reason}"
        for ordinal, axis in enumerate(local, start=1)
        for reason in axis["reasons"]
    ]
    units = {axis["canonical_unit"] for axis in local if axis["complete"]}
    explicit_incomplete = any(
        not axis["complete"] and (axis["evidence"] or axis["undeclared_evidence"]) for axis in local
    )
    source = None
    canonical_unit = None
    if len(units) > 1:
        reasons.append("MATRIX_FRAGMENT_UNITS_CONFLICT")
    elif len(units) == 1 and not explicit_incomplete:
        canonical_unit = next(iter(units))
        source = "LOCAL_MATRIX_FRAGMENT_UNIT"
    elif not units and not explicit_incomplete:
        context = document_unit_context_evidence
        if (
            type(context) is dict
            and context.get("status") == "UNIQUE_AUTHENTICATED_DOCUMENT_MONEY_UNIT_CONSENSUS"
            and type(context.get("canonical_unit")) is str
        ):
            canonical_unit = context["canonical_unit"]
            source = "INDEXED_DOCUMENT_MONEY_UNIT_CONSENSUS"
        else:
            root_evidence = (
                context.get("primary_statement_root_unit_evidence", [])
                if type(context) is dict
                else []
            )
            matches = [
                item
                for item in root_evidence
                if type(item) is dict
                and type(family_root_boundary_vector) is dict
                and item.get("root_values_source_order")
                == [
                    family_root_boundary_vector.get("closing"),
                    family_root_boundary_vector.get("opening"),
                ]
            ]
            if (
                compiled_specs.get("primary_statement_root_unit_policy", {}).get("mode")
                == "EXACT_FAMILY_ROOT_BOUNDARY_VECTOR_CORROBORATION"
                and len(matches) == 1
                and type(matches[0].get("canonical_unit")) is str
            ):
                canonical_unit = matches[0]["canonical_unit"]
                source = "EXACT_PRIMARY_STATEMENT_FAMILY_ROOT_BOUNDARY_VECTOR_UNIT"
            else:
                reasons.append("AUTHENTICATED_DOCUMENT_MONEY_UNIT_CONSENSUS_UNAVAILABLE")
    return (
        {
            "canonical_unit": canonical_unit,
            "document_unit_context_evidence": canonical_clone_v1(document_unit_context_evidence),
            "fragment_unit_axes": local,
            "source": source,
        },
        sorted(set(reasons)),
    )


def _parsed_cell(
    *, value: Any, region: Mapping[str, Any], row_id: str, column_id: str
) -> tuple[dict[str, Any] | None, str | None]:
    source_value = value
    if type(value) is str:
        compact = "".join(value.split())
        if compact and (
            all(character in "-–—_" for character in compact)
            or (
                any(character in "-–—_" for character in compact)
                and not any(character.isdigit() for character in compact)
            )
        ):
            value = "-"
    try:
        parsed = _money(value)
    except ValueError:
        parsed = None
    if parsed is None and type(value) is str:
        # Some otherwise complete matrix cells retain a source footnote/OCR
        # suffix (for example ``19.279.848(*)`` or ``25带有-``).  Recover a
        # value only when one and only one numeric token starts the cell.  A
        # leading dash before a parenthesized amount (``-(5.000)``) is rejected:
        # in compacted matrices that surface can represent two adjacent source
        # cells and must be resolved by layout evidence, not scalar parsing.
        stripped = value.strip()
        numeric_tokens = list(
            re.finditer(r"\(?-?\d{1,3}(?:[.,]\d{3})+\)?|\(?-?\d+\)?", stripped)
        )
        if len(numeric_tokens) == 1 and numeric_tokens[0].start() == 0:
            token = numeric_tokens[0].group(0)
            suffix = stripped[numeric_tokens[0].end() :]
            if suffix and not any(character.isdigit() for character in suffix):
                try:
                    normalized = _money(token)
                except ValueError:
                    normalized = None
                if normalized is not None and normalized["state"] == "RAW_SIGNED_INTEGER":
                    parsed = {
                        **normalized,
                        "state": "NORMALIZED_SINGLE_NUMERIC_TOKEN_PENDING_GRAPH",
                    }
    if parsed is None:
        return None, f"MONEY_CELL_INVALID:{region['page_json_version_id']}:{row_id}:{column_id}"
    parsed["source_text"] = source_value
    return (
        {
            **parsed,
            "cell_ref": {
                "column_id": column_id,
                "locator": canonical_clone_v1(region),
                "row_id": row_id,
            },
        },
        None,
    )


def _dash_prefixed_numeric_coefficient(value: Any) -> int | None:
    if type(value) is not str:
        return None
    remainder = re.sub(r"^[\s\-–—_]+", "", value)
    if remainder == value or not remainder.strip():
        return None
    try:
        parsed = _money(remainder)
    except ValueError:
        return None
    return parsed["coefficient"] if parsed["state"] == "RAW_SIGNED_INTEGER" else None


def _signed_branch_movement_axis_v1(
    *, table: Mapping[str, Any], region: Mapping[str, Any], compiled_specs: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[str]]:
    raw = [
        _movement_surface_record(
            members=_header_members(column),
            axis_id=f"c{ordinal}",
            axis_ordinal=ordinal,
            source_ref={**canonical_clone_v1(region), "column_id": f"c{ordinal}"},
            compiled_specs=compiled_specs,
        )
        for ordinal, column in enumerate(table["columns"], start=1)
    ]
    reasons = [reason for item in raw for reason in item["reasons"]]
    by_role = {role: [] for role in _MAPPED_MOVEMENT_ROLES}
    for item in raw:
        roles = [role for role in item["explicit_roles"] if role in by_role]
        if len(roles) == 1:
            by_role[roles[0]].append(item)
        elif len(roles) > 1:
            reasons.append("SIGNED_BRANCH_MOVEMENT_SURFACE_IS_AMBIGUOUS")
    # A source matrix may print only the boundary dates (``1.1.2025`` and
    # ``31.12.2025``), without an additional ``opening``/``closing`` label.
    # Treat those dates as endpoint evidence only when they are the two unique
    # outer columns in increasing order.  This is a structural/date grammar,
    # not a column-index fallback: a date on an interior movement column,
    # duplicate dates, or a date contradicting an explicit endpoint remains
    # unresolved and is subsequently vetoed by the exact movement frontier.
    if not by_role["OPENING"] or not by_role["CLOSING"]:
        dated = [item for item in raw if len(item["dates"]) == 1]
        if (
            len(dated) == 2
            and dated[0] is raw[0]
            and dated[1] is raw[-1]
            and dated[0]["dates"][0] < dated[1]["dates"][0]
        ):
            if not by_role["OPENING"]:
                by_role["OPENING"].append(dated[0])
            elif by_role["OPENING"] != [dated[0]]:
                reasons.append("SIGNED_BRANCH_EXPLICIT_OPENING_CONTRADICTS_DATE_BOUNDARY")
            if not by_role["CLOSING"]:
                by_role["CLOSING"].append(dated[1])
            elif by_role["CLOSING"] != [dated[1]]:
                reasons.append("SIGNED_BRANCH_EXPLICIT_CLOSING_CONTRADICTS_DATE_BOUNDARY")
    if any(len(by_role[role]) != 1 for role in _MAPPED_MOVEMENT_ROLES):
        reasons.append("SIGNED_BRANCH_EXACT_PRIMARY_MOVEMENT_AXIS_REQUIRED")
        return [], sorted(set(reasons))
    selected = [by_role[role][0] for role in _MAPPED_MOVEMENT_ROLES]
    if len({id(item) for item in selected}) != len(selected) or len(raw) != len(selected):
        reasons.append("SIGNED_BRANCH_UNCONSUMED_OR_DUPLICATE_MOVEMENT_COLUMN")
        return [], sorted(set(reasons))
    if [item["axis_ordinal"] for item in selected] != sorted(
        item["axis_ordinal"] for item in selected
    ):
        reasons.append("SIGNED_BRANCH_MOVEMENT_COLUMN_ORDER_DRIFTED")
        return [], sorted(set(reasons))
    for role, item in zip(_MAPPED_MOVEMENT_ROLES, selected, strict=True):
        item["axis_role"] = role
    return selected, sorted(set(reasons))


def _signed_branch_derived_cell_v1(
    *,
    source_cells: Sequence[tuple[Mapping[str, Any], int]],
    axis_role: str,
) -> dict[str, Any]:
    components = [
        _mapping_value(cell, axis_role=axis_role, equation_multiplier=multiplier)
        for cell, multiplier in source_cells
    ]
    return {
        "aggregate_components": components,
        "cell_ref": None,
        "coefficient": sum(
            component["coefficient"] * component["equation_multiplier"] for component in components
        ),
        "source_text": None,
        "state": "SIGNED_BRANCH_NET_SOURCE_CELLS_GRAPH_EXACT",
    }


def _build_signed_branch_matrix_graph_v1(
    *,
    regions: Sequence[Mapping[str, Any]],
    tables: Sequence[Mapping[str, Any]],
    classifications: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    reasons = []
    if any(
        item.get("matrix_mode") != "SIGNED_BRANCH_FRAGMENT"
        or item.get("orientation") != "COMPONENT_ROWS"
        for item in classifications
    ):
        return {}, ["SIGNED_BRANCH_FRAGMENT_MODES_DIFFER"]
    expected_branches = tuple(sorted(compiled_specs["signed_branch_multipliers"]))
    visible_branches = {
        role for item in classifications for role in item.get("signed_branch_roles", [])
    }
    if visible_branches != set(expected_branches):
        return {}, ["SIGNED_BRANCH_EXACT_DECLARED_FRONTIER_REQUIRED"]
    source_movement_axes = []
    for region, table in zip(regions, tables, strict=True):
        movement, movement_reasons = _signed_branch_movement_axis_v1(
            table=table, region=region, compiled_specs=compiled_specs
        )
        source_movement_axes.append(movement)
        reasons.extend(movement_reasons)
    if reasons:
        return {}, sorted(set(reasons))
    if any(
        [item["axis_role"] for item in movement] != list(_MAPPED_MOVEMENT_ROLES)
        for movement in source_movement_axes
    ):
        return {}, ["SIGNED_BRANCH_MOVEMENT_AXES_DIFFER"]

    raw_axis = []
    raw_cells: dict[str, dict[str, dict[str, Any]]] = {}
    for fragment_ordinal, (region, table, classification, movement_axis) in enumerate(
        zip(regions, tables, classifications, source_movement_axes, strict=True), start=1
    ):
        for source_item, row in zip(classification["component_axis"], table["rows"], strict=True):
            item = canonical_clone_v1(source_item)
            item["source_axis_id"] = item["axis_id"]
            item["source_fragment_ordinal"] = fragment_ordinal
            item["axis_id"] = f"f{fragment_ordinal}:{item['source_axis_id']}"
            item["axis_ordinal"] = len(raw_axis) + 1
            raw_axis.append(item)
            raw_cells[item["axis_id"]] = {}
            if item["kind"] == "SIGNED_BRANCH_HEADER":
                continue
            for movement in movement_axis:
                cell, reason = _parsed_cell(
                    value=row["values_exact"][movement["axis_ordinal"] - 1],
                    region=region,
                    row_id=item["source_axis_id"],
                    column_id=movement["axis_id"],
                )
                if reason:
                    reasons.append(reason)
                elif cell is not None:
                    raw_cells[item["axis_id"]][movement["axis_role"]] = cell

    branch_axes = {
        branch_role: [item for item in raw_axis if item.get("signed_branch_role") == branch_role]
        for branch_role in expected_branches
    }
    branch_movement_multipliers = {}
    equations = []
    for branch_role, branch_items in branch_axes.items():
        totals = [item for item in branch_items if item["kind"] == "SIGNED_BRANCH_TOTAL"]
        leaves = [
            item
            for item in branch_items
            if item["kind"] in {"MAPPED_COMPONENT", "SOURCE_ONLY_COMPONENT"}
        ]
        if len(totals) != 1 or not leaves:
            reasons.append("SIGNED_BRANCH_TOTAL_OR_LEAF_AXIS_INCOMPLETE")
            continue
        total = totals[0]
        for axis_role in _MAPPED_MOVEMENT_ROLES:
            result = raw_cells[total["axis_id"]].get(axis_role)
            terms = [raw_cells[item["axis_id"]].get(axis_role) for item in leaves]
            if result is None or any(cell is None for cell in terms):
                reasons.append("SIGNED_BRANCH_HORIZONTAL_CELL_AXIS_INCOMPLETE")
                continue
            computed = sum(cell["coefficient"] for cell in terms if cell is not None)
            status = "EXACT" if computed == result["coefficient"] else "MISMATCH"
            equations.append(
                {
                    "axis_role": axis_role,
                    "branch_role": branch_role,
                    "computed_value": computed,
                    "equation_kind": "VISIBLE_SIGNED_BRANCH_HORIZONTAL_TOTAL",
                    "result": _cell_term(result),
                    "status": status,
                    "terms": [_cell_term(cell) for cell in terms if cell is not None],
                    "total_axis_id": total["axis_id"],
                }
            )
            if status != "EXACT":
                reasons.append("SIGNED_BRANCH_HORIZONTAL_TOTAL_MISMATCH")
        equation_items = [*leaves, total]
        modes = []
        for increase_multiplier in (1, -1):
            for decrease_multiplier in (1, -1):
                if all(
                    raw_cells[item["axis_id"]]["OPENING"]["coefficient"]
                    + increase_multiplier * raw_cells[item["axis_id"]]["INCREASE"]["coefficient"]
                    + decrease_multiplier * raw_cells[item["axis_id"]]["DECREASE"]["coefficient"]
                    == raw_cells[item["axis_id"]]["CLOSING"]["coefficient"]
                    for item in equation_items
                ):
                    modes.append((increase_multiplier, decrease_multiplier))
        if len(modes) > 1:
            varying_roles = {
                role
                for role in ("INCREASE", "DECREASE")
                if any(
                    raw_cells[item["axis_id"]][role]["coefficient"] != 0 for item in equation_items
                )
            }
            modes = [
                mode
                for mode in modes
                if all(
                    multiplier == 1
                    for role, multiplier in zip(("INCREASE", "DECREASE"), mode, strict=True)
                    if role not in varying_roles
                )
            ]
        if len(modes) != 1:
            reasons.append("SIGNED_BRANCH_VERTICAL_SIGN_MODE_NOT_UNIQUE")
            continue
        increase_multiplier, decrease_multiplier = modes[0]
        branch_movement_multipliers[branch_role] = {
            "CLOSING": 1,
            "DECREASE": decrease_multiplier,
            "INCREASE": increase_multiplier,
            "OPENING": 1,
        }
        for item in equation_items:
            opening = raw_cells[item["axis_id"]]["OPENING"]
            increase = raw_cells[item["axis_id"]]["INCREASE"]
            decrease = raw_cells[item["axis_id"]]["DECREASE"]
            closing = raw_cells[item["axis_id"]]["CLOSING"]
            computed = (
                opening["coefficient"]
                + increase_multiplier * increase["coefficient"]
                + decrease_multiplier * decrease["coefficient"]
            )
            equations.append(
                {
                    "branch_role": branch_role,
                    "component_axis_id": item["axis_id"],
                    "computed_value": computed,
                    "decrease_multiplier": decrease_multiplier,
                    "equation_kind": "VERTICAL_SIGNED_BRANCH_ROLLFORWARD",
                    "increase_multiplier": increase_multiplier,
                    "result": _cell_term(closing),
                    "status": "EXACT",
                    "terms": [
                        _cell_term(opening),
                        _cell_term(increase, multiplier=increase_multiplier),
                        _cell_term(decrease, multiplier=decrease_multiplier),
                    ],
                }
            )
    if reasons or set(branch_movement_multipliers) != set(expected_branches):
        return {}, sorted(set(reasons))

    role_order = []
    for item in raw_axis:
        if item["kind"] == "MAPPED_COMPONENT" and item["role"] not in role_order:
            role_order.append(item["role"])
    synthetic_axis = []
    synthetic_cells = {}
    for role in role_order:
        source_items = [
            item for item in raw_axis if item["kind"] == "MAPPED_COMPONENT" and item["role"] == role
        ]
        item = {
            "axis_id": f"signed-net:{role}",
            "axis_ordinal": len(synthetic_axis) + 1,
            "group_prefix": [],
            "kind": "MAPPED_COMPONENT",
            "members_exact": [],
            "reasons": [],
            "role": role,
            "semantic_path": [f"signed net {role.lower()}"],
            "signed_branch_components": canonical_clone_v1(source_items),
        }
        synthetic_axis.append(item)
        synthetic_cells[item["axis_id"]] = {}
        for axis_role in _MAPPED_MOVEMENT_ROLES:
            sources = []
            for source_item in source_items:
                branch_role = source_item["signed_branch_role"]
                multiplier = compiled_specs["signed_branch_multipliers"][branch_role]
                multiplier *= branch_movement_multipliers[branch_role][axis_role]
                sources.append((raw_cells[source_item["axis_id"]][axis_role], multiplier))
            synthetic_cells[item["axis_id"]][axis_role] = _signed_branch_derived_cell_v1(
                source_cells=sources, axis_role=axis_role
            )
    branch_totals = [item for item in raw_axis if item["kind"] == "SIGNED_BRANCH_TOTAL"]
    grand_total = {
        "axis_id": "signed-net:FAMILY_TOTAL",
        "axis_ordinal": len(synthetic_axis) + 1,
        "group_prefix": [],
        "kind": "GRAND_TOTAL",
        "members_exact": [],
        "reasons": [],
        "role": None,
        "semantic_path": ["signed net family total"],
        "signed_branch_components": canonical_clone_v1(branch_totals),
    }
    synthetic_axis.append(grand_total)
    synthetic_cells[grand_total["axis_id"]] = {}
    for axis_role in _MAPPED_MOVEMENT_ROLES:
        sources = []
        for source_item in branch_totals:
            branch_role = source_item["signed_branch_role"]
            multiplier = compiled_specs["signed_branch_multipliers"][branch_role]
            multiplier *= branch_movement_multipliers[branch_role][axis_role]
            sources.append((raw_cells[source_item["axis_id"]][axis_role], multiplier))
        synthetic_cells[grand_total["axis_id"]][axis_role] = _signed_branch_derived_cell_v1(
            source_cells=sources, axis_role=axis_role
        )

    for item in synthetic_axis:
        for axis_role in _MAPPED_MOVEMENT_ROLES:
            result = synthetic_cells[item["axis_id"]][axis_role]
            equations.append(
                {
                    "axis_role": axis_role,
                    "component_axis_id": item["axis_id"],
                    "computed_value": result["coefficient"],
                    "equation_kind": "SIGNED_BRANCH_NET_COMPONENT_DERIVATION",
                    "result": {
                        "cell_ref": None,
                        "coefficient": result["coefficient"],
                        "multiplier": 1,
                        "state": result["state"],
                    },
                    "status": "EXACT",
                    "terms": [
                        {
                            "cell_ref": canonical_clone_v1(component["cell_ref"]),
                            "coefficient": component["coefficient"],
                            "multiplier": component["equation_multiplier"],
                            "state": component["state"],
                        }
                        for component in result["aggregate_components"]
                    ],
                }
            )
        opening = synthetic_cells[item["axis_id"]]["OPENING"]
        increase = synthetic_cells[item["axis_id"]]["INCREASE"]
        decrease = synthetic_cells[item["axis_id"]]["DECREASE"]
        closing = synthetic_cells[item["axis_id"]]["CLOSING"]
        computed = opening["coefficient"] + increase["coefficient"] + decrease["coefficient"]
        if computed != closing["coefficient"]:
            reasons.append("SIGNED_BRANCH_NET_ROLLFORWARD_MISMATCH")
        equations.append(
            {
                "component_axis_id": item["axis_id"],
                "computed_value": computed,
                "equation_kind": "VERTICAL_SIGNED_BRANCH_NET_ROLLFORWARD",
                "result": {
                    "cell_ref": None,
                    "coefficient": closing["coefficient"],
                    "multiplier": 1,
                    "state": closing["state"],
                },
                "status": "EXACT" if computed == closing["coefficient"] else "MISMATCH",
                "terms": [
                    {
                        "cell_ref": None,
                        "coefficient": cell["coefficient"],
                        "multiplier": 1,
                        "state": cell["state"],
                    }
                    for cell in (opening, increase, decrease)
                ],
            }
        )
    movement_axis = []
    for ordinal, _axis_role in enumerate(_MAPPED_MOVEMENT_ROLES):
        item = canonical_clone_v1(source_movement_axes[0][ordinal])
        item["signed_branch_source_axes"] = [
            canonical_clone_v1(axis[ordinal]) for axis in source_movement_axes
        ]
        movement_axis.append(item)
    return (
        {
            "alignment_receipts": [],
            "component_axis": synthetic_axis,
            "component_cells": synthetic_cells,
            "equations": equations,
            "movement_axis": movement_axis,
            "movement_decomposition_equations": [],
            "orientation": "COMPONENT_ROWS",
            "period_block_receipt": None,
            "signed_branch_mode": True,
            "signed_branch_receipt": {
                "branch_movement_multipliers": branch_movement_multipliers,
                "branch_multipliers": canonical_clone_v1(
                    compiled_specs["signed_branch_multipliers"]
                ),
                "raw_component_axis": raw_axis,
                "rule": "EACH_BRANCH_HORIZONTAL_AND_VERTICAL_EXACT_BEFORE_SIGNED_NET_PROJECTION",
            },
            "supplemental_rollforward_additive_roles": [],
        },
        sorted(set(reasons)),
    )


def _build_matrix_graph(
    *,
    regions: Sequence[Mapping[str, Any]],
    tables: Sequence[Mapping[str, Any]],
    classifications: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    if classifications and any(
        item.get("matrix_mode") == "SIGNED_BRANCH_FRAGMENT" for item in classifications
    ):
        return _build_signed_branch_matrix_graph_v1(
            regions=regions,
            tables=tables,
            classifications=classifications,
            compiled_specs=compiled_specs,
        )
    supplemental_plan = _supplemental_component_group_plan_v1(
        tables=tables,
        classifications=classifications,
        compiled_specs=compiled_specs,
    )
    if supplemental_plan is not None:
        primary_graph, primary_reasons = _build_matrix_graph(
            regions=regions[:1],
            tables=tables[:1],
            classifications=classifications[:1],
            compiled_specs=compiled_specs,
        )
        if supplemental_plan["mode"] == "COMPLETE_ROLLFORWARD_MATRIX":
            supplemental_graph, supplemental_reasons = _build_matrix_graph(
                regions=regions[1:],
                tables=tables[1:],
                classifications=classifications[1:],
                compiled_specs=compiled_specs,
            )
        else:
            source_axis = classifications[1]["component_axis"]
            snapshot_axis = []
            snapshot_cells = {}
            supplemental_reasons = []
            for item in source_axis:
                projected = canonical_clone_v1(item)
                if projected["kind"] == "GROUP_TOTAL":
                    projected["kind"] = "GRAND_TOTAL"
                    projected["group_prefix"] = []
                snapshot_axis.append(projected)
                value = tables[1]["rows"][0]["values_exact"][item["axis_ordinal"] - 1]
                cell, reason = _parsed_cell(
                    value=value,
                    region=regions[1],
                    row_id="r1",
                    column_id=item["axis_id"],
                )
                if reason:
                    supplemental_reasons.append(reason)
                    continue
                assert cell is not None
                snapshot_cells[item["axis_id"]] = {
                    "OPENING": canonical_clone_v1(cell),
                    "CLOSING": canonical_clone_v1(cell),
                }
            movement_source = _movement_surface_record(
                members=[tables[1]["rows"][0]["label_exact"]],
                axis_id="r1",
                axis_ordinal=1,
                source_ref={**canonical_clone_v1(regions[1]), "row_id": "r1"},
                compiled_specs=compiled_specs,
            )
            supplemental_graph = {
                "alignment_receipts": [],
                "component_axis": snapshot_axis,
                "component_cells": snapshot_cells,
                "movement_axis": [
                    {
                        **canonical_clone_v1(movement_source),
                        "axis_id": f"snapshot:{axis_role}",
                        "axis_role": axis_role,
                    }
                    for axis_role in ("OPENING", "CLOSING")
                ],
                "movement_decomposition_equations": [],
                "orientation": "COMPONENT_COLUMNS",
                "period_block_receipt": {
                    "period_date": supplemental_plan["supplemental_period_date"],
                    "rule": (
                        "EXPLICIT_SOURCE_ROW_DECLARING_BOTH_OPENING_AND_CLOSING_"
                        "WITH_ONE_COLUMN_PERIOD"
                    ),
                },
                "supplemental_rollforward_additive_roles": [],
            }
        reasons = [
            *[f"PRIMARY_COMPONENT_GROUP:{reason}" for reason in primary_reasons],
            *[
                f"SUPPLEMENTAL_COMPONENT_GROUP:{reason}"
                for reason in supplemental_reasons
            ],
        ]
        primary_equations = []
        supplemental_equations = []
        if primary_graph and not primary_reasons:
            primary_equations, equation_reasons, _primary_sign = _build_equations(
                primary_graph
            )
            reasons.extend(
                f"PRIMARY_COMPONENT_GROUP:{reason}" for reason in equation_reasons
            )
        if supplemental_graph and not supplemental_reasons:
            supplemental_equations, equation_reasons, _supplemental_sign = _build_equations(
                supplemental_graph
            )
            reasons.extend(
                f"SUPPLEMENTAL_COMPONENT_GROUP:{reason}" for reason in equation_reasons
            )
        if reasons or not primary_graph or not supplemental_graph:
            return primary_graph, sorted(set(reasons))

        primary_axis_by_role = {
            item["role"]: item
            for item in primary_graph["component_axis"]
            if item["kind"] in {"MAPPED_COMPONENT", "MAPPED_COMPONENT_GROUP_TOTAL"}
        }
        supplemental_axis_by_role = {
            item["role"]: item
            for item in supplemental_graph["component_axis"]
            if item["kind"] in {"MAPPED_COMPONENT", "MAPPED_COMPONENT_GROUP_TOTAL"}
        }
        primary_movement_roles = {
            item["axis_role"] for item in primary_graph["movement_axis"]
        }
        supplemental_movement_roles = {
            item["axis_role"] for item in supplemental_graph["movement_axis"]
        }
        boundary_roles = [
            role
            for role in ("OPENING", "CLOSING")
            if role in primary_movement_roles and role in supplemental_movement_roles
        ]
        if boundary_roles != ["OPENING", "CLOSING"]:
            return primary_graph, ["SUPPLEMENTAL_COMPONENT_GROUP_BOUNDARY_AXIS_INCOMPLETE"]

        reconciliation = []

        def compare_cells(
            *,
            comparison_role: str,
            primary_cell: Mapping[str, Any],
            supplemental_cell: Mapping[str, Any],
            axis_role: str,
        ) -> None:
            primary_value = observed_source_coefficient_v1(primary_cell)
            supplemental_value = observed_source_coefficient_v1(supplemental_cell)
            status = (
                "INCOMPLETE_BLANK_SOURCE_CELL"
                if primary_value is None or supplemental_value is None
                else "EXACT"
                if primary_value == supplemental_value
                else "MISMATCH"
            )
            reconciliation.append(
                {
                    "axis_role": axis_role,
                    "comparison_role": comparison_role,
                    "primary_cell": canonical_clone_v1(primary_cell),
                    "status": status,
                    "supplemental_cell": canonical_clone_v1(supplemental_cell),
                }
            )
            if status != "EXACT":
                reasons.append(
                    "SUPPLEMENTAL_COMPONENT_GROUP_SOURCE_CONFLICT_OR_BLANK_BOUNDARY"
                )

        group_axis_id = supplemental_plan["group_axis_id"]
        supplemental_grand = next(
            item
            for item in supplemental_graph["component_axis"]
            if item["kind"] == "GRAND_TOTAL"
        )
        if group_axis_id is not None:
            for axis_role in boundary_roles:
                compare_cells(
                    comparison_role=supplemental_plan["receipt"][
                        "group_source_only_role"
                    ],
                    primary_cell=primary_graph["component_cells"][group_axis_id][
                        axis_role
                    ],
                    supplemental_cell=supplemental_graph["component_cells"][
                        supplemental_grand["axis_id"]
                    ][axis_role],
                    axis_role=axis_role,
                )
        else:
            for role in supplemental_plan["overlapping_primary_roles"]:
                for axis_role in boundary_roles:
                    compare_cells(
                        comparison_role=role,
                        primary_cell=primary_graph["component_cells"][
                            primary_axis_by_role[role]["axis_id"]
                        ][axis_role],
                        supplemental_cell=supplemental_graph["component_cells"][
                            supplemental_axis_by_role[role]["axis_id"]
                        ][axis_role],
                        axis_role=axis_role,
                    )
        if reasons:
            return primary_graph, sorted(set(reasons))

        combined = canonical_clone_v1(primary_graph)
        for role in supplemental_plan["mapped_child_roles"]:
            if role in primary_axis_by_role:
                continue
            source_axis = supplemental_axis_by_role[role]
            axis = {
                **canonical_clone_v1(source_axis),
                "axis_id": f"supplemental:{source_axis['axis_id']}",
                "kind": "MAPPED_SUPPLEMENTAL_COMPONENT",
                "supplemental_source_axis_id": source_axis["axis_id"],
            }
            combined["component_axis"].append(axis)
            combined["component_cells"][axis["axis_id"]] = canonical_clone_v1(
                supplemental_graph["component_cells"][source_axis["axis_id"]]
            )
        combined["alignment_receipts"].append(
            {
                **canonical_clone_v1(supplemental_plan["receipt"]),
                "primary_equations": primary_equations,
                "reconciliation": reconciliation,
                "supplemental_equations": supplemental_equations,
            }
        )
        return combined, []
    reasons = []
    orientations = {item["orientation"] for item in classifications}
    if len(orientations) != 1 or None in orientations:
        return {}, ["MATRIX_FRAGMENT_ORIENTATIONS_DIFFER"]
    orientation = next(iter(orientations))
    continuation_plan = _component_row_continuation_plan_v1(
        tables=tables,
        classifications=classifications,
        compiled_specs=compiled_specs,
    )
    projections = [_component_projection(item["component_axis"]) for item in classifications]
    if continuation_plan is None and any(
        not same_typed_json_v1(projections[0], item) for item in projections[1:]
    ):
        return {}, ["CONTINUATION_COMPONENT_AXES_DIFFER"]
    component_axis = canonical_clone_v1(
        continuation_plan["component_axis"]
        if continuation_plan is not None
        else classifications[0]["component_axis"]
    )
    movement_axis = []
    component_cells: dict[str, dict[str, dict[str, Any]]] = {
        item["axis_id"]: {} for item in component_axis
    }
    alignment_receipts = (
        [canonical_clone_v1(continuation_plan["receipt"])]
        if continuation_plan is not None
        else []
    )
    period_block_receipt = None
    if orientation == "COMPONENT_ROWS":
        if len(tables) != 1 and continuation_plan is None:
            return {}, ["COMPONENT_ROW_ORIENTATION_CANNOT_SPAN_MULTIPLE_FRAGMENTS"]
        movement_fragment_ordinal = (
            continuation_plan["movement_fragment_ordinal"]
            if continuation_plan is not None
            else 1
        )
        table = tables[movement_fragment_ordinal - 1]
        columns = table["columns"]
        raw_movement = [
            _movement_surface_record(
                members=_header_members(column),
                axis_id=f"c{ordinal}",
                axis_ordinal=ordinal,
                source_ref={
                    **canonical_clone_v1(regions[movement_fragment_ordinal - 1]),
                    "column_id": f"c{ordinal}",
                },
                compiled_specs=compiled_specs,
            )
            for ordinal, column in enumerate(columns, start=1)
            # A component-row table may retain a visible enumeration/stub
            # column (for example ``A`` with row numbers 1..13).  It is not a
            # movement lane and must not make the four MONEY columns look
            # unclassified.  The original column remains source-visible in
            # the sealed table; only the arithmetic movement projection is
            # restricted to declared MONEY columns.
            if column.get("value_kind") == "MONEY"
        ]
        for declaration in compiled_specs["movement_decomposition_equations"]:
            result_role = declaration["result_role"]
            term_roles = set(declaration["term_multipliers"])
            ambiguous_by_term = {
                term_role: [
                    item
                    for item in raw_movement
                    if set(item["explicit_roles"]) == {result_role, term_role}
                ]
                for term_role in term_roles
            }
            independent_results = [
                item for item in raw_movement if item["explicit_roles"] == [result_role]
            ]
            complete = len(independent_results) == 1 and all(
                len(items) == 1 for items in ambiguous_by_term.values()
            )
            for term_role, items in ambiguous_by_term.items():
                for item in items:
                    item["explicit_roles"] = [term_role] if complete else [result_role]
        for item in raw_movement:
            if len(item["explicit_roles"]) > 1:
                item["reasons"].append("MOVEMENT_AXIS_SURFACE_MATCHES_MULTIPLE_ROLES")
        reasons.extend(reason for item in raw_movement for reason in item["reasons"])
        by_role: dict[str, list[dict[str, Any]]] = {
            role: [] for role in compiled_specs["movement_roles"]
        }
        for item in raw_movement:
            if len(item["explicit_roles"]) == 1:
                by_role[item["explicit_roles"][0]].append(item)
        dated_balances = [
            item
            for item in raw_movement
            if len(item["dates"]) == 1 and (item["balance_marker"] or not item["explicit_roles"])
        ]
        distinct_dates = sorted({item["dates"][0] for item in dated_balances})
        if len(distinct_dates) == 2:
            opening_candidates = [
                item
                for item in dated_balances
                if item["dates"] == [distinct_dates[0]] and not item["explicit_roles"]
            ]
            if not by_role["OPENING"] and len(opening_candidates) == 1:
                by_role["OPENING"].append(opening_candidates[0])
            closing_candidates = [
                item
                for item in dated_balances
                if item["dates"] == [distinct_dates[1]]
                and not item["explicit_roles"]
                and any(
                    _matches(member, alias)
                    for member in _semantic_component_members(
                        item["members_exact"], compiled_specs=compiled_specs
                    )
                    for alias in compiled_specs["total_aliases"]
                )
            ]
            if not by_role["CLOSING"] and len(closing_candidates) == 1:
                by_role["CLOSING"].append(closing_candidates[0])
        if not by_role["OPENING"] and len(dated_balances) == 2:
            by_role["OPENING"].append(dated_balances[0])
        if not by_role["CLOSING"] and len(dated_balances) == 2:
            by_role["CLOSING"].append(dated_balances[-1])
        if any(len(by_role[role]) != 1 for role in _MAPPED_MOVEMENT_ROLES):
            reasons.append("EXACT_OPENING_INCREASE_DECREASE_CLOSING_COLUMN_AXIS_REQUIRED")
        else:
            if any(
                len(by_role[role]) > 1
                for role in compiled_specs["movement_roles"]
                if role not in _MAPPED_MOVEMENT_ROLES
            ):
                reasons.append("DUPLICATE_SUPPLEMENTAL_MOVEMENT_COLUMN_ROLE")
            selected_by_role = {
                role: items[0] for role, items in by_role.items() if len(items) == 1
            }
            movement_axis = sorted(selected_by_role.values(), key=lambda item: item["axis_ordinal"])
            if len(movement_axis) != len(raw_movement):
                reasons.append("UNCLASSIFIED_OR_DUPLICATE_MOVEMENT_COLUMN_PRESENT")
            primary_ordinals = [
                selected_by_role[role]["axis_ordinal"] for role in _MAPPED_MOVEMENT_ROLES
            ]
            if primary_ordinals != sorted(primary_ordinals):
                reasons.append("MOVEMENT_COLUMN_AXIS_ORDER_DRIFTED")
            role_by_identity = {id(item): role for role, item in selected_by_role.items()}
            for item in movement_axis:
                role = role_by_identity[id(item)]
                item["axis_role"] = role
        for component in component_axis:
            source_fragment_ordinal = component.get("source_fragment_ordinal", 1)
            source_row_ordinal = component.get("source_row_ordinal", component["axis_ordinal"])
            source_table = tables[source_fragment_ordinal - 1]
            row = source_table["rows"][source_row_ordinal - 1]
            source_region = regions[source_fragment_ordinal - 1]
            for movement in movement_axis:
                column_index = movement["axis_ordinal"] - 1
                cell, reason = _parsed_cell(
                    value=row["values_exact"][column_index],
                    region=source_region,
                    row_id=f"r{source_row_ordinal}",
                    column_id=movement["axis_id"],
                )
                if reason:
                    reasons.append(reason)
                elif cell is not None:
                    component_cells[component["axis_id"]][movement["axis_role"]] = cell
    else:
        raw_rows = []
        for fragment_ordinal, (region, table) in enumerate(
            zip(regions, tables, strict=True), start=1
        ):
            for row_ordinal, row in enumerate(table["rows"], start=1):
                axis_id = f"f{fragment_ordinal}:r{row_ordinal}"
                raw_rows.append(
                    {
                        **_movement_surface_record(
                            members=[row.get("label_exact")]
                            if type(row.get("label_exact")) is str
                            else [],
                            axis_id=axis_id,
                            axis_ordinal=len(raw_rows) + 1,
                            source_ref={
                                **canonical_clone_v1(region),
                                "row_id": f"r{row_ordinal}",
                            },
                            compiled_specs=compiled_specs,
                        ),
                        "fragment_ordinal": fragment_ordinal,
                        "row": row,
                        "row_id": f"r{row_ordinal}",
                    }
                )
        reasons.extend(reason for item in raw_rows for reason in item["reasons"])
        balances = [
            item
            for item in raw_rows
            if item["balance_marker"]
            and (item["dates"] or set(item["explicit_roles"]) & {"OPENING", "CLOSING"})
        ]
        if len(balances) < 2:
            reasons.append("AT_LEAST_TWO_ORDERED_BALANCE_ROWS_REQUIRED")
        else:
            blocks = []
            for opening, closing in zip(balances, balances[1:], strict=False):
                detail_count = closing["axis_ordinal"] - opening["axis_ordinal"] - 1
                explicit_pair = (
                    "OPENING" in opening["explicit_roles"]
                    and "CLOSING" in closing["explicit_roles"]
                )
                if (
                    detail_count < 0
                    or (detail_count == 0 and not explicit_pair)
                    or "CLOSING" in opening["explicit_roles"]
                    or "OPENING" in closing["explicit_roles"]
                ):
                    continue
                start = date.fromisoformat(opening["dates"][0]) if opening["dates"] else None
                end = date.fromisoformat(closing["dates"][0]) if closing["dates"] else None
                if (start is None) != (end is None):
                    continue
                if start is not None and (not start < end or (end - start).days > 366):
                    continue
                blocks.append(
                    {
                        "closing": closing,
                        "closing_date": end.isoformat() if end is not None else None,
                        "detail_row_count": detail_count,
                        "opening": opening,
                        "opening_date": start.isoformat() if start is not None else None,
                    }
                )
            selected_block = None
            if len(blocks) == 1:
                selected_block = blocks[0]
                selection_rule = "ONLY_COMPLETE_ORDERED_BALANCE_BLOCK"
            elif len(blocks) > 1 and all(item["closing_date"] is not None for item in blocks):
                latest = max(item["closing_date"] for item in blocks)
                latest_blocks = [item for item in blocks if item["closing_date"] == latest]
                if len(latest_blocks) == 1:
                    selected_block = latest_blocks[0]
                    selection_rule = "UNIQUE_LATEST_SOURCE_DATED_COMPLETE_BALANCE_BLOCK"
            elif len(blocks) > 1:
                # Comparative annual disclosures can print two complete but
                # undated relative blocks.  ``năm nay``/``kỳ này`` is explicit
                # current-period source semantics; it can select one block
                # without manufacturing an endpoint date.  A tie or a block
                # with the marker on only one boundary remains unresolved.
                def is_current_relative_boundary(item: Mapping[str, Any]) -> bool:
                    folded = " ".join(
                        _normalized(member) for member in item["members_exact"]
                    )
                    return bool(re.search(r"\b(?:nam nay|ky nay)\b", folded))

                current_blocks = [
                    item
                    for item in blocks
                    if is_current_relative_boundary(item["opening"])
                    and is_current_relative_boundary(item["closing"])
                ]
                if len(current_blocks) == 1:
                    selected_block = current_blocks[0]
                    selection_rule = "UNIQUE_EXPLICIT_CURRENT_RELATIVE_BALANCE_BLOCK"
            if selected_block is None:
                reasons.append("CURRENT_MOVEMENT_BLOCK_PERIOD_NOT_UNIQUE")
            else:
                opening = selected_block["opening"]
                closing = selected_block["closing"]
                selected = raw_rows[opening["axis_ordinal"] - 1 : closing["axis_ordinal"]]
                period_block_receipt = {
                    "candidate_blocks": [
                        {
                            "closing_axis_id": item["closing"]["axis_id"],
                            "closing_date": item["closing_date"],
                            "detail_row_count": item["detail_row_count"],
                            "opening_axis_id": item["opening"]["axis_id"],
                            "opening_date": item["opening_date"],
                        }
                        for item in blocks
                    ],
                    "rule": selection_rule,
                    "selected_closing_axis_id": closing["axis_id"],
                    "selected_opening_axis_id": opening["axis_id"],
                }
            if selected_block is None:
                selected = []
            selected, parent_child_receipts = _collapse_exact_parent_movement_rows_v1(selected)
            alignment_receipts.extend(parent_child_receipts)
            deduplicated = []
            for item in selected:
                same_label_duplicate = next(
                    (
                        prior
                        for prior in deduplicated[1:]
                        if item is not selected[-1]
                        and len(item["explicit_roles"]) == 1
                        and item["explicit_roles"] in (["INCREASE"], ["DECREASE"])
                        and item["explicit_roles"] == prior["explicit_roles"]
                        and _normalized(item["row"].get("label_exact"))
                        == _normalized(prior["row"].get("label_exact"))
                        and same_typed_json_v1(
                            item["row"].get("values_exact"),
                            prior["row"].get("values_exact"),
                        )
                    ),
                    None,
                )
                same_label_observed_subset_duplicate = None
                if (
                    same_label_duplicate is None
                    and compiled_specs["directional_duplicate_control_mode"]
                    == "EXACT_ADJACENT_DIRECTIONAL_CHILD_CONTROL"
                    and len(deduplicated) > 1
                    and item is not selected[-1]
                ):
                    prior = deduplicated[-1]
                    prior_values = prior["row"].get("values_exact")
                    current_values = item["row"].get("values_exact")

                    def observed_axis(values: Any) -> dict[int, int] | None:
                        if type(values) is not list:
                            return None
                        result = {}
                        for value_ordinal, value in enumerate(values):
                            try:
                                parsed = _money(value)
                            except ValueError:
                                return None
                            if parsed is None:
                                continue
                            coefficient = parsed.get("coefficient")
                            if coefficient is None and parsed.get("state") == "BLANK_SOURCE_CELL":
                                continue
                            if type(coefficient) is not int:
                                return None
                            result[value_ordinal] = coefficient
                        return result

                    prior_observed = observed_axis(prior_values)
                    current_observed = observed_axis(current_values)
                    if (
                        item["axis_ordinal"] == prior["axis_ordinal"] + 1
                        and len(item["explicit_roles"]) == 1
                        and item["explicit_roles"] == prior["explicit_roles"]
                        and _normalized(item["row"].get("label_exact"))
                        == _normalized(prior["row"].get("label_exact"))
                        and prior_observed is not None
                        and current_observed is not None
                        and len(current_observed) >= 2
                        and len(current_values) - 1 in current_observed
                        and set(current_observed) < set(prior_observed)
                        and all(
                            prior_observed[ordinal] == coefficient
                            for ordinal, coefficient in current_observed.items()
                        )
                    ):
                        same_label_observed_subset_duplicate = prior
                directional_child_duplicate = None
                if (
                    same_label_duplicate is None
                    and compiled_specs["directional_duplicate_control_mode"]
                    == "EXACT_ADJACENT_DIRECTIONAL_CHILD_CONTROL"
                    and len(deduplicated) > 1
                    and item is not selected[-1]
                ):
                    prior = deduplicated[-1]
                    prior_role = (
                        prior["explicit_roles"][0]
                        if len(prior["explicit_roles"]) == 1
                        and prior["explicit_roles"][0] in {"INCREASE", "DECREASE"}
                        else None
                    )
                    subordinate_aliases = compiled_specs[
                        "directional_duplicate_control_aliases_by_role"
                    ].get(prior_role, [])
                    if (
                        prior_role is not None
                        and item["axis_ordinal"] == prior["axis_ordinal"] + 1
                        and any(
                            _matches(item["row"].get("label_exact"), alias)
                            for alias in subordinate_aliases
                        )
                        and same_typed_json_v1(
                            item["row"].get("values_exact"),
                            prior["row"].get("values_exact"),
                        )
                    ):
                        directional_child_duplicate = prior
                duplicate = (
                    same_label_duplicate
                    or same_label_observed_subset_duplicate
                    or directional_child_duplicate
                )
                if duplicate is None:
                    deduplicated.append(item)
                    continue
                alignment_receipts.append(
                    {
                        "axis_role": duplicate["explicit_roles"][0],
                        "corroborating_source_ref": canonical_clone_v1(item["source_ref"]),
                        "retained_source_ref": canonical_clone_v1(duplicate["source_ref"]),
                        "rule": (
                            "EXACT_ADJACENT_DECLARED_DIRECTIONAL_CHILD_ROW_IS_"
                            "CORROBORATING_CONTROL_NOT_SECOND_ADDITIVE_TERM"
                            if directional_child_duplicate is not None
                            else "EXACT_OBSERVED_SUBSET_SAME_LABEL_ADJACENT_ROW_IS_"
                            "CORROBORATING_CONTROL_BLANKS_REMAIN_UNOBSERVED"
                            if same_label_observed_subset_duplicate is not None
                            else "EXACT_DUPLICATE_DECLARED_MOVEMENT_ROW_IS_"
                            "CORROBORATING_CONTROL_NOT_SECOND_ADDITIVE_TERM"
                        ),
                    }
                )
            selected = deduplicated
            explicit_middle_roles: set[str] = set()
            for ordinal, item in enumerate(selected):
                if ordinal == 0:
                    item["axis_role"] = "OPENING"
                elif ordinal == len(selected) - 1:
                    item["axis_role"] = "CLOSING"
                elif len(item["explicit_roles"]) == 1 and item["explicit_roles"][0] in {
                    "INCREASE",
                    "DECREASE",
                }:
                    explicit_role = item["explicit_roles"][0]
                    if explicit_role in explicit_middle_roles:
                        reasons.append("DUPLICATE_EXPLICIT_MOVEMENT_TOTAL_ROLE")
                    explicit_middle_roles.add(explicit_role)
                    item["axis_role"] = explicit_role
                else:
                    item["axis_role"] = f"MOVEMENT_{ordinal:04d}"
            movement_axis = selected
            for component in component_axis:
                column_index = component["axis_ordinal"] - 1
                for movement in movement_axis:
                    region = regions[movement["fragment_ordinal"] - 1]
                    value = movement["row"]["values_exact"][column_index]
                    mixed_coefficient = _dash_prefixed_numeric_coefficient(value)
                    if (
                        component["kind"] == "GROUP_TOTAL"
                        and mixed_coefficient is not None
                        and column_index + 1 < len(movement["row"]["values_exact"])
                    ):
                        try:
                            following = _money(movement["row"]["values_exact"][column_index + 1])
                        except ValueError:
                            following = None
                        if following is not None and following["coefficient"] == mixed_coefficient:
                            alignment_receipts.append(
                                {
                                    "axis_role": movement["axis_role"],
                                    "component_axis_id": component["axis_id"],
                                    "raw_source_text": value,
                                    "rule": (
                                        "GROUP_TOTAL_DASH_WITH_DUPLICATED_FOLLOWING_"
                                        "LEAF_VALUE_CANONICALIZED_TO_DASH"
                                    ),
                                }
                            )
                            value = "-"
                    cell, reason = _parsed_cell(
                        value=value,
                        region=region,
                        row_id=movement["row_id"],
                        column_id=component["axis_id"],
                    )
                    if reason:
                        reasons.append(reason)
                    elif cell is not None:
                        component_cells[component["axis_id"]][movement["axis_role"]] = cell
    return (
        {
            "component_axis": component_axis,
            "component_cells": component_cells,
            "alignment_receipts": alignment_receipts,
            "movement_axis": [
                {key: canonical_clone_v1(value) for key, value in item.items() if key != "row"}
                for item in movement_axis
            ],
            "movement_decomposition_equations": canonical_clone_v1(
                compiled_specs["movement_decomposition_equations"]
            ),
            "orientation": orientation,
            "period_block_receipt": period_block_receipt,
            "supplemental_rollforward_additive_roles": canonical_clone_v1(
                compiled_specs["supplemental_rollforward_additive_roles"]
            ),
        },
        sorted(set(reasons)),
    )


def _starts_with(value: Sequence[str], prefix: Sequence[str]) -> bool:
    return len(value) > len(prefix) and list(value[: len(prefix)]) == list(prefix)


def _equation_terms_for_total(
    *, total: Mapping[str, Any], component_axis: Sequence[Mapping[str, Any]]
) -> list[Mapping[str, Any]]:
    leaves = [
        item
        for item in component_axis
        if item["kind"] in {"MAPPED_COMPONENT", "SOURCE_ONLY_COMPONENT"}
    ]
    groups = [
        item
        for item in component_axis
        if item["kind"] in {"GROUP_TOTAL", "MAPPED_COMPONENT_GROUP_TOTAL"}
    ]
    if total["kind"] in {"GROUP_TOTAL", "MAPPED_COMPONENT_GROUP_TOTAL"}:
        return [
            item for item in leaves if _starts_with(item["semantic_path"], total["group_prefix"])
        ]
    grouped_prefixes = [item["group_prefix"] for item in groups]
    return [
        *groups,
        *[
            item
            for item in leaves
            if not any(_starts_with(item["semantic_path"], prefix) for prefix in grouped_prefixes)
        ],
    ]


def _cell_term(cell: Mapping[str, Any], *, multiplier: int = 1) -> dict[str, Any]:
    return {
        "cell_ref": canonical_clone_v1(cell["cell_ref"]),
        "coefficient": cell["coefficient"],
        "multiplier": multiplier,
        "state": cell["state"],
    }


def _additive_equation_outcome_v1(
    *,
    result: Mapping[str, Any],
    terms: Sequence[tuple[Mapping[str, Any], int]],
) -> tuple[int | None, str]:
    """Evaluate only source-observed lanes; a blank is unknown, never zero."""

    result_coefficient = observed_source_coefficient_v1(result)
    term_coefficients = [observed_source_coefficient_v1(cell) for cell, _ in terms]
    if result_coefficient is None or any(value is None for value in term_coefficients):
        return None, "INCOMPLETE_BLANK_SOURCE_CELL"
    computed = sum(
        coefficient * multiplier
        for coefficient, (_cell, multiplier) in zip(term_coefficients, terms, strict=True)
        if coefficient is not None
    )
    return computed, "EXACT" if computed == result_coefficient else "MISMATCH"


def _build_equations(graph: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[str], int]:
    if graph.get("signed_branch_mode") is True:
        return canonical_clone_v1(graph["equations"]), [], 1
    axis = graph["component_axis"]
    arithmetic_axis = [
        item for item in axis if item["kind"] != "MAPPED_SUPPLEMENTAL_COMPONENT"
    ]
    cells = graph["component_cells"]
    movement = graph["movement_axis"]
    totals = [
        item
        for item in arithmetic_axis
        if item["kind"] in {"GROUP_TOTAL", "GRAND_TOTAL", "MAPPED_COMPONENT_GROUP_TOTAL"}
    ]
    reasons = []
    equations = []
    for move in movement:
        move_role = move["axis_role"]
        for total in totals:
            terms = _equation_terms_for_total(total=total, component_axis=arithmetic_axis)
            result = cells[total["axis_id"]].get(move_role)
            term_cells = [cells[item["axis_id"]].get(move_role) for item in terms]
            if result is None or not terms or any(item is None for item in term_cells):
                reasons.append("HORIZONTAL_TOTAL_EQUATION_CELL_AXIS_INCOMPLETE")
                continue
            computed, status = _additive_equation_outcome_v1(
                result=result,
                terms=[(item, 1) for item in term_cells if item is not None],
            )
            equation = {
                "axis_role": move_role,
                "computed_value": computed,
                "equation_kind": (
                    "VISIBLE_GROUP_HORIZONTAL_TOTAL"
                    if total["kind"] in {"GROUP_TOTAL", "MAPPED_COMPONENT_GROUP_TOTAL"}
                    else "VISIBLE_GRAND_HORIZONTAL_TOTAL"
                ),
                "result": _cell_term(result),
                "status": status,
                "terms": [_cell_term(item) for item in term_cells if item is not None],
                "total_axis_id": total["axis_id"],
            }
            equations.append(equation)
            if status == "MISMATCH":
                reasons.append("HORIZONTAL_VISIBLE_TOTAL_MISMATCH")
    disclosure_headers = [
        item for item in arithmetic_axis if item["kind"] == "DISCLOSURE_GROUP_HEADER"
    ]
    for header in disclosure_headers:
        prior = [
            item
            for item in arithmetic_axis
            if item["axis_ordinal"] < header["axis_ordinal"]
            and item["kind"] in {"MAPPED_COMPONENT", "MAPPED_COMPONENT_GROUP_TOTAL"}
        ]
        terms = [
            item
            for item in arithmetic_axis
            if item["kind"] == "DISCLOSURE_COMPONENT"
            and _starts_with(item["semantic_path"], header["group_prefix"])
        ]
        if not prior or not terms:
            reasons.append("DISCLOSURE_GROUP_COMPONENT_AXIS_INCOMPLETE")
            continue
        result_axis = prior[-1]
        for move in movement:
            role = move["axis_role"]
            result = cells[result_axis["axis_id"]].get(role)
            term_cells = [cells[item["axis_id"]].get(role) for item in terms]
            if result is None or any(item is None for item in term_cells):
                reasons.append("DISCLOSURE_GROUP_CELL_AXIS_INCOMPLETE")
                continue
            computed, status = _additive_equation_outcome_v1(
                result=result,
                terms=[(item, 1) for item in term_cells if item is not None],
            )
            equations.append(
                {
                    "axis_role": role,
                    "computed_value": computed,
                    "disclosure_group_axis_id": header["axis_id"],
                    "equation_kind": "VISIBLE_DISCLOSURE_CHILDREN_EQUAL_PRIOR_MAPPED_COMPONENT",
                    "result": _cell_term(result),
                    "status": status,
                    "terms": [_cell_term(item) for item in term_cells if item is not None],
                    "total_axis_id": result_axis["axis_id"],
                }
            )
            if status == "MISMATCH":
                reasons.append("DISCLOSURE_GROUP_VISIBLE_TOTAL_MISMATCH")
    present_movement_roles = {item["axis_role"] for item in movement}
    for declaration in graph.get("movement_decomposition_equations", []):
        declared_roles = {
            declaration["result_role"],
            *declaration["term_multipliers"],
        }
        # A decomposition may refine a primary movement (for example the
        # visible closing balance into payable and receivable columns).  The
        # primary result by itself must not activate that optional layout: the
        # ordinary four-column matrix also contains CLOSING.  Activate only
        # when at least one declared supplemental term is source-visible, then
        # require the complete declared frontier.
        supplemental_terms = declared_roles - set(_MAPPED_MOVEMENT_ROLES)
        if not (supplemental_terms & present_movement_roles):
            continue
        present_declared = declared_roles & present_movement_roles
        if present_declared != declared_roles:
            reasons.append("SUPPLEMENTAL_MOVEMENT_DECOMPOSITION_AXIS_INCOMPLETE")
            continue
        for item in arithmetic_axis:
            result = cells[item["axis_id"]][declaration["result_role"]]
            term_cells = [
                (
                    cells[item["axis_id"]][role],
                    multiplier,
                )
                for role, multiplier in declaration["term_multipliers"].items()
            ]
            computed, status = _additive_equation_outcome_v1(
                result=result,
                terms=term_cells,
            )
            equations.append(
                {
                    "component_axis_id": item["axis_id"],
                    "computed_value": computed,
                    "equation_kind": "DECLARED_SUPPLEMENTAL_MOVEMENT_DECOMPOSITION",
                    "result": _cell_term(result),
                    "status": status,
                    "terms": [
                        _cell_term(cell, multiplier=multiplier) for cell, multiplier in term_cells
                    ],
                }
            )
            if status == "MISMATCH":
                reasons.append("SUPPLEMENTAL_MOVEMENT_DECOMPOSITION_MISMATCH")
    sign_multiplier = 1
    if graph["orientation"] == "COMPONENT_ROWS":
        additive_roles = [
            role
            for role in graph.get("supplemental_rollforward_additive_roles", [])
            if role in present_movement_roles
        ]
        complete_axes = []
        for item in arithmetic_axis:
            component = cells[item["axis_id"]]
            required_roles = ["OPENING", "INCREASE", *additive_roles, "DECREASE", "CLOSING"]
            if all(
                role in component
                and observed_source_coefficient_v1(component[role]) is not None
                for role in required_roles
            ):
                complete_axes.append(item)
        exact_modes = []
        for candidate in (1, -1):
            if complete_axes and all(
                observed_source_coefficient_v1(cells[item["axis_id"]]["OPENING"])
                + observed_source_coefficient_v1(cells[item["axis_id"]]["INCREASE"])
                + sum(
                    observed_source_coefficient_v1(cells[item["axis_id"]][role])
                    for role in additive_roles
                )
                + candidate
                * observed_source_coefficient_v1(cells[item["axis_id"]]["DECREASE"])
                == observed_source_coefficient_v1(cells[item["axis_id"]]["CLOSING"])
                for item in complete_axes
            ):
                exact_modes.append(candidate)
        if complete_axes:
            if not exact_modes:
                reasons.append("VERTICAL_EXPLICIT_MOVEMENT_SIGN_MODE_UNRESOLVED")
            else:
                sign_multiplier = exact_modes[0] if len(exact_modes) == 1 else -1
        else:
            # The source label itself declares a decrease.  With no complete
            # arithmetic lane available it remains a negative presentation
            # multiplier, while every equation is explicitly incomplete.
            sign_multiplier = -1
        for item in arithmetic_axis:
            required = ["OPENING", "INCREASE", "DECREASE", "CLOSING"]
            if any(role not in cells[item["axis_id"]] for role in required):
                reasons.append("VERTICAL_EXPLICIT_MOVEMENT_CELL_AXIS_INCOMPLETE")
                continue
            opening = cells[item["axis_id"]]["OPENING"]
            increase = cells[item["axis_id"]]["INCREASE"]
            decrease = cells[item["axis_id"]]["DECREASE"]
            closing = cells[item["axis_id"]]["CLOSING"]
            computed, status = _additive_equation_outcome_v1(
                result=closing,
                terms=[
                    (opening, 1),
                    (increase, 1),
                    *[(cells[item["axis_id"]][role], 1) for role in additive_roles],
                    (decrease, sign_multiplier),
                ],
            )
            equations.append(
                {
                    "component_axis_id": item["axis_id"],
                    "computed_value": computed,
                    "decrease_multiplier": sign_multiplier,
                    "equation_kind": "VERTICAL_EXPLICIT_MOVEMENT_ROLLFORWARD",
                    "result": _cell_term(closing),
                    "status": status,
                    "terms": [
                        _cell_term(opening),
                        _cell_term(increase),
                        *[_cell_term(cells[item["axis_id"]][role]) for role in additive_roles],
                        _cell_term(decrease, multiplier=sign_multiplier),
                    ],
                }
            )
            if status == "MISMATCH":
                reasons.append("VERTICAL_COMPONENT_ROLLFORWARD_MISMATCH")
    else:
        roles = [item["axis_role"] for item in movement]
        if len(roles) < 2 or roles[0] != "OPENING" or roles[-1] != "CLOSING":
            reasons.append("VERTICAL_DETAILED_MOVEMENT_AXIS_INVALID")
        else:
            for item in arithmetic_axis:
                component = cells[item["axis_id"]]
                if any(role not in component for role in roles):
                    reasons.append("VERTICAL_DETAILED_MOVEMENT_CELL_AXIS_INCOMPLETE")
                    continue
                opening = component["OPENING"]
                closing = component["CLOSING"]
                detail = [component[role] for role in roles[1:-1]]
                computed, status = _additive_equation_outcome_v1(
                    result=closing,
                    terms=[(opening, 1), *[(cell, 1) for cell in detail]],
                )
                equations.append(
                    {
                        "component_axis_id": item["axis_id"],
                        "computed_value": computed,
                        "equation_kind": "VERTICAL_DETAILED_MOVEMENT_ROLLFORWARD",
                        "result": _cell_term(closing),
                        "status": status,
                        "terms": [_cell_term(opening), *[_cell_term(cell) for cell in detail]],
                    }
                )
                if status == "MISMATCH":
                    reasons.append("VERTICAL_COMPONENT_ROLLFORWARD_MISMATCH")
    return equations, sorted(set(reasons)), sign_multiplier


def _component_column_row_alignment_candidates(
    *,
    graph: Mapping[str, Any],
    axis_role: str,
) -> list[dict[str, Any]]:
    axis = graph["component_axis"]
    source_cells = [graph["component_cells"][item["axis_id"]][axis_role] for item in axis]
    # A blank source slot is an unknown observation.  It cannot be used as a
    # zero placeholder by the digit-placement solver.
    if any(observed_source_coefficient_v1(cell) is None for cell in source_cells):
        return []
    tokens = [
        (ordinal, cell)
        for ordinal, cell in enumerate(source_cells)
        if observed_source_coefficient_v1(cell) != 0
    ]
    totals = [
        item
        for item in axis
        if item["kind"] in {"GROUP_TOTAL", "GRAND_TOTAL", "MAPPED_COMPONENT_GROUP_TOTAL"}
    ]
    candidates: dict[tuple[int, ...], dict[str, Any]] = {}
    # The matrix widths in the sealed policy are small (the production maximum
    # is eleven).  Enumerating monotone placements preserves Gemini's token
    # order and never invents or changes a digit.
    from itertools import combinations

    for positions in combinations(range(len(axis)), len(tokens)):
        vector = [0] * len(axis)
        placed: dict[int, Mapping[str, Any]] = {}
        for (_source_ordinal, cell), target_ordinal in zip(tokens, positions, strict=True):
            vector[target_ordinal] = cell["coefficient"]
            placed[target_ordinal] = cell
        if any(
            sum(
                vector[item["axis_ordinal"] - 1]
                for item in _equation_terms_for_total(total=total, component_axis=axis)
            )
            != vector[total["axis_ordinal"] - 1]
            for total in totals
        ):
            continue
        score = sum(
            abs(source_ordinal - target_ordinal)
            for (source_ordinal, _cell), target_ordinal in zip(tokens, positions, strict=True)
        )
        key = tuple(vector)
        prior = candidates.get(key)
        if prior is not None and prior["displacement_score"] <= score:
            continue
        effective_cells = []
        assignments = []
        for target_ordinal, component in enumerate(axis):
            if target_ordinal in placed:
                cell = canonical_clone_v1(placed[target_ordinal])
                source_cell_ref = canonical_clone_v1(cell["cell_ref"])
                source_column_id = source_cell_ref["column_id"]
                effective_cell_ref = canonical_clone_v1(source_cell_ref)
                effective_cell_ref["column_id"] = component["axis_id"]
                cell["cell_ref"] = effective_cell_ref
                cell["source_cell_ref"] = source_cell_ref
                if source_column_id != component["axis_id"]:
                    cell["source_state"] = cell["state"]
                    cell["state"] = "ROW_ALIGNMENT_SOURCE_DIGIT_REASSIGNED_GRAPH_EXACT"
                assignments.append(
                    {
                        "coefficient": cell["coefficient"],
                        "effective_cell_ref": effective_cell_ref,
                        "effective_component_axis_id": component["axis_id"],
                        "source_cell_ref": source_cell_ref,
                        "source_column_id": source_column_id,
                        "source_text": cell["source_text"],
                    }
                )
            else:
                raw = source_cells[target_ordinal]
                cell = canonical_clone_v1(raw)
                if raw["coefficient"] != 0:
                    # The non-zero source slot is consumed by one assignment
                    # elsewhere.  Keep the effective zero explicitly derived
                    # instead of claiming the same raw cell as both a digit
                    # and a blank.
                    cell = {
                        "cell_ref": canonical_clone_v1(raw["cell_ref"]),
                        "coefficient": 0,
                        "source_cell_ref": None,
                        "source_text": None,
                        "state": "ROW_ALIGNMENT_ZERO_EQUATION_EXACT",
                    }
                else:
                    cell["source_cell_ref"] = canonical_clone_v1(raw["cell_ref"])
            effective_cells.append(cell)
        candidates[key] = {
            "assignments": assignments,
            "cells": effective_cells,
            "displacement_score": score,
            "vector": key,
        }
    return sorted(
        candidates.values(),
        key=lambda item: (item["displacement_score"], item["vector"]),
    )


def _resolve_component_column_row_alignment_v1(
    graph: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    if graph.get("orientation") != "COMPONENT_COLUMNS":
        return None, ["ROW_ALIGNMENT_ONLY_APPLIES_TO_COMPONENT_COLUMNS"]
    movement = graph["movement_axis"]
    if len(movement) < 3:
        return None, ["ROW_ALIGNMENT_REQUIRES_DETAILED_MOVEMENT_ROWS"]
    axis = graph["component_axis"]
    opening_role = movement[0]["axis_role"]
    closing_role = movement[-1]["axis_role"]
    detail_roles = [item["axis_role"] for item in movement[1:-1]]
    if any(
        observed_source_coefficient_v1(
            graph["component_cells"][item["axis_id"]][axis_role]
        )
        is None
        for item in axis
        for axis_role in (opening_role, closing_role)
    ):
        return None, ["ROW_ALIGNMENT_REQUIRES_OBSERVED_BOUNDARY_AXIS"]
    domains = [
        _component_column_row_alignment_candidates(graph=graph, axis_role=axis_role)
        for axis_role in detail_roles
    ]
    if any(not domain for domain in domains):
        return None, ["ROW_ALIGNMENT_HAS_NO_HORIZONTAL_EXACT_PLACEMENT"]
    target = tuple(
        graph["component_cells"][item["axis_id"]][closing_role]["coefficient"]
        - graph["component_cells"][item["axis_id"]][opening_role]["coefficient"]
        for item in axis
    )
    state_bound = 100_000

    def achievable_sums(excluded: int, component_ordinal: int) -> set[int] | None:
        sums = {0}
        for domain_ordinal, domain in enumerate(domains):
            if domain_ordinal == excluded:
                continue
            values = {item["vector"][component_ordinal] for item in domain}
            sums = {left + right for left in sums for right in values}
            if len(sums) > state_bound:
                return None
        return sums

    changed = True
    while changed:
        changed = False
        for component_ordinal in range(len(axis)):
            complementary = [
                achievable_sums(domain_ordinal, component_ordinal)
                for domain_ordinal in range(len(domains))
            ]
            if any(values is None for values in complementary):
                return None, ["ROW_ALIGNMENT_SOLVER_STATE_BOUND_EXCEEDED"]
            for domain_ordinal, domain in enumerate(domains):
                remaining = complementary[domain_ordinal]
                assert remaining is not None
                filtered = [
                    item
                    for item in domain
                    if target[component_ordinal] - item["vector"][component_ordinal] in remaining
                ]
                if not filtered:
                    return None, ["ROW_ALIGNMENT_HAS_NO_VERTICAL_EXACT_PLACEMENT"]
                if len(filtered) != len(domain):
                    domains[domain_ordinal] = filtered
                    changed = True
    if any(len(domain) != 1 for domain in domains):
        return None, ["ROW_ALIGNMENT_EXACT_PLACEMENT_IS_NOT_UNIQUE"]
    selected = [domain[0] for domain in domains]
    if any(
        sum(item["vector"][component_ordinal] for item in selected) != target[component_ordinal]
        for component_ordinal in range(len(axis))
    ):
        return None, ["ROW_ALIGNMENT_VERTICAL_EXACT_SUM_DRIFTED"]
    rebuilt = canonical_clone_v1(graph)
    receipts = canonical_clone_v1(rebuilt.get("alignment_receipts", []))
    changed_row_count = 0
    for axis_role, candidate in zip(detail_roles, selected, strict=True):
        raw_vector = tuple(
            graph["component_cells"][item["axis_id"]][axis_role]["coefficient"] for item in axis
        )
        if candidate["vector"] != raw_vector:
            changed_row_count += 1
            receipts.append(
                {
                    "assignments": candidate["assignments"],
                    "axis_role": axis_role,
                    "displacement_score": candidate["displacement_score"],
                    "effective_vector": list(candidate["vector"]),
                    "raw_vector": list(raw_vector),
                    "rule": (
                        "UNIQUE_MONOTONE_DIGIT_PRESERVING_ROW_ALIGNMENT_"
                        "HORIZONTAL_AND_VERTICAL_GRAPH_EXACT"
                    ),
                }
            )
        for component, cell in zip(axis, candidate["cells"], strict=True):
            rebuilt["component_cells"][component["axis_id"]][axis_role] = cell
    if changed_row_count == 0:
        return None, ["ROW_ALIGNMENT_DID_NOT_CHANGE_THE_SOURCE_MATRIX"]
    rebuilt["alignment_receipts"] = receipts
    return rebuilt, []


def _resolve_directional_cumulative_movement_control_v1(
    graph: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], int]:
    """Select an exact cumulative directional row over its adjacent detail.

    Some statements print a direction subtotal immediately followed by a more
    complete directional row.  The latter may repeat the subtotal values and
    add one further component.  It replaces, rather than adds to, the former
    only when the complete matrix becomes uniquely exact.  Blank cells remain
    unobserved throughout.
    """

    if (
        graph.get("orientation") != "COMPONENT_COLUMNS"
        or compiled_specs.get("directional_duplicate_control_mode")
        != "EXACT_ADJACENT_DIRECTIONAL_CHILD_CONTROL"
    ):
        return None, [], 1
    movement = graph.get("movement_axis", [])
    candidates = []
    for movement_ordinal, (prior, current) in enumerate(
        zip(movement, movement[1:], strict=False), start=1
    ):
        prior_role = prior.get("axis_role")
        current_role = current.get("axis_role")
        aliases = compiled_specs["directional_duplicate_control_aliases_by_role"].get(
            prior_role, []
        )
        if (
            prior_role not in {"INCREASE", "DECREASE"}
            or not aliases
            or current_role in _MAPPED_MOVEMENT_ROLES
            or current.get("axis_ordinal") != prior.get("axis_ordinal", 0) + 1
            or not any(
                _matches(member, alias)
                for member in current.get("members_exact", [])
                for alias in aliases
            )
        ):
            continue
        overlap_equal_nonzero = 0
        incompatible_overlap = False
        for component in graph.get("component_axis", []):
            cells = graph.get("component_cells", {}).get(component.get("axis_id"), {})
            prior_cell = cells.get(prior_role)
            current_cell = cells.get(current_role)
            if not isinstance(prior_cell, Mapping) or not isinstance(current_cell, Mapping):
                incompatible_overlap = True
                break
            prior_value = observed_source_coefficient_v1(prior_cell)
            current_value = observed_source_coefficient_v1(current_cell)
            if prior_value is None or current_value is None:
                continue
            if component.get("kind") == "GRAND_TOTAL":
                continue
            if prior_value != current_value and prior_value != 0 and current_value != 0:
                incompatible_overlap = True
                break
            if prior_value == current_value and prior_value != 0:
                overlap_equal_nonzero += 1
        if incompatible_overlap or overlap_equal_nonzero == 0:
            continue
        rebuilt = canonical_clone_v1(graph)
        rebuilt_movement = rebuilt["movement_axis"]
        discarded = rebuilt_movement.pop(movement_ordinal - 1)
        retained = rebuilt_movement[movement_ordinal - 1]
        retained_source_role = retained["axis_role"]
        retained["axis_role"] = prior_role
        for component in rebuilt["component_axis"]:
            cells = rebuilt["component_cells"][component["axis_id"]]
            cells.pop(prior_role)
            cells[prior_role] = cells.pop(retained_source_role)
        receipt = {
            "axis_role": prior_role,
            "discarded_source_ref": canonical_clone_v1(discarded["source_ref"]),
            "retained_source_ref": canonical_clone_v1(retained["source_ref"]),
            "rule": (
                "UNIQUE_EXACT_ADJACENT_DIRECTIONAL_CUMULATIVE_ROW_REPLACES_"
                "ITS_INCLUDED_DETAIL_WITHOUT_BLANK_ZERO_INFERENCE"
            ),
        }
        rebuilt["alignment_receipts"].append(receipt)
        equations, reasons, sign_multiplier = _build_equations(rebuilt)
        grand_total = next(
            (
                item
                for item in rebuilt["component_axis"]
                if item.get("kind") == "GRAND_TOTAL"
            ),
            None,
        )
        exact_vertical = [
            equation
            for equation in equations
            if equation.get("equation_kind") == "VERTICAL_DETAILED_MOVEMENT_ROLLFORWARD"
            and equation.get("status") == "EXACT"
        ]
        grand_is_exact = bool(
            grand_total
            and any(
                equation.get("component_axis_id") == grand_total["axis_id"]
                for equation in exact_vertical
            )
        )
        if not reasons and grand_is_exact and len(exact_vertical) >= 2:
            candidates.append((rebuilt, equations, sign_multiplier))
    if len(candidates) != 1:
        return None, [], 1
    return candidates[0]


def _mapping_value(
    cell: Mapping[str, Any], *, axis_role: str, equation_multiplier: int = 1
) -> dict[str, Any]:
    coefficient = observed_source_coefficient_v1(cell)
    state = "BLANK_SOURCE_CELL" if coefficient is None else cell["state"]
    result = {
        "axis_role": axis_role,
        "cell_ref": canonical_clone_v1(cell["cell_ref"]),
        "coefficient": coefficient,
        "equation_multiplier": equation_multiplier,
        "source_text": None if coefficient is None else cell["source_text"],
        "state": state,
    }
    if cell.get("state") == "SIGNED_BRANCH_NET_SOURCE_CELLS_GRAPH_EXACT":
        result["aggregate_components"] = canonical_clone_v1(cell["aggregate_components"])
    return result


def _aggregate_component_axis_v1(
    *, role: str, items: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    return {
        "axis_id": f"aggregate:{role}",
        "axis_ordinals": [item["axis_ordinal"] for item in items],
        "kind": "AGGREGATED_MAPPED_COMPONENT",
        "member_axes": canonical_clone_v1(list(items)),
        "role": role,
        "rule": "DECLARED_DUPLICATE_ROLE_SOURCE_ROWS_SUM_AFTER_EACH_ROW_GRAPH_EXACT",
    }


def _aggregate_mapping_value_v1(
    cells: Sequence[Mapping[str, Any]], *, axis_role: str, equation_multiplier: int
) -> dict[str, Any]:
    components = [
        _mapping_value(
            cell,
            axis_role=axis_role,
            equation_multiplier=equation_multiplier,
        )
        for cell in cells
    ]
    coefficients = [item["coefficient"] for item in components]
    incomplete = any(coefficient is None for coefficient in coefficients)
    return {
        "aggregate_components": components,
        "axis_role": axis_role,
        "cell_ref": None,
        "coefficient": (
            None
            if incomplete
            else sum(coefficient for coefficient in coefficients if coefficient is not None)
        ),
        "equation_multiplier": equation_multiplier,
        "source_text": None,
        "state": (
            "DERIVED_INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL"
            if incomplete
            else "AGGREGATED_SOURCE_CELLS_GRAPH_EXACT"
        ),
    }


def _build_mappings(
    *, graph: Mapping[str, Any], compiled_specs: Mapping[str, Any], unit: str, sign_multiplier: int
) -> tuple[list[dict[str, Any]], list[str]]:
    result = []
    omitted_all_blank_roles = []

    def append_if_observed(payload: dict[str, Any]) -> None:
        if any(value["coefficient"] is not None for value in payload["values"]):
            payload["item_mapping_id"] = "gjeqmfv1:item:" + canonical_json_sha256_v1(
                {key: value for key, value in payload.items() if key != "item_mapping_id"}
            )
            result.append(payload)
        else:
            omitted_all_blank_roles.append(payload["role"])

    movement_roles = [item["axis_role"] for item in graph["movement_axis"]]
    selected_child_roles = (
        [
            role
            for role in movement_roles
            if role in _MAPPED_MOVEMENT_ROLES
            or role in compiled_specs["mapped_supplemental_movement_roles"]
        ]
        if graph["orientation"] == "COMPONENT_ROWS"
        else [
            "OPENING",
            *[role for role in ("INCREASE", "DECREASE") if role in movement_roles],
            "CLOSING",
        ]
    )
    grand_total = next(item for item in graph["component_axis"] if item["kind"] == "GRAND_TOTAL")
    if (
        compiled_specs["root_mapping_policy"]
        == "SOURCE_VISIBLE_MATRIX_GRAND_TOTAL_VECTOR_WITH_COMPONENT_VECTORS"
    ):
        payload = {
            "component_axis": canonical_clone_v1(grand_total),
            "item_mapping_id": "gjeqmfv1:item:pending",
            "report_norm_id": compiled_specs["family_root_report_norm_id"],
            "role": "FAMILY_TOTAL",
            "row_id": "component:FAMILY_TOTAL",
            "unit": unit,
            "values": [
                _mapping_value(
                    graph["component_cells"][grand_total["axis_id"]][axis_role],
                    axis_role=axis_role,
                    equation_multiplier=sign_multiplier if axis_role == "DECREASE" else 1,
                )
                for axis_role in selected_child_roles
                if axis_role in graph["component_cells"][grand_total["axis_id"]]
            ],
        }
        append_if_observed(payload)
    else:
        for axis_role in selected_child_roles:
            if axis_role not in movement_roles:
                continue
            total_role = _MAPPED_TOTAL_ROLES[axis_role]
            cell = graph["component_cells"][grand_total["axis_id"]][axis_role]
            payload = {
                "item_mapping_id": "gjeqmfv1:item:pending",
                "report_norm_id": compiled_specs["movement_total_report_norm_id_by_role"][
                    total_role
                ],
                "role": total_role,
                "row_id": f"movement:{axis_role}",
                "unit": unit,
                "values": [
                    _mapping_value(
                        cell,
                        axis_role=axis_role,
                        equation_multiplier=sign_multiplier if axis_role == "DECREASE" else 1,
                    )
                ],
            }
            append_if_observed(payload)
    mapped_by_role: dict[str, list[Mapping[str, Any]]] = {}
    for item in graph["component_axis"]:
        if item["kind"] in {
            "MAPPED_COMPONENT",
            "MAPPED_COMPONENT_GROUP_TOTAL",
            "MAPPED_SUPPLEMENTAL_COMPONENT",
        }:
            mapped_by_role.setdefault(item["role"], []).append(item)
    for role, items in mapped_by_role.items():
        if len(items) == 1:
            item = items[0]
            component_axis = canonical_clone_v1(item)
            values = [
                _mapping_value(
                    graph["component_cells"][item["axis_id"]][axis_role],
                    axis_role=axis_role,
                    equation_multiplier=sign_multiplier if axis_role == "DECREASE" else 1,
                )
                for axis_role in selected_child_roles
                if axis_role in graph["component_cells"][item["axis_id"]]
            ]
        else:
            component_axis = _aggregate_component_axis_v1(role=role, items=items)
            values = [
                _aggregate_mapping_value_v1(
                    [graph["component_cells"][item["axis_id"]][axis_role] for item in items],
                    axis_role=axis_role,
                    equation_multiplier=sign_multiplier if axis_role == "DECREASE" else 1,
                )
                for axis_role in selected_child_roles
                if all(axis_role in graph["component_cells"][item["axis_id"]] for item in items)
            ]
        payload = {
            "component_axis": component_axis,
            "item_mapping_id": "gjeqmfv1:item:pending",
            "report_norm_id": compiled_specs["component_report_norm_id_by_role"][role],
            "role": role,
            "row_id": f"component:{role}",
            "unit": unit,
            "values": values,
        }
        append_if_observed(payload)
    return result, sorted(omitted_all_blank_roles)


def _valuation_cell_v1(
    *,
    value: Any,
    region: Mapping[str, Any],
    row_id: str,
    column_id: str,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    source_text = value
    cell_ref = {
        "column_id": column_id,
        "locator": canonical_clone_v1(region),
        "row_id": row_id,
    }
    if value is None or type(value) is str and not value.strip():
        return {
            "cell_ref": cell_ref,
            "coefficient": None,
            "source_text": source_text,
            "state": "BLANK",
        }
    if type(value) is not str:
        return {
            "cell_ref": cell_ref,
            "coefficient": None,
            "source_text": source_text,
            "state": "INVALID_NON_STRING_SOURCE_CELL",
        }
    stripped = value.strip()
    unavailable = compiled_specs["valuation_marker_aliases"]["unavailable_value_aliases"]
    if stripped in unavailable:
        return {
            "cell_ref": cell_ref,
            "coefficient": None,
            "source_text": source_text,
            "state": "SOURCE_EXPLICIT_FAIR_VALUE_UNAVAILABLE",
        }
    compact = "".join(stripped.split())
    if (
        compact
        and any(character in "-–—_" for character in compact)
        and not any(character.isdigit() for character in compact)
    ):
        return {
            "cell_ref": cell_ref,
            "coefficient": 0,
            "source_text": source_text,
            "state": "DASH_ZERO",
        }
    try:
        parsed = _money(value)
    except ValueError:
        parsed = None
    if parsed is not None:
        return {**parsed, "cell_ref": cell_ref, "source_text": source_text}
    numeric_tokens = re.findall(r"\(?-?\d{1,3}(?:[.,]\d{3})+\)?|\(?-?\d+\)?", stripped)
    if len(numeric_tokens) == 1:
        try:
            parsed = _money(numeric_tokens[0])
        except ValueError:
            parsed = None
        if parsed is not None and parsed["state"] == "RAW_SIGNED_INTEGER":
            return {
                **parsed,
                "cell_ref": cell_ref,
                "source_text": source_text,
                "state": "NORMALIZED_SINGLE_NUMERIC_TOKEN_PENDING_GRAPH",
            }
    return {
        "cell_ref": cell_ref,
        "coefficient": None,
        "source_text": source_text,
        "state": "INVALID_SOURCE_CELL",
    }


def _valuation_resolve_row_v1(
    *,
    row: Mapping[str, Any],
    row_axis: Mapping[str, Any],
    column_axis: Sequence[Mapping[str, Any]],
    region: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    cells = [
        _valuation_cell_v1(
            value=value,
            region=region,
            row_id=row_axis["row_id"],
            column_id=f"c{ordinal}",
            compiled_specs=compiled_specs,
        )
        for ordinal, value in enumerate(row["values_exact"], start=1)
    ]
    category_ordinals = [
        int(item["column_id"][1:])
        for item in column_axis
        if item["roles"] == ["BOOK_CLASSIFICATION"]
    ]
    total_ordinal = next(
        int(item["column_id"][1:]) for item in column_axis if item["roles"] == ["BOOK_TOTAL"]
    )
    fair_ordinal = next(
        int(item["column_id"][1:]) for item in column_axis if item["roles"] == ["FAIR_VALUE"]
    )

    def numeric(cell: Mapping[str, Any]) -> bool:
        return type(cell.get("coefficient")) is int and cell.get("state") not in {
            "SOURCE_EXPLICIT_FAIR_VALUE_UNAVAILABLE",
        }

    candidates = []
    fixed_categories = [cells[ordinal - 1] for ordinal in category_ordinals]
    fixed_total = cells[total_ordinal - 1]
    fixed_fair = cells[fair_ordinal - 1]
    fixed_invalid = [
        cell
        for cell in fixed_categories
        if cell["state"]
        not in {
            "BLANK",
            "DASH_ZERO",
            "RAW_SIGNED_INTEGER",
            "NORMALIZED_SINGLE_NUMERIC_TOKEN_PENDING_GRAPH",
        }
    ]
    fair_valid = fixed_fair["state"] in {
        "BLANK",
        "DASH_ZERO",
        "RAW_SIGNED_INTEGER",
        "NORMALIZED_SINGLE_NUMERIC_TOKEN_PENDING_GRAPH",
        "SOURCE_EXPLICIT_FAIR_VALUE_UNAVAILABLE",
    }
    if fixed_total["state"] == "BLANK" and not fixed_invalid:
        known_categories = [cell for cell in fixed_categories if numeric(cell)]
        known_sum = sum(cell["coefficient"] for cell in known_categories)
        if known_categories and known_sum == 0:
            fixed_total = canonical_clone_v1(fixed_total)
            fixed_total["coefficient"] = 0
            fixed_total["state"] = "BLANK_ZERO_AFTER_COMPLETE_CLASSIFICATION_AXIS_EXACT"
    if numeric(fixed_total) and not fixed_invalid and fair_valid:
        known_sum = sum(cell["coefficient"] for cell in fixed_categories if numeric(cell))
        normalized_categories = canonical_clone_v1(fixed_categories)
        if known_sum != fixed_total["coefficient"]:
            adjacent_index = total_ordinal - 2
            adjacent = (
                normalized_categories[adjacent_index]
                if 0 <= adjacent_index < len(normalized_categories)
                else None
            )
            if (
                adjacent is not None
                and numeric(adjacent)
                and adjacent["coefficient"] == fixed_total["coefficient"]
                and known_sum - adjacent["coefficient"] == fixed_total["coefficient"]
            ):
                adjacent["coefficient"] = 0
                adjacent["state"] = (
                    "DUPLICATE_ADJACENT_BOOK_TOTAL_EXTRACTION_SUPPRESSED_ROW_GRAPH_EXACT"
                )
                known_sum = fixed_total["coefficient"]
        if known_sum == fixed_total["coefficient"]:
            for cell in normalized_categories:
                if cell["state"] == "BLANK":
                    cell["coefficient"] = 0
                    cell["state"] = "BLANK_ZERO_AFTER_ROW_EQUATION_EXACT"
            candidates.append(
                {
                    "alignment_mode": "FIXED_DECLARED_AXIS",
                    "classification_cells": normalized_categories,
                    "fair_value_cell": canonical_clone_v1(fixed_fair),
                    "book_total_cell": canonical_clone_v1(fixed_total),
                }
            )
    # Gemini occasionally preserves the visible cells but compacts them to
    # the left.  Resolve that representation only through a unique arithmetic
    # pivot; source order alone is never enough to select a total column.
    last_active = max(
        (ordinal for ordinal, cell in enumerate(cells, start=1) if cell["state"] != "BLANK"),
        default=0,
    )
    packed = [cell for cell in cells[:last_active] if cell["state"] != "BLANK"]
    for pivot in range(2, len(packed) + 1) if not candidates else ():
        classification = packed[: pivot - 1]
        total = packed[pivot - 1]
        tail = packed[pivot:]
        fair_cell = None
        ignored_tail_zero_cells = []
        if tail:
            if tail[-1]["state"] in {
                "RAW_SIGNED_INTEGER",
                "NORMALIZED_SINGLE_NUMERIC_TOKEN_PENDING_GRAPH",
                "SOURCE_EXPLICIT_FAIR_VALUE_UNAVAILABLE",
            }:
                fair_cell = tail[-1]
                filler = tail[:-1]
            else:
                filler = tail
            if not all(numeric(cell) and cell["coefficient"] == 0 for cell in filler):
                continue
            ignored_tail_zero_cells = canonical_clone_v1(filler)
        if (
            not all(numeric(cell) for cell in classification)
            or not numeric(total)
            or sum(cell["coefficient"] for cell in classification) != total["coefficient"]
        ):
            continue
        candidates.append(
            {
                "alignment_mode": "PACKED_SPARSE_ROW_UNIQUE_ARITHMETIC_PIVOT",
                "classification_cells": canonical_clone_v1(classification),
                "fair_value_cell": canonical_clone_v1(fair_cell),
                "ignored_packed_zero_cells": ignored_tail_zero_cells,
                "book_total_cell": canonical_clone_v1(total),
            }
        )
    if (
        not candidates
        and len(packed) >= 2
        and packed[-1]["state"] == "SOURCE_EXPLICIT_FAIR_VALUE_UNAVAILABLE"
        and all(numeric(cell) and cell["coefficient"] == 0 for cell in packed[:-1])
        and cells[total_ordinal - 1]["state"] == "BLANK"
    ):
        inferred_total = canonical_clone_v1(cells[total_ordinal - 1])
        inferred_total["coefficient"] = 0
        inferred_total["state"] = "BLANK_ZERO_AFTER_COMPLETE_CLASSIFICATION_AXIS_EXACT"
        candidates.append(
            {
                "alignment_mode": "PACKED_SPARSE_ROW_ZERO_TOTAL_OMITTED_BEFORE_UNAVAILABLE_FAIR",
                "classification_cells": canonical_clone_v1(packed[:-1]),
                "fair_value_cell": canonical_clone_v1(packed[-1]),
                "ignored_packed_zero_cells": [],
                "book_total_cell": inferred_total,
            }
        )
    unique = {canonical_json_sha256_v1(candidate): candidate for candidate in candidates}
    if len(unique) != 1:
        return None, [
            "VALUATION_ROW_ALIGNMENT_NOT_UNIQUE"
            if unique
            else "VALUATION_ROW_CLASSIFICATION_TOTAL_NOT_EXACT"
        ]
    resolved = next(iter(unique.values()))
    for cell in [
        *resolved["classification_cells"],
        resolved["book_total_cell"],
        *([resolved["fair_value_cell"]] if resolved["fair_value_cell"] is not None else []),
    ]:
        if cell["state"] == "NORMALIZED_SINGLE_NUMERIC_TOKEN_PENDING_GRAPH":
            cell["state"] = "NORMALIZED_SINGLE_NUMERIC_TOKEN_ROW_GRAPH_EXACT"
    equation = {
        "computed_value": sum(cell["coefficient"] for cell in resolved["classification_cells"]),
        "equation_kind": "CLASSIFICATION_CELLS_EQUAL_BOOK_TOTAL",
        "result_cell": canonical_clone_v1(resolved["book_total_cell"]),
        "row_id": row_axis["row_id"],
        "status": "EXACT",
        "term_cells": canonical_clone_v1(resolved["classification_cells"]),
    }
    return (
        {
            **canonical_clone_v1(row_axis),
            **resolved,
            "equation": equation,
        },
        [],
    )


def _valuation_aggregate_value_v1(
    *, cells: Sequence[Mapping[str, Any]], period_role: str, period_date: str, axis_role: str
) -> dict[str, Any]:
    components = [
        {
            "axis_role": axis_role,
            "cell_ref": canonical_clone_v1(cell["cell_ref"]),
            "coefficient": cell["coefficient"],
            "period_date": period_date,
            "period_role": period_role,
            "source_text": cell["source_text"],
            "state": cell["state"],
        }
        for cell in cells
    ]
    return {
        "aggregate_components": components,
        "axis_role": axis_role,
        "cell_ref": None,
        "coefficient": sum(item["coefficient"] for item in components),
        "period_date": period_date,
        "period_role": period_role,
        "source_text": None,
        "state": "AGGREGATED_SOURCE_CELLS_GRAPH_EXACT",
    }


def _valuation_mapping_value_v1(
    *, cell: Mapping[str, Any], period_role: str, period_date: str, axis_role: str
) -> dict[str, Any]:
    return {
        "axis_role": axis_role,
        "cell_ref": canonical_clone_v1(cell["cell_ref"]),
        "coefficient": cell["coefficient"],
        "period_date": period_date,
        "period_role": period_role,
        "source_text": cell["source_text"],
        "state": cell["state"],
    }


def _build_valuation_mappings_v1(
    *,
    compiled_specs: Mapping[str, Any],
    canonical_unit: str,
    period_assignments: Sequence[Mapping[str, Any]],
    role_period_cells: Mapping[tuple[str, str, str], Sequence[Mapping[str, Any]]],
    total_period_cells: Mapping[tuple[str, str], Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build the exact schema projection from a closed valuation cell graph."""

    period_dates = {item["period_role"]: item["period_date"] for item in period_assignments}
    if set(period_dates) not in (
        {"CURRENT_PERIOD"},
        {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"},
    ):
        raise _error("valuation-matrix period mapping axis is incomplete")
    mappings = []
    for role, report_norm_id in (
        ("FAMILY", compiled_specs["family_root_report_norm_id"]),
        ("BOOK_BRANCH", compiled_specs["book_branch_report_norm_id"]),
        ("FAIR_BRANCH", compiled_specs["fair_branch_report_norm_id"]),
    ):
        mapping = {
            "item_mapping_id": "gjeqmfv1:item:pending",
            "report_norm_id": report_norm_id,
            "role": role,
            "row_id": f"structural:{role}",
            "unit": None,
            "values": [],
        }
        mapping["item_mapping_id"] = "gjeqmfv1:item:" + canonical_json_sha256_v1(
            {key: value for key, value in mapping.items() if key != "item_mapping_id"}
        )
        mappings.append(mapping)
    for role, binding in {
        **compiled_specs["valuation_total_bindings_by_role"],
        **compiled_specs["valuation_component_bindings_by_role"],
    }.items():
        values = []
        for period_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"):
            if period_role not in period_dates:
                continue
            if role in compiled_specs["valuation_total_bindings_by_role"]:
                cell = total_period_cells.get((role, period_role))
                cells = [cell] if cell is not None else []
            else:
                cells = list(role_period_cells.get((role, period_role, "CARRYING_VALUE"), []))
            if len(cells) == 1:
                values.append(
                    _valuation_mapping_value_v1(
                        cell=cells[0],
                        period_role=period_role,
                        period_date=period_dates[period_role],
                        axis_role="CARRYING_VALUE",
                    )
                )
            elif len(cells) > 1:
                values.append(
                    _valuation_aggregate_value_v1(
                        cells=cells,
                        period_role=period_role,
                        period_date=period_dates[period_role],
                        axis_role="CARRYING_VALUE",
                    )
                )
        if values:
            mapping = {
                "item_mapping_id": "gjeqmfv1:item:pending",
                "report_norm_id": binding["book_report_norm_id"],
                "role": role,
                "row_id": f"book:{role}",
                "unit": canonical_unit,
                "values": values,
            }
            mapping["item_mapping_id"] = "gjeqmfv1:item:" + canonical_json_sha256_v1(
                {key: value for key, value in mapping.items() if key != "item_mapping_id"}
            )
            mappings.append(mapping)
        fair_values = []
        for period_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"):
            if period_role not in period_dates:
                continue
            cells = list(role_period_cells.get((role, period_role, "FAIR_VALUE"), []))
            if len(cells) == 1:
                fair_values.append(
                    _valuation_mapping_value_v1(
                        cell=cells[0],
                        period_role=period_role,
                        period_date=period_dates[period_role],
                        axis_role="FAIR_VALUE",
                    )
                )
            elif len(cells) > 1:
                fair_values.append(
                    _valuation_aggregate_value_v1(
                        cells=cells,
                        period_role=period_role,
                        period_date=period_dates[period_role],
                        axis_role="FAIR_VALUE",
                    )
                )
        if fair_values:
            fair_role = role.replace("BOOK_", "FAIR_", 1)
            mapping = {
                "item_mapping_id": "gjeqmfv1:item:pending",
                "report_norm_id": binding["fair_report_norm_id"],
                "role": fair_role,
                "row_id": f"fair:{role}",
                "unit": canonical_unit,
                "values": fair_values,
            }
            mapping["item_mapping_id"] = "gjeqmfv1:item:" + canonical_json_sha256_v1(
                {key: value for key, value in mapping.items() if key != "item_mapping_id"}
            )
            mappings.append(mapping)
    return mappings


def _evaluate_valuation_matrix_cluster_v1(
    *,
    regions: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
    document_unit_context_evidence: Mapping[str, Any] | None,
) -> dict[str, Any]:
    checked_regions = _checked_region_axis(regions)
    expected_query = build_gemini_json_equity_matrix_region_query_receipt_v1(
        checked_regions, owner_receipt=query_receipt.get("owner_receipt", {})
    )
    if not same_typed_json_v1(expected_query, query_receipt):
        raise _error("valuation-matrix query receipt drifted")
    period_assignments = query_receipt.get("owner_receipt", {}).get("period_assignments")
    if type(period_assignments) is not list or len(period_assignments) != len(checked_regions):
        raise _error("valuation-matrix period assignment axis is incomplete")
    assignment_by_key = {
        (
            item.get("page_json_version_id"),
            item.get("section_id"),
            item.get("table_id"),
        ): item
        for item in period_assignments
        if type(item) is dict
    }
    tables = []
    classifications = []
    reasons = []
    table_receipts = []
    role_period_cells: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    total_period_cells: dict[tuple[str, str], dict[str, Any]] = {}
    equations = []
    for region in checked_regions:
        page = page_json_by_version.get(region["page_json_version_id"])
        if type(page) is not dict:
            raise _error("valuation-matrix selected canonical page is absent")
        _section, table = _source_table(
            page, section_id=region["section_id"], table_id=region["table_id"]
        )
        classification = _classify_valuation_matrix_table_v1(table, compiled_specs=compiled_specs)
        tables.append(table)
        classifications.append(classification)
        reasons.extend(classification["reasons"])
        assignment = assignment_by_key.get(
            (region["page_json_version_id"], region["section_id"], region["table_id"])
        )
        if (
            type(assignment) is not dict
            or assignment.get("period_role") not in {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"}
            or type(assignment.get("period_date")) is not str
        ):
            reasons.append("VALUATION_FRAGMENT_PERIOD_ASSIGNMENT_MISSING")
            continue
        resolved_rows = []
        row_by_id = {f"r{ordinal}": row for ordinal, row in enumerate(table["rows"], start=1)}
        for row_axis in classification["component_axis"]:
            if row_axis["kind"] not in {"MAPPED_COMPONENT", "BRANCH_TOTAL"}:
                continue
            resolved, row_reasons = _valuation_resolve_row_v1(
                row=row_by_id[row_axis["row_id"]],
                row_axis=row_axis,
                column_axis=classification["column_axis"],
                region=region,
                compiled_specs=compiled_specs,
            )
            reasons.extend(f"{row_axis['row_id']}:{reason}" for reason in row_reasons)
            if resolved is None:
                continue
            resolved_rows.append(resolved)
            equations.append(canonical_clone_v1(resolved["equation"]))
            if row_axis["kind"] == "MAPPED_COMPONENT":
                role_period_cells.setdefault(
                    (row_axis["role"], assignment["period_role"], "CARRYING_VALUE"), []
                ).append(resolved["book_total_cell"])
                fair = resolved["fair_value_cell"]
                if fair is not None and fair.get("state") in {
                    "RAW_SIGNED_INTEGER",
                    "NORMALIZED_SINGLE_NUMERIC_TOKEN_ROW_GRAPH_EXACT",
                }:
                    role_period_cells.setdefault(
                        (row_axis["role"], assignment["period_role"], "FAIR_VALUE"), []
                    ).append(fair)
            else:
                total_period_cells[(row_axis["role"], assignment["period_role"])] = resolved[
                    "book_total_cell"
                ]
                fair = resolved["fair_value_cell"]
                if fair is not None and fair.get("state") in {
                    "RAW_SIGNED_INTEGER",
                    "NORMALIZED_SINGLE_NUMERIC_TOKEN_ROW_GRAPH_EXACT",
                }:
                    role_period_cells.setdefault(
                        (row_axis["role"], assignment["period_role"], "FAIR_VALUE"), []
                    ).append(fair)
        for branch in ("ASSET", "LIABILITY"):
            item_cells = [
                row["book_total_cell"]
                for row in resolved_rows
                if row["branch"] == branch and row["kind"] == "MAPPED_COMPONENT"
            ]
            total_rows = [
                row
                for row in resolved_rows
                if row["branch"] == branch and row["kind"] == "BRANCH_TOTAL"
            ]
            if len(total_rows) != 1 or not item_cells:
                reasons.append(f"{branch}_BOOK_BRANCH_FRONTIER_INCOMPLETE")
                continue
            result_cell = total_rows[0]["book_total_cell"]
            computed = sum(cell["coefficient"] for cell in item_cells)
            status = "EXACT" if computed == result_cell["coefficient"] else "MISMATCH"
            equations.append(
                {
                    "computed_value": computed,
                    "equation_kind": f"{branch}_ITEM_BOOK_TOTALS_EQUAL_BRANCH_TOTAL",
                    "result_cell": canonical_clone_v1(result_cell),
                    "status": status,
                    "term_cells": canonical_clone_v1(item_cells),
                }
            )
            if status != "EXACT":
                reasons.append(f"{branch}_BOOK_BRANCH_TOTAL_MISMATCH")
        table_receipts.append(
            {
                "classification": classification,
                "period_assignment": canonical_clone_v1(assignment),
                "region": canonical_clone_v1(region),
                "resolved_rows": resolved_rows,
            }
        )
    unit_receipt, unit_reasons = _resolve_cluster_unit(
        tables=tables,
        compiled_specs=compiled_specs,
        document_unit_context_evidence=document_unit_context_evidence,
    )
    reasons.extend(unit_reasons)
    reasons = sorted(set(reasons))
    mappings = []
    if not reasons and unit_receipt["canonical_unit"] is not None:
        mappings = _build_valuation_mappings_v1(
            compiled_specs=compiled_specs,
            canonical_unit=unit_receipt["canonical_unit"],
            period_assignments=period_assignments,
            role_period_cells=role_period_cells,
            total_period_cells=total_period_cells,
        )
    first = checked_regions[0]
    closure_receipt = {
        "equations": equations,
        "matrix_kind": "VALUATION_CLASSIFICATION",
        "period_assignments": canonical_clone_v1(period_assignments),
        "query_receipt": canonical_clone_v1(query_receipt),
        "rule": ("EXACT_FIXED_OR_UNIQUE_PACKED_ROWS_AND_ASSET_LIABILITY_BRANCH_TOTALS"),
        "table_receipts": table_receipts,
        "unit_receipt": unit_receipt,
    }
    material = {
        "claim_boundary": VALUATION_CLAIM_BOUNDARY,
        "closure_receipt": closure_receipt,
        "component_regions": canonical_clone_v1(checked_regions),
        "document_id": first["document_id"],
        "family_id": compiled_specs["family_id"],
        "mappings": mappings,
        "page_json_version_id": first["page_json_version_id"],
        "physical_page": first["physical_page"],
        "reasons": reasons,
        "section_id": first["section_id"],
        "source_logical_name": first["source_logical_name"],
        "source_sha256": first["source_sha256"],
        "status": READY if not reasons else UNRESOLVED,
        "table_id": first["table_id"],
    }
    if reasons:
        material["mappings"] = []
    return {
        "candidate_id": "gjeqmfv1:candidate:" + canonical_json_sha256_v1(material),
        **material,
    }


def evaluate_gemini_json_equity_matrix_family_cluster_v1(
    *,
    regions: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
    document_unit_context_evidence: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Evaluate one exact matrix cluster and emit mappings only after closure."""

    if compiled_specs.get("exchange_rate_mode") is True:
        from bctc_ai.evaluation.gemini_json_categorical_period_matrix_v1 import (
            evaluate_gemini_json_categorical_period_matrix_cluster_v1,
        )

        return evaluate_gemini_json_categorical_period_matrix_cluster_v1(
            regions=regions,
            page_json_by_version=page_json_by_version,
            compiled_specs=compiled_specs,
            query_receipt=query_receipt,
            document_unit_context_evidence=document_unit_context_evidence,
        )
    if compiled_specs.get("currency_risk_mode") is True:
        from bctc_ai.evaluation.gemini_json_currency_risk_matrix_v1 import (
            evaluate_gemini_json_currency_risk_cluster_v1,
        )

        return evaluate_gemini_json_currency_risk_cluster_v1(
            regions=regions,
            page_json_by_version=page_json_by_version,
            compiled_specs=compiled_specs,
            query_receipt=query_receipt,
            document_unit_context_evidence=document_unit_context_evidence,
        )
    if compiled_specs.get("valuation_mode") is True:
        return _evaluate_valuation_matrix_cluster_v1(
            regions=regions,
            page_json_by_version=page_json_by_version,
            compiled_specs=compiled_specs,
            query_receipt=query_receipt,
            document_unit_context_evidence=document_unit_context_evidence,
        )

    checked_regions = _checked_region_axis(regions)
    expected_query = build_gemini_json_equity_matrix_region_query_receipt_v1(
        checked_regions, owner_receipt=query_receipt.get("owner_receipt", {})
    )
    if not same_typed_json_v1(expected_query, query_receipt):
        raise _error("equity-matrix query receipt drifted")
    if (
        type(compiled_specs) is not dict
        or compiled_specs.get("engine_format_version") != ENGINE_FORMAT_VERSION
    ):
        raise _error("equity-matrix compiled specs are invalid")
    effective_page_json_by_version, source_repair_receipts = (
        _apply_authenticated_source_repair_artifact_v1(
            page_json_by_version=page_json_by_version,
            compiled_specs=compiled_specs,
            regions=checked_regions,
        )
    )
    tables = []
    classifications = []
    reasons = []
    for region in checked_regions:
        page = effective_page_json_by_version.get(region["page_json_version_id"])
        if type(page) is not dict:
            raise _error("equity-matrix selected canonical page is absent")
        _section, table = _source_table(
            page, section_id=region["section_id"], table_id=region["table_id"]
        )
        classification = classify_gemini_json_equity_matrix_table_v1(
            table, compiled_specs=compiled_specs
        )
        tables.append(table)
        classifications.append(classification)
    continuation_plan = _component_row_continuation_plan_v1(
        tables=tables,
        classifications=classifications,
        compiled_specs=compiled_specs,
    )
    supplemental_component_group_plan = _supplemental_component_group_plan_v1(
        tables=tables,
        classifications=classifications,
        compiled_specs=compiled_specs,
    )
    if continuation_plan is None and supplemental_component_group_plan is None:
        for classification in classifications:
            reasons.extend(classification["reasons"])
            if classification["status"] != "MATRIX_FRAGMENT":
                reasons.append("SELECTED_FRAGMENT_IS_NOT_ONE_COMPLETE_MATRIX_AXIS")
    graph, graph_reasons = _build_matrix_graph(
        regions=checked_regions,
        tables=tables,
        classifications=classifications,
        compiled_specs=compiled_specs,
    )
    reasons.extend(graph_reasons)
    equations = []
    sign_multiplier = 1
    if graph and not graph_reasons:
        equations, equation_reasons, sign_multiplier = _build_equations(graph)
        matrix_mismatch_reasons = {
            "HORIZONTAL_VISIBLE_TOTAL_MISMATCH",
            "VERTICAL_COMPONENT_ROLLFORWARD_MISMATCH",
        }
        if (
            graph["orientation"] == "COMPONENT_COLUMNS"
            and equation_reasons
            and set(equation_reasons) <= matrix_mismatch_reasons
        ):
            aligned_graph, alignment_reasons = _resolve_component_column_row_alignment_v1(graph)
            if aligned_graph is not None:
                aligned_equations, aligned_reasons, aligned_multiplier = _build_equations(
                    aligned_graph
                )
                if not aligned_reasons:
                    graph = aligned_graph
                    equations = aligned_equations
                    sign_multiplier = aligned_multiplier
                    equation_reasons = []
            else:
                equation_reasons = sorted(set(equation_reasons) | set(alignment_reasons))
        if graph["orientation"] == "COMPONENT_COLUMNS":
            cumulative_graph, cumulative_equations, cumulative_multiplier = (
                _resolve_directional_cumulative_movement_control_v1(
                    graph, compiled_specs=compiled_specs
                )
            )
            if cumulative_graph is not None:
                graph = cumulative_graph
                equations = cumulative_equations
                sign_multiplier = cumulative_multiplier
                equation_reasons = []
        reasons.extend(equation_reasons)
    family_root_boundary_vector = None
    grand_totals = [
        item for item in graph.get("component_axis", []) if item.get("kind") == "GRAND_TOTAL"
    ]
    if len(grand_totals) == 1:
        boundary_cells = graph.get("component_cells", {}).get(
            grand_totals[0].get("axis_id"), {}
        )
        opening_cell = boundary_cells.get("OPENING")
        closing_cell = boundary_cells.get("CLOSING")
        if isinstance(opening_cell, Mapping) and isinstance(closing_cell, Mapping):
            opening = observed_source_coefficient_v1(opening_cell)
            closing = observed_source_coefficient_v1(closing_cell)
            if type(opening) is int and type(closing) is int:
                family_root_boundary_vector = {"closing": closing, "opening": opening}
    unit_receipt, unit_reasons = _resolve_cluster_unit(
        tables=tables,
        compiled_specs=compiled_specs,
        document_unit_context_evidence=document_unit_context_evidence,
        family_root_boundary_vector=family_root_boundary_vector,
    )
    reasons.extend(unit_reasons)
    reasons = sorted(set(reasons))
    mappings, omitted_all_blank_mapping_roles = (
        _build_mappings(
            graph=graph,
            compiled_specs=compiled_specs,
            unit=unit_receipt["canonical_unit"],
            sign_multiplier=sign_multiplier,
        )
        if not reasons and graph and unit_receipt["canonical_unit"] is not None
        else ([], [])
    )
    if not mappings and omitted_all_blank_mapping_roles and not reasons:
        reasons = ["ALL_SCHEMA_MAPPING_ROLES_HAVE_BLANK_SOURCE_LANES"]
    first = checked_regions[0]
    status = READY if mappings and not reasons else UNRESOLVED
    closure_receipt = {
        "alignment_receipts": canonical_clone_v1(graph.get("alignment_receipts", [])),
        "component_axis": canonical_clone_v1(graph.get("component_axis", [])),
        "equations": equations,
        "movement_axis": canonical_clone_v1(graph.get("movement_axis", [])),
        "omitted_all_blank_mapping_roles": omitted_all_blank_mapping_roles,
        "orientation": graph.get("orientation"),
        "period_block_receipt": canonical_clone_v1(graph.get("period_block_receipt")),
        "query_receipt": canonical_clone_v1(query_receipt),
        "rule": (
            "COMPLETE_BIDIRECTIONAL_MATRIX_HORIZONTAL_HIERARCHY_AND_VERTICAL_"
            "ROLLFORWARD_EXACT_BEFORE_SCHEMA_MAPPING"
        ),
        "source_only_component_axes": [
            canonical_clone_v1(item)
            for item in graph.get("component_axis", [])
            if item["kind"] in {"SOURCE_ONLY_COMPONENT", "DISCLOSURE_COMPONENT"}
        ],
        "source_repair_receipts": source_repair_receipts,
        "unit_receipt": unit_receipt,
    }
    if graph.get("signed_branch_mode") is True:
        closure_receipt["signed_branch_receipt"] = canonical_clone_v1(
            graph["signed_branch_receipt"]
        )
    candidate = {
        "candidate_id": "gjeqmfv1:candidate:pending",
        "claim_boundary": CLAIM_BOUNDARY,
        "closure_receipt": closure_receipt,
        "component_regions": checked_regions,
        "document_id": first["document_id"],
        "family_id": compiled_specs["family_id"],
        "mappings": mappings,
        "page_json_version_id": first["page_json_version_id"],
        "physical_page": first["physical_page"],
        "reasons": reasons,
        "section_id": first["section_id"],
        "source_logical_name": first["source_logical_name"],
        "source_sha256": first["source_sha256"],
        "status": status,
        "table_id": first["table_id"],
    }
    candidate["candidate_id"] = "gjeqmfv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in candidate.items() if key != "candidate_id"}
    )
    return candidate


def validate_gemini_json_equity_matrix_family_candidate_replay_v1(
    value: Any,
    *,
    regions: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
    document_unit_context_evidence: Mapping[str, Any] | None,
) -> dict[str, Any]:
    expected = evaluate_gemini_json_equity_matrix_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
        document_unit_context_evidence=document_unit_context_evidence,
    )
    if not same_typed_json_v1(value, expected):
        source = value.get("source_logical_name") if type(value) is dict else None
        raise _error(
            "equity-matrix candidate does not replay from selected canonical JSON"
            + (f": {source}" if type(source) is str and source else "")
        )
    return expected


def _selected_page_record_axis(page_records: Any) -> list[dict[str, Any]]:
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
        raise _error("equity-matrix selected page records are absent")
    checked = []
    identity = None
    prior = None
    for record in page_records:
        if (
            type(record) is not dict
            or set(record) != fields
            or _DOCUMENT_ID.fullmatch(record.get("document_id", "")) is None
            or type(record.get("document_ordinal")) is not int
            or record["document_ordinal"] <= 0
            or _PAGE_VERSION.fullmatch(record.get("page_json_version_id", "")) is None
            or type(record.get("physical_page")) is not int
            or record["physical_page"] <= 0
            or type(record.get("selected_page_ordinal")) is not int
            or record["selected_page_ordinal"] <= 0
            or type(record.get("source_logical_name")) is not str
            or not record["source_logical_name"]
            or _SHA256.fullmatch(record.get("source_sha256", "")) is None
            or type(record.get("page_json")) is not dict
            or type(record["page_json"].get("sections")) is not list
        ):
            raise _error("equity-matrix selected page record is invalid")
        current_identity = tuple(
            record[key]
            for key in (
                "document_id",
                "document_ordinal",
                "source_logical_name",
                "source_sha256",
            )
        )
        position = (record["selected_page_ordinal"], record["physical_page"])
        if identity is None:
            identity = current_identity
        elif current_identity != identity:
            raise _error("equity-matrix selected pages cross document identity")
        if prior is not None and position <= prior:
            raise _error("equity-matrix selected pages are not in source order")
        prior = position
        checked.append(canonical_clone_v1(record))
    return checked


def _contained_declared_alias(value: Any, aliases: Sequence[str]) -> str | None:
    folded = _normalized(value)
    matches = [
        alias
        for alias in aliases
        if re.search(
            rf"(?<![a-z0-9]){re.escape(_normalized(alias))}(?![a-z0-9])",
            folded,
        )
    ]
    if not matches:
        return None
    maximum = max(len(_normalized(alias)) for alias in matches)
    winners = sorted(alias for alias in matches if len(_normalized(alias)) == maximum)
    # Every alias in one call denotes the same typed marker role.  Multiple
    # owner spellings on a heading (for example both ``Vốn và các quỹ`` and
    # ``vốn chủ sở hữu``) corroborate rather than conflict.  Seal the
    # deterministic longest/lexical representative.
    return winners[0]


def _declared_reset_alias_v1(value: Any, aliases: Sequence[str]) -> str | None:
    """Match broad reset headings exactly, while retaining specific phrase anchors."""

    exact_heading_aliases = {"co phieu", "co tuc"}
    exact_matches = [
        alias
        for alias in aliases
        if _normalized(alias) in exact_heading_aliases and _matches(value, alias)
    ]
    contained = _contained_declared_alias(
        value,
        [alias for alias in aliases if _normalized(alias) not in exact_heading_aliases],
    )
    matches = [*exact_matches, *([contained] if contained is not None else [])]
    if not matches:
        return None
    maximum = max(len(_normalized(alias)) for alias in matches)
    return sorted(alias for alias in matches if len(_normalized(alias)) == maximum)[0]


def _primary_statement_root_unit_evidence_v1(
    pages: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Return typed statement-root vectors carrying an explicit money unit.

    A unitless continuation page may inherit only from the reciprocal table on
    the immediately preceding physical page.  Proximity alone is deliberately
    insufficient: the downstream resolver must also exact-match the statement
    root vector to the selected equity matrix boundary vector.
    """

    table_records = []
    for record in pages:
        page = record["page_json"]
        if page.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
            continue
        for section_ordinal, section in enumerate(page.get("sections", []), start=1):
            if type(section) is not dict or type(section.get("tables")) is not list:
                continue
            for table_ordinal, table in enumerate(section["tables"], start=1):
                if type(table) is not dict:
                    continue
                table_records.append(
                    {
                        "local_unit_axis": _local_unit_axis(
                            table, compiled_specs=compiled_specs
                        ),
                        "page_json_version_id": record["page_json_version_id"],
                        "physical_page": record["physical_page"],
                        "section_id": f"s{section_ordinal}",
                        "table": table,
                        "table_id": f"t{table_ordinal}",
                    }
                )

    evidence = []
    owner_aliases = compiled_specs["query_policy"]["owner_aliases"]
    for current in table_records:
        table = current["table"]
        unit_axis = current["local_unit_axis"]
        unit_governor = None
        if unit_axis["complete"]:
            unit_governor = {
                "local_unit_axis": canonical_clone_v1(unit_axis),
                "page_json_version_id": current["page_json_version_id"],
                "physical_page": current["physical_page"],
                "rule": "SAME_PRIMARY_STATEMENT_TABLE_EXPLICIT_UNIT",
                "section_id": current["section_id"],
                "table_id": current["table_id"],
            }
        elif table.get("continuation") == "CONTINUES_FROM_PREVIOUS_PAGE":
            current_kinds = [
                column.get("value_kind")
                for column in table.get("columns", [])
                if type(column) is dict
            ]
            prior = [
                item
                for item in table_records
                if item["physical_page"] + 1 == current["physical_page"]
                and item["section_id"] == current["section_id"]
                and item["table_id"] == current["table_id"]
                and item["table"].get("continuation") == "CONTINUES_ON_NEXT_PAGE"
                and item["local_unit_axis"]["complete"]
                and [
                    column.get("value_kind")
                    for column in item["table"].get("columns", [])
                    if type(column) is dict
                ]
                == current_kinds
            ]
            if len(prior) == 1:
                governor = prior[0]
                unit_axis = governor["local_unit_axis"]
                unit_governor = {
                    "continuation_exact": table["continuation"],
                    "governor_continuation_exact": governor["table"]["continuation"],
                    "local_unit_axis": canonical_clone_v1(unit_axis),
                    "page_json_version_id": governor["page_json_version_id"],
                    "physical_page": governor["physical_page"],
                    "rule": "EXPLICIT_RECIPROCAL_ADJACENT_PRIMARY_STATEMENT_CONTINUATION_UNIT",
                    "section_id": governor["section_id"],
                    "table_id": governor["table_id"],
                }
        if unit_governor is None:
            continue
        columns = table.get("columns", [])
        money_ordinals = [
            ordinal
            for ordinal, column in enumerate(columns)
            if type(column) is dict and column.get("value_kind") == "MONEY"
        ]
        if len(money_ordinals) != 2:
            continue
        for row_ordinal, row in enumerate(table.get("rows", []), start=1):
            if type(row) is not dict or type(row.get("values_exact")) is not list:
                continue
            members = [row.get("label_exact"), *(row.get("hierarchy_path_exact") or [])]
            if not any(
                _matches(member, alias)
                for member in members
                if type(member) is str
                for alias in owner_aliases
            ):
                continue
            if len(row["values_exact"]) != len(columns):
                continue
            source_values = [row["values_exact"][ordinal] for ordinal in money_ordinals]
            parsed = []
            for source_value in source_values:
                try:
                    cell = _money(source_value)
                except ValueError:
                    cell = None
                if cell is None or type(cell.get("coefficient")) is not int:
                    parsed = []
                    break
                parsed.append(cell["coefficient"])
            if len(parsed) != 2:
                continue
            evidence.append(
                {
                    "canonical_unit": unit_axis["canonical_unit"],
                    "page_json_version_id": current["page_json_version_id"],
                    "physical_page": current["physical_page"],
                    "root_label_exact": row.get("label_exact"),
                    "root_values_source_order": parsed,
                    "root_values_source_text": canonical_clone_v1(source_values),
                    "row_id": f"r{row_ordinal}",
                    "rule": "PRIMARY_STATEMENT_DECLARED_FAMILY_ROOT_TWO_MONEY_LANE_VECTOR",
                    "section_id": current["section_id"],
                    "table_id": current["table_id"],
                    "unit_governor": unit_governor,
                }
            )
    return evidence


def _document_unit_context_v1(
    pages: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
    target_tables: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    evidence = []
    for record in pages:
        for section_ordinal, section in enumerate(record["page_json"]["sections"], start=1):
            if type(section) is not dict or type(section.get("tables")) is not list:
                continue
            for table_ordinal, table in enumerate(section["tables"], start=1):
                if type(table) is not dict or type(table.get("unit_exact")) is not str:
                    continue
                occurrences = _unit_occurrences(table["unit_exact"], compiled_specs=compiled_specs)
                identities = {
                    (item["canonical_unit"], item["magnitude_power10"])
                    for item in occurrences
                    if compiled_specs["unit_binding_by_alias"][item["matched_alias"]][
                        "document_consensus_eligible"
                    ]
                }
                if len(identities) != 1:
                    continue
                canonical_unit, magnitude = next(iter(identities))
                evidence.append(
                    {
                        "canonical_unit": canonical_unit,
                        "magnitude_power10": magnitude,
                        "page_json_version_id": record["page_json_version_id"],
                        "physical_page": record["physical_page"],
                        "section_id": f"s{section_ordinal}",
                        "source_exact": table["unit_exact"],
                        "source_kind": "TABLE_UNIT",
                        "table_id": f"t{table_ordinal}",
                    }
                )
    identities = {(item["canonical_unit"], item["magnitude_power10"]) for item in evidence}
    distinct_pages = {(item["page_json_version_id"], item["physical_page"]) for item in evidence}
    canonical_unit = next(iter(identities))[0] if len(identities) == 1 else None
    status = (
        "UNIQUE_AUTHENTICATED_DOCUMENT_MONEY_UNIT_CONSENSUS"
        if len(identities) == 1 and len(distinct_pages) >= 2
        else "CONFLICTING_DOCUMENT_MONEY_UNIT_CONTEXT"
        if len(identities) > 1
        else "INSUFFICIENT_DOCUMENT_MONEY_UNIT_CONTEXT"
    )
    material: dict[str, Any] = {
        "canonical_unit": canonical_unit,
        "distinct_page_count": len(distinct_pages),
        "evidence": evidence,
        "evidence_axis_sha256": canonical_json_sha256_v1(evidence),
        "status": status,
    }
    target_unit_axes = [
        _local_unit_axis(table, compiled_specs=compiled_specs) for table in target_tables
    ]
    fallback_enabled = (
        compiled_specs.get("primary_statement_root_unit_policy", {}).get("mode")
        == "EXACT_FAMILY_ROOT_BOUNDARY_VECTOR_CORROBORATION"
    )
    target_has_no_unit_surface = bool(target_unit_axes) and all(
        not axis["evidence"] and not axis["undeclared_evidence"]
        for axis in target_unit_axes
    )
    if fallback_enabled and status != "UNIQUE_AUTHENTICATED_DOCUMENT_MONEY_UNIT_CONSENSUS" and target_has_no_unit_surface:
        root_evidence = _primary_statement_root_unit_evidence_v1(
            pages, compiled_specs=compiled_specs
        )
        if root_evidence:
            material["primary_statement_root_unit_evidence"] = root_evidence
    return {
        **material,
        "document_unit_context_sha256": canonical_json_sha256_v1(material),
    }


def _matrix_region(item: Mapping[str, Any], *, fragment_ordinal: int) -> dict[str, Any]:
    record = item["record"]
    return {
        "document_id": record["document_id"],
        "document_ordinal": record["document_ordinal"],
        "page_json_version_id": record["page_json_version_id"],
        "physical_page": record["physical_page"],
        "selected_page_ordinal": record["selected_page_ordinal"],
        "section_id": item["section_id"],
        "source_logical_name": record["source_logical_name"],
        "source_sha256": record["source_sha256"],
        "table_id": item["table_id"],
    }


def _valuation_period_date_from_table_v1(
    *, section: Mapping[str, Any], table: Mapping[str, Any]
) -> tuple[str | None, list[dict[str, Any]], list[str]]:
    observed = []
    for source_kind, surface in (
        ("TABLE_TITLE", table.get("title_exact")),
        ("SECTION_TITLE", section.get("title_exact")),
    ):
        dates = sorted(item.isoformat() for item in _header_dates(surface or ""))
        observed.append(
            {
                "dates": dates,
                "source_exact": surface,
                "source_kind": source_kind,
            }
        )
    # A table title is the narrowest source-governed period carrier.  A broad
    # section/report title is used only when the table title is silent.  This
    # avoids treating a current report heading as a contradiction to an
    # explicitly titled comparative sibling table.
    for item in observed:
        if len(item["dates"]) == 1:
            evidence = [
                {
                    "period_date": item["dates"][0],
                    "source_exact": item["source_exact"],
                    "source_kind": item["source_kind"],
                }
            ]
            return item["dates"][0], evidence, []
        if item["source_kind"] == "TABLE_TITLE" and len(item["dates"]) > 1:
            return None, canonical_clone_v1(observed), ["TABLE_TITLE_PERIOD_DATE_NOT_UNIQUE"]
    return None, canonical_clone_v1(observed), []


def _valuation_document_reporting_date_receipt_v1(
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    # The typed reporting-date primitive is source-generic and already seals
    # PRIMARY_STATEMENT date carriers without inventing a calendar year end.
    from bctc_ai.evaluation.gemini_json_fixed_asset_rollforward_family_v1 import (
        _document_reporting_date_receipt,
    )

    return _document_reporting_date_receipt(pages)


def _valuation_role_population_signature_v1(classification: Mapping[str, Any]) -> list[Any]:
    return [
        [item.get("branch"), item.get("kind"), item.get("role")]
        for item in classification.get("component_axis", [])
        if item.get("kind") != "STRUCTURAL_GROUP"
    ]


def _valuation_forward_table_marker_v1(value: Any) -> bool:
    folded = _normalized(value)
    return bool(
        re.search(r"\bbang\b", folded)
        and re.search(r"\b(?:sau|duoi day|tiep theo)\b", folded)
        and re.search(r"\b(?:trinh bay|the hien|chi tiet|tong hop)\b", folded)
    )


def _coalesce_valuation_matrix_document_v1(
    *, page_records: Any, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    pages = _selected_page_record_axis(page_records)
    inventory = []
    owner_markers = []
    period_markers = []
    continuation_markers = []
    reset_markers = []
    for record in pages:
        for section_ordinal, section in enumerate(record["page_json"]["sections"], start=1):
            if type(section) is not dict:
                continue
            section_id = f"s{section_ordinal}"
            surfaces = [section.get("title_exact"), *(section.get("narratives_exact") or [])]
            title_dates = sorted(
                item.isoformat() for item in _header_dates(section.get("title_exact") or "")
            )
            title_folded = _normalized(section.get("title_exact"))
            if len(title_dates) == 1 and any(
                marker in title_folded
                for marker in ("tai ngay", "ket thuc ngay", "ket thuc cung ngay")
            ):
                period_markers.append(
                    {
                        "period_date": title_dates[0],
                        "position": [record["selected_page_ordinal"], section_ordinal, 0],
                        "source_exact": section.get("title_exact"),
                        "source_kind": "BOUNDED_REPORT_SECTION_TITLE",
                    }
                )
            for source_exact in surfaces:
                position = [record["selected_page_ordinal"], section_ordinal, 0]
                owner = _contained_declared_alias(
                    source_exact, compiled_specs["query_policy"]["owner_aliases"]
                )
                reset = _contained_declared_alias(
                    source_exact,
                    [
                        *compiled_specs["query_policy"]["reset_aliases"],
                        *compiled_specs["query_policy"]["hard_negative_aliases"],
                    ],
                )
                if owner is not None:
                    owner_markers.append(
                        {"alias": owner, "position": position, "source_exact": source_exact}
                    )
                if _valuation_forward_table_marker_v1(source_exact):
                    continuation_markers.append(
                        {
                            "position": position,
                            "source_exact": source_exact,
                            "source_kind": "EXPLICIT_FORWARD_TABLE_NARRATIVE",
                        }
                    )
                if reset is not None:
                    reset_markers.append(
                        {"alias": reset, "position": position, "source_exact": source_exact}
                    )
            tables = section.get("tables")
            if type(tables) is not list:
                continue
            for table_ordinal, table in enumerate(tables, start=1):
                if type(table) is not dict:
                    continue
                position = [record["selected_page_ordinal"], section_ordinal, table_ordinal]
                source_exact = table.get("title_exact")
                owner = _contained_declared_alias(
                    source_exact, compiled_specs["query_policy"]["owner_aliases"]
                )
                reset = _contained_declared_alias(
                    source_exact,
                    [
                        *compiled_specs["query_policy"]["reset_aliases"],
                        *compiled_specs["query_policy"]["hard_negative_aliases"],
                    ],
                )
                if owner is not None:
                    owner_markers.append(
                        {"alias": owner, "position": position, "source_exact": source_exact}
                    )
                if reset is not None:
                    reset_markers.append(
                        {"alias": reset, "position": position, "source_exact": source_exact}
                    )
                classification = _classify_valuation_matrix_table_v1(
                    table, compiled_specs=compiled_specs
                )
                declared_columns = set(classification["column_declared_component_roles"])
                if {"BOOK_TOTAL", "FAIR_VALUE"} <= declared_columns and classification[
                    "row_declared_component_roles"
                ]:
                    local_date, period_evidence, period_reasons = (
                        _valuation_period_date_from_table_v1(section=section, table=table)
                    )
                    inventory.append(
                        {
                            "classification": classification,
                            "continuation": table.get("continuation"),
                            "local_period_date": local_date,
                            "period_evidence": period_evidence,
                            "period_reasons": period_reasons,
                            "position": position,
                            "record": record,
                            "section_title_exact": section.get("title_exact"),
                            "section_id": section_id,
                            "table_id": f"t{table_ordinal}",
                        }
                    )
    selected = [item for item in inventory if item["classification"]["status"] == "MATRIX_FRAGMENT"]
    reasons = [
        reason
        for item in inventory
        if item["classification"]["status"] != "MATRIX_FRAGMENT"
        for reason in item["classification"]["reasons"]
    ]
    if inventory and len(selected) != len(inventory):
        reasons.append("INCOMPLETE_DECLARED_VALUATION_TABLE_PRESENT")
    reporting_date_receipt = _valuation_document_reporting_date_receipt_v1(pages)
    period_assignments = []
    if len(selected) not in {0, 1, 2}:
        reasons.append("MORE_THAN_TWO_VALUATION_PERIOD_TABLES_UNDER_DOCUMENT_OWNER")
    if len(selected) == 2 and not same_typed_json_v1(
        _valuation_role_population_signature_v1(selected[0]["classification"]),
        _valuation_role_population_signature_v1(selected[1]["classification"]),
    ):
        reasons.append("VALUATION_PERIOD_TABLE_ROLE_POPULATIONS_DIFFER")
    for item in selected:
        reasons.extend(item["period_reasons"])
        period_date = item["local_period_date"]
        source = "LOCAL_TABLE_OR_SECTION_DATE"
        if period_date is None:
            prior_period_markers = [
                marker
                for marker in period_markers
                if marker["position"] <= item["position"]
                and item["position"][0] - marker["position"][0]
                <= compiled_specs["query_policy"]["max_continuation_pages"]
            ]
            if prior_period_markers:
                marker = max(prior_period_markers, key=lambda value: value["position"])
                period_date = marker["period_date"]
                source = "BOUNDED_PRECEDING_REPORT_HEADING"
                item["period_evidence"].append(canonical_clone_v1(marker))
        if period_date is None and len(selected) == 1:
            period_date = reporting_date_receipt.get("current_date")
            source = "TYPED_DOCUMENT_REPORTING_DATE"
        if period_date is None:
            reasons.append("VALUATION_PERIOD_DATE_UNRESOLVED")
        period_assignments.append(
            {
                "page_json_version_id": item["record"]["page_json_version_id"],
                "period_date": period_date,
                "period_evidence": canonical_clone_v1(item["period_evidence"]),
                "section_id": item["section_id"],
                "source": source,
                "table_id": item["table_id"],
            }
        )
    distinct_dates = {item["period_date"] for item in period_assignments if item["period_date"]}
    if len(selected) == 2 and len(distinct_dates) != 2:
        reasons.append("TWO_VALUATION_TABLE_PERIOD_DATES_NOT_DISTINCT")
    period_roles = {}
    if len(distinct_dates) == len(selected) and selected:
        ordered_dates = sorted(distinct_dates, reverse=True)
        period_roles = {
            period_date: "CURRENT_PERIOD" if ordinal == 0 else "COMPARATIVE_PERIOD"
            for ordinal, period_date in enumerate(ordered_dates)
        }
        for assignment in period_assignments:
            assignment["period_role"] = period_roles[assignment["period_date"]]

    owner_receipt = None
    if selected:
        first_position = min(item["position"] for item in selected)
        last_position = max(item["position"] for item in selected)
        prior_owners = [
            marker
            for marker in owner_markers
            if marker["position"] <= first_position
            and first_position[0] - marker["position"][0]
            <= compiled_specs["query_policy"]["max_continuation_pages"]
            and (
                marker["position"][0] == first_position[0]
                or min(selected, key=lambda item: item["position"])["continuation"]
                == "CONTINUES_FROM_PREVIOUS_PAGE"
                or any(
                    marker["position"] <= continuation["position"] < first_position
                    and first_position[0] - continuation["position"][0]
                    <= compiled_specs["query_policy"]["max_continuation_pages"]
                    for continuation in continuation_markers
                )
            )
        ]
        if not prior_owners:
            reasons.append("EXPLICIT_BOUNDED_VALUATION_MATRIX_OWNER_NOT_VISIBLE")
        else:
            owner = max(prior_owners, key=lambda item: item["position"])
            fenced_resets = [
                marker
                for marker in reset_markers
                if owner["position"] <= marker["position"] <= last_position
            ]
            if fenced_resets:
                reasons.append("OWNER_TO_VALUATION_MATRIX_INTERVAL_CONTAINS_RESET")
            first_selected = min(selected, key=lambda item: item["position"])
            continuation_evidence = None
            if owner["position"][0] != first_position[0]:
                narrative_markers = [
                    marker
                    for marker in continuation_markers
                    if owner["position"] <= marker["position"] < first_position
                    and first_position[0] - marker["position"][0]
                    <= compiled_specs["query_policy"]["max_continuation_pages"]
                ]
                if narrative_markers:
                    continuation_evidence = max(
                        narrative_markers, key=lambda item: item["position"]
                    )
                elif first_selected["continuation"] == "CONTINUES_FROM_PREVIOUS_PAGE":
                    continuation_evidence = {
                        "position": first_selected["position"],
                        "source_exact": first_selected["continuation"],
                        "source_kind": "STRUCTURED_TABLE_CONTINUATION",
                    }
            owner_receipt = {
                "continuation_evidence": continuation_evidence,
                "document_reporting_date_receipt": reporting_date_receipt,
                "owner_alias": owner["alias"],
                "owner_position": owner["position"],
                "owner_source_exact": owner["source_exact"],
                "period_assignments": period_assignments,
                "reset_fence_axis": fenced_resets,
                "rule": "LATEST_EXPLICIT_OWNER_WITHIN_ONE_PAGE_RESET_FREE_INTERVAL",
            }
    regions = [
        _matrix_region(item, fragment_ordinal=ordinal)
        for ordinal, item in enumerate(selected, start=1)
    ]
    if regions:
        try:
            _checked_region_axis(regions)
        except GeminiJsonEquityMatrixAccountingFamilyV1Error:
            reasons.append("VALUATION_REGION_AXIS_IS_NOT_ONE_OR_TWO_ADJACENT_FRAGMENTS")
    inventory_receipt = [
        {
            "classification": canonical_clone_v1(item["classification"]),
            "continuation": item["continuation"],
            "disposition": (
                "SELECTED_VALUATION_FRAGMENT"
                if item in selected
                else "UNSELECTED_DECLARED_VALUATION_TABLE"
            ),
            "local_period_date": item["local_period_date"],
            "page_json_version_id": item["record"]["page_json_version_id"],
            "period_evidence": canonical_clone_v1(item["period_evidence"]),
            "physical_page": item["record"]["physical_page"],
            "position": item["position"],
            "section_id": item["section_id"],
            "table_id": item["table_id"],
        }
        for item in inventory
    ]
    unit_context = _document_unit_context_v1(pages, compiled_specs=compiled_specs)
    first = pages[0]
    status = (
        NOT_OBSERVED
        if not inventory
        else READY
        if selected and not reasons and owner_receipt is not None
        else UNRESOLVED
    )
    material = {
        "component_regions": regions if status == READY else [],
        "declared_table_inventory": inventory_receipt,
        "document_id": first["document_id"],
        "document_ordinal": first["document_ordinal"],
        "document_unit_context_evidence": unit_context,
        "owner_receipt": owner_receipt,
        "reasons": sorted(set(reasons)),
        "source_logical_name": first["source_logical_name"],
        "source_sha256": first["source_sha256"],
        "status": status,
    }
    return {
        "cluster_id": "gjeqmfv1:cluster:" + canonical_json_sha256_v1(material),
        **material,
    }


def coalesce_gemini_json_equity_matrix_document_v1(
    *, page_records: Any, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Select one complete matrix under one bounded owner/reset fence."""

    if compiled_specs.get("exchange_rate_mode") is True:
        from bctc_ai.evaluation.gemini_json_categorical_period_matrix_v1 import (
            coalesce_gemini_json_categorical_period_matrix_document_v1,
        )

        return coalesce_gemini_json_categorical_period_matrix_document_v1(
            page_records=page_records, compiled_specs=compiled_specs
        )
    if compiled_specs.get("liquidity_risk_mode") is True:
        from bctc_ai.evaluation.gemini_json_liquidity_risk_matrix_v1 import (
            coalesce_gemini_json_liquidity_risk_document_v1,
        )

        return coalesce_gemini_json_liquidity_risk_document_v1(
            page_records=page_records, compiled_specs=compiled_specs
        )
    if compiled_specs.get("interest_rate_risk_mode") is True:
        from bctc_ai.evaluation.gemini_json_interest_rate_risk_matrix_v1 import (
            coalesce_gemini_json_interest_rate_risk_document_v1,
        )

        return coalesce_gemini_json_interest_rate_risk_document_v1(
            page_records=page_records, compiled_specs=compiled_specs
        )
    if compiled_specs.get("currency_risk_mode") is True:
        from bctc_ai.evaluation.gemini_json_currency_risk_matrix_v1 import (
            coalesce_gemini_json_currency_risk_document_v1,
        )

        return coalesce_gemini_json_currency_risk_document_v1(
            page_records=page_records, compiled_specs=compiled_specs
        )
    if compiled_specs.get("valuation_mode") is True:
        return _coalesce_valuation_matrix_document_v1(
            page_records=page_records, compiled_specs=compiled_specs
        )

    pages = _selected_page_record_axis(page_records)
    inventory = []
    owner_markers = []
    reset_markers = []
    for record in pages:
        for section_ordinal, section in enumerate(record["page_json"]["sections"], start=1):
            if type(section) is not dict:
                continue
            section_id = f"s{section_ordinal}"
            section_values = [(section.get("title_exact"), 0)]
            if type(section.get("narratives_exact")) is list:
                section_values.extend(
                    (source_exact, ordinal)
                    for ordinal, source_exact in enumerate(
                        section["narratives_exact"], start=1
                    )
                )
            for source_exact, source_ordinal in section_values:
                position = [
                    record["selected_page_ordinal"],
                    section_ordinal,
                    0,
                    source_ordinal,
                ]
                owner = _contained_declared_alias(
                    source_exact, compiled_specs["query_policy"]["owner_aliases"]
                )
                reset = _declared_reset_alias_v1(
                    source_exact,
                    [
                        *compiled_specs["query_policy"]["reset_aliases"],
                        *compiled_specs["query_policy"]["hard_negative_aliases"],
                    ],
                )
                if owner is not None:
                    owner_markers.append(
                        {"alias": owner, "position": position, "source_exact": source_exact}
                    )
                if reset is not None:
                    reset_markers.append(
                        {"alias": reset, "position": position, "source_exact": source_exact}
                    )
            tables = section.get("tables")
            if type(tables) is not list:
                continue
            for table_ordinal, table in enumerate(tables, start=1):
                if type(table) is not dict:
                    continue
                table_id = f"t{table_ordinal}"
                position = [
                    record["selected_page_ordinal"],
                    section_ordinal,
                    table_ordinal,
                    0,
                ]
                for source_exact in [table.get("title_exact")]:
                    owner = _contained_declared_alias(
                        source_exact, compiled_specs["query_policy"]["owner_aliases"]
                    )
                    reset = _declared_reset_alias_v1(
                        source_exact,
                        [
                            *compiled_specs["query_policy"]["reset_aliases"],
                            *compiled_specs["query_policy"]["hard_negative_aliases"],
                        ],
                    )
                    if owner is not None:
                        owner_markers.append(
                            {
                                "alias": owner,
                                "position": position,
                                "source_exact": source_exact,
                            }
                        )
                    if reset is not None:
                        reset_markers.append(
                            {
                                "alias": reset,
                                "position": position,
                                "source_exact": source_exact,
                            }
                        )
                classification = classify_gemini_json_equity_matrix_table_v1(
                    table, compiled_specs=compiled_specs
                )
                supplemental_owner = next(
                    (
                        {
                            "alias": alias,
                            "position": position,
                            "source_exact": source_exact,
                        }
                        for source_exact in (
                            table.get("title_exact"),
                            section.get("title_exact"),
                        )
                        if (
                            alias := _contained_declared_alias(
                                source_exact,
                                compiled_specs["supplemental_component_group_policy"][
                                    "owner_aliases"
                                ],
                            )
                        )
                        is not None
                    ),
                    None,
                )
                if (
                    classification["row_declared_component_roles"]
                    or classification["column_declared_component_roles"]
                ):
                    inventory.append(
                        {
                            "classification": classification,
                            "continuation": table.get("continuation"),
                            "position": position,
                            "record": record,
                            "section_title_exact": section.get("title_exact"),
                            "section_id": section_id,
                            "supplemental_owner": supplemental_owner,
                            "table": table,
                            "table_title_exact": table.get("title_exact"),
                            "table_id": table_id,
                        }
                    )
    # A role word on an unrelated statement/detail table is not evidence that
    # this family was observed.  Retain every complete matrix (so a missing
    # owner still fails closed), but retain an incomplete declared-role table
    # only when a bounded, reset-free explicit family owner governs it.
    def governed_incomplete_table(item: Mapping[str, Any]) -> bool:
        owners = [
            marker
            for marker in owner_markers
            if marker["position"] <= item["position"]
            and item["position"][0] - marker["position"][0]
            <= compiled_specs["query_policy"]["max_continuation_pages"]
        ]
        if not owners:
            return False
        owner = max(owners, key=lambda marker: marker["position"])
        return not any(
            owner["position"] < marker["position"] <= item["position"]
            for marker in reset_markers
        )

    inventory = [
        item
        for item in inventory
        if not (
            item["classification"].get("orientation") is None
            and len(
                {
                    *item["classification"].get(
                        "row_declared_component_roles", []
                    ),
                    *item["classification"].get(
                        "column_declared_component_roles", []
                    ),
                }
            )
            <= 1
            and any(
                column.get("value_kind") != "MONEY"
                for column in item["table"].get("columns", [])
            )
        )
        and (
            item["classification"]["status"] == "MATRIX_FRAGMENT"
            or governed_incomplete_table(item)
        )
    ]
    selected = [item for item in inventory if item["classification"]["status"] == "MATRIX_FRAGMENT"]
    authenticated_comparative_keys: set[tuple[str, str, str]] = set()
    period_selection_receipt = None
    reasons = []
    continuation_pair_receipt = None
    supplemental_pair_receipt = None
    continuation_pairs = []
    ordered_inventory = sorted(inventory, key=lambda item: item["position"])
    for first_item, second_item in zip(ordered_inventory, ordered_inventory[1:], strict=False):
        if (
            second_item["position"][0] - first_item["position"][0] != 1
            or second_item["record"]["physical_page"]
            - first_item["record"]["physical_page"]
            != 1
        ):
            continue
        plan = _component_row_continuation_plan_v1(
            tables=[first_item["table"], second_item["table"]],
            classifications=[
                first_item["classification"],
                second_item["classification"],
            ],
            compiled_specs=compiled_specs,
        )
        if plan is not None:
            continuation_pairs.append((first_item, second_item, plan))
    if len(continuation_pairs) == 1:
        first_item, second_item, plan = continuation_pairs[0]
        selected = [first_item, second_item]
        continuation_pair_receipt = {
            **canonical_clone_v1(plan["receipt"]),
            "fragment_positions": [
                canonical_clone_v1(first_item["position"]),
                canonical_clone_v1(second_item["position"]),
            ],
        }
    elif len(continuation_pairs) > 1:
        reasons.append("MULTIPLE_RECIPROCAL_COMPONENT_ROW_CONTINUATION_PAIRS")
    supplemental_pairs = []

    def supplemental_owner_for_pair(
        primary_item: Mapping[str, Any], supplemental_item: Mapping[str, Any]
    ) -> dict[str, Any] | None:
        direct = supplemental_item["supplemental_owner"]
        if direct is not None:
            return canonical_clone_v1(direct)
        if (
            supplemental_item["position"][0] - primary_item["position"][0] != 1
            or supplemental_item["record"]["physical_page"]
            - primary_item["record"]["physical_page"]
            != 1
        ):
            return None
        section_title = supplemental_item.get("section_title_exact")
        family_owner = _contained_declared_alias(
            section_title, compiled_specs["query_policy"]["owner_aliases"]
        )
        if (
            family_owner is not None
            and "tiep theo" in _normalized(section_title)
        ):
            return {
                "alias": family_owner,
                "position": canonical_clone_v1(supplemental_item["position"]),
                "rule": (
                    "ADJACENT_FAMILY_OWNER_CONTINUATION_PLUS_PRIMARY_DECLARED_"
                    "GROUP_RECONCILIATION"
                ),
                "source_exact": section_title,
            }
        if supplemental_item["continuation"] != "CONTINUES_FROM_PREVIOUS_PAGE":
            return None
        prior_group_owners = [
            item
            for item in ordered_inventory
            if item["position"] < supplemental_item["position"]
            and supplemental_item["position"][0] - item["position"][0] == 1
            and item["supplemental_owner"] is not None
            and same_typed_json_v1(
                _component_projection(item["classification"]["component_axis"]),
                _component_projection(
                    supplemental_item["classification"]["component_axis"]
                ),
            )
        ]
        if len(prior_group_owners) != 1:
            return None
        prior = prior_group_owners[0]
        return {
            **canonical_clone_v1(prior["supplemental_owner"]),
            "position": canonical_clone_v1(supplemental_item["position"]),
            "rule": (
                "STRUCTURED_FROM_PREVIOUS_PAGE_INHERITS_UNIQUE_ADJACENT_"
                "SUPPLEMENTAL_GROUP_OWNER_WITH_IDENTICAL_COMPONENT_AXIS"
            ),
        }

    for primary_item in ordered_inventory:
        for supplemental_item in ordered_inventory:
            if (
                supplemental_item["position"] <= primary_item["position"]
                or supplemental_item["position"][0] - primary_item["position"][0]
                > compiled_specs["query_policy"]["max_continuation_pages"]
            ):
                continue
            plan = _supplemental_component_group_plan_v1(
                tables=[primary_item["table"], supplemental_item["table"]],
                classifications=[
                    primary_item["classification"],
                    supplemental_item["classification"],
                ],
                compiled_specs=compiled_specs,
            )
            supplemental_owner = supplemental_owner_for_pair(
                primary_item, supplemental_item
            )
            if plan is not None and supplemental_owner is not None:
                supplemental_pairs.append(
                    (
                        primary_item,
                        {**supplemental_item, "supplemental_owner": supplemental_owner},
                        plan,
                    )
                )
    complete_supplemental_pairs = [
        item for item in supplemental_pairs if item[2]["mode"] == "COMPLETE_ROLLFORWARD_MATRIX"
    ]
    snapshot_supplemental_pairs = [
        item
        for item in supplemental_pairs
        if item[2]["mode"] == "EXPLICIT_OPENING_AND_CLOSING_PERIOD_SNAPSHOT"
    ]
    selected_supplemental_pair = None
    authenticated_snapshot_comparatives = []
    if len(complete_supplemental_pairs) == 1 and not snapshot_supplemental_pairs:
        selected_supplemental_pair = complete_supplemental_pairs[0]
    elif len(complete_supplemental_pairs) > 1 and not snapshot_supplemental_pairs:
        primary_positions = {
            tuple(primary_item["position"])
            for primary_item, _supplemental_item, _plan in complete_supplemental_pairs
        }

        def relative_balance_role(item: Mapping[str, Any]) -> str | None:
            role_surfaces: dict[str, list[str]] = {"OPENING": [], "CLOSING": []}
            for row_ordinal, row in enumerate(item["table"].get("rows", []), start=1):
                movement = _movement_surface_record(
                    members=[row.get("label_exact")]
                    if type(row.get("label_exact")) is str
                    else [],
                    axis_id=f"r{row_ordinal}",
                    axis_ordinal=row_ordinal,
                    source_ref={},
                    compiled_specs=compiled_specs,
                )
                for role in ("OPENING", "CLOSING"):
                    if role in movement["explicit_roles"]:
                        role_surfaces[role].append(
                            _normalized(row.get("label_exact"))
                        )
            if any(len(role_surfaces[role]) != 1 for role in role_surfaces):
                return None
            surfaces = [*role_surfaces["OPENING"], *role_surfaces["CLOSING"]]
            if all(re.search(r"\b(?:nam nay|ky nay)\b", value) for value in surfaces):
                return "CURRENT_RELATIVE_PERIOD"
            if all(re.search(r"\b(?:nam truoc|ky truoc)\b", value) for value in surfaces):
                return "COMPARATIVE_RELATIVE_PERIOD"
            return None

        current_pairs = [
            item
            for item in complete_supplemental_pairs
            if relative_balance_role(item[1]) == "CURRENT_RELATIVE_PERIOD"
        ]
        if len(primary_positions) == 1 and len(current_pairs) == 1:
            selected_supplemental_pair = current_pairs[0]
            authenticated_snapshot_comparatives = [
                item for item in complete_supplemental_pairs if item is not current_pairs[0]
            ]
            for _primary_item, comparative_item, _plan in authenticated_snapshot_comparatives:
                authenticated_comparative_keys.add(
                    (
                        comparative_item["record"]["page_json_version_id"],
                        comparative_item["section_id"],
                        comparative_item["table_id"],
                    )
                )
    elif snapshot_supplemental_pairs and not complete_supplemental_pairs:
        primary_positions = {
            tuple(primary_item["position"])
            for primary_item, _supplemental_item, _plan in snapshot_supplemental_pairs
        }
        child_role_axes = {
            tuple(plan["mapped_child_roles"])
            for _primary_item, _supplemental_item, plan in snapshot_supplemental_pairs
        }
        latest_period = max(
            plan["supplemental_period_date"]
            for _primary_item, _supplemental_item, plan in snapshot_supplemental_pairs
        )
        latest = [
            item
            for item in snapshot_supplemental_pairs
            if item[2]["supplemental_period_date"] == latest_period
        ]
        if len(primary_positions) == 1 and len(child_role_axes) == 1 and len(latest) == 1:
            selected_supplemental_pair = latest[0]
            authenticated_snapshot_comparatives = [
                item for item in snapshot_supplemental_pairs if item is not latest[0]
            ]
            for _primary_item, comparative_item, _plan in authenticated_snapshot_comparatives:
                authenticated_comparative_keys.add(
                    (
                        comparative_item["record"]["page_json_version_id"],
                        comparative_item["section_id"],
                        comparative_item["table_id"],
                    )
                )
    if selected_supplemental_pair is not None:
        primary_item, supplemental_item, plan = selected_supplemental_pair
        selected = [primary_item, supplemental_item]
        supplemental_pair_receipt = {
            **canonical_clone_v1(plan["receipt"]),
            "authenticated_comparative_snapshots": [
                {
                    "page_json_version_id": item[1]["record"]["page_json_version_id"],
                    "period_date": item[2]["supplemental_period_date"],
                    "position": canonical_clone_v1(item[1]["position"]),
                    "section_id": item[1]["section_id"],
                    "table_id": item[1]["table_id"],
                }
                for item in authenticated_snapshot_comparatives
            ],
            "fragment_positions": [
                canonical_clone_v1(primary_item["position"]),
                canonical_clone_v1(supplemental_item["position"]),
            ],
            "supplemental_owner": canonical_clone_v1(
                supplemental_item["supplemental_owner"]
            ),
        }
    elif supplemental_pairs:
        reasons.append("MULTIPLE_SUPPLEMENTAL_COMPONENT_GROUP_MATRIX_PAIRS")
    if (
        continuation_pair_receipt is None
        and supplemental_pair_receipt is None
        and len(selected) == 2
        and selected[0]["position"][:2] == selected[1]["position"][:2]
        and all(item["classification"]["orientation"] == "COMPONENT_ROWS" for item in selected)
        and same_typed_json_v1(
            _component_projection(selected[0]["classification"]["component_axis"]),
            _component_projection(selected[1]["classification"]["component_axis"]),
        )
    ):
        dated = []
        for item in selected:
            dates = sorted(
                date_item.isoformat()
                for date_item in _header_dates(item.get("table_title_exact") or "")
            )
            if len(dates) == 1:
                dated.append((dates[0], item))
        if len(dated) == 2 and dated[0][0] != dated[1][0]:
            dated.sort(key=lambda pair: pair[0])
            comparative = dated[0][1]
            current = dated[1][1]
            selected = [current]
            authenticated_comparative_keys.add(
                (
                    comparative["record"]["page_json_version_id"],
                    comparative["section_id"],
                    comparative["table_id"],
                )
            )
            period_selection_receipt = {
                "comparative_date": dated[0][0],
                "comparative_table_id": comparative["table_id"],
                "current_date": dated[1][0],
                "current_table_id": current["table_id"],
                "page_json_version_id": current["record"]["page_json_version_id"],
                "rule": "UNIQUE_LATEST_SOURCE_DATED_SAME_PAGE_COMPONENT_ROW_MATRIX",
            }
    elif (
        continuation_pair_receipt is None
        and supplemental_pair_receipt is None
        and len(selected) == 2
        and not (
            selected[0]["continuation"] == "CONTINUES_ON_NEXT_PAGE"
            and selected[1]["continuation"] == "CONTINUES_FROM_PREVIOUS_PAGE"
            and selected[1]["position"][0] - selected[0]["position"][0] == 1
            and selected[1]["record"]["physical_page"]
            - selected[0]["record"]["physical_page"]
            == 1
        )
        and all(
            item["classification"]["orientation"] == "COMPONENT_COLUMNS"
            for item in selected
        )
    ):
        dated = []
        for item in selected:
            _section, table = _source_table(
                item["record"]["page_json"],
                section_id=item["section_id"],
                table_id=item["table_id"],
            )
            boundary_dates = sorted(
                {
                    date_exact
                    for row_ordinal, row in enumerate(table["rows"], start=1)
                    for surface in [
                        _movement_surface_record(
                            members=[row.get("label_exact")]
                            if type(row.get("label_exact")) is str
                            else [],
                            axis_id=f"r{row_ordinal}",
                            axis_ordinal=row_ordinal,
                            source_ref={},
                            compiled_specs=compiled_specs,
                        )
                    ]
                    if surface["balance_marker"]
                    for date_exact in surface["dates"]
                }
            )
            if len(boundary_dates) >= 2:
                dated.append((boundary_dates[-1], item))
        if len(dated) == 2 and dated[0][0] != dated[1][0]:
            dated.sort(key=lambda pair: pair[0])
            comparative = dated[0][1]
            current = dated[1][1]
            selected = [current]
            authenticated_comparative_keys.add(
                (
                    comparative["record"]["page_json_version_id"],
                    comparative["section_id"],
                    comparative["table_id"],
                )
            )
            period_selection_receipt = {
                "comparative_date": dated[0][0],
                "comparative_table_id": comparative["table_id"],
                "current_date": dated[1][0],
                "current_table_id": current["table_id"],
                "page_json_version_id": current["record"]["page_json_version_id"],
                "rule": "UNIQUE_LATEST_SOURCE_DATED_COMPONENT_COLUMN_MATRIX",
            }
        else:
            reasons.append("MULTIPLE_UNAUTHENTICATED_COMPONENT_COLUMN_MATRICES_UNDER_OWNER")
    signed_fragments = [
        item
        for item in selected
        if item["classification"].get("matrix_mode") == "SIGNED_BRANCH_FRAGMENT"
    ]
    if signed_fragments:
        expected_branches = set(compiled_specs["signed_branch_multipliers"])
        occurrence_count = {
            branch_role: sum(
                branch_role in item["classification"].get("signed_branch_roles", [])
                for item in signed_fragments
            )
            for branch_role in expected_branches
        }
        if len(signed_fragments) != len(selected) or any(
            count != 1 for count in occurrence_count.values()
        ):
            reasons.append("SIGNED_BRANCH_EXACT_DECLARED_DOCUMENT_FRONTIER_REQUIRED")
    elif (
        continuation_pair_receipt is None
        and supplemental_pair_receipt is None
        and len(selected) > 1
        and all(
        item["classification"]["orientation"] == "COMPONENT_ROWS" for item in selected
        )
    ):
        # Two row-oriented tables are either an explicitly dated current /
        # comparative pair (reduced above) or an unresolved duplicate period
        # population.  Only signed branches have a declarative sibling
        # composition grammar; source order alone cannot choose or merge the
        # remaining ordinary tables.
        reasons.append("MULTIPLE_UNDATED_COMPONENT_ROW_MATRICES_UNDER_OWNER")
    if inventory and not selected:
        reasons.extend(
            reason for item in inventory for reason in item["classification"].get("reasons", [])
        )
        if not reasons:
            reasons.append("DECLARED_COMPONENT_EVIDENCE_NOT_COMPLETE_MATRIX")
    owner_receipt = None
    if selected:
        first_position = min(item["position"] for item in selected)
        last_position = max(item["position"] for item in selected)
        if len(selected) > 2:
            reasons.append("MORE_THAN_TWO_MATRIX_FRAGMENTS_UNDER_DOCUMENT_OWNER")
        if (
            last_position[0] - first_position[0]
            > compiled_specs["query_policy"]["max_continuation_pages"]
        ):
            reasons.append("MATRIX_FRAGMENT_SPAN_EXCEEDS_DECLARED_BOUND")
        prior_owners = [
            marker
            for marker in owner_markers
            if marker["position"] <= first_position
            and first_position[0] - marker["position"][0]
            <= compiled_specs["query_policy"]["max_continuation_pages"]
        ]
        implicit_policy = compiled_specs["implicit_owner_policy"]
        if (
            not prior_owners
            and implicit_policy["mode"]
            == "UNIQUE_COMPLETE_MATRIX_PLUS_SUPPLEMENTAL_COMPONENT_GROUP"
            and supplemental_pair_receipt is not None
            and len(selected) == 2
            and len(
                selected[0]["classification"].get(
                    "mapped_component_roles", []
                )
            )
            >= implicit_policy["minimum_mapped_component_roles"]
        ):
            prior_owners = [
                {
                    "alias": "STRUCTURAL_EQUITY_MATRIX",
                    "position": canonical_clone_v1(first_position),
                    "rule": (
                        "UNIQUE_COMPLETE_HIGH_DIMENSION_EQUITY_MATRIX_PLUS_"
                        "SUPPLEMENTAL_COMPONENT_GROUP_RECONCILIATION"
                    ),
                    "source_exact": selected[0].get("section_title_exact")
                    or selected[0].get("table_title_exact"),
                }
            ]
        if not prior_owners:
            reasons.append("EXPLICIT_BOUNDED_MATRIX_OWNER_NOT_VISIBLE")
        else:
            owner = max(prior_owners, key=lambda item: item["position"])
            fenced_resets = [
                marker
                for marker in reset_markers
                if owner["position"] < marker["position"] <= last_position
                and not (
                    marker["position"][2:] != [0, 0]
                    and marker["position"][2] == 0
                    and any(
                        item["position"][:2] == marker["position"][:2]
                        for item in selected
                    )
                )
            ]
            authorized_supplemental_resets = []
            if supplemental_pair_receipt is not None:
                supplemental_owner_position = supplemental_pair_receipt[
                    "supplemental_owner"
                ]["position"]
                authorized_supplemental_resets = [
                    marker
                    for marker in fenced_resets
                    if marker["position"] < supplemental_owner_position
                ]
                fenced_resets = [
                    marker
                    for marker in fenced_resets
                    if marker not in authorized_supplemental_resets
                ]
            if fenced_resets:
                reasons.append("OWNER_TO_MATRIX_INTERVAL_CONTAINS_RESET_OR_HARD_NEGATIVE")
            owner_receipt = {
                "owner_alias": owner["alias"],
                "owner_position": owner["position"],
                "owner_source_exact": owner["source_exact"],
                "reset_fence_axis": fenced_resets,
                "rule": owner.get(
                    "rule", "LATEST_EXPLICIT_OWNER_WITHIN_ONE_PAGE_RESET_FREE_INTERVAL"
                ),
            }
            if authorized_supplemental_resets:
                owner_receipt["authorized_supplemental_reset_axis"] = canonical_clone_v1(
                    authorized_supplemental_resets
                )
            if period_selection_receipt is not None:
                owner_receipt["period_selection_receipt"] = period_selection_receipt
            if continuation_pair_receipt is not None:
                owner_receipt["component_row_continuation_receipt"] = (
                    continuation_pair_receipt
                )
            if supplemental_pair_receipt is not None:
                owner_receipt["supplemental_component_group_receipt"] = (
                    supplemental_pair_receipt
                )
            selected_keys = {
                (
                    item["record"]["page_json_version_id"],
                    item["section_id"],
                    item["table_id"],
                )
                for item in selected
            }
            max_scope_page = (
                first_position[0] + compiled_specs["query_policy"]["max_continuation_pages"]
            )
            unconsumed = [
                item
                for item in inventory
                if owner["position"] <= item["position"]
                and item["position"][0] <= max_scope_page
                and not any(
                    owner["position"] < marker["position"] <= item["position"]
                    or (
                        marker["position"][:2] == item["position"][:2]
                        and marker["position"][2] == 0
                        and any(
                            selected_item["position"][:2] == item["position"][:2]
                            and 0 < selected_item["position"][2] < item["position"][2]
                            for selected_item in selected
                        )
                    )
                    for marker in reset_markers
                )
                and (
                    item["record"]["page_json_version_id"],
                    item["section_id"],
                    item["table_id"],
                )
                not in selected_keys
                and (
                    item["record"]["page_json_version_id"],
                    item["section_id"],
                    item["table_id"],
                )
                not in authenticated_comparative_keys
            ]
            if unconsumed:
                reasons.append("UNCONSUMED_DECLARED_COMPONENT_EVIDENCE_IN_OWNER_INTERVAL")
    regions = [
        _matrix_region(item, fragment_ordinal=ordinal)
        for ordinal, item in enumerate(selected, start=1)
    ]
    if regions:
        try:
            _checked_region_axis(regions)
        except GeminiJsonEquityMatrixAccountingFamilyV1Error:
            reasons.append("MATRIX_REGION_AXIS_IS_NOT_ONE_OR_TWO_ADJACENT_FRAGMENTS")
    inventory_receipt = [
        {
            "classification": canonical_clone_v1(item["classification"]),
            "continuation": item["continuation"],
            "disposition": (
                "SELECTED_MATRIX_FRAGMENT"
                if item in selected
                else "AUTHENTICATED_COMPARATIVE_MATRIX_FRAGMENT"
                if (
                    item["record"]["page_json_version_id"],
                    item["section_id"],
                    item["table_id"],
                )
                in authenticated_comparative_keys
                else "UNSELECTED_DECLARED_ROLE_TABLE"
            ),
            "page_json_version_id": item["record"]["page_json_version_id"],
            "physical_page": item["record"]["physical_page"],
            "position": item["position"],
            "section_id": item["section_id"],
            "table_id": item["table_id"],
        }
        for item in inventory
    ]
    unit_context = _document_unit_context_v1(
        pages,
        compiled_specs=compiled_specs,
        target_tables=[item["table"] for item in selected],
    )
    first = pages[0]
    status = (
        NOT_OBSERVED
        if not selected and not inventory
        else READY
        if selected and not reasons and owner_receipt is not None
        else UNRESOLVED
    )
    material = {
        "component_regions": regions if status == READY else [],
        "declared_table_inventory": inventory_receipt,
        "document_id": first["document_id"],
        "document_ordinal": first["document_ordinal"],
        "document_unit_context_evidence": unit_context,
        "owner_receipt": owner_receipt,
        "reasons": sorted(set(reasons)),
        "source_logical_name": first["source_logical_name"],
        "source_sha256": first["source_sha256"],
        "status": status,
    }
    return {
        "cluster_id": "gjeqmfv1:cluster:" + canonical_json_sha256_v1(material),
        **material,
    }


def build_gemini_json_indexed_equity_matrix_query_evidence_v1(
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
            "cluster": canonical_clone_v1(cluster),
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
        "accepted_fragment_count": sum(len(item.get("component_regions", [])) for item in accepted),
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
        "query_evidence_id": "gjeqmfv1:evidence:" + canonical_json_sha256_v1(material),
    }


def validate_gemini_json_indexed_equity_matrix_query_evidence_v1(
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
        raise _error("indexed equity-matrix query evidence is invalid")
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
        raise _error("indexed equity-matrix document axis is incomplete")
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
            raise _error("indexed equity-matrix selected document axis is invalid")
        by_ordinal[ordinal] = document
    page_fields = document_fields | {
        "page_json_version_id",
        "physical_page",
        "selected_page_ordinal",
    }
    per_document: dict[int, int] = {}
    page_versions = []
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
            raise _error("indexed equity-matrix selected page axis is invalid")
        prior_document = page["document_ordinal"]
        per_document[page["document_ordinal"]] = per_document.get(page["document_ordinal"], 0) + 1
        if page.get("selected_page_ordinal") != per_document[page["document_ordinal"]]:
            raise _error("indexed equity-matrix selected page order is incomplete")
        page_versions.append(page["page_json_version_id"])
    if len(page_versions) != len(set(page_versions)) or set(per_document) != set(by_ordinal):
        raise _error("indexed equity-matrix page frontier is duplicate or incomplete")
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
            != "gjeqmfv1:cluster:"
            + canonical_json_sha256_v1(
                {key: item for key, item in cluster.items() if key != "cluster_id"}
            )
        ):
            raise _error("indexed equity-matrix cluster binding drifted")
        regions = cluster.get("component_regions")
        reasons = cluster.get("reasons")
        if (
            type(reasons) is not list
            or reasons != sorted(set(reasons))
            or type(cluster.get("document_unit_context_evidence")) is not dict
            or (cluster["status"] == READY and (not regions or reasons))
            or (cluster["status"] == NOT_OBSERVED and regions)
            or (cluster["status"] == UNRESOLVED and (not reasons or regions))
        ):
            raise _error("indexed equity-matrix disposition semantics drifted")
        if cluster["status"] == READY:
            _checked_region_axis(regions)
            accepted.append(cluster)
    if not same_typed_json_v1(value["accepted_clusters"], accepted):
        raise _error("indexed equity-matrix accepted projection drifted")
    expected_receipt = {
        "accepted_cluster_axis_sha256": canonical_json_sha256_v1(accepted),
        "accepted_cluster_count": len(accepted),
        "accepted_fragment_count": sum(len(item["component_regions"]) for item in accepted),
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
        raise _error("indexed equity-matrix query receipt drifted")
    material = {key: canonical_clone_v1(value[key]) for key in fields - {"query_evidence_id"}}
    if value["query_evidence_id"] != "gjeqmfv1:evidence:" + canonical_json_sha256_v1(material):
        raise _error("indexed equity-matrix query evidence identity drifted")
    return canonical_clone_v1(value)


def _validate_valuation_matrix_candidate_binding_v1(
    candidate: Any,
    *,
    document: Mapping[str, Any],
    cluster: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Seal the self-contained valuation graph before SQLite source replay."""

    candidate_fields = {
        "candidate_id",
        "claim_boundary",
        "closure_receipt",
        "component_regions",
        "document_id",
        "family_id",
        "mappings",
        "page_json_version_id",
        "physical_page",
        "reasons",
        "section_id",
        "source_logical_name",
        "source_sha256",
        "status",
        "table_id",
    }
    closure_fields = {
        "equations",
        "matrix_kind",
        "period_assignments",
        "query_receipt",
        "rule",
        "table_receipts",
        "unit_receipt",
    }
    table_receipt_fields = {
        "classification",
        "period_assignment",
        "region",
        "resolved_rows",
    }
    unit_fields = {
        "canonical_unit",
        "document_unit_context_evidence",
        "fragment_unit_axes",
        "source",
    }
    local_unit_fields = {
        "canonical_unit",
        "complete",
        "conflicting_surfaces",
        "evidence",
        "reasons",
        "source",
        "undeclared_evidence",
    }
    row_axis_fields = {
        "branch",
        "kind",
        "label_exact",
        "role",
        "role_matches",
        "row_id",
        "row_kind",
        "source_order",
    }
    row_equation_fields = {
        "computed_value",
        "equation_kind",
        "result_cell",
        "row_id",
        "status",
        "term_cells",
    }
    branch_equation_fields = {
        "computed_value",
        "equation_kind",
        "result_cell",
        "status",
        "term_cells",
    }
    regions = cluster["component_regions"]
    first = regions[0]
    closure = candidate.get("closure_receipt") if type(candidate) is dict else None
    if (
        type(candidate) is not dict
        or set(candidate) != candidate_fields
        or candidate.get("claim_boundary") != VALUATION_CLAIM_BOUNDARY
        or candidate.get("family_id") != compiled_specs["family_id"]
        or candidate.get("document_id") != first["document_id"]
        or candidate.get("page_json_version_id") != first["page_json_version_id"]
        or candidate.get("physical_page") != first["physical_page"]
        or candidate.get("section_id") != first["section_id"]
        or candidate.get("table_id") != first["table_id"]
        or candidate.get("source_logical_name") != document["source_logical_name"]
        or candidate.get("source_sha256") != document["source_sha256"]
        or not same_typed_json_v1(candidate.get("component_regions"), regions)
        or candidate.get("status") not in {READY, UNRESOLVED}
        or type(candidate.get("reasons")) is not list
        or candidate["reasons"] != sorted(set(candidate["reasons"]))
        or type(candidate.get("mappings")) is not list
        or type(closure) is not dict
        or set(closure) != closure_fields
        or closure.get("matrix_kind") != "VALUATION_CLASSIFICATION"
        or closure.get("rule")
        != "EXACT_FIXED_OR_UNIQUE_PACKED_ROWS_AND_ASSET_LIABILITY_BRANCH_TOTALS"
        or type(closure.get("equations")) is not list
        or type(closure.get("period_assignments")) is not list
        or type(closure.get("table_receipts")) is not list
        or type(closure.get("unit_receipt")) is not dict
        or set(closure["unit_receipt"]) != unit_fields
    ):
        raise _error("valuation-matrix candidate structure drifted")
    expected_query = build_gemini_json_equity_matrix_region_query_receipt_v1(
        regions, owner_receipt=cluster["owner_receipt"]
    )
    if not same_typed_json_v1(closure["query_receipt"], expected_query):
        raise _error("valuation-matrix candidate query receipt drifted")
    expected_period_assignments = cluster["owner_receipt"].get("period_assignments")
    if not same_typed_json_v1(closure["period_assignments"], expected_period_assignments):
        raise _error("valuation-matrix candidate period assignments drifted")
    unit_receipt = closure["unit_receipt"]
    if (
        not same_typed_json_v1(
            unit_receipt["document_unit_context_evidence"],
            cluster["document_unit_context_evidence"],
        )
        or type(unit_receipt["fragment_unit_axes"]) is not list
        or len(unit_receipt["fragment_unit_axes"]) != len(regions)
        or any(
            type(axis) is not dict
            or set(axis) != local_unit_fields
            or type(axis.get("complete")) is not bool
            or type(axis.get("conflicting_surfaces")) is not list
            or type(axis.get("evidence")) is not list
            or type(axis.get("reasons")) is not list
            or axis["reasons"] != sorted(set(axis["reasons"]))
            or type(axis.get("undeclared_evidence")) is not list
            for axis in unit_receipt["fragment_unit_axes"]
        )
    ):
        raise _error("valuation-matrix unit receipt drifted")
    material = {key: value for key, value in candidate.items() if key != "candidate_id"}
    if candidate["candidate_id"] != "gjeqmfv1:candidate:" + canonical_json_sha256_v1(material):
        raise _error("valuation-matrix candidate identity drifted")

    inventory_by_locator = {
        (
            item["page_json_version_id"],
            item["section_id"],
            item["table_id"],
        ): item
        for item in cluster.get("declared_table_inventory", [])
        if type(item) is dict and item.get("disposition") == "SELECTED_VALUATION_FRAGMENT"
    }
    assignment_by_locator = {
        (
            item["page_json_version_id"],
            item["section_id"],
            item["table_id"],
        ): item
        for item in closure["period_assignments"]
        if type(item) is dict
    }
    if (
        len(inventory_by_locator) != len(regions)
        or len(assignment_by_locator) != len(regions)
        or len(closure["table_receipts"]) != len(regions)
    ):
        raise _error("valuation-matrix candidate table frontier drifted")

    expected_equations = []
    role_period_cells: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    total_period_cells: dict[tuple[str, str], dict[str, Any]] = {}
    for table_receipt, region in zip(closure["table_receipts"], regions, strict=True):
        locator = (
            region["page_json_version_id"],
            region["section_id"],
            region["table_id"],
        )
        inventory = inventory_by_locator.get(locator)
        assignment = assignment_by_locator.get(locator)
        if (
            type(table_receipt) is not dict
            or set(table_receipt) != table_receipt_fields
            or inventory is None
            or assignment is None
            or not same_typed_json_v1(table_receipt["region"], region)
            or not same_typed_json_v1(table_receipt["classification"], inventory["classification"])
            or not same_typed_json_v1(table_receipt["period_assignment"], assignment)
            or type(table_receipt["resolved_rows"]) is not list
        ):
            raise _error("valuation-matrix table receipt drifted")
        classification = table_receipt["classification"]
        expected_row_axes = [
            item
            for item in classification.get("component_axis", [])
            if item.get("kind") in {"MAPPED_COMPONENT", "BRANCH_TOTAL"}
        ]
        resolved_rows = table_receipt["resolved_rows"]
        if len(resolved_rows) > len(expected_row_axes):
            raise _error("valuation-matrix resolved row axis is overcomplete")
        expected_by_row = {item["row_id"]: item for item in expected_row_axes}
        seen_rows = set()
        for resolved in resolved_rows:
            row_id = resolved.get("row_id") if type(resolved) is dict else None
            expected_axis = expected_by_row.get(row_id)
            optional_fields = (
                {"ignored_packed_zero_cells"}
                if type(resolved) is dict and "ignored_packed_zero_cells" in resolved
                else set()
            )
            expected_fields = (
                row_axis_fields
                | {
                    "alignment_mode",
                    "book_total_cell",
                    "classification_cells",
                    "equation",
                    "fair_value_cell",
                }
                | optional_fields
            )
            if (
                type(resolved) is not dict
                or set(resolved) != expected_fields
                or expected_axis is None
                or row_id in seen_rows
                or not same_typed_json_v1(
                    {key: resolved[key] for key in row_axis_fields}, expected_axis
                )
                or type(resolved["classification_cells"]) is not list
                or not resolved["classification_cells"]
                or type(resolved["book_total_cell"]) is not dict
                or resolved["fair_value_cell"] is not None
                and type(resolved["fair_value_cell"]) is not dict
                or type(resolved["equation"]) is not dict
                or set(resolved["equation"]) != row_equation_fields
            ):
                raise _error("valuation-matrix resolved row receipt drifted")
            seen_rows.add(row_id)
            cells = [
                *resolved["classification_cells"],
                resolved["book_total_cell"],
                *([resolved["fair_value_cell"]] if resolved["fair_value_cell"] is not None else []),
                *resolved.get("ignored_packed_zero_cells", []),
            ]
            for cell in cells:
                ref = cell.get("cell_ref") if type(cell) is dict else None
                if (
                    type(cell) is not dict
                    or set(cell) != {"cell_ref", "coefficient", "source_text", "state"}
                    or type(cell.get("state")) is not str
                    or not cell["state"]
                    or cell.get("source_text") is not None
                    and type(cell["source_text"]) is not str
                    or cell.get("coefficient") is not None
                    and type(cell["coefficient"]) is not int
                    or type(ref) is not dict
                    or set(ref) != {"column_id", "locator", "row_id"}
                    or ref.get("row_id") != row_id
                    or _COLUMN_ID.fullmatch(ref.get("column_id", "")) is None
                    or not same_typed_json_v1(ref.get("locator"), region)
                ):
                    raise _error("valuation-matrix resolved cell provenance drifted")
            expected_row_equation = {
                "computed_value": sum(
                    cell["coefficient"] for cell in resolved["classification_cells"]
                ),
                "equation_kind": "CLASSIFICATION_CELLS_EQUAL_BOOK_TOTAL",
                "result_cell": canonical_clone_v1(resolved["book_total_cell"]),
                "row_id": row_id,
                "status": "EXACT",
                "term_cells": canonical_clone_v1(resolved["classification_cells"]),
            }
            if (
                any(
                    type(cell.get("coefficient")) is not int
                    for cell in resolved["classification_cells"]
                )
                or type(resolved["book_total_cell"].get("coefficient")) is not int
                or expected_row_equation["computed_value"]
                != resolved["book_total_cell"]["coefficient"]
                or not same_typed_json_v1(resolved["equation"], expected_row_equation)
            ):
                raise _error("valuation-matrix row equation drifted")
            expected_equations.append(expected_row_equation)
            if resolved["kind"] == "MAPPED_COMPONENT":
                role_period_cells.setdefault(
                    (resolved["role"], assignment["period_role"], "CARRYING_VALUE"),
                    [],
                ).append(resolved["book_total_cell"])
                fair = resolved["fair_value_cell"]
                if fair is not None and fair.get("state") in {
                    "RAW_SIGNED_INTEGER",
                    "NORMALIZED_SINGLE_NUMERIC_TOKEN_ROW_GRAPH_EXACT",
                }:
                    role_period_cells.setdefault(
                        (resolved["role"], assignment["period_role"], "FAIR_VALUE"),
                        [],
                    ).append(fair)
            else:
                total_key = (resolved["role"], assignment["period_role"])
                if total_key in total_period_cells:
                    raise _error("valuation-matrix branch total is duplicate")
                total_period_cells[total_key] = resolved["book_total_cell"]
                fair = resolved["fair_value_cell"]
                if fair is not None and fair.get("state") in {
                    "RAW_SIGNED_INTEGER",
                    "NORMALIZED_SINGLE_NUMERIC_TOKEN_ROW_GRAPH_EXACT",
                }:
                    role_period_cells.setdefault(
                        (resolved["role"], assignment["period_role"], "FAIR_VALUE"), []
                    ).append(fair)
        for branch in ("ASSET", "LIABILITY"):
            item_cells = [
                row["book_total_cell"]
                for row in resolved_rows
                if row["branch"] == branch and row["kind"] == "MAPPED_COMPONENT"
            ]
            total_rows = [
                row
                for row in resolved_rows
                if row["branch"] == branch and row["kind"] == "BRANCH_TOTAL"
            ]
            if len(total_rows) == 1 and item_cells:
                result_cell = total_rows[0]["book_total_cell"]
                computed = sum(cell["coefficient"] for cell in item_cells)
                expected_equations.append(
                    {
                        "computed_value": computed,
                        "equation_kind": f"{branch}_ITEM_BOOK_TOTALS_EQUAL_BRANCH_TOTAL",
                        "result_cell": canonical_clone_v1(result_cell),
                        "status": "EXACT" if computed == result_cell["coefficient"] else "MISMATCH",
                        "term_cells": canonical_clone_v1(item_cells),
                    }
                )
    if any(
        type(item) is not dict or set(item) not in (row_equation_fields, branch_equation_fields)
        for item in closure["equations"]
    ) or not same_typed_json_v1(closure["equations"], expected_equations):
        raise _error("valuation-matrix closure equation axis drifted")

    if candidate["status"] == READY:
        canonical_unit = unit_receipt.get("canonical_unit")
        if (
            candidate["reasons"]
            or type(canonical_unit) is not str
            or not canonical_unit
            or any(
                len(receipt["resolved_rows"])
                != len(
                    [
                        item
                        for item in receipt["classification"]["component_axis"]
                        if item["kind"] in {"MAPPED_COMPONENT", "BRANCH_TOTAL"}
                    ]
                )
                for receipt in closure["table_receipts"]
            )
            or any(item.get("status") != "EXACT" for item in expected_equations)
        ):
            raise _error("valuation-matrix READY closure is incomplete")
        expected_mappings = _build_valuation_mappings_v1(
            compiled_specs=compiled_specs,
            canonical_unit=canonical_unit,
            period_assignments=closure["period_assignments"],
            role_period_cells=role_period_cells,
            total_period_cells=total_period_cells,
        )
        if not same_typed_json_v1(candidate["mappings"], expected_mappings):
            raise _error("valuation-matrix schema mapping axis drifted")
    elif candidate["mappings"] or not candidate["reasons"]:
        raise _error("valuation-matrix unresolved candidate semantics drifted")
    return candidate


def validate_gemini_json_equity_matrix_sweep_query_bindings_v1(
    *, trials: Any, indexed_query_evidence: Any, compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    evidence = validate_gemini_json_indexed_equity_matrix_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
    documents = evidence["selected_document_axis"]
    if type(trials) is not list or len(trials) != len(documents):
        raise _error("equity-matrix sweep trial axis is incomplete")
    accepted = {item["document_ordinal"]: item for item in evidence["accepted_clusters"]}
    trial_fields = {
        "candidate_count",
        "candidates",
        "document_ordinal",
        "mappings",
        "reasons",
        "selected_candidate_id",
        "source_logical_name",
        "source_sha256",
        "status",
    }
    candidate_fields = {
        "candidate_id",
        "claim_boundary",
        "closure_receipt",
        "component_regions",
        "document_id",
        "family_id",
        "mappings",
        "page_json_version_id",
        "physical_page",
        "reasons",
        "section_id",
        "source_logical_name",
        "source_sha256",
        "status",
        "table_id",
    }
    closure_fields = {
        "alignment_receipts",
        "component_axis",
        "equations",
        "movement_axis",
        "omitted_all_blank_mapping_roles",
        "orientation",
        "period_block_receipt",
        "query_receipt",
        "rule",
        "source_only_component_axes",
        "source_repair_receipts",
        "unit_receipt",
    }
    mapping_fields = {
        "item_mapping_id",
        "report_norm_id",
        "role",
        "row_id",
        "unit",
        "values",
    }
    value_fields = {
        "axis_role",
        "cell_ref",
        "coefficient",
        "equation_multiplier",
        "source_text",
        "state",
    }

    def validate_candidate(
        candidate: Any, *, document: Mapping[str, Any], cluster: Mapping[str, Any]
    ) -> dict[str, Any]:
        if compiled_specs.get("exchange_rate_mode") is True:
            from bctc_ai.evaluation.gemini_json_categorical_period_matrix_v1 import (
                validate_gemini_json_categorical_period_matrix_candidate_binding_v1,
            )

            return validate_gemini_json_categorical_period_matrix_candidate_binding_v1(
                candidate,
                document=document,
                cluster=cluster,
                compiled_specs=compiled_specs,
            )
        if compiled_specs.get("currency_risk_mode") is True:
            from bctc_ai.evaluation.gemini_json_currency_risk_matrix_v1 import (
                validate_gemini_json_currency_risk_candidate_binding_v1,
            )

            return validate_gemini_json_currency_risk_candidate_binding_v1(
                candidate,
                document=document,
                cluster=cluster,
                compiled_specs=compiled_specs,
            )
        if compiled_specs.get("valuation_mode") is True:
            return _validate_valuation_matrix_candidate_binding_v1(
                candidate,
                document=document,
                cluster=cluster,
                compiled_specs=compiled_specs,
            )
        regions = cluster["component_regions"]
        first = regions[0]
        closure = candidate.get("closure_receipt") if type(candidate) is dict else None
        signed_closure = type(closure) is dict and "signed_branch_receipt" in closure
        expected_closure_fields = closure_fields | (
            {"signed_branch_receipt"} if signed_closure else set()
        )
        candidate_status = candidate.get("status") if type(candidate) is dict else None
        if (
            type(candidate) is not dict
            or set(candidate) != candidate_fields
            or candidate.get("claim_boundary") != CLAIM_BOUNDARY
            or candidate.get("family_id") != compiled_specs["family_id"]
            or candidate.get("document_id") != first["document_id"]
            or candidate.get("page_json_version_id") != first["page_json_version_id"]
            or candidate.get("physical_page") != first["physical_page"]
            or candidate.get("section_id") != first["section_id"]
            or candidate.get("table_id") != first["table_id"]
            or candidate.get("source_logical_name") != document["source_logical_name"]
            or candidate.get("source_sha256") != document["source_sha256"]
            or not same_typed_json_v1(candidate.get("component_regions"), regions)
            or candidate_status not in {READY, UNRESOLVED}
            or type(candidate.get("reasons")) is not list
            or candidate["reasons"] != sorted(set(candidate["reasons"]))
            or type(candidate.get("mappings")) is not list
            or type(closure) is not dict
            or set(closure) != expected_closure_fields
            or signed_closure != bool(compiled_specs["signed_branch_multipliers"])
            and signed_closure
            or signed_closure
            and type(closure.get("signed_branch_receipt")) is not dict
            or closure.get("orientation")
            not in {None, "COMPONENT_COLUMNS", "COMPONENT_ROWS"}
            or type(closure.get("component_axis")) is not list
            or type(closure.get("movement_axis")) is not list
            or type(closure.get("equations")) is not list
            or type(closure.get("alignment_receipts")) is not list
            or type(closure.get("source_only_component_axes")) is not list
            or type(closure.get("source_repair_receipts")) is not list
            or type(closure.get("omitted_all_blank_mapping_roles")) is not list
            or closure.get("omitted_all_blank_mapping_roles")
            != sorted(set(closure.get("omitted_all_blank_mapping_roles", [])))
            or any(
                type(role) is not str or not role
                for role in closure.get("omitted_all_blank_mapping_roles", [])
            )
            or type(closure.get("unit_receipt")) is not dict
            or (
                candidate_status == READY
                and closure["orientation"] == "COMPONENT_COLUMNS"
                and type(closure.get("period_block_receipt")) is not dict
            )
            or (
                closure["orientation"] == "COMPONENT_ROWS"
                and closure.get("period_block_receipt") is not None
            )
            or (
                closure["orientation"] is None
                and closure.get("period_block_receipt") is not None
            )
            or (candidate_status == READY and closure["orientation"] is None)
        ):
            raise _error("equity-matrix candidate structure drifted")
        expected_query = build_gemini_json_equity_matrix_region_query_receipt_v1(
            regions, owner_receipt=cluster["owner_receipt"]
        )
        if not same_typed_json_v1(closure["query_receipt"], expected_query):
            raise _error("equity-matrix candidate query receipt drifted")
        material = {key: value for key, value in candidate.items() if key != "candidate_id"}
        if candidate["candidate_id"] != "gjeqmfv1:candidate:" + canonical_json_sha256_v1(material):
            raise _error("equity-matrix candidate identity drifted")
        if candidate_status == UNRESOLVED:
            if candidate["mappings"] or not candidate["reasons"]:
                raise _error("equity-matrix unresolved candidate semantics drifted")
            return candidate
        component_axis = closure["component_axis"]
        mapped_component_kinds = {
            "MAPPED_COMPONENT",
            "MAPPED_COMPONENT_GROUP_TOTAL",
            "MAPPED_SUPPLEMENTAL_COMPONENT",
        }
        mapped_source_by_role: dict[str, list[dict[str, Any]]] = {}
        for item in component_axis:
            if type(item) is dict and item.get("kind") in mapped_component_kinds:
                mapped_source_by_role.setdefault(item.get("role"), []).append(item)
        allowed_aggregates = set(compiled_specs["hierarchy_policy"]["aggregate_duplicate_roles"])
        mapped_components = {
            role: (
                items[0]
                if len(items) == 1
                else _aggregate_component_axis_v1(role=role, items=items)
            )
            for role, items in mapped_source_by_role.items()
        }
        if (
            None in mapped_components
            or any(
                len(items) > 1 and role not in allowed_aggregates
                for role, items in mapped_source_by_role.items()
            )
            or sum(
                type(item) is dict and item.get("kind") == "GRAND_TOTAL" for item in component_axis
            )
            != 1
        ):
            raise _error("equity-matrix candidate component axis drifted")
        movement_roles = [
            item.get("axis_role") for item in closure["movement_axis"] if type(item) is dict
        ]
        expected_axis_roles = (
            [
                role
                for role in movement_roles
                if role in _MAPPED_MOVEMENT_ROLES
                or role in compiled_specs["mapped_supplemental_movement_roles"]
            ]
            if closure["orientation"] == "COMPONENT_ROWS"
            else [
                "OPENING",
                *[role for role in ("INCREASE", "DECREASE") if role in movement_roles],
                "CLOSING",
            ]
        )
        vector_root_mode = (
            compiled_specs["root_mapping_policy"]
            == "SOURCE_VISIBLE_MATRIX_GRAND_TOTAL_VECTOR_WITH_COMPONENT_VECTORS"
        )
        expected_total_roles = (
            set()
            if vector_root_mode
            else {_MAPPED_TOTAL_ROLES[role] for role in expected_axis_roles}
        )
        expected_root_roles = {"FAMILY_TOTAL"} if vector_root_mode else set()
        expected_roles = set(mapped_components) | expected_total_roles | expected_root_roles
        omitted_roles = set(closure["omitted_all_blank_mapping_roles"])
        if not omitted_roles <= expected_roles:
            raise _error("equity-matrix omitted mapping role axis drifted")
        supplemental_components = [
            item
            for item in component_axis
            if type(item) is dict and item.get("kind") == "MAPPED_SUPPLEMENTAL_COMPONENT"
        ]
        supplemental_mapping_axis: list[str] | None = None
        if supplemental_components:
            supplemental_receipts = [
                item
                for item in closure["alignment_receipts"]
                if type(item) is dict
                and item.get("rule")
                == (
                    "PRIMARY_EQUITY_MATRIX_PLUS_EXPLICIT_SUPPLEMENTAL_COMPONENT_"
                    "GROUP_MATRIX_RECONCILE_BEFORE_CHILD_PROJECTION"
                )
            ]
            if len(supplemental_receipts) != 1:
                raise _error("equity-matrix supplemental mapping receipt axis drifted")
            supplemental_receipt = supplemental_receipts[0]
            supplemental_equations = supplemental_receipt.get("supplemental_equations")
            mapped_child_roles = supplemental_receipt.get("mapped_child_roles")
            if (
                type(supplemental_equations) is not list
                or type(mapped_child_roles) is not list
                or any(type(role) is not str or not role for role in mapped_child_roles)
                or len(set(mapped_child_roles)) != len(mapped_child_roles)
                or {item.get("role") for item in supplemental_components}
                - set(mapped_child_roles)
            ):
                raise _error("equity-matrix supplemental mapping receipt axis drifted")
            supplemental_mapping_axis = []
            for equation in supplemental_equations:
                if (
                    type(equation) is not dict
                    or equation.get("equation_kind") != "VISIBLE_GRAND_HORIZONTAL_TOTAL"
                ):
                    continue
                axis_role = equation.get("axis_role")
                if (
                    type(axis_role) is not str
                    or not axis_role
                    or axis_role in supplemental_mapping_axis
                ):
                    raise _error("equity-matrix supplemental movement axis drifted")
                supplemental_mapping_axis.append(axis_role)
            if not supplemental_mapping_axis:
                raise _error("equity-matrix supplemental movement axis drifted")
        grand_total = next(
            item
            for item in component_axis
            if type(item) is dict and item.get("kind") == "GRAND_TOTAL"
        )
        canonical_unit = closure["unit_receipt"].get("canonical_unit")
        seen_roles = set()
        region_hashes = {canonical_json_sha256_v1(item) for item in regions}
        for mapping in candidate["mappings"]:
            role = mapping.get("role") if type(mapping) is dict else None
            component_vector_role = role in mapped_components or role in expected_root_roles
            fields = mapping_fields | ({"component_axis"} if component_vector_role else set())
            values = mapping.get("values") if type(mapping) is dict else None
            expected_rnid = (
                compiled_specs["component_report_norm_id_by_role"].get(role)
                if role in mapped_components
                else (
                    compiled_specs["family_root_report_norm_id"]
                    if role in expected_root_roles
                    else compiled_specs["movement_total_report_norm_id_by_role"].get(role)
                )
            )
            if (
                type(mapping) is not dict
                or set(mapping) != fields
                or role not in expected_roles
                or role in seen_roles
                or mapping.get("report_norm_id") != expected_rnid
                or mapping.get("unit") != canonical_unit
                or type(values) is not list
                or not values
                or (
                    role in mapped_components
                    and (
                        mapping.get("row_id") != f"component:{role}"
                        or not same_typed_json_v1(
                            mapping.get("component_axis"), mapped_components[role]
                        )
                    )
                )
                or (
                    role in expected_root_roles
                    and (
                        mapping.get("row_id") != "component:FAMILY_TOTAL"
                        or not same_typed_json_v1(mapping.get("component_axis"), grand_total)
                    )
                )
                or (
                    role in expected_total_roles
                    and mapping.get("row_id")
                    != f"movement:{next(key for key, value in _MAPPED_TOTAL_ROLES.items() if value == role)}"
                )
            ):
                raise _error("equity-matrix mapping schema binding drifted")
            seen_roles.add(role)
            mapping_material = {
                key: value for key, value in mapping.items() if key != "item_mapping_id"
            }
            if mapping["item_mapping_id"] != "gjeqmfv1:item:" + canonical_json_sha256_v1(
                mapping_material
            ):
                raise _error("equity-matrix mapping identity drifted")
            for value in values:
                if type(value) is not dict:
                    raise _error("equity-matrix mapping value provenance drifted")
                cell_ref = value.get("cell_ref") if type(value) is dict else None
                aggregate_components = (
                    value.get("aggregate_components") if type(value) is dict else None
                )
                aggregate_value = aggregate_components is not None
                signed_aggregate = (
                    aggregate_value
                    and value.get("state") == "SIGNED_BRANCH_NET_SOURCE_CELLS_GRAPH_EXACT"
                )
                if (
                    set(value)
                    != (
                        value_fields | {"aggregate_components"} if aggregate_value else value_fields
                    )
                    or value.get("axis_role") not in compiled_specs["movement_roles"]
                    or value.get("coefficient") is not None
                    and type(value.get("coefficient")) is not int
                    or type(value.get("equation_multiplier")) is not int
                    or type(value.get("state")) is not str
                    or not value["state"]
                    or value.get("source_text") is not None
                    and type(value["source_text"]) is not str
                    or (
                        not aggregate_value
                        and (
                            type(cell_ref) is not dict
                            or set(cell_ref) != {"column_id", "locator", "row_id"}
                            or _COLUMN_ID.fullmatch(cell_ref.get("column_id", "")) is None
                            or _ROW_ID.fullmatch(cell_ref.get("row_id", "")) is None
                            or type(cell_ref.get("locator")) is not dict
                            or canonical_json_sha256_v1(cell_ref["locator"]) not in region_hashes
                            or (
                                value.get("coefficient") is None
                                and (
                                    value.get("source_text") is not None
                                    or value.get("state") != "BLANK_SOURCE_CELL"
                                )
                            )
                        )
                    )
                    or (
                        aggregate_value
                        and (
                            cell_ref is not None
                            or value.get("source_text") is not None
                            or value.get("state")
                            not in {
                                "AGGREGATED_SOURCE_CELLS_GRAPH_EXACT",
                                "DERIVED_INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL",
                                "SIGNED_BRANCH_NET_SOURCE_CELLS_GRAPH_EXACT",
                            }
                            or type(aggregate_components) is not list
                            or len(aggregate_components) < (1 if signed_aggregate else 2)
                            or any(
                                type(component) is not dict
                                or set(component) != value_fields
                                or component.get("axis_role") != value.get("axis_role")
                                or component.get("coefficient") is not None
                                and type(component.get("coefficient")) is not int
                                or (
                                    not signed_aggregate
                                    and component.get("equation_multiplier")
                                    != value.get("equation_multiplier")
                                )
                                or type(component.get("cell_ref")) is not dict
                                or canonical_json_sha256_v1(component["cell_ref"].get("locator"))
                                not in region_hashes
                                for component in aggregate_components
                            )
                            or (
                                value.get("state")
                                == "DERIVED_INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL"
                                and (
                                    value.get("coefficient") is not None
                                    or signed_aggregate
                                    or not any(
                                        component.get("coefficient") is None
                                        for component in aggregate_components
                                    )
                                )
                            )
                            or (
                                value.get("state")
                                != "DERIVED_INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL"
                                and (
                                    any(
                                        component.get("coefficient") is None
                                        for component in aggregate_components
                                    )
                                    or sum(
                                        component["coefficient"]
                                        * (
                                            component["equation_multiplier"]
                                            if signed_aggregate
                                            else 1
                                        )
                                        for component in aggregate_components
                                    )
                                    != value.get("coefficient")
                                )
                            )
                            or signed_aggregate
                            and value.get("equation_multiplier") != 1
                        )
                    )
                ):
                    raise _error("equity-matrix mapping value provenance drifted")
            if role in expected_total_roles:
                expected_mapping_axis = [
                    next(
                        key
                        for key, value in _MAPPED_TOTAL_ROLES.items()
                        if value == role
                    )
                ]
            elif (
                component_vector_role
                and mapping["component_axis"].get("kind")
                == "MAPPED_SUPPLEMENTAL_COMPONENT"
            ):
                if supplemental_mapping_axis is None:
                    raise _error("equity-matrix supplemental movement axis drifted")
                expected_mapping_axis = [
                    axis_role
                    for axis_role in expected_axis_roles
                    if axis_role in supplemental_mapping_axis
                ]
            else:
                expected_mapping_axis = expected_axis_roles
            if [value["axis_role"] for value in values] != expected_mapping_axis:
                raise _error("equity-matrix mapping movement axis drifted")
        if candidate["status"] == READY:
            if (
                candidate["reasons"]
                or seen_roles & omitted_roles
                or seen_roles | omitted_roles != expected_roles
                or canonical_unit is None
            ):
                raise _error("equity-matrix READY candidate semantics drifted")
        elif candidate["mappings"] or not candidate["reasons"]:
            raise _error("equity-matrix unresolved candidate semantics drifted")
        return candidate

    for ordinal, (trial, document, disposition) in enumerate(
        zip(trials, documents, evidence["candidate_dispositions"], strict=True), start=1
    ):
        if (
            type(trial) is not dict
            or set(trial) != trial_fields
            or trial.get("document_ordinal") != ordinal
            or trial.get("source_logical_name") != document["source_logical_name"]
            or trial.get("source_sha256") != document["source_sha256"]
            or type(trial.get("candidates")) is not list
            or trial.get("candidate_count") != len(trial["candidates"])
            or type(trial.get("mappings")) is not list
            or type(trial.get("reasons")) is not list
            or trial["reasons"] != sorted(set(trial["reasons"]))
            or trial.get("status") not in {READY, NOT_OBSERVED, UNRESOLVED}
        ):
            raise _error("equity-matrix sweep trial identity drifted")
        if disposition["disposition"] == READY:
            if len(trial["candidates"]) != 1:
                raise _error("equity-matrix accepted document needs exactly one candidate")
            candidate = validate_candidate(
                trial["candidates"][0], document=document, cluster=accepted[ordinal]
            )
            if not same_typed_json_v1(
                candidate.get("component_regions"), accepted[ordinal]["component_regions"]
            ):
                raise _error("equity-matrix candidate region binding drifted")
            if candidate.get("status") == READY:
                if (
                    trial.get("status") != READY
                    or trial.get("selected_candidate_id") != candidate.get("candidate_id")
                    or not same_typed_json_v1(trial.get("mappings"), candidate.get("mappings"))
                    or trial.get("reasons")
                ):
                    raise _error("equity-matrix READY trial binding drifted")
            elif (
                trial.get("status") != UNRESOLVED
                or trial.get("selected_candidate_id") is not None
                or trial.get("mappings")
                or trial.get("reasons") != candidate.get("reasons")
            ):
                raise _error("equity-matrix unresolved candidate binding drifted")
        elif disposition["disposition"] == NOT_OBSERVED:
            if (
                trial.get("status") != NOT_OBSERVED
                or trial["candidates"]
                or trial.get("mappings")
                or trial.get("reasons")
                or trial.get("selected_candidate_id") is not None
            ):
                raise _error("equity-matrix not-observed trial binding drifted")
        elif (
            trial.get("status") != UNRESOLVED
            or trial["candidates"]
            or trial.get("mappings")
            or trial.get("selected_candidate_id") is not None
            or trial.get("reasons") != disposition["cluster"]["reasons"]
        ):
            raise _error("equity-matrix unresolved query disposition binding drifted")
    return canonical_clone_v1(trials)
