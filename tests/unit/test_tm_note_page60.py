from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import cv2
import pytest

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.tables.tm_note_page60 import load_tm_page60_policy, parse_tm_page60
from bctc_ai.tables.tm_note_word_box import TMNoteWordBoxError

_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0060-ppocrv6-word-box.json")
_FIXTURE_SHA256 = "59c7c24afc9b5f42ee147aa51d2442e8fb3d771e6f8b2527acb39ed66a66057a"
_UPSTREAM_OCR_SHA256 = "bbb9f5d727251c37cca5d9b331f09c214f288ed1cf7b049f6287e78694feb8ec"
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")


def _policy(project_root: Path):
    return load_tm_page60_policy(project_root / "config/tables/tm-note-page60-v1.yaml")


def _render(project_root: Path, tmp_path: Path) -> Path:
    return Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={60},
        )[0].path
    )


def _parsed(project_root: Path, tmp_path: Path):
    return parse_tm_page60(
        project_root / _FIXTURE,
        _render(project_root, tmp_path),
        _policy(project_root),
    )


def test_real_page60_reconstructs_exact_rows_slots_and_provenance(
    project_root: Path, tmp_path: Path
) -> None:
    fixture = project_root / _FIXTURE
    assert sha256_file(fixture) == _FIXTURE_SHA256
    assert fixture.stat().st_size < 9_000

    parsed = _parsed(project_root, tmp_path)

    assert parsed.source_sha256 == _FIXTURE_SHA256
    assert parsed.upstream_ocr_sha256 == _UPSTREAM_OCR_SHA256
    assert parsed.source_render_sha256 == (
        "3d59e84360bcf27266c702102d4acc2561cc8e9f50ba22fb6371d6423ade8026"
    )
    assert parsed.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert parsed.scope == "CONSOLIDATED"
    assert len(parsed.tables) == 1
    assert len(parsed.rows) == 22
    assert parsed.numeric_row_count == 20
    assert parsed.label_only_row_count == 2
    assert parsed.financial_slot_count == 140
    assert parsed.observation_count(ObservationKind.VALUE) == 93
    assert parsed.observation_count(ObservationKind.ZERO) == 0
    assert parsed.observation_count(ObservationKind.DASH) == 47
    assert parsed.observation_count(ObservationKind.BLANK) == 0
    assert parsed.unassigned_numeric_line_indices == ()
    assert parsed.excluded_artifact_line_indices == ()
    assert parsed.excluded_low_confidence_line_indices == (17,)
    assert parsed.excluded_footer_numeric_line_indices == (135,)
    assert not parsed.mapping_authority
    assert not parsed.continues_to_page_61
    assert parsed.next_page_topic == "EXCHANGE_RATE"


def test_page60_binds_seven_visible_axes_to_one_snapshot_unit_scope(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)

    assert [axis.axis_key for axis in parsed.axes] == [
        "OVERDUE",
        "WITHIN_1M",
        "FROM_1_TO_3M",
        "FROM_3_TO_12M",
        "FROM_1_TO_5Y",
        "OVER_5Y",
        "TOTAL",
    ]
    assert [axis.axis_right_edge for axis in parsed.axes] == [
        1220,
        1570,
        1912,
        2251,
        2589,
        2935,
        3273,
    ]
    assert {axis.period_role for axis in parsed.axes} == {"CURRENT"}
    assert {axis.period_type for axis in parsed.axes} == {"SNAPSHOT"}
    assert {axis.period_start for axis in parsed.axes} == {date(2026, 3, 31)}
    assert {axis.period_end for axis in parsed.axes} == {date(2026, 3, 31)}
    assert {axis.canonical_unit for axis in parsed.axes} == {"VND"}
    assert {axis.unit_multiplier for axis in parsed.axes} == {1_000_000}
    numeric = [row for row in parsed.rows if row.metric_key]
    assert all(set(row.cell_period_roles) == {"CURRENT"} for row in numeric)
    assert all(set(row.cell_period_types) == {"SNAPSHOT"} for row in numeric)


