from __future__ import annotations

import json
from copy import deepcopy

import pytest

from bctc_ai.source_structure import semantic_local_accounting_graph_v2 as graph_v2
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from bctc_ai.source_structure.local_accounting_graph_v1 import (
    LOAN_MATURITY_BUCKETS_SPEC_V1,
    LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    local_accounting_family_spec_sha256_v1,
)

SPECS = (
    LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    LOAN_MATURITY_BUCKETS_SPEC_V1,
)


def _span(
    index: int,
    text: str,
    *,
    semantic: bool,
    role: str | None = None,
    x: int = 100,
    y: int | None = None,
) -> dict:
    top = index * 30 if y is None else y
    result = {
        "source_line_index": index,
        "source_atom_id": f"ssv1:atom:{index:064x}",
        "raw_pixel_bbox": [x, top, x + 100, top + 20],
        "canonical_bbox_mpt": [x * 10, top * 10, (x + 100) * 10, (top + 20) * 10],
    }
    if semantic:
        result.update(
            {
                "transformer_text_nfc": text,
                "accentless_comparison_key": text.casefold(),
                "match_kind": "ACCENTLESS_ALIAS",
                "presentation_normalization": "NONE",
                "promotion_status": "PROMOTED_BY_UNIQUE_COMPLETE_TOPOLOGY",
                "semantic_text_source": "VIETOCR_VGG_TRANSFORMER_0_3_13",
            }
        )
        if role is not None:
            result["role"] = role
    else:
        result.update({"raw_text": text, "text_source": "PPOCRV6_NUMERIC_ONLY"})
    return result


def _accepted_observation() -> dict:
    owner = _span(0, "CHO VAY KHÁCH HÀNG", semantic=True, role="OWNER", y=100)
    branch = _span(
        1,
        "Phân tích dư nợ theo thời hạn gốc của khoản vay",
        semantic=True,
        role="BRANCH",
        y=140,
    )
    axes = []
    for axis_index, (index, text, period, x) in enumerate(
        ((2, "30/06/2026", "DATE:2026-06-30", 500), (3, "31/12/2025", "DATE:2025-12-31", 700))
    ):
        axis = _span(index, text, semantic=False, x=x, y=180)
        axis.update(
            {
                "axis_index": axis_index,
                "period": period,
                "text_source": "PPOCRV6_DATE_ONLY",
            }
        )
        axes.append(axis)
    units = []
    for index, x in ((4, 500), (5, 700)):
        unit = _span(index, "Triệu đồng", semantic=True, x=x, y=210)
        unit.pop("match_kind")
        unit.pop("presentation_normalization")
        unit.pop("promotion_status")
        unit["unit"] = {
            "basis": "LOCAL_VISIBLE_UNIT",
            "currency": "VND",
            "scale": 1_000_000,
        }
        units.append(unit)
    roles = (
        ("SHORT_TERM", "Nợ ngắn hạn", (10, 1)),
        ("MEDIUM_TERM", "Nợ trung hạn", (20, 2)),
        ("LONG_TERM", "Nợ dài hạn", (30, 3)),
    )
    rows = []
    next_index = 6
    for row_index, (role, text, values) in enumerate(roles):
        y = 250 + row_index * 40
        label = _span(next_index, text, semantic=True, role=role, y=y)
        next_index += 1
        positions = []
        for axis_index, (value, x) in enumerate(zip(values, (500, 700), strict=True)):
            position = _span(next_index, str(value), semantic=False, x=x, y=y)
            position.update(
                {
                    "axis_index": axis_index,
                    "normalized_decimal": str(value),
                    "state": "OBSERVED_VALUE",
                }
            )
            next_index += 1
            positions.append(position)
        rows.append({"role": role, "label": label, "value_positions": positions})
    total_positions = []
    for axis_index, (value, x) in enumerate(zip((60, 6), (500, 700), strict=True)):
        position = _span(next_index, str(value), semantic=False, x=x, y=370)
        position.update(
            {
                "axis_index": axis_index,
                "normalized_decimal": str(value),
                "state": "OBSERVED_VALUE",
            }
        )
        next_index += 1
        total_positions.append(position)
    rows.append(
        {
            "role": "TOTAL",
            "label": None,
            "total_resolution": "IMMEDIATE_UNLABELED_NUMERIC_ROW",
            "value_positions": total_positions,
        }
    )
    region = {
        "canonical_bbox_mpt": [1000, 1000, 8000, 3900],
        "owner_label": owner,
        "branch_label": branch,
        "axes": axes,
        "local_unit_labels": units,
        "rows": rows,
        "arithmetic": {"status": "CORROBORATED", "evaluated_axis_indexes": [0, 1]},
        "topology": {
            "owner_resolution": True,
            "parent_child_edge": True,
            "ordered_sibling_set": True,
            "comparative_period_axis": True,
            "unit_scope_edge": True,
            "total_subtotal": True,
            "internal_additive_closure": True,
            "same_population_claimed": False,
            "row_frontier": True,
        },
    }
    scope = {spec.family_id: local_accounting_family_spec_sha256_v1(spec) for spec in SPECS}
    return {
        "format_version": "BANK_CORPUS_SEMANTIC_LOCAL_ACCOUNTING_OBSERVATION_CANDIDATE_V2",
        "claim_boundary": "test",
        "source_local_page_id": "ssv2:page:" + "1" * 64,
        "source_projection_sha256": "2" * 64,
        "semantic_page_binding_sha256": "3" * 64,
        "family_id": LOAN_MATURITY_BUCKETS_SPEC_V1.family_id,
        "family_spec_sha256": local_accounting_family_spec_sha256_v1(LOAN_MATURITY_BUCKETS_SPEC_V1),
        "supplied_family_collision_scope_spec_sha256_by_id": scope,
        "status": "READY_FOR_GRAPH_V2",
        "candidate_regions": [region],
        "unresolved_reasons": [],
        "readiness": {
            "complete_topology_count": 1,
            "unique_complete_topology": True,
            "accentless_candidates_promoted_by_topology": True,
            "ready_within_supplied_family_collision_scope": True,
            "globally_collision_free_claimed": False,
            "graph_v1_accepted": False,
        },
        "safety": {},
    }


