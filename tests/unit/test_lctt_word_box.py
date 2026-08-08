from __future__ import annotations

from pathlib import Path

import pytest

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.mapping.lctt import CashFlowMethod
from bctc_ai.tables.lctt_word_box import (
    LCTTPageInput,
    LCTTWordBoxError,
    load_lctt_word_box_policy,
    parse_lctt_word_box_document,
)

_OCR_ROOT = Path("output/calibration/recovery-e0027-mbb-q1-2026-role-c-20260807")
_RENDER_ROOT = Path(
    "output/calibration/recovery-e0027-mbb-q1-2026-20260807/eebeda2ebc09b0d42032/renders"
)
_EXPECTED_HASHES = {
    "page-0007-ocr": "a30bec185a158747560700d545fbef993fd518cb74fd34e17ca7369dceddb664",
    "page-0008-ocr": "db39b3e6f2dd7985283ee12e834f22abb835d774b446363a4e32382a1186b105",
    "page-0007-image": "6f80fc19aff43a0e0969fd2eeae5ad7789479d9d089cdee294de7bf10f781933",
    "page-0008-image": "3736962e3ca39499039dead61780854ead6338ec3f8b36fc2e175d041c16f370",
}


def _real_page_inputs(project_root: Path) -> tuple[LCTTPageInput, ...]:
    inputs = tuple(
        LCTTPageInput(
            result_path=(project_root / _OCR_ROOT / f"ppocrv6-page-{page:04d}" / "ocr_result.json"),
            source_image_path=project_root / _RENDER_ROOT / f"page-{page:04d}.png",
            page_tag=f"page-{page:04d}",
        )
        for page in (7, 8)
    )
    if not all(page.result_path.is_file() and page.source_image_path.is_file() for page in inputs):
        pytest.skip("hash-locked MBB Q1/2026 LCTT source artifacts are not local")
    return inputs


