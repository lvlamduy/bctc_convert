"""Bind PP-OCRv6 numeric cells to one unique loan-industry graph."""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))
sys.path.insert(0, os.fspath(PROJECT_ROOT / "src"))

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (  # noqa: E402
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from scripts.experiments import loan_industry_variant_graph_v1 as graph_v1  # noqa: E402
from scripts.experiments.loan_type_numeric_row_reconciliation_v1 import (  # noqa: E402
    _parsed_value,
)

FORMAT_VERSION = "LOAN_INDUSTRY_NUMERIC_ROW_RECONCILIATION_V1"
CLAIM_BOUNDARY = (
    "UNIQUE_LOAN_INDUSTRY_GRAPH_PPOCRV6_NUMERIC_ROW_CLUSTER_VISIBLE_UNMODELLED_"
    "ADDITIVE_ROW_TOTAL_CANDIDATE_AND_ACCOUNTING_RECONCILIATION_PROPOSAL_ONLY_"
    "MISSING_CELL_REQUIRES_PIXEL_DASH_OR_TARGETED_RECOGNITION_"
    "NO_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "accounting_equation_is_numeric_veto_not_sole_cell_authority": True,
    "blank_or_missing_cell_imputed_as_zero": False,
    "gemma4_used": False,
    "mapping_authority": False,
    "ppocrv6_same_line_numeric_proposal_authority": True,
    "schema_authority": False,
    "unmodelled_labeled_additive_rows_retained": True,
    "unmodelled_unlabeled_clusters_are_total_candidates_only": True,
    "vietocr_text_used_for_numeric_authority": False,
}
_FIELDS = {
    "accounting_checks",
    "authority",
    "claim_boundary",
    "family_id",
    "format_version",
    "graph_result_id",
    "intermediate_subtotals",
    "lane_types",
    "page_sequence",
    "result_id",
    "rows",
    "status",
    "total",
    "total_candidate_count",
    "total_selection",
    "unmodelled_additive_rows",
}


class LoanIndustryNumericRowReconciliationV1Error(ValueError):
    """The industry graph, PP numeric axis, or accounting closure drifted."""


def _error(message: str) -> LoanIndustryNumericRowReconciliationV1Error:
    return LoanIndustryNumericRowReconciliationV1Error(message)


def _cell(
    value: Mapping[str, Any],
    lines: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    lane = value["lane_index"]
    lane_type = value["lane_type"]
    index = value["source_line_index"]
    if index is None:
        return {
            "lane_index": lane,
            "lane_type": lane_type,
            "parsed_value": None,
            "ppocrv6_surface": None,
            "semantic_surface": None,
            "source_line_index": None,
            "status": "MISSING_CELL_REQUIRES_VISIBLE_DASH_OR_NUMERIC_RESCUE",
        }
    if type(index) is not int or not 0 <= index < len(lines):
        raise _error("industry graph numeric line locator drifted")
    line = lines[index]
    if line["source_line_index"] != index:
        raise _error("industry PP-OCRv6 line axis drifted")
    surface = line["source_text"]
    ppocr_surface = surface if type(surface) is str and surface.strip() else None
    parsed = _parsed_value(ppocr_surface, lane_type)
    return {
        "lane_index": lane,
        "lane_type": lane_type,
        "parsed_value": parsed,
        "ppocrv6_surface": ppocr_surface,
        "semantic_surface": value["semantic_surface"],
        "source_line_index": index,
        "status": (
            "PP_OCRV6_NUMERIC_PROPOSAL"
            if parsed is not None
            else "PP_OCRV6_NUMERIC_PARSE_UNRESOLVED"
        ),
    }


def _line_cell(
    line: Mapping[str, Any] | None,
    *,
    lane_index: int,
    lane_type: str,
) -> dict[str, Any]:
    if line is None:
        return {
            "lane_index": lane_index,
            "lane_type": lane_type,
            "parsed_value": None,
            "ppocrv6_surface": None,
            "semantic_surface": None,
            "source_line_index": None,
            "status": "MISSING_CELL_REQUIRES_VISIBLE_DASH_OR_NUMERIC_RESCUE",
        }
    ppocr = line.get("source_text")
    ppocr_surface = ppocr if type(ppocr) is str and ppocr.strip() else None
    parsed = _parsed_value(ppocr_surface, lane_type)
    return {
        "lane_index": lane_index,
        "lane_type": lane_type,
        "parsed_value": parsed,
        "ppocrv6_surface": ppocr_surface,
        "semantic_surface": line["vietocr_text"],
        "source_line_index": line["source_line_index"],
        "status": (
            "PP_OCRV6_NUMERIC_PROPOSAL"
            if parsed is not None
            else "PP_OCRV6_NUMERIC_PARSE_UNRESOLVED"
        ),
    }


def _cells(
    by_lane: Mapping[int, Mapping[str, Any]], lane_types: Sequence[str]
) -> list[dict[str, Any]]:
    return [
        _line_cell(by_lane.get(index), lane_index=index, lane_type=lane_type)
        for index, lane_type in enumerate(lane_types)
    ]


def _cluster_indices(cluster: Mapping[str, Any]) -> set[int]:
    return {line["source_line_index"] for line in cluster["by_lane"].values()}


def _label_for_unassigned_cluster(
    lines: Sequence[Mapping[str, Any]],
    cluster: Mapping[str, Any],
    *,
    excluded_indices: set[int],
    first_lane_center_x2: int,
) -> dict[str, Any] | None:
    center = cluster["center_x2"]
    candidates = []
    for line in lines:
        index = line["source_line_index"]
        normalized = normalize_vietnamese_anchor_v1(line["vietocr_text"])
        if (
            index in excluded_indices
            or graph_v1._line_is_number_like(line)
            or not normalized
            or normalized in {"tong", "tong cong"}
            or line["bbox"][2] * 2 >= first_lane_center_x2
            or line["bbox"][1] * 2 > center + 40
            or line["bbox"][3] * 2 < center - 220
        ):
            continue
        candidates.append(line)
    if not candidates:
        return None
    closest = min(
        candidates,
        key=lambda line: abs(line["bbox"][1] + line["bbox"][3] - center),
    )
    selected = [closest]
    for line in candidates:
        if line is closest:
            continue
        if abs(line["bbox"][1] + line["bbox"][3] - center) <= 200:
            selected.append(line)
    selected.sort(key=lambda line: (line["bbox"][1], line["bbox"][0]))
    surface = " ".join(line["vietocr_text"].strip() for line in selected).strip()
    return {
        "bbox": graph_v1._union_bbox(lines, [line["source_line_index"] for line in selected]),
        "source_line_indices": [line["source_line_index"] for line in selected],
        "surface": surface,
    }


def _candidate_key(cells: Sequence[Mapping[str, Any]]) -> tuple[int | None, ...]:
    return tuple(cell["source_line_index"] for cell in cells)


def _checks(
    rows: Sequence[Mapping[str, Any]],
    additive: Sequence[Mapping[str, Any]],
    total: Sequence[Mapping[str, Any]],
    lane_types: Sequence[str],
) -> list[dict[str, Any]]:
    checks = []
    all_rows = (*rows, *additive)
    for lane_index, lane_type in enumerate(lane_types):
        if lane_type != "MONEY":
            continue
        cells = [row["cells"][lane_index] for row in all_rows]
        observed = [cell["parsed_value"] for cell in cells]
        parsed = [item for item in observed if type(item) is int]
        missing_count = sum(item is None for item in observed)
        target = total[lane_index]["parsed_value"]
        exact = type(target) is int and sum(parsed) == target
        residual = None if type(target) is not int else sum(parsed) - target
        rounding_tolerance = max(1, (len(cells) + 1) // 2)
        semantic_agrees = all(
            cell["semantic_surface"] is None
            or _parsed_value(cell["semantic_surface"], "MONEY") == cell["parsed_value"]
            for cell in cells
        )
        companion_closes = False
        companion_lane = lane_index + 1
        if companion_lane < len(lane_types) and lane_types[companion_lane] == "PERCENT":
            companion_values = [row["cells"][companion_lane]["parsed_value"] for row in all_rows]
            companion_target = total[companion_lane]["parsed_value"]
            try:
                companion_closes = (
                    all(type(item) is str for item in companion_values)
                    and type(companion_target) is str
                    and sum((Decimal(item) for item in companion_values), Decimal(0))
                    == Decimal(companion_target)
                )
            except InvalidOperation:
                companion_closes = False
        rounded = (
            not exact
            and missing_count == 0
            and residual is not None
            and abs(residual) <= rounding_tolerance
            and semantic_agrees
            and companion_closes
        )
        checks.append(
            {
                "lane_index": lane_index,
                "missing_cell_count": missing_count,
                "observed_additive_sum": sum(parsed),
                "residual": residual,
                "rounding_tolerance_units": rounding_tolerance,
                "status": (
                    "EXACT_PP_NUMERIC_EQUATION"
                    if exact and missing_count == 0
                    else "EXACT_IF_MISSING_CELLS_ARE_VISIBLE_DASH_ZERO"
                    if exact
                    else "CORROBORATED_ROUNDED_SOURCE_EQUATION"
                    if rounded
                    else "UNRESOLVED_PP_NUMERIC_EQUATION"
                ),
                "target_total": target,
            }
        )
    return checks


def _checks_exact_or_pending(checks: Sequence[Mapping[str, Any]]) -> bool:
    return bool(checks) and all(
        item["status"]
        in {
            "CORROBORATED_ROUNDED_SOURCE_EQUATION",
            "EXACT_PP_NUMERIC_EQUATION",
            "EXACT_IF_MISSING_CELLS_ARE_VISIBLE_DASH_ZERO",
        }
        for item in checks
    )


def _validate_shape(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["family_id"] != graph_v1.FAMILY_ID
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["graph_result_id"]) is not str
        or not value["graph_result_id"].startswith("livgv1:result:")
        or type(value["page_sequence"]) is not int
        or value["page_sequence"] <= 0
        or type(value["lane_types"]) is not list
        or not value["lane_types"]
        or type(value["rows"]) is not list
        or type(value["unmodelled_additive_rows"]) is not list
        or type(value["intermediate_subtotals"]) is not list
        or type(value["total"]) is not list
        or type(value["total_candidate_count"]) is not int
        or value["total_candidate_count"] <= 0
        or type(value["total_selection"]) is not str
        or type(value["accounting_checks"]) is not list
        or value["status"]
        not in {
            "PP_NUMERIC_EXACT",
            "PP_NUMERIC_EXACT_PENDING_VISIBLE_DASH_EVIDENCE",
            "PP_NUMERIC_CORROBORATED_WITH_ROUNDING_TOLERANCE",
            "UNRESOLVED_PP_NUMERIC_RECONCILIATION",
        }
    ):
        raise _error("loan-industry numeric reconciliation fields drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "linrrv1:result:" + canonical_json_sha256_v1(material):
        raise _error("loan-industry numeric reconciliation identity drifted")
    return canonical_clone_v1(value)


def build_loan_industry_numeric_row_reconciliation_v1(
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Reconcile exact PP cells without changing graph structure or digits."""

    graph_result = graph_v1.build_loan_industry_variant_graph_document_v1(
        pages, enable_extended_annual_variants=True
    )
    if graph_result["status"] != "ACCEPTED_UNIQUE_VARIANT_GRAPH":
        raise _error("industry numeric reconciliation requires one unique graph")
    normalized_pages = graph_v1._pages(pages)
    graph = graph_result["graphs"][0]
    page = next(
        (item for item in normalized_pages if item["page_sequence"] == graph["page_sequence"]),
        None,
    )
    if page is None or page["primary_numeric_authority"] is not True:
        raise _error("industry numeric reconciliation requires the bound PP-OCRv6 axis")
    lines = page["lines"]
    lane_types = graph["lane_types"]
    first_row_line = min(row["label"]["source_line_indices"][0] for row in graph["rows"])
    clusters = graph_v1._numeric_row_clusters(
        lines,
        first_row_line,
        graph["table_source_line_range"][1] + 1,
        graph["lane_centers_x2"],
    )
    cluster_by_index = {
        index: cluster for cluster in clusters for index in _cluster_indices(cluster)
    }
    rows = []
    assigned_indices: set[int] = set()
    excluded_label_indices = set(graph["branch"]["source_line_indices"])
    context_indices = graph["customer_loan_context"].get("source_line_indices")
    if type(context_indices) is list:
        excluded_label_indices.update(context_indices)
    for row in graph["rows"]:
        excluded_label_indices.update(row["label"]["source_line_indices"])
        by_lane = {}
        for value in row["values"]:
            index = value["source_line_index"]
            if index is None:
                continue
            cluster = cluster_by_index.get(index)
            if cluster is None:
                raise _error("industry graph numeric locator is absent from PP row clusters")
            assigned_indices.update(_cluster_indices(cluster))
            by_lane.update(cluster["by_lane"])
        rows.append(
            {
                "cells": _cells(by_lane, lane_types),
                "label": canonical_clone_v1(row["label"]),
                "role": row["role"],
            }
        )

    graph_total_indices = {
        value["source_line_index"]
        for value in graph["total"]
        if value["source_line_index"] is not None
    }
    graph_total_cluster = next(
        (
            cluster
            for cluster in clusters
            if graph_total_indices and graph_total_indices <= _cluster_indices(cluster)
        ),
        None,
    )
    graph_total = (
        _cells(graph_total_cluster["by_lane"], lane_types)
        if graph_total_cluster is not None
        else [_cell(value, lines) for value in graph["total"]]
    )
    graph_total_key = _candidate_key(graph_total)
    candidates_by_key: dict[tuple[int | None, ...], list[dict[str, Any]]] = {
        graph_total_key: graph_total
    }
    additive = []
    subtotals = []
    for cluster in clusters:
        indices = _cluster_indices(cluster)
        cluster_cells = _cells(cluster["by_lane"], lane_types)
        key = _candidate_key(cluster_cells)
        if key == graph_total_key:
            assigned_indices.update(indices)
            continue
        if indices & assigned_indices:
            continue
        label = _label_for_unassigned_cluster(
            lines,
            cluster,
            excluded_indices=excluded_label_indices,
            first_lane_center_x2=graph["lane_centers_x2"][0],
        )
        if label is None:
            candidates_by_key[key] = cluster_cells
            subtotals.append({"cells": cluster_cells})
        else:
            excluded_label_indices.update(label["source_line_indices"])
            additive.append(
                {
                    "cells": cluster_cells,
                    "label": label,
                    "role": "UNMODELLED_ADDITIVE_OTHER",
                }
            )

    candidate_evaluations = [
        (cells, _checks(rows, additive, cells, lane_types)) for cells in candidates_by_key.values()
    ]
    exact_candidates = [
        (cells, checks)
        for cells, checks in candidate_evaluations
        if _checks_exact_or_pending(checks)
    ]
    if len(exact_candidates) == 1:
        total, checks = exact_candidates[0]
        total_selection = "UNIQUE_ACCOUNTING_CLOSED_TOTAL_CANDIDATE"
    else:
        total = graph_total
        checks = _checks(rows, additive, total, lane_types)
        total_selection = (
            "AMBIGUOUS_MULTIPLE_ACCOUNTING_CLOSED_TOTAL_CANDIDATES"
            if len(exact_candidates) > 1
            else "UNRESOLVED_NO_ACCOUNTING_CLOSED_TOTAL_CANDIDATE"
        )
    if checks and all(item["status"] == "EXACT_PP_NUMERIC_EQUATION" for item in checks):
        status = (
            "PP_NUMERIC_EXACT"
            if total_selection == "UNIQUE_ACCOUNTING_CLOSED_TOTAL_CANDIDATE"
            else "UNRESOLVED_PP_NUMERIC_RECONCILIATION"
        )
    elif (
        checks
        and any(item["status"] == "CORROBORATED_ROUNDED_SOURCE_EQUATION" for item in checks)
        and all(
            item["status"] in {"CORROBORATED_ROUNDED_SOURCE_EQUATION", "EXACT_PP_NUMERIC_EQUATION"}
            for item in checks
        )
    ):
        status = (
            "PP_NUMERIC_CORROBORATED_WITH_ROUNDING_TOLERANCE"
            if total_selection == "UNIQUE_ACCOUNTING_CLOSED_TOTAL_CANDIDATE"
            else "UNRESOLVED_PP_NUMERIC_RECONCILIATION"
        )
    elif checks and all(
        item["status"]
        in {"EXACT_PP_NUMERIC_EQUATION", "EXACT_IF_MISSING_CELLS_ARE_VISIBLE_DASH_ZERO"}
        for item in checks
    ):
        status = (
            "PP_NUMERIC_EXACT_PENDING_VISIBLE_DASH_EVIDENCE"
            if total_selection == "UNIQUE_ACCOUNTING_CLOSED_TOTAL_CANDIDATE"
            else "UNRESOLVED_PP_NUMERIC_RECONCILIATION"
        )
    else:
        status = "UNRESOLVED_PP_NUMERIC_RECONCILIATION"
    material = {
        "accounting_checks": checks,
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": graph_v1.FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "graph_result_id": graph_result["result_id"],
        "intermediate_subtotals": subtotals,
        "lane_types": canonical_clone_v1(lane_types),
        "page_sequence": graph["page_sequence"],
        "rows": rows,
        "status": status,
        "total": total,
        "total_candidate_count": len(candidates_by_key),
        "total_selection": total_selection,
        "unmodelled_additive_rows": additive,
    }
    return _validate_shape(
        {**material, "result_id": "linrrv1:result:" + canonical_json_sha256_v1(material)}
    )


def validate_loan_industry_numeric_row_reconciliation_replay_v1(
    value: Any,
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    expected = build_loan_industry_numeric_row_reconciliation_v1(pages)
    if not same_typed_json_v1(value, expected):
        raise _error("industry numeric reconciliation does not replay exactly")
    return expected