@pytest.fixture
def replay_inputs(monkeypatch: pytest.MonkeyPatch):
    projection = object()
    binding = object()
    receipt = object()
    observation = _accepted_observation()

    def build(source, page, authority, spec, scope):
        assert (source, page, authority) == (projection, binding, receipt)
        assert spec is LOAN_MATURITY_BUCKETS_SPEC_V1
        assert scope is SPECS
        return deepcopy(observation)

    monkeypatch.setattr(
        graph_v2,
        "build_semantic_local_accounting_observation_candidate_v2",
        build,
    )
    return projection, binding, receipt, observation


def _build(replay_inputs):
    projection, binding, receipt, _observation = replay_inputs
    return graph_v2.build_semantic_local_accounting_graph_v2(
        projection,
        binding,
        receipt,
        LOAN_MATURITY_BUCKETS_SPEC_V1,
        SPECS,
    )


def test_accepted_graph_is_closed_persistable_and_bounded(replay_inputs) -> None:
    graph = _build(replay_inputs)

    assert graph["status"] == "ACCEPTED_WITHIN_SUPPLIED_FAMILY_COLLISION_SCOPE"
    assert graph["graph_id"].startswith("slagv2:graph:")
    assert json.loads(json.dumps(graph, ensure_ascii=False)) == graph
    assert graph["acceptance_scope"] == {
        "supplied_family_collision_scope_only": True,
        "ready_within_supplied_family_collision_scope": True,
        "globally_collision_free_claimed": False,
        "family_registry_exhaustiveness_claimed": False,
        "page_family_exhaustiveness_claimed": False,
        "target_family_evaluated_only": True,
        "non_target_supplied_families_used_for_collision_only": True,
        "non_target_supplied_family_dispositions_claimed": False,
    }
    assert (
        graph["supplied_family_collision_scope_spec_sha256_by_id"]
        == (replay_inputs[3]["supplied_family_collision_scope_spec_sha256_by_id"])
    )
    assert graph["supplied_family_evaluation_partition"] == {
        "LOAN_MATURITY_BUCKETS": {
            "use": "TARGET_FAMILY_EVALUATED",
            "disposition": "ACCEPTED_WITHIN_SUPPLIED_FAMILY_COLLISION_SCOPE",
        },
        "LOAN_QUALITY_CLASSIFICATION": {
            "use": "COLLISION_SCOPE_ONLY",
            "disposition": "NOT_EVALUATED",
        },
    }
    assert graph["arithmetic"] == {
        "status": "CORROBORATED",
        "evaluated_axis_indexes": [0, 1],
        "internal_additive_closure_only": True,
        "same_population_claimed": False,
    }
    assert graph["safety"]["canonicalization_authority"] is False
    assert graph["safety"]["schema_mapping_authority"] is False
    assert graph["safety"]["export_authority"] is False
    assert graph["safety"]["target_family_evaluated_only"] is True
    assert graph["safety"]["non_target_supplied_family_dispositions_claimed"] is False


