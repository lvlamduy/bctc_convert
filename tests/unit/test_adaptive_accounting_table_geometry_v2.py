from __future__ import annotations

from copy import deepcopy

import pytest

from bctc_ai.evaluation.adaptive_accounting_table_geometry_v2 import (
    ADAPTIVE_ACCOUNTING_TABLE_GEOMETRY_AUTHORITY_V2,
    AdaptiveAccountingTableGeometryV2Error,
    build_row_band_envelope_v2,
    compare_page_lane_signatures_v2,
    normalize_bbox_to_ppm_v2,
    resolve_accounting_table_geometry_v2,
)


def _atom(atom_id: str, kind: str, bbox: list[int]) -> dict[str, object]:
    return {"atom_id": atom_id, "bbox": bbox, "kind": kind}


def _base_atoms() -> list[dict[str, object]]:
    return [
        _atom("label-1", "LABEL", [20, 60, 300, 90]),
        _atom("value-1-a", "VALUE", [620, 60, 720, 90]),
        _atom("value-1-b", "VALUE", [840, 61, 920, 91]),
        _atom("label-2", "LABEL", [20, 110, 310, 140]),
        _atom("value-2-a", "VALUE", [650, 110, 720, 140]),
        _atom("value-2-b", "VALUE", [810, 111, 920, 141]),
        _atom("label-3", "LABEL", [20, 160, 260, 190]),
        _atom("value-3-a", "VALUE", [635, 160, 720, 190]),
        _atom("value-3-b", "VALUE", [825, 159, 920, 189]),
    ]


def _resolve(
    atoms: list[dict[str, object]],
    *,
    page_width: int = 1000,
    page_height: int = 400,
    region_bbox: list[int] | None = None,
) -> dict[str, object]:
    return resolve_accounting_table_geometry_v2(
        atoms,
        page_width=page_width,
        page_height=page_height,
        expected_lane_count=2,
        region_bbox=region_bbox or [10, 40, 980, 230],
    )


def _transform(
    atoms: list[dict[str, object]], *, factor: int, dx: int, dy: int
) -> list[dict[str, object]]:
    transformed = []
    for atom in atoms:
        left, top, right, bottom = atom["bbox"]  # type: ignore[misc]
        transformed.append(
            {
                **atom,
                "bbox": [
                    left * factor + dx,
                    top * factor + dy,
                    right * factor + dx,
                    bottom * factor + dy,
                ],
            }
        )
    return transformed


def _assignment_projection(result: dict[str, object]) -> list[tuple[int, int | None, str]]:
    return [
        (item["row_ordinal"], item["column_ordinal"], item["status"])
        for item in result["assignments"]  # type: ignore[union-attr]
    ]


def test_integer_normalization_and_row_envelope_are_exact() -> None:
    assert normalize_bbox_to_ppm_v2([150, 250, 550, 450], extent_bbox=[50, 50, 1050, 850]) == [
        100_000,
        250_000,
        500_000,
        500_000,
    ]
    envelope = build_row_band_envelope_v2(
        [[150, 250, 300, 280], [600, 252, 700, 282]],
        extent_bbox=[50, 50, 1050, 850],
    )
    assert envelope == {
        "bbox": [150, 250, 700, 282],
        "center2_median": 532,
        "height_median": 30,
        "member_count": 2,
        "normalized_bbox_ppm": [100_000, 250_000, 650_000, 290_000],
        "vertical_center2_spread": 4,
    }


def test_provider_permutation_is_byte_for_byte_invariant() -> None:
    forward = _resolve(_base_atoms())
    reverse = _resolve(list(reversed(_base_atoms())))

    assert forward == reverse
    assert forward["status"] == "GEOMETRY_PROPOSAL_RESOLVED"
    assert len(forward["row_bands"]) == 3  # type: ignore[arg-type]
    assert len(forward["column_lanes"]) == 2  # type: ignore[arg-type]
    assert forward["authority_boundary"] == ADAPTIVE_ACCOUNTING_TABLE_GEOMETRY_AUTHORITY_V2


@pytest.mark.parametrize("factor", [2, 3, 4])
def test_scale_and_translation_preserve_topology_id_and_scope_signature(factor: int) -> None:
    base = _resolve(_base_atoms())
    dx, dy = 70, 90
    moved = _resolve(
        _transform(_base_atoms(), factor=factor, dx=dx, dy=dy),
        page_width=1000 * factor + 2 * dx,
        page_height=400 * factor + 2 * dy,
        region_bbox=[
            10 * factor + dx,
            40 * factor + dy,
            980 * factor + dx,
            230 * factor + dy,
        ],
    )

    assert moved["geometry_invariance_id"] == base["geometry_invariance_id"]
    assert moved["page_lane_signature"] == base["page_lane_signature"]
    assert _assignment_projection(moved) == _assignment_projection(base)


