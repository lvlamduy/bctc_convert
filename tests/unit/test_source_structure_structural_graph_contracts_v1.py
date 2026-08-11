from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest
from test_source_structure_evidence_projection_v2 import _synthetic_ocr_pair

from bctc_ai.source_structure import structural_graph_contracts_v1 as graph_v1
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from bctc_ai.source_structure.contracts_v2 import make_page_proposal_set_v2
from bctc_ai.source_structure.evidence_projection_v2 import project_authenticated_page_v2
from bctc_ai.source_structure.page_geometry_proposals_v1 import (
    generate_page_geometry_proposals_v1,
)


def _digest(label: str) -> str:
    return sha256(label.encode()).hexdigest()


def _source_id(label: str) -> str:
    return f"ssv1:source_object:{_digest(label)}"


def _authority(*, terminal: bool = False) -> tuple[dict, dict]:
    atoms = [
        {
            "source_local_id": _source_id("line"),
            "kind": "LINE",
            "authority": "AUTHENTICATED_PRIMARY",
            "canonical_bbox_mpt": [0, 0, 1000, 100],
        },
        {
            "source_local_id": _source_id("word"),
            "kind": "WORD",
            "authority": "AUTHENTICATED_PRIMARY",
            "canonical_bbox_mpt": [600, 0, 800, 100],
        },
        {
            "source_local_id": _source_id("quarantine"),
            "kind": "QUARANTINED_SPAN",
            "authority": "UPSTREAM_QUARANTINE",
            "canonical_bbox_mpt": None,
        },
    ]
    projection = {
        "source_local_page_id": f"ssv2:page:{_digest('page')}",
        "source_locator": {"source_sha256": _digest("source")},
        "terminal": terminal,
        "neutral_page_v1": {"atoms": atoms},
    }
    proposal_items = []
    if not terminal:
        proposal_items.append(
            {
                "source_local_id": _source_id("tabular-proposal"),
                "kind": "TABULAR_GEOMETRY_CANDIDATE",
                "canonical_bbox_mpt": [0, 0, 1000, 100],
                "primary_atom_ids": [atoms[0]["source_local_id"], atoms[1]["source_local_id"]],
                "supporting_atom_ids": [],
                "evidence_codes": ["LOCAL_GEOMETRY"],
            }
        )
    proposal_id = proposal_items[0]["source_local_id"] if proposal_items else None
    dispositions = []
    for atom in atoms:
        if atom["authority"] == "UPSTREAM_QUARANTINE":
            primary = "UPSTREAM_QUARANTINED"
            source_object_id = None
            reason = "UPSTREAM_QUARANTINE_RETAINED"
        elif terminal:
            primary = "UPSTREAM_TERMINAL_UNRESOLVED"
            source_object_id = None
            reason = "UPSTREAM_TERMINAL_RETAINED"
        else:
            primary = "OWNED_BY_SOURCE_OBJECT"
            source_object_id = proposal_id
            reason = "PRIMARY_LOCAL_GEOMETRY_OWNERSHIP"
        dispositions.append(
            {
                "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_ATOM_DISPOSITION_V1",
                "source_atom_id": atom["source_local_id"],
                "primary_disposition": primary,
                "source_object_id": source_object_id,
                "reason_code": reason,
            }
        )
    proposal = {"proposal_set_v1": {"proposals": proposal_items, "dispositions": dispositions}}
    return projection, proposal


@pytest.fixture(autouse=True)
def _patch_upstream_validators(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        graph_v1,
        "validate_source_evidence_projection_v2",
        lambda value: deepcopy(value),
    )
    monkeypatch.setattr(
        graph_v1,
        "validate_page_proposal_set_v2",
        lambda value, *, projection: deepcopy(value),
    )


def _node(
    ordinal: int,
    kind: graph_v1.GraphNodeKindV1,
    status: graph_v1.GraphNodeStatusV1,
    binding: str | None,
    *,
    bbox: list[int] | None = None,
    atom_ids: tuple[str, ...] = (),
    proposal_ids: tuple[str, ...] = (),
    source_local_page_id: str | None = None,
) -> dict:
    if source_local_page_id is None and kind not in {
        graph_v1.GraphNodeKindV1.DOCUMENT,
        graph_v1.GraphNodeKindV1.PAGE,
    }:
        source_local_page_id = f"ssv2:page:{_digest('page')}"
    return graph_v1.make_graph_node_v1(
        ordinal=ordinal,
        kind=kind,
        status=status,
        source_binding_sha256=binding,
        source_local_page_id=source_local_page_id,
        canonical_bbox_mpt=bbox,
        source_atom_ids=atom_ids,
        source_proposal_ids=proposal_ids,
    )


