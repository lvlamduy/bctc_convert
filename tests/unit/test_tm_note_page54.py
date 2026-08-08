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
from bctc_ai.tables.tm_note_page54 import load_tm_page54_policy, parse_tm_page54
from bctc_ai.tables.tm_note_word_box import TMNoteRowKind, TMNoteWordBoxError

_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0054-ppocrv6-word-box.json")
_FIXTURE_SHA256 = "a965e909d7f170a2a3bceab4921c2682ed3433b4502b0b021081e569b6f35c71"
_UPSTREAM_OCR_SHA256 = "a0aa1f9c72a93dda30ab95ef4411b8edc37c84b125f788a9f351f4700e9f9073"
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")


def _policy(project_root: Path):
    return load_tm_page54_policy(project_root / "config/tables/tm-note-page54-v1.yaml")


def _render(project_root: Path, tmp_path: Path) -> Path:
    return Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={54},
        )[0].path
    )


def _parsed(project_root: Path, tmp_path: Path):
    return parse_tm_page54(
        project_root / _FIXTURE,
        _render(project_root, tmp_path),
        _policy(project_root),
    )


def test_real_page54_reconstructs_exact_rows_slots_and_provenance(
    project_root: Path, tmp_path: Path
) -> None:
    fixture = project_root / _FIXTURE
    assert sha256_file(fixture) == _FIXTURE_SHA256
    assert fixture.stat().st_size < 7_000

    parsed = _parsed(project_root, tmp_path)

    assert parsed.source_sha256 == _FIXTURE_SHA256
    assert parsed.upstream_ocr_sha256 == _UPSTREAM_OCR_SHA256
    assert parsed.source_render_sha256 == (
        "271d8a818154a13942a0ee22b089985ea5f304e541b374d4150c32a1fad0d902"
    )
    assert parsed.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert parsed.scope == "CONSOLIDATED"
    assert len(parsed.tables) == 1
    assert len(parsed.rows) == 13
    assert parsed.numeric_row_count == 12
    assert parsed.label_only_row_count == 1
    assert parsed.financial_slot_count == 72
    assert parsed.observation_count(ObservationKind.VALUE) == 68
    assert parsed.observation_count(ObservationKind.ZERO) == 0
    assert parsed.observation_count(ObservationKind.DASH) == 4
    assert parsed.unassigned_numeric_line_indices == ()
    assert parsed.excluded_artifact_line_indices == ()
    assert parsed.excluded_footer_numeric_line_indices == (116,)
    assert parsed.mapping_authority is False


def test_page54_binds_six_axes_and_preserves_visible_debt_asset_variants(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)

    assert [axis.axis_key for axis in parsed.axes] == [
        "FINANCE_BANKING",
        "SECURITIES_FUND_MANAGEMENT",
        "INSURANCE",
        "DEBT_AND_ASSET_MANAGEMENT",
        "ELIMINATION",
        "TOTAL",
    ]
    assert [axis.canonical_label for axis in parsed.axes] == [
        "Tài chính Ngân hàng",
        "Chứng khoán Quản lý quỹ",
        "Bảo hiểm",
        "Quản lý nợ và Khai thác tài sản",
        "Loại trừ/Phân loại",
        "Tổng cộng",
    ]
    debt_asset = parsed.axes[3]
    assert debt_asset.current_header_text == "Qun lý n và Khai thác tài săn"
    assert debt_asset.comparative_header_text == "Khai thác n Quăn lý tái sn"
    assert debt_asset.current_header_text != debt_asset.comparative_header_text
    assert len(debt_asset.current_header_line_indices) == 3
    assert len(debt_asset.comparative_header_line_indices) == 3
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


def test_page54_preserves_metric_local_snapshot_and_duration_semantics(
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


def test_page54_preserves_exact_values_and_four_pixel_backed_dashes(
    project_root: Path, tmp_path: Path
) -> None:
    rows = [row for row in _parsed(project_root, tmp_path).rows if row.metric_key]

    assert [[cell.value for cell in row.row.cells] for row in rows] == [
        [1_588_501_057, 31_394_880, 28_098_653, 2_093_615, -38_865_441, 1_611_222_764],
        [1_445_609_236, 22_325_950, 23_274_359, 620_398, -30_352_504, 1_461_477_439],
        [4_916_608, 127_523, 400_952, 55_579, None, 5_500_662],
        [69_039_493, 1_092_526, 2_469_883, 218_554, -35_220_165, 37_600_291],
        [60_128_220, 686_768, 2_247_453, 129_629, -35_220_165, 27_971_905],
        [8_911_273, 405_758, 222_430, 88_925, None, 9_628_386],
        [1_590_458_621, 31_478_443, 27_073_013, 2_250_753, -35_496_903, 1_615_763_927],
        [1_454_652_920, 22_819_473, 22_405_488, 848_676, -26_985_155, 1_473_741_402],
        [5_026_150, 132_990, 397_833, 59_574, None, 5_616_547],
        [209_317_554, 3_896_638, 10_872_447, 1_845_167, -104_342_087, 121_589_719],
        [178_178_314, 2_355_973, 10_246_258, 882_903, -104_342_087, 87_321_361],
        [31_139_240, 1_540_665, 626_189, 962_264, None, 34_268_358],
    ]
    dash_rows = [row for row in rows if row.metric_key in {"FIXED_ASSETS", "PROFIT_BEFORE_TAX"}]
    assert len(dash_rows) == 4
    assert [row.visual_cell_evidence[4].component_box for row in dash_rows] == [
        (2804, 663, 2816, 667),
        (2807, 850, 2821, 855),
        (2816, 1346, 2828, 1350),
        (2819, 1539, 2833, 1544),
    ]
    assert all(
        row.row_kind is TMNoteRowKind.NUMERIC
        and row.row.cells[4].observation is ObservationKind.DASH
        and row.row.cells[4].value is None
        and row.visual_cell_evidence[4] is not None
        for row in dash_rows
    )


def test_page54_period_and_dash_evidence_fail_closed(project_root: Path, tmp_path: Path) -> None:
    fixture = project_root / _FIXTURE
    render = _render(project_root, tmp_path)
    baseline = parse_tm_page54(fixture, render, _policy(project_root))
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    payload["rec_texts"][6] = "30 tháng 03 năm 2026"
    mutated_ocr = tmp_path / "page54-date-drift.json"
    mutated_ocr.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    date_policy = replace(_policy(project_root), source_ocr_sha256=sha256_file(mutated_ocr))
    with pytest.raises(TMNoteWordBoxError, match="visible date drifted"):
        parse_tm_page54(mutated_ocr, render, date_policy)

    image = cv2.imread(str(render), cv2.IMREAD_COLOR)
    assert image is not None
    image[630:700, 2760:2850] = 255
    missing_dash = tmp_path / "page54-missing-dash.png"
    assert cv2.imwrite(str(missing_dash), image)
    missing_dash_hash = sha256_file(missing_dash)
    dash_payload = json.loads(fixture.read_text(encoding="utf-8"))
    dash_payload["source_render_sha256"] = missing_dash_hash
    dash_fixture = tmp_path / "page54-missing-dash.json"
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
        parse_tm_page54(dash_fixture, missing_dash, dash_policy)

    assert "dash_as_zero" in dash_policy.forbidden_semantic_inputs
    assert "flat_period_type_across_mixed_metric_rows" in dash_policy.forbidden_semantic_inputs
    assert "page53_values_as_page54_mapping_or_imputation" in dash_policy.forbidden_semantic_inputs
    assert not baseline.continues_to_page_55
    assert baseline.next_page_note_number == "5"
