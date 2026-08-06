from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date

import pytest

from bctc_ai.axes.word_box_header_binding import (
    WordBoxHeaderBindingError,
    bind_word_box_visible_headers,
    load_word_box_header_binding_policy,
)
from bctc_ai.evaluation.word_box_rows import GeometryAxis


@dataclass(frozen=True)
class _Geometry:
    axes: tuple[GeometryAxis, ...]
    line_height: float = 40.0


def _policy(project_root):
    return load_word_box_header_binding_policy(
        project_root / "config/tables/word-box-header-binding-v1.yaml"
    )


def _write_result(tmp_path, lines):
    path = tmp_path / "ocr_result.json"
    path.write_text(
        json.dumps(
            {
                "rec_texts": [line[0] for line in lines],
                "rec_scores": [1.0 for _line in lines],
                "rec_boxes": [line[1] for line in lines],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def test_binds_staggered_visible_dates_and_fuzzy_units_without_horizontal_roles(
    project_root, tmp_path
):
    path = _write_result(
        tmp_path,
        [
            ("31/12/2025", [500, 80, 600, 120]),
            ("31/03/2026", [300, 120, 400, 160]),
            ("triu đồng", [305, 165, 400, 200]),
            ("triu đồng", [505, 165, 600, 200]),
            ("9.999.999", [300, 300, 400, 340]),
            ("1", [550, 300, 600, 340]),
        ],
    )
    geometry = _Geometry(
        axes=(
            GeometryAxis("left", "31/03/2026", 400, 1),
            GeometryAxis("right", "31/12/2025", 600, 0),
        )
    )

    result = bind_word_box_visible_headers(
        path, geometry, _policy(project_root), statement_type="CDKT"
    )

    assert [axis.period_end for axis in result.axes] == [
        date(2026, 3, 31),
        date(2025, 12, 31),
    ]
    assert [axis.current_or_comparative for axis in result.axes] == [
        "CURRENT",
        "COMPARATIVE",
    ]
    assert [axis.raw_unit_text for axis in result.axes] == ["triu đồng", "triu đồng"]
    assert [axis.canonical_unit for axis in result.axes] == ["VND", "VND"]
    assert [axis.unit_multiplier for axis in result.axes] == [1_000_000, 1_000_000]
    assert all(axis.unit_similarity >= 0.86 for axis in result.axes)
    assert "9.999.999" not in " ".join(
        evidence for axis in result.axes for evidence in axis.evidence
    )


def test_roles_follow_dates_even_when_comparative_is_left(project_root, tmp_path):
    path = _write_result(
        tmp_path,
        [
            ("31/12/2025", [300, 100, 400, 140]),
            ("31/03/2026", [500, 100, 600, 140]),
            ("triệu đồng", [305, 150, 400, 185]),
            ("triệu đồng", [505, 150, 600, 185]),
        ],
    )
    geometry = _Geometry(
        axes=(
            GeometryAxis("left", "31/12/2025", 400, 0),
            GeometryAxis("right", "31/03/2026", 600, 1),
        )
    )

    result = bind_word_box_visible_headers(
        path, geometry, _policy(project_root), statement_type="CDKT"
    )

    assert [axis.current_or_comparative for axis in result.axes] == [
        "COMPARATIVE",
        "CURRENT",
    ]
    assert [binding.current_or_comparative for binding in result.header_bindings] == [
        "COMPARATIVE",
        "CURRENT",
    ]


def test_missing_unit_fails_closed(project_root, tmp_path):
    path = _write_result(
        tmp_path,
        [
            ("31/03/2026", [300, 100, 400, 140]),
            ("31/12/2025", [500, 100, 600, 140]),
            ("đã kiểm toán", [500, 150, 600, 185]),
        ],
    )
    geometry = _Geometry(
        axes=(
            GeometryAxis("left", "31/03/2026", 400, 0),
            GeometryAxis("right", "31/12/2025", 600, 1),
        )
    )

    with pytest.raises(WordBoxHeaderBindingError, match="no bounded visible unit"):
        bind_word_box_visible_headers(path, geometry, _policy(project_root), statement_type="CDKT")


def test_duplicate_dates_and_unsupported_duration_statement_fail_closed(project_root, tmp_path):
    path = _write_result(
        tmp_path,
        [
            ("31/03/2026", [300, 100, 400, 140]),
            ("31/03/2026", [500, 100, 600, 140]),
            ("triệu đồng", [305, 150, 400, 185]),
            ("triệu đồng", [505, 150, 600, 185]),
        ],
    )
    geometry = _Geometry(
        axes=(
            GeometryAxis("left", "31/03/2026", 400, 0),
            GeometryAxis("right", "31/03/2026", 600, 1),
        )
    )

    with pytest.raises(WordBoxHeaderBindingError, match="unique required roles"):
        bind_word_box_visible_headers(path, geometry, _policy(project_root), statement_type="CDKT")
    with pytest.raises(WordBoxHeaderBindingError, match="no explicit v1 period semantics"):
        bind_word_box_visible_headers(path, geometry, _policy(project_root), statement_type="KQKD")


def test_policy_forbids_values_history_schema_review_and_x_order(project_root):
    policy = _policy(project_root)

    assert set(policy.forbidden_inputs) == {
        "numeric_cell_text_or_value_as_period_unit_feature",
        "numeric_value_magnitude",
        "historical_or_mongodb_values",
        "template_labels_or_report_norm_ids",
        "human_review_period_answers",
        "horizontal_position_as_period_role",
    }
