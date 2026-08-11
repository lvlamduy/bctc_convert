from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from statistics import fmean
from typing import Any

import pytest
from test_source_structure_evidence_projection_v1 import (
    _refresh_ocr_axis_accounting,
    _refresh_result_ref,
)
from test_source_structure_evidence_projection_v2 import (
    _refresh_native_result_ref,
    _synthetic_native_pair,
    _synthetic_ocr_pair,
)
from test_source_structure_page_geometry_proposals_v1 import _line

from bctc_ai.source_structure import adjacent_page_table_geometry_relations_v1 as relation_v1
from bctc_ai.source_structure.adjacent_page_table_geometry_relations_v1 import (
    ADJACENT_PAGE_TABLE_GEOMETRY_SAFETY_V1,
    AdjacentPageTableGeometryRelationError,
    build_adjacent_page_table_geometry_relations_v1,
    validate_adjacent_page_table_geometry_relations_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)
from bctc_ai.source_structure.contracts_v2 import make_page_proposal_set_v2
from bctc_ai.source_structure.evidence_projection_v2 import project_authenticated_page_v2
from bctc_ai.source_structure.page_geometry_proposals_v1 import (
    generate_page_geometry_proposals_v1,
)
from bctc_ai.source_structure.page_prestructural_graph_v1 import (
    build_page_prestructural_graph_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


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


def _narrative_rows() -> list[tuple[int, list[tuple[int, int]]]]:
    return [
        (120, [(100, 170), (240, 320), (430, 500), (650, 730)]),
        (200, [(100, 170), (280, 360), (490, 560), (720, 800)]),
        (280, [(100, 170), (330, 410), (550, 620), (790, 870)]),
        (360, [(100, 170), (380, 460), (610, 680), (860, 940)]),
    ]


def _ocr_page_graph(
    physical_page: int,
    rows: list[tuple[int, list[tuple[int, int]]]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    record, result = _synthetic_ocr_pair()
    record["request_ordinal"] = physical_page
    record["physical_page"] = physical_page
    record["request"]["physical_page"] = physical_page
    result["physical_page"] = physical_page
    result["request"] = deepcopy(record["request"])
    request_sha256 = canonical_json_sha256_v1(record["request"])
    record["request_sha256"] = request_sha256
    result["request_sha256"] = request_sha256

    tokens = iter(f"token-{index}" for index in range(200))
    result["lines"] = [
        _line(
            y0,
            [(x0, x1, next(tokens)) for x0, x1 in boxes],
        )
        for y0, boxes in rows
    ]
    _refresh_ocr_axis_accounting(record, result)
    result["metrics"]["mean_line_score"] = fmean(line["score"] for line in result["lines"])
    _refresh_result_ref(record, result)
    record.pop("line_count", None)
    record["line_axis_count"] = len(result["lines"])
    record["nonempty_line_axis_count"] = len(result["lines"])
    record["exact_empty_line_axis_count"] = 0
    record["accepted_line_count"] = len(result["lines"])
    record["upstream_v2_adoption"]["source_refs"]["result_ref"] = deepcopy(record["result_ref"])

    projection = project_authenticated_page_v2(page_record=record, page_result=result)
    proposal = make_page_proposal_set_v2(
        projection,
        proposal_set_v1=generate_page_geometry_proposals_v1(projection),
    )
    graph = build_page_prestructural_graph_v1(projection, proposal)
    return projection, proposal, graph


def _ocr_terminal_page_graph(
    physical_page: int,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    record, result = _synthetic_ocr_pair()
    record["request_ordinal"] = physical_page
    record["physical_page"] = physical_page
    record["request"]["physical_page"] = physical_page
    result["physical_page"] = physical_page
    result["request"] = deepcopy(record["request"])
    request_sha256 = canonical_json_sha256_v1(record["request"])
    record["request_sha256"] = request_sha256
    result["request_sha256"] = request_sha256

    result["format_version"] = "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V3"
    result["status"] = "UNRESOLVED_OCR_WORD_BOX_GEOMETRY"
    result["claim_boundary"] = "SOURCE_VISIBLE_PAGE_RAW_OCR_EVIDENCE_WITH_UNRESOLVED_GEOMETRY"
    result.pop("word_box_normalization_ledger")
    result["normalization_failure"] = {
        "format_version": "BANK_CORPUS_WAVE_1_PPOCRV6_NORMALIZATION_FAILURE_V1",
        "status": result["status"],
        "reason": "BOUNDED_WORD_BOX_NORMALIZATION_INVARIANT_FAILED",
        "policy_sha256": "3" * 64,
        "control_identity_sha256": "4" * 64,
        "normalization_producer_implementation_ledger_sha256": "5" * 64,
        "pixel_dimensions": result["coordinate_authority"]["pixel_dimensions"],
        "raw_payload_sha256": "6" * 64,
    }
    result["lines"] = []
    result["words"] = []
    result["metrics"] = {"line_count": 0, "word_token_count": 0}
    result["ocr_fallback_used"] = False
    record["status"] = result["status"]
    record["upstream_status"] = result["status"]
    record["unresolved"] = True
    record["upstream_unresolved"] = True
    for field in (
        "line_axis_count",
        "nonempty_line_axis_count",
        "exact_empty_line_axis_count",
        "accepted_line_count",
        "word_token_count",
        "word_box_correction_count",
        "word_box_corrected_edge_count",
    ):
        record[field] = 0
    record["upstream_v2_adoption"]["source_status"] = result["status"]
    record["upstream_v2_adoption"]["source_unresolved"] = True
    _refresh_result_ref(record, result)
    record["upstream_v2_adoption"]["source_refs"]["result_ref"] = deepcopy(record["result_ref"])

    projection = project_authenticated_page_v2(page_record=record, page_result=result)
    proposal = make_page_proposal_set_v2(
        projection,
        proposal_set_v1=generate_page_geometry_proposals_v1(projection),
    )
    graph = build_page_prestructural_graph_v1(projection, proposal)
    return projection, proposal, graph


def _native_page_graph(
    monkeypatch: pytest.MonkeyPatch,
    *,
    physical_page: int,
    terminal: bool,
    source_sha256: str,
    source_size_bytes: int,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    record, result = _synthetic_native_pair(
        monkeypatch,
        contiguity_terminal=terminal,
    )
    for item in (record, result):
        item["source_sha256"] = source_sha256
        item["source_size_bytes"] = source_size_bytes
        item["physical_page"] = physical_page
    record["request_ordinal"] = physical_page
    record["document_id"] = f"sha256:{source_sha256}"
    result["document_id"] = f"sha256:{source_sha256}"
    for request in (record["request"], result["request"]):
        request["source_sha256"] = source_sha256
        request["source_size_bytes"] = source_size_bytes
        request["physical_page"] = physical_page
    result["request"] = deepcopy(record["request"])
    for quarantined_span in result["quarantined_spans"]:
        quarantined_span["page"] = physical_page
    request_sha256 = canonical_json_sha256_v1(record["request"])
    record["request_sha256"] = request_sha256
    result["request_sha256"] = request_sha256
    _refresh_native_result_ref(record, result)

    projection = project_authenticated_page_v2(page_record=record, page_result=result)
    proposal = make_page_proposal_set_v2(
        projection,
        proposal_set_v1=generate_page_geometry_proposals_v1(projection),
    )
    graph = build_page_prestructural_graph_v1(projection, proposal)
    return projection, proposal, graph


def _build(
    previous: tuple[dict[str, Any], dict[str, Any], dict[str, Any]],
    following: tuple[dict[str, Any], dict[str, Any], dict[str, Any]],
) -> dict[str, Any]:
    return build_adjacent_page_table_geometry_relations_v1(*previous, *following)


def _table_nodes(graph: dict[str, Any]) -> list[dict[str, Any]]:
    return [node for node in graph["nodes"] if node["kind"] == "TABLE"]


def _assert_no_float(value: Any) -> None:
    assert type(value) is not float
    if type(value) is dict:
        for item in value.values():
            _assert_no_float(item)
    elif type(value) is list:
        for item in value:
            _assert_no_float(item)


def test_every_table_and_axis_candidate_enters_exact_cartesian_geometry_evidence() -> None:
    previous = _ocr_page_graph(1, _aligned_rows(second_block=True))
    following = _ocr_page_graph(2, _aligned_rows())

    first = _build(previous, following)
    repeated = _build(previous, following)

    assert canonical_json_bytes_v1(first) == canonical_json_bytes_v1(repeated)
    assert (
        validate_adjacent_page_table_geometry_relations_v1(
            first,
            previous_projection=previous[0],
            previous_proposal_projection=previous[1],
            previous_graph=previous[2],
            following_projection=following[0],
            following_proposal_projection=following[1],
            following_graph=following[2],
        )
        == first
    )
    metrics = first["metrics"]
    assert metrics["previous_table_candidate_count"] == 2
    assert metrics["following_table_candidate_count"] == 1
    assert metrics["expected_cartesian_fragment_pair_count"] == 2
    assert metrics["emitted_cartesian_fragment_pair_count"] == 2
    assert metrics["expected_cartesian_axis_distance_count"] == 18
    assert metrics["emitted_cartesian_axis_distance_count"] == 18
    assert metrics["axis_disposition_count"] == 9
    assert metrics["axis_disposition_counts"] == {
        "MEASURED_IN_CARTESIAN_AXIS_PAIRS": 9,
        "RETAINED_WITHOUT_AXIS_COUNTERPART": 0,
    }
    assert first["page_pair_disposition"]["primary_disposition"] == (
        "MEASURED_CARTESIAN_FRAGMENT_PAIRS"
    )

    expected_table_ids = {
        node["node_id"] for node in [*_table_nodes(previous[2]), *_table_nodes(following[2])]
    }
    fragments = first["table_fragments"]
    assert {fragment["table_node_id"] for fragment in fragments} == expected_table_ids
    assert len(first["fragment_dispositions"]) == len(fragments) == 3
    assert {
        disposition["primary_disposition"] for disposition in first["fragment_dispositions"]
    } == {"MEASURED_IN_CARTESIAN_FRAGMENT_PAIRS"}
    assert [len(disposition["relation_ids"]) for disposition in first["fragment_dispositions"]] == [
        1,
        1,
        2,
    ]

    for fragment in fragments:
        graph = previous[2] if fragment["side"] == "PREVIOUS_PAGE" else following[2]
        table = next(
            node for node in graph["nodes"] if node["node_id"] == fragment["table_node_id"]
        )
        assert fragment["canonical_bbox_mpt"] == table["canonical_bbox_mpt"]
        assert all(type(coordinate) is int for coordinate in fragment["normalized_bbox_ppm"])
        for axis in fragment["axis_or_dimension_candidates"]:
            assert axis["source_atom_count"] == len(axis["source_atom_geometries"])
            assert all(
                all(type(coordinate) is int for coordinate in atom["normalized_bbox_ppm"])
                for atom in axis["source_atom_geometries"]
            )

    for relation in first["fragment_pair_relations"]:
        assert relation["status"] == "MEASURED_PRESTRUCTURAL_FRAGMENT_PAIR_UNRESOLVED"
        assert relation["axis_cartesian_distance_count"] == (
            relation["previous_axis_count"] * relation["following_axis_count"]
        )
        assert len(relation["axis_cartesian_distances"]) == 9
        evidence = relation["table_distance_evidence"]
        assert len(evidence["normalized_bbox_edge_signed_delta_ppm"]) == 4
        for field in (
            "exact_left_edge_absolute_distance_page_width_fraction",
            "exact_right_edge_absolute_distance_page_width_fraction",
            "exact_width_absolute_distance_page_width_fraction",
        ):
            assert evidence[field]["denominator"] > 0
        assert all(
            distance["exact_center_absolute_distance_page_width_fraction"]["denominator"] > 0
            for distance in relation["axis_cartesian_distances"]
        )
    assert len(first["axis_dispositions"]) == 9
    assert all(
        disposition["primary_disposition"] == "MEASURED_IN_CARTESIAN_AXIS_PAIRS"
        and disposition["axis_distance_ids"]
        for disposition in first["axis_dispositions"]
    )
    _assert_no_float(first)


@pytest.mark.parametrize(
    ("previous_rows", "following_rows", "expected", "retained"),
    [
        (_narrative_rows(), _aligned_rows(), "NO_PREVIOUS_TABLE_CANDIDATE", 1),
        (_aligned_rows(), _narrative_rows(), "NO_FOLLOWING_TABLE_CANDIDATE", 1),
        (_narrative_rows(), _narrative_rows(), "NO_TABLE_CANDIDATES", 0),
    ],
)
def test_zero_table_sides_are_explicitly_accounted_without_an_absence_claim(
    previous_rows: list[tuple[int, list[tuple[int, int]]]],
    following_rows: list[tuple[int, list[tuple[int, int]]]],
    expected: str,
    retained: int,
) -> None:
    result = _build(
        _ocr_page_graph(1, previous_rows),
        _ocr_page_graph(2, following_rows),
    )

    assert result["fragment_pair_relations"] == []
    page_pair_id = result["ordered_page_pair"]["page_pair_id"]
    assert result["page_pair_disposition"]["primary_disposition"] == expected
    assert result["page_pair_disposition"]["source_table_absence_claimed"] is False
    assert result["metrics"]["fragment_disposition_counts"] == {
        "MEASURED_IN_CARTESIAN_FRAGMENT_PAIRS": 0,
        "RETAINED_WITHOUT_CROSS_PAGE_COUNTERPART": retained,
    }
    assert all(
        disposition["primary_disposition"] == "RETAINED_WITHOUT_CROSS_PAGE_COUNTERPART"
        and disposition["page_pair_id"] == page_pair_id
        and disposition["relation_ids"] == []
        for disposition in result["fragment_dispositions"]
    )
    expected_retained_axes = retained * 3
    assert result["metrics"]["axis_disposition_counts"] == {
        "MEASURED_IN_CARTESIAN_AXIS_PAIRS": 0,
        "RETAINED_WITHOUT_AXIS_COUNTERPART": expected_retained_axes,
    }
    assert len(result["axis_dispositions"]) == expected_retained_axes
    assert all(
        disposition["primary_disposition"] == "RETAINED_WITHOUT_AXIS_COUNTERPART"
        and disposition["page_pair_id"] == page_pair_id
        and disposition["axis_distance_ids"] == []
        for disposition in result["axis_dispositions"]
    )
    assert result["safety"]["absence_claimed"] is False


def test_upstream_terminal_page_is_a_hard_explicit_relation_barrier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed_record, _seed_result = _synthetic_native_pair(
        monkeypatch,
        contiguity_terminal=False,
    )
    source_sha256 = seed_record["source_sha256"]
    source_size_bytes = seed_record["source_size_bytes"]
    previous = _native_page_graph(
        monkeypatch,
        physical_page=1,
        terminal=False,
        source_sha256=source_sha256,
        source_size_bytes=source_size_bytes,
    )
    following = _native_page_graph(
        monkeypatch,
        physical_page=2,
        terminal=True,
        source_sha256=source_sha256,
        source_size_bytes=source_size_bytes,
    )

    result = _build(previous, following)

    assert result["ordered_page_pair"]["following_page_binding"]["terminal"] is True
    assert result["ordered_page_pair"]["following_page_binding"]["canonical_page_extent_mpt"] == [
        0,
        0,
        400_000,
        300_000,
    ]
    assert result["page_pair_disposition"]["primary_disposition"] == ("UPSTREAM_TERMINAL_BARRIER")
    assert result["metrics"]["terminal_page_count"] == 1
    assert result["table_fragments"] == []
    assert result["fragment_pair_relations"] == []
    assert result["safety"]["continuation_claimed"] is False


def test_terminal_barrier_retains_every_nonterminal_fragment_without_pairing() -> None:
    result = _build(
        _ocr_page_graph(1, _aligned_rows(second_block=True)),
        _ocr_terminal_page_graph(2),
    )

    assert result["page_pair_disposition"]["primary_disposition"] == ("UPSTREAM_TERMINAL_BARRIER")
    assert result["metrics"]["previous_table_candidate_count"] == 2
    assert result["metrics"]["following_table_candidate_count"] == 0
    assert result["metrics"]["expected_cartesian_fragment_pair_count"] == 0
    assert result["fragment_pair_relations"] == []
    assert len(result["fragment_dispositions"]) == 2
    assert all(
        disposition["primary_disposition"] == "RETAINED_WITHOUT_CROSS_PAGE_COUNTERPART"
        and disposition["reason_code"]
        == "FRAGMENT_RETAINED_BECAUSE_AN_ADJACENT_PAGE_IS_UPSTREAM_TERMINAL"
        and disposition["relation_ids"] == []
        for disposition in result["fragment_dispositions"]
    )
    assert len(result["axis_dispositions"]) == 6
    assert all(
        disposition["primary_disposition"] == "RETAINED_WITHOUT_AXIS_COUNTERPART"
        and disposition["reason_code"]
        == "AXIS_RETAINED_BECAUSE_AN_ADJACENT_PAGE_IS_UPSTREAM_TERMINAL"
        and disposition["axis_distance_ids"] == []
        for disposition in result["axis_dispositions"]
    )


def test_axis_center2_is_the_direct_median_of_each_atom_center2() -> None:
    atoms = [
        {"source_local_id": "first", "canonical_bbox_mpt": [0, 1, 100, 2]},
        {"source_local_id": "second", "canonical_bbox_mpt": [10, 1, 21, 2]},
        {"source_local_id": "third", "canonical_bbox_mpt": [20, 1, 22, 2]},
    ]
    axis = {
        "node_id": "axis-node",
        "ordinal": 1,
        "source_binding_sha256": "a" * 64,
        "canonical_bbox_mpt": [0, 1, 100, 2],
        "source_atom_ids": ["first", "second", "third"],
    }

    geometry = relation_v1._axis_geometry(  # noqa: SLF001
        axis=axis,
        atoms=atoms,
        extent=[0, 0, 1_000, 1_000],
    )

    assert geometry["source_atom_x0_median_mpt"] == 10
    assert geometry["source_atom_x2_median_mpt"] == 22
    assert geometry["source_atom_center2_median_mpt"] == 42
    assert geometry["source_atom_center2_median_mpt"] != (
        geometry["source_atom_x0_median_mpt"] + geometry["source_atom_x2_median_mpt"]
    )
    assert geometry["normalized_source_atom_center2_median_ppm"] == 42_000


def test_page_and_fragment_content_identities_do_not_depend_on_pair_side() -> None:
    first_page = _ocr_page_graph(1, _aligned_rows())
    middle_page = _ocr_page_graph(2, _aligned_rows())
    last_page = _ocr_page_graph(3, _aligned_rows())

    first_pair = _build(first_page, middle_page)
    second_pair = _build(middle_page, last_page)
    middle_as_following = first_pair["ordered_page_pair"]["following_page_binding"]
    middle_as_previous = second_pair["ordered_page_pair"]["previous_page_binding"]
    following_fragment = next(
        fragment
        for fragment in first_pair["table_fragments"]
        if fragment["side"] == "FOLLOWING_PAGE"
    )
    previous_fragment = next(
        fragment
        for fragment in second_pair["table_fragments"]
        if fragment["side"] == "PREVIOUS_PAGE"
    )

    assert middle_as_following["source_local_page_id"] == middle_as_previous["source_local_page_id"]
    assert middle_as_following["page_binding_id"] == middle_as_previous["page_binding_id"]
    assert following_fragment["table_node_id"] == previous_fragment["table_node_id"]
    assert following_fragment["fragment_id"] == previous_fragment["fragment_id"]
    assert middle_as_following["side"] != middle_as_previous["side"]
    assert following_fragment["side"] != previous_fragment["side"]


def test_distinct_exact_plus_one_pages_and_all_six_bindings_are_mandatory() -> None:
    previous = _ocr_page_graph(1, _aligned_rows())
    following = _ocr_page_graph(2, _aligned_rows())
    nonadjacent = _ocr_page_graph(3, _aligned_rows())

    with pytest.raises(
        AdjacentPageTableGeometryRelationError,
        match="exactly previous physical page plus one",
    ):
        _build(previous, nonadjacent)
    with pytest.raises(
        AdjacentPageTableGeometryRelationError,
        match="exact page-local contract",
    ):
        build_adjacent_page_table_geometry_relations_v1(
            previous[0],
            previous[1],
            previous[2],
            following[0],
            previous[1],
            following[2],
        )
    with pytest.raises(
        AdjacentPageTableGeometryRelationError,
        match="exact page-local contract",
    ):
        build_adjacent_page_table_geometry_relations_v1(
            previous[0],
            previous[1],
            previous[2],
            following[0],
            following[1],
            previous[2],
        )


def test_replay_rejects_forged_geometry_even_if_no_identity_is_reused() -> None:
    previous = _ocr_page_graph(1, _aligned_rows())
    following = _ocr_page_graph(2, _aligned_rows())
    result = _build(previous, following)
    forged = deepcopy(result)
    forged["fragment_pair_relations"][0]["table_distance_evidence"][
        "normalized_left_edge_absolute_distance_ppm"
    ] += 1
    forged["fragment_pair_relations"][0]["relation_id"] = (
        "apgrv1:relation:"
        + canonical_json_sha256_v1(
            {
                key: value
                for key, value in forged["fragment_pair_relations"][0].items()
                if key != "relation_id"
            }
        )
    )
    forged["artifact_identity"] = "apgrv1:artifact:" + canonical_json_sha256_v1(
        {key: value for key, value in forged.items() if key != "artifact_identity"}
    )

    with pytest.raises(
        AdjacentPageTableGeometryRelationError,
        match="drifted from exact replay",
    ):
        validate_adjacent_page_table_geometry_relations_v1(
            forged,
            previous_projection=previous[0],
            previous_proposal_projection=previous[1],
            previous_graph=previous[2],
            following_projection=following[0],
            following_proposal_projection=following[1],
            following_graph=following[2],
        )


def test_replay_rejects_a_self_rehashed_retained_disposition_with_foreign_pair_id() -> None:
    previous = _ocr_page_graph(1, _aligned_rows())
    following = _ocr_page_graph(2, _narrative_rows())
    result = _build(previous, following)
    forged = deepcopy(result)
    disposition = forged["fragment_dispositions"][0]
    disposition["page_pair_id"] = "apgrv1:page_pair:" + "f" * 64
    disposition["fragment_disposition_id"] = (
        "apgrv1:fragment_disposition:"
        + canonical_json_sha256_v1(
            {key: value for key, value in disposition.items() if key != "fragment_disposition_id"}
        )
    )
    forged["artifact_identity"] = "apgrv1:artifact:" + canonical_json_sha256_v1(
        {key: value for key, value in forged.items() if key != "artifact_identity"}
    )

    with pytest.raises(
        AdjacentPageTableGeometryRelationError,
        match="drifted from exact replay",
    ):
        validate_adjacent_page_table_geometry_relations_v1(
            forged,
            previous_projection=previous[0],
            previous_proposal_projection=previous[1],
            previous_graph=previous[2],
            following_projection=following[0],
            following_proposal_projection=following[1],
            following_graph=following[2],
        )


def test_module_has_no_semantic_or_identity_routing_input_surface() -> None:
    source_path = (
        PROJECT_ROOT / "src/bctc_ai/source_structure/adjacent_page_table_geometry_relations_v1.py"
    )
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
            "accepted",
            "bank",
            "bank_name",
            "filename",
            "header",
            "historical_values",
            "mapping",
            "merge",
            "note",
            "path",
            "period",
            "raw_text",
            "report_norm_id",
            "role_a",
            "same_table",
            "schema",
            "scope",
            "statement_family",
            "title",
            "unit",
            "value",
            "winner",
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
    assert ADJACENT_PAGE_TABLE_GEOMETRY_SAFETY_V1["threshold_applied"] is False
    assert ADJACENT_PAGE_TABLE_GEOMETRY_SAFETY_V1["winner_selected"] is False
    assert ADJACENT_PAGE_TABLE_GEOMETRY_SAFETY_V1["same_table_claimed"] is False
    assert ADJACENT_PAGE_TABLE_GEOMETRY_SAFETY_V1["table_semantic_claimed"] is False
