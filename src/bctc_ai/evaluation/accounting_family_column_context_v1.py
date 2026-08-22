"""Bind visible period/unit evidence to generic family numeric columns.

This stage consumes an exactly replayed family row axis.  Local table headers
are preferred; document-wide period/unit observations are used only to resolve
relative labels or one unambiguous explicit inherited unit.  It is deliberately
bank-, path-, page-, note-, year- and schema-blind.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from itertools import combinations
from statistics import median
from typing import Any

from bctc_ai.evaluation.accounting_family_row_axis_v1 import (
    AccountingFamilyRowAxisV1Error,
    validate_accounting_family_row_axis_replay_v1,
)
from bctc_ai.evaluation.accounting_table_axes_v1 import (
    accounting_unit_surface_v1,
    center_x2_v1,
    extract_period_axis_v1,
    extract_reporting_year_axis_v1,
    infer_document_accounting_unit_context_v1,
    infer_document_reporting_period_context_v1,
    resolve_relative_period_axis_v1,
)
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.evaluation.adaptive_accounting_table_geometry_v1 import (
    median_text_height_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "AccountingFamilyColumnContextV1Error",
    "build_accounting_family_column_context_v1",
    "validate_accounting_family_column_context_replay_v1",
]


FORMAT_VERSION = "ACCOUNTING_FAMILY_COLUMN_CONTEXT_V1"
CLAIM_BOUNDARY = (
    "VISIBLE_LOCAL_OR_UNAMBIGUOUS_DOCUMENT_INHERITED_PERIOD_AND_UNIT_TO_BODY_"
    "DERIVED_COLUMN_PROPOSAL_ONLY_NO_NUMERIC_ACCOUNTING_POPULATION_SCHEMA_"
    "MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_file_note_page_or_fixed_year_used_for_routing": False,
    "document_unit_inheritance_requires_no_conflicting_explicit_unit": True,
    "mapping_authority": False,
    "numeric_authority": False,
    "period_axis_proposal_only": True,
    "raw_record_self_authenticating": False,
    "schema_authority": False,
    "unit_axis_proposal_only": True,
}
_RESULT_FIELDS = {
    "claim_boundary",
    "column_context_id",
    "document_period_context",
    "document_unit_context",
    "family_id",
    "format_version",
    "metrics",
    "period_axis",
    "period_semantics",
    "row_axis_id",
    "safety",
    "status",
    "unit_axis",
    "unresolved_reasons",
}
_PERIOD_FIELDS = {
    "column_center",
    "column_ordinal",
    "evidence_locations",
    "projection_status",
    "resolved_period",
}
_UNIT_FIELDS = {
    "column_center",
    "column_ordinal",
    "currency",
    "evidence_locations",
    "magnitude_power10",
    "projection_status",
    "unit_kind",
}
_METRIC_FIELDS = {"column_count", "period_column_count", "unit_column_count"}
_LOCATION_FIELDS = {"page_sequence", "source_line_index"}
_COMPARATIVE_QUALIFIERS = {
    "da kiem toan",
    "da soat xet",
    "da duoc kiem toan",
    "da duoc soat xet",
    "so lieu so sanh",
}


class AccountingFamilyColumnContextV1Error(ValueError):
    """The row-axis replay, context, projection, scalar type, or identity drifted."""


def _error(message: str) -> AccountingFamilyColumnContextV1Error:
    return AccountingFamilyColumnContextV1Error(message)


def _axis_pages(pages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "lines": [
                {
                    "bbox": canonical_clone_v1(line["bbox"]),
                    "source_line_index": line["line_ordinal"],
                    "vietocr_text": line["vietocr_text"],
                }
                for line in page["lines"]
            ],
            "page_sequence": page["page_sequence"],
        }
        for page in pages
    ]


def _header_lines(
    pages: Sequence[Mapping[str, Any]],
    region: Mapping[str, Any],
    centers: Sequence[float],
    rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], int] | None:
    value_rows = [row for row in rows if row["values"]]
    if not region["child_matches"] or not value_rows:
        return None
    header_start = region["cluster_start_document_line_ordinal"]
    first_body = min(
        (row["label_match"] for row in value_rows),
        key=lambda item: item["document_line_ordinal"],
    )
    header_stop = first_body["document_line_ordinal"]
    offset = 0
    selected: list[dict[str, Any]] = []
    page_sequences: set[int] = set()
    for page in pages:
        for line in page["lines"]:
            document_ordinal = offset + line["line_ordinal"]
            if header_start <= document_ordinal < header_stop:
                page_sequences.add(page["page_sequence"])
                selected.append(
                    {
                        "bbox": canonical_clone_v1(line["bbox"]),
                        "source_line_index": line["line_ordinal"],
                        "vietocr_text": line["vietocr_text"],
                    }
                )
        offset += len(page["lines"])
    # Period and unit bands may precede either an implied child cluster or an
    # explicit value-bearing parent row.  Extend the local header upward in a
    # page-local, text-height-bounded body-column band for both cases.  Only
    # period/unit parsers consume these extra lines; arbitrary preceding values
    # therefore cannot become an axis merely by proximity.
    if first_body["page_sequence"] == region["page_sequence"]:
        child_page = next(
            (page for page in pages if page["page_sequence"] == first_body["page_sequence"]),
            None,
        )
        if child_page is None:
            raise _error("implied-parent first-child page is absent from the document axis")
        child_lines = [
            line
            for line in child_page["lines"]
            if first_body["source_line_index"]
            <= line["line_ordinal"]
            <= first_body["end_source_line_index"]
        ]
        if not child_lines:
            raise _error("implied-parent first-child geometry is absent from its page")
        child_top = min(line["bbox"][1] for line in child_lines)
        scale = median_text_height_v1(child_page["lines"])
        lane_gap = (
            float(median(right - left for left, right in zip(centers, centers[1:], strict=False)))
            if len(centers) > 1
            else scale * 8.0
        )
        band_left = centers[0] - lane_gap * 0.5
        band_right = centers[-1] + lane_gap * 0.5
        # A body group label may sit between the family owner and a multi-row
        # period/unit header.  Ten median text rows covers the observed
        # page-level and nested header bands while remaining page-scale,
        # geometry-bounded, and independent of bank/family/year identities.
        lookback_top = child_top - scale * 10.0
        by_index = {line["source_line_index"]: line for line in selected}
        for line in child_page["lines"]:
            bbox = line["bbox"]
            if (
                line["line_ordinal"] < first_body["source_line_index"]
                and bbox[1] < child_top
                and bbox[3] >= lookback_top
                and bbox[2] >= band_left
                and bbox[0] <= band_right
            ):
                by_index[line["line_ordinal"]] = {
                    "bbox": canonical_clone_v1(bbox),
                    "source_line_index": line["line_ordinal"],
                    "vietocr_text": line["vietocr_text"],
                }
        selected = [by_index[index] for index in sorted(by_index)]
        page_sequences.add(first_body["page_sequence"])
    if not selected or len(page_sequences) != 1:
        return None
    return selected, next(iter(page_sequences))


def _lane_centers(axis: Mapping[str, Any]) -> list[float] | None:
    if not axis["rows"]:
        return None
    lane_count = (
        max(
            (value["column_ordinal"] for row in axis["rows"] for value in row["values"]),
            default=-1,
        )
        + 1
    )
    if lane_count <= 0:
        return None
    centers = []
    for lane in range(lane_count):
        values = [
            value
            for row in axis["rows"]
            for value in row["values"]
            if value["column_ordinal"] == lane
        ]
        if not values:
            return None
        centers.append(float(median(value["column_center"] for value in values)))
    return centers if centers == sorted(set(centers)) else None


def _project_records_to_lanes(
    records: Sequence[Mapping[str, Any]], centers: Sequence[float]
) -> list[tuple[int, Mapping[str, Any]]] | None:
    if len(records) != len(centers) or not centers:
        return None
    minimum_gap = (
        min(right - left for left, right in zip(centers, centers[1:], strict=False))
        if len(centers) > 1
        else max(centers[0] * 0.25, 1.0)
    )
    tolerance = max(minimum_gap * 0.55, 1.0)
    projected = []
    used: set[int] = set()
    for record in records:
        x_center = record["x_center_x2"] / 2
        lane = min(range(len(centers)), key=lambda item: abs(x_center - centers[item]))
        if lane in used or abs(x_center - centers[lane]) > tolerance:
            return None
        used.add(lane)
        projected.append((lane, record))
    return sorted(projected, key=lambda item: item[0]) if used == set(range(len(centers))) else None


def _expected_periods(context: Mapping[str, Any], semantics: str) -> list[str] | None:
    if semantics == "BALANCE_COMPARATIVE":
        values = [context["current_period_end"], context["balance_comparative_period_end"]]
    elif semantics == "CURRENT_ROLLFORWARD":
        values = [context["current_period_end"], context["current_period_start"]]
    else:
        raise _error("family period semantics drifted")
    return values if all(type(value) is str and value for value in values) else None


def _duplicate_current_date_rescue(
    records: Sequence[Mapping[str, Any]],
    header_lines: Sequence[Mapping[str, Any]],
    page_lines: Sequence[Mapping[str, Any]],
    document_context: Mapping[str, Any],
    semantics: str,
) -> list[dict[str, Any]] | None:
    """Resolve a qualified comparison column after one duplicated local date.

    The missing date is supplied only by repeated document-wide consensus and
    only when one audited/reviewed/comparative qualifier geometrically selects
    exactly one of the duplicate date columns.  Otherwise the caller remains
    unresolved instead of guessing from column order.
    """

    expected = _expected_periods(document_context, semantics)
    if (
        semantics != "BALANCE_COMPARATIVE"
        or expected is None
        or expected[0] == expected[1]
        or len(records) != 2
        or any(
            set(record)
            != {
                "evidence_source_line_indices",
                "resolved_period",
                "x_center_x2",
            }
            for record in records
        )
        or {record["resolved_period"] for record in records} != {expected[0]}
    ):
        return None
    ordered = sorted(records, key=lambda item: item["x_center_x2"])
    gap = ordered[1]["x_center_x2"] - ordered[0]["x_center_x2"]
    if type(gap) not in {int, float} or gap <= 0:
        return None
    candidates: list[tuple[int, int]] = []
    for line in header_lines:
        normalized = normalize_vietnamese_anchor_v1(line["vietocr_text"])
        if not any(qualifier in normalized for qualifier in _COMPARATIVE_QUALIFIERS):
            continue
        x_center = center_x2_v1(line)
        distances = [abs(x_center - record["x_center_x2"]) for record in ordered]
        selected = min(range(2), key=lambda index: distances[index])
        if distances[selected] <= gap * 0.45 and distances[selected] < distances[1 - selected]:
            candidates.append((selected, line["source_line_index"]))
    if len(candidates) != 1:
        return None
    comparative_index, qualifier_line_index = candidates[0]
    supporting_current_lines: set[int] = set()
    supporting_comparative_lines: set[int] = set()
    tolerance = gap * 0.45
    for left_index, left in enumerate(page_lines):
        for right in page_lines[left_index + 1 :]:
            left_bbox = left["bbox"]
            right_bbox = right["bbox"]
            left_height = left_bbox[3] - left_bbox[1]
            right_height = right_bbox[3] - right_bbox[1]
            if abs((left_bbox[1] + left_bbox[3]) - (right_bbox[1] + right_bbox[3])) > 2 * max(
                left_height, right_height
            ):
                continue
            axis, mode = extract_period_axis_v1([left, right])
            if mode != "LOCAL_EXACT_DATES" or {item["period"] for item in axis} != set(expected):
                continue
            by_period = {item["period"]: item for item in axis}
            current_lane = 1 - comparative_index
            if (
                abs(by_period[expected[0]]["x_center_x2"] - ordered[current_lane]["x_center_x2"])
                > tolerance
                or abs(
                    by_period[expected[1]]["x_center_x2"]
                    - ordered[comparative_index]["x_center_x2"]
                )
                > tolerance
            ):
                continue
            support_by_period = {
                item["period"]: item["evidence_source_line_indices"] for item in axis
            }
            supporting_current_lines.update(support_by_period[expected[0]])
            supporting_comparative_lines.update(support_by_period[expected[1]])
    if len(supporting_current_lines) < 2 or len(supporting_comparative_lines) < 2:
        return None
    rescued = []
    for index, record in enumerate(ordered):
        evidence = list(record["evidence_source_line_indices"])
        resolved_period = record["resolved_period"]
        if index == comparative_index:
            evidence = sorted(set([*evidence, qualifier_line_index, *supporting_comparative_lines]))
            resolved_period = expected[1]
        else:
            evidence = sorted(set([*evidence, *supporting_current_lines]))
        rescued.append(
            {
                "evidence_source_line_indices": evidence,
                "resolved_period": resolved_period,
                "x_center_x2": record["x_center_x2"],
            }
        )
    return rescued


def _local_period_records(
    header_lines: Sequence[Mapping[str, Any]],
    page_lines: Sequence[Mapping[str, Any]],
    document_context: Mapping[str, Any],
    semantics: str,
) -> tuple[list[dict[str, Any]], str]:
    axis, mode = extract_period_axis_v1(header_lines)
    if mode == "LOCAL_RELATIVE_PERIOD_ROLES":
        resolved, resolved_mode = resolve_relative_period_axis_v1(
            axis, document_context, period_semantics=semantics
        )
        return (
            [
                {
                    "evidence_source_line_indices": item["evidence_source_line_indices"],
                    "resolved_period": item["resolved_period"],
                    "x_center_x2": item["x_center_x2"],
                }
                for item in resolved
            ],
            resolved_mode,
        )
    if mode in {"LOCAL_EXACT_DATES", "LOCAL_SPLIT_DATES"}:
        records = [
            {
                "evidence_source_line_indices": item["evidence_source_line_indices"],
                "resolved_period": item["period"],
                "x_center_x2": item["x_center_x2"],
            }
            for item in axis
        ]
        rescued = _duplicate_current_date_rescue(
            records,
            header_lines,
            page_lines,
            document_context,
            semantics,
        )
        if rescued is not None:
            return (
                rescued,
                "LOCAL_DUPLICATED_CURRENT_DATE_COMPARATIVE_QUALIFIER_BOUND_TO_DOCUMENT_CONTEXT",
            )
        return records, mode
    # Do not silently downgrade an ambiguous set of full/split/relative period
    # surfaces to a coarser two-year axis.  The caller may still recover one
    # unique expected-period subset using document context plus lane geometry.
    if any(
        extract_period_axis_v1(subset)[1] != "UNRESOLVED"
        for subset_size in range(2, min(4, len(header_lines)) + 1)
        for subset in combinations(header_lines, subset_size)
    ):
        return [], "UNRESOLVED_MULTIPLE_LOCAL_PERIOD_SURFACES"
    years, year_mode = extract_reporting_year_axis_v1(header_lines)
    expected = _expected_periods(document_context, semantics)
    if year_mode != "VISIBLE_TWO_YEAR_REPORTING_AXIS" or expected is None:
        return [], "UNRESOLVED"
    by_year = {int(value[-4:]): value for value in expected}
    if set(by_year) != {item["year"] for item in years}:
        return [], "UNRESOLVED"
    return (
        [
            {
                "evidence_source_line_indices": item["evidence_source_line_indices"],
                "resolved_period": by_year[item["year"]],
                "x_center_x2": item["x_center_x2"],
            }
            for item in years
        ],
        "LOCAL_TWO_YEAR_AXIS_BOUND_TO_DOCUMENT_DATES",
    )


def _period_axis(
    header_lines: Sequence[Mapping[str, Any]],
    page_lines: Sequence[Mapping[str, Any]],
    header_page_sequence: int,
    centers: Sequence[float],
    document_context: Mapping[str, Any],
    semantics: str,
) -> list[dict[str, Any]]:
    records, mode = _local_period_records(
        header_lines,
        page_lines,
        document_context,
        semantics,
    )
    expected = _expected_periods(document_context, semantics)
    if expected is None:
        return []
    projected = (
        _project_records_to_lanes(records, centers)
        if {item["resolved_period"] for item in records} == set(expected)
        else None
    )
    if projected is None:
        # A bounded header lookback can legitimately include a narrative date
        # from the preceding disclosure paragraph.  Search the smallest
        # header subsets needed by the supported exact/split/relative/year
        # axis forms, then accept only one unique expected-period geometry.
        # The expected dates come from repeated document evidence; bank, page,
        # note and fixed-year identities never enter this choice.
        alternatives: dict[
            tuple[tuple[int, str, tuple[int, ...], int], ...],
            tuple[list[tuple[int, Mapping[str, Any]]], str],
        ] = {}
        for subset_size in range(2, min(4, len(header_lines)) + 1):
            for subset in combinations(header_lines, subset_size):
                subset_records, subset_mode = _local_period_records(
                    subset,
                    page_lines,
                    document_context,
                    semantics,
                )
                if {item["resolved_period"] for item in subset_records} != set(expected):
                    continue
                subset_projection = _project_records_to_lanes(subset_records, centers)
                if subset_projection is None:
                    continue
                key = tuple(
                    (
                        lane,
                        record["resolved_period"],
                        tuple(record["evidence_source_line_indices"]),
                        record["x_center_x2"],
                    )
                    for lane, record in subset_projection
                )
                alternatives[key] = (subset_projection, subset_mode)
        if len(alternatives) != 1:
            return []
        projected, mode = next(iter(alternatives.values()))
        mode += "_UNIQUE_EXPECTED_HEADER_SUBSET"
    if projected is None:
        return []
    return [
        {
            "column_center": centers[lane],
            "column_ordinal": lane,
            "evidence_locations": [
                {
                    "page_sequence": header_page_sequence,
                    "source_line_index": index,
                }
                for index in record["evidence_source_line_indices"]
            ],
            "projection_status": mode + "_PROJECTED_TO_BODY_COLUMN",
            "resolved_period": record["resolved_period"],
        }
        for lane, record in projected
    ]


def _local_unit_records(
    header_lines: Sequence[Mapping[str, Any]], header_page_sequence: int
) -> list[dict[str, Any]]:
    result = []
    for line in header_lines:
        parsed = accounting_unit_surface_v1(line["vietocr_text"])
        if parsed is None:
            continue
        result.append(
            {
                **parsed,
                "evidence_locations": [
                    {
                        "page_sequence": header_page_sequence,
                        "source_line_index": line["source_line_index"],
                    }
                ],
                "x_center_x2": center_x2_v1(line),
            }
        )
    return result


def _unit_record(
    lane: int,
    center: float,
    unit: Mapping[str, Any],
    *,
    status: str,
) -> dict[str, Any]:
    return {
        "column_center": center,
        "column_ordinal": lane,
        "currency": unit["currency"],
        "evidence_locations": canonical_clone_v1(unit["evidence_locations"]),
        "magnitude_power10": unit["magnitude_power10"],
        "projection_status": status,
        "unit_kind": unit["unit_kind"],
    }


def _unit_axis(
    header_lines: Sequence[Mapping[str, Any]],
    header_page_sequence: int,
    centers: Sequence[float],
    expected_kinds: Sequence[str],
    document_context: Mapping[str, Any],
) -> list[dict[str, Any]]:
    local = _local_unit_records(header_lines, header_page_sequence)
    if len(local) == len(centers):
        projected = _project_records_to_lanes(local, centers)
        if projected is not None and [record["unit_kind"] for _lane, record in projected] == list(
            expected_kinds
        ):
            return [
                _unit_record(
                    lane,
                    centers[lane],
                    record,
                    status="LOCAL_EXPLICIT_UNIT_PROJECTED_TO_BODY_COLUMN",
                )
                for lane, record in projected
            ]
    if len(local) == 1 and len(set(expected_kinds)) == 1:
        unit = local[0]
        if unit["unit_kind"] == expected_kinds[0]:
            return [
                _unit_record(
                    lane,
                    center,
                    unit,
                    status="LOCAL_EXPLICIT_SPANNING_UNIT_BROADCAST_TO_BODY_COLUMNS",
                )
                for lane, center in enumerate(centers)
            ]
    if (
        set(expected_kinds) == {"MONEY"}
        and document_context["unit_kind"] == "MONEY"
        and document_context["resolution"]
        in {
            "REPEATED_EXPLICIT_DOCUMENT_UNIT_CONSENSUS",
            "UNIQUE_EXPLICIT_DOCUMENT_UNIT_PROPOSAL",
        }
    ):
        inherited = {
            "currency": document_context["currency"],
            "evidence_locations": [
                {
                    "page_sequence": item["page_sequence"],
                    "source_line_index": item["source_line_index"],
                }
                for item in document_context["evidence"]
            ],
            "magnitude_power10": document_context["magnitude_power10"],
            "unit_kind": document_context["unit_kind"],
        }
        return [
            _unit_record(
                lane,
                center,
                inherited,
                status="UNAMBIGUOUS_EXPLICIT_DOCUMENT_UNIT_INHERITED_TO_BODY_COLUMNS",
            )
            for lane, center in enumerate(centers)
        ]
    return []


def _metrics(
    period_axis: Sequence[Any], unit_axis: Sequence[Any], lane_count: int
) -> dict[str, int]:
    return {
        "column_count": lane_count,
        "period_column_count": len(period_axis),
        "unit_column_count": len(unit_axis),
    }


def _valid_locations(value: Any) -> bool:
    return (
        type(value) is list
        and bool(value)
        and all(
            type(item) is dict
            and set(item) == _LOCATION_FIELDS
            and type(item["page_sequence"]) is int
            and item["page_sequence"] > 0
            and type(item["source_line_index"]) is int
            and item["source_line_index"] >= 0
            for item in value
        )
    )


def _validate_result(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _RESULT_FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["family_id"]) is not str
        or not value["family_id"]
        or type(value["row_axis_id"]) is not str
        or not value["row_axis_id"].startswith("afrav1:axis:")
        or value["period_semantics"] not in {"BALANCE_COMPARATIVE", "CURRENT_ROLLFORWARD"}
        or type(value["status"]) is not str
        or type(value["period_axis"]) is not list
        or type(value["unit_axis"]) is not list
        or type(value["unresolved_reasons"]) is not list
        or any(type(reason) is not str or not reason for reason in value["unresolved_reasons"])
        or type(value["metrics"]) is not dict
        or set(value["metrics"]) != _METRIC_FIELDS
        or any(type(metric) is not int or metric < 0 for metric in value["metrics"].values())
        or not same_typed_json_v1(
            value["metrics"],
            _metrics(value["period_axis"], value["unit_axis"], value["metrics"]["column_count"]),
        )
    ):
        raise _error("family column context result contract drifted")
    for expected_lane, item in enumerate(value["period_axis"]):
        if (
            type(item) is not dict
            or set(item) != _PERIOD_FIELDS
            or item["column_ordinal"] != expected_lane
            or type(item["column_center"]) is not float
            or not _valid_locations(item["evidence_locations"])
            or type(item["projection_status"]) is not str
            or not item["projection_status"]
            or type(item["resolved_period"]) is not str
            or not item["resolved_period"]
        ):
            raise _error("family period-column record drifted")
    for expected_lane, item in enumerate(value["unit_axis"]):
        if (
            type(item) is not dict
            or set(item) != _UNIT_FIELDS
            or item["column_ordinal"] != expected_lane
            or type(item["column_center"]) is not float
            or item["unit_kind"] not in {"MONEY", "PERCENT"}
            or (item["currency"] is not None and type(item["currency"]) is not str)
            or (
                item["magnitude_power10"] is not None and type(item["magnitude_power10"]) is not int
            )
            or not _valid_locations(item["evidence_locations"])
            or type(item["projection_status"]) is not str
            or not item["projection_status"]
        ):
            raise _error("family unit-column record drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("column_context_id")
    if identity != "afccv1:context:" + canonical_json_sha256_v1(material):
        raise _error("family column context identity drifted")
    return canonical_clone_v1(value)


def build_accounting_family_column_context_v1(
    row_axis: Any,
    pages: Any,
    family_topology_spec: Any,
    *,
    period_semantics: str,
    expected_lane_unit_kinds: Any,
    visible_dash_rescues: Any = (),
) -> dict[str, Any]:
    """Bind local/document period and unit evidence to every body-derived lane."""

    try:
        axis = validate_accounting_family_row_axis_replay_v1(
            row_axis,
            pages,
            family_topology_spec,
            visible_dash_rescues=visible_dash_rescues,
        )
    except AccountingFamilyRowAxisV1Error as exc:
        raise _error("family column context row-axis replay failed") from exc
    if type(expected_lane_unit_kinds) is not list or any(
        item not in {"MONEY", "PERCENT"} for item in expected_lane_unit_kinds
    ):
        raise _error("expected lane unit-kind declaration drifted")
    parsed_pages = canonical_clone_v1(pages)
    document_pages = _axis_pages(parsed_pages)
    document_period = infer_document_reporting_period_context_v1(document_pages)
    document_unit = infer_document_accounting_unit_context_v1(document_pages)
    centers = _lane_centers(axis)
    header = (
        _header_lines(parsed_pages, axis["topology_region"], centers, axis["rows"])
        if axis["topology_region"] is not None and centers is not None
        else None
    )
    period_axis: list[dict[str, Any]] = []
    unit_axis: list[dict[str, Any]] = []
    reasons = []
    if centers is None:
        reasons.append("BODY_DERIVED_COLUMN_AXIS_UNRESOLVED")
    elif len(expected_lane_unit_kinds) != len(centers):
        reasons.append("DECLARED_UNIT_KIND_AXIS_LENGTH_DIFFERS_FROM_BODY_COLUMNS")
    if axis["topology_region"] is not None and axis["topology_region"]["continuation_page_count"]:
        reasons.append("CROSS_PAGE_PERIOD_UNIT_INHERITANCE_NOT_PROVEN")
    if header is None:
        reasons.append("LOCAL_HEADER_REGION_UNRESOLVED")
    if centers is not None and header is not None:
        header_lines, header_page = header
        period_axis = _period_axis(
            header_lines,
            next(page["lines"] for page in document_pages if page["page_sequence"] == header_page),
            header_page,
            centers,
            document_period,
            period_semantics,
        )
        if len(expected_lane_unit_kinds) == len(centers):
            unit_axis = _unit_axis(
                header_lines,
                header_page,
                centers,
                expected_lane_unit_kinds,
                document_unit,
            )
        if len(period_axis) != len(centers):
            reasons.append("PERIOD_AXIS_NOT_BOUND_TO_EVERY_BODY_COLUMN")
        if len(unit_axis) != len(centers):
            reasons.append("UNIT_AXIS_NOT_BOUND_TO_EVERY_BODY_COLUMN")
    lane_count = len(centers or [])
    status = (
        "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
        if not reasons and lane_count > 0
        else "UNRESOLVED_PERIOD_UNIT_COLUMN_CONTEXT"
    )
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "document_period_context": document_period,
        "document_unit_context": document_unit,
        "family_id": axis["family_id"],
        "format_version": FORMAT_VERSION,
        "metrics": _metrics(period_axis, unit_axis, lane_count),
        "period_axis": period_axis,
        "period_semantics": period_semantics,
        "row_axis_id": axis["row_axis_id"],
        "safety": canonical_clone_v1(_SAFETY),
        "status": status,
        "unit_axis": unit_axis,
        "unresolved_reasons": reasons,
    }
    return _validate_result(
        {
            **material,
            "column_context_id": "afccv1:context:" + canonical_json_sha256_v1(material),
        }
    )


def validate_accounting_family_column_context_replay_v1(
    value: Any,
    row_axis: Any,
    pages: Any,
    family_topology_spec: Any,
    *,
    period_semantics: str,
    expected_lane_unit_kinds: Any,
    visible_dash_rescues: Any = (),
) -> dict[str, Any]:
    """Reject any period/unit/lane mutation by complete-input reconstruction."""

    persisted = _validate_result(value)
    expected = build_accounting_family_column_context_v1(
        row_axis,
        pages,
        family_topology_spec,
        period_semantics=period_semantics,
        expected_lane_unit_kinds=expected_lane_unit_kinds,
        visible_dash_rescues=visible_dash_rescues,
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("family column context does not replay exactly")
    return persisted
