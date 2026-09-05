"""Family-29 source adapter for interest-expense disclosures.

The shared multi-table hierarchical evaluator remains the accounting and
schema-mapping authority.  This adapter is deliberately limited to two kinds
of source evidence that cannot be reconstructed from arithmetic:

* exact PDF-authenticated transcription repairs on immutable selected pages;
* an otherwise unitless note whose exact visible total matches one canonical
  unit on the same document's primary interest-expense statement row.

Every transformation is applied to a private clone.  A blank source cell is
never converted to zero and no missing value is backsolved from a total.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
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
    _classification_roles,
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
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FAMILY_ID = "INTEREST_EXPENSE"
ADAPTER_FORMAT_VERSION = "GEMINI_JSON_INTEREST_EXPENSE_FAMILY_ADAPTER_V1"
SOURCE_REPAIR_FORMAT_VERSION = "INTEREST_EXPENSE_AUTHENTICATED_SOURCE_REPAIR_SPEC_V1"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_DECLARATIVE_INTEREST_EXPENSE_"
    "MULTITABLE_HIERARCHICAL_AUTHENTICATED_PDF_VISIBLE_SOURCE_REPAIR_AND_"
    "EXACT_SAME_DOCUMENT_PRIMARY_STATEMENT_UNIT_CORROBORATION_PRIVATE_CLONE_"
    "ONLY_NO_BLANK_ZERO_NO_NUMERIC_BACKSOLVE_NO_MAGNITUDE_UNIT_INFERENCE_"
    "NO_BANK_FILE_YEAR_PAGE_VALUE_ROUTING_PROPOSAL_ONLY_" + SHARED_CLAIM_BOUNDARY
)

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_PAGE_VERSION = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_SECTION_ID = re.compile(r"s[1-9][0-9]*\Z")
_TABLE_ID = re.compile(r"t[1-9][0-9]*\Z")
_REPAIR_ID = re.compile(r"gjiefav1:repair:[0-9a-f]{64}\Z")
_UNIT_SURFACE = {"MILLION_VND": "Triệu đồng", "VND": "VND"}


class GeminiJsonInterestExpenseFamilyV1Error(ValueError):
    """Family-29 source evidence, candidate, or replay drifted."""


def _error(message: str) -> GeminiJsonInterestExpenseFamilyV1Error:
    return GeminiJsonInterestExpenseFamilyV1Error(message)


def _valid_locator(value: Any) -> bool:
    return bool(
        type(value) is dict
        and set(value)
        == {
            "page_json_version_id",
            "physical_page",
            "section_id",
            "table_id",
        }
        and _PAGE_VERSION.fullmatch(value.get("page_json_version_id", ""))
        and type(value.get("physical_page")) is int
        and value["physical_page"] > 0
        and _SECTION_ID.fullmatch(value.get("section_id", ""))
        and _TABLE_ID.fullmatch(value.get("table_id", ""))
    )


def _valid_exact_row(value: Any) -> bool:
    return bool(
        type(value) is dict
        and set(value)
        == {"hierarchy_path_exact", "label_exact", "row_kind", "values_exact"}
        and type(value.get("hierarchy_path_exact")) is list
        and value["hierarchy_path_exact"]
        and all(item is None or type(item) is str for item in value["hierarchy_path_exact"])
        and (value.get("label_exact") is None or type(value.get("label_exact")) is str)
        and type(value.get("row_kind")) is str
        and bool(value["row_kind"])
        and type(value.get("values_exact")) is list
        and value["values_exact"]
        and all(item is None or type(item) is str for item in value["values_exact"])
    )


def _valid_corroboration(value: Any) -> bool:
    return bool(
        type(value) is dict
        and set(value)
        == {
            "column_ordinal",
            "page_json_version_id",
            "pdf_page_render_sha256",
            "physical_page",
            "row_ordinal",
            "section_id",
            "source_logical_name",
            "source_sha256",
            "table_id",
            "value_exact",
        }
        and _PAGE_VERSION.fullmatch(value.get("page_json_version_id", ""))
        and _SHA256.fullmatch(value.get("pdf_page_render_sha256", ""))
        and _SHA256.fullmatch(value.get("source_sha256", ""))
        and type(value.get("source_logical_name")) is str
        and bool(value["source_logical_name"])
        and type(value.get("physical_page")) is int
        and value["physical_page"] > 0
        and _SECTION_ID.fullmatch(value.get("section_id", ""))
        and _TABLE_ID.fullmatch(value.get("table_id", ""))
        and type(value.get("row_ordinal")) is int
        and value["row_ordinal"] > 0
        and type(value.get("column_ordinal")) is int
        and value["column_ordinal"] > 0
        and type(value.get("value_exact")) is str
        and bool(value["value_exact"])
    )


def _validate_source_repairs(value: Any) -> list[dict[str, Any]]:
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
        or not value["repairs"]
    ):
        raise _error("interest-expense authenticated source-repair spec is invalid")

    checked = []
    identities: set[tuple[Any, ...]] = set()
    ids: set[str] = set()
    for raw in value["repairs"]:
        kind = raw.get("repair_kind") if type(raw) is dict else None
        common = {
            "locator",
            "pdf_page_render_sha256",
            "repair_id",
            "repair_kind",
            "source_sha256",
        }
        if kind == "APPEND_ROWS_PDF_VISIBLE_EXACT":
            fields = common | {"after_rows_exact", "before_row_count"}
        elif kind == "MONEY_CELL_CROSS_SOURCE_CORROBORATED_EXACT":
            fields = common | {
                "after_exact",
                "before_exact",
                "column_ordinal",
                "corroboration",
                "row_ordinal",
            }
        else:
            fields = common | {
                "after_exact",
                "before_exact",
                "column_ordinal",
                "row_ordinal",
            }
        if (
            type(raw) is not dict
            or set(raw) != fields
            or kind
            not in {
                "APPEND_ROWS_PDF_VISIBLE_EXACT",
                "MONEY_CELL_CROSS_SOURCE_CORROBORATED_EXACT",
                "MONEY_CELL_PDF_VISIBLE_EXACT",
            }
            or not _valid_locator(raw.get("locator"))
            or _SHA256.fullmatch(raw.get("source_sha256", "")) is None
            or _SHA256.fullmatch(raw.get("pdf_page_render_sha256", "")) is None
            or _REPAIR_ID.fullmatch(raw.get("repair_id", "")) is None
        ):
            raise _error("interest-expense authenticated source repair is invalid")
        if kind == "APPEND_ROWS_PDF_VISIBLE_EXACT":
            if (
                type(raw.get("before_row_count")) is not int
                or raw["before_row_count"] < 0
                or type(raw.get("after_rows_exact")) is not list
                or not raw["after_rows_exact"]
                or not all(_valid_exact_row(row) for row in raw["after_rows_exact"])
            ):
                raise _error("interest-expense appended-row repair is invalid")
            identity = (
                raw["source_sha256"],
                raw["locator"]["page_json_version_id"],
                raw["locator"]["section_id"],
                raw["locator"]["table_id"],
                "ROWS_AFTER",
            )
        else:
            if (
                type(raw.get("row_ordinal")) is not int
                or raw["row_ordinal"] <= 0
                or type(raw.get("column_ordinal")) is not int
                or raw["column_ordinal"] <= 0
                or (
                    raw.get("before_exact") is not None
                    and type(raw.get("before_exact")) is not str
                )
                or type(raw.get("after_exact")) is not str
                or not raw["after_exact"]
                or (
                    kind == "MONEY_CELL_PDF_VISIBLE_EXACT"
                    and raw["after_exact"] != "-"
                )
                or (
                    kind == "MONEY_CELL_CROSS_SOURCE_CORROBORATED_EXACT"
                    and not _valid_corroboration(raw.get("corroboration"))
                )
            ):
                raise _error("interest-expense money-cell repair is invalid")
            if kind == "MONEY_CELL_CROSS_SOURCE_CORROBORATED_EXACT" and (
                raw["corroboration"]["value_exact"] != raw["after_exact"]
                or raw["corroboration"]["source_sha256"] == raw["source_sha256"]
            ):
                raise _error("interest-expense cross-source corroboration is invalid")
            identity = (
                raw["source_sha256"],
                raw["locator"]["page_json_version_id"],
                raw["locator"]["section_id"],
                raw["locator"]["table_id"],
                raw["row_ordinal"],
                raw["column_ordinal"],
            )
        material = {
            key: canonical_clone_v1(item)
            for key, item in raw.items()
            if key != "repair_id"
        }
        if raw["repair_id"] != "gjiefav1:repair:" + canonical_json_sha256_v1(material):
            raise _error("interest-expense source-repair identity drifted")
        if identity in identities or raw["repair_id"] in ids:
            raise _error("interest-expense source-repair axis is duplicate")
        identities.add(identity)
        ids.add(raw["repair_id"])
        checked.append(canonical_clone_v1(raw))
    return checked


def compile_gemini_json_interest_expense_family_specs_v1(
    topology_spec: Any,
    evaluation_spec: Any,
    schema_binding_spec: Any,
    source_repair_spec: Any,
) -> dict[str, Any]:
    """Compile the Family-29 declarative frontier and source evidence."""

    try:
        compiled = compile_gemini_json_multitable_hierarchical_family_specs_v1(
            topology_spec, evaluation_spec, schema_binding_spec
        )
    except ValueError as exc:
        raise _error("interest-expense declarative family specs are invalid") from exc
    if (
        compiled.get("topology", {}).get("family_id") != FAMILY_ID
        or compiled.get("evaluation", {}).get("family_id") != FAMILY_ID
        or compiled.get("schema", {}).get("family_id") != FAMILY_ID
        or set(compiled.get("bindings", {}))
        != {
            "BORROWING_INTEREST",
            "DEPOSIT_INTEREST",
            "FINANCE_LEASE_INTEREST",
            "ISSUED_PAPER_INTEREST",
            "OTHER_CREDIT_EXPENSE",
        }
        or {
            item["canonical_unit"]
            for item in compiled.get("unit_bindings", [])
            if item.get("accepted") is True
        }
        != {"MILLION_VND", "VND"}
    ):
        raise _error("interest-expense compiled family frontier is invalid")
    compiled["interest_expense_source_repairs"] = _validate_source_repairs(
        source_repair_spec
    )
    compiled["interest_expense_source_repair_spec_sha256"] = canonical_json_sha256_v1(
        source_repair_spec
    )
    compiled["interest_expense_adapter_format_version"] = ADAPTER_FORMAT_VERSION
    return compiled


def _source_table(
    page_json: Mapping[str, Any], *, section_id: str, table_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        section = page_json["sections"][int(section_id[1:]) - 1]
        table = section["tables"][int(table_id[1:]) - 1]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise _error("interest-expense source locator does not resolve one table") from exc
    if type(section) is not dict or type(table) is not dict:
        raise _error("interest-expense source table is invalid")
    return section, table


def _repair_receipt(
    repair: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    material = {
        "repair": canonical_clone_v1(repair),
        "rule": (
            "EXACT_IMMUTABLE_SOURCE_SELECTED_PAGE_PDF_RENDER_TABLE_ROW_COLUMN_"
            "BEFORE_IMAGE_TO_VISIBLE_SOURCE_TRANSCRIPTION_ONLY"
        ),
        "source_repair_spec_sha256": compiled_specs[
            "interest_expense_source_repair_spec_sha256"
        ],
        "status": "AUTHENTICATED_SOURCE_REPAIR_APPLIED_TO_PRIVATE_CLONE",
    }
    return {
        **material,
        "receipt_id": "gjiefav1:repair-receipt:"
        + canonical_json_sha256_v1(material),
    }


def _document_repairs(
    *,
    regions: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    if not regions:
        raise _error("interest-expense source-repair region axis is empty")
    source_sha256s = {region.get("source_sha256") for region in regions}
    if len(source_sha256s) != 1:
        raise _error("interest-expense cluster crosses source documents")
    source_sha256 = next(iter(source_sha256s))
    pages = {
        version_id: canonical_clone_v1(page)
        for version_id, page in page_json_by_version.items()
    }
    region_keys = {
        (
            region.get("page_json_version_id"),
            region.get("physical_page"),
            region.get("section_id"),
            region.get("table_id"),
        )
        for region in regions
    }
    applicable = [
        repair
        for repair in compiled_specs.get("interest_expense_source_repairs", [])
        if repair["source_sha256"] == source_sha256
    ]
    receipts = []
    for repair in applicable:
        locator = repair["locator"]
        key = (
            locator["page_json_version_id"],
            locator["physical_page"],
            locator["section_id"],
            locator["table_id"],
        )
        if key not in region_keys:
            raise _error("interest-expense repair is outside its selected family region")
        page = pages.get(locator["page_json_version_id"])
        if type(page) is not dict:
            raise _error("interest-expense repair page is outside the selected document")
        _section, table = _source_table(
            page,
            section_id=locator["section_id"],
            table_id=locator["table_id"],
        )
        rows = table.get("rows")
        columns = table.get("columns")
        if type(rows) is not list or type(columns) is not list:
            raise _error("interest-expense repair table axes are invalid")
        if repair["repair_kind"] == "APPEND_ROWS_PDF_VISIBLE_EXACT":
            if len(rows) != repair["before_row_count"]:
                raise _error("interest-expense appended-row before-image drifted")
            for row in repair["after_rows_exact"]:
                if len(row["values_exact"]) != len(columns):
                    raise _error("interest-expense appended row width is invalid")
                rows.append(canonical_clone_v1(row))
        else:
            row_ordinal = repair["row_ordinal"]
            column_ordinal = repair["column_ordinal"]
            if not (1 <= row_ordinal <= len(rows) and 1 <= column_ordinal <= len(columns)):
                raise _error("interest-expense repair cell is outside its source table")
            row = rows[row_ordinal - 1]
            values = row.get("values_exact") if type(row) is dict else None
            if (
                type(row) is not dict
                or type(values) is not list
                or len(values) != len(columns)
                or columns[column_ordinal - 1].get("value_kind") != "MONEY"
                or not same_typed_json_v1(
                    values[column_ordinal - 1], repair["before_exact"]
                )
            ):
                raise _error("interest-expense money-cell before-image drifted")
            values[column_ordinal - 1] = repair["after_exact"]
        receipts.append(_repair_receipt(repair, compiled_specs=compiled_specs))
    return pages, receipts


def _money_column_ordinals(table: Mapping[str, Any]) -> list[int]:
    columns = table.get("columns")
    return [
        ordinal
        for ordinal, column in enumerate(
            columns if type(columns) is list else [], start=1
        )
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]


def _observed_vector(
    row: Mapping[str, Any], money_ordinals: Sequence[int]
) -> list[int] | None:
    values = row.get("values_exact")
    if type(values) is not list or any(
        type(ordinal) is not int or ordinal <= 0 or ordinal > len(values)
        for ordinal in money_ordinals
    ):
        return None
    cells = []
    for ordinal in money_ordinals:
        try:
            cell = _source_money(values[ordinal - 1])
        except (TypeError, ValueError):
            return None
        if type(cell.get("coefficient")) is not int:
            return None
        cells.append(cell["coefficient"])
    return cells if cells else None


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
        if type(money_ordinals) is not list or len(money_ordinals) != 2 or type(rows) is not list:
            continue
        for total in classification.get("total_rows", []):
            row_ordinal = total.get("row_ordinal") if type(total) is dict else None
            if type(row_ordinal) is not int or not (1 <= row_ordinal <= len(rows)):
                continue
            vector = _observed_vector(rows[row_ordinal - 1], money_ordinals)
            if vector is not None:
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
    return {
        _normalized(alias)
        for alias in compiled_specs["topology"]["parent"]["aliases"]
    }


def _is_parent_label(value: Any, *, compiled_specs: Mapping[str, Any]) -> bool:
    return bool(
        type(value) is str
        and _without_leading_ordinal(_normalized(value)) in _parent_aliases(compiled_specs)
    )


def _local_explicit_unit(
    table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any] | None:
    axis = _unit_axis(
        table, compiled_specs=compiled_specs, document_unit_context=None
    )
    if axis.get("complete") is not True or axis.get("canonical_unit") not in _UNIT_SURFACE:
        return None
    return {
        "canonical_unit": axis["canonical_unit"],
        "evidence": canonical_clone_v1(axis),
        "rule": "LOCAL_PRIMARY_STATEMENT_TABLE_EXPLICIT_ACCEPTED_UNIT",
    }


def _preceding_primary_page_unit(
    *,
    page_json_version_id: str,
    document_ordinal: int,
    pages: Mapping[str, dict[str, Any]],
    selected_page_axis: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    document_axis = [
        item
        for item in selected_page_axis
        if item.get("document_ordinal") == document_ordinal
    ]
    positions = [
        index
        for index, item in enumerate(document_axis)
        if item.get("page_json_version_id") == page_json_version_id
    ]
    if len(positions) != 1 or positions[0] == 0:
        return None
    current = document_axis[positions[0]]
    prior = document_axis[positions[0] - 1]
    if (
        prior.get("selected_page_ordinal") + 1 != current.get("selected_page_ordinal")
        or prior.get("physical_page") + 1 != current.get("physical_page")
    ):
        return None
    page = pages.get(prior.get("page_json_version_id"))
    if type(page) is not dict or page.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
        return None
    evidence = []
    for section_ordinal, section in enumerate(page.get("sections", []), start=1):
        if type(section) is not dict or section.get("content_kind") != "PRIMARY_STATEMENT":
            continue
        for table_ordinal, table in enumerate(section.get("tables", []), start=1):
            if type(table) is not dict:
                continue
            unit = _local_explicit_unit(table, compiled_specs=compiled_specs)
            if unit is not None:
                evidence.append(
                    {
                        **unit,
                        "locator": {
                            "page_json_version_id": prior["page_json_version_id"],
                            "physical_page": prior["physical_page"],
                            "section_id": f"s{section_ordinal}",
                            "table_id": f"t{table_ordinal}",
                        },
                    }
                )
    units = {item["canonical_unit"] for item in evidence}
    if len(units) != 1:
        return None
    return {
        "canonical_unit": next(iter(units)),
        "evidence": evidence,
        "rule": "IMMEDIATELY_PRECEDING_CONTIGUOUS_PRIMARY_STATEMENT_PAGE_EXPLICIT_UNIT",
    }


def _primary_interest_expense_roots(
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
                    unit = _preceding_primary_page_unit(
                        page_json_version_id=page_json_version_id,
                        document_ordinal=document_ordinal,
                        pages=pages,
                        selected_page_axis=selected_page_axis,
                        compiled_specs=compiled_specs,
                    )
                if unit is None:
                    continue
                rows = table.get("rows")
                for row_ordinal, row in enumerate(
                    rows if type(rows) is list else [], start=1
                ):
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
        _section, table = _source_table(
            pages[region["page_json_version_id"]],
            section_id=region["section_id"],
            table_id=region["table_id"],
        )
        tables.append((region, table))
    if any(table.get("unit_exact") is not None for _region, table in tables):
        return []
    target = _target_total_observation(
        pages=pages, regions=regions, compiled_specs=compiled_specs
    )
    if target is None:
        return []
    document_ordinals = {region.get("document_ordinal") for region in regions}
    if len(document_ordinals) != 1 or type(next(iter(document_ordinals))) is not int:
        return []
    document_ordinal = next(iter(document_ordinals))
    roots = _primary_interest_expense_roots(
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
    if len(units) != 1:
        return []
    canonical_unit = next(iter(units))
    for _region, table in tables:
        table["unit_exact"] = _UNIT_SURFACE[canonical_unit]
    material = {
        "canonical_unit": canonical_unit,
        "matched_primary_roots": matches,
        "rule": (
            "UNITLESS_INTEREST_EXPENSE_NOTE_UNIQUE_VISIBLE_TOTAL_EQUALS_ONE_"
            "CANONICAL_UNIT_PRIMARY_INTEREST_EXPENSE_ROOT_CONTIGUOUS_PERIOD_"
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
            "receipt_id": "gjiefav1:unit:" + canonical_json_sha256_v1(material),
        }
    ]


def _reclassified_regions(
    *,
    regions: Sequence[Mapping[str, Any]],
    pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    result = []
    changes = []
    for region in regions:
        adapted = canonical_clone_v1(region)
        page = pages.get(region.get("page_json_version_id"))
        if type(page) is not dict:
            raise _error("interest-expense selected page JSON is absent")
        section, table = _source_table(
            page, section_id=region["section_id"], table_id=region["table_id"]
        )
        classification = classify_gemini_json_multitable_hierarchical_table_v1(
            page, section, table, compiled_specs=compiled_specs
        )
        after = sorted(_classification_roles(classification))
        before = canonical_clone_v1(adapted.get("component_roles"))
        adapted["component_roles"] = after
        result.append(adapted)
        if not same_typed_json_v1(before, after):
            changes.append(
                {
                    "after_component_roles": after,
                    "before_component_roles": before,
                    "locator": {
                        key: adapted[key]
                        for key in (
                            "page_json_version_id",
                            "physical_page",
                            "section_id",
                            "table_id",
                        )
                    },
                }
            )
    return result, changes


def _validate_cross_source_selected_json(
    *,
    selected_document_axis: Sequence[Mapping[str, Any]],
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> None:
    by_sha = {item.get("source_sha256"): item for item in selected_document_axis}
    for repair in compiled_specs["interest_expense_source_repairs"]:
        corroboration = repair.get("corroboration")
        if repair["source_sha256"] not in by_sha or corroboration is None:
            continue
        document = by_sha.get(corroboration["source_sha256"])
        if (
            type(document) is not dict
            or document.get("source_logical_name")
            != corroboration["source_logical_name"]
        ):
            raise _error("interest-expense corroborating selected document is absent")
        pages = page_json_by_document.get(document["document_ordinal"])
        page = (
            pages.get(corroboration["page_json_version_id"])
            if type(pages) is dict
            else None
        )
        if type(page) is not dict:
            raise _error("interest-expense corroborating selected page is absent")
        _section, table = _source_table(
            page,
            section_id=corroboration["section_id"],
            table_id=corroboration["table_id"],
        )
        rows = table.get("rows")
        columns = table.get("columns")
        row_ordinal = corroboration["row_ordinal"]
        column_ordinal = corroboration["column_ordinal"]
        values = (
            rows[row_ordinal - 1].get("values_exact")
            if type(rows) is list
            and 1 <= row_ordinal <= len(rows)
            and type(rows[row_ordinal - 1]) is dict
            else None
        )
        if (
            type(columns) is not list
            or type(values) is not list
            or not (1 <= column_ordinal <= len(columns))
            or column_ordinal > len(values)
            or not same_typed_json_v1(
                values[column_ordinal - 1], corroboration["value_exact"]
            )
        ):
            raise _error("interest-expense corroborating selected value drifted")


def build_gemini_json_interest_expense_indexed_query_evidence_v1(
    *,
    base_indexed_query_evidence: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Re-seal query regions whose PDF repair reveals another declared role."""

    base = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        base_indexed_query_evidence, compiled_specs=compiled_specs
    )
    _validate_cross_source_selected_json(
        selected_document_axis=base["selected_document_axis"],
        page_json_by_document=page_json_by_document,
        compiled_specs=compiled_specs,
    )
    clusters = []
    for disposition in base["candidate_dispositions"]:
        cluster = canonical_clone_v1(disposition["cluster"])
        repairs = [
            repair
            for repair in compiled_specs["interest_expense_source_repairs"]
            if repair["source_sha256"] == disposition["source_sha256"]
        ]
        if cluster["status"] != READY:
            if repairs:
                raise _error("interest-expense repair source has no selected family region")
            clusters.append(cluster)
            continue
        if not repairs:
            clusters.append(cluster)
            continue
        pages = page_json_by_document.get(disposition["document_ordinal"])
        if type(pages) is not dict:
            raise _error("interest-expense selected document page JSON is absent")
        repaired_pages, repair_receipts = _document_repairs(
            regions=cluster["component_regions"],
            page_json_by_version=pages,
            compiled_specs=compiled_specs,
        )
        regions, role_changes = _reclassified_regions(
            regions=cluster["component_regions"],
            pages=repaired_pages,
            compiled_specs=compiled_specs,
        )
        material = {
            **{key: value for key, value in cluster.items() if key != "cluster_id"},
            "component_regions": regions,
        }
        if repair_receipts:
            receipt_material = {
                "repair_receipt_ids": [item["receipt_id"] for item in repair_receipts],
                "role_axis_changes": role_changes,
                "source_repair_spec_sha256": compiled_specs[
                    "interest_expense_source_repair_spec_sha256"
                ],
            }
            material["interest_expense_query_adapter_receipt"] = {
                **receipt_material,
                "receipt_id": "gjiefav1:query:"
                + canonical_json_sha256_v1(receipt_material),
            }
        clusters.append(
            {
                **material,
                "cluster_id": "gjmthfcv1:cluster:"
                + canonical_json_sha256_v1(material),
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


def _reseal_candidate(
    candidate: dict[str, Any],
    *,
    source_repair_receipts: Sequence[Mapping[str, Any]],
    unit_receipts: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    material = {
        "adapter_format_version": ADAPTER_FORMAT_VERSION,
        "shared_engine_claim_boundary": SHARED_CLAIM_BOUNDARY,
        "source_repair_receipts": canonical_clone_v1(list(source_repair_receipts)),
        "source_repair_spec_sha256": compiled_specs[
            "interest_expense_source_repair_spec_sha256"
        ],
        "unit_corroboration_receipts": canonical_clone_v1(list(unit_receipts)),
    }
    candidate["claim_boundary"] = CLAIM_BOUNDARY
    candidate["closure_receipt"]["interest_expense_adapter_receipt"] = {
        **material,
        "adapter_receipt_id": "gjiefav1:receipt:"
        + canonical_json_sha256_v1(material),
    }
    candidate_material = {
        key: value for key, value in candidate.items() if key != "candidate_id"
    }
    candidate["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        candidate_material
    )
    return candidate


def evaluate_gemini_json_interest_expense_family_cluster_v1(
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    selected_page_axis: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate Family 29 after exact source repair and unit corroboration."""

    if compiled_specs.get("topology", {}).get("family_id") != FAMILY_ID:
        raise _error("interest-expense adapter received another family")
    expected = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
    if type(query_receipt) is not dict or not same_typed_json_v1(query_receipt, expected):
        raise _error("interest-expense query receipt does not bind exact fragments")
    region_axis = expected["region_axis"]
    pages, source_repair_receipts = _document_repairs(
        regions=region_axis,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
    )
    unit_receipts = _bind_exact_primary_statement_unit(
        pages=pages,
        regions=region_axis,
        selected_page_axis=selected_page_axis,
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
        source_repair_receipts=source_repair_receipts,
        unit_receipts=unit_receipts,
        compiled_specs=compiled_specs,
    )


def build_gemini_json_interest_expense_trials_v1(
    *,
    indexed_query_evidence: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Evaluate every accepted cluster while preserving exhaustive dispositions."""

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
            candidate = evaluate_gemini_json_interest_expense_family_cluster_v1(
                regions=regions,
                page_json_by_version=page_json_by_document[document_ordinal],
                selected_page_axis=pages_by_document[document_ordinal],
                compiled_specs=compiled_specs,
                query_receipt=(
                    build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
                        regions
                    )
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
            raise _error("interest-expense query disposition is invalid")
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


def validate_gemini_json_interest_expense_candidate_replay_v1(
    value: Any,
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    selected_page_axis: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    expected = evaluate_gemini_json_interest_expense_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        selected_page_axis=selected_page_axis,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if type(value) is not dict or not same_typed_json_v1(value, expected):
        raise _error("interest-expense candidate replay drifted")
    return expected


def validate_gemini_json_interest_expense_replay_v1(
    *,
    base_indexed_query_evidence: Any,
    indexed_query_evidence: Any,
    trials: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    replayed = build_gemini_json_interest_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base_indexed_query_evidence,
        page_json_by_document=page_json_by_document,
        compiled_specs=compiled_specs,
    )
    if not same_typed_json_v1(indexed_query_evidence, replayed):
        raise _error("interest-expense indexed query evidence replay drifted")
    expected = build_gemini_json_interest_expense_trials_v1(
        indexed_query_evidence=replayed,
        page_json_by_document=page_json_by_document,
        compiled_specs=compiled_specs,
    )
    if type(trials) is not list or not same_typed_json_v1(trials, expected):
        raise _error("interest-expense sweep replay drifted")
    return expected