def _candidate_parts(projection: dict, proposal: dict) -> tuple[list[dict], list[dict], list[dict]]:
    atoms = projection["neutral_page_v1"]["atoms"]
    atom_ids = [atom["source_local_id"] for atom in atoms]
    atom_by_id = {atom["source_local_id"]: atom for atom in atoms}
    proposal_items = proposal["proposal_set_v1"]["proposals"]
    proposal_ids = tuple(item["source_local_id"] for item in proposal_items)
    candidate_atom_ids = sorted(
        {
            atom_id
            for item in proposal_items
            for atom_id in item["primary_atom_ids"] + item["supporting_atom_ids"]
        }
    )
    candidate_atom_set = set(candidate_atom_ids)
    unresolved_atom_ids = tuple(
        atom_id for atom_id in atom_ids if atom_id not in candidate_atom_set
    )
    proposal_box = [
        min(item["canonical_bbox_mpt"][0] for item in proposal_items),
        min(item["canonical_bbox_mpt"][1] for item in proposal_items),
        max(item["canonical_bbox_mpt"][2] for item in proposal_items),
        max(item["canonical_bbox_mpt"][3] for item in proposal_items),
    ]
    candidate_atom_boxes = [
        atom_by_id[atom_id]["canonical_bbox_mpt"] for atom_id in candidate_atom_ids
    ]
    candidate_atom_box = [
        min(box[0] for box in candidate_atom_boxes),
        min(box[1] for box in candidate_atom_boxes),
        max(box[2] for box in candidate_atom_boxes),
        max(box[3] for box in candidate_atom_boxes),
    ]
    cell_atom_id = next(
        (atom_id for atom_id in candidate_atom_ids if atom_by_id[atom_id]["kind"] == "WORD"),
        candidate_atom_ids[0],
    )
    cell_proposal_id = next(
        item["source_local_id"]
        for item in proposal_items
        if cell_atom_id in item["primary_atom_ids"] + item["supporting_atom_ids"]
    )
    unresolved_boxes = [proposal_box] + [
        atom_by_id[atom_id]["canonical_bbox_mpt"]
        for atom_id in unresolved_atom_ids
        if atom_by_id[atom_id]["canonical_bbox_mpt"] is not None
    ]
    unresolved_box = [
        min(box[0] for box in unresolved_boxes),
        min(box[1] for box in unresolved_boxes),
        max(box[2] for box in unresolved_boxes),
        max(box[3] for box in unresolved_boxes),
    ]
    nodes = [
        _node(
            1,
            graph_v1.GraphNodeKindV1.DOCUMENT,
            graph_v1.GraphNodeStatusV1.BOUND_SOURCE_CONTEXT,
            projection["source_locator"]["source_sha256"],
        ),
        _node(
            2,
            graph_v1.GraphNodeKindV1.PAGE,
            graph_v1.GraphNodeStatusV1.BOUND_SOURCE_CONTEXT,
            canonical_json_sha256_v1(projection["source_local_page_id"]),
        ),
        _node(
            3,
            graph_v1.GraphNodeKindV1.UNRESOLVED_REGION,
            graph_v1.GraphNodeStatusV1.EXPLICIT_UNRESOLVED,
            None,
            bbox=unresolved_box,
            atom_ids=unresolved_atom_ids,
            source_local_page_id=projection["source_local_page_id"],
        ),
        _node(
            4,
            graph_v1.GraphNodeKindV1.TABLE,
            graph_v1.GraphNodeStatusV1.PRESTRUCTURAL_CANDIDATE,
            None,
            bbox=proposal_box,
            atom_ids=tuple(candidate_atom_ids),
            proposal_ids=proposal_ids,
            source_local_page_id=projection["source_local_page_id"],
        ),
        _node(
            5,
            graph_v1.GraphNodeKindV1.ROW,
            graph_v1.GraphNodeStatusV1.PRESTRUCTURAL_CANDIDATE,
            None,
            bbox=candidate_atom_box,
            atom_ids=tuple(candidate_atom_ids),
            proposal_ids=proposal_ids,
            source_local_page_id=projection["source_local_page_id"],
        ),
        _node(
            6,
            graph_v1.GraphNodeKindV1.CELL_OR_VALUE_POSITION,
            graph_v1.GraphNodeStatusV1.PRESTRUCTURAL_CANDIDATE,
            None,
            bbox=atom_by_id[cell_atom_id]["canonical_bbox_mpt"],
            atom_ids=(cell_atom_id,),
            proposal_ids=(cell_proposal_id,),
            source_local_page_id=projection["source_local_page_id"],
        ),
        _node(
            7,
            graph_v1.GraphNodeKindV1.AXIS_OR_DIMENSION,
            graph_v1.GraphNodeStatusV1.PRESTRUCTURAL_CANDIDATE,
            None,
            bbox=atom_by_id[cell_atom_id]["canonical_bbox_mpt"],
            atom_ids=(cell_atom_id,),
            proposal_ids=(cell_proposal_id,),
            source_local_page_id=projection["source_local_page_id"],
        ),
    ]
    for offset, atom in enumerate(atoms, start=8):
        nodes.append(
            _node(
                offset,
                graph_v1.GraphNodeKindV1.EVIDENCE,
                graph_v1.GraphNodeStatusV1.BOUND_SOURCE_EVIDENCE,
                None,
                bbox=atom["canonical_bbox_mpt"],
                atom_ids=(atom["source_local_id"],),
                source_local_page_id=projection["source_local_page_id"],
            )
        )
    by_kind = {node["kind"]: node for node in nodes[:7]}
    evidence = {node["source_atom_ids"][0]: node for node in nodes[7:]}
    edge_specs = [
        (
            graph_v1.GraphEdgeKindV1.PRESTRUCTURAL_CONTAINS,
            by_kind["DOCUMENT"],
            by_kind["PAGE"],
        ),
        (
            graph_v1.GraphEdgeKindV1.PRESTRUCTURAL_CONTAINS,
            by_kind["PAGE"],
            by_kind["UNRESOLVED_REGION"],
        ),
        (
            graph_v1.GraphEdgeKindV1.PRESTRUCTURAL_CONTAINS,
            by_kind["UNRESOLVED_REGION"],
            by_kind["TABLE"],
        ),
        (
            graph_v1.GraphEdgeKindV1.PRESTRUCTURAL_CONTAINS,
            by_kind["TABLE"],
            by_kind["ROW"],
        ),
        (
            graph_v1.GraphEdgeKindV1.PRESTRUCTURAL_CONTAINS,
            by_kind["ROW"],
            by_kind["CELL_OR_VALUE_POSITION"],
        ),
        (
            graph_v1.GraphEdgeKindV1.PRESTRUCTURAL_CONTAINS,
            by_kind["TABLE"],
            by_kind["AXIS_OR_DIMENSION"],
        ),
    ]
    edge_specs.extend(
        (graph_v1.GraphEdgeKindV1.SUPPORTS, evidence[atom_id], by_kind[target_kind])
        for target_kind in ("TABLE", "ROW")
        for atom_id in candidate_atom_ids
    )
    edge_specs.extend(
        [
            (
                graph_v1.GraphEdgeKindV1.SUPPORTS,
                evidence[cell_atom_id],
                by_kind["CELL_OR_VALUE_POSITION"],
            ),
            (
                graph_v1.GraphEdgeKindV1.SUPPORTS,
                evidence[cell_atom_id],
                by_kind["AXIS_OR_DIMENSION"],
            ),
        ]
    )
    edge_specs.extend(
        (
            graph_v1.GraphEdgeKindV1.SUPPORTS,
            evidence[atom_id],
            by_kind["UNRESOLVED_REGION"],
        )
        for atom_id in unresolved_atom_ids
    )
    edge_specs.append(
        (
            graph_v1.GraphEdgeKindV1.PRESTRUCTURAL_ALIGNED_TO_AXIS,
            by_kind["CELL_OR_VALUE_POSITION"],
            by_kind["AXIS_OR_DIMENSION"],
        )
    )
    edges = [
        graph_v1.make_graph_edge_v1(
            ordinal=ordinal,
            kind=kind,
            from_node_id=left["node_id"],
            to_node_id=right["node_id"],
        )
        for ordinal, (kind, left, right) in enumerate(edge_specs, start=1)
    ]
    upstream_by_atom = {
        item["source_atom_id"]: item for item in proposal["proposal_set_v1"]["dispositions"]
    }
    dispositions = []
    for atom_id in atom_ids:
        upstream = upstream_by_atom[atom_id]
        if atom_id in candidate_atom_set:
            primary = graph_v1.AtomGraphDispositionV1.SUPPORTS_PRESTRUCTURAL_CANDIDATE
            owner = by_kind["CELL_OR_VALUE_POSITION"] if atom_id == cell_atom_id else by_kind["ROW"]
        else:
            primary = {
                "UPSTREAM_QUARANTINED": graph_v1.AtomGraphDispositionV1.UPSTREAM_QUARANTINED,
                "UPSTREAM_TERMINAL_UNRESOLVED": (
                    graph_v1.AtomGraphDispositionV1.UPSTREAM_TERMINAL_UNRESOLVED
                ),
            }.get(
                upstream["primary_disposition"],
                graph_v1.AtomGraphDispositionV1.RETAINED_UNRESOLVED,
            )
            owner = by_kind["UNRESOLVED_REGION"]
        dispositions.append(
            graph_v1.make_atom_graph_disposition_v1(
                source_atom_id=atom_id,
                upstream_disposition=upstream,
                evidence_node_id=evidence[atom_id]["node_id"],
                primary_disposition=primary,
                owner_node_id=owner["node_id"],
            )
        )
    return nodes, edges, dispositions


