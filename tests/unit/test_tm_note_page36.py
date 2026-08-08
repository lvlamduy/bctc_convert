from __future__ import annotations

from datetime import date
from pathlib import Path

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.tables.tm_note_page36 import load_tm_page36_policy, parse_tm_page36
from bctc_ai.tables.tm_note_word_box import TMNoteRowKind

_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0036-ppocrv6-word-box.json")
_FIXTURE_SHA256 = "9c1cd6f78104d4c8e0a478a070278cfed00561bac2f238e38845111fd0e052dd"
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")


def _policy(project_root: Path):
    return load_tm_page36_policy(project_root / "config/tables/tm-note-page36-v1.yaml")


def _render(project_root: Path, tmp_path: Path) -> Path:
    return Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={36},
        )[0].path
    )


def _parsed(project_root: Path, tmp_path: Path):
    return parse_tm_page36(
        project_root / _FIXTURE,
        _render(project_root, tmp_path),
        _policy(project_root),
    )


def test_real_page36_reconstructs_three_tables_and_exact_source_denominator(
    project_root: Path, tmp_path: Path
) -> None:
    fixture = project_root / _FIXTURE
    assert sha256_file(fixture) == _FIXTURE_SHA256

    parsed = _parsed(project_root, tmp_path)

    assert parsed.source_sha256 == _FIXTURE_SHA256
    assert parsed.source_render_sha256 == (
        "4e924e4e964ab4e60d486e3e1654cda8f2818c2fb451bdb627697b28a484002c"
    )
    assert parsed.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert parsed.scope == "CONSOLIDATED"
    assert [table.table_key for table in parsed.tables] == [
        "HTM_SECURITIES",
        "LONG_TERM_NET",
        "LONG_TERM_DETAIL",
    ]
    assert [len(table.rows) for table in parsed.tables] == [7, 4, 3]
    assert len(parsed.rows) == 14
    assert parsed.numeric_row_count == 13
    assert parsed.label_only_row_count == 1
    assert parsed.financial_slot_count == 26
    assert parsed.observation_count(ObservationKind.VALUE) == 26
    assert parsed.observation_count(ObservationKind.DASH) == 0
    assert parsed.unassigned_numeric_line_indices == ()
    assert parsed.excluded_footer_numeric_line_indices == (66,)
    assert parsed.mapping_authority is False


def test_all_local_headers_bind_snapshot_period_unit_and_scope(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)

    for table in parsed.tables:
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


def test_wrapped_structural_heading_and_numeric_net_remain_distinct(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    htm = parsed.tables[0]

    assert htm.rows[0].row_kind is TMNoteRowKind.LABEL_ONLY
    assert htm.rows[0].label_line_indices == (7, 8)
    assert htm.rows[0].row.label == "Chúng khoán đu tư gi đén ngày đáo hąn"
    assert all(cell.observation is ObservationKind.BLANK for cell in htm.rows[0].row.cells)
    assert htm.rows[-1].row.label == ""
    assert [cell.value for cell in htm.rows[-1].row.cells] == [4_273_769, 4_225_737]


def test_visible_values_and_provisions_are_preserved_exactly(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    htm, net, detail = parsed.tables

    assert [[cell.value for cell in row.row.cells] for row in htm.rows[1:]] == [
        [268_962, 269_099],
        [2_419_898, 2_395_896],
        [1_647_699, 1_630_130],
        [4_336_559, 4_295_125],
        [-62_790, -69_388],
        [4_273_769, 4_225_737],
    ]
    assert [[cell.value for cell in row.row.cells] for row in net.rows] == [
        [559_134, 559_624],
        [559_134, 559_624],
        [-91_228, -91_228],
        [467_906, 468_396],
    ]
    assert [[cell.value for cell in row.row.cells] for row in detail.rows] == [
        [492_584, 493_184],
        [66_550, 66_440],
        [559_134, 559_624],
    ]


def test_page36_policy_forbids_semantic_mapping_and_equation_imputation(
    project_root: Path,
) -> None:
    assert set(_policy(project_root).forbidden_semantic_inputs) == {
        "template_labels_as_row_reconstruction_input",
        "approved_report_norm_id_assignment",
        "historical_or_mongodb_values",
        "human_review_answers",
        "accounting_equations_as_value_imputation",
    }
