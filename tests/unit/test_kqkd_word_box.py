from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from bctc_ai.core.contracts import BoundingBox, ObservationKind
from bctc_ai.tables.kqkd_word_box import (
    KQKDAxisGroup,
    KQKDWordBoxError,
    load_kqkd_word_box_policy,
    parse_kqkd_word_box_page,
)

_REAL_FIXTURE = Path("tests/golden/kqkd/mbb-q1-2026-page-0006-ppocrv6-word-box.json")


def _policy(project_root: Path):
    return load_kqkd_word_box_policy(project_root / "config/tables/kqkd-word-box-v1.yaml")


def _write_result(path: Path, lines: list[tuple[str, list[int]]]) -> Path:
    path.write_text(
        json.dumps(
            {
                "input_path": "synthetic-page.png",
                "rec_texts": [line[0] for line in lines],
                "rec_scores": [1.0 for _line in lines],
                "rec_boxes": [line[1] for line in lines],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def _hierarchical_fixture(*, scope: str = "HỢP NHẤT") -> list[tuple[str, list[int]]]:
    return [
        (f"BÁO CÁO KẾT QUẢ HOẠT ĐỘNG {scope}", [0, 0, 600, 20]),
        ("Quý II/2026", [0, 22, 120, 42]),
        ("Số phát sinh quý II", [400, 40, 600, 60]),
        ("Lũy kế từ đầu năm đến cuối quý", [800, 40, 1000, 60]),
        # Comparative deliberately precedes current on both physical groups.
        ("Năm trước", [330, 70, 390, 90]),
        ("Năm nay", [530, 70, 590, 90]),
        ("Năm trước", [730, 70, 790, 90]),
        ("Năm nay", [930, 70, 990, 90]),
        ("triệu đồng", [340, 100, 400, 120]),
        ("triệu đồng", [540, 100, 600, 120]),
        ("triệu đồng", [740, 100, 800, 120]),
        ("triệu đồng", [940, 100, 1000, 120]),
        ("Thu nhập lãi thuần", [0, 140, 250, 160]),
        # Deliberately equal: equality must not merge or type the four axes.
        ("100", [360, 140, 400, 160]),
        ("100", [560, 140, 600, 160]),
        ("100", [760, 140, 800, 160]),
        ("100", [960, 140, 1000, 160]),
    ]


def test_mbb_q1_2026_reconstructs_22_rows_and_all_88_numeric_cells(project_root: Path):
    parsed = parse_kqkd_word_box_page(
        project_root / _REAL_FIXTURE,
        _policy(project_root),
        page_tag="page-0006",
    )

    assert (
        parsed.source_sha256 == "2ca7b17dc07834c6a2cfbbe80681e4e58ad96c3c8b4096c7f8ea0417e29a8f44"
    )
    assert parsed.scope == "CONSOLIDATED"
    assert parsed.statement_title_line_index == 3
    assert parsed.report_period_line_index == 4
    assert len(parsed.axes) == 4
    assert len(parsed.rows) == 22
    assert parsed.assigned_numeric_line_count == 88
    assert parsed.observed_cell_count == 88
    assert parsed.unassigned_numeric_line_indices == ()
    assert parsed.orphan_label_line_indices == ()
    assert all(len(row.row.cells) == 4 for row in parsed.rows)
    assert all(row.observed_cell_count == 4 for row in parsed.rows)
    assert all(
        row.row.cells[0].value == row.row.cells[2].value
        and row.row.cells[1].value == row.row.cells[3].value
        for row in parsed.rows
    )


def test_mbb_visible_header_keeps_quarter_export_and_ytd_provenance_distinct(
    project_root: Path,
):
    parsed = parse_kqkd_word_box_page(
        project_root / _REAL_FIXTURE,
        _policy(project_root),
        page_tag="page-0006",
    )

    assert [axis.group for axis in parsed.axes] == [
        KQKDAxisGroup.QUARTER,
        KQKDAxisGroup.QUARTER,
        KQKDAxisGroup.YTD,
        KQKDAxisGroup.YTD,
    ]
    assert [axis.current_or_comparative for axis in parsed.axes] == [
        "CURRENT",
        "COMPARATIVE",
        "CURRENT",
        "COMPARATIVE",
    ]
    assert [axis.period_type for axis in parsed.axes] == [
        "DURATION",
        "DURATION",
        "YTD",
        "YTD",
    ]
    assert [axis.period_start for axis in parsed.axes] == [
        date(2026, 1, 1),
        date(2025, 1, 1),
        date(2026, 1, 1),
        date(2025, 1, 1),
    ]
    assert [axis.period_end for axis in parsed.axes] == [
        date(2026, 3, 31),
        date(2025, 3, 31),
        date(2026, 3, 31),
        date(2025, 3, 31),
    ]
    assert [axis.axis_id for axis in parsed.schema_export_axes] == ["value-1", "value-2"]
    assert [axis.axis_id for axis in parsed.provenance_only_axes] == ["value-3", "value-4"]
    assert all(axis.canonical_unit == "VND" for axis in parsed.axes)
    assert all(axis.unit_multiplier == 1_000_000 for axis in parsed.axes)


def test_mbb_wrap_is_one_logical_row_and_retains_exact_source_geometry(project_root: Path):
    parsed = parse_kqkd_word_box_page(
        project_root / _REAL_FIXTURE,
        _policy(project_root),
        page_tag="page-0006",
    )
    wrapped = parsed.rows[13]

    assert wrapped.label_line_indices == (90, 91)
    assert wrapped.label_bbox == BoundingBox(21, 1138, 1037, 1227)
    assert wrapped.row.label == ("Li nhun thun t hot đng kinh doanh trưc chi phí d phòng ri ro")
    assert wrapped.value_line_indices == ((92,), (93,), (94,), (95,))
    assert [cell.value for cell in wrapped.row.cells] == [
        13_083_204,
        11_372_739,
        13_083_204,
        11_372_739,
    ]
    assert parsed.source_ocr_bbox == BoundingBox(17, 89, 3128, 2332)
    assert parsed.table_bbox == BoundingBox(18, 479, 3128, 1652)
    assert parsed.rows[2].row.note_reference == "IV.1"
    assert parsed.rows[8].row.note_reference == "JV.4"
    assert all(
        cell.observation is not ObservationKind.INVALID
        for row in parsed.rows
        for cell in row.row.cells
    )


def test_roles_follow_visible_child_text_not_horizontal_order_or_equal_values(
    project_root: Path, tmp_path: Path
):
    result_path = _write_result(tmp_path / "ocr.json", _hierarchical_fixture())
    parsed = parse_kqkd_word_box_page(result_path, _policy(project_root), page_tag="page-0001")

    assert [axis.current_or_comparative for axis in parsed.axes] == [
        "COMPARATIVE",
        "CURRENT",
        "COMPARATIVE",
        "CURRENT",
    ]
    assert [axis.group for axis in parsed.axes] == [
        KQKDAxisGroup.QUARTER,
        KQKDAxisGroup.QUARTER,
        KQKDAxisGroup.YTD,
        KQKDAxisGroup.YTD,
    ]
    assert [axis.period_start for axis in parsed.axes] == [
        date(2025, 4, 1),
        date(2026, 4, 1),
        date(2025, 1, 1),
        date(2026, 1, 1),
    ]
    assert [axis.period_end for axis in parsed.axes] == [
        date(2025, 6, 30),
        date(2026, 6, 30),
        date(2025, 6, 30),
        date(2026, 6, 30),
    ]
    assert len({axis.axis_id for axis in parsed.axes}) == 4
    assert parsed.observed_cell_count == 4


def test_missing_scope_fails_closed_and_axis_overrun_is_never_hidden(
    project_root: Path, tmp_path: Path
):
    missing_scope = _write_result(
        tmp_path / "missing-scope.json",
        _hierarchical_fixture(scope=""),
    )
    with pytest.raises(KQKDWordBoxError, match="scope is unresolved"):
        parse_kqkd_word_box_page(missing_scope, _policy(project_root), page_tag="page-0001")

    shifted = _hierarchical_fixture()
    shifted[-1] = ("100", [1080, 140, 1120, 160])
    shifted_path = _write_result(tmp_path / "shifted.json", shifted)
    parsed = parse_kqkd_word_box_page(shifted_path, _policy(project_root), page_tag="page-0001")
    assert parsed.unassigned_numeric_line_indices == (16,)
    assert parsed.assigned_numeric_line_count == 3
    assert parsed.observed_cell_count == 3
    assert parsed.rows[0].row.cells[3].observation is ObservationKind.BLANK


def test_policy_forbids_schema_history_review_and_value_driven_header_semantics(
    project_root: Path,
):
    policy = _policy(project_root)

    assert set(policy.forbidden_header_inputs) == {
        "numeric_cell_text_or_value_as_period_feature",
        "numeric_value_equality_between_quarter_and_ytd",
        "numeric_value_magnitude",
        "template_labels_or_report_norm_ids",
        "historical_or_mongodb_values",
        "human_review_period_or_scope_answers",
        "horizontal_position_as_current_or_comparative_role",
    }