def _candidate_graph() -> tuple[dict, dict, dict]:
    projection, proposal = _authority()
    nodes, edges, dispositions = _candidate_parts(projection, proposal)
    graph = graph_v1.make_page_prestructural_graph_v1(
        projection,
        proposal,
        nodes=nodes,
        edges=edges,
        atom_dispositions=dispositions,
    )
    return projection, proposal, graph


def _refresh_graph_identity(graph: dict) -> None:
    graph["graph_identity"] = (
        f"ssgv1:graph:{canonical_json_sha256_v1({key: graph[key] for key in graph if key != 'graph_identity'})}"
    )


def _refresh_edge_id(edge: dict) -> None:
    edge["edge_id"] = (
        f"ssgv1:edge:{canonical_json_sha256_v1({key: edge[key] for key in edge if key != 'edge_id'})}"
    )


def _rewire_node(nodes: list[dict], edges: list[dict], old: dict, new: dict) -> None:
    nodes[nodes.index(old)] = new
    for edge in edges:
        if edge["from_node_id"] == old["node_id"]:
            edge["from_node_id"] = new["node_id"]
        if edge["to_node_id"] == old["node_id"]:
            edge["to_node_id"] = new["node_id"]
        _refresh_edge_id(edge)


def test_candidate_graph_is_exact_prestructural_and_no_drop() -> None:
    projection, proposal, graph = _candidate_graph()

    assert (
        graph_v1.validate_page_prestructural_graph_v1(
            graph, projection=projection, proposal_projection=proposal
        )
        == graph
    )
    assert graph["status"] == "PARTIAL_PRESTRUCTURAL_CANDIDATES"
    assert graph["metrics"]["atom_count"] == 3
    assert graph["metrics"]["node_counts"]["STATEMENT_BLOCK"] == 0
    assert graph["metrics"]["node_counts"]["TABLE"] == 1
    assert graph["metrics"]["disposition_counts"] == {
        "SUPPORTS_PRESTRUCTURAL_CANDIDATE": 2,
        "RETAINED_UNRESOLVED": 0,
        "UPSTREAM_TERMINAL_UNRESOLVED": 0,
        "UPSTREAM_QUARANTINED": 1,
    }
    assert not graph["safety"]["statement_claimed"]
    assert not graph["safety"]["table_claimed"]


