from __future__ import annotations

import copy

import pytest

from bctc_ai.evaluation.accounting_additive_table_closure_v1 import (
    AccountingAdditiveTableClosureV1Error,
    build_accounting_additive_table_closure_v1,
    validate_accounting_additive_table_closure_replay_v1,
)
from bctc_ai.evaluation.accounting_family_row_axis_v1 import (
    build_accounting_family_row_axis_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _spec() -> dict[str, object]:
    return {
        "children": [
            {
                "aliases": ["Nợ ngắn hạn"],
                "presence": "REQUIRED",
                "role": "SHORT_TERM",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "aliases": ["Nợ trung hạn"],
                "presence": "REQUIRED",
                "role": "MEDIUM_TERM",
                "role_kind": "ADDITIVE_CHILD",
            },
        ],
        "family_id": "LOAN_MATURITY",
        "format_version": "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V1",
        "hard_negative_aliases": ["Phân tích chất lượng nợ"],
        "limits": {
            "max_cluster_span_lines": 30,
            "max_continuation_pages": 1,
            "max_label_line_span": 2,
        },
        "parent": {
            "aliases": ["Phân tích dư nợ theo thời gian"],
            "resolution_mode": "EXPLICIT_ONLY",
            "role": "LOAN_MATURITY",
        },
        "structural_reset_aliases": ["Phân tích cho vay theo ngành"],
    }


def _line(ordinal: int, text: str, numeric: str, bbox: list[int]) -> dict[str, object]:
    sample = ordinal + 1
    return {
        "bbox": bbox,
        "crop_ref": {
            "path": f"opaque/crop-{sample:04d}.png",
            "sha256": f"{sample:064x}",
            "size_bytes": 100 + sample,
        },
        "line_ordinal": ordinal,
        "numeric_recognition": {"raw_prediction": numeric, "reader_score": 0.95},
        "sample_id": f"sample-{sample:09d}",
        "vietocr_text": text,
    }


def _pages(*, total_rows: list[tuple[str, str]] | None = None) -> list[dict[str, object]]:
    if total_rows is None:
        total_rows = [("300", "270")]
    lines = [
        _line(0, "Phân tích dư nợ theo thời gian", "", [30, 20, 430, 42]),
        _line(1, "Nợ ngắn hạn", "", [50, 100, 300, 122]),
        _line(2, "100", "100", [600, 100, 700, 122]),
        _line(3, "90", "90", [800, 100, 900, 122]),
        _line(4, "Nợ trung hạn", "", [50, 150, 300, 172]),
        _line(5, "200", "200", [600, 150, 700, 172]),
        _line(6, "180", "180", [800, 150, 900, 172]),
    ]
    for row, values in enumerate(total_rows):
        ordinal = 7 + row * 2
        top = 200 + row * 50
        lines.extend(
            [
                _line(ordinal, values[0], values[0], [600, top, 700, top + 22]),
                _line(ordinal + 1, values[1], values[1], [800, top, 900, top + 22]),
            ]
        )
    return [{"lines": lines, "page_sequence": 1, "page_width": 1000}]


def _axis(pages: list[dict[str, object]]) -> dict[str, object]:
    return build_accounting_family_row_axis_v1(pages, _spec())


def test_exact_unique_visible_total_corroborates_without_numeric_authority() -> None:
    pages = _pages()
    result = build_accounting_additive_table_closure_v1(_axis(pages), pages, _spec())

    assert result["status"] == "CORROBORATED_EXACT_UNIQUE_TRAILING_TOTAL"
    assert result["additive_roles"] == ["SHORT_TERM", "MEDIUM_TERM"]
    assert [item["sum_value"]["coefficient"] for item in result["lane_sums"]] == [300, 270]
    assert result["metrics"] == {
        "additive_role_count": 2,
        "exact_total_candidate_count": 1,
        "lane_count": 2,
        "visible_trailing_candidate_count": 1,
    }
    assert result["safety"]["accounting_equation_can_change_or_supply_digits"] is False
    assert result["safety"]["numeric_authority"] is False


def test_wrong_visible_total_remains_unresolved_and_preserves_source_digits() -> None:
    pages = _pages(total_rows=[("301", "270")])
    result = build_accounting_additive_table_closure_v1(_axis(pages), pages, _spec())

    assert result["status"] == "UNRESOLVED_ADDITIVE_TABLE_CLOSURE"
    assert result["exact_total_candidates"] == []
    assert result["unresolved_reasons"] == [
        "NO_TRAILING_ROW_EQUALS_VISIBLE_COMPONENT_SUMS_ON_EVERY_LANE"
    ]
    assert result["lane_sums"][0]["sum_value"]["coefficient"] == 300


def test_two_equal_visible_totals_are_ambiguous_not_selected() -> None:
    pages = _pages(total_rows=[("300", "270"), ("300", "270")])
    result = build_accounting_additive_table_closure_v1(_axis(pages), pages, _spec())

    assert result["status"] == "UNRESOLVED_ADDITIVE_TABLE_CLOSURE"
    assert result["metrics"]["exact_total_candidate_count"] == 2
    assert result["unresolved_reasons"] == ["MULTIPLE_TRAILING_ROWS_EQUAL_VISIBLE_COMPONENT_SUMS"]


def test_missing_component_recognition_cannot_be_filled_by_equation() -> None:
    pages = _pages()
    pages[0]["lines"][5]["numeric_recognition"] = {
        "raw_prediction": "",
        "reader_score": 0.2,
    }
    result = build_accounting_additive_table_closure_v1(_axis(pages), pages, _spec())

    assert result["status"] == "UNRESOLVED_ADDITIVE_TABLE_CLOSURE"
    assert result["lane_sums"] == []
    assert result["unresolved_reasons"] == [
        "ADDITIVE_CHILD_LANES_INCOMPLETE_OR_NUMERIC_TOKEN_UNRESOLVED"
    ]


def test_visible_dash_is_zero_and_decimal_scales_are_compared_exactly() -> None:
    pages = _pages(total_rows=[("100,5", "270")])
    pages[0]["lines"][2]["numeric_recognition"] = {
        "raw_prediction": "100,5",
        "reader_score": 0.95,
    }
    pages[0]["lines"][5]["numeric_recognition"] = {
        "raw_prediction": "-",
        "reader_score": 0.95,
    }

    result = build_accounting_additive_table_closure_v1(_axis(pages), pages, _spec())

    assert result["status"] == "CORROBORATED_EXACT_UNIQUE_TRAILING_TOTAL"
    assert result["lane_sums"][0]["component_values"] == [
        {"coefficient": 1005, "percentage_mark_present": False, "scale": 1},
        {"coefficient": 0, "percentage_mark_present": False, "scale": 0},
    ]
    assert result["lane_sums"][0]["sum_value"] == {
        "coefficient": 1005,
        "percentage_mark_present": False,
        "scale": 1,
    }


def test_money_and_percentage_surfaces_cannot_close_one_lane() -> None:
    pages = _pages(total_rows=[("300", "270")])
    pages[0]["lines"][5]["numeric_recognition"] = {
        "raw_prediction": "200%",
        "reader_score": 0.95,
    }

    result = build_accounting_additive_table_closure_v1(_axis(pages), pages, _spec())

    assert result["status"] == "UNRESOLVED_ADDITIVE_TABLE_CLOSURE"
    assert result["lane_sums"] == []
    assert result["unresolved_reasons"] == [
        "ADDITIVE_CHILD_LANES_INCOMPLETE_OR_NUMERIC_TOKEN_UNRESOLVED"
    ]


def test_exact_replay_rejects_coordinated_equation_mutation() -> None:
    pages = _pages()
    axis = _axis(pages)
    result = build_accounting_additive_table_closure_v1(axis, pages, _spec())
    forged = copy.deepcopy(result)
    forged["lane_sums"][0]["sum_value"]["coefficient"] = 999
    material = copy.deepcopy(forged)
    material.pop("closure_id")
    forged["closure_id"] = "aatcv1:closure:" + canonical_json_sha256_v1(material)

    with pytest.raises(AccountingAdditiveTableClosureV1Error, match="replay exactly"):
        validate_accounting_additive_table_closure_replay_v1(forged, axis, pages, _spec())


def test_declared_source_group_replaces_its_exact_components_without_double_count() -> None:
    spec = _spec()
    spec["format_version"] = "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V2"
    spec["presence_evidence_mode"] = "GLOBAL_CORE_HITS"
    spec["required_role_combinations"] = [["SHORT_TERM", "MEDIUM_TERM"]]
    for child in spec["children"]:
        child["presence"] = "OPTIONAL"
    spec["children"].insert(
        0,
        {
            "aliases": ["Dư nợ lõi"],
            "presence": "OPTIONAL",
            "role": "CORE_GROUP",
            "role_kind": "SOURCE_ONLY_GROUP_PARENT",
        },
    )
    pages = _pages(total_rows=[("310", "280")])
    lines = pages[0]["lines"]
    lines[1:1] = [
        _line(20, "Dư nợ lõi", "", [50, 70, 300, 92]),
        _line(21, "300", "300", [600, 70, 700, 92]),
        _line(22, "270", "270", [800, 70, 900, 92]),
    ]
    lines[10:10] = [
        _line(23, "Phụ trội", "", [50, 180, 300, 202]),
        _line(24, "10", "10", [600, 180, 700, 202]),
        _line(25, "10", "10", [800, 180, 900, 202]),
    ]
    spec["children"].append(
        {
            "aliases": ["Phụ trội"],
            "presence": "OPTIONAL",
            "role": "MARGIN",
            "role_kind": "ADDITIVE_CHILD",
        }
    )
    for ordinal, line in enumerate(lines):
        line["line_ordinal"] = ordinal
        line["sample_id"] = f"sample-{ordinal + 1:09d}"
        line["crop_ref"] = {
            "path": f"opaque/crop-{ordinal + 1:04d}.png",
            "sha256": f"{ordinal + 1:064x}",
            "size_bytes": 101 + ordinal,
        }
    axis = build_accounting_family_row_axis_v1(pages, spec)
    equivalences = [{"group_role": "CORE_GROUP", "component_roles": ["SHORT_TERM", "MEDIUM_TERM"]}]

    result = build_accounting_additive_table_closure_v1(
        axis,
        pages,
        spec,
        source_group_equivalences=equivalences,
    )

    assert result["format_version"] == "ACCOUNTING_ADDITIVE_TABLE_CLOSURE_V2"
    assert result["status"] == "CORROBORATED_EXACT_UNIQUE_TRAILING_TOTAL"
    assert result["additive_roles"] == ["CORE_GROUP", "MARGIN"]
    assert [item["sum_value"]["coefficient"] for item in result["lane_sums"]] == [310, 280]
