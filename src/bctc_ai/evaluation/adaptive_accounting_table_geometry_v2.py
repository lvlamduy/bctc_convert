"""Fail-closed, scale-adaptive geometry proposals for accounting tables.

This module is deliberately below the semantic and accounting layers.  It
does not read text, values, periods, banks, notes, or families.  A caller
first supplies a bounded candidate region and classifies source atoms as
``LABEL``, ``VALUE``, or ``OTHER``.  The resolver then measures row bands and
value lanes, but every inferred blank cell and adjacent-page relation remains
a proposal that requires independent evidence.

All decisions use exact integers.  Coordinates are retained in source pixels
and also projected to integer parts-per-million (ppm) inside the caller's
candidate region.  No floating-point tolerance or page-specific route is
used.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import Any

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

__all__ = [
    "ADAPTIVE_ACCOUNTING_TABLE_GEOMETRY_AUTHORITY_V2",
    "ADAPTIVE_ACCOUNTING_TABLE_GEOMETRY_FORMAT_VERSION_V2",
    "AdaptiveAccountingTableGeometryV2Error",
    "build_row_band_envelope_v2",
    "compare_page_lane_signatures_v2",
    "normalize_bbox_to_ppm_v2",
    "resolve_accounting_table_geometry_v2",
]


ADAPTIVE_ACCOUNTING_TABLE_GEOMETRY_FORMAT_VERSION_V2 = "ADAPTIVE_ACCOUNTING_TABLE_GEOMETRY_V2"
ADAPTIVE_ACCOUNTING_TABLE_GEOMETRY_AUTHORITY_V2 = (
    "GEOMETRY_PROPOSALS_ONLY_NO_TEXT_VALUE_PERIOD_UNIT_FAMILY_MAPPING_"
    "BLANK_OR_CROSS_PAGE_CONTINUATION_AUTHORITY"
)

_PPM = 1_000_000
_KINDS = frozenset({"LABEL", "OTHER", "VALUE"})
_ALIGNMENTS = ("RIGHT", "CENTER", "LEFT")


class AdaptiveAccountingTableGeometryV2Error(ValueError):
    """The bounded geometry input is malformed or cannot be measured."""


def _error(message: str) -> AdaptiveAccountingTableGeometryV2Error:
    return AdaptiveAccountingTableGeometryV2Error(message)


def _bbox(value: Any, *, extent: Sequence[int] | None = None) -> list[int]:
    if (
        type(value) not in {list, tuple}
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or value[0] < 0
        or value[1] < 0
        or value[0] >= value[2]
        or value[1] >= value[3]
    ):
        raise _error("bbox must be four exact nonnegative positive-area integers")
    parsed = list(value)
    if extent is not None and (
        parsed[0] < extent[0]
        or parsed[1] < extent[1]
        or parsed[2] > extent[2]
        or parsed[3] > extent[3]
    ):
        raise _error("bbox falls outside its exact extent")
    return parsed


def _median(values: Sequence[int]) -> int:
    if not values or any(type(value) is not int for value in values):
        raise _error("exact geometry median requires nonempty integer input")
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) // 2


def _union(boxes: Sequence[Sequence[int]]) -> list[int]:
    parsed = [_bbox(box) for box in boxes]
    if not parsed:
        raise _error("bbox envelope requires at least one member")
    return [
        min(box[0] for box in parsed),
        min(box[1] for box in parsed),
        max(box[2] for box in parsed),
        max(box[3] for box in parsed),
    ]


def _overlaps(left: Sequence[int], right: Sequence[int]) -> bool:
    return left[0] < right[2] and right[0] < left[2] and left[1] < right[3] and right[1] < left[3]


def _normalize(coordinate: int, *, origin: int, dimension: int) -> int:
    offset = coordinate - origin
    if type(coordinate) is not int or dimension <= 0 or not 0 <= offset <= dimension:
        raise _error("coordinate cannot be normalized inside its exact extent")
    return (offset * _PPM + dimension // 2) // dimension


def _normalize_center2(center2: int, *, origin: int, dimension: int) -> int:
    offset2 = center2 - 2 * origin
    if type(center2) is not int or dimension <= 0 or not 0 <= offset2 <= 2 * dimension:
        raise _error("doubled center cannot be normalized inside its exact extent")
    return (offset2 * _PPM + dimension) // (2 * dimension)


def normalize_bbox_to_ppm_v2(bbox: Sequence[int], *, extent_bbox: Sequence[int]) -> list[int]:
    """Normalize a bbox to exact integer ppm inside an arbitrary extent."""

    extent = _bbox(extent_bbox)
    box = _bbox(bbox, extent=extent)
    width = extent[2] - extent[0]
    height = extent[3] - extent[1]
    return [
        _normalize(box[0], origin=extent[0], dimension=width),
        _normalize(box[1], origin=extent[1], dimension=height),
        _normalize(box[2], origin=extent[0], dimension=width),
        _normalize(box[3], origin=extent[1], dimension=height),
    ]


def build_row_band_envelope_v2(
    member_bboxes: Sequence[Sequence[int]], *, extent_bbox: Sequence[int]
) -> dict[str, Any]:
    """Build one exact row envelope without deciding its semantic role."""

    extent = _bbox(extent_bbox)
    boxes = [_bbox(box, extent=extent) for box in member_bboxes]
    if not boxes:
        raise _error("row-band envelope requires at least one member bbox")
    envelope = _union(boxes)
    centers2 = [box[1] + box[3] for box in boxes]
    heights = [box[3] - box[1] for box in boxes]
    return {
        "bbox": envelope,
        "center2_median": _median(centers2),
        "height_median": _median(heights),
        "member_count": len(boxes),
        "normalized_bbox_ppm": normalize_bbox_to_ppm_v2(envelope, extent_bbox=extent),
        "vertical_center2_spread": max(centers2) - min(centers2),
    }


@dataclass(frozen=True)
class _Atom:
    atom_id: str
    bbox: list[int]
    kind: str

    @property
    def center2_x(self) -> int:
        return self.bbox[0] + self.bbox[2]

    @property
    def center2_y(self) -> int:
        return self.bbox[1] + self.bbox[3]


@dataclass
class _Row:
    atoms: list[_Atom]
    minimum_center2: int
    maximum_center2: int


@dataclass(frozen=True)
class _ValueGroup:
    group_id: str
    row_ordinal: int
    atom_ids: tuple[str, ...]
    bbox: list[int]

    @property
    def center2(self) -> int:
        return self.bbox[0] + self.bbox[2]


@dataclass
class _ColumnCluster:
    groups: list[_ValueGroup]
    minimum_anchor2: int
    maximum_anchor2: int


@dataclass(frozen=True)
class _Alignment:
    mode: str
    clusters: tuple[_ColumnCluster, ...]
    eligible: tuple[_ColumnCluster, ...]
    orphan_count: int
    duplicate_row_count: int
    dispersion: int
    cost: int


def _atoms(
    raw_atoms: Sequence[Mapping[str, Any]],
    *,
    page_extent: Sequence[int],
    region: Sequence[int],
) -> tuple[list[_Atom], list[dict[str, Any]]]:
    if type(raw_atoms) not in {list, tuple} or not raw_atoms:
        raise _error("geometry resolver requires one nonempty exact atom sequence")
    parsed: list[_Atom] = []
    uncertainties: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_atoms:
        if type(raw) is not dict or set(raw) != {"atom_id", "bbox", "kind"}:
            raise _error("geometry atom must contain exactly atom_id, bbox, and kind")
        atom_id = raw["atom_id"]
        kind = raw["kind"]
        if type(atom_id) is not str or not atom_id or atom_id in seen:
            raise _error("geometry atom IDs must be unique nonempty strings")
        if type(kind) is not str or kind not in _KINDS:
            raise _error("geometry atom kind is outside LABEL/OTHER/VALUE")
        seen.add(atom_id)
        box = _bbox(raw["bbox"], extent=page_extent)
        contained = (
            region[0] <= box[0]
            and region[1] <= box[1]
            and box[2] <= region[2]
            and box[3] <= region[3]
        )
        if not contained:
            if _overlaps(box, region):
                uncertainties.append(
                    {
                        "atom_id": atom_id,
                        "kind": "SCOPE_EDGE_INTERSECTION_OMITTED",
                    }
                )
            continue
        parsed.append(_Atom(atom_id=atom_id, bbox=box, kind=kind))
    if not parsed:
        raise _error("candidate region contains no complete geometry atoms")
    return parsed, uncertainties


def _cluster_rows(
    atoms: Sequence[_Atom], *, typical_height: int
) -> tuple[list[_Row], list[dict[str, Any]]]:
    tolerance2 = max(2, (typical_height * 4 + 2) // 3)
    rows: list[_Row] = []
    uncertainties: list[dict[str, Any]] = []
    for atom in sorted(atoms, key=lambda item: (item.center2_y, item.bbox[0], item.atom_id)):
        height = atom.bbox[3] - atom.bbox[1]
        if height > typical_height * 5 // 2:
            uncertainties.append(
                {
                    "atom_id": atom.atom_id,
                    "height": height,
                    "kind": "TALL_ATOM_CROSSES_POSSIBLE_ROW_BANDS_OMITTED",
                    "typical_height": typical_height,
                }
            )
            continue
        compatible = []
        for row in reversed(rows):
            if atom.center2_y - row.maximum_center2 > tolerance2:
                break
            if (
                max(row.maximum_center2, atom.center2_y) - min(row.minimum_center2, atom.center2_y)
                <= tolerance2
            ):
                compatible.append(row)
        if compatible:
            row = min(
                compatible,
                key=lambda item: (
                    abs(atom.center2_y - _median([member.center2_y for member in item.atoms])),
                    item.minimum_center2,
                ),
            )
            row.atoms.append(atom)
            row.minimum_center2 = min(row.minimum_center2, atom.center2_y)
            row.maximum_center2 = max(row.maximum_center2, atom.center2_y)
        else:
            rows.append(
                _Row(
                    atoms=[atom],
                    minimum_center2=atom.center2_y,
                    maximum_center2=atom.center2_y,
                )
            )
    rows.sort(
        key=lambda row: (_median([atom.center2_y for atom in row.atoms]), row.minimum_center2)
    )
    return rows, uncertainties


def _value_groups(rows: Sequence[_Row], *, typical_height: int) -> list[_ValueGroup]:
    maximum_fragment_gap = max(1, typical_height // 2)
    groups: list[_ValueGroup] = []
    for row_ordinal, row in enumerate(rows):
        values = sorted(
            (atom for atom in row.atoms if atom.kind == "VALUE"),
            key=lambda atom: (atom.bbox[0], atom.bbox[2], atom.atom_id),
        )
        fragments: list[list[_Atom]] = []
        for atom in values:
            if fragments:
                prior_box = _union([member.bbox for member in fragments[-1]])
                gap = atom.bbox[0] - prior_box[2]
                overlap = min(prior_box[3], atom.bbox[3]) - max(prior_box[1], atom.bbox[1])
                shorter = min(prior_box[3] - prior_box[1], atom.bbox[3] - atom.bbox[1])
                if gap <= maximum_fragment_gap and overlap * 2 >= shorter:
                    fragments[-1].append(atom)
                    continue
            fragments.append([atom])
        for group_ordinal, members in enumerate(fragments):
            groups.append(
                _ValueGroup(
                    group_id=f"row-{row_ordinal + 1:04d}:value-{group_ordinal + 1:02d}",
                    row_ordinal=row_ordinal,
                    atom_ids=tuple(sorted(member.atom_id for member in members)),
                    bbox=_union([member.bbox for member in members]),
                )
            )
    return groups


def _anchor2(group: _ValueGroup, mode: str) -> int:
    if mode == "RIGHT":
        return 2 * group.bbox[2]
    if mode == "CENTER":
        return group.bbox[0] + group.bbox[2]
    if mode == "LEFT":
        return 2 * group.bbox[0]
    raise _error("accounting value-lane alignment mode drifted")


def _alignment(
    groups: Sequence[_ValueGroup],
    *,
    mode: str,
    tolerance2: int,
    expected_lane_count: int | None,
) -> _Alignment:
    clusters: list[_ColumnCluster] = []
    for group in sorted(groups, key=lambda item: (_anchor2(item, mode), item.group_id)):
        anchor2 = _anchor2(group, mode)
        compatible = []
        for cluster in reversed(clusters):
            if anchor2 - cluster.maximum_anchor2 > tolerance2:
                break
            if (
                max(cluster.maximum_anchor2, anchor2) - min(cluster.minimum_anchor2, anchor2)
                <= tolerance2
            ):
                compatible.append(cluster)
        if compatible:
            cluster = min(
                compatible,
                key=lambda item: abs(anchor2 - (item.minimum_anchor2 + item.maximum_anchor2) // 2),
            )
            cluster.groups.append(group)
            cluster.minimum_anchor2 = min(cluster.minimum_anchor2, anchor2)
            cluster.maximum_anchor2 = max(cluster.maximum_anchor2, anchor2)
        else:
            clusters.append(
                _ColumnCluster(
                    groups=[group],
                    minimum_anchor2=anchor2,
                    maximum_anchor2=anchor2,
                )
            )
    row_count = len({group.row_ordinal for group in groups})
    minimum_support = 2 if row_count >= 2 else 1
    eligible = tuple(
        cluster
        for cluster in clusters
        if len({group.row_ordinal for group in cluster.groups}) >= minimum_support
    )
    eligible_group_ids = {group.group_id for cluster in eligible for group in cluster.groups}
    orphan_count = sum(group.group_id not in eligible_group_ids for group in groups)
    duplicate_row_count = sum(
        len(cluster.groups) - len({group.row_ordinal for group in cluster.groups})
        for cluster in eligible
    )
    dispersion = 0
    for cluster in eligible:
        center = _median([_anchor2(member, mode) for member in cluster.groups])
        dispersion += sum(abs(_anchor2(group, mode) - center) for group in cluster.groups)
    mismatch = 0 if expected_lane_count is None else abs(len(eligible) - expected_lane_count)
    cost = mismatch * 1_000_000_000_000 + duplicate_row_count * 1_000_000_000
    cost += orphan_count * 1_000_000 + dispersion
    return _Alignment(
        mode=mode,
        clusters=tuple(clusters),
        eligible=eligible,
        orphan_count=orphan_count,
        duplicate_row_count=duplicate_row_count,
        dispersion=dispersion,
        cost=cost,
    )


def _partition(alignment: _Alignment) -> tuple[tuple[str, ...], ...]:
    return tuple(
        sorted(
            tuple(sorted(group.group_id for group in cluster.groups))
            for cluster in alignment.eligible
        )
    )


def _missing_region(
    *,
    lane: Mapping[str, Any],
    row: _Row,
    row_ordinal: int,
    rows: Sequence[_Row],
    groups: Sequence[_ValueGroup],
    assignments: Sequence[Mapping[str, Any]],
    lanes: Sequence[Mapping[str, Any]],
    alignment_mode: str,
    typical_height: int,
    region: Sequence[int],
) -> dict[str, Any]:
    assigned_by_group = {
        item["value_group_id"]: item
        for item in assignments
        if item["status"] == "ASSIGNED_TO_UNIQUE_ROW_LANE"
    }
    row_groups = [group for group in groups if group.row_ordinal == row_ordinal]
    visible_boxes = [group.bbox for group in row_groups if group.group_id in assigned_by_group]
    if not visible_boxes:
        raise _error("missing-cell proposal requires one independently visible sibling lane")
    row_center2 = _median([box[1] + box[3] for box in visible_boxes])
    row_height = _median([box[3] - box[1] for box in visible_boxes])
    padding_y = max(1, typical_height // 5)
    top = max(region[1], row_center2 // 2 - row_height // 2 - padding_y)
    bottom = min(region[3], (row_center2 + 1) // 2 + (row_height + 1) // 2 + padding_y)
    other_centers2 = sorted(
        {
            _median(
                [group.bbox[1] + group.bbox[3] for group in groups if group.row_ordinal == other]
            )
            for other in range(len(rows))
            if other != row_ordinal and any(group.row_ordinal == other for group in groups)
        }
    )
    prior = [center2 for center2 in other_centers2 if center2 < row_center2]
    following = [center2 for center2 in other_centers2 if center2 > row_center2]
    if prior:
        top = max(top, (max(prior) + row_center2 + 2) // 4)
    if following:
        bottom = min(bottom, (min(following) + row_center2) // 4)

    lane_ordinal = lane["column_ordinal"]
    widths = [
        group.bbox[2] - group.bbox[0]
        for group in groups
        if assigned_by_group.get(group.group_id, {}).get("column_ordinal") == lane_ordinal
    ]
    width = _median(widths) if widths else typical_height * 3
    anchor2 = lane["anchor2_median"]
    padding_x = max(1, typical_height // 3)
    if alignment_mode == "RIGHT":
        right = (anchor2 + 1) // 2 + padding_x
        left = right - width - 2 * padding_x
    elif alignment_mode == "LEFT":
        left = anchor2 // 2 - padding_x
        right = left + width + 2 * padding_x
    else:
        center = anchor2 // 2
        left = center - width // 2 - padding_x
        right = center + (width + 1) // 2 + padding_x

    visual_centers2 = [item["visual_center2_median"] for item in lanes]
    if lane_ordinal > 0:
        left = max(
            left,
            (visual_centers2[lane_ordinal - 1] + visual_centers2[lane_ordinal] + 2) // 4,
        )
    if lane_ordinal + 1 < len(lanes):
        right = min(
            right,
            (visual_centers2[lane_ordinal] + visual_centers2[lane_ordinal + 1]) // 4,
        )
    left = max(region[0], left)
    right = min(region[2], right)
    if right <= left or bottom <= top:
        raise _error("clipped missing-cell proposal has no positive area")
    bbox = [left, top, right, bottom]
    return {
        "authority": "PIXEL_REGION_PROPOSAL_REQUIRES_INDEPENDENT_RECOGNITION",
        "column_ordinal": lane_ordinal,
        "raw_pixel_bbox": bbox,
        "normalized_scope_bbox_ppm": normalize_bbox_to_ppm_v2(bbox, extent_bbox=region),
        "row_ordinal": row_ordinal,
        "visible_lane_ordinals": sorted(
            {
                item["column_ordinal"]
                for item in assignments
                if item["status"] == "ASSIGNED_TO_UNIQUE_ROW_LANE"
                and next(
                    group.row_ordinal
                    for group in groups
                    if group.group_id == item["value_group_id"]
                )
                == row_ordinal
            }
        ),
    }


def resolve_accounting_table_geometry_v2(
    atoms: Sequence[Mapping[str, Any]],
    *,
    page_width: int,
    page_height: int,
    expected_lane_count: int | None = None,
    region_bbox: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Resolve a bounded table's row/lane geometry as non-authoritative proposals."""

    if type(page_width) is not int or page_width <= 0:
        raise _error("page width must be one positive exact integer")
    if type(page_height) is not int or page_height <= 0:
        raise _error("page height must be one positive exact integer")
    if expected_lane_count is not None and (
        type(expected_lane_count) is not int or not 1 <= expected_lane_count <= 16
    ):
        raise _error("expected lane count must be one exact integer inside [1, 16]")
    page_extent = [0, 0, page_width, page_height]
    region = page_extent if region_bbox is None else _bbox(region_bbox, extent=page_extent)
    parsed, uncertainties = _atoms(atoms, page_extent=page_extent, region=region)
    typical_height = _median([atom.bbox[3] - atom.bbox[1] for atom in parsed])
    rows, row_uncertainties = _cluster_rows(parsed, typical_height=typical_height)
    uncertainties.extend(row_uncertainties)
    if not rows:
        raise _error("candidate region has no measurable row bands")
    groups = _value_groups(rows, typical_height=typical_height)
    tolerance2 = max(2, typical_height * 2)
    alternatives = [
        _alignment(
            groups,
            mode=mode,
            tolerance2=tolerance2,
            expected_lane_count=expected_lane_count,
        )
        for mode in _ALIGNMENTS
    ]
    ranked = sorted(alternatives, key=lambda item: (item.cost, _ALIGNMENTS.index(item.mode)))
    selected = ranked[0]
    ambiguity_margin = ranked[1].cost - selected.cost
    equivalent_modes = [
        item.mode
        for item in ranked
        if item.cost == selected.cost and _partition(item) == _partition(selected)
    ]
    if (
        len(ranked) > 1
        and ranked[1].cost == selected.cost
        and _partition(ranked[1]) != _partition(selected)
    ):
        uncertainties.append(
            {
                "ambiguity_margin": ambiguity_margin,
                "kind": "ALIGNMENT_MODE_HAS_MULTIPLE_EXACT_PARTITIONS",
                "modes": [selected.mode, ranked[1].mode],
            }
        )
    if not groups:
        uncertainties.append({"kind": "CANDIDATE_REGION_HAS_NO_VALUE_GEOMETRY"})
    if expected_lane_count is not None and len(selected.eligible) != expected_lane_count:
        uncertainties.append(
            {
                "expected_lane_count": expected_lane_count,
                "kind": "EXPECTED_LANE_COUNT_UNRESOLVED",
                "measured_lane_count": len(selected.eligible),
            }
        )

    lane_clusters = sorted(
        selected.eligible,
        key=lambda cluster: _median([_anchor2(group, selected.mode) for group in cluster.groups]),
    )
    lanes: list[dict[str, Any]] = []
    for ordinal, cluster in enumerate(lane_clusters):
        lane_groups = cluster.groups
        lanes.append(
            {
                "anchor2_median": _median(
                    [_anchor2(group, selected.mode) for group in lane_groups]
                ),
                "bbox_envelope": _union([group.bbox for group in lane_groups]),
                "column_ordinal": ordinal,
                "source_row_ordinals": sorted({group.row_ordinal for group in lane_groups}),
                "supporting_value_group_ids": sorted(group.group_id for group in lane_groups),
                "vertical_support_count": len({group.row_ordinal for group in lane_groups}),
                "visual_center2_median": _median([group.center2 for group in lane_groups]),
            }
        )

    assignments: list[dict[str, Any]] = []
    for group in groups:
        if not lanes:
            assignments.append(
                {
                    "atom_ids": list(group.atom_ids),
                    "bbox": group.bbox,
                    "column_ordinal": None,
                    "row_ordinal": group.row_ordinal,
                    "status": "NO_RESOLVED_LANE_AXIS",
                    "value_group_id": group.group_id,
                }
            )
            continue
        anchor2 = _anchor2(group, selected.mode)
        distances = sorted(
            ((abs(anchor2 - lane["anchor2_median"]), lane["column_ordinal"]) for lane in lanes),
            key=lambda item: (item[0], item[1]),
        )
        best_distance, best_lane = distances[0]
        second_distance = distances[1][0] if len(distances) > 1 else None
        margin = second_distance - best_distance if second_distance is not None else None
        minimum_gap2 = (
            min(right["anchor2_median"] - left["anchor2_median"] for left, right in pairwise(lanes))
            if len(lanes) > 1
            else tolerance2 * 4
        )
        required_margin = max(2, minimum_gap2 // 6)
        contained_visual_lanes = [
            lane["column_ordinal"]
            for lane in lanes
            if 2 * group.bbox[0] <= lane["visual_center2_median"] <= 2 * group.bbox[2]
        ]
        if len(contained_visual_lanes) > 1:
            status = "CROSS_LANE_MERGED_VALUE_GROUP_UNRESOLVED"
            lane_ordinal: int | None = None
        elif best_distance > tolerance2:
            status = "OUTSIDE_RESOLVED_LANE_TOLERANCE"
            lane_ordinal = None
        elif margin is not None and margin <= required_margin:
            status = "LANE_ASSIGNMENT_MARGIN_AMBIGUOUS"
            lane_ordinal = None
        else:
            status = "ASSIGNED_TO_UNIQUE_ROW_LANE"
            lane_ordinal = best_lane
        assignment = {
            "ambiguity_margin": margin,
            "atom_ids": list(group.atom_ids),
            "bbox": group.bbox,
            "best_distance2": best_distance,
            "column_ordinal": lane_ordinal,
            "required_ambiguity_margin2": required_margin,
            "row_ordinal": group.row_ordinal,
            "status": status,
            "tolerance2": tolerance2,
            "value_group_id": group.group_id,
        }
        assignments.append(assignment)
        if lane_ordinal is None:
            uncertainties.append(
                {
                    "kind": status,
                    "value_group_id": group.group_id,
                }
            )

    collisions: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for assignment in assignments:
        lane = assignment["column_ordinal"]
        if lane is not None:
            collisions.setdefault((assignment["row_ordinal"], lane), []).append(assignment)
    for (row_ordinal, lane_ordinal), members in collisions.items():
        if len(members) < 2:
            continue
        for member in members:
            member["column_ordinal"] = None
            member["status"] = "ROW_LANE_COLLISION_UNRESOLVED"
        uncertainties.append(
            {
                "column_ordinal": lane_ordinal,
                "kind": "ROW_LANE_COLLISION_UNRESOLVED",
                "row_ordinal": row_ordinal,
                "value_group_ids": sorted(member["value_group_id"] for member in members),
            }
        )

    groups_by_row: dict[int, list[_ValueGroup]] = {}
    for group in groups:
        groups_by_row.setdefault(group.row_ordinal, []).append(group)
    assignments_by_row: dict[int, list[dict[str, Any]]] = {}
    for assignment in assignments:
        assignments_by_row.setdefault(assignment["row_ordinal"], []).append(assignment)

    row_results = []
    for ordinal, row in enumerate(rows):
        envelope = build_row_band_envelope_v2([atom.bbox for atom in row.atoms], extent_bbox=region)
        row_results.append(
            {
                **envelope,
                "atom_ids": sorted(atom.atom_id for atom in row.atoms),
                "label_atom_ids": sorted(
                    atom.atom_id for atom in row.atoms if atom.kind == "LABEL"
                ),
                "row_ordinal": ordinal,
                "value_group_ids": sorted(
                    group.group_id for group in groups_by_row.get(ordinal, [])
                ),
            }
        )

    missing_regions = []
    for row_ordinal, row in enumerate(rows):
        row_assignments = assignments_by_row.get(row_ordinal, [])
        visible = {
            item["column_ordinal"]
            for item in row_assignments
            if item["status"] == "ASSIGNED_TO_UNIQUE_ROW_LANE"
        }
        unresolved_on_row = any(
            item["status"] != "ASSIGNED_TO_UNIQUE_ROW_LANE" for item in row_assignments
        )
        if not visible or unresolved_on_row:
            continue
        for lane in lanes:
            if lane["column_ordinal"] in visible:
                continue
            missing_regions.append(
                _missing_region(
                    lane=lane,
                    row=row,
                    row_ordinal=row_ordinal,
                    rows=rows,
                    groups=groups,
                    assignments=assignments,
                    lanes=lanes,
                    alignment_mode=selected.mode,
                    typical_height=typical_height,
                    region=region,
                )
            )

    region_width = region[2] - region[0]
    relative_anchors = [
        _normalize_center2(lane["anchor2_median"], origin=region[0], dimension=region_width)
        for lane in lanes
    ]
    signature_payload: dict[str, Any] = {
        "alignment_mode": selected.mode,
        "lane_anchor_scope_ppm": relative_anchors,
        "lane_count": len(lanes),
        "lane_gap_scope_ppm": [right - left for left, right in pairwise(relative_anchors)],
        "normalization": "INTEGER_PPM_INSIDE_CALLER_BOUNDED_REGION",
    }
    signature_payload["lane_signature_id"] = (
        f"aatgv2:lane_signature:{canonical_json_sha256_v1(signature_payload)}"
    )
    topology_payload = {
        "alignment_mode": selected.mode,
        "assignments": [
            {
                "atom_ids": item["atom_ids"],
                "column_ordinal": item["column_ordinal"],
                "row_ordinal": item["row_ordinal"],
                "status": item["status"],
            }
            for item in assignments
        ],
        "expected_lane_count": expected_lane_count,
        "rows": [row["atom_ids"] for row in row_results],
    }
    invariance_id = f"aatgv2:invariance:{canonical_json_sha256_v1(topology_payload)}"
    status = "GEOMETRY_PROPOSAL_UNRESOLVED" if uncertainties else "GEOMETRY_PROPOSAL_RESOLVED"
    if missing_regions and not uncertainties:
        status = "GEOMETRY_PROPOSAL_WITH_MISSING_CELL_REGIONS_REQUIRES_PIXEL_AUTHORITY"
    return {
        "alignment": {
            "ambiguity_margin": ambiguity_margin,
            "equivalent_modes": equivalent_modes,
            "mode": selected.mode,
            "mode_costs": {item.mode: item.cost for item in alternatives},
            "tolerance2": tolerance2,
        },
        "assignments": assignments,
        "authority_boundary": ADAPTIVE_ACCOUNTING_TABLE_GEOMETRY_AUTHORITY_V2,
        "column_lanes": lanes,
        "coordinate_system": {
            "normalized_scale": _PPM,
            "normalized_unit": "INTEGER_PARTS_PER_MILLION",
            "raw_unit": "CALLER_PAGE_PIXEL_OR_CANONICAL_INTEGER_UNIT",
        },
        "expected_lane_count": expected_lane_count,
        "format_version": ADAPTIVE_ACCOUNTING_TABLE_GEOMETRY_FORMAT_VERSION_V2,
        "geometry_invariance_id": invariance_id,
        "missing_cell_region_proposals": missing_regions,
        "page_extent": page_extent,
        "page_lane_signature": signature_payload,
        "region_bbox": region,
        "region_bbox_page_ppm": normalize_bbox_to_ppm_v2(region, extent_bbox=page_extent),
        "row_bands": row_results,
        "status": status,
        "typical_text_height": typical_height,
        "uncertainties": sorted(
            uncertainties,
            key=lambda item: (
                item["kind"],
                str(item.get("atom_id", "")),
                str(item.get("value_group_id", "")),
            ),
        ),
    }


def _signature(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict:
        raise _error("page-lane signature must be one exact object")
    required = {
        "alignment_mode",
        "lane_anchor_scope_ppm",
        "lane_count",
        "lane_gap_scope_ppm",
        "lane_signature_id",
        "normalization",
    }
    if set(value) != required:
        raise _error("page-lane signature fields drifted")
    payload = {key: value[key] for key in required if key != "lane_signature_id"}
    expected_id = f"aatgv2:lane_signature:{canonical_json_sha256_v1(payload)}"
    if value["lane_signature_id"] != expected_id:
        raise _error("page-lane signature identity drifted")
    anchors = value["lane_anchor_scope_ppm"]
    gaps = value["lane_gap_scope_ppm"]
    if (
        value["alignment_mode"] not in _ALIGNMENTS
        or value["normalization"] != "INTEGER_PPM_INSIDE_CALLER_BOUNDED_REGION"
        or type(value["lane_count"]) is not int
        or type(anchors) is not list
        or len(anchors) != value["lane_count"]
        or any(type(item) is not int or not 0 <= item <= _PPM for item in anchors)
        or anchors != sorted(set(anchors))
        or type(gaps) is not list
        or gaps != [right - left for left, right in pairwise(anchors)]
    ):
        raise _error("page-lane signature geometry drifted")
    return dict(value)


def compare_page_lane_signatures_v2(
    previous_signature: Mapping[str, Any], following_signature: Mapping[str, Any]
) -> dict[str, Any]:
    """Measure two signatures without asserting a cross-page continuation."""

    previous = _signature(previous_signature)
    following = _signature(following_signature)
    count_match = previous["lane_count"] == following["lane_count"]
    mode_match = previous["alignment_mode"] == following["alignment_mode"]
    deltas = (
        [
            abs(right - left)
            for left, right in zip(
                previous["lane_anchor_scope_ppm"],
                following["lane_anchor_scope_ppm"],
                strict=True,
            )
        ]
        if count_match
        else []
    )
    gaps = previous["lane_gap_scope_ppm"] + following["lane_gap_scope_ppm"]
    tolerance = max(8_000, (_median(gaps) // 8 if gaps else 20_000))
    maximum_delta = max(deltas) if deltas else None
    compatible = bool(
        count_match
        and mode_match
        and deltas
        and maximum_delta is not None
        and maximum_delta <= tolerance
    )
    payload: dict[str, Any] = {
        "authority": "GEOMETRY_COMPATIBILITY_CANDIDATE_ONLY_NO_CONTINUATION_OR_MERGE_CLAIM",
        "following_lane_signature_id": following["lane_signature_id"],
        "lane_count_match": count_match,
        "lane_delta_scope_ppm": deltas,
        "maximum_lane_delta_scope_ppm": maximum_delta,
        "mode_match": mode_match,
        "previous_lane_signature_id": previous["lane_signature_id"],
        "status": (
            "COMPATIBLE_PAGE_LANE_SIGNATURE_CANDIDATE"
            if compatible
            else "UNRESOLVED_PAGE_LANE_SIGNATURE"
        ),
        "tolerance_margin_ppm": (tolerance - maximum_delta if maximum_delta is not None else None),
        "tolerance_ppm": tolerance,
    }
    payload["comparison_id"] = f"aatgv2:page_lane_comparison:{canonical_json_sha256_v1(payload)}"
    return payload
