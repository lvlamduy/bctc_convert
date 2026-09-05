"""Family-37 source adapter for credit-risk provision expense disclosures.

The shared multi-table hierarchical engine remains the accounting and schema
mapping authority for ordinary two-period disclosures.  This module adds only
source-observable structure that the shared query cannot represent directly:

* exact PDF-authenticated repairs applied to a private JSON clone;
* exact same-document primary-statement unit corroboration for unitless notes;
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
    _classification_roles,
    _multitable_lane_axis,
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
    "AUTHENTICATED_PDF_VISIBLE_REPAIR_EXACT_SAME_DOCUMENT_PRIMARY_UNIT_"
    "CORROBORATION_STRUCTURAL_DUPLICATE_OTHER_ROLE_SPLIT_AND_TRANSPOSED_"
    "CUSTOMER_PROVISION_PRIVATE_CLONE_ONLY_NO_BLANK_ZERO_NO_BACKSOLVE_"
    "NO_BANK_FILE_YEAR_PAGE_NOTE_VALUE_ROUTING_PROPOSAL_ONLY_"
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
) -> list[dict[str, Any]]:
    """Carry exact customer role headers across an explicit adjacent continuation."""

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
                    or _transposed_role_axis(previous_table) is None
                    or _movement_owner_kind(
                        " ".join(
                            (
                                str(previous_section.get("title_exact") or ""),
                                str(previous_table.get("title_exact") or ""),
                            )
                        )
                    )
                    != "CUSTOMER"
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
        before_columns = canonical_clone_v1(current_table["columns"])
        current_table["columns"] = canonical_clone_v1(previous_table["columns"])
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
            "before_columns_exact": before_columns,
            "before_initial_hierarchy_paths_exact": before_hierarchy_paths,
            "before_section_title_exact": before_section_title,
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
                "CARRIES_IDENTICAL_ROLE_HEADERS_AND_OWNER"
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
                            "row": canonical_clone_v1(row),
                            "row_ordinal": row_ordinal,
                            "unit_receipt": canonical_clone_v1(unit),
                        }
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
        money_ordinals = classification.get("money_column_ordinals")
        rows = table.get("rows")
        if type(money_ordinals) is not list or len(money_ordinals) != 2 or type(rows) is not list:
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


def _bind_exact_primary_statement_unit(
    *,
    pages: dict[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    selected_page_axis: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    tables = []
    for region in regions:
        section, table = _source_table(
            pages[region["page_json_version_id"]],
            section_id=region["section_id"],
            table_id=region["table_id"],
        )
        if section.get("content_kind") == "PRIMARY_STATEMENT":
            continue
        tables.append((region, table))
    if not tables or any(table.get("unit_exact") is not None for _region, table in tables):
        return []
    target = _target_total_observation(
        pages=pages,
        regions=[region for region, _table in tables],
        compiled_specs=compiled_specs,
    )
    document_ordinals = {region.get("document_ordinal") for region, _table in tables}
    if target is None or len(document_ordinals) != 1:
        return []
    document_ordinal = next(iter(document_ordinals))
    if type(document_ordinal) is not int:
        return []
    roots = _primary_root_observations(
        pages=pages,
        selected_page_axis=selected_page_axis,
        document_ordinal=document_ordinal,
        compiled_specs=compiled_specs,
    )
    target_vector = [cell["coefficient"] for cell in target["cells"]]
    matches = []
    for root in roots:
        vector = [cell["coefficient"] for cell in root["cells"]]
        if vector == target_vector:
            match_kind = "EXACT_SIGNED_COEFFICIENT_VECTOR"
        elif [abs(item) for item in vector] == [abs(item) for item in target_vector]:
            match_kind = "EXACT_MAGNITUDE_VECTOR_WITH_SOURCE_PRESENTATION_SIGN_DIFFERENCE"
        else:
            continue
        matches.append({**canonical_clone_v1(root), "match_kind": match_kind})
    units = {item["canonical_unit"] for item in matches}
    if len(units) != 1:
        return []
    unit = next(iter(units))
    for _region, table in tables:
        table["unit_exact"] = _UNIT_SURFACE[unit]
    material = {
        "canonical_unit": unit,
        "matched_primary_roots": matches,
        "rule": (
            "UNITLESS_FAMILY37_NOTE_VISIBLE_TOTAL_EQUALS_SAME_DOCUMENT_"
            "PRIMARY_FAMILY_ROOT_BOTH_DURATION_LANES_EXACT_OR_EXACT_"
            "MAGNITUDE_SIGN_PRESENTATION_DIFFERENCE_NO_SCALE_INFERENCE"
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
        "target_unit_exact": _UNIT_SURFACE[unit],
    }
    return [
        {
            **material,
            "receipt_id": "gjcrpefav1:unit:" + canonical_json_sha256_v1(material),
        }
    ]


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


def _duration_signatures(value: Any) -> list[str]:
    surface = _normalized(
        " ".join(str(item or "") for item in value)
        if type(value) is list
        else str(value or "")
    )
    patterns = (
        ("THREE_MONTH", ("quy 1", "quy i ", "ba thang")),
        ("SIX_MONTH", ("quy 2", "quy ii ", "sau thang")),
        ("NINE_MONTH", ("quy 3", "quy iii ", "chin thang")),
        (
            "FULL_YEAR",
            (
                "quy 4",
                "quy iv ",
                "nam tai chinh",
                "trong nam",
                "cho nam ket thuc",
                "01/01/",
            ),
        ),
    )
    result = []
    for signature, markers in patterns:
        if any(marker in surface for marker in markers):
            result.append(signature)
    return result


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


def _customer_balance_unit_context(
    *,
    pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    ending_vectors = []
    primary_vectors = []
    for page_json_version_id, page in pages.items():
        for section_ordinal, section in enumerate(page.get("sections", []), start=1):
            if type(section) is not dict:
                continue
            for table_ordinal, table in enumerate(
                section.get("tables", []), start=1
            ):
                if type(table) is not dict:
                    continue
                locator = {
                    "page_json_version_id": page_json_version_id,
                    "section_id": f"s{section_ordinal}",
                    "table_id": f"t{table_ordinal}",
                }
                role_axis = _transposed_role_axis(table)
                if role_axis is not None:
                    table_endings = []
                    for row_ordinal, row in enumerate(
                        table.get("rows", []), start=1
                    ):
                        if (
                            type(row) is not dict
                            or "so du cuoi"
                            not in _normalized(row.get("label_exact") or "")
                        ):
                            continue
                        cells = _transposed_cells(row, role_axis=role_axis)
                        coefficient = (
                            cells.get("CUSTOMER_PROVISION", {}).get("coefficient")
                            if type(cells) is dict
                            else None
                        )
                        if type(coefficient) is int:
                            table_endings.append(
                                {
                                    "coefficient": coefficient,
                                    "locator": locator,
                                    "row_ordinal": row_ordinal,
                                }
                            )
                    if table_endings:
                        ending_vectors.append(table_endings)
                if (
                    page.get("status") != "PRIMARY_FINANCIAL_STATEMENT"
                    or section.get("content_kind") != "PRIMARY_STATEMENT"
                ):
                    continue
                # These are balance positions, not duration lanes.  Their
                # exact MONEY columns and local unit remain admissible unit
                # corroboration even when the duration compiler rejects the
                # position-style headers.
                money_ordinals = _money_column_ordinals(table)
                unit = _local_explicit_unit(
                    table,
                    compiled_specs=compiled_specs,
                    document_unit_context=None,
                )
                if len(money_ordinals) != 2 or unit is None:
                    continue
                for row_ordinal, row in enumerate(
                    table.get("rows", []), start=1
                ):
                    if type(row) is not dict:
                        continue
                    label = _without_leading_ordinal(
                        _normalized(row.get("label_exact") or "")
                    )
                    if "du phong rui ro cho vay khach hang" not in label:
                        continue
                    cells = _observed_cells(row, money_ordinals)
                    if cells is None:
                        continue
                    primary_vectors.append(
                        {
                            "canonical_unit": unit["canonical_unit"],
                            "coefficients": [
                                cell["coefficient"] for cell in cells
                            ],
                            "locator": locator,
                            "money_column_ordinals": canonical_clone_v1(
                                money_ordinals
                            ),
                            "row_ordinal": row_ordinal,
                            "unit_receipt": canonical_clone_v1(unit),
                        }
                    )
    matches = []
    for endings in ending_vectors:
        ending_coefficients = [item["coefficient"] for item in endings]
        for primary in primary_vectors:
            primary_coefficients = primary["coefficients"]
            matched_lane_count = 0
            for ending, primary_coefficient in zip(
                ending_coefficients, primary_coefficients, strict=False
            ):
                if abs(ending) != abs(primary_coefficient):
                    break
                matched_lane_count += 1
            # One exact same-document balance lane is sufficient to identify
            # the movement table's presentation unit.  The remaining balance
            # lane can legitimately differ by one reporting-unit quantum
            # because the primary statement is rounded while the note is not.
            # This receipt never chooses a period or a value; it only accepts
            # the unique explicit unit attached to an otherwise identical
            # customer-provision closing balance.
            if matched_lane_count >= 1:
                matches.append(
                    {
                        "canonical_unit": primary["canonical_unit"],
                        "ending_observations": canonical_clone_v1(endings),
                        "matched_lane_count": matched_lane_count,
                        "primary_observation": canonical_clone_v1(primary),
                    }
                )
    units = {item["canonical_unit"] for item in matches}
    if len(units) != 1:
        return None
    material = {
        "canonical_unit": next(iter(units)),
        "evidence": matches,
        "rule": (
            "CUSTOMER_PROVISION_MOVEMENT_VISIBLE_ENDING_GENERAL_AND_SPECIFIC_"
            "SUM_MATCHES_EXPLICIT_UNIT_PRIMARY_BALANCE_ALLOWANCE_LANES"
        ),
        "status": "UNIQUE",
    }
    return {
        **material,
        "evidence_axis_sha256": canonical_json_sha256_v1(matches),
    }


def _family_document_unit_context(
    *,
    pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    consensus = _document_unit_context_axis(pages, compiled_specs=compiled_specs)
    if consensus.get("status") == "UNIQUE":
        return consensus
    balance = _customer_balance_unit_context(
        pages=pages, compiled_specs=compiled_specs
    )
    return balance if balance is not None else consensus


def _customer_balance_position_observations(
    *,
    pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Return direct two-position customer allowance rows with explicit units."""

    observations = []
    for page_json_version_id, page in pages.items():
        if page.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
            continue
        for section_ordinal, section in enumerate(page.get("sections", []), start=1):
            if (
                type(section) is not dict
                or section.get("content_kind") != "PRIMARY_STATEMENT"
                or section.get("statement_type") == "INCOME_STATEMENT"
            ):
                continue
            for table_ordinal, table in enumerate(
                section.get("tables", []), start=1
            ):
                if type(table) is not dict:
                    continue
                money_ordinals = _money_column_ordinals(table)
                unit = _local_explicit_unit(
                    table,
                    compiled_specs=compiled_specs,
                    document_unit_context=None,
                )
                if len(money_ordinals) != 2 or unit is None:
                    continue
                for row_ordinal, row in enumerate(table.get("rows", []), start=1):
                    if type(row) is not dict:
                        continue
                    label = _without_leading_ordinal(
                        _normalized(row.get("label_exact") or "")
                    )
                    if "du phong rui ro cho vay khach hang" not in label:
                        continue
                    cells = _observed_cells(row, money_ordinals)
                    if cells is None:
                        continue
                    observations.append(
                        {
                            "canonical_unit": unit["canonical_unit"],
                            "cells": cells,
                            "locator": {
                                "page_json_version_id": page_json_version_id,
                                "section_id": f"s{section_ordinal}",
                                "table_id": f"t{table_ordinal}",
                            },
                            "money_column_ordinals": canonical_clone_v1(
                                money_ordinals
                            ),
                            "row_ordinal": row_ordinal,
                            "unit_receipt": canonical_clone_v1(unit),
                        }
                    )
    return observations


