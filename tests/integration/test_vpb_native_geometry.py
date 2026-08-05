from __future__ import annotations

import json
from datetime import date

import pytest

from bctc_ai.axes.header_binding import bind_value_headers
from bctc_ai.core.contracts import RowType
from bctc_ai.core.hashing import sha256_file
from bctc_ai.ocr.pdf_text import extract_pdf_text
from bctc_ai.rows.pdf_statement import reconstruct_statement_rows
from bctc_ai.tables.geometry import ColumnRole, analyze_page_geometry, load_geometry_config


def _period_record(binding) -> list[str | int | None]:
    return [
        binding.period_type,
        binding.duration_months,
        binding.period_start.isoformat() if isinstance(binding.period_start, date) else None,
        binding.period_end.isoformat() if isinstance(binding.period_end, date) else None,
        binding.current_or_comparative,
        binding.unit_multiplier,
    ]


def test_registered_vpb_native_geometry_fixture(project_root):
    expected_path = project_root / "docs/experiments/E-0006-vpb-native-geometry.json"
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    pdf_path = project_root / expected["source_path"]
    if not pdf_path.is_file():
        pytest.skip("external registered PDF fixture is not present")

    assert sha256_file(pdf_path) == expected["source_sha256"]
    config_path = project_root / expected["config_path"]
    assert sha256_file(config_path) == expected["config_sha256"]
    for relative_path, digest in expected["algorithm_files_sha256"].items():
        assert sha256_file(project_root / relative_path) == digest

    config = load_geometry_config(config_path)
    page_numbers = {int(page) for page in expected["pages"]}
    observed_aggregate = {
        "pages": 0,
        "logical_rows": 0,
        "value_cells": 0,
        "note_references": 0,
        "numeric_rows_without_visible_label": 0,
    }
    for page in extract_pdf_text(pdf_path, page_numbers):
        page_expected = expected["pages"][str(page.page)]
        geometry = analyze_page_geometry(page, config)
        rows = reconstruct_statement_rows(geometry, config)
        bindings = bind_value_headers(geometry, config)
        labels = {row.label for row in rows}
        multiline_labels = {row.label for row in rows if len(row.label_boxes) > 1}
        sections = [row.label for row in rows if row.row_type is RowType.SECTION_HEADER]
        numeric_without_label = sum(bool(row.cells) and not row.label for row in rows)
        value_axes = [axis for axis in geometry.axes if axis.role is ColumnRole.VALUE]

        assert len(value_axes) == expected["aggregate"]["value_axes_per_page"]
        assert len(rows) == page_expected["row_count"]
        assert sum(len(row.cells) for row in rows) == page_expected["value_cell_count"]
        assert (
            sum(row.note_reference is not None for row in rows)
            == page_expected["note_reference_count"]
        )
        assert sum(len(row.label_boxes) > 1 for row in rows) == page_expected["multiline_row_count"]
        assert numeric_without_label == page_expected["numeric_without_label_count"]
        assert sections == page_expected["section_labels"]
        assert [_period_record(binding) for binding in bindings] == page_expected["periods"]
        assert set(page_expected.get("required_labels", ())) <= labels
        assert set(page_expected.get("required_multiline_labels", ())) <= multiline_labels

        observed_aggregate["pages"] += 1
        observed_aggregate["logical_rows"] += len(rows)
        observed_aggregate["value_cells"] += sum(len(row.cells) for row in rows)
        observed_aggregate["note_references"] += sum(row.note_reference is not None for row in rows)
        observed_aggregate["numeric_rows_without_visible_label"] += numeric_without_label

    for metric, value in observed_aggregate.items():
        assert value == expected["aggregate"][metric]