def test_page60_preserves_exact_twenty_by_seven_value_and_dash_matrix(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    rows = [row for row in parsed.rows if row.metric_key]

    assert [[cell.value for cell in row.row.cells] for row in rows] == [
        [None, 5_741_287, None, None, None, None, 5_741_287],
        [None, 15_156_039, None, None, None, None, 15_156_039],
        [None, 140_423_657, 13_234_746, 9_011_770, 2_441_094, 197_480, 165_308_747],
        [None, 5_093_432, None, None, None, None, 5_093_432],
        [None, None, None, None, None, None, None],
        [
            23_974_299,
            102_219_076,
            194_018_146,
            326_479_156,
            250_874_307,
            225_284_766,
            1_122_849_750,
        ],
        [1_630_386, 11_955_439, 20_164_961, 102_088_360, 60_520_276, 67_031_876, 263_391_298],
        [None, None, None, None, 559_134, None, 559_134],
        [None, None, None, None, 5_716_976, None, 5_716_976],
        [66_980, 40_152_229, 60_086, 2_402_149, 180_315, 45_284, 42_907_043],
        [
            25_671_665,
            320_741_159,
            227_477_939,
            439_981_435,
            320_292_102,
            292_559_406,
            1_626_723_706,
        ],
        [None, 25_669_608, 2_676_891, None, None, None, 28_346_499],
        [None, 160_704_304, 48_741_418, 28_819_850, 18_625_903, None, 256_891_475],
        [None, 186_297_873, 158_102_383, 315_175_933, 246_318_606, 23_537, 905_918_332],
        [None, 100_278, 403_319, 76_874, 80_855, None, 661_326],
        [None, 326_675, 1_365_173, 1_551_614, 3_553, None, 3_247_015],
        [None, 3_150_000, 16_071_246, 89_498_946, 83_421_162, 16_675_099, 208_816_453],
        [None, 57_110_115, 123_167, 330_559, 26_671, 3_507, 57_594_019],
        [None, 433_358_853, 227_483_597, 435_453_776, 348_476_750, 16_702_143, 1_461_475_119],
        [25_671_665, -112_617_694, -5_658, 4_527_659, -28_184_648, 275_857_263, 165_248_587],
    ]
    assert [row.metric_key for row in rows][0] == "CASH_AND_PRECIOUS_METALS"
    assert [row.metric_key for row in rows][-1] == "NET_LIQUIDITY_GAP"
    assert [row.source_role for row in parsed.rows if not row.metric_key] == [
        "ASSET_SECTION",
        "LIABILITY_SECTION",
    ]


def test_page60_all_dashes_are_pixel_backed_and_false_glyph_is_excluded(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    evidence = []
    for row in parsed.rows:
        for index, record in enumerate(row.visual_cell_evidence):
            if record is not None:
                evidence.append((row.metric_key, parsed.axes[index].axis_key, record.component_box))

    assert len(evidence) == 47
    assert (
        hashlib.sha256(json.dumps(evidence, separators=(",", ":")).encode()).hexdigest()
        == "f906f656a42ab60f51195a1a1b97a2dc8b61b5f4a2c00e0f25b5fb7c92eaec8c"
    )
    assert evidence[0] == (
        "CASH_AND_PRECIOUS_METALS",
        "OVERDUE",
        (1197, 538, 1209, 541),
    )
    derivative = [item for item in evidence if item[0] == "DERIVATIVE_ASSETS"]
    assert len(derivative) == 7
    assert {item[1] for item in derivative} == {axis.axis_key for axis in parsed.axes}
    used_value_indices = {
        index for row in parsed.rows for indices in row.value_line_indices for index in indices
    }
    assert 17 not in used_value_indices


def test_page60_dash_pixels_date_and_low_score_glyph_fail_closed(
    project_root: Path, tmp_path: Path
) -> None:
    fixture = project_root / _FIXTURE
    render = _render(project_root, tmp_path)
    policy = _policy(project_root)

    image = cv2.imread(str(render), cv2.IMREAD_COLOR)
    assert image is not None
    image[525:550, 1185:1225] = 255
    missing_dash = tmp_path / "page60-missing-dash.png"
    assert cv2.imwrite(str(missing_dash), image)
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    payload["source_render_sha256"] = sha256_file(missing_dash)
    mutated_fixture = tmp_path / "page60-missing-dash.json"
    mutated_fixture.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    missing_policy = replace(
        policy,
        source_render_sha256=sha256_file(missing_dash),
        source_ocr_sha256=sha256_file(mutated_fixture),
    )
    with pytest.raises(TMNoteWordBoxError, match="visible dash lacks constrained pixel evidence"):
        parse_tm_page60(mutated_fixture, missing_dash, missing_policy)

    date_payload = json.loads(fixture.read_text(encoding="utf-8"))
    date_payload["rec_texts"][0] = "Phân loại tài sản và công nợ ngày 30 tháng 03 năm 2026"
    date_fixture = tmp_path / "page60-date-drift.json"
    date_fixture.write_text(
        json.dumps(date_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(TMNoteWordBoxError, match="visible snapshot date drifted"):
        parse_tm_page60(
            date_fixture,
            render,
            replace(policy, source_ocr_sha256=sha256_file(date_fixture)),
        )

    score_payload = json.loads(fixture.read_text(encoding="utf-8"))
    score_payload["rec_scores"][17] = 0.81
    score_fixture = tmp_path / "page60-false-glyph-score-drift.json"
    score_fixture.write_text(
        json.dumps(score_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(TMNoteWordBoxError, match="rejected low-confidence line set drifted"):
        parse_tm_page60(
            score_fixture,
            render,
            replace(policy, source_ocr_sha256=sha256_file(score_fixture)),
        )

    with pytest.raises(TMNoteWordBoxError, match="native VND-million unit drifted"):
        parse_tm_page60(
            fixture,
            render,
            replace(policy, canonical_unit="USD", unit_multiplier=1),
        )

    assert {
        "dash_as_zero",
        "tiny_ocr_glyph_as_numeric_without_full_height_geometry",
        "accounting_equations_as_value_imputation",
        "page57_values_as_page60_mapping_or_imputation",
        "page61_values_as_page60_mapping_or_imputation",
    } <= set(policy.forbidden_semantic_inputs)
