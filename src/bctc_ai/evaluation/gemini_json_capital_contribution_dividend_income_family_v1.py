"""Family-35 adapter for capital-contribution and dividend income.

The shared multi-table evaluator remains the accounting authority.  This
adapter adds only three narrow, replayable source interpretations:

* literal PDF-visible transcription repairs on private page clones;
* one exact root row from a primary income statement when the detailed note is
  not observed; and
* one guarded semantic retry when an otherwise ambiguous family label is a
  standalone source leaf rather than a structural carrier; and
* a VND retry only after the ordinary result fails and source unit evidence is
  uniquely VND.

No branch derives a source value, turns a blank into zero, or routes by bank,
filename, page number, note number, or numeric magnitude.
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
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    _source_table,
    _unit_axis,
    build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
    validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
)
from bctc_ai.evaluation.gemini_json_other_long_term_investments_family_v1 import (
    _source_money,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FAMILY_ID = "CAPITAL_CONTRIBUTION_DIVIDEND_INCOME"
ADAPTER_FORMAT_VERSION = (
    "GEMINI_JSON_CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_FAMILY_ADAPTER_V1"
)
ADAPTER_SPEC_FORMAT_VERSION = (
    "GEMINI_JSON_CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_ADAPTER_SPEC_V1"
)
SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION = (
    "GEMINI_JSON_CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_"
    "AUTHENTICATED_SOURCE_REPAIR_ARTIFACT_V1"
)
SOURCE_REPAIR_POLICY = (
    "PDF_VISIBLE_LITERAL_TRANSCRIPTION_ONLY_PRIVATE_CLONE_NO_EQUATION_"
    "BACKSOLVE_NO_BLANK_TO_ZERO"
)
PRIMARY_ROOT_POLICY = (
    "UNIQUE_EXACT_INCOME_STATEMENT_ROOT_WHEN_DISCLOSURE_NOT_OBSERVED_"
    "PRIVATE_SEMANTIC_PROJECTION"
)
STANDALONE_LONG_TERM_LEAF_POLICY = (
    "UNIQUE_STANDALONE_ITEM_UNDER_EXPLICIT_FAMILY_TABLE_WITH_DIRECT_CARRIER_"
    "AND_EXACT_SHARED_CLOSURE_RETRY"
)
VND_RETRY_POLICY = (
    "BASE_RESULT_FIRST_THEN_EXPLICIT_LOCAL_OR_DOCUMENT_CONSENSUS_VND_ONLY"
)
VND_ZERO_DECIMAL_SUFFIX_POLICY = (
    "EXPLICIT_LOCAL_VND_STRICT_GROUPED_INTEGER_WITH_LITERAL_ZERO_DECIMAL_"
    "SUFFIX_PRIVATE_PARSE_PROJECTION_SOURCE_TEXT_PRESERVED"
)
DEFAULT_ADAPTER_SPEC_PATH = (
    "config/families/tm-capital-contribution-dividend-income-adapter-v1.json"
)
DEFAULT_SOURCE_REPAIR_PATH = (
    "data/registered/"
    "gemini_json_capital_contribution_dividend_income_source_repairs_v1.json"
)
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_CAPITAL_CONTRIBUTION_DIVIDEND_"
    "INCOME_EXACT_PRIMARY_INCOME_STATEMENT_ROOT_FALLBACK_EXPLICIT_SOURCE_"
    "STANDALONE_LONG_TERM_LEAF_SEMANTIC_RETRY_VND_RETRY_PDF_AUTHENTICATED_"
    "LITERAL_REPAIR_PRIVATE_CLONE_ONLY_NO_"
    "BLANK_ZERO_NO_NUMERIC_BACKSOLVE_NO_BANK_FILE_PAGE_VALUE_ROUTING_"
    "PROPOSAL_ONLY_" + SHARED_CLAIM_BOUNDARY
)

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_PAGE_ID = re.compile(r"gfpstorev1:page:[0-9a-f]{64}\Z")
_PAGE_VERSION = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_DOCUMENT_ID = re.compile(r"gfpstorev1:document:[0-9a-f]{64}\Z")
_EXTRACTION_RUN_ID = re.compile(r"gfpstorev1:run:[0-9a-f]{64}\Z")
_SECTION_ID = re.compile(r"s[1-9][0-9]*\Z")
_TABLE_ID = re.compile(r"t[1-9][0-9]*\Z")
_ROW_ID = re.compile(r"r[1-9][0-9]*\Z")
_REPAIR_ID = re.compile(r"gjccdifav1:repair:[0-9a-f]{64}\Z")
_OVERLAY_ID = re.compile(r"gjccdifav1:overlay:[0-9a-f]{64}\Z")
_VND_ZERO_DECIMAL_SUFFIX = re.compile(
    r"(?P<open>\()?"
    r"(?P<sign>-)?"
    r"(?P<body>[0-9]{1,3}(?:\.[0-9]{3})+)"
    r",00"
    r"(?P<close>\))?\Z"
)


class GeminiJsonCapitalContributionDividendIncomeFamilyV1Error(ValueError):
    """The Family-35 adapter source, policy, or replay boundary drifted."""


def _error(message: str) -> GeminiJsonCapitalContributionDividendIncomeFamilyV1Error:
    return GeminiJsonCapitalContributionDividendIncomeFamilyV1Error(message)


def _load_json(path: str) -> dict[str, Any]:
    source = Path(__file__).resolve().parents[3] / path
    try:
        value = json.loads(source.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("Family-35 adapter resource is absent or invalid") from exc
    if type(value) is not dict:
        raise _error("Family-35 adapter resource is not one object")
    return value


def _bbox(value: Any, *, width: int, height: int, label: str) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or not (0 <= value[0] < value[2] <= width)
        or not (0 <= value[1] < value[3] <= height)
    ):
        raise _error(f"Family-35 {label} is invalid")
    return list(value)


def _compile_adapter_spec(value: Any) -> dict[str, Any]:
    fields = {
        "family_id",
        "format_version",
        "primary_statement_root_aliases",
        "primary_statement_root_policy",
        "standalone_long_term_leaf_aliases",
        "standalone_long_term_leaf_policy",
        "vnd_retry_policy",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value.get("family_id") != FAMILY_ID
        or value.get("format_version") != ADAPTER_SPEC_FORMAT_VERSION
        or value.get("primary_statement_root_policy") != PRIMARY_ROOT_POLICY
        or value.get("standalone_long_term_leaf_policy")
        != STANDALONE_LONG_TERM_LEAF_POLICY
        or value.get("vnd_retry_policy") != VND_RETRY_POLICY
        or type(value.get("primary_statement_root_aliases")) is not list
        or not value["primary_statement_root_aliases"]
        or type(value.get("standalone_long_term_leaf_aliases")) is not list
        or not value["standalone_long_term_leaf_aliases"]
        or any(
            type(alias) is not str or not _normalized(alias)
            for key in (
                "primary_statement_root_aliases",
                "standalone_long_term_leaf_aliases",
            )
            for alias in value[key]
        )
        or len({_normalized(alias) for alias in value["primary_statement_root_aliases"]})
        != len(value["primary_statement_root_aliases"])
        or len(
            {
                _normalized(alias)
                for alias in value["standalone_long_term_leaf_aliases"]
            }
        )
        != len(value["standalone_long_term_leaf_aliases"])
    ):
        raise _error("Family-35 adapter spec is invalid")
    return canonical_clone_v1(value)


def _compile_source_repair_artifact(value: Any) -> dict[str, Any]:
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
    ):
        raise _error("Family-35 source-repair artifact is invalid")

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
    repairs = []
    seen_versions: set[str] = set()
    seen_ids: set[str] = set()
    for raw in value["repairs"]:
        if type(raw) is not dict or set(raw) != repair_fields:
            raise _error("Family-35 source-repair fields drifted")
        repair = canonical_clone_v1(raw)
        source = repair.get("source_binding")
        if type(source) is not dict or set(source) != source_fields:
            raise _error("Family-35 source-repair source fields drifted")
        if (
            _DOCUMENT_ID.fullmatch(source.get("document_id", "")) is None
            or _SHA256.fullmatch(source.get("source_sha256", "")) is None
            or type(source.get("source_logical_name")) is not str
            or not source["source_logical_name"]
            or type(source.get("physical_page")) is not int
            or source["physical_page"] <= 0
            or type(source.get("source_size_bytes")) is not int
            or source["source_size_bytes"] <= 0
            or _PAGE_ID.fullmatch(source.get("page_id", "")) is None
            or source.get("media_type") != "image/png"
            or source.get("render_dpi") != 300
            or any(type(source.get(key)) is not int or source[key] <= 0 for key in ("image_size_bytes", "pixel_height", "pixel_width"))
            or _SHA256.fullmatch(source.get("image_sha256", "")) is None
        ):
            raise _error("Family-35 source-repair source binding is invalid")
        expected_document = "gfpstorev1:document:" + canonical_json_sha256_v1(
            {
                "source_logical_name": source["source_logical_name"],
                "source_sha256": source["source_sha256"],
                "source_size_bytes": source["source_size_bytes"],
            }
        )
        if source["document_id"] != expected_document:
            raise _error("Family-35 source-repair document identity does not replay")
        expected_page = "gfpstorev1:page:" + canonical_json_sha256_v1(
            {
                "document_id": expected_document,
                "image_sha256": source["image_sha256"],
                "image_size_bytes": source["image_size_bytes"],
                "media_type": source["media_type"],
                "physical_page": source["physical_page"],
                "pixel_height": source["pixel_height"],
                "pixel_width": source["pixel_width"],
                "render_dpi": source["render_dpi"],
            }
        )
        if source["page_id"] != expected_page:
            raise _error("Family-35 source-repair page identity does not replay")
        if (
            _PAGE_VERSION.fullmatch(repair.get("base_page_json_version_id", "")) is None
            or repair["base_page_json_version_id"] in seen_versions
            or _SHA256.fullmatch(repair.get("base_page_json_sha256", "")) is None
            or _SHA256.fullmatch(repair.get("effective_page_json_sha256", "")) is None
            or _SHA256.fullmatch(repair.get("stored_canonical_json_sha256", "")) is None
            or _EXTRACTION_RUN_ID.fullmatch(repair.get("extraction_run_id", "")) is None
        ):
            raise _error("Family-35 source-repair page identity is invalid")
        expected_version = "gfpstorev1:json:" + canonical_json_sha256_v1(
            {
                "canonical_json_sha256": repair["stored_canonical_json_sha256"],
                "extraction_run_id": repair["extraction_run_id"],
                "page_id": source["page_id"],
            }
        )
        if repair["base_page_json_version_id"] != expected_version:
            raise _error("Family-35 source-repair page identity does not replay")
        seen_versions.add(repair["base_page_json_version_id"])

        table_ref = repair.get("table_ref")
        if (
            type(table_ref) is not dict
            or set(table_ref) != table_fields
            or _SECTION_ID.fullmatch(table_ref.get("section_id", "")) is None
            or _TABLE_ID.fullmatch(table_ref.get("table_id", "")) is None
            or _SHA256.fullmatch(table_ref.get("base_table_sha256", "")) is None
            or _SHA256.fullmatch(table_ref.get("effective_table_sha256", "")) is None
        ):
            raise _error("Family-35 source-repair table binding is invalid")
        visual = repair.get("visual_evidence")
        if (
            type(visual) is not dict
            or set(visual) != visual_fields
            or visual.get("evidence_kind") != "PDF_RENDER_VISIBLE_LITERAL"
            or visual.get("render_mode") != "PYMUPDF_RGB_300_DPI_ALPHA_FALSE"
            or not re.fullmatch(r"20[0-9]{2}-[01][0-9]-[0-3][0-9]", visual.get("reviewed_utc_date", ""))
            or _SHA256.fullmatch(visual.get("table_crop_rgb_sha256", "")) is None
        ):
            raise _error("Family-35 source-repair visual evidence is invalid")
        table_crop = _bbox(
            visual["table_crop_bbox_pixels_xyxy"],
            width=source["pixel_width"],
            height=source["pixel_height"],
            label="table crop",
        )

        cells = []
        seen_cells: set[tuple[int, int]] = set()
        for raw_cell in repair.get("cell_repairs", []):
            if type(raw_cell) is not dict or set(raw_cell) != cell_fields:
                raise _error("Family-35 source-repair cell fields drifted")
            cell = canonical_clone_v1(raw_cell)
            match = re.fullmatch(r"r([1-9][0-9]*):c([1-9][0-9]*)", cell.get("cell_id", ""))
            identity = None if match is None else (int(match.group(1)), int(match.group(2)))
            if (
                identity is None
                or identity in seen_cells
                or cell.get("visual_state") != "PDF_RENDER_VISIBLE_LITERAL"
                or cell.get("after_exact") != "-"
                or cell.get("before_exact") == "-"
                or cell.get("after_exact") is not None and type(cell.get("after_exact")) is not str
                or cell.get("before_exact") is not None and type(cell.get("before_exact")) is not str
                or type(cell.get("column_header_path_exact")) is not list
                or type(cell.get("row_hierarchy_path_exact")) is not list
                or cell.get("row_label_exact") is not None and type(cell.get("row_label_exact")) is not str
                or _SHA256.fullmatch(cell.get("crop_rgb_sha256", "")) is None
            ):
                raise _error("Family-35 source-repair cell is invalid")
            cell_crop = _bbox(
                cell["crop_bbox_pixels_xyxy"],
                width=source["pixel_width"],
                height=source["pixel_height"],
                label="cell crop",
            )
            if not (
                table_crop[0] <= cell_crop[0] < cell_crop[2] <= table_crop[2]
                and table_crop[1] <= cell_crop[1] < cell_crop[3] <= table_crop[3]
            ):
                raise _error("Family-35 source-repair cell crop is outside its table crop")
            seen_cells.add(identity)
            cells.append(cell)
        if cells != sorted(cells, key=lambda item: tuple(int(v) for v in item["cell_id"][1:].split(":c"))):
            raise _error("Family-35 source-repair cell axis is unordered")

        rows = []
        seen_rows: set[int] = set()
        for raw_row in repair.get("row_repairs", []):
            if type(raw_row) is not dict or set(raw_row) != row_fields:
                raise _error("Family-35 source-repair row fields drifted")
            row = canonical_clone_v1(raw_row)
            match = _ROW_ID.fullmatch(row.get("row_id", ""))
            ordinal = None if match is None else int(row["row_id"][1:])
            if (
                ordinal is None
                or ordinal in seen_rows
                or row.get("visual_state") != "PDF_RENDER_VISIBLE_LITERAL"
                or type(row.get("row_kind")) is not str
                or not row["row_kind"]
                or row.get("before_label_exact") is not None and type(row.get("before_label_exact")) is not str
                or row.get("after_label_exact") is not None and type(row.get("after_label_exact")) is not str
                or type(row.get("before_hierarchy_path_exact")) is not list
                or type(row.get("after_hierarchy_path_exact")) is not list
                or _SHA256.fullmatch(row.get("crop_rgb_sha256", "")) is None
            ):
                raise _error("Family-35 source-repair row is invalid")
            _bbox(row["crop_bbox_pixels_xyxy"], width=source["pixel_width"], height=source["pixel_height"], label="row crop")
            seen_rows.add(ordinal)
            rows.append(row)
        if rows != sorted(rows, key=lambda item: int(item["row_id"][1:])) or not cells and not rows:
            raise _error("Family-35 source-repair row axis is unordered or empty")
        repair["cell_repairs"] = cells
        repair["row_repairs"] = rows
        if repair.get("repair_reason") != "VISIBLE_PDF_TRANSCRIPTION_MISMATCH":
            raise _error("Family-35 source-repair reason is invalid")
        expected_id = "gjccdifav1:repair:" + canonical_json_sha256_v1(
            {key: repair[key] for key in repair if key != "repair_id"}
        )
        if (
            _REPAIR_ID.fullmatch(repair.get("repair_id", "")) is None
            or repair["repair_id"] != expected_id
            or repair["repair_id"] in seen_ids
        ):
            raise _error("Family-35 source-repair identity does not replay")
        seen_ids.add(repair["repair_id"])
        repairs.append(repair)
    repairs.sort(key=lambda item: (item["source_binding"]["source_logical_name"], item["source_binding"]["physical_page"], item["repair_id"]))
    if repairs != value["repairs"]:
        raise _error("Family-35 source-repair axis is unordered")
    material = {
        "family_id": FAMILY_ID,
        "format_version": SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION,
        "repairs": repairs,
        "review_policy": SOURCE_REPAIR_POLICY,
    }
    expected_overlay = "gjccdifav1:overlay:" + canonical_json_sha256_v1(material)
    if _OVERLAY_ID.fullmatch(value.get("overlay_id", "")) is None or value["overlay_id"] != expected_overlay:
        raise _error("Family-35 source-repair overlay identity does not replay")
    return {**material, "overlay_id": expected_overlay}


def compile_gemini_json_capital_contribution_dividend_income_family_specs_v1(
    topology_spec: Any,
    evaluation_spec: Any,
    schema_binding_spec: Any,
    *,
    adapter_spec: Any | None = None,
    source_repair_spec: Any | None = None,
) -> dict[str, Any]:
    """Compile the base family and the two private retry projections."""

    adapter = _compile_adapter_spec(
        _load_json(DEFAULT_ADAPTER_SPEC_PATH) if adapter_spec is None else adapter_spec
    )
    overlay = _compile_source_repair_artifact(
        _load_json(DEFAULT_SOURCE_REPAIR_PATH)
        if source_repair_spec is None
        else source_repair_spec
    )
    base = compile_gemini_json_multitable_hierarchical_family_specs_v1(
        topology_spec, evaluation_spec, schema_binding_spec
    )
    if base.get("topology", {}).get("family_id") != FAMILY_ID:
        raise _error("Family-35 adapter received another family")

    primary_topology = canonical_clone_v1(topology_spec)
    existing_primary_aliases = {
        _normalized(alias) for alias in primary_topology["parent"]["aliases"]
    }
    primary_topology["parent"]["aliases"].extend(
        alias
        for alias in adapter["primary_statement_root_aliases"]
        if _normalized(alias) not in existing_primary_aliases
    )
    primary_evaluation = canonical_clone_v1(evaluation_spec)
    primary_evaluation["primary_statement_source_result_fallback_policy"] = (
        "UNIQUE_SHALLOWEST_STRUCTURAL_EXACT_VISIBLE_ROOT_WHEN_NOTE_NOT_OBSERVED"
    )
    # The fallback projects one exact income-statement result row, not the
    # surrounding statement population.  Scope parsing to that explicit root
    # so an unrelated malformed OCR cell elsewhere on the primary statement
    # cannot suppress a source-visible Family-35 result.  The root row itself
    # remains subject to the ordinary exact-money and two-period gates.
    primary_evaluation["family_root_population_policy"] = (
        "EXPLICIT_PRIMARY_STATEMENT_SOURCE_ROOT_SUBTREE_OTHERWISE_WHOLE_TABLE"
    )
    primary_evaluation["unmapped_direct_family_row_policy"] = "IGNORE"
    primary_schema = canonical_clone_v1(schema_binding_spec)
    primary_schema["root_mapping_policy"] = "SOURCE_VISIBLE_PRIMARY_RESULT_OR_EXACT_NOTE_EQUATION"
    primary = compile_gemini_json_multitable_hierarchical_family_specs_v1(
        primary_topology, primary_evaluation, primary_schema
    )

    standalone_long_term_topology = canonical_clone_v1(topology_spec)
    long_term_roles = [
        item
        for item in standalone_long_term_topology.get("children", [])
        if item.get("role") == "LONG_TERM_CAPITAL_DIVIDEND"
    ]
    if len(long_term_roles) != 1:
        raise _error("Family-35 standalone long-term role is absent or ambiguous")
    long_term_roles[0]["matchers"].append(
        {
            "aliases": canonical_clone_v1(
                adapter["standalone_long_term_leaf_aliases"]
            ),
            "within_role": "DIRECT_DIVIDEND",
        }
    )
    standalone_long_term = (
        compile_gemini_json_multitable_hierarchical_family_specs_v1(
            standalone_long_term_topology, evaluation_spec, schema_binding_spec
        )
    )

    def with_vnd(spec: Mapping[str, Any]) -> dict[str, Any]:
        source = canonical_clone_v1(spec)
        bindings = source.get("money_unit_bindings")
        if type(bindings) is not list:
            raise _error("Family-35 unit bindings are invalid")
        vnd = [item for item in bindings if item.get("canonical_unit") == "VND"]
        if len(vnd) != 1 or vnd[0].get("accepted") is not False:
            raise _error("Family-35 VND retry binding is absent or already accepted")
        vnd[0]["accepted"] = True
        return source

    vnd = compile_gemini_json_multitable_hierarchical_family_specs_v1(
        topology_spec, with_vnd(evaluation_spec), schema_binding_spec
    )
    primary_vnd = compile_gemini_json_multitable_hierarchical_family_specs_v1(
        primary_topology, with_vnd(primary_evaluation), primary_schema
    )
    standalone_long_term_vnd = (
        compile_gemini_json_multitable_hierarchical_family_specs_v1(
            standalone_long_term_topology,
            with_vnd(evaluation_spec),
            schema_binding_spec,
        )
    )
    base["capital_contribution_dividend_income_adapter_spec"] = adapter
    base["capital_contribution_dividend_income_source_repair_overlay"] = overlay
    base["capital_contribution_dividend_income_source_repair_spec_sha256"] = canonical_json_sha256_v1(source_repair_spec if source_repair_spec is not None else _load_json(DEFAULT_SOURCE_REPAIR_PATH))
    base["capital_contribution_dividend_income_primary_specs"] = primary
    base["capital_contribution_dividend_income_standalone_long_term_specs"] = (
        standalone_long_term
    )
    base["capital_contribution_dividend_income_vnd_specs"] = vnd
    base["capital_contribution_dividend_income_primary_vnd_specs"] = primary_vnd
    base[
        "capital_contribution_dividend_income_standalone_long_term_vnd_specs"
    ] = standalone_long_term_vnd
    return base


def _repair_receipt(
    repair: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    material = {
        "base_page_json_sha256": repair["base_page_json_sha256"],
        "base_page_json_version_id": repair["base_page_json_version_id"],
        "cell_axis_sha256": canonical_json_sha256_v1(repair["cell_repairs"]),
        "effective_page_json_sha256": repair["effective_page_json_sha256"],
        "overlay_id": compiled_specs[
            "capital_contribution_dividend_income_source_repair_overlay"
        ]["overlay_id"],
        "repair_id": repair["repair_id"],
        "row_axis_sha256": canonical_json_sha256_v1(repair["row_repairs"]),
        "rule": (
            "EXACT_CONTENT_ADDRESSED_PDF_RENDER_AND_CROP_VISIBLE_LITERAL_"
            "TRANSCRIPTION_ONLY_PRIVATE_CLONE_NO_EQUATION_BACKSOLVE"
        ),
        "source_binding": canonical_clone_v1(repair["source_binding"]),
        "status": "AUTHENTICATED_PDF_VISIBLE_SOURCE_TRANSCRIBED",
        "table_ref": canonical_clone_v1(repair["table_ref"]),
        "visual_evidence": canonical_clone_v1(repair["visual_evidence"]),
    }
    return {
        **material,
        "receipt_id": "gjccdifav1:repair-receipt:"
        + canonical_json_sha256_v1(material),
    }


def _apply_repairs_to_pages(
    *,
    page_json_by_version: Mapping[str, dict[str, Any]],
    source_by_version: Mapping[str, Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    pages = {
        version_id: canonical_clone_v1(page)
        for version_id, page in page_json_by_version.items()
    }
    overlay = compiled_specs.get(
        "capital_contribution_dividend_income_source_repair_overlay"
    )
    if type(overlay) is not dict:
        raise _error("Family-35 compiled source-repair overlay is invalid")
    receipts = []
    for repair in overlay["repairs"]:
        version_id = repair["base_page_json_version_id"]
        if version_id not in pages:
            continue
        source = repair["source_binding"]
        locator = source_by_version.get(version_id)
        if (
            not isinstance(locator, Mapping)
            or locator.get("document_id") != source["document_id"]
            or locator.get("source_logical_name") != source["source_logical_name"]
            or locator.get("source_sha256") != source["source_sha256"]
            or locator.get("physical_page") != source["physical_page"]
        ):
            raise _error("Family-35 source-repair source identity drifted")
        base_page = page_json_by_version[version_id]
        if canonical_json_sha256_v1(base_page) != repair["base_page_json_sha256"]:
            raise _error("Family-35 source-repair base page drifted")
        table_ref = repair["table_ref"]
        _base_section, base_table = _source_table(
            base_page,
            section_id=table_ref["section_id"],
            table_id=table_ref["table_id"],
        )
        if canonical_json_sha256_v1(base_table) != table_ref["base_table_sha256"]:
            raise _error("Family-35 source-repair base table drifted")
        _section, table = _source_table(
            pages[version_id],
            section_id=table_ref["section_id"],
            table_id=table_ref["table_id"],
        )
        rows = table.get("rows")
        columns = table.get("columns")
        if type(rows) is not list or type(columns) is not list:
            raise _error("Family-35 source-repair table axes are invalid")
        for cell in repair["cell_repairs"]:
            match = re.fullmatch(r"r([1-9][0-9]*):c([1-9][0-9]*)", cell["cell_id"])
            assert match is not None
            row_index = int(match.group(1)) - 1
            column_index = int(match.group(2)) - 1
            if not (0 <= row_index < len(rows) and 0 <= column_index < len(columns)):
                raise _error("Family-35 source-repair cell is outside its table")
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
                    row.get("hierarchy_path_exact"), cell["row_hierarchy_path_exact"]
                )
                or not same_typed_json_v1(
                    column.get("header_path_exact"), cell["column_header_path_exact"]
                )
                or not same_typed_json_v1(values[column_index], cell["before_exact"])
            ):
                raise _error("Family-35 source-repair cell binding drifted")
            values[column_index] = cell["after_exact"]
        for row_repair in repair["row_repairs"]:
            row_index = int(row_repair["row_id"][1:]) - 1
            if not 0 <= row_index < len(rows):
                raise _error("Family-35 source-repair row is outside its table")
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
                raise _error("Family-35 source-repair row binding drifted")
            row["label_exact"] = row_repair["after_label_exact"]
            row["hierarchy_path_exact"] = canonical_clone_v1(
                row_repair["after_hierarchy_path_exact"]
            )
        if canonical_json_sha256_v1(table) != table_ref["effective_table_sha256"]:
            raise _error("Family-35 source-repair effective table drifted")
        if canonical_json_sha256_v1(pages[version_id]) != repair["effective_page_json_sha256"]:
            raise _error("Family-35 source-repair effective page drifted")
        receipts.append(_repair_receipt(repair, compiled_specs=compiled_specs))
    receipts.sort(key=lambda item: item["repair_id"])
    return pages, receipts


def _source_axis_from_regions(
    regions: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    axis: dict[str, Mapping[str, Any]] = {}
    for region in regions:
        version_id = region.get("page_json_version_id")
        if type(version_id) is not str:
            raise _error("Family-35 region version is invalid")
        prior = axis.setdefault(version_id, region)
        if any(
            prior.get(key) != region.get(key)
            for key in (
                "document_id",
                "source_logical_name",
                "source_sha256",
                "physical_page",
            )
        ):
            raise _error("Family-35 region source identity conflicts")
    return axis


def _repair_page_records(
    page_records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pages = {}
    sources = {}
    for record in page_records:
        version_id = record.get("page_json_version_id")
        page = record.get("page_json")
        if type(version_id) is not str or type(page) is not dict or version_id in pages:
            raise _error("Family-35 page record axis is invalid")
        pages[version_id] = page
        sources[version_id] = record
    effective, receipts = _apply_repairs_to_pages(
        page_json_by_version=pages,
        source_by_version=sources,
        compiled_specs=compiled_specs,
    )
    return [
        {**canonical_clone_v1(record), "page_json": effective[record["page_json_version_id"]]}
        for record in page_records
    ], receipts


def _reseal_cluster(cluster: Mapping[str, Any], **updates: Any) -> dict[str, Any]:
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


def _primary_root_occurrences(
    page_records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    primary_specs = compiled_specs[
        "capital_contribution_dividend_income_primary_specs"
    ]
    aliases = set(primary_specs["topology"]["parent"]["aliases"])
    occurrences = []
    for record in page_records:
        page = record["page_json"]
        if page.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
            continue
        sections = page.get("sections")
        for section_ordinal, section in enumerate(
            sections if type(sections) is list else [], start=1
        ):
            if (
                type(section) is not dict
                or section.get("content_kind") != "PRIMARY_STATEMENT"
                or section.get("statement_type") != "INCOME_STATEMENT"
            ):
                continue
            tables = section.get("tables")
            for table_ordinal, table in enumerate(
                tables if type(tables) is list else [], start=1
            ):
                if type(table) is not dict:
                    continue
                columns = table.get("columns")
                money_ordinals = [
                    ordinal
                    for ordinal, column in enumerate(
                        columns if type(columns) is list else [], start=1
                    )
                    if type(column) is dict and column.get("value_kind") == "MONEY"
                ]
                if len(money_ordinals) < 2:
                    continue
                rows = table.get("rows")
                for row_ordinal, row in enumerate(
                    rows if type(rows) is list else [], start=1
                ):
                    if type(row) is not dict:
                        continue
                    label = _without_leading_ordinal(_normalized(row.get("label_exact")))
                    values = row.get("values_exact")
                    if (
                        label not in aliases
                        or type(values) is not list
                        or not any(
                            ordinal <= len(values) and values[ordinal - 1] is not None
                            for ordinal in money_ordinals
                        )
                    ):
                        continue
                    occurrences.append(
                        {
                            "label_exact": row.get("label_exact"),
                            "money_column_ordinals": money_ordinals,
                            "record": record,
                            "row_ordinal": row_ordinal,
                            "section_id": f"s{section_ordinal}",
                            "table_id": f"t{table_ordinal}",
                        }
                    )
    return occurrences


def recover_gemini_json_capital_contribution_dividend_income_query_cluster_v1(
    *,
    page_records: Any,
    base_cluster: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Recover repaired detail or one exact primary income-statement root."""

    if compiled_specs.get("topology", {}).get("family_id") != FAMILY_ID:
        raise _error("Family-35 adapter received another family")
    if type(page_records) not in {list, tuple} or not page_records:
        raise _error("Family-35 page record axis is invalid")
    records, repair_receipts = _repair_page_records(
        page_records, compiled_specs=compiled_specs
    )
    repaired_cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled_specs
    )
    # A registered literal repair is authoritative for its private replay.  If
    # it does not improve the disposition, retain the safer of the two states.
    priority = {READY: 2, UNRESOLVED: 1, NOT_OBSERVED: 0}
    selected = (
        repaired_cluster
        if priority.get(repaired_cluster.get("status"), -1)
        >= priority.get(base_cluster.get("status"), -1)
        else canonical_clone_v1(base_cluster)
    )
    if selected.get("status") != NOT_OBSERVED:
        return selected

    occurrences = _primary_root_occurrences(records, compiled_specs=compiled_specs)
    if not occurrences:
        return selected
    if len(occurrences) != 1:
        return _reseal_cluster(
            selected,
            component_regions=[],
            owner_receipt=None,
            reasons=["MULTIPLE_EXACT_PRIMARY_INCOME_STATEMENT_FAMILY_ROOTS"],
            status=UNRESOLVED,
        )
    occurrence = occurrences[0]
    record = canonical_clone_v1(occurrence["record"])
    section_ordinal = int(occurrence["section_id"][1:])
    section = record["page_json"]["sections"][section_ordinal - 1]
    before_page_sha = canonical_json_sha256_v1(record["page_json"])
    section["statement_type"] = "BALANCE_SHEET"
    after_page_sha = canonical_json_sha256_v1(record["page_json"])
    primary_specs = compiled_specs[
        "capital_contribution_dividend_income_primary_specs"
    ]
    projected = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[record], compiled_specs=primary_specs
    )
    if projected.get("status") != READY or len(projected.get("component_regions", [])) != 1:
        return _reseal_cluster(
            selected,
            component_regions=[],
            owner_receipt=None,
            reasons=["EXACT_PRIMARY_INCOME_STATEMENT_ROOT_NOT_LOCALLY_USABLE"],
            status=UNRESOLVED,
        )
    material = {
        "adapter_format_version": ADAPTER_FORMAT_VERSION,
        "after_page_json_sha256": after_page_sha,
        "before_page_json_sha256": before_page_sha,
        "label_exact": occurrence["label_exact"],
        "locator": {
            key: occurrence["record"][key]
            for key in (
                "document_id",
                "document_ordinal",
                "page_json_version_id",
                "physical_page",
                "selected_page_ordinal",
                "source_logical_name",
                "source_sha256",
            )
        }
        | {
            "section_id": occurrence["section_id"],
            "table_id": occurrence["table_id"],
            "row_id": f"r{occurrence['row_ordinal']}",
            "row_ordinal": occurrence["row_ordinal"],
        },
        "money_column_ordinals": occurrence["money_column_ordinals"],
        "policy": PRIMARY_ROOT_POLICY,
        "repair_receipt_ids": [item["receipt_id"] for item in repair_receipts],
        "rule": (
            "UNIQUE_EXACT_VISIBLE_ROOT_ON_PRIMARY_INCOME_STATEMENT_SELECTED_ONLY_"
            "AFTER_DETAILED_FAMILY_NOT_OBSERVED_PRIVATE_STATEMENT_SEMANTIC_"
            "PROJECTION_VALUES_ROWS_COLUMNS_AND_LOCATORS_UNCHANGED"
        ),
        "statement_type_after": "BALANCE_SHEET",
        "statement_type_before": "INCOME_STATEMENT",
    }
    projection_receipt = {
        **material,
        "receipt_id": "gjccdifav1:primary-root:" + canonical_json_sha256_v1(material),
    }
    owner_receipt = canonical_clone_v1(projected["owner_receipt"])
    owner_receipt["capital_contribution_dividend_income_primary_root_receipt"] = (
        projection_receipt
    )
    return _reseal_cluster(projected, owner_receipt=owner_receipt)