def test_mbb_q1_2026_lctt_two_page_matrix(project_root: Path) -> None:
    inputs = _real_page_inputs(project_root)
    for page in inputs:
        assert sha256_file(page.result_path) == _EXPECTED_HASHES[f"{page.page_tag}-ocr"]
        assert sha256_file(page.source_image_path) == _EXPECTED_HASHES[f"{page.page_tag}-image"]

    policy = load_lctt_word_box_policy(project_root / "config/tables/lctt-word-box-v1.yaml")
    parsed = parse_lctt_word_box_document(inputs, policy)

    assert parsed.scope == "CONSOLIDATED"
    assert parsed.method is CashFlowMethod.DIRECT
    assert [page.continuation for page in parsed.pages] == [False, True]
    assert [len(page.rows) for page in parsed.pages] == [34, 9]
    assert len(parsed.rows) == 43
    assert parsed.cell_slot_count == 86
    assert parsed.value_cell_count == 71
    assert parsed.dash_cell_count == 9
    assert parsed.blank_cell_count == 6
    assert all(not page.unassigned_numeric_line_indices for page in parsed.pages)

    for page in parsed.pages:
        assert [axis.current_or_comparative for axis in page.axes] == [
            "CURRENT",
            "COMPARATIVE",
        ]
        assert [axis.period_start.isoformat() for axis in page.axes] == [
            "2026-01-01",
            "2025-01-01",
        ]
        assert [axis.period_end.isoformat() for axis in page.axes] == [
            "2026-03-31",
            "2025-03-31",
        ]
        assert {axis.period_type for axis in page.axes} == {"DURATION"}
        assert {axis.duration_months for axis in page.axes} == {3}
        assert {axis.canonical_unit for axis in page.axes} == {"VND"}
        assert {axis.unit_multiplier for axis in page.axes} == {1_000_000}

    page_7, page_8 = parsed.pages
    assert [row.label_line_indices for row in page_7.rows] == [
        (13,),
        (16,),
        (19,),
        (22,),
        (23, 26),
        (29,),
        (30, 33),
        (36,),
        (40,),
        (41, 44),
        (47,),
        (50,),
        (53,),
        (54, 55),
        (58,),
        (59, 62),
        (65,),
        (68,),
        (71,),
        (74,),
        (77,),
        (80,),
        (81, 84),
        (85, 88),
        (91,),
        (94,),
        (97,),
        (98,),
        (101,),
        (104,),
        (105,),
        (108,),
        (109, 112),
        (115,),
    ]
    assert [row.label_line_indices for row in page_8.rows] == [
        (13,),
        (14,),
        (16, 17),
        (19, 20),
        (22,),
        (23,),
        (26,),
        (29,),
        (32,),
    ]
    assert [[cell.observation for cell in row.row.cells] for row in page_7.rows] == [
        [ObservationKind.BLANK, ObservationKind.BLANK],
        *[[ObservationKind.VALUE, ObservationKind.VALUE] for _ in range(12)],
        [ObservationKind.DASH, ObservationKind.DASH],
        *[[ObservationKind.VALUE, ObservationKind.VALUE] for _ in range(13)],
        [ObservationKind.BLANK, ObservationKind.BLANK],
        [ObservationKind.VALUE, ObservationKind.VALUE],
        [ObservationKind.VALUE, ObservationKind.VALUE],
        [ObservationKind.DASH, ObservationKind.DASH],
        [ObservationKind.VALUE, ObservationKind.VALUE],
        [ObservationKind.VALUE, ObservationKind.VALUE],
        [ObservationKind.VALUE, ObservationKind.VALUE],
    ]
    assert [[cell.observation for cell in row.row.cells] for row in page_8.rows] == [
        [ObservationKind.BLANK, ObservationKind.BLANK],
        [ObservationKind.VALUE, ObservationKind.DASH],
        [ObservationKind.DASH, ObservationKind.VALUE],
        [ObservationKind.VALUE, ObservationKind.DASH],
        [ObservationKind.DASH, ObservationKind.DASH],
        *[[ObservationKind.VALUE, ObservationKind.VALUE] for _ in range(4)],
    ]
    assert [axis.axis_right_edge for axis in page_7.axes] == [1859.5, 2389.5]
    assert [axis.axis_right_edge for axis in page_8.axes] == [1887.0, 2420.0]
    assert page_7.rows[8].row.note_reference == "IV.10"
    assert page_8.rows[-1].row.note_reference == "IV.12"
    assert [cell.observation for cell in page_7.rows[13].row.cells] == [
        ObservationKind.DASH,
        ObservationKind.DASH,
    ]
    assert [cell.observation for cell in page_7.rows[30].row.cells] == [
        ObservationKind.DASH,
        ObservationKind.DASH,
    ]
    assert [cell.observation for cell in page_8.rows[4].row.cells] == [
        ObservationKind.DASH,
        ObservationKind.DASH,
    ]
    assert page_7.rows[31].row.label == ("Tin thu/(chi) đu tư, góp vôn vào các đon v khác")
    assert [cell.value for cell in page_7.rows[31].row.cells] == [490, -71_299]


def test_lctt_policy_is_hash_bound_to_visible_dash_detector(
    project_root: Path, tmp_path: Path
) -> None:
    source = project_root / "config/tables/lctt-word-box-v1.yaml"
    dash_source = project_root / "config/tables/word-box-reconstruction.yaml"
    policy = tmp_path / source.name
    dash = tmp_path / dash_source.name
    policy.write_bytes(source.read_bytes())
    dash.write_text(
        dash_source.read_text(encoding="utf-8").replace(
            "dash_min_foreground_contrast: 25", "dash_min_foreground_contrast: 24"
        ),
        encoding="utf-8",
    )

    with pytest.raises(LCTTWordBoxError, match="dash detector config hash drifted"):
        load_lctt_word_box_policy(policy)
