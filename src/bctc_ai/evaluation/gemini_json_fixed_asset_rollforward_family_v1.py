"""Generic fixed-asset roll-forward over selected Gemini page JSON.

Gemini is only the source reader.  Deterministic code inventories every
family-bearing table, selects the unique current presentation, normalizes the
row hierarchy, proves each horizontal total, seals a bounded right-edge total
shift only through all affected equations, collapses visible subtotal blocks,
and closes every declared signed branch plus any declared carrying-value
control equation.  The primitive
contains no bank, filename, note, page, value, or prompt route.

The engine is intentionally family-parameterized.  Tangible, leased,
intangible and investment-property families can provide different aliases,
schema IDs and declarative sibling-component policies without changing the
algorithm or the provider prompt boundary.
"""

from __future__ import annotations

import calendar
import json
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.accounting_family_topology_v1 import (
    compile_accounting_family_topology_spec_v1,
)
from bctc_ai.evaluation.accounting_row_width_total_column_seal_v1 import (
    build_accounting_equation_inventory_manifest_v1,
    build_accounting_row_width_total_column_seal_v1,
)
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.evaluation.gemini_json_customer_deposit_family_v1 import _source_table
from bctc_ai.evaluation.ordered_visible_subtotal_block_collapse_v1 import (
    build_ordered_visible_subtotal_block_collapse_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

ENGINE_FORMAT_VERSION = "GEMINI_JSON_FIXED_ASSET_ROLLFORWARD_ACCOUNTING_FAMILY_V1"
INDEXED_QUERY_EVIDENCE_FORMAT_VERSION = (
    "GEMINI_JSON_INDEXED_FIXED_ASSET_ROLLFORWARD_QUERY_EVIDENCE_V1"
)
EVALUATION_FORMAT_VERSION = "ACCOUNTING_FIXED_ASSET_ROLLFORWARD_FAMILY_EVALUATION_SPEC_V1"
SCHEMA_FORMAT_VERSION = "ACCOUNTING_FIXED_ASSET_ROLLFORWARD_SCHEMA_BINDING_SPEC_V1"
SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION = (
    "GEMINI_JSON_FIXED_ASSET_AUTHENTICATED_SOURCE_REPAIR_ARTIFACT_V1"
)
READY = "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
NOT_OBSERVED = "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
UNRESOLVED = "UNRESOLVED_GEMINI_JSON_FAMILY"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_DECLARATIVE_FIXED_ASSET_OWNER_HEADER_"
    "CONFIGURED_BRANCH_CURRENT_PERIOD_EXPLICIT_OR_SINGLE_ASSET_IMPLICIT_TOTAL_"
    "COLUMN_APPLICABLE_ROW_HORIZONTAL_SIGNED_"
    "BRANCH_OPTIONAL_CARRYING_CONTROL_AND_CONFIGURED_SUPPLEMENTAL_DISCLOSURE_"
    "CURRENT_PERIOD_VISIBLE_SUBTOTAL_AND_UNIQUE_ALL_EQUATION_WIDTH_SEAL_SCHEMA_"
    "MAPPING_PROPOSAL_ONLY_GENERIC_CONTENT_ADDRESSED_VISUAL_SOURCE_REPAIR_ARTIFACT_"
    "TRANSCRIPTION_ONLY_NO_EQUATION_BACKSOLVE_PROVIDER_OR_PROMPT_ROUTING_"
    "ROUTING_CANONICAL_SQLITE_QUERY_AND_CANDIDATE_REPLAY_REQUIRED_FOR_PERSISTENCE"
)

_PAGE_VERSION = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_DOCUMENT_ID = re.compile(r"gfpstorev1:document:[0-9a-f]{64}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_EXTRACTION_RUN_ID = re.compile(r"gfpstorev1:run:[0-9a-f]{64}\Z")
_SOURCE_REPAIR_ID = re.compile(r"gjffasrv1:repair:[0-9a-f]{64}\Z")
_SOURCE_REPAIR_OVERLAY_ID = re.compile(r"gjffasrv1:overlay:[0-9a-f]{64}\Z")
_SECTION_ID = re.compile(r"s[1-9][0-9]*\Z")
_TABLE_ID = re.compile(r"t[1-9][0-9]*\Z")
_DATE_DMY = re.compile(
    r"(?<!\d)([0-3]?\d)(?:[./-]|\s+(?:thang\s+)?)"
    r"([01]?\d)(?:[./-]|\s+(?:nam\s+)?)((?:19|20)\d{2})(?!\d)"
)
_DASHES = {"-", "_", "–", "—", "−"}
_DASH_ANNOTATIONS = {"Singledashplaceholderordash", "带有横线"}
_IGNORABLE_TRAILING_MODEL_GLYPHS = {"单"}
_GROUPED_MONEY = re.compile(r"(?<!\d)\(?\d{1,3}(?:[.\s]\d{3})+\)?(?!\d)")
_GROUPED_INTEGER_WITH_ZERO_DECIMALS = re.compile(
    r"(?:\d{1,3}(?:\.\d{3})+,00|\d{1,3}(?:,\d{3})+\.00)\Z"
)
_VISIBLE_ACCOUNTING_MONEY = re.compile(
    r"(?:[-_–—−]|\d+(?:[., ]\d+)*|\(\d+(?:[., ]\d+)*\))\Z"
)
_BRANCH_KINDS = {"SIGNED_ADDITIVE", "COST_AND_DEPRECIATION_CONTROL"}
_CLOSURE_POLICIES = {
    "ALL_SOURCE_ROWS_HORIZONTAL_PLUS_SIGNED_BRANCH_AND_CARRYING_EQUATIONS_EXACT",
    "ALL_SOURCE_ROWS_HORIZONTAL_PLUS_SIGNED_BRANCH_EQUATIONS_EXACT_WITH_OPTIONAL_CARRYING_CONTROL",
}
_ROW_LEVEL_STRICT_SUBSET_POLICY = (
    "UNIQUE_UNREPAIRED_PRINTED_TOTAL_OR_CROPPED_TOTAL_COMPLETE_DISJOINT_"
    "ASSET_FRONTIER_PER_ROLE"
)
_ROW_LEVEL_STRICT_SUBSET_CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_TANGIBLE_FIXED_ASSET_UNIQUE_OWNER_"
    "PERIOD_UNIT_ROLE_ROW_LEVEL_STRICT_SUBSET_UNREPAIRED_PRINTED_TOTAL_OR_"
    "COMPLETE_DISJOINT_ASSET_COLUMN_FORWARD_AGGREGATION_PER_ROW_EQUATION_"
    "RECEIPTS_ENDPOINT_HORIZONTAL_CONFLICT_VETO_EXCLUDED_ROWS_TYPED_NO_BLANK_"
    "ZERO_BACKSOLVE_GEOMETRY_OCR_PROVIDER_BANK_FILE_PAGE_OR_VALUE_ROUTING"
)


class GeminiJsonFixedAssetRollforwardFamilyV1Error(ValueError):
    """The selected JSON, declarative triplet, or exact closure drifted."""


def _error(message: str) -> GeminiJsonFixedAssetRollforwardFamilyV1Error:
    return GeminiJsonFixedAssetRollforwardFamilyV1Error(message)


def _normalized(value: Any) -> str:
    if type(value) is not str:
        return ""
    # Gemini can preserve PDF line breaks either as real whitespace or as the
    # two-character JSON escape spelling (``\\n``).  Treat the latter as the
    # same source-layout whitespace before applying the shared Vietnamese
    # normalization; otherwise a spurious ``n`` becomes part of an asset
    # header (for example ``vật kiến\\ntrúc``).
    surface = value.replace("\\n", " ").replace("\\r", " ").replace("\\t", " ")
    return normalize_vietnamese_anchor_v1(surface)


def _normalized_aliases(value: Any, *, label: str) -> list[str]:
    if (
        type(value) is not list
        or not value
        or any(type(item) is not str or not item.strip() for item in value)
    ):
        raise _error(f"fixed-asset {label} aliases are invalid")
    aliases = [_normalized(item) for item in value]
    if any(not item for item in aliases) or len(aliases) != len(set(aliases)):
        raise _error(f"fixed-asset {label} aliases collide")
    return aliases


def _aliases(child: Mapping[str, Any]) -> list[str]:
    return sorted(
        {_normalized(alias) for matcher in child["matchers"] for alias in matcher["aliases"]}
    )


def _compile_units(value: Any) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if type(value) is not list or not value:
        raise _error("fixed-asset unit bindings are absent")
    bindings = []
    by_alias: dict[str, dict[str, Any]] = {}
    canonical_units: set[str] = set()
    for raw in value:
        if (
            type(raw) is not dict
            or set(raw) != {"accepted", "aliases", "canonical_unit", "magnitude_power10"}
            or type(raw["accepted"]) is not bool
            or type(raw["canonical_unit"]) is not str
            or not raw["canonical_unit"]
            or raw["canonical_unit"] in canonical_units
            or type(raw["magnitude_power10"]) is not int
            or raw["magnitude_power10"] < 0
        ):
            raise _error("fixed-asset unit binding drifted")
        canonical_units.add(raw["canonical_unit"])
        aliases = _normalized_aliases(raw["aliases"], label=raw["canonical_unit"])
        binding = {**canonical_clone_v1(raw), "aliases": aliases}
        bindings.append(binding)
        for alias in aliases:
            if alias in by_alias:
                raise _error("fixed-asset unit aliases collide")
            by_alias[alias] = binding
    if not any(item["accepted"] for item in bindings):
        raise _error("fixed-asset needs one accepted money unit")
    return bindings, by_alias


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
        raise _error(f"fixed-asset authenticated source-repair {label} is invalid")
    return list(value)


def _compile_authenticated_source_repair_artifact_v1(
    value: Any,
    *,
    family_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load and compile one externally pinned visual cell-transcription artifact.

    The family spec contains only a content reference.  Bank/file/page/value
    exceptions live in the immutable registered artifact and are admitted only
    after source, render, selected page JSON, table and individual cell
    identities all replay.  The artifact may transcribe a PDF-visible money
    token or accounting dash; it cannot create a value from an equation.
    """

    ref_fields = {
        "artifact_format_version",
        "overlay_id",
        "path",
        "sha256",
        "size_bytes",
    }
    if (
        type(value) is not dict
        or set(value) != ref_fields
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
        raise _error("fixed-asset authenticated source-repair artifact ref is invalid")
    artifact_path = Path(__file__).resolve().parents[3] / value["path"]
    try:
        payload = artifact_path.read_bytes()
    except OSError as exc:
        raise _error("fixed-asset authenticated source-repair artifact is absent") from exc
    if len(payload) != value["size_bytes"] or sha256(payload).hexdigest() != value["sha256"]:
        raise _error("fixed-asset authenticated source-repair artifact bytes drifted")
    try:
        raw_artifact = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("fixed-asset authenticated source-repair artifact JSON is invalid") from exc

    artifact_fields = {
        "family_id",
        "format_version",
        "overlay_id",
        "repairs",
        "review_policy",
    }
    review_policy = (
        "TRANSCRIBE_ONLY_PDF_VISIBLE_CELL_TOKENS_NO_EQUATION_BACKSOLVE_"
        "NO_BLANK_TO_ZERO_NO_PROVIDER"
    )
    if (
        type(raw_artifact) is not dict
        or set(raw_artifact) != artifact_fields
        or raw_artifact.get("format_version") != SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION
        or raw_artifact.get("family_id") != family_id
        or raw_artifact.get("review_policy") != review_policy
        or type(raw_artifact.get("repairs")) is not list
        or not raw_artifact["repairs"]
    ):
        raise _error("fixed-asset authenticated source-repair artifact is invalid")

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
    checked_repairs = []
    seen_versions: set[str] = set()
    for raw in raw_artifact["repairs"]:
        if type(raw) is not dict or set(raw) != repair_fields:
            raise _error("fixed-asset authenticated source-repair fields drifted")
        repair = canonical_clone_v1(raw)
        source = repair["source_binding"]
        if type(source) is not dict or set(source) != source_fields:
            raise _error("fixed-asset authenticated source-repair source binding drifted")
        if (
            type(source["source_logical_name"]) is not str
            or not source["source_logical_name"].strip()
            or _SHA256.fullmatch(source.get("source_sha256", "")) is None
            or type(source["source_size_bytes"]) is not int
            or source["source_size_bytes"] <= 0
            or _DOCUMENT_ID.fullmatch(source.get("document_id", "")) is None
            or type(source["physical_page"]) is not int
            or source["physical_page"] <= 0
            or _SHA256.fullmatch(source.get("image_sha256", "")) is None
            or type(source["image_size_bytes"]) is not int
            or source["image_size_bytes"] <= 0
            or type(source["pixel_width"]) is not int
            or source["pixel_width"] <= 0
            or type(source["pixel_height"]) is not int
            or source["pixel_height"] <= 0
            or source["render_dpi"] not in {200, 300}
            or source["media_type"] != "image/png"
            or not isinstance(source.get("page_id"), str)
        ):
            raise _error("fixed-asset authenticated source-repair source binding is invalid")
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
            raise _error("fixed-asset authenticated source-repair source identity does not replay")
        if (
            _SHA256.fullmatch(repair.get("base_page_json_sha256", "")) is None
            or _SHA256.fullmatch(repair.get("effective_page_json_sha256", "")) is None
            or _SHA256.fullmatch(repair.get("stored_canonical_json_sha256", "")) is None
            or _EXTRACTION_RUN_ID.fullmatch(repair.get("extraction_run_id", "")) is None
            or _PAGE_VERSION.fullmatch(repair.get("base_page_json_version_id", "")) is None
        ):
            raise _error("fixed-asset authenticated source-repair page version is invalid")
        expected_version_id = "gfpstorev1:json:" + canonical_json_sha256_v1(
            {
                "canonical_json_sha256": repair["stored_canonical_json_sha256"],
                "extraction_run_id": repair["extraction_run_id"],
                "page_id": source["page_id"],
            }
        )
        if repair["base_page_json_version_id"] != expected_version_id:
            raise _error("fixed-asset authenticated source-repair page version does not replay")
        if repair["base_page_json_version_id"] in seen_versions:
            raise _error("fixed-asset authenticated source-repair page version is duplicated")
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
            raise _error("fixed-asset authenticated source-repair table binding is invalid")
        visual = repair["visual_evidence"]
        if (
            type(visual) is not dict
            or set(visual) != visual_fields
            or visual.get("evidence_kind")
            != "AUTHENTICATED_MANUAL_VISUAL_CELL_TRANSCRIPTION"
            or visual.get("render_mode") != "PDF_PAGE_GET_PIXMAP_DPI_EXACT"
            or not re.fullmatch(r"20\d{2}-[01]\d-[0-3]\d", visual.get("reviewed_utc_date", ""))
            or _SHA256.fullmatch(visual.get("table_crop_rgb_sha256", "")) is None
        ):
            raise _error("fixed-asset authenticated source-repair visual evidence is invalid")
        table_bbox = _source_repair_bbox_v1(
            visual["table_crop_bbox_pixels_xyxy"],
            pixel_width=source["pixel_width"],
            pixel_height=source["pixel_height"],
            label="table crop",
        )
        cells = repair["cell_repairs"]
        if type(cells) is not list or not cells:
            raise _error("fixed-asset authenticated source-repair cell axis is empty")
        checked_cells = []
        seen_cells = set()
        for raw_cell in cells:
            if type(raw_cell) is not dict or set(raw_cell) != cell_fields:
                raise _error("fixed-asset authenticated source-repair cell fields drifted")
            cell = canonical_clone_v1(raw_cell)
            match = re.fullmatch(r"r([1-9][0-9]*):c([1-9][0-9]*)", cell.get("cell_id", ""))
            after = cell.get("after_exact")
            expected_visual_state = "DASH" if after in _DASHES else "PRINTED_MONEY"
            if (
                match is None
                or cell["cell_id"] in seen_cells
                or type(cell.get("before_exact")) not in {str, type(None)}
                or type(after) is not str
                or _VISIBLE_ACCOUNTING_MONEY.fullmatch(after.strip()) is None
                or cell["visual_state"] != expected_visual_state
                or same_typed_json_v1(cell["before_exact"], after)
                or type(cell.get("row_label_exact")) is not str
                or not cell["row_label_exact"].strip()
                or type(cell.get("row_hierarchy_path_exact")) is not list
                or not cell["row_hierarchy_path_exact"]
                or any(type(item) is not str or not item for item in cell["row_hierarchy_path_exact"])
                or type(cell.get("column_header_path_exact")) is not list
                or not cell["column_header_path_exact"]
                or any(type(item) is not str or not item for item in cell["column_header_path_exact"])
                or _SHA256.fullmatch(cell.get("crop_rgb_sha256", "")) is None
            ):
                raise _error("fixed-asset authenticated source-repair cell is invalid")
            seen_cells.add(cell["cell_id"])
            cell_bbox = _source_repair_bbox_v1(
                cell["crop_bbox_pixels_xyxy"],
                pixel_width=source["pixel_width"],
                pixel_height=source["pixel_height"],
                label="cell crop",
            )
            if not (
                table_bbox[0] <= cell_bbox[0] < cell_bbox[2] <= table_bbox[2]
                and table_bbox[1] <= cell_bbox[1] < cell_bbox[3] <= table_bbox[3]
            ):
                raise _error("fixed-asset authenticated source-repair cell leaves table crop")
            checked_cells.append(cell)
        checked_cells.sort(
            key=lambda item: tuple(int(part[1:]) for part in item["cell_id"].split(":"))
        )
        if cells != checked_cells:
            raise _error("fixed-asset authenticated source-repair cell axis is unordered")
        if repair["repair_reason"] != "VISIBLE_PDF_CELL_MISALIGNED_IN_SELECTED_JSON":
            raise _error("fixed-asset authenticated source-repair reason is invalid")
        expected_repair_id = "gjffasrv1:repair:" + canonical_json_sha256_v1(
            {key: repair[key] for key in repair if key != "repair_id"}
        )
        if (
            _SOURCE_REPAIR_ID.fullmatch(repair.get("repair_id", "")) is None
            or repair["repair_id"] != expected_repair_id
        ):
            raise _error("fixed-asset authenticated source-repair identity does not replay")
        checked_repairs.append(repair)
    checked_repairs.sort(
        key=lambda item: (
            item["source_binding"]["source_logical_name"],
            item["source_binding"]["physical_page"],
            int(item["table_ref"]["section_id"][1:]),
            int(item["table_ref"]["table_id"][1:]),
        )
    )
    if raw_artifact["repairs"] != checked_repairs:
        raise _error("fixed-asset authenticated source-repair axis is unordered")
    material = {
        "family_id": family_id,
        "format_version": SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION,
        "repairs": checked_repairs,
        "review_policy": review_policy,
    }
    expected_overlay_id = "gjffasrv1:overlay:" + canonical_json_sha256_v1(material)
    if (
        raw_artifact.get("overlay_id") != expected_overlay_id
        or value["overlay_id"] != expected_overlay_id
    ):
        raise _error("fixed-asset authenticated source-repair overlay identity does not replay")
    return {**material, "overlay_id": expected_overlay_id}, canonical_clone_v1(value)


def compile_gemini_json_fixed_asset_rollforward_family_specs_v1(
    topology_spec: Any, evaluation_spec: Any, schema_binding_spec: Any
) -> dict[str, Any]:
    """Compile one data-only fixed-asset family triplet."""

    try:
        topology = compile_accounting_family_topology_spec_v1(topology_spec)
    except ValueError as exc:
        raise _error("fixed-asset topology spec is invalid") from exc
    evaluation_fields = {
        "asset_header_aliases",
        "branch_layouts",
        "closure_policy",
        "family_id",
        "format_version",
        "header_hard_negative_aliases",
        "layout_policy",
        "minimum_distinct_asset_header_aliases",
        "money_unit_bindings",
        "period_policy",
        "row_width_policy",
        "subtotal_policy",
        "total_column_aliases",
    }
    optional_evaluation_fields = {
        "adjacent_page_endpoint_first_continuation_policy",
        "adjacent_owner_continuation_policy",
        "authenticated_source_repair_artifact_ref",
        "blank_subtotal_heading_policy",
        "component_policy",
        "direct_role_fallbacks",
        "endpoint_first_layout",
        "equation_only_roles",
        "leading_implicit_cost_branch_policy",
        "immediately_preceding_table_period_policy",
        "missing_local_unit_policy",
        "movement_role_directions",
        "ordered_dated_endpoint_policy",
        "ordered_branch_scope_policy",
        "partial_detail_total_policy",
        "row_level_strict_subset_policy",
        "source_only_carrying_control",
        "source_only_row_aliases",
        "source_presentation_rounding_policy",
        "single_asset_period_column_policy",
        "singleton_declared_subtotal_projections",
        "supplemental_disclosure_roles",
        "trailing_owner_heading_policy",
        "undated_full_table_sequence_policy",
        "undated_sibling_policy",
    }
    if (
        type(evaluation_spec) is not dict
        or not evaluation_fields <= set(evaluation_spec)
        or set(evaluation_spec) - evaluation_fields - optional_evaluation_fields
        or evaluation_spec.get("format_version") != EVALUATION_FORMAT_VERSION
        or evaluation_spec.get("family_id") != topology["family_id"]
        or evaluation_spec.get("closure_policy") not in _CLOSURE_POLICIES
        or evaluation_spec.get("layout_policy")
        != "ONE_CURRENT_TOTAL_COLUMN_TABLE_WITH_OPTIONAL_TYPED_COMPARATIVE_CONTROL_TABLES"
        or evaluation_spec.get("period_policy")
        != "UNIQUE_SOURCE_VISIBLE_OR_TYPED_DOCUMENT_REPORTING_DATE_WITH_COMPARATIVE_ENDPOINT_CONTINUITY"
        or evaluation_spec.get("row_width_policy")
        != "UNIQUE_RIGHT_EDGE_TOTAL_WITH_ALL_EQUATION_SEALED_RELOCATION_ONLY"
        or evaluation_spec.get("subtotal_policy")
        != "VISIBLE_SUBTOTAL_AND_DIRECT_CHILDREN_COEXIST_BUT_VERTICAL_CONSUMES_EXACTLY_ONE_FRONTIER"
        or type(evaluation_spec.get("minimum_distinct_asset_header_aliases")) is not int
        or evaluation_spec["minimum_distinct_asset_header_aliases"] < 1
    ):
        raise _error("fixed-asset evaluation spec is invalid")
    adjacent_owner_continuation_policy = evaluation_spec.get(
        "adjacent_owner_continuation_policy"
    )
    if adjacent_owner_continuation_policy not in {
        None,
        "IMMEDIATELY_PRECEDING_EXPLICIT_OWNER_SAME_HEADER_AXIS_WITH_CONTINUATION_HEADING",
    }:
        raise _error("fixed-asset adjacent owner-continuation policy drifted")
    blank_subtotal_heading_policy = evaluation_spec.get("blank_subtotal_heading_policy")
    if blank_subtotal_heading_policy not in {
        None,
        "VISIBLE_BLANK_SUBTOTAL_HEADING_CHILDREN_PROMOTE_TO_DIRECT_MOVEMENTS",
    }:
        raise _error("fixed-asset blank subtotal-heading policy drifted")
    adjacent_page_endpoint_first_continuation_policy = evaluation_spec.get(
        "adjacent_page_endpoint_first_continuation_policy"
    )
    if adjacent_page_endpoint_first_continuation_policy not in {
        None,
        "PAGE_FINAL_OWNER_PARTIAL_PLUS_NEXT_PAGE_LEADING_HEADERLESS_COMPLEMENT_EXACT_ENDPOINT_TOPOLOGY",
    }:
        raise _error("fixed-asset adjacent page endpoint-first policy drifted")
    leading_implicit_cost_branch_policy = evaluation_spec.get(
        "leading_implicit_cost_branch_policy"
    )
    if leading_implicit_cost_branch_policy not in {
        None,
        "LEADING_UNSCOPED_ROWS_BEFORE_FIRST_EXPLICIT_DEPRECIATION_BRANCH_ARE_COST",
    }:
        raise _error("fixed-asset leading implicit cost-branch policy drifted")
    source_presentation_rounding_policy = evaluation_spec.get(
        "source_presentation_rounding_policy"
    )
    if source_presentation_rounding_policy not in {
        None,
        "INDEPENDENT_DISPLAY_UNIT_ROUNDING_INTERVAL_ALL_EQUATIONS",
    }:
        raise _error("fixed-asset source presentation-rounding policy drifted")
    single_asset_period_column_policy = evaluation_spec.get(
        "single_asset_period_column_policy"
    )
    if single_asset_period_column_policy not in {
        None,
        "SAME_RECOGNIZED_ASSET_DISTINCT_PERIOD_COLUMNS_SELECT_UNIQUE_CURRENT_PERIOD",
    }:
        raise _error("fixed-asset single-asset period-column policy drifted")
    immediately_preceding_table_period_policy = evaluation_spec.get(
        "immediately_preceding_table_period_policy"
    )
    if immediately_preceding_table_period_policy not in {
        None,
        "IMMEDIATELY_PRECEDING_SIBLING_TABLE_UNIQUE_EXPLICIT_AS_AT_DATE",
    }:
        raise _error("fixed-asset immediately preceding-table period policy drifted")
    source_repair_overlay = None
    source_repair_artifact_ref = None
    if "authenticated_source_repair_artifact_ref" in evaluation_spec:
        source_repair_overlay, source_repair_artifact_ref = (
            _compile_authenticated_source_repair_artifact_v1(
                evaluation_spec["authenticated_source_repair_artifact_ref"],
                family_id=topology["family_id"],
            )
        )
    trailing_owner_heading_policy = evaluation_spec.get("trailing_owner_heading_policy")
    if trailing_owner_heading_policy not in {
        None,
        "IMMEDIATELY_PRECEDING_PAGE_FINAL_EMPTY_OWNER_SECTION_BINDS_FIRST_HEADER_COMPLETE_TABLE",
    }:
        raise _error("fixed-asset trailing owner-heading policy drifted")
    asset_aliases = _normalized_aliases(
        evaluation_spec["asset_header_aliases"], label="asset header"
    )
    hard_negative_aliases = _normalized_aliases(
        evaluation_spec["header_hard_negative_aliases"], label="header hard-negative"
    )
    total_aliases = _normalized_aliases(
        evaluation_spec["total_column_aliases"], label="total column"
    )
    units, unit_by_alias = _compile_units(evaluation_spec["money_unit_bindings"])
    child_by_role = {child["role"]: child for child in topology["children"]}
    raw_equation_only_roles = evaluation_spec.get("equation_only_roles", [])
    if (
        type(raw_equation_only_roles) is not list
        or any(
            type(role) is not str or role not in child_by_role for role in raw_equation_only_roles
        )
        or len(raw_equation_only_roles) != len(set(raw_equation_only_roles))
    ):
        raise _error("fixed-asset equation-only role axis is invalid")
    equation_only_roles = set(raw_equation_only_roles)
    direct_role_fallback_by_role = {}
    raw_direct_role_fallbacks = evaluation_spec.get("direct_role_fallbacks", [])
    if type(raw_direct_role_fallbacks) is not list:
        raise _error("fixed-asset direct-role fallback axis is invalid")
    for raw in raw_direct_role_fallbacks:
        if (
            type(raw) is not dict
            or set(raw) != {"fallback_role", "source_role"}
            or raw["source_role"] not in child_by_role
            or raw["fallback_role"] not in child_by_role
            or raw["source_role"] in direct_role_fallback_by_role
            or raw["source_role"] == raw["fallback_role"]
        ):
            raise _error("fixed-asset direct-role fallback drifted")
        direct_role_fallback_by_role[raw["source_role"]] = raw["fallback_role"]
    singleton_declared_subtotal_by_source_role = {}
    raw_singleton_subtotal_projections = evaluation_spec.get(
        "singleton_declared_subtotal_projections", []
    )
    if type(raw_singleton_subtotal_projections) is not list:
        raise _error("fixed-asset singleton declared-subtotal projection axis is invalid")
    for raw in raw_singleton_subtotal_projections:
        if (
            type(raw) is not dict
            or set(raw) != {"source_role", "subtotal_role"}
            or raw["source_role"] not in child_by_role
            or raw["subtotal_role"] not in child_by_role
            or raw["source_role"] in singleton_declared_subtotal_by_source_role
            or raw["source_role"] == raw["subtotal_role"]
        ):
            raise _error("fixed-asset singleton declared-subtotal projection drifted")
        singleton_declared_subtotal_by_source_role[raw["source_role"]] = raw[
            "subtotal_role"
        ]
    movement_role_directions = {}
    raw_movement_role_directions = evaluation_spec.get("movement_role_directions", [])
    if type(raw_movement_role_directions) is not list:
        raise _error("fixed-asset movement-role direction axis is invalid")
    for raw in raw_movement_role_directions:
        if (
            type(raw) is not dict
            or set(raw) != {"direction", "role"}
            or raw["role"] not in child_by_role
            or raw["role"] in movement_role_directions
            or raw["direction"] not in {"INCREASE", "DECREASE", "PRESERVE_SIGN"}
        ):
            raise _error("fixed-asset movement-role direction drifted")
        movement_role_directions[raw["role"]] = raw["direction"]
    supplemental_disclosure_roles = []
    supplemental_role_names = set()
    raw_supplemental_roles = evaluation_spec.get("supplemental_disclosure_roles", [])
    if type(raw_supplemental_roles) is not list:
        raise _error("fixed-asset supplemental disclosure role axis is invalid")
    for raw in raw_supplemental_roles:
        raw_fields = (
            {"aliases", "required_token_groups", "role", "value_header_aliases"}
            | ({"contextual_aliases"} if type(raw) is dict and "contextual_aliases" in raw else set())
        )
        if (
            type(raw) is not dict
            or set(raw) != raw_fields
            or raw.get("role") not in child_by_role
            or raw["role"] in supplemental_role_names
            or type(raw["required_token_groups"]) is not list
            or not raw["required_token_groups"]
        ):
            raise _error("fixed-asset supplemental disclosure role drifted")
        supplemental_role_names.add(raw["role"])
        supplemental_disclosure_roles.append(
            {
                "aliases": _normalized_aliases(
                    raw["aliases"], label=raw["role"] + " supplemental disclosure"
                ),
                "contextual_aliases": (
                    _normalized_aliases(
                        raw["contextual_aliases"],
                        label=raw["role"] + " contextual supplemental disclosure",
                    )
                    if "contextual_aliases" in raw
                    else []
                ),
                "required_token_groups": [
                    _normalized_aliases(
                        group,
                        label=raw["role"] + f" supplemental token group {ordinal}",
                    )
                    for ordinal, group in enumerate(raw["required_token_groups"], start=1)
                ],
                "role": raw["role"],
                "value_header_aliases": _normalized_aliases(
                    raw["value_header_aliases"],
                    label=raw["role"] + " supplemental value header",
                ),
            }
        )
    source_only_row_aliases = (
        _normalized_aliases(
            evaluation_spec["source_only_row_aliases"], label="source-only row"
        )
        if "source_only_row_aliases" in evaluation_spec
        else []
    )
    source_only_carrying_control = None
    raw_source_only_carrying_control = evaluation_spec.get("source_only_carrying_control")
    if raw_source_only_carrying_control is not None:
        if (
            type(raw_source_only_carrying_control) is not dict
            or set(raw_source_only_carrying_control)
            != {"control_kind", "hierarchy_aliases"}
            or raw_source_only_carrying_control.get("control_kind")
            != "COST_MINUS_DEPRECIATION_ENDPOINTS_EXACT_NO_SCHEMA_MAPPING"
        ):
            raise _error("fixed-asset source-only carrying control drifted")
        source_only_carrying_control = {
            **canonical_clone_v1(raw_source_only_carrying_control),
            "hierarchy_aliases": _normalized_aliases(
                raw_source_only_carrying_control["hierarchy_aliases"],
                label="source-only carrying control",
            ),
        }
    partial_detail_total_policy = evaluation_spec.get("partial_detail_total_policy")
    if partial_detail_total_policy not in {
        None,
        "SOURCE_VISIBLE_TOTAL_CONTROLS_VERTICAL_PRESERVE_BLANK_DETAILS_NO_MAPPING_INFERENCE",
    }:
        raise _error("fixed-asset partial-detail total policy drifted")
    row_level_strict_subset_policy = evaluation_spec.get(
        "row_level_strict_subset_policy"
    )
    if row_level_strict_subset_policy not in {
        None,
        _ROW_LEVEL_STRICT_SUBSET_POLICY,
    }:
        raise _error("fixed-asset row-level strict-subset policy drifted")
    if (
        row_level_strict_subset_policy is not None
        and topology["family_id"] != "TANGIBLE_FIXED_ASSETS_ROLLFORWARD"
    ):
        raise _error("fixed-asset row-level strict-subset policy is not family-local")
    ordered_dated_endpoint_policy = evaluation_spec.get("ordered_dated_endpoint_policy")
    if ordered_dated_endpoint_policy not in {
        None,
        "EARLIEST_AND_LATEST_DISTINCT_DATED_BALANCES_BIND_OPENING_ENDING",
    }:
        raise _error("fixed-asset ordered dated-endpoint policy drifted")
    ordered_branch_scope_policy = evaluation_spec.get("ordered_branch_scope_policy")
    if ordered_branch_scope_policy not in {
        None,
        "PRECEDING_EXPLICIT_BRANCH_UNTIL_NEXT_GROUP_FOR_UNIQUE_ROLE_ROW",
    }:
        raise _error("fixed-asset ordered branch-scope policy drifted")
    missing_local_unit_policy = evaluation_spec.get("missing_local_unit_policy")
    if missing_local_unit_policy not in {
        None,
        "UNIQUE_TYPED_BALANCE_SHEET_OWNER_ENDPOINT_VECTOR_BASE_VALUE",
    }:
        raise _error("fixed-asset missing local-unit policy drifted")
    undated_sibling_policy = evaluation_spec.get("undated_sibling_policy")
    if undated_sibling_policy not in {
        None,
        "UNIQUE_EXACT_DOCUMENT_CURRENT_DATE_DOMINATES_UNDATED_COMPLETE_SIBLINGS_AS_SOURCE_ONLY",
    }:
        raise _error("fixed-asset undated sibling policy drifted")
    undated_full_table_sequence_policy = evaluation_spec.get(
        "undated_full_table_sequence_policy"
    )
    if undated_full_table_sequence_policy not in {
        None,
        "LEADING_EXPLICIT_OWNER_THEN_ADJACENT_CONTINUATION_TABLES_BIND_CURRENT_AS_SOURCE_ONLY_HISTORY",
    }:
        raise _error("fixed-asset undated full-table sequence policy drifted")
    endpoint_first_layout = None
    raw_endpoint_first_layout = evaluation_spec.get("endpoint_first_layout")
    if raw_endpoint_first_layout is not None:
        if (
            type(raw_endpoint_first_layout) is not dict
            or set(raw_endpoint_first_layout)
            != {"cost_child_aliases", "depreciation_child_aliases", "layout_kind"}
            or raw_endpoint_first_layout.get("layout_kind")
            != "CARRYING_ENDPOINT_PARENT_WITH_COST_AND_DEPRECIATION_CHILDREN"
            or sum(
                raw.get("rollforward_kind") == "COST_AND_DEPRECIATION_CONTROL"
                for raw in evaluation_spec["branch_layouts"]
                if type(raw) is dict
            )
            != 1
        ):
            raise _error("fixed-asset endpoint-first layout drifted")
        endpoint_first_layout = {
            **canonical_clone_v1(raw_endpoint_first_layout),
            "cost_child_aliases": _normalized_aliases(
                raw_endpoint_first_layout["cost_child_aliases"],
                label="endpoint-first cost child",
            ),
            "depreciation_child_aliases": _normalized_aliases(
                raw_endpoint_first_layout["depreciation_child_aliases"],
                label="endpoint-first depreciation child",
            ),
        }
    branch_layouts = []
    branch_roles: set[str] = set()
    endpoint_roles: set[str] = set()
    subtotal_roles: set[str] = set()
    for raw in evaluation_spec["branch_layouts"]:
        if (
            type(raw) is not dict
            or set(raw)
            != {
                "branch_role",
                "ending_role",
                "hierarchy_aliases",
                "opening_role",
                "rollforward_kind",
                "subtotal_roles",
            }
            or raw["branch_role"] not in child_by_role
            or raw["branch_role"] in branch_roles
            or raw["opening_role"] not in child_by_role
            or raw["ending_role"] not in child_by_role
            or raw["opening_role"] in endpoint_roles
            or raw["ending_role"] in endpoint_roles
            or raw["rollforward_kind"] not in _BRANCH_KINDS
            or type(raw["subtotal_roles"]) is not list
            or any(role not in child_by_role for role in raw["subtotal_roles"])
        ):
            raise _error("fixed-asset branch layout drifted")
        branch_roles.add(raw["branch_role"])
        endpoint_roles.update((raw["opening_role"], raw["ending_role"]))
        subtotal_roles.update(raw["subtotal_roles"])
        branch_layouts.append(
            {
                **canonical_clone_v1(raw),
                "hierarchy_aliases": _normalized_aliases(
                    raw["hierarchy_aliases"], label=raw["branch_role"]
                ),
            }
        )
    if (
        len(branch_layouts) not in {2, 3}
        or sum(item["rollforward_kind"] == "SIGNED_ADDITIVE" for item in branch_layouts) != 2
        or sum(
            item["rollforward_kind"] == "COST_AND_DEPRECIATION_CONTROL" for item in branch_layouts
        )
        not in {0, 1}
    ):
        raise _error("fixed-asset needs two signed branches and at most one carrying control")
    if equation_only_roles - subtotal_roles:
        raise _error("fixed-asset equation-only roles must be declared branch subtotals")
    carrying_count = sum(
        item["rollforward_kind"] == "COST_AND_DEPRECIATION_CONTROL" for item in branch_layouts
    )
    signed_branch_layouts = [
        item for item in branch_layouts if item["rollforward_kind"] == "SIGNED_ADDITIVE"
    ]
    if (
        sum(layout["opening_role"].startswith("COST_") for layout in signed_branch_layouts) != 1
        or sum(layout["opening_role"].startswith("DEP_") for layout in signed_branch_layouts) != 1
    ):
        raise _error("fixed-asset signed branches need one cost and one depreciation role")
    if (
        evaluation_spec["closure_policy"]
        == "ALL_SOURCE_ROWS_HORIZONTAL_PLUS_SIGNED_BRANCH_AND_CARRYING_EQUATIONS_EXACT"
        and carrying_count != 1
    ):
        raise _error("fixed-asset carrying closure policy needs one carrying control")
    schema_fields = {
        "context_only_roles",
        "family_id",
        "family_root_report_norm_id",
        "format_version",
        "role_bindings",
        "schema_period_role",
        "structural_root_mapping_policy",
    }
    if (
        type(schema_binding_spec) is not dict
        or set(schema_binding_spec) != schema_fields
        or schema_binding_spec.get("format_version") != SCHEMA_FORMAT_VERSION
        or schema_binding_spec.get("family_id") != topology["family_id"]
        or type(schema_binding_spec.get("family_root_report_norm_id")) is not int
        or schema_binding_spec["family_root_report_norm_id"] <= 0
        or schema_binding_spec.get("schema_period_role") != "CURRENT_PERIOD"
        or schema_binding_spec.get("structural_root_mapping_policy")
        != "CONTEXT_ONLY_NO_NUMERIC_MAPPING"
        or type(schema_binding_spec.get("context_only_roles")) is not dict
        or type(schema_binding_spec.get("role_bindings")) is not list
    ):
        raise _error("fixed-asset schema binding spec is invalid")
    context_roles = schema_binding_spec["context_only_roles"]
    if (
        set(context_roles) != {topology["parent"]["role"], *branch_roles}
        or context_roles[topology["parent"]["role"]]
        != schema_binding_spec["family_root_report_norm_id"]
        or any(type(value) is not int or value <= 0 for value in context_roles.values())
    ):
        raise _error("fixed-asset context-only role bindings drifted")
    bindings: dict[str, int] = {}
    output_role_order = []
    seen_ids = set(context_roles.values())
    for raw in schema_binding_spec["role_bindings"]:
        if (
            type(raw) is not dict
            or set(raw) != {"report_norm_id", "role"}
            or raw["role"] not in child_by_role
            or raw["role"] in branch_roles
            or raw["role"] in bindings
            or type(raw["report_norm_id"]) is not int
            or raw["report_norm_id"] <= 0
            or raw["report_norm_id"] in seen_ids
        ):
            raise _error("fixed-asset output role binding drifted")
        bindings[raw["role"]] = raw["report_norm_id"]
        output_role_order.append(raw["role"])
        seen_ids.add(raw["report_norm_id"])
    if (
        endpoint_roles - set(bindings)
        or subtotal_roles - set(bindings) - equation_only_roles
        or supplemental_role_names - set(bindings)
    ):
        raise _error("fixed-asset endpoint/subtotal schema frontier is incomplete")
    if set(movement_role_directions) & endpoint_roles:
        raise _error("fixed-asset endpoint roles cannot carry movement directions")
    role_aliases = {role: _aliases(child) for role, child in child_by_role.items()}
    role_matchers = {
        role: [
            {
                "aliases": [_normalized(alias) for alias in matcher["aliases"]],
                "within_role": matcher["within_role"],
            }
            for matcher in child["matchers"]
        ]
        for role, child in child_by_role.items()
    }
    output_roles_by_branch = {}
    for layout in branch_layouts:
        prefix = (
            "CARRY_"
            if layout["rollforward_kind"] == "COST_AND_DEPRECIATION_CONTROL"
            else ("COST_" if layout["branch_role"].startswith("COST") else "DEP_")
        )
        roles = [role for role in output_role_order if role.startswith(prefix)]
        if set((layout["opening_role"], layout["ending_role"])) - set(roles):
            raise _error("fixed-asset branch output role frontier drifted")
        output_roles_by_branch[layout["branch_role"]] = roles
    recognized_roles_by_branch = canonical_clone_v1(output_roles_by_branch)
    for role in sorted(equation_only_roles):
        within_roles = {
            matcher["within_role"]
            for matcher in role_matchers[role]
            if matcher["within_role"] in branch_roles
        }
        if len(within_roles) != 1 or role in bindings:
            raise _error("fixed-asset equation-only role branch is ambiguous")
        recognized_roles_by_branch[next(iter(within_roles))].append(role)
    role_branch = {
        role: branch_role for branch_role, roles in output_roles_by_branch.items() for role in roles
    }
    if any(
        source_role not in role_branch
        or fallback_role not in role_branch
        or role_branch[source_role] != role_branch[fallback_role]
        for source_role, fallback_role in direct_role_fallback_by_role.items()
    ):
        raise _error("fixed-asset direct-role fallback crosses a branch boundary")
    if any(
        source_role not in role_branch
        or subtotal_role not in role_branch
        or role_branch[source_role] != role_branch[subtotal_role]
        or subtotal_role not in subtotal_roles
        or source_role in subtotal_roles | endpoint_roles
        for source_role, subtotal_role in (
            singleton_declared_subtotal_by_source_role.items()
        )
    ):
        raise _error("fixed-asset singleton declared-subtotal projection is not structural")
    component_policy = None
    raw_component_policy = evaluation_spec.get("component_policy")
    if raw_component_policy is not None:
        component_fields = {
            "combined_endpoint_policy",
            "default_branch_fragment_roles",
            "fragment_mode",
            "optional_absent_branch_roles",
            "summary_control",
        }
        summary_fields = {
            "current_role",
            "opening_role",
            "row_aliases",
            "selection_policy",
        }
        summary = (
            raw_component_policy.get("summary_control")
            if type(raw_component_policy) is dict
            else None
        )
        default_branches = (
            raw_component_policy.get("default_branch_fragment_roles")
            if type(raw_component_policy) is dict
            else None
        )
        optional_branches = (
            raw_component_policy.get("optional_absent_branch_roles")
            if type(raw_component_policy) is dict
            else None
        )
        if (
            type(raw_component_policy) is not dict
            or set(raw_component_policy) != component_fields
            or raw_component_policy.get("combined_endpoint_policy")
            != "ONE_SOURCE_ROW_WITH_DISTINCT_OPENING_AND_ENDING_SEMANTICS_MAY_BIND_BOTH"
            or raw_component_policy.get("fragment_mode")
            != "SAME_PERIOD_SIBLING_TABLES_EXACT_AGGREGATION"
            or type(default_branches) is not list
            or not default_branches
            or len(default_branches) != len(set(default_branches))
            or any(role not in branch_roles for role in default_branches)
            or type(optional_branches) is not list
            or len(optional_branches) != len(set(optional_branches))
            or any(role not in branch_roles for role in optional_branches)
            or type(summary) is not dict
            or set(summary) != summary_fields
            or summary.get("selection_policy") != "UNIQUE_TOTAL_ROW_TWO_EXPLICIT_PERIOD_COLUMNS"
            or summary.get("opening_role") not in bindings
            or summary.get("current_role") not in bindings
        ):
            raise _error("fixed-asset component policy is invalid")
        summary_roles = {summary["opening_role"], summary["current_role"]}
        summary_layouts = [
            layout
            for layout in branch_layouts
            if {layout["opening_role"], layout["ending_role"]} == summary_roles
        ]
        if len(summary_layouts) != 1 or summary_layouts[0]["branch_role"] in optional_branches:
            raise _error("fixed-asset component summary does not bind one required branch")
        component_policy = {
            **canonical_clone_v1(raw_component_policy),
            "summary_control": {
                **canonical_clone_v1(summary),
                "row_aliases": _normalized_aliases(
                    summary["row_aliases"], label="component summary row"
                ),
            },
        }
    evaluation = {
        **canonical_clone_v1(evaluation_spec),
        "adjacent_page_endpoint_first_continuation_policy": (
            adjacent_page_endpoint_first_continuation_policy
        ),
        "adjacent_owner_continuation_policy": adjacent_owner_continuation_policy,
        "asset_header_aliases": asset_aliases,
        "branch_layouts": branch_layouts,
        "blank_subtotal_heading_policy": blank_subtotal_heading_policy,
        "component_policy": component_policy,
        "direct_role_fallback_by_role": direct_role_fallback_by_role,
        "equation_only_roles": sorted(equation_only_roles),
        "endpoint_first_layout": endpoint_first_layout,
        "header_hard_negative_aliases": hard_negative_aliases,
        "immediately_preceding_table_period_policy": (
            immediately_preceding_table_period_policy
        ),
        "leading_implicit_cost_branch_policy": leading_implicit_cost_branch_policy,
        "money_unit_bindings": units,
        "missing_local_unit_policy": missing_local_unit_policy,
        "movement_role_directions": movement_role_directions,
        "ordered_branch_scope_policy": ordered_branch_scope_policy,
        "ordered_dated_endpoint_policy": ordered_dated_endpoint_policy,
        "partial_detail_total_policy": partial_detail_total_policy,
        "row_level_strict_subset_policy": row_level_strict_subset_policy,
        "source_only_carrying_control": source_only_carrying_control,
        "source_only_row_aliases": source_only_row_aliases,
        "source_presentation_rounding_policy": source_presentation_rounding_policy,
        "single_asset_period_column_policy": single_asset_period_column_policy,
        "singleton_declared_subtotal_by_source_role": (
            singleton_declared_subtotal_by_source_role
        ),
        "supplemental_disclosure_roles": supplemental_disclosure_roles,
        "total_column_aliases": total_aliases,
        "trailing_owner_heading_policy": trailing_owner_heading_policy,
        "undated_full_table_sequence_policy": undated_full_table_sequence_policy,
        "undated_sibling_policy": undated_sibling_policy,
    }
    schema = canonical_clone_v1(schema_binding_spec)
    query_policy = {
        "asset_header_aliases": asset_aliases,
        "branch_layouts": branch_layouts,
        "header_hard_negative_aliases": hard_negative_aliases,
        "minimum_distinct_asset_header_aliases": evaluation[
            "minimum_distinct_asset_header_aliases"
        ],
        "owner_aliases": canonical_clone_v1(topology["parent"]["aliases"]),
        "structural_reset_aliases": canonical_clone_v1(topology["structural_reset_aliases"]),
        "total_column_aliases": total_aliases,
    }
    if component_policy is not None:
        query_policy["component_policy"] = canonical_clone_v1(component_policy)
    if supplemental_disclosure_roles:
        query_policy["supplemental_disclosure_roles"] = canonical_clone_v1(
            supplemental_disclosure_roles
        )
    if source_only_carrying_control is not None:
        query_policy["source_only_carrying_control"] = canonical_clone_v1(
            source_only_carrying_control
        )
    if source_only_row_aliases:
        query_policy["source_only_row_aliases"] = canonical_clone_v1(source_only_row_aliases)
    if ordered_dated_endpoint_policy is not None:
        query_policy["ordered_dated_endpoint_policy"] = ordered_dated_endpoint_policy
    if ordered_branch_scope_policy is not None:
        query_policy["ordered_branch_scope_policy"] = ordered_branch_scope_policy
    if adjacent_owner_continuation_policy is not None:
        query_policy["adjacent_owner_continuation_policy"] = (
            adjacent_owner_continuation_policy
        )
    if adjacent_page_endpoint_first_continuation_policy is not None:
        query_policy["adjacent_page_endpoint_first_continuation_policy"] = (
            adjacent_page_endpoint_first_continuation_policy
        )
    if leading_implicit_cost_branch_policy is not None:
        query_policy["leading_implicit_cost_branch_policy"] = (
            leading_implicit_cost_branch_policy
        )
    if immediately_preceding_table_period_policy is not None:
        query_policy["immediately_preceding_table_period_policy"] = (
            immediately_preceding_table_period_policy
        )
    if row_level_strict_subset_policy is not None:
        query_policy["row_level_strict_subset_policy"] = (
            row_level_strict_subset_policy
        )
    if source_repair_artifact_ref is not None:
        query_policy["authenticated_source_repair_artifact_ref"] = canonical_clone_v1(
            source_repair_artifact_ref
        )
    if undated_sibling_policy is not None:
        query_policy["undated_sibling_policy"] = undated_sibling_policy
    if trailing_owner_heading_policy is not None:
        query_policy["trailing_owner_heading_policy"] = trailing_owner_heading_policy
    if undated_full_table_sequence_policy is not None:
        query_policy["undated_full_table_sequence_policy"] = (
            undated_full_table_sequence_policy
        )
    return {
        "bindings": bindings,
        "claim_boundary": CLAIM_BOUNDARY,
        "engine_format_version": ENGINE_FORMAT_VERSION,
        "evaluation": evaluation,
        "output_role_order": output_role_order,
        "output_roles_by_branch": output_roles_by_branch,
        "recognized_roles_by_branch": recognized_roles_by_branch,
        "query_policy": query_policy,
        "role_aliases": role_aliases,
        "role_matchers": role_matchers,
        "schema": schema,
        "source_repair_artifact_ref": source_repair_artifact_ref,
        "source_repair_overlay": source_repair_overlay,
        "topology": topology,
        "unit_binding_by_alias": unit_by_alias,
    }


def _authenticated_source_repair_receipt_v1(
    *,
    compiled_specs: Mapping[str, Any],
    repair: Mapping[str, Any],
) -> dict[str, Any]:
    material = {
        "artifact_ref": canonical_clone_v1(compiled_specs["source_repair_artifact_ref"]),
        "base_page_json_sha256": repair["base_page_json_sha256"],
        "base_page_json_version_id": repair["base_page_json_version_id"],
        "cell_axis_sha256": canonical_json_sha256_v1(repair["cell_repairs"]),
        "effective_page_json_sha256": repair["effective_page_json_sha256"],
        "overlay_id": compiled_specs["source_repair_overlay"]["overlay_id"],
        "repair_id": repair["repair_id"],
        "rule": (
            "EXACT_CONTENT_ADDRESSED_SOURCE_PAGE_IMAGE_SELECTED_JSON_TABLE_CELL_"
            "VISIBLE_TRANSCRIPTION_ONLY_NO_EQUATION_BACKSOLVE"
        ),
        "status": "AUTHENTICATED_PDF_VISIBLE_CELLS_TRANSCRIBED",
    }
    return {
        **material,
        "receipt_id": "gjffasrv1:receipt:" + canonical_json_sha256_v1(material),
    }


def _apply_authenticated_source_repair_artifact_v1(
    *,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    page_records: Sequence[Mapping[str, Any]] | None = None,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Apply exact selected-cell transcriptions to clones of pinned pages."""

    overlay = compiled_specs.get("source_repair_overlay")
    if overlay is None:
        return dict(page_json_by_version), []
    artifact_ref = compiled_specs.get("source_repair_artifact_ref")
    if type(overlay) is not dict or type(artifact_ref) is not dict:
        raise _error("fixed-asset compiled source-repair artifact is invalid")
    record_by_version = {}
    if page_records is not None:
        for record in page_records:
            version_id = record.get("page_json_version_id")
            if type(version_id) is not str or version_id in record_by_version:
                raise _error("fixed-asset source-repair page-record axis is invalid")
            record_by_version[version_id] = record
    effective_pages = dict(page_json_by_version)
    receipts = []
    for repair in overlay["repairs"]:
        version_id = repair["base_page_json_version_id"]
        if version_id not in page_json_by_version:
            continue
        source = repair["source_binding"]
        if page_records is not None:
            record = record_by_version.get(version_id)
            if record is None or any(
                record.get(field) != source[field]
                for field in (
                    "document_id",
                    "physical_page",
                    "source_logical_name",
                    "source_sha256",
                )
            ):
                raise _error("fixed-asset authenticated source-repair page record drifted")
        base_page = page_json_by_version[version_id]
        if (
            type(base_page) is not dict
            or canonical_json_sha256_v1(base_page) != repair["base_page_json_sha256"]
        ):
            raise _error("fixed-asset authenticated source-repair base page drifted")
        table_ref = repair["table_ref"]
        _base_section, base_table = _source_table(
            base_page,
            section_id=table_ref["section_id"],
            table_id=table_ref["table_id"],
        )
        if canonical_json_sha256_v1(base_table) != table_ref["base_table_sha256"]:
            raise _error("fixed-asset authenticated source-repair base table drifted")
        effective_page = canonical_clone_v1(base_page)
        _effective_section, effective_table = _source_table(
            effective_page,
            section_id=table_ref["section_id"],
            table_id=table_ref["table_id"],
        )
        rows = effective_table.get("rows")
        columns = effective_table.get("columns")
        if type(rows) is not list or type(columns) is not list:
            raise _error("fixed-asset authenticated source-repair table axes are invalid")
        for cell_repair in repair["cell_repairs"]:
            match = re.fullmatch(
                r"r([1-9][0-9]*):c([1-9][0-9]*)", cell_repair["cell_id"]
            )
            if match is None:
                raise _error("fixed-asset authenticated source-repair cell identity drifted")
            row_index = int(match.group(1)) - 1
            column_index = int(match.group(2)) - 1
            if not (0 <= row_index < len(rows) and 0 <= column_index < len(columns)):
                raise _error("fixed-asset authenticated source-repair cell is out of bounds")
            row = rows[row_index]
            column = columns[column_index]
            values = row.get("values_exact") if isinstance(row, Mapping) else None
            if (
                type(values) is not list
                or len(values) != len(columns)
                or row.get("label_exact") != cell_repair["row_label_exact"]
                or not same_typed_json_v1(
                    row.get("hierarchy_path_exact"),
                    cell_repair["row_hierarchy_path_exact"],
                )
                or not same_typed_json_v1(
                    column.get("header_path_exact"),
                    cell_repair["column_header_path_exact"],
                )
                or not same_typed_json_v1(
                    values[column_index], cell_repair["before_exact"]
                )
            ):
                raise _error("fixed-asset authenticated source-repair cell binding drifted")
            values[column_index] = cell_repair["after_exact"]
        if canonical_json_sha256_v1(effective_table) != table_ref["effective_table_sha256"]:
            raise _error("fixed-asset authenticated source-repair effective table drifted")
        if canonical_json_sha256_v1(effective_page) != repair["effective_page_json_sha256"]:
            raise _error("fixed-asset authenticated source-repair effective page drifted")
        effective_pages[version_id] = effective_page
        receipts.append(
            _authenticated_source_repair_receipt_v1(
                compiled_specs=compiled_specs,
                repair=repair,
            )
        )
    receipts.sort(key=lambda item: item["repair_id"])
    return effective_pages, receipts


def _contains_alias(value: Any, alias: str) -> bool:
    folded = _normalized(value)
    return bool(folded and re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", folded))


def _surface_dates(value: Any) -> set[date]:
    folded = _normalized(value)
    dates = set()
    for day_text, month_text, year_text in _DATE_DMY.findall(folded):
        try:
            dates.add(date(int(year_text), int(month_text), int(day_text)))
        except ValueError:
            continue
    return dates


def _header_text(column: Mapping[str, Any]) -> str:
    path = column.get("header_path_exact")
    return " ".join(item for item in path if type(item) is str) if type(path) is list else ""


def _period_header_evidence(value: Any) -> bool:
    folded = _normalized(value)
    return bool(
        _surface_dates(value)
        or any(
            token in folded
            for token in (
                "so dau ky",
                "so dau nam",
                "so cuoi ky",
                "so cuoi nam",
                "current period",
                "comparative period",
            )
        )
    )


def _governed_period_end_from_surface(value: Any) -> date | None:
    folded = _normalized(value)
    fiscal_interim = re.search(
        r"(?<![a-z0-9])(?:ky\s+)?(3|6|9|ba|sau|chin)\s+thang\s+dau\s+"
        r"(?:cua\s+)?nam\s+tai\s+chinh\s+ket\s+thuc\s+(?:vao\s+)?"
        r"(?:ngay\s+)?([0-3]?\d)\s+(?:thang\s+)?([01]?\d)\s+"
        r"(?:nam\s+)?((?:19|20)\d{2})(?!\d)",
        folded,
    )
    if fiscal_interim is not None:
        months = {
            "3": 3,
            "6": 6,
            "9": 9,
            "ba": 3,
            "sau": 6,
            "chin": 9,
        }[fiscal_interim.group(1)]
        try:
            fiscal_end = date(
                int(fiscal_interim.group(4)),
                int(fiscal_interim.group(3)),
                int(fiscal_interim.group(2)),
            )
        except ValueError:
            return None
        base_month_index = fiscal_end.month - 1 + months
        interim_year = fiscal_end.year - 1 + base_month_index // 12
        interim_month = base_month_index % 12 + 1
        target_month_last_day = calendar.monthrange(interim_year, interim_month)[1]
        interim_day = (
            target_month_last_day
            if fiscal_end.day
            == calendar.monthrange(fiscal_end.year, fiscal_end.month)[1]
            else min(fiscal_end.day, target_month_last_day)
        )
        return date(interim_year, interim_month, interim_day)
    governed_full = re.search(
        r"(?:ky|nam|giai doan)?\s*(?:tai chinh\s*)?(?:ket thuc|ended)\s*"
        r"(?:vao\s*)?(?:ngay\s*)?([0-3]?\d)\s+(?:thang\s+)?([01]?\d)\s+"
        r"(?:nam\s+)?((?:19|20)\d{2})",
        folded,
    )
    if governed_full is not None:
        try:
            return date(
                int(governed_full.group(3)),
                int(governed_full.group(2)),
                int(governed_full.group(1)),
            )
        except ValueError:
            return None
    governed_as_at = re.search(
        r"(?<![a-z0-9])(?:tai|as at)\s+(?:ngay\s+)?([0-3]?\d)\s+"
        r"(?:thang\s+)?([01]?\d)\s+(?:nam\s+)?((?:19|20)\d{2})(?!\d)",
        folded,
    )
    if governed_as_at is not None:
        try:
            return date(
                int(governed_as_at.group(3)),
                int(governed_as_at.group(2)),
                int(governed_as_at.group(1)),
            )
        except ValueError:
            return None
    quarter = re.search(
        r"(?<![a-z0-9])quy\s+(i{1,3}|iv|[1-4])(?:\s*[/.-]\s*|\s+)"
        r"((?:19|20)\d{2})(?!\d)",
        folded,
    )
    if quarter is not None:
        quarter_token = quarter.group(1)
        quarter_ordinal = (
            int(quarter_token)
            if quarter_token.isdigit()
            else {"i": 1, "ii": 2, "iii": 3, "iv": 4}[quarter_token]
        )
        month_day = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}.get(
            quarter_ordinal
        )
        if month_day is not None:
            return date(int(quarter.group(2)), month_day[0], month_day[1])
    interim_months = re.search(
        r"(?<![a-z0-9])(?:giai doan\s+|ky\s+)?([369])\s+thang\s+dau\s+nam\s+"
        r"((?:19|20)\d{2})(?!\d)",
        folded,
    )
    if interim_months is not None:
        month = int(interim_months.group(1))
        day = {3: 31, 6: 30, 9: 30}[month]
        return date(int(interim_months.group(2)), month, day)
    # A bare reporting year is not proof of a calendar-year end.  Exact
    # day/month comes from source-visible endpoints or the typed document
    # reporting-date receipt; this also supports non-calendar fiscal years.
    return None


def _surface_axis(section: Mapping[str, Any], table: Mapping[str, Any]) -> list[str]:
    axis = []
    for value in (section.get("title_exact"), table.get("title_exact")):
        if type(value) is str and value.strip():
            axis.append(value)
    narratives = section.get("narratives_exact")
    if type(narratives) is list:
        axis.extend(value for value in narratives if type(value) is str and value.strip())
    return axis


def _owner_visible(
    section: Mapping[str, Any], table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> bool:
    if type(table.get("__adjacent_owner_continuation_receipt")) is dict:
        return True
    aliases = [_normalized(alias) for alias in compiled_specs["topology"]["parent"]["aliases"]]
    return any(
        _contains_alias(surface, alias)
        for surface in _surface_axis(section, table)
        for alias in aliases
    )


def _standalone_heading_alias(value: Any, alias: str) -> bool:
    folded = _normalized(value)
    return bool(
        folded
        and re.fullmatch(
            rf"(?:(?:[0-9]+(?:\s+[0-9]+)*|[ivxlcdm]+)\s+)?"
            rf"{re.escape(alias)}(?:\s+tiep theo)?",
            folded,
        )
    )


def _structural_reset_heading_hits(
    section: Mapping[str, Any], table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> list[dict[str, str]]:
    """Return only standalone configured reset headings, never incidental prose."""

    hits = []
    aliases = [
        _normalized(alias) for alias in compiled_specs["topology"]["structural_reset_aliases"]
    ]
    for surface in _surface_axis(section, table):
        for alias in aliases:
            if _standalone_heading_alias(surface, alias):
                hits.append({"alias": alias, "surface_exact": surface})
    return hits


def _supplemental_disclosure_role_hits(
    table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> list[str]:
    surfaces = [table.get("title_exact")]
    rows = table.get("rows")
    if type(rows) is list:
        for row in rows:
            if type(row) is not dict:
                continue
            surfaces.append(row.get("label_exact"))
    return sorted(
        {
            disclosure["role"]
            for disclosure in compiled_specs["evaluation"]["supplemental_disclosure_roles"]
            if any(_supplemental_surface_matches(surface, disclosure) for surface in surfaces)
            or (
                type(rows) is list
                and any(
                    type(row) is dict
                    and _supplemental_row_matches(
                        row,
                        disclosure,
                        table=table,
                        compiled_specs=compiled_specs,
                    )
                    for row in rows
                )
            )
        }
    )


def _supplemental_surface_matches(value: Any, disclosure: Mapping[str, Any]) -> bool:
    return any(_contains_alias(value, alias) for alias in disclosure["aliases"]) or all(
        any(_contains_alias(value, alias) for alias in group)
        for group in disclosure["required_token_groups"]
    )


def _supplemental_row_matches(
    row: Mapping[str, Any],
    disclosure: Mapping[str, Any],
    *,
    table: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> bool:
    """Match a disclosure row through its exact label or visible ancestor path."""

    surfaces = [row.get("label_exact")]
    path = row.get("hierarchy_path_exact")
    if type(path) is list:
        surfaces.extend(path)
    if any(_supplemental_surface_matches(surface, disclosure) for surface in surfaces):
        return True
    contextual_aliases = disclosure.get("contextual_aliases", [])
    columns = table.get("columns")
    family_asset_header_visible = bool(
        contextual_aliases
        and type(columns) is list
        and any(
            type(column) is dict
            and column.get("value_kind") == "MONEY"
            and any(
                _contains_alias(_header_text(column), alias)
                for alias in compiled_specs["evaluation"]["asset_header_aliases"]
            )
            for column in columns
        )
    )
    return bool(
        family_asset_header_visible
        and any(
            _contains_alias(surface, alias)
            for surface in surfaces
            for alias in contextual_aliases
        )
    )


def _source_only_row_matches(
    row: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> bool:
    path = row.get("hierarchy_path_exact")
    surfaces = [row.get("label_exact")]
    if type(path) is list:
        surfaces.extend(path)
    return any(
        _contains_alias(surface, alias)
        for surface in surfaces
        for alias in compiled_specs["evaluation"].get("source_only_row_aliases", [])
    )


def _source_only_surface_matches(
    value: Any, *, compiled_specs: Mapping[str, Any]
) -> bool:
    return any(
        _contains_alias(value, alias)
        for alias in compiled_specs["evaluation"].get("source_only_row_aliases", [])
    )


def _branch_layout_for_row(
    row: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any] | None:
    path = row.get("hierarchy_path_exact")
    surfaces = []
    if type(path) is list:
        # Extractors can retain a table-local owner above the accounting
        # branch (owner -> branch -> row).  Every source-visible ancestor is
        # admissible, while the unique-match requirement below still rejects
        # paths that mention more than one configured branch.
        surfaces.extend(item for item in path if type(item) is str)
    if not surfaces and type(row.get("label_exact")) is str:
        surfaces.append(row["label_exact"])
    matches = [
        layout
        for layout in compiled_specs["evaluation"]["branch_layouts"]
        if any(
            _contains_alias(surface, alias)
            for surface in surfaces
            for alias in layout["hierarchy_aliases"]
        )
    ]
    return matches[0] if len(matches) == 1 else None


def _source_only_carrying_control_role(
    row: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> str | None:
    """Classify one configured carrying endpoint that has no schema binding.

    Some fixed-asset schemas expose only cost and depreciation movements while
    the source table also prints carrying value as an arithmetic control.  The
    control remains source-only: it authenticates mapped endpoints but can
    never create a schema mapping.
    """

    policy = compiled_specs["evaluation"].get("source_only_carrying_control")
    if policy is None:
        return None
    path = row.get("hierarchy_path_exact")
    surfaces = [item for item in path if type(item) is str] if type(path) is list else []
    if not surfaces and type(row.get("label_exact")) is str:
        surfaces.append(row["label_exact"])
    if not any(
        _contains_alias(surface, alias)
        for surface in surfaces
        for alias in policy["hierarchy_aliases"]
    ):
        return None
    if row.get("row_kind") == "GROUP":
        return "GROUP"
    folded = _normalized(row.get("label_exact"))
    dates = _surface_dates(row.get("label_exact"))
    opening = any(item.month == 1 and item.day == 1 for item in dates) or any(
        token in folded for token in ("so du dau", "so dau", "tai ngay dau ky", "tai ngay dau nam")
    )
    ending = any(item.month != 1 or item.day != 1 for item in dates) or any(
        token in folded for token in ("so du cuoi", "so cuoi", "tai ngay cuoi ky", "tai ngay cuoi nam")
    )
    if opening and not ending:
        return "SOURCE_ONLY_CARRY_OPENING"
    if ending and not opening:
        return "SOURCE_ONLY_CARRY_ENDING"
    return None


def _endpoint_role(
    label: Any, layout: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> str | None:
    folded = _normalized(label)
    dates = _surface_dates(label)
    opening = any(item.month == 1 and item.day == 1 for item in dates) or any(
        token in folded for token in ("so du dau", "so dau", "tai ngay dau ky", "tai ngay dau nam")
    )
    ending = any(item.month != 1 or item.day != 1 for item in dates) or any(
        token in folded
        for token in ("so du cuoi", "so cuoi", "tai ngay cuoi ky", "tai ngay cuoi nam")
    )
    if opening and not ending:
        return layout["opening_role"]
    if ending and not opening:
        return layout["ending_role"]
    for role in (layout["opening_role"], layout["ending_role"]):
        if any(_contains_alias(label, alias) for alias in compiled_specs["role_aliases"][role]):
            return role
    return None


def _role_for_row(
    row: Mapping[str, Any], layout: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> str | None:
    forced_role = row.get("__forced_role")
    if forced_role in compiled_specs["recognized_roles_by_branch"][layout["branch_role"]]:
        return forced_role
    endpoint = _endpoint_role(row.get("label_exact"), layout, compiled_specs=compiled_specs)
    if endpoint is not None:
        return endpoint
    path = row.get("hierarchy_path_exact")
    ancestors = path[:-1] if type(path) is list else []
    candidates = []
    for role in compiled_specs["recognized_roles_by_branch"][layout["branch_role"]]:
        if role in {layout["opening_role"], layout["ending_role"]}:
            continue
        matching_aliases = []
        for matcher in compiled_specs["role_matchers"][role]:
            within_role = matcher["within_role"]
            if within_role not in {None, layout["branch_role"]} and not any(
                _contains_alias(surface, alias)
                for surface in ancestors
                for alias in compiled_specs["role_aliases"].get(within_role, [])
            ):
                continue
            matching_aliases.extend(
                alias
                for alias in matcher["aliases"]
                if _contains_alias(row.get("label_exact"), alias)
            )
        if matching_aliases:
            candidates.append((max(map(len, matching_aliases)), role))
    if not candidates:
        return None
    longest = max(item[0] for item in candidates)
    roles = {role for length, role in candidates if length == longest}
    ancestor_subtotal_roles = _visible_subtotal_ancestor_roles(
        row, layout, compiled_specs=compiled_specs
    )
    directions = {
        direction
        for direction in ("INCREASE", "DECREASE")
        if any(role.endswith("_" + direction) for role in ancestor_subtotal_roles)
    }
    if len(roles) > 1 and len(directions) == 1:
        direction = next(iter(directions))
        roles = {role for role in roles if role.endswith("_" + direction)}
    return next(iter(roles)) if len(roles) == 1 else None


def _visible_subtotal_ancestor_roles(
    row: Mapping[str, Any],
    layout: Mapping[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
) -> set[str]:
    path = row.get("hierarchy_path_exact")
    ancestors = list(path[:-1]) if type(path) is list else []
    if _flattened_child(row):
        ancestors.append(path[-1])
    return {
        subtotal_role
        for subtotal_role in layout["subtotal_roles"]
        if any(
            _contains_alias(surface, alias)
            for surface in ancestors
            for alias in compiled_specs["role_aliases"][subtotal_role]
        )
    }


def _table_period_receipt(
    section: Mapping[str, Any], table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    ending_dates = set()
    rows = table.get("rows")
    if type(rows) is list:
        for row in rows:
            if type(row) is not dict:
                continue
            if _source_only_row_matches(row, compiled_specs=compiled_specs):
                continue
            if any(
                _supplemental_row_matches(
                    row,
                    disclosure,
                    table=table,
                    compiled_specs=compiled_specs,
                )
                for disclosure in compiled_specs["evaluation"]["supplemental_disclosure_roles"]
            ):
                continue
            layout = _branch_layout_for_row(row, compiled_specs=compiled_specs)
            if layout is None:
                continue
            if _role_for_row(row, layout, compiled_specs=compiled_specs) == layout["ending_role"]:
                ending_dates.update(_surface_dates(row.get("label_exact")))
    column_header_surfaces = [
        surface
        for column in table.get("columns", [])
        if type(column) is dict
        for surface in column.get("header_path_exact", [])
        if type(surface) is str
    ]
    local_governed_dates = {
        item
        for surface in [table.get("title_exact"), *column_header_surfaces]
        if (item := _governed_period_end_from_surface(surface)) is not None
    }
    section_context_dates = {
        item
        for surface in [section.get("title_exact"), *(section.get("narratives_exact") or [])]
        if not _source_only_surface_matches(surface, compiled_specs=compiled_specs)
        if (item := _governed_period_end_from_surface(surface)) is not None
    }
    adjacent_period_receipt = table.get("__immediately_preceding_table_period_receipt")
    adjacent_period_date = (
        adjacent_period_receipt.get("period_end_date")
        if type(adjacent_period_receipt) is dict
        else None
    )
    # Table-local narratives and endpoint rows outrank a page/section report
    # heading.  This lets a comparative table retain its prior-year date when
    # it appears under a current-period report header, while still rejecting
    # contradictions inside the table's own source boundary.
    local_dates = ending_dates | local_governed_dates
    if len(local_dates) > 1:
        status = "CONFLICTING_SOURCE_VISIBLE_PERIOD_END_DATES"
        period_end_date = None
    elif len(local_dates) == 1:
        status = "UNIQUE_SOURCE_VISIBLE_PERIOD_END_DATE"
        period_end_date = next(iter(local_dates)).isoformat()
    elif len(section_context_dates) == 1:
        status = "UNIQUE_SECTION_CONTEXT_PERIOD_END_DATE"
        period_end_date = next(iter(section_context_dates)).isoformat()
    elif len(section_context_dates) > 1:
        status = "MULTIPLE_SECTION_CONTEXT_PERIOD_END_DATES_REQUIRE_TABLE_RELATION"
        period_end_date = None
    elif (
        type(adjacent_period_date) is str
        and adjacent_period_receipt.get("status")
        == "EXACT_IMMEDIATELY_PRECEDING_TABLE_AS_AT_DATE"
    ):
        status = "UNIQUE_IMMEDIATELY_PRECEDING_TABLE_PERIOD_END_DATE"
        period_end_date = adjacent_period_date
    else:
        status = "NO_EXACT_PERIOD_END_DATE"
        period_end_date = None
    return {
        "endpoint_dates": sorted(item.isoformat() for item in ending_dates),
        "local_governed_surface_dates": sorted(item.isoformat() for item in local_governed_dates),
        "immediately_preceding_table_period_receipt": (
            canonical_clone_v1(adjacent_period_receipt)
            if type(adjacent_period_receipt) is dict
            else None
        ),
        "period_end_date": period_end_date,
        "section_context_dates": sorted(item.isoformat() for item in section_context_dates),
        "status": status,
    }


def _project_immediately_preceding_table_period(
    table: Mapping[str, Any],
    *,
    section: Mapping[str, Any],
    page_json: Mapping[str, Any],
    page_json_version_id: str,
    physical_page: int,
    section_ordinal: int,
    table_ordinal: int,
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Bind a date only from the immediately preceding sibling table.

    This covers a page-local note layout where one explicit ``Tại ngày`` row
    states the report date and the very next fixed-asset section continues
    without repeating it.  No date is guessed from filename, year, ordering,
    or a non-adjacent table.
    """

    projected = canonical_clone_v1(table)
    policy = compiled_specs["evaluation"].get(
        "immediately_preceding_table_period_policy"
    )
    if (
        policy is None
        or section_ordinal <= 1
        or table_ordinal != 1
        or not _owner_visible(section, table, compiled_specs=compiled_specs)
        or _table_period_receipt(section, table, compiled_specs=compiled_specs)[
            "period_end_date"
        ]
        is not None
    ):
        return projected, None
    sections = page_json.get("sections")
    if type(sections) is not list or section_ordinal > len(sections):
        return projected, None
    preceding_section = sections[section_ordinal - 2]
    preceding_tables = (
        preceding_section.get("tables") if type(preceding_section) is dict else None
    )
    if type(preceding_tables) is not list or not preceding_tables:
        return projected, None
    preceding_table = preceding_tables[-1]
    if type(preceding_table) is not dict:
        return projected, None
    evidence = []
    for row_ordinal, row in enumerate(preceding_table.get("rows", []), start=1):
        if type(row) is not dict:
            continue
        label = row.get("label_exact")
        folded = _normalized(label)
        period_end = _governed_period_end_from_surface(label)
        if period_end is not None and (
            folded.startswith("tai ngay ") or folded.startswith("as at ")
        ):
            evidence.append(
                {
                    "label_exact": label,
                    "period_end_date": period_end.isoformat(),
                    "row_id": f"r{row_ordinal}",
                }
            )
    dates = {item["period_end_date"] for item in evidence}
    if len(evidence) != 1 or len(dates) != 1:
        return projected, None
    material = {
        "current_section_id": f"s{section_ordinal}",
        "current_table_id": "t1",
        "evidence": evidence,
        "page_json_version_id": page_json_version_id,
        "period_end_date": next(iter(dates)),
        "physical_page": physical_page,
        "policy": policy,
        "preceding_section_id": f"s{section_ordinal - 1}",
        "preceding_table_id": f"t{len(preceding_tables)}",
        "preceding_table_sha256": canonical_json_sha256_v1(preceding_table),
        "status": "EXACT_IMMEDIATELY_PRECEDING_TABLE_AS_AT_DATE",
    }
    receipt = {
        **material,
        "receipt_id": "faiptsv1:receipt:" + canonical_json_sha256_v1(material),
    }
    projected["__immediately_preceding_table_period_receipt"] = receipt
    return projected, receipt


def _required_branch_roles(compiled_specs: Mapping[str, Any]) -> set[str]:
    configured = {
        item["branch_role"] for item in compiled_specs["evaluation"]["branch_layouts"]
    }
    component_policy = compiled_specs["evaluation"].get("component_policy")
    optional = (
        set(component_policy["optional_absent_branch_roles"]) & configured
        if component_policy is not None
        else set()
    )
    return configured - optional


def _endpoint_kind(value: Any) -> str | None:
    folded = _normalized(value)
    dates = _surface_dates(value)
    opening = any(item.month == 1 and item.day == 1 for item in dates) or any(
        token in folded for token in ("so du dau", "so dau", "tai ngay dau ky", "tai ngay dau nam")
    )
    ending = any(item.month != 1 or item.day != 1 for item in dates) or any(
        token in folded for token in ("so du cuoi", "so cuoi", "tai ngay cuoi ky", "tai ngay cuoi nam")
    )
    if opening and not ending:
        return "OPENING"
    if ending and not opening:
        return "ENDING"
    return None


def _project_endpoint_first_unknown_numeric_columns(
    table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> tuple[dict[str, Any], list[int], dict[str, Any] | None]:
    """Type a fully numeric endpoint table whose extractor left every column UNKNOWN.

    This is deliberately narrower than general value-kind inference: every column
    must be UNKNOWN, every header must be a configured asset or the unique
    right-edge total, and every populated cell must parse as exact integer money.
    The endpoint row topology is still proved separately before the projection is
    accepted.
    """

    projected = canonical_clone_v1(table)
    columns = projected.get("columns")
    rows = projected.get("rows")
    if type(columns) is not list or type(rows) is not list or not columns:
        return projected, [], None
    typed_money_ordinals = [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    if typed_money_ordinals:
        return projected, typed_money_ordinals, None
    if not all(
        type(column) is dict and column.get("value_kind") == "UNKNOWN"
        for column in columns
    ):
        return projected, [], None

    family_ordinals = []
    total_ordinals = []
    for ordinal, column in enumerate(columns, start=1):
        header = _header_text(column)
        if any(
            _contains_alias(header, alias)
            for alias in compiled_specs["evaluation"]["header_hard_negative_aliases"]
        ):
            return projected, [], None
        if any(
            _contains_alias(header, alias)
            for alias in compiled_specs["evaluation"]["asset_header_aliases"]
        ):
            family_ordinals.append(ordinal)
        if any(
            _contains_alias(header, alias)
            for alias in compiled_specs["evaluation"]["total_column_aliases"]
        ):
            total_ordinals.append(ordinal)
    if (
        len(family_ordinals)
        < compiled_specs["evaluation"]["minimum_distinct_asset_header_aliases"]
        or total_ordinals != [len(columns)]
        or sorted({*family_ordinals, *total_ordinals})
        != list(range(1, len(columns) + 1))
    ):
        return projected, [], None

    populated_by_column = [0] * len(columns)
    for row_ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict:
            return canonical_clone_v1(table), [], None
        values = row.get("values_exact")
        if type(values) is not list or len(values) != len(columns):
            return canonical_clone_v1(table), [], None
        for column_ordinal, value in enumerate(values, start=1):
            if value in {None, ""}:
                continue
            try:
                _money(
                    value,
                    source_locator={
                        "column_ordinal": column_ordinal,
                        "row_ordinal": row_ordinal,
                    },
                )
            except GeminiJsonFixedAssetRollforwardFamilyV1Error:
                return canonical_clone_v1(table), [], None
            populated_by_column[column_ordinal - 1] += 1
    if not all(populated_by_column):
        return canonical_clone_v1(table), [], None

    for column in projected["columns"]:
        column["value_kind"] = "MONEY"
    receipt = {
        "column_ordinals": list(range(1, len(columns) + 1)),
        "policy": (
            "ALL_UNKNOWN_COLUMNS_CONFIGURED_ASSET_OR_UNIQUE_RIGHT_EDGE_TOTAL_"
            "WITH_EXACT_INTEGER_MONEY_CELLS"
        ),
        "source_value_kind": "UNKNOWN",
    }
    return projected, list(range(1, len(columns) + 1)), receipt


def _project_endpoint_first_table(
    table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    policy = compiled_specs["evaluation"].get("endpoint_first_layout")
    if policy is None:
        return canonical_clone_v1(table), None
    existing_receipt = table.get("__endpoint_first_layout_receipt")
    if type(existing_receipt) is dict:
        return canonical_clone_v1(table), canonical_clone_v1(existing_receipt)
    rows = table.get("rows")
    columns = table.get("columns")
    if type(rows) is not list or type(columns) is not list:
        return canonical_clone_v1(table), None
    projected_source, money_ordinals, column_typing_receipt = (
        _project_endpoint_first_unknown_numeric_columns(
            table, compiled_specs=compiled_specs
        )
    )
    rows = projected_source["rows"]
    columns = projected_source["columns"]
    descriptors = []
    current_endpoint = None
    parent_label_by_endpoint = {}
    for source_ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict:
            return canonical_clone_v1(table), None
        values = row.get("values_exact")
        has_money = type(values) is list and any(
            ordinal <= len(values) and values[ordinal - 1] not in {None, ""}
            for ordinal in money_ordinals
        )
        if not has_money:
            continue
        endpoint = _endpoint_kind(row.get("label_exact"))
        cost = any(
            _contains_alias(row.get("label_exact"), alias)
            for alias in policy["cost_child_aliases"]
        )
        depreciation = any(
            _contains_alias(row.get("label_exact"), alias)
            for alias in policy["depreciation_child_aliases"]
        )
        if endpoint is not None and not cost and not depreciation:
            current_endpoint = endpoint
            parent_label_by_endpoint[endpoint] = row.get("label_exact")
            descriptors.append(("CARRYING_BRANCH", endpoint, source_ordinal, row))
        elif current_endpoint is not None and cost != depreciation:
            descriptors.append(
                (
                    "COST_BRANCH" if cost else "DEPRECIATION_BRANCH",
                    current_endpoint,
                    source_ordinal,
                    row,
                )
            )
        else:
            return canonical_clone_v1(table), None
    expected = [
        ("CARRYING_BRANCH", "OPENING"),
        ("COST_BRANCH", "OPENING"),
        ("DEPRECIATION_BRANCH", "OPENING"),
        ("CARRYING_BRANCH", "ENDING"),
        ("COST_BRANCH", "ENDING"),
        ("DEPRECIATION_BRANCH", "ENDING"),
    ]
    if [(branch, endpoint) for branch, endpoint, _ordinal, _row in descriptors] != expected:
        return canonical_clone_v1(table), None
    by_key = {
        (branch, endpoint): (source_ordinal, row)
        for branch, endpoint, source_ordinal, row in descriptors
    }
    layout_by_branch = {
        layout["branch_role"]: layout
        for layout in compiled_specs["evaluation"]["branch_layouts"]
    }
    projected_rows = []
    receipts = []
    for branch_role in ("COST_BRANCH", "DEPRECIATION_BRANCH", "CARRYING_BRANCH"):
        layout = layout_by_branch.get(branch_role)
        if layout is None:
            return canonical_clone_v1(table), None
        for endpoint in ("OPENING", "ENDING"):
            source_ordinal, source_row = by_key[(branch_role, endpoint)]
            projected_role = layout[
                "opening_role" if endpoint == "OPENING" else "ending_role"
            ]
            projected_row = canonical_clone_v1(source_row)
            projected_row["__engine_row_id"] = "endpoint-first:" + projected_role
            projected_row["__source_hierarchy_path_exact"] = canonical_clone_v1(
                source_row.get(
                    "__source_hierarchy_path_exact",
                    source_row.get("hierarchy_path_exact"),
                )
            )
            projected_row["__source_label_exact"] = source_row.get(
                "__source_label_exact", source_row.get("label_exact")
            )
            projected_row["__source_ordinal"] = source_row.get(
                "__source_ordinal", source_ordinal
            )
            projected_row["__source_row_id"] = source_row.get(
                "__source_row_id", f"r{source_ordinal}"
            )
            projected_row["__source_row_kind"] = source_row.get("row_kind")
            if branch_role == "CARRYING_BRANCH":
                projected_row["row_kind"] = "TOTAL"
            projected_row["hierarchy_path_exact"] = [
                layout["hierarchy_aliases"][0],
                parent_label_by_endpoint[endpoint],
            ]
            projected_row["label_exact"] = parent_label_by_endpoint[endpoint]
            projected_rows.append(projected_row)
            receipts.append(
                {
                    "endpoint_kind": endpoint,
                    "projected_role": projected_role,
                    "source_label_exact": source_row.get("label_exact"),
                    "source_ordinal": source_ordinal,
                }
            )
    receipt = {
        "column_typing_receipt": column_typing_receipt,
        "layout_kind": policy["layout_kind"],
        "projection_kind": "ENDPOINT_ONLY_NO_MOVEMENT_ROLLFORWARD_EQUATION",
        "rows": receipts,
    }
    projected_table = projected_source
    projected_table["rows"] = projected_rows
    projected_table["__endpoint_first_layout_receipt"] = receipt
    return projected_table, receipt


def _project_leading_implicit_cost_branch(
    table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Bind a source-order cost prefix terminated by an explicit depreciation branch.

    Some presentations print the cost rows immediately below the fixed-asset
    owner and omit only the ``Nguyên giá`` group heading.  This projection is
    deliberately structural: it requires an unscoped leading population, the
    first explicit branch to be depreciation, and every projected numeric row
    to bind one configured cost role.  Arithmetic closure remains mandatory
    after the projection.
    """

    policy = compiled_specs["evaluation"].get("leading_implicit_cost_branch_policy")
    projected = canonical_clone_v1(table)
    if policy is None:
        return projected, None
    existing = table.get("__leading_implicit_cost_branch_receipt")
    if type(existing) is dict:
        return projected, canonical_clone_v1(existing)
    rows = table.get("rows")
    columns = table.get("columns")
    if type(rows) is not list or type(columns) is not list:
        return projected, None
    money_ordinals = [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    if not money_ordinals:
        return projected, None
    cost_layouts = [
        layout
        for layout in compiled_specs["evaluation"]["branch_layouts"]
        if layout["rollforward_kind"] == "SIGNED_ADDITIVE"
        and layout["opening_role"].startswith("COST_")
    ]
    depreciation_layouts = [
        layout
        for layout in compiled_specs["evaluation"]["branch_layouts"]
        if layout["rollforward_kind"] == "SIGNED_ADDITIVE"
        and layout["opening_role"].startswith("DEP_")
    ]
    if len(cost_layouts) != 1 or len(depreciation_layouts) != 1:
        return projected, None
    cost_layout = cost_layouts[0]
    depreciation_layout = depreciation_layouts[0]
    first_explicit = next(
        (
            (ordinal, layout)
            for ordinal, row in enumerate(rows, start=1)
            if type(row) is dict
            and (layout := _branch_layout_for_row(row, compiled_specs=compiled_specs))
            is not None
        ),
        None,
    )
    if first_explicit is None or first_explicit[1] != depreciation_layout:
        return projected, None
    prefix_end = first_explicit[0] - 1
    candidates = []
    for source_ordinal, row in enumerate(rows[:prefix_end], start=1):
        if type(row) is not dict:
            return canonical_clone_v1(table), None
        if row.get("row_kind") == "GROUP":
            # A missing cost heading cannot be inferred across an unrelated
            # source-visible group boundary.
            return canonical_clone_v1(table), None
        values = row.get("values_exact")
        has_money = type(values) is list and any(
            ordinal <= len(values) and values[ordinal - 1] not in {None, ""}
            for ordinal in money_ordinals
        )
        if not has_money:
            continue
        synthetic = canonical_clone_v1(row)
        source_path = row.get("hierarchy_path_exact")
        synthetic["hierarchy_path_exact"] = [
            cost_layout["hierarchy_aliases"][0],
            *(
                canonical_clone_v1(source_path)
                if type(source_path) is list and source_path
                else [row.get("label_exact")]
            ),
        ]
        role = _role_for_row(synthetic, cost_layout, compiled_specs=compiled_specs)
        if role is None:
            return canonical_clone_v1(table), None
        candidates.append((source_ordinal, role, synthetic["hierarchy_path_exact"]))
    if not candidates:
        return canonical_clone_v1(table), None
    roles = [role for _ordinal, role, _path in candidates]
    if (
        roles.count(cost_layout["opening_role"]) != 1
        or roles.count(cost_layout["ending_role"]) != 1
        or roles[0] != cost_layout["opening_role"]
        or roles[-1] != cost_layout["ending_role"]
    ):
        return canonical_clone_v1(table), None
    receipts = []
    for source_ordinal, role, hierarchy_path in candidates:
        source_row = rows[source_ordinal - 1]
        target = projected["rows"][source_ordinal - 1]
        target["__source_hierarchy_path_exact"] = canonical_clone_v1(
            source_row.get("hierarchy_path_exact")
        )
        target["hierarchy_path_exact"] = hierarchy_path
        receipts.append(
            {
                "projected_role": role,
                "source_ordinal": source_ordinal,
            }
        )
    receipt = {
        "branch_role": cost_layout["branch_role"],
        "first_explicit_branch_role": depreciation_layout["branch_role"],
        "policy": policy,
        "projection_kind": "SOURCE_ORDER_LEADING_IMPLICIT_COST_BRANCH",
        "rows": receipts,
    }
    projected["__leading_implicit_cost_branch_receipt"] = receipt
    return projected, receipt


def _project_ordered_dated_endpoints(
    table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Bind two dated balance rows by their exact chronological order.

    A calendar-year roll-forward can print both endpoints as 31 December
    dates.  A row-local rule therefore cannot distinguish the prior-year
    opening balance from the current-year ending balance.  This projection is
    enabled declaratively and only binds a branch when it contains exactly two
    distinct dated, non-movement money rows.
    """

    policy = compiled_specs["evaluation"].get("ordered_dated_endpoint_policy")
    if policy is None:
        return canonical_clone_v1(table), None
    existing_receipt = table.get("__ordered_dated_endpoint_receipt")
    if type(existing_receipt) is dict:
        return canonical_clone_v1(table), canonical_clone_v1(existing_receipt)
    rows = table.get("rows")
    columns = table.get("columns")
    if type(rows) is not list or type(columns) is not list:
        return canonical_clone_v1(table), None
    money_ordinals = [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    projected = canonical_clone_v1(table)
    projected_rows = projected["rows"]
    receipts = []
    for layout in compiled_specs["evaluation"]["branch_layouts"]:
        candidates = []
        movement_roles = (
            set(compiled_specs["recognized_roles_by_branch"][layout["branch_role"]])
            - {layout["opening_role"], layout["ending_role"]}
        )
        for source_ordinal, row in enumerate(rows, start=1):
            if type(row) is not dict or row.get("row_kind") == "GROUP":
                continue
            if _source_only_row_matches(row, compiled_specs=compiled_specs):
                continue
            if any(
                _supplemental_row_matches(
                    row,
                    disclosure,
                    table=table,
                    compiled_specs=compiled_specs,
                )
                for disclosure in compiled_specs["evaluation"]["supplemental_disclosure_roles"]
            ):
                continue
            if _branch_layout_for_row(row, compiled_specs=compiled_specs) != layout:
                continue
            values = row.get("values_exact")
            if type(values) is not list or not any(
                ordinal <= len(values) and values[ordinal - 1] not in {None, ""}
                for ordinal in money_ordinals
            ):
                continue
            dates = _surface_dates(row.get("label_exact"))
            if len(dates) != 1:
                continue
            if any(
                _contains_alias(row.get("label_exact"), alias)
                for role in movement_roles
                for alias in compiled_specs["role_aliases"][role]
            ):
                continue
            candidates.append((source_ordinal, next(iter(dates))))
        if len(candidates) != 2 or len({item[1] for item in candidates}) != 2:
            continue
        chronological = sorted(candidates, key=lambda item: item[1])
        for (source_ordinal, parsed), role in zip(
            chronological,
            (layout["opening_role"], layout["ending_role"]),
            strict=True,
        ):
            projected_rows[source_ordinal - 1]["__forced_role"] = role
            receipts.append(
                {
                    "branch_role": layout["branch_role"],
                    "date": parsed.isoformat(),
                    "projected_role": role,
                    "source_ordinal": source_ordinal,
                }
            )
    if not receipts:
        return projected, None
    receipt = {
        "policy": policy,
        "projection_kind": "TWO_DISTINCT_DATED_BALANCE_ROWS_CHRONOLOGICAL_ENDPOINT_BINDING",
        "rows": receipts,
    }
    projected["__ordered_dated_endpoint_receipt"] = receipt
    return projected, receipt


def _project_ordered_branch_scope(
    table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Restore a uniquely typed row dropped from its visible branch path.

    The projection is bounded by source order: an explicit configured branch
    starts the scope, an unmatched group ends it, and only a numeric row whose
    label binds exactly one role in that branch may inherit the scope.
    """

    policy = compiled_specs["evaluation"].get("ordered_branch_scope_policy")
    if policy is None:
        return canonical_clone_v1(table), None
    existing_receipt = table.get("__ordered_branch_scope_receipt")
    if type(existing_receipt) is dict:
        return canonical_clone_v1(table), canonical_clone_v1(existing_receipt)
    rows = table.get("rows")
    columns = table.get("columns")
    if type(rows) is not list or type(columns) is not list:
        return canonical_clone_v1(table), None
    money_ordinals = [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    projected = canonical_clone_v1(table)
    receipts = []
    current_layout = None
    for source_ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict:
            current_layout = None
            continue
        explicit_layout = _branch_layout_for_row(row, compiled_specs=compiled_specs)
        if explicit_layout is not None:
            current_layout = explicit_layout
            continue
        if row.get("row_kind") == "GROUP":
            current_layout = None
            continue
        if current_layout is None or _source_only_row_matches(
            row, compiled_specs=compiled_specs
        ):
            continue
        values = row.get("values_exact")
        if type(values) is not list or not any(
            ordinal <= len(values) and values[ordinal - 1] not in {None, ""}
            for ordinal in money_ordinals
        ):
            continue
        synthetic = canonical_clone_v1(row)
        synthetic["hierarchy_path_exact"] = [
            current_layout["hierarchy_aliases"][0],
            row.get("label_exact"),
        ]
        role = _role_for_row(synthetic, current_layout, compiled_specs=compiled_specs)
        if role is None:
            continue
        projected_row = projected["rows"][source_ordinal - 1]
        projected_row["__source_hierarchy_path_exact"] = canonical_clone_v1(
            row.get("hierarchy_path_exact")
        )
        projected_row["hierarchy_path_exact"] = synthetic["hierarchy_path_exact"]
        receipts.append(
            {
                "branch_role": current_layout["branch_role"],
                "projected_role": role,
                "source_ordinal": source_ordinal,
            }
        )
    if not receipts:
        return projected, None
    receipt = {
        "policy": policy,
        "projection_kind": "PRECEDING_EXPLICIT_BRANCH_UNIQUE_ROLE_BINDING",
        "rows": receipts,
    }
    projected["__ordered_branch_scope_receipt"] = receipt
    return projected, receipt


def _single_asset_current_period_column_binding(
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    *,
    money_ordinals: Sequence[int],
    total_ordinals: Sequence[int],
    negative_header_hits: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Select one source-visible current column from a single-asset period axis.

    Some schedules repeat the same sole asset in current and comparative
    columns instead of printing a separate total.  The current column is
    usable only when one exact section reporting date binds exactly one of the
    distinct source period headers.  The comparative column remains source
    only; no source cell or header is rewritten.
    """

    policy = compiled_specs["evaluation"].get("single_asset_period_column_policy")
    columns = table.get("columns")
    if (
        policy is None
        or type(columns) is not list
        or len(money_ordinals) < 2
        or total_ordinals
        or negative_header_hits
    ):
        return None
    longest_asset_aliases = []
    period_axis = []
    for ordinal in money_ordinals:
        header = _header_text(columns[ordinal - 1])
        hits = [
            alias
            for alias in compiled_specs["evaluation"]["asset_header_aliases"]
            if _contains_alias(header, alias)
        ]
        if not hits:
            return None
        longest = max(map(len, hits))
        identities = {alias for alias in hits if len(alias) == longest}
        if len(identities) != 1:
            return None
        longest_asset_aliases.append(next(iter(identities)))
        explicit_dates = _surface_dates(header)
        if len(explicit_dates) > 1:
            return None
        if explicit_dates:
            parsed = next(iter(explicit_dates))
            period_axis.append(
                {
                    "column_ordinal": ordinal,
                    "evidence_kind": "EXACT_DATE",
                    "period_date": parsed.isoformat(),
                    "period_year": parsed.year,
                }
            )
            continue
        years = {
            int(match.group(0))
            for match in re.finditer(r"(?<!\d)(?:19|20)\d{2}(?!\d)", _normalized(header))
        }
        if len(years) != 1:
            return None
        period_axis.append(
            {
                "column_ordinal": ordinal,
                "evidence_kind": "EXACT_YEAR_WITH_SECTION_DATE",
                "period_date": None,
                "period_year": next(iter(years)),
            }
        )
    if len(set(longest_asset_aliases)) != 1:
        return None
    identities = {
        (item["period_date"], item["period_year"])
        for item in period_axis
    }
    if len(identities) != len(period_axis):
        return None
    section_dates = {
        item
        for surface in [section.get("title_exact"), *(section.get("narratives_exact") or [])]
        if (item := _governed_period_end_from_surface(surface)) is not None
    }
    if len(section_dates) != 1:
        return None
    current = next(iter(section_dates))
    selected = [
        item
        for item in period_axis
        if (
            item["period_date"] == current.isoformat()
            if item["period_date"] is not None
            else item["period_year"] == current.year
        )
    ]
    if len(selected) != 1:
        return None
    selected_ordinal = selected[0]["column_ordinal"]
    material = {
        "asset_alias": longest_asset_aliases[0],
        "period_end_date": current.isoformat(),
        "policy": policy,
        "selected_current_column_ordinal": selected_ordinal,
        "source_money_column_ordinals": list(money_ordinals),
        "source_period_axis": period_axis,
        "source_values_mutated": False,
    }
    return {
        **material,
        "receipt_id": "faspcrv1:receipt:" + canonical_json_sha256_v1(material),
    }


def _cropped_total_complete_asset_frontier_binding(
    columns: Sequence[Mapping[str, Any]],
    *,
    source_money_ordinals: Sequence[int],
    family_header_ordinals: Sequence[int],
    total_ordinals: Sequence[int],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Bind one visibly truncated terminal total without using its cells.

    This is deliberately narrower than treating a table without a total as an
    implicit aggregate.  The source must contain exactly one terminal MONEY
    column whose non-empty header is a strict textual prefix of a configured
    total header, while every preceding MONEY column is a recognized asset
    column.  The truncated column and all of its values remain source-only.
    """

    if (
        compiled_specs["evaluation"].get("row_level_strict_subset_policy")
        != _ROW_LEVEL_STRICT_SUBSET_POLICY
        or total_ordinals
        or len(source_money_ordinals) < 3
        or list(family_header_ordinals) != list(source_money_ordinals[:-1])
    ):
        return None
    cropped_ordinal = source_money_ordinals[-1]
    if cropped_ordinal != len(columns):
        return None
    cropped_header_exact = _header_text(columns[cropped_ordinal - 1]).strip()
    cropped_header = _normalized(cropped_header_exact)
    if len(cropped_header) < 3:
        return None
    matching_aliases = sorted(
        alias
        for alias in compiled_specs["evaluation"]["total_column_aliases"]
        if alias != cropped_header and alias.startswith(cropped_header)
    )
    if not matching_aliases:
        return None
    asset_headers = [
        _normalized(_header_text(columns[ordinal - 1]))
        for ordinal in family_header_ordinals
    ]
    if any(not header for header in asset_headers) or len(asset_headers) != len(
        set(asset_headers)
    ):
        return None
    material = {
        "asset_column_ordinals": list(family_header_ordinals),
        "binding_kind": "CROPPED_PRINTED_TOTAL_COMPLETE_DISJOINT_ASSET_FRONTIER",
        "cropped_total_column_ordinal": cropped_ordinal,
        "cropped_total_header_exact": cropped_header_exact,
        "matching_declared_total_aliases": matching_aliases,
        "policy": _ROW_LEVEL_STRICT_SUBSET_POLICY,
        "source_cropped_total_cells_consumed": False,
    }
    return {
        **material,
        "receipt_id": "factafv1:receipt:" + canonical_json_sha256_v1(material),
    }


def classify_gemini_json_fixed_asset_rollforward_table_v1(
    section: Any, table: Any, *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Classify one table from owner, typed headers and complete branch seeds."""

    if type(section) is not dict or type(table) is not dict:
        raise _error("fixed-asset section/table is invalid")
    table, leading_implicit_cost_branch_receipt = _project_leading_implicit_cost_branch(
        table, compiled_specs=compiled_specs
    )
    table, endpoint_first_layout_receipt = _project_endpoint_first_table(
        table, compiled_specs=compiled_specs
    )
    table, ordered_branch_scope_receipt = _project_ordered_branch_scope(
        table, compiled_specs=compiled_specs
    )
    table, ordered_dated_endpoint_receipt = _project_ordered_dated_endpoints(
        table, compiled_specs=compiled_specs
    )
    rows = table.get("rows")
    columns = table.get("columns")
    if type(rows) is not list or type(columns) is not list:
        raise _error("fixed-asset table axes are invalid")
    source_money_ordinals = [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    family_header_ordinals = []
    negative_header_hits = []
    total_ordinals = []
    for ordinal in source_money_ordinals:
        header = _header_text(columns[ordinal - 1])
        if any(
            _contains_alias(header, alias)
            for alias in compiled_specs["evaluation"]["asset_header_aliases"]
        ):
            family_header_ordinals.append(ordinal)
        for alias in compiled_specs["evaluation"]["header_hard_negative_aliases"]:
            if _contains_alias(header, alias):
                negative_header_hits.append({"alias": alias, "column_ordinal": ordinal})
        if any(
            _contains_alias(header, alias)
            for alias in compiled_specs["evaluation"]["total_column_aliases"]
        ):
            total_ordinals.append(ordinal)
    single_asset_period_column_receipt = _single_asset_current_period_column_binding(
        section,
        table,
        money_ordinals=source_money_ordinals,
        total_ordinals=total_ordinals,
        negative_header_hits=negative_header_hits,
        compiled_specs=compiled_specs,
    )
    cropped_total_asset_frontier_binding = (
        _cropped_total_complete_asset_frontier_binding(
            columns,
            source_money_ordinals=source_money_ordinals,
            family_header_ordinals=family_header_ordinals,
            total_ordinals=total_ordinals,
            compiled_specs=compiled_specs,
        )
    )
    if single_asset_period_column_receipt is None:
        money_ordinals = list(source_money_ordinals)
    else:
        selected_period_ordinal = single_asset_period_column_receipt[
            "selected_current_column_ordinal"
        ]
        money_ordinals = [selected_period_ordinal]
        family_header_ordinals = [selected_period_ordinal]
    branch_hits = set()
    recognized_row_count = 0
    source_only_carrying_control_row_count = 0
    unclassified_numeric_rows = []
    for ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict:
            continue
        if any(
            _supplemental_row_matches(
                row,
                disclosure,
                table=table,
                compiled_specs=compiled_specs,
            )
            for disclosure in compiled_specs["evaluation"]["supplemental_disclosure_roles"]
        ):
            continue
        if _source_only_row_matches(row, compiled_specs=compiled_specs):
            continue
        values = row.get("values_exact")
        has_money = type(values) is list and any(
            index - 1 < len(values) and values[index - 1] not in {None, ""}
            for index in money_ordinals
        )
        source_only_control_role = _source_only_carrying_control_role(
            row, compiled_specs=compiled_specs
        )
        if source_only_control_role is not None:
            if source_only_control_role != "GROUP" and has_money:
                source_only_carrying_control_row_count += 1
            continue
        layout = _branch_layout_for_row(row, compiled_specs=compiled_specs)
        if layout is None:
            if row.get("row_kind") != "GROUP" and has_money:
                unclassified_numeric_rows.append(ordinal)
            continue
        branch_hits.add(layout["branch_role"])
        if row.get("row_kind") == "GROUP":
            continue
        role = _role_for_row(row, layout, compiled_specs=compiled_specs)
        if role is None and has_money:
            unclassified_numeric_rows.append(ordinal)
        elif role is not None:
            recognized_row_count += 1
    required_branches = _required_branch_roles(compiled_specs)
    owner = _owner_visible(section, table, compiled_specs=compiled_specs)
    structural_reset_heading_hits = _structural_reset_heading_hits(
        section, table, compiled_specs=compiled_specs
    )
    explicit_owner_heading_visible = any(
        _standalone_heading_alias(surface, _normalized(alias))
        for surface in _surface_axis(section, table)
        for alias in compiled_specs["topology"]["parent"]["aliases"]
    )
    variant_hard_negative_visible = any(
        _contains_alias(surface, negative_alias)
        and not any(
            _contains_alias(source_alias, negative_alias) and _contains_alias(surface, source_alias)
            for role_aliases in compiled_specs["role_aliases"].values()
            for source_alias in role_aliases
        )
        for surface in _surface_axis(section, table)
        for negative_alias in compiled_specs["evaluation"]["header_hard_negative_aliases"]
    )
    explicit_variant_hard_negative_heading_visible = any(
        _standalone_heading_alias(surface, negative_alias)
        for surface in _surface_axis(section, table)
        for negative_alias in compiled_specs["evaluation"]["header_hard_negative_aliases"]
    )
    scoped_variant_hard_negative_visible = bool(
        explicit_variant_hard_negative_heading_visible
        or (variant_hard_negative_visible and not explicit_owner_heading_visible)
    )
    two_period_non_rollforward_control = bool(
        owner
        and not required_branches <= branch_hits
        and not family_header_ordinals
        and len(money_ordinals) == 2
        and all(
            _period_header_evidence(_header_text(columns[ordinal - 1]))
            for ordinal in money_ordinals
        )
    )
    supplemental_disclosure_roles = _supplemental_disclosure_role_hits(
        table, compiled_specs=compiled_specs
    )
    supplemental_only_control = bool(
        supplemental_disclosure_roles and not required_branches <= branch_hits
    )
    # A section owner can legitimately govern a two-period informational
    # control table (for example fully-depreciated assets).  Such a table is
    # not a roll-forward fragment.
    min_headers = compiled_specs["evaluation"]["minimum_distinct_asset_header_aliases"]
    implicit_single_asset_total = bool(
        len(money_ordinals) == 1
        and family_header_ordinals == money_ordinals
        and min_headers == 1
        and single_asset_period_column_receipt is None
        and not total_ordinals
        and not negative_header_hits
        and not scoped_variant_hard_negative_visible
    )
    single_asset_period_total = single_asset_period_column_receipt is not None
    effective_total_ordinals = (
        list(money_ordinals)
        if implicit_single_asset_total or single_asset_period_total
        else total_ordinals
    )
    has_governed_total_binding = bool(
        (
            len(effective_total_ordinals) == 1
            and effective_total_ordinals[0] == money_ordinals[-1]
        )
        or cropped_total_asset_frontier_binding is not None
    )
    has_family_signal = bool(
        not two_period_non_rollforward_control
        and not supplemental_only_control
        # A standalone sibling-family heading terminates owner scope when the
        # configured owner appears only incidentally in prose.  If both owners
        # are themselves explicit headings, retain the table as unresolved so
        # that a real source-scope conflict cannot silently become absence.
        and (not structural_reset_heading_hits or explicit_owner_heading_visible)
        and (
            (owner and (family_header_ordinals or branch_hits))
            or (
                required_branches <= branch_hits
                and len(family_header_ordinals) >= min_headers
                and not negative_header_hits
                and not scoped_variant_hard_negative_visible
            )
        )
    )
    if single_asset_period_column_receipt is None:
        period_receipt = _table_period_receipt(section, table, compiled_specs=compiled_specs)
    else:
        period_receipt = {
            "endpoint_dates": [],
            "immediately_preceding_table_period_receipt": None,
            "local_governed_surface_dates": [
                single_asset_period_column_receipt["period_end_date"]
            ],
            "period_end_date": single_asset_period_column_receipt["period_end_date"],
            "section_context_dates": [
                single_asset_period_column_receipt["period_end_date"]
            ],
            "single_asset_period_column_receipt": canonical_clone_v1(
                single_asset_period_column_receipt
            ),
            "status": "UNIQUE_SINGLE_ASSET_CURRENT_PERIOD_COLUMN",
        }
    reasons = []
    if negative_header_hits and has_family_signal:
        reasons.append("HARD_NEGATIVE_ASSET_HEADER_VISIBLE")
    if scoped_variant_hard_negative_visible and owner:
        reasons.append("HARD_NEGATIVE_FIXED_ASSET_VARIANT_SURFACE_VISIBLE")
    if branch_hits and not required_branches <= branch_hits:
        reasons.append("CONFIGURED_BRANCH_SEED_FRONTIER_INCOMPLETE")
    if required_branches <= branch_hits and not owner:
        reasons.append("EXPLICIT_FIXED_ASSET_OWNER_NOT_VISIBLE")
    if (
        required_branches <= branch_hits
        and len(family_header_ordinals)
        < compiled_specs["evaluation"]["minimum_distinct_asset_header_aliases"]
    ):
        reasons.append("DISTINCT_ASSET_HEADER_FRONTIER_INCOMPLETE")
    if required_branches <= branch_hits and (
        not money_ordinals or not has_governed_total_binding
    ):
        reasons.append("UNIQUE_RIGHT_EDGE_TOTAL_COLUMN_NOT_VISIBLE")
    if unclassified_numeric_rows:
        reasons.append("UNCLASSIFIED_NUMERIC_ROW_INSIDE_FIXED_ASSET_BRANCH")
    if period_receipt["status"] == "CONFLICTING_SOURCE_VISIBLE_PERIOD_END_DATES":
        reasons.append("FIXED_ASSET_TABLE_PERIOD_EVIDENCE_CONFLICT")
    complete = (
        required_branches <= branch_hits
        and owner
        and len(family_header_ordinals)
        >= compiled_specs["evaluation"]["minimum_distinct_asset_header_aliases"]
        and has_governed_total_binding
        and not reasons
    )
    return {
        "branch_roles": sorted(branch_hits),
        "complete": complete,
        "family_header_column_ordinals": family_header_ordinals,
        "family_signal": has_family_signal,
        "hard_negative_header_hits": negative_header_hits,
        "leading_implicit_cost_branch_receipt": leading_implicit_cost_branch_receipt,
        "money_column_ordinals": money_ordinals,
        "source_money_column_ordinals": source_money_ordinals,
        "cropped_total_complete_asset_frontier_binding": (
            cropped_total_asset_frontier_binding
        ),
        "owner_visible": owner,
        "endpoint_first_layout_receipt": endpoint_first_layout_receipt,
        "ordered_dated_endpoint_receipt": ordered_dated_endpoint_receipt,
        "ordered_branch_scope_receipt": ordered_branch_scope_receipt,
        "single_asset_period_column_receipt": single_asset_period_column_receipt,
        "period_end_date": period_receipt["period_end_date"],
        "period_receipt": period_receipt,
        "reasons": sorted(set(reasons)),
        "recognized_row_count": recognized_row_count,
        "source_only_carrying_control_row_count": source_only_carrying_control_row_count,
        "structural_reset_heading_hits": structural_reset_heading_hits,
        "total_column_binding_kind": (
            "IMPLICIT_SINGLE_RECOGNIZED_ASSET_MONEY_COLUMN"
            if implicit_single_asset_total
            else (
                "IMPLICIT_SINGLE_RECOGNIZED_ASSET_CURRENT_PERIOD_COLUMN"
                if single_asset_period_total
                else (
                    "EXPLICIT_RIGHT_EDGE_TOTAL_COLUMN"
                    if effective_total_ordinals
                    else (
                        "CROPPED_PRINTED_TOTAL_COMPLETE_DISJOINT_ASSET_FRONTIER"
                        if cropped_total_asset_frontier_binding is not None
                        else None
                    )
                )
            )
        ),
        "total_column_ordinals": effective_total_ordinals,
        "unclassified_numeric_row_ordinals": unclassified_numeric_rows,
    }


def _endpoint_total_signature(
    section: Mapping[str, Any], table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> dict[str, int] | None:
    table, _leading_implicit_cost_branch_receipt = _project_leading_implicit_cost_branch(
        table, compiled_specs=compiled_specs
    )
    table, _endpoint_first_layout_receipt = _project_endpoint_first_table(
        table, compiled_specs=compiled_specs
    )
    table, _ordered_branch_scope_receipt = _project_ordered_branch_scope(
        table, compiled_specs=compiled_specs
    )
    table, _ordered_dated_endpoint_receipt = _project_ordered_dated_endpoints(
        table, compiled_specs=compiled_specs
    )
    classification = classify_gemini_json_fixed_asset_rollforward_table_v1(
        section, table, compiled_specs=compiled_specs
    )
    if not classification["complete"]:
        return None
    cropped_binding = classification.get(
        "cropped_total_complete_asset_frontier_binding"
    )
    total_ordinal = (
        classification["total_column_ordinals"][0]
        if cropped_binding is None
        else None
    )
    signature = {}
    for row in table.get("rows", []):
        if type(row) is not dict or row.get("row_kind") == "GROUP":
            continue
        layout = _branch_layout_for_row(row, compiled_specs=compiled_specs)
        if layout is None:
            continue
        role = _role_for_row(row, layout, compiled_specs=compiled_specs)
        if role not in {layout["opening_role"], layout["ending_role"]}:
            continue
        values = row.get("values_exact")
        if type(values) is not list or (
            total_ordinal is not None and total_ordinal > len(values)
        ):
            return None
        try:
            if cropped_binding is None:
                cells = [
                    _money(
                        values[total_ordinal - 1],
                        source_locator={"period_selection_endpoint": role},
                    )
                ]
            else:
                cells = [
                    _money(
                        values[ordinal - 1],
                        source_locator={
                            "asset_column_ordinal": ordinal,
                            "period_selection_endpoint": role,
                        },
                    )
                    for ordinal in cropped_binding["asset_column_ordinals"]
                ]
        except GeminiJsonFixedAssetRollforwardFamilyV1Error:
            return None
        if any(cell["state"] == "BLANK" for cell in cells) or role in signature:
            return None
        signature[role] = sum(cell["coefficient"] for cell in cells)
    expected = {
        role
        for layout in compiled_specs["evaluation"]["branch_layouts"]
        for role in (layout["opening_role"], layout["ending_role"])
    }
    return signature if set(signature) == expected else None


def _combined_endpoint_roles(
    label: Any, layout: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> list[str]:
    """Return both roles only for one row with bounded explicit endpoint semantics."""

    if compiled_specs["evaluation"].get("component_policy") is None:
        return []
    movement_roles = set(compiled_specs["recognized_roles_by_branch"][layout["branch_role"]]) - {
        layout["opening_role"],
        layout["ending_role"],
    }
    if any(
        _contains_alias(label, alias)
        for role in movement_roles
        for alias in compiled_specs["role_aliases"][role]
    ):
        return []
    dates = sorted(set(_surface_dates(label)))
    if len(dates) == 2:
        opening = [item for item in dates if item.month == 1 and item.day == 1]
        ending = [item for item in dates if not (item.month == 1 and item.day == 1)]
        folded = _normalized(label)
        explicit_endpoint_pair = bool(
            len(folded.split()) <= 24
            and (
                re.match(r"(?:so du )?tai ngay\b", folded)
                or re.match(r"(?:balance )?(?:as at|at)\b", folded)
            )
            and re.search(r"\b(?:va|and)\b", folded)
        )
        if (
            len(opening) == 1
            and len(ending) == 1
            and opening[0] < ending[0]
            and explicit_endpoint_pair
        ):
            return [layout["opening_role"], layout["ending_role"]]
    folded = _normalized(label)
    # Some source tables print one unchanged endpoint row such as "opening
    # and closing balance" instead of duplicating the same value.  This is a
    # structural relation, not a family-specific value inference.  Require a
    # bounded source-visible grammar containing both endpoint directions and
    # an explicit connector; a lone opening/closing alias never qualifies.
    tokens = folded.split()
    combined_semantics = bool(
        len(tokens) <= 14
        and (
            re.search(
                r"(?:so du )?dau (?:ky|nam)(?: [a-z0-9]+){0,4} "
                r"(?:va|den)(?: [a-z0-9]+){0,4} (?:so du )?cuoi (?:ky|nam)",
                folded,
            )
            or re.search(
                r"(?:opening|beginning)(?: [a-z0-9]+){0,4} "
                r"(?:and|to)(?: [a-z0-9]+){0,4} (?:closing|end)",
                folded,
            )
        )
    )
    if not combined_semantics:
        return []
    return [layout["opening_role"], layout["ending_role"]]


def _expanded_component_table(
    table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any], default_branch_role: str | None
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Build a local projection while retaining every physical source-row locator."""

    projected = canonical_clone_v1(table)
    rows = projected.get("rows")
    if type(rows) is not list:
        return projected, []
    layout_by_role = {
        item["branch_role"]: item for item in compiled_specs["evaluation"]["branch_layouts"]
    }
    receipts = []
    expanded = []
    for source_ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict:
            expanded.append(row)
            continue
        sanitized_row = canonical_clone_v1(row)
        for key in list(sanitized_row):
            if type(key) is str and key.startswith("__"):
                sanitized_row.pop(key)
        layout = _branch_layout_for_row(sanitized_row, compiled_specs=compiled_specs)
        if layout is None and default_branch_role is not None:
            layout = layout_by_role[default_branch_role]
        roles = (
            _combined_endpoint_roles(
                sanitized_row.get("label_exact"), layout, compiled_specs=compiled_specs
            )
            if layout is not None
            else []
        )
        projected_rows = []
        if roles:
            dates = sorted(set(_surface_dates(sanitized_row.get("label_exact"))))
            opening_dates = [item for item in dates if item.month == 1 and item.day == 1]
            ending_dates = [item for item in dates if not (item.month == 1 and item.day == 1)]
            date_by_role = (
                {
                    layout["opening_role"]: opening_dates[0],
                    layout["ending_role"]: ending_dates[0],
                }
                if len(opening_dates) == len(ending_dates) == 1
                else {}
            )
            for role in roles:
                clone = canonical_clone_v1(sanitized_row)
                if date_by_role:
                    parsed = date_by_role[role]
                    label = f"Tại ngày {parsed.day} tháng {parsed.month} năm {parsed.year}"
                    clone["label_exact"] = label
                    path = clone.get("hierarchy_path_exact")
                    if type(path) is list and path:
                        path[-1] = label
                clone["__forced_role"] = role
                clone["__engine_row_id"] = f"r{source_ordinal}:{role}"
                clone["__source_row_id"] = f"r{source_ordinal}"
                clone["__source_ordinal"] = source_ordinal
                projected_rows.append(clone)
            receipts.append(
                {
                    "binding_kind": (
                        "ONE_SOURCE_ROW_BINDS_DISTINCT_OPENING_AND_ENDING_DATES"
                        if date_by_role
                        else "ONE_SOURCE_ROW_BINDS_EXPLICIT_OPENING_AND_ENDING_SEMANTICS"
                    ),
                    "roles": roles,
                    "source_label_exact": sanitized_row.get("label_exact"),
                    "source_row_id": f"r{source_ordinal}",
                }
            )
        else:
            clone = canonical_clone_v1(sanitized_row)
            clone["__source_row_id"] = f"r{source_ordinal}"
            clone["__source_ordinal"] = source_ordinal
            projected_rows.append(clone)
        for clone in projected_rows:
            if default_branch_role is not None and layout is not None:
                hierarchy = clone.get("hierarchy_path_exact")
                first = hierarchy[0] if type(hierarchy) is list and hierarchy else None
                if not any(_contains_alias(first, alias) for alias in layout["hierarchy_aliases"]):
                    clone["hierarchy_path_exact"] = [
                        layout["hierarchy_aliases"][0],
                        clone.get("label_exact"),
                    ]
            expanded.append(clone)
    projected["rows"] = expanded
    return projected, receipts


def _summary_control_classification(
    section: Mapping[str, Any], table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any] | None:
    policy = compiled_specs["evaluation"].get("component_policy")
    if policy is None or not _owner_visible(section, table, compiled_specs=compiled_specs):
        return None
    columns = table.get("columns")
    rows = table.get("rows")
    if type(columns) is not list or type(rows) is not list:
        return None
    money_ordinals = [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    if len(money_ordinals) != 2:
        return None
    dates_by_column = [
        sorted(set(_surface_dates(_header_text(columns[ordinal - 1]))))
        for ordinal in money_ordinals
    ]
    if any(len(axis) != 1 for axis in dates_by_column):
        return None
    period_dates = [axis[0] for axis in dates_by_column]
    if len(set(period_dates)) != 2:
        return None
    total_rows = [
        ordinal
        for ordinal, row in enumerate(rows, start=1)
        if type(row) is dict and row.get("row_kind") == "TOTAL"
    ]
    aliases = policy["summary_control"]["row_aliases"]
    declared_row_bindings = []
    for ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict or row.get("row_kind") == "TOTAL":
            continue
        matches = [alias for alias in aliases if _contains_alias(row.get("label_exact"), alias)]
        if len(matches) == 1:
            declared_row_bindings.append(
                {
                    "matched_summary_row_alias": matches[0],
                    "row_id": f"r{ordinal}",
                    "source_ordinal": ordinal,
                }
            )
    non_total_numeric = [
        row
        for row in rows
        if type(row) is dict
        and row.get("row_kind") != "TOTAL"
        and type(row.get("values_exact")) is list
        and any(row["values_exact"][ordinal - 1] not in {None, ""} for ordinal in money_ordinals)
    ]
    if (
        len(total_rows) != 1
        or total_rows[0] != len(rows)
        or not declared_row_bindings
        or len(declared_row_bindings) != len(non_total_numeric)
        or len({item["matched_summary_row_alias"] for item in declared_row_bindings})
        != len(declared_row_bindings)
    ):
        return None
    return {
        "branch_roles": [],
        "complete": True,
        "component_kind": "CARRYING_SUMMARY_CONTROL",
        "declared_summary_row_bindings": declared_row_bindings,
        "family_header_column_ordinals": [],
        "family_signal": True,
        "hard_negative_header_hits": [],
        "money_column_ordinals": money_ordinals,
        "owner_visible": True,
        "period_end_date": max(period_dates).isoformat(),
        "period_receipt": {
            "column_period_dates": [item.isoformat() for item in period_dates],
            "period_end_date": max(period_dates).isoformat(),
            "status": "UNIQUE_TWO_COLUMN_CARRYING_SUMMARY_PERIOD_AXIS",
        },
        "reasons": [],
        "recognized_row_count": len(declared_row_bindings) + 1,
        "total_column_ordinals": [],
        "unclassified_numeric_row_ordinals": [],
        "control_row_ordinal": total_rows[0],
    }


def _statement_root_row_ordinals(
    section: Mapping[str, Any], table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> list[int]:
    """Inventory configured root rows without treating child labels as the root."""

    if not (
        compiled_specs["evaluation"].get("component_policy") is not None
        and section.get("content_kind") == "PRIMARY_STATEMENT"
        and section.get("statement_type") == "BALANCE_SHEET"
        and type(table.get("rows")) is list
    ):
        return []
    owner_aliases = [
        _normalized(alias) for alias in compiled_specs["topology"]["parent"]["aliases"]
    ]
    # The statement line is a control for the family root.  A branch line or
    # a configured component-population line may contain the root wording as
    # a prefix (for example, "investment property - accumulated
    # depreciation").  Derive the exclusion frontier from the declarative
    # family config instead of maintaining language- or family-specific
    # negative tokens here.
    child_aliases = {
        alias
        for layout in compiled_specs["evaluation"]["branch_layouts"]
        for alias in layout["hierarchy_aliases"]
    }
    child_aliases.update(
        alias for aliases in compiled_specs["role_aliases"].values() for alias in aliases
    )
    child_aliases.update(
        compiled_specs["evaluation"]["component_policy"]["summary_control"]["row_aliases"]
    )
    result = []
    for ordinal, row in enumerate(table["rows"], start=1):
        if type(row) is not dict:
            continue
        folded = _normalized(row.get("label_exact"))
        if any(_contains_alias(folded, alias) for alias in owner_aliases) and not any(
            _contains_alias(folded, alias) for alias in child_aliases
        ):
            result.append(ordinal)
    return result


def _statement_carrying_control_classification(
    section: Mapping[str, Any], table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any] | None:
    """Bind the family carrying line from a typed balance sheet, never its child rows."""

    control_rows = _statement_root_row_ordinals(section, table, compiled_specs=compiled_specs)
    if len(control_rows) != 1:
        return None
    columns = table.get("columns")
    rows = table.get("rows")
    if type(columns) is not list or type(rows) is not list:
        return None
    money_ordinals = [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    if len(money_ordinals) != 2:
        return None
    dates_by_column = [
        sorted(set(_surface_dates(_header_text(columns[ordinal - 1]))))
        for ordinal in money_ordinals
    ]
    control_values = rows[control_rows[0] - 1].get("values_exact")
    if (
        type(control_values) is not list
        or len(control_values) != len(columns)
        or not any(control_values[index - 1] not in {None, ""} for index in money_ordinals)
    ):
        return None
    if all(len(axis) == 1 for axis in dates_by_column):
        period_dates = [axis[0] for axis in dates_by_column]
        if len(set(period_dates)) != 2:
            return None
        return {
            "branch_roles": [],
            "complete": True,
            "component_kind": "PRIMARY_STATEMENT_CARRYING_CONTROL",
            "control_row_ordinal": control_rows[0],
            "family_header_column_ordinals": [],
            "family_signal": True,
            "hard_negative_header_hits": [],
            "money_column_ordinals": money_ordinals,
            "owner_visible": True,
            "period_end_date": max(period_dates).isoformat(),
            "period_receipt": {
                "column_period_dates": [item.isoformat() for item in period_dates],
                "period_end_date": max(period_dates).isoformat(),
                "status": "UNIQUE_TYPED_BALANCE_SHEET_CARRYING_PERIOD_AXIS",
            },
            "reasons": [],
            "recognized_row_count": 1,
            "total_column_ordinals": [],
            "unclassified_numeric_row_ordinals": [],
        }
    # A typed balance sheet can label its two amount columns only by relative
    # roles (for example, ``Số cuối năm`` and ``Số đầu năm``). Bind that
    # layout only when the section supplies one exact reporting endpoint. The
    # opening column remains a source-visible relative role; no comparative
    # endpoint is fabricated from a year or from arithmetic.
    if any(dates_by_column):
        return None
    section_surfaces = [
        ("SECTION_TITLE", section.get("title_exact")),
        *[
            ("SECTION_NARRATIVE", item)
            for item in (section.get("narratives_exact") or [])
            if type(item) is str
        ],
    ]
    governed_evidence = []
    all_surface_dates = set()
    for source_kind, surface in section_surfaces:
        all_surface_dates.update(_surface_dates(surface))
        governed = _governed_period_end_from_surface(surface)
        if governed is not None:
            governed_evidence.append(
                {
                    "period_end_date": governed.isoformat(),
                    "source_kind": source_kind,
                    "surface_exact": surface,
                }
            )
    governed_dates = {item["period_end_date"] for item in governed_evidence}
    if len(governed_dates) != 1:
        return None
    period_end_date = next(iter(governed_dates))
    if all_surface_dates != {date.fromisoformat(period_end_date)}:
        return None
    summary_policy = compiled_specs["evaluation"]["component_policy"]["summary_control"]
    relative_aliases = {
        summary_policy["current_role"]: ("so cuoi ky", "so cuoi nam"),
        summary_policy["opening_role"]: ("so dau ky", "so dau nam"),
    }
    role_by_ordinal = {}
    for ordinal in money_ordinals:
        header = _header_text(columns[ordinal - 1])
        matched_roles = [
            role
            for role, aliases in relative_aliases.items()
            if any(_contains_alias(header, alias) for alias in aliases)
        ]
        if len(matched_roles) != 1:
            return None
        role_by_ordinal[ordinal] = matched_roles[0]
    if set(role_by_ordinal.values()) != set(relative_aliases):
        return None
    column_period_bindings = [
        {
            "column_header_exact": _header_text(columns[ordinal - 1]),
            "column_ordinal": ordinal,
            "period_date": (
                period_end_date if role == summary_policy["current_role"] else None
            ),
            "period_role": role,
            "source_kind": "TYPED_BALANCE_SHEET_RELATIVE_PERIOD_COLUMN",
        }
        for ordinal, role in role_by_ordinal.items()
    ]
    return {
        "branch_roles": [],
        "complete": True,
        "component_kind": "PRIMARY_STATEMENT_CARRYING_CONTROL",
        "control_row_ordinal": control_rows[0],
        "family_header_column_ordinals": [],
        "family_signal": True,
        "hard_negative_header_hits": [],
        "money_column_ordinals": money_ordinals,
        "owner_visible": True,
        "period_end_date": period_end_date,
        "period_receipt": {
            "column_period_bindings": column_period_bindings,
            "governed_period_evidence": governed_evidence,
            "period_end_date": period_end_date,
            "status": "UNIQUE_TYPED_BALANCE_SHEET_RELATIVE_CARRYING_PERIOD_AXIS",
        },
        "reasons": [],
        "recognized_row_count": 1,
        "total_column_ordinals": [],
        "unclassified_numeric_row_ordinals": [],
    }


def _component_table_classification(
    section: Mapping[str, Any], table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """Classify complete tables, configured fragments and carrying summaries."""

    table, leading_implicit_cost_branch_receipt = _project_leading_implicit_cost_branch(
        table, compiled_specs=compiled_specs
    )
    table, endpoint_first_layout_receipt = _project_endpoint_first_table(
        table, compiled_specs=compiled_specs
    )
    table, ordered_branch_scope_receipt = _project_ordered_branch_scope(
        table, compiled_specs=compiled_specs
    )
    table, ordered_dated_endpoint_receipt = _project_ordered_dated_endpoints(
        table, compiled_specs=compiled_specs
    )
    summary = _summary_control_classification(section, table, compiled_specs=compiled_specs)
    if summary is not None:
        return summary, canonical_clone_v1(table), []
    statement_control = _statement_carrying_control_classification(
        section, table, compiled_specs=compiled_specs
    )
    if statement_control is not None:
        return statement_control, canonical_clone_v1(table), []
    expanded, endpoint_receipts = _expanded_component_table(
        table, compiled_specs=compiled_specs, default_branch_role=None
    )
    if endpoint_first_layout_receipt is not None:
        endpoint_receipts = [endpoint_first_layout_receipt, *endpoint_receipts]
    if leading_implicit_cost_branch_receipt is not None:
        endpoint_receipts = [leading_implicit_cost_branch_receipt, *endpoint_receipts]
    if ordered_dated_endpoint_receipt is not None:
        endpoint_receipts = [ordered_dated_endpoint_receipt, *endpoint_receipts]
    if ordered_branch_scope_receipt is not None:
        endpoint_receipts = [ordered_branch_scope_receipt, *endpoint_receipts]
    standard = classify_gemini_json_fixed_asset_rollforward_table_v1(
        section, expanded, compiled_specs=compiled_specs
    )
    if standard["complete"]:
        return (
            {**standard, "component_kind": "COMPLETE_ROLLFORWARD_TABLE"},
            expanded,
            endpoint_receipts,
        )
    policy = compiled_specs["evaluation"].get("component_policy")
    if policy is None:
        return (
            {**standard, "component_kind": "INVALID_OR_UNSUPPORTED_TABLE"},
            expanded,
            endpoint_receipts,
        )
    candidates = []
    for branch_role in policy["default_branch_fragment_roles"]:
        projected, receipts = _expanded_component_table(
            table, compiled_specs=compiled_specs, default_branch_role=branch_role
        )
        fragment_specs = canonical_clone_v1(compiled_specs)
        layout = next(
            item
            for item in fragment_specs["evaluation"]["branch_layouts"]
            if item["branch_role"] == branch_role
        )
        fragment_specs["evaluation"]["branch_layouts"] = [layout]
        fragment_specs["output_roles_by_branch"] = {
            branch_role: fragment_specs["output_roles_by_branch"][branch_role]
        }
        fragment_specs["recognized_roles_by_branch"] = {
            branch_role: fragment_specs["recognized_roles_by_branch"][branch_role]
        }
        classification = classify_gemini_json_fixed_asset_rollforward_table_v1(
            section, projected, compiled_specs=fragment_specs
        )
        if classification["complete"]:
            candidates.append((branch_role, classification, projected, receipts))
    if len(candidates) == 1:
        branch_role, classification, projected, receipts = candidates[0]
        return (
            {
                **classification,
                "component_kind": "DEFAULT_BRANCH_ROLLFORWARD_FRAGMENT",
                "default_branch_role": branch_role,
            },
            projected,
            receipts,
        )
    if len(candidates) > 1:
        standard = {
            **standard,
            "family_signal": True,
            "reasons": sorted({*standard["reasons"], "DEFAULT_BRANCH_FRAGMENT_ROLE_IS_AMBIGUOUS"}),
        }
    summary_signal = _owner_visible(section, table, compiled_specs=compiled_specs) and any(
        _contains_alias(row.get("label_exact"), alias)
        for row in table.get("rows", [])
        if type(row) is dict
        for alias in policy["summary_control"]["row_aliases"]
    )
    statement_signal = bool(
        _statement_root_row_ordinals(section, table, compiled_specs=compiled_specs)
    )
    unresolved_control_signal = (summary_signal or statement_signal) and not standard[
        "family_signal"
    ]
    if unresolved_control_signal:
        standard = {
            **standard,
            "family_signal": True,
            "reasons": sorted(
                {
                    *standard["reasons"],
                    "CARRYING_SUMMARY_CONTROL_STRUCTURE_IS_NOT_AUTHENTICATED",
                }
            ),
        }
    return (
        {
            **standard,
            "component_kind": (
                "UNRESOLVED_CARRYING_SUMMARY_CONTROL"
                if unresolved_control_signal
                else "INVALID_OR_UNSUPPORTED_TABLE"
            ),
        },
        expanded,
        endpoint_receipts,
    )


def _continuity_selects_current(
    candidate: Mapping[str, Any],
    controls: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
) -> bool:
    current_signature = _endpoint_total_signature(
        candidate["section"], candidate["table"], compiled_specs=compiled_specs
    )
    if current_signature is None:
        return False
    for control in controls:
        comparative_signature = _endpoint_total_signature(
            control["section"], control["table"], compiled_specs=compiled_specs
        )
        if comparative_signature is None:
            return False
        for layout in compiled_specs["evaluation"]["branch_layouts"]:
            if (
                current_signature[layout["opening_role"]]
                != comparative_signature[layout["ending_role"]]
            ):
                return False
    return True


def _leading_undated_owner_sequence(
    tables: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> bool:
    if (
        compiled_specs["evaluation"].get("undated_full_table_sequence_policy")
        != "LEADING_EXPLICIT_OWNER_THEN_ADJACENT_CONTINUATION_TABLES_BIND_CURRENT_AS_SOURCE_ONLY_HISTORY"
        or len(tables) < 2
        or any(item["classification"]["period_end_date"] is not None for item in tables)
    ):
        return False
    parent_aliases = [
        _normalized(alias) for alias in compiled_specs["topology"]["parent"]["aliases"]
    ]
    first = tables[0]
    first_surfaces = _surface_axis(first["section"], first["table"])
    if (
        not any(
            _standalone_heading_alias(surface, alias)
            for surface in first_surfaces
            for alias in parent_aliases
        )
        or any(_contains_alias(surface, "tiep theo") for surface in first_surfaces)
    ):
        return False
    header_axis = [
        _normalized(_header_text(column))
        for column in first["table"].get("columns", [])
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    if not header_axis:
        return False
    prior = first
    for item in tables[1:]:
        surfaces = _surface_axis(item["section"], item["table"])
        current_axis = [
            _normalized(_header_text(column))
            for column in item["table"].get("columns", [])
            if type(column) is dict and column.get("value_kind") == "MONEY"
        ]
        if (
            item["record"]["selected_page_ordinal"]
            != prior["record"]["selected_page_ordinal"] + 1
            or item["record"]["physical_page"] != prior["record"]["physical_page"] + 1
            or current_axis != header_axis
            or not any(_contains_alias(surface, "tiep theo") for surface in surfaces)
            or not any(
                _contains_alias(surface, alias)
                for surface in surfaces
                for alias in parent_aliases
            )
        ):
            return False
        prior = item
    return True


def _adjacent_undated_owner_continuation_siblings(
    current: Mapping[str, Any],
    missing: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
) -> bool:
    """Authenticate undated historical tables by exact adjacent owner scope."""

    if not missing:
        return False
    parent_aliases = [
        _normalized(alias) for alias in compiled_specs["topology"]["parent"]["aliases"]
    ]

    def header_axis(item: Mapping[str, Any]) -> list[str]:
        return [
            _normalized(_header_text(column))
            for column in item["table"].get("columns", [])
            if type(column) is dict and column.get("value_kind") == "MONEY"
        ]

    expected_axis = header_axis(current)
    if not expected_axis:
        return False
    ordered = sorted(missing, key=lambda item: item["position"])
    prior = current
    for item in ordered:
        surfaces = _surface_axis(item["section"], item["table"])
        if (
            item["position"] <= current["position"]
            or item["record"]["selected_page_ordinal"]
            != prior["record"]["selected_page_ordinal"] + 1
            or item["record"]["physical_page"] != prior["record"]["physical_page"] + 1
            or header_axis(item) != expected_axis
            or not any(_contains_alias(surface, "tiep theo") for surface in surfaces)
            or not any(
                _contains_alias(surface, alias)
                for surface in surfaces
                for alias in parent_aliases
            )
        ):
            return False
        prior = item
    return True


def _document_reporting_date_receipt(page_records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    evidence = []
    for record in page_records:
        for section_ordinal, section in enumerate(record["page_json"].get("sections", []), start=1):
            if type(section) is not dict:
                continue
            if section.get("content_kind") == "PRIMARY_STATEMENT" and section.get(
                "statement_type"
            ) in {"BALANCE_SHEET", "INCOME_STATEMENT", "CASH_FLOW"}:
                governed_dates = {
                    item
                    for surface in [
                        section.get("title_exact"),
                        *(section.get("narratives_exact") or []),
                    ]
                    if (item := _governed_period_end_from_surface(surface)) is not None
                }
                if len(governed_dates) == 1:
                    current = next(iter(governed_dates))
                    evidence.append(
                        {
                            "comparative_date": None,
                            "current_date": current.isoformat(),
                            "page_json_version_id": record["page_json_version_id"],
                            "physical_page": record["physical_page"],
                            "section_id": f"s{section_ordinal}",
                            "source_kind": "TYPED_PRIMARY_STATEMENT_PERIOD_HEADING",
                            "statement_type": section["statement_type"],
                            "table_id": None,
                        }
                    )
            if not (
                section.get("content_kind") == "PRIMARY_STATEMENT"
                and section.get("statement_type") == "BALANCE_SHEET"
            ):
                continue
            for table_ordinal, table in enumerate(section.get("tables", []), start=1):
                if type(table) is not dict:
                    continue
                column_dates = []
                for column_ordinal, column in enumerate(table.get("columns", []), start=1):
                    if type(column) is not dict or column.get("value_kind") != "MONEY":
                        continue
                    dates = sorted(_surface_dates(_header_text(column)))
                    if len(dates) == 1:
                        column_dates.append((column_ordinal, dates[0]))
                distinct = sorted({item[1] for item in column_dates})
                if (
                    len(distinct) != 2
                    or not distinct[1] > distinct[0]
                    or (distinct[1] - distinct[0]).days > 366
                ):
                    continue
                evidence.append(
                    {
                        "comparative_date": distinct[0].isoformat(),
                        "current_date": distinct[1].isoformat(),
                        "page_json_version_id": record["page_json_version_id"],
                        "physical_page": record["physical_page"],
                        "section_id": f"s{section_ordinal}",
                        "source_kind": "TYPED_BALANCE_SHEET_DATE_COLUMNS",
                        "statement_type": "BALANCE_SHEET",
                        "table_id": f"t{table_ordinal}",
                    }
                )
    current_dates = sorted({item["current_date"] for item in evidence})
    comparative_dates = sorted(
        {item["comparative_date"] for item in evidence if item["comparative_date"] is not None}
    )
    current_date = current_dates[0] if len(current_dates) == 1 else None
    comparative_date = comparative_dates[0] if len(comparative_dates) == 1 else None
    status = "UNIQUE_TYPED_DOCUMENT_REPORTING_DATE" if current_date else "NOT_UNIQUE"
    if current_date is None:
        # A typed balance sheet governs point-in-time fixed-asset endpoints.
        # A stale title on a different primary-statement type must not poison
        # its unique reporting date, but conflicts within the balance-sheet
        # evidence itself remain unresolved.
        balance_sheet_evidence = [
            item for item in evidence if item["statement_type"] == "BALANCE_SHEET"
        ]
        balance_sheet_current_dates = sorted(
            {item["current_date"] for item in balance_sheet_evidence}
        )
        balance_sheet_comparative_dates = sorted(
            {
                item["comparative_date"]
                for item in balance_sheet_evidence
                if item["comparative_date"] is not None
            }
        )
        if len(balance_sheet_current_dates) == 1:
            current_date = balance_sheet_current_dates[0]
            comparative_date = (
                balance_sheet_comparative_dates[0]
                if len(balance_sheet_comparative_dates) == 1
                else None
            )
            status = "UNIQUE_TYPED_BALANCE_SHEET_DATE_DOMINATES_OTHER_STATEMENT_TYPES"
    return {
        "comparative_date": comparative_date,
        "current_date": current_date,
        "evidence": evidence,
        "status": status,
    }


def _page_record_axis(page_records: Any) -> list[dict[str, Any]]:
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
        raise _error("fixed-asset selected page records are absent")
    checked = []
    identity = None
    prior_position = None
    for raw in page_records:
        if (
            type(raw) is not dict
            or set(raw) != fields
            or _DOCUMENT_ID.fullmatch(raw.get("document_id", "")) is None
            or type(raw.get("document_ordinal")) is not int
            or raw["document_ordinal"] <= 0
            or _PAGE_VERSION.fullmatch(raw.get("page_json_version_id", "")) is None
            or type(raw.get("physical_page")) is not int
            or raw["physical_page"] <= 0
            or type(raw.get("selected_page_ordinal")) is not int
            or raw["selected_page_ordinal"] <= 0
            or type(raw.get("source_logical_name")) is not str
            or not raw["source_logical_name"]
            or _SHA256.fullmatch(raw.get("source_sha256", "")) is None
            or type(raw.get("page_json")) is not dict
            or type(raw["page_json"].get("sections")) is not list
        ):
            raise _error("fixed-asset selected page record is invalid")
        current_identity = tuple(
            raw[key]
            for key in ("document_id", "document_ordinal", "source_logical_name", "source_sha256")
        )
        position = (raw["selected_page_ordinal"], raw["physical_page"])
        if identity is None:
            identity = current_identity
        elif current_identity != identity:
            raise _error("fixed-asset page records cross document identity")
        if prior_position is not None and position <= prior_position:
            raise _error("fixed-asset page records are not ordered")
        prior_position = position
        checked.append(canonical_clone_v1(raw))
    if [item["selected_page_ordinal"] for item in checked] != list(range(1, len(checked) + 1)):
        raise _error("fixed-asset selected page ordinals are incomplete")
    return checked


def _region(
    item: Mapping[str, Any],
    *,
    component_role: str,
    fragment_ordinal: int,
    period_end_date: str | None,
    period_selection_kind: str,
) -> dict[str, Any]:
    return {
        "component_role": component_role,
        "document_id": item["record"]["document_id"],
        "document_ordinal": item["record"]["document_ordinal"],
        "fragment_ordinal": fragment_ordinal,
        "page_json_version_id": item["record"]["page_json_version_id"],
        "period_end_date": period_end_date,
        "period_selection_kind": period_selection_kind,
        "physical_page": item["record"]["physical_page"],
        "section_id": item["section_id"],
        "selected_page_ordinal": item["record"]["selected_page_ordinal"],
        "source_logical_name": item["record"]["source_logical_name"],
        "source_sha256": item["record"]["source_sha256"],
        "table_id": item["table_id"],
    }


def _bind_adjacent_owner_continuations(
    family_tables: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    policy = compiled_specs["evaluation"].get("adjacent_owner_continuation_policy")
    result = [canonical_clone_v1(item) for item in family_tables]
    if policy is None:
        return result

    def header_axis(table: Mapping[str, Any]) -> list[str]:
        return [
            _normalized(_header_text(column))
            for column in table.get("columns", [])
            if type(column) is dict and column.get("value_kind") == "MONEY"
        ]

    for index, item in enumerate(result):
        classification = item["classification"]
        if classification["owner_visible"] or "EXPLICIT_FIXED_ASSET_OWNER_NOT_VISIBLE" not in (
            classification["reasons"]
        ):
            continue
        continuation_surfaces = _surface_axis(item["section"], item["table"])
        if not any(_contains_alias(surface, "tiep theo") for surface in continuation_surfaces):
            continue
        if index == 0:
            continue
        prior = result[index - 1]
        if (
            not prior["classification"]["owner_visible"]
            or item["record"]["selected_page_ordinal"]
            != prior["record"]["selected_page_ordinal"] + 1
            or item["record"]["physical_page"] != prior["record"]["physical_page"] + 1
            or header_axis(item["table"]) != header_axis(prior["table"])
        ):
            continue
        projected_table = canonical_clone_v1(item["table"])
        receipt = {
            "binding_kind": policy,
            "owner_page_json_version_id": prior["record"]["page_json_version_id"],
            "owner_physical_page": prior["record"]["physical_page"],
            "status": "EXACT_ADJACENT_OWNER_SCOPE",
        }
        projected_table["__adjacent_owner_continuation_receipt"] = receipt
        rebound = classify_gemini_json_fixed_asset_rollforward_table_v1(
            item["section"], projected_table, compiled_specs=compiled_specs
        )
        if not rebound["complete"]:
            continue
        result[index] = {
            **item,
            "classification": {
                **rebound,
                "adjacent_owner_continuation_receipt": receipt,
            },
            "table": projected_table,
        }
    return result


def _trailing_owner_heading_receipt(
    prior_page_json: Mapping[str, Any],
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    *,
    owner_page_json_version_id: str,
    owner_physical_page: int,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    policy = compiled_specs["evaluation"].get("trailing_owner_heading_policy")
    if policy is None or _owner_visible(section, table, compiled_specs=compiled_specs):
        return None
    sections = prior_page_json.get("sections")
    if type(sections) is not list or not sections or type(sections[-1]) is not dict:
        return None
    owner_section = sections[-1]
    if type(owner_section.get("tables")) is not list or owner_section["tables"]:
        return None
    title = owner_section.get("title_exact")
    aliases = compiled_specs["topology"]["parent"]["aliases"]
    if not any(
        _standalone_heading_alias(title, _normalized(alias)) for alias in aliases
    ):
        return None
    if _structural_reset_heading_hits(section, table, compiled_specs=compiled_specs):
        return None
    return {
        "binding_kind": policy,
        "owner_page_json_version_id": owner_page_json_version_id,
        "owner_physical_page": owner_physical_page,
        "owner_section_id": f"s{len(sections)}",
        "status": "EXACT_TRAILING_OWNER_HEADING_NEXT_PAGE_SCOPE",
    }


def _project_trailing_owner_heading_from_page_map(
    table: Mapping[str, Any],
    *,
    section: Mapping[str, Any],
    region: Mapping[str, Any],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    projected = canonical_clone_v1(table)
    if (
        compiled_specs["evaluation"].get("trailing_owner_heading_policy") is None
        or region.get("section_id") != "s1"
        or region.get("table_id") != "t1"
        or type(region.get("selected_page_ordinal")) is not int
        or region["selected_page_ordinal"] <= 1
    ):
        return projected, None
    page_ids = list(page_json_by_version)
    current_index = region["selected_page_ordinal"] - 1
    if (
        current_index >= len(page_ids)
        or page_ids[current_index] != region.get("page_json_version_id")
    ):
        return projected, None
    owner_page_json_version_id = page_ids[current_index - 1]
    receipt = _trailing_owner_heading_receipt(
        page_json_by_version[owner_page_json_version_id],
        section,
        table,
        owner_page_json_version_id=owner_page_json_version_id,
        owner_physical_page=region["physical_page"] - 1,
        compiled_specs=compiled_specs,
    )
    if receipt is not None:
        projected["__adjacent_owner_continuation_receipt"] = receipt
    return projected, receipt


def _project_adjacent_page_endpoint_first_continuation_from_page_map(
    table: Mapping[str, Any],
    *,
    section: Mapping[str, Any],
    region: Mapping[str, Any],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Stitch one exact page-final endpoint table to a headerless next-page tail."""

    policy = compiled_specs["evaluation"].get(
        "adjacent_page_endpoint_first_continuation_policy"
    )
    projected = canonical_clone_v1(table)
    if policy is None:
        return projected, None
    existing = table.get("__adjacent_page_endpoint_first_continuation_receipt")
    if type(existing) is dict:
        return projected, canonical_clone_v1(existing)
    selected_ordinal = region.get("selected_page_ordinal")
    if type(selected_ordinal) is not int or selected_ordinal < 1:
        return projected, None
    page_ids = list(page_json_by_version)
    current_index = selected_ordinal - 1
    if (
        current_index + 1 >= len(page_ids)
        or page_ids[current_index] != region.get("page_json_version_id")
    ):
        return projected, None
    current_page = page_json_by_version[page_ids[current_index]]
    next_page_id = page_ids[current_index + 1]
    next_page = page_json_by_version[next_page_id]
    current_sections = current_page.get("sections")
    next_sections = next_page.get("sections")
    if type(current_sections) is not list or type(next_sections) is not list or not next_sections:
        return projected, None
    try:
        section_ordinal = int(region["section_id"][1:])
        table_ordinal = int(region["table_id"][1:])
    except (KeyError, TypeError, ValueError):
        return projected, None
    current_tables = (
        current_sections[section_ordinal - 1].get("tables")
        if 0 < section_ordinal <= len(current_sections)
        and type(current_sections[section_ordinal - 1]) is dict
        else None
    )
    if (
        section_ordinal != len(current_sections)
        or type(current_tables) is not list
        or table_ordinal != len(current_tables)
        or current_tables[table_ordinal - 1] != table
        or not _owner_visible(section, table, compiled_specs=compiled_specs)
    ):
        return projected, None
    leading_section = next_sections[0]
    leading_tables = leading_section.get("tables") if type(leading_section) is dict else None
    if type(leading_tables) is not list or not leading_tables or type(leading_tables[0]) is not dict:
        return projected, None
    continuation = leading_tables[0]
    if any(
        type(surface) is str and surface.strip()
        for surface in _surface_axis(leading_section, continuation)
    ):
        return projected, None
    first_columns = table.get("columns")
    continuation_columns = continuation.get("columns")
    first_rows = table.get("rows")
    continuation_rows = continuation.get("rows")
    if (
        type(first_columns) is not list
        or type(continuation_columns) is not list
        or len(first_columns) < 2
        or len(first_columns) != len(continuation_columns)
        or type(first_rows) is not list
        or not first_rows
        or type(continuation_rows) is not list
        or not continuation_rows
        or any(
            type(column) is not dict or column.get("value_kind") != "MONEY"
            for column in first_columns
        )
        or any(
            type(column) is not dict
            or column.get("value_kind") != "MONEY"
            or any(
                type(item) is str and item.strip()
                for item in (column.get("header_path_exact") or [])
            )
            for column in continuation_columns
        )
    ):
        return projected, None
    # A visible configured sibling heading immediately after the anonymous
    # continuation authenticates its right boundary.
    if not any(
        _structural_reset_heading_hits(
            later_section,
            (later_section.get("tables") or [{}])[0],
            compiled_specs=compiled_specs,
        )
        for later_section in next_sections[1:]
        if type(later_section) is dict
    ):
        return projected, None

    merged = canonical_clone_v1(table)
    merged_rows = []
    for source_page_id, source_section_id, source_table_id, source_rows in (
        (
            region["page_json_version_id"],
            region["section_id"],
            region["table_id"],
            first_rows,
        ),
        (next_page_id, "s1", "t1", continuation_rows),
    ):
        for source_ordinal, row in enumerate(source_rows, start=1):
            if type(row) is not dict:
                return canonical_clone_v1(table), None
            clone = canonical_clone_v1(row)
            clone["__source_page_json_version_id"] = source_page_id
            clone["__source_section_id"] = source_section_id
            clone["__source_table_id"] = source_table_id
            clone["__source_row_id"] = f"r{source_ordinal}"
            clone["__source_ordinal"] = source_ordinal
            merged_rows.append(clone)
    merged["rows"] = merged_rows
    endpoint_projection, endpoint_receipt = _project_endpoint_first_table(
        merged, compiled_specs=compiled_specs
    )
    if endpoint_receipt is None:
        return canonical_clone_v1(table), None
    # Prove that the joined topology, rather than only either fragment, is the
    # exact six-row endpoint presentation.
    if len(endpoint_projection.get("rows", [])) != 6:
        return canonical_clone_v1(table), None
    receipt_material = {
        "base_first_table_sha256": canonical_json_sha256_v1(table),
        "base_second_table_sha256": canonical_json_sha256_v1(continuation),
        "first_page_json_version_id": region["page_json_version_id"],
        "first_physical_page": region["physical_page"],
        "merged_table_sha256": canonical_json_sha256_v1(merged),
        "policy": policy,
        "second_page_json_version_id": next_page_id,
        "second_physical_page": region["physical_page"] + 1,
        "status": "EXACT_ADJACENT_PAGE_ENDPOINT_FIRST_TOPOLOGY",
    }
    receipt = {
        **receipt_material,
        "receipt_id": "faapefcv1:receipt:"
        + canonical_json_sha256_v1(receipt_material),
    }
    merged["__adjacent_page_endpoint_first_continuation_receipt"] = receipt
    return merged, receipt


def _summary_control_signature(
    item: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Project one carrying control onto the same typed two-role axis."""

    classification = item["classification"]
    table = item["source_table"]
    unit_axis = _unit_axis(table, compiled_specs=compiled_specs)
    reasons = list(unit_axis["reasons"])
    if not unit_axis["complete"]:
        reasons.append("SUMMARY_CONTROL_COMPARISON_UNIT_IS_NOT_COMPLETE")
    columns = table.get("columns")
    rows = table.get("rows")
    money_ordinals = classification["money_column_ordinals"]
    observations = []
    if type(columns) is not list or type(rows) is not list:
        reasons.append("SUMMARY_CONTROL_COMPARISON_SOURCE_AXES_INVALID")
    else:
        control_ordinal = classification["control_row_ordinal"]
        control_row = rows[control_ordinal - 1]
        values = control_row.get("values_exact") if type(control_row) is dict else None
        if type(values) is not list or len(values) != len(columns):
            reasons.append("SUMMARY_CONTROL_COMPARISON_CELL_AXIS_INVALID")
        else:
            summary_policy = compiled_specs["evaluation"]["component_policy"][
                "summary_control"
            ]
            relative_bindings = classification["period_receipt"].get(
                "column_period_bindings"
            )
            relative_axis = relative_bindings is not None
            role_by_ordinal = {}
            period_date_by_ordinal = {}
            source_kind_by_ordinal = {}
            period_axis_valid = True
            if relative_axis:
                expected_fields = {
                    "column_header_exact",
                    "column_ordinal",
                    "period_date",
                    "period_role",
                    "source_kind",
                }
                if (
                    type(relative_bindings) is not list
                    or len(relative_bindings) != 2
                    or any(
                        type(binding) is not dict
                        or set(binding) != expected_fields
                        or type(binding["column_ordinal"]) is not int
                        or not (0 < binding["column_ordinal"] <= len(columns))
                        or type(binding["column_header_exact"]) is not str
                        or type(binding["period_role"]) is not str
                        or binding["period_date"] is not None
                        and type(binding["period_date"]) is not str
                        or binding["source_kind"]
                        != "TYPED_BALANCE_SHEET_RELATIVE_PERIOD_COLUMN"
                        for binding in relative_bindings
                    )
                ):
                    period_axis_valid = False
                else:
                    role_by_ordinal = {
                        binding["column_ordinal"]: binding["period_role"]
                        for binding in relative_bindings
                    }
                    period_date_by_ordinal = {
                        binding["column_ordinal"]: binding["period_date"]
                        for binding in relative_bindings
                    }
                    source_kind_by_ordinal = {
                        binding["column_ordinal"]: binding["source_kind"]
                        for binding in relative_bindings
                    }
                    binding_by_role = {
                        binding["period_role"]: binding for binding in relative_bindings
                    }
                    period_axis_valid = (
                        set(role_by_ordinal) == set(money_ordinals)
                        and set(role_by_ordinal.values())
                        == {summary_policy["opening_role"], summary_policy["current_role"]}
                        and all(
                            binding["column_header_exact"]
                            == _header_text(columns[binding["column_ordinal"] - 1])
                            for binding in relative_bindings
                        )
                        and binding_by_role[summary_policy["current_role"]]["period_date"]
                        == classification["period_end_date"]
                        and binding_by_role[summary_policy["opening_role"]]["period_date"]
                        is None
                    )
                if not period_axis_valid:
                    reasons.append(
                        "SUMMARY_CONTROL_COMPARISON_RELATIVE_PERIOD_AXIS_INVALID"
                    )
            else:
                dates = {
                    ordinal: sorted(
                        set(_surface_dates(_header_text(columns[ordinal - 1])))
                    )
                    for ordinal in money_ordinals
                }
                if any(len(axis) != 1 for axis in dates.values()):
                    period_axis_valid = False
                    reasons.append("SUMMARY_CONTROL_COMPARISON_PERIOD_AXIS_INVALID")
                else:
                    current_date = date.fromisoformat(classification["period_end_date"])
                    role_by_ordinal = {
                        ordinal: (
                            summary_policy["current_role"]
                            if axis[0] == current_date
                            else summary_policy["opening_role"]
                        )
                        for ordinal, axis in dates.items()
                    }
                    period_date_by_ordinal = {
                        ordinal: axis[0].isoformat() for ordinal, axis in dates.items()
                    }
            if period_axis_valid:
                if len(set(role_by_ordinal.values())) != 2:
                    reasons.append("SUMMARY_CONTROL_COMPARISON_ROLE_AXIS_INVALID")
                else:
                    for ordinal, role in role_by_ordinal.items():
                        try:
                            cell = _money(
                                values[ordinal - 1],
                                source_locator={
                                    "column_id": f"c{ordinal}",
                                    "page_json_version_id": item["record"]["page_json_version_id"],
                                    "row_id": f"r{control_ordinal}",
                                    "section_id": item["section_id"],
                                    "table_id": item["table_id"],
                                },
                            )
                        except GeminiJsonFixedAssetRollforwardFamilyV1Error:
                            reasons.append("SUMMARY_CONTROL_COMPARISON_CELL_INVALID:" + role)
                            continue
                        if cell["state"] == "BLANK":
                            reasons.append("SUMMARY_CONTROL_COMPARISON_CELL_IS_BLANK:" + role)
                            continue
                        observation = {
                            "cell": cell,
                            "column_period_date": period_date_by_ordinal[ordinal],
                            "role": role,
                        }
                        if relative_axis:
                            observation["column_period_source_kind"] = source_kind_by_ordinal[
                                ordinal
                            ]
                        observations.append(observation)
    return {
        "bound_unit": unit_axis["canonical_unit"],
        "component_kind": classification["component_kind"],
        "observations": observations,
        "page_json_version_id": item["record"]["page_json_version_id"],
        "physical_page": item["record"]["physical_page"],
        "reasons": sorted(set(reasons)),
        "section_id": item["section_id"],
        "status": "COMPLETE" if not reasons and len(observations) == 2 else "UNRESOLVED",
        "table_id": item["table_id"],
    }


def _coalesce_component_fixed_asset_document_v1(
    *, pages: Sequence[Mapping[str, Any]], compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Select one current same-period component population plus typed controls."""

    reporting_date_receipt = _document_reporting_date_receipt(pages)
    inventory = []
    family_tables = []
    for record in pages:
        for section_ordinal, section in enumerate(record["page_json"]["sections"], start=1):
            if type(section) is not dict or type(section.get("tables")) is not list:
                continue
            for table_ordinal, table in enumerate(section["tables"], start=1):
                if type(table) is not dict:
                    continue
                classification, projected_table, endpoint_receipts = (
                    _component_table_classification(section, table, compiled_specs=compiled_specs)
                )
                reset_hits = _structural_reset_heading_hits(
                    section, table, compiled_specs=compiled_specs
                )
                if classification["family_signal"] and reset_hits:
                    classification = {
                        **classification,
                        "complete": False,
                        "reasons": sorted(
                            {
                                *classification["reasons"],
                                "STRUCTURAL_RESET_HEADING_INSIDE_COMPONENT_OWNER_SCOPE",
                            }
                        ),
                        "structural_reset_heading_hits": reset_hits,
                    }
                if not classification["family_signal"]:
                    continue
                family_tables.append(
                    {
                        "classification": classification,
                        "combined_endpoint_receipts": endpoint_receipts,
                        "position": [
                            record["selected_page_ordinal"],
                            section_ordinal,
                            table_ordinal,
                        ],
                        "record": record,
                        "section": section,
                        "section_id": f"s{section_ordinal}",
                        "source_table": table,
                        "table": projected_table,
                        "table_id": f"t{table_ordinal}",
                    }
                )
    reasons = []
    unresolved_controls = [
        item
        for item in family_tables
        if not item["classification"]["complete"]
        and item["classification"]["component_kind"] == "UNRESOLVED_CARRYING_SUMMARY_CONTROL"
    ]
    invalid = [
        item
        for item in family_tables
        if not item["classification"]["complete"]
        and item["classification"]["component_kind"] != "UNRESOLVED_CARRYING_SUMMARY_CONTROL"
    ]
    reasons.extend(reason for item in invalid for reason in item["classification"]["reasons"])
    if invalid:
        reasons.append("FAMILY_SIGNAL_TABLE_IS_NOT_A_SUPPORTED_FIXED_ASSET_COMPONENT")
    core = [
        item
        for item in family_tables
        if item["classification"]["complete"]
        and item["classification"]["component_kind"]
        not in {"CARRYING_SUMMARY_CONTROL", "PRIMARY_STATEMENT_CARRYING_CONTROL"}
    ]
    summaries = [
        item
        for item in family_tables
        if item["classification"]["complete"]
        and item["classification"]["component_kind"]
        in {"CARRYING_SUMMARY_CONTROL", "PRIMARY_STATEMENT_CARRYING_CONTROL"}
    ]
    if core and unresolved_controls:
        reasons.extend(
            reason for item in unresolved_controls for reason in item["classification"]["reasons"]
        )
        reasons.append("CARRYING_SUMMARY_CONTROL_POPULATION_IS_UNRESOLVED")
    selected = []
    controls = []
    if core and not reasons:
        period_dates = [item["classification"]["period_end_date"] for item in core]
        if not any(value is None for value in period_dates):
            latest = max(period_dates)
            selected = [
                item for item in core if item["classification"]["period_end_date"] == latest
            ]
            controls = [item for item in core if item not in selected]
            # Two ordered roll-forward tables can sit under one current-period
            # section narrative even though the later table is the comparative
            # control.  A section date is context, not a table-local period
            # declaration.  Select a current table only when all complete
            # branch endpoints prove one exact prior-close -> current-open
            # relation; coincidental or partial component populations remain
            # unresolved.
            if len(selected) > 1 and all(
                item["classification"]["component_kind"] == "COMPLETE_ROLLFORWARD_TABLE"
                and item["classification"]["period_receipt"]["status"]
                == "UNIQUE_SECTION_CONTEXT_PERIOD_END_DATE"
                for item in selected
            ):
                current_candidates = [
                    item
                    for item in selected
                    if _continuity_selects_current(
                        item,
                        [other for other in selected if other is not item],
                        compiled_specs=compiled_specs,
                    )
                ]
                if len(current_candidates) == 1:
                    controls = [
                        *controls,
                        *[item for item in selected if item is not current_candidates[0]],
                    ]
                    selected = current_candidates
                else:
                    reasons.append(
                        "SAME_CONTEXT_COMPLETE_TABLES_REQUIRE_UNIQUE_ENDPOINT_CONTINUITY"
                    )
        elif len(core) == 1:
            selected = core
        else:
            current_candidates = [
                item
                for item in core
                if item["classification"]["component_kind"] == "COMPLETE_ROLLFORWARD_TABLE"
                and _continuity_selects_current(
                    item,
                    [other for other in core if other is not item],
                    compiled_specs=compiled_specs,
                )
            ]
            if len(current_candidates) == 1:
                selected = current_candidates
                controls = [item for item in core if item not in selected]
            else:
                reasons.append(
                    "MULTIPLE_COMPONENT_TABLES_REQUIRE_UNIQUE_PERIOD_OR_ENDPOINT_CONTINUITY"
                )
    # A balance-sheet/note carrying-value summary alone is only a control.  It
    # is common in documents with no movement schedule and must not create a
    # false family U without at least one roll-forward component.
    if selected and any(
        item["classification"]["component_kind"] != "COMPLETE_ROLLFORWARD_TABLE"
        for item in controls
    ):
        reasons.append("COMPARATIVE_FRAGMENT_POPULATION_IS_NOT_SUPPORTED")
    effective_period = None
    if selected and not reasons:
        local_periods = {
            item["classification"]["period_end_date"]
            for item in selected
            if item["classification"]["period_end_date"] is not None
        }
        if len(local_periods) > 1:
            reasons.append("CURRENT_COMPONENT_PERIOD_AXIS_CONFLICTS")
        else:
            effective_period = (
                next(iter(local_periods))
                if local_periods
                else reporting_date_receipt["current_date"]
            )
            if effective_period is None:
                reasons.append("CURRENT_FIXED_ASSET_PERIOD_END_DATE_NOT_AUTHENTICATED")
    selected_summary = []
    summary_control_comparison_receipt = {
        "controls": [],
        "status": "NO_SAME_PERIOD_CROSS_CONTROL_COMPARISON_REQUIRED",
    }
    component_population_bindings = []
    component_population_status = "NO_SELECTED_COMPONENT_POPULATION"
    if effective_period is not None and not reasons:
        same_period_summaries = [
            item
            for item in summaries
            if item["classification"]["period_end_date"] == effective_period
        ]
        note_summaries = [
            item
            for item in same_period_summaries
            if item["classification"]["component_kind"] == "CARRYING_SUMMARY_CONTROL"
        ]
        statement_summaries = [
            item
            for item in same_period_summaries
            if item["classification"]["component_kind"] == "PRIMARY_STATEMENT_CARRYING_CONTROL"
        ]
        selected_summary = note_summaries or statement_summaries
        if len(selected_summary) > 1:
            reasons.append("CURRENT_CARRYING_SUMMARY_CONTROL_IS_NOT_UNIQUE")
        elif summaries and len(selected_summary) != 1:
            reasons.append("CARRYING_SUMMARY_CONTROL_PERIOD_DOES_NOT_BIND_CURRENT_COMPONENTS")
        elif len(note_summaries) == 1 and statement_summaries:
            signatures = [
                _summary_control_signature(item, compiled_specs=compiled_specs)
                for item in [note_summaries[0], *statement_summaries]
            ]
            reasons.extend(reason for item in signatures for reason in item["reasons"])
            vectors = {
                (
                    item["bound_unit"],
                    tuple(
                        sorted(
                            (observation["role"], observation["cell"]["coefficient"])
                            for observation in item["observations"]
                        )
                    ),
                )
                for item in signatures
                if item["status"] == "COMPLETE"
            }
            exact = len(vectors) == 1 and all(item["status"] == "COMPLETE" for item in signatures)
            summary_control_comparison_receipt = {
                "controls": signatures,
                "status": "EXACT" if exact else "MISMATCH_OR_INCOMPLETE",
            }
            if not exact:
                reasons.append("SAME_PERIOD_CARRYING_SUMMARY_CONTROLS_MISMATCH")
        branch_roles = {
            role for item in selected for role in item["classification"]["branch_roles"]
        }
        if len(selected) > 1:
            containers = {
                (item["record"]["page_json_version_id"], item["section_id"]) for item in selected
            }
            table_ordinals = sorted(item["position"][2] for item in selected)
            if len(containers) != 1:
                reasons.append("CURRENT_SIBLING_COMPONENTS_CROSS_PAGE_OR_SECTION_BOUNDARY")
            if table_ordinals != list(
                range(table_ordinals[0], table_ordinals[0] + len(table_ordinals))
            ):
                reasons.append("CURRENT_SIBLING_COMPONENT_TABLE_INTERVAL_IS_NOT_CONTIGUOUS")
            aliases = compiled_specs["evaluation"]["component_policy"]["summary_control"][
                "row_aliases"
            ]
            used_aliases = []
            for item in selected:
                title = item["source_table"].get("title_exact")
                matches = [alias for alias in aliases if _contains_alias(title, alias)]
                component_population_bindings.append(
                    {
                        "matched_summary_row_alias": matches[0] if len(matches) == 1 else None,
                        "page_json_version_id": item["record"]["page_json_version_id"],
                        "section_id": item["section_id"],
                        "table_id": item["table_id"],
                        "title_exact": title,
                    }
                )
                if len(matches) != 1:
                    reasons.append("SIBLING_COMPONENT_TITLE_DOES_NOT_BIND_ONE_SUMMARY_POPULATION")
                else:
                    used_aliases.append(matches[0])
            if len(used_aliases) != len(set(used_aliases)):
                reasons.append("SIBLING_COMPONENT_SUMMARY_POPULATION_IS_DUPLICATE")
            if (
                len(selected_summary) == 1
                and selected_summary[0]["classification"]["component_kind"]
                == "CARRYING_SUMMARY_CONTROL"
            ):
                declared_aliases = {
                    item["matched_summary_row_alias"]
                    for item in selected_summary[0]["classification"][
                        "declared_summary_row_bindings"
                    ]
                }
                if set(used_aliases) != declared_aliases:
                    reasons.append("SIBLING_COMPONENT_TO_SUMMARY_POPULATION_EXACT_SET_MISMATCH")
            component_population_status = (
                "EXACT_CONTIGUOUS_SIBLING_COMPONENT_TO_SUMMARY_POPULATION_BINDING"
                if not any(
                    reason.startswith("CURRENT_SIBLING_COMPONENT")
                    or reason.startswith("SIBLING_COMPONENT")
                    for reason in reasons
                )
                else "UNRESOLVED_SIBLING_COMPONENT_POPULATION"
            )
        elif len(selected) == 1:
            component_population_status = "SINGLE_CURRENT_COMPONENT_NO_SIBLING_BINDING_REQUIRED"
        if selected_summary:
            summary_roles = {
                compiled_specs["evaluation"]["component_policy"]["summary_control"]["opening_role"],
                compiled_specs["evaluation"]["component_policy"]["summary_control"]["current_role"],
            }
            summary_branch = next(
                item["branch_role"]
                for item in compiled_specs["evaluation"]["branch_layouts"]
                if {item["opening_role"], item["ending_role"]} == summary_roles
            )
            branch_roles.add(summary_branch)
        optional_absent = set(
            compiled_specs["evaluation"]["component_policy"]["optional_absent_branch_roles"]
        )
        carrying_control_roles = {
            item["branch_role"]
            for item in compiled_specs["evaluation"]["branch_layouts"]
            if item["rollforward_kind"] == "COST_AND_DEPRECIATION_CONTROL"
        }
        embedded_carrying_control = bool(carrying_control_roles & branch_roles)
        if (
            len(selected) > 1
            or (optional_absent - branch_roles and not embedded_carrying_control)
        ) and not selected_summary:
            reasons.append("COMPONENT_AGGREGATION_REQUIRES_CARRYING_SUMMARY_CONTROL")
    control_period_bindings = []
    if selected and effective_period is not None and not reasons:
        for item in controls:
            control_period = item["classification"]["period_end_date"]
            control_period_status = item["classification"]["period_receipt"]["status"]
            if control_period is not None and (
                control_period_status == "UNIQUE_SOURCE_VISIBLE_PERIOD_END_DATE"
                or control_period < effective_period
            ):
                control_period_bindings.append(
                    (control_period, "LOCAL_EXPLICIT_COMPARATIVE_CONTROL_DATE")
                )
            elif (
                len(selected) == 1
                and reporting_date_receipt["comparative_date"] is not None
                and _continuity_selects_current(selected[0], [item], compiled_specs=compiled_specs)
            ):
                control_period_bindings.append(
                    (
                        reporting_date_receipt["comparative_date"],
                        "TYPED_DOCUMENT_COMPARATIVE_DATE_WITH_ENDPOINT_CONTINUITY",
                    )
                )
            else:
                reasons.append("COMPARATIVE_CONTROL_PERIOD_END_DATE_NOT_AUTHENTICATED")
    current_items = sorted([*selected, *selected_summary], key=lambda item: item["position"])
    current_regions = []
    if current_items and effective_period is not None and not reasons:
        for ordinal, item in enumerate(current_items, start=1):
            current_regions.append(
                _region(
                    item,
                    component_role="CURRENT_TABLE",
                    fragment_ordinal=ordinal,
                    period_end_date=effective_period,
                    period_selection_kind=(
                        "LOCAL_EXPLICIT_END_DATE"
                        if item["classification"]["period_end_date"] is not None
                        else "UNIQUE_TYPED_DOCUMENT_REPORTING_DATE"
                    ),
                )
            )
    control_regions = (
        [
            _region(
                item,
                component_role="COMPARATIVE_CONTROL_TABLE",
                fragment_ordinal=ordinal,
                period_end_date=control_period_bindings[ordinal - 1][0],
                period_selection_kind=control_period_bindings[ordinal - 1][1],
            )
            for ordinal, item in enumerate(controls, start=1)
        ]
        if not reasons
        else []
    )
    for item in family_tables:
        if item in current_items:
            disposition = "SELECTED_CURRENT_COMPONENT_TABLE"
        elif item in controls:
            disposition = "TYPED_COMPARATIVE_CONTROL_TABLE"
        elif item["classification"]["complete"]:
            disposition = "UNSELECTED_COMPLETE_FAMILY_COMPONENT"
        else:
            disposition = "UNRESOLVED_FAMILY_SIGNAL_TABLE"
        inventory.append(
            {
                "classification": canonical_clone_v1(item["classification"]),
                "combined_endpoint_receipts": canonical_clone_v1(
                    item["combined_endpoint_receipts"]
                ),
                "disposition": disposition,
                "page_json_version_id": item["record"]["page_json_version_id"],
                "physical_page": item["record"]["physical_page"],
                "position": item["position"],
                "section_id": item["section_id"],
                "table_id": item["table_id"],
            }
        )
    material = {
        "component_population_receipt": {
            "bindings": component_population_bindings,
            "status": component_population_status,
        },
        "component_regions": current_regions,
        "control_regions": control_regions,
        "document_id": pages[0]["document_id"],
        "document_ordinal": pages[0]["document_ordinal"],
        "family_table_inventory": inventory,
        "document_reporting_date_receipt": reporting_date_receipt,
        "reasons": sorted(set(reasons)),
        "source_logical_name": pages[0]["source_logical_name"],
        "source_sha256": pages[0]["source_sha256"],
        "summary_control_comparison_receipt": summary_control_comparison_receipt,
        "status": (
            READY
            if current_regions and not reasons
            else (
                NOT_OBSERVED
                if not family_tables
                or ((summaries or unresolved_controls) and not core and not invalid)
                else UNRESOLVED
            )
        ),
    }
    return {
        **material,
        "cluster_id": "gjffarfcv1:cluster:" + canonical_json_sha256_v1(material),
    }


def coalesce_gemini_json_fixed_asset_rollforward_document_v1(
    *, page_records: Any, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Inventory all family signals and select one current table by source period."""

    pages = _page_record_axis(page_records)
    base_page_json_by_version = {
        record["page_json_version_id"]: record["page_json"] for record in pages
    }
    effective_page_json_by_version, source_repair_overlay_receipts = (
        _apply_authenticated_source_repair_artifact_v1(
            page_json_by_version=base_page_json_by_version,
            compiled_specs=compiled_specs,
            page_records=pages,
        )
    )
    pages = [
        {
            **record,
            "page_json": effective_page_json_by_version[record["page_json_version_id"]],
        }
        for record in pages
    ]
    if compiled_specs["evaluation"].get("component_policy") is not None:
        result = _coalesce_component_fixed_asset_document_v1(
            pages=pages, compiled_specs=compiled_specs
        )
        if not source_repair_overlay_receipts:
            return result
        material = {
            key: value for key, value in result.items() if key != "cluster_id"
        }
        material["source_repair_overlay_receipts"] = source_repair_overlay_receipts
        return {
            **material,
            "cluster_id": "gjffarfcv1:cluster:" + canonical_json_sha256_v1(material),
        }
    reporting_date_receipt = _document_reporting_date_receipt(pages)
    page_json_by_version = {
        record["page_json_version_id"]: record["page_json"] for record in pages
    }
    inventory = []
    family_tables = []
    for record_index, record in enumerate(pages):
        sections = record["page_json"]["sections"]
        for section_ordinal, section in enumerate(sections, start=1):
            if type(section) is not dict:
                continue
            tables = section.get("tables")
            if type(tables) is not list:
                continue
            for table_ordinal, table in enumerate(tables, start=1):
                if type(table) is not dict:
                    continue
                projected_table, adjacent_page_endpoint_first_receipt = (
                    _project_adjacent_page_endpoint_first_continuation_from_page_map(
                        table,
                        section=section,
                        region={
                            **record,
                            "section_id": f"s{section_ordinal}",
                            "table_id": f"t{table_ordinal}",
                        },
                        page_json_by_version=page_json_by_version,
                        compiled_specs=compiled_specs,
                    )
                )
                trailing_owner_receipt = None
                if (
                    record_index > 0
                    and section_ordinal == 1
                    and table_ordinal == 1
                    and record["selected_page_ordinal"]
                    == pages[record_index - 1]["selected_page_ordinal"] + 1
                    and record["physical_page"]
                    == pages[record_index - 1]["physical_page"] + 1
                ):
                    trailing_owner_receipt = _trailing_owner_heading_receipt(
                        pages[record_index - 1]["page_json"],
                        section,
                        table,
                        owner_page_json_version_id=pages[record_index - 1][
                            "page_json_version_id"
                        ],
                        owner_physical_page=pages[record_index - 1]["physical_page"],
                        compiled_specs=compiled_specs,
                    )
                    if trailing_owner_receipt is not None:
                        projected_table = canonical_clone_v1(table)
                        projected_table["__adjacent_owner_continuation_receipt"] = (
                            trailing_owner_receipt
                        )
                projected_table, immediately_preceding_table_period_receipt = (
                    _project_immediately_preceding_table_period(
                        projected_table,
                        section=section,
                        page_json=record["page_json"],
                        page_json_version_id=record["page_json_version_id"],
                        physical_page=record["physical_page"],
                        section_ordinal=section_ordinal,
                        table_ordinal=table_ordinal,
                        compiled_specs=compiled_specs,
                    )
                )
                classification = classify_gemini_json_fixed_asset_rollforward_table_v1(
                    section, projected_table, compiled_specs=compiled_specs
                )
                if trailing_owner_receipt is not None:
                    classification = {
                        **classification,
                        "trailing_owner_heading_receipt": trailing_owner_receipt,
                    }
                if adjacent_page_endpoint_first_receipt is not None:
                    classification = {
                        **classification,
                        "adjacent_page_endpoint_first_continuation_receipt": (
                            adjacent_page_endpoint_first_receipt
                        ),
                    }
                if immediately_preceding_table_period_receipt is not None:
                    classification = {
                        **classification,
                        "immediately_preceding_table_period_receipt": (
                            immediately_preceding_table_period_receipt
                        ),
                    }
                if not classification["family_signal"]:
                    continue
                item = {
                    "classification": classification,
                    "position": [record["selected_page_ordinal"], section_ordinal, table_ordinal],
                    "record": record,
                    "section": section,
                    "section_id": f"s{section_ordinal}",
                    "table": projected_table,
                    "table_id": f"t{table_ordinal}",
                }
                family_tables.append(item)
    family_tables = _bind_adjacent_owner_continuations(
        family_tables, compiled_specs=compiled_specs
    )
    complete = [item for item in family_tables if item["classification"]["complete"]]
    reasons = []
    current = None
    controls = []
    source_only_undated = []
    if family_tables and len(complete) != len(family_tables):
        reasons.extend(
            reason
            for item in family_tables
            if not item["classification"]["complete"]
            for reason in item["classification"]["reasons"]
        )
        reasons.append("FAMILY_SIGNAL_TABLE_IS_NOT_A_COMPLETE_FIXED_ASSET_PRESENTATION")
    elif len(complete) == 1:
        current = complete[0]
    elif len(complete) > 1:
        period_dates = [item["classification"]["period_end_date"] for item in complete]
        local_periods = all(
            item["classification"]["period_receipt"]["status"]
            == "UNIQUE_SOURCE_VISIBLE_PERIOD_END_DATE"
            for item in complete
        )
        if not any(value is None for value in period_dates) and (
            len(set(period_dates)) > 1 or local_periods
        ):
            latest = max(period_dates)
            selected = [
                item for item in complete if item["classification"]["period_end_date"] == latest
            ]
            if len(selected) != 1:
                reasons.append("CURRENT_FIXED_ASSET_TABLE_IS_NOT_UNIQUE")
            else:
                current = selected[0]
                controls = [item for item in complete if item is not current]
        else:
            document_date = reporting_date_receipt["current_date"]
            missing = [
                item for item in complete if item["classification"]["period_end_date"] is None
            ]
            known = [
                item for item in complete if item["classification"]["period_end_date"] is not None
            ]
            exact_document_current = [
                item
                for item in known
                if item["classification"]["period_end_date"] == document_date
            ]
            if (
                document_date is not None
                and not known
                and _leading_undated_owner_sequence(
                    complete, compiled_specs=compiled_specs
                )
            ):
                selected = [complete[0]]
                source_only_undated = list(complete[1:])
            elif (
                compiled_specs["evaluation"].get("undated_sibling_policy")
                == "UNIQUE_EXACT_DOCUMENT_CURRENT_DATE_DOMINATES_UNDATED_COMPLETE_SIBLINGS_AS_SOURCE_ONLY"
                and document_date is not None
                and missing
                and len(exact_document_current) == 1
                and (
                    all(
                        any(
                            _source_only_surface_matches(
                                surface, compiled_specs=compiled_specs
                            )
                            for surface in item["section"].get("narratives_exact", [])
                        )
                        for item in missing
                    )
                    or _adjacent_undated_owner_continuation_siblings(
                        exact_document_current[0],
                        missing,
                        compiled_specs=compiled_specs,
                    )
                )
            ):
                selected = exact_document_current
                source_only_undated = list(missing)
            elif (
                document_date is not None
                and len(missing) == 1
                and known
                and all(item["classification"]["period_end_date"] < document_date for item in known)
            ):
                selected = missing
            else:
                selected = [
                    item
                    for item in complete
                    if _continuity_selects_current(
                        item,
                        [other for other in complete if other is not item],
                        compiled_specs=compiled_specs,
                    )
                ]
            if len(selected) != 1:
                reasons.append(
                    "MULTIPLE_FAMILY_TABLES_REQUIRE_UNIQUE_PERIOD_OR_ENDPOINT_CONTINUITY"
                )
            else:
                current = selected[0]
                controls = [
                    item
                    for item in complete
                    if item is not current and item not in source_only_undated
                ]
    control_period_bindings = []
    if current is not None and not reasons:
        local_period = current["classification"]["period_end_date"]
        effective_period = local_period or reporting_date_receipt["current_date"]
        if effective_period is None:
            reasons.append("CURRENT_FIXED_ASSET_PERIOD_END_DATE_NOT_AUTHENTICATED")
        for item in controls:
            control_period = item["classification"]["period_end_date"]
            if control_period is not None:
                control_period_bindings.append(
                    (control_period, "LOCAL_EXPLICIT_COMPARATIVE_CONTROL_DATE")
                )
            elif reporting_date_receipt["comparative_date"] is not None and (
                _continuity_selects_current(current, [item], compiled_specs=compiled_specs)
            ):
                control_period_bindings.append(
                    (
                        reporting_date_receipt["comparative_date"],
                        "TYPED_DOCUMENT_COMPARATIVE_DATE_WITH_ENDPOINT_CONTINUITY",
                    )
                )
            else:
                reasons.append("COMPARATIVE_CONTROL_PERIOD_END_DATE_NOT_AUTHENTICATED")
    if current is not None and not reasons:
        local_period = current["classification"]["period_end_date"]
        effective_period = local_period or reporting_date_receipt["current_date"]
        current_period_status = current["classification"]["period_receipt"]["status"]
        current_region = _region(
            current,
            component_role="CURRENT_TABLE",
            fragment_ordinal=1,
            period_end_date=effective_period,
            period_selection_kind=(
                "IMMEDIATELY_PRECEDING_TABLE_EXPLICIT_AS_AT_DATE"
                if current_period_status
                == "UNIQUE_IMMEDIATELY_PRECEDING_TABLE_PERIOD_END_DATE"
                else "LOCAL_EXPLICIT_END_DATE"
                if local_period is not None
                else "UNIQUE_TYPED_DOCUMENT_REPORTING_DATE"
            ),
        )
        control_regions = [
            _region(
                item,
                component_role="COMPARATIVE_CONTROL_TABLE",
                fragment_ordinal=index,
                period_end_date=control_period_bindings[index - 1][0],
                period_selection_kind=control_period_bindings[index - 1][1],
            )
            for index, item in enumerate(controls, start=1)
        ]
    else:
        current_region = None
        control_regions = []
    for item in family_tables:
        if item is current:
            disposition = "SELECTED_UNIQUE_CURRENT_TABLE"
        elif item in controls:
            disposition = "TYPED_COMPARATIVE_CONTROL_TABLE"
        elif item in source_only_undated:
            disposition = "SOURCE_ONLY_UNDATED_NONCURRENT_TABLE"
        elif item["classification"]["complete"]:
            disposition = "UNSELECTED_COMPLETE_FAMILY_TABLE"
        else:
            disposition = "UNRESOLVED_FAMILY_SIGNAL_TABLE"
        inventory.append(
            {
                "classification": canonical_clone_v1(item["classification"]),
                "disposition": disposition,
                "page_json_version_id": item["record"]["page_json_version_id"],
                "physical_page": item["record"]["physical_page"],
                "position": item["position"],
                "section_id": item["section_id"],
                "table_id": item["table_id"],
            }
        )
    material = {
        "component_regions": [current_region] if current_region is not None else [],
        "control_regions": control_regions,
        "document_id": pages[0]["document_id"],
        "document_ordinal": pages[0]["document_ordinal"],
        "family_table_inventory": inventory,
        "document_reporting_date_receipt": reporting_date_receipt,
        "reasons": sorted(set(reasons)),
        "source_logical_name": pages[0]["source_logical_name"],
        "source_sha256": pages[0]["source_sha256"],
        "status": (
            READY
            if current_region is not None and not reasons
            else (NOT_OBSERVED if not family_tables else UNRESOLVED)
        ),
    }
    if source_repair_overlay_receipts:
        material["source_repair_overlay_receipts"] = source_repair_overlay_receipts
    return {
        **material,
        "cluster_id": "gjffarfcv1:cluster:" + canonical_json_sha256_v1(material),
    }


def _region_axis(regions: Any, *, component_role: str, maximum: int) -> list[dict[str, Any]]:
    fields = {
        "component_role",
        "document_id",
        "document_ordinal",
        "fragment_ordinal",
        "page_json_version_id",
        "period_end_date",
        "period_selection_kind",
        "physical_page",
        "section_id",
        "selected_page_ordinal",
        "source_logical_name",
        "source_sha256",
        "table_id",
    }
    if type(regions) not in {list, tuple} or not 0 <= len(regions) <= maximum:
        raise _error("fixed-asset region axis cardinality is invalid")
    checked = []
    identity = None
    prior = None
    for ordinal, raw in enumerate(regions, start=1):
        period_end_date = raw.get("period_end_date") if type(raw) is dict else None
        period_selection_kind = raw.get("period_selection_kind") if type(raw) is dict else None
        try:
            parsed_period_end = (
                date.fromisoformat(period_end_date) if type(period_end_date) is str else None
            )
        except ValueError:
            parsed_period_end = None
        expected_period_kinds = (
            {
                "IMMEDIATELY_PRECEDING_TABLE_EXPLICIT_AS_AT_DATE",
                "LOCAL_EXPLICIT_END_DATE",
                "UNIQUE_TYPED_DOCUMENT_REPORTING_DATE",
            }
            if component_role == "CURRENT_TABLE"
            else {
                "LOCAL_EXPLICIT_COMPARATIVE_CONTROL_DATE",
                "TYPED_DOCUMENT_COMPARATIVE_DATE_WITH_ENDPOINT_CONTINUITY",
            }
        )
        if (
            type(raw) is not dict
            or set(raw) != fields
            or raw.get("component_role") != component_role
            or raw.get("fragment_ordinal") != ordinal
            or _DOCUMENT_ID.fullmatch(raw.get("document_id", "")) is None
            or type(raw.get("document_ordinal")) is not int
            or raw["document_ordinal"] <= 0
            or _PAGE_VERSION.fullmatch(raw.get("page_json_version_id", "")) is None
            or parsed_period_end is None
            or period_end_date != parsed_period_end.isoformat()
            or period_selection_kind not in expected_period_kinds
            or type(raw.get("physical_page")) is not int
            or raw["physical_page"] <= 0
            or type(raw.get("selected_page_ordinal")) is not int
            or raw["selected_page_ordinal"] <= 0
            or _SECTION_ID.fullmatch(raw.get("section_id", "")) is None
            or _TABLE_ID.fullmatch(raw.get("table_id", "")) is None
            or type(raw.get("source_logical_name")) is not str
            or not raw["source_logical_name"]
            or _SHA256.fullmatch(raw.get("source_sha256", "")) is None
        ):
            raise _error("fixed-asset region is invalid")
        current_identity = tuple(
            raw[key]
            for key in ("document_id", "document_ordinal", "source_logical_name", "source_sha256")
        )
        position = (
            raw["selected_page_ordinal"],
            int(raw["section_id"][1:]),
            int(raw["table_id"][1:]),
        )
        if identity is None:
            identity = current_identity
        elif identity != current_identity:
            raise _error("fixed-asset regions cross document identity")
        if prior is not None and position <= prior:
            raise _error("fixed-asset regions are not in source order")
        prior = position
        checked.append(canonical_clone_v1(raw))
    return checked


def build_gemini_json_fixed_asset_rollforward_region_query_receipt_v1(
    regions: Any, *, control_regions: Any
) -> dict[str, Any]:
    current = _region_axis(regions, component_role="CURRENT_TABLE", maximum=8)
    controls = _region_axis(control_regions, component_role="COMPARATIVE_CONTROL_TABLE", maximum=8)
    if not current:
        raise _error("fixed-asset query receipt needs one current component population")
    if controls and any(
        item["document_id"] != current[0]["document_id"]
        or item["source_sha256"] != current[0]["source_sha256"]
        for item in controls
    ):
        raise _error("fixed-asset control regions cross current document")
    material = (
        {
            "control_region_axis_sha256": canonical_json_sha256_v1(controls),
            "current_region": current[0],
            "document_id": current[0]["document_id"],
            "exact_control_region_count": len(controls),
            "format_version": "GEMINI_JSON_FIXED_ASSET_ROLLFORWARD_REGION_QUERY_RECEIPT_V1",
            "source_logical_name": current[0]["source_logical_name"],
            "source_sha256": current[0]["source_sha256"],
        }
        if len(current) == 1
        else {
            "control_region_axis_sha256": canonical_json_sha256_v1(controls),
            "current_region_axis_sha256": canonical_json_sha256_v1(current),
            "current_regions": current,
            "document_id": current[0]["document_id"],
            "exact_control_region_count": len(controls),
            "exact_current_region_count": len(current),
            "format_version": "GEMINI_JSON_FIXED_ASSET_ROLLFORWARD_REGION_QUERY_RECEIPT_V2",
            "source_logical_name": current[0]["source_logical_name"],
            "source_sha256": current[0]["source_sha256"],
        }
    )
    return {
        **material,
        "query_receipt_id": "gjffarrqrv1:receipt:" + canonical_json_sha256_v1(material),
    }


def _money(value: Any, *, source_locator: Mapping[str, Any]) -> dict[str, Any]:
    if value is None:
        return {
            "coefficient": None,
            "source_locator": canonical_clone_v1(source_locator),
            "source_text": "",
            "state": "BLANK",
        }
    if type(value) is not str:
        raise _error("fixed-asset money source must be exact text or null")
    source_text = value
    text = value.strip()
    if not text or text.casefold() == "null":
        return {
            "coefficient": None,
            "source_locator": canonical_clone_v1(source_locator),
            "source_text": source_text,
            "state": "BLANK",
        }
    if (
        text in _DASHES
        or (
            any(character in _DASHES for character in text)
            and all(character in _DASHES or character.isspace() for character in text)
        )
        or (
            text[0] in _DASHES
            and text[-1] in _DASHES
            and "".join(
                character
                for character in text[1:-1]
                if character not in _DASHES and not character.isspace()
            )
            in _DASH_ANNOTATIONS
        )
    ):
        return {
            "coefficient": 0,
            "source_locator": canonical_clone_v1(source_locator),
            "source_text": source_text,
            "state": "DASH_ZERO",
        }
    suffix = re.fullmatch(r"(.+?)([^\x00-\x7f])", text)
    if suffix is not None and suffix.group(2) in _IGNORABLE_TRAILING_MODEL_GLYPHS:
        text = suffix.group(1).strip()
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1].strip()
    explicit_negative = text.startswith("-")
    if explicit_negative:
        text = text[1:].strip()
    if _GROUPED_INTEGER_WITH_ZERO_DECIMALS.fullmatch(text):
        text = text[:-3]
    elif "." in text and "," in text:
        raise _error("fixed-asset money text is not one exact signed integer")
    digits = re.sub(r"[.,\s]", "", text)
    if not digits.isdigit():
        raise _error("fixed-asset money text is not one exact signed integer")
    coefficient = int(digits)
    if negative or explicit_negative:
        coefficient = -coefficient
    return {
        "coefficient": coefficient,
        "source_locator": canonical_clone_v1(source_locator),
        "source_text": source_text,
        "state": "PRINTED_ZERO" if coefficient == 0 else "NUMBER",
    }


def _unit_axis(table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]) -> dict[str, Any]:
    recognized = list(compiled_specs["unit_binding_by_alias"])
    evidence = []
    conflicting_surfaces = []
    undeclared = []

    def classify(surface: dict[str, Any], *, explicit_slot: bool) -> dict[str, Any] | None:
        folded = _normalized(surface["text_exact"])
        occurrences = [
            (match.start(), match.end(), alias)
            for alias in recognized
            for match in re.finditer(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", folded)
        ]
        maximal = sorted(
            [
                occurrence
                for occurrence in occurrences
                if not any(
                    other[0] <= occurrence[0]
                    and occurrence[1] <= other[1]
                    and other[1] - other[0] > occurrence[1] - occurrence[0]
                    for other in occurrences
                )
            ],
            key=lambda item: (item[0], item[1], item[2]),
        )
        if maximal:
            records = []
            for match_ordinal, (_start, _end, alias) in enumerate(maximal, start=1):
                binding = compiled_specs["unit_binding_by_alias"][alias]
                record = {
                    **surface,
                    "accepted": binding["accepted"],
                    "canonical_unit": binding["canonical_unit"],
                    "match_ordinal": match_ordinal,
                    "matched_alias": alias,
                    "magnitude_power10": binding["magnitude_power10"],
                }
                records.append(record)
                evidence.append(record)
            identities = {
                (record["canonical_unit"], record["magnitude_power10"]) for record in records
            }
            if len(identities) != 1:
                conflicting_surfaces.append(
                    {**surface, "matched_aliases": [record["matched_alias"] for record in records]}
                )
                return None
            return records[0]
        if explicit_slot or re.search(r"\b(?:dong|vnd|trieu|nghin|ty)\b", folded):
            undeclared.append(surface)
        return None

    table_record = None
    unit_exact = table.get("unit_exact")
    if type(unit_exact) is str and unit_exact.strip():
        table_record = classify(
            {"source_kind": "TABLE_UNIT", "text_exact": unit_exact}, explicit_slot=True
        )
    columns = table.get("columns")
    money_records = []
    if type(columns) is list:
        for ordinal, column in enumerate(columns, start=1):
            if type(column) is not dict or column.get("value_kind") != "MONEY":
                continue
            header = _header_text(column)
            money_records.append(
                classify(
                    {"source_kind": f"MONEY_COLUMN_HEADER:c{ordinal}", "text_exact": header},
                    explicit_slot=False,
                )
                if header
                else None
            )
    reasons = []
    if conflicting_surfaces:
        reasons.append("MULTIPLE_CONFLICTING_DECLARED_MONEY_UNITS_ON_ONE_SURFACE")
    if undeclared:
        reasons.append("UNDECLARED_EXPLICIT_MONEY_UNIT")
    if any(item is not None and not item["accepted"] for item in [table_record, *money_records]):
        reasons.append("EXPLICIT_MONEY_UNIT_IS_NOT_ACCEPTED")
    canonical_unit = None
    source = None
    if table_record is not None and table_record["accepted"]:
        canonical_unit = table_record["canonical_unit"]
        source = "LOCAL_TABLE_UNIT"
        if any(
            item is not None and item["canonical_unit"] != canonical_unit for item in money_records
        ):
            reasons.append("CONFLICTING_EXPLICIT_MONEY_UNITS")
    elif money_records:
        if any(item is None or not item["accepted"] for item in money_records):
            reasons.append("MONEY_COLUMN_UNITS_ARE_NOT_UNIFORMLY_EXPLICIT")
        else:
            units = {item["canonical_unit"] for item in money_records if item is not None}
            if len(units) != 1:
                reasons.append("CONFLICTING_EXPLICIT_MONEY_UNITS")
            else:
                canonical_unit = next(iter(units))
                source = "LOCAL_UNIFORM_ALL_MONEY_COLUMN_UNITS"
    return {
        "canonical_unit": canonical_unit,
        "complete": canonical_unit is not None and not reasons,
        "conflicting_surfaces": conflicting_surfaces,
        "evidence": evidence,
        "reasons": sorted(set(reasons)),
        "source": source,
        "undeclared_evidence": undeclared,
    }


def _resolve_missing_local_unit_from_balance_sheet_owner_vector(
    *,
    table: Mapping[str, Any],
    classification: Mapping[str, Any],
    local_unit_axis: Mapping[str, Any],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve only an otherwise absent unit through an exact two-endpoint control.

    The note's carrying opening/ending totals and a typed balance-sheet owner
    row must represent the same two base-currency values under exactly one
    accepted magnitude.  When the configured source-presentation policy is
    active, a coarser local display may also bind when both statement values
    fall independently inside its half-unit rounding intervals.  Duplicate
    statement renderings are allowed only when they identify that same unique
    local unit.  Explicit, conflicting or undeclared local unit evidence is
    never overridden.
    """

    policy = compiled_specs["evaluation"].get("missing_local_unit_policy")
    if policy is None or local_unit_axis["complete"]:
        return canonical_clone_v1(local_unit_axis)
    if (
        local_unit_axis["evidence"]
        or local_unit_axis["conflicting_surfaces"]
        or local_unit_axis["undeclared_evidence"]
        or set(local_unit_axis["reasons"])
        != {"MONEY_COLUMN_UNITS_ARE_NOT_UNIFORMLY_EXPLICIT"}
    ):
        return canonical_clone_v1(local_unit_axis)
    total_ordinals = classification.get("total_column_ordinals")
    if type(total_ordinals) is not list or len(total_ordinals) != 1:
        return canonical_clone_v1(local_unit_axis)
    total_ordinal = total_ordinals[0]
    carrying_layouts = [
        layout
        for layout in compiled_specs["evaluation"]["branch_layouts"]
        if layout["rollforward_kind"] == "COST_AND_DEPRECIATION_CONTROL"
    ]
    if len(carrying_layouts) != 1:
        return canonical_clone_v1(local_unit_axis)
    carrying_layout = carrying_layouts[0]
    endpoint_coefficients: dict[str, list[int]] = defaultdict(list)
    for source_ordinal, row in enumerate(table.get("rows", []), start=1):
        if type(row) is not dict or row.get("row_kind") == "GROUP":
            continue
        if _branch_layout_for_row(row, compiled_specs=compiled_specs) != carrying_layout:
            continue
        role = _role_for_row(row, carrying_layout, compiled_specs=compiled_specs)
        if role not in {carrying_layout["opening_role"], carrying_layout["ending_role"]}:
            continue
        values = row.get("values_exact")
        if type(values) is not list or total_ordinal > len(values):
            return canonical_clone_v1(local_unit_axis)
        try:
            cell = _money(
                values[total_ordinal - 1],
                source_locator={"cross_control_source_row_ordinal": source_ordinal},
            )
        except GeminiJsonFixedAssetRollforwardFamilyV1Error:
            return canonical_clone_v1(local_unit_axis)
        if cell["state"] == "BLANK":
            return canonical_clone_v1(local_unit_axis)
        endpoint_coefficients[role].append(cell["coefficient"])
    endpoint_roles = (carrying_layout["opening_role"], carrying_layout["ending_role"])
    if any(len(endpoint_coefficients[role]) != 1 for role in endpoint_roles):
        return canonical_clone_v1(local_unit_axis)
    local_vector = sorted(endpoint_coefficients[role][0] for role in endpoint_roles)
    accepted_units = {
        (binding["canonical_unit"], binding["magnitude_power10"])
        for binding in compiled_specs["evaluation"]["money_unit_bindings"]
        if binding["accepted"]
    }
    magnitude_by_unit = {
        binding["canonical_unit"]: binding["magnitude_power10"]
        for binding in compiled_specs["evaluation"]["money_unit_bindings"]
    }
    owner_aliases = [
        _normalized(alias) for alias in compiled_specs["topology"]["parent"]["aliases"]
    ]
    hard_negatives = [
        _normalized(alias) for alias in compiled_specs["topology"]["hard_negative_aliases"]
    ]
    matches_by_candidate: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    rounded_matches_by_candidate: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(
        list
    )
    for page_json_version_id, page_json in page_json_by_version.items():
        sections = page_json.get("sections")
        if type(sections) is not list:
            continue
        for section_ordinal, section in enumerate(sections, start=1):
            if (
                type(section) is not dict
                or section.get("content_kind") != "PRIMARY_STATEMENT"
                or section.get("statement_type") != "BALANCE_SHEET"
            ):
                continue
            tables = section.get("tables")
            if type(tables) is not list:
                continue
            for table_ordinal, statement_table in enumerate(tables, start=1):
                if type(statement_table) is not dict:
                    continue
                statement_unit_axis = _unit_axis(
                    statement_table, compiled_specs=compiled_specs
                )
                if not statement_unit_axis["complete"]:
                    continue
                statement_magnitude = magnitude_by_unit.get(
                    statement_unit_axis["canonical_unit"]
                )
                if statement_magnitude is None:
                    continue
                columns = statement_table.get("columns")
                rows = statement_table.get("rows")
                if type(columns) is not list or type(rows) is not list:
                    continue
                money_ordinals = [
                    ordinal
                    for ordinal, column in enumerate(columns, start=1)
                    if type(column) is dict and column.get("value_kind") == "MONEY"
                ]
                for row_ordinal, row in enumerate(rows, start=1):
                    if type(row) is not dict:
                        continue
                    label = row.get("label_exact")
                    if not any(_contains_alias(label, alias) for alias in owner_aliases) or any(
                        _contains_alias(label, alias) for alias in hard_negatives
                    ):
                        continue
                    values = row.get("values_exact")
                    if type(values) is not list or len(values) != len(columns):
                        continue
                    statement_coefficients = []
                    invalid = False
                    for ordinal in money_ordinals:
                        try:
                            cell = _money(
                                values[ordinal - 1],
                                source_locator={
                                    "column_id": f"c{ordinal}",
                                    "page_json_version_id": page_json_version_id,
                                    "row_id": f"r{row_ordinal}",
                                    "section_id": f"s{section_ordinal}",
                                    "table_id": f"t{table_ordinal}",
                                },
                            )
                        except GeminiJsonFixedAssetRollforwardFamilyV1Error:
                            invalid = True
                            break
                        if cell["state"] != "BLANK":
                            statement_coefficients.append(cell["coefficient"])
                    if invalid or len(statement_coefficients) != 2:
                        continue
                    statement_base_vector = sorted(
                        coefficient * 10**statement_magnitude
                        for coefficient in statement_coefficients
                    )
                    for candidate in accepted_units:
                        candidate_unit, candidate_magnitude = candidate
                        candidate_base_vector = [
                            coefficient * 10**candidate_magnitude
                            for coefficient in local_vector
                        ]
                        match = {
                            "candidate_local_unit": candidate_unit,
                            "page_json_version_id": page_json_version_id,
                            "row_id": f"r{row_ordinal}",
                            "section_id": f"s{section_ordinal}",
                            "statement_unit": statement_unit_axis["canonical_unit"],
                            "table_id": f"t{table_ordinal}",
                        }
                        if candidate_base_vector == statement_base_vector:
                            matches_by_candidate[candidate].append(match)
                            continue
                        if (
                            compiled_specs["evaluation"].get(
                                "source_presentation_rounding_policy"
                            )
                            == "INDEPENDENT_DISPLAY_UNIT_ROUNDING_INTERVAL_ALL_EQUATIONS"
                            and candidate_magnitude >= 3
                        ):
                            half_local_display_unit = 10**candidate_magnitude // 2
                            half_statement_display_unit = 10**statement_magnitude // 2
                            independent_interval_tolerance = (
                                half_local_display_unit + half_statement_display_unit
                            )
                            deltas = [
                                statement_value - candidate_value
                                for candidate_value, statement_value in zip(
                                    candidate_base_vector,
                                    statement_base_vector,
                                    strict=True,
                                )
                            ]
                            if all(
                                abs(delta) <= independent_interval_tolerance
                                for delta in deltas
                            ):
                                rounded_matches_by_candidate[candidate].append(
                                    {
                                        **match,
                                        "base_value_deltas": deltas,
                                        "independent_interval_tolerance": (
                                            independent_interval_tolerance
                                        ),
                                        "local_half_display_unit": half_local_display_unit,
                                        "statement_half_display_unit": (
                                            half_statement_display_unit
                                        ),
                                    }
                                )
    selected_matches = matches_by_candidate or rounded_matches_by_candidate
    if len(selected_matches) != 1:
        unresolved = canonical_clone_v1(local_unit_axis)
        unresolved["cross_control_receipt"] = {
            "candidate_unit_count": len(selected_matches),
            "policy": policy,
            "status": "NOT_UNIQUE_OR_NOT_OBSERVED",
        }
        return unresolved
    (canonical_unit, magnitude_power10), matches = next(iter(selected_matches.items()))
    return {
        "canonical_unit": canonical_unit,
        "complete": True,
        "conflicting_surfaces": [],
        "cross_control_receipt": {
            "local_endpoint_coefficients": {
                role: endpoint_coefficients[role][0] for role in endpoint_roles
            },
            "magnitude_power10": magnitude_power10,
            "matches": matches,
            "policy": policy,
            "status": (
                "EXACT_UNIQUE_LOCAL_UNIT"
                if matches_by_candidate
                else "UNIQUE_LOCAL_UNIT_WITHIN_INDEPENDENT_DISPLAY_ROUNDING_INTERVAL"
            ),
        },
        "evidence": [],
        "reasons": [],
        "source": policy,
        "undeclared_evidence": [],
    }


def _dated_money_pairs(value: Any) -> list[tuple[date, str]]:
    folded = _normalized(value)
    if not folded:
        return []
    date_matches = []
    for match in _DATE_DMY.finditer(folded):
        try:
            parsed = date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
        except ValueError:
            continue
        date_matches.append((match.start(), match.end(), parsed))
    money_matches = [
        match
        for match in _GROUPED_MONEY.finditer(folded)
        if not any(start <= match.start() < end for start, end, _parsed in date_matches)
    ]
    result = []
    for index, (_start, end, parsed) in enumerate(date_matches):
        next_start = date_matches[index + 1][0] if index + 1 < len(date_matches) else len(folded)
        candidates = [match for match in money_matches if end <= match.start() < next_start]
        if candidates:
            result.append((parsed, candidates[0].group(0)))
    return result


def _shared_dated_money_token(value: Any, *, current_date: date) -> str | None:
    """Return one value explicitly shared by two dated narrative endpoints."""

    folded = _normalized(value)
    date_matches = []
    for match in _DATE_DMY.finditer(folded):
        try:
            parsed = date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
        except ValueError:
            continue
        date_matches.append((match.start(), match.end(), parsed))
    if (
        len(date_matches) != 2
        or current_date not in {item[2] for item in date_matches}
        or " va " not in folded
    ):
        return None
    money_matches = [
        match
        for match in _GROUPED_MONEY.finditer(folded)
        if not any(start <= match.start() < end for start, end, _parsed in date_matches)
    ]
    if len(money_matches) != 1 or money_matches[0].start() <= max(
        end for _start, end, _parsed in date_matches
    ):
        return None
    return money_matches[0].group(0)


def _surface_unit_bindings(
    value: Any, *, compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    folded = _normalized(value)
    occurrences = [
        (match.start(), match.end(), alias)
        for alias in compiled_specs["unit_binding_by_alias"]
        for match in re.finditer(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", folded)
    ]
    maximal = [
        occurrence
        for occurrence in occurrences
        if not any(
            other[0] <= occurrence[0]
            and occurrence[1] <= other[1]
            and other[1] - other[0] > occurrence[1] - occurrence[0]
            for other in occurrences
        )
    ]
    return [
        canonical_clone_v1(compiled_specs["unit_binding_by_alias"][alias])
        for _start, _end, alias in sorted(maximal)
    ]


def _supplemental_disclosure_projection(
    *,
    page_json_by_version: Mapping[str, dict[str, Any]],
    region: Mapping[str, Any],
    bound_unit: str | None,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    disclosures = compiled_specs["evaluation"]["supplemental_disclosure_roles"]
    if not disclosures:
        return {"mappings": [], "observations": [], "reasons": []}
    current_date = date.fromisoformat(region["period_end_date"])
    observations = []
    reasons = []

    def append_observation(
        *, role: str, source_kind: str, source_locator: Mapping[str, Any], source_text: str
    ) -> None:
        try:
            cell = _money(source_text, source_locator=source_locator)
        except GeminiJsonFixedAssetRollforwardFamilyV1Error:
            reasons.append(f"SUPPLEMENTAL_DISCLOSURE_MONEY_INVALID:{role}")
            return
        if cell["state"] == "BLANK":
            reasons.append(f"SUPPLEMENTAL_DISCLOSURE_CURRENT_VALUE_IS_BLANK:{role}")
            return
        observations.append(
            {
                "bound_unit": bound_unit,
                "cell": cell,
                "role": role,
                "source_kind": source_kind,
                "source_locator": canonical_clone_v1(source_locator),
            }
        )

    for page_json_version_id, page_json in page_json_by_version.items():
        sections = page_json.get("sections")
        if type(sections) is not list:
            continue
        for section_ordinal, section in enumerate(sections, start=1):
            if type(section) is not dict:
                continue
            narratives = section.get("narratives_exact")
            if type(narratives) is list:
                for narrative_ordinal, narrative in enumerate(narratives, start=1):
                    if type(narrative) is not str:
                        continue
                    for disclosure in disclosures:
                        if not _supplemental_surface_matches(narrative, disclosure):
                            continue
                        pairs = [
                            token
                            for parsed, token in _dated_money_pairs(narrative)
                            if parsed == current_date
                        ]
                        source_kind = "DATED_NARRATIVE_CURRENT_VALUE"
                        if not pairs:
                            shared = _shared_dated_money_token(
                                narrative, current_date=current_date
                            )
                            if shared is not None:
                                pairs = [shared]
                                source_kind = "SHARED_DATED_NARRATIVE_CURRENT_VALUE"
                        if len(pairs) != 1:
                            reasons.append(
                                "SUPPLEMENTAL_NARRATIVE_CURRENT_VALUE_NOT_UNIQUE:"
                                + disclosure["role"]
                            )
                            continue
                        unit_bindings = _surface_unit_bindings(
                            narrative, compiled_specs=compiled_specs
                        )
                        unit_identities = {
                            (item["accepted"], item["canonical_unit"]) for item in unit_bindings
                        }
                        if len(unit_identities) != 1 or next(iter(unit_identities)) != (
                            True,
                            bound_unit,
                        ):
                            reasons.append(
                                "SUPPLEMENTAL_NARRATIVE_UNIT_NOT_UNIQUE_OR_CONFLICTING:"
                                + disclosure["role"]
                            )
                            continue
                        append_observation(
                            role=disclosure["role"],
                            source_kind=source_kind,
                            source_locator={
                                "narrative_ordinal": narrative_ordinal,
                                "page_json_version_id": page_json_version_id,
                                "section_id": f"s{section_ordinal}",
                            },
                            source_text=pairs[0],
                        )
            tables = section.get("tables")
            if type(tables) is not list:
                continue
            for table_ordinal, table in enumerate(tables, start=1):
                if type(table) is not dict:
                    continue
                columns = table.get("columns")
                rows = table.get("rows")
                if type(columns) is not list or type(rows) is not list:
                    continue
                money_ordinals = [
                    ordinal
                    for ordinal, column in enumerate(columns, start=1)
                    if type(column) is dict and column.get("value_kind") == "MONEY"
                ]
                table_title = table.get("title_exact")
                for disclosure in disclosures:
                    title_hit = _supplemental_surface_matches(table_title, disclosure)
                    matched_rows = []
                    for row_ordinal, row in enumerate(rows, start=1):
                        if type(row) is not dict or row.get("row_kind") == "GROUP":
                            continue
                        row_hit = _supplemental_row_matches(
                            row,
                            disclosure,
                            table=table,
                            compiled_specs=compiled_specs,
                        )
                        dated_title_row = bool(
                            title_hit and current_date in _surface_dates(row.get("label_exact"))
                        )
                        if row_hit or dated_title_row or (title_hit and len(rows) == 1):
                            matched_rows.append((row_ordinal, row))
                    if not matched_rows:
                        continue
                    unit_axis = _unit_axis(table, compiled_specs=compiled_specs)
                    if unit_axis["reasons"]:
                        selected_table_inherits_bound_unit = bool(
                            bound_unit is not None
                            and page_json_version_id == region["page_json_version_id"]
                            and f"s{section_ordinal}" == region["section_id"]
                            and f"t{table_ordinal}" == region["table_id"]
                            and set(unit_axis["reasons"])
                            == {"MONEY_COLUMN_UNITS_ARE_NOT_UNIFORMLY_EXPLICIT"}
                            and not unit_axis["evidence"]
                            and not unit_axis["conflicting_surfaces"]
                            and not unit_axis["undeclared_evidence"]
                        )
                        if not selected_table_inherits_bound_unit:
                            reasons.append(
                                "SUPPLEMENTAL_DISCLOSURE_UNIT_INVALID:"
                                + disclosure["role"]
                            )
                            continue
                    if (
                        unit_axis["canonical_unit"] is not None
                        and bound_unit is not None
                        and unit_axis["canonical_unit"] != bound_unit
                    ):
                        reasons.append(
                            "SUPPLEMENTAL_DISCLOSURE_UNIT_CONFLICT:" + disclosure["role"]
                        )
                        continue
                    for row_ordinal, row in matched_rows:
                        values = row.get("values_exact")
                        if type(values) is not list or len(values) != len(columns):
                            reasons.append(
                                "SUPPLEMENTAL_DISCLOSURE_CELL_AXIS_INVALID:" + disclosure["role"]
                            )
                            continue
                        row_label = row.get("label_exact")
                        label_pairs = [
                            token
                            for parsed, token in _dated_money_pairs(row_label)
                            if parsed == current_date
                        ]
                        if len(label_pairs) == 1:
                            label_unit_bindings = _surface_unit_bindings(
                                row_label, compiled_specs=compiled_specs
                            )
                            label_unit_identities = {
                                (item["accepted"], item["canonical_unit"])
                                for item in label_unit_bindings
                            }
                            if len(label_unit_identities) != 1 or next(
                                iter(label_unit_identities)
                            ) != (True, bound_unit):
                                reasons.append(
                                    "SUPPLEMENTAL_TABLE_LABEL_UNIT_NOT_UNIQUE_OR_CONFLICTING:"
                                    + disclosure["role"]
                                )
                                continue
                            append_observation(
                                role=disclosure["role"],
                                source_kind="DATED_TABLE_ROW_LABEL_CURRENT_VALUE",
                                source_locator={
                                    "page_json_version_id": page_json_version_id,
                                    "row_id": f"r{row_ordinal}",
                                    "section_id": f"s{section_ordinal}",
                                    "table_id": f"t{table_ordinal}",
                                },
                                source_text=label_pairs[0],
                            )
                            continue
                        row_dates = _surface_dates(row_label)
                        if row_dates and current_date not in row_dates:
                            continue
                        if len(row_dates) > 1:
                            reasons.append(
                                "SUPPLEMENTAL_TABLE_ROW_PERIOD_EVIDENCE_CONFLICT:"
                                + disclosure["role"]
                            )
                            continue
                        date_axis_by_column = {
                            ordinal: _surface_dates(_header_text(columns[ordinal - 1]))
                            for ordinal in money_ordinals
                        }
                        conflicting_period_columns = [
                            ordinal
                            for ordinal, dates in date_axis_by_column.items()
                            if len(dates) > 1
                        ]
                        period_columns = [
                            ordinal for ordinal, dates in date_axis_by_column.items() if dates
                        ]
                        current_columns = [
                            ordinal
                            for ordinal, dates in date_axis_by_column.items()
                            if current_date in dates
                        ]
                        metric_columns = [
                            ordinal
                            for ordinal in money_ordinals
                            if any(
                                _contains_alias(_header_text(columns[ordinal - 1]), alias)
                                for alias in disclosure["value_header_aliases"]
                            )
                        ]
                        total_columns = [
                            ordinal
                            for ordinal in money_ordinals
                            if any(
                                _contains_alias(_header_text(columns[ordinal - 1]), alias)
                                for alias in compiled_specs["evaluation"]["total_column_aliases"]
                            )
                        ]
                        nonblank_columns = [
                            ordinal
                            for ordinal in money_ordinals
                            if values[ordinal - 1] not in {None, ""}
                        ]
                        selected = []
                        if conflicting_period_columns or len(current_columns) > 1:
                            reasons.append(
                                "SUPPLEMENTAL_TABLE_PERIOD_EVIDENCE_CONFLICT:" + disclosure["role"]
                            )
                        elif len(current_columns) == 1:
                            selected = current_columns
                        elif period_columns:
                            reasons.append(
                                "SUPPLEMENTAL_TABLE_CURRENT_PERIOD_NOT_VISIBLE:"
                                + disclosure["role"]
                            )
                        elif len(metric_columns) > 1:
                            reasons.append(
                                "SUPPLEMENTAL_TABLE_METRIC_COLUMN_NOT_UNIQUE:" + disclosure["role"]
                            )
                        elif len(metric_columns) == 1:
                            selected = metric_columns
                        elif len(total_columns) > 1:
                            reasons.append(
                                "SUPPLEMENTAL_TABLE_TOTAL_COLUMN_NOT_UNIQUE:" + disclosure["role"]
                            )
                        elif len(total_columns) == 1:
                            selected = total_columns
                        elif len(nonblank_columns) == 1:
                            selected = nonblank_columns
                        if len(selected) != 1:
                            if not any(
                                reason.endswith(":" + disclosure["role"])
                                for reason in reasons
                                if reason.startswith("SUPPLEMENTAL_TABLE_")
                            ):
                                reasons.append(
                                    "SUPPLEMENTAL_TABLE_CURRENT_VALUE_NOT_UNIQUE:"
                                    + disclosure["role"]
                                )
                            continue
                        column_ordinal = selected[0]
                        append_observation(
                            role=disclosure["role"],
                            source_kind="TYPED_SUPPLEMENTAL_TABLE_VALUE",
                            source_locator={
                                "column_id": f"c{column_ordinal}",
                                "page_json_version_id": page_json_version_id,
                                "row_id": f"r{row_ordinal}",
                                "section_id": f"s{section_ordinal}",
                                "table_id": f"t{table_ordinal}",
                            },
                            source_text=values[column_ordinal - 1],
                        )
    mappings = []
    for disclosure in disclosures:
        role = disclosure["role"]
        role_observations = [item for item in observations if item["role"] == role]
        coefficients = {item["cell"]["coefficient"] for item in role_observations}
        if len(coefficients) > 1:
            reasons.append("SUPPLEMENTAL_DISCLOSURE_VALUES_CONFLICT:" + role)
            continue
        if not role_observations:
            continue
        coefficient = next(iter(coefficients))
        material = {
            "bound_unit": bound_unit,
            "cell": {
                "coefficient": coefficient,
                "state": (
                    role_observations[0]["cell"]["state"]
                    if len(role_observations) == 1
                    else "CORROBORATED_DUPLICATE_EXACT"
                ),
            },
            "period_date": region["period_end_date"],
            "report_norm_id": compiled_specs["bindings"][role],
            "role": role,
            "row_id": "supplemental:" + role,
            "source_refs": canonical_clone_v1(role_observations),
        }
        mappings.append(
            {
                **material,
                "item_mapping_id": "gjffarimv1:item:" + canonical_json_sha256_v1(material),
            }
        )
    if reasons:
        mappings = []
    return {
        "mappings": mappings,
        "observations": observations,
        "reasons": sorted(set(reasons)),
    }


def _effective_blank(cell: Any, *, fallback: Mapping[str, Any]) -> dict[str, Any]:
    if cell is not None:
        return canonical_clone_v1(cell)
    return {
        "coefficient": None,
        "source_locator": canonical_clone_v1(fallback["source_locator"]),
        "source_text": "",
        "state": "BLANK",
    }


def _flattened_child(row: Mapping[str, Any]) -> bool:
    path = row.get("hierarchy_path_exact")
    return bool(
        type(path) is list
        and len(path) == 2
        and type(path[-1]) is str
        and _normalized(row.get("label_exact")) != _normalized(path[-1])
        and _contains_alias(path[-1], _normalized(row.get("label_exact")))
    )


def _build_single_asset_column_vertical_seal(
    *,
    records: Sequence[Mapping[str, Any]],
    equations: Sequence[Mapping[str, Any]],
    total_id: str,
    region: Mapping[str, Any],
    unit_id: str,
    binding_kind: str,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Seal a sole asset column without inventing a vacuous horizontal sum."""

    rows = [
        {
            "cells": canonical_clone_v1(record["cells"]),
            "row_id": record["row_id"],
            "row_kind": "DATA",
            "row_ordinal": ordinal,
        }
        for ordinal, record in enumerate(records)
    ]
    by_row = {row["row_id"]: row for row in rows}
    reasons = []
    equation_receipts = []
    for equation in equations:
        if equation["axis"] != "VERTICAL_ROLLFORWARD":
            reasons.append("SINGLE_ASSET_COLUMN_HAS_NON_VERTICAL_EQUATION")
            continue
        refs = [equation["result"], *(equation["terms"])]
        cells = []
        for ref in refs:
            row = by_row.get(ref["row_id"])
            cell = None if row is None else row["cells"].get(ref["column_id"])
            if cell is None or cell["state"] == "BLANK":
                cells = []
                break
            cells.append(cell)
        if not cells:
            status = "BLANK_OR_MISSING_TERM"
            reasons.append("SINGLE_ASSET_COLUMN_VERTICAL_EQUATION_HAS_BLANK_OR_MISSING_TERM")
            expected = None
            observed = None
        else:
            observed = cells[0]["coefficient"]
            expected = sum(
                term["multiplier"] * cell["coefficient"]
                for term, cell in zip(equation["terms"], cells[1:], strict=True)
            )
            status = "EXACT" if observed == expected else "MISMATCH"
            if status != "EXACT":
                reasons.append("SINGLE_ASSET_COLUMN_VERTICAL_EQUATION_MISMATCH")
        equation_receipts.append(
            {
                "equation_id": equation["equation_id"],
                "expected_coefficient": expected,
                "observed_coefficient": observed,
                "status": status,
            }
        )
    authority_sha256 = canonical_json_sha256_v1(compiled_specs["evaluation"])
    columns = [{"column_id": total_id, "column_kind": "IMPLICIT_TOTAL", "column_ordinal": 0}]
    projection = {
        "columns": columns,
        "equation_inventory": build_accounting_equation_inventory_manifest_v1(
            list(equations),
            authority_kind="PINNED_CONFIG",
            authority_ref=(
                compiled_specs["topology"]["family_id"] + ":" + EVALUATION_FORMAT_VERSION
            ),
            authority_sha256=authority_sha256,
        ),
        "equations": canonical_clone_v1(list(equations)),
        "period_id": region["period_end_date"] or "CURRENT_PERIOD",
        "rows": rows,
        "table_id": region["table_id"],
        "unit_id": unit_id,
    }
    material = {
        "binding_kind": binding_kind,
        "claim_boundary": (
            "EXACTLY_ONE_RECOGNIZED_ASSET_MONEY_COLUMN_IS_THE_SOLE_IMPLICIT_TOTAL_"
            "NO_VACUOUS_HORIZONTAL_SUM_SIGNED_VERTICAL_AND_CARRYING_CONTROLS_EXACT_"
            "NO_BLANK_TO_ZERO_SOURCE_MUTATION_SCHEMA_OR_BANK_FILE_PAGE_ROUTING"
        ),
        "effective_projection": projection,
        "equation_receipts": equation_receipts,
        "format_version": "FIXED_ASSET_SINGLE_ASSET_COLUMN_VERTICAL_SEAL_V1",
        "raw_table_snapshot": canonical_clone_v1(projection),
        "safety": {
            "blank_cell_means_zero": False,
            "family_bank_file_or_page_routing": False,
            "horizontal_equation_skipped_as_vacuous_identity": True,
            "source_rows_mutated": False,
            "vertical_equations_required_exact": True,
        },
        "status": (
            "SEALED_EXACT_SINGLE_ASSET_COLUMN_VERTICAL_BINDING"
            if not reasons
            else "UNRESOLVED"
        ),
        "unresolved_reasons": sorted(set(reasons)),
    }
    return {**material, "seal_id": "fasacvsv1:seal:" + canonical_json_sha256_v1(material)}


def _build_preserved_blank_explicit_total_seal(
    *,
    records: Sequence[Mapping[str, Any]],
    equations: Sequence[Mapping[str, Any]],
    money_ids: Sequence[str],
    total_id: str,
    omitted_horizontal_rows: Sequence[Mapping[str, Any]],
    region: Mapping[str, Any],
    unit_id: str,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Seal raw explicit totals while preserving unavailable detail cells."""

    rows = [
        {
            "cells": canonical_clone_v1(record["cells"]),
            "row_id": record["row_id"],
            "row_kind": "DATA",
            "row_ordinal": ordinal,
        }
        for ordinal, record in enumerate(records)
    ]
    by_row = {row["row_id"]: row for row in rows}
    reasons = []
    equation_receipts = []
    for equation in equations:
        refs = [equation["result"], *(equation["terms"])]
        cells = []
        for ref in refs:
            row = by_row.get(ref["row_id"])
            cell = None if row is None else row["cells"].get(ref["column_id"])
            if cell is None or cell["state"] == "BLANK":
                cells = []
                break
            cells.append(cell)
        if not cells:
            status = "BLANK_OR_MISSING_TERM"
            reasons.append("PRESERVED_BLANK_TOTAL_LANE_EQUATION_HAS_BLANK_OR_MISSING_TERM")
            expected = None
            observed = None
        else:
            observed = cells[0]["coefficient"]
            expected = sum(
                term["multiplier"] * cell["coefficient"]
                for term, cell in zip(equation["terms"], cells[1:], strict=True)
            )
            status = "EXACT" if observed == expected else "MISMATCH"
            if status != "EXACT":
                reasons.append("PRESERVED_BLANK_TOTAL_LANE_EQUATION_MISMATCH")
        equation_receipts.append(
            {
                "axis": equation["axis"],
                "equation_id": equation["equation_id"],
                "expected_coefficient": expected,
                "observed_coefficient": observed,
                "status": status,
            }
        )
    authority_sha256 = canonical_json_sha256_v1(compiled_specs["evaluation"])
    columns = [
        {
            "column_id": column_id,
            "column_kind": "TOTAL" if column_id == total_id else "DETAIL",
            "column_ordinal": ordinal,
        }
        for ordinal, column_id in enumerate(money_ids)
    ]
    projection = {
        "columns": columns,
        "equation_inventory": build_accounting_equation_inventory_manifest_v1(
            list(equations),
            authority_kind="PINNED_CONFIG",
            authority_ref=(
                compiled_specs["topology"]["family_id"] + ":" + EVALUATION_FORMAT_VERSION
            ),
            authority_sha256=authority_sha256,
        ),
        "equations": canonical_clone_v1(list(equations)),
        "period_id": region["period_end_date"] or "CURRENT_PERIOD",
        "rows": rows,
        "table_id": region["table_id"],
        "unit_id": unit_id,
    }
    material = {
        "binding_kind": "SOURCE_VISIBLE_EXPLICIT_TOTAL_WITH_PRESERVED_BLANK_DETAILS",
        "claim_boundary": (
            "SOURCE_VISIBLE_EXPLICIT_TOTAL_CONTROLS_VERTICAL_CLOSURE_COMPLETE_DETAIL_"
            "ROWS_RETAIN_EXACT_HORIZONTAL_EQUATIONS_INCOMPLETE_DETAIL_ROWS_PRESERVE_"
            "BLANKS_WITHOUT_INFERENCE_NO_RELOCATION_SOURCE_MUTATION_OR_BANK_FILE_PAGE_ROUTING"
        ),
        "effective_projection": projection,
        "equation_receipts": equation_receipts,
        "format_version": "FIXED_ASSET_PRESERVED_BLANK_EXPLICIT_TOTAL_SEAL_V1",
        "omitted_horizontal_rows": canonical_clone_v1(list(omitted_horizontal_rows)),
        "raw_table_snapshot": canonical_clone_v1(projection),
        "safety": {
            "blank_cell_means_zero": False,
            "family_bank_file_or_page_routing": False,
            "incomplete_detail_row_horizontal_equation_omitted": True,
            "source_rows_mutated": False,
            "vertical_equations_required_exact": True,
        },
        "status": "SEALED_EXACT_PRESERVED_BLANK_TOTAL_LANE" if not reasons else "UNRESOLVED",
        "unresolved_reasons": sorted(set(reasons)),
    }
    return {**material, "seal_id": "fapbetsv1:seal:" + canonical_json_sha256_v1(material)}


def _project_bounded_source_presentation_rounding_seal(
    width_seal: Mapping[str, Any],
    *,
    unit_id: str,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Accept only equation deltas possible under independent display rounding.

    Printed subtotals and their independently rounded components need not add
    exactly in a displayed thousand/million/billion unit.  For an equation
    with ``n`` source terms plus one result, the closed integer interval is
    ``floor((n + 1) / 2)`` display units.  No cell is changed and every
    equation must be either exact or inside its own interval.
    """

    policy = compiled_specs["evaluation"].get("source_presentation_rounding_policy")
    cloned = canonical_clone_v1(width_seal)
    if policy is None or width_seal.get("status") != "UNRESOLVED":
        return cloned
    unit_bindings = [
        binding
        for binding in compiled_specs["evaluation"]["money_unit_bindings"]
        if binding["canonical_unit"] == unit_id
    ]
    if len(unit_bindings) != 1 or unit_bindings[0]["magnitude_power10"] < 3:
        return cloned
    raw = width_seal.get("raw_table_snapshot")
    if type(raw) is not dict or type(raw.get("rows")) is not list or type(
        raw.get("equations")
    ) is not list or not raw["equations"]:
        return cloned
    by_row = {
        row.get("row_id"): row.get("cells")
        for row in raw["rows"]
        if type(row) is dict and type(row.get("row_id")) is str
    }
    receipts = []
    rounded_count = 0
    for equation in raw["equations"]:
        if type(equation) is not dict:
            return cloned
        refs = [equation.get("result"), *(equation.get("terms") or [])]
        cells = []
        for ref in refs:
            if type(ref) is not dict:
                return cloned
            row = by_row.get(ref.get("row_id"))
            cell = row.get(ref.get("column_id")) if type(row) is dict else None
            if (
                type(cell) is not dict
                or cell.get("state") == "BLANK"
                or type(cell.get("coefficient")) is not int
            ):
                return cloned
            cells.append(cell)
        terms = equation.get("terms")
        if type(terms) is not list or not terms:
            return cloned
        observed = cells[0]["coefficient"]
        expected = sum(
            term.get("multiplier") * cell["coefficient"]
            for term, cell in zip(terms, cells[1:], strict=True)
            if type(term.get("multiplier")) is int
        )
        if any(type(term.get("multiplier")) is not int for term in terms):
            return cloned
        delta = observed - expected
        tolerance = (len(terms) + 1) // 2
        if abs(delta) > tolerance:
            return cloned
        status = "EXACT" if delta == 0 else "WITHIN_INDEPENDENT_ROUNDING_INTERVAL"
        rounded_count += int(delta != 0)
        receipts.append(
            {
                "axis": equation.get("axis"),
                "delta_display_units": delta,
                "equation_id": equation.get("equation_id"),
                "expected_coefficient": expected,
                "observed_coefficient": observed,
                "rounding_interval_display_units": [-tolerance, tolerance],
                "status": status,
            }
        )
    if rounded_count == 0:
        return cloned
    material = {
        "binding_kind": policy,
        "claim_boundary": (
            "SOURCE_CELLS_REMAIN_EXACT_PRINTED_VALUES_ALL_DECLARED_EQUATIONS_EXACT_"
            "OR_WITHIN_THE_MATHEMATICALLY_BOUNDED_INDEPENDENT_DISPLAY_ROUNDING_"
            "INTERVAL_NO_CELL_REPAIR_VALUE_INFERENCE_OR_BANK_FILE_PAGE_ROUTING"
        ),
        "effective_projection": canonical_clone_v1(raw),
        "equation_receipts": receipts,
        "format_version": "FIXED_ASSET_BOUNDED_SOURCE_PRESENTATION_ROUNDING_SEAL_V1",
        "magnitude_power10": unit_bindings[0]["magnitude_power10"],
        "raw_table_snapshot": canonical_clone_v1(raw),
        "safety": {
            "blank_cell_means_zero": False,
            "family_bank_file_or_page_routing": False,
            "source_cells_mutated": False,
            "source_values_inferred": False,
        },
        "status": "SEALED_ALL_EQUATIONS_WITHIN_INDEPENDENT_DISPLAY_ROUNDING_INTERVAL",
        "unit_id": unit_id,
        "unresolved_reasons": [],
    }
    return {
        **material,
        "seal_id": "fasprsv1:seal:" + canonical_json_sha256_v1(material),
    }


def _movement_equation_multiplier(
    record: Mapping[str, Any],
    *,
    total_id: str,
    branch_balance_sign: int,
    compiled_specs: Mapping[str, Any],
) -> tuple[int, dict[str, Any]]:
    direction = compiled_specs["evaluation"]["movement_role_directions"].get(
        record["role"], "PRESERVE_SIGN"
    )
    coefficient = record["cells"][total_id]["coefficient"]
    if direction == "PRESERVE_SIGN" or coefficient in {None, 0}:
        multiplier = 1
    else:
        observed_sign = 1 if coefficient > 0 else -1
        economic_sign = branch_balance_sign * (1 if direction == "INCREASE" else -1)
        multiplier = 1 if observed_sign == economic_sign else -1
    return multiplier, {
        "branch_balance_sign": branch_balance_sign,
        "configured_direction": direction,
        "equation_multiplier": multiplier,
        "observed_coefficient": coefficient,
        "role": record["role"],
        "row_id": record["row_id"],
    }


def _equation_closes_on_fully_observed_source_cells(
    equation: Mapping[str, Any],
    *,
    row_by_id: Mapping[str, Mapping[str, Any]],
) -> bool:
    """Return true only for literal source cells that close one equation exactly."""

    result = equation.get("result")
    terms = equation.get("terms")
    if type(result) is not dict or type(terms) is not list or not terms:
        return False
    coordinates = [(result, 1), *((term, term.get("multiplier")) for term in terms)]
    values = []
    for coordinate, multiplier in coordinates:
        if type(coordinate) is not dict or type(multiplier) is not int:
            return False
        record = row_by_id.get(coordinate.get("row_id"))
        cell = (
            record.get("cells", {}).get(coordinate.get("column_id"))
            if type(record) is dict
            else None
        )
        if (
            type(cell) is not dict
            or cell.get("state") == "BLANK"
            or type(cell.get("coefficient")) is not int
        ):
            return False
        values.append((multiplier, cell["coefficient"]))
    return values[0][1] == sum(multiplier * value for multiplier, value in values[1:])


def _source_repair_cell_identities(
    compiled_specs: Mapping[str, Any],
) -> set[tuple[str, str, str, str, str]]:
    identities = set()
    overlay = compiled_specs.get("source_repair_overlay")
    if type(overlay) is not dict:
        return identities
    for repair in overlay.get("repairs", []):
        if type(repair) is not dict:
            continue
        version_id = repair.get("base_page_json_version_id")
        table_ref = repair.get("table_ref")
        if type(version_id) is not str or type(table_ref) is not dict:
            continue
        for cell in repair.get("cell_repairs", []):
            if type(cell) is not dict or type(cell.get("cell_id")) is not str:
                continue
            match = re.fullmatch(r"(r[1-9][0-9]*):(c[1-9][0-9]*)", cell["cell_id"])
            if match is None:
                continue
            identities.add(
                (
                    version_id,
                    table_ref.get("section_id"),
                    table_ref.get("table_id"),
                    match.group(1),
                    match.group(2),
                )
            )
    return identities


def _source_cell_identity(
    cell: Mapping[str, Any],
) -> tuple[str, str, str, str, str] | None:
    locator = cell.get("source_locator")
    if type(locator) is not dict:
        return None
    identity = tuple(
        locator.get(field)
        for field in (
            "page_json_version_id",
            "section_id",
            "table_id",
            "row_id",
            "column_id",
        )
    )
    return identity if all(type(item) is str and item for item in identity) else None


def _strict_subset_equation_receipt(
    equation: Mapping[str, Any],
    *,
    row_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    result = equation.get("result")
    terms = equation.get("terms")
    if type(result) is not dict or type(terms) is not list or not terms:
        return {
            "axis": equation.get("axis"),
            "equation_id": equation.get("equation_id"),
            "status": "INVALID_EQUATION_SHAPE",
        }
    coordinates = [result, *terms]
    cells = []
    coordinate_keys = []
    for coordinate in coordinates:
        if type(coordinate) is not dict:
            return {
                "axis": equation.get("axis"),
                "equation_id": equation.get("equation_id"),
                "status": "INVALID_EQUATION_COORDINATE",
            }
        record = row_by_id.get(coordinate.get("row_id"))
        cell = (
            record.get("cells", {}).get(coordinate.get("column_id"))
            if type(record) is dict
            else None
        )
        identity = _source_cell_identity(cell) if type(cell) is dict else None
        if (
            type(cell) is not dict
            or cell.get("state") == "BLANK"
            or type(cell.get("coefficient")) is not int
            or identity is None
        ):
            return {
                "axis": equation.get("axis"),
                "equation_id": equation.get("equation_id"),
                "status": "BLANK_MISSING_OR_UNBOUND_SOURCE_CELL",
            }
        cells.append(cell)
        coordinate_keys.append(identity)
    term_keys = coordinate_keys[1:]
    if coordinate_keys[0] in term_keys or len(term_keys) != len(set(term_keys)):
        return {
            "axis": equation.get("axis"),
            "equation_id": equation.get("equation_id"),
            "status": "OVERLAPPING_OR_DUPLICATED_SOURCE_OPERAND",
        }
    multipliers = [term.get("multiplier") for term in terms]
    if any(type(multiplier) is not int for multiplier in multipliers):
        return {
            "axis": equation.get("axis"),
            "equation_id": equation.get("equation_id"),
            "status": "INVALID_EQUATION_MULTIPLIER",
        }
    observed = cells[0]["coefficient"]
    expected = sum(
        multiplier * cell["coefficient"]
        for multiplier, cell in zip(multipliers, cells[1:], strict=True)
    )
    material = {
        "axis": equation.get("axis"),
        "complete_disjoint_source_operands": True,
        "equation_id": equation.get("equation_id"),
        "expected_coefficient": expected,
        "observed_coefficient": observed,
        "result": canonical_clone_v1(result),
        "status": "EXACT" if expected == observed else "MISMATCH",
        "terms": canonical_clone_v1(terms),
    }
    return {
        **material,
        "receipt_id": "fasrersv1:receipt:" + canonical_json_sha256_v1(material),
    }


def _row_mapping_material(
    *,
    record: Mapping[str, Any],
    cell: Mapping[str, Any],
    source_cells: Sequence[Mapping[str, Any]],
    period_date: str,
    unit_id: str,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    source_refs = [
        {
            "cell": canonical_clone_v1(source_cell),
            "hierarchy_path_exact": canonical_clone_v1(record["hierarchy_path_exact"]),
            "label_exact": record["label_exact"],
            "row_id": record["source_row_id"],
            "source_ordinal": record["source_ordinal"],
        }
        for source_cell in source_cells
    ]
    return {
        "bound_unit": unit_id,
        "cell": canonical_clone_v1(cell),
        "period_date": period_date,
        "report_norm_id": compiled_specs["bindings"][record["role"]],
        "role": record["role"],
        "row_id": record["row_id"],
        "source_refs": source_refs,
    }


def _seal_mapping_material(material: Mapping[str, Any]) -> dict[str, Any]:
    cloned = canonical_clone_v1(material)
    return {
        **cloned,
        "item_mapping_id": "gjffarimv1:item:" + canonical_json_sha256_v1(cloned),
    }


def _extract_cropped_total_complete_asset_frontier(
    *,
    table: Mapping[str, Any],
    region: Mapping[str, Any],
    classification: Mapping[str, Any],
    unit_axis: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Forward-aggregate rows only after every asset lane closes vertically."""

    binding = classification.get("cropped_total_complete_asset_frontier_binding")
    columns = table.get("columns")
    rows = table.get("rows")
    reasons = []
    if (
        type(binding) is not dict
        or type(columns) is not list
        or type(rows) is not list
        or not classification.get("complete")
        or not unit_axis.get("complete")
        or type(unit_axis.get("canonical_unit")) is not str
        or not unit_axis["canonical_unit"]
    ):
        reasons.append("CROPPED_TOTAL_STRICT_SUBSET_CONTEXT_IS_NOT_COMPLETE")
    asset_ordinals = (
        list(binding.get("asset_column_ordinals", [])) if type(binding) is dict else []
    )
    if (
        not asset_ordinals
        or asset_ordinals != sorted(set(asset_ordinals))
        or any(type(ordinal) is not int or not 1 <= ordinal <= len(columns) for ordinal in asset_ordinals)
    ):
        reasons.append("CROPPED_TOTAL_ASSET_FRONTIER_IS_INVALID")
    repaired_cells = _source_repair_cell_identities(compiled_specs)
    records = []
    row_by_id = {}
    branch_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    subtotal_roles = {
        role
        for layout in compiled_specs["evaluation"]["branch_layouts"]
        for role in layout["subtotal_roles"]
    }
    for source_ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict:
            reasons.append("SOURCE_ROW_IS_NOT_AN_OBJECT")
            continue
        if any(
            _supplemental_row_matches(
                row,
                disclosure,
                table=table,
                compiled_specs=compiled_specs,
            )
            for disclosure in compiled_specs["evaluation"]["supplemental_disclosure_roles"]
        ) or _source_only_row_matches(row, compiled_specs=compiled_specs):
            continue
        layout = _branch_layout_for_row(row, compiled_specs=compiled_specs)
        if layout is None or row.get("row_kind") == "GROUP":
            continue
        role = _role_for_row(row, layout, compiled_specs=compiled_specs)
        values = row.get("values_exact")
        if role is None or type(values) is not list or len(values) != len(columns):
            reasons.append(f"CROPPED_TOTAL_SOURCE_ROW_IS_NOT_EXACT:r{source_ordinal}")
            continue
        if role in subtotal_roles or _visible_subtotal_ancestor_roles(
            row, layout, compiled_specs=compiled_specs
        ):
            reasons.append(f"CROPPED_TOTAL_FRONTIER_IS_NOT_FLAT:r{source_ordinal}")
            continue
        cells = {}
        try:
            for ordinal in asset_ordinals:
                column_id = f"c{ordinal}"
                cells[column_id] = _money(
                    values[ordinal - 1],
                    source_locator={
                        "column_id": column_id,
                        "page_json_version_id": region["page_json_version_id"],
                        "row_id": f"r{source_ordinal}",
                        "section_id": region["section_id"],
                        "table_id": region["table_id"],
                    },
                )
        except GeminiJsonFixedAssetRollforwardFamilyV1Error:
            reasons.append(f"CROPPED_TOTAL_MONEY_CELL_INVALID:r{source_ordinal}")
            continue
        if any(cell["state"] == "BLANK" for cell in cells.values()):
            reasons.append(f"CROPPED_TOTAL_ASSET_ROW_HAS_BLANK_OPERAND:r{source_ordinal}")
            continue
        if any(_source_cell_identity(cell) in repaired_cells for cell in cells.values()):
            reasons.append(f"CROPPED_TOTAL_ASSET_ROW_USES_SOURCE_REPAIR:r{source_ordinal}")
            continue
        record = {
            "branch_role": layout["branch_role"],
            "cells": cells,
            "hierarchy_path_exact": canonical_clone_v1(row.get("hierarchy_path_exact")),
            "label_exact": row.get("label_exact"),
            "role": role,
            "row_id": f"r{source_ordinal}",
            "source_row_id": f"r{source_ordinal}",
            "source_ordinal": source_ordinal,
            "source_order_ordinal": source_ordinal,
        }
        records.append(record)
        row_by_id[record["row_id"]] = record
        branch_records[layout["branch_role"]].append(record)
    role_counts: dict[str, int] = defaultdict(int)
    for record in records:
        role_counts[record["role"]] += 1
    for role, count in role_counts.items():
        if count != 1:
            reasons.append("CROPPED_TOTAL_ROLE_ROW_IS_NOT_UNIQUE:" + role)
    equations = []
    equation_receipts = []
    signed_layouts = [
        item
        for item in compiled_specs["evaluation"]["branch_layouts"]
        if item["rollforward_kind"] == "SIGNED_ADDITIVE"
    ]
    carrying_layout = next(
        (
            item
            for item in compiled_specs["evaluation"]["branch_layouts"]
            if item["rollforward_kind"] == "COST_AND_DEPRECIATION_CONTROL"
        ),
        None,
    )
    for layout in signed_layouts:
        branch_axis = branch_records.get(layout["branch_role"], [])
        opening = [item for item in branch_axis if item["role"] == layout["opening_role"]]
        ending = [item for item in branch_axis if item["role"] == layout["ending_role"]]
        movements = [
            item
            for item in branch_axis
            if item["role"] not in {layout["opening_role"], layout["ending_role"]}
        ]
        if len(opening) != 1 or len(ending) != 1 or not movements:
            reasons.append("CROPPED_TOTAL_BRANCH_FRONTIER_IS_INCOMPLETE:" + layout["branch_role"])
            continue
        if not (
            opening[0]["source_order_ordinal"] < ending[0]["source_order_ordinal"]
            and all(
                opening[0]["source_order_ordinal"]
                < item["source_order_ordinal"]
                < ending[0]["source_order_ordinal"]
                for item in movements
            )
        ):
            reasons.append("CROPPED_TOTAL_BRANCH_SOURCE_ORDER_IS_INVALID:" + layout["branch_role"])
            continue
        for ordinal in asset_ordinals:
            column_id = f"c{ordinal}"
            endpoints = [
                opening[0]["cells"][column_id]["coefficient"],
                ending[0]["cells"][column_id]["coefficient"],
            ]
            if all(value >= 0 for value in endpoints):
                branch_sign = 1
            elif all(value <= 0 for value in endpoints):
                branch_sign = -1
            else:
                reasons.append(
                    "CROPPED_TOTAL_BRANCH_ENDPOINT_SIGN_IS_NOT_UNIQUE:"
                    + layout["branch_role"]
                    + ":"
                    + column_id
                )
                continue
            terms = [{"column_id": column_id, "multiplier": 1, "row_id": opening[0]["row_id"]}]
            for movement in movements:
                multiplier, _receipt = _movement_equation_multiplier(
                    movement,
                    total_id=column_id,
                    branch_balance_sign=branch_sign,
                    compiled_specs=compiled_specs,
                )
                terms.append(
                    {
                        "column_id": column_id,
                        "multiplier": multiplier,
                        "row_id": movement["row_id"],
                    }
                )
            equation = {
                "axis": "VERTICAL_ASSET_COLUMN_ROLLFORWARD",
                "equation_id": f"cropped:{layout['branch_role']}:{column_id}",
                "result": {"column_id": column_id, "row_id": ending[0]["row_id"]},
                "terms": terms,
            }
            receipt = _strict_subset_equation_receipt(equation, row_by_id=row_by_id)
            equations.append(equation)
            equation_receipts.append(receipt)
            if receipt["status"] != "EXACT":
                reasons.append("CROPPED_TOTAL_VERTICAL_EQUATION_NOT_EXACT:" + equation["equation_id"])
    if carrying_layout is not None:
        cost_layout = next(item for item in signed_layouts if item["branch_role"] == "COST_BRANCH")
        dep_layout = next(
            item for item in signed_layouts if item["branch_role"] == "DEPRECIATION_BRANCH"
        )
        by_role = {record["role"]: record for record in records if role_counts[record["role"]] == 1}
        for endpoint in ("opening_role", "ending_role"):
            roles = (
                cost_layout[endpoint],
                dep_layout[endpoint],
                carrying_layout[endpoint],
            )
            if any(role not in by_role for role in roles):
                reasons.append("CROPPED_TOTAL_CARRYING_FRONTIER_IS_INCOMPLETE:" + endpoint)
                continue
            for ordinal in asset_ordinals:
                column_id = f"c{ordinal}"
                dep_value = by_role[roles[1]]["cells"][column_id]["coefficient"]
                dep_multiplier = -1 if dep_value >= 0 else 1
                equation = {
                    "axis": "VERTICAL_ASSET_COLUMN_CARRYING_CONTROL",
                    "equation_id": f"cropped:carrying:{endpoint}:{column_id}",
                    "result": {"column_id": column_id, "row_id": by_role[roles[2]]["row_id"]},
                    "terms": [
                        {"column_id": column_id, "multiplier": 1, "row_id": by_role[roles[0]]["row_id"]},
                        {"column_id": column_id, "multiplier": dep_multiplier, "row_id": by_role[roles[1]]["row_id"]},
                    ],
                }
                receipt = _strict_subset_equation_receipt(equation, row_by_id=row_by_id)
                equations.append(equation)
                equation_receipts.append(receipt)
                if receipt["status"] != "EXACT":
                    reasons.append("CROPPED_TOTAL_CARRYING_EQUATION_NOT_EXACT:" + equation["equation_id"])
    mappings = []
    row_receipts = []
    if not reasons:
        by_role = {record["role"]: record for record in records}
        for role in compiled_specs["output_role_order"]:
            record = by_role.get(role)
            if record is None:
                continue
            source_cells = [record["cells"][f"c{ordinal}"] for ordinal in asset_ordinals]
            coefficient = sum(cell["coefficient"] for cell in source_cells)
            mapping = _seal_mapping_material(
                _row_mapping_material(
                    record=record,
                    cell={
                        "coefficient": coefficient,
                        "state": "DERIVED_EXACT_COMPLETE_DISJOINT_ASSET_COLUMN_FRONTIER",
                    },
                    source_cells=source_cells,
                    period_date=region["period_end_date"],
                    unit_id=unit_axis["canonical_unit"],
                    compiled_specs=compiled_specs,
                )
            )
            mappings.append(mapping)
            row_material = {
                "asset_column_ids": [f"c{ordinal}" for ordinal in asset_ordinals],
                "derived_coefficient": coefficient,
                "mapping_id": mapping["item_mapping_id"],
                "role": role,
                "row_id": record["row_id"],
                "source_ref_count": len(source_cells),
                "status": "MAPPED_FORWARD_AGGREGATE_COMPLETE_DISJOINT_FRONTIER",
            }
            row_receipts.append(
                {
                    **row_material,
                    "receipt_id": "fasrdrsv1:receipt:"
                    + canonical_json_sha256_v1(row_material),
                }
            )
    projection = {
        "columns": [
            {"column_id": f"c{ordinal}", "column_kind": "ASSET_DETAIL", "column_ordinal": ordinal}
            for ordinal in asset_ordinals
        ],
        "equations": canonical_clone_v1(equations),
        "period_id": region["period_end_date"],
        "rows": [
            {
                "cells": canonical_clone_v1(record["cells"]),
                "row_id": record["row_id"],
                "row_kind": "DATA",
                "row_ordinal": ordinal,
            }
            for ordinal, record in enumerate(records, start=1)
        ],
        "table_id": region["table_id"],
        "unit_id": unit_axis.get("canonical_unit"),
    }
    receipt_material = {
        "binding": canonical_clone_v1(binding),
        "equation_receipts": equation_receipts,
        "excluded_cropped_total_column": binding.get("cropped_total_column_ordinal") if type(binding) is dict else None,
        "mapped_rows": row_receipts,
        "policy": _ROW_LEVEL_STRICT_SUBSET_POLICY,
        "safety": {
            "blank_cell_means_zero": False,
            "complete_disjoint_asset_frontier_required": True,
            "cropped_total_cells_consumed": False,
            "equation_backsolve": False,
            "family_bank_file_page_or_value_routing": False,
            "source_repair_cells_consumed": False,
        },
        "status": "SEALED" if mappings and not reasons else "UNRESOLVED",
        "unresolved_reasons": sorted(set(reasons)),
    }
    subset_receipt = {
        **receipt_material,
        "receipt_id": "fasrssv1:receipt:" + canonical_json_sha256_v1(receipt_material),
    }
    seal_material = {
        "claim_boundary": _ROW_LEVEL_STRICT_SUBSET_CLAIM_BOUNDARY,
        "effective_projection": projection,
        "format_version": "FIXED_ASSET_ROW_LEVEL_STRICT_SUBSET_SEAL_V1",
        "row_level_strict_subset_receipt": subset_receipt,
        "status": "SEALED_EXACT_ROW_LEVEL_STRICT_SUBSET" if mappings and not reasons else "UNRESOLVED",
        "unresolved_reasons": sorted(set(reasons)),
    }
    width_seal = {
        **seal_material,
        "seal_id": "fasrlssv1:seal:" + canonical_json_sha256_v1(seal_material),
    }
    table_receipt = {
        "classification": canonical_clone_v1(classification),
        "equations": equations,
        "raw_row_inventory": [
            {
                "branch_role": record["branch_role"],
                "hierarchy_path_exact": canonical_clone_v1(record["hierarchy_path_exact"]),
                "label_exact": record["label_exact"],
                "role": record["role"],
                "row_id": record["row_id"],
                "source_ordinal": record["source_ordinal"],
            }
            for record in records
        ],
        "row_level_strict_subset_receipt": subset_receipt,
        "source_only_rows": [],
        "unit_axis": canonical_clone_v1(unit_axis),
    }
    return {
        "claim_boundary": _ROW_LEVEL_STRICT_SUBSET_CLAIM_BOUNDARY,
        "classification": canonical_clone_v1(classification),
        "mappings": mappings,
        "reasons": sorted(set(reasons)),
        "subtotal_collapse": None,
        "table_receipt": table_receipt,
        "unit_axis": canonical_clone_v1(unit_axis),
        "width_seal": width_seal,
    }


def _build_printed_total_row_level_strict_subset(
    *,
    records: Sequence[Mapping[str, Any]],
    row_by_id: Mapping[str, Mapping[str, Any]],
    equations: Sequence[Mapping[str, Any]],
    total_id: str,
    region: Mapping[str, Any],
    unit_id: str,
    raw_projection: Mapping[str, Any],
    original_reasons: Sequence[str],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Keep only independently authenticated printed role totals.

    A failed equation excludes its result row, not unrelated rows.  Endpoints
    additionally require their own horizontal asset equation to close.  A
    declared subtotal may use its exact complete-disjoint child-total frontier
    when its horizontal detail axis conflicts; ordinary movement rows may not.
    """

    repaired_cells = _source_repair_cell_identities(compiled_specs)
    endpoint_roles = {
        role
        for layout in compiled_specs["evaluation"]["branch_layouts"]
        for role in (layout["opening_role"], layout["ending_role"])
    }
    subtotal_roles = {
        role
        for layout in compiled_specs["evaluation"]["branch_layouts"]
        for role in layout["subtotal_roles"]
    }
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["role"]].append(record)
    equation_receipts = [
        _strict_subset_equation_receipt(equation, row_by_id=row_by_id)
        for equation in equations
    ]
    paired = list(zip(equations, equation_receipts, strict=True))
    mappings = []
    mapped_rows = []
    excluded_rows = []
    for role in compiled_specs["output_role_order"]:
        observations = grouped.get(role, [])
        if not observations:
            continue
        if len(observations) != 1:
            excluded_rows.append(
                {
                    "reasons": ["ROLE_SOURCE_ROW_IS_NOT_UNIQUE"],
                    "role": role,
                    "row_ids": [item["row_id"] for item in observations],
                    "status": "EXCLUDED",
                }
            )
            continue
        record = observations[0]
        cell = record.get("cells", {}).get(total_id)
        row_reasons = []
        if (
            type(cell) is not dict
            or cell.get("state") == "BLANK"
            or type(cell.get("coefficient")) is not int
            or type(cell.get("source_text")) is not str
            or _source_cell_identity(cell) is None
        ):
            row_reasons.append("PRINTED_TOTAL_CELL_IS_NOT_EXACTLY_SOURCE_BOUND")
        elif _source_cell_identity(cell) in repaired_cells:
            row_reasons.append(
                "PRINTED_TOTAL_DEPENDS_ON_AUTHENTICATED_SOURCE_REPAIR_REQUIRES_SEPARATE_REVIEW"
            )
        horizontal = [
            receipt
            for equation, receipt in paired
            if equation.get("axis") == "HORIZONTAL_ROW"
            and equation.get("result")
            == {"column_id": total_id, "row_id": record["row_id"]}
        ]
        result_equations = [
            receipt
            for equation, receipt in paired
            if equation.get("axis") != "HORIZONTAL_ROW"
            and equation.get("result")
            == {"column_id": total_id, "row_id": record["row_id"]}
        ]
        exact_horizontal = len(horizontal) == 1 and horizontal[0]["status"] == "EXACT"
        exact_subtotal = any(
            receipt["status"] == "EXACT"
            and type(receipt.get("equation_id")) is str
            and receipt["equation_id"].startswith(f"subtotal:{record['row_id']}:")
            for receipt in result_equations
        )
        mismatched_result = [
            receipt.get("equation_id")
            for receipt in result_equations
            if receipt.get("status") != "EXACT"
        ]
        if mismatched_result:
            row_reasons.append("RESULT_EQUATION_NOT_EXACT")
        if role in endpoint_roles:
            if not exact_horizontal:
                row_reasons.append("ENDPOINT_HORIZONTAL_ASSET_EQUATION_NOT_EXACT")
        elif role in subtotal_roles:
            if not (exact_horizontal or exact_subtotal):
                row_reasons.append("SUBTOTAL_HAS_NO_EXACT_ROW_OR_CHILD_TOTAL_FRONTIER")
        elif not exact_horizontal:
            row_reasons.append("DIRECT_ROLE_HORIZONTAL_ASSET_EQUATION_NOT_EXACT")
        relevant_receipts = [*horizontal, *result_equations]
        if any(
            receipt.get("status")
            in {
                "BLANK_MISSING_OR_UNBOUND_SOURCE_CELL",
                "INVALID_EQUATION_COORDINATE",
                "INVALID_EQUATION_MULTIPLIER",
                "INVALID_EQUATION_SHAPE",
                "OVERLAPPING_OR_DUPLICATED_SOURCE_OPERAND",
            }
            for receipt in relevant_receipts
        ):
            row_reasons.append("ROW_EQUATION_IS_NOT_COMPLETE_AND_DISJOINT")
        if row_reasons:
            excluded_rows.append(
                {
                    "equation_receipts": relevant_receipts,
                    "reasons": sorted(set(row_reasons)),
                    "role": role,
                    "row_id": record["row_id"],
                    "status": "EXCLUDED",
                }
            )
            continue
        mapping = _seal_mapping_material(
            _row_mapping_material(
                record=record,
                cell={"coefficient": cell["coefficient"], "state": cell["state"]},
                source_cells=[cell],
                period_date=region["period_end_date"],
                unit_id=unit_id,
                compiled_specs=compiled_specs,
            )
        )
        mappings.append(mapping)
        row_material = {
            "equation_receipts": relevant_receipts,
            "mapping_id": mapping["item_mapping_id"],
            "role": role,
            "row_id": record["row_id"],
            "status": "MAPPED_EXACT_UNREPAIRED_PRINTED_TOTAL",
            "value_binding_kind": (
                "PRINTED_SUBTOTAL_WITH_EXACT_CHILD_TOTAL_FRONTIER"
                if role in subtotal_roles and not exact_horizontal
                else "PRINTED_TOTAL_WITH_EXACT_HORIZONTAL_ASSET_FRONTIER"
            ),
        }
        mapped_rows.append(
            {
                **row_material,
                "receipt_id": "fasrmrsv1:receipt:" + canonical_json_sha256_v1(row_material),
            }
        )
    receipt_material = {
        "excluded_rows": excluded_rows,
        "mapped_rows": mapped_rows,
        "original_table_reasons": sorted(set(original_reasons)),
        "policy": _ROW_LEVEL_STRICT_SUBSET_POLICY,
        "safety": {
            "blank_cell_means_zero": False,
            "complete_disjoint_equation_required": True,
            "endpoint_horizontal_conflict_veto": True,
            "equation_backsolve": False,
            "family_bank_file_page_or_value_routing": False,
            "source_repair_total_cells_consumed": False,
            "unmapped_rows_typed": True,
        },
        "status": "SEALED" if mappings else "UNRESOLVED",
    }
    receipt = {
        **receipt_material,
        "receipt_id": "fasrssv1:receipt:" + canonical_json_sha256_v1(receipt_material),
    }
    seal_material = {
        "claim_boundary": _ROW_LEVEL_STRICT_SUBSET_CLAIM_BOUNDARY,
        "effective_projection": canonical_clone_v1(raw_projection),
        "format_version": "FIXED_ASSET_ROW_LEVEL_STRICT_SUBSET_SEAL_V1",
        "row_level_strict_subset_receipt": receipt,
        "status": "SEALED_EXACT_ROW_LEVEL_STRICT_SUBSET" if mappings else "UNRESOLVED",
        "unresolved_reasons": [] if mappings else sorted(set(original_reasons)),
    }
    return {
        "claim_boundary": _ROW_LEVEL_STRICT_SUBSET_CLAIM_BOUNDARY,
        "mappings": mappings,
        "receipt": receipt,
        "width_seal": {
            **seal_material,
            "seal_id": "fasrlssv1:seal:" + canonical_json_sha256_v1(seal_material),
        },
    }


def _extract_table_records(
    *,
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    region: Mapping[str, Any],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    table, adjacent_page_endpoint_first_receipt = (
        _project_adjacent_page_endpoint_first_continuation_from_page_map(
            table,
            section=section,
            region=region,
            page_json_by_version=page_json_by_version,
            compiled_specs=compiled_specs,
        )
    )
    table, trailing_owner_heading_receipt = (
        _project_trailing_owner_heading_from_page_map(
            table,
            section=section,
            region=region,
            page_json_by_version=page_json_by_version,
            compiled_specs=compiled_specs,
        )
    )
    table, leading_implicit_cost_branch_receipt = _project_leading_implicit_cost_branch(
        table, compiled_specs=compiled_specs
    )
    table, endpoint_first_layout_receipt = _project_endpoint_first_table(
        table, compiled_specs=compiled_specs
    )
    table, ordered_branch_scope_receipt = _project_ordered_branch_scope(
        table, compiled_specs=compiled_specs
    )
    table, ordered_dated_endpoint_receipt = _project_ordered_dated_endpoints(
        table, compiled_specs=compiled_specs
    )
    classification = classify_gemini_json_fixed_asset_rollforward_table_v1(
        section, table, compiled_specs=compiled_specs
    )
    if trailing_owner_heading_receipt is not None:
        classification = {
            **classification,
            "trailing_owner_heading_receipt": trailing_owner_heading_receipt,
        }
    reasons = list(classification["reasons"])
    if not classification["complete"]:
        reasons.append("CURRENT_TABLE_CLASSIFICATION_IS_NOT_COMPLETE")
    unit_axis = _resolve_missing_local_unit_from_balance_sheet_owner_vector(
        table=table,
        classification=classification,
        local_unit_axis=_unit_axis(table, compiled_specs=compiled_specs),
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
    )
    reasons.extend(unit_axis["reasons"])
    if not unit_axis["complete"]:
        reasons.append("CURRENT_TABLE_MONEY_UNIT_IS_NOT_COMPLETE")
    columns = table.get("columns")
    rows = table.get("rows")
    if type(columns) is not list or type(rows) is not list:
        raise _error("fixed-asset current table axes are invalid")
    money_ordinals = classification["money_column_ordinals"]
    total_ordinal = (
        classification["total_column_ordinals"][0]
        if classification["total_column_ordinals"]
        else None
    )
    if total_ordinal is None:
        if classification.get("cropped_total_complete_asset_frontier_binding") is not None:
            return _extract_cropped_total_complete_asset_frontier(
                table=table,
                region=region,
                classification=classification,
                unit_axis=unit_axis,
                compiled_specs=compiled_specs,
            )
        return {
            "classification": classification,
            "mappings": [],
            "reasons": sorted(set(reasons)),
            "subtotal_collapse": None,
            "table_receipt": None,
            "unit_axis": unit_axis,
            "width_seal": None,
        }
    money_ids = [f"c{ordinal}" for ordinal in money_ordinals]
    total_id = f"c{total_ordinal}"
    records = []
    source_only_control_records = []
    source_only_row_receipts = []
    branch_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    row_by_id = {}
    for order_ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict:
            reasons.append("SOURCE_ROW_IS_NOT_AN_OBJECT")
            continue
        source_ordinal = row.get("__source_ordinal", order_ordinal)
        source_row_id = row.get("__source_row_id", f"r{source_ordinal}")
        row_id = row.get("__engine_row_id", f"r{order_ordinal}")
        source_page_json_version_id = row.get(
            "__source_page_json_version_id", region["page_json_version_id"]
        )
        source_section_id = row.get("__source_section_id", region["section_id"])
        source_table_id = row.get("__source_table_id", region["table_id"])
        if (
            type(source_ordinal) is not int
            or source_ordinal <= 0
            or type(source_row_id) is not str
            or not source_row_id
            or type(row_id) is not str
            or not row_id
            or type(source_page_json_version_id) is not str
            or _PAGE_VERSION.fullmatch(source_page_json_version_id) is None
            or type(source_section_id) is not str
            or _SECTION_ID.fullmatch(source_section_id) is None
            or type(source_table_id) is not str
            or _TABLE_ID.fullmatch(source_table_id) is None
        ):
            reasons.append("SOURCE_ROW_PROJECTION_IDENTITY_INVALID")
            continue
        if any(
            _supplemental_row_matches(
                row,
                disclosure,
                table=table,
                compiled_specs=compiled_specs,
            )
            for disclosure in compiled_specs["evaluation"]["supplemental_disclosure_roles"]
        ):
            continue
        if _source_only_row_matches(row, compiled_specs=compiled_specs):
            source_only_row_receipts.append(
                {
                    "disposition": "SOURCE_ONLY_NO_SCHEMA_ROLE",
                    "label_exact": row.get("label_exact"),
                    "row_id": source_row_id,
                    "source_ordinal": source_ordinal,
                }
            )
            continue
        source_only_control_role = _source_only_carrying_control_role(
            row, compiled_specs=compiled_specs
        )
        if source_only_control_role == "GROUP":
            continue
        layout = _branch_layout_for_row(row, compiled_specs=compiled_specs)
        if source_only_control_role is not None:
            values = row.get("values_exact")
            if type(values) is not list or len(values) != len(columns):
                reasons.append(f"SOURCE_ROW_CELL_AXIS_INVALID:r{source_ordinal}")
                continue
            cells = {}
            try:
                for ordinal in money_ordinals:
                    column_id = f"c{ordinal}"
                    cells[column_id] = _money(
                        values[ordinal - 1],
                        source_locator={
                            "column_id": column_id,
                            "page_json_version_id": source_page_json_version_id,
                            "row_id": source_row_id,
                            "section_id": source_section_id,
                            "table_id": source_table_id,
                        },
                    )
            except GeminiJsonFixedAssetRollforwardFamilyV1Error:
                reasons.append(f"MONEY_CELL_INVALID:{row_id}")
                continue
            if all(cell["state"] == "BLANK" for cell in cells.values()):
                continue
            control_record = {
                "cells": cells,
                "label_exact": row.get("label_exact"),
                "role": source_only_control_role,
                "row_id": row_id,
                "source_row_id": source_row_id,
                "source_ordinal": source_ordinal,
                "source_order_ordinal": order_ordinal,
            }
            source_only_control_records.append(control_record)
            row_by_id[row_id] = control_record
            continue
        if layout is None or row.get("row_kind") == "GROUP":
            continue
        role = _role_for_row(row, layout, compiled_specs=compiled_specs)
        if role is None:
            reasons.append(f"UNCLASSIFIED_NUMERIC_ROW:r{source_ordinal}")
            continue
        values = row.get("values_exact")
        if type(values) is not list or len(values) != len(columns):
            reasons.append(f"SOURCE_ROW_CELL_AXIS_INVALID:r{source_ordinal}")
            continue
        cells = {}
        try:
            for ordinal in money_ordinals:
                column_id = f"c{ordinal}"
                cells[column_id] = _money(
                    values[ordinal - 1],
                    source_locator={
                        "column_id": column_id,
                        "page_json_version_id": source_page_json_version_id,
                        "row_id": source_row_id,
                        "section_id": source_section_id,
                        "table_id": source_table_id,
                    },
                )
        except GeminiJsonFixedAssetRollforwardFamilyV1Error:
            reasons.append(f"MONEY_CELL_INVALID:{row_id}")
            continue
        if all(cell["state"] == "BLANK" for cell in cells.values()):
            continue
        record = {
            "branch_role": layout["branch_role"],
            "cells": cells,
            "flattened_child": _flattened_child(row),
            "hierarchy_path_exact": canonical_clone_v1(
                row.get("__source_hierarchy_path_exact", row.get("hierarchy_path_exact"))
            ),
            "label_exact": row.get("__source_label_exact", row.get("label_exact")),
            "role": role,
            "row_id": row_id,
            "row_kind": row.get("row_kind"),
            "source_row_id": source_row_id,
            "source_ordinal": source_ordinal,
            "source_order_ordinal": order_ordinal,
        }
        records.append(record)
        branch_records[layout["branch_role"]].append(record)
        row_by_id[row_id] = record
    direct_role_fallback_receipts = []
    branch_layout_by_role = {
        item["branch_role"]: item for item in compiled_specs["evaluation"]["branch_layouts"]
    }
    for source_role, fallback_role in compiled_specs["evaluation"][
        "direct_role_fallback_by_role"
    ].items():
        source_records = [record for record in records if record["role"] == source_role]
        for branch_role in {record["branch_role"] for record in source_records}:
            branch_sources = [
                record for record in source_records if record["branch_role"] == branch_role
            ]
            if any(
                record["branch_role"] == branch_role and record["role"] == fallback_role
                for record in records
            ):
                continue
            layout = branch_layout_by_role[branch_role]
            for record in branch_sources:
                if record["flattened_child"] or _visible_subtotal_ancestor_roles(
                    record, layout, compiled_specs=compiled_specs
                ):
                    continue
                record["role"] = fallback_role
                direct_role_fallback_receipts.append(
                    {
                        "fallback_role": fallback_role,
                        "reason": "DIRECT_SOURCE_ROLE_WITH_NO_SEPARATE_FALLBACK_ROLE_POPULATION",
                        "row_id": record["row_id"],
                        "source_role": source_role,
                    }
                )
    block_by_subtotal: dict[str, list[str]] = {}
    parent_by_child: dict[str, str] = {}
    direct_by_branch: dict[str, list[str]] = defaultdict(list)
    blank_subtotal_heading_receipts = []
    same_role_subtotal_child_receipts = []
    for branch_role, branch_axis in branch_records.items():
        layout = branch_layout_by_role[branch_role]
        current_subtotal = None
        for record in branch_axis:
            visible_subtotal_ancestor_roles = _visible_subtotal_ancestor_roles(
                record, layout, compiled_specs=compiled_specs
            )
            is_child = bool(visible_subtotal_ancestor_roles)
            # A source-visible numeric subtotal establishes its own frontier
            # even when a flattened hierarchy path repeats its label.  The
            # path is structural evidence, not evidence that the subtotal is
            # a child of itself.
            if (
                record["role"] in layout["subtotal_roles"]
                and is_child
                and current_subtotal is not None
                and current_subtotal["role"] in visible_subtotal_ancestor_roles
            ):
                parent_by_child[record["row_id"]] = current_subtotal["row_id"]
                block_by_subtotal[current_subtotal["row_id"]].append(record["row_id"])
                same_role_subtotal_child_receipts.append(
                    {
                        "disposition": "SOURCE_ONLY_CHILD_CORROBORATES_VISIBLE_SUBTOTAL",
                        "row_id": record["row_id"],
                        "subtotal_row_id": current_subtotal["row_id"],
                        "subtotal_role": record["role"],
                    }
                )
                continue
            if record["role"] in layout["subtotal_roles"]:
                current_subtotal = record
                block_by_subtotal.setdefault(record["row_id"], [])
                direct_by_branch[branch_role].append(record["row_id"])
                continue
            if is_child:
                if (
                    current_subtotal is not None
                    and current_subtotal["role"] in visible_subtotal_ancestor_roles
                ):
                    parent_by_child[record["row_id"]] = current_subtotal["row_id"]
                    block_by_subtotal[current_subtotal["row_id"]].append(record["row_id"])
                    continue
                if (
                    compiled_specs["evaluation"].get("blank_subtotal_heading_policy")
                    == "VISIBLE_BLANK_SUBTOTAL_HEADING_CHILDREN_PROMOTE_TO_DIRECT_MOVEMENTS"
                    and len(visible_subtotal_ancestor_roles) == 1
                ):
                    visible_subtotal_role = next(iter(visible_subtotal_ancestor_roles))
                    current_subtotal = None
                    direct_by_branch[branch_role].append(record["row_id"])
                    blank_subtotal_heading_receipts.append(
                        {
                            "branch_role": branch_role,
                            "reason": (
                                "VISIBLE_BLANK_SUBTOTAL_HEADING_HAS_NO_NUMERIC_"
                                "SUBTOTAL_ROW"
                            ),
                            "row_id": record["row_id"],
                            "visible_subtotal_role": visible_subtotal_role,
                        }
                    )
                    continue
                if current_subtotal is None:
                    reasons.append(
                        f"VISIBLE_SUBTOTAL_CHILD_HAS_NO_PRECEDING_SUBTOTAL:{record['row_id']}"
                    )
                    continue
                reasons.append(
                    f"VISIBLE_SUBTOTAL_CHILD_PRECEDING_SUBTOTAL_ROLE_MISMATCH:{record['row_id']}"
                )
                continue
            current_subtotal = None
            if record["role"] not in {layout["opening_role"], layout["ending_role"]}:
                direct_by_branch[branch_role].append(record["row_id"])
    equations = []
    horizontal_records = [*records, *source_only_control_records]
    implicit_single_asset_total = classification["total_column_binding_kind"] in {
        "IMPLICIT_SINGLE_RECOGNIZED_ASSET_MONEY_COLUMN",
        "IMPLICIT_SINGLE_RECOGNIZED_ASSET_CURRENT_PERIOD_COLUMN",
    }
    preserve_partial_details = bool(
        compiled_specs["evaluation"].get("partial_detail_total_policy")
    )
    omitted_horizontal_rows = []
    equation_only_zero_row_ids = set()
    for record in horizontal_records:
        if implicit_single_asset_total:
            continue
        detail_ids = list(money_ids[:-1])
        blank_detail_ids = [
            column_id
            for column_id in detail_ids
            if record["cells"][column_id]["state"] == "BLANK"
        ]
        if preserve_partial_details and record["cells"][total_id]["state"] == "BLANK":
            numeric_details = [
                record["cells"][column_id]["coefficient"]
                for column_id in detail_ids
                if record["cells"][column_id]["state"] != "BLANK"
            ]
            exact_visible_net_zero = bool(
                not blank_detail_ids and numeric_details and sum(numeric_details) == 0
            )
            no_nonzero_visible_detail = bool(
                blank_detail_ids
                and numeric_details
                and all(coefficient == 0 for coefficient in numeric_details)
            )
            if exact_visible_net_zero or no_nonzero_visible_detail:
                equation_only_zero_row_ids.add(record["row_id"])
                omitted_horizontal_rows.append(
                    {
                        "disposition": (
                            "SOURCE_ONLY_DERIVED_EXACT_NET_ZERO_NO_MAPPING"
                            if exact_visible_net_zero
                            else (
                                "SOURCE_ONLY_NO_TOTAL_NO_NONZERO_VISIBLE_DETAIL_"
                                "VERTICAL_CLOSURE_REQUIRED_NO_MAPPING"
                            )
                        ),
                        "preserved_blank_column_ids": (
                            [total_id]
                            if exact_visible_net_zero
                            else [*blank_detail_ids, total_id]
                        ),
                        "row_id": record["row_id"],
                    }
                )
                continue
            # Keep the established all-equation right-edge relocation path
            # available for non-zero rows.  That path remains fail-closed: an
            # actual blank total is not interpreted as zero and can close only
            # when the unique projection satisfies every exact equation.
            legacy_right_edge_candidate = bool(
                not blank_detail_ids
                and len(detail_ids) >= 2
                and record["cells"][detail_ids[-1]]["coefficient"]
                == sum(
                    record["cells"][column_id]["coefficient"]
                    for column_id in detail_ids[:-1]
                )
            )
            if not legacy_right_edge_candidate:
                reasons.append(
                    "SOURCE_TOTAL_BLANK_WITH_NONZERO_OR_INCOMPLETE_DETAILS:"
                    + record["row_id"]
                )
                continue
        if preserve_partial_details and blank_detail_ids:
            omitted_horizontal_rows.append(
                {
                    "disposition": "SOURCE_VISIBLE_TOTAL_CONTROLS_VERTICAL_ONLY",
                    "preserved_blank_column_ids": blank_detail_ids,
                    "row_id": record["row_id"],
                }
            )
            continue
        detail_numeric = [
            column_id
            for column_id in money_ids[:-1]
            if record["cells"][column_id]["state"] != "BLANK"
        ]
        omitted_candidate = None
        if detail_numeric:
            rightmost = detail_numeric[-1]
            preceding = [
                column_id for column_id in detail_numeric if int(column_id[1:]) < int(rightmost[1:])
            ]
            rightmost_coefficient = record["cells"][rightmost]["coefficient"]
            if (
                preceding
                and rightmost_coefficient != 0
                and rightmost_coefficient
                == sum(record["cells"][column_id]["coefficient"] for column_id in preceding)
                and all(
                    record["cells"][f"c{ordinal}"]["state"] == "BLANK"
                    for ordinal in money_ordinals
                    if int(rightmost[1:]) < ordinal < total_ordinal
                )
                and (
                    record["cells"][total_id]["state"] == "BLANK"
                    or (
                        record["cells"][total_id]["coefficient"] == rightmost_coefficient
                        and record["cells"][total_id]["state"]
                        == record["cells"][rightmost]["state"]
                        and record["cells"][total_id]["source_text"]
                        == record["cells"][rightmost]["source_text"]
                    )
                )
            ):
                omitted_candidate = rightmost
        term_ids = [column_id for column_id in detail_numeric if column_id != omitted_candidate]
        if not term_ids:
            reasons.append(f"HORIZONTAL_EQUATION_HAS_NO_VISIBLE_DETAIL_TERM:{record['row_id']}")
            continue
        equations.append(
            {
                "axis": "HORIZONTAL_ROW",
                "equation_id": f"horizontal:{record['row_id']}",
                "result": {"column_id": total_id, "row_id": record["row_id"]},
                "terms": [
                    {"column_id": column_id, "multiplier": 1, "row_id": record["row_id"]}
                    for column_id in term_ids
                ],
            }
        )
    if equation_only_zero_row_ids:
        for branch_role in list(direct_by_branch):
            direct_by_branch[branch_role] = [
                row_id
                for row_id in direct_by_branch[branch_role]
                if row_id not in equation_only_zero_row_ids
            ]
    for subtotal_id, child_ids in block_by_subtotal.items():
        if not child_ids:
            continue
        for column_id in money_ids:
            involved = [row_by_id[subtotal_id], *(row_by_id[child_id] for child_id in child_ids)]
            if any(item["cells"][column_id]["state"] == "BLANK" for item in involved):
                continue
            equations.append(
                {
                    "axis": "VERTICAL_ROLLFORWARD",
                    "equation_id": f"subtotal:{subtotal_id}:{column_id}",
                    "result": {"column_id": column_id, "row_id": subtotal_id},
                    "terms": [
                        {"column_id": column_id, "multiplier": 1, "row_id": child_id}
                        for child_id in child_ids
                    ],
                }
            )
    signed_layouts = [
        item
        for item in compiled_specs["evaluation"]["branch_layouts"]
        if item["rollforward_kind"] == "SIGNED_ADDITIVE"
    ]
    carrying_layout = next(
        (
            item
            for item in compiled_specs["evaluation"]["branch_layouts"]
            if item["rollforward_kind"] == "COST_AND_DEPRECIATION_CONTROL"
        ),
        None,
    )
    endpoint_by_role: dict[str, list[str]] = defaultdict(list)
    for record in records:
        endpoint_by_role[record["role"]].append(record["row_id"])
    optional_absent_branch_roles = (
        set(compiled_specs["evaluation"]["component_policy"]["optional_absent_branch_roles"])
        if compiled_specs["evaluation"].get("component_policy") is not None
        else set()
    )
    observed_branch_roles = set(branch_records)
    for layout in compiled_specs["evaluation"]["branch_layouts"]:
        if (
            layout["branch_role"] in optional_absent_branch_roles
            and layout["branch_role"] not in observed_branch_roles
        ):
            continue
        for role in (layout["opening_role"], layout["ending_role"]):
            if len(endpoint_by_role[role]) != 1:
                reasons.append(f"EXACT_ONE_BRANCH_ENDPOINT_REQUIRED:{role}")
        opening_ids = endpoint_by_role[layout["opening_role"]]
        ending_ids = endpoint_by_role[layout["ending_role"]]
        if len(opening_ids) == len(ending_ids) == 1:
            opening_ordinal = row_by_id[opening_ids[0]]["source_order_ordinal"]
            ending_ordinal = row_by_id[ending_ids[0]]["source_order_ordinal"]
            movement_ordinals = [
                record["source_order_ordinal"]
                for record in branch_records[layout["branch_role"]]
                if record["role"] not in {layout["opening_role"], layout["ending_role"]}
            ]
            if not (
                opening_ordinal < ending_ordinal
                and all(opening_ordinal < ordinal < ending_ordinal for ordinal in movement_ordinals)
            ):
                reasons.append(
                    f"BRANCH_SOURCE_ORDER_OPENING_MOVEMENTS_ENDING_INVALID:{layout['branch_role']}"
                )
    movement_direction_receipts = []
    for layout in signed_layouts:
        if endpoint_first_layout_receipt is not None:
            continue
        if (
            layout["branch_role"] in optional_absent_branch_roles
            and layout["branch_role"] not in observed_branch_roles
        ):
            continue
        opening_ids = endpoint_by_role[layout["opening_role"]]
        ending_ids = endpoint_by_role[layout["ending_role"]]
        if len(opening_ids) == len(ending_ids) == 1:
            endpoint_coefficients = [
                row_by_id[row_id]["cells"][total_id]["coefficient"]
                for row_id in (opening_ids[0], ending_ids[0])
            ]
            if all(type(value) is int and value >= 0 for value in endpoint_coefficients):
                branch_balance_sign = 1
            elif all(type(value) is int and value <= 0 for value in endpoint_coefficients):
                branch_balance_sign = -1
            else:
                branch_balance_sign = None
                reasons.append(
                    f"BRANCH_ENDPOINT_SIGN_CONVENTION_IS_MIXED_OR_BLANK:{layout['branch_role']}"
                )
            movement_terms = []
            if branch_balance_sign is not None:
                for row_id in direct_by_branch[layout["branch_role"]]:
                    multiplier, direction_receipt = _movement_equation_multiplier(
                        row_by_id[row_id],
                        total_id=total_id,
                        branch_balance_sign=branch_balance_sign,
                        compiled_specs=compiled_specs,
                    )
                    movement_direction_receipts.append(direction_receipt)
                    movement_terms.append(
                        {"column_id": total_id, "multiplier": multiplier, "row_id": row_id}
                    )
            if branch_balance_sign is None:
                continue
            equations.append(
                {
                    "axis": "VERTICAL_ROLLFORWARD",
                    "equation_id": f"branch:{layout['branch_role']}",
                    "result": {"column_id": total_id, "row_id": ending_ids[0]},
                    "terms": [
                        {"column_id": total_id, "multiplier": 1, "row_id": opening_ids[0]},
                        *movement_terms,
                    ],
                }
            )
    if carrying_layout is not None and all(
        len(endpoint_by_role[layout[endpoint]]) == 1
        for layout in [
            *[
                item
                for item in signed_layouts
                if item["branch_role"] in observed_branch_roles
                or item["branch_role"] not in optional_absent_branch_roles
            ],
            carrying_layout,
        ]
        for endpoint in ("opening_role", "ending_role")
    ):
        cost_layout = next(
            layout for layout in signed_layouts if layout["opening_role"].startswith("COST_")
        )
        depreciation_layout = next(
            layout for layout in signed_layouts if layout["opening_role"].startswith("DEP_")
        )
        depreciation_absent = bool(
            depreciation_layout["branch_role"] in optional_absent_branch_roles
            and depreciation_layout["branch_role"] not in observed_branch_roles
        )
        dep_values = (
            [0, 0]
            if depreciation_absent
            else [
                row_by_id[endpoint_by_role[depreciation_layout[key]][0]]["cells"][total_id][
                    "coefficient"
                ]
                for key in ("opening_role", "ending_role")
            ]
        )
        if depreciation_absent:
            depreciation_multiplier = None
        elif all(type(value) is int and value <= 0 for value in dep_values):
            depreciation_multiplier = 1
        elif all(type(value) is int and value >= 0 for value in dep_values):
            depreciation_multiplier = -1
        else:
            depreciation_multiplier = None
            reasons.append("DEPRECIATION_ENDPOINT_SIGN_CONVENTION_IS_MIXED_OR_BLANK")
        if depreciation_absent or depreciation_multiplier is not None:
            for endpoint in ("opening_role", "ending_role"):
                carry_role = carrying_layout[endpoint]
                cost_role = cost_layout[endpoint]
                depreciation_role = depreciation_layout[endpoint]
                equations.append(
                    {
                        "axis": "VERTICAL_ROLLFORWARD",
                        "equation_id": f"carrying:{carry_role}",
                        "result": {
                            "column_id": total_id,
                            "row_id": endpoint_by_role[carry_role][0],
                        },
                        "terms": [
                            {
                                "column_id": total_id,
                                "multiplier": 1,
                                "row_id": endpoint_by_role[cost_role][0],
                            },
                            *(
                                []
                                if depreciation_absent
                                else [
                                    {
                                        "column_id": total_id,
                                        "multiplier": depreciation_multiplier,
                                        "row_id": endpoint_by_role[depreciation_role][0],
                                    }
                                ]
                            ),
                        ],
                    }
                )
    if (
        compiled_specs["evaluation"].get("source_only_carrying_control") is not None
        and source_only_control_records
    ):
        control_by_role: dict[str, list[str]] = defaultdict(list)
        for record in source_only_control_records:
            control_by_role[record["role"]].append(record["row_id"])
        for role in ("SOURCE_ONLY_CARRY_OPENING", "SOURCE_ONLY_CARRY_ENDING"):
            if len(control_by_role[role]) != 1:
                reasons.append(f"EXACT_ONE_SOURCE_ONLY_CARRYING_ENDPOINT_REQUIRED:{role}")
        if all(
            len(endpoint_by_role[layout[endpoint]]) == 1
            for layout in signed_layouts
            for endpoint in ("opening_role", "ending_role")
        ) and all(
            len(control_by_role[role]) == 1
            for role in ("SOURCE_ONLY_CARRY_OPENING", "SOURCE_ONLY_CARRY_ENDING")
        ):
            cost_layout = next(
                layout for layout in signed_layouts if layout["opening_role"].startswith("COST_")
            )
            depreciation_layout = next(
                layout for layout in signed_layouts if layout["opening_role"].startswith("DEP_")
            )
            dep_values = [
                row_by_id[endpoint_by_role[depreciation_layout[key]][0]]["cells"][total_id][
                    "coefficient"
                ]
                for key in ("opening_role", "ending_role")
            ]
            if all(type(value) is int and value <= 0 for value in dep_values):
                source_only_depreciation_multiplier = 1
            elif all(type(value) is int and value >= 0 for value in dep_values):
                source_only_depreciation_multiplier = -1
            else:
                source_only_depreciation_multiplier = None
                reasons.append("SOURCE_ONLY_DEPRECIATION_ENDPOINT_SIGN_IS_MIXED_OR_BLANK")
            if source_only_depreciation_multiplier is not None:
                for endpoint, control_role in (
                    ("opening_role", "SOURCE_ONLY_CARRY_OPENING"),
                    ("ending_role", "SOURCE_ONLY_CARRY_ENDING"),
                ):
                    equations.append(
                        {
                            "axis": "VERTICAL_ROLLFORWARD",
                            "equation_id": f"source-only-carrying:{control_role}",
                            "result": {
                                "column_id": total_id,
                                "row_id": control_by_role[control_role][0],
                            },
                            "terms": [
                                {
                                    "column_id": total_id,
                                    "multiplier": 1,
                                    "row_id": endpoint_by_role[cost_layout[endpoint]][0],
                                },
                                {
                                    "column_id": total_id,
                                    "multiplier": source_only_depreciation_multiplier,
                                    "row_id": endpoint_by_role[depreciation_layout[endpoint]][0],
                                },
                            ],
                        }
                    )
    pre_width_reasons = tuple(reasons)
    width_input = None
    width_seal = None
    if not reasons:
        seal_records = [*records, *source_only_control_records]
        if implicit_single_asset_total:
            width_seal = _build_single_asset_column_vertical_seal(
                records=seal_records,
                equations=equations,
                total_id=total_id,
                region=region,
                unit_id=unit_axis["canonical_unit"],
                binding_kind=classification["total_column_binding_kind"],
                compiled_specs=compiled_specs,
            )
        elif preserve_partial_details and omitted_horizontal_rows:
            width_seal = _build_preserved_blank_explicit_total_seal(
                records=seal_records,
                equations=equations,
                money_ids=money_ids,
                total_id=total_id,
                omitted_horizontal_rows=omitted_horizontal_rows,
                region=region,
                unit_id=unit_axis["canonical_unit"],
                compiled_specs=compiled_specs,
            )
        else:
            authority_sha256 = canonical_json_sha256_v1(compiled_specs["evaluation"])
            width_input = {
                "columns": [
                    {
                        "column_id": column_id,
                        "column_kind": "TOTAL" if column_id == total_id else "DETAIL",
                        "column_ordinal": ordinal,
                    }
                    for ordinal, column_id in enumerate(money_ids)
                ],
                "equation_inventory": build_accounting_equation_inventory_manifest_v1(
                    equations,
                    authority_kind="PINNED_CONFIG",
                    authority_ref=(
                        compiled_specs["topology"]["family_id"]
                        + ":"
                        + EVALUATION_FORMAT_VERSION
                    ),
                    authority_sha256=authority_sha256,
                ),
                "equations": equations,
                "period_id": region["period_end_date"] or "CURRENT_PERIOD",
                "rows": [
                    {
                        "cells": canonical_clone_v1(record["cells"]),
                        "row_id": record["row_id"],
                        "row_kind": "DATA",
                        "row_ordinal": ordinal,
                    }
                    for ordinal, record in enumerate(seal_records)
                ],
                "table_id": region["table_id"],
                "unit_id": unit_axis["canonical_unit"],
            }
            width_seal = build_accounting_row_width_total_column_seal_v1(width_input)
        width_seal = _project_bounded_source_presentation_rounding_seal(
            width_seal,
            unit_id=unit_axis["canonical_unit"],
            compiled_specs=compiled_specs,
        )
        if width_seal["status"] == "UNRESOLVED":
            reasons.extend(width_seal["unresolved_reasons"])
    effective_by_row = {}
    if width_seal is not None:
        effective_by_row = {
            row["row_id"]: row["cells"] for row in width_seal["effective_projection"]["rows"]
        }
    collapse_input_rows = []
    collapse_mappings = []
    collapse_frontiers = []
    prior_branch = None
    for record in records:
        branch_role = record["branch_role"]
        if prior_branch is not None and prior_branch != branch_role:
            collapse_input_rows.append(
                {
                    "cells": {
                        total_id: {
                            "coefficient": None,
                            "source_locator": {"synthetic_reset": branch_role},
                            "source_text": "",
                            "state": "BLANK",
                        }
                    },
                    "hierarchy_level": 0,
                    "money_lane_ids": [total_id],
                    "period_id": region["period_end_date"] or "CURRENT_PERIOD",
                    "root_id": branch_role,
                    "row_id": f"reset:{branch_role}",
                    "row_kind": "RESET",
                    "row_ordinal": len(collapse_input_rows),
                    "source_parent_row_id": None,
                    "table_id": region["table_id"],
                    "unit_id": unit_axis["canonical_unit"] or "UNRESOLVED_UNIT",
                }
            )
        prior_branch = branch_role
        children = block_by_subtotal.get(record["row_id"], [])
        parent_id = parent_by_child.get(record["row_id"])
        if children:
            block_records = [record, *(row_by_id[row_id] for row_id in children)]
            lane_ids = [
                column_id
                for column_id in money_ids
                if all(
                    _effective_blank(
                        effective_by_row.get(item["row_id"], item["cells"]).get(column_id),
                        fallback=item["cells"][column_id],
                    )["state"]
                    != "BLANK"
                    for item in block_records
                )
            ]
        elif parent_id is not None:
            subtotal = row_by_id[parent_id]
            siblings = block_by_subtotal[parent_id]
            block_records = [subtotal, *(row_by_id[row_id] for row_id in siblings)]
            lane_ids = [
                column_id
                for column_id in money_ids
                if all(
                    _effective_blank(
                        effective_by_row.get(item["row_id"], item["cells"]).get(column_id),
                        fallback=item["cells"][column_id],
                    )["state"]
                    != "BLANK"
                    for item in block_records
                )
            ]
        else:
            lane_ids = [total_id]
        lane_ids = lane_ids or [total_id]
        source_parent = (
            (f"root:{branch_role}" if record["flattened_child"] else parent_id)
            if parent_id is not None
            else f"root:{branch_role}"
        )
        collapse_input_rows.append(
            {
                "cells": {
                    column_id: _effective_blank(
                        effective_by_row.get(record["row_id"], record["cells"]).get(column_id),
                        fallback=record["cells"][column_id],
                    )
                    for column_id in lane_ids
                },
                "hierarchy_level": 2 if parent_id is not None else 1,
                "money_lane_ids": lane_ids,
                "period_id": region["period_end_date"] or "CURRENT_PERIOD",
                "root_id": branch_role,
                "row_id": record["row_id"],
                "row_kind": (
                    "DETAIL" if parent_id is not None else ("SUBTOTAL" if children else "PEER")
                ),
                "row_ordinal": len(collapse_input_rows),
                "source_parent_row_id": source_parent,
                "table_id": region["table_id"],
                "unit_id": unit_axis["canonical_unit"] or "UNRESOLVED_UNIT",
            }
        )
        mapping_id = f"mapping:{record['row_id']}:{record['role']}"
        collapse_mappings.append(
            {"mapping_id": mapping_id, "role_id": record["role"], "row_id": record["row_id"]}
        )
        if children:
            collapse_frontiers.append(
                {
                    "equation_id": f"branch:{branch_role}",
                    "mapping_ids": [mapping_id],
                    "subtotal_row_id": record["row_id"],
                }
            )
    collapse_source = {
        "equation_frontiers": collapse_frontiers,
        "mappings": collapse_mappings,
        "rows": collapse_input_rows,
    }
    subtotal_collapse = None
    if effective_by_row and collapse_input_rows:
        subtotal_collapse = build_ordered_visible_subtotal_block_collapse_v1(collapse_source)
        if subtotal_collapse["status"] == "UNRESOLVED":
            reasons.extend(subtotal_collapse["unresolved_reasons"])
    records_by_role: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if effective_by_row:
        for record in records:
            parent_id = parent_by_child.get(record["row_id"])
            if (
                parent_id is not None
                and row_by_id[parent_id]["role"] == record["role"]
            ):
                continue
            cell = _effective_blank(
                effective_by_row[record["row_id"]].get(total_id),
                fallback=record["cells"][total_id],
            )
            if cell["state"] != "BLANK":
                records_by_role[record["role"]].append({"cell": cell, "record": record})
    singleton_declared_subtotal_receipts = []
    if effective_by_row and not reasons:
        for source_role, subtotal_role in compiled_specs["evaluation"][
            "singleton_declared_subtotal_by_source_role"
        ].items():
            source_layouts = [
                layout
                for layout in compiled_specs["evaluation"]["branch_layouts"]
                if source_role
                in compiled_specs["output_roles_by_branch"][layout["branch_role"]]
            ]
            if not source_layouts:
                continue
            if len(source_layouts) != 1:
                raise _error("compiled singleton declared-subtotal branch is ambiguous")
            branch_role = source_layouts[0]["branch_role"]
            source_records = [
                row_by_id[row_id]
                for row_id in direct_by_branch[branch_role]
                if row_by_id[row_id]["role"] == source_role
            ]
            if len(source_records) != 1 or records_by_role.get(subtotal_role):
                continue
            source_record = source_records[0]
            if any(
                source_record["cells"][column_id]["state"] == "BLANK"
                for column_id in money_ids
            ):
                continue
            branch_equations = [
                equation
                for equation in equations
                if equation.get("axis") == "VERTICAL_ROLLFORWARD"
                and equation.get("equation_id") == f"branch:{branch_role}"
                and any(
                    term.get("row_id") == source_record["row_id"]
                    for term in equation.get("terms", [])
                )
            ]
            if len(branch_equations) != 1 or not (
                _equation_closes_on_fully_observed_source_cells(
                    branch_equations[0], row_by_id=row_by_id
                )
            ):
                continue
            raw_source_cell = canonical_clone_v1(source_record["cells"][total_id])
            records_by_role[subtotal_role].append(
                {
                    "cell": {
                        "coefficient": raw_source_cell["coefficient"],
                        "source_locator": canonical_clone_v1(raw_source_cell["source_locator"]),
                        "source_text": None,
                        "state": "DERIVED_EXACT_SINGLETON_DECLARED_SUBTOTAL",
                    },
                    "record": source_record,
                    "source_cell": raw_source_cell,
                }
            )
            singleton_declared_subtotal_receipts.append(
                {
                    "branch_equation_id": branch_equations[0]["equation_id"],
                    "disposition": (
                        "DERIVED_EXACT_SINGLETON_DIRECT_CHILD_IS_DECLARED_SUBTOTAL"
                    ),
                    "source_role": source_role,
                    "source_row_id": source_record["row_id"],
                    "subtotal_role": subtotal_role,
                }
            )
    mappings = []
    if not reasons:
        for role in compiled_specs["output_role_order"]:
            observations = records_by_role.get(role, [])
            if not observations:
                continue
            coefficient = sum(item["cell"]["coefficient"] for item in observations)
            source_refs = [
                {
                    "cell": canonical_clone_v1(item.get("source_cell", item["cell"])),
                    "hierarchy_path_exact": canonical_clone_v1(
                        item["record"]["hierarchy_path_exact"]
                    ),
                    "label_exact": item["record"]["label_exact"],
                    "row_id": item["record"]["source_row_id"],
                    "source_ordinal": item["record"]["source_ordinal"],
                }
                for item in observations
            ]
            row_id = (
                observations[0]["record"]["row_id"]
                if len(observations) == 1
                else "aggregate:" + role
            )
            material = {
                "bound_unit": unit_axis["canonical_unit"],
                "cell": {
                    "coefficient": coefficient,
                    "state": (
                        observations[0]["cell"]["state"]
                        if len(observations) == 1
                        else "AGGREGATED_EXACT_SAME_ROLE_SOURCE_ROWS"
                    ),
                },
                "period_date": region["period_end_date"],
                "report_norm_id": compiled_specs["bindings"][role],
                "role": role,
                "row_id": row_id,
                "source_refs": source_refs,
            }
            mappings.append(
                {
                    **material,
                    "item_mapping_id": "gjffarimv1:item:" + canonical_json_sha256_v1(material),
                }
            )
    row_level_strict_subset_receipt = None
    claim_boundary = CLAIM_BOUNDARY
    if (
        not mappings
        and reasons
        and not pre_width_reasons
        and compiled_specs["evaluation"].get("row_level_strict_subset_policy")
        == _ROW_LEVEL_STRICT_SUBSET_POLICY
        and type(width_seal) is dict
        and type(width_seal.get("raw_table_snapshot")) is dict
        and "NO_ALL_EQUATION_CLOSING_PROJECTION" in reasons
        and set(reasons)
        <= {
            "NO_ALL_EQUATION_CLOSING_PROJECTION",
            "VISIBLE_SUBTOTAL_SIGNED_SUM_MISMATCH",
        }
    ):
        strict_subset = _build_printed_total_row_level_strict_subset(
            records=records,
            row_by_id=row_by_id,
            equations=equations,
            total_id=total_id,
            region=region,
            unit_id=unit_axis["canonical_unit"],
            raw_projection=width_seal["raw_table_snapshot"],
            original_reasons=reasons,
            compiled_specs=compiled_specs,
        )
        if strict_subset["mappings"]:
            mappings = strict_subset["mappings"]
            width_seal = strict_subset["width_seal"]
            row_level_strict_subset_receipt = strict_subset["receipt"]
            claim_boundary = strict_subset["claim_boundary"]
            reasons = []
    table_receipt = {
        "classification": classification,
        "adjacent_page_endpoint_first_continuation_receipt": (
            adjacent_page_endpoint_first_receipt
        ),
        "blank_subtotal_heading_receipts": blank_subtotal_heading_receipts,
        "direct_role_fallback_receipts": direct_role_fallback_receipts,
        "endpoint_first_layout_receipt": endpoint_first_layout_receipt,
        "leading_implicit_cost_branch_receipt": leading_implicit_cost_branch_receipt,
        "equations": equations,
        "movement_direction_receipts": movement_direction_receipts,
        "omitted_horizontal_rows": omitted_horizontal_rows,
        "ordered_branch_scope_receipt": ordered_branch_scope_receipt,
        "ordered_dated_endpoint_receipt": ordered_dated_endpoint_receipt,
        "raw_row_inventory": [
            {
                "branch_role": record["branch_role"],
                "hierarchy_path_exact": canonical_clone_v1(record["hierarchy_path_exact"]),
                "label_exact": record["label_exact"],
                "role": record["role"],
                "row_id": record["row_id"],
                **(
                    {"source_row_id": record["source_row_id"]}
                    if record["source_row_id"] != record["row_id"]
                    else {}
                ),
                "source_ordinal": record["source_ordinal"],
            }
            for record in records
        ],
        "same_role_subtotal_child_receipts": same_role_subtotal_child_receipts,
        "singleton_declared_subtotal_receipts": (
            singleton_declared_subtotal_receipts
        ),
        "source_only_carrying_control": {
            "mapping_emitted": False,
            "policy": "SOURCE_ONLY_EXACT_ARITHMETIC_CONTROL_NO_SCHEMA_BINDING",
            "rows": [
                {
                    "label_exact": record["label_exact"],
                    "role": record["role"],
                    "row_id": record["row_id"],
                    "source_ordinal": record["source_ordinal"],
                }
                for record in source_only_control_records
            ],
        },
        "source_only_rows": source_only_row_receipts,
        "unit_axis": unit_axis,
        **(
            {"row_level_strict_subset_receipt": row_level_strict_subset_receipt}
            if row_level_strict_subset_receipt is not None
            else {}
        ),
    }
    return {
        "claim_boundary": claim_boundary,
        "classification": classification,
        "mappings": mappings,
        "reasons": sorted(set(reasons)),
        "subtotal_collapse": subtotal_collapse,
        "table_receipt": table_receipt,
        "unit_axis": unit_axis,
        "width_seal": width_seal,
    }


def _fragment_compiled_specs(compiled_specs: Mapping[str, Any], branch_role: str) -> dict[str, Any]:
    projected = canonical_clone_v1(compiled_specs)
    layout = next(
        item
        for item in projected["evaluation"]["branch_layouts"]
        if item["branch_role"] == branch_role
    )
    projected["evaluation"]["branch_layouts"] = [layout]
    projected["output_roles_by_branch"] = {
        branch_role: projected["output_roles_by_branch"][branch_role]
    }
    projected["recognized_roles_by_branch"] = {
        branch_role: projected["recognized_roles_by_branch"][branch_role]
    }
    projected["output_role_order"] = projected["output_roles_by_branch"][branch_role]
    return projected


def _summary_control_projection(
    *,
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    region: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    classification = _summary_control_classification(
        section, table, compiled_specs=compiled_specs
    ) or _statement_carrying_control_classification(section, table, compiled_specs=compiled_specs)
    reasons = []
    if classification is None:
        return {
            "classification": None,
            "mappings": [],
            "reasons": ["CURRENT_SUMMARY_CONTROL_CLASSIFICATION_DRIFTED"],
            "unit_axis": None,
        }
    unit_axis = _unit_axis(table, compiled_specs=compiled_specs)
    reasons.extend(unit_axis["reasons"])
    if not unit_axis["complete"]:
        reasons.append("CURRENT_SUMMARY_CONTROL_MONEY_UNIT_IS_NOT_COMPLETE")
    columns = table["columns"]
    rows = table["rows"]
    money_ordinals = classification["money_column_ordinals"]
    current_date = date.fromisoformat(region["period_end_date"])
    summary_policy = compiled_specs["evaluation"]["component_policy"]["summary_control"]
    relative_bindings = classification["period_receipt"].get("column_period_bindings")
    relative_axis = relative_bindings is not None
    role_by_ordinal = {}
    period_date_by_ordinal = {}
    source_kind_by_ordinal = {}
    period_axis_valid = True
    if relative_axis:
        expected_fields = {
            "column_header_exact",
            "column_ordinal",
            "period_date",
            "period_role",
            "source_kind",
        }
        if (
            type(relative_bindings) is not list
            or len(relative_bindings) != 2
            or any(
                type(binding) is not dict
                or set(binding) != expected_fields
                or type(binding["column_ordinal"]) is not int
                or not (0 < binding["column_ordinal"] <= len(columns))
                or type(binding["column_header_exact"]) is not str
                or type(binding["period_role"]) is not str
                or binding["period_date"] is not None
                and type(binding["period_date"]) is not str
                or binding["source_kind"]
                != "TYPED_BALANCE_SHEET_RELATIVE_PERIOD_COLUMN"
                for binding in relative_bindings
            )
        ):
            period_axis_valid = False
        else:
            role_by_ordinal = {
                binding["column_ordinal"]: binding["period_role"]
                for binding in relative_bindings
            }
            period_date_by_ordinal = {
                binding["column_ordinal"]: binding["period_date"]
                for binding in relative_bindings
            }
            source_kind_by_ordinal = {
                binding["column_ordinal"]: binding["source_kind"]
                for binding in relative_bindings
            }
            binding_by_role = {
                binding["period_role"]: binding for binding in relative_bindings
            }
            period_axis_valid = (
                set(role_by_ordinal) == set(money_ordinals)
                and set(role_by_ordinal.values())
                == {summary_policy["opening_role"], summary_policy["current_role"]}
                and all(
                    binding["column_header_exact"]
                    == _header_text(columns[binding["column_ordinal"] - 1])
                    for binding in relative_bindings
                )
                and binding_by_role[summary_policy["current_role"]]["period_date"]
                == current_date.isoformat()
                and binding_by_role[summary_policy["opening_role"]]["period_date"] is None
            )
        if not period_axis_valid:
            reasons.append("SUMMARY_CONTROL_CURRENT_COMPARATIVE_PERIOD_AXIS_INVALID")
    else:
        dates_by_ordinal = {
            ordinal: sorted(set(_surface_dates(_header_text(columns[ordinal - 1]))))
            for ordinal in money_ordinals
        }
        if any(len(axis) != 1 for axis in dates_by_ordinal.values()):
            period_axis_valid = False
        else:
            date_by_ordinal = {
                ordinal: axis[0] for ordinal, axis in dates_by_ordinal.items()
            }
            current_ordinals = [
                ordinal for ordinal, parsed in date_by_ordinal.items() if parsed == current_date
            ]
            comparative_ordinals = [
                ordinal for ordinal, parsed in date_by_ordinal.items() if parsed < current_date
            ]
            if len(current_ordinals) != 1 or len(comparative_ordinals) != 1:
                period_axis_valid = False
            else:
                role_by_ordinal = {
                    comparative_ordinals[0]: summary_policy["opening_role"],
                    current_ordinals[0]: summary_policy["current_role"],
                }
                period_date_by_ordinal = {
                    ordinal: parsed.isoformat() for ordinal, parsed in date_by_ordinal.items()
                }
        if not period_axis_valid:
            reasons.append("SUMMARY_CONTROL_CURRENT_COMPARATIVE_PERIOD_AXIS_INVALID")
    control_row_ordinal = classification["control_row_ordinal"]
    control_rows = [
        (control_row_ordinal, rows[control_row_ordinal - 1])
        if 0 < control_row_ordinal <= len(rows)
        else None
    ]
    if control_rows == [None] or type(control_rows[0][1]) is not dict:
        reasons.append("SUMMARY_CONTROL_SOURCE_ROW_IS_INVALID")
    observations = []
    detail_observations = []
    summary_equations = []
    if not reasons:
        row_ordinal, row = control_rows[0]
        values = row.get("values_exact")
        if type(values) is not list or len(values) != len(columns):
            reasons.append("SUMMARY_CONTROL_TOTAL_ROW_CELL_AXIS_INVALID")
        else:
            for column_ordinal, role in role_by_ordinal.items():
                try:
                    cell = _money(
                        values[column_ordinal - 1],
                        source_locator={
                            "column_id": f"c{column_ordinal}",
                            "page_json_version_id": region["page_json_version_id"],
                            "row_id": f"r{row_ordinal}",
                            "section_id": region["section_id"],
                            "table_id": region["table_id"],
                        },
                    )
                except GeminiJsonFixedAssetRollforwardFamilyV1Error:
                    reasons.append("SUMMARY_CONTROL_TOTAL_CELL_INVALID:" + role)
                    continue
                if cell["state"] == "BLANK":
                    reasons.append("SUMMARY_CONTROL_TOTAL_CELL_IS_BLANK:" + role)
                    continue
                observation = {
                    "cell": cell,
                    "column_period_date": period_date_by_ordinal[column_ordinal],
                    "role": role,
                    "row_id": f"r{row_ordinal}",
                    "source_ordinal": row_ordinal,
                }
                if relative_axis:
                    observation["column_period_source_kind"] = source_kind_by_ordinal[
                        column_ordinal
                    ]
                observations.append(observation)
            if classification["component_kind"] == "CARRYING_SUMMARY_CONTROL":
                aliases = compiled_specs["evaluation"]["component_policy"]["summary_control"][
                    "row_aliases"
                ]
                declared_rows = []
                for detail_ordinal, detail_row in enumerate(rows, start=1):
                    if detail_ordinal == control_row_ordinal or type(detail_row) is not dict:
                        continue
                    matches = [
                        alias
                        for alias in aliases
                        if _contains_alias(detail_row.get("label_exact"), alias)
                    ]
                    if len(matches) != 1:
                        reasons.append(
                            "SUMMARY_CONTROL_DETAIL_ROW_DOES_NOT_BIND_ONE_DECLARED_POPULATION:"
                            f"r{detail_ordinal}"
                        )
                        continue
                    declared_rows.append((detail_ordinal, detail_row, matches[0]))
                if not declared_rows:
                    reasons.append("SUMMARY_CONTROL_DECLARED_DETAIL_POPULATION_IS_EMPTY")
                for column_ordinal, role in role_by_ordinal.items():
                    terms = []
                    for detail_ordinal, detail_row, matched_alias in declared_rows:
                        detail_values = detail_row.get("values_exact")
                        if type(detail_values) is not list or len(detail_values) != len(columns):
                            reasons.append(
                                f"SUMMARY_CONTROL_DETAIL_ROW_CELL_AXIS_INVALID:r{detail_ordinal}"
                            )
                            continue
                        try:
                            detail_cell = _money(
                                detail_values[column_ordinal - 1],
                                source_locator={
                                    "column_id": f"c{column_ordinal}",
                                    "page_json_version_id": region["page_json_version_id"],
                                    "row_id": f"r{detail_ordinal}",
                                    "section_id": region["section_id"],
                                    "table_id": region["table_id"],
                                },
                            )
                        except GeminiJsonFixedAssetRollforwardFamilyV1Error:
                            reasons.append(
                                f"SUMMARY_CONTROL_DETAIL_CELL_INVALID:{role}:r{detail_ordinal}"
                            )
                            continue
                        if detail_cell["state"] == "BLANK":
                            reasons.append(
                                f"SUMMARY_CONTROL_DETAIL_CELL_IS_BLANK:{role}:r{detail_ordinal}"
                            )
                            continue
                        term = {
                            "cell": detail_cell,
                            "matched_summary_row_alias": matched_alias,
                            "row_id": f"r{detail_ordinal}",
                            "source_ordinal": detail_ordinal,
                        }
                        terms.append(term)
                        detail_observation = {
                            **canonical_clone_v1(term),
                            "column_period_date": period_date_by_ordinal[column_ordinal],
                            "role": role,
                        }
                        if relative_axis:
                            detail_observation["column_period_source_kind"] = (
                                source_kind_by_ordinal[column_ordinal]
                            )
                        detail_observations.append(detail_observation)
                    total = next((item for item in observations if item["role"] == role), None)
                    if total is None or len(terms) != len(declared_rows):
                        continue
                    expected = sum(item["cell"]["coefficient"] for item in terms)
                    observed = total["cell"]["coefficient"]
                    summary_equations.append(
                        {
                            "axis": "HORIZONTAL_SUMMARY_POPULATION",
                            "equation_id": f"summary-control:{role}",
                            "expected_coefficient": expected,
                            "observed_coefficient": observed,
                            "result": {
                                "column_id": f"c{column_ordinal}",
                                "row_id": f"r{control_row_ordinal}",
                            },
                            "status": "EXACT" if expected == observed else "MISMATCH",
                            "terms": [
                                {
                                    "column_id": f"c{column_ordinal}",
                                    "matched_summary_row_alias": item["matched_summary_row_alias"],
                                    "multiplier": 1,
                                    "row_id": item["row_id"],
                                }
                                for item in terms
                            ],
                        }
                    )
                    if expected != observed:
                        reasons.append("SUMMARY_CONTROL_HORIZONTAL_EQUATION_MISMATCH:" + role)
    mappings = []
    if not reasons:
        for observation in observations:
            role = observation["role"]
            source_ref = {
                "cell": canonical_clone_v1(observation["cell"]),
                "column_period_date": observation["column_period_date"],
                "hierarchy_path_exact": canonical_clone_v1(
                    control_rows[0][1].get("hierarchy_path_exact")
                ),
                "label_exact": control_rows[0][1].get("label_exact"),
                "row_id": observation["row_id"],
                "source_ordinal": observation["source_ordinal"],
            }
            if relative_axis:
                source_ref["column_period_source_kind"] = observation[
                    "column_period_source_kind"
                ]
            material = {
                "bound_unit": unit_axis["canonical_unit"],
                "cell": {
                    "coefficient": observation["cell"]["coefficient"],
                    "state": observation["cell"]["state"],
                },
                "period_date": region["period_end_date"],
                "report_norm_id": compiled_specs["bindings"][role],
                "role": role,
                "row_id": observation["row_id"],
                "source_refs": [source_ref],
            }
            mappings.append(
                {
                    **material,
                    "item_mapping_id": "gjffarimv1:item:" + canonical_json_sha256_v1(material),
                }
            )
    return {
        "classification": classification,
        "detail_observations": detail_observations,
        "mappings": mappings,
        "observations": observations,
        "reasons": sorted(set(reasons)),
        "summary_equations": summary_equations,
        "unit_axis": unit_axis,
    }


def _aggregate_component_mapping_axis(
    mappings: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for mapping in mappings:
        grouped[mapping["role"]].append(mapping)
    result = []
    for role in compiled_specs["output_role_order"]:
        observations = grouped.get(role, [])
        if not observations:
            continue
        if len(observations) == 1:
            result.append(canonical_clone_v1(observations[0]))
            continue
        units = {item["bound_unit"] for item in observations}
        periods = {item["period_date"] for item in observations}
        if len(units) != 1 or len(periods) != 1:
            raise _error("component mapping aggregation crosses unit or period")
        material = {
            "bound_unit": next(iter(units)),
            "cell": {
                "coefficient": sum(item["cell"]["coefficient"] for item in observations),
                "state": "AGGREGATED_EXACT_SAME_ROLE_COMPONENT_ROWS",
            },
            "period_date": next(iter(periods)),
            "report_norm_id": compiled_specs["bindings"][role],
            "role": role,
            "row_id": "aggregate:" + role,
            "source_refs": [
                source_ref
                for item in observations
                for source_ref in canonical_clone_v1(item["source_refs"])
            ],
        }
        result.append(
            {
                **material,
                "item_mapping_id": "gjffarimv1:item:" + canonical_json_sha256_v1(material),
            }
        )
    return result


def _extract_component_population(
    *,
    current: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    reasons = []
    components = []
    core_mappings = []
    summary = None
    units = set()
    branch_roles = set()
    for region in current:
        page_json = page_json_by_version.get(region["page_json_version_id"])
        if type(page_json) is not dict:
            raise _error("fixed-asset current component page JSON is absent")
        section, source_table = _source_table(
            page_json, section_id=region["section_id"], table_id=region["table_id"]
        )
        classification, projected_table, endpoint_receipts = _component_table_classification(
            section, source_table, compiled_specs=compiled_specs
        )
        kind = classification["component_kind"]
        if kind in {"CARRYING_SUMMARY_CONTROL", "PRIMARY_STATEMENT_CARRYING_CONTROL"}:
            if summary is not None:
                reasons.append("CURRENT_CARRYING_SUMMARY_CONTROL_IS_NOT_UNIQUE")
                continue
            summary = _summary_control_projection(
                section=section,
                table=source_table,
                region=region,
                compiled_specs=compiled_specs,
            )
            reasons.extend(summary["reasons"])
            if summary["unit_axis"] and summary["unit_axis"]["canonical_unit"]:
                units.add(summary["unit_axis"]["canonical_unit"])
            summary_roles = {
                compiled_specs["evaluation"]["component_policy"]["summary_control"]["opening_role"],
                compiled_specs["evaluation"]["component_policy"]["summary_control"]["current_role"],
            }
            branch_roles.add(
                next(
                    item["branch_role"]
                    for item in compiled_specs["evaluation"]["branch_layouts"]
                    if {item["opening_role"], item["ending_role"]} == summary_roles
                )
            )
            components.append(
                {
                    "classification": classification,
                    "combined_endpoint_receipts": endpoint_receipts,
                    "region": canonical_clone_v1(region),
                    "summary_control_projection": summary,
                }
            )
            continue
        fragment_specs = (
            _fragment_compiled_specs(compiled_specs, classification["default_branch_role"])
            if kind == "DEFAULT_BRANCH_ROLLFORWARD_FRAGMENT"
            else compiled_specs
        )
        extracted = _extract_table_records(
            section=section,
            table=projected_table,
            region=region,
            page_json_by_version=page_json_by_version,
            compiled_specs=fragment_specs,
        )
        reasons.extend(extracted["reasons"])
        units.add(extracted["unit_axis"]["canonical_unit"])
        branch_roles.update(classification["branch_roles"])
        core_mappings.extend(extracted["mappings"])
        components.append(
            {
                "classification": classification,
                "combined_endpoint_receipts": endpoint_receipts,
                "region": canonical_clone_v1(region),
                "subtotal_collapse": extracted["subtotal_collapse"],
                "table_receipt": extracted["table_receipt"],
                "width_seal": extracted["width_seal"],
            }
        )
    units.discard(None)
    if len(units) != 1:
        reasons.append("CURRENT_COMPONENT_MONEY_UNIT_AXIS_IS_NOT_UNIQUE")
    carry_roles = {
        compiled_specs["evaluation"]["component_policy"]["summary_control"]["opening_role"],
        compiled_specs["evaluation"]["component_policy"]["summary_control"]["current_role"],
    }
    if summary is not None:
        core_mappings = [item for item in core_mappings if item["role"] not in carry_roles]
        core_mappings.extend(summary["mappings"])
    mappings = _aggregate_component_mapping_axis(core_mappings, compiled_specs=compiled_specs)
    by_role = {item["role"]: item for item in mappings}
    aggregate_equations = []
    if summary is not None and not reasons:
        cost_layout = next(
            item
            for item in compiled_specs["evaluation"]["branch_layouts"]
            if item["branch_role"] == "COST_BRANCH"
        )
        dep_layout = next(
            item
            for item in compiled_specs["evaluation"]["branch_layouts"]
            if item["branch_role"] == "DEPRECIATION_BRANCH"
        )
        carry_layout = next(
            item
            for item in compiled_specs["evaluation"]["branch_layouts"]
            if item["branch_role"] == "CARRYING_BRANCH"
        )
        dep_cells = [
            by_role.get(dep_layout[key], {}).get("cell", {}).get("coefficient")
            for key in ("opening_role", "ending_role")
        ]
        if all(value is None for value in dep_cells) and "DEPRECIATION_BRANCH" in set(
            compiled_specs["evaluation"]["component_policy"]["optional_absent_branch_roles"]
        ):
            dep_cells = [0, 0]
            depreciation_multiplier = -1
        elif all(type(value) is int and value >= 0 for value in dep_cells):
            depreciation_multiplier = -1
        elif all(type(value) is int and value <= 0 for value in dep_cells):
            depreciation_multiplier = 1
        else:
            depreciation_multiplier = None
            reasons.append("AGGREGATE_DEPRECIATION_ENDPOINT_SIGN_IS_NOT_UNIQUE")
        if depreciation_multiplier is not None:
            for index, endpoint in enumerate(("opening_role", "ending_role")):
                cost_role = cost_layout[endpoint]
                carry_role = carry_layout[endpoint]
                if cost_role not in by_role or carry_role not in by_role:
                    reasons.append("AGGREGATE_CARRYING_ENDPOINT_FRONTIER_IS_INCOMPLETE")
                    continue
                expected = (
                    by_role[cost_role]["cell"]["coefficient"]
                    + depreciation_multiplier * dep_cells[index]
                )
                observed = by_role[carry_role]["cell"]["coefficient"]
                aggregate_equations.append(
                    {
                        "equation_id": "component-carrying:" + carry_role,
                        "expected_coefficient": expected,
                        "observed_coefficient": observed,
                        "status": "EXACT" if expected == observed else "MISMATCH",
                    }
                )
                if expected != observed:
                    reasons.append("AGGREGATE_CARRYING_CONTROL_EQUATION_MISMATCH:" + carry_role)
    required_branches = {
        item["branch_role"] for item in compiled_specs["evaluation"]["branch_layouts"]
    } - set(compiled_specs["evaluation"]["component_policy"]["optional_absent_branch_roles"])
    if required_branches - branch_roles:
        reasons.append("REQUIRED_COMPONENT_BRANCH_FRONTIER_IS_INCOMPLETE")
    if reasons:
        mappings = []
    return {
        "aggregate_equations": aggregate_equations,
        "bound_unit": next(iter(units)) if len(units) == 1 else None,
        "components": components,
        "mappings": mappings,
        "reasons": sorted(set(reasons)),
    }


def evaluate_gemini_json_fixed_asset_rollforward_family_cluster_v1(
    *,
    regions: Any,
    control_regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate one current fixed-asset table and retain typed controls."""

    component_policy = compiled_specs["evaluation"].get("component_policy")
    current = _region_axis(
        regions, component_role="CURRENT_TABLE", maximum=8 if component_policy else 1
    )
    controls = _region_axis(control_regions, component_role="COMPARATIVE_CONTROL_TABLE", maximum=8)
    expected_receipt = build_gemini_json_fixed_asset_rollforward_region_query_receipt_v1(
        current, control_regions=controls
    )
    if type(query_receipt) is not dict or not same_typed_json_v1(query_receipt, expected_receipt):
        raise _error("fixed-asset query receipt does not bind current/control regions")
    page_json_by_version, source_repair_overlay_receipts = (
        _apply_authenticated_source_repair_artifact_v1(
            page_json_by_version=page_json_by_version,
            compiled_specs=compiled_specs,
        )
    )
    if component_policy is not None:
        if not current:
            raise _error("fixed-asset component evaluator needs current source tables")
        extracted_population = _extract_component_population(
            current=current,
            page_json_by_version=page_json_by_version,
            compiled_specs=compiled_specs,
        )
        region = current[0]
        supplemental = _supplemental_disclosure_projection(
            page_json_by_version=page_json_by_version,
            region=region,
            bound_unit=extracted_population["bound_unit"],
            compiled_specs=compiled_specs,
        )
        reasons = sorted(set([*extracted_population["reasons"], *supplemental["reasons"]]))
        mappings = (
            [*extracted_population["mappings"], *supplemental["mappings"]] if not reasons else []
        )
        material = {
            "claim_boundary": CLAIM_BOUNDARY,
            "closure_receipt": {
                "component_population_receipt": extracted_population,
                "control_regions": controls,
                "query_receipt": expected_receipt,
                "structural_root_receipt": {
                    "emitted_mapping": False,
                    "mapping_policy": compiled_specs["schema"]["structural_root_mapping_policy"],
                    "report_norm_id": compiled_specs["schema"]["family_root_report_norm_id"],
                    "role": compiled_specs["topology"]["parent"]["role"],
                },
                "supplemental_disclosure_receipt": supplemental,
                "subtotal_collapse": None,
                "table_receipt": None,
                "width_seal": None,
                **(
                    {
                        "source_repair_overlay_receipts": (
                            source_repair_overlay_receipts
                        )
                    }
                    if source_repair_overlay_receipts
                    else {}
                ),
            },
            "component_regions": current,
            "control_regions": controls,
            "document_id": region["document_id"],
            "family_id": compiled_specs["topology"]["family_id"],
            "mappings": mappings,
            "page_json_version_id": region["page_json_version_id"],
            "physical_page": region["physical_page"],
            "reasons": reasons,
            "section_id": region["section_id"],
            "source_logical_name": region["source_logical_name"],
            "source_sha256": region["source_sha256"],
            "status": READY if mappings and not reasons else UNRESOLVED,
            "table_id": region["table_id"],
        }
        return {
            "candidate_id": "gjffarcv1:candidate:" + canonical_json_sha256_v1(material),
            **material,
        }
    if len(current) != 1:
        raise _error("fixed-asset evaluator needs exactly one current table")
    region = current[0]
    page_json = page_json_by_version.get(region["page_json_version_id"])
    if type(page_json) is not dict:
        raise _error("fixed-asset current page JSON is absent")
    section, table = _source_table(
        page_json, section_id=region["section_id"], table_id=region["table_id"]
    )
    extracted = _extract_table_records(
        section=section,
        table=table,
        region=region,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
    )
    supplemental = _supplemental_disclosure_projection(
        page_json_by_version=page_json_by_version,
        region=region,
        bound_unit=extracted["unit_axis"]["canonical_unit"],
        compiled_specs=compiled_specs,
    )
    reasons = sorted(set([*extracted["reasons"], *supplemental["reasons"]]))
    mappings = [*extracted["mappings"], *supplemental["mappings"]] if not reasons else []
    material = {
        "claim_boundary": extracted.get("claim_boundary", CLAIM_BOUNDARY),
        "closure_receipt": {
            "control_regions": controls,
            "query_receipt": expected_receipt,
            "structural_root_receipt": {
                "emitted_mapping": False,
                "mapping_policy": compiled_specs["schema"]["structural_root_mapping_policy"],
                "report_norm_id": compiled_specs["schema"]["family_root_report_norm_id"],
                "role": compiled_specs["topology"]["parent"]["role"],
            },
            "supplemental_disclosure_receipt": supplemental,
            "subtotal_collapse": extracted["subtotal_collapse"],
            "table_receipt": extracted["table_receipt"],
            "width_seal": extracted["width_seal"],
            **(
                {"source_repair_overlay_receipts": source_repair_overlay_receipts}
                if source_repair_overlay_receipts
                else {}
            ),
        },
        "component_regions": current,
        "control_regions": controls,
        "document_id": region["document_id"],
        "family_id": compiled_specs["topology"]["family_id"],
        "mappings": mappings,
        "page_json_version_id": region["page_json_version_id"],
        "physical_page": region["physical_page"],
        "reasons": reasons,
        "section_id": region["section_id"],
        "source_logical_name": region["source_logical_name"],
        "source_sha256": region["source_sha256"],
        "status": READY if mappings and not reasons else UNRESOLVED,
        "table_id": region["table_id"],
    }
    return {
        "candidate_id": "gjffarcv1:candidate:" + canonical_json_sha256_v1(material),
        **material,
    }


def validate_gemini_json_fixed_asset_rollforward_family_candidate_replay_v1(
    value: Any,
    *,
    regions: Any,
    control_regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    rebuilt = evaluate_gemini_json_fixed_asset_rollforward_family_cluster_v1(
        regions=regions,
        control_regions=control_regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if type(value) is not dict or not same_typed_json_v1(value, rebuilt):
        raise _error("fixed-asset candidate does not replay exactly")
    return rebuilt


def build_gemini_json_indexed_fixed_asset_rollforward_query_evidence_v1(
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
            "cluster": cluster,
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
        "accepted_control_region_count": sum(
            len(item.get("control_regions", [])) for item in accepted
        ),
        "accepted_current_region_count": sum(
            len(item.get("component_regions", [])) for item in accepted
        ),
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
        "query_evidence_id": "gjffareqv1:evidence:" + canonical_json_sha256_v1(material),
    }


def validate_gemini_json_indexed_fixed_asset_rollforward_query_evidence_v1(
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
        raise _error("indexed fixed-asset query evidence is invalid")
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
        raise _error("indexed fixed-asset document axis is incomplete")
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
            raise _error("indexed fixed-asset document axis is invalid")
        by_ordinal[ordinal] = document
    page_fields = document_fields | {
        "page_json_version_id",
        "physical_page",
        "selected_page_ordinal",
    }
    page_versions = []
    per_document: dict[int, int] = defaultdict(int)
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
            raise _error("indexed fixed-asset page axis is invalid")
        prior_document = page["document_ordinal"]
        per_document[page["document_ordinal"]] += 1
        if page.get("selected_page_ordinal") != per_document[page["document_ordinal"]]:
            raise _error("indexed fixed-asset page order is incomplete")
        page_versions.append(page["page_json_version_id"])
    if len(page_versions) != len(set(page_versions)) or set(per_document) != set(by_ordinal):
        raise _error("indexed fixed-asset page frontier is incomplete")
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
            != "gjffarfcv1:cluster:"
            + canonical_json_sha256_v1(
                {key: item for key, item in cluster.items() if key != "cluster_id"}
            )
        ):
            raise _error("indexed fixed-asset cluster binding drifted")
        regions = cluster.get("component_regions")
        controls = cluster.get("control_regions")
        reasons = cluster.get("reasons")
        if (
            type(reasons) is not list
            or reasons != sorted(set(reasons))
            or type(controls) is not list
            or (
                cluster["status"] == READY
                and (
                    not regions
                    or len(regions)
                    > (8 if compiled_specs["evaluation"].get("component_policy") else 1)
                    or reasons
                )
            )
            or (cluster["status"] == NOT_OBSERVED and (regions or controls or reasons))
            or (cluster["status"] == UNRESOLVED and (not reasons or regions or controls))
        ):
            raise _error("indexed fixed-asset disposition drifted")
        if cluster["status"] == READY:
            _region_axis(
                regions,
                component_role="CURRENT_TABLE",
                maximum=8 if compiled_specs["evaluation"].get("component_policy") else 1,
            )
            _region_axis(controls, component_role="COMPARATIVE_CONTROL_TABLE", maximum=8)
            accepted.append(cluster)
    if not same_typed_json_v1(value["accepted_clusters"], accepted):
        raise _error("indexed fixed-asset accepted cluster axis drifted")
    expected_receipt = {
        "accepted_cluster_axis_sha256": canonical_json_sha256_v1(accepted),
        "accepted_cluster_count": len(accepted),
        "accepted_control_region_count": sum(len(item["control_regions"]) for item in accepted),
        "accepted_current_region_count": sum(len(item["component_regions"]) for item in accepted),
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
        raise _error("indexed fixed-asset query receipt drifted")
    material = {key: canonical_clone_v1(value[key]) for key in fields - {"query_evidence_id"}}
    if value["query_evidence_id"] != "gjffareqv1:evidence:" + canonical_json_sha256_v1(material):
        raise _error("indexed fixed-asset evidence identity drifted")
    return canonical_clone_v1(value)


def validate_gemini_json_fixed_asset_rollforward_sweep_query_bindings_v1(
    *, trials: Any, indexed_query_evidence: Any, compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    evidence = validate_gemini_json_indexed_fixed_asset_rollforward_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
    documents = evidence["selected_document_axis"]
    if type(trials) is not list or len(trials) != len(documents):
        raise _error("fixed-asset sweep trial axis is incomplete")
    accepted = {item["document_ordinal"]: item for item in evidence["accepted_clusters"]}
    checked = []
    for ordinal, (trial, document, disposition) in enumerate(
        zip(trials, documents, evidence["candidate_dispositions"], strict=True), start=1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("source_logical_name") != document["source_logical_name"]
            or trial.get("source_sha256") != document["source_sha256"]
            or type(trial.get("candidates")) is not list
            or trial.get("candidate_count") != len(trial["candidates"])
        ):
            raise _error("fixed-asset sweep trial identity drifted")
        if disposition["disposition"] == READY:
            if len(trial["candidates"]) != 1:
                raise _error("accepted fixed-asset source needs exactly one candidate")
            candidate = trial["candidates"][0]
            cluster = accepted[ordinal]
            if not same_typed_json_v1(
                candidate.get("component_regions"), cluster["component_regions"]
            ) or not same_typed_json_v1(
                candidate.get("control_regions"), cluster["control_regions"]
            ):
                raise _error("fixed-asset candidate region binding drifted")
            if candidate.get("status") == READY:
                if (
                    trial.get("status") != READY
                    or trial.get("selected_candidate_id") != candidate.get("candidate_id")
                    or not same_typed_json_v1(trial.get("mappings"), candidate.get("mappings"))
                    or trial.get("reasons")
                ):
                    raise _error("fixed-asset READY trial drifted")
            elif (
                trial.get("status") != UNRESOLVED
                or trial.get("selected_candidate_id") is not None
                or trial.get("mappings")
                or trial.get("reasons") != candidate.get("reasons")
            ):
                raise _error("fixed-asset unresolved candidate drifted")
        elif disposition["disposition"] == NOT_OBSERVED:
            if (
                trial.get("status") != NOT_OBSERVED
                or trial["candidates"]
                or trial.get("mappings")
                or trial.get("reasons")
                or trial.get("selected_candidate_id") is not None
            ):
                raise _error("fixed-asset not-observed trial drifted")
        elif (
            trial.get("status") != UNRESOLVED
            or trial["candidates"]
            or trial.get("mappings")
            or trial.get("selected_candidate_id") is not None
            or trial.get("reasons") != disposition["cluster"]["reasons"]
        ):
            raise _error("fixed-asset unresolved source disposition drifted")
        checked.append(canonical_clone_v1(trial))
    return checked