def coalesce_gemini_json_capital_contribution_dividend_income_document_v1(
    *, page_records: Any, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=page_records, compiled_specs=compiled_specs
    )
    return recover_gemini_json_capital_contribution_dividend_income_query_cluster_v1(
        page_records=page_records,
        base_cluster=base,
        compiled_specs=compiled_specs,
    )


def adapt_gemini_json_capital_contribution_dividend_income_indexed_query_evidence_v1(
    *,
    indexed_query_evidence: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild the indexed axis after deterministic Family-35 recoveries."""

    checked = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        indexed_query_evidence,
        compiled_specs=compiled_specs,
    )
    cluster_by_ordinal = {
        item["document_ordinal"]: item["cluster"]
        for item in checked["candidate_dispositions"]
    }
    pages_by_ordinal: dict[int, list[dict[str, Any]]] = {}
    for axis in checked["selected_page_axis"]:
        ordinal = axis["document_ordinal"]
        page = page_json_by_document.get(ordinal, {}).get(axis["page_json_version_id"])
        if type(page) is not dict:
            raise _error("Family-35 indexed replay page is absent")
        pages_by_ordinal.setdefault(ordinal, []).append(
            {**canonical_clone_v1(axis), "page_json": page}
        )
    clusters = []
    for document in checked["selected_document_axis"]:
        ordinal = document["document_ordinal"]
        base = cluster_by_ordinal.get(ordinal)
        if type(base) is not dict:
            raise _error("Family-35 indexed base cluster is absent")
        clusters.append(
            recover_gemini_json_capital_contribution_dividend_income_query_cluster_v1(
                page_records=pages_by_ordinal.get(ordinal, []),
                base_cluster=base,
                compiled_specs=compiled_specs,
            )
        )
    rebuilt = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=checked["selected_document_axis"],
        selected_page_axis=checked["selected_page_axis"],
        document_clusters=clusters,
        query_policy_sha256=canonical_json_sha256_v1(compiled_specs["query_policy"]),
    )
    return validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        rebuilt,
        compiled_specs=compiled_specs,
    )


def build_gemini_json_capital_contribution_dividend_income_region_query_receipt_v1(
    regions: Any,
    *,
    cluster: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    shared = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
    projection = None
    if cluster is not None:
        owner = cluster.get("owner_receipt")
        if type(owner) is dict:
            projection = owner.get(
                "capital_contribution_dividend_income_primary_root_receipt"
            )
    material = {
        "format_version": (
            "GEMINI_JSON_CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_QUERY_RECEIPT_V1"
        ),
        "primary_root_projection_receipt": canonical_clone_v1(projection),
        "shared_query_receipt": shared,
    }
    return {
        **material,
        "query_receipt_id": "gjccdifav1:query-receipt:"
        + canonical_json_sha256_v1(material),
    }


def _validate_query_receipt(value: Any, *, regions: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise _error("Family-35 query receipt is invalid")
    expected_shared = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        regions
    )
    fields = {
        "format_version",
        "primary_root_projection_receipt",
        "query_receipt_id",
        "shared_query_receipt",
    }
    if (
        set(value) != fields
        or value.get("format_version")
        != "GEMINI_JSON_CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_QUERY_RECEIPT_V1"
        or not same_typed_json_v1(value.get("shared_query_receipt"), expected_shared)
    ):
        raise _error("Family-35 query receipt does not bind exact fragments")
    material = {key: value[key] for key in value if key != "query_receipt_id"}
    if value["query_receipt_id"] != "gjccdifav1:query-receipt:" + canonical_json_sha256_v1(material):
        raise _error("Family-35 query receipt identity does not replay")
    return canonical_clone_v1(value)


def _project_primary_root_page(
    *,
    pages: dict[str, dict[str, Any]],
    projection: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    locator = projection.get("locator")
    if (
        type(locator) is not dict
        or projection.get("policy") != PRIMARY_ROOT_POLICY
        or projection.get("statement_type_before") != "INCOME_STATEMENT"
        or projection.get("statement_type_after") != "BALANCE_SHEET"
    ):
        raise _error("Family-35 primary-root projection receipt is invalid")
    version_id = locator.get("page_json_version_id")
    page = pages.get(version_id)
    if type(page) is not dict or canonical_json_sha256_v1(page) != projection.get(
        "before_page_json_sha256"
    ):
        raise _error("Family-35 primary-root projection source drifted")
    try:
        section = page["sections"][int(locator["section_id"][1:]) - 1]
        table = section["tables"][int(locator["table_id"][1:]) - 1]
        row = table["rows"][locator["row_ordinal"] - 1]
    except (IndexError, KeyError, TypeError, ValueError) as exc:
        raise _error("Family-35 primary-root projection locator is invalid") from exc
    primary = compiled_specs[
        "capital_contribution_dividend_income_primary_specs"
    ]
    aliases = set(primary["topology"]["parent"]["aliases"])
    if (
        page.get("status") != "PRIMARY_FINANCIAL_STATEMENT"
        or section.get("content_kind") != "PRIMARY_STATEMENT"
        or section.get("statement_type") != "INCOME_STATEMENT"
        or row.get("label_exact") != projection.get("label_exact")
        or _without_leading_ordinal(_normalized(row.get("label_exact"))) not in aliases
        or f"r{locator['row_ordinal']}" != locator.get("row_id")
    ):
        raise _error("Family-35 primary-root projection semantic source drifted")
    section["statement_type"] = "BALANCE_SHEET"
    if canonical_json_sha256_v1(page) != projection.get("after_page_json_sha256"):
        raise _error("Family-35 primary-root projection output drifted")
    material = canonical_clone_v1(projection)
    if material.pop("receipt_id", None) != "gjccdifav1:primary-root:" + canonical_json_sha256_v1(material):
        raise _error("Family-35 primary-root projection identity drifted")
    return pages, canonical_clone_v1(projection)


def _standalone_vnd_evidence(
    *,
    pages: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    vnd_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Require local VND or a unique explicit VND unit across the document."""

    local = []
    document = []
    primary_statement = []
    region_keys = {
        (item["page_json_version_id"], item["section_id"], item["table_id"])
        for item in regions
    }
    for version_id, page in pages.items():
        for section_ordinal, section in enumerate(page.get("sections") or [], start=1):
            if type(section) is not dict:
                continue
            for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
                if type(table) is not dict:
                    continue
                axis = _unit_axis(
                    table, compiled_specs=vnd_specs, document_unit_context=None
                )
                if not axis.get("complete"):
                    continue
                item = {
                    "canonical_unit": axis["canonical_unit"],
                    "evidence": canonical_clone_v1(axis.get("evidence", [])),
                    "page_json_version_id": version_id,
                    "section_id": f"s{section_ordinal}",
                    "source": axis.get("source"),
                    "table_id": f"t{table_ordinal}",
                }
                document.append(item)
                if (
                    page.get("status") == "PRIMARY_FINANCIAL_STATEMENT"
                    and section.get("content_kind") == "PRIMARY_STATEMENT"
                ):
                    primary_statement.append(item)
                if (version_id, f"s{section_ordinal}", f"t{table_ordinal}") in region_keys:
                    local.append(item)
    if local and {item["canonical_unit"] for item in local} == {"VND"}:
        rule = "EVERY_SELECTED_TABLE_HAS_EXPLICIT_LOCAL_VND"
        evidence = local
    elif document and {item["canonical_unit"] for item in document} == {"VND"}:
        rule = "DOCUMENT_EXPLICIT_TABLE_UNIT_CONSENSUS_IS_UNIQUELY_VND"
        evidence = document
    elif (
        region_keys
        and all(
            pages[version_id].get("status") == "PRIMARY_FINANCIAL_STATEMENT"
            for version_id, _section_id, _table_id in region_keys
        )
        and len({item["page_json_version_id"] for item in primary_statement}) >= 2
        and {item["canonical_unit"] for item in primary_statement} == {"VND"}
    ):
        rule = (
            "PRIMARY_FINANCIAL_STATEMENT_EXPLICIT_UNIT_CONSENSUS_ON_AT_LEAST_"
            "TWO_DISTINCT_PAGES_IS_UNIQUELY_VND"
        )
        evidence = primary_statement
    else:
        return None
    material = {
        "canonical_unit": "VND",
        "evidence": canonical_clone_v1(evidence),
        "policy": VND_RETRY_POLICY,
        "rule": rule,
        "target_unit_projections": [],
    }
    return {
        **material,
        "receipt_id": "gjccdifav1:vnd:" + canonical_json_sha256_v1(material),
    }


def _project_primary_statement_consensus_vnd(
    *,
    pages: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    receipt: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Project an exact primary-statement suite unit onto its unitless table.

    The projected literal is never represented as locally observed evidence:
    the returned receipt binds every target before/after page and table hash to
    the independently observed multi-page primary-statement unit consensus.
    """

    expected_rule = (
        "PRIMARY_FINANCIAL_STATEMENT_EXPLICIT_UNIT_CONSENSUS_ON_AT_LEAST_"
        "TWO_DISTINCT_PAGES_IS_UNIQUELY_VND"
    )
    if receipt.get("rule") != expected_rule:
        return (
            {key: canonical_clone_v1(page) for key, page in pages.items()},
            canonical_clone_v1(receipt),
        )
    effective = {key: canonical_clone_v1(page) for key, page in pages.items()}
    projections = []
    seen: set[tuple[str, str, str]] = set()
    for region in regions:
        key = (
            region["page_json_version_id"],
            region["section_id"],
            region["table_id"],
        )
        if key in seen:
            continue
        seen.add(key)
        version_id, section_id, table_id = key
        page = effective.get(version_id)
        if type(page) is not dict or page.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
            raise _error("Family-35 primary VND projection target is not a primary page")
        section, table = _source_table(page, section_id=section_id, table_id=table_id)
        if section.get("content_kind") != "PRIMARY_STATEMENT" or table.get("unit_exact") is not None:
            raise _error("Family-35 primary VND projection target is not exactly unitless")
        before_page = canonical_json_sha256_v1(page)
        before_table = canonical_json_sha256_v1(table)
        table["unit_exact"] = "VND"
        projections.append(
            {
                "after_page_json_sha256": canonical_json_sha256_v1(page),
                "after_table_sha256": canonical_json_sha256_v1(table),
                "before_page_json_sha256": before_page,
                "before_table_sha256": before_table,
                "locator": {
                    key: region[key]
                    for key in (
                        "document_id",
                        "document_ordinal",
                        "page_json_version_id",
                        "physical_page",
                        "section_id",
                        "source_logical_name",
                        "source_sha256",
                        "table_id",
                    )
                },
                "projected_unit_exact": "VND",
                "source_unit_exact": None,
            }
        )
    if not projections:
        raise _error("Family-35 primary VND projection target axis is empty")
    material = {
        key: canonical_clone_v1(value)
        for key, value in receipt.items()
        if key != "receipt_id"
    }
    material["target_unit_projections"] = projections
    return effective, {
        **material,
        "receipt_id": "gjccdifav1:vnd:" + canonical_json_sha256_v1(material),
    }


def _candidate_vnd_is_source_proven(candidate: Mapping[str, Any]) -> bool:
    receipts = candidate.get("closure_receipt", {}).get("table_receipts")
    if type(receipts) is not list or not receipts:
        return False
    axes = [item.get("unit_axis") for item in receipts if type(item) is dict]
    return bool(
        axes
        and all(
            type(axis) is dict
            and axis.get("complete") is True
            and axis.get("canonical_unit") == "VND"
            and axis.get("source")
            in {"LOCAL_TABLE_UNIT", "DOCUMENT_EXPLICIT_TABLE_UNIT_CONSENSUS"}
            for axis in axes
        )
    )


def _normalize_explicit_local_vnd_zero_decimal_suffixes(
    *,
    pages: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    vnd_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Normalize only a literal `,00` suffix under an explicit local VND unit.

    Vietnamese VND statements occasionally print an integer as
    ``8.303.955.000,00``.  The shared locale parser intentionally remains
    generic and can read this surface as a differently grouped integer.  This
    family-local projection removes only the literal zero-decimal suffix on a
    private clone.  It does not round, scale, infer a unit, or accept a nonzero
    fractional suffix.  The original source text is restored on every emitted
    mapping cell and the exact projected cells are recorded below.
    """

    effective = {
        version_id: canonical_clone_v1(page) for version_id, page in pages.items()
    }
    projections: list[dict[str, Any]] = []
    seen_tables: set[tuple[str, str, str]] = set()
    for region in regions:
        version_id = region["page_json_version_id"]
        section_id = region["section_id"]
        table_id = region["table_id"]
        table_key = (version_id, section_id, table_id)
        if table_key in seen_tables:
            continue
        seen_tables.add(table_key)
        page = effective.get(version_id)
        if type(page) is not dict:
            raise _error("Family-35 VND zero-decimal target page is absent")
        _section, table = _source_table(
            page, section_id=section_id, table_id=table_id
        )
        unit_axis = _unit_axis(
            table, compiled_specs=vnd_specs, document_unit_context=None
        )
        if (
            unit_axis.get("complete") is not True
            or unit_axis.get("canonical_unit") != "VND"
            or unit_axis.get("source") != "LOCAL_TABLE_UNIT"
        ):
            continue
        columns = table.get("columns")
        rows = table.get("rows")
        if type(columns) is not list or type(rows) is not list:
            raise _error("Family-35 VND zero-decimal target axes are invalid")
        money_ordinals = [
            ordinal
            for ordinal, column in enumerate(columns, start=1)
            if type(column) is dict and column.get("value_kind") == "MONEY"
        ]
        for row_ordinal, row in enumerate(rows, start=1):
            values = row.get("values_exact") if type(row) is dict else None
            if type(values) is not list or len(values) != len(columns):
                continue
            for column_ordinal in money_ordinals:
                source = values[column_ordinal - 1]
                if type(source) is not str:
                    continue
                stripped = source.strip()
                match = _VND_ZERO_DECIMAL_SUFFIX.fullmatch(stripped)
                if match is None or bool(match.group("open")) != bool(
                    match.group("close")
                ):
                    continue
                normalized = (
                    ("(" if match.group("open") else "")
                    + (match.group("sign") or "")
                    + match.group("body")
                    + (")" if match.group("close") else "")
                )
                before_table = canonical_json_sha256_v1(table)
                values[column_ordinal - 1] = normalized
                after_table = canonical_json_sha256_v1(table)
                locator = {
                    key: region[key]
                    for key in (
                        "document_id",
                        "document_ordinal",
                        "page_json_version_id",
                        "physical_page",
                        "section_id",
                        "source_logical_name",
                        "source_sha256",
                        "table_id",
                    )
                }
                material = {
                    "after_exact": normalized,
                    "after_table_sha256": after_table,
                    "before_exact": source,
                    "before_table_sha256": before_table,
                    "column_header_path_exact": canonical_clone_v1(
                        columns[column_ordinal - 1].get("header_path_exact")
                    ),
                    "column_ordinal": column_ordinal,
                    "locator": locator,
                    "policy": VND_ZERO_DECIMAL_SUFFIX_POLICY,
                    "row_hierarchy_path_exact": canonical_clone_v1(
                        row.get("hierarchy_path_exact")
                    ),
                    "row_label_exact": row.get("label_exact"),
                    "row_ordinal": row_ordinal,
                    "rule": (
                        "LITERAL_ZERO_DECIMAL_SUFFIX_REMOVED_FOR_INTEGER_PARSE_"
                        "ONLY_NO_ROUNDING_NO_SCALING"
                    ),
                    "unit_axis": canonical_clone_v1(unit_axis),
                }
                projections.append(
                    {
                        **material,
                        "projection_id": "gjccdifav1:vnd-zero-decimal:"
                        + canonical_json_sha256_v1(material),
                    }
                )
    return effective, projections


def _restore_vnd_zero_decimal_source_cells(
    candidate: dict[str, Any],
    *,
    projections: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not projections:
        return candidate
    by_cell = {
        (
            item["locator"]["page_json_version_id"],
            item["locator"]["section_id"],
            item["locator"]["table_id"],
            item["row_ordinal"],
            item["column_ordinal"],
        ): item
        for item in projections
    }
    candidate = canonical_clone_v1(candidate)
    for mapping in candidate.get("mappings", []):
        source_refs = mapping.get("source_refs")
        values = mapping.get("values")
        if type(source_refs) is not list or type(values) is not list:
            continue
        for lane, cell in enumerate(values):
            if type(cell) is not dict or cell.get("source_text") is None:
                continue
            matches = []
            for source_ref in source_refs:
                locator = source_ref.get("locator") if type(source_ref) is dict else None
                ordinals = (
                    source_ref.get("money_column_ordinals")
                    if type(source_ref) is dict
                    else None
                )
                if (
                    type(locator) is not dict
                    or type(ordinals) is not list
                    or lane >= len(ordinals)
                    or type(source_ref.get("row_ordinal")) is not int
                ):
                    continue
                key = (
                    locator.get("page_json_version_id"),
                    locator.get("section_id"),
                    locator.get("table_id"),
                    source_ref["row_ordinal"],
                    ordinals[lane],
                )
                projection = by_cell.get(key)
                if projection is not None:
                    matches.append(projection)
            if not matches:
                continue
            before = {item["before_exact"] for item in matches}
            after = {item["after_exact"] for item in matches}
            if (
                len(before) != 1
                or len(after) != 1
                or cell.get("source_text") not in after
            ):
                raise _error("Family-35 VND zero-decimal mapping provenance conflicts")
            cell["source_text"] = next(iter(before))
            cell["state"] = "RAW_VND_INTEGER_WITH_EXPLICIT_ZERO_DECIMAL_SUFFIX"
        material = {
            key: value for key, value in mapping.items() if key != "item_mapping_id"
        }
        mapping["item_mapping_id"] = "gjmthfmv1:item:" + canonical_json_sha256_v1(
            material
        )
    return candidate


def _prefer_visible_root_over_incomplete_component_equation(
    candidate: dict[str, Any],
    *,
    pages: Mapping[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Keep one printed root when a sibling component lane is source-blank.

    A complete source total remains authoritative even when only one lane of
    the component equation can be checked.  The shared evaluator historically
    excluded a partially observed component from the derived-root frontier,
    which could understate the *observed* lane.  This correction is deliberately
    narrow: one printed total, one incomplete all-preceding equation, one
    obsolete derived-root equation, and an existing partial component mapping
    are all required.  No missing component value is synthesized.
    """

    if candidate.get("status") != READY:
        return candidate, None
    closure = candidate.get("closure_receipt")
    equations = closure.get("equations") if type(closure) is dict else None
    mappings = candidate.get("mappings")
    if type(equations) is not list or type(mappings) is not list:
        return candidate, None
    visible = [
        item
        for item in equations
        if item.get("equation_kind")
        == "EXACT_ALL_PRECEDING_NON_TOTAL_ROWS_EQUAL_PRINTED_TOTAL"
        and item.get("status") == "INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL"
        and type(item.get("lane_statuses")) is list
        and "EXACT" in item["lane_statuses"]
        and "INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL" in item["lane_statuses"]
        and type(item.get("result_coefficients")) is list
        and all(type(value) is int for value in item["result_coefficients"])
        and type(item.get("result_source_refs")) is list
        and len(item["result_source_refs"]) == 1
    ]
    obsolete = [
        item
        for item in equations
        if item.get("equation_kind")
        == "EXACT_COMPLETE_TOP_LEVEL_COMPONENT_SUM_DERIVES_FAMILY_ROOT"
        and item.get("result_role") == "FAMILY_ROOT_TOTAL"
    ]
    roots = [item for item in mappings if item.get("role") == "FAMILY_ROOT_TOTAL"]
    partials = [
        item
        for item in mappings
        if item.get("role") != "FAMILY_ROOT_TOTAL"
        and type(item.get("values")) is list
        and any(cell.get("coefficient") is None for cell in item["values"])
        and any(type(cell.get("coefficient")) is int for cell in item["values"])
    ]
    if not (
        len(visible) == len(obsolete) == len(roots) == len(partials) == 1
        and [cell.get("coefficient") for cell in roots[0]["values"]]
        == obsolete[0].get("result_coefficients")
        and visible[0].get("result_coefficients")
        != obsolete[0].get("result_coefficients")
    ):
        return candidate, None
    source_ref = visible[0]["result_source_refs"][0]
    locator = source_ref.get("locator")
    ordinals = source_ref.get("money_column_ordinals")
    if type(locator) is not dict or type(ordinals) is not list:
        return candidate, None
    page = pages.get(locator.get("page_json_version_id"))
    if type(page) is not dict:
        raise _error("Family-35 printed partial-equation root page is absent")
    _section, table = _source_table(
        page,
        section_id=locator["section_id"],
        table_id=locator["table_id"],
    )
    try:
        row = table["rows"][source_ref["row_ordinal"] - 1]
        source_values = [row["values_exact"][ordinal - 1] for ordinal in ordinals]
    except (IndexError, KeyError, TypeError) as exc:
        raise _error("Family-35 printed partial-equation root locator drifted") from exc
    cells = [_source_money(value) for value in source_values]
    if (
        any(cell["coefficient"] is None for cell in cells)
        or [cell["coefficient"] for cell in cells]
        != visible[0]["result_coefficients"]
    ):
        raise _error("Family-35 printed partial-equation root values drifted")
    candidate = canonical_clone_v1(candidate)
    root = next(
        item for item in candidate["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL"
    )
    root.update(
        {
            "row_id": source_ref["row_id"],
            "source_refs": canonical_clone_v1(visible[0]["result_source_refs"]),
            "state": "SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_WITH_INCOMPLETE_COMPONENT_EQUATION",
            "values": cells,
        }
    )
    mapping_material = {
        key: value for key, value in root.items() if key != "item_mapping_id"
    }
    root["item_mapping_id"] = "gjmthfmv1:item:" + canonical_json_sha256_v1(
        mapping_material
    )
    candidate["closure_receipt"]["equations"] = [
        item
        for item in candidate["closure_receipt"]["equations"]
        if item.get("equation_id") != obsolete[0].get("equation_id")
    ]
    candidate["closure_receipt"]["root_component_sum_receipts"] = [
        {
            "coefficients": [cell["coefficient"] for cell in cells],
            "component_roles": canonical_clone_v1(visible[0]["component_roles"]),
            "lane_statuses": canonical_clone_v1(visible[0]["lane_statuses"]),
            "result_state": root["state"],
            "rule": (
                "SOURCE_VISIBLE_ROOT_PRESERVED_WHEN_COMPONENT_EQUATION_HAS_"
                "AN_EXACT_LANE_AND_A_SOURCE_BLANK_LANE"
            ),
            "source_refs": canonical_clone_v1(visible[0]["result_source_refs"]),
        }
    ]
    material = {
        "discarded_derived_equation_id": obsolete[0]["equation_id"],
        "partial_component_role": partials[0]["role"],
        "policy": (
            "PRINTED_ROOT_VALUES_GOVERN_INCOMPLETE_COMPONENT_EQUATION_NO_"
            "BLANK_VALUE_SYNTHESIS"
        ),
        "result_coefficients": [cell["coefficient"] for cell in cells],
        "result_source_refs": canonical_clone_v1(visible[0]["result_source_refs"]),
        "source_equation_id": visible[0]["equation_id"],
        "source_lane_statuses": canonical_clone_v1(visible[0]["lane_statuses"]),
    }
    return candidate, {
        **material,
        "receipt_id": "gjccdifav1:partial-root:"
        + canonical_json_sha256_v1(material),
    }


def _standalone_long_term_leaf_evidence(
    *,
    pages: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Find one ambiguous label that is provably a leaf, not a carrier.

    Some banks print ``Thu nhập góp vốn, mua cổ phần`` as a standalone
    component below an explicit family note, while others use the same text as
    the structural carrier of narrower children.  The ordinary topology must
    not globally alias those two shapes.  This guard admits only one ITEM row
    with a one-element path, no descendants, one visible direct carrier and a
    printed total in the same explicitly owned table.  The shared evaluator
    still has to prove the complete arithmetic after the semantic retry.
    """

    adapter = compiled_specs.get(
        "capital_contribution_dividend_income_adapter_spec"
    )
    if type(adapter) is not dict:
        raise _error("Family-35 standalone long-term adapter spec is absent")
    aliases = {
        _normalized(alias)
        for alias in adapter["standalone_long_term_leaf_aliases"]
    }
    direct_aliases = set(compiled_specs.get("aliases_by_role", {}).get(
        "DIRECT_DIVIDEND", []
    ))
    parent_aliases = set(compiled_specs.get("topology", {}).get("parent", {}).get(
        "aliases", []
    ))
    if not aliases or not direct_aliases or not parent_aliases:
        raise _error("Family-35 standalone long-term alias axes are empty")

    occurrences: list[dict[str, Any]] = []
    seen_tables: set[tuple[str, str, str]] = set()
    for region in regions:
        version_id = region["page_json_version_id"]
        key = (version_id, region["section_id"], region["table_id"])
        if key in seen_tables:
            continue
        seen_tables.add(key)
        page = pages.get(version_id)
        if type(page) is not dict:
            raise _error("Family-35 standalone long-term page is absent")
        section, table = _source_table(
            page,
            section_id=region["section_id"],
            table_id=region["table_id"],
        )
        owner_surfaces = [section.get("title_exact"), table.get("title_exact")]
        if not any(
            _without_leading_ordinal(_normalized(surface)) in parent_aliases
            for surface in owner_surfaces
            if type(surface) is str
        ):
            continue
        rows = table.get("rows")
        if type(rows) is not list:
            raise _error("Family-35 standalone long-term row axis is invalid")
        normalized_paths = [
            [
                _normalized(item)
                for item in row.get("hierarchy_path_exact", [])
                if type(item) is str and _normalized(item)
            ]
            if type(row) is dict
            and type(row.get("hierarchy_path_exact")) is list
            else []
            for row in rows
        ]
        direct_rows = [
            ordinal
            for ordinal, row in enumerate(rows, start=1)
            if type(row) is dict
            and _normalized(row.get("label_exact")) in direct_aliases
            and type(row.get("values_exact")) is list
            and any(value is not None for value in row["values_exact"])
        ]
        total_rows = [
            ordinal
            for ordinal, row in enumerate(rows, start=1)
            if type(row) is dict
            and row.get("row_kind") == "TOTAL"
            and type(row.get("values_exact")) is list
            and any(value is not None for value in row["values_exact"])
        ]
        if len(direct_rows) != 1 or len(total_rows) != 1:
            continue
        for ordinal, row in enumerate(rows, start=1):
            if type(row) is not dict:
                continue
            label = _normalized(row.get("label_exact"))
            path = normalized_paths[ordinal - 1]
            if (
                label not in aliases
                or row.get("row_kind") != "ITEM"
                or path != [label]
                or type(row.get("values_exact")) is not list
                or not any(value is not None for value in row["values_exact"])
                or any(
                    len(other_path) > len(path)
                    and other_path[: len(path)] == path
                    for other_ordinal, other_path in enumerate(
                        normalized_paths, start=1
                    )
                    if other_ordinal != ordinal
                )
            ):
                continue
            occurrences.append(
                {
                    "direct_carrier_row_ordinal": direct_rows[0],
                    "hierarchy_path_exact": canonical_clone_v1(
                        row["hierarchy_path_exact"]
                    ),
                    "label_exact": row["label_exact"],
                    "locator": {
                        key: region[key]
                        for key in (
                            "document_id",
                            "document_ordinal",
                            "page_json_version_id",
                            "physical_page",
                            "section_id",
                            "source_logical_name",
                            "source_sha256",
                            "table_id",
                        )
                    }
                    | {"row_id": f"r{ordinal}", "row_ordinal": ordinal},
                    "row_kind": row["row_kind"],
                    "source_values_exact": canonical_clone_v1(row["values_exact"]),
                    "total_row_ordinal": total_rows[0],
                }
            )
    if len(occurrences) != 1:
        return None
    return occurrences[0]


def _standalone_long_term_retry_consumes_evidence(
    candidate: Mapping[str, Any], *, evidence: Mapping[str, Any]
) -> bool:
    mappings = candidate.get("mappings")
    if candidate.get("status") != READY or type(mappings) is not list:
        return False
    targets = [
        item for item in mappings if item.get("role") == "LONG_TERM_CAPITAL_DIVIDEND"
    ]
    if len(targets) != 1 or type(targets[0].get("source_refs")) is not list:
        return False
    locator = evidence["locator"]
    return any(
        type(source_ref) is dict
        and source_ref.get("label_exact") == evidence["label_exact"]
        and source_ref.get("hierarchy_path_exact") == evidence["hierarchy_path_exact"]
        and source_ref.get("row_ordinal") == locator["row_ordinal"]
        and type(source_ref.get("locator")) is dict
        and all(
            source_ref["locator"].get(key) == locator[key]
            for key in (
                "page_json_version_id",
                "section_id",
                "table_id",
            )
        )
        for source_ref in targets[0]["source_refs"]
    )


def _standalone_long_term_retry_receipt(
    *,
    base_candidate: Mapping[str, Any],
    retry_candidate: Mapping[str, Any],
    evidence: Mapping[str, Any],
    retry_specs: Mapping[str, Any],
) -> dict[str, Any]:
    material = {
        "base_candidate_id": base_candidate["candidate_id"],
        "base_reasons": canonical_clone_v1(base_candidate.get("reasons", [])),
        "evidence": canonical_clone_v1(evidence),
        "policy": STANDALONE_LONG_TERM_LEAF_POLICY,
        "retry_candidate_id": retry_candidate["candidate_id"],
        "retry_query_policy_sha256": canonical_json_sha256_v1(
            retry_specs["query_policy"]
        ),
        "rule": (
            "UNIQUE_SOURCE_VISIBLE_STANDALONE_ITEM_SEMANTICALLY_ALIASED_ONLY_"
            "AFTER_BASE_FAILURE_SHARED_EXACT_CLOSURE_REQUIRED_VALUES_AND_"
            "SOURCE_LABELS_UNCHANGED"
        ),
        "status": "EXACT_SHARED_CLOSURE_RETRY_ACCEPTED",
    }
    return {
        **material,
        "receipt_id": "gjccdifav1:standalone-long-term:"
        + canonical_json_sha256_v1(material),
    }


def _reseal_candidate(
    candidate: dict[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
    projection_receipt: Mapping[str, Any] | None,
    partial_root_projection_receipt: Mapping[str, Any] | None,
    repair_receipts: Sequence[Mapping[str, Any]],
    standalone_long_term_leaf_retry_receipt: Mapping[str, Any] | None,
    vnd_receipt: Mapping[str, Any] | None,
    vnd_zero_decimal_projections: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if (
        projection_receipt is None
        and partial_root_projection_receipt is None
        and not repair_receipts
        and standalone_long_term_leaf_retry_receipt is None
        and vnd_receipt is None
        and not vnd_zero_decimal_projections
    ):
        return candidate
    material = {
        "adapter_format_version": ADAPTER_FORMAT_VERSION,
        "adapter_spec_sha256": canonical_json_sha256_v1(
            compiled_specs["capital_contribution_dividend_income_adapter_spec"]
        ),
        "primary_root_projection_receipt": canonical_clone_v1(projection_receipt),
        "partial_root_projection_receipt": canonical_clone_v1(
            partial_root_projection_receipt
        ),
        "shared_engine_claim_boundary": SHARED_CLAIM_BOUNDARY,
        "source_repair_overlay_id": compiled_specs[
            "capital_contribution_dividend_income_source_repair_overlay"
        ]["overlay_id"],
        "source_repair_receipts": canonical_clone_v1(list(repair_receipts)),
        "source_repair_spec_sha256": compiled_specs[
            "capital_contribution_dividend_income_source_repair_spec_sha256"
        ],
        "standalone_long_term_leaf_retry_receipt": canonical_clone_v1(
            standalone_long_term_leaf_retry_receipt
        ),
        "vnd_retry_receipt": canonical_clone_v1(vnd_receipt),
        "vnd_zero_decimal_projections": canonical_clone_v1(
            list(vnd_zero_decimal_projections)
        ),
    }
    candidate = canonical_clone_v1(candidate)
    candidate["claim_boundary"] = CLAIM_BOUNDARY
    candidate["closure_receipt"][
        "capital_contribution_dividend_income_adapter_receipt"
    ] = {
        **material,
        "adapter_receipt_id": "gjccdifav1:receipt:"
        + canonical_json_sha256_v1(material),
    }
    candidate_material = {
        key: value for key, value in candidate.items() if key != "candidate_id"
    }
    candidate["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        candidate_material
    )
    return candidate


def evaluate_gemini_json_capital_contribution_dividend_income_family_cluster_v1(
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate Family 35 with only exact, locally replayable adaptations."""

    if compiled_specs.get("topology", {}).get("family_id") != FAMILY_ID:
        raise _error("Family-35 adapter received another family")
    checked_receipt = _validate_query_receipt(query_receipt, regions=regions)
    region_axis = checked_receipt["shared_query_receipt"]["region_axis"]
    sources = _source_axis_from_regions(region_axis)
    pages, repairs = _apply_repairs_to_pages(
        page_json_by_version=page_json_by_version,
        source_by_version=sources,
        compiled_specs=compiled_specs,
    )
    projection = checked_receipt["primary_root_projection_receipt"]
    effective_specs = compiled_specs
    if projection is not None:
        pages, projection = _project_primary_root_page(
            pages=pages,
            projection=projection,
            compiled_specs=compiled_specs,
        )
        effective_specs = compiled_specs[
            "capital_contribution_dividend_income_primary_specs"
        ]
    zero_decimal_specs = compiled_specs[
        "capital_contribution_dividend_income_primary_vnd_specs"
        if projection is not None
        else "capital_contribution_dividend_income_vnd_specs"
    ]
    pages, vnd_zero_decimal_projections = (
        _normalize_explicit_local_vnd_zero_decimal_suffixes(
            pages=pages,
            regions=region_axis,
            vnd_specs=zero_decimal_specs,
        )
    )
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=region_axis,
        page_json_by_version=pages,
        compiled_specs=effective_specs,
        query_receipt=checked_receipt["shared_query_receipt"],
    )
    base_candidate = candidate
    standalone_long_term_evidence = None
    standalone_long_term_leaf_retry_receipt = None
    if candidate.get("status") != READY and projection is None:
        standalone_long_term_evidence = _standalone_long_term_leaf_evidence(
            pages=pages,
            regions=region_axis,
            compiled_specs=compiled_specs,
        )
        if standalone_long_term_evidence is not None:
            retry_specs = compiled_specs[
                "capital_contribution_dividend_income_standalone_long_term_specs"
            ]
            retry = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
                regions=region_axis,
                page_json_by_version=pages,
                compiled_specs=retry_specs,
                query_receipt=checked_receipt["shared_query_receipt"],
            )
            if _standalone_long_term_retry_consumes_evidence(
                retry, evidence=standalone_long_term_evidence
            ):
                candidate = retry
                standalone_long_term_leaf_retry_receipt = (
                    _standalone_long_term_retry_receipt(
                        base_candidate=base_candidate,
                        retry_candidate=retry,
                        evidence=standalone_long_term_evidence,
                        retry_specs=retry_specs,
                    )
                )
    vnd_receipt = None
    if candidate.get("status") != READY:
        if projection is not None:
            vnd_specs = compiled_specs[
                "capital_contribution_dividend_income_primary_vnd_specs"
            ]
        elif standalone_long_term_evidence is not None:
            vnd_specs = compiled_specs[
                "capital_contribution_dividend_income_standalone_long_term_vnd_specs"
            ]
        else:
            vnd_specs = compiled_specs[
                "capital_contribution_dividend_income_vnd_specs"
            ]
        vnd_evidence = _standalone_vnd_evidence(
            pages=pages,
            regions=region_axis,
            vnd_specs=vnd_specs,
        )
        if vnd_evidence is not None:
            retry_pages, vnd_evidence = _project_primary_statement_consensus_vnd(
                pages=pages,
                regions=region_axis,
                receipt=vnd_evidence,
            )
            retry = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
                regions=region_axis,
                page_json_by_version=retry_pages,
                compiled_specs=vnd_specs,
                query_receipt=checked_receipt["shared_query_receipt"],
            )
            standalone_consumed = (
                standalone_long_term_evidence is None
                or _standalone_long_term_retry_consumes_evidence(
                    retry, evidence=standalone_long_term_evidence
                )
            )
            if (
                retry.get("status") == READY
                and _candidate_vnd_is_source_proven(retry)
                and standalone_consumed
            ):
                candidate = retry
                vnd_receipt = vnd_evidence
                if standalone_long_term_evidence is not None:
                    standalone_long_term_leaf_retry_receipt = (
                        _standalone_long_term_retry_receipt(
                            base_candidate=base_candidate,
                            retry_candidate=retry,
                            evidence=standalone_long_term_evidence,
                            retry_specs=vnd_specs,
                        )
                    )
    candidate, partial_root_projection_receipt = (
        _prefer_visible_root_over_incomplete_component_equation(
            candidate,
            pages=pages,
        )
    )
    candidate = _restore_vnd_zero_decimal_source_cells(
        candidate,
        projections=vnd_zero_decimal_projections,
    )
    return _reseal_candidate(
        candidate,
        compiled_specs=compiled_specs,
        projection_receipt=projection,
        partial_root_projection_receipt=partial_root_projection_receipt,
        repair_receipts=repairs,
        standalone_long_term_leaf_retry_receipt=(
            standalone_long_term_leaf_retry_receipt
        ),
        vnd_receipt=vnd_receipt,
        vnd_zero_decimal_projections=vnd_zero_decimal_projections,
    )


def validate_gemini_json_capital_contribution_dividend_income_family_candidate_replay_v1(
    value: Any,
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    expected = evaluate_gemini_json_capital_contribution_dividend_income_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if type(value) is not dict or not same_typed_json_v1(value, expected):
        raise _error("Family-35 candidate replay drifted")
    return expected
