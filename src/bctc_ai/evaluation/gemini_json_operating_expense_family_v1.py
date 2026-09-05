"""Family-36 source adapter for operating-expense disclosures.

The shared multi-table evaluator remains the accounting authority.  This
adapter only supplies a missing local unit when an otherwise unitless note's
printed total exactly corroborates the same document's primary income-
statement operating-expense row.  All changes are made to a private clone;
source blanks are preserved and values are never scaled or backsolved.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.evaluation.gemini_json_customer_deposit_family_v1 import (
    _document_unit_context_axis,
)
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
    _duration_multitable_lane_axis,
    _extract_table_local_records,
    _local_equation,
    _multitable_global_records,
    _source_money,
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

FAMILY_ID = "OPERATING_EXPENSE"
ADAPTER_FORMAT_VERSION = "GEMINI_JSON_OPERATING_EXPENSE_FAMILY_ADAPTER_V1"
SOURCE_REPAIR_FORMAT_VERSION = "GEMINI_JSON_OPERATING_EXPENSE_AUTHENTICATED_SOURCE_REPAIR_SPEC_V1"
SOURCE_ROW_COVERAGE_FORMAT_VERSION = "OPERATING_EXPENSE_SOURCE_ROW_COVERAGE_V1"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_DECLARATIVE_OPERATING_EXPENSE_"
    "MULTITABLE_HIERARCHICAL_EXACT_SAME_DOCUMENT_PRIMARY_STATEMENT_UNIT_"
    "CORROBORATION_EXACT_PDF_VISIBLE_DASH_REPAIR_PRIVATE_CLONE_ONLY_"
    "UNIQUE_EXACT_OWNER_WHOLE_MONEY_TABLE_REGION_RECOVERY_"
    "EXACT_ALL_LANES_RAW_NULL_VALIDATION_ROLE_OMISSION_PRIVATE_COMPILED_CLONE_"
    "NO_BLANK_ZERO_NO_NUMERIC_BACKSOLVE_"
    "NO_MAGNITUDE_UNIT_INFERENCE_NO_BANK_FILE_YEAR_PAGE_VALUE_ROUTING_"
    "PROPOSAL_ONLY_" + SHARED_CLAIM_BOUNDARY
)

_UNIT_SURFACE = {"MILLION_VND": "Triệu đồng", "VND": "VND"}
_PAGE_VERSION = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_SECTION_ID = re.compile(r"s[1-9][0-9]*\Z")
_TABLE_ID = re.compile(r"t[1-9][0-9]*\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class GeminiJsonOperatingExpenseFamilyV1Error(ValueError):
    """Family-36 source evidence, candidate, or replay drifted."""


def _error(message: str) -> GeminiJsonOperatingExpenseFamilyV1Error:
    return GeminiJsonOperatingExpenseFamilyV1Error(message)


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
        != (
            "ONLY_PDF_VISIBLE_ACCOUNTING_DASH_CORRECTS_NULL_OR_FALSE_NUMERIC_"
            "CELL_NO_BLANK_ZERO_INFERENCE"
        )
        or value.get("render_contract") != render_contract
        or type(value.get("repairs")) is not list
        or not value["repairs"]
    ):
        raise _error("operating-expense authenticated source-repair spec is invalid")
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
            or not (
                (
                    repair.get("repair_kind") == "MONEY_CELL_VISIBLE_DASH"
                    and repair.get("before_exact") is None
                )
                or (
                    repair.get("repair_kind") == "MONEY_CELL_FALSE_NUMERIC_PDF_VISIBLE_DASH"
                    and type(repair.get("before_exact")) is str
                    and bool(repair["before_exact"])
                    and repair["before_exact"] != "-"
                )
            )
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
            or _PAGE_VERSION.fullmatch(locator.get("page_json_version_id", "")) is None
            or type(locator.get("physical_page")) is not int
            or locator["physical_page"] <= 0
            or type(locator.get("row_ordinal")) is not int
            or locator["row_ordinal"] <= 0
            or type(locator.get("column_ordinal")) is not int
            or locator["column_ordinal"] <= 0
            or _SECTION_ID.fullmatch(locator.get("section_id", "")) is None
            or _TABLE_ID.fullmatch(locator.get("table_id", "")) is None
            or type(source) is not dict
            or set(source) != {"source_logical_name", "source_sha256", "source_size_bytes"}
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
            or set(crop) != {"bbox_pixels_xyxy", "pixel_height", "pixel_width", "rgb_sha256"}
            or type(bbox) is not list
            or len(bbox) != 4
            or any(type(coordinate) is not int for coordinate in bbox)
            or not (0 <= bbox[0] < bbox[2] <= render["pixel_width"])
            or not (0 <= bbox[1] < bbox[3] <= render["pixel_height"])
            or crop.get("pixel_width") != bbox[2] - bbox[0]
            or crop.get("pixel_height") != bbox[3] - bbox[1]
            or _SHA256.fullmatch(crop.get("rgb_sha256", "")) is None
        ):
            raise _error("operating-expense authenticated source repair is invalid")
        material = {
            key: canonical_clone_v1(item) for key, item in repair.items() if key != "repair_id"
        }
        if repair.get("repair_id") != (
            "gjoefav1:source-repair:" + canonical_json_sha256_v1(material)
        ):
            raise _error("operating-expense source-repair identity drifted")
        identity = (
            source["source_sha256"],
            locator["page_json_version_id"],
            locator["section_id"],
            locator["table_id"],
            locator["row_ordinal"],
            locator["column_ordinal"],
        )
        if identity in identities:
            raise _error("operating-expense source-repair cell axis is duplicate")
        identities.add(identity)
        checked.append(canonical_clone_v1(repair))
    if value.get("repair_axis_sha256") != canonical_json_sha256_v1(checked):
        raise _error("operating-expense source-repair axis seal drifted")
    return checked


def compile_gemini_json_operating_expense_family_specs_v1(
    topology_spec: Any,
    evaluation_spec: Any,
    schema_binding_spec: Any,
    source_repair_spec: Any | None = None,
) -> dict[str, Any]:
    """Compile and seal the Family-36 declarative frontier."""

    try:
        compiled = compile_gemini_json_multitable_hierarchical_family_specs_v1(
            topology_spec, evaluation_spec, schema_binding_spec
        )
    except ValueError as exc:
        raise _error("operating-expense declarative family specs are invalid") from exc
    expected_bindings = {
        "ADMIN_EXPENSE",
        "ASSET_EXPENSE",
        "DEPOSIT_INSURANCE_EXPENSE",
        "DEPRECIATION_EXPENSE",
        "EMPLOYEE_BENEFIT",
        "EMPLOYEE_EXPENSE",
        "LONG_TERM_BAD_DEBT_PROVISION",
        "OTHER_ASSET_PROVISION",
        "OTHER_EMPLOYEE_EXPENSE",
        "OTHER_OPERATING_EXPENSE",
        "PAYROLL_CONTRIBUTIONS",
        "SALARY_ALLOWANCE",
        "TAX_FEES",
        "TRAVEL_EXPENSE",
        "UNION_ACTIVITY_EXPENSE",
    }
    accepted_units = {
        item["canonical_unit"]
        for item in compiled.get("unit_bindings", [])
        if item.get("accepted") is True
    }
    if (
        compiled.get("topology", {}).get("family_id") != FAMILY_ID
        or compiled.get("evaluation", {}).get("family_id") != FAMILY_ID
        or compiled.get("schema", {}).get("family_id") != FAMILY_ID
        or set(compiled.get("bindings", {})) != expected_bindings
        or set(compiled.get("aggregate_duplicate_roles", [])) != expected_bindings
        or accepted_units != {"MILLION_VND", "VND"}
        or compiled.get("owner_complete_population_policy") != "EXACT_OWNER_WHOLE_MONEY_TABLE"
        or compiled.get("source_presentation_rounding_policy")
        != "INDEPENDENT_DISPLAY_UNIT_ROUNDING_INTERVAL_ALL_EQUATIONS"
        or compiled.get("source_total_blank_lane_control_policy")
        != "OBSERVED_LANES_EXACT_REMAINDER_BLANK"
    ):
        raise _error("operating-expense compiled family frontier is invalid")
    compiled["operating_expense_source_repairs"] = (
        [] if source_repair_spec is None else _validate_source_repairs(source_repair_spec)
    )
    compiled["operating_expense_source_repair_spec_sha256"] = (
        None if source_repair_spec is None else canonical_json_sha256_v1(source_repair_spec)
    )
    compiled["operating_expense_adapter_format_version"] = ADAPTER_FORMAT_VERSION
    return compiled


def _source_table(
    page_json: Mapping[str, Any], *, section_id: str, table_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        section = page_json["sections"][int(section_id[1:]) - 1]
        table = section["tables"][int(table_id[1:]) - 1]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise _error("operating-expense source locator does not resolve one table") from exc
    if type(section) is not dict or type(table) is not dict:
        raise _error("operating-expense source table is invalid")
    return section, table


def _is_last_source_table_on_page(
    page_json: Mapping[str, Any], *, section_id: str, table_id: str
) -> bool:
    """Return whether a table is followed by no other source table on its page."""

    sections = page_json.get("sections")
    try:
        section_ordinal = int(section_id[1:])
        table_ordinal = int(table_id[1:])
    except (TypeError, ValueError):
        return False
    if (
        type(sections) is not list
        or not 1 <= section_ordinal <= len(sections)
        or type(sections[section_ordinal - 1]) is not dict
    ):
        return False
    tables = sections[section_ordinal - 1].get("tables")
    if type(tables) is not list or table_ordinal != len(tables):
        return False
    return all(
        type(section) is dict and type(section.get("tables")) is list and section["tables"] == []
        for section in sections[section_ordinal:]
    )


def _receiver_continuation_narratives(
    section: Mapping[str, Any],
) -> list[str] | None:
    """Accept only absent or exact report-form boilerplate receiver narratives."""

    narratives = section.get("narratives_exact")
    if narratives is None:
        return []
    if type(narratives) is not list or any(type(item) is not str for item in narratives):
        return None
    if any(not _normalized(item).startswith("mau so ") for item in narratives):
        return None
    return canonical_clone_v1(narratives)


def _money_column_ordinals(table: Mapping[str, Any]) -> list[int]:
    columns = table.get("columns")
    return [
        ordinal
        for ordinal, column in enumerate(columns if type(columns) is list else [], start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]


def _observed_vector(row: Mapping[str, Any], money_ordinals: Sequence[int]) -> list[int] | None:
    values = row.get("values_exact")
    if type(values) is not list or any(
        type(ordinal) is not int or ordinal <= 0 or ordinal > len(values)
        for ordinal in money_ordinals
    ):
        return None
    result = []
    for ordinal in money_ordinals:
        try:
            cell = _source_money(values[ordinal - 1])
        except (TypeError, ValueError):
            return None
        coefficient = cell.get("coefficient")
        if type(coefficient) is not int:
            return None
        result.append(coefficient)
    return result if result else None


def _target_total_observation(
    *,
    pages: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    observations = []
    for region in regions:
        page = pages.get(region.get("page_json_version_id"))
        if type(page) is not dict:
            return None
        section, table = _source_table(
            page, section_id=region["section_id"], table_id=region["table_id"]
        )
        classification = classify_gemini_json_multitable_hierarchical_table_v1(
            page, section, table, compiled_specs=compiled_specs
        )
        money_ordinals = classification.get("money_column_ordinals")
        rows = table.get("rows")
        if (
            type(money_ordinals) is not list
            or len(money_ordinals) != 2
            or type(rows) is not list
            or classification.get("family_presence_anchor_visible") is not True
        ):
            continue
        for total in classification.get("total_rows", []):
            row_ordinal = total.get("row_ordinal") if type(total) is dict else None
            if (
                type(row_ordinal) is not int
                or total.get("row_kind") != "TOTAL"
                or not 1 <= row_ordinal <= len(rows)
            ):
                continue
            vector = _observed_vector(rows[row_ordinal - 1], money_ordinals)
            if vector is None:
                continue
            observations.append(
                {
                    "locator": {
                        key: region[key]
                        for key in (
                            "page_json_version_id",
                            "physical_page",
                            "section_id",
                            "table_id",
                        )
                    },
                    "money_column_ordinals": canonical_clone_v1(money_ordinals),
                    "row_ordinal": row_ordinal,
                    "vector": vector,
                }
            )
    return observations[0] if len(observations) == 1 else None


def _parent_aliases(compiled_specs: Mapping[str, Any]) -> set[str]:
    return {_normalized(alias) for alias in compiled_specs["topology"]["parent"]["aliases"]}


def _is_parent_label(value: Any, *, compiled_specs: Mapping[str, Any]) -> bool:
    return bool(
        type(value) is str
        and _without_leading_ordinal(_normalized(value)) in _parent_aliases(compiled_specs)
    )


def _local_explicit_unit(
    table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any] | None:
    axis = _unit_axis(table, compiled_specs=compiled_specs, document_unit_context=None)
    canonical_unit = axis.get("canonical_unit")
    if axis.get("complete") is not True or canonical_unit not in _UNIT_SURFACE:
        return None
    if not any(
        item.get("canonical_unit") == canonical_unit and item.get("accepted") is True
        for item in compiled_specs["unit_bindings"]
    ):
        return None
    return {
        "canonical_unit": canonical_unit,
        "evidence": canonical_clone_v1(axis),
        "rule": "LOCAL_PRIMARY_STATEMENT_TABLE_EXPLICIT_ACCEPTED_UNIT",
    }


def _unique_primary_statement_unit_context(
    *,
    pages: Mapping[str, dict[str, Any]],
    selected_version_ids: set[str],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Bind one explicit unit shared by all unit-bearing primary tables.

    Primary tables with no unit evidence do not vote. Any visible undeclared,
    incomplete, or conflicting unit evidence vetoes the context. Values,
    magnitude, page distance, and the target note never participate.
    """

    evidence_axis = []
    for page_json_version_id, page in sorted(pages.items()):
        if (
            page_json_version_id not in selected_version_ids
            or type(page) is not dict
            or page.get("status") != "PRIMARY_FINANCIAL_STATEMENT"
        ):
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
                if type(table) is not dict or not _money_column_ordinals(table):
                    continue
                axis = _unit_axis(
                    table,
                    compiled_specs=compiled_specs,
                    document_unit_context=None,
                )
                visible_evidence = [
                    *axis.get("evidence", []),
                    *axis.get("undeclared_evidence", []),
                ]
                if not visible_evidence:
                    continue
                canonical_unit = axis.get("canonical_unit")
                if (
                    axis.get("complete") is not True
                    or canonical_unit not in _UNIT_SURFACE
                    or axis.get("undeclared_evidence")
                ):
                    return None
                evidence_axis.append(
                    {
                        "canonical_unit": canonical_unit,
                        "locator": {
                            "page_json_version_id": page_json_version_id,
                            "section_id": f"s{section_ordinal}",
                            "table_id": f"t{table_ordinal}",
                        },
                        "statement_type": section.get("statement_type"),
                        "unit_axis": canonical_clone_v1(axis),
                    }
                )
    units = {item["canonical_unit"] for item in evidence_axis}
    if len(units) != 1:
        return None
    canonical_unit = next(iter(units))
    material = {
        "canonical_unit": canonical_unit,
        "evidence_axis": evidence_axis,
        "rule": (
            "EVERY_UNIT_BEARING_PRIMARY_STATEMENT_TABLE_IN_THE_SAME_SELECTED_"
            "DOCUMENT_HAS_ONE_COMPLETE_ACCEPTED_CANONICAL_UNIT_WHILE_UNITLESS_"
            "TABLES_DO_NOT_VOTE_NO_VALUE_MAGNITUDE_DISTANCE_OR_ROUNDING"
        ),
    }
    return {
        **material,
        "receipt_id": "gjoefav1:primary-statement-unit-context:"
        + canonical_json_sha256_v1(material),
    }


