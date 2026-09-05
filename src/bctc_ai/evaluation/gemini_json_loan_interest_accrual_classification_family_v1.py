"""Family 26 adapter and cross-family ownership gate.

The shared multi-table evaluator owns source discovery, period/unit handling,
and accounting closure.  This module narrows that engine to the source-visible
interest/fee-receivable subtree under ``Tài sản Có khác`` and binds only report
normalization IDs 982--986.

Family 22 historically owned those same roles.  A Family-26 release therefore
requires an authenticated Family-22 sweep for the identical corpus and fails
closed until that sweep contains none of the five IDs.  The receipt also
compares exact source/page/table/row/report-ID axes, so a future alias or role
rename cannot silently reintroduce double ownership.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.evaluation.gemini_json_customer_deposit_family_v1 import _money
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    compile_gemini_json_flat_family_specs_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    _classification_roles,
    build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    classify_gemini_json_multitable_hierarchical_table_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
    validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    validate_gemini_json_multitable_hierarchical_sweep_query_bindings_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FAMILY_ID = "LOAN_INTEREST_ACCRUAL_CLASSIFICATION"
LEGACY_OWNER_FAMILY_ID = "OTHER_ASSETS"
ADAPTER_FORMAT_VERSION = (
    "GEMINI_JSON_LOAN_INTEREST_ACCRUAL_CLASSIFICATION_FAMILY_ADAPTER_V1"
)
CROSS_FAMILY_RECEIPT_FORMAT_VERSION = (
    "LOAN_INTEREST_ACCRUAL_CLASSIFICATION_CROSS_FAMILY_DISJOINTNESS_RECEIPT_V1"
)
SOURCE_ROW_COVERAGE_FORMAT_VERSION = (
    "LOAN_INTEREST_ACCRUAL_CLASSIFICATION_SOURCE_ROW_COVERAGE_V1"
)
OWNED_ROLE_BINDINGS = {
    "CREDIT_INTEREST": 983,
    "DEPOSIT_INTEREST": 984,
    "DERIVATIVE_INTEREST": 985,
    "INTEREST_FEE_RECEIVABLES": 982,
    "OTHER_INTEREST": 986,
}
OWNED_REPORT_NORM_IDS = frozenset(OWNED_ROLE_BINDINGS.values())

_FAMILY26_AGGREGATE_ALIASES = (
    "cac khoan lai phi phai thu",
    "cac khoan lai va phi phai thu",
    "lai va phi phai thu",
)
_OFF_BALANCE_CONTEXT_MARKERS = (
    "chi tieu ngoai bao cao tinh hinh tai chinh",
    "chi tieu ngoai bang can doi ke toan",
    "chi tieu ngoai bang bao cao tinh hinh tai chinh",
)
_RELATED_PARTY_CONTEXT_MARKERS = (
    "ben lien quan",
    "cac ben co lien quan",
    "cac ca nhan lien quan",
    "cac cong ty lien quan",
    "cac cong ty va ca nhan lien quan",
    "giao dich cho vay khach hang",
    "giao dich trai phieu",
    "hoi dong quan tri",
    "ban tong giam doc",
    "ban dieu hanh",
    "ban kiem soat",
)
_GENERAL_RECEIVABLES_CONTEXT_MARKERS = (
    "cac khoan phai thu",
    "phai thu ben ngoai",
    "tai san co khac",
)
_EXPENSE_OR_REVERSAL_MARKERS = (
    "chi phi du phong",
    "hoan nhap du phong",
    "thoai lai du thu",
)
_CREDIT_RISK_CONTEXT_MARKERS = (
    "rui ro tin dung",
    "tai san va no phai tra tai chinh",
    "tai san tai chinh",
    "phan loai no",
)

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_PAGE_VERSION = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_SECTION_ID = re.compile(r"s[1-9][0-9]*\Z")
_TABLE_ID = re.compile(r"t[1-9][0-9]*\Z")


class GeminiJsonLoanInterestAccrualClassificationFamilyV1Error(ValueError):
    """Family-26 specs, evidence, replay, or ownership handoff drifted."""


def _error(
    message: str,
) -> GeminiJsonLoanInterestAccrualClassificationFamilyV1Error:
    return GeminiJsonLoanInterestAccrualClassificationFamilyV1Error(message)


def compile_gemini_json_loan_interest_accrual_classification_family_specs_v1(
    topology_spec: Any,
    evaluation_spec: Any,
    schema_binding_spec: Any,
) -> dict[str, Any]:
    """Compile and narrow one immutable Family-26 declarative triplet."""

    compiled = compile_gemini_json_flat_family_specs_v1(
        topology_spec, evaluation_spec, schema_binding_spec
    )
    if (
        compiled.get("topology", {}).get("family_id") != FAMILY_ID
        or compiled.get("evaluation", {}).get("family_id") != FAMILY_ID
        or compiled.get("schema", {}).get("family_id") != FAMILY_ID
        or compiled.get("schema", {}).get("family_root_report_norm_id") != 966
        or compiled.get("schema", {}).get("root_mapping_policy")
        != "STRUCTURAL_CONTEXT_ONLY"
        or compiled.get("bindings") != OWNED_ROLE_BINDINGS
        or compiled.get("root_component_roles") != ["INTEREST_FEE_RECEIVABLES"]
        or compiled.get("context_total_mapping_roles")
        != ["INTEREST_FEE_RECEIVABLES"]
        or compiled.get("table_context_roles") != ["INTEREST_FEE_RECEIVABLES"]
        or compiled.get("evaluation", {}).get("derived_role_equations")
        or compiled.get("evaluation", {}).get("corroboration_pairs")
    ):
        raise _error("Family-26 declarative ownership frontier is invalid")
    compiled["loan_interest_accrual_classification_adapter_format_version"] = (
        ADAPTER_FORMAT_VERSION
    )
    return compiled


def _source_table(
    page_json: Mapping[str, Any], *, section_id: str, table_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        section = page_json["sections"][int(section_id[1:]) - 1]
        table = section["tables"][int(table_id[1:]) - 1]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise _error("Family-26 source locator does not resolve one table") from exc
    if type(section) is not dict or type(table) is not dict:
        raise _error("Family-26 source table is invalid")
    return section, table


def _explicit_unit(
    table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> tuple[str, int] | None:
    source = normalize_vietnamese_anchor_v1(table.get("unit_exact") or "")
    matches = []
    for binding in compiled_specs.get("unit_bindings", []):
        if binding.get("accepted") is not True:
            continue
        for alias in binding["aliases"]:
            if alias == source or alias in source:
                matches.append(
                    (
                        len(alias),
                        binding["canonical_unit"],
                        binding["magnitude_power10"],
                    )
                )
    if not matches:
        return None
    longest = max(item[0] for item in matches)
    units = sorted({item[1:] for item in matches if item[0] == longest})
    return units[0] if len(units) == 1 else None


def _document_primary_unit(
    page_json_by_version: Mapping[str, dict[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
) -> tuple[str, int] | None:
    units = []
    for page in page_json_by_version.values():
        for section in page.get("sections", []) if type(page) is dict else []:
            if (
                type(section) is not dict
                or section.get("statement_type") != "BALANCE_SHEET"
                or section.get("content_kind") != "PRIMARY_STATEMENT"
            ):
                continue
            for table in section.get("tables", []):
                if type(table) is not dict:
                    continue
                unit = _explicit_unit(table, compiled_specs=compiled_specs)
                if unit is not None:
                    units.append(unit)
    unique = sorted(set(units))
    return unique[0] if len(unique) == 1 else None


def _primary_regions(
    *,
    document: Mapping[str, Any],
    selected_page_axis: list[dict[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    regions = []
    for page_axis in selected_page_axis:
        page = page_json_by_version.get(page_axis["page_json_version_id"])
        if type(page) is not dict:
            raise _error("Family-26 selected page JSON is absent")
        for section_ordinal, section in enumerate(page.get("sections", []), start=1):
            if (
                type(section) is not dict
                or section.get("statement_type") != "BALANCE_SHEET"
                or section.get("content_kind") != "PRIMARY_STATEMENT"
            ):
                continue
            for table_ordinal, table in enumerate(section.get("tables", []), start=1):
                if type(table) is not dict:
                    continue
                classification = classify_gemini_json_multitable_hierarchical_table_v1(
                    page, section, table, compiled_specs=compiled_specs
                )
                hits = [
                    hit
                    for hit in classification.get("role_hits", [])
                    if hit.get("role") == "INTEREST_FEE_RECEIVABLES"
                ]
                if len(hits) != 1:
                    continue
                regions.append(
                    {
                        "component_roles": sorted(_classification_roles(classification)),
                        "document_id": document["document_id"],
                        "document_ordinal": document["document_ordinal"],
                        "fragment_ordinal": len(regions) + 1,
                        "page_json_version_id": page_axis["page_json_version_id"],
                        "physical_page": page_axis["physical_page"],
                        "section_id": f"s{section_ordinal}",
                        "selected_page_ordinal": page_axis["selected_page_ordinal"],
                        "source_logical_name": document["source_logical_name"],
                        "source_sha256": document["source_sha256"],
                        "table_id": f"t{table_ordinal}",
                    }
                )
    return regions


def _explicit_detail_regions(
    *,
    document: Mapping[str, Any],
    selected_page_axis: list[dict[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Recover exact locally titled detail tables outside a broad owner fence."""

    selected = []
    rejected_population_scoped = []
    explicit_context_kinds = {
        "EXPLICIT_SOLE_TABLE_SECTION_TITLE",
        "EXPLICIT_TABLE_TITLE",
        "EXPLICIT_TITLELESS_SOLE_TABLE_SECTION_NARRATIVE",
    }
    for page_axis in selected_page_axis:
        page = page_json_by_version.get(page_axis["page_json_version_id"])
        if type(page) is not dict:
            raise _error("Family-26 selected page JSON is absent")
        for section_ordinal, section in enumerate(page.get("sections", []), start=1):
            if type(section) is not dict or (
                section.get("statement_type") == "BALANCE_SHEET"
                and section.get("content_kind") == "PRIMARY_STATEMENT"
            ):
                continue
            for table_ordinal, table in enumerate(section.get("tables", []), start=1):
                if type(table) is not dict:
                    continue
                classification = classify_gemini_json_multitable_hierarchical_table_v1(
                    page, section, table, compiled_specs=compiled_specs
                )
                roles = sorted(_classification_roles(classification))
                detail_roles = sorted(set(roles) - {"INTEREST_FEE_RECEIVABLES"})
                exact_owner_total = bool(
                    "INTEREST_FEE_RECEIVABLES" in roles
                    and classification.get("owner_visible") is True
                    and classification.get("family_presence_anchor_visible") is True
                    and classification.get("typed_control_disposition") is None
                    and len(classification.get("money_column_ordinals", [])) == 2
                )
                if not detail_roles and not exact_owner_total:
                    continue
                locator = {
                    "page_json_version_id": page_axis["page_json_version_id"],
                    "physical_page": page_axis["physical_page"],
                    "section_id": f"s{section_ordinal}",
                    "table_id": f"t{table_ordinal}",
                }
                detail_context_invalid = bool(
                    classification.get("context_roles")
                    != ["INTEREST_FEE_RECEIVABLES"]
                    or classification.get("family_presence_anchor_visible") is not True
                    or classification.get("context_resolution_kind")
                    not in explicit_context_kinds
                )
                if detail_roles and detail_context_invalid and not exact_owner_total:
                    rejected_population_scoped.append(
                        {
                            **locator,
                            "context_resolution_kind": classification.get(
                                "context_resolution_kind"
                            ),
                            "detail_roles": detail_roles,
                            "rule": (
                                "NONLOCAL_ROW_POPULATION_CONTEXT_CANNOT_PROMOTE_"
                                "A_DETAIL_TABLE"
                            ),
                        }
                    )
                    continue
                selected.append(
                    {
                        "component_roles": roles,
                        "document_id": document["document_id"],
                        "document_ordinal": document["document_ordinal"],
                        "fragment_ordinal": len(selected) + 1,
                        "page_json_version_id": page_axis["page_json_version_id"],
                        "physical_page": page_axis["physical_page"],
                        "section_id": f"s{section_ordinal}",
                        "selected_page_ordinal": page_axis["selected_page_ordinal"],
                        "source_logical_name": document["source_logical_name"],
                        "source_sha256": document["source_sha256"],
                        "table_id": f"t{table_ordinal}",
                    }
                )
    material = {
        "rejected_population_scoped_tables": rejected_population_scoped,
        "rule": (
            "EXACT_LOCAL_DETAIL_CONTEXT_OR_EXACT_OWNER_VISIBLE_TWO_LANE_NOTE_"
            "TOTAL_PLUS_SOURCE_VISIBLE_DECLARED_ROLE"
        ),
        "selected_regions": canonical_clone_v1(selected),
    }
    return selected, {
        **material,
        "receipt_id": "glicafv1:detail-query:" + canonical_json_sha256_v1(material),
    }


