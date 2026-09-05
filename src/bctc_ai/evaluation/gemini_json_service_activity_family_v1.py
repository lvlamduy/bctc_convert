"""Family-30 adapter for service-activity disclosures.

The shared multi-table engine remains the accounting authority.  This module
adds only three independently replayable source-normalisation steps before the
shared evaluator runs:

* exact, content-addressed PDF transcription repairs for visible cells/labels;
* governed cumulative-duration header normalisation; and
* an exact source-unit corroboration against the same document's primary
  service-activity row.

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
    _coalesce_document_declared_root_components_v1,
    _multitable_lane_axis,
    _outline_top_level_number,
    _page_record_axis,
    _source_money,
    _source_table,
    _unit_axis,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    classify_gemini_json_multitable_hierarchical_table_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FAMILY_ID = "SERVICE_ACTIVITY"
ADAPTER_FORMAT_VERSION = "GEMINI_JSON_SERVICE_ACTIVITY_FAMILY_ADAPTER_V1"
SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION = (
    "GEMINI_JSON_SERVICE_ACTIVITY_AUTHENTICATED_SOURCE_REPAIR_ARTIFACT_V1"
)
SOURCE_REPAIR_POLICY = (
    "TRANSCRIBE_ONLY_PDF_VISIBLE_TOKENS_NO_EQUATION_BACKSOLVE_NO_BLANK_TO_ZERO_NO_PROVIDER"
)
OWNER_ONLY_CONTINUATION_POLICY = (
    "UNIQUE_ADJACENT_PRIOR_EXACT_OWNER_ONLY_SECTION_BINDS_COMPLETE_FROM_PREVIOUS_TABLE"
)
OWNER_ONLY_CONTINUATION_CONFIG_GATE = (
    "EXACT_PRIOR_ROOT_CARRIER_SCOPES_CONSECUTIVE_RECEIVER_PREFIX"
)
ROOT_ALTERNATIVE_LEGACY_FALLBACK_POLICY = (
    "EXACT_FIRST_DECLARED_LEGACY_COMPONENT_FRONTIER_ONLY_WHEN_OTHER_ALTERNATIVE_ROLES_ABSENT"
)
ROOT_ALTERNATIVE_PRIMARY_SOURCE_RESULT_FALLBACK_POLICY = (
    "EXACT_FIRST_DECLARED_LEGACY_COMPONENT_FRONTIER_WITH_UNIQUE_VISIBLE_PRIMARY_RESULT_"
    "ONLY_WHEN_OTHER_ALTERNATIVE_ROLES_ABSENT"
)
ROOT_ALTERNATIVE_PRIMARY_PARENT_CONTROL_FALLBACK_POLICY = (
    "EXACT_PRIMARY_ROOT_EQUATION_REPLACES_ONLY_PARTIAL_ROOT_PARENT_MAPPING_WITH_"
    "THE_SAME_VISIBLE_PRIMARY_PARENT_ROW"
)
ADJACENT_COMPLEMENTARY_PARENT_POLICY = (
    "UNIQUE_IMMEDIATE_NEXT_MONEY_TABLE_EXACT_EXPENSE_PARENT_COMPLEMENTS_SELECTED_INCOME_PARENT"
)
DOCUMENT_DECLARED_RECOVERY_POLICY = (
    "F30_EXACT_DOCUMENT_DECLARED_ROOT_COMPONENTS_PLUS_SOURCE_RESULT_WHEN_GENERIC_"
    "OWNER_PATH_WAS_SELECTED_BY_AN_UNRELATED_CONTINUATION_MARKER"
)
PRIMARY_SOURCE_RESULT_AUGMENTATION_POLICY = (
    "UNIQUE_EXACT_PRIMARY_SOURCE_RESULT_CONTROL_PREPENDS_READY_OWNER_NOTE_"
    "WITH_EXACT_SEMANTIC_PERIOD_UNIT_AND_SOURCE_AXIS_OR_ROOT_VECTOR_BINDING"
)
DEFAULT_SOURCE_REPAIR_PATH = "data/registered/gemini_json_service_activity_source_repairs_v1.json"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_DECLARATIVE_SERVICE_ACTIVITY_"
    "MULTITABLE_HIERARCHICAL_EXACT_PDF_DASH_TRANSCRIPTION_GOVERNED_DURATION_"
    "HEADER_AND_PRIMARY_STATEMENT_VALUE_PERIOD_UNIT_CORROBORATION_PRIVATE_CLONE_"
    "ONLY_NO_BLANK_ZERO_NO_NUMERIC_BACKSOLVE_NO_MAGNITUDE_UNIT_INFERENCE_"
    "PROPOSAL_ONLY_" + SHARED_CLAIM_BOUNDARY
)

_PAGE_VERSION = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_DOCUMENT_ID = re.compile(r"gfpstorev1:document:[0-9a-f]{64}\Z")
_EXTRACTION_RUN_ID = re.compile(r"gfpstorev1:run:[0-9a-f]{64}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SECTION_ID = re.compile(r"s[1-9][0-9]*\Z")
_TABLE_ID = re.compile(r"t[1-9][0-9]*\Z")
_ROW_ID = re.compile(r"r[1-9][0-9]*\Z")
_REPAIR_ID = re.compile(r"gjsafav1:repair:[0-9a-f]{64}\Z")
_OVERLAY_ID = re.compile(r"gjsafav1:overlay:[0-9a-f]{64}\Z")
_DASHES = {"-", "_", "–", "—", "−"}
_VISIBLE_ACCOUNTING_MONEY = re.compile(r"(?:[-_–—−]|\d+(?:[., ]\d+)*|\(\d+(?:[., ]\d+)*\))\Z")
_DURATION_GOVERNOR = re.compile(
    r"(?:(?:luy ke )?(?:tu )?dau (?:nam|ky)"
    r"(?: den(?: cuoi)?(?: quy| ky)?(?: nay)?)?"
    r"|(?:3|6|9|ba|sau|chin) thang dau (?:cua )?nam)\Z"
)


class GeminiJsonServiceActivityFamilyV1Error(ValueError):
    """The Family-30 source adapter or its replay evidence drifted."""


def _error(message: str) -> GeminiJsonServiceActivityFamilyV1Error:
    return GeminiJsonServiceActivityFamilyV1Error(message)


def _load_default_source_repair_artifact_v1() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[3] / DEFAULT_SOURCE_REPAIR_PATH
    try:
        return json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("service-activity source-repair artifact is absent or invalid") from exc


def _source_repair_bbox_v1(
    value: Any,
    *,
    pixel_width: int,
    pixel_height: int,
    label: str,
) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or not (0 <= value[0] < value[2] <= pixel_width)
        or not (0 <= value[1] < value[3] <= pixel_height)
    ):
        raise _error(f"service-activity source-repair {label} is invalid")
    return list(value)


def _compile_authenticated_source_repair_artifact_v1(value: Any) -> dict[str, Any]:
    """Compile one immutable, content-addressed visual transcription artifact."""

    artifact_fields = {
        "family_id",
        "format_version",
        "overlay_id",
        "repairs",
        "review_policy",
    }
    if (
        type(value) is not dict
        or set(value) != artifact_fields
        or value.get("family_id") != FAMILY_ID
        or value.get("format_version") != SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION
        or value.get("review_policy") != SOURCE_REPAIR_POLICY
        or type(value.get("repairs")) is not list
        or not value["repairs"]
    ):
        raise _error("service-activity source-repair artifact is invalid")

    repair_fields = {
        "base_page_json_sha256",
        "base_page_json_version_id",
        "cell_repairs",
        "effective_page_json_sha256",
        "extraction_run_id",
        "repair_id",
        "repair_reason",
        "row_repairs",
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
    row_fields = {
        "after_hierarchy_path_exact",
        "after_label_exact",
        "before_hierarchy_path_exact",
        "before_label_exact",
        "crop_bbox_pixels_xyxy",
        "crop_rgb_sha256",
        "row_id",
        "row_kind",
        "visual_state",
    }
    checked_repairs = []
    seen_versions: set[str] = set()
    seen_ids: set[str] = set()
    for raw_repair in value["repairs"]:
        if type(raw_repair) is not dict or set(raw_repair) != repair_fields:
            raise _error("service-activity source-repair fields drifted")
        repair = canonical_clone_v1(raw_repair)
        source = repair["source_binding"]
        if type(source) is not dict or set(source) != source_fields:
            raise _error("service-activity source-repair source fields drifted")
        if (
            type(source.get("source_logical_name")) is not str
            or not source["source_logical_name"].strip()
            or _SHA256.fullmatch(source.get("source_sha256", "")) is None
            or type(source.get("source_size_bytes")) is not int
            or source["source_size_bytes"] <= 0
            or _DOCUMENT_ID.fullmatch(source.get("document_id", "")) is None
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
            or type(source.get("page_id")) is not str
        ):
            raise _error("service-activity source-repair source binding is invalid")
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
            raise _error("service-activity source-repair source identity does not replay")

        if (
            _SHA256.fullmatch(repair.get("base_page_json_sha256", "")) is None
            or _SHA256.fullmatch(repair.get("effective_page_json_sha256", "")) is None
            or _SHA256.fullmatch(repair.get("stored_canonical_json_sha256", "")) is None
            or _EXTRACTION_RUN_ID.fullmatch(repair.get("extraction_run_id", "")) is None
            or _PAGE_VERSION.fullmatch(repair.get("base_page_json_version_id", "")) is None
            or repair["base_page_json_version_id"] in seen_versions
        ):
            raise _error("service-activity source-repair page version is invalid")
        expected_version_id = "gfpstorev1:json:" + canonical_json_sha256_v1(
            {
                "canonical_json_sha256": repair["stored_canonical_json_sha256"],
                "extraction_run_id": repair["extraction_run_id"],
                "page_id": source["page_id"],
            }
        )
        if repair["base_page_json_version_id"] != expected_version_id:
            raise _error("service-activity source-repair page version does not replay")
        seen_versions.add(repair["base_page_json_version_id"])

        table_ref = repair["table_ref"]
        if (
            type(table_ref) is not dict
            or set(table_ref) != table_fields
            or _SECTION_ID.fullmatch(table_ref.get("section_id", "")) is None
            or _TABLE_ID.fullmatch(table_ref.get("table_id", "")) is None
            or _SHA256.fullmatch(table_ref.get("base_table_sha256", "")) is None
            or _SHA256.fullmatch(table_ref.get("effective_table_sha256", "")) is None
        ):
            raise _error("service-activity source-repair table binding is invalid")
        visual = repair["visual_evidence"]
        if (
            type(visual) is not dict
            or set(visual) != visual_fields
            or visual.get("evidence_kind") != "AUTHENTICATED_MANUAL_VISUAL_TRANSCRIPTION"
            or visual.get("render_mode") != "PDF_PAGE_GET_PIXMAP_DPI_EXACT"
            or re.fullmatch(
                r"20\d{2}-[01]\d-[0-3]\d",
                visual.get("reviewed_utc_date", ""),
            )
            is None
            or _SHA256.fullmatch(visual.get("table_crop_rgb_sha256", "")) is None
        ):
            raise _error("service-activity source-repair visual evidence is invalid")
        table_bbox = _source_repair_bbox_v1(
            visual["table_crop_bbox_pixels_xyxy"],
            pixel_width=source["pixel_width"],
            pixel_height=source["pixel_height"],
            label="table crop",
        )

        cells = []
        seen_cells: set[str] = set()
        if type(repair.get("cell_repairs")) is not list:
            raise _error("service-activity source-repair cell axis is invalid")
        for raw_cell in repair["cell_repairs"]:
            if type(raw_cell) is not dict or set(raw_cell) != cell_fields:
                raise _error("service-activity source-repair cell fields drifted")
            cell = canonical_clone_v1(raw_cell)
            match = re.fullmatch(
                r"r([1-9][0-9]*):c([1-9][0-9]*)",
                cell.get("cell_id", ""),
            )
            after = cell.get("after_exact")
            cell_bbox = _source_repair_bbox_v1(
                cell.get("crop_bbox_pixels_xyxy"),
                pixel_width=source["pixel_width"],
                pixel_height=source["pixel_height"],
                label="cell crop",
            )
            if (
                match is None
                or cell["cell_id"] in seen_cells
                or type(cell.get("before_exact")) not in {str, type(None)}
                or type(after) is not str
                or _VISIBLE_ACCOUNTING_MONEY.fullmatch(after.strip()) is None
                or cell.get("visual_state") != ("DASH" if after in _DASHES else "PRINTED_MONEY")
                or same_typed_json_v1(cell.get("before_exact"), after)
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
                    table_bbox[0] <= cell_bbox[0] < cell_bbox[2] <= table_bbox[2]
                    and table_bbox[1] <= cell_bbox[1] < cell_bbox[3] <= table_bbox[3]
                )
            ):
                raise _error("service-activity source-repair cell is invalid")
            seen_cells.add(cell["cell_id"])
            cells.append(cell)
        cells.sort(key=lambda item: tuple(int(part[1:]) for part in item["cell_id"].split(":")))
        if repair["cell_repairs"] != cells:
            raise _error("service-activity source-repair cell axis is unordered")

        rows = []
        seen_rows: set[str] = set()
        if type(repair.get("row_repairs")) is not list:
            raise _error("service-activity source-repair row axis is invalid")
        for raw_row in repair["row_repairs"]:
            if type(raw_row) is not dict or set(raw_row) != row_fields:
                raise _error("service-activity source-repair row fields drifted")
            row = canonical_clone_v1(raw_row)
            row_bbox = _source_repair_bbox_v1(
                row.get("crop_bbox_pixels_xyxy"),
                pixel_width=source["pixel_width"],
                pixel_height=source["pixel_height"],
                label="row crop",
            )
            if (
                _ROW_ID.fullmatch(row.get("row_id", "")) is None
                or row["row_id"] in seen_rows
                or type(row.get("row_kind")) is not str
                or not row["row_kind"]
                or type(row.get("before_label_exact")) is not str
                or not row["before_label_exact"].strip()
                or type(row.get("after_label_exact")) is not str
                or not row["after_label_exact"].strip()
                or row["before_label_exact"] == row["after_label_exact"]
                or type(row.get("before_hierarchy_path_exact")) is not list
                or not row["before_hierarchy_path_exact"]
                or any(
                    type(item) is not str or not item for item in row["before_hierarchy_path_exact"]
                )
                or type(row.get("after_hierarchy_path_exact")) is not list
                or not row["after_hierarchy_path_exact"]
                or any(
                    type(item) is not str or not item for item in row["after_hierarchy_path_exact"]
                )
                or same_typed_json_v1(
                    row["before_hierarchy_path_exact"],
                    row["after_hierarchy_path_exact"],
                )
                or row.get("visual_state") != "PRINTED_LABEL"
                or _SHA256.fullmatch(row.get("crop_rgb_sha256", "")) is None
                or not (
                    table_bbox[0] <= row_bbox[0] < row_bbox[2] <= table_bbox[2]
                    and table_bbox[1] <= row_bbox[1] < row_bbox[3] <= table_bbox[3]
                )
            ):
                raise _error("service-activity source-repair row is invalid")
            seen_rows.add(row["row_id"])
            rows.append(row)
        rows.sort(key=lambda item: int(item["row_id"][1:]))
        if repair["row_repairs"] != rows or not cells and not rows:
            raise _error("service-activity source-repair row axis is unordered or empty")

        if repair.get("repair_reason") != "VISIBLE_PDF_TRANSCRIPTION_MISMATCH":
            raise _error("service-activity source-repair reason is invalid")
        expected_id = "gjsafav1:repair:" + canonical_json_sha256_v1(
            {key: repair[key] for key in repair if key != "repair_id"}
        )
        if (
            _REPAIR_ID.fullmatch(repair.get("repair_id", "")) is None
            or repair["repair_id"] != expected_id
            or repair["repair_id"] in seen_ids
        ):
            raise _error("service-activity source-repair identity does not replay")
        seen_ids.add(repair["repair_id"])
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
        raise _error("service-activity source-repair axis is unordered")
    material = {
        "family_id": FAMILY_ID,
        "format_version": SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION,
        "repairs": checked_repairs,
        "review_policy": SOURCE_REPAIR_POLICY,
    }
    expected_overlay_id = "gjsafav1:overlay:" + canonical_json_sha256_v1(material)
    if (
        _OVERLAY_ID.fullmatch(value.get("overlay_id", "")) is None
        or value["overlay_id"] != expected_overlay_id
    ):
        raise _error("service-activity source-repair overlay identity does not replay")
    return {**material, "overlay_id": expected_overlay_id}


def compile_gemini_json_service_activity_family_specs_v1(
    topology_spec: Any,
    evaluation_spec: Any,
    schema_binding_spec: Any,
    source_repair_spec: Any | None = None,
) -> dict[str, Any]:
    """Compile Family 30 plus its independently authenticated source overlay."""

    try:
        compiled = compile_gemini_json_multitable_hierarchical_family_specs_v1(
            topology_spec, evaluation_spec, schema_binding_spec
        )
    except ValueError as exc:
        raise _error("service-activity declarative family specs are invalid") from exc
    return bind_gemini_json_service_activity_source_repair_artifact_v1(
        compiled,
        source_repair_spec,
    )


def bind_gemini_json_service_activity_source_repair_artifact_v1(
    compiled_specs: Any,
    source_repair_spec: Any | None = None,
) -> dict[str, Any]:
    """Bind the exact dash overlay to an already compiled generic family."""

    if type(compiled_specs) is not dict:
        raise _error("service-activity compiled family frontier is invalid")
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
        raise _error("service-activity compiled family frontier is invalid")
    raw_overlay = (
        _load_default_source_repair_artifact_v1()
        if source_repair_spec is None
        else source_repair_spec
    )
    compiled["service_activity_adapter_format_version"] = ADAPTER_FORMAT_VERSION
    compiled["service_activity_source_repair_overlay"] = (
        _compile_authenticated_source_repair_artifact_v1(raw_overlay)
    )
    compiled["service_activity_source_repair_spec_sha256"] = canonical_json_sha256_v1(raw_overlay)
    return compiled


def build_gemini_json_service_activity_region_query_receipt_v1(
    regions: Any,
) -> dict[str, Any]:
    return build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)


def _section_money_table_count_v1(section: Mapping[str, Any]) -> int:
    count = 0
    tables = section.get("tables")
    for table in tables if type(tables) is list else []:
        columns = table.get("columns") if type(table) is dict else None
        if type(columns) is list and any(
            type(column) is dict and column.get("value_kind") == "MONEY"
            for column in columns
        ):
            count += 1
    return count


def _exact_alias_v1(value: Any, aliases: Sequence[str]) -> str | None:
    folded = _without_leading_ordinal(_normalized(value))
    if not folded:
        return None
    matches = sorted({alias for alias in aliases if _normalized(alias) == folded})
    return matches[0] if len(matches) == 1 else None


def _exact_current_comparative_axis_v1(table: Mapping[str, Any]) -> dict[str, Any] | None:
    columns = table.get("columns")
    if type(columns) is not list:
        return None
    money = [
        (ordinal, column)
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    if len(money) != 2:
        return None
    roles = []
    paths = []
    for _ordinal, column in money:
        path = column.get("header_path_exact")
        if (
            type(path) is not list
            or not path
            or any(type(item) is not str or not _normalized(item) for item in path)
        ):
            return None
        folded = _normalized(" ".join(path))
        if folded in {"ky nay", "nam nay"}:
            roles.append("CURRENT_PERIOD")
        elif folded in {"ky truoc", "nam truoc"}:
            roles.append("COMPARATIVE_PERIOD")
        else:
            return None
        paths.append(canonical_clone_v1(path))
    if roles != ["CURRENT_PERIOD", "COMPARATIVE_PERIOD"]:
        return None
    return {
        "header_paths_exact": paths,
        "money_column_ordinals": [ordinal for ordinal, _column in money],
        "semantic_roles": roles,
    }


def _complete_source_vector_v1(
    row: Mapping[str, Any], money_ordinals: Sequence[int]
) -> list[int] | None:
    values = row.get("values_exact")
    if type(values) is not list or any(ordinal > len(values) for ordinal in money_ordinals):
        return None
    vector = [_source_money(values[ordinal - 1])["coefficient"] for ordinal in money_ordinals]
    return vector if all(type(value) is int for value in vector) else None


def _receiver_recovery_signal_v1(
    *,
    record: Mapping[str, Any],
    section: Mapping[str, Any],
    section_ordinal: int,
    table: Mapping[str, Any],
    table_ordinal: int,
    classification: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    if (
        table.get("continuation") != "CONTINUES_FROM_PREVIOUS_PAGE"
        or _normalized(section.get("title_exact"))
        or _normalized(table.get("title_exact"))
        or classification.get("typed_control_disposition") is not None
    ):
        return None
    axis = _exact_current_comparative_axis_v1(table)
    roots = classification.get("family_root_row_ordinals")
    rows = table.get("rows")
    if axis is None or type(roots) is not list or len(roots) != 1 or type(rows) is not list:
        return None
    root_ordinal = roots[0]
    money_ordinals = axis["money_column_ordinals"]
    if (
        type(root_ordinal) is not int
        or not 1 <= root_ordinal <= len(rows)
        or _complete_source_vector_v1(rows[root_ordinal - 1], money_ordinals) is None
    ):
        return None
    ambiguous_ordinals = {
        item.get("row_ordinal") for item in classification.get("ambiguous_rows", [])
    }
    component_rows = {}
    for role in compiled_specs.get("root_component_roles", []):
        ordinals = {
            hit.get("row_ordinal")
            for hit in classification.get("role_hits", [])
            if hit.get("role") == role and type(hit.get("row_ordinal")) is int
        }
        if len(ordinals) != 1:
            return None
        ordinal = next(iter(ordinals))
        if (
            ordinal in ambiguous_ordinals
            or not 1 <= ordinal <= len(rows)
            or _complete_source_vector_v1(rows[ordinal - 1], money_ordinals) is None
        ):
            return None
        component_rows[role] = ordinal
    roles = {
        hit.get("role")
        for hit in classification.get("role_hits", [])
        if type(hit.get("role")) is str
    } | {
        role for role in classification.get("context_roles", []) if type(role) is str
    }
    return {
        "axis": axis,
        "classification": classification,
        "component_row_ordinals": component_rows,
        "component_roles": sorted(roles),
        "record": record,
        "root_row_ordinal": root_ordinal,
        "section_id": f"s{section_ordinal}",
        "table_id": f"t{table_ordinal}",
    }


def _reseal_cluster_v1(cluster: Mapping[str, Any], **updates: Any) -> dict[str, Any]:
    material = {
        key: canonical_clone_v1(value)
        for key, value in cluster.items()
        if key != "cluster_id"
    }
    material.update(canonical_clone_v1(updates))
    return {
        **material,
        "cluster_id": "gjmthfcv1:cluster:" + canonical_json_sha256_v1(material),
    }


def _recover_owner_only_continuation_cluster_v1(
    *,
    page_records: Sequence[Mapping[str, Any]],
    base_cluster: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Recover one exact owner-only-page-break shape without mutating source JSON."""

    if (
        base_cluster.get("status") != "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
        or base_cluster.get("component_regions")
        or base_cluster.get("reasons")
    ):
        return None
    inventory = base_cluster.get("declared_money_table_inventory")
    if type(inventory) is not list:
        return None
    classification_by_key = {
        (
            item.get("page_json_version_id"),
            item.get("section_id"),
            item.get("table_id"),
        ): item.get("classification")
        for item in inventory
        if type(item) is dict and type(item.get("classification")) is dict
    }
    owner_aliases = compiled_specs.get("query_policy", {}).get("owner_aliases", [])
    reset_aliases = [
        *compiled_specs.get("query_policy", {}).get("reset_aliases", []),
        *compiled_specs.get("query_policy", {}).get("hard_negative_aliases", []),
    ]
    owners = []
    receivers = []
    for record in page_records:
        page = record.get("page_json")
        if type(page) is not dict or page.get("status") == "PRIMARY_FINANCIAL_STATEMENT":
            continue
        sections = page.get("sections")
        if type(sections) is not list:
            continue
        for section_ordinal, section in enumerate(sections, start=1):
            if type(section) is not dict:
                continue
            alias = _exact_alias_v1(section.get("title_exact"), owner_aliases)
            if alias is not None:
                later_resets = [
                    {
                        "matched_alias": matched,
                        "section_id": f"s{later_ordinal}",
                        "source_exact": later.get("title_exact"),
                    }
                    for later_ordinal, later in enumerate(
                        sections[section_ordinal:], start=section_ordinal + 1
                    )
                    if type(later) is dict
                    and (
                        matched := _exact_alias_v1(
                            later.get("title_exact"), reset_aliases
                        )
                    )
                    is not None
                ]
                owners.append(
                    {
                        "later_resets": later_resets,
                        "matched_alias": alias,
                        "money_table_count": _section_money_table_count_v1(section),
                        "record": record,
                        "section_id": f"s{section_ordinal}",
                        "source_exact": section.get("title_exact"),
                    }
                )
            tables = section.get("tables")
            for table_ordinal, table in enumerate(
                tables if type(tables) is list else [], start=1
            ):
                if type(table) is not dict:
                    continue
                classification = classification_by_key.get(
                    (
                        record.get("page_json_version_id"),
                        f"s{section_ordinal}",
                        f"t{table_ordinal}",
                    )
                )
                if type(classification) is not dict:
                    continue
                signal = _receiver_recovery_signal_v1(
                    record=record,
                    section=section,
                    section_ordinal=section_ordinal,
                    table=table,
                    table_ordinal=table_ordinal,
                    classification=classification,
                    compiled_specs=compiled_specs,
                )
                if signal is not None:
                    receivers.append(signal)
    if not owners or not receivers:
        return None
    reasons = []
    if len(receivers) != 1:
        reasons.append("SERVICE_ACTIVITY_OWNER_ONLY_CONTINUATION_RECEIVER_AMBIGUOUS")
    if len(owners) != 1:
        reasons.append("SERVICE_ACTIVITY_OWNER_ONLY_CONTINUATION_OWNER_AMBIGUOUS")
    if reasons:
        return _reseal_cluster_v1(
            base_cluster,
            component_regions=[],
            owner_receipt=None,
            reasons=sorted(reasons),
            status="UNRESOLVED_GEMINI_JSON_FAMILY",
        )
    owner = owners[0]
    receiver = receivers[0]
    if owner["money_table_count"] != 0:
        reasons.append("SERVICE_ACTIVITY_OWNER_ONLY_SECTION_HAS_MONEY_TABLE")
    if owner["later_resets"]:
        reasons.append("SERVICE_ACTIVITY_OWNER_ONLY_SECTION_RESET_BEFORE_RECEIVER")
    owner_record = owner["record"]
    receiver_record = receiver["record"]
    if (
        receiver_record.get("selected_page_ordinal")
        != owner_record.get("selected_page_ordinal", -1) + 1
        or receiver_record.get("physical_page") != owner_record.get("physical_page", -1) + 1
    ):
        reasons.append("SERVICE_ACTIVITY_OWNER_ONLY_CONTINUATION_NOT_ADJACENT")
    if reasons:
        return _reseal_cluster_v1(
            base_cluster,
            component_regions=[],
            owner_receipt=None,
            reasons=sorted(reasons),
            status="UNRESOLVED_GEMINI_JSON_FAMILY",
        )
    region = {
        "component_roles": receiver["component_roles"],
        "document_id": receiver_record["document_id"],
        "document_ordinal": receiver_record["document_ordinal"],
        "fragment_ordinal": 1,
        "page_json_version_id": receiver_record["page_json_version_id"],
        "physical_page": receiver_record["physical_page"],
        "section_id": receiver["section_id"],
        "selected_page_ordinal": receiver_record["selected_page_ordinal"],
        "source_logical_name": receiver_record["source_logical_name"],
        "source_sha256": receiver_record["source_sha256"],
        "table_id": receiver["table_id"],
    }
    receipt_material = {
        "adapter_format_version": ADAPTER_FORMAT_VERSION,
        "owner_section": {
            "matched_alias": owner["matched_alias"],
            "money_table_count": owner["money_table_count"],
            "page_json_version_id": owner_record["page_json_version_id"],
            "physical_page": owner_record["physical_page"],
            "section_id": owner["section_id"],
            "selected_page_ordinal": owner_record["selected_page_ordinal"],
            "source_exact": owner["source_exact"],
        },
        "policy": OWNER_ONLY_CONTINUATION_POLICY,
        "receiver_table": {
            "component_row_ordinals": receiver["component_row_ordinals"],
            "continuation": "CONTINUES_FROM_PREVIOUS_PAGE",
            "explicit_period_axis": receiver["axis"],
            "page_json_version_id": receiver_record["page_json_version_id"],
            "physical_page": receiver_record["physical_page"],
            "root_row_ordinal": receiver["root_row_ordinal"],
            "section_id": receiver["section_id"],
            "selected_page_ordinal": receiver_record["selected_page_ordinal"],
            "table_id": receiver["table_id"],
        },
        "rule": (
            "UNIQUE_ADJACENT_EXACT_OWNER_SECTION_WITH_ZERO_MONEY_TABLES_BINDS_"
            "ONE_COMPLETE_LOCAL_CURRENT_COMPARATIVE_FROM_PREVIOUS_TABLE_NO_SOURCE_MUTATION"
        ),
    }
    owner_receipt = {
        **receipt_material,
        "receipt_id": "gjsafav1:owner-continuation:"
        + canonical_json_sha256_v1(receipt_material),
    }
    selected_inventory = canonical_clone_v1(inventory)
    for item in selected_inventory:
        if (
            item.get("page_json_version_id") == receiver_record["page_json_version_id"]
            and item.get("section_id") == receiver["section_id"]
            and item.get("table_id") == receiver["table_id"]
        ):
            item["disposition"] = (
                "SELECTED_F30_ADJACENT_OWNER_ONLY_SECTION_CONTINUATION"
            )
    return _reseal_cluster_v1(
        base_cluster,
        component_regions=[region],
        declared_money_table_inventory=selected_inventory,
        owner_receipt=owner_receipt,
        reasons=[],
        status="READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY",
    )


