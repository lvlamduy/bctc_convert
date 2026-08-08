from __future__ import annotations

import json
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.tables.tm_note_page61 import load_tm_page61_policy, parse_tm_page61
from bctc_ai.tables.tm_note_word_box import TMNoteWordBoxError

_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0061-ppocrv6-word-box.json")
_FIXTURE_SHA256 = "4cc47afa46962ffef7ee45d0be9d45f59f18a41c63ab72966e362b3a1f262636"
_UPSTREAM_OCR_SHA256 = "20a1e92685aaef93ae0dd34ee06cc1347f0af29ddc66df9d10cd604099574cc9"
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")


def _policy(project_root: Path):
    return load_tm_page61_policy(project_root / "config/tables/tm-note-page61-v1.yaml")


def _render(project_root: Path, tmp_path: Path) -> Path:
    return Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={61},
        )[0].path
    )


def _parsed(project_root: Path, tmp_path: Path):
    return parse_tm_page61(
        project_root / _FIXTURE,
        _render(project_root, tmp_path),
        _policy(project_root),
    )


def test_real_page61_reconstructs_exact_rates_and_provenance(
    project_root: Path, tmp_path: Path
) -> None:
    fixture = project_root / _FIXTURE
    assert sha256_file(fixture) == _FIXTURE_SHA256
    assert fixture.stat().st_size < 4_000

    parsed = _parsed(project_root, tmp_path)

    assert parsed.source_sha256 == _FIXTURE_SHA256
    assert parsed.upstream_ocr_sha256 == _UPSTREAM_OCR_SHA256
    assert parsed.source_render_sha256 == (
        "35163ef52851f7026891b450b7deaac1d6dbf7e0a16a26d0cd03a708d8366117"
    )
    assert parsed.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert parsed.scope == "CONSOLIDATED"
    assert len(parsed.tables) == 1
    assert parsed.numeric_row_count == 10
    assert parsed.financial_slot_count == 20
    assert parsed.observation_count(ObservationKind.VALUE) == 20
    assert parsed.observation_count(ObservationKind.ZERO) == 0
    assert parsed.observation_count(ObservationKind.DASH) == 0
    assert parsed.observation_count(ObservationKind.BLANK) == 0
    assert parsed.unassigned_numeric_line_indices == ()
    assert parsed.excluded_low_confidence_line_indices == (52,)
    assert parsed.excluded_post_table_numeric_line_indices == (40,)
    assert parsed.excluded_footer_numeric_line_indices == (53,)
    assert not parsed.mapping_authority
    assert not parsed.continues_after_page_61


def test_page61_binds_two_visible_snapshot_axes_to_native_vnd_per_currency_unit(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)

    assert [period.period_role for period in parsed.periods] == ["CURRENT", "PRIOR"]
    assert [period.visible_date for period in parsed.periods] == [
        date(2026, 3, 31),
        date(2025, 12, 31),
    ]
    assert [period.axis_right_edge for period in parsed.periods] == [1431, 1979]
    assert {period.period_type for period in parsed.periods} == {"SNAPSHOT"}
    assert {period.canonical_unit for period in parsed.periods} == {"VND"}
    assert {period.unit_multiplier for period in parsed.periods} == {1}
    assert {period.unit_denominator for period in parsed.periods} == {"ONE_UNIT_OF_ROW_CURRENCY"}
    assert all(
        row.cell_unit_denominators == ("ONE_UNIT_OF_ROW_CURRENCY", "ONE_UNIT_OF_ROW_CURRENCY")
        for row in parsed.rows
    )


def test_page61_preserves_currency_order_raw_decimal_commas_and_exact_values(
    project_root: Path, tmp_path: Path
) -> None:
    rows = _parsed(project_root, tmp_path).rows

    assert [row.currency_code for row in rows] == [
        "USD",
        "EUR",
        "GBP",
        "JPY",
        "CHF",
        "AUD",
        "CAD",
        "SGD",
        "THB",
        "SEK",
    ]
    assert [[cell.raw_text for cell in row.row.cells] for row in rows] == [
        ["26.335,00", "26.290,00"],
        ["30.358,00", "30.945,00"],
        ["34.837,50", "35.443,00"],
        ["165,68", "168,88"],
        ["32.920,50", "33.195,00"],
        ["18.125,50", "17.641,00"],
        ["18.979,50", "19.250,50"],
        ["20.413,50", "20.505,50"],
        ["808,12", "841,86"],
        ["2.768,95", "2.879,53"],
    ]
    assert [[cell.value for cell in row.row.cells] for row in rows] == [
        [Decimal("26335.00"), Decimal("26290.00")],
        [Decimal("30358.00"), Decimal("30945.00")],
        [Decimal("34837.50"), Decimal("35443.00")],
        [Decimal("165.68"), Decimal("168.88")],
        [Decimal("32920.50"), Decimal("33195.00")],
        [Decimal("18125.50"), Decimal("17641.00")],
        [Decimal("18979.50"), Decimal("19250.50")],
        [Decimal("20413.50"), Decimal("20505.50")],
        [Decimal("808.12"), Decimal("841.86")],
        [Decimal("2768.95"), Decimal("2879.53")],
    ]


def test_page61_period_unit_decimal_and_non_table_drift_fail_closed(
    project_root: Path, tmp_path: Path
) -> None:
    fixture = project_root / _FIXTURE
    render = _render(project_root, tmp_path)
    policy = _policy(project_root)

    date_payload = json.loads(fixture.read_text(encoding="utf-8"))
    date_payload["rec_texts"][1] = "30/03/2026"
    date_fixture = tmp_path / "page61-date-drift.json"
    date_fixture.write_text(
        json.dumps(date_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(TMNoteWordBoxError, match="visible period/unit geometry drifted"):
        parse_tm_page61(
            date_fixture,
            render,
            replace(policy, source_ocr_sha256=sha256_file(date_fixture)),
        )

    unit_payload = json.loads(fixture.read_text(encoding="utf-8"))
    unit_payload["rec_texts"][3] = "Triệu đồng"
    unit_fixture = tmp_path / "page61-unit-drift.json"
    unit_fixture.write_text(
        json.dumps(unit_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(TMNoteWordBoxError, match="visible period/unit geometry drifted"):
        parse_tm_page61(
            unit_fixture,
            render,
            replace(policy, source_ocr_sha256=sha256_file(unit_fixture)),
        )

    decimal_payload = json.loads(fixture.read_text(encoding="utf-8"))
    decimal_payload["rec_texts"][6] = "26.335"
    decimal_fixture = tmp_path / "page61-decimal-drift.json"
    decimal_fixture.write_text(
        json.dumps(decimal_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(TMNoteWordBoxError, match="decimal-comma precision drifted"):
        parse_tm_page61(
            decimal_fixture,
            render,
            replace(policy, source_ocr_sha256=sha256_file(decimal_fixture)),
        )

    score_payload = json.loads(fixture.read_text(encoding="utf-8"))
    score_payload["rec_scores"][52] = 0.81
    score_fixture = tmp_path / "page61-stamp-score-drift.json"
    score_fixture.write_text(
        json.dumps(score_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(TMNoteWordBoxError, match="rejected low-confidence line set drifted"):
        parse_tm_page61(
            score_fixture,
            render,
            replace(policy, source_ocr_sha256=sha256_file(score_fixture)),
        )

    assert {
        "vnd_million_multiplier",
        "decimal_comma_loss_or_integer_rounding",
        "period_axis_swapping",
        "page60_values_as_page61_mapping_or_imputation",
        "signatures_stamps_or_approval_text_as_financial_rows",
    } <= set(policy.forbidden_semantic_inputs)