def test_graph_identity_is_deterministic() -> None:
    assert _candidate_graph()[2] == _candidate_graph()[2]


def test_statement_block_node_is_rejected_without_statement_authority() -> None:
    with pytest.raises(graph_v1.PrestructuralGraphContractError, match="separate statement"):
        _node(
            1,
            graph_v1.GraphNodeKindV1.STATEMENT_BLOCK,
            graph_v1.GraphNodeStatusV1.PRESTRUCTURAL_CANDIDATE,
            None,
            bbox=[0, 0, 1, 1],
        )


def test_missing_atom_disposition_is_rejected_even_after_metrics_refresh() -> None:
    projection, proposal, graph = _candidate_graph()
    graph = deepcopy(graph)
    graph["atom_dispositions"].pop()
    graph["metrics"] = graph_v1._metrics(  # noqa: SLF001
        graph["nodes"], graph["edges"], graph["atom_dispositions"]
    )
    graph["graph_identity"] = (
        f"ssgv1:graph:{canonical_json_sha256_v1({key: graph[key] for key in graph if key != 'graph_identity'})}"
    )

    with pytest.raises(graph_v1.PrestructuralGraphContractError, match="order/accounting"):
        graph_v1.validate_page_prestructural_graph_v1(
            graph, projection=projection, proposal_projection=proposal
        )


def test_quarantined_atom_cannot_support_candidate() -> None:
    projection, proposal = _authority()
    nodes, edges, dispositions = _candidate_parts(projection, proposal)
    quarantine = projection["neutral_page_v1"]["atoms"][2]["source_local_id"]
    evidence = next(
        node
        for node in nodes
        if node["kind"] == "EVIDENCE" and node["source_atom_ids"] == [quarantine]
    )
    cell = next(node for node in nodes if node["kind"] == "CELL_OR_VALUE_POSITION")
    dispositions[2] = graph_v1.make_atom_graph_disposition_v1(
        source_atom_id=quarantine,
        upstream_disposition=proposal["proposal_set_v1"]["dispositions"][2],
        evidence_node_id=evidence["node_id"],
        primary_disposition=graph_v1.AtomGraphDispositionV1.SUPPORTS_PRESTRUCTURAL_CANDIDATE,
        owner_node_id=cell["node_id"],
    )
    edges.insert(
        -1,
        graph_v1.make_graph_edge_v1(
            ordinal=len(edges),
            kind=graph_v1.GraphEdgeKindV1.SUPPORTS,
            from_node_id=evidence["node_id"],
            to_node_id=cell["node_id"],
        ),
    )
    for ordinal, edge in enumerate(edges, start=1):
        edge["ordinal"] = ordinal
        edge["edge_id"] = (
            f"ssgv1:edge:{canonical_json_sha256_v1({key: edge[key] for key in edge if key != 'edge_id'})}"
        )

    with pytest.raises(
        graph_v1.PrestructuralGraphContractError, match="support edge|source authority"
    ):
        graph_v1.make_page_prestructural_graph_v1(
            projection,
            proposal,
            nodes=nodes,
            edges=edges,
            atom_dispositions=dispositions,
        )