def coalesce_gemini_json_service_activity_document_v1(
    *, page_records: Any, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    if compiled_specs.get("topology", {}).get("family_id") != FAMILY_ID:
        raise _error("service-activity adapter received another family")
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=page_records,
        compiled_specs=compiled_specs,
    )
    return recover_gemini_json_service_activity_query_cluster_v1(
        page_records=page_records,
        base_cluster=base,
        compiled_specs=compiled_specs,
    )


def recover_gemini_json_service_activity_owner_only_continuation_v1(
    *,
    page_records: Any,
    base_cluster: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply the exact F30 query recovery to one already sealed generic cluster."""

    if compiled_specs.get("topology", {}).get("family_id") != FAMILY_ID:
        raise _error("service-activity adapter received another family")
    if (
        compiled_specs.get("continuation_leading_child_scope_policy")
        != OWNER_ONLY_CONTINUATION_CONFIG_GATE
    ):
        return canonical_clone_v1(base_cluster)
    if type(page_records) not in {list, tuple}:
        return canonical_clone_v1(base_cluster)
    recovered = _recover_owner_only_continuation_cluster_v1(
        page_records=page_records,
        base_cluster=base_cluster,
        compiled_specs=compiled_specs,
    )
    return canonical_clone_v1(base_cluster) if recovered is None else recovered


def _classification_roles_v1(classification: Mapping[str, Any]) -> set[str]:
    return {
        hit.get("role")
        for hit in classification.get("role_hits", [])
        if type(hit) is dict and type(hit.get("role")) is str
    } | {
        role
        for role in classification.get("context_roles", [])
        if type(role) is str
    }


def _recover_document_declared_cluster_v1(
    *,
    page_records: Sequence[Mapping[str, Any]],
    base_cluster: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Replay F30's declared document graph when generic routing chose owner mode.

    The shared coalescer deliberately routes a document through its continuation
    owner path when *any* MONEY table in that document carries an explicit page
    continuation marker.  A primary income statement commonly carries such a
    marker even though the service note itself is local and complete.  F30's
    declared policy still requires that exact primary source-result control to
    be joined with the detailed note population.  Replaying the already-shared
    document policy here restores only a fully resolved alternative; incomplete
    or ambiguous alternatives leave the original generic disposition untouched.
    """

    if compiled_specs.get("document_cluster_policy") != (
        "DOCUMENT_EXACT_DECLARED_ROOT_COMPONENTS_PLUS_SOURCE_RESULT"
    ):
        return None
    if (
        base_cluster.get("status") != "UNRESOLVED_GEMINI_JSON_FAMILY"
        or base_cluster.get("reasons") != ["COMPLETE_OWNER_CLUSTER_NOT_RESOLVED"]
        or base_cluster.get("component_regions")
    ):
        return None
    owner_receipt = base_cluster.get("owner_receipt")
    if (
        type(owner_receipt) is dict
        and owner_receipt.get("policy")
        == "DOCUMENT_EXACT_DECLARED_ROOT_COMPONENTS_PLUS_SOURCE_RESULT"
    ):
        return None
    try:
        pages = _page_record_axis(page_records)
    except (TypeError, ValueError):
        return None
    table_axis = []
    for record in pages:
        page = record["page_json"]
        sections = page.get("sections")
        for section_ordinal, section in enumerate(
            sections if type(sections) is list else [], start=1
        ):
            if type(section) is not dict:
                continue
            tables = section.get("tables")
            for table_ordinal, table in enumerate(
                tables if type(tables) is list else [], start=1
            ):
                if type(table) is not dict:
                    continue
                classification = classify_gemini_json_multitable_hierarchical_table_v1(
                    page,
                    section,
                    table,
                    compiled_specs=compiled_specs,
                )
                if not classification.get("money_column_ordinals"):
                    continue
                table_axis.append(
                    {
                        "classification": classification,
                        "outline_top_level_number": _outline_top_level_number(
                            table.get("title_exact")
                        ),
                        "position": [
                            record["selected_page_ordinal"],
                            section_ordinal,
                            table_ordinal,
                        ],
                        "record": record,
                        "section_id": f"s{section_ordinal}",
                        "table_id": f"t{table_ordinal}",
                    }
                )
    alternative = _coalesce_document_declared_root_components_v1(
        pages=pages,
        table_axis=table_axis,
        compiled_specs=compiled_specs,
    )
    alternative_receipt = alternative.get("owner_receipt")
    if (
        alternative.get("status")
        == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
        and alternative.get("component_regions") == []
        and alternative.get("reasons")
        == ["DOCUMENT_DECLARED_ROOT_DETAIL_ALTERNATIVE_INCOMPLETE"]
        and type(alternative_receipt) is dict
        and alternative_receipt.get("policy")
        == "DOCUMENT_EXACT_DECLARED_ROOT_COMPONENTS_PLUS_SOURCE_RESULT"
        and alternative_receipt.get("detailed_root_roles") == []
        and alternative_receipt.get("selected_component_positions")
    ):
        receipt = canonical_clone_v1(alternative_receipt)
        receipt["service_activity_document_declared_recovery_policy"] = (
            DOCUMENT_DECLARED_RECOVERY_POLICY
        )
        return _reseal_cluster_v1(alternative, owner_receipt=receipt)
    if alternative.get("status") != "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY":
        return None
    selected_keys = {
        (
            region.get("page_json_version_id"),
            region.get("section_id"),
            region.get("table_id"),
        )
        for region in alternative.get("component_regions", [])
        if type(region) is dict
    }
    selected_primary_controls = [
        item
        for item in alternative.get("declared_money_table_inventory", [])
        if type(item) is dict
        and (
            item.get("page_json_version_id"),
            item.get("section_id"),
            item.get("table_id"),
        )
        in selected_keys
        and item.get("classification", {}).get("typed_control_disposition")
        == "PRIMARY_FINANCIAL_STATEMENT_SUMMARY"
        and len(item.get("classification", {}).get("family_root_row_ordinals", [])) == 1
    ]
    selected_note_components = [
        item
        for item in alternative.get("declared_money_table_inventory", [])
        if type(item) is dict
        and (
            item.get("page_json_version_id"),
            item.get("section_id"),
            item.get("table_id"),
        )
        in selected_keys
        and item.get("classification", {}).get("typed_control_disposition") is None
    ]
    if len(selected_primary_controls) != 1 or not selected_note_components:
        return None
    detailed_root_roles = (
        alternative_receipt.get("detailed_root_roles", [])
        if type(alternative_receipt) is dict
        else []
    )
    if (
        type(detailed_root_roles) is not list
        or not detailed_root_roles
        or any(type(role) is not str for role in detailed_root_roles)
        or any(
            sum(
                role in _classification_roles_v1(item["classification"])
                for item in selected_note_components
            )
            != 1
            for role in detailed_root_roles
        )
    ):
        return None
    receipt = canonical_clone_v1(alternative.get("owner_receipt"))
    if type(receipt) is not dict:
        return None
    receipt["service_activity_document_declared_recovery_policy"] = (
        DOCUMENT_DECLARED_RECOVERY_POLICY
    )
    return _reseal_cluster_v1(alternative, owner_receipt=receipt)


def _augment_primary_statement_source_result_cluster_v1(
    *,
    page_records: Sequence[Mapping[str, Any]],
    base_cluster: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Prepend one exact primary net-result control to a ready owner cluster."""

    regions = base_cluster.get("component_regions")
    inventory = base_cluster.get("declared_money_table_inventory")
    if (
        base_cluster.get("status") != "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
        or base_cluster.get("reasons")
        or type(regions) is not list
        or not regions
        or type(inventory) is not list
    ):
        return None
    records_by_version = {
        record.get("page_json_version_id"): record
        for record in page_records
        if type(record) is dict
        and type(record.get("page_json_version_id")) is str
        and type(record.get("page_json")) is dict
    }
    selected_keys = {
        (
            region.get("page_json_version_id"),
            region.get("section_id"),
            region.get("table_id"),
        )
        for region in regions
        if type(region) is dict
    }
    if len(selected_keys) != len(regions):
        return None
    selected_items = [
        item
        for item in inventory
        if type(item) is dict
        and (
            item.get("page_json_version_id"),
            item.get("section_id"),
            item.get("table_id"),
        )
        in selected_keys
    ]
    if len(selected_items) != len(regions) or any(
        item.get("classification", {}).get("typed_control_disposition") is not None
        for item in selected_items
    ):
        return None
    primary_items = [
        item
        for item in inventory
        if type(item) is dict
        and item.get("classification", {}).get("typed_control_disposition")
        == "PRIMARY_FINANCIAL_STATEMENT_SUMMARY"
        and item.get("classification", {}).get("ambiguous_rows") == []
        and len(item.get("classification", {}).get("family_root_row_ordinals", [])) == 1
        and set(compiled_specs.get("root_component_roles", [])).issubset(
            _classification_roles_v1(item["classification"])
        )
    ]
    if len(primary_items) != 1:
        return None

    def bound_table(
        item: Mapping[str, Any],
    ) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]] | None:
        record = records_by_version.get(item.get("page_json_version_id"))
        if type(record) is not dict:
            return None
        try:
            section, table = _source_table(
                record["page_json"],
                section_id=item["section_id"],
                table_id=item["table_id"],
            )
        except (KeyError, TypeError, ValueError):
            return None
        return record, section, table

    primary_item = primary_items[0]
    primary_bound = bound_table(primary_item)
    selected_bounds = [bound_table(item) for item in selected_items]
    if primary_bound is None or any(bound is None for bound in selected_bounds):
        return None
    primary_record, primary_section, primary_table = primary_bound
    primary_axis = _multitable_lane_axis(
        primary_section,
        primary_table,
        compiled_specs=compiled_specs,
    )
    primary_unit = _unit_axis(
        primary_table,
        compiled_specs=compiled_specs,
        document_unit_context=None,
    )
    if primary_axis.get("complete") is not True or primary_unit.get("complete") is not True:
        return None
    selected_axis_receipts = []
    selected_source_axes_exact = True
    for bound in selected_bounds:
        assert bound is not None
        _record, section, table = bound
        axis = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
        unit = _unit_axis(
            table,
            compiled_specs=compiled_specs,
            document_unit_context=None,
        )
        if (
            axis.get("complete") is not True
            or unit.get("complete") is not True
            or axis.get("lane_keys") != primary_axis.get("lane_keys")
            or axis.get("selected_metric_kinds")
            != primary_axis.get("selected_metric_kinds")
            or unit.get("canonical_unit") != primary_unit.get("canonical_unit")
        ):
            return None
        selected_source_axes_exact = bool(
            selected_source_axes_exact
            and axis.get("source_lane_keys") == primary_axis.get("source_lane_keys")
        )
        selected_axis_receipts.append(
            {
                "lane_keys": canonical_clone_v1(axis["lane_keys"]),
                "source_lane_keys": canonical_clone_v1(axis["source_lane_keys"]),
            }
        )
    primary_classification = primary_item["classification"]
    source_axis_rule = "IDENTICAL_EXACT_SOURCE_PERIOD_AXES"
    if not selected_source_axes_exact:
        primary_rows = primary_table.get("rows")
        primary_root_ordinal = primary_classification["family_root_row_ordinals"][0]
        primary_money_ordinals = primary_axis.get("money_column_ordinals")
        if (
            type(primary_rows) is not list
            or not 1 <= primary_root_ordinal <= len(primary_rows)
            or type(primary_money_ordinals) is not list
        ):
            return None
        primary_root_vector = _complete_source_vector_v1(
            primary_rows[primary_root_ordinal - 1], primary_money_ordinals
        )
        selected_root_vectors = []
        for item, bound, axis_receipt in zip(
            selected_items, selected_bounds, selected_axis_receipts, strict=True
        ):
            assert bound is not None
            _record, _section, table = bound
            classification = item["classification"]
            roots = classification.get("family_root_row_ordinals")
            rows = table.get("rows")
            if type(roots) is not list or len(roots) != 1 or type(rows) is not list:
                continue
            root_ordinal = roots[0]
            money_ordinals = classification.get("money_column_ordinals")
            if (
                type(root_ordinal) is not int
                or not 1 <= root_ordinal <= len(rows)
                or type(money_ordinals) is not list
            ):
                continue
            vector = _complete_source_vector_v1(
                rows[root_ordinal - 1], money_ordinals
            )
            if vector is not None:
                selected_root_vectors.append(vector)
                axis_receipt["family_root_source_coefficients"] = vector
        if (
            primary_root_vector is None
            or not any(primary_root_vector)
            or selected_root_vectors != [primary_root_vector]
        ):
            return None
        source_axis_rule = (
            "SEMANTIC_CURRENT_COMPARATIVE_AXES_WITH_ONE_IDENTICAL_NONZERO_EXACT_"
            "SOURCE_ROOT_VECTOR"
        )
    primary_region = {
        "component_roles": sorted(
            _classification_roles_v1(primary_classification)
        ),
        "document_id": primary_record["document_id"],
        "document_ordinal": primary_record["document_ordinal"],
        "fragment_ordinal": 1,
        "page_json_version_id": primary_record["page_json_version_id"],
        "physical_page": primary_record["physical_page"],
        "section_id": primary_item["section_id"],
        "selected_page_ordinal": primary_record["selected_page_ordinal"],
        "source_logical_name": primary_record["source_logical_name"],
        "source_sha256": primary_record["source_sha256"],
        "table_id": primary_item["table_id"],
    }
    augmented_regions = [primary_region]
    for fragment_ordinal, region in enumerate(regions, start=2):
        augmented_regions.append(
            {**canonical_clone_v1(region), "fragment_ordinal": fragment_ordinal}
        )
    receipt_material = {
        "acceptance_gate": (
            "FULL_F30_EVALUATOR_READY_WITH_NONEMPTY_MAPPINGS_AND_ZERO_REASONS"
        ),
        "canonical_unit": primary_unit["canonical_unit"],
        "policy": PRIMARY_SOURCE_RESULT_AUGMENTATION_POLICY,
        "primary_control": {
            "family_root_row_ordinal": primary_classification[
                "family_root_row_ordinals"
            ][0],
            "locator": canonical_clone_v1(primary_item["position"]),
            "root_component_roles": sorted(
                set(compiled_specs["root_component_roles"])
            ),
        },
        "primary_period_axis": {
            "lane_keys": canonical_clone_v1(primary_axis["lane_keys"]),
            "source_lane_keys": canonical_clone_v1(primary_axis["source_lane_keys"]),
        },
        "rule": (
            "UNIQUE_EXACT_TYPED_PRIMARY_SOURCE_RESULT_CONTROL_AND_READY_NOTE_"
            "POPULATION_HAVE_IDENTICAL_COMPLETE_SEMANTIC_PERIOD_AND_UNIT_AXES_"
            "WITH_IDENTICAL_SOURCE_PERIOD_AXES_OR_ONE_IDENTICAL_NONZERO_EXACT_"
            "SOURCE_ROOT_VECTOR_AND_FULL_EVALUATOR_CLOSURE_NO_SOURCE_MUTATION_"
            "NO_ARITHMETIC_BACKSOLVE"
        ),
        "selected_note_period_axes": selected_axis_receipts,
        "source_axis_rule": source_axis_rule,
    }
    receipt = {
        **receipt_material,
        "receipt_id": "gjsafav1:primary-source-result:"
        + canonical_json_sha256_v1(receipt_material),
    }
    selected_inventory = canonical_clone_v1(inventory)
    for item in selected_inventory:
        if (
            item.get("page_json_version_id") == primary_item["page_json_version_id"]
            and item.get("section_id") == primary_item["section_id"]
            and item.get("table_id") == primary_item["table_id"]
        ):
            item["disposition"] = "SELECTED_F30_PRIMARY_SOURCE_RESULT_CONTROL"
    owner_receipt = canonical_clone_v1(base_cluster.get("owner_receipt"))
    if type(owner_receipt) is not dict:
        return None
    owner_receipt["service_activity_primary_source_result_receipt"] = receipt
    augmented = _reseal_cluster_v1(
        base_cluster,
        component_regions=augmented_regions,
        declared_money_table_inventory=selected_inventory,
        owner_receipt=owner_receipt,
    )
    query_receipt = build_gemini_json_service_activity_region_query_receipt_v1(
        augmented_regions
    )
    candidate = evaluate_gemini_json_service_activity_family_cluster_v1(
        regions=augmented_regions,
        page_json_by_version={
            version_id: record["page_json"]
            for version_id, record in records_by_version.items()
        },
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if (
        candidate.get("status") != "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
        or candidate.get("reasons")
        or not candidate.get("mappings")
    ):
        return None
    return augmented


def _recover_adjacent_complementary_parent_cluster_v1(
    *,
    page_records: Sequence[Mapping[str, Any]],
    base_cluster: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Bind one exact adjacent expense table omitted by an income owner fence.

    Some issuers print service income and service expense as consecutive numbered
    disclosures.  The generic owner fence correctly selects the first disclosure,
    but Family 30 needs both declared parents to map the printed net result.  This
    recovery is deliberately narrower than a second owner search: the expense
    population must be the unique immediately following MONEY table, carry the
    complementary parent only, and expose the identical local period and unit
    axes.  Source pages and tables remain untouched.
    """

    regions = base_cluster.get("component_regions")
    inventory = base_cluster.get("declared_money_table_inventory")
    if (
        base_cluster.get("status") != "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
        or base_cluster.get("reasons")
        or type(regions) is not list
        or len(regions) != 1
        or type(inventory) is not list
        or compiled_specs.get("root_component_roles")
        != ["INCOME_PARENT", "EXPENSE_PARENT"]
    ):
        return None
    selected_region = regions[0]
    if type(selected_region) is not dict:
        return None
    selected_roles = {
        role
        for role in selected_region.get("component_roles", [])
        if type(role) is str
    }
    if "INCOME_PARENT" not in selected_roles or "EXPENSE_PARENT" in selected_roles:
        return None

    selected_indexes = [
        index
        for index, item in enumerate(inventory)
        if type(item) is dict
        and item.get("page_json_version_id")
        == selected_region.get("page_json_version_id")
        and item.get("section_id") == selected_region.get("section_id")
        and item.get("table_id") == selected_region.get("table_id")
        and item.get("disposition") == "SELECTED_FAMILY_COMPONENT"
    ]
    if len(selected_indexes) != 1:
        return None
    selected_index = selected_indexes[0]
    selected_item = inventory[selected_index]
    selected_classification = selected_item.get("classification")
    if (
        type(selected_classification) is not dict
        or selected_classification.get("typed_control_disposition") is not None
        or selected_classification.get("owner_visible") is not True
        or "INCOME_PARENT" not in _classification_roles_v1(selected_classification)
        or "EXPENSE_PARENT" in _classification_roles_v1(selected_classification)
    ):
        return None

    selected_position = selected_item.get("position")
    if (
        type(selected_position) is not list
        or len(selected_position) != 3
        or any(type(value) is not int for value in selected_position)
    ):
        return None
    role_eligible = []
    for index, item in enumerate(inventory):
        if index == selected_index or type(item) is not dict:
            continue
        classification = item.get("classification")
        position = item.get("position")
        if (
            type(classification) is not dict
            or type(position) is not list
            or len(position) != 3
            or any(type(value) is not int for value in position)
            or position <= selected_position
            or position[0] - selected_position[0] not in {0, 1}
            or item.get("disposition") != "OUTSIDE_SELECTED_OWNER_FENCE"
            or classification.get("typed_control_disposition") is not None
            or classification.get("owner_visible") is not True
        ):
            continue
        roles = _classification_roles_v1(classification)
        if "EXPENSE_PARENT" in roles and "INCOME_PARENT" not in roles:
            role_eligible.append((index, item))
    if len(role_eligible) != 1 or role_eligible[0][0] != selected_index + 1:
        return None
    candidate_index, candidate_item = role_eligible[0]
    del candidate_index

    records_by_version = {
        record.get("page_json_version_id"): record
        for record in page_records
        if type(record) is dict
        and type(record.get("page_json_version_id")) is str
        and type(record.get("page_json")) is dict
    }

    def bound_table(
        item: Mapping[str, Any],
    ) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]] | None:
        record = records_by_version.get(item.get("page_json_version_id"))
        if type(record) is not dict:
            return None
        page = record["page_json"]
        try:
            section, table = _source_table(
                page,
                section_id=item["section_id"],
                table_id=item["table_id"],
            )
        except (KeyError, TypeError, ValueError):
            return None
        return record, section, table

    selected_bound = bound_table(selected_item)
    candidate_bound = bound_table(candidate_item)
    if selected_bound is None or candidate_bound is None:
        return None
    selected_record, selected_section, selected_table = selected_bound
    candidate_record, candidate_section, candidate_table = candidate_bound
    if (
        candidate_record.get("document_id") != selected_record.get("document_id")
        or candidate_record.get("selected_page_ordinal")
        - selected_record.get("selected_page_ordinal", -2)
        not in {0, 1}
        or candidate_record.get("physical_page")
        - selected_record.get("physical_page", -2)
        not in {0, 1}
    ):
        return None

    selected_axis = _multitable_lane_axis(
        selected_section,
        selected_table,
        compiled_specs=compiled_specs,
    )
    candidate_axis = _multitable_lane_axis(
        candidate_section,
        candidate_table,
        compiled_specs=compiled_specs,
    )
    if (
        selected_axis.get("complete") is not True
        or candidate_axis.get("complete") is not True
        or not same_typed_json_v1(
            selected_axis.get("lane_keys"), candidate_axis.get("lane_keys")
        )
        or not same_typed_json_v1(
            selected_axis.get("source_lane_keys"),
            candidate_axis.get("source_lane_keys"),
        )
        or not same_typed_json_v1(
            selected_axis.get("money_column_ordinals"),
            candidate_axis.get("money_column_ordinals"),
        )
        or not same_typed_json_v1(
            selected_axis.get("selected_metric_kinds"),
            candidate_axis.get("selected_metric_kinds"),
        )
    ):
        return None
    selected_unit = _unit_axis(
        selected_table,
        compiled_specs=compiled_specs,
        document_unit_context=None,
    )
    candidate_unit = _unit_axis(
        candidate_table,
        compiled_specs=compiled_specs,
        document_unit_context=None,
    )
    if (
        selected_unit.get("complete") is not True
        or candidate_unit.get("complete") is not True
        or selected_unit.get("canonical_unit") != candidate_unit.get("canonical_unit")
    ):
        return None

    def exact_parent_row(
        classification: Mapping[str, Any],
        table: Mapping[str, Any],
        axis: Mapping[str, Any],
        role: str,
    ) -> dict[str, Any] | None:
        ordinals = {
            hit.get("row_ordinal")
            for hit in classification.get("role_hits", [])
            if type(hit) is dict
            and hit.get("role") == role
            and type(hit.get("row_ordinal")) is int
        }
        if not ordinals and classification.get("context_roles") == [role]:
            total_ordinals = {
                item.get("row_ordinal")
                for item in classification.get("total_rows", [])
                if type(item) is dict and type(item.get("row_ordinal")) is int
            }
            if len(total_ordinals) == 1:
                ordinals = total_ordinals
        rows = table.get("rows")
        ambiguous = {
            item.get("row_ordinal")
            for item in classification.get("ambiguous_rows", [])
            if type(item) is dict
        }
        money_ordinals = axis.get("money_column_ordinals")
        if (
            len(ordinals) != 1
            or type(rows) is not list
            or type(money_ordinals) is not list
        ):
            return None
        ordinal = next(iter(ordinals))
        if ordinal in ambiguous or not 1 <= ordinal <= len(rows):
            return None
        row = rows[ordinal - 1]
        if type(row) is not dict:
            return None
        vector = _complete_source_vector_v1(row, money_ordinals)
        if vector is None or not any(vector):
            return None
        return {"row_ordinal": ordinal, "source_coefficients": vector}

    selected_parent = exact_parent_row(
        selected_classification,
        selected_table,
        selected_axis,
        "INCOME_PARENT",
    )
    candidate_classification = candidate_item["classification"]
    candidate_parent = exact_parent_row(
        candidate_classification,
        candidate_table,
        candidate_axis,
        "EXPENSE_PARENT",
    )
    if selected_parent is None or candidate_parent is None:
        return None

    candidate_roles = sorted(_classification_roles_v1(candidate_classification))
    region = {
        "component_roles": candidate_roles,
        "document_id": candidate_record["document_id"],
        "document_ordinal": candidate_record["document_ordinal"],
        "fragment_ordinal": 2,
        "page_json_version_id": candidate_record["page_json_version_id"],
        "physical_page": candidate_record["physical_page"],
        "section_id": candidate_item["section_id"],
        "selected_page_ordinal": candidate_record["selected_page_ordinal"],
        "source_logical_name": candidate_record["source_logical_name"],
        "source_sha256": candidate_record["source_sha256"],
        "table_id": candidate_item["table_id"],
    }
    receipt_material = {
        "base_cluster_id": base_cluster.get("cluster_id"),
        "candidate_expense_parent": {
            "component_roles": candidate_roles,
            "locator": canonical_clone_v1(candidate_item["position"]),
            **candidate_parent,
        },
        "canonical_unit": selected_unit["canonical_unit"],
        "period_axis": {
            "lane_keys": canonical_clone_v1(selected_axis["lane_keys"]),
            "selected_source_lane_keys": canonical_clone_v1(
                selected_axis["source_lane_keys"]
            ),
            "candidate_source_lane_keys": canonical_clone_v1(
                candidate_axis["source_lane_keys"]
            ),
        },
        "policy": ADJACENT_COMPLEMENTARY_PARENT_POLICY,
        "rule": (
            "UNIQUE_IMMEDIATE_NEXT_DECLARED_MONEY_TABLE_OUTSIDE_SELECTED_OWNER_FENCE_"
            "HAS_EXACT_COMPLEMENTARY_EXPENSE_PARENT_AND_IDENTICAL_LOCAL_PERIOD_UNIT_"
            "AXES_NO_SOURCE_MUTATION"
        ),
        "selected_income_parent": {
            "component_roles": sorted(selected_roles),
            "locator": canonical_clone_v1(selected_item["position"]),
            **selected_parent,
        },
    }
    recovery_receipt = {
        **receipt_material,
        "receipt_id": "gjsafav1:adjacent-complementary-parent:"
        + canonical_json_sha256_v1(receipt_material),
    }
    selected_inventory = canonical_clone_v1(inventory)
    selected_inventory[selected_index + 1]["disposition"] = (
        "SELECTED_F30_ADJACENT_COMPLEMENTARY_PARENT"
    )
    owner_receipt = canonical_clone_v1(base_cluster.get("owner_receipt"))
    if type(owner_receipt) is not dict:
        return None
    owner_receipt["service_activity_adjacent_complementary_parent_receipt"] = (
        recovery_receipt
    )
    return _reseal_cluster_v1(
        base_cluster,
        component_regions=[canonical_clone_v1(selected_region), region],
        declared_money_table_inventory=selected_inventory,
        owner_receipt=owner_receipt,
    )


