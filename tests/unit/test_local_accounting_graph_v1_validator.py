from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from test_local_accounting_graph_v1 import (
    EvidenceBuilder,
    _observation,
    _quality_region,
)

from bctc_ai.source_structure import local_accounting_graph_v1 as lag
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _rehash_edge(edge: dict[str, Any]) -> None:
    payload = {key: edge[key] for key in edge if key != "edge_id"}
    edge["edge_id"] = "lagv1:edge:" + canonical_json_sha256_v1(payload)


def _rehash_graph(graph: dict[str, Any]) -> dict[str, Any]:
    graph["nodes"] = sorted(graph["nodes"], key=lambda node: node["node_id"])
    graph["edges"] = sorted(graph["edges"], key=lambda edge: edge["edge_id"])
    payload = {key: graph[key] for key in graph if key != "graph_identity"}
    graph["graph_identity"] = "lagv1:graph:" + canonical_json_sha256_v1(payload)
    return graph


def _replace_node_identity(graph: dict[str, Any], node: dict[str, Any]) -> None:
    old_node_id = node["node_id"]
    payload = {key: node[key] for key in node if key != "node_id"}
    new_node_id = "lagv1:node:" + canonical_json_sha256_v1(payload)
    assert new_node_id != old_node_id
    node["node_id"] = new_node_id
    for edge in graph["edges"]:
        if edge["from_node_id"] == old_node_id:
            edge["from_node_id"] = new_node_id
        if edge["to_node_id"] == old_node_id:
            edge["to_node_id"] = new_node_id
        edge["evidence_node_ids"] = sorted(
            new_node_id if node_id == old_node_id else node_id
            for node_id in edge["evidence_node_ids"]
        )
        _rehash_edge(edge)
    _rehash_graph(graph)


