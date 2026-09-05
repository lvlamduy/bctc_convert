"""Family-37 source adapter for credit-risk provision expense disclosures.

The shared multi-table hierarchical engine remains the accounting and schema
mapping authority for ordinary two-period disclosures.  This module adds only
source-observable structure that the shared query cannot represent directly:

* exact PDF-authenticated repairs applied to a private JSON clone;
* exact textual unit authority and closed-continuation unit propagation;
* conditional splitting of two distinct ``OTHER_PROVISION`` source rows before
  their declared additive equation is evaluated; and
* customer-provision movement tables whose period is on rows and whose
  provision roles are on columns.

No bank, filename, document ordinal, note number, page number, or value is a
selection feature.  Blank source cells are preserved unless an authenticated
PDF render visibly contains a dash.
"""

from __future__ import annotations

import re
from calendar import monthrange
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
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
    _classification_roles,
    _multitable_lane_axis,
    _source_money,
    _unit_axis,
    build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    classify_gemini_json_multitable_hierarchical_table_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
    validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    validate_gemini_json_multitable_hierarchical_sweep_query_bindings_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    audit_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FAMILY_ID = "CREDIT_RISK_PROVISION_EXPENSE"
ADAPTER_FORMAT_VERSION = (
    "GEMINI_JSON_CREDIT_RISK_PROVISION_EXPENSE_FAMILY_ADAPTER_V1"
)
SOURCE_REPAIR_FORMAT_VERSION = (
    "CREDIT_RISK_PROVISION_EXPENSE_AUTHENTICATED_SOURCE_REPAIR_SPEC_V1"
)
SOURCE_COVERAGE_FORMAT_VERSION = (
    "CREDIT_RISK_PROVISION_EXPENSE_SOURCE_ROLE_COVERAGE_V1"
)
SOURCE_ROW_COVERAGE_FORMAT_VERSION = (
    "CREDIT_RISK_PROVISION_EXPENSE_SOURCE_ROW_COVERAGE_V1"
)
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_CREDIT_RISK_PROVISION_EXPENSE_"
    "AUTHENTICATED_PDF_VISIBLE_REPAIR_EXACT_TEXTUAL_OR_CLOSED_STRUCTURAL_"
    "UNIT_AUTHORITY_STRUCTURAL_DUPLICATE_OTHER_ROLE_SPLIT_AND_TRANSPOSED_"
    "CUSTOMER_PROVISION_PRIVATE_CLONE_ONLY_NO_BLANK_ZERO_NO_BACKSOLVE_"
    "NO_VALUE_UNIT_OR_PERIOD_INFERENCE_NO_BANK_FILE_YEAR_PAGE_NOTE_VALUE_"
    "ROUTING_PROPOSAL_ONLY_"
    + SHARED_CLAIM_BOUNDARY
)

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_PAGE_VERSION = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_SECTION_ID = re.compile(r"s[1-9][0-9]*\Z")
_TABLE_ID = re.compile(r"t[1-9][0-9]*\Z")
_REPAIR_ID = re.compile(r"gjcrpefav1:repair:[0-9a-f]{64}\Z")
_UNIT_SURFACE = {"MILLION_VND": "Triệu đồng", "VND": "VND"}
_SPLIT_LABELS = (
    "Nguồn quan sát thành phần dự phòng khác A",
    "Nguồn quan sát thành phần dự phòng khác B",
)
_CUSTOMER_ADDITIONAL_COMPONENT_ALIASES = {
    _normalized(alias)
    for alias in (
        "Trích lập dự phòng cho vay giao dịch ký quỹ và ứng trước",
        "Trích lập dự phòng cho vay giao dịch ký quỹ và ứng trước cho khách hàng",
        "(Hoàn nhập)/Trích lập dự phòng cho vay giao dịch ký quỹ và ứng trước cho khách hàng",
        "Trích lập dự phòng cho vay hoạt động ký quỹ và cho vay hoạt động ứng trước tiền bán của khách hàng",
        "Trích lập dự phòng các khoản cho vay hoạt động ký quỹ và cho vay hoạt động ứng trước tiền bán của khách hàng",
    )
}


class GeminiJsonCreditRiskProvisionExpenseFamilyV1Error(ValueError):
    """Family-37 source evidence, candidate, or replay drifted."""


def _error(message: str) -> GeminiJsonCreditRiskProvisionExpenseFamilyV1Error:
    return GeminiJsonCreditRiskProvisionExpenseFamilyV1Error(message)


def _valid_locator(value: Any) -> bool:
    return bool(
        type(value) is dict
        and set(value)
        == {"page_json_version_id", "physical_page", "section_id", "table_id"}
        and _PAGE_VERSION.fullmatch(value.get("page_json_version_id", ""))
        and type(value.get("physical_page")) is int
        and value["physical_page"] > 0
        and _SECTION_ID.fullmatch(value.get("section_id", ""))
        and _TABLE_ID.fullmatch(value.get("table_id", ""))
    )


def _valid_source_cell(value: Any) -> bool:
    return value is None or type(value) is str


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
        raise _error("Family-37 authenticated source-repair spec is invalid")
    checked = []
    identities: set[tuple[Any, ...]] = set()
    ids: set[str] = set()
    common = {
        "locator",
        "pdf_page_render_sha256",
        "repair_id",
        "repair_kind",
        "source_sha256",
    }
    for raw in value["repairs"]:
        kind = raw.get("repair_kind") if type(raw) is dict else None
        if kind == "MONEY_CELL_PDF_VISIBLE_EXACT":
            fields = common | {
                "after_exact",
                "before_exact",
                "column_ordinal",
                "row_ordinal",
            }
        elif kind == "ROW_VALUES_PDF_VISIBLE_EXACT":
            fields = common | {
                "after_values_exact",
                "before_values_exact",
                "row_ordinal",
            }
        elif kind == "ROW_LABEL_PDF_VISIBLE_EXACT":
            fields = common | {
                "after_hierarchy_path_exact",
                "after_label_exact",
                "before_hierarchy_path_exact",
                "before_label_exact",
                "row_ordinal",
            }
        elif kind == "SECTION_AND_TABLE_TITLE_PDF_VISIBLE_EXACT":
            fields = common | {
                "after_title_exact",
                "before_section_title_exact",
                "before_table_title_exact",
            }
        else:
            raise _error("Family-37 source-repair kind is invalid")
        if (
            type(raw) is not dict
            or set(raw) != fields
            or not _valid_locator(raw.get("locator"))
            or _SHA256.fullmatch(raw.get("source_sha256", "")) is None
            or _SHA256.fullmatch(raw.get("pdf_page_render_sha256", "")) is None
            or _REPAIR_ID.fullmatch(raw.get("repair_id", "")) is None
        ):
            raise _error("Family-37 authenticated source repair is invalid")
        if kind == "MONEY_CELL_PDF_VISIBLE_EXACT":
            if (
                type(raw.get("row_ordinal")) is not int
                or raw["row_ordinal"] <= 0
                or type(raw.get("column_ordinal")) is not int
                or raw["column_ordinal"] <= 0
                or not _valid_source_cell(raw.get("before_exact"))
                or raw.get("after_exact") != "-"
            ):
                raise _error("Family-37 money-cell repair is invalid")
            axis = (raw["row_ordinal"], raw["column_ordinal"])
        elif kind == "ROW_VALUES_PDF_VISIBLE_EXACT":
            if (
                type(raw.get("row_ordinal")) is not int
                or raw["row_ordinal"] <= 0
                or type(raw.get("before_values_exact")) is not list
                or type(raw.get("after_values_exact")) is not list
                or len(raw["before_values_exact"]) != len(raw["after_values_exact"])
                or not raw["before_values_exact"]
                or not all(_valid_source_cell(item) for item in raw["before_values_exact"])
                or not all(_valid_source_cell(item) for item in raw["after_values_exact"])
                or raw["after_values_exact"].count("-")
                != raw["before_values_exact"].count("-") + 1
            ):
                raise _error("Family-37 row-vector repair is invalid")
            axis = (raw["row_ordinal"], "ROW_VALUES")
        elif kind == "ROW_LABEL_PDF_VISIBLE_EXACT":
            if (
                type(raw.get("row_ordinal")) is not int
                or raw["row_ordinal"] <= 0
                or type(raw.get("before_label_exact")) is not str
                or type(raw.get("after_label_exact")) is not str
                or not raw["after_label_exact"]
                or type(raw.get("before_hierarchy_path_exact")) is not list
                or type(raw.get("after_hierarchy_path_exact")) is not list
                or not raw["before_hierarchy_path_exact"]
                or len(raw["before_hierarchy_path_exact"])
                != len(raw["after_hierarchy_path_exact"])
                or not all(
                    item is None or type(item) is str
                    for item in raw["before_hierarchy_path_exact"]
                )
                or not all(
                    item is None or type(item) is str
                    for item in raw["after_hierarchy_path_exact"]
                )
            ):
                raise _error("Family-37 row-label repair is invalid")
            axis = (raw["row_ordinal"], "ROW_LABEL")
        else:
            if (
                type(raw.get("before_section_title_exact")) is not str
                or type(raw.get("before_table_title_exact")) is not str
                or type(raw.get("after_title_exact")) is not str
                or not raw["after_title_exact"]
            ):
                raise _error("Family-37 title repair is invalid")
            axis = ("SECTION_AND_TABLE_TITLE",)
        identity = (
            raw["source_sha256"],
            raw["locator"]["page_json_version_id"],
            raw["locator"]["section_id"],
            raw["locator"]["table_id"],
            *axis,
        )
        material = {key: canonical_clone_v1(item) for key, item in raw.items() if key != "repair_id"}
        if raw["repair_id"] != "gjcrpefav1:repair:" + canonical_json_sha256_v1(material):
            raise _error("Family-37 source-repair identity drifted")
        if identity in identities or raw["repair_id"] in ids:
            raise _error("Family-37 source-repair axis is duplicate")
        identities.add(identity)
        ids.add(raw["repair_id"])
        checked.append(canonical_clone_v1(raw))
    return checked


