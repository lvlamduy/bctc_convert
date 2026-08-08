from __future__ import annotations

import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import cv2
import pytest

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.tables.tm_note_page53 import load_tm_page53_policy, parse_tm_page53
from bctc_ai.tables.tm_note_word_box import TMNoteRowKind, TMNoteWordBoxError

_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0053-ppocrv6-word-box.json")
_FIXTURE_SHA256 = "7116c59b95d2698fc695d1b7bb1690620a0784b5426c8fdce9c459768c1a875f"
_UPSTREAM_OCR_SHA256 = "02e0fe3284a12649d5cce9bd586abedca9afb8ccad33e18425cd555c0df0a551"
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")


def _policy(project_root: Path):
    return load_tm_page53_policy(project_root / "config/tables/tm-note-page53-v1.yaml")


def _render(project_root: Path, tmp_path: Path) -> Path:
    return Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={53},
        )[0].path
    )


def _parsed(project_root: Path, tmp_path: Path):
    return parse_tm_page53(
        project_root / _FIXTURE,
        _render(project_root, tmp_path),
        _policy(project_root),
    )


def test_real_page53_reconstructs_exact_rows_slots_and_provenance(
    project_root: Path, tmp_path: Path
) -> None:
    fixture = project_root / _FIXTURE
    assert sha256_file(fixture) == _FIXTURE_SHA256
    assert fixture.stat().st_size < 7_000

    parsed = _parsed(project_root, tmp_path)

    assert parsed.source_sha256 == _FIXTURE_SHA256
    assert parsed.upstream_ocr_sha256 == _UPSTREAM_OCR_SHA256
    assert parsed.source_render_sha256 == (
        "08ddbfa56c7696c6ade6e2481986f355d6e8a1808296ccc5f800357d57df9d23"
    )
    assert parsed.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert parsed.scope == "CONSOLIDATED"
    assert len(parsed.tables) == 1
    assert len(parsed.rows) == 14
    assert parsed.numeric_row_count == 12
    assert parsed.label_only_row_count == 2
    assert parsed.financial_slot_count == 72
    assert parsed.observation_count(ObservationKind.VALUE) == 68
    assert parsed.observation_count(ObservationKind.ZERO) == 0
    assert parsed.observation_count(ObservationKind.DASH) == 4
    assert parsed.unassigned_numeric_line_indices == ()
    assert parsed.excluded_artifact_line_indices == ()
    assert parsed.excluded_footer_numeric_line_indices == (108,)
    assert parsed.mapping_authority is False


def test_page53_binds_six_axes_in_both_visible_period_blocks(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)

    assert [axis.axis_key for axis in parsed.axes] == [
        "NORTH",
        "CENTRAL",
        "SOUTH",
        "OTHER",
        "ELIMINATION",
        "TOTAL",
    ]
    assert [axis.canonical_label for axis in parsed.axes] == [
        "Miền Bắc",
        "Miền Trung",
        "Miền Nam",
        "Khu vực khác",
        "Loại trừ/Phân loại",
        "Tổng cộng",
    ]
    assert [binding.period_role for binding in parsed.period_bindings] == [
        "CURRENT",
        "COMPARATIVE",
    ]
    assert [binding.visible_date for binding in parsed.period_bindings] == [
        date(2026, 3, 31),
        date(2025, 12, 31),
    ]
    assert {axis.canonical_unit for axis in parsed.axes} == {"VND"}
    assert {axis.unit_multiplier for axis in parsed.axes} == {1_000_000}
    assert all(
        len(axis.current_header_line_indices) == 2
        and len(axis.comparative_header_line_indices) == 2
        for axis in parsed.axes
    )


def test_page53_preserves_metric_local_snapshot_and_duration_semantics(
    project_root: Path, tmp_path: Path
) -> None:
    rows = [row for row in _parsed(project_root, tmp_path).rows if row.metric_key]
    by_role_metric = {(row.period_role, row.metric_key): row for row in rows}

    for metric in ("ASSETS", "LIABILITIES", "FIXED_ASSETS"):
        current = by_role_metric[("CURRENT", metric)]
        comparative = by_role_metric[("COMPARATIVE", metric)]
        assert current.period_type == "SNAPSHOT"
        assert set(current.cell_period_starts) == {date(2026, 3, 31)}
        assert set(current.cell_period_ends) == {date(2026, 3, 31)}
        assert comparative.period_type == "SNAPSHOT"
        assert set(comparative.cell_period_starts) == {date(2025, 12, 31)}
        assert set(comparative.cell_period_ends) == {date(2025, 12, 31)}
    for metric in ("REVENUE", "EXPENSE", "PROFIT_BEFORE_TAX"):
        current = by_role_metric[("CURRENT", metric)]
        comparative = by_role_metric[("COMPARATIVE", metric)]
        assert current.period_type == "DURATION"
        assert set(current.cell_period_starts) == {date(2026, 1, 1)}
        assert set(current.cell_period_ends) == {date(2026, 3, 31)}
        assert comparative.period_type == "DURATION"
        assert set(comparative.cell_period_starts) == {date(2025, 1, 1)}
        assert set(comparative.cell_period_ends) == {date(2025, 12, 31)}