def _primary_operating_expense_roots(
    *,
    pages: Mapping[str, dict[str, Any]],
    selected_page_axis: Sequence[Mapping[str, Any]],
    document_ordinal: int,
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    axis_by_version = {
        item["page_json_version_id"]: item
        for item in selected_page_axis
        if item.get("document_ordinal") == document_ordinal
    }
    document_unit_context = _unique_primary_statement_unit_context(
        pages=pages,
        selected_version_ids=set(axis_by_version),
        compiled_specs=compiled_specs,
    )
    roots = []
    for page_json_version_id, page in pages.items():
        page_axis = axis_by_version.get(page_json_version_id)
        if page_axis is None or page.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
            continue
        for section_ordinal, section in enumerate(page.get("sections", []), start=1):
            if (
                type(section) is not dict
                or section.get("content_kind") != "PRIMARY_STATEMENT"
                or section.get("statement_type") != "INCOME_STATEMENT"
            ):
                continue
            for table_ordinal, table in enumerate(section.get("tables", []), start=1):
                if type(table) is not dict:
                    continue
                money_ordinals = _money_column_ordinals(table)
                if len(money_ordinals) < 2:
                    continue
                unit = _local_explicit_unit(table, compiled_specs=compiled_specs)
                if unit is None:
                    if document_unit_context is None:
                        continue
                    unit = {
                        "canonical_unit": document_unit_context["canonical_unit"],
                        "evidence": canonical_clone_v1(document_unit_context),
                        "rule": (
                            "UNITLESS_PRIMARY_INCOME_STATEMENT_TABLE_USES_UNIQUE_"
                            "SAME_DOCUMENT_PRIMARY_STATEMENT_UNIT_CONTEXT"
                        ),
                    }
                rows = table.get("rows")
                for row_ordinal, row in enumerate(rows if type(rows) is list else [], start=1):
                    if type(row) is not dict or not _is_parent_label(
                        row.get("label_exact"), compiled_specs=compiled_specs
                    ):
                        continue
                    vector = _observed_vector(row, money_ordinals)
                    if vector is None:
                        continue
                    roots.append(
                        {
                            "canonical_unit": unit["canonical_unit"],
                            "locator": {
                                "page_json_version_id": page_json_version_id,
                                "physical_page": page_axis["physical_page"],
                                "section_id": f"s{section_ordinal}",
                                "table_id": f"t{table_ordinal}",
                            },
                            "money_column_ordinals": money_ordinals,
                            "row_ordinal": row_ordinal,
                            "unit_receipt": canonical_clone_v1(unit),
                            "vector": vector,
                        }
                    )
    return roots


def _bind_exact_primary_statement_unit(
    *,
    pages: dict[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    selected_page_axis: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    tables = []
    for region in regions:
        page = pages.get(region.get("page_json_version_id"))
        if type(page) is not dict:
            raise _error("operating-expense selected page JSON is absent")
        _section, table = _source_table(
            page, section_id=region["section_id"], table_id=region["table_id"]
        )
        tables.append((region, table))
    if any(table.get("unit_exact") is not None for _region, table in tables):
        return []
    target = _target_total_observation(pages=pages, regions=regions, compiled_specs=compiled_specs)
    if target is None:
        return []
    document_ordinals = {region.get("document_ordinal") for region in regions}
    if len(document_ordinals) != 1 or type(next(iter(document_ordinals))) is not int:
        return []
    document_ordinal = next(iter(document_ordinals))
    roots = _primary_operating_expense_roots(
        pages=pages,
        selected_page_axis=selected_page_axis,
        document_ordinal=document_ordinal,
        compiled_specs=compiled_specs,
    )
    matches = []
    target_vector = target["vector"]
    for root in roots:
        vector = root["vector"]
        for start in range(len(vector) - len(target_vector) + 1):
            window = vector[start : start + len(target_vector)]
            if window == target_vector:
                match_kind = "EXACT_SIGNED_COEFFICIENT_VECTOR"
            elif [abs(item) for item in window] == [abs(item) for item in target_vector]:
                match_kind = "EXACT_MAGNITUDE_VECTOR_WITH_SOURCE_PRESENTATION_SIGN_DIFFERENCE"
            else:
                continue
            matches.append(
                {
                    **canonical_clone_v1(root),
                    "match_kind": match_kind,
                    "matched_money_column_ordinals": root["money_column_ordinals"][
                        start : start + len(target_vector)
                    ],
                    "matched_vector": window,
                }
            )
    units = {item["canonical_unit"] for item in matches}
    if len(units) != 1 or not matches:
        return []
    canonical_unit = next(iter(units))
    for _region, table in tables:
        table["unit_exact"] = _UNIT_SURFACE[canonical_unit]
    material = {
        "canonical_unit": canonical_unit,
        "matched_primary_roots": matches,
        "rule": (
            "UNITLESS_OPERATING_EXPENSE_NOTE_UNIQUE_VISIBLE_TOTAL_EQUALS_ONE_"
            "CANONICAL_UNIT_PRIMARY_OPERATING_EXPENSE_ROOT_CONTIGUOUS_PERIOD_"
            "VECTOR_EXACTLY_WITH_OPTIONAL_SOURCE_PRESENTATION_SIGN_DIFFERENCE_"
            "NO_MAGNITUDE_SCALE_INFERENCE"
        ),
        "target_observation": canonical_clone_v1(target),
        "target_region_axis": [
            {
                key: region[key]
                for key in (
                    "page_json_version_id",
                    "physical_page",
                    "section_id",
                    "table_id",
                )
            }
            for region, _table in tables
        ],
        "target_unit_before_exact": None,
        "target_unit_exact": _UNIT_SURFACE[canonical_unit],
    }
    return [
        {
            **material,
            "receipt_id": "gjoefav1:unit:" + canonical_json_sha256_v1(material),
        }
    ]


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


def _classification_roles(classification: Mapping[str, Any]) -> list[str]:
    return sorted(
        {
            hit["role"]
            for hit in classification.get("role_hits", [])
            if type(hit) is dict and type(hit.get("role")) is str
        }
        | {role for role in classification.get("context_roles", []) if type(role) is str}
    )


def _blank_money_header_axis(table: Mapping[str, Any]) -> bool:
    columns = table.get("columns")
    money_ordinals = _money_column_ordinals(table)
    return bool(
        type(columns) is list
        and money_ordinals
        and all(
            type(columns[ordinal - 1].get("header_path_exact")) is list
            and not any(
                _normalized(segment) for segment in columns[ordinal - 1]["header_path_exact"]
            )
            for ordinal in money_ordinals
        )
    )


def _strip_exact_owner_header_prefix(
    table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
    """Remove only a duplicated exact owner title from MONEY header paths."""

    title = table.get("title_exact")
    columns = table.get("columns")
    money_ordinals = _money_column_ordinals(table)
    if (
        not _is_parent_label(title, compiled_specs=compiled_specs)
        or type(columns) is not list
        or not money_ordinals
    ):
        return None
    projected = canonical_clone_v1(table)
    changes = []
    for ordinal in money_ordinals:
        path = columns[ordinal - 1].get("header_path_exact")
        if (
            type(path) is not list
            or len(path) < 2
            or not same_typed_json_v1(path[0], title)
            or not any(_normalized(item) for item in path[1:])
        ):
            return None
        after = canonical_clone_v1(path[1:])
        projected["columns"][ordinal - 1]["header_path_exact"] = after
        changes.append(
            {
                "after_header_path_exact": after,
                "before_header_path_exact": canonical_clone_v1(path),
                "money_column_ordinal": ordinal,
            }
        )
    return projected, changes


def _generic_financial_note_report_header(value: Any) -> bool:
    return bool(type(value) is str and "thuyet minh bao cao tai chinh" in _normalized(value))


def _duration_axis_with_optional_owner_prefix_projection(
    table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]] | None:
    stripped = _strip_exact_owner_header_prefix(table, compiled_specs=compiled_specs)
    if stripped is not None:
        projected, changes = stripped
        lane_axis = _duration_multitable_lane_axis(projected, compiled_specs=compiled_specs)
        if lane_axis.get("complete") is True:
            return projected, canonical_clone_v1(lane_axis), changes
    lane_axis = _duration_multitable_lane_axis(table, compiled_specs=compiled_specs)
    if lane_axis.get("complete") is True:
        return canonical_clone_v1(table), canonical_clone_v1(lane_axis), []
    return None


def _complete_owner_continuation_projection(
    *,
    pages: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], dict[str, Any]] | None:
    """Join one exact adjacent source continuation on a private table clone.

    The position/marker/period/unit grammar selects the two fragments.  Any
    flattened suffix is scoped only to the sender's final declared structural
    parent, and only when its declared match is uniquely compatible with that
    parent.  Arithmetic remains solely an evaluator veto after projection.
    """

    if type(regions) not in {list, tuple} or len(regions) != 2:
        return None
    original_regions = canonical_clone_v1(list(regions))
    prior_region, receiver_region = original_regions
    if (
        prior_region.get("document_id") != receiver_region.get("document_id")
        or prior_region.get("document_ordinal") != receiver_region.get("document_ordinal")
        or prior_region.get("source_sha256") != receiver_region.get("source_sha256")
        or prior_region.get("source_logical_name") != receiver_region.get("source_logical_name")
        or receiver_region.get("physical_page") != prior_region.get("physical_page", -2) + 1
        or receiver_region.get("selected_page_ordinal")
        != prior_region.get("selected_page_ordinal", -2) + 1
        or receiver_region.get("section_id") != "s1"
        or receiver_region.get("table_id") != "t1"
    ):
        return None
    prior_page = pages.get(prior_region.get("page_json_version_id"))
    receiver_page = pages.get(receiver_region.get("page_json_version_id"))
    if type(prior_page) is not dict or type(receiver_page) is not dict:
        return None
    try:
        prior_section, prior_table = _source_table(
            prior_page,
            section_id=prior_region["section_id"],
            table_id=prior_region["table_id"],
        )
        receiver_section, receiver_table = _source_table(
            receiver_page,
            section_id=receiver_region["section_id"],
            table_id=receiver_region["table_id"],
        )
    except GeminiJsonOperatingExpenseFamilyV1Error:
        return None
    receiver_narratives = _receiver_continuation_narratives(receiver_section)
    if (
        prior_table.get("continuation") not in {"NONE", "CONTINUES_ON_NEXT_PAGE"}
        or receiver_table.get("continuation") != "CONTINUES_FROM_PREVIOUS_PAGE"
        or not _is_last_source_table_on_page(
            prior_page,
            section_id=prior_region["section_id"],
            table_id=prior_region["table_id"],
        )
        or receiver_narratives is None
    ):
        return None
    receiver_title = receiver_table.get("title_exact")
    normalized_receiver_title = _normalized(receiver_title)
    if receiver_title is not None and not (
        "tiep theo" in normalized_receiver_title
        and any(alias in normalized_receiver_title for alias in _parent_aliases(compiled_specs))
    ):
        return None
    receiver_section_title = receiver_section.get("title_exact")
    if receiver_section_title is not None and not _generic_financial_note_report_header(
        receiver_section_title
    ):
        return None
    prior_axis_result = _duration_axis_with_optional_owner_prefix_projection(
        prior_table, compiled_specs=compiled_specs
    )
    if prior_axis_result is None:
        return None
    projected_prior_source, prior_lane_axis, header_changes = prior_axis_result
    prior_money_ordinals = _money_column_ordinals(projected_prior_source)
    receiver_money_ordinals = _money_column_ordinals(receiver_table)
    if len(prior_money_ordinals) != 2 or len(receiver_money_ordinals) != 2:
        return None
    receiver_headers_blank = _blank_money_header_axis(receiver_table)
    receiver_lane_axis = None
    if not receiver_headers_blank:
        receiver_lane_axis = _duration_multitable_lane_axis(
            receiver_table, compiled_specs=compiled_specs
        )
        if receiver_lane_axis.get("complete") is not True or receiver_lane_axis.get(
            "lane_keys"
        ) != prior_lane_axis.get("lane_keys"):
            return None
    # The exact owner prefix has already been authenticated and removed from
    # the projected period headers above.  Unit parsing must use that private
    # header projection too; on the raw table the owner text is deliberately
    # treated as undeclared header evidence by the shared unit parser.
    prior_unit = _local_explicit_unit(projected_prior_source, compiled_specs=compiled_specs)
    receiver_unit = _local_explicit_unit(receiver_table, compiled_specs=compiled_specs)
    if (
        prior_unit is not None
        and receiver_unit is not None
        and prior_unit["canonical_unit"] != receiver_unit["canonical_unit"]
    ):
        return None

    prior_classification = classify_gemini_json_multitable_hierarchical_table_v1(
        prior_page, prior_section, prior_table, compiled_specs=compiled_specs
    )
    receiver_classification = classify_gemini_json_multitable_hierarchical_table_v1(
        receiver_page, receiver_section, receiver_table, compiled_specs=compiled_specs
    )
    prior_rows = prior_table.get("rows")
    receiver_rows = receiver_table.get("rows")
    receiver_total_rows = receiver_classification.get("total_rows")
    if (
        prior_classification.get("owner_visible") is not True
        or prior_classification.get("family_presence_anchor_visible") is not True
        or prior_classification.get("typed_control_disposition") is not None
        or receiver_classification.get("typed_control_disposition") is not None
        or type(prior_rows) is not list
        or not prior_rows
        or type(receiver_rows) is not list
        or len(receiver_rows) < 2
        or receiver_total_rows
        != [
            {
                "row_kind": "TOTAL",
                "row_ordinal": len(receiver_rows),
                "source_order": len(receiver_rows),
            }
        ]
        or _observed_vector(receiver_rows[-1], receiver_money_ordinals) is None
    ):
        return None

    structural_hits = [
        hit
        for hit in prior_classification.get("role_hits", [])
        if type(hit) is dict
        and hit.get("role") in compiled_specs["root_component_roles"]
        and compiled_specs["child_by_role"].get(hit.get("role"), {}).get("role_kind")
        == "STRUCTURAL_GROUP"
    ]
    active_parent = (
        max(structural_hits, key=lambda item: item["row_ordinal"]) if structural_hits else None
    )

    def compatible_child_role(role: Any) -> bool:
        if active_parent is None or type(role) is not str:
            return False
        parent = active_parent["role"]
        if parent == "ADMIN_EXPENSE" and role.startswith("FLAT_ADMIN_"):
            return True
        if parent == "ASSET_EXPENSE" and role.startswith("FLAT_ASSET_"):
            return True
        return any(
            matcher.get("within_role") == parent
            for matcher in compiled_specs["matchers_by_role"].get(role, [])
        )

    def scoped_flat_ordinals(
        rows: Sequence[Mapping[str, Any]],
        classification: Mapping[str, Any],
        *,
        money_ordinals: Sequence[int],
        start_ordinal: int,
        stop_at_first_nonchild: bool,
    ) -> list[int] | None:
        hits_by_row: dict[int, list[str]] = {}
        for hit in classification.get("role_hits", []):
            if type(hit) is dict and type(hit.get("row_ordinal")) is int:
                hits_by_row.setdefault(hit["row_ordinal"], []).append(hit.get("role"))
        ambiguous_by_row = {
            item["row_ordinal"]: item.get("matched_roles", [])
            for item in classification.get("ambiguous_rows", [])
            if type(item) is dict and type(item.get("row_ordinal")) is int
        }
        scoped = []
        for ordinal in range(start_ordinal, len(rows) + 1):
            row = rows[ordinal - 1]
            if type(row) is not dict or row.get("row_kind") != "ITEM":
                if stop_at_first_nonchild:
                    break
                continue
            path = row.get("hierarchy_path_exact")
            if path != [row.get("label_exact")]:
                if stop_at_first_nonchild:
                    break
                continue
            roles = [
                role
                for role in [*hits_by_row.get(ordinal, []), *ambiguous_by_row.get(ordinal, [])]
                if compatible_child_role(role)
            ]
            if len(set(roles)) != 1:
                if stop_at_first_nonchild:
                    break
                continue
            if _observed_vector(row, money_ordinals) is None:
                return None
            scoped.append(ordinal)
        return scoped

    prior_scoped_ordinals: list[int] = []
    receiver_scoped_ordinals: list[int] = []
    if active_parent is not None:
        prior_scoped = scoped_flat_ordinals(
            prior_rows,
            prior_classification,
            money_ordinals=prior_money_ordinals,
            start_ordinal=active_parent["row_ordinal"] + 1,
            stop_at_first_nonchild=False,
        )
        receiver_scoped = scoped_flat_ordinals(
            receiver_rows[:-1],
            receiver_classification,
            money_ordinals=receiver_money_ordinals,
            start_ordinal=1,
            stop_at_first_nonchild=True,
        )
        if prior_scoped is None or receiver_scoped is None:
            return None
        prior_scoped_ordinals = prior_scoped
        receiver_scoped_ordinals = receiver_scoped
    if prior_classification.get("ambiguous_rows") and not {
        item.get("row_ordinal") for item in prior_classification["ambiguous_rows"]
    }.issubset(set(prior_scoped_ordinals)):
        return None
    if receiver_classification.get("ambiguous_rows") and not {
        item.get("row_ordinal") for item in receiver_classification["ambiguous_rows"]
    }.issubset(set(receiver_scoped_ordinals)):
        return None

    def direct_detail_subtotal_ordinals(
        rows: Sequence[Mapping[str, Any]], classification: Mapping[str, Any]
    ) -> dict[int, str]:
        hits_by_row: dict[int, list[str]] = {}
        for hit in classification.get("role_hits", []):
            if type(hit) is dict and type(hit.get("row_ordinal")) is int:
                hits_by_row.setdefault(hit["row_ordinal"], []).append(hit.get("role"))
        result = {}
        for row_ordinal, roles in hits_by_row.items():
            unique_roles = {role for role in roles if type(role) is str}
            row = rows[row_ordinal - 1] if 1 <= row_ordinal <= len(rows) else None
            if type(row) is not dict or row.get("row_kind") != "SUBTOTAL":
                continue
            if len(unique_roles) != 1:
                continue
            role = next(iter(unique_roles))
            if (
                role not in compiled_specs.get("bindings", {})
                or role in compiled_specs.get("root_component_roles", [])
                or not any(
                    type(matcher.get("within_role")) is str
                    for matcher in compiled_specs["matchers_by_role"].get(role, [])
                )
                or type(row.get("hierarchy_path_exact")) is not list
                or len(row["hierarchy_path_exact"]) < 2
            ):
                continue
            result[row_ordinal] = role
        return result

    prior_detail_subtotals = direct_detail_subtotal_ordinals(prior_rows, prior_classification)
    receiver_detail_subtotals = direct_detail_subtotal_ordinals(
        receiver_rows, receiver_classification
    )

    projected_pages = {version_id: canonical_clone_v1(page) for version_id, page in pages.items()}
    projected_prior_section, projected_prior_table = _source_table(
        projected_pages[prior_region["page_json_version_id"]],
        section_id=prior_region["section_id"],
        table_id=prior_region["table_id"],
    )
    projected_prior_table["columns"] = canonical_clone_v1(projected_prior_source["columns"])
    projected_prior_table["continuation"] = "NONE"
    if prior_unit is None and receiver_unit is not None:
        projected_prior_table["unit_exact"] = receiver_table.get("unit_exact")
    parent_row = prior_rows[active_parent["row_ordinal"] - 1] if active_parent is not None else None
    parent_label = parent_row.get("label_exact") if type(parent_row) is dict else None
    projected_rows = []
    row_projections = []

    def append_projected_row(
        row: Mapping[str, Any],
        *,
        row_ordinal: int,
        region: Mapping[str, Any],
        before_money_ordinals: Sequence[int],
        scope_to_parent: bool,
        normalize_detail_subtotal: bool,
    ) -> None:
        projected_row = canonical_clone_v1(row)
        if list(before_money_ordinals) != prior_money_ordinals:
            values = row.get("values_exact")
            if type(values) is not list:
                raise _error("operating-expense continuation row value axis is invalid")
            aligned = [None] * len(projected_prior_table["columns"])
            for before_ordinal, after_ordinal in zip(
                before_money_ordinals, prior_money_ordinals, strict=True
            ):
                if before_ordinal > len(values):
                    raise _error("operating-expense continuation MONEY cell is absent")
                aligned[after_ordinal - 1] = canonical_clone_v1(values[before_ordinal - 1])
            projected_row["values_exact"] = aligned
        if scope_to_parent:
            if type(parent_label) is not str:
                raise _error("operating-expense continuation parent label is invalid")
            projected_row["hierarchy_path_exact"] = [
                parent_label,
                row.get("label_exact"),
            ]
        if normalize_detail_subtotal:
            projected_row["row_kind"] = "ITEM"
        projected_rows.append(projected_row)
        row_projections.append(
            {
                "after_money_column_ordinals": canonical_clone_v1(prior_money_ordinals),
                "after_row": canonical_clone_v1(projected_row),
                "before_locator": _region_locator(region),
                "before_money_column_ordinals": canonical_clone_v1(list(before_money_ordinals)),
                "before_row": canonical_clone_v1(row),
                "before_row_ordinal": row_ordinal,
                "projected_row_ordinal": len(projected_rows),
            }
        )

    for row_ordinal, row in enumerate(prior_rows, start=1):
        append_projected_row(
            row,
            row_ordinal=row_ordinal,
            region=prior_region,
            before_money_ordinals=prior_money_ordinals,
            scope_to_parent=row_ordinal in prior_scoped_ordinals,
            normalize_detail_subtotal=row_ordinal in prior_detail_subtotals,
        )
    for row_ordinal, row in enumerate(receiver_rows, start=1):
        append_projected_row(
            row,
            row_ordinal=row_ordinal,
            region=receiver_region,
            before_money_ordinals=receiver_money_ordinals,
            scope_to_parent=row_ordinal in receiver_scoped_ordinals,
            normalize_detail_subtotal=row_ordinal in receiver_detail_subtotals,
        )
    projected_prior_table["rows"] = projected_rows
    projected_region = canonical_clone_v1(prior_region)
    projected_region["fragment_ordinal"] = 1
    projected_classification = classify_gemini_json_multitable_hierarchical_table_v1(
        projected_pages[prior_region["page_json_version_id"]],
        projected_prior_section,
        projected_prior_table,
        compiled_specs=compiled_specs,
    )
    terminal_total = len(projected_rows)
    if (
        projected_classification.get("ambiguous_rows") != []
        or projected_classification.get("family_presence_anchor_visible") is not True
        or projected_classification.get("owner_visible") is not True
        or projected_classification.get("total_rows")[-1:]
        != [
            {
                "row_kind": "TOTAL",
                "row_ordinal": terminal_total,
                "source_order": terminal_total,
            }
        ]
        or set(projected_classification.get("unbound_money_row_ordinals", [])) - {terminal_total}
    ):
        return None
    projected_region["component_roles"] = _classification_roles(projected_classification)
    projected_regions = [projected_region]
    original_query_receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        original_regions
    )
    projected_query_receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        projected_regions
    )
    material = {
        "active_parent": (
            None
            if active_parent is None
            else {
                "role": active_parent["role"],
                "row": canonical_clone_v1(parent_row),
                "row_ordinal": active_parent["row_ordinal"],
            }
        ),
        "header_path_projections": header_changes,
        "partial_detail_subtotal_item_projections": [
            {
                "before_locator": _region_locator(region),
                "before_row_ordinal": row_ordinal,
                "role": role,
            }
            for region, axis in (
                (prior_region, prior_detail_subtotals),
                (receiver_region, receiver_detail_subtotals),
            )
            for row_ordinal, role in sorted(axis.items())
        ],
        "original_query_receipt": original_query_receipt,
        "original_regions": original_regions,
        "prior_classification_id": prior_classification["classification_id"],
        "prior_lane_axis": prior_lane_axis,
        "prior_locator": _region_locator(prior_region),
        "prior_marker": prior_table.get("continuation"),
        "prior_scoped_row_ordinals": prior_scoped_ordinals,
        "prior_unit": canonical_clone_v1(prior_unit),
        "projected_classification_id": projected_classification["classification_id"],
        "projected_query_receipt": projected_query_receipt,
        "projected_region": projected_region,
        "receiver_classification_id": receiver_classification["classification_id"],
        "receiver_header_axis_rule": (
            "INHERITED_ONLY_FROM_COMPLETE_PRIOR_AXIS"
            if receiver_headers_blank
            else "EXACT_EQUIVALENT_EXPLICIT_PERIOD_AXIS_NO_MUTATION"
        ),
        "receiver_lane_axis": canonical_clone_v1(receiver_lane_axis),
        "receiver_locator": _region_locator(receiver_region),
        "receiver_narratives_exact": receiver_narratives,
        "receiver_scoped_row_ordinals": receiver_scoped_ordinals,
        "receiver_unit": canonical_clone_v1(receiver_unit),
        "row_projections": row_projections,
        "rule": (
            "UNIQUE_EXACT_PHYSICALLY_AND_SELECTED_ADJACENT_OPERATING_EXPENSE_"
            "OWNER_TABLE_TO_EXPLICIT_RECEIVER_WITH_EQUIVALENT_OR_BLANK_PERIOD_"
            "AXIS_COMPATIBLE_EXPLICIT_UNIT_AND_ONLY_UNIQUE_DECLARED_FINAL_PARENT_"
            "FLAT_SUFFIX_SCOPE_AND_NESTED_DIRECT_DETAIL_SUBTOTAL_KIND_"
            "NORMALIZATION_PRIVATE_CLONE_NO_SOURCE_VALUE_CHANGE"
        ),
    }
    return (
        projected_pages,
        projected_regions,
        {
            **material,
            "receipt_id": "gjoefav1:continuation-projection:" + canonical_json_sha256_v1(material),
        },
    )