@pytest.fixture
def accepted_case(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    monkeypatch.setattr(
        lag,
        "validate_source_evidence_projection_v2",
        lambda value: deepcopy(value),
    )
    builder = EvidenceBuilder()
    region = _quality_region(builder)
    projection = builder.projection()
    observation = _observation(projection, [region])
    graph = lag.infer_local_accounting_graph_v1(
        projection,
        observation,
        lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    )
    assert graph["status"] == "CORE_ACCEPTED"
    return {
        "projection": projection,
        "observation": observation,
        "graph": graph,
    }


@pytest.fixture
def unresolved_graph(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    monkeypatch.setattr(
        lag,
        "validate_source_evidence_projection_v2",
        lambda value: deepcopy(value),
    )
    builder = EvidenceBuilder()
    region = _quality_region(builder, owner="Chứng khoán đầu tư")
    projection = builder.projection()
    graph = lag.infer_local_accounting_graph_v1(
        projection,
        _observation(projection, [region]),
        lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    )
    assert graph["status"] == "EXPLICIT_UNRESOLVED"
    return graph


def _evidence(graph: dict[str, Any], role: str) -> dict[str, Any]:
    return next(
        node
        for node in graph["nodes"]
        if node["kind"] == "EVIDENCE" and node["attributes"].get("evidence_role") == role
    )


def test_validator_rejects_rehashed_edgeless_accepted_graph(
    accepted_case: dict[str, Any],
) -> None:
    graph = deepcopy(accepted_case["graph"])
    graph["edges"] = []
    graph["accepted_counts"]["HIERARCHY"] = 0
    _rehash_graph(graph)

    with pytest.raises(lag.LocalAccountingGraphContractError):
        lag.validate_local_accounting_graph_v1(graph)


def test_validator_rejects_rehashed_wrong_supported_by_target(
    accepted_case: dict[str, Any],
) -> None:
    graph = deepcopy(accepted_case["graph"])
    owner_id = next(
        node["node_id"]
        for node in graph["nodes"]
        if node["kind"] == "ACCOUNTING_ROLE"
        and node["attributes"].get("accounting_role") == "OWNER_LABEL"
    )
    branch_evidence_id = _evidence(graph, "BRANCH_LABEL")["node_id"]
    edge = next(
        edge
        for edge in graph["edges"]
        if edge["kind"] == "SUPPORTED_BY" and edge["from_node_id"] == owner_id
    )
    edge["to_node_id"] = branch_evidence_id
    edge["evidence_node_ids"] = [branch_evidence_id]
    _rehash_edge(edge)
    _rehash_graph(graph)

    with pytest.raises(lag.LocalAccountingGraphContractError):
        lag.validate_local_accounting_graph_v1(graph)


def test_validator_rejects_rehashed_wrong_owns_evidence(
    accepted_case: dict[str, Any],
) -> None:
    graph = deepcopy(accepted_case["graph"])
    branch_evidence_id = _evidence(graph, "BRANCH_LABEL")["node_id"]
    edge = next(edge for edge in graph["edges"] if edge["kind"] == "OWNS")
    edge["evidence_node_ids"] = [branch_evidence_id]
    _rehash_edge(edge)
    _rehash_graph(graph)

    with pytest.raises(lag.LocalAccountingGraphContractError):
        lag.validate_local_accounting_graph_v1(graph)


def test_validator_rejects_rehashed_value_evidence_with_row_index_999(
    accepted_case: dict[str, Any],
) -> None:
    graph = deepcopy(accepted_case["graph"])
    evidence = _evidence(graph, "VALUE_POSITION:0:0")
    evidence["attributes"]["evidence_role"] = "VALUE_POSITION:999:0"
    _replace_node_identity(graph, evidence)

    with pytest.raises(lag.LocalAccountingGraphContractError):
        lag.validate_local_accounting_graph_v1(graph)


def test_validator_rejects_rehashed_source_raw_owner_mutation(
    accepted_case: dict[str, Any],
) -> None:
    graph = deepcopy(accepted_case["graph"])
    evidence = _evidence(graph, "OWNER_LABEL")
    evidence["attributes"]["raw_text"] = "Chứng khoán đầu tư"
    _replace_node_identity(graph, evidence)

    with pytest.raises(lag.LocalAccountingGraphContractError):
        lag.validate_local_accounting_graph_v1(graph)


def test_validator_rejects_rehashed_unknown_family(
    accepted_case: dict[str, Any],
) -> None:
    graph = deepcopy(accepted_case["graph"])
    graph["family_id"] = "UNKNOWN_FAMILY"
    graph["family_spec_sha256"] = canonical_json_sha256_v1({"family_id": "UNKNOWN_FAMILY"})
    _rehash_graph(graph)

    with pytest.raises(lag.LocalAccountingGraphContractError):
        lag.validate_local_accounting_graph_v1(graph)


def test_validator_rejects_rehashed_invalid_arithmetic_axis_index(
    accepted_case: dict[str, Any],
) -> None:
    graph = deepcopy(accepted_case["graph"])
    graph["arithmetic_check"]["evaluated_axis_indexes"] = [999]
    _rehash_graph(graph)

    with pytest.raises(lag.LocalAccountingGraphContractError):
        lag.validate_local_accounting_graph_v1(graph)


def test_validator_rejects_rehashed_edgeless_unresolved_graph(
    unresolved_graph: dict[str, Any],
) -> None:
    graph = deepcopy(unresolved_graph)
    graph["edges"] = []
    _rehash_graph(graph)

    with pytest.raises(lag.LocalAccountingGraphContractError):
        lag.validate_local_accounting_graph_v1(graph)


def test_replay_rejects_source_divergent_but_internally_valid_rehashed_graph(
    accepted_case: dict[str, Any],
) -> None:
    graph = deepcopy(accepted_case["graph"])
    evidence = _evidence(graph, "OWNER_LABEL")
    evidence["attributes"]["raw_text"] = "Dư nợ cho vay khách hàng"
    _replace_node_identity(graph, evidence)

    # The alternate text is a registered owner alias, so the persisted graph
    # remains internally valid. Exact replay must still reject it because those
    # bytes were not present in the supplied observation/projection.
    lag.validate_local_accounting_graph_v1(graph)
    with pytest.raises(
        lag.LocalAccountingGraphContractError,
        match="not the deterministic replay of exact source inputs",
    ):
        lag.validate_local_accounting_graph_replay_v1(
            graph,
            source_projection_v2=accepted_case["projection"],
            observation=accepted_case["observation"],
            family_spec=lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
        )


def test_validator_rejects_rehashed_orphan_evidence_node(
    accepted_case: dict[str, Any],
) -> None:
    graph = deepcopy(accepted_case["graph"])
    orphan = deepcopy(_evidence(graph, "OWNER_LABEL"))
    orphan["attributes"]["evidence_role"] = "ROW_LABEL:999"
    payload = {key: orphan[key] for key in orphan if key != "node_id"}
    orphan["node_id"] = "lagv1:node:" + canonical_json_sha256_v1(payload)
    graph["nodes"].append(orphan)
    _rehash_graph(graph)

    with pytest.raises(lag.LocalAccountingGraphContractError):
        lag.validate_local_accounting_graph_v1(graph)