def test_every_node_edge_and_evidence_is_closed(replay_inputs) -> None:
    graph = _build(replay_inputs)
    node_ids = {node["node_id"] for node in graph["nodes"]}
    evidence_ids = {node["node_id"] for node in graph["nodes"] if node["kind"] == "EVIDENCE"}

    assert len(node_ids) == len(graph["nodes"])
    assert graph["metrics"]["orphan_node_count"] == 0
    assert graph["metrics"]["orphan_evidence_count"] == 0
    assert graph["metrics"]["invalid_edge_count"] == 0
    assert evidence_ids
    assert all(
        edge["from_node_id"] in node_ids
        and edge["to_node_id"] in node_ids
        and set(edge["evidence_node_ids"]) <= evidence_ids
        and edge["evidence_node_ids"]
        for edge in graph["edges"]
    )
    supported = {edge["to_node_id"] for edge in graph["edges"] if edge["kind"] == "SUPPORTED_BY"}
    assert supported == evidence_ids


def test_text_authority_is_split_by_evidence_role(replay_inputs) -> None:
    graph = _build(replay_inputs)
    evidence = [node for node in graph["nodes"] if node["kind"] == "EVIDENCE"]
    semantic = [
        node
        for node in evidence
        if node["attributes"]["evidence_role"]
        in {"OWNER_LABEL", "BRANCH_LABEL", "ROW_LABEL", "UNIT_LABEL"}
    ]
    numeric_or_date = [node for node in evidence if node not in semantic]

    assert all(
        node["attributes"]["text_source"] == "VIETOCR_VGG_TRANSFORMER_0_3_13"
        and node["attributes"]["semantic_identity_authority"] is True
        and node["attributes"]["numeric_authority"] is False
        for node in semantic
    )
    assert all(
        node["attributes"]["text_source"].startswith("PPOCRV6_")
        and node["attributes"]["semantic_identity_authority"] is False
        for node in numeric_or_date
    )


def test_unresolved_observation_persists_no_accepted_graph(
    replay_inputs, monkeypatch: pytest.MonkeyPatch
) -> None:
    unresolved = deepcopy(replay_inputs[3])
    unresolved["status"] = "UNRESOLVED"
    unresolved["candidate_regions"] = []
    unresolved["unresolved_reasons"] = ["OWNER_NOT_RESOLVED_FROM_TRANSFORMER"]
    unresolved["readiness"]["complete_topology_count"] = 0
    unresolved["readiness"]["unique_complete_topology"] = False
    unresolved["readiness"]["accentless_candidates_promoted_by_topology"] = False
    unresolved["readiness"]["ready_within_supplied_family_collision_scope"] = False
    monkeypatch.setattr(
        graph_v2,
        "build_semantic_local_accounting_observation_candidate_v2",
        lambda *_args: deepcopy(unresolved),
    )

    graph = _build(replay_inputs)

    assert graph["status"] == "UNRESOLVED"
    assert graph["nodes"] == []
    assert graph["edges"] == []
    assert graph["metrics"]["accepted_region_count"] == 0
    assert graph["unresolved_reasons"] == ["OWNER_NOT_RESOLVED_FROM_TRANSFORMER"]


def test_replay_rejects_forged_persisted_nodes_and_scope(replay_inputs) -> None:
    graph = _build(replay_inputs)
    projection, binding, receipt, _observation = replay_inputs
    replayed = graph_v2.validate_semantic_local_accounting_graph_replay_v2(
        graph,
        projection,
        binding,
        receipt,
        LOAN_MATURITY_BUCKETS_SPEC_V1,
        SPECS,
    )
    assert replayed == graph

    for forged in (deepcopy(graph), deepcopy(graph)):
        if forged is not None and forged["nodes"][0]["kind"] == "TABLE":
            forged["nodes"][0]["attributes"]["same_population_claimed"] = True
        with pytest.raises(graph_v2.SemanticLocalAccountingGraphV2Error):
            graph_v2.validate_semantic_local_accounting_graph_replay_v2(
                forged,
                projection,
                binding,
                receipt,
                LOAN_MATURITY_BUCKETS_SPEC_V1,
                SPECS,
            )
        break

    forged_scope = deepcopy(graph)
    forged_scope["acceptance_scope"]["globally_collision_free_claimed"] = True
    with pytest.raises(graph_v2.SemanticLocalAccountingGraphV2Error):
        graph_v2.validate_semantic_local_accounting_graph_replay_v2(
            forged_scope,
            projection,
            binding,
            receipt,
            LOAN_MATURITY_BUCKETS_SPEC_V1,
            SPECS,
        )