@pytest.mark.parametrize("jitter", range(1, 9))
def test_bbox_jitter_one_through_eight_is_topologically_stable(jitter: int) -> None:
    atoms = deepcopy(_base_atoms())
    for ordinal, atom in enumerate(atoms):
        if atom["kind"] == "VALUE":
            direction = -1 if ordinal % 2 else 1
            atom["bbox"][1] += direction * jitter  # type: ignore[index]
            atom["bbox"][3] += direction * jitter  # type: ignore[index]
            atom["bbox"][2] += direction * jitter  # type: ignore[index]
    base = _resolve(_base_atoms())
    jittered = _resolve(atoms)

    assert jittered["geometry_invariance_id"] == base["geometry_invariance_id"]
    assert _assignment_projection(jittered) == _assignment_projection(base)
    assert not jittered["uncertainties"]


def test_horizontal_provider_split_is_merged_before_lane_assignment() -> None:
    base = _resolve(_base_atoms())
    split = [atom for atom in _base_atoms() if atom["atom_id"] != "value-1-a"]
    split.extend(
        [
            _atom("value-1-a-left", "VALUE", [620, 60, 667, 90]),
            _atom("value-1-a-right", "VALUE", [670, 60, 720, 90]),
        ]
    )
    result = _resolve(split)

    assert result["page_lane_signature"] == base["page_lane_signature"]
    first = next(
        item
        for item in result["assignments"]  # type: ignore[union-attr]
        if item["row_ordinal"] == 0 and item["column_ordinal"] == 0
    )
    assert first["atom_ids"] == ["value-1-a-left", "value-1-a-right"]


def test_provider_merge_across_two_lanes_fails_closed() -> None:
    merged = [atom for atom in _base_atoms() if atom["atom_id"] not in {"value-1-a", "value-1-b"}]
    merged.append(_atom("merged-two-lanes", "VALUE", [620, 60, 920, 91]))
    result = _resolve(merged)

    assignment = next(
        item
        for item in result["assignments"]  # type: ignore[union-attr]
        if item["atom_ids"] == ["merged-two-lanes"]
    )
    assert assignment["column_ordinal"] is None
    assert assignment["status"] == "CROSS_LANE_MERGED_VALUE_GROUP_UNRESOLVED"
    assert result["status"] == "GEOMETRY_PROPOSAL_UNRESOLVED"
    assert not any(
        item["row_ordinal"] == 0
        for item in result["missing_cell_region_proposals"]  # type: ignore[union-attr]
    )


def test_missing_cell_proposal_is_bounded_and_requires_pixel_authority() -> None:
    atoms = [atom for atom in _base_atoms() if atom["atom_id"] != "value-3-a"]
    result = _resolve(atoms)

    assert result["status"] == (
        "GEOMETRY_PROPOSAL_WITH_MISSING_CELL_REGIONS_REQUIRES_PIXEL_AUTHORITY"
    )
    proposals = result["missing_cell_region_proposals"]
    assert len(proposals) == 1  # type: ignore[arg-type]
    proposal = proposals[0]  # type: ignore[index]
    assert (proposal["row_ordinal"], proposal["column_ordinal"]) == (2, 0)
    assert proposal["authority"] == ("PIXEL_REGION_PROPOSAL_REQUIRES_INDEPENDENT_RECOGNITION")
    left, top, right, bottom = proposal["raw_pixel_bbox"]
    assert 10 <= left < right <= 980
    assert 40 <= top < bottom <= 230


def test_extra_value_is_retained_as_uncertainty_not_a_new_lane() -> None:
    atoms = [*_base_atoms(), _atom("poison-value", "VALUE", [480, 160, 530, 190])]
    result = _resolve(atoms)

    assert len(result["column_lanes"]) == 2  # type: ignore[arg-type]
    poison = next(
        item
        for item in result["assignments"]  # type: ignore[union-attr]
        if item["atom_ids"] == ["poison-value"]
    )
    assert poison["column_ordinal"] is None
    assert poison["status"] == "OUTSIDE_RESOLVED_LANE_TOLERANCE"
    assert result["status"] == "GEOMETRY_PROPOSAL_UNRESOLVED"


def test_region_first_scope_excludes_a_following_table_poison() -> None:
    base = _resolve(_base_atoms(), page_height=700)
    poison = [
        _atom("next-label-1", "LABEL", [20, 400, 300, 430]),
        _atom("next-value-1-a", "VALUE", [500, 400, 590, 430]),
        _atom("next-value-1-b", "VALUE", [740, 400, 830, 430]),
        _atom("next-label-2", "LABEL", [20, 450, 300, 480]),
        _atom("next-value-2-a", "VALUE", [500, 450, 590, 480]),
        _atom("next-value-2-b", "VALUE", [740, 450, 830, 480]),
    ]
    bounded = _resolve([*_base_atoms(), *poison], page_height=700)

    assert bounded == base