def recover_gemini_json_service_activity_query_cluster_v1(
    *,
    page_records: Any,
    base_cluster: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply every exact Family-30-only query recovery to a generic cluster."""

    if compiled_specs.get("topology", {}).get("family_id") != FAMILY_ID:
        raise _error("service-activity adapter received another family")
    document_declared = (
        _recover_document_declared_cluster_v1(
            page_records=page_records,
            base_cluster=base_cluster,
            compiled_specs=compiled_specs,
        )
        if type(page_records) in {list, tuple}
        else None
    )
    base = base_cluster if document_declared is None else document_declared
    recovered = recover_gemini_json_service_activity_owner_only_continuation_v1(
        page_records=page_records,
        base_cluster=base,
        compiled_specs=compiled_specs,
    )
    if type(page_records) not in {list, tuple}:
        return recovered
    complemented = _recover_adjacent_complementary_parent_cluster_v1(
        page_records=page_records,
        base_cluster=recovered,
        compiled_specs=compiled_specs,
    )
    completed = recovered if complemented is None else complemented
    primary_augmented = _augment_primary_statement_source_result_cluster_v1(
        page_records=page_records,
        base_cluster=completed,
        compiled_specs=compiled_specs,
    )
    return completed if primary_augmented is None else primary_augmented


def _region_table(
    pages: Mapping[str, dict[str, Any]], region: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    page = pages.get(region.get("page_json_version_id"))
    if type(page) is not dict:
        raise _error("service-activity selected page JSON is absent")
    try:
        return _source_table(
            page,
            section_id=region["section_id"],
            table_id=region["table_id"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise _error("service-activity selected source table is invalid") from exc


def _repair_receipt(
    *, repair: Mapping[str, Any], compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    material = {
        "base_page_json_sha256": repair["base_page_json_sha256"],
        "base_page_json_version_id": repair["base_page_json_version_id"],
        "cell_axis_sha256": canonical_json_sha256_v1(repair["cell_repairs"]),
        "effective_page_json_sha256": repair["effective_page_json_sha256"],
        "overlay_id": compiled_specs["service_activity_source_repair_overlay"]["overlay_id"],
        "repair_id": repair["repair_id"],
        "row_axis_sha256": canonical_json_sha256_v1(repair["row_repairs"]),
        "rule": (
            "EXACT_CONTENT_ADDRESSED_SOURCE_PAGE_IMAGE_SELECTED_JSON_TABLE_"
            "VISIBLE_CELL_OR_LABEL_TRANSCRIPTION_ONLY_NO_EQUATION_BACKSOLVE"
        ),
        "source_binding": canonical_clone_v1(repair["source_binding"]),
        "status": "AUTHENTICATED_PDF_VISIBLE_SOURCE_TRANSCRIBED",
        "table_ref": canonical_clone_v1(repair["table_ref"]),
        "visual_evidence": canonical_clone_v1(repair["visual_evidence"]),
    }
    return {
        **material,
        "receipt_id": "gjsafav1:repair-receipt:" + canonical_json_sha256_v1(material),
    }


def _apply_authenticated_source_repairs_v1(
    *,
    regions: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Apply only authenticated literal transcriptions to private page clones."""

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
    overlay = compiled_specs.get("service_activity_source_repair_overlay")
    if type(overlay) is not dict:
        raise _error("service-activity compiled source-repair overlay is invalid")
    for repair in overlay["repairs"]:
        source = repair["source_binding"]
        table_ref = repair["table_ref"]
        key = (
            repair["base_page_json_version_id"],
            source["physical_page"],
            table_ref["section_id"],
            table_ref["table_id"],
        )
        region = region_keys.get(key)
        if region is None:
            continue
        if (
            region.get("source_logical_name") != source["source_logical_name"]
            or region.get("source_sha256") != source["source_sha256"]
        ):
            raise _error("service-activity source-repair source identity drifted")
        version_id = repair["base_page_json_version_id"]
        base_page = page_json_by_version.get(version_id)
        if (
            type(base_page) is not dict
            or canonical_json_sha256_v1(base_page) != repair["base_page_json_sha256"]
        ):
            raise _error("service-activity source-repair base page drifted")
        _base_section, base_table = _source_table(
            base_page,
            section_id=table_ref["section_id"],
            table_id=table_ref["table_id"],
        )
        if canonical_json_sha256_v1(base_table) != table_ref["base_table_sha256"]:
            raise _error("service-activity source-repair base table drifted")
        _section, table = _source_table(
            pages[version_id],
            section_id=table_ref["section_id"],
            table_id=table_ref["table_id"],
        )
        rows = table.get("rows")
        columns = table.get("columns")
        if type(rows) is not list or type(columns) is not list:
            raise _error("service-activity source-repair table axes are invalid")

        for cell in repair["cell_repairs"]:
            match = re.fullmatch(
                r"r([1-9][0-9]*):c([1-9][0-9]*)",
                cell["cell_id"],
            )
            if match is None:
                raise _error("service-activity source-repair cell identity drifted")
            row_index = int(match.group(1)) - 1
            column_index = int(match.group(2)) - 1
            if not (0 <= row_index < len(rows) and 0 <= column_index < len(columns)):
                raise _error("service-activity source-repair cell is outside its table")
            row = rows[row_index]
            column = columns[column_index]
            values = row.get("values_exact") if type(row) is dict else None
            if (
                type(row) is not dict
                or type(column) is not dict
                or column.get("value_kind") != "MONEY"
                or type(values) is not list
                or len(values) != len(columns)
                or row.get("label_exact") != cell["row_label_exact"]
                or not same_typed_json_v1(
                    row.get("hierarchy_path_exact"),
                    cell["row_hierarchy_path_exact"],
                )
                or not same_typed_json_v1(
                    column.get("header_path_exact"),
                    cell["column_header_path_exact"],
                )
                or not same_typed_json_v1(values[column_index], cell["before_exact"])
            ):
                raise _error("service-activity source-repair cell binding drifted")
            values[column_index] = cell["after_exact"]

        for row_repair in repair["row_repairs"]:
            row_index = int(row_repair["row_id"][1:]) - 1
            if not 0 <= row_index < len(rows):
                raise _error("service-activity source-repair row is outside its table")
            row = rows[row_index]
            if (
                type(row) is not dict
                or row.get("row_kind") != row_repair["row_kind"]
                or row.get("label_exact") != row_repair["before_label_exact"]
                or not same_typed_json_v1(
                    row.get("hierarchy_path_exact"),
                    row_repair["before_hierarchy_path_exact"],
                )
            ):
                raise _error("service-activity source-repair row binding drifted")
            row["label_exact"] = row_repair["after_label_exact"]
            row["hierarchy_path_exact"] = canonical_clone_v1(
                row_repair["after_hierarchy_path_exact"]
            )

        if canonical_json_sha256_v1(table) != table_ref["effective_table_sha256"]:
            raise _error("service-activity source-repair effective table drifted")
        if canonical_json_sha256_v1(pages[version_id]) != repair["effective_page_json_sha256"]:
            raise _error("service-activity source-repair effective page drifted")
        receipts.append(_repair_receipt(repair=repair, compiled_specs=compiled_specs))
    receipts.sort(key=lambda item: item["repair_id"])
    return pages, receipts


def _normalize_governed_duration_headers_v1(
    *,
    pages: dict[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Remove only whole header components that are pure duration governors."""

    receipts = []
    for region in regions:
        _section, table = _region_table(pages, region)
        columns = table.get("columns")
        money = [
            (ordinal, column)
            for ordinal, column in enumerate(
                columns if type(columns) is list else [],
                start=1,
            )
            if type(column) is dict and column.get("value_kind") == "MONEY"
        ]
        if len(money) < 2:
            continue
        before = []
        after = []
        complete = True
        changed = False
        for _ordinal, column in money:
            path = column.get("header_path_exact")
            if type(path) is not list or not path:
                complete = False
                break
            stripped = [
                item
                for item in path
                if not (
                    type(item) is str
                    and _DURATION_GOVERNOR.fullmatch(_normalized(item)) is not None
                )
            ]
            if not stripped:
                complete = False
                break
            before.append(canonical_clone_v1(path))
            after.append(canonical_clone_v1(stripped))
            changed = changed or not same_typed_json_v1(path, stripped)
        if not complete or not changed:
            continue
        if any(same_typed_json_v1(left, right) for left, right in zip(before, after, strict=True)):
            continue
        for (_ordinal, column), path in zip(money, after, strict=True):
            column["header_path_exact"] = path
        material = {
            "after_header_paths_exact": after,
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
            "money_column_ordinals": [ordinal for ordinal, _column in money],
            "rule": (
                "WHOLE_COMPONENT_GOVERNED_CUMULATIVE_DURATION_PHRASE_REMOVED_"
                "BEFORE_CURRENT_COMPARATIVE_PERIOD_SEMANTICS"
            ),
        }
        receipts.append(
            {
                **material,
                "receipt_id": "gjsafav1:period:" + canonical_json_sha256_v1(material),
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


def _target_family_control_vectors(
    *,
    page: Mapping[str, Any],
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Inventory only complete, nonzero, source-visible semantic controls.

    A unitless note can be corroborated by its printed family root or by either
    printed root-component parent.  The semantic role is part of the evidence:
    an equal number belonging to another statement row is never a match.  This
    function neither sums rows nor repairs an unobserved lane.
    """

    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        page, section, table, compiled_specs=compiled_specs
    )
    money_ordinals = classification.get("money_column_ordinals")
    rows = table.get("rows")
    if type(money_ordinals) is not list or len(money_ordinals) != 2 or type(rows) is not list:
        return []
    ambiguous_ordinals = {
        item.get("row_ordinal") for item in classification.get("ambiguous_rows", [])
    }
    ordinals_by_role: dict[str, set[int]] = {
        "FAMILY_ROOT_TOTAL": {
            ordinal
            for ordinal in classification.get("family_root_row_ordinals", [])
            if type(ordinal) is int
        }
    }
    component_roles = set(compiled_specs.get("root_component_roles", []))
    for hit in classification.get("role_hits", []):
        role = hit.get("role")
        ordinal = hit.get("row_ordinal")
        if role in component_roles and type(ordinal) is int:
            ordinals_by_role.setdefault(role, set()).add(ordinal)

    controls = []
    for role, ordinals in sorted(ordinals_by_role.items()):
        if len(ordinals) != 1:
            continue
        ordinal = next(iter(ordinals))
        if ordinal in ambiguous_ordinals or not (1 <= ordinal <= len(rows)):
            continue
        row = rows[ordinal - 1]
        if type(row) is not dict:
            continue
        vector = _observed_vector(row, money_ordinals)
        if vector is None or not any(vector):
            continue
        controls.append(
            {
                "coefficients": vector,
                "money_column_ordinals": list(money_ordinals),
                "row_ordinal": ordinal,
                "semantic_role": role,
                "source_kind": "SOURCE_VISIBLE_COMPLETE_NONZERO_SEMANTIC_CONTROL",
            }
        )
    return controls


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


def _primary_statement_service_activity_controls(
    pages: Mapping[str, dict[str, Any]], compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    roles_by_alias: dict[str, set[str]] = {}
    for alias in compiled_specs["topology"]["parent"]["aliases"]:
        roles_by_alias.setdefault(_normalized(alias), set()).add("FAMILY_ROOT_TOTAL")
    for role in compiled_specs.get("root_component_roles", []):
        for alias in compiled_specs.get("aliases_by_role", {}).get(role, []):
            roles_by_alias.setdefault(_normalized(alias), set()).add(role)
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
                    semantic_roles = roles_by_alias.get(folded, set())
                    if len(semantic_roles) != 1:
                        continue
                    semantic_role = next(iter(semantic_roles))
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
                            "semantic_role": semantic_role,
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
    primary_controls = _primary_statement_service_activity_controls(pages, compiled_specs)
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
        targets = _target_family_control_vectors(
            page=pages[region["page_json_version_id"]],
            section=section,
            table=table,
            compiled_specs=compiled_specs,
        )
        if not targets:
            continue
        matches = []
        matched_targets = []
        for target in targets:
            target_matches = []
            target_vector = target["coefficients"]
            for primary in primary_controls:
                if primary["semantic_role"] != target["semantic_role"]:
                    continue
                coefficients = primary["coefficients"]
                matching_starts = [
                    start
                    for start in range(len(coefficients) - len(target_vector) + 1)
                    if coefficients[start : start + len(target_vector)] == target_vector
                ]
                if not matching_starts:
                    continue
                match = {
                    **canonical_clone_v1(primary),
                    "matched_primary_money_column_ordinal_axes": [
                        primary["money_column_ordinals"][start : start + len(target_vector)]
                        for start in matching_starts
                    ],
                }
                if len(matching_starts) == 1:
                    match["matched_primary_money_column_ordinals"] = match[
                        "matched_primary_money_column_ordinal_axes"
                    ][0]
                target_matches.append(match)
            if target_matches:
                matches.extend(target_matches)
                matched_targets.append(canonical_clone_v1(target))
        units = {item["canonical_unit"] for item in matches}
        if len(units) != 1:
            continue
        canonical_unit = next(iter(units))
        unit_exact_by_canonical = {"MILLION_VND": "Triệu đồng", "VND": "VND"}
        if canonical_unit not in unit_exact_by_canonical:
            continue
        table["unit_exact"] = unit_exact_by_canonical[canonical_unit]
        material = {
            "canonical_unit": canonical_unit,
            "matched_primary_controls": canonical_clone_v1(matches),
            "matched_target_controls": matched_targets,
            "rule": (
                "UNITLESS_SERVICE_ACTIVITY_NOTE_ONE_OR_MORE_VISIBLE_NONZERO_SEMANTIC_"
                "ROOT_OR_PARENT_CONTROLS_EQUAL_ONE_CANONICAL_UNIT_PRIMARY_STATEMENT_"
                "SAME_ROLE_ONE_OR_MORE_CONTIGUOUS_PERIOD_VECTOR_OCCURRENCES_"
                "NO_MAGNITUDE_INFERENCE"
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
        }
        receipts.append(
            {
                **material,
                "receipt_id": "gjsafav1:unit:" + canonical_json_sha256_v1(material),
            }
        )
    return receipts


def _reseal_candidate(
    candidate: dict[str, Any],
    *,
    source_repair_receipts: Sequence[Mapping[str, Any]],
    period_receipts: Sequence[Mapping[str, Any]],
    unit_receipts: Sequence[Mapping[str, Any]],
    root_fallback_receipt: Mapping[str, Any] | None,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        not source_repair_receipts
        and not period_receipts
        and not unit_receipts
        and root_fallback_receipt is None
    ):
        return candidate
    material = {
        "adapter_format_version": ADAPTER_FORMAT_VERSION,
        "period_normalization_receipts": canonical_clone_v1(list(period_receipts)),
        "shared_engine_claim_boundary": SHARED_CLAIM_BOUNDARY,
        "source_repair_overlay_id": compiled_specs["service_activity_source_repair_overlay"][
            "overlay_id"
        ],
        "source_repair_receipts": canonical_clone_v1(list(source_repair_receipts)),
        "source_repair_spec_sha256": compiled_specs["service_activity_source_repair_spec_sha256"],
        "unit_corroboration_receipts": canonical_clone_v1(list(unit_receipts)),
    }
    if root_fallback_receipt is not None:
        material["root_alternative_legacy_fallback_receipt"] = canonical_clone_v1(
            root_fallback_receipt
        )
    candidate["claim_boundary"] = CLAIM_BOUNDARY
    candidate["closure_receipt"]["service_activity_adapter_receipt"] = {
        **material,
        "adapter_receipt_id": "gjsafav1:receipt:" + canonical_json_sha256_v1(material),
    }
    candidate_material = {key: candidate[key] for key in candidate if key != "candidate_id"}
    candidate["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        candidate_material
    )
    return candidate


def _replace_partial_root_parent_mappings_with_exact_primary_controls_v1(
    *,
    candidate: Mapping[str, Any],
    pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Replace an incomplete derived parent with its exact primary source row.

    The shared evaluator must already have proved the printed primary root
    against the printed primary parents. A replacement is allowed only for a
    parent mapping containing an unobserved lane, and every already observed
    lane must equal the corresponding primary source cell. No note cell changes.
    """

    root_roles = compiled_specs.get("root_component_roles")
    mappings = candidate.get("mappings")
    if (
        type(root_roles) is not list
        or not root_roles
        or any(type(role) is not str for role in root_roles)
        or type(mappings) is not list
    ):
        return None
    mappings_by_role: dict[str, list[Mapping[str, Any]]] = {}
    for role in root_roles:
        mappings_by_role[role] = [
            mapping
            for mapping in mappings
            if type(mapping) is dict and mapping.get("role") == role
        ]
    if any(len(mappings_by_role[role]) != 1 for role in root_roles):
        return None
    partial_roles = [
        role
        for role in root_roles
        if any(
            type(cell) is dict and cell.get("coefficient") is None
            for cell in mappings_by_role[role][0].get("values", [])
        )
    ]
    if not partial_roles:
        return None

    root_mappings = [
        mapping
        for mapping in mappings
        if type(mapping) is dict and mapping.get("role") == "FAMILY_ROOT_TOTAL"
    ]
    root_receipts = candidate.get("closure_receipt", {}).get(
        "root_component_sum_receipts"
    )
    if (
        len(root_mappings) != 1
        or type(root_receipts) is not list
        or any(
            type(cell) is not dict
            or type(cell.get("coefficient")) is not int
            or type(cell.get("source_text")) is not str
            for cell in root_mappings[0].get("values", [])
        )
    ):
        return None
    direct_receipts = [
        receipt
        for receipt in root_receipts
        if type(receipt) is dict
        and receipt.get("rule")
        == (
            "SOURCE_VISIBLE_FAMILY_ROOT_USES_UNIQUE_TABLE_LOCAL_DIRECT_FRONTIER_"
            "EACH_BLANK_LANE_REMAINS_INCOMPLETE_DISCLOSURE_MAPPINGS_ARE_NOT_"
            "ASSUMED_ADDITIVE"
        )
        and receipt.get("result_state")
        == "SOURCE_VISIBLE_FAMILY_ROOT_BOUND_TO_UNIQUE_EXACT_TABLE_FRONTIER"
        and type(receipt.get("component_source_refs")) is list
        and len(receipt["component_source_refs"]) == len(root_roles)
    ]
    if len(direct_receipts) != 1:
        return None
    direct_receipt = direct_receipts[0]
    replacement_by_role: dict[str, dict[str, Any]] = {}
    replacement_receipts = []
    primary_table_keys = set()
    for role, source_refs in zip(
        root_roles,
        direct_receipt["component_source_refs"],
        strict=True,
    ):
        if role not in partial_roles:
            continue
        if type(source_refs) is not list or len(source_refs) != 1:
            return None
        source_ref = source_refs[0]
        locator = source_ref.get("locator") if type(source_ref) is dict else None
        if type(locator) is not dict:
            return None
        version_id = locator.get("page_json_version_id")
        page = pages.get(version_id) if type(version_id) is str else None
        if type(page) is not dict or page.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
            return None
        try:
            section, table = _source_table(
                page,
                section_id=locator["section_id"],
                table_id=locator["table_id"],
            )
        except (KeyError, TypeError, ValueError):
            return None
        classification = classify_gemini_json_multitable_hierarchical_table_v1(
            page,
            section,
            table,
            compiled_specs=compiled_specs,
        )
        role_ordinals = {
            hit.get("row_ordinal")
            for hit in classification.get("role_hits", [])
            if hit.get("role") == role
        }
        row_ordinal = source_ref.get("row_ordinal")
        money_ordinals = source_ref.get("money_column_ordinals")
        rows = table.get("rows")
        lane_axis = _multitable_lane_axis(
            section,
            table,
            compiled_specs=compiled_specs,
        )
        unit_axis = _unit_axis(
            table,
            compiled_specs=compiled_specs,
            document_unit_context=None,
        )
        mapping = mappings_by_role[role][0]
        if (
            classification.get("typed_control_disposition")
            != "PRIMARY_FINANCIAL_STATEMENT_SUMMARY"
            or role_ordinals != {row_ordinal}
            or type(row_ordinal) is not int
            or type(rows) is not list
            or not 1 <= row_ordinal <= len(rows)
            or type(money_ordinals) is not list
            or lane_axis.get("complete") is not True
            or lane_axis.get("money_column_ordinals") != money_ordinals
            or unit_axis.get("complete") is not True
            or unit_axis.get("canonical_unit") != mapping.get("unit")
        ):
            return None
        row = rows[row_ordinal - 1]
        if (
            type(row) is not dict
            or source_ref.get("row_id") != f"r{row_ordinal}"
            or source_ref.get("label_exact") != row.get("label_exact")
            or not same_typed_json_v1(
                source_ref.get("hierarchy_path_exact"),
                row.get("hierarchy_path_exact"),
            )
        ):
            return None
        values = row.get("values_exact")
        if (
            type(values) is not list
            or any(ordinal > len(values) for ordinal in money_ordinals)
        ):
            return None
        source_cells = [
            _source_money(values[ordinal - 1]) for ordinal in money_ordinals
        ]
        current_cells = mapping.get("values")
        if (
            type(current_cells) is not list
            or len(current_cells) != len(source_cells)
            or any(
                type(cell.get("coefficient")) is not int
                or type(cell.get("source_text")) is not str
                for cell in source_cells
            )
            or any(
                type(current.get("coefficient")) is int
                and current["coefficient"] != source["coefficient"]
                for current, source in zip(current_cells, source_cells, strict=True)
                if type(current) is dict
            )
        ):
            return None
        material = {
            "report_norm_id": mapping["report_norm_id"],
            "role": role,
            "row_id": source_ref["row_id"],
            "source_refs": [canonical_clone_v1(source_ref)],
            "state": "SOURCE_OBSERVED_PRIMARY_STATEMENT_ROOT_COMPONENT_CONTROL",
            "unit": mapping["unit"],
            "values": canonical_clone_v1(source_cells),
        }
        replacement = {
            **material,
            "item_mapping_id": "gjmthfmv1:item:"
            + canonical_json_sha256_v1(material),
        }
        replacement_by_role[role] = replacement
        primary_table_keys.add(
            (
                locator.get("page_json_version_id"),
                locator.get("section_id"),
                locator.get("table_id"),
            )
        )
        replacement_receipts.append(
            {
                "original_mapping_id": mapping.get("item_mapping_id"),
                "replacement_mapping_id": replacement["item_mapping_id"],
                "role": role,
                "source_coefficients": [cell["coefficient"] for cell in source_cells],
                "source_ref": canonical_clone_v1(source_ref),
            }
        )
    if set(replacement_by_role) != set(partial_roles) or len(primary_table_keys) != 1:
        return None
    recovered = canonical_clone_v1(candidate)
    recovered["mappings"] = [
        replacement_by_role.get(mapping.get("role"), mapping)
        if type(mapping) is dict
        else mapping
        for mapping in recovered["mappings"]
    ]
    receipt_material = {
        "direct_primary_root_receipt_sha256": canonical_json_sha256_v1(
            direct_receipt
        ),
        "policy": ROOT_ALTERNATIVE_PRIMARY_PARENT_CONTROL_FALLBACK_POLICY,
        "replacement_receipts": replacement_receipts,
        "rule": (
            "SHARED_ENGINE_FIRST_PROVES_ONE_EXACT_PRIMARY_ROOT_PARENT_EQUATION_"
            "THEN_EACH_PARTIAL_PARENT_MAPPING_IS_REPLACED_BY_ITS_SAME_VISIBLE_"
            "PRIMARY_SOURCE_ROW_ONLY_WHEN_ALL_ALREADY_OBSERVED_LANES_MATCH_"
            "NO_BLANK_FILL_NO_ARITHMETIC_BACKSOLVE"
        ),
    }
    return recovered, {
        **receipt_material,
        "receipt_id": "gjsafav1:primary-parent-control:"
        + canonical_json_sha256_v1(receipt_material),
    }


def _evaluate_root_alternative_legacy_fallback_v1(
    *,
    initial_candidate: dict[str, Any],
    regions: Sequence[Mapping[str, Any]],
    pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Preserve the declared two-parent path when no alternative population exists."""

    declarations = compiled_specs.get("root_component_role_combinations")
    if (
        type(declarations) is not list
        or len(declarations) < 2
        or initial_candidate.get("status") != "UNRESOLVED_GEMINI_JSON_FAMILY"
        or initial_candidate.get("mappings")
    ):
        return initial_candidate, None
    first = declarations[0]
    if (
        type(first) is not dict
        or first.get("roles") != compiled_specs.get("root_component_roles")
        or first.get("equation_policy")
        != compiled_specs.get("root_component_equation_policy")
        or first.get("component_frontier_equation_policy") != "DECLARED_DIRECT_SUM"
    ):
        return initial_candidate, None
    alternative_roles = {
        role
        for declaration in declarations[1:]
        if type(declaration) is dict and type(declaration.get("roles")) is list
        for role in declaration["roles"]
        if type(role) is str
    }
    observed_source_only_roles = {
        item.get("declared_role")
        for item in initial_candidate.get("closure_receipt", {}).get(
            "source_only_unmapped_rows", []
        )
        if type(item) is dict and type(item.get("declared_role")) is str
    }
    if alternative_roles & observed_source_only_roles:
        return initial_candidate, None
    legacy_specs = canonical_clone_v1(compiled_specs)
    legacy_specs.pop("root_component_role_combinations", None)
    fallback = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=regions,
        page_json_by_version=pages,
        compiled_specs=legacy_specs,
        query_receipt=query_receipt,
    )
    primary_parent_control_receipt = None
    if (
        initial_candidate.get("reasons")
        == ["FAMILY_ROOT_DECLARED_COMPONENT_ALTERNATIVE_INCOMPLETE"]
        and fallback.get("status") == "UNRESOLVED_GEMINI_JSON_FAMILY"
        and fallback.get("reasons")
        == ["FAMILY_ROOT_DECLARED_COMPONENT_SIGN_ORIENTATION_MISMATCH"]
        and not fallback.get("mappings")
    ):
        direct_specs = canonical_clone_v1(legacy_specs)
        direct_specs["root_component_equation_policy"] = "DECLARED_DIRECT_SUM"
        direct_specs["evaluation"]["root_component_equation_policy"] = (
            "DECLARED_DIRECT_SUM"
        )
        direct = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
            regions=regions,
            page_json_by_version=pages,
            compiled_specs=direct_specs,
            query_receipt=query_receipt,
        )
        recovered = _replace_partial_root_parent_mappings_with_exact_primary_controls_v1(
            candidate=direct,
            pages=pages,
            compiled_specs=compiled_specs,
        )
        if recovered is not None:
            fallback, primary_parent_control_receipt = recovered
    root_mappings = [
        mapping
        for mapping in fallback.get("mappings", [])
        if type(mapping) is dict and mapping.get("role") == "FAMILY_ROOT_TOTAL"
    ]
    root_receipts = fallback.get("closure_receipt", {}).get(
        "root_component_sum_receipts"
    )
    common_ready = (
        fallback.get("status") != "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
        or fallback.get("reasons")
        or len(root_mappings) != 1
        or type(root_receipts) is not list
    )
    if common_ready:
        return initial_candidate, None
    derived_root = bool(
        root_mappings[0].get("state")
        == "DECLARED_FAMILY_ROOT_DERIVED_FROM_COMPLETE_TOP_LEVEL_COMPONENT_SUM"
        and len(root_receipts) == 1
        and root_receipts[0].get("component_roles") == first["roles"]
        and root_receipts[0].get("rule")
        == "COMPLETE_DECLARED_TOP_LEVEL_ROLE_FRONTIER_DIRECT_SUM_NO_BACKSOLVE"
    )
    direct_receipts = [
        receipt
        for receipt in root_receipts
        if type(receipt) is dict
        and receipt.get("rule")
        == (
            "SOURCE_VISIBLE_FAMILY_ROOT_USES_UNIQUE_TABLE_LOCAL_DIRECT_FRONTIER_"
            "EACH_BLANK_LANE_REMAINS_INCOMPLETE_DISCLOSURE_MAPPINGS_ARE_NOT_"
            "ASSUMED_ADDITIVE"
        )
        and receipt.get("result_state")
        == "SOURCE_VISIBLE_FAMILY_ROOT_BOUND_TO_UNIQUE_EXACT_TABLE_FRONTIER"
    ]
    equation_receipts = [
        receipt
        for receipt in root_receipts
        if type(receipt) is dict
        and receipt.get("component_roles") == first["roles"]
        and receipt.get("rule")
        == "UNIQUE_PLUS_MINUS_ONE_ORIENTATION_FIRST_DECLARED_COMPONENT_POSITIVE"
        and receipt.get("result_role") == "FAMILY_ROOT_TOTAL"
    ]
    source_visible_root = bool(
        root_mappings[0].get("state")
        == "SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_BY_DIRECT_FRONTIER"
        and len(root_receipts) == 2
        and len(direct_receipts) == 1
        and len(equation_receipts) == 1
        and all(
            value.get("state") == "RAW_SIGNED_INTEGER"
            for value in root_mappings[0].get("values", [])
            if type(value) is dict
        )
        and len(root_mappings[0].get("values", [])) > 0
    )
    primary_parent_control_root = primary_parent_control_receipt is not None
    if not derived_root and not source_visible_root and not primary_parent_control_root:
        return initial_candidate, None
    material = {
        "first_declared_legacy_alternative": canonical_clone_v1(first),
        "initial_candidate_id": initial_candidate.get("candidate_id"),
        "initial_reasons": canonical_clone_v1(initial_candidate.get("reasons", [])),
        "other_declared_alternative_roles": sorted(alternative_roles),
    }
    if primary_parent_control_root:
        material.update(
            {
                "policy": ROOT_ALTERNATIVE_PRIMARY_PARENT_CONTROL_FALLBACK_POLICY,
                "primary_parent_control_receipt": primary_parent_control_receipt,
                "root_evidence_receipts_sha256": canonical_json_sha256_v1(
                    root_receipts
                ),
                "rule": (
                    "RETRY_WITH_DIRECT_SOURCE_SIGNS_ONLY_AFTER_THE_DECLARED_"
                    "ALTERNATIVE_AND_SIGNED_LEGACY_PATHS_FAIL_EXACTLY_THEN_BIND_"
                    "EACH_PARTIAL_PARENT_TO_ITS_SHARED_ENGINE_PROVEN_PRIMARY_ROW"
                ),
            }
        )
    elif derived_root:
        material.update(
            {
                "policy": ROOT_ALTERNATIVE_LEGACY_FALLBACK_POLICY,
                "root_component_sum_receipt_sha256": canonical_json_sha256_v1(
                    root_receipts[0]
                ),
                "rule": (
                    "RETRY_WITHOUT_ALTERNATIVE_SELECTOR_ONLY_AFTER_OTHER_ALTERNATIVE_"
                    "ROLES_ARE_ABSENT_AND_ACCEPT_ONLY_EXACT_COMPLETE_LEGACY_"
                    "COMPONENT_SUM"
                ),
            }
        )
    else:
        material.update(
            {
                "policy": ROOT_ALTERNATIVE_PRIMARY_SOURCE_RESULT_FALLBACK_POLICY,
                "root_evidence_receipts_sha256": canonical_json_sha256_v1(root_receipts),
                "rule": (
                    "RETRY_WITHOUT_ALTERNATIVE_SELECTOR_ONLY_AFTER_OTHER_ALTERNATIVE_"
                    "ROLES_ARE_ABSENT_AND_ACCEPT_ONLY_UNIQUE_SOURCE_VISIBLE_PRIMARY_"
                    "RESULT"
                ),
            }
        )
    return fallback, {
        **material,
        "receipt_id": "gjsafav1:root-alternative-fallback:"
        + canonical_json_sha256_v1(material),
    }


def evaluate_gemini_json_service_activity_family_cluster_v1(
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate Family 30 after only exact, replayable source normalisation."""

    if compiled_specs.get("topology", {}).get("family_id") != FAMILY_ID:
        raise _error("service-activity adapter received another family")
    expected_receipt = build_gemini_json_service_activity_region_query_receipt_v1(regions)
    if type(query_receipt) is not dict or not same_typed_json_v1(query_receipt, expected_receipt):
        raise _error("service-activity query receipt does not bind exact fragments")
    region_axis = expected_receipt["region_axis"]
    pages, source_repairs = _apply_authenticated_source_repairs_v1(
        regions=region_axis,
        page_json_by_version=page_json_by_version,
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
    candidate, root_fallback_receipt = _evaluate_root_alternative_legacy_fallback_v1(
        initial_candidate=candidate,
        regions=region_axis,
        pages=pages,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    return _reseal_candidate(
        candidate,
        source_repair_receipts=source_repairs,
        period_receipts=period_receipts,
        unit_receipts=unit_receipts,
        root_fallback_receipt=root_fallback_receipt,
        compiled_specs=compiled_specs,
    )


def validate_gemini_json_service_activity_family_candidate_replay_v1(
    value: Any,
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    expected = evaluate_gemini_json_service_activity_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if type(value) is not dict or not same_typed_json_v1(value, expected):
        raise _error("service-activity candidate replay drifted")
    return expected
