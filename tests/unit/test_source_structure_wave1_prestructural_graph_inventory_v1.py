from __future__ import annotations

import ast
import os
import stat
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from bctc_ai.source_structure import wave1_prestructural_graph_inventory_v1 as inventory_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)
from bctc_ai.source_structure.finalized_v3_survey_stream_v1 import (
    AuthenticatedV3SurveyPage,
    FinalizedV3SurveyAuthority,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    PROJECT_ROOT / "src/bctc_ai/source_structure/wave1_prestructural_graph_inventory_v1.py"
)
_DOCUMENT_IDS = ("sha256:" + "a" * 64, "sha256:" + "b" * 64)


def _authority() -> FinalizedV3SurveyAuthority:
    return FinalizedV3SurveyAuthority(
        aggregate_artifact_sha256="1" * 64,
        aggregate_size_bytes=101,
        aggregate_identity_sha256="2" * 64,
        control_artifact_sha256="3" * 64,
        control_size_bytes=202,
        control_identity_sha256="4" * 64,
        sealed_plan_sha256="5" * 64,
        document_ids=_DOCUMENT_IDS,
        document_count=2,
        request_count=2,
        referenced_object_count=4,
    )


def _authority_payload(authority: FinalizedV3SurveyAuthority) -> dict[str, Any]:
    return {
        "aggregate_artifact_sha256": authority.aggregate_artifact_sha256,
        "aggregate_size_bytes": authority.aggregate_size_bytes,
        "aggregate_identity_sha256": authority.aggregate_identity_sha256,
        "control_artifact_sha256": authority.control_artifact_sha256,
        "control_size_bytes": authority.control_size_bytes,
        "control_identity_sha256": authority.control_identity_sha256,
        "sealed_plan_sha256": authority.sealed_plan_sha256,
        "document_ids": list(authority.document_ids),
        "document_count": authority.document_count,
        "request_count": authority.request_count,
        "referenced_object_count": authority.referenced_object_count,
    }


def _projections() -> list[dict[str, Any]]:
    return [
        {
            "source_local_page_id": "ssv2:page:" + "6" * 64,
            "source_locator": {"source_sha256": "a" * 64},
            "route": "DOMINANT_RASTER_OCR",
            "upstream_status": "OCR_WORD_BOX_READ_COMPLETE",
            "terminal": False,
        },
        {
            "source_local_page_id": "ssv2:page:" + "7" * 64,
            "source_locator": {"source_sha256": "b" * 64},
            "route": "CAUSAL_NATIVE_TEXT",
            "upstream_status": "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY",
            "terminal": True,
        },
    ]


def _proposal_projections(projections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "source_local_page_id": projection["source_local_page_id"],
            "proposal_set_v1": {"synthetic_ordinal": ordinal},
        }
        for ordinal, projection in enumerate(projections, start=1)
    ]


def _node(
    ordinal: int,
    kind: str,
    status: str,
    *,
    atoms: tuple[str, ...] = (),
    proposals: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "node_id": f"node-{ordinal}",
        "ordinal": ordinal,
        "kind": kind,
        "status": status,
        "source_atom_ids": list(atoms),
        "source_proposal_ids": list(proposals),
    }


def _edge(ordinal: int, kind: str, left: int, right: int) -> dict[str, Any]:
    return {
        "ordinal": ordinal,
        "kind": kind,
        "from_node_id": f"node-{left}",
        "to_node_id": f"node-{right}",
    }


def _closed_counts(vocabulary: tuple[str, ...], **overrides: int) -> dict[str, int]:
    return {key: overrides.get(key, 0) for key in vocabulary}


