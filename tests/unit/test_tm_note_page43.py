from __future__ import annotations

from datetime import date
from pathlib import Path

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.tables.tm_note_page43 import load_tm_page43_policy, parse_tm_page43
from bctc_ai.tables.tm_note_word_box import TMNoteRowKind

_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0043-ppocrv6-word-box.json")
_FIXTURE_SHA256 = "fba2b7270727d806170dc503f840071297a1ee2eceeb1ab5039c494379d72e10"
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")


def _policy(project_root: Path):
    return load_tm_page43_policy(project_root / "config/tables/tm-note-page43-v1.yaml")


def _render(project_root: Path, tmp_path: Path) -> Path:
    return Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={43},
        )[0].path
    )


def _parsed(project_root: Path, tmp_path: Path):
    return parse_tm_page43(
        project_root / _FIXTURE,
        _render(project_root, tmp_path),
        _policy(project_root),
    )


def test_real_page43_reconstructs_exact_multi_axis_source_denominator(
    project_root: Path, tmp_path: Path
) -> None:
    fixture = project_root / _FIXTURE
    assert sha256_file(fixture) == _FIXTURE_SHA256

    parsed = _parsed(project_root, tmp_path)

    assert parsed.source_sha256 == _FIXTURE_SHA256
    assert parsed.source_render_sha256 == (
        "11f7a3d8011a2026ddb2e859aa11cabedb6ed9d90fc5b971affc8f39922256f4"
    )
    assert parsed.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert parsed.scope == "CONSOLIDATED"
    assert [table.table_key for table in parsed.tables] == [
        "DEPOSIT_TYPE",
        "DEPOSIT_CUSTOMER",
        "DERIVATIVES",
        "TRUST_FUNDING",
    ]
    assert [len(table.rows) for table in parsed.tables] == [13, 4, 9, 3]
    assert len(parsed.rows) == 29
    assert parsed.numeric_row_count == 22
    assert parsed.label_only_row_count == 7
    assert parsed.financial_slot_count == 50
    assert parsed.observation_count(ObservationKind.VALUE) == 44
    assert parsed.observation_count(ObservationKind.DASH) == 6
    assert parsed.unassigned_numeric_line_indices == ()
    assert parsed.excluded_footer_numeric_line_indices == (92,)
    assert parsed.mapping_authority is False


def test_all_visible_period_unit_scope_and_derivative_measure_axes_bind_locally(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)

    for table_key in ("DEPOSIT_TYPE", "DEPOSIT_CUSTOMER", "TRUST_FUNDING"):
        table = next(item for item in parsed.tables if item.table_key == table_key)
        assert [axis.current_or_comparative for axis in table.axes] == [
            "CURRENT",
            "COMPARATIVE",
        ]
        assert [axis.period_end for axis in table.axes] == [
            date(2026, 3, 31),
            date(2025, 12, 31),
        ]
        assert {axis.period_type for axis in table.axes} == {"SNAPSHOT"}
        assert {axis.canonical_unit for axis in table.axes} == {"VND"}
        assert {axis.unit_multiplier for axis in table.axes} == {1_000_000}

    derivative = next(item for item in parsed.tables if item.table_key == "DERIVATIVES")
    assert [axis.measure_role for axis in derivative.axes] == [
        "ASSET_CARRYING",
        "LIABILITY_CARRYING",
        "NET_CARRYING",
    ]
    assert all(axis.period_end is None for axis in derivative.axes)
    assert derivative.rows[2].cell_period_ends == (date(2026, 3, 31),) * 3
    assert derivative.rows[6].cell_period_ends == (date(2025, 12, 31),) * 3
    assert derivative.rows[2].cell_period_roles == ("CURRENT",) * 3
    assert derivative.rows[6].cell_period_roles == ("COMPARATIVE",) * 3


def test_deposit_and_trust_values_are_preserved_exactly(project_root: Path, tmp_path: Path) -> None:
    parsed = _parsed(project_root, tmp_path)
    deposit, customer, _derivative, trust = parsed.tables

    assert [[cell.value for cell in row.row.cells] for row in deposit.rows[2:]] == [
        [292_374_334, 339_352_789],
        [259_402_211, 304_453_535],
        [32_972_123, 34_899_254],
        [605_909_873, 573_482_507],
        [596_712_663, 563_989_870],
        [9_197_210, 9_492_637],
        [1_189_296, 1_226_310],
        [6_444_829, 7_306_526],
        [4_151_100, 4_544_143],
        [2_293_729, 2_762_383],
        [905_918_332, 921_368_132],
    ]
    assert [[cell.value for cell in row.row.cells] for row in customer.rows[1:]] == [
        [365_071_880, 402_397_512],
        [540_846_452, 518_970_620],
        [905_918_332, 921_368_132],
    ]
    assert [[cell.value for cell in row.row.cells] for row in trust.rows[1:]] == [
        [3_247_015, 3_912_833],
        [3_247_015, 3_912_833],
    ]


def test_derivative_dashes_and_negative_values_preserve_pixel_provenance(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    derivative = next(item for item in parsed.tables if item.table_key == "DERIVATIVES")
    numeric = [row for row in derivative.rows if row.row_kind is TMNoteRowKind.NUMERIC]

    assert [[cell.value for cell in row.row.cells] for row in numeric] == [
        [None, -661_326, -661_326],
        [None, -150_745, -150_745],
        [None, -510_581, -510_581],
        [None, -698_507, -698_507],
        [None, -19_293, -19_293],
        [None, -679_214, -679_214],
    ]
    for row in numeric:
        assert row.row.cells[0].observation is ObservationKind.DASH
        assert row.row.cells[0].value is None
        assert row.visual_cell_evidence[0] is not None
        assert row.visual_cell_evidence[0].observation == "DASH"
        assert row.visual_cell_evidence[1:] == (None, None)


def test_page43_policy_forbids_semantic_mapping_history_review_and_dash_coercion(
    project_root: Path,
) -> None:
    assert set(_policy(project_root).forbidden_semantic_inputs) == {
        "missing_ocr_cell_as_dash_without_pixel_evidence",
        "template_labels_as_row_reconstruction_input",
        "approved_report_norm_id_assignment",
        "historical_or_mongodb_values",
        "human_review_answers",
        "dash_as_zero",
        "accounting_equations_as_value_imputation",
    }
