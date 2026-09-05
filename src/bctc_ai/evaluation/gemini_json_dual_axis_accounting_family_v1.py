"""Exact dual-axis projection for manifest-selected Gemini accounting JSON.

The adapter transposes either geography rows under one exact metric column or
geography columns on one exact metric row into the canonical role-row/period-
column shape consumed by the shared hierarchical closure engine.  It reads no
PDF geometry and has no bank, filename, note, year, or page routing rule.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    READY,
    _candidate_result,
)
from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import (
    _header_dates,
    _money,
    _normalized,
    evaluate_gemini_json_hierarchical_family_table_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
)

FORMAT_VERSION = "GEMINI_JSON_DUAL_AXIS_ACCOUNTING_FAMILY_CANDIDATE_V1"
_REPORTING_PERIOD_ENDS = {(3, 31), (6, 30), (9, 30), (12, 31)}
_MONEY_MAGNITUDE = re.compile(r"\b(nghin|trieu|ty)\s+(?:dong|vnd)\b")
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_EXACT_OPPOSITE_AXIS_METRIC_QUALIFIER_"
    "TWO_ROLE_ROW_OR_COLUMN_TRANSPOSE_ONE_OR_TWO_PERIOD_SAME_OR_ADJACENT_"
    "TABLE_CLUSTER_EXACT_VISIBLE_ROLE_OR_TOTAL_PERIOD_UNIT_AND_EXHAUSTIVE_GRAPH_"
    "WITH_TYPED_UNMAPPED_SOURCE_BLANKS_NO_ZERO_INFERENCE_NO_GEOMETRY_"
    "PPOCR_VIETOCR_BANK_FILE_PAGE_NOTE_ROUTING_OR_NONZERO_BACKSOLVE_AUTHORITY"
)


class GeminiJsonDualAxisAccountingFamilyV1Error(ValueError):
    """The dual-axis policy, region references, or JSON source drifted."""


def _error(message: str) -> GeminiJsonDualAxisAccountingFamilyV1Error:
    return GeminiJsonDualAxisAccountingFamilyV1Error(message)


def _node_index(identifier: Any, prefix: str, limit: int) -> int:
    if type(identifier) is not str or not identifier.startswith(prefix):
        raise _error("dual-axis JSON node identity is invalid")
    suffix = identifier.removeprefix(prefix)
    if not suffix.isdigit() or suffix.startswith("0"):
        raise _error("dual-axis JSON node identity is invalid")
    index = int(suffix) - 1
    if not 0 <= index < limit:
        raise _error("dual-axis JSON node identity is out of range")
    return index


def _source_nodes(
    page_json: dict[str, Any], *, section_id: str, table_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    sections = page_json.get("sections")
    if type(sections) is not list:
        raise _error("dual-axis page has no section axis")
    section = sections[_node_index(section_id, "s", len(sections))]
    tables = section.get("tables") if type(section) is dict else None
    if type(tables) is not list:
        raise _error("dual-axis section has no table axis")
    table = tables[_node_index(table_id, "t", len(tables))]
    if type(table) is not dict:
        raise _error("dual-axis table is invalid")
    return section, table


def _dual_axis_normalized(value: Any) -> str:
    """Normalize one source surface, including literal JSON whitespace escapes."""

    if type(value) is not str:
        return _normalized(value)
    return _normalized(re.sub(r"\\[nrt]+", " ", value))


def _axis_leaf(path: Any, *, unit_aliases: list[str]) -> str:
    if type(path) is not list or any(
        value is not None and type(value) is not str for value in path
    ):
        return ""
    for value in reversed(path):
        folded = _dual_axis_normalized(value)
        for unit in sorted(unit_aliases, key=lambda item: (-len(item), item)):
            if folded == unit:
                folded = ""
                break
            if folded.endswith(" " + unit):
                folded = folded[: -(len(unit) + 1)].strip()
                break
        if folded:
            return folded
    return ""


def _unit_alias(text: Any, aliases: list[str]) -> str | None:
    folded = _dual_axis_normalized(text)
    matches = [alias for alias in aliases if folded == alias or folded.endswith(" " + alias)]
    longest = max((len(alias) for alias in matches), default=0)
    selected = sorted(alias for alias in matches if len(alias) == longest)
    return selected[0] if len(selected) == 1 else None


def _money_magnitudes(text: Any) -> set[str]:
    return (
        set()
        if type(text) is not str
        else {
            match.group(1)
            for match in _MONEY_MAGNITUDE.finditer(_dual_axis_normalized(text))
        }
    )


def _context_surface_records(
    *,
    regions: list[dict[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return target-local and same-page sibling text without document drift."""

    local: list[dict[str, Any]] = []
    sibling: list[dict[str, Any]] = []
    target_sections_by_page: dict[str, set[str]] = {}
    for region in regions:
        target_sections_by_page.setdefault(region["page_json_version_id"], set()).add(
            region["section_id"]
        )
    for page_version_id, target_sections in target_sections_by_page.items():
        page_json = page_json_by_version.get(page_version_id)
        if type(page_json) is not dict or type(page_json.get("sections")) is not list:
            raise _error("dual-axis context page is absent or invalid")
        for section_ordinal, section in enumerate(page_json["sections"], start=1):
            section_id = f"s{section_ordinal}"
            target = local if section_id in target_sections else sibling
            title = section.get("title_exact")
            if type(title) is str and title:
                target.append(
                    {
                        "page_json_version_id": page_version_id,
                        "section_id": section_id,
                        "source_kind": "SECTION_TITLE",
                        "table_id": None,
                        "text_exact": title,
                    }
                )
            narratives = section.get("narratives_exact")
            if type(narratives) is list:
                for ordinal, narrative in enumerate(narratives, start=1):
                    if type(narrative) is str and narrative:
                        target.append(
                            {
                                "narrative_ordinal": ordinal,
                                "page_json_version_id": page_version_id,
                                "section_id": section_id,
                                "source_kind": "SECTION_NARRATIVE",
                                "table_id": None,
                                "text_exact": narrative,
                            }
                        )
            tables = section.get("tables")
            if type(tables) is not list:
                continue
            for table_ordinal, table in enumerate(tables, start=1):
                table_id = f"t{table_ordinal}"
                table_title = table.get("title_exact") if type(table) is dict else None
                if type(table_title) is str and table_title:
                    target.append(
                        {
                            "page_json_version_id": page_version_id,
                            "section_id": section_id,
                            "source_kind": "TABLE_TITLE",
                            "table_id": table_id,
                            "text_exact": table_title,
                        }
                    )
    return local, sibling