def _graphs() -> list[dict[str, Any]]:
    candidate_nodes = [
        _node(1, "DOCUMENT", "BOUND_SOURCE_CONTEXT"),
        _node(2, "PAGE", "BOUND_SOURCE_CONTEXT"),
        _node(3, "UNRESOLVED_REGION", "EXPLICIT_UNRESOLVED"),
        _node(
            4,
            "TABLE",
            "PRESTRUCTURAL_CANDIDATE",
            atoms=("atom-1",),
            proposals=("proposal-1",),
        ),
        _node(
            5,
            "ROW",
            "PRESTRUCTURAL_CANDIDATE",
            atoms=("atom-1",),
            proposals=("proposal-1",),
        ),
        _node(
            6,
            "CELL_OR_VALUE_POSITION",
            "PRESTRUCTURAL_CANDIDATE",
            atoms=("atom-1",),
            proposals=("proposal-1",),
        ),
        _node(
            7,
            "AXIS_OR_DIMENSION",
            "PRESTRUCTURAL_CANDIDATE",
            atoms=("atom-1",),
            proposals=("proposal-1",),
        ),
        _node(8, "EVIDENCE", "BOUND_SOURCE_EVIDENCE", atoms=("atom-1",)),
    ]
    candidate_edges = [
        _edge(1, "PRESTRUCTURAL_CONTAINS", 1, 2),
        _edge(2, "PRESTRUCTURAL_CONTAINS", 2, 3),
        _edge(3, "PRESTRUCTURAL_CONTAINS", 3, 4),
        _edge(4, "PRESTRUCTURAL_CONTAINS", 4, 5),
        _edge(5, "PRESTRUCTURAL_CONTAINS", 5, 6),
        _edge(6, "PRESTRUCTURAL_CONTAINS", 4, 7),
        _edge(7, "PRESTRUCTURAL_ALIGNED_TO_AXIS", 6, 7),
        _edge(8, "SUPPORTS", 8, 4),
        _edge(9, "SUPPORTS", 8, 5),
        _edge(10, "SUPPORTS", 8, 6),
        _edge(11, "SUPPORTS", 8, 7),
    ]
    terminal_nodes = [
        _node(1, "DOCUMENT", "BOUND_SOURCE_CONTEXT"),
        _node(2, "PAGE", "BOUND_SOURCE_CONTEXT"),
        _node(3, "UNRESOLVED_REGION", "EXPLICIT_UNRESOLVED", atoms=("atom-2",)),
        _node(4, "EVIDENCE", "BOUND_SOURCE_EVIDENCE", atoms=("atom-2",)),
    ]
    terminal_edges = [
        _edge(1, "PRESTRUCTURAL_CONTAINS", 1, 2),
        _edge(2, "PRESTRUCTURAL_CONTAINS", 2, 3),
        _edge(3, "SUPPORTS", 4, 3),
    ]
    return [
        {
            "graph_identity": "ssgv1:graph:" + "8" * 64,
            "nodes": candidate_nodes,
            "edges": candidate_edges,
            "atom_dispositions": [
                {
                    "source_atom_id": "atom-1",
                    "primary_disposition": "SUPPORTS_PRESTRUCTURAL_CANDIDATE",
                }
            ],
            "metrics": {
                "atom_count": 1,
                "node_counts": _closed_counts(
                    inventory_v1._NODE_KINDS,
                    DOCUMENT=1,
                    PAGE=1,
                    TABLE=1,
                    ROW=1,
                    CELL_OR_VALUE_POSITION=1,
                    AXIS_OR_DIMENSION=1,
                    EVIDENCE=1,
                    UNRESOLVED_REGION=1,
                ),
                "edge_counts": _closed_counts(
                    inventory_v1._EDGE_KINDS,
                    PRESTRUCTURAL_CONTAINS=6,
                    SUPPORTS=4,
                    PRESTRUCTURAL_ALIGNED_TO_AXIS=1,
                ),
                "disposition_counts": _closed_counts(
                    inventory_v1._DISPOSITIONS,
                    SUPPORTS_PRESTRUCTURAL_CANDIDATE=1,
                ),
            },
        },
        {
            "graph_identity": "ssgv1:graph:" + "9" * 64,
            "nodes": terminal_nodes,
            "edges": terminal_edges,
            "atom_dispositions": [
                {"source_atom_id": "atom-2", "primary_disposition": "UPSTREAM_QUARANTINED"}
            ],
            "metrics": {
                "atom_count": 1,
                "node_counts": _closed_counts(
                    inventory_v1._NODE_KINDS,
                    DOCUMENT=1,
                    PAGE=1,
                    EVIDENCE=1,
                    UNRESOLVED_REGION=1,
                ),
                "edge_counts": _closed_counts(
                    inventory_v1._EDGE_KINDS,
                    PRESTRUCTURAL_CONTAINS=2,
                    SUPPORTS=1,
                ),
                "disposition_counts": _closed_counts(
                    inventory_v1._DISPOSITIONS,
                    UPSTREAM_QUARANTINED=1,
                ),
            },
        },
    ]


def _source_inventory(
    authority: FinalizedV3SurveyAuthority,
    projections: list[dict[str, Any]],
    proposals: list[dict[str, Any]],
) -> dict[str, Any]:
    pages = []
    for ordinal, (document_id, projection, proposal) in enumerate(
        zip(_DOCUMENT_IDS, projections, proposals, strict=True), start=1
    ):
        pages.append(
            {
                "request_ordinal": ordinal,
                "document_id": document_id,
                "physical_page": 1,
                "route": projection["route"],
                "status": projection["upstream_status"],
                "terminal": projection["terminal"],
                "projection_identity": projection["source_local_page_id"],
                "projection_sha256": canonical_json_sha256_v1(projection),
                "v2_geometry_proposal_projection_sha256": canonical_json_sha256_v1(proposal),
                "page_inventory_identity_sha256": f"{ordinal + 5}" * 64,
                "metrics": {
                    "atom_count": 1,
                    "proposal_kind_counts": {
                        "CONTINUATION_GEOMETRY_CANDIDATE": 0,
                        "SOURCE_BLOCK_CANDIDATE": 0,
                        "TABULAR_GEOMETRY_CANDIDATE": int(ordinal == 1),
                    },
                    "disposition_counts": {
                        "OWNED_BY_SOURCE_OBJECT": int(ordinal == 1),
                        "RETAINED_UNOWNED": 0,
                        "UPSTREAM_TERMINAL_UNRESOLVED": 0,
                        "UPSTREAM_QUARANTINED": int(ordinal == 2),
                    },
                },
            }
        )
    source = {
        "authority": _authority_payload(authority),
        "documents": [],
        "pages": pages,
        "corpus_metrics": {"page_count": 2, "terminal_page_count": 1},
    }
    source["inventory_identity_sha256"] = canonical_json_sha256_v1(source)
    return source


