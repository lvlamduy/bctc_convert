"""Family-38 adapter for other-activity disclosures.

The shared multi-table engine remains the accounting authority.  This module
adds only two source-bound operations on private clones: a direct primary
income-statement result when the detailed note is absent, and exact
same-document unit corroboration for an otherwise unitless selected note.
When a complete note does not print its own result, its direct detail mappings
are combined with the direct primary-statement result.  No source value is
derived and a blank source cell is never converted to zero.
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
from bctc_ai.evaluation.source_observation_lane_math_v1 import (
    additive_source_lane_receipts_v1,
    observed_source_coefficient_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
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
            "EXACT_SAME_DOCUMENT_ROOT_LABEL_AND_NONZERO_SCALAR_IN_EXPLICIT_UNIT_"
            "TABLE_OR_EXACT_UNIQUE_IMMEDIATELY_PRECEDING_PRIMARY_STATEMENT_UNIT"
        )
        or value.get("unit_corroboration_policy")
        != (
            "EXACT_SAME_DOCUMENT_ROOT_OR_TERMINAL_VECTOR_ALL_LANES_OR_"
            "VND_TO_MILLION_WITHIN_HALF_DISPLAY_UNIT"
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
    if unit_control is not None:
        table["unit_exact"] = unit_control["unit_surface_exact"]
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
    source_record = occurrence["record"]
    source_page = source_record["page_json"]
    source_section, source_table = _source_table(
        source_page,
        section_id=occurrence["section_id"],
        table_id=occurrence["table_id"],
    )
    if _unit_axis(source_table, compiled_specs=compiled_specs, document_unit_context=None).get(
        "complete"
    ):
        return None
    lane = _multitable_lane_axis(source_section, source_table, compiled_specs=compiled_specs)
    money_ordinals = lane.get("money_column_ordinals")
    try:
        source_row = source_table["rows"][occurrence["row_ordinal"] - 1]
        source_values = source_row["values_exact"]
    except (IndexError, KeyError, TypeError) as exc:
        raise _error("other-activity primary unit-control source is invalid") from exc
    if (
        not lane.get("complete")
        or type(money_ordinals) is not list
        or len(money_ordinals) < 2
        or type(source_values) is not list
    ):
        return None
    primary_cells = [
        (ordinal, _source_money(source_values[ordinal - 1])["coefficient"])
        for ordinal in money_ordinals
        if ordinal <= len(source_values)
    ]
    primary_cells = [(ordinal, value) for ordinal, value in primary_cells if value not in {None, 0}]
    if not primary_cells:
        return None

    aliases = set(compiled_specs["topology"]["parent"]["aliases"])
    controls = []
    for record in page_records:
        page = record["page_json"]
        for section_ordinal, section in enumerate(page.get("sections") or [], start=1):
            if type(section) is not dict:
                continue
            for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
                if type(table) is not dict or table is source_table:
                    continue
                unit_axis = _unit_axis(
                    table, compiled_specs=compiled_specs, document_unit_context=None
                )
                canonical_unit = unit_axis.get("canonical_unit")
                if not unit_axis.get("complete") or canonical_unit not in _UNIT_SURFACE:
                    continue
                for row_ordinal, row in enumerate(table.get("rows") or [], start=1):
                    if (
                        type(row) is not dict
                        or _without_leading_ordinal(_normalized(row.get("label_exact")))
                        not in aliases
                        or type(row.get("values_exact")) is not list
                    ):
                        continue
                    for column_ordinal, source_text in enumerate(row["values_exact"], start=1):
                        coefficient = _source_money(source_text)["coefficient"]
                        for primary_column_ordinal, primary_coefficient in primary_cells:
                            if coefficient != primary_coefficient:
                                continue
                            controls.append(
                                {
                                    "canonical_unit": canonical_unit,
                                    "control_label_exact": row.get("label_exact"),
                                    "control_page_json_sha256": canonical_json_sha256_v1(page),
                                    "control_source_text_exact": source_text,
                                    "control_value": coefficient,
                                    "locator": {
                                        "column_ordinal": column_ordinal,
                                        "page_json_version_id": record["page_json_version_id"],
                                        "physical_page": record["physical_page"],
                                        "row_ordinal": row_ordinal,
                                        "section_id": f"s{section_ordinal}",
                                        "table_id": f"t{table_ordinal}",
                                    },
                                    "primary_column_ordinal": primary_column_ordinal,
                                    "rule": (
                                        "EXACT_SAME_DOCUMENT_FAMILY_ROOT_LABEL_AND_"
                                        "NONZERO_SCALAR_IN_EXPLICIT_UNIT_TABLE"
                                    ),
                                    "unit_surface_exact": _UNIT_SURFACE[canonical_unit],
                                }
                            )
    if len(controls) == 1:
        material = controls[0]
        return {
            **material,
            "receipt_id": "gjoafav1:primary-unit:" + canonical_json_sha256_v1(material),
        }

    adjacent_controls = []
    for record in page_records:
        if (
            record.get("physical_page") + 1 != source_record.get("physical_page")
            or record.get("selected_page_ordinal") + 1
            != source_record.get("selected_page_ordinal")
        ):
            continue
        page = record["page_json"]
        if page.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
            continue
        for section_ordinal, section in enumerate(page.get("sections") or [], start=1):
            if (
                type(section) is not dict
                or section.get("content_kind") != "PRIMARY_STATEMENT"
                or section.get("statement_type") != "BALANCE_SHEET"
            ):
                continue
            for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
                if type(table) is not dict:
                    continue
                unit_axis = _unit_axis(
                    table, compiled_specs=compiled_specs, document_unit_context=None
                )
                canonical_unit = unit_axis.get("canonical_unit")
                evidence = unit_axis.get("evidence")
                columns = table.get("columns")
                money_ordinals = [
                    ordinal
                    for ordinal, column in enumerate(
                        columns if type(columns) is list else [], start=1
                    )
                    if type(column) is dict and column.get("value_kind") == "MONEY"
                ]
                header_unit_ordinals = (
                    {
                        int(item["source_kind"].split(":", 2)[1])
                        for item in evidence
                        if type(item) is dict
                        and type(item.get("source_kind")) is str
                        and item["source_kind"].startswith("MONEY_COLUMN_HEADER:")
                        and item.get("accepted") is True
                        and item.get("canonical_unit") == canonical_unit
                    }
                    if type(evidence) is list
                    else set()
                )
                if (
                    not unit_axis.get("complete")
                    or canonical_unit not in _UNIT_SURFACE
                    or len(money_ordinals) < 2
                    or set(range(1, len(money_ordinals) + 1)) != header_unit_ordinals
                ):
                    continue
                adjacent_controls.append(
                    {
                        "canonical_unit": canonical_unit,
                        "control_kind": "ADJACENT_PRIMARY_STATEMENT_EXPLICIT_UNIT",
                        "control_page_json_sha256": canonical_json_sha256_v1(page),
                        "control_unit_evidence": canonical_clone_v1(evidence),
                        "locator": {
                            "page_json_version_id": record["page_json_version_id"],
                            "physical_page": record["physical_page"],
                            "section_id": f"s{section_ordinal}",
                            "selected_page_ordinal": record["selected_page_ordinal"],
                            "table_id": f"t{table_ordinal}",
                        },
                        "rule": (
                            "EXACT_UNIQUE_IMMEDIATELY_PRECEDING_PRIMARY_BALANCE_"
                            "SHEET_TABLE_WITH_EXPLICIT_ACCEPTED_UNIT_IN_EVERY_MONEY_HEADER"
                        ),
                        "unit_surface_exact": _UNIT_SURFACE[canonical_unit],
                    }
                )
    if len(adjacent_controls) != 1:
        return None
    material = adjacent_controls[0]
    return {
        **material,
        "receipt_id": "gjoafav1:primary-unit:" + canonical_json_sha256_v1(material),
    }


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
    unit_control = receipt.get("primary_unit_corroboration_receipt")
    if unit_control is not None:
        if type(unit_control) is not dict:
            raise _error("other-activity primary unit-control receipt is invalid")
        unit_material = {
            key: canonical_clone_v1(value)
            for key, value in unit_control.items()
            if key != "receipt_id"
        }
        if unit_control.get("receipt_id") != (
            "gjoafav1:primary-unit:" + canonical_json_sha256_v1(unit_material)
        ):
            raise _error("other-activity primary unit-control identity drifted")
        control_locator = unit_control.get("locator")
        control_page = (
            pages.get(control_locator.get("page_json_version_id"))
            if type(control_locator) is dict
            else None
        )
        if type(control_page) is not dict or canonical_json_sha256_v1(
            control_page
        ) != unit_control.get("control_page_json_sha256"):
            raise _error("other-activity primary unit-control page drifted")
        try:
            control_section, control_table = _source_table(
                control_page,
                section_id=control_locator["section_id"],
                table_id=control_locator["table_id"],
            )
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            raise _error("other-activity primary unit-control locator drifted") from exc
        control_axis = _unit_axis(
            control_table,
            compiled_specs=compiled_specs,
            document_unit_context=None,
        )
        if unit_control.get("control_kind") == "ADJACENT_PRIMARY_STATEMENT_EXPLICIT_UNIT":
            columns = control_table.get("columns")
            evidence = control_axis.get("evidence")
            money_ordinals = [
                ordinal
                for ordinal, column in enumerate(
                    columns if type(columns) is list else [], start=1
                )
                if type(column) is dict and column.get("value_kind") == "MONEY"
            ]
            header_unit_ordinals = (
                {
                    int(item["source_kind"].split(":", 2)[1])
                    for item in evidence
                    if type(item) is dict
                    and type(item.get("source_kind")) is str
                    and item["source_kind"].startswith("MONEY_COLUMN_HEADER:")
                    and item.get("accepted") is True
                    and item.get("canonical_unit") == control_axis.get("canonical_unit")
                }
                if type(evidence) is list
                else set()
            )
            if (
                control_page.get("status") != "PRIMARY_FINANCIAL_STATEMENT"
                or control_section.get("content_kind") != "PRIMARY_STATEMENT"
                or control_section.get("statement_type") != "BALANCE_SHEET"
                or control_locator.get("physical_page") + 1
                != locator.get("physical_page")
                or control_locator.get("selected_page_ordinal") + 1
                != locator.get("selected_page_ordinal")
                or not control_axis.get("complete")
                or control_axis.get("canonical_unit") != unit_control.get("canonical_unit")
                or evidence != unit_control.get("control_unit_evidence")
                or len(money_ordinals) < 2
                or set(range(1, len(money_ordinals) + 1)) != header_unit_ordinals
                or _UNIT_SURFACE.get(unit_control.get("canonical_unit"))
                != unit_control.get("unit_surface_exact")
            ):
                raise _error("other-activity adjacent primary unit-control source drifted")
        else:
            try:
                control_row = control_table["rows"][control_locator["row_ordinal"] - 1]
                control_source_text = control_row["values_exact"][
                    control_locator["column_ordinal"] - 1
                ]
                primary_source_text = row["values_exact"][
                    unit_control["primary_column_ordinal"] - 1
                ]
            except (IndexError, KeyError, TypeError, ValueError) as exc:
                raise _error("other-activity primary unit-control locator drifted") from exc
            if (
                _without_leading_ordinal(_normalized(control_row.get("label_exact")))
                not in set(compiled_specs["topology"]["parent"]["aliases"])
                or control_row.get("label_exact") != unit_control.get("control_label_exact")
                or control_source_text != unit_control.get("control_source_text_exact")
                or _source_money(control_source_text)["coefficient"]
                != unit_control.get("control_value")
                or _source_money(primary_source_text)["coefficient"]
                != unit_control.get("control_value")
                or unit_control.get("control_value") in {None, 0}
                or not control_axis.get("complete")
                or control_axis.get("canonical_unit") != unit_control.get("canonical_unit")
                or _UNIT_SURFACE.get(unit_control.get("canonical_unit"))
                != unit_control.get("unit_surface_exact")
            ):
                raise _error("other-activity primary unit-control source drifted")
        table["unit_exact"] = unit_control["unit_surface_exact"]
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
    primary_unit = primary_mapping.get("unit")
    primary_vector = _mapping_vector(primary_mapping)
    if (
        primary_unit not in _UNIT_SURFACE
        or not primary_vector
        or any(value is None for value in primary_vector)
    ):
        return pages, []
    selected = []
    incomplete = []
    controls = []
    receipts = []
    prior_control_fragment = None
    for region in note_regions:
        page = pages[region["page_json_version_id"]]
        section, table = _source_table(
            page, section_id=region["section_id"], table_id=region["table_id"]
        )
        scope_receipt = _scope_repeated_owner_header_prefix(
            region=region,
            section=section,
            table=table,
            compiled_specs=compiled_specs,
        )
        if scope_receipt is not None:
            receipts.append(scope_receipt)
        selected.append((region, section, table))
        axis = _unit_axis(table, compiled_specs=compiled_specs, document_unit_context=None)
        if axis.get("complete"):
            prior_control_fragment = (region, section, table)
            continue
        incomplete.append((region, section, table))
        fallback_money_ordinals = None
        if prior_control_fragment is not None:
            prior_region, prior_section, prior_table = prior_control_fragment
            prior_lane = _multitable_lane_axis(
                prior_section, prior_table, compiled_specs=compiled_specs
            )
            columns = table.get("columns")
            if (
                prior_table.get("continuation") == "CONTINUES_ON_NEXT_PAGE"
                and table.get("continuation") == "CONTINUES_FROM_PREVIOUS_PAGE"
                and region["physical_page"] == prior_region["physical_page"] + 1
                and prior_lane.get("complete")
                and type(columns) is list
                and len(prior_lane["money_column_ordinals"])
                == sum(
                    type(column) is dict and column.get("value_kind") == "MONEY"
                    for column in columns
                )
            ):
                fallback_money_ordinals = [
                    ordinal
                    for ordinal, column in enumerate(columns, start=1)
                    if type(column) is dict and column.get("value_kind") == "MONEY"
                ]
        matches = _source_root_rows(
            table=table,
            section=section,
            compiled_specs=compiled_specs,
            fallback_money_ordinals=fallback_money_ordinals,
        )
        for ordinal, note_vector in matches:
            for target_unit in _UNIT_SURFACE:
                if _unit_control_match(
                    primary_unit=primary_unit,
                    primary_vector=primary_vector,
                    note_vector=note_vector,
                    target_unit=target_unit,
                ):
                    controls.append((region, ordinal, note_vector, target_unit))
        prior_control_fragment = (region, section, table)
    if not incomplete:
        return pages, receipts
    if len(controls) != 1:
        return pages, receipts
    if len(incomplete) > 1 and not _continuation_chain([item[2] for item in selected]):
        return pages, receipts
    control_region, control_row_ordinal, note_vector, unit = controls[0]
    surface = _UNIT_SURFACE[unit]
    projections = []
    for region, _section, table in incomplete:
        before_sha = canonical_json_sha256_v1(table)
        table["unit_exact"] = surface
        projections.append(
            {
                "after_table_sha256": canonical_json_sha256_v1(table),
                "before_table_sha256": before_sha,
                "locator": {
                    key: region[key]
                    for key in (
                        "page_json_version_id",
                        "physical_page",
                        "section_id",
                        "table_id",
                    )
                },
            }
        )
    material = {
        "canonical_unit": unit,
        "control_mapping_id": primary_mapping["item_mapping_id"],
        "control_row_ordinal": control_row_ordinal,
        "control_table_locator": {
            key: control_region[key]
            for key in ("page_json_version_id", "physical_page", "section_id", "table_id")
        },
        "matched_note_vector": list(note_vector),
        "matched_primary_vector": list(primary_vector),
        "primary_canonical_unit": primary_unit,
        "projections": projections,
        "rule": (
            "UNITLESS_SELECTED_NOTE_EXACT_ROOT_OR_TERMINAL_TOTAL_ALL_LANES_"
            "EQUALS_DIRECT_PRIMARY_SOURCE_RESULT_OR_VND_TO_MILLION_WITHIN_HALF_"
            "DISPLAY_UNIT_AND_EXACT_CONTINUATION_SCOPE"
        ),
    }
    return pages, [
        *receipts,
        {
            **material,
            "receipt_id": "gjoafav1:unit:" + canonical_json_sha256_v1(material),
        },
    ]


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


def evaluate_gemini_json_other_activity_family_cluster_v1(
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
