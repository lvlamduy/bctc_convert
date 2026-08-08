from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.tables.tm_note_word_box import (
    TMNoteRowKind,
    TMNoteWordBoxError,
    TMSchemaDisposition,
    load_tm_note_word_box_policy,
    parse_tm_note_word_box_page,
)

_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0030-ppocrv6-word-box.json")
_FIXTURE_SHA256 = "cbe621c45dbe909cf5e110f5a4a45b6ceba70950acea72866abec94d859d7429"
_SOURCE_OCR_SHA256 = "18dff9580e26ff236c41e087da75da8dc1787affd97d69faee6f1a742f270a30"
_SOURCE_RENDER_SHA256 = "e8cea48c6d8f93771b4b5bd9026df7a8b3e592ff7e403e036ed33eda913a092b"
_SOURCE_PDF_SHA256 = "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"


def _policy(project_root: Path):
    return load_tm_note_word_box_policy(project_root / "config/tables/tm-note-word-box-v1.yaml")


def _parse(project_root: Path):
    return parse_tm_note_word_box_page(
        project_root / _FIXTURE,
        _policy(project_root),
        page_tag="page-0030",
    )


def test_mbb_page_30_reconstructs_three_tables_and_exact_coverage(project_root: Path) -> None:
    fixture = project_root / _FIXTURE
    assert sha256_file(fixture) == _FIXTURE_SHA256

    parsed = _parse(project_root)

    assert parsed.source_sha256 == _FIXTURE_SHA256
    assert parsed.upstream_ocr_sha256 == _SOURCE_OCR_SHA256
    assert parsed.source_render_sha256 == _SOURCE_RENDER_SHA256
    assert parsed.source_pdf_sha256 == _SOURCE_PDF_SHA256
    assert parsed.scope == "CONSOLIDATED"
    assert parsed.section_title_line_indices == (0, 1)
    assert parsed.section_title == (
        "III THÔNG TIN BO SUNG CHO CÁC KHOÀN MUC TRINH BÀY TRONG BÁO CÁO "
        "TINH HINH TÀI CHÍNH HOP NHÁT"
    )
    assert len(parsed.tables) == 3
    assert len(parsed.rows) == 22
    assert parsed.numeric_row_count == 20
    assert parsed.label_only_row_count == 2
    assert parsed.numeric_cell_count == 40
    assert parsed.source_only_row_count == 2
    assert parsed.ambiguous_row_count == 1
    assert parsed.unassigned_numeric_line_indices == ()
    assert parsed.excluded_footer_numeric_line_indices == (80,)
    assert parsed.mapping_authority is False
    assert all(row.mapping_approved is False for row in parsed.rows)


def test_repeated_headers_bind_two_snapshot_axes_from_visible_dates(project_root: Path) -> None:
    parsed = _parse(project_root)

    for table in parsed.tables:
        assert len(table.axes) == 2
        assert [axis.current_or_comparative for axis in table.axes] == [
            "CURRENT",
            "COMPARATIVE",
        ]
        assert [axis.period_start for axis in table.axes] == [
            date(2026, 3, 31),
            date(2025, 12, 31),
        ]
        assert [axis.period_end for axis in table.axes] == [
            date(2026, 3, 31),
            date(2025, 12, 31),
        ]
        assert {axis.period_type for axis in table.axes} == {"SNAPSHOT"}
        assert {axis.canonical_unit for axis in table.axes} == {"VND"}
        assert {axis.unit_multiplier for axis in table.axes} == {1_000_000}


def test_root_source_only_label_only_and_ambiguous_rows_remain_distinct(
    project_root: Path,
) -> None:
    parsed = _parse(project_root)

    assert [table.root_candidate_report_norm_ids for table in parsed.tables] == [
        (561,),
        (569,),
        (575,),
    ]
    assert [[cell.value for cell in table.root_row.row.cells] for table in parsed.tables] == [
        [5_741_287, 4_965_786],
        [15_156_039, 68_494_426],
        [165_297_962, 182_923_726],
    ]
    assert all(
        table.root_row.schema_disposition is TMSchemaDisposition.ROOT_CANDIDATE
        for table in parsed.tables
    )

    source_only = tuple(
        row
        for row in parsed.rows
        if row.schema_disposition is TMSchemaDisposition.SOURCE_ONLY_CANDIDATE
    )
    assert [row.label_line_indices for row in source_only] == [(34,), (37,)]
    assert [[cell.value for cell in row.row.cells] for row in source_only] == [
        [797_376, 667_675],
        [1_426_377, 1_590_858],
    ]

    label_only = tuple(row for row in parsed.rows if row.row_kind is TMNoteRowKind.LABEL_ONLY)
    assert [row.label_line_indices for row in label_only] == [(52,), (59,)]
    assert all(
        cell.observation is ObservationKind.BLANK for row in label_only for cell in row.row.cells
    )

    ambiguous = tuple(
        row
        for row in parsed.rows
        if row.schema_disposition is TMSchemaDisposition.AMBIGUOUS_MAPPING_CANDIDATE
    )
    assert len(ambiguous) == 1
    assert ambiguous[0].label_line_indices == (77,)
    assert ambiguous[0].candidate_report_norm_ids == (583, 590)
    assert [cell.value for cell in ambiguous[0].row.cells] == [-10_785, -9_096]
    assert [cell.sign_evidence for cell in ambiguous[0].row.cells] == [
        "parentheses",
        "parentheses",
    ]


def test_current_comparative_roles_follow_dates_not_horizontal_order(
    project_root: Path, tmp_path: Path
) -> None:
    payload = json.loads((project_root / _FIXTURE).read_text(encoding="utf-8"))
    for left, right in ((4, 5), (21, 22), (44, 45)):
        payload["rec_texts"][left], payload["rec_texts"][right] = (
            payload["rec_texts"][right],
            payload["rec_texts"][left],
        )
    fixture = tmp_path / "reversed-dates.json"
    fixture.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    parsed = parse_tm_note_word_box_page(
        fixture,
        _policy(project_root),
        page_tag="page-0030",
    )

    for table in parsed.tables:
        assert [axis.current_or_comparative for axis in table.axes] == [
            "COMPARATIVE",
            "CURRENT",
        ]
        assert [axis.period_end for axis in table.axes] == [
            date(2025, 12, 31),
            date(2026, 3, 31),
        ]


def test_missing_local_unit_fails_closed_and_policy_forbids_mapping_authority(
    project_root: Path, tmp_path: Path
) -> None:
    payload = json.loads((project_root / _FIXTURE).read_text(encoding="utf-8"))
    payload["rec_texts"][6] = "unknown"
    fixture = tmp_path / "missing-unit.json"
    fixture.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(TMNoteWordBoxError, match="two dates and two local units"):
        parse_tm_note_word_box_page(
            fixture,
            _policy(project_root),
            page_tag="page-0030",
        )

    assert set(_policy(project_root).forbidden_semantic_inputs) == {
        "numeric_value_as_period_or_scope_feature",
        "horizontal_position_as_current_or_comparative_role",
        "template_labels_as_row_reconstruction_input",
        "approved_report_norm_id_assignment",
        "historical_or_mongodb_values",
        "human_review_answers",
        "accounting_equations_as_value_imputation",
    }
