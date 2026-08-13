"""Fail-closed, source-bound Local Accounting Graph acceptance core.

This module is an add-only overlay after Reader V3 and the pre-structural
candidate graph.  It accepts a small source-visible family topology only when
exactly one region is a complete match.  It deliberately does not discover
pages, mutate reader evidence, map schema identities, or infer hidden units.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    SourceStructureContractError,
    _normalized_financial_token_v1,
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.source_structure.contracts_v2 import validate_source_evidence_projection_v2

__all__ = [
    "LOCAL_ACCOUNTING_GRAPH_CLAIM_BOUNDARY_V1",
    "LOCAL_ACCOUNTING_GRAPH_FORMAT_VERSION_V1",
    "LOCAL_ACCOUNTING_GRAPH_SAFETY_V1",
    "LOCAL_ACCOUNTING_OBSERVATION_FORMAT_VERSION_V1",
    "LOAN_MATURITY_BUCKETS_SPEC_V1",
    "LOAN_QUALITY_CLASSIFICATION_SPEC_V1",
    "AcceptedEdgeKindV1",
    "AcceptedNodeKindV1",
    "AxisLayoutSpecV1",
    "FamilySpecV1",
    "GraphStatusV1",
    "LocalAccountingGraphContractError",
    "RowRoleSpecV1",
    "ValueStateV1",
    "infer_local_accounting_graph_v1",
    "local_accounting_family_spec_payload_v1",
    "local_accounting_family_spec_sha256_v1",
    "parse_local_accounting_period_v1",
    "parse_local_accounting_unit_v1",
    "validate_local_accounting_graph_v1",
    "validate_local_accounting_graph_replay_v1",
]


class LocalAccountingGraphContractError(ValueError):
    """The input or result crossed the closed LAG v1 contract."""


class GraphStatusV1(StrEnum):
    CORE_ACCEPTED = "CORE_ACCEPTED"
    EXPLICIT_UNRESOLVED = "EXPLICIT_UNRESOLVED"


class AcceptedNodeKindV1(StrEnum):
    TABLE = "TABLE"
    LOGICAL_ROW = "LOGICAL_ROW"
    VALUE_POSITION = "VALUE_POSITION"
    AXIS = "AXIS"
    ACCOUNTING_ROLE = "ACCOUNTING_ROLE"
    CONTEXT = "CONTEXT"
    EVIDENCE = "EVIDENCE"
    UNRESOLVED_REGION = "UNRESOLVED_REGION"


class AcceptedEdgeKindV1(StrEnum):
    CONTAINS = "CONTAINS"
    OWNS = "OWNS"
    PARENT_OF = "PARENT_OF"
    NEXT_SIBLING = "NEXT_SIBLING"
    ALIGNED_TO_AXIS = "ALIGNED_TO_AXIS"
    SCOPED_BY = "SCOPED_BY"
    TOTAL_OF = "TOTAL_OF"
    SUPPORTED_BY = "SUPPORTED_BY"


class ValueStateV1(StrEnum):
    OBSERVED_VALUE = "OBSERVED_VALUE"
    OBSERVED_ZERO = "OBSERVED_ZERO"
    DASH = "DASH"
    BLANK = "BLANK"
    NOT_OBSERVED = "NOT_OBSERVED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class RowRoleSpecV1:
    """One source-visible row role and its presentation aliases."""

    role: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class AxisLayoutSpecV1:
    """Required visible axis layout; v1 intentionally supports no inheritance."""

    comparative_monetary_period_count: int = 2


@dataclass(frozen=True)
class FamilySpecV1:
    """Declarative configuration for one recurring accounting family."""

    family_id: str
    owner_aliases: tuple[str, ...]
    branch_aliases: tuple[str, ...]
    ordered_children: tuple[RowRoleSpecV1, ...]
    optional_children: tuple[RowRoleSpecV1, ...]
    total_aliases: tuple[str, ...]
    closure_child_roles: tuple[str, ...]
    axis_layout: AxisLayoutSpecV1 = AxisLayoutSpecV1()


LOAN_QUALITY_CLASSIFICATION_SPEC_V1 = FamilySpecV1(
    family_id="LOAN_QUALITY_CLASSIFICATION",
    owner_aliases=("cho vay khach hang", "du no cho vay khach hang"),
    branch_aliases=(
        "chat luong no cho vay",
        "phan loai no cho vay",
        "phan tich chat luong no",
        "phan tich chat luong no cho vay",
    ),
    ordered_children=(
        RowRoleSpecV1("STANDARD", ("no du tieu chuan",)),
        RowRoleSpecV1("SPECIAL_MENTION", ("no can chu y",)),
        RowRoleSpecV1("SUBSTANDARD", ("no duoi tieu chuan",)),
        RowRoleSpecV1("DOUBTFUL", ("no nghi ngo",)),
        RowRoleSpecV1("LOSS", ("no co kha nang mat von",)),
    ),
    optional_children=(RowRoleSpecV1("MARGIN_OR_ADVANCE", ("cho vay ky quy", "ung truoc")),),
    total_aliases=("tong cong", "tong"),
    closure_child_roles=(
        "STANDARD",
        "SPECIAL_MENTION",
        "SUBSTANDARD",
        "DOUBTFUL",
        "LOSS",
    ),
)


LOAN_MATURITY_BUCKETS_SPEC_V1 = FamilySpecV1(
    family_id="LOAN_MATURITY_BUCKETS",
    owner_aliases=("cho vay khach hang", "du no cho vay khach hang"),
    branch_aliases=(
        "phan tich theo thoi han",
        "phan tich theo ky han",
        "phan tich du no theo thoi gian",
        "phan tich du no theo thoi han",
        "thoi han cho vay",
        "ky han cho vay",
    ),
    ordered_children=(
        RowRoleSpecV1("SHORT_TERM", ("ngan han", "cho vay ngan han")),
        RowRoleSpecV1("MEDIUM_TERM", ("trung han", "cho vay trung han")),
        RowRoleSpecV1("LONG_TERM", ("dai han", "cho vay dai han")),
    ),
    optional_children=(),
    total_aliases=("tong cong", "tong"),
    closure_child_roles=("SHORT_TERM", "MEDIUM_TERM", "LONG_TERM"),
)


def _family_spec_payload(spec: FamilySpecV1) -> dict[str, Any]:
    return {
        "format_version": "LOCAL_ACCOUNTING_FAMILY_SPEC_V1",
        "family_id": spec.family_id,
        "owner_aliases": list(spec.owner_aliases),
        "branch_aliases": list(spec.branch_aliases),
        "ordered_children": [
            {"role": item.role, "aliases": list(item.aliases)} for item in spec.ordered_children
        ],
        "optional_children": [
            {"role": item.role, "aliases": list(item.aliases)} for item in spec.optional_children
        ],
        "total_aliases": list(spec.total_aliases),
        "closure_child_roles": list(spec.closure_child_roles),
        "axis_layout": {
            "comparative_monetary_period_count": (
                spec.axis_layout.comparative_monetary_period_count
            )
        },
    }


def _family_spec_sha256(spec: FamilySpecV1) -> str:
    return canonical_json_sha256_v1(_family_spec_payload(spec))


def local_accounting_family_spec_payload_v1(spec: FamilySpecV1) -> dict[str, Any]:
    """Return the canonical payload of one structurally valid family config."""

    _validate_family_spec_structure(spec)
    return canonical_clone_v1(_family_spec_payload(spec))


def local_accounting_family_spec_sha256_v1(spec: FamilySpecV1) -> str:
    """Return the identity of one structurally valid family config."""

    _validate_family_spec_structure(spec)
    return _family_spec_sha256(spec)


_FROZEN_FAMILY_SPEC_SHA256_BY_ID = {
    spec.family_id: _family_spec_sha256(spec)
    for spec in (
        LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
        LOAN_MATURITY_BUCKETS_SPEC_V1,
    )
}
_FROZEN_FAMILY_SPEC_BY_ID = {
    spec.family_id: spec
    for spec in (
        LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
        LOAN_MATURITY_BUCKETS_SPEC_V1,
    )
}


LOCAL_ACCOUNTING_OBSERVATION_FORMAT_VERSION_V1 = "BANK_CORPUS_LOCAL_ACCOUNTING_OBSERVATION_V1"
LOCAL_ACCOUNTING_GRAPH_FORMAT_VERSION_V1 = "BANK_CORPUS_LOCAL_ACCOUNTING_GRAPH_V1"
LOCAL_ACCOUNTING_GRAPH_CLAIM_BOUNDARY_V1 = (
    "SOURCE_VISIBLE_LOCAL_ACCOUNTING_STRUCTURE_ONLY_WITHIN_SUPPLIED_OBSERVATION_"
    "REGIONS_NO_PAGE_OR_SOURCE_EXHAUSTIVENESS_NO_READER_MUTATION_NO_INHERITED_"
    "CONTEXT_NO_SCHEMA_OR_ROLE_A_ROUTING"
)
LOCAL_ACCOUNTING_GRAPH_SAFETY_V1: dict[str, bool] = {
    "downstream_overlay_only": True,
    "reader_v3_mutated": False,
    "local_visible_unit_required": True,
    "unit_inheritance_used": False,
    "unique_complete_match_required": True,
    "supplied_observation_regions_only": True,
    "candidate_exhaustiveness_claimed": False,
    "page_exhaustiveness_claimed": False,
    "source_exhaustiveness_claimed": False,
    "arithmetic_used_for_selection": False,
    "arithmetic_may_veto": True,
    "internal_additive_closure_only": True,
    "same_population_claimed": False,
    "values_invented": False,
    "blank_coerced_to_zero": False,
    "bank_identity_used_for_routing": False,
    "filename_identity_used_for_routing": False,
    "page_number_used_for_routing": False,
    "note_number_used_for_routing": False,
    "role_a_used_for_routing": False,
    "schema_used_for_routing": False,
}

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_PAGE_ID_RE = re.compile(r"^ssv2:page:[0-9a-f]{64}$")
_ATOM_ID_RE = re.compile(r"^ssv1:[a-z][a-z0-9_]{0,39}:[0-9a-f]{64}$")
_NODE_ID_RE = re.compile(r"^lagv1:node:[0-9a-f]{64}$")
_EDGE_ID_RE = re.compile(r"^lagv1:edge:[0-9a-f]{64}$")
_GRAPH_ID_RE = re.compile(r"^lagv1:graph:[0-9a-f]{64}$")
_ROLE_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
_UNRESOLVED_REASON_CODES_V1 = {
    "AMBIGUOUS_LOCAL_VISIBLE_UNIT",
    "ARITHMETIC_CLOSURE_VETO",
    "BRANCH_NOT_RESOLVED",
    "COMPARATIVE_MONETARY_AXIS_LAYOUT_NOT_RESOLVED",
    "DUPLICATE_ROW_ROLE",
    "MISSING_LOCAL_VISIBLE_UNIT",
    "MULTIPLE_COMPLETE_MATCHES",
    "MULTIPLE_LOCAL_VISIBLE_UNITS",
    "NO_COMPLETE_MATCH",
    "ORDERED_SIBLING_SET_NOT_RESOLVED",
    "OWNER_NOT_RESOLVED",
    "TOTAL_NOT_AFTER_CHILDREN",
    "TOTAL_NOT_RESOLVED",
    "UNCLASSIFIED_OR_AMBIGUOUS_ROW",
    "VALUE_POSITION_AXIS_COVERAGE_NOT_RESOLVED",
    "VALUE_POSITION_SEMANTICS_UNRESOLVED",
}
_PERIOD_DATE_RE = re.compile(r"(?<!\d)([0-3]?\d)[/.-]([01]?\d)[/.-]((?:19|20)\d{2})(?!\d)")
_PERIOD_YEAR_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")

_OBSERVATION_FIELDS = {
    "format_version",
    "source_local_page_id",
    "source_projection_sha256",
    "regions",
}
_REGION_FIELDS = {
    "canonical_bbox_mpt",
    "owner_label",
    "branch_label",
    "rows",
    "axes",
    "local_unit_labels",
    "adjacent_row_boundaries_verified",
}
_SPAN_FIELDS = {"text", "canonical_bbox_mpt", "source_atom_ids"}
_ROW_FIELDS = {"label", "value_positions"}
_VALUE_FIELDS = {
    "axis_index",
    "state",
    "raw_text",
    "canonical_bbox_mpt",
    "source_atom_ids",
}
_AXIS_FIELDS = {"header"}
_GRAPH_FIELDS = {
    "format_version",
    "claim_boundary",
    "status",
    "family_id",
    "family_spec_sha256",
    "source_local_page_id",
    "source_projection_sha256",
    "source_observation_sha256",
    "nodes",
    "edges",
    "arithmetic_check",
    "unresolved_reasons",
    "accepted_counts",
    "canonicalization_eligible",
    "export_eligible",
    "safety",
    "graph_identity",
}
_NODE_FIELDS = {
    "node_id",
    "kind",
    "status",
    "source_ref",
    "attributes",
    "unresolved_reasons",
}
_SOURCE_REF_FIELDS = {
    "source_local_page_id",
    "source_projection_sha256",
    "canonical_bbox_mpt",
    "source_atom_ids",
}
_EDGE_FIELDS = {
    "edge_id",
    "kind",
    "from_node_id",
    "to_node_id",
    "evidence_node_ids",
}
_ACCEPTED_COUNTS_FIELDS = {
    "TABLE",
    "LOGICAL_ROW",
    "VALUE_POSITION",
    "AXIS",
    "HIERARCHY",
}
_NONDETERMINATE_VALUE_STATES = {
    ValueStateV1.BLANK.value,
    ValueStateV1.NOT_OBSERVED.value,
    ValueStateV1.AMBIGUOUS.value,
    ValueStateV1.UNRESOLVED.value,
}
_HIERARCHY_EDGES = {
    AcceptedEdgeKindV1.OWNS.value,
    AcceptedEdgeKindV1.PARENT_OF.value,
    AcceptedEdgeKindV1.NEXT_SIBLING.value,
    AcceptedEdgeKindV1.TOTAL_OF.value,
}


def _error(message: str) -> LocalAccountingGraphContractError:
    return LocalAccountingGraphContractError(message)


def _exact_dict(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise _error(f"{label} field set drifted")
    return value


def _bbox(value: Any, label: str) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or value[0] >= value[2]
        or value[1] >= value[3]
    ):
        raise _error(f"{label} must be one positive canonical mpt box")
    return value


def _atom_ids(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    if (
        type(value) is not list
        or (not allow_empty and not value)
        or any(type(item) is not str or _ATOM_ID_RE.fullmatch(item) is None for item in value)
        or value != sorted(set(value))
    ):
        qualifier = "possibly empty" if allow_empty else "non-empty"
        raise _error(f"{label} must be a sorted unique {qualifier} source-atom list")
    return value


def _span_atom_ids(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    if (
        type(value) is not list
        or (not allow_empty and not value)
        or any(type(item) is not str or _ATOM_ID_RE.fullmatch(item) is None for item in value)
        or len(value) != len(set(value))
    ):
        qualifier = "possibly empty" if allow_empty else "non-empty"
        raise _error(f"{label} must be a unique {qualifier} source-atom sequence")
    return value


def _contains(outer: Sequence[int], inner: Sequence[int]) -> bool:
    return (
        outer[0] <= inner[0]
        and outer[1] <= inner[1]
        and inner[2] <= outer[2]
        and inner[3] <= outer[3]
    )


def _union_box(boxes: Sequence[Sequence[int]]) -> list[int]:
    return [
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    ]


def _display_bbox(
    canonical_bbox: Sequence[int], coordinate_authority: Mapping[str, Any]
) -> list[int]:
    rotation = coordinate_authority.get("pdf_rotation_degrees")
    dimensions = coordinate_authority.get("unrotated_dimensions_mpt")
    if dimensions is None:
        cropbox = coordinate_authority.get("canonical_cropbox_bounds_mpt")
        dimensions = cropbox[2:] if type(cropbox) is list and len(cropbox) == 4 else None
    if (
        type(rotation) is not int
        or rotation not in {0, 90, 180, 270}
        or type(dimensions) is not list
        or len(dimensions) != 2
        or any(type(item) is not int or item <= 0 for item in dimensions)
    ):
        raise _error("source projection lacks usable rotation/display geometry authority")
    width, height = dimensions

    def transform(x: int, y: int) -> tuple[int, int]:
        if rotation == 0:
            return x, y
        if rotation == 90:
            return height - y, x
        if rotation == 180:
            return width - x, height - y
        return y, width - x

    points = [
        transform(canonical_bbox[0], canonical_bbox[1]),
        transform(canonical_bbox[2], canonical_bbox[1]),
        transform(canonical_bbox[2], canonical_bbox[3]),
        transform(canonical_bbox[0], canonical_bbox[3]),
    ]
    return [
        min(point[0] for point in points),
        min(point[1] for point in points),
        max(point[0] for point in points),
        max(point[1] for point in points),
    ]


def _center(box: Sequence[int], axis: int) -> int:
    return box[axis] + box[axis + 2]


def _validate_value_geometry(
    region: Mapping[str, Any],
    *,
    coordinate_authority: Mapping[str, Any],
    label: str,
) -> None:
    display_axes = [
        _display_bbox(axis["header"]["canonical_bbox_mpt"], coordinate_authority)
        for axis in region["axes"]
    ]

    display_row_boxes: list[list[int]] = []
    row_anchor_centers: list[int] = []
    for row_index, row in enumerate(region["rows"]):
        if row["label"] is not None:
            anchor = _display_bbox(row["label"]["canonical_bbox_mpt"], coordinate_authority)
        else:
            observed_boxes = [
                _display_bbox(position["canonical_bbox_mpt"], coordinate_authority)
                for position in row["value_positions"]
                if position["source_atom_ids"]
            ]
            if not observed_boxes:
                raise _error(f"{label} unlabeled row {row_index} lacks visible geometry")
            anchor = _union_box(observed_boxes)
        display_row_boxes.append(anchor)
        row_anchor_centers.append(_center(anchor, 1))
    if row_anchor_centers != sorted(row_anchor_centers) or len(set(row_anchor_centers)) != len(
        row_anchor_centers
    ):
        raise _error(f"{label} visible row anchors are not ordered and distinct")

    lane_centers: list[list[int]] = [[] for _ in display_axes]
    for row_index, row in enumerate(region["rows"]):
        previous_center = row_anchor_centers[row_index - 1] if row_index else None
        current_center = row_anchor_centers[row_index]
        next_center = (
            row_anchor_centers[row_index + 1] if row_index + 1 < len(row_anchor_centers) else None
        )
        upper_twice = (
            (previous_center + current_center) // 2
            if previous_center is not None
            else current_center - (next_center - current_center) // 2
        )
        lower_twice = (
            (current_center + next_center) // 2
            if next_center is not None
            else current_center + (current_center - previous_center) // 2
        )
        for position in row["value_positions"]:
            if not position["source_atom_ids"]:
                continue
            display_box = _display_bbox(position["canonical_bbox_mpt"], coordinate_authority)
            value_center_twice = _center(display_box, 1)
            if value_center_twice <= upper_twice or value_center_twice >= lower_twice:
                raise _error(
                    f"{label} row {row_index} contains a value outside its visible row band"
                )
            axis_index = position["axis_index"]
            value_x_twice = _center(display_box, 0)
            lane_centers[axis_index].append(value_x_twice)
    if any(not centers for centers in lane_centers):
        raise _error(f"{label} lacks observed values for a numeric lane")
    lane_ranges = [[min(centers), max(centers)] for centers in lane_centers]
    if any(left[1] >= right[0] for left, right in zip(lane_ranges, lane_ranges[1:], strict=False)):
        raise _error(f"{label} numeric value lanes are inconsistent or overlapping")
    lane_representatives = [(item[0] + item[1]) // 2 for item in lane_ranges]
    adjacent_separations = [
        right - left
        for left, right in zip(lane_representatives, lane_representatives[1:], strict=False)
    ]
    maximum_within_lane_spread = max(right - left for left, right in lane_ranges)
    if (
        not adjacent_separations
        or min(adjacent_separations) <= 0
        or maximum_within_lane_spread * 2 >= min(adjacent_separations)
    ):
        raise _error(f"{label} numeric value lanes are inconsistent or overlapping")
    lane_partitions = []
    for axis_index, representative in enumerate(lane_representatives):
        left_boundary = (
            (lane_representatives[axis_index - 1] + representative) // 2
            if axis_index
            else representative - (lane_representatives[axis_index + 1] - representative) // 2
        )
        right_boundary = (
            (representative + lane_representatives[axis_index + 1]) // 2
            if axis_index + 1 < len(lane_representatives)
            else representative + (representative - lane_representatives[axis_index - 1]) // 2
        )
        lane_partitions.append([left_boundary, right_boundary])
    for axis_index, header_box in enumerate(display_axes):
        partition = lane_partitions[axis_index]
        if max(header_box[0] * 2, partition[0]) >= min(header_box[2] * 2, partition[1]):
            raise _error(f"{label} axis header does not corroborate its numeric value lane")


def _normalize_text(value: str) -> str:
    value = value.casefold().replace("đ", "d")
    value = "".join(
        character
        for character in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(character)
    )
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())


def _normalized_aliases(aliases: tuple[str, ...], label: str) -> tuple[str, ...]:
    if type(aliases) is not tuple or any(type(alias) is not str for alias in aliases):
        raise _error(f"{label} aliases must be an immutable tuple of strings")
    normalized = tuple(_normalize_text(alias) for alias in aliases)
    if (
        not normalized
        or any(not alias for alias in normalized)
        or len(set(normalized)) != len(normalized)
    ):
        raise _error(f"{label} aliases must be non-empty and unique after normalization")
    return normalized


def _validate_family_spec_structure(spec: FamilySpecV1) -> None:
    if (
        type(spec) is not FamilySpecV1
        or type(spec.family_id) is not str
        or _ROLE_RE.fullmatch(spec.family_id) is None
    ):
        raise _error("family spec identity drifted")
    if (
        type(spec.owner_aliases) is not tuple
        or type(spec.branch_aliases) is not tuple
        or type(spec.ordered_children) is not tuple
        or type(spec.optional_children) is not tuple
        or type(spec.total_aliases) is not tuple
        or type(spec.closure_child_roles) is not tuple
    ):
        raise _error("family spec sequence fields must be immutable tuples")
    _normalized_aliases(spec.owner_aliases, "owner")
    _normalized_aliases(spec.branch_aliases, "branch")
    _normalized_aliases(spec.total_aliases, "total")
    if (
        type(spec.axis_layout) is not AxisLayoutSpecV1
        or type(spec.axis_layout.comparative_monetary_period_count) is not int
        or spec.axis_layout.comparative_monetary_period_count < 2
    ):
        raise _error("family axis layout drifted")
    row_specs = spec.ordered_children + spec.optional_children
    roles = []
    for row_spec in row_specs:
        if (
            type(row_spec) is not RowRoleSpecV1
            or type(row_spec.role) is not str
            or _ROLE_RE.fullmatch(row_spec.role) is None
        ):
            raise _error("family row role drifted")
        if type(row_spec.aliases) is not tuple:
            raise _error("family row aliases must be immutable tuples")
        _normalized_aliases(row_spec.aliases, f"row role {row_spec.role}")
        roles.append(row_spec.role)
    if not spec.ordered_children or len(roles) != len(set(roles)):
        raise _error("family row roles must be non-empty and unique")
    if (
        type(spec.closure_child_roles) is not tuple
        or not spec.closure_child_roles
        or len(set(spec.closure_child_roles)) != len(spec.closure_child_roles)
        or not set(spec.closure_child_roles).issubset({item.role for item in spec.ordered_children})
    ):
        raise _error("closure child roles must be unique required row roles")


def _validate_family_spec(spec: FamilySpecV1) -> None:
    _validate_family_spec_structure(spec)
    if _FROZEN_FAMILY_SPEC_SHA256_BY_ID.get(spec.family_id) != _family_spec_sha256(spec):
        raise _error("family spec is not an exact frozen LAG v1 configuration")


def _validate_span(
    value: Any,
    label: str,
    *,
    source_atoms: Mapping[str, Mapping[str, Any]],
    source_ordinals: Mapping[str, int],
    claimed_atom_ids: set[str],
    allow_empty_atoms: bool = False,
) -> dict[str, Any]:
    span = _exact_dict(value, _SPAN_FIELDS, label)
    if type(span["text"]) is not str or not span["text"].strip():
        raise _error(f"{label} text must be source-visible non-empty text")
    bbox = _bbox(span["canonical_bbox_mpt"], f"{label} bbox")
    atom_ids = _span_atom_ids(
        span["source_atom_ids"], f"{label} atom ids", allow_empty=allow_empty_atoms
    )
    if not atom_ids:
        return span
    if any(atom_id not in source_atoms for atom_id in atom_ids):
        raise _error(f"{label} cites an atom outside the exact source projection")
    if atom_ids != sorted(atom_ids, key=source_ordinals.__getitem__):
        raise _error(f"{label} atom sequence disagrees with authenticated source order")
    atoms = [source_atoms[atom_id] for atom_id in atom_ids]
    atom_kinds = {atom["kind"] for atom in atoms}
    if len(atom_kinds) != 1:
        raise _error(f"{label} cannot mix line and word authority")
    if any(
        atom.get("authority") != "AUTHENTICATED_PRIMARY"
        or atom.get("kind") not in {"LINE", "WORD"}
        or type(atom.get("raw_text")) is not str
        or not atom["raw_text"]
        or atom.get("canonical_bbox_mpt") is None
        for atom in atoms
    ):
        raise _error(f"{label} cites non-primary or non-visible source evidence")
    locator_kinds = {atom.get("upstream_locator", {}).get("kind") for atom in atoms}
    if len(atoms) > 1:
        locators = [atom.get("upstream_locator", {}) for atom in atoms]
        if locator_kinds == {"OCR_WORD_INDEX"}:
            line_indexes = {locator["line_index"] for locator in locators}
            word_indexes = [locator["word_index"] for locator in locators]
            contiguous = len(line_indexes) == 1 and word_indexes == list(
                range(word_indexes[0], word_indexes[0] + len(word_indexes))
            )
        elif locator_kinds == {"NATIVE_WORD_INDEX"}:
            line_identities = {
                (locator["block_number"], locator["line_number"]) for locator in locators
            }
            word_numbers = [locator["word_number"] for locator in locators]
            contiguous = len(line_identities) == 1 and word_numbers == list(
                range(word_numbers[0], word_numbers[0] + len(word_numbers))
            )
        elif locator_kinds == {None}:
            ordinals = [source_ordinals[atom_id] for atom_id in atom_ids]
            contiguous = ordinals == list(range(ordinals[0], ordinals[0] + len(ordinals)))
        else:
            contiguous = False
        if not contiguous:
            raise _error(f"{label} cherry-picks noncontiguous source atoms")
    if atom_kinds == {"LINE"} and len(atoms) != 1:
        raise _error(f"{label} cannot concatenate multiple authenticated lines")
    if locator_kinds == {"OCR_WORD_INDEX"}:
        expected_text = "".join(atom["raw_text"] for atom in atoms)
    elif locator_kinds in ({"NATIVE_WORD_INDEX"}, {None}):
        expected_text = " ".join(atom["raw_text"] for atom in atoms)
    else:
        expected_text = atoms[0]["raw_text"]
    if span["text"] != expected_text:
        raise _error(f"{label} text disagrees with cited source atoms")
    if bbox != _union_box([atom["canonical_bbox_mpt"] for atom in atoms]):
        raise _error(f"{label} bbox disagrees with cited source atoms")
    if claimed_atom_ids.intersection(atom_ids):
        raise _error(f"{label} reuses source atoms assigned to another observed role")
    claimed_atom_ids.update(atom_ids)
    return span


def _parse_decimal(raw_text: str) -> Decimal | None:
    try:
        normalized = _normalized_financial_token_v1(raw_text)
    except SourceStructureContractError:
        return None
    return Decimal(normalized)


def _validate_value_position(
    value: Any,
    label: str,
    *,
    axis_count: int,
    source_atoms: Mapping[str, Mapping[str, Any]],
    source_ordinals: Mapping[str, int],
    claimed_atom_ids: set[str],
) -> dict[str, Any]:
    item = _exact_dict(value, _VALUE_FIELDS, label)
    axis_index = item["axis_index"]
    if type(axis_index) is not int or not 0 <= axis_index < axis_count:
        raise _error(f"{label} axis index is outside the visible axes")
    try:
        state = ValueStateV1(item["state"])
    except (TypeError, ValueError) as error:
        raise _error(f"{label} value state drifted") from error
    _bbox(item["canonical_bbox_mpt"], f"{label} bbox")
    atoms = _span_atom_ids(item["source_atom_ids"], f"{label} atom ids", allow_empty=True)
    raw_text = item["raw_text"]
    if raw_text is not None and (type(raw_text) is not str or not raw_text.strip()):
        raise _error(f"{label} raw text must be null or non-empty source text")
    if atoms:
        _validate_span(
            {
                "text": raw_text,
                "canonical_bbox_mpt": item["canonical_bbox_mpt"],
                "source_atom_ids": atoms,
            },
            label,
            source_atoms=source_atoms,
            source_ordinals=source_ordinals,
            claimed_atom_ids=claimed_atom_ids,
        )
    parsed = _parse_decimal(raw_text) if type(raw_text) is str else None
    if state is ValueStateV1.OBSERVED_ZERO and (not atoms or parsed != 0):
        raise _error(f"{label} OBSERVED_ZERO must retain an observed numeric zero")
    if state is ValueStateV1.OBSERVED_VALUE and (not atoms or parsed is None or parsed == 0):
        raise _error(f"{label} OBSERVED_VALUE must retain an observed non-zero number")
    if state is ValueStateV1.DASH and (not atoms or raw_text.strip() not in {"-", "–", "—"}):
        raise _error(f"{label} DASH must retain an observed dash")
    if state in {ValueStateV1.BLANK, ValueStateV1.NOT_OBSERVED} and (raw_text is not None or atoms):
        raise _error(f"{label} {state.value} cannot carry an observed token")
    if state is ValueStateV1.NOT_APPLICABLE and (
        not atoms or _normalize_text(raw_text or "") not in {"n a", "khong ap dung"}
    ):
        raise _error(f"{label} NOT_APPLICABLE must retain an explicit visible marker")
    return item


def _validate_observation(
    observation: Any,
    *,
    source_projection: Mapping[str, Any],
) -> dict[str, Any]:
    value = _exact_dict(observation, _OBSERVATION_FIELDS, "observation")
    if value["format_version"] != LOCAL_ACCOUNTING_OBSERVATION_FORMAT_VERSION_V1:
        raise _error("observation format version drifted")
    if (
        type(value["source_local_page_id"]) is not str
        or _PAGE_ID_RE.fullmatch(value["source_local_page_id"]) is None
    ):
        raise _error("observation source-local page identity drifted")
    expected_projection_sha256 = canonical_json_sha256_v1(source_projection)
    if value["source_projection_sha256"] != expected_projection_sha256:
        raise _error("observation does not bind the exact validated source projection")
    if value["source_local_page_id"] != source_projection["source_local_page_id"]:
        raise _error("observation source-local page binding drifted")
    source_atom_sequence = source_projection["neutral_page_v1"]["atoms"]
    source_atoms = {atom["source_local_id"]: atom for atom in source_atom_sequence}
    if len(source_atoms) != len(source_atom_sequence):
        raise _error("validated source projection repeats an atom identity")
    source_ordinals = {
        atom["source_local_id"]: ordinal for ordinal, atom in enumerate(source_atom_sequence)
    }
    if type(value["regions"]) is not list or not value["regions"]:
        raise _error("observation must contain at least one bounded region")
    for region_index, region_value in enumerate(value["regions"]):
        claimed_atom_ids: set[str] = set()
        region = _exact_dict(region_value, _REGION_FIELDS, f"region {region_index}")
        region_box = _bbox(region["canonical_bbox_mpt"], f"region {region_index} bbox")
        if type(region["adjacent_row_boundaries_verified"]) is not bool:
            raise _error(f"region {region_index} row-boundary evidence drifted")
        component_boxes: list[list[int]] = []
        for field in ("owner_label", "branch_label"):
            span = _validate_span(
                region[field],
                f"region {region_index} {field}",
                source_atoms=source_atoms,
                source_ordinals=source_ordinals,
                claimed_atom_ids=claimed_atom_ids,
            )
            component_boxes.append(span["canonical_bbox_mpt"])
        if type(region["axes"]) is not list or not region["axes"]:
            raise _error(f"region {region_index} axes must be a non-empty list")
        for axis_index, axis_value in enumerate(region["axes"]):
            axis = _exact_dict(axis_value, _AXIS_FIELDS, f"region {region_index} axis {axis_index}")
            span = _validate_span(
                axis["header"],
                f"region {region_index} axis {axis_index} header",
                source_atoms=source_atoms,
                source_ordinals=source_ordinals,
                claimed_atom_ids=claimed_atom_ids,
            )
            component_boxes.append(span["canonical_bbox_mpt"])
        if type(region["local_unit_labels"]) is not list:
            raise _error(f"region {region_index} local unit labels must be a list")
        for unit_index, unit_value in enumerate(region["local_unit_labels"]):
            span = _validate_span(
                unit_value,
                f"region {region_index} local unit {unit_index}",
                source_atoms=source_atoms,
                source_ordinals=source_ordinals,
                claimed_atom_ids=claimed_atom_ids,
            )
            component_boxes.append(span["canonical_bbox_mpt"])
        if type(region["rows"]) is not list or not region["rows"]:
            raise _error(f"region {region_index} rows must be a non-empty list")
        for row_index, row_value in enumerate(region["rows"]):
            row = _exact_dict(row_value, _ROW_FIELDS, f"region {region_index} row {row_index}")
            if row["label"] is not None:
                label_span = _validate_span(
                    row["label"],
                    f"region {region_index} row {row_index} label",
                    source_atoms=source_atoms,
                    source_ordinals=source_ordinals,
                    claimed_atom_ids=claimed_atom_ids,
                )
                component_boxes.append(label_span["canonical_bbox_mpt"])
            if type(row["value_positions"]) is not list:
                raise _error(f"region {region_index} row {row_index} values must be a list")
            seen_axes: set[int] = set()
            for value_index, position_value in enumerate(row["value_positions"]):
                position = _validate_value_position(
                    position_value,
                    f"region {region_index} row {row_index} value {value_index}",
                    axis_count=len(region["axes"]),
                    source_atoms=source_atoms,
                    source_ordinals=source_ordinals,
                    claimed_atom_ids=claimed_atom_ids,
                )
                if position["axis_index"] in seen_axes:
                    raise _error(f"region {region_index} row {row_index} repeats an axis")
                seen_axes.add(position["axis_index"])
                component_boxes.append(position["canonical_bbox_mpt"])
        if region_box != _union_box(component_boxes):
            raise _error(f"region {region_index} bbox must be the exact union of cited evidence")
        axis_headers = [axis["header"] for axis in region["axes"]]
        axis_ordinals = [
            min(source_ordinals[atom_id] for atom_id in header["source_atom_ids"])
            for header in axis_headers
        ]
        if axis_ordinals != sorted(axis_ordinals):
            raise _error(f"region {region_index} axis order is not source-visible")
        labeled_row_ordinals = [
            min(source_ordinals[atom_id] for atom_id in row["label"]["source_atom_ids"])
            for row in region["rows"]
            if row["label"] is not None
        ]
        if labeled_row_ordinals != sorted(labeled_row_ordinals):
            raise _error(f"region {region_index} row-label source order drifted")
        for row_index, row in enumerate(region["rows"]):
            observed_positions = [
                position for position in row["value_positions"] if position["source_atom_ids"]
            ]
            position_ordinals = [
                min(source_ordinals[atom_id] for atom_id in position["source_atom_ids"])
                for position in observed_positions
            ]
            if position_ordinals != sorted(position_ordinals):
                raise _error(f"region {region_index} row {row_index} value-position order drifted")
        _validate_value_geometry(
            region,
            coordinate_authority=source_projection["coordinate_authority"],
            label=f"region {region_index}",
        )
    return value


def _presentation_label_body(text: str) -> str:
    normalized = _normalize_text(text)
    return re.sub(r"^(?:(?:[0-9]+|[ivxlcdm]+)\s+)+", "", normalized)


def _branch_matches(text: str, aliases: tuple[str, ...]) -> bool:
    return _presentation_label_body(text) in _normalized_aliases(aliases, "runtime branch")


def _owner_matches(text: str, aliases: tuple[str, ...]) -> bool:
    return _presentation_label_body(text) in _normalized_aliases(aliases, "runtime owner")


def _row_role(text: str | None, spec: FamilySpecV1) -> str | None:
    if text is None:
        return None
    normalized = _normalize_text(text)
    matches = [
        row_spec.role
        for row_spec in spec.ordered_children + spec.optional_children
        if normalized in _normalized_aliases(row_spec.aliases, f"runtime {row_spec.role}")
    ]
    total_match = normalized in _normalized_aliases(spec.total_aliases, "runtime total")
    if total_match:
        matches.append("TOTAL")
    return matches[0] if len(matches) == 1 else None


def parse_local_accounting_period_v1(text: str) -> str | None:
    """Parse one strict, source-visible comparative period label."""

    if type(text) is not str or not text.strip():
        return None
    normalized = _normalize_text(text)
    if "%" in text or "phan tram" in normalized or "ty le" in normalized:
        return None
    date_matches = _PERIOD_DATE_RE.findall(text)
    if len(date_matches) == 1:
        day, month, year = date_matches[0]
        day_int = int(day)
        month_int = int(month)
        year_int = int(year)
        try:
            date(year_int, month_int, day_int)
        except ValueError:
            return None
        year_matches = _PERIOD_YEAR_RE.findall(text)
        if year_matches != [year]:
            return None
        return f"DATE:{year_int:04d}-{month_int:02d}-{day_int:02d}"
    year_matches = _PERIOD_YEAR_RE.findall(text)
    if not date_matches and len(year_matches) == 1:
        return f"YEAR:{year_matches[0]}"
    return None


def parse_local_accounting_unit_v1(text: str) -> dict[str, Any] | None:
    """Parse one strict, local source-visible VND unit expression."""

    if type(text) is not str or not text.strip():
        return None
    text = _normalize_text(text)
    forbidden_tokens = {"usd", "eur", "jpy", "cny", "phan tram", "ty le", "quy doi"}
    if any(token in text for token in forbidden_tokens):
        return None
    match = re.fullmatch(
        r"(?:(?:don vi(?: tinh)?|dvt) )?"
        r"(?:(nghin|ngan|trieu|triu|ty) )?"
        r"(vnd|dong|dong viet nam)",
        text,
    )
    if match is None or (match.group(1) is None and not text.startswith(("don vi ", "dvt "))):
        return None
    scale = {
        None: 1,
        "nghin": 1_000,
        "ngan": 1_000,
        "trieu": 1_000_000,
        "triu": 1_000_000,
        "ty": 1_000_000_000,
    }[match.group(1)]
    return {"basis": "LOCAL_VISIBLE_UNIT", "currency": "VND", "scale": scale}


def _period_label(text: str) -> str | None:
    return parse_local_accounting_period_v1(text)


def _local_unit(span: Mapping[str, Any]) -> dict[str, Any] | None:
    return parse_local_accounting_unit_v1(span["text"])


def _region_evidence(region: Mapping[str, Any]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = [
        {"role": "OWNER_LABEL", "span": region["owner_label"]},
        {"role": "BRANCH_LABEL", "span": region["branch_label"]},
    ]
    evidence.extend(
        {"role": f"AXIS_HEADER:{index}", "span": axis["header"]}
        for index, axis in enumerate(region["axes"])
    )
    evidence.extend(
        {"role": f"LOCAL_UNIT:{index}", "span": span}
        for index, span in enumerate(region["local_unit_labels"])
    )
    for row_index, row in enumerate(region["rows"]):
        if row["label"] is not None:
            evidence.append({"role": f"ROW_LABEL:{row_index}", "span": row["label"]})
        for position in row["value_positions"]:
            evidence.append(
                {
                    "role": f"VALUE_POSITION:{row_index}:{position['axis_index']}",
                    "span": {
                        "text": position["raw_text"],
                        "canonical_bbox_mpt": position["canonical_bbox_mpt"],
                        "source_atom_ids": position["source_atom_ids"],
                    },
                    "value_state": position["state"],
                }
            )
    return evidence


def _unlabeled_total_is_immediate(
    region: Mapping[str, Any], source_projection: Mapping[str, Any]
) -> bool:
    unlabeled_indexes = [index for index, row in enumerate(region["rows"]) if row["label"] is None]
    if len(unlabeled_indexes) != 1 or unlabeled_indexes[0] == 0:
        return False
    total_index = unlabeled_indexes[0]
    if total_index != len(region["rows"]) - 1:
        return False
    previous_row = region["rows"][total_index - 1]
    total_row = region["rows"][total_index]
    previous_ids = [
        *(previous_row["label"] or {"source_atom_ids": []})["source_atom_ids"],
        *(
            atom_id
            for position in previous_row["value_positions"]
            for atom_id in position["source_atom_ids"]
        ),
    ]
    total_ids = [
        atom_id
        for position in total_row["value_positions"]
        for atom_id in position["source_atom_ids"]
    ]
    if not previous_ids or not total_ids:
        return False
    atom_sequence = source_projection["neutral_page_v1"]["atoms"]
    atom_by_id = {atom["source_local_id"]: atom for atom in atom_sequence}
    authority_kind = atom_by_id[previous_ids[-1]]["kind"]
    if authority_kind not in {"LINE", "WORD"} or any(
        atom_by_id[atom_id]["kind"] != authority_kind for atom_id in previous_ids + total_ids
    ):
        return False
    eligible_ids = [
        atom["source_local_id"]
        for atom in atom_sequence
        if atom.get("authority") == "AUTHENTICATED_PRIMARY"
        and atom.get("kind") == authority_kind
        and atom.get("canonical_bbox_mpt") is not None
        and _contains(region["canonical_bbox_mpt"], atom["canonical_bbox_mpt"])
    ]
    eligible_position = {atom_id: index for index, atom_id in enumerate(eligible_ids)}
    if previous_ids[-1] not in eligible_position or total_ids[0] not in eligible_position:
        return False
    previous_box, _ = _row_source_parts(previous_row)
    total_box, _ = _row_source_parts(total_row)
    return (
        eligible_position[total_ids[0]] == eligible_position[previous_ids[-1]] + 1
        and previous_box[1] < total_box[1]
    )


def _evaluate_region(
    region: Mapping[str, Any],
    spec: FamilySpecV1,
    *,
    source_projection: Mapping[str, Any],
) -> dict[str, Any]:
    reasons: set[str] = set()
    if not _owner_matches(region["owner_label"]["text"], spec.owner_aliases):
        reasons.add("OWNER_NOT_RESOLVED")
    if not _branch_matches(region["branch_label"]["text"], spec.branch_aliases):
        reasons.add("BRANCH_NOT_RESOLVED")

    axis_count = spec.axis_layout.comparative_monetary_period_count
    if len(region["axes"]) != axis_count:
        reasons.add("COMPARATIVE_MONETARY_AXIS_LAYOUT_NOT_RESOLVED")
        period_labels: list[str | None] = [None] * len(region["axes"])
    else:
        period_labels = [_period_label(axis["header"]["text"]) for axis in region["axes"]]
        if any(label is None for label in period_labels) or len(set(period_labels)) != axis_count:
            reasons.add("COMPARATIVE_MONETARY_AXIS_LAYOUT_NOT_RESOLVED")

    if not region["local_unit_labels"]:
        reasons.add("MISSING_LOCAL_VISIBLE_UNIT")
        unit = None
    elif len(region["local_unit_labels"]) > 1:
        reasons.add("MULTIPLE_LOCAL_VISIBLE_UNITS")
        unit = None
    else:
        unit = _local_unit(region["local_unit_labels"][0])
        if unit is None:
            reasons.add("AMBIGUOUS_LOCAL_VISIBLE_UNIT")

    row_roles = [
        _row_role(row["label"]["text"] if row["label"] is not None else None, spec)
        for row in region["rows"]
    ]
    unlabeled_indexes = [index for index, row in enumerate(region["rows"]) if row["label"] is None]
    labeled_total_present = "TOTAL" in row_roles
    child_roles = {item.role for item in spec.ordered_children + spec.optional_children}
    if (
        len(unlabeled_indexes) == 1
        and not labeled_total_present
        and region["adjacent_row_boundaries_verified"] is True
        and _unlabeled_total_is_immediate(region, source_projection)
        and unlabeled_indexes[0] == len(region["rows"]) - 1
        and unlabeled_indexes[0] > 0
        and row_roles[unlabeled_indexes[0] - 1] in child_roles
    ):
        row_roles[unlabeled_indexes[0]] = "TOTAL"
    if any(role is None for role in row_roles):
        reasons.add("UNCLASSIFIED_OR_AMBIGUOUS_ROW")
    if any(row_roles.count(role) != 1 for role in row_roles if role is not None):
        reasons.add("DUPLICATE_ROW_ROLE")
    required_roles = [item.role for item in spec.ordered_children]
    present_required = [role for role in row_roles if role in required_roles]
    if present_required != required_roles:
        reasons.add("ORDERED_SIBLING_SET_NOT_RESOLVED")
    if row_roles.count("TOTAL") != 1:
        reasons.add("TOTAL_NOT_RESOLVED")
    elif row_roles[-1] != "TOTAL":
        reasons.add("TOTAL_NOT_AFTER_CHILDREN")

    row_by_role: dict[str, Mapping[str, Any]] = {}
    for role, row in zip(row_roles, region["rows"], strict=True):
        if role is not None and role not in row_by_role:
            row_by_role[role] = row
        positions = row["value_positions"]
        if len(positions) != axis_count or sorted(
            position["axis_index"] for position in positions
        ) != list(range(axis_count)):
            reasons.add("VALUE_POSITION_AXIS_COVERAGE_NOT_RESOLVED")
        if any(position["state"] in _NONDETERMINATE_VALUE_STATES for position in positions):
            reasons.add("VALUE_POSITION_SEMANTICS_UNRESOLVED")

    structural_reasons = sorted(reasons)
    arithmetic = {"status": "NOT_EVALUABLE", "evaluated_axis_indexes": []}
    present_optional_closure_roles = tuple(
        item.role for item in spec.optional_children if item.role in row_by_role
    )
    closure_roles = spec.closure_child_roles + present_optional_closure_roles
    closure_rows_available = all(role in row_by_role for role in closure_roles)
    if closure_rows_available and "TOTAL" in row_by_role and len(region["axes"]) == axis_count:
        evaluated: list[int] = []
        mismatched: list[int] = []
        for axis_index in range(axis_count):
            values: list[Decimal] = []
            for role in closure_roles:
                position = next(
                    (
                        item
                        for item in row_by_role[role]["value_positions"]
                        if item["axis_index"] == axis_index
                    ),
                    None,
                )
                parsed = (
                    _parse_decimal(position["raw_text"])
                    if position is not None
                    and position["state"]
                    in {ValueStateV1.OBSERVED_VALUE.value, ValueStateV1.OBSERVED_ZERO.value}
                    else None
                )
                if parsed is None:
                    values = []
                    break
                values.append(parsed)
            total_position = next(
                (
                    item
                    for item in row_by_role["TOTAL"]["value_positions"]
                    if item["axis_index"] == axis_index
                ),
                None,
            )
            total = (
                _parse_decimal(total_position["raw_text"])
                if total_position is not None
                and total_position["state"]
                in {ValueStateV1.OBSERVED_VALUE.value, ValueStateV1.OBSERVED_ZERO.value}
                else None
            )
            if values and total is not None:
                evaluated.append(axis_index)
                if sum(values, Decimal()) != total:
                    mismatched.append(axis_index)
        arithmetic = {
            "status": (
                "VETOED"
                if mismatched
                else "CORROBORATED"
                if len(evaluated) == axis_count
                else "NOT_EVALUABLE"
            ),
            "evaluated_axis_indexes": evaluated,
        }
        if mismatched:
            reasons.add("ARITHMETIC_CLOSURE_VETO")
    return {
        "structurally_complete": not structural_reasons,
        "complete": not reasons,
        "reasons": sorted(reasons),
        "row_roles": row_roles,
        "period_labels": period_labels,
        "unit": unit,
        "arithmetic": arithmetic,
    }


def _source_ref(
    observation: Mapping[str, Any], bbox: Sequence[int], atom_ids: Sequence[str]
) -> dict[str, Any]:
    return {
        "source_local_page_id": observation["source_local_page_id"],
        "source_projection_sha256": observation["source_projection_sha256"],
        "canonical_bbox_mpt": list(bbox),
        "source_atom_ids": sorted(set(atom_ids)),
    }


def _node(
    *,
    kind: AcceptedNodeKindV1,
    status: str,
    source_ref: Mapping[str, Any],
    attributes: Mapping[str, Any],
    unresolved_reasons: Sequence[str] = (),
) -> dict[str, Any]:
    value = {
        "kind": kind.value,
        "status": status,
        "source_ref": canonical_clone_v1(source_ref),
        "attributes": canonical_clone_v1(attributes),
        "unresolved_reasons": sorted(set(unresolved_reasons)),
    }
    value["node_id"] = f"lagv1:node:{canonical_json_sha256_v1(value)}"
    return value


def _edge(
    kind: AcceptedEdgeKindV1,
    from_node_id: str,
    to_node_id: str,
    evidence_node_ids: Sequence[str],
) -> dict[str, Any]:
    value = {
        "kind": kind.value,
        "from_node_id": from_node_id,
        "to_node_id": to_node_id,
        "evidence_node_ids": sorted(set(evidence_node_ids)),
    }
    value["edge_id"] = f"lagv1:edge:{canonical_json_sha256_v1(value)}"
    return value


def _evidence_nodes(
    observation: Mapping[str, Any], region: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    nodes = []
    by_role = {}
    for evidence in _region_evidence(region):
        span = evidence["span"]
        attributes = {"evidence_role": evidence["role"], "raw_text": span["text"]}
        if "value_state" in evidence:
            attributes["value_state"] = evidence["value_state"]
        node = _node(
            kind=AcceptedNodeKindV1.EVIDENCE,
            status="BOUND_SOURCE_EVIDENCE",
            source_ref=_source_ref(
                observation,
                span["canonical_bbox_mpt"],
                span["source_atom_ids"],
            ),
            attributes=attributes,
        )
        nodes.append(node)
        by_role[evidence["role"]] = node["node_id"]
    return nodes, by_role


def _row_source_parts(row: Mapping[str, Any]) -> tuple[list[int], list[str]]:
    if row["label"] is not None:
        return row["label"]["canonical_bbox_mpt"], row["label"]["source_atom_ids"]
    positions = row["value_positions"]
    return (
        _union_box([position["canonical_bbox_mpt"] for position in positions]),
        sorted({atom_id for position in positions for atom_id in position["source_atom_ids"]}),
    )


def _row_evidence_ids(
    evidence_by_role: Mapping[str, str], row_index: int, row: Mapping[str, Any]
) -> list[str]:
    label_key = f"ROW_LABEL:{row_index}"
    if label_key in evidence_by_role:
        return [evidence_by_role[label_key]]
    return [
        evidence_by_role[f"VALUE_POSITION:{row_index}:{position['axis_index']}"]
        for position in row["value_positions"]
    ]


def _accepted_region_graph(
    observation: Mapping[str, Any],
    region: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    spec: FamilySpecV1,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    evidence_nodes, evidence_by_role = _evidence_nodes(observation, region)
    nodes = list(evidence_nodes)
    edges: list[dict[str, Any]] = []
    all_atom_ids = sorted(
        {
            atom_id
            for evidence in _region_evidence(region)
            for atom_id in evidence["span"]["source_atom_ids"]
        }
    )
    all_evidence_ids = sorted(evidence_by_role.values())
    table = _node(
        kind=AcceptedNodeKindV1.TABLE,
        status="ACCEPTED_SOURCE_STRUCTURE",
        source_ref=_source_ref(observation, region["canonical_bbox_mpt"], all_atom_ids),
        attributes={
            "family_id": spec.family_id,
            "family_spec_sha256": _family_spec_sha256(spec),
            "closure_claim": "INTERNAL_ADDITIVE_CLOSURE_ONLY",
        },
    )
    nodes.append(table)
    owner = _node(
        kind=AcceptedNodeKindV1.ACCOUNTING_ROLE,
        status="ACCEPTED_SOURCE_STRUCTURE",
        source_ref=_source_ref(
            observation,
            region["owner_label"]["canonical_bbox_mpt"],
            region["owner_label"]["source_atom_ids"],
        ),
        attributes={"accounting_role": "OWNER_LABEL", "family_id": spec.family_id},
    )
    branch = _node(
        kind=AcceptedNodeKindV1.ACCOUNTING_ROLE,
        status="ACCEPTED_SOURCE_STRUCTURE",
        source_ref=_source_ref(
            observation,
            region["branch_label"]["canonical_bbox_mpt"],
            region["branch_label"]["source_atom_ids"],
        ),
        attributes={"accounting_role": "BRANCH", "family_id": spec.family_id},
    )
    nodes.extend((owner, branch))
    edges.extend(
        (
            _edge(
                AcceptedEdgeKindV1.OWNS,
                owner["node_id"],
                table["node_id"],
                [evidence_by_role["OWNER_LABEL"]],
            ),
            _edge(
                AcceptedEdgeKindV1.PARENT_OF,
                owner["node_id"],
                branch["node_id"],
                [evidence_by_role["OWNER_LABEL"], evidence_by_role["BRANCH_LABEL"]],
            ),
            _edge(
                AcceptedEdgeKindV1.SUPPORTED_BY,
                table["node_id"],
                evidence_by_role["OWNER_LABEL"],
                all_evidence_ids,
            ),
            _edge(
                AcceptedEdgeKindV1.SUPPORTED_BY,
                owner["node_id"],
                evidence_by_role["OWNER_LABEL"],
                [evidence_by_role["OWNER_LABEL"]],
            ),
            _edge(
                AcceptedEdgeKindV1.SUPPORTED_BY,
                branch["node_id"],
                evidence_by_role["BRANCH_LABEL"],
                [evidence_by_role["BRANCH_LABEL"]],
            ),
        )
    )

    axis_nodes = []
    for axis_index, (axis, period_label) in enumerate(
        zip(region["axes"], evaluation["period_labels"], strict=True)
    ):
        axis_node = _node(
            kind=AcceptedNodeKindV1.AXIS,
            status="ACCEPTED_SOURCE_STRUCTURE",
            source_ref=_source_ref(
                observation,
                axis["header"]["canonical_bbox_mpt"],
                axis["header"]["source_atom_ids"],
            ),
            attributes={
                "axis_index": axis_index,
                "axis_role": "COMPARATIVE_MONETARY_PERIOD",
                "period_label": period_label,
            },
        )
        axis_nodes.append(axis_node)
        nodes.append(axis_node)
        evidence_id = evidence_by_role[f"AXIS_HEADER:{axis_index}"]
        edges.extend(
            (
                _edge(
                    AcceptedEdgeKindV1.CONTAINS,
                    table["node_id"],
                    axis_node["node_id"],
                    [evidence_id],
                ),
                _edge(
                    AcceptedEdgeKindV1.SUPPORTED_BY,
                    axis_node["node_id"],
                    evidence_id,
                    [evidence_id],
                ),
            )
        )

    unit_span = region["local_unit_labels"][0]
    unit_node = _node(
        kind=AcceptedNodeKindV1.CONTEXT,
        status="ACCEPTED_SOURCE_STRUCTURE",
        source_ref=_source_ref(
            observation,
            unit_span["canonical_bbox_mpt"],
            unit_span["source_atom_ids"],
        ),
        attributes=evaluation["unit"],
    )
    nodes.append(unit_node)
    unit_evidence_id = evidence_by_role["LOCAL_UNIT:0"]
    edges.extend(
        (
            _edge(
                AcceptedEdgeKindV1.SCOPED_BY,
                table["node_id"],
                unit_node["node_id"],
                [unit_evidence_id],
            ),
            _edge(
                AcceptedEdgeKindV1.SUPPORTED_BY,
                unit_node["node_id"],
                unit_evidence_id,
                [unit_evidence_id],
            ),
        )
    )

    row_nodes = []
    row_node_by_role = {}
    for row_index, (row, row_role) in enumerate(
        zip(region["rows"], evaluation["row_roles"], strict=True)
    ):
        row_kind = (
            "TOTAL"
            if row_role == "TOTAL"
            else "OPTIONAL_CHILD"
            if row_role in {item.role for item in spec.optional_children}
            else "REQUIRED_CHILD"
        )
        row_box, row_atom_ids = _row_source_parts(row)
        row_node = _node(
            kind=AcceptedNodeKindV1.LOGICAL_ROW,
            status="ACCEPTED_SOURCE_STRUCTURE",
            source_ref=_source_ref(
                observation,
                row_box,
                row_atom_ids,
            ),
            attributes={"family_row_role": row_role, "row_kind": row_kind},
        )
        row_nodes.append(row_node)
        row_node_by_role[row_role] = row_node
        nodes.append(row_node)
        row_evidence_ids = _row_evidence_ids(evidence_by_role, row_index, row)
        primary_row_evidence_id = row_evidence_ids[0]
        edges.extend(
            (
                _edge(
                    AcceptedEdgeKindV1.CONTAINS,
                    table["node_id"],
                    row_node["node_id"],
                    row_evidence_ids,
                ),
                _edge(
                    AcceptedEdgeKindV1.PARENT_OF,
                    branch["node_id"],
                    row_node["node_id"],
                    [evidence_by_role["BRANCH_LABEL"], *row_evidence_ids],
                ),
                _edge(
                    AcceptedEdgeKindV1.SUPPORTED_BY,
                    row_node["node_id"],
                    primary_row_evidence_id,
                    row_evidence_ids,
                ),
            )
        )
        for position in row["value_positions"]:
            axis_index = position["axis_index"]
            value_evidence_id = evidence_by_role[f"VALUE_POSITION:{row_index}:{axis_index}"]
            value_node = _node(
                kind=AcceptedNodeKindV1.VALUE_POSITION,
                status="ACCEPTED_SOURCE_STRUCTURE",
                source_ref=_source_ref(
                    observation,
                    position["canonical_bbox_mpt"],
                    position["source_atom_ids"],
                ),
                attributes={
                    "axis_index": axis_index,
                    "raw_text": position["raw_text"],
                    "value_state": position["state"],
                },
            )
            nodes.append(value_node)
            edges.extend(
                (
                    _edge(
                        AcceptedEdgeKindV1.CONTAINS,
                        row_node["node_id"],
                        value_node["node_id"],
                        [*row_evidence_ids, value_evidence_id],
                    ),
                    _edge(
                        AcceptedEdgeKindV1.ALIGNED_TO_AXIS,
                        value_node["node_id"],
                        axis_nodes[axis_index]["node_id"],
                        [value_evidence_id, evidence_by_role[f"AXIS_HEADER:{axis_index}"]],
                    ),
                    _edge(
                        AcceptedEdgeKindV1.SUPPORTED_BY,
                        value_node["node_id"],
                        value_evidence_id,
                        [value_evidence_id],
                    ),
                )
            )

    for left_index, (left, right) in enumerate(zip(row_nodes, row_nodes[1:], strict=False)):
        right_index = left_index + 1
        edges.append(
            _edge(
                AcceptedEdgeKindV1.NEXT_SIBLING,
                left["node_id"],
                right["node_id"],
                [
                    *_row_evidence_ids(evidence_by_role, left_index, region["rows"][left_index]),
                    *_row_evidence_ids(evidence_by_role, right_index, region["rows"][right_index]),
                ],
            )
        )
    total_node = row_node_by_role["TOTAL"]
    total_relation_roles = spec.closure_child_roles + tuple(
        item.role for item in spec.optional_children if item.role in row_node_by_role
    )
    for role in total_relation_roles:
        child_node = row_node_by_role[role]
        child_index = row_nodes.index(child_node)
        total_index = row_nodes.index(total_node)
        evidence_ids = [
            *_row_evidence_ids(evidence_by_role, child_index, region["rows"][child_index]),
            *_row_evidence_ids(evidence_by_role, total_index, region["rows"][total_index]),
        ]
        edges.append(
            _edge(
                AcceptedEdgeKindV1.TOTAL_OF,
                total_node["node_id"],
                child_node["node_id"],
                evidence_ids,
            )
        )
    return nodes, edges


def _unresolved_region_node(
    observation: Mapping[str, Any],
    region: Mapping[str, Any],
    reasons: Sequence[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    evidence_nodes, evidence_by_role = _evidence_nodes(observation, region)
    atom_ids = sorted(
        {
            atom_id
            for evidence in _region_evidence(region)
            for atom_id in evidence["span"]["source_atom_ids"]
        }
    )
    unresolved = _node(
        kind=AcceptedNodeKindV1.UNRESOLVED_REGION,
        status="EXPLICIT_UNRESOLVED",
        source_ref=_source_ref(observation, region["canonical_bbox_mpt"], atom_ids),
        attributes={"retained_source_evidence": True},
        unresolved_reasons=reasons,
    )
    edges = [
        _edge(
            AcceptedEdgeKindV1.SUPPORTED_BY,
            unresolved["node_id"],
            evidence_node_id,
            list(evidence_by_role.values()),
        )
        for evidence_node_id in sorted(evidence_by_role.values())
    ]
    return evidence_nodes + [unresolved], edges


def infer_local_accounting_graph_v1(
    source_projection_v2: Mapping[str, Any],
    observation: Mapping[str, Any],
    family_spec: FamilySpecV1,
    *,
    diagnostic_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Accept one unique complete local family match or retain explicit unresolved.

    ``diagnostic_metadata`` is deliberately ignored and excluded from every
    decision, digest, and output.  It permits provenance/reporting callers to
    carry bank/file/page/Role-A/schema annotations without allowing them to
    become inference inputs.
    """

    del diagnostic_metadata
    _validate_family_spec(family_spec)
    try:
        source_projection = validate_source_evidence_projection_v2(source_projection_v2)
    except Exception as error:
        raise _error("source projection did not satisfy the exact V2 contract") from error
    if source_projection.get("terminal") is not False:
        raise _error("LAG acceptance requires a non-terminal exact V2 source projection")
    source = _validate_observation(
        canonical_clone_v1(observation), source_projection=source_projection
    )
    evaluations = [
        _evaluate_region(region, family_spec, source_projection=source_projection)
        for region in source["regions"]
    ]
    structurally_complete_indexes = [
        index for index, item in enumerate(evaluations) if item["structurally_complete"]
    ]
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    unresolved_reasons: set[str] = set()
    arithmetic_check: dict[str, Any]
    if (
        len(structurally_complete_indexes) == 1
        and evaluations[structurally_complete_indexes[0]]["complete"]
    ):
        accepted_index = structurally_complete_indexes[0]
        accepted_nodes, accepted_edges = _accepted_region_graph(
            source,
            source["regions"][accepted_index],
            evaluations[accepted_index],
            family_spec,
        )
        nodes.extend(accepted_nodes)
        edges.extend(accepted_edges)
        arithmetic_check = evaluations[accepted_index]["arithmetic"]
        for index, (region, evaluation) in enumerate(
            zip(source["regions"], evaluations, strict=True)
        ):
            if index == accepted_index:
                continue
            unresolved_nodes, unresolved_edges = _unresolved_region_node(
                source, region, evaluation["reasons"]
            )
            nodes.extend(unresolved_nodes)
            edges.extend(unresolved_edges)
            unresolved_reasons.update(evaluation["reasons"])
        status = GraphStatusV1.CORE_ACCEPTED.value
    else:
        reason = (
            "MULTIPLE_COMPLETE_MATCHES"
            if len(structurally_complete_indexes) > 1
            else "NO_COMPLETE_MATCH"
        )
        unresolved_reasons.add(reason)
        for region, evaluation in zip(source["regions"], evaluations, strict=True):
            region_reasons = (
                [reason]
                if len(structurally_complete_indexes) > 1
                else evaluation["reasons"] or [reason]
            )
            unresolved_reasons.update(region_reasons)
            unresolved_nodes, unresolved_edges = _unresolved_region_node(
                source, region, region_reasons
            )
            nodes.extend(unresolved_nodes)
            edges.extend(unresolved_edges)
        arithmetic_check = (
            evaluations[0]["arithmetic"]
            if len(evaluations) == 1
            else {"status": "NOT_APPLICABLE", "evaluated_axis_indexes": []}
        )
        status = GraphStatusV1.EXPLICIT_UNRESOLVED.value

    nodes_by_id: dict[str, dict[str, Any]] = {}
    for node in nodes:
        prior = nodes_by_id.setdefault(node["node_id"], node)
        if not same_typed_json_v1(prior, node):  # pragma: no cover - SHA collision guard
            raise _error("content-addressed node identity collision")
    edges_by_id: dict[str, dict[str, Any]] = {}
    for edge in edges:
        prior = edges_by_id.setdefault(edge["edge_id"], edge)
        if not same_typed_json_v1(prior, edge):  # pragma: no cover - SHA collision guard
            raise _error("content-addressed edge identity collision")
    nodes = sorted(nodes_by_id.values(), key=lambda item: item["node_id"])
    edges = sorted(edges_by_id.values(), key=lambda item: item["edge_id"])
    accepted_counts = {
        "TABLE": sum(
            node["kind"] == AcceptedNodeKindV1.TABLE.value
            and node["status"] == "ACCEPTED_SOURCE_STRUCTURE"
            for node in nodes
        ),
        "LOGICAL_ROW": sum(
            node["kind"] == AcceptedNodeKindV1.LOGICAL_ROW.value
            and node["status"] == "ACCEPTED_SOURCE_STRUCTURE"
            for node in nodes
        ),
        "VALUE_POSITION": sum(
            node["kind"] == AcceptedNodeKindV1.VALUE_POSITION.value
            and node["status"] == "ACCEPTED_SOURCE_STRUCTURE"
            for node in nodes
        ),
        "AXIS": sum(
            node["kind"] == AcceptedNodeKindV1.AXIS.value
            and node["status"] == "ACCEPTED_SOURCE_STRUCTURE"
            for node in nodes
        ),
        "HIERARCHY": sum(edge["kind"] in _HIERARCHY_EDGES for edge in edges),
    }
    graph = {
        "format_version": LOCAL_ACCOUNTING_GRAPH_FORMAT_VERSION_V1,
        "claim_boundary": LOCAL_ACCOUNTING_GRAPH_CLAIM_BOUNDARY_V1,
        "status": status,
        "family_id": family_spec.family_id,
        "family_spec_sha256": _family_spec_sha256(family_spec),
        "source_local_page_id": source["source_local_page_id"],
        "source_projection_sha256": source["source_projection_sha256"],
        "source_observation_sha256": canonical_json_sha256_v1(source),
        "nodes": nodes,
        "edges": edges,
        "arithmetic_check": arithmetic_check,
        "unresolved_reasons": sorted(unresolved_reasons),
        "accepted_counts": accepted_counts,
        "canonicalization_eligible": False,
        "export_eligible": False,
        "safety": canonical_clone_v1(LOCAL_ACCOUNTING_GRAPH_SAFETY_V1),
    }
    graph["graph_identity"] = "lagv1:graph:" + canonical_json_sha256_v1(graph)
    return validate_local_accounting_graph_v1(graph)


