"""Build one deterministic page-local pre-structural candidate graph.

The builder consumes only an already authenticated source-evidence projection
and its already validated geometry-proposal projection.  It reads source atom
kind, authority, order, and canonical geometry; visible text and external
routing metadata are deliberately outside this module.

The result remains partial and pre-structural.  Repeated geometry may yield
TABLE, ROW, CELL_OR_VALUE_POSITION, and AXIS_OR_DIMENSION candidates, but no
statement, accounting, value, blank, absence, or hierarchy truth is accepted.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from bctc_ai.source_structure.contracts_v2 import (
    validate_page_proposal_set_v2,
    validate_source_evidence_projection_v2,
)
from bctc_ai.source_structure.structural_graph_contracts_v1 import (
    AtomGraphDispositionV1,
    GraphEdgeKindV1,
    GraphNodeKindV1,
    GraphNodeStatusV1,
    make_atom_graph_disposition_v1,
    make_graph_edge_v1,
    make_graph_node_v1,
    make_page_prestructural_graph_v1,
)

__all__ = [
    "PagePrestructuralGraphBuildError",
    "build_page_prestructural_graph_v1",
]


class PagePrestructuralGraphBuildError(ValueError):
    """Validated source geometry cannot form the bounded candidate graph."""


_PRIMARY_AUTHORITY = "AUTHENTICATED_PRIMARY"
_LINE_KIND = "LINE"
_WORD_KIND = "WORD"
_TABULAR_KIND = "TABULAR_GEOMETRY_CANDIDATE"


@dataclass
class _Run:
    atom_ids: list[str]
    bbox: list[int]
    words: list[tuple[str, list[int]]] = field(default_factory=list)


@dataclass
class _Row:
    atom_ids: list[str]
    bbox: list[int]
    words: list[tuple[str, list[int]]]


@dataclass
class _TableParts:
    proposal_id: str
    table: dict[str, Any]
    rows: list[dict[str, Any]]
    cells: list[list[dict[str, Any]]]
    axes: list[dict[str, Any]]
    cell_axis_pairs: list[tuple[dict[str, Any], dict[str, Any]]]


def _error(message: str) -> PagePrestructuralGraphBuildError:
    return PagePrestructuralGraphBuildError(message)


def _positive_box(value: Any) -> bool:
    return (
        type(value) is list
        and len(value) == 4
        and all(type(coordinate) is int for coordinate in value)
        and value[0] < value[2]
        and value[1] < value[3]
    )


def _source_box(value: Any) -> bool:
    """Accept exact source geometry, including authenticated zero-area boxes."""

    return (
        type(value) is list
        and len(value) == 4
        and all(type(coordinate) is int for coordinate in value)
        and value[0] <= value[2]
        and value[1] <= value[3]
    )


def _union(boxes: Sequence[Sequence[int]]) -> list[int]:
    if not boxes:
        raise _error("cannot derive candidate geometry without a source box")
    return [
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    ]


def _same_vertical_band(left: Sequence[int], right: Sequence[int]) -> bool:
    overlap = min(left[3], right[3]) - max(left[1], right[1])
    if overlap <= 0:
        return False
    shorter_height = min(left[3] - left[1], right[3] - right[1])
    return overlap * 2 >= shorter_height


def _integer_median(values: Sequence[int]) -> int:
    if not values:
        raise _error("cannot derive a median from no geometry")
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) // 2


def _proposal_atom_ids(proposal: Mapping[str, Any]) -> list[str]:
    return list(dict.fromkeys(proposal["primary_atom_ids"] + proposal["supporting_atom_ids"]))


def _ordered_runs(
    atoms: Sequence[Mapping[str, Any]],
    proposal_atom_ids: set[str],
) -> list[_Run]:
    """Bind words to the preceding compatible line without reordering atoms."""

    runs: list[_Run] = []
    current: _Run | None = None
    for atom in atoms:
        atom_id = atom["source_local_id"]
        bbox = atom["canonical_bbox_mpt"]
        if (
            atom_id not in proposal_atom_ids
            or atom["authority"] != _PRIMARY_AUTHORITY
            or atom["kind"] not in {_LINE_KIND, _WORD_KIND}
            or not _positive_box(bbox)
        ):
            continue
        if atom["kind"] == _LINE_KIND:
            current = _Run(atom_ids=[atom_id], bbox=list(bbox))
            runs.append(current)
            continue
        word = (atom_id, list(bbox))
        if current is not None and _same_vertical_band(current.bbox, bbox):
            current.atom_ids.append(atom_id)
            current.bbox = _union([current.bbox, bbox])
            current.words.append(word)
        else:
            current = _Run(atom_ids=[atom_id], bbox=list(bbox), words=[word])
            runs.append(current)
    return runs


def _visual_rows(runs: Sequence[_Run]) -> list[_Row]:
    rows: list[_Row] = []
    for run in runs:
        if rows and _same_vertical_band(rows[-1].bbox, run.bbox):
            row = rows[-1]
            row.atom_ids.extend(run.atom_ids)
            row.bbox = _union([row.bbox, run.bbox])
            row.words.extend(run.words)
        else:
            rows.append(
                _Row(
                    atom_ids=list(run.atom_ids),
                    bbox=list(run.bbox),
                    words=list(run.words),
                )
            )
    return rows


def _dense_word_axes(rows: Sequence[_Row]) -> list[list[tuple[str, list[int]]]]:
    """Cluster repeated word starts using the proposal generator's geometry scale."""

    if len(rows) < 3:
        return []
    anchors = [
        (bbox[0], row_index, word_index, atom_id, bbox)
        for row_index, row in enumerate(rows)
        for word_index, (atom_id, bbox) in enumerate(row.words)
    ]
    if not anchors:
        return []
    tolerance = max(1, _integer_median([row.bbox[3] - row.bbox[1] for row in rows]) // 4)
    clusters: list[dict[str, Any]] = []
    for x_start, row_index, _word_index, atom_id, bbox in sorted(
        anchors,
        key=lambda item: (item[0], item[1], item[2]),
    ):
        matches = [
            (abs(x_start - cluster["center"]), cluster_index)
            for cluster_index, cluster in enumerate(clusters)
            if abs(x_start - cluster["center"]) <= tolerance
        ]
        if matches:
            _, cluster_index = min(matches)
            cluster = clusters[cluster_index]
            cluster["positions"].append(x_start)
            cluster["rows"].add(row_index)
            cluster["members"].append((atom_id, bbox))
            cluster["center"] = _integer_median(cluster["positions"])
        else:
            clusters.append(
                {
                    "center": x_start,
                    "positions": [x_start],
                    "rows": {row_index},
                    "members": [(atom_id, bbox)],
                }
            )
    minimum_support = max(3, (len(rows) * 3 + 4) // 5)
    return [
        list(cluster["members"]) for cluster in clusters if len(cluster["rows"]) >= minimum_support
    ]


def _node(
    *,
    ordinal: int,
    kind: GraphNodeKindV1,
    status: GraphNodeStatusV1,
    source_local_page_id: str,
    source_binding_sha256: str | None = None,
    bbox: Sequence[int] | None = None,
    atom_ids: Sequence[str] = (),
    proposal_ids: Sequence[str] = (),
) -> dict[str, Any]:
    return make_graph_node_v1(
        ordinal=ordinal,
        kind=kind,
        status=status,
        source_binding_sha256=source_binding_sha256,
        source_local_page_id=(
            None
            if kind in {GraphNodeKindV1.DOCUMENT, GraphNodeKindV1.PAGE}
            else source_local_page_id
        ),
        canonical_bbox_mpt=bbox,
        source_atom_ids=atom_ids,
        source_proposal_ids=proposal_ids,
    )


def _table_parts(
    *,
    proposal: Mapping[str, Any],
    eligible_atom_ids: Sequence[str],
    atoms: Sequence[Mapping[str, Any]],
    source_local_page_id: str,
    next_ordinal: int,
) -> tuple[_TableParts, int]:
    proposal_id = proposal["source_local_id"]
    proposal_atom_ids = list(eligible_atom_ids)
    atom_by_id = {atom["source_local_id"]: atom for atom in atoms}
    cited_boxes = [
        atom_by_id[atom_id]["canonical_bbox_mpt"]
        for atom_id in proposal_atom_ids
        if atom_id in atom_by_id and _positive_box(atom_by_id[atom_id]["canonical_bbox_mpt"])
    ]
    table_bbox = _union([proposal["canonical_bbox_mpt"], *cited_boxes])
    table = _node(
        ordinal=next_ordinal,
        kind=GraphNodeKindV1.TABLE,
        status=GraphNodeStatusV1.PRESTRUCTURAL_CANDIDATE,
        source_local_page_id=source_local_page_id,
        bbox=table_bbox,
        atom_ids=proposal_atom_ids,
        proposal_ids=(proposal_id,),
    )
    next_ordinal += 1

    row_parts = _visual_rows(_ordered_runs(atoms, set(proposal_atom_ids)))
    rows: list[dict[str, Any]] = []
    cells: list[list[dict[str, Any]]] = []
    cell_by_atom: dict[str, dict[str, Any]] = {}
    for row_part in row_parts:
        row = _node(
            ordinal=next_ordinal,
            kind=GraphNodeKindV1.ROW,
            status=GraphNodeStatusV1.PRESTRUCTURAL_CANDIDATE,
            source_local_page_id=source_local_page_id,
            bbox=row_part.bbox,
            atom_ids=row_part.atom_ids,
            proposal_ids=(proposal_id,),
        )
        next_ordinal += 1
        rows.append(row)
        row_cells: list[dict[str, Any]] = []
        for atom_id, bbox in row_part.words:
            cell = _node(
                ordinal=next_ordinal,
                kind=GraphNodeKindV1.CELL_OR_VALUE_POSITION,
                status=GraphNodeStatusV1.PRESTRUCTURAL_CANDIDATE,
                source_local_page_id=source_local_page_id,
                bbox=bbox,
                atom_ids=(atom_id,),
                proposal_ids=(proposal_id,),
            )
            next_ordinal += 1
            row_cells.append(cell)
            cell_by_atom[atom_id] = cell
        cells.append(row_cells)

    axes: list[dict[str, Any]] = []
    cell_axis_pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for members in _dense_word_axes(row_parts):
        member_ids = [atom_id for atom_id, _bbox_value in members]
        axis = _node(
            ordinal=next_ordinal,
            kind=GraphNodeKindV1.AXIS_OR_DIMENSION,
            status=GraphNodeStatusV1.PRESTRUCTURAL_CANDIDATE,
            source_local_page_id=source_local_page_id,
            bbox=_union([bbox for _atom_id, bbox in members]),
            atom_ids=member_ids,
            proposal_ids=(proposal_id,),
        )
        next_ordinal += 1
        axes.append(axis)
        cell_axis_pairs.extend(
            (cell_by_atom[atom_id], axis) for atom_id in member_ids if atom_id in cell_by_atom
        )
    return (
        _TableParts(
            proposal_id=proposal_id,
            table=table,
            rows=rows,
            cells=cells,
            axes=axes,
            cell_axis_pairs=cell_axis_pairs,
        ),
        next_ordinal,
    )


def build_page_prestructural_graph_v1(
    projection: Mapping[str, Any],
    proposal_projection: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the bounded candidate graph for one authenticated page."""

    source = validate_source_evidence_projection_v2(projection)
    proposals = validate_page_proposal_set_v2(proposal_projection, projection=source)
    source_local_page_id = source["source_local_page_id"]
    atoms = source["neutral_page_v1"]["atoms"]
    atom_ids = [atom["source_local_id"] for atom in atoms]
    atom_by_id = {atom["source_local_id"]: atom for atom in atoms}
    proposal_set = proposals["proposal_set_v1"]
    proposal_items = proposal_set["proposals"]
    upstream_by_atom = {item["source_atom_id"]: item for item in proposal_set["dispositions"]}
    memberships: dict[str, list[str]] = {}
    for proposal in proposal_items:
        for atom_id in _proposal_atom_ids(proposal):
            memberships.setdefault(atom_id, []).append(proposal["source_local_id"])
    tabular = (
        []
        if source["terminal"]
        else [proposal for proposal in proposal_items if proposal["kind"] == _TABULAR_KIND]
    )

    nodes: list[dict[str, Any]] = [
        _node(
            ordinal=1,
            kind=GraphNodeKindV1.DOCUMENT,
            status=GraphNodeStatusV1.BOUND_SOURCE_CONTEXT,
            source_local_page_id=source_local_page_id,
            source_binding_sha256=source["source_locator"]["source_sha256"],
        ),
        _node(
            ordinal=2,
            kind=GraphNodeKindV1.PAGE,
            status=GraphNodeStatusV1.BOUND_SOURCE_CONTEXT,
            source_local_page_id=source_local_page_id,
            source_binding_sha256=canonical_json_sha256_v1(source_local_page_id),
        ),
    ]
    next_ordinal = 4
    table_parts: list[_TableParts] = []
    for proposal in tabular:
        proposal_id = proposal["source_local_id"]
        eligible_atom_ids = [
            atom_id
            for atom_id in _proposal_atom_ids(proposal)
            if memberships.get(atom_id) == [proposal_id]
            and upstream_by_atom[atom_id]["source_object_id"] in {None, proposal_id}
            and atom_id in atom_by_id
            and atom_by_id[atom_id]["authority"] == _PRIMARY_AUTHORITY
            and atom_by_id[atom_id]["kind"] in {_LINE_KIND, _WORD_KIND}
            and _positive_box(atom_by_id[atom_id]["canonical_bbox_mpt"])
        ]
        if not eligible_atom_ids:
            continue
        parts, next_ordinal = _table_parts(
            proposal=proposal,
            eligible_atom_ids=eligible_atom_ids,
            atoms=atoms,
            source_local_page_id=source_local_page_id,
            next_ordinal=next_ordinal,
        )
        table_parts.append(parts)

    candidate_atom_ids = {
        atom_id for parts in table_parts for atom_id in parts.table["source_atom_ids"]
    }
    unresolved_atom_ids = [atom_id for atom_id in atom_ids if atom_id not in candidate_atom_ids]
    unresolved_boxes = [
        atom_by_id[atom_id]["canonical_bbox_mpt"]
        for atom_id in unresolved_atom_ids
        if _source_box(atom_by_id[atom_id]["canonical_bbox_mpt"])
    ] + [parts.table["canonical_bbox_mpt"] for parts in table_parts]
    unresolved = _node(
        ordinal=3,
        kind=GraphNodeKindV1.UNRESOLVED_REGION,
        status=GraphNodeStatusV1.EXPLICIT_UNRESOLVED,
        source_local_page_id=source_local_page_id,
        bbox=_union(unresolved_boxes) if unresolved_boxes else None,
        atom_ids=unresolved_atom_ids,
    )
    nodes.append(unresolved)
    for parts in table_parts:
        nodes.append(parts.table)
        for row, row_cells in zip(parts.rows, parts.cells, strict=True):
            nodes.append(row)
            nodes.extend(row_cells)
        nodes.extend(parts.axes)

    evidence_by_atom: dict[str, dict[str, Any]] = {}
    for atom in atoms:
        evidence = _node(
            ordinal=next_ordinal,
            kind=GraphNodeKindV1.EVIDENCE,
            status=GraphNodeStatusV1.BOUND_SOURCE_EVIDENCE,
            source_local_page_id=source_local_page_id,
            bbox=atom["canonical_bbox_mpt"],
            atom_ids=(atom["source_local_id"],),
        )
        next_ordinal += 1
        nodes.append(evidence)
        evidence_by_atom[atom["source_local_id"]] = evidence

    # Node construction is grouped for clarity above; the contract requires
    # ordinals to match the serialized sequence exactly.
    nodes.sort(key=lambda node: node["ordinal"])
    if [node["ordinal"] for node in nodes] != list(range(1, len(nodes) + 1)):
        raise _error("candidate node assembly produced a non-contiguous order")

    edge_specs: list[tuple[GraphEdgeKindV1, dict[str, Any], dict[str, Any]]] = [
        (GraphEdgeKindV1.PRESTRUCTURAL_CONTAINS, nodes[0], nodes[1]),
        (GraphEdgeKindV1.PRESTRUCTURAL_CONTAINS, nodes[1], unresolved),
    ]
    candidate_targets_by_atom: dict[str, list[dict[str, Any]]] = {}
    for parts in table_parts:
        edge_specs.append((GraphEdgeKindV1.PRESTRUCTURAL_CONTAINS, unresolved, parts.table))
        for atom_id in parts.table["source_atom_ids"]:
            candidate_targets_by_atom.setdefault(atom_id, []).append(parts.table)
        for row, row_cells in zip(parts.rows, parts.cells, strict=True):
            edge_specs.append((GraphEdgeKindV1.PRESTRUCTURAL_CONTAINS, parts.table, row))
            for atom_id in row["source_atom_ids"]:
                candidate_targets_by_atom.setdefault(atom_id, []).append(row)
            for cell in row_cells:
                edge_specs.append((GraphEdgeKindV1.PRESTRUCTURAL_CONTAINS, row, cell))
                for atom_id in cell["source_atom_ids"]:
                    candidate_targets_by_atom.setdefault(atom_id, []).append(cell)
            edge_specs.extend(
                (
                    GraphEdgeKindV1.PRECEDES_IN_AUTHENTICATED_SOURCE_ORDER,
                    left,
                    right,
                )
                for left, right in zip(row_cells, row_cells[1:], strict=False)
            )
        edge_specs.extend(
            (
                GraphEdgeKindV1.PRECEDES_IN_AUTHENTICATED_SOURCE_ORDER,
                left,
                right,
            )
            for left, right in zip(parts.rows, parts.rows[1:], strict=False)
        )
        for axis in parts.axes:
            edge_specs.append((GraphEdgeKindV1.PRESTRUCTURAL_CONTAINS, parts.table, axis))
            for atom_id in axis["source_atom_ids"]:
                candidate_targets_by_atom.setdefault(atom_id, []).append(axis)
        edge_specs.extend(
            (GraphEdgeKindV1.PRESTRUCTURAL_ALIGNED_TO_AXIS, cell, axis)
            for cell, axis in parts.cell_axis_pairs
        )

    for atom_id in atom_ids:
        targets = candidate_targets_by_atom.get(atom_id, [])
        if not targets:
            targets = [unresolved]
        edge_specs.extend(
            (GraphEdgeKindV1.SUPPORTS, evidence_by_atom[atom_id], target) for target in targets
        )
    edges = [
        make_graph_edge_v1(
            ordinal=ordinal,
            kind=kind,
            from_node_id=left["node_id"],
            to_node_id=right["node_id"],
        )
        for ordinal, (kind, left, right) in enumerate(edge_specs, start=1)
    ]

    dispositions = []
    candidate_priority = {
        GraphNodeKindV1.CELL_OR_VALUE_POSITION.value: 0,
        GraphNodeKindV1.ROW.value: 1,
        GraphNodeKindV1.AXIS_OR_DIMENSION.value: 2,
        GraphNodeKindV1.TABLE.value: 3,
    }
    for atom in atoms:
        atom_id = atom["source_local_id"]
        upstream = upstream_by_atom[atom_id]
        upstream_primary = upstream["primary_disposition"]
        targets = candidate_targets_by_atom.get(atom_id, [])
        if upstream_primary == "UPSTREAM_QUARANTINED":
            primary = AtomGraphDispositionV1.UPSTREAM_QUARANTINED
            owner = unresolved
        elif upstream_primary == "UPSTREAM_TERMINAL_UNRESOLVED":
            primary = AtomGraphDispositionV1.UPSTREAM_TERMINAL_UNRESOLVED
            owner = unresolved
        elif targets:
            primary = AtomGraphDispositionV1.SUPPORTS_PRESTRUCTURAL_CANDIDATE
            owner = min(
                targets,
                key=lambda target: (candidate_priority[target["kind"]], target["ordinal"]),
            )
        else:
            primary = AtomGraphDispositionV1.RETAINED_UNRESOLVED
            owner = unresolved
        dispositions.append(
            make_atom_graph_disposition_v1(
                source_atom_id=atom_id,
                upstream_disposition=upstream,
                evidence_node_id=evidence_by_atom[atom_id]["node_id"],
                primary_disposition=primary,
                owner_node_id=owner["node_id"],
            )
        )

    return make_page_prestructural_graph_v1(
        source,
        proposals,
        nodes=nodes,
        edges=edges,
        atom_dispositions=dispositions,
    )
