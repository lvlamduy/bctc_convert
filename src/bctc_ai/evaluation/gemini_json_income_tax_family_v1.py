"""Family-local source adapter for income-tax expense disclosures.

The shared multi-table engine remains the accounting authority.  This module
adds a deterministic fallback for tax rows printed directly on the primary
income statement and applies separately authenticated PDF transcription
repairs on private page clones.  It never derives a source value, turns a
blank into zero, or changes the shared evaluator/query policy.
"""

from __future__ import annotations

import json
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
    _multitable_lane_axis,
    _source_money,
    _source_table,
    _unit_axis,
    build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
    validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    validate_gemini_json_multitable_hierarchical_sweep_query_bindings_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FAMILY_ID = "INCOME_TAX"
ADAPTER_FORMAT_VERSION = "GEMINI_JSON_INCOME_TAX_FAMILY_ADAPTER_V1"
ADAPTER_SPEC_FORMAT_VERSION = "INCOME_TAX_FAMILY_ADAPTER_SPEC_V1"
SOURCE_REPAIR_FORMAT_VERSION = "INCOME_TAX_AUTHENTICATED_SOURCE_REPAIR_SPEC_V1"
QUERY_RECEIPT_FORMAT_VERSION = "GEMINI_JSON_INCOME_TAX_QUERY_RECEIPT_V1"
DEFAULT_ADAPTER_SPEC_PATH = "config/families/tm-income-tax-adapter-v1.json"
DEFAULT_SOURCE_REPAIR_SPEC_PATH = "config/families/tm-income-tax-source-repair-v1.json"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_INCOME_TAX_EXACT_PRIMARY_INCOME_"
    "STATEMENT_DIRECT_SOURCE_ROWS_FINAL_DURATION_LANES_PDF_AUTHENTICATED_"
    "PRIVATE_CLONE_REPAIR_NO_BLANK_ZERO_NO_VALUE_MAGNITUDE_OR_SIGN_"
    "BACKSOLVE_NO_BANK_FILE_YEAR_PAGE_ROUTING_PROPOSAL_ONLY_" + SHARED_CLAIM_BOUNDARY
)
_QUERY_ADAPTER_RULE = (
    "EXACT_PRIMARY_INCOME_STATEMENT_TAX_ROWS_PROJECTED_ON_PRIVATE_CLONE_"
    "WITH_OR_WITHOUT_A_READY_DIRECT_NOTE"
)
_QUERY_ADAPTER_STRATEGIES = {
    "DIRECT_NOTE_PLUS_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION",
    "DIRECT_NOTE_PLUS_SUPPLEMENTAL_NOTE_PLUS_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION",
    "DIRECT_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION",
}

_ROOT_LABELS = {
    "chi phi thue tndn",
    "chi phi thue tndn tam tinh",
    "chi phi thue thu nhap doanh nghiep",
    "chi phi thue thu nhap doanh nghiep tam tinh",
    "tong chi phi thue tndn",
    "tong chi phi thue thu nhap doanh nghiep",
}
_CANONICAL_LABEL = {
    "PROFIT_BEFORE_TAX": "Lợi nhuận kế toán trước thuế",
    "NON_DEDUCTIBLE_EXPENSE": "Chi phí không được khấu trừ",
    "CURRENT_TAX_AT_RATE": "Chi phí thuế TNDN theo thuế suất",
    "CURRENT_TAX_BANK": "Chi phí thuế TNDN hiện hành ước tính của Ngân hàng",
    "SUBSIDIARY_TAX": "Chi phí thuế TNDN hiện hành của công ty con",
    "PRIOR_PERIOD_TAX_ADJUSTMENT": "Điều chỉnh thuế TNDN các năm trước",
    "SOURCE_ONLY_EQUATION_COMPONENT": "Điều chỉnh khác",
    "CURRENT_TAX_PARENT": "Chi phí thuế TNDN hiện hành",
    "DEFERRED_TAX_NET": "Chi phí thuế thu nhập doanh nghiệp hoãn lại",
    "FAMILY_ROOT_TOTAL": "Chi phí thuế thu nhập doanh nghiệp",
}

_SUPPLEMENTAL_DIRECT_ROLES = (
    "PROFIT_BEFORE_TAX",
    "NON_DEDUCTIBLE_EXPENSE",
    "CURRENT_TAX_AT_RATE",
    "CURRENT_TAX_BANK",
    "SUBSIDIARY_TAX",
    "PRIOR_PERIOD_TAX_ADJUSTMENT",
    "CURRENT_TAX_PARENT",
    "DEFERRED_TAX_NET",
)
_SUPPLEMENTAL_PROJECTED_ROLES = (
    *_SUPPLEMENTAL_DIRECT_ROLES,
    "SOURCE_ONLY_EQUATION_COMPONENT",
)


class GeminiJsonIncomeTaxFamilyV1Error(ValueError):
    """Family-39 source evidence, projection, or replay drifted."""


def _error(message: str) -> GeminiJsonIncomeTaxFamilyV1Error:
    return GeminiJsonIncomeTaxFamilyV1Error(message)


