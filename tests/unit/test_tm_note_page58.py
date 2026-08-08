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
from bctc_ai.tables.tm_note_page58 import load_tm_page58_policy, parse_tm_page58
from bctc_ai.tables.tm_note_word_box import TMNoteWordBoxError

_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0058-ppocrv6-word-box.json")
_FIXTURE_SHA256 = "76faf621905629fb1a4193844481af5cc36818f4729f7c5c2f89dd79098bbfb5"
_UPSTREAM_OCR_SHA256 = "7169e93279d86778e7ef9ad33badd04ed60991a8417e0d5a05972bf7115fc204"
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")


def _policy(project_root: Path):
    return load_tm_page58_policy(project_root / "config/tables/tm-note-page58-v1.yaml")


def _render(project_root: Path, tmp_path: Path) -> Path:
    return Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={58},
        )[0].path
    )


def _parsed(project_root: Path, tmp_path: Path):
    return parse_tm_page58(
        project_root / _FIXTURE,
        _render(project_root, tmp_path),
        _policy(project_root),
    )


def test_real_page58_reconstructs_exact_rows_slots_and_provenance(
    project_root: Path, tmp_path: Path
) -> None:
    fixture = project_root / _FIXTURE
    assert sha256_file(fixture) == _FIXTURE_SHA256
    assert fixture.stat().st_size < 7_000

    parsed = _parsed(project_root, tmp_path)

    assert parsed.source_sha256 == _FIXTURE_SHA256
    assert parsed.upstream_ocr_sha256 == _UPSTREAM_OCR_SHA256
    assert parsed.source_render_sha256 == (
        "bbcf019fd8b7c0a3ca461cf0ca7e1b77a617a062441d35d090e42ea5aa0348e2"
    )
    assert parsed.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert parsed.scope == "CONSOLIDATED"
    assert len(parsed.tables) == 1
    assert len(parsed.rows) == 20
    assert parsed.numeric_row_count == 18
    assert parsed.label_only_row_count == 2
    assert parsed.financial_slot_count == 72
    assert parsed.observation_count(ObservationKind.VALUE) == 63
    assert parsed.observation_count(ObservationKind.ZERO) == 0
    assert parsed.observation_count(ObservationKind.DASH) == 9
    assert parsed.structural_blank_count == 8
    assert parsed.unassigned_numeric_line_indices == ()
    assert parsed.excluded_artifact_line_indices == ()
    assert parsed.excluded_footer_numeric_line_indices == (99,)
    assert not parsed.mapping_authority
    assert not parsed.continues_to_page_59
    assert parsed.next_page_topic == "LIQUIDITY_RISK"


def test_page58_binds_four_visible_axes_to_one_snapshot_unit_scope(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)

    assert [axis.axis_key for axis in parsed.axes] == [
        "USD",
        "EUR",
        "OTHER_FOREIGN_CURRENCIES",
        "TOTAL",
    ]
    assert [axis.axis_right_edge for axis in parsed.axes] == [1855, 2278, 2759, 3236]
    assert {axis.period_role for axis in parsed.axes} == {"CURRENT"}
    assert {axis.period_type for axis in parsed.axes} == {"SNAPSHOT"}
    assert {axis.period_start for axis in parsed.axes} == {date(2026, 3, 31)}
    assert {axis.period_end for axis in parsed.axes} == {date(2026, 3, 31)}
    assert {(axis.canonical_unit, axis.unit_multiplier) for axis in parsed.axes} == {
        ("VND", 1_000_000)
    }