def _producer() -> dict[str, Any]:
    records = [
        {
            "phase": "READ",
            "kind": "IMPLEMENTATION",
            "path": path.as_posix(),
            "sha256": f"{index + 1:x}"[-1] * 64,
            "size_bytes": index + 1,
        }
        for index, path in enumerate(sorted(set(inventory_v1._IMPLEMENTATION_PATHS)))
    ]
    return {
        "git": {"commit": "f" * 40, "dirty": False},
        "implementation_ledger": {
            "records": records,
            "sha256": canonical_json_sha256_v1(records),
        },
    }


class _FakeStream:
    def __init__(
        self,
        authority: FinalizedV3SurveyAuthority,
        pages: list[AuthenticatedV3SurveyPage],
    ) -> None:
        self.authority = authority
        self._pages = pages

    def __iter__(self):
        return iter(self._pages)


def _patch_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, int]]:
    authority = _authority()
    projections = _projections()
    proposals = _proposal_projections(projections)
    graphs = _graphs()
    source = _source_inventory(authority, projections, proposals)
    source_payload = canonical_json_bytes_v1(source)
    producer = _producer()
    calls = {"projection": 0, "proposal": 0, "wrapper": 0, "graph": 0, "graph_validate": 0}
    pages = [
        AuthenticatedV3SurveyPage(
            page_record={
                "request_ordinal": ordinal,
                "document_id": document_id,
                "physical_page": 1,
            },
            page_result={"synthetic": ordinal},
        )
        for ordinal, document_id in enumerate(_DOCUMENT_IDS, start=1)
    ]

    @contextmanager
    def open_stream(_project_root: Path):
        yield _FakeStream(authority, pages)

    def project(*, page_record: dict[str, Any], page_result: dict[str, Any]):
        ordinal = page_record["request_ordinal"]
        assert page_result == {"synthetic": ordinal}
        calls["projection"] += 1
        return deepcopy(projections[ordinal - 1])

    def propose(projection: dict[str, Any]):
        calls["proposal"] += 1
        ordinal = projections.index(projection) + 1
        return {"synthetic_ordinal": ordinal}

    def wrap(projection: dict[str, Any], *, proposal_set_v1: dict[str, Any]):
        calls["wrapper"] += 1
        ordinal = proposal_set_v1["synthetic_ordinal"]
        assert projection == projections[ordinal - 1]
        return deepcopy(proposals[ordinal - 1])

    def build_graph(projection: dict[str, Any], proposal: dict[str, Any]):
        calls["graph"] += 1
        ordinal = proposal["proposal_set_v1"]["synthetic_ordinal"]
        assert projection == projections[ordinal - 1]
        return deepcopy(graphs[ordinal - 1])

    def validate_graph(
        graph: dict[str, Any],
        *,
        projection: dict[str, Any],
        proposal_projection: dict[str, Any],
    ):
        calls["graph_validate"] += 1
        ordinal = proposal_projection["proposal_set_v1"]["synthetic_ordinal"]
        assert projection == projections[ordinal - 1]
        assert graph == graphs[ordinal - 1]
        return deepcopy(graph)

    monkeypatch.setattr(inventory_v1, "FINALIZED_V3_SURVEY_AUTHORITY_V1", authority)
    monkeypatch.setattr(
        inventory_v1,
        "_SOURCE_INVENTORY_IDENTITY_SHA256",
        source["inventory_identity_sha256"],
    )
    monkeypatch.setattr(
        inventory_v1, "_SOURCE_INVENTORY_SHA256", sha256(source_payload).hexdigest()
    )
    monkeypatch.setattr(inventory_v1, "_SOURCE_INVENTORY_SIZE_BYTES", len(source_payload))
    monkeypatch.setattr(inventory_v1, "open_finalized_v3_survey_stream_v1", open_stream)
    monkeypatch.setattr(inventory_v1, "project_authenticated_page_v2", project)
    monkeypatch.setattr(inventory_v1, "generate_page_geometry_proposals_v1", propose)
    monkeypatch.setattr(inventory_v1, "make_page_proposal_set_v2", wrap)
    monkeypatch.setattr(inventory_v1, "build_page_prestructural_graph_v1", build_graph)
    monkeypatch.setattr(inventory_v1, "validate_page_prestructural_graph_v1", validate_graph)
    monkeypatch.setattr(inventory_v1, "validate_wave1_source_inventory_v1", deepcopy)
    monkeypatch.setattr(inventory_v1, "_load_source_inventory", lambda _root: deepcopy(source))
    monkeypatch.setattr(inventory_v1, "_producer_receipt", lambda _root: deepcopy(producer))
    monkeypatch.setattr(
        inventory_v1.sentinel,
        "_implementation_ledger",
        lambda _root, _commit, _paths: deepcopy(producer["implementation_ledger"]),
    )
    return source, producer, calls