def validate_local_accounting_graph_replay_v1(
    value: Any,
    *,
    source_projection_v2: Mapping[str, Any],
    observation: Mapping[str, Any],
    family_spec: FamilySpecV1,
) -> dict[str, Any]:
    """Rebuild a LAG graph from exact source inputs and compare typed bytes.

    ``validate_local_accounting_graph_v1`` proves the closed persisted graph
    contract and content identities.  This replay boundary additionally proves
    that its raw text, boxes, atom bindings, roles, and topology were produced
    from the supplied exact V2 projection and bounded observation.
    """

    actual = validate_local_accounting_graph_v1(value)
    expected = infer_local_accounting_graph_v1(
        source_projection_v2,
        observation,
        family_spec,
    )
    if not same_typed_json_v1(actual, expected):
        raise _error("graph is not the deterministic replay of exact source inputs")
    return actual


def _accepted_nodes_by_kind(
    node_by_id: Mapping[str, Mapping[str, Any]], kind: AcceptedNodeKindV1
) -> list[Mapping[str, Any]]:
    return [
        node
        for node in node_by_id.values()
        if node["status"] == "ACCEPTED_SOURCE_STRUCTURE" and node["kind"] == kind.value
    ]


def _edge_triples(
    edges: Sequence[Mapping[str, Any]], kind: AcceptedEdgeKindV1
) -> set[tuple[str, str]]:
    return {
        (edge["from_node_id"], edge["to_node_id"]) for edge in edges if edge["kind"] == kind.value
    }