def _terminal_parts(projection: dict, proposal: dict) -> tuple[list[dict], list[dict], list[dict]]:
    atoms = projection["neutral_page_v1"]["atoms"]
    upstream_by_atom = {
        item["source_atom_id"]: item for item in proposal["proposal_set_v1"]["dispositions"]
    }
    nodes = [
        _node(
            1,
            graph_v1.GraphNodeKindV1.DOCUMENT,
            graph_v1.GraphNodeStatusV1.BOUND_SOURCE_CONTEXT,
            projection["source_locator"]["source_sha256"],
        ),
        _node(
            2,
            graph_v1.GraphNodeKindV1.PAGE,
            graph_v1.GraphNodeStatusV1.BOUND_SOURCE_CONTEXT,
            canonical_json_sha256_v1(projection["source_local_page_id"]),
        ),
        _node(
            3,
            graph_v1.GraphNodeKindV1.UNRESOLVED_REGION,
            graph_v1.GraphNodeStatusV1.EXPLICIT_UNRESOLVED,
            None,
            bbox=[0, 0, 1000, 100],
            atom_ids=tuple(atom["source_local_id"] for atom in atoms),
            source_local_page_id=projection["source_local_page_id"],
        ),
    ]
    for ordinal, atom in enumerate(atoms, start=4):
        nodes.append(
            _node(
                ordinal,
                graph_v1.GraphNodeKindV1.EVIDENCE,
                graph_v1.GraphNodeStatusV1.BOUND_SOURCE_EVIDENCE,
                None,
                bbox=atom["canonical_bbox_mpt"],
                atom_ids=(atom["source_local_id"],),
                source_local_page_id=projection["source_local_page_id"],
            )
        )
    unresolved = nodes[2]
    evidence = {node["source_atom_ids"][0]: node for node in nodes[3:]}
    edge_pairs = [(nodes[0], nodes[1]), (nodes[1], unresolved)] + [
        (node, unresolved) for node in nodes[3:]
    ]
    edges = [
        graph_v1.make_graph_edge_v1(
            ordinal=ordinal,
            kind=(
                graph_v1.GraphEdgeKindV1.PRESTRUCTURAL_CONTAINS
                if ordinal <= 2
                else graph_v1.GraphEdgeKindV1.SUPPORTS
            ),
            from_node_id=left["node_id"],
            to_node_id=right["node_id"],
        )
        for ordinal, (left, right) in enumerate(edge_pairs, start=1)
    ]
    dispositions = [
        graph_v1.make_atom_graph_disposition_v1(
            source_atom_id=atom["source_local_id"],
            upstream_disposition=upstream_by_atom[atom["source_local_id"]],
            evidence_node_id=evidence[atom["source_local_id"]]["node_id"],
            primary_disposition=(
                graph_v1.AtomGraphDispositionV1.UPSTREAM_QUARANTINED
                if atom["authority"] == "UPSTREAM_QUARANTINE"
                else graph_v1.AtomGraphDispositionV1.UPSTREAM_TERMINAL_UNRESOLVED
            ),
            owner_node_id=unresolved["node_id"],
        )
        for atom in atoms
    ]
    return nodes, edges, dispositions


def test_terminal_page_requires_only_explicit_unresolved_evidence() -> None:
    projection, proposal = _authority(terminal=True)
    nodes, edges, dispositions = _terminal_parts(projection, proposal)

    graph = graph_v1.make_page_prestructural_graph_v1(
        projection,
        proposal,
        nodes=nodes,
        edges=edges,
        atom_dispositions=dispositions,
    )

    assert graph["metrics"]["node_counts"]["TABLE"] == 0
    assert graph["metrics"]["disposition_counts"]["UPSTREAM_TERMINAL_UNRESOLVED"] == 2
    assert graph["metrics"]["disposition_counts"]["UPSTREAM_QUARANTINED"] == 1


def test_terminal_page_rejects_candidate_promotion() -> None:
    projection, proposal = _authority(terminal=True)
    candidate_projection, candidate_proposal = _authority()
    nodes, edges, dispositions = _candidate_parts(candidate_projection, candidate_proposal)

    with pytest.raises(graph_v1.PrestructuralGraphContractError):
        graph_v1.make_page_prestructural_graph_v1(
            projection,
            proposal,
            nodes=nodes,
            edges=edges,
            atom_dispositions=dispositions,
        )


def test_source_projection_drift_is_rejected() -> None:
    projection, proposal, graph = _candidate_graph()
    changed = deepcopy(projection)
    changed["source_local_page_id"] = f"ssv2:page:{_digest('different-page')}"

    with pytest.raises(graph_v1.PrestructuralGraphContractError, match="authority/claim"):
        graph_v1.validate_page_prestructural_graph_v1(
            graph, projection=changed, proposal_projection=proposal
        )


def test_noncontext_node_identity_is_page_local() -> None:
    first = _node(
        1,
        graph_v1.GraphNodeKindV1.UNRESOLVED_REGION,
        graph_v1.GraphNodeStatusV1.EXPLICIT_UNRESOLVED,
        None,
        source_local_page_id=f"ssv2:page:{_digest('first-page')}",
    )
    second = _node(
        1,
        graph_v1.GraphNodeKindV1.UNRESOLVED_REGION,
        graph_v1.GraphNodeStatusV1.EXPLICIT_UNRESOLVED,
        None,
        source_local_page_id=f"ssv2:page:{_digest('second-page')}",
    )
    assert first["source_binding_sha256"] != second["source_binding_sha256"]
    assert first["node_id"] != second["node_id"]


def test_upstream_atom_disposition_binding_cannot_be_relabelled() -> None:
    projection, proposal, graph = _candidate_graph()
    graph = deepcopy(graph)
    graph["atom_dispositions"][0]["upstream_disposition_sha256"] = _digest("forged")
    _refresh_graph_identity(graph)

    with pytest.raises(graph_v1.PrestructuralGraphContractError, match="disposition binding"):
        graph_v1.validate_page_prestructural_graph_v1(
            graph, projection=projection, proposal_projection=proposal
        )


