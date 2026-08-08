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
from bctc_ai.tables.tm_note_page57 import load_tm_page57_policy, parse_tm_page57
from bctc_ai.tables.tm_note_word_box import TMNoteWordBoxError

_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0057-ppocrv6-word-box.json")
_FIXTURE_SHA256 = "54ba3de69d2ce284c4b12222aad7ddca0c096bee3698079675af528826496dfa"
_UPSTREAM_OCR_SHA256 = "133b3f223c0556d3039cde4b51a11c70b7fc90a7265a917758467db621f7ffa8"
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")


def _policy(project_root: Path):
    return load_tm_page57_policy(project_root / "config/tables/tm-note-page57-v1.yaml")


def _render(project_root: Path, tmp_path: Path) -> Path:
    return Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={57},
        )[0].path
    )


def _parsed(project_root: Path, tmp_path: Path):
    return parse_tm_page57(
        project_root / _FIXTURE,
        _render(project_root, tmp_path),
        _policy(project_root),
    )


def test_real_page57_reconstructs_exact_rows_slots_and_provenance(
    project_root: Path, tmp_path: Path
) -> None:
    fixture = project_root / _FIXTURE
    assert sha256_file(fixture) == _FIXTURE_SHA256
    assert fixture.stat().st_size < 9_000

    parsed = _parsed(project_root, tmp_path)

    assert parsed.source_sha256 == _FIXTURE_SHA256
    assert parsed.upstream_ocr_sha256 == _UPSTREAM_OCR_SHA256
    assert parsed.source_render_sha256 == (
        "48a2f2de934f982cae206f23b5c85176e794e9b06f9a03cb47531d8af9e7e26b"
    )
    assert parsed.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert parsed.scope == "CONSOLIDATED"
    assert len(parsed.tables) == 1
    assert len(parsed.rows) == 22
    assert parsed.numeric_row_count == 20
    assert parsed.label_only_row_count == 2
    assert parsed.financial_slot_count == 160
    assert parsed.observation_count(ObservationKind.VALUE) == 92
    assert parsed.observation_count(ObservationKind.ZERO) == 0
    assert parsed.observation_count(ObservationKind.DASH) == 68
    assert parsed.unassigned_numeric_line_indices == ()
    assert parsed.excluded_artifact_line_indices == (31, 32, 33, 98, 114)
    assert parsed.excluded_footer_numeric_line_indices == (137,)
    assert not parsed.mapping_authority
    assert not parsed.continues_to_page_58
    assert parsed.next_page_topic == "CURRENCY_RISK"