def _load_json(path: str, *, message: str) -> dict[str, Any]:
    resolved = Path(__file__).resolve().parents[3] / path
    try:
        value = json.loads(resolved.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(message) from exc
    if type(value) is not dict:
        raise _error(message)
    return value


def _compile_adapter_spec(value: Any) -> dict[str, Any]:
    expected = {
        "family_id": FAMILY_ID,
        "format_version": ADAPTER_SPEC_FORMAT_VERSION,
        "primary_duplicate_presentation_policy": (
            "EVIDENCE_FRONTIER_DOMINANT_PRESENTATION_THEN_UNIQUE_VND_WITH_EXACT_"
            "COMMON_ROLE_ECONOMIC_COMPATIBILITY"
        ),
        "primary_projection_policy": (
            "EXACT_PRIMARY_INCOME_STATEMENT_TAX_ROWS_AND_FINAL_DURATION_LANES_PRIVATE_CLONE_ONLY"
        ),
        "primary_unit_corroboration_policy": (
            "UNIQUE_CANONICAL_UNIT_FROM_AT_LEAST_TWO_EXPLICIT_PRIMARY_"
            "STATEMENT_TABLES_SAME_DOCUMENT"
        ),
        "supplemental_note_projection_policy": (
            "EXACT_TAX_OWNER_TWO_LANE_DIRECT_ROLES_WITH_SOURCE_EQUATION_"
            "AND_EXHAUSTIVE_ROW_RECEIPT"
        ),
        "source_repair_policy": (
            "PDF_RENDER_AUTHENTICATED_EXACT_CELL_OR_ROW_TRANSCRIPTION_PRIVATE_CLONE_ONLY"
        ),
    }
    if type(value) is not dict or not same_typed_json_v1(value, expected):
        raise _error("income-tax adapter spec is invalid")
    return canonical_clone_v1(value)


def _sha256_string(value: Any) -> bool:
    return bool(
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _compile_source_repairs(value: Any) -> list[dict[str, Any]]:
    if (
        type(value) is not dict
        or set(value) != {"family_id", "format_version", "render_contract", "repairs"}
        or value.get("family_id") != FAMILY_ID
        or value.get("format_version") != SOURCE_REPAIR_FORMAT_VERSION
        or value.get("render_contract")
        != {
            "alpha": False,
            "colorspace": "RGB",
            "format": "PNG",
            "matrix": [2, 2],
            "renderer": "PyMuPDF",
        }
        or type(value.get("repairs")) is not list
    ):
        raise _error("income-tax source-repair spec is invalid")
    checked = []
    identities = set()
    for raw in value["repairs"]:
        locator = raw.get("locator") if type(raw) is dict else None
        visual = raw.get("visual_evidence") if type(raw) is dict else None
        kind = raw.get("repair_kind") if type(raw) is dict else None
        fields = {
            "after_exact",
            "before_exact",
            "locator",
            "pdf_source",
            "repair_id",
            "repair_kind",
            "visual_evidence",
        }
        if kind == "MONEY_CELL_PDF_VISIBLE_DASH":
            fields.add("column_ordinal")
        if (
            type(raw) is not dict
            or set(raw) != fields
            or kind not in {"MONEY_CELL_PDF_VISIBLE_DASH", "ROW_PDF_VISIBLE_EXACT"}
            or type(locator) is not dict
            or set(locator)
            != {
                "page_json_version_id",
                "physical_page",
                "row_ordinal",
                "section_id",
                "table_id",
            }
            or not str(locator.get("page_json_version_id", "")).startswith("gfpstorev1:json:")
            or type(locator.get("physical_page")) is not int
            or locator["physical_page"] <= 0
            or type(locator.get("row_ordinal")) is not int
            or locator["row_ordinal"] <= 0
            or type(locator.get("section_id")) is not str
            or type(locator.get("table_id")) is not str
            or type(raw.get("pdf_source")) is not dict
            or set(raw["pdf_source"]) != {"logical_name", "sha256", "size_bytes"}
            or type(raw["pdf_source"].get("logical_name")) is not str
            or not raw["pdf_source"]["logical_name"]
            or not _sha256_string(raw["pdf_source"].get("sha256"))
            or type(raw["pdf_source"].get("size_bytes")) is not int
            or raw["pdf_source"]["size_bytes"] <= 0
            or type(visual) is not dict
            or set(visual) != {"crop_bbox_pixels", "crop_rgb_sha256", "page_render"}
            or type(visual.get("crop_bbox_pixels")) is not list
            or len(visual["crop_bbox_pixels"]) != 4
            or any(type(item) is not int or item < 0 for item in visual["crop_bbox_pixels"])
            or not _sha256_string(visual.get("crop_rgb_sha256"))
            or type(visual.get("page_render")) is not dict
            or set(visual["page_render"]) != {"height_pixels", "sha256", "width_pixels"}
            or not _sha256_string(visual["page_render"].get("sha256"))
            or any(
                type(visual["page_render"].get(field)) is not int
                or visual["page_render"][field] <= 0
                for field in ("height_pixels", "width_pixels")
            )
            or visual["crop_bbox_pixels"][0] >= visual["crop_bbox_pixels"][2]
            or visual["crop_bbox_pixels"][1] >= visual["crop_bbox_pixels"][3]
            or visual["crop_bbox_pixels"][2] > visual["page_render"]["width_pixels"]
            or visual["crop_bbox_pixels"][3] > visual["page_render"]["height_pixels"]
        ):
            raise _error("income-tax source repair is invalid")
        if kind == "MONEY_CELL_PDF_VISIBLE_DASH" and (
            raw.get("before_exact") is not None
            or raw.get("after_exact") != "-"
            or type(raw.get("column_ordinal")) is not int
            or raw["column_ordinal"] <= 0
        ):
            raise _error("income-tax dash source repair is invalid")
        if kind == "ROW_PDF_VISIBLE_EXACT" and (
            type(raw.get("before_exact")) is not dict
            or type(raw.get("after_exact")) is not dict
            or set(raw["before_exact"])
            != {"hierarchy_path_exact", "label_exact", "row_kind", "values_exact"}
            or set(raw["after_exact"]) != set(raw["before_exact"])
        ):
            raise _error("income-tax row source repair is invalid")
        material = {
            key: canonical_clone_v1(item) for key, item in raw.items() if key != "repair_id"
        }
        if raw.get("repair_id") != "gjitfav1:repair:" + canonical_json_sha256_v1(material):
            raise _error("income-tax source-repair identity drifted")
        identity = (
            raw["pdf_source"]["sha256"],
            locator["page_json_version_id"],
            locator["section_id"],
            locator["table_id"],
            locator["row_ordinal"],
            raw.get("column_ordinal"),
        )
        if identity in identities:
            raise _error("income-tax source-repair axis is duplicate")
        identities.add(identity)
        checked.append(canonical_clone_v1(raw))
    ordered = sorted(
        checked,
        key=lambda item: (
            item["pdf_source"]["sha256"],
            item["locator"]["physical_page"],
            item["locator"]["section_id"],
            item["locator"]["table_id"],
            item["locator"]["row_ordinal"],
            item.get("column_ordinal", 0),
        ),
    )
    if not same_typed_json_v1(checked, ordered):
        raise _error("income-tax source-repair axis is unordered")
    return checked


def _private_specs(
    topology_spec: Mapping[str, Any],
    evaluation_spec: Mapping[str, Any],
    schema_binding_spec: Mapping[str, Any],
    *,
    root_component_roles: Sequence[str],
    root_policy: str,
) -> dict[str, Any]:
    topology = canonical_clone_v1(topology_spec)
    topology["required_role_combinations"] = [
        ["CURRENT_TAX_PARENT"],
        ["DEFERRED_TAX_NET"],
    ]
    evaluation = canonical_clone_v1(evaluation_spec)
    evaluation["family_root_requirement"] = "OPTIONAL"
    evaluation["minimum_declared_detail_role_count"] = 1
    evaluation["minimum_source_visible_root_component_count"] = 1
    evaluation["ordered_role_scopes"] = []
    evaluation["ordered_role_scope_projections"] = []
    evaluation["root_component_roles"] = list(root_component_roles)
    evaluation["unmapped_direct_family_row_policy"] = "IGNORE"
    schema = canonical_clone_v1(schema_binding_spec)
    schema["root_mapping_policy"] = root_policy
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(topology, evaluation, schema)


def _supplemental_specs(
    topology_spec: Mapping[str, Any],
    evaluation_spec: Mapping[str, Any],
    schema_binding_spec: Mapping[str, Any],
) -> dict[str, Any]:
    topology = canonical_clone_v1(topology_spec)
    topology["required_role_combinations"] = [
        [role] for role in _SUPPLEMENTAL_DIRECT_ROLES
    ]
    evaluation = canonical_clone_v1(evaluation_spec)
    evaluation["family_root_requirement"] = "OPTIONAL"
    evaluation["minimum_declared_detail_role_count"] = 1
    evaluation["minimum_source_visible_root_component_count"] = 1
    evaluation["ordered_role_scopes"] = []
    evaluation["ordered_role_scope_projections"] = []
    evaluation["root_component_roles"] = list(_SUPPLEMENTAL_PROJECTED_ROLES)
    evaluation["unmapped_direct_family_row_policy"] = "IGNORE"
    schema = canonical_clone_v1(schema_binding_spec)
    schema["root_mapping_policy"] = "STRUCTURAL_CONTEXT_ONLY"
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        topology, evaluation, schema
    )


def compile_gemini_json_income_tax_family_specs_v1(
    topology_spec: Any,
    evaluation_spec: Any,
    schema_binding_spec: Any,
    adapter_spec: Any | None = None,
    source_repair_spec: Any | None = None,
) -> dict[str, Any]:
    """Compile the shared family plus narrow private primary projections."""

    base = compile_gemini_json_multitable_hierarchical_family_specs_v1(
        topology_spec, evaluation_spec, schema_binding_spec
    )
    if base.get("topology", {}).get("family_id") != FAMILY_ID:
        raise _error("income-tax adapter received another family")
    adapter_raw = (
        _load_json(DEFAULT_ADAPTER_SPEC_PATH, message="income-tax adapter spec is absent")
        if adapter_spec is None
        else adapter_spec
    )
    repairs_raw = (
        _load_json(
            DEFAULT_SOURCE_REPAIR_SPEC_PATH,
            message="income-tax source-repair spec is absent",
        )
        if source_repair_spec is None
        else source_repair_spec
    )
    base["income_tax_adapter_spec"] = _compile_adapter_spec(adapter_raw)
    base["income_tax_adapter_spec_sha256"] = canonical_json_sha256_v1(adapter_raw)
    base["income_tax_source_repairs"] = _compile_source_repairs(repairs_raw)
    base["income_tax_source_repair_spec_sha256"] = canonical_json_sha256_v1(repairs_raw)
    base["income_tax_primary_both_specs"] = _private_specs(
        topology_spec,
        evaluation_spec,
        schema_binding_spec,
        root_component_roles=["CURRENT_TAX_PARENT", "DEFERRED_TAX_NET"],
        root_policy="SOURCE_VISIBLE_TOTAL_PROVEN_BY_EXACT_EQUATION_ONLY",
    )
    base["income_tax_primary_current_specs"] = _private_specs(
        topology_spec,
        evaluation_spec,
        schema_binding_spec,
        root_component_roles=["CURRENT_TAX_PARENT"],
        root_policy="SOURCE_VISIBLE_TOTAL_PROVEN_BY_EXACT_EQUATION_ONLY",
    )
    base["income_tax_primary_detail_specs"] = _private_specs(
        topology_spec,
        evaluation_spec,
        schema_binding_spec,
        root_component_roles=["CURRENT_TAX_PARENT", "DEFERRED_TAX_NET"],
        root_policy="STRUCTURAL_CONTEXT_ONLY",
    )
    base["income_tax_supplemental_specs"] = _supplemental_specs(
        topology_spec,
        evaluation_spec,
        schema_binding_spec,
    )
    return base


def _reseal_cluster(cluster: Mapping[str, Any], **updates: Any) -> dict[str, Any]:
    material = {
        key: canonical_clone_v1(value) for key, value in cluster.items() if key != "cluster_id"
    }
    material.update(canonical_clone_v1(updates))
    return {
        **material,
        "cluster_id": "gjmthfcv1:cluster:" + canonical_json_sha256_v1(material),
    }


def _apply_source_repairs(
    page_records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records = [canonical_clone_v1(item) for item in page_records]
    by_version = {item["page_json_version_id"]: item for item in records}
    if len(by_version) != len(records):
        raise _error("income-tax selected page axis is duplicate")
    source_sha256s = {item.get("source_sha256") for item in records}
    if len(source_sha256s) != 1:
        raise _error("income-tax selected document source axis is invalid")
    receipts = []
    source_sha256 = next(iter(source_sha256s))
    for repair in compiled_specs["income_tax_source_repairs"]:
        if repair["pdf_source"]["sha256"] != source_sha256:
            continue
        locator = repair["locator"]
        record = by_version.get(locator["page_json_version_id"])
        if (
            record is None
            or record.get("physical_page") != locator["physical_page"]
            or record.get("source_logical_name") != repair["pdf_source"]["logical_name"]
        ):
            raise _error("income-tax source-repair selected page drifted")
        page = record["page_json"]
        before_page_sha = canonical_json_sha256_v1(page)
        try:
            _section, table = _source_table(
                page,
                section_id=locator["section_id"],
                table_id=locator["table_id"],
            )
            row = table["rows"][locator["row_ordinal"] - 1]
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            raise _error("income-tax source-repair locator drifted") from exc
        if repair["repair_kind"] == "MONEY_CELL_PDF_VISIBLE_DASH":
            try:
                before = row["values_exact"][repair["column_ordinal"] - 1]
            except (IndexError, KeyError, TypeError) as exc:
                raise _error("income-tax source-repair cell drifted") from exc
            if before != repair["before_exact"]:
                raise _error("income-tax source-repair before image drifted")
            row["values_exact"][repair["column_ordinal"] - 1] = repair["after_exact"]
        else:
            before = {
                key: canonical_clone_v1(row.get(key))
                for key in (
                    "hierarchy_path_exact",
                    "label_exact",
                    "row_kind",
                    "values_exact",
                )
            }
            if not same_typed_json_v1(before, repair["before_exact"]):
                raise _error("income-tax source-repair row before image drifted")
            row.clear()
            row.update(canonical_clone_v1(repair["after_exact"]))
        after_page_sha = canonical_json_sha256_v1(page)
        material = {
            "after_page_json_sha256": after_page_sha,
            "before_page_json_sha256": before_page_sha,
            "repair": canonical_clone_v1(repair),
            "rule": (
                "PDF_RENDER_AUTHENTICATED_VISIBLE_SOURCE_TRANSCRIPTION_TO_PRIVATE_"
                "PAGE_CLONE_NO_BLANK_OR_VALUE_INFERENCE"
            ),
            "source_repair_spec_sha256": compiled_specs["income_tax_source_repair_spec_sha256"],
        }
        receipts.append(
            {
                **material,
                "receipt_id": "gjitfav1:repair-receipt:" + canonical_json_sha256_v1(material),
            }
        )
    return records, receipts


def _role_for_primary_label(value: Any) -> str | None:
    label = _without_leading_ordinal(_normalized(value))
    if "hien hanh" in label and "chi phi thue" in label:
        return "CURRENT_TAX_PARENT"
    if "hoan lai" in label and (
        "chi phi thue" in label or "loi ich thue" in label or "thu nhap thue" in label
    ):
        return "DEFERRED_TAX_NET"
    if label in _ROOT_LABELS:
        return "FAMILY_ROOT_TOTAL"
    return None


def _record_locator(record: Mapping[str, Any], *, section_id: str, table_id: str) -> dict[str, Any]:
    return {
        key: canonical_clone_v1(record[key])
        for key in (
            "document_id",
            "document_ordinal",
            "page_json_version_id",
            "physical_page",
            "selected_page_ordinal",
            "source_logical_name",
            "source_sha256",
        )
    } | {"section_id": section_id, "table_id": table_id}


def _primary_statement_unit_corroboration(
    page_records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any] | None:
    sources = []
    for record in page_records:
        page = record["page_json"]
        if page.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
            continue
        for section_ordinal, section in enumerate(page.get("sections") or [], start=1):
            if type(section) is not dict or section.get("content_kind") != "PRIMARY_STATEMENT":
                continue
            for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
                if type(table) is not dict:
                    continue
                unit = _unit_axis(table, compiled_specs=compiled_specs)
                if not unit.get("complete"):
                    if not _local_money_unit_is_truly_absent(unit):
                        return None
                    continue
                if unit.get("canonical_unit") not in {"MILLION_VND", "VND"}:
                    return None
                sources.append(
                    {
                        "canonical_unit": unit["canonical_unit"],
                        "evidence": canonical_clone_v1(unit["evidence"]),
                        "locator": _record_locator(
                            record,
                            section_id=f"s{section_ordinal}",
                            table_id=f"t{table_ordinal}",
                        ),
                        "statement_type": section.get("statement_type"),
                        "table_json_sha256": canonical_json_sha256_v1(table),
                    }
                )
    canonical_units = {item["canonical_unit"] for item in sources}
    if len(sources) < 2 or len(canonical_units) != 1:
        return None
    material = {
        "canonical_unit": next(iter(canonical_units)),
        "rule": (
            "AT_LEAST_TWO_DISTINCT_PRIMARY_STATEMENT_TABLES_EXPLICITLY_DECLARE_"
            "ONE_CANONICAL_UNIT_NO_VALUE_OR_MAGNITUDE_INFERENCE"
        ),
        "sources": sources,
    }
    return {
        **material,
        "receipt_id": "gjitfav1:primary-unit:" + canonical_json_sha256_v1(material),
    }


def _local_money_unit_is_truly_absent(unit_axis: Mapping[str, Any]) -> bool:
    """Permit document corroboration only when no local unit surface exists."""

    return bool(
        not unit_axis.get("complete")
        and unit_axis.get("canonical_unit") is None
        and unit_axis.get("evidence") == []
        and unit_axis.get("undeclared_evidence") == []
        and unit_axis.get("document_unit_context_evidence") is None
    )


def _primary_invalid_source_role_rows(
    page_records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    invalid = []
    for record in page_records:
        page = record["page_json"]
        if page.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
            continue
        for section_ordinal, section in enumerate(page.get("sections") or [], start=1):
            if (
                type(section) is not dict
                or section.get("content_kind") != "PRIMARY_STATEMENT"
                or section.get("statement_type") != "INCOME_STATEMENT"
            ):
                continue
            for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
                if type(table) is not dict:
                    continue
                lane = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
                money_ordinals = lane.get("money_column_ordinals")
                if (
                    not lane.get("complete")
                    or type(money_ordinals) is not list
                    or len(money_ordinals) != 2
                ):
                    continue
                for row_ordinal, row in enumerate(table.get("rows") or [], start=1):
                    if type(row) is not dict:
                        continue
                    role = _role_for_primary_label(row.get("label_exact"))
                    if role is None:
                        continue
                    values = row.get("values_exact")
                    selected = [
                        values[ordinal - 1]
                        if type(values) is list and ordinal <= len(values)
                        else None
                        for ordinal in money_ordinals
                    ]
                    reasons = []
                    for value in selected:
                        try:
                            parsed = _source_money(value)
                        except (TypeError, ValueError):
                            reasons.append("INVALID_PRIMARY_SOURCE_MONEY_CELL")
                        else:
                            reasons.extend(parsed.get("reasons", []))
                    if reasons:
                        invalid.append(
                            {
                                "locator": _record_locator(
                                    record,
                                    section_id=f"s{section_ordinal}",
                                    table_id=f"t{table_ordinal}",
                                ),
                                "reasons": sorted(set(reasons)),
                                "role": role,
                                "row_ordinal": row_ordinal,
                                "source_values_exact": canonical_clone_v1(selected),
                                "table_json_sha256": canonical_json_sha256_v1(table),
                            }
                        )
    return invalid


def _primary_duplicate_source_role_rows(
    page_records: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    duplicates = []
    for record in page_records:
        page = record["page_json"]
        if page.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
            continue
        for section_ordinal, section in enumerate(page.get("sections") or [], start=1):
            if (
                type(section) is not dict
                or section.get("content_kind") != "PRIMARY_STATEMENT"
                or section.get("statement_type") != "INCOME_STATEMENT"
            ):
                continue
            for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
                if type(table) is not dict:
                    continue
                by_role: dict[str, list[dict[str, Any]]] = {}
                for row_ordinal, row in enumerate(table.get("rows") or [], start=1):
                    if type(row) is not dict:
                        continue
                    role = _role_for_primary_label(row.get("label_exact"))
                    if role is not None:
                        by_role.setdefault(role, []).append(
                            {
                                "label_exact": row.get("label_exact"),
                                "row_ordinal": row_ordinal,
                                "values_exact": canonical_clone_v1(row.get("values_exact")),
                            }
                        )
                for role, rows in by_role.items():
                    if len(rows) > 1:
                        duplicates.append(
                            {
                                "locator": _record_locator(
                                    record,
                                    section_id=f"s{section_ordinal}",
                                    table_id=f"t{table_ordinal}",
                                ),
                                "role": role,
                                "rows": rows,
                                "table_json_sha256": canonical_json_sha256_v1(table),
                            }
                        )
    return duplicates


def _primary_equation_mismatch_axis(
    page_records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    mismatches = []
    for record in page_records:
        page = record["page_json"]
        if page.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
            continue
        for section_ordinal, section in enumerate(page.get("sections") or [], start=1):
            if (
                type(section) is not dict
                or section.get("content_kind") != "PRIMARY_STATEMENT"
                or section.get("statement_type") != "INCOME_STATEMENT"
            ):
                continue
            for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
                if type(table) is not dict:
                    continue
                lane = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
                money_ordinals = lane.get("money_column_ordinals")
                if (
                    not lane.get("complete")
                    or type(money_ordinals) is not list
                    or len(money_ordinals) != 2
                ):
                    continue
                by_role: dict[str, Mapping[str, Any]] = {}
                duplicate = False
                for row in table.get("rows") or []:
                    if type(row) is not dict:
                        continue
                    role = _role_for_primary_label(row.get("label_exact"))
                    if role is None:
                        continue
                    if role in by_role:
                        duplicate = True
                        break
                    by_role[role] = row
                if duplicate or not {"FAMILY_ROOT_TOTAL", "CURRENT_TAX_PARENT"}.issubset(
                    by_role
                ):
                    continue
                parsed_by_role = {}
                invalid = False
                for role in ("FAMILY_ROOT_TOTAL", "CURRENT_TAX_PARENT", "DEFERRED_TAX_NET"):
                    row = by_role.get(role)
                    if row is None:
                        parsed_by_role[role] = [0, 0]
                        continue
                    values = row.get("values_exact")
                    selected = [
                        values[ordinal - 1]
                        if type(values) is list and ordinal <= len(values)
                        else None
                        for ordinal in money_ordinals
                    ]
                    parsed = []
                    for value in selected:
                        try:
                            item = _source_money(value)
                        except (TypeError, ValueError):
                            invalid = True
                            break
                        if item.get("reasons"):
                            invalid = True
                            break
                        parsed.append(item.get("coefficient"))
                    if invalid:
                        break
                    parsed_by_role[role] = parsed
                if invalid:
                    continue
                lane_mismatches = []
                for ordinal, (root, current, deferred) in enumerate(
                    zip(
                        parsed_by_role["FAMILY_ROOT_TOTAL"],
                        parsed_by_role["CURRENT_TAX_PARENT"],
                        parsed_by_role["DEFERRED_TAX_NET"],
                        strict=True,
                    )
                ):
                    if root is None or current is None or deferred is None:
                        continue
                    if current + deferred != root:
                        lane_mismatches.append(
                            {
                                "current": current,
                                "deferred": deferred,
                                "lane_ordinal": ordinal,
                                "root": root,
                            }
                        )
                if lane_mismatches:
                    mismatches.append(
                        {
                            "lane_mismatches": lane_mismatches,
                            "locator": _record_locator(
                                record,
                                section_id=f"s{section_ordinal}",
                                table_id=f"t{table_ordinal}",
                            ),
                            "table_json_sha256": canonical_json_sha256_v1(table),
                        }
                    )
    return mismatches


def _primary_presentations(
    page_records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    presentations = []
    document_unit = _primary_statement_unit_corroboration(
        page_records, compiled_specs=compiled_specs
    )
    for record in page_records:
        page = record["page_json"]
        if page.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
            continue
        for section_ordinal, section in enumerate(page.get("sections") or [], start=1):
            if (
                type(section) is not dict
                or section.get("content_kind") != "PRIMARY_STATEMENT"
                or section.get("statement_type") != "INCOME_STATEMENT"
            ):
                continue
            for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
                if type(table) is not dict:
                    continue
                by_role: dict[str, list[tuple[int, Mapping[str, Any]]]] = {}
                for row_ordinal, row in enumerate(table.get("rows") or [], start=1):
                    if type(row) is not dict:
                        continue
                    role = _role_for_primary_label(row.get("label_exact"))
                    if role is not None:
                        by_role.setdefault(role, []).append((row_ordinal, row))
                if not by_role or any(len(items) != 1 for items in by_role.values()):
                    continue
                lane = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
                unit = _unit_axis(table, compiled_specs=compiled_specs)
                money_ordinals = lane.get("money_column_ordinals")
                if (
                    not lane.get("complete")
                    or type(money_ordinals) is not list
                    or len(money_ordinals) != 2
                ):
                    continue
                unit_receipt = None
                if unit.get("complete") and unit.get("canonical_unit") in {
                    "MILLION_VND",
                    "VND",
                }:
                    canonical_unit = unit["canonical_unit"]
                    unit_evidence = canonical_clone_v1(unit["evidence"])
                elif (
                    document_unit is not None
                    and _local_money_unit_is_truly_absent(unit)
                ):
                    canonical_unit = document_unit["canonical_unit"]
                    unit_evidence = canonical_clone_v1(document_unit["sources"])
                    unit_receipt = canonical_clone_v1(document_unit)
                else:
                    continue
                rows = []
                for role in (
                    "FAMILY_ROOT_TOTAL",
                    "CURRENT_TAX_PARENT",
                    "DEFERRED_TAX_NET",
                ):
                    if role not in by_role:
                        continue
                    row_ordinal, row = by_role[role][0]
                    values = row.get("values_exact")
                    if type(values) is not list or any(
                        ordinal > len(values) for ordinal in money_ordinals
                    ):
                        rows = []
                        break
                    selected = [values[ordinal - 1] for ordinal in money_ordinals]
                    parsed = []
                    for value in selected:
                        try:
                            parsed.append(_source_money(value))
                        except (TypeError, ValueError):
                            parsed.append(
                                {
                                    "coefficient": None,
                                    "reasons": ["INVALID_PRIMARY_SOURCE_MONEY_CELL"],
                                }
                            )
                    rows.append(
                        {
                            "hierarchy_path_exact": canonical_clone_v1(
                                row.get("hierarchy_path_exact")
                            ),
                            "label_exact": row.get("label_exact"),
                            "parsed_values": [item.get("coefficient") for item in parsed],
                            "row_kind": row.get("row_kind"),
                            "row_ordinal": row_ordinal,
                            "role": role,
                            "source_values_exact": canonical_clone_v1(selected),
                            "values_usable": all(not item.get("reasons") for item in parsed),
                        }
                    )
                if not rows:
                    continue
                by_output_role = {item["role"]: item for item in rows}
                root = by_output_role.get("FAMILY_ROOT_TOTAL")
                current = by_output_role.get("CURRENT_TAX_PARENT")
                deferred = by_output_role.get("DEFERRED_TAX_NET")
                included = []
                if root is not None and root["values_usable"]:
                    included.append(root)
                if current is not None and current["values_usable"]:
                    included.append(current)
                if deferred is not None and deferred["values_usable"]:
                    if any(value is not None for value in deferred["parsed_values"]):
                        included.append(deferred)
                included_by_role = {item["role"]: item for item in included}
                root_values = (
                    included_by_role["FAMILY_ROOT_TOTAL"]["parsed_values"]
                    if "FAMILY_ROOT_TOTAL" in included_by_role
                    else None
                )
                current_values = (
                    included_by_role["CURRENT_TAX_PARENT"]["parsed_values"]
                    if "CURRENT_TAX_PARENT" in included_by_role
                    else None
                )
                deferred_values = (
                    included_by_role["DEFERRED_TAX_NET"]["parsed_values"]
                    if "DEFERRED_TAX_NET" in included_by_role
                    else None
                )
                if root_values is not None and current_values is not None:
                    observed_lane_mismatch = False
                    for root_value, current_value, deferred_value in zip(
                        root_values,
                        current_values,
                        deferred_values or [0] * len(root_values),
                        strict=True,
                    ):
                        if root_value is None or current_value is None or deferred_value is None:
                            continue
                        if current_value + deferred_value != root_value:
                            observed_lane_mismatch = True
                            break
                    if observed_lane_mismatch:
                        continue
                if not included:
                    continue
                role_axis = [item["role"] for item in included]
                if "FAMILY_ROOT_TOTAL" in role_axis and "DEFERRED_TAX_NET" in role_axis:
                    specs_key = "income_tax_primary_both_specs"
                elif "FAMILY_ROOT_TOTAL" in role_axis and "CURRENT_TAX_PARENT" in role_axis:
                    specs_key = "income_tax_primary_current_specs"
                elif "FAMILY_ROOT_TOTAL" in role_axis:
                    specs_key = "income_tax_primary_current_specs"
                else:
                    specs_key = "income_tax_primary_detail_specs"
                columns = table.get("columns")
                if type(columns) is not list:
                    continue
                descriptor = {
                    "canonical_unit": canonical_unit,
                    "locator": _record_locator(
                        record,
                        section_id=f"s{section_ordinal}",
                        table_id=f"t{table_ordinal}",
                    ),
                    "money_column_ordinals": canonical_clone_v1(money_ordinals),
                    "original_page_json_sha256": canonical_json_sha256_v1(page),
                    "original_table_json_sha256": canonical_json_sha256_v1(table),
                    "primary_unit_corroboration_receipt": unit_receipt,
                    "projected_unit_exact": (
                        "Triệu VND" if canonical_unit == "MILLION_VND" else "VND"
                    ),
                    "projected_specs_key": specs_key,
                    "rows": canonical_clone_v1(included),
                    "source_role_rows": canonical_clone_v1(rows),
                    "unit_evidence": unit_evidence,
                }
                projected_page = _project_primary_page(page, descriptor=descriptor)
                descriptor["projected_page_json_sha256"] = canonical_json_sha256_v1(projected_page)
                presentations.append(descriptor)
    return presentations


def _supplemental_owner_matches(
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
) -> bool:
    surface = _normalized(
        " | ".join(
            value
            for value in (section.get("title_exact"), table.get("title_exact"))
            if type(value) is str and value.strip()
        )
    )
    aliases = compiled_specs.get("query_policy", {}).get("owner_aliases", [])
    negative_aliases = {
        *compiled_specs.get("query_policy", {}).get("hard_negative_aliases", []),
        *compiled_specs.get("query_policy", {}).get("reset_aliases", []),
    }
    if any(alias in surface for alias in negative_aliases):
        return False
    return bool(surface and any(alias in surface for alias in aliases))


def _supplemental_role_alias_axis(
    compiled_specs: Mapping[str, Any],
) -> dict[str, str]:
    axis: dict[str, str] = {}
    for child in compiled_specs["topology"]["children"]:
        role = child["role"]
        if role not in _SUPPLEMENTAL_DIRECT_ROLES:
            continue
        for matcher in child["matchers"]:
            for alias in matcher["aliases"]:
                if alias in axis and axis[alias] != role:
                    raise _error("income-tax supplemental role alias is ambiguous")
                axis[alias] = role
    return axis


def _supplemental_source_rows(
    table: Mapping[str, Any],
    *,
    money_column_ordinals: Sequence[int],
    role_alias_axis: Mapping[str, str],
) -> list[dict[str, Any]]:
    output = []
    for row_ordinal, row in enumerate(table.get("rows") or [], start=1):
        if type(row) is not dict:
            raise _error("income-tax supplemental source row is invalid")
        values = row.get("values_exact")
        if type(values) is not list:
            raise _error("income-tax supplemental source values are invalid")
        selected = [
            values[ordinal - 1] if ordinal <= len(values) else None
            for ordinal in money_column_ordinals
        ]
        parsed = []
        for value in selected:
            try:
                parsed.append(_source_money(value))
            except (TypeError, ValueError):
                parsed.append(
                    {
                        "coefficient": None,
                        "reasons": ["INVALID_SUPPLEMENTAL_SOURCE_MONEY_CELL"],
                    }
                )
        normalized_label = _without_leading_ordinal(_normalized(row.get("label_exact")))
        output.append(
            {
                "hierarchy_path_exact": canonical_clone_v1(row.get("hierarchy_path_exact")),
                "label_exact": row.get("label_exact"),
                "matched_role": role_alias_axis.get(normalized_label),
                "normalized_label": normalized_label,
                "parsed_values": [item.get("coefficient") for item in parsed],
                "row_kind": row.get("row_kind"),
                "row_ordinal": row_ordinal,
                "source_values_exact": canonical_clone_v1(selected),
                "values_usable": all(not item.get("reasons") for item in parsed),
            }
        )
    return output


def _all_observed(values: Sequence[int | None]) -> bool:
    return bool(values and all(value is not None for value in values))


def _exact_sum(
    components: Sequence[Mapping[str, Any]], parent: Mapping[str, Any]
) -> bool:
    component_values = [item["parsed_values"] for item in components]
    parent_values = parent["parsed_values"]
    if (
        not components
        or not _all_observed(parent_values)
        or any(not _all_observed(values) for values in component_values)
    ):
        return False
    return all(
        sum(values[lane] for values in component_values) == parent_values[lane]
        for lane in range(len(parent_values))
    )


def _projected_source_row(
    item: Mapping[str, Any], *, role: str, projected_row_kind: str
) -> dict[str, Any]:
    return {
        key: canonical_clone_v1(item[key])
        for key in (
            "hierarchy_path_exact",
            "label_exact",
            "parsed_values",
            "row_kind",
            "row_ordinal",
            "source_values_exact",
            "values_usable",
        )
    } | {"projected_row_kind": projected_row_kind, "role": role}


def _supplemental_equation_receipt(
    *,
    component_rows: Sequence[Mapping[str, Any]],
    parent_row: Mapping[str, Any],
    equation_kind: str,
) -> dict[str, Any]:
    material = {
        "component_rows": [
            {
                "parsed_values": canonical_clone_v1(item["parsed_values"]),
                "role": item["role"],
                "row_ordinal": item["row_ordinal"],
            }
            for item in component_rows
        ],
        "equation_kind": equation_kind,
        "parent_row": {
            "parsed_values": canonical_clone_v1(parent_row["parsed_values"]),
            "role": parent_row["role"],
            "row_ordinal": parent_row["row_ordinal"],
        },
        "status": "EXACT_ALL_OBSERVED_LANES",
    }
    return {
        **material,
        "equation_id": "gjitfav1:supplemental-equation:"
        + canonical_json_sha256_v1(material),
    }


def _finalize_supplemental_descriptor(
    *,
    record: Mapping[str, Any],
    page: Mapping[str, Any],
    section_ordinal: int,
    table_ordinal: int,
    table: Mapping[str, Any],
    money_column_ordinals: Sequence[int],
    canonical_unit: str,
    unit_evidence: Any,
    unit_receipt: Mapping[str, Any] | None,
    source_rows: Sequence[Mapping[str, Any]],
    rows: Sequence[Mapping[str, Any]],
    presentation_kind: str,
    equation_receipts: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    descriptor = {
        "canonical_unit": canonical_unit,
        "equation_receipts": canonical_clone_v1(list(equation_receipts)),
        "locator": _record_locator(
            record,
            section_id=f"s{section_ordinal}",
            table_id=f"t{table_ordinal}",
        ),
        "money_column_ordinals": canonical_clone_v1(list(money_column_ordinals)),
        "original_page_json_sha256": canonical_json_sha256_v1(page),
        "original_table_json_sha256": canonical_json_sha256_v1(table),
        "presentation_kind": presentation_kind,
        "primary_unit_corroboration_receipt": canonical_clone_v1(unit_receipt),
        "projected_specs_key": "income_tax_supplemental_specs",
        "projected_unit_exact": "Triệu VND" if canonical_unit == "MILLION_VND" else "VND",
        "rows": canonical_clone_v1(list(rows)),
        "source_table_row_axis": canonical_clone_v1(list(source_rows)),
        "unit_evidence": canonical_clone_v1(unit_evidence),
    }
    projected_page = _project_primary_page(page, descriptor=descriptor)
    descriptor["projected_page_json_sha256"] = canonical_json_sha256_v1(projected_page)
    projected_record = {
        key: canonical_clone_v1(descriptor["locator"][key])
        for key in (
            "document_id",
            "document_ordinal",
            "page_json_version_id",
            "physical_page",
            "selected_page_ordinal",
            "source_logical_name",
            "source_sha256",
        )
    } | {"page_json": projected_page}
    specs = compiled_specs["income_tax_supplemental_specs"]
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[projected_record], compiled_specs=specs
    )
    if cluster.get("status") != READY:
        return None
    regions = cluster["component_regions"]
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=regions,
        page_json_by_version={descriptor["locator"]["page_json_version_id"]: projected_page},
        compiled_specs=specs,
        query_receipt=(
            build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
        ),
    )
    if candidate.get("status") != READY:
        return None
    descriptor["projected_component_regions"] = canonical_clone_v1(regions)
    material = canonical_clone_v1(descriptor)
    descriptor["descriptor_id"] = (
        "gjitfav1:supplemental:" + canonical_json_sha256_v1(material)
    )
    return descriptor


def _supplemental_presentations(
    page_records: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
    issues: list[str] | None = None,
    consumed_source_rows: frozenset[tuple[str, str, str, int]] = frozenset(),
) -> list[dict[str, Any]]:
    role_alias_axis = _supplemental_role_alias_axis(compiled_specs)
    document_unit = _primary_statement_unit_corroboration(
        page_records, compiled_specs=compiled_specs
    )
    descriptors = []
    for record in page_records:
        page = record["page_json"]
        for section_ordinal, section in enumerate(page.get("sections") or [], start=1):
            if type(section) is not dict or section.get("content_kind") != "FINANCIAL_NOTE":
                continue
            for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
                if type(table) is not dict or not _supplemental_owner_matches(
                    section, table, compiled_specs=compiled_specs
                ):
                    continue
                lane = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
                money_ordinals = lane.get("money_column_ordinals")
                if (
                    not lane.get("complete")
                    or type(money_ordinals) is not list
                    or len(money_ordinals) != 2
                ):
                    continue
                unit = _unit_axis(table, compiled_specs=compiled_specs)
                unit_receipt = None
                if unit.get("complete") and unit.get("canonical_unit") in {
                    "MILLION_VND",
                    "VND",
                }:
                    canonical_unit = unit["canonical_unit"]
                    unit_evidence = canonical_clone_v1(unit["evidence"])
                elif (
                    document_unit is not None
                    and _local_money_unit_is_truly_absent(unit)
                ):
                    canonical_unit = document_unit["canonical_unit"]
                    unit_evidence = canonical_clone_v1(document_unit["sources"])
                    unit_receipt = canonical_clone_v1(document_unit)
                else:
                    continue
                all_source_rows = _supplemental_source_rows(
                    table,
                    money_column_ordinals=money_ordinals,
                    role_alias_axis=role_alias_axis,
                )
                if consumed_source_rows and not any(
                    (
                        item["matched_role"] in _SUPPLEMENTAL_DIRECT_ROLES
                        or (
                            "ngan hang" in item["normalized_label"]
                            and "thue" not in item["normalized_label"]
                        )
                        or (
                            "cong ty" in item["normalized_label"]
                            and (
                                "quan ly no" in item["normalized_label"]
                                or "khai thac tai san" in item["normalized_label"]
                                or "amc" in item["normalized_label"]
                            )
                        )
                        or item["normalized_label"] in {"ky hien hanh", "nam hien hanh"}
                    )
                    and (
                        record["page_json_version_id"],
                        f"s{section_ordinal}",
                        f"t{table_ordinal}",
                        item["row_ordinal"],
                    )
                    not in consumed_source_rows
                    for item in all_source_rows
                ):
                    continue
                negative_aliases = {
                    *compiled_specs.get("query_policy", {}).get(
                        "hard_negative_aliases", []
                    ),
                    *compiled_specs.get("query_policy", {}).get("reset_aliases", []),
                }
                reset_ordinals = [
                    item["row_ordinal"]
                    for item in all_source_rows
                    if item["row_kind"] in {"GROUP", "SUBTOTAL", "TOTAL"}
                    and any(
                        alias in item["normalized_label"] for alias in negative_aliases
                    )
                ]
                if reset_ordinals:
                    first_reset = min(reset_ordinals)
                    if any(
                        item["row_ordinal"] > first_reset
                        and item["matched_role"] in _SUPPLEMENTAL_DIRECT_ROLES
                        for item in all_source_rows
                    ):
                        if issues is not None:
                            issues.append("SUPPLEMENTAL_ROLE_AFTER_STRUCTURAL_RESET")
                        continue
                    source_rows = [
                        item
                        for item in all_source_rows
                        if item["row_ordinal"] < first_reset
                    ]
                else:
                    source_rows = all_source_rows
                claimed: set[int] = set()
                table_has_certified_equation = False
                table_equation_receipts: list[dict[str, Any]] = []
                certified_adjustment_ordinals: set[int] = set()

                bank_surface_rows = [
                    item
                    for item in source_rows
                    if (
                        item["matched_role"] == "CURRENT_TAX_BANK"
                        or (
                            "ngan hang" in item["normalized_label"]
                            and "cong ty" not in item["normalized_label"]
                            and "thue" not in item["normalized_label"]
                        )
                    )
                    and item["row_kind"] not in {"SUBTOTAL", "TOTAL"}
                ]
                subsidiary_surface_rows = [
                    item
                    for item in source_rows
                    if (
                        item["matched_role"] == "SUBSIDIARY_TAX"
                        or (
                            "cong ty" in item["normalized_label"]
                            and "thue" not in item["normalized_label"]
                            and (
                                "quan ly no" in item["normalized_label"]
                                or "khai thac tai san" in item["normalized_label"]
                                or "amc" in item["normalized_label"]
                            )
                        )
                    )
                ]
                bank_rows = [
                    item
                    for item in bank_surface_rows
                    if item["values_usable"] and _all_observed(item["parsed_values"])
                ]
                subsidiary_rows = [
                    item
                    for item in subsidiary_surface_rows
                    if item["values_usable"] and _all_observed(item["parsed_values"])
                ]
                entity_parents = [
                    item
                    for item in source_rows
                    if item["row_kind"] in {"SUBTOTAL", "TOTAL"}
                    and (
                        item["normalized_label"] in {"cong", "tong cong"}
                        or item["matched_role"] == "CURRENT_TAX_PARENT"
                    )
                ]
                entity_shape_present = bool(bank_surface_rows and subsidiary_surface_rows)
                if entity_shape_present and not (
                    len(bank_surface_rows)
                    == len(subsidiary_surface_rows)
                    == len(bank_rows)
                    == len(subsidiary_rows)
                    == len(entity_parents)
                    == 1
                ):
                    if issues is not None:
                        issues.append("SUPPLEMENTAL_CURRENT_TAX_ENTITY_AXIS_NOT_UNIQUE")
                elif len(bank_rows) == len(subsidiary_rows) == len(entity_parents) == 1:
                    component_ordinals = {
                        bank_rows[0]["row_ordinal"],
                        subsidiary_rows[0]["row_ordinal"],
                    }
                    parent_ordinal = entity_parents[0]["row_ordinal"]
                    entity_frontier = [
                        item
                        for item in source_rows
                        if min(component_ordinals) <= item["row_ordinal"] < parent_ordinal
                    ]
                    if (
                        not all(ordinal < parent_ordinal for ordinal in component_ordinals)
                        or {item["row_ordinal"] for item in entity_frontier}
                        != component_ordinals
                    ):
                        if issues is not None:
                            issues.append(
                                "SUPPLEMENTAL_CURRENT_TAX_ENTITY_FRONTIER_NOT_COMPLETE"
                            )
                        continue
                    entity_rows = [
                        _projected_source_row(
                            bank_rows[0], role="CURRENT_TAX_BANK", projected_row_kind="ITEM"
                        ),
                        _projected_source_row(
                            subsidiary_rows[0],
                            role="SUBSIDIARY_TAX",
                            projected_row_kind="ITEM",
                        ),
                        _projected_source_row(
                            entity_parents[0],
                            role="CURRENT_TAX_PARENT",
                            projected_row_kind="TOTAL",
                        ),
                    ]
                    if _exact_sum(entity_rows[:2], entity_rows[2]):
                        equation = _supplemental_equation_receipt(
                            component_rows=entity_rows[:2],
                            parent_row=entity_rows[2],
                            equation_kind="BANK_PLUS_ASSET_MANAGEMENT_SUBSIDIARY_EQUALS_CURRENT_TAX",
                        )
                        table_equation_receipts.append(equation)
                        descriptor = _finalize_supplemental_descriptor(
                            record=record,
                            page=page,
                            section_ordinal=section_ordinal,
                            table_ordinal=table_ordinal,
                            table=table,
                            money_column_ordinals=money_ordinals,
                            canonical_unit=canonical_unit,
                            unit_evidence=unit_evidence,
                            unit_receipt=unit_receipt,
                            source_rows=all_source_rows,
                            rows=entity_rows,
                            presentation_kind="CURRENT_TAX_ENTITY_SPLIT_EXACT_SUM",
                            equation_receipts=[equation],
                            compiled_specs=compiled_specs,
                        )
                        if descriptor is not None:
                            descriptors.append(descriptor)
                            claimed.update(item["row_ordinal"] for item in entity_rows)
                            table_has_certified_equation = True
                    elif issues is not None:
                        issues.append("SUPPLEMENTAL_CURRENT_TAX_ENTITY_EQUATION_MISMATCH")

                rate_rows = [
                    item
                    for item in source_rows
                    if item["matched_role"] == "CURRENT_TAX_AT_RATE"
                    or item["normalized_label"] in {"ky hien hanh", "nam hien hanh"}
                ]
                if len(rate_rows) > 1 and issues is not None:
                    issues.append("SUPPLEMENTAL_CURRENT_TAX_RATE_AXIS_NOT_UNIQUE")
                if len(rate_rows) == 1:
                    parent_options = [
                        item
                        for item in source_rows
                        if item["row_ordinal"] > rate_rows[0]["row_ordinal"]
                        and item["row_kind"] in {"SUBTOTAL", "TOTAL"}
                    ]
                    if parent_options:
                        parent = parent_options[0]
                        component_items = [
                            item
                            for item in source_rows
                            if rate_rows[0]["row_ordinal"] <= item["row_ordinal"]
                            < parent["row_ordinal"]
                        ]
                        frontier_complete = bool(
                            component_items
                            and component_items[0] is rate_rows[0]
                            and all(
                                item["row_kind"] not in {"GROUP", "SUBTOTAL", "TOTAL"}
                                for item in component_items
                            )
                            and parent["values_usable"]
                            and _all_observed(parent["parsed_values"])
                            and all(
                                item["values_usable"]
                                and _all_observed(item["parsed_values"])
                                for item in component_items
                            )
                        )
                        equation_components = [
                            _projected_source_row(
                                item,
                                role=(
                                    "CURRENT_TAX_AT_RATE"
                                    if item is rate_rows[0]
                                    else (
                                        item["matched_role"]
                                        if item["matched_role"]
                                        in _SUPPLEMENTAL_DIRECT_ROLES
                                        else "SOURCE_ONLY_EQUATION_COMPONENT"
                                    )
                                ),
                                projected_row_kind="ITEM",
                            )
                            for item in component_items
                        ] if frontier_complete else []
                        equation_parent = _projected_source_row(
                            parent,
                            role="CURRENT_TAX_PARENT",
                            projected_row_kind="TOTAL",
                        )
                        if not frontier_complete:
                            if issues is not None:
                                issues.append(
                                    "SUPPLEMENTAL_CURRENT_TAX_FRONTIER_NOT_COMPLETE"
                                )
                        elif _exact_sum(equation_components, equation_parent):
                            equation = _supplemental_equation_receipt(
                                component_rows=equation_components,
                                parent_row=equation_parent,
                                equation_kind="CURRENT_RATE_PLUS_VISIBLE_ADJUSTMENTS_EQUALS_CURRENT_TAX",
                            )
                            equation_rows = [*equation_components, equation_parent]
                            table_equation_receipts.append(equation)
                            table_has_certified_equation = True
                            certified_adjustment_ordinals.update(
                                item["row_ordinal"]
                                for item in equation_components
                                if item["role"]
                                in {
                                    "NON_DEDUCTIBLE_EXPENSE",
                                    "PRIOR_PERIOD_TAX_ADJUSTMENT",
                                }
                            )
                            descriptor = _finalize_supplemental_descriptor(
                                record=record,
                                page=page,
                                section_ordinal=section_ordinal,
                                table_ordinal=table_ordinal,
                                table=table,
                                money_column_ordinals=money_ordinals,
                                canonical_unit=canonical_unit,
                                unit_evidence=unit_evidence,
                                unit_receipt=unit_receipt,
                                source_rows=all_source_rows,
                                rows=equation_rows,
                                presentation_kind="CURRENT_TAX_RECONCILIATION_EXACT_SUM",
                                equation_receipts=[equation],
                                compiled_specs=compiled_specs,
                            )
                            if descriptor is not None:
                                descriptors.append(descriptor)
                                claimed.update(item["row_ordinal"] for item in equation_rows)
                        elif issues is not None:
                            issues.append("SUPPLEMENTAL_CURRENT_TAX_EQUATION_MISMATCH")
                    elif issues is not None:
                        issues.append("SUPPLEMENTAL_CURRENT_TAX_FRONTIER_NOT_COMPLETE")

                nonblank_rows = [
                    item
                    for item in source_rows
                    if item["values_usable"]
                    and any(value is not None for value in item["parsed_values"])
                ]
                direct_parent_surface_rows = [
                    item
                    for item in source_rows
                    if item["matched_role"] == "CURRENT_TAX_PARENT"
                ]
                direct_parent_rows = [
                    item
                    for item in nonblank_rows
                    if item["matched_role"] == "CURRENT_TAX_PARENT"
                ]
                if len(direct_parent_surface_rows) > 1 and issues is not None:
                    issues.append("SUPPLEMENTAL_CURRENT_TAX_PARENT_AXIS_NOT_UNIQUE")
                if (
                    len(nonblank_rows) == 1
                    and len(direct_parent_rows) == 1
                ):
                    direct_parent = _projected_source_row(
                        nonblank_rows[0],
                        role="CURRENT_TAX_PARENT",
                        projected_row_kind="ITEM",
                    )
                    descriptor = _finalize_supplemental_descriptor(
                        record=record,
                        page=page,
                        section_ordinal=section_ordinal,
                        table_ordinal=table_ordinal,
                        table=table,
                        money_column_ordinals=money_ordinals,
                        canonical_unit=canonical_unit,
                        unit_evidence=unit_evidence,
                        unit_receipt=unit_receipt,
                        source_rows=all_source_rows,
                        rows=[direct_parent],
                        presentation_kind="DIRECT_CURRENT_TAX_SINGLETON",
                        equation_receipts=[],
                        compiled_specs=compiled_specs,
                    )
                    if descriptor is not None:
                        descriptors.append(descriptor)
                        claimed.add(direct_parent["row_ordinal"])
                elif (
                    len(direct_parent_surface_rows) == 1
                    and (
                        len(direct_parent_rows) != 1
                        or direct_parent_surface_rows[0]["row_ordinal"] not in claimed
                    )
                    and not table_has_certified_equation
                    and not rate_rows
                    and issues is not None
                ):
                    issues.append("SUPPLEMENTAL_CURRENT_TAX_SINGLETON_FRONTIER_NOT_COMPLETE")

                extra_roles = {
                    "PROFIT_BEFORE_TAX",
                    "CURRENT_TAX_BANK",
                    "SUBSIDIARY_TAX",
                    "DEFERRED_TAX_NET",
                }
                if table_has_certified_equation:
                    extra_roles.update(
                        {"NON_DEDUCTIBLE_EXPENSE", "PRIOR_PERIOD_TAX_ADJUSTMENT"}
                    )
                direct_extras = []
                for role in sorted(extra_roles):
                    surface_matches = [
                        item
                        for item in source_rows
                        if item["matched_role"] == role
                        and item["row_ordinal"] not in claimed
                        and (
                            role
                            not in {
                                "NON_DEDUCTIBLE_EXPENSE",
                                "PRIOR_PERIOD_TAX_ADJUSTMENT",
                            }
                            or item["row_ordinal"] in certified_adjustment_ordinals
                        )
                    ]
                    matches = [
                        item
                        for item in surface_matches
                        if item["values_usable"]
                        and any(value is not None for value in item["parsed_values"])
                    ]
                    if len(surface_matches) > 1 and issues is not None:
                        issues.append("SUPPLEMENTAL_DIRECT_ROLE_AXIS_NOT_UNIQUE:" + role)
                    elif len(surface_matches) == len(matches) == 1:
                        direct_extras.append(
                            _projected_source_row(
                                matches[0], role=role, projected_row_kind="ITEM"
                            )
                        )
                    elif len(surface_matches) == 1 and issues is not None:
                        issues.append("SUPPLEMENTAL_DIRECT_ROLE_FRONTIER_NOT_COMPLETE:" + role)
                if direct_extras:
                    descriptor = _finalize_supplemental_descriptor(
                        record=record,
                        page=page,
                        section_ordinal=section_ordinal,
                        table_ordinal=table_ordinal,
                        table=table,
                        money_column_ordinals=money_ordinals,
                        canonical_unit=canonical_unit,
                        unit_evidence=unit_evidence,
                        unit_receipt=unit_receipt,
                        source_rows=all_source_rows,
                        rows=direct_extras,
                        presentation_kind="DIRECT_SUPPLEMENTAL_TAX_ROLES",
                        equation_receipts=table_equation_receipts,
                        compiled_specs=compiled_specs,
                    )
                    if descriptor is not None:
                        descriptors.append(descriptor)
    if issues is not None:
        issues[:] = sorted(set(issues))
    return sorted(
        descriptors,
        key=lambda item: (
            item["locator"]["selected_page_ordinal"],
            item["locator"]["section_id"],
            item["locator"]["table_id"],
            item["presentation_kind"],
        ),
    )


def _project_primary_page(
    source_page: Mapping[str, Any], *, descriptor: Mapping[str, Any]
) -> dict[str, Any]:
    locator = descriptor["locator"]
    try:
        source_section, source_table = _source_table(
            source_page,
            section_id=locator["section_id"],
            table_id=locator["table_id"],
        )
        columns = source_table["columns"]
        source_rows = source_table["rows"]
    except (KeyError, TypeError, ValueError) as exc:
        raise _error("income-tax primary source locator drifted") from exc
    if (
        canonical_json_sha256_v1(source_page) != descriptor["original_page_json_sha256"]
        or canonical_json_sha256_v1(source_table) != descriptor["original_table_json_sha256"]
    ):
        raise _error("income-tax primary source image drifted")
    projected_rows = []
    root_label = _CANONICAL_LABEL["FAMILY_ROOT_TOTAL"]
    for projected_ordinal, item in enumerate(descriptor["rows"], start=1):
        try:
            source_row = source_rows[item["row_ordinal"] - 1]
            selected = [
                source_row["values_exact"][ordinal - 1]
                for ordinal in descriptor["money_column_ordinals"]
            ]
        except (IndexError, KeyError, TypeError) as exc:
            raise _error("income-tax primary source row drifted") from exc
        if (
            source_row.get("label_exact") != item["label_exact"]
            or source_row.get("row_kind") != item["row_kind"]
            or source_row.get("hierarchy_path_exact") != item["hierarchy_path_exact"]
            or not same_typed_json_v1(selected, item["source_values_exact"])
        ):
            raise _error("income-tax primary source row image drifted")
        role = item["role"]
        canonical = _CANONICAL_LABEL[role]
        projected_rows.append(
            {
                "hierarchy_path_exact": (
                    [root_label] if role == "FAMILY_ROOT_TOTAL" else [root_label, canonical]
                ),
                "label_exact": canonical,
                "row_kind": item.get(
                    "projected_row_kind",
                    "TOTAL" if role == "FAMILY_ROOT_TOTAL" else "ITEM",
                ),
                "values_exact": canonical_clone_v1(selected),
            }
        )
        if projected_ordinal <= 0:  # pragma: no cover - documents the one-based axis
            raise AssertionError
    projected_table = {
        "columns": [
            canonical_clone_v1(columns[ordinal - 1])
            for ordinal in descriptor["money_column_ordinals"]
        ],
        "continuation": "NONE",
        "rows": projected_rows,
        "title_exact": root_label,
        "unit_exact": descriptor["projected_unit_exact"],
    }
    return {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [projected_table],
                "title_exact": root_label,
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _economic_role_axis(presentation: Mapping[str, Any]) -> dict[str, tuple[int | None, ...]]:
    power = {"MILLION_VND": 6, "VND": 0}.get(presentation.get("canonical_unit"))
    if power is None:
        return {}
    return {
        item["role"]: tuple(
            None if value is None else value * (10**power) for value in item["parsed_values"]
        )
        for item in presentation["rows"]
    }


def _presentations_compatible(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    left_axis = _economic_role_axis(left)
    right_axis = _economic_role_axis(right)
    common = set(left_axis).intersection(right_axis)
    if not common:
        return False
    tolerance = (
        500_000
        if {left["canonical_unit"], right["canonical_unit"]}
        == {
            "MILLION_VND",
            "VND",
        }
        else 0
    )
    compared_lane_count = 0
    for role in common:
        left_observed = {
            ordinal for ordinal, value in enumerate(left_axis[role]) if value is not None
        }
        right_observed = {
            ordinal for ordinal, value in enumerate(right_axis[role]) if value is not None
        }
        if not (
            left_observed.issubset(right_observed)
            or right_observed.issubset(left_observed)
        ):
            return False
        for left_value, right_value in zip(left_axis[role], right_axis[role], strict=True):
            if left_value is None or right_value is None:
                continue
            compared_lane_count += 1
            if abs(left_value - right_value) > tolerance:
                return False
    return compared_lane_count > 0


def _presentation_evidence_contains(
    container: Mapping[str, Any], other: Mapping[str, Any]
) -> bool:
    """Return true only when selecting ``container`` cannot drop ``other`` evidence."""

    container_axis = _economic_role_axis(container)
    other_axis = _economic_role_axis(other)
    if not set(container_axis).issuperset(other_axis):
        return False
    for role, other_values in other_axis.items():
        container_observed = {
            ordinal
            for ordinal, value in enumerate(container_axis[role])
            if value is not None
        }
        other_observed = {
            ordinal for ordinal, value in enumerate(other_values) if value is not None
        }
        if not container_observed.issuperset(other_observed):
            return False
    return True


def _select_primary_presentation(
    page_records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> tuple[dict[str, Any] | None, list[str]]:
    if _primary_duplicate_source_role_rows(page_records):
        return None, ["DUPLICATE_PRIMARY_INCOME_TAX_SOURCE_ROLE"]
    if _primary_invalid_source_role_rows(page_records, compiled_specs=compiled_specs):
        return None, ["INVALID_PRIMARY_INCOME_TAX_SOURCE_MONEY_CELL"]
    if _primary_equation_mismatch_axis(page_records, compiled_specs=compiled_specs):
        return None, ["MISMATCHED_PRIMARY_INCOME_TAX_SOURCE_EQUATION"]
    presentations = _primary_presentations(page_records, compiled_specs=compiled_specs)
    if not presentations:
        return None, ["PRIMARY_INCOME_TAX_SOURCE_ROWS_NOT_LOCALLY_USABLE"]
    candidates = []
    for item in presentations:
        source_page = next(
            record["page_json"]
            for record in page_records
            if record["page_json_version_id"] == item["locator"]["page_json_version_id"]
        )
        projected = _project_primary_page(source_page, descriptor=item)
        specs = compiled_specs[item["projected_specs_key"]]
        record = {
            key: canonical_clone_v1(item["locator"][key])
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
        record["page_json"] = projected
        cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
            page_records=[record], compiled_specs=specs
        )
        if cluster.get("status") != READY:
            continue
        regions = cluster["component_regions"]
        candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
            regions=regions,
            page_json_by_version={item["locator"]["page_json_version_id"]: projected},
            compiled_specs=specs,
            query_receipt=(
                build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
            ),
        )
        if candidate.get("status") == READY:
            candidates.append({"cluster": cluster, "descriptor": item})
    if not candidates:
        return None, ["PRIMARY_INCOME_TAX_SOURCE_ROWS_NOT_SCHEMA_MAPPABLE"]
    # A preferred high-precision VND presentation may still omit a direct role
    # or an observed lane carried by a compatible million-VND presentation.
    # Select only from presentations whose evidence frontier contains every
    # other usable presentation; otherwise fail closed rather than silently
    # discarding source-visible evidence.
    dominant = [
        item
        for item in candidates
        if all(
            _presentation_evidence_contains(item["descriptor"], other["descriptor"])
            for other in candidates
        )
    ]
    if not dominant:
        return None, ["CONFLICTING_PRIMARY_INCOME_TAX_SOURCE_PRESENTATIONS"]
    vnd = [item for item in dominant if item["descriptor"]["canonical_unit"] == "VND"]
    pool = vnd if len(vnd) == 1 else dominant
    if len(pool) != 1:
        first = pool[0]
        if not all(
            _presentations_compatible(first["descriptor"], item["descriptor"]) for item in pool[1:]
        ):
            return None, ["CONFLICTING_PRIMARY_INCOME_TAX_SOURCE_PRESENTATIONS"]
        return None, ["MULTIPLE_EQUIVALENT_PRIMARY_INCOME_TAX_SOURCE_PRESENTATIONS"]
    selected = pool[0]
    if not all(
        _presentations_compatible(selected["descriptor"], item["descriptor"])
        for item in candidates
        if item is not selected
    ):
        return None, ["CONFLICTING_PRIMARY_INCOME_TAX_SOURCE_PRESENTATIONS"]
    descriptor = canonical_clone_v1(selected["descriptor"])
    descriptor["corroborating_presentations"] = [
        {
            "canonical_unit": item["descriptor"]["canonical_unit"],
            "locator": canonical_clone_v1(item["descriptor"]["locator"]),
            "role_economic_axis": {
                role: list(values)
                for role, values in _economic_role_axis(item["descriptor"]).items()
            },
            "selected": item is selected,
        }
        for item in candidates
    ]
    descriptor["selection_rule"] = (
        "ROLE_AND_OBSERVED_LANE_EVIDENCE_FRONTIER_DOMINANT_THEN_UNIQUE_VND_"
        "IF_PRESENT_ELSE_UNIQUE_USABLE_PRESENTATION_ALL_OTHER_USABLE_"
        "PRESENTATIONS_EXACT_OR_HALF_MILLION_DISPLAY_COMPATIBLE"
    )
    return {"cluster": selected["cluster"], "descriptor": descriptor}, []


def _primary_selection_conflict_receipt(
    page_records: Sequence[Mapping[str, Any]],
    *,
    reasons: Sequence[str],
    repair_receipts: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    material = {
        "format_version": "INCOME_TAX_PRIMARY_SELECTION_CONFLICT_RECEIPT_V1",
        "adapter_spec_sha256": compiled_specs["income_tax_adapter_spec_sha256"],
        "invalid_source_rows": _primary_invalid_source_role_rows(
            page_records, compiled_specs=compiled_specs
        ),
        "duplicate_source_roles": _primary_duplicate_source_role_rows(page_records),
        "equation_mismatches": _primary_equation_mismatch_axis(
            page_records, compiled_specs=compiled_specs
        ),
        "presentations": _primary_presentations(
            page_records, compiled_specs=compiled_specs
        ),
        "reasons": list(reasons),
        "repair_receipt_ids": [item["receipt_id"] for item in repair_receipts],
        "rule": "VALID_NOTE_CANNOT_HIDE_CONFLICTING_DIRECT_PRIMARY_PRESENTATIONS",
    }
    return {
        **material,
        "receipt_id": "gjitfav1:primary-conflict:"
        + canonical_json_sha256_v1(material),
    }


def _query_adapter_receipt(
    descriptor: Mapping[str, Any],
    *,
    repair_receipts: Sequence[Mapping[str, Any]],
    supplemental_descriptors: Sequence[Mapping[str, Any]],
    strategy: str,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    if strategy not in _QUERY_ADAPTER_STRATEGIES:
        raise _error("income-tax query adapter strategy is invalid")
    material = {
        "adapter_spec_sha256": compiled_specs["income_tax_adapter_spec_sha256"],
        "adapter_format_version": ADAPTER_FORMAT_VERSION,
        "primary_projection_receipt": canonical_clone_v1(descriptor),
        "repair_receipt_ids": [item["receipt_id"] for item in repair_receipts],
        "rule": _QUERY_ADAPTER_RULE,
        "strategy": strategy,
        "supplemental_projection_receipts": canonical_clone_v1(
            list(supplemental_descriptors)
        ),
    }
    return {
        **material,
        "receipt_id": "gjitfav1:query:" + canonical_json_sha256_v1(material),
    }


def _candidate_source_row_axis(
    candidate: Mapping[str, Any] | None,
) -> frozenset[tuple[str, str, str, int]]:
    axis = set()
    for mapping in candidate.get("mappings", []) if type(candidate) is dict else []:
        for ref in mapping.get("source_refs", []):
            locator = ref.get("locator") if type(ref) is dict else None
            key = (
                locator.get("page_json_version_id"),
                locator.get("section_id"),
                locator.get("table_id"),
                ref.get("row_ordinal"),
            ) if type(locator) is dict else None
            if (
                type(key) is tuple
                and all(type(item) is str for item in key[:3])
                and type(key[3]) is int
            ):
                axis.add(key)
    closure = candidate.get("closure_receipt") if type(candidate) is dict else None
    source_only_rows = (
        closure.get("source_only_unmapped_rows", [])
        if type(closure) is dict
        else []
    )
    for item in source_only_rows:
        source_ref = item.get("source_ref") if type(item) is dict else None
        locator = source_ref.get("locator") if type(source_ref) is dict else None
        row_ordinal = (
            source_ref.get("row_ordinal")
            if type(source_ref) is dict
            else None
        )
        key = (
            locator.get("page_json_version_id"),
            locator.get("section_id"),
            locator.get("table_id"),
            row_ordinal,
        ) if type(locator) is dict else None
        if (
            type(key) is tuple
            and all(type(value) is str for value in key[:3])
            and type(key[3]) is int
        ):
            axis.add(key)
    return frozenset(axis)


def recover_gemini_json_income_tax_query_cluster_v1(
    *,
    page_records: Any,
    base_cluster: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Preserve a valid note; otherwise select one direct primary presentation."""

    if type(page_records) not in {list, tuple} or not page_records:
        raise _error("income-tax page-record axis is invalid")
    repaired_records, repair_receipts = _apply_source_repairs(
        page_records, compiled_specs=compiled_specs
    )
    selected_base = canonical_clone_v1(base_cluster)
    if repair_receipts:
        # Source repairs are applied only to private page clones.  A row-level
        # repair can legitimately change the generic row classification, so
        # regions sealed against the unmodified selected JSON must never be
        # replayed against the repaired clone.  Re-coalesce the exact repaired
        # document and carry those freshly sealed regions through evaluation.
        selected_base = coalesce_gemini_json_multitable_hierarchical_document_v1(
            page_records=repaired_records, compiled_specs=compiled_specs
        )
    note_candidate = None
    if selected_base.get("status") == READY:
        regions = selected_base["component_regions"]
        pages = {item["page_json_version_id"]: item["page_json"] for item in repaired_records}
        candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
            regions=regions,
            page_json_by_version=pages,
            compiled_specs=compiled_specs,
            query_receipt=(
                build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
            ),
        )
        if candidate.get("status") == READY:
            note_candidate = candidate
    primary, reasons = _select_primary_presentation(repaired_records, compiled_specs=compiled_specs)
    if note_candidate is not None and primary is None:
        if any(
            reason.startswith("CONFLICTING_PRIMARY_")
            or reason.startswith("MULTIPLE_EQUIVALENT_PRIMARY_")
            or reason.startswith("INVALID_PRIMARY_")
            or reason.startswith("DUPLICATE_PRIMARY_")
            or reason.startswith("MISMATCHED_PRIMARY_")
            for reason in reasons
        ):
            owner = canonical_clone_v1(selected_base.get("owner_receipt"))
            if type(owner) is not dict:
                raise _error("income-tax valid note owner receipt is absent")
            owner["income_tax_primary_selection_conflict_receipt"] = (
                _primary_selection_conflict_receipt(
                    repaired_records,
                    reasons=reasons,
                    repair_receipts=repair_receipts,
                    compiled_specs=compiled_specs,
                )
            )
            return _reseal_cluster(
                selected_base,
                component_regions=[],
                owner_receipt=owner,
                reasons=reasons,
                status=UNRESOLVED,
            )
        return selected_base
    if primary is None:
        owner = canonical_clone_v1(selected_base.get("owner_receipt"))
        if any(
            reason.startswith("INVALID_PRIMARY_")
            or reason.startswith("DUPLICATE_PRIMARY_")
            or reason.startswith("MISMATCHED_PRIMARY_")
            for reason in reasons
        ):
            receipt = _primary_selection_conflict_receipt(
                repaired_records,
                reasons=reasons,
                repair_receipts=repair_receipts,
                compiled_specs=compiled_specs,
            )
            if type(owner) is not dict:
                evidence = [
                    *receipt["invalid_source_rows"],
                    *receipt["duplicate_source_roles"],
                    *receipt["equation_mismatches"],
                    *receipt["presentations"],
                ]
                if not evidence:
                    raise _error("income-tax primary failure evidence is absent")
                locator = evidence[0]["locator"]
                owner = {
                    "alias": "INVALID_EXACT_PRIMARY_INCOME_STATEMENT_TAX_ROWS",
                    "leading_component_positions": [],
                    "leading_component_rule": "FAMILY_LOCAL_DIRECT_SOURCE_PROJECTION",
                    "outline_top_level_number": None,
                    "position": [
                        locator["selected_page_ordinal"],
                        int(locator["section_id"][1:]),
                        int(locator["table_id"][1:]),
                    ],
                    "source_exact": None,
                }
            owner["income_tax_primary_selection_conflict_receipt"] = receipt
        return _reseal_cluster(
            selected_base,
            component_regions=[],
            **({"owner_receipt": owner} if type(owner) is dict else {}),
            reasons=reasons or canonical_clone_v1(selected_base.get("reasons", [])),
            status=UNRESOLVED,
        )
    projected_cluster = primary["cluster"]
    supplemental_issues: list[str] = []
    supplemental_descriptors = _supplemental_presentations(
        repaired_records,
        compiled_specs=compiled_specs,
        issues=supplemental_issues,
        consumed_source_rows=_candidate_source_row_axis(note_candidate),
    )
    if supplemental_issues:
        return _reseal_cluster(
            selected_base,
            component_regions=[],
            reasons=supplemental_issues,
            status=UNRESOLVED,
        )
    strategy = (
        (
            "DIRECT_NOTE_PLUS_SUPPLEMENTAL_NOTE_PLUS_PRIMARY_INCOME_STATEMENT_"
            "SOURCE_PRESENTATION"
        )
        if note_candidate is not None and supplemental_descriptors
        else (
            "DIRECT_NOTE_PLUS_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION"
            if note_candidate is not None
            else "DIRECT_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION"
        )
    )
    adapter = _query_adapter_receipt(
        primary["descriptor"],
        repair_receipts=repair_receipts,
        supplemental_descriptors=supplemental_descriptors,
        strategy=strategy,
        compiled_specs=compiled_specs,
    )
    output_cluster = selected_base if note_candidate is not None else projected_cluster
    owner = canonical_clone_v1(output_cluster.get("owner_receipt"))
    if type(owner) is not dict:
        owner = {
            "alias": "EXACT_PRIMARY_INCOME_STATEMENT_TAX_ROWS",
            "leading_component_positions": [],
            "leading_component_rule": "FAMILY_LOCAL_DIRECT_SOURCE_PROJECTION",
            "outline_top_level_number": None,
            "position": [
                primary["descriptor"]["locator"]["selected_page_ordinal"],
                int(primary["descriptor"]["locator"]["section_id"][1:]),
                int(primary["descriptor"]["locator"]["table_id"][1:]),
            ],
            "source_exact": None,
        }
    owner["income_tax_query_adapter_receipt"] = adapter
    return _reseal_cluster(
        output_cluster,
        owner_receipt=owner,
        reasons=[],
        status=READY,
    )


def adapt_gemini_json_income_tax_indexed_query_evidence_v1(
    *,
    indexed_query_evidence: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    checked = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
    cluster_by_ordinal = {
        item["document_ordinal"]: item["cluster"] for item in checked["candidate_dispositions"]
    }
    records_by_ordinal: dict[int, list[dict[str, Any]]] = {}
    for axis in checked["selected_page_axis"]:
        page = page_json_by_document.get(axis["document_ordinal"], {}).get(
            axis["page_json_version_id"]
        )
        if type(page) is not dict:
            raise _error("income-tax indexed replay page is absent")
        records_by_ordinal.setdefault(axis["document_ordinal"], []).append(
            {**canonical_clone_v1(axis), "page_json": page}
        )
    clusters = []
    for document in checked["selected_document_axis"]:
        ordinal = document["document_ordinal"]
        clusters.append(
            recover_gemini_json_income_tax_query_cluster_v1(
                page_records=records_by_ordinal[ordinal],
                base_cluster=cluster_by_ordinal[ordinal],
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
        rebuilt, compiled_specs=compiled_specs
    )


def build_gemini_json_income_tax_region_query_receipt_v1(
    regions: Any, *, cluster: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    shared = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
    adapter = None
    if cluster is not None and type(cluster.get("owner_receipt")) is dict:
        adapter = cluster["owner_receipt"].get("income_tax_query_adapter_receipt")
    material = {
        "adapter_receipt": canonical_clone_v1(adapter),
        "format_version": QUERY_RECEIPT_FORMAT_VERSION,
        "shared_query_receipt": shared,
    }
    return {
        **material,
        "query_receipt_id": "gjitfav1:query-receipt:" + canonical_json_sha256_v1(material),
    }


def _validate_query_receipt(value: Any, *, regions: Any) -> dict[str, Any]:
    expected_shared = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
    if (
        type(value) is not dict
        or set(value)
        != {
            "adapter_receipt",
            "format_version",
            "query_receipt_id",
            "shared_query_receipt",
        }
        or value.get("format_version") != QUERY_RECEIPT_FORMAT_VERSION
        or not same_typed_json_v1(value.get("shared_query_receipt"), expected_shared)
    ):
        raise _error("income-tax query receipt does not bind exact fragments")
    material = {
        key: canonical_clone_v1(item) for key, item in value.items() if key != "query_receipt_id"
    }
    if value["query_receipt_id"] != "gjitfav1:query-receipt:" + canonical_json_sha256_v1(material):
        raise _error("income-tax query receipt identity drifted")
    return canonical_clone_v1(value)


def _restore_source_refs(value: Any, *, descriptor: Mapping[str, Any]) -> Any:
    row_by_projected = {ordinal: item for ordinal, item in enumerate(descriptor["rows"], start=1)}
    locator = descriptor["locator"]

    def visit(item: Any) -> Any:
        if type(item) is list:
            return [visit(child) for child in item]
        if type(item) is not dict:
            return item
        output = {key: visit(child) for key, child in item.items()}
        source_locator = output.get("locator")
        projected_ordinal = output.get("row_ordinal")
        if (
            type(source_locator) is dict
            and source_locator.get("page_json_version_id") == locator["page_json_version_id"]
            and source_locator.get("section_id") == "s1"
            and source_locator.get("table_id") == "t1"
            and type(projected_ordinal) is int
            and projected_ordinal in row_by_projected
        ):
            source = row_by_projected[projected_ordinal]
            for key, source_value in locator.items():
                if key in output["locator"]:
                    output["locator"][key] = canonical_clone_v1(source_value)
            output["hierarchy_path_exact"] = canonical_clone_v1(source["hierarchy_path_exact"])
            output["label_exact"] = source["label_exact"]
            output["money_column_ordinals"] = canonical_clone_v1(
                descriptor["money_column_ordinals"]
            )
            output["row_id"] = f"r{source['row_ordinal']}"
            output["row_kind"] = source["row_kind"]
            output["row_ordinal"] = source["row_ordinal"]
        return output

    return visit(canonical_clone_v1(value))


def _reseal_equations(candidate: dict[str, Any]) -> None:
    equations = candidate.get("closure_receipt", {}).get("equations", [])
    replacements = {}
    for equation in equations if type(equations) is list else []:
        old = equation.get("equation_id")
        if type(old) is not str:
            continue
        material = {key: item for key, item in equation.items() if key != "equation_id"}
        new = "gjitfav1:equation:" + canonical_json_sha256_v1(material)
        equation["equation_id"] = new
        replacements[old] = new

    def replace(value: Any) -> Any:
        if type(value) is str:
            return replacements.get(value, value)
        if type(value) is list:
            return [replace(item) for item in value]
        if type(value) is dict:
            return {key: replace(item) for key, item in value.items()}
        return value

    if replacements:
        replaced = replace(candidate["closure_receipt"])
        candidate["closure_receipt"] = replaced


def _reseal_candidate(
    candidate: Mapping[str, Any],
    *,
    descriptor: Mapping[str, Any] | None,
    repair_receipts: Sequence[Mapping[str, Any]],
    strategy: str,
    compiled_specs: Mapping[str, Any],
    restore_primary_source_refs: bool = True,
    primary_candidate_proof: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    output = canonical_clone_v1(candidate)
    if descriptor is not None and restore_primary_source_refs:
        output = _restore_source_refs(output, descriptor=descriptor)
        for mapping in output.get("mappings", []):
            refs = mapping.get("source_refs")
            if type(refs) is list and len(refs) == 1:
                mapping["row_id"] = refs[0]["row_id"]
            material = {key: item for key, item in mapping.items() if key != "item_mapping_id"}
            mapping["item_mapping_id"] = "gjmthfmv1:item:" + canonical_json_sha256_v1(material)
        _reseal_equations(output)
    output["claim_boundary"] = CLAIM_BOUNDARY
    material = {
        "adapter_spec_sha256": compiled_specs["income_tax_adapter_spec_sha256"],
        "adapter_format_version": ADAPTER_FORMAT_VERSION,
        "primary_projection_receipt": canonical_clone_v1(descriptor),
        "source_repair_receipts": canonical_clone_v1(list(repair_receipts)),
        "strategy": strategy,
    }
    if primary_candidate_proof is not None:
        material["primary_candidate_proof"] = canonical_clone_v1(primary_candidate_proof)
    output["closure_receipt"]["income_tax_adapter_receipt"] = {
        **material,
        "receipt_id": "gjitfav1:candidate:" + canonical_json_sha256_v1(material),
    }
    candidate_material = {key: item for key, item in output.items() if key != "candidate_id"}
    output["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(candidate_material)
    return output


def _evaluate_selected_primary(
    selected: Mapping[str, Any],
    *,
    repaired_pages: Mapping[str, dict[str, Any]],
    repair_receipts: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    descriptor = selected["descriptor"]
    locator = descriptor["locator"]
    source_page = repaired_pages[locator["page_json_version_id"]]
    projected_page = _project_primary_page(source_page, descriptor=descriptor)
    if canonical_json_sha256_v1(projected_page) != descriptor["projected_page_json_sha256"]:
        raise _error("income-tax primary projection output drifted")
    specs = compiled_specs[descriptor["projected_specs_key"]]
    regions = selected["cluster"]["component_regions"]
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=regions,
        page_json_by_version={locator["page_json_version_id"]: projected_page},
        compiled_specs=specs,
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions),
    )
    return _reseal_candidate(
        candidate,
        descriptor=descriptor,
        repair_receipts=repair_receipts,
        strategy="DIRECT_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION",
        compiled_specs=compiled_specs,
    )


def _evaluate_supplemental_descriptor(
    descriptor: Mapping[str, Any],
    *,
    repaired_pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    locator = descriptor["locator"]
    source_page = repaired_pages[locator["page_json_version_id"]]
    projected_page = _project_primary_page(source_page, descriptor=descriptor)
    if canonical_json_sha256_v1(projected_page) != descriptor["projected_page_json_sha256"]:
        raise _error("income-tax supplemental projection output drifted")
    specs = compiled_specs["income_tax_supplemental_specs"]
    projected_record = {
        key: canonical_clone_v1(locator[key])
        for key in (
            "document_id",
            "document_ordinal",
            "page_json_version_id",
            "physical_page",
            "selected_page_ordinal",
            "source_logical_name",
            "source_sha256",
        )
    } | {"page_json": projected_page}
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[projected_record], compiled_specs=specs
    )
    if cluster.get("status") != READY or not same_typed_json_v1(
        cluster.get("component_regions"), descriptor["projected_component_regions"]
    ):
        raise _error("income-tax supplemental projection query replay drifted")
    regions = cluster["component_regions"]
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=regions,
        page_json_by_version={locator["page_json_version_id"]: projected_page},
        compiled_specs=specs,
        query_receipt=(
            build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
        ),
    )
    if candidate.get("status") != READY:
        raise _error("income-tax supplemental projection candidate replay drifted")
    candidate = _restore_source_refs(candidate, descriptor=descriptor)
    for mapping in candidate.get("mappings", []):
        refs = mapping.get("source_refs")
        if type(refs) is list and len(refs) == 1:
            mapping["row_id"] = refs[0]["row_id"]
        material = {key: item for key, item in mapping.items() if key != "item_mapping_id"}
        mapping["item_mapping_id"] = "gjmthfmv1:item:" + canonical_json_sha256_v1(material)
    _reseal_equations(candidate)
    material = {key: item for key, item in candidate.items() if key != "candidate_id"}
    candidate["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(material)
    return candidate


def _mapping_economic_values(mapping: Mapping[str, Any]) -> tuple[int | None, ...] | None:
    power = {"MILLION_VND": 6, "VND": 0}.get(mapping.get("unit"))
    values = mapping.get("values")
    if power is None or type(values) is not list:
        return None
    output = []
    for item in values:
        coefficient = item.get("coefficient") if type(item) is dict else None
        if coefficient is not None and type(coefficient) is not int:
            return None
        output.append(None if coefficient is None else coefficient * (10**power))
    return tuple(output)


def _supplemental_mappings_compatible(
    left: Mapping[str, Any], right: Mapping[str, Any]
) -> bool:
    return _cross_source_mappings_compatible(left, right, allow_sign_inversion=False)


def _cross_source_mappings_compatible(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    *,
    allow_sign_inversion: bool,
) -> bool:
    return bool(
        _cross_source_mapping_signs(
            left, right, allow_sign_inversion=allow_sign_inversion
        )
    )


def _cross_source_mapping_signs(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    *,
    allow_sign_inversion: bool,
) -> frozenset[int]:
    left_values = _mapping_economic_values(left)
    right_values = _mapping_economic_values(right)
    if left_values is None or right_values is None or len(left_values) != len(right_values):
        return frozenset()
    tolerance = (
        500_000
        if {left.get("unit"), right.get("unit")} == {"MILLION_VND", "VND"}
        else 0
    )
    paired = [
        (left_value, right_value)
        for left_value, right_value in zip(left_values, right_values, strict=True)
        if left_value is not None and right_value is not None
    ]
    if not paired:
        return frozenset()
    signs = (1, -1) if allow_sign_inversion else (1,)
    return frozenset(
        sign
        for sign in signs
        if all(
            abs(left_value - sign * right_value) <= tolerance
            for left_value, right_value in paired
        )
    )


def _observed_mapping_lane_axis(mapping: Mapping[str, Any]) -> frozenset[int]:
    values = mapping.get("values")
    if type(values) is not list:
        return frozenset()
    return frozenset(
        ordinal
        for ordinal, item in enumerate(values)
        if type(item) is dict and item.get("coefficient") is not None
    )


def _cross_source_orientation(
    pairs: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]]
) -> int | None:
    allowed = {1, -1}
    for left, right in pairs:
        left_lanes = _observed_mapping_lane_axis(left)
        right_lanes = _observed_mapping_lane_axis(right)
        if not (left_lanes.issubset(right_lanes) or right_lanes.issubset(left_lanes)):
            return None
        allowed.intersection_update(
            _cross_source_mapping_signs(left, right, allow_sign_inversion=True)
        )
        if not allowed:
            return None
    if 1 in allowed:
        return 1
    return -1 if -1 in allowed else None


def _mapping_is_direct_source_observation(mapping: Mapping[str, Any]) -> bool:
    state = mapping.get("state")
    values = mapping.get("values")
    return bool(
        type(state) is str
        and "SOURCE_VISIBLE" in state
        and not state.startswith("DERIVED_")
        and type(values) is list
        and any(type(item) is dict and item.get("source_text") is not None for item in values)
    )


def _unresolved_from_candidate(
    candidate: Mapping[str, Any],
    *,
    reason: str,
    evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    output = canonical_clone_v1(candidate)
    output["mappings"] = []
    output["reasons"] = [reason]
    output["status"] = UNRESOLVED
    if evidence is not None:
        evidence_material = {
            "evidence": canonical_clone_v1(evidence),
            "reason": reason,
        }
        output["closure_receipt"]["income_tax_unresolved_evidence_receipt"] = {
            **evidence_material,
            "receipt_id": "gjitfav1:unresolved:"
            + canonical_json_sha256_v1(evidence_material),
        }
    material = {key: item for key, item in output.items() if key != "candidate_id"}
    output["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(material)
    return output


def _supplemental_merge_evidence(
    supplemental: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]],
    primary_candidate: Mapping[str, Any],
    *,
    descriptor: Mapping[str, Any],
    repair_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "primary_candidate_id": primary_candidate["candidate_id"],
        "primary_closure_receipt": canonical_clone_v1(primary_candidate["closure_receipt"]),
        "primary_projection_receipt": canonical_clone_v1(descriptor),
        "source_repair_receipts": canonical_clone_v1(list(repair_receipts)),
        "supplemental_candidates": [
            {
                "candidate_id": candidate["candidate_id"],
                "closure_receipt": canonical_clone_v1(candidate["closure_receipt"]),
                "descriptor": canonical_clone_v1(supplement_descriptor),
                "mappings": canonical_clone_v1(candidate["mappings"]),
            }
            for supplement_descriptor, candidate in supplemental
        ],
    }


def _merge_supplemental_and_primary_candidates(
    supplemental: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]],
    primary_candidate: Mapping[str, Any],
    *,
    descriptor: Mapping[str, Any],
    repair_receipts: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    supplemental_by_role: dict[str, tuple[dict[str, Any], Mapping[str, Any]]] = {}
    suppressed_supplemental = []
    for supplement_descriptor, candidate in supplemental:
        if candidate.get("status") != READY:
            raise _error("income-tax supplemental source candidate is not ready")
        for mapping in candidate["mappings"]:
            role = mapping["role"]
            existing = supplemental_by_role.get(role)
            if existing is None:
                supplemental_by_role[role] = (
                    canonical_clone_v1(mapping),
                    supplement_descriptor,
                )
                continue
            if not _supplemental_mappings_compatible(existing[0], mapping):
                return _unresolved_from_candidate(
                    primary_candidate,
                    reason="CONFLICTING_DIRECT_SUPPLEMENTAL_INCOME_TAX_PRESENTATIONS",
                    evidence=_supplemental_merge_evidence(
                        supplemental,
                        primary_candidate,
                        descriptor=descriptor,
                        repair_receipts=repair_receipts,
                    ),
                )
            existing_lanes = _observed_mapping_lane_axis(existing[0])
            incoming_lanes = _observed_mapping_lane_axis(mapping)
            if not (
                existing_lanes.issubset(incoming_lanes)
                or incoming_lanes.issubset(existing_lanes)
            ):
                return _unresolved_from_candidate(
                    primary_candidate,
                    reason="INCOMPARABLE_PARTIAL_DIRECT_SUPPLEMENTAL_PRESENTATIONS",
                    evidence=_supplemental_merge_evidence(
                        supplemental,
                        primary_candidate,
                        descriptor=descriptor,
                        repair_receipts=repair_receipts,
                    ),
                )
            if incoming_lanes > existing_lanes:
                suppressed_supplemental.append(existing[0])
                supplemental_by_role[role] = (
                    canonical_clone_v1(mapping),
                    supplement_descriptor,
                )
            else:
                suppressed_supplemental.append(canonical_clone_v1(mapping))

    primary_by_role = {item["role"]: item for item in primary_candidate["mappings"]}
    if len(primary_by_role) != len(primary_candidate["mappings"]):
        raise _error("income-tax primary source role axis is duplicate")
    overlap_pairs = [
        (item[0], primary_by_role[role])
        for role, item in supplemental_by_role.items()
        if role in primary_by_role
    ]
    cross_source_orientation = _cross_source_orientation(overlap_pairs)
    if overlap_pairs and cross_source_orientation is None:
        return _unresolved_from_candidate(
            primary_candidate,
            reason="CONFLICTING_DIRECT_SUPPLEMENTAL_AND_PRIMARY_INCOME_TAX_PRESENTATIONS",
            evidence=_supplemental_merge_evidence(
                supplemental,
                primary_candidate,
                descriptor=descriptor,
                repair_receipts=repair_receipts,
            ),
        )
    suppress_entire_supplemental_axis = cross_source_orientation == -1
    merged_by_role = (
        {}
        if suppress_entire_supplemental_axis
        else {
            role: canonical_clone_v1(item[0])
            for role, item in supplemental_by_role.items()
        }
    )
    suppressed_primary = []
    suppressed_cross_source_supplemental = (
        [canonical_clone_v1(item[0]) for item in supplemental_by_role.values()]
        if suppress_entire_supplemental_axis
        else []
    )
    for role, mapping in primary_by_role.items():
        if role == "FAMILY_ROOT_TOTAL" or role not in merged_by_role:
            merged_by_role[role] = canonical_clone_v1(mapping)
        else:
            supplemental_lanes = _observed_mapping_lane_axis(merged_by_role[role])
            primary_lanes = _observed_mapping_lane_axis(mapping)
            if primary_lanes > supplemental_lanes:
                suppressed_cross_source_supplemental.append(
                    canonical_clone_v1(merged_by_role[role])
                )
                merged_by_role[role] = canonical_clone_v1(mapping)
            else:
                suppressed_primary.append(canonical_clone_v1(mapping))
    role_order = [item["role"] for item in compiled_specs["topology"]["children"]]
    role_order.append("FAMILY_ROOT_TOTAL")
    order = {role: ordinal for ordinal, role in enumerate(role_order)}
    merged = canonical_clone_v1(primary_candidate)
    merged["mappings"] = sorted(
        merged_by_role.values(),
        key=lambda item: (order.get(item["role"], len(order)), item["role"]),
    )
    supplemental_equations = []
    if not suppress_entire_supplemental_axis:
        for _supplement_descriptor, candidate in supplemental:
            supplemental_equations.extend(
                canonical_clone_v1(candidate.get("closure_receipt", {}).get("equations", []))
            )
    merged["closure_receipt"]["equations"] = [
        *canonical_clone_v1(merged["closure_receipt"].get("equations", [])),
        *supplemental_equations,
    ]
    proof = {
        "primary_candidate_id": primary_candidate["candidate_id"],
        "primary_closure_receipt": canonical_clone_v1(primary_candidate["closure_receipt"]),
        "rule": (
            "SUPPLEMENTAL_DIRECT_NOTE_ROLES_PRESERVED_PRIMARY_DIRECT_ROOT_AND_ONLY_"
            "SUPPLEMENT_ABSENT_ROLES_ADDED_EQUIVALENT_DUPLICATES_RETAINED_AS_CONTROLS"
        ),
        "supplemental_candidates": [
            {
                "candidate_id": candidate["candidate_id"],
                "closure_receipt": canonical_clone_v1(candidate["closure_receipt"]),
                "descriptor_id": supplement_descriptor["descriptor_id"],
            }
            for supplement_descriptor, candidate in supplemental
        ],
        "supplemental_projection_receipts": canonical_clone_v1(
            [item[0] for item in supplemental]
        ),
        "cross_source_sign_orientation": cross_source_orientation or 1,
        "suppressed_cross_source_supplemental_mappings": (
            suppressed_cross_source_supplemental
        ),
        "suppressed_duplicate_primary_mappings": suppressed_primary,
        "suppressed_equivalent_supplemental_mappings": suppressed_supplemental,
    }
    return _reseal_candidate(
        merged,
        descriptor=descriptor,
        repair_receipts=repair_receipts,
        strategy="DIRECT_SUPPLEMENTAL_NOTE_PLUS_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION",
        compiled_specs=compiled_specs,
        restore_primary_source_refs=False,
        primary_candidate_proof=proof,
    )


def _merge_note_and_primary_candidates(
    note_candidate: Mapping[str, Any],
    primary_candidate: Mapping[str, Any],
    *,
    descriptor: Mapping[str, Any],
    repair_receipts: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    strategy: str,
) -> dict[str, Any]:
    if note_candidate.get("status") != READY or primary_candidate.get("status") != READY:
        raise _error("income-tax independent source candidate is not ready")
    note_by_role = {item["role"]: item for item in note_candidate["mappings"]}
    primary_by_role = {item["role"]: item for item in primary_candidate["mappings"]}
    if len(note_by_role) != len(note_candidate["mappings"]) or len(primary_by_role) != len(
        primary_candidate["mappings"]
    ):
        raise _error("income-tax independent source role axis is duplicate")
    conflict_evidence = {
        "note_candidate_id": note_candidate["candidate_id"],
        "note_closure_receipt": canonical_clone_v1(note_candidate["closure_receipt"]),
        "note_mappings": canonical_clone_v1(note_candidate["mappings"]),
        "primary_candidate_id": primary_candidate["candidate_id"],
        "primary_closure_receipt": canonical_clone_v1(primary_candidate["closure_receipt"]),
        "primary_mappings": canonical_clone_v1(primary_candidate["mappings"]),
        "primary_projection_receipt": canonical_clone_v1(descriptor),
        "source_repair_receipts": canonical_clone_v1(list(repair_receipts)),
    }
    overlap_pairs = []
    for role, note_mapping in note_by_role.items():
        primary_mapping = primary_by_role.get(role)
        if primary_mapping is None:
            continue
        if role != "FAMILY_ROOT_TOTAL" or _mapping_is_direct_source_observation(
            note_mapping
        ):
            overlap_pairs.append((note_mapping, primary_mapping))
    cross_source_orientation = _cross_source_orientation(overlap_pairs)
    if overlap_pairs and cross_source_orientation is None:
        return _unresolved_from_candidate(
            primary_candidate,
            reason="CONFLICTING_DIRECT_NOTE_AND_PRIMARY_INCOME_TAX_PRESENTATIONS",
            evidence=conflict_evidence,
        )
    if cross_source_orientation == -1:
        return _unresolved_from_candidate(
            primary_candidate,
            reason="SIGN_INVERTED_DIRECT_NOTE_AND_PRIMARY_INCOME_TAX_PRESENTATIONS",
            evidence=conflict_evidence,
        )
    merged_by_role = canonical_clone_v1(note_by_role)
    suppressed_primary = []
    suppressed_note_roots = []
    suppressed_cross_source_note = []
    for role, mapping in primary_by_role.items():
        if role == "FAMILY_ROOT_TOTAL":
            note_root = merged_by_role.get(role)
            if note_root is None:
                merged_by_role[role] = canonical_clone_v1(mapping)
            elif not _mapping_is_direct_source_observation(note_root):
                suppressed_note_roots.append(canonical_clone_v1(note_root))
                merged_by_role[role] = canonical_clone_v1(mapping)
            else:
                note_lanes = _observed_mapping_lane_axis(note_root)
                primary_lanes = _observed_mapping_lane_axis(mapping)
                if primary_lanes > note_lanes:
                    suppressed_note_roots.append(canonical_clone_v1(note_root))
                    merged_by_role[role] = canonical_clone_v1(mapping)
                else:
                    suppressed_primary.append(canonical_clone_v1(mapping))
        elif role not in merged_by_role:
            merged_by_role[role] = canonical_clone_v1(mapping)
        else:
            note_lanes = _observed_mapping_lane_axis(merged_by_role[role])
            primary_lanes = _observed_mapping_lane_axis(mapping)
            if primary_lanes > note_lanes:
                suppressed_cross_source_note.append(
                    canonical_clone_v1(merged_by_role[role])
                )
                merged_by_role[role] = canonical_clone_v1(mapping)
            else:
                suppressed_primary.append(canonical_clone_v1(mapping))
    role_order = [item["role"] for item in compiled_specs["topology"]["children"]]
    role_order.append("FAMILY_ROOT_TOTAL")
    order = {role: ordinal for ordinal, role in enumerate(role_order)}
    merged = canonical_clone_v1(note_candidate)
    merged["mappings"] = sorted(
        merged_by_role.values(),
        key=lambda item: (order.get(item["role"], len(order)), item["role"]),
    )
    proof = {
        "primary_candidate_id": primary_candidate["candidate_id"],
        "primary_closure_receipt": canonical_clone_v1(primary_candidate["closure_receipt"]),
        "rule": (
            "NOTE_DIRECT_ROLES_PRESERVED_PRIMARY_DIRECT_ROOT_AND_ONLY_NOTE_ABSENT_"
            "ROLES_ADDED_DUPLICATE_PRIMARY_ROLES_RETAINED_AS_SOURCE_CONTROL"
        ),
        "cross_source_sign_orientation": cross_source_orientation or 1,
        "suppressed_cross_source_note_mappings": suppressed_cross_source_note,
        "suppressed_note_root_mappings": suppressed_note_roots,
        "suppressed_duplicate_primary_mappings": suppressed_primary,
    }
    return _reseal_candidate(
        merged,
        descriptor=descriptor,
        repair_receipts=repair_receipts,
        strategy=strategy,
        compiled_specs=compiled_specs,
        restore_primary_source_refs=False,
        primary_candidate_proof=proof,
    )


def evaluate_gemini_json_income_tax_family_cluster_v1(
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    selected_page_axis: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    checked = _validate_query_receipt(query_receipt, regions=regions)
    source_axis = {
        (item.get("document_id"), item.get("document_ordinal"), item.get("source_sha256"))
        for item in regions
    }
    if len(source_axis) != 1:
        raise _error("income-tax region document axis is invalid")
    document_id, document_ordinal, source_sha256 = next(iter(source_axis))
    page_records = []
    seen_versions = set()
    for axis in selected_page_axis:
        if (
            type(axis) is not dict
            or axis.get("document_id") != document_id
            or axis.get("document_ordinal") != document_ordinal
            or axis.get("source_sha256") != source_sha256
        ):
            continue
        page_version_id = axis.get("page_json_version_id")
        page = page_json_by_version.get(page_version_id)
        if type(page_version_id) is not str or type(page) is not dict:
            raise _error("income-tax selected page image is absent")
        if page_version_id in seen_versions:
            raise _error("income-tax selected page axis is duplicate")
        seen_versions.add(page_version_id)
        page_records.append({**canonical_clone_v1(axis), "page_json": page})
    if not page_records or set(page_json_by_version) != seen_versions:
        raise _error("income-tax selected page axis does not bind supplied pages")
    repaired_records, repair_receipts = _apply_source_repairs(
        page_records, compiled_specs=compiled_specs
    )
    repaired_pages = {item["page_json_version_id"]: item["page_json"] for item in repaired_records}
    adapter = checked["adapter_receipt"]
    if adapter is None:
        selected_primary, primary_reasons = _select_primary_presentation(
            repaired_records, compiled_specs=compiled_specs
        )
        if selected_primary is not None or any(
            reason.startswith("CONFLICTING_PRIMARY_")
            or reason.startswith("MULTIPLE_EQUIVALENT_PRIMARY_")
            or reason.startswith("INVALID_PRIMARY_")
            or reason.startswith("DUPLICATE_PRIMARY_")
            or reason.startswith("MISMATCHED_PRIMARY_")
            for reason in primary_reasons
        ):
            raise _error("income-tax adapter receipt is absent for usable primary source")
        candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
            regions=checked["shared_query_receipt"]["region_axis"],
            page_json_by_version=repaired_pages,
            compiled_specs=compiled_specs,
            query_receipt=checked["shared_query_receipt"],
        )
        supplemental_issues: list[str] = []
        supplemental_descriptors = _supplemental_presentations(
            repaired_records,
            compiled_specs=compiled_specs,
            issues=supplemental_issues,
            consumed_source_rows=_candidate_source_row_axis(candidate),
        )
        if supplemental_issues or supplemental_descriptors:
            raise _error("income-tax adapter receipt is absent for supplemental source")
        return _reseal_candidate(
            candidate,
            descriptor=None,
            repair_receipts=repair_receipts,
            strategy="DIRECT_NOTE_SOURCE_PRESENTATION",
            compiled_specs=compiled_specs,
        )
    if (
        type(adapter) is not dict
        or set(adapter)
        != {
            "adapter_spec_sha256",
            "adapter_format_version",
            "primary_projection_receipt",
            "receipt_id",
            "repair_receipt_ids",
            "rule",
            "strategy",
            "supplemental_projection_receipts",
        }
        or adapter.get("adapter_spec_sha256")
        != compiled_specs["income_tax_adapter_spec_sha256"]
        or adapter.get("adapter_format_version") != ADAPTER_FORMAT_VERSION
        or adapter.get("rule") != _QUERY_ADAPTER_RULE
        or adapter.get("strategy") not in _QUERY_ADAPTER_STRATEGIES
        or type(adapter.get("primary_projection_receipt")) is not dict
        or type(adapter.get("supplemental_projection_receipts")) is not list
        or adapter.get("repair_receipt_ids")
        != [item["receipt_id"] for item in repair_receipts]
    ):
        raise _error("income-tax adapter query receipt schema drifted")
    material = {
        key: canonical_clone_v1(item) for key, item in adapter.items() if key != "receipt_id"
    }
    if adapter.get("receipt_id") != "gjitfav1:query:" + canonical_json_sha256_v1(material):
        raise _error("income-tax adapter query receipt drifted")
    selected, reasons = _select_primary_presentation(
        repaired_records, compiled_specs=compiled_specs
    )
    descriptor = adapter["primary_projection_receipt"]
    if selected is None or reasons or not same_typed_json_v1(selected["descriptor"], descriptor):
        raise _error("income-tax primary projection query replay drifted")
    primary_candidate = _evaluate_selected_primary(
        selected,
        repaired_pages=repaired_pages,
        repair_receipts=repair_receipts,
        compiled_specs=compiled_specs,
    )
    strategy = adapter.get("strategy")
    if strategy == "DIRECT_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION":
        if not same_typed_json_v1(
            selected["cluster"]["component_regions"],
            checked["shared_query_receipt"]["region_axis"],
        ):
            raise _error("income-tax primary query region replay drifted")
        supplemental_issues: list[str] = []
        supplemental_descriptors = _supplemental_presentations(
            repaired_records,
            compiled_specs=compiled_specs,
            issues=supplemental_issues,
        )
        if supplemental_issues:
            raise _error("income-tax supplemental projection issue axis drifted")
        if not same_typed_json_v1(
            supplemental_descriptors,
            adapter.get("supplemental_projection_receipts"),
        ):
            raise _error("income-tax supplemental projection query replay drifted")
        if supplemental_descriptors:
            supplemental_candidates = [
                (
                    item,
                    _evaluate_supplemental_descriptor(
                        item,
                        repaired_pages=repaired_pages,
                        compiled_specs=compiled_specs,
                    ),
                )
                for item in supplemental_descriptors
            ]
            return _merge_supplemental_and_primary_candidates(
                supplemental_candidates,
                primary_candidate,
                descriptor=descriptor,
                repair_receipts=repair_receipts,
                compiled_specs=compiled_specs,
            )
        return primary_candidate
    note_strategies = {
        "DIRECT_NOTE_PLUS_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION",
        (
            "DIRECT_NOTE_PLUS_SUPPLEMENTAL_NOTE_PLUS_PRIMARY_INCOME_STATEMENT_"
            "SOURCE_PRESENTATION"
        ),
    }
    if strategy not in note_strategies:
        raise _error("income-tax adapter evaluation strategy drifted")
    note_candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=checked["shared_query_receipt"]["region_axis"],
        page_json_by_version=repaired_pages,
        compiled_specs=compiled_specs,
        query_receipt=checked["shared_query_receipt"],
    )
    supplemental_issues = []
    supplemental_descriptors = _supplemental_presentations(
        repaired_records,
        compiled_specs=compiled_specs,
        issues=supplemental_issues,
        consumed_source_rows=_candidate_source_row_axis(note_candidate),
    )
    if supplemental_issues:
        raise _error("income-tax supplemental projection issue axis drifted")
    if not same_typed_json_v1(
        supplemental_descriptors, adapter.get("supplemental_projection_receipts")
    ):
        raise _error("income-tax supplemental projection query replay drifted")
    if strategy == "DIRECT_NOTE_PLUS_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION":
        if supplemental_descriptors:
            raise _error("income-tax direct-note strategy omits supplemental projections")
        merged_primary = primary_candidate
    else:
        if not supplemental_descriptors:
            raise _error("income-tax triple-source strategy lacks supplemental projection")
        supplemental_candidates = [
            (
                item,
                _evaluate_supplemental_descriptor(
                    item,
                    repaired_pages=repaired_pages,
                    compiled_specs=compiled_specs,
                ),
            )
            for item in supplemental_descriptors
        ]
        merged_primary = _merge_supplemental_and_primary_candidates(
            supplemental_candidates,
            primary_candidate,
            descriptor=descriptor,
            repair_receipts=repair_receipts,
            compiled_specs=compiled_specs,
        )
        if merged_primary.get("status") != READY:
            return merged_primary
    return _merge_note_and_primary_candidates(
        note_candidate,
        merged_primary,
        descriptor=descriptor,
        repair_receipts=repair_receipts,
        compiled_specs=compiled_specs,
        strategy=strategy,
    )


def build_gemini_json_income_tax_trials_v1(
    *,
    indexed_query_evidence: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    evidence = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
    page_axis_by_document: dict[int, list[dict[str, Any]]] = {}
    for item in evidence["selected_page_axis"]:
        page_axis_by_document.setdefault(item["document_ordinal"], []).append(item)
    trials = []
    for disposition in evidence["candidate_dispositions"]:
        cluster = disposition["cluster"]
        ordinal = disposition["document_ordinal"]
        candidates = []
        mappings = []
        reasons = []
        selected_candidate_id = None
        status = disposition["disposition"]
        if status == READY:
            regions = cluster["component_regions"]
            candidate = evaluate_gemini_json_income_tax_family_cluster_v1(
                regions=regions,
                page_json_by_version=page_json_by_document[ordinal],
                selected_page_axis=page_axis_by_document[ordinal],
                compiled_specs=compiled_specs,
                query_receipt=build_gemini_json_income_tax_region_query_receipt_v1(
                    regions, cluster=cluster
                ),
            )
            candidates = [candidate]
            status = candidate["status"]
            if status == READY:
                mappings = candidate["mappings"]
                selected_candidate_id = candidate["candidate_id"]
            else:
                reasons = candidate["reasons"]
        elif status == UNRESOLVED:
            reasons = cluster["reasons"]
        elif status != NOT_OBSERVED:
            raise _error("income-tax query disposition is invalid")
        trials.append(
            {
                "candidate_count": len(candidates),
                "candidates": candidates,
                "document_ordinal": ordinal,
                "mappings": mappings,
                "reasons": reasons,
                "selected_candidate_id": selected_candidate_id,
                "source_logical_name": disposition["source_logical_name"],
                "source_sha256": disposition["source_sha256"],
                "status": status,
            }
        )
    return validate_gemini_json_multitable_hierarchical_sweep_query_bindings_v1(
        trials=trials,
        indexed_query_evidence=evidence,
        compiled_specs=compiled_specs,
    )


def validate_gemini_json_income_tax_replay_v1(
    *,
    base_indexed_query_evidence: Any,
    indexed_query_evidence: Any,
    trials: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    expected_indexed = adapt_gemini_json_income_tax_indexed_query_evidence_v1(
        indexed_query_evidence=base_indexed_query_evidence,
        page_json_by_document=page_json_by_document,
        compiled_specs=compiled_specs,
    )
    if not same_typed_json_v1(expected_indexed, indexed_query_evidence):
        raise _error("income-tax indexed query replay drifted")
    expected_trials = build_gemini_json_income_tax_trials_v1(
        indexed_query_evidence=expected_indexed,
        page_json_by_document=page_json_by_document,
        compiled_specs=compiled_specs,
    )
    if type(trials) is not list or not same_typed_json_v1(expected_trials, trials):
        raise _error("income-tax trial replay drifted")
    return expected_trials
