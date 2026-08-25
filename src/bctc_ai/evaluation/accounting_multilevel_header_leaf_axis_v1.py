"""Project a resolved multi-level accounting header onto typed body leaves.

This primitive is deliberately page-, family-, bank-, note-, year- and
schema-blind.  It reuses :func:`build_multilevel_header_graph_v1` as the sole
geometry engine, then adds only the semantic checks needed to propagate two
visible balance-period parents to their MONEY/PERCENT leaf columns.

Currency and magnitude are not inferred here.  A leaf headed ``Giá trị`` is a
MONEY lane, but its VND/scale still has to be proved by the existing local or
document accounting-unit gate.  Any incomplete parent partition, ambiguous
period, ambiguous leaf kind, or graph ambiguity affecting the projected axis
produces an empty unresolved leaf axis.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.evaluation.accounting_table_axes_v1 import (
    AccountingTableAxesV1Error,
    accounting_unit_surface_v1,
    extract_period_axis_v1,
    resolve_relative_period_axis_v1,
)
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.evaluation.adaptive_accounting_table_geometry_v1 import (
    AdaptiveAccountingTableGeometryV1Error,
    build_multilevel_header_graph_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "AccountingMultilevelHeaderLeafAxisV1Error",
    "build_accounting_multilevel_header_leaf_axis_v1",
    "validate_accounting_multilevel_header_leaf_axis_replay_v1",
]


FORMAT_VERSION = "ACCOUNTING_MULTILEVEL_HEADER_LEAF_AXIS_V1"
CLAIM_BOUNDARY = (
    "VISIBLE_TWO_PERIOD_PARENT_EXACT_PARTITION_AND_EXPLICIT_HEADER_LEAF_KIND_"
    "PROPAGATION_TO_BODY_COLUMNS_PROPOSAL_ONLY_NO_CURRENCY_MAGNITUDE_NUMERIC_"
    "ACCOUNTING_POPULATION_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_file_note_page_or_fixed_year_used_for_routing": False,
    "currency_or_magnitude_inferred_from_money_lane_kind": False,
    "header_geometry_reuses_shared_multilevel_graph": True,
    "mapping_authority": False,
    "merged_period_without_word_boxes_can_resolve": False,
    "numeric_authority": False,
    "period_parent_partition_must_be_exact": True,
    "period_unit_axis_proposal_only": True,
    "provider_sequence_used_as_visual_order": False,
    "schema_authority": False,
}
_RESULT_FIELDS = {
    "axis_id",
    "claim_boundary",
    "expected_lane_kinds",
    "format_version",
    "header_graph",
    "leaf_axis",
    "metrics",
    "period_resolution_mode",
    "safety",
    "status",
    "unresolved_reasons",
}
_METRIC_FIELDS = {"column_count", "period_parent_count", "typed_leaf_count"}
_LEAF_FIELDS = {
    "column_center",
    "column_ordinal",
    "header_cell_id",
    "header_evidence_source_line_indices",
    "header_surface",
    "lane_kind",
    "lane_kind_resolution",
    "period_evidence_source_line_indices",
    "period_parent_cell_ids",
    "period_parent_column_start",
    "period_parent_column_stop",
    "resolved_period",
}
_PERIOD_CONTEXT_FIELDS = {
    "balance_comparative_period_end",
    "current_period_end",
    "current_period_start",
    "flow_comparative_period_end",
    "flow_comparative_period_start",
    "observed_dates",
    "period_kind",
    "reporting_year",
    "resolution",
    "supporting_page_count",
}
_EXACT_MONEY_LEAF_HEADERS = {
    "du no",
    "gia tri",
    "so du",
    "so tien",
}
_EXACT_PERCENT_LEAF_HEADERS = {
    "ty le",
    "ty trong",
}
_FULL_DATE_SURFACE = re.compile(r"(?<!\d)\d{1,2}\s*[./-]\s*\d{1,2}\s*[./-]\s*\d{4}(?!\d)")
_VIETNAMESE_FULL_DATE_SURFACE = re.compile(
    r"(?<!\d)(?:ngay\s+)?\d{1,2}\s+thang\s+\d{1,2}\s+nam\s+\d{4}(?!\d)"
)
_RELATIVE_PERIOD_SURFACE = re.compile(r"\b(?:so cuoi ky|so cuoi nam|so dau ky|so dau nam)\b")


class AccountingMultilevelHeaderLeafAxisV1Error(ValueError):
    """The typed header input, result contract, identity, or replay drifted."""


def _error(message: str) -> AccountingMultilevelHeaderLeafAxisV1Error:
    return AccountingMultilevelHeaderLeafAxisV1Error(message)


def _canonical_header_lines(value: Any) -> list[dict[str, Any]]:
    if type(value) is not list or not value:
        raise _error("multilevel leaf axis requires one nonempty header line list")
    lines = canonical_clone_v1(value)
    source_indices: set[int] = set()
    for line in lines:
        if type(line) is not dict:
            raise _error("multilevel leaf header line must be one exact mapping")
        bbox = line.get("bbox")
        source_index = line.get("source_line_index")
        text = line.get("vietocr_text")
        if (
            type(bbox) is not list
            or len(bbox) != 4
            or any(type(item) is not int for item in bbox)
            or bbox[0] < 0
            or bbox[1] < 0
            or bbox[2] <= bbox[0]
            or bbox[3] <= bbox[1]
            or type(source_index) is not int
            or source_index < 0
            or source_index in source_indices
            or type(text) is not str
            or not text.strip()
        ):
            raise _error("multilevel leaf header geometry/index/text drifted")
        source_indices.add(source_index)
    # Provider serialization order is not a visual axis.  Sorting before the
    # shared graph also makes its generated cell IDs stable under list reorder.
    return sorted(
        lines,
        key=lambda line: (
            line["bbox"][1],
            line["bbox"][0],
            line["bbox"][3],
            line["bbox"][2],
            line["source_line_index"],
            line["vietocr_text"],
        ),
    )


def _visible_period_token_count(surface: str) -> int:
    normalized = normalize_vietnamese_anchor_v1(surface)
    return (
        len(_FULL_DATE_SURFACE.findall(surface))
        + len(_VIETNAMESE_FULL_DATE_SURFACE.findall(normalized))
        + len(_RELATIVE_PERIOD_SURFACE.findall(normalized))
    )


def _merged_period_surface_lacks_word_boxes(lines: Sequence[Mapping[str, Any]]) -> bool:
    """Reject a multi-period OCR surface unless boxes split exact period tokens."""

    for line in lines:
        surface_count = _visible_period_token_count(line["vietocr_text"])
        tokens = line.get("tokens")
        token_boxes = line.get("token_bboxes")
        if tokens is None:
            if surface_count > 1:
                return True
            continue
        if type(tokens) is not list:
            continue
        token_counts = [
            _visible_period_token_count(token) if type(token) is str else 0 for token in tokens
        ]
        token_period_count = sum(token_counts)
        if max(surface_count, token_period_count) <= 1:
            continue
        if (
            type(token_boxes) is not list
            or len(token_boxes) != len(tokens)
            or token_period_count != surface_count
            or any(count > 1 for count in token_counts)
        ):
            return True
    return False


def _inputs(
    column_centers: Any,
    page_width: Any,
    document_period_context: Any,
    period_semantics: Any,
    expected_lane_kinds: Any,
) -> tuple[list[float], dict[str, Any], list[str]]:
    if (
        type(column_centers) is not list
        or len(column_centers) < 2
        or any(type(center) is not float for center in column_centers)
        or column_centers != sorted(set(column_centers))
        or type(page_width) is not int
        or page_width <= 0
        or any(not 0 <= center <= page_width for center in column_centers)
    ):
        raise _error("multilevel leaf body-column geometry drifted")
    if (
        type(expected_lane_kinds) is not list
        or len(expected_lane_kinds) != len(column_centers)
        or any(kind not in {"MONEY", "PERCENT"} for kind in expected_lane_kinds)
    ):
        raise _error("multilevel leaf expected lane-kind declaration drifted")
    if period_semantics != "BALANCE_COMPARATIVE":
        raise _error("multilevel leaf period semantics must be BALANCE_COMPARATIVE")
    if (
        type(document_period_context) is not dict
        or set(document_period_context) != _PERIOD_CONTEXT_FIELDS
    ):
        raise _error("multilevel leaf document-period context fields drifted")
    return (
        list(column_centers),
        canonical_clone_v1(document_period_context),
        list(expected_lane_kinds),
    )


def _graph_period_records(
    graph: Mapping[str, Any],
    document_period_context: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], str, str | None]:
    cells = [cell for cell in graph["cells"] if cell["column_start"] is not None]
    semantic_lines = [
        {
            "bbox": canonical_clone_v1(cell["bbox"]),
            "source_line_index": ordinal,
            "vietocr_text": cell["text"],
        }
        for ordinal, cell in enumerate(cells)
    ]
    try:
        raw_axis, mode = extract_period_axis_v1(semantic_lines)
        if mode == "LOCAL_RELATIVE_PERIOD_ROLES":
            resolved, resolved_mode = resolve_relative_period_axis_v1(
                raw_axis,
                document_period_context,
                period_semantics="BALANCE_COMPARATIVE",
            )
            records = [
                {
                    "cell_ordinals": item["evidence_source_line_indices"],
                    "resolved_period": item["resolved_period"],
                }
                for item in resolved
            ]
            mode = resolved_mode
        elif mode in {"LOCAL_EXACT_DATES", "LOCAL_SPLIT_DATES"}:
            records = [
                {
                    "cell_ordinals": item["evidence_source_line_indices"],
                    "resolved_period": item["period"],
                }
                for item in raw_axis
            ]
        else:
            records = []
    except AccountingTableAxesV1Error as exc:
        raise _error("multilevel leaf period parser input drifted") from exc
    if len(records) != 2:
        return [], mode, "EXACTLY_TWO_PERIOD_PARENTS_NOT_RESOLVED"
    expected = [
        document_period_context["current_period_end"],
        document_period_context["balance_comparative_period_end"],
    ]
    if any(type(period) is not str or not period for period in expected):
        return [], mode, "DOCUMENT_BALANCE_PERIOD_CONTEXT_UNRESOLVED"
    if len(set(expected)) != 2 or {record["resolved_period"] for record in records} != set(
        expected
    ):
        return [], mode, "VISIBLE_PERIOD_PARENTS_DIFFER_FROM_DOCUMENT_BALANCE_PERIODS"

    expanded = []
    for record in records:
        evidence_cells = [cells[ordinal] for ordinal in record["cell_ordinals"]]
        spans = {
            (cell["column_start"], cell["column_stop"])
            for cell in evidence_cells
            if cell["column_start"] is not None
        }
        if len(spans) != 1:
            return [], mode, "PERIOD_PARENT_FRAGMENTS_DO_NOT_SHARE_ONE_COLUMN_SPAN"
        start, stop = next(iter(spans))
        expanded.append(
            {
                "cell_ids": sorted(cell["cell_id"] for cell in evidence_cells),
                "column_start": start,
                "column_stop": stop,
                "evidence_source_line_indices": sorted(
                    {cell["source_line_index"] for cell in evidence_cells}
                ),
                "resolved_period": record["resolved_period"],
            }
        )
    return (
        sorted(expanded, key=lambda item: (item["column_start"], item["column_stop"])),
        mode,
        None,
    )


def _lane_kind(cell: Mapping[str, Any]) -> tuple[str, str] | None:
    try:
        explicit = accounting_unit_surface_v1(cell["text"])
    except AccountingTableAxesV1Error as exc:
        raise _error("multilevel leaf unit parser input drifted") from exc
    if explicit is not None:
        return explicit["unit_kind"], "EXPLICIT_ACCOUNTING_UNIT_SURFACE"
    normalized = normalize_vietnamese_anchor_v1(cell["text"])
    if normalized in _EXACT_MONEY_LEAF_HEADERS:
        return "MONEY", "EXACT_SEMANTIC_MONEY_HEADER"
    if normalized in _EXACT_PERCENT_LEAF_HEADERS:
        return "PERCENT", "EXACT_SEMANTIC_PERCENT_HEADER"
    return None


def _typed_leaf_candidates(
    graph: Mapping[str, Any],
    parents: Sequence[Mapping[str, Any]],
    expected_lane_kinds: Sequence[str],
) -> tuple[list[dict[str, Any]], str | None]:
    candidates_by_lane: dict[int, list[dict[str, Any]]] = {
        ordinal: [] for ordinal in range(len(expected_lane_kinds))
    }
    for cell in graph["cells"]:
        start = cell["column_start"]
        stop = cell["column_stop"]
        if start is None or stop != start + 1:
            # A table-level unit is context evidence, not a leaf kind.  Its
            # currency/scale remains the responsibility of the existing unit
            # context gate used by the caller.
            continue
        classified = _lane_kind(cell)
        if classified is None:
            continue
        lane_kind, resolution = classified
        candidates_by_lane[start].append(
            {
                "cell": cell,
                "lane_kind": lane_kind,
                "lane_kind_resolution": resolution,
            }
        )
    if any(len(candidates) != 1 for candidates in candidates_by_lane.values()):
        return [], "EACH_BODY_COLUMN_REQUIRES_ONE_UNAMBIGUOUS_TYPED_HEADER_LEAF"
    candidates = [candidates_by_lane[ordinal][0] for ordinal in range(len(expected_lane_kinds))]
    if [candidate["lane_kind"] for candidate in candidates] != list(expected_lane_kinds):
        return [], "VISIBLE_HEADER_LEAF_KINDS_DIFFER_FROM_DECLARED_BODY_LANES"

    parent_by_cell_id = {cell_id: parent for parent in parents for cell_id in parent["cell_ids"]}
    edges_by_child: dict[str, list[Mapping[str, Any]]] = {}
    for edge in graph["edges"]:
        edges_by_child.setdefault(edge["child_cell_id"], []).append(edge)
    result = []
    for ordinal, candidate in enumerate(candidates):
        cell = candidate["cell"]
        parent_edges = [
            edge
            for edge in edges_by_child.get(cell["cell_id"], [])
            if edge["parent_cell_id"] in parent_by_cell_id
        ]
        if len(parent_edges) != 1:
            return [], "TYPED_HEADER_LEAF_LACKS_ONE_UNIQUE_PERIOD_PARENT_EDGE"
        parent = parent_by_cell_id[parent_edges[0]["parent_cell_id"]]
        if not parent["column_start"] <= ordinal < parent["column_stop"]:
            return [], "TYPED_HEADER_LEAF_EDGE_CROSSES_PERIOD_PARTITION"
        result.append(
            {
                "column_center": graph["column_centers"][ordinal],
                "column_ordinal": ordinal,
                "header_cell_id": cell["cell_id"],
                "header_evidence_source_line_indices": [cell["source_line_index"]],
                "header_surface": cell["text"],
                "lane_kind": candidate["lane_kind"],
                "lane_kind_resolution": candidate["lane_kind_resolution"],
                "period_evidence_source_line_indices": canonical_clone_v1(
                    parent["evidence_source_line_indices"]
                ),
                "period_parent_cell_ids": canonical_clone_v1(parent["cell_ids"]),
                "period_parent_column_start": parent["column_start"],
                "period_parent_column_stop": parent["column_stop"],
                "resolved_period": parent["resolved_period"],
            }
        )
    signatures = [
        tuple(
            leaf["lane_kind"]
            for leaf in result
            if parent["column_start"] <= leaf["column_ordinal"] < parent["column_stop"]
        )
        for parent in parents
    ]
    if len(set(signatures)) != 1:
        return [], "PERIOD_PARENT_LEAF_KIND_SEQUENCES_DIFFER"
    return result, None


def _axis_graph_ambiguity_reasons(
    graph: Mapping[str, Any],
    parents: Sequence[Mapping[str, Any]],
    leaves: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Reject graph ambiguity only when it can affect the projected axis.

    The bounded header region may retain an owner or stub just left of the
    numeric grid.  A low-confidence span on that unrelated text is not a
    period/leaf ambiguity.  Level-wide assignment failure and ambiguity on a
    participating period/leaf cell still fail closed.
    """

    relevant_cell_ids = {
        *(cell_id for parent in parents for cell_id in parent["cell_ids"]),
        *(leaf["header_cell_id"] for leaf in leaves),
    }
    relevant_levels = {
        level
        for cell in graph["cells"]
        if cell["cell_id"] in relevant_cell_ids
        for level in range(cell["level_start"], cell["level_stop"])
    }
    reasons = []
    for ambiguity in graph["ambiguities"]:
        kind = ambiguity["kind"]
        if kind in {
            "MERGED_HEADER_ORDER_ONLY_WITHOUT_WORD_BOXES",
            "MERGED_HEADER_TOKEN_GRID_AMBIGUOUS",
        }:
            reasons.append("MERGED_PERIOD_OR_LEAF_HEADER_WITHOUT_WORD_BOXES_UNRESOLVED")
        elif ambiguity.get("cell_id") in relevant_cell_ids:
            reasons.append("SHARED_MULTILEVEL_HEADER_GRAPH_AMBIGUOUS_ON_PROJECTED_AXIS")
        elif kind == "NON_CROSSING_COLUMN_SPAN_ASSIGNMENT_FAILED" and any(
            level in relevant_levels
            for level in range(ambiguity["level_start"], ambiguity["level_stop"])
        ):
            reasons.append("SHARED_MULTILEVEL_HEADER_GRAPH_AMBIGUOUS_ON_PROJECTED_AXIS")
    return reasons


