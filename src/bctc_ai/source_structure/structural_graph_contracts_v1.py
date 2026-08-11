"""Closed page-local contract for pre-structural graph candidates.

This boundary is deliberately narrower than statement or table discovery.  It
binds candidate nodes to one authenticated V2 source projection and its V2
geometry proposals, accounts every source atom exactly once, and keeps all
candidate structure inside an explicit unresolved region.  It makes no
statement type, accounting, value, period, unit, scope, hierarchy, schema, or
absence claim.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from enum import StrEnum
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

__all__ = [
    "ATOM_GRAPH_DISPOSITION_FORMAT_VERSION_V1",
    "PAGE_PRESTRUCTURAL_GRAPH_CLAIM_BOUNDARY_V1",
    "PAGE_PRESTRUCTURAL_GRAPH_FORMAT_VERSION_V1",
    "PAGE_PRESTRUCTURAL_GRAPH_SAFETY_V1",
    "PAGE_PRESTRUCTURAL_GRAPH_STATUS_V1",
    "AtomGraphDispositionV1",
    "GraphEdgeKindV1",
    "GraphNodeKindV1",
    "GraphNodeStatusV1",
    "PrestructuralGraphContractError",
    "make_atom_graph_disposition_v1",
    "make_graph_edge_v1",
    "make_graph_node_v1",
    "make_page_prestructural_graph_v1",
    "validate_page_prestructural_graph_v1",
]


class PrestructuralGraphContractError(ValueError):
    """A page graph crossed its closed pre-structural boundary."""


class GraphNodeKindV1(StrEnum):
    DOCUMENT = "DOCUMENT"
    PAGE = "PAGE"
    STATEMENT_BLOCK = "STATEMENT_BLOCK"
    TABLE = "TABLE"
    ROW = "ROW"
    CELL_OR_VALUE_POSITION = "CELL_OR_VALUE_POSITION"
    AXIS_OR_DIMENSION = "AXIS_OR_DIMENSION"
    EVIDENCE = "EVIDENCE"
    UNRESOLVED_REGION = "UNRESOLVED_REGION"


class GraphNodeStatusV1(StrEnum):
    BOUND_SOURCE_CONTEXT = "BOUND_SOURCE_CONTEXT"
    BOUND_SOURCE_EVIDENCE = "BOUND_SOURCE_EVIDENCE"
    PRESTRUCTURAL_CANDIDATE = "PRESTRUCTURAL_CANDIDATE"
    EXPLICIT_UNRESOLVED = "EXPLICIT_UNRESOLVED"


class GraphEdgeKindV1(StrEnum):
    PRESTRUCTURAL_CONTAINS = "PRESTRUCTURAL_CONTAINS"
    PRECEDES_IN_AUTHENTICATED_SOURCE_ORDER = "PRECEDES_IN_AUTHENTICATED_SOURCE_ORDER"
    SUPPORTS = "SUPPORTS"
    PRESTRUCTURAL_ALIGNED_TO_AXIS = "PRESTRUCTURAL_ALIGNED_TO_AXIS"


class AtomGraphDispositionV1(StrEnum):
    SUPPORTS_PRESTRUCTURAL_CANDIDATE = "SUPPORTS_PRESTRUCTURAL_CANDIDATE"
    RETAINED_UNRESOLVED = "RETAINED_UNRESOLVED"
    UPSTREAM_TERMINAL_UNRESOLVED = "UPSTREAM_TERMINAL_UNRESOLVED"
    UPSTREAM_QUARANTINED = "UPSTREAM_QUARANTINED"


PAGE_PRESTRUCTURAL_GRAPH_FORMAT_VERSION_V1 = "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_PRESTRUCTURAL_GRAPH_V1"
PAGE_PRESTRUCTURAL_GRAPH_CLAIM_BOUNDARY_V1 = (
    "BOUND_SOURCE_GEOMETRY_CANDIDATES_AND_EXPLICIT_UNRESOLVED_REGIONS_ONLY_"
    "NO_ACCEPTED_STATEMENT_TABLE_ROW_CELL_AXIS_OR_ACCOUNTING_CLAIM"
)
PAGE_PRESTRUCTURAL_GRAPH_STATUS_V1 = "PARTIAL_PRESTRUCTURAL_CANDIDATES"
ATOM_GRAPH_DISPOSITION_FORMAT_VERSION_V1 = (
    "BANK_CORPUS_WAVE_1_ROLE_B_ATOM_PRESTRUCTURAL_DISPOSITION_V1"
)

PAGE_PRESTRUCTURAL_GRAPH_SAFETY_V1: dict[str, bool] = {
    "prestructural_candidates_only": True,
    "candidate_relations_only": True,
    "statement_claimed": False,
    "table_claimed": False,
    "logical_rows_claimed": False,
    "financial_cells_claimed": False,
    "period_axis_claimed": False,
    "unit_axis_claimed": False,
    "scope_claimed": False,
    "hierarchy_claimed": False,
    "accepted_hierarchy_claimed": False,
    "value_claimed": False,
    "blank_claimed": False,
    "absence_claimed": False,
    "bank_identity_used_for_routing": False,
    "filename_identity_used_for_routing": False,
    "note_number_rules_used_for_routing": False,
    "page_number_rules_used_for_routing": False,
    "role_a_used_for_routing": False,
    "schema_used_for_routing": False,
    "historical_values_used": False,
}

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_NODE_ID_RE = re.compile(r"^ssgv1:node:[0-9a-f]{64}$")
_EDGE_ID_RE = re.compile(r"^ssgv1:edge:[0-9a-f]{64}$")
_GRAPH_ID_RE = re.compile(r"^ssgv1:graph:[0-9a-f]{64}$")
_SOURCE_OBJECT_ID_RE = re.compile(r"^ssv1:[a-z][a-z0-9_]{0,39}:[0-9a-f]{64}$")
_SOURCE_PAGE_ID_RE = re.compile(r"^ssv2:page:[0-9a-f]{64}$")

_GRAPH_FIELDS = {
    "format_version",
    "claim_boundary",
    "status",
    "source_local_page_id",
    "source_projection_sha256",
    "source_proposal_projection_sha256",
    "nodes",
    "edges",
    "atom_dispositions",
    "metrics",
    "safety",
    "graph_identity",
}
_NODE_FIELDS = {
    "node_id",
    "ordinal",
    "kind",
    "status",
    "source_binding_sha256",
    "canonical_bbox_mpt",
    "source_atom_ids",
    "source_proposal_ids",
}
_EDGE_FIELDS = {"edge_id", "ordinal", "kind", "from_node_id", "to_node_id"}
_DISPOSITION_FIELDS = {
    "format_version",
    "source_atom_id",
    "evidence_node_id",
    "primary_disposition",
    "owner_node_id",
    "reason_code",
    "upstream_disposition_sha256",
}
_METRIC_FIELDS = {
    "atom_count",
    "node_counts",
    "edge_counts",
    "disposition_counts",
}

_CANDIDATE_KINDS = {
    GraphNodeKindV1.TABLE.value,
    GraphNodeKindV1.ROW.value,
    GraphNodeKindV1.CELL_OR_VALUE_POSITION.value,
    GraphNodeKindV1.AXIS_OR_DIMENSION.value,
}
_EXPECTED_STATUS = {
    GraphNodeKindV1.DOCUMENT.value: GraphNodeStatusV1.BOUND_SOURCE_CONTEXT.value,
    GraphNodeKindV1.PAGE.value: GraphNodeStatusV1.BOUND_SOURCE_CONTEXT.value,
    GraphNodeKindV1.TABLE.value: GraphNodeStatusV1.PRESTRUCTURAL_CANDIDATE.value,
    GraphNodeKindV1.ROW.value: GraphNodeStatusV1.PRESTRUCTURAL_CANDIDATE.value,
    GraphNodeKindV1.CELL_OR_VALUE_POSITION.value: (GraphNodeStatusV1.PRESTRUCTURAL_CANDIDATE.value),
    GraphNodeKindV1.AXIS_OR_DIMENSION.value: (GraphNodeStatusV1.PRESTRUCTURAL_CANDIDATE.value),
    GraphNodeKindV1.EVIDENCE.value: GraphNodeStatusV1.BOUND_SOURCE_EVIDENCE.value,
    GraphNodeKindV1.UNRESOLVED_REGION.value: GraphNodeStatusV1.EXPLICIT_UNRESOLVED.value,
}
_REASON_BY_DISPOSITION = {
    AtomGraphDispositionV1.SUPPORTS_PRESTRUCTURAL_CANDIDATE.value: (
        "PRIMARY_SOURCE_EVIDENCE_SUPPORTS_CANDIDATE"
    ),
    AtomGraphDispositionV1.RETAINED_UNRESOLVED.value: (
        "SOURCE_EVIDENCE_RETAINED_WITHOUT_STRUCTURAL_PROMOTION"
    ),
    AtomGraphDispositionV1.UPSTREAM_TERMINAL_UNRESOLVED.value: (
        "UPSTREAM_TERMINAL_SOURCE_EVIDENCE_RETAINED"
    ),
    AtomGraphDispositionV1.UPSTREAM_QUARANTINED.value: (
        "UPSTREAM_QUARANTINE_RETAINED_OUTSIDE_PRIMARY_STRUCTURE"
    ),
}


def _error(message: str) -> PrestructuralGraphContractError:
    return PrestructuralGraphContractError(message)


def _exact_dict(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise _error(f"{label} field set drifted")
    return value


def _positive(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} must be a positive integer")
    return value


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise _error(f"{label} is not a canonical SHA-256 digest")
    return value


def _sorted_unique_ids(value: Any, label: str) -> list[str]:
    if (
        type(value) is not list
        or any(
            type(item) is not str or _SOURCE_OBJECT_ID_RE.fullmatch(item) is None for item in value
        )
        or value != sorted(set(value))
    ):
        raise _error(f"{label} must be sorted unique source-object identities")
    return value


def _bbox(value: Any, label: str) -> list[int] | None:
    if value is None:
        return None
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(coordinate) is not int for coordinate in value)
        or value[0] >= value[2]
        or value[1] >= value[3]
    ):
        raise _error(f"{label} must be null or one positive canonical mpt box")
    return value


def _box_contains(outer: Sequence[int], inner: Sequence[int]) -> bool:
    return (
        outer[0] <= inner[0]
        and outer[1] <= inner[1]
        and inner[2] <= outer[2]
        and inner[3] <= outer[3]
    )


def _box_union(boxes: Sequence[Sequence[int]]) -> list[int]:
    if not boxes:
        raise _error("cannot derive a bounding box from no source boxes")
    return [
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    ]


def _x_ranges_overlap(left: Sequence[int], right: Sequence[int]) -> bool:
    return max(left[0], right[0]) < min(left[2], right[2])


def _node_identity_payload(node: Mapping[str, Any]) -> dict[str, Any]:
    return {key: node[key] for key in node if key not in {"node_id", "ordinal"}}


def _derived_node_source_binding(
    *,
    source_local_page_id: str,
    kind: str,
    canonical_bbox_mpt: Sequence[int] | None,
    source_atom_ids: Sequence[str],
    source_proposal_ids: Sequence[str],
) -> str:
    return canonical_json_sha256_v1(
        {
            "source_local_page_id": source_local_page_id,
            "kind": kind,
            "canonical_bbox_mpt": (
                list(canonical_bbox_mpt) if canonical_bbox_mpt is not None else None
            ),
            "source_atom_ids": sorted(source_atom_ids),
            "source_proposal_ids": sorted(source_proposal_ids),
        }
    )


def make_graph_node_v1(
    *,
    ordinal: int,
    kind: GraphNodeKindV1 | str,
    status: GraphNodeStatusV1 | str,
    source_binding_sha256: str | None = None,
    source_local_page_id: str | None = None,
    canonical_bbox_mpt: Sequence[int] | None = None,
    source_atom_ids: Sequence[str] = (),
    source_proposal_ids: Sequence[str] = (),
) -> dict[str, Any]:
    """Build one content-bound node without interpreting source text."""

    kind_value = str(kind)
    bbox_value = list(canonical_bbox_mpt) if canonical_bbox_mpt is not None else None
    atom_ids = sorted(source_atom_ids)
    proposal_ids = sorted(source_proposal_ids)
    is_context = kind_value in {GraphNodeKindV1.DOCUMENT.value, GraphNodeKindV1.PAGE.value}
    if not is_context:
        if (
            type(source_local_page_id) is not str
            or _SOURCE_PAGE_ID_RE.fullmatch(source_local_page_id) is None
        ):
            raise _error("non-context nodes require the authenticated source page identity")
        expected_binding = _derived_node_source_binding(
            source_local_page_id=source_local_page_id,
            kind=kind_value,
            canonical_bbox_mpt=bbox_value,
            source_atom_ids=atom_ids,
            source_proposal_ids=proposal_ids,
        )
        if source_binding_sha256 is None:
            source_binding_sha256 = expected_binding
        elif source_binding_sha256 != expected_binding:
            raise _error("non-context node source binding drifted from cited evidence")
    elif source_binding_sha256 is None:
        raise _error("source-context nodes require an authenticated external binding")
    value: dict[str, Any] = {
        "ordinal": ordinal,
        "kind": kind_value,
        "status": str(status),
        "source_binding_sha256": source_binding_sha256,
        "canonical_bbox_mpt": bbox_value,
        "source_atom_ids": atom_ids,
        "source_proposal_ids": proposal_ids,
    }
    value["node_id"] = f"ssgv1:node:{canonical_json_sha256_v1(_node_identity_payload(value))}"
    return _validate_node_shape(value)


def _validate_node_shape(value: Any) -> dict[str, Any]:
    node = _exact_dict(value, _NODE_FIELDS, "pre-structural graph node")
    _positive(node["ordinal"], "node ordinal")
    try:
        kind = GraphNodeKindV1(node["kind"])
    except (TypeError, ValueError) as exc:
        raise _error("pre-structural graph node kind drifted") from exc
    if kind is GraphNodeKindV1.STATEMENT_BLOCK:
        raise _error("statement-block nodes require separate statement evidence authority")
    if node["status"] != _EXPECTED_STATUS[kind.value]:
        raise _error("pre-structural graph node status drifted")
    _sha(node["source_binding_sha256"], "node source binding")
    bbox = _bbox(node["canonical_bbox_mpt"], "node bounding box")
    atoms = _sorted_unique_ids(node["source_atom_ids"], "node source atom IDs")
    proposals = _sorted_unique_ids(node["source_proposal_ids"], "node proposal IDs")
    if kind in {GraphNodeKindV1.DOCUMENT, GraphNodeKindV1.PAGE}:
        if bbox is not None or atoms or proposals:
            raise _error("source-context nodes cannot promote atom/proposal evidence")
    else:
        if kind is GraphNodeKindV1.EVIDENCE:
            if len(atoms) != 1 or proposals:
                raise _error("each evidence node must bind exactly one source atom")
        elif kind is GraphNodeKindV1.UNRESOLVED_REGION:
            if proposals:
                raise _error("unresolved regions cannot cite geometry proposals directly")
        elif kind.value in _CANDIDATE_KINDS and (bbox is None or not atoms or not proposals):
            raise _error("candidate nodes require atoms, a box, and geometry proposals")
    if (
        type(node["node_id"]) is not str
        or _NODE_ID_RE.fullmatch(node["node_id"]) is None
        or node["node_id"] != f"ssgv1:node:{canonical_json_sha256_v1(_node_identity_payload(node))}"
    ):
        raise _error("pre-structural graph node identity drifted")
    return canonical_clone_v1(node)


def make_graph_edge_v1(
    *, ordinal: int, kind: GraphEdgeKindV1 | str, from_node_id: str, to_node_id: str
) -> dict[str, Any]:
    """Build one content-bound graph edge."""

    value: dict[str, Any] = {
        "ordinal": ordinal,
        "kind": str(kind),
        "from_node_id": from_node_id,
        "to_node_id": to_node_id,
    }
    value["edge_id"] = f"ssgv1:edge:{canonical_json_sha256_v1(value)}"
    return _validate_edge_shape(value)


def _validate_edge_shape(value: Any) -> dict[str, Any]:
    edge = _exact_dict(value, _EDGE_FIELDS, "pre-structural graph edge")
    _positive(edge["ordinal"], "edge ordinal")
    try:
        GraphEdgeKindV1(edge["kind"])
    except (TypeError, ValueError) as exc:
        raise _error("pre-structural graph edge kind drifted") from exc
    for field in ("from_node_id", "to_node_id"):
        if type(edge[field]) is not str or _NODE_ID_RE.fullmatch(edge[field]) is None:
            raise _error("pre-structural graph edge endpoint drifted")
    expected = f"ssgv1:edge:{canonical_json_sha256_v1({key: edge[key] for key in edge if key != 'edge_id'})}"
    if (
        type(edge["edge_id"]) is not str
        or _EDGE_ID_RE.fullmatch(edge["edge_id"]) is None
        or edge["edge_id"] != expected
    ):
        raise _error("pre-structural graph edge identity drifted")
    return canonical_clone_v1(edge)


def make_atom_graph_disposition_v1(
    *,
    source_atom_id: str,
    upstream_disposition: Mapping[str, Any],
    evidence_node_id: str,
    primary_disposition: AtomGraphDispositionV1 | str,
    owner_node_id: str,
) -> dict[str, Any]:
    """Build one exact primary disposition for one authenticated source atom."""

    disposition = str(primary_disposition)
    try:
        AtomGraphDispositionV1(disposition)
    except ValueError as exc:
        raise _error("atom graph disposition drifted") from exc
    return _validate_disposition_shape(
        {
            "format_version": ATOM_GRAPH_DISPOSITION_FORMAT_VERSION_V1,
            "source_atom_id": source_atom_id,
            "evidence_node_id": evidence_node_id,
            "primary_disposition": disposition,
            "owner_node_id": owner_node_id,
            "reason_code": _REASON_BY_DISPOSITION[disposition],
            "upstream_disposition_sha256": canonical_json_sha256_v1(upstream_disposition),
        }
    )


def _validate_disposition_shape(value: Any) -> dict[str, Any]:
    item = _exact_dict(value, _DISPOSITION_FIELDS, "atom graph disposition")
    if item["format_version"] != ATOM_GRAPH_DISPOSITION_FORMAT_VERSION_V1:
        raise _error("atom graph disposition format drifted")
    if (
        type(item["source_atom_id"]) is not str
        or _SOURCE_OBJECT_ID_RE.fullmatch(item["source_atom_id"]) is None
    ):
        raise _error("atom graph source identity drifted")
    for field in ("evidence_node_id", "owner_node_id"):
        if type(item[field]) is not str or _NODE_ID_RE.fullmatch(item[field]) is None:
            raise _error("atom graph disposition owner identity drifted")
    try:
        disposition = AtomGraphDispositionV1(item["primary_disposition"])
    except (TypeError, ValueError) as exc:
        raise _error("atom graph primary disposition drifted") from exc
    if item["reason_code"] != _REASON_BY_DISPOSITION[disposition.value]:
        raise _error("atom graph disposition reason drifted")
    _sha(item["upstream_disposition_sha256"], "upstream atom disposition binding")
    return canonical_clone_v1(item)


def _metrics(
    nodes: Sequence[Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
    dispositions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    node_counts = Counter(node["kind"] for node in nodes)
    edge_counts = Counter(edge["kind"] for edge in edges)
    disposition_counts = Counter(item["primary_disposition"] for item in dispositions)
    return {
        "atom_count": len(dispositions),
        "node_counts": {kind.value: node_counts[kind.value] for kind in GraphNodeKindV1},
        "edge_counts": {kind.value: edge_counts[kind.value] for kind in GraphEdgeKindV1},
        "disposition_counts": {
            kind.value: disposition_counts[kind.value] for kind in AtomGraphDispositionV1
        },
    }


def make_page_prestructural_graph_v1(
    projection: Mapping[str, Any],
    proposal_projection: Mapping[str, Any],
    *,
    nodes: Sequence[Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
    atom_dispositions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Bind one page-local candidate graph to authenticated source evidence."""

    source = validate_source_evidence_projection_v2(projection)
    proposals = validate_page_proposal_set_v2(proposal_projection, projection=source)
    validated_nodes = [_validate_node_shape(node) for node in nodes]
    validated_edges = [_validate_edge_shape(edge) for edge in edges]
    validated_dispositions = [_validate_disposition_shape(item) for item in atom_dispositions]
    graph: dict[str, Any] = {
        "format_version": PAGE_PRESTRUCTURAL_GRAPH_FORMAT_VERSION_V1,
        "claim_boundary": PAGE_PRESTRUCTURAL_GRAPH_CLAIM_BOUNDARY_V1,
        "status": PAGE_PRESTRUCTURAL_GRAPH_STATUS_V1,
        "source_local_page_id": source["source_local_page_id"],
        "source_projection_sha256": canonical_json_sha256_v1(source),
        "source_proposal_projection_sha256": canonical_json_sha256_v1(proposals),
        "nodes": validated_nodes,
        "edges": validated_edges,
        "atom_dispositions": validated_dispositions,
        "metrics": _metrics(validated_nodes, validated_edges, validated_dispositions),
        "safety": canonical_clone_v1(PAGE_PRESTRUCTURAL_GRAPH_SAFETY_V1),
    }
    graph["graph_identity"] = f"ssgv1:graph:{canonical_json_sha256_v1(graph)}"
    return validate_page_prestructural_graph_v1(
        graph,
        projection=source,
        proposal_projection=proposals,
    )