def _value_state_matches_raw_text(raw_text: Any, state_value: Any) -> bool:
    try:
        state = ValueStateV1(state_value)
    except (TypeError, ValueError):
        return False
    parsed = _parse_decimal(raw_text) if type(raw_text) is str else None
    if state is ValueStateV1.OBSERVED_VALUE:
        return parsed is not None and parsed != 0
    if state is ValueStateV1.OBSERVED_ZERO:
        return parsed == 0
    if state is ValueStateV1.DASH:
        return type(raw_text) is str and raw_text.strip() in {"-", "–", "—"}
    if state in {ValueStateV1.BLANK, ValueStateV1.NOT_OBSERVED}:
        return raw_text is None
    if state is ValueStateV1.NOT_APPLICABLE:
        return type(raw_text) is str and _normalize_text(raw_text) in {
            "n a",
            "khong ap dung",
        }
    if state in {ValueStateV1.AMBIGUOUS, ValueStateV1.UNRESOLVED}:
        return raw_text is None or (type(raw_text) is str and bool(raw_text.strip()))
    return False


def _evidence_role(node: Mapping[str, Any]) -> str | None:
    if node["kind"] != AcceptedNodeKindV1.EVIDENCE.value:
        return None
    value = node["attributes"].get("evidence_role")
    return value if type(value) is str else None


