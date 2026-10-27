"""Family-38 adapter for other-activity disclosures.

The shared multi-table engine remains the accounting authority.  This module
adds a direct primary income-statement result when the detailed note is absent
and family-local checks of independently source-owned units and role scope.
When a complete note does not print its own result, its direct detail mappings
are combined with the direct primary-statement result.  No source value is
derived and a blank source cell is never converted to zero. Unknown semantic
rows and unproved mixed granularity remain held, even when totals close.
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
    classify_gemini_json_multitable_hierarchical_table_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
    validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    validate_gemini_json_multitable_hierarchical_sweep_query_bindings_v1,
)
from bctc_ai.evaluation.source_observation_lane_math_v1 import (
    additive_source_lane_receipts_v1,
    observed_source_coefficient_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FAMILY_ID = "OTHER_ACTIVITY"
ADAPTER_FORMAT_VERSION = "GEMINI_JSON_OTHER_ACTIVITY_FAMILY_ADAPTER_V1"
QUERY_RECEIPT_FORMAT_VERSION = "GEMINI_JSON_OTHER_ACTIVITY_QUERY_RECEIPT_V1"
ADAPTER_SPEC_FORMAT_VERSION = "GEMINI_JSON_OTHER_ACTIVITY_ADAPTER_SPEC_V1"
SOURCE_REPAIR_FORMAT_VERSION = "OTHER_ACTIVITY_AUTHENTICATED_SOURCE_REPAIR_SPEC_V1"
DEFAULT_ADAPTER_SPEC_PATH = "config/families/tm-other-activity-adapter-v1.json"
DEFAULT_SOURCE_REPAIR_SPEC_PATH = "config/families/tm-other-activity-source-repair-v1.json"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_OTHER_ACTIVITY_DIRECT_SOURCE_"
    "PRESENTATION_PRIMARY_RESULT_FALLBACK_AND_EXACT_SAME_DOCUMENT_UNIT_"
    "CORROBORATION_PRIVATE_CLONE_ONLY_NO_BLANK_ZERO_NO_VALUE_OR_MAGNITUDE_"
    "BACKSOLVE_NO_BANK_FILE_YEAR_PAGE_ROUTING_PROPOSAL_ONLY_" + SHARED_CLAIM_BOUNDARY
)

_UNIT_SURFACE = {"MILLION_VND": "Triệu đồng", "VND": "VND"}


class GeminiJsonOtherActivityFamilyV1Error(ValueError):
    """Family-38 source evidence, policy, or replay drifted."""


def _error(message: str) -> GeminiJsonOtherActivityFamilyV1Error:
    return GeminiJsonOtherActivityFamilyV1Error(message)


def _load_adapter_spec() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[3] / DEFAULT_ADAPTER_SPEC_PATH
    try:
        value = json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("other-activity adapter spec is absent or invalid") from exc
    if type(value) is not dict:
        raise _error("other-activity adapter spec is not one object")
    return value


def _load_source_repair_spec() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[3] / DEFAULT_SOURCE_REPAIR_SPEC_PATH
    try:
        value = json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("other-activity source-repair spec is absent or invalid") from exc
    if type(value) is not dict:
        raise _error("other-activity source-repair spec is not one object")
    return value


def _sha256_string(value: Any) -> bool:
    return bool(
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _compile_source_repair_spec(value: Any) -> list[dict[str, Any]]:
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
        raise _error("other-activity source-repair spec is invalid")
    checked = []
    identities = set()
    for raw in value["repairs"]:
        kind = raw.get("repair_kind") if type(raw) is dict else None
        locator = raw.get("locator") if type(raw) is dict else None
        common_fields = {
            "after_exact",
            "before_exact",
            "locator",
            "pdf_page_render_sha256",
            "repair_id",
            "repair_kind",
            "source_sha256",
        }
        expected_fields = (
            common_fields | {"column_ordinal"}
            if kind
            in {
                "COLUMN_VALUE_KIND_PDF_VISIBLE_MONEY",
                "MONEY_CELL_PDF_VISIBLE_DASH",
            }
            else common_fields
        )
        if (
            type(raw) is not dict
            or set(raw) != expected_fields
            or kind
            not in {
                "COLUMN_VALUE_KIND_PDF_VISIBLE_MONEY",
                "MONEY_CELL_PDF_VISIBLE_DASH",
                "ROW_KIND_PDF_VISIBLE_TOTAL",
                "ROW_VALUES_PDF_VISIBLE_EXACT",
            }
            or not _sha256_string(raw.get("source_sha256"))
            or not _sha256_string(raw.get("pdf_page_render_sha256"))
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
            or not _sha256_string(
                str(locator.get("page_json_version_id", "")).removeprefix("gfpstorev1:json:")
            )
            or type(locator.get("physical_page")) is not int
            or locator["physical_page"] <= 0
            or type(locator.get("row_ordinal")) is not int
            or locator["row_ordinal"] <= 0
            or type(locator.get("section_id")) is not str
            or not locator["section_id"].startswith("s")
            or type(locator.get("table_id")) is not str
            or not locator["table_id"].startswith("t")
        ):
            raise _error("other-activity source repair is invalid")
        if kind == "MONEY_CELL_PDF_VISIBLE_DASH" and (
            raw.get("before_exact") is not None
            or raw.get("after_exact") != "-"
            or type(raw.get("column_ordinal")) is not int
            or raw["column_ordinal"] <= 0
        ):
            raise _error("other-activity dash source repair is invalid")
        if kind == "COLUMN_VALUE_KIND_PDF_VISIBLE_MONEY" and (
            raw.get("before_exact") != "UNKNOWN"
            or raw.get("after_exact") != "MONEY"
            or type(raw.get("column_ordinal")) is not int
            or raw["column_ordinal"] <= 0
        ):
            raise _error("other-activity money-column source repair is invalid")
        if kind == "ROW_KIND_PDF_VISIBLE_TOTAL" and (
            raw.get("before_exact") != "UNKNOWN" or raw.get("after_exact") != "TOTAL"
        ):
            raise _error("other-activity total-row source repair is invalid")
        if kind == "ROW_VALUES_PDF_VISIBLE_EXACT" and (
            type(raw.get("before_exact")) is not list
            or type(raw.get("after_exact")) is not list
            or not raw["before_exact"]
            or len(raw["before_exact"]) != len(raw["after_exact"])
            or any(
                item is not None and type(item) is not str
                for item in [*raw["before_exact"], *raw["after_exact"]]
            )
        ):
            raise _error("other-activity row-values source repair is invalid")
        material = {
            key: canonical_clone_v1(item) for key, item in raw.items() if key != "repair_id"
        }
        if raw.get("repair_id") != ("gjoafav1:repair:" + canonical_json_sha256_v1(material)):
            raise _error("other-activity source-repair identity drifted")
        identity = (
            raw["source_sha256"],
            locator["page_json_version_id"],
            locator["section_id"],
            locator["table_id"],
            locator["row_ordinal"],
            raw.get("column_ordinal"),
        )
        if identity in identities:
            raise _error("other-activity source-repair axis is duplicate")
        identities.add(identity)
        checked.append(canonical_clone_v1(raw))
    ordered = sorted(
        checked,
        key=lambda item: (
            item["source_sha256"],
            item["locator"]["physical_page"],
            item["locator"]["section_id"],
            item["locator"]["table_id"],
            item["locator"]["row_ordinal"],
            item.get("column_ordinal", 0),
        ),
    )
    if not same_typed_json_v1(checked, ordered):
        raise _error("other-activity source-repair axis is unordered")
    return checked


def _compile_adapter_spec(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value)
        != {
            "family_id",
            "format_version",
            "primary_duplicate_presentation_policy",
            "primary_unit_corroboration_policy",
            "primary_projection_policy",
            "unit_corroboration_policy",
            "unlabeled_structural_subtotal_policy",
        }
        or value.get("family_id") != FAMILY_ID
        or value.get("format_version") != ADAPTER_SPEC_FORMAT_VERSION
        or value.get("primary_duplicate_presentation_policy")
        != (
            "EXACT_OR_VND_WITHIN_ONE_MILLION_TWO_COMPONENT_INDEPENDENT_"
            "DISPLAY_ROUNDING_PREFER_MILLION_VND"
        )
        or value.get("primary_projection_policy")
        != "EXACT_ROOT_ROW_ONLY_NONFAMILY_PRIMARY_ROWS_EXCLUDED"
        or value.get("primary_unit_corroboration_policy")
        != (
            "NO_UNIT_DONATION_WITHOUT_TARGET_LOCAL_SOURCE_UNIT_SCOPE"
        )
        or value.get("unit_corroboration_policy")
        != (
            "SOURCE_OWNED_LOCAL_NOTE_UNIT_ONLY_NO_NUMERIC_PRIMARY_DONATION"
        )
        or value.get("unlabeled_structural_subtotal_policy")
        != "EXACT_NONTERMINAL_CONTIGUOUS_SOURCE_COMPONENT_SUM_PRIVATE_OMISSION"
    ):
        raise _error("other-activity adapter spec is invalid")
    return canonical_clone_v1(value)


def compile_gemini_json_other_activity_family_specs_v1(
    topology_spec: Any,
    evaluation_spec: Any,
    schema_binding_spec: Any,
    adapter_spec: Any | None = None,
    source_repair_spec: Any | None = None,
) -> dict[str, Any]:
    """Compile the base family plus private primary/detail projections."""

    adapter = _compile_adapter_spec(_load_adapter_spec() if adapter_spec is None else adapter_spec)
    if type(evaluation_spec) is not dict or evaluation_spec.get("context_residual_bindings") != []:
        raise _error("other-activity unknown source rows cannot gain OTHER roles from closure")
    source_repairs_raw = (
        _load_source_repair_spec() if source_repair_spec is None else source_repair_spec
    )
    base = compile_gemini_json_multitable_hierarchical_family_specs_v1(
        topology_spec, evaluation_spec, schema_binding_spec
    )
    if base.get("topology", {}).get("family_id") != FAMILY_ID:
        raise _error("other-activity adapter received another family")

    primary_topology = canonical_clone_v1(topology_spec)
    for child in primary_topology["children"]:
        role = child["role"].replace("_", " ").lower()
        for matcher_ordinal, matcher in enumerate(child["matchers"], start=1):
            matcher["aliases"] = [
                f"other activity primary root only sentinel {role} {matcher_ordinal}"
            ]
    primary_evaluation = canonical_clone_v1(evaluation_spec)
    primary_evaluation["primary_statement_source_result_fallback_policy"] = (
        "UNIQUE_SHALLOWEST_STRUCTURAL_EXACT_VISIBLE_ROOT_WHEN_NOTE_NOT_OBSERVED"
    )
    primary_evaluation["root_only_source_result_policy"] = "ALLOW_EXACT_SOURCE_RESULT"
    primary_evaluation["unmapped_direct_family_row_policy"] = "IGNORE"
    primary_schema = canonical_clone_v1(schema_binding_spec)
    primary_schema["root_mapping_policy"] = "SOURCE_VISIBLE_PRIMARY_RESULT_OR_EXACT_NOTE_EQUATION"
    primary = compile_gemini_json_multitable_hierarchical_family_specs_v1(
        primary_topology, primary_evaluation, primary_schema
    )

    detail_evaluation = canonical_clone_v1(evaluation_spec)
    detail_evaluation["family_root_requirement"] = "OPTIONAL"
    detail_schema = canonical_clone_v1(schema_binding_spec)
    detail_schema["root_mapping_policy"] = "STRUCTURAL_CONTEXT_ONLY"
    detail = compile_gemini_json_multitable_hierarchical_family_specs_v1(
        topology_spec, detail_evaluation, detail_schema
    )

    base["other_activity_primary_specs"] = primary
    base["other_activity_direct_detail_specs"] = detail
    base["other_activity_adapter_spec"] = adapter
    base["other_activity_source_repairs"] = _compile_source_repair_spec(source_repairs_raw)
    base["other_activity_source_repair_spec_sha256"] = canonical_json_sha256_v1(source_repairs_raw)
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


def _source_position(region: Mapping[str, Any]) -> tuple[int, int, int]:
    return (
        region["selected_page_ordinal"],
        int(region["section_id"][1:]),
        int(region["table_id"][1:]),
    )


def _resequence_regions(regions: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[tuple[str, str, str], dict[str, Any]] = {}
    for region in regions:
        key = (
            region["page_json_version_id"],
            region["section_id"],
            region["table_id"],
        )
        unique.setdefault(key, canonical_clone_v1(region))
    ordered = sorted(unique.values(), key=_source_position)
    for ordinal, region in enumerate(ordered, start=1):
        region["fragment_ordinal"] = ordinal
    return ordered


def _page_records_by_version(
    page_records: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    result = {}
    for record in page_records:
        version_id = record.get("page_json_version_id")
        page = record.get("page_json")
        if type(version_id) is not str or type(page) is not dict or version_id in result:
            raise _error("other-activity page-record axis is invalid")
        result[version_id] = record
    return result


def _source_repair_receipt(
    repair: Mapping[str, Any],
    *,
    before_page_json_sha256: str,
    after_page_json_sha256: str,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    rules = {
        "COLUMN_VALUE_KIND_PDF_VISIBLE_MONEY": (
            "PDF_RENDER_AUTHENTICATED_VISIBLE_MONEY_COLUMN_KIND_TRANSCRIBED_"
            "TO_PRIVATE_SOURCE_CLONE_NO_VALUE_INFERENCE"
        ),
        "MONEY_CELL_PDF_VISIBLE_DASH": (
            "PDF_RENDER_AUTHENTICATED_VISIBLE_DASH_TRANSCRIBED_TO_PRIVATE_"
            "SOURCE_CLONE_NO_BLANK_OR_VALUE_INFERENCE"
        ),
        "ROW_VALUES_PDF_VISIBLE_EXACT": (
            "PDF_RENDER_AUTHENTICATED_EXACT_ROW_VALUE_ALIGNMENT_TRANSCRIBED_"
            "TO_PRIVATE_SOURCE_CLONE_NO_VALUE_INFERENCE"
        ),
        "ROW_KIND_PDF_VISIBLE_TOTAL": (
            "PDF_RENDER_AUTHENTICATED_VISIBLE_DOUBLE_RULE_TOTAL_ROW_KIND_"
            "TRANSCRIBED_TO_PRIVATE_SOURCE_CLONE_NO_VALUE_INFERENCE"
        ),
    }
    material = {
        "after_page_json_sha256": after_page_json_sha256,
        "before_page_json_sha256": before_page_json_sha256,
        "repair": canonical_clone_v1(repair),
        "rule": rules[repair["repair_kind"]],
        "source_repair_spec_sha256": compiled_specs["other_activity_source_repair_spec_sha256"],
    }
    return {
        **material,
        "receipt_id": "gjoafav1:repair-receipt:" + canonical_json_sha256_v1(material),
    }


def _apply_source_repairs_to_page_records(
    page_records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records = [canonical_clone_v1(record) for record in page_records]
    by_version = _page_records_by_version(records)
    source_sha256s = {record.get("source_sha256") for record in records}
    if len(source_sha256s) != 1:
        raise _error("other-activity source-repair document axis is invalid")
    source_sha256 = next(iter(source_sha256s))
    receipts = []
    for repair in compiled_specs["other_activity_source_repairs"]:
        if repair["source_sha256"] != source_sha256:
            continue
        locator = repair["locator"]
        record = by_version.get(locator["page_json_version_id"])
        if (
            record is None
            or record.get("source_sha256") != repair["source_sha256"]
            or record.get("physical_page") != locator["physical_page"]
        ):
            raise _error("other-activity source-repair selected page drifted")
        page = record["page_json"]
        before_sha = canonical_json_sha256_v1(page)
        try:
            _section, table = _source_table(
                page,
                section_id=locator["section_id"],
                table_id=locator["table_id"],
            )
            row = table["rows"][locator["row_ordinal"] - 1]
            values = row["values_exact"]
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            raise _error("other-activity source-repair locator drifted") from exc
        if type(values) is not list:
            raise _error("other-activity source-repair row values drifted")
        if repair["repair_kind"] == "COLUMN_VALUE_KIND_PDF_VISIBLE_MONEY":
            try:
                before_exact = table["columns"][repair["column_ordinal"] - 1]["value_kind"]
            except (IndexError, KeyError, TypeError) as exc:
                raise _error("other-activity source-repair column drifted") from exc
        elif repair["repair_kind"] == "ROW_KIND_PDF_VISIBLE_TOTAL":
            before_exact = row.get("row_kind")
        elif repair["repair_kind"] == "MONEY_CELL_PDF_VISIBLE_DASH":
            try:
                before_exact: Any = values[repair["column_ordinal"] - 1]
            except IndexError as exc:
                raise _error("other-activity source-repair cell drifted") from exc
        else:
            before_exact = canonical_clone_v1(values)
        if before_exact != repair["before_exact"]:
            raise _error("other-activity source-repair before image drifted")
        if repair["repair_kind"] == "COLUMN_VALUE_KIND_PDF_VISIBLE_MONEY":
            table["columns"][repair["column_ordinal"] - 1]["value_kind"] = repair["after_exact"]
        elif repair["repair_kind"] == "ROW_KIND_PDF_VISIBLE_TOTAL":
            row["row_kind"] = repair["after_exact"]
        elif repair["repair_kind"] == "MONEY_CELL_PDF_VISIBLE_DASH":
            values[repair["column_ordinal"] - 1] = repair["after_exact"]
        else:
            row["values_exact"] = canonical_clone_v1(repair["after_exact"])
        after_sha = canonical_json_sha256_v1(page)
        receipts.append(
            _source_repair_receipt(
                repair,
                before_page_json_sha256=before_sha,
                after_page_json_sha256=after_sha,
                compiled_specs=compiled_specs,
            )
        )
    return records, receipts


def _apply_source_repair_receipts_to_pages(
    pages: dict[str, dict[str, Any]], receipts: Any
) -> dict[str, dict[str, Any]]:
    if type(receipts) is not list:
        raise _error("other-activity source-repair receipt axis is invalid")
    for receipt in receipts:
        if type(receipt) is not dict:
            raise _error("other-activity source-repair receipt is invalid")
        material = {
            key: canonical_clone_v1(value) for key, value in receipt.items() if key != "receipt_id"
        }
        if receipt.get("receipt_id") != (
            "gjoafav1:repair-receipt:" + canonical_json_sha256_v1(material)
        ):
            raise _error("other-activity source-repair receipt identity drifted")
        repair = receipt.get("repair")
        locator = repair.get("locator") if type(repair) is dict else None
        page = pages.get(locator.get("page_json_version_id")) if type(locator) is dict else None
        if type(page) is not dict or canonical_json_sha256_v1(page) != receipt.get(
            "before_page_json_sha256"
        ):
            raise _error("other-activity source-repair replay page drifted")
        try:
            _section, table = _source_table(
                page,
                section_id=locator["section_id"],
                table_id=locator["table_id"],
            )
            row = table["rows"][locator["row_ordinal"] - 1]
            values = row["values_exact"]
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            raise _error("other-activity source-repair replay locator drifted") from exc
        if type(values) is not list:
            raise _error("other-activity source-repair replay row drifted")
        if repair["repair_kind"] == "COLUMN_VALUE_KIND_PDF_VISIBLE_MONEY":
            try:
                before_exact = table["columns"][repair["column_ordinal"] - 1]["value_kind"]
            except (IndexError, KeyError, TypeError) as exc:
                raise _error("other-activity source-repair replay column drifted") from exc
        elif repair["repair_kind"] == "ROW_KIND_PDF_VISIBLE_TOTAL":
            before_exact = row.get("row_kind")
        elif repair["repair_kind"] == "MONEY_CELL_PDF_VISIBLE_DASH":
            try:
                before_exact = values[repair["column_ordinal"] - 1]
            except IndexError as exc:
                raise _error("other-activity source-repair replay cell drifted") from exc
        else:
            before_exact = canonical_clone_v1(values)
        if before_exact != repair.get("before_exact"):
            raise _error("other-activity source-repair replay source drifted")
        if repair["repair_kind"] == "COLUMN_VALUE_KIND_PDF_VISIBLE_MONEY":
            table["columns"][repair["column_ordinal"] - 1]["value_kind"] = repair["after_exact"]
        elif repair["repair_kind"] == "ROW_KIND_PDF_VISIBLE_TOTAL":
            row["row_kind"] = repair["after_exact"]
        elif repair["repair_kind"] == "MONEY_CELL_PDF_VISIBLE_DASH":
            values[repair["column_ordinal"] - 1] = repair["after_exact"]
        else:
            row["values_exact"] = canonical_clone_v1(repair["after_exact"])
        if canonical_json_sha256_v1(page) != receipt.get("after_page_json_sha256"):
            raise _error("other-activity source-repair replay output drifted")
    return pages


def _primary_occurrences(
    page_records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    aliases = set(compiled_specs["topology"]["parent"]["aliases"])
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
            for table_ordinal, table in enumerate(tables if type(tables) is list else [], start=1):
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
                for row_ordinal, row in enumerate(rows if type(rows) is list else [], start=1):
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
                            "record": record,
                            "row_ordinal": row_ordinal,
                            "section_id": f"s{section_ordinal}",
                            "table_id": f"t{table_ordinal}",
                        }
                    )
    return occurrences


def _project_primary_occurrence(
    occurrence: Mapping[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
    unit_control: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    record = canonical_clone_v1(occurrence["record"])
    page = record["page_json"]
    section_ordinal = int(occurrence["section_id"][1:])
    section = page["sections"][section_ordinal - 1]
    before_sha = canonical_json_sha256_v1(page)
    section["statement_type"] = "BALANCE_SHEET"
    table = section["tables"][int(occurrence["table_id"][1:]) - 1]
    if unit_control is not None or not _unit_axis(
        table, compiled_specs=compiled_specs, document_unit_context=None
    ).get("complete"):
        return None
    suppressed_nonfamily_row_ordinals = []
    for row_ordinal, row in enumerate(table.get("rows") or [], start=1):
        if row_ordinal == occurrence["row_ordinal"] or type(row) is not dict:
            continue
        values = row.get("values_exact")
        if type(values) is list and any(value is not None for value in values):
            row["values_exact"] = [None for _value in values]
            suppressed_nonfamily_row_ordinals.append(row_ordinal)
    after_sha = canonical_json_sha256_v1(page)
    primary_specs = compiled_specs["other_activity_primary_specs"]
    projected = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[record], compiled_specs=primary_specs
    )
    regions = projected.get("component_regions")
    if projected.get("status") != READY or type(regions) is not list or len(regions) != 1:
        return None
    region = regions[0]
    if (
        region["page_json_version_id"] != record["page_json_version_id"]
        or region["section_id"] != occurrence["section_id"]
        or region["table_id"] != occurrence["table_id"]
    ):
        return None
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=regions,
        page_json_by_version={record["page_json_version_id"]: page},
        compiled_specs=primary_specs,
        query_receipt=(build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)),
    )
    mappings = candidate.get("mappings")
    root_mappings = (
        [mapping for mapping in mappings if mapping.get("role") == "FAMILY_ROOT_TOTAL"]
        if type(mappings) is list
        else []
    )
    if (
        candidate.get("status") != READY
        or type(mappings) is not list
        or len(root_mappings) != 1
        or root_mappings[0].get("state") != "SOURCE_VISIBLE_PRIMARY_STATEMENT_EXACT_RESULT"
    ):
        return None
    root_mapping = root_mappings[0]
    locator = {
        key: record[key]
        for key in (
            "document_id",
            "document_ordinal",
            "page_json_version_id",
            "physical_page",
            "selected_page_ordinal",
            "source_logical_name",
            "source_sha256",
        )
    } | {
        "row_ordinal": occurrence["row_ordinal"],
        "section_id": occurrence["section_id"],
        "table_id": occurrence["table_id"],
    }
    material = {
        "after_page_json_sha256": after_sha,
        "before_page_json_sha256": before_sha,
        "label_exact": occurrence["label_exact"],
        "locator": locator,
        "mapping_id": root_mapping["item_mapping_id"],
        "primary_unit_corroboration_receipt": canonical_clone_v1(unit_control),
        "rule": (
            "EXACT_PRIMARY_INCOME_STATEMENT_ROOT_PRIVATE_STATEMENT_TYPE_"
            "AND_ROW_SCOPE_PROJECTION_ROOT_VALUES_ROWS_COLUMNS_AND_LOCATORS_"
            "UNCHANGED_NONFAMILY_VALUES_EXCLUDED"
        ),
        "suppressed_nonfamily_row_ordinals": suppressed_nonfamily_row_ordinals,
        "statement_type_after": "BALANCE_SHEET",
        "statement_type_before": "INCOME_STATEMENT",
    }
    return {
        "candidate": candidate,
        "mapping": root_mapping,
        "projected_page": page,
        "projection_receipt": {
            **material,
            "receipt_id": "gjoafav1:primary:" + canonical_json_sha256_v1(material),
        },
        "region": region,
    }


def _economic_vector(mapping: Mapping[str, Any], compiled_specs: Mapping[str, Any]) -> tuple:
    powers = {
        item["canonical_unit"]: item["magnitude_power10"]
        for item in compiled_specs["unit_bindings"]
        if item["accepted"]
    }
    power = powers.get(mapping.get("unit"))
    values = mapping.get("values")
    if power is None or type(values) is not list:
        return ()
    return tuple(
        None if cell.get("coefficient") is None else cell["coefficient"] * (10**power)
        for cell in values
    )


def _primary_presentations_compatible(
    candidates: Sequence[Mapping[str, Any]], compiled_specs: Mapping[str, Any]
) -> bool:
    if not candidates:
        return False
    vectors = [_economic_vector(item["mapping"], compiled_specs) for item in candidates]
    if any(not vector for vector in vectors):
        return False
    if len(set(vectors)) == 1:
        return True
    if compiled_specs["other_activity_adapter_spec"]["primary_duplicate_presentation_policy"] != (
        "EXACT_OR_VND_WITHIN_ONE_MILLION_TWO_COMPONENT_INDEPENDENT_"
        "DISPLAY_ROUNDING_PREFER_MILLION_VND"
    ):
        return False
    vnd = [item for item in candidates if item["mapping"].get("unit") == "VND"]
    million = [item for item in candidates if item["mapping"].get("unit") == "MILLION_VND"]
    if len(vnd) != 1 or len(million) != 1 or len(candidates) != 2:
        return False
    raw = _mapping_vector(vnd[0]["mapping"])
    displayed = _mapping_vector(million[0]["mapping"])
    return bool(
        len(raw) == len(displayed)
        and all(
            source is not None
            and rounded is not None
            and abs(source - rounded * 1_000_000) < 1_000_000
            for source, rounded in zip(raw, displayed, strict=True)
        )
    )


def _primary_unit_control(
    occurrence: Mapping[str, Any],
    *,
    page_records: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Neither scalar equality nor a neighbouring statement donates a unit.

    No independently scoped target-unit receipt is implemented here. A target
    without its own printed local unit remains unusable.
    """
    return None