def validate_page_prestructural_graph_v1(
    value: Any,
    *,
    projection: Mapping[str, Any],
    proposal_projection: Mapping[str, Any],
) -> dict[str, Any]:
    """Strictly replay one page graph against its source/proposal authority."""

    source = validate_source_evidence_projection_v2(projection)
    proposals = validate_page_proposal_set_v2(proposal_projection, projection=source)
    graph = _exact_dict(value, _GRAPH_FIELDS, "page pre-structural graph")
    if (
        graph["format_version"] != PAGE_PRESTRUCTURAL_GRAPH_FORMAT_VERSION_V1
        or graph["claim_boundary"] != PAGE_PRESTRUCTURAL_GRAPH_CLAIM_BOUNDARY_V1
        or graph["status"] != PAGE_PRESTRUCTURAL_GRAPH_STATUS_V1
        or graph["source_local_page_id"] != source["source_local_page_id"]
        or graph["source_projection_sha256"] != canonical_json_sha256_v1(source)
        or graph["source_proposal_projection_sha256"] != canonical_json_sha256_v1(proposals)
        or not same_typed_json_v1(graph["safety"], PAGE_PRESTRUCTURAL_GRAPH_SAFETY_V1)
    ):
        raise _error("page pre-structural authority/claim binding drifted")

    if type(graph["nodes"]) is not list or type(graph["edges"]) is not list:
        raise _error("page pre-structural graph collections drifted")
    if type(graph["atom_dispositions"]) is not list:
        raise _error("page pre-structural atom disposition collection drifted")
    nodes = [_validate_node_shape(node) for node in graph["nodes"]]
    edges = [_validate_edge_shape(edge) for edge in graph["edges"]]
    dispositions = [_validate_disposition_shape(item) for item in graph["atom_dispositions"]]
    if [node["ordinal"] for node in nodes] != list(range(1, len(nodes) + 1)):
        raise _error("page pre-structural node order drifted")
    if [edge["ordinal"] for edge in edges] != list(range(1, len(edges) + 1)):
        raise _error("page pre-structural edge order drifted")
    node_by_id = {node["node_id"]: node for node in nodes}
    if len(node_by_id) != len(nodes) or len({edge["edge_id"] for edge in edges}) != len(edges):
        raise _error("page pre-structural node/edge identity duplication")
    if any(
        edge["from_node_id"] not in node_by_id or edge["to_node_id"] not in node_by_id
        for edge in edges
    ):
        raise _error("page pre-structural edge references an unknown node")

    by_kind: dict[str, list[dict[str, Any]]] = {
        kind.value: [node for node in nodes if node["kind"] == kind.value]
        for kind in GraphNodeKindV1
    }
    if (
        len(by_kind[GraphNodeKindV1.DOCUMENT.value]) != 1
        or len(by_kind[GraphNodeKindV1.PAGE.value]) != 1
    ):
        raise _error("page graph requires exactly one document and one page node")
    if by_kind[GraphNodeKindV1.STATEMENT_BLOCK.value]:
        raise _error("statement-block promotion is outside this graph version")
    document = by_kind[GraphNodeKindV1.DOCUMENT.value][0]
    page = by_kind[GraphNodeKindV1.PAGE.value][0]
    source_sha = _sha(source["source_locator"]["source_sha256"], "source locator digest")
    page_binding = canonical_json_sha256_v1(source["source_local_page_id"])
    if (
        document["source_binding_sha256"] != source_sha
        or page["source_binding_sha256"] != page_binding
    ):
        raise _error("document/page source binding drifted")
    for node in nodes:
        if node["kind"] not in {GraphNodeKindV1.DOCUMENT.value, GraphNodeKindV1.PAGE.value}:
            expected_binding = _derived_node_source_binding(
                source_local_page_id=source["source_local_page_id"],
                kind=node["kind"],
                canonical_bbox_mpt=node["canonical_bbox_mpt"],
                source_atom_ids=node["source_atom_ids"],
                source_proposal_ids=node["source_proposal_ids"],
            )
            if node["source_binding_sha256"] != expected_binding:
                raise _error("page-local node source binding drifted")

    atoms = source["neutral_page_v1"]["atoms"]
    atom_ids = [atom["source_local_id"] for atom in atoms]
    atom_by_id = {atom["source_local_id"]: atom for atom in atoms}
    evidence_nodes = by_kind[GraphNodeKindV1.EVIDENCE.value]
    evidence_by_atom = {node["source_atom_ids"][0]: node for node in evidence_nodes}
    if len(evidence_nodes) != len(atoms) or set(evidence_by_atom) != set(atom_ids):
        raise _error("page graph evidence-node atom accounting drifted")
    for atom_id, evidence in evidence_by_atom.items():
        atom = atom_by_id[atom_id]
        if evidence["canonical_bbox_mpt"] != atom["canonical_bbox_mpt"]:
            raise _error("page graph evidence node drifted from its atom")

    proposal_items = proposals["proposal_set_v1"]["proposals"]
    proposal_by_id = {item["source_local_id"]: item for item in proposal_items}
    upstream_dispositions = proposals["proposal_set_v1"]["dispositions"]
    upstream_disposition_by_atom = {item["source_atom_id"]: item for item in upstream_dispositions}
    if set(upstream_disposition_by_atom) != set(atom_ids):
        raise _error("upstream source-proposal disposition accounting drifted")
    for node in nodes:
        if not set(node["source_atom_ids"]).issubset(atom_by_id):
            raise _error("page graph node cites an unknown source atom")
        if not set(node["source_proposal_ids"]).issubset(proposal_by_id):
            raise _error("page graph node cites an unknown source proposal")
        if node["kind"] in _CANDIDATE_KINDS:
            cited_proposals = [proposal_by_id[item] for item in node["source_proposal_ids"]]
            proposal_atom_sets = [
                set(proposal["primary_atom_ids"] + proposal["supporting_atom_ids"])
                for proposal in cited_proposals
            ]
            cited_atoms = set().union(*proposal_atom_sets)
            node_atoms = set(node["source_atom_ids"])
            if not node_atoms.issubset(cited_atoms) or any(
                not node_atoms.intersection(proposal_atoms) for proposal_atoms in proposal_atom_sets
            ):
                raise _error("structural candidate cites atoms outside its proposals")
            candidate_atoms = [atom_by_id[atom_id] for atom_id in node["source_atom_ids"]]
            if any(
                atom["authority"] != "AUTHENTICATED_PRIMARY" or atom["canonical_bbox_mpt"] is None
                for atom in candidate_atoms
            ):
                raise _error("structural candidate atom authority drifted")
            proposal_boxes = [proposal["canonical_bbox_mpt"] for proposal in cited_proposals]
            proposal_envelope = _box_union(proposal_boxes)
            atom_envelope = _box_union([atom["canonical_bbox_mpt"] for atom in candidate_atoms])
            expected_candidate_box = (
                proposal_envelope if node["kind"] == GraphNodeKindV1.TABLE.value else atom_envelope
            )
            if node["canonical_bbox_mpt"] != expected_candidate_box:
                raise _error("structural candidate source-derived box drifted")

    contains = [
        edge for edge in edges if edge["kind"] == GraphEdgeKindV1.PRESTRUCTURAL_CONTAINS.value
    ]
    incoming_contains: dict[str, list[str]] = {}
    for edge in contains:
        incoming_contains.setdefault(edge["to_node_id"], []).append(edge["from_node_id"])
    if incoming_contains.get(page["node_id"]) != [document["node_id"]]:
        raise _error("document-to-page containment drifted")
    allowed_parent_kind = {
        GraphNodeKindV1.UNRESOLVED_REGION.value: {GraphNodeKindV1.PAGE.value},
        GraphNodeKindV1.TABLE.value: {GraphNodeKindV1.UNRESOLVED_REGION.value},
        GraphNodeKindV1.ROW.value: {GraphNodeKindV1.TABLE.value},
        GraphNodeKindV1.CELL_OR_VALUE_POSITION.value: {GraphNodeKindV1.ROW.value},
        GraphNodeKindV1.AXIS_OR_DIMENSION.value: {GraphNodeKindV1.TABLE.value},
    }
    for kind, parent_kinds in allowed_parent_kind.items():
        for node in by_kind[kind]:
            parents = incoming_contains.get(node["node_id"], [])
            if len(parents) != 1 or node_by_id[parents[0]]["kind"] not in parent_kinds:
                raise _error("page graph containment hierarchy drifted")
    if not by_kind[GraphNodeKindV1.UNRESOLVED_REGION.value]:
        raise _error("page graph requires at least one explicit unresolved region")

    source_boxes_by_unresolved: dict[str, list[list[int]]] = {}
    for unresolved in by_kind[GraphNodeKindV1.UNRESOLVED_REGION.value]:
        source_boxes_by_unresolved[unresolved["node_id"]] = [
            atom_by_id[atom_id]["canonical_bbox_mpt"]
            for atom_id in unresolved["source_atom_ids"]
            if atom_by_id[atom_id]["canonical_bbox_mpt"] is not None
        ]
    for edge in contains:
        parent = node_by_id[edge["from_node_id"]]
        child = node_by_id[edge["to_node_id"]]
        parent_box = parent["canonical_bbox_mpt"]
        child_box = child["canonical_bbox_mpt"]
        if (
            parent_box is not None
            and child_box is not None
            and not _box_contains(parent_box, child_box)
        ):
            raise _error("candidate containment geometry drifted")
        if parent["kind"] == GraphNodeKindV1.UNRESOLVED_REGION.value and child_box is not None:
            source_boxes_by_unresolved[parent["node_id"]].append(child_box)
    for unresolved in by_kind[GraphNodeKindV1.UNRESOLVED_REGION.value]:
        boxes = source_boxes_by_unresolved[unresolved["node_id"]]
        expected_box = _box_union(boxes) if boxes else None
        if unresolved["canonical_bbox_mpt"] != expected_box:
            raise _error("unresolved-region source geometry drifted")

    atom_id_by_evidence_node = {
        evidence["node_id"]: atom_id for atom_id, evidence in evidence_by_atom.items()
    }
    supported_atoms_by_target: dict[str, set[str]] = {}
    candidate_support_targets_by_atom: dict[str, set[str]] = {}
    next_edges: list[dict[str, Any]] = []
    for edge in edges:
        left = node_by_id[edge["from_node_id"]]
        right = node_by_id[edge["to_node_id"]]
        if left["node_id"] == right["node_id"]:
            raise _error("page graph self-edge is not permitted")
        if edge["kind"] == GraphEdgeKindV1.PRESTRUCTURAL_CONTAINS.value and (
            left["kind"],
            right["kind"],
        ) not in {
            (GraphNodeKindV1.DOCUMENT.value, GraphNodeKindV1.PAGE.value),
            (GraphNodeKindV1.PAGE.value, GraphNodeKindV1.UNRESOLVED_REGION.value),
            (GraphNodeKindV1.UNRESOLVED_REGION.value, GraphNodeKindV1.TABLE.value),
            (GraphNodeKindV1.TABLE.value, GraphNodeKindV1.ROW.value),
            (GraphNodeKindV1.ROW.value, GraphNodeKindV1.CELL_OR_VALUE_POSITION.value),
            (GraphNodeKindV1.TABLE.value, GraphNodeKindV1.AXIS_OR_DIMENSION.value),
        }:
            raise _error("page graph containment edge kind drifted")
        if edge["kind"] == GraphEdgeKindV1.SUPPORTS.value and (
            left["kind"] != GraphNodeKindV1.EVIDENCE.value
            or right["kind"] not in _CANDIDATE_KINDS | {GraphNodeKindV1.UNRESOLVED_REGION.value}
        ):
            raise _error("page graph evidence-support edge drifted")
        if edge["kind"] == GraphEdgeKindV1.SUPPORTS.value:
            supported_atom = atom_id_by_evidence_node[left["node_id"]]
            if supported_atom not in right["source_atom_ids"]:
                raise _error("evidence-support edge is absent from its target citations")
            if right["kind"] in _CANDIDATE_KINDS and (
                source["terminal"]
                or atom_by_id[supported_atom]["authority"] != "AUTHENTICATED_PRIMARY"
            ):
                raise _error("ineligible source authority supports a structural candidate")
            if right["kind"] in _CANDIDATE_KINDS:
                candidate_support_targets_by_atom.setdefault(supported_atom, set()).add(
                    right["node_id"]
                )
            supported_atoms_by_target.setdefault(right["node_id"], set()).add(supported_atom)
        if edge["kind"] == GraphEdgeKindV1.PRESTRUCTURAL_ALIGNED_TO_AXIS.value:
            if (
                left["kind"] != GraphNodeKindV1.CELL_OR_VALUE_POSITION.value
                or right["kind"] != GraphNodeKindV1.AXIS_OR_DIMENSION.value
            ):
                raise _error("page graph cell-axis alignment edge drifted")
            row_id = incoming_contains[left["node_id"]][0]
            cell_table_id = incoming_contains[row_id][0]
            axis_table_id = incoming_contains[right["node_id"]][0]
            if (
                cell_table_id != axis_table_id
                or not set(left["source_proposal_ids"]).intersection(right["source_proposal_ids"])
                or not _x_ranges_overlap(left["canonical_bbox_mpt"], right["canonical_bbox_mpt"])
            ):
                raise _error("candidate cell-axis context/geometry drifted")
        if edge["kind"] == GraphEdgeKindV1.PRECEDES_IN_AUTHENTICATED_SOURCE_ORDER.value:
            if left["kind"] != right["kind"]:
                raise _error("page graph source-order edge must connect equal node kinds")
            next_edges.append(edge)

    for node in nodes:
        if node["kind"] in _CANDIDATE_KINDS | {GraphNodeKindV1.UNRESOLVED_REGION.value}:
            if supported_atoms_by_target.get(node["node_id"], set()) != set(
                node["source_atom_ids"]
            ):
                raise _error("node source citations and evidence-support edges drifted")

    atom_source_order = {atom_id: index for index, atom_id in enumerate(atom_ids)}
    next_predecessors: Counter[str] = Counter()
    next_successors: Counter[str] = Counter()
    for edge in next_edges:
        left = node_by_id[edge["from_node_id"]]
        right = node_by_id[edge["to_node_id"]]
        if not left["source_atom_ids"] or not right["source_atom_ids"]:
            raise _error("source-order edges require authenticated atom citations")
        left_order = [atom_source_order[atom_id] for atom_id in left["source_atom_ids"]]
        right_order = [atom_source_order[atom_id] for atom_id in right["source_atom_ids"]]
        if max(left_order) >= min(right_order):
            raise _error("candidate source-order edge contradicts authenticated atom order")
        next_successors[left["node_id"]] += 1
        next_predecessors[right["node_id"]] += 1
    if any(count > 1 for count in next_successors.values()) or any(
        count > 1 for count in next_predecessors.values()
    ):
        raise _error("candidate source-order relation is not a bounded chain")

    logical_edges = {(edge["kind"], edge["from_node_id"], edge["to_node_id"]) for edge in edges}
    if len(logical_edges) != len(edges):
        raise _error("page pre-structural logical edge duplication")

    if [item["source_atom_id"] for item in dispositions] != atom_ids:
        raise _error("page graph atom disposition order/accounting drifted")
    if len({item["source_atom_id"] for item in dispositions}) != len(dispositions):
        raise _error("page graph atom disposition duplication")
    support_edges = {
        (edge["from_node_id"], edge["to_node_id"])
        for edge in edges
        if edge["kind"] == GraphEdgeKindV1.SUPPORTS.value
    }
    for item in dispositions:
        evidence = evidence_by_atom[item["source_atom_id"]]
        upstream_disposition = upstream_disposition_by_atom[item["source_atom_id"]]
        owner = node_by_id.get(item["owner_node_id"])
        if (
            item["evidence_node_id"] != evidence["node_id"]
            or item["upstream_disposition_sha256"] != canonical_json_sha256_v1(upstream_disposition)
            or owner is None
        ):
            raise _error("page graph atom disposition binding drifted")
        expected: set[str]
        upstream_primary = upstream_disposition["primary_disposition"]
        if upstream_primary == "UPSTREAM_QUARANTINED":
            expected = {AtomGraphDispositionV1.UPSTREAM_QUARANTINED.value}
        elif upstream_primary == "UPSTREAM_TERMINAL_UNRESOLVED":
            expected = {AtomGraphDispositionV1.UPSTREAM_TERMINAL_UNRESOLVED.value}
        elif upstream_primary == "OWNED_BY_SOURCE_OBJECT":
            expected = {
                AtomGraphDispositionV1.SUPPORTS_PRESTRUCTURAL_CANDIDATE.value,
                AtomGraphDispositionV1.RETAINED_UNRESOLVED.value,
            }
        elif upstream_primary == "RETAINED_UNOWNED":
            expected = {
                AtomGraphDispositionV1.SUPPORTS_PRESTRUCTURAL_CANDIDATE.value,
                AtomGraphDispositionV1.RETAINED_UNRESOLVED.value,
            }
        else:
            raise _error("upstream atom disposition vocabulary drifted")
        if item["primary_disposition"] not in expected:
            raise _error("page graph atom disposition conflicts with source authority")
        if (
            item["primary_disposition"]
            == AtomGraphDispositionV1.SUPPORTS_PRESTRUCTURAL_CANDIDATE.value
        ):
            if owner["kind"] not in _CANDIDATE_KINDS or owner[
                "node_id"
            ] not in candidate_support_targets_by_atom.get(item["source_atom_id"], set()):
                raise _error("candidate-support disposition owner drifted")
        elif owner[
            "kind"
        ] != GraphNodeKindV1.UNRESOLVED_REGION.value or candidate_support_targets_by_atom.get(
            item["source_atom_id"], set()
        ):
            raise _error("unresolved/quarantined disposition support drifted")
        if (evidence["node_id"], owner["node_id"]) not in support_edges:
            raise _error("page graph atom disposition lacks its evidence-support edge")

    if source["terminal"] and any(by_kind[kind] for kind in _CANDIDATE_KINDS):
        raise _error("terminal source evidence cannot promote structural candidates")
    observed_metrics = _exact_dict(graph["metrics"], _METRIC_FIELDS, "page graph metrics")
    expected_metrics = _metrics(nodes, edges, dispositions)
    if not same_typed_json_v1(observed_metrics, expected_metrics):
        raise _error("page graph metrics drifted")
    expected_identity = f"ssgv1:graph:{canonical_json_sha256_v1({key: graph[key] for key in graph if key != 'graph_identity'})}"
    if (
        type(graph["graph_identity"]) is not str
        or _GRAPH_ID_RE.fullmatch(graph["graph_identity"]) is None
        or graph["graph_identity"] != expected_identity
    ):
        raise _error("page pre-structural graph identity drifted")
    return canonical_clone_v1(graph)