def test_graph_identity_binds_the_exact_observation_candidate(replay_inputs) -> None:
    graph = _build(replay_inputs)

    assert graph["observation_candidate_sha256"] == canonical_json_sha256_v1(replay_inputs[3])


def _rehash_edge_and_graph(graph: dict, edge_index: int) -> None:
    edge = graph["edges"][edge_index]
    edge["edge_id"] = "slagv2:edge:" + canonical_json_sha256_v1(
        {key: value for key, value in edge.items() if key != "edge_id"}
    )
    graph["graph_id"] = "slagv2:graph:" + canonical_json_sha256_v1(
        {key: value for key, value in graph.items() if key != "graph_id"}
    )


def test_replay_rejects_coordinated_rehashed_edge_evidence_swap(replay_inputs) -> None:
    graph = _build(replay_inputs)
    projection, binding, receipt, _observation = replay_inputs
    forged = deepcopy(graph)
    edge_index = next(
        index for index, edge in enumerate(forged["edges"]) if edge["kind"] == "NEXT_SIBLING"
    )
    evidence_ids = [node["node_id"] for node in forged["nodes"] if node["kind"] == "EVIDENCE"]
    forged["edges"][edge_index]["evidence_node_ids"] = [evidence_ids[-1]]
    _rehash_edge_and_graph(forged, edge_index)

    with pytest.raises(graph_v2.SemanticLocalAccountingGraphV2Error):
        graph_v2.validate_semantic_local_accounting_graph_replay_v2(
            forged,
            projection,
            binding,
            receipt,
            LOAN_MATURITY_BUCKETS_SPEC_V1,
            SPECS,
        )


def test_replay_rejects_coordinated_rehashed_extra_supported_by_edge(replay_inputs) -> None:
    graph = _build(replay_inputs)
    projection, binding, receipt, _observation = replay_inputs
    forged = deepcopy(graph)
    support = next(edge for edge in forged["edges"] if edge["kind"] == "SUPPORTED_BY")
    duplicate = deepcopy(support)
    structural = next(
        node
        for node in forged["nodes"]
        if node["kind"] == "VALUE_POSITION" and node["node_id"] != support["from_node_id"]
    )
    duplicate["from_node_id"] = structural["node_id"]
    duplicate["edge_id"] = "slagv2:edge:" + canonical_json_sha256_v1(
        {key: value for key, value in duplicate.items() if key != "edge_id"}
    )
    forged["edges"].append(duplicate)
    forged["metrics"] = graph_v2._metrics(forged["nodes"], forged["edges"], True)
    forged["graph_id"] = "slagv2:graph:" + canonical_json_sha256_v1(
        {key: value for key, value in forged.items() if key != "graph_id"}
    )

    with pytest.raises(graph_v2.SemanticLocalAccountingGraphV2Error):
        graph_v2.validate_semantic_local_accounting_graph_replay_v2(
            forged,
            projection,
            binding,
            receipt,
            LOAN_MATURITY_BUCKETS_SPEC_V1,
            SPECS,
        )