def _select_primary(
    page_records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> tuple[dict[str, Any] | None, list[str]]:
    occurrences = _primary_occurrences(page_records, compiled_specs=compiled_specs)
    candidates = []
    for occurrence in occurrences:
        candidate = _project_primary_occurrence(occurrence, compiled_specs=compiled_specs)
        if candidate is None:
            unit_control = _primary_unit_control(
                occurrence,
                page_records=page_records,
                compiled_specs=compiled_specs,
            )
            if unit_control is not None:
                candidate = _project_primary_occurrence(
                    occurrence,
                    compiled_specs=compiled_specs,
                    unit_control=unit_control,
                )
        if candidate is not None:
            candidates.append(candidate)
    if not occurrences:
        return None, []
    if not candidates:
        return None, ["PRIMARY_OTHER_ACTIVITY_SOURCE_RESULT_NOT_LOCALLY_USABLE"]
    if len(candidates) == 1:
        selected = candidates[0]
    else:
        if not _primary_presentations_compatible(candidates, compiled_specs):
            return None, ["CONFLICTING_PRIMARY_OTHER_ACTIVITY_SOURCE_PRESENTATIONS"]
        preference = {"MILLION_VND": 0, "VND": 1}
        ordered = sorted(
            candidates,
            key=lambda item: (
                preference.get(item["mapping"].get("unit"), 9),
                _source_position(item["region"]),
            ),
        )
        best_rank = preference.get(ordered[0]["mapping"].get("unit"), 9)
        if (
            sum(preference.get(item["mapping"].get("unit"), 9) == best_rank for item in ordered)
            != 1
        ):
            return None, ["MULTIPLE_EQUIVALENT_PRIMARY_OTHER_ACTIVITY_PRESENTATIONS"]
        selected = ordered[0]
    alternatives = [
        {
            "economic_vector": list(_economic_vector(item["mapping"], compiled_specs)),
            "locator": canonical_clone_v1(item["projection_receipt"]["locator"]),
            "unit": item["mapping"]["unit"],
        }
        for item in candidates
    ]
    receipt = selected["projection_receipt"]
    material = {
        **{key: canonical_clone_v1(value) for key, value in receipt.items() if key != "receipt_id"},
        "corroborating_presentations": alternatives,
        "selection_rule": (
            "UNIQUE_USABLE_PRIMARY_RESULT_OR_UNIQUE_PREFERRED_MILLION_VND_"
            "AMONG_EXACT_OR_TWO_COMPONENT_INDEPENDENT_DISPLAY_ROUNDING_"
            "COMPATIBLE_PRESENTATIONS"
        ),
    }
    selected["projection_receipt"] = {
        **material,
        "receipt_id": "gjoafav1:primary:" + canonical_json_sha256_v1(material),
    }
    return selected, []


def _financial_note_owner_visible(
    page_records: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
    excluded_row_locator: Mapping[str, Any] | None = None,
) -> bool:
    aliases = set(compiled_specs["topology"]["parent"]["aliases"])
    for record in page_records:
        page = record["page_json"]
        for section_ordinal, section in enumerate(page.get("sections") or [], start=1):
            if type(section) is not dict or section.get("content_kind") == "PRIMARY_STATEMENT":
                continue
            surfaces = [section.get("title_exact")]
            for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
                if type(table) is not dict:
                    continue
                surfaces.append(table.get("title_exact"))
                for row_ordinal, row in enumerate(table.get("rows") or [], start=1):
                    if type(row) is dict:
                        if type(excluded_row_locator) is dict and all(
                            excluded_row_locator.get(key) == value
                            for key, value in {
                                "page_json_version_id": record["page_json_version_id"],
                                "physical_page": record["physical_page"],
                                "row_ordinal": row_ordinal,
                                "section_id": f"s{section_ordinal}",
                                "table_id": f"t{table_ordinal}",
                            }.items()
                        ):
                            continue
                        surfaces.append(row.get("label_exact"))
            if any(
                _without_leading_ordinal(_normalized(surface)) in aliases for surface in surfaces
            ):
                return True
    return False


def _note_query_records(
    page_records: Sequence[Mapping[str, Any]],
    *,
    excluded_row_locator: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    records = [
        canonical_clone_v1(record)
        for record in page_records
        if record["page_json"].get("status") != "PRIMARY_FINANCIAL_STATEMENT"
    ]
    if excluded_row_locator is None:
        return records
    for record in records:
        if record["page_json_version_id"] != excluded_row_locator.get("page_json_version_id"):
            continue
        try:
            _section, table = _source_table(
                record["page_json"],
                section_id=excluded_row_locator["section_id"],
                table_id=excluded_row_locator["table_id"],
            )
            row = table["rows"][excluded_row_locator["row_ordinal"] - 1]
            values = row["values_exact"]
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            raise _error("other-activity unit-control note projection drifted") from exc
        if type(values) is not list or not any(value is not None for value in values):
            raise _error("other-activity unit-control note source drifted")
        row["values_exact"] = [None for _value in values]
    return records


def _recover_authenticated_adjacent_root_receiver(
    *,
    page_records: Sequence[Mapping[str, Any]],
    failed_cluster: Mapping[str, Any],
    source_repair_receipts: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Select one PDF-authenticated root-only receiver the shared query rejects."""

    if failed_cluster.get("status") != UNRESOLVED:
        return None
    relevant = [
        receipt
        for receipt in source_repair_receipts
        if receipt.get("repair", {}).get("repair_kind")
        in {
            "COLUMN_VALUE_KIND_PDF_VISIBLE_MONEY",
            "ROW_KIND_PDF_VISIBLE_TOTAL",
        }
    ]
    if len(relevant) != 2:
        return None
    locators = [receipt["repair"]["locator"] for receipt in relevant]
    if any(locator != locators[0] for locator in locators[1:]):
        return None
    receiver_locator = locators[0]
    receiver_record = next(
        (
            record
            for record in page_records
            if record["page_json_version_id"] == receiver_locator["page_json_version_id"]
        ),
        None,
    )
    if receiver_record is None:
        return None
    try:
        receiver_section, receiver_table = _source_table(
            receiver_record["page_json"],
            section_id=receiver_locator["section_id"],
            table_id=receiver_locator["table_id"],
        )
        receiver_row = receiver_table["rows"][receiver_locator["row_ordinal"] - 1]
    except (IndexError, KeyError, TypeError, ValueError):
        return None
    columns = receiver_table.get("columns")
    values = receiver_row.get("values_exact")
    if (
        receiver_table.get("continuation") != "CONTINUES_FROM_PREVIOUS_PAGE"
        or type(columns) is not list
        or len(columns) < 2
        or any(
            type(column) is not dict
            or column.get("value_kind") != "MONEY"
            or type(column.get("header_path_exact")) is not list
            or any(_normalized(item) for item in column.get("header_path_exact", []))
            for column in columns
        )
        or receiver_row.get("row_kind") != "TOTAL"
        or _normalized(receiver_row.get("label_exact"))
        or type(values) is not list
        or len(values) != len(columns)
        or any(_source_money(value)["coefficient"] is None for value in values)
    ):
        return None
    prior_records = [
        canonical_clone_v1(record)
        for record in page_records
        if record["selected_page_ordinal"] + 1 == receiver_record["selected_page_ordinal"]
        and record["physical_page"] + 1 == receiver_record["physical_page"]
    ]
    if len(prior_records) != 1:
        return None
    prior_cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=prior_records, compiled_specs=compiled_specs
    )
    prior_regions = prior_cluster.get("component_regions")
    if prior_cluster.get("status") != READY or type(prior_regions) is not list or not prior_regions:
        return None
    prior_region = max(prior_regions, key=_source_position)
    if (
        prior_region["selected_page_ordinal"] + 1 != receiver_record["selected_page_ordinal"]
        or prior_region["physical_page"] + 1 != receiver_record["physical_page"]
    ):
        return None
    try:
        _prior_section, prior_table = _source_table(
            next(
                record["page_json"]
                for record in prior_records
                if record["page_json_version_id"] == prior_region["page_json_version_id"]
            ),
            section_id=prior_region["section_id"],
            table_id=prior_region["table_id"],
        )
    except (KeyError, StopIteration, TypeError, ValueError):
        return None
    if prior_table.get("continuation") != "CONTINUES_ON_NEXT_PAGE":
        return None
    receiver_region = {
        key: canonical_clone_v1(receiver_record[key])
        for key in (
            "document_id",
            "document_ordinal",
            "page_json_version_id",
            "physical_page",
            "selected_page_ordinal",
            "source_logical_name",
            "source_sha256",
        )
    } | {
        "component_roles": [],
        "fragment_ordinal": len(prior_regions) + 1,
        "section_id": receiver_locator["section_id"],
        "table_id": receiver_locator["table_id"],
    }
    inventory = canonical_clone_v1(failed_cluster.get("declared_money_table_inventory"))
    if type(inventory) is not list:
        return None
    receiver_inventory = [
        item
        for item in inventory
        if item.get("page_json_version_id") == receiver_region["page_json_version_id"]
        and item.get("section_id") == receiver_region["section_id"]
        and item.get("table_id") == receiver_region["table_id"]
    ]
    if len(receiver_inventory) != 1:
        return None
    receiver_inventory[0]["disposition"] = "SELECTED_FAMILY_COMPONENT"
    regions = _resequence_regions([*prior_regions, receiver_region])
    material = {
        "prior_region": canonical_clone_v1(prior_region),
        "receiver_region": canonical_clone_v1(regions[-1]),
        "receiver_source_values_exact": canonical_clone_v1(values),
        "repair_receipt_ids": sorted(receipt["receipt_id"] for receipt in relevant),
        "rule": (
            "PDF_AUTHENTICATED_ROOT_ONLY_EXPLICIT_ADJACENT_RECEIVER_WITH_"
            "COMPLETE_MONEY_COLUMNS_AND_VISIBLE_TOTAL_ROW"
        ),
    }
    continuation_receipt = {
        **material,
        "receipt_id": "gjoafav1:continuation:" + canonical_json_sha256_v1(material),
    }
    owner = canonical_clone_v1(prior_cluster["owner_receipt"])
    owner["other_activity_authenticated_continuation_receipt"] = continuation_receipt
    return _reseal_cluster(
        failed_cluster,
        component_regions=regions,
        declared_money_table_inventory=inventory,
        owner_receipt=owner,
        reasons=[],
        status=READY,
    )


def recover_gemini_json_other_activity_query_cluster_v1(
    *,
    page_records: Any,
    base_cluster: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Add one exact direct primary result without suppressing a visible note."""

    if compiled_specs.get("topology", {}).get("family_id") != FAMILY_ID:
        raise _error("other-activity adapter received another family")
    if type(page_records) not in {list, tuple} or not page_records:
        raise _error("other-activity page-record axis is invalid")
    projected_records, source_repair_receipts = _apply_source_repairs_to_page_records(
        page_records, compiled_specs=compiled_specs
    )
    primary, primary_reasons = _select_primary(projected_records, compiled_specs=compiled_specs)
    unit_control = (
        primary["projection_receipt"].get("primary_unit_corroboration_receipt")
        if primary is not None
        else None
    )
    excluded_row_locator = (
        unit_control.get("locator")
        if type(unit_control) is dict
        and unit_control.get("control_kind") != "ADJACENT_PRIMARY_STATEMENT_EXPLICIT_UNIT"
        else None
    )
    note_visible = _financial_note_owner_visible(
        projected_records,
        compiled_specs=compiled_specs,
        excluded_row_locator=excluded_row_locator,
    )
    selected_base = canonical_clone_v1(base_cluster)
    if note_visible:
        note_only_records = _note_query_records(
            projected_records, excluded_row_locator=excluded_row_locator
        )
        if note_only_records:
            note_only = coalesce_gemini_json_multitable_hierarchical_document_v1(
                page_records=note_only_records, compiled_specs=compiled_specs
            )
            if note_only.get("status") == UNRESOLVED:
                recovered = _recover_authenticated_adjacent_root_receiver(
                    page_records=note_only_records,
                    failed_cluster=note_only,
                    source_repair_receipts=source_repair_receipts,
                    compiled_specs=compiled_specs,
                )
                if recovered is None:
                    return note_only
                note_only = recovered
            if note_only.get("status") == READY:
                selected_base = note_only
            elif note_only.get("status") == NOT_OBSERVED:
                note_visible = False
    base_status = selected_base.get("status")

    if base_status == UNRESOLVED:
        if note_visible:
            return canonical_clone_v1(selected_base)
        if primary is None:
            return (
                _reseal_cluster(selected_base, reasons=primary_reasons)
                if primary_reasons
                else canonical_clone_v1(selected_base)
            )
        note_regions: list[dict[str, Any]] = []
    elif base_status == NOT_OBSERVED:
        if primary is None:
            return (
                _reseal_cluster(
                    selected_base,
                    component_regions=[],
                    reasons=primary_reasons,
                    status=UNRESOLVED,
                )
                if primary_reasons
                else canonical_clone_v1(selected_base)
            )
        note_regions = []
    elif base_status == READY:
        note_regions = [
            canonical_clone_v1(region)
            for region in selected_base["component_regions"]
            if primary is None
            or (
                region["page_json_version_id"],
                region["section_id"],
                region["table_id"],
            )
            != (
                primary["region"]["page_json_version_id"],
                primary["region"]["section_id"],
                primary["region"]["table_id"],
            )
        ]
        if not note_visible and primary is not None:
            note_regions = []
        if primary is None:
            return canonical_clone_v1(selected_base)
    else:
        raise _error("other-activity base query disposition is invalid")

    assert primary is not None
    regions = _resequence_regions([*note_regions, primary["region"]])
    primary_key = (
        primary["region"]["page_json_version_id"],
        primary["region"]["section_id"],
        primary["region"]["table_id"],
    )
    primary_region = next(
        region
        for region in regions
        if (region["page_json_version_id"], region["section_id"], region["table_id"]) == primary_key
    )
    note_regions = [region for region in regions if region is not primary_region]
    material = {
        "adapter_format_version": ADAPTER_FORMAT_VERSION,
        "authenticated_continuation_receipt": canonical_clone_v1(
            (selected_base.get("owner_receipt") or {}).get(
                "other_activity_authenticated_continuation_receipt"
            )
        ),
        "note_regions": canonical_clone_v1(note_regions),
        "primary_projection_receipt": canonical_clone_v1(primary["projection_receipt"]),
        "primary_region": canonical_clone_v1(primary_region),
        "source_repair_receipts": canonical_clone_v1(source_repair_receipts),
        "rule": (
            "DIRECT_NOTE_POPULATION_PLUS_EXACT_PRIMARY_SOURCE_RESULT"
            if note_regions
            else "EXACT_PRIMARY_SOURCE_RESULT_AFTER_NOTE_NOT_OBSERVED"
        ),
    }
    adapter_receipt = {
        **material,
        "receipt_id": "gjoafav1:query:" + canonical_json_sha256_v1(material),
    }
    owner = canonical_clone_v1(selected_base.get("owner_receipt"))
    if type(owner) is not dict:
        owner = {
            "alias": "EXACT_PRIMARY_STATEMENT_SOURCE_RESULT_FALLBACK",
            "leading_component_positions": [],
            "leading_component_rule": "FAMILY_LOCAL_EXACT_PRIMARY_SOURCE_RESULT",
            "outline_top_level_number": None,
            "position": list(_source_position(primary_region)),
            "source_exact": None,
        }
    owner["other_activity_query_adapter_receipt"] = adapter_receipt
    return _reseal_cluster(
        selected_base,
        component_regions=regions,
        owner_receipt=owner,
        reasons=[],
        status=READY,
    )


def adapt_gemini_json_other_activity_indexed_query_evidence_v1(
    *,
    indexed_query_evidence: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild the indexed axis after deterministic Family-38 augmentation."""

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
            raise _error("other-activity indexed replay page is absent")
        records_by_ordinal.setdefault(axis["document_ordinal"], []).append(
            {**canonical_clone_v1(axis), "page_json": page}
        )
    clusters = []
    for document in checked["selected_document_axis"]:
        ordinal = document["document_ordinal"]
        clusters.append(
            recover_gemini_json_other_activity_query_cluster_v1(
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


def build_gemini_json_other_activity_region_query_receipt_v1(
    regions: Any, *, cluster: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    shared = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
    adapter = None
    if cluster is not None and type(cluster.get("owner_receipt")) is dict:
        adapter = cluster["owner_receipt"].get("other_activity_query_adapter_receipt")
    material = {
        "adapter_receipt": canonical_clone_v1(adapter),
        "format_version": QUERY_RECEIPT_FORMAT_VERSION,
        "shared_query_receipt": shared,
    }
    return {
        **material,
        "query_receipt_id": "gjoafav1:query-receipt:" + canonical_json_sha256_v1(material),
    }


def _validate_query_receipt(value: Any, *, regions: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise _error("other-activity query receipt is invalid")
    expected_shared = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
    if (
        set(value)
        != {
            "adapter_receipt",
            "format_version",
            "query_receipt_id",
            "shared_query_receipt",
        }
        or value.get("format_version") != QUERY_RECEIPT_FORMAT_VERSION
        or not same_typed_json_v1(value.get("shared_query_receipt"), expected_shared)
    ):
        raise _error("other-activity query receipt does not bind exact fragments")
    material = {key: value[key] for key in value if key != "query_receipt_id"}
    if value["query_receipt_id"] != "gjoafav1:query-receipt:" + canonical_json_sha256_v1(material):
        raise _error("other-activity query receipt identity does not replay")
    return canonical_clone_v1(value)


def _project_primary_page(
    pages: dict[str, dict[str, Any]],
    receipt: Mapping[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    locator = receipt.get("locator")
    if (
        type(locator) is not dict
        or receipt.get("statement_type_before") != "INCOME_STATEMENT"
        or receipt.get("statement_type_after") != "BALANCE_SHEET"
    ):
        raise _error("other-activity primary projection receipt is invalid")
    version_id = locator.get("page_json_version_id")
    page = pages.get(version_id)
    if type(page) is not dict or canonical_json_sha256_v1(page) != receipt.get(
        "before_page_json_sha256"
    ):
        raise _error("other-activity primary projection source drifted")
    try:
        section = page["sections"][int(locator["section_id"][1:]) - 1]
        table = section["tables"][int(locator["table_id"][1:]) - 1]
        row = table["rows"][locator["row_ordinal"] - 1]
    except (IndexError, KeyError, TypeError, ValueError) as exc:
        raise _error("other-activity primary projection locator is invalid") from exc
    if (
        page.get("status") != "PRIMARY_FINANCIAL_STATEMENT"
        or section.get("content_kind") != "PRIMARY_STATEMENT"
        or section.get("statement_type") != "INCOME_STATEMENT"
        or row.get("label_exact") != receipt.get("label_exact")
    ):
        raise _error("other-activity primary projection semantic source drifted")
    if receipt.get("primary_unit_corroboration_receipt") is not None:
        raise _error("other-activity borrowed primary unit is not source-owned")
    if not _unit_axis(table, compiled_specs=compiled_specs, document_unit_context=None).get("complete"):
        raise _error("other-activity primary unit is not locally source-owned")
    section["statement_type"] = "BALANCE_SHEET"
    suppressed = receipt.get("suppressed_nonfamily_row_ordinals")
    if type(suppressed) is not list or suppressed != sorted(set(suppressed)):
        raise _error("other-activity primary row-scope projection is invalid")
    for row_ordinal in suppressed:
        try:
            other_row = table["rows"][row_ordinal - 1]
            values = other_row["values_exact"]
        except (IndexError, KeyError, TypeError) as exc:
            raise _error("other-activity primary row-scope source drifted") from exc
        if type(values) is not list or not any(value is not None for value in values):
            raise _error("other-activity primary row-scope source drifted")
        other_row["values_exact"] = [None for _value in values]
    if canonical_json_sha256_v1(page) != receipt.get("after_page_json_sha256"):
        raise _error("other-activity primary projection output drifted")
    material = {
        key: canonical_clone_v1(value) for key, value in receipt.items() if key != "receipt_id"
    }
    if receipt.get("receipt_id") != "gjoafav1:primary:" + canonical_json_sha256_v1(material):
        raise _error("other-activity primary projection identity drifted")
    return pages


def _mapping_vector(mapping: Mapping[str, Any]) -> tuple[int | None, ...]:
    values = mapping.get("values")
    if type(values) is not list:
        return ()
    return tuple(cell.get("coefficient") for cell in values)


def _source_root_rows(
    *,
    table: Mapping[str, Any],
    section: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
    fallback_money_ordinals: Sequence[int] | None = None,
) -> list[tuple[int, tuple[int | None, ...]]]:
    lane = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
    money_ordinals = lane.get("money_column_ordinals")
    if not lane.get("complete") and fallback_money_ordinals is None:
        return []
    if not lane.get("complete"):
        money_ordinals = list(fallback_money_ordinals or [])
    rows = table.get("rows")
    aliases = set(compiled_specs["topology"]["parent"]["aliases"])
    visible_ordinals = []
    parsed_by_ordinal = {}
    for ordinal, row in enumerate(rows if type(rows) is list else [], start=1):
        if type(row) is not dict or type(row.get("values_exact")) is not list:
            continue
        values = row["values_exact"]
        money = money_ordinals
        if any(column > len(values) for column in money):
            continue
        parsed = tuple(_source_money(values[column - 1])["coefficient"] for column in money)
        if any(value is not None for value in parsed):
            visible_ordinals.append(ordinal)
            parsed_by_ordinal[ordinal] = parsed
    terminal = max(visible_ordinals, default=None)
    matches = []
    for ordinal, parsed in parsed_by_ordinal.items():
        row = rows[ordinal - 1]
        exact_root = _without_leading_ordinal(_normalized(row.get("label_exact"))) in aliases
        terminal_total = bool(
            ordinal == terminal
            and (
                row.get("row_kind") in {"SUBTOTAL", "TOTAL"}
                or not _normalized(row.get("label_exact"))
            )
        )
        if exact_root or terminal_total:
            matches.append((ordinal, parsed))
    return matches


def _unit_control_match(
    *,
    primary_unit: str,
    primary_vector: tuple[int | None, ...],
    note_vector: tuple[int | None, ...],
    target_unit: str,
) -> bool:
    if (
        not primary_vector
        or len(primary_vector) != len(note_vector)
        or any(value is None for value in primary_vector)
        or any(value is None for value in note_vector)
    ):
        return False
    if primary_unit == target_unit:
        return primary_vector == note_vector
    return bool(
        primary_unit == "VND"
        and target_unit == "MILLION_VND"
        and all(
            abs(source - displayed * 1_000_000) <= 500_000
            for source, displayed in zip(primary_vector, note_vector, strict=True)
        )
    )


def _source_presentations_compatible(
    left: Mapping[str, Any], right: Mapping[str, Any], compiled_specs: Mapping[str, Any]
) -> bool:
    if _economic_vector(left, compiled_specs) == _economic_vector(right, compiled_specs):
        return True
    left_unit = left.get("unit")
    right_unit = right.get("unit")
    left_vector = _mapping_vector(left)
    right_vector = _mapping_vector(right)
    if left_unit == "VND":
        return _unit_control_match(
            primary_unit=left_unit,
            primary_vector=left_vector,
            note_vector=right_vector,
            target_unit=right_unit,
        )
    if right_unit == "VND":
        return _unit_control_match(
            primary_unit=right_unit,
            primary_vector=right_vector,
            note_vector=left_vector,
            target_unit=left_unit,
        )
    return False


def _continuation_chain(tables: Sequence[Mapping[str, Any]]) -> bool:
    if len(tables) <= 1:
        return True
    for prior, current in zip(tables, tables[1:], strict=False):
        if (
            prior.get("continuation") != "CONTINUES_ON_NEXT_PAGE"
            or current.get("continuation") != "CONTINUES_FROM_PREVIOUS_PAGE"
        ):
            return False
    return True


def _scope_repeated_owner_header_prefix(
    *,
    region: Mapping[str, Any],
    section: Mapping[str, Any],
    table: dict[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    before_axis = _unit_axis(table, compiled_specs=compiled_specs, document_unit_context=None)
    if before_axis.get("complete") or not _normalized(table.get("unit_exact")):
        return None
    lane = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
    scope = lane.get("source_period_axis", {}).get("header_path_scope_receipt")
    prefix = scope.get("common_prefix_exact") if type(scope) is dict else None
    suffixes = scope.get("money_column_suffixes_exact") if type(scope) is dict else None
    money_ordinals = lane.get("money_column_ordinals")
    if (
        not lane.get("complete")
        or type(prefix) is not list
        or not prefix
        or type(suffixes) is not dict
        or type(money_ordinals) is not list
    ):
        return None
    projected = canonical_clone_v1(table)
    header_projections = []
    for ordinal in money_ordinals:
        column = projected["columns"][ordinal - 1]
        before_path = column.get("header_path_exact")
        after_path = suffixes.get(f"c{ordinal}")
        if (
            type(before_path) is not list
            or before_path[: len(prefix)] != prefix
            or type(after_path) is not list
            or not after_path
            or before_path[len(prefix) :] != after_path
        ):
            return None
        column["header_path_exact"] = canonical_clone_v1(after_path)
        header_projections.append(
            {
                "after_header_path_exact": canonical_clone_v1(after_path),
                "before_header_path_exact": canonical_clone_v1(before_path),
                "column_ordinal": ordinal,
            }
        )
    after_axis = _unit_axis(projected, compiled_specs=compiled_specs, document_unit_context=None)
    if not after_axis.get("complete") or after_axis.get("source") != "LOCAL_TABLE_UNIT":
        return None
    before_sha = canonical_json_sha256_v1(table)
    table.clear()
    table.update(projected)
    material = {
        "canonical_unit": after_axis["canonical_unit"],
        "header_projections": header_projections,
        "locator": {
            key: region[key]
            for key in ("page_json_version_id", "physical_page", "section_id", "table_id")
        },
        "projected_table_sha256": canonical_json_sha256_v1(table),
        "rule": (
            "EXACT_REPEATED_OWNER_HEADER_PREFIX_SCOPED_OUT_BEFORE_UNIT_MATCH_"
            "EXPLICIT_TABLE_UNIT_REMAINS_AUTHORITATIVE"
        ),
        "source_table_sha256": before_sha,
        "unit_exact": table["unit_exact"],
    }
    return {
        **material,
        "receipt_id": "gjoafav1:unit-scope:" + canonical_json_sha256_v1(material),
    }


def _project_note_unit(
    *,
    pages: dict[str, dict[str, Any]],
    note_regions: Sequence[Mapping[str, Any]],
    primary_mapping: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Retain printed note units; never populate a unit from PRIMARY values."""
    receipts = []
    for region in note_regions:
        section, table = _source_table(pages[region["page_json_version_id"]],
            section_id=region["section_id"], table_id=region["table_id"])
        scope = _scope_repeated_owner_header_prefix(region=region, section=section,
            table=table, compiled_specs=compiled_specs)
        if scope is not None:
            receipts.append(scope)
    return pages, receipts


def _row_source_cells(
    row: Mapping[str, Any], money_column_ordinals: Sequence[int]
) -> list[dict[str, Any]] | None:
    values = row.get("values_exact")
    if (
        type(values) is not list
        or not money_column_ordinals
        or any(ordinal > len(values) for ordinal in money_column_ordinals)
    ):
        return None
    return [_source_money(values[ordinal - 1]) for ordinal in money_column_ordinals]


def _project_exact_unlabeled_structural_subtotals(
    *,
    pages: dict[str, dict[str, Any]],
    note_regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Omit only proven nonterminal unlabeled context totals on a private clone."""

    if (
        compiled_specs["other_activity_adapter_spec"]["unlabeled_structural_subtotal_policy"]
        != "EXACT_NONTERMINAL_CONTIGUOUS_SOURCE_COMPONENT_SUM_PRIVATE_OMISSION"
    ):
        raise _error("other-activity unlabeled subtotal policy drifted")
    receipts = []
    for region in note_regions:
        page = pages[region["page_json_version_id"]]
        section, table = _source_table(
            page, section_id=region["section_id"], table_id=region["table_id"]
        )
        lane = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
        money_ordinals = lane.get("money_column_ordinals")
        rows = table.get("rows")
        if not lane.get("complete") or type(money_ordinals) is not list or type(rows) is not list:
            continue
        for subtotal_index, row in enumerate(rows):
            if (
                type(row) is not dict
                or row.get("row_kind") != "SUBTOTAL"
                or _normalized(row.get("label_exact"))
            ):
                continue
            result_cells = _row_source_cells(row, money_ordinals)
            if result_cells is None or any(
                observed_source_coefficient_v1(cell) is None for cell in result_cells
            ):
                continue
            later_visible = False
            for later in rows[subtotal_index + 1 :]:
                if type(later) is not dict:
                    continue
                cells = _row_source_cells(later, money_ordinals)
                if cells is not None and any(
                    observed_source_coefficient_v1(cell) is not None for cell in cells
                ):
                    later_visible = True
                    break
            if not later_visible:
                continue
            component_indices = []
            for prior_index in range(subtotal_index - 1, -1, -1):
                prior = rows[prior_index]
                if type(prior) is not dict:
                    break
                cells = _row_source_cells(prior, money_ordinals)
                if cells is None:
                    break
                observed = [observed_source_coefficient_v1(cell) for cell in cells]
                if all(value is None for value in observed):
                    break
                if not _normalized(prior.get("label_exact")):
                    break
                component_indices.append(prior_index)
            component_indices.reverse()
            if len(component_indices) < 2:
                continue
            component_cells = [
                _row_source_cells(rows[index], money_ordinals) for index in component_indices
            ]
            if any(cells is None for cells in component_cells):
                continue
            lane_receipts = additive_source_lane_receipts_v1(
                result_cells=result_cells,
                component_cell_vectors=component_cells,  # type: ignore[arg-type]
            )
            if any(item["status"] != "EXACT_OBSERVED_SOURCE_LANE" for item in lane_receipts):
                continue
            before_sha = canonical_json_sha256_v1(table)
            before_values = canonical_clone_v1(row["values_exact"])
            before_row_kind = row["row_kind"]
            for ordinal in money_ordinals:
                row["values_exact"][ordinal - 1] = None
            row["row_kind"] = "UNKNOWN"
            material = {
                "after_table_sha256": canonical_json_sha256_v1(table),
                "before_table_sha256": before_sha,
                "component_row_ordinals": [index + 1 for index in component_indices],
                "lane_receipts": lane_receipts,
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
                "rule": (
                    "EXACT_OBSERVED_NONTERMINAL_UNLABELED_STRUCTURAL_SUBTOTAL_"
                    "EQUALS_CONTIGUOUS_SOURCE_COMPONENT_SUM_PRIVATE_OMISSION_"
                    "NO_VALUE_OR_BLANK_INFERENCE"
                ),
                "source_row_kind": before_row_kind,
                "source_values_exact": before_values,
                "subtotal_row_ordinal": subtotal_index + 1,
                "structural_row_kind_after": "UNKNOWN",
            }
            receipts.append(
                {
                    **material,
                    "receipt_id": "gjoafav1:subtotal:" + canonical_json_sha256_v1(material),
                }
            )
    return pages, receipts


def _direct_source_root(mapping: Mapping[str, Any]) -> bool:
    return bool(
        mapping.get("role") == "FAMILY_ROOT_TOTAL"
        and type(mapping.get("state")) is str
        and mapping["state"].startswith("SOURCE_VISIBLE")
        and mapping.get("source_refs")
    )


def _align_mapping_locators(
    mappings: Sequence[Mapping[str, Any]], regions: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """Bind separately evaluated source refs back to the combined region axis."""

    by_key = {
        (region["page_json_version_id"], region["section_id"], region["table_id"]): region
        for region in regions
    }
    output = []
    for source_mapping in mappings:
        mapping = canonical_clone_v1(source_mapping)
        for source_ref in mapping.get("source_refs", []):
            locator = source_ref.get("locator")
            if type(locator) is not dict:
                continue
            region = by_key.get(
                (
                    locator.get("page_json_version_id"),
                    locator.get("section_id"),
                    locator.get("table_id"),
                )
            )
            if region is None:
                raise _error("other-activity mapping source is outside the combined query")
            source_ref["locator"] = canonical_clone_v1(region)
        material = {key: value for key, value in mapping.items() if key != "item_mapping_id"}
        mapping["item_mapping_id"] = "gjmthfmv1:item:" + canonical_json_sha256_v1(material)
        output.append(mapping)
    return output


def _reseal_candidate(
    candidate: Mapping[str, Any],
    *,
    regions: Sequence[Mapping[str, Any]],
    query_receipt: Mapping[str, Any],
    strategy: str,
    primary_candidate: Mapping[str, Any] | None,
    note_candidate: Mapping[str, Any] | None,
    unit_receipts: Sequence[Mapping[str, Any]],
    structural_receipts: Sequence[Mapping[str, Any]] = (),
    mappings: Sequence[Mapping[str, Any]] | None = None,
    reasons: Sequence[str] | None = None,
) -> dict[str, Any]:
    output = canonical_clone_v1(candidate)
    output["claim_boundary"] = CLAIM_BOUNDARY
    output["component_regions"] = canonical_clone_v1(regions)
    if mappings is not None:
        output["mappings"] = _align_mapping_locators(mappings, regions)
    if reasons is not None:
        output["reasons"] = sorted(set(reasons))
        output["status"] = UNRESOLVED if output["reasons"] else READY
        if output["status"] == UNRESOLVED:
            output["mappings"] = []
    retired_note_root_authority = None
    direct_primary_root_mapping_id = None
    if mappings is not None:
        primary_roots = [mapping for mapping in output["mappings"]
            if mapping.get("role") == "FAMILY_ROOT_TOTAL"
            and mapping.get("state") == "SOURCE_VISIBLE_PRIMARY_STATEMENT_EXACT_RESULT"]
        if len(primary_roots) == 1:
            retired_note_root_authority = _retire_root_authority_v1(output,
                root_mappings_before=[mapping for mapping in candidate.get("mappings", []) if mapping.get("role") == "FAMILY_ROOT_TOTAL"])
            direct_primary_root_mapping_id = primary_roots[0]["item_mapping_id"]
            structural_root = output["closure_receipt"]["structural_root_receipt"]
            structural_root["emitted_mapping"] = output["status"] == READY
            structural_root["source_root_mapping_id"] = direct_primary_root_mapping_id
            structural_root["active_permission"] = "F38_DIRECT_PRIMARY_SOURCE_ROOT"
    output["closure_receipt"]["query_receipt"] = canonical_clone_v1(
        query_receipt["shared_query_receipt"]
    )
    material = {
        "adapter_format_version": ADAPTER_FORMAT_VERSION,
        "note_candidate_id": (
            note_candidate.get("candidate_id") if type(note_candidate) is Mapping else None
        ),
        "primary_candidate_id": (
            primary_candidate.get("candidate_id") if type(primary_candidate) is Mapping else None
        ),
        "strategy": strategy,
        "retired_note_root_authority": retired_note_root_authority,
        "direct_primary_root_mapping_id": direct_primary_root_mapping_id,
        "structural_projection_receipts": canonical_clone_v1(list(structural_receipts)),
        "unit_corroboration_receipts": canonical_clone_v1(list(unit_receipts)),
    }
    output["closure_receipt"]["other_activity_adapter_receipt"] = {
        **material,
        "receipt_id": "gjoafav1:candidate:" + canonical_json_sha256_v1(material),
    }
    output_material = {key: value for key, value in output.items() if key != "candidate_id"}
    output["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(output_material)
    return output


def _evaluate_source_projected_cluster_v1(
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate direct note rows and bind the root to a printed source result."""

    checked = _validate_query_receipt(query_receipt, regions=regions)
    region_axis = checked["shared_query_receipt"]["region_axis"]
    adapter = checked["adapter_receipt"]
    if adapter is None:
        candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
            regions=region_axis,
            page_json_by_version=page_json_by_version,
            compiled_specs=compiled_specs,
            query_receipt=checked["shared_query_receipt"],
        )
        roots = [
            mapping
            for mapping in candidate.get("mappings", [])
            if mapping.get("role") == "FAMILY_ROOT_TOTAL"
        ]
        if candidate.get("status") == READY and len(roots) == 1 and _direct_source_root(roots[0]):
            return _reseal_candidate(
                candidate,
                regions=region_axis,
                query_receipt=checked,
                strategy="DIRECT_NOTE_SOURCE_PRESENTATION",
                primary_candidate=None,
                note_candidate=candidate,
                unit_receipts=[],
            )
        return _reseal_candidate(
            candidate,
            regions=region_axis,
            query_receipt=checked,
            strategy="DIRECT_NOTE_ROOT_NOT_PROVEN",
            primary_candidate=None,
            note_candidate=candidate,
            unit_receipts=[],
            reasons=[*candidate.get("reasons", []), "DIRECT_SOURCE_FAMILY_ROOT_NOT_PROVEN"],
        )

    expected_material = {
        key: canonical_clone_v1(value) for key, value in adapter.items() if key != "receipt_id"
    }
    if adapter.get("receipt_id") != "gjoafav1:query:" + canonical_json_sha256_v1(expected_material):
        raise _error("other-activity adapter query receipt drifted")
    note_regions = _resequence_regions(adapter["note_regions"])
    primary_region = _resequence_regions([adapter["primary_region"]])[0]
    pages = {
        version_id: canonical_clone_v1(page) for version_id, page in page_json_by_version.items()
    }
    pages = _apply_source_repair_receipts_to_pages(pages, adapter.get("source_repair_receipts"))
    pages = _project_primary_page(
        pages,
        adapter["primary_projection_receipt"],
        compiled_specs=compiled_specs,
    )
    primary_candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=[primary_region],
        page_json_by_version=pages,
        compiled_specs=compiled_specs["other_activity_primary_specs"],
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            [primary_region]
        ),
    )
    primary_roots = [
        mapping for mapping in primary_candidate.get("mappings", []) if _direct_source_root(mapping)
    ]
    if primary_candidate.get("status") != READY or len(primary_roots) != 1:
        return _reseal_candidate(
            primary_candidate,
            regions=region_axis,
            query_receipt=checked,
            strategy="PRIMARY_SOURCE_RESULT_NOT_REPLAYABLE",
            primary_candidate=primary_candidate,
            note_candidate=None,
            unit_receipts=[],
            reasons=["PRIMARY_OTHER_ACTIVITY_SOURCE_RESULT_NOT_LOCALLY_USABLE"],
        )
    primary_root = primary_roots[0]
    if not note_regions:
        return _reseal_candidate(
            primary_candidate,
            regions=region_axis,
            query_receipt=checked,
            strategy="DIRECT_PRIMARY_SOURCE_RESULT_AFTER_NOTE_NOT_OBSERVED",
            primary_candidate=primary_candidate,
            note_candidate=None,
            unit_receipts=[],
        )

    pages, unit_receipts = _project_note_unit(
        pages=pages,
        note_regions=note_regions,
        primary_mapping=primary_root,
        compiled_specs=compiled_specs,
    )
    pages, structural_receipts = _project_exact_unlabeled_structural_subtotals(
        pages=pages,
        note_regions=note_regions,
        compiled_specs=compiled_specs,
    )
    note_query = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(note_regions)
    note_candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=note_regions,
        page_json_by_version=pages,
        compiled_specs=compiled_specs,
        query_receipt=note_query,
    )
    if note_candidate.get("status") != READY:
        direct_detail = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
            regions=note_regions,
            page_json_by_version=pages,
            compiled_specs=compiled_specs["other_activity_direct_detail_specs"],
            query_receipt=note_query,
        )
        if direct_detail.get("status") == READY:
            note_candidate = direct_detail
    if note_candidate.get("status") != READY:
        return _reseal_candidate(
            note_candidate,
            regions=region_axis,
            query_receipt=checked,
            strategy="VISIBLE_NOTE_POPULATION_NOT_SCHEMA_MAPPABLE",
            primary_candidate=primary_candidate,
            note_candidate=note_candidate,
            unit_receipts=unit_receipts,
            structural_receipts=structural_receipts,
            reasons=note_candidate.get("reasons", []),
        )
    note_roots = [
        mapping
        for mapping in note_candidate["mappings"]
        if mapping.get("role") == "FAMILY_ROOT_TOTAL"
    ]
    direct_note_roots = [mapping for mapping in note_roots if _direct_source_root(mapping)]
    if direct_note_roots and (
        len(direct_note_roots) != 1
        or not _source_presentations_compatible(direct_note_roots[0], primary_root, compiled_specs)
    ):
        return _reseal_candidate(
            note_candidate,
            regions=region_axis,
            query_receipt=checked,
            strategy="NOTE_PRIMARY_SOURCE_RESULT_CONFLICT",
            primary_candidate=primary_candidate,
            note_candidate=note_candidate,
            unit_receipts=unit_receipts,
            structural_receipts=structural_receipts,
            reasons=["NOTE_AND_PRIMARY_OTHER_ACTIVITY_SOURCE_RESULT_CONFLICT"],
        )
    mappings = [
        mapping
        for mapping in note_candidate["mappings"]
        if mapping.get("role") != "FAMILY_ROOT_TOTAL"
    ] + [primary_root]
    if len({mapping["role"] for mapping in mappings}) != len(mappings):
        return _reseal_candidate(
            note_candidate,
            regions=region_axis,
            query_receipt=checked,
            strategy="DUPLICATE_DIRECT_NOTE_ROLE",
            primary_candidate=primary_candidate,
            note_candidate=note_candidate,
            unit_receipts=unit_receipts,
            structural_receipts=structural_receipts,
            reasons=["DUPLICATE_DIRECT_OTHER_ACTIVITY_MAPPING_ROLE"],
        )
    return _reseal_candidate(
        note_candidate,
        regions=region_axis,
        query_receipt=checked,
        strategy="DIRECT_NOTE_DETAILS_PLUS_DIRECT_PRIMARY_SOURCE_RESULT",
        primary_candidate=primary_candidate,
        note_candidate=note_candidate,
        unit_receipts=unit_receipts,
        structural_receipts=structural_receipts,
        mappings=mappings,
        reasons=[],
    )