def compile_gemini_json_credit_risk_provision_expense_family_specs_v1(
    topology_spec: Any,
    evaluation_spec: Any,
    schema_binding_spec: Any,
    source_repair_spec: Any,
) -> dict[str, Any]:
    """Compile and narrow one immutable Family-37 declarative frontier."""

    try:
        compiled = compile_gemini_json_multitable_hierarchical_family_specs_v1(
            topology_spec, evaluation_spec, schema_binding_spec
        )
    except ValueError as exc:
        raise _error("Family-37 declarative specs are invalid") from exc
    expected_bindings = {
        "CUSTOMER_GENERAL": 1224,
        "CUSTOMER_PROVISION": 6031,
        "CUSTOMER_SPECIFIC": 1225,
        "INTERBANK_GENERAL": 1222,
        "INTERBANK_PROVISION": 6032,
        "INTERBANK_SPECIFIC": 1223,
        "OFF_BALANCE_COMMITMENT_PROVISION": 1227,
        "OTHER_PROVISION": 1228,
        "PURCHASED_DEBT_PROVISION": 6033,
        "VAMC_PROVISION": 1226,
    }
    evaluation = compiled.get("evaluation", {})
    if (
        compiled.get("topology", {}).get("family_id") != FAMILY_ID
        or evaluation.get("family_id") != FAMILY_ID
        or compiled.get("schema", {}).get("family_id") != FAMILY_ID
        or compiled.get("bindings") != expected_bindings
        or compiled.get("schema", {}).get("family_root_report_norm_id") != 1221
        or evaluation.get("context_total_mapping_roles")
        != ["CUSTOMER_GENERAL", "CUSTOMER_SPECIFIC"]
        or evaluation.get("minimum_declared_detail_role_count") != 1
        or evaluation.get("minimum_source_visible_root_component_count") != 1
        or evaluation.get("family_root_requirement") != "OPTIONAL"
        or compiled.get("derived_role_equations")
        != [
            {
                "component_roles": [
                    "OTHER_PROVISION_COMPONENT_A_SOURCE_ONLY",
                    "OTHER_PROVISION_COMPONENT_B_SOURCE_ONLY",
                ],
                "result_role": "OTHER_PROVISION",
            }
        ]
        or not {
            "OTHER_PROVISION_COMPONENT_A_SOURCE_ONLY",
            "OTHER_PROVISION_COMPONENT_B_SOURCE_ONLY",
        }
        <= set(compiled.get("validation_only_roles", []))
        or {
            item["canonical_unit"]
            for item in compiled.get("unit_bindings", [])
            if item.get("accepted") is True
        }
        != {"MILLION_VND", "VND"}
    ):
        raise _error("Family-37 compiled frontier is invalid")
    compiled["credit_risk_provision_expense_source_repairs"] = _validate_source_repairs(
        source_repair_spec
    )
    compiled["credit_risk_provision_expense_source_repair_spec_sha256"] = (
        canonical_json_sha256_v1(source_repair_spec)
    )
    compiled["credit_risk_provision_expense_adapter_format_version"] = (
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
        raise _error("Family-37 source locator does not resolve one table") from exc
    if type(section) is not dict or type(table) is not dict:
        raise _error("Family-37 source table is invalid")
    return section, table


def _repair_receipt(
    repair: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    material = {
        "repair": canonical_clone_v1(repair),
        "rule": (
            "EXACT_IMMUTABLE_SOURCE_SELECTED_PAGE_PDF_RENDER_TABLE_BEFORE_"
            "IMAGE_TO_VISIBLE_SOURCE_TRANSCRIPTION_PRIVATE_CLONE_ONLY"
        ),
        "source_repair_spec_sha256": compiled_specs[
            "credit_risk_provision_expense_source_repair_spec_sha256"
        ],
        "status": "AUTHENTICATED_SOURCE_REPAIR_APPLIED_TO_PRIVATE_CLONE",
    }
    return {
        **material,
        "receipt_id": "gjcrpefav1:repair-receipt:"
        + canonical_json_sha256_v1(material),
    }


def _apply_document_repairs(
    *,
    pages: Mapping[str, dict[str, Any]],
    source_sha256: str,
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    projected = {key: canonical_clone_v1(value) for key, value in pages.items()}
    receipts = []
    for repair in compiled_specs["credit_risk_provision_expense_source_repairs"]:
        if repair["source_sha256"] != source_sha256:
            continue
        locator = repair["locator"]
        page = projected.get(locator["page_json_version_id"])
        if type(page) is not dict:
            raise _error("Family-37 repair page is outside the selected document")
        section, table = _source_table(
            page, section_id=locator["section_id"], table_id=locator["table_id"]
        )
        rows = table.get("rows")
        columns = table.get("columns")
        if type(rows) is not list or type(columns) is not list:
            raise _error("Family-37 repair table axes are invalid")
        kind = repair["repair_kind"]
        if kind == "SECTION_AND_TABLE_TITLE_PDF_VISIBLE_EXACT":
            if (
                section.get("title_exact") != repair["before_section_title_exact"]
                or table.get("title_exact") != repair["before_table_title_exact"]
            ):
                raise _error("Family-37 title-repair before image drifted")
            section["title_exact"] = repair["after_title_exact"]
            table["title_exact"] = repair["after_title_exact"]
        elif kind == "ROW_VALUES_PDF_VISIBLE_EXACT":
            row_ordinal = repair["row_ordinal"]
            if not (1 <= row_ordinal <= len(rows)):
                raise _error("Family-37 row repair is outside its table")
            row = rows[row_ordinal - 1]
            if (
                type(row) is not dict
                or not same_typed_json_v1(
                    row.get("values_exact"), repair["before_values_exact"]
                )
                or len(repair["after_values_exact"]) != len(columns)
            ):
                raise _error("Family-37 row-repair before image drifted")
            row["values_exact"] = canonical_clone_v1(repair["after_values_exact"])
        elif kind == "ROW_LABEL_PDF_VISIBLE_EXACT":
            row_ordinal = repair["row_ordinal"]
            if not (1 <= row_ordinal <= len(rows)):
                raise _error("Family-37 row-label repair is outside its table")
            row = rows[row_ordinal - 1]
            if (
                type(row) is not dict
                or not same_typed_json_v1(
                    row.get("label_exact"), repair["before_label_exact"]
                )
                or not same_typed_json_v1(
                    row.get("hierarchy_path_exact"),
                    repair["before_hierarchy_path_exact"],
                )
            ):
                raise _error("Family-37 row-label-repair before image drifted")
            row["label_exact"] = repair["after_label_exact"]
            row["hierarchy_path_exact"] = canonical_clone_v1(
                repair["after_hierarchy_path_exact"]
            )
        else:
            row_ordinal = repair["row_ordinal"]
            column_ordinal = repair["column_ordinal"]
            if not (
                1 <= row_ordinal <= len(rows) and 1 <= column_ordinal <= len(columns)
            ):
                raise _error("Family-37 cell repair is outside its table")
            row = rows[row_ordinal - 1]
            values = row.get("values_exact") if type(row) is dict else None
            if (
                type(values) is not list
                or len(values) != len(columns)
                or not same_typed_json_v1(
                    values[column_ordinal - 1], repair["before_exact"]
                )
            ):
                raise _error("Family-37 cell-repair before image drifted")
            values[column_ordinal - 1] = repair["after_exact"]
        receipts.append(_repair_receipt(repair, compiled_specs=compiled_specs))
    return projected, receipts


def _project_shared_duration_header_prefixes(
    pages: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Remove one contradictory shared outer duration prefix on a clone."""

    receipts = []
    for page_json_version_id, page in pages.items():
        for section_ordinal, section in enumerate(page.get("sections", []), start=1):
            if type(section) is not dict:
                continue
            for table_ordinal, table in enumerate(
                section.get("tables", []), start=1
            ):
                if type(table) is not dict:
                    continue
                owner_surface = _normalized(
                    " ".join(
                        [
                            str(section.get("title_exact") or ""),
                            str(table.get("title_exact") or ""),
                        ]
                    )
                )
                if "chi phi du phong rui ro tin dung" not in owner_surface:
                    continue
                money_ordinals = _money_column_ordinals(table)
                columns = table.get("columns")
                if type(columns) is not list or len(money_ordinals) != 2:
                    continue
                money_columns = [columns[ordinal - 1] for ordinal in money_ordinals]
                paths = [column.get("header_path_exact") for column in money_columns]
                if (
                    any(type(path) is not list or len(path) != 2 for path in paths)
                    or _normalized(paths[0][0])
                    != "luy ke tu dau nam den cuoi ky nay"
                    or _normalized(paths[1][0])
                    != "luy ke tu dau nam den cuoi ky nay"
                    or [_normalized(path[1]) for path in paths]
                    != ["nam nay", "nam truoc"]
                ):
                    continue
                before = canonical_clone_v1(paths)
                for column, path in zip(money_columns, paths, strict=True):
                    column["header_path_exact"] = [path[1]]
                material = {
                    "after_header_paths_exact": [
                        canonical_clone_v1(column["header_path_exact"])
                        for column in money_columns
                    ],
                    "before_header_paths_exact": before,
                    "locator": {
                        "page_json_version_id": page_json_version_id,
                        "section_id": f"s{section_ordinal}",
                        "table_id": f"t{table_ordinal}",
                    },
                    "money_column_ordinals": money_ordinals,
                    "rule": (
                        "IDENTICAL_OUTER_LUY_KE_DURATION_PREFIX_IS_NOT_A_LANE_"
                        "ROLE_WHEN_EXACT_LEAVES_ARE_NAM_NAY_AND_NAM_TRUOC"
                    ),
                }
                receipts.append(
                    {
                        **material,
                        "receipt_id": "gjcrpefav1:header-projection:"
                        + canonical_json_sha256_v1(material),
                    }
                )
    return receipts


def _project_customer_adjacent_continuations(
    pages: dict[str, dict[str, Any]],
    *,
    selected_page_axis: Sequence[Mapping[str, Any]],
    document_ordinal: int,
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Carry exact customer structure across an authenticated continuation."""

    axis = sorted(
        (
            item
            for item in selected_page_axis
            if item.get("document_ordinal") == document_ordinal
            and item.get("page_json_version_id") in pages
        ),
        key=lambda item: item["selected_page_ordinal"],
    )
    receipts = []
    for previous_axis, current_axis in zip(axis, axis[1:], strict=False):
        if current_axis["physical_page"] != previous_axis["physical_page"] + 1:
            continue
        previous_page = pages[previous_axis["page_json_version_id"]]
        current_page = pages[current_axis["page_json_version_id"]]
        pairs = []
        for previous_section_ordinal, previous_section in enumerate(
            previous_page.get("sections", []), start=1
        ):
            if type(previous_section) is not dict:
                continue
            for previous_table_ordinal, previous_table in enumerate(
                previous_section.get("tables", []), start=1
            ):
                if (
                    type(previous_table) is not dict
                    or previous_table.get("continuation")
                    != "CONTINUES_ON_NEXT_PAGE"
                    or (
                        _movement_owner_kind(
                            " ".join(
                                (
                                    str(previous_section.get("title_exact") or ""),
                                    str(previous_table.get("title_exact") or ""),
                                )
                            )
                        )
                        != "CUSTOMER"
                        and not _is_structural_customer_movement(
                            previous_section, previous_table
                        )
                    )
                ):
                    continue
                previous_columns = previous_table.get("columns")
                for current_section_ordinal, current_section in enumerate(
                    current_page.get("sections", []), start=1
                ):
                    if type(current_section) is not dict:
                        continue
                    for current_table_ordinal, current_table in enumerate(
                        current_section.get("tables", []), start=1
                    ):
                        current_columns = (
                            current_table.get("columns")
                            if type(current_table) is dict
                            else None
                        )
                        if (
                            type(current_table) is not dict
                            or current_table.get("continuation")
                            != "CONTINUES_FROM_PREVIOUS_PAGE"
                            or type(previous_columns) is not list
                            or type(current_columns) is not list
                            or len(previous_columns) != len(current_columns)
                            or not previous_columns
                            or any(
                                type(column) is not dict
                                or column.get("value_kind") != "MONEY"
                                or column.get("header_path_exact") != [None]
                                for column in current_columns
                            )
                            or [
                                column.get("value_kind") for column in current_columns
                            ]
                            != [
                                column.get("value_kind")
                                for column in previous_columns
                            ]
                        ):
                            continue
                        pairs.append(
                            (
                                previous_section_ordinal,
                                previous_table_ordinal,
                                previous_section,
                                previous_table,
                                current_section_ordinal,
                                current_table_ordinal,
                                current_section,
                                current_table,
                            )
                        )
        if len(pairs) != 1:
            continue
        (
            previous_section_ordinal,
            previous_table_ordinal,
            previous_section,
            previous_table,
            current_section_ordinal,
            current_table_ordinal,
            current_section,
            current_table,
        ) = pairs[0]
        previous_unit_axis = _unit_axis(
            previous_table,
            compiled_specs=compiled_specs,
            document_unit_context=None,
        )
        current_unit_axis = _unit_axis(
            current_table,
            compiled_specs=compiled_specs,
            document_unit_context=None,
        )
        if (
            previous_unit_axis.get("complete") is True
            and current_unit_axis.get("complete") is True
            and previous_unit_axis.get("canonical_unit")
            != current_unit_axis.get("canonical_unit")
        ):
            continue
        before_columns = canonical_clone_v1(current_table["columns"])
        current_table["columns"] = canonical_clone_v1(previous_table["columns"])
        before_unit_exact = current_table.get("unit_exact")
        if (
            previous_unit_axis.get("complete") is True
            and current_unit_axis.get("complete") is not True
            and before_unit_exact is None
        ):
            current_table["unit_exact"] = previous_table.get("unit_exact")
        before_section_title = current_section.get("title_exact")
        if before_section_title is None:
            current_section["title_exact"] = previous_section.get("title_exact")
        previous_groups = [
            row
            for row in previous_table.get("rows", [])
            if type(row) is dict and row.get("row_kind") == "GROUP"
        ]
        carried_path = (
            canonical_clone_v1(previous_groups[-1].get("hierarchy_path_exact"))
            if previous_groups
            else None
        )
        before_hierarchy_paths = []
        after_hierarchy_paths = []
        if type(carried_path) is list and carried_path:
            for row in current_table.get("rows", []):
                if type(row) is not dict or row.get("row_kind") == "GROUP":
                    break
                path = row.get("hierarchy_path_exact")
                if type(path) is not list:
                    break
                before_hierarchy_paths.append(canonical_clone_v1(path))
                if path[: len(carried_path)] != carried_path:
                    row["hierarchy_path_exact"] = [
                        *canonical_clone_v1(carried_path),
                        *canonical_clone_v1(path),
                    ]
                after_hierarchy_paths.append(
                    canonical_clone_v1(row["hierarchy_path_exact"])
                )
        material = {
            "after_columns_exact": canonical_clone_v1(current_table["columns"]),
            "after_initial_hierarchy_paths_exact": after_hierarchy_paths,
            "after_section_title_exact": current_section.get("title_exact"),
            "after_unit_exact": current_table.get("unit_exact"),
            "before_columns_exact": before_columns,
            "before_initial_hierarchy_paths_exact": before_hierarchy_paths,
            "before_section_title_exact": before_section_title,
            "before_unit_exact": before_unit_exact,
            "carried_group_hierarchy_path_exact": carried_path,
            "current_locator": {
                "page_json_version_id": current_axis["page_json_version_id"],
                "section_id": f"s{current_section_ordinal}",
                "table_id": f"t{current_table_ordinal}",
            },
            "previous_locator": {
                "page_json_version_id": previous_axis["page_json_version_id"],
                "section_id": f"s{previous_section_ordinal}",
                "table_id": f"t{previous_table_ordinal}",
            },
            "rule": (
                "EXPLICIT_ADJACENT_ON_NEXT_FROM_PREVIOUS_CUSTOMER_TABLE_"
                "CARRIES_IDENTICAL_ROLE_HEADERS_OWNER_AND_EXPLICIT_UNIT"
            ),
        }
        receipts.append(
            {
                **material,
                "receipt_id": "gjcrpefav1:continuation-projection:"
                + canonical_json_sha256_v1(material),
            }
        )
    return receipts


def _money_column_ordinals(table: Mapping[str, Any]) -> list[int]:
    columns = table.get("columns")
    return [
        ordinal
        for ordinal, column in enumerate(
            columns if type(columns) is list else [], start=1
        )
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]


def _observed_cells(
    row: Mapping[str, Any], money_ordinals: Sequence[int]
) -> list[dict[str, Any]] | None:
    values = row.get("values_exact")
    if type(values) is not list or any(
        type(ordinal) is not int or not (1 <= ordinal <= len(values))
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
        cells.append(cell)
    return cells if cells else None


def _parent_aliases(compiled_specs: Mapping[str, Any]) -> set[str]:
    return {
        _normalized(alias)
        for alias in compiled_specs["topology"]["parent"]["aliases"]
    }


def _is_parent_label(value: Any, *, compiled_specs: Mapping[str, Any]) -> bool:
    return bool(
        type(value) is str
        and _without_leading_ordinal(_normalized(value))
        in _parent_aliases(compiled_specs)
    )


def _local_explicit_unit(
    table: Mapping[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
    document_unit_context: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    axis = _unit_axis(
        table,
        compiled_specs=compiled_specs,
        document_unit_context=document_unit_context,
    )
    if axis.get("complete") is not True or axis.get("canonical_unit") not in _UNIT_SURFACE:
        return None
    return {
        "canonical_unit": axis["canonical_unit"],
        "evidence": canonical_clone_v1(axis),
        "rule": "LOCAL_PRIMARY_STATEMENT_TABLE_EXPLICIT_ACCEPTED_UNIT",
    }


def _primary_root_observations(
    *,
    pages: Mapping[str, dict[str, Any]],
    selected_page_axis: Sequence[Mapping[str, Any]],
    document_ordinal: int,
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    document_unit_context = _family_document_unit_context(
        pages=pages, compiled_specs=compiled_specs
    )
    axis_by_version = {
        item["page_json_version_id"]: item
        for item in selected_page_axis
        if item.get("document_ordinal") == document_ordinal
    }
    result = []
    for version_id, page in pages.items():
        page_axis = axis_by_version.get(version_id)
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
                lane_axis = _multitable_lane_axis(
                    section, table, compiled_specs=compiled_specs
                )
                money_ordinals = lane_axis.get("money_column_ordinals")
                unit = _local_explicit_unit(
                    table,
                    compiled_specs=compiled_specs,
                    document_unit_context=document_unit_context,
                )
                if (
                    lane_axis.get("complete") is not True
                    or type(money_ordinals) is not list
                    or len(money_ordinals) != 2
                    or unit is None
                ):
                    continue
                columns = table.get("columns")
                if type(columns) is not list:
                    continue
                common_period_surfaces = [
                    item
                    for item in (
                        table.get("title_exact"),
                        section.get("title_exact"),
                    )
                    if type(item) is str and item.strip()
                ]
                period_scope_by_lane = {}
                for semantic_role, column_ordinal in zip(
                    ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"),
                    money_ordinals,
                    strict=True,
                ):
                    column = columns[column_ordinal - 1]
                    header_path = (
                        column.get("header_path_exact")
                        if type(column) is dict
                        else None
                    )
                    local_surfaces = [
                        item
                        for item in (
                            header_path if type(header_path) is list else []
                        )
                        if type(item) is str and item.strip()
                    ]
                    period_scope_by_lane[semantic_role] = (
                        _family37_period_scope_v1(
                            [*local_surfaces, *common_period_surfaces],
                            semantic_role=semantic_role,
                        )
                    )
                rows = table.get("rows")
                for row_ordinal, row in enumerate(
                    rows if type(rows) is list else [], start=1
                ):
                    if type(row) is not dict or not _is_parent_label(
                        row.get("label_exact"), compiled_specs=compiled_specs
                    ):
                        continue
                    cells = _observed_cells(row, money_ordinals)
                    if cells is None:
                        continue
                    result.append(
                        {
                            "canonical_unit": unit["canonical_unit"],
                            "cells": cells,
                            "lane_axis": canonical_clone_v1(lane_axis),
                            "locator": {
                                "page_json_version_id": version_id,
                                "physical_page": page_axis["physical_page"],
                                "section_id": f"s{section_ordinal}",
                                "table_id": f"t{table_ordinal}",
                            },
                            "money_column_ordinals": canonical_clone_v1(money_ordinals),
                            "period_scope_by_lane": period_scope_by_lane,
                            "row": canonical_clone_v1(row),
                            "row_ordinal": row_ordinal,
                            "unit_receipt": canonical_clone_v1(unit),
                        }
                    )
    result.sort(
        key=lambda item: (
            item["locator"]["physical_page"],
            int(item["locator"]["section_id"][1:]),
            int(item["locator"]["table_id"][1:]),
            item["row_ordinal"],
        )
    )
    return result


def _primary_roots_compatible_with_observations(
    roots: Sequence[Mapping[str, Any]],
    observations: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    units = {
        item.get("canonical_unit")
        for item in observations
        if type(item.get("canonical_unit")) is str
    }
    if len(units) != 1:
        return [canonical_clone_v1(item) for item in roots]
    canonical_unit = next(iter(units))
    return [
        canonical_clone_v1(item)
        for item in roots
        if item.get("canonical_unit") == canonical_unit
    ]


def _target_total_observation(
    *,
    pages: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    observations = []
    for region in regions:
        page = pages.get(region["page_json_version_id"])
        if type(page) is not dict:
            return None
        section, table = _source_table(
            page, section_id=region["section_id"], table_id=region["table_id"]
        )
        classification = classify_gemini_json_multitable_hierarchical_table_v1(
            page, section, table, compiled_specs=compiled_specs
        )
        # ``classification.money_column_ordinals`` is the physical source
        # order.  Root values must use the same semantic current/comparative
        # lane order as every child mapping; otherwise a fully reversed table
        # silently swaps only the printed root.
        lane_axis = _multitable_lane_axis(
            section, table, compiled_specs=compiled_specs
        )
        money_ordinals = lane_axis.get("money_column_ordinals")
        rows = table.get("rows")
        if (
            lane_axis.get("complete") is not True
            or type(money_ordinals) is not list
            or len(money_ordinals) != 2
            or type(rows) is not list
        ):
            continue
        for total in classification.get("total_rows", []):
            row_ordinal = total.get("row_ordinal") if type(total) is dict else None
            if type(row_ordinal) is not int or not (1 <= row_ordinal <= len(rows)):
                continue
            cells = _observed_cells(rows[row_ordinal - 1], money_ordinals)
            if cells is not None:
                observations.append(
                    {
                        "cells": cells,
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
                    }
                )
    return observations[0] if len(observations) == 1 else None


def _region(
    *,
    document: Mapping[str, Any],
    page_axis: Mapping[str, Any],
    section_ordinal: int,
    table_ordinal: int,
    component_roles: Sequence[str],
) -> dict[str, Any]:
    return {
        "component_roles": sorted(component_roles),
        "document_id": document["document_id"],
        "document_ordinal": document["document_ordinal"],
        "fragment_ordinal": 1,
        "page_json_version_id": page_axis["page_json_version_id"],
        "physical_page": page_axis["physical_page"],
        "section_id": f"s{section_ordinal}",
        "selected_page_ordinal": page_axis["selected_page_ordinal"],
        "source_logical_name": document["source_logical_name"],
        "source_sha256": document["source_sha256"],
        "table_id": f"t{table_ordinal}",
    }


def _family37_selected_document_pages_v1(
    *,
    document: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    source_pages: Mapping[str, dict[str, Any]],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Join selected metadata to exact page payloads in source order.

    The page-version identifier is an upstream store identity, not a raw JSON
    hash.  This family layer therefore binds both the authenticated identifier
    and the exact payload hash, and refuses missing or surplus payloads.
    """

    axis = sorted(
        (
            canonical_clone_v1(item)
            for item in selected_page_axis
            if item.get("document_ordinal") == document.get("document_ordinal")
        ),
        key=lambda item: (
            item["selected_page_ordinal"],
            item["physical_page"],
            item["page_json_version_id"],
        ),
    )
    expected_versions = [item["page_json_version_id"] for item in axis]
    if (
        not axis
        or len(expected_versions) != len(set(expected_versions))
        or set(expected_versions) != set(source_pages)
    ):
        raise _error("Family-37 selected page payload frontier drifted")
    result = []
    for expected_ordinal, item in enumerate(axis, start=1):
        if item.get("selected_page_ordinal") != expected_ordinal:
            raise _error("Family-37 selected page source order drifted")
        page = source_pages.get(item["page_json_version_id"])
        if type(page) is not dict:
            raise _error("Family-37 selected page JSON is invalid")
        result.append((item, page))
    return result


def _family37_page_identity_axis_v1(
    *,
    ordered_pages: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]],
    repaired_pages: Mapping[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    result = []
    for page_axis, page in ordered_pages:
        version_id = page_axis["page_json_version_id"]
        repaired = repaired_pages.get(version_id)
        if type(repaired) is not dict:
            raise _error("Family-37 repaired page frontier drifted")
        result.append(
            {
                "input_page_json_sha256": canonical_json_sha256_v1(page),
                "page_json_version_id": version_id,
                "physical_page": page_axis["physical_page"],
                "repaired_page_json_sha256": canonical_json_sha256_v1(repaired),
                "selected_page_ordinal": page_axis["selected_page_ordinal"],
            }
        )
    return result


def _family37_recomputed_base_cluster_v1(
    *,
    document: Mapping[str, Any],
    ordered_pages: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    identity_fields = (
        "document_id",
        "document_ordinal",
        "source_logical_name",
        "source_sha256",
    )
    if any(
        page_axis.get(field) != document.get(field)
        for page_axis, _page in ordered_pages
        for field in identity_fields
    ):
        raise _error("Family-37 selected page document identity drifted")
    records = [
        {**canonical_clone_v1(page_axis), "page_json": canonical_clone_v1(page)}
        for page_axis, page in ordered_pages
    ]
    return coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records,
        compiled_specs=compiled_specs,
    )


def _money_bearing_row_ordinals(table: Mapping[str, Any]) -> set[int]:
    money_ordinals = _money_column_ordinals(table)
    result = set()
    rows = table.get("rows")
    for row_ordinal, row in enumerate(rows if type(rows) is list else [], start=1):
        values = row.get("values_exact") if type(row) is dict else None
        if type(values) is list and any(
            ordinal <= len(values) and values[ordinal - 1] is not None
            for ordinal in money_ordinals
        ):
            result.add(row_ordinal)
    return result


def _normal_expense_regions(
    *,
    document: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    page_axis = {
        item["page_json_version_id"]: item
        for item in selected_page_axis
        if item.get("document_ordinal") == document["document_ordinal"]
    }
    result = []
    for version_id, page in pages.items():
        axis = page_axis.get(version_id)
        if axis is None:
            continue
        for section_ordinal, section in enumerate(page.get("sections", []), start=1):
            if type(section) is not dict or section.get("content_kind") != "FINANCIAL_NOTE":
                continue
            for table_ordinal, table in enumerate(section.get("tables", []), start=1):
                if type(table) is not dict:
                    continue
                owner_surface = _normalized(
                    " ".join(
                        [
                            str(section.get("title_exact") or ""),
                            str(table.get("title_exact") or ""),
                        ]
                    )
                )
                if "du phong rui ro" not in owner_surface:
                    continue
                lane_axis = _multitable_lane_axis(
                    section, table, compiled_specs=compiled_specs
                )
                if (
                    lane_axis.get("complete") is not True
                    or len(lane_axis.get("money_column_ordinals", [])) != 2
                ):
                    continue
                classification = classify_gemini_json_multitable_hierarchical_table_v1(
                    page, section, table, compiled_specs=compiled_specs
                )
                hits = classification.get("role_hits", [])
                hit_rows = {
                    hit.get("row_ordinal")
                    for hit in hits
                    if type(hit) is dict
                    and hit.get("role") in compiled_specs["child_by_role"]
                }
                money_rows = _money_bearing_row_ordinals(table)
                total_rows = {
                    item.get("row_ordinal")
                    for item in classification.get("total_rows", [])
                    if type(item) is dict
                }
                detail_rows = money_rows - total_rows
                rows = table.get("rows")
                action_rows = {
                    row_ordinal
                    for row_ordinal, row in enumerate(
                        rows if type(rows) is list else [], start=1
                    )
                    if type(row) is dict
                    and "du phong" in _normalized(row.get("label_exact") or "")
                    and any(
                        marker in _normalized(row.get("label_exact") or "")
                        for marker in ("trich lap", "hoan nhap", "chi phi")
                    )
                }
                semantic_owner_visible = bool(
                    classification.get("owner_visible") is True
                    or "du phong rui ro tin dung" in owner_surface
                )
                if (
                    not semantic_owner_visible
                    or classification.get("family_presence_anchor_visible") is not True
                    or not detail_rows
                    or not detail_rows <= hit_rows
                    or not action_rows.intersection(detail_rows)
                    or len(total_rows.intersection(money_rows)) != 1
                    or max(money_rows) not in total_rows
                ):
                    continue
                result.append(
                    _region(
                        document=document,
                        page_axis=axis,
                        section_ordinal=section_ordinal,
                        table_ordinal=table_ordinal,
                        component_roles=_classification_roles(classification),
                    )
                )
    return result


def _family37_normal_fragment_inventory_v1(
    *,
    document: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Inventory positive normal owners before strict candidate admission."""

    axis_by_version = {
        item["page_json_version_id"]: item
        for item in selected_page_axis
        if item.get("document_ordinal") == document["document_ordinal"]
    }
    document_unit_context = _family_document_unit_context(
        pages=pages, compiled_specs=compiled_specs
    )
    result = []
    for version_id, axis in sorted(
        axis_by_version.items(),
        key=lambda item: (
            item[1]["selected_page_ordinal"],
            item[1]["physical_page"],
            item[0],
        ),
    ):
        page = pages.get(version_id)
        if type(page) is not dict:
            raise _error("Family-37 normal owner page is absent")
        for section_ordinal, section in enumerate(page.get("sections", []), start=1):
            if (
                type(section) is not dict
                or section.get("content_kind") != "FINANCIAL_NOTE"
            ):
                continue
            for table_ordinal, table in enumerate(
                section.get("tables", []), start=1
            ):
                if type(table) is not dict:
                    continue
                classification = (
                    classify_gemini_json_multitable_hierarchical_table_v1(
                        page, section, table, compiled_specs=compiled_specs
                    )
                )
                roles = sorted(
                    {
                        hit["role"]
                        for hit in classification.get("role_hits", [])
                        if type(hit) is dict
                        and hit.get("role") in compiled_specs["child_by_role"]
                    }
                )
                hit_rows = {
                    hit["row_ordinal"]
                    for hit in classification.get("role_hits", [])
                    if type(hit) is dict
                    and hit.get("role") in compiled_specs["child_by_role"]
                    and type(hit.get("row_ordinal")) is int
                }
                rows = table.get("rows")
                if type(rows) is not list:
                    continue
                money_rows = _money_bearing_row_ordinals(table)
                total_rows = {
                    item["row_ordinal"]
                    for item in classification.get("total_rows", [])
                    if type(item) is dict
                    and type(item.get("row_ordinal")) is int
                    and item["row_ordinal"] in money_rows
                }
                detail_rows = money_rows - total_rows
                action_rows = {
                    row_ordinal
                    for row_ordinal, row in enumerate(rows, start=1)
                    if type(row) is dict
                    and _transposed_action_kind(row.get("label_exact")) is not None
                }
                owner_surface_exact = " ".join(
                    item
                    for item in (
                        section.get("title_exact"),
                        table.get("title_exact"),
                    )
                    if type(item) is str
                )
                owner_surface = _normalized(owner_surface_exact)
                semantic_owner = bool(
                    classification.get("owner_visible") is True
                    or "du phong rui ro tin dung" in owner_surface
                )
                positive_owner = bool(
                    semantic_owner
                    and classification.get("family_presence_anchor_visible") is True
                    and (roles or action_rows.intersection(money_rows))
                )
                marker = table.get("continuation")
                provisional_receiver = bool(
                    marker == "CONTINUES_FROM_PREVIOUS_PAGE" and money_rows
                )
                if not positive_owner and not provisional_receiver:
                    continue
                lane_axis = _multitable_lane_axis(
                    section, table, compiled_specs=compiled_specs
                )
                unit_axis = _unit_axis(
                    table,
                    compiled_specs=compiled_specs,
                    document_unit_context=document_unit_context,
                )
                region = _region(
                    document=document,
                    page_axis=axis,
                    section_ordinal=section_ordinal,
                    table_ordinal=table_ordinal,
                    component_roles=roles,
                )
                result.append(
                    {
                        "action_row_ordinals": sorted(action_rows),
                        "component_roles": roles,
                        "continuation": marker,
                        "detail_row_ordinals": sorted(detail_rows),
                        "detail_rows_are_declared": bool(
                            detail_rows
                            and detail_rows <= hit_rows
                            and action_rows.intersection(detail_rows)
                        ),
                        "lane_axis": canonical_clone_v1(lane_axis),
                        "money_row_ordinals": sorted(money_rows),
                        "owner_surface_exact": owner_surface_exact,
                        "positive_owner": positive_owner,
                        "semantic_owner": semantic_owner,
                        "region": region,
                        "total_row_ordinals": sorted(total_rows),
                        "unit": (
                            unit_axis.get("canonical_unit")
                            if unit_axis.get("complete") is True
                            else None
                        ),
                    }
                )
    result.sort(
        key=lambda item: (
            item["region"]["selected_page_ordinal"],
            item["region"]["physical_page"],
            int(item["region"]["section_id"][1:]),
            int(item["region"]["table_id"][1:]),
        )
    )
    return result


def _family37_normal_candidate_groups_v1(
    records: Sequence[Mapping[str, Any]],
) -> tuple[list[list[dict[str, Any]]], list[dict[str, Any]]]:
    """Close standalone and exact adjacent NEXT/FROM normal populations."""

    groups: list[list[dict[str, Any]]] = []
    rejected: list[dict[str, Any]] = []
    consumed: set[int] = set()

    def complete_lanes(record: Mapping[str, Any]) -> bool:
        axis = record.get("lane_axis")
        return bool(
            type(axis) is dict
            and axis.get("complete") is True
            and len(axis.get("money_column_ordinals", [])) == 2
        )

    def complete_unit(record: Mapping[str, Any]) -> bool:
        return record.get("unit") in _UNIT_SURFACE

    def strict_standalone(record: Mapping[str, Any]) -> bool:
        totals = record.get("total_row_ordinals", [])
        money = record.get("money_row_ordinals", [])
        return bool(
            record.get("positive_owner") is True
            and complete_lanes(record)
            and complete_unit(record)
            and record.get("detail_rows_are_declared") is True
            and len(totals) == 1
            and money
            and max(money) == totals[0]
        )

    for index, record in enumerate(records):
        marker = record.get("continuation")
        if marker == "NONE" and strict_standalone(record):
            groups.append([canonical_clone_v1(record["region"])])
            consumed.add(index)

    for index, sender in enumerate(records):
        if index in consumed or sender.get("continuation") != "CONTINUES_ON_NEXT_PAGE":
            continue
        sender_region = sender["region"]
        receivers = [
            (receiver_index, receiver)
            for receiver_index, receiver in enumerate(records)
            if receiver_index not in consumed
            and receiver.get("continuation") == "CONTINUES_FROM_PREVIOUS_PAGE"
            and receiver["region"]["selected_page_ordinal"]
            == sender_region["selected_page_ordinal"] + 1
            and receiver["region"]["physical_page"]
            == sender_region["physical_page"] + 1
        ]
        if len(receivers) != 1:
            rejected.append(
                {
                    "positive_owner": sender.get("positive_owner") is True,
                    "reason": "NEXT_RECEIVER_NOT_UNIQUE",
                    "region": canonical_clone_v1(sender_region),
                }
            )
            continue
        receiver_index, receiver = receivers[0]
        sender_lanes = sender.get("lane_axis", {})
        receiver_lanes = receiver.get("lane_axis", {})
        unit_conflict = bool(
            sender.get("unit") is not None
            and receiver.get("unit") is not None
            and sender.get("unit") != receiver.get("unit")
        )
        total_records = [
            item
            for item in (sender, receiver)
            for _row in item.get("total_row_ordinals", [])
        ]
        receiver_money = receiver.get("money_row_ordinals", [])
        combined_detail = bool(
            sender.get("detail_row_ordinals")
            or receiver.get("detail_row_ordinals")
        )
        detail_valid = bool(
            (not sender.get("detail_row_ordinals") or sender.get("detail_rows_are_declared"))
            and (
                not receiver.get("detail_row_ordinals")
                or receiver.get("detail_rows_are_declared")
            )
        )
        compatible = bool(
            sender.get("positive_owner") is True
            and complete_lanes(sender)
            and complete_lanes(receiver)
            and complete_unit(sender)
            and complete_unit(receiver)
            and sender_lanes.get("lane_keys") == receiver_lanes.get("lane_keys")
            and sender_lanes.get("source_lane_keys")
            == receiver_lanes.get("source_lane_keys")
            and not unit_conflict
            and (
                receiver.get("semantic_owner") is True
                or not _normalized(receiver.get("owner_surface_exact") or "")
            )
            and combined_detail
            and detail_valid
            and len(total_records) == 1
            and len(receiver.get("total_row_ordinals", [])) == 1
            and receiver_money
            and max(receiver_money) == receiver["total_row_ordinals"][0]
        )
        if not compatible:
            rejected.append(
                {
                    "positive_owner": sender.get("positive_owner") is True,
                    "reason": "CONTINUATION_SEMANTIC_CONFLICT",
                    "region": canonical_clone_v1(sender_region),
                }
            )
            continue
        pair = [
            canonical_clone_v1(sender_region),
            canonical_clone_v1(receiver["region"]),
        ]
        for fragment_ordinal, region in enumerate(pair, start=1):
            region["fragment_ordinal"] = fragment_ordinal
        groups.append(pair)
        consumed.update({index, receiver_index})

    for index, record in enumerate(records):
        if index in consumed or record.get("continuation") == "NONE":
            continue
        if not any(
            item.get("region") == record.get("region") for item in rejected
        ):
            rejected.append(
                {
                    "positive_owner": record.get("positive_owner") is True,
                    "reason": (
                        "MULTIHOP_BOTH_UNSUPPORTED"
                        if record.get("continuation") == "BOTH"
                        else "FROM_WITHOUT_SENDER"
                        if record.get("continuation")
                        == "CONTINUES_FROM_PREVIOUS_PAGE"
                        else "NEXT_RECEIVER_NOT_UNIQUE"
                    ),
                    "region": canonical_clone_v1(record["region"]),
                }
            )
    groups.sort(
        key=lambda group: (
            group[0]["selected_page_ordinal"],
            group[0]["physical_page"],
            int(group[0]["section_id"][1:]),
            int(group[0]["table_id"][1:]),
        )
    )
    rejected.sort(
        key=lambda item: (
            item["region"]["selected_page_ordinal"],
            item["region"]["physical_page"],
            int(item["region"]["section_id"][1:]),
            int(item["region"]["table_id"][1:]),
            item["reason"],
        )
    )
    return groups, rejected


def _split_duplicate_other_rows(
    *,
    pages: dict[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    receipts = []
    output = []
    for raw_region in regions:
        region = canonical_clone_v1(raw_region)
        page = pages[region["page_json_version_id"]]
        section, table = _source_table(
            page, section_id=region["section_id"], table_id=region["table_id"]
        )
        classification = classify_gemini_json_multitable_hierarchical_table_v1(
            page, section, table, compiled_specs=compiled_specs
        )
        rows = table.get("rows")
        other_hits = [
            hit
            for hit in classification.get("role_hits", [])
            if hit.get("role") == "OTHER_PROVISION"
        ]
        if len(other_hits) == 2 and type(rows) is list:
            changes = []
            for marker, hit in zip(_SPLIT_LABELS, other_hits, strict=True):
                row_ordinal = hit["row_ordinal"]
                row = rows[row_ordinal - 1]
                before = canonical_clone_v1(row)
                row["label_exact"] = marker
                path = row.get("hierarchy_path_exact")
                if type(path) is not list or not path:
                    raise _error("Family-37 duplicate-other hierarchy is invalid")
                path[-1] = marker
                changes.append(
                    {
                        "after_label_exact": marker,
                        "before_row_exact": before,
                        "row_ordinal": row_ordinal,
                    }
                )
            material = {
                "changes": changes,
                "locator": {
                    key: region[key]
                    for key in (
                        "page_json_version_id",
                        "physical_page",
                        "section_id",
                        "table_id",
                    )
                },
                "rule": (
                    "EXACT_TWO_DISTINCT_SOURCE_ROWS_MATCH_OTHER_PROVISION_"
                    "SPLIT_TO_DECLARED_VALIDATION_COMPONENTS_BEFORE_DIRECT_SUM"
                ),
            }
            receipts.append(
                {
                    **material,
                    "receipt_id": "gjcrpefav1:other-split:"
                    + canonical_json_sha256_v1(material),
                }
            )
            classification = classify_gemini_json_multitable_hierarchical_table_v1(
                page, section, table, compiled_specs=compiled_specs
            )
        region["component_roles"] = sorted(_classification_roles(classification))
        output.append(region)
    return output, receipts


def _transposed_role_axis(table: Mapping[str, Any]) -> dict[str, int] | None:
    columns = table.get("columns")
    money_ordinals = _money_column_ordinals(table)
    if type(columns) is not list or len(money_ordinals) not in {2, 3}:
        return None
    result = {}
    for ordinal in money_ordinals:
        column = columns[ordinal - 1]
        header_path = (
            column.get("header_path_exact") if type(column) is dict else None
        )
        if type(header_path) is not list or any(
            item is not None and type(item) is not str for item in header_path
        ):
            return None
        surface = _normalized(
            " ".join(item for item in header_path if type(item) is str)
        )
        if "du phong chung" in surface:
            role = "CUSTOMER_GENERAL"
        elif "du phong cu the" in surface:
            role = "CUSTOMER_SPECIFIC"
        elif "tong" in surface:
            role = "CUSTOMER_PROVISION"
        else:
            return None
        if role in result:
            return None
        result[role] = ordinal
    if set(result) == {"CUSTOMER_GENERAL", "CUSTOMER_SPECIFIC"}:
        return result
    if set(result) == {
        "CUSTOMER_GENERAL",
        "CUSTOMER_PROVISION",
        "CUSTOMER_SPECIFIC",
    }:
        return result
    return None


def _transposed_action_kind(value: Any) -> str | None:
    label = _normalized(value or "")
    if any(marker in label for marker in ("su dung", "xu ly")):
        return None
    if not any(marker in label for marker in ("trich lap", "hoan nhap")):
        return None
    if "trich lap" in label and "hoan nhap" in label:
        return "COMBINED_PROVISION_OR_REVERSAL"
    if "hoan nhap" in label:
        return "REVERSAL"
    return "PROVISION"


def _surface_years(value: Any) -> list[int]:
    if type(value) is str:
        surface = value
    elif type(value) is list:
        surface = " ".join(str(item or "") for item in value)
    else:
        surface = ""
    result = []
    for raw in re.findall(r"(?<!\d)(20\d{2})(?!\d)", surface):
        year = int(raw)
        if year not in result:
            result.append(year)
    return result


def _family37_source_dates_v1(surface: str) -> list[date] | None:
    matches = []
    for pattern in (
        re.compile(
            r"(?<!\d)(\d{1,2})[./-](\d{1,2})[./-](20\d{2})(?!\d)"
        ),
        re.compile(
            r"ng[aà]y\s+(\d{1,2})\s+th[aá]ng\s+(\d{1,2})\s+"
            r"n[aă]m\s+(20\d{2})",
            flags=re.IGNORECASE,
        ),
    ):
        for match in pattern.finditer(surface):
            day, month, year = match.groups()
            try:
                parsed = date(int(year), int(month), int(day))
            except ValueError:
                return None
            matches.append((match.start(), parsed))
    return [parsed for _position, parsed in sorted(matches)]


def _family37_full_twelve_month_range_v1(start: date, end: date) -> bool:
    next_year = start.year + 1
    next_day = min(start.day, monthrange(next_year, start.month)[1])
    boundary = date(next_year, start.month, next_day)
    return end in {boundary - timedelta(days=1), boundary}


_MONTH_COUNT_WORDS = {
    "mot": 1,
    "hai": 2,
    "ba": 3,
    "bon": 4,
    "nam": 5,
    "sau": 6,
    "bay": 7,
    "tam": 8,
    "chin": 9,
    "muoi": 10,
    "muoi mot": 11,
    "muoi hai": 12,
}


def _family37_numeric_month_token_v1(surface: str) -> str | None:
    """Return a duration count, excluding ``ngày 31 tháng 12`` dates."""

    for match in re.finditer(
        r"(?<!\d)([-+−–]?\s*\d{1,2})\s+thang\b", surface
    ):
        prefix = surface[: match.start()].rstrip()
        suffix = surface[match.end() :]
        if prefix.endswith("ngay") or re.match(r"\s+\d{1,2}\s+nam\b", suffix):
            continue
        return match.group(1).replace(" ", "")
    return None


def _family37_month_count_v1(surface: str) -> int | None:
    token = _family37_numeric_month_token_v1(surface)
    if token is not None:
        if token.startswith(("-", "+", "−", "–")):
            return None
        count = int(token)
        return count if 1 <= count <= 12 else None
    match = re.search(
        r"\b(muoi hai|muoi mot|muoi|chin|tam|bay|sau|nam|bon|ba|hai|mot)\s+thang\b",
        surface,
    )
    if match is None:
        return None
    token = match.group(1)
    return _MONTH_COUNT_WORDS[token]


def _family37_period_scope_v1(
    value: Any, *, semantic_role: str
) -> dict[str, Any]:
    """Parse one movement duration without inferring it from an amount."""

    surfaces = value if type(value) is list else [value]
    exact_axis = [item for item in surfaces if type(item) is str and item.strip()]
    raw_surface = " | ".join(exact_axis)
    surface = _normalized(raw_surface)
    dates = _family37_source_dates_v1(raw_surface)
    years = [
        int(item)
        for item in re.findall(r"(?<!\d)(20\d{2})(?!\d)", raw_surface)
    ]
    calendar_year = years[0] if years else None
    reasons = []
    quarter_match = re.search(
        r"\b(?:quy|q)\s*(iv|iii|ii|i|[1-4])(?:\s*[./-]?\s*(20\d{2}))?\b",
        surface,
    )
    quarter = None
    if quarter_match is not None:
        quarter = {
            "i": 1,
            "ii": 2,
            "iii": 3,
            "iv": 4,
        }.get(quarter_match.group(1))
        if quarter is None:
            quarter = int(quarter_match.group(1))
        if quarter_match.group(2) is not None:
            calendar_year = int(quarter_match.group(2))
    signed_numeric_month = re.search(
        r"[-+−–]\s*\d{1,2}\s+th(?:a|á)ng\b",
        raw_surface,
        flags=re.IGNORECASE,
    ) is not None
    numeric_month_token = _family37_numeric_month_token_v1(surface)
    unsupported_numeric_month = bool(
        signed_numeric_month
        or numeric_month_token is not None
        and (
            numeric_month_token.startswith(("-", "+", "−", "–"))
            or not 1 <= int(numeric_month_token) <= 12
        )
    )
    explicit_date_ranges = [
        (dates[index], dates[index + 1])
        for index in range(0, len(dates) - 1, 2)
    ] if dates is not None else []
    conflicting_explicit_date_ranges = bool(
        dates is not None
        and len(dates) > 2
        and (
            len(dates) % 2 != 0
            or len(set(explicit_date_ranges)) != 1
        )
    )
    if dates is None:
        dates = []
        basis = "INVALID_DATE"
        reasons.append("INVALID_CALENDAR_DATE")
    elif conflicting_explicit_date_ranges:
        basis = "INVALID_RANGE"
        reasons.append("CONFLICTING_EXPLICIT_DATE_RANGES")
    elif len(dates) >= 2 and dates[0] > dates[1]:
        basis = "INVALID_RANGE"
        reasons.append("REVERSED_DATE_RANGE")
    elif len(dates) == 1 and any(
        marker in surface for marker in ("tai ngay", "as of")
    ):
        basis = "STOCK_DATE"
    elif unsupported_numeric_month:
        basis = "UNSUPPORTED_EXPLICIT_DURATION"
        reasons.append("UNSUPPORTED_EXPLICIT_MONTH_COUNT")
    elif any(
        marker in surface
        for marker in (
            "luy ke tu dau",
            "tu dau nam den cuoi",
            "tu dau ky den ngay",
        )
    ):
        basis = "ELAPSED_FROM_YEAR_START"
    else:
        months = _family37_month_count_v1(surface)
        if months is not None and any(
            marker in surface for marker in ("dau nam", "ky", "ket thuc")
        ):
            basis = "ELAPSED_FROM_YEAR_START"
        elif len(dates) >= 2:
            if _family37_full_twelve_month_range_v1(dates[0], dates[1]):
                basis = "FULL_YEAR"
            elif dates[0].month == 1 and dates[0].day == 1:
                basis = "ELAPSED_FROM_YEAR_START"
            else:
                basis = "EXACT_DATE_RANGE"
        elif "cho nam tai chinh ket thuc" in surface or "cho nam ket thuc" in surface:
            basis = "FULL_YEAR"
        elif quarter is not None:
            basis = "SINGLE_QUARTER"
        elif "trong nam" in surface:
            basis = "AMBIGUOUS_WITHIN_YEAR"
        elif any(
            marker in surface for marker in ("trong ky", "ky nay", "ky truoc")
        ):
            basis = "RELATIVE_REPORTING_PERIOD"
        else:
            basis = "UNKNOWN"
    elapsed_month_count = None
    if basis == "ELAPSED_FROM_YEAR_START":
        if quarter is not None:
            elapsed_month_count = quarter * 3
        else:
            elapsed_month_count = _family37_month_count_v1(surface)
            if (
                elapsed_month_count is None
                and len(dates) >= 2
                and dates[0].year == dates[1].year
                and dates[0].month == dates[0].day == 1
                and dates[1].day
                == monthrange(dates[1].year, dates[1].month)[1]
            ):
                elapsed_month_count = dates[1].month
    material = {
        "basis": basis,
        "calendar_year": calendar_year,
        "elapsed_month_count": elapsed_month_count,
        "end_date": dates[1].isoformat() if len(dates) >= 2 else None,
        "quarter_ordinal": quarter,
        "raw_surface_axis": exact_axis,
        "reasons": reasons,
        "semantic_role": semantic_role,
        "start_date": dates[0].isoformat() if len(dates) >= 2 else None,
    }
    return {
        **material,
        "receipt_id": "gjcrpefav1:period-scope:"
        + canonical_json_sha256_v1(material),
    }


def _family37_section_period_surfaces_v1(
    section: Mapping[str, Any],
) -> dict[str, list[str]]:
    """Extract only lane-labelled duration clauses from section narratives."""

    result = {"CURRENT_PERIOD": [], "COMPARATIVE_PERIOD": []}
    narratives = section.get("narratives_exact")
    for narrative in narratives if type(narratives) is list else []:
        if type(narrative) is not str:
            continue
        for clause in re.split(r"[;\n]+", narrative):
            exact = clause.strip()
            normalized = _normalized(exact)
            roles = []
            if any(marker in normalized for marker in ("ky nay", "nam nay")):
                roles.append("CURRENT_PERIOD")
            if any(marker in normalized for marker in ("ky truoc", "nam truoc")):
                roles.append("COMPARATIVE_PERIOD")
            explicit_date_count = len(
                re.findall(
                    r"(?<!\d)\d{1,2}[./-]\d{1,2}[./-]20\d{2}(?!\d)",
                    exact,
                )
            )
            has_duration = bool(
                explicit_date_count >= 2
                or _family37_month_count_v1(normalized) is not None
                or re.search(r"\b(?:quy|q)\s*(?:iv|iii|ii|i|[1-4])\b", normalized)
                or "cho nam ket thuc" in normalized
            )
            if len(roles) == 1 and has_duration:
                result[roles[0]].append(exact)
    return result


def _family37_supported_duration_scope_v1(scope: Mapping[str, Any]) -> bool:
    basis = scope.get("basis")
    if basis == "EXACT_DATE_RANGE":
        return bool(scope.get("start_date") and scope.get("end_date"))
    if basis == "ELAPSED_FROM_YEAR_START":
        return bool(
            scope.get("calendar_year") is not None
            and (
                scope.get("elapsed_month_count") is not None
                or (scope.get("start_date") and scope.get("end_date"))
            )
        )
    if basis == "SINGLE_QUARTER":
        return bool(
            scope.get("calendar_year") is not None
            and scope.get("quarter_ordinal") is not None
        )
    if basis == "FULL_YEAR":
        return scope.get("calendar_year") is not None
    return False


def _family37_root_has_exact_period_axis_v1(root: Mapping[str, Any] | None) -> bool:
    if type(root) is not dict:
        return False
    scopes = root.get("period_scope_by_lane")
    return bool(
        type(scopes) is dict
        and all(
            type(scopes.get(role)) is dict
            and _family37_supported_duration_scope_v1(scopes[role])
            for role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD")
        )
    )


def _family37_observation_period_scope_v1(
    observation: Mapping[str, Any], *, semantic_role: str
) -> dict[str, Any]:
    layout_scope = observation.get("layout_period_scope")
    if (
        type(layout_scope) is dict
        and layout_scope.get("semantic_role") == semantic_role
    ):
        return canonical_clone_v1(layout_scope)
    return _family37_period_scope_v1(
        observation.get("duration_surface_axis", []),
        semantic_role=semantic_role,
    )


def _family37_exact_root_lane_for_observation_v1(
    observation: Mapping[str, Any], root: Mapping[str, Any] | None
) -> str | None:
    if not _family37_root_has_exact_period_axis_v1(root):
        return None
    period_key = observation.get("period_key")
    if (
        type(period_key) is list
        and len(period_key) == 2
        and period_key[0] == "YEAR"
        and type(period_key[1]) is int
    ):
        year_matches = [
            semantic_role
            for semantic_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD")
            if root["period_scope_by_lane"][semantic_role].get("calendar_year")
            == period_key[1]
        ]
        if len(year_matches) == 1:
            semantic_role = year_matches[0]
            detail_scope = _family37_observation_period_scope_v1(
                observation,
                semantic_role=semantic_role,
            )
            allowed, _compatibility = _family37_period_compatibility_v1(
                detail_scope, root["period_scope_by_lane"][semantic_role]
            )
            if allowed:
                return semantic_role
    matches = []
    for semantic_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"):
        root_scope = root["period_scope_by_lane"][semantic_role]
        detail_scope = _family37_observation_period_scope_v1(
            observation,
            semantic_role=semantic_role,
        )
        if not _family37_supported_duration_scope_v1(detail_scope):
            continue
        allowed, compatibility = _family37_period_compatibility_v1(
            detail_scope, root_scope
        )
        if allowed and compatibility == "EXACT_COMPATIBLE":
            matches.append(semantic_role)
    return matches[0] if len(matches) == 1 else None


def _family37_period_compatibility_v1(
    detail: Mapping[str, Any], root: Mapping[str, Any]
) -> tuple[bool, str]:
    if detail.get("semantic_role") != root.get("semantic_role"):
        return False, "SEMANTIC_LANE_CONFLICT"
    detail_basis = detail.get("basis")
    root_basis = root.get("basis")
    if detail_basis == "RELATIVE_REPORTING_PERIOD":
        invalid_parent_reasons = {
            "AMBIGUOUS_WITHIN_YEAR",
            "INVALID_DATE",
            "INVALID_RANGE",
            "STOCK_DATE",
            "UNSUPPORTED_EXPLICIT_DURATION",
            "UNKNOWN",
        }
        if root_basis in invalid_parent_reasons:
            return False, (
                "PRIMARY_PARENT_INVALID_CALENDAR_DATE"
                if root_basis == "INVALID_DATE"
                else "RELATIVE_DETAIL_WITHOUT_EXACT_PARENT_SCOPE"
            )
        if (
            detail.get("calendar_year") is not None
            and root.get("calendar_year") is not None
            and detail.get("calendar_year") != root.get("calendar_year")
        ):
            return False, "CALENDAR_YEAR_CONFLICT"
        return True, "PRIMARY_PARENT_INHERITED"
    if detail_basis in {
        "AMBIGUOUS_WITHIN_YEAR",
        "INVALID_RANGE",
        "INVALID_DATE",
        "STOCK_DATE",
        "UNSUPPORTED_EXPLICIT_DURATION",
    }:
        return False, "DETAIL_DURATION_SCOPE_NOT_PROVEN"
    if root_basis == "UNKNOWN" and detail_basis != "UNKNOWN":
        return True, "PRIMARY_ROOT_DURATION_UNPROVEN_DETAIL_ONLY"
    if detail_basis == root_basis == "UNKNOWN":
        return False, "DETAIL_AND_PRIMARY_DURATION_SCOPES_UNPROVEN"
    if detail_basis != root_basis:
        full_year_equivalent = {
            detail_basis,
            root_basis,
        } == {"FULL_YEAR", "ELAPSED_FROM_YEAR_START"} and (
            detail.get("elapsed_month_count") == 12
            or root.get("elapsed_month_count") == 12
        )
        if full_year_equivalent:
            if detail.get("calendar_year") != root.get("calendar_year"):
                return False, "CALENDAR_YEAR_CONFLICT"
            return True, "FULL_YEAR_EQUIVALENT_TWELVE_MONTH_SCOPE"
        return False, "DURATION_BASIS_CONFLICT"
    if (
        detail.get("quarter_ordinal") is not None
        and root.get("quarter_ordinal") is not None
        and detail.get("quarter_ordinal") != root.get("quarter_ordinal")
    ):
        return False, "QUARTER_CONFLICT"
    if detail.get("elapsed_month_count") != root.get("elapsed_month_count"):
        return False, "ELAPSED_WINDOW_CONFLICT"
    if (
        detail.get("calendar_year") is not None
        and root.get("calendar_year") is not None
        and detail.get("calendar_year") != root.get("calendar_year")
    ):
        return False, "CALENDAR_YEAR_CONFLICT"
    detail_bounds = (detail.get("start_date"), detail.get("end_date"))
    root_bounds = (root.get("start_date"), root.get("end_date"))
    if (
        detail_basis == "EXACT_DATE_RANGE"
        and detail_bounds != root_bounds
    ) or (
        all(item is not None for item in (*detail_bounds, *root_bounds))
        and detail_bounds != root_bounds
    ):
        return False, "EXACT_DATE_RANGE_ENDPOINT_CONFLICT"
    return True, "EXACT_COMPATIBLE"


def _family37_layout_period_scope_v1(
    narrative_exact: str, *, semantic_role: str
) -> dict[str, Any]:
    """Interpret an exact annual movement-introduction narrative."""

    scope = _family37_period_scope_v1(
        narrative_exact, semantic_role=semantic_role
    )
    surface = _normalized(narrative_exact)
    years = _surface_years(narrative_exact)
    is_full_year_surface = bool(
        len(years) == 1
        and (
            re.search(r"\btrong nam\s+20\d{2}\b", surface)
            or re.search(r"\bden het quy\s*(?:iv|4)\s+(?:nam\s+)?20\d{2}\b", surface)
        )
    )
    if not is_full_year_surface:
        return scope
    material = {
        key: canonical_clone_v1(value)
        for key, value in scope.items()
        if key != "receipt_id"
    }
    material.update(
        {
            "basis": "FULL_YEAR",
            "calendar_year": years[0],
            "elapsed_month_count": None,
            "end_date": None,
            "quarter_ordinal": None,
            "reasons": [],
            "start_date": None,
        }
    )
    return {
        **material,
        "receipt_id": "gjcrpefav1:period-scope:"
        + canonical_json_sha256_v1(material),
    }


def _family37_layout_member_kind_v1(
    section: Mapping[str, Any], member: Any
) -> str | None:
    if type(member) is str:
        surface = _normalized(member)
        if (
            "thay doi" in surface
            and "du phong rui ro tin dung" in surface
            and "sau" in surface
        ):
            return "CUSTOMER_MOVEMENT"
        if "so du du phong" in surface and "tai ngay" in surface and "sau" in surface:
            return "CUSTOMER_SNAPSHOT"
        return None
    if type(member) is not dict:
        return None
    role_axis = _transposed_role_axis(member)
    actions = [
        row
        for row in member.get("rows", [])
        if type(row) is dict
        and _transposed_action_kind(row.get("label_exact")) is not None
    ]
    if (
        role_axis is not None
        and {"CUSTOMER_GENERAL", "CUSTOMER_SPECIFIC"} <= set(role_axis)
        and actions
        and _is_structural_customer_movement(section, member)
    ):
        return "CUSTOMER_MOVEMENT"
    labels = {
        _without_leading_ordinal(_normalized(row.get("label_exact") or ""))
        for row in member.get("rows", [])
        if type(row) is dict
    }
    if (
        len(_money_column_ordinals(member)) == 1
        and not actions
        and {"du phong chung", "du phong cu the"} <= labels
    ):
        return "CUSTOMER_SNAPSHOT"
    return None


def _project_family37_same_section_period_layouts_v1(
    pages: dict[str, dict[str, Any]],
    *,
    selected_page_axis: Sequence[Mapping[str, Any]],
    document_ordinal: int,
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Bind exact annual narratives to same-section tables by visible layout."""

    roots = _primary_root_observations(
        pages=pages,
        selected_page_axis=selected_page_axis,
        document_ordinal=document_ordinal,
        compiled_specs=compiled_specs,
    )
    receipts = []
    for page_json_version_id, page in pages.items():
        source_page_sha256 = canonical_json_sha256_v1(page)
        for section_ordinal, section in enumerate(page.get("sections", []), start=1):
            if type(section) is not dict:
                continue
            narratives = section.get("narratives_exact")
            tables = section.get("tables")
            if (
                type(narratives) is not list
                or type(tables) is not list
                or len(narratives) != len(tables)
                or len(tables) < 3
                or any(type(item) is not str or not item.strip() for item in narratives)
                or any(type(item) is not dict for item in tables)
            ):
                continue
            narrative_kinds = [
                _family37_layout_member_kind_v1(section, item)
                for item in narratives
            ]
            table_kinds = [
                _family37_layout_member_kind_v1(section, item) for item in tables
            ]
            if (
                narrative_kinds != table_kinds
                or narrative_kinds.count("CUSTOMER_SNAPSHOT") != 1
                or narrative_kinds.count("CUSTOMER_MOVEMENT") != 2
            ):
                continue
            movement_indexes = [
                index
                for index, kind in enumerate(table_kinds)
                if kind == "CUSTOMER_MOVEMENT"
            ]
            movement_units = []
            for index in movement_indexes:
                unit_axis = _unit_axis(
                    tables[index],
                    compiled_specs=compiled_specs,
                    document_unit_context=None,
                )
                if unit_axis.get("complete") is not True:
                    break
                movement_units.append(unit_axis)
            if len(movement_units) != 2:
                continue
            canonical_units = {
                item.get("canonical_unit") for item in movement_units
            }
            if len(canonical_units) != 1:
                continue
            matching_roots = [
                root
                for root in roots
                if root.get("canonical_unit") == next(iter(canonical_units))
                and _family37_root_has_exact_period_axis_v1(root)
            ]
            if len(matching_roots) != 1:
                continue
            root = matching_roots[0]
            bindings = []
            for index, unit_axis in zip(
                movement_indexes, movement_units, strict=True
            ):
                narrative_exact = narratives[index]
                lane_matches = []
                for semantic_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"):
                    detail_scope = _family37_layout_period_scope_v1(
                        narrative_exact,
                        semantic_role=semantic_role,
                    )
                    root_scope = root["period_scope_by_lane"][semantic_role]
                    allowed, compatibility = _family37_period_compatibility_v1(
                        detail_scope, root_scope
                    )
                    if allowed and _family37_supported_duration_scope_v1(
                        detail_scope
                    ):
                        lane_matches.append(
                            (semantic_role, detail_scope, root_scope, compatibility)
                        )
                if len(lane_matches) != 1:
                    bindings = []
                    break
                semantic_role, detail_scope, root_scope, compatibility = lane_matches[0]
                bindings.append(
                    {
                        "compatibility": compatibility,
                        "detail_scope": detail_scope,
                        "narrative_exact": narrative_exact,
                        "narrative_ordinal": index + 1,
                        "root_locator": canonical_clone_v1(root["locator"]),
                        "root_scope": canonical_clone_v1(root_scope),
                        "semantic_role": semantic_role,
                        "table_ordinal": index + 1,
                        "unit_axis": canonical_clone_v1(unit_axis),
                    }
                )
            if [item["semantic_role"] for item in bindings] != [
                "CURRENT_PERIOD",
                "COMPARATIVE_PERIOD",
            ]:
                continue
            for binding in bindings:
                material = {
                    **binding,
                    "format_version": ADAPTER_FORMAT_VERSION,
                    "locator": {
                        "page_json_version_id": page_json_version_id,
                        "section_id": f"s{section_ordinal}",
                        "table_id": f"t{binding['table_ordinal']}",
                    },
                    "rule": (
                        "SAME_AUTHENTICATED_PAGE_SECTION_EQUAL_NARRATIVE_TABLE_"
                        "ORDINAL_TYPE_COMPATIBLE_EXACT_ROOT_PERIOD_BINDING"
                    ),
                    "source_page_canonical_json_sha256_before_projection": (
                        source_page_sha256
                    ),
                }
                receipt = {
                    **material,
                    "receipt_id": "gjcrpefav1:period-layout-projection:"
                    + canonical_json_sha256_v1(material),
                }
                tables[binding["table_ordinal"] - 1][
                    "_family37_period_layout_binding_v1"
                ] = {
                    "detail_scope": canonical_clone_v1(binding["detail_scope"]),
                    "narrative_exact": binding["narrative_exact"],
                    "receipt_id": receipt["receipt_id"],
                    "semantic_role": binding["semantic_role"],
                }
                receipts.append(receipt)
    return receipts


def _duration_signatures(value: Any) -> list[str]:
    scope = _family37_period_scope_v1(value, semantic_role="UNASSIGNED")
    basis = scope["basis"]
    if basis == "SINGLE_QUARTER":
        return [f"SINGLE_QUARTER_Q{scope['quarter_ordinal']}"]
    if basis == "ELAPSED_FROM_YEAR_START":
        months = scope["elapsed_month_count"]
        return [f"ELAPSED_{months or 'UNKNOWN'}_MONTH"]
    return [basis] if basis not in {"UNKNOWN", "RELATIVE_REPORTING_PERIOD"} else []


def _transposed_period_marker(value: Any) -> str | None:
    surface = _normalized(
        " ".join(str(item or "") for item in value)
        if type(value) is list
        else str(value or "")
    )
    if any(marker in surface for marker in ("ky nay", "nam nay")):
        return "CURRENT_PERIOD"
    if any(marker in surface for marker in ("ky truoc", "nam truoc")):
        return "COMPARATIVE_PERIOD"
    return None


def _transposed_row_period_key(
    table: Mapping[str, Any], *, row_ordinal: int
) -> tuple[str, int | str] | None:
    rows = table.get("rows")
    if type(rows) is not list or not (1 <= row_ordinal <= len(rows)):
        return None
    row = rows[row_ordinal - 1]
    if type(row) is not dict:
        return None
    path = row.get("hierarchy_path_exact")
    marker = _transposed_period_marker(path)
    if marker is not None:
        return ("SEMANTIC_ROLE", marker)
    years = _surface_years(path)
    if len(years) == 1:
        return ("YEAR", years[0])

    next_action = next(
        (
            index
            for index in range(row_ordinal, len(rows))
            if type(rows[index]) is dict
            and _transposed_action_kind(rows[index].get("label_exact")) is not None
        ),
        len(rows),
    )
    forward_years = []
    for candidate in rows[row_ordinal:next_action]:
        if type(candidate) is dict:
            forward_years.extend(_surface_years(candidate.get("hierarchy_path_exact")))
            forward_years.extend(_surface_years(candidate.get("label_exact")))
    if forward_years:
        return ("YEAR", max(forward_years))

    previous_action = next(
        (
            index
            for index in range(row_ordinal - 2, -1, -1)
            if type(rows[index]) is dict
            and _transposed_action_kind(rows[index].get("label_exact")) is not None
        ),
        -1,
    )
    backward_years = []
    for candidate in rows[previous_action + 1 : row_ordinal - 1]:
        if type(candidate) is dict:
            backward_years.extend(_surface_years(candidate.get("hierarchy_path_exact")))
            backward_years.extend(_surface_years(candidate.get("label_exact")))
    if backward_years:
        return ("YEAR", max(backward_years))
    return None


def _transposed_cells(
    row: Mapping[str, Any], *, role_axis: Mapping[str, int]
) -> dict[str, dict[str, Any]] | None:
    values = row.get("values_exact")
    if type(values) is not list:
        return None
    result = {}
    try:
        for role, ordinal in role_axis.items():
            if not (1 <= ordinal <= len(values)):
                return None
            cell = _source_money(values[ordinal - 1])
            if cell.get("coefficient") is not None and type(cell["coefficient"]) is not int:
                return None
            result[role] = cell
    except (TypeError, ValueError):
        return None
    general = result["CUSTOMER_GENERAL"].get("coefficient")
    specific = result["CUSTOMER_SPECIFIC"].get("coefficient")
    if "CUSTOMER_PROVISION" in result:
        total = result["CUSTOMER_PROVISION"].get("coefficient")
        if (
            all(type(item) is int for item in (total, general, specific))
            and general + specific != total
        ):
            return None
    elif general is None or specific is None:
        result["CUSTOMER_PROVISION"] = {
            "coefficient": None,
            "source_text": None,
            "state": "DERIVED_INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL",
        }
    elif type(general) is int and type(specific) is int:
        result["CUSTOMER_PROVISION"] = {
            "coefficient": general + specific,
            "source_text": None,
            "state": "EXACT_VISIBLE_GENERAL_AND_SPECIFIC_SUM",
        }
    else:
        return None
    return result


def _family_document_unit_context(
    *,
    pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    # Unit authority is strictly textual/structural.  Matching monetary
    # coefficients, magnitudes, signs, or scales must never select a unit.
    context = canonical_clone_v1(
        _document_unit_context_axis(pages, compiled_specs=compiled_specs)
    )
    # The shared customer-deposit context intentionally retains exact owner
    # row coefficients for that family's narrowly governed value
    # corroboration.  Family 37 has no such authority: strip the evidence at
    # this boundary even when textual document-unit consensus is otherwise
    # unique.  Shared ``_unit_axis`` can then inherit only the explicit
    # consensus fields, never a matching coefficient vector.
    context["owner_row_evidence"] = []
    context["owner_row_evidence_axis_sha256"] = canonical_json_sha256_v1([])
    context["family37_value_unit_corroboration_disabled"] = True
    return context


def _project_family37_document_unit_consensus_v1(
    pages: dict[str, dict[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Materialize only a strict textual document-unit consensus on a clone."""

    context = _family_document_unit_context(
        pages=pages, compiled_specs=compiled_specs
    )
    canonical_unit = context.get("canonical_unit")
    if (
        context.get("status") != "UNIQUE"
        or canonical_unit not in _UNIT_SURFACE
        or context.get("conflicts")
    ):
        return []
    receipts = []
    for page_json_version_id, page in pages.items():
        for section_ordinal, section in enumerate(page.get("sections", []), start=1):
            if (
                type(section) is not dict
                or section.get("content_kind") != "FINANCIAL_NOTE"
            ):
                continue
            for table_ordinal, table in enumerate(
                section.get("tables", []), start=1
            ):
                if type(table) is not dict:
                    continue
                owner_surface = _normalized(
                    " ".join(
                        item
                        for item in (
                            section.get("title_exact"),
                            table.get("title_exact"),
                        )
                        if type(item) is str
                    )
                )
                if "du phong rui ro" not in owner_surface:
                    continue
                local_axis = _unit_axis(
                    table,
                    compiled_specs=compiled_specs,
                    document_unit_context=None,
                )
                if (
                    local_axis.get("complete") is True
                    or local_axis.get("evidence")
                    or local_axis.get("undeclared_evidence")
                    or local_axis.get("reasons")
                    != ["MONEY_UNIT_NOT_EXACTLY_RESOLVED"]
                ):
                    continue
                before_unit_exact = table.get("unit_exact")
                table["unit_exact"] = _UNIT_SURFACE[canonical_unit]
                material = {
                    "after_unit_exact": table["unit_exact"],
                    "before_unit_exact": before_unit_exact,
                    "document_unit_context": {
                        "canonical_unit": canonical_unit,
                        "distinct_page_version_count": context[
                            "distinct_page_version_count"
                        ],
                        "evidence": canonical_clone_v1(context["evidence"]),
                        "evidence_axis_sha256": context["evidence_axis_sha256"],
                        "status": context["status"],
                    },
                    "locator": {
                        "page_json_version_id": page_json_version_id,
                        "section_id": f"s{section_ordinal}",
                        "table_id": f"t{table_ordinal}",
                    },
                    "rule": (
                        "STRICT_EXPLICIT_MULTI_PAGE_DOCUMENT_UNIT_CONSENSUS_"
                        "PROJECTED_WITHOUT_OWNER_ROW_VALUE_CORROBORATION"
                    ),
                }
                receipts.append(
                    {
                        **material,
                        "receipt_id": "gjcrpefav1:unit-consensus-projection:"
                        + canonical_json_sha256_v1(material),
                    }
                )
    return receipts


def _sum_transposed_action_cells(
    actions: Sequence[Mapping[str, Any]], *, role: str
) -> dict[str, Any]:
    cells = [action["cells"][role] for action in actions]
    if len(cells) == 1:
        return canonical_clone_v1(cells[0])
    coefficients = [cell.get("coefficient") for cell in cells]
    if any(coefficient is None for coefficient in coefficients):
        return {
            "coefficient": None,
            "source_text": None,
            "state": "DERIVED_INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL",
        }
    if not all(type(coefficient) is int for coefficient in coefficients):
        raise _error("Family-37 transposed action coefficient is invalid")
    return {
        "coefficient": sum(coefficients),
        "source_text": None,
        "state": "EXACT_VISIBLE_PROVISION_AND_REVERSAL_SUM",
    }


def _transposed_table_observations(
    *,
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    region: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
    document_unit_context: Mapping[str, Any] | None,
    period_surface_by_lane: Mapping[str, Sequence[str]],
) -> list[dict[str, Any]]:
    role_axis = _transposed_role_axis(table)
    rows = table.get("rows")
    if role_axis is None or type(rows) is not list:
        return []
    grouped: dict[tuple[str, int | str] | None, list[dict[str, Any]]] = {}
    ending_by_period: dict[
        tuple[str, int | str] | None, list[dict[str, Any]]
    ] = {}
    for row_ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict:
            continue
        normalized_label = _normalized(row.get("label_exact") or "")
        if "so du cuoi" in normalized_label:
            ending_cells = _transposed_cells(row, role_axis=role_axis)
            ending_coefficient = (
                ending_cells.get("CUSTOMER_PROVISION", {}).get("coefficient")
                if type(ending_cells) is dict
                else None
            )
            if type(ending_coefficient) is int:
                ending_by_period.setdefault(
                    _transposed_row_period_key(table, row_ordinal=row_ordinal), []
                ).append(
                    {
                        "cells": canonical_clone_v1(ending_cells),
                        "row": canonical_clone_v1(row),
                        "row_ordinal": row_ordinal,
                    }
                )
        action_kind = _transposed_action_kind(row.get("label_exact"))
        cells = _transposed_cells(row, role_axis=role_axis)
        if action_kind is None or cells is None:
            continue
        key = _transposed_row_period_key(table, row_ordinal=row_ordinal)
        grouped.setdefault(key, []).append(
            {
                "action_kind": action_kind,
                "cells": cells,
                "row": canonical_clone_v1(row),
                "row_ordinal": row_ordinal,
            }
        )
    if not grouped:
        return []
    unit_axis = _unit_axis(
        table,
        compiled_specs=compiled_specs,
        document_unit_context=document_unit_context,
    )
    canonical_unit = (
        unit_axis.get("canonical_unit") if unit_axis.get("complete") is True else None
    )
    header_surface = _normalized(
        " ".join(
            str(item or "")
            for column in table.get("columns", [])
            if type(column) is dict and column.get("value_kind") == "MONEY"
            for item in column.get("header_path_exact", [])
        )
    )
    container_surface = " ".join(
        [
            str(section.get("title_exact") or ""),
            str(table.get("title_exact") or ""),
        ]
    )
    position_surface = _normalized(header_surface + " " + container_surface)
    container_marker = _transposed_period_marker(table.get("title_exact"))
    structural_container_years = _surface_years(container_surface)
    layout_period_binding = table.get("_family37_period_layout_binding_v1")
    result = []
    for period_key, actions in grouped.items():
        if (
            period_key is None
            and type(layout_period_binding) is dict
            and layout_period_binding.get("semantic_role")
            in {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"}
        ):
            period_key = (
                "SEMANTIC_ROLE",
                layout_period_binding["semantic_role"],
            )
        elif period_key is None and container_marker is not None:
            period_key = ("SEMANTIC_ROLE", container_marker)
        elif period_key is None and len(structural_container_years) == 1:
            period_key = ("YEAR", structural_container_years[0])
        combined = [
            item
            for item in actions
            if item["action_kind"] == "COMBINED_PROVISION_OR_REVERSAL"
        ]
        provisions = [item for item in actions if item["action_kind"] == "PROVISION"]
        reversals = [item for item in actions if item["action_kind"] == "REVERSAL"]
        variants = []
        if combined and (provisions or reversals):
            continue
        variant_actions = []
        if combined:
            variant_actions.append(("DIRECT_COMBINED_PROVISION_OR_REVERSAL", combined))
        elif provisions:
            variant_actions.append(("DIRECT_GROSS_PROVISION", provisions))
            if reversals:
                variant_actions.append(
                    ("EXACT_NET_PROVISION_PLUS_REVERSAL", [*provisions, *reversals])
                )
        elif reversals:
            variant_actions.append(("DIRECT_REVERSAL", reversals))
        for variant_kind, selected_actions in variant_actions:
            variants.append(
                {
                    "cells": {
                        role: _sum_transposed_action_cells(
                            selected_actions, role=role
                        )
                        for role in (
                            "CUSTOMER_PROVISION",
                            "CUSTOMER_GENERAL",
                            "CUSTOMER_SPECIFIC",
                        )
                    },
                    "duration_signatures": _duration_signatures(
                        [action["row"].get("label_exact") for action in selected_actions]
                    ),
                    "selected_actions": canonical_clone_v1(selected_actions),
                    "variant_kind": variant_kind,
                }
            )
        if not variants:
            continue
        endings = ending_by_period.get(period_key, [])
        if not endings and len(grouped) == 1:
            all_endings = [
                ending
                for period_endings in ending_by_period.values()
                for ending in period_endings
            ]
            endings = all_endings if len(all_endings) == 1 else []
        action_scope_surface = _normalized(
            " ".join(
                str(item or "")
                for action in actions
                for item in action["row"].get("hierarchy_path_exact", [])
            )
        )
        duration_surface_axis = [
            item
            for item in (
                table.get("title_exact"),
                (
                    layout_period_binding.get("narrative_exact")
                    if type(layout_period_binding) is dict
                    else None
                ),
            )
            if type(item) is str and item.strip()
        ]
        for action in actions:
            path = action["row"].get("hierarchy_path_exact")
            duration_surface_axis.extend(
                item
                for item in (path if type(path) is list else [])
                if type(item) is str and item.strip()
            )
            label = action["row"].get("label_exact")
            if type(label) is str and label.strip():
                duration_surface_axis.append(label)
        if (
            type(period_key) is tuple
            and len(period_key) == 2
            and period_key[0] == "SEMANTIC_ROLE"
        ):
            duration_surface_axis.extend(
                item
                for item in period_surface_by_lane.get(str(period_key[1]), [])
                if item not in duration_surface_axis
            )
        elif (
            type(period_key) is tuple
            and len(period_key) == 2
            and period_key[0] == "YEAR"
        ):
            for surfaces in period_surface_by_lane.values():
                duration_surface_axis.extend(
                    item
                    for item in surfaces
                    if _surface_years(item) == [period_key[1]]
                    and item not in duration_surface_axis
                )
        container_years = _surface_years(duration_surface_axis)
        container_duration_signatures = _duration_signatures(
            duration_surface_axis
        )
        result.append(
            {
                "all_actions": canonical_clone_v1(actions),
                "canonical_unit": canonical_unit,
                "container_years": container_years,
                "duration_surface_axis": duration_surface_axis,
                "container_duration_signatures": container_duration_signatures,
                "ending_observation": (
                    canonical_clone_v1(endings[0]) if len(endings) == 1 else None
                ),
                "header_position": (
                    "CURRENT_POSITION"
                    if "so cuoi quy" in position_surface
                    or period_key == ("SEMANTIC_ROLE", "CURRENT_PERIOD")
                    else "OPENING_ANNUAL_POSITION"
                    if "so dau nam" in position_surface
                    or "so du dau nam" in action_scope_surface
                    else None
                ),
                "layout_period_scope": (
                    canonical_clone_v1(
                        layout_period_binding.get("detail_scope")
                    )
                    if type(layout_period_binding) is dict
                    and type(layout_period_binding.get("detail_scope")) is dict
                    else None
                ),
                "layout_period_binding_receipt_id": (
                    layout_period_binding.get("receipt_id")
                    if type(layout_period_binding) is dict
                    else None
                ),
                "period_key": (
                    list(period_key) if type(period_key) is tuple else period_key
                ),
                "region": canonical_clone_v1(region),
                "role_axis": canonical_clone_v1(role_axis),
                "table_title_exact": table.get("title_exact"),
                "unit_axis": canonical_clone_v1(unit_axis),
                "variants": variants,
            }
        )
    return result


def _movement_owner_kind(surface: str) -> str | None:
    normalized = _normalized(surface)
    if "du phong" not in normalized and "cho vay khach hang" not in normalized:
        return None
    if "mua no" in normalized:
        return "PURCHASED_DEBT"
    if "chung khoan" in normalized or "trai phieu" in normalized:
        return "SECURITIES_CONTROL"
    if "cho vay khach hang" in normalized or "du no cho vay khach hang" in normalized:
        return "CUSTOMER"
    if "tctd" in normalized or "to chuc tin dung" in normalized:
        return "INTERBANK"
    return None


def _is_structural_customer_movement(
    section: Mapping[str, Any], table: Mapping[str, Any]
) -> bool:
    """Recognize a customer movement from local table structure only.

    Section narratives can describe an earlier table and therefore cannot own a
    later continuation. Exact general/specific columns plus a generic credit-
    risk movement title establish customer scope unless the local section/table
    title explicitly names a competing provision owner.
    """

    role_axis = _transposed_role_axis(table)
    if role_axis is None or not {
        "CUSTOMER_GENERAL",
        "CUSTOMER_SPECIFIC",
    } <= set(role_axis):
        return False
    structural_surface = " ".join(
        (
            str(section.get("title_exact") or ""),
            str(table.get("title_exact") or ""),
        )
    )
    structural_owner = _movement_owner_kind(structural_surface)
    if structural_owner in {
        "INTERBANK",
        "PURCHASED_DEBT",
        "SECURITIES_CONTROL",
    }:
        return False
    structural_normalized = _normalized(structural_surface)
    return bool(
        "du phong rui ro tin dung" in structural_normalized
        and any(
            marker in structural_normalized
            for marker in ("thay doi", "tang giam", "doi voi")
        )
    )


def _customer_balance_summary_owner(table: Mapping[str, Any]) -> bool:
    """Recognize an exact customer allowance summary preceding a movement table."""

    rows = table.get("rows")
    if type(rows) is not list:
        return False
    normalized_rows = [
        _without_leading_ordinal(_normalized(row.get("label_exact") or ""))
        for row in rows
        if type(row) is dict
    ]
    owner_surface = _normalized(
        " ".join(
            [
                str(table.get("title_exact") or ""),
                *(
                    str(item or "")
                    for row in rows
                    if type(row) is dict
                    for item in row.get("hierarchy_path_exact", [])
                ),
            ]
        )
    )
    has_customer_scope = "du phong rui ro cho vay khach hang" in owner_surface
    has_general = any(label == "du phong chung" for label in normalized_rows)
    has_specific = any(label == "du phong cu the" for label in normalized_rows)
    return has_customer_scope and has_general and has_specific


def _choose_transposed_variant(
    observation: Mapping[str, Any], *, root: Mapping[str, Any] | None
) -> dict[str, Any] | None:
    """Choose gross/net only from an exact primary action label, never amounts."""

    variants = observation.get("variants")
    if type(variants) is not list or not variants:
        return None
    if len(variants) == 1:
        return canonical_clone_v1(variants[0])
    root_label = (
        root.get("row", {}).get("label_exact") if type(root) is dict else None
    )
    normalized_root = _without_leading_ordinal(_normalized(root_label or ""))
    if "hoan nhap" in normalized_root:
        required_kind = "EXACT_NET_PROVISION_PLUS_REVERSAL"
    elif "chi phi" in normalized_root and "du phong" in normalized_root:
        required_kind = "DIRECT_GROSS_PROVISION"
    else:
        return None
    matching = [
        variant
        for variant in variants
        if variant.get("variant_kind") == required_kind
    ]
    return canonical_clone_v1(matching[0]) if len(matching) == 1 else None


def _separate_customer_role_kind(
    section: Mapping[str, Any], table: Mapping[str, Any]
) -> str | None:
    surface = _normalized(
        " ".join(
            [
                str(section.get("title_exact") or ""),
                *(str(item or "") for item in section.get("narratives_exact", [])),
                str(table.get("title_exact") or ""),
            ]
        )
    )
    if "cho vay khach hang" not in surface or "bien dong" not in surface:
        return None
    roles = []
    if "du phong chung" in surface:
        roles.append("CUSTOMER_GENERAL")
    if "du phong cu the" in surface:
        roles.append("CUSTOMER_SPECIFIC")
    return roles[0] if len(roles) == 1 else None


def _sum_separate_role_action_cells(
    actions: Sequence[Mapping[str, Any]], *, lane: int
) -> dict[str, Any]:
    cells = [action["cells"][lane] for action in actions]
    if len(cells) == 1:
        return canonical_clone_v1(cells[0])
    coefficients = [cell.get("coefficient") for cell in cells]
    if any(coefficient is None for coefficient in coefficients):
        return {
            "coefficient": None,
            "source_text": None,
            "state": "DERIVED_INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL",
        }
    if not all(type(coefficient) is int for coefficient in coefficients):
        raise _error("Family-37 separate-role action coefficient is invalid")
    return {
        "coefficient": sum(coefficients),
        "source_text": None,
        "state": "EXACT_VISIBLE_PROVISION_AND_REVERSAL_SUM",
    }


def _separate_role_variants(
    *,
    table: Mapping[str, Any],
    money_ordinals: Sequence[int],
) -> list[dict[str, Any]]:
    actions = []
    for row_ordinal, row in enumerate(table.get("rows", []), start=1):
        if type(row) is not dict:
            continue
        action_kind = _transposed_action_kind(row.get("label_exact"))
        values = row.get("values_exact")
        if action_kind is None or type(values) is not list:
            continue
        cells = []
        try:
            for ordinal in money_ordinals:
                cells.append(_source_money(values[ordinal - 1]))
        except (IndexError, TypeError, ValueError):
            return []
        actions.append(
            {
                "action_kind": action_kind,
                "cells": cells,
                "row": canonical_clone_v1(row),
                "row_ordinal": row_ordinal,
            }
        )
    combined = [
        item
        for item in actions
        if item["action_kind"] == "COMBINED_PROVISION_OR_REVERSAL"
    ]
    provisions = [item for item in actions if item["action_kind"] == "PROVISION"]
    reversals = [item for item in actions if item["action_kind"] == "REVERSAL"]
    if combined and (provisions or reversals):
        return []
    variant_actions = []
    if combined:
        variant_actions.append(("DIRECT_COMBINED_PROVISION_OR_REVERSAL", combined))
    elif provisions:
        variant_actions.append(("DIRECT_GROSS_PROVISION", provisions))
        if reversals:
            variant_actions.append(
                ("EXACT_NET_PROVISION_PLUS_REVERSAL", [*provisions, *reversals])
            )
    elif reversals:
        variant_actions.append(("DIRECT_REVERSAL", reversals))
    return [
        {
            "selected_actions": canonical_clone_v1(selected_actions),
            "values": [
                _sum_separate_role_action_cells(selected_actions, lane=lane)
                for lane in range(len(money_ordinals))
            ],
            "variant_kind": variant_kind,
        }
        for variant_kind, selected_actions in variant_actions
    ]


def _customer_separate_role_observations(
    *,
    document: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    document_unit_context: Mapping[str, Any],
) -> list[dict[str, Any]]:
    axis_by_version = {
        item["page_json_version_id"]: item
        for item in selected_page_axis
        if item.get("document_ordinal") == document["document_ordinal"]
    }
    tables_by_role: dict[str, list[dict[str, Any]]] = {
        "CUSTOMER_GENERAL": [],
        "CUSTOMER_SPECIFIC": [],
    }
    for page_json_version_id, page in pages.items():
        page_axis = axis_by_version.get(page_json_version_id)
        if page_axis is None or page.get("status") not in {
            "FINANCIAL_NOTE_CONTENT",
            "MIXED_FINANCIAL_CONTENT",
        }:
            continue
        for section_ordinal, section in enumerate(page.get("sections", []), start=1):
            if type(section) is not dict or section.get("content_kind") != "FINANCIAL_NOTE":
                continue
            for table_ordinal, table in enumerate(
                section.get("tables", []), start=1
            ):
                if type(table) is not dict:
                    continue
                role = _separate_customer_role_kind(section, table)
                if role is None:
                    continue
                lane_axis = _multitable_lane_axis(
                    section, table, compiled_specs=compiled_specs
                )
                money_ordinals = lane_axis.get("money_column_ordinals")
                unit_axis = _unit_axis(
                    table,
                    compiled_specs=compiled_specs,
                    document_unit_context=document_unit_context,
                )
                if (
                    lane_axis.get("complete") is not True
                    or type(money_ordinals) is not list
                    or len(money_ordinals) != 2
                    or unit_axis.get("complete") is not True
                    or unit_axis.get("canonical_unit") not in _UNIT_SURFACE
                ):
                    continue
                variants = _separate_role_variants(
                    table=table, money_ordinals=money_ordinals
                )
                if not variants:
                    continue
                tables_by_role[role].append(
                    {
                        "duration_surface_by_lane": [
                            [
                                item
                                for item in (
                                    table["columns"][column_ordinal - 1].get(
                                        "header_path_exact", []
                                    )
                                    if type(table["columns"][column_ordinal - 1])
                                    is dict
                                    else []
                                )
                                if type(item) is str and item.strip()
                            ]
                            for column_ordinal in money_ordinals
                        ],
                        "lane_axis": canonical_clone_v1(lane_axis),
                        "money_column_ordinals": canonical_clone_v1(money_ordinals),
                        "region": _region(
                            document=document,
                            page_axis=page_axis,
                            section_ordinal=section_ordinal,
                            table_ordinal=table_ordinal,
                            component_roles=[role],
                        ),
                        "role": role,
                        "unit_axis": canonical_clone_v1(unit_axis),
                        "variants": variants,
                    }
                )
    if any(len(tables_by_role[role]) != 1 for role in tables_by_role):
        return []
    general = tables_by_role["CUSTOMER_GENERAL"][0]
    specific = tables_by_role["CUSTOMER_SPECIFIC"][0]
    if (
        general["lane_axis"].get("lane_keys")
        != specific["lane_axis"].get("lane_keys")
        or general["unit_axis"]["canonical_unit"]
        != specific["unit_axis"]["canonical_unit"]
    ):
        return []
    observations = []
    for lane, period_key in enumerate(general["lane_axis"]["lane_keys"]):
        variants = []
        for general_variant in general["variants"]:
            for specific_variant in specific["variants"]:
                general_cell = general_variant["values"][lane]
                specific_cell = specific_variant["values"][lane]
                coefficients = [
                    general_cell.get("coefficient"),
                    specific_cell.get("coefficient"),
                ]
                if any(coefficient is None for coefficient in coefficients):
                    total_cell = {
                        "coefficient": None,
                        "source_text": None,
                        "state": "DERIVED_INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL",
                    }
                elif all(type(coefficient) is int for coefficient in coefficients):
                    total_cell = {
                        "coefficient": sum(coefficients),
                        "source_text": None,
                        "state": "EXACT_VISIBLE_GENERAL_AND_SPECIFIC_SUM",
                    }
                else:
                    continue
                selected_actions = []
                all_actions = []
                for role_table, role_variant in (
                    (general, general_variant),
                    (specific, specific_variant),
                ):
                    for action in role_variant["selected_actions"]:
                        material = {
                            **canonical_clone_v1(action),
                            "column_ordinal": role_table[
                                "money_column_ordinals"
                            ][lane],
                            "region": canonical_clone_v1(role_table["region"]),
                            "source_cell": canonical_clone_v1(
                                action["cells"][lane]
                            ),
                            "source_role": role_table["role"],
                        }
                        selected_actions.append(material)
                        all_actions.append(material)
                variants.append(
                    {
                        "cells": {
                            "CUSTOMER_GENERAL": canonical_clone_v1(general_cell),
                            "CUSTOMER_PROVISION": total_cell,
                            "CUSTOMER_SPECIFIC": canonical_clone_v1(specific_cell),
                        },
                        "duration_signatures": _duration_signatures(
                            [
                                action["row"].get("label_exact")
                                for action in selected_actions
                            ]
                        ),
                        "selected_actions": selected_actions,
                        "variant_kind": (
                            "EXACT_SEPARATE_GENERAL_AND_SPECIFIC_TABLES_"
                            + general_variant["variant_kind"]
                            + "_"
                            + specific_variant["variant_kind"]
                        ),
                    }
                )
        if not variants:
            return []
        all_actions_by_axis = {}
        for variant in variants:
            for action in variant["selected_actions"]:
                region = action["region"]
                axis = (
                    region["page_json_version_id"],
                    region["section_id"],
                    region["table_id"],
                    action["row_ordinal"],
                    action["column_ordinal"],
                )
                all_actions_by_axis[axis] = canonical_clone_v1(action)
        observations.append(
            {
                "all_actions": list(all_actions_by_axis.values()),
                "canonical_unit": general["unit_axis"]["canonical_unit"],
                "container_duration_signatures": [],
                "container_years": [],
                "duration_surface_axis": canonical_clone_v1(
                    general["duration_surface_by_lane"][lane]
                ),
                "ending_observation": None,
                "header_position": None,
                "period_key": [
                    "SEMANTIC_ROLE",
                    "CURRENT_PERIOD" if lane == 0 else "COMPARATIVE_PERIOD",
                ],
                "region": canonical_clone_v1(general["region"]),
                "regions": [
                    canonical_clone_v1(general["region"]),
                    canonical_clone_v1(specific["region"]),
                ],
                "role_axis": {
                    "CUSTOMER_GENERAL": general["money_column_ordinals"][lane],
                    "CUSTOMER_SPECIFIC": specific["money_column_ordinals"][lane],
                },
                "source_layout_kind": "SEPARATE_CUSTOMER_ROLE_TABLES",
                "source_period_key": canonical_clone_v1(period_key),
                "table_title_exact": None,
                "unit_axis": canonical_clone_v1(general["unit_axis"]),
                "variants": variants,
            }
        )
    return observations


def _customer_transposed_observations(
    *,
    document: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    document_unit_context = _family_document_unit_context(
        pages=pages, compiled_specs=compiled_specs
    )
    axis_by_version = {
        item["page_json_version_id"]: item
        for item in selected_page_axis
        if item.get("document_ordinal") == document["document_ordinal"]
    }
    ordered_pages = sorted(
        (
            (axis["selected_page_ordinal"], version_id, pages[version_id], axis)
            for version_id, axis in axis_by_version.items()
            if version_id in pages
        ),
        key=lambda item: item[0],
    )
    observations = []
    active_owner: str | None = None
    active_owner_page: int | None = None
    continuation_support_region: dict[str, Any] | None = None
    continuation_support_page: int | None = None
    continuation_period_surface_by_lane: dict[str, list[str]] | None = None
    for _selected_ordinal, _version_id, page, axis in ordered_pages:
        if page.get("status") not in {
            "FINANCIAL_NOTE_CONTENT",
            "MIXED_FINANCIAL_CONTENT",
        }:
            continue
        for section_ordinal, section in enumerate(page.get("sections", []), start=1):
            if (
                type(section) is not dict
                or section.get("content_kind") != "FINANCIAL_NOTE"
            ):
                continue
            section_surface = " ".join(
                [
                    str(section.get("title_exact") or ""),
                    *(str(item or "") for item in section.get("narratives_exact", [])),
                ]
            )
            section_owner = _movement_owner_kind(section_surface)
            if section_owner is not None:
                active_owner = section_owner
                active_owner_page = axis["physical_page"]
            for table_ordinal, table in enumerate(
                section.get("tables", []), start=1
            ):
                if type(table) is not dict:
                    continue
                table_surface = section_surface + " " + str(
                    table.get("title_exact") or ""
                )
                explicit_owner = _movement_owner_kind(table_surface)
                owner = explicit_owner
                if _customer_balance_summary_owner(table):
                    active_owner = "CUSTOMER"
                    active_owner_page = axis["physical_page"]
                structural_customer_movement = _is_structural_customer_movement(
                    section, table
                )
                if structural_customer_movement:
                    owner = "CUSTOMER"
                if owner is None and active_owner_page is not None and (
                    axis["physical_page"] - active_owner_page <= 1
                ):
                    owner = active_owner
                elif structural_customer_movement and active_owner in {
                    "CUSTOMER",
                    "INTERBANK",
                }:
                    owner = active_owner
                if owner != "CUSTOMER":
                    if explicit_owner is not None:
                        active_owner = explicit_owner
                        active_owner_page = axis["physical_page"]
                    continue
                local_period_surface_by_lane = (
                    _family37_section_period_surfaces_v1(section)
                )
                effective_period_surface_by_lane = canonical_clone_v1(
                    local_period_surface_by_lane
                )
                if (
                    table.get("continuation") == "CONTINUES_FROM_PREVIOUS_PAGE"
                    and continuation_support_region is not None
                    and continuation_support_page == axis["physical_page"] - 1
                    and continuation_period_surface_by_lane is not None
                ):
                    for semantic_role, surfaces in (
                        continuation_period_surface_by_lane.items()
                    ):
                        effective_period_surface_by_lane[semantic_role] = [
                            *surfaces,
                            *(
                                item
                                for item in effective_period_surface_by_lane.get(
                                    semantic_role, []
                                )
                                if item not in surfaces
                            ),
                        ]
                region = _region(
                    document=document,
                    page_axis=axis,
                    section_ordinal=section_ordinal,
                    table_ordinal=table_ordinal,
                    component_roles=[
                        "CUSTOMER_GENERAL",
                        "CUSTOMER_PROVISION",
                        "CUSTOMER_SPECIFIC",
                    ],
                )
                if table.get("continuation") == "CONTINUES_ON_NEXT_PAGE":
                    continuation_support_region = canonical_clone_v1(region)
                    continuation_support_page = axis["physical_page"]
                    continuation_period_surface_by_lane = canonical_clone_v1(
                        local_period_surface_by_lane
                    )
                    active_owner = "CUSTOMER"
                    active_owner_page = axis["physical_page"]
                table_observations = _transposed_table_observations(
                    section=section,
                    table=table,
                    region=region,
                    compiled_specs=compiled_specs,
                    document_unit_context=document_unit_context,
                    period_surface_by_lane=effective_period_surface_by_lane,
                )
                if table_observations:
                    if (
                        table.get("continuation") == "CONTINUES_FROM_PREVIOUS_PAGE"
                        and continuation_support_region is not None
                        and continuation_support_page == axis["physical_page"] - 1
                    ):
                        for observation in table_observations:
                            observation["regions"] = [
                                canonical_clone_v1(continuation_support_region),
                                canonical_clone_v1(observation["region"]),
                            ]
                    observations.extend(table_observations)
                    active_owner = "CUSTOMER"
                    active_owner_page = axis["physical_page"]
    observations.extend(
        _customer_separate_role_observations(
            document=document,
            selected_page_axis=selected_page_axis,
            pages=pages,
            compiled_specs=compiled_specs,
            document_unit_context=document_unit_context,
        )
    )
    observations.sort(
        key=lambda item: (
            item["region"]["selected_page_ordinal"],
            int(item["region"]["section_id"][1:]),
            int(item["region"]["table_id"][1:]),
            str(item.get("period_key")),
        )
    )
    return observations


def _transposed_detail_receipt(
    *,
    document: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    roots = _primary_root_observations(
        pages=pages,
        selected_page_axis=selected_page_axis,
        document_ordinal=document["document_ordinal"],
        compiled_specs=compiled_specs,
    )
    observations = _customer_transposed_observations(
        document=document,
        selected_page_axis=selected_page_axis,
        pages=pages,
        compiled_specs=compiled_specs,
    )
    if not observations:
        return None
    roots = _primary_roots_compatible_with_observations(roots, observations)
    if len(roots) > 1:
        return None
    root = roots[0] if roots else None
    excluded_position_control = None
    excluded_noncomparable_duration_control = None
    position_current = [
        item for item in observations if item.get("header_position") == "CURRENT_POSITION"
    ]
    position_opening = [
        item
        for item in observations
        if item.get("header_position") == "OPENING_ANNUAL_POSITION"
    ]
    rule = None
    current = None
    comparative = None
    if len(position_current) == 1 and len(position_opening) == 1:
        current = position_current[0]
        excluded_position_control = position_opening[0]
        rule = (
            "CURRENT_DURATION_MOVEMENT_ROW_ONLY_SECOND_ANNUAL_POSITION_"
            "CONTROL_IS_NOT_COMPARATIVE_DURATION"
        )
    else:
        semantic_candidates = {
            semantic_role: [
                observation
                for observation in observations
                if observation.get("header_position")
                == (
                    "CURRENT_POSITION"
                    if semantic_role == "CURRENT_PERIOD"
                    else "COMPARATIVE_POSITION"
                )
                or observation.get("period_key")
                == ["SEMANTIC_ROLE", semantic_role]
                or _transposed_period_marker(
                    observation.get("table_title_exact")
                )
                == semantic_role
            ]
            for semantic_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD")
        }
        if len(semantic_candidates["CURRENT_PERIOD"]) == 1:
            current = semantic_candidates["CURRENT_PERIOD"][0]
        if len(semantic_candidates["COMPARATIVE_PERIOD"]) == 1:
            comparative = semantic_candidates["COMPARATIVE_PERIOD"][0]

        assigned = {id(item) for item in (current, comparative) if item is not None}
        exact_root_candidates = {
            "CURRENT_PERIOD": [],
            "COMPARATIVE_PERIOD": [],
        }
        for observation in observations:
            if id(observation) in assigned:
                continue
            exact_lane = _family37_exact_root_lane_for_observation_v1(
                observation, root
            )
            if exact_lane is not None:
                exact_root_candidates[exact_lane].append(observation)
        if current is None and len(exact_root_candidates["CURRENT_PERIOD"]) == 1:
            current = exact_root_candidates["CURRENT_PERIOD"][0]
        if (
            comparative is None
            and len(exact_root_candidates["COMPARATIVE_PERIOD"]) == 1
        ):
            comparative = exact_root_candidates["COMPARATIVE_PERIOD"][0]
        if current is not None or comparative is not None:
            rule = (
                "EXPLICIT_SEMANTIC_LANE_OR_EXACT_PRIMARY_PERIOD_SCOPE_"
                "MATCH_WITHOUT_YEAR_ORDER_OR_AMOUNT_ROUTING"
            )
    if current is None and comparative is None:
        return None
    layout_period_binding_receipt_ids = [
        item.get("layout_period_binding_receipt_id")
        for item in (current, comparative)
        if type(item) is dict
    ]
    both_lanes_layout_bound = bool(
        current is not None
        and comparative is not None
        and len(layout_period_binding_receipt_ids) == 2
        and all(type(item) is str for item in layout_period_binding_receipt_ids)
    )
    if current is not None and comparative is not None:
        ordered_container_durations = []
        for observation in (current, comparative):
            for signature in observation.get("container_duration_signatures", []):
                if signature not in ordered_container_durations:
                    ordered_container_durations.append(signature)
        comparative_action_durations = {
            signature
            for variant in comparative.get("variants", [])
            for signature in variant.get("duration_signatures", [])
        }
        current_container_durations = set(
            current.get("container_duration_signatures", [])
        )
        current_action_durations = {
            signature
            for variant in current.get("variants", [])
            for signature in variant.get("duration_signatures", [])
        }
        if not both_lanes_layout_bound and (
            len(ordered_container_durations) >= 2
            and ordered_container_durations[0]
            != ordered_container_durations[1]
        ) or (
            comparative_action_durations == {"FULL_YEAR"}
            and current_container_durations
            and "FULL_YEAR" not in current_container_durations
        ) or (
            comparative_action_durations == {"FULL_YEAR"}
            and "FULL_YEAR" not in current_action_durations
            and root is not None
        ):
            excluded_noncomparable_duration_control = comparative
            comparative = None
            rule = (
                "CURRENT_DURATION_MOVEMENT_ONLY_NONCOMPARABLE_ANNUAL_"
                "ROLLFORWARD_IS_SOURCE_ONLY"
            )
        elif both_lanes_layout_bound:
            rule = (
                "BOTH_LANES_INDEPENDENT_EXACT_SAME_SECTION_LAYOUT_PERIOD_"
                "BINDINGS_SUPERSEDE_NONCOMPARABLE_CONTAINER_HEURISTIC"
            )
    period_compatibility_axis = []
    primary_root_duration_accepted = root is not None
    excluded_period_controls: list[dict[str, Any]] = []
    if root is not None:
        for semantic_role, observation in (
            ("CURRENT_PERIOD", current),
            ("COMPARATIVE_PERIOD", comparative),
        ):
            if observation is None:
                continue
            detail_scope = _family37_observation_period_scope_v1(
                observation,
                semantic_role=semantic_role,
            )
            root_scope = root.get("period_scope_by_lane", {}).get(semantic_role)
            if type(root_scope) is not dict:
                allowed, compatibility = True, "PRIMARY_DURATION_SCOPE_UNSPECIFIED"
            else:
                allowed, compatibility = _family37_period_compatibility_v1(
                    detail_scope, root_scope
                )
            period_compatibility_axis.append(
                {
                    "accepted": allowed,
                    "compatibility": compatibility,
                    "detail_scope": detail_scope,
                    "root_scope": canonical_clone_v1(root_scope),
                    "semantic_role": semantic_role,
                }
            )
            if compatibility == "PRIMARY_ROOT_DURATION_UNPROVEN_DETAIL_ONLY":
                primary_root_duration_accepted = False
            if not allowed:
                excluded_period_controls.append(
                    {
                        "observation": canonical_clone_v1(observation),
                        "reason": compatibility,
                        "semantic_role": semantic_role,
                    }
                )
                if semantic_role == "CURRENT_PERIOD":
                    current = None
                else:
                    comparative = None
        if excluded_period_controls:
            rule = (
                "EXACT_LANE_DURATION_COMPATIBILITY_REJECTS_ONLY_CONFLICTING_"
                "MOVEMENT_LANES"
            )
    else:
        for semantic_role, observation in (
            ("CURRENT_PERIOD", current),
            ("COMPARATIVE_PERIOD", comparative),
        ):
            if observation is None:
                continue
            detail_scope = _family37_observation_period_scope_v1(
                observation,
                semantic_role=semantic_role,
            )
            period_key = observation.get("period_key")
            lane_is_explicit = period_key == ["SEMANTIC_ROLE", semantic_role]
            allowed = bool(
                lane_is_explicit
                and _family37_supported_duration_scope_v1(detail_scope)
            )
            compatibility = (
                "DETAIL_EXACT_SCOPE_SELF_AUTHORIZED"
                if allowed
                else "DETAIL_WITHOUT_EXACT_SEMANTIC_LANE_DURATION_AUTHORITY"
            )
            period_compatibility_axis.append(
                {
                    "accepted": allowed,
                    "compatibility": compatibility,
                    "detail_scope": detail_scope,
                    "root_scope": None,
                    "semantic_role": semantic_role,
                }
            )
            if not allowed:
                excluded_period_controls.append(
                    {
                        "observation": canonical_clone_v1(observation),
                        "reason": compatibility,
                        "semantic_role": semantic_role,
                    }
                )
                if semantic_role == "CURRENT_PERIOD":
                    current = None
                else:
                    comparative = None
        if excluded_period_controls:
            rule = "DETAIL_ONLY_REQUIRES_EXACT_SEMANTIC_LANE_DURATION_AUTHORITY"
    if current is None and comparative is None:
        return None
    current_variant = (
        None
        if current is None
        else _choose_transposed_variant(
            current, root=root
        )
    )
    comparative_variant = (
        None
        if comparative is None
        else _choose_transposed_variant(
            comparative,
            root=root,
        )
    )
    if (current is not None and current_variant is None) or (
        comparative is not None and comparative_variant is None
    ):
        return None
    current = (
        None
        if current is None
        else {
            **canonical_clone_v1(current),
            **current_variant,
        }
    )
    comparative = (
        None
        if comparative is None
        else {**canonical_clone_v1(comparative), **comparative_variant}
    )
    units = {
        item
        for item in (
            current.get("canonical_unit") if current is not None else None,
            comparative.get("canonical_unit") if comparative is not None else None,
            root.get("canonical_unit") if root is not None else None,
        )
        if item is not None
    }
    if len(units) != 1:
        return None
    canonical_unit = next(iter(units))
    selected_action_axes = {
        (
            _action_region(item, action)["page_json_version_id"],
            _action_region(item, action)["section_id"],
            _action_region(item, action)["table_id"],
            action["row_ordinal"],
        )
        for item in (current, comparative)
        if item is not None
        for action in item["selected_actions"]
    }
    source_only_rows = []
    for observation in observations:
        for action in observation["all_actions"]:
            axis = (
                _action_region(observation, action)["page_json_version_id"],
                _action_region(observation, action)["section_id"],
                _action_region(observation, action)["table_id"],
                action["row_ordinal"],
            )
            if axis not in selected_action_axes:
                period_control = next(
                    (
                        item
                        for item in excluded_period_controls
                        if item["observation"].get("region")
                        == observation.get("region")
                        and item["observation"].get("period_key")
                        == observation.get("period_key")
                    ),
                    None,
                )
                source_only_rows.append(
                    {
                        "disposition": (
                            "DETAIL_LANE_REJECTED_BY_EXACT_DURATION_SCOPE_"
                            + period_control["reason"]
                            if period_control is not None
                            else "PRIOR_ANNUAL_POSITION_CONTROL_NOT_COMPARATIVE_DURATION"
                            if observation is excluded_position_control
                            else "NONCOMPARABLE_ANNUAL_ROLLFORWARD_NOT_COMPARATIVE_DURATION"
                            if observation is excluded_noncomparable_duration_control
                            else "MOVEMENT_ACTION_EXCLUDED_BY_DIRECT_PRIMARY_EXPENSE_PRESENTATION"
                        ),
                        "region": canonical_clone_v1(
                            _action_region(observation, action)
                        ),
                        "row_ordinal": action["row_ordinal"],
                    }
                )
    material = {
        "canonical_unit": canonical_unit,
        "current": current,
        "comparative": comparative,
        "excluded_noncomparable_duration_control": (
            excluded_noncomparable_duration_control
        ),
        "excluded_period_controls": excluded_period_controls,
        "excluded_position_control": excluded_position_control,
        "format_version": ADAPTER_FORMAT_VERSION,
        "layout_period_binding_receipt_ids": (
            layout_period_binding_receipt_ids
            if both_lanes_layout_bound
            else []
        ),
        "rule": rule,
        "period_compatibility_axis": period_compatibility_axis,
        "primary_root_duration_accepted": primary_root_duration_accepted,
        "source_only_rows": source_only_rows,
    }
    return {
        **material,
        "receipt_id": "gjcrpefav1:transposed:" + canonical_json_sha256_v1(material),
    }


def _primary_root_region(
    observation: Mapping[str, Any],
    *,
    document: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    locator = observation["locator"]
    axis = next(
        (
            item
            for item in selected_page_axis
            if item.get("document_ordinal") == document["document_ordinal"]
            and item.get("page_json_version_id") == locator["page_json_version_id"]
        ),
        None,
    )
    if axis is None:
        raise _error("Family-37 primary-root selected page is absent")
    return _region(
        document=document,
        page_axis=axis,
        section_ordinal=int(locator["section_id"][1:]),
        table_ordinal=int(locator["table_id"][1:]),
        component_roles=[],
    )


def _family37_unique_regions_v1(
    regions: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    unique: dict[tuple[str, str, str], dict[str, Any]] = {}
    for source_region in regions:
        region = canonical_clone_v1(source_region)
        identity = (
            region["page_json_version_id"],
            region["section_id"],
            region["table_id"],
        )
        existing = unique.get(identity)
        if existing is None:
            unique[identity] = region
        else:
            roles = sorted(
                set(existing.get("component_roles", []))
                | set(region.get("component_roles", []))
            )
            existing["component_roles"] = roles
    result = sorted(
        unique.values(),
        key=lambda item: (
            item["selected_page_ordinal"],
            item["physical_page"],
            int(item["section_id"][1:]),
            int(item["table_id"][1:]),
        ),
    )
    for fragment_ordinal, region in enumerate(result, start=1):
        region["fragment_ordinal"] = fragment_ordinal
    return result


def _family37_movement_continuation_rejections_v1(
    *,
    observations: Sequence[Mapping[str, Any]],
    pages: Mapping[str, dict[str, Any]],
    structural_projection_receipts: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    accepted = {
        (
            locator["page_json_version_id"],
            locator["section_id"],
            locator["table_id"],
        )
        for receipt in structural_projection_receipts
        if type(receipt) is dict
        and type(receipt.get("receipt_id")) is str
        and receipt["receipt_id"].startswith("gjcrpefav1:continuation-projection:")
        for locator in (
            receipt.get("previous_locator"),
            receipt.get("current_locator"),
        )
        if type(locator) is dict
    }
    regions = _family37_unique_regions_v1(
        [
            region
            for observation in observations
            for region in _observation_regions(observation)
        ]
    )
    rejected = []
    for region in regions:
        _section, table = _source_table(
            pages[region["page_json_version_id"]],
            section_id=region["section_id"],
            table_id=region["table_id"],
        )
        marker = table.get("continuation")
        identity = (
            region["page_json_version_id"],
            region["section_id"],
            region["table_id"],
        )
        if marker != "NONE" and identity not in accepted:
            rejected.append(
                {
                    "continuation": marker,
                    "reason": "F37_SOURCE_CONTINUATION_NOT_CLOSED",
                    "region": canonical_clone_v1(region),
                }
            )
    return rejected


def _family37_all_observations_conflict_with_root_period_v1(
    *,
    observations: Sequence[Mapping[str, Any]],
    root: Mapping[str, Any] | None,
) -> bool:
    authority_axis = _family37_period_authority_axis_v1(
        observations=observations,
        root=root,
    )
    return bool(authority_axis and not any(item["accepted"] for item in authority_axis))


def _family37_period_authority_axis_v1(
    *,
    observations: Sequence[Mapping[str, Any]],
    root: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """Bind each assignable detail lane to an exact primary-period decision."""

    if root is None or not observations:
        return []
    root_scopes = root.get("period_scope_by_lane")
    if type(root_scopes) is not dict:
        return []
    assignments: list[tuple[str, Mapping[str, Any]]] = []
    for observation in observations:
        period_key = observation.get("period_key")
        lane = None
        if period_key == ["SEMANTIC_ROLE", "CURRENT_PERIOD"]:
            lane = "CURRENT_PERIOD"
        elif period_key == ["SEMANTIC_ROLE", "COMPARATIVE_PERIOD"]:
            lane = "COMPARATIVE_PERIOD"
        else:
            lane = _family37_exact_root_lane_for_observation_v1(
                observation, root
            )
            # A fully scoped observation that disagrees on one endpoint must
            # still appear as rejected exact source authority.  Attribute it
            # only when its visible calendar year uniquely identifies one
            # exact root lane; this never makes the observation acceptable and
            # never relies on year ordering or table position.
            if lane is None and _family37_root_has_exact_period_axis_v1(root):
                unassigned_scope = _family37_period_scope_v1(
                    observation.get("duration_surface_axis", []),
                    semantic_role="UNASSIGNED",
                )
                observation_year = unassigned_scope.get("calendar_year")
                matching_lanes = [
                    role
                    for role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD")
                    if observation_year is not None
                    and root_scopes[role].get("calendar_year") == observation_year
                ]
                if len(matching_lanes) == 1:
                    lane = matching_lanes[0]
        if lane is not None:
            assignments.append((lane, observation))
    if not assignments:
        return []
    result = []
    for lane, observation in assignments:
        root_scope = root_scopes.get(lane)
        if type(root_scope) is not dict:
            continue
        detail_scope = _family37_observation_period_scope_v1(
            observation, semantic_role=lane
        )
        allowed, reason = _family37_period_compatibility_v1(
            detail_scope, root_scope
        )
        material = {
            "accepted": allowed,
            "compatibility": reason,
            "detail_scope": detail_scope,
            "observation_regions": _family37_unique_regions_v1(
                _observation_regions(observation)
            ),
            "period_key": canonical_clone_v1(observation.get("period_key")),
            "root_locator": canonical_clone_v1(root["locator"]),
            "root_scope": canonical_clone_v1(root_scope),
            "semantic_lane": lane,
        }
        result.append(
            {
                **material,
                "period_authority_id": "gjcrpefav1:period-authority:"
                + canonical_json_sha256_v1(material),
            }
        )
    result.sort(
        key=lambda item: (
            item["observation_regions"][0]["selected_page_ordinal"],
            item["observation_regions"][0]["physical_page"],
            int(item["observation_regions"][0]["section_id"][1:]),
            int(item["observation_regions"][0]["table_id"][1:]),
            item["semantic_lane"],
        )
    )
    return result


def _family37_normal_breakdown_authorized_roles_v1(
    *,
    regions: Sequence[Mapping[str, Any]],
    pages: Mapping[str, dict[str, Any]],
    transposed_receipt: Mapping[str, Any] | None,
    compiled_specs: Mapping[str, Any],
) -> set[str]:
    """Authorize child movement cells only after exact direct-lane reconciliation."""

    if not regions or type(transposed_receipt) is not dict:
        return set()
    query_receipt = (
        build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
    )
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=regions,
        page_json_by_version=pages,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if candidate.get("status") != READY:
        return set()
    by_role = {
        mapping.get("role"): mapping
        for mapping in candidate.get("mappings", [])
        if type(mapping) is dict and type(mapping.get("role")) is str
    }
    customer = by_role.get("CUSTOMER_PROVISION")
    if type(customer) is not dict or any(
        role in by_role for role in ("CUSTOMER_GENERAL", "CUSTOMER_SPECIFIC")
    ):
        return set()
    direct_values = customer.get("values")
    if type(direct_values) is not list or len(direct_values) != 2:
        return set()
    if transposed_receipt.get("canonical_unit") != customer.get("unit"):
        return set()
    observed_lane_count = 0
    for lane, key in enumerate(("current", "comparative")):
        observation = transposed_receipt.get(key)
        if observation is None:
            continue
        if type(observation) is not dict:
            return set()
        observed = (
            observation.get("cells", {})
            .get("CUSTOMER_PROVISION", {})
            .get("coefficient")
        )
        direct = direct_values[lane].get("coefficient")
        if type(observed) is not int or type(direct) is not int or observed != direct:
            return set()
        observed_lane_count += 1
    return (
        {"CUSTOMER_GENERAL", "CUSTOMER_SPECIFIC"}
        if observed_lane_count
        else set()
    )


def _family37_document_plan_v1(
    *,
    document: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    source_pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Recompute the complete family-local source authority for one document."""

    ordered_pages = _family37_selected_document_pages_v1(
        document=document,
        selected_page_axis=selected_page_axis,
        source_pages=source_pages,
    )
    base_cluster = _family37_recomputed_base_cluster_v1(
        document=document,
        ordered_pages=ordered_pages,
        compiled_specs=compiled_specs,
    )
    repaired_pages, repair_receipts = _apply_document_repairs(
        pages=source_pages,
        source_sha256=document["source_sha256"],
        compiled_specs=compiled_specs,
    )
    page_identity_axis = _family37_page_identity_axis_v1(
        ordered_pages=ordered_pages,
        repaired_pages=repaired_pages,
    )
    pages = {
        page_axis["page_json_version_id"]: canonical_clone_v1(
            repaired_pages[page_axis["page_json_version_id"]]
        )
        for page_axis, _page in ordered_pages
    }
    structural_projection_receipts = _project_shared_duration_header_prefixes(
        pages
    )
    structural_projection_receipts.extend(
        _project_family37_document_unit_consensus_v1(
            pages,
            compiled_specs=compiled_specs,
        )
    )
    structural_projection_receipts.extend(
        _project_customer_adjacent_continuations(
            pages,
            selected_page_axis=selected_page_axis,
            document_ordinal=document["document_ordinal"],
            compiled_specs=compiled_specs,
        )
    )
    structural_projection_receipts.extend(
        _project_family37_same_section_period_layouts_v1(
            pages,
            selected_page_axis=selected_page_axis,
            document_ordinal=document["document_ordinal"],
            compiled_specs=compiled_specs,
        )
    )
    normal_records = _family37_normal_fragment_inventory_v1(
        document=document,
        selected_page_axis=selected_page_axis,
        pages=pages,
        compiled_specs=compiled_specs,
    )
    normal_groups, normal_rejections = _family37_normal_candidate_groups_v1(
        normal_records
    )
    positive_normal_rejections = [
        item for item in normal_rejections if item.get("positive_owner") is True
    ]
    transposed_observations = _customer_transposed_observations(
        document=document,
        selected_page_axis=selected_page_axis,
        pages=pages,
        compiled_specs=compiled_specs,
    )
    movement_rejections = _family37_movement_continuation_rejections_v1(
        observations=transposed_observations,
        pages=pages,
        structural_projection_receipts=structural_projection_receipts,
    )
    roots = _primary_root_observations(
        pages=pages,
        selected_page_axis=selected_page_axis,
        document_ordinal=document["document_ordinal"],
        compiled_specs=compiled_specs,
    )
    roots = _primary_roots_compatible_with_observations(
        roots, transposed_observations
    )
    transposed_receipt = _transposed_detail_receipt(
        document=document,
        selected_page_axis=selected_page_axis,
        pages=pages,
        compiled_specs=compiled_specs,
    )

    decision = NOT_OBSERVED
    query_kind = "NO_POSITIVE_F37_OWNER"
    blocking_reasons: list[str] = []
    accepted_regions: list[dict[str, Any]] = []
    split_receipts: list[dict[str, Any]] = []

    if len(normal_groups) == 1:
        if positive_normal_rejections or movement_rejections:
            blocking_reasons.append("F37_SOURCE_CONTINUATION_NOT_CLOSED")
        else:
            accepted_regions, split_receipts = _split_duplicate_other_rows(
                pages=pages,
                regions=normal_groups[0],
                compiled_specs=compiled_specs,
            )
            decision = READY
            query_kind = (
                "NORMAL_TWO_PERIOD_CLOSED_CONTINUATION"
                if len(accepted_regions) > 1
                else "NORMAL_TWO_PERIOD_SOURCE_TABLE"
            )
    elif len(normal_groups) > 1:
        blocking_reasons.append("F37_MULTIPLE_NORMAL_SOURCE_POPULATIONS")

    if decision != READY and not blocking_reasons:
        if transposed_receipt is not None:
            accepted_roots = (
                roots
                if transposed_receipt.get("primary_root_duration_accepted") is True
                else []
            )
            detail_axis = [
                item
                for item in (
                    transposed_receipt.get("current"),
                    transposed_receipt.get("comparative"),
                )
                if type(item) is dict
            ]
            accepted_regions = [
                region for item in detail_axis for region in _observation_regions(item)
            ]
            if len(accepted_roots) == 1:
                accepted_regions.append(
                    _primary_root_region(
                        accepted_roots[0],
                        document=document,
                        selected_page_axis=selected_page_axis,
                    )
                )
            if movement_rejections and any(
                (
                    region["page_json_version_id"],
                    region["section_id"],
                    region["table_id"],
                )
                in {
                    (
                        rejected["region"]["page_json_version_id"],
                        rejected["region"]["section_id"],
                        rejected["region"]["table_id"],
                    )
                    for rejected in movement_rejections
                }
                for region in accepted_regions
            ):
                accepted_regions = []
                blocking_reasons.append("F37_SOURCE_CONTINUATION_NOT_CLOSED")
            else:
                decision = READY
                query_kind = (
                    "TRANSPOSED_CUSTOMER_PROVISION_WITH_PRIMARY_ROOT"
                    if accepted_roots
                    else "TRANSPOSED_CUSTOMER_PROVISION_WITH_LOCAL_UNIT"
                )
        elif transposed_observations:
            blocking_reasons.append(
                "F37_DETAIL_PRIMARY_DURATION_SCOPE_CONFLICT"
                if len(roots) == 1
                and _family37_all_observations_conflict_with_root_period_v1(
                    observations=transposed_observations, root=roots[0]
                )
                else "F37_TRANSPOSED_PRESENTATION_NOT_UNIQUE"
            )
    positive_owner = bool(
        any(item.get("positive_owner") is True for item in normal_records)
        or transposed_observations
    )
    if decision != READY:
        if positive_normal_rejections or movement_rejections:
            blocking_reasons.append("F37_SOURCE_CONTINUATION_NOT_CLOSED")
        if positive_owner and not blocking_reasons:
            blocking_reasons.append(
                "F37_POSITIVE_OWNER_WITHOUT_SAFE_SEMANTIC_LANES"
            )
        if blocking_reasons:
            decision = UNRESOLVED
            query_kind = "POSITIVE_F37_OWNER_REJECTED_BY_SOURCE_AUTHORITY"
        elif repair_receipts:
            raise _error(
                "Family-37 authenticated repair did not select one family region"
            )

    accepted_regions = _family37_unique_regions_v1(accepted_regions)
    owned_regions = _family37_unique_regions_v1(
        [
            *(
                item["region"]
                for item in normal_records
                if item.get("positive_owner") is True
            ),
            *(
                region
                for observation in transposed_observations
                for region in _observation_regions(observation)
            ),
            *(
                _primary_root_region(
                    root,
                    document=document,
                    selected_page_axis=selected_page_axis,
                )
                for root in roots
                if transposed_observations
            ),
            *accepted_regions,
        ]
    )
    blocking_reasons = sorted(set(blocking_reasons))
    accepted_movement_roles: set[str] = set()
    if decision == READY:
        if query_kind.startswith("NORMAL_TWO_PERIOD"):
            accepted_movement_roles = _family37_normal_breakdown_authorized_roles_v1(
                regions=accepted_regions,
                pages=pages,
                transposed_receipt=transposed_receipt,
                compiled_specs=compiled_specs,
            )
        else:
            accepted_movement_roles = {
                "CUSTOMER_GENERAL",
                "CUSTOMER_PROVISION",
                "CUSTOMER_SPECIFIC",
            }
    accepted_source_cells, rejected_source_cells = (
        _family37_movement_source_cell_axes_v1(
            observations=transposed_observations,
            transposed_receipt=(transposed_receipt if decision == READY else None),
            accepted_roles=accepted_movement_roles,
            source_sha256=document["source_sha256"],
        )
    )
    period_authority_axis = _family37_period_authority_axis_v1(
        observations=transposed_observations,
        root=roots[0] if len(roots) == 1 else None,
    )
    authority_material = {
        "accepted_region_axis": accepted_regions if decision == READY else [],
        "accepted_movement_role_axis": sorted(accepted_movement_roles),
        "accepted_source_cell_axis": accepted_source_cells,
        "blocking_reason_axis": blocking_reasons,
        "decision": decision,
        "document": canonical_clone_v1(document),
        "format_version": "F37_EXACT_SOURCE_AUTHORITY_V1",
        "movement_continuation_rejection_axis": movement_rejections,
        "normal_continuation_rejection_axis": normal_rejections,
        "normal_owner_record_axis": normal_records,
        "owned_region_axis": owned_regions,
        "page_identity_axis": page_identity_axis,
        "period_authority_axis": period_authority_axis,
        "query_kind": query_kind,
        "rejected_source_cell_axis": rejected_source_cells,
        "repair_receipt_ids": sorted(
            item["receipt_id"] for item in repair_receipts
        ),
        "source_repair_spec_sha256": compiled_specs[
            "credit_risk_provision_expense_source_repair_spec_sha256"
        ],
        "structural_projection_receipt_ids": sorted(
            item["receipt_id"] for item in structural_projection_receipts
        ),
        "transposed_receipt": canonical_clone_v1(transposed_receipt),
    }
    source_authority_receipt = {
        **authority_material,
        "receipt_id": "gjcrpefav1:source-authority:"
        + canonical_json_sha256_v1(authority_material),
    }
    adapter_material = {
        "format_version": ADAPTER_FORMAT_VERSION,
        "query_kind": query_kind,
        "source_authority_receipt": source_authority_receipt,
        "source_repair_receipt_ids": [
            item["receipt_id"] for item in repair_receipts
        ],
        "split_receipts": split_receipts,
        "structural_projection_receipt_ids": [
            item["receipt_id"] for item in structural_projection_receipts
        ],
        **(
            {"transposed_receipt": transposed_receipt}
            if transposed_receipt is not None
            else {}
        ),
    }
    adapter_receipt = {
        **adapter_material,
        "receipt_id": "gjcrpefav1:query:"
        + canonical_json_sha256_v1(adapter_material),
    }
    return {
        "accepted_region_axis": accepted_regions if decision == READY else [],
        "adapter_receipt": adapter_receipt,
        "base_cluster": base_cluster,
        "blocking_reasons": blocking_reasons,
        "decision": decision,
        "owned_region_axis": owned_regions,
        "pages": pages,
        "repair_receipts": repair_receipts,
        "split_receipts": split_receipts,
        "structural_projection_receipts": structural_projection_receipts,
        "transposed_receipt": transposed_receipt,
    }


def _family37_cluster_from_plan_v1(plan: Mapping[str, Any]) -> dict[str, Any]:
    base_cluster = plan["base_cluster"]
    material = {
        key: canonical_clone_v1(value)
        for key, value in base_cluster.items()
        if key
        not in {
            "cluster_id",
            "component_regions",
            "owner_receipt",
            "reasons",
            "status",
            "credit_risk_provision_expense_query_adapter_receipt",
        }
    }
    decision = plan["decision"]
    material.update(
        {
            "component_regions": (
                canonical_clone_v1(plan["accepted_region_axis"])
                if decision == READY
                else []
            ),
            "credit_risk_provision_expense_query_adapter_receipt": canonical_clone_v1(
                plan["adapter_receipt"]
            ),
            "owner_receipt": (
                canonical_clone_v1(base_cluster.get("owner_receipt"))
                if decision == READY
                else None
            ),
            "reasons": (
                canonical_clone_v1(plan["blocking_reasons"])
                if decision == UNRESOLVED
                else []
            ),
            "status": decision,
        }
    )
    return {
        **material,
        "cluster_id": "gjmthfcv1:cluster:"
        + canonical_json_sha256_v1(material),
    }


def _validate_family37_cluster_against_plan_v1(
    cluster: Mapping[str, Any], plan: Mapping[str, Any]
) -> None:
    expected = _family37_cluster_from_plan_v1(plan)
    if not same_typed_json_v1(cluster, expected):
        raise _error("Family-37 source authority disposition drifted")


def build_gemini_json_credit_risk_provision_expense_indexed_query_evidence_v1(
    *,
    base_indexed_query_evidence: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Build indexed evidence from independently recomputed F37 authority."""

    base = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        base_indexed_query_evidence, compiled_specs=compiled_specs
    )
    clusters = []
    for disposition, document in zip(
        base["candidate_dispositions"],
        base["selected_document_axis"],
        strict=True,
    ):
        source_pages = page_json_by_document.get(document["document_ordinal"])
        if type(source_pages) is not dict:
            raise _error("Family-37 selected document page JSON is absent")
        plan = _family37_document_plan_v1(
            document=document,
            selected_page_axis=base["selected_page_axis"],
            source_pages=source_pages,
            compiled_specs=compiled_specs,
        )
        if not same_typed_json_v1(disposition["cluster"], plan["base_cluster"]):
            raise _error("Family-37 base indexed source authority drifted")
        clusters.append(_family37_cluster_from_plan_v1(plan))
    adapted = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=base["selected_document_axis"],
        selected_page_axis=base["selected_page_axis"],
        document_clusters=clusters,
        query_policy_sha256=canonical_json_sha256_v1(compiled_specs["query_policy"]),
    )
    return validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        adapted, compiled_specs=compiled_specs
    )


def _restore_split_source_refs(
    value: Any, split_receipts: Sequence[Mapping[str, Any]]
) -> None:
    by_axis = {}
    for receipt in split_receipts:
        locator = receipt["locator"]
        for change in receipt["changes"]:
            by_axis[
                (
                    locator["page_json_version_id"],
                    locator["section_id"],
                    locator["table_id"],
                    change["row_ordinal"],
                )
            ] = change["before_row_exact"]

    def walk(item: Any) -> None:
        if type(item) is dict:
            locator = item.get("locator")
            key = (
                locator.get("page_json_version_id"),
                locator.get("section_id"),
                locator.get("table_id"),
                item.get("row_ordinal"),
            ) if type(locator) is dict else None
            before = by_axis.get(key)
            if before is not None:
                if "label_exact" in item:
                    item["label_exact"] = before["label_exact"]
                if "hierarchy_path_exact" in item:
                    item["hierarchy_path_exact"] = canonical_clone_v1(
                        before["hierarchy_path_exact"]
                    )
            for child in item.values():
                walk(child)
        elif type(item) is list:
            for child in item:
                walk(child)

    walk(value)


def _reseal_restored_mapping_and_equation_ids(candidate: dict[str, Any]) -> None:
    """Bind content-addressed IDs to the final restored source references."""

    mappings = candidate.get("mappings")
    equations = candidate.get("closure_receipt", {}).get("equations")
    if type(mappings) is not list or type(equations) is not list:
        raise _error("Family-37 candidate content-addressed axes are invalid")
    for mapping in mappings:
        if type(mapping) is not dict or type(mapping.get("item_mapping_id")) is not str:
            raise _error("Family-37 item mapping identity is invalid")
        material = {
            key: value for key, value in mapping.items() if key != "item_mapping_id"
        }
        mapping["item_mapping_id"] = (
            "gjmthfmv1:item:" + canonical_json_sha256_v1(material)
        )
    for equation in equations:
        if type(equation) is not dict or type(equation.get("equation_id")) is not str:
            raise _error("Family-37 equation identity is invalid")
        prefix, separator, digest = equation["equation_id"].rpartition(":")
        if not separator or not _SHA256.fullmatch(digest):
            raise _error("Family-37 equation identity prefix is invalid")
        material = {
            key: value for key, value in equation.items() if key != "equation_id"
        }
        equation["equation_id"] = prefix + ":" + canonical_json_sha256_v1(material)


def _aggregate_customer_additional_component(
    candidate: dict[str, Any],
) -> dict[str, Any] | None:
    """Widen one visibly narrow customer component to its schema aggregate.

    Some disclosures print general, specific, and a separate margin-loan
    provision as three direct rows, but the schema has no standalone role for
    the third row.  Its direct alias is used only to keep the source frontier
    exhaustive.  When, and only when, both named customer components coexist,
    replace that narrow direct mapping with their exact three-row aggregate.
    """

    by_role = {
        mapping.get("role"): mapping
        for mapping in candidate.get("mappings", [])
        if type(mapping) is dict
    }
    customer = by_role.get("CUSTOMER_PROVISION")
    general = by_role.get("CUSTOMER_GENERAL")
    specific = by_role.get("CUSTOMER_SPECIFIC")
    if type(customer) is not dict:
        return None
    customer_refs = customer.get("source_refs")
    labels = {
        _normalized(source_ref.get("label_exact") or "")
        for source_ref in customer_refs
        if type(source_ref) is dict
    } if type(customer_refs) is list else set()
    is_narrow_component = bool(
        labels and labels <= _CUSTOMER_ADDITIONAL_COMPONENT_ALIASES
    )
    if not is_narrow_component:
        return None
    if type(general) is not dict or type(specific) is not dict:
        candidate["mappings"] = []
        candidate["reasons"] = sorted(
            set(candidate.get("reasons", []))
            | {"NARROW_CUSTOMER_PROVISION_COMPONENT_LACKS_GENERAL_SPECIFIC_FRONTIER"}
        )
        candidate["status"] = UNRESOLVED
        return {
            "rule": (
                "NARROW_CUSTOMER_COMPONENT_NEVER_MAPS_TO_BROAD_SCHEMA_ROLE_"
                "WITHOUT_VISIBLE_GENERAL_AND_SPECIFIC_COMPONENTS"
            ),
            "status": "FAILED_CLOSED_MISSING_COMPONENT_FRONTIER",
        }
    components = [general, specific, customer]
    if any(
        type(mapping.get("values")) is not list or len(mapping["values"]) != 2
        for mapping in components
    ):
        raise _error("Family-37 customer component mapping axis is invalid")
    values = []
    for lane in range(2):
        cells = [mapping["values"][lane] for mapping in components]
        coefficients = [cell.get("coefficient") for cell in cells]
        if any(coefficient is None for coefficient in coefficients):
            values.append(
                {
                    "coefficient": None,
                    "source_text": None,
                    "state": "DERIVED_INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL",
                }
            )
        elif all(type(coefficient) is int for coefficient in coefficients):
            values.append(
                {
                    "coefficient": sum(coefficients),
                    "source_text": None,
                    "state": "EXACT_VISIBLE_CUSTOMER_COMPONENT_SUM",
                }
            )
        else:
            raise _error("Family-37 customer component coefficient is invalid")
    source_refs = [
        canonical_clone_v1(source_ref)
        for mapping in components
        for source_ref in mapping["source_refs"]
    ]
    aggregate = _mapping(
        role="CUSTOMER_PROVISION",
        report_norm_id=customer["report_norm_id"],
        values=values,
        source_refs=source_refs,
        unit=customer["unit"],
        state=(
            "DECLARED_CUSTOMER_PROVISION_DERIVED_FROM_EXACT_VISIBLE_GENERAL_"
            "SPECIFIC_AND_ADDITIONAL_COMPONENTS"
        ),
    )
    candidate["mappings"] = [
        aggregate if mapping is customer else mapping
        for mapping in candidate["mappings"]
    ]
    material = {
        "component_roles": [
            "CUSTOMER_GENERAL",
            "CUSTOMER_SPECIFIC",
            "CUSTOMER_ADDITIONAL_DIRECT_SOURCE_COMPONENT",
        ],
        "result_role": "CUSTOMER_PROVISION",
        "rule": (
            "EXACT_VISIBLE_GENERAL_PLUS_SPECIFIC_PLUS_SEPARATE_MARGIN_LOAN_"
            "PROVISION_COMPONENT_PROJECTS_TO_BROAD_CUSTOMER_PROVISION_SCHEMA_ROLE"
        ),
        "source_refs": source_refs,
        "values": values,
    }
    return {
        **material,
        "receipt_id": "gjcrpefav1:customer-aggregate:"
        + canonical_json_sha256_v1(material),
        "status": "EXACT_VISIBLE_COMPONENT_FRONTIER_AGGREGATED",
    }


def _augment_normal_customer_breakdown(
    candidate: dict[str, Any],
    *,
    pages: Mapping[str, dict[str, Any]],
    selected_page_axis: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Keep an exact movement breakdown beside its direct customer expense row."""

    if candidate.get("status") != READY:
        return None
    mappings = candidate.get("mappings")
    if type(mappings) is not list:
        raise _error("Family-37 normal candidate mapping axis is invalid")
    by_role = {
        mapping.get("role"): mapping
        for mapping in mappings
        if type(mapping) is dict and type(mapping.get("role")) is str
    }
    customer = by_role.get("CUSTOMER_PROVISION")
    if type(customer) is not dict or any(
        role in by_role for role in ("CUSTOMER_GENERAL", "CUSTOMER_SPECIFIC")
    ):
        return None
    regions = candidate.get("component_regions")
    if type(regions) is not list or not regions:
        raise _error("Family-37 normal customer candidate has no source regions")
    first = regions[0]
    document = {
        key: first[key]
        for key in (
            "document_id",
            "document_ordinal",
            "source_logical_name",
            "source_sha256",
        )
    }
    receipt = _transposed_detail_receipt(
        document=document,
        selected_page_axis=selected_page_axis,
        pages=pages,
        compiled_specs=compiled_specs,
    )
    if type(receipt) is not dict or receipt.get("canonical_unit") != customer.get(
        "unit"
    ):
        return None
    direct_values = customer.get("values")
    if type(direct_values) is not list or len(direct_values) != 2:
        raise _error("Family-37 direct customer mapping has an invalid lane axis")
    observations = [receipt["current"], receipt.get("comparative")]
    observed_lane_count = 0
    for lane, observation in enumerate(observations):
        if observation is None:
            continue
        observed = observation.get("cells", {}).get("CUSTOMER_PROVISION", {}).get(
            "coefficient"
        )
        direct = direct_values[lane].get("coefficient")
        if type(observed) is not int or type(direct) is not int or observed != direct:
            return None
        observed_lane_count += 1
    if observed_lane_count == 0:
        return None

    added = []
    for role in ("CUSTOMER_GENERAL", "CUSTOMER_SPECIFIC"):
        values = []
        source_refs = []
        for observation in observations:
            if observation is None:
                values.append(
                    {
                        "coefficient": None,
                        "source_text": None,
                        "state": "UNOBSERVED_SOURCE_LANE",
                    }
                )
                continue
            values.append(canonical_clone_v1(observation["cells"][role]))
            source_refs.extend(
                _transposed_mapping_source_refs(observation, role=role)
            )
        if all(value.get("coefficient") is None for value in values):
            continue
        mapping = _mapping(
            role=role,
            report_norm_id=compiled_specs["bindings"][role],
            values=values,
            source_refs=source_refs,
            unit=customer["unit"],
            state=(
                "SOURCE_VISIBLE_CUSTOMER_MOVEMENT_BREAKDOWN_EXACTLY_"
                "RECONCILED_TO_DIRECT_CUSTOMER_EXPENSE"
            ),
        )
        mappings.append(mapping)
        added.append(canonical_clone_v1(mapping))
    if not added:
        return None
    material = {
        "added_mappings": added,
        "direct_customer_mapping_id": customer["item_mapping_id"],
        "observed_lane_count": observed_lane_count,
        "rule": (
            "SOURCE_VISIBLE_GENERAL_AND_SPECIFIC_MOVEMENT_COMPONENTS_MAP_ONLY_"
            "WHEN_THEIR_PRINTED_TOTAL_EQUALS_THE_DIRECT_CUSTOMER_EXPENSE_"
            "ON_EVERY_OBSERVED_DURATION_LANE"
        ),
        "transposed_receipt_id": receipt["receipt_id"],
    }
    return {
        **material,
        "receipt_id": "gjcrpefav1:normal-customer-breakdown:"
        + canonical_json_sha256_v1(material),
    }


def _bind_normal_source_visible_root(
    candidate: dict[str, Any],
    *,
    pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Use the one printed terminal total, never a duplicated role sum."""

    if candidate.get("status") != READY or not candidate.get("mappings"):
        return None
    regions = candidate.get("component_regions")
    if type(regions) is not list:
        raise _error("Family-37 normal candidate region axis is invalid")
    total = _target_total_observation(
        pages=pages, regions=regions, compiled_specs=compiled_specs
    )
    if total is None:
        candidate["mappings"] = []
        candidate["reasons"] = sorted(
            set(candidate.get("reasons", []))
            | {"UNIQUE_SOURCE_VISIBLE_TERMINAL_FAMILY_ROOT_NOT_PROVEN"}
        )
        candidate["status"] = UNRESOLVED
        return {
            "rule": "NORMAL_FAMILY37_REQUIRES_ONE_PRINTED_TERMINAL_TOTAL",
            "status": "FAILED_CLOSED_SOURCE_TOTAL_NOT_UNIQUE",
        }
    region = next(
        (
            item
            for item in regions
            if all(
                item[key] == total["locator"][key]
                for key in (
                    "page_json_version_id",
                    "physical_page",
                    "section_id",
                    "table_id",
                )
            )
        ),
        None,
    )
    if type(region) is not dict:
        raise _error("Family-37 source total region is absent")
    _section, table = _source_table(
        pages[region["page_json_version_id"]],
        section_id=region["section_id"],
        table_id=region["table_id"],
    )
    rows = table.get("rows")
    if type(rows) is not list or not 1 <= total["row_ordinal"] <= len(rows):
        raise _error("Family-37 source total row is invalid")
    units = {
        mapping.get("unit")
        for mapping in candidate["mappings"]
        if type(mapping) is dict
        and mapping.get("role") != "FAMILY_ROOT_TOTAL"
        and type(mapping.get("unit")) is str
    }
    if len(units) != 1:
        candidate["mappings"] = []
        candidate["reasons"] = sorted(
            set(candidate.get("reasons", []))
            | {"SOURCE_VISIBLE_ROOT_UNIT_AXIS_NOT_UNIQUE"}
        )
        candidate["status"] = UNRESOLVED
        return {
            "rule": "NORMAL_FAMILY37_SOURCE_TOTAL_REUSES_UNIQUE_MAPPING_UNIT",
            "status": "FAILED_CLOSED_UNIT_NOT_UNIQUE",
        }
    source_ref = _source_ref(
        region=region,
        row=rows[total["row_ordinal"] - 1],
        row_ordinal=total["row_ordinal"],
        money_ordinals=total["money_column_ordinals"],
    )
    root = _mapping(
        role="FAMILY_ROOT_TOTAL",
        report_norm_id=compiled_specs["schema"]["family_root_report_norm_id"],
        values=canonical_clone_v1(total["cells"]),
        source_refs=[source_ref],
        unit=next(iter(units)),
        state="SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_FROM_UNIQUE_TERMINAL_TABLE_TOTAL",
    )
    replaced = False
    output = []
    for mapping in candidate["mappings"]:
        if mapping.get("role") == "FAMILY_ROOT_TOTAL":
            if not replaced:
                output.append(root)
                replaced = True
        else:
            output.append(mapping)
    if not replaced:
        output.append(root)
    candidate["mappings"] = output
    candidate["closure_receipt"]["structural_root_receipt"] = {
        "emitted_mapping": True,
        "mapping_policy": "DIRECT_UNIQUE_SOURCE_VISIBLE_TERMINAL_TABLE_TOTAL",
        "report_norm_id": compiled_specs["schema"]["family_root_report_norm_id"],
        "role": compiled_specs["topology"]["parent"]["role"],
    }
    material = {
        "source_ref": source_ref,
        "values": canonical_clone_v1(total["cells"]),
        "rule": (
            "UNIQUE_PRINTED_TERMINAL_TOTAL_IS_FAMILY_ROOT_AND_VETOES_ANY_"
            "DUPLICATED_PARENT_CHILD_ROLE_SUM"
        ),
    }
    return {
        **material,
        "receipt_id": "gjcrpefav1:normal-root:"
        + canonical_json_sha256_v1(material),
        "status": "DIRECT_SOURCE_VISIBLE_ROOT_BOUND",
    }


def _reseal_candidate(
    candidate: dict[str, Any],
    *,
    pages: Mapping[str, dict[str, Any]],
    selected_page_axis: Sequence[Mapping[str, Any]],
    source_repair_receipts: Sequence[Mapping[str, Any]],
    split_receipts: Sequence[Mapping[str, Any]],
    structural_projection_receipts: Sequence[Mapping[str, Any]],
    unit_receipts: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    _restore_split_source_refs(candidate, split_receipts)
    normal_root_receipt = _bind_normal_source_visible_root(
        candidate, pages=pages, compiled_specs=compiled_specs
    )
    customer_aggregate_receipt = _aggregate_customer_additional_component(candidate)
    customer_breakdown_receipt = _augment_normal_customer_breakdown(
        candidate,
        pages=pages,
        selected_page_axis=selected_page_axis,
        compiled_specs=compiled_specs,
    )
    _reseal_restored_mapping_and_equation_ids(candidate)
    observation_audit = audit_source_observation_mapping_contract_v1(
        candidate.get("mappings", [])
    )
    if observation_audit["violation_count"]:
        candidate["mappings"] = []
        candidate["reasons"] = sorted(
            set(candidate.get("reasons", []))
            | {"SOURCE_OBSERVATION_MAPPING_CONTRACT_FAILED"}
        )
        candidate["status"] = UNRESOLVED
    first_region = candidate.get("component_regions", [None])[0]
    if type(first_region) is not dict:
        raise _error("Family-37 normal candidate lacks one source region")
    document = {
        key: first_region[key]
        for key in (
            "document_id",
            "document_ordinal",
            "source_logical_name",
            "source_sha256",
        )
    }
    movement_coverage = _movement_source_role_coverage(
        document=document,
        selected_page_axis=selected_page_axis,
        pages=pages,
        compiled_specs=compiled_specs,
        mappings=candidate.get("mappings", []),
        direct_expense_table_selected=True,
    )
    if movement_coverage["violation_count"]:
        candidate["mappings"] = []
        candidate["reasons"] = sorted(
            set(candidate.get("reasons", []))
            | {"SOURCE_ROLE_COVERAGE_CONTRACT_FAILED"}
        )
        candidate["status"] = UNRESOLVED
    material = {
        "adapter_format_version": ADAPTER_FORMAT_VERSION,
        "shared_engine_claim_boundary": SHARED_CLAIM_BOUNDARY,
        "source_observation_audit": observation_audit,
        "source_role_coverage": movement_coverage,
        "source_repair_receipts": canonical_clone_v1(list(source_repair_receipts)),
        "source_repair_spec_sha256": compiled_specs[
            "credit_risk_provision_expense_source_repair_spec_sha256"
        ],
        "split_receipts": canonical_clone_v1(list(split_receipts)),
        "structural_projection_receipts": canonical_clone_v1(
            list(structural_projection_receipts)
        ),
        "unit_corroboration_receipts": canonical_clone_v1(list(unit_receipts)),
        **(
            {"normal_root_receipt": normal_root_receipt}
            if normal_root_receipt is not None
            else {}
        ),
        **(
            {"customer_aggregate_receipt": customer_aggregate_receipt}
            if customer_aggregate_receipt is not None
            else {}
        ),
        **(
            {"customer_breakdown_receipt": customer_breakdown_receipt}
            if customer_breakdown_receipt is not None
            else {}
        ),
    }
    candidate["claim_boundary"] = CLAIM_BOUNDARY
    candidate["closure_receipt"]["credit_risk_provision_expense_adapter_receipt"] = {
        **material,
        "adapter_receipt_id": "gjcrpefav1:evaluation:"
        + canonical_json_sha256_v1(material),
    }
    candidate_material = {
        key: value for key, value in candidate.items() if key != "candidate_id"
    }
    candidate["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        candidate_material
    )
    return candidate


def _source_ref(
    *,
    region: Mapping[str, Any],
    row: Mapping[str, Any],
    row_ordinal: int,
    money_ordinals: list[int],
) -> dict[str, Any]:
    return {
        "hierarchy_path_exact": canonical_clone_v1(row["hierarchy_path_exact"]),
        "label_exact": row.get("label_exact"),
        "locator": canonical_clone_v1(region),
        "money_column_ordinals": canonical_clone_v1(money_ordinals),
        "row_id": f"r{row_ordinal}",
        "row_kind": row["row_kind"],
        "row_ordinal": row_ordinal,
    }


def _observation_regions(
    observation: Mapping[str, Any],
) -> list[dict[str, Any]]:
    regions = observation.get("regions")
    if type(regions) is list and regions:
        return canonical_clone_v1(regions)
    return [canonical_clone_v1(observation["region"])]


def _action_region(
    observation: Mapping[str, Any], action: Mapping[str, Any]
) -> Mapping[str, Any]:
    region = action.get("region")
    return region if type(region) is dict else observation["region"]


def _transposed_mapping_source_refs(
    observation: Mapping[str, Any], *, role: str
) -> list[dict[str, Any]]:
    if observation.get("source_layout_kind") != "SEPARATE_CUSTOMER_ROLE_TABLES":
        return [
            _source_ref(
                region=observation["region"],
                row=action["row"],
                row_ordinal=action["row_ordinal"],
                money_ordinals=_transposed_role_source_ordinals(
                    observation, role=role
                ),
            )
            for action in observation["selected_actions"]
        ]
    wanted = (
        {"CUSTOMER_GENERAL", "CUSTOMER_SPECIFIC"}
        if role == "CUSTOMER_PROVISION"
        else {role}
    )
    refs = []
    for action in observation["selected_actions"]:
        if action.get("source_role") not in wanted:
            continue
        refs.append(
            _source_ref(
                region=_action_region(observation, action),
                row=action["row"],
                row_ordinal=action["row_ordinal"],
                money_ordinals=[action["column_ordinal"]],
            )
        )
    if not refs:
        raise _error("Family-37 separate-role mapping has no source reference")
    return refs


def _transposed_role_source_ordinals(
    observation: Mapping[str, Any], *, role: str
) -> list[int]:
    role_axis = observation.get("role_axis")
    if type(role_axis) is not dict:
        raise _error("Family-37 transposed role axis is invalid")
    direct = role_axis.get(role)
    if type(direct) is int:
        return [direct]
    if role == "CUSTOMER_PROVISION":
        components = [
            role_axis.get("CUSTOMER_GENERAL"),
            role_axis.get("CUSTOMER_SPECIFIC"),
        ]
        if all(type(item) is int for item in components):
            return sorted(components)
    raise _error("Family-37 transposed role has no source-column frontier")


def _family37_observation_semantic_lanes_v1(
    observations: Sequence[Mapping[str, Any]],
    *,
    transposed_receipt: Mapping[str, Any] | None,
) -> dict[tuple[str, str, str, str], str]:
    result = {}

    def observation_key(item: Mapping[str, Any]) -> tuple[str, str, str, str]:
        region = item["region"]
        return (
            region["page_json_version_id"],
            region["section_id"],
            region["table_id"],
            canonical_json_sha256_v1(item.get("period_key")),
        )

    if type(transposed_receipt) is dict:
        for lane, key in (
            ("CURRENT_PERIOD", "current"),
            ("COMPARATIVE_PERIOD", "comparative"),
        ):
            observation = transposed_receipt.get(key)
            if type(observation) is dict:
                result[observation_key(observation)] = lane
        for excluded in transposed_receipt.get("excluded_period_controls", []):
            if type(excluded) is dict and type(excluded.get("observation")) is dict:
                result[observation_key(excluded["observation"])] = excluded.get(
                    "semantic_role", "UNRESOLVED_PERIOD_LANE"
                )
    for observation in observations:
        key = observation_key(observation)
        if key in result:
            continue
        period_key = observation.get("period_key")
        if period_key == ["SEMANTIC_ROLE", "CURRENT_PERIOD"]:
            result[key] = "CURRENT_PERIOD"
        elif period_key == ["SEMANTIC_ROLE", "COMPARATIVE_PERIOD"]:
            result[key] = "COMPARATIVE_PERIOD"
        else:
            result[key] = "UNRESOLVED_PERIOD_LANE"
    return result


def _family37_movement_source_cell_axes_v1(
    *,
    observations: Sequence[Mapping[str, Any]],
    transposed_receipt: Mapping[str, Any] | None,
    accepted_roles: set[str],
    source_sha256: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    lane_by_observation = _family37_observation_semantic_lanes_v1(
        observations, transposed_receipt=transposed_receipt
    )
    accepted_action_axes = set()
    if type(transposed_receipt) is dict:
        for observation in (
            transposed_receipt.get("current"),
            transposed_receipt.get("comparative"),
        ):
            if type(observation) is not dict:
                continue
            for action in observation.get("selected_actions", []):
                if type(action) is not dict:
                    continue
                region = _action_region(observation, action)
                accepted_action_axes.add(
                    (
                        region["page_json_version_id"],
                        region["section_id"],
                        region["table_id"],
                        action["row_ordinal"],
                        action["action_kind"],
                    )
                )

    accepted = []
    rejected = []
    for observation in observations:
        observation_region = observation["region"]
        observation_key = (
            observation_region["page_json_version_id"],
            observation_region["section_id"],
            observation_region["table_id"],
            canonical_json_sha256_v1(observation.get("period_key")),
        )
        semantic_lane = lane_by_observation[observation_key]
        for action in observation.get("all_actions", []):
            if type(action) is not dict:
                continue
            region = _action_region(observation, action)
            if observation.get("source_layout_kind") == "SEPARATE_CUSTOMER_ROLE_TABLES":
                role_cells = [
                    (
                        action["source_role"],
                        action["column_ordinal"],
                        action["source_cell"],
                    )
                ]
            else:
                role_cells = [
                    (role, column_ordinal, action["cells"][role])
                    for role, column_ordinal in observation["role_axis"].items()
                ]
            action_axis = (
                region["page_json_version_id"],
                region["section_id"],
                region["table_id"],
                action["row_ordinal"],
                action["action_kind"],
            )
            for role, column_ordinal, source_cell in role_cells:
                material = {
                    "action_kind": action["action_kind"],
                    "column_ordinal": column_ordinal,
                    "page_json_version_id": region["page_json_version_id"],
                    "physical_page": region["physical_page"],
                    "role": role,
                    "row_ordinal": action["row_ordinal"],
                    "section_id": region["section_id"],
                    "semantic_lane": semantic_lane,
                    "source_cell": canonical_clone_v1(source_cell),
                    "source_sha256": source_sha256,
                    "table_id": region["table_id"],
                }
                item = {
                    **material,
                    "source_authority_cell_id": "gjcrpefav1:source-cell:"
                    + canonical_json_sha256_v1(material),
                }
                (
                    accepted
                    if action_axis in accepted_action_axes and role in accepted_roles
                    else rejected
                ).append(item)
    def sort_key(item: Mapping[str, Any]) -> tuple[Any, ...]:
        return (
            item["physical_page"],
            int(item["section_id"][1:]),
            int(item["table_id"][1:]),
            item["row_ordinal"],
            item["column_ordinal"],
            item["semantic_lane"],
            item["role"],
            item["action_kind"],
        )
    accepted.sort(key=sort_key)
    rejected.sort(key=sort_key)
    return accepted, rejected


def _movement_source_role_coverage(
    *,
    document: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    mappings: Sequence[Mapping[str, Any]],
    direct_expense_table_selected: bool,
    source_authority_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    mapped_axes = {
        (
            source_ref["locator"]["page_json_version_id"],
            source_ref["locator"]["section_id"],
            source_ref["locator"]["table_id"],
            source_ref["row_ordinal"],
            column_ordinal,
            mapping.get("role"),
        )
        for mapping in mappings
        if type(mapping) is dict
        for source_ref in mapping.get("source_refs", [])
        if type(source_ref) is dict and type(source_ref.get("locator")) is dict
        for column_ordinal in source_ref.get("money_column_ordinals", [])
    }
    observations = _customer_transposed_observations(
        document=document,
        selected_page_axis=selected_page_axis,
        pages=pages,
        compiled_specs=compiled_specs,
    )
    lane_by_observation = _family37_observation_semantic_lanes_v1(
        observations,
        transposed_receipt=(
            source_authority_receipt.get("transposed_receipt")
            if type(source_authority_receipt) is dict
            else None
        ),
    )
    accepted_by_identity = {}
    rejected_by_identity = {}
    if type(source_authority_receipt) is dict:
        for item in source_authority_receipt.get("accepted_source_cell_axis", []):
            if type(item) is not dict:
                raise _error("Family-37 accepted source-cell authority is invalid")
            identity = (
                item.get("source_sha256"),
                item.get("page_json_version_id"),
                item.get("section_id"),
                item.get("table_id"),
                item.get("row_ordinal"),
                item.get("column_ordinal"),
                item.get("semantic_lane"),
                item.get("role"),
                item.get("action_kind"),
            )
            if identity in accepted_by_identity:
                raise _error("Family-37 accepted source-cell authority is duplicate")
            accepted_by_identity[identity] = item
        for item in source_authority_receipt.get("rejected_source_cell_axis", []):
            if type(item) is not dict:
                raise _error("Family-37 rejected source-cell authority is invalid")
            identity = (
                item.get("source_sha256"),
                item.get("page_json_version_id"),
                item.get("section_id"),
                item.get("table_id"),
                item.get("row_ordinal"),
                item.get("column_ordinal"),
                item.get("semantic_lane"),
                item.get("role"),
                item.get("action_kind"),
            )
            if identity in rejected_by_identity:
                raise _error("Family-37 rejected source-cell authority is duplicate")
            rejected_by_identity[identity] = item
    entries = []
    violations = []
    for observation in observations:
        observation_region = observation["region"]
        observation_identity = (
            observation_region["page_json_version_id"],
            observation_region["section_id"],
            observation_region["table_id"],
            canonical_json_sha256_v1(observation.get("period_key")),
        )
        semantic_lane = lane_by_observation[observation_identity]
        if observation.get("source_layout_kind") == "SEPARATE_CUSTOMER_ROLE_TABLES":
            source_cells = [
                (
                    action["source_role"],
                    action["column_ordinal"],
                    _action_region(observation, action),
                    action,
                    action["source_cell"],
                )
                for action in observation["all_actions"]
            ]
        else:
            source_cells = [
                (
                    role,
                    column_ordinal,
                    observation["region"],
                    action,
                    action["cells"][role],
                )
                for action in observation["all_actions"]
                for role, column_ordinal in observation["role_axis"].items()
            ]
        for role, column_ordinal, region, action, source_cell in source_cells:
            axis = (
                region["page_json_version_id"],
                region["section_id"],
                region["table_id"],
                action["row_ordinal"],
                column_ordinal,
                role,
            )
            mapped = axis in mapped_axes
            authority_identity = (
                document["source_sha256"],
                region["page_json_version_id"],
                region["section_id"],
                region["table_id"],
                action["row_ordinal"],
                column_ordinal,
                semantic_lane,
                role,
                action["action_kind"],
            )
            accepted_authority = accepted_by_identity.get(authority_identity)
            rejected_authority = rejected_by_identity.get(authority_identity)
            if mapped and accepted_authority is not None:
                disposition = "MAPPED_FROM_EXACT_SOURCE_OBSERVATION"
            elif mapped and source_authority_receipt is None:
                disposition = "MAPPED_FROM_EXACT_SOURCE_OBSERVATION"
            elif mapped and rejected_authority is not None:
                disposition = "VIOLATION_MAPPING_USES_REJECTED_SOURCE_CELL"
            elif mapped and type(source_authority_receipt) is dict:
                disposition = (
                    "VIOLATION_MAPPING_CELL_NOT_IN_ACCEPTED_SOURCE_AUTHORITY"
                )
            elif source_cell.get("coefficient") is None:
                disposition = "SOURCE_ONLY_BLANK_ROLE_OBSERVATION_NOT_MAPPED"
            elif accepted_authority is not None:
                disposition = "VIOLATION_ACCEPTED_SOURCE_CELL_NOT_MAPPED"
            elif rejected_authority is not None:
                disposition = (
                    "SOURCE_ONLY_MOVEMENT_ACTION_NOT_SELECTED_BY_EXACT_"
                    "DURATION_AND_PRIMARY_PRESENTATION"
                )
            elif (
                type(source_authority_receipt) is dict
            ):
                disposition = "VIOLATION_MOVEMENT_CELL_NOT_IN_EXACT_SOURCE_AUTHORITY"
            elif direct_expense_table_selected:
                disposition = (
                    "SOURCE_ONLY_CUSTOMER_ROLLFORWARD_ACTION_SUPERSEDED_BY_"
                    "DIRECT_CREDIT_RISK_EXPENSE_TABLE"
                )
            else:
                disposition = (
                    "SOURCE_ONLY_MOVEMENT_ACTION_NOT_SELECTED_BY_EXACT_"
                    "DURATION_AND_PRIMARY_PRESENTATION"
                )
            entry = {
                "action_kind": action["action_kind"],
                "column_ordinal": column_ordinal,
                "disposition": disposition,
                "locator": {
                    key: region[key]
                    for key in (
                        "page_json_version_id",
                        "physical_page",
                        "section_id",
                        "table_id",
                    )
                },
                "role": role,
                "row_ordinal": action["row_ordinal"],
                "semantic_lane": semantic_lane,
                "source_cell": canonical_clone_v1(source_cell),
                "source_label_exact": action["row"].get("label_exact"),
                "source_authority_cell_id": (
                    accepted_authority.get("source_authority_cell_id")
                    if type(accepted_authority) is dict
                    else rejected_authority.get("source_authority_cell_id")
                    if type(rejected_authority) is dict
                    else None
                ),
                "source_authority_disposition": (
                    "EXACT_ACCEPTED_SOURCE_CELL"
                    if type(accepted_authority) is dict
                    else "EXACT_REJECTED_SOURCE_ONLY_CELL"
                    if type(rejected_authority) is dict
                    else "NO_EXACT_SOURCE_AUTHORITY"
                ),
                "source_authority_receipt_id": (
                    source_authority_receipt.get("receipt_id")
                    if type(source_authority_receipt) is dict
                    else None
                ),
            }
            entries.append(entry)
            if disposition.startswith("VIOLATION_"):
                violations.append(canonical_clone_v1(entry))
    material = {
        "covered_observation_count": len(entries),
        "entries": entries,
        "format_version": SOURCE_COVERAGE_FORMAT_VERSION,
        "mapped_observation_count": sum(
            item["disposition"] == "MAPPED_FROM_EXACT_SOURCE_OBSERVATION"
            for item in entries
        ),
        "source_only_observation_count": sum(
            item["disposition"].startswith("SOURCE_ONLY_") for item in entries
        ),
        "violation_count": len(violations),
        "violations": violations,
    }
    return {
        **material,
        "receipt_id": "gjcrpefav1:coverage:"
        + canonical_json_sha256_v1(material),
    }


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


def _raw_family37_target_surface(
    *,
    row: Mapping[str, Any],
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Return a narrow raw target receipt independent of configured role hits."""

    label_exact = row.get("label_exact")
    if type(label_exact) is not str or not label_exact.strip():
        return None
    label = _normalized(label_exact)
    if _is_parent_label(label_exact, compiled_specs=compiled_specs):
        return {
            "kind": "EXACT_FAMILY_ROOT_SURFACE",
            "surface_exact": label_exact,
        }
    if "loi nhuan" in label and "truoc chi phi du phong" in label:
        return None
    action_markers = (
        "trich lap",
        "hoan nhap",
        "chi phi du phong",
        "bien dong du phong",
    )
    if not any(marker in label for marker in action_markers):
        return None
    context_exact = [
        label_exact,
        *(row.get("hierarchy_path_exact", []) or []),
        section.get("title_exact"),
        table.get("title_exact"),
        *(section.get("narratives_exact", []) or []),
    ]
    context = _normalized(
        " ".join(item for item in context_exact if type(item) is str)
    )
    population_markers = (
        "rui ro tin dung",
        "cho vay khach hang",
        "cho vay cac tctd",
        "cho vay tctd",
        "tien gui va cho vay cac tctd",
        "hoat dong mua no",
        "khoan mua no",
        "trai phieu dac biet vamc",
        "trai phieu dac biet do vamc",
        "cam ket ngoai bang",
        "no tiem an",
        "thu tin dung tra cham",
        "tai san co noi bang khac",
        "tai san co khac co rui ro",
    )
    if not any(marker in context for marker in population_markers):
        return None
    return {
        "context_exact": [
            item for item in context_exact if type(item) is str and item.strip()
        ],
        "kind": "FAMILY37_POPULATION_ACTION_SURFACE",
        "surface_exact": label_exact,
    }


def _balance_movement_control_table(table: Mapping[str, Any]) -> bool:
    rows = table.get("rows")
    surfaces = {
        _normalized(row.get("label_exact") or "")
        for row in (rows if type(rows) is list else [])
        if type(row) is dict
    }
    has_position = any(
        any(marker in surface for marker in ("so du dau", "so du cuoi"))
        for surface in surfaces
    )
    has_nonexpense_movement = any(
        any(marker in surface for marker in ("su dung du phong", "xu ly rui ro"))
        for surface in surfaces
    )
    return has_position or has_nonexpense_movement


def _secondary_family_root_source_only_disposition(
    *,
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    money_ordinals: Sequence[int],
) -> str | None:
    """Type exact-root controls whose source axis is not the Family-37 axis."""

    # More than two MONEY columns encode another dimension (for example
    # geographic/business segments, quarter plus year-to-date, or a regulatory
    # delta column).  Family 37 has exactly two duration lanes, so consuming
    # one of these rows would either collapse a visible axis or double-map the
    # same primary-statement total.
    if len(money_ordinals) > 2:
        return (
            "SECONDARY_MULTIDIMENSIONAL_OR_REGULATORY_FAMILY_ROOT_"
            "PRESENTATION_SOURCE_ONLY"
        )

    rows = table.get("rows")
    context = _normalized(
        " ".join(
            str(item or "")
            for item in (
                section.get("title_exact"),
                table.get("title_exact"),
                *(section.get("narratives_exact", []) or []),
                *(
                    row.get("label_exact")
                    for row in (rows if type(rows) is list else [])
                    if type(row) is dict
                ),
            )
        )
    )
    restructuring_markers = (
        "paccl",
        "phuong an co cau lai",
        "de an co cau lai",
        "chi phi thuc hien theo",
    )
    if any(marker in context for marker in restructuring_markers):
        return "SECONDARY_RESTRUCTURING_PLAN_SUBSET_FAMILY_ROOT_SOURCE_ONLY"
    return None


def build_credit_risk_provision_expense_source_row_coverage_receipt_v1(
    *,
    indexed_query_evidence: Mapping[str, Any],
    trials: Sequence[Mapping[str, Any]],
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
    fail_on_violation: bool = True,
) -> dict[str, Any]:
    """Classify every configured or raw Family-37 source row and fail closed."""

    indexed = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
    if (
        compiled_specs.get("topology", {}).get("family_id") != FAMILY_ID
        or type(trials) not in {list, tuple}
        or len(trials) != len(indexed["candidate_dispositions"])
    ):
        raise _error("Family-37 source-row coverage input is invalid")
    page_axis_by_document: dict[int, dict[str, dict[str, Any]]] = {}
    for item in indexed["selected_page_axis"]:
        page_axis_by_document.setdefault(item["document_ordinal"], {})[
            item["page_json_version_id"]
        ] = item
    mapped_rows: set[tuple[str, str, str, str, int]] = set()
    mapped_role_rows: set[tuple[str, str, str, str, int, str]] = set()
    for trial in trials:
        for mapping in trial.get("mappings", []):
            role = mapping.get("role")
            for source_ref in mapping.get("source_refs", []):
                locator = source_ref.get("locator", {})
                row_ordinal = source_ref.get("row_ordinal")
                if (
                    type(locator) is not dict
                    or type(row_ordinal) is not int
                    or type(locator.get("page_json_version_id")) is not str
                ):
                    raise _error("Family-37 mapped source-row locator is invalid")
                identity = _coverage_row_locator(
                    source_sha256=trial["source_sha256"],
                    page_json_version_id=locator["page_json_version_id"],
                    section_id=locator["section_id"],
                    table_id=locator["table_id"],
                    row_ordinal=row_ordinal,
                )
                mapped_rows.add(identity)
                if type(role) is str:
                    mapped_role_rows.add((*identity, role))

    source_rows: dict[str, dict[str, Any]] = {}
    raw_rows: dict[str, dict[str, Any]] = {}
    total_rows: dict[str, dict[str, Any]] = {}
    violations: dict[str, dict[str, Any]] = {}
    movement_entries: list[dict[str, Any]] = []
    validation_only = set(compiled_specs.get("validation_only_roles", []))
    bindings = compiled_specs["bindings"]
    for disposition, document, trial in zip(
        indexed["candidate_dispositions"],
        indexed["selected_document_axis"],
        trials,
        strict=True,
    ):
        document_ordinal = document["document_ordinal"]
        source_pages = page_json_by_document.get(document_ordinal)
        axes = page_axis_by_document.get(document_ordinal)
        if type(source_pages) is not dict or type(axes) is not dict:
            raise _error("Family-37 source-row coverage page frontier is absent")
        plan = _family37_document_plan_v1(
            document=document,
            selected_page_axis=indexed["selected_page_axis"],
            source_pages=source_pages,
            compiled_specs=compiled_specs,
        )
        cluster = disposition["cluster"]
        _validate_family37_cluster_against_plan_v1(cluster, plan)
        pages = plan["pages"]
        selected_tables = {
            (
                region["page_json_version_id"],
                region["section_id"],
                region["table_id"],
            )
            for region in cluster.get("component_regions", [])
        }
        query_kind = cluster.get(
            "credit_risk_provision_expense_query_adapter_receipt", {}
        ).get("query_kind")
        direct_selected = str(query_kind).startswith("NORMAL_TWO_PERIOD")
        movement = _movement_source_role_coverage(
            document=document,
            selected_page_axis=indexed["selected_page_axis"],
            pages=pages,
            compiled_specs=compiled_specs,
            mappings=trial.get("mappings", []),
            direct_expense_table_selected=direct_selected,
            source_authority_receipt=plan["adapter_receipt"][
                "source_authority_receipt"
            ],
        )
        if movement["violation_count"]:
            raise _error("Family-37 nested movement coverage is invalid")
        for entry in movement["entries"]:
            locator = entry["locator"]
            page = pages[locator["page_json_version_id"]]
            section, table = _source_table(
                page,
                section_id=locator["section_id"],
                table_id=locator["table_id"],
            )
            row = table["rows"][entry["row_ordinal"] - 1]
            full_entry = _coverage_source_row(
                coverage=entry["disposition"],
                document=document,
                page_axis=axes[locator["page_json_version_id"]],
                section=section,
                table=table,
                section_id=locator["section_id"],
                table_id=locator["table_id"],
                row=row,
                row_ordinal=entry["row_ordinal"],
                role=entry["role"],
                report_norm_id=bindings.get(entry["role"]),
                evidence={
                    "action_kind": entry["action_kind"],
                    "column_ordinal": entry["column_ordinal"],
                    "semantic_lane": entry["semantic_lane"],
                    "source_cell": entry["source_cell"],
                    "source_authority_cell_id": entry[
                        "source_authority_cell_id"
                    ],
                    "source_authority_disposition": entry[
                        "source_authority_disposition"
                    ],
                    "source_authority_receipt_id": entry[
                        "source_authority_receipt_id"
                    ],
                },
            )
            movement_entries.append(full_entry)
        movement_row_locators = {
            _coverage_row_locator(
                source_sha256=document["source_sha256"],
                page_json_version_id=entry["locator"]["page_json_version_id"],
                section_id=entry["locator"]["section_id"],
                table_id=entry["locator"]["table_id"],
                row_ordinal=entry["row_ordinal"],
            )
            for entry in movement["entries"]
        }
        for page_json_version_id, page in pages.items():
            page_axis = axes.get(page_json_version_id)
            if page_axis is None:
                raise _error("Family-37 source-row page axis is absent")
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
                    table_axis = (page_json_version_id, section_id, table_id)
                    classification = (
                        classify_gemini_json_multitable_hierarchical_table_v1(
                            page, section, table, compiled_specs=compiled_specs
                        )
                    )
                    money_ordinals = classification.get(
                        "money_column_ordinals", []
                    )
                    rows = table.get("rows")
                    if type(rows) is not list:
                        continue
                    hit_by_row: dict[int, list[str]] = {}
                    for hit in classification.get("role_hits", []):
                        if (
                            type(hit) is dict
                            and type(hit.get("row_ordinal")) is int
                            and type(hit.get("role")) is str
                        ):
                            hit_by_row.setdefault(hit["row_ordinal"], []).append(
                                hit["role"]
                            )
                    total_ordinals = {
                        item.get("row_ordinal")
                        for item in classification.get("total_rows", [])
                        if type(item) is dict
                        and type(item.get("row_ordinal")) is int
                    }
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
                        values = row.get("values_exact")
                        visible = bool(
                            type(values) is list
                            and any(
                                type(ordinal) is int
                                and ordinal <= len(values)
                                and values[ordinal - 1] is not None
                                for ordinal in money_ordinals
                            )
                        )
                        roles = sorted(set(hit_by_row.get(row_ordinal, [])))
                        for role in roles:
                            report_norm_id = bindings.get(role)
                            if identity in movement_row_locators:
                                coverage = "ACCOUNTED_CUSTOMER_MOVEMENT_SOURCE_ROW"
                            elif (*identity, role) in mapped_role_rows:
                                coverage = "MAPPED_EXACT_SOURCE_ROLE_ROW"
                            elif identity in mapped_rows:
                                coverage = "CONSUMED_BY_EXACT_SOURCE_DERIVATION"
                            elif not visible:
                                coverage = "BLANK_STRUCTURAL_ROLE_ROW_SOURCE_ONLY"
                            elif role in validation_only:
                                coverage = "DECLARED_VALIDATION_ONLY_SOURCE_ROW"
                            elif section.get("content_kind") == "PRIMARY_STATEMENT":
                                coverage = (
                                    "PRIMARY_STATEMENT_FAMILY_ROLE_CARRIER_SOURCE_ONLY"
                                )
                            elif table_axis in selected_tables:
                                coverage = "VIOLATION_UNMAPPED_SELECTED_SCHEMA_ROLE_ROW"
                            elif classification.get("typed_control_disposition") is not None:
                                coverage = "TYPED_NONFAMILY_CONTROL_SOURCE_ONLY"
                            elif (
                                classification.get("owner_visible") is True
                                and classification.get(
                                    "family_presence_anchor_visible"
                                )
                                is True
                            ):
                                coverage = "VIOLATION_UNSELECTED_EXPLICIT_OWNER_ROLE_ROW"
                            else:
                                coverage = (
                                    "OUTSIDE_DURATION_EXPENSE_OWNER_FENCE_SOURCE_ONLY"
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
                                    "family_presence_anchor_visible": classification.get(
                                        "family_presence_anchor_visible"
                                    ),
                                    "money_column_ordinals": canonical_clone_v1(
                                        money_ordinals
                                    ),
                                    "owner_visible": classification.get(
                                        "owner_visible"
                                    ),
                                    "table_selected": table_axis in selected_tables,
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
                            elif identity in mapped_rows:
                                coverage = "CONSUMED_BY_EXACT_SOURCE_DERIVATION"
                            elif not visible:
                                coverage = "BLANK_FAMILY_ROOT_HEADING_SOURCE_ONLY"
                            elif section.get("content_kind") == "PRIMARY_STATEMENT":
                                if trial.get("status") == UNRESOLVED:
                                    coverage = (
                                        "PRIMARY_STATEMENT_ROOT_CARRIER_WITH_TYPED_"
                                        "SOURCE_AMBIGUITY"
                                    )
                                elif trial.get("status") == NOT_OBSERVED:
                                    coverage = (
                                        "PRIMARY_STATEMENT_ROOT_CARRIER_ONLY_MISSING_"
                                        "DISCLOSURE_OWNER_PERIOD_OR_UNIT"
                                    )
                                else:
                                    coverage = (
                                        "CORROBORATING_PRIMARY_STATEMENT_ROOT_"
                                        "CARRIER_SOURCE_ONLY"
                                    )
                            elif table_axis in selected_tables:
                                coverage = "VIOLATION_UNMAPPED_SELECTED_FAMILY_ROOT_ROW"
                            else:
                                coverage = (
                                    _secondary_family_root_source_only_disposition(
                                        section=section,
                                        table=table,
                                        money_ordinals=money_ordinals,
                                    )
                                    or "VIOLATION_UNACCOUNTED_EXACT_FAMILY_ROOT_ROW"
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
                                role="CREDIT_RISK_PROVISION_EXPENSE",
                                report_norm_id=compiled_specs["schema"][
                                    "family_root_report_norm_id"
                                ],
                                evidence={"table_selected": table_axis in selected_tables},
                            )
                            item_id = canonical_json_sha256_v1(item)
                            source_rows.setdefault(item_id, item)
                            if coverage.startswith("VIOLATION_"):
                                violations.setdefault(item_id, item)
                        if direct_selected and table_axis in selected_tables and (
                            row_ordinal in total_ordinals
                        ):
                            if (*identity, "FAMILY_ROOT_TOTAL") in mapped_role_rows:
                                coverage = "MAPPED_EXACT_TERMINAL_FAMILY_TOTAL"
                            elif not visible:
                                coverage = "BLANK_STRUCTURAL_TERMINAL_TOTAL"
                            else:
                                coverage = "VIOLATION_UNMAPPED_VISIBLE_TERMINAL_TOTAL"
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
                                report_norm_id=compiled_specs["schema"][
                                    "family_root_report_norm_id"
                                ],
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
                        raw_target = _raw_family37_target_surface(
                            row=row,
                            section=section,
                            table=table,
                            compiled_specs=compiled_specs,
                        )
                        if raw_target is None:
                            continue
                        classified_here = bool(roles or root_surface)
                        if classified_here:
                            coverage = "ACCOUNTED_CONFIGURED_FAMILY_SOURCE_ROW"
                        elif identity in movement_row_locators:
                            coverage = "ACCOUNTED_CUSTOMER_MOVEMENT_SOURCE_ROW"
                        elif identity in mapped_rows:
                            coverage = "ACCOUNTED_MAPPED_SOURCE_ROW"
                        elif section.get("content_kind") == "PRIMARY_STATEMENT":
                            coverage = "PRIMARY_STATEMENT_TARGET_CARRIER_SOURCE_ONLY"
                        elif _balance_movement_control_table(table):
                            coverage = "BALANCE_ALLOWANCE_MOVEMENT_CONTROL_SOURCE_ONLY"
                        else:
                            lane_axis = _multitable_lane_axis(
                                section, table, compiled_specs=compiled_specs
                            )
                            explicit_duration_owner = bool(
                                lane_axis.get("complete") is True
                                and (
                                    classification.get("owner_visible") is True
                                    or "chi phi du phong rui ro"
                                    in _normalized(
                                        " ".join(
                                            item
                                            for item in (
                                                section.get("title_exact"),
                                                table.get("title_exact"),
                                            )
                                            if type(item) is str
                                        )
                                    )
                                )
                            )
                            if explicit_duration_owner and visible:
                                coverage = (
                                    "VIOLATION_UNCLASSIFIED_VISIBLE_FAMILY37_"
                                    "DURATION_ROW"
                                )
                            else:
                                coverage = (
                                    "OUTSIDE_EXPLICIT_DURATION_OWNER_FENCE_"
                                    "SOURCE_ONLY"
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
                            evidence=raw_target,
                        )
                        item_id = canonical_json_sha256_v1(item)
                        raw_rows.setdefault(item_id, item)
                        if coverage.startswith("VIOLATION_"):
                            violations.setdefault(item_id, item)

    source_row_axis = [source_rows[key] for key in sorted(source_rows)]
    raw_target_like_row_axis = [raw_rows[key] for key in sorted(raw_rows)]
    candidate_table_total_row_axis = [total_rows[key] for key in sorted(total_rows)]
    movement_entries.sort(key=canonical_json_sha256_v1)
    violation_axis = [violations[key] for key in sorted(violations)]

    def disposition_counts(axis: Sequence[Mapping[str, Any]]) -> dict[str, int]:
        return {
            disposition: sum(item["coverage"] == disposition for item in axis)
            for disposition in sorted({item["coverage"] for item in axis})
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
        "movement_cell_disposition_counts": {
            disposition: sum(
                item["coverage"] == disposition for item in movement_entries
            )
            for disposition in sorted(
                {item["coverage"] for item in movement_entries}
            )
        },
        "movement_cell_axis": movement_entries,
        "movement_cell_axis_sha256": canonical_json_sha256_v1(movement_entries),
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
        "receipt_id": "gjcrpefav1:source-row-coverage:"
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
            f"Family-37 source-row coverage has {len(violation_axis)} violation(s): "
            + preview
        )
    return receipt


def _mapping(
    *,
    role: str,
    report_norm_id: int,
    values: list[dict[str, Any]],
    source_refs: list[dict[str, Any]],
    unit: str,
    state: str,
) -> dict[str, Any]:
    material = {
        "report_norm_id": report_norm_id,
        "role": role,
        "row_id": source_refs[0]["row_id"] if len(source_refs) == 1 else "corroborated:" + role,
        "source_refs": canonical_clone_v1(source_refs),
        "state": state,
        "unit": unit,
        "values": canonical_clone_v1(values),
    }
    return {
        **material,
        "item_mapping_id": "gjmthfmv1:item:" + canonical_json_sha256_v1(material),
    }


def _transposed_candidate(
    *,
    regions: Sequence[Mapping[str, Any]],
    pages: Mapping[str, dict[str, Any]],
    selected_page_axis: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
    source_repair_receipts: Sequence[Mapping[str, Any]],
    structural_projection_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    first = regions[0]
    document = {
        key: first[key]
        for key in (
            "document_id",
            "document_ordinal",
            "source_logical_name",
            "source_sha256",
        )
    }
    receipt = _transposed_detail_receipt(
        document=document,
        selected_page_axis=selected_page_axis,
        pages=pages,
        compiled_specs=compiled_specs,
    )
    roots = _primary_root_observations(
        pages=pages,
        selected_page_axis=selected_page_axis,
        document_ordinal=first["document_ordinal"],
        compiled_specs=compiled_specs,
    )
    roots = _primary_roots_compatible_with_observations(
        roots,
        [
            item
            for item in (receipt.get("current"), receipt.get("comparative"))
            if type(item) is dict
        ]
        if type(receipt) is dict
        else [],
    )
    if (
        type(receipt) is dict
        and receipt.get("primary_root_duration_accepted") is not True
    ):
        roots = []
    if receipt is None or len(roots) > 1:
        raise _error("Family-37 transposed candidate source structure drifted")
    root = roots[0] if roots else None
    unit = receipt["canonical_unit"]
    mappings = []
    role_order = ["CUSTOMER_PROVISION", "CUSTOMER_GENERAL", "CUSTOMER_SPECIFIC"]
    for role in role_order:
        if receipt["current"] is None:
            values = [
                {
                    "coefficient": None,
                    "source_text": None,
                    "state": "UNOBSERVED_SOURCE_LANE",
                },
                canonical_clone_v1(receipt["comparative"]["cells"][role]),
            ]
            refs = _transposed_mapping_source_refs(
                receipt["comparative"], role=role
            )
            selected_variant = receipt["comparative"]["variant_kind"]
        else:
            values = [canonical_clone_v1(receipt["current"]["cells"][role])]
            refs = _transposed_mapping_source_refs(receipt["current"], role=role)
            selected_variant = receipt["current"]["variant_kind"]
        if receipt["current"] is not None and receipt["comparative"] is None:
            values.append(
                {
                    "coefficient": None,
                    "source_text": None,
                    "state": "UNOBSERVED_SOURCE_LANE",
                }
            )
        elif receipt["current"] is not None:
            values.append(canonical_clone_v1(receipt["comparative"]["cells"][role]))
            refs.extend(
                _transposed_mapping_source_refs(
                    receipt["comparative"], role=role
                )
            )
        if all(value.get("coefficient") is None for value in values):
            continue
        mappings.append(
            _mapping(
                role=role,
                report_norm_id=compiled_specs["bindings"][role],
                values=values,
                source_refs=refs,
                unit=unit,
                state=(
                    "SOURCE_VISIBLE_TRANSPOSED_CUSTOMER_PROVISION_ROLE_"
                    + selected_variant
                ),
            )
        )
    if root is not None:
        primary_region = next(
            region
            for region in regions
            if region["page_json_version_id"]
            == root["locator"]["page_json_version_id"]
            and region["section_id"] == root["locator"]["section_id"]
            and region["table_id"] == root["locator"]["table_id"]
        )
        mappings.append(
            _mapping(
                role="FAMILY_ROOT_TOTAL",
                report_norm_id=compiled_specs["schema"][
                    "family_root_report_norm_id"
                ],
                values=canonical_clone_v1(root["cells"]),
                source_refs=[
                    _source_ref(
                        region=primary_region,
                        row=root["row"],
                        row_ordinal=root["row_ordinal"],
                        money_ordinals=root["money_column_ordinals"],
                    )
                ],
                unit=unit,
                state="SOURCE_VISIBLE_PRIMARY_FAMILY_ROOT_TOTAL",
            )
        )
    observation_audit = audit_source_observation_mapping_contract_v1(mappings)
    movement_coverage = _movement_source_role_coverage(
        document=document,
        selected_page_axis=selected_page_axis,
        pages=pages,
        compiled_specs=compiled_specs,
        mappings=mappings,
        direct_expense_table_selected=False,
    )
    reasons = []
    if observation_audit["violation_count"]:
        reasons.append("SOURCE_OBSERVATION_MAPPING_CONTRACT_FAILED")
    if movement_coverage["violation_count"]:
        reasons.append("SOURCE_ROLE_COVERAGE_CONTRACT_FAILED")
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "closure_receipt": {
            "credit_risk_provision_expense_adapter_receipt": {
                "adapter_format_version": ADAPTER_FORMAT_VERSION,
                "source_observation_audit": observation_audit,
                "source_role_coverage": movement_coverage,
                "source_repair_receipts": canonical_clone_v1(
                    list(source_repair_receipts)
                ),
                "source_repair_spec_sha256": compiled_specs[
                    "credit_risk_provision_expense_source_repair_spec_sha256"
                ],
                "structural_projection_receipts": canonical_clone_v1(
                    list(structural_projection_receipts)
                ),
                "transposed_receipt": receipt,
            },
            "partial_role_observations": (
                ["CUSTOMER_PROVISION", "CUSTOMER_GENERAL", "CUSTOMER_SPECIFIC"]
                if receipt["current"] is None or receipt["comparative"] is None
                else []
            ),
            "query_receipt": canonical_clone_v1(query_receipt),
            "rule": (
                "EXACT_SOURCE_VISIBLE_TRANSPOSED_CUSTOMER_PROVISION_COMPONENTS_"
                "OPTIONAL_DIRECT_PRIMARY_FAMILY_ROOT_NO_BACKSOLVE"
            ),
            "source_only_unmapped_rows": canonical_clone_v1(
                receipt["source_only_rows"]
            ),
            "structural_root_receipt": {
                "emitted_mapping": root is not None,
                "mapping_policy": (
                    "DIRECT_PRIMARY_SOURCE_VISIBLE_FAMILY_ROOT"
                    if root is not None
                    else "OPTIONAL_ROOT_NOT_SOURCE_OBSERVED_NO_SYNTHESIS"
                ),
                "report_norm_id": compiled_specs["schema"]["family_root_report_norm_id"],
                "role": compiled_specs["topology"]["parent"]["role"],
            },
        },
        "component_regions": canonical_clone_v1(list(regions)),
        "document_id": first["document_id"],
        "family_id": FAMILY_ID,
        "mappings": [] if reasons else mappings,
        "page_json_version_id": first["page_json_version_id"],
        "physical_page": first["physical_page"],
        "reasons": reasons,
        "section_id": first["section_id"],
        "source_logical_name": first["source_logical_name"],
        "source_sha256": first["source_sha256"],
        "status": READY if not reasons else UNRESOLVED,
        "table_id": first["table_id"],
    }
    return {
        "candidate_id": "gjmthfcv1:candidate:" + canonical_json_sha256_v1(material),
        **material,
    }


def _ambiguous_transposed_candidate(
    *,
    regions: Sequence[Mapping[str, Any]],
    pages: Mapping[str, dict[str, Any]],
    selected_page_axis: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
    observations: Sequence[Mapping[str, Any]],
    source_repair_receipts: Sequence[Mapping[str, Any]],
    structural_projection_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    first = regions[0]
    document = {
        key: first[key]
        for key in (
            "document_id",
            "document_ordinal",
            "source_logical_name",
            "source_sha256",
        )
    }
    coverage = _movement_source_role_coverage(
        document=document,
        selected_page_axis=selected_page_axis,
        pages=pages,
        compiled_specs=compiled_specs,
        mappings=[],
        direct_expense_table_selected=False,
    )
    observation_audit = audit_source_observation_mapping_contract_v1([])
    reason = (
        "SOURCE_VISIBLE_TRANSPOSED_CUSTOMER_EXPENSE_DURATION_OR_"
        "GROSS_NET_PRESENTATION_AMBIGUOUS"
    )
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "closure_receipt": {
            "credit_risk_provision_expense_adapter_receipt": {
                "adapter_format_version": ADAPTER_FORMAT_VERSION,
                "ambiguous_transposed_observations": canonical_clone_v1(
                    list(observations)
                ),
                "source_observation_audit": observation_audit,
                "source_role_coverage": coverage,
                "source_repair_receipts": canonical_clone_v1(
                    list(source_repair_receipts)
                ),
                "source_repair_spec_sha256": compiled_specs[
                    "credit_risk_provision_expense_source_repair_spec_sha256"
                ],
                "structural_projection_receipts": canonical_clone_v1(
                    list(structural_projection_receipts)
                ),
            },
            "query_receipt": canonical_clone_v1(query_receipt),
            "rule": (
                "VISIBLE_CUSTOMER_MOVEMENT_ACTIONS_ARE_ACCOUNTED_BUT_NO_"
                "VALUE_IS_MAPPED_UNTIL_DURATION_AND_GROSS_NET_VARIANT_IS_UNIQUE"
            ),
            "structural_root_receipt": {
                "emitted_mapping": False,
                "mapping_policy": "AMBIGUITY_FAILS_CLOSED_WITH_NO_MAPPING",
                "report_norm_id": compiled_specs["schema"][
                    "family_root_report_norm_id"
                ],
                "role": compiled_specs["topology"]["parent"]["role"],
            },
        },
        "component_regions": canonical_clone_v1(list(regions)),
        "document_id": first["document_id"],
        "family_id": FAMILY_ID,
        "mappings": [],
        "page_json_version_id": first["page_json_version_id"],
        "physical_page": first["physical_page"],
        "reasons": [reason],
        "section_id": first["section_id"],
        "source_logical_name": first["source_logical_name"],
        "source_sha256": first["source_sha256"],
        "status": UNRESOLVED,
        "table_id": first["table_id"],
    }
    return {
        "candidate_id": "gjmthfcv1:candidate:" + canonical_json_sha256_v1(material),
        **material,
    }


def _evaluate_gemini_json_credit_risk_provision_expense_family_cluster_from_authorized_plan_v1(
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    selected_page_axis: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate one Family-37 cluster after exact private-clone adaptation."""

    if compiled_specs.get("topology", {}).get("family_id") != FAMILY_ID:
        raise _error("Family-37 adapter received another family")
    expected = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
    if type(query_receipt) is not dict or not same_typed_json_v1(query_receipt, expected):
        raise _error("Family-37 query receipt does not bind exact fragments")
    region_axis = expected["region_axis"]
    first = region_axis[0]
    pages, source_repair_receipts = _apply_document_repairs(
        pages=page_json_by_version,
        source_sha256=first["source_sha256"],
        compiled_specs=compiled_specs,
    )
    structural_projection_receipts = _project_shared_duration_header_prefixes(
        pages
    )
    structural_projection_receipts.extend(
        _project_family37_document_unit_consensus_v1(
            pages,
            compiled_specs=compiled_specs,
        )
    )
    structural_projection_receipts.extend(
        _project_customer_adjacent_continuations(
            pages,
            selected_page_axis=selected_page_axis,
            document_ordinal=first["document_ordinal"],
            compiled_specs=compiled_specs,
        )
    )
    structural_projection_receipts.extend(
        _project_family37_same_section_period_layouts_v1(
            pages,
            selected_page_axis=selected_page_axis,
            document_ordinal=first["document_ordinal"],
            compiled_specs=compiled_specs,
        )
    )
    document = {
        key: first[key]
        for key in (
            "document_id",
            "document_ordinal",
            "source_logical_name",
            "source_sha256",
        )
    }
    transposed_receipt = _transposed_detail_receipt(
        document=document,
        selected_page_axis=selected_page_axis,
        pages=pages,
        compiled_specs=compiled_specs,
    )
    transposed_observations = _customer_transposed_observations(
        document=document,
        selected_page_axis=selected_page_axis,
        pages=pages,
        compiled_specs=compiled_specs,
    )
    roots = _primary_root_observations(
        pages=pages,
        selected_page_axis=selected_page_axis,
        document_ordinal=first["document_ordinal"],
        compiled_specs=compiled_specs,
    )
    roots = _primary_roots_compatible_with_observations(
        roots, transposed_observations
    )
    transposed_axes = set()
    if transposed_receipt is not None:
        for observation in (
            transposed_receipt["current"],
            transposed_receipt["comparative"],
        ):
            if observation is not None:
                transposed_axes.update(
                    (
                        region["page_json_version_id"],
                        region["section_id"],
                        region["table_id"],
                    )
                    for region in _observation_regions(observation)
                )
        if (
            len(roots) == 1
            and transposed_receipt.get("primary_root_duration_accepted") is True
        ):
            transposed_axes.add(
                (
                    roots[0]["locator"]["page_json_version_id"],
                    roots[0]["locator"]["section_id"],
                    roots[0]["locator"]["table_id"],
                )
            )
    region_axes = {
        (
            region["page_json_version_id"],
            region["section_id"],
            region["table_id"],
        )
        for region in region_axis
    }
    if transposed_receipt is not None and region_axes == transposed_axes:
        return _transposed_candidate(
            regions=region_axis,
            pages=pages,
            selected_page_axis=selected_page_axis,
            compiled_specs=compiled_specs,
            query_receipt=query_receipt,
            source_repair_receipts=source_repair_receipts,
            structural_projection_receipts=structural_projection_receipts,
        )
    ambiguous_axes = {
        (region["page_json_version_id"], region["section_id"], region["table_id"])
        for observation in transposed_observations
        for region in _observation_regions(observation)
    }
    for root in roots:
        ambiguous_axes.add(
            (
                root["locator"]["page_json_version_id"],
                root["locator"]["section_id"],
                root["locator"]["table_id"],
            )
        )
    if (
        transposed_receipt is None
        and transposed_observations
        and region_axes == ambiguous_axes
    ):
        return _ambiguous_transposed_candidate(
            regions=region_axis,
            pages=pages,
            selected_page_axis=selected_page_axis,
            compiled_specs=compiled_specs,
            query_receipt=query_receipt,
            observations=transposed_observations,
            source_repair_receipts=source_repair_receipts,
            structural_projection_receipts=structural_projection_receipts,
        )
    adapted_regions, split_receipts = _split_duplicate_other_rows(
        pages=pages, regions=region_axis, compiled_specs=compiled_specs
    )
    if not same_typed_json_v1(adapted_regions, region_axis):
        raise _error("Family-37 split role axis drifted from indexed query evidence")
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=region_axis,
        page_json_by_version=pages,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    return _reseal_candidate(
        candidate,
        pages=pages,
        selected_page_axis=selected_page_axis,
        source_repair_receipts=source_repair_receipts,
        split_receipts=split_receipts,
        structural_projection_receipts=structural_projection_receipts,
        unit_receipts=[],
        compiled_specs=compiled_specs,
    )


def _bind_family37_candidate_source_authority_v1(
    candidate: dict[str, Any],
    *,
    plan: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    closure = candidate.get("closure_receipt")
    adapter = (
        closure.get("credit_risk_provision_expense_adapter_receipt")
        if type(closure) is dict
        else None
    )
    if type(adapter) is not dict:
        raise _error("Family-37 candidate adapter receipt is absent")
    material = {
        key: canonical_clone_v1(value)
        for key, value in adapter.items()
        if key != "adapter_receipt_id"
    }
    material["source_authority_receipt"] = canonical_clone_v1(
        plan["adapter_receipt"]["source_authority_receipt"]
    )
    regions = candidate.get("component_regions")
    if type(regions) is not list or not regions:
        raise _error("Family-37 candidate source regions are absent")
    first = regions[0]
    document = {
        key: first[key]
        for key in (
            "document_id",
            "document_ordinal",
            "source_logical_name",
            "source_sha256",
        )
    }
    source_authority = plan["adapter_receipt"]["source_authority_receipt"]
    material["source_role_coverage"] = _movement_source_role_coverage(
        document=document,
        selected_page_axis=selected_page_axis,
        pages=plan["pages"],
        compiled_specs=compiled_specs,
        mappings=candidate.get("mappings", []),
        direct_expense_table_selected=str(plan["adapter_receipt"]["query_kind"]).startswith(
            "NORMAL_TWO_PERIOD"
        ),
        source_authority_receipt=source_authority,
    )
    if material["source_role_coverage"]["violation_count"]:
        raise _error("Family-37 candidate exact source-cell coverage failed")
    closure["credit_risk_provision_expense_adapter_receipt"] = {
        **material,
        "adapter_receipt_id": "gjcrpefav1:evaluation:"
        + canonical_json_sha256_v1(material),
    }
    candidate_material = {
        key: value for key, value in candidate.items() if key != "candidate_id"
    }
    candidate["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        candidate_material
    )
    return candidate


def _family37_direct_unresolved_candidate_v1(
    *,
    regions: Sequence[Mapping[str, Any]],
    query_receipt: Mapping[str, Any],
    plan: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    first = regions[0]
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "closure_receipt": {
            "credit_risk_provision_expense_adapter_receipt": canonical_clone_v1(
                plan["adapter_receipt"]
            ),
            "query_receipt": canonical_clone_v1(query_receipt),
            "rule": (
                "POSITIVE_F37_OWNER_REJECTED_BY_EXACT_SOURCE_AUTHORITY_"
                "NO_MAPPING_NO_BACKSOLVE"
            ),
            "structural_root_receipt": {
                "emitted_mapping": False,
                "mapping_policy": (
                    "TYPED_SOURCE_AUTHORITY_FAILS_CLOSED_WITH_NO_MAPPING"
                ),
                "report_norm_id": compiled_specs["schema"][
                    "family_root_report_norm_id"
                ],
                "role": compiled_specs["topology"]["parent"]["role"],
            },
        },
        "component_regions": canonical_clone_v1(list(regions)),
        "document_id": first["document_id"],
        "family_id": FAMILY_ID,
        "mappings": [],
        "page_json_version_id": first["page_json_version_id"],
        "physical_page": first["physical_page"],
        "reasons": canonical_clone_v1(plan["blocking_reasons"]),
        "section_id": first["section_id"],
        "source_logical_name": first["source_logical_name"],
        "source_sha256": first["source_sha256"],
        "status": UNRESOLVED,
        "table_id": first["table_id"],
    }
    return {
        "candidate_id": "gjmthfcv1:candidate:"
        + canonical_json_sha256_v1(material),
        **material,
    }


def evaluate_gemini_json_credit_risk_provision_expense_family_cluster_v1(
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    selected_page_axis: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate only the exact population admitted by recomputed authority."""

    expected_query = (
        build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
    )
    if not same_typed_json_v1(query_receipt, expected_query):
        raise _error("Family-37 query receipt does not bind exact fragments")
    supplied_regions = expected_query["region_axis"]
    first = supplied_regions[0]
    document = {
        key: first[key]
        for key in (
            "document_id",
            "document_ordinal",
            "source_logical_name",
            "source_sha256",
        )
    }
    plan = _family37_document_plan_v1(
        document=document,
        selected_page_axis=selected_page_axis,
        source_pages=page_json_by_version,
        compiled_specs=compiled_specs,
    )
    if plan["decision"] == READY:
        if not same_typed_json_v1(
            supplied_regions, plan["accepted_region_axis"]
        ):
            raise _error(
                "Family-37 direct candidate regions drifted from source authority"
            )
        candidate = (
            _evaluate_gemini_json_credit_risk_provision_expense_family_cluster_from_authorized_plan_v1(
                regions=supplied_regions,
                page_json_by_version={
                    version_id: page_json_by_version[version_id]
                    for version_id in plan["pages"]
                },
                selected_page_axis=selected_page_axis,
                compiled_specs=compiled_specs,
                query_receipt=query_receipt,
            )
        )
        return _bind_family37_candidate_source_authority_v1(
            candidate,
            plan=plan,
            selected_page_axis=selected_page_axis,
            compiled_specs=compiled_specs,
        )
    if plan["decision"] == UNRESOLVED:
        if not same_typed_json_v1(supplied_regions, plan["owned_region_axis"]):
            raise _error(
                "Family-37 direct candidate regions drifted from source authority"
            )
        return _family37_direct_unresolved_candidate_v1(
            regions=supplied_regions,
            query_receipt=query_receipt,
            plan=plan,
            compiled_specs=compiled_specs,
        )
    raise _error("Family-37 direct candidate has no positive source owner")


def build_gemini_json_credit_risk_provision_expense_trials_v1(
    *,
    indexed_query_evidence: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Evaluate every accepted cluster while preserving exhaustive dispositions."""

    evidence = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
    page_axis_by_document: dict[int, list[dict[str, Any]]] = {}
    for page in evidence["selected_page_axis"]:
        page_axis_by_document.setdefault(page["document_ordinal"], []).append(page)
    trials = []
    for disposition in evidence["candidate_dispositions"]:
        cluster = disposition["cluster"]
        ordinal = disposition["document_ordinal"]
        source_pages = page_json_by_document.get(ordinal)
        if type(source_pages) is not dict:
            raise _error("Family-37 trial selected page JSON is absent")
        plan = _family37_document_plan_v1(
            document=evidence["selected_document_axis"][ordinal - 1],
            selected_page_axis=evidence["selected_page_axis"],
            source_pages=source_pages,
            compiled_specs=compiled_specs,
        )
        _validate_family37_cluster_against_plan_v1(cluster, plan)
        candidates = []
        mappings = []
        reasons = []
        selected_candidate_id = None
        status = disposition["disposition"]
        if status == READY:
            regions = cluster["component_regions"]
            candidate = evaluate_gemini_json_credit_risk_provision_expense_family_cluster_v1(
                regions=regions,
                page_json_by_version=source_pages,
                selected_page_axis=page_axis_by_document[ordinal],
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
            raise _error("Family-37 query disposition is invalid")
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


def validate_gemini_json_credit_risk_provision_expense_candidate_replay_v1(
    value: Any,
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    selected_page_axis: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    expected = evaluate_gemini_json_credit_risk_provision_expense_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        selected_page_axis=selected_page_axis,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if type(value) is not dict or not same_typed_json_v1(value, expected):
        raise _error("Family-37 candidate replay drifted")
    return expected


def validate_gemini_json_credit_risk_provision_expense_replay_v1(
    *,
    base_indexed_query_evidence: Any,
    indexed_query_evidence: Any,
    trials: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    replayed = build_gemini_json_credit_risk_provision_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base_indexed_query_evidence,
        page_json_by_document=page_json_by_document,
        compiled_specs=compiled_specs,
    )
    if not same_typed_json_v1(indexed_query_evidence, replayed):
        raise _error("Family-37 indexed query evidence replay drifted")
    expected = build_gemini_json_credit_risk_provision_expense_trials_v1(
        indexed_query_evidence=replayed,
        page_json_by_document=page_json_by_document,
        compiled_specs=compiled_specs,
    )
    if type(trials) is not list or not same_typed_json_v1(trials, expected):
        raise _error("Family-37 sweep replay drifted")
    return expected
