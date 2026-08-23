"""Reconcile PP-OCRv6 numeric rows inside one unique loan-type variant graph.

VietOCR remains the semantic-label reader.  PP-OCRv6 supplies numeric cell
proposals.  Unmodelled visible additive rows are retained by geometry and may
later aggregate into the schema's ``Cho vay khac`` leaf; unlabeled numeric
clusters remain source-only subtotals.  Missing cells are never silently made
zero: exact equations can only mark them as requiring independent dash-pixel
evidence.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))
sys.path.insert(0, os.fspath(PROJECT_ROOT / "src"))

from bctc_ai.evaluation.accounting_table_axes_v1 import money_integer_v1  # noqa: E402
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (  # noqa: E402
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from scripts.experiments import loan_type_variant_graph_v1 as graph_v1  # noqa: E402

__all__ = [
    "FORMAT_VERSION",
    "LoanTypeNumericRowReconciliationV1Error",
    "build_loan_type_numeric_row_reconciliation_v1",
    "validate_loan_type_numeric_row_reconciliation_replay_v1",
]


FORMAT_VERSION = "LOAN_TYPE_NUMERIC_ROW_RECONCILIATION_V1"
CLAIM_BOUNDARY = (
    "UNIQUE_LOAN_TYPE_GRAPH_PP_OCRV6_NUMERIC_ROW_CLUSTER_VISIBLE_UNMODELLED_"
    "ADDITIVE_ROW_AND_ACCOUNTING_RECONCILIATION_PROPOSAL_ONLY_MISSING_CELL_"
    "REQUIRES_PIXEL_DASH_NO_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
FAMILY_ID = "LOAN_TYPE_CLASSIFICATION"
_AUTHORITY = {
    "accounting_equation_is_numeric_veto_not_sole_cell_authority": True,
    "blank_or_missing_cell_imputed_as_zero": False,
    "gemma4_used": False,
    "mapping_authority": False,
    "ppocrv6_numeric_proposal_authority": True,
    "schema_authority": False,
    "unmodelled_labeled_additive_rows_retained": True,
    "unmodelled_unlabeled_clusters_are_subtotals_only": True,
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
    "unmodelled_additive_rows",
}


class LoanTypeNumericRowReconciliationV1Error(ValueError):
    """The loan-type graph, PP numeric axis, or reconciliation drifted."""


def _error(message: str) -> LoanTypeNumericRowReconciliationV1Error:
    return LoanTypeNumericRowReconciliationV1Error(message)


def _parsed_value(surface: str | None, lane_type: str) -> int | str | None:
    if surface is None or not surface.strip():
        return None
    if lane_type == "MONEY":
        return money_integer_v1(surface)
    try:
        value = Decimal(surface.strip().replace("%", "").replace(",", "."))
    except Exception:  # Decimal exposes several string failure subclasses.
        return None
    return format(value, "f") if value.is_finite() else None


def _cell(
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
        _cell(by_lane.get(index), lane_index=index, lane_type=lane_type)
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
    candidates.sort(
        key=lambda line: (
            line["bbox"][1],
            line["bbox"][0],
            line["source_line_index"],
        )
    )
    # Retain only the closest vertically connected block.  This admits a
    # wrapped label while excluding a preceding parent or following footnote.
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


def _validate_shape(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["family_id"] != FAMILY_ID
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["graph_result_id"]) is not str
        or not value["graph_result_id"].startswith("ltvgv1:result:")
        or type(value["page_sequence"]) is not int
        or value["page_sequence"] <= 0
        or type(value["lane_types"]) is not list
        or not value["lane_types"]
        or any(item not in {"MONEY", "PERCENT"} for item in value["lane_types"])
        or type(value["rows"]) is not list
        or type(value["unmodelled_additive_rows"]) is not list
        or type(value["intermediate_subtotals"]) is not list
        or type(value["total"]) is not list
        or type(value["accounting_checks"]) is not list
        or value["status"]
        not in {
            "PP_NUMERIC_EXACT",
            "PP_NUMERIC_EXACT_PENDING_VISIBLE_DASH_EVIDENCE",
            "UNRESOLVED_PP_NUMERIC_RECONCILIATION",
        }
    ):
        raise _error("loan-type numeric reconciliation fields drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "ltnrrv1:result:" + canonical_json_sha256_v1(material):
        raise _error("loan-type numeric reconciliation identity drifted")
    return canonical_clone_v1(value)


def build_loan_type_numeric_row_reconciliation_v1(
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build the exact PP numeric reconciliation for one complete document."""

    graph_result = graph_v1.build_loan_type_variant_graph_document_v1(
        pages, enable_extended_owner_table_variants=True
    )
    if graph_result["status"] != "ACCEPTED_UNIQUE_VARIANT_GRAPH":
        raise _error("numeric reconciliation requires one unique loan-type graph")
    normalized_pages = graph_v1._pages(pages)
    graph = graph_result["graphs"][0]
    page = next(
        (item for item in normalized_pages if item["page_sequence"] == graph["page_sequence"]),
        None,
    )
    if page is None or page["primary_numeric_authority"] is not True:
        raise _error("numeric reconciliation requires the bound PP-OCRv6 surface")
    lines = page["lines"]
    lane_types = graph["lane_types"]
    clusters = graph_v1._numeric_row_clusters(
        lines,
        min(row["label"]["source_line_indices"][0] for row in graph["rows"]),
        graph["table_source_line_range"][1] + 1,
        graph["lane_centers_x2"],
    )
    cluster_by_index = {
        index: cluster for cluster in clusters for index in _cluster_indices(cluster)
    }
    rows = []
    assigned_indices: set[int] = set()
    excluded_label_indices = set(graph["owner"]["source_line_indices"])
    for row in graph["rows"]:
        excluded_label_indices.update(row["label"]["source_line_indices"])
        by_lane = {}
        for value in row["values"]:
            index = value["source_line_index"]
            if index is None:
                continue
            cluster = cluster_by_index.get(index)
            if cluster is None:
                raise _error("graph numeric locator is absent from PP row clusters")
            assigned_indices.update(_cluster_indices(cluster))
            by_lane.update(cluster["by_lane"])
        rows.append(
            {
                "cells": _cells(by_lane, lane_types),
                "label": canonical_clone_v1(row["label"]),
                "role": row["role"],
            }
        )
    total_indices = {item["source_line_index"] for item in graph["total"]}
    total_cluster = next(
        (cluster for cluster in clusters if total_indices <= _cluster_indices(cluster)), None
    )
    if total_cluster is None:
        raise _error("graph final total is absent from PP row clusters")
    assigned_indices.update(_cluster_indices(total_cluster))

    additive = []
    subtotals = []
    for cluster in clusters:
        indices = _cluster_indices(cluster)
        if indices & assigned_indices:
            continue
        label = _label_for_unassigned_cluster(
            lines,
            cluster,
            excluded_indices=excluded_label_indices,
            first_lane_center_x2=graph["lane_centers_x2"][0],
        )
        record = {"cells": _cells(cluster["by_lane"], lane_types)}
        if label is None:
            subtotals.append(record)
        else:
            excluded_label_indices.update(label["source_line_indices"])
            additive.append({**record, "label": label, "role": "UNMODELLED_ADDITIVE_OTHER"})

    total = _cells(total_cluster["by_lane"], lane_types)
    checks = []
    for lane_index, lane_type in enumerate(lane_types):
        if lane_type != "MONEY":
            continue
        known = [row["cells"][lane_index] for row in rows]
        extras = [row["cells"][lane_index] for row in additive]
        target = total[lane_index]["parsed_value"]
        observed = [cell["parsed_value"] for cell in (*known, *extras)]
        parsed = [item for item in observed if type(item) is int]
        missing_count = sum(item is None for item in observed)
        exact = type(target) is int and sum(parsed) == target
        status = (
            "EXACT_PP_NUMERIC_EQUATION"
            if exact and missing_count == 0
            else "EXACT_IF_MISSING_CELLS_ARE_VISIBLE_DASH_ZERO"
            if exact
            else "UNRESOLVED_PP_NUMERIC_EQUATION"
        )
        checks.append(
            {
                "lane_index": lane_index,
                "missing_cell_count": missing_count,
                "observed_additive_sum": sum(parsed),
                "status": status,
                "target_total": target,
            }
        )
    if checks and all(item["status"] == "EXACT_PP_NUMERIC_EQUATION" for item in checks):
        status = "PP_NUMERIC_EXACT"
    elif checks and all(
        item["status"]
        in {"EXACT_PP_NUMERIC_EQUATION", "EXACT_IF_MISSING_CELLS_ARE_VISIBLE_DASH_ZERO"}
        for item in checks
    ):
        status = "PP_NUMERIC_EXACT_PENDING_VISIBLE_DASH_EVIDENCE"
    else:
        status = "UNRESOLVED_PP_NUMERIC_RECONCILIATION"
    material = {
        "accounting_checks": checks,
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "graph_result_id": graph_result["result_id"],
        "intermediate_subtotals": subtotals,
        "lane_types": canonical_clone_v1(lane_types),
        "page_sequence": graph["page_sequence"],
        "rows": rows,
        "status": status,
        "total": total,
        "unmodelled_additive_rows": additive,
    }
    return _validate_shape(
        {
            **material,
            "result_id": "ltnrrv1:result:" + canonical_json_sha256_v1(material),
        }
    )


def validate_loan_type_numeric_row_reconciliation_replay_v1(
    value: Any,
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Exact-rebuild a reconciliation from its bound text/number geometry."""

    observed = _validate_shape(value)
    expected = build_loan_type_numeric_row_reconciliation_v1(pages)
    if not same_typed_json_v1(observed, expected):
        raise _error("loan-type numeric reconciliation does not replay exactly")
    return expected