def _refresh_topology(topology: dict[str, Any]) -> None:
    topology["topology_identity"] = "sspgiv1:topology:" + canonical_json_sha256_v1(
        {key: topology[key] for key in topology if key != "topology_identity"}
    )


def _refresh_page(page: dict[str, Any]) -> None:
    page["page_inventory_identity_sha256"] = canonical_json_sha256_v1(
        {key: page[key] for key in page if key != "page_inventory_identity_sha256"}
    )


def _refresh_inventory(inventory: dict[str, Any]) -> None:
    inventory["inventory_identity_sha256"] = canonical_json_sha256_v1(
        {key: inventory[key] for key in inventory if key != "inventory_identity_sha256"}
    )


def _reroll_inventory(inventory: dict[str, Any]) -> None:
    document_ids = inventory["authority"]["finalized_v3"]["document_ids"]
    inventory["documents"] = inventory_v1._rollup_documents(document_ids, inventory["pages"])
    inventory["corpus_metrics"] = inventory_v1._rollup_corpus(
        inventory["authority"]["finalized_v3"], inventory["pages"]
    )
    _refresh_inventory(inventory)


def test_builder_replays_every_page_and_retains_only_compact_graph_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source, _producer_value, calls = _patch_pipeline(monkeypatch)

    inventory = inventory_v1.build_wave1_prestructural_graph_inventory_v1(tmp_path)

    assert calls == {
        "projection": 2,
        "proposal": 2,
        "wrapper": 2,
        "graph": 2,
        "graph_validate": 2,
    }
    assert inventory["corpus_metrics"]["document_count"] == 2
    assert inventory["corpus_metrics"]["page_count"] == 2
    assert inventory["corpus_metrics"]["source_accounted_page_count"] == 2
    assert inventory["corpus_metrics"]["terminal_page_count"] == 1
    assert inventory["corpus_metrics"]["atom_count"] == 2
    assert inventory["corpus_metrics"]["node_counts"]["TABLE"] == 1
    assert inventory["corpus_metrics"]["node_counts"]["EVIDENCE"] == 2
    assert inventory["corpus_metrics"]["disposition_counts"] == {
        "SUPPORTS_PRESTRUCTURAL_CANDIDATE": 1,
        "RETAINED_UNRESOLVED": 0,
        "UPSTREAM_TERMINAL_UNRESOLVED": 0,
        "UPSTREAM_QUARANTINED": 1,
    }
    assert len(inventory["documents"]) == 2
    assert len(inventory["pages"]) == len(source["pages"]) == 2
    forbidden = {
        "nodes",
        "edges",
        "atom_dispositions",
    }
    payload_forbidden = {
        "canonical_bbox_mpt",
        "source_atom_ids",
        "source_proposal_ids",
        "text",
    }
    for page in inventory["pages"]:
        assert forbidden.isdisjoint(page)
        assert payload_forbidden.isdisjoint(page["candidate_topology"])
        assert all(
            payload_forbidden.isdisjoint(node) for node in page["candidate_topology"]["nodes"]
        )
        assert all(edge["kind"] != "SUPPORTS" for edge in page["candidate_topology"]["edges"])
    assert inventory["pages"][0]["candidate_topology"]["nodes"][-1]["kind"] == ("AXIS_OR_DIMENSION")
    assert inventory["pages"][1]["candidate_topology"]["nodes"][-1]["kind"] == ("UNRESOLVED_REGION")
    assert inventory["safety"]["table_claimed"] is False
    assert inventory["safety"]["role_a_used"] is False
    assert inventory["safety"]["model_or_ocr_invoked"] is False


def test_candidate_topology_drops_payload_identity_but_preserves_relations() -> None:
    first_graph = _graphs()[0]
    renamed = deepcopy(first_graph)
    for node in renamed["nodes"]:
        old_id = node["node_id"]
        new_id = "renamed-" + old_id
        node["node_id"] = new_id
        for edge in renamed["edges"]:
            if edge["from_node_id"] == old_id:
                edge["from_node_id"] = new_id
            if edge["to_node_id"] == old_id:
                edge["to_node_id"] = new_id
    for node in renamed["nodes"]:
        node["source_atom_ids"] = ["different"] * len(node["source_atom_ids"])
        node["source_proposal_ids"] = ["different"] * len(node["source_proposal_ids"])

    original_topology = inventory_v1._compact_candidate_topology(first_graph)
    renamed_topology = inventory_v1._compact_candidate_topology(renamed)

    assert renamed_topology == original_topology
    assert len(original_topology["nodes"]) == 7
    assert len(original_topology["edges"]) == 7
    assert all(node["kind"] != "EVIDENCE" for node in original_topology["nodes"])
    assert all(edge["kind"] != "SUPPORTS" for edge in original_topology["edges"])


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda value: value["pages"][0]["graph_metrics"]["disposition_counts"].update(
                {"SUPPORTS_PRESTRUCTURAL_CANDIDATE": 0}
            ),
            "source accounting",
        ),
        (
            lambda value: value["pages"][0].update({"nodes": []}),
            "fields drifted",
        ),
        (
            lambda value: value["pages"].pop(),
            "page denominator",
        ),
        (
            lambda value: value["authority"]["source_inventory"].update({"sha256": "0" * 64}),
            "authority pin",
        ),
    ],
)
def test_validator_rejects_count_payload_denominator_and_authority_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mutation,
    message: str,
) -> None:
    source, _producer_value, _calls = _patch_pipeline(monkeypatch)
    inventory = inventory_v1.build_wave1_prestructural_graph_inventory_v1(tmp_path)
    broken = deepcopy(inventory)
    mutation(broken)
    _refresh_inventory(broken)

    with pytest.raises(inventory_v1.Wave1PrestructuralGraphInventoryV1Error, match=message):
        inventory_v1.validate_wave1_prestructural_graph_inventory_v1(
            broken,
            project_root=tmp_path,
            source_inventory=source,
        )