def _internal_owner_continuation_projection(
    *,
    pages: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], dict[str, Any]] | None:
    """Expose one exact internal owner that begins a split source schedule.

    Some source pages concatenate several notes into one extracted table.  This
    projection accepts only a blank, exact Family-36 GROUP owner followed by
    its detail suffix at the end of the page and an explicitly reciprocal
    page-leading receiver.  The excluded prefix is fully bound in the receipt;
    source row ordinals are restored before any mapping leaves the adapter.
    """

    if type(regions) not in {list, tuple} or len(regions) != 2:
        return None
    prior_region, receiver_region = canonical_clone_v1(list(regions))
    if (
        prior_region.get("document_id") != receiver_region.get("document_id")
        or prior_region.get("document_ordinal") != receiver_region.get("document_ordinal")
        or prior_region.get("source_sha256") != receiver_region.get("source_sha256")
        or prior_region.get("source_logical_name") != receiver_region.get("source_logical_name")
        or receiver_region.get("physical_page") != prior_region.get("physical_page", -2) + 1
        or receiver_region.get("selected_page_ordinal")
        != prior_region.get("selected_page_ordinal", -2) + 1
        or receiver_region.get("section_id") != "s1"
        or receiver_region.get("table_id") != "t1"
    ):
        return None
    prior_page = pages.get(prior_region.get("page_json_version_id"))
    receiver_page = pages.get(receiver_region.get("page_json_version_id"))
    if type(prior_page) is not dict or type(receiver_page) is not dict:
        return None
    try:
        prior_section, prior_table = _source_table(
            prior_page,
            section_id=prior_region["section_id"],
            table_id=prior_region["table_id"],
        )
        _receiver_section, receiver_table = _source_table(
            receiver_page,
            section_id=receiver_region["section_id"],
            table_id=receiver_region["table_id"],
        )
    except GeminiJsonOperatingExpenseFamilyV1Error:
        return None
    prior_rows = prior_table.get("rows")
    money_ordinals = _money_column_ordinals(prior_table)
    if (
        prior_table.get("continuation") != "BOTH"
        or receiver_table.get("continuation") != "CONTINUES_FROM_PREVIOUS_PAGE"
        or type(prior_rows) is not list
        or len(prior_rows) < 4
        or len(money_ordinals) != 2
        or not _is_last_source_table_on_page(
            prior_page,
            section_id=prior_region["section_id"],
            table_id=prior_region["table_id"],
        )
    ):
        return None
    owners = []
    for ordinal, row in enumerate(prior_rows, start=1):
        if (
            type(row) is not dict
            or row.get("row_kind") != "GROUP"
            or not _is_parent_label(row.get("label_exact"), compiled_specs=compiled_specs)
            or row.get("hierarchy_path_exact") != [row.get("label_exact")]
        ):
            continue
        values = row.get("values_exact")
        if type(values) is not list or any(
            ordinal_ > len(values) or values[ordinal_ - 1] is not None
            for ordinal_ in money_ordinals
        ):
            continue
        owners.append((ordinal, row))
    if len(owners) != 1:
        return None
    owner_ordinal, owner_row = owners[0]
    if owner_ordinal >= len(prior_rows):
        return None

    prepared_pages = {version_id: canonical_clone_v1(page) for version_id, page in pages.items()}
    prepared_section, prepared_table = _source_table(
        prepared_pages[prior_region["page_json_version_id"]],
        section_id=prior_region["section_id"],
        table_id=prior_region["table_id"],
    )
    prepared_table["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    prepared_table["rows"] = canonical_clone_v1(prior_rows[owner_ordinal:])
    prepared_table["title_exact"] = owner_row["label_exact"]
    prepared_classification = classify_gemini_json_multitable_hierarchical_table_v1(
        prepared_pages[prior_region["page_json_version_id"]],
        prepared_section,
        prepared_table,
        compiled_specs=compiled_specs,
    )
    declared_roles = set(_classification_roles(prepared_classification))
    if (
        prepared_classification.get("owner_visible") is not True
        or prepared_classification.get("family_presence_anchor_visible") is not True
        or prepared_classification.get("typed_control_disposition") is not None
        or prepared_classification.get("ambiguous_rows")
        or not any(
            set(combination) <= declared_roles
            for combination in compiled_specs["topology"]["required_role_combinations"]
        )
    ):
        return None
    prepared_prior_region = canonical_clone_v1(prior_region)
    prepared_prior_region["component_roles"] = _classification_roles(prepared_classification)
    projected = _complete_owner_continuation_projection(
        pages=prepared_pages,
        regions=[prepared_prior_region, receiver_region],
        compiled_specs=compiled_specs,
    )
    if projected is None:
        return None
    projected_pages, projected_regions, receipt = projected
    for projection in receipt["row_projections"]:
        if projection["before_locator"]["page_json_version_id"] == prior_region[
            "page_json_version_id"
        ]:
            projection["before_row_ordinal"] += owner_ordinal
    receipt["original_regions"] = canonical_clone_v1([prior_region, receiver_region])
    receipt["original_query_receipt"] = (
        build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            receipt["original_regions"]
        )
    )
    receipt["internal_owner_projection"] = {
        "excluded_prefix_rows": canonical_clone_v1(prior_rows[: owner_ordinal - 1]),
        "owner_row": canonical_clone_v1(owner_row),
        "owner_row_ordinal": owner_ordinal,
        "prepared_classification_id": prepared_classification["classification_id"],
        "raw_prior_locator": _region_locator(prior_region),
        "rule": (
            "ONE_EXACT_ALL_MONEY_LANES_BLANK_INTERNAL_FAMILY_OWNER_GROUP_BEGINS_"
            "THE_FINAL_SOURCE_TABLE_SUFFIX_BEFORE_AN_EXPLICIT_RECIPROCAL_RECEIVER"
        ),
    }
    receipt["rule"] = (
        "UNIQUE_EXACT_INTERNAL_OPERATING_EXPENSE_OWNER_SUFFIX_AND_RECIPROCAL_"
        "ADJACENT_RECEIVER_MERGED_ON_PRIVATE_CLONE_WITH_RAW_ROW_ORDINAL_RESTORATION"
    )
    receipt_material = {key: value for key, value in receipt.items() if key != "receipt_id"}
    receipt["receipt_id"] = "gjoefav1:continuation-projection:" + canonical_json_sha256_v1(
        receipt_material
    )
    return projected_pages, projected_regions, receipt


def _continuation_projection(
    *,
    pages: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], dict[str, Any]] | None:
    """Merge one exact adjacent split note on a private evaluation clone.

    The receiver's leading flattened rows are scoped only to the sender's
    final structural parent. The source rows and values are not changed; a
    row-projection axis restores every emitted mapping to its original page.
    """

    internal_owner = _internal_owner_continuation_projection(
        pages=pages, regions=regions, compiled_specs=compiled_specs
    )
    if internal_owner is not None:
        return internal_owner
    complete = _complete_owner_continuation_projection(
        pages=pages, regions=regions, compiled_specs=compiled_specs
    )
    if complete is not None:
        return complete
    if type(regions) not in {list, tuple} or len(regions) != 2:
        return None
    original_regions = canonical_clone_v1(list(regions))
    prior_region, receiver_region = original_regions
    if (
        prior_region.get("document_id") != receiver_region.get("document_id")
        or prior_region.get("document_ordinal") != receiver_region.get("document_ordinal")
        or prior_region.get("source_sha256") != receiver_region.get("source_sha256")
        or prior_region.get("source_logical_name") != receiver_region.get("source_logical_name")
        or receiver_region.get("physical_page") != prior_region.get("physical_page", -2) + 1
        or receiver_region.get("selected_page_ordinal")
        != prior_region.get("selected_page_ordinal", -2) + 1
    ):
        return None
    prior_page = pages.get(prior_region.get("page_json_version_id"))
    receiver_page = pages.get(receiver_region.get("page_json_version_id"))
    if type(prior_page) is not dict or type(receiver_page) is not dict:
        return None
    try:
        prior_section, prior_table = _source_table(
            prior_page,
            section_id=prior_region["section_id"],
            table_id=prior_region["table_id"],
        )
        receiver_section, receiver_table = _source_table(
            receiver_page,
            section_id=receiver_region["section_id"],
            table_id=receiver_region["table_id"],
        )
    except GeminiJsonOperatingExpenseFamilyV1Error:
        return None
    if (
        prior_table.get("continuation") != "CONTINUES_ON_NEXT_PAGE"
        or receiver_table.get("continuation") != "CONTINUES_FROM_PREVIOUS_PAGE"
        or receiver_region.get("section_id") != "s1"
        or receiver_region.get("table_id") != "t1"
        or int(prior_region["section_id"][1:]) != len(prior_page.get("sections", []))
        or int(prior_region["table_id"][1:]) != len(prior_section.get("tables", []))
        or receiver_table.get("title_exact") is not None
        or receiver_section.get("narratives_exact") != []
        or not _generic_financial_note_report_header(receiver_section.get("title_exact"))
        or not _blank_money_header_axis(receiver_table)
    ):
        return None
    stripped = _strip_exact_owner_header_prefix(prior_table, compiled_specs=compiled_specs)
    if stripped is None:
        return None
    stripped_prior_table, header_changes = stripped
    prior_lane_axis = _duration_multitable_lane_axis(
        stripped_prior_table, compiled_specs=compiled_specs
    )
    prior_unit = _local_explicit_unit(stripped_prior_table, compiled_specs=compiled_specs)
    receiver_unit = _local_explicit_unit(receiver_table, compiled_specs=compiled_specs)
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
    prior_rows = prior_table.get("rows")
    receiver_rows = receiver_table.get("rows")
    total_rows = receiver_classification.get("total_rows")
    if (
        prior_lane_axis.get("complete") is not True
        or type(prior_unit) is not dict
        or type(receiver_unit) is not dict
        or prior_unit["canonical_unit"] != receiver_unit["canonical_unit"]
        or len(_money_column_ordinals(receiver_table))
        != len(prior_lane_axis.get("money_column_ordinals", []))
        or prior_classification.get("ambiguous_rows") != []
        or type(prior_rows) is not list
        or not prior_rows
        or type(receiver_rows) is not list
        or len(receiver_rows) < 3
        or type(total_rows) is not list
        or total_rows
        != [
            {
                "row_kind": "TOTAL",
                "row_ordinal": len(receiver_rows),
                "source_order": len(receiver_rows),
            }
        ]
        or _observed_vector(receiver_rows[-1], _money_column_ordinals(receiver_table)) is None
    ):
        return None
    structural_hits = [
        hit
        for hit in prior_classification.get("role_hits", [])
        if type(hit) is dict
        and compiled_specs.get("child_by_role", {}).get(hit.get("role"), {}).get("role_kind")
        == "STRUCTURAL_GROUP"
    ]
    if not structural_hits:
        return None
    active_parent = max(structural_hits, key=lambda item: item["row_ordinal"])
    active_parent_role = active_parent["role"]
    if receiver_classification.get("context_roles") != [active_parent_role]:
        return None
    boundary_ordinals = [
        row_ordinal
        for row_ordinal, row in enumerate(receiver_rows[:-1], start=1)
        if type(row) is dict
        and type(row.get("label_exact")) is str
        and _without_leading_ordinal(_normalized(row["label_exact"]))
        != _normalized(row["label_exact"])
    ]
    if not boundary_ordinals:
        return None
    boundary_ordinal = boundary_ordinals[0]
    receiver_ambiguities = receiver_classification.get("ambiguous_rows")
    validation_roles = set(compiled_specs.get("validation_only_roles", []))
    if type(receiver_ambiguities) is not list or any(
        type(item) is not dict
        or type(item.get("row_ordinal")) is not int
        or not 1 <= item["row_ordinal"] < boundary_ordinal
        or type(item.get("matched_roles")) is not list
        or not item["matched_roles"]
        or not set(item["matched_roles"]).issubset(validation_roles)
        for item in receiver_ambiguities
    ):
        return None
    leading_rows = receiver_rows[: boundary_ordinal - 1]
    boundary_row = receiver_rows[boundary_ordinal - 1]
    receiver_money_ordinals = _money_column_ordinals(receiver_table)
    if (
        not leading_rows
        or any(
            type(row) is not dict
            or row.get("row_kind") != "ITEM"
            or row.get("hierarchy_path_exact") != [row.get("label_exact")]
            or _observed_vector(row, receiver_money_ordinals) is None
            for row in leading_rows
        )
        or type(boundary_row) is not dict
        or boundary_row.get("row_kind") not in {"ITEM", "GROUP"}
        or _observed_vector(boundary_row, receiver_money_ordinals) is None
    ):
        return None
    boundary_roles = {
        hit["role"]
        for hit in receiver_classification.get("role_hits", [])
        if type(hit) is dict and hit.get("row_ordinal") == boundary_ordinal
    }
    if (
        len(boundary_roles) != 1
        or active_parent_role in boundary_roles
        or not boundary_roles.issubset(set(compiled_specs.get("root_component_roles", [])))
    ):
        return None
    parent_row = prior_rows[active_parent["row_ordinal"] - 1]
    parent_label = parent_row.get("label_exact") if type(parent_row) is dict else None
    prior_title = prior_table.get("title_exact")
    if type(parent_label) is not str or type(prior_title) is not str:
        return None

    projected_pages = {version_id: canonical_clone_v1(page) for version_id, page in pages.items()}
    projected_prior_section, projected_prior_table = _source_table(
        projected_pages[prior_region["page_json_version_id"]],
        section_id=prior_region["section_id"],
        table_id=prior_region["table_id"],
    )
    projected_prior_table["columns"] = canonical_clone_v1(stripped_prior_table["columns"])
    projected_prior_table["continuation"] = "NONE"
    projected_rows = []
    row_projections = []
    for row_ordinal, row in enumerate(prior_rows, start=1):
        projected_rows.append(canonical_clone_v1(row))
        row_projections.append(
            {
                "after_row": canonical_clone_v1(projected_rows[-1]),
                "before_locator": _region_locator(prior_region),
                "before_row": canonical_clone_v1(row),
                "before_row_ordinal": row_ordinal,
                "projected_row_ordinal": len(projected_rows),
            }
        )
    for row_ordinal, row in enumerate(receiver_rows, start=1):
        projected_row = canonical_clone_v1(row)
        if row_ordinal < boundary_ordinal:
            projected_row["hierarchy_path_exact"] = [
                prior_title,
                parent_label,
                row.get("label_exact"),
            ]
        projected_rows.append(projected_row)
        row_projections.append(
            {
                "after_row": canonical_clone_v1(projected_row),
                "before_locator": _region_locator(receiver_region),
                "before_row": canonical_clone_v1(row),
                "before_row_ordinal": row_ordinal,
                "projected_row_ordinal": len(projected_rows),
            }
        )
    projected_prior_table["rows"] = projected_rows
    projected_region = canonical_clone_v1(prior_region)
    projected_region["fragment_ordinal"] = 1
    projected_classification = classify_gemini_json_multitable_hierarchical_table_v1(
        projected_pages[prior_region["page_json_version_id"]],
        projected_prior_section,
        projected_prior_table,
        compiled_specs=compiled_specs,
    )
    if (
        projected_classification.get("ambiguous_rows") != []
        or projected_classification.get("family_presence_anchor_visible") is not True
        or projected_classification.get("total_rows")
        != [
            {
                "row_kind": "TOTAL",
                "row_ordinal": len(projected_rows),
                "source_order": len(projected_rows),
            }
        ]
    ):
        return None
    projected_region["component_roles"] = _classification_roles(projected_classification)
    projected_regions = [projected_region]
    original_query_receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        original_regions
    )
    projected_query_receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        projected_regions
    )
    material = {
        "active_parent": {
            "role": active_parent_role,
            "row": canonical_clone_v1(parent_row),
            "row_ordinal": active_parent["row_ordinal"],
        },
        "boundary_ordinal": boundary_ordinal,
        "boundary_roles": sorted(boundary_roles),
        "header_path_projections": header_changes,
        "original_query_receipt": original_query_receipt,
        "original_regions": original_regions,
        "prior_classification_id": prior_classification["classification_id"],
        "prior_lane_axis": canonical_clone_v1(prior_lane_axis),
        "prior_locator": _region_locator(prior_region),
        "prior_unit": canonical_clone_v1(prior_unit),
        "projected_classification_id": projected_classification["classification_id"],
        "projected_query_receipt": projected_query_receipt,
        "projected_region": projected_region,
        "receiver_classification_id": receiver_classification["classification_id"],
        "receiver_leading_validation_ambiguities": canonical_clone_v1(receiver_ambiguities),
        "receiver_generic_section_title_exact": receiver_section.get("title_exact"),
        "receiver_locator": _region_locator(receiver_region),
        "receiver_unit": canonical_clone_v1(receiver_unit),
        "row_projections": row_projections,
        "rule": (
            "UNIQUE_RECIPROCAL_PHYSICALLY_AND_SELECTED_ADJACENT_OPERATING_"
            "EXPENSE_NOTE_SPLIT_WITH_EXACT_OWNER_TITLE_DUPLICATE_HEADER_PREFIX_"
            "BLANK_RECEIVER_HEADERS_SAME_EXPLICIT_UNIT_GENERIC_REPORT_HEADER_"
            "AND_CONSECUTIVE_FLATTENED_FINAL_PARENT_CHILD_PREFIX_MERGED_ON_"
            "PRIVATE_CLONE_NO_SOURCE_VALUE_CHANGE"
        ),
    }
    return (
        projected_pages,
        projected_regions,
        {
            **material,
            "receipt_id": "gjoefav1:continuation-projection:" + canonical_json_sha256_v1(material),
        },
    )


