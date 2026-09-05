"""Family-33 adapter for investment-securities activity disclosures.

The shared multi-table engine remains the accounting authority.  This adapter
adds four narrowly bounded source operations on private page clones:

* content-addressed transcription repair of PDF-visible money tokens;
* recognition of an explicit terminal ``Tổng``/``Cộng`` row as the table's
  source-visible result when the owner and component graph are already exact;
* exact unit corroboration from a same-page, same-label, same-value control to
  one explicit-unit primary-statement presentation; and
* recovery of one unshadowed, source-visible primary income-statement result.

No operation derives a value, guesses a scale, completes a blank, or routes by
bank, file name, year, page number, or value magnitude.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from itertools import product
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
    _multitable_lane_axis,
    _source_money,
    _unit_axis,
    build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    classify_gemini_json_multitable_hierarchical_table_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
    validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
)
from bctc_ai.evaluation.source_observation_lane_math_v1 import (
    observed_source_coefficient_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FAMILY_ID = "INVESTMENT_SECURITIES_ACTIVITY"
ADAPTER_FORMAT_VERSION = "GEMINI_JSON_INVESTMENT_SECURITIES_ACTIVITY_FAMILY_ADAPTER_V1"
SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION = (
    "GEMINI_JSON_INVESTMENT_SECURITIES_ACTIVITY_AUTHENTICATED_SOURCE_REPAIR_ARTIFACT_V1"
)
SOURCE_REPAIR_POLICY = (
    "TRANSCRIBE_ONLY_PDF_VISIBLE_MONEY_TOKENS_NO_EQUATION_BACKSOLVE_"
    "NO_BLANK_TO_ZERO_NO_PROVIDER"
)
PRIMARY_ROOT_QUERY_RECEIPT_FORMAT_VERSION = (
    "GEMINI_JSON_INVESTMENT_SECURITIES_ACTIVITY_PRIMARY_ROOT_QUERY_RECEIPT_V1"
)
DEFAULT_SOURCE_REPAIR_PATH = (
    "data/registered/gemini_json_investment_securities_activity_source_repairs_v1.json"
)
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_FAMILY33_EXACT_PDF_TOKEN_REPAIR_"
    "VISIBLE_TERMINAL_RESULT_PRIMARY_STATEMENT_DIRECT_RESULT_AND_EXACT_"
    "SAME_LABEL_VALUE_PERIOD_UNIT_CORROBORATION_PRIVATE_CLONE_ONLY_NO_"
    "BLANK_ZERO_VALUE_DERIVATION_MAGNITUDE_INFERENCE_OR_BANK_ROUTING_"
    "PROPOSAL_ONLY_" + SHARED_CLAIM_BOUNDARY
)

_PAGE_VERSION = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SECTION_ID = re.compile(r"s[1-9][0-9]*\Z")
_TABLE_ID = re.compile(r"t[1-9][0-9]*\Z")
_ROW_ID = re.compile(r"r[1-9][0-9]*\Z")
_VISIBLE_MONEY = re.compile(
    r"(?:[-_–—−]+|\d+(?:[., ]\d+)*(?:\n[., ]?\d+)*|\(\d+(?:[., ]\d+)*\))\Z"
)
_GENERIC_RESULT_LABELS = {"cong", "tong"}


class GeminiJsonInvestmentSecuritiesActivityFamilyV1Error(ValueError):
    """Family-33 adapter input, source evidence, or replay drifted."""


def _error(message: str) -> GeminiJsonInvestmentSecuritiesActivityFamilyV1Error:
    return GeminiJsonInvestmentSecuritiesActivityFamilyV1Error(message)


def _load_default_source_repair_artifact_v1() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[3] / DEFAULT_SOURCE_REPAIR_PATH
    try:
        return json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("investment-securities source-repair artifact is absent or invalid") from exc


def _compile_source_repair_artifact_v1(value: Any) -> dict[str, Any]:
    artifact_fields = {"family_id", "format_version", "policy", "repairs"}
    if (
        type(value) is not dict
        or set(value) != artifact_fields
        or value.get("family_id") != FAMILY_ID
        or value.get("format_version") != SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION
        or value.get("policy") != SOURCE_REPAIR_POLICY
        or type(value.get("repairs")) is not list
        or not value["repairs"]
    ):
        raise _error("investment-securities source-repair artifact is invalid")
    repair_fields = {
        "base_page_json_sha256",
        "base_table_sha256",
        "cell_repairs",
        "column_repairs",
        "page_image",
        "page_json_version_id",
        "physical_page",
        "reviewed_utc_date",
        "section_id",
        "source_logical_name",
        "source_sha256",
        "source_size_bytes",
        "table_id",
    }
    image_fields = {"height", "media_type", "render_dpi", "sha256", "size_bytes", "width"}
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
    column_fields = {
        "column_ordinal",
        "header_path_exact",
        "original_value_kind",
        "replacement_value_kind",
        "visual_observation",
    }
    repairs = []
    seen_versions: set[str] = set()
    for raw in value["repairs"]:
        if type(raw) is not dict or set(raw) != repair_fields:
            raise _error("investment-securities source-repair fields drifted")
        repair = canonical_clone_v1(raw)
        image = repair.get("page_image")
        if (
            _PAGE_VERSION.fullmatch(repair.get("page_json_version_id", "")) is None
            or repair["page_json_version_id"] in seen_versions
            or _SHA256.fullmatch(repair.get("base_page_json_sha256", "")) is None
            or _SHA256.fullmatch(repair.get("base_table_sha256", "")) is None
            or _SHA256.fullmatch(repair.get("source_sha256", "")) is None
            or type(repair.get("source_logical_name")) is not str
            or not repair["source_logical_name"].strip()
            or type(repair.get("source_size_bytes")) is not int
            or repair["source_size_bytes"] <= 0
            or type(repair.get("physical_page")) is not int
            or repair["physical_page"] <= 0
            or _SECTION_ID.fullmatch(repair.get("section_id", "")) is None
            or _TABLE_ID.fullmatch(repair.get("table_id", "")) is None
            or repair.get("reviewed_utc_date") != "2026-09-04"
            or type(image) is not dict
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
            or type(repair.get("cell_repairs")) is not list
            or type(repair.get("column_repairs")) is not list
            or not (repair["cell_repairs"] or repair["column_repairs"])
        ):
            raise _error("investment-securities source-repair binding is invalid")
        seen_versions.add(repair["page_json_version_id"])
        seen_cells: set[tuple[str, int]] = set()
        for cell in repair["cell_repairs"]:
            key = (
                cell.get("row_id") if type(cell) is dict else None,
                cell.get("column_ordinal") if type(cell) is dict else None,
            )
            if (
                type(cell) is not dict
                or set(cell) != cell_fields
                or _ROW_ID.fullmatch(cell.get("row_id", "")) is None
                or type(cell.get("column_ordinal")) is not int
                or cell["column_ordinal"] <= 0
                or key in seen_cells
                or cell.get("original_value_exact") is not None
                and type(cell.get("original_value_exact")) is not str
                or type(cell.get("replacement_value_exact")) is not str
                or _VISIBLE_MONEY.fullmatch(cell["replacement_value_exact"].strip()) is None
                or type(cell.get("row_label_exact")) is not str
                or not cell["row_label_exact"].strip()
                or type(cell.get("row_hierarchy_path_exact")) is not list
                or type(cell.get("row_kind")) is not str
                or cell.get("visual_observation") != "PDF_RENDER_VISIBLE_MONEY_TOKEN"
            ):
                raise _error("investment-securities source-repair cell is invalid")
            seen_cells.add(key)  # type: ignore[arg-type]
        seen_columns: set[int] = set()
        for column in repair["column_repairs"]:
            if (
                type(column) is not dict
                or set(column) != column_fields
                or type(column.get("column_ordinal")) is not int
                or column["column_ordinal"] <= 0
                or column["column_ordinal"] in seen_columns
                or type(column.get("header_path_exact")) is not list
                or column.get("original_value_kind") != "TEXT"
                or column.get("replacement_value_kind") != "MONEY"
                or column.get("visual_observation")
                != "PDF_RENDER_VISIBLE_MONEY_COLUMN"
            ):
                raise _error("investment-securities source-repair column is invalid")
            seen_columns.add(column["column_ordinal"])
        material = canonical_clone_v1(repair)
        repair["repair_id"] = "gjisafav1:repair:" + canonical_json_sha256_v1(material)
        repairs.append(repair)
    repairs.sort(key=lambda item: item["page_json_version_id"])
    compiled = {
        "family_id": FAMILY_ID,
        "format_version": SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION,
        "policy": SOURCE_REPAIR_POLICY,
        "repairs": repairs,
    }
    compiled["repair_axis_sha256"] = canonical_json_sha256_v1(repairs)
    compiled["overlay_id"] = "gjisafav1:overlay:" + canonical_json_sha256_v1(compiled)
    return compiled


def compile_gemini_json_investment_securities_activity_family_specs_v1(
    topology_spec: Any,
    evaluation_spec: Any,
    schema_binding_spec: Any,
    source_repair_spec: Any | None = None,
) -> dict[str, Any]:
    """Compile Family 33 and its immutable source adapter."""

    compiled = compile_gemini_json_multitable_hierarchical_family_specs_v1(
        topology_spec, evaluation_spec, schema_binding_spec
    )
    if (
        compiled.get("topology", {}).get("family_id") != FAMILY_ID
        or compiled.get("schema", {}).get("family_id") != FAMILY_ID
        or compiled.get("family_root_requirement") != "OPTIONAL"
        or compiled.get("source_total_blank_lane_control_policy")
        != "OBSERVED_LANES_EXACT_REMAINDER_BLANK"
        or compiled.get("source_presentation_rounding_policy")
        != "INDEPENDENT_DISPLAY_UNIT_ROUNDING_INTERVAL_ALL_EQUATIONS"
        or compiled.get("duration_header_path_scope_policy")
        != "DISTINCT_SUFFIX_AFTER_EXACT_COMMON_PREFIX"
        or {
            item.get("canonical_unit")
            for item in compiled.get("unit_bindings", [])
            if item.get("accepted") is True
        }
        != {"MILLION_VND", "VND"}
    ):
        raise _error("investment-securities declarative adapter boundary is invalid")
    raw = (
        _load_default_source_repair_artifact_v1()
        if source_repair_spec is None
        else source_repair_spec
    )
    compiled["investment_securities_activity_adapter_format_version"] = ADAPTER_FORMAT_VERSION
    compiled["investment_securities_activity_source_repair_overlay"] = (
        _compile_source_repair_artifact_v1(raw)
    )
    compiled["investment_securities_activity_source_repair_spec_sha256"] = (
        canonical_json_sha256_v1(raw)
    )
    return compiled


def build_gemini_json_investment_securities_activity_region_query_receipt_v1(
    regions: Any,
) -> dict[str, Any]:
    return build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)


def _region_table(
    pages: Mapping[str, dict[str, Any]], region: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    page = pages.get(region.get("page_json_version_id"))
    try:
        section = page["sections"][int(region["section_id"][1:]) - 1]  # type: ignore[index]
        table = section["tables"][int(region["table_id"][1:]) - 1]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise _error("investment-securities region does not resolve one source table") from exc
    if type(page) is not dict or type(section) is not dict or type(table) is not dict:
        raise _error("investment-securities region source table is invalid")
    return page, section, table


def _apply_source_repairs_v1(
    *,
    pages: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    projected = {key: canonical_clone_v1(page) for key, page in pages.items()}
    region_by_version = {
        region["page_json_version_id"]: region
        for region in regions
        if type(region) is dict and type(region.get("page_json_version_id")) is str
    }
    receipts = []
    overlay = compiled_specs["investment_securities_activity_source_repair_overlay"]
    for repair in overlay["repairs"]:
        version_id = repair["page_json_version_id"]
        region = region_by_version.get(version_id)
        if region is None:
            continue
        if any(
            region.get(key) != repair[key]
            for key in ("physical_page", "section_id", "table_id")
        ) or any(
            region.get(key) != repair[key]
            for key in ("source_logical_name", "source_sha256")
        ):
            raise _error("investment-securities source-repair locator drifted")
        page, _section, table = _region_table(projected, region)
        if (
            canonical_json_sha256_v1(page) != repair["base_page_json_sha256"]
            or canonical_json_sha256_v1(table) != repair["base_table_sha256"]
        ):
            raise _error("investment-securities source-repair base content drifted")
        before_page_sha = canonical_json_sha256_v1(page)
        applied_cells = []
        for cell in repair["cell_repairs"]:
            row_ordinal = int(cell["row_id"][1:])
            column_ordinal = cell["column_ordinal"]
            try:
                row = table["rows"][row_ordinal - 1]
                before = row["values_exact"][column_ordinal - 1]
            except (KeyError, IndexError, TypeError) as exc:
                raise _error("investment-securities source-repair cell locator drifted") from exc
            if (
                row.get("label_exact") != cell["row_label_exact"]
                or row.get("hierarchy_path_exact") != cell["row_hierarchy_path_exact"]
                or row.get("row_kind") != cell["row_kind"]
                or before != cell["original_value_exact"]
            ):
                raise _error("investment-securities source-repair cell source drifted")
            row["values_exact"][column_ordinal - 1] = cell["replacement_value_exact"]
            applied_cells.append(canonical_clone_v1(cell))
        applied_columns = []
        for column_repair in repair["column_repairs"]:
            ordinal = column_repair["column_ordinal"]
            try:
                column = table["columns"][ordinal - 1]
            except (KeyError, IndexError, TypeError) as exc:
                raise _error("investment-securities source-repair column locator drifted") from exc
            if (
                column.get("header_path_exact") != column_repair["header_path_exact"]
                or column.get("value_kind") != column_repair["original_value_kind"]
            ):
                raise _error("investment-securities source-repair column source drifted")
            column["value_kind"] = column_repair["replacement_value_kind"]
            applied_columns.append(canonical_clone_v1(column_repair))
        material = {
            "after_page_json_sha256": canonical_json_sha256_v1(page),
            "after_table_sha256": canonical_json_sha256_v1(table),
            "applied_cell_repairs": applied_cells,
            "applied_column_repairs": applied_columns,
            "before_page_json_sha256": before_page_sha,
            "before_table_sha256": repair["base_table_sha256"],
            "locator": {
                key: region[key]
                for key in ("page_json_version_id", "physical_page", "section_id", "table_id")
            },
            "page_image": canonical_clone_v1(repair["page_image"]),
            "repair_id": repair["repair_id"],
            "rule": SOURCE_REPAIR_POLICY,
        }
        receipts.append(
            {
                **material,
                "receipt_id": "gjisafav1:source-repair:"
                + canonical_json_sha256_v1(material),
            }
        )
    return projected, receipts


def _root_alias(value: Any, *, compiled_specs: Mapping[str, Any]) -> str | None:
    folded = _without_leading_ordinal(_normalized(value))
    aliases = {
        _normalized(alias) for alias in compiled_specs["topology"]["parent"]["aliases"]
    }
    return folded if folded in aliases else None


def _promote_visible_terminal_results_v1(
    *,
    pages: dict[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    receipts = []
    replacement_label = compiled_specs["topology"]["parent"]["aliases"][0]
    for region in regions:
        page, section, table = _region_table(pages, region)
        classification = classify_gemini_json_multitable_hierarchical_table_v1(
            page, section, table, compiled_specs=compiled_specs
        )
        if (
            classification.get("family_root_row_ordinals")
            or classification.get("owner_visible") is not True
        ):
            continue
        declared_roles = {
            item.get("role")
            for item in classification.get("role_hits", [])
            if item.get("role") in set(compiled_specs.get("root_component_roles", []))
        }
        rows = table.get("rows")
        money_ordinals = classification.get("money_column_ordinals")
        if not declared_roles or type(rows) is not list or type(money_ordinals) is not list:
            continue
        visible_rows = [
            ordinal
            for ordinal, row in enumerate(rows, start=1)
            if type(row) is dict
            and type(row.get("values_exact")) is list
            and any(
                column <= len(row["values_exact"])
                and row["values_exact"][column - 1] is not None
                for column in money_ordinals
            )
        ]
        matches = [
            (
                ordinal,
                row,
                (
                    "GENERIC_TONG_OR_CONG"
                    if _without_leading_ordinal(_normalized(row.get("label_exact")))
                    in _GENERIC_RESULT_LABELS
                    else "UNLABELED_TOTAL"
                ),
            )
            for ordinal, row in enumerate(rows, start=1)
            if type(row) is dict
            and row.get("row_kind") in {"SUBTOTAL", "TOTAL"}
            and (
                _without_leading_ordinal(_normalized(row.get("label_exact")))
                in _GENERIC_RESULT_LABELS
                or (
                    row.get("row_kind") == "TOTAL"
                    and not _normalized(row.get("label_exact"))
                )
            )
            and ordinal == max(visible_rows, default=-1)
        ]
        if len(matches) != 1:
            continue
        ordinal, row, source_result_surface_kind = matches[0]
        before = {
            "hierarchy_path_exact": canonical_clone_v1(row.get("hierarchy_path_exact")),
            "label_exact": row.get("label_exact"),
            "row_kind": row.get("row_kind"),
        }
        hierarchy = row.get("hierarchy_path_exact")
        if type(hierarchy) is not list or not hierarchy:
            continue
        row["label_exact"] = replacement_label
        row["hierarchy_path_exact"] = [*hierarchy[:-1], replacement_label]
        material = {
            "after": {
                "hierarchy_path_exact": canonical_clone_v1(row["hierarchy_path_exact"]),
                "label_exact": row["label_exact"],
                "row_kind": row["row_kind"],
            },
            "before": before,
            "declared_root_component_roles": sorted(declared_roles),
            "locator": {
                key: region[key]
                for key in ("page_json_version_id", "physical_page", "section_id", "table_id")
            },
            "row_ordinal": ordinal,
            "source_result_surface_kind": source_result_surface_kind,
            "rule": (
                "UNIQUE_LAST_SOURCE_VISIBLE_TOTAL_OR_SUBTOTAL_GENERIC_OR_UNLABELED_"
                "WITHIN_EXACT_SELECTED_OWNER_AND_DECLARED_COMPONENT_GRAPH"
            ),
        }
        receipts.append(
            {
                **material,
                "receipt_id": "gjisafav1:terminal-result:"
                + canonical_json_sha256_v1(material),
            }
        )
    return receipts


def _money_ordinals(table: Mapping[str, Any]) -> list[int]:
    columns = table.get("columns")
    return [
        ordinal
        for ordinal, column in enumerate(columns if type(columns) is list else [], start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]


def _observed_vector(
    row: Mapping[str, Any], money_ordinals: Sequence[int]
) -> list[int] | None:
    values = row.get("values_exact")
    if type(values) is not list or any(ordinal > len(values) for ordinal in money_ordinals):
        return None
    try:
        coefficients = [
            _source_money(values[ordinal - 1])["coefficient"]
            for ordinal in money_ordinals
        ]
    except ValueError:
        return None
    if not coefficients or any(type(value) is not int for value in coefficients):
        return None
    return coefficients  # type: ignore[return-value]


def _unit_control_label_key_v1(value: Any) -> str:
    """Canonicalize an exact accounting topic, never numeric content."""

    folded = _without_leading_ordinal(_normalized(value))
    folded = re.sub(r"[^a-z0-9]+", " ", folded).strip()
    folded = re.sub(r"\bck\b", "chung khoan", folded)
    folded = re.sub(
        r"^(?:"
        r"lai lo thuan|lo lai thuan|lai thuan|lo thuan|"
        r"trich hoan nhap du phong rui ro|hoan nhap du phong rui ro|"
        r"chi phi du phong giam gia|chi phi du phong rui ro|"
        r"du phong giam gia|du phong rui ro|"
        r"thu nhap|chi phi ve|chi phi"
        r")(?: |$)",
        "",
        folded,
    )
    for phrase in (
        "tu hoat dong kinh doanh",
        "tu hoat dong",
        "hoat dong kinh doanh",
        "mua ban",
    ):
        folded = re.sub(rf"(?:^| )({phrase})(?: |$)", " ", folded)
        folded = " ".join(folded.split())
    folded = re.sub(r"^tu(?: |$)", "", folded).strip()
    return folded


def _page_label_vector_controls_v1(
    *,
    page_json_version_id: str,
    page: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
    require_explicit_unit: bool,
    required_statement_type: str | None = None,
) -> list[dict[str, Any]]:
    controls = []
    for section_ordinal, section in enumerate(page.get("sections") or [], start=1):
        if type(section) is not dict:
            continue
        if (
            required_statement_type is not None
            and section.get("statement_type") != required_statement_type
        ):
            continue
        for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
            if type(table) is not dict:
                continue
            lane_axis = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
            ordinals = lane_axis.get("money_column_ordinals")
            unit_axis = _unit_axis(table, compiled_specs=compiled_specs)
            if (
                lane_axis.get("complete") is not True
                or type(ordinals) is not list
                or len(ordinals) != 2
                or require_explicit_unit and unit_axis.get("complete") is not True
            ):
                continue
            lane_variants = [("CANONICAL_SELECTED_DURATION_PAIR", lane_axis, ordinals)]
            excluded = lane_axis.get("excluded_parallel_duration_money_column_ordinals")
            columns = table.get("columns")
            if (
                type(excluded) is list
                and len(excluded) == 2
                and excluded != ordinals
                and type(columns) is list
                and all(
                    type(column) is int
                    and 1 <= column <= len(columns)
                    and type(columns[column - 1]) is dict
                    and columns[column - 1].get("value_kind") == "MONEY"
                    for column in excluded
                )
            ):
                alternate_lane_axis = canonical_clone_v1(lane_axis)
                lane_variants.append(
                    (
                        "SHARED_AXIS_EXACT_EXCLUDED_PARALLEL_DURATION_PAIR",
                        alternate_lane_axis,
                        excluded,
                    )
                )
            for lane_selection_kind, control_lane_axis, control_ordinals in lane_variants:
                component_topic_counts: dict[str, int] = {}
                for component_row in table.get("rows") or []:
                    if (
                        type(component_row) is not dict
                        or component_row.get("row_kind") in {"SUBTOTAL", "TOTAL"}
                        or _observed_vector(component_row, control_ordinals) is None
                    ):
                        continue
                    topic = _unit_control_label_key_v1(component_row.get("label_exact"))
                    if len(topic.split()) >= 2:
                        component_topic_counts[topic] = component_topic_counts.get(topic, 0) + 1
                repeated_topics = sorted(
                    topic for topic, count in component_topic_counts.items() if count >= 2
                )
                for row_ordinal, row in enumerate(table.get("rows") or [], start=1):
                    if type(row) is not dict:
                        continue
                    source_label = row.get("label_exact")
                    label = _without_leading_ordinal(_normalized(source_label))
                    if row.get("row_kind") in {"SUBTOTAL", "TOTAL"} and (
                        not label or label in _GENERIC_RESULT_LABELS
                    ):
                        source_label = table.get("title_exact") or section.get("title_exact")
                        label = _without_leading_ordinal(_normalized(source_label))
                    label_key = _unit_control_label_key_v1(source_label)
                    if (
                        row.get("row_kind") in {"SUBTOTAL", "TOTAL"}
                        and not label_key
                        and len(repeated_topics) == 1
                    ):
                        label = repeated_topics[0]
                        label_key = repeated_topics[0]
                    vector = _observed_vector(row, control_ordinals)
                    if (
                        not label
                        or not label_key
                        or label in _GENERIC_RESULT_LABELS
                        or len(label.split()) < 3
                        or vector is None
                        or not any(vector)
                    ):
                        continue
                    controls.append(
                        {
                            "canonical_unit": unit_axis.get("canonical_unit"),
                            "label_key": label_key,
                            "label_normalized": label,
                            "lane_axis": canonical_clone_v1(control_lane_axis),
                            "lane_selection_kind": lane_selection_kind,
                            "locator": {
                                "page_json_version_id": page_json_version_id,
                                "section_id": f"s{section_ordinal}",
                                "table_id": f"t{table_ordinal}",
                            },
                            "money_column_ordinals": list(control_ordinals),
                            "row_ordinal": row_ordinal,
                            "source_label_exact": source_label,
                            "unit_axis": canonical_clone_v1(unit_axis),
                            "vector": vector,
                        }
                    )
    return controls


def _bind_same_page_exact_primary_units_v1(
    *,
    pages: dict[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    explicit_primary_controls = [
        control
        for version_id, page in pages.items()
        if page.get("status") == "PRIMARY_FINANCIAL_STATEMENT"
        for control in _page_label_vector_controls_v1(
            page_json_version_id=version_id,
            page=page,
            compiled_specs=compiled_specs,
            require_explicit_unit=True,
            required_statement_type="INCOME_STATEMENT",
        )
    ]
    income_statement_controls = [
        control
        for version_id, page in pages.items()
        if page.get("status") == "PRIMARY_FINANCIAL_STATEMENT"
        for control in _page_label_vector_controls_v1(
            page_json_version_id=version_id,
            page=page,
            compiled_specs=compiled_specs,
            require_explicit_unit=False,
            required_statement_type="INCOME_STATEMENT",
        )
    ]
    primary_unit_evidence = []
    for version_id, page in pages.items():
        if page.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
            continue
        for section_ordinal, section in enumerate(page.get("sections") or [], start=1):
            if type(section) is not dict or section.get("content_kind") != "PRIMARY_STATEMENT":
                continue
            for table_ordinal, primary_table in enumerate(
                section.get("tables") or [], start=1
            ):
                if type(primary_table) is not dict:
                    continue
                primary_unit_axis = _unit_axis(
                    primary_table, compiled_specs=compiled_specs
                )
                if primary_unit_axis.get("complete") is True:
                    primary_unit_evidence.append(
                        {
                            "locator": {
                                "page_json_version_id": version_id,
                                "section_id": f"s{section_ordinal}",
                                "table_id": f"t{table_ordinal}",
                            },
                            "unit_axis": canonical_clone_v1(primary_unit_axis),
                        }
                    )
    document_primary_units = {
        item["unit_axis"]["canonical_unit"] for item in primary_unit_evidence
    }
    receipts = []
    for region in regions:
        _page, _section, table = _region_table(pages, region)
        local_unit = _unit_axis(table, compiled_specs=compiled_specs)
        if (
            local_unit.get("complete") is True
            or local_unit.get("evidence")
            or local_unit.get("undeclared_evidence")
        ):
            continue
        target_page = pages[region["page_json_version_id"]]
        target_controls = _page_label_vector_controls_v1(
            page_json_version_id=region["page_json_version_id"],
            page=target_page,
            compiled_specs=compiled_specs,
            require_explicit_unit=False,
        )
        matches = [
            {
                "canonical_unit": primary["canonical_unit"],
                "primary_control": primary,
                "target_control": target,
                "unit_source_kind": "MATCHED_EXPLICIT_UNIT_PRIMARY_INCOME_STATEMENT_CONTROL",
            }
            for target in target_controls
            for primary in explicit_primary_controls
            if primary["label_key"] == target["label_key"]
            and primary["vector"] == target["vector"]
        ]
        if not matches and len(document_primary_units) == 1:
            inherited_unit = next(iter(document_primary_units))
            matches = [
                {
                    "canonical_unit": inherited_unit,
                    "primary_control": primary,
                    "target_control": target,
                    "unit_source_kind": (
                        "MATCHED_UNITLESS_PRIMARY_INCOME_STATEMENT_CONTROL_WITH_"
                        "UNIQUE_EXPLICIT_PRIMARY_STATEMENT_DOCUMENT_UNIT"
                    ),
                }
                for target in target_controls
                for primary in income_statement_controls
                if primary["label_key"] == target["label_key"]
                and primary["vector"] == target["vector"]
            ]
        units = {item["canonical_unit"] for item in matches}
        if len(units) != 1:
            continue
        canonical_unit = next(iter(units))
        source_tokens = sorted(
            {
                evidence["source_exact"]
                for item in matches
                for evidence in item["primary_control"]["unit_axis"].get("evidence", [])
                if type(evidence.get("source_exact")) is str
                and evidence["source_exact"].strip()
            }
        )
        if not source_tokens:
            source_tokens = sorted(
                {
                    evidence["source_exact"]
                    for item in primary_unit_evidence
                    if item["unit_axis"]["canonical_unit"] == canonical_unit
                    for evidence in item["unit_axis"].get("evidence", [])
                    if type(evidence.get("source_exact")) is str
                    and evidence["source_exact"].strip()
                }
            )
        if not source_tokens:
            continue
        before = table.get("unit_exact")
        table["unit_exact"] = source_tokens[0]
        if _unit_axis(table, compiled_specs=compiled_specs).get("canonical_unit") != canonical_unit:
            raise _error("investment-securities corroborated unit token does not recompile")
        material = {
            "after_table_unit_exact": table["unit_exact"],
            "before_table_unit_exact": before,
            "canonical_unit": canonical_unit,
            "exact_same_label_value_controls": canonical_clone_v1(matches),
            "primary_statement_document_unit_evidence": canonical_clone_v1(
                primary_unit_evidence
            ),
            "rule": (
                "ONE_CANONICAL_UNIT_MATCHED_BY_EXACT_ACCOUNTING_TOPIC_AND_DURATION_"
                "VECTOR_TO_PRIMARY_INCOME_STATEMENT_WITH_EXPLICIT_CONTROL_UNIT_OR_"
                "UNIQUE_EXPLICIT_PRIMARY_STATEMENT_DOCUMENT_UNIT"
            ),
            "target_locator": {
                key: region[key]
                for key in ("page_json_version_id", "physical_page", "section_id", "table_id")
            },
        }
        receipts.append(
            {
                **material,
                "receipt_id": "gjisafav1:unit:" + canonical_json_sha256_v1(material),
            }
        )
    return receipts


def _table_from_inventory(
    item: Mapping[str, Any], pages: Mapping[str, dict[str, Any]]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None:
    try:
        region = {
            "page_json_version_id": item["page_json_version_id"],
            "section_id": item["section_id"],
            "table_id": item["table_id"],
        }
        return _region_table(pages, region)
    except (KeyError, GeminiJsonInvestmentSecuritiesActivityFamilyV1Error):
        return None


def _direct_note_candidate_axis(
    inventory: Sequence[Mapping[str, Any]],
    pages: Mapping[str, dict[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    activity_roles = {
        "EXPENSE_INVESTMENT_SECURITIES",
        "INCOME_INVESTMENT_SECURITIES",
    }
    result = []
    for item in inventory:
        classification = item.get("classification") if type(item) is dict else None
        resolved = _table_from_inventory(item, pages) if type(classification) is dict else None
        if resolved is None:
            continue
        page, section, table = resolved
        lane_axis = _multitable_lane_axis(
            section, table, compiled_specs=compiled_specs
        )
        unit_axis = _unit_axis(table, compiled_specs=compiled_specs)
        roles = sorted(
            {
                hit.get("role")
                for hit in classification.get("role_hits", [])
                if type(hit) is dict and type(hit.get("role")) is str
            }
        )
        if (
            page.get("status") != "PRIMARY_FINANCIAL_STATEMENT"
            and section.get("content_kind") == "FINANCIAL_NOTE"
            and classification.get("typed_control_disposition") is None
            and lane_axis.get("complete") is True
            and len(lane_axis.get("money_column_ordinals", [])) == 2
            and unit_axis.get("complete") is True
            and (
                bool(activity_roles.intersection(roles))
                or classification.get("family_root_row_ordinals")
            )
        ):
            result.append(
                {
                    "classification_id": classification.get("classification_id"),
                    "locator": {
                        key: item[key]
                        for key in ("page_json_version_id", "physical_page", "section_id", "table_id")
                    },
                    "roles": roles,
                }
            )
    return result


def _primary_statement_projection_v1(
    *,
    region: Mapping[str, Any],
    pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]] | None:
    page = pages.get(region.get("page_json_version_id"))
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
    unit_axis = _unit_axis(table, compiled_specs=compiled_specs)
    source_money_ordinals = _money_ordinals(table)
    lane_axis = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
    money_ordinals = lane_axis.get("money_column_ordinals")
    rows = table.get("rows")
    if (
        unit_axis.get("complete") is not True
        or lane_axis.get("complete") is not True
        or type(money_ordinals) is not list
        or len(money_ordinals) != 2
        or not set(money_ordinals).issubset(source_money_ordinals)
        or type(rows) is not list
    ):
        return None
    matches = []
    for ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict or _root_alias(row.get("label_exact"), compiled_specs=compiled_specs) is None:
            continue
        hierarchy = row.get("hierarchy_path_exact")
        vector = _observed_vector(row, money_ordinals)
        if (
            row.get("row_kind") not in {"ITEM", "GROUP", "SUBTOTAL", "TOTAL"}
            or type(hierarchy) is not list
            or not hierarchy
            or _root_alias(hierarchy[-1], compiled_specs=compiled_specs) is None
            or vector is None
        ):
            return None
        matches.append((ordinal, row, vector))
    if len(matches) != 1:
        return None
    ordinal, source_row, vector = matches[0]
    locator = {
        key: region[key]
        for key in ("page_json_version_id", "physical_page", "section_id", "table_id")
    }
    material = {
        "canonical_unit": unit_axis["canonical_unit"],
        "document_id": region["document_id"],
        "document_ordinal": region["document_ordinal"],
        "format_version": PRIMARY_ROOT_QUERY_RECEIPT_FORMAT_VERSION,
        "lane_axis": canonical_clone_v1(lane_axis),
        "locator": locator,
        "money_column_ordinals": list(money_ordinals),
        "projection": {
            "after_page_status": page["status"],
            "after_row_kind": source_row["row_kind"],
            "after_section_content_kind": section["content_kind"],
            "after_section_statement_type": section["statement_type"],
            "after_table_continuation": table.get("continuation"),
            "after_table_row_count": 1,
            "before_page_status": page["status"],
            "before_row_kind": source_row["row_kind"],
            "before_section_content_kind": section["content_kind"],
            "before_section_statement_type": section["statement_type"],
            "before_table_continuation": table.get("continuation"),
            "before_table_row_count": len(rows),
        },
        "root_row": {
            "hierarchy_path_exact": canonical_clone_v1(source_row["hierarchy_path_exact"]),
            "label_exact": source_row["label_exact"],
            "row_kind": source_row["row_kind"],
            "row_ordinal": ordinal,
            "values_exact": canonical_clone_v1(source_row["values_exact"]),
        },
        "rule": (
            "ONE_EXACT_DECLARED_SOURCE_VISIBLE_FAMILY_ROOT_IN_PRIMARY_INCOME_"
            "STATEMENT_ROOT_ROW_ONLY_PRIVATE_QUERY_PROJECTION_PREFERRED_EXPLICIT_"
            "MILLION_VND_PRESENTATION_NO_VALUE_MUTATION_BLANK_COMPLETION_OR_SCALE_"
            "INFERENCE"
        ),
        "source_logical_name": region["source_logical_name"],
        "source_money_column_ordinals": source_money_ordinals,
        "source_sha256": region["source_sha256"],
        "unit_axis": canonical_clone_v1(unit_axis),
        "vector": vector,
    }
    receipt = {
        **material,
        "primary_root_query_receipt_id": "gjisafav1:primary-root:"
        + canonical_json_sha256_v1(material),
    }
    projected = {key: canonical_clone_v1(value) for key, value in pages.items()}
    target_page = projected[region["page_json_version_id"]]
    target_section = target_page["sections"][int(region["section_id"][1:]) - 1]
    target_table = target_section["tables"][int(region["table_id"][1:]) - 1]
    target_row = canonical_clone_v1(target_table["rows"][ordinal - 1])
    target_table["rows"] = [target_row]
    return projected, receipt


def _primary_query_recovery_v1(
    *,
    cluster: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]] | None:
    if cluster.get("status") != NOT_OBSERVED or cluster.get("reasons") != []:
        return None
    inventory = cluster.get("declared_money_table_inventory")
    if type(inventory) is not list:
        return None
    direct_note_candidates = _direct_note_candidate_axis(
        inventory, pages, compiled_specs=compiled_specs
    )
    note_regions = []
    for note in direct_note_candidates:
        locator = note["locator"]
        selected = [
            page
            for page in selected_page_axis
            if page.get("document_ordinal") == cluster.get("document_ordinal")
            and page.get("page_json_version_id") == locator.get("page_json_version_id")
            and page.get("physical_page") == locator.get("physical_page")
        ]
        if len(selected) != 1:
            return None
        note_regions.append(
            {
                "component_roles": canonical_clone_v1(note["roles"]),
                "document_id": cluster["document_id"],
                "document_ordinal": cluster["document_ordinal"],
                "fragment_ordinal": 0,
                "page_json_version_id": locator["page_json_version_id"],
                "physical_page": locator["physical_page"],
                "section_id": locator["section_id"],
                "selected_page_ordinal": selected[0]["selected_page_ordinal"],
                "source_logical_name": cluster["source_logical_name"],
                "source_sha256": cluster["source_sha256"],
                "table_id": locator["table_id"],
            }
        )
    candidates = []
    for item in inventory:
        classification = item.get("classification") if type(item) is dict else None
        if (
            type(classification) is not dict
            or classification.get("typed_control_disposition")
            != "PRIMARY_FINANCIAL_STATEMENT_SUMMARY"
            or len(classification.get("family_root_row_ordinals", [])) != 1
        ):
            continue
        selected = [
            page
            for page in selected_page_axis
            if page.get("document_ordinal") == cluster.get("document_ordinal")
            and page.get("page_json_version_id") == item.get("page_json_version_id")
            and page.get("physical_page") == item.get("physical_page")
        ]
        if len(selected) != 1:
            continue
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
        projected_pages, _source_repair_receipts = _apply_source_repairs_v1(
            pages=pages,
            regions=[region],
            compiled_specs=compiled_specs,
        )
        _bind_same_page_exact_primary_units_v1(
            pages=projected_pages,
            regions=[region],
            compiled_specs=compiled_specs,
        )
        projected = _primary_statement_projection_v1(
            region=region,
            pages=projected_pages,
            compiled_specs=compiled_specs,
        )
        if projected is None:
            continue
        _projected_pages, receipt = projected
        if (
            classification.get("family_root_row_ordinals")
            != [receipt["root_row"]["row_ordinal"]]
            or classification.get("ambiguous_rows") != []
        ):
            continue
        combined_regions = [region, *canonical_clone_v1(note_regions)]
        combined_regions.sort(
            key=lambda item: (
                item["selected_page_ordinal"],
                int(item["section_id"][1:]),
                int(item["table_id"][1:]),
            )
        )
        for fragment_ordinal, combined_region in enumerate(combined_regions, start=1):
            combined_region["fragment_ordinal"] = fragment_ordinal
        receipt_material = {
            key: canonical_clone_v1(item)
            for key, item in receipt.items()
            if key != "primary_root_query_receipt_id"
        }
        receipt_material["direct_note_region_axis"] = [
            {
                key: canonical_clone_v1(note_region[key])
                for key in (
                    "component_roles",
                    "page_json_version_id",
                    "physical_page",
                    "section_id",
                    "selected_page_ordinal",
                    "table_id",
                )
            }
            for note_region in combined_regions
            if note_region["page_json_version_id"] != region["page_json_version_id"]
            or note_region["section_id"] != region["section_id"]
            or note_region["table_id"] != region["table_id"]
        ]
        receipt = {
            **receipt_material,
            "primary_root_query_receipt_id": "gjisafav1:primary-root:"
            + canonical_json_sha256_v1(receipt_material),
        }
        candidates.append((combined_regions, receipt))
    preferred = [item for item in candidates if item[1]["canonical_unit"] == "MILLION_VND"]
    selected_candidates = preferred if preferred else candidates
    return selected_candidates[0] if len(selected_candidates) == 1 else None


def adapt_gemini_json_investment_securities_activity_indexed_query_evidence_v1(
    value: Any,
    *,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    evidence = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        value, compiled_specs=compiled_specs
    )
    clusters = []
    receipts = []
    for disposition in evidence["candidate_dispositions"]:
        cluster = canonical_clone_v1(disposition["cluster"])
        pages = page_json_by_document.get(cluster["document_ordinal"])
        recovered = (
            _primary_query_recovery_v1(
                cluster=cluster,
                selected_page_axis=evidence["selected_page_axis"],
                pages=pages,
                compiled_specs=compiled_specs,
            )
            if type(pages) is dict
            else None
        )
        if recovered is not None:
            regions, receipt = recovered
            selected_region_keys = {
                (
                    region["page_json_version_id"],
                    region["section_id"],
                    region["table_id"],
                )
                for region in regions
            }
            for item in cluster["declared_money_table_inventory"]:
                if (
                    item.get("page_json_version_id"),
                    item.get("section_id"),
                    item.get("table_id"),
                ) in selected_region_keys:
                    item["disposition"] = (
                        "SELECTED_PRIMARY_STATEMENT_EXACT_FAMILY_ROOT_AFTER_FAMILY33_RECEIPT"
                        if item.get("page_json_version_id")
                        == receipt["locator"]["page_json_version_id"]
                        and item.get("section_id") == receipt["locator"]["section_id"]
                        and item.get("table_id") == receipt["locator"]["table_id"]
                        else "SELECTED_DIRECT_FAMILY_NOTE_AFTER_FAMILY33_PRIMARY_ROOT_RECEIPT"
                    )
            cluster["component_regions"] = regions
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


def _restore_projected_source_refs_v1(
    candidate: dict[str, Any], receipts: Sequence[Mapping[str, Any]]
) -> None:
    for receipt in receipts:
        before = receipt.get("before") or receipt.get("root_row")
        locator = receipt["locator"]
        row_ordinal = receipt.get("row_ordinal", before.get("row_ordinal"))
        for mapping in candidate.get("mappings", []):
            changed = False
            for source_ref in mapping.get("source_refs", []):
                ref_locator = source_ref.get("locator") if type(source_ref) is dict else None
                if (
                    type(ref_locator) is dict
                    and source_ref.get("row_ordinal") == row_ordinal
                    and all(
                        ref_locator.get(key) == locator[key]
                        for key in ("page_json_version_id", "physical_page", "section_id", "table_id")
                    )
                ):
                    source_ref["label_exact"] = before["label_exact"]
                    source_ref["hierarchy_path_exact"] = canonical_clone_v1(
                        before["hierarchy_path_exact"]
                    )
                    source_ref["row_kind"] = before["row_kind"]
                    source_ref["row_id"] = f"r{row_ordinal}"
                    changed = True
            if changed:
                material = {key: mapping[key] for key in mapping if key != "item_mapping_id"}
                mapping["item_mapping_id"] = "gjmthfmv1:item:" + canonical_json_sha256_v1(
                    material
                )


def _visible_result_row_axis_v1(
    *,
    pages: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    result = []
    for region in regions:
        page, section, table = _region_table(pages, region)
        classification = classify_gemini_json_multitable_hierarchical_table_v1(
            page, section, table, compiled_specs=compiled_specs
        )
        rows = table.get("rows")
        money_ordinals = classification.get("money_column_ordinals")
        for ordinal in classification.get("family_root_row_ordinals", []):
            if (
                type(rows) is not list
                or not (1 <= ordinal <= len(rows))
                or type(money_ordinals) is not list
                or type(rows[ordinal - 1].get("values_exact")) is not list
                or not any(
                    column <= len(rows[ordinal - 1]["values_exact"])
                    and rows[ordinal - 1]["values_exact"][column - 1] is not None
                    for column in money_ordinals
                )
            ):
                continue
            result.append(
                {
                    "locator": {
                        key: region[key]
                        for key in ("page_json_version_id", "physical_page", "section_id", "table_id")
                    },
                    "row_ordinal": ordinal,
                }
            )
    return result


def _bind_source_visible_family_result_v1(
    candidate: dict[str, Any],
    *,
    pages: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    visible_roots: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> None:
    """Map one printed family result directly, with component equations as vetoes.

    The shared Family-33 configuration is internally optional so the adapter
    can validate source-visible results whose unsigned expense presentation
    does not fit the shared additive path.  The public adapter still requires
    one exact source-visible family result.  Some
    source presentations also print a result row whose expense figures are
    unsigned magnitudes, so the shared additive-total path correctly leaves
    that result unmapped.  Here the printed result remains the sole numeric
    authority.  A fully observed declared-component lane is only a veto: at
    least one source-consistent +/- orientation must equal the printed result.
    Blank lanes never participate and are retained as typed null cells.
    """

    if candidate.get("status") != READY or not visible_roots:
        return
    root_mappings = [
        mapping
        for mapping in candidate.get("mappings", [])
        if mapping.get("role") == "FAMILY_ROOT_TOTAL"
    ]
    if len(root_mappings) > 1:
        candidate["status"] = UNRESOLVED
        candidate["reasons"] = ["SOURCE_VISIBLE_FAMILY_RESULT_NOT_UNIQUE"]
        candidate["mappings"] = []
        return
    if len(visible_roots) != 1:
        candidate["status"] = UNRESOLVED
        candidate["reasons"] = ["SOURCE_VISIBLE_FAMILY_RESULT_NOT_UNIQUE"]
        candidate["mappings"] = []
        return
    visible = visible_roots[0]
    locator = visible["locator"]
    matches = [
        region
        for region in regions
        if all(
            region.get(key) == locator[key]
            for key in ("page_json_version_id", "physical_page", "section_id", "table_id")
        )
    ]
    if len(matches) != 1:
        raise _error("investment-securities visible result locator drifted")
    region = matches[0]
    _page, section, table = _region_table(pages, region)
    rows = table.get("rows")
    ordinal = visible["row_ordinal"]
    lane_axis = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
    unit_axis = _unit_axis(table, compiled_specs=compiled_specs)
    money_ordinals = lane_axis.get("money_column_ordinals")
    if (
        lane_axis.get("complete") is not True
        or unit_axis.get("complete") is not True
        or type(rows) is not list
        or not (1 <= ordinal <= len(rows))
        or type(money_ordinals) is not list
        or len(money_ordinals) != 2
    ):
        raise _error("investment-securities visible result axes drifted after evaluation")
    row = rows[ordinal - 1]
    values = row.get("values_exact") if type(row) is dict else None
    if type(values) is not list or any(column > len(values) for column in money_ordinals):
        raise _error("investment-securities visible result row drifted after evaluation")
    cells = [_source_money(values[column - 1]) for column in money_ordinals]
    if not any(observed_source_coefficient_v1(cell) is not None for cell in cells):
        return

    component_by_role = {
        mapping["role"]: mapping
        for mapping in candidate["mappings"]
        if mapping.get("role") in compiled_specs["root_component_roles"]
    }
    component_roles = [
        role for role in compiled_specs["root_component_roles"] if role in component_by_role
    ]
    multiplier_candidates: list[list[int]] = []
    multiplier_candidates_by_lane: list[dict[str, Any]] = []
    exact_lane_ordinals = []
    if component_roles:
        root_coefficients = [observed_source_coefficient_v1(cell) for cell in cells]
        component_coefficients = [
            [observed_source_coefficient_v1(cell) for cell in component_by_role[role]["values"]]
            for role in component_roles
        ]
        exact_lane_ordinals = [
            lane
            for lane, root_coefficient in enumerate(root_coefficients)
            if root_coefficient is not None
            and all(coefficients[lane] is not None for coefficients in component_coefficients)
        ]
        if exact_lane_ordinals:
            magnitude_power10 = next(
                (
                    binding["magnitude_power10"]
                    for binding in compiled_specs["unit_bindings"]
                    if binding["canonical_unit"] == unit_axis["canonical_unit"]
                    and binding["accepted"] is True
                ),
                None,
            )
            rounding_allowed = bool(
                compiled_specs["source_presentation_rounding_policy"]
                == "INDEPENDENT_DISPLAY_UNIT_ROUNDING_INTERVAL_ALL_EQUATIONS"
                and type(magnitude_power10) is int
                and magnitude_power10 >= 3
                and unit_axis["canonical_unit"] != "VND"
            )
            all_multiplier_candidates = [
                list(multipliers)
                for multipliers in product((-1, 1), repeat=len(component_roles))
                if (
                    "INCOME_INVESTMENT_SECURITIES" not in component_roles
                    or multipliers[component_roles.index("INCOME_INVESTMENT_SECURITIES")] == 1
                )
            ]
            multiplier_candidates_by_lane = [
                {
                    "lane_ordinal": lane,
                    "matching_multiplier_candidates": [
                        multipliers
                        for multipliers in all_multiplier_candidates
                        if abs(
                            sum(
                                multiplier * component_coefficients[index][lane]  # type: ignore[operator]
                                for index, multiplier in enumerate(multipliers)
                            )
                            - root_coefficients[lane]  # type: ignore[operator]
                        )
                        <= (1 if rounding_allowed else 0)
                    ],
                }
                for lane in exact_lane_ordinals
            ]
            if any(
                not item["matching_multiplier_candidates"]
                for item in multiplier_candidates_by_lane
            ):
                candidate["status"] = UNRESOLVED
                candidate["reasons"] = ["SOURCE_VISIBLE_FAMILY_RESULT_COMPONENT_VETO_MISMATCH"]
                candidate["mappings"] = []
                return
            multiplier_candidates = [
                multipliers
                for multipliers in all_multiplier_candidates
                if all(
                    abs(
                        sum(
                            multiplier * component_coefficients[index][lane]  # type: ignore[operator]
                        for index, multiplier in enumerate(multipliers)
                        )
                        - root_coefficients[lane]  # type: ignore[operator]
                    )
                    <= (1 if rounding_allowed else 0)
                    for lane in exact_lane_ordinals
                )
            ]

    source_ref = {
        "hierarchy_path_exact": canonical_clone_v1(row.get("hierarchy_path_exact")),
        "label_exact": row.get("label_exact"),
        "locator": canonical_clone_v1(region),
        "money_column_ordinals": list(money_ordinals),
        "row_id": f"r{ordinal}",
        "row_kind": row.get("row_kind"),
        "row_ordinal": ordinal,
    }
    mapping_material = {
        "report_norm_id": compiled_specs["schema"]["family_root_report_norm_id"],
        "role": "FAMILY_ROOT_TOTAL",
        "row_id": f"r{ordinal}",
        "source_refs": [source_ref],
        "state": "SOURCE_VISIBLE_EXACT_FAMILY_RESULT_ROW_DIRECT",
        "unit": unit_axis["canonical_unit"],
        "values": cells,
    }
    if root_mappings:
        mapped_root = root_mappings[0]
        if (
            mapped_root.get("unit") != unit_axis["canonical_unit"]
            or [
                observed_source_coefficient_v1(cell)
                for cell in mapped_root.get("values", [])
            ]
            != [observed_source_coefficient_v1(cell) for cell in cells]
        ):
            raise _error("investment-securities visible result mapping drifted")
    else:
        candidate["mappings"].append(
            {
                **mapping_material,
                "item_mapping_id": "gjmthfmv1:item:"
                + canonical_json_sha256_v1(mapping_material),
            }
        )
    receipt_material = {
        "component_roles": component_roles,
        "exact_observed_lane_ordinals": exact_lane_ordinals,
        "matching_multiplier_candidates": multiplier_candidates,
        "matching_multiplier_candidates_by_lane": multiplier_candidates_by_lane,
        "source_presentation_rounding_policy": compiled_specs[
            "source_presentation_rounding_policy"
        ],
        "result_source_ref": source_ref,
        "rule": (
            "SOURCE_VISIBLE_RESULT_MAPS_OR_REVALIDATES_DIRECTLY_COMPONENT_SIGN_ORIENTATION_"
            "IS_AN_INDEPENDENT_VETO_PER_FULLY_OBSERVED_LANE_BLANK_LANES_EXCLUDED"
        ),
    }
    candidate["closure_receipt"]["source_visible_family_result_direct_mapping_receipt"] = {
        **receipt_material,
        "receipt_id": "gjisafav1:root:" + canonical_json_sha256_v1(receipt_material),
    }
    candidate["closure_receipt"]["structural_root_receipt"]["emitted_mapping"] = True
    candidate["closure_receipt"]["structural_root_receipt"]["mapping_policy"] = (
        "FAMILY33_SOURCE_VISIBLE_RESULT_DIRECT_COMPONENT_EQUATION_VETO"
    )


def _reseal_candidate_v1(
    candidate: dict[str, Any],
    *,
    source_repairs: Sequence[Mapping[str, Any]],
    terminal_receipts: Sequence[Mapping[str, Any]],
    unit_receipts: Sequence[Mapping[str, Any]],
    primary_receipt: Mapping[str, Any] | None,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    material = {
        "adapter_format_version": ADAPTER_FORMAT_VERSION,
        "primary_root_projection_receipt": canonical_clone_v1(primary_receipt),
        "shared_engine_claim_boundary": SHARED_CLAIM_BOUNDARY,
        "source_repair_overlay_id": compiled_specs[
            "investment_securities_activity_source_repair_overlay"
        ]["overlay_id"],
        "source_repair_receipts": canonical_clone_v1(list(source_repairs)),
        "source_repair_spec_sha256": compiled_specs[
            "investment_securities_activity_source_repair_spec_sha256"
        ],
        "terminal_result_projection_receipts": canonical_clone_v1(
            list(terminal_receipts)
        ),
        "unit_corroboration_receipts": canonical_clone_v1(list(unit_receipts)),
    }
    candidate["claim_boundary"] = CLAIM_BOUNDARY
    candidate["closure_receipt"]["investment_securities_activity_adapter_receipt"] = {
        **material,
        "adapter_receipt_id": "gjisafav1:receipt:"
        + canonical_json_sha256_v1(material),
    }
    candidate_material = {key: value for key, value in candidate.items() if key != "candidate_id"}
    candidate["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        candidate_material
    )
    return candidate


def evaluate_gemini_json_investment_securities_activity_family_cluster_v1(
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate Family 33 after exact, replayable source normalization."""

    if compiled_specs.get("topology", {}).get("family_id") != FAMILY_ID:
        raise _error("investment-securities adapter received another family")
    expected = build_gemini_json_investment_securities_activity_region_query_receipt_v1(regions)
    if type(query_receipt) is not dict or not same_typed_json_v1(query_receipt, expected):
        raise _error("investment-securities query receipt drifted")
    region_axis = expected["region_axis"]
    primary_receipt = None
    projected_pages = None
    repaired_pages, source_repairs = _apply_source_repairs_v1(
        pages=page_json_by_version,
        regions=region_axis,
        compiled_specs=compiled_specs,
    )
    primary_unit_receipts: list[dict[str, Any]] = []
    primary_source_pages = canonical_clone_v1(repaired_pages)
    primary_unit_receipts = _bind_same_page_exact_primary_units_v1(
        pages=primary_source_pages,
        regions=region_axis,
        compiled_specs=compiled_specs,
    )
    primary_projections = [
        primary
        for region in region_axis
        if (
            primary := _primary_statement_projection_v1(
                region=region,
                pages=primary_source_pages,
                compiled_specs=compiled_specs,
            )
        )
        is not None
    ]
    if len(primary_projections) == 1:
        projected_pages, primary_receipt = primary_projections[0]
    if projected_pages is None:
        projected_pages = repaired_pages
        terminal_receipts = _promote_visible_terminal_results_v1(
            pages=projected_pages,
            regions=region_axis,
            compiled_specs=compiled_specs,
        )
        unit_receipts = _bind_same_page_exact_primary_units_v1(
            pages=projected_pages,
            regions=region_axis,
            compiled_specs=compiled_specs,
        )
    else:
        terminal_receipts = []
        unit_receipts = primary_unit_receipts
    effective_specs = canonical_clone_v1(compiled_specs)
    visible_roots = _visible_result_row_axis_v1(
        pages=projected_pages,
        regions=region_axis,
        compiled_specs=effective_specs,
    )
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=region_axis,
        page_json_by_version=projected_pages,
        compiled_specs=effective_specs,
        query_receipt=query_receipt,
    )
    _bind_source_visible_family_result_v1(
        candidate,
        pages=projected_pages,
        regions=region_axis,
        visible_roots=visible_roots,
        compiled_specs=effective_specs,
    )
    _restore_projected_source_refs_v1(
        candidate,
        [*terminal_receipts, *([] if primary_receipt is None else [primary_receipt])],
    )
    if candidate.get("status") == READY and visible_roots:
        root_refs = {
            (
                ref["locator"]["page_json_version_id"],
                ref["locator"]["physical_page"],
                ref["locator"]["section_id"],
                ref["locator"]["table_id"],
                ref["row_ordinal"],
            )
            for mapping in candidate.get("mappings", [])
            if mapping.get("role") == "FAMILY_ROOT_TOTAL"
            for ref in mapping.get("source_refs", [])
        }
        expected_refs = {
            (
                item["locator"]["page_json_version_id"],
                item["locator"]["physical_page"],
                item["locator"]["section_id"],
                item["locator"]["table_id"],
                item["row_ordinal"],
            )
            for item in visible_roots
        }
        if not expected_refs <= root_refs:
            candidate["status"] = UNRESOLVED
            candidate["reasons"] = ["SOURCE_VISIBLE_FAMILY_RESULT_NOT_USED_DIRECTLY"]
            candidate["mappings"] = []
    has_root_mapping = any(
        mapping.get("role") == "FAMILY_ROOT_TOTAL"
        for mapping in candidate.get("mappings", [])
    )
    if candidate.get("status") == READY and not has_root_mapping:
        candidate["status"] = UNRESOLVED
        candidate["reasons"] = ["REQUIRED_SOURCE_VISIBLE_EXACT_FAMILY_ROOT_NOT_PROVEN"]
        candidate["mappings"] = []
    elif (
        candidate.get("status") == UNRESOLVED
        and not has_root_mapping
        and not visible_roots
        and "REQUIRED_SOURCE_VISIBLE_EXACT_FAMILY_ROOT_NOT_PROVEN"
        not in candidate.get("reasons", [])
    ):
        candidate["reasons"] = sorted(
            [
                *candidate.get("reasons", []),
                "REQUIRED_SOURCE_VISIBLE_EXACT_FAMILY_ROOT_NOT_PROVEN",
            ]
        )
    return _reseal_candidate_v1(
        candidate,
        source_repairs=source_repairs,
        terminal_receipts=terminal_receipts,
        unit_receipts=unit_receipts,
        primary_receipt=primary_receipt,
        compiled_specs=compiled_specs,
    )


def validate_gemini_json_investment_securities_activity_family_candidate_replay_v1(
    value: Any,
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    expected = evaluate_gemini_json_investment_securities_activity_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if type(value) is not dict or not same_typed_json_v1(value, expected):
        raise _error("investment-securities candidate replay drifted")
    return expected