def _balance_position_matches_movement_ending(
    balance_cell: Mapping[str, Any], observation: Mapping[str, Any]
) -> bool:
    ending = observation.get("ending_observation")
    ending_coefficient = (
        ending.get("cells", {}).get("CUSTOMER_PROVISION", {}).get("coefficient")
        if type(ending) is dict
        else None
    )
    balance_coefficient = balance_cell.get("coefficient")
    return bool(
        type(ending_coefficient) is int
        and type(balance_coefficient) is int
        and abs(abs(ending_coefficient) - abs(balance_coefficient)) <= 1
    )


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
            *(str(item or "") for item in section.get("narratives_exact", [])),
            str(table.get("title_exact") or ""),
        ]
    )
    position_surface = _normalized(header_surface + " " + container_surface)
    container_marker = _transposed_period_marker(table.get("title_exact"))
    container_years = _surface_years(container_surface)
    container_duration_signatures = _duration_signatures(container_surface)
    result = []
    for period_key, actions in grouped.items():
        if period_key is None and container_marker is not None:
            period_key = ("SEMANTIC_ROLE", container_marker)
        elif period_key is None and len(container_years) == 1:
            period_key = ("YEAR", container_years[0])
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
        result.append(
            {
                "all_actions": canonical_clone_v1(actions),
                "canonical_unit": canonical_unit,
                "container_years": container_years,
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
    observation: Mapping[str, Any], *, root_cell: Mapping[str, Any] | None
) -> dict[str, Any] | None:
    variants = observation.get("variants")
    if type(variants) is not list or not variants:
        return None
    if len(variants) == 1:
        return canonical_clone_v1(variants[0])
    root_coefficient = root_cell.get("coefficient") if type(root_cell) is dict else None
    if type(root_coefficient) is not int:
        return None
    matches = [
        variant
        for variant in variants
        if type(variant.get("cells", {}).get("CUSTOMER_PROVISION", {}).get("coefficient"))
        is int
        and abs(variant["cells"]["CUSTOMER_PROVISION"]["coefficient"])
        == abs(root_coefficient)
    ]
    return canonical_clone_v1(matches[0]) if len(matches) == 1 else None


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
                "ending_observation": None,
                "header_position": None,
                "period_key": canonical_clone_v1(period_key),
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
                structural_surface = " ".join(
                    [
                        str(section.get("title_exact") or ""),
                        str(table.get("title_exact") or ""),
                    ]
                )
                structural_normalized = _normalized(structural_surface)
                structural_owner = _movement_owner_kind(structural_surface)
                role_axis = _transposed_role_axis(table)
                if _customer_balance_summary_owner(table):
                    active_owner = "CUSTOMER"
                    active_owner_page = axis["physical_page"]
                generic_movement = bool(
                    "du phong rui ro tin dung" in structural_normalized
                    and any(
                        marker in structural_normalized
                        for marker in ("thay doi", "tang giam", "doi voi")
                    )
                )
                if (
                    role_axis is not None
                    and {
                        "CUSTOMER_GENERAL",
                        "CUSTOMER_SPECIFIC",
                    }
                    <= set(role_axis)
                    and generic_movement
                    and structural_owner not in {
                        "INTERBANK",
                        "PURCHASED_DEBT",
                        "SECURITIES_CONTROL",
                    }
                ):
                    owner = "CUSTOMER"
                if owner is None and active_owner_page is not None and (
                    axis["physical_page"] - active_owner_page <= 1
                ):
                    owner = active_owner
                elif generic_movement and active_owner in {"CUSTOMER", "INTERBANK"}:
                    owner = active_owner
                if owner != "CUSTOMER":
                    if explicit_owner is not None:
                        active_owner = explicit_owner
                        active_owner_page = axis["physical_page"]
                    continue
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
                table_observations = _transposed_table_observations(
                    section=section,
                    table=table,
                    region=region,
                    compiled_specs=compiled_specs,
                    document_unit_context=document_unit_context,
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
    elif len(observations) == 1:
        observation = observations[0]
        period_key = observation.get("period_key")
        table_marker = _transposed_period_marker(
            observation.get("table_title_exact")
        )
        if observation.get("header_position") == "OPENING_ANNUAL_POSITION":
            pass
        elif (
            observation.get("header_position") == "CURRENT_POSITION"
            or period_key == ["SEMANTIC_ROLE", "CURRENT_PERIOD"]
            or table_marker == "CURRENT_PERIOD"
        ):
            current = observation
            rule = "ONE_SOURCE_VISIBLE_CURRENT_DURATION_MOVEMENT_OBSERVATION"
        elif (
            period_key == ["SEMANTIC_ROLE", "COMPARATIVE_PERIOD"]
            or table_marker == "COMPARATIVE_PERIOD"
        ):
            comparative = observation
            rule = (
                "ONE_SOURCE_VISIBLE_COMPARATIVE_DURATION_MOVEMENT_"
                "OBSERVATION_CURRENT_UNOBSERVED"
            )
        elif (
            type(period_key) is list
            and len(period_key) == 2
            and period_key[0] == "YEAR"
            and type(period_key[1]) is int
            and root is not None
        ):
            source_lane_keys = root.get("lane_axis", {}).get("source_lane_keys")
            lane_years = [
                _surface_years(item)
                for item in (
                    source_lane_keys if type(source_lane_keys) is list else []
                )
            ]
            if len(lane_years) == 2 and lane_years[0] == [period_key[1]]:
                current = observation
                rule = (
                    "ONE_SOURCE_VISIBLE_YEAR_MOVEMENT_MATCHES_PRIMARY_"
                    "CURRENT_DURATION_LANE"
                )
            elif len(lane_years) == 2 and lane_years[1] == [period_key[1]]:
                comparative = observation
                rule = (
                    "ONE_SOURCE_VISIBLE_YEAR_MOVEMENT_MATCHES_PRIMARY_"
                    "COMPARATIVE_DURATION_LANE_CURRENT_UNOBSERVED"
                )
    elif len(observations) == 2:
        by_marker = {
            item.get("period_key", (None, None))[1]: item
            for item in observations
            if type(item.get("period_key")) is list
            and item["period_key"][0] == "SEMANTIC_ROLE"
        }
        by_year = {
            item["period_key"][1]: item
            for item in observations
            if type(item.get("period_key")) is list
            and item["period_key"][0] == "YEAR"
        }
        if set(by_marker) == {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"}:
            current = by_marker["CURRENT_PERIOD"]
            comparative = by_marker["COMPARATIVE_PERIOD"]
            rule = "EXACT_SOURCE_VISIBLE_CURRENT_AND_COMPARATIVE_GROUP_LABELS"
        elif (
            set(by_marker) == {"COMPARATIVE_PERIOD"}
            and len(by_year) == 1
        ):
            comparative = by_marker["COMPARATIVE_PERIOD"]
            current = next(iter(by_year.values()))
            rule = (
                "EXACT_SOURCE_VISIBLE_COMPARATIVE_GROUP_AND_SINGLE_EXPLICIT_"
                "CURRENT_YEAR_MOVEMENT"
            )
        elif len(by_year) == 2:
            years = sorted(by_year, reverse=True)
            current, comparative = by_year[years[0]], by_year[years[1]]
            rule = "TWO_EXPLICIT_SOURCE_YEAR_MOVEMENT_OBSERVATIONS"
        elif all(item.get("period_key") is None for item in observations):
            observation_units = {
                item.get("canonical_unit")
                for item in observations
                if type(item.get("canonical_unit")) is str
            }
            balance_positions = [
                item
                for item in _customer_balance_position_observations(
                    pages=pages, compiled_specs=compiled_specs
                )
                if len(observation_units) == 1
                and item.get("canonical_unit") == next(iter(observation_units))
            ]
            matched_orders = []
            for balance in balance_positions:
                lane_matches = [
                    [
                        observation
                        for observation in observations
                        if _balance_position_matches_movement_ending(
                            balance_cell, observation
                        )
                    ]
                    for balance_cell in balance["cells"]
                ]
                if (
                    all(len(items) == 1 for items in lane_matches)
                    and lane_matches[0][0] is not lane_matches[1][0]
                ):
                    matched_orders.append(
                        (lane_matches[0][0], lane_matches[1][0])
                    )
            distinct_orders = {
                tuple(
                    (
                        item["region"]["page_json_version_id"],
                        item["region"]["section_id"],
                        item["region"]["table_id"],
                    )
                    for item in order
                )
                for order in matched_orders
            }
            if len(distinct_orders) == 1:
                current, comparative = matched_orders[0]
                rule = (
                    "EXACT_CUSTOMER_ALLOWANCE_BALANCE_POSITIONS_BIND_TWO_"
                    "UNTITLED_MOVEMENT_TABLES"
                )
            else:
                ordered_container_years = []
                for observation in observations:
                    for year in observation.get("container_years", []):
                        if year not in ordered_container_years:
                            ordered_container_years.append(year)
                if len(ordered_container_years) >= 2:
                    current, comparative = observations
                    rule = (
                        "TWO_ORDERED_MOVEMENT_TABLES_BIND_TO_TWO_ORDERED_"
                        "VISIBLE_CONTAINER_PERIODS"
                    )
        else:
            ordered_container_years = []
            for observation in observations:
                for year in observation.get("container_years", []):
                    if year not in ordered_container_years:
                        ordered_container_years.append(year)
            if len(ordered_container_years) >= 2:
                current, comparative = observations
                rule = (
                    "TWO_ORDERED_MOVEMENT_TABLES_BIND_TO_TWO_ORDERED_VISIBLE_"
                    "CONTAINER_PERIODS"
                )
            elif root is not None:
                matches = []
                for _lane, root_cell in enumerate(root["cells"]):
                    lane_matches = []
                    for observation in observations:
                        if any(
                            type(variant["cells"]["CUSTOMER_PROVISION"].get("coefficient"))
                            is int
                            and abs(
                                variant["cells"]["CUSTOMER_PROVISION"]["coefficient"]
                            )
                            == abs(root_cell["coefficient"])
                            for variant in observation["variants"]
                        ):
                            lane_matches.append(observation)
                    matches.append(lane_matches)
                if (
                    all(len(items) == 1 for items in matches)
                    and matches[0][0] is not matches[1][0]
                ):
                    current, comparative = matches[0][0], matches[1][0]
                    rule = "PRIMARY_DURATION_LANES_EXACTLY_BIND_TWO_MOVEMENT_TABLES"
                elif len(matches[0]) == 1 and not matches[1]:
                    current = matches[0][0]
                    excluded_noncomparable_duration_control = next(
                        item for item in observations if item is not current
                    )
                    rule = (
                        "PRIMARY_CURRENT_DURATION_LANE_EXACTLY_BINDS_ONE_"
                        "MOVEMENT_OTHER_ANNUAL_CONTROL_IS_SOURCE_ONLY"
                    )
    if current is None and comparative is None:
        return None
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
        comparative_root_exact = bool(
            root is not None
            and any(
                type(
                    variant.get("cells", {})
                    .get("CUSTOMER_PROVISION", {})
                    .get("coefficient")
                )
                is int
                and abs(
                    variant["cells"]["CUSTOMER_PROVISION"]["coefficient"]
                )
                == abs(root["cells"][1]["coefficient"])
                for variant in comparative.get("variants", [])
            )
        )
        if (
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
            and not comparative_root_exact
        ):
            excluded_noncomparable_duration_control = comparative
            comparative = None
            rule = (
                "CURRENT_DURATION_MOVEMENT_ONLY_NONCOMPARABLE_ANNUAL_"
                "ROLLFORWARD_IS_SOURCE_ONLY"
            )
    current_variant = (
        None
        if current is None
        else _choose_transposed_variant(
            current, root_cell=root["cells"][0] if root is not None else None
        )
    )
    comparative_variant = (
        None
        if comparative is None
        else _choose_transposed_variant(
            comparative,
            root_cell=root["cells"][1] if root is not None else None,
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
                source_only_rows.append(
                    {
                        "disposition": (
                            "PRIOR_ANNUAL_POSITION_CONTROL_NOT_COMPARATIVE_DURATION"
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
        "excluded_position_control": excluded_position_control,
        "format_version": ADAPTER_FORMAT_VERSION,
        "rule": rule,
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


def build_gemini_json_credit_risk_provision_expense_indexed_query_evidence_v1(
    *,
    base_indexed_query_evidence: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Recover every strict source-visible Family-37 disclosure generically."""

    base = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        base_indexed_query_evidence, compiled_specs=compiled_specs
    )
    clusters = []
    for disposition, document in zip(
        base["candidate_dispositions"], base["selected_document_axis"], strict=True
    ):
        source_pages = page_json_by_document.get(document["document_ordinal"])
        if type(source_pages) is not dict:
            raise _error("Family-37 selected document page JSON is absent")
        pages, repair_receipts = _apply_document_repairs(
            pages=source_pages,
            source_sha256=document["source_sha256"],
            compiled_specs=compiled_specs,
        )
        structural_projection_receipts = _project_shared_duration_header_prefixes(
            pages
        )
        structural_projection_receipts.extend(
            _project_customer_adjacent_continuations(
                pages,
                selected_page_axis=base["selected_page_axis"],
                document_ordinal=document["document_ordinal"],
            )
        )
        normal = _normal_expense_regions(
            document=document,
            selected_page_axis=base["selected_page_axis"],
            pages=pages,
            compiled_specs=compiled_specs,
        )
        transposed_observations = (
            []
            if normal
            else _customer_transposed_observations(
                document=document,
                selected_page_axis=base["selected_page_axis"],
                pages=pages,
                compiled_specs=compiled_specs,
            )
        )
        transposed = None if normal else _transposed_detail_receipt(
            document=document,
            selected_page_axis=base["selected_page_axis"],
            pages=pages,
            compiled_specs=compiled_specs,
        )
        query_kind = None
        query_receipt: dict[str, Any] | None = None
        regions: list[dict[str, Any]] = []
        split_receipts: list[dict[str, Any]] = []
        if len(normal) == 1:
            regions, split_receipts = _split_duplicate_other_rows(
                pages=pages, regions=normal, compiled_specs=compiled_specs
            )
            query_kind = "NORMAL_TWO_PERIOD_SOURCE_TABLE"
        elif len(normal) > 1:
            raise _error("Family-37 document has multiple strict normal candidates")
        elif transposed is not None:
            roots = _primary_root_observations(
                pages=pages,
                selected_page_axis=base["selected_page_axis"],
                document_ordinal=document["document_ordinal"],
                compiled_specs=compiled_specs,
            )
            roots = _primary_roots_compatible_with_observations(
                roots, transposed_observations
            )
            if len(roots) > 1:
                raise _error("Family-37 transposed disclosure has ambiguous primary roots")
            detail_axis = [
                item
                for item in (transposed["current"], transposed["comparative"])
                if item is not None
            ]
            regions = [
                region
                for item in detail_axis
                for region in _observation_regions(item)
            ]
            if roots:
                regions.append(
                    _primary_root_region(
                        roots[0],
                        document=document,
                        selected_page_axis=base["selected_page_axis"],
                    )
                )
            query_kind = (
                "TRANSPOSED_CUSTOMER_PROVISION_WITH_PRIMARY_ROOT"
                if roots
                else "TRANSPOSED_CUSTOMER_PROVISION_WITH_LOCAL_UNIT"
            )
            query_receipt = canonical_clone_v1(transposed)
        elif transposed_observations:
            roots = _primary_root_observations(
                pages=pages,
                selected_page_axis=base["selected_page_axis"],
                document_ordinal=document["document_ordinal"],
                compiled_specs=compiled_specs,
            )
            roots = _primary_roots_compatible_with_observations(
                roots, transposed_observations
            )
            observation_units = {
                item.get("canonical_unit")
                for item in transposed_observations
                if type(item.get("canonical_unit")) is str
            }
            if roots or len(observation_units) == 1:
                regions = [
                    region
                    for observation in transposed_observations
                    for region in _observation_regions(observation)
                ]
                for root in roots:
                    regions.append(
                        _primary_root_region(
                            root,
                            document=document,
                            selected_page_axis=base["selected_page_axis"],
                        )
                    )
                query_kind = "TRANSPOSED_CUSTOMER_PROVISION_AMBIGUOUS_PRESENTATION"
                query_receipt = {
                    "observations": canonical_clone_v1(transposed_observations),
                    "reason": (
                        "SOURCE_VISIBLE_MOVEMENT_ACTIONS_EXIST_BUT_EXACT_"
                        "DURATION_OR_GROSS_NET_PRESENTATION_IS_NOT_UNIQUE"
                    ),
                    **(
                        {"root": canonical_clone_v1(roots[0])}
                        if len(roots) == 1
                        else {"root_axis": canonical_clone_v1(roots)}
                        if roots
                        else {}
                    ),
                }
        elif repair_receipts:
            raise _error("Family-37 authenticated repair did not select one family region")
        if not regions:
            source_cluster = disposition["cluster"]
            material = {
                **{
                    key: canonical_clone_v1(value)
                    for key, value in source_cluster.items()
                    if key
                    not in {
                        "cluster_id",
                        "component_regions",
                        "owner_receipt",
                        "reasons",
                        "status",
                    }
                },
                "component_regions": [],
                "owner_receipt": None,
                "reasons": [],
                "status": NOT_OBSERVED,
            }
            clusters.append(
                {
                    **material,
                    "cluster_id": "gjmthfcv1:cluster:"
                    + canonical_json_sha256_v1(material),
                }
            )
            continue
        unique_regions = {}
        for region in regions:
            identity = (
                region["page_json_version_id"],
                region["section_id"],
                region["table_id"],
            )
            existing = unique_regions.get(identity)
            if existing is None:
                unique_regions[identity] = region
            elif existing.get("component_roles") != region.get("component_roles"):
                raise _error("Family-37 duplicate region role axis drifted")
        regions = list(unique_regions.values())
        regions.sort(
            key=lambda item: (
                item["selected_page_ordinal"],
                int(item["section_id"][1:]),
                int(item["table_id"][1:]),
            )
        )
        for fragment_ordinal, region in enumerate(regions, start=1):
            region["fragment_ordinal"] = fragment_ordinal
        adapter_material = {
            "format_version": ADAPTER_FORMAT_VERSION,
            "query_kind": query_kind,
            "source_repair_receipt_ids": [
                item["receipt_id"] for item in repair_receipts
            ],
            "structural_projection_receipt_ids": [
                item["receipt_id"] for item in structural_projection_receipts
            ],
            "split_receipts": split_receipts,
            **({"transposed_receipt": query_receipt} if query_receipt is not None else {}),
        }
        adapter_receipt = {
            **adapter_material,
            "receipt_id": "gjcrpefav1:query:"
            + canonical_json_sha256_v1(adapter_material),
        }
        source_cluster = disposition["cluster"]
        material = {
            **{key: canonical_clone_v1(value) for key, value in source_cluster.items() if key != "cluster_id"},
            "component_regions": regions,
            "credit_risk_provision_expense_query_adapter_receipt": adapter_receipt,
            "reasons": [],
            "status": READY,
        }
        clusters.append(
            {
                **material,
                "cluster_id": "gjmthfcv1:cluster:"
                + canonical_json_sha256_v1(material),
            }
        )
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


def _movement_source_role_coverage(
    *,
    document: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    mappings: Sequence[Mapping[str, Any]],
    direct_expense_table_selected: bool,
) -> dict[str, Any]:
    mapped_axes = {
        (
            source_ref["locator"]["page_json_version_id"],
            source_ref["locator"]["section_id"],
            source_ref["locator"]["table_id"],
            source_ref["row_ordinal"],
            column_ordinal,
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
    entries = []
    violations = []
    for observation in observations:
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
            )
            mapped = axis in mapped_axes
            if mapped:
                disposition = "MAPPED_FROM_EXACT_SOURCE_OBSERVATION"
            elif source_cell.get("coefficient") is None:
                disposition = "SOURCE_ONLY_BLANK_ROLE_OBSERVATION_NOT_MAPPED"
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
                "source_cell": canonical_clone_v1(source_cell),
                "source_label_exact": action["row"].get("label_exact"),
            }
            entries.append(entry)
            if not mapped and not disposition.startswith("SOURCE_ONLY_"):
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
        pages, _repair_receipts = _apply_document_repairs(
            pages=source_pages,
            source_sha256=document["source_sha256"],
            compiled_specs=compiled_specs,
        )
        _project_shared_duration_header_prefixes(pages)
        _project_customer_adjacent_continuations(
            pages,
            selected_page_axis=indexed["selected_page_axis"],
            document_ordinal=document_ordinal,
        )
        cluster = disposition["cluster"]
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
        direct_selected = query_kind == "NORMAL_TWO_PERIOD_SOURCE_TABLE"
        movement = _movement_source_role_coverage(
            document=document,
            selected_page_axis=indexed["selected_page_axis"],
            pages=pages,
            compiled_specs=compiled_specs,
            mappings=trial.get("mappings", []),
            direct_expense_table_selected=direct_selected,
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
                    "source_cell": entry["source_cell"],
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


def evaluate_gemini_json_credit_risk_provision_expense_family_cluster_v1(
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
        _project_customer_adjacent_continuations(
            pages,
            selected_page_axis=selected_page_axis,
            document_ordinal=first["document_ordinal"],
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
        if len(roots) == 1:
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
        pages=pages,
        selected_page_axis=selected_page_axis,
        source_repair_receipts=source_repair_receipts,
        split_receipts=split_receipts,
        structural_projection_receipts=structural_projection_receipts,
        unit_receipts=unit_receipts,
        compiled_specs=compiled_specs,
    )


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
        candidates = []
        mappings = []
        reasons = []
        selected_candidate_id = None
        status = disposition["disposition"]
        if status == READY:
            regions = cluster["component_regions"]
            candidate = evaluate_gemini_json_credit_risk_provision_expense_family_cluster_v1(
                regions=regions,
                page_json_by_version=page_json_by_document[ordinal],
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
