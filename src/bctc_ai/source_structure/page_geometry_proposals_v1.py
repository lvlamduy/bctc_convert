"""Deterministic page-local geometry proposals over neutral source atoms.

The generator deliberately stops at source-block and tabular-geometry
candidates.  It reads atom order, kind, authority, and canonical bounding
boxes only.  It does not interpret visible text or promote any downstream
financial structure.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    ATOM_DISPOSITION_FORMAT_VERSION,
    NEUTRAL_PAGE_FORMAT_VERSION,
    AtomAuthority,
    AtomKind,
    PrimaryDisposition,
    ProposalKind,
    make_empty_page_proposal_set_v1,
    make_page_proposal_set_v1,
    make_source_object_id_v1,
    validate_neutral_page_envelope_v1,
)
from bctc_ai.source_structure.contracts_v2 import (
    SOURCE_PROJECTION_FORMAT_VERSION_V2,
    validate_source_evidence_projection_v2,
)

__all__ = [
    "PageGeometryProposalError",
    "generate_page_geometry_proposals_v1",
]


class PageGeometryProposalError(ValueError):
    """Input evidence is not one of the closed neutral page formats."""


_PRIMARY_AUTHORITY = AtomAuthority.AUTHENTICATED_PRIMARY.value
_LINE_KIND = AtomKind.LINE.value
_WORD_KIND = AtomKind.WORD.value


@dataclass
class _Run:
    atom_indexes: list[int]
    bbox: list[int]
    word_x_starts: list[tuple[int, int]] = field(default_factory=list)


@dataclass
class _VisualRow:
    runs: list[_Run]
    atom_indexes: list[int]
    bbox: list[int]
    word_x_starts: list[tuple[int, int]]


def _union(boxes: list[list[int]]) -> list[int]:
    return [
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    ]


def _positive_box(value: Any) -> bool:
    return (
        type(value) is list
        and len(value) == 4
        and all(type(coordinate) is int for coordinate in value)
        and value[0] < value[2]
        and value[1] < value[3]
    )


def _same_vertical_band(left: list[int], right: list[int]) -> bool:
    overlap = min(left[3], right[3]) - max(left[1], right[1])
    if overlap <= 0:
        return False
    shorter_height = min(left[3] - left[1], right[3] - right[1])
    return overlap * 2 >= shorter_height


def _neutral_page(evidence: Mapping[str, Any]) -> dict[str, Any]:
    if type(evidence) is not dict:
        raise PageGeometryProposalError("page geometry evidence must be a plain object")
    version = evidence.get("format_version")
    if version == NEUTRAL_PAGE_FORMAT_VERSION:
        return validate_neutral_page_envelope_v1(evidence)
    if version == SOURCE_PROJECTION_FORMAT_VERSION_V2:
        return validate_source_evidence_projection_v2(evidence)["neutral_page_v1"]
    raise PageGeometryProposalError("page geometry evidence format is outside the closed boundary")


def _ordered_primary_runs(page: Mapping[str, Any]) -> list[_Run]:
    """Bind words to their preceding, vertically compatible line in atom order."""

    atoms = page["atoms"]
    runs: list[_Run] = []
    current: _Run | None = None
    for atom_index, atom in enumerate(atoms):
        if (
            atom["authority"] != _PRIMARY_AUTHORITY
            or atom["kind"] not in {_LINE_KIND, _WORD_KIND}
            or not _positive_box(atom["canonical_bbox_mpt"])
        ):
            continue
        bbox = atom["canonical_bbox_mpt"]
        if atom["kind"] == _LINE_KIND:
            current = _Run(atom_indexes=[atom_index], bbox=list(bbox))
            runs.append(current)
            continue
        word_anchor = (bbox[0], atom_index)
        if current is not None and _same_vertical_band(current.bbox, bbox):
            current.atom_indexes.append(atom_index)
            current.bbox = _union([current.bbox, bbox])
            current.word_x_starts.append(word_anchor)
        else:
            current = _Run(
                atom_indexes=[atom_index],
                bbox=list(bbox),
                word_x_starts=[word_anchor],
            )
            runs.append(current)
    return runs


def _visual_rows(runs: list[_Run]) -> list[_VisualRow]:
    """Merge same-band runs without changing their authenticated atom order."""

    rows: list[_VisualRow] = []
    for run in runs:
        if rows and _same_vertical_band(rows[-1].bbox, run.bbox):
            row = rows[-1]
            row.runs.append(run)
            row.atom_indexes.extend(run.atom_indexes)
            row.bbox = _union([row.bbox, run.bbox])
            row.word_x_starts.extend(run.word_x_starts)
            row.word_x_starts.sort(key=lambda item: (item[0], item[1]))
        else:
            rows.append(
                _VisualRow(
                    runs=[run],
                    atom_indexes=list(run.atom_indexes),
                    bbox=list(run.bbox),
                    word_x_starts=sorted(run.word_x_starts),
                )
            )
    return rows


def _integer_median(values: list[int]) -> int:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) // 2


def _vertical_blocks(rows: list[_VisualRow]) -> list[list[_VisualRow]]:
    if not rows:
        return []
    typical_height = max(1, _integer_median([row.bbox[3] - row.bbox[1] for row in rows]))
    blocks: list[list[_VisualRow]] = [[rows[0]]]
    for row in rows[1:]:
        prior = blocks[-1][-1]
        vertical_gap = max(0, row.bbox[1] - prior.bbox[3])
        if vertical_gap > typical_height * 2:
            blocks.append([row])
        else:
            blocks[-1].append(row)
    return blocks


def _aligned_column_count(block: list[_VisualRow]) -> tuple[int, int]:
    """Return dense aligned-column and qualifying-row counts for one block."""

    if len(block) < 3:
        return 0, 0
    anchors = [
        (x_start, row_index, atom_index)
        for row_index, row in enumerate(block)
        for x_start, atom_index in row.word_x_starts
    ]
    if not anchors:
        return 0, 0
    atom_heights = [row.bbox[3] - row.bbox[1] for row in block if row.word_x_starts]
    tolerance = max(1, _integer_median(atom_heights) // 4)
    clusters: list[dict[str, Any]] = []
    for x_start, row_index, _atom_index in sorted(anchors):
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
            cluster["center"] = _integer_median(cluster["positions"])
        else:
            clusters.append(
                {
                    "center": x_start,
                    "positions": [x_start],
                    "rows": {row_index},
                }
            )
    minimum_support = max(3, (len(block) * 3 + 4) // 5)
    dense_clusters = [cluster for cluster in clusters if len(cluster["rows"]) >= minimum_support]
    dense_memberships = [
        sum(row_index in cluster["rows"] for cluster in dense_clusters)
        for row_index in range(len(block))
    ]
    qualifying_rows = sum(count >= 2 for count in dense_memberships)
    return len(dense_clusters), qualifying_rows


def _proposal_kind(block: list[_VisualRow]) -> ProposalKind:
    aligned_columns, qualifying_rows = _aligned_column_count(block)
    minimum_support = max(3, (len(block) * 3 + 4) // 5)
    if aligned_columns >= 2 and qualifying_rows >= minimum_support:
        return ProposalKind.TABULAR_GEOMETRY_CANDIDATE
    return ProposalKind.SOURCE_BLOCK_CANDIDATE


def _proposal(
    page: Mapping[str, Any],
    block: list[_VisualRow],
) -> dict[str, Any]:
    atom_indexes = sorted(index for row in block for index in row.atom_indexes)
    atoms = page["atoms"]
    atom_ids = [atoms[index]["source_local_id"] for index in atom_indexes]
    bbox = _union([atoms[index]["canonical_bbox_mpt"] for index in atom_indexes])
    kind = _proposal_kind(block)
    evidence_codes = {
        "BBOX_CONTAINS_PRIMARY_ATOMS",
        "LOCAL_GEOMETRY",
    }
    if len(atom_indexes) > 1:
        evidence_codes.add("ADJACENT_ATOM_GEOMETRY")
    if len(block) > 1:
        evidence_codes.add("VERTICAL_GAP_COHERENCE")
    if kind is ProposalKind.TABULAR_GEOMETRY_CANDIDATE:
        evidence_codes.update({"DENSE_TABULAR_ALIGNMENT", "HORIZONTAL_ALIGNMENT"})
    codes = sorted(evidence_codes)
    identity = {
        "source_local_page_id": page["source_local_page_id"],
        "request_sha256": page["source_locator"]["request_sha256"],
        "kind": kind.value,
        "canonical_bbox_mpt": bbox,
        "primary_atom_ids": atom_ids,
        "supporting_atom_ids": [],
        "evidence_codes": codes,
    }
    return {
        "source_local_id": make_source_object_id_v1("source_object", identity),
        "kind": kind.value,
        "canonical_bbox_mpt": bbox,
        "primary_atom_ids": atom_ids,
        "supporting_atom_ids": [],
        "evidence_codes": codes,
    }


def generate_page_geometry_proposals_v1(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Generate closed geometry candidates and exactly one disposition per atom."""

    page = _neutral_page(evidence)
    empty = make_empty_page_proposal_set_v1(page)
    if page["terminal"]:
        return empty
    proposals = [
        _proposal(page, block)
        for block in _vertical_blocks(_visual_rows(_ordered_primary_runs(page)))
    ]
    owner_by_atom = {
        atom_id: proposal["source_local_id"]
        for proposal in proposals
        for atom_id in proposal["primary_atom_ids"]
    }
    dispositions = empty["dispositions"]
    for disposition in dispositions:
        owner = owner_by_atom.get(disposition["source_atom_id"])
        if owner is None:
            continue
        disposition.update(
            {
                "format_version": ATOM_DISPOSITION_FORMAT_VERSION,
                "primary_disposition": PrimaryDisposition.OWNED_BY_SOURCE_OBJECT.value,
                "source_object_id": owner,
                "reason_code": "PRIMARY_LOCAL_GEOMETRY_OWNERSHIP",
            }
        )
    return make_page_proposal_set_v1(
        page,
        proposals=proposals,
        dispositions=dispositions,
    )