def test_retained_graph_disposition_cannot_keep_candidate_support_edges() -> None:
    projection, proposal, graph = _candidate_graph()
    graph = deepcopy(graph)
    unresolved = next(node for node in graph["nodes"] if node["kind"] == "UNRESOLVED_REGION")
    upstream = proposal["proposal_set_v1"]["dispositions"][0]
    evidence = next(
        node
        for node in graph["nodes"]
        if node["kind"] == "EVIDENCE" and node["source_atom_ids"] == [upstream["source_atom_id"]]
    )
    graph["atom_dispositions"][0] = graph_v1.make_atom_graph_disposition_v1(
        source_atom_id=upstream["source_atom_id"],
        upstream_disposition=upstream,
        evidence_node_id=evidence["node_id"],
        primary_disposition=graph_v1.AtomGraphDispositionV1.RETAINED_UNRESOLVED,
        owner_node_id=unresolved["node_id"],
    )
    _refresh_graph_identity(graph)

    with pytest.raises(graph_v1.PrestructuralGraphContractError, match="disposition support"):
        graph_v1.validate_page_prestructural_graph_v1(
            graph, projection=projection, proposal_projection=proposal
        )


def test_source_block_and_multi_proposal_envelope_are_candidate_evidence() -> None:
    projection, proposal = _authority()
    line, word = projection["neutral_page_v1"]["atoms"][:2]
    source_block_id = _source_id("source-block-proposal")
    tabular_id = _source_id("tabular-subproposal")
    proposal["proposal_set_v1"]["proposals"] = [
        {
            "source_local_id": source_block_id,
            "kind": "SOURCE_BLOCK_CANDIDATE",
            "canonical_bbox_mpt": line["canonical_bbox_mpt"],
            "primary_atom_ids": [line["source_local_id"]],
            "supporting_atom_ids": [],
            "evidence_codes": ["LOCAL_GEOMETRY"],
        },
        {
            "source_local_id": tabular_id,
            "kind": "TABULAR_GEOMETRY_CANDIDATE",
            "canonical_bbox_mpt": word["canonical_bbox_mpt"],
            "primary_atom_ids": [word["source_local_id"]],
            "supporting_atom_ids": [],
            "evidence_codes": ["LOCAL_GEOMETRY"],
        },
    ]
    proposal["proposal_set_v1"]["dispositions"][0]["source_object_id"] = source_block_id
    proposal["proposal_set_v1"]["dispositions"][1]["source_object_id"] = tabular_id
    nodes, edges, dispositions = _candidate_parts(projection, proposal)

    graph = graph_v1.make_page_prestructural_graph_v1(
        projection,
        proposal,
        nodes=nodes,
        edges=edges,
        atom_dispositions=dispositions,
    )
    table = next(node for node in graph["nodes"] if node["kind"] == "TABLE")
    assert table["source_proposal_ids"] == sorted([source_block_id, tabular_id])
    assert table["canonical_bbox_mpt"] == [0, 0, 1000, 100]


def test_logical_node_duplication_and_reverse_source_order_are_rejected() -> None:
    projection, proposal = _authority()
    nodes, edges, dispositions = _candidate_parts(projection, proposal)
    duplicate_row = deepcopy(next(node for node in nodes if node["kind"] == "ROW"))
    duplicate_row["ordinal"] = len(nodes) + 1
    nodes.append(duplicate_row)
    with pytest.raises(graph_v1.PrestructuralGraphContractError, match="identity duplication"):
        graph_v1.make_page_prestructural_graph_v1(
            projection,
            proposal,
            nodes=nodes,
            edges=edges,
            atom_dispositions=dispositions,
        )

    nodes.pop()
    line_id, word_id = [
        atom["source_local_id"] for atom in projection["neutral_page_v1"]["atoms"][:2]
    ]
    evidence_by_atom = {
        node["source_atom_ids"][0]: node for node in nodes if node["kind"] == "EVIDENCE"
    }
    edges.append(
        graph_v1.make_graph_edge_v1(
            ordinal=len(edges) + 1,
            kind=graph_v1.GraphEdgeKindV1.PRECEDES_IN_AUTHENTICATED_SOURCE_ORDER,
            from_node_id=evidence_by_atom[word_id]["node_id"],
            to_node_id=evidence_by_atom[line_id]["node_id"],
        )
    )
    with pytest.raises(graph_v1.PrestructuralGraphContractError, match="authenticated atom order"):
        graph_v1.make_page_prestructural_graph_v1(
            projection,
            proposal,
            nodes=nodes,
            edges=edges,
            atom_dispositions=dispositions,
        )