def test_page57_binds_eight_visible_axes_to_one_snapshot_unit_scope(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)

    assert [axis.axis_key for axis in parsed.axes] == [
        "OVERDUE",
        "NOT_REPRICED",
        "WITHIN_1M",
        "FROM_1_TO_3M",
        "FROM_3_TO_6M",
        "FROM_6_TO_12M",
        "OVER_1Y",
        "TOTAL",
    ]
    assert [axis.axis_right_edge for axis in parsed.axes] == [
        1265,
        1540,
        1804,
        2090,
        2368,
        2657,
        2954,
        3242,
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


def test_page57_preserves_exact_twenty_by_eight_value_and_dash_matrix(
    project_root: Path, tmp_path: Path
) -> None:
    rows = [row for row in _parsed(project_root, tmp_path).rows if row.metric_key]

    assert [[cell.value for cell in row.row.cells] for row in rows] == [
        [None, 5_741_287, None, None, None, None, None, 5_741_287],
        [None, 15_156_039, None, None, None, None, None, 15_156_039],
        [None, None, 140_423_657, 13_234_746, 4_672_838, 4_338_932, 2_638_574, 165_308_747],
        [None, 315_986, 4_777_446, None, None, None, None, 5_093_432],
        [None, None, None, None, None, None, None, None],
        [
            23_974_299,
            None,
            324_460_963,
            411_603_013,
            146_949_639,
            123_093_594,
            92_768_242,
            1_122_849_750,
        ],
        [1_630_386, None, 18_815_881, 30_571_152, 24_803_224, 76_991_257, 110_579_398, 263_391_298],
        [None, 559_134, None, None, None, None, None, 559_134],
        [None, 5_716_976, None, None, None, None, None, 5_716_976],
        [66_980, 42_840_063, None, None, None, None, None, 42_907_043],
        [
            25_671_665,
            70_329_485,
            488_477_947,
            455_408_911,
            176_425_701,
            204_423_783,
            205_986_214,
            1_626_723_706,
        ],
        [None, None, 25_669_608, 2_676_891, None, None, None, 28_346_499],
        [None, None, 160_704_304, 48_741_418, 23_491_162, 5_328_688, 18_625_903, 256_891_475],
        [None, None, 419_122_444, 158_070_968, 178_503_701, 136_569_221, 13_651_998, 905_918_332],
        [None, None, 100_278, 403_319, 103_966, -27_092, 80_855, 661_326],
        [None, None, 326_675, 1_365_173, 1_372_614, 179_000, 3_553, 3_247_015],
        [None, None, 3_150_000, 16_071_246, 24_872_825, 64_626_121, 100_096_261, 208_816_453],
        [None, 57_594_019, None, None, None, None, None, 57_594_019],
        [
            None,
            57_594_019,
            609_073_309,
            227_329_015,
            228_344_268,
            206_675_938,
            132_458_570,
            1_461_475_119,
        ],
        [
            25_671_665,
            12_735_466,
            -120_595_362,
            228_079_896,
            -51_918_567,
            -2_252_155,
            73_527_644,
            165_248_587,
        ],
    ]
    assert [row.metric_key for row in rows][0] == "CASH_AND_PRECIOUS_METALS"
    assert [row.metric_key for row in rows][-1] == "ON_BALANCE_INTEREST_SENSITIVITY_GAP"
    assert [
        row.source_role for row in _parsed(project_root, tmp_path).rows if not row.metric_key
    ] == [
        "ASSET_SECTION",
        "LIABILITY_SECTION",
    ]


def test_page57_all_sixty_eight_dashes_are_pixel_backed_and_tiny_glyphs_are_excluded(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    evidence = []
    for row in parsed.rows:
        for index, record in enumerate(row.visual_cell_evidence):
            if record is not None:
                evidence.append((row.metric_key, parsed.axes[index].axis_key, record.component_box))

    assert len(evidence) == 68
    assert (
        hashlib.sha256(json.dumps(evidence, separators=(",", ":")).encode("utf-8")).hexdigest()
        == "258c08cd15d9c0aa115798d6a65719516ba6523abaaa5ef9056301181a911f9a"
    )
    assert evidence[0] == (
        "CASH_AND_PRECIOUS_METALS",
        "OVERDUE",
        (1227, 574, 1239, 577),
    )
    derivative = [item for item in evidence if item[0] == "DERIVATIVE_ASSETS"]
    assert len(derivative) == 8
    assert {item[1] for item in derivative} == {axis.axis_key for axis in parsed.axes}
    used_value_indices = {
        index for row in parsed.rows for indices in row.value_line_indices for index in indices
    }
    assert not ({31, 32, 33, 98, 114} & used_value_indices)


def test_page57_dash_pixels_date_and_tiny_glyph_geometry_fail_closed(
    project_root: Path, tmp_path: Path
) -> None:
    fixture = project_root / _FIXTURE
    render = _render(project_root, tmp_path)
    policy = _policy(project_root)

    image = cv2.imread(str(render), cv2.IMREAD_COLOR)
    assert image is not None
    image[550:600, 1200:1270] = 255
    missing_dash = tmp_path / "page57-missing-dash.png"
    assert cv2.imwrite(str(missing_dash), image)
    missing_dash_hash = sha256_file(missing_dash)
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    payload["source_render_sha256"] = missing_dash_hash
    mutated_fixture = tmp_path / "page57-missing-dash.json"
    mutated_fixture.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    missing_policy = replace(
        policy,
        source_render_sha256=missing_dash_hash,
        source_ocr_sha256=sha256_file(mutated_fixture),
    )
    with pytest.raises(TMNoteWordBoxError, match="visible dash lacks constrained pixel evidence"):
        parse_tm_page57(mutated_fixture, missing_dash, missing_policy)

    date_payload = json.loads(fixture.read_text(encoding="utf-8"))
    date_payload["rec_texts"][0] = "Phân loại tài sản và công nợ ngày 30 tháng 03 năm 2026"
    date_fixture = tmp_path / "page57-date-drift.json"
    date_fixture.write_text(
        json.dumps(date_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(TMNoteWordBoxError, match="visible snapshot date drifted"):
        parse_tm_page57(
            date_fixture,
            render,
            replace(policy, source_ocr_sha256=sha256_file(date_fixture)),
        )

    with pytest.raises(TMNoteWordBoxError, match="tiny OCR artifact set drifted"):
        parse_tm_page57(
            fixture,
            render,
            replace(policy, tiny_glyph_max_height_line_heights=0.20),
        )

    assert {
        "dash_as_zero",
        "tiny_ocr_glyph_as_numeric_without_full_height_geometry",
        "accounting_equations_as_value_imputation",
        "page58_values_as_page57_mapping_or_imputation",
    } <= set(policy.forbidden_semantic_inputs)