def _unique_parent_context(
    *,
    regions: list[dict[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    parent_aliases: list[str],
    hard_negative_aliases: list[str],
    structural_reset_aliases: list[str],
) -> tuple[dict[str, Any] | None, list[str]]:
    local, sibling = _context_surface_records(
        regions=regions,
        page_json_by_version=page_json_by_version,
    )
    reasons: list[str] = []
    for record in local:
        folded = _dual_axis_normalized(record["text_exact"])
        if any(alias in folded for alias in hard_negative_aliases):
            reasons.append("HARD_NEGATIVE_FAMILY_TITLE_PRESENT")
        if any(alias in folded for alias in structural_reset_aliases):
            reasons.append("STRUCTURAL_RESET_FAMILY_TITLE_PRESENT")
    for scope, records in (("TARGET_SECTION", local), ("SAME_PAGE_SIBLING_SECTION", sibling)):
        matches = []
        for record in records:
            folded = _dual_axis_normalized(record["text_exact"])
            matched_aliases = [alias for alias in parent_aliases if alias in folded]
            if matched_aliases:
                matches.append(
                    {
                        **canonical_clone_v1(record),
                        "context_scope": scope,
                        "matched_parent_alias": max(
                            matched_aliases, key=lambda alias: (len(alias), alias)
                        ),
                    }
                )
        if matches:
            matches.sort(
                key=lambda record: (
                    record["page_json_version_id"],
                    record["section_id"],
                    str(record["table_id"]),
                    record["source_kind"],
                    record.get("narrative_ordinal", 0),
                    record["text_exact"],
                )
            )
            return matches[0], reasons
    return None, reasons


def _table_period_evidence(
    *, section: dict[str, Any], table: dict[str, Any]
) -> dict[date, list[dict[str, Any]]]:
    by_date: dict[date, list[dict[str, Any]]] = {}

    def add(text: Any, source_kind: str, priority: int) -> None:
        if type(text) is not str or not text:
            return
        for parsed in _header_dates(text):
            by_date.setdefault(parsed, []).append(
                {
                    "priority": priority,
                    "source_kind": source_kind,
                    "text_exact": text,
                }
            )

    add(table.get("title_exact"), "TABLE_TITLE", 0)
    columns = table.get("columns")
    if type(columns) is list:
        for column_ordinal, column in enumerate(columns, start=1):
            path = column.get("header_path_exact") if type(column) is dict else None
            if type(path) is list:
                for value in path:
                    add(value, f"COLUMN_HEADER:c{column_ordinal}", 1)
    # A repeated report/section heading is document context, not evidence that
    # one continuation table owns that date.  Treating it as table-local would
    # assign the current date to both halves of an adjacent comparative pair.
    del section
    return by_date


def _document_period_evidence(
    document_context: Mapping[str, Any],
) -> dict[date, list[dict[str, Any]]]:
    records = document_context.get("period_evidence")
    if type(records) is not list:
        raise _error("dual-axis document period context is invalid")
    by_date: dict[date, list[dict[str, Any]]] = {}
    for record in records:
        if type(record) is not dict or type(record.get("text_exact")) is not str:
            raise _error("dual-axis document period evidence is invalid")
        for parsed in _header_dates(record["text_exact"]):
            by_date.setdefault(parsed, []).append(canonical_clone_v1(record))
    return by_date


def _document_balance_period_axis(
    document_context: Mapping[str, Any], *, table_count: int
) -> tuple[list[date], dict[str, Any] | None, list[str]]:
    """Resolve current/comparative balance dates from repeated JSON evidence."""

    by_date = _document_period_evidence(document_context)
    summaries = []
    for parsed in sorted(by_date):
        evidence = by_date[parsed]
        page_count = len({record["physical_page"] for record in evidence})
        summaries.append(
            {
                "date": parsed.isoformat(),
                "occurrence_count": len(evidence),
                "page_count": page_count,
            }
        )
    candidates = [
        parsed
        for parsed, evidence in by_date.items()
        if (parsed.month, parsed.day) in _REPORTING_PERIOD_ENDS
        and len({record["physical_page"] for record in evidence}) >= 2
    ]
    if not candidates:
        return [], None, ["DOCUMENT_REPORTING_PERIOD_CONSENSUS_IS_ABSENT"]
    maximum_page_support = max(
        len({record["physical_page"] for record in by_date[parsed]}) for parsed in candidates
    )
    dominant = [
        parsed
        for parsed in candidates
        if len({record["physical_page"] for record in by_date[parsed]}) * 4 >= maximum_page_support
    ]
    current = max(
        dominant,
        key=lambda parsed: (
            parsed,
            len({record["physical_page"] for record in by_date[parsed]}),
            len(by_date[parsed]),
        ),
    )
    axis = [current]
    if table_count == 2:
        comparative = date(current.year - 1, 12, 31)
        if comparative not in by_date:
            return [], None, ["DOCUMENT_BALANCE_COMPARATIVE_PERIOD_IS_ABSENT"]
        axis.append(comparative)
    receipt = {
        "balance_comparative_period": (None if table_count == 1 else axis[1].isoformat()),
        "current_period": current.isoformat(),
        "dominant_candidate_dates": [parsed.isoformat() for parsed in sorted(dominant)],
        "maximum_page_support": maximum_page_support,
        "observed_dates": summaries,
        "resolution": "DOMINANT_REPEATED_REPORTING_END_DATE_BALANCE_AXIS",
        "supporting_page_count": len({record["physical_page"] for record in by_date[current]}),
    }
    return axis, receipt, []


def _period_axis(
    *,
    projections: list[dict[str, Any]],
    document_context: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, list[str]]:
    reasons: list[str] = []
    local_axes = [projection["local_period_evidence"] for projection in projections]
    if any(len(axis) > 1 for axis in local_axes):
        return projections, None, ["SOURCE_TABLE_PERIOD_AXIS_IS_AMBIGUOUS"]
    known = {index: next(iter(axis)) for index, axis in enumerate(local_axes) if len(axis) == 1}
    if len(set(known.values())) != len(known):
        return projections, None, ["SOURCE_TABLE_PERIODS_ARE_NOT_DISTINCT"]
    table_count = len(projections)
    if len(known) == table_count:
        axis_dates = sorted(known.values(), reverse=True)
        current = axis_dates[0]
        if (current.month, current.day) not in _REPORTING_PERIOD_ENDS or (
            table_count == 2 and axis_dates[1] != date(current.year - 1, 12, 31)
        ):
            return projections, None, ["SOURCE_TABLE_LOCAL_BALANCE_PERIOD_AXIS_IS_NOT_EXACT"]
        document_axis_receipt = {
            "balance_comparative_period": (None if table_count == 1 else axis_dates[1].isoformat()),
            "current_period": current.isoformat(),
            "resolution": "COMPLETE_SOURCE_TABLE_LOCAL_BALANCE_AXIS",
        }
        document_dates: dict[date, list[dict[str, Any]]] = {}
    else:
        axis_dates, document_axis_receipt, document_axis_reasons = _document_balance_period_axis(
            document_context, table_count=table_count
        )
        if document_axis_reasons:
            return projections, None, document_axis_reasons
        if any(value not in axis_dates for value in known.values()):
            return projections, None, ["SOURCE_TABLE_PERIOD_IS_OUTSIDE_DOCUMENT_BALANCE_AXIS"]
        document_dates = _document_period_evidence(document_context)
    missing_dates = [value for value in axis_dates if value not in known.values()]
    missing_indices = [index for index in range(table_count) if index not in known]
    for index, value in zip(missing_indices, missing_dates, strict=True):
        known[index] = value
    if len(known) != table_count or len(set(known.values())) != table_count:
        return projections, None, ["PERIOD_TABLE_ASSIGNMENT_IS_NOT_UNIQUE"]

    assigned = []
    receipts = []
    for index, projection in enumerate(projections):
        period = known[index]
        local = projection["local_period_evidence"].get(period, [])
        if local:
            source = sorted(
                local,
                key=lambda record: (
                    record["priority"],
                    record["source_kind"],
                    record["text_exact"],
                ),
            )[0]
            source_mode = "SOURCE_TABLE_LOCAL"
        else:
            candidates = document_dates.get(period, [])
            if not candidates:
                reasons.append("DOCUMENT_PERIOD_EVIDENCE_IS_ABSENT")
                continue
            source_page = projection["source_ref"]["physical_page"]
            source = sorted(
                candidates,
                key=lambda record: (
                    abs(record["physical_page"] - source_page),
                    record["physical_page"],
                    record["section_id"],
                    str(record["table_id"]),
                    record["source_kind"],
                    record["text_exact"],
                ),
            )[0]
            source_mode = "DOCUMENT_JSON_ACCOUNTING_AXIS"
        assigned.append({**projection, "period": period})
        receipts.append(
            {
                "period": period.isoformat(),
                "source_evidence": canonical_clone_v1(source),
                "source_mode": source_mode,
                "source_ref": canonical_clone_v1(projection["source_ref"]),
            }
        )
    if reasons:
        return projections, None, reasons
    ordered = sorted(assigned, key=lambda projection: projection["period"], reverse=True)
    receipt_by_ref = {
        canonical_json_sha256_v1(receipt["source_ref"]): receipt for receipt in receipts
    }
    ordered_receipts = [
        receipt_by_ref[canonical_json_sha256_v1(projection["source_ref"])] for projection in ordered
    ]
    return (
        ordered,
        {
            "document_balance_axis": document_axis_receipt,
            "periods": [projection["period"].isoformat() for projection in ordered],
            "rule": "TABLE_TITLE_OR_HEADER_THEN_ADJACENT_COMPLEMENT_FROM_DOCUMENT_BALANCE_AXIS",
            "sources": ordered_receipts,
        },
        [],
    )


def _adjacent_tables_have_complete_local_balance_axis(
    *,
    regions: Sequence[dict[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
) -> bool:
    """Bind an adjacent pair without a continuation flag only from exact dates."""

    if len(regions) != 2:
        return False
    axis_dates = []
    for region in regions:
        page_json = page_json_by_version.get(region["page_json_version_id"])
        if type(page_json) is not dict:
            return False
        section, table = _source_nodes(
            page_json,
            section_id=region["section_id"],
            table_id=region["table_id"],
        )
        evidence = _table_period_evidence(section=section, table=table)
        local_dates = set(evidence)
        narratives = section.get("narratives_exact")
        for surface in [
            section.get("title_exact"),
            *(narratives if type(narratives) is list else []),
        ]:
            if type(surface) is str and surface:
                local_dates.update(_header_dates(surface))
        if len(local_dates) != 1:
            return False
        axis_dates.append(next(iter(local_dates)))
    axis = sorted(axis_dates, reverse=True)
    current = axis[0]
    return (
        len(set(axis)) == 2
        and (current.month, current.day) in _REPORTING_PERIOD_ENDS
        and axis[1] == date(current.year - 1, 12, 31)
    )


def _unit_evidence_for_projection(
    *,
    projection: dict[str, Any],
    document_context: Mapping[str, Any],
    unit_aliases: list[str],
) -> tuple[dict[str, Any] | None, list[str]]:
    document_records = document_context.get("unit_evidence")
    local_records = projection.get("local_unit_evidence")
    if (
        type(document_records) is not list
        or type(local_records) is not list
        or any(type(record) is not dict for record in [*local_records, *document_records])
    ):
        raise _error("dual-axis document unit context is invalid")
    records_by_hash = {
        canonical_json_sha256_v1(record): record for record in [*local_records, *document_records]
    }
    records = [records_by_hash[key] for key in sorted(records_by_hash)]
    source = projection["source_ref"]
    accepted_magnitudes = {
        magnitude for alias in unit_aliases for magnitude in _money_magnitudes(alias)
    }
    candidates = []
    conflicting_local_scale_records = []
    for record in records:
        if type(record) is not dict:
            raise _error("dual-axis document unit evidence is invalid")
        same_page = record.get("physical_page") == source["physical_page"]
        same_section = same_page and record.get("section_id") == source["section_id"]
        same_table = same_section and record.get("table_id") == source["table_id"]
        observed_magnitudes = _money_magnitudes(record.get("text_exact"))
        if same_table and observed_magnitudes - accepted_magnitudes:
            conflicting_local_scale_records.append(canonical_clone_v1(record))
        alias = _unit_alias(record.get("text_exact"), unit_aliases)
        if alias is None:
            continue
        if same_table and record.get("source_kind") == "TABLE_UNIT":
            scope_rank = 0
            scope = "SOURCE_TABLE_UNIT"
        elif same_table:
            scope_rank = 1
            scope = "SOURCE_TABLE_COLUMN_HEADER"
        elif same_section:
            scope_rank = 2
            scope = "SAME_SECTION_SIBLING_TABLE"
        elif same_page:
            scope_rank = 3
            scope = "SAME_PAGE_OTHER_TABLE"
        else:
            scope_rank = 4
            scope = "DOCUMENT_JSON_ACCOUNTING_AXIS"
        candidates.append(
            {
                "declared_unit_alias": alias,
                "distance_pages": abs(record["physical_page"] - source["physical_page"]),
                "scope": scope,
                "scope_rank": scope_rank,
                "source_evidence": canonical_clone_v1(record),
            }
        )
    if conflicting_local_scale_records:
        return None, ["DUAL_AXIS_SOURCE_TABLE_MONEY_UNIT_SCALE_CONFLICT"]
    if not candidates:
        return None, ["DUAL_AXIS_MONEY_UNIT_EVIDENCE_IS_ABSENT"]
    ordered = sorted(
        candidates,
        key=lambda candidate: (
            candidate["scope_rank"],
            candidate["distance_pages"],
            candidate["source_evidence"]["physical_page"],
            candidate["source_evidence"]["section_id"],
            str(candidate["source_evidence"]["table_id"]),
            candidate["source_evidence"]["source_kind"],
            candidate["source_evidence"]["text_exact"],
        ),
    )
    best = ordered[0]
    return best, []


def _projection_metric_leaf(
    projection: Mapping[str, Any], *, unit_aliases: list[str]
) -> str:
    source = projection["metric_source"]
    if type(source.get("label_exact")) is str:
        return _dual_axis_normalized(source["label_exact"])
    return _axis_leaf(source.get("header_path_exact"), unit_aliases=unit_aliases)


def _external_population_control_axis(
    *,
    projections: Sequence[dict[str, Any]],
    projection_units: Sequence[dict[str, Any]],
    document_context: Mapping[str, Any],
    control_policy: Mapping[str, Any],
    unit_aliases: list[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Corroborate declared population-sensitive metrics against an external row."""

    records = document_context.get("external_population_controls", [])
    if type(records) is not list or any(type(record) is not dict for record in records):
        raise _error("dual-axis external population control context is invalid")
    controlled_aliases = set(control_policy["controlled_metric_aliases"])
    control_report_norm_id = control_policy["control_report_norm_id"]
    magnitude_by_alias = control_policy["unit_decimal_magnitude_by_alias"]
    receipts = []
    reasons = []
    for projection, projection_unit in zip(projections, projection_units, strict=True):
        metric = _projection_metric_leaf(projection, unit_aliases=unit_aliases)
        if metric not in controlled_aliases:
            continue
        period = projection["period"].isoformat()
        projection_unit_alias = projection_unit["declared_unit_alias"]
        projection_unit_magnitude = magnitude_by_alias.get(projection_unit_alias)
        period_records = [
            record
            for record in records
            if record.get("period") == period
            and record.get("control_report_norm_id") == control_report_norm_id
            and type(record.get("coefficient")) is int
        ]
        candidates = [
            record
            for record in period_records
            if (
                control_alias := _unit_alias(record.get("unit_exact"), unit_aliases)
            )
            is not None
            and magnitude_by_alias.get(control_alias) == projection_unit_magnitude
        ]
        values = {record["coefficient"] for record in candidates}
        population_value = (
            projection["total_coefficient"]
            if projection["total_visible"] and projection["total_coefficient"] is not None
            else sum(projection["role_coefficients"])
            if all(value is not None for value in projection["role_coefficients"])
            else None
        )
        control_value = next(iter(values)) if len(values) == 1 else None
        if period_records and not candidates:
            disposition = "EXTERNAL_POPULATION_CONTROL_UNIT_MAGNITUDE_MISMATCH"
            reasons.append(disposition)
        elif not candidates:
            disposition = "EXTERNAL_POPULATION_CONTROL_IS_ABSENT"
            reasons.append(disposition)
        elif len(values) != 1:
            disposition = "EXTERNAL_POPULATION_CONTROL_IS_AMBIGUOUS"
            reasons.append(disposition)
        elif population_value is None:
            disposition = "EXTERNAL_POPULATION_TOTAL_IS_NOT_EXACT"
            reasons.append(disposition)
        elif population_value != control_value:
            disposition = "EXTERNAL_POPULATION_CONTROL_CONFLICT"
            reasons.append(disposition)
        else:
            disposition = "EXACT_EXTERNAL_POPULATION_CONTROL_MATCH"
        receipts.append(
            {
                "control_sources": canonical_clone_v1(candidates),
                "control_value": control_value,
                "control_report_norm_id": control_report_norm_id,
                "disposition": disposition,
                "metric": metric,
                "period": period,
                "population_value": population_value,
                "unit_decimal_magnitude": projection_unit_magnitude,
                "source_ref": canonical_clone_v1(projection["source_ref"]),
            }
        )
    return receipts, reasons


def _visible_total_rounding_receipt(
    *,
    projection: Mapping[str, Any],
    projection_unit: Mapping[str, Any],
    rounding_policy: Mapping[str, Any] | None,
) -> tuple[dict[str, Any] | None, list[str]]:
    residual = projection["total_equation_residual"]
    if residual in {None, 0}:
        return None, []
    if rounding_policy is None:
        return None, ["DUAL_AXIS_VISIBLE_TOTAL_EQUATION_FAILED"]
    unit_alias = projection_unit["declared_unit_alias"]
    magnitude = rounding_policy["unit_decimal_magnitude_by_alias"].get(unit_alias)
    if (
        magnitude is None
        or magnitude < rounding_policy["minimum_unit_decimal_magnitude"]
        or abs(residual) > rounding_policy["maximum_absolute_display_residual"]
    ):
        return None, ["DUAL_AXIS_VISIBLE_TOTAL_EQUATION_FAILED"]
    return (
        {
            "format_version": rounding_policy["format_version"],
            "maximum_absolute_display_residual": rounding_policy[
                "maximum_absolute_display_residual"
            ],
            "minimum_unit_decimal_magnitude": rounding_policy[
                "minimum_unit_decimal_magnitude"
            ],
            "unit_decimal_magnitude": magnitude,
        },
        [],
    )


def _project_single_source_table(
    *,
    region: dict[str, Any],
    page_json: dict[str, Any],
    compiled_specs: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    policy = compiled_specs["dual_axis_projection_policy"]
    section, table = _source_nodes(
        page_json,
        section_id=region["section_id"],
        table_id=region["table_id"],
    )
    columns = table.get("columns")
    rows = table.get("rows")
    if type(columns) is not list or not columns or type(rows) is not list or not rows:
        return None, ["DUAL_AXIS_SOURCE_TABLE_IS_EMPTY"]
    if any(
        type(column) is not dict
        or type(column.get("header_path_exact")) is not list
        for column in columns
    ):
        return None, ["DUAL_AXIS_SOURCE_COLUMN_AXIS_IS_INVALID"]
    role_order = policy["projected_role_order"]
    role_aliases = {
        role: {_normalized(alias) for alias in compiled_specs["query_aliases_by_role"][role]}
        for role in role_order
    }
    metric_aliases = set(policy["metric_aliases"])
    total_aliases = set(policy["total_aliases"])
    unit_aliases = policy["unit_aliases"]
    column_leaves = [
        _axis_leaf(column["header_path_exact"], unit_aliases=unit_aliases) for column in columns
    ]
    local_unit_evidence = []
    if type(table.get("unit_exact")) is str and table["unit_exact"]:
        local_unit_evidence.append(
            {
                "physical_page": region["physical_page"],
                "section_id": region["section_id"],
                "source_kind": "TABLE_UNIT",
                "table_id": region["table_id"],
                "text_exact": table["unit_exact"],
            }
        )
    for column_ordinal, column in enumerate(columns, start=1):
        for text_exact in column["header_path_exact"]:
            if type(text_exact) is str and text_exact:
                local_unit_evidence.append(
                    {
                        "physical_page": region["physical_page"],
                        "section_id": region["section_id"],
                        "source_kind": f"COLUMN_HEADER:c{column_ordinal}",
                        "table_id": region["table_id"],
                        "text_exact": text_exact,
                    }
                )
    orientation = region.get("orientation")
    role_values: dict[str, Any] = {}
    role_sources: dict[str, dict[str, Any]] = {}
    absent_source_roles: list[str] = []
    total_value: Any = None
    total_source: dict[str, Any] | None = None
    total_visible = False
    metric_source: dict[str, Any] | None = None
    unmatched_numeric: list[str] = []

    if orientation == "ROW_ROLES_METRIC_COLUMN":
        metric_indices = [
            index for index, leaf in enumerate(column_leaves) if leaf in metric_aliases
        ]
        row_matches = {
            role: [
                (ordinal, row)
                for ordinal, row in enumerate(rows, start=1)
                if _dual_axis_normalized(row.get("label_exact")) in aliases
            ]
            for role, aliases in role_aliases.items()
        }
        if (
            len(metric_indices) != 1
            or any(len(matches) > 1 for matches in row_matches.values())
            or not any(len(matches) == 1 for matches in row_matches.values())
        ):
            return None, ["ROW_ROLE_METRIC_COLUMN_EXACT_ASSIGNMENT_COUNT_NOT_ONE"]
        metric_index = metric_indices[0]
        if columns[metric_index].get("value_kind") != "MONEY":
            return None, ["DUAL_AXIS_BOUND_VALUE_COLUMN_IS_NOT_MONEY"]
        metric_source = {
            "column_index": metric_index,
            "header_path_exact": canonical_clone_v1(columns[metric_index]["header_path_exact"]),
        }
        role_ordinals = set()
        total_candidates = []
        for role, matches in row_matches.items():
            if not matches:
                absent_source_roles.append(role)
                role_values[role] = None
                role_sources[role] = {"presence": "ABSENT_SOURCE_AXIS_ROLE"}
                continue
            ordinal, row = matches[0]
            values = row.get("values_exact")
            if type(values) is not list or len(values) != len(columns):
                return None, ["DUAL_AXIS_ROW_VALUE_VECTOR_DRIFTED"]
            role_ordinals.add(ordinal)
            role_values[role] = values[metric_index]
            role_sources[role] = {
                "label_exact": row.get("label_exact"),
                "row_id": row.get("_dual_axis_original_row_id", f"r{ordinal}"),
            }
        for ordinal, row in enumerate(rows, start=1):
            if ordinal in role_ordinals:
                continue
            values = row.get("values_exact")
            if type(values) is not list or len(values) != len(columns):
                return None, ["DUAL_AXIS_ROW_VALUE_VECTOR_DRIFTED"]
            value = values[metric_index]
            if value is None:
                continue
            folded = _dual_axis_normalized(row.get("label_exact"))
            stacked_unlabeled_subtotal = (
                region.get("row_group_id") is not None
                and row.get("row_kind") == "SUBTOTAL"
                and not folded
            )
            if (
                row.get("row_kind") == "TOTAL"
                or folded in total_aliases
                or stacked_unlabeled_subtotal
            ):
                total_candidates.append((ordinal, row, value))
            else:
                unmatched_numeric.append(f"r{ordinal}")
        if len(total_candidates) > 1:
            return None, ["DUAL_AXIS_VISIBLE_TOTAL_COUNT_ABOVE_ONE"]
        if total_candidates:
            total_visible = True
            total_ordinal, total_row, total_value = total_candidates[0]
            total_source = {
                "label_exact": total_row.get("label_exact"),
                "row_id": total_row.get("_dual_axis_original_row_id", f"r{total_ordinal}"),
            }
    elif orientation == "METRIC_ROW_ROLE_COLUMNS":
        metric_rows = [
            (ordinal, row)
            for ordinal, row in enumerate(rows, start=1)
            if _dual_axis_normalized(row.get("label_exact")) in metric_aliases
        ]
        role_indices = {
            role: [index for index, leaf in enumerate(column_leaves) if leaf in aliases]
            for role, aliases in role_aliases.items()
        }
        if (
            len(metric_rows) != 1
            or any(len(indices) > 1 for indices in role_indices.values())
            or not any(len(indices) == 1 for indices in role_indices.values())
        ):
            return None, ["METRIC_ROW_ROLE_COLUMN_EXACT_ASSIGNMENT_COUNT_NOT_ONE"]
        metric_ordinal, metric_row = metric_rows[0]
        values = metric_row.get("values_exact")
        if type(values) is not list or len(values) != len(columns):
            return None, ["DUAL_AXIS_ROW_VALUE_VECTOR_DRIFTED"]
        metric_source = {
            "label_exact": metric_row.get("label_exact"),
            "row_id": f"r{metric_ordinal}",
        }
        role_column_indices = set()
        for role, indices in role_indices.items():
            if not indices:
                absent_source_roles.append(role)
                role_values[role] = None
                role_sources[role] = {"presence": "ABSENT_SOURCE_AXIS_ROLE"}
                continue
            index = indices[0]
            if columns[index].get("value_kind") != "MONEY":
                return None, ["DUAL_AXIS_BOUND_VALUE_COLUMN_IS_NOT_MONEY"]
            role_column_indices.add(index)
            role_values[role] = values[index]
            role_sources[role] = {
                "column_id": f"c{index + 1}",
                "header_path_exact": canonical_clone_v1(columns[index]["header_path_exact"]),
            }
        total_indices = [index for index, leaf in enumerate(column_leaves) if leaf in total_aliases]
        if len(total_indices) > 1:
            return None, ["DUAL_AXIS_VISIBLE_TOTAL_COUNT_ABOVE_ONE"]
        if total_indices:
            total_visible = True
            total_index = total_indices[0]
            if columns[total_index].get("value_kind") != "MONEY":
                return None, ["DUAL_AXIS_BOUND_VALUE_COLUMN_IS_NOT_MONEY"]
            total_value = values[total_index]
            total_source = {
                "column_id": f"c{total_index + 1}",
                "header_path_exact": canonical_clone_v1(columns[total_index]["header_path_exact"]),
            }
        bound_indices = role_column_indices | set(total_indices)
        metric_label = _dual_axis_normalized(metric_row.get("label_exact"))
        unmatched_numeric.extend(
            f"c{index + 1}"
            for index, value in enumerate(values)
            if index not in bound_indices
            and value is not None
            and not (
                columns[index].get("value_kind") == "TEXT"
                and _dual_axis_normalized(value) == metric_label
            )
        )
    else:
        return None, ["DUAL_AXIS_ORIENTATION_IS_NOT_DECLARED"]
    if unmatched_numeric:
        return None, ["DUAL_AXIS_UNBOUND_VISIBLE_VALUES:" + ",".join(unmatched_numeric)]

    blank_derived_roles = []
    unmapped_blank_roles = []
    effective_values = dict(role_values)
    preserve_source_blanks = policy["source_blank_mapping_policy"] == "PRESERVE_BLANK_OMIT_MAPPING"
    for role in role_order:
        if role_values[role] is not None:
            try:
                _money(role_values[role])
            except ValueError:
                return None, [f"DUAL_AXIS_ROLE_VALUE_IS_NOT_EXACT_INTEGER:{role}"]
            continue
        if preserve_source_blanks:
            unmapped_blank_roles.append(role)
            continue
        if role not in policy["blank_zero_derivable_roles"]:
            return None, [f"BLANK_ROLE_CELL_IS_NOT_DECLARED_ZERO_DERIVABLE:{role}"]
        other = next(other for other in role_order if other != role)
        if not total_visible or total_value is None or role_values[other] is None:
            if (
                policy["source_blank_mapping_policy"]
                == "OMIT_ROLE_WHEN_SOURCE_BLANK_AND_NO_EXACT_ZERO_EQUATION"
            ):
                unmapped_blank_roles.append(role)
                continue
            return None, [f"BLANK_ROLE_CELL_HAS_NO_EXACT_TOTAL_EQUATION:{role}"]
        try:
            inferred = (
                _money(total_value)["coefficient"] - _money(role_values[other])["coefficient"]
            )
        except ValueError:
            return None, ["DUAL_AXIS_VISIBLE_TOTAL_IS_NOT_EXACT_INTEGER"]
        if inferred != 0:
            return None, [f"BLANK_ROLE_CELL_WOULD_REQUIRE_NONZERO_BACKSOLVE:{role}"]
        effective_values[role] = "0"
        blank_derived_roles.append(role)
    try:
        role_coefficients = [
            (
                None
                if role in unmapped_blank_roles
                else _money(effective_values[role])["coefficient"]
            )
            for role in role_order
        ]
        total_coefficient = _money(total_value)["coefficient"] if total_visible else None
    except ValueError:
        return None, ["DUAL_AXIS_VALUE_OR_TOTAL_IS_NOT_EXACT_INTEGER"]
    total_equation_residual = None
    if total_visible and not unmapped_blank_roles:
        total_equation_residual = total_coefficient - sum(
            coefficient for coefficient in role_coefficients if coefficient is not None
        )

    source_ref = {
        "orientation": orientation,
        "page_json_version_id": region["page_json_version_id"],
        "physical_page": region["physical_page"],
        "section_id": region["section_id"],
        "table_id": region["table_id"],
    }
    if region.get("row_group_id") is not None:
        source_ref.update(
            {
                "row_group_id": region["row_group_id"],
                "row_group_path_exact": canonical_clone_v1(region["row_group_path_exact"]),
            }
        )
    role_value_states = {
        role: (
            "ABSENT_SOURCE_AXIS_ROLE"
            if role in absent_source_roles
            else "BLANK_SOURCE_CELL"
            if role_values[role] is None
            else _money(role_values[role])["state"]
        )
        for role in role_order
    }
    role_coefficient_by_role = dict(zip(role_order, role_coefficients, strict=True))
    return (
        {
            "absent_source_roles": absent_source_roles,
            "blank_derived_roles": blank_derived_roles,
            "unmapped_blank_roles": unmapped_blank_roles,
            "effective_values": effective_values,
            "local_period_evidence": _table_period_evidence(section=section, table=table),
            "local_unit_evidence": local_unit_evidence,
            "metric_source": metric_source,
            "orientation": orientation,
            "role_coefficients": role_coefficients,
            "role_coefficient_by_role": role_coefficient_by_role,
            "role_sources": role_sources,
            "role_value_states": role_value_states,
            "role_values": role_values,
            "source_ref": source_ref,
            "source_table_continuation": table.get("continuation"),
            "total_coefficient": total_coefficient,
            "total_equation_residual": total_equation_residual,
            "total_rounding_policy": None,
            "total_source": total_source,
            "total_source_text": total_value,
            "total_visible": total_visible,
        },
        [],
    )


def _stacked_row_scope_path(row: Mapping[str, Any]) -> list[Any] | None:
    path = row.get("hierarchy_path_exact")
    if type(path) is not list or any(
        value is not None and type(value) is not str for value in path
    ):
        return None
    scope = canonical_clone_v1(path)
    label = row.get("label_exact")
    if scope and (
        scope[-1] is None
        or (
            type(label) is str
            and _dual_axis_normalized(label)
            and _dual_axis_normalized(scope[-1]) == _dual_axis_normalized(label)
        )
    ):
        scope.pop()
    return scope


def _stacked_scope_key(path: Sequence[Any]) -> tuple[Any, ...]:
    return tuple(_dual_axis_normalized(value) if type(value) is str else value for value in path)


def _project_stacked_period_row_table(
    *,
    region: dict[str, Any],
    page_json: dict[str, Any],
    compiled_specs: dict[str, Any],
) -> tuple[list[dict[str, Any]] | None, list[str]]:
    """Split two exact date-owned role groups without inventing table lanes."""

    policy = compiled_specs["dual_axis_projection_policy"]
    section, table = _source_nodes(
        page_json,
        section_id=region["section_id"],
        table_id=region["table_id"],
    )
    rows = table.get("rows")
    columns = table.get("columns")
    if type(rows) is not list or type(columns) is not list:
        return None, ["DUAL_AXIS_SOURCE_TABLE_IS_EMPTY"]
    role_order = policy["projected_role_order"]
    role_aliases = {
        role: {_normalized(alias) for alias in compiled_specs["query_aliases_by_role"][role]}
        for role in role_order
    }
    role_matches = {
        role: [
            (ordinal, row)
            for ordinal, row in enumerate(rows, start=1)
            if _dual_axis_normalized(row.get("label_exact")) in aliases
        ]
        for role, aliases in role_aliases.items()
    }
    if not all(len(matches) == 2 for matches in role_matches.values()):
        return None, ["ROW_ROLE_METRIC_COLUMN_EXACT_ASSIGNMENT_COUNT_NOT_ONE_OR_TWO"]

    grouped: dict[tuple[Any, ...], dict[str, Any]] = {}
    all_role_ordinals = set()
    for role, matches in role_matches.items():
        for ordinal, row in matches:
            all_role_ordinals.add(ordinal)
            path = _stacked_row_scope_path(row)
            if not path:
                return None, ["DUAL_AXIS_STACKED_PERIOD_ROLE_GROUP_PATH_IS_ABSENT"]
            key = _stacked_scope_key(path)
            group = grouped.setdefault(key, {"path_exact": path, "roles": {}})
            if role in group["roles"]:
                return None, ["DUAL_AXIS_STACKED_PERIOD_ROLE_REPEATS_WITHIN_GROUP"]
            group["roles"][role] = (ordinal, row)
    if len(grouped) != 2 or any(
        set(group["roles"]) != set(role_order) for group in grouped.values()
    ):
        return None, ["DUAL_AXIS_STACKED_PERIOD_ROLE_GROUP_ASSIGNMENT_IS_NOT_EXACT"]

    metric_aliases = set(policy["metric_aliases"])
    column_leaves = [
        _axis_leaf(column.get("header_path_exact"), unit_aliases=policy["unit_aliases"])
        if type(column) is dict
        else ""
        for column in columns
    ]
    metric_indices = [index for index, leaf in enumerate(column_leaves) if leaf in metric_aliases]
    if len(metric_indices) != 1:
        return None, ["ROW_ROLE_METRIC_COLUMN_EXACT_ASSIGNMENT_COUNT_NOT_ONE"]
    metric_index = metric_indices[0]

    ordered_groups = sorted(
        grouped.items(),
        key=lambda item: min(ordinal for ordinal, _row in item[1]["roles"].values()),
    )
    group_periods: dict[tuple[Any, ...], tuple[date, str]] = {}
    for key, group in ordered_groups:
        observations = [
            (parsed, surface)
            for surface in group["path_exact"]
            if type(surface) is str
            for parsed in _header_dates(surface)
        ]
        dates = {parsed for parsed, _surface in observations}
        if len(dates) != 1:
            return None, ["DUAL_AXIS_STACKED_PERIOD_GROUP_DATE_IS_NOT_EXACT"]
        parsed = next(iter(dates))
        surface = next(surface for candidate, surface in observations if candidate == parsed)
        group_periods[key] = (parsed, surface)

    rows_by_group: dict[tuple[Any, ...], list[tuple[int, dict[str, Any]]]] = {
        key: [] for key in grouped
    }
    for ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict:
            return None, ["DUAL_AXIS_SOURCE_TABLE_ROW_IS_INVALID"]
        values = row.get("values_exact")
        if type(values) is not list or len(values) != len(columns):
            return None, ["DUAL_AXIS_ROW_VALUE_VECTOR_DRIFTED"]
        if ordinal in all_role_ordinals:
            owning_key = next(
                key
                for key, group in grouped.items()
                if ordinal in {item[0] for item in group["roles"].values()}
            )
            rows_by_group[owning_key].append((ordinal, row))
            continue
        if values[metric_index] is None:
            continue
        scope = _stacked_row_scope_path(row)
        scope_key = () if scope is None else _stacked_scope_key(scope)
        owners = [
            key for key in grouped if len(scope_key) >= len(key) and scope_key[: len(key)] == key
        ]
        if len(owners) != 1:
            return None, [f"DUAL_AXIS_STACKED_PERIOD_UNBOUND_VISIBLE_VALUE:r{ordinal}"]
        rows_by_group[owners[0]].append((ordinal, row))

    projections = []
    for group_index, (key, group) in enumerate(ordered_groups, start=1):
        projected_page = canonical_clone_v1(page_json)
        projected_table = projected_page["sections"][
            _node_index(region["section_id"], "s", len(projected_page["sections"]))
        ]["tables"][_node_index(region["table_id"], "t", len(section["tables"]))]
        projected_rows = []
        for ordinal, source_row in sorted(rows_by_group[key]):
            projected_row = canonical_clone_v1(source_row)
            projected_row["_dual_axis_original_row_id"] = f"r{ordinal}"
            projected_rows.append(projected_row)
        projected_table["rows"] = projected_rows
        grouped_region = {
            **region,
            "row_group_id": f"g{group_index}",
            "row_group_path_exact": canonical_clone_v1(group["path_exact"]),
        }
        projection, reasons = _project_single_source_table(
            region=grouped_region,
            page_json=projected_page,
            compiled_specs=compiled_specs,
        )
        if projection is None:
            return None, reasons
        parsed, surface = group_periods[key]
        projection["local_period_evidence"] = {
            parsed: [
                {
                    "priority": 0,
                    "source_kind": "ROW_GROUP_PATH",
                    "text_exact": surface,
                }
            ]
        }
        projections.append(projection)
    return projections, []


def _project_source_table(
    *,
    region: dict[str, Any],
    page_json: dict[str, Any],
    compiled_specs: dict[str, Any],
) -> tuple[list[dict[str, Any]] | None, list[str]]:
    if region.get("orientation") == "ROW_ROLES_METRIC_COLUMN":
        _section, table = _source_nodes(
            page_json,
            section_id=region["section_id"],
            table_id=region["table_id"],
        )
        rows = table.get("rows")
        if type(rows) is list:
            role_counts = []
            for role in compiled_specs["dual_axis_projection_policy"]["projected_role_order"]:
                aliases = {
                    _normalized(alias) for alias in compiled_specs["query_aliases_by_role"][role]
                }
                role_counts.append(
                    sum(
                        type(row) is dict
                        and _dual_axis_normalized(row.get("label_exact")) in aliases
                        for row in rows
                    )
                )
            if any(count > 1 for count in role_counts):
                return _project_stacked_period_row_table(
                    region=region,
                    page_json=page_json,
                    compiled_specs=compiled_specs,
                )
    projection, reasons = _project_single_source_table(
        region=region,
        page_json=page_json,
        compiled_specs=compiled_specs,
    )
    return (None, reasons) if projection is None else ([projection], reasons)


def _failed_candidate(
    *,
    compiled_specs: dict[str, Any],
    primary_region: dict[str, Any],
    reasons: list[str],
    receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = _candidate_result(
        topology=compiled_specs["topology"],
        page_json_version_id=primary_region["page_json_version_id"],
        physical_page=primary_region["physical_page"],
        section_id=primary_region["section_id"],
        table_id=primary_region["table_id"],
        reasons=reasons,
    )
    if receipt is not None:
        result["dual_axis_projection_receipt"] = receipt
    return result


def _projection_role_cell_receipt(projection: Mapping[str, Any], *, role: str) -> dict[str, Any]:
    return {
        "axis_source": canonical_clone_v1(projection["role_sources"][role]),
        "coefficient": projection["role_coefficient_by_role"][role],
        "raw_value_exact": projection["role_values"][role],
        "role": role,
        "source_ref": canonical_clone_v1(projection["source_ref"]),
        "source_value_state": projection["role_value_states"][role],
        "value_disposition": (
            "DERIVED_ZERO_FROM_EXACT_VISIBLE_TOTAL_AND_OTHER_ROLE"
            if role in projection["blank_derived_roles"]
            else "UNMAPPED_ABSENT_SOURCE_AXIS_ROLE"
            if role in projection["absent_source_roles"]
            else "UNMAPPED_SOURCE_BLANK"
            if role in projection["unmapped_blank_roles"]
            else "VISIBLE_SOURCE_VALUE"
        ),
    }


def _projection_equation_receipt(
    projection: Mapping[str, Any], *, role_order: list[str]
) -> dict[str, Any]:
    role_cells = [_projection_role_cell_receipt(projection, role=role) for role in role_order]
    total_cell = (
        None
        if not projection["total_visible"]
        else {
            "axis_source": canonical_clone_v1(projection["total_source"]),
            "coefficient": projection["total_coefficient"],
            "raw_value_exact": projection["total_source_text"],
            "source_ref": canonical_clone_v1(projection["source_ref"]),
        }
    )
    blank_zero_equations = []
    by_role = {cell["role"]: cell for cell in role_cells}
    for role in projection["blank_derived_roles"]:
        other_role = next(other for other in role_order if other != role)
        blank_zero_equations.append(
            {
                "derived_role": role,
                "equation": "EXACT_VISIBLE_TOTAL_MINUS_OTHER_ROLE_EQUALS_ZERO",
                "other_role_cell": canonical_clone_v1(by_role[other_role]),
                "total_cell": canonical_clone_v1(total_cell),
            }
        )
    return {
        "blank_zero_equations": blank_zero_equations,
        "mode": (
            "VISIBLE_TOTAL_WITH_MONEY_UNIT_DISPLAY_ROUNDING_RESIDUAL"
            if projection["total_equation_residual"] not in {None, 0}
            else "VISIBLE_TOTAL_RETAINED_WITH_ABSENT_SOURCE_AXIS_ROLE_NO_INFERENCE"
            if projection["total_visible"] and projection["absent_source_roles"]
            else
            "VISIBLE_TOTAL_RETAINED_WITH_TYPED_UNMAPPED_SOURCE_BLANK_NO_EXHAUSTIVE_EQUATION"
            if projection["total_visible"] and projection["unmapped_blank_roles"]
            else "VISIBLE_TOTAL_EXACTLY_EQUALS_EXHAUSTIVE_ROLE_PAIR"
            if projection["total_visible"]
            else "EXHAUSTIVE_ROLE_PAIR_WITH_TYPED_UNMAPPED_SOURCE_BLANK"
            if projection["unmapped_blank_roles"]
            else "EXHAUSTIVE_ROLE_PAIR_WITHOUT_PRINTED_TOTAL"
        ),
        "role_cells": role_cells,
        "source_ref": canonical_clone_v1(projection["source_ref"]),
        "total_cell": total_cell,
        "total_equation_residual": projection["total_equation_residual"],
        "total_rounding_policy": canonical_clone_v1(projection["total_rounding_policy"]),
    }


def evaluate_gemini_json_dual_axis_family_cluster_v1(
    *,
    regions: Sequence[dict[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    document_context: Mapping[str, Any],
    compiled_specs: dict[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Project and close one exact one/two-table dual-axis document cluster."""

    policy = compiled_specs.get("dual_axis_projection_policy")
    source_regions = list(regions)
    if policy is None or not source_regions:
        raise _error("dual-axis projection policy or regions are absent")
    source_regions.sort(
        key=lambda region: (
            region["physical_page"],
            region["section_id"],
            region["table_id"],
            region["page_json_version_id"],
        )
    )
    primary_region = source_regions[0]
    reasons: list[str] = []
    locations = {
        (
            region.get("page_json_version_id"),
            region.get("section_id"),
            region.get("table_id"),
        )
        for region in source_regions
    }
    source_paths = {region.get("source_logical_name") for region in source_regions}
    pages = {region.get("physical_page") for region in source_regions}
    orientations = {region.get("orientation") for region in source_regions}
    if len(source_regions) not in policy["period_table_count_alternatives"]:
        reasons.append("DUAL_AXIS_PERIOD_TABLE_COUNT_IS_NOT_DECLARED")
    if len(locations) != len(source_regions):
        reasons.append("DUAL_AXIS_SOURCE_TABLE_LOCATION_IS_DUPLICATE")
    if len(source_paths) != 1:
        reasons.append("DUAL_AXIS_CLUSTER_CROSSES_DOCUMENTS")
    if any(type(page) is not int for page in pages) or max(pages) - min(pages) > 1:
        reasons.append("DUAL_AXIS_CLUSTER_IS_NOT_SAME_OR_ADJACENT_PAGE")
    if len(orientations) != 1 or not orientations <= set(policy["orientations"]):
        reasons.append("DUAL_AXIS_CLUSTER_ORIENTATION_IS_NOT_UNIQUE")
    if len(pages) == 2:
        continuation_values = []
        for region in source_regions:
            page_json = page_json_by_version.get(region["page_json_version_id"])
            if type(page_json) is not dict:
                reasons.append("DUAL_AXIS_SOURCE_PAGE_IS_ABSENT")
                continue
            _section, table = _source_nodes(
                page_json,
                section_id=region["section_id"],
                table_id=region["table_id"],
            )
            continuation_values.append(table.get("continuation"))
        if not any(
            value in {"CONTINUES_FROM_PREVIOUS_PAGE", "CONTINUES_ON_NEXT_PAGE"}
            for value in continuation_values
        ) and not _adjacent_tables_have_complete_local_balance_axis(
            regions=source_regions,
            page_json_by_version=page_json_by_version,
        ):
            reasons.append("ADJACENT_PERIOD_TABLE_CLUSTER_HAS_NO_CONTINUATION_BINDING")

    parent_context, parent_reasons = _unique_parent_context(
        regions=source_regions,
        page_json_by_version=page_json_by_version,
        parent_aliases=compiled_specs["topology"]["parent"]["aliases"],
        hard_negative_aliases=compiled_specs["topology"]["hard_negative_aliases"],
        structural_reset_aliases=compiled_specs["topology"]["structural_reset_aliases"],
    )
    reasons.extend(parent_reasons)
    projections = []
    for region in source_regions:
        page_json = page_json_by_version.get(region["page_json_version_id"])
        if type(page_json) is not dict:
            reasons.append("DUAL_AXIS_SOURCE_PAGE_IS_ABSENT")
            continue
        projected_tables, projection_reasons = _project_source_table(
            region=region,
            page_json=page_json,
            compiled_specs=compiled_specs,
        )
        reasons.extend(projection_reasons)
        if projected_tables is not None:
            projections.extend(projected_tables)
    base_receipt = {
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "parent_context": canonical_clone_v1(parent_context),
        "query_receipt": canonical_clone_v1(dict(query_receipt)),
        "source_table_refs": [
            {
                key: region[key]
                for key in (
                    "orientation",
                    "page_json_version_id",
                    "physical_page",
                    "section_id",
                    "table_id",
                )
            }
            for region in source_regions
        ],
    }
    if len(projections) not in policy["period_table_count_alternatives"]:
        reasons.append("DUAL_AXIS_PROJECTED_PERIOD_COUNT_IS_NOT_DECLARED")
    if reasons:
        return _failed_candidate(
            compiled_specs=compiled_specs,
            primary_region=primary_region,
            reasons=reasons,
            receipt=base_receipt,
        )

    projections, period_receipt, period_reasons = _period_axis(
        projections=projections,
        document_context=document_context,
    )
    reasons.extend(period_reasons)
    unit_receipts = []
    for projection in projections:
        unit, unit_reasons = _unit_evidence_for_projection(
            projection=projection,
            document_context=document_context,
            unit_aliases=policy["unit_aliases"],
        )
        reasons.extend(unit_reasons)
        if unit is None:
            continue
        else:
            unit_receipt = {
                **unit,
                "source_ref": canonical_clone_v1(projection["source_ref"]),
            }
            rounding_receipt, rounding_reasons = _visible_total_rounding_receipt(
                projection=projection,
                projection_unit=unit_receipt,
                rounding_policy=policy.get("visible_total_rounding_policy"),
            )
            projection["total_rounding_policy"] = rounding_receipt
            reasons.extend(rounding_reasons)
            unit_receipts.append(unit_receipt)
    external_control_policy = policy.get("external_population_control")
    external_control_receipts = []
    if (
        external_control_policy is not None
        and period_receipt is not None
        and len(unit_receipts) == len(projections)
    ):
        external_control_receipts, external_control_reasons = (
            _external_population_control_axis(
                projections=projections,
                projection_units=unit_receipts,
                document_context=document_context,
                control_policy=external_control_policy,
                unit_aliases=policy["unit_aliases"],
            )
        )
        reasons.extend(external_control_reasons)
    receipt = {
        **base_receipt,
        "period_axis": period_receipt,
        "source_table_equations": [
            _projection_equation_receipt(
                projection,
                role_order=policy["projected_role_order"],
            )
            for projection in projections
        ],
        "unit_axis": {
            "declared_equivalent_unit_aliases": canonical_clone_v1(policy["unit_aliases"]),
            "sources": unit_receipts,
        },
    }
    if external_control_policy is not None:
        receipt["external_population_control"] = {
            "control_report_norm_id": external_control_policy["control_report_norm_id"],
            "controlled_projection_count": len(external_control_receipts),
            "match_rule": external_control_policy["match_rule"],
            "sources": external_control_receipts,
        }
    if reasons or period_receipt is None or len(unit_receipts) != len(projections):
        return _failed_candidate(
            compiled_specs=compiled_specs,
            primary_region=primary_region,
            reasons=reasons,
            receipt=receipt,
        )

    role_order = policy["projected_role_order"]
    columns = []
    for projection, unit in zip(projections, unit_receipts, strict=True):
        metric_source = projection["metric_source"]
        metric_text = metric_source.get("label_exact") or " | ".join(
            value
            for value in metric_source.get("header_path_exact", [])
            if type(value) is str and value
        )
        columns.append(
            {
                "header_path_exact": [
                    projection["period"].strftime("%d.%m.%Y"),
                    metric_text,
                    unit["source_evidence"]["text_exact"],
                ],
                "value_kind": "MONEY",
            }
        )
    primary_projection = projections[0]
    source_blank_roles = [
        role
        for role in role_order
        if any(role in projection["unmapped_blank_roles"] for projection in projections)
    ]
    unmapped_blank_roles = [
        role
        for role in role_order
        if all(role in projection["unmapped_blank_roles"] for projection in projections)
    ]
    partially_blank_roles = [
        role for role in source_blank_roles if role not in unmapped_blank_roles
    ]
    mapped_roles = [role for role in role_order if role not in unmapped_blank_roles]
    if not mapped_roles:
        return _failed_candidate(
            compiled_specs=compiled_specs,
            primary_region=primary_region,
            reasons=["DUAL_AXIS_NO_VISIBLE_ROLE_REMAINS_FOR_MAPPING"],
            receipt=receipt,
        )
    if source_blank_roles:
        result = _candidate_result(
            topology=compiled_specs["topology"],
            page_json_version_id=primary_projection["source_ref"]["page_json_version_id"],
            physical_page=primary_projection["source_ref"]["physical_page"],
            section_id=primary_projection["source_ref"]["section_id"],
            table_id=primary_projection["source_ref"]["table_id"],
            reasons=[],
        )
        result["mappings"] = [
            {
                "columns": canonical_clone_v1(columns),
                "hierarchy_path_exact": [compiled_specs["query_aliases_by_role"][role][0]],
                "label_exact": compiled_specs["query_aliases_by_role"][role][0],
                "report_norm_id": compiled_specs["bindings"][role],
                "role": role,
                "row_id": f"r{role_order.index(role) + 1}",
                "values": [
                    (
                        canonical_clone_v1(_money(projection["role_values"][role]))
                        if projection["role_values"][role] is not None
                        else {
                            "coefficient": None,
                            "source_text": None,
                            "state": (
                                "ABSENT_SOURCE_AXIS_ROLE"
                                if role in projection["absent_source_roles"]
                                else "BLANK_SOURCE_CELL"
                            ),
                        }
                    )
                    for projection in projections
                ],
            }
            for role in mapped_roles
        ]
        result["parent_binding_kind"] = (
            "UNIQUE_EXACT_DUAL_AXIS_ANCHOR_CLUSTER"
            if parent_context is None
            else "EXPLICIT_SECTION_OR_TABLE_TITLE"
        )
        result["closure_receipt"] = {
            "equations": [],
            "family_root_mapping_policy": compiled_specs["schema"]["family_root_mapping_policy"],
            "inferred_ambiguous_provision_role": None,
            "period_value_column_axis": {
                "money_column_indices": list(range(len(columns))),
                "percent_column_indices": [],
                "period_signatures": [
                    ["DATE", projection["period"].isoformat()] for projection in projections
                ],
                "source_value_kind_sequence": ["MONEY"] * len(columns),
                "unit_disposition": "EXPLICIT_TABLE_OR_COLUMN_MONEY_UNIT",
            },
            "rule": "EXACT_VISIBLE_DUAL_AXIS_CHILD_ROLE_WITH_TYPED_UNMAPPED_SOURCE_BLANK",
            "source_blank_mapping_policy": policy["source_blank_mapping_policy"],
            "partially_blank_mapped_roles": partially_blank_roles,
            "unmapped_source_blank_roles": unmapped_blank_roles,
            "used_anonymous_result_row_ids": [],
        }
    else:
        rows = []
        for role in role_order:
            rows.append(
                {
                    "hierarchy_path_exact": [compiled_specs["query_aliases_by_role"][role][0]],
                    "label_exact": compiled_specs["query_aliases_by_role"][role][0],
                    "row_kind": "ITEM",
                    "values_exact": [
                        projection["effective_values"][role] for projection in projections
                    ],
                }
            )
        if all(
            projection["total_visible"] and projection["total_equation_residual"] == 0
            for projection in projections
        ):
            rows.append(
                {
                    "hierarchy_path_exact": [None],
                    "label_exact": None,
                    "row_kind": "TOTAL",
                    "values_exact": [projection["total_source_text"] for projection in projections],
                }
            )
        projected_table = {
            "columns": columns,
            "continuation": "NONE",
            "rows": rows,
            "title_exact": None if parent_context is None else parent_context["text_exact"],
            "unit_exact": unit_receipts[0]["source_evidence"]["text_exact"],
        }
        projected_page = {
            "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
            "sections": [
                {
                    "content_kind": "FINANCIAL_NOTE",
                    "narratives_exact": [],
                    "statement_type": "NOT_APPLICABLE",
                    "tables": [projected_table],
                    "title_exact": None,
                }
            ],
            "status": "FINANCIAL_NOTE_CONTENT",
        }
        result = evaluate_gemini_json_hierarchical_family_table_v1(
            page_json=projected_page,
            page_json_version_id=primary_projection["source_ref"]["page_json_version_id"],
            physical_page=primary_projection["source_ref"]["physical_page"],
            section_id="s1",
            table_id="t1",
            compiled_specs=compiled_specs,
        )
    blank_by_role_and_lane = {
        (role, lane)
        for lane, projection in enumerate(projections)
        for role in projection["blank_derived_roles"]
    }
    for mapping in result.get("mappings", []):
        for lane, value in enumerate(mapping["values"]):
            if (mapping["role"], lane) in blank_by_role_and_lane:
                value.update(
                    {
                        "coefficient": 0,
                        "source_text": None,
                        "state": "DERIVED_ZERO_FROM_EXACT_VISIBLE_TOTAL_AND_OTHER_ROLE",
                    }
                )
    mapping_source_bindings = []
    equation_by_source_ref = {
        canonical_json_sha256_v1(equation["source_ref"]): equation
        for equation in receipt["source_table_equations"]
    }
    for mapping in result.get("mappings", []):
        if mapping["role"] not in role_order:
            continue
        lanes = []
        for lane, projection in enumerate(projections):
            cell = _projection_role_cell_receipt(projection, role=mapping["role"])
            equation = equation_by_source_ref[canonical_json_sha256_v1(projection["source_ref"])]
            lane_binding = {
                **cell,
                "mapping_value": canonical_clone_v1(mapping["values"][lane]),
                "period": projection["period"].isoformat(),
            }
            if mapping["role"] in projection["blank_derived_roles"]:
                lane_binding["blank_zero_equation"] = next(
                    canonical_clone_v1(item)
                    for item in equation["blank_zero_equations"]
                    if item["derived_role"] == mapping["role"]
                )
            lanes.append(lane_binding)
        binding = {
            "lanes": lanes,
            "report_norm_id": mapping["report_norm_id"],
            "role": mapping["role"],
        }
        binding_id = "gjdafv1:source-binding:" + canonical_json_sha256_v1(binding)
        binding["source_binding_id"] = binding_id
        mapping["dual_axis_lane_source_binding_id"] = binding_id
        mapping_source_bindings.append(binding)
    receipt["mapping_lane_source_bindings"] = mapping_source_bindings
    result["mapping_lane_source_bindings"] = canonical_clone_v1(mapping_source_bindings)
    result["dual_axis_projection_receipt"] = receipt
    if result.get("closure_receipt") is not None:
        result["closure_receipt"]["dual_axis_projection"] = canonical_clone_v1(receipt)
    if parent_context is None and result.get("status") == READY:
        result["parent_binding_kind"] = "UNIQUE_EXACT_DUAL_AXIS_ANCHOR_CLUSTER"
    source_refs = receipt["source_table_refs"]
    result.update(
        {
            "component_page_json_version_ids": [
                projection["source_ref"]["page_json_version_id"] for projection in projections
            ],
            "component_table_ids": [
                projection["source_ref"]["table_id"] for projection in projections
            ],
            "page_json_version_id": primary_projection["source_ref"]["page_json_version_id"],
            "physical_page": primary_projection["source_ref"]["physical_page"],
            "section_id": primary_projection["source_ref"]["section_id"],
            "source_table_refs": source_refs,
            "table_id": primary_projection["source_ref"]["table_id"],
        }
    )
    candidate_material = {
        "family_id": compiled_specs["topology"]["family_id"],
        "source_table_refs": source_refs,
    }
    result["candidate_id"] = "gjfafcv1:candidate:" + canonical_json_sha256_v1(candidate_material)
    return result