def test_precedes_relation_truthfully_allows_nonadjacent_source_atoms() -> None:
    projection, proposal = _authority()
    nodes, edges, dispositions = _candidate_parts(projection, proposal)
    first_id, _, third_id = [
        atom["source_local_id"] for atom in projection["neutral_page_v1"]["atoms"]
    ]
    evidence_by_atom = {
        node["source_atom_ids"][0]: node for node in nodes if node["kind"] == "EVIDENCE"
    }
    edges.append(
        graph_v1.make_graph_edge_v1(
            ordinal=len(edges) + 1,
            kind=graph_v1.GraphEdgeKindV1.PRECEDES_IN_AUTHENTICATED_SOURCE_ORDER,
            from_node_id=evidence_by_atom[first_id]["node_id"],
            to_node_id=evidence_by_atom[third_id]["node_id"],
        )
    )
    graph = graph_v1.make_page_prestructural_graph_v1(
        projection,
        proposal,
        nodes=nodes,
        edges=edges,
        atom_dispositions=dispositions,
    )
    assert graph["metrics"]["edge_counts"]["PRECEDES_IN_AUTHENTICATED_SOURCE_ORDER"] == 1


def test_candidate_containment_and_axis_alignment_require_coherent_geometry() -> None:
    projection, proposal = _authority()
    projection["neutral_page_v1"]["atoms"][0]["canonical_bbox_mpt"] = [0, 0, 400, 100]
    projection["neutral_page_v1"]["atoms"][1]["canonical_bbox_mpt"] = [600, 0, 800, 100]
    line_proposal_id = _source_id("left-source-block")
    word_proposal_id = _source_id("right-tabular-block")
    proposal["proposal_set_v1"]["proposals"] = [
        {
            "source_local_id": line_proposal_id,
            "kind": "SOURCE_BLOCK_CANDIDATE",
            "canonical_bbox_mpt": [0, 0, 400, 100],
            "primary_atom_ids": [projection["neutral_page_v1"]["atoms"][0]["source_local_id"]],
            "supporting_atom_ids": [],
            "evidence_codes": ["LOCAL_GEOMETRY"],
        },
        {
            "source_local_id": word_proposal_id,
            "kind": "TABULAR_GEOMETRY_CANDIDATE",
            "canonical_bbox_mpt": [600, 0, 800, 100],
            "primary_atom_ids": [projection["neutral_page_v1"]["atoms"][1]["source_local_id"]],
            "supporting_atom_ids": [],
            "evidence_codes": ["LOCAL_GEOMETRY"],
        },
    ]
    proposal["proposal_set_v1"]["dispositions"][0]["source_object_id"] = line_proposal_id
    proposal["proposal_set_v1"]["dispositions"][1]["source_object_id"] = word_proposal_id
    nodes, edges, dispositions = _candidate_parts(projection, proposal)
    line_id, word_id = [
        atom["source_local_id"] for atom in projection["neutral_page_v1"]["atoms"][:2]
    ]
    evidence_by_atom = {
        node["source_atom_ids"][0]: node for node in nodes if node["kind"] == "EVIDENCE"
    }

    old_table = next(node for node in nodes if node["kind"] == "TABLE")
    narrow_table = _node(
        old_table["ordinal"],
        graph_v1.GraphNodeKindV1.TABLE,
        graph_v1.GraphNodeStatusV1.PRESTRUCTURAL_CANDIDATE,
        None,
        bbox=[0, 0, 400, 100],
        atom_ids=(line_id,),
        proposal_ids=(line_proposal_id,),
        source_local_page_id=projection["source_local_page_id"],
    )
    edges = [
        edge
        for edge in edges
        if not (
            edge["kind"] == "SUPPORTS"
            and edge["from_node_id"] == evidence_by_atom[word_id]["node_id"]
            and edge["to_node_id"] == old_table["node_id"]
        )
    ]
    for ordinal, edge in enumerate(edges, start=1):
        edge["ordinal"] = ordinal
    _rewire_node(nodes, edges, old_table, narrow_table)
    with pytest.raises(graph_v1.PrestructuralGraphContractError, match="containment geometry"):
        graph_v1.make_page_prestructural_graph_v1(
            projection,
            proposal,
            nodes=nodes,
            edges=edges,
            atom_dispositions=dispositions,
        )

    nodes, edges, dispositions = _candidate_parts(projection, proposal)
    old_axis = next(node for node in nodes if node["kind"] == "AXIS_OR_DIMENSION")
    left_axis = _node(
        old_axis["ordinal"],
        graph_v1.GraphNodeKindV1.AXIS_OR_DIMENSION,
        graph_v1.GraphNodeStatusV1.PRESTRUCTURAL_CANDIDATE,
        None,
        bbox=[0, 0, 400, 100],
        atom_ids=(line_id,),
        proposal_ids=(line_proposal_id,),
        source_local_page_id=projection["source_local_page_id"],
    )
    for edge in edges:
        if edge["kind"] == "SUPPORTS" and edge["to_node_id"] == old_axis["node_id"]:
            edge["from_node_id"] = evidence_by_atom[line_id]["node_id"]
    _rewire_node(nodes, edges, old_axis, left_axis)
    with pytest.raises(graph_v1.PrestructuralGraphContractError, match="cell-axis"):
        graph_v1.make_page_prestructural_graph_v1(
            projection,
            proposal,
            nodes=nodes,
            edges=edges,
            atom_dispositions=dispositions,
        )