def _validate_result(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _RESULT_FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or value["status"]
        not in {
            "MULTILEVEL_HEADER_LEAF_AXIS_BOUND_PROPOSAL_ONLY",
            "UNRESOLVED_MULTILEVEL_HEADER_LEAF_AXIS",
        }
        or type(value["expected_lane_kinds"]) is not list
        or any(kind not in {"MONEY", "PERCENT"} for kind in value["expected_lane_kinds"])
        or type(value["header_graph"]) is not dict
        or value["header_graph"].get("format_version")
        != "ADAPTIVE_ACCOUNTING_MULTILEVEL_HEADER_GRAPH_V1"
        or type(value["period_resolution_mode"]) is not str
        or not value["period_resolution_mode"]
        or type(value["leaf_axis"]) is not list
        or type(value["unresolved_reasons"]) is not list
        or any(type(reason) is not str or not reason for reason in value["unresolved_reasons"])
        or type(value["metrics"]) is not dict
        or set(value["metrics"]) != _METRIC_FIELDS
        or any(type(metric) is not int or metric < 0 for metric in value["metrics"].values())
        or value["metrics"]["column_count"] != len(value["expected_lane_kinds"])
        or value["metrics"]["typed_leaf_count"] != len(value["leaf_axis"])
        or (value["status"].startswith("UNRESOLVED") and value["leaf_axis"])
        or (
            value["status"] == "MULTILEVEL_HEADER_LEAF_AXIS_BOUND_PROPOSAL_ONLY"
            and (
                value["unresolved_reasons"]
                or len(value["leaf_axis"]) != len(value["expected_lane_kinds"])
                or value["metrics"]["period_parent_count"] != 2
            )
        )
    ):
        raise _error("multilevel header leaf-axis result contract drifted")
    for ordinal, leaf in enumerate(value["leaf_axis"]):
        if (
            type(leaf) is not dict
            or set(leaf) != _LEAF_FIELDS
            or leaf["column_ordinal"] != ordinal
            or type(leaf["column_center"]) is not float
            or type(leaf["header_cell_id"]) is not str
            or not leaf["header_cell_id"]
            or type(leaf["header_surface"]) is not str
            or not leaf["header_surface"]
            or leaf["lane_kind"] != value["expected_lane_kinds"][ordinal]
            or leaf["lane_kind_resolution"]
            not in {
                "EXPLICIT_ACCOUNTING_UNIT_SURFACE",
                "EXACT_SEMANTIC_MONEY_HEADER",
                "EXACT_SEMANTIC_PERCENT_HEADER",
            }
            or type(leaf["resolved_period"]) is not str
            or not leaf["resolved_period"]
            or type(leaf["period_parent_column_start"]) is not int
            or type(leaf["period_parent_column_stop"]) is not int
            or not leaf["period_parent_column_start"] <= ordinal < leaf["period_parent_column_stop"]
        ):
            raise _error("multilevel header typed leaf record drifted")
        for field in (
            "header_evidence_source_line_indices",
            "period_evidence_source_line_indices",
        ):
            indices = leaf[field]
            if (
                type(indices) is not list
                or not indices
                or any(type(index) is not int or index < 0 for index in indices)
                or indices != sorted(set(indices))
            ):
                raise _error("multilevel header leaf evidence axis drifted")
        parent_ids = leaf["period_parent_cell_ids"]
        if (
            type(parent_ids) is not list
            or not parent_ids
            or any(type(cell_id) is not str or not cell_id for cell_id in parent_ids)
            or parent_ids != sorted(set(parent_ids))
        ):
            raise _error("multilevel header period-parent cell axis drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("axis_id")
    if identity != "amhlav1:axis:" + canonical_json_sha256_v1(material):
        raise _error("multilevel header leaf-axis identity drifted")
    return canonical_clone_v1(value)


def build_accounting_multilevel_header_leaf_axis_v1(
    header_lines: Any,
    *,
    column_centers: Any,
    page_width: Any,
    document_period_context: Any,
    period_semantics: str,
    expected_lane_kinds: Any,
) -> dict[str, Any]:
    """Bind exactly two balance-period parents to typed body-column leaves."""

    lines = _canonical_header_lines(header_lines)
    merged_period_surface_lacks_word_boxes = _merged_period_surface_lacks_word_boxes(lines)
    centers, period_context, expected_kinds = _inputs(
        column_centers,
        page_width,
        document_period_context,
        period_semantics,
        expected_lane_kinds,
    )
    try:
        graph = build_multilevel_header_graph_v1(
            lines,
            column_centers=centers,
            page_width=page_width,
        )
    except AdaptiveAccountingTableGeometryV1Error as exc:
        raise _error("shared multilevel header graph input drifted") from exc

    reasons: list[str] = []
    parents: list[dict[str, Any]] = []
    leaves: list[dict[str, Any]] = []
    period_mode = "UNRESOLVED"
    if merged_period_surface_lacks_word_boxes or any(
        ambiguity["kind"]
        in {
            "MERGED_HEADER_ORDER_ONLY_WITHOUT_WORD_BOXES",
            "MERGED_HEADER_TOKEN_GRID_AMBIGUOUS",
        }
        for ambiguity in graph["ambiguities"]
    ):
        reasons.append("MERGED_PERIOD_OR_LEAF_HEADER_WITHOUT_WORD_BOXES_UNRESOLVED")
    else:
        parents, period_mode, period_reason = _graph_period_records(graph, period_context)
        if period_reason is not None:
            reasons.append(period_reason)
        if not reasons:
            cursor = 0
            for parent in parents:
                if parent["column_start"] != cursor or parent["column_stop"] <= cursor:
                    reasons.append("PERIOD_PARENTS_DO_NOT_EXACTLY_PARTITION_BODY_COLUMNS")
                    break
                cursor = parent["column_stop"]
            if cursor != len(centers):
                reasons.append("PERIOD_PARENTS_DO_NOT_EXACTLY_PARTITION_BODY_COLUMNS")
        if not reasons:
            leaves, leaf_reason = _typed_leaf_candidates(graph, parents, expected_kinds)
            if leaf_reason is not None:
                reasons.append(leaf_reason)
        if not reasons:
            reasons.extend(_axis_graph_ambiguity_reasons(graph, parents, leaves))
    reasons = sorted(set(reasons))
    if reasons:
        leaves = []
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "expected_lane_kinds": expected_kinds,
        "format_version": FORMAT_VERSION,
        "header_graph": canonical_clone_v1(graph),
        "leaf_axis": leaves,
        "metrics": {
            "column_count": len(centers),
            "period_parent_count": len(parents),
            "typed_leaf_count": len(leaves),
        },
        "period_resolution_mode": period_mode,
        "safety": canonical_clone_v1(_SAFETY),
        "status": (
            "MULTILEVEL_HEADER_LEAF_AXIS_BOUND_PROPOSAL_ONLY"
            if not reasons
            else "UNRESOLVED_MULTILEVEL_HEADER_LEAF_AXIS"
        ),
        "unresolved_reasons": reasons,
    }
    return _validate_result(
        {**material, "axis_id": "amhlav1:axis:" + canonical_json_sha256_v1(material)}
    )


def validate_accounting_multilevel_header_leaf_axis_replay_v1(
    value: Any,
    header_lines: Any,
    *,
    column_centers: Any,
    page_width: Any,
    document_period_context: Any,
    period_semantics: str,
    expected_lane_kinds: Any,
) -> dict[str, Any]:
    """Reject a self-rehashed mutation through exact input reconstruction."""

    persisted = _validate_result(value)
    expected = build_accounting_multilevel_header_leaf_axis_v1(
        header_lines,
        column_centers=column_centers,
        page_width=page_width,
        document_period_context=document_period_context,
        period_semantics=period_semantics,
        expected_lane_kinds=expected_lane_kinds,
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("multilevel header leaf axis does not replay exactly")
    return persisted