_UNPROVEN_MIXED_ROLE_LABELS_V1 = (
    "Thu bán tài sản gán nợ",
    "Thu từ bán tài sản gán nợ",
    "Thu nhập từ thanh lý tài sản gán xiết nợ",
    "Thu nhập từ thanh lý tài sản gán nợ",
    "Chi từ thanh lý tài sản gán nợ",
    "Thu nhập từ bán nhà cửa vật kiến trúc và quyền sử dụng đất (*)",
    "Giá vốn từ bán nhà cửa vật kiến trúc và quyền sử dụng đất (*)",
    "Thu từ thanh lý TSCĐ, công cụ lao động",
    "Thu hồi các khoản nợ đã được xử lý rủi ro và từ nghiệp vụ mua bán nợ",
)
_SOURCE_IDENTITY_FIELDS_V1 = (
    "document_id", "document_ordinal", "source_logical_name", "source_sha256",
    "page_json_version_id", "selected_page_ordinal", "physical_page", "section_id", "table_id",
)
_SOURCE_GENERIC_TOTAL_LABELS_V1 = {"tong", "cong", "tong cong", "tong so", "total", "subtotal"}


def _inactive_evidence_envelope_v1(value: Any) -> dict[str, Any]:
    """Keep exact retired JSON outside the recursive active-mapping shape."""
    raw = canonical_json_bytes_v1(value)
    return {"format_version": "F38_INACTIVE_CANONICAL_JSON_UTF8_TEXT_V1",
        "canonical_json_one_lf_utf8_text": raw.decode("utf-8"),
        "sha256": canonical_json_sha256_v1(value), "size_bytes": len(raw)}