def _restore_continuation_mapping_source_refs(
    candidate: dict[str, Any], *, receipt: Mapping[str, Any]
) -> None:
    projections = receipt.get("row_projections")
    original_regions = receipt.get("original_regions")
    if type(projections) is not list or type(original_regions) is not list:
        raise _error("operating-expense continuation projection receipt is invalid")
    by_projected_ordinal = {
        item.get("projected_row_ordinal"): item for item in projections if type(item) is dict
    }
    if len(by_projected_ordinal) != len(projections):
        raise _error("operating-expense continuation projected row axis is duplicate")

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
            raise _error("operating-expense continuation source locator drifted")
        return canonical_clone_v1(matches[0])

    for mapping in candidate.get("mappings", []):
        if type(mapping) is not dict:
            raise _error("operating-expense continuation mapping is invalid")
        row_id = mapping.get("row_id")
        if type(row_id) is str and row_id.startswith("r") and row_id[1:].isdigit():
            projection = by_projected_ordinal.get(int(row_id[1:]))
            if projection is not None:
                mapping["row_id"] = f"r{projection['before_row_ordinal']}"
        refs = mapping.get("source_refs")
        if type(refs) is not list or not refs:
            raise _error("operating-expense continuation mapping source is absent")
        for source_ref in refs:
            locator = source_ref.get("locator") if type(source_ref) is dict else None
            projection = by_projected_ordinal.get(
                source_ref.get("row_ordinal") if type(source_ref) is dict else None
            )
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
                raise _error("operating-expense projected source ref drifted")
            before_row = projection["before_row"]
            after_row = projection["after_row"]
            if (
                source_ref.get("label_exact") != after_row.get("label_exact")
                or source_ref.get("hierarchy_path_exact") != after_row.get("hierarchy_path_exact")
                or source_ref.get("row_kind") != after_row.get("row_kind")
            ):
                raise _error("operating-expense projected source row drifted")
            source_ref["locator"] = original_region(projection)
            source_ref["row_id"] = f"r{projection['before_row_ordinal']}"
            source_ref["row_ordinal"] = projection["before_row_ordinal"]
            source_ref["label_exact"] = before_row.get("label_exact")
            source_ref["hierarchy_path_exact"] = canonical_clone_v1(
                before_row.get("hierarchy_path_exact")
            )
            source_ref["row_kind"] = before_row.get("row_kind")
            before_money_ordinals = projection.get("before_money_column_ordinals")
            if type(before_money_ordinals) is list:
                source_ref["money_column_ordinals"] = canonical_clone_v1(before_money_ordinals)
        mapping_material = {key: item for key, item in mapping.items() if key != "item_mapping_id"}
        mapping["item_mapping_id"] = "gjmthfmv1:item:" + canonical_json_sha256_v1(mapping_material)
    candidate["component_regions"] = canonical_clone_v1(original_regions)
    candidate["closure_receipt"]["query_receipt"] = canonical_clone_v1(
        receipt["original_query_receipt"]
    )


