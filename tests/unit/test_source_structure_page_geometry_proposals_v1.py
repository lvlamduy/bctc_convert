from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path

from test_source_structure_evidence_projection_v1 import (
    _line_supplement,
    _native_nonmonotonic_visual_order_complete,
    _ocr_complete,
    _ocr_terminal,
    _refresh_ocr_axis_accounting,
    _refresh_result_ref,
)
from test_source_structure_evidence_projection_v2 import _synthetic_ocr_pair

from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
)
from bctc_ai.source_structure.evidence_projection_v1 import project_authenticated_page_v1
from bctc_ai.source_structure.evidence_projection_v2 import project_authenticated_page_v2
from bctc_ai.source_structure.page_geometry_proposals_v1 import (
    generate_page_geometry_proposals_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _canonical_box(pixel_box: list[int]) -> list[int]:
    return [coordinate * 500 for coordinate in pixel_box]


def _line(
    y0: int,
    words: list[tuple[int, int, str]],
) -> dict:
    y1 = y0 + 40
    x0 = min(word[0] for word in words)
    x1 = max(word[1] for word in words)
    pixel_box = [x0, y0, x1, y1]
    pixel_polygon = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
    projected_words = []
    for word_x0, word_x1, text in words:
        word_box = [word_x0, y0, word_x1, y1]
        word_polygon = [
            [word_x0, y0],
            [word_x1, y0],
            [word_x1, y1],
            [word_x0, y1],
        ]
        projected_words.append(
            {
                "raw_text": text,
                "score": None,
                "score_kind": "PP_OCRV6_LINE_SCORE_ONLY",
                "normalized_pixel_bbox": word_box,
                "canonical_bbox_mpt": _canonical_box(word_box),
                "canonical_polygon_mpt": [
                    _canonical_box([point[0], point[1], point[0] + 1, point[1] + 1])[:2]
                    for point in word_polygon
                ],
            }
        )
    return {
        "raw_text": "".join(text for _, _, text in words) or "visible-line",
        "score": 0.95,
        "score_kind": "PP_OCRV6_LINE_RECOGNITION_SCORE",
        "raw_pixel_bbox": pixel_box,
        "raw_pixel_polygon": pixel_polygon,
        "canonical_bbox_mpt": _canonical_box(pixel_box),
        "canonical_polygon_mpt": [[x * 500, y * 500] for x, y in pixel_polygon],
        "words": projected_words,
    }


def _layout_envelope(
    rows: list[tuple[int, list[tuple[int, int]]]],
    *,
    vocabulary: list[str] | None = None,
) -> dict:
    record, result = _ocr_complete()
    words = iter(vocabulary or [f"token-{index}" for index in range(100)])
    result["lines"] = [_line(y0, [(x0, x1, next(words)) for x0, x1 in boxes]) for y0, boxes in rows]
    _refresh_ocr_axis_accounting(record, result)
    return project_authenticated_page_v1(page_record=record, page_result=result)


def _structure_signature(proposal_set: dict, envelope: dict) -> list[tuple]:
    atom_by_id = {atom["source_local_id"]: atom for atom in envelope["atoms"]}
    return [
        (
            proposal["kind"],
            tuple(proposal["canonical_bbox_mpt"]),
            tuple(atom_by_id[atom_id]["kind"] for atom_id in proposal["primary_atom_ids"]),
            tuple(
                tuple(atom_by_id[atom_id]["canonical_bbox_mpt"])
                for atom_id in proposal["primary_atom_ids"]
            ),
            tuple(proposal["evidence_codes"]),
        )
        for proposal in proposal_set["proposals"]
    ]


def test_repeated_columns_create_only_a_tabular_geometry_candidate() -> None:
    rows = [
        (120, [(100, 180), (500, 590), (850, 930)]),
        (200, [(100, 180), (500, 590), (850, 930)]),
        (280, [(100, 180), (500, 590), (850, 930)]),
        (360, [(100, 180), (500, 590), (850, 930)]),
    ]
    envelope = _layout_envelope(rows)
    first = generate_page_geometry_proposals_v1(envelope)
    second = generate_page_geometry_proposals_v1(deepcopy(envelope))

    assert canonical_json_bytes_v1(first) == canonical_json_bytes_v1(second)
    assert [proposal["kind"] for proposal in first["proposals"]] == ["TABULAR_GEOMETRY_CANDIDATE"]
    assert "DENSE_TABULAR_ALIGNMENT" in first["proposals"][0]["evidence_codes"]
    assert len(first["dispositions"]) == len(envelope["atoms"])
    assert all(
        disposition["primary_disposition"] == "OWNED_BY_SOURCE_OBJECT"
        for disposition in first["dispositions"]
    )


def test_narrative_geometry_stays_a_source_block_candidate() -> None:
    rows = [
        (120, [(100, 170), (240, 320), (430, 500), (650, 730)]),
        (200, [(100, 170), (280, 360), (490, 560), (720, 800)]),
        (280, [(100, 170), (330, 410), (550, 620), (790, 870)]),
        (360, [(100, 170), (380, 460), (610, 680), (860, 940)]),
    ]
    proposals = generate_page_geometry_proposals_v1(_layout_envelope(rows))
    assert [proposal["kind"] for proposal in proposals["proposals"]] == ["SOURCE_BLOCK_CANDIDATE"]
    assert "DENSE_TABULAR_ALIGNMENT" not in proposals["proposals"][0]["evidence_codes"]


def test_large_vertical_gap_splits_source_blocks_without_semantic_help() -> None:
    rows = [
        (100, [(100, 180), (300, 380)]),
        (180, [(100, 180), (340, 420)]),
        (600, [(120, 200), (500, 580)]),
        (680, [(120, 200), (540, 620)]),
    ]
    proposals = generate_page_geometry_proposals_v1(_layout_envelope(rows))
    assert [proposal["kind"] for proposal in proposals["proposals"]] == [
        "SOURCE_BLOCK_CANDIDATE",
        "SOURCE_BLOCK_CANDIDATE",
    ]
    assert all(len(proposal["primary_atom_ids"]) == 6 for proposal in proposals["proposals"])


def test_authenticated_native_order_is_not_resorted_by_geometric_y() -> None:
    record, result = _native_nonmonotonic_visual_order_complete()
    vertical_positions = ((600_000, 610_000), (100_000, 110_000))
    for line, (y0, y1) in zip(result["lines"], vertical_positions, strict=True):
        line["canonical_bbox_mpt"][1::2] = [y0, y1]
        for word in line["words"]:
            word["canonical_bbox_mpt"][1::2] = [y0, y1]
    result["words"] = [word for line in result["lines"] for word in line["words"]]
    _refresh_result_ref(record, result)
    envelope = project_authenticated_page_v1(page_record=record, page_result=result)

    proposals = generate_page_geometry_proposals_v1(envelope)

    assert len(proposals["proposals"]) == 1
    primary_ids = proposals["proposals"][0]["primary_atom_ids"]
    expected_ids = [
        atom["source_local_id"]
        for atom in envelope["atoms"]
        if atom["authority"] == "AUTHENTICATED_PRIMARY"
    ]
    assert primary_ids == expected_ids


def test_text_and_numeric_appearance_cannot_change_geometry_classification() -> None:
    rows = [
        (120, [(100, 180), (500, 590), (850, 930)]),
        (200, [(100, 180), (500, 590), (850, 930)]),
        (280, [(100, 180), (500, 590), (850, 930)]),
    ]
    numeric = _layout_envelope(
        rows,
        vocabulary=["1", "2.000", "(3)", "4", "5", "6", "7", "8", "9"],
    )
    prose = _layout_envelope(
        rows,
        vocabulary=[
            "heading",
            "alpha",
            "omega",
            "paragraph",
            "plain",
            "words",
            "title",
            "text",
            "only",
        ],
    )
    assert _structure_signature(generate_page_geometry_proposals_v1(numeric), numeric) == (
        _structure_signature(generate_page_geometry_proposals_v1(prose), prose)
    )


def test_quarantine_and_terminal_atoms_are_never_promoted() -> None:
    rows = [
        (120, [(100, 180), (500, 590), (850, 930)]),
        (200, [(100, 180), (500, 590), (850, 930)]),
        (280, [(100, 180), (500, 590), (850, 930)]),
    ]
    envelope = _layout_envelope(
        rows,
        vocabulary=["", "b", "c", "d", "e", "f", "g", "h", "i"],
    )
    quarantined_id = next(
        atom["source_local_id"]
        for atom in envelope["atoms"]
        if atom["authority"] == "UPSTREAM_QUARANTINE"
    )
    nonterminal = generate_page_geometry_proposals_v1(envelope)
    assert all(
        quarantined_id not in proposal["primary_atom_ids"] for proposal in nonterminal["proposals"]
    )
    quarantine_disposition = next(
        item for item in nonterminal["dispositions"] if item["source_atom_id"] == quarantined_id
    )
    assert quarantine_disposition["primary_disposition"] == "UPSTREAM_QUARANTINED"

    record, result = _ocr_terminal()
    supplement, supplement_ref = _line_supplement(record, result)
    terminal = project_authenticated_page_v1(
        page_record=record,
        page_result=result,
        line_only_supplement=supplement,
        line_only_supplement_ref=supplement_ref,
    )
    proposal_set = generate_page_geometry_proposals_v1(terminal)
    assert proposal_set["proposals"] == []
    assert len(proposal_set["dispositions"]) == len(terminal["atoms"])
    assert {disposition["primary_disposition"] for disposition in proposal_set["dispositions"]} <= {
        "UPSTREAM_TERMINAL_UNRESOLVED",
        "UPSTREAM_QUARANTINED",
    }


def test_validated_v2_projection_uses_the_transitively_bound_neutral_view() -> None:
    record, result = _synthetic_ocr_pair()
    projection = project_authenticated_page_v2(page_record=record, page_result=result)
    proposals = generate_page_geometry_proposals_v1(projection)
    assert proposals["neutral_page_sha256"] == projection["neutral_page_v1_sha256"]
    assert len(proposals["dispositions"]) == len(projection["neutral_page_v1"]["atoms"])


def test_generator_source_has_no_visible_text_or_external_hint_access() -> None:
    source_path = PROJECT_ROOT / "src/bctc_ai/source_structure/page_geometry_proposals_v1.py"
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
            "filename",
            "note",
            "raw_text",
            "raw_token",
            "role_a",
            "schema",
            "title",
            "normalized_value",
            "document_id",
            "physical_page",
            "route",
            "source_sha256",
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
    }