def _source_identity_v1(region: Mapping[str, Any]) -> tuple[Any, ...]:
    return tuple(region.get(field) for field in _SOURCE_IDENTITY_FIELDS_V1)


def _retire_root_authority_v1(
    candidate: dict[str, Any], *, root_mappings_before: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    closure = candidate["closure_receipt"]
    root_kind = "EXACT_COMPLETE_TOP_LEVEL_COMPONENT_SUM_DERIVES_FAMILY_ROOT"
    retired = _inactive_evidence_envelope_v1({
        "root_mappings_before": canonical_clone_v1(root_mappings_before),
        "global_root_equations": [equation for equation in closure["equations"] if equation.get("equation_kind") == root_kind],
        "root_component_sum_receipts": closure.get("root_component_sum_receipts", []),
        "structural_root_receipt_before": closure["structural_root_receipt"]})
    closure["equations"] = [equation for equation in closure["equations"] if equation.get("equation_kind") != root_kind]
    if "root_component_sum_receipts" in closure:
        closure["root_component_sum_receipts"] = []
    return retired


def _source_owned_continuation_unit_context_v1(
    prior: Mapping[str, Any] | None, current: Mapping[str, Any], *, compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """A continued source table carries its printed unit, without amount tests."""
    if prior is None:
        return None
    before, after = prior["region"], current["region"]
    page, section, table = current["page"], current["section"], current["table"]
    old_page, old_section, old_table = prior["page"], prior["section"], prior["table"]
    local_unit, old_unit = current["scoped_axis"], prior["scoped_axis"]
    source_fields = ("document_id", "document_ordinal", "source_logical_name", "source_sha256")
    aliases = {_without_leading_ordinal(_normalized(value)) for value in compiled_specs["topology"]["parent"]["aliases"]}
    owner_surfaces = [old_table.get("title_exact")]
    if len(old_section.get("tables") or []) == 1:
        owner_surfaces.append(old_section.get("title_exact"))
    if (page.get("status") != "FINANCIAL_NOTE_CONTENT" or old_page.get("status") != "FINANCIAL_NOTE_CONTENT"
            or section.get("content_kind") != "FINANCIAL_NOTE" or old_section.get("content_kind") != "FINANCIAL_NOTE"
            or section.get("statement_type") != "NOT_APPLICABLE" or old_section.get("statement_type") != "NOT_APPLICABLE"
            or any(before.get(field) != after.get(field) for field in source_fields)
            or after["selected_page_ordinal"] != before["selected_page_ordinal"] + 1
            or after["physical_page"] != before["physical_page"] + 1
            or old_section is not old_page["sections"][-1] or old_table is not old_section["tables"][-1]
            or section is not page["sections"][0] or table is not section["tables"][0]
            or old_table.get("continuation") != "CONTINUES_ON_NEXT_PAGE"
            or table.get("continuation") != "CONTINUES_FROM_PREVIOUS_PAGE"
            or not any(_without_leading_ordinal(_normalized(value)) in aliases for value in owner_surfaces)
            or _normalized(table.get("title_exact"))
            or _normalized(section.get("title_exact")) not in {"", "thuyet minh"}
            or not old_unit.get("complete") or local_unit.get("complete")
            or local_unit.get("evidence") or local_unit.get("undeclared_evidence")
            or _normalized(table.get("unit_exact"))):
        return None
    old_receipt, receipt = prior["table_receipt"], current["table_receipt"]
    if type(old_receipt) is not dict or type(receipt) is not dict:
        return None
    old_axis, axis = old_receipt["lane_axis"], receipt["lane_axis"]
    if (old_axis.get("complete") is not True or axis.get("complete") is not True
            or old_axis.get("lane_keys") != axis.get("lane_keys")
            or old_axis.get("source_lane_keys") != axis.get("source_lane_keys")
            or old_axis.get("money_column_ordinals") != axis.get("money_column_ordinals")):
        return None
    ordinals = axis["money_column_ordinals"]
    current_columns = current["semantic_table"]["columns"]
    old_columns = prior["semantic_table"]["columns"]
    current_headers = [current_columns[ordinal - 1].get("header_path_exact") for ordinal in ordinals]
    old_headers = [old_columns[ordinal - 1].get("header_path_exact") for ordinal in ordinals]
    inherited = axis.get("source_period_axis", {}).get("inherited_from_locator")
    blank_inherited = bool(current_headers and all(header == [None] for header in current_headers)
        and type(inherited) is dict and _source_identity_v1(inherited) == _source_identity_v1(before))
    local_axis = _multitable_lane_axis(current["semantic_section"], current["semantic_table"], compiled_specs=compiled_specs)
    repeated_local = bool(local_axis.get("complete") and current_headers == old_headers
        and local_axis.get("lane_keys") == old_axis.get("lane_keys")
        and local_axis.get("source_lane_keys") == old_axis.get("source_lane_keys"))
    if not (blank_inherited or repeated_local):
        return None
    return {"rule": "SOURCE_OWNED_EXPLICIT_CONTINUED_TABLE_UNIT_SCOPE_NO_AMOUNT_PERMISSION",
        "prior_locator": canonical_clone_v1(before), "receiver_locator": canonical_clone_v1(after),
        "prior_source_table_sha256": canonical_json_sha256_v1(old_table),
        "prior_local_printed_unit_axis": canonical_clone_v1(old_unit),
        "canonical_unit": old_unit["canonical_unit"],
        "period_source_axis": canonical_clone_v1(axis.get("source_period_axis")),
        "period_proof_kind": "EXACT_INHERITED_BLANK_HEADERS" if blank_inherited else "EXACT_REPEATED_LOCAL_HEADERS"}


def _apply_source_role_unit_control_v1(
    candidate: Mapping[str, Any], *, regions: Sequence[Mapping[str, Any]],
    pages: Mapping[str, dict[str, Any]], compiled_specs: Mapping[str, Any],
    semantic_pages: Mapping[str, dict[str, Any]], source_repair_receipts: Any,
) -> dict[str, Any]:
    """Source permission precedes amount closure; unsupported scope holds all.

    This checks the original selected tables, before private projection. A
    schema ambiguity never splits a source value, and another table's unit
    never supplies a missing note/PRIMARY unit.
    """
    reasons, fragments, mixed_rows = [], [], []
    units_by_source = {}
    table_receipts = {_source_identity_v1(item["region"]): item for item in candidate["closure_receipt"]["table_receipts"]}
    prior_source = None
    mixed_labels = {_without_leading_ordinal(_normalized(label)) for label in _UNPROVEN_MIXED_ROLE_LABELS_V1}
    for region in regions:
        page = pages[region["page_json_version_id"]]
        section, table = _source_table(page, section_id=region["section_id"], table_id=region["table_id"])
        semantic_page = semantic_pages[region["page_json_version_id"]]
        semantic_section, semantic_table = _source_table(semantic_page,
            section_id=region["section_id"], table_id=region["table_id"])
        source_axis = _unit_axis(table, compiled_specs=compiled_specs, document_unit_context=None)
        private = canonical_clone_v1(table)
        scope = _scope_repeated_owner_header_prefix(region=region, section=section,
            table=private, compiled_specs=compiled_specs)
        scoped_axis = _unit_axis(private, compiled_specs=compiled_specs, document_unit_context=None)
        source_key = _source_identity_v1(region)
        current_source = {"region": region, "page": page, "section": section, "table": table,
            "semantic_section": semantic_section, "semantic_table": semantic_table,
            "scoped_axis": scoped_axis, "table_receipt": table_receipts.get(source_key)}
        unit_context = _source_owned_continuation_unit_context_v1(prior_source, current_source, compiled_specs=compiled_specs)
        effective_unit = scoped_axis.get("canonical_unit") if scoped_axis.get("complete") else (
            unit_context["canonical_unit"] if unit_context is not None else None)
        units_by_source[source_key] = effective_unit
        fragments.append({"locator": canonical_clone_v1(region), "source_table_sha256": canonical_json_sha256_v1(table),
            "authenticated_semantic_table_sha256": canonical_json_sha256_v1(semantic_table),
            "source_local_unit_axis": source_axis, "scoped_local_unit_axis": scoped_axis,
            "source_header_scope_receipt": scope, "source_owned_continuation_unit_context": unit_context,
            "source_owned_canonical_unit": effective_unit})
        if effective_unit is None:
            reasons.append("F38_SOURCE_UNIT_NOT_LOCALLY_PROVEN")
        if page.get("status") == "FINANCIAL_NOTE_CONTENT" and section.get("content_kind") == "FINANCIAL_NOTE":
            classification = classify_gemini_json_multitable_hierarchical_table_v1(
                semantic_page, semantic_section, semantic_table, compiled_specs=compiled_specs)
            declared_rows = {hit["row_ordinal"] for hit in classification["role_hits"]}
            declared_rows.update(classification.get("family_root_row_ordinals", []))
            money_ordinals = [ordinal for ordinal, column in enumerate(semantic_table.get("columns") or [], 1)
                              if type(column) is dict and column.get("value_kind") == "MONEY"]
            for ordinal, row in enumerate(semantic_table.get("rows") or [], 1):
                if type(row) is not dict:
                    continue
                values = row.get("values_exact")
                try:
                    observed = type(values) is list and any(column <= len(values)
                        and _source_money(values[column - 1])["coefficient"] is not None for column in money_ordinals)
                except (TypeError, ValueError):
                    observed = True
                    reasons.append("F38_ORIGINAL_SOURCE_MONEY_NOT_DIRECTLY_PARSEABLE")
                generic_total = _without_leading_ordinal(_normalized(row.get("label_exact"))) in _SOURCE_GENERIC_TOTAL_LABELS_V1 or (
                    not _normalized(row.get("label_exact")) and row.get("row_kind") in {"TOTAL", "SUBTOTAL"})
                if observed and ordinal not in declared_rows and not generic_total:
                    reasons.append("F38_NONDECLARED_SOURCE_MONEY_ROLE_NOT_PROVEN")
                if type(row) is dict and _without_leading_ordinal(_normalized(row.get("label_exact"))) in mixed_labels:
                    reasons.append("F38_SOURCE_TEMPLATE_ROLE_GRANULARITY_NOT_PROVEN")
                    mixed_rows.append({"locator": canonical_clone_v1(region), "row_ordinal": ordinal,
                        "source_row": canonical_clone_v1(table["rows"][ordinal - 1]),
                        "authenticated_semantic_row": canonical_clone_v1(row), "rule": "NO_UNPROVEN_MIXED_ROLE_OR_VALUE_SPLIT"})
        prior_source = current_source
    for mapping in candidate.get("mappings", []):
        for ref in mapping.get("source_refs", []):
            locator = ref.get("locator", {})
            source_key = _source_identity_v1(locator)
            if source_key not in units_by_source or units_by_source[source_key] != mapping.get("unit"):
                reasons.append("F38_MAPPING_UNIT_DIFFERS_FROM_ORIGINAL_SOURCE_SCOPE")
    output = canonical_clone_v1(candidate)
    retired = None
    withheld = []
    if reasons:
        withheld = output["mappings"]
        output["mappings"] = []
        output["status"] = UNRESOLVED
        output["reasons"] = sorted(set(output.get("reasons", []) + reasons))
        closure = output["closure_receipt"]
        retired = _retire_root_authority_v1(output,
            root_mappings_before=[mapping for mapping in withheld if mapping.get("role") == "FAMILY_ROOT_TOTAL"])
        closure["structural_root_receipt"]["emitted_mapping"] = False
        closure["structural_root_receipt"]["active_permission"] = "NONE_HELD_BY_F38_SOURCE_ROLE_UNIT_CONTROL"
    material = {"format_version": "F38_SOURCE_ROLE_UNIT_CONTROL_V1",
        "candidate_before_sha256": canonical_json_sha256_v1(candidate), "fragments": fragments,
        "source_repair_receipts": canonical_clone_v1(source_repair_receipts),
        "unproven_role_source_rows": mixed_rows, "reasons": sorted(set(reasons)),
        "withheld_mapping_evidence": _inactive_evidence_envelope_v1(withheld),
        "retired_root_authority": retired,
        "rule": "ORIGINAL_LOCAL_SOURCE_UNIT_AND_DECLARED_ROLE_SCOPE_NO_AMOUNT_PERMISSION_NO_SPLIT"}
    receipt = {**material, "receipt_id": "gjoafav1:source-role-unit:" + canonical_json_sha256_v1(material)}
    output["closure_receipt"]["other_activity_source_role_unit_control_receipt"] = receipt
    output["closure_receipt"]["structural_root_receipt"]["source_role_unit_control_receipt_id"] = receipt["receipt_id"]
    return {**output, "candidate_id": "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in output.items() if key != "candidate_id"})}


def evaluate_gemini_json_other_activity_family_cluster_v1(
    *, regions: Any, page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any], query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    checked = _validate_query_receipt(query_receipt, regions=regions)
    candidate = _evaluate_source_projected_cluster_v1(regions=regions,
        page_json_by_version=page_json_by_version, compiled_specs=compiled_specs, query_receipt=checked)
    adapter = checked["adapter_receipt"]
    repairs = adapter.get("source_repair_receipts", []) if type(adapter) is dict else []
    semantic_pages = _apply_source_repair_receipts_to_pages(
        canonical_clone_v1(dict(page_json_by_version)), repairs)
    return _apply_source_role_unit_control_v1(candidate, regions=regions,
        pages=page_json_by_version, compiled_specs=compiled_specs,
        semantic_pages=semantic_pages, source_repair_receipts=repairs)


def validate_gemini_json_other_activity_family_candidate_replay_v1(
    candidate: Any, *, regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]], compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    expected = evaluate_gemini_json_other_activity_family_cluster_v1(regions=regions,
        page_json_by_version=page_json_by_version, compiled_specs=compiled_specs, query_receipt=query_receipt)
    if not same_typed_json_v1(candidate, expected):
        raise _error("other-activity candidate replay drifted")
    return expected


def build_gemini_json_other_activity_trials_v1(
    *,
    indexed_query_evidence: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    evidence = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
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
            candidate = evaluate_gemini_json_other_activity_family_cluster_v1(
                regions=regions,
                page_json_by_version=page_json_by_document[ordinal],
                compiled_specs=compiled_specs,
                query_receipt=build_gemini_json_other_activity_region_query_receipt_v1(
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
            raise _error("other-activity query disposition is invalid")
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


def validate_gemini_json_other_activity_replay_v1(
    *,
    base_indexed_query_evidence: Any,
    indexed_query_evidence: Any,
    trials: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    expected_indexed = adapt_gemini_json_other_activity_indexed_query_evidence_v1(
        indexed_query_evidence=base_indexed_query_evidence,
        page_json_by_document=page_json_by_document,
        compiled_specs=compiled_specs,
    )
    if not same_typed_json_v1(expected_indexed, indexed_query_evidence):
        raise _error("other-activity indexed query replay drifted")
    expected_trials = build_gemini_json_other_activity_trials_v1(
        indexed_query_evidence=expected_indexed,
        page_json_by_document=page_json_by_document,
        compiled_specs=compiled_specs,
    )
    if type(trials) is not list or not same_typed_json_v1(expected_trials, trials):
        raise _error("other-activity trial replay drifted")
    return expected_trials