def _apply_authenticated_source_repairs(
    *,
    pages: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    repaired_pages = {version_id: canonical_clone_v1(page) for version_id, page in pages.items()}
    repairs = compiled_specs.get("operating_expense_source_repairs", [])
    if not regions or not repairs:
        return repaired_pages, []
    identities = {
        (region.get("source_logical_name"), region.get("source_sha256")) for region in regions
    }
    if len(identities) != 1:
        raise _error("operating-expense repair candidate source identity is ambiguous")
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
        for repair in repairs
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
    receipts = []
    for repair in applicable:
        source = repair["source"]
        locator = repair["locator"]
        if source["source_logical_name"] != source_logical_name:
            raise _error("operating-expense repair logical source identity drifted")
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
            raise _error("operating-expense repair is outside its selected table")
        page = repaired_pages.get(locator["page_json_version_id"])
        if type(page) is not dict:
            raise _error("operating-expense repair page is outside selected document")
        _section, table = _source_table(
            page, section_id=locator["section_id"], table_id=locator["table_id"]
        )
        rows = table.get("rows")
        if type(rows) is not list or locator["row_ordinal"] > len(rows):
            raise _error("operating-expense repair row is outside selected table")
        row = rows[locator["row_ordinal"] - 1]
        values = row.get("values_exact") if type(row) is dict else None
        if (
            type(values) is not list
            or locator["column_ordinal"] > len(values)
            or not same_typed_json_v1(values[locator["column_ordinal"] - 1], repair["before_exact"])
        ):
            raise _error("operating-expense repair cell before-image drifted")
        values[locator["column_ordinal"] - 1] = repair["after_exact"]
        material = {
            "repair": canonical_clone_v1(repair),
            "rule": (
                "PDF_VISIBLE_ACCOUNTING_DASH_REPLACES_EXACT_NULL_OR_FALSE_"
                "NUMERIC_CELL_ON_PRIVATE_CLONE_NO_OTHER_SOURCE_CHANGE"
            ),
            "source_repair_spec_sha256": compiled_specs[
                "operating_expense_source_repair_spec_sha256"
            ],
        }
        receipts.append(
            {
                **material,
                "receipt_id": "gjoefav1:source-repair-receipt:"
                + canonical_json_sha256_v1(material),
            }
        )
    return repaired_pages, receipts


def _all_blank_validation_role_omission_retry(
    *,
    pages: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Retry after omitting only source roles whose every visible lane is raw null.

    The shared engine already omits mappings for an all-blank role, but an
    additive validation-only role can still veto an otherwise exact printed
    root.  Family 36 has literal placeholder rows of that shape.  This retry
    changes no page bytes: it marks a role non-additive only in a private
    compiled-spec clone, and only when every occurrence of that role in the
    selected cluster has exact ``None`` in every MONEY cell.  A dash, partial
    row, invalid cell, ambiguity, or observed number therefore cannot enter
    this path.
    """

    validation_roles = set(compiled_specs.get("validation_only_roles", []))
    observations_by_role: dict[str, list[dict[str, Any]]] = {}
    disqualified_roles: set[str] = set()
    for region in regions:
        page = pages.get(region.get("page_json_version_id"))
        if type(page) is not dict:
            return None, []
        _section, table = _source_table(
            page, section_id=region["section_id"], table_id=region["table_id"]
        )
        classification = classify_gemini_json_multitable_hierarchical_table_v1(
            page, _section, table, compiled_specs=compiled_specs
        )
        if classification.get("ambiguous_rows"):
            return None, []
        money_ordinals = classification.get("money_column_ordinals")
        rows = table.get("rows")
        if type(money_ordinals) is not list or not money_ordinals or type(rows) is not list:
            continue
        for hit in classification.get("role_hits", []):
            role = hit.get("role") if type(hit) is dict else None
            child = compiled_specs.get("child_by_role", {}).get(role)
            row_ordinal = hit.get("row_ordinal") if type(hit) is dict else None
            if (
                role not in validation_roles
                or type(child) is not dict
                or child.get("role_kind") != "ADDITIVE_CHILD"
                or type(row_ordinal) is not int
                or not 1 <= row_ordinal <= len(rows)
            ):
                continue
            row = rows[row_ordinal - 1]
            values = row.get("values_exact") if type(row) is dict else None
            if type(values) is not list or any(
                type(ordinal) is not int or not 1 <= ordinal <= len(values)
                for ordinal in money_ordinals
            ):
                disqualified_roles.add(role)
                continue
            raw_values = [values[ordinal - 1] for ordinal in money_ordinals]
            if any(value is not None for value in raw_values):
                disqualified_roles.add(role)
                continue
            observations_by_role.setdefault(role, []).append(
                {
                    "locator": {
                        key: region[key]
                        for key in (
                            "page_json_version_id",
                            "physical_page",
                            "section_id",
                            "table_id",
                        )
                    },
                    "money_column_ordinals": canonical_clone_v1(money_ordinals),
                    "raw_values_exact": raw_values,
                    "row_id": row.get("row_id"),
                    "row_kind": row.get("row_kind"),
                    "row_ordinal": row_ordinal,
                    "role": role,
                }
            )
    eligible = sorted(set(observations_by_role) - disqualified_roles)
    if not eligible:
        return None, []
    retry_specs = canonical_clone_v1(compiled_specs)
    for role in eligible:
        retry_specs["child_by_role"][role]["role_kind"] = "NONADDITIVE_CHILD"
        topology_children = [
            child for child in retry_specs["topology"]["children"] if child.get("role") == role
        ]
        if len(topology_children) != 1:
            raise _error("operating-expense blank-role topology axis drifted")
        topology_children[0]["role_kind"] = "NONADDITIVE_CHILD"
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=regions,
        page_json_by_version=pages,
        compiled_specs=retry_specs,
        query_receipt=query_receipt,
    )
    if candidate.get("status") != READY:
        return None, []
    receipts = []
    for role in eligible:
        material = {
            "original_role_kind": "ADDITIVE_CHILD",
            "private_retry_role_kind": "NONADDITIVE_CHILD",
            "role": role,
            "rule": (
                "OMIT_VALIDATION_ONLY_ROLE_FROM_EQUATION_FRONTIER_IFF_EVERY_"
                "SELECTED_SOURCE_OCCURRENCE_HAS_RAW_NULL_IN_EVERY_MONEY_LANE"
            ),
            "source_observations": observations_by_role[role],
        }
        receipts.append(
            {
                **material,
                "receipt_id": "gjoefav1:all-blank-validation-role:"
                + canonical_json_sha256_v1(material),
            }
        )
    return candidate, receipts


def _source_ref_key(source_ref: Mapping[str, Any]) -> tuple[Any, ...] | None:
    locator = source_ref.get("locator")
    row_ordinal = source_ref.get("row_ordinal")
    if type(locator) is not dict or type(row_ordinal) is not int:
        return None
    return (
        locator.get("page_json_version_id"),
        locator.get("section_id"),
        locator.get("table_id"),
        row_ordinal,
    )


def _accepted_operating_expense_root_equation(
    *,
    components: Sequence[Mapping[str, Any]],
    result: Mapping[str, Any],
    canonical_unit: str,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Prove one printed root without changing a displayed source value.

    The shared rounding primitive deliberately uses a cross-family residual
    cap of one display unit.  Family 36 contains source schedules whose
    independently rounded component frontier has more terms.  The exact
    interval for a sum of ``n`` independently rounded components and one
    independently rounded result is ``floor((n + 1) / 2)`` display units.
    This family-local extension remains gated by the existing scaled-unit
    opt-in and requires every source cell to be observed.
    """

    equation = _local_equation(
        equation_kind=(
            "OPERATING_EXPENSE_SOURCE_VISIBLE_DIRECT_COMPONENT_FRONTIER_"
            "EQUALS_TERMINAL_PRINTED_ROOT"
        ),
        components=components,
        result=result,
    )
    if equation["status"] == "EXACT":
        return equation
    if (
        equation["status"] == "INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL"
        and compiled_specs.get("source_total_blank_lane_control_policy")
        == "OBSERVED_LANES_EXACT_REMAINDER_BLANK"
        and "EXACT" in equation.get("lane_statuses", [])
        and set(equation.get("lane_statuses", []))
        <= {"EXACT", "INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL"}
    ):
        return equation
    binding = next(
        (
            item
            for item in compiled_specs.get("unit_bindings", [])
            if item.get("accepted") is True and item.get("canonical_unit") == canonical_unit
        ),
        None,
    )
    if (
        equation["status"] != "MISMATCH"
        or compiled_specs.get("source_presentation_rounding_policy")
        != "INDEPENDENT_DISPLAY_UNIT_ROUNDING_INTERVAL_ALL_EQUATIONS"
        or type(binding) is not dict
        or type(binding.get("magnitude_power10")) is not int
        or binding["magnitude_power10"] < 3
        or canonical_unit == "VND"
        or any(
            type(cell.get("coefficient")) is not int
            for record in [*components, result]
            for cell in record["cells"]
        )
    ):
        return None
    tolerance = (len(components) + 1) // 2
    lane_receipts = []
    for lane_key, expected, observed in zip(
        equation["lane_keys"],
        equation["component_sums"],
        equation["result_coefficients"],
        strict=True,
    ):
        if type(expected) is not int or type(observed) is not int:
            return None
        residual = observed - expected
        if abs(residual) > tolerance:
            return None
        lane_receipts.append(
            {
                "expected_component_sum": expected,
                "lane_key": canonical_clone_v1(lane_key),
                "observed_result": observed,
                "residual": residual,
            }
        )
    if not any(item["residual"] for item in lane_receipts):
        return None
    material = {
        key: canonical_clone_v1(value)
        for key, value in equation.items()
        if key != "equation_id"
    }
    material["status"] = "SOURCE_PRESENTATION_ROUNDING_INTERVAL_EXACT"
    material["source_presentation_rounding_receipt"] = {
        "canonical_unit": canonical_unit,
        "component_count": len(components),
        "lane_receipts": lane_receipts,
        "magnitude_power10": binding["magnitude_power10"],
        "maximum_absolute_display_unit_residual": tolerance,
        "rule": (
            "INDEPENDENT_DISPLAY_UNIT_ROUNDING_INTERVAL_TERM_COUNT_BOUND_"
            "NO_SOURCE_VALUE_CHANGE"
        ),
    }
    return {
        **material,
        "equation_id": "gjmthfev1:equation:" + canonical_json_sha256_v1(material),
    }


def _operating_expense_root_closure_retry(
    *,
    candidate: Mapping[str, Any],
    pages: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]]]:
    """Retain a source-visible root proved by a bounded Family-36 frontier.

    This retry is intentionally narrower than a second evaluator.  It only
    consumes the shared engine's table-local records and equations, requires
    one terminal source TOTAL in one selected table, and admits only the two
    known fail-closed classes: an otherwise unpromoted source root, or a
    directly observed structural parent whose following source rows are a
    demonstrably non-exhaustive detail disclosure.  No value, hierarchy, row
    kind, blank, or unit is changed.
    """

    reasons = candidate.get("reasons")
    if candidate.get("status") != UNRESOLVED or type(reasons) is not list or not reasons:
        return None, [], []
    mapped_subtotal_prefix = "MAPPED_SOURCE_SUBTOTAL_NOT_PROVEN_BY_EXACT_DIRECT_FRONTIER:"
    permitted_exact = {
        "REQUIRED_SOURCE_VISIBLE_EXACT_FAMILY_ROOT_NOT_PROVEN",
        "UNMAPPED_TOP_LEVEL_SOURCE_ONLY_ROW_NOT_DECLARED_VALIDATION_ROLE",
    }
    if any(
        type(reason) is not str
        or (reason not in permitted_exact and not reason.startswith(mapped_subtotal_prefix))
        for reason in reasons
    ):
        return None, [], []
    if type(regions) not in {list, tuple} or len(regions) != 1:
        return None, [], []

    document_unit_context = _document_unit_context_axis(
        pages, compiled_specs=compiled_specs
    )
    extracted_axis = []
    local_records = []
    proven_roles: set[str] = set()
    prior_fragment: dict[str, Any] | None = None
    for region in regions:
        page = pages.get(region.get("page_json_version_id"))
        if type(page) is not dict:
            return None, [], []
        section, table = _source_table(
            page, section_id=region["section_id"], table_id=region["table_id"]
        )
        extracted = _extract_table_local_records(
            page_json=page,
            section=section,
            table=table,
            region=region,
            compiled_specs=compiled_specs,
            document_unit_context=document_unit_context,
            document_period_context={},
            prior_fragment=prior_fragment,
        )
        if extracted.get("unconsumed_reason") is not None:
            return None, [], []
        extracted_axis.append((region, table, extracted))
        local_records.extend(extracted["local_records"])
        proven_roles.update(extracted["proven_roles"])
        prior_fragment = {
            "classification": canonical_clone_v1(extracted["receipt"]["classification"]),
            "lane_axis": canonical_clone_v1(extracted["receipt"]["lane_axis"]),
            "region": canonical_clone_v1(region),
            "section": canonical_clone_v1(section),
            "table": canonical_clone_v1(table),
            "unit_axis": canonical_clone_v1(extracted["receipt"]["unit_axis"]),
        }
    region, table, extracted = extracted_axis[0]
    classification = extracted["receipt"]["classification"]
    lane_axis = extracted["receipt"]["lane_axis"]
    unit_axis = extracted["receipt"]["unit_axis"]
    rows = table.get("rows")
    totals = [
        item
        for item in classification.get("total_rows", [])
        if type(item) is dict and item.get("row_kind") == "TOTAL"
    ]
    if (
        type(rows) is not list
        or not rows
        or totals
        != [
            {
                "row_kind": "TOTAL",
                "row_ordinal": len(rows),
                "source_order": len(rows),
            }
        ]
        or lane_axis.get("complete") is not True
        or unit_axis.get("complete") is not True
        or type(unit_axis.get("canonical_unit")) is not str
        or classification.get("ambiguous_rows")
    ):
        return None, [], []
    total_ordinal = len(rows)
    root_records = [record for record in local_records if record["role"] == "FAMILY_ROOT_TOTAL"]
    if len(root_records) > 1:
        return None, [], []
    root_record = (
        root_records[0]
        if root_records
        else _row_local_record(
            "FAMILY_ROOT_TOTAL",
            total_ordinal,
            rows[-1],
            region=region,
            lane_axis=lane_axis,
            state="SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PENDING_OPERATING_EXPENSE_FRONTIER",
        )
    )
    if root_record is None or any(
        type(cell.get("coefficient")) is not int for cell in root_record["cells"]
    ):
        return None, [], []
    root_key = _source_ref_key(root_record["source_refs"][0])

    direct_records = [
        record
        for record in local_records
        if record.get("state") == "SOURCE_OBSERVED_ROLE_ROW"
        and len(record.get("source_refs", [])) == 1
        and _source_ref_key(record["source_refs"][0]) is not None
    ]
    by_key: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for record in direct_records:
        by_key.setdefault(_source_ref_key(record["source_refs"][0]), []).append(record)

    root_equations = [
        equation
        for equation in candidate.get("closure_receipt", {}).get("equations", [])
        if type(equation) is dict
        and any(
            _source_ref_key(source_ref) == root_key
            for source_ref in equation.get("result_source_refs", [])
        )
        and equation.get("status")
        in {
            "EXACT",
            "INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL",
            "SOURCE_PRESENTATION_ROUNDING_INTERVAL_EXACT",
        }
    ]
    component_records: list[dict[str, Any]] = []
    equation = None
    component_selection_rule = ""
    if len(root_equations) == 1:
        proposed = []
        for source_refs in root_equations[0].get("component_source_refs", []):
            if type(source_refs) is not list or len(source_refs) != 1:
                return None, [], []
            matches = by_key.get(_source_ref_key(source_refs[0]), [])
            if len(matches) != 1:
                return None, [], []
            proposed.append(matches[0])
        if not proposed:
            return None, [], []
        component_records = proposed
        equation = canonical_clone_v1(root_equations[0])
        component_selection_rule = "SHARED_TABLE_LOCAL_SOURCE_TOTAL_EQUATION_FRONTIER"
    elif not root_equations:
        candidates = []
        owner_aliases = _parent_aliases(compiled_specs)
        for record in direct_records:
            if record["role"] not in compiled_specs["root_component_roles"]:
                continue
            source_ref = record["source_refs"][0]
            label = _normalized(source_ref.get("label_exact"))
            path = [
                _normalized(value)
                for value in source_ref.get("hierarchy_path_exact", [])
                if _normalized(value)
            ]
            if path and _without_leading_ordinal(path[0]) in owner_aliases:
                path = path[1:]
            if (
                not label
                or len(path) != 1
                or path[0] != label
                or all(cell.get("coefficient") is None for cell in record["cells"])
            ):
                continue
            candidates.append(record)
        selected_roles = [record["role"] for record in candidates]
        selected_keys = [_source_ref_key(record["source_refs"][0]) for record in candidates]
        if (
            len(candidates)
            < compiled_specs["evaluation"]["minimum_source_visible_root_component_count"]
            or len(set(selected_keys)) != len(selected_keys)
            or not any(
                set(combination) <= set(selected_roles)
                for combination in compiled_specs["topology"]["required_role_combinations"]
            )
            or set(classification.get("unbound_money_row_ordinals", [])) - {total_ordinal}
        ):
            return None, [], []
        component_records = sorted(
            candidates, key=lambda item: item["source_refs"][0]["row_ordinal"]
        )
        equation = _accepted_operating_expense_root_equation(
            components=component_records,
            result=root_record,
            canonical_unit=unit_axis["canonical_unit"],
            compiled_specs=compiled_specs,
        )
        component_selection_rule = (
            "UNIQUE_DECLARED_DIRECT_SOURCE_ROW_ROOT_COMPONENT_FRONTIER"
        )
    else:
        return None, [], []
    if equation is None:
        return None, [], []
    if equation["status"] == "INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL" and not (
        compiled_specs.get("source_total_blank_lane_control_policy")
        == "OBSERVED_LANES_EXACT_REMAINDER_BLANK"
        and "EXACT" in equation.get("lane_statuses", [])
        and set(equation.get("lane_statuses", []))
        <= {"EXACT", "INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL"}
    ):
        return None, [], []

    component_keys = {
        _source_ref_key(source_ref)
        for record in component_records
        for source_ref in record["source_refs"]
    }
    component_ordinals = sorted(
        source_ref["row_ordinal"]
        for record in component_records
        for source_ref in record["source_refs"]
        if source_ref["locator"]["page_json_version_id"] == region["page_json_version_id"]
    )
    nonexhaustive_receipts = []
    subtotal_roles = sorted(
        reason.removeprefix(mapped_subtotal_prefix)
        for reason in reasons
        if reason.startswith(mapped_subtotal_prefix)
    )
    for role in subtotal_roles:
        parents = [record for record in component_records if record["role"] == role]
        if not parents and role in compiled_specs["validation_only_roles"]:
            observations = [record for record in direct_records if record["role"] == role]
            if not observations or any(
                cell.get("coefficient") not in {0, None}
                for record in observations
                for cell in record["cells"]
            ):
                return None, [], []
            material = {
                "role": role,
                "rule": (
                    "SOURCE_VISIBLE_ZERO_OR_BLANK_VALIDATION_WRAPPER_IS_NOT_A_"
                    "ROOT_EQUATION_OPERAND_AND_IS_NEVER_SCHEMA_MAPPED"
                ),
                "source_refs": [
                    canonical_clone_v1(record["source_refs"]) for record in observations
                ],
            }
            nonexhaustive_receipts.append(
                {
                    **material,
                    "receipt_id": "gjoefav1:nonoperand-validation-wrapper:"
                    + canonical_json_sha256_v1(material),
                }
            )
            continue
        if len(parents) != 1:
            return None, [], []
        parent = parents[0]
        parent_ordinal = parent["source_refs"][0]["row_ordinal"]
        next_component = min(
            (ordinal for ordinal in component_ordinals if ordinal > parent_ordinal),
            default=total_ordinal,
        )
        children = [
            record
            for record in direct_records
            if parent_ordinal < record["source_refs"][0]["row_ordinal"] < next_component
            and record["role"] != role
        ]
        if not children:
            return None, [], []
        child_sums = []
        unequal_lanes = []
        for lane, parent_cell in enumerate(parent["cells"]):
            values = [child["cells"][lane].get("coefficient") for child in children]
            child_sum = None if any(type(value) is not int for value in values) else sum(values)
            child_sums.append(child_sum)
            if type(child_sum) is int and child_sum != parent_cell.get("coefficient"):
                unequal_lanes.append(canonical_clone_v1(parent["lane_keys"][lane]))
        if not unequal_lanes:
            return None, [], []
        material = {
            "child_roles": [child["role"] for child in children],
            "child_source_refs": [
                canonical_clone_v1(child["source_refs"]) for child in children
            ],
            "child_sums": child_sums,
            "parent_coefficients": [cell["coefficient"] for cell in parent["cells"]],
            "parent_role": role,
            "parent_source_refs": canonical_clone_v1(parent["source_refs"]),
            "rule": (
                "DIRECT_SOURCE_PARENT_IS_ROOT_EQUATION_OPERAND_AND_FOLLOWING_"
                "BOUNDED_HIERARCHICAL_DETAIL_FRONTIER_IS_ARITHMETICALLY_"
                "NONEXHAUSTIVE_NO_PARENT_OR_CHILD_VALUE_CHANGE"
            ),
            "unequal_lane_keys": unequal_lanes,
        }
        nonexhaustive_receipts.append(
            {
                **material,
                "receipt_id": "gjoefav1:nonexhaustive-parent:"
                + canonical_json_sha256_v1(material),
            }
        )

    root_state = {
        "EXACT": "SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_BY_OPERATING_EXPENSE_DIRECT_FRONTIER",
        "INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL": (
            "SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_WITH_OPERATING_EXPENSE_OBSERVED_LANE_CONTROL"
        ),
        "SOURCE_PRESENTATION_ROUNDING_INTERVAL_EXACT": (
            "SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_BY_OPERATING_EXPENSE_DISPLAY_ROUNDING_INTERVAL"
        ),
    }[equation["status"]]
    root_record = {**root_record, "state": root_state}
    local_without_root = [
        record
        for record in local_records
        if record["role"] != "FAMILY_ROOT_TOTAL"
        and record["role"] not in compiled_specs["validation_only_roles"]
    ]
    records, partial, global_reasons, optional_omissions = _multitable_global_records(
        [*local_without_root, root_record],
        proven_roles={*proven_roles, "FAMILY_ROOT_TOTAL"},
        compiled_specs=compiled_specs,
    )
    if global_reasons or "FAMILY_ROOT_TOTAL" not in records:
        return None, [], []
    mappings = []
    for role in [*compiled_specs["output_role_order"], "FAMILY_ROOT_TOTAL"]:
        record = records.get(role)
        if record is None or role in compiled_specs["validation_only_roles"]:
            continue
        report_norm_id = (
            compiled_specs["schema"]["family_root_report_norm_id"]
            if role == "FAMILY_ROOT_TOTAL"
            else compiled_specs["bindings"][role]
        )
        material = {
            "report_norm_id": report_norm_id,
            "role": role,
            "row_id": (
                record["source_refs"][0]["row_id"]
                if len(record["source_refs"]) == 1
                else "corroborated:" + role
            ),
            "source_refs": canonical_clone_v1(record["source_refs"]),
            "state": record["state"],
            "unit": compiled_specs["role_unit_overrides"].get(
                role, unit_axis["canonical_unit"]
            ),
            "values": canonical_clone_v1(record["cells"]),
        }
        mappings.append(
            {
                **material,
                "item_mapping_id": "gjmthfmv1:item:"
                + canonical_json_sha256_v1(material),
            }
        )

    retried = canonical_clone_v1(candidate)
    retried["mappings"] = mappings
    retried["reasons"] = []
    retried["status"] = READY
    closure = retried["closure_receipt"]
    if not any(
        item.get("equation_id") == equation["equation_id"]
        for item in closure.get("equations", [])
    ):
        closure["equations"].append(canonical_clone_v1(equation))
    closure["partial_role_observations"] = canonical_clone_v1(partial)
    if optional_omissions:
        closure["optional_conditional_omissions"] = canonical_clone_v1(optional_omissions)
    for source_only in [
        *closure.get("source_only_unmapped_rows", []),
        *[
            item
            for receipt in closure.get("table_receipts", [])
            for item in receipt.get("source_only_rows", [])
        ],
    ]:
        if _source_ref_key(source_only.get("source_ref", {})) in component_keys:
            source_only["consumed_by_exact_equation"] = True
    closure["structural_root_receipt"]["emitted_mapping"] = True
    root_sum_receipt = {
        "coefficients": [cell["coefficient"] for cell in root_record["cells"]],
        "component_source_refs": canonical_clone_v1(equation["component_source_refs"]),
        "result_state": root_state,
        "rule": (
            "FAMILY_LOCAL_SOURCE_VISIBLE_ROOT_USES_ONE_BOUNDED_TABLE_LOCAL_"
            "DIRECT_FRONTIER_WITH_EXACT_OR_OBSERVED_LANE_OR_CONFIGURED_"
            "SCALED_PRESENTATION_ROUNDING_PROOF"
        ),
        "source_equation_id": equation["equation_id"],
        "source_refs": canonical_clone_v1(root_record["source_refs"]),
    }
    closure.setdefault("root_component_sum_receipts", []).append(root_sum_receipt)
    receipt_material = {
        "component_roles": [record["role"] for record in component_records],
        "component_selection_rule": component_selection_rule,
        "equation": canonical_clone_v1(equation),
        "original_reasons": canonical_clone_v1(reasons),
        "result_source_refs": canonical_clone_v1(root_record["source_refs"]),
        "rule": (
            "ONE_TERMINAL_SOURCE_TOTAL_ONE_COMPLETE_PERIOD_UNIT_AXIS_"
            "NO_VALUE_HIERARCHY_ROW_KIND_BLANK_OR_UNIT_MUTATION"
        ),
    }
    root_receipt = {
        **receipt_material,
        "receipt_id": "gjoefav1:root-closure:"
        + canonical_json_sha256_v1(receipt_material),
    }
    return retried, [root_receipt], nonexhaustive_receipts


def _continuation_query_recovery(
    *,
    cluster: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]] | None:
    regions = cluster.get("component_regions")
    inventory = cluster.get("declared_money_table_inventory")
    if type(regions) is not list or type(inventory) is not list:
        return None

    selected_by_version: dict[str, dict[str, Any]] = {}
    duplicate_selected_versions: set[str] = set()
    for selected in selected_page_axis:
        if (
            selected.get("document_id") != cluster.get("document_id")
            or selected.get("document_ordinal") != cluster.get("document_ordinal")
            or selected.get("source_sha256") != cluster.get("source_sha256")
        ):
            continue
        version_id = selected.get("page_json_version_id")
        if type(version_id) is not str or version_id in selected_by_version:
            if type(version_id) is str:
                duplicate_selected_versions.add(version_id)
            continue
        selected_by_version[version_id] = canonical_clone_v1(selected)

    def classified_region(
        item: Mapping[str, Any], *, fragment_ordinal: int
    ) -> tuple[dict[str, Any], dict[str, Any]] | None:
        version_id = item.get("page_json_version_id")
        selected = selected_by_version.get(version_id)
        page = pages.get(version_id)
        if (
            version_id in duplicate_selected_versions
            or type(selected) is not dict
            or type(page) is not dict
            or selected.get("physical_page") != item.get("physical_page")
        ):
            return None
        try:
            section, table = _source_table(
                page,
                section_id=item["section_id"],
                table_id=item["table_id"],
            )
        except (KeyError, GeminiJsonOperatingExpenseFamilyV1Error):
            return None
        classification = classify_gemini_json_multitable_hierarchical_table_v1(
            page, section, table, compiled_specs=compiled_specs
        )
        return (
            {
                "component_roles": _classification_roles(classification),
                "document_id": cluster["document_id"],
                "document_ordinal": cluster["document_ordinal"],
                "fragment_ordinal": fragment_ordinal,
                "page_json_version_id": version_id,
                "physical_page": item["physical_page"],
                "section_id": item["section_id"],
                "selected_page_ordinal": selected["selected_page_ordinal"],
                "source_logical_name": cluster["source_logical_name"],
                "source_sha256": cluster["source_sha256"],
                "table_id": item["table_id"],
            },
            classification,
        )

    pair_candidates: list[list[dict[str, Any]]] = []
    if cluster.get("status") == READY and len(regions) == 1:
        prior = canonical_clone_v1(regions[0])
        matching_inventory = [
            item
            for item in inventory
            if type(item) is dict
            and (
                item.get("page_json_version_id"),
                item.get("section_id"),
                item.get("table_id"),
            )
            == (
                prior.get("page_json_version_id"),
                prior.get("section_id"),
                prior.get("table_id"),
            )
        ]
        if len(matching_inventory) != 1:
            return None
        prior_result = classified_region(matching_inventory[0], fragment_ordinal=1)
        if prior_result is None:
            return None
        prior = prior_result[0]
        for item in inventory:
            if (
                type(item) is not dict
                or item.get("physical_page") != prior.get("physical_page", -2) + 1
                or item.get("section_id") != "s1"
                or item.get("table_id") != "t1"
                or item.get("disposition") == "SELECTED_FAMILY_COMPONENT"
            ):
                continue
            receiver_result = classified_region(item, fragment_ordinal=2)
            if receiver_result is not None:
                pair_candidates.append([prior, receiver_result[0]])
    elif cluster.get("status") == UNRESOLVED and regions == []:
        reasons = cluster.get("reasons")
        if type(reasons) is not list or len(reasons) != 1:
            return None
        match = re.fullmatch(
            r"UNCONSUMED_MONEY_TABLE_INSIDE_OWNER_FENCE:"
            r"(gfpstorev1:json:[0-9a-f]{64}):(s[1-9][0-9]*):(t[1-9][0-9]*)",
            reasons[0],
        )
        if match is None:
            return None
        receiver_items = [
            item
            for item in inventory
            if type(item) is dict
            and item.get("page_json_version_id") == match[1]
            and item.get("section_id") == match[2]
            and item.get("table_id") == match[3]
            and item.get("disposition") == "UNCONSUMED_MONEY_TABLE_INSIDE_OWNER_FENCE"
        ]
        if len(receiver_items) != 1:
            return None
        receiver_item = receiver_items[0]
        receiver_result = classified_region(receiver_item, fragment_ordinal=2)
        if receiver_result is None:
            return None
        receiver = receiver_result[0]
        prior_results = []
        for item in inventory:
            if (
                type(item) is not dict
                or item.get("disposition") != "SELECTED_FAMILY_COMPONENT"
                or item.get("physical_page") != receiver.get("physical_page", 0) - 1
            ):
                continue
            result = classified_region(item, fragment_ordinal=1)
            if result is None:
                continue
            prior, classification = result
            prior_page = pages.get(prior["page_json_version_id"])
            if type(prior_page) is not dict:
                continue
            _section, _table = _source_table(
                prior_page,
                section_id=prior["section_id"],
                table_id=prior["table_id"],
            )
            if (
                prior.get("selected_page_ordinal") != receiver.get("selected_page_ordinal", 0) - 1
                or classification.get("owner_visible") is not True
                or classification.get("family_presence_anchor_visible") is not True
                or classification.get("typed_control_disposition") is not None
                or not _is_last_source_table_on_page(
                    prior_page,
                    section_id=prior["section_id"],
                    table_id=prior["table_id"],
                )
            ):
                continue
            prior_results.append(prior)
        if len(prior_results) != 1:
            return None
        pair_candidates.append([prior_results[0], receiver])
    elif cluster.get("status") == NOT_OBSERVED and regions == []:
        # One KLB presentation starts the Family-36 schedule inside a table
        # that also carries three preceding notes.  The raw reciprocal marker
        # and exact physical/selected adjacency are still visible even though
        # the shared owner query correctly selected no region.  Offer only
        # exact last-table BOTH -> page-leading FROM_PREVIOUS pairs here; the
        # internal-owner projection below applies the remaining unique blank
        # GROUP-owner, suffix-role, lane, unit, and terminal-total gates.
        prior_results: list[dict[str, Any]] = []
        receiver_results: list[dict[str, Any]] = []
        for item in inventory:
            if type(item) is not dict:
                continue
            result = classified_region(
                item,
                fragment_ordinal=(
                    2
                    if item.get("section_id") == "s1" and item.get("table_id") == "t1"
                    else 1
                ),
            )
            if result is None:
                continue
            region, _classification = result
            page = pages.get(region["page_json_version_id"])
            if type(page) is not dict:
                continue
            _section, table = _source_table(
                page,
                section_id=region["section_id"],
                table_id=region["table_id"],
            )
            if table.get("continuation") == "BOTH" and _is_last_source_table_on_page(
                page,
                section_id=region["section_id"],
                table_id=region["table_id"],
            ):
                prior_results.append(region)
            if (
                table.get("continuation") == "CONTINUES_FROM_PREVIOUS_PAGE"
                and region.get("section_id") == "s1"
                and region.get("table_id") == "t1"
            ):
                receiver_results.append(region)
        for prior in prior_results:
            for receiver in receiver_results:
                if (
                    receiver.get("physical_page") == prior.get("physical_page", -2) + 1
                    and receiver.get("selected_page_ordinal")
                    == prior.get("selected_page_ordinal", -2) + 1
                ):
                    prior["fragment_ordinal"] = 1
                    receiver["fragment_ordinal"] = 2
                    pair_candidates.append([prior, receiver])
    else:
        return None

    candidates = []
    for pair in pair_candidates:
        projected = _continuation_projection(
            pages=pages,
            regions=pair,
            compiled_specs=compiled_specs,
        )
        if projected is not None:
            candidates.append((pair, projected[2]))
    return candidates[0] if len(candidates) == 1 else None