def _primary_observation(
    region: dict[str, Any],
    *,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    page = page_json_by_version[region["page_json_version_id"]]
    section, table = _source_table(
        page, section_id=region["section_id"], table_id=region["table_id"]
    )
    unit = _explicit_unit(table, compiled_specs=compiled_specs)
    unit_rule = "LOCAL_PRIMARY_TABLE_EXPLICIT_UNIT"
    if unit is None:
        unit = _document_primary_unit(
            page_json_by_version, compiled_specs=compiled_specs
        )
        unit_rule = "UNIQUE_DOCUMENT_PRIMARY_BALANCE_EXPLICIT_UNIT"
    one_region = canonical_clone_v1(region)
    one_region["fragment_ordinal"] = 1
    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        page, section, table, compiled_specs=compiled_specs
    )
    hits = [
        hit
        for hit in classification.get("role_hits", [])
        if hit.get("role") == "INTEREST_FEE_RECEIVABLES"
    ]
    money_ordinals = classification.get("money_column_ordinals", [])
    reasons = []
    row = None
    row_ordinal = None
    if len(hits) != 1:
        reasons.append("PRIMARY_INTEREST_FEE_RECEIVABLE_SOURCE_ROW_NOT_UNIQUE")
    else:
        row_ordinal = hits[0]["row_ordinal"]
        rows = table.get("rows")
        if type(rows) is not list or row_ordinal > len(rows):
            reasons.append("PRIMARY_INTEREST_FEE_RECEIVABLE_SOURCE_ROW_ABSENT")
        else:
            row = rows[row_ordinal - 1]
    values = []
    if row is not None:
        source_values = row.get("values_exact")
        if (
            type(source_values) is not list
            or len(money_ordinals) != 2
            or any(ordinal > len(source_values) for ordinal in money_ordinals)
        ):
            reasons.append("PRIMARY_INTEREST_FEE_RECEIVABLE_CELL_AXIS_INCOMPLETE")
        else:
            for ordinal in money_ordinals:
                try:
                    values.append(_money(source_values[ordinal - 1]))
                except (TypeError, ValueError):
                    reasons.append("PRIMARY_INTEREST_FEE_RECEIVABLE_MONEY_CELL_INVALID")
    inspected = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=[one_region],
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        query_receipt=(
            build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
                [one_region]
            )
        ),
    )
    table_receipts = inspected.get("closure_receipt", {}).get("table_receipts", [])
    table_receipt = table_receipts[0] if len(table_receipts) == 1 else None
    lane_axis = table_receipt.get("lane_axis") if type(table_receipt) is dict else None
    if (
        type(lane_axis) is not dict
        or lane_axis.get("complete") is not True
        or len(lane_axis.get("lane_keys", [])) != 2
    ):
        reasons.append("PRIMARY_INTEREST_FEE_RECEIVABLE_PERIOD_AXIS_INCOMPLETE")
    if unit is None:
        reasons.append("PRIMARY_INTEREST_FEE_RECEIVABLE_EXPLICIT_UNIT_ABSENT")
    if values and all(value.get("coefficient") is None for value in values):
        reasons.append("PRIMARY_INTEREST_FEE_RECEIVABLE_ALL_LANES_BLANK")
    source_ref = None
    mapping = None
    if row is not None and row_ordinal is not None:
        source_ref = {
            "hierarchy_path_exact": canonical_clone_v1(
                row.get("hierarchy_path_exact", [])
            ),
            "label_exact": row.get("label_exact"),
            "locator": canonical_clone_v1(one_region),
            "money_column_ordinals": canonical_clone_v1(money_ordinals),
            "row_id": row.get("row_id", f"r{row_ordinal}"),
            "row_kind": row.get("row_kind"),
            "row_ordinal": row_ordinal,
        }
    if source_ref is not None and values and not reasons:
        mapping_material = {
            "report_norm_id": 982,
            "role": "INTEREST_FEE_RECEIVABLES",
            "row_id": source_ref["row_id"],
            "source_refs": [source_ref],
            "state": "SOURCE_OBSERVED_ROLE_ROW",
            "unit": unit[0],
            "values": values,
        }
        mapping = {
            **mapping_material,
            "item_mapping_id": (
                "gjmthfmv1:item:" + canonical_json_sha256_v1(mapping_material)
            ),
        }
    return {
        "candidate": inspected,
        "magnitude_power10": None if unit is None else unit[1],
        "mapping": mapping,
        "reasons": sorted(set(reasons)),
        "region": canonical_clone_v1(one_region),
        "table_receipt": canonical_clone_v1(table_receipt),
        "unit": None if unit is None else unit[0],
        "unit_rule": None if unit is None else unit_rule,
    }