def test_page58_preserves_exact_eighteen_by_four_value_and_dash_matrix(
    project_root: Path, tmp_path: Path
) -> None:
    rows = [row for row in _parsed(project_root, tmp_path).rows if row.metric_key]

    assert [row.metric_key for row in rows] == [
        "CASH_AND_PRECIOUS_METALS",
        "SBV_DEPOSITS",
        "INTERBANK_ASSETS",
        "DERIVATIVE_ASSETS",
        "CUSTOMER_LOANS",
        "INVESTMENT_SECURITIES",
        "LONG_TERM_INVESTMENTS",
        "FIXED_ASSETS_AND_INVESTMENT_PROPERTY",
        "OTHER_ASSETS",
        "TOTAL_ASSETS",
        "INTERBANK_LIABILITIES",
        "CUSTOMER_DEPOSITS",
        "DERIVATIVE_LIABILITIES",
        "OTHER_LIABILITIES",
        "TOTAL_LIABILITIES",
        "ON_BALANCE_CURRENCY_POSITION",
        "OFF_BALANCE_CURRENCY_POSITION",
        "COMBINED_CURRENCY_POSITION",
    ]
    assert [[cell.value for cell in row.row.cells] for row in rows] == [
        [385_410, 36_806, 68_200, 490_416],
        [3_822_420, 968, 247_863, 4_071_251],
        [10_213_951, 333_874, 1_311_070, 11_858_895],
        [None, None, None, None],
        [58_186_719, 63_412, 1_213_230, 59_463_361],
        [None, None, 46_914, 46_914],
        [None, 2_731, None, 2_731],
        [347_892, None, 14_526, 362_418],
        [1_476_716, 188, 126_328, 1_603_232],
        [74_433_108, 437_979, 3_028_131, 77_899_218],
        [70_512_000, 86_370, 1_225_150, 71_823_520],
        [37_505_831, 6_499_492, 1_287_122, 45_292_445],
        [-34_673_329, -6_034_694, 133_877, -40_574_146],
        [1_138_155, 5_105, 128_837, 1_272_097],
        [74_482_657, 556_273, 2_774_986, 77_813_916],
        [-49_549, -118_294, 253_145, 85_302],
        [-1_059_075, 76_502, 125_263, -857_310],
        [-1_108_624, -41_792, 378_408, -772_008],
    ]
    structural = [row for row in _parsed(project_root, tmp_path).rows if not row.metric_key]
    assert [row.source_role for row in structural] == ["ASSET_SECTION", "LIABILITY_SECTION"]
    assert all(
        cell.observation is ObservationKind.BLANK for row in structural for cell in row.row.cells
    )


def test_page58_all_nine_dashes_are_pixel_backed(project_root: Path, tmp_path: Path) -> None:
    parsed = _parsed(project_root, tmp_path)
    evidence = [
        (row.metric_key, parsed.axes[index].axis_key, record.component_box)
        for row in parsed.rows
        for index, record in enumerate(row.visual_cell_evidence)
        if record is not None
    ]

    assert len(evidence) == 9
    assert (
        hashlib.sha256(json.dumps(evidence, separators=(",", ":")).encode("utf-8")).hexdigest()
        == "3eaedbf0114b8cb7e33bfe21975104228a4f44d82003b4487fed0a88eb5d2fa8"
    )
    assert evidence[0] == ("DERIVATIVE_ASSETS", "USD", (1822, 1165, 1835, 1170))
    assert evidence[-1] == (
        "FIXED_ASSETS_AND_INVESTMENT_PROPERTY",
        "EUR",
        (2252, 1353, 2264, 1358),
    )


def test_page58_dash_pixels_date_and_source_hash_fail_closed(
    project_root: Path, tmp_path: Path
) -> None:
    fixture = project_root / _FIXTURE
    render = _render(project_root, tmp_path)
    policy = _policy(project_root)

    image = cv2.imread(str(render), cv2.IMREAD_COLOR)
    assert image is not None
    image[1140:1180, 1800:1860] = 255
    missing_dash = tmp_path / "page58-missing-dash.png"
    assert cv2.imwrite(str(missing_dash), image)
    missing_dash_hash = sha256_file(missing_dash)
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    payload["source_render_sha256"] = missing_dash_hash
    mutated_fixture = tmp_path / "page58-missing-dash.json"
    mutated_fixture.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    with pytest.raises(TMNoteWordBoxError, match="visible dash lacks constrained pixel evidence"):
        parse_tm_page58(
            mutated_fixture,
            missing_dash,
            replace(
                policy,
                source_render_sha256=missing_dash_hash,
                source_ocr_sha256=sha256_file(mutated_fixture),
            ),
        )

    date_payload = json.loads(fixture.read_text(encoding="utf-8"))
    date_payload["rec_texts"][7] = date_payload["rec_texts"][7].replace("31 tháng", "30 tháng")
    date_fixture = tmp_path / "page58-date-drift.json"
    date_fixture.write_text(
        json.dumps(date_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    with pytest.raises(TMNoteWordBoxError, match="visible snapshot date drifted"):
        parse_tm_page58(
            date_fixture,
            render,
            replace(policy, source_ocr_sha256=sha256_file(date_fixture)),
        )

    with pytest.raises(TMNoteWordBoxError, match="compact OCR fixture hash drifted"):
        parse_tm_page58(fixture, render, replace(policy, source_ocr_sha256="0" * 64))
    assert {
        "dash_as_zero",
        "accounting_equations_as_value_imputation",
        "page57_values_as_page58_mapping_or_imputation",
    } <= set(policy.forbidden_semantic_inputs)