def _unique_complete_owner_region_recovery(
    *,
    cluster: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]] | None:
    """Select one structurally complete owner table from an over-wide fence.

    This is the family-local implementation of the declarative
    ``EXACT_OWNER_WHOLE_MONEY_TABLE`` opt-in.  It never consults arithmetic:
    one table must expose the exact owner, a complete required role
    combination, and one terminal printed TOTAL.  A duplicate qualifying
    table or any ambiguous row leaves the original query disposition intact.
    """

    inventory = cluster.get("declared_money_table_inventory")
    original_regions = cluster.get("component_regions")
    if (
        compiled_specs.get("owner_complete_population_policy") != "EXACT_OWNER_WHOLE_MONEY_TABLE"
        or cluster.get("status") not in {READY, UNRESOLVED}
        or type(inventory) is not list
        or type(original_regions) is not list
        or (
            cluster.get("status") == UNRESOLVED
            and cluster.get("reasons") != ["COMPLETE_OWNER_CLUSTER_NOT_RESOLVED"]
        )
    ):
        return None

    selected_by_version = {
        item.get("page_json_version_id"): item
        for item in selected_page_axis
        if item.get("document_id") == cluster.get("document_id")
        and item.get("document_ordinal") == cluster.get("document_ordinal")
        and item.get("source_sha256") == cluster.get("source_sha256")
    }
    candidates: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for item in inventory:
        if type(item) is not dict:
            continue
        page = pages.get(item.get("page_json_version_id"))
        selected = selected_by_version.get(item.get("page_json_version_id"))
        if (
            type(page) is not dict
            or type(selected) is not dict
            or selected.get("physical_page") != item.get("physical_page")
        ):
            continue
        section, table = _source_table(
            page, section_id=item["section_id"], table_id=item["table_id"]
        )
        classification = classify_gemini_json_multitable_hierarchical_table_v1(
            page, section, table, compiled_specs=compiled_specs
        )
        role_hits = classification.get("role_hits")
        total_rows = classification.get("total_rows")
        money_ordinals = classification.get("money_column_ordinals")
        rows = table.get("rows")
        if (
            classification.get("owner_visible") is not True
            or classification.get("family_presence_anchor_visible") is not True
            or classification.get("typed_control_disposition") is not None
            or classification.get("ambiguous_rows")
            or type(role_hits) is not list
            or type(total_rows) is not list
            or type(money_ordinals) is not list
            or len(money_ordinals) != 2
            or type(rows) is not list
        ):
            continue
        total_ordinals = {
            row.get("row_ordinal")
            for row in total_rows
            if type(row) is dict and row.get("row_kind") == "TOTAL"
        }
        observed_ordinals = {
            hit.get("row_ordinal") for hit in role_hits if type(hit) is dict
        } | set(classification.get("unbound_money_row_ordinals", []))
        declared_roles = {hit.get("role") for hit in role_hits if type(hit) is dict}
        if (
            len(total_ordinals) != 1
            or not observed_ordinals
            or max(observed_ordinals | total_ordinals) not in total_ordinals
            or not any(
                set(combination) <= declared_roles
                for combination in compiled_specs["topology"]["required_role_combinations"]
            )
            or len(declared_roles.intersection(compiled_specs["root_component_roles"]))
            < compiled_specs["evaluation"]["minimum_source_visible_root_component_count"]
        ):
            continue
        region = {
            "component_roles": _classification_roles(classification),
            "document_id": cluster["document_id"],
            "document_ordinal": cluster["document_ordinal"],
            "fragment_ordinal": 1,
            "page_json_version_id": item["page_json_version_id"],
            "physical_page": item["physical_page"],
            "section_id": item["section_id"],
            "selected_page_ordinal": selected["selected_page_ordinal"],
            "source_logical_name": cluster["source_logical_name"],
            "source_sha256": cluster["source_sha256"],
            "table_id": item["table_id"],
        }
        evidence = {
            "classification_id": classification["classification_id"],
            "declared_roles": sorted(declared_roles),
            "money_column_ordinals": canonical_clone_v1(money_ordinals),
            "region": _region_locator(region),
            "required_role_combinations": canonical_clone_v1(
                compiled_specs["topology"]["required_role_combinations"]
            ),
            "terminal_total_row_ordinal": next(iter(total_ordinals)),
        }
        candidates.append((region, evidence))
    if len(candidates) != 1:
        return None
    region, evidence = candidates[0]
    original_region_axis = [
        _region_locator(item) for item in original_regions if type(item) is dict
    ]
    if original_region_axis == [_region_locator(region)] and cluster.get("status") == READY:
        return None
    material = {
        "original_cluster_id": cluster.get("cluster_id"),
        "original_reasons": canonical_clone_v1(cluster.get("reasons", [])),
        "original_region_axis": original_region_axis,
        "rule": (
            "UNIQUE_EXACT_OWNER_WHOLE_MONEY_TABLE_WITH_REQUIRED_DECLARED_ROLES_"
            "AND_ONE_TERMINAL_SOURCE_TOTAL"
        ),
        "selected_owner_evidence": evidence,
    }
    return [region], {
        **material,
        "receipt_id": "gjoefav1:owner-region-recovery:" + canonical_json_sha256_v1(material),
    }


def _titleless_primary_corroborated_region_recovery(
    *,
    cluster: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]] | None:
    """Recover one titleless complete schedule from exact primary-root proof.

    This path is intentionally narrower than ordinary owner recovery.  It is
    available only when the shared query found no semantic owner, the table is
    the final source table on its page, every money row is classified except
    one terminal TOTAL, and that TOTAL exactly matches a same-document primary
    operating-expense root under one canonical source unit.  Values, row kinds,
    hierarchy, period headers, and units are never changed by this query step.
    """

    inventory = cluster.get("declared_money_table_inventory")
    regions = cluster.get("component_regions")
    if (
        cluster.get("status") != NOT_OBSERVED
        or regions != []
        or type(inventory) is not list
    ):
        return None
    selected_by_version: dict[str, dict[str, Any]] = {}
    duplicate_versions: set[str] = set()
    for selected in selected_page_axis:
        if (
            selected.get("document_id") != cluster.get("document_id")
            or selected.get("document_ordinal") != cluster.get("document_ordinal")
            or selected.get("source_sha256") != cluster.get("source_sha256")
        ):
            continue
        version_id = selected.get("page_json_version_id")
        if type(version_id) is not str or version_id in selected_by_version:
            if type(version_id) is str:
                duplicate_versions.add(version_id)
            continue
        selected_by_version[version_id] = canonical_clone_v1(selected)

    primary_roots = _primary_operating_expense_roots(
        pages=pages,
        selected_page_axis=selected_page_axis,
        document_ordinal=cluster["document_ordinal"],
        compiled_specs=compiled_specs,
    )
    candidates: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for item in inventory:
        if type(item) is not dict:
            continue
        version_id = item.get("page_json_version_id")
        selected = selected_by_version.get(version_id)
        page = pages.get(version_id)
        if (
            version_id in duplicate_versions
            or type(selected) is not dict
            or type(page) is not dict
            or selected.get("physical_page") != item.get("physical_page")
        ):
            continue
        try:
            section, table = _source_table(
                page,
                section_id=item["section_id"],
                table_id=item["table_id"],
            )
        except (KeyError, GeminiJsonOperatingExpenseFamilyV1Error):
            continue
        if (
            section.get("title_exact") is not None
            or section.get("narratives_exact") not in (None, [])
            or table.get("title_exact") is not None
            or table.get("continuation") != "NONE"
            or table.get("unit_exact") is not None
            or not _is_last_source_table_on_page(
                page,
                section_id=item["section_id"],
                table_id=item["table_id"],
            )
        ):
            continue
        classification = classify_gemini_json_multitable_hierarchical_table_v1(
            page, section, table, compiled_specs=compiled_specs
        )
        rows = table.get("rows")
        role_hits = classification.get("role_hits")
        total_rows = classification.get("total_rows")
        money_ordinals = classification.get("money_column_ordinals")
        lane_axis = _duration_multitable_lane_axis(table, compiled_specs=compiled_specs)
        if (
            classification.get("owner_visible") is not False
            or classification.get("family_presence_anchor_visible") is not True
            or classification.get("typed_control_disposition") is not None
            or classification.get("ambiguous_rows")
            or type(rows) is not list
            or len(rows) < 3
            or type(role_hits) is not list
            or type(total_rows) is not list
            or type(money_ordinals) is not list
            or len(money_ordinals) != 2
            or lane_axis.get("complete") is not True
            or total_rows
            != [
                {
                    "row_kind": "TOTAL",
                    "row_ordinal": len(rows),
                    "source_order": len(rows),
                }
            ]
            or classification.get("unbound_money_row_ordinals") != [len(rows)]
            or {hit.get("row_ordinal") for hit in role_hits if type(hit) is dict}
            != set(range(1, len(rows)))
        ):
            continue
        declared_roles = {
            hit.get("role")
            for hit in role_hits
            if type(hit) is dict and type(hit.get("role")) is str
        }
        if (
            not any(
                set(combination) <= declared_roles
                for combination in compiled_specs["topology"]["required_role_combinations"]
            )
            or len(declared_roles.intersection(compiled_specs["root_component_roles"]))
            < compiled_specs["evaluation"]["minimum_source_visible_root_component_count"]
        ):
            continue
        region = {
            "component_roles": _classification_roles(classification),
            "document_id": cluster["document_id"],
            "document_ordinal": cluster["document_ordinal"],
            "fragment_ordinal": 1,
            "page_json_version_id": version_id,
            "physical_page": item["physical_page"],
            "section_id": item["section_id"],
            "selected_page_ordinal": selected["selected_page_ordinal"],
            "source_logical_name": cluster["source_logical_name"],
            "source_sha256": cluster["source_sha256"],
            "table_id": item["table_id"],
        }
        target = _target_total_observation(
            pages=pages,
            regions=[region],
            compiled_specs=compiled_specs,
        )
        if target is None:
            continue
        matches = []
        for root in primary_roots:
            root_vector = root["vector"]
            target_vector = target["vector"]
            for start in range(len(root_vector) - len(target_vector) + 1):
                window = root_vector[start : start + len(target_vector)]
                if window == target_vector:
                    match_kind = "EXACT_SIGNED_COEFFICIENT_VECTOR"
                elif [abs(value) for value in window] == [
                    abs(value) for value in target_vector
                ]:
                    match_kind = (
                        "EXACT_MAGNITUDE_VECTOR_WITH_SOURCE_PRESENTATION_SIGN_DIFFERENCE"
                    )
                else:
                    continue
                matches.append(
                    {
                        **canonical_clone_v1(root),
                        "match_kind": match_kind,
                        "matched_money_column_ordinals": root["money_column_ordinals"][
                            start : start + len(target_vector)
                        ],
                        "matched_vector": canonical_clone_v1(window),
                    }
                )
        units = {match["canonical_unit"] for match in matches}
        if not matches or len(units) != 1:
            continue
        evidence = {
            "classification_id": classification["classification_id"],
            "declared_roles": sorted(declared_roles),
            "lane_axis": canonical_clone_v1(lane_axis),
            "matched_primary_roots": matches,
            "region": _region_locator(region),
            "target_total_observation": canonical_clone_v1(target),
            "unique_canonical_unit": next(iter(units)),
        }
        candidates.append((region, evidence))
    if len(candidates) != 1:
        return None
    region, evidence = candidates[0]
    material = {
        "original_cluster_id": cluster.get("cluster_id"),
        "original_reasons": canonical_clone_v1(cluster.get("reasons", [])),
        "rule": (
            "UNIQUE_TITLELESS_UNITLESS_FINAL_SOURCE_TABLE_WITH_COMPLETE_PERIOD_"
            "AXIS_EXACT_DECLARED_OPERATING_EXPENSE_ROLES_ONE_TERMINAL_TOTAL_AND_"
            "SAME_DOCUMENT_PRIMARY_OPERATING_EXPENSE_ROOT_VECTOR_PROOF"
        ),
        "selected_region_evidence": evidence,
    }
    return [region], {
        **material,
        "receipt_id": "gjoefav1:titleless-primary-region-recovery:"
        + canonical_json_sha256_v1(material),
    }