def _round_to_power(coefficient: int, power: int) -> int:
    divisor = 10**power
    magnitude = (abs(coefficient) + divisor // 2) // divisor
    return -magnitude if coefficient < 0 else magnitude


def _unit_power10(
    unit: str, *, compiled_specs: Mapping[str, Any]
) -> int | None:
    powers = {
        binding["magnitude_power10"]
        for binding in compiled_specs.get("unit_bindings", [])
        if binding.get("accepted") is True and binding.get("canonical_unit") == unit
    }
    return next(iter(powers)) if len(powers) == 1 else None


def _mapping_values_corroborate(
    primary_mapping: Mapping[str, Any],
    note_mapping: Mapping[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
) -> tuple[bool, dict[str, Any]]:
    """Compare two source-observed totals without manufacturing blank lanes."""

    primary_power = _unit_power10(
        primary_mapping.get("unit"), compiled_specs=compiled_specs
    )
    note_power = _unit_power10(note_mapping.get("unit"), compiled_specs=compiled_specs)
    primary_values = primary_mapping.get("values")
    note_values = note_mapping.get("values")
    lane_receipts = []
    complete = (
        primary_power is not None
        and note_power is not None
        and type(primary_values) is list
        and type(note_values) is list
        and len(primary_values) == len(note_values) == 2
    )
    if complete:
        for lane_ordinal, (primary_value, note_value) in enumerate(
            zip(primary_values, note_values, strict=True), start=1
        ):
            primary_coefficient = (
                primary_value.get("coefficient")
                if type(primary_value) is dict
                else None
            )
            note_coefficient = (
                note_value.get("coefficient") if type(note_value) is dict else None
            )
            if primary_coefficient is None or note_coefficient is None:
                equal = primary_coefficient is None and note_coefficient is None
            elif primary_power <= note_power:
                equal = (
                    _round_to_power(
                        primary_coefficient, note_power - primary_power
                    )
                    == note_coefficient
                )
            else:
                equal = (
                    _round_to_power(note_coefficient, primary_power - note_power)
                    == primary_coefficient
                )
            lane_receipts.append(
                {
                    "corroborated": equal,
                    "lane_ordinal": lane_ordinal,
                    "note_coefficient": note_coefficient,
                    "primary_coefficient": primary_coefficient,
                }
            )
        complete = all(item["corroborated"] for item in lane_receipts)
    material = {
        "corroborated": complete,
        "lane_receipts": lane_receipts,
        "note_source_refs": canonical_clone_v1(note_mapping.get("source_refs", [])),
        "note_unit": note_mapping.get("unit"),
        "primary_source_refs": canonical_clone_v1(
            primary_mapping.get("source_refs", [])
        ),
        "primary_unit": primary_mapping.get("unit"),
        "rule": (
            "SOURCE_OBSERVED_TOTALS_EQUAL_AFTER_ROUNDING_HIGHER_PRECISION_"
            "PRESENTATION_TO_LOWER_PRECISION"
        ),
    }
    return complete, {
        **material,
        "receipt_id": "glicafv1:corroboration:" + canonical_json_sha256_v1(material),
    }


def _select_primary_region(
    regions: list[dict[str, Any]],
    *,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    observations = [
        _primary_observation(
            region,
            page_json_by_version=page_json_by_version,
            compiled_specs=compiled_specs,
        )
        for region in regions
    ]
    usable = [item for item in observations if not item["reasons"]]
    selected = list(regions)
    rule = "ALL_PRIMARY_SOURCE_PRESENTATIONS_RETAINED_UNRESOLVED"
    if len(usable) == 1:
        selected = [usable[0]["region"]]
        rule = "UNIQUE_PRIMARY_SOURCE_PRESENTATION"
    elif len(usable) > 1:
        chosen = min(
            usable,
            key=lambda item: (
                item["magnitude_power10"],
                item["region"]["selected_page_ordinal"],
                item["region"]["section_id"],
                item["region"]["table_id"],
            ),
        )
        chosen_power = chosen["magnitude_power10"]
        chosen_values = [value["coefficient"] for value in chosen["mapping"]["values"]]
        corroborated = True
        for observation in usable:
            power = observation["magnitude_power10"]
            values = [value["coefficient"] for value in observation["mapping"]["values"]]
            delta = power - chosen_power
            for chosen_value, value in zip(chosen_values, values, strict=True):
                if chosen_value is None or value is None:
                    if chosen_value is not None or value is not None:
                        corroborated = False
                        break
                    continue
                expected = (
                    _round_to_power(chosen_value, delta)
                    if delta >= 0
                    else chosen_value * (10 ** -delta)
                )
                if expected != value:
                    corroborated = False
                    break
            if not corroborated:
                break
        if corroborated:
            selected = [chosen["region"]]
            rule = "ROUNDED_LOWER_PRECISION_DUPLICATES_SELECT_HIGHEST_PRECISION_SOURCE"
    for ordinal, region in enumerate(selected, start=1):
        region["fragment_ordinal"] = ordinal
    material = {
        "observations": [
            {
                "magnitude_power10": item["magnitude_power10"],
                "reasons": item["reasons"],
                "region": item["region"],
                "unit": item["unit"],
                "unit_rule": item["unit_rule"],
                "values": (
                    [] if item["mapping"] is None else item["mapping"]["values"]
                ),
            }
            for item in observations
        ],
        "rule": rule,
        "selected_region_axis_sha256": canonical_json_sha256_v1(selected),
    }
    return selected, {
        **material,
        "receipt_id": "glicafv1:primary:" + canonical_json_sha256_v1(material),
    }


def build_gemini_json_loan_interest_accrual_classification_indexed_query_evidence_v1(
    *,
    base_indexed_query_evidence: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Promote exact primary RNID-982 rows absent from note-table discovery."""

    base = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        base_indexed_query_evidence, compiled_specs=compiled_specs
    )
    pages_by_document: dict[int, list[dict[str, Any]]] = {}
    for page in base["selected_page_axis"]:
        pages_by_document.setdefault(page["document_ordinal"], []).append(page)
    clusters = []
    for disposition, document in zip(
        base["candidate_dispositions"], base["selected_document_axis"], strict=True
    ):
        cluster = canonical_clone_v1(disposition["cluster"])
        document_pages = page_json_by_document.get(document["document_ordinal"])
        if type(document_pages) is not dict:
            raise _error("Family-26 selected document page JSON is absent")
        primary_regions = _primary_regions(
            document=document,
            selected_page_axis=pages_by_document[document["document_ordinal"]],
            page_json_by_version=document_pages,
            compiled_specs=compiled_specs,
        )
        detail_regions, detail_receipt = _explicit_detail_regions(
            document=document,
            selected_page_axis=pages_by_document[document["document_ordinal"]],
            page_json_by_version=document_pages,
            compiled_specs=compiled_specs,
        )
        if not primary_regions and not detail_regions:
            clusters.append(cluster)
            continue
        selected = []
        primary_receipt = None
        if primary_regions:
            selected, primary_receipt = _select_primary_region(
                primary_regions,
                page_json_by_version=document_pages,
                compiled_specs=compiled_specs,
            )
        selected.extend(detail_regions)
        existing = (
            canonical_clone_v1(cluster.get("component_regions", []))
            if disposition["disposition"] == READY
            else []
        )
        by_locator = {
            (
                region["page_json_version_id"],
                region["section_id"],
                region["table_id"],
            ): region
            for region in [*selected, *existing]
        }
        combined = sorted(
            by_locator.values(),
            key=lambda region: (
                region["selected_page_ordinal"],
                region["section_id"],
                region["table_id"],
            ),
        )
        for fragment_ordinal, region in enumerate(combined, start=1):
            region["fragment_ordinal"] = fragment_ordinal
        material = {
            **{key: value for key, value in cluster.items() if key != "cluster_id"},
            "component_regions": combined,
            "loan_interest_accrual_detail_query_receipt": detail_receipt,
            **(
                {
                    "loan_interest_accrual_primary_query_receipt": primary_receipt
                }
                if primary_receipt is not None
                else {}
            ),
            "reasons": [],
            "status": READY,
        }
        clusters.append(
            {
                **material,
                "cluster_id": "gjmthfcv1:cluster:" + canonical_json_sha256_v1(material),
            }
        )
    evidence = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=base["selected_document_axis"],
        selected_page_axis=base["selected_page_axis"],
        document_clusters=clusters,
        query_policy_sha256=canonical_json_sha256_v1(compiled_specs["query_policy"]),
    )
    return validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        evidence, compiled_specs=compiled_specs
    )


def _evaluate_candidate(
    *,
    regions: list[dict[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    primary_regions = []
    note_regions = []
    for region in regions:
        page = page_json_by_version[region["page_json_version_id"]]
        section, _ = _source_table(
            page, section_id=region["section_id"], table_id=region["table_id"]
        )
        target = (
            primary_regions
            if section.get("statement_type") == "BALANCE_SHEET"
            and section.get("content_kind") == "PRIMARY_STATEMENT"
            else note_regions
        )
        target.append(region)
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
    if not primary_regions:
        return evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
            regions=regions,
            page_json_by_version=page_json_by_version,
            compiled_specs=compiled_specs,
            query_receipt=receipt,
        )
    observations = [
        _primary_observation(
            region,
            page_json_by_version=page_json_by_version,
            compiled_specs=compiled_specs,
        )
        for region in primary_regions
    ]
    reasons = sorted(
        {
            reason
            for observation in observations
            for reason in observation["reasons"]
        }
    )
    if len(primary_regions) != 1:
        reasons.append("MULTIPLE_PRIMARY_INTEREST_FEE_RECEIVABLE_POPULATIONS")
        reasons = sorted(set(reasons))
    adapter_material = {
        "adapter_format_version": ADAPTER_FORMAT_VERSION,
        "observations": [
            {
                "magnitude_power10": observation["magnitude_power10"],
                "reasons": observation["reasons"],
                "region": observation["region"],
                "table_receipt": observation["table_receipt"],
                "unit": observation["unit"],
                "unit_rule": observation["unit_rule"],
                "values": (
                    []
                    if observation["mapping"] is None
                    else observation["mapping"]["values"]
                ),
            }
            for observation in observations
        ],
        "rule": (
            "EXACT_PRIMARY_SOURCE_ROW_WITH_EXPLICIT_PERIOD_UNIT_AND_OPTIONAL_"
            "DETAIL_NOTE_FRONTIER"
        ),
    }
    adapter_receipt = {
        **adapter_material,
        "receipt_id": (
            "glicafv1:candidate:" + canonical_json_sha256_v1(adapter_material)
        ),
    }
    note_candidate = None
    note_total_corroboration = None
    note_mappings = []
    if note_regions:
        local_note_regions = canonical_clone_v1(note_regions)
        for fragment_ordinal, region in enumerate(local_note_regions, start=1):
            region["fragment_ordinal"] = fragment_ordinal
        note_receipt = (
            build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
                local_note_regions
            )
        )
        note_candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
            regions=local_note_regions,
            page_json_by_version=page_json_by_version,
            compiled_specs=compiled_specs,
            query_receipt=note_receipt,
        )
        if note_candidate["status"] != READY:
            reasons.extend(note_candidate["reasons"])
        note_totals = [
            mapping
            for mapping in note_candidate["mappings"]
            if mapping.get("report_norm_id") == 982
        ]
        if len(note_totals) > 1:
            reasons.append("MULTIPLE_DETAIL_NOTE_INTEREST_FEE_RECEIVABLE_TOTALS")
        elif len(note_totals) == 1 and observations[0]["mapping"] is not None:
            corroborated, note_total_corroboration = _mapping_values_corroborate(
                observations[0]["mapping"],
                note_totals[0],
                compiled_specs=compiled_specs,
            )
            if not corroborated:
                reasons.append("PRIMARY_AND_DETAIL_NOTE_TOTALS_CONFLICT")
        note_mappings = [
            mapping
            for mapping in note_candidate["mappings"]
            if mapping.get("report_norm_id") != 982
        ]
    reasons = sorted(set(reasons))
    mappings = (
        []
        if reasons
        else [observations[0]["mapping"], *canonical_clone_v1(note_mappings)]
    )
    if note_candidate is None:
        closure_receipt = {
            "loan_interest_accrual_primary_adapter_receipt": adapter_receipt,
            "query_receipt": receipt,
            "rule": "EXACT_SOURCE_VISIBLE_PRIMARY_INTEREST_FEE_RECEIVABLE_ROW_ONLY",
        }
    else:
        closure_receipt = canonical_clone_v1(note_candidate["closure_receipt"])
        closure_receipt["loan_interest_accrual_primary_adapter_receipt"] = (
            adapter_receipt
        )
        closure_receipt["query_receipt"] = receipt
        closure_receipt["rule"] = (
            "EXACT_SOURCE_VISIBLE_PRIMARY_TOTAL_PLUS_EXHAUSTIVE_DETAIL_NOTE_"
            "FRONTIER_WITH_OPTIONAL_SOURCE_TOTAL_CORROBORATION"
        )
        if note_total_corroboration is not None:
            closure_receipt["primary_detail_note_total_corroboration"] = (
                note_total_corroboration
            )
    first = regions[0]
    material = {
        "claim_boundary": (
            "FAMILY26_EXACT_PRIMARY_SOURCE_ROW_EXPLICIT_PERIOD_UNIT_SCHEMA_MAPPING_"
            "PROPOSAL_ONLY_NO_BANK_FILE_YEAR_PAGE_VALUE_ROUTING_OR_BACKSOLVE"
        ),
        "closure_receipt": closure_receipt,
        "component_regions": canonical_clone_v1(regions),
        "document_id": first["document_id"],
        "family_id": FAMILY_ID,
        "mappings": mappings,
        "page_json_version_id": first["page_json_version_id"],
        "physical_page": first["physical_page"],
        "reasons": reasons,
        "section_id": first["section_id"],
        "source_logical_name": first["source_logical_name"],
        "source_sha256": first["source_sha256"],
        "status": READY if mappings and not reasons else UNRESOLVED,
        "table_id": first["table_id"],
    }
    return {
        **material,
        "candidate_id": "gjmthfcv1:candidate:" + canonical_json_sha256_v1(material),
    }


def build_gemini_json_loan_interest_accrual_classification_trials_v1(
    *,
    indexed_query_evidence: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Evaluate every accepted cluster and retain every N/U disposition."""

    indexed = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
    candidates_by_ordinal: dict[int, dict[str, Any]] = {}
    for cluster in indexed["accepted_clusters"]:
        ordinal = cluster["document_ordinal"]
        pages = page_json_by_document.get(ordinal)
        if type(pages) is not dict:
            raise _error("Family-26 selected document pages are absent")
        regions = cluster["component_regions"]
        candidate = _evaluate_candidate(
            regions=regions,
            page_json_by_version=pages,
            compiled_specs=compiled_specs,
        )
        candidates_by_ordinal[ordinal] = candidate

    trials = []
    for document, disposition in zip(
        indexed["selected_document_axis"],
        indexed["candidate_dispositions"],
        strict=True,
    ):
        ordinal = document["document_ordinal"]
        candidate = candidates_by_ordinal.get(ordinal)
        if candidate is not None and candidate["status"] == READY:
            status = READY
            reasons: list[str] = []
            mappings = candidate["mappings"]
            selected_candidate_id = candidate["candidate_id"]
        elif candidate is not None:
            status = UNRESOLVED
            reasons = candidate["reasons"]
            mappings = []
            selected_candidate_id = None
        elif disposition["disposition"] == NOT_OBSERVED:
            status = NOT_OBSERVED
            reasons = []
            mappings = []
            selected_candidate_id = None
        else:
            status = UNRESOLVED
            reasons = disposition["cluster"]["reasons"]
            mappings = []
            selected_candidate_id = None
        trials.append(
            {
                "candidate_count": int(candidate is not None),
                "candidates": [] if candidate is None else [candidate],
                "document_ordinal": ordinal,
                "mappings": canonical_clone_v1(mappings),
                "reasons": canonical_clone_v1(reasons),
                "selected_candidate_id": selected_candidate_id,
                "source_logical_name": document["source_logical_name"],
                "source_sha256": document["source_sha256"],
                "status": status,
            }
        )
    return validate_gemini_json_multitable_hierarchical_sweep_query_bindings_v1(
        trials=trials,
        indexed_query_evidence=indexed,
        compiled_specs=compiled_specs,
    )


def validate_gemini_json_loan_interest_accrual_classification_replay_v1(
    *,
    trials: Any,
    indexed_query_evidence: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Re-evaluate the complete selected source frontier exactly."""

    expected = build_gemini_json_loan_interest_accrual_classification_trials_v1(
        indexed_query_evidence=indexed_query_evidence,
        page_json_by_document=page_json_by_document,
        compiled_specs=compiled_specs,
    )
    if type(trials) is not list or not same_typed_json_v1(trials, expected):
        raise _error("Family-26 candidate replay drifted")
    return expected


def _source_row_identity(
    *,
    source_sha256: str,
    page_json_version_id: str,
    section_id: str,
    table_id: str,
    row_ordinal: int,
    report_norm_id: int,
) -> tuple[str, str, str, str, int, int]:
    return (
        source_sha256,
        page_json_version_id,
        section_id,
        table_id,
        row_ordinal,
        report_norm_id,
    )


def _resolved_family26_total_source_row(
    *,
    document_ordinal: int,
    source_sha256: str,
    source_logical_name: str,
    source_ref: Mapping[str, Any],
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Resolve one provenance-bound detail total without deriving a value."""

    locator = source_ref.get("locator")
    row_ordinal = source_ref.get("row_ordinal")
    money_ordinals = source_ref.get("money_column_ordinals")
    if (
        type(locator) is not dict
        or locator.get("document_ordinal") != document_ordinal
        or locator.get("source_sha256") != source_sha256
        or type(row_ordinal) is not int
        or row_ordinal <= 0
        or type(money_ordinals) is not list
        or len(money_ordinals) != 2
        or any(type(ordinal) is not int or ordinal <= 0 for ordinal in money_ordinals)
    ):
        raise _error("Family-26 detail-total source reference is invalid")
    pages = page_json_by_document.get(document_ordinal)
    page_json_version_id = locator.get("page_json_version_id")
    section_id = locator.get("section_id")
    table_id = locator.get("table_id")
    page = pages.get(page_json_version_id) if type(pages) is dict else None
    if type(page) is not dict:
        raise _error("Family-26 detail-total source page is absent")
    section, table = _source_table(
        page, section_id=section_id, table_id=table_id
    )
    rows = table.get("rows")
    if type(rows) is not list or row_ordinal > len(rows):
        raise _error("Family-26 detail-total source row is absent")
    row = rows[row_ordinal - 1]
    if type(row) is not dict:
        raise _error("Family-26 detail-total source row is invalid")
    row_id = row.get("row_id", f"r{row_ordinal}")
    row_kind = row.get("row_kind")
    if (
        row_id != source_ref.get("row_id", row_id)
        or row_kind != source_ref.get("row_kind", row_kind)
        or row_kind not in {"SUBTOTAL", "TOTAL"}
        or row.get("label_exact") != source_ref.get("label_exact")
        or not same_typed_json_v1(
            row.get("hierarchy_path_exact", []),
            source_ref.get("hierarchy_path_exact", []),
        )
    ):
        raise _error("Family-26 detail-total source row provenance drifted")
    values = row.get("values_exact")
    if type(values) is not list or any(
        ordinal > len(values) for ordinal in money_ordinals
    ):
        raise _error("Family-26 detail-total source cell axis is invalid")
    try:
        parsed_values = [_money(values[ordinal - 1]) for ordinal in money_ordinals]
    except (TypeError, ValueError) as exc:
        raise _error("Family-26 detail-total source cell is invalid") from exc
    physical_page = locator.get("physical_page")
    if type(physical_page) is not int or physical_page <= 0:
        raise _error("Family-26 detail-total physical page is invalid")
    item = {
        "context_resolution_kind": "EXACT_CANDIDATE_DETAIL_TOTAL_SOURCE_REF",
        "document_ordinal": document_ordinal,
        "hierarchy_path_exact": canonical_clone_v1(
            row.get("hierarchy_path_exact", [])
        ),
        "inventory_disposition": "SELECTED_FAMILY_COMPONENT_TOTAL_CONTROL",
        "label_exact": row.get("label_exact"),
        "money_column_ordinals": canonical_clone_v1(money_ordinals),
        "page_json_version_id": page_json_version_id,
        "physical_page": physical_page,
        "report_norm_id": 982,
        "role": "INTEREST_FEE_RECEIVABLES",
        "row_id": row_id,
        "row_kind": row_kind,
        "row_ordinal": row_ordinal,
        "section_id": section_id,
        "section_title_exact": section.get("title_exact"),
        "source_logical_name": source_logical_name,
        "source_sha256": source_sha256,
        "table_id": table_id,
        "table_title_exact": table.get("title_exact"),
        "typed_control_disposition": None,
        "values_exact": canonical_clone_v1(values),
    }
    return item, parsed_values


def _family26_total_lane_receipts(
    *, parsed_values: list[dict[str, Any]], expected_coefficients: Any
) -> list[dict[str, Any]]:
    if (
        type(expected_coefficients) is not list
        or len(expected_coefficients) != 2
        or any(
            type(coefficient) not in {int, type(None)}
            for coefficient in expected_coefficients
        )
    ):
        return []
    receipts = []
    for lane_ordinal, (parsed, expected) in enumerate(
        zip(parsed_values, expected_coefficients, strict=True), start=1
    ):
        observed = parsed.get("coefficient")
        receipts.append(
            {
                "corroborated": observed == expected,
                "expected_existing_mapping_coefficient": expected,
                "lane_ordinal": lane_ordinal,
                "source_observed_total_coefficient": observed,
                "source_observed_total_state": parsed.get("state"),
            }
        )
    return receipts


def _candidate_detail_total_control_rows(
    *,
    trials: list[dict[str, Any]],
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Cover visible note totals while leaving the selected mapping unchanged."""

    controls: dict[tuple[str, str, str, str, int, int], dict[str, Any]] = {}
    directly_corroborated = set()
    for trial in trials:
        for candidate in trial.get("candidates", []):
            closure = candidate.get("closure_receipt", {})
            corroboration = closure.get(
                "primary_detail_note_total_corroboration"
            )
            if type(corroboration) is not dict or (
                corroboration.get("corroborated") is not True
            ):
                continue
            document_ordinal = trial.get("document_ordinal")
            source_sha256 = trial.get("source_sha256")
            source_logical_name = trial.get("source_logical_name")
            if (
                type(document_ordinal) is not int
                or type(source_sha256) is not str
                or type(source_logical_name) is not str
            ):
                raise _error("Family-26 detail-total trial identity is invalid")
            corroboration_lanes = corroboration.get("lane_receipts", [])
            lane_by_ordinal = {
                lane.get("lane_ordinal"): lane
                for lane in corroboration_lanes
                if type(lane) is dict
                and lane.get("corroborated") is True
                and lane.get("lane_ordinal") in {1, 2}
            }
            expected_coefficients = (
                [lane_by_ordinal[ordinal].get("note_coefficient") for ordinal in (1, 2)]
                if type(corroboration_lanes) is list
                and len(corroboration_lanes) == 2
                and set(lane_by_ordinal) == {1, 2}
                else None
            )
            for source_ref in corroboration.get("note_source_refs", []):
                if (
                    type(source_ref) is not dict
                    or source_ref.get("row_kind") not in {"SUBTOTAL", "TOTAL"}
                ):
                    continue
                item, parsed_values = _resolved_family26_total_source_row(
                    document_ordinal=document_ordinal,
                    source_sha256=source_sha256,
                    source_logical_name=source_logical_name,
                    source_ref=source_ref,
                    page_json_by_document=page_json_by_document,
                )
                lane_receipts = _family26_total_lane_receipts(
                    parsed_values=parsed_values,
                    expected_coefficients=expected_coefficients,
                )
                visible = any(
                    value.get("coefficient") is not None for value in parsed_values
                )
                corroborated = bool(
                    len(lane_receipts) == 2
                    and all(lane["corroborated"] for lane in lane_receipts)
                )
                if not corroborated:
                    coverage = (
                        "VIOLATION_NONCLOSING_VISIBLE_FAMILY26_DETAIL_TOTAL_CONTROL"
                    )
                elif visible:
                    coverage = (
                        "CORROBORATED_VISIBLE_FAMILY26_DETAIL_TOTAL_CONTROL"
                    )
                else:
                    coverage = "BLANK_FAMILY26_DETAIL_TOTAL_CONTROL"
                item.update(
                    {
                        "coverage": coverage,
                        "coverage_evidence_kind": (
                            "PRIMARY_DETAIL_NOTE_TOTAL_CORROBORATION_RECEIPT"
                        ),
                        "coverage_proof_id": corroboration.get("receipt_id"),
                        "coverage_rule": (
                            "SOURCE_OBSERVED_DETAIL_TOTAL_MATCHES_AUTHENTICATED_"
                            "NOTE_TOTAL_COEFFICIENTS"
                        ),
                        "lane_corroboration_receipts": lane_receipts,
                    }
                )
                locator = source_ref["locator"]
                identity = _source_row_identity(
                    source_sha256=source_sha256,
                    page_json_version_id=locator["page_json_version_id"],
                    section_id=locator["section_id"],
                    table_id=locator["table_id"],
                    row_ordinal=source_ref["row_ordinal"],
                    report_norm_id=982,
                )
                controls.setdefault(identity, item)
                directly_corroborated.add(identity)

    for trial in trials:
        for candidate in trial.get("candidates", []):
            table_receipts = candidate.get("closure_receipt", {}).get(
                "table_receipts", []
            )
            if not table_receipts:
                continue
            document_ordinal = trial.get("document_ordinal")
            source_sha256 = trial.get("source_sha256")
            source_logical_name = trial.get("source_logical_name")
            pages = page_json_by_document.get(document_ordinal)
            if (
                type(document_ordinal) is not int
                or type(source_sha256) is not str
                or type(source_logical_name) is not str
                or type(pages) is not dict
            ):
                raise _error("Family-26 detail-total page frontier is invalid")
            aggregate_mappings = [
                mapping
                for mapping in candidate.get("mappings", [])
                if mapping.get("report_norm_id") == 982
                and mapping.get("role") == "INTEREST_FEE_RECEIVABLES"
            ]
            for table_receipt in table_receipts:
                classification = table_receipt.get("classification", {})
                role_hits = [
                    hit
                    for hit in classification.get("role_hits", [])
                    if hit.get("role") in OWNED_ROLE_BINDINGS
                    and type(hit.get("row_ordinal")) is int
                ]
                child_hits = [
                    hit
                    for hit in role_hits
                    if hit.get("role") != "INTEREST_FEE_RECEIVABLES"
                ]
                if (
                    not child_hits
                    or classification.get("context_roles")
                    != ["INTEREST_FEE_RECEIVABLES"]
                    or classification.get("family_presence_anchor_visible") is not True
                    or classification.get("typed_control_disposition") is not None
                    or len(classification.get("money_column_ordinals", [])) != 2
                    or table_receipt.get("lane_axis", {}).get("complete") is not True
                    or table_receipt.get("lane_axis", {}).get(
                        "money_column_ordinals"
                    )
                    != classification.get("money_column_ordinals")
                    or table_receipt.get("unit_axis", {}).get("complete") is not True
                ):
                    continue
                region = table_receipt.get("region")
                if type(region) is not dict:
                    raise _error("Family-26 detail-total region is invalid")
                page = pages.get(region.get("page_json_version_id"))
                if type(page) is not dict:
                    raise _error("Family-26 detail-total region page is absent")
                section, table = _source_table(
                    page,
                    section_id=region.get("section_id"),
                    table_id=region.get("table_id"),
                )
                rows = table.get("rows")
                if type(rows) is not list:
                    raise _error("Family-26 detail-total region rows are invalid")
                final_role_row = max(hit["row_ordinal"] for hit in role_hits)
                if final_role_row > len(rows):
                    raise _error("Family-26 detail-total role row is absent")
                final_role_source_row = rows[final_role_row - 1]
                for total in classification.get("total_rows", []):
                    row_ordinal = total.get("row_ordinal")
                    if row_ordinal != final_role_row + 1 or row_ordinal > len(rows):
                        continue
                    row = rows[row_ordinal - 1]
                    context_surfaces = [
                        section.get("title_exact"),
                        table.get("title_exact"),
                    ]
                    for context_row in (final_role_source_row, row):
                        context_surfaces.extend(
                            context_row.get("hierarchy_path_exact", [])
                            if type(context_row) is dict
                            and type(context_row.get("hierarchy_path_exact")) is list
                            else []
                        )
                    exact_context = [
                        surface
                        for surface in context_surfaces
                        if _is_exact_family26_aggregate_surface(surface)
                    ]
                    if not exact_context:
                        continue
                    source_ref = {
                        "hierarchy_path_exact": canonical_clone_v1(
                            row.get("hierarchy_path_exact", [])
                        ),
                        "label_exact": row.get("label_exact"),
                        "locator": canonical_clone_v1(region),
                        "money_column_ordinals": canonical_clone_v1(
                            classification["money_column_ordinals"]
                        ),
                        "row_id": row.get("row_id", f"r{row_ordinal}"),
                        "row_kind": row.get("row_kind"),
                        "row_ordinal": row_ordinal,
                    }
                    identity = _source_row_identity(
                        source_sha256=source_sha256,
                        page_json_version_id=region["page_json_version_id"],
                        section_id=region["section_id"],
                        table_id=region["table_id"],
                        row_ordinal=row_ordinal,
                        report_norm_id=982,
                    )
                    if identity in directly_corroborated:
                        continue
                    item, parsed_values = _resolved_family26_total_source_row(
                        document_ordinal=document_ordinal,
                        source_sha256=source_sha256,
                        source_logical_name=source_logical_name,
                        source_ref=source_ref,
                        page_json_by_document=page_json_by_document,
                    )
                    mapping = (
                        aggregate_mappings[0]
                        if len(aggregate_mappings) == 1
                        else None
                    )
                    expected_coefficients = (
                        [
                            value.get("coefficient")
                            for value in mapping.get("values", [])
                            if type(value) is dict
                        ]
                        if type(mapping) is dict
                        else None
                    )
                    table_unit = table_receipt.get("unit_axis", {}).get(
                        "canonical_unit"
                    )
                    mapping_is_source_observed = bool(
                        type(mapping) is dict
                        and mapping.get("state") == "SOURCE_OBSERVED_ROLE_ROW"
                        and type(mapping.get("source_refs")) is list
                        and bool(mapping["source_refs"])
                        and mapping.get("unit") == table_unit
                    )
                    lane_receipts = _family26_total_lane_receipts(
                        parsed_values=parsed_values,
                        expected_coefficients=(
                            expected_coefficients
                            if mapping_is_source_observed
                            else None
                        ),
                    )
                    visible = any(
                        value.get("coefficient") is not None
                        for value in parsed_values
                    )
                    corroborated = bool(
                        len(lane_receipts) == 2
                        and all(lane["corroborated"] for lane in lane_receipts)
                    )
                    proof_material = {
                        "aggregate_item_mapping_id": (
                            mapping.get("item_mapping_id")
                            if type(mapping) is dict
                            else None
                        ),
                        "context_evidence_exact": exact_context,
                        "lane_corroboration_receipts": lane_receipts,
                        "source_ref": source_ref,
                        "table_unit": table_unit,
                    }
                    if not corroborated:
                        coverage = (
                            "VIOLATION_NONCLOSING_VISIBLE_FAMILY26_DETAIL_"
                            "TOTAL_CONTROL"
                        )
                    elif visible:
                        coverage = (
                            "CORROBORATED_VISIBLE_FAMILY26_DETAIL_TOTAL_CONTROL"
                        )
                    else:
                        coverage = "BLANK_FAMILY26_DETAIL_TOTAL_CONTROL"
                    item.update(
                        {
                            "context_evidence_exact": exact_context,
                            "coverage": coverage,
                            "coverage_evidence_kind": (
                                "ADJACENT_ROW_LOCAL_DETAIL_TOTAL_CONTROL"
                            ),
                            "coverage_proof_id": (
                                "glicafv1:detail-total-control:"
                                + canonical_json_sha256_v1(proof_material)
                            ),
                            "coverage_rule": (
                                "SOURCE_OBSERVED_ADJACENT_DETAIL_TOTAL_EQUALS_"
                                "EXISTING_SOURCE_OBSERVED_PRIMARY_MAPPING_"
                                "IN_THE_SAME_UNIT"
                            ),
                            "lane_corroboration_receipts": lane_receipts,
                        }
                    )
                    controls.setdefault(identity, item)
    return [controls[identity] for identity in sorted(controls)]


def _candidate_table_total_disposition_rows(
    *,
    trials: list[dict[str, Any]],
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    detail_total_controls: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Classify every total exposed by a candidate table receipt."""

    def hierarchy_root_exact(row: Mapping[str, Any]) -> Any:
        path = row.get("hierarchy_path_exact")
        if type(path) is not list:
            return None
        return next(
            (
                component
                for component in path
                if type(component) is str and component.strip()
            ),
            None,
        )

    def following_scope_boundary_axis(
        *, rows: list[Any], last_role_row: int | None, total_row: int
    ) -> list[dict[str, Any]]:
        if last_role_row is None or total_row <= last_role_row + 1:
            return []
        last_source_row = rows[last_role_row - 1]
        if type(last_source_row) is not dict:
            raise _error("Family-26 final role source row is invalid")
        last_root_exact = hierarchy_root_exact(last_source_row)
        last_root = normalize_vietnamese_anchor_v1(last_root_exact or "")
        result = []
        for boundary_ordinal in range(last_role_row + 1, total_row):
            boundary = rows[boundary_ordinal - 1]
            if type(boundary) is not dict:
                raise _error("Family-26 following-scope boundary row is invalid")
            boundary_root_exact = hierarchy_root_exact(boundary)
            boundary_root = normalize_vietnamese_anchor_v1(
                boundary_root_exact or ""
            )
            evidence_kinds = []
            if boundary.get("row_kind") in {
                "GROUP",
                "HEADER",
                "SUBTOTAL",
                "TOTAL",
            }:
                evidence_kinds.append("INTERVENING_STRUCTURAL_ROW")
            if last_root and boundary_root and boundary_root != last_root:
                evidence_kinds.append("INTERVENING_HIERARCHY_ROOT_TRANSITION")
            if evidence_kinds:
                result.append(
                    {
                        "boundary_evidence_kinds": evidence_kinds,
                        "hierarchy_root_exact": boundary_root_exact,
                        "label_exact": boundary.get("label_exact"),
                        "last_owned_role_hierarchy_root_exact": last_root_exact,
                        "row_id": boundary.get(
                            "row_id", f"r{boundary_ordinal}"
                        ),
                        "row_kind": boundary.get("row_kind"),
                        "row_ordinal": boundary_ordinal,
                    }
                )
        return result

    controls_by_locator = {
        (
            item["source_sha256"],
            item["page_json_version_id"],
            item["section_id"],
            item["table_id"],
            item["row_ordinal"],
        ): item
        for item in detail_total_controls
    }
    records: dict[tuple[str, str, str, str, int], dict[str, Any]] = {}
    for trial in trials:
        candidates = [
            candidate
            for candidate in trial.get("candidates", [])
            if candidate.get("closure_receipt", {}).get("table_receipts")
        ]
        if not candidates:
            continue
        document_ordinal = trial.get("document_ordinal")
        source_sha256 = trial.get("source_sha256")
        source_logical_name = trial.get("source_logical_name")
        pages = page_json_by_document.get(document_ordinal)
        if (
            type(document_ordinal) is not int
            or type(source_sha256) is not str
            or type(source_logical_name) is not str
            or type(pages) is not dict
        ):
            raise _error("Family-26 candidate-total trial frontier is invalid")
        for candidate in candidates:
            for table_receipt in candidate.get("closure_receipt", {}).get(
                "table_receipts", []
            ):
                classification = table_receipt.get("classification", {})
                role_hits = [
                    hit
                    for hit in classification.get("role_hits", [])
                    if hit.get("role") in OWNED_ROLE_BINDINGS
                    and type(hit.get("row_ordinal")) is int
                ]
                if not role_hits and classification.get("context_roles") != [
                    "INTEREST_FEE_RECEIVABLES"
                ]:
                    continue
                region = table_receipt.get("region")
                if type(region) is not dict:
                    raise _error("Family-26 candidate-total region is invalid")
                page = pages.get(region.get("page_json_version_id"))
                if type(page) is not dict:
                    raise _error("Family-26 candidate-total region page is absent")
                section, table = _source_table(
                    page,
                    section_id=region.get("section_id"),
                    table_id=region.get("table_id"),
                )
                rows = table.get("rows")
                if type(rows) is not list:
                    raise _error("Family-26 candidate-total table rows are invalid")
                first_role_row = min(
                    (hit["row_ordinal"] for hit in role_hits), default=None
                )
                last_role_row = max(
                    (hit["row_ordinal"] for hit in role_hits), default=None
                )
                context_material = {
                    "context_resolution_kind": classification.get(
                        "context_resolution_kind"
                    ),
                    "context_roles": canonical_clone_v1(
                        classification.get("context_roles", [])
                    ),
                    "family_presence_anchor_visible": classification.get(
                        "family_presence_anchor_visible"
                    ),
                    "first_owned_role_row_ordinal": first_role_row,
                    "last_owned_role_row_ordinal": last_role_row,
                    "role_hit_axis": [
                        [hit["row_ordinal"], hit["role"]]
                        for hit in sorted(
                            role_hits,
                            key=lambda hit: (hit["row_ordinal"], hit["role"]),
                        )
                    ],
                }
                money_ordinals = classification.get("money_column_ordinals", [])
                for total in classification.get("total_rows", []):
                    row_ordinal = total.get("row_ordinal")
                    if (
                        type(row_ordinal) is not int
                        or not 1 <= row_ordinal <= len(rows)
                    ):
                        raise _error("Family-26 candidate-total row is absent")
                    row = rows[row_ordinal - 1]
                    if (
                        type(row) is not dict
                        or row.get("row_kind") not in {"SUBTOTAL", "TOTAL"}
                        or row.get("row_kind") != total.get("row_kind")
                    ):
                        raise _error("Family-26 candidate-total row kind drifted")
                    values = row.get("values_exact")
                    visible = bool(
                        type(values) is list
                        and type(money_ordinals) is list
                        and any(
                            type(ordinal) is int
                            and 0 < ordinal <= len(values)
                            and values[ordinal - 1] is not None
                            for ordinal in money_ordinals
                        )
                    )
                    identity = (
                        source_sha256,
                        region["page_json_version_id"],
                        region["section_id"],
                        region["table_id"],
                        row_ordinal,
                    )
                    item = records.setdefault(
                        identity,
                        {
                            "document_ordinal": document_ordinal,
                            "hierarchy_path_exact": canonical_clone_v1(
                                row.get("hierarchy_path_exact", [])
                            ),
                            "label_exact": row.get("label_exact"),
                            "page_json_version_id": region[
                                "page_json_version_id"
                            ],
                            "physical_page": region["physical_page"],
                            "row_id": row.get("row_id", f"r{row_ordinal}"),
                            "row_kind": row.get("row_kind"),
                            "row_ordinal": row_ordinal,
                            "section_id": region["section_id"],
                            "section_title_exact": section.get("title_exact"),
                            "source_logical_name": source_logical_name,
                            "source_sha256": source_sha256,
                            "table_id": region["table_id"],
                            "table_title_exact": table.get("title_exact"),
                            "values_exact": canonical_clone_v1(values),
                            "visible_money": visible,
                            "receipt_context_axis": [],
                        },
                    )
                    context_with_boundary = {
                        **context_material,
                        "following_scope_boundary_axis": (
                            following_scope_boundary_axis(
                                rows=rows,
                                last_role_row=last_role_row,
                                total_row=row_ordinal,
                            )
                        ),
                    }
                    if context_with_boundary not in item["receipt_context_axis"]:
                        item["receipt_context_axis"].append(
                            canonical_clone_v1(context_with_boundary)
                        )

    result = []
    for identity in sorted(records):
        item = records[identity]
        contexts = sorted(
            item.pop("receipt_context_axis"), key=canonical_json_sha256_v1
        )
        row_ordinal = item["row_ordinal"]
        control = controls_by_locator.get(identity)
        local_surfaces = [
            item.get("label_exact"),
            item.get("section_title_exact"),
            item.get("table_title_exact"),
            *item.get("hierarchy_path_exact", []),
        ]
        uncovered_exact_family26_surface = any(
            _is_exact_family26_aggregate_surface(surface)
            for surface in local_surfaces
        )
        parent_other_assets_total = bool(
            normalize_vietnamese_anchor_v1(item.get("label_exact") or "")
            == "tai san co khac"
            and any(
                context["last_owned_role_row_ordinal"] is not None
                and row_ordinal == context["last_owned_role_row_ordinal"] + 1
                and context["role_hit_axis"]
                and all(
                    role == "INTEREST_FEE_RECEIVABLES"
                    for _, role in context["role_hit_axis"]
                )
                for context in contexts
            )
        )
        wholly_preceding = bool(
            contexts
            and all(
                context["first_owned_role_row_ordinal"] is not None
                and row_ordinal < context["first_owned_role_row_ordinal"]
                for context in contexts
            )
        )
        wholly_following = bool(
            contexts
            and all(
                context["last_owned_role_row_ordinal"] is not None
                and row_ordinal > context["last_owned_role_row_ordinal"]
                and bool(context["following_scope_boundary_axis"])
                for context in contexts
            )
        )
        if control is not None:
            coverage = control["coverage"]
            coverage_proof_id = control.get("coverage_proof_id")
            report_norm_id = 982
            role = "INTEREST_FEE_RECEIVABLES"
        elif uncovered_exact_family26_surface:
            coverage = "VIOLATION_UNCOVERED_EXACT_FAMILY26_TOTAL"
            coverage_proof_id = None
            report_norm_id = 982
            role = "INTEREST_FEE_RECEIVABLES"
        elif parent_other_assets_total:
            coverage = "OUTSIDE_FAMILY26_STRUCTURAL_PARENT_OTHER_ASSETS_TOTAL"
            coverage_proof_id = None
            report_norm_id = 966
            role = "OTHER_ASSETS_STRUCTURAL_CONTEXT"
        elif wholly_preceding:
            coverage = "OUTSIDE_FAMILY26_PRECEDING_OTHER_SUBTREE_TOTAL"
            coverage_proof_id = None
            report_norm_id = None
            role = None
        elif wholly_following:
            coverage = "OUTSIDE_FAMILY26_FOLLOWING_OTHER_NOTE_TOTAL"
            coverage_proof_id = None
            report_norm_id = None
            role = None
        else:
            coverage = "VIOLATION_UNCLASSIFIED_CANDIDATE_TABLE_TOTAL"
            coverage_proof_id = None
            report_norm_id = None
            role = None
        result.append(
            {
                **item,
                "coverage": coverage,
                "coverage_proof_id": coverage_proof_id,
                "receipt_context_axis": contexts,
                "report_norm_id": report_norm_id,
                "role": role,
            }
        )
    return result


def _target_like_receivable_label(label_exact: Any) -> bool:
    exact = (
        re.sub(r"\s+", " ", label_exact.casefold()).strip()
        if type(label_exact) is str
        else ""
    )
    label = normalize_vietnamese_anchor_v1(exact)
    accented_vietnamese = bool(
        re.search(r"(?<!\w)(?:lãi|phí)(?!\w)", exact)
        and re.search(
            r"(?<!\w)(?:phải\s+thu(?!\s+hồi\b)|dự\s+thu)(?!\w)",
            exact,
        )
    )
    ascii_vietnamese = bool(
        re.search(r"(?<!\w)(?:lai|phi)(?!\w)", exact)
        and re.search(
            r"(?<!\w)(?:phai\s+thu(?!\s+hoi\b)|du\s+thu)(?!\w)",
            exact,
        )
        and "ban lai" not in label
        and "tctd phi ngan hang" not in label
    )
    vietnamese = bool(
        accented_vietnamese or ascii_vietnamese
    )
    english = bool(
        re.search(r"(?<!\w)(?:interest|fee)(?!\w)", exact)
        and re.search(r"(?<!\w)(?:receivable|accrued)(?!\w)", exact)
    )
    return vietnamese or english


def _target_like_receivable_source_surface(
    *,
    label_exact: Any,
    hierarchy_path_exact: Any,
    columns: Any = None,
    values_exact: Any = None,
) -> dict[str, Any] | None:
    """Return the row-local target surface, including label-loss representations."""

    if _target_like_receivable_label(label_exact):
        return {
            "origin": "LABEL_EXACT",
            "surface_exact": label_exact,
            "value_ordinal": None,
        }
    if type(hierarchy_path_exact) is list:
        terminal = next(
            (
                value
                for value in reversed(hierarchy_path_exact)
                if type(value) is str and value.strip()
            ),
            None,
        )
        if _target_like_receivable_label(terminal):
            return {
                "origin": "HIERARCHY_TERMINAL_EXACT",
                "surface_exact": terminal,
                "value_ordinal": None,
            }
    if type(columns) is not list or type(values_exact) is not list:
        return None
    money_column_count = sum(
        type(column) is dict and column.get("value_kind") == "MONEY"
        for column in columns
    )
    for value_ordinal, (column, value) in enumerate(
        zip(columns, values_exact, strict=False), start=1
    ):
        compact = re.sub(r"\s+", " ", value).strip() if type(value) is str else ""
        if (
            type(column) is dict
            and column.get("value_kind") == "TEXT"
            and compact
            and _target_like_receivable_label(compact)
        ):
            return {
                "origin": (
                    "EXPLICIT_TEXT_VALUE_CELL"
                    if (
                        len(compact) <= 160
                        and len(compact.split()) <= 24
                    )
                    or money_column_count
                    else "NARRATIVE_TEXT_VALUE_CELL"
                ),
                "surface_exact": value,
                "value_ordinal": value_ordinal,
            }
    return None


def _allowed_interest_support_receivable(
    *,
    label_exact: Any,
    hierarchy_path_exact: Any,
    section_title_exact: Any = None,
    table_title_exact: Any = None,
) -> bool:
    label = normalize_vietnamese_anchor_v1(
        label_exact if type(label_exact) is str else ""
    )
    context = [
        normalize_vietnamese_anchor_v1(value)
        for value in (
            hierarchy_path_exact if type(hierarchy_path_exact) is list else []
        )
        if type(value) is str
    ]
    context.extend(
        normalize_vietnamese_anchor_v1(value)
        for value in (section_title_exact, table_title_exact)
        if type(value) is str
    )
    return bool(
        "ho tro lai suat" in label
        and any(
            marker in surface
            for marker in _GENERAL_RECEIVABLES_CONTEXT_MARKERS
            for surface in context
        )
    )


def _is_exact_family26_aggregate_surface(value: Any) -> bool:
    """Recognize an aggregate heading without accepting a composite row."""

    surface = normalize_vietnamese_anchor_v1(
        value if type(value) is str else ""
    )
    tokens = surface.split()
    for alias in _FAMILY26_AGGREGATE_ALIASES:
        alias_tokens = alias.split()
        width = len(alias_tokens)
        for start in range(len(tokens) - width + 1):
            if tokens[start : start + width] != alias_tokens:
                continue
            prefix = tokens[:start]
            suffix = tokens[start + width :]
            prefix_is_outline = all(
                token.isdigit() or re.fullmatch(r"[ivx]+", token)
                for token in prefix
            )
            suffix_is_annotation = (
                not suffix
                or suffix == ["tiep", "theo"]
                or all(
                    token.isdigit()
                    or re.fullmatch(r"[a-z]|[ivx]+", token)
                    for token in suffix
                )
                or (
                    suffix[:2] == ["thuyet", "minh"]
                    and all(
                        token.isdigit()
                        or re.fullmatch(r"[a-z]|[ivx]+", token)
                        for token in suffix[2:]
                    )
                )
            )
            if prefix_is_outline and suffix_is_annotation:
                return True
    return False


def _raw_target_context_disposition(
    *,
    label_exact: Any,
    hierarchy_path_exact: Any,
    section_title_exact: Any,
    table_title_exact: Any,
    inventory_disposition: Any,
    section_narratives_exact: Any = None,
    target_surface_origin: Any = None,
    row_label_context_exact: Any = None,
) -> dict[str, Any]:
    """Classify one raw target-like row without crossing the F26 frontier."""

    label = normalize_vietnamese_anchor_v1(
        label_exact if type(label_exact) is str else ""
    )
    if target_surface_origin == "NARRATIVE_TEXT_VALUE_CELL":
        return {
            "coverage": "OUTSIDE_FAMILY26_NARRATIVE_POLICY_OR_RISK_TEXT",
            "context_evidence_exact": [label_exact],
            "rule": (
                "LONG_FORM_TEXT_CELL_WITHOUT_A_MONEY_COLUMN_IS_NARRATIVE_"
                "NOT_A_SCHEMA_MAPPABLE_BALANCE_ROW"
            ),
        }
    hierarchy = [
        value
        for value in (
            hierarchy_path_exact if type(hierarchy_path_exact) is list else []
        )
        if type(value) is str
    ]
    ancestor_surfaces = (
        hierarchy
        if target_surface_origin == "EXPLICIT_TEXT_VALUE_CELL"
        else hierarchy[:-1]
    )
    structural_surfaces = [
        value
        for value in (
            section_title_exact,
            table_title_exact,
            *ancestor_surfaces,
            row_label_context_exact,
        )
        if type(value) is str
        and normalize_vietnamese_anchor_v1(value) != label
    ]
    narrative_surfaces = [
        value
        for value in (
            section_narratives_exact
            if type(section_narratives_exact) is list
            else []
        )
        if type(value) is str
    ]
    context_surfaces = [*structural_surfaces, *narrative_surfaces]
    normalized_context = [
        (value, normalize_vietnamese_anchor_v1(value))
        for value in context_surfaces
    ]
    matched_family_surfaces = [
        value
        for value in structural_surfaces
        if _is_exact_family26_aggregate_surface(value)
    ]
    if matched_family_surfaces:
        return {
            "coverage": "VIOLATION_UNCLASSIFIED_TARGET_LIKE_SOURCE_ROW",
            "context_evidence_exact": matched_family_surfaces,
            "rule": "UNBOUND_ROW_INSIDE_EXACT_FAMILY26_AGGREGATE_CONTEXT",
        }

    off_balance_evidence = [
        value
        for value, normalized in normalized_context
        for marker in _OFF_BALANCE_CONTEXT_MARKERS
        if marker in normalized
    ]
    if off_balance_evidence or any(
        marker in label
        for marker in ("phai thu chua thu duoc", "phi chua thu duoc")
    ):
        return {
            "coverage": "OUTSIDE_FAMILY26_OFF_BALANCE_UNCOLLECTED_INTEREST_FEE",
            "context_evidence_exact": off_balance_evidence or [label_exact],
            "rule": "OFF_BALANCE_DISCLOSURE_IS_OUTSIDE_BALANCE_SHEET_ACCRUAL_SUBTREE",
        }

    related_party_evidence = [
        value
        for value, normalized in normalized_context
        for marker in _RELATED_PARTY_CONTEXT_MARKERS
        if marker in normalized
    ]
    if related_party_evidence:
        return {
            "coverage": "OUTSIDE_FAMILY26_RELATED_PARTY_BALANCE_OR_TRANSACTION",
            "context_evidence_exact": related_party_evidence,
            "rule": "RELATED_PARTY_AXIS_IS_NOT_THE_BALANCE_SHEET_ACCRUAL_SUBTREE",
        }

    if _allowed_interest_support_receivable(
        label_exact=label_exact,
        hierarchy_path_exact=hierarchy_path_exact,
        section_title_exact=section_title_exact,
        table_title_exact=table_title_exact,
    ):
        return {
            "coverage": "OUTSIDE_FAMILY26_GENERAL_RECEIVABLES_INTEREST_SUPPORT_PROGRAM",
            "context_evidence_exact": [label_exact],
            "rule": "INTEREST_SUPPORT_PROGRAM_RECEIVABLE_IS_A_GENERAL_RECEIVABLE",
        }

    if "hop dong mua va cam ket ban lai chung khoan" in label:
        return {
            "coverage": "OUTSIDE_FAMILY26_REVERSE_REPO_RECEIVABLE_LEXICAL_COLLISION",
            "context_evidence_exact": [label_exact],
            "rule": "BAN_LAI_IS_RESALE_NOT_INTEREST",
        }

    if any(marker in label for marker in _EXPENSE_OR_REVERSAL_MARKERS):
        return {
            "coverage": "OUTSIDE_FAMILY26_EXPENSE_OR_REVERSAL_CONTROL",
            "context_evidence_exact": [label_exact],
            "rule": "EXPENSE_OR_REVERSAL_FLOW_IS_NOT_A_RECEIVABLE_BALANCE",
        }

    credit_risk_evidence = [
        value
        for value, normalized in normalized_context
        for marker in _CREDIT_RISK_CONTEXT_MARKERS
        if marker in normalized
    ]
    if credit_risk_evidence:
        return {
            "coverage": "OUTSIDE_FAMILY26_CREDIT_RISK_OR_FINANCIAL_INSTRUMENT_CONTROL",
            "context_evidence_exact": credit_risk_evidence,
            "rule": "RISK_OR_FINANCIAL_INSTRUMENT_AXIS_IS_NOT_THE_ACCRUAL_SUBTREE",
        }

    if _is_exact_family26_aggregate_surface(label_exact) or (
        inventory_disposition == "SELECTED_FAMILY_COMPONENT"
    ):
        return {
            "coverage": "VIOLATION_UNCLASSIFIED_TARGET_LIKE_SOURCE_ROW",
            "context_evidence_exact": [label_exact],
            "rule": (
                "UNBOUND_EXACT_FAMILY26_AGGREGATE_ROW"
                if _is_exact_family26_aggregate_surface(label_exact)
                else "UNBOUND_ROW_INSIDE_SELECTED_FAMILY26_COMPONENT"
            ),
        }

    return {
        "coverage": "OUTSIDE_EXPLICIT_FAMILY26_CONTEXT",
        "context_evidence_exact": structural_surfaces,
        "rule": "NO_EXACT_FAMILY26_AGGREGATE_OR_SELECTED_COMPONENT_CONTEXT",
    }


def _text_cell_primary_presentation_corroboration(
    *,
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    row: Mapping[str, Any],
    mapped_aggregate: Mapping[str, Any] | None,
    compiled_specs: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Corroborate a primary row whose printed label landed in a TEXT cell."""

    target = _target_like_receivable_source_surface(
        label_exact=row.get("label_exact"),
        hierarchy_path_exact=row.get("hierarchy_path_exact"),
        columns=table.get("columns"),
        values_exact=row.get("values_exact"),
    )
    if (
        target is None
        or target["origin"] != "EXPLICIT_TEXT_VALUE_CELL"
        or not _is_exact_family26_aggregate_surface(target["surface_exact"])
        or section.get("statement_type") != "BALANCE_SHEET"
        or section.get("content_kind") != "PRIMARY_STATEMENT"
        or type(mapped_aggregate) is not dict
        or mapped_aggregate.get("report_norm_id") != 982
        or mapped_aggregate.get("role") != "INTEREST_FEE_RECEIVABLES"
        or mapped_aggregate.get("state") != "SOURCE_OBSERVED_ROLE_ROW"
        or type(compiled_specs) is not dict
    ):
        return None
    columns = table.get("columns")
    values_exact = row.get("values_exact")
    money_ordinals = (
        [
            ordinal
            for ordinal, column in enumerate(columns, start=1)
            if type(column) is dict and column.get("value_kind") == "MONEY"
        ]
        if type(columns) is list
        else []
    )
    unit = _explicit_unit(table, compiled_specs=compiled_specs)
    parsed_values = []
    parse_error = None
    if type(values_exact) is not list or len(money_ordinals) != 2 or (
        any(ordinal > len(values_exact) for ordinal in money_ordinals)
    ):
        parse_error = "PRIMARY_TEXT_CELL_PRESENTATION_LANE_AXIS_INCOMPLETE"
    else:
        try:
            parsed_values = [
                _money(values_exact[ordinal - 1]) for ordinal in money_ordinals
            ]
        except (TypeError, ValueError):
            parse_error = "PRIMARY_TEXT_CELL_PRESENTATION_MONEY_CELL_INVALID"
    source_mapping = {
        "unit": None if unit is None else unit[0],
        "values": parsed_values,
    }
    corroborated = False
    lane_receipts = []
    if parse_error is None and unit is not None:
        corroborated, comparison = _mapping_values_corroborate(
            source_mapping,
            mapped_aggregate,
            compiled_specs=compiled_specs,
        )
        lane_receipts = comparison["lane_receipts"]
    material = {
        "corroborated": corroborated,
        "lane_receipts": lane_receipts,
        "mapped_aggregate_item_mapping_id": mapped_aggregate.get(
            "item_mapping_id"
        ),
        "money_column_ordinals": money_ordinals,
        "parse_error": parse_error,
        "rule": (
            "EXACT_TEXT_CELL_PRIMARY_AGGREGATE_EQUALS_EXISTING_SOURCE_"
            "OBSERVED_RNID982_IN_THE_SAME_EXPLICIT_UNIT"
        ),
        "source_unit": None if unit is None else unit[0],
        "target_surface_receipt": target,
    }
    return {
        **material,
        "receipt_id": (
            "glicafv1:text-cell-primary:"
            + canonical_json_sha256_v1(material)
        ),
    }


def build_loan_interest_accrual_source_row_coverage_receipt_v1(
    *,
    sweep: Mapping[str, Any],
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Fail closed on every classified, total-control, or target-like row."""

    indexed = sweep.get("indexed_query_evidence")
    trials = sweep.get("trials")
    if (
        sweep.get("family_id") != FAMILY_ID
        or type(indexed) is not dict
        or type(indexed.get("candidate_dispositions")) is not list
        or type(trials) is not list
        or len(indexed["candidate_dispositions"]) != len(trials)
        or (
            compiled_specs is not None
            and compiled_specs.get("topology", {}).get("family_id")
            != FAMILY_ID
        )
    ):
        raise _error("Family-26 source-row coverage input is invalid")
    mapped = set()
    corroborated_note_totals = set()
    for trial in trials:
        for mapping in trial.get("mappings", []):
            for source_ref in mapping.get("source_refs", []):
                locator = source_ref.get("locator", {})
                mapped.add(
                    _source_row_identity(
                        source_sha256=locator.get("source_sha256"),
                        page_json_version_id=locator.get("page_json_version_id"),
                        section_id=locator.get("section_id"),
                        table_id=locator.get("table_id"),
                        row_ordinal=source_ref.get("row_ordinal"),
                        report_norm_id=mapping.get("report_norm_id"),
                    )
                )
        for candidate in trial.get("candidates", []):
            corroboration = candidate.get("closure_receipt", {}).get(
                "primary_detail_note_total_corroboration"
            )
            if type(corroboration) is not dict or (
                corroboration.get("corroborated") is not True
            ):
                continue
            for source_ref in corroboration.get("note_source_refs", []):
                locator = source_ref.get("locator", {})
                corroborated_note_totals.add(
                    _source_row_identity(
                        source_sha256=locator.get("source_sha256"),
                        page_json_version_id=locator.get("page_json_version_id"),
                        section_id=locator.get("section_id"),
                        table_id=locator.get("table_id"),
                        row_ordinal=source_ref.get("row_ordinal"),
                        report_norm_id=982,
                    )
                )

    source_rows: dict[str, dict[str, Any]] = {}
    violations: dict[str, dict[str, Any]] = {}
    for disposition in indexed["candidate_dispositions"]:
        cluster = disposition.get("cluster", {})
        document_ordinal = cluster.get("document_ordinal")
        pages = page_json_by_document.get(document_ordinal)
        if type(pages) is not dict:
            raise _error("Family-26 source-row coverage page frontier is absent")
        primary_receipt = cluster.get(
            "loan_interest_accrual_primary_query_receipt", {}
        )
        duplicate_primary_tables = (
            {
                (
                    observation["region"]["page_json_version_id"],
                    observation["region"]["section_id"],
                    observation["region"]["table_id"],
                )
                for observation in primary_receipt.get("observations", [])
            }
            if primary_receipt.get("rule")
            == "ROUNDED_LOWER_PRECISION_DUPLICATES_SELECT_HIGHEST_PRECISION_SOURCE"
            else set()
        )
        rejected_detail_tables = {
            (
                item["page_json_version_id"],
                item["section_id"],
                item["table_id"],
            )
            for item in cluster.get(
                "loan_interest_accrual_detail_query_receipt", {}
            ).get("rejected_population_scoped_tables", [])
        }
        for inventory_item in cluster.get("declared_money_table_inventory", []):
            classification = inventory_item.get("classification", {})
            page_version = inventory_item.get("page_json_version_id")
            section_id = inventory_item.get("section_id")
            table_id = inventory_item.get("table_id")
            page = pages.get(page_version)
            if type(page) is not dict:
                raise _error("Family-26 source-row coverage page JSON is absent")
            section, table = _source_table(
                page, section_id=section_id, table_id=table_id
            )
            rows = table.get("rows")
            money_ordinals = classification.get("money_column_ordinals", [])
            for hit in classification.get("role_hits", []):
                role = hit.get("role")
                report_norm_id = OWNED_ROLE_BINDINGS.get(role)
                row_ordinal = hit.get("row_ordinal")
                if (
                    type(rows) is not list
                    or type(row_ordinal) is not int
                    or not 1 <= row_ordinal <= len(rows)
                    or report_norm_id is None
                ):
                    raise _error("Family-26 classified source-row locator is invalid")
                row = rows[row_ordinal - 1]
                values = row.get("values_exact") if type(row) is dict else None
                visible = bool(
                    type(values) is list
                    and any(
                        ordinal <= len(values) and values[ordinal - 1] is not None
                        for ordinal in money_ordinals
                    )
                )
                identity = _source_row_identity(
                    source_sha256=cluster["source_sha256"],
                    page_json_version_id=page_version,
                    section_id=section_id,
                    table_id=table_id,
                    row_ordinal=row_ordinal,
                    report_norm_id=report_norm_id,
                )
                table_identity = (page_version, section_id, table_id)
                if identity in mapped:
                    coverage = "MAPPED_EXACT_SOURCE_ROW"
                elif identity in corroborated_note_totals:
                    coverage = "CORROBORATED_DUPLICATE_NOTE_TOTAL"
                elif role == "INTEREST_FEE_RECEIVABLES" and (
                    table_identity in duplicate_primary_tables
                ):
                    coverage = "CORROBORATED_DUPLICATE_PRIMARY_PRESENTATION"
                elif not visible:
                    coverage = "BLANK_STRUCTURAL_CONTEXT_HEADING"
                elif classification.get("typed_control_disposition") is not None:
                    coverage = "TYPED_CONTROL_OUTSIDE_FAMILY26"
                elif table_identity in rejected_detail_tables:
                    coverage = "REJECTED_NONLOCAL_ROW_POPULATION_CONTEXT"
                elif (
                    role == "INTEREST_FEE_RECEIVABLES"
                    and classification.get("owner_visible") is not True
                    and not classification.get("context_roles")
                ):
                    coverage = "REJECTED_NONLOCAL_TOTAL_CONTROL_CONTEXT"
                elif (
                    classification.get("owner_visible") is not True
                    and not classification.get("context_roles")
                ):
                    coverage = "VIOLATION_UNACCOUNTED_NONLOCAL_CHILD_ROLE_ROW"
                else:
                    coverage = "VIOLATION_UNACCOUNTED_SCHEMA_ROLE_ROW"
                item = {
                    "context_resolution_kind": classification.get(
                        "context_resolution_kind"
                    ),
                    "coverage": coverage,
                    "document_ordinal": document_ordinal,
                    "hierarchy_path_exact": canonical_clone_v1(
                        row.get("hierarchy_path_exact", [])
                    ),
                    "inventory_disposition": inventory_item.get("disposition"),
                    "label_exact": row.get("label_exact"),
                    "page_json_version_id": page_version,
                    "physical_page": inventory_item.get("physical_page"),
                    "report_norm_id": report_norm_id,
                    "role": role,
                    "row_id": row.get("row_id", f"r{row_ordinal}"),
                    "row_ordinal": row_ordinal,
                    "section_id": section_id,
                    "section_title_exact": section.get("title_exact"),
                    "source_logical_name": cluster["source_logical_name"],
                    "source_sha256": cluster["source_sha256"],
                    "table_id": table_id,
                    "table_title_exact": table.get("title_exact"),
                    "typed_control_disposition": classification.get(
                        "typed_control_disposition"
                    ),
                    "values_exact": canonical_clone_v1(values),
                }
                item_id = canonical_json_sha256_v1(item)
                source_rows.setdefault(item_id, item)
                if coverage.startswith("VIOLATION_"):
                    violations.setdefault(item_id, item)

    detail_total_controls = _candidate_detail_total_control_rows(
        trials=trials, page_json_by_document=page_json_by_document
    )
    for item in detail_total_controls:
        item_id = canonical_json_sha256_v1(item)
        source_rows.setdefault(item_id, item)
    candidate_table_total_axis = _candidate_table_total_disposition_rows(
        trials=trials,
        page_json_by_document=page_json_by_document,
        detail_total_controls=detail_total_controls,
    )
    for item in candidate_table_total_axis:
        if item["coverage"].startswith("VIOLATION_"):
            item_id = canonical_json_sha256_v1(item)
            violations.setdefault(item_id, item)

    target_like_exclusions: dict[str, dict[str, Any]] = {}
    for trial in trials:
        for candidate in trial.get("candidates", []):
            for source_only in candidate.get("closure_receipt", {}).get(
                "source_only_unmapped_rows", []
            ):
                source_ref = source_only.get("source_ref", {})
                target_surface_receipt = _target_like_receivable_source_surface(
                    label_exact=source_ref.get("label_exact"),
                    hierarchy_path_exact=source_ref.get(
                        "hierarchy_path_exact"
                    ),
                )
                if target_surface_receipt is None:
                    continue
                target_surface_exact = target_surface_receipt[
                    "surface_exact"
                ]
                allowed = _allowed_interest_support_receivable(
                    label_exact=target_surface_exact,
                    hierarchy_path_exact=source_ref.get(
                        "hierarchy_path_exact"
                    ),
                )
                locator = source_ref.get("locator", {})
                pages = page_json_by_document.get(trial.get("document_ordinal"), {})
                page = pages.get(locator.get("page_json_version_id"))
                source_values = None
                if type(page) is dict:
                    try:
                        _, table = _source_table(
                            page,
                            section_id=locator.get("section_id"),
                            table_id=locator.get("table_id"),
                        )
                        rows = table.get("rows")
                        row_ordinal = source_ref.get("row_ordinal")
                        if (
                            type(rows) is list
                            and type(row_ordinal) is int
                            and 1 <= row_ordinal <= len(rows)
                        ):
                            source_values = canonical_clone_v1(
                                rows[row_ordinal - 1].get("values_exact")
                            )
                    except GeminiJsonLoanInterestAccrualClassificationFamilyV1Error:
                        source_values = None
                item = {
                    "allowed_non_family_context": allowed,
                    "document_ordinal": trial.get("document_ordinal"),
                    "hierarchy_path_exact": canonical_clone_v1(
                        source_ref.get("hierarchy_path_exact", [])
                    ),
                    "label_exact": source_ref.get("label_exact"),
                    "source_ref": canonical_clone_v1(source_ref),
                    "source_values_exact": source_values,
                    "target_surface_origin": target_surface_receipt["origin"],
                    "target_surface_exact": target_surface_exact,
                    "target_surface_value_ordinal": target_surface_receipt[
                        "value_ordinal"
                    ],
                    "rule": (
                        "INTEREST_SUPPORT_PROGRAM_RECEIVABLE_INSIDE_GENERAL_"
                        "RECEIVABLES_IS_NOT_ACCRUED_INTEREST_OR_FEE"
                        if allowed
                        else "UNBOUND_TARGET_LIKE_SOURCE_ROW"
                    ),
                }
                item_id = canonical_json_sha256_v1(item)
                target_like_exclusions.setdefault(item_id, item)
                if not allowed:
                    violations.setdefault(item_id, item)

    source_row_axis = [source_rows[key] for key in sorted(source_rows)]
    exclusion_axis = [
        target_like_exclusions[key] for key in sorted(target_like_exclusions)
    ]
    accounted_row_locators = {
        (
            item["source_sha256"],
            item["page_json_version_id"],
            item["section_id"],
            item["table_id"],
            item["row_ordinal"],
        )
        for item in source_row_axis
    }
    cluster_by_ordinal = {
        disposition.get("cluster", {}).get("document_ordinal"): disposition.get(
            "cluster", {}
        )
        for disposition in indexed["candidate_dispositions"]
    }
    aggregate_mappings_by_ordinal = {
        trial.get("document_ordinal"): [
            mapping
            for mapping in trial.get("mappings", [])
            if mapping.get("report_norm_id") == 982
            and mapping.get("role") == "INTEREST_FEE_RECEIVABLES"
        ]
        for trial in trials
        if type(trial) is dict
    }
    physical_page_by_version = {
        item.get("page_json_version_id"): item.get("physical_page")
        for item in indexed.get("selected_page_axis", [])
        if type(item) is dict
    }
    raw_target_rows: dict[str, dict[str, Any]] = {}
    for document_ordinal, pages in page_json_by_document.items():
        cluster = cluster_by_ordinal.get(document_ordinal)
        if type(cluster) is not dict or type(pages) is not dict:
            raise _error("Family-26 raw source-row coverage frontier is invalid")
        source_sha256 = cluster.get("source_sha256")
        source_logical_name = cluster.get("source_logical_name")
        inventory_by_table = {
            (
                item.get("page_json_version_id"),
                item.get("section_id"),
                item.get("table_id"),
            ): item
            for item in cluster.get("declared_money_table_inventory", [])
            if type(item) is dict
        }
        for page_json_version_id, page in pages.items():
            if type(page) is not dict:
                raise _error("Family-26 raw source-row page JSON is invalid")
            for section_ordinal, section in enumerate(
                page.get("sections", []), start=1
            ):
                if type(section) is not dict:
                    continue
                section_id = f"s{section_ordinal}"
                for table_ordinal, table in enumerate(
                    section.get("tables", []), start=1
                ):
                    if type(table) is not dict:
                        continue
                    table_id = f"t{table_ordinal}"
                    for row_ordinal, row in enumerate(
                        table.get("rows", []), start=1
                    ):
                        if type(row) is not dict:
                            continue
                        target_surface_receipt = (
                            _target_like_receivable_source_surface(
                                label_exact=row.get("label_exact"),
                                hierarchy_path_exact=row.get(
                                    "hierarchy_path_exact"
                                ),
                                columns=table.get("columns"),
                                values_exact=row.get("values_exact"),
                            )
                        )
                        if target_surface_receipt is None:
                            continue
                        target_surface_exact = target_surface_receipt[
                            "surface_exact"
                        ]
                        locator = (
                            source_sha256,
                            page_json_version_id,
                            section_id,
                            table_id,
                            row_ordinal,
                        )
                        inventory_item = inventory_by_table.get(
                            (page_json_version_id, section_id, table_id), {}
                        )
                        duplicate_representation_ref = None
                        for adjacent_ordinal in (
                            row_ordinal - 1,
                            row_ordinal + 1,
                        ):
                            if not 1 <= adjacent_ordinal <= len(table["rows"]):
                                continue
                            adjacent = table["rows"][adjacent_ordinal - 1]
                            adjacent_locator = (
                                source_sha256,
                                page_json_version_id,
                                section_id,
                                table_id,
                                adjacent_ordinal,
                            )
                            adjacent_target_receipt = (
                                _target_like_receivable_source_surface(
                                    label_exact=adjacent.get("label_exact"),
                                    hierarchy_path_exact=adjacent.get(
                                        "hierarchy_path_exact"
                                    ),
                                    columns=table.get("columns"),
                                    values_exact=adjacent.get("values_exact"),
                                )
                                if type(adjacent) is dict
                                else None
                            )
                            adjacent_target_surface = (
                                adjacent_target_receipt["surface_exact"]
                                if adjacent_target_receipt is not None
                                else None
                            )
                            if (
                                type(adjacent) is dict
                                and adjacent_locator in accounted_row_locators
                                and adjacent_target_surface is not None
                                and normalize_vietnamese_anchor_v1(
                                    adjacent_target_surface
                                )
                                == normalize_vietnamese_anchor_v1(
                                    target_surface_exact
                                )
                                and same_typed_json_v1(
                                    row.get("hierarchy_path_exact"),
                                    adjacent.get("hierarchy_path_exact"),
                                )
                                and same_typed_json_v1(
                                    row.get("values_exact"),
                                    adjacent.get("values_exact"),
                                )
                            ):
                                duplicate_representation_ref = {
                                    "label_exact": adjacent.get("label_exact"),
                                    "row_id": adjacent.get(
                                        "row_id", f"r{adjacent_ordinal}"
                                    ),
                                    "row_ordinal": adjacent_ordinal,
                                    "target_surface_exact": (
                                        adjacent_target_surface
                                    ),
                                }
                                break
                        aggregate_mappings = aggregate_mappings_by_ordinal.get(
                            document_ordinal, []
                        )
                        primary_text_cell_corroboration = (
                            _text_cell_primary_presentation_corroboration(
                                section=section,
                                table=table,
                                row=row,
                                mapped_aggregate=(
                                    aggregate_mappings[0]
                                    if len(aggregate_mappings) == 1
                                    else None
                                ),
                                compiled_specs=compiled_specs,
                            )
                        )
                        if locator in accounted_row_locators:
                            coverage = "ACCOUNTED_CLASSIFIED_SOURCE_ROW"
                            context_rule = (
                                "CLASSIFIED_SOURCE_ROW_ACCOUNTED_ON_SCHEMA_AXIS"
                            )
                            context_evidence_exact = [row.get("label_exact")]
                        elif duplicate_representation_ref is not None:
                            coverage = (
                                "CORROBORATED_ADJACENT_DUPLICATE_SOURCE_"
                                "REPRESENTATION"
                            )
                            context_rule = (
                                "ADJACENT_ROWS_HAVE_IDENTICAL_HIERARCHY_AND_"
                                "VALUES_AND_THE_CANONICAL_LABEL_ROW_IS_"
                                "ACCOUNTED_ON_THE_SCHEMA_AXIS"
                            )
                            context_evidence_exact = [
                                target_surface_exact,
                                duplicate_representation_ref["label_exact"],
                            ]
                        elif (
                            type(primary_text_cell_corroboration) is dict
                            and primary_text_cell_corroboration.get(
                                "corroborated"
                            )
                            is True
                        ):
                            coverage = (
                                "CORROBORATED_TEXT_CELL_PRIMARY_PRESENTATION"
                            )
                            context_rule = primary_text_cell_corroboration[
                                "rule"
                            ]
                            context_evidence_exact = [target_surface_exact]
                        else:
                            context_disposition = (
                                _raw_target_context_disposition(
                                    label_exact=target_surface_exact,
                                    hierarchy_path_exact=row.get(
                                        "hierarchy_path_exact"
                                    ),
                                    section_title_exact=section.get(
                                        "title_exact"
                                    ),
                                    table_title_exact=table.get("title_exact"),
                                    inventory_disposition=inventory_item.get(
                                        "disposition"
                                    ),
                                    section_narratives_exact=section.get(
                                        "narratives_exact"
                                    ),
                                    target_surface_origin=(
                                        target_surface_receipt["origin"]
                                    ),
                                    row_label_context_exact=row.get(
                                        "label_exact"
                                    ),
                                )
                            )
                            coverage = context_disposition["coverage"]
                            context_rule = context_disposition["rule"]
                            context_evidence_exact = context_disposition[
                                "context_evidence_exact"
                            ]
                        item = {
                            "context_disposition_rule": context_rule,
                            "context_evidence_exact": canonical_clone_v1(
                                context_evidence_exact
                            ),
                            "coverage": coverage,
                            "document_ordinal": document_ordinal,
                            "duplicate_source_row_representation_ref": (
                                duplicate_representation_ref
                            ),
                            "hierarchy_path_exact": canonical_clone_v1(
                                row.get("hierarchy_path_exact", [])
                            ),
                            "inventory_disposition": inventory_item.get(
                                "disposition"
                            ),
                            "label_exact": row.get("label_exact"),
                            "page_json_version_id": page_json_version_id,
                            "physical_page": physical_page_by_version.get(
                                page_json_version_id
                            ),
                            "primary_text_cell_corroboration": (
                                primary_text_cell_corroboration
                            ),
                            "row_id": row.get("row_id", f"r{row_ordinal}"),
                            "row_ordinal": row_ordinal,
                            "section_id": section_id,
                            "section_title_exact": section.get("title_exact"),
                            "source_logical_name": source_logical_name,
                            "source_sha256": source_sha256,
                            "table_id": table_id,
                            "table_title_exact": table.get("title_exact"),
                            "target_surface_origin": target_surface_receipt[
                                "origin"
                            ],
                            "target_surface_exact": target_surface_exact,
                            "target_surface_value_ordinal": (
                                target_surface_receipt["value_ordinal"]
                            ),
                            "values_exact": canonical_clone_v1(
                                row.get("values_exact")
                            ),
                        }
                        item_id = canonical_json_sha256_v1(item)
                        raw_target_rows.setdefault(item_id, item)
                        if coverage.startswith("VIOLATION_"):
                            violations.setdefault(item_id, item)

    raw_target_row_axis = [
        raw_target_rows[key] for key in sorted(raw_target_rows)
    ]
    violation_axis = [violations[key] for key in sorted(violations)]
    disposition_counts = {
        disposition: sum(item["coverage"] == disposition for item in source_row_axis)
        for disposition in sorted({item["coverage"] for item in source_row_axis})
    }
    material = {
        "candidate_table_total_disposition_counts": {
            disposition: sum(
                item["coverage"] == disposition
                for item in candidate_table_total_axis
            )
            for disposition in sorted(
                {item["coverage"] for item in candidate_table_total_axis}
            )
        },
        "candidate_table_total_row_axis": candidate_table_total_axis,
        "candidate_table_total_row_axis_sha256": canonical_json_sha256_v1(
            candidate_table_total_axis
        ),
        "disposition_counts": disposition_counts,
        "family_id": FAMILY_ID,
        "format_version": SOURCE_ROW_COVERAGE_FORMAT_VERSION,
        "raw_target_like_disposition_counts": {
            disposition: sum(
                item["coverage"] == disposition for item in raw_target_row_axis
            )
            for disposition in sorted(
                {item["coverage"] for item in raw_target_row_axis}
            )
        },
        "raw_target_like_row_axis": raw_target_row_axis,
        "raw_target_like_row_axis_sha256": canonical_json_sha256_v1(
            raw_target_row_axis
        ),
        "source_row_axis": source_row_axis,
        "source_row_axis_sha256": canonical_json_sha256_v1(source_row_axis),
        "target_like_non_family_exclusion_axis": exclusion_axis,
        "target_like_non_family_exclusion_axis_sha256": (
            canonical_json_sha256_v1(exclusion_axis)
        ),
        "violation_axis": violation_axis,
        "violation_count": len(violation_axis),
    }
    receipt = {
        **material,
        "receipt_id": "glicafv1:source-row-coverage:"
        + canonical_json_sha256_v1(material),
    }
    if violation_axis:
        raise _error(
            f"Family-26 source-row coverage has {len(violation_axis)} violation(s)"
        )
    return receipt


def _mapping_source_axis(
    sweep: Any, *, require_family_id: str
) -> list[dict[str, Any]]:
    if (
        type(sweep) is not dict
        or sweep.get("family_id") != require_family_id
        or type(sweep.get("corpus_manifest_index_id")) is not str
        or type(sweep.get("trials")) is not list
    ):
        raise _error("cross-family sweep envelope is invalid")
    axis: dict[str, dict[str, Any]] = {}
    for trial in sweep["trials"]:
        mappings = trial.get("mappings") if type(trial) is dict else None
        if type(mappings) is not list:
            raise _error("cross-family trial mapping axis is invalid")
        for mapping in mappings:
            report_norm_id = mapping.get("report_norm_id") if type(mapping) is dict else None
            source_refs = mapping.get("source_refs") if type(mapping) is dict else None
            if type(report_norm_id) is not int or type(source_refs) is not list or not source_refs:
                raise _error("cross-family mapping source provenance is invalid")
            for source_ref in source_refs:
                locator = source_ref.get("locator") if type(source_ref) is dict else None
                if (
                    type(locator) is not dict
                    or _SHA256.fullmatch(locator.get("source_sha256", "")) is None
                    or _PAGE_VERSION.fullmatch(locator.get("page_json_version_id", ""))
                    is None
                    or _SECTION_ID.fullmatch(locator.get("section_id", "")) is None
                    or _TABLE_ID.fullmatch(locator.get("table_id", "")) is None
                    or type(source_ref.get("row_id")) is not str
                    or not source_ref["row_id"]
                    or type(source_ref.get("row_ordinal")) is not int
                    or source_ref["row_ordinal"] <= 0
                ):
                    raise _error("cross-family source-row locator is invalid")
                item = {
                    "page_json_version_id": locator["page_json_version_id"],
                    "physical_page": locator.get("physical_page"),
                    "report_norm_id": report_norm_id,
                    "row_id": source_ref["row_id"],
                    "row_ordinal": source_ref["row_ordinal"],
                    "section_id": locator["section_id"],
                    "source_sha256": locator["source_sha256"],
                    "table_id": locator["table_id"],
                }
                identity = canonical_json_sha256_v1(item)
                axis.setdefault(identity, item)
    return [axis[key] for key in sorted(axis)]


def _trial_source_axis(sweep: Mapping[str, Any]) -> list[dict[str, Any]]:
    axis = []
    for ordinal, trial in enumerate(sweep.get("trials", []), start=1):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or _SHA256.fullmatch(trial.get("source_sha256", "")) is None
            or type(trial.get("source_logical_name")) is not str
            or not trial["source_logical_name"]
        ):
            raise _error("cross-family trial source axis is invalid")
        axis.append(
            {
                "document_ordinal": ordinal,
                "source_logical_name": trial["source_logical_name"],
                "source_sha256": trial["source_sha256"],
            }
        )
    if not axis:
        raise _error("cross-family trial source axis is empty")
    return axis


def build_loan_interest_accrual_cross_family_disjointness_receipt_v1(
    *, f26_sweep: Any, other_assets_sweep: Any
) -> dict[str, Any]:
    """Require an exact same-corpus Family-22 ownership handoff."""

    f26_axis = _mapping_source_axis(f26_sweep, require_family_id=FAMILY_ID)
    f22_axis = _mapping_source_axis(
        other_assets_sweep, require_family_id=LEGACY_OWNER_FAMILY_ID
    )
    f26_trial_source_axis = _trial_source_axis(f26_sweep)
    f22_trial_source_axis = _trial_source_axis(other_assets_sweep)
    if (
        f26_sweep["corpus_manifest_index_id"]
        != other_assets_sweep["corpus_manifest_index_id"]
        or not same_typed_json_v1(f26_trial_source_axis, f22_trial_source_axis)
    ):
        raise _error("cross-family sweeps do not bind the same exact source corpus")
    f26_mapping_ids = {
        mapping["report_norm_id"]
        for trial in f26_sweep["trials"]
        for mapping in trial["mappings"]
    }
    if not f26_mapping_ids or not f26_mapping_ids <= OWNED_REPORT_NORM_IDS:
        raise _error("Family-26 emitted outside its five-ID ownership frontier")
    legacy_owned_axis = [
        item for item in f22_axis if item["report_norm_id"] in OWNED_REPORT_NORM_IDS
    ]
    if legacy_owned_axis:
        raise _error(
            "Family-22 ownership handoff is incomplete for report normalization IDs 982--986"
        )
    f26_identities = {canonical_json_sha256_v1(item) for item in f26_axis}
    f22_identities = {canonical_json_sha256_v1(item) for item in f22_axis}
    overlaps = sorted(f26_identities.intersection(f22_identities))
    if overlaps:
        raise _error("Family-22 and Family-26 exact source-row axes overlap")
    material = {
        "family_22_mapping_source_axis_count": len(f22_axis),
        "family_22_mapping_source_axis_sha256": canonical_json_sha256_v1(f22_axis),
        "family_22_sweep_id": other_assets_sweep.get("sweep_id"),
        "family_26_mapping_source_axis_count": len(f26_axis),
        "family_26_mapping_source_axis_sha256": canonical_json_sha256_v1(f26_axis),
        "family_26_sweep_id": f26_sweep.get("sweep_id"),
        "format_version": CROSS_FAMILY_RECEIPT_FORMAT_VERSION,
        "overlap_count": 0,
        "owned_report_norm_ids": sorted(OWNED_REPORT_NORM_IDS),
        "rule": "SAME_CORPUS_NO_LEGACY_OWNED_ID_AND_EXACT_SOURCE_PAGE_TABLE_ROW_RNID_DISJOINT",
        "trial_source_axis_count": len(f26_trial_source_axis),
        "trial_source_axis_sha256": canonical_json_sha256_v1(
            f26_trial_source_axis
        ),
    }
    return {
        **material,
        "receipt_id": "glicacfdv1:receipt:" + canonical_json_sha256_v1(material),
    }


def validate_loan_interest_accrual_cross_family_disjointness_receipt_v1(
    value: Any, *, f26_sweep: Any, other_assets_sweep: Any
) -> dict[str, Any]:
    """Replay one cross-family disjointness receipt exactly."""

    expected = build_loan_interest_accrual_cross_family_disjointness_receipt_v1(
        f26_sweep=f26_sweep, other_assets_sweep=other_assets_sweep
    )
    if type(value) is not dict or not same_typed_json_v1(value, expected):
        raise _error("Family-26 cross-family disjointness receipt drifted")
    return expected
