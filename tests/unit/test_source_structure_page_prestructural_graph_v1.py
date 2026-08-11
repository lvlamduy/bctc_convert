from __future__ import annotations

import ast
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from statistics import fmean

import pytest
from test_source_structure_evidence_projection_v1 import (
    _refresh_ocr_axis_accounting,
    _refresh_result_ref,
)
from test_source_structure_evidence_projection_v2 import (
    _synthetic_native_pair,
    _synthetic_ocr_pair,
)
from test_source_structure_page_geometry_proposals_v1 import _line

from bctc_ai.source_structure import page_prestructural_graph_v1 as builder_v1
from bctc_ai.source_structure import structural_graph_contracts_v1 as graph_contract_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    make_source_object_id_v1,
)
from bctc_ai.source_structure.contracts_v2 import make_page_proposal_set_v2
from bctc_ai.source_structure.evidence_projection_v2 import project_authenticated_page_v2
from bctc_ai.source_structure.page_geometry_proposals_v1 import (
    generate_page_geometry_proposals_v1,
)
from bctc_ai.source_structure.page_prestructural_graph_v1 import (
    build_page_prestructural_graph_v1,
)
from bctc_ai.source_structure.structural_graph_contracts_v1 import (
    validate_page_prestructural_graph_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _page_authority(
    rows: list[tuple[int, list[tuple[int, int]]]],
    *,
    vocabulary: list[str] | None = None,
) -> tuple[dict, dict]:
    record, result = _synthetic_ocr_pair()
    tokens = iter(vocabulary or [f"token-{index}" for index in range(200)])
    result["lines"] = [
        _line(y0, [(x0, x1, next(tokens)) for x0, x1 in boxes]) for y0, boxes in rows
    ]
    _refresh_ocr_axis_accounting(record, result)
    result["metrics"]["mean_line_score"] = fmean(line["score"] for line in result["lines"])
    _refresh_result_ref(record, result)
    # The shared frozen-V1 helper refreshes the legacy alias as well.  V2 has
    # the exact line-axis fields instead and rejects that extra key.
    record.pop("line_count", None)
    record["line_axis_count"] = len(result["lines"])
    record["nonempty_line_axis_count"] = len(result["lines"])
    record["exact_empty_line_axis_count"] = 0
    record["accepted_line_count"] = len(result["lines"])
    record["upstream_v2_adoption"]["source_refs"]["result_ref"] = deepcopy(record["result_ref"])
    projection = project_authenticated_page_v2(page_record=record, page_result=result)
    proposal_v1 = generate_page_geometry_proposals_v1(projection)
    proposal_v2 = make_page_proposal_set_v2(
        projection,
        proposal_set_v1=proposal_v1,
    )
    return projection, proposal_v2


def _aligned_rows(*, second_block: bool = False) -> list[tuple[int, list[tuple[int, int]]]]:
    rows = [
        (120, [(100, 180), (500, 590), (850, 930)]),
        (200, [(100, 180), (500, 590), (850, 930)]),
        (280, [(100, 180), (500, 590), (850, 930)]),
        (360, [(100, 180), (500, 590), (850, 930)]),
    ]
    if second_block:
        rows.extend(
            [
                (900, [(120, 200), (520, 610), (870, 950)]),
                (980, [(120, 200), (520, 610), (870, 950)]),
                (1060, [(120, 200), (520, 610), (870, 950)]),
            ]
        )
    return rows


def _node_counts(graph: dict) -> dict[str, int]:
    return graph["metrics"]["node_counts"]


def _structure_signature(graph: dict) -> tuple:
    node_by_id = {node["node_id"]: node for node in graph["nodes"]}
    nodes = tuple(
        (
            node["ordinal"],
            node["kind"],
            node["status"],
            tuple(node["canonical_bbox_mpt"] or ()),
            len(node["source_atom_ids"]),
            len(node["source_proposal_ids"]),
        )
        for node in graph["nodes"]
    )
    edges = tuple(
        (
            edge["kind"],
            node_by_id[edge["from_node_id"]]["ordinal"],
            node_by_id[edge["to_node_id"]]["ordinal"],
        )
        for edge in graph["edges"]
    )
    dispositions = tuple(item["primary_disposition"] for item in graph["atom_dispositions"])
    return nodes, edges, dispositions


def test_aligned_geometry_builds_only_prestructural_table_row_cell_axis_candidates() -> None:
    projection, proposal = _page_authority(_aligned_rows())
    graph = build_page_prestructural_graph_v1(projection, proposal)

    assert (
        validate_page_prestructural_graph_v1(
            graph,
            projection=projection,
            proposal_projection=proposal,
        )
        == graph
    )
    assert graph["status"] == "PARTIAL_PRESTRUCTURAL_CANDIDATES"
    assert _node_counts(graph) == {
        "DOCUMENT": 1,
        "PAGE": 1,
        "STATEMENT_BLOCK": 0,
        "TABLE": 1,
        "ROW": 4,
        "CELL_OR_VALUE_POSITION": 12,
        "AXIS_OR_DIMENSION": 3,
        "EVIDENCE": 16,
        "UNRESOLVED_REGION": 1,
    }
    candidates = {
        "TABLE",
        "ROW",
        "CELL_OR_VALUE_POSITION",
        "AXIS_OR_DIMENSION",
    }
    assert {node["status"] for node in graph["nodes"] if node["kind"] in candidates} == {
        "PRESTRUCTURAL_CANDIDATE"
    }
    assert graph["safety"]["table_claimed"] is False
    assert graph["safety"]["logical_rows_claimed"] is False
    assert graph["safety"]["financial_cells_claimed"] is False
    assert graph["safety"]["period_axis_claimed"] is False
    assert graph["safety"]["unit_axis_claimed"] is False
    assert graph["safety"]["hierarchy_claimed"] is False


def test_builder_is_canonical_and_text_identity_cannot_change_geometry_decisions() -> None:
    rows = _aligned_rows()
    numeric, numeric_proposals = _page_authority(
        rows,
        vocabulary=[str(index) for index in range(12)],
    )
    prose, prose_proposals = _page_authority(
        rows,
        vocabulary=[f"word-{index}" for index in range(12)],
    )
    first = build_page_prestructural_graph_v1(numeric, numeric_proposals)
    repeated = build_page_prestructural_graph_v1(numeric, numeric_proposals)
    second = build_page_prestructural_graph_v1(prose, prose_proposals)

    assert canonical_json_bytes_v1(first) == canonical_json_bytes_v1(repeated)
    assert _structure_signature(first) == _structure_signature(second)


def test_narrative_source_block_remains_one_explicit_unresolved_region() -> None:
    rows = [
        (120, [(100, 170), (240, 320), (430, 500), (650, 730)]),
        (200, [(100, 170), (280, 360), (490, 560), (720, 800)]),
        (280, [(100, 170), (330, 410), (550, 620), (790, 870)]),
        (360, [(100, 170), (380, 460), (610, 680), (860, 940)]),
    ]
    projection, proposal = _page_authority(rows)
    assert [item["kind"] for item in proposal["proposal_set_v1"]["proposals"]] == [
        "SOURCE_BLOCK_CANDIDATE"
    ]

    graph = build_page_prestructural_graph_v1(projection, proposal)

    assert _node_counts(graph)["TABLE"] == 0
    assert _node_counts(graph)["ROW"] == 0
    assert _node_counts(graph)["CELL_OR_VALUE_POSITION"] == 0
    assert _node_counts(graph)["AXIS_OR_DIMENSION"] == 0
    assert _node_counts(graph)["UNRESOLVED_REGION"] == 1
    assert graph["metrics"]["disposition_counts"]["RETAINED_UNRESOLVED"] == len(
        projection["neutral_page_v1"]["atoms"]
    )


def test_continuation_geometry_remains_unresolved_without_cross_page_authority() -> None:
    rows = [
        (120, [(100, 170), (240, 320), (430, 500), (650, 730)]),
        (200, [(100, 170), (280, 360), (490, 560), (720, 800)]),
        (280, [(100, 170), (330, 410), (550, 620), (790, 870)]),
    ]
    projection, proposal = _page_authority(rows)
    proposal_v1 = deepcopy(proposal["proposal_set_v1"])
    item = proposal_v1["proposals"][0]
    old_id = item["source_local_id"]
    item["kind"] = "CONTINUATION_GEOMETRY_CANDIDATE"
    item["source_local_id"] = make_source_object_id_v1(
        "source_object",
        {
            "source_local_page_id": projection["neutral_page_v1"]["source_local_page_id"],
            "request_sha256": projection["neutral_page_v1"]["source_locator"]["request_sha256"],
            "kind": item["kind"],
            "canonical_bbox_mpt": item["canonical_bbox_mpt"],
            "primary_atom_ids": item["primary_atom_ids"],
            "supporting_atom_ids": item["supporting_atom_ids"],
            "evidence_codes": item["evidence_codes"],
        },
    )
    for disposition in proposal_v1["dispositions"]:
        if disposition["source_object_id"] == old_id:
            disposition["source_object_id"] = item["source_local_id"]
    continuation = make_page_proposal_set_v2(
        projection,
        proposal_set_v1=proposal_v1,
    )

    graph = build_page_prestructural_graph_v1(projection, continuation)

    assert _node_counts(graph)["TABLE"] == 0
    assert _node_counts(graph)["UNRESOLVED_REGION"] == 1
    assert graph["metrics"]["disposition_counts"]["RETAINED_UNRESOLVED"] == len(
        projection["neutral_page_v1"]["atoms"]
    )


def test_mixed_tabular_and_source_block_geometry_is_exactly_no_drop() -> None:
    rows = _aligned_rows() + [
        (900, [(120, 190), (260, 340), (450, 520), (670, 750)]),
        (980, [(120, 190), (300, 380), (510, 580), (740, 820)]),
        (1060, [(120, 190), (350, 430), (570, 640), (810, 890)]),
    ]
    projection, proposal = _page_authority(rows)
    assert [item["kind"] for item in proposal["proposal_set_v1"]["proposals"]] == [
        "TABULAR_GEOMETRY_CANDIDATE",
        "SOURCE_BLOCK_CANDIDATE",
    ]

    graph = build_page_prestructural_graph_v1(projection, proposal)

    counts = graph["metrics"]["disposition_counts"]
    assert _node_counts(graph)["TABLE"] == 1
    assert counts["SUPPORTS_PRESTRUCTURAL_CANDIDATE"] > 0
    assert counts["RETAINED_UNRESOLVED"] > 0
    assert sum(counts.values()) == len(projection["neutral_page_v1"]["atoms"])


def test_non_tabular_owned_overlap_is_conservatively_kept_unresolved() -> None:
    rows = _aligned_rows() + [
        (900, [(120, 190), (260, 340), (450, 520), (670, 750)]),
        (980, [(120, 190), (300, 380), (510, 580), (740, 820)]),
        (1060, [(120, 190), (350, 430), (570, 640), (810, 890)]),
    ]
    projection, proposal = _page_authority(rows)
    proposal_v1 = deepcopy(proposal["proposal_set_v1"])
    tabular, source_block = proposal_v1["proposals"]
    overlapping_atom_id = source_block["primary_atom_ids"][0]
    old_tabular_id = tabular["source_local_id"]
    tabular["supporting_atom_ids"].append(overlapping_atom_id)
    tabular["source_local_id"] = make_source_object_id_v1(
        "source_object",
        {
            "source_local_page_id": projection["neutral_page_v1"]["source_local_page_id"],
            "request_sha256": projection["neutral_page_v1"]["source_locator"]["request_sha256"],
            "kind": tabular["kind"],
            "canonical_bbox_mpt": tabular["canonical_bbox_mpt"],
            "primary_atom_ids": tabular["primary_atom_ids"],
            "supporting_atom_ids": tabular["supporting_atom_ids"],
            "evidence_codes": tabular["evidence_codes"],
        },
    )
    for disposition in proposal_v1["dispositions"]:
        if disposition["source_object_id"] == old_tabular_id:
            disposition["source_object_id"] = tabular["source_local_id"]
    overlapping = make_page_proposal_set_v2(
        projection,
        proposal_set_v1=proposal_v1,
    )

    graph = build_page_prestructural_graph_v1(projection, overlapping)
    candidate_kinds = {"TABLE", "ROW", "CELL_OR_VALUE_POSITION", "AXIS_OR_DIMENSION"}
    candidate_atoms = {
        atom_id
        for node in graph["nodes"]
        if node["kind"] in candidate_kinds
        for atom_id in node["source_atom_ids"]
    }
    disposition = next(
        item for item in graph["atom_dispositions"] if item["source_atom_id"] == overlapping_atom_id
    )

    assert overlapping_atom_id not in candidate_atoms
    assert disposition["primary_disposition"] == "RETAINED_UNRESOLVED"


def test_many_geometry_proposals_remain_candidates_and_never_become_truth() -> None:
    projection, proposal = _page_authority(_aligned_rows(second_block=True))
    assert [item["kind"] for item in proposal["proposal_set_v1"]["proposals"]] == [
        "TABULAR_GEOMETRY_CANDIDATE",
        "TABULAR_GEOMETRY_CANDIDATE",
    ]

    graph = build_page_prestructural_graph_v1(projection, proposal)

    assert _node_counts(graph)["TABLE"] == 2
    assert _node_counts(graph)["STATEMENT_BLOCK"] == 0
    assert _node_counts(graph)["UNRESOLVED_REGION"] == 1
    assert all(
        node["status"] == "PRESTRUCTURAL_CANDIDATE"
        for node in graph["nodes"]
        if node["kind"] in {"TABLE", "ROW", "CELL_OR_VALUE_POSITION", "AXIS_OR_DIMENSION"}
    )
    assert graph["safety"]["statement_claimed"] is False
    assert graph["safety"]["table_claimed"] is False


def test_terminal_page_has_one_unresolved_region_and_evidence_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record, result = _synthetic_native_pair(monkeypatch, contiguity_terminal=True)
    projection = project_authenticated_page_v2(page_record=record, page_result=result)
    proposal_v1 = generate_page_geometry_proposals_v1(projection)
    proposal = make_page_proposal_set_v2(projection, proposal_set_v1=proposal_v1)

    graph = build_page_prestructural_graph_v1(projection, proposal)

    assert projection["terminal"] is True
    assert _node_counts(graph) == {
        "DOCUMENT": 1,
        "PAGE": 1,
        "STATEMENT_BLOCK": 0,
        "TABLE": 0,
        "ROW": 0,
        "CELL_OR_VALUE_POSITION": 0,
        "AXIS_OR_DIMENSION": 0,
        "EVIDENCE": 1,
        "UNRESOLVED_REGION": 1,
    }
    assert graph["metrics"]["disposition_counts"] == {
        "SUPPORTS_PRESTRUCTURAL_CANDIDATE": 0,
        "RETAINED_UNRESOLVED": 0,
        "UPSTREAM_TERMINAL_UNRESOLVED": 0,
        "UPSTREAM_QUARANTINED": 1,
    }
    assert graph["safety"]["blank_claimed"] is False
    assert graph["safety"]["absence_claimed"] is False


def test_nonterminal_supplement_keeps_upstream_terminal_disposition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    projection, proposal = _page_authority(
        [
            (120, [(100, 170), (260, 340)]),
            (200, [(100, 170), (300, 380)]),
        ]
    )
    projection = deepcopy(projection)
    proposal = deepcopy(proposal)
    atom = projection["neutral_page_v1"]["atoms"][0]
    atom["authority"] = "SUPPLEMENTAL_COARSE_LINE"
    upstream = next(
        item
        for item in proposal["proposal_set_v1"]["dispositions"]
        if item["source_atom_id"] == atom["source_local_id"]
    )
    upstream.update(
        {
            "primary_disposition": "UPSTREAM_TERMINAL_UNRESOLVED",
            "source_object_id": None,
            "reason_code": "UPSTREAM_TERMINAL_RETAINED",
        }
    )
    for module in (builder_v1, graph_contract_v1):
        monkeypatch.setattr(
            module,
            "validate_source_evidence_projection_v2",
            lambda value: deepcopy(value),
        )
        monkeypatch.setattr(
            module,
            "validate_page_proposal_set_v2",
            lambda value, *, projection: deepcopy(value),
        )

    graph = build_page_prestructural_graph_v1(projection, proposal)
    disposition = next(
        item
        for item in graph["atom_dispositions"]
        if item["source_atom_id"] == atom["source_local_id"]
    )

    assert disposition["primary_disposition"] == "UPSTREAM_TERMINAL_UNRESOLVED"
    assert disposition["reason_code"] == "UPSTREAM_TERMINAL_SOURCE_EVIDENCE_RETAINED"


def test_every_atom_keeps_exact_upstream_disposition_binding_and_one_owner() -> None:
    projection, proposal = _page_authority(_aligned_rows())
    graph = build_page_prestructural_graph_v1(projection, proposal)
    upstream = {
        item["source_atom_id"]: item for item in proposal["proposal_set_v1"]["dispositions"]
    }

    assert [item["source_atom_id"] for item in graph["atom_dispositions"]] == [
        atom["source_local_id"] for atom in projection["neutral_page_v1"]["atoms"]
    ]
    assert len({item["source_atom_id"] for item in graph["atom_dispositions"]}) == len(
        projection["neutral_page_v1"]["atoms"]
    )
    for disposition in graph["atom_dispositions"]:
        assert (
            disposition["upstream_disposition_sha256"]
            == sha256(canonical_json_bytes_v1(upstream[disposition["source_atom_id"]])).hexdigest()
        )


def test_builder_has_no_forbidden_routing_or_semantic_input_surface() -> None:
    source_path = PROJECT_ROOT / "src/bctc_ai/source_structure/page_prestructural_graph_v1.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    subscript_keys = {
        node.slice.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Subscript)
        and isinstance(node.slice, ast.Constant)
        and isinstance(node.slice.value, str)
    }
    assert subscript_keys.isdisjoint(
        {
            "bank",
            "document_id",
            "filename",
            "historical_values",
            "note",
            "page_number",
            "path",
            "physical_page",
            "raw_text",
            "role_a",
            "schema",
        }
    )
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert {name for name in imported if name.startswith("bctc_ai.")} == {
        "bctc_ai.source_structure.contracts_v1",
        "bctc_ai.source_structure.contracts_v2",
        "bctc_ai.source_structure.structural_graph_contracts_v1",
    }