def build_gemini_json_operating_expense_indexed_query_evidence_v1(
    *,
    base_indexed_query_evidence: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Add only one exact reciprocal adjacent operating-expense receiver."""

    base = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        base_indexed_query_evidence,
        compiled_specs=compiled_specs,
    )
    clusters = []
    for disposition in base["candidate_dispositions"]:
        cluster = canonical_clone_v1(disposition["cluster"])
        pages = page_json_by_document.get(disposition["document_ordinal"])
        titleless_recovered = (
            _titleless_primary_corroborated_region_recovery(
                cluster=cluster,
                selected_page_axis=base["selected_page_axis"],
                pages=pages,
                compiled_specs=compiled_specs,
            )
            if type(pages) is dict
            else None
        )
        if titleless_recovered is not None:
            regions, receipt = titleless_recovered
            selected_locator = _region_locator(regions[0])
            for item in cluster["declared_money_table_inventory"]:
                if all(
                    item.get(key) == selected_locator[key]
                    for key in (
                        "page_json_version_id",
                        "physical_page",
                        "section_id",
                        "table_id",
                    )
                ):
                    item["disposition"] = (
                        "SELECTED_UNIQUE_TITLELESS_OPERATING_EXPENSE_TABLE_"
                        "CORROBORATED_BY_PRIMARY_ROOT"
                    )
            cluster["component_regions"] = canonical_clone_v1(regions)
            cluster["operating_expense_titleless_primary_region_recovery_receipt"] = (
                canonical_clone_v1(receipt)
            )
            cluster["reasons"] = []
            cluster["status"] = READY
        owner_recovered = (
            _unique_complete_owner_region_recovery(
                cluster=cluster,
                selected_page_axis=base["selected_page_axis"],
                pages=pages,
                compiled_specs=compiled_specs,
            )
            if type(pages) is dict
            else None
        )
        if owner_recovered is not None:
            regions, receipt = owner_recovered
            selected_locator = {
                key: regions[0][key]
                for key in (
                    "page_json_version_id",
                    "physical_page",
                    "section_id",
                    "table_id",
                )
            }
            for item in cluster["declared_money_table_inventory"]:
                item_locator = {
                    key: item.get(key)
                    for key in (
                        "page_json_version_id",
                        "physical_page",
                        "section_id",
                        "table_id",
                    )
                }
                if item_locator == selected_locator:
                    item["disposition"] = (
                        "SELECTED_UNIQUE_EXACT_OPERATING_EXPENSE_OWNER_WHOLE_TABLE"
                    )
                elif item.get("disposition") == "SELECTED_FAMILY_COMPONENT":
                    item["disposition"] = (
                        "EXCLUDED_OUTSIDE_UNIQUE_EXACT_OPERATING_EXPENSE_OWNER_TABLE"
                    )
            cluster["component_regions"] = canonical_clone_v1(regions)
            cluster["operating_expense_owner_region_recovery_receipt"] = canonical_clone_v1(receipt)
            cluster["reasons"] = []
            cluster["status"] = READY
        recovered = (
            _continuation_query_recovery(
                cluster=cluster,
                selected_page_axis=base["selected_page_axis"],
                pages=pages,
                compiled_specs=compiled_specs,
            )
            if type(pages) is dict
            else None
        )
        if recovered is not None:
            regions, receipt = recovered
            receiver = regions[-1]
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
                        "SELECTED_RECIPROCAL_OPERATING_EXPENSE_CONTINUATION_AFTER_FAMILY36_RECEIPT"
                    )
            cluster["component_regions"] = canonical_clone_v1(regions)
            cluster["operating_expense_continuation_query_receipt"] = canonical_clone_v1(receipt)
            cluster["reasons"] = []
            cluster["status"] = READY
        material = {key: item for key, item in cluster.items() if key != "cluster_id"}
        cluster["cluster_id"] = "gjmthfcv1:cluster:" + canonical_json_sha256_v1(material)
        clusters.append(cluster)
    evidence = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=base["selected_document_axis"],
        selected_page_axis=base["selected_page_axis"],
        document_clusters=clusters,
        query_policy_sha256=canonical_json_sha256_v1(compiled_specs["query_policy"]),
    )
    return validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        evidence,
        compiled_specs=compiled_specs,
    )


def _reseal_candidate(
    candidate: dict[str, Any],
    *,
    all_blank_validation_role_omission_receipts: Sequence[Mapping[str, Any]],
    continuation_projection_receipts: Sequence[Mapping[str, Any]],
    nonexhaustive_parent_receipts: Sequence[Mapping[str, Any]],
    root_closure_receipts: Sequence[Mapping[str, Any]],
    source_repair_receipts: Sequence[Mapping[str, Any]],
    unit_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    material = {
        "adapter_format_version": ADAPTER_FORMAT_VERSION,
        "all_blank_validation_role_omission_receipts": canonical_clone_v1(
            list(all_blank_validation_role_omission_receipts)
        ),
        "continuation_projection_receipts": canonical_clone_v1(
            list(continuation_projection_receipts)
        ),
        "nonexhaustive_parent_receipts": canonical_clone_v1(
            list(nonexhaustive_parent_receipts)
        ),
        "root_closure_receipts": canonical_clone_v1(list(root_closure_receipts)),
        "shared_engine_claim_boundary": SHARED_CLAIM_BOUNDARY,
        "source_repair_receipts": canonical_clone_v1(list(source_repair_receipts)),
        "unit_corroboration_receipts": canonical_clone_v1(list(unit_receipts)),
    }
    candidate["claim_boundary"] = CLAIM_BOUNDARY
    candidate["closure_receipt"]["operating_expense_adapter_receipt"] = {
        **material,
        "adapter_receipt_id": "gjoefav1:receipt:" + canonical_json_sha256_v1(material),
    }
    candidate_material = {key: value for key, value in candidate.items() if key != "candidate_id"}
    candidate["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        candidate_material
    )
    return candidate


def evaluate_gemini_json_operating_expense_family_cluster_v1(
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    selected_page_axis: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate one Family-36 cluster after exact unit corroboration."""

    if compiled_specs.get("topology", {}).get("family_id") != FAMILY_ID:
        raise _error("operating-expense adapter received another family")
    expected = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
    if type(query_receipt) is not dict or not same_typed_json_v1(query_receipt, expected):
        raise _error("operating-expense query receipt does not bind exact fragments")
    region_axis = expected["region_axis"]
    pages, source_repair_receipts = _apply_authenticated_source_repairs(
        pages=page_json_by_version,
        regions=region_axis,
        compiled_specs=compiled_specs,
    )
    continuation = _continuation_projection(
        pages=pages,
        regions=region_axis,
        compiled_specs=compiled_specs,
    )
    continuation_receipts = []
    if continuation is not None:
        projected_pages, projected_regions, continuation_receipt = continuation
        if not same_typed_json_v1(continuation_receipt["original_query_receipt"], query_receipt):
            raise _error("operating-expense continuation query receipt drifted")
        continuation_receipts = [continuation_receipt]
        evaluation_pages = projected_pages
        evaluation_regions = projected_regions
        evaluation_query_receipt = continuation_receipt["projected_query_receipt"]
        unit_receipts = _bind_exact_primary_statement_unit(
            pages=evaluation_pages,
            regions=evaluation_regions,
            selected_page_axis=selected_page_axis,
            compiled_specs=compiled_specs,
        )
    else:
        unit_receipts = _bind_exact_primary_statement_unit(
            pages=pages,
            regions=region_axis,
            selected_page_axis=selected_page_axis,
            compiled_specs=compiled_specs,
        )
        evaluation_pages = pages
        evaluation_regions = region_axis
        evaluation_query_receipt = query_receipt
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=evaluation_regions,
        page_json_by_version=evaluation_pages,
        compiled_specs=compiled_specs,
        query_receipt=evaluation_query_receipt,
    )
    all_blank_receipts: list[dict[str, Any]] = []
    if candidate.get("status") == UNRESOLVED:
        retried, all_blank_receipts = _all_blank_validation_role_omission_retry(
            pages=evaluation_pages,
            regions=evaluation_regions,
            compiled_specs=compiled_specs,
            query_receipt=evaluation_query_receipt,
        )
        if retried is not None:
            candidate = retried
    root_closure_receipts: list[dict[str, Any]] = []
    nonexhaustive_parent_receipts: list[dict[str, Any]] = []
    if candidate.get("status") == UNRESOLVED:
        (
            retried,
            root_closure_receipts,
            nonexhaustive_parent_receipts,
        ) = _operating_expense_root_closure_retry(
            candidate=candidate,
            pages=evaluation_pages,
            regions=evaluation_regions,
            compiled_specs=compiled_specs,
        )
        if retried is not None:
            candidate = retried
    if continuation is not None:
        _restore_continuation_mapping_source_refs(
            candidate,
            receipt=continuation_receipts[0],
        )
    return _reseal_candidate(
        candidate,
        all_blank_validation_role_omission_receipts=all_blank_receipts,
        continuation_projection_receipts=continuation_receipts,
        nonexhaustive_parent_receipts=nonexhaustive_parent_receipts,
        root_closure_receipts=root_closure_receipts,
        source_repair_receipts=source_repair_receipts,
        unit_receipts=unit_receipts,
    )