@pytest.mark.parametrize("mutation", ("TOTAL", "UNIT_DUPLICATE", "VALUE_DUPLICATE"))
def test_graph_builder_recomputes_closure_and_rejects_reused_source_slots(
    replay_inputs,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    malformed = deepcopy(replay_inputs[3])
    region = malformed["candidate_regions"][0]
    if mutation == "TOTAL":
        region["rows"][-1]["value_positions"][0]["raw_text"] = "999"
        region["rows"][-1]["value_positions"][0]["normalized_decimal"] = "999"
    elif mutation == "UNIT_DUPLICATE":
        region["local_unit_labels"][1] = deepcopy(region["local_unit_labels"][0])
    else:
        region["rows"][1]["value_positions"][0] = deepcopy(region["rows"][0]["value_positions"][0])
    monkeypatch.setattr(
        graph_v2,
        "build_semantic_local_accounting_observation_candidate_v2",
        lambda *_args: deepcopy(malformed),
    )

    with pytest.raises(graph_v2.SemanticLocalAccountingGraphV2Error):
        _build(replay_inputs)


@pytest.mark.parametrize("mutation", ("NUMERIC_TEXT", "DATE_TEXT", "UNIT_TEXT", "OWNER_TEXT"))
def test_graph_builder_reparses_declared_pp_and_unit_authority(
    replay_inputs,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    malformed = deepcopy(replay_inputs[3])
    region = malformed["candidate_regions"][0]
    if mutation == "NUMERIC_TEXT":
        region["rows"][0]["value_positions"][0]["raw_text"] = "999"
    elif mutation == "DATE_TEXT":
        region["axes"][0]["raw_text"] = "01/01/2000"
    else:
        if mutation == "UNIT_TEXT":
            region["local_unit_labels"][0]["transformer_text_nfc"] = "Đồng"
            region["local_unit_labels"][1]["transformer_text_nfc"] = "Đồng"
        else:
            region["owner_label"]["transformer_text_nfc"] = "TIỀN GỬI KHÁCH HÀNG"
    monkeypatch.setattr(
        graph_v2,
        "build_semantic_local_accounting_observation_candidate_v2",
        lambda *_args: deepcopy(malformed),
    )

    with pytest.raises(graph_v2.SemanticLocalAccountingGraphV2Error):
        _build(replay_inputs)


def test_exported_safety_view_cannot_change_fixed_mint_or_replay_policy(
    replay_inputs,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(TypeError):
        graph_v2.SAFETY["schema_mapping_authority"] = True

    monkeypatch.setattr(
        graph_v2,
        "SAFETY",
        {"schema_mapping_authority": True, "export_authority": True},
    )
    graph = _build(replay_inputs)
    projection, binding, receipt, _observation = replay_inputs

    assert graph["safety"]["schema_mapping_authority"] is False
    assert graph["safety"]["export_authority"] is False
    assert (
        graph_v2.validate_semantic_local_accounting_graph_replay_v2(
            graph,
            projection,
            binding,
            receipt,
            LOAN_MATURITY_BUCKETS_SPEC_V1,
            SPECS,
        )
        == graph
    )


@pytest.mark.parametrize(
    "mutation",
    (
        "CHILD_LABEL_NONE",
        "CHILD_SEMANTIC_SOURCE_NONE",
        "CHILD_TOTAL_RESOLUTION",
        "TOTAL_LABEL_PRESENT",
        "TOTAL_RESOLUTION_DRIFT",
    ),
)
def test_graph_builder_enforces_exact_child_and_unlabeled_total_row_contract(
    replay_inputs,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    malformed = deepcopy(replay_inputs[3])
    rows = malformed["candidate_regions"][0]["rows"]
    if mutation == "CHILD_LABEL_NONE":
        rows[0]["label"] = None
    elif mutation == "CHILD_SEMANTIC_SOURCE_NONE":
        rows[0]["label"]["semantic_text_source"] = None
    elif mutation == "CHILD_TOTAL_RESOLUTION":
        rows[0]["total_resolution"] = "IMMEDIATE_UNLABELED_NUMERIC_ROW"
    elif mutation == "TOTAL_LABEL_PRESENT":
        rows[-1]["label"] = _span(999, "TỔNG CỘNG", semantic=True, role="TOTAL", y=390)
    else:
        rows[-1]["total_resolution"] = "FORGED_TOTAL_RESOLUTION"
    monkeypatch.setattr(
        graph_v2,
        "build_semantic_local_accounting_observation_candidate_v2",
        lambda *_args: deepcopy(malformed),
    )

    with pytest.raises(graph_v2.SemanticLocalAccountingGraphV2Error):
        _build(replay_inputs)


def test_duplicate_family_scope_and_target_spec_swap_fail_closed(replay_inputs) -> None:
    projection, binding, receipt, _observation = replay_inputs
    with pytest.raises(graph_v2.SemanticLocalAccountingGraphV2Error):
        graph_v2.build_semantic_local_accounting_graph_v2(
            projection,
            binding,
            receipt,
            LOAN_MATURITY_BUCKETS_SPEC_V1,
            (LOAN_MATURITY_BUCKETS_SPEC_V1, LOAN_MATURITY_BUCKETS_SPEC_V1),
        )
    with pytest.raises(graph_v2.SemanticLocalAccountingGraphV2Error):
        graph_v2.validate_semantic_local_accounting_graph_replay_v2(
            _build(replay_inputs),
            projection,
            binding,
            receipt,
            LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
            SPECS,
        )
