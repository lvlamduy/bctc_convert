"""Measure candidate table geometry across two authenticated adjacent pages.

This add-only boundary consumes two exact V2 source projections, their exact
V2 geometry-proposal projections, and their full page-local pre-structural
graphs.  It emits every Cartesian pair of page-local TABLE candidates and,
inside each fragment pair, every Cartesian pair of candidate axes.

The output is measurement evidence only.  It does not choose a winner, claim
that two fragments are the same table, accept a continuation or merge, read
visible text or values, or infer statement, period, unit, scope, hierarchy,
schema, or accounting meaning.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import gcd
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.source_structure.contracts_v2 import (
    validate_page_proposal_set_v2,
    validate_source_evidence_projection_v2,
)
from bctc_ai.source_structure.structural_graph_contracts_v1 import (
    validate_page_prestructural_graph_v1,
)

__all__ = [
    "ADJACENT_PAGE_TABLE_GEOMETRY_CLAIM_BOUNDARY_V1",
    "ADJACENT_PAGE_TABLE_GEOMETRY_FORMAT_VERSION_V1",
    "ADJACENT_PAGE_TABLE_GEOMETRY_SAFETY_V1",
    "ADJACENT_PAGE_TABLE_GEOMETRY_STATUS_V1",
    "AdjacentPageTableGeometryRelationError",
    "build_adjacent_page_table_geometry_relations_v1",
    "validate_adjacent_page_table_geometry_relations_v1",
]


class AdjacentPageTableGeometryRelationError(ValueError):
    """Authenticated page evidence cannot form the closed relation set."""


ADJACENT_PAGE_TABLE_GEOMETRY_FORMAT_VERSION_V1 = (
    "BANK_CORPUS_WAVE_1_ROLE_B_ADJACENT_PAGE_TABLE_GEOMETRY_RELATIONS_V1"
)
ADJACENT_PAGE_TABLE_GEOMETRY_CLAIM_BOUNDARY_V1 = (
    "ALL_CARTESIAN_ADJACENT_PAGE_PRESTRUCTURAL_TABLE_AND_AXIS_GEOMETRY_"
    "MEASUREMENTS_ONLY_NO_WINNER_SAME_TABLE_CONTINUATION_MERGE_OR_SEMANTIC_CLAIM"
)
ADJACENT_PAGE_TABLE_GEOMETRY_STATUS_V1 = "COMPLETE_ADJACENT_PAGE_PRESTRUCTURAL_GEOMETRY_ACCOUNTING"

_NORMALIZED_SCALE = 1_000_000
_PREVIOUS_SIDE = "PREVIOUS_PAGE"
_FOLLOWING_SIDE = "FOLLOWING_PAGE"
_TABLE_KIND = "TABLE"
_ROW_KIND = "ROW"
_CELL_KIND = "CELL_OR_VALUE_POSITION"
_AXIS_KIND = "AXIS_OR_DIMENSION"
_CONTAINS_KIND = "PRESTRUCTURAL_CONTAINS"
_CANDIDATE_STATUS = "PRESTRUCTURAL_CANDIDATE"
_RELATION_STATUS = "MEASURED_PRESTRUCTURAL_FRAGMENT_PAIR_UNRESOLVED"
_MEASURED_FRAGMENT = "MEASURED_IN_CARTESIAN_FRAGMENT_PAIRS"
_RETAINED_FRAGMENT = "RETAINED_WITHOUT_CROSS_PAGE_COUNTERPART"
_MEASURED_AXIS = "MEASURED_IN_CARTESIAN_AXIS_PAIRS"
_RETAINED_AXIS = "RETAINED_WITHOUT_AXIS_COUNTERPART"
_PAIR_DISPOSITIONS = (
    "MEASURED_CARTESIAN_FRAGMENT_PAIRS",
    "NO_PREVIOUS_TABLE_CANDIDATE",
    "NO_FOLLOWING_TABLE_CANDIDATE",
    "NO_TABLE_CANDIDATES",
    "UPSTREAM_TERMINAL_BARRIER",
)
_PAIR_REASON = {
    "MEASURED_CARTESIAN_FRAGMENT_PAIRS": (
        "EVERY_PREVIOUS_TABLE_CANDIDATE_PAIRED_WITH_EVERY_FOLLOWING_TABLE_CANDIDATE"
    ),
    "NO_PREVIOUS_TABLE_CANDIDATE": (
        "VALIDATED_PREVIOUS_GRAPH_HAS_ZERO_PRESTRUCTURAL_TABLE_CANDIDATES"
    ),
    "NO_FOLLOWING_TABLE_CANDIDATE": (
        "VALIDATED_FOLLOWING_GRAPH_HAS_ZERO_PRESTRUCTURAL_TABLE_CANDIDATES"
    ),
    "NO_TABLE_CANDIDATES": "BOTH_VALIDATED_GRAPHS_HAVE_ZERO_PRESTRUCTURAL_TABLE_CANDIDATES",
    "UPSTREAM_TERMINAL_BARRIER": (
        "AT_LEAST_ONE_AUTHENTICATED_PAGE_HAS_AN_EXPLICIT_UPSTREAM_TERMINAL_DISPOSITION"
    ),
}

ADJACENT_PAGE_TABLE_GEOMETRY_SAFETY_V1: dict[str, bool] = {
    "prestructural_candidate_geometry_only": True,
    "all_cartesian_fragment_pairs_emitted": True,
    "all_cartesian_axis_pairs_emitted": True,
    "threshold_applied": False,
    "winner_selected": False,
    "accepted_relation_claimed": False,
    "same_table_claimed": False,
    "successor_claimed": False,
    "continuation_claimed": False,
    "merge_claimed": False,
    "statement_claimed": False,
    "table_semantic_claimed": False,
    "logical_rows_claimed": False,
    "financial_cells_claimed": False,
    "period_claimed": False,
    "unit_claimed": False,
    "scope_claimed": False,
    "hierarchy_claimed": False,
    "schema_used": False,
    "mapping_used": False,
    "visible_text_used": False,
    "numeric_value_used": False,
    "blank_claimed": False,
    "absence_claimed": False,
    "bank_identity_used_for_routing": False,
    "filename_identity_used_for_routing": False,
    "source_path_used_for_routing": False,
    "note_number_used_for_routing": False,
    "role_a_used_for_routing": False,
    "historical_values_used": False,
    "model_or_reader_invoked": False,
    "network_used": False,
}


@dataclass(frozen=True)
class _PageInputs:
    source: dict[str, Any]
    proposals: dict[str, Any]
    graph: dict[str, Any]


@dataclass(frozen=True)
class _AdjacentInputs:
    previous: _PageInputs
    following: _PageInputs


def _error(message: str) -> AdjacentPageTableGeometryRelationError:
    return AdjacentPageTableGeometryRelationError(message)


def _content_id(namespace: str, value: Mapping[str, Any]) -> str:
    return f"apgrv1:{namespace}:{canonical_json_sha256_v1(value)}"


def _validate_page_inputs(
    projection: Mapping[str, Any],
    proposal_projection: Mapping[str, Any],
    graph: Mapping[str, Any],
) -> _PageInputs:
    try:
        source = validate_source_evidence_projection_v2(projection)
        proposals = validate_page_proposal_set_v2(
            proposal_projection,
            projection=source,
        )
        validated_graph = validate_page_prestructural_graph_v1(
            graph,
            projection=source,
            proposal_projection=proposals,
        )
    except ValueError as exc:
        raise _error("adjacent-page input failed its exact page-local contract") from exc
    return _PageInputs(source=source, proposals=proposals, graph=validated_graph)


def _validated_inputs(
    previous_projection: Mapping[str, Any],
    previous_proposal_projection: Mapping[str, Any],
    previous_graph: Mapping[str, Any],
    following_projection: Mapping[str, Any],
    following_proposal_projection: Mapping[str, Any],
    following_graph: Mapping[str, Any],
) -> _AdjacentInputs:
    previous = _validate_page_inputs(
        previous_projection,
        previous_proposal_projection,
        previous_graph,
    )
    following = _validate_page_inputs(
        following_projection,
        following_proposal_projection,
        following_graph,
    )
    left_locator = previous.source["source_locator"]
    right_locator = following.source["source_locator"]
    left_record = previous.source["page_record_v2"]
    right_record = following.source["page_record_v2"]
    if (
        left_record["document_id"] != right_record["document_id"]
        or left_locator["source_sha256"] != right_locator["source_sha256"]
        or left_locator["source_size_bytes"] != right_locator["source_size_bytes"]
    ):
        raise _error("adjacent pages must bind the same authenticated source document")
    if previous.source["source_local_page_id"] == following.source["source_local_page_id"]:
        raise _error("adjacent pages require two distinct authenticated page identities")
    if right_locator["physical_page"] != left_locator["physical_page"] + 1:
        raise _error("following physical page must be exactly previous physical page plus one")
    return _AdjacentInputs(previous=previous, following=following)


def _page_extent(page: _PageInputs) -> list[int]:
    authority = page.source["coordinate_authority"]
    route = page.source["route"]
    if route == "DOMINANT_RASTER_OCR":
        dimensions = authority.get("unrotated_dimensions_mpt")
        if (
            type(dimensions) is not list
            or len(dimensions) != 2
            or any(type(item) is not int or item <= 0 for item in dimensions)
        ):
            raise _error("OCR page extent is not two positive integer millipoint dimensions")
        return [0, 0, dimensions[0], dimensions[1]]
    if route == "CAUSAL_NATIVE_TEXT":
        bounds = authority.get("canonical_cropbox_bounds_mpt")
        if (
            type(bounds) is not list
            or len(bounds) != 4
            or any(type(item) is not int for item in bounds)
            or bounds[:2] != [0, 0]
            or bounds[0] >= bounds[2]
            or bounds[1] >= bounds[3]
        ):
            raise _error("native page extent is not one canonical positive cropbox")
        return list(bounds)
    raise _error("page route is outside the authenticated V2 source boundary")


def _bbox(value: Any, *, extent: Sequence[int], label: str) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or value[0] >= value[2]
        or value[1] >= value[3]
        or value[0] < extent[0]
        or value[1] < extent[1]
        or value[2] > extent[2]
        or value[3] > extent[3]
    ):
        raise _error(f"{label} falls outside its canonical page extent")
    return list(value)


def _normalize_coordinate(coordinate: int, *, origin: int, dimension: int) -> int:
    offset = coordinate - origin
    if type(coordinate) is not int or offset < 0 or offset > dimension:
        raise _error("coordinate cannot be normalized inside the page extent")
    return (offset * _NORMALIZED_SCALE + dimension // 2) // dimension


def _normalize_bbox(box: Sequence[int], *, extent: Sequence[int]) -> list[int]:
    width = extent[2] - extent[0]
    height = extent[3] - extent[1]
    return [
        _normalize_coordinate(box[0], origin=extent[0], dimension=width),
        _normalize_coordinate(box[1], origin=extent[1], dimension=height),
        _normalize_coordinate(box[2], origin=extent[0], dimension=width),
        _normalize_coordinate(box[3], origin=extent[1], dimension=height),
    ]


def _integer_median(values: Sequence[int]) -> int:
    if not values or any(type(item) is not int for item in values):
        raise _error("integer geometry median requires one or more exact integers")
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) // 2


def _reduced_fraction(numerator: int, denominator: int) -> dict[str, int]:
    if type(numerator) is not int or type(denominator) is not int or denominator <= 0:
        raise _error("exact geometry fraction types drifted")
    common = gcd(abs(numerator), denominator)
    return {
        "numerator": numerator // common,
        "denominator": denominator // common,
    }


def _absolute_proportion_distance(
    left_numerator: int,
    left_denominator: int,
    right_numerator: int,
    right_denominator: int,
) -> dict[str, int]:
    return _reduced_fraction(
        abs(left_numerator * right_denominator - right_numerator * left_denominator),
        left_denominator * right_denominator,
    )


def _node_receipts(nodes: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "node_id": node["node_id"],
            "ordinal": node["ordinal"],
            "source_binding_sha256": node["source_binding_sha256"],
        }
        for node in sorted(nodes, key=lambda item: item["ordinal"])
    ]


def _page_binding(side: str, page: _PageInputs) -> dict[str, Any]:
    extent = _page_extent(page)
    locator = page.source["source_locator"]
    payload: dict[str, Any] = {
        "source_local_page_id": page.source["source_local_page_id"],
        "document_id": page.source["page_record_v2"]["document_id"],
        "source_sha256": locator["source_sha256"],
        "source_size_bytes": locator["source_size_bytes"],
        "physical_page": locator["physical_page"],
        "route": page.source["route"],
        "upstream_status": page.source["upstream_status"],
        "terminal": page.source["terminal"],
        "canonical_page_extent_mpt": extent,
        "normalized_geometry_scale": _NORMALIZED_SCALE,
        "normalized_geometry_unit": "INTEGER_PARTS_PER_MILLION_OF_PAGE_EXTENT",
        "source_projection_sha256": canonical_json_sha256_v1(page.source),
        "source_proposal_projection_sha256": canonical_json_sha256_v1(page.proposals),
        "page_prestructural_graph_sha256": canonical_json_sha256_v1(page.graph),
        "page_prestructural_graph_identity": page.graph["graph_identity"],
    }
    payload["page_binding_id"] = _content_id("page_binding", payload)
    return {"side": side, **payload}


def _axis_geometry(
    *,
    axis: Mapping[str, Any],
    atoms: Sequence[Mapping[str, Any]],
    extent: Sequence[int],
) -> dict[str, Any]:
    axis_box = _bbox(
        axis["canonical_bbox_mpt"],
        extent=extent,
        label="axis candidate bounding box",
    )
    cited_atom_ids = set(axis["source_atom_ids"])
    atom_geometries = []
    for atom in atoms:
        atom_id = atom["source_local_id"]
        if atom_id not in cited_atom_ids:
            continue
        atom_box = _bbox(
            atom["canonical_bbox_mpt"],
            extent=extent,
            label="axis source-atom bounding box",
        )
        atom_geometries.append(
            {
                "source_atom_id": atom_id,
                "canonical_bbox_mpt": atom_box,
                "normalized_bbox_ppm": _normalize_bbox(atom_box, extent=extent),
            }
        )
    if len(atom_geometries) != len(cited_atom_ids) or not atom_geometries:
        raise _error("axis candidate source-atom accounting drifted")
    raw_x0 = _integer_median([item["canonical_bbox_mpt"][0] for item in atom_geometries])
    raw_x2 = _integer_median([item["canonical_bbox_mpt"][2] for item in atom_geometries])
    raw_center2 = _integer_median(
        [item["canonical_bbox_mpt"][0] + item["canonical_bbox_mpt"][2] for item in atom_geometries]
    )
    normalized_x0 = _integer_median([item["normalized_bbox_ppm"][0] for item in atom_geometries])
    normalized_x2 = _integer_median([item["normalized_bbox_ppm"][2] for item in atom_geometries])
    normalized_center2 = _integer_median(
        [
            item["normalized_bbox_ppm"][0] + item["normalized_bbox_ppm"][2]
            for item in atom_geometries
        ]
    )
    payload: dict[str, Any] = {
        "axis_node_id": axis["node_id"],
        "axis_node_ordinal": axis["ordinal"],
        "axis_source_binding_sha256": axis["source_binding_sha256"],
        "canonical_bbox_mpt": axis_box,
        "normalized_bbox_ppm": _normalize_bbox(axis_box, extent=extent),
        "source_atom_count": len(atom_geometries),
        "source_atom_geometries": atom_geometries,
        "source_atom_geometries_sha256": canonical_json_sha256_v1(atom_geometries),
        "source_atom_x0_median_mpt": raw_x0,
        "source_atom_x2_median_mpt": raw_x2,
        "source_atom_center2_median_mpt": raw_center2,
        "normalized_source_atom_x0_median_ppm": normalized_x0,
        "normalized_source_atom_x2_median_ppm": normalized_x2,
        "normalized_source_atom_center2_median_ppm": normalized_center2,
    }
    payload["axis_geometry_id"] = _content_id("axis_geometry", payload)
    return payload


def _fragments(
    side: str,
    page: _PageInputs,
    binding: Mapping[str, Any],
) -> list[dict[str, Any]]:
    extent = binding["canonical_page_extent_mpt"]
    node_by_id = {node["node_id"]: node for node in page.graph["nodes"]}
    children: dict[str, list[dict[str, Any]]] = {}
    for edge in page.graph["edges"]:
        if edge["kind"] != _CONTAINS_KIND:
            continue
        parent = node_by_id[edge["from_node_id"]]
        child = node_by_id[edge["to_node_id"]]
        children.setdefault(parent["node_id"], []).append(child)
    atoms = page.source["neutral_page_v1"]["atoms"]
    tables = sorted(
        (
            node
            for node in page.graph["nodes"]
            if node["kind"] == _TABLE_KIND and node["status"] == _CANDIDATE_STATUS
        ),
        key=lambda node: node["ordinal"],
    )
    if page.source["terminal"] and tables:
        raise _error("an upstream-terminal page cannot expose table candidates")

    fragments: list[dict[str, Any]] = []
    for table in tables:
        direct_children = children.get(table["node_id"], [])
        rows = sorted(
            (node for node in direct_children if node["kind"] == _ROW_KIND),
            key=lambda node: node["ordinal"],
        )
        axes = sorted(
            (node for node in direct_children if node["kind"] == _AXIS_KIND),
            key=lambda node: node["ordinal"],
        )
        cells = sorted(
            (
                cell
                for row in rows
                for cell in children.get(row["node_id"], [])
                if cell["kind"] == _CELL_KIND
            ),
            key=lambda node: node["ordinal"],
        )
        table_box = _bbox(
            table["canonical_bbox_mpt"],
            extent=extent,
            label="table candidate bounding box",
        )
        normalized_table_box = _normalize_bbox(table_box, extent=extent)
        axis_geometries = [_axis_geometry(axis=axis, atoms=atoms, extent=extent) for axis in axes]
        payload: dict[str, Any] = {
            "source_local_page_id": binding["source_local_page_id"],
            "physical_page": binding["physical_page"],
            "source_projection_sha256": binding["source_projection_sha256"],
            "source_proposal_projection_sha256": binding["source_proposal_projection_sha256"],
            "page_prestructural_graph_sha256": binding["page_prestructural_graph_sha256"],
            "page_prestructural_graph_identity": binding["page_prestructural_graph_identity"],
            "table_node_id": table["node_id"],
            "table_node_ordinal": table["ordinal"],
            "table_source_binding_sha256": table["source_binding_sha256"],
            "canonical_bbox_mpt": table_box,
            "normalized_bbox_ppm": normalized_table_box,
            "distance_from_page_top_mpt": table_box[1] - extent[1],
            "distance_to_page_bottom_mpt": extent[3] - table_box[3],
            "distance_from_page_top_ppm": normalized_table_box[1],
            "distance_to_page_bottom_ppm": _normalize_coordinate(
                extent[3] - table_box[3],
                origin=0,
                dimension=extent[3] - extent[1],
            ),
            "distance_from_page_top_page_height_fraction": _reduced_fraction(
                table_box[1] - extent[1],
                extent[3] - extent[1],
            ),
            "distance_to_page_bottom_page_height_fraction": _reduced_fraction(
                extent[3] - table_box[3],
                extent[3] - extent[1],
            ),
            "row_candidates": _node_receipts(rows),
            "cell_or_value_position_candidates": _node_receipts(cells),
            "axis_or_dimension_candidates": axis_geometries,
            "candidate_counts": {
                "row_count": len(rows),
                "cell_or_value_position_count": len(cells),
                "axis_or_dimension_count": len(axes),
                "axis_source_atom_geometry_count": sum(
                    axis["source_atom_count"] for axis in axis_geometries
                ),
            },
        }
        payload["fragment_id"] = _content_id("fragment", payload)
        fragments.append({"side": side, **payload})
    return fragments


def _axis_distance(
    *,
    ordinal: int,
    relation_context: Mapping[str, Any],
    previous_axis: Mapping[str, Any],
    following_axis: Mapping[str, Any],
    previous_extent: Sequence[int],
    following_extent: Sequence[int],
) -> dict[str, Any]:
    previous_width = previous_extent[2] - previous_extent[0]
    following_width = following_extent[2] - following_extent[0]
    previous_center2 = previous_axis["source_atom_center2_median_mpt"] - 2 * previous_extent[0]
    following_center2 = following_axis["source_atom_center2_median_mpt"] - 2 * following_extent[0]
    previous_normalized_center2 = previous_axis["normalized_source_atom_center2_median_ppm"]
    following_normalized_center2 = following_axis["normalized_source_atom_center2_median_ppm"]
    payload: dict[str, Any] = {
        "ordinal": ordinal,
        "page_pair_id": relation_context["page_pair_id"],
        "previous_fragment_id": relation_context["previous_fragment_id"],
        "following_fragment_id": relation_context["following_fragment_id"],
        "previous_axis_geometry_id": previous_axis["axis_geometry_id"],
        "following_axis_geometry_id": following_axis["axis_geometry_id"],
        "previous_axis_node_id": previous_axis["axis_node_id"],
        "following_axis_node_id": following_axis["axis_node_id"],
        "x0_median_signed_delta_ppm": (
            following_axis["normalized_source_atom_x0_median_ppm"]
            - previous_axis["normalized_source_atom_x0_median_ppm"]
        ),
        "x0_median_absolute_distance_ppm": abs(
            following_axis["normalized_source_atom_x0_median_ppm"]
            - previous_axis["normalized_source_atom_x0_median_ppm"]
        ),
        "x2_median_signed_delta_ppm": (
            following_axis["normalized_source_atom_x2_median_ppm"]
            - previous_axis["normalized_source_atom_x2_median_ppm"]
        ),
        "x2_median_absolute_distance_ppm": abs(
            following_axis["normalized_source_atom_x2_median_ppm"]
            - previous_axis["normalized_source_atom_x2_median_ppm"]
        ),
        "center2_median_signed_delta_ppm": (
            following_normalized_center2 - previous_normalized_center2
        ),
        "center2_median_absolute_distance_ppm": abs(
            following_normalized_center2 - previous_normalized_center2
        ),
        "exact_center_absolute_distance_page_width_fraction": (
            _absolute_proportion_distance(
                previous_center2,
                2 * previous_width,
                following_center2,
                2 * following_width,
            )
        ),
    }
    payload["axis_distance_id"] = _content_id("axis_distance", payload)
    return payload


def _table_distance_evidence(
    previous: Mapping[str, Any],
    following: Mapping[str, Any],
    *,
    previous_extent: Sequence[int],
    following_extent: Sequence[int],
) -> dict[str, Any]:
    previous_normalized = previous["normalized_bbox_ppm"]
    following_normalized = following["normalized_bbox_ppm"]
    signed_edges = [following_normalized[index] - previous_normalized[index] for index in range(4)]
    previous_width_mpt = previous_extent[2] - previous_extent[0]
    following_width_mpt = following_extent[2] - following_extent[0]
    previous_box = previous["canonical_bbox_mpt"]
    following_box = following["canonical_bbox_mpt"]
    previous_left = previous_box[0] - previous_extent[0]
    following_left = following_box[0] - following_extent[0]
    previous_right = previous_box[2] - previous_extent[0]
    following_right = following_box[2] - following_extent[0]
    previous_table_width = previous_box[2] - previous_box[0]
    following_table_width = following_box[2] - following_box[0]
    return {
        "normalized_bbox_edge_signed_delta_ppm": signed_edges,
        "normalized_bbox_edge_absolute_distance_ppm": [abs(item) for item in signed_edges],
        "normalized_left_edge_signed_delta_ppm": signed_edges[0],
        "normalized_left_edge_absolute_distance_ppm": abs(signed_edges[0]),
        "normalized_right_edge_signed_delta_ppm": signed_edges[2],
        "normalized_right_edge_absolute_distance_ppm": abs(signed_edges[2]),
        "normalized_width_signed_delta_ppm": (
            (following_normalized[2] - following_normalized[0])
            - (previous_normalized[2] - previous_normalized[0])
        ),
        "normalized_width_absolute_distance_ppm": abs(
            (following_normalized[2] - following_normalized[0])
            - (previous_normalized[2] - previous_normalized[0])
        ),
        "exact_left_edge_absolute_distance_page_width_fraction": (
            _absolute_proportion_distance(
                previous_left,
                previous_width_mpt,
                following_left,
                following_width_mpt,
            )
        ),
        "exact_right_edge_absolute_distance_page_width_fraction": (
            _absolute_proportion_distance(
                previous_right,
                previous_width_mpt,
                following_right,
                following_width_mpt,
            )
        ),
        "exact_width_absolute_distance_page_width_fraction": (
            _absolute_proportion_distance(
                previous_table_width,
                previous_width_mpt,
                following_table_width,
                following_width_mpt,
            )
        ),
        "previous_distance_to_page_bottom_mpt": previous["distance_to_page_bottom_mpt"],
        "previous_distance_to_page_bottom_ppm": previous["distance_to_page_bottom_ppm"],
        "previous_distance_to_page_bottom_page_height_fraction": previous[
            "distance_to_page_bottom_page_height_fraction"
        ],
        "following_distance_from_page_top_mpt": following["distance_from_page_top_mpt"],
        "following_distance_from_page_top_ppm": following["distance_from_page_top_ppm"],
        "following_distance_from_page_top_page_height_fraction": following[
            "distance_from_page_top_page_height_fraction"
        ],
    }


def _axis_dispositions(
    *,
    page_pair_id: str,
    previous_fragments: Sequence[Mapping[str, Any]],
    following_fragments: Sequence[Mapping[str, Any]],
    relations: Sequence[Mapping[str, Any]],
    terminal_barrier: bool,
) -> list[dict[str, Any]]:
    distance_ids_by_axis: dict[str, list[str]] = {}
    for relation in relations:
        for distance in relation["axis_cartesian_distances"]:
            for field in ("previous_axis_geometry_id", "following_axis_geometry_id"):
                distance_ids_by_axis.setdefault(distance[field], []).append(
                    distance["axis_distance_id"]
                )
    dispositions = []
    for side, fragments, opposite_fragments in (
        (_PREVIOUS_SIDE, previous_fragments, following_fragments),
        (_FOLLOWING_SIDE, following_fragments, previous_fragments),
    ):
        opposite_axis_count = sum(
            len(fragment["axis_or_dimension_candidates"]) for fragment in opposite_fragments
        )
        for fragment in fragments:
            for axis in fragment["axis_or_dimension_candidates"]:
                distance_ids = distance_ids_by_axis.get(axis["axis_geometry_id"], [])
                measured = bool(distance_ids)
                if measured:
                    reason = "AXIS_PARTICIPATES_IN_EVERY_CARTESIAN_OPPOSITE_PAGE_AXIS_PAIR"
                elif terminal_barrier:
                    reason = "AXIS_RETAINED_BECAUSE_AN_ADJACENT_PAGE_IS_UPSTREAM_TERMINAL"
                elif not opposite_fragments:
                    reason = "AXIS_RETAINED_BECAUSE_OPPOSITE_PAGE_HAS_ZERO_TABLE_CANDIDATES"
                elif not opposite_axis_count:
                    reason = "AXIS_RETAINED_BECAUSE_OPPOSITE_PAGE_TABLES_HAVE_ZERO_AXIS_CANDIDATES"
                else:
                    raise _error("axis Cartesian accounting dropped an eligible counterpart")
                payload: dict[str, Any] = {
                    "ordinal": len(dispositions) + 1,
                    "page_pair_id": page_pair_id,
                    "fragment_id": fragment["fragment_id"],
                    "side": side,
                    "axis_geometry_id": axis["axis_geometry_id"],
                    "axis_node_id": axis["axis_node_id"],
                    "primary_disposition": _MEASURED_AXIS if measured else _RETAINED_AXIS,
                    "reason_code": reason,
                    "axis_distance_ids": distance_ids,
                }
                payload["axis_disposition_id"] = _content_id("axis_disposition", payload)
                dispositions.append(payload)
    return dispositions


def _relations(
    *,
    page_pair_id: str,
    previous_fragments: Sequence[Mapping[str, Any]],
    following_fragments: Sequence[Mapping[str, Any]],
    previous_extent: Sequence[int],
    following_extent: Sequence[int],
) -> list[dict[str, Any]]:
    relations: list[dict[str, Any]] = []
    for previous in previous_fragments:
        for following in following_fragments:
            relation_context = {
                "page_pair_id": page_pair_id,
                "previous_fragment_id": previous["fragment_id"],
                "following_fragment_id": following["fragment_id"],
            }
            axis_distances = [
                _axis_distance(
                    ordinal=axis_ordinal,
                    relation_context=relation_context,
                    previous_axis=previous_axis,
                    following_axis=following_axis,
                    previous_extent=previous_extent,
                    following_extent=following_extent,
                )
                for axis_ordinal, (previous_axis, following_axis) in enumerate(
                    (
                        (previous_axis, following_axis)
                        for previous_axis in previous["axis_or_dimension_candidates"]
                        for following_axis in following["axis_or_dimension_candidates"]
                    ),
                    start=1,
                )
            ]
            payload: dict[str, Any] = {
                "ordinal": len(relations) + 1,
                **relation_context,
                "previous_table_node_id": previous["table_node_id"],
                "following_table_node_id": following["table_node_id"],
                "status": _RELATION_STATUS,
                "table_distance_evidence": _table_distance_evidence(
                    previous,
                    following,
                    previous_extent=previous_extent,
                    following_extent=following_extent,
                ),
                "previous_axis_count": len(previous["axis_or_dimension_candidates"]),
                "following_axis_count": len(following["axis_or_dimension_candidates"]),
                "axis_count_signed_delta": (
                    len(following["axis_or_dimension_candidates"])
                    - len(previous["axis_or_dimension_candidates"])
                ),
                "axis_cartesian_distance_count": len(axis_distances),
                "axis_cartesian_distances": axis_distances,
            }
            payload["relation_id"] = _content_id("relation", payload)
            relations.append(payload)
    return relations


def _fragment_dispositions(
    *,
    page_pair_id: str,
    fragments: Sequence[Mapping[str, Any]],
    relations: Sequence[Mapping[str, Any]],
    terminal_barrier: bool,
) -> list[dict[str, Any]]:
    relation_ids_by_fragment: dict[str, list[str]] = {}
    for relation in relations:
        for field in ("previous_fragment_id", "following_fragment_id"):
            relation_ids_by_fragment.setdefault(relation[field], []).append(relation["relation_id"])
    dispositions = []
    for fragment in fragments:
        relation_ids = relation_ids_by_fragment.get(fragment["fragment_id"], [])
        measured = bool(relation_ids)
        if measured:
            reason = "FRAGMENT_PARTICIPATES_IN_EVERY_ORDERED_CARTESIAN_COUNTERPART_PAIR"
        elif terminal_barrier:
            reason = "FRAGMENT_RETAINED_BECAUSE_AN_ADJACENT_PAGE_IS_UPSTREAM_TERMINAL"
        else:
            reason = "FRAGMENT_RETAINED_BECAUSE_OPPOSITE_PAGE_HAS_ZERO_TABLE_CANDIDATES"
        payload: dict[str, Any] = {
            "ordinal": len(dispositions) + 1,
            "page_pair_id": page_pair_id,
            "fragment_id": fragment["fragment_id"],
            "side": fragment["side"],
            "table_node_id": fragment["table_node_id"],
            "primary_disposition": _MEASURED_FRAGMENT if measured else _RETAINED_FRAGMENT,
            "reason_code": reason,
            "relation_ids": relation_ids,
        }
        payload["fragment_disposition_id"] = _content_id("fragment_disposition", payload)
        dispositions.append(payload)
    return dispositions


def _page_pair_disposition(
    *,
    page_pair_id: str,
    terminal_barrier: bool,
    previous_fragment_count: int,
    following_fragment_count: int,
    relation_count: int,
) -> dict[str, Any]:
    if terminal_barrier:
        disposition = "UPSTREAM_TERMINAL_BARRIER"
    elif previous_fragment_count and following_fragment_count:
        disposition = "MEASURED_CARTESIAN_FRAGMENT_PAIRS"
    elif not previous_fragment_count and not following_fragment_count:
        disposition = "NO_TABLE_CANDIDATES"
    elif not previous_fragment_count:
        disposition = "NO_PREVIOUS_TABLE_CANDIDATE"
    else:
        disposition = "NO_FOLLOWING_TABLE_CANDIDATE"
    payload: dict[str, Any] = {
        "page_pair_id": page_pair_id,
        "primary_disposition": disposition,
        "reason_code": _PAIR_REASON[disposition],
        "previous_table_candidate_count": previous_fragment_count,
        "following_table_candidate_count": following_fragment_count,
        "emitted_cartesian_relation_count": relation_count,
        "source_table_absence_claimed": False,
    }
    payload["page_pair_disposition_id"] = _content_id("page_pair_disposition", payload)
    return payload


def _metrics(
    *,
    previous_fragments: Sequence[Mapping[str, Any]],
    following_fragments: Sequence[Mapping[str, Any]],
    relations: Sequence[Mapping[str, Any]],
    fragment_dispositions: Sequence[Mapping[str, Any]],
    axis_dispositions: Sequence[Mapping[str, Any]],
    pair_disposition: Mapping[str, Any],
    terminal_page_count: int,
) -> dict[str, Any]:
    fragments = [*previous_fragments, *following_fragments]
    fragment_disposition_counts = Counter(
        item["primary_disposition"] for item in fragment_dispositions
    )
    pair_counts = Counter({pair_disposition["primary_disposition"]: 1})
    axis_disposition_counts = Counter(
        disposition["primary_disposition"] for disposition in axis_dispositions
    )
    return {
        "page_count": 2,
        "terminal_page_count": terminal_page_count,
        "previous_table_candidate_count": len(previous_fragments),
        "following_table_candidate_count": len(following_fragments),
        "table_fragment_count": len(fragments),
        "row_candidate_count": sum(item["candidate_counts"]["row_count"] for item in fragments),
        "cell_or_value_position_candidate_count": sum(
            item["candidate_counts"]["cell_or_value_position_count"] for item in fragments
        ),
        "axis_or_dimension_candidate_count": sum(
            item["candidate_counts"]["axis_or_dimension_count"] for item in fragments
        ),
        "axis_source_atom_geometry_count": sum(
            item["candidate_counts"]["axis_source_atom_geometry_count"] for item in fragments
        ),
        "expected_cartesian_fragment_pair_count": (
            len(previous_fragments) * len(following_fragments)
        ),
        "emitted_cartesian_fragment_pair_count": len(relations),
        "expected_cartesian_axis_distance_count": sum(
            relation["previous_axis_count"] * relation["following_axis_count"]
            for relation in relations
        ),
        "emitted_cartesian_axis_distance_count": sum(
            relation["axis_cartesian_distance_count"] for relation in relations
        ),
        "axis_disposition_count": len(axis_dispositions),
        "axis_disposition_counts": {
            _MEASURED_AXIS: axis_disposition_counts[_MEASURED_AXIS],
            _RETAINED_AXIS: axis_disposition_counts[_RETAINED_AXIS],
        },
        "fragment_disposition_count": len(fragment_dispositions),
        "fragment_disposition_counts": {
            _MEASURED_FRAGMENT: fragment_disposition_counts[_MEASURED_FRAGMENT],
            _RETAINED_FRAGMENT: fragment_disposition_counts[_RETAINED_FRAGMENT],
        },
        "page_pair_disposition_counts": {
            disposition: pair_counts[disposition] for disposition in _PAIR_DISPOSITIONS
        },
    }


def _derive(inputs: _AdjacentInputs) -> dict[str, Any]:
    previous_binding = _page_binding(_PREVIOUS_SIDE, inputs.previous)
    following_binding = _page_binding(_FOLLOWING_SIDE, inputs.following)
    pair_payload = {
        "previous_page_binding_id": previous_binding["page_binding_id"],
        "following_page_binding_id": following_binding["page_binding_id"],
        "source_sha256": previous_binding["source_sha256"],
        "source_size_bytes": previous_binding["source_size_bytes"],
        "document_id": previous_binding["document_id"],
        "previous_physical_page": previous_binding["physical_page"],
        "following_physical_page": following_binding["physical_page"],
        "physical_page_delta": 1,
    }
    page_pair_id = _content_id("page_pair", pair_payload)
    ordered_page_pair = {
        "page_pair_id": page_pair_id,
        **pair_payload,
        "previous_page_binding": previous_binding,
        "following_page_binding": following_binding,
    }
    previous_fragments = _fragments(_PREVIOUS_SIDE, inputs.previous, previous_binding)
    following_fragments = _fragments(_FOLLOWING_SIDE, inputs.following, following_binding)
    terminal_barrier = previous_binding["terminal"] or following_binding["terminal"]
    relations = (
        []
        if terminal_barrier
        else _relations(
            page_pair_id=page_pair_id,
            previous_fragments=previous_fragments,
            following_fragments=following_fragments,
            previous_extent=previous_binding["canonical_page_extent_mpt"],
            following_extent=following_binding["canonical_page_extent_mpt"],
        )
    )
    fragments = [*previous_fragments, *following_fragments]
    fragment_dispositions = _fragment_dispositions(
        page_pair_id=page_pair_id,
        fragments=fragments,
        relations=relations,
        terminal_barrier=terminal_barrier,
    )
    axis_dispositions = _axis_dispositions(
        page_pair_id=page_pair_id,
        previous_fragments=previous_fragments,
        following_fragments=following_fragments,
        relations=relations,
        terminal_barrier=terminal_barrier,
    )
    pair_disposition = _page_pair_disposition(
        page_pair_id=page_pair_id,
        terminal_barrier=terminal_barrier,
        previous_fragment_count=len(previous_fragments),
        following_fragment_count=len(following_fragments),
        relation_count=len(relations),
    )
    artifact: dict[str, Any] = {
        "format_version": ADJACENT_PAGE_TABLE_GEOMETRY_FORMAT_VERSION_V1,
        "claim_boundary": ADJACENT_PAGE_TABLE_GEOMETRY_CLAIM_BOUNDARY_V1,
        "status": ADJACENT_PAGE_TABLE_GEOMETRY_STATUS_V1,
        "ordered_page_pair": ordered_page_pair,
        "table_fragments": fragments,
        "fragment_pair_relations": relations,
        "fragment_dispositions": fragment_dispositions,
        "axis_dispositions": axis_dispositions,
        "page_pair_disposition": pair_disposition,
        "metrics": _metrics(
            previous_fragments=previous_fragments,
            following_fragments=following_fragments,
            relations=relations,
            fragment_dispositions=fragment_dispositions,
            axis_dispositions=axis_dispositions,
            pair_disposition=pair_disposition,
            terminal_page_count=int(previous_binding["terminal"])
            + int(following_binding["terminal"]),
        ),
        "safety": canonical_clone_v1(ADJACENT_PAGE_TABLE_GEOMETRY_SAFETY_V1),
    }
    artifact["artifact_identity"] = _content_id("artifact", artifact)
    return canonical_clone_v1(artifact)


def build_adjacent_page_table_geometry_relations_v1(
    previous_projection: Mapping[str, Any],
    previous_proposal_projection: Mapping[str, Any],
    previous_graph: Mapping[str, Any],
    following_projection: Mapping[str, Any],
    following_proposal_projection: Mapping[str, Any],
    following_graph: Mapping[str, Any],
) -> dict[str, Any]:
    """Emit every threshold-free candidate-fragment geometry measurement."""

    inputs = _validated_inputs(
        previous_projection,
        previous_proposal_projection,
        previous_graph,
        following_projection,
        following_proposal_projection,
        following_graph,
    )
    return _derive(inputs)


def validate_adjacent_page_table_geometry_relations_v1(
    value: Any,
    *,
    previous_projection: Mapping[str, Any],
    previous_proposal_projection: Mapping[str, Any],
    previous_graph: Mapping[str, Any],
    following_projection: Mapping[str, Any],
    following_proposal_projection: Mapping[str, Any],
    following_graph: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay the complete relation set against all six authenticated inputs."""

    if type(value) is not dict:
        raise _error("adjacent-page geometry relation set must be a plain object")
    inputs = _validated_inputs(
        previous_projection,
        previous_proposal_projection,
        previous_graph,
        following_projection,
        following_proposal_projection,
        following_graph,
    )
    expected = _derive(inputs)
    if not same_typed_json_v1(value, expected):
        raise _error("adjacent-page geometry relation set drifted from exact replay")
    return canonical_clone_v1(expected)