def _same_source_ref(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return same_typed_json_v1(left["source_ref"], right["source_ref"])


def _validate_evidence_node(node: Mapping[str, Any]) -> None:
    attributes = node["attributes"]
    role = attributes.get("evidence_role")
    if type(role) is not str:
        raise _error("evidence role identity drifted")
    value_match = re.fullmatch(r"VALUE_POSITION:(\d+):(\d+)", role)
    other_match = re.fullmatch(
        r"(?:OWNER_LABEL|BRANCH_LABEL|AXIS_HEADER:\d+|LOCAL_UNIT:\d+|ROW_LABEL:\d+)",
        role,
    )
    if value_match:
        if set(attributes) != {"evidence_role", "raw_text", "value_state"} or not (
            _value_state_matches_raw_text(attributes["raw_text"], attributes["value_state"])
        ):
            raise _error("value evidence semantics drifted")
        state = ValueStateV1(attributes["value_state"])
        has_atoms = bool(node["source_ref"]["source_atom_ids"])
        if has_atoms != (state not in {ValueStateV1.BLANK, ValueStateV1.NOT_OBSERVED}):
            raise _error("value evidence source binding drifted")
    elif other_match:
        if (
            set(attributes) != {"evidence_role", "raw_text"}
            or type(attributes["raw_text"]) is not str
            or not attributes["raw_text"].strip()
            or not node["source_ref"]["source_atom_ids"]
        ):
            raise _error("text evidence semantics drifted")
    else:
        raise _error("evidence role is outside the LAG v1 contract")


def _validate_unresolved_partitions(
    graph: Mapping[str, Any],
    *,
    node_by_id: Mapping[str, Mapping[str, Any]],
    permitted_other_evidence_ids: set[str],
) -> tuple[set[str], set[str]]:
    """Validate and account every explicit-unresolved evidence partition."""

    unresolved_nodes = [
        node
        for node in graph["nodes"]
        if node["kind"] == AcceptedNodeKindV1.UNRESOLVED_REGION.value
    ]
    assigned_evidence_ids: set[str] = set()
    unresolved_reasons: set[str] = set()
    for unresolved in unresolved_nodes:
        outgoing = [
            edge for edge in graph["edges"] if edge["from_node_id"] == unresolved["node_id"]
        ]
        target_ids = {edge["to_node_id"] for edge in outgoing}
        if (
            not target_ids
            or len(outgoing) != len(target_ids)
            or any(
                edge["kind"] != AcceptedEdgeKindV1.SUPPORTED_BY.value
                or node_by_id[edge["to_node_id"]]["kind"] != AcceptedNodeKindV1.EVIDENCE.value
                or set(edge["evidence_node_ids"]) != target_ids
                for edge in outgoing
            )
        ):
            raise _error("explicit unresolved region lost its bounded evidence")
        region_evidence = [node_by_id[node_id] for node_id in target_ids]
        expected_source_ref = {
            "source_local_page_id": graph["source_local_page_id"],
            "source_projection_sha256": graph["source_projection_sha256"],
            "canonical_bbox_mpt": _union_box(
                [item["source_ref"]["canonical_bbox_mpt"] for item in region_evidence]
            ),
            "source_atom_ids": sorted(
                {
                    atom_id
                    for item in region_evidence
                    for atom_id in item["source_ref"]["source_atom_ids"]
                }
            ),
        }
        if not same_typed_json_v1(unresolved["source_ref"], expected_source_ref):
            raise _error("explicit unresolved source-evidence union drifted")
        assigned_evidence_ids.update(target_ids)
        unresolved_reasons.update(unresolved["unresolved_reasons"])
    all_evidence_ids = {
        node["node_id"]
        for node in graph["nodes"]
        if node["kind"] == AcceptedNodeKindV1.EVIDENCE.value
    }
    if all_evidence_ids != assigned_evidence_ids | permitted_other_evidence_ids:
        raise _error("graph contains orphan or unaccounted evidence")
    return assigned_evidence_ids, unresolved_reasons


def _validate_accepted_topology(
    graph: Mapping[str, Any],
    *,
    node_by_id: Mapping[str, Mapping[str, Any]],
) -> None:
    spec = _FROZEN_FAMILY_SPEC_BY_ID[graph["family_id"]]
    nodes = node_by_id.values()
    edges = graph["edges"]
    tables = _accepted_nodes_by_kind(node_by_id, AcceptedNodeKindV1.TABLE)
    rows = _accepted_nodes_by_kind(node_by_id, AcceptedNodeKindV1.LOGICAL_ROW)
    values = _accepted_nodes_by_kind(node_by_id, AcceptedNodeKindV1.VALUE_POSITION)
    axes = _accepted_nodes_by_kind(node_by_id, AcceptedNodeKindV1.AXIS)
    roles = _accepted_nodes_by_kind(node_by_id, AcceptedNodeKindV1.ACCOUNTING_ROLE)
    contexts = _accepted_nodes_by_kind(node_by_id, AcceptedNodeKindV1.CONTEXT)
    if len(tables) != 1 or len(contexts) != 1 or len(roles) != 2:
        raise _error("accepted graph table/context/accounting-role cardinality drifted")
    table = tables[0]
    context = contexts[0]
    expected_table_attributes = {
        "family_id": spec.family_id,
        "family_spec_sha256": graph["family_spec_sha256"],
        "closure_claim": "INTERNAL_ADDITIVE_CLOSURE_ONLY",
    }
    if not same_typed_json_v1(table["attributes"], expected_table_attributes):
        raise _error("accepted table family/spec/closure attributes drifted")
    role_by_name = {node["attributes"].get("accounting_role"): node for node in roles}
    if set(role_by_name) != {"OWNER_LABEL", "BRANCH"} or any(
        node["attributes"].get("family_id") != spec.family_id
        or set(node["attributes"]) != {"accounting_role", "family_id"}
        for node in roles
    ):
        raise _error("accepted owner/branch attributes drifted")
    owner = role_by_name["OWNER_LABEL"]
    branch = role_by_name["BRANCH"]
    if not same_typed_json_v1(
        context["attributes"],
        {
            "basis": "LOCAL_VISIBLE_UNIT",
            "currency": "VND",
            "scale": context["attributes"].get("scale"),
        },
    ) or context["attributes"]["scale"] not in {1, 1_000, 1_000_000, 1_000_000_000}:
        raise _error("accepted local visible unit context drifted")

    axis_count = spec.axis_layout.comparative_monetary_period_count
    axis_by_index = {node["attributes"].get("axis_index"): node for node in axes}
    if set(axis_by_index) != set(range(axis_count)) or len(axes) != axis_count:
        raise _error("accepted comparative-axis cardinality/indexes drifted")
    for axis_index, axis in axis_by_index.items():
        attributes = axis["attributes"]
        if (
            set(attributes) != {"axis_index", "axis_role", "period_label"}
            or attributes["axis_role"] != "COMPARATIVE_MONETARY_PERIOD"
            or type(attributes["period_label"]) is not str
        ):
            raise _error(f"accepted axis {axis_index} attributes drifted")
        if not re.fullmatch(r"(?:DATE:\d{4}-\d{2}-\d{2}|YEAR:\d{4})", attributes["period_label"]):
            raise _error(f"accepted axis {axis_index} period identity drifted")
        if attributes["period_label"].startswith("DATE:"):
            try:
                date.fromisoformat(attributes["period_label"].removeprefix("DATE:"))
            except ValueError as error:
                raise _error(f"accepted axis {axis_index} date identity drifted") from error
    if len({axis["attributes"]["period_label"] for axis in axes}) != axis_count:
        raise _error("accepted comparative-axis periods must be distinct")

    required_roles = [item.role for item in spec.ordered_children]
    optional_roles = {item.role for item in spec.optional_children}
    row_by_role: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        attributes = row["attributes"]
        if set(attributes) != {"family_row_role", "row_kind"}:
            raise _error("accepted row attributes drifted")
        role = attributes["family_row_role"]
        expected_kind = (
            "TOTAL"
            if role == "TOTAL"
            else "OPTIONAL_CHILD"
            if role in optional_roles
            else "REQUIRED_CHILD"
            if role in required_roles
            else None
        )
        if expected_kind is None or attributes["row_kind"] != expected_kind or role in row_by_role:
            raise _error("accepted row role/kind identity drifted")
        row_by_role[role] = row
    if not set(required_roles + ["TOTAL"]).issubset(row_by_role) or not set(row_by_role).issubset(
        set(required_roles) | optional_roles | {"TOTAL"}
    ):
        raise _error("accepted required/optional/total row set drifted")

    value_owner: dict[str, str] = {}
    contains = _edge_triples(edges, AcceptedEdgeKindV1.CONTAINS)
    aligned = _edge_triples(edges, AcceptedEdgeKindV1.ALIGNED_TO_AXIS)
    for value in values:
        attributes = value["attributes"]
        if set(attributes) != {"axis_index", "raw_text", "value_state"}:
            raise _error("accepted value-position attributes drifted")
        try:
            state = ValueStateV1(attributes["value_state"])
        except (TypeError, ValueError) as error:
            raise _error("accepted value-position state drifted") from error
        if (
            state.value in _NONDETERMINATE_VALUE_STATES
            or attributes["axis_index"] not in axis_by_index
            or not _value_state_matches_raw_text(attributes["raw_text"], attributes["value_state"])
        ):
            raise _error("accepted value-position semantics/axis drifted")
        owners = [row for row in rows if (row["node_id"], value["node_id"]) in contains]
        if len(owners) != 1:
            raise _error("accepted value-position must belong to exactly one logical row")
        value_owner[value["node_id"]] = owners[0]["node_id"]
        expected_axis = axis_by_index[attributes["axis_index"]]["node_id"]
        if (value["node_id"], expected_axis) not in aligned:
            raise _error("accepted value-position axis alignment drifted")
    for row in rows:
        owned = [value for value in values if value_owner.get(value["node_id"]) == row["node_id"]]
        if len(owned) != axis_count or {
            value["attributes"]["axis_index"] for value in owned
        } != set(range(axis_count)):
            raise _error("accepted row value-position axis coverage drifted")
    expected_aligned = {
        (
            value["node_id"],
            axis_by_index[value["attributes"]["axis_index"]]["node_id"],
        )
        for value in values
    }
    if aligned != expected_aligned:
        raise _error("accepted value-position axis alignment edge set drifted")

    owns = _edge_triples(edges, AcceptedEdgeKindV1.OWNS)
    parent = _edge_triples(edges, AcceptedEdgeKindV1.PARENT_OF)
    scoped = _edge_triples(edges, AcceptedEdgeKindV1.SCOPED_BY)
    if owns != {(owner["node_id"], table["node_id"])}:
        raise _error("accepted owner-to-table edge drifted")
    if parent != {
        (owner["node_id"], branch["node_id"]),
        *((branch["node_id"], row["node_id"]) for row in rows),
    }:
        raise _error("accepted owner/branch/row hierarchy drifted")
    expected_contains = {
        *((table["node_id"], axis["node_id"]) for axis in axes),
        *((table["node_id"], row["node_id"]) for row in rows),
        *((value_owner[value["node_id"]], value["node_id"]) for value in values),
    }
    if contains != expected_contains or scoped != {(table["node_id"], context["node_id"])}:
        raise _error("accepted table/row/value/unit containment drifted")

    sibling_edges = _edge_triples(edges, AcceptedEdgeKindV1.NEXT_SIBLING)
    next_by_left = {left: right for left, right in sibling_edges}
    previous = {right: left for left, right in sibling_edges}
    if len(next_by_left) != len(sibling_edges) or len(previous) != len(sibling_edges):
        raise _error("accepted sibling chain forks or merges")
    starts = [row["node_id"] for row in rows if row["node_id"] not in previous]
    if len(starts) != 1 or len(sibling_edges) != len(rows) - 1:
        raise _error("accepted sibling chain cardinality drifted")
    ordered_row_ids = [starts[0]]
    while ordered_row_ids[-1] in next_by_left:
        ordered_row_ids.append(next_by_left[ordered_row_ids[-1]])
    if len(ordered_row_ids) != len(rows):
        raise _error("accepted sibling chain is disconnected or cyclic")
    role_by_id = {row["node_id"]: row["attributes"]["family_row_role"] for row in rows}
    ordered_roles = [role_by_id[row_id] for row_id in ordered_row_ids]
    if [
        role for role in ordered_roles if role in required_roles
    ] != required_roles or ordered_roles[-1] != "TOTAL":
        raise _error("accepted ordered sibling roles drifted")
    expected_total_children = set(spec.closure_child_roles) | (set(row_by_role) & optional_roles)
    total_edges = _edge_triples(edges, AcceptedEdgeKindV1.TOTAL_OF)
    if total_edges != {
        (row_by_role["TOTAL"]["node_id"], row_by_role[role]["node_id"])
        for role in expected_total_children
    }:
        raise _error("accepted internal additive closure edges drifted")

    accepted_non_evidence = [
        node for node in nodes if node["status"] == "ACCEPTED_SOURCE_STRUCTURE"
    ]
    if any(not node["source_ref"]["source_atom_ids"] for node in accepted_non_evidence):
        raise _error("accepted node lacks exact supporting source atoms")

    evidence_nodes = [node for node in nodes if node["kind"] == AcceptedNodeKindV1.EVIDENCE.value]
    if any(_evidence_role(node) is None for node in evidence_nodes):
        raise _error("accepted graph evidence role drifted")

    def matching_evidence(role: str, source_node: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        return [
            evidence
            for evidence in evidence_nodes
            if _evidence_role(evidence) == role and _same_source_ref(source_node, evidence)
        ]

    def exact_evidence(role: str, source_node: Mapping[str, Any]) -> Mapping[str, Any]:
        matches = matching_evidence(role, source_node)
        if len(matches) != 1:
            raise _error(f"accepted {role} evidence binding drifted")
        return matches[0]

    owner_evidence = exact_evidence("OWNER_LABEL", owner)
    branch_evidence = exact_evidence("BRANCH_LABEL", branch)
    if not _owner_matches(owner_evidence["attributes"]["raw_text"], spec.owner_aliases):
        raise _error("accepted owner evidence semantics drifted")
    if not _branch_matches(branch_evidence["attributes"]["raw_text"], spec.branch_aliases):
        raise _error("accepted branch evidence semantics drifted")
    axis_evidence_by_index = {
        axis_index: exact_evidence(f"AXIS_HEADER:{axis_index}", axis)
        for axis_index, axis in axis_by_index.items()
    }
    for axis_index, evidence in axis_evidence_by_index.items():
        if (
            parse_local_accounting_period_v1(evidence["attributes"]["raw_text"])
            != axis_by_index[axis_index]["attributes"]["period_label"]
        ):
            raise _error("accepted axis evidence semantics drifted")
    unit_evidence = exact_evidence("LOCAL_UNIT:0", context)
    if not same_typed_json_v1(
        parse_local_accounting_unit_v1(unit_evidence["attributes"]["raw_text"]),
        context["attributes"],
    ):
        raise _error("accepted unit evidence semantics drifted")

    row_evidence_by_id: dict[str, list[Mapping[str, Any]]] = {}
    value_evidence_by_id: dict[str, Mapping[str, Any]] = {}
    for row_index, row_id in enumerate(ordered_row_ids):
        row = node_by_id[row_id]
        row_role = row["attributes"]["family_row_role"]
        row_values = sorted(
            (value for value in values if value_owner[value["node_id"]] == row_id),
            key=lambda value: value["attributes"]["axis_index"],
        )
        value_evidence = []
        for value in row_values:
            axis_index = value["attributes"]["axis_index"]
            evidence = exact_evidence(f"VALUE_POSITION:{row_index}:{axis_index}", value)
            if not same_typed_json_v1(
                {
                    "raw_text": evidence["attributes"]["raw_text"],
                    "value_state": evidence["attributes"]["value_state"],
                },
                {
                    "raw_text": value["attributes"]["raw_text"],
                    "value_state": value["attributes"]["value_state"],
                },
            ):
                raise _error("accepted value evidence semantics drifted")
            value_evidence_by_id[value["node_id"]] = evidence
            value_evidence.append(evidence)
        row_label_matches = matching_evidence(f"ROW_LABEL:{row_index}", row)
        if row_label_matches:
            if len(row_label_matches) != 1 or (
                _row_role(row_label_matches[0]["attributes"]["raw_text"], spec) != row_role
            ):
                raise _error("accepted row-label evidence semantics drifted")
            row_evidence = row_label_matches
        else:
            if row_role != "TOTAL":
                raise _error("accepted non-total row lacks an exact visible label")
            value_boxes = [item["source_ref"]["canonical_bbox_mpt"] for item in value_evidence]
            value_atoms = sorted(
                {
                    atom_id
                    for item in value_evidence
                    for atom_id in item["source_ref"]["source_atom_ids"]
                }
            )
            if not same_typed_json_v1(
                row["source_ref"],
                {
                    "source_local_page_id": graph["source_local_page_id"],
                    "source_projection_sha256": graph["source_projection_sha256"],
                    "canonical_bbox_mpt": _union_box(value_boxes),
                    "source_atom_ids": value_atoms,
                },
            ):
                raise _error("accepted unlabeled-total source binding drifted")
            row_evidence = value_evidence
        row_evidence_by_id[row_id] = row_evidence

    accepted_evidence_by_id = {
        item["node_id"]: item
        for item in (
            owner_evidence,
            branch_evidence,
            unit_evidence,
            *axis_evidence_by_index.values(),
            *value_evidence_by_id.values(),
            *(item for group in row_evidence_by_id.values() for item in group),
        )
    }
    _, side_unresolved_reasons = _validate_unresolved_partitions(
        graph,
        node_by_id=node_by_id,
        permitted_other_evidence_ids=set(accepted_evidence_by_id),
    )
    if set(graph["unresolved_reasons"]) != side_unresolved_reasons:
        raise _error("accepted graph side-region reason accounting drifted")
    expected_table_source_ref = {
        "source_local_page_id": graph["source_local_page_id"],
        "source_projection_sha256": graph["source_projection_sha256"],
        "canonical_bbox_mpt": _union_box(
            [item["source_ref"]["canonical_bbox_mpt"] for item in accepted_evidence_by_id.values()]
        ),
        "source_atom_ids": sorted(
            {
                atom_id
                for item in accepted_evidence_by_id.values()
                for atom_id in item["source_ref"]["source_atom_ids"]
            }
        ),
    }
    if not same_typed_json_v1(table["source_ref"], expected_table_source_ref):
        raise _error("accepted table source-evidence union drifted")

    expected_edges: list[dict[str, Any]] = [
        _edge(
            AcceptedEdgeKindV1.OWNS,
            owner["node_id"],
            table["node_id"],
            [owner_evidence["node_id"]],
        ),
        _edge(
            AcceptedEdgeKindV1.PARENT_OF,
            owner["node_id"],
            branch["node_id"],
            [owner_evidence["node_id"], branch_evidence["node_id"]],
        ),
        _edge(
            AcceptedEdgeKindV1.SUPPORTED_BY,
            table["node_id"],
            owner_evidence["node_id"],
            list(accepted_evidence_by_id),
        ),
        _edge(
            AcceptedEdgeKindV1.SUPPORTED_BY,
            owner["node_id"],
            owner_evidence["node_id"],
            [owner_evidence["node_id"]],
        ),
        _edge(
            AcceptedEdgeKindV1.SUPPORTED_BY,
            branch["node_id"],
            branch_evidence["node_id"],
            [branch_evidence["node_id"]],
        ),
        _edge(
            AcceptedEdgeKindV1.SCOPED_BY,
            table["node_id"],
            context["node_id"],
            [unit_evidence["node_id"]],
        ),
        _edge(
            AcceptedEdgeKindV1.SUPPORTED_BY,
            context["node_id"],
            unit_evidence["node_id"],
            [unit_evidence["node_id"]],
        ),
    ]
    for axis_index, axis in axis_by_index.items():
        evidence = axis_evidence_by_index[axis_index]
        expected_edges.extend(
            (
                _edge(
                    AcceptedEdgeKindV1.CONTAINS,
                    table["node_id"],
                    axis["node_id"],
                    [evidence["node_id"]],
                ),
                _edge(
                    AcceptedEdgeKindV1.SUPPORTED_BY,
                    axis["node_id"],
                    evidence["node_id"],
                    [evidence["node_id"]],
                ),
            )
        )
    for row_id in ordered_row_ids:
        row = node_by_id[row_id]
        row_evidence_ids = [item["node_id"] for item in row_evidence_by_id[row_id]]
        expected_edges.extend(
            (
                _edge(
                    AcceptedEdgeKindV1.CONTAINS,
                    table["node_id"],
                    row_id,
                    row_evidence_ids,
                ),
                _edge(
                    AcceptedEdgeKindV1.PARENT_OF,
                    branch["node_id"],
                    row_id,
                    [branch_evidence["node_id"], *row_evidence_ids],
                ),
                _edge(
                    AcceptedEdgeKindV1.SUPPORTED_BY,
                    row_id,
                    row_evidence_ids[0],
                    row_evidence_ids,
                ),
            )
        )
        row_values = sorted(
            (value for value in values if value_owner[value["node_id"]] == row_id),
            key=lambda value: value["attributes"]["axis_index"],
        )
        for value in row_values:
            axis_index = value["attributes"]["axis_index"]
            value_evidence = value_evidence_by_id[value["node_id"]]
            axis_evidence = axis_evidence_by_index[axis_index]
            expected_edges.extend(
                (
                    _edge(
                        AcceptedEdgeKindV1.CONTAINS,
                        row_id,
                        value["node_id"],
                        [*row_evidence_ids, value_evidence["node_id"]],
                    ),
                    _edge(
                        AcceptedEdgeKindV1.ALIGNED_TO_AXIS,
                        value["node_id"],
                        axis_by_index[axis_index]["node_id"],
                        [value_evidence["node_id"], axis_evidence["node_id"]],
                    ),
                    _edge(
                        AcceptedEdgeKindV1.SUPPORTED_BY,
                        value["node_id"],
                        value_evidence["node_id"],
                        [value_evidence["node_id"]],
                    ),
                )
            )
    for left_id, right_id in zip(ordered_row_ids, ordered_row_ids[1:], strict=False):
        expected_edges.append(
            _edge(
                AcceptedEdgeKindV1.NEXT_SIBLING,
                left_id,
                right_id,
                [
                    *(item["node_id"] for item in row_evidence_by_id[left_id]),
                    *(item["node_id"] for item in row_evidence_by_id[right_id]),
                ],
            )
        )
    total_id = row_by_role["TOTAL"]["node_id"]
    for role in expected_total_children:
        child_id = row_by_role[role]["node_id"]
        expected_edges.append(
            _edge(
                AcceptedEdgeKindV1.TOTAL_OF,
                total_id,
                child_id,
                [
                    *(item["node_id"] for item in row_evidence_by_id[child_id]),
                    *(item["node_id"] for item in row_evidence_by_id[total_id]),
                ],
            )
        )
    accepted_node_ids = {node["node_id"] for node in accepted_non_evidence}
    actual_accepted_edges = sorted(
        (edge for edge in edges if edge["from_node_id"] in accepted_node_ids),
        key=lambda edge: edge["edge_id"],
    )
    expected_edges = sorted(expected_edges, key=lambda edge: edge["edge_id"])
    if not same_typed_json_v1(actual_accepted_edges, expected_edges):
        raise _error("accepted graph edge topology/provenance drifted")

    allowed_endpoint_kinds = {
        AcceptedEdgeKindV1.OWNS.value: {("ACCOUNTING_ROLE", "TABLE")},
        AcceptedEdgeKindV1.PARENT_OF.value: {
            ("ACCOUNTING_ROLE", "ACCOUNTING_ROLE"),
            ("ACCOUNTING_ROLE", "LOGICAL_ROW"),
        },
        AcceptedEdgeKindV1.CONTAINS.value: {
            ("TABLE", "AXIS"),
            ("TABLE", "LOGICAL_ROW"),
            ("LOGICAL_ROW", "VALUE_POSITION"),
        },
        AcceptedEdgeKindV1.ALIGNED_TO_AXIS.value: {("VALUE_POSITION", "AXIS")},
        AcceptedEdgeKindV1.SCOPED_BY.value: {("TABLE", "CONTEXT")},
        AcceptedEdgeKindV1.TOTAL_OF.value: {("LOGICAL_ROW", "LOGICAL_ROW")},
        AcceptedEdgeKindV1.NEXT_SIBLING.value: {("LOGICAL_ROW", "LOGICAL_ROW")},
        AcceptedEdgeKindV1.SUPPORTED_BY.value: {
            (kind.value, "EVIDENCE")
            for kind in AcceptedNodeKindV1
            if kind is not AcceptedNodeKindV1.EVIDENCE
        },
    }
    for edge in edges:
        endpoints = (
            node_by_id[edge["from_node_id"]]["kind"],
            node_by_id[edge["to_node_id"]]["kind"],
        )
        if endpoints not in allowed_endpoint_kinds[edge["kind"]]:
            raise _error("accepted graph edge kind/direction drifted")


def validate_local_accounting_graph_v1(value: Any) -> dict[str, Any]:
    """Validate exact fields, source bindings, identities, and fail-closed counts."""

    graph = _exact_dict(value, _GRAPH_FIELDS, "local accounting graph")
    if graph["format_version"] != LOCAL_ACCOUNTING_GRAPH_FORMAT_VERSION_V1:
        raise _error("graph format version drifted")
    if graph["claim_boundary"] != LOCAL_ACCOUNTING_GRAPH_CLAIM_BOUNDARY_V1:
        raise _error("graph claim boundary drifted")
    try:
        status = GraphStatusV1(graph["status"])
    except (TypeError, ValueError) as error:
        raise _error("graph status drifted") from error
    if type(graph["family_id"]) is not str or _ROLE_RE.fullmatch(graph["family_id"]) is None:
        raise _error("graph family identity drifted")
    expected_spec_sha256 = _FROZEN_FAMILY_SPEC_SHA256_BY_ID.get(graph["family_id"])
    if (
        expected_spec_sha256 is None
        or type(graph["family_spec_sha256"]) is not str
        or _SHA256_RE.fullmatch(graph["family_spec_sha256"]) is None
        or graph["family_spec_sha256"] != expected_spec_sha256
    ):
        raise _error("graph family spec identity drifted")
    if (
        type(graph["source_local_page_id"]) is not str
        or _PAGE_ID_RE.fullmatch(graph["source_local_page_id"]) is None
    ):
        raise _error("graph source-local page identity drifted")
    for field in ("source_projection_sha256", "source_observation_sha256"):
        if type(graph[field]) is not str or _SHA256_RE.fullmatch(graph[field]) is None:
            raise _error(f"graph {field} drifted")
    if not same_typed_json_v1(graph["safety"], LOCAL_ACCOUNTING_GRAPH_SAFETY_V1):
        raise _error("graph safety policy drifted")
    if type(graph["nodes"]) is not list or graph["nodes"] != sorted(
        graph["nodes"], key=lambda item: item.get("node_id", "")
    ):
        raise _error("graph nodes must be in canonical identity order")
    node_by_id = {}
    for index, node_value in enumerate(graph["nodes"]):
        node = _exact_dict(node_value, _NODE_FIELDS, f"node {index}")
        if type(node["node_id"]) is not str or _NODE_ID_RE.fullmatch(node["node_id"]) is None:
            raise _error(f"node {index} identity drifted")
        try:
            kind = AcceptedNodeKindV1(node["kind"])
        except (TypeError, ValueError) as error:
            raise _error(f"node {index} kind drifted") from error
        source_ref = _exact_dict(node["source_ref"], _SOURCE_REF_FIELDS, f"node {index} source ref")
        if (
            source_ref["source_local_page_id"] != graph["source_local_page_id"]
            or source_ref["source_projection_sha256"] != graph["source_projection_sha256"]
        ):
            raise _error(f"node {index} source binding drifted")
        _bbox(source_ref["canonical_bbox_mpt"], f"node {index} source bbox")
        _atom_ids(source_ref["source_atom_ids"], f"node {index} atom ids", allow_empty=True)
        if type(node["attributes"]) is not dict:
            raise _error(f"node {index} attributes drifted")
        if (
            type(node["unresolved_reasons"]) is not list
            or node["unresolved_reasons"] != sorted(set(node["unresolved_reasons"]))
            or any(type(reason) is not str or not reason for reason in node["unresolved_reasons"])
        ):
            raise _error(f"node {index} unresolved reasons drifted")
        if kind is AcceptedNodeKindV1.UNRESOLVED_REGION:
            if (
                node["status"] != "EXPLICIT_UNRESOLVED"
                or not node["unresolved_reasons"]
                or not set(node["unresolved_reasons"]).issubset(_UNRESOLVED_REASON_CODES_V1)
            ):
                raise _error(f"node {index} unresolved status drifted")
        elif kind is AcceptedNodeKindV1.EVIDENCE:
            if node["status"] != "BOUND_SOURCE_EVIDENCE" or node["unresolved_reasons"]:
                raise _error(f"node {index} evidence status drifted")
            _validate_evidence_node(node)
        elif node["status"] != "ACCEPTED_SOURCE_STRUCTURE" or node["unresolved_reasons"]:
            raise _error(f"node {index} accepted status drifted")
        identity_payload = {key: node[key] for key in node if key != "node_id"}
        if node["node_id"] != "lagv1:node:" + canonical_json_sha256_v1(identity_payload):
            raise _error(f"node {index} content identity drifted")
        if node["node_id"] in node_by_id:
            raise _error("graph repeats a node identity")
        node_by_id[node["node_id"]] = node

    if type(graph["edges"]) is not list or graph["edges"] != sorted(
        graph["edges"], key=lambda item: item.get("edge_id", "")
    ):
        raise _error("graph edges must be in canonical identity order")
    edge_ids = set()
    for index, edge_value in enumerate(graph["edges"]):
        edge = _exact_dict(edge_value, _EDGE_FIELDS, f"edge {index}")
        if type(edge["edge_id"]) is not str or _EDGE_ID_RE.fullmatch(edge["edge_id"]) is None:
            raise _error(f"edge {index} identity drifted")
        try:
            AcceptedEdgeKindV1(edge["kind"])
        except (TypeError, ValueError) as error:
            raise _error(f"edge {index} kind drifted") from error
        if edge["from_node_id"] not in node_by_id or edge["to_node_id"] not in node_by_id:
            raise _error(f"edge {index} references an unknown node")
        if (
            type(edge["evidence_node_ids"]) is not list
            or not edge["evidence_node_ids"]
            or edge["evidence_node_ids"] != sorted(set(edge["evidence_node_ids"]))
            or any(
                evidence_id not in node_by_id
                or node_by_id[evidence_id]["kind"] != AcceptedNodeKindV1.EVIDENCE.value
                for evidence_id in edge["evidence_node_ids"]
            )
        ):
            raise _error(f"edge {index} evidence binding drifted")
        identity_payload = {key: edge[key] for key in edge if key != "edge_id"}
        if edge["edge_id"] != "lagv1:edge:" + canonical_json_sha256_v1(identity_payload):
            raise _error(f"edge {index} content identity drifted")
        if edge["edge_id"] in edge_ids:
            raise _error("graph repeats an edge identity")
        edge_ids.add(edge["edge_id"])

    if status is GraphStatusV1.CORE_ACCEPTED:
        _validate_accepted_topology(graph, node_by_id=node_by_id)
    else:
        if any(
            node["kind"]
            not in {
                AcceptedNodeKindV1.EVIDENCE.value,
                AcceptedNodeKindV1.UNRESOLVED_REGION.value,
            }
            for node in graph["nodes"]
        ) or any(
            edge["kind"] != AcceptedEdgeKindV1.SUPPORTED_BY.value
            or node_by_id[edge["from_node_id"]]["kind"]
            != AcceptedNodeKindV1.UNRESOLVED_REGION.value
            or node_by_id[edge["to_node_id"]]["kind"] != AcceptedNodeKindV1.EVIDENCE.value
            for edge in graph["edges"]
        ):
            raise _error("explicit unresolved graph topology drifted")
        _, region_reasons = _validate_unresolved_partitions(
            graph,
            node_by_id=node_by_id,
            permitted_other_evidence_ids=set(),
        )
        expected_reasons = set(region_reasons)
        if "MULTIPLE_COMPLETE_MATCHES" not in expected_reasons:
            expected_reasons.add("NO_COMPLETE_MATCH")
        if set(graph["unresolved_reasons"]) != expected_reasons:
            raise _error("explicit unresolved reason accounting drifted")

    counts = _exact_dict(graph["accepted_counts"], _ACCEPTED_COUNTS_FIELDS, "accepted counts")
    if any(type(count) is not int or count < 0 for count in counts.values()):
        raise _error("accepted counts drifted")
    expected_counts = {
        "TABLE": sum(
            node["kind"] == AcceptedNodeKindV1.TABLE.value
            and node["status"] == "ACCEPTED_SOURCE_STRUCTURE"
            for node in graph["nodes"]
        ),
        "LOGICAL_ROW": sum(
            node["kind"] == AcceptedNodeKindV1.LOGICAL_ROW.value
            and node["status"] == "ACCEPTED_SOURCE_STRUCTURE"
            for node in graph["nodes"]
        ),
        "VALUE_POSITION": sum(
            node["kind"] == AcceptedNodeKindV1.VALUE_POSITION.value
            and node["status"] == "ACCEPTED_SOURCE_STRUCTURE"
            for node in graph["nodes"]
        ),
        "AXIS": sum(
            node["kind"] == AcceptedNodeKindV1.AXIS.value
            and node["status"] == "ACCEPTED_SOURCE_STRUCTURE"
            for node in graph["nodes"]
        ),
        "HIERARCHY": sum(edge["kind"] in _HIERARCHY_EDGES for edge in graph["edges"]),
    }
    if not same_typed_json_v1(counts, expected_counts):
        raise _error("accepted counts disagree with graph contents")
    if (
        type(graph["unresolved_reasons"]) is not list
        or graph["unresolved_reasons"] != sorted(set(graph["unresolved_reasons"]))
        or any(type(reason) is not str or not reason for reason in graph["unresolved_reasons"])
        or not set(graph["unresolved_reasons"]).issubset(_UNRESOLVED_REASON_CODES_V1)
    ):
        raise _error("graph unresolved reasons drifted")
    arithmetic = graph["arithmetic_check"]
    if (
        type(arithmetic) is not dict
        or set(arithmetic) != {"status", "evaluated_axis_indexes"}
        or arithmetic["status"]
        not in {
            "NOT_APPLICABLE",
            "NOT_EVALUABLE",
            "CORROBORATED",
            "VETOED",
        }
        or type(arithmetic["evaluated_axis_indexes"]) is not list
        or arithmetic["evaluated_axis_indexes"] != sorted(set(arithmetic["evaluated_axis_indexes"]))
    ):
        raise _error("graph arithmetic check drifted")
    axis_count = _FROZEN_FAMILY_SPEC_BY_ID[
        graph["family_id"]
    ].axis_layout.comparative_monetary_period_count
    evaluated_axes = arithmetic["evaluated_axis_indexes"]
    if any(type(index) is not int or not 0 <= index < axis_count for index in evaluated_axes):
        raise _error("graph arithmetic axis identity drifted")
    if arithmetic["status"] == "CORROBORATED" and evaluated_axes != list(range(axis_count)):
        raise _error("corroborated arithmetic must cover every accepted axis")
    if arithmetic["status"] == "VETOED" and not evaluated_axes:
        raise _error("vetoed arithmetic must identify an evaluated axis")
    accepted = status is GraphStatusV1.CORE_ACCEPTED
    if arithmetic["status"] == "NOT_APPLICABLE" and accepted:
        raise _error("accepted graph arithmetic cannot be not applicable")
    if graph["canonicalization_eligible"] is not False:
        raise _error("LAG v1 lacks accepted statement/scope and cannot authorize canonicalization")
    if graph["export_eligible"] is not False:
        raise _error("LAG v1 cannot independently authorize export")
    if accepted != (counts["TABLE"] == 1):
        raise _error("graph status disagrees with unique table acceptance")
    if not accepted and any(counts.values()):
        raise _error("unresolved graph contains accepted structure")
    identity_payload = {key: graph[key] for key in graph if key != "graph_identity"}
    if (
        type(graph["graph_identity"]) is not str
        or _GRAPH_ID_RE.fullmatch(graph["graph_identity"]) is None
        or graph["graph_identity"] != "lagv1:graph:" + canonical_json_sha256_v1(identity_payload)
    ):
        raise _error("graph content identity drifted")
    return canonical_clone_v1(graph)