def test_historical_ctg_missing_dash_region_survives_real_bbox_jitter() -> None:
    # Frozen annual-2025 CTG p39 boxes.  The current-period dash on the
    # "Vàng phi tiền tệ" row is visible at [1258, 1413, 1292, 1447] but was
    # absent from the detector axis.
    atoms = [
        _atom("l36", "LABEL", [319, 1318, 570, 1349]),
        _atom("v37", "VALUE", [1142, 1316, 1285, 1349]),
        _atom("v38", "VALUE", [1386, 1317, 1513, 1345]),
        _atom("l39", "LABEL", [317, 1347, 610, 1383]),
        _atom("v40", "VALUE", [1157, 1349, 1284, 1379]),
        _atom("v41", "VALUE", [1387, 1349, 1515, 1377]),
        _atom("l42", "LABEL", [318, 1381, 476, 1415]),
        _atom("v43", "VALUE", [1196, 1379, 1290, 1415]),
        _atom("v44", "VALUE", [1423, 1380, 1517, 1412]),
        _atom("l45", "LABEL", [319, 1413, 521, 1447]),
        _atom("v46", "VALUE", [1476, 1411, 1520, 1445]),
        _atom("l47", "LABEL", [318, 1445, 642, 1477]),
        _atom("v48", "VALUE", [1196, 1441, 1289, 1477]),
        _atom("v49", "VALUE", [1424, 1443, 1518, 1476]),
        _atom("v50", "VALUE", [1143, 1508, 1287, 1539]),
        _atom("v51", "VALUE", [1371, 1507, 1516, 1538]),
    ]
    result = resolve_accounting_table_geometry_v2(
        atoms,
        page_width=1654,
        page_height=2339,
        expected_lane_count=2,
        region_bbox=[300, 1300, 1540, 1560],
    )

    proposals = result["missing_cell_region_proposals"]
    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal["column_ordinal"] == 0
    left, top, right, bottom = proposal["raw_pixel_bbox"]
    assert left <= 1258 < 1292 <= right
    assert top <= 1430 <= bottom
    assert [left, top, right, bottom] == [1150, 1412, 1297, 1443]


def test_adjacent_page_signature_is_only_a_compatibility_candidate() -> None:
    previous = _resolve(_base_atoms())["page_lane_signature"]
    following_atoms = _transform(_base_atoms(), factor=2, dx=35, dy=300)
    following = _resolve(
        following_atoms,
        page_width=2070,
        page_height=1200,
        region_bbox=[55, 380, 1995, 760],
    )["page_lane_signature"]

    assert previous == following
    comparison = compare_page_lane_signatures_v2(previous, following)
    assert comparison["status"] == "COMPATIBLE_PAGE_LANE_SIGNATURE_CANDIDATE"
    assert comparison["authority"] == (
        "GEOMETRY_COMPATIBILITY_CANDIDATE_ONLY_NO_CONTINUATION_OR_MERGE_CLAIM"
    )
    assert comparison["lane_delta_scope_ppm"] == [0, 0]


def test_adjacent_page_lane_drift_is_unresolved() -> None:
    previous = _resolve(_base_atoms())["page_lane_signature"]
    drifted_atoms = deepcopy(_base_atoms())
    for atom in drifted_atoms:
        if atom["atom_id"].endswith("-b"):
            atom["bbox"][0] -= 50  # type: ignore[index]
            atom["bbox"][2] -= 50  # type: ignore[index]
    following = _resolve(drifted_atoms)["page_lane_signature"]

    comparison = compare_page_lane_signatures_v2(previous, following)
    assert comparison["status"] == "UNRESOLVED_PAGE_LANE_SIGNATURE"
    assert comparison["tolerance_margin_ppm"] < 0


def test_synthetic_five_hundred_row_panel_retains_two_lanes() -> None:
    atoms = []
    for row in range(500):
        top = 30 + row * 34
        atoms.extend(
            [
                _atom(f"l-{row}", "LABEL", [20, top, 400, top + 24]),
                _atom(f"a-{row}", "VALUE", [620 - row % 7, top, 720, top + 24]),
                _atom(f"b-{row}", "VALUE", [820 - row % 11, top, 920, top + 24]),
            ]
        )
    result = resolve_accounting_table_geometry_v2(
        atoms,
        page_width=1000,
        page_height=17_100,
        expected_lane_count=2,
        region_bbox=[10, 10, 980, 17_050],
    )

    assert result["status"] == "GEOMETRY_PROPOSAL_RESOLVED"
    assert len(result["row_bands"]) == 500
    assert len(result["assignments"]) == 1000
    assert [lane["vertical_support_count"] for lane in result["column_lanes"]] == [500, 500]


@pytest.mark.parametrize(
    ("atoms", "kwargs"),
    [
        ([_atom("a", "VALUE", [1, 1, 2, 2]), _atom("a", "VALUE", [3, 3, 4, 4])], {}),
        ([_atom("a", "VALUE", [1, 1, 2, 2])], {"expected_lane_count": True}),
        ([{"atom_id": "a", "bbox": [1, 1, 2, 2], "kind": "NUMBER"}], {}),
    ],
)
def test_malformed_or_typed_forgery_is_rejected(
    atoms: list[dict[str, object]], kwargs: dict[str, object]
) -> None:
    with pytest.raises(AdaptiveAccountingTableGeometryV2Error):
        resolve_accounting_table_geometry_v2(
            atoms,
            page_width=100,
            page_height=100,
            **kwargs,  # type: ignore[arg-type]
        )