def test_validator_rejects_payload_free_topology_relation_drift_even_when_rehashed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source, _producer_value, _calls = _patch_pipeline(monkeypatch)
    inventory = inventory_v1.build_wave1_prestructural_graph_inventory_v1(tmp_path)
    broken = deepcopy(inventory)
    edge = broken["pages"][0]["candidate_topology"]["edges"][2]
    edge["to_node_ordinal"] = 5
    _refresh_topology(broken["pages"][0]["candidate_topology"])
    _refresh_page(broken["pages"][0])
    _refresh_inventory(broken)

    with pytest.raises(
        inventory_v1.Wave1PrestructuralGraphInventoryV1Error,
        match="containment relation",
    ):
        inventory_v1.validate_wave1_prestructural_graph_inventory_v1(
            broken,
            project_root=tmp_path,
            source_inventory=source,
        )


def test_validator_rejects_source_inventory_cross_binding_after_rehash(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source, _producer_value, _calls = _patch_pipeline(monkeypatch)
    inventory = inventory_v1.build_wave1_prestructural_graph_inventory_v1(tmp_path)
    broken = deepcopy(inventory)
    broken["pages"][0]["source_projection_sha256"] = "0" * 64
    _refresh_page(broken["pages"][0])
    _refresh_inventory(broken)

    with pytest.raises(
        inventory_v1.Wave1PrestructuralGraphInventoryV1Error,
        match="differs from compact source inventory",
    ):
        inventory_v1.validate_wave1_prestructural_graph_inventory_v1(
            broken,
            project_root=tmp_path,
            source_inventory=source,
        )


def test_validator_rejects_forged_graph_atom_denominator_after_every_rollup_is_rehashed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source, _producer_value, _calls = _patch_pipeline(monkeypatch)
    inventory = inventory_v1.build_wave1_prestructural_graph_inventory_v1(tmp_path)
    broken = deepcopy(inventory)
    page = broken["pages"][0]
    page["graph_metrics"]["atom_count"] = 2
    page["graph_metrics"]["node_counts"]["EVIDENCE"] = 2
    page["graph_metrics"]["edge_counts"]["SUPPORTS"] = 7
    page["graph_metrics"]["disposition_counts"]["SUPPORTS_PRESTRUCTURAL_CANDIDATE"] = 2
    for node in page["candidate_topology"]["nodes"]:
        if node["kind"] in {"TABLE", "ROW", "CELL_OR_VALUE_POSITION"}:
            node["source_atom_count"] = 2
    _refresh_topology(page["candidate_topology"])
    _refresh_page(page)
    _reroll_inventory(broken)

    with pytest.raises(
        inventory_v1.Wave1PrestructuralGraphInventoryV1Error,
        match="graph/source atom-disposition",
    ):
        inventory_v1.validate_wave1_prestructural_graph_inventory_v1(
            broken,
            project_root=tmp_path,
            source_inventory=source,
        )


def test_validator_rejects_forged_upstream_disposition_after_every_rollup_is_rehashed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source, _producer_value, _calls = _patch_pipeline(monkeypatch)
    inventory = inventory_v1.build_wave1_prestructural_graph_inventory_v1(tmp_path)
    broken = deepcopy(inventory)
    page = broken["pages"][1]
    page["graph_metrics"]["disposition_counts"]["UPSTREAM_QUARANTINED"] = 0
    page["graph_metrics"]["disposition_counts"]["UPSTREAM_TERMINAL_UNRESOLVED"] = 1
    _refresh_page(page)
    _reroll_inventory(broken)

    with pytest.raises(
        inventory_v1.Wave1PrestructuralGraphInventoryV1Error,
        match="graph/source atom-disposition",
    ):
        inventory_v1.validate_wave1_prestructural_graph_inventory_v1(
            broken,
            project_root=tmp_path,
            source_inventory=source,
        )


def test_validator_binds_candidate_and_unresolved_atoms_to_exact_graph_dispositions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source, _producer_value, _calls = _patch_pipeline(monkeypatch)
    inventory = inventory_v1.build_wave1_prestructural_graph_inventory_v1(tmp_path)
    broken = deepcopy(inventory)
    page = broken["pages"][0]
    page["graph_metrics"]["disposition_counts"]["SUPPORTS_PRESTRUCTURAL_CANDIDATE"] = 0
    page["graph_metrics"]["disposition_counts"]["RETAINED_UNRESOLVED"] = 1
    _refresh_page(page)
    _reroll_inventory(broken)

    with pytest.raises(
        inventory_v1.Wave1PrestructuralGraphInventoryV1Error,
        match="atom disposition partition",
    ):
        inventory_v1.validate_wave1_prestructural_graph_inventory_v1(
            broken,
            project_root=tmp_path,
            source_inventory=source,
        )


def test_validator_requires_exact_parent_coverage_for_every_retained_candidate_node(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source, _producer_value, _calls = _patch_pipeline(monkeypatch)
    inventory = inventory_v1.build_wave1_prestructural_graph_inventory_v1(tmp_path)
    broken = deepcopy(inventory)
    page = broken["pages"][0]
    page["candidate_topology"]["nodes"].append(
        {
            "ordinal": 8,
            "kind": "ROW",
            "status": "PRESTRUCTURAL_CANDIDATE",
            "source_atom_count": 1,
            "source_proposal_count": 1,
        }
    )
    page["graph_metrics"]["node_counts"]["ROW"] = 2
    page["graph_metrics"]["edge_counts"]["SUPPORTS"] = 5
    _refresh_topology(page["candidate_topology"])
    _refresh_page(page)
    _reroll_inventory(broken)

    with pytest.raises(
        inventory_v1.Wave1PrestructuralGraphInventoryV1Error,
        match="exact containment coverage",
    ):
        inventory_v1.validate_wave1_prestructural_graph_inventory_v1(
            broken,
            project_root=tmp_path,
            source_inventory=source,
        )


def test_validator_rejects_impossible_rehashed_row_atom_inflation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source, _producer_value, _calls = _patch_pipeline(monkeypatch)
    inventory = inventory_v1.build_wave1_prestructural_graph_inventory_v1(tmp_path)
    broken = deepcopy(inventory)
    page = broken["pages"][0]
    row = next(node for node in page["candidate_topology"]["nodes"] if node["kind"] == "ROW")
    row["source_atom_count"] = 2
    page["graph_metrics"]["edge_counts"]["SUPPORTS"] = 5
    _refresh_topology(page["candidate_topology"])
    _refresh_page(page)
    _reroll_inventory(broken)

    with pytest.raises(
        inventory_v1.Wave1PrestructuralGraphInventoryV1Error,
        match="table/row source partition",
    ):
        inventory_v1.validate_wave1_prestructural_graph_inventory_v1(
            broken,
            project_root=tmp_path,
            source_inventory=source,
        )


def test_validator_requires_contiguous_retained_edge_ordinals(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source, _producer_value, _calls = _patch_pipeline(monkeypatch)
    inventory = inventory_v1.build_wave1_prestructural_graph_inventory_v1(tmp_path)
    broken = deepcopy(inventory)
    page = broken["pages"][0]
    page["candidate_topology"]["edges"][-1]["ordinal"] = 9
    _refresh_topology(page["candidate_topology"])
    _refresh_page(page)
    _refresh_inventory(broken)

    with pytest.raises(
        inventory_v1.Wave1PrestructuralGraphInventoryV1Error,
        match="edge order",
    ):
        inventory_v1.validate_wave1_prestructural_graph_inventory_v1(
            broken,
            project_root=tmp_path,
            source_inventory=source,
        )


def test_validator_rejects_rehashed_self_source_order_edge(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source, _producer_value, _calls = _patch_pipeline(monkeypatch)
    inventory = inventory_v1.build_wave1_prestructural_graph_inventory_v1(tmp_path)
    broken = deepcopy(inventory)
    page = broken["pages"][0]
    page["candidate_topology"]["edges"].append(
        {
            "ordinal": 8,
            "kind": "PRECEDES_IN_AUTHENTICATED_SOURCE_ORDER",
            "from_node_ordinal": 5,
            "to_node_ordinal": 5,
        }
    )
    page["graph_metrics"]["edge_counts"]["PRECEDES_IN_AUTHENTICATED_SOURCE_ORDER"] = 1
    _refresh_topology(page["candidate_topology"])
    _refresh_page(page)
    _reroll_inventory(broken)

    with pytest.raises(
        inventory_v1.Wave1PrestructuralGraphInventoryV1Error,
        match="self-edge",
    ):
        inventory_v1.validate_wave1_prestructural_graph_inventory_v1(
            broken,
            project_root=tmp_path,
            source_inventory=source,
        )


def test_validator_requires_supplied_source_object_to_reproduce_exact_raw_pin(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source, _producer_value, _calls = _patch_pipeline(monkeypatch)
    inventory = inventory_v1.build_wave1_prestructural_graph_inventory_v1(tmp_path)
    forged_source = deepcopy(source)
    forged_source["corpus_metrics"]["page_count"] = 3
    forged_source["inventory_identity_sha256"] = canonical_json_sha256_v1(
        {key: forged_source[key] for key in forged_source if key != "inventory_identity_sha256"}
    )

    with pytest.raises(
        inventory_v1.Wave1PrestructuralGraphInventoryV1Error,
        match="exact raw/logical pin",
    ):
        inventory_v1.validate_wave1_prestructural_graph_inventory_v1(
            inventory,
            project_root=tmp_path,
            source_inventory=forged_source,
        )


def test_validator_replays_exact_committed_producer_ledger(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source, producer, _calls = _patch_pipeline(monkeypatch)
    inventory = inventory_v1.build_wave1_prestructural_graph_inventory_v1(tmp_path)
    broken = deepcopy(inventory)
    broken["producer"]["implementation_ledger"]["records"][0]["path"] = "wrong.py"
    broken["producer"]["implementation_ledger"]["sha256"] = canonical_json_sha256_v1(
        broken["producer"]["implementation_ledger"]["records"]
    )
    _refresh_inventory(broken)

    with pytest.raises(
        inventory_v1.Wave1PrestructuralGraphInventoryV1Error,
        match="role/path",
    ):
        inventory_v1.validate_wave1_prestructural_graph_inventory_v1(
            broken,
            project_root=tmp_path,
            source_inventory=source,
        )
    assert inventory["producer"] == producer
    assert [record["path"] for record in producer["implementation_ledger"]["records"]] == [
        path.as_posix() for path in sorted(set(inventory_v1._IMPLEMENTATION_PATHS))
    ]


def test_exclusive_publisher_seals_one_read_only_inode_and_refuses_overwrite(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    relative = Path("out/prestructural.json")
    (tmp_path / relative.parent).mkdir(parents=True)
    monkeypatch.setattr(
        inventory_v1,
        "WAVE1_PRESTRUCTURAL_GRAPH_INVENTORY_OUTPUT_RELATIVE_PATH_V1",
        relative,
    )
    payload = canonical_json_bytes_v1({"candidate_only": True})

    path = inventory_v1._publish_canonical_exclusive(tmp_path, payload)

    identity = path.stat()
    assert path.read_bytes() == payload
    assert stat.S_IMODE(identity.st_mode) == 0o444
    assert identity.st_nlink == 1
    assert not list(path.parent.glob(f".{path.name}.*.tmp"))
    with pytest.raises(
        inventory_v1.Wave1PrestructuralGraphInventoryV1Error,
        match="destination already exists",
    ):
        inventory_v1._publish_canonical_exclusive(tmp_path, payload)


def test_exclusive_publisher_cleans_owned_temporary_after_link_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    relative = Path("out/prestructural.json")
    (tmp_path / relative.parent).mkdir(parents=True)
    monkeypatch.setattr(
        inventory_v1,
        "WAVE1_PRESTRUCTURAL_GRAPH_INVENTORY_OUTPUT_RELATIVE_PATH_V1",
        relative,
    )
    monkeypatch.setattr(
        inventory_v1.os,
        "link",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("link failed")),
    )

    with pytest.raises(
        inventory_v1.Wave1PrestructuralGraphInventoryV1Error,
        match="publication failed",
    ):
        inventory_v1._publish_canonical_exclusive(
            tmp_path,
            canonical_json_bytes_v1({"candidate_only": True}),
        )

    assert not (tmp_path / relative).exists()
    assert not list((tmp_path / relative.parent).iterdir())


def test_publication_race_preserves_competitor_and_cleans_only_owned_temporary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    relative = Path("out/prestructural.json")
    parent = tmp_path / relative.parent
    parent.mkdir(parents=True)
    monkeypatch.setattr(
        inventory_v1,
        "WAVE1_PRESTRUCTURAL_GRAPH_INVENTORY_OUTPUT_RELATIVE_PATH_V1",
        relative,
    )
    competitor = b"competitor\n"
    real_link = os.link
    raced = False

    def race_link(
        src: str,
        dst: str,
        *,
        src_dir_fd: int,
        dst_dir_fd: int,
        follow_symlinks: bool,
    ) -> None:
        nonlocal raced
        if not raced:
            raced = True
            descriptor = os.open(
                dst,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o444,
                dir_fd=dst_dir_fd,
            )
            try:
                os.write(descriptor, competitor)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        real_link(
            src,
            dst,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )

    monkeypatch.setattr(inventory_v1.os, "link", race_link)
    with pytest.raises(
        inventory_v1.Wave1PrestructuralGraphInventoryV1Error,
        match="exclusive race",
    ):
        inventory_v1._publish_canonical_exclusive(
            tmp_path,
            canonical_json_bytes_v1({"candidate_only": True}),
        )

    assert raced is True
    assert (tmp_path / relative).read_bytes() == competitor
    assert sorted(item.name for item in parent.iterdir()) == [relative.name]


def test_postlink_precommit_directory_fsync_failure_rolls_back_both_owned_names(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    relative = Path("out/prestructural.json")
    parent = tmp_path / relative.parent
    parent.mkdir(parents=True)
    monkeypatch.setattr(
        inventory_v1,
        "WAVE1_PRESTRUCTURAL_GRAPH_INVENTORY_OUTPUT_RELATIVE_PATH_V1",
        relative,
    )
    real_fsync = os.fsync
    failed = False

    def fail_first_directory_fsync(descriptor: int) -> None:
        nonlocal failed
        if not failed and stat.S_ISDIR(os.fstat(descriptor).st_mode):
            failed = True
            raise OSError("injected directory fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(inventory_v1.os, "fsync", fail_first_directory_fsync)
    with pytest.raises(
        inventory_v1.Wave1PrestructuralGraphInventoryV1Error,
        match="publication failed",
    ):
        inventory_v1._publish_canonical_exclusive(
            tmp_path,
            canonical_json_bytes_v1({"candidate_only": True}),
        )

    assert failed is True
    assert list(parent.iterdir()) == []


def test_public_publisher_revalidates_authority_and_producer_before_exclusive_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    inventory = {"producer": {"git": "receipt"}, "inventory_identity_sha256": "a" * 64}
    source = {"source": "authority"}
    target = tmp_path / "published.json"
    calls: list[str] = []
    monkeypatch.setattr(
        inventory_v1, "_require_destination_absent", lambda _root: calls.append("absent")
    )
    monkeypatch.setattr(
        inventory_v1,
        "build_wave1_prestructural_graph_inventory_v1",
        lambda _root: deepcopy(inventory),
    )
    monkeypatch.setattr(inventory_v1, "_load_source_inventory", lambda _root: deepcopy(source))
    monkeypatch.setattr(
        inventory_v1,
        "validate_wave1_prestructural_graph_inventory_v1",
        lambda value, *, project_root, source_inventory: calls.append("validate") or value,
    )
    monkeypatch.setattr(
        inventory_v1,
        "_producer_receipt",
        lambda _root: deepcopy(inventory["producer"]),
    )
    monkeypatch.setattr(
        inventory_v1,
        "_publish_canonical_exclusive",
        lambda _root, _payload: calls.append("publish") or target,
    )

    result = inventory_v1.publish_wave1_prestructural_graph_inventory_v1(tmp_path)
    payload = canonical_json_bytes_v1(inventory)

    assert calls == ["absent", "validate", "publish"]
    assert result == (
        target,
        sha256(payload).hexdigest(),
        len(payload),
        "a" * 64,
    )


def test_module_has_no_role_a_schema_pdf_model_or_ocr_execution_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert all("role_a" not in name for name in imports)
    assert all("schema" not in name for name in imports)
    assert all("model" not in name for name in imports)
    assert all("pdf" not in name for name in imports)
    assert inventory_v1._SAFETY["source_pdf_opened"] is False
    assert inventory_v1._SAFETY["model_or_ocr_invoked"] is False
    assert inventory_v1._SAFETY["bank_identity_used_for_routing"] is False
    assert inventory_v1._SAFETY["physical_page_used_for_routing"] is False
    assert inventory_v1._SAFETY["role_a_used"] is False
    assert inventory_v1._SAFETY["schema_used_for_routing"] is False
    assert "os.replace" not in MODULE_PATH.read_text(encoding="utf-8")

    implementation_paths = set(inventory_v1._IMPLEMENTATION_PATHS)
    package_root = Path("src/bctc_ai")

    def with_package_initializers(relative: Path) -> set[Path]:
        resolved = {relative}
        parent = relative.parent
        while parent == package_root or package_root in parent.parents:
            initializer = parent / "__init__.py"
            if (PROJECT_ROOT / initializer).is_file():
                resolved.add(initializer)
            if parent == package_root:
                break
            parent = parent.parent
        return resolved

    def local_module_path(module: str) -> Path | None:
        if not module.startswith("bctc_ai"):
            return None
        candidate = Path("src", *module.split(".")).with_suffix(".py")
        if (PROJECT_ROOT / candidate).is_file():
            return candidate
        initializer = Path("src", *module.split("."), "__init__.py")
        return initializer if (PROJECT_ROOT / initializer).is_file() else None

    start = Path("src/bctc_ai/source_structure/wave1_prestructural_graph_inventory_v1.py")
    closure = with_package_initializers(start)
    pending = list(closure)
    while pending:
        relative = pending.pop()
        local_tree = ast.parse((PROJECT_ROOT / relative).read_text(encoding="utf-8"))
        for node in ast.walk(local_tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules = [
                    node.module,
                    *(f"{node.module}.{alias.name}" for alias in node.names),
                ]
            for module in modules:
                candidate = local_module_path(module)
                if candidate is None:
                    continue
                for discovered in with_package_initializers(candidate) - closure:
                    closure.add(discovered)
                    pending.append(discovered)

    sealed_support = Path("src/bctc_ai/corpus/wave1_pre_ocr_structure.py")
    closure.update(with_package_initializers(sealed_support))

    assert closure == implementation_paths
    assert len(implementation_paths) == 33


def test_output_name_is_one_fixed_corpus_artifact_path() -> None:
    path = PROJECT_ROOT / inventory_v1.WAVE1_PRESTRUCTURAL_GRAPH_INVENTORY_OUTPUT_RELATIVE_PATH_V1
    assert os.fspath(path).endswith("wave-1-role-b-prestructural-graph-inventory-v1.json")
