from __future__ import annotations

from datetime import date
from pathlib import Path

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.tables.tm_note_page42 import load_tm_page42_policy, parse_tm_page42

_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0042-ppocrv6-word-box.json")
_FIXTURE_SHA256 = "ec221ba8132e21c04910c71d9955944c063a8c7153280bb1ec1782f8669b642f"
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")


def _policy(project_root: Path):
    return load_tm_page42_policy(project_root / "config/tables/tm-note-page42-v1.yaml")


def _render(project_root: Path, tmp_path: Path) -> Path:
    return Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={42},
        )[0].path
    )


def _parsed(project_root: Path, tmp_path: Path):
    return parse_tm_page42(
        project_root / _FIXTURE,
        _render(project_root, tmp_path),
        _policy(project_root),
    )


def test_real_page42_reconstructs_five_tables_and_exact_source_denominator(
    project_root: Path, tmp_path: Path
) -> None:
    fixture = project_root / _FIXTURE
    assert sha256_file(fixture) == _FIXTURE_SHA256

    parsed = _parsed(project_root, tmp_path)

    assert parsed.source_sha256 == _FIXTURE_SHA256
    assert parsed.source_render_sha256 == (
        "afb03eeaec7e0f96eee5c1cc02c44f31642e342c8a50f517a354cb617e45888a"
    )
    assert parsed.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert parsed.scope == "CONSOLIDATED"
    assert [table.table_key for table in parsed.tables] == [
        "RECEIVABLE_SUMMARY",
        "RECEIVABLE_DETAIL",
        "OTHER_ASSETS",
        "GOVERNMENT_DEBT",
        "INTERBANK_FUNDING",
    ]
    assert [len(table.rows) for table in parsed.tables] == [3, 6, 3, 2, 10]
    assert len(parsed.rows) == parsed.numeric_row_count == 24
    assert parsed.label_only_row_count == 0
    assert parsed.financial_slot_count == 48
    assert parsed.observation_count(ObservationKind.VALUE) == 48
    assert parsed.observation_count(ObservationKind.DASH) == 0
    assert parsed.unassigned_numeric_line_indices == ()
    assert parsed.excluded_footer_numeric_line_indices == (96,)
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


def test_receivable_and_other_asset_values_are_preserved_exactly(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    summary, detail, other = parsed.tables[:3]

    assert [[cell.value for cell in row.row.cells] for row in summary.rows] == [
        [583_366, 359_532],
        [19_581_449, 27_766_232],
        [20_164_815, 28_125_764],
    ]
    assert [[cell.value for cell in row.row.cells] for row in detail.rows] == [
        [1_295_059, 1_039_654],
        [839_371, 891_504],
        [861_287, 1_525_624],
        [11_281_653, 8_046_079],
        [5_304_079, 16_263_371],
        [19_581_449, 27_766_232],
    ]
    assert [[cell.value for cell in row.row.cells] for row in other.rows] == [
        [3_446_974, 3_478_007],
        [3_175_424, 4_416_084],
        [6_622_398, 7_894_091],
    ]


def test_government_and_interbank_values_are_preserved_exactly(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    government, interbank = parsed.tables[3:]

    assert [[cell.value for cell in row.row.cells] for row in government.rows] == [
        [28_346_499, 47_474_800],
        [28_346_499, 47_474_800],
    ]
    assert [[cell.value for cell in row.row.cells] for row in interbank.rows] == [
        [23_428_463, 4_446_570],
        [23_416_877, 4_396_618],
        [11_586, 49_952],
        [160_739_978, 179_188_755],
        [145_022_000, 164_580_000],
        [15_717_978, 14_608_755],
        [72_723_034, 64_382_164],
        [16_629_078, 14_074_208],
        [56_093_956, 50_307_956],
        [256_891_475, 248_017_489],
    ]


def test_page42_policy_forbids_semantic_mapping_and_equation_imputation(
    project_root: Path,
) -> None:
    assert set(_policy(project_root).forbidden_semantic_inputs) == {
        "template_labels_as_row_reconstruction_input",
        "approved_report_norm_id_assignment",
        "historical_or_mongodb_values",
        "human_review_answers",
        "accounting_equations_as_value_imputation",
    }