def build_gemini_json_operating_expense_trials_v1(
    *,
    indexed_query_evidence: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Evaluate every selected Family-36 cluster and preserve all dispositions."""

    evidence = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
    pages_by_document: dict[int, list[dict[str, Any]]] = {}
    for page in evidence["selected_page_axis"]:
        pages_by_document.setdefault(page["document_ordinal"], []).append(page)
    trials = []
    for disposition in evidence["candidate_dispositions"]:
        cluster = disposition["cluster"]
        document_ordinal = disposition["document_ordinal"]
        candidates = []
        mappings = []
        reasons = []
        selected_candidate_id = None
        status = disposition["disposition"]
        if status == READY:
            regions = cluster["component_regions"]
            candidate = evaluate_gemini_json_operating_expense_family_cluster_v1(
                regions=regions,
                page_json_by_version=page_json_by_document[document_ordinal],
                selected_page_axis=pages_by_document[document_ordinal],
                compiled_specs=compiled_specs,
                query_receipt=(
                    build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
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
            raise _error("operating-expense query disposition is invalid")
        trials.append(
            {
                "candidate_count": len(candidates),
                "candidates": candidates,
                "document_ordinal": document_ordinal,
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


def _coverage_row_locator(
    *,
    source_sha256: str,
    page_json_version_id: str,
    section_id: str,
    table_id: str,
    row_ordinal: int,
) -> tuple[str, str, str, str, int]:
    return (
        source_sha256,
        page_json_version_id,
        section_id,
        table_id,
        row_ordinal,
    )


def _coverage_source_row(
    *,
    coverage: str,
    document: Mapping[str, Any],
    page_axis: Mapping[str, Any],
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    section_id: str,
    table_id: str,
    row: Mapping[str, Any],
    row_ordinal: int,
    role: str | None = None,
    report_norm_id: int | None = None,
    evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    item = {
        "coverage": coverage,
        "document_ordinal": document["document_ordinal"],
        "hierarchy_path_exact": canonical_clone_v1(
            row.get("hierarchy_path_exact", [])
        ),
        "label_exact": row.get("label_exact"),
        "page_json_version_id": page_axis["page_json_version_id"],
        "physical_page": page_axis["physical_page"],
        "report_norm_id": report_norm_id,
        "role": role,
        "row_id": row.get("row_id", f"r{row_ordinal}"),
        "row_kind": row.get("row_kind"),
        "row_ordinal": row_ordinal,
        "section_id": section_id,
        "section_title_exact": section.get("title_exact"),
        "source_logical_name": document["source_logical_name"],
        "source_sha256": document["source_sha256"],
        "statement_type": section.get("statement_type"),
        "table_id": table_id,
        "table_title_exact": table.get("title_exact"),
        "values_exact": canonical_clone_v1(row.get("values_exact")),
    }
    if evidence is not None:
        item["evidence"] = canonical_clone_v1(evidence)
    return item


def _raw_configured_operating_expense_roles(
    label_exact: Any, *, compiled_specs: Mapping[str, Any]
) -> list[str]:
    """Return exact configured aliases without relying on table classification."""

    if type(label_exact) is not str or not label_exact.strip():
        return []
    surface = _without_leading_ordinal(_normalized(label_exact))
    roles = []
    for child in compiled_specs.get("topology", {}).get("children", []):
        if type(child) is not dict or type(child.get("role")) is not str:
            continue
        aliases = {
            _normalized(alias)
            for matcher in child.get("matchers", [])
            if type(matcher) is dict
            for alias in matcher.get("aliases", [])
            if type(alias) is str
        }
        if surface in aliases:
            roles.append(child["role"])
    return sorted(set(roles))


def _raw_operating_expense_target_surface(
    *,
    row: Mapping[str, Any],
    configured_roles: Sequence[str],
    root_surface: bool,
    selected_row: bool,
    terminal_total: bool,
    visible: bool,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Find target-like rows independently of configured classifier hits."""

    label_exact = row.get("label_exact")
    exact_alias_roles = _raw_configured_operating_expense_roles(
        label_exact, compiled_specs=compiled_specs
    )
    normalized = (
        _without_leading_ordinal(_normalized(label_exact))
        if type(label_exact) is str
        else ""
    )
    root_like = bool(
        root_surface
        or normalized.startswith("chi phi hoat dong")
        or normalized.startswith("chi hoat dong")
    )
    if root_surface:
        kind = "EXACT_FAMILY_ROOT_OR_OWNER_ROW"
    elif terminal_total:
        kind = "SELECTED_TERMINAL_TOTAL_ROW"
    elif configured_roles or exact_alias_roles:
        kind = "CONFIGURED_FAMILY_ROLE_SURFACE"
    elif selected_row and visible:
        kind = "VISIBLE_ROW_INSIDE_SELECTED_OPERATING_EXPENSE_REGION"
    elif root_like:
        kind = "RAW_OPERATING_EXPENSE_ROOT_LIKE_SURFACE"
    else:
        return None
    return {
        "configured_alias_roles": exact_alias_roles,
        "configured_classification_roles": sorted(set(configured_roles)),
        "kind": kind,
        "root_like": root_like,
        "surface_exact": label_exact,
    }


def _coverage_source_ref_identity(
    *,
    source_ref: Any,
    document: Mapping[str, Any],
    page_axis: Mapping[str, Mapping[str, Any]],
    pages: Mapping[str, Mapping[str, Any]],
    strict: bool,
) -> tuple[str, str, str, str, int] | None:
    """Resolve one receipt source ref to an exact selected raw source row."""

    try:
        if type(source_ref) is not dict:
            raise _error("operating-expense coverage source ref is invalid")
        locator = source_ref.get("locator")
        row_ordinal = source_ref.get("row_ordinal")
        if (
            type(locator) is not dict
            or type(row_ordinal) is not int
            or row_ordinal <= 0
            or type(locator.get("page_json_version_id")) is not str
            or type(locator.get("section_id")) is not str
            or type(locator.get("table_id")) is not str
        ):
            raise _error("operating-expense coverage source-row locator is invalid")
        version_id = locator["page_json_version_id"]
        axis = page_axis.get(version_id)
        page = pages.get(version_id)
        if type(axis) is not dict or type(page) is not dict:
            raise _error("operating-expense coverage source-row page is not selected")
        if (
            locator.get("document_ordinal", document["document_ordinal"])
            != document["document_ordinal"]
            or locator.get("source_sha256", document["source_sha256"])
            != document["source_sha256"]
            or locator.get("source_logical_name", document["source_logical_name"])
            != document["source_logical_name"]
            or locator.get("physical_page", axis["physical_page"])
            != axis["physical_page"]
        ):
            raise _error("operating-expense coverage source-row identity drifted")
        section, table = _source_table(
            page,
            section_id=locator["section_id"],
            table_id=locator["table_id"],
        )
        rows = table.get("rows")
        if type(rows) is not list or not 1 <= row_ordinal <= len(rows):
            raise _error("operating-expense coverage source-row locator does not resolve")
        row = rows[row_ordinal - 1]
        if type(row) is not dict:
            raise _error("operating-expense coverage source row is invalid")
        expected_row_id = row.get("row_id", f"r{row_ordinal}")
        for field, expected in (
            ("hierarchy_path_exact", row.get("hierarchy_path_exact", [])),
            ("label_exact", row.get("label_exact")),
            ("row_id", expected_row_id),
            ("row_kind", row.get("row_kind")),
        ):
            if (
                field in source_ref
                and not (field == "row_id" and source_ref[field] is None)
                and not same_typed_json_v1(source_ref[field], expected)
            ):
                raise _error("operating-expense coverage source-row before-image drifted")
        return _coverage_row_locator(
            source_sha256=document["source_sha256"],
            page_json_version_id=version_id,
            section_id=locator["section_id"],
            table_id=locator["table_id"],
            row_ordinal=row_ordinal,
        )
    except (
        GeminiJsonOperatingExpenseFamilyV1Error,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        if strict:
            raise _error(
                "operating-expense coverage source-row locator is invalid"
            ) from exc
        return None


def _coverage_candidate_receipt_sets(
    *,
    trial: Mapping[str, Any],
    document: Mapping[str, Any],
    page_axis: Mapping[str, Mapping[str, Any]],
    pages: Mapping[str, Mapping[str, Any]],
) -> tuple[
    set[tuple[str, str, str, str, int]],
    dict[tuple[str, str, str, str, int], set[str]],
    dict[tuple[str, str, str, str, int], set[str]],
]:
    """Collect equation, source-only, and all-blank raw-row receipts."""

    equation_rows: set[tuple[str, str, str, str, int]] = set()
    source_only_roles: dict[tuple[str, str, str, str, int], set[str]] = {}
    all_blank_roles: dict[tuple[str, str, str, str, int], set[str]] = {}

    def resolved(source_ref: Any) -> tuple[str, str, str, str, int] | None:
        return _coverage_source_ref_identity(
            source_ref=source_ref,
            document=document,
            page_axis=page_axis,
            pages=pages,
            strict=False,
        )

    candidates = trial.get("candidates", [])
    if type(candidates) is not list:
        raise _error("operating-expense coverage candidate axis is invalid")
    for candidate in candidates:
        if type(candidate) is not dict:
            raise _error("operating-expense coverage candidate is invalid")
        closure = candidate.get("closure_receipt")
        if type(closure) is not dict:
            raise _error("operating-expense coverage closure receipt is invalid")
        for equation in closure.get("equations", []):
            if type(equation) is not dict:
                raise _error("operating-expense coverage equation is invalid")
            groups = equation.get("component_source_refs", [])
            result_refs = equation.get("result_source_refs", [])
            if type(groups) is not list or type(result_refs) is not list:
                raise _error("operating-expense coverage equation source axis is invalid")
            for group in groups:
                if type(group) is not list:
                    raise _error("operating-expense coverage equation component is invalid")
                for source_ref in group:
                    identity = resolved(source_ref)
                    if identity is not None:
                        equation_rows.add(identity)
            for source_ref in result_refs:
                identity = resolved(source_ref)
                if identity is not None:
                    equation_rows.add(identity)
        source_only_axis = [*closure.get("source_only_unmapped_rows", [])]
        for table_receipt in closure.get("table_receipts", []):
            if type(table_receipt) is not dict:
                raise _error("operating-expense coverage table receipt is invalid")
            source_only_axis.extend(table_receipt.get("source_only_rows", []))
        for item in source_only_axis:
            if type(item) is not dict:
                raise _error("operating-expense source-only receipt is invalid")
            identity = resolved(item.get("source_ref"))
            role = item.get("declared_validation_role", item.get("declared_role"))
            if identity is not None and type(role) is str:
                source_only_roles.setdefault(identity, set()).add(role)
                if item.get("consumed_by_exact_equation") is True:
                    equation_rows.add(identity)
        adapter = closure.get("operating_expense_adapter_receipt", {})
        if type(adapter) is not dict:
            raise _error("operating-expense coverage adapter receipt is invalid")
        for omission in adapter.get(
            "all_blank_validation_role_omission_receipts", []
        ):
            if type(omission) is not dict or type(omission.get("role")) is not str:
                raise _error("operating-expense all-blank receipt is invalid")
            role = omission["role"]
            observations = omission.get("source_observations")
            if type(observations) is not list or not observations:
                raise _error("operating-expense all-blank observation axis is invalid")
            for observation in observations:
                identity = resolved(observation)
                if identity is not None:
                    all_blank_roles.setdefault(identity, set()).add(role)
    return equation_rows, source_only_roles, all_blank_roles


def build_operating_expense_source_row_coverage_receipt_v1(
    *,
    indexed_query_evidence: Mapping[str, Any],
    trials: Sequence[Mapping[str, Any]],
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
    fail_on_violation: bool = True,
) -> dict[str, Any]:
    """Classify every configured or raw Family-36 source row and fail closed."""

    indexed = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
    documents = indexed["selected_document_axis"]
    if (
        compiled_specs.get("topology", {}).get("family_id") != FAMILY_ID
        or type(trials) not in {list, tuple}
        or len(trials) != len(documents)
        or type(page_json_by_document) is not dict
        or type(fail_on_violation) is not bool
    ):
        raise _error("operating-expense source-row coverage input is invalid")

    page_axis_by_document: dict[int, dict[str, dict[str, Any]]] = {}
    for page_axis in indexed["selected_page_axis"]:
        ordinal = page_axis["document_ordinal"]
        version_id = page_axis["page_json_version_id"]
        by_version = page_axis_by_document.setdefault(ordinal, {})
        if version_id in by_version:
            raise _error("operating-expense coverage selected page axis is duplicate")
        by_version[version_id] = page_axis
    expected_ordinals = {document["document_ordinal"] for document in documents}
    if set(page_json_by_document) != expected_ordinals:
        raise _error("operating-expense coverage document page frontier is incomplete")

    mapped_rows: set[tuple[str, str, str, str, int]] = set()
    mapped_role_rows: set[tuple[str, str, str, str, int, str]] = set()
    mapped_roles_by_identity: dict[
        tuple[str, str, str, str, int], set[str]
    ] = {}
    equation_rows: set[tuple[str, str, str, str, int]] = set()
    source_only_roles: dict[tuple[str, str, str, str, int], set[str]] = {}
    all_blank_roles: dict[tuple[str, str, str, str, int], set[str]] = {}
    for ordinal, (trial, document, disposition) in enumerate(
        zip(trials, documents, indexed["candidate_dispositions"], strict=True),
        start=1,
    ):
        if (
            type(trial) is not dict
            or document["document_ordinal"] != ordinal
            or trial.get("document_ordinal") != ordinal
            or trial.get("source_logical_name") != document["source_logical_name"]
            or trial.get("source_sha256") != document["source_sha256"]
            or disposition.get("document_ordinal") != ordinal
        ):
            raise _error("operating-expense source-row coverage trial identity drifted")
        pages = page_json_by_document.get(ordinal)
        axes = page_axis_by_document.get(ordinal)
        if type(pages) is not dict or type(axes) is not dict or set(pages) != set(axes):
            raise _error("operating-expense coverage selected page frontier is incomplete")
        bindings = compiled_specs.get("bindings", {})
        root_report_norm_id = compiled_specs.get("schema", {}).get(
            "family_root_report_norm_id"
        )
        mappings = trial.get("mappings")
        if type(mappings) is not list:
            raise _error("operating-expense coverage mapping axis is invalid")
        for mapping in mappings:
            if type(mapping) is not dict or type(mapping.get("role")) is not str:
                raise _error("operating-expense coverage mapping is invalid")
            role = mapping["role"]
            expected_report_norm_id = (
                root_report_norm_id if role == "FAMILY_ROOT_TOTAL" else bindings.get(role)
            )
            refs = mapping.get("source_refs")
            if (
                type(expected_report_norm_id) is not int
                or mapping.get("report_norm_id") != expected_report_norm_id
                or type(refs) is not list
                or not refs
            ):
                raise _error("operating-expense coverage mapping binding drifted")
            for source_ref in refs:
                identity = _coverage_source_ref_identity(
                    source_ref=source_ref,
                    document=document,
                    page_axis=axes,
                    pages=pages,
                    strict=True,
                )
                assert identity is not None
                mapped_rows.add(identity)
                mapped_role_rows.add((*identity, role))
                mapped_roles_by_identity.setdefault(identity, set()).add(role)
        candidate_sets = _coverage_candidate_receipt_sets(
            trial=trial,
            document=document,
            page_axis=axes,
            pages=pages,
        )
        equation_rows.update(candidate_sets[0])
        for identity, roles in candidate_sets[1].items():
            source_only_roles.setdefault(identity, set()).update(roles)
        for identity, roles in candidate_sets[2].items():
            all_blank_roles.setdefault(identity, set()).update(roles)

    source_rows: dict[str, dict[str, Any]] = {}
    total_rows: dict[str, dict[str, Any]] = {}
    raw_rows: dict[str, dict[str, Any]] = {}
    violations: dict[str, dict[str, Any]] = {}
    bindings = compiled_specs["bindings"]
    validation_only = set(compiled_specs.get("validation_only_roles", []))
    root_report_norm_id = compiled_specs["schema"]["family_root_report_norm_id"]

    for disposition, document, _trial in zip(
        indexed["candidate_dispositions"], documents, trials, strict=True
    ):
        document_ordinal = document["document_ordinal"]
        axes = page_axis_by_document[document_ordinal]
        source_pages = page_json_by_document[document_ordinal]
        cluster = disposition.get("cluster")
        if type(cluster) is not dict or type(cluster.get("component_regions")) is not list:
            raise _error("operating-expense coverage cluster is invalid")
        pages, _repair_receipts = _apply_authenticated_source_repairs(
            pages=source_pages,
            regions=cluster["component_regions"],
            compiled_specs=compiled_specs,
        )
        selected_tables = {
            (
                region.get("page_json_version_id"),
                region.get("section_id"),
                region.get("table_id"),
            )
            for region in cluster["component_regions"]
            if type(region) is dict
        }
        internal_owner_rows: dict[tuple[str, str, str], int] = {}
        continuation_receipt = cluster.get(
            "operating_expense_continuation_query_receipt", {}
        )
        internal = (
            continuation_receipt.get("internal_owner_projection", {})
            if type(continuation_receipt) is dict
            else {}
        )
        internal_locator = internal.get("raw_prior_locator")
        owner_ordinal = internal.get("owner_row_ordinal")
        if type(internal_locator) is dict and type(owner_ordinal) is int:
            internal_owner_rows[
                (
                    internal_locator.get("page_json_version_id"),
                    internal_locator.get("section_id"),
                    internal_locator.get("table_id"),
                )
            ] = owner_ordinal
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
            page_axis = axes.get(page_json_version_id)
            if type(page_axis) is not dict or type(page) is not dict:
                raise _error("operating-expense coverage page frontier drifted")
            for section_ordinal, section in enumerate(
                page.get("sections", []), start=1
            ):
                if type(section) is not dict:
                    continue
                section_id = f"s{section_ordinal}"
                tables = section.get("tables", [])
                if type(tables) is not list:
                    raise _error("operating-expense coverage table axis is invalid")
                for table_ordinal, table in enumerate(tables, start=1):
                    if type(table) is not dict:
                        continue
                    table_id = f"t{table_ordinal}"
                    table_key = (page_json_version_id, section_id, table_id)
                    table_selected = table_key in selected_tables
                    owner_row_ordinal = internal_owner_rows.get(table_key)
                    inventory = inventory_by_table.get(table_key, {})
                    classification = (
                        classify_gemini_json_multitable_hierarchical_table_v1(
                            page, section, table, compiled_specs=compiled_specs
                        )
                    )
                    money_ordinals = classification.get(
                        "money_column_ordinals", _money_column_ordinals(table)
                    )
                    if type(money_ordinals) is not list:
                        money_ordinals = _money_column_ordinals(table)
                    rows = table.get("rows")
                    if type(rows) is not list:
                        continue
                    hit_by_row: dict[int, set[str]] = {}
                    for hit in classification.get("role_hits", []):
                        if (
                            type(hit) is dict
                            and type(hit.get("row_ordinal")) is int
                            and type(hit.get("role")) is str
                        ):
                            hit_by_row.setdefault(hit["row_ordinal"], set()).add(
                                hit["role"]
                            )
                    visible_by_row = {}
                    for row_ordinal, row in enumerate(rows, start=1):
                        values = row.get("values_exact") if type(row) is dict else None
                        visible_by_row[row_ordinal] = bool(
                            type(values) is list
                            and any(
                                type(column_ordinal) is int
                                and 1 <= column_ordinal <= len(values)
                                and values[column_ordinal - 1] is not None
                                for column_ordinal in money_ordinals
                            )
                        )
                    selected_ordinals = [
                        row_ordinal
                        for row_ordinal in range(1, len(rows) + 1)
                        if table_selected
                        and (
                            owner_row_ordinal is None
                            or row_ordinal > owner_row_ordinal
                        )
                    ]
                    terminal_ordinal = None
                    if selected_ordinals:
                        last_selected = selected_ordinals[-1]
                        last_row = rows[last_selected - 1]
                        if type(last_row) is dict and last_row.get("row_kind") == "TOTAL":
                            terminal_ordinal = last_selected
                    for row_ordinal, row in enumerate(rows, start=1):
                        if type(row) is not dict:
                            continue
                        identity = _coverage_row_locator(
                            source_sha256=document["source_sha256"],
                            page_json_version_id=page_json_version_id,
                            section_id=section_id,
                            table_id=table_id,
                            row_ordinal=row_ordinal,
                        )
                        visible = visible_by_row[row_ordinal]
                        selected_row = row_ordinal in selected_ordinals
                        internal_owner = owner_row_ordinal == row_ordinal
                        roles = set(hit_by_row.get(row_ordinal, set()))
                        roles.update(
                            mapped_roles_by_identity.get(identity, set())
                            - {"FAMILY_ROOT_TOTAL"}
                        )
                        roles.update(source_only_roles.get(identity, set()))
                        roles.update(all_blank_roles.get(identity, set()))
                        for role in sorted(roles):
                            report_norm_id = bindings.get(role)
                            if (*identity, role) in mapped_role_rows:
                                coverage = "MAPPED_EXACT_SOURCE_ROLE_ROW"
                            elif identity in mapped_rows:
                                coverage = "CONSUMED_BY_EXACT_SOURCE_DERIVATION"
                            elif role in all_blank_roles.get(identity, set()):
                                coverage = (
                                    "ALL_BLANK_VALIDATION_ROLE_OMISSION_SOURCE_ONLY"
                                )
                            elif role in source_only_roles.get(identity, set()):
                                coverage = (
                                    "EQUATION_CONSUMED_DECLARED_SOURCE_ONLY_ROLE_ROW"
                                    if identity in equation_rows
                                    else "DECLARED_SOURCE_ONLY_ROLE_ROW"
                                )
                            elif not visible:
                                coverage = "BLANK_STRUCTURAL_ROLE_ROW_SOURCE_ONLY"
                            elif section.get("content_kind") == "PRIMARY_STATEMENT":
                                coverage = (
                                    "PRIMARY_STATEMENT_CONFIGURED_ROLE_CONTROL_SOURCE_ONLY"
                                )
                            elif selected_row and role in bindings:
                                coverage = (
                                    "VIOLATION_UNMAPPED_SELECTED_SCHEMA_ROLE_ROW"
                                )
                            elif selected_row and role in validation_only:
                                coverage = "DECLARED_VALIDATION_ONLY_SOURCE_ROW"
                            else:
                                coverage = (
                                    "OUTSIDE_SELECTED_OPERATING_EXPENSE_CONTEXT_SOURCE_ONLY"
                                )
                            item = _coverage_source_row(
                                coverage=coverage,
                                document=document,
                                page_axis=page_axis,
                                section=section,
                                table=table,
                                section_id=section_id,
                                table_id=table_id,
                                row=row,
                                row_ordinal=row_ordinal,
                                role=role,
                                report_norm_id=report_norm_id,
                                evidence={
                                    "equation_consumed": identity in equation_rows,
                                    "inventory_disposition": inventory.get(
                                        "disposition"
                                    ),
                                    "money_column_ordinals": canonical_clone_v1(
                                        money_ordinals
                                    ),
                                    "owner_visible": classification.get(
                                        "owner_visible"
                                    ),
                                    "table_selected": table_selected,
                                    "selected_row": selected_row,
                                },
                            )
                            item_id = canonical_json_sha256_v1(item)
                            source_rows.setdefault(item_id, item)
                            if coverage.startswith("VIOLATION_"):
                                violations.setdefault(item_id, item)
                        root_surface = _is_parent_label(
                            row.get("label_exact"), compiled_specs=compiled_specs
                        )
                        if root_surface:
                            if (*identity, "FAMILY_ROOT_TOTAL") in mapped_role_rows:
                                coverage = "MAPPED_EXACT_FAMILY_ROOT_ROW"
                            elif internal_owner and not visible:
                                coverage = (
                                    "BLANK_SELECTED_FAMILY_OWNER_ROOT_HEADING_SOURCE_ONLY"
                                )
                            elif not visible:
                                coverage = "BLANK_FAMILY_ROOT_HEADING_SOURCE_ONLY"
                            elif section.get("content_kind") == "PRIMARY_STATEMENT":
                                coverage = (
                                    "PRIMARY_STATEMENT_FAMILY_ROOT_CONTROL_SOURCE_ONLY"
                                )
                            elif selected_row:
                                coverage = (
                                    "VIOLATION_UNMAPPED_SELECTED_FAMILY_ROOT_ROW"
                                )
                            else:
                                coverage = (
                                    "OUTSIDE_SELECTED_OPERATING_EXPENSE_ROOT_SOURCE_ONLY"
                                )
                            item = _coverage_source_row(
                                coverage=coverage,
                                document=document,
                                page_axis=page_axis,
                                section=section,
                                table=table,
                                section_id=section_id,
                                table_id=table_id,
                                row=row,
                                row_ordinal=row_ordinal,
                                role="OPERATING_EXPENSE",
                                report_norm_id=root_report_norm_id,
                                evidence={
                                    "internal_owner_row": internal_owner,
                                    "inventory_disposition": inventory.get(
                                        "disposition"
                                    ),
                                    "table_selected": table_selected,
                                    "selected_row": selected_row,
                                },
                            )
                            item_id = canonical_json_sha256_v1(item)
                            source_rows.setdefault(item_id, item)
                            if coverage.startswith("VIOLATION_"):
                                violations.setdefault(item_id, item)
                        terminal_total = terminal_ordinal == row_ordinal
                        if terminal_total:
                            if (*identity, "FAMILY_ROOT_TOTAL") in mapped_role_rows:
                                coverage = "MAPPED_EXACT_TERMINAL_FAMILY_TOTAL"
                            elif not visible:
                                coverage = "BLANK_STRUCTURAL_TERMINAL_TOTAL"
                            else:
                                coverage = (
                                    "VIOLATION_UNMAPPED_VISIBLE_TERMINAL_TOTAL"
                                )
                            item = _coverage_source_row(
                                coverage=coverage,
                                document=document,
                                page_axis=page_axis,
                                section=section,
                                table=table,
                                section_id=section_id,
                                table_id=table_id,
                                row=row,
                                row_ordinal=row_ordinal,
                                role="FAMILY_ROOT_TOTAL",
                                report_norm_id=root_report_norm_id,
                                evidence={
                                    "money_column_ordinals": canonical_clone_v1(
                                        money_ordinals
                                    ),
                                    "table_selected": True,
                                },
                            )
                            item_id = canonical_json_sha256_v1(item)
                            total_rows.setdefault(item_id, item)
                            if coverage.startswith("VIOLATION_"):
                                violations.setdefault(item_id, item)
                        raw_target = _raw_operating_expense_target_surface(
                            row=row,
                            configured_roles=sorted(roles),
                            root_surface=root_surface,
                            selected_row=selected_row,
                            terminal_total=terminal_total,
                            visible=visible,
                            compiled_specs=compiled_specs,
                        )
                        if raw_target is None:
                            continue
                        if roles or root_surface:
                            coverage = "ACCOUNTED_CONFIGURED_FAMILY_SOURCE_ROW"
                        elif terminal_total and (
                            *identity,
                            "FAMILY_ROOT_TOTAL",
                        ) in mapped_role_rows:
                            coverage = "ACCOUNTED_MAPPED_TERMINAL_TOTAL_ROW"
                        elif identity in mapped_rows:
                            coverage = "ACCOUNTED_MAPPED_SOURCE_ROW"
                        elif (
                            identity in equation_rows
                            and identity in source_only_roles
                        ):
                            coverage = (
                                "ACCOUNTED_EXACT_EQUATION_SOURCE_ONLY_ROW"
                            )
                        elif section.get("content_kind") == "PRIMARY_STATEMENT":
                            coverage = (
                                "PRIMARY_STATEMENT_OPERATING_EXPENSE_CONTROL_SOURCE_ONLY"
                            )
                        elif selected_row and visible:
                            coverage = (
                                "VIOLATION_UNCLASSIFIED_VISIBLE_OPERATING_EXPENSE_ROW"
                            )
                        elif selected_row:
                            coverage = "BLANK_STRUCTURAL_TARGET_ROW_SOURCE_ONLY"
                        else:
                            coverage = (
                                "OUTSIDE_SELECTED_OPERATING_EXPENSE_CONTEXT_SOURCE_ONLY"
                            )
                        item = _coverage_source_row(
                            coverage=coverage,
                            document=document,
                            page_axis=page_axis,
                            section=section,
                            table=table,
                            section_id=section_id,
                            table_id=table_id,
                            row=row,
                            row_ordinal=row_ordinal,
                            evidence={
                                **raw_target,
                                "inventory_disposition": inventory.get(
                                    "disposition"
                                ),
                                "table_selected": table_selected,
                                "selected_row": selected_row,
                            },
                        )
                        item_id = canonical_json_sha256_v1(item)
                        raw_rows.setdefault(item_id, item)
                        if coverage.startswith("VIOLATION_"):
                            violations.setdefault(item_id, item)

    source_row_axis = [source_rows[key] for key in sorted(source_rows)]
    candidate_table_total_row_axis = [total_rows[key] for key in sorted(total_rows)]
    raw_target_like_row_axis = [raw_rows[key] for key in sorted(raw_rows)]
    violation_axis = [violations[key] for key in sorted(violations)]

    def disposition_counts(axis: Sequence[Mapping[str, Any]]) -> dict[str, int]:
        return {
            coverage: sum(item["coverage"] == coverage for item in axis)
            for coverage in sorted({item["coverage"] for item in axis})
        }

    material = {
        "candidate_table_total_disposition_counts": disposition_counts(
            candidate_table_total_row_axis
        ),
        "candidate_table_total_row_axis": candidate_table_total_row_axis,
        "candidate_table_total_row_axis_sha256": canonical_json_sha256_v1(
            candidate_table_total_row_axis
        ),
        "family_id": FAMILY_ID,
        "format_version": SOURCE_ROW_COVERAGE_FORMAT_VERSION,
        "raw_target_like_disposition_counts": disposition_counts(
            raw_target_like_row_axis
        ),
        "raw_target_like_row_axis": raw_target_like_row_axis,
        "raw_target_like_row_axis_sha256": canonical_json_sha256_v1(
            raw_target_like_row_axis
        ),
        "source_row_disposition_counts": disposition_counts(source_row_axis),
        "source_row_axis": source_row_axis,
        "source_row_axis_sha256": canonical_json_sha256_v1(source_row_axis),
        "violation_axis": violation_axis,
        "violation_count": len(violation_axis),
    }
    receipt = {
        **material,
        "receipt_id": "gjoefav1:source-row-coverage:"
        + canonical_json_sha256_v1(material),
    }
    if violation_axis and fail_on_violation:
        preview = ", ".join(
            (
                f"d{item.get('document_ordinal')}:p{item.get('physical_page')}:"
                f"{item.get('section_id')}/{item.get('table_id')}/"
                f"r{item.get('row_ordinal')}={item.get('coverage')}"
            )
            for item in violation_axis[:20]
        )
        raise _error(
            f"operating-expense source-row coverage has {len(violation_axis)} "
            f"violation(s): {preview}"
        )
    return receipt


def validate_gemini_json_operating_expense_candidate_replay_v1(
    value: Any,
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    selected_page_axis: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    expected = evaluate_gemini_json_operating_expense_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        selected_page_axis=selected_page_axis,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if type(value) is not dict or not same_typed_json_v1(value, expected):
        raise _error("operating-expense candidate replay drifted")
    return expected


def validate_gemini_json_operating_expense_replay_v1(
    *,
    indexed_query_evidence: Any,
    trials: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    expected = build_gemini_json_operating_expense_trials_v1(
        indexed_query_evidence=indexed_query_evidence,
        page_json_by_document=page_json_by_document,
        compiled_specs=compiled_specs,
    )
    if type(trials) is not list or not same_typed_json_v1(trials, expected):
        raise _error("operating-expense sweep replay drifted")
    return expected