def test_page53_preserves_exact_values_and_four_pixel_backed_dashes(
    project_root: Path, tmp_path: Path
) -> None:
    rows = [row for row in _parsed(project_root, tmp_path).rows if row.metric_key]

    assert [[cell.value for cell in row.row.cells] for row in rows] == [
        [1_158_931_821, 77_723_187, 400_272_594, 13_160_603, -38_865_441, 1_611_222_764],
        [1_004_150_541, 77_299_644, 399_330_816, 11_048_942, -30_352_504, 1_461_477_439],
        [4_847_641, 79_081, 211_522, 362_418, None, 5_500_662],
        [57_201_579, 2_476_226, 12_686_399, 456_252, -35_220_165, 37_600_291],
        [49_431_430, 1_946_291, 11_349_378, 464_971, -35_220_165, 27_971_905],
        [7_770_149, 529_935, 1_337_021, -8_719, None, 9_628_386],
        [1_172_468_605, 73_486_567, 391_719_355, 13_586_303, -35_496_903, 1_615_763_927],
        [1_032_999_587, 71_795_670, 384_462_199, 11_469_101, -26_985_155, 1_473_741_402],
        [4_970_480, 78_441, 204_175, 363_451, None, 5_616_547],
        [174_442_496, 8_000_254, 41_850_617, 1_638_439, -104_342_087, 121_589_719],
        [151_444_226, 5_880_238, 32_740_234, 1_598_750, -104_342_087, 87_321_361],
        [22_998_270, 2_120_016, 9_110_383, 39_689, None, 34_268_358],
    ]
    dash_rows = [row for row in rows if row.metric_key in {"FIXED_ASSETS", "PROFIT_BEFORE_TAX"}]
    assert len(dash_rows) == 4
    assert all(row.row.cells[4].observation is ObservationKind.DASH for row in dash_rows)
    assert [row.visual_cell_evidence[4].component_box for row in dash_rows] == [
        (2813, 727, 2825, 732),
        (2814, 916, 2828, 921),
        (2819, 1365, 2831, 1370),
        (2820, 1558, 2833, 1562),
    ]
    assert all(
        row.row_kind is TMNoteRowKind.NUMERIC
        and row.row.cells[4].value is None
        and row.visual_cell_evidence[4] is not None
        for row in dash_rows
    )


def test_page53_period_and_dash_evidence_fail_closed(project_root: Path, tmp_path: Path) -> None:
    fixture = project_root / _FIXTURE
    render = _render(project_root, tmp_path)
    baseline = parse_tm_page53(fixture, render, _policy(project_root))
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    payload["rec_texts"][8] = "30 tháng 03 năm 2026"
    mutated_ocr = tmp_path / "page53-date-drift.json"
    mutated_ocr.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    date_policy = replace(_policy(project_root), source_ocr_sha256=sha256_file(mutated_ocr))
    with pytest.raises(TMNoteWordBoxError, match="visible date drifted"):
        parse_tm_page53(mutated_ocr, render, date_policy)

    image = cv2.imread(str(render), cv2.IMREAD_COLOR)
    assert image is not None
    image[690:760, 2760:2860] = 255
    missing_dash = tmp_path / "page53-missing-dash.png"
    assert cv2.imwrite(str(missing_dash), image)
    missing_dash_hash = sha256_file(missing_dash)
    dash_payload = json.loads(fixture.read_text(encoding="utf-8"))
    dash_payload["source_render_sha256"] = missing_dash_hash
    dash_fixture = tmp_path / "page53-missing-dash.json"
    dash_fixture.write_text(
        json.dumps(dash_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    dash_policy = replace(
        _policy(project_root),
        source_render_sha256=missing_dash_hash,
        source_ocr_sha256=sha256_file(dash_fixture),
    )
    with pytest.raises(TMNoteWordBoxError, match="lacks constrained pixel evidence"):
        parse_tm_page53(dash_fixture, missing_dash, dash_policy)

    assert "dash_as_zero" in dash_policy.forbidden_semantic_inputs
    assert "flat_period_type_across_mixed_metric_rows" in dash_policy.forbidden_semantic_inputs
    assert not baseline.continues_to_page_54
    assert baseline.next_page_note_number == "4.2"