def test_real_v2_source_block_projection_replays_without_mocked_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.undo()
    page_record, page_result = _synthetic_ocr_pair()
    projection = project_authenticated_page_v2(
        page_record=page_record,
        page_result=page_result,
    )
    proposal_v1 = generate_page_geometry_proposals_v1(projection)
    proposal = make_page_proposal_set_v2(projection, proposal_set_v1=proposal_v1)
    assert [item["kind"] for item in proposal_v1["proposals"]] == ["SOURCE_BLOCK_CANDIDATE"]
    nodes, edges, dispositions = _candidate_parts(projection, proposal)

    graph = graph_v1.make_page_prestructural_graph_v1(
        projection,
        proposal,
        nodes=nodes,
        edges=edges,
        atom_dispositions=dispositions,
    )
    assert (
        graph_v1.validate_page_prestructural_graph_v1(
            graph,
            projection=projection,
            proposal_projection=proposal,
        )
        == graph
    )


def test_noncontext_node_binding_is_derived_not_caller_asserted() -> None:
    with pytest.raises(graph_v1.PrestructuralGraphContractError, match="source binding"):
        _node(
            1,
            graph_v1.GraphNodeKindV1.TABLE,
            graph_v1.GraphNodeStatusV1.PRESTRUCTURAL_CANDIDATE,
            _digest("forged-binding"),
            bbox=[0, 0, 1000, 100],
            atom_ids=(_source_id("line"),),
            proposal_ids=(_source_id("tabular-proposal"),),
        )


def test_candidate_atoms_and_box_must_be_inside_cited_proposal() -> None:
    projection, proposal = _authority()
    nodes, edges, dispositions = _candidate_parts(projection, proposal)
    proposal_id = proposal["proposal_set_v1"]["proposals"][0]["source_local_id"]
    quarantine = projection["neutral_page_v1"]["atoms"][2]["source_local_id"]
    nodes.append(
        _node(
            len(nodes) + 1,
            graph_v1.GraphNodeKindV1.TABLE,
            graph_v1.GraphNodeStatusV1.PRESTRUCTURAL_CANDIDATE,
            None,
            bbox=[0, 0, 1000, 100],
            atom_ids=(quarantine,),
            proposal_ids=(proposal_id,),
        )
    )
    with pytest.raises(graph_v1.PrestructuralGraphContractError, match="outside its proposals"):
        graph_v1.make_page_prestructural_graph_v1(
            projection,
            proposal,
            nodes=nodes,
            edges=edges,
            atom_dispositions=dispositions,
        )

    nodes.pop()
    nodes.append(
        _node(
            len(nodes) + 1,
            graph_v1.GraphNodeKindV1.TABLE,
            graph_v1.GraphNodeStatusV1.PRESTRUCTURAL_CANDIDATE,
            None,
            bbox=[1000, 0, 1100, 100],
            atom_ids=(projection["neutral_page_v1"]["atoms"][0]["source_local_id"],),
            proposal_ids=(proposal_id,),
        )
    )
    with pytest.raises(graph_v1.PrestructuralGraphContractError, match="source-derived box"):
        graph_v1.make_page_prestructural_graph_v1(
            projection,
            proposal,
            nodes=nodes,
            edges=edges,
            atom_dispositions=dispositions,
        )


def test_invalid_containment_and_duplicate_logical_edges_are_rejected() -> None:
    projection, proposal = _authority()
    nodes, edges, dispositions = _candidate_parts(projection, proposal)
    evidence = next(node for node in nodes if node["kind"] == "EVIDENCE")
    document = next(node for node in nodes if node["kind"] == "DOCUMENT")
    edges.append(
        graph_v1.make_graph_edge_v1(
            ordinal=len(edges) + 1,
            kind=graph_v1.GraphEdgeKindV1.PRESTRUCTURAL_CONTAINS,
            from_node_id=evidence["node_id"],
            to_node_id=document["node_id"],
        )
    )
    with pytest.raises(graph_v1.PrestructuralGraphContractError, match="containment edge"):
        graph_v1.make_page_prestructural_graph_v1(
            projection,
            proposal,
            nodes=nodes,
            edges=edges,
            atom_dispositions=dispositions,
        )

    edges.pop()
    original = next(edge for edge in edges if edge["kind"] == "SUPPORTS")
    edges.append(
        graph_v1.make_graph_edge_v1(
            ordinal=len(edges) + 1,
            kind=original["kind"],
            from_node_id=original["from_node_id"],
            to_node_id=original["to_node_id"],
        )
    )
    with pytest.raises(graph_v1.PrestructuralGraphContractError, match="logical edge"):
        graph_v1.make_page_prestructural_graph_v1(
            projection,
            proposal,
            nodes=nodes,
            edges=edges,
            atom_dispositions=dispositions,
        )


def test_contract_has_no_forbidden_semantic_or_routing_dependencies() -> None:
    source = Path(graph_v1.__file__).read_text(encoding="utf-8")
    forbidden_imports = (
        "document_phase",
        "tables.geometry",
        "rows.",
        "role_a",
        "schema",
        "reportnorm",
    )
    assert not any(
        f"import {item}" in source or f"from bctc_ai.{item}" in source for item in forbidden_imports
    )
    for forbidden_key in (
        '["bank"]',
        '["filename"]',
        '["path"]',
        '["note"]',
        '["physical_page"]',
        '["raw_text"]',
    ):
        assert forbidden_key not in source
